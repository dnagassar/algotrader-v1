"""Pure parsing for a survivorship-aware delisting registry.

Every function here is offline and deterministic: bytes in, records out. The
network lives entirely in `edgar_delisting_adapter`, so this layer can be tested
exhaustively without touching SEC.

The registry exists because a ticker is not a security identifier. The V6.01
probe showed a symbol can be silently reused by an unrelated company — `SHLD`
returns a series that begins in 2023 for a company delisted in 2018, and `BBBY`
returns one unbroken series spanning two different corporations across a
bankruptcy. A price history is therefore only trustworthy up to the delisting
date of the CIK that actually owned the ticker at the time.

Coverage boundary, stated once and enforced by `TICKER_TAGGING_ERA_START`:
cover-page inline XBRL became broadly required in 2019, so delistings before
then yield a CIK and a date but usually no recoverable symbol. Those records are
kept and marked, never silently dropped and never guessed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
import re

from algotrader.errors import ValidationError

__all__ = [
    "DELISTING_FORMS",
    "TICKER_TAGGING_ERA_START",
    "DelistingFiling",
    "DelistingRecord",
    "build_delisting_records",
    "extract_trading_symbols",
    "parse_form_index",
    "select_symbol_source_filing",
]

DELISTING_FORMS = ("25", "25-NSE")
# Inline XBRL cover-page tagging phased in from 2019; before that a historical
# ticker is generally not recoverable from EDGAR at all.
TICKER_TAGGING_ERA_START = date(2019, 1, 1)

_SYMBOL_TAG = re.compile(
    r'name="dei:TradingSymbol"[^>]*>\s*([^<\s][^<]{0,19}?)\s*<', re.I
)
_EXCHANGE_TAG = re.compile(
    r'name="dei:SecurityExchangeName"[^>]*>\s*([^<\s][^<]{0,60}?)\s*<', re.I
)
_DOCUMENT_STEM = re.compile(r"^([a-z0-9\-]{1,12})-\d{8}\.htm$", re.I)
_SYMBOL_SHAPE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,14}$")


@dataclass(frozen=True, slots=True)
class DelistingFiling:
    """One Form 25 row from a quarterly EDGAR index."""

    form_type: str
    company: str
    cik: str
    filed: date
    archive_path: str


@dataclass(frozen=True, slots=True)
class DelistingRecord:
    """A CIK, its recovered symbols, and the date its listing ended."""

    cik: str
    company: str
    delisted_on: date
    symbols: tuple[str, ...]
    exchange: str
    symbol_source: str
    ticker_recoverable: bool

    def as_payload(self) -> dict[str, object]:
        return {
            "cik": self.cik,
            "company": self.company,
            "delisted_on": self.delisted_on.isoformat(),
            "symbols": list(self.symbols),
            "exchange": self.exchange,
            "symbol_source": self.symbol_source,
            "ticker_recoverable": self.ticker_recoverable,
        }


def parse_form_index(payload: bytes | str) -> tuple[DelistingFiling, ...]:
    """Extract Form 25 and 25-NSE rows from a quarterly `form.idx`.

    The file is fixed-width and sorted by form type, so rows are matched on the
    leading form token rather than by splitting on whitespace, which would break
    on company names containing spaces.
    """

    text = (
        payload.decode("latin-1") if isinstance(payload, bytes) else payload
    )
    filings: list[DelistingFiling] = []
    for line in text.splitlines():
        token = line.split(" ", 1)[0].strip()
        if token not in DELISTING_FORMS:
            continue
        match = re.match(
            r"^(\S+)\s+(.+?)\s{2,}(\d{1,10})\s+(\d{4}-\d{2}-\d{2})\s+(\S+)\s*$",
            line,
        )
        if not match:
            continue
        form_type, company, cik, filed, path = match.groups()
        if form_type not in DELISTING_FORMS:
            continue
        filings.append(
            DelistingFiling(
                form_type=form_type,
                company=company.strip(),
                cik=cik.zfill(10),
                filed=date.fromisoformat(filed),
                archive_path=path.strip(),
            )
        )
    return tuple(filings)


def extract_trading_symbols(document: bytes | str) -> tuple[tuple[str, ...], str]:
    """Recover cover-page symbols and exchange from an inline-XBRL filing."""

    text = (
        document.decode("utf-8", "ignore")
        if isinstance(document, bytes)
        else document
    )
    symbols: list[str] = []
    for candidate in _SYMBOL_TAG.findall(text):
        cleaned = candidate.strip().upper()
        if _SYMBOL_SHAPE.match(cleaned) and cleaned not in symbols:
            symbols.append(cleaned)
    exchanges = _EXCHANGE_TAG.findall(text)
    exchange = exchanges[0].strip() if exchanges else ""
    return tuple(symbols), exchange


def symbol_from_document_name(document_name: str) -> str:
    """The filename stem is a free cross-check on the tagged symbol."""

    match = _DOCUMENT_STEM.match(document_name.strip())
    if not match:
        return ""
    candidate = match.group(1).upper()
    return candidate if _SYMBOL_SHAPE.match(candidate) else ""


def select_symbol_source_filing(
    filings: Sequence[Mapping[str, object]],
    *,
    delisted_on: date,
) -> Mapping[str, object] | None:
    """Choose the latest periodic report filed at or before the delisting.

    Later filings are never used: after delisting a shell can keep filing, and a
    successor entity can reuse the ticker. Only a report the company filed while
    still listed can attest to the symbol it traded under.
    """

    eligible = []
    for filing in filings:
        form = str(filing.get("form", ""))
        if form not in ("10-K", "10-Q", "20-F", "40-F"):
            continue
        filed = filing.get("filed")
        if not isinstance(filed, date) or filed > delisted_on:
            continue
        eligible.append((filed, filing))
    if not eligible:
        return None
    eligible.sort(key=lambda item: item[0])
    return eligible[-1][1]


def build_delisting_records(
    resolutions: Sequence[Mapping[str, object]],
) -> tuple[DelistingRecord, ...]:
    """Assemble final records, marking anything whose symbol is unrecoverable."""

    records: list[DelistingRecord] = []
    for item in resolutions:
        cik = str(item["cik"]).zfill(10)
        delisted_on = item["delisted_on"]
        if not isinstance(delisted_on, date):
            raise ValidationError("delisted_on must be a date.")
        symbols = tuple(str(value).upper() for value in item.get("symbols", ()))
        for symbol in symbols:
            if not _SYMBOL_SHAPE.match(symbol):
                raise ValidationError(f"malformed symbol: {symbol}")
        source = str(item.get("symbol_source", "none"))
        records.append(
            DelistingRecord(
                cik=cik,
                company=str(item.get("company", "")).strip(),
                delisted_on=delisted_on,
                symbols=symbols,
                exchange=str(item.get("exchange", "")).strip(),
                symbol_source=source if symbols else "unrecoverable",
                ticker_recoverable=bool(symbols),
            )
        )
    records.sort(key=lambda record: (record.delisted_on, record.cik))
    return tuple(records)


def price_admission_window(record: DelistingRecord) -> dict[str, object]:
    """The only window in which a price series for this ticker is trustworthy.

    Anything dated after the delisting belongs to whoever holds the symbol now,
    which is exactly how `BBBY` produced one unbroken series spanning two
    unrelated companies.
    """

    return {
        "cik": record.cik,
        "symbols": list(record.symbols),
        "admit_through": record.delisted_on.isoformat(),
        "admit_after": None,
        "reuse_risk_after_delisting": True,
        "ticker_recoverable": record.ticker_recoverable,
    }
