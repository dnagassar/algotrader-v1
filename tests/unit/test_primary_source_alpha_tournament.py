from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pytest

from algotrader.research import primary_source_alpha_tournament as subject


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "docs/design/v5_72_primary_source_alpha_tournament_preregistration.md"
RECEIPT = ROOT / "docs/design/v5_72_primary_source_alpha_tournament_data_receipt.md"
DATA = ROOT / "runs/v5_72_primary_source_alpha_tournament/canonical_data.csv"
SCRIPT = ROOT / "scripts/run_primary_source_alpha_tournament.ps1"


def test_preregistration_is_exact_and_outcome_blind() -> None:
    payload = subject.build_primary_source_alpha_preregistration()

    assert payload["candidate_ids"] == [subject.TURN_ID, subject.SECTOR_ID]
    assert payload["cost_bps_per_one_way_turnover"] == {
        "zero": "0",
        "decision": "5",
        "stress": "15",
    }
    assert payload["parameter_search_performed"] is False
    assert payload["source_metrics_used"] is False
    assert payload["validated_alpha_means_shadow_eligible_only"] is True
    assert payload["paper_or_live_promotion_allowed"] is False


@pytest.mark.skipif(not DATA.is_file(), reason="ignored canonical V5.72 data required")
def test_canonical_tournament_replays_byte_identically(tmp_path: Path) -> None:
    output = tmp_path / "evaluation"

    first = subject.run_primary_source_alpha_tournament(output)
    first_bytes = {path.name: path.read_bytes() for path in output.iterdir()}
    second = subject.run_primary_source_alpha_tournament(output)
    second_bytes = {path.name: path.read_bytes() for path in output.iterdir()}

    assert first_bytes == second_bytes
    assert first["tournament_decision"] == second["tournament_decision"]
    assert set(first["candidate_decisions"]) == {subject.TURN_ID, subject.SECTOR_ID}
    for candidate_id, decision in first["candidate_decisions"].items():
        assert decision["route"] in {"validated_alpha_candidate", "close_candidate"}
        assert decision["paper_promotion_allowed"] is False
        assert decision["live_authorized"] is False
        assert set(decision["gates"]) == {
            "common_integrity",
            "candidate_specific_alpha",
            "portfolio_level_value",
        }
        metrics = first["evaluation"]["candidates"][candidate_id]["cost_metrics"]
        assert set(metrics) == {"zero", "decision", "stress"}
        assert metrics["decision"]["oos"]["session_count"] == 4421
    assert first["source_metric_trust"]["external_performance_trusted"] is False
    assert first["safety"]["broker_access"] is False
    assert first["safety"]["live_authorized"] is False


@pytest.mark.skipif(not DATA.is_file(), reason="ignored canonical V5.72 data required")
def test_calendar_and_sector_weight_contracts_are_literal() -> None:
    data = subject._load_data()
    _actions, targets = subject._turn_of_month_actions(data.dates)
    oos = [item for item in data.dates if subject._OOS_START <= item <= subject._OOS_END]
    invested = [item for item in oos if targets[item]["SPY"] == 1.0]
    assert 0.12 <= len(invested) / len(oos) <= 0.25
    for item in invested:
        month = [value for value in data.dates if (value.year, value.month) == (item.year, item.month)]
        assert item == month[-1] or item in month[:3]

    sector_actions = subject._sector_momentum_actions(data)
    first = sector_actions[subject._OOS_START]
    assert sum(first.values()) == pytest.approx(1.0)
    assert max(first.values()) <= 1.0 / 3.0 + 1e-12
    assert all(value * 18 == pytest.approx(round(value * 18)) for value in first.values())


def test_wrapper_blocks_loaded_credential_without_disclosing_value(tmp_path: Path) -> None:
    powershell = _powershell()
    sentinel = "must-never-appear-v572"
    env = os.environ.copy()
    env["TIINGO_API_KEY"] = sentinel
    result = subprocess.run(
        [powershell, "-NoProfile", "-File", str(SCRIPT), "-OutputRoot", str(tmp_path)],
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


def test_tracked_contracts_and_wrapper_safety_are_explicit() -> None:
    assert PROTOCOL.is_file()
    assert RECEIPT.is_file()
    text = SCRIPT.read_text(encoding="utf-8")
    assert "APP_PROFILE" in text
    assert "TIINGO_API_KEY" in text
    assert "NEXUSTRADE_ACCESS_TOKEN" in text
    assert "algotrader.research.primary_source_alpha_tournament" in text
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
