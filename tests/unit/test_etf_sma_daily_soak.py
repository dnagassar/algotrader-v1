from __future__ import annotations

import json
import os
import re
from pathlib import Path
import pytest

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_daily_soak import (
    EtfSmaDailySoakConfig,
    run_etf_sma_daily_soak,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "etf_sma_cycle_matrix"


@pytest.fixture(autouse=True)
def enforce_preflight_offline_only() -> None:
    """Ensure that no credentials or paper profiles are present in the environment."""
    assert not os.environ.get("APP_PROFILE") == "paper"
    for var in (
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
    ):
        assert var not in os.environ


def test_soak_happy_path(tmp_path: Path) -> None:
    """Test a successful soak run over 3 days (which have insufficient history)."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    config = EtfSmaDailySoakConfig(
        start_date="2025-07-10",
        end_date="2025-07-12",
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
        output_root=output_root,
        soak_rollup_jsonl=output_root / "soak_rollup.jsonl",
        soak_rollup_text=output_root / "soak_rollup.txt",
    )

    payload = run_etf_sma_daily_soak(config)

    assert payload["status"] == "completed_with_findings"  # completed with findings due to insufficient history
    assert payload["finding_count"] == 0
    assert len(payload["attempted_dates"]) == 3
    assert payload["attempted_dates"] == ["2025-07-10", "2025-07-11", "2025-07-12"]
    assert payload["accepted_dates"] == []
    assert payload["blocked_dates"] == []
    assert payload["insufficient_history_dates"] == ["2025-07-10", "2025-07-11", "2025-07-12"]

    # Check output files exist
    assert (output_root / "soak_rollup.jsonl").exists()
    assert (output_root / "soak_rollup.txt").exists()

    # Check each day folder and bundle files exist
    for d in ["2025-07-10", "2025-07-11", "2025-07-12"]:
        day_dir = output_root / d
        assert day_dir.exists()
        assert (day_dir / "cycle.jsonl").exists()
        assert (day_dir / "offline_check.jsonl").exists()

    # Verify JSON content
    rollup_data = json.loads((output_root / "soak_rollup.jsonl").read_text(encoding="utf-8").strip())
    assert rollup_data["phase"] == "offline_daily_loop_soak"
    assert rollup_data["status"] == "completed_with_findings"
    assert rollup_data["live_trading_authorized"] is False
    assert rollup_data["network_access_authorized"] is False


def test_soak_single_day_accepted(tmp_path: Path) -> None:
    """Test a soak run over the single date in the CSV with sufficient history (2025-07-19)."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    config = EtfSmaDailySoakConfig(
        start_date="2025-07-19",
        end_date="2025-07-19",
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
        output_root=output_root,
        soak_rollup_jsonl=output_root / "soak_rollup.jsonl",
        soak_rollup_text=output_root / "soak_rollup.txt",
    )

    payload = run_etf_sma_daily_soak(config)

    assert payload["status"] == "accepted"
    assert payload["finding_count"] == 0
    assert payload["attempted_dates"] == ["2025-07-19"]
    assert payload["accepted_dates"] == ["2025-07-19"]
    assert payload["blocked_dates"] == []
    assert payload["insufficient_history_dates"] == []


def test_soak_invalid_date_range(tmp_path: Path) -> None:
    """Verify start date after end date raises ValidationError."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    config = EtfSmaDailySoakConfig(
        start_date="2025-07-12",
        end_date="2025-07-10",
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
        output_root=output_root,
    )

    with pytest.raises(ValidationError, match="is after end_date"):
        run_etf_sma_daily_soak(config)


def test_soak_no_dates_found(tmp_path: Path) -> None:
    """Verify range with no overlapping dates raises ValidationError."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    config = EtfSmaDailySoakConfig(
        start_date="1999-01-01",
        end_date="1999-01-10",
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
        output_root=output_root,
    )

    with pytest.raises(ValidationError, match="No dates found in bars CSV"):
        run_etf_sma_daily_soak(config)


def test_soak_blocker_propagates(tmp_path: Path) -> None:
    """Verify blocker presence propagates to the rollup status and blocked lists."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_open_order.jsonl"

    config = EtfSmaDailySoakConfig(
        start_date="2025-07-10",
        end_date="2025-07-12",
        bars_csv=bars_csv,
        reconciliation_state_path=reco_path,
        output_root=output_root,
        soak_rollup_jsonl=output_root / "soak_rollup.jsonl",
        soak_rollup_text=output_root / "soak_rollup.txt",
    )

    payload = run_etf_sma_daily_soak(config)

    assert payload["status"] == "completed_with_findings"
    assert payload["finding_count"] > 0
    assert len(payload["attempted_dates"]) == 3
    assert payload["accepted_dates"] == []
    assert payload["blocked_dates"] == ["2025-07-10", "2025-07-11", "2025-07-12"]

    # Verify JSON content
    rollup_data = json.loads((output_root / "soak_rollup.jsonl").read_text(encoding="utf-8").strip())
    assert rollup_data["status"] == "completed_with_findings"
    assert rollup_data["finding_count"] > 0


def test_soak_no_absolute_paths() -> None:
    """Verify that soak rollups and artifact listings do not leak absolute paths."""
    test_run_dir = Path("runs/test_soak_absolute_path_assertion")
    if test_run_dir.exists():
        import shutil
        shutil.rmtree(test_run_dir, ignore_errors=True)

    try:
        bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
        reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

        config = EtfSmaDailySoakConfig(
            start_date="2025-07-10",
            end_date="2025-07-12",
            bars_csv=bars_csv,
            reconciliation_state_path=reco_path,
            output_root=test_run_dir,
            soak_rollup_jsonl=test_run_dir / "soak_rollup.jsonl",
            soak_rollup_text=test_run_dir / "soak_rollup.txt",
        )

        payload = run_etf_sma_daily_soak(config)
        assert payload["status"] == "completed_with_findings"

        # Verify no absolute paths in soak_rollup.jsonl
        rollup_json = test_run_dir / "soak_rollup.jsonl"
        content = rollup_json.read_text(encoding="utf-8")
        assert "C:" not in content
        assert "c:" not in content
        assert not re.search(r"[a-zA-Z]:[\\/]", content)

        # Parse paths and ensure they are all relative POSIX paths
        data = json.loads(content)
        for path_str in data["artifact_paths"]:
            assert not path_str.startswith("/")
            assert "\\" not in path_str
            assert not re.match(r"^[a-zA-Z]:", path_str)

    finally:
        import shutil
        shutil.rmtree(test_run_dir, ignore_errors=True)


def test_soak_cli_command(tmp_path: Path) -> None:
    """Test CLI dispatching of the soak command."""
    output_root = tmp_path / "daily"
    bars_csv = FIXTURES_DIR / "spy_daily_bars_200_bullish.csv"
    reco_path = FIXTURES_DIR / "reconciliation_state_flat.jsonl"

    code = cli_module.main([
        "etf-sma-daily-soak",
        "--start-date", "2025-07-10",
        "--end-date", "2025-07-12",
        "--bars-csv", str(bars_csv),
        "--reconciliation-state-path", str(reco_path),
        "--output-root", str(output_root),
        "--soak-rollup-jsonl", str(output_root / "soak_rollup.jsonl"),
        "--soak-rollup-text", str(output_root / "soak_rollup.txt"),
        "--format", "json",
    ])
    assert code == 0
