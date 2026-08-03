from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import subprocess

import pytest

from algotrader.errors import ValidationError
from algotrader.research import keller_flexible_asset_allocation_tournament as subject

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_v587_keller_flexible_asset_allocation_tournament.ps1"


def test_preregistration_is_frozen_and_offline() -> None:
    payload = subject.build_keller_flexible_asset_allocation_preregistration()

    assert payload["protocol_id"] == "v5_87_keller_faa_v3"
    assert payload["candidate_ids"] == [subject.CANDIDATE_ID]
    assert payload["symbols"] == [
        "VTI",
        "VEA",
        "VWO",
        "SHY",
        "BND",
        "GSG",
        "VNQ",
        "SPY",
        "IEF",
    ]
    assert payload["lookback_calendar_months"] == 4
    assert payload["daily_volatility_estimator"] == "sample_standard_deviation_n_minus_1"
    assert payload["correlation_estimator"] == "sample_pearson_daily_returns"
    assert payload["score_weights"] == {
        "return_rank": "1.000000000000",
        "volatility_rank": "0.500000000000",
        "correlation_rank": "0.500000000000",
    }
    assert payload["selected_symbol_count"] == 3
    assert payload["selected_weight"] == "0.333333333333"
    assert payload["factor_tie_rule"] == "average_ordinal_rank"
    assert payload["candidate_score_tie_rule"] == "published_etf_order"
    assert payload["ablation_return_tie_rule"] == "published_etf_order"
    assert payload["negative_return_substitute"] == "SHY"
    assert payload["action_lag"] == "month_end_close_t_to_next_common_close_t_plus_1"
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


def test_average_ranks_and_pearson_are_exact() -> None:
    values = dict(
        zip(subject.CANDIDATE_SYMBOLS, (9.0, 9.0, 7.0, 6.0, 6.0, 6.0, 1.0), strict=True)
    )

    high = subject._average_ranks(values, higher_is_better=True)
    low = subject._average_ranks(values, higher_is_better=False)

    assert [high[symbol] for symbol in subject.CANDIDATE_SYMBOLS] == [
        1.5,
        1.5,
        3.0,
        5.0,
        5.0,
        5.0,
        7.0,
    ]
    assert [low[symbol] for symbol in subject.CANDIDATE_SYMBOLS] == [
        6.5,
        6.5,
        5.0,
        3.0,
        3.0,
        3.0,
        1.0,
    ]
    assert subject._pearson((1.0, 2.0, 4.0), (2.0, 4.0, 8.0)) == pytest.approx(1.0)
    assert subject._pearson((1.0, 2.0, 4.0), (-2.0, -4.0, -8.0)) == pytest.approx(-1.0)
    with pytest.raises(ValidationError, match="align"):
        subject._pearson((1.0, 2.0), (1.0,))
    with pytest.raises(ValidationError, match="denominator"):
        subject._pearson((1.0, 1.0), (2.0, 3.0))


@pytest.mark.parametrize(
    ("january_close", "expected_shy"),
    ((100.0, 0.0), (99.0, 1.0)),
)
def test_four_month_boundary_final_tie_and_strict_negative_shy_transfer(
    monkeypatch: pytest.MonkeyPatch,
    january_close: float,
    expected_shy: float,
) -> None:
    dates = (
        date(2012, 8, 31),
        date(2012, 9, 28),
        date(2012, 10, 31),
        date(2012, 11, 30),
        date(2012, 12, 31),
        date(2013, 1, 31),
        date(2013, 2, 1),
    )
    path = (200.0, 100.0, 110.0, 100.0, 120.0, january_close, january_close)
    data = subject._Data(dates, {symbol: path for symbol in subject.ALL_SYMBOLS})
    monkeypatch.setattr(subject, "_OOS_START", date(2013, 2, 1))
    monkeypatch.setattr(subject, "_END", date(2013, 2, 1))

    actions = subject._build_actions(data)
    target = actions[subject.CANDIDATE_ID][date(2013, 2, 1)]

    assert target["SHY"] == pytest.approx(expected_shy)
    for symbol in ("VTI", "VEA", "VWO"):
        assert target[symbol] == pytest.approx(0.0 if expected_shy else 1.0 / 3.0)
    assert sum(target.values()) == pytest.approx(1.0)


def test_simulator_uses_t_plus_1_close_then_drifts_and_charges_turnover(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dates = (
        date(2013, 1, 31),
        date(2013, 2, 1),
        date(2013, 2, 4),
        date(2013, 2, 5),
    )
    prices = {
        symbol: (100.0, 100.0, 100.0, 100.0)
        for symbol in subject.ALL_SYMBOLS
    }
    prices["VTI"] = (100.0, 200.0, 220.0, 220.0)
    target = subject._empty_target()
    target["VTI"] = 0.5
    target["VEA"] = 0.5
    monkeypatch.setattr(subject, "_OOS_START", date(2013, 2, 1))
    monkeypatch.setattr(subject, "_END", date(2013, 2, 5))

    series = subject._simulate(
        subject._Data(dates, prices),
        {dates[1]: target, dates[3]: target},
        0.0005,
    )

    assert series.returns[0] == pytest.approx(-0.0005)
    assert series.returns[1] == pytest.approx(0.05)
    assert series.turnover[0] == pytest.approx(1.0)
    assert series.weights[0]["VTI"] == pytest.approx(0.0)
    assert series.weights[1]["VTI"] == pytest.approx(0.5)
    assert series.weights[2]["VTI"] == pytest.approx(0.55 / 1.05)
    assert series.weights[2]["VEA"] == pytest.approx(0.50 / 1.05)
    assert series.turnover[2] == pytest.approx(abs(0.55 / 1.05 - 0.5))
    for index in range(len(series.returns)):
        assert (
            sum(series.contributions[index].values())
            + series.cost_contributions[index]
            == pytest.approx(series.returns[index])
        )


def test_data_and_manifest_pins_admit_exact_panel() -> None:
    data = subject._load_data()

    assert len(data.dates) == 4784
    assert data.dates[0] == date(2007, 7, 26)
    assert data.dates[-1] == date(2026, 7, 31)
    assert tuple(data.prices) == subject.ALL_SYMBOLS
    assert all(len(values) == 4784 for values in data.prices.values())


@pytest.mark.parametrize(
    ("attribute", "source", "message"),
    (
        ("_DATA", "_DATA", "canonical data SHA-256 mismatch"),
        ("_DATA_MANIFEST", "_DATA_MANIFEST", "canonical data manifest SHA-256 mismatch"),
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
    sentinel = "must-never-appear-v587"
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


def test_full_tournament_replays_byte_identically_and_stays_offline(
    tmp_path: Path,
) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"

    first = subject.run_keller_flexible_asset_allocation_tournament(first_root)
    second = subject.run_keller_flexible_asset_allocation_tournament(second_root)

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
    assert first["safety"]["network_access_performed_by_engine"] is False
    assert first["safety"]["broker_access_performed"] is False
    assert first["safety"]["paper_mutation_performed"] is False
    assert first["safety"]["live_authorized"] is False
    assert first["source_metric_trust"]["external_performance_trusted"] is False
    assert first["tournament_decision"]["selected_shadow_winner_count"] in (0, 1)
    for name in ("preregistration.json", "evaluation_results.json", "manifest.json"):
        assert isinstance(json.loads((first_root / name).read_text(encoding="utf-8")), dict)
