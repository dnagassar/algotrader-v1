from __future__ import annotations

from datetime import date, timedelta
import json
import math
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research import vault_cross_sectional_trend_triage as subject


def test_preregistration_is_exact_and_frozen() -> None:
    payload = subject.build_vault_triage_preregistration()

    assert payload["protocol_id"] == "v5_91_vault_cross_sectional_trend_triage_v1"
    assert payload["markets"] == [
        "EWA", "EWC", "EWD", "EWG", "EWH", "EWI", "EWK", "EWL", "EWM",
        "EWN", "EWO", "EWP", "EWQ", "EWS", "EWU", "EWW", "EWY", "EWZ",
    ]
    assert payload["market_count"] == 18
    assert payload["warm_up_sessions"] == 200
    assert payload["decisions_per_market"] == 303
    assert payload["total_decisions"] == 303 * 18
    assert payload["primary_gate"]["required_wins"] == 13
    assert payload["primary_gate"]["independence_assumed_and_overstated"] is True
    assert payload["secondary_gates"]["post_2007_sharpe_wins_required"] == 12
    assert payload["protocol_sha256"] == subject._PROTOCOL_HASH
    assert payload["receipt_sha256"] == subject._RECEIPT_HASH
    assert payload["data_sha256"] == subject._DATA_HASH
    assert payload["data_manifest_sha256"] == subject._MANIFEST_HASH
    assert payload["validated_alpha_claimed"] is False
    assert payload["paper_or_live_promotion_allowed"] is False
    assert payload["safety"]["live_authorized"] is False
    assert payload["safety"]["network_access_performed_by_engine"] is False


def test_binomial_tail_matches_the_preregistered_threshold() -> None:
    # The primary gate's whole justification: 13 of 18 is p < 0.05, 12 is not.
    assert subject._binomial_tail(13, 18) == pytest.approx(0.048126220703, abs=1e-12)
    assert subject._binomial_tail(12, 18) == pytest.approx(0.118942260742, abs=1e-12)
    assert subject._binomial_tail(18, 18) == pytest.approx(1.0 / 2**18)


def test_signal_is_strict_and_uses_a_full_trailing_window() -> None:
    # 260 sessions across two months; a rising then falling path.
    dates = [date(2020, 1, 1) + timedelta(days=offset) for offset in range(260)]
    closes = [100.0 + offset for offset in range(260)]

    actions = subject._build_actions(dates, closes)

    # Only month-ends at or beyond the 200-session warm-up produce actions.
    assert actions
    assert all(value in (0.0, 1.0) for value in actions.values())
    # A monotonically rising series is always above its trailing average.
    assert set(actions.values()) == {1.0}

    falling = [100.0 - offset * 0.1 for offset in range(260)]
    falling_actions = subject._build_actions(dates, falling)
    assert set(falling_actions.values()) == {0.0}


def test_flat_series_is_not_on_because_the_test_is_strict() -> None:
    dates = [date(2020, 1, 1) + timedelta(days=offset) for offset in range(260)]
    closes = [100.0] * 260

    actions = subject._build_actions(dates, closes)

    # close == average is not "above" the average.
    assert set(actions.values()) == {0.0}


def test_simulator_lags_actions_and_charges_one_way_turnover() -> None:
    dates = [date(2020, 1, 1) + timedelta(days=offset) for offset in range(203)]
    closes = [100.0] * 201 + [110.0, 110.0]
    scored = dates[200:]
    actions = {scored[0]: 1.0}

    series = subject._simulate(dates, closes, actions, 0.0005)

    assert series.dates == tuple(scored)
    # First scored session: enters from flat, earns nothing, pays full turnover.
    assert series.turnover[0] == pytest.approx(1.0)
    assert series.returns[0] == pytest.approx(-0.0005)
    # Second session: fully invested through the +10% move.
    assert series.returns[1] == pytest.approx(0.10)


def test_simulator_rejects_targets_outside_the_unit_interval() -> None:
    dates = [date(2020, 1, 1) + timedelta(days=offset) for offset in range(203)]
    closes = [100.0] * 203

    with pytest.raises(ValidationError, match="unit interval"):
        subject._simulate(dates, closes, {dates[200]: 1.5}, 0.0)


def test_pearson_is_exact_for_identical_and_opposite_series() -> None:
    left = [0.01, -0.02, 0.03, -0.01]
    assert subject._pearson(left, left) == pytest.approx(1.0)
    assert subject._pearson(left, [-value for value in left]) == pytest.approx(-1.0)
    assert subject._pearson(left, [0.0, 0.0, 0.0, 0.0]) is None


def test_real_panel_structure_matches_the_frozen_contract() -> None:
    dates, prices = subject._load_data()

    assert len(dates) == 6550
    assert dates[0] == date(2000, 7, 14)
    assert dates[-1] == date(2026, 7, 31)
    assert tuple(prices) == subject.MARKETS
    assert all(len(series) == 6550 for series in prices.values())
    for market in subject.MARKETS:
        actions = subject._build_actions(dates, prices[market])
        assert len(actions) == 303
        assert min(actions) == date(2001, 5, 1)


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

    first = subject.run_vault_cross_sectional_trend_triage(first_root)
    second = subject.run_vault_cross_sectional_trend_triage(second_root)

    assert (
        (first_root / "evaluation_results.json").read_bytes()
        == (second_root / "evaluation_results.json").read_bytes()
    )
    assert (
        (first_root / "manifest.json").read_bytes()
        == (second_root / "manifest.json").read_bytes()
    )
    cross = first["cross_section"]
    assert cross["market_count"] == 18
    assert 0 <= cross["sharpe_wins"] <= 18
    assert 0 <= cross["drawdown_wins"] <= 18
    assert cross["independence_assumed_and_overstated"] is True
    assert first["route"] in (
        "cross_sectional_evidence_supports_forward_shadow_registration",
        "close_triage_without_tuning",
    )
    # A triage can never claim validated alpha or authorize anything.
    assert first["validated_alpha_claimed"] is False
    assert first["historical_not_forward_evidence"] is True
    assert first["paper_promotion_allowed"] is False
    assert first["live_authorized"] is False
    assert first["safety"]["network_access_performed_by_engine"] is False
    assert first["safety"]["broker_access_performed"] is False
    for name in ("preregistration.json", "evaluation_results.json", "manifest.json"):
        assert isinstance(
            json.loads((first_root / name).read_text(encoding="utf-8")), dict
        )


def test_binomial_p_is_consistent_with_the_reported_win_count(
    tmp_path: Path,
) -> None:
    result = subject.run_vault_cross_sectional_trend_triage(tmp_path / "run")
    cross = result["cross_section"]

    expected = subject._binomial_tail(int(cross["sharpe_wins"]), 18)
    assert float(cross["one_sided_binomial_p"]) == pytest.approx(expected, abs=1e-12)
    assert result["gates"]["primary_sharpe_wins_at_least_13"] is (
        int(cross["sharpe_wins"]) >= 13
    )
    assert math.isfinite(float(cross["mean_pairwise_excess_correlation"]))
