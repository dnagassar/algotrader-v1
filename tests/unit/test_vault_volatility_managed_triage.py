from __future__ import annotations

from datetime import date, timedelta
import json
import math
from pathlib import Path
from statistics import stdev

import pytest

from algotrader.errors import ValidationError
from algotrader.research import vault_volatility_managed_triage as subject


def _calendar(count: int) -> list[date]:
    return [date(2020, 1, 1) + timedelta(days=offset) for offset in range(count)]


def test_preregistration_is_exact_and_frozen() -> None:
    payload = subject.build_volatility_triage_preregistration()

    assert payload["protocol_id"] == "v5_92_vault_volatility_managed_triage_v1"
    assert payload["markets"] == [
        "ARGT", "ECH", "EDEN", "EFNL", "EIDO", "EIRL", "EIS", "ENZL", "EPHE",
        "EPOL", "EPU", "EWT", "EZA", "GREK", "INDA", "NORW", "THD", "TUR",
    ]
    assert payload["market_count"] == 18
    assert payload["target_annualized_volatility"] == "0.150000000000"
    assert payload["volatility_window_sessions"] == 60
    assert payload["direction_consulted"] is False
    assert payload["warm_up_sessions"] == 61
    assert payload["decisions_per_market"] == 170
    assert payload["total_decisions"] == 170 * 18
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


def test_weight_is_exact_inverse_volatility_scaling() -> None:
    dates = _calendar(120)
    # Alternating +/-1% returns give a known, sizeable realized volatility.
    closes = [100.0]
    for index in range(1, 120):
        closes.append(closes[-1] * (1.01 if index % 2 else 0.99))

    actions = subject._build_actions(dates, closes)

    assert actions
    for action_date, weight in actions.items():
        index = dates.index(action_date) - 1
        window = closes[index - 60 : index + 1]
        returns = [
            window[step] / window[step - 1] - 1.0 for step in range(1, len(window))
        ]
        expected = min(
            1.0, 0.15 / (stdev(returns) * math.sqrt(252.0))
        )
        assert weight == pytest.approx(expected)
        assert 0.0 < weight <= 1.0


def test_low_volatility_is_capped_at_full_investment() -> None:
    dates = _calendar(120)
    # Tiny, steady drift: realized volatility is far below the 15% target.
    closes = [100.0 * (1.0 + 0.00001) ** index for index in range(120)]
    closes = [
        value * (1.0 + (0.000005 if index % 2 else -0.000005))
        for index, value in enumerate(closes)
    ]

    actions = subject._build_actions(dates, closes)

    assert set(round(value, 12) for value in actions.values()) == {1.0}


def test_direction_is_never_consulted(monkeypatch: pytest.MonkeyPatch) -> None:
    """The defining difference from V5.91: a calm falling market stays held."""

    dates = _calendar(120)
    closes = [100.0]
    for index in range(1, 120):
        # Steadily falling, with volatility far below the target.
        closes.append(closes[-1] * (0.999 if index % 2 else 0.998))

    actions = subject._build_actions(dates, closes)

    assert closes[-1] < closes[0]
    # Absolute trend following would be fully in cash here; this rule is not.
    assert all(value == pytest.approx(1.0) for value in actions.values())


def test_zero_volatility_blocks_rather_than_dividing_by_zero() -> None:
    dates = _calendar(120)
    closes = [100.0] * 120

    with pytest.raises(ValidationError, match="realized volatility is invalid"):
        subject._build_actions(dates, closes)


def test_simulator_lags_actions_and_charges_one_way_turnover() -> None:
    dates = _calendar(64)
    closes = [100.0] * 62 + [110.0, 110.0]
    scored = dates[61:]

    series = subject._simulate(dates, closes, {scored[0]: 1.0}, 0.0005)

    assert series.dates == tuple(scored)
    assert series.turnover[0] == pytest.approx(1.0)
    assert series.returns[0] == pytest.approx(-0.0005)
    assert series.returns[1] == pytest.approx(0.10)


def test_partial_weight_earns_a_proportional_share() -> None:
    dates = _calendar(64)
    closes = [100.0] * 62 + [110.0, 110.0]
    scored = dates[61:]

    series = subject._simulate(dates, closes, {scored[0]: 0.25}, 0.0)

    assert series.turnover[0] == pytest.approx(0.25)
    assert series.returns[1] == pytest.approx(0.025)


def test_second_half_split_is_deterministic_and_uses_no_chosen_date() -> None:
    dates = _calendar(64)
    closes = [100.0 + index * 0.5 for index in range(64)]
    series = subject._simulate(dates, closes, {dates[61]: 1.0}, 0.0)

    metrics = subject._window_metrics(series)

    total = len(series.returns)
    assert metrics["full"]["session_count"] == total
    assert metrics["second_half"]["session_count"] == total - total // 2
    assert metrics["second_half"]["start"] == series.dates[total // 2].isoformat()


def test_real_panel_structure_matches_the_frozen_contract() -> None:
    dates, prices = subject._load_data()

    assert len(dates) == 3643
    assert dates[0] == date(2012, 2, 3)
    assert dates[-1] == date(2026, 7, 31)
    assert tuple(prices) == subject.MARKETS
    for market in subject.MARKETS:
        actions = subject._build_actions(dates, prices[market])
        assert len(actions) == 170
        assert all(0.0 < value <= 1.0 for value in actions.values())


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

    first = subject.run_vault_volatility_managed_triage(first_root)
    second = subject.run_vault_volatility_managed_triage(second_root)

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
