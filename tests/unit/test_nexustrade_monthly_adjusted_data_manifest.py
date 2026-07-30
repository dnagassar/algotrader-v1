from __future__ import annotations

from datetime import date
from decimal import Decimal
import json
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.nexustrade_monthly_adjusted_data_manifest import (
    NEXUSTRADE_MONTHLY_ADJUSTED_DATA_SYMBOLS,
    NexusTradeMonthlyAdjustedDataManifestConfig,
    TIINGO_PROVIDER_SYMBOL_BY_CANONICAL,
    build_nexustrade_monthly_adjusted_data_manifest,
    main,
    run_nexustrade_monthly_adjusted_data_manifest,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REFRESH_SCRIPT = (
    PROJECT_ROOT / "scripts" / "refresh_nexustrade_monthly_adjusted_data.ps1"
)
SESSION_DATES = (
    date(2019, 1, 2),
    date(2021, 12, 30),
    date(2021, 12, 31),
    date(2024, 3, 22),
    date(2024, 3, 25),
    date(2025, 3, 28),
)


def test_complete_exact_universe_writes_hashed_combined_csv_and_manifest(
    tmp_path: Path,
) -> None:
    canonical_paths = _write_universe(tmp_path)
    combined = tmp_path / "multi_etf_adjusted_daily_canonical.csv"
    manifest = tmp_path / "canonical_data_manifest.json"

    payload = run_nexustrade_monthly_adjusted_data_manifest(
        NexusTradeMonthlyAdjustedDataManifestConfig(
            output_manifest=manifest,
            combined_output_csv=combined,
            canonical_paths=canonical_paths,
            minimum_pretraining_sessions=2,
        )
    )

    assert payload["canonical_data_ready"] is True
    assert payload["symbols"] == list(NEXUSTRADE_MONTHLY_ADJUSTED_DATA_SYMBOLS)
    assert payload["valid_symbols"] == list(NEXUSTRADE_MONTHLY_ADJUSTED_DATA_SYMBOLS)
    assert payload["blocked_symbols"] == []
    assert payload["session_reference_basis"] == "Tiingo SPY observed EOD dates"
    assert payload["session_reference_count"] == len(SESSION_DATES)
    assert payload["provider_symbol_map"]["BRK-B"] == "BRK-B"
    assert payload["brk_b_mapping"] == "BRK-B->BRK-B"
    assert payload["canonical_price_source_field"] == "adjClose"
    assert payload["adjusted_ohlcv_claimed"] is False
    assert payload["authentic_indicator_warmup_semantics_resolved"] is False
    assert payload["combined_output_written"] is True
    assert payload["combined_output_sha256"]
    assert payload["combined_row_count"] == (
        len(NEXUSTRADE_MONTHLY_ADJUSTED_DATA_SYMBOLS) * len(SESSION_DATES)
    )
    assert combined.is_file()
    assert manifest.is_file()
    assert json.loads(manifest.read_text(encoding="utf-8")) == payload

    rows = combined.read_text(encoding="utf-8").splitlines()
    assert rows[0] == "symbol,date,open,high,low,close,adjusted_close,volume"
    assert sum(1 for row in rows if row.startswith("BRK-B,")) == len(SESSION_DATES)
    assert sum(1 for row in rows if row.startswith("META,")) == len(SESSION_DATES)

    for record in payload["symbol_data"]:
        assert record["canonical_sha256"]
        assert record["session_validation_status"] == (
            "matches_tiingo_spy_observed_sessions"
        )
        assert record["supports_365_calendar_day_warmup"] is True
        assert record["supports_minimum_pretraining_sessions"] is True
        assert record["validation_status"] == "valid"
        assert record["blockers"] == []


def test_missing_one_spy_reference_session_blocks_combined_output(
    tmp_path: Path,
) -> None:
    canonical_paths = _write_universe(
        tmp_path,
        session_overrides={
            "META": tuple(value for value in SESSION_DATES if value != date(2024, 3, 25))
        },
    )
    combined = tmp_path / "combined.csv"

    payload = run_nexustrade_monthly_adjusted_data_manifest(
        NexusTradeMonthlyAdjustedDataManifestConfig(
            output_manifest=tmp_path / "manifest.json",
            combined_output_csv=combined,
            canonical_paths=canonical_paths,
            minimum_pretraining_sessions=2,
        )
    )

    assert payload["canonical_data_ready"] is False
    assert payload["blocked_symbols"] == ["META"]
    assert payload["combined_output_written"] is False
    assert payload["combined_output_sha256"] == ""
    assert not combined.exists()
    meta = _symbol_record(payload, "META")
    assert meta["missing_reference_sessions"] == ["2024-03-25"]
    assert "missing_spy_reference_sessions" in meta["blockers"]


def test_exact_canonical_path_set_and_date_order_are_required(tmp_path: Path) -> None:
    paths = _write_universe(tmp_path)
    paths.pop("SPY")
    with pytest.raises(
        ValidationError,
        match="canonical_paths must contain exactly",
    ):
        NexusTradeMonthlyAdjustedDataManifestConfig(canonical_paths=paths)

    with pytest.raises(ValidationError, match="date contract must satisfy"):
        NexusTradeMonthlyAdjustedDataManifestConfig(
            canonical_paths=_write_universe(tmp_path / "second"),
            data_start="2022-01-01",
            train_start="2021-12-31",
        )


def test_build_is_offline_and_does_not_write_outputs(tmp_path: Path) -> None:
    combined = tmp_path / "combined.csv"
    manifest = tmp_path / "manifest.json"
    payload = build_nexustrade_monthly_adjusted_data_manifest(
        NexusTradeMonthlyAdjustedDataManifestConfig(
            output_manifest=manifest,
            combined_output_csv=combined,
            canonical_paths=_write_universe(tmp_path),
            minimum_pretraining_sessions=2,
        )
    )

    assert payload["canonical_data_ready"] is True
    assert payload["safety"]["network_access_attempted"] is False
    assert payload["safety"]["credential_access_attempted"] is False
    assert payload["safety"]["broker_access_attempted"] is False
    assert not combined.exists()
    assert not manifest.exists()


def test_symbol_map_is_exact_and_wrapper_is_fail_closed() -> None:
    assert tuple(TIINGO_PROVIDER_SYMBOL_BY_CANONICAL) == (
        NEXUSTRADE_MONTHLY_ADJUSTED_DATA_SYMBOLS
    )
    assert TIINGO_PROVIDER_SYMBOL_BY_CANONICAL["BRK-B"] == "BRK-B"

    script = REFRESH_SCRIPT.read_text(encoding="utf-8")
    assert '[string]$Mode = "dry_run"' in script
    assert '[string]$DataStart = "2019-01-02"' in script
    assert '[string]$ExpectedLatestBarDate = "2025-03-28"' in script
    assert "[switch]$LiveMarketDataFetchAuthorized" in script
    assert "live_market_data_fetch requires -LiveMarketDataFetchAuthorized" in script
    assert "TIINGO_API_KEY" in script
    assert "ALPACA_API_KEY" not in script
    assert "does not read broker state" in script
    assert "copy the dotenv file" in script
    for symbol in NEXUSTRADE_MONTHLY_ADJUSTED_DATA_SYMBOLS:
        assert f'"{symbol}"' in script


def test_cli_accepts_all_repeated_canonical_path_overrides(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    paths = _write_universe(tmp_path)
    args = [
        "--output-manifest",
        str(tmp_path / "manifest.json"),
        "--combined-output-csv",
        str(tmp_path / "combined.csv"),
        "--minimum-pretraining-sessions",
        "2",
    ]
    for symbol in NEXUSTRADE_MONTHLY_ADJUSTED_DATA_SYMBOLS:
        args.extend(("--canonical-path", f"{symbol}={paths[symbol]}"))

    assert main(args) == 0
    output = capsys.readouterr().out
    assert "nexustrade_monthly_adjusted_data_manifest_status=ready" in output
    assert "blocked_symbols=" in output


def _write_universe(
    root: Path,
    *,
    session_overrides: dict[str, tuple[date, ...]] | None = None,
) -> dict[str, Path]:
    overrides = session_overrides or {}
    return {
        symbol: _write_symbol_csv(
            root / f"{symbol.lower()}_daily_tiingo_adjusted_canonical.csv",
            symbol,
            overrides.get(symbol, SESSION_DATES),
        )
        for symbol in NEXUSTRADE_MONTHLY_ADJUSTED_DATA_SYMBOLS
    }


def _write_symbol_csv(
    path: Path,
    symbol: str,
    sessions: tuple[date, ...],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    base = Decimal("100") + Decimal(len(symbol))
    rows = ["symbol,date,open,high,low,close,adjusted_close,volume"]
    for index, session in enumerate(sessions):
        price = base + Decimal(index)
        rows.append(
            f"{symbol},{session.isoformat()},{price},{price},{price},{price},"
            f"{price + Decimal('0.25')},1000"
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def _symbol_record(payload: dict[str, object], symbol: str) -> dict[str, object]:
    for record in payload["symbol_data"]:
        if record["symbol"] == symbol:
            return record
    raise AssertionError(symbol)
