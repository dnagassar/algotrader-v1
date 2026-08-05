"""Coverage for the EDGAR delisting registry and its adapter.

Parsing is exercised on fixtures shaped like the real artifacts; the adapter is
exercised without a network. The registry's whole purpose is to prevent the
V6.01 ticker-reuse failure, so those cases are pinned explicitly.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.execution import edgar_delisting_adapter as adapter
from algotrader.research import delisting_registry as subject

_UA = "algotrader-research contact@example.com"

# Shaped exactly like the fixed-width rows in a real quarterly form.idx.
_INDEX = """Form Type   Company Name                                     CIK        Date Filed  File Name
---------------------------------------------------------------------------------------
10-K        SOME LIVE COMPANY INC                            1234567    2023-04-01  edgar/data/1/a.txt
25          SVB FINANCIAL GROUP                              719739     2023-05-02  edgar/data/719739/b.txt
25-NSE      Twitter, Inc.                                    1418091    2022-11-01  edgar/data/1418091/c.txt
25          BONSO ELECTRONICS INTERNATIONAL INC              846546     2023-06-23  edgar/data/846546/d.txt
253G2       NOT A DELISTING FORM                             999999     2023-06-23  edgar/data/999999/e.txt
"""


def test_form_index_extracts_only_delisting_forms() -> None:
    filings = subject.parse_form_index(_INDEX)

    assert [f.form_type for f in filings] == ["25", "25-NSE", "25"]
    # 253G2 starts with "25" as a string but is not a delisting form.
    assert all(f.form_type in subject.DELISTING_FORMS for f in filings)
    assert filings[0].company == "SVB FINANCIAL GROUP"
    assert filings[0].cik == "0000719739"
    assert filings[0].filed == date(2023, 5, 2)
    assert filings[1].cik == "0001418091"


def test_company_names_with_spaces_survive_parsing() -> None:
    filings = subject.parse_form_index(_INDEX)
    assert filings[1].company == "Twitter, Inc."
    assert filings[2].company == "BONSO ELECTRONICS INTERNATIONAL INC"


def test_form_index_accepts_bytes() -> None:
    assert subject.parse_form_index(_INDEX.encode("latin-1"))


def test_trading_symbols_are_recovered_from_cover_page_xbrl() -> None:
    document = """
    <ix:nonNumeric name="dei:TradingSymbol" contextRef="c1">SIVB</ix:nonNumeric>
    <ix:nonNumeric name="dei:SecurityExchangeName">The Nasdaq Stock Market LLC</ix:nonNumeric>
    <ix:nonNumeric name="dei:TradingSymbol" contextRef="c2">SIVBP</ix:nonNumeric>
    """

    symbols, exchange = subject.extract_trading_symbols(document)

    assert symbols == ("SIVB", "SIVBP")
    assert exchange == "The Nasdaq Stock Market LLC"


def test_symbol_extraction_deduplicates_and_rejects_junk() -> None:
    document = """
    <ix:nonNumeric name="dei:TradingSymbol">TWTR</ix:nonNumeric>
    <ix:nonNumeric name="dei:TradingSymbol">TWTR</ix:nonNumeric>
    <ix:nonNumeric name="dei:TradingSymbol">not a ticker at all</ix:nonNumeric>
    """

    symbols, exchange = subject.extract_trading_symbols(document)

    assert symbols == ("TWTR",)
    assert exchange == ""


def test_missing_tags_yield_no_symbol_rather_than_a_guess() -> None:
    assert subject.extract_trading_symbols("<html>no xbrl here</html>") == ((), "")


def test_document_filename_is_a_usable_cross_check() -> None:
    assert subject.symbol_from_document_name("sivb-20221231.htm") == "SIVB"
    assert subject.symbol_from_document_name("twtr-20220630.htm") == "TWTR"
    assert subject.symbol_from_document_name("index.htm") == ""
    assert subject.symbol_from_document_name("") == ""


# --- the V6.01 reuse failure, pinned ---------------------------------------


def test_symbol_source_never_uses_a_filing_after_delisting() -> None:
    """A successor entity can file under a reused ticker; it must be ignored."""

    delisted = date(2023, 5, 2)
    filings = [
        {"form": "10-K", "filed": date(2023, 2, 24), "doc": "sivb-20221231.htm"},
        {"form": "10-Q", "filed": date(2024, 8, 1), "doc": "other-20240630.htm"},
    ]

    chosen = subject.select_symbol_source_filing(filings, delisted_on=delisted)

    assert chosen is not None
    assert chosen["doc"] == "sivb-20221231.htm"


def test_latest_eligible_filing_wins() -> None:
    delisted = date(2023, 5, 2)
    filings = [
        {"form": "10-K", "filed": date(2021, 2, 1), "doc": "old.htm"},
        {"form": "10-Q", "filed": date(2023, 2, 24), "doc": "new-20221231.htm"},
    ]

    chosen = subject.select_symbol_source_filing(filings, delisted_on=delisted)

    assert chosen["doc"] == "new-20221231.htm"


def test_no_eligible_filing_returns_none() -> None:
    filings = [{"form": "8-K", "filed": date(2020, 1, 1), "doc": "x.htm"}]
    assert (
        subject.select_symbol_source_filing(filings, delisted_on=date(2023, 5, 2))
        is None
    )


def test_price_admission_window_stops_at_the_delisting() -> None:
    record = subject.DelistingRecord(
        cik="0000719739",
        company="SVB FINANCIAL GROUP",
        delisted_on=date(2023, 5, 2),
        symbols=("SIVB",),
        exchange="Nasdaq",
        symbol_source="cover_page_xbrl",
        ticker_recoverable=True,
    )

    window = subject.price_admission_window(record)

    assert window["admit_through"] == "2023-05-02"
    assert window["admit_after"] is None
    assert window["reuse_risk_after_delisting"] is True


def test_unrecoverable_tickers_are_marked_not_dropped() -> None:
    records = subject.build_delisting_records(
        [
            {
                "cik": "846546",
                "company": "OLD CO",
                "delisted_on": date(2012, 3, 1),
                "symbols": (),
            },
            {
                "cik": "719739",
                "company": "SVB FINANCIAL GROUP",
                "delisted_on": date(2023, 5, 2),
                "symbols": ("SIVB",),
                "symbol_source": "cover_page_xbrl",
            },
        ]
    )

    assert len(records) == 2
    pre_era = records[0]
    assert pre_era.delisted_on < subject.TICKER_TAGGING_ERA_START
    assert pre_era.ticker_recoverable is False
    assert pre_era.symbol_source == "unrecoverable"
    assert records[1].ticker_recoverable is True
    # Sorted by delisting date, so the coverage boundary is visible.
    assert records[0].delisted_on < records[1].delisted_on


def test_malformed_symbols_are_refused() -> None:
    with pytest.raises(ValidationError, match="malformed symbol"):
        subject.build_delisting_records(
            [{"cik": "1", "delisted_on": date(2023, 1, 1), "symbols": ("no spaces",)}]
        )


def test_delisted_on_must_be_a_date() -> None:
    with pytest.raises(ValidationError, match="must be a date"):
        subject.build_delisting_records(
            [{"cik": "1", "delisted_on": "2023-01-01", "symbols": ()}]
        )


# --- adapter safety --------------------------------------------------------


def _exploding(*args, **kwargs):
    raise AssertionError("the network must not be touched")


def test_dry_run_performs_zero_network_calls(tmp_path: Path) -> None:
    receipt = adapter.run_edgar_fetch(
        adapter.EdgarRequestConfig(
            kind="form_index", user_agent=_UA, output_root=tmp_path,
            year=2023, quarter=2,
        ),
        http_get=_exploding,
    )

    assert receipt["network_access_attempted"] is False
    assert receipt["refresh_state"] == "dry_run_request_plan_built"


def test_sec_requires_identifying_contact_information(tmp_path: Path) -> None:
    for bad in ("", "bot", "algotrader-no-contact"):
        with pytest.raises(ValidationError, match="contact information"):
            adapter.EdgarRequestConfig(
                kind="form_index", user_agent=bad, output_root=tmp_path,
                year=2023, quarter=2,
            )


def test_requests_are_get_against_allowlisted_sec_hosts(tmp_path: Path) -> None:
    index = adapter.build_edgar_request(
        adapter.EdgarRequestConfig(
            kind="form_index", user_agent=_UA, output_root=tmp_path,
            year=2023, quarter=2,
        )
    )
    subs = adapter.build_edgar_request(
        adapter.EdgarRequestConfig(
            kind="submissions", user_agent=_UA, output_root=tmp_path, cik="719739",
        )
    )

    for request in (index, subs):
        assert request["method"] == "GET"
        assert request["destination_host"] in adapter.DESTINATION_ALLOWLIST
        assert request["credentials_used"] is False
        assert request["authenticated"] is False
    assert index["destination_path"].endswith("/2023/QTR2/form.idx")
    # CIK is zero-padded to ten digits, which EDGAR requires.
    assert subs["destination_path"] == "/submissions/CIK0000719739.json"


def test_archive_path_cannot_traverse_directories(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="traverse"):
        adapter.build_edgar_request(
            adapter.EdgarRequestConfig(
                kind="document", user_agent=_UA, output_root=tmp_path,
                path="/Archives/../../etc/passwd",
            )
        )


def test_unallowlisted_host_is_refused() -> None:
    with pytest.raises(ValidationError, match="not allowlisted"):
        adapter._https_get("evil.example.com", "/x", _UA)


def test_live_fetch_requires_explicit_authorization(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="requires explicit authorization"):
        adapter.EdgarRequestConfig(
            kind="form_index", user_agent=_UA, output_root=tmp_path,
            year=2023, quarter=2, mode="live_fetch",
        )


def test_adapter_has_no_credential_reading_code_path() -> None:
    import ast

    tree = ast.parse(Path(adapter.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    attributes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Attribute):
            attributes.add(node.attr)

    for module in ("os", "dotenv", "keyring", "subprocess"):
        assert module not in imported, f"credential-capable import: {module}"
    for accessor in ("getenv", "environ", "get_password", "load_dotenv"):
        assert accessor not in attributes, f"credential accessor used: {accessor}"
