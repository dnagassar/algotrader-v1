from __future__ import annotations

from datetime import date
import os
from pathlib import Path
import subprocess

import pytest

from algotrader.errors import ValidationError
from algotrader.research import halloween_spy_bil as subject


ROOT = Path(__file__).resolve().parents[2]
DATA = (
    ROOT
    / "runs/v5_73_global_equities_dual_momentum/canonical/bil_daily_tiingo_adjusted_canonical.csv"
)
SCRIPT = ROOT / "scripts/run_halloween_spy_bil.ps1"


def test_preregistration_is_exact_outcome_blind_and_shadow_only() -> None:
    payload = subject.build_halloween_spy_bil_preregistration()

    assert payload["candidate_id"] == "halloween_spy_bil_seasonal_proxy"
    assert payload["symbols"] == ["SPY", "BIL"]
    assert payload["spy_months"] == [11, 12, 1, 2, 3, 4]
    assert payload["bil_months"] == [5, 6, 7, 8, 9, 10]
    assert payload["cost_bps_per_one_way_turnover"] == {
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
        subject.build_halloween_spy_bil_preregistration()


def test_calendar_targets_and_first_common_session_switches() -> None:
    dates = (
        date(2020, 4, 30),
        date(2020, 5, 1),
        date(2020, 5, 4),
        date(2020, 10, 30),
        date(2020, 11, 2),
        date(2020, 11, 3),
    )
    actions = subject._seasonal_actions(dates)

    assert subject._calendar_target(date(2020, 1, 2)) == "SPY"
    assert subject._calendar_target(date(2020, 7, 1)) == "BIL"
    assert actions == {
        date(2020, 4, 30): {"SPY": 1.0},
        date(2020, 5, 1): {"BIL": 1.0},
        date(2020, 11, 2): {"SPY": 1.0},
    }


def test_turnover_includes_initial_cash_and_full_switch() -> None:
    dates = (date(2020, 4, 30), date(2020, 5, 1))
    returns = {"SPY": (0.02, 0.0), "BIL": (0.0, 0.01)}
    actions = {
        dates[0]: {"SPY": 1.0},
        dates[1]: {"BIL": 1.0},
    }
    series = subject._simulate_allocations(
        dates, returns, actions, 0.0005, subject.CANDIDATE_SYMBOLS
    )

    assert series.turnover == pytest.approx((1.0, 1.0))
    assert series.returns[0] == pytest.approx((1.0 - 0.0005) * 1.02 - 1.0)
    assert series.returns[1] == pytest.approx((1.0 - 0.0005) * 1.01 - 1.0)
    assert series.holdings == ("SPY", "BIL")


def test_annual_balanced_baseline_drifts_until_next_year() -> None:
    dates = (date(2020, 1, 2), date(2020, 1, 3), date(2021, 1, 4))
    actions = subject._annual_balanced_actions(dates)
    assert actions == {
        date(2020, 1, 2): {"SPY": 0.5, "BIL": 0.5},
        date(2021, 1, 4): {"SPY": 0.5, "BIL": 0.5},
    }
    returns = {"SPY": (0.10, 0.0, 0.0), "BIL": (0.0, 0.0, 0.0)}
    series = subject._simulate_allocations(
        dates, returns, actions, 0.0, subject.CANDIDATE_SYMBOLS
    )
    assert series.turnover[0] == pytest.approx(1.0)
    assert series.turnover[1] == pytest.approx(0.0)
    assert series.turnover[2] == pytest.approx(1.0 / 42.0)


@pytest.mark.skipif(not DATA.is_file(), reason="ignored canonical V5.76 data required")
def test_canonical_evaluation_replays_byte_identically(tmp_path: Path) -> None:
    output = tmp_path / "evaluation"
    first = subject.run_halloween_spy_bil(output)
    first_bytes = {path.name: path.read_bytes() for path in output.iterdir()}
    second = subject.run_halloween_spy_bil(output)
    second_bytes = {path.name: path.read_bytes() for path in output.iterdir()}

    assert first_bytes == second_bytes
    assert first["terminal_decision"] == second["terminal_decision"]
    assert first["terminal_decision"]["route"] in {
        "validated_alpha_candidate",
        "close_halloween_spy_bil_seasonal_proxy",
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
        == 4674
    )
    assert first["source_metric_trust"]["external_performance_trusted"] is False


@pytest.mark.skipif(not DATA.is_file(), reason="ignored canonical V5.76 data required")
def test_canonical_actions_preserve_calendar_state_and_fold_continuity() -> None:
    data = subject._load_data()
    actions = subject._seasonal_actions(data.dates[1:])
    oos_actions = [
        item for item in actions if subject._OOS_START <= item <= subject._END
    ]

    assert len(oos_actions) == 37
    assert all(item.month in (5, 11) for item in oos_actions)
    assert all(next(iter(actions[item])) == subject._calendar_target(item) for item in actions)


def test_wrapper_blocks_credentials_without_disclosure(tmp_path: Path) -> None:
    shell = _powershell()
    sentinel = "halloween-secret-must-not-print"
    env = os.environ.copy()
    env["NEXUSTRADE_ACCESS_TOKEN"] = sentinel
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
    assert "algotrader.research.halloween_spy_bil" in text
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
