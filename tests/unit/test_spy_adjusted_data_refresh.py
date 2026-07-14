from __future__ import annotations

import ast
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
from typing import Mapping

import pytest

from algotrader.errors import ValidationError
from algotrader.execution import etf_sma_adjusted_spy_data_refresh as refresh
from algotrader.execution.etf_sma_adjusted_spy_data_refresh import (
    SPYAdjustedDataRefreshConfig,
    run_spy_adjusted_data_refresh,
)


EXPECTED_DATE = "2026-06-22"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REFRESH_SCRIPT = PROJECT_ROOT / "scripts" / "refresh_spy_adjusted_data.ps1"


def test_refresh_script_contract_defaults_to_dry_run_and_requires_live_flag() -> None:
    script = REFRESH_SCRIPT.read_text(encoding="utf-8")

    assert "[ValidateSet(\"offline_fixture\", \"dry_run\", \"live_market_data_fetch\")]" in script
    assert "[ValidateSet(\"SPY\", \"QQQ\", \"IWM\", \"TLT\", \"GLD\")]" in script
    assert "[string]$Mode = \"dry_run\"" in script
    assert "[switch]$LiveMarketDataFetchAuthorized" in script
    assert "[string]$StartDate = \"auto\"" in script
    assert "[ValidateRange(1, 31)]" in script
    assert "[int]$RevisionLookbackDays = 10" in script
    assert "[string]$DotenvPath = \".env\"" in script
    assert "--live-market-data-fetch-authorized" in script
    assert "--revision-lookback-days" in script
    assert "--symbol" in script
    assert "--dotenv-path" in script
    assert "if ($LiveMarketDataFetchAuthorized)" in script
    assert "$AppProfile -eq \"live\"" in script
    assert "TIINGO_API_KEY" in script
    assert "ALPACA_API_KEY" not in script
    assert "does not read broker state" in script


def test_dry_run_builds_tiingo_request_without_network(tmp_path: Path) -> None:
    output_csv = tmp_path / "operator_input.csv"
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"

    payload = run_spy_adjusted_data_refresh(
        SPYAdjustedDataRefreshConfig(
            provider="tiingo",
            expected_latest_bar_date=EXPECTED_DATE,
            output_csv=output_csv,
            canonical_csv=canonical_csv,
            run_log=run_log,
            mode="dry_run",
        ),
        token_lookup=_raise_token_lookup,
        http_get=_raise_http_get,
    )

    assert payload["refresh_state"] == "dry_run_refresh_plan_built"
    assert payload["dry_run_only"] is True
    assert payload["network_access_attempted"] is False
    assert payload["market_data_token_access_attempted"] is False
    assert payload["request_start_date"] == "1993-01-29"
    assert "api.tiingo.com/tiingo/daily/SPY/prices" in payload["provider_request"]["url"]
    assert "endDate=2026-06-22" in payload["provider_request"]["url"]
    assert "TIINGO_API_KEY" not in payload["provider_request"]["url"]
    assert not output_csv.exists()
    assert not canonical_csv.exists()
    assert run_log.exists()


def test_dry_run_builds_tiingo_request_for_approved_non_spy_without_network(
    tmp_path: Path,
) -> None:
    payload = run_spy_adjusted_data_refresh(
        SPYAdjustedDataRefreshConfig(
            provider="tiingo",
            expected_latest_bar_date=EXPECTED_DATE,
            output_csv=tmp_path / "operator_input.csv",
            canonical_csv=tmp_path / "canonical.csv",
            run_log=tmp_path / "manifest.jsonl",
            symbol="QQQ",
            mode="dry_run",
        ),
        token_lookup=_raise_token_lookup,
        http_get=_raise_http_get,
    )

    assert payload["refresh_state"] == "dry_run_refresh_plan_built"
    assert payload["symbol"] == "QQQ"
    assert "api.tiingo.com/tiingo/daily/QQQ/prices" in payload["provider_request"]["url"]
    assert payload["network_access_attempted"] is False
    assert payload["market_data_token_access_attempted"] is False


def test_offline_fixture_refresh_normalizes_provider_data_into_canonical_schema(
    tmp_path: Path,
) -> None:
    fixture_csv = tmp_path / "tiingo_fixture.csv"
    output_csv = tmp_path / "operator_input.csv"
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"
    _write_canonical(canonical_csv, latest_date="2026-06-18")
    _write_provider_csv(
        fixture_csv,
        [
            {"date": "2026-06-19T00:00:00.000Z", "adjClose": "550.50"},
            {"date": "2026-06-22T00:00:00.000Z", "adjClose": "555.25"},
        ],
    )

    payload = run_spy_adjusted_data_refresh(
        _offline_config(fixture_csv, output_csv, canonical_csv, run_log),
        http_get=_raise_http_get,
    )

    assert payload["refresh_state"] == "accepted_adjusted_spy_data_refresh"
    assert payload["source_row_count"] == 2
    assert payload["accepted_row_count"] == 3
    assert payload["latest_provider_bar_date"] == EXPECTED_DATE
    assert payload["current_canonical_latest_bar_date"] == "2026-06-18"
    assert payload["canonical_intake_performed"] is True
    rows = output_csv.read_text(encoding="utf-8").splitlines()
    assert rows[0] == "symbol,date,open,high,low,close,adjusted_close,volume"
    assert rows[1] == "SPY,2026-06-18,500,501,499,500,500,1000"
    assert rows[-1] == "SPY,2026-06-22,551,556,550,555,555.25,1000"
    assert canonical_csv.read_text(encoding="utf-8") == output_csv.read_text(
        encoding="utf-8"
    )
    assert payload["canonical_csv_sha256"]


def test_offline_fixture_refresh_normalizes_approved_non_spy_symbol(
    tmp_path: Path,
) -> None:
    fixture_csv = tmp_path / "tiingo_fixture.csv"
    output_csv = tmp_path / "operator_input.csv"
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"
    _write_canonical(canonical_csv, latest_date="2026-06-18", symbol="QQQ")
    _write_provider_csv(
        fixture_csv,
        [
            {"date": "2026-06-19T00:00:00.000Z", "adjClose": "550.50"},
            {"date": "2026-06-22T00:00:00.000Z", "adjClose": "555.25"},
        ],
    )

    payload = run_spy_adjusted_data_refresh(
        SPYAdjustedDataRefreshConfig(
            provider="tiingo",
            expected_latest_bar_date=EXPECTED_DATE,
            output_csv=output_csv,
            canonical_csv=canonical_csv,
            run_log=run_log,
            symbol="QQQ",
            mode="offline_fixture",
            fixture_input_path=fixture_csv,
        ),
        token_lookup=_raise_token_lookup,
        http_get=_raise_http_get,
    )

    assert payload["refresh_state"] == "accepted_adjusted_spy_data_refresh"
    assert payload["symbol"] == "QQQ"
    assert payload["existing_intake_manifest"]["symbol"] == "QQQ"
    rows = output_csv.read_text(encoding="utf-8").splitlines()
    assert rows[1].startswith("QQQ,2026-06-18,")
    assert rows[-1].startswith("QQQ,2026-06-22,")


def test_duplicate_dates_rejected(tmp_path: Path) -> None:
    payload, output_csv = _run_invalid_fixture(
        tmp_path,
        [
            {"date": EXPECTED_DATE, "adjClose": "555.25"},
            {"date": EXPECTED_DATE, "adjClose": "555.30"},
        ],
    )

    assert payload["refresh_state"] == "blocked_invalid_provider_adjusted_bars"
    assert payload["refresh_blockers"] == ["duplicate_dates"]
    assert not output_csv.exists()


def test_missing_adjusted_close_rejected(tmp_path: Path) -> None:
    payload, output_csv = _run_invalid_fixture(
        tmp_path,
        [{"date": EXPECTED_DATE, "adjClose": ""}],
    )

    assert payload["refresh_state"] == "blocked_invalid_provider_adjusted_bars"
    assert payload["refresh_blockers"] == ["missing_adjusted_close"]
    assert not output_csv.exists()


def test_nonpositive_adjusted_close_rejected(tmp_path: Path) -> None:
    payload, output_csv = _run_invalid_fixture(
        tmp_path,
        [{"date": EXPECTED_DATE, "adjClose": "0"}],
    )

    assert payload["refresh_state"] == "blocked_invalid_provider_adjusted_bars"
    assert payload["refresh_blockers"] == ["nonpositive_adjusted_close"]
    assert not output_csv.exists()


def test_unsorted_input_sorted_ascending(tmp_path: Path) -> None:
    fixture_csv = tmp_path / "tiingo_fixture.csv"
    output_csv = tmp_path / "operator_input.csv"
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"
    _write_canonical(canonical_csv, latest_date="2026-06-18")
    _write_provider_csv(
        fixture_csv,
        [
            {"date": EXPECTED_DATE, "adjClose": "555.25"},
            {"date": "2026-06-19", "adjClose": "550.50"},
        ],
    )

    payload = run_spy_adjusted_data_refresh(
        _offline_config(fixture_csv, output_csv, canonical_csv, run_log),
        token_lookup=_raise_token_lookup,
        http_get=_raise_http_get,
    )

    assert payload["refresh_state"] == "accepted_adjusted_spy_data_refresh"
    dates = [
        line.split(",")[1]
        for line in output_csv.read_text(encoding="utf-8").splitlines()[1:]
    ]
    assert dates == ["2026-06-18", "2026-06-19", "2026-06-22"]


def test_provider_latest_date_cannot_precede_existing_canonical(
    tmp_path: Path,
) -> None:
    fixture_csv = tmp_path / "tiingo_fixture.csv"
    output_csv = tmp_path / "operator_input.csv"
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"
    _write_canonical(canonical_csv, latest_date=EXPECTED_DATE)
    before = canonical_csv.read_text(encoding="utf-8")
    _write_provider_csv(fixture_csv, [{"date": "2026-06-19", "adjClose": "550.25"}])

    payload = run_spy_adjusted_data_refresh(
        SPYAdjustedDataRefreshConfig(
            provider="tiingo",
            expected_latest_bar_date="2026-06-19",
            output_csv=output_csv,
            canonical_csv=canonical_csv,
            run_log=run_log,
            mode="offline_fixture",
            fixture_input_path=fixture_csv,
        ),
        http_get=_raise_http_get,
    )

    assert payload["refresh_state"] == "blocked_latest_bar_date_precedes_canonical"
    assert payload["refresh_blockers"] == ["latest_bar_date_precedes_canonical"]
    assert canonical_csv.read_text(encoding="utf-8") == before
    assert not output_csv.exists()


def test_expected_latest_bar_date_mismatch_fails_deterministically(
    tmp_path: Path,
) -> None:
    fixture_csv = tmp_path / "tiingo_fixture.csv"
    output_csv = tmp_path / "operator_input.csv"
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"
    _write_canonical(canonical_csv, latest_date="2026-06-18")
    _write_provider_csv(fixture_csv, [{"date": "2026-06-21", "adjClose": "554.25"}])

    payload = run_spy_adjusted_data_refresh(
        _offline_config(fixture_csv, output_csv, canonical_csv, run_log),
        http_get=_raise_http_get,
    )

    assert payload["refresh_state"] == "blocked_expected_latest_bar_date_mismatch"
    assert payload["refresh_blockers"] == ["expected_latest_bar_date_mismatch"]
    assert not output_csv.exists()


def test_missing_token_in_live_mode_produces_token_required_gate(
    tmp_path: Path,
) -> None:
    payload = run_spy_adjusted_data_refresh(
        SPYAdjustedDataRefreshConfig(
            provider="tiingo",
            expected_latest_bar_date=EXPECTED_DATE,
            output_csv=tmp_path / "operator_input.csv",
            canonical_csv=tmp_path / "canonical.csv",
            run_log=tmp_path / "manifest.jsonl",
            mode="live_market_data_fetch",
            live_fetch_authorized=True,
        ),
        token_lookup=lambda name: None,
        http_get=_raise_http_get,
    )

    assert payload["refresh_state"] == "blocked_market_data_refresh_token_required"
    assert payload["refresh_blockers"] == ["market_data_refresh_token_required"]
    assert payload["market_data_token_access_attempted"] is True
    assert payload["network_access_attempted"] is False


def test_live_mode_cannot_run_without_explicit_authorization_flag(
    tmp_path: Path,
) -> None:
    payload = run_spy_adjusted_data_refresh(
        SPYAdjustedDataRefreshConfig(
            provider="tiingo",
            expected_latest_bar_date=EXPECTED_DATE,
            output_csv=tmp_path / "operator_input.csv",
            canonical_csv=tmp_path / "canonical.csv",
            run_log=tmp_path / "manifest.jsonl",
            mode="live_market_data_fetch",
            live_fetch_authorized=False,
        ),
        token_lookup=_raise_token_lookup,
        http_get=_raise_http_get,
    )

    assert payload["refresh_state"] == "blocked_live_market_data_fetch_not_authorized"
    assert payload["refresh_blockers"] == ["live_market_data_fetch_not_authorized"]
    assert payload["market_data_token_access_attempted"] is False
    assert payload["network_access_attempted"] is False


def test_default_pytest_paths_do_not_load_dotenv(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        refresh,
        "load_tiingo_api_key_from_dotenv",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("dotenv loaded")
        ),
    )
    fixture_csv = tmp_path / "tiingo_fixture.csv"
    canonical_csv = tmp_path / "canonical.csv"
    _write_canonical(canonical_csv, latest_date="2026-06-18")
    _write_provider_csv(fixture_csv, [{"date": EXPECTED_DATE, "adjClose": "555.25"}])

    dry_payload = run_spy_adjusted_data_refresh(
        SPYAdjustedDataRefreshConfig(
            provider="tiingo",
            expected_latest_bar_date=EXPECTED_DATE,
            output_csv=tmp_path / "dry.csv",
            canonical_csv=tmp_path / "dry_canonical.csv",
            run_log=tmp_path / "dry.jsonl",
            mode="dry_run",
        ),
        token_lookup=_raise_token_lookup,
        http_get=_raise_http_get,
    )
    fixture_payload = run_spy_adjusted_data_refresh(
        _offline_config(
            fixture_csv,
            tmp_path / "candidate.csv",
            canonical_csv,
            tmp_path / "fixture.jsonl",
        ),
        token_lookup=_raise_token_lookup,
        http_get=_raise_http_get,
    )

    assert dry_payload["refresh_state"] == "dry_run_refresh_plan_built"
    assert fixture_payload["refresh_state"] == "accepted_adjusted_spy_data_refresh"


def test_scoped_dotenv_loader_retrieves_only_tiingo_key(
    tmp_path: Path,
    monkeypatch,
) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "ALPACA_API_KEY=broker-key\n"
        "TIINGO_API_KEY=tiingo-token\n"
        "APCA_API_SECRET_KEY=broker-secret\n",
        encoding="utf-8",
    )
    for name in (
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "TIINGO_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    assert refresh.load_tiingo_api_key_from_dotenv(dotenv_path) == "tiingo-token"
    assert os.environ.get("TIINGO_API_KEY") is None
    assert os.environ.get("ALPACA_API_KEY") is None
    assert os.environ.get("APCA_API_SECRET_KEY") is None


def test_loaded_broker_credential_coexists_with_tiingo_only_fetch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("ALPACA_API_KEY", "broker-key-must-not-be-read")
    canonical_csv = tmp_path / "canonical.csv"
    _write_canonical(canonical_csv, latest_date="2026-06-18")

    payload = run_spy_adjusted_data_refresh(
        _live_config(tmp_path, canonical_csv),
        token_lookup=lambda name: "tiingo-token",
        http_get=_valid_same_day_http_get,
    )

    assert payload["refresh_state"] == "accepted_adjusted_spy_data_refresh"
    assert payload["network_access_attempted"] is True
    assert payload["broker_credential_lookup_attempted"] is False
    rendered = refresh.render_spy_adjusted_data_refresh_json(payload)
    assert "broker-key-must-not-be-read" not in rendered


def test_app_profile_paper_allows_tiingo_only_fetch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_PROFILE", "paper")
    canonical_csv = tmp_path / "canonical.csv"
    _write_canonical(canonical_csv, latest_date="2026-06-18")

    payload = run_spy_adjusted_data_refresh(
        _live_config(tmp_path, canonical_csv),
        token_lookup=lambda name: "tiingo-token",
        http_get=_valid_same_day_http_get,
    )

    assert payload["refresh_state"] == "accepted_adjusted_spy_data_refresh"
    assert payload["network_access_attempted"] is True
    assert payload["broker_access_attempted"] is False
    assert payload["broker_mutation_attempted"] is False


def test_app_profile_live_blocks_market_data_fetch_before_token_lookup(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_PROFILE", "live")

    payload = run_spy_adjusted_data_refresh(
        _live_config(tmp_path, tmp_path / "canonical.csv"),
        token_lookup=_raise_token_lookup,
        http_get=_raise_http_get,
    )

    assert payload["refresh_state"] == "blocked_live_market_data_fetch_preflight_failed"
    assert payload["refresh_blockers"] == ["APP_PROFILE_is_live"]
    assert payload["market_data_token_access_attempted"] is False
    assert payload["network_access_attempted"] is False


def test_current_canonical_runs_bounded_revision_check_and_is_idempotent(
    tmp_path: Path,
) -> None:
    canonical_csv = tmp_path / "canonical.csv"
    _write_canonical(canonical_csv, latest_date=EXPECTED_DATE)
    before = canonical_csv.read_bytes()

    payload = run_spy_adjusted_data_refresh(
        _live_config(tmp_path, canonical_csv),
        token_lookup=lambda name: "tiingo-token",
        http_get=_valid_same_day_http_get,
    )

    assert payload["refresh_state"] == "accepted_adjusted_spy_data_refresh"
    assert payload["request_start_date"] == "2026-06-12"
    assert payload["revision_lookback_days"] == 10
    assert payload["revision_check_performed"] is True
    assert payload["revision_outcome"] == "revision_window_checked_no_change"
    assert payload["canonical_changed"] is False
    assert payload["overlap_row_count"] == 1
    assert payload["revised_row_count"] == 0
    assert payload["unchanged_overlap_row_count"] == 1
    assert payload["network_access_attempted"] is True
    assert payload["market_data_token_access_attempted"] is True
    assert canonical_csv.read_bytes() == before


def test_http_failure_preserves_existing_canonical(tmp_path: Path) -> None:
    canonical_csv = tmp_path / "canonical.csv"
    _write_canonical(canonical_csv, latest_date="2026-06-18")
    before = canonical_csv.read_bytes()

    def fake_http_get(url: str, headers: Mapping[str, str]) -> bytes:
        raise refresh.MarketDataFetchError("provider_http_status_failure")

    payload = run_spy_adjusted_data_refresh(
        SPYAdjustedDataRefreshConfig(
            provider="tiingo",
            expected_latest_bar_date=EXPECTED_DATE,
            output_csv=tmp_path / "operator_input.csv",
            canonical_csv=canonical_csv,
            run_log=tmp_path / "manifest.jsonl",
            mode="live_market_data_fetch",
            live_fetch_authorized=True,
            raw_response_path=tmp_path / "raw_response.json",
        ),
        token_lookup=lambda name: "token",
        http_get=fake_http_get,
    )

    assert payload["refresh_state"] == "blocked_live_market_data_fetch_http_failed"
    assert payload["http_outcome_category"] == "provider_http_status_failure"
    assert payload["previous_canonical_preserved_on_failure"] is True
    assert canonical_csv.read_bytes() == before
    assert not (tmp_path / "operator_input.csv").exists()


def test_invalid_live_json_preserves_existing_canonical(tmp_path: Path) -> None:
    canonical_csv = tmp_path / "canonical.csv"
    _write_canonical(canonical_csv, latest_date="2026-06-18")
    before = canonical_csv.read_bytes()

    payload = run_spy_adjusted_data_refresh(
        SPYAdjustedDataRefreshConfig(
            provider="tiingo",
            expected_latest_bar_date=EXPECTED_DATE,
            output_csv=tmp_path / "operator_input.csv",
            canonical_csv=canonical_csv,
            run_log=tmp_path / "manifest.jsonl",
            mode="live_market_data_fetch",
            live_fetch_authorized=True,
            raw_response_path=tmp_path / "raw_response.json",
        ),
        token_lookup=lambda name: "token",
        http_get=lambda url, headers: b"not-json",
    )

    assert payload["refresh_state"] == "blocked_invalid_provider_json_response"
    assert payload["previous_canonical_preserved_on_failure"] is True
    assert canonical_csv.read_bytes() == before
    assert not (tmp_path / "operator_input.csv").exists()


def test_invalid_live_data_preserves_existing_canonical(tmp_path: Path) -> None:
    canonical_csv = tmp_path / "canonical.csv"
    _write_canonical(canonical_csv, latest_date="2026-06-18")
    before = canonical_csv.read_bytes()

    payload = run_spy_adjusted_data_refresh(
        SPYAdjustedDataRefreshConfig(
            provider="tiingo",
            expected_latest_bar_date=EXPECTED_DATE,
            output_csv=tmp_path / "operator_input.csv",
            canonical_csv=canonical_csv,
            run_log=tmp_path / "manifest.jsonl",
            mode="live_market_data_fetch",
            live_fetch_authorized=True,
            raw_response_path=tmp_path / "raw_response.json",
        ),
        token_lookup=lambda name: "token",
        http_get=lambda url, headers: json.dumps(
            [{"date": EXPECTED_DATE, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]
        ).encode("utf-8"),
    )

    assert payload["refresh_state"] == "blocked_invalid_provider_adjusted_bars"
    assert payload["refresh_blockers"] == ["missing_adjusted_close"]
    assert payload["previous_canonical_preserved_on_failure"] is True
    assert canonical_csv.read_bytes() == before
    assert not (tmp_path / "operator_input.csv").exists()


def test_token_value_is_never_printed_or_written(tmp_path: Path) -> None:
    secret = "secret-tiingo-token-value"
    output_csv = tmp_path / "operator_input.csv"
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"
    raw_response = tmp_path / "raw_response.json"
    _write_canonical(canonical_csv, latest_date="2026-06-18")

    def fake_http_get(url: str, headers: Mapping[str, str]) -> bytes:
        assert headers == {"Authorization": f"Token {secret}"}
        assert secret not in url
        assert "token" not in url.lower()
        return json.dumps(
            [
                {
                    "date": f"{EXPECTED_DATE}T00:00:00.000Z",
                    "open": 551,
                    "high": 556,
                    "low": 550,
                    "close": 555,
                    "volume": 1000,
                    "adjClose": 555.25,
                }
            ]
        ).encode("utf-8")

    payload = run_spy_adjusted_data_refresh(
        SPYAdjustedDataRefreshConfig(
            provider="tiingo",
            expected_latest_bar_date=EXPECTED_DATE,
            output_csv=output_csv,
            canonical_csv=canonical_csv,
            run_log=run_log,
            mode="live_market_data_fetch",
            live_fetch_authorized=True,
            raw_response_path=raw_response,
        ),
        token_lookup=lambda name: secret,
        http_get=fake_http_get,
    )

    assert payload["refresh_state"] == "accepted_adjusted_spy_data_refresh"
    assert payload["source_row_count"] == 1
    assert payload["accepted_row_count"] == 2
    assert payload["market_data_token_loaded"] is True
    assert payload["token_available"] is True
    assert payload["canonical_intake_performed"] is True
    rendered = refresh.render_spy_adjusted_data_refresh_json(payload)
    for text in (
        rendered,
        refresh.render_spy_adjusted_data_refresh_text(payload),
        run_log.read_text(encoding="utf-8"),
        raw_response.read_text(encoding="utf-8"),
        output_csv.read_text(encoding="utf-8"),
        canonical_csv.read_text(encoding="utf-8"),
    ):
        assert secret not in text
    assert payload["provider_request"]["headers"] == {"Authorization": "Token <redacted>"}


def test_normal_pytest_paths_do_not_access_network(tmp_path: Path) -> None:
    fixture_csv = tmp_path / "tiingo_fixture.csv"
    _write_provider_csv(fixture_csv, [{"date": EXPECTED_DATE, "adjClose": "555.25"}])
    canonical_csv = tmp_path / "canonical.csv"
    _write_canonical(canonical_csv, latest_date="2026-06-18")

    dry_payload = run_spy_adjusted_data_refresh(
        SPYAdjustedDataRefreshConfig(
            provider="tiingo",
            expected_latest_bar_date=EXPECTED_DATE,
            output_csv=tmp_path / "dry_operator_input.csv",
            canonical_csv=tmp_path / "dry_canonical.csv",
            run_log=tmp_path / "dry_manifest.jsonl",
            mode="dry_run",
        ),
        http_get=_raise_http_get,
    )
    fixture_payload = run_spy_adjusted_data_refresh(
        _offline_config(
            fixture_csv,
            tmp_path / "operator_input.csv",
            canonical_csv,
            tmp_path / "manifest.jsonl",
        ),
        http_get=_raise_http_get,
    )

    assert dry_payload["network_access_attempted"] is False
    assert fixture_payload["network_access_attempted"] is False


def test_refresh_path_has_no_broker_sdk_import_or_broker_credentials() -> None:
    source = Path(refresh.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)

    forbidden_import_terms = ("alpaca", "broker_base", "alpaca_adapter", "alpaca_sdk")
    assert not any(
        term in module.lower()
        for module in imported_modules
        for term in forbidden_import_terms
    )
    assert "_BROKER_CREDENTIAL_ENV_VARS" not in source
    for credential_name in (
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
    ):
        assert credential_name not in source
    assert "token_env_var must be TIINGO_API_KEY" in source
    assert '_TIINGO_DESTINATION_HOST = "api.tiingo.com"' in source
    assert "_validated_tiingo_request_target" in source


def test_equal_latest_date_applies_revised_overlap_with_hash_evidence(
    tmp_path: Path,
) -> None:
    canonical_csv = tmp_path / "canonical.csv"
    canonical_csv.write_text(
        "symbol,date,open,high,low,close,adjusted_close,volume\n"
        "SPY,2026-06-19,490,491,489,490,490,900\n"
        "SPY,2026-06-22,500,501,499,500,500,1000\n",
        encoding="utf-8",
    )
    before_sha256 = refresh._sha256_file(canonical_csv)

    def revised_http_get(url: str, headers: Mapping[str, str]) -> bytes:
        assert "startDate=2026-06-12" in url
        assert headers == {"Authorization": "Token tiingo-token"}
        return json.dumps(
            [
                {
                    "date": "2026-06-19T00:00:00.000Z",
                    "open": 491,
                    "high": 492,
                    "low": 490,
                    "close": 491,
                    "volume": 950,
                    "adjClose": 491.25,
                },
                {
                    "date": "2026-06-22T00:00:00.000Z",
                    "open": 500,
                    "high": 501,
                    "low": 499,
                    "close": 500,
                    "volume": 1000,
                    "adjClose": 500,
                },
            ]
        ).encode("utf-8")

    payload = run_spy_adjusted_data_refresh(
        _live_config(tmp_path, canonical_csv),
        token_lookup=lambda name: "tiingo-token",
        http_get=revised_http_get,
    )

    assert payload["refresh_state"] == "accepted_adjusted_spy_data_refresh"
    assert payload["revision_outcome"] == "revisions_applied"
    assert payload["canonical_changed"] is True
    assert payload["overlap_row_count"] == 2
    assert payload["revised_row_count"] == 1
    assert payload["revised_dates"] == ["2026-06-19"]
    assert payload["new_row_count"] == 0
    assert payload["unchanged_overlap_row_count"] == 1
    assert payload["current_canonical_sha256"] == before_sha256
    assert payload["canonical_csv_sha256"] != before_sha256
    assert "2026-06-19,491,492,490,491,491.25,950" in canonical_csv.read_text(
        encoding="utf-8"
    )


def test_config_rejects_any_non_tiingo_token_variable(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="token_env_var must be TIINGO_API_KEY"):
        SPYAdjustedDataRefreshConfig(
            provider="tiingo",
            expected_latest_bar_date=EXPECTED_DATE,
            output_csv=tmp_path / "candidate.csv",
            canonical_csv=tmp_path / "canonical.csv",
            run_log=tmp_path / "manifest.jsonl",
            token_env_var="ALPACA_API_KEY",
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://api.tiingo.com/tiingo/daily/SPY/prices?startDate=2026-06-12&endDate=2026-06-22&format=json",
        "https://api.tiingo.com.evil/tiingo/daily/SPY/prices?startDate=2026-06-12&endDate=2026-06-22&format=json",
        "https://api.tiingo.com@evil.example/tiingo/daily/SPY/prices?startDate=2026-06-12&endDate=2026-06-22&format=json",
        "https://api.tiingo.com:443/tiingo/daily/SPY/prices?startDate=2026-06-12&endDate=2026-06-22&format=json",
        "https://api.tiingo.com/tiingo/daily/BTC/prices?startDate=2026-06-12&endDate=2026-06-22&format=json",
        "https://api.tiingo.com/tiingo/daily/SPY/metadata?startDate=2026-06-12&endDate=2026-06-22&format=json",
        "https://api.tiingo.com/tiingo/daily/SPY/prices?startDate=2026-06-12&endDate=2026-06-22&format=json&token=secret",
    ],
)
def test_tiingo_url_scope_rejects_any_non_allowlisted_destination(url: str) -> None:
    with pytest.raises(refresh.MarketDataFetchError) as exc_info:
        refresh._validated_tiingo_request_target(url)

    assert exc_info.value.category == "provider_url_scope_violation"


def test_tiingo_transport_rejects_non_token_header_before_connection() -> None:
    url = (
        "https://api.tiingo.com/tiingo/daily/SPY/prices"
        "?startDate=2026-06-12&endDate=2026-06-22&format=json"
    )
    with pytest.raises(refresh.MarketDataFetchError) as exc_info:
        refresh._tiingo_http_get(url, {"Authorization": "Bearer wrong-scheme"})

    assert exc_info.value.category == "provider_header_scope_violation"


def test_default_expected_date_uses_latest_completed_nyse_session() -> None:
    assert (
        refresh._default_expected_latest_bar_date(
            datetime(2026, 7, 15, 0, 10, tzinfo=UTC)
        )
        == "2026-07-14"
    )
    assert (
        refresh._default_expected_latest_bar_date(
            datetime(2026, 7, 14, 19, 30, tzinfo=UTC)
        )
        == "2026-07-13"
    )
    assert (
        refresh._default_expected_latest_bar_date(
            datetime(2026, 7, 19, 16, 0, tzinfo=UTC)
        )
        == "2026-07-17"
    )


def test_atomic_writer_preserves_previous_file_when_replace_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = tmp_path / "canonical.csv"
    target.write_bytes(b"previous")

    def fail_replace(self: Path, target_path: Path) -> Path:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        refresh._write_bytes_atomic(target, b"replacement")

    assert target.read_bytes() == b"previous"
    assert not target.with_name("canonical.csv.tmp").exists()


def test_no_files_under_runs_are_tracked_by_git() -> None:
    result = subprocess.run(
        ["git", "ls-files", "runs"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def _live_config(
    tmp_path: Path,
    canonical_csv: Path,
) -> SPYAdjustedDataRefreshConfig:
    return SPYAdjustedDataRefreshConfig(
        provider="tiingo",
        expected_latest_bar_date=EXPECTED_DATE,
        output_csv=tmp_path / "operator_input.csv",
        canonical_csv=canonical_csv,
        run_log=tmp_path / "manifest.jsonl",
        mode="live_market_data_fetch",
        live_fetch_authorized=True,
        raw_response_path=tmp_path / "raw_response.json",
    )


def _valid_same_day_http_get(url: str, headers: Mapping[str, str]) -> bytes:
    assert url.startswith(
        "https://api.tiingo.com/tiingo/daily/SPY/prices?"
    )
    assert headers == {"Authorization": "Token tiingo-token"}
    return json.dumps(
        [
            {
                "date": f"{EXPECTED_DATE}T00:00:00.000Z",
                "open": 500,
                "high": 501,
                "low": 499,
                "close": 500,
                "volume": 1000,
                "adjClose": 500,
            }
        ]
    ).encode("utf-8")


def _offline_config(
    fixture_csv: Path,
    output_csv: Path,
    canonical_csv: Path,
    run_log: Path,
) -> SPYAdjustedDataRefreshConfig:
    return SPYAdjustedDataRefreshConfig(
        provider="tiingo",
        expected_latest_bar_date=EXPECTED_DATE,
        output_csv=output_csv,
        canonical_csv=canonical_csv,
        run_log=run_log,
        mode="offline_fixture",
        fixture_input_path=fixture_csv,
    )


def _run_invalid_fixture(
    tmp_path: Path,
    rows: list[dict[str, str]],
) -> tuple[dict[str, object], Path]:
    fixture_csv = tmp_path / "tiingo_fixture.csv"
    output_csv = tmp_path / "operator_input.csv"
    canonical_csv = tmp_path / "canonical.csv"
    run_log = tmp_path / "manifest.jsonl"
    _write_canonical(canonical_csv, latest_date="2026-06-18")
    _write_provider_csv(fixture_csv, rows)
    payload = run_spy_adjusted_data_refresh(
        _offline_config(fixture_csv, output_csv, canonical_csv, run_log),
        http_get=_raise_http_get,
    )
    return payload, output_csv


def _write_provider_csv(path: Path, rows: list[dict[str, str]]) -> None:
    header = "date,open,high,low,close,volume,adjClose\n"
    lines = [header]
    for row in rows:
        lines.append(
            ",".join(
                (
                    row["date"],
                    row.get("open", "551"),
                    row.get("high", "556"),
                    row.get("low", "550"),
                    row.get("close", "555"),
                    row.get("volume", "1000"),
                    row.get("adjClose", "555.25"),
                )
            )
            + "\n"
        )
    path.write_text("".join(lines), encoding="utf-8")


def _write_canonical(path: Path, *, latest_date: str, symbol: str = "SPY") -> None:
    path.write_text(
        "symbol,date,open,high,low,close,adjusted_close,volume\n"
        f"{symbol},{latest_date},500,501,499,500,500,1000\n",
        encoding="utf-8",
        newline="\n",
    )


def _raise_http_get(url: str, headers: Mapping[str, str]) -> bytes:
    raise AssertionError("network access attempted")


def _raise_token_lookup(name: str) -> str | None:
    raise AssertionError("token lookup attempted")
