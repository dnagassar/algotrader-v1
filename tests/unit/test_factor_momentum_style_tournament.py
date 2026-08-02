from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import subprocess

import pytest

from algotrader.research import factor_momentum_style_tournament as subject

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_v584_factor_momentum_tournament.ps1"


def test_preregistration_is_frozen_and_offline() -> None:
    payload = subject.build_factor_momentum_style_preregistration()

    assert payload["candidate_ids"] == [subject.A_ID, subject.B_ID, subject.C_ID]
    assert payload["signal_lookback_sessions"] == 252
    assert payload["action_lag"] == "month_end_close_t_to_next_common_close_t_plus_1"
    assert payload["parameter_search_performed"] is False
    assert payload["source_metrics_used"] is False
    assert payload["paper_or_live_promotion_allowed"] is False
    assert payload["safety"]["network_access_performed_by_engine"] is False
    assert payload["safety"]["live_authorized"] is False


def test_simulator_does_not_earn_action_close_return() -> None:
    dates = (date(2012, 12, 31), date(2013, 1, 2), date(2013, 1, 3))
    prices = {symbol: (100.0, 100.0, 100.0) for symbol in subject.ALL_SYMBOLS}
    prices["IWD"] = (100.0, 200.0, 220.0)
    target = subject._empty_target()
    target["IWD"] = 1.0

    series = subject._simulate(subject._Data(dates, prices), {dates[1]: target}, 0.0005)

    assert series.returns[0] == pytest.approx(-0.0005)
    assert series.returns[1] == pytest.approx(0.10)
    assert series.turnover[0] == pytest.approx(1.0)
    assert series.weights[0]["IWD"] == pytest.approx(0.0)
    assert sum(series.contributions[0].values()) + series.cost_contributions[0] == pytest.approx(series.returns[0])


def test_simulator_drifts_holdings_and_charges_rebalance_turnover() -> None:
    dates = (
        date(2012, 12, 31),
        date(2013, 1, 2),
        date(2013, 1, 3),
        date(2013, 1, 4),
    )
    prices = {symbol: (100.0, 100.0, 100.0, 100.0) for symbol in subject.ALL_SYMBOLS}
    prices["IWD"] = (100.0, 100.0, 110.0, 110.0)
    target = subject._empty_target()
    target["IWD"] = 0.5
    target["IWF"] = 0.5

    series = subject._simulate(
        subject._Data(dates, prices),
        {dates[1]: target, dates[3]: target},
        0.0,
    )

    assert series.weights[0]["IWD"] == pytest.approx(0.0)
    assert series.weights[1]["IWD"] == pytest.approx(0.5)
    assert series.weights[1]["IWF"] == pytest.approx(0.5)
    assert series.weights[2]["IWD"] == pytest.approx(0.55 / 1.05)
    assert series.weights[2]["IWF"] == pytest.approx(0.50 / 1.05)
    assert series.turnover[2] == pytest.approx(abs(0.55 / 1.05 - 0.5))


def test_actual_targets_have_exact_lag_caps_and_genuine_ensemble() -> None:
    data = subject._load_data()
    actions = subject._build_actions(data)

    assert min(actions[subject.A_ID]) == date(2013, 1, 2)
    assert tuple(actions[subject.A_ID]) == tuple(actions[subject.B_ID])
    assert max(target[symbol] for target in actions[subject.A_ID].values() for symbol in subject.RISK_SYMBOLS) <= 0.35
    for item in actions[subject.C_ID]:
        for symbol in subject.ALL_SYMBOLS:
            assert actions[subject.C_ID][item][symbol] == pytest.approx(
                0.5 * actions[subject.A_ID][item][symbol]
                + 0.5 * actions[subject.B_ID][item][symbol]
            )
    assert subject._divergence(actions[subject.C_ID], actions[subject.A_ID]) >= 12
    assert subject._divergence(actions[subject.C_ID], actions[subject.B_ID]) >= 12


def test_full_tournament_replays_byte_identically_and_stays_offline(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"

    first = subject.run_factor_momentum_style_tournament(first_root)
    second = subject.run_factor_momentum_style_tournament(second_root)

    assert (first_root / "evaluation_results.json").read_bytes() == (second_root / "evaluation_results.json").read_bytes()
    assert (first_root / "manifest.json").read_bytes() == (second_root / "manifest.json").read_bytes()
    assert first["replay_evidence"] == {
        "full_pipeline_replays": 2,
        "result_bytes_equal": True,
        "manifest_bytes_equal": True,
    }
    assert first["safety"]["broker_access_performed"] is False
    assert first["safety"]["paper_mutation_performed"] is False
    assert first["safety"]["live_authorized"] is False
    assert first["source_metric_trust"]["external_performance_trusted"] is False
    selected = first["tournament_decision"]["selected_shadow_winner_count"]
    assert selected in (0, 1)


def test_wrapper_blocks_credential_bearing_process_without_printing_value(tmp_path: Path) -> None:
    sentinel = "must-never-appear-v584"
    env = dict(os.environ)
    env["TIINGO_API_KEY"] = sentinel

    completed = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(SCRIPT),
            "-OutputRoot",
            str(tmp_path / "blocked"),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    combined = completed.stdout + completed.stderr
    assert completed.returncode == 2
    assert "blocked_unsafe_environment" in combined
    assert sentinel not in combined


def test_result_artifacts_are_json_objects_after_atomic_reveal(tmp_path: Path) -> None:
    subject.run_factor_momentum_style_tournament(tmp_path)

    for name in ("preregistration.json", "evaluation_results.json", "manifest.json"):
        assert isinstance(json.loads((tmp_path / name).read_text(encoding="utf-8")), dict)
