"""Deterministic, preregistered crypto strategy tournament.

This module is a research-only successor lane to the legacy crypto evidence
battery.  It deliberately does not mutate the legacy candidate factory or the
closed ADA repair state.  Candidate parameters, temporal windows, costs, and
promotion gates are fixed in code before long-history data is fetched.

Passing this tournament permits only no-submit shadow evaluation.  Nothing in
this module can read a trading account, submit an order, mutate a broker, or
authorize paper/live trading.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from algotrader.errors import ValidationError
from algotrader.research.crypto_strategy_evidence_battery import (
    CryptoEvidenceBar,
    load_crypto_evidence_bars_from_csv,
)

CRYPTO_PREREGISTERED_TOURNAMENT_SCHEMA_VERSION = (
    "v5_22_crypto_preregistered_tournament_v1"
)
CRYPTO_PREREGISTERED_TOURNAMENT_FACTORY_VERSION = (
    "v5_22_crypto_preregistered_candidate_factory_v1"
)
CRYPTO_PREREGISTERED_TOURNAMENT_POLICY_VERSION = (
    "v5_22_crypto_preregistered_gate_policy_v1"
)

TOURNAMENT_SYMBOLS = ("BTCUSD", "ETHUSD", "SOLUSD", "ADAUSD")
PRIMARY_TIMEFRAME = "1Hour"
ROBUSTNESS_TIMEFRAME = "4Hour"
MINIMUM_COMMON_HOURLY_BARS = 4_320
PREFERRED_COMMON_HOURLY_BARS = 8_760
OOS_HOURLY_BARS = 1_728
OOS_FOLD_COUNT = 4
OOS_FOLD_HOURLY_BARS = OOS_HOURLY_BARS // OOS_FOLD_COUNT
MINIMUM_DISCOVERY_HOURLY_BARS = (
    MINIMUM_COMMON_HOURLY_BARS - OOS_HOURLY_BARS
)
BASE_FEE_BPS = Decimal("25")
BASE_SLIPPAGE_BPS = Decimal("15")
STRESS_FEE_BPS = Decimal("50")
STRESS_SLIPPAGE_BPS = Decimal("30")
MAX_OOS_DRAWDOWN = Decimal("0.20")
MINIMUM_POSITIVE_OOS_FOLDS = 3
MAX_POSITIVE_PROFIT_CONCENTRATION = Decimal("0.50")
MINIMUM_COMPLETED_ROUND_TRIPS = 30
MINIMUM_OOS_TRANSITIONS = 20
MINIMUM_POSITIVE_VOLUME_FRACTION = Decimal("0.95")

_ZERO = Decimal("0")
_ONE = Decimal("1")
_BPS_DENOMINATOR = Decimal("10000")
_DECIMAL_QUANTUM = Decimal("0.00000001")
_FIXTURE_SOURCE_MARKERS = ("fixture", "synthetic", "generated_demo", "sample_data")
_CANONICAL_REFRESH_COLUMNS = {
    "timestamp",
    "symbol",
    "asset_class",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "basis",
    "source",
}
_EXPECTED_REFRESH_SOURCE = "alpaca_market_data_crypto_bars_v1beta3"
_EXPECTED_REFRESH_BASIS = "alpaca_crypto_bars_v1beta3_ohlcv"
_FALSE_SAFETY_FIELDS = (
    "network_access_attempted",
    "market_data_fetch_occurred",
    "broker_read_occurred",
    "broker_mutation_authorized",
    "broker_mutation_occurred",
    "paper_submit_authorized",
    "paper_submit_occurred",
    "paper_cancel_occurred",
    "paper_replace_occurred",
    "paper_close_occurred",
    "paper_liquidate_occurred",
    "live_authorized",
    "live_endpoint_touched",
    "credential_values_exposed",
)

__all__ = [
    "BASE_FEE_BPS",
    "BASE_SLIPPAGE_BPS",
    "CRYPTO_PREREGISTERED_TOURNAMENT_SCHEMA_VERSION",
    "MINIMUM_COMMON_HOURLY_BARS",
    "PREFERRED_COMMON_HOURLY_BARS",
    "STRESS_FEE_BPS",
    "STRESS_SLIPPAGE_BPS",
    "TOURNAMENT_SYMBOLS",
    "build_crypto_tournament_preregistration",
    "classify_crypto_tournament_candidate",
    "render_crypto_tournament_markdown",
    "run_crypto_preregistered_tournament",
    "run_crypto_preregistered_tournament_from_csv",
]


@dataclass(frozen=True, slots=True)
class _CandidateSpec:
    strategy_id: str
    strategy_family: str
    lookback_hours: int = 0
    fast_hours: int = 0
    slow_hours: int = 0

    def parameters(self) -> dict[str, int]:
        if self.strategy_family in {"trend_momentum", "breakout"}:
            return {"lookback_hours": self.lookback_hours}
        if self.strategy_family == "moving_average_regime":
            return {
                "fast_hours": self.fast_hours,
                "slow_hours": self.slow_hours,
            }
        raise ValidationError("unsupported tournament strategy family.")

    def timeframe_parameters(self, timeframe_hours: int) -> dict[str, int]:
        if timeframe_hours not in {1, 4}:
            raise ValidationError("tournament timeframe must be one or four hours.")
        for value in self.parameters().values():
            if value % timeframe_hours:
                raise ValidationError("elapsed-hour parameter does not map to timeframe.")
        if self.strategy_family in {"trend_momentum", "breakout"}:
            return {"lookback_bars": self.lookback_hours // timeframe_hours}
        return {
            "fast_bars": self.fast_hours // timeframe_hours,
            "slow_bars": self.slow_hours // timeframe_hours,
        }


@dataclass(frozen=True, slots=True)
class _ReturnPoint:
    timestamp: datetime
    target_exposure: Decimal
    applied_exposure: Decimal
    asset_return: Decimal
    transaction_cost: Decimal
    net_return: Decimal
    transition_delta: Decimal
    completed_round_trip: bool


@dataclass(frozen=True, slots=True)
class _PreparedHistory:
    hourly_by_symbol: Mapping[str, tuple[CryptoEvidenceBar, ...]]
    four_hour_by_symbol: Mapping[str, tuple[CryptoEvidenceBar, ...]]
    selected_hourly_bars: int
    discovery_hourly_bars: int
    dropped_leading_bars: int
    dropped_trailing_bars: int
    normalized_snapshot_sha256: str


def _candidate_specs() -> tuple[_CandidateSpec, ...]:
    return (
        _CandidateSpec(
            strategy_id="trend_momentum_72h",
            strategy_family="trend_momentum",
            lookback_hours=72,
        ),
        _CandidateSpec(
            strategy_id="breakout_168h",
            strategy_family="breakout",
            lookback_hours=168,
        ),
        _CandidateSpec(
            strategy_id="moving_average_regime_24h_168h",
            strategy_family="moving_average_regime",
            fast_hours=24,
            slow_hours=168,
        ),
    )


def build_crypto_tournament_preregistration() -> dict[str, object]:
    """Return the immutable candidate, window, cost, and gate contract."""

    candidates: list[dict[str, object]] = []
    for symbol in TOURNAMENT_SYMBOLS:
        for spec in _candidate_specs():
            candidate_id = f"crypto:tournament_v1:{symbol}:{spec.strategy_id}"
            payload: dict[str, object] = {
                "candidate_id": candidate_id,
                "symbol": symbol,
                "strategy_id": spec.strategy_id,
                "strategy_family": spec.strategy_family,
                "elapsed_hour_parameters": spec.parameters(),
                "primary_1h_parameters": spec.timeframe_parameters(1),
                "robustness_4h_parameters": spec.timeframe_parameters(4),
                "direction": "long_or_cash",
                "signal_execution": "one_bar_lag",
                "factory_version": CRYPTO_PREREGISTERED_TOURNAMENT_FACTORY_VERSION,
            }
            payload["candidate_fingerprint"] = _stable_hash(payload)
            candidates.append(payload)

    contract: dict[str, object] = {
        "schema_version": CRYPTO_PREREGISTERED_TOURNAMENT_SCHEMA_VERSION,
        "factory_version": CRYPTO_PREREGISTERED_TOURNAMENT_FACTORY_VERSION,
        "policy_version": CRYPTO_PREREGISTERED_TOURNAMENT_POLICY_VERSION,
        "record_type": "crypto_preregistered_tournament_manifest",
        "symbols": list(TOURNAMENT_SYMBOLS),
        "primary_timeframe": PRIMARY_TIMEFRAME,
        "robustness_timeframe": ROBUSTNESS_TIMEFRAME,
        "history_policy": {
            "minimum_common_hourly_bars": MINIMUM_COMMON_HOURLY_BARS,
            "preferred_common_hourly_bars": PREFERRED_COMMON_HOURLY_BARS,
            "maximum_common_hourly_bars_used": PREFERRED_COMMON_HOURLY_BARS,
            "minimum_discovery_hourly_bars": MINIMUM_DISCOVERY_HOURLY_BARS,
            "oos_hourly_bars": OOS_HOURLY_BARS,
            "oos_fold_count": OOS_FOLD_COUNT,
            "oos_fold_hourly_bars": OOS_FOLD_HOURLY_BARS,
            "common_consecutive_utc_grid_required": True,
            "partial_hour_bars_allowed": False,
            "complete_utc_4h_buckets_required": True,
            "guarded_refresh_receipt_and_output_sha256_required": True,
            "expected_source": _EXPECTED_REFRESH_SOURCE,
            "expected_basis": _EXPECTED_REFRESH_BASIS,
            "minimum_positive_volume_fraction_per_symbol": _decimal_text(
                MINIMUM_POSITIVE_VOLUME_FRACTION
            ),
        },
        "cost_policy": {
            "base": {
                "fee_bps_per_transition": _decimal_text(BASE_FEE_BPS),
                "slippage_bps_per_transition": _decimal_text(BASE_SLIPPAGE_BPS),
                "total_bps_per_transition": _decimal_text(
                    BASE_FEE_BPS + BASE_SLIPPAGE_BPS
                ),
            },
            "stress": {
                "fee_bps_per_transition": _decimal_text(STRESS_FEE_BPS),
                "slippage_bps_per_transition": _decimal_text(STRESS_SLIPPAGE_BPS),
                "total_bps_per_transition": _decimal_text(
                    STRESS_FEE_BPS + STRESS_SLIPPAGE_BPS
                ),
            },
        },
        "promotion_gates": {
            "aggregate_oos_base_return_strictly_positive": True,
            "aggregate_oos_stress_return_strictly_positive": True,
            "must_beat_cash_buy_hold_and_equal_weight_buy_hold_under_both_costs": True,
            "max_oos_drawdown": _decimal_text(MAX_OOS_DRAWDOWN),
            "drawdown_no_worse_than_risky_benchmarks": True,
            "minimum_positive_oos_folds": MINIMUM_POSITIVE_OOS_FOLDS,
            "oos_fold_count": OOS_FOLD_COUNT,
            "max_positive_profit_concentration": _decimal_text(
                MAX_POSITIVE_PROFIT_CONCENTRATION
            ),
            "minimum_completed_round_trips_full_sample": (
                MINIMUM_COMPLETED_ROUND_TRIPS
            ),
            "minimum_oos_transitions": MINIMUM_OOS_TRANSITIONS,
            "four_hour_robustness_required": True,
            "passing_scope": "eligible_for_no_submit_shadow_evaluation",
        },
        "candidates": candidates,
        "candidate_count": len(candidates),
        "dynamic_parameter_optimization": False,
        "post_hoc_retuning": False,
        "candidate_set_mutation_allowed": False,
        "paper_or_live_execution_authorized": False,
    }
    contract["preregistration_fingerprint"] = _stable_hash(contract)
    return contract


def run_crypto_preregistered_tournament_from_csv(
    input_path: Path | str,
    *,
    refresh_packet_path: Path | str,
    as_of: datetime | str,
) -> dict[str, object]:
    """Load a canonical hourly CSV and run the frozen tournament contract."""

    path = Path(input_path)
    intake = _inspect_canonical_csv(path)
    input_sha256 = _file_sha256(path)
    provenance = _validate_refresh_provenance(
        input_path=path,
        input_sha256=input_sha256,
        refresh_packet_path=Path(refresh_packet_path),
        as_of=_utc_datetime(as_of, "as_of"),
    )
    bars = load_crypto_evidence_bars_from_csv(path, symbols=TOURNAMENT_SYMBOLS)
    packet = run_crypto_preregistered_tournament(
        bars,
        as_of=as_of,
        data_source=str(provenance["data_source"]),
        data_freshness="guarded_refresh_receipt_bound_snapshot",
        input_path=str(path),
        input_sha256=input_sha256,
        provenance_binding=provenance,
    )
    packet["input_intake"] = intake
    return packet


def run_crypto_preregistered_tournament(
    bars: Iterable[CryptoEvidenceBar],
    *,
    as_of: datetime | str,
    data_source: str,
    data_freshness: str,
    input_path: str = "",
    input_sha256: str = "",
    provenance_binding: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Evaluate every preregistered candidate on fixed 1h and 4h OOS windows."""

    evaluated_at = _utc_datetime(as_of, "as_of")
    source = _required_text(data_source, "data_source")
    freshness = _required_text(data_freshness, "data_freshness")
    manifest = build_crypto_tournament_preregistration()
    checked_bars = tuple(bars)
    provenance = dict(provenance_binding or {})
    expected_start = provenance.get("requested_start")
    expected_end = provenance.get("requested_end")
    coverage_errors = _coverage_errors(
        checked_bars,
        evaluated_at,
        expected_start=expected_start,
        expected_end=expected_end,
    )

    base_packet: dict[str, object] = {
        "schema_version": CRYPTO_PREREGISTERED_TOURNAMENT_SCHEMA_VERSION,
        "record_type": "crypto_preregistered_tournament_evidence_packet",
        "as_of": evaluated_at.isoformat(),
        "classification": "",
        "preregistration": manifest,
        "preregistration_fingerprint": manifest["preregistration_fingerprint"],
        "data_source": source,
        "data_freshness": freshness,
        "input_path": input_path,
        "input_sha256": input_sha256,
        "refresh_provenance": provenance,
        "refresh_provenance_status": (
            "passed" if provenance.get("status") == "passed" else "unbound"
        ),
        "coverage_errors": coverage_errors,
        "candidate_evaluations": [],
        "eligible_candidate_count": 0,
        "selected_candidate": {},
        "ranking": [],
        "paper_planning_eligibility": "not_eligible",
        "broker_execution_eligibility": "not_eligible",
        "labels": [
            "crypto_preregistered_tournament",
            "research_only",
            "no_submit",
            "paper_lab_only",
            "not_live_authorized",
            "profit_claim=none",
        ],
        "profit_claim": "none",
        **_false_safety_flags(),
    }
    if coverage_errors:
        base_packet.update(
            {
                "classification": "insufficient_or_invalid_history",
                "next_safe_action": (
                    "Refresh a consecutive shared 1Hour history with at least "
                    "4,320 complete bars per required symbol, then rerun unchanged."
                ),
            }
        )
        return base_packet

    prepared = _prepare_history(checked_bars)
    base_packet["history_contract"] = _history_contract_payload(prepared)
    base_packet["normalized_snapshot_sha256"] = prepared.normalized_snapshot_sha256
    base_packet["oos_windows"] = _oos_window_payload(prepared)

    evaluations: list[dict[str, object]] = []
    for symbol in TOURNAMENT_SYMBOLS:
        for spec in _candidate_specs():
            evaluations.append(
                _evaluate_candidate(
                    symbol=symbol,
                    spec=spec,
                    prepared=prepared,
                    manifest=manifest,
                )
            )

    ranked = sorted(evaluations, key=_ranking_key)
    eligible = [
        item
        for item in ranked
        if item["candidate_decision"]
        == "eligible_for_no_submit_shadow_evaluation"
    ]
    provenance_passed = provenance.get("status") == "passed"
    selected = eligible[0] if eligible and provenance_passed else {}
    base_packet.update(
        {
            "classification": (
                "eligible_for_no_submit_shadow_evaluation"
                if selected
                else (
                    "no_candidate_qualified"
                    if provenance_passed
                    else "unbound_input_not_eligible"
                )
            ),
            "candidate_evaluations": ranked,
            "eligible_candidate_count": len(eligible) if provenance_passed else 0,
            "selected_candidate": _selected_candidate_payload(selected),
            "ranking": [str(item["candidate_id"]) for item in ranked],
            "next_safe_action": (
                "Open a separate no-submit shadow-evaluation milestone; paper "
                "or broker execution remains unauthorized."
                if selected
                else (
                    "Bind the input to a passing guarded refresh receipt before any evidence classification."
                    if not provenance_passed
                    else "Close rejected candidates without retuning and register a new hypothesis only in a new tournament version."
                )
            ),
        }
    )
    return base_packet


def classify_crypto_tournament_candidate(
    *,
    primary: Mapping[str, object],
    robustness: Mapping[str, object],
    completed_round_trips_full_sample: int,
) -> tuple[str, tuple[str, ...]]:
    """Apply the preregistered promotion gates to one metrics payload."""

    reasons: list[str] = []
    _return_gate_reasons(primary, prefix="primary", reasons=reasons)
    _drawdown_gate_reasons(primary, prefix="primary", reasons=reasons)

    positive_folds = int(primary.get("positive_fold_count", 0))
    if positive_folds < MINIMUM_POSITIVE_OOS_FOLDS:
        reasons.append("insufficient_positive_oos_folds")
    concentration = _decimal(primary.get("positive_profit_concentration", "1"))
    if concentration > MAX_POSITIVE_PROFIT_CONCENTRATION:
        reasons.append("positive_profit_concentration_exceeded")
    if completed_round_trips_full_sample < MINIMUM_COMPLETED_ROUND_TRIPS:
        reasons.append("insufficient_completed_round_trips")
    if int(primary.get("oos_transition_count", 0)) < MINIMUM_OOS_TRANSITIONS:
        reasons.append("insufficient_oos_transitions")

    _return_gate_reasons(robustness, prefix="robustness", reasons=reasons)
    _drawdown_gate_reasons(robustness, prefix="robustness", reasons=reasons)

    if reasons:
        return "reject_candidate", tuple(reasons)
    return "eligible_for_no_submit_shadow_evaluation", ()


def render_crypto_tournament_markdown(packet: Mapping[str, object]) -> str:
    """Render a compact operator-facing research packet."""

    selected = _mapping(packet.get("selected_candidate"))
    lines = [
        "# Preregistered Crypto Strategy Tournament",
        "",
        f"- Classification: `{packet.get('classification', '')}`",
        f"- As of: `{packet.get('as_of', '')}`",
        f"- Preregistration fingerprint: `{packet.get('preregistration_fingerprint', '')}`",
        f"- Normalized snapshot SHA-256: `{packet.get('normalized_snapshot_sha256', '')}`",
        f"- Eligible candidates: `{packet.get('eligible_candidate_count', 0)}`",
        f"- Selected candidate: `{selected.get('candidate_id', '')}`",
        f"- Paper planning: `{packet.get('paper_planning_eligibility', 'not_eligible')}`",
        f"- Profit claim: `{packet.get('profit_claim', 'none')}`",
        "",
        "## Candidate Decisions",
        "",
        "| Candidate | Decision | Base OOS | Stress OOS | 4h Base | Reasons |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for item in _mapping_sequence(packet.get("candidate_evaluations")):
        primary = _mapping(item.get("primary"))
        robustness = _mapping(item.get("robustness"))
        reasons = ", ".join(_string_sequence(item.get("rejection_reasons")))
        lines.append(
            "| {candidate} | {decision} | {base} | {stress} | {robust} | {reasons} |".format(
                candidate=item.get("candidate_id", ""),
                decision=item.get("candidate_decision", ""),
                base=primary.get("base_total_return", ""),
                stress=primary.get("stress_total_return", ""),
                robust=robustness.get("base_total_return", ""),
                reasons=reasons,
            )
        )
    lines.extend(
        [
            "",
            "This packet is research-only and no-submit. It does not authorize paper or live trading.",
            "",
        ]
    )
    return "\n".join(lines)


def _inspect_canonical_csv(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ValidationError("crypto tournament input path is missing.")
    seen: set[tuple[str, datetime]] = set()
    previous_by_symbol: dict[str, datetime] = {}
    source_values: set[str] = set()
    basis_values: set[str] = set()
    volume_rows_by_symbol = {symbol: 0 for symbol in TOURNAMENT_SYMBOLS}
    positive_volume_rows_by_symbol = {symbol: 0 for symbol in TOURNAMENT_SYMBOLS}
    row_count = 0
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = tuple(reader.fieldnames or ())
            if not _CANONICAL_REFRESH_COLUMNS.issubset(fieldnames):
                raise ValidationError(
                    "crypto tournament CSV does not match the canonical guarded refresh schema."
                )
            for row in reader:
                row_count += 1
                symbol = _canonical_symbol(row.get("symbol", ""))
                if str(row.get("asset_class", "")).strip().lower() != "crypto":
                    raise ValidationError("tournament CSV asset_class must be crypto.")
                timestamp = _utc_datetime(row.get("timestamp", ""), "timestamp")
                key = (symbol, timestamp)
                if key in seen:
                    raise ValidationError("duplicate tournament symbol/timestamp row.")
                previous = previous_by_symbol.get(symbol)
                if previous is not None and timestamp <= previous:
                    raise ValidationError("tournament rows must be strictly chronological per symbol.")
                seen.add(key)
                previous_by_symbol[symbol] = timestamp
                source = str(row.get("source", "")).strip()
                basis = str(row.get("basis", "")).strip()
                source_values.add(source)
                basis_values.add(basis)
                if source != _EXPECTED_REFRESH_SOURCE:
                    raise ValidationError("tournament CSV source is not the guarded Alpaca refresh source.")
                if basis != _EXPECTED_REFRESH_BASIS:
                    raise ValidationError("tournament CSV basis is not the guarded OHLCV basis.")
                volume = _decimal(row.get("volume", ""))
                if volume < _ZERO:
                    raise ValidationError("tournament CSV volume cannot be negative.")
                volume_rows_by_symbol[symbol] += 1
                if volume > _ZERO:
                    positive_volume_rows_by_symbol[symbol] += 1
    except OSError as exc:
        raise ValidationError("unable to read crypto tournament CSV.") from exc

    lowered_sources = " ".join(sorted(source_values)).lower()
    if any(marker in lowered_sources for marker in _FIXTURE_SOURCE_MARKERS):
        raise ValidationError("fixture or synthetic history cannot enter the tournament.")
    positive_volume_fraction_by_symbol: dict[str, str] = {}
    for symbol in TOURNAMENT_SYMBOLS:
        observed = volume_rows_by_symbol[symbol]
        fraction = (
            Decimal(positive_volume_rows_by_symbol[symbol]) / Decimal(observed)
            if observed
            else _ZERO
        )
        positive_volume_fraction_by_symbol[symbol] = _decimal_text(fraction)
        if observed and fraction < MINIMUM_POSITIVE_VOLUME_FRACTION:
            raise ValidationError(
                f"positive-volume coverage below tournament threshold for {symbol}."
            )
    return {
        "status": "passed",
        "row_count": row_count,
        "source_values": sorted(source_values),
        "basis_values": sorted(basis_values),
        "positive_volume_rows_by_symbol": positive_volume_rows_by_symbol,
        "positive_volume_fraction_by_symbol": positive_volume_fraction_by_symbol,
        "minimum_positive_volume_fraction": _decimal_text(
            MINIMUM_POSITIVE_VOLUME_FRACTION
        ),
        "duplicate_timestamp_status": "passed",
        "chronology_status": "passed",
        "fixture_source_status": "passed",
    }


def _validate_refresh_provenance(
    *,
    input_path: Path,
    input_sha256: str,
    refresh_packet_path: Path,
    as_of: datetime,
) -> dict[str, object]:
    if not refresh_packet_path.is_file():
        raise ValidationError("guarded refresh packet is required for tournament evidence.")
    try:
        packet_value = json.loads(refresh_packet_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError("guarded refresh packet is not valid JSON.") from exc
    packet = _mapping(packet_value)
    if not packet:
        raise ValidationError("guarded refresh packet must be a JSON object.")

    required_pairs = {
        "record_type": "crypto_history_refresh_adapter_packet",
        "mode": "market_data_fetch",
        "classification": "sufficient_real_crypto_history",
        "coverage_gate_classification": "sufficient_real_crypto_history",
        "authorization_status": "authorized",
        "endpoint_safety_status": "passed_non_live_endpoint_check",
        "data_source": _EXPECTED_REFRESH_SOURCE,
        "timeframe": PRIMARY_TIMEFRAME,
        "loc": "us",
        "schema_validation_status": "passed",
    }
    for field, expected in required_pairs.items():
        if str(packet.get(field, "")) != expected:
            raise ValidationError(f"guarded refresh packet field mismatch: {field}.")

    required_true = ("market_data_fetch_occurred", "network_access_attempted")
    required_false = (
        "broker_read_occurred",
        "broker_mutation_authorized",
        "broker_mutation_occurred",
        "paper_submit_authorized",
        "paper_submit_occurred",
        "live_authorized",
        "live_endpoint_indicator",
        "live_endpoint_touched",
        "credential_values_exposed",
    )
    if any(packet.get(field) is not True for field in required_true):
        raise ValidationError("guarded refresh packet does not prove market-data fetch.")
    if any(packet.get(field) is not False for field in required_false):
        raise ValidationError("guarded refresh packet violates no-mutation safety fields.")

    requested_symbols = tuple(str(item) for item in _string_sequence(packet.get("requested_symbols")))
    fetched_symbols = tuple(str(item) for item in _string_sequence(packet.get("fetched_symbols")))
    if set(requested_symbols) != set(TOURNAMENT_SYMBOLS) or set(fetched_symbols) != set(TOURNAMENT_SYMBOLS):
        raise ValidationError("guarded refresh packet does not bind all tournament symbols.")

    packet_output = Path(_required_text(packet.get("output_path"), "output_path"))
    if packet_output.resolve() != input_path.resolve():
        raise ValidationError("guarded refresh packet output path does not match tournament input.")
    if str(packet.get("output_sha256", "")).lower() != input_sha256.lower():
        raise ValidationError("guarded refresh packet output SHA-256 mismatch.")

    requested_start = _utc_datetime(packet.get("requested_start", ""), "requested_start")
    requested_end = _utc_datetime(packet.get("requested_end", ""), "requested_end")
    packet_as_of = _utc_datetime(packet.get("as_of", ""), "refresh_as_of")
    if requested_end != as_of or packet_as_of != as_of:
        raise ValidationError("tournament as_of must equal the guarded refresh end/as_of.")
    if requested_end - requested_start < timedelta(hours=MINIMUM_COMMON_HOURLY_BARS):
        raise ValidationError("guarded refresh window is shorter than 4,320 hours.")

    rows_per_symbol = _mapping(packet.get("rows_per_symbol_after_normalization"))
    if any(int(rows_per_symbol.get(symbol, 0)) < MINIMUM_COMMON_HOURLY_BARS for symbol in TOURNAMENT_SYMBOLS):
        raise ValidationError("guarded refresh packet row coverage is below tournament minimum.")
    if _string_sequence(packet.get("coverage_gate_blocking_reasons")):
        raise ValidationError("guarded refresh packet contains coverage blockers.")

    return {
        "status": "passed",
        "refresh_packet_path": str(refresh_packet_path),
        "refresh_packet_sha256": _file_sha256(refresh_packet_path),
        "input_path": str(input_path),
        "input_sha256": input_sha256,
        "data_source": _EXPECTED_REFRESH_SOURCE,
        "requested_start": requested_start.isoformat(),
        "requested_end": requested_end.isoformat(),
        "timeframe": PRIMARY_TIMEFRAME,
        "symbols": list(TOURNAMENT_SYMBOLS),
        "market_data_fetch_occurred": True,
        "broker_mutation_occurred": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
    }


def _coverage_errors(
    bars: Sequence[CryptoEvidenceBar],
    as_of: datetime,
    *,
    expected_start: object = None,
    expected_end: object = None,
) -> list[str]:
    errors: list[str] = []
    grouped: dict[str, list[CryptoEvidenceBar]] = {symbol: [] for symbol in TOURNAMENT_SYMBOLS}
    seen: set[tuple[str, datetime]] = set()
    for bar in bars:
        if bar.symbol not in grouped:
            continue
        key = (bar.symbol, bar.timestamp)
        if key in seen and "duplicate_symbol_timestamp" not in errors:
            errors.append("duplicate_symbol_timestamp")
        seen.add(key)
        grouped[bar.symbol].append(bar)

    reference_timestamps: tuple[datetime, ...] | None = None
    bound_start = (
        _utc_datetime(expected_start, "expected_start")
        if expected_start not in (None, "")
        else None
    )
    bound_end = (
        _utc_datetime(expected_end, "expected_end")
        if expected_end not in (None, "")
        else None
    )
    if bound_end is not None and bound_end != as_of:
        errors.append("refresh_end_as_of_mismatch")
    for symbol in TOURNAMENT_SYMBOLS:
        symbol_bars = tuple(grouped[symbol])
        if not symbol_bars:
            errors.append(f"missing_symbol:{symbol}")
            continue
        ordered = tuple(sorted(symbol_bars, key=lambda item: item.timestamp))
        timestamps = tuple(item.timestamp for item in ordered)
        if timestamps != tuple(item.timestamp for item in symbol_bars):
            errors.append(f"non_monotonic_symbol:{symbol}")
        if len(timestamps) < MINIMUM_COMMON_HOURLY_BARS:
            errors.append(f"insufficient_rows:{symbol}")
        if any(
            current - previous != timedelta(hours=1)
            for previous, current in zip(timestamps, timestamps[1:])
        ):
            errors.append(f"non_hourly_gap:{symbol}")
        if any(timestamp + timedelta(hours=1) > as_of for timestamp in timestamps):
            errors.append(f"partial_or_future_bar:{symbol}")
        if bound_start is not None and timestamps[0] != bound_start:
            errors.append(f"refresh_start_history_mismatch:{symbol}")
        if bound_end is not None and timestamps[-1] + timedelta(hours=1) != bound_end:
            errors.append(f"stale_or_incomplete_refresh_end:{symbol}")
        if reference_timestamps is None:
            reference_timestamps = timestamps
        elif timestamps != reference_timestamps:
            errors.append(f"unequal_timestamp_grid:{symbol}")
    return errors


def _prepare_history(bars: Sequence[CryptoEvidenceBar]) -> _PreparedHistory:
    grouped = {
        symbol: tuple(sorted((bar for bar in bars if bar.symbol == symbol), key=lambda item: item.timestamp))
        for symbol in TOURNAMENT_SYMBOLS
    }
    timestamps = tuple(bar.timestamp for bar in grouped[TOURNAMENT_SYMBOLS[0]])

    end_index = len(timestamps)
    while end_index and (timestamps[end_index - 1] + timedelta(hours=1)).hour % 4:
        end_index -= 1
    aligned_count = min(end_index, PREFERRED_COMMON_HOURLY_BARS)
    aligned_count -= aligned_count % 24
    start_index = end_index - aligned_count
    if aligned_count < MINIMUM_COMMON_HOURLY_BARS:
        raise ValidationError("aligned tournament history is below 4,320 hourly bars.")

    selected = {
        symbol: grouped[symbol][start_index:end_index]
        for symbol in TOURNAMENT_SYMBOLS
    }
    four_hour = {
        symbol: _aggregate_four_hour(selected[symbol])
        for symbol in TOURNAMENT_SYMBOLS
    }
    discovery_bars = aligned_count - OOS_HOURLY_BARS
    if discovery_bars < MINIMUM_DISCOVERY_HOURLY_BARS:
        raise ValidationError("tournament discovery/warmup history is insufficient.")
    return _PreparedHistory(
        hourly_by_symbol=selected,
        four_hour_by_symbol=four_hour,
        selected_hourly_bars=aligned_count,
        discovery_hourly_bars=discovery_bars,
        dropped_leading_bars=start_index,
        dropped_trailing_bars=len(timestamps) - end_index,
        normalized_snapshot_sha256=_normalized_snapshot_hash(selected),
    )


def _aggregate_four_hour(
    bars: Sequence[CryptoEvidenceBar],
) -> tuple[CryptoEvidenceBar, ...]:
    if len(bars) % 4:
        raise ValidationError("hourly tournament history must form complete 4h buckets.")
    aggregated: list[CryptoEvidenceBar] = []
    for offset in range(0, len(bars), 4):
        bucket = tuple(bars[offset : offset + 4])
        start = bucket[0].timestamp
        if start.hour % 4 or start.minute or start.second or start.microsecond:
            raise ValidationError("4h tournament buckets must align to UTC boundaries.")
        expected = tuple(start + timedelta(hours=index) for index in range(4))
        if tuple(item.timestamp for item in bucket) != expected:
            raise ValidationError("4h tournament bucket is incomplete.")
        aggregated.append(
            CryptoEvidenceBar(
                symbol=bucket[-1].symbol,
                timestamp=bucket[-1].timestamp,
                close=bucket[-1].close,
            )
        )
    return tuple(aggregated)


def _evaluate_candidate(
    *,
    symbol: str,
    spec: _CandidateSpec,
    prepared: _PreparedHistory,
    manifest: Mapping[str, object],
) -> dict[str, object]:
    candidate_id = f"crypto:tournament_v1:{symbol}:{spec.strategy_id}"
    candidate_manifest = next(
        item
        for item in _mapping_sequence(manifest.get("candidates"))
        if item.get("candidate_id") == candidate_id
    )
    primary_bars = prepared.hourly_by_symbol[symbol]
    robustness_bars = prepared.four_hour_by_symbol[symbol]
    primary = _timeframe_evaluation(
        symbol=symbol,
        spec=spec,
        timeframe_hours=1,
        bars=primary_bars,
        bars_by_symbol=prepared.hourly_by_symbol,
        oos_bars=OOS_HOURLY_BARS,
        fold_bars=OOS_FOLD_HOURLY_BARS,
    )
    robustness = _timeframe_evaluation(
        symbol=symbol,
        spec=spec,
        timeframe_hours=4,
        bars=robustness_bars,
        bars_by_symbol=prepared.four_hour_by_symbol,
        oos_bars=OOS_HOURLY_BARS // 4,
        fold_bars=OOS_FOLD_HOURLY_BARS // 4,
    )
    full_targets = _strategy_targets(primary_bars, spec, timeframe_hours=1)
    completed_round_trips = _completed_round_trips(full_targets)
    decision, reasons = classify_crypto_tournament_candidate(
        primary=primary,
        robustness=robustness,
        completed_round_trips_full_sample=completed_round_trips,
    )
    return {
        "candidate_id": candidate_id,
        "candidate_fingerprint": candidate_manifest["candidate_fingerprint"],
        "symbol": symbol,
        "strategy_id": spec.strategy_id,
        "strategy_family": spec.strategy_family,
        "elapsed_hour_parameters": spec.parameters(),
        "completed_round_trips_full_sample": completed_round_trips,
        "candidate_decision": decision,
        "rejection_reasons": list(reasons),
        "primary": primary,
        "robustness": robustness,
        "paper_or_broker_eligible": False,
    }


def _timeframe_evaluation(
    *,
    symbol: str,
    spec: _CandidateSpec,
    timeframe_hours: int,
    bars: Sequence[CryptoEvidenceBar],
    bars_by_symbol: Mapping[str, Sequence[CryptoEvidenceBar]],
    oos_bars: int,
    fold_bars: int,
) -> dict[str, object]:
    targets = _strategy_targets(bars, spec, timeframe_hours=timeframe_hours)
    start = len(bars) - oos_bars
    oos_timestamps = tuple(item.timestamp for item in bars[start:])
    asset_returns = _asset_returns(tuple(item.close for item in bars[start:]))
    oos_targets = targets[start:]

    base_points = _simulate(
        timestamps=oos_timestamps,
        asset_returns=asset_returns,
        targets=oos_targets,
        fee_bps=BASE_FEE_BPS,
        slippage_bps=BASE_SLIPPAGE_BPS,
    )
    stress_points = _simulate(
        timestamps=oos_timestamps,
        asset_returns=asset_returns,
        targets=oos_targets,
        fee_bps=STRESS_FEE_BPS,
        slippage_bps=STRESS_SLIPPAGE_BPS,
    )
    base_metrics = _metrics(base_points)
    stress_metrics = _metrics(stress_points)
    benchmark = _benchmark_evaluation(
        symbol=symbol,
        bars_by_symbol=bars_by_symbol,
        start=start,
    )
    fold_metrics = [
        _metrics(base_points[index * fold_bars : (index + 1) * fold_bars])
        for index in range(OOS_FOLD_COUNT)
    ]
    fold_returns = tuple(_decimal(item["total_return"]) for item in fold_metrics)
    positive_folds = sum(1 for value in fold_returns if value > _ZERO)
    positive_values = tuple(value for value in fold_returns if value > _ZERO)
    positive_sum = sum(positive_values, _ZERO)
    concentration = (
        max(positive_values) / positive_sum if positive_values else _ONE
    )
    return {
        "timeframe": PRIMARY_TIMEFRAME if timeframe_hours == 1 else ROBUSTNESS_TIMEFRAME,
        "timeframe_hours": timeframe_hours,
        "parameters": spec.timeframe_parameters(timeframe_hours),
        "oos_start": oos_timestamps[0].isoformat(),
        "oos_end": oos_timestamps[-1].isoformat(),
        "oos_bar_count": len(oos_timestamps),
        "base_metrics": base_metrics,
        "stress_metrics": stress_metrics,
        "base_total_return": base_metrics["total_return"],
        "stress_total_return": stress_metrics["total_return"],
        "base_max_drawdown": base_metrics["max_drawdown"],
        "oos_transition_count": int(base_metrics["transition_count"]),
        "folds": [
            {
                "fold": index + 1,
                **metrics,
            }
            for index, metrics in enumerate(fold_metrics)
        ],
        "positive_fold_count": positive_folds,
        "positive_profit_concentration": _decimal_text(concentration),
        "worst_fold_return": _decimal_text(min(fold_returns)),
        "benchmarks": benchmark,
        "base_excess_vs_buy_hold": _decimal_text(
            _decimal(base_metrics["total_return"])
            - _decimal(_mapping(benchmark["base"])["buy_hold_total_return"])
        ),
        "base_excess_vs_basket": _decimal_text(
            _decimal(base_metrics["total_return"])
            - _decimal(_mapping(benchmark["base"])["basket_total_return"])
        ),
        "stress_excess_vs_buy_hold": _decimal_text(
            _decimal(stress_metrics["total_return"])
            - _decimal(_mapping(benchmark["stress"])["buy_hold_total_return"])
        ),
        "stress_excess_vs_basket": _decimal_text(
            _decimal(stress_metrics["total_return"])
            - _decimal(_mapping(benchmark["stress"])["basket_total_return"])
        ),
    }


def _benchmark_evaluation(
    *,
    symbol: str,
    bars_by_symbol: Mapping[str, Sequence[CryptoEvidenceBar]],
    start: int,
) -> dict[str, object]:
    symbol_bars = tuple(bars_by_symbol[symbol][start:])
    timestamps = tuple(item.timestamp for item in symbol_bars)
    buy_hold_returns = _asset_returns(tuple(item.close for item in symbol_bars))
    basket_returns = _equal_weight_buy_hold_returns(
        {
            candidate_symbol: tuple(
                item.close for item in bars_by_symbol[candidate_symbol][start:]
            )
            for candidate_symbol in TOURNAMENT_SYMBOLS
        }
    )
    targets = tuple(_ONE for _ in timestamps)
    result: dict[str, object] = {}
    for label, fee_bps, slippage_bps in (
        ("base", BASE_FEE_BPS, BASE_SLIPPAGE_BPS),
        ("stress", STRESS_FEE_BPS, STRESS_SLIPPAGE_BPS),
    ):
        buy_hold_metrics = _metrics(
            _simulate(
                timestamps=timestamps,
                asset_returns=buy_hold_returns,
                targets=targets,
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
            )
        )
        basket_metrics = _metrics(
            _simulate(
                timestamps=timestamps,
                asset_returns=basket_returns,
                targets=targets,
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
            )
        )
        result[label] = {
            "cash_total_return": "0",
            "buy_hold_total_return": buy_hold_metrics["total_return"],
            "buy_hold_max_drawdown": buy_hold_metrics["max_drawdown"],
            "basket_total_return": basket_metrics["total_return"],
            "basket_max_drawdown": basket_metrics["max_drawdown"],
            "basket_semantics": "equal_weight_at_oos_start_then_buy_and_hold_without_rebalancing",
        }
    return result


def _return_gate_reasons(
    evaluation: Mapping[str, object],
    *,
    prefix: str,
    reasons: list[str],
) -> None:
    benchmarks = _mapping(evaluation.get("benchmarks"))
    for cost_case in ("base", "stress"):
        candidate_return = _decimal(evaluation.get(f"{cost_case}_total_return", "0"))
        case = _mapping(benchmarks.get(cost_case))
        if candidate_return <= _ZERO:
            reasons.append(f"{prefix}_{cost_case}_not_positive")
        if candidate_return <= _decimal(case.get("buy_hold_total_return", "0")):
            reasons.append(f"{prefix}_{cost_case}_buy_hold_underperformance")
        if candidate_return <= _decimal(case.get("basket_total_return", "0")):
            reasons.append(f"{prefix}_{cost_case}_basket_underperformance")


def _drawdown_gate_reasons(
    evaluation: Mapping[str, object],
    *,
    prefix: str,
    reasons: list[str],
) -> None:
    drawdown = _decimal(evaluation.get("base_max_drawdown", "0"))
    base_benchmarks = _mapping(_mapping(evaluation.get("benchmarks")).get("base"))
    if drawdown > MAX_OOS_DRAWDOWN:
        reasons.append(f"{prefix}_drawdown_above_limit")
    if drawdown > _decimal(base_benchmarks.get("buy_hold_max_drawdown", "0")):
        reasons.append(f"{prefix}_drawdown_worse_than_buy_hold")
    if drawdown > _decimal(base_benchmarks.get("basket_max_drawdown", "0")):
        reasons.append(f"{prefix}_drawdown_worse_than_basket")


def _strategy_targets(
    bars: Sequence[CryptoEvidenceBar],
    spec: _CandidateSpec,
    *,
    timeframe_hours: int,
) -> tuple[Decimal, ...]:
    closes = tuple(item.close for item in bars)
    parameters = spec.timeframe_parameters(timeframe_hours)
    targets: list[Decimal] = []
    for index, close in enumerate(closes):
        target = _ZERO
        if spec.strategy_family == "trend_momentum":
            lookback = parameters["lookback_bars"]
            if index >= lookback and close > closes[index - lookback]:
                target = _ONE
        elif spec.strategy_family == "breakout":
            lookback = parameters["lookback_bars"]
            if index >= lookback and close > max(closes[index - lookback : index]):
                target = _ONE
        elif spec.strategy_family == "moving_average_regime":
            fast = parameters["fast_bars"]
            slow = parameters["slow_bars"]
            if index + 1 >= slow:
                fast_average = sum(closes[index - fast + 1 : index + 1], _ZERO) / Decimal(fast)
                slow_average = sum(closes[index - slow + 1 : index + 1], _ZERO) / Decimal(slow)
                if fast_average > slow_average:
                    target = _ONE
        else:  # pragma: no cover - frozen specs make this unreachable
            raise ValidationError("unsupported tournament strategy family.")
        targets.append(target)
    return tuple(targets)


def _asset_returns(closes: Sequence[Decimal]) -> tuple[Decimal, ...]:
    if not closes:
        return ()
    returns = [_ZERO]
    returns.extend(
        (current / previous) - _ONE
        for previous, current in zip(closes, closes[1:])
    )
    return tuple(returns)


def _equal_weight_buy_hold_returns(
    closes_by_symbol: Mapping[str, Sequence[Decimal]],
) -> tuple[Decimal, ...]:
    lengths = {len(values) for values in closes_by_symbol.values()}
    if len(lengths) != 1 or not lengths:
        raise ValidationError("basket histories must share one length.")
    count = lengths.pop()
    if count == 0:
        return ()
    weights = {symbol: _ONE / Decimal(len(closes_by_symbol)) for symbol in closes_by_symbol}
    returns = [_ZERO]
    for index in range(1, count):
        symbol_returns = {
            symbol: (values[index] / values[index - 1]) - _ONE
            for symbol, values in closes_by_symbol.items()
        }
        portfolio_return = sum(
            weights[symbol] * symbol_returns[symbol] for symbol in weights
        )
        returns.append(portfolio_return)
        denominator = _ONE + portfolio_return
        if denominator <= _ZERO:
            raise ValidationError("basket value became non-positive.")
        weights = {
            symbol: (
                weights[symbol] * (_ONE + symbol_returns[symbol]) / denominator
            )
            for symbol in weights
        }
    return tuple(returns)


def _simulate(
    *,
    timestamps: Sequence[datetime],
    asset_returns: Sequence[Decimal],
    targets: Sequence[Decimal],
    fee_bps: Decimal,
    slippage_bps: Decimal,
) -> tuple[_ReturnPoint, ...]:
    if not (len(timestamps) == len(asset_returns) == len(targets)):
        raise ValidationError("tournament simulation inputs must align.")
    cost_rate = (fee_bps + slippage_bps) / _BPS_DENOMINATOR
    previous_exposure = _ZERO
    points: list[_ReturnPoint] = []
    for timestamp, asset_return, target in zip(timestamps, asset_returns, targets):
        transition = abs(target - previous_exposure)
        cost = transition * cost_rate
        gross_multiplier = _ONE + (previous_exposure * asset_return)
        net_return = (gross_multiplier * (_ONE - cost)) - _ONE
        points.append(
            _ReturnPoint(
                timestamp=timestamp,
                target_exposure=target,
                applied_exposure=previous_exposure,
                asset_return=asset_return,
                transaction_cost=cost,
                net_return=net_return,
                transition_delta=transition,
                completed_round_trip=previous_exposure == _ONE and target == _ZERO,
            )
        )
        previous_exposure = target
    return tuple(points)


def _metrics(points: Sequence[_ReturnPoint]) -> dict[str, object]:
    if not points:
        return {
            "start": "",
            "end": "",
            "bar_count": 0,
            "total_return": "0",
            "max_drawdown": "0",
            "transition_count": 0,
            "completed_round_trips": 0,
            "turnover": "0",
            "estimated_cost_return": "0",
        }
    equity = _ONE
    peak = _ONE
    max_drawdown = _ZERO
    turnover = _ZERO
    costs = _ZERO
    transitions = 0
    round_trips = 0
    for point in points:
        equity *= _ONE + point.net_return
        if equity > peak:
            peak = equity
        drawdown = _ONE - (equity / peak)
        max_drawdown = max(max_drawdown, drawdown)
        turnover += point.transition_delta
        costs += point.transaction_cost
        if point.transition_delta > _ZERO:
            transitions += 1
        if point.completed_round_trip:
            round_trips += 1
    return {
        "start": points[0].timestamp.isoformat(),
        "end": points[-1].timestamp.isoformat(),
        "bar_count": len(points),
        "total_return": _decimal_text(equity - _ONE),
        "max_drawdown": _decimal_text(max_drawdown),
        "transition_count": transitions,
        "completed_round_trips": round_trips,
        "turnover": _decimal_text(turnover),
        "estimated_cost_return": _decimal_text(costs),
    }


def _completed_round_trips(targets: Sequence[Decimal]) -> int:
    previous = _ZERO
    count = 0
    for target in targets:
        if previous == _ONE and target == _ZERO:
            count += 1
        previous = target
    return count


def _history_contract_payload(prepared: _PreparedHistory) -> dict[str, object]:
    first_symbol = TOURNAMENT_SYMBOLS[0]
    hourly = prepared.hourly_by_symbol[first_symbol]
    four_hour = prepared.four_hour_by_symbol[first_symbol]
    return {
        "status": "passed",
        "selected_hourly_bars_per_symbol": prepared.selected_hourly_bars,
        "selected_4h_bars_per_symbol": len(four_hour),
        "discovery_hourly_bars": prepared.discovery_hourly_bars,
        "oos_hourly_bars": OOS_HOURLY_BARS,
        "dropped_leading_bars": prepared.dropped_leading_bars,
        "dropped_trailing_bars": prepared.dropped_trailing_bars,
        "start": hourly[0].timestamp.isoformat(),
        "end": hourly[-1].timestamp.isoformat(),
        "four_hour_start": four_hour[0].timestamp.isoformat(),
        "four_hour_end": four_hour[-1].timestamp.isoformat(),
        "common_timestamp_grid": "passed",
        "hourly_cadence": "passed",
        "complete_4h_buckets": "passed",
    }


def _oos_window_payload(prepared: _PreparedHistory) -> list[dict[str, object]]:
    bars = prepared.hourly_by_symbol[TOURNAMENT_SYMBOLS[0]]
    start = len(bars) - OOS_HOURLY_BARS
    return [
        {
            "fold": index + 1,
            "start": bars[start + (index * OOS_FOLD_HOURLY_BARS)].timestamp.isoformat(),
            "end": bars[start + ((index + 1) * OOS_FOLD_HOURLY_BARS) - 1].timestamp.isoformat(),
            "hourly_bar_count": OOS_FOLD_HOURLY_BARS,
            "four_hour_bar_count": OOS_FOLD_HOURLY_BARS // 4,
        }
        for index in range(OOS_FOLD_COUNT)
    ]


def _normalized_snapshot_hash(
    bars_by_symbol: Mapping[str, Sequence[CryptoEvidenceBar]],
) -> str:
    payload = [
        {
            "symbol": symbol,
            "bars": [
                [bar.timestamp.isoformat(), _decimal_text(bar.close)]
                for bar in bars_by_symbol[symbol]
            ],
        }
        for symbol in TOURNAMENT_SYMBOLS
    ]
    return _stable_hash(payload)


def _selected_candidate_payload(candidate: Mapping[str, object]) -> dict[str, object]:
    if not candidate:
        return {}
    return {
        "candidate_id": candidate.get("candidate_id", ""),
        "candidate_fingerprint": candidate.get("candidate_fingerprint", ""),
        "candidate_decision": candidate.get("candidate_decision", ""),
        "paper_or_broker_eligible": False,
    }


def _ranking_key(item: Mapping[str, object]) -> tuple[object, ...]:
    primary = _mapping(item.get("primary"))
    eligible_rank = (
        0
        if item.get("candidate_decision")
        == "eligible_for_no_submit_shadow_evaluation"
        else 1
    )
    return (
        eligible_rank,
        -_decimal(primary.get("stress_total_return", "0")),
        -_decimal(primary.get("base_total_return", "0")),
        -_decimal(primary.get("worst_fold_return", "0")),
        _decimal(primary.get("base_max_drawdown", "0")),
        _decimal(_mapping(primary.get("base_metrics")).get("turnover", "0")),
        str(item.get("candidate_id", "")),
    )


def _stable_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _false_safety_flags() -> dict[str, bool]:
    return {field: False for field in _FALSE_SAFETY_FIELDS}


def _canonical_symbol(value: object) -> str:
    symbol = str(value).strip().upper().replace("/", "")
    if symbol not in TOURNAMENT_SYMBOLS:
        raise ValidationError("tournament CSV contains an unsupported symbol.")
    return symbol


def _utc_datetime(value: datetime | str | object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        result = value
    else:
        text = str(value).strip()
        if not text:
            raise ValidationError(f"{field_name} is required.")
        try:
            result = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be an ISO-8601 timestamp.") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValidationError(f"{field_name} must be timezone-aware.")
    return result.astimezone(UTC)


def _required_text(value: object, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


def _decimal(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError("invalid decimal tournament metric.") from exc
    if not result.is_finite():
        raise ValidationError("tournament metric must be finite.")
    return result


def _decimal_text(value: Decimal) -> str:
    if value == _ZERO:
        return "0"
    return format(value.quantize(_DECIMAL_QUANTUM), "f").rstrip("0").rstrip(".")


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _mapping_sequence(value: object) -> tuple[Mapping[str, object], ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(item for item in value if isinstance(item, Mapping))
    return ()


def _string_sequence(value: object) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(item) for item in value)
    return ()


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--refresh-packet-path", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-markdown", required=True)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        packet = run_crypto_preregistered_tournament_from_csv(
            args.input_path,
            refresh_packet_path=args.refresh_packet_path,
            as_of=args.as_of,
        )
    except ValidationError as exc:
        print(str(exc))
        return 2
    json_text = json.dumps(packet, indent=2, sort_keys=True) + "\n"
    markdown_text = render_crypto_tournament_markdown(packet)
    _write_text_atomic(Path(args.output_json), json_text)
    _write_text_atomic(Path(args.output_markdown), markdown_text)
    if args.format == "json":
        print(json_text, end="")
    else:
        print(
            "crypto_tournament_classification="
            f"{packet.get('classification', '')}"
        )
        print(
            "crypto_tournament_eligible_candidates="
            f"{packet.get('eligible_candidate_count', 0)}"
        )
        print("crypto_tournament_no_submit_enforced=true")
        print("crypto_tournament_broker_mutation_occurred=false")
        print("crypto_tournament_live_endpoint_touched=false")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
