from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest

from algotrader.research import global_equities_dual_momentum as subject


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "runs/v5_73_global_equities_dual_momentum/canonical/veu_daily_tiingo_adjusted_canonical.csv"
SCRIPT = ROOT / "scripts/run_global_equities_dual_momentum.ps1"


def test_preregistration_is_fixed_and_shadow_only() -> None:
    payload = subject.build_global_equities_dual_momentum_preregistration()

    assert payload["candidate_id"] == "global_equities_dual_momentum_12m_proxy"
    assert payload["cost_bps_per_one_way_turnover"] == {"zero": "0", "decision": "5", "stress": "15"}
    assert payload["parameter_search_performed"] is False
    assert payload["source_metrics_used"] is False
    assert payload["maximum_route"] == "new_untouched_no_submit_shadow"
    assert payload["paper_promotion_allowed"] is False
    assert payload["live_authorized"] is False


@pytest.mark.skipif(not DATA.is_file(), reason="ignored canonical V5.73 data required")
def test_canonical_evaluation_replays_byte_identically(tmp_path: Path) -> None:
    output = tmp_path / "evaluation"
    first = subject.run_global_equities_dual_momentum(output)
    first_bytes = {path.name: path.read_bytes() for path in output.iterdir()}
    second = subject.run_global_equities_dual_momentum(output)
    second_bytes = {path.name: path.read_bytes() for path in output.iterdir()}

    assert first_bytes == second_bytes
    assert first["terminal_decision"] == second["terminal_decision"]
    assert first["terminal_decision"]["route"] in {
        "validated_alpha_candidate",
        "close_global_equities_dual_momentum_12m_proxy",
    }
    assert first["terminal_decision"]["paper_promotion_allowed"] is False
    assert first["terminal_decision"]["live_authorized"] is False
    assert set(first["gates"]) == {"common_integrity", "candidate_specific_alpha", "portfolio_level_value"}
    assert first["evaluation"]["candidate_cost_metrics"]["decision"]["oos"]["session_count"] == 3415
    assert first["source_metric_trust"]["external_performance_trusted"] is False


@pytest.mark.skipif(not DATA.is_file(), reason="ignored canonical V5.73 data required")
def test_monthly_actions_use_exact_single_asset_targets_and_warmup() -> None:
    data = subject._load_data()
    actions = subject._actions(data)

    assert subject._OOS_START in actions
    assert set(actions.values()) <= {"SPY", "VEU", "AGG"}
    assert all(item in data.dates for item in actions)
    assert len([item for item in actions if subject._OOS_START <= item <= subject._END]) > 150


def test_wrapper_blocks_credentials_without_disclosure(tmp_path: Path) -> None:
    shell = _powershell()
    sentinel = "gem-secret-must-not-print"
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
    assert "algotrader.research.global_equities_dual_momentum" in text
    assert "broker" not in text.lower()
    assert "submit" not in text.lower()


def _powershell() -> str:
    for candidate in ("pwsh", "powershell"):
        try:
            result = subprocess.run(
                [candidate, "-NoProfile", "-Command", "$PSVersionTable.PSVersion.Major"],
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
