from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from algotrader.research.crypto_preregistered_tournament import (
    build_crypto_tournament_preregistration,
)
from algotrader.research.crypto_preregistered_tournament_v2 import (
    CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT,
    DISCOVERY_EXPECTED_HOURLY_BARS,
    OOS_FOLD_COUNT,
    OOS_FOLD_HOURLY_BARS,
    OOS_HOURLY_BARS,
    TOURNAMENT_V2_SYMBOLS,
    build_crypto_tournament_v2_preregistration,
)

MODULE = Path("src/algotrader/research/crypto_preregistered_tournament_v2.py")


def test_v2_preregistration_is_pinned_before_future_oos() -> None:
    first = build_crypto_tournament_v2_preregistration()
    second = build_crypto_tournament_v2_preregistration()
    temporal = first["temporal_policy"]

    assert first == second
    assert first["preregistration_fingerprint"] == (
        CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT
    )
    assert first["preregistration_fingerprint"] == (
        "2ed9489543d8d21ab00d9f2f4000927b8012decf39882cb721cb2d1ce0b9376b"
    )
    assert datetime.fromisoformat(
        temporal["preregistration_must_be_committed_before"]
    ) == datetime(2026, 7, 16, tzinfo=UTC)
    assert temporal["oos_start"] == "2026-07-16T00:00:00+00:00"
    assert temporal["oos_end_inclusive"] == "2026-08-12T23:00:00+00:00"
    assert temporal["terminal_scoring_not_before"] == (
        "2026-08-13T00:00:00+00:00"
    )


def test_v2_has_exactly_nine_new_non_ada_candidates() -> None:
    manifest = build_crypto_tournament_v2_preregistration()
    candidates = manifest["candidates"]
    candidate_ids = [candidate["candidate_id"] for candidate in candidates]

    assert manifest["symbols"] == list(TOURNAMENT_V2_SYMBOLS)
    assert manifest["candidate_count"] == 9
    assert len(candidate_ids) == len(set(candidate_ids)) == 9
    assert all(identifier.startswith("crypto:tournament_v2:") for identifier in candidate_ids)
    assert all("ADAUSD" not in identifier for identifier in candidate_ids)
    assert {candidate["strategy_id"] for candidate in candidates} == {
        "trend_momentum_72h",
        "breakout_168h",
        "moving_average_regime_24h_168h",
    }
    assert all(len(candidate["candidate_fingerprint"]) == 64 for candidate in candidates)


def test_v1_stays_closed_and_fingerprint_distinct() -> None:
    v1 = build_crypto_tournament_preregistration()
    v2 = build_crypto_tournament_v2_preregistration()

    assert v1["candidate_count"] == 12
    assert v1["preregistration_fingerprint"] == (
        "1475d35634750a7f00832f0a540fbaac3e28e7ed82ac7dbd8ef2d60e08f09097"
    )
    assert v2["predecessor_tournament"] == {
        "version": "v1",
        "status": "closed_terminal_input_quality_gate",
        "preregistration_fingerprint":
            "1475d35634750a7f00832f0a540fbaac3e28e7ed82ac7dbd8ef2d60e08f09097",
        "candidate_reuse_allowed": False,
        "oos_reuse_allowed": False,
    }
    assert v2["preregistration_fingerprint"] != v1["preregistration_fingerprint"]


def test_v2_window_and_interim_disclosure_policy_are_exact() -> None:
    manifest = build_crypto_tournament_v2_preregistration()
    temporal = manifest["temporal_policy"]

    assert DISCOVERY_EXPECTED_HOURLY_BARS == 4320
    assert OOS_HOURLY_BARS == 672
    assert OOS_FOLD_COUNT == 4
    assert OOS_FOLD_HOURLY_BARS == 168
    assert temporal["oos_hourly_bars_per_symbol"] == 672
    assert temporal["oos_fold_4h_bars"] == 42
    assert temporal["interim_checkpoints"] == [
        "2026-07-23T00:00:00+00:00",
        "2026-07-30T00:00:00+00:00",
        "2026-08-06T00:00:00+00:00",
    ]
    assert temporal["embargo_role"] == "causal_signal_warmup_only"
    assert temporal["embargo_data_must_be_receipt_bound"] is True
    assert temporal["embargo_candidate_metrics_allowed"] is False
    assert temporal["embargo_return_scoring_allowed"] is False
    assert temporal["embargo_completed_round_trip_gate_included"] is False
    assert temporal["embargo_expected_hourly_bars_per_symbol"] == 24
    assert temporal["interim_candidate_metrics_allowed"] is False
    assert temporal["optional_stopping_allowed"] is False
    assert temporal["window_extension_allowed"] is False


def test_v2_gap_policy_is_conservative_and_frozen() -> None:
    policy = build_crypto_tournament_v2_preregistration()["data_quality_policy"]

    assert policy["minimum_raw_hourly_coverage_per_symbol"] == "0.995"
    assert policy["minimum_positive_raw_volume_fraction_per_symbol"] == "0.95"
    assert policy["maximum_consecutive_missing_hours"] == 1
    assert policy["missing_first_or_last_oos_bar_allowed"] is False
    assert policy["isolated_gap_fill"] == "prior_close_ohlc_zero_volume"
    assert policy["transition_on_imputed_hour_allowed"] is False
    assert policy["transition_on_4h_bucket_containing_imputation_allowed"] is False
    assert policy["quality_failure_extends_window"] is False


def test_v2_retains_costs_gates_and_never_authorizes_paper() -> None:
    manifest = build_crypto_tournament_v2_preregistration()
    gates = manifest["promotion_gates"]

    assert manifest["cost_policy"]["base"]["total_bps_per_transition"] == 40
    assert manifest["cost_policy"]["stress"]["total_bps_per_transition"] == 80
    assert gates["minimum_positive_oos_folds"] == 3
    assert gates["minimum_completed_round_trips_full_sample"] == 30
    assert gates["minimum_oos_transitions"] == 20
    assert gates["passing_scope"] == "eligible_for_no_submit_shadow_evaluation"
    assert gates["paper_eligibility"] is False
    assert gates["subsequent_single_winner_untouched_forward_shadow_required"] is True
    assert manifest["early_promotion_allowed"] is False
    assert manifest["paper_or_live_execution_authorized"] is False
    assert manifest["profit_claim"] == "none"


def test_v2_preregistration_module_has_no_runtime_boundary_imports() -> None:
    source = MODULE.read_text(encoding="utf-8")

    assert "algotrader.execution" not in source
    assert "algotrader.orchestration" not in source
    assert "socket" not in source
    assert "urllib" not in source
    assert "http.client" not in source
    assert "os.environ" not in source
