from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import subprocess

import pytest

from algotrader.errors import ValidationError
from algotrader.research import clare_risk_parity_trend_tournament as subject

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_v586_clare_risk_parity_trend_tournament.ps1"


def test_preregistration_is_frozen_and_offline() -> None:
    payload = subject.build_clare_risk_parity_trend_preregistration()

    assert payload["candidate_ids"] == [subject.CANDIDATE_ID]
    assert payload["volatility_lookback_monthly_returns"] == 12
    assert payload["trend_lookback_month_end_levels"] == 10
    assert payload["trend_rule"] == "strictly_above_arithmetic_mean"
    assert payload["survivor_renormalization"] is False
    assert (
        payload["action_lag"]
        == "month_end_close_t_to_next_common_close_t_plus_1"
    )
    assert payload["parameter_search_performed"] is False
    assert payload["source_metrics_used"] is False
    assert payload["paper_or_live_promotion_allowed"] is False
    assert payload["safety"]["network_access_performed_by_engine"] is False
    assert payload["safety"]["live_authorized"] is False


def test_simulator_does_not_earn_action_close_return() -> None:
    dates = (date(2016, 3, 31), date(2016, 4, 1), date(2016, 4, 4))
    prices = {
        symbol: (100.0, 100.0, 100.0) for symbol in subject.ALL_SYMBOLS
    }
    prices["URTH"] = (100.0, 200.0, 220.0)
    target = subject._empty_target()
    target["URTH"] = 1.0

    series = subject._simulate(
        subject._Data(dates, prices),
        {dates[1]: target},
        0.0005,
    )

    assert series.returns[0] == pytest.approx(-0.0005)
    assert series.returns[1] == pytest.approx(0.10)
    assert series.turnover[0] == pytest.approx(1.0)
    assert series.weights[0]["URTH"] == pytest.approx(0.0)
    assert (
        sum(series.contributions[0].values())
        + series.cost_contributions[0]
        == pytest.approx(series.returns[0])
    )


def test_simulator_drifts_holdings_and_charges_rebalance_turnover() -> None:
    dates = (
        date(2016, 3, 31),
        date(2016, 4, 1),
        date(2016, 4, 4),
        date(2016, 4, 5),
    )
    prices = {
        symbol: (100.0, 100.0, 100.0, 100.0)
        for symbol in subject.ALL_SYMBOLS
    }
    prices["URTH"] = (100.0, 100.0, 110.0, 110.0)
    target = subject._empty_target()
    target["URTH"] = 0.5
    target["VWO"] = 0.5

    series = subject._simulate(
        subject._Data(dates, prices),
        {dates[1]: target, dates[3]: target},
        0.0,
    )

    assert series.weights[0]["URTH"] == pytest.approx(0.0)
    assert series.weights[1]["URTH"] == pytest.approx(0.5)
    assert series.weights[1]["VWO"] == pytest.approx(0.5)
    assert series.weights[2]["URTH"] == pytest.approx(0.55 / 1.05)
    assert series.weights[2]["VWO"] == pytest.approx(0.50 / 1.05)
    assert series.turnover[2] == pytest.approx(abs(0.55 / 1.05 - 0.5))


def test_actual_targets_use_exact_lag_and_transfer_to_bil() -> None:
    data = subject._load_data()
    actions = subject._build_actions(data)

    candidate = actions[subject.CANDIDATE_ID]
    ablation = actions[subject.ABLATION_ID]
    assert min(candidate) == date(2016, 4, 1)
    assert tuple(candidate) == tuple(ablation)
    assert subject._divergence(candidate, ablation) >= 12
    for item in candidate:
        assert candidate[item]["BIL"] == pytest.approx(
            1.0
            - sum(candidate[item][symbol] for symbol in subject.RISK_SYMBOLS)
        )
        assert ablation[item]["BIL"] == pytest.approx(0.0)
        for symbol in subject.RISK_SYMBOLS:
            assert candidate[item][symbol] == pytest.approx(
                0.0 if candidate[item][symbol] == 0.0 else ablation[item][symbol]
            )


def test_data_hash_mismatch_blocks_before_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    changed = tmp_path / "changed.csv"
    changed.write_bytes(subject._DATA.read_bytes() + b"\n")
    monkeypatch.setattr(subject, "_DATA", changed)

    with pytest.raises(ValidationError, match="canonical data SHA-256 mismatch"):
        subject._load_data()


def test_full_tournament_replays_byte_identically_and_stays_offline(
    tmp_path: Path,
) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"

    first = subject.run_clare_risk_parity_trend_tournament(first_root)
    second = subject.run_clare_risk_parity_trend_tournament(second_root)

    assert (
        (first_root / "evaluation_results.json").read_bytes()
        == (second_root / "evaluation_results.json").read_bytes()
    )
    assert (
        (first_root / "manifest.json").read_bytes()
        == (second_root / "manifest.json").read_bytes()
    )
    assert first["replay_evidence"] == {
        "full_pipeline_replays": 2,
        "result_bytes_equal": True,
        "manifest_bytes_equal": True,
    }
    assert first["safety"]["broker_access_performed"] is False
    assert first["safety"]["paper_mutation_performed"] is False
    assert first["safety"]["live_authorized"] is False
    assert first["source_metric_trust"]["external_performance_trusted"] is False
    assert first["tournament_decision"]["selected_shadow_winner_count"] in (0, 1)


def test_wrapper_blocks_credential_bearing_process_without_printing_value(
    tmp_path: Path,
) -> None:
    sentinel = "must-never-appear-v586"
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


def test_result_artifacts_are_json_objects_after_atomic_reveal(
    tmp_path: Path,
) -> None:
    subject.run_clare_risk_parity_trend_tournament(tmp_path)

    for name in (
        "preregistration.json",
        "evaluation_results.json",
        "manifest.json",
    ):
        assert isinstance(
            json.loads((tmp_path / name).read_text(encoding="utf-8")),
            dict,
        )