from __future__ import annotations

from datetime import date
import os
from pathlib import Path
import subprocess

import pytest

from algotrader.errors import ValidationError
from algotrader.research import faber_global_relative_strength as subject


ROOT = Path(__file__).resolve().parents[2]
DATA = (
    ROOT
    / "runs/v5_75_faber_global_relative_strength/canonical/efa_daily_tiingo_adjusted_canonical.csv"
)
SCRIPT = ROOT / "scripts/run_faber_global_relative_strength.ps1"


def test_preregistration_is_exact_outcome_blind_and_shadow_only() -> None:
    payload = subject.build_faber_global_relative_strength_preregistration()

    assert payload["candidate_id"] == (
        "faber_global_asset_relative_strength_top2_12m_proxy"
    )
    assert payload["symbols"] == ["SPY", "EFA", "IEF", "VNQ", "DBC"]
    assert payload["formation"] == "twelve_complete_month_end_total_return_intervals"
    assert payload["target_weights"] == {"selected_1": "0.5", "selected_2": "0.5"}
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


def test_tracked_protocol_and_receipt_are_hash_pinned(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subject, "_RECEIPT_HASH", "0" * 64)
    with pytest.raises(ValidationError, match="data receipt SHA-256 mismatch"):
        subject.build_faber_global_relative_strength_preregistration()


def test_exact_rank_ties_use_ticker_ascending() -> None:
    assert subject._rank_top_two({symbol: 0.0 for symbol in subject.CANDIDATE_SYMBOLS}) == (
        "DBC",
        "EFA",
    )
    scores = {symbol: 0.0 for symbol in subject.CANDIDATE_SYMBOLS}
    scores["VNQ"] = 1.0
    assert subject._rank_top_two(scores) == ("VNQ", "DBC")


def test_missing_calendar_month_is_not_compressed() -> None:
    months = [
        (2020, 1),
        (2020, 2),
        (2020, 3),
        (2020, 4),
        (2020, 5),
        (2020, 6),
        (2020, 8),
        (2020, 9),
        (2020, 10),
        (2020, 11),
        (2020, 12),
        (2021, 1),
        (2021, 2),
    ]
    dates = tuple(date(year, month, 28) for year, month in months) + (date(2021, 3, 1),)
    prices = {
        symbol: tuple(float(index + 1) for index in range(len(dates)))
        for symbol in subject.CANDIDATE_SYMBOLS
    }
    with pytest.raises(
        ValidationError, match="twelve complete consecutive month intervals required"
    ):
        subject._actions(subject._Data(dates, prices))


def test_initial_and_drift_rebalance_turnover_include_cash() -> None:
    dates = (date(2020, 2, 3), date(2020, 3, 2))
    returns = {
        symbol: ((0.10, 0.0) if symbol == "SPY" else (0.0, 0.0))
        for symbol in subject.CANDIDATE_SYMBOLS
    }
    actions = {
        dates[0]: ("SPY", "EFA"),
        dates[1]: ("SPY", "EFA"),
    }
    series = subject._simulate(dates, returns, actions, 0.0)

    assert series.turnover[0] == pytest.approx(1.0)
    assert series.returns[0] == pytest.approx(0.05)
    assert series.turnover[1] == pytest.approx(1.0 / 42.0)
    assert series.exposure == pytest.approx((1.0, 1.0))


@pytest.mark.skipif(not DATA.is_file(), reason="ignored canonical V5.75 data required")
def test_canonical_evaluation_replays_byte_identically(tmp_path: Path) -> None:
    output = tmp_path / "evaluation"
    first = subject.run_faber_global_relative_strength(output)
    first_bytes = {path.name: path.read_bytes() for path in output.iterdir()}
    second = subject.run_faber_global_relative_strength(output)
    second_bytes = {path.name: path.read_bytes() for path in output.iterdir()}

    assert first_bytes == second_bytes
    assert first["terminal_decision"] == second["terminal_decision"]
    assert first["terminal_decision"]["route"] in {
        "validated_alpha_candidate",
        "close_faber_global_asset_relative_strength_top2_12m_proxy",
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
        == 3917
    )
    assert first["source_metric_trust"]["external_performance_trusted"] is False


@pytest.mark.skipif(not DATA.is_file(), reason="ignored canonical V5.75 data required")
def test_monthly_actions_use_exact_top_two_and_next_session_lag() -> None:
    data = subject._load_data()
    actions, scores = subject._actions(data)
    positions = {item: index for index, item in enumerate(data.dates)}

    assert subject._OOS_START in actions
    assert all(len(target) == 2 and len(set(target)) == 2 for target in actions.values())
    for item, target in actions.items():
        assert target == subject._rank_top_two(scores[item])
        prior = data.dates[positions[item] - 1]
        assert (prior.year, prior.month) != (item.year, item.month)


def test_wrapper_blocks_credentials_without_disclosure(tmp_path: Path) -> None:
    shell = _powershell()
    sentinel = "faber-secret-must-not-print"
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
    assert "algotrader.research.faber_global_relative_strength" in text
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
