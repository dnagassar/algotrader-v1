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
import html
import re

from algotrader.errors import ValidationError

__all__ = [
    "DELISTING_FORMS",
    "EPISODE_GAP_DAYS",
    "PERIODIC_REPORT_FORMS",
    "RECOVERY_STRATA",
    "TICKER_TAGGING_ERA_START",
    "DelistingEpisode",
    "DelistingFiling",
    "DelistingRecord",
    "build_delisting_records",
    "group_delisting_episodes",
    "extract_trading_symbols",
    "parse_form_index",
    "price_admission_window",
    "select_symbol_source_filing",
    "summarize_symbol_recovery",
    "symbol_from_document_name",
]

DELISTING_FORMS = ("25", "25-NSE")
PERIODIC_REPORT_FORMS = ("10-K", "10-Q", "20-F", "40-F")
# Inline XBRL cover-page tagging phased in from 2019; before that a historical
# ticker is generally not recoverable from EDGAR at all.
TICKER_TAGGING_ERA_START = date(2019, 1, 1)

# An inline-XBRL fact is an element, not an attribute value, and issuers
# routinely wrap the visible text in presentation markup:
#   <ix:nonNumeric name="dei:TradingSymbol" ...><b>BLUA</b></ix:nonNumeric>
# so the value has to be read from the element body with that markup removed.
# Matching the character straight after the opening tag — which the first
# version of this parser did — silently loses every wrapped filing.
_IX_FACT_OPEN = re.compile(
    r"<ix:nonnumeric\b[^>]*?\bname\s*=\s*[\"']\s*([^\"']+?)\s*[\"'][^>]*>", re.I
)
_IX_FACT_CLOSE = re.compile(r"</ix:nonnumeric\s*>", re.I)
_PLAIN_FACT = re.compile(
    r"<dei:(TradingSymbol|SecurityExchangeName)\b[^>]*>(.*?)</dei:\1\s*>",
    re.I | re.S,
)
_INNER_MARKUP = re.compile(r"<[^>]*>")
_DOCUMENT_STEM = re.compile(r"^([a-z0-9\-]{1,12})-\d{8}\.htm$", re.I)
_SYMBOL_SHAPE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,14}$")
# Cover pages tag an explicit placeholder when a registered class has no
# ticker. Those are absences, not symbols, and must never enter the registry.
_NON_SYMBOL_VALUES = frozenset({"NONE", "N/A", "NA.", "NOTAPPLICABLE"})
# Zero-width and non-breaking characters are used as layout spacers inside the
# tagged value and are not part of the symbol.
_INVISIBLE_CHARACTERS = "\u200b\u00a0\ufeff\u2060"


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


def _clean_fact_text(raw: str) -> str:
    """Reduce a fact's element body to the text a reader would see.

    Tags are stripped before and after entity decoding: a filing may wrap the
    value in markup, escape markup into the value, or both.
    """

    text = _INNER_MARKUP.sub("", raw)
    text = _INNER_MARKUP.sub("", html.unescape(text))
    for character in _INVISIBLE_CHARACTERS:
        text = text.replace(character, "")
    return " ".join(text.split())


def _fact_values(text: str, concept: str) -> list[str]:
    """Every value tagged against one `dei` concept, in document order.

    Handles the inline-XBRL form used by filings and the plain element form
    used by an extracted instance document.
    """

    target = f"dei:{concept}".casefold()
    values: list[str] = []
    for opening in _IX_FACT_OPEN.finditer(text):
        if opening.group(1).casefold() != target:
            continue
        # These concepts are leaf facts, so the first closing tag is theirs.
        closing = _IX_FACT_CLOSE.search(text, opening.end())
        if closing is None:
            continue
        values.append(_clean_fact_text(text[opening.end(): closing.start()]))
    for match in _PLAIN_FACT.finditer(text):
        if match.group(1).casefold() == concept.casefold():
            values.append(_clean_fact_text(match.group(2)))
    return values


def extract_trading_symbols(document: bytes | str) -> tuple[tuple[str, ...], str]:
    """Recover cover-page symbols and exchange from an inline-XBRL filing."""

    text = (
        document.decode("utf-8", "ignore")
        if isinstance(document, bytes)
        else document
    )
    symbols: list[str] = []
    for candidate in _fact_values(text, "TradingSymbol"):
        cleaned = candidate.upper()
        if cleaned in _NON_SYMBOL_VALUES or not _SYMBOL_SHAPE.match(cleaned):
            continue
        if cleaned not in symbols:
            symbols.append(cleaned)
    exchanges = [value for value in _fact_values(text, "SecurityExchangeName") if value]
    return tuple(symbols), exchanges[0] if exchanges else ""


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
        if form not in PERIODIC_REPORT_FORMS:
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


# A company that delists, relists, and delists again is two events, not one.
# Form 25 filings for the several classes of a single delisting land within
# weeks of each other, so a year of silence separates episodes safely.
EPISODE_GAP_DAYS = 365


@dataclass(frozen=True, slots=True)
class DelistingEpisode:
    """One delisting event for one CIK, and every Form 25 that constitutes it."""

    cik: str
    company: str
    delisted_on: date
    last_filed_on: date
    filing_count: int
    form_types: tuple[str, ...]

    def as_payload(self) -> dict[str, object]:
        return {
            "cik": self.cik,
            "company": self.company,
            "delisted_on": self.delisted_on.isoformat(),
            "last_filed_on": self.last_filed_on.isoformat(),
            "filing_count": self.filing_count,
            "form_types": list(self.form_types),
        }


def group_delisting_episodes(
    filings: Sequence[DelistingFiling],
    *,
    gap_days: int = EPISODE_GAP_DAYS,
) -> tuple[DelistingEpisode, ...]:
    """Collapse a CIK's Form 25 filings into distinct delisting episodes.

    `delisted_on` is the **earliest** filing in an episode. Two reasons: the
    several classes of one delisting are filed days apart and the earliest
    bounds them all, and truncating a price series too early is the safe
    direction of error when the whole point is to sever a ticker-reuse splice.

    Note this is the Form 25 *filing* date, not the effective date, which Rule
    12d2-2 puts ten days later. That also errs early, and deliberately so.
    """

    by_cik: dict[str, list[DelistingFiling]] = {}
    for filing in filings:
        by_cik.setdefault(filing.cik, []).append(filing)

    episodes: list[DelistingEpisode] = []
    for cik, cik_filings in by_cik.items():
        ordered = sorted(cik_filings, key=lambda item: (item.filed, item.form_type))
        current: list[DelistingFiling] = []
        for filing in ordered:
            if current and (filing.filed - current[-1].filed).days > gap_days:
                episodes.append(_episode(cik, current))
                current = []
            current.append(filing)
        if current:
            episodes.append(_episode(cik, current))
    episodes.sort(key=lambda episode: (episode.delisted_on, episode.cik))
    return tuple(episodes)


def _episode(cik: str, filings: Sequence[DelistingFiling]) -> DelistingEpisode:
    return DelistingEpisode(
        cik=cik,
        # The company name can drift across filings; the latest is the closest
        # to how the entity was known when it left the exchange.
        company=filings[-1].company,
        delisted_on=filings[0].filed,
        last_filed_on=filings[-1].filed,
        filing_count=len(filings),
        form_types=tuple(sorted({filing.form_type for filing in filings})),
    )


RECOVERY_STRATA = ("era", "source_form", "entity_type", "outcome")


def summarize_symbol_recovery(
    rows: Sequence[Mapping[str, object]],
    *,
    strata: Sequence[str] = RECOVERY_STRATA,
) -> dict[str, object]:
    """Recovery counts overall and within each stratum.

    The V6.02 sample of seven produced a filer-type story that a defect had
    manufactured, so the rate is never reported on its own: every stratum is
    counted here and quoted together with its denominator.
    """

    total = len(rows)
    resolved = sum(1 for row in rows if row.get("ticker_recoverable"))
    breakdown: dict[str, dict[str, dict[str, object]]] = {}
    for stratum in strata:
        buckets: dict[str, dict[str, object]] = {}
        for row in rows:
            key = str(row.get(stratum, "")) or "unknown"
            bucket = buckets.setdefault(key, {"total": 0, "resolved": 0})
            bucket["total"] = int(bucket["total"]) + 1
            if row.get("ticker_recoverable"):
                bucket["resolved"] = int(bucket["resolved"]) + 1
        for bucket in buckets.values():
            count = int(bucket["total"])
            bucket["recovery_rate"] = (
                int(bucket["resolved"]) / count if count else 0.0
            )
        breakdown[stratum] = dict(sorted(buckets.items()))
    return {
        "total": total,
        "resolved": resolved,
        "recovery_rate": resolved / total if total else 0.0,
        "by": breakdown,
    }


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
