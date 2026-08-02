from __future__ import annotations

from datetime import date
import os
from pathlib import Path
import subprocess

import pytest

from algotrader.errors import ValidationError
from algotrader.research import spy_inverse_variance as subject


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "runs/v5_72_primary_source_alpha_tournament/canonical_data.csv"
SCRIPT = ROOT / "scripts/run_spy_inverse_variance.ps1"


def test_preregistration_is_exact_outcome_blind_and_shadow_only() -> None:
    payload = subject.build_spy_inverse_variance_preregistration()
    assert payload["candidate_id"] == "spy_inverse_variance_long_cash_proxy"
    assert payload["symbol"] == "SPY"
    assert payload["cash_return"] == "0"
    assert payload["variance_estimator"] == "calendar_month_population_variance"
    assert payload["weight_rule"] == "min_1_c_divided_by_prior_month_variance"
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
        subject.build_spy_inverse_variance_preregistration()


def test_weight_simulation_drifts_and_charges_cash_inclusive_turnover() -> None:
    dates = (date(2020, 1, 2), date(2020, 1, 3), date(2020, 2, 3))
    returns = (0.10, 0.0, 0.0)
    actions = {dates[0]: 0.5, dates[2]: 0.5}
    series = subject._simulate(dates, returns, actions, 0.0)

    assert series.turnover[0] == pytest.approx(0.5)
    assert series.returns[0] == pytest.approx(0.05)
    assert series.turnover[1] == pytest.approx(0.0)
    assert series.turnover[2] == pytest.approx(1.0 / 42.0)
    assert series.exposure[0] == pytest.approx(0.5)
    assert series.exposure[1] == pytest.approx(11.0 / 21.0)


def test_weight_validation_fails_closed() -> None:
    with pytest.raises(ValidationError, match="target weight is invalid"):
        subject._simulate((date(2020, 1, 2),), (0.0,), {date(2020, 1, 2): 1.1}, 0.0)


@pytest.mark.skipif(not DATA.is_file(), reason="ignored canonical V5.77 data required")
def test_calibration_and_actions_are_fixed_and_lagged() -> None:
    data = subject._load_data()
    calibration, variances, actions = subject._actions(data)
    positions = {item: index for index, item in enumerate(data.dates)}

    assert calibration > 0.0
    assert len(
        [
            key
            for key in variances
            if key >= (2004, 12) and key <= (2016, 12)
        ]
    ) == 145
    assert min(actions) == date(2017, 1, 3)
    assert all(0.0 <= weight <= 1.0 for weight in actions.values())
    for item in actions:
        prior = data.dates[positions[item] - 1]
        assert (prior.year, prior.month) != (item.year, item.month)


@pytest.mark.skipif(not DATA.is_file(), reason="ignored canonical V5.77 data required")
def test_canonical_evaluation_replays_byte_identically(tmp_path: Path) -> None:
    output = tmp_path / "evaluation"
    first = subject.run_spy_inverse_variance(output)
    first_bytes = {path.name: path.read_bytes() for path in output.iterdir()}
    second = subject.run_spy_inverse_variance(output)
    second_bytes = {path.name: path.read_bytes() for path in output.iterdir()}

    assert first_bytes == second_bytes
    assert first["terminal_decision"] == second["terminal_decision"]
    assert first["terminal_decision"]["route"] in {
        "validated_alpha_candidate",
        "close_spy_inverse_variance_long_cash_proxy",
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
        == 2304
    )
    assert first["source_metric_trust"]["external_performance_trusted"] is False


def test_wrapper_blocks_credentials_without_disclosure(tmp_path: Path) -> None:
    shell = _powershell()
    sentinel = "inverse-variance-secret-must-not-print"
    env = os.environ.copy()
    env["APCA_API_SECRET_KEY"] = sentinel
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
    assert "algotrader.research.spy_inverse_variance" in text
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
