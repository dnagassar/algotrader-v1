from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.crypto_preregistered_tournament import (
    BASE_FEE_BPS,
    BASE_SLIPPAGE_BPS,
    MINIMUM_COMMON_HOURLY_BARS,
    STRESS_FEE_BPS,
    STRESS_SLIPPAGE_BPS,
    TOURNAMENT_SYMBOLS,
    _CandidateSpec,
    _aggregate_four_hour,
    _equal_weight_buy_hold_returns,
    _metrics,
    _simulate,
    build_crypto_tournament_preregistration,
    classify_crypto_tournament_candidate,
    run_crypto_preregistered_tournament,
    run_crypto_preregistered_tournament_from_csv,
)
from algotrader.research.crypto_strategy_evidence_battery import CryptoEvidenceBar

AS_OF = datetime(2026, 7, 15, 0, 0, tzinfo=UTC)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNNER = PROJECT_ROOT / "scripts" / "run_crypto_preregistered_tournament.ps1"


def test_preregistration_freezes_exactly_twelve_novel_candidates() -> None:
    first = build_crypto_tournament_preregistration()
    second = build_crypto_tournament_preregistration()

    candidate_ids = [item["candidate_id"] for item in first["candidates"]]
    assert first == second
    assert first["candidate_count"] == 12
    assert len(set(candidate_ids)) == 12
    assert all(candidate_id.startswith("crypto:tournament_v1:") for candidate_id in candidate_ids)
    assert "crypto:ADAUSD:trend_momentum_24h_repair" not in candidate_ids
    assert first["dynamic_parameter_optimization"] is False
    assert first["post_hoc_retuning"] is False
    assert first["candidate_set_mutation_allowed"] is False
    assert first["cost_policy"]["base"]["total_bps_per_transition"] == "40"
    assert first["cost_policy"]["stress"]["total_bps_per_transition"] == "80"
    assert first["preregistration_fingerprint"] == (
        "1475d35634750a7f00832f0a540fbaac3e28e7ed82ac7dbd8ef2d60e08f09097"
    )


def test_simulation_is_one_bar_lagged_and_charges_40_and_80_bps() -> None:
    timestamps = tuple(AS_OF + timedelta(hours=index) for index in range(3))
    returns = (Decimal("0"), Decimal("0.10"), Decimal("0.10"))
    targets = (Decimal("1"), Decimal("1"), Decimal("0"))

    base = _simulate(
        timestamps=timestamps,
        asset_returns=returns,
        targets=targets,
        fee_bps=BASE_FEE_BPS,
        slippage_bps=BASE_SLIPPAGE_BPS,
    )
    stress = _simulate(
        timestamps=timestamps,
        asset_returns=returns,
        targets=targets,
        fee_bps=STRESS_FEE_BPS,
        slippage_bps=STRESS_SLIPPAGE_BPS,
    )

    assert base[0].applied_exposure == 0
    assert base[0].net_return == Decimal("-0.004")
    assert base[1].applied_exposure == 1
    assert base[1].net_return == Decimal("0.10")
    assert base[2].net_return == Decimal("0.0956")
    assert stress[0].transaction_cost == Decimal("0.008")
    assert stress[2].transaction_cost == Decimal("0.008")
    assert stress[2].net_return == Decimal("0.0912")
    assert _metrics(base)["transition_count"] == 2
    assert _metrics(base)["completed_round_trips"] == 1


def test_equal_weight_benchmark_drifts_without_free_rebalancing() -> None:
    returns = _equal_weight_buy_hold_returns(
        {
            "BTCUSD": (Decimal("1"), Decimal("2"), Decimal("2")),
            "ETHUSD": (Decimal("1"), Decimal("1"), Decimal("2")),
        }
    )

    assert returns[0] == 0
    assert returns[1] == Decimal("0.5")
    assert returns[2].quantize(Decimal("0.00000001")) == Decimal("0.33333333")
    assert returns[2] != Decimal("0.5")


def test_four_hour_aggregation_requires_complete_utc_buckets() -> None:
    bars = tuple(
        CryptoEvidenceBar(
            symbol="BTCUSD",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=index),
            close=Decimal("100") + Decimal(index),
        )
        for index in range(8)
    )

    aggregated = _aggregate_four_hour(bars)
    assert [item.timestamp.hour for item in aggregated] == [3, 7]
    assert [item.close for item in aggregated] == [Decimal("103"), Decimal("107")]
    with pytest.raises(ValidationError, match="complete 4h"):
        _aggregate_four_hour(bars[:-1])
    with pytest.raises(ValidationError, match="UTC boundaries"):
        _aggregate_four_hour(bars[1:5])


def test_candidate_classifier_requires_every_preregistered_gate() -> None:
    primary = _passing_evaluation()
    robustness = _passing_evaluation()

    decision, reasons = classify_crypto_tournament_candidate(
        primary=primary,
        robustness=robustness,
        completed_round_trips_full_sample=30,
    )
    assert decision == "eligible_for_no_submit_shadow_evaluation"
    assert reasons == ()

    cases = (
        ("base_total_return", "0", "primary_base_not_positive"),
        ("stress_total_return", "0", "primary_stress_not_positive"),
        ("positive_fold_count", 2, "insufficient_positive_oos_folds"),
        (
            "positive_profit_concentration",
            "0.51",
            "positive_profit_concentration_exceeded",
        ),
        ("oos_transition_count", 19, "insufficient_oos_transitions"),
    )
    for field, value, reason in cases:
        changed = deepcopy(primary)
        changed[field] = value
        rejected, rejection_reasons = classify_crypto_tournament_candidate(
            primary=changed,
            robustness=robustness,
            completed_round_trips_full_sample=30,
        )
        assert rejected == "reject_candidate"
        assert reason in rejection_reasons

    rejected, rejection_reasons = classify_crypto_tournament_candidate(
        primary=primary,
        robustness=robustness,
        completed_round_trips_full_sample=29,
    )
    assert rejected == "reject_candidate"
    assert "insufficient_completed_round_trips" in rejection_reasons

    weak_robustness = deepcopy(robustness)
    weak_robustness["stress_total_return"] = "-0.01"
    rejected, rejection_reasons = classify_crypto_tournament_candidate(
        primary=primary,
        robustness=weak_robustness,
        completed_round_trips_full_sample=30,
    )
    assert rejected == "reject_candidate"
    assert "robustness_stress_not_positive" in rejection_reasons


def test_tournament_fails_closed_below_4320_common_hours() -> None:
    bars = _history_bars(240)
    packet = run_crypto_preregistered_tournament(
        bars,
        as_of=AS_OF,
        data_source="external_market_data",
        data_freshness="frozen_snapshot",
    )

    assert packet["classification"] == "insufficient_or_invalid_history"
    assert set(packet["coverage_errors"]) == {
        f"insufficient_rows:{symbol}" for symbol in TOURNAMENT_SYMBOLS
    }
    assert packet["market_data_fetch_occurred"] is False
    assert packet["broker_mutation_occurred"] is False


@pytest.fixture(scope="module")
def full_tournament_packet() -> dict[str, object]:
    return run_crypto_preregistered_tournament(
        _history_bars(MINIMUM_COMMON_HOURLY_BARS),
        as_of=AS_OF,
        data_source="external_market_data",
        data_freshness="frozen_snapshot",
    )


def test_full_tournament_uses_four_untouched_folds_and_all_safety_flags(
    full_tournament_packet: dict[str, object],
) -> None:
    packet = full_tournament_packet
    assert packet["classification"] == "unbound_input_not_eligible"
    assert packet["refresh_provenance_status"] == "unbound"
    assert packet["history_contract"]["selected_hourly_bars_per_symbol"] == 4320
    assert packet["history_contract"]["selected_4h_bars_per_symbol"] == 1080
    assert packet["history_contract"]["discovery_hourly_bars"] == 2592
    assert len(packet["oos_windows"]) == 4
    assert {item["hourly_bar_count"] for item in packet["oos_windows"]} == {432}
    assert len(packet["candidate_evaluations"]) == 12
    assert packet["paper_planning_eligibility"] == "not_eligible"
    assert packet["broker_execution_eligibility"] == "not_eligible"
    for field in (
        "network_access_attempted",
        "market_data_fetch_occurred",
        "broker_read_occurred",
        "broker_mutation_authorized",
        "broker_mutation_occurred",
        "paper_submit_authorized",
        "paper_submit_occurred",
        "live_authorized",
        "live_endpoint_touched",
        "credential_values_exposed",
    ):
        assert packet[field] is False
    assert all(
        len(item["primary"]["folds"]) == 4
        and item["primary"]["oos_bar_count"] == 1728
        and item["robustness"]["oos_bar_count"] == 432
        and item["paper_or_broker_eligible"] is False
        for item in packet["candidate_evaluations"]
    )


def test_tournament_packet_is_deterministically_ranked(
    full_tournament_packet: dict[str, object],
) -> None:
    packet = full_tournament_packet
    manifest = build_crypto_tournament_preregistration()
    assert packet["preregistration_fingerprint"] == manifest["preregistration_fingerprint"]
    assert packet["ranking"] == [
        item["candidate_id"] for item in packet["candidate_evaluations"]
    ]
    assert len(packet["normalized_snapshot_sha256"]) == 64


def test_csv_intake_rejects_duplicate_and_untrusted_source_rows(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.csv"
    duplicate.write_text(
        "timestamp,symbol,asset_class,open,high,low,close,volume,basis,source\n"
        "2026-01-01T00:00:00Z,BTCUSD,crypto,1,1,1,1,1,alpaca_crypto_bars_v1beta3_ohlcv,alpaca_market_data_crypto_bars_v1beta3\n"
        "2026-01-01T00:00:00Z,BTCUSD,crypto,1,1,1,1,1,alpaca_crypto_bars_v1beta3_ohlcv,alpaca_market_data_crypto_bars_v1beta3\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="duplicate"):
        run_crypto_preregistered_tournament_from_csv(
            duplicate,
            refresh_packet_path=tmp_path / "missing.json",
            as_of=AS_OF,
        )

    fixture = tmp_path / "fixture.csv"
    fixture.write_text(
        "timestamp,symbol,asset_class,open,high,low,close,volume,basis,source\n"
        "2026-01-01T00:00:00Z,BTCUSD,crypto,1,1,1,1,1,alpaca_crypto_bars_v1beta3_ohlcv,offline_fixture\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="source is not"):
        run_crypto_preregistered_tournament_from_csv(
            fixture,
            refresh_packet_path=tmp_path / "missing.json",
            as_of=AS_OF,
        )


def test_refresh_receipt_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    input_path = tmp_path / "history.csv"
    _write_canonical_csv(input_path, count=1)
    packet_path = tmp_path / "refresh.json"
    refresh = _refresh_packet(input_path, output_sha256="0" * 64, rows=4320)
    packet_path.write_text(json.dumps(refresh), encoding="utf-8")

    with pytest.raises(ValidationError, match="SHA-256 mismatch"):
        run_crypto_preregistered_tournament_from_csv(
            input_path,
            refresh_packet_path=packet_path,
            as_of=AS_OF,
        )


def test_bound_refresh_receipt_can_produce_authoritative_classification(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "history.csv"
    _write_canonical_csv(input_path, count=MINIMUM_COMMON_HOURLY_BARS)
    input_hash = hashlib.sha256(input_path.read_bytes()).hexdigest()
    packet_path = tmp_path / "refresh.json"
    packet_path.write_text(
        json.dumps(
            _refresh_packet(
                input_path,
                output_sha256=input_hash,
                rows=MINIMUM_COMMON_HOURLY_BARS,
            )
        ),
        encoding="utf-8",
    )

    packet = run_crypto_preregistered_tournament_from_csv(
        input_path,
        refresh_packet_path=packet_path,
        as_of=AS_OF,
    )

    assert packet["refresh_provenance_status"] == "passed"
    assert packet["refresh_provenance"]["input_sha256"] == input_hash
    assert packet["classification"] in {
        "no_candidate_qualified",
        "eligible_for_no_submit_shadow_evaluation",
    }
    assert packet["input_intake"]["minimum_positive_volume_fraction"] == "0.95"
    assert set(packet["input_intake"]["positive_volume_fraction_by_symbol"].values()) == {"1"}
    assert packet["input_intake"]["source_binding"] == "guarded_refresh_receipt"
    assert packet["input_intake"]["optional_provenance_columns_present"] == []
    assert packet["input_intake"]["fixture_source_status"] == (
        "receipt_bound_not_present_in_normalized_csv"
    )


def test_refresh_receipt_end_is_inclusive_and_must_precede_as_of(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "history.csv"
    _write_canonical_csv(input_path, count=1)
    input_hash = hashlib.sha256(input_path.read_bytes()).hexdigest()
    packet_path = tmp_path / "refresh.json"
    refresh = _refresh_packet(input_path, output_sha256=input_hash, rows=4320)
    refresh["requested_end"] = AS_OF.isoformat()
    packet_path.write_text(json.dumps(refresh), encoding="utf-8")

    with pytest.raises(ValidationError, match="last completed hourly bar"):
        run_crypto_preregistered_tournament_from_csv(
            input_path,
            refresh_packet_path=packet_path,
            as_of=AS_OF,
        )


def test_refresh_receipt_requires_exact_schema_version(tmp_path: Path) -> None:
    input_path = tmp_path / "history.csv"
    _write_canonical_csv(input_path, count=1)
    input_hash = hashlib.sha256(input_path.read_bytes()).hexdigest()
    packet_path = tmp_path / "refresh.json"
    refresh = _refresh_packet(input_path, output_sha256=input_hash, rows=4320)
    refresh["schema_version"] = "obsolete_receipt"
    packet_path.write_text(json.dumps(refresh), encoding="utf-8")

    with pytest.raises(ValidationError, match="schema_version"):
        run_crypto_preregistered_tournament_from_csv(
            input_path,
            refresh_packet_path=packet_path,
            as_of=AS_OF,
        )


def test_normalized_adapter_csv_rejects_low_positive_volume_coverage(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "low-volume.csv"
    rows = ["timestamp,symbol,open,high,low,close,volume"]
    for bar in _history_bars(20):
        close = str(bar.close)
        volume = "0" if bar.symbol == "ADAUSD" else "1"
        rows.append(
            ",".join(
                (
                    bar.timestamp.isoformat(),
                    bar.symbol,
                    close,
                    close,
                    close,
                    close,
                    volume,
                )
            )
        )
    input_path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="positive-volume coverage.*ADAUSD"):
        run_crypto_preregistered_tournament_from_csv(
            input_path,
            refresh_packet_path=tmp_path / "missing.json",
            as_of=AS_OF,
        )


def test_runner_is_offline_local_csv_only() -> None:
    script = RUNNER.read_text(encoding="utf-8")
    assert "algotrader.research.crypto_preregistered_tournament" in script
    assert "--refresh-packet-path" in script
    assert "crypto_tournament_offline_only=true" in script
    assert "crypto_tournament_no_submit_enforced=true" in script
    assert "-MarketDataFetchAuthorized" not in script
    assert "--allow-network" not in script
    assert "--submit" not in script
    assert "ALPACA_API_KEY" not in script


def _passing_evaluation() -> dict[str, object]:
    return {
        "base_total_return": "0.10",
        "stress_total_return": "0.08",
        "base_max_drawdown": "0.05",
        "positive_fold_count": 3,
        "positive_profit_concentration": "0.40",
        "oos_transition_count": 20,
        "benchmarks": {
            "base": {
                "buy_hold_total_return": "0.04",
                "basket_total_return": "0.03",
                "buy_hold_max_drawdown": "0.10",
                "basket_max_drawdown": "0.08",
            },
            "stress": {
                "buy_hold_total_return": "0.03",
                "basket_total_return": "0.02",
                "buy_hold_max_drawdown": "0.10",
                "basket_max_drawdown": "0.08",
            },
        },
    }


def _history_bars(count: int) -> tuple[CryptoEvidenceBar, ...]:
    start = AS_OF - timedelta(hours=count)
    bars: list[CryptoEvidenceBar] = []
    for symbol_index, symbol in enumerate(TOURNAMENT_SYMBOLS):
        base = Decimal("100") + Decimal(symbol_index * 25)
        for index in range(count):
            cycle = Decimal((index % 240) - 120) / Decimal("200")
            slow_trend = Decimal(index) / Decimal("5000")
            symbol_wave = Decimal(((index + (symbol_index * 17)) % 96) - 48) / Decimal("500")
            bars.append(
                CryptoEvidenceBar(
                    symbol=symbol,
                    timestamp=start + timedelta(hours=index),
                    close=base + cycle + slow_trend + symbol_wave,
                )
            )
    return tuple(bars)


def _write_canonical_csv(path: Path, *, count: int) -> None:
    rows = ["timestamp,symbol,open,high,low,close,volume"]
    for bar in _history_bars(count):
        close = str(bar.close)
        rows.append(
            ",".join(
                (
                    bar.timestamp.isoformat(),
                    bar.symbol,
                    close,
                    close,
                    close,
                    close,
                    "1",
                )
            )
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _refresh_packet(
    input_path: Path,
    *,
    output_sha256: str,
    rows: int,
) -> dict[str, object]:
    start = AS_OF - timedelta(hours=rows)
    end = AS_OF - timedelta(hours=1)
    return {
        "schema_version": "v5_22_crypto_history_refresh_adapter_receipt_v2",
        "record_type": "crypto_history_refresh_adapter_packet",
        "mode": "market_data_fetch",
        "classification": "sufficient_real_crypto_history",
        "coverage_gate_classification": "sufficient_real_crypto_history",
        "coverage_gate_blocking_reasons": [],
        "authorization_status": "authorized",
        "endpoint_safety_status": "passed_non_live_endpoint_check",
        "data_source": "alpaca_market_data_crypto_bars_v1beta3",
        "timeframe": "1Hour",
        "loc": "us",
        "schema_validation_status": "passed",
        "requested_symbols": list(TOURNAMENT_SYMBOLS),
        "fetched_symbols": list(TOURNAMENT_SYMBOLS),
        "rows_per_symbol_after_normalization": {
            symbol: rows for symbol in TOURNAMENT_SYMBOLS
        },
        "output_path": str(input_path),
        "output_sha256": output_sha256,
        "requested_start": start.isoformat(),
        "requested_end": end.isoformat(),
        "as_of": AS_OF.isoformat(),
        "market_data_fetch_occurred": True,
        "network_access_attempted": True,
        "broker_read_occurred": False,
        "broker_mutation_authorized": False,
        "broker_mutation_occurred": False,
        "paper_submit_authorized": False,
        "paper_submit_occurred": False,
        "live_authorized": False,
        "live_endpoint_indicator": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
    }
