from __future__ import annotations

from datetime import date, timedelta
import json
import math
import os
from pathlib import Path
import subprocess

import pytest

from algotrader.errors import ValidationError
from algotrader.research import baa_tournament as subject

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_v589_baa_tournament.ps1"


def test_preregistration_is_exact_frozen_atomic_family_and_offline() -> None:
    payload = subject.build_baa_preregistration()

    assert payload["protocol_id"] == "v5_89_keller_bold_asset_allocation_v1"
    assert payload["candidate_ids"] == [
        "baa_g4_aggressive_proxy",
        "baa_g12_balanced_proxy",
    ]
    assert payload["symbols"] == [
        "SPY", "QQQ", "IWM", "VGK", "EWJ", "EEM", "VNQ", "DBC", "GLD",
        "TLT", "HYG", "LQD", "EFA", "AGG", "TIP", "BIL", "IEF",
    ]
    assert payload["canary_symbols"] == ["SPY", "EFA", "EEM", "AGG"]
    assert payload["g4_offensive_symbols"] == ["QQQ", "EEM", "EFA", "AGG"]
    assert payload["g12_offensive_symbols"] == [
        "SPY", "QQQ", "IWM", "VGK", "EWJ", "EEM", "VNQ", "DBC", "GLD",
        "TLT", "HYG", "LQD",
    ]
    assert payload["defensive_symbols"] == [
        "TIP", "DBC", "BIL", "IEF", "TLT", "LQD", "AGG",
    ]
    assert payload["canary_momentum"] == "13612W_monthly_close"
    assert (
        payload["canary_breadth_rule"]
        == "any_nonpositive_canary_momentum_is_defensive"
    )
    assert (
        payload["relative_momentum"]
        == "p0_over_mean_p0_through_p12_monthly_close"
    )
    assert payload["g4_offensive_selection"] == "top_1_weight_1_000000000000"
    assert payload["g12_offensive_selection"] == "top_6_weight_one_sixth_each"
    assert payload["defensive_selection"] == "top_3_weight_one_third_each"
    assert payload["offensive_cash_substitution"] == "none"
    assert payload["oos_start"] == "2022-09-01"
    assert payload["oos_end"] == "2026-07-31"
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


def test_13612w_momentum_is_exact_weighted_combination() -> None:
    closes = [100.0] * 13
    closes[1] = 90.0
    closes[3] = 80.0
    closes[6] = 50.0
    closes[12] = 25.0

    value = subject._momentum_13612w(closes)

    expected = (
        12.0 * (100.0 / 90.0 - 1.0)
        + 4.0 * (100.0 / 80.0 - 1.0)
        + 2.0 * (100.0 / 50.0 - 1.0)
        + 1.0 * (100.0 / 25.0 - 1.0)
    )
    assert value == pytest.approx(expected)


def test_relative_momentum_is_p0_over_thirteen_close_mean() -> None:
    closes = [110.0] + [100.0] * 12

    value = subject._relative_momentum(closes)

    assert value == pytest.approx(110.0 / (sum(closes) / len(closes)))


def test_top_selection_resolves_ties_by_frozen_universe_order() -> None:
    values = {symbol: 1.0 for symbol in subject.G12_OFFENSIVE_SYMBOLS}

    selected = subject._top_by_relative_momentum(
        values, subject.G12_OFFENSIVE_SYMBOLS, 6
    )

    assert selected == subject.G12_OFFENSIVE_SYMBOLS[:6]


def _flat_monthly_data(
    months: int, per_symbol: dict[str, list[float]] | None = None
) -> subject._Data:
    """Build synthetic month-end-only session data (2 sessions per month)."""
    dates: list[date] = []
    current = date(2021, 1, 1)
    for _ in range(months):
        month_last = _month_last(current)
        dates.append(date(current.year, current.month, 15))
        dates.append(month_last)
        current = month_last + timedelta(days=1)
    prices = {}
    for symbol in subject.ALL_SYMBOLS:
        if per_symbol and symbol in per_symbol:
            monthly = per_symbol[symbol]
            series = []
            for index in range(months):
                series.extend([monthly[index], monthly[index]])
            prices[symbol] = tuple(series)
        else:
            prices[symbol] = tuple([100.0] * (2 * months))
    return subject._Data(tuple(dates), prices)


def _month_last(anchor: date) -> date:
    if anchor.month == 12:
        return date(anchor.year, 12, 31)
    return date(anchor.year, anchor.month + 1, 1) - timedelta(days=1)


def test_negative_canary_triggers_defensive_mode_with_bil_substitution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    months = 20
    data = _flat_monthly_data(
        months,
        {
            "EEM": [100.0 - 2.0 * index for index in range(months)],
            "TIP": [100.0 + 1.0 * index for index in range(months)],
            "IEF": [100.0 - 0.8 * index for index in range(months)],
            "LQD": [100.0 - 1.0 * index for index in range(months)],
            "TLT": [100.0 - 1.5 * index for index in range(months)],
            "DBC": [100.0 - 1.2 * index for index in range(months)],
            "AGG": [100.0 - 0.5 * index for index in range(months)],
        },
    )
    action_date = data.dates[-2]
    monkeypatch.setattr(subject, "_OOS_START", action_date)
    monkeypatch.setattr(subject, "_END", action_date)

    actions, modes = subject._build_actions(data)

    # Top-3 defensive by relative momentum: TIP (rising), BIL (flat), AGG
    # (least-falling). AGG ranks below BIL, so its third moves to cash.
    assert modes[action_date] == "defensive"
    g4 = actions[subject.G4_ID][action_date]
    held = {symbol for symbol in subject.ALL_SYMBOLS if g4[symbol] > 0.0}
    assert held == {"TIP", "BIL"}
    assert g4["TIP"] == pytest.approx(1.0 / 3.0)
    assert g4["BIL"] == pytest.approx(1.0 / 3.0)
    assert sum(g4.values()) == pytest.approx(2.0 / 3.0)
    assert actions[subject.G12_ID][action_date] == g4
    ablation = actions[subject.ABLATION_G4_ID][action_date]
    assert sum(ablation.values()) == pytest.approx(1.0)


def test_positive_canaries_select_top_offensive_assets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    months = 20
    rising = {
        symbol: [100.0 + 3.0 * index for index in range(months)]
        for symbol in subject.ALL_SYMBOLS
    }
    rising["QQQ"] = [100.0 + 6.0 * index for index in range(months)]
    data = _flat_monthly_data(months, rising)
    action_date = data.dates[-2]
    monkeypatch.setattr(subject, "_OOS_START", action_date)
    monkeypatch.setattr(subject, "_END", action_date)

    actions, modes = subject._build_actions(data)

    assert modes[action_date] == "offensive"
    g4 = actions[subject.G4_ID][action_date]
    assert g4["QQQ"] == pytest.approx(1.0)
    assert sum(g4.values()) == pytest.approx(1.0)
    g12 = actions[subject.G12_ID][action_date]
    g12_held = {
        symbol for symbol in subject.ALL_SYMBOLS if g12[symbol] > 0.0
    }
    assert "QQQ" in g12_held
    assert len(g12_held) == 6
    assert all(
        g12[symbol] == pytest.approx(1.0 / 6.0) for symbol in g12_held
    )


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
    actions, modes = subject._build_actions(data)
    subject._validate_action_contract(data, actions, modes)

    assert len(data.dates) == subject._SESSION_COUNTS["all"]
    assert data.dates[0] == date(2007, 7, 26)
    assert data.dates[-1] == date(2026, 7, 31)
    assert tuple(data.prices) == subject.ALL_SYMBOLS
    for strategy_id in (
        *subject.CANDIDATE_IDS,
        subject.ABLATION_G4_ID,
        subject.ABLATION_G12_ID,
        subject.STATIC_ID,
        subject.PARENT_ID,
    ):
        assert len(actions[strategy_id]) == 47
    assert tuple(actions[subject.SPY_ID]) == (date(2022, 9, 1),)
    assert min(modes) == date(2022, 9, 1)
    assert set(modes.values()) <= {"offensive", "defensive"}


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
    sentinel = "must-never-appear-v589"
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

    first = subject.run_baa_tournament(first_root)
    second = subject.run_baa_tournament(second_root)

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
