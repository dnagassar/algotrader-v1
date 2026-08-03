from __future__ import annotations

from datetime import date, timedelta
import json
import os
from pathlib import Path
from statistics import stdev
import subprocess

import pytest

from algotrader.errors import ValidationError
from algotrader.research import butler_source_family_tournament as subject

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_v588_butler_source_family_tournament.ps1"


def test_preregistration_is_exact_frozen_atomic_family_and_offline() -> None:
    payload = subject.build_butler_source_family_preregistration()

    assert payload["protocol_id"] == (
        "v5_88_butler_exhibit3_4_source_family_v2"
    )
    assert payload["candidate_ids"] == list(subject.CANDIDATE_IDS)
    assert payload["symbols"] == [
        "DBC", "EEM", "EWJ", "GLD", "ICF", "IEF",
        "RWX", "TLT", "VGK", "VTI", "SPY",
    ]
    assert payload["momentum_lookback_calendar_months"] == 6
    assert payload["selected_symbol_count"] == 5
    assert payload["exhibit3_selected_weight"] == "0.200000000000"
    assert payload["exhibit4_daily_volatility_sessions"] == 60
    assert (
        payload["exhibit4_volatility_estimator"]
        == "sample_standard_deviation_n_minus_1"
    )
    assert (
        payload["exhibit4_raw_weight"]
        == "0.20*(0.01/daily_standard_deviation)"
    )
    assert payload["exhibit4_individual_cap"] == "0.200000000000"
    assert payload["exhibit4_renormalized"] is False
    assert payload["unallocated_cash_return"] == "0.000000000000"
    assert payload["return_tie_rank"] == "average_ordinal_rank"
    assert payload["selection_tie_rule"] == "published_author_universe_order"
    assert payload["action_lag"] == (
        "month_end_close_t_to_next_common_close_t_plus_1"
    )
    assert payload["protocol_sha256"] == subject._PROTOCOL_HASH
    assert payload["receipt_sha256"] == subject._RECEIPT_HASH
    assert payload["data_sha256"] == subject._DATA_HASH
    assert payload["data_manifest_sha256"] == subject._MANIFEST_HASH
    assert payload["parameter_search_performed"] is False
    assert payload["source_metrics_used"] is False
    assert payload["paper_or_live_promotion_allowed"] is False
    assert payload["safety"]["network_access_performed_by_engine"] is False
    assert payload["safety"]["broker_access_performed"] is False
    assert payload["safety"]["paper_mutation_performed"] is False
    assert payload["safety"]["live_authorized"] is False


def test_average_ranks_preserve_ties_and_published_order() -> None:
    values = dict(
        zip(
            subject.CANDIDATE_SYMBOLS,
            (9.0, 9.0, 7.0, 6.0, 6.0, 6.0, 3.0, 2.0, 1.0, 0.0),
            strict=True,
        )
    )

    ranks = subject._average_ranks(values, higher_is_better=True)

    assert [ranks[symbol] for symbol in subject.CANDIDATE_SYMBOLS] == [
        1.5, 1.5, 3.0, 5.0, 5.0, 5.0, 7.0, 8.0, 9.0, 10.0,
    ]


def test_six_month_tie_selects_first_five_and_exhibit4_keeps_cash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dates = tuple(
        date(2013, 9, 1) + timedelta(days=offset)
        for offset in range((date(2014, 4, 1) - date(2013, 9, 1)).days + 1)
    )
    common_prices = [100.0]
    return_cycle = (-0.020, -0.010, 0.000, 0.010, 0.020)
    for index in range(1, len(dates)):
        common_prices.append(
            common_prices[-1] * (1.0 + return_cycle[index % 5])
        )
    path = tuple(common_prices)
    data = subject._Data(
        dates,
        {symbol: path for symbol in subject.ALL_SYMBOLS},
    )
    monkeypatch.setattr(subject, "_OOS_START", date(2014, 4, 1))
    monkeypatch.setattr(subject, "_END", date(2014, 4, 1))

    actions = subject._build_actions(data)
    exhibit3 = actions[subject.EXHIBIT3_ID][date(2014, 4, 1)]
    exhibit4 = actions[subject.EXHIBIT4_ID][date(2014, 4, 1)]
    expected_selected = set(subject.CANDIDATE_SYMBOLS[:5])
    last_returns = [
        path[index] / path[index - 1] - 1.0
        for index in range(len(path) - 61, len(path) - 1)
    ]
    expected_weight = min(0.20, 0.20 * (0.01 / stdev(last_returns)))

    assert {
        symbol
        for symbol in subject.CANDIDATE_SYMBOLS
        if exhibit3[symbol] > 0.0
    } == expected_selected
    assert {
        symbol
        for symbol in subject.CANDIDATE_SYMBOLS
        if exhibit4[symbol] > 0.0
    } == expected_selected
    assert all(
        exhibit3[symbol] == pytest.approx(0.20)
        for symbol in expected_selected
    )
    assert all(
        exhibit4[symbol] == pytest.approx(expected_weight)
        for symbol in expected_selected
    )
    assert sum(exhibit4.values()) < 1.0
    assert sum(exhibit4.values()) == pytest.approx(5.0 * expected_weight)


def test_simulator_lags_action_drifts_cash_and_charges_one_way_turnover(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dates = (
        date(2014, 3, 31),
        date(2014, 4, 1),
        date(2014, 4, 2),
        date(2014, 4, 3),
    )
    prices = {
        symbol: (100.0, 100.0, 100.0, 100.0)
        for symbol in subject.ALL_SYMBOLS
    }
    prices["DBC"] = (100.0, 200.0, 220.0, 220.0)
    target = subject._empty_target()
    target["DBC"] = 0.25
    target["EEM"] = 0.25
    monkeypatch.setattr(subject, "_OOS_START", date(2014, 4, 1))
    monkeypatch.setattr(subject, "_END", date(2014, 4, 3))

    series = subject._simulate(
        subject._Data(dates, prices),
        {dates[1]: target, dates[3]: target},
        0.0005,
    )

    assert series.turnover[0] == pytest.approx(0.5)
    assert series.returns[0] == pytest.approx(-0.00025)
    assert series.weights[0]["DBC"] == pytest.approx(0.0)
    assert series.returns[1] == pytest.approx(0.025)
    assert series.weights[1]["DBC"] == pytest.approx(0.25)
    drifted_dbc = 0.275 / 1.025
    drifted_eem = 0.25 / 1.025
    drifted_cash = 0.50 / 1.025
    expected_turnover = 0.5 * (
        abs(0.25 - drifted_dbc)
        + abs(0.25 - drifted_eem)
        + abs(0.50 - drifted_cash)
    )
    assert series.turnover[2] == pytest.approx(expected_turnover)
    for index in range(len(series.returns)):
        assert (
            sum(series.contributions[index].values())
            + series.cost_contributions[index]
            == pytest.approx(series.returns[index])
        )


def test_data_manifest_and_real_action_structure_are_exact() -> None:
    data = subject._load_data()
    actions = subject._build_actions(data)
    subject._validate_action_contract(data, actions)

    assert len(data.dates) == 4784
    assert data.dates[0] == date(2007, 7, 26)
    assert data.dates[-1] == date(2026, 7, 31)
    assert tuple(data.prices) == subject.ALL_SYMBOLS
    assert all(len(values) == 4784 for values in data.prices.values())
    for strategy_id in (
        *subject.CANDIDATE_IDS,
        subject.ABLATION_ID,
        subject.STATIC_ID,
        subject.PARENT_ID,
    ):
        assert len(actions[strategy_id]) == 148
    assert tuple(actions[subject.SPY_ID]) == (date(2014, 4, 1),)
    assert max(
        target[symbol]
        for candidate_id in subject.CANDIDATE_IDS
        for target in actions[candidate_id].values()
        for symbol in subject.CANDIDATE_SYMBOLS
    ) <= 0.20 + 1e-12


@pytest.mark.parametrize(
    ("attribute", "source", "message"),
    (
        ("_DATA", "_DATA", "canonical data SHA-256 mismatch"),
        (
            "_DATA_MANIFEST",
            "_DATA_MANIFEST",
            "canonical data manifest SHA-256 mismatch",
        ),
    ),
)
def test_tamper_blocks_before_scoring(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attribute: str,
    source: str,
    message: str,
) -> None:
    original = getattr(subject, source)
    changed = tmp_path / original.name
    changed.write_bytes(original.read_bytes() + b"\n")
    monkeypatch.setattr(subject, attribute, changed)

    with pytest.raises(ValidationError, match=message):
        subject._load_data()


def test_relative_output_path_cannot_escape_runs() -> None:
    with pytest.raises(ValidationError, match="remain beneath runs"):
        subject._local_path(Path("runs") / ".." / "src" / "escape")


def test_wrapper_blocks_credential_bearing_process_without_printing_value(
    tmp_path: Path,
) -> None:
    sentinel = "must-never-appear-v588"
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


def test_full_tournament_replays_atomically_and_stays_offline(
    tmp_path: Path,
) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"

    first = subject.run_butler_source_family_tournament(first_root)
    second = subject.run_butler_source_family_tournament(second_root)

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
    assert tuple(first["candidate_decisions"]) == subject.CANDIDATE_IDS
    assert first["tournament_decision"]["atomic_candidate_count"] == 2
    assert first["tournament_decision"]["selected_shadow_winner_count"] in (0, 1)
    assert first["safety"]["network_access_performed_by_engine"] is False
    assert first["safety"]["broker_access_performed"] is False
    assert first["safety"]["paper_mutation_performed"] is False
    assert first["safety"]["live_authorized"] is False
    assert first["source_metric_trust"]["external_performance_trusted"] is False
    for name in (
        "preregistration.json",
        "evaluation_results.json",
        "manifest.json",
    ):
        assert isinstance(
            json.loads((first_root / name).read_text(encoding="utf-8")),
            dict,
        )