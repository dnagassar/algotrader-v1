from __future__ import annotations

from datetime import date
import os
from pathlib import Path
import subprocess

import pytest

from algotrader.errors import ValidationError
from algotrader.research import qual_quality_sleeve as subject


ROOT = Path(__file__).resolve().parents[2]
DATA = (
    ROOT
    / "runs/v5_78_qual_quality_sleeve/canonical/qual_daily_tiingo_adjusted_canonical.csv"
)
SCRIPT = ROOT / "scripts/run_qual_quality_sleeve.ps1"


def test_preregistration_is_exact_outcome_blind_and_shadow_only() -> None:
    payload = subject.build_qual_quality_sleeve_preregistration()
    assert payload["candidate_id"] == "static_qual_quality_sleeve_proxy"
    assert payload["candidate_symbol"] == "QUAL"
    assert payload["comparators"] == ["PBUS", "SPY"]
    assert payload["rule"] == "buy_and_hold_qual_with_one_oos_entry_cost"
    assert payload["cost_bps_one_time_entry"] == {
        "zero": "0",
        "decision": "5",
        "stress": "15",
    }
    assert payload["parameter_search_performed"] is False
    assert payload["source_metrics_used"] is False
    assert payload["maximum_route"] == "new_untouched_no_submit_shadow"
    assert payload["paper_promotion_allowed"] is False
    assert payload["live_authorized"] is False


def test_tracked_receipt_is_hash_pinned(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subject, "_RECEIPT_HASH", "0" * 64)
    with pytest.raises(ValidationError, match="data receipt SHA-256 mismatch"):
        subject.build_qual_quality_sleeve_preregistration()


def test_one_time_entry_cost_is_applied_only_at_oos_start() -> None:
    dates = (date(2019, 12, 31), date(2020, 1, 2), date(2020, 1, 3))
    returns = (0.01, 0.02, 0.03)
    series = subject._candidate(dates, returns, 0.0005)
    assert series.turnover == (0.0, 1.0, 0.0)
    assert series.returns[0] == pytest.approx(0.01)
    assert series.returns[1] == pytest.approx((1.0 - 0.0005) * 1.02 - 1.0)
    assert series.returns[2] == pytest.approx(0.03)
    assert series.holdings == ("QUAL", "QUAL", "QUAL")


@pytest.mark.skipif(not DATA.is_file(), reason="ignored canonical V5.78 data required")
def test_canonical_evaluation_replays_byte_identically(tmp_path: Path) -> None:
    output = tmp_path / "evaluation"
    first = subject.run_qual_quality_sleeve(output)
    first_bytes = {path.name: path.read_bytes() for path in output.iterdir()}
    second = subject.run_qual_quality_sleeve(output)
    second_bytes = {path.name: path.read_bytes() for path in output.iterdir()}
    assert first_bytes == second_bytes
    assert first["terminal_decision"] == second["terminal_decision"]
    assert first["terminal_decision"]["route"] in {
        "validated_alpha_candidate",
        "close_static_qual_quality_sleeve_proxy",
    }
    assert first["terminal_decision"]["paper_promotion_allowed"] is False
    assert first["terminal_decision"]["live_authorized"] is False
    assert set(first["gates"]) == {
        "common_integrity",
        "candidate_specific_alpha",
        "portfolio_level_value",
    }
    assert (
        first["evaluation"]["candidate_cost_metrics"]["decision"]["oos"][
            "session_count"
        ]
        == 1653
    )
    assert first["source_metric_trust"]["external_performance_trusted"] is False


@pytest.mark.skipif(not DATA.is_file(), reason="ignored canonical V5.78 data required")
def test_canonical_inputs_are_exactly_common() -> None:
    data = subject._load_data()
    assert len(data.dates) == 1905
    assert data.dates[0] == date(2019, 1, 2)
    assert data.dates[-1] == date(2026, 7, 31)
    assert set(data.prices) == set(subject.SYMBOLS)
    assert all(len(values) == len(data.dates) for values in data.prices.values())


def test_wrapper_blocks_credentials_without_disclosure(tmp_path: Path) -> None:
    shell = _powershell()
    sentinel = "quality-secret-must-not-print"
    env = os.environ.copy()
    env["TIINGO_API_KEY"] = sentinel
    result = subprocess.run(
        [shell, "-NoProfile", "-File", str(SCRIPT), "-OutputRoot", str(tmp_path)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 2
    assert "blocked_unsafe_environment" in combined
    assert sentinel not in combined


def test_wrapper_has_no_broker_or_submit_surface() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "APP_PROFILE" in text
    assert "TIINGO_API_KEY" in text
    assert "NEXUSTRADE_ACCESS_TOKEN" in text
    assert "algotrader.research.qual_quality_sleeve" in text
    assert "broker" not in text.lower()
    assert "submit" not in text.lower()


def _powershell() -> str:
    for candidate in ("pwsh", "powershell"):
        try:
            result = subprocess.run(
                [
                    candidate,
                    "-NoProfile",
                    "-Command",
                    "$PSVersionTable.PSVersion.Major",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except OSError:
            continue
        if result.returncode == 0:
            return candidate
    pytest.skip("PowerShell is required")
