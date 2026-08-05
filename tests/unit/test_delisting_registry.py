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


# --- the V6.02 extraction defect, pinned -----------------------------------
#
# The first parser read the character straight after the opening tag, so any
# filing that wrapped the value in presentation markup returned nothing. That
# turned parseable filings into "unrecoverable" records and produced a false
# filer-type coverage story. Each fixture below is the real markup shape taken
# from the filing named in its comment.


def test_symbols_wrapped_in_presentation_markup_are_recovered() -> None:
    # BlueRiver Acquisition Corp 10-K: value inside <b>.
    bold = (
        '<ix:nonNumeric contextRef="Duration_1_1_2022_To_12_31_2022" '
        'name="dei:TradingSymbol" id="Tc_pSZk3">'
        '<b style="font-size:8pt;font-weight:bold;">BLUA</b></ix:nonNumeric>'
    )
    # 51Talk 20-F: value inside <span>.
    span = (
        '<ix:nonNumeric contextRef="Duration_1_1_2022_To_12_31_2022" '
        'name="dei:TradingSymbol" id="Tc_h8tLg">'
        '<span style="font-size:9pt;">COE</span></ix:nonNumeric>'
    )
    # Banco Santander Mexico 20-F: value inside <span>, exchange tagged with a
    # leading format attribute so `name` is not the first attribute.
    foreign = (
        '<ix:nonNumeric contextRef="Duration_1_1_2022" name="dei:TradingSymbol" '
        'id="Tc_jgM57">'
        '<span style="font-family:\'Times New Roman\';">BSMX</span>'
        "</ix:nonNumeric>"
        '<ix:nonNumeric format="ixt-sec:exchnameen" contextRef="Duration_1_1_2022" '
        'name="dei:SecurityExchangeName"><span>New York Stock Exchange</span>'
        "</ix:nonNumeric>"
    )

    assert subject.extract_trading_symbols(bold)[0] == ("BLUA",)
    assert subject.extract_trading_symbols(span)[0] == ("COE",)
    assert subject.extract_trading_symbols(foreign) == (
        ("BSMX",),
        "New York Stock Exchange",
    )


def test_bare_and_wrapped_values_are_read_the_same_way() -> None:
    """SVB tagged a bare value and passed the old parser; the others did not.

    Both forms must yield the same symbol, or the recovery rate measures the
    parser rather than EDGAR.
    """

    bare = '<ix:nonNumeric name="dei:TradingSymbol">SIVB</ix:nonNumeric>'
    wrapped = '<ix:nonNumeric name="dei:TradingSymbol"><b>SIVB</b></ix:nonNumeric>'

    assert subject.extract_trading_symbols(bare) == subject.extract_trading_symbols(
        wrapped
    )


def test_layout_spacers_and_entities_are_not_part_of_the_symbol() -> None:
    document = (
        '<ix:nonNumeric name="dei:TradingSymbol">'
        "&#8203; <span>&#160;</span>BRK.B&#160;</ix:nonNumeric>"
    )

    assert subject.extract_trading_symbols(document)[0] == ("BRK.B",)


def test_tagged_placeholders_are_absences_not_symbols() -> None:
    document = (
        '<ix:nonNumeric name="dei:TradingSymbol"><span>None</span></ix:nonNumeric>'
        '<ix:nonNumeric name="dei:TradingSymbol">N/A</ix:nonNumeric>'
        '<ix:nonNumeric name="dei:TradingSymbol"><b>REAL</b></ix:nonNumeric>'
    )

    assert subject.extract_trading_symbols(document)[0] == ("REAL",)


def test_plain_instance_elements_are_read_as_well_as_inline_xbrl() -> None:
    instance = (
        '<dei:TradingSymbol contextRef="c1">TWTR</dei:TradingSymbol>'
        '<dei:SecurityExchangeName contextRef="c1">NYSE</dei:SecurityExchangeName>'
    )

    assert subject.extract_trading_symbols(instance) == (("TWTR",), "NYSE")


def test_a_concept_whose_name_merely_contains_the_target_is_not_matched() -> None:
    document = (
        '<ix:nonNumeric name="dei:TradingSymbolAxis">NOTASYMBOL</ix:nonNumeric>'
        '<ix:nonNumeric name="custom:TradingSymbol">ALSONOT</ix:nonNumeric>'
    )

    assert subject.extract_trading_symbols(document)[0] == ()


# --- exact per-security attribution (the V6.03a defect) --------------------
#
# V6.03 attached every cover-page ticker to the delisting, which marked AAPL
# and ABBV as delisted and would have truncated live price series. These pin
# the repair, and in particular pin that it fails closed.

# Shaped like ProShares Trust II's cover page, where twenty series share one
# filing and each class's facts are joined only by contextRef.
_MULTI_CLASS_COVER = """
<ix:nonNumeric contextRef="cA" name="dei:Security12bTitle">ProShares Short VIX Short-Term Futures ETF</ix:nonNumeric>
<ix:nonNumeric contextRef="cA" name="dei:TradingSymbol"><b>SVXY</b></ix:nonNumeric>
<ix:nonNumeric contextRef="cA" name="dei:SecurityExchangeName">NYSEARCA</ix:nonNumeric>
<ix:nonNumeric contextRef="cB" name="dei:Security12bTitle">ProShares Ultra Gold</ix:nonNumeric>
<ix:nonNumeric contextRef="cB" name="dei:TradingSymbol"><span>UGL</span></ix:nonNumeric>
<ix:nonNumeric contextRef="cB" name="dei:SecurityExchangeName">NYSEARCA</ix:nonNumeric>
"""

_FORM25_XML = """<?xml version="1.0"?>
<edgarSubmission>
  <issuerName>ProShares Trust II</issuerName>
  <fileNumber>001-34200</fileNumber>
  <descriptionClassSecurity>ProShares Ultra Gold</descriptionClassSecurity>
  <ruleProvision>17 CFR 240.12d2-2(a)(3)</ruleProvision>
</edgarSubmission>
"""

# Shaped like a real N-CEN, where the ticker is an attribute, not an element.
_NCEN_XML = """<?xml version="1.0"?>
<edgarSubmission>
 <managementInvestmentQuestionSeriesInfo>
  <managementInvestmentQuestion>
   <mgmtInvFundName>JPMorgan Ultra-Short Municipal Income ETF</mgmtInvFundName>
   <mgmtInvSeriesId>S000063269</mgmtInvSeriesId>
   <sharesOutstandings>
    <sharesOutstanding sharesOutstandingClassId="C000205216" sharesOutstandingTickerSymbol="JMST"/>
   </sharesOutstandings>
   <fundTypes><fundType>Exchange-Traded Fund</fundType></fundTypes>
  </managementInvestmentQuestion>
  <managementInvestmentQuestion>
   <mgmtInvFundName>JPMorgan Something Else ETF</mgmtInvFundName>
   <mgmtInvSeriesId>S000099999</mgmtInvSeriesId>
   <sharesOutstandings>
    <sharesOutstanding sharesOutstandingClassId="C000111111" sharesOutstandingTickerSymbol="JOTH"/>
   </sharesOutstandings>
   <fundTypes><fundType>Exchange-Traded Fund</fundType></fundTypes>
  </managementInvestmentQuestion>
 </managementInvestmentQuestionSeriesInfo>
</edgarSubmission>
"""


def test_form25_names_the_class_it_delists() -> None:
    """V6.02 concluded Form 25 carries no ticker. True, and one step short."""

    parsed = subject.parse_form25_security(_FORM25_XML)

    assert parsed["description_class_security"] == "ProShares Ultra Gold"
    assert parsed["file_number"] == "001-34200"
    assert parsed["issuer_name"] == "ProShares Trust II"


def test_cover_page_classes_keep_the_title_to_ticker_pairing() -> None:
    classes = subject.extract_cover_page_classes(_MULTI_CLASS_COVER)

    assert {(c.title, c.symbol) for c in classes} == {
        ("ProShares Short VIX Short-Term Futures ETF", "SVXY"),
        ("ProShares Ultra Gold", "UGL"),
    }
    assert all(c.exchange == "NYSEARCA" for c in classes)


def test_only_the_delisted_class_is_attributed() -> None:
    """The V6.03a defect, directly: SVXY must not inherit UGL's delisting."""

    result = subject.attribute_delisted_symbols(
        "ProShares Ultra Gold",
        cover_page_classes=subject.extract_cover_page_classes(_MULTI_CLASS_COVER),
    )

    assert result["symbols"] == ("UGL",)
    assert result["attribution"] == "matched_delisted_class"
    assert result["candidate_count"] == 2


def test_a_sole_registered_class_needs_no_match() -> None:
    single = (
        '<ix:nonNumeric contextRef="c1" name="dei:Security12bTitle">Common Stock</ix:nonNumeric>'
        '<ix:nonNumeric contextRef="c1" name="dei:TradingSymbol">SIVB</ix:nonNumeric>'
    )

    result = subject.attribute_delisted_symbols(
        "Common Stock, par value $0.001",
        cover_page_classes=subject.extract_cover_page_classes(single),
    )

    assert result["symbols"] == ("SIVB",)
    assert result["attribution"] == "sole_registered_class"


def test_attribution_fails_closed_when_the_class_cannot_be_identified() -> None:
    """Emitting nothing beats truncating a live series, which is what V6.03 did."""

    classes = subject.extract_cover_page_classes(_MULTI_CLASS_COVER)

    unmatched = subject.attribute_delisted_symbols(
        "Some Entirely Different Security", cover_page_classes=classes
    )
    blank = subject.attribute_delisted_symbols("", cover_page_classes=classes)

    assert unmatched["symbols"] == ()
    assert unmatched["attribution"] == "unmatched_delisted_class"
    assert blank["symbols"] == ()
    assert blank["attribution"] == "unmatched_delisted_class"


def test_no_candidates_is_reported_rather_than_guessed() -> None:
    result = subject.attribute_delisted_symbols("Common Stock")

    assert result["symbols"] == ()
    assert result["attribution"] == "no_candidate_classes"


def test_ncen_yields_fund_series_and_class_tickers() -> None:
    """The only route by which a dead ETF can be named at all."""

    series = subject.parse_ncen_series(_NCEN_XML)

    assert len(series) == 2
    first = series[0]
    assert first.name == "JPMorgan Ultra-Short Municipal Income ETF"
    assert first.series_id == "S000063269"
    assert first.fund_type == "Exchange-Traded Fund"
    assert first.symbols == ("JMST",)


def test_a_delisted_fund_series_resolves_to_its_own_ticker_only() -> None:
    result = subject.attribute_delisted_symbols(
        "JPMorgan Ultra-Short Municipal Income ETF",
        fund_series=subject.parse_ncen_series(_NCEN_XML),
    )

    assert result["symbols"] == ("JMST",)
    assert result["attribution"] == "matched_delisted_class"


def test_legal_form_differences_do_not_defeat_the_match() -> None:
    """Filers write the same security differently in Form 25 and on the cover."""

    result = subject.attribute_delisted_symbols(
        "ProShares Ultra Gold Fund",
        cover_page_classes=subject.extract_cover_page_classes(_MULTI_CLASS_COVER),
    )

    assert result["symbols"] == ("UGL",)


_SGML_HEADER = """<SEC-HEADER>
<SERIES-AND-CLASSES-CONTRACTS-DATA>
<EXISTING-SERIES-AND-CLASSES-CONTRACTS>
<SERIES>
<OWNER-CIK>0001547950
<SERIES-ID>S000067929
<SERIES-NAME>Armor US Equity Index ETF
<CLASS-CONTRACT>
<CLASS-CONTRACT-ID>C000217769
<CLASS-CONTRACT-NAME>Armor US Equity Index ETF
<CLASS-CONTRACT-TICKER-SYMBOL>ARMR
</CLASS-CONTRACT>
</SERIES>
</EXISTING-SERIES-AND-CLASSES-CONTRACTS>
</SERIES-AND-CLASSES-CONTRACTS-DATA>
</SEC-HEADER>
"""


def test_sgml_header_yields_fund_series_and_ticker() -> None:
    """Preferred fund route: kilobytes, and available from 2006 not 2018."""

    series = subject.parse_filing_header_series(_SGML_HEADER)

    assert len(series) == 1
    assert series[0].name == "Armor US Equity Index ETF"
    assert series[0].series_id == "S000067929"
    assert series[0].symbols == ("ARMR",)


def test_a_header_without_series_data_yields_nothing() -> None:
    assert subject.parse_filing_header_series("<SEC-HEADER>plain</SEC-HEADER>") == ()


def test_a_delisted_fund_resolves_through_the_header_route() -> None:
    result = subject.attribute_delisted_symbols(
        "Armor US Equity Index ETF",
        fund_series=subject.parse_filing_header_series(_SGML_HEADER),
    )

    assert result["symbols"] == ("ARMR",)
    assert result["attribution"] == "sole_registered_class"


def test_a_name_matching_several_classes_is_refused() -> None:
    ambiguous = (
        '<ix:nonNumeric contextRef="c1" name="dei:Security12bTitle">Growth Fund</ix:nonNumeric>'
        '<ix:nonNumeric contextRef="c1" name="dei:TradingSymbol">AAA</ix:nonNumeric>'
        '<ix:nonNumeric contextRef="c2" name="dei:Security12bTitle">Growth Fund</ix:nonNumeric>'
        '<ix:nonNumeric contextRef="c2" name="dei:TradingSymbol">BBB</ix:nonNumeric>'
    )

    result = subject.attribute_delisted_symbols(
        "Growth Fund", cover_page_classes=subject.extract_cover_page_classes(ambiguous)
    )

    assert result["symbols"] == ()
    assert result["attribution"] == "ambiguous_class_match"


# --- recovery reporting ----------------------------------------------------


def test_recovery_is_summarised_with_denominators_per_stratum() -> None:
    rows = [
        {"ticker_recoverable": True, "source_form": "10-K", "era": "tagging_era"},
        {"ticker_recoverable": True, "source_form": "20-F", "era": "tagging_era"},
        {"ticker_recoverable": False, "source_form": "20-F", "era": "tagging_era"},
        {"ticker_recoverable": False, "source_form": "", "era": "pre_tagging_era"},
    ]

    summary = subject.summarize_symbol_recovery(
        rows, strata=("source_form", "era")
    )

    assert summary["total"] == 4
    assert summary["resolved"] == 2
    assert summary["recovery_rate"] == 0.5
    by_form = summary["by"]["source_form"]
    assert by_form["10-K"] == {"total": 1, "resolved": 1, "recovery_rate": 1.0}
    assert by_form["20-F"] == {"total": 2, "resolved": 1, "recovery_rate": 0.5}
    # An absent stratum value is labelled rather than dropped.
    assert by_form["unknown"]["total"] == 1
    assert summary["by"]["era"]["pre_tagging_era"]["recovery_rate"] == 0.0


def test_recovery_summary_of_nothing_does_not_divide_by_zero() -> None:
    summary = subject.summarize_symbol_recovery([])

    assert summary["total"] == 0
    assert summary["recovery_rate"] == 0.0


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
