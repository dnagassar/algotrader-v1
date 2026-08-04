from __future__ import annotations

from datetime import date, timedelta
import json
import math
from pathlib import Path
from statistics import stdev

import pytest

from algotrader.errors import ValidationError
from algotrader.research import nonequity_reversal_triage as subject


def _calendar(count: int) -> list[date]:
    return [date(2020, 1, 1) + timedelta(days=offset) for offset in range(count)]


def test_preregistration_is_exact_and_frozen() -> None:
    payload = subject.build_reversal_triage_preregistration()

    assert payload["protocol_id"] == "v5_93_nonequity_reversal_triage_v1"
    assert payload["markets"] == [
        "BWX", "DBA", "DBB", "DBO", "EMB", "FXA", "FXB", "FXC", "FXE",
        "FXF", "FXY", "IGOV", "MBB", "MUB", "PFF", "SLV", "UNG", "USO",
    ]
    assert payload["market_count"] == 18
    assert payload["lookback_sessions"] == 21
    assert payload["contrarian"] is True
    assert payload["warm_up_sessions"] == 22
    assert payload["decisions_per_market"] == 208
    assert payload["total_decisions"] == 208 * 18
    assert payload["primary_gate"]["required_wins"] == 13
    assert payload["secondary_gates"]["second_half_sharpe_wins_required"] == 12
    assert payload["protocol_sha256"] == subject._PROTOCOL_HASH
    assert payload["receipt_sha256"] == subject._RECEIPT_HASH
    assert payload["data_sha256"] == subject._DATA_HASH
    assert payload["data_manifest_sha256"] == subject._MANIFEST_HASH
    assert payload["validated_alpha_claimed"] is False
    assert payload["paper_or_live_promotion_allowed"] is False
    assert payload["safety"]["live_authorized"] is False


def test_binomial_tail_matches_the_preregistered_threshold() -> None:
    assert subject._binomial_tail(13, 18) == pytest.approx(0.048126220703, abs=1e-12)
    assert subject._binomial_tail(12, 18) == pytest.approx(0.118942260742, abs=1e-12)


def test_holds_only_after_a_negative_trailing_return() -> None:
    dates = _calendar(80)
    # Monotonically rising: trailing 21-session return is always positive.
    rising = [100.0 + index for index in range(80)]

    actions = subject._build_actions(dates, rising)

    assert actions
    assert set(actions.values()) == {0.0}


def test_holds_after_a_decline() -> None:
    dates = _calendar(80)
    falling = [200.0 - index for index in range(80)]

    actions = subject._build_actions(dates, falling)

    assert set(actions.values()) == {1.0}


def test_flat_series_is_not_held_because_the_test_is_strict() -> None:
    dates = _calendar(80)
    closes = [100.0] * 80

    actions = subject._build_actions(dates, closes)

    # A trailing return of exactly zero is not "below zero".
    assert set(actions.values()) == {0.0}


def test_signal_is_the_mechanical_opposite_of_trend_following() -> None:
    """V5.91 held rising markets; this holds falling ones. Same data, inverse."""

    dates = _calendar(80)
    rising = [100.0 + index for index in range(80)]
    falling = [200.0 - index for index in range(80)]

    up = subject._build_actions(dates, rising)
    down = subject._build_actions(dates, falling)

    assert set(up.values()) == {0.0}
    assert set(down.values()) == {1.0}
    assert set(up) == set(down)


def test_simulator_lags_actions_and_charges_one_way_turnover() -> None:
    dates = _calendar(64)
    # The +10% move lands on the session after the action, so the lag is visible.
    closes = [100.0] * 23 + [110.0] * 41
    scored = dates[22:]

    series = subject._simulate(dates, closes, {scored[0]: 1.0}, 0.0005)

    assert series.dates == tuple(scored)
    assert series.turnover[0] == pytest.approx(1.0)
    assert series.returns[0] == pytest.approx(-0.0005)
    assert series.returns[1] == pytest.approx(0.10)


def test_cash_position_earns_nothing() -> None:
    dates = _calendar(64)
    closes = [100.0] * 62 + [110.0, 110.0]
    scored = dates[22:]

    series = subject._simulate(dates, closes, {scored[0]: 0.0}, 0.0)

    assert series.turnover[0] == pytest.approx(0.0)
    assert all(value == pytest.approx(0.0) for value in series.returns)


def test_second_half_split_is_deterministic_and_uses_no_chosen_date() -> None:
    dates = _calendar(64)
    closes = [100.0 + index * 0.5 for index in range(64)]
    series = subject._simulate(dates, closes, {dates[22]: 1.0}, 0.0)

    metrics = subject._window_metrics(series)

    total = len(series.returns)
    assert metrics["full"]["session_count"] == total
    assert metrics["second_half"]["session_count"] == total - total // 2
    assert metrics["second_half"]["start"] == series.dates[total // 2].isoformat()


def test_real_panel_structure_matches_the_frozen_contract() -> None:
    dates, prices = subject._load_data()

    assert len(dates) == 4403
    assert dates[0] == date(2009, 1, 29)
    assert dates[-1] == date(2026, 7, 31)
    assert tuple(prices) == subject.MARKETS
    for market in subject.MARKETS:
        actions = subject._build_actions(dates, prices[market])
        assert len(actions) == 208
        assert all(value in (0.0, 1.0) for value in actions.values())


@pytest.mark.parametrize(
    ("attribute", "message"),
    (
        ("_DATA", "canonical data SHA-256 mismatch"),
        ("_DATA_MANIFEST", "canonical data manifest SHA-256 mismatch"),
    ),
)
def test_tamper_blocks_before_scoring(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attribute: str,
    message: str,
) -> None:
    original = getattr(subject, attribute)
    changed = tmp_path / original.name
    changed.write_bytes(original.read_bytes() + b"\n")
    monkeypatch.setattr(subject, attribute, changed)

    with pytest.raises(ValidationError, match=message):
        subject._load_data()


def test_relative_output_path_cannot_escape_runs() -> None:
    with pytest.raises(ValidationError, match="remain beneath runs"):
        subject._local_path(Path("runs") / ".." / "src" / "escape")


def test_full_triage_replays_atomically_and_stays_offline(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"

    first = subject.run_nonequity_reversal_triage(first_root)
    second = subject.run_nonequity_reversal_triage(second_root)

    assert (
        (first_root / "evaluation_results.json").read_bytes()
        == (second_root / "evaluation_results.json").read_bytes()
    )
    cross = first["cross_section"]
    assert cross["market_count"] == 18
    assert 0 <= cross["sharpe_wins"] <= 18
    assert float(cross["one_sided_binomial_p"]) == pytest.approx(
        subject._binomial_tail(int(cross["sharpe_wins"]), 18), abs=1e-12
    )
    assert first["route"] in (
        "cross_sectional_evidence_supports_forward_shadow_registration",
        "close_triage_without_tuning",
    )
    assert first["validated_alpha_claimed"] is False
    assert first["historical_not_forward_evidence"] is True
    assert first["paper_promotion_allowed"] is False
    assert first["live_authorized"] is False
    assert first["safety"]["network_access_performed_by_engine"] is False
    for name in ("preregistration.json", "evaluation_results.json", "manifest.json"):
        assert isinstance(
            json.loads((first_root / name).read_text(encoding="utf-8")), dict
        )
