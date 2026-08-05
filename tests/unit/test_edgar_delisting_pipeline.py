"""Coverage for the full-history delisting pipeline.

Every test injects its own fetcher, so the suite exercises the real staging,
resumption, and outcome logic without touching SEC. The payloads are shaped
like the real artifacts, including the presentation markup that defeated the
first version of the symbol parser.
"""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.execution import edgar_delisting_pipeline as subject

_UA = "algotrader-research contact@example.com"

_INDEX_2023Q2 = """Form Type   Company Name                                     CIK        Date Filed  File Name
---------------------------------------------------------------------------------------
10-K        STILL LISTED INC                                 111111     2023-04-01  edgar/data/1/a.txt
25          SVB FINANCIAL GROUP                              719739     2023-05-02  edgar/data/719739/b.txt
25-NSE      SVB FINANCIAL GROUP                              719739     2023-05-04  edgar/data/719739/c.txt
25          BLUERIVER ACQUISITION CORP                       1831006    2023-04-10  edgar/data/1831006/d.txt
"""

_INDEX_2023Q3 = """Form Type   Company Name                                     CIK        Date Filed  File Name
---------------------------------------------------------------------------------------
25          LATER DELISTING CO                               222222     2023-08-15  edgar/data/222222/e.txt
"""

_SUBMISSIONS = json.dumps(
    {
        "entityType": "operating",
        "sicDescription": "State Commercial Banks",
        "filings": {
            "recent": {
                "form": ["10-K", "8-K", "10-Q"],
                "filingDate": ["2023-02-24", "2023-03-10", "2024-08-01"],
                "accessionNumber": [
                    "0000719739-23-000021",
                    "0000719739-23-000030",
                    "0000719739-24-000010",
                ],
                "primaryDocument": [
                    "sivb-20221231.htm",
                    "sivb-8k.htm",
                    "successor-20240630.htm",
                ],
            }
        },
    }
).encode()

# The value is wrapped in presentation markup, as real filings are.
_DOCUMENT = (
    '<ix:nonNumeric contextRef="d1" name="dei:TradingSymbol"><b>SIVB</b>'
    "</ix:nonNumeric>"
    '<ix:nonNumeric contextRef="d2" name="dei:TradingSymbol"><span>SIVBP</span>'
    "</ix:nonNumeric>"
    '<ix:nonNumeric name="dei:SecurityExchangeName">NASDAQ</ix:nonNumeric>'
).encode()

_UNTAGGED_DOCUMENT = b"<html><body>an older filing with no cover-page tags</body></html>"


def _config(tmp_path: Path, **overrides: object) -> subject.DelistingPipelineConfig:
    settings: dict[str, object] = {
        "user_agent": _UA,
        "output_root": tmp_path,
        "mode": "live_fetch",
        "live_fetch_authorized": True,
        "start_quarter": (2023, 2),
        "end_quarter": (2023, 3),
        "request_interval_seconds": 0.1,
    }
    settings.update(overrides)
    return subject.DelistingPipelineConfig(**settings)  # type: ignore[arg-type]


def _index_fetcher(calls: list[str]):
    def fetch(host: str, path: str, user_agent: str) -> bytes:
        calls.append(path)
        if path.endswith("/2023/QTR2/form.idx"):
            return _INDEX_2023Q2.encode("latin-1")
        if path.endswith("/2023/QTR3/form.idx"):
            return _INDEX_2023Q3.encode("latin-1")
        raise AssertionError(f"unexpected path: {path}")

    return fetch


def _resolution_fetcher(calls: list[str], *, document: bytes = _DOCUMENT):
    def fetch(host: str, path: str, user_agent: str) -> bytes:
        calls.append(path)
        if path.startswith("/submissions/"):
            return _SUBMISSIONS
        return document

    return fetch


# --- configuration ---------------------------------------------------------


def test_live_fetch_requires_explicit_authorization(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="requires explicit authorization"):
        subject.DelistingPipelineConfig(
            user_agent=_UA, output_root=tmp_path, mode="live_fetch"
        )


def test_contact_information_is_mandatory(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="contact information"):
        subject.DelistingPipelineConfig(user_agent="bot", output_root=tmp_path)


def test_request_interval_cannot_breach_sec_fair_access(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="fair access"):
        subject.DelistingPipelineConfig(
            user_agent=_UA, output_root=tmp_path, request_interval_seconds=0.001
        )


def test_quarter_range_is_inclusive_and_ordered() -> None:
    assert subject.quarters_in_range((2023, 3), (2024, 2)) == (
        (2023, 3),
        (2023, 4),
        (2024, 1),
        (2024, 2),
    )
    assert subject.quarters_in_range((2023, 1), (2023, 1)) == ((2023, 1),)


def test_reversed_or_invalid_quarter_ranges_are_refused() -> None:
    with pytest.raises(ValidationError, match="must not follow"):
        subject.quarters_in_range((2024, 1), (2023, 1))
    with pytest.raises(ValidationError, match="quarter must be 1-4"):
        subject.quarters_in_range((2023, 5), (2024, 1))


def test_dry_run_plans_requests_without_touching_the_network(tmp_path: Path) -> None:
    def explode(*args: object, **kwargs: object) -> bytes:
        raise AssertionError("the network must not be touched")

    summary = subject.run_stage_a(
        _config(tmp_path, mode="dry_run", live_fetch_authorized=False),
        http_get=explode,
    )

    assert summary["network_access_attempted"] is False
    assert summary["quarters_to_fetch"] == 2
    assert summary["planned_requests"] == [
        "https://www.sec.gov/Archives/edgar/full-index/2023/QTR2/form.idx",
        "https://www.sec.gov/Archives/edgar/full-index/2023/QTR3/form.idx",
    ]


# --- stage A ---------------------------------------------------------------


def test_stage_a_records_only_delisting_forms(tmp_path: Path) -> None:
    calls: list[str] = []

    summary = subject.run_stage_a(_config(tmp_path), http_get=_index_fetcher(calls))

    assert len(calls) == 2
    assert summary["delisting_filings_written"] == 4
    rows = [
        json.loads(line)
        for line in (tmp_path / "stage_a_filings.jsonl").read_text().splitlines()
    ]
    assert {row["form_type"] for row in rows} == {"25", "25-NSE"}
    assert "STILL LISTED INC" not in {row["company"] for row in rows}


def test_stage_a_resumes_without_refetching_recorded_quarters(tmp_path: Path) -> None:
    first: list[str] = []
    subject.run_stage_a(_config(tmp_path), http_get=_index_fetcher(first))

    second: list[str] = []
    summary = subject.run_stage_a(_config(tmp_path), http_get=_index_fetcher(second))

    assert len(first) == 2
    assert second == []
    assert summary["quarters_fetched"] == 0


def test_stage_a_hashes_each_payload_but_does_not_retain_it(tmp_path: Path) -> None:
    subject.run_stage_a(_config(tmp_path), http_get=_index_fetcher([]))

    quarters = [
        json.loads(line)
        for line in (tmp_path / "stage_a_quarters.jsonl").read_text().splitlines()
    ]
    assert len(quarters) == 2
    for row in quarters:
        assert len(row["sha256"]) == 64
        assert row["byte_count"] > 0
        assert row["raw_response_retained"] is False
    # 50 MB of index per quarter is never written to disk.
    assert list(tmp_path.glob("*.bin")) == []


def test_a_failing_quarter_is_reported_and_does_not_stop_the_run(tmp_path: Path) -> None:
    def flaky(host: str, path: str, user_agent: str) -> bytes:
        if "QTR2" in path:
            raise OSError("connection reset")
        return _INDEX_2023Q3.encode("latin-1")

    summary = subject.run_stage_a(_config(tmp_path), http_get=flaky)

    assert summary["quarters_failed"] == 1
    assert summary["quarters_fetched"] == 1
    # The failed quarter is not marked complete, so a rerun retries it.
    recorded = [
        json.loads(line)
        for line in (tmp_path / "stage_a_quarters.jsonl").read_text().splitlines()
    ]
    assert [(row["year"], row["quarter"]) for row in recorded] == [(2023, 3)]


def test_repeated_index_rows_are_deduplicated_on_load(tmp_path: Path) -> None:
    subject.run_stage_a(_config(tmp_path), http_get=_index_fetcher([]))
    # Simulate a quarter refetched after an interruption.
    existing = (tmp_path / "stage_a_filings.jsonl").read_text()
    (tmp_path / "stage_a_filings.jsonl").write_text(existing + existing)

    filings = subject.load_stage_a_filings(tmp_path)

    assert len(filings) == 4


# --- stage B ---------------------------------------------------------------


def test_stage_b_resolves_symbols_wrapped_in_presentation_markup(
    tmp_path: Path,
) -> None:
    subject.run_stage_a(_config(tmp_path), http_get=_index_fetcher([]))
    calls: list[str] = []

    summary = subject.run_stage_b(
        _config(tmp_path, resolve_from=date(2019, 1, 1)),
        http_get=_resolution_fetcher(calls),
    )

    rows = [
        json.loads(line)
        for line in (tmp_path / "stage_b_resolutions.jsonl").read_text().splitlines()
    ]
    svb = next(row for row in rows if row["cik"] == "0000719739")
    assert svb["symbols"] == ["SIVB", "SIVBP"]
    assert svb["exchange"] == "NASDAQ"
    assert svb["outcome"] == "resolved"
    assert summary["outcomes"]["resolved"] >= 1


def test_two_form_25_filings_days_apart_are_one_delisting_episode(
    tmp_path: Path,
) -> None:
    subject.run_stage_a(_config(tmp_path), http_get=_index_fetcher([]))

    subject.run_stage_b(
        _config(tmp_path, resolve_from=date(2019, 1, 1)),
        http_get=_resolution_fetcher([]),
    )

    rows = [
        json.loads(line)
        for line in (tmp_path / "stage_b_resolutions.jsonl").read_text().splitlines()
    ]
    svb = [row for row in rows if row["cik"] == "0000719739"]
    assert len(svb) == 1
    # The earliest filing bounds the episode; the later one is recorded, not lost.
    assert svb[0]["delisted_on"] == "2023-05-02"
    assert svb[0]["last_filed_on"] == "2023-05-04"
    assert svb[0]["delisting_filing_count"] == 2


def test_source_filing_is_never_one_filed_after_the_delisting(tmp_path: Path) -> None:
    subject.run_stage_a(_config(tmp_path), http_get=_index_fetcher([]))
    calls: list[str] = []

    subject.run_stage_b(
        _config(tmp_path, resolve_from=date(2019, 1, 1)),
        http_get=_resolution_fetcher(calls),
    )

    rows = [
        json.loads(line)
        for line in (tmp_path / "stage_b_resolutions.jsonl").read_text().splitlines()
    ]
    svb = next(row for row in rows if row["cik"] == "0000719739")
    assert svb["source_filed"] == "2023-02-24"
    # The 2024 successor filing is in the window and must not be fetched.
    assert not any("successor-20240630" in path for path in calls)


def test_a_filing_without_cover_page_tags_is_recorded_as_such(tmp_path: Path) -> None:
    subject.run_stage_a(_config(tmp_path), http_get=_index_fetcher([]))

    subject.run_stage_b(
        _config(tmp_path, resolve_from=date(2019, 1, 1)),
        http_get=_resolution_fetcher([], document=_UNTAGGED_DOCUMENT),
    )

    rows = [
        json.loads(line)
        for line in (tmp_path / "stage_b_resolutions.jsonl").read_text().splitlines()
    ]
    assert {row["outcome"] for row in rows} == {"no_tag_in_source_filing"}
    assert all(row["ticker_recoverable"] is False for row in rows)
    # An absent symbol is never inferred from the document filename.
    assert all(row["symbols"] == [] for row in rows)


def test_a_truncated_submissions_window_is_not_reported_as_no_report(
    tmp_path: Path,
) -> None:
    """EDGAR pages filings beyond a thousand; that is not the same as absence."""

    subject.run_stage_a(_config(tmp_path), http_get=_index_fetcher([]))
    truncated = json.dumps(
        {
            "entityType": "operating",
            "filings": {
                "recent": {
                    "form": ["10-Q"],
                    "filingDate": ["2025-08-01"],
                    "accessionNumber": ["0000719739-25-000001"],
                    "primaryDocument": ["late.htm"],
                }
            },
        }
    ).encode()

    def fetch(host: str, path: str, user_agent: str) -> bytes:
        if path.startswith("/submissions/"):
            return truncated
        raise AssertionError("no document should be fetched")

    subject.run_stage_b(
        _config(tmp_path, resolve_from=date(2019, 1, 1)), http_get=fetch
    )

    rows = [
        json.loads(line)
        for line in (tmp_path / "stage_b_resolutions.jsonl").read_text().splitlines()
    ]
    assert {row["outcome"] for row in rows} == {"submissions_window_insufficient"}


def test_a_source_filing_with_no_primary_document_costs_no_request(
    tmp_path: Path,
) -> None:
    subject.run_stage_a(_config(tmp_path), http_get=_index_fetcher([]))
    no_document = json.dumps(
        {
            "entityType": "operating",
            "filings": {
                "recent": {
                    "form": ["10-K"],
                    "filingDate": ["2020-02-24"],
                    "accessionNumber": ["0000719739-20-000001"],
                    "primaryDocument": [""],
                }
            },
        }
    ).encode()

    def fetch(host: str, path: str, user_agent: str) -> bytes:
        if path.startswith("/submissions/"):
            return no_document
        raise AssertionError("no document should be fetched")

    subject.run_stage_b(
        _config(tmp_path, resolve_from=date(2019, 1, 1)), http_get=fetch
    )

    rows = [
        json.loads(line)
        for line in (tmp_path / "stage_b_resolutions.jsonl").read_text().splitlines()
    ]
    assert {row["outcome"] for row in rows} == {
        "source_filing_has_no_primary_document"
    }


def test_pre_tagging_era_episodes_are_recorded_but_never_fetched(
    tmp_path: Path,
) -> None:
    index = (
        "Form Type   Company Name          CIK        Date Filed  File Name\n"
        "-----------------------------------------------------------------\n"
        "25          OLD DELISTING CO      333333     2008-06-02  edgar/data/333333/x.txt\n"
    )

    def fetch_index(host: str, path: str, user_agent: str) -> bytes:
        return index.encode("latin-1")

    config = _config(tmp_path, start_quarter=(2008, 2), end_quarter=(2008, 2))
    subject.run_stage_a(config, http_get=fetch_index)

    def explode(*args: object, **kwargs: object) -> bytes:
        raise AssertionError("pre-tagging-era episodes must not be fetched")

    summary = subject.run_stage_b(config, http_get=explode)

    assert summary["episodes_total"] == 1
    assert summary["episodes_in_tagging_era"] == 0
    assert summary["episodes_attempted"] == 0


def test_stage_b_resumes_and_respects_its_resolution_cap(tmp_path: Path) -> None:
    subject.run_stage_a(_config(tmp_path), http_get=_index_fetcher([]))

    capped = [
        subject.run_stage_b(
            _config(tmp_path, resolve_from=date(2019, 1, 1), max_resolutions=1),
            http_get=_resolution_fetcher([]),
        )
        for _ in range(2)
    ]
    # Three episodes exist, so one remains for an uncapped run.
    remainder = subject.run_stage_b(
        _config(tmp_path, resolve_from=date(2019, 1, 1)),
        http_get=_resolution_fetcher([]),
    )
    exhausted = subject.run_stage_b(
        _config(tmp_path, resolve_from=date(2019, 1, 1)),
        http_get=_resolution_fetcher([]),
    )

    assert [run["episodes_attempted"] for run in capped] == [1, 1]
    assert remainder["episodes_attempted"] == 1
    assert exhausted["episodes_attempted"] == 0
    # Four runs, three episodes, three rows: nothing resolved twice.
    rows = (tmp_path / "stage_b_resolutions.jsonl").read_text().splitlines()
    assert len(rows) == 3


def test_a_failed_document_fetch_does_not_abort_the_remaining_episodes(
    tmp_path: Path,
) -> None:
    subject.run_stage_a(_config(tmp_path), http_get=_index_fetcher([]))

    def flaky(host: str, path: str, user_agent: str) -> bytes:
        if path.startswith("/submissions/"):
            return _SUBMISSIONS
        raise OSError("connection reset")

    summary = subject.run_stage_b(
        _config(tmp_path, resolve_from=date(2019, 1, 1)), http_get=flaky
    )

    assert summary["outcomes"] == {"document_unavailable": 3}
    assert summary["episodes_attempted"] == 3


def test_every_request_is_recorded_with_its_hash_and_allowlist_match(
    tmp_path: Path,
) -> None:
    subject.run_stage_a(_config(tmp_path), http_get=_index_fetcher([]))
    subject.run_stage_b(
        _config(tmp_path, resolve_from=date(2019, 1, 1)),
        http_get=_resolution_fetcher([]),
    )

    manifest = [
        json.loads(line)
        for line in (tmp_path / "stage_b_manifest.jsonl").read_text().splitlines()
    ]
    assert manifest
    for row in manifest:
        assert row["method"] == "GET"
        assert row["destination_host"] in ("www.sec.gov", "data.sec.gov")
        assert row["destination_allowlist_match"] is True
        assert row["credentials_used"] is False
        assert row["authenticated"] is False
        assert len(row["sha256"]) == 64
        assert row["raw_response_retained"] is False


# --- reporting -------------------------------------------------------------


def test_summary_reports_recovery_with_strata(tmp_path: Path) -> None:
    subject.run_stage_a(_config(tmp_path), http_get=_index_fetcher([]))
    subject.run_stage_b(
        _config(tmp_path, resolve_from=date(2019, 1, 1)),
        http_get=_resolution_fetcher([]),
    )

    summary = subject.summarize_stage_b(tmp_path)

    assert summary["total"] == 3
    assert summary["resolved"] == 3
    assert summary["recovery_rate"] == 1.0
    assert summary["distinct_symbols"] == 2
    assert summary["by"]["source_form"]["10-K"]["total"] == 3
    assert summary["by"]["outcome"]["resolved"]["total"] == 3
    # The tagging boundary falls on the source filing, not the delisting.
    assert summary["by"]["source_filed_year"]["2023"]["total"] == 3


def test_recovery_is_stratified_by_the_source_filing_year(tmp_path: Path) -> None:
    """A 2019 delisting is described by a 2018 report that predates tagging."""

    subject.run_stage_a(_config(tmp_path), http_get=_index_fetcher([]))
    subject.run_stage_b(
        _config(tmp_path, resolve_from=date(2019, 1, 1)),
        http_get=_resolution_fetcher([], document=_UNTAGGED_DOCUMENT),
    )

    summary = subject.summarize_stage_b(tmp_path)

    by_year = summary["by"]["source_filed_year"]
    assert by_year["2023"] == {"total": 3, "resolved": 0, "recovery_rate": 0.0}


def test_summary_of_an_unstarted_run_is_empty_rather_than_an_error(
    tmp_path: Path,
) -> None:
    assert subject.summarize_stage_b(tmp_path)["total"] == 0


# --- the exported registry -------------------------------------------------


def _export(tmp_path: Path, **stage_b: object) -> list[dict[str, object]]:
    subject.run_stage_a(_config(tmp_path), http_get=_index_fetcher([]))
    subject.run_stage_b(
        _config(tmp_path, resolve_from=date(2019, 1, 1)),
        http_get=_resolution_fetcher([], **stage_b),  # type: ignore[arg-type]
    )
    subject.export_registry(tmp_path)
    return [
        json.loads(line)
        for line in (tmp_path / "delisting_registry.jsonl").read_text().splitlines()
    ]


def test_exported_records_admit_prices_only_through_the_delisting(
    tmp_path: Path,
) -> None:
    records = _export(tmp_path)

    svb = next(row for row in records if row["cik"] == "0000719739")
    window = svb["price_admission_window"]
    assert window["admit_through"] == "2023-05-02"
    assert window["admit_after"] is None
    assert window["reuse_risk_after_delisting"] is True
    assert window["symbols"] == ["SIVB", "SIVBP"]


def test_unnamed_delistings_stay_in_the_registry(tmp_path: Path) -> None:
    """Dropping them would rebuild the survivorship bias this reduces."""

    records = _export(tmp_path, document=_UNTAGGED_DOCUMENT)

    assert len(records) == 3
    assert all(row["ticker_recoverable"] is False for row in records)
    assert all(row["symbol_source"] == "unrecoverable" for row in records)
    assert all(row["outcome"] == "no_tag_in_source_filing" for row in records)


def test_pre_tagging_era_episodes_are_exported_as_not_attempted(
    tmp_path: Path,
) -> None:
    index = (
        "Form Type   Company Name          CIK        Date Filed  File Name\n"
        "-----------------------------------------------------------------\n"
        "25          OLD DELISTING CO      333333     2008-06-02  edgar/data/333333/x.txt\n"
    )
    config = _config(tmp_path, start_quarter=(2008, 2), end_quarter=(2008, 2))
    subject.run_stage_a(config, http_get=lambda *_: index.encode("latin-1"))

    subject.export_registry(tmp_path)

    records = [
        json.loads(line)
        for line in (tmp_path / "delisting_registry.jsonl").read_text().splitlines()
    ]
    assert len(records) == 1
    assert records[0]["outcome"] == "not_attempted"
    assert records[0]["ticker_recoverable"] is False


def test_export_is_idempotent_rather_than_appending(tmp_path: Path) -> None:
    first = _export(tmp_path)
    subject.export_registry(tmp_path)
    second = [
        json.loads(line)
        for line in (tmp_path / "delisting_registry.jsonl").read_text().splitlines()
    ]

    assert first == second


# --- safety ----------------------------------------------------------------


def test_pipeline_has_no_credential_reading_code_path() -> None:
    import ast

    tree = ast.parse(Path(subject.__file__).read_text(encoding="utf-8"))
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


def test_pipeline_reaches_the_network_only_through_the_audited_adapter() -> None:
    import ast

    tree = ast.parse(Path(subject.__file__).read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }

    for module in ("http", "socket", "urllib", "requests", "httpx", "ssl"):
        assert module not in imported, f"pipeline opens its own socket via {module}"
