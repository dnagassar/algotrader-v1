from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest

from algotrader.research import vigilant_asset_allocation_g4 as subject


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "runs/v5_74_vigilant_asset_allocation_g4/canonical/vea_daily_tiingo_adjusted_canonical.csv"
SCRIPT = ROOT / "scripts/run_vigilant_asset_allocation_g4.ps1"


def test_preregistration_is_exact_and_shadow_only() -> None:
    payload = subject.build_vigilant_asset_allocation_g4_preregistration()
    assert payload["candidate_id"] == "vigilant_asset_allocation_g4_13612w_proxy"
    assert payload["risky_symbols"] == ["SPY", "VEA", "VWO", "BND"]
    assert payload["defensive_symbols"] == ["SHY", "IEF", "LQD"]
    assert payload["T"] == 1 and payload["B"] == 1
    assert payload["cost_bps_per_one_way_turnover"] == {"zero": "0", "decision": "10", "stress": "20"}
    assert payload["parameter_search_performed"] is False
    assert payload["source_metrics_used"] is False
    assert payload["paper_promotion_allowed"] is False
    assert payload["live_authorized"] is False


@pytest.mark.skipif(not DATA.is_file(), reason="ignored V5.74 data required")
def test_canonical_evaluation_replays_byte_identically(tmp_path: Path) -> None:
    output = tmp_path / "evaluation"
    first = subject.run_vigilant_asset_allocation_g4(output)
    first_bytes = {path.name: path.read_bytes() for path in output.iterdir()}
    second = subject.run_vigilant_asset_allocation_g4(output)
    second_bytes = {path.name: path.read_bytes() for path in output.iterdir()}
    assert first_bytes == second_bytes
    assert first["terminal_decision"] == second["terminal_decision"]
    assert first["terminal_decision"]["route"] in {"validated_alpha_candidate", "close_vigilant_asset_allocation_g4_13612w_proxy"}
    assert first["terminal_decision"]["paper_promotion_allowed"] is False
    assert first["terminal_decision"]["live_authorized"] is False
    assert set(first["gates"]) == {"common_integrity", "candidate_specific_alpha", "portfolio_level_value"}
    assert first["evaluation"]["candidate_cost_metrics"]["decision"]["oos"]["session_count"] == 2156


@pytest.mark.skipif(not DATA.is_file(), reason="ignored V5.74 data required")
def test_actions_obey_breadth_trigger_and_single_target() -> None:
    data = subject._load_data()
    actions, scores = subject._actions(data)
    assert subject._OOS_START in actions
    assert set(actions.values()) <= set((*subject.RISKY, *subject.DEFENSIVE))
    for item, target in actions.items():
        risky_all_positive = all(scores[item][symbol] > 0.0 for symbol in subject.RISKY)
        assert (target in subject.RISKY) is risky_all_positive


def test_wrapper_blocks_credentials_without_disclosure(tmp_path: Path) -> None:
    shell = _powershell()
    sentinel = "vaa-secret-must-not-print"
    env = os.environ.copy()
    env["TIINGO_API_KEY"] = sentinel
    result = subprocess.run([shell, "-NoProfile", "-File", str(SCRIPT), "-OutputRoot", str(tmp_path)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60, check=False)
    combined = result.stdout + result.stderr
    assert result.returncode == 2
    assert "blocked_unsafe_environment" in combined
    assert sentinel not in combined


def test_wrapper_has_no_broker_or_submit_surface() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "APP_PROFILE" in text and "TIINGO_API_KEY" in text
    assert "algotrader.research.vigilant_asset_allocation_g4" in text
    assert "broker" not in text.lower()
    assert "submit" not in text.lower()


def _powershell() -> str:
    for candidate in ("pwsh", "powershell"):
        try:
            result = subprocess.run([candidate, "-NoProfile", "-Command", "$PSVersionTable.PSVersion.Major"], capture_output=True, text=True, timeout=10, check=False)
        except OSError:
            continue
        if result.returncode == 0:
            return candidate
    pytest.skip("PowerShell is required")
