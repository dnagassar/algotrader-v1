"""Immutable forward-OOS accrual and terminal evaluation for tournament v2.

The module is deliberately research-only. It accepts receipt-bound local
files, freezes the discovery snapshot, accrues embargo/OOS bars, and withholds
all candidate metrics until the preregistered terminal timestamp. It has no
network, broker, account, order, or paper-mutation capability.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import csv
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

from algotrader.errors import ValidationError
from algotrader.research.crypto_preregistered_tournament import (
    BASE_FEE_BPS,
    BASE_SLIPPAGE_BPS,
    STRESS_FEE_BPS,
    STRESS_SLIPPAGE_BPS,
    _CandidateSpec as _EvaluationCandidateSpec,
    _asset_returns,
    _completed_round_trips,
    _equal_weight_buy_hold_returns,
    _ranking_key,
    _strategy_targets,
    classify_crypto_tournament_candidate,
)
from algotrader.research.crypto_preregistered_tournament_v2 import (
    CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT,
    DISCOVERY_END_EXCLUSIVE,
    DISCOVERY_EXPECTED_HOURLY_BARS,
    DISCOVERY_START,
    EMBARGO_END_EXCLUSIVE,
    EMBARGO_START,
    MAXIMUM_CONSECUTIVE_MISSING_HOURS,
    MINIMUM_POSITIVE_RAW_VOLUME_FRACTION,
    MINIMUM_RAW_HOURLY_COVERAGE,
    OOS_END_EXCLUSIVE,
    OOS_FOLD_COUNT,
    OOS_FOLD_HOURLY_BARS,
    OOS_HOURLY_BARS,
    OOS_START,
    TOURNAMENT_V2_SYMBOLS,
    build_crypto_tournament_v2_preregistration,
)
from algotrader.research.crypto_strategy_evidence_battery import CryptoEvidenceBar


CRYPTO_TOURNAMENT_V2_FORWARD_OOS_SCHEMA_VERSION = (
    "v5_23_crypto_tournament_v2_forward_oos_v1"
)
CRYPTO_TOURNAMENT_V2_STATE_SCHEMA_VERSION = (
    "v5_23_crypto_tournament_v2_frozen_state_v1"
)
CRYPTO_TOURNAMENT_V2_DEFAULT_OUTPUT_ROOT = Path(
    "runs/crypto_strategy_tournament/v2/latest"
)
CRYPTO_TOURNAMENT_V2_DEFAULT_DISCOVERY_SOURCE_PATH = Path(
    "runs/crypto_strategy_tournament/v1/input/crypto_1h_1y.csv"
)
CRYPTO_TOURNAMENT_V2_DEFAULT_DISCOVERY_RECEIPT_PATH = Path(
    "runs/crypto_strategy_tournament/v1/refresh/refresh_packet.json"
)

_EXPECTED_RECEIPT_SCHEMA = "v5_22_crypto_history_refresh_adapter_receipt_v2"
_EXPECTED_SOURCE = "alpaca_market_data_crypto_bars_v1beta3"
_EXPECTED_BASIS = "alpaca_crypto_bars_v1beta3_ohlcv"
_REQUIRED_COLUMNS = {
    "timestamp", "symbol", "open", "high", "low", "close", "volume"
}
_CORE_FALSE_SAFETY_FIELDS = (
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
_EXTENDED_FALSE_SAFETY_FIELDS = (
    "paper_cancel_occurred",
    "paper_replace_occurred",
    "paper_close_occurred",
    "paper_liquidate_occurred",
)
_FALSE_SAFETY_FIELDS = _CORE_FALSE_SAFETY_FIELDS + _EXTENDED_FALSE_SAFETY_FIELDS
_FIXTURE_MARKERS = ("fixture", "synthetic", "generated_demo", "sample_data")
_ZERO = Decimal("0")
_BPS_DENOMINATOR = Decimal("10000")
_ONE = Decimal("1")
_DECIMAL_QUANTUM = Decimal("0.00000001")
_ONE_HOUR = timedelta(hours=1)

__all__ = [
    "CRYPTO_TOURNAMENT_V2_DEFAULT_DISCOVERY_RECEIPT_PATH",
    "CRYPTO_TOURNAMENT_V2_DEFAULT_DISCOVERY_SOURCE_PATH",
    "CRYPTO_TOURNAMENT_V2_DEFAULT_OUTPUT_ROOT",
    "CRYPTO_TOURNAMENT_V2_FORWARD_OOS_SCHEMA_VERSION",
    "CRYPTO_TOURNAMENT_V2_STATE_SCHEMA_VERSION",
    "export_crypto_tournament_v2_selected_shadow_context",
    "initialize_crypto_tournament_v2_forward_oos",
    "render_crypto_tournament_v2_forward_oos_markdown",
    "run_crypto_tournament_v2_forward_oos",
]


def export_crypto_tournament_v2_selected_shadow_context(
    *,
    output_root: Path | str = CRYPTO_TOURNAMENT_V2_DEFAULT_OUTPUT_ROOT,
    as_of: datetime | str,
) -> dict[str, object]:
    """Export 169 validated selected-symbol bars from one sealed v2 winner."""

    root = Path(output_root)
    evaluated_at = _utc_datetime(as_of, "as_of")
    packet = run_crypto_tournament_v2_forward_oos(
        output_root=root,
        as_of=evaluated_at,
        write_artifacts=False,
    )
    if packet.get("classification") != (
        "eligible_for_no_submit_shadow_evaluation"
    ):
        raise ValidationError(
            "selected shadow context requires one sealed eligible v2 winner."
        )
    state, _, _, raw_oos, _ = _load_and_validate_state(_state_paths(root))
    normalized, quality, errors = _normalize_window(
        raw_oos,
        start=_utc_datetime(OOS_START, "oos_start"),
        end_exclusive=_utc_datetime(OOS_END_EXCLUSIVE, "oos_end"),
        phase="shadow_context",
        strict_complete=False,
        boundary_missing_allowed=False,
    )
    if errors:
        raise ValidationError(
            "sealed v2 winner context failed replayed input quality: "
            + ",".join(errors)
        )
    selected = _mapping(packet.get("selected_candidate"))
    candidate_id = str(selected.get("candidate_id", ""))
    candidate_fingerprint = str(
        selected.get("candidate_fingerprint", "")
    )
    candidates = _mapping_sequence(
        build_crypto_tournament_v2_preregistration().get("candidates")
    )
    matches = tuple(
        dict(candidate)
        for candidate in candidates
        if candidate.get("candidate_id") == candidate_id
        and candidate.get("candidate_fingerprint") == candidate_fingerprint
    )
    if len(matches) != 1:
        raise ValidationError(
            "sealed v2 selected candidate drifted from preregistration."
        )
    candidate = matches[0]
    symbol = str(candidate.get("symbol", ""))
    selected_rows = tuple(row for row in normalized if row.symbol == symbol)
    if len(selected_rows) < 169:
        raise ValidationError(
            "sealed v2 winner lacks 169 causal context bars."
        )
    context = selected_rows[-169:]
    expected_end = _utc_datetime(OOS_END_EXCLUSIVE, "oos_end")
    if (
        context[-1].timestamp != expected_end - _ONE_HOUR
        or context[-1].imputed
    ):
        raise ValidationError(
            "sealed v2 context requires a raw final boundary bar."
        )
    terminal_path = _state_paths(root)["terminal_packet"]
    return {
        "schema_version": "v5_25_crypto_tournament_v2_shadow_context_v1",
        "record_type": "crypto_tournament_v2_selected_shadow_context",
        "as_of": evaluated_at.isoformat(),
        "candidate": candidate,
        "context_rows": [row.canonical() for row in context],
        "context_row_count": len(context),
        "context_sha256": _rows_hash(context),
        "context_quality": quality,
        "source_binding": {
            "tournament_preregistration_fingerprint": (
                CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT
            ),
            "terminal_packet_path": str(terminal_path),
            "terminal_packet_sha256": state.get(
                "terminal_packet_sha256", ""
            ),
            "terminal_evidence_fingerprint": state.get(
                "terminal_evidence_fingerprint", ""
            ),
            "state_fingerprint": state.get("state_fingerprint", ""),
            "terminal_closed_at": state.get("terminal_closed_at", ""),
        },
        "network_access_attempted": False,
        "broker_read_occurred": False,
        "broker_mutation_occurred": False,
        "paper_or_live_execution_authorized": False,
        "live_authorized": False,
        "profit_claim": "none",
    }


@dataclass(frozen=True, slots=True)
class _Bar:
    timestamp: datetime
    symbol: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    imputed: bool = False

    def key(self) -> tuple[str, datetime]:
        return (self.symbol, self.timestamp)

    def canonical(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "open": _decimal_text(self.open),
            "high": _decimal_text(self.high),
            "low": _decimal_text(self.low),
            "close": _decimal_text(self.close),
            "volume": _decimal_text(self.volume),
            "imputed": self.imputed,
        }


@dataclass(frozen=True, slots=True)
class _WindowReturnPoint:
    timestamp: datetime
    target_exposure: Decimal
    applied_exposure: Decimal
    asset_return: Decimal
    transaction_cost: Decimal
    net_return: Decimal
    boundary_transition_delta: Decimal
    signal_transition_delta: Decimal
    transition_delta: Decimal
    completed_round_trip: bool


def initialize_crypto_tournament_v2_forward_oos(
    *,
    discovery_source_path: Path | str = (
        CRYPTO_TOURNAMENT_V2_DEFAULT_DISCOVERY_SOURCE_PATH
    ),
    discovery_receipt_path: Path | str = (
        CRYPTO_TOURNAMENT_V2_DEFAULT_DISCOVERY_RECEIPT_PATH
    ),
    output_root: Path | str = CRYPTO_TOURNAMENT_V2_DEFAULT_OUTPUT_ROOT,
    as_of: datetime | str,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Freeze receipt-bound discovery state without reading v2 OOS bytes."""

    root = Path(output_root)
    paths = _state_paths(root)
    evaluated_at = _utc_datetime(as_of, "as_of")
    if evaluated_at < _utc_datetime(DISCOVERY_END_EXCLUSIVE, "discovery_end"):
        raise ValidationError("v2 discovery cannot freeze before its fixed cutoff.")
    if paths["state"].is_file():
        return run_crypto_tournament_v2_forward_oos(
            output_root=root,
            as_of=evaluated_at,
            write_artifacts=write_artifacts,
        )

    source_path = Path(discovery_source_path)
    receipt_path = Path(discovery_receipt_path)
    provenance = _validate_receipt(
        history_path=source_path,
        receipt_path=receipt_path,
        exact_symbols=False,
    )
    receipt_start = _utc_datetime(
        provenance["requested_start"], "requested_start"
    )
    receipt_end = _utc_datetime(provenance["requested_end"], "requested_end")
    discovery_start = _utc_datetime(DISCOVERY_START, "discovery_start")
    discovery_end = _utc_datetime(
        DISCOVERY_END_EXCLUSIVE, "discovery_end"
    )
    if (
        receipt_start > discovery_start
        or receipt_end != discovery_end - _ONE_HOUR
    ):
        raise ValidationError(
            "guarded receipt must end exactly at the frozen discovery cutoff."
        )
    source_rows = _load_rows(
        source_path,
        allow_symbol_superset=True,
        allow_imputed=False,
        latest_allowed_timestamp=receipt_end,
    )
    if any(
        row.timestamp < receipt_start or row.timestamp > receipt_end
        for row in source_rows
    ):
        raise ValidationError(
            "v2 discovery source contains rows outside its guarded receipt."
        )

    selected = tuple(
        row
        for row in source_rows
        if discovery_start <= row.timestamp < discovery_end
    )
    normalized, quality, errors = _normalize_window(
        selected,
        start=discovery_start,
        end_exclusive=discovery_end,
        phase="discovery",
        strict_complete=False,
        boundary_missing_allowed=True,
    )
    if errors:
        raise ValidationError(
            "v2 discovery quality gate failed: " + ",".join(errors)
        )

    manifest = build_crypto_tournament_v2_preregistration()
    empty: tuple[_Bar, ...] = ()
    ledger = {
        "schema_version": CRYPTO_TOURNAMENT_V2_STATE_SCHEMA_VERSION,
        "record_type": "crypto_tournament_v2_receipt_ledger",
        "receipts": [
            {
                "phase": "discovery_source",
                "receipt_sha256": provenance["receipt_sha256"],
                "output_sha256": provenance["output_sha256"],
                "requested_start": provenance["requested_start"],
                "requested_end": provenance["requested_end"],
                "receipt_as_of": provenance["receipt_as_of"],
                "accepted_row_count": len(selected),
            }
        ],
    }
    if write_artifacts:
        root.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(paths["preregistration"], manifest)
        _write_rows_atomic(paths["discovery"], normalized)
        _write_rows_atomic(paths["embargo"], empty)
        _write_rows_atomic(paths["oos"], empty)
        _write_json_atomic(paths["ledger"], ledger)

    state = {
        "schema_version": CRYPTO_TOURNAMENT_V2_STATE_SCHEMA_VERSION,
        "record_type": "crypto_tournament_v2_frozen_state",
        "preregistration_fingerprint": (
            CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT
        ),
        "initialized_at": evaluated_at.isoformat(),
        "updated_at": evaluated_at.isoformat(),
        "discovery_source_path": str(source_path),
        "discovery_source_sha256": provenance["output_sha256"],
        "discovery_receipt_sha256": provenance["receipt_sha256"],
        "discovery_quality": quality,
        "discovery_normalized_rows": len(normalized),
        "discovery_imputed_rows": sum(row.imputed for row in normalized),
        "embargo_raw_rows": 0,
        "oos_raw_rows": 0,
        "terminal_outcome_closed": False,
        "terminal_classification": "",
        "terminal_closed_at": "",
        "terminal_packet_sha256": "",
        "terminal_scoring_performed": False,
        "terminal_evidence_fingerprint": "",
        "artifact_sha256": _artifact_hashes(
            paths, write_artifacts=write_artifacts
        ),
    }
    state["state_fingerprint"] = _stable_hash(state)
    if write_artifacts:
        _write_json_atomic(paths["state"], state)

    packet = _build_packet(
        root=root,
        state=state,
        discovery=normalized,
        embargo=empty,
        oos=empty,
        ledger=ledger,
        as_of=evaluated_at,
        operation_network_access=False,
        operation_market_data_fetch=False,
    )
    if write_artifacts:
        _write_packet(paths, packet)
    return packet

def run_crypto_tournament_v2_forward_oos(
    *,
    output_root: Path | str = CRYPTO_TOURNAMENT_V2_DEFAULT_OUTPUT_ROOT,
    as_of: datetime | str,
    delta_history_path: Path | str | None = None,
    delta_receipt_path: Path | str | None = None,
    operation_network_access: bool = False,
    operation_market_data_fetch: bool = False,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Accrue one guarded delta or inspect the immutable v2 state."""

    if (delta_history_path is None) != (delta_receipt_path is None):
        raise ValidationError(
            "delta history and receipt paths must be supplied together."
        )
    if operation_market_data_fetch and not operation_network_access:
        raise ValidationError(
            "market-data fetch cannot occur without network access."
        )

    root = Path(output_root)
    paths = _state_paths(root)
    evaluated_at = _utc_datetime(as_of, "as_of")
    state, discovery, embargo, oos, ledger = _load_and_validate_state(paths)
    updated_at = _utc_datetime(
        state.get("updated_at"), "state_updated_at"
    )
    if evaluated_at < updated_at:
        raise ValidationError(
            "tournament v2 as_of cannot regress frozen state time."
        )
    if bool(state.get("terminal_outcome_closed", False)):
        if delta_history_path is not None:
            raise ValidationError(
                "tournament v2 terminal outcome rejects later deltas."
            )
        if operation_network_access or operation_market_data_fetch:
            raise ValidationError(
                "closed tournament v2 cannot report a new fetch."
            )
        packet = _load_terminal_packet(paths, state)
        packet["status_checked_at"] = evaluated_at.isoformat()
        packet["frozen_state"] = _state_summary(state)
        packet["next_refresh"] = {
            "classification": "terminal_window_closed",
            "requested_start": "",
            "requested_end": "",
            "as_of": evaluated_at.isoformat(),
        }
        if write_artifacts:
            _write_packet(paths, packet)
        return packet


    if delta_history_path is not None and delta_receipt_path is not None:
        history_path = Path(delta_history_path)
        receipt_path = Path(delta_receipt_path)
        provenance = _validate_receipt(
            history_path=history_path,
            receipt_path=receipt_path,
            exact_symbols=True,
        )
        receipt_start = _utc_datetime(
            provenance["requested_start"], "requested_start"
        )
        receipt_end = _utc_datetime(
            provenance["requested_end"], "requested_end"
        )
        receipt_as_of = _utc_datetime(
            provenance["receipt_as_of"], "receipt_as_of"
        )
        delta = _load_rows(
            history_path,
            allow_symbol_superset=False,
            allow_imputed=False,
            latest_allowed_timestamp=receipt_end,
        )
        embargo_start = _utc_datetime(EMBARGO_START, "embargo_start")
        oos_start = _utc_datetime(OOS_START, "oos_start")
        oos_end = _utc_datetime(OOS_END_EXCLUSIVE, "oos_end")
        if receipt_start < embargo_start or receipt_end >= oos_end:
            raise ValidationError(
                "v2 delta receipt falls outside the frozen accrual window."
            )
        if receipt_as_of > _floor_hour(evaluated_at):
            raise ValidationError(
                "v2 delta receipt is later than the evaluation as-of."
            )
        if any(
            row.timestamp < receipt_start or row.timestamp > receipt_end
            for row in delta
        ):
            raise ValidationError(
                "v2 delta contains rows outside its guarded receipt."
            )
        if any(row.timestamp >= _floor_hour(evaluated_at) for row in delta):
            raise ValidationError(
                "v2 delta contains an incomplete/lookahead hour."
            )

        embargo_delta = tuple(
            row
            for row in delta
            if embargo_start <= row.timestamp < oos_start
        )
        oos_delta = tuple(
            row for row in delta if oos_start <= row.timestamp < oos_end
        )
        embargo, embargo_new, embargo_duplicate = _merge_raw_rows(
            embargo, embargo_delta
        )
        oos, oos_new, oos_duplicate = _merge_raw_rows(oos, oos_delta)
        receipt_entry = {
            "phase": "embargo_and_oos_delta",
            "receipt_sha256": provenance["receipt_sha256"],
            "output_sha256": provenance["output_sha256"],
            "requested_start": provenance["requested_start"],
            "requested_end": provenance["requested_end"],
            "receipt_as_of": provenance["receipt_as_of"],
            "accepted_row_count": len(delta),
            "new_row_count": embargo_new + oos_new,
            "exact_duplicate_row_count": (
                embargo_duplicate + oos_duplicate
            ),
        }
        existing_receipts = list(
            _mapping_sequence(ledger.get("receipts"))
        )
        ledger_key = (
            receipt_entry["receipt_sha256"],
            receipt_entry["output_sha256"],
        )
        if not any(
            (
                item.get("receipt_sha256"),
                item.get("output_sha256"),
            )
            == ledger_key
            for item in existing_receipts
        ):
            existing_receipts.append(receipt_entry)
        ledger = {**ledger, "receipts": existing_receipts}

        if write_artifacts:
            _write_rows_atomic(paths["embargo"], embargo)
            _write_rows_atomic(paths["oos"], oos)
            _write_json_atomic(paths["ledger"], ledger)
        state = _updated_state(
            state,
            paths=paths,
            as_of=evaluated_at,
            embargo=embargo,
            oos=oos,
            write_artifacts=write_artifacts,
        )
        if write_artifacts:
            _write_json_atomic(paths["state"], state)

    packet = _build_packet(
        root=root,
        state=state,
        discovery=discovery,
        embargo=embargo,
        oos=oos,
        ledger=ledger,
        as_of=evaluated_at,
        operation_network_access=operation_network_access,
        operation_market_data_fetch=operation_market_data_fetch,
    )
    terminal_closed = packet.get("phase") in {
        "terminal_scored",
        "terminal_closed_without_candidate_scoring",
    }
    if terminal_closed:
        if not packet.get("terminal_evidence_fingerprint"):
            packet["terminal_evidence_fingerprint"] = _stable_hash(
                {
                    "preregistration_fingerprint": (
                        CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT
                    ),
                    "classification": packet.get("classification", ""),
                    "terminal_input_quality": packet.get(
                        "terminal_input_quality", {}
                    ),
                    "discovery_hash": _rows_hash(discovery),
                    "embargo_hash": _rows_hash(embargo),
                    "oos_hash": _rows_hash(oos),
                }
            )
        packet["next_refresh"] = {
            "classification": "terminal_window_closed",
            "requested_start": "",
            "requested_end": "",
            "as_of": evaluated_at.isoformat(),
        }
        packet["terminal_closure"] = {
            "terminal_outcome_closed": True,
            "terminal_classification": str(
                packet.get("classification", "")
            ),
            "terminal_closed_at": evaluated_at.isoformat(),
            "terminal_scoring_performed": bool(
                packet.get("terminal_scoring_performed", False)
            ),
            "terminal_evidence_fingerprint": str(
                packet.get("terminal_evidence_fingerprint", "")
            ),
        }
        packet.pop("frozen_state", None)
        if write_artifacts:
            _write_json_atomic(paths["terminal_packet"], packet)
            terminal_packet_sha256 = _file_sha256(
                paths["terminal_packet"]
            )
        else:
            terminal_packet_sha256 = _stable_hash(packet)
        state = _updated_state(
            state,
            paths=paths,
            as_of=evaluated_at,
            embargo=embargo,
            oos=oos,
            write_artifacts=write_artifacts,
            terminal_outcome_closed=True,
            terminal_classification=str(
                packet.get("classification", "")
            ),
            terminal_closed_at=evaluated_at.isoformat(),
            terminal_packet_sha256=terminal_packet_sha256,
            terminal_scoring_performed=bool(
                packet.get("terminal_scoring_performed", False)
            ),
            terminal_evidence_fingerprint=str(
                packet.get("terminal_evidence_fingerprint", "")
            ),
        )
        if write_artifacts:
            _write_json_atomic(paths["state"], state)
        packet["frozen_state"] = _state_summary(state)
    if write_artifacts:
        _write_packet(paths, packet)
    return packet


def _build_packet(
    *,
    root: Path,
    state: Mapping[str, object],
    discovery: Sequence[_Bar],
    embargo: Sequence[_Bar],
    oos: Sequence[_Bar],
    ledger: Mapping[str, object],
    as_of: datetime,
    operation_network_access: bool,
    operation_market_data_fetch: bool,
) -> dict[str, object]:
    embargo_start = _utc_datetime(EMBARGO_START, "embargo_start")
    embargo_end = _utc_datetime(EMBARGO_END_EXCLUSIVE, "embargo_end")
    oos_start = _utc_datetime(OOS_START, "oos_start")
    oos_end = _utc_datetime(OOS_END_EXCLUSIVE, "oos_end")
    packet: dict[str, object] = {
        "schema_version": CRYPTO_TOURNAMENT_V2_FORWARD_OOS_SCHEMA_VERSION,
        "record_type": "crypto_tournament_v2_forward_oos_packet",
        "as_of": as_of.isoformat(),
        "output_root": str(root),
        "preregistration_fingerprint": (
            CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT
        ),
        "predecessor_v1_status": "closed_terminal_input_quality_gate",
        "frozen_state": _state_summary(state),
        "discovery": {
            "start": DISCOVERY_START,
            "end_exclusive": DISCOVERY_END_EXCLUSIVE,
            "expected_rows_per_symbol": DISCOVERY_EXPECTED_HOURLY_BARS,
            "normalized_rows": len(discovery),
            "imputed_rows": sum(row.imputed for row in discovery),
            "candidate_metrics_included": False,
        },
        "embargo_progress": _progress_payload(
            embargo,
            start=embargo_start,
            end_exclusive=embargo_end,
            as_of=as_of,
        ),
        "oos_progress": _progress_payload(
            oos,
            start=oos_start,
            end_exclusive=oos_end,
            as_of=as_of,
        ),
        "receipt_count": len(_mapping_sequence(ledger.get("receipts"))),
        "candidate_evaluations": [],
        "ranking": [],
        "selected_candidate": {},
        "qualified_candidate_count": 0,
        "terminal_scoring_performed": False,
        "terminal_evidence_fingerprint": "",
        "paper_or_broker_eligible": False,
        "paper_planning_eligibility": "not_eligible",
        "paper_or_live_execution_authorized": False,
        "subsequent_single_winner_untouched_forward_shadow_required": True,
        "network_access_attempted": operation_network_access,
        "market_data_fetch_occurred": operation_market_data_fetch,
        "broker_read_occurred": False,
        "broker_mutation_authorized": False,
        "broker_mutation_occurred": False,
        "paper_submit_authorized": False,
        "paper_submit_occurred": False,
        "paper_cancel_occurred": False,
        "paper_replace_occurred": False,
        "paper_close_occurred": False,
        "paper_liquidate_occurred": False,
        "live_authorized": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "profit_claim": "none",
    }
    packet["next_refresh"] = _next_refresh_payload(
        embargo=embargo,
        oos=oos,
        as_of=as_of,
    )
    if as_of < oos_start:
        packet["classification"] = "research_ready_for_future_oos_accrual"
        packet["phase"] = "collecting_embargo_signal_warmup"
        return packet
    if as_of < oos_end:
        packet["classification"] = "collecting_untouched_oos"
        packet["phase"] = "untouched_oos_accrual"
        return packet

    terminal_receipt_end = (
        _utc_datetime(OOS_END_EXCLUSIVE, "oos_end")
        - _ONE_HOUR
    ).isoformat()
    terminal_receipt_bound = any(
        item.get("phase") == "embargo_and_oos_delta"
        and item.get("requested_end") == terminal_receipt_end
        for item in _mapping_sequence(ledger.get("receipts"))
    )
    if not terminal_receipt_bound:
        packet["classification"] = "awaiting_terminal_market_data_receipt"
        packet["phase"] = "awaiting_terminal_refresh"
        packet["candidate_evaluations"] = []
        packet["ranking"] = []
        packet["selected_candidate"] = {}
        return packet

    normalized_embargo, embargo_quality, embargo_errors = _normalize_window(
        embargo,
        start=embargo_start,
        end_exclusive=embargo_end,
        phase="embargo",
        strict_complete=True,
        boundary_missing_allowed=False,
    )
    normalized_oos, oos_quality, oos_errors = _normalize_window(
        oos,
        start=oos_start,
        end_exclusive=oos_end,
        phase="oos",
        strict_complete=False,
        boundary_missing_allowed=False,
    )
    packet["terminal_input_quality"] = {
        "embargo": embargo_quality,
        "oos": oos_quality,
        "errors": list(embargo_errors + oos_errors),
    }
    if embargo_errors or oos_errors:
        packet["classification"] = "terminal_input_quality_gate"
        packet["phase"] = "terminal_closed_without_candidate_scoring"
        return packet

    evaluations = _terminal_evaluations(
        discovery=discovery,
        embargo=normalized_embargo,
        oos=normalized_oos,
    )
    ranking = sorted(evaluations, key=_ranking_key)
    eligible, selected = _eligible_and_selected(ranking)
    evidence_fingerprint = _stable_hash(
        {
            "preregistration_fingerprint": (
                CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT
            ),
            "discovery_hash": _rows_hash(discovery),
            "embargo_hash": _rows_hash(normalized_embargo),
            "oos_hash": _rows_hash(normalized_oos),
            "evaluations": evaluations,
            "selected_candidate": selected,
        }
    )
    packet.update(
        {
            "classification": (
                "eligible_for_no_submit_shadow_evaluation"
                if selected
                else "no_candidate_qualified"
            ),
            "phase": "terminal_scored",
            "candidate_evaluations": evaluations,
            "ranking": [
                str(item.get("candidate_id", "")) for item in ranking
            ],
            "selected_candidate": selected,
            "qualified_candidate_count": len(eligible),
            "terminal_scoring_performed": True,
            "terminal_evidence_fingerprint": evidence_fingerprint,
        }
    )
    return packet

def _terminal_evaluations(
    *,
    discovery: Sequence[_Bar],
    embargo: Sequence[_Bar],
    oos: Sequence[_Bar],
) -> list[dict[str, object]]:
    manifest = build_crypto_tournament_v2_preregistration()
    discovery_by_symbol = _by_symbol(discovery)
    embargo_by_symbol = _by_symbol(embargo)
    oos_by_symbol = _by_symbol(oos)
    combined_by_symbol = {
        symbol: (
            discovery_by_symbol[symbol]
            + embargo_by_symbol[symbol]
            + oos_by_symbol[symbol]
        )
        for symbol in TOURNAMENT_V2_SYMBOLS
    }
    combined_4h_by_symbol = {
        symbol: _aggregate_four_hour(combined_by_symbol[symbol])
        for symbol in TOURNAMENT_V2_SYMBOLS
    }
    oos_4h_by_symbol = {
        symbol: tuple(
            row
            for row in combined_4h_by_symbol[symbol]
            if _utc_datetime(OOS_START, "oos_start")
            <= row.timestamp
            < _utc_datetime(OOS_END_EXCLUSIVE, "oos_end")
        )
        for symbol in TOURNAMENT_V2_SYMBOLS
    }
    candidates = _mapping_sequence(manifest.get("candidates"))
    evaluations: list[dict[str, object]] = []
    for candidate in candidates:
        symbol = str(candidate["symbol"])
        spec = _spec_from_candidate(candidate)
        primary = _timeframe_evaluation(
            symbol=symbol,
            spec=spec,
            timeframe_hours=1,
            combined=combined_by_symbol[symbol],
            bars_by_symbol=combined_by_symbol,
        )
        robustness = _timeframe_evaluation(
            symbol=symbol,
            spec=spec,
            timeframe_hours=4,
            combined=combined_4h_by_symbol[symbol],
            bars_by_symbol=combined_4h_by_symbol,
        )
        discovery_targets = _targets_with_imputation_hold(
            discovery_by_symbol[symbol],
            spec,
            timeframe_hours=1,
        )
        combined_targets = _targets_with_imputation_hold(
            combined_by_symbol[symbol],
            spec,
            timeframe_hours=1,
        )
        oos_start_index = len(discovery_by_symbol[symbol]) + len(
            embargo_by_symbol[symbol]
        )
        oos_targets = combined_targets[oos_start_index:]
        round_trips = (
            _completed_round_trips(discovery_targets)
            + _completed_round_trips_with_initial(
                oos_targets,
                initial_exposure=combined_targets[oos_start_index - 1],
            )
        )
        decision, reasons = classify_crypto_tournament_candidate(
            primary=primary,
            robustness=robustness,
            completed_round_trips_full_sample=round_trips,
        )
        evaluations.append(
            {
                "candidate_id": candidate["candidate_id"],
                "candidate_fingerprint": candidate[
                    "candidate_fingerprint"
                ],
                "symbol": symbol,
                "strategy_id": candidate["strategy_id"],
                "strategy_family": candidate["strategy_family"],
                "elapsed_hour_parameters": candidate[
                    "elapsed_hour_parameters"
                ],
                "completed_round_trips_discovery_plus_oos": round_trips,
                "embargo_round_trips_excluded": True,
                "candidate_decision": decision,
                "rejection_reasons": list(reasons),
                "primary": primary,
                "robustness": robustness,
                "paper_or_broker_eligible": False,
            }
        )
    return evaluations


def _timeframe_evaluation(
    *,
    symbol: str,
    spec: _EvaluationCandidateSpec,
    timeframe_hours: int,
    combined: Sequence[_Bar],
    bars_by_symbol: Mapping[str, Sequence[_Bar]],
) -> dict[str, object]:
    oos_start = _utc_datetime(OOS_START, "oos_start")
    start = next(
        index
        for index, row in enumerate(combined)
        if row.timestamp >= oos_start
    )
    all_targets = _targets_with_imputation_hold(
        combined,
        spec,
        timeframe_hours=timeframe_hours,
    )
    initial_exposure = all_targets[start - 1]
    targets = all_targets[start:]
    oos_rows = tuple(combined[start:])
    expected = OOS_HOURLY_BARS // timeframe_hours
    if len(oos_rows) != expected:
        raise ValidationError(
            "terminal OOS bar count drifted from preregistration."
        )
    timestamps = tuple(row.timestamp for row in oos_rows)
    returns = _asset_returns(
        (combined[start - 1].close,)
        + tuple(row.close for row in oos_rows)
    )[1:]
    base_points = _simulate_window(
        initial_exposure=initial_exposure,
        timestamps=timestamps,
        asset_returns=returns,
        targets=targets,
        fee_bps=BASE_FEE_BPS,
        slippage_bps=BASE_SLIPPAGE_BPS,
    )
    stress_points = _simulate_window(
        initial_exposure=initial_exposure,
        timestamps=timestamps,
        asset_returns=returns,
        targets=targets,
        fee_bps=STRESS_FEE_BPS,
        slippage_bps=STRESS_SLIPPAGE_BPS,
    )
    base_metrics = _window_metrics(base_points)
    stress_metrics = _window_metrics(stress_points)
    benchmarks = _benchmark_evaluation(
        symbol=symbol,
        bars_by_symbol=bars_by_symbol,
    )
    fold_bars = OOS_FOLD_HOURLY_BARS // timeframe_hours
    fold_metrics = [
        _window_metrics(
            base_points[index * fold_bars : (index + 1) * fold_bars]
        )
        for index in range(OOS_FOLD_COUNT)
    ]
    fold_returns = tuple(
        _decimal(item["total_return"]) for item in fold_metrics
    )
    positive = tuple(value for value in fold_returns if value > _ZERO)
    positive_sum = sum(positive, _ZERO)
    concentration = max(positive) / positive_sum if positive else _ONE
    return {
        "timeframe": "1Hour" if timeframe_hours == 1 else "4Hour",
        "timeframe_hours": timeframe_hours,
        "parameters": spec.timeframe_parameters(timeframe_hours),
        "oos_start": timestamps[0].isoformat(),
        "oos_end": timestamps[-1].isoformat(),
        "oos_bar_count": len(timestamps),
        "oos_imputed_bar_count": sum(row.imputed for row in oos_rows),
        "imputed_signal_transition_count": sum(
            int(point.signal_transition_delta)
            for point, row in zip(base_points, oos_rows)
            if row.imputed
        ),
        "imputed_transition_policy": "hold_prior_target_no_transition",
        "base_metrics": base_metrics,
        "stress_metrics": stress_metrics,
        "base_total_return": base_metrics["total_return"],
        "stress_total_return": stress_metrics["total_return"],
        "base_max_drawdown": base_metrics["max_drawdown"],
        "oos_boundary_entry_transition_count": int(
            base_points[0].boundary_transition_delta
        ),
        "first_oos_signal_transition_count": int(
            base_points[0].signal_transition_delta
        ),
        "oos_transition_count": int(base_metrics["transition_count"]),
        "folds": [
            {"fold": index + 1, **metrics}
            for index, metrics in enumerate(fold_metrics)
        ],
        "positive_fold_count": sum(
            value > _ZERO for value in fold_returns
        ),
        "positive_profit_concentration": _decimal_text(concentration),
        "worst_fold_return": _decimal_text(min(fold_returns)),
        "benchmarks": benchmarks,
        "base_excess_vs_buy_hold": _decimal_text(
            _decimal(base_metrics["total_return"])
            - _decimal(
                _mapping(benchmarks["base"])["buy_hold_total_return"]
            )
        ),
        "base_excess_vs_basket": _decimal_text(
            _decimal(base_metrics["total_return"])
            - _decimal(_mapping(benchmarks["base"])["basket_total_return"])
        ),
        "stress_excess_vs_buy_hold": _decimal_text(
            _decimal(stress_metrics["total_return"])
            - _decimal(
                _mapping(benchmarks["stress"])["buy_hold_total_return"]
            )
        ),
        "stress_excess_vs_basket": _decimal_text(
            _decimal(stress_metrics["total_return"])
            - _decimal(
                _mapping(benchmarks["stress"])["basket_total_return"]
            )
        ),
    }

def _benchmark_evaluation(
    *,
    symbol: str,
    bars_by_symbol: Mapping[str, Sequence[_Bar]],
) -> dict[str, object]:
    oos_start = _utc_datetime(OOS_START, "oos_start")
    starts = {
        candidate_symbol: next(
            index
            for index, row in enumerate(
                bars_by_symbol[candidate_symbol]
            )
            if row.timestamp >= oos_start
        )
        for candidate_symbol in TOURNAMENT_V2_SYMBOLS
    }
    symbol_rows = tuple(
        bars_by_symbol[symbol][starts[symbol] :]
    )
    timestamps = tuple(row.timestamp for row in symbol_rows)
    buy_hold_returns = _asset_returns(
        (
            bars_by_symbol[symbol][starts[symbol] - 1].close,
        )
        + tuple(row.close for row in symbol_rows)
    )[1:]
    basket_returns = _equal_weight_buy_hold_returns(
        {
            candidate_symbol: tuple(
                row.close
                for row in bars_by_symbol[candidate_symbol][
                    starts[candidate_symbol] - 1 :
                ]
            )
            for candidate_symbol in TOURNAMENT_V2_SYMBOLS
        }
    )[1:]
    targets = tuple(_ONE for _ in timestamps)
    result: dict[str, object] = {}
    for label, fee_bps, slippage_bps in (
        ("base", BASE_FEE_BPS, BASE_SLIPPAGE_BPS),
        ("stress", STRESS_FEE_BPS, STRESS_SLIPPAGE_BPS),
    ):
        buy_hold = _window_metrics(
            _simulate_window(
                initial_exposure=_ONE,
                timestamps=timestamps,
                asset_returns=buy_hold_returns,
                targets=targets,
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
            )
        )
        basket = _window_metrics(
            _simulate_window(
                initial_exposure=_ONE,
                timestamps=timestamps,
                asset_returns=basket_returns,
                targets=targets,
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
            )
        )
        result[label] = {
            "cash_total_return": "0",
            "buy_hold_total_return": buy_hold["total_return"],
            "buy_hold_max_drawdown": buy_hold["max_drawdown"],
            "basket_total_return": basket["total_return"],
            "basket_max_drawdown": basket["max_drawdown"],
            "basket_semantics": (
                "equal_weight_at_oos_start_then_drift_no_rebalancing"
            ),
        }
    return result


def _simulate_window(
    *,
    initial_exposure: Decimal,
    timestamps: Sequence[datetime],
    asset_returns: Sequence[Decimal],
    targets: Sequence[Decimal],
    fee_bps: Decimal,
    slippage_bps: Decimal,
) -> tuple[_WindowReturnPoint, ...]:
    if not (len(timestamps) == len(asset_returns) == len(targets)):
        raise ValidationError("v2 terminal simulation inputs must align.")
    if initial_exposure not in {_ZERO, _ONE}:
        raise ValidationError("v2 initial exposure must be binary.")

    cost_rate = (fee_bps + slippage_bps) / _BPS_DENOMINATOR
    previous_exposure = initial_exposure
    points: list[_WindowReturnPoint] = []
    for index, (timestamp, asset_return, target) in enumerate(
        zip(timestamps, asset_returns, targets)
    ):
        if target not in {_ZERO, _ONE}:
            raise ValidationError("v2 target exposure must be binary.")
        if asset_return <= -_ONE:
            raise ValidationError("v2 asset return must be greater than -1.")

        boundary_transition = (
            abs(initial_exposure - _ZERO) if index == 0 else _ZERO
        )
        signal_transition = abs(target - previous_exposure)
        boundary_cost = boundary_transition * cost_rate
        signal_cost = signal_transition * cost_rate
        gross_multiplier = _ONE + (previous_exposure * asset_return)
        net_multiplier = (
            (_ONE - boundary_cost)
            * gross_multiplier
            * (_ONE - signal_cost)
        )
        points.append(
            _WindowReturnPoint(
                timestamp=timestamp,
                target_exposure=target,
                applied_exposure=previous_exposure,
                asset_return=asset_return,
                transaction_cost=boundary_cost + signal_cost,
                net_return=net_multiplier - _ONE,
                boundary_transition_delta=boundary_transition,
                signal_transition_delta=signal_transition,
                transition_delta=boundary_transition + signal_transition,
                completed_round_trip=(
                    previous_exposure == _ONE and target == _ZERO
                ),
            )
        )
        previous_exposure = target
    return tuple(points)


def _window_metrics(
    points: Sequence[_WindowReturnPoint],
) -> dict[str, object]:
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
        transitions += int(point.transition_delta)
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


def _completed_round_trips_with_initial(
    targets: Sequence[Decimal],
    *,
    initial_exposure: Decimal,
) -> int:
    previous = initial_exposure
    count = 0
    for target in targets:
        if previous == _ONE and target == _ZERO:
            count += 1
        previous = target
    return count

def _targets_with_imputation_hold(
    rows: Sequence[_Bar],
    spec: _EvaluationCandidateSpec,
    *,
    timeframe_hours: int,
) -> tuple[Decimal, ...]:
    evidence = tuple(
        CryptoEvidenceBar(
            symbol=row.symbol,
            timestamp=row.timestamp,
            close=row.close,
        )
        for row in rows
    )
    targets = list(
        _strategy_targets(
            evidence,
            spec,
            timeframe_hours=timeframe_hours,
        )
    )
    for index, row in enumerate(rows):
        if row.imputed:
            targets[index] = targets[index - 1] if index else _ZERO
    return tuple(targets)


def _aggregate_four_hour(rows: Sequence[_Bar]) -> tuple[_Bar, ...]:
    if len(rows) % 4:
        raise ValidationError(
            "v2 history must form complete four-hour buckets."
        )
    result: list[_Bar] = []
    for offset in range(0, len(rows), 4):
        bucket = tuple(rows[offset : offset + 4])
        start = bucket[0].timestamp
        if (
            start.hour % 4
            or start.minute
            or start.second
            or start.microsecond
        ):
            raise ValidationError(
                "v2 four-hour buckets must align to UTC."
            )
        if tuple(row.timestamp for row in bucket) != tuple(
            start + timedelta(hours=index) for index in range(4)
        ):
            raise ValidationError("v2 four-hour bucket is incomplete.")
        result.append(
            _Bar(
                timestamp=bucket[-1].timestamp,
                symbol=bucket[0].symbol,
                open=bucket[0].open,
                high=max(row.high for row in bucket),
                low=min(row.low for row in bucket),
                close=bucket[-1].close,
                volume=sum((row.volume for row in bucket), _ZERO),
                imputed=any(row.imputed for row in bucket),
            )
        )
    return tuple(result)


def _normalize_window(
    rows: Sequence[_Bar],
    *,
    start: datetime,
    end_exclusive: datetime,
    phase: str,
    strict_complete: bool,
    boundary_missing_allowed: bool,
) -> tuple[tuple[_Bar, ...], dict[str, object], tuple[str, ...]]:
    expected = tuple(_hour_grid(start, end_exclusive))
    expected_set = set(expected)
    by_symbol = _by_symbol(rows)
    normalized_by_symbol: dict[str, tuple[_Bar, ...]] = {}
    stats: dict[str, object] = {}
    errors: list[str] = []
    minimum_coverage = (
        _ONE
        if strict_complete
        else _decimal(MINIMUM_RAW_HOURLY_COVERAGE)
    )
    minimum_volume = _decimal(
        MINIMUM_POSITIVE_RAW_VOLUME_FRACTION
    )
    for symbol in TOURNAMENT_V2_SYMBOLS:
        observed = {row.timestamp: row for row in by_symbol[symbol]}
        if set(observed) - expected_set:
            errors.append(f"{phase}_{symbol}_outside_window")
        missing = [
            timestamp for timestamp in expected if timestamp not in observed
        ]
        raw_count = len(expected) - len(missing)
        coverage = Decimal(raw_count) / Decimal(len(expected))
        raw_rows = tuple(
            observed[timestamp]
            for timestamp in expected
            if timestamp in observed
        )
        positive_fraction = (
            Decimal(sum(row.volume > _ZERO for row in raw_rows))
            / Decimal(raw_count)
            if raw_count
            else _ZERO
        )
        max_gap = _maximum_consecutive_gap(expected, set(missing))
        if coverage < minimum_coverage:
            errors.append(
                f"{phase}_{symbol}_raw_coverage_below_threshold"
            )
        if positive_fraction < minimum_volume:
            errors.append(
                f"{phase}_{symbol}_positive_volume_below_threshold"
            )
        allowed_gap = (
            0 if strict_complete else MAXIMUM_CONSECUTIVE_MISSING_HOURS
        )
        if max_gap > allowed_gap:
            errors.append(f"{phase}_{symbol}_consecutive_gap_exceeded")
        if not boundary_missing_allowed and (
            expected[0] in missing or expected[-1] in missing
        ):
            errors.append(f"{phase}_{symbol}_boundary_bar_missing")
        output: list[_Bar] = []
        for timestamp in expected:
            row = observed.get(timestamp)
            if row is not None:
                output.append(row)
                continue
            if strict_complete or not output:
                continue
            prior = output[-1]
            output.append(
                _Bar(
                    timestamp=timestamp,
                    symbol=symbol,
                    open=prior.close,
                    high=prior.close,
                    low=prior.close,
                    close=prior.close,
                    volume=_ZERO,
                    imputed=True,
                )
            )
        if len(output) == len(expected):
            normalized_by_symbol[symbol] = tuple(output)
        stats[symbol] = {
            "expected_raw_rows": len(expected),
            "observed_raw_rows": raw_count,
            "raw_coverage": _decimal_text(coverage),
            "positive_raw_volume_fraction": _decimal_text(
                positive_fraction
            ),
            "missing_timestamps": [
                item.isoformat() for item in missing
            ],
            "maximum_consecutive_missing_hours": max_gap,
            "imputed_rows": sum(row.imputed for row in output),
        }
    if len(normalized_by_symbol) != len(TOURNAMENT_V2_SYMBOLS):
        errors.append(f"{phase}_normalized_common_grid_incomplete")
    normalized = tuple(
        row
        for symbol in TOURNAMENT_V2_SYMBOLS
        for row in normalized_by_symbol.get(symbol, ())
    )
    quality = {
        "phase": phase,
        "status": "passed" if not errors else "failed",
        "start": start.isoformat(),
        "end_exclusive": end_exclusive.isoformat(),
        "symbols": stats,
        "isolated_gap_fill": "prior_close_ohlc_zero_volume",
        "imputation_explicit": True,
    }
    return normalized, quality, tuple(dict.fromkeys(errors))

def _load_rows(
    path: Path,
    *,
    allow_symbol_superset: bool,
    allow_imputed: bool,
    latest_allowed_timestamp: datetime | None = None,
) -> tuple[_Bar, ...]:
    if not path.is_file():
        raise ValidationError("v2 history path is missing.")
    rows: list[_Bar] = []
    seen: set[tuple[str, datetime]] = set()
    previous: dict[str, datetime] = {}
    try:
        with path.open(
            "r", encoding="utf-8-sig", newline=""
        ) as stream:
            reader = csv.DictReader(stream)
            fields = set(reader.fieldnames or ())
            if not _REQUIRED_COLUMNS.issubset(fields):
                raise ValidationError(
                    "v2 history does not match canonical OHLCV schema."
                )
            for raw in reader:
                symbol_text = (
                    str(raw.get("symbol", ""))
                    .strip()
                    .upper()
                    .replace("/", "")
                )
                timestamp = _utc_datetime(
                    raw.get("timestamp", ""), "timestamp"
                )
                if (
                    latest_allowed_timestamp is not None
                    and timestamp > latest_allowed_timestamp
                ):
                    raise ValidationError(
                        "v2 history contains rows after its guarded cutoff."
                    )
                if symbol_text not in TOURNAMENT_V2_SYMBOLS:
                    if allow_symbol_superset:
                        continue
                    raise ValidationError(
                        "v2 delta contains an unsupported symbol."
                    )
                key = (symbol_text, timestamp)
                if key in seen:
                    raise ValidationError(
                        "duplicate v2 symbol/timestamp row."
                    )
                if (
                    symbol_text in previous
                    and timestamp <= previous[symbol_text]
                ):
                    raise ValidationError(
                        "v2 rows must be chronological per symbol."
                    )
                seen.add(key)
                previous[symbol_text] = timestamp
                if (
                    "asset_class" in fields
                    and str(raw.get("asset_class", "")).strip().lower()
                    != "crypto"
                ):
                    raise ValidationError(
                        "v2 history asset_class must be crypto."
                    )
                if (
                    "basis" in fields
                    and str(raw.get("basis", "")).strip()
                    != _EXPECTED_BASIS
                ):
                    raise ValidationError(
                        "v2 history basis is not the guarded OHLCV basis."
                    )
                if "source" in fields:
                    source = str(raw.get("source", "")).strip()
                    if source != _EXPECTED_SOURCE:
                        raise ValidationError(
                            "v2 history source is not the guarded source."
                        )
                    if any(
                        marker in source.lower()
                        for marker in _FIXTURE_MARKERS
                    ):
                        raise ValidationError(
                            "fixture history cannot enter tournament v2."
                        )
                imputed = (
                    _bool_field(raw.get("imputed", False))
                    if "imputed" in fields
                    else False
                )
                if imputed and not allow_imputed:
                    raise ValidationError(
                        "receipt-bound source rows cannot be pre-imputed."
                    )
                bar = _Bar(
                    timestamp=timestamp,
                    symbol=symbol_text,
                    open=_positive_decimal(raw.get("open"), "open"),
                    high=_positive_decimal(raw.get("high"), "high"),
                    low=_positive_decimal(raw.get("low"), "low"),
                    close=_positive_decimal(raw.get("close"), "close"),
                    volume=_non_negative_decimal(
                        raw.get("volume"), "volume"
                    ),
                    imputed=imputed,
                )
                if (
                    bar.low > min(bar.open, bar.close)
                    or bar.high < max(bar.open, bar.close)
                    or bar.low > bar.high
                ):
                    raise ValidationError(
                        "v2 OHLC row is internally inconsistent."
                    )
                rows.append(bar)
    except OSError as exc:
        raise ValidationError("unable to read v2 history.") from exc
    return tuple(sorted(rows, key=_row_sort_key))


def _validate_receipt(
    *,
    history_path: Path,
    receipt_path: Path,
    exact_symbols: bool,
) -> dict[str, object]:
    packet = _read_json_mapping(receipt_path)
    if not packet:
        raise ValidationError("guarded v2 refresh receipt is required.")
    required = {
        "schema_version": _EXPECTED_RECEIPT_SCHEMA,
        "record_type": "crypto_history_refresh_adapter_packet",
        "mode": "market_data_fetch",
        "authorization_status": "authorized",
        "endpoint_safety_status": (
            "passed_non_live_endpoint_check"
        ),
        "data_source": _EXPECTED_SOURCE,
        "timeframe": "1Hour",
        "loc": "us",
        "schema_validation_status": "passed",
    }
    for field, expected in required.items():
        if str(packet.get(field, "")) != expected:
            raise ValidationError(
                f"guarded v2 receipt field mismatch: {field}."
            )
    if (
        packet.get("market_data_fetch_occurred") is not True
        or packet.get("network_access_attempted") is not True
    ):
        raise ValidationError(
            "guarded v2 receipt does not prove a market-data fetch."
        )
    required_false = (
        _FALSE_SAFETY_FIELDS
        if exact_symbols
        else _CORE_FALSE_SAFETY_FIELDS
    )
    if any(
        field not in packet or packet.get(field) is not False
        for field in required_false
    ) or any(
        field in packet and packet.get(field) is not False
        for field in _EXTENDED_FALSE_SAFETY_FIELDS
    ):
        raise ValidationError(
            "guarded v2 receipt violates a no-mutation safety field."
        )
    if exact_symbols and (
        packet.get("data_intake_only") is not True
        or packet.get("strategy_evidence_evaluation_performed") is not False
    ):
        raise ValidationError(
            "v2 accrual requires a data-intake-only refresh receipt."
        )
    requested = set(
        _string_sequence(packet.get("requested_symbols"))
    )
    fetched = set(_string_sequence(packet.get("fetched_symbols")))
    wanted = set(TOURNAMENT_V2_SYMBOLS)
    if exact_symbols:
        symbols_valid = requested == wanted and fetched == wanted
    else:
        symbols_valid = (
            requested.issuperset(wanted)
            and fetched.issuperset(wanted)
        )
    if not symbols_valid:
        raise ValidationError(
            "guarded v2 receipt does not bind the frozen symbols."
        )
    packet_output = Path(
        _required_text(packet.get("output_path"), "output_path")
    )
    if packet_output.resolve() != history_path.resolve():
        raise ValidationError(
            "guarded v2 receipt output path mismatch."
        )
    output_sha = _file_sha256(history_path)
    if str(packet.get("output_sha256", "")).lower() != output_sha:
        raise ValidationError(
            "guarded v2 receipt output SHA-256 mismatch."
        )
    requested_start = _utc_datetime(
        packet.get("requested_start"), "requested_start"
    )
    requested_end = _utc_datetime(
        packet.get("requested_end"), "requested_end"
    )
    receipt_as_of = _utc_datetime(
        packet.get("as_of"), "receipt_as_of"
    )
    if (
        requested_end < requested_start
        or requested_end + _ONE_HOUR != receipt_as_of
    ):
        raise ValidationError(
            "guarded v2 receipt must end at the last completed hour."
        )
    if any(
        value.minute or value.second or value.microsecond
        for value in (requested_start, requested_end, receipt_as_of)
    ):
        raise ValidationError(
            "guarded v2 receipt must align to UTC hours."
        )
    return {
        "receipt_sha256": _file_sha256(receipt_path),
        "output_sha256": output_sha,
        "requested_start": requested_start.isoformat(),
        "requested_end": requested_end.isoformat(),
        "receipt_as_of": receipt_as_of.isoformat(),
    }


def _load_and_validate_state(
    paths: Mapping[str, Path],
) -> tuple[
    dict[str, object],
    tuple[_Bar, ...],
    tuple[_Bar, ...],
    tuple[_Bar, ...],
    dict[str, object],
]:
    state = _read_json_mapping(paths["state"])
    if not state:
        raise ValidationError(
            "tournament v2 frozen state is not initialized."
        )
    fingerprint = str(state.get("state_fingerprint", ""))
    unsigned = dict(state)
    unsigned.pop("state_fingerprint", None)
    if fingerprint != _stable_hash(unsigned):
        raise ValidationError(
            "tournament v2 frozen-state fingerprint mismatch."
        )
    if (
        state.get("preregistration_fingerprint")
        != CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT
    ):
        raise ValidationError(
            "tournament v2 preregistration fingerprint mismatch."
        )
    frozen_manifest = _read_json_mapping(paths["preregistration"])
    if (
        frozen_manifest
        != build_crypto_tournament_v2_preregistration()
    ):
        raise ValidationError(
            "tournament v2 frozen preregistration drifted."
        )
    expected_hashes = _mapping(state.get("artifact_sha256"))
    for name in (
        "preregistration", "discovery", "embargo", "oos", "ledger"
    ):
        if (
            not paths[name].is_file()
            or _file_sha256(paths[name]) != expected_hashes.get(name)
        ):
            raise ValidationError(
                f"tournament v2 frozen artifact mismatch: {name}."
            )
    discovery = _load_rows(
        paths["discovery"],
        allow_symbol_superset=False,
        allow_imputed=True,
    )
    embargo = _load_rows(
        paths["embargo"],
        allow_symbol_superset=False,
        allow_imputed=False,
    )
    oos = _load_rows(
        paths["oos"],
        allow_symbol_superset=False,
        allow_imputed=False,
    )
    _validate_normalized_grid(
        discovery,
        start=_utc_datetime(DISCOVERY_START, "discovery_start"),
        end_exclusive=_utc_datetime(
            DISCOVERY_END_EXCLUSIVE, "discovery_end"
        ),
    )
    ledger = _read_json_mapping(paths["ledger"])
    if (
        ledger.get("record_type")
        != "crypto_tournament_v2_receipt_ledger"
    ):
        raise ValidationError(
            "tournament v2 receipt ledger is invalid."
        )
    if bool(state.get("terminal_outcome_closed", False)):
        _load_terminal_packet(paths, state)
    return state, discovery, embargo, oos, ledger


def _load_terminal_packet(
    paths: Mapping[str, Path],
    state: Mapping[str, object],
) -> dict[str, object]:
    expected_sha = str(state.get("terminal_packet_sha256", ""))
    if (
        len(expected_sha) != 64
        or not paths["terminal_packet"].is_file()
        or _file_sha256(paths["terminal_packet"]) != expected_sha
    ):
        raise ValidationError(
            "tournament v2 terminal packet hash mismatch."
        )
    packet = _read_json_mapping(paths["terminal_packet"])
    closure = _mapping(packet.get("terminal_closure"))
    if (
        packet.get("record_type")
        != "crypto_tournament_v2_forward_oos_packet"
        or "frozen_state" in packet
        or packet.get("classification")
        != state.get("terminal_classification")
        or packet.get("terminal_evidence_fingerprint")
        != state.get("terminal_evidence_fingerprint")
        or packet.get("preregistration_fingerprint")
        != CRYPTO_TOURNAMENT_V2_PREREGISTRATION_FINGERPRINT
        or closure.get("terminal_outcome_closed") is not True
        or closure.get("terminal_classification")
        != state.get("terminal_classification")
        or closure.get("terminal_closed_at")
        != state.get("terminal_closed_at")
        or closure.get("terminal_scoring_performed")
        != state.get("terminal_scoring_performed")
        or closure.get("terminal_evidence_fingerprint")
        != state.get("terminal_evidence_fingerprint")
    ):
        raise ValidationError(
            "tournament v2 terminal packet identity mismatch."
        )
    return packet

def _updated_state(
    state: Mapping[str, object],
    *,
    paths: Mapping[str, Path],
    as_of: datetime,
    embargo: Sequence[_Bar],
    oos: Sequence[_Bar],
    write_artifacts: bool,
    terminal_scoring_performed: bool | None = None,
    terminal_outcome_closed: bool | None = None,
    terminal_classification: str | None = None,
    terminal_closed_at: str | None = None,
    terminal_packet_sha256: str | None = None,
    terminal_evidence_fingerprint: str | None = None,
) -> dict[str, object]:
    updated = dict(state)
    updated.pop("state_fingerprint", None)
    updated["updated_at"] = as_of.isoformat()
    updated["embargo_raw_rows"] = len(embargo)
    updated["oos_raw_rows"] = len(oos)
    if terminal_outcome_closed is not None:
        updated["terminal_outcome_closed"] = terminal_outcome_closed
    if terminal_classification is not None:
        updated["terminal_classification"] = terminal_classification
    if terminal_closed_at is not None:
        updated["terminal_closed_at"] = terminal_closed_at
    if terminal_packet_sha256 is not None:
        updated["terminal_packet_sha256"] = (
            terminal_packet_sha256
        )
    if terminal_scoring_performed is not None:
        updated[
            "terminal_scoring_performed"
        ] = terminal_scoring_performed
    if terminal_evidence_fingerprint is not None:
        updated[
            "terminal_evidence_fingerprint"
        ] = terminal_evidence_fingerprint
    updated["artifact_sha256"] = _artifact_hashes(
        paths, write_artifacts=write_artifacts
    )
    updated["state_fingerprint"] = _stable_hash(updated)
    return updated


def _artifact_hashes(
    paths: Mapping[str, Path],
    *,
    write_artifacts: bool,
) -> dict[str, str]:
    names = (
        "preregistration", "discovery", "embargo", "oos", "ledger"
    )
    if not write_artifacts:
        return {name: "" for name in names}
    return {name: _file_sha256(paths[name]) for name in names}


def _merge_raw_rows(
    existing: Sequence[_Bar],
    incoming: Sequence[_Bar],
) -> tuple[tuple[_Bar, ...], int, int]:
    merged = {row.key(): row for row in existing}
    added = 0
    duplicate = 0
    for row in incoming:
        current = merged.get(row.key())
        if current is None:
            merged[row.key()] = row
            added += 1
        elif current.canonical() == row.canonical():
            duplicate += 1
        else:
            raise ValidationError(
                "conflicting rewrite of an accrued v2 bar."
            )
    return (
        tuple(sorted(merged.values(), key=_row_sort_key)),
        added,
        duplicate,
    )


def _progress_payload(
    rows: Sequence[_Bar],
    *,
    start: datetime,
    end_exclusive: datetime,
    as_of: datetime,
) -> dict[str, object]:
    by_symbol = _by_symbol(rows)
    timestamp_sets = {
        symbol: {row.timestamp for row in by_symbol[symbol]}
        for symbol in TOURNAMENT_V2_SYMBOLS
    }
    available_end = min(_floor_hour(as_of), end_exclusive)
    available_grid = tuple(
        _hour_grid(start, max(start, available_end))
    )
    complete_grid = tuple(_hour_grid(start, end_exclusive))
    common_frontier = ""
    for timestamp in available_grid:
        if all(
            timestamp in timestamp_sets[symbol]
            for symbol in TOURNAMENT_V2_SYMBOLS
        ):
            common_frontier = timestamp.isoformat()
        else:
            break
    return {
        "start": start.isoformat(),
        "end_exclusive": end_exclusive.isoformat(),
        "expected_rows_per_symbol": len(complete_grid),
        "available_rows_per_symbol_as_of": len(available_grid),
        "observed_rows_per_symbol": {
            symbol: len(by_symbol[symbol])
            for symbol in TOURNAMENT_V2_SYMBOLS
        },
        "common_contiguous_frontier": common_frontier,
        "complete_raw_grid": all(
            timestamp_sets[symbol] == set(complete_grid)
            for symbol in TOURNAMENT_V2_SYMBOLS
        ),
        "candidate_metrics_included": False,
    }


def _next_refresh_payload(
    *,
    embargo: Sequence[_Bar],
    oos: Sequence[_Bar],
    as_of: datetime,
) -> dict[str, object]:
    by_symbol = _by_symbol(tuple(embargo) + tuple(oos))
    timestamp_sets = {
        symbol: {row.timestamp for row in by_symbol[symbol]}
        for symbol in TOURNAMENT_V2_SYMBOLS
    }
    start = _utc_datetime(EMBARGO_START, "embargo_start")
    end_exclusive = _utc_datetime(OOS_END_EXCLUSIVE, "oos_end")
    available_end = min(_floor_hour(as_of), end_exclusive)
    missing = next(
        (
            timestamp
            for timestamp in _hour_grid(start, end_exclusive)
            if any(
                timestamp not in timestamp_sets[symbol]
                for symbol in TOURNAMENT_V2_SYMBOLS
            )
        ),
        None,
    )
    if missing is None:
        return {
            "classification": "accrual_complete",
            "requested_start": "",
            "requested_end": "",
            "as_of": _floor_hour(as_of).isoformat(),
        }
    if missing >= available_end:
        return {
            "classification": "waiting_for_calendar_hour",
            "requested_start": missing.isoformat(),
            "requested_end": "",
            "as_of": _floor_hour(as_of).isoformat(),
        }
    return {
        "classification": (
            "ready_for_explicit_read_only_market_data_fetch"
        ),
        "requested_start": missing.isoformat(),
        "requested_end": (available_end - _ONE_HOUR).isoformat(),
        "as_of": available_end.isoformat(),
        "symbols": list(TOURNAMENT_V2_SYMBOLS),
        "timeframe": "1Hour",
        "no_submit": True,
        "paper_mutation_authorized": False,
    }


def _validate_normalized_grid(
    rows: Sequence[_Bar],
    *,
    start: datetime,
    end_exclusive: datetime,
) -> None:
    expected = tuple(_hour_grid(start, end_exclusive))
    by_symbol = _by_symbol(rows)
    if any(
        tuple(row.timestamp for row in by_symbol[symbol]) != expected
        for symbol in TOURNAMENT_V2_SYMBOLS
    ):
        raise ValidationError(
            "frozen v2 normalized discovery grid drifted."
        )


def _by_symbol(
    rows: Sequence[_Bar],
) -> dict[str, tuple[_Bar, ...]]:
    return {
        symbol: tuple(
            sorted(
                (row for row in rows if row.symbol == symbol),
                key=lambda row: row.timestamp,
            )
        )
        for symbol in TOURNAMENT_V2_SYMBOLS
    }


def _spec_from_candidate(
    candidate: Mapping[str, object],
) -> _EvaluationCandidateSpec:
    parameters = _mapping(
        candidate.get("elapsed_hour_parameters")
    )
    return _EvaluationCandidateSpec(
        strategy_id=str(candidate.get("strategy_id", "")),
        strategy_family=str(
            candidate.get("strategy_family", "")
        ),
        lookback_hours=int(parameters.get("lookback_hours", 0)),
        fast_hours=int(parameters.get("fast_hours", 0)),
        slow_hours=int(parameters.get("slow_hours", 0)),
    )


def _eligible_and_selected(
    ranking: Sequence[Mapping[str, object]],
) -> tuple[
    tuple[Mapping[str, object], ...],
    dict[str, object],
]:
    eligible = tuple(
        item
        for item in ranking
        if item.get("candidate_decision")
        == "eligible_for_no_submit_shadow_evaluation"
    )
    selected = (
        _selected_payload(eligible[0]) if eligible else {}
    )
    return eligible, selected


def _selected_payload(
    candidate: Mapping[str, object],
) -> dict[str, object]:
    return {
        "candidate_id": candidate.get("candidate_id", ""),
        "candidate_fingerprint": candidate.get(
            "candidate_fingerprint", ""
        ),
        "candidate_decision": candidate.get(
            "candidate_decision", ""
        ),
        "selection_scope": (
            "eligible_for_no_submit_shadow_evaluation"
        ),
        "paper_or_broker_eligible": False,
    }


def _state_summary(
    state: Mapping[str, object],
) -> dict[str, object]:
    return {
        "schema_version": state.get("schema_version", ""),
        "state_fingerprint": state.get("state_fingerprint", ""),
        "preregistration_fingerprint": state.get(
            "preregistration_fingerprint", ""
        ),
        "initialized_at": state.get("initialized_at", ""),
        "updated_at": state.get("updated_at", ""),
        "discovery_normalized_rows": state.get(
            "discovery_normalized_rows", 0
        ),
        "discovery_imputed_rows": state.get(
            "discovery_imputed_rows", 0
        ),
        "embargo_raw_rows": state.get("embargo_raw_rows", 0),
        "oos_raw_rows": state.get("oos_raw_rows", 0),
        "terminal_outcome_closed": state.get(
            "terminal_outcome_closed", False
        ),
        "terminal_classification": state.get(
            "terminal_classification", ""
        ),
        "terminal_closed_at": state.get("terminal_closed_at", ""),
        "terminal_packet_sha256": state.get("terminal_packet_sha256", ""),
        "terminal_scoring_performed": state.get(
            "terminal_scoring_performed", False
        ),
        "terminal_evidence_fingerprint": state.get(
            "terminal_evidence_fingerprint", ""
        ),
    }

def render_crypto_tournament_v2_forward_oos_markdown(
    packet: Mapping[str, object],
) -> str:
    """Render a compact no-submit operating packet."""

    selected = _mapping(packet.get("selected_candidate"))
    next_refresh = _mapping(packet.get("next_refresh"))
    embargo = _mapping(packet.get("embargo_progress"))
    oos = _mapping(packet.get("oos_progress"))
    return "\n".join(
        (
            "# Crypto Tournament V2 Forward-OOS",
            "",
            f"- Classification: {packet.get('classification', '')}",
            f"- Phase: {packet.get('phase', '')}",
            (
                "- Preregistration fingerprint: "
                f"{packet.get('preregistration_fingerprint', '')}"
            ),
            (
                "- Embargo rows per symbol: "
                f"{_compact_mapping(_mapping(embargo.get('observed_rows_per_symbol')))}"
            ),
            (
                "- OOS rows per symbol: "
                f"{_compact_mapping(_mapping(oos.get('observed_rows_per_symbol')))}"
            ),
            (
                "- Terminal scoring performed: "
                f"{_bool_text(packet.get('terminal_scoring_performed'))}"
            ),
            (
                "- Selected candidate: "
                f"{selected.get('candidate_id', '')}"
            ),
            (
                "- Next refresh: "
                f"{next_refresh.get('classification', '')}"
            ),
            (
                "- Next start/end: "
                f"{next_refresh.get('requested_start', '')} / "
                f"{next_refresh.get('requested_end', '')}"
            ),
            (
                "- Network / market-data fetch this operation: "
                f"{_bool_text(packet.get('network_access_attempted'))} / "
                f"{_bool_text(packet.get('market_data_fetch_occurred'))}"
            ),
            (
                "- Broker read/mutation, submit, cancel, replace, close, "
                "liquidation, and live authorization: false"
            ),
            "- Paper eligibility: not_eligible",
            "- Profit claim: none",
            "",
            (
                "Interim packets intentionally contain no candidate metrics. "
                "A terminal pass permits only a separate no-submit shadow "
                "evaluation."
            ),
            "",
        )
    )


def _state_paths(root: Path) -> dict[str, Path]:
    return {
        "preregistration": root / "frozen_preregistration.json",
        "discovery": root / "frozen_discovery_history.csv",
        "embargo": root / "embargo_history.csv",
        "oos": root / "accrued_oos_history.csv",
        "ledger": root / "receipt_ledger.json",
        "state": root / "frozen_state.json",
        "terminal_packet": root / "terminal_packet.json",
        "packet_json": root / "operating_packet.json",
        "packet_markdown": root / "operating_packet.md",
    }


def _write_packet(
    paths: Mapping[str, Path],
    packet: Mapping[str, object],
) -> None:
    _write_json_atomic(paths["packet_json"], packet)
    _write_text_atomic(
        paths["packet_markdown"],
        render_crypto_tournament_v2_forward_oos_markdown(packet),
    )


def _write_rows_atomic(
    path: Path,
    rows: Sequence[_Bar],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "timestamp",
                "symbol",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "imputed",
            ),
            lineterminator="\n",
        )
        writer.writeheader()
        for row in sorted(rows, key=_row_sort_key):
            writer.writerow(
                {
                    **row.canonical(),
                    "imputed": _bool_text(row.imputed),
                }
            )
    temporary.replace(path)


def _write_json_atomic(
    path: Path,
    payload: Mapping[str, object],
) -> None:
    _write_text_atomic(
        path,
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        text, encoding="utf-8", newline="\n"
    )
    temporary.replace(path)


def _read_json_mapping(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(
            f"invalid JSON artifact: {path}."
        ) from exc
    if not isinstance(value, Mapping):
        raise ValidationError(
            f"JSON artifact must be an object: {path}."
        )
    return dict(value)


def _hour_grid(
    start: datetime,
    end_exclusive: datetime,
) -> Sequence[datetime]:
    count = int((end_exclusive - start) / _ONE_HOUR)
    if (
        count < 0
        or start + (count * _ONE_HOUR) != end_exclusive
    ):
        raise ValidationError(
            "v2 window must be a positive hourly grid."
        )
    return tuple(
        start + (index * _ONE_HOUR) for index in range(count)
    )


def _maximum_consecutive_gap(
    expected: Sequence[datetime],
    missing: set[datetime],
) -> int:
    longest = 0
    current = 0
    for timestamp in expected:
        if timestamp in missing:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _utc_datetime(
    value: object,
    field_name: str,
) -> datetime:
    if isinstance(value, datetime):
        result = value
    else:
        text = str(value).strip()
        if not text:
            raise ValidationError(f"{field_name} is required.")
        try:
            result = datetime.fromisoformat(
                text.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise ValidationError(
                f"{field_name} must be ISO-8601."
            ) from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValidationError(
            f"{field_name} must be timezone-aware."
        )
    return result.astimezone(UTC)


def _floor_hour(value: datetime) -> datetime:
    return value.astimezone(UTC).replace(
        minute=0, second=0, microsecond=0
    )


def _decimal(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValidationError("invalid v2 decimal value.") from exc
    if not result.is_finite():
        raise ValidationError(
            "v2 decimal value must be finite."
        )
    return result


def _positive_decimal(
    value: object,
    field_name: str,
) -> Decimal:
    result = _decimal(value)
    if result <= _ZERO:
        raise ValidationError(f"{field_name} must be positive.")
    return result


def _non_negative_decimal(
    value: object,
    field_name: str,
) -> Decimal:
    result = _decimal(value)
    if result < _ZERO:
        raise ValidationError(
            f"{field_name} must be non-negative."
        )
    return result


def _decimal_text(value: Decimal) -> str:
    if value == _ZERO:
        return "0"
    return (
        format(value.quantize(_DECIMAL_QUANTUM), "f")
        .rstrip("0")
        .rstrip(".")
    )


def _bool_field(value: object) -> bool:
    if value in (True, "true", "True", "1", 1):
        return True
    if value in (False, "false", "False", "0", 0, "", None):
        return False
    raise ValidationError("invalid imputed boolean value.")


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _required_text(
    value: object,
    field_name: str,
) -> str:
    text = str(value).strip()
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _mapping_sequence(
    value: object,
) -> tuple[Mapping[str, object], ...]:
    if (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
    ):
        return tuple(
            item for item in value if isinstance(item, Mapping)
        )
    return ()


def _string_sequence(value: object) -> tuple[str, ...]:
    if (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
    ):
        return tuple(str(item) for item in value)
    return ()


def _row_sort_key(row: _Bar) -> tuple[int, datetime]:
    return (
        TOURNAMENT_V2_SYMBOLS.index(row.symbol),
        row.timestamp,
    )


def _rows_hash(rows: Sequence[_Bar]) -> str:
    return _stable_hash(
        [
            row.canonical()
            for row in sorted(rows, key=_row_sort_key)
        ]
    )


def _stable_hash(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024), b""
        ):
            digest.update(chunk)
    return digest.hexdigest()


def _compact_mapping(value: Mapping[str, object]) -> str:
    return ",".join(
        f"{key}={item}" for key, item in sorted(value.items())
    )
