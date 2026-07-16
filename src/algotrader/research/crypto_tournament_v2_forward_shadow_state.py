"""Immutable selected-winner forward-shadow accrual and terminal evidence.

The state machine consumes only a validated V5.24 activation and guarded local
OHLCV receipts.  It freezes 169 selected-symbol causal context bars, accrues a
separate unscored activation-warmup interval when terminal closure is delayed,
then evaluates exactly 168 future one-hour shadow bars.  It has no execution,
network, credential, broker, account, order, paper-mutation, or live-capital
dependency.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
from typing import BinaryIO, Iterator

from algotrader.errors import ValidationError
from algotrader.research.crypto_preregistered_tournament import (
    BASE_FEE_BPS,
    BASE_SLIPPAGE_BPS,
    STRESS_FEE_BPS,
    STRESS_SLIPPAGE_BPS,
)
from algotrader.research.crypto_preregistered_tournament_v2 import (
    MAXIMUM_CONSECUTIVE_MISSING_HOURS,
    MINIMUM_POSITIVE_RAW_VOLUME_FRACTION,
    MINIMUM_RAW_HOURLY_COVERAGE,
    OOS_END_EXCLUSIVE,
)
from algotrader.research.crypto_tournament_v2_forward_oos import (
    _Bar,
    _asset_returns,
    _decimal_text,
    _file_sha256,
    _load_rows,
    _read_json_mapping,
    _rows_hash,
    _simulate_window,
    _spec_from_candidate,
    _targets_with_imputation_hold,
    _window_metrics,
    _write_json_atomic,
    _write_rows_atomic,
    _write_text_atomic,
    export_crypto_tournament_v2_selected_shadow_context,
)
from algotrader.research.crypto_tournament_v2_forward_shadow import (
    CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT,
    CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PREREGISTRATION_FINGERPRINT,
    FORWARD_SHADOW_CHECKPOINT_HOURS,
    FORWARD_SHADOW_HOURLY_BARS,
    build_crypto_tournament_v2_forward_shadow_preregistration,
    run_crypto_tournament_v2_forward_shadow_readiness,
    validate_crypto_tournament_v2_forward_shadow_activation,
)


CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_STATE_SCHEMA_VERSION = (
    "v5_25_crypto_tournament_v2_forward_shadow_state_v1"
)
CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PACKET_SCHEMA_VERSION = (
    "v5_25_crypto_tournament_v2_forward_shadow_packet_v1"
)
CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_TERMINAL_EVIDENCE_SCHEMA_VERSION = (
    "v5_26_crypto_tournament_v2_forward_shadow_terminal_evidence_v1"
)
CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_CONTEXT_ROWS = 169

_EXPECTED_RECEIPT_SCHEMA = "v5_22_crypto_history_refresh_adapter_receipt_v2"
_EXPECTED_SOURCE = "alpaca_market_data_crypto_bars_v1beta3"
_EXPECTED_BASIS = "alpaca_crypto_bars_v1beta3_ohlcv"
_FALSE_RECEIPT_FIELDS = (
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
    "live_endpoint_indicator",
    "live_endpoint_touched",
    "credential_values_exposed",
)
_ARTIFACT_NAMES = (
    "preregistration",
    "activation",
    "source_terminal_packet",
    "context",
    "activation_warmup",
    "shadow_raw",
    "shadow_normalized",
    "ledger",
    "decision_log",
    "checkpoint_ledger",
)
_MUTABLE_ARTIFACT_NAMES = (
    "activation_warmup",
    "shadow_raw",
    "shadow_normalized",
    "ledger",
    "decision_log",
    "checkpoint_ledger",
)
_TRANSACTION_ENTRY_NAMES = (*_MUTABLE_ARTIFACT_NAMES, "terminal_packet", "state")
_ONE_HOUR = timedelta(hours=1)
_ZERO = Decimal("0")
_ONE = Decimal("1")

__all__ = [
    "CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_CONTEXT_ROWS",
    "CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PACKET_SCHEMA_VERSION",
    "CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_STATE_SCHEMA_VERSION",
    "CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_TERMINAL_EVIDENCE_SCHEMA_VERSION",
    "export_crypto_tournament_v2_forward_shadow_terminal_evidence",
    "initialize_crypto_tournament_v2_forward_shadow_state",
    "render_crypto_tournament_v2_forward_shadow_state_markdown",
    "run_crypto_tournament_v2_forward_shadow_state",
]


def initialize_crypto_tournament_v2_forward_shadow_state(
    *,
    tournament_root: Path | str,
    output_root: Path | str = (
        CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT
    ),
    as_of: datetime | str,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Initialize under one process-exclusive state-generation lock."""

    if not write_artifacts:
        raise ValidationError(
            "forward-shadow initialization must persist its frozen state."
        )
    root = _local_path(output_root, "output_root")
    with _exclusive_state_lock(root):
        paths = _state_paths(root)
        _recover_pending_transaction(paths)
        return _initialize_crypto_tournament_v2_forward_shadow_state_locked(
            tournament_root=tournament_root,
            output_root=root,
            as_of=as_of,
            write_artifacts=write_artifacts,
        )


def _initialize_crypto_tournament_v2_forward_shadow_state_locked(
    *,
    tournament_root: Path | str,
    output_root: Path | str = (
        CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT
    ),
    as_of: datetime | str,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Initialize only from one sealed, validated V5.24 winner activation."""

    root = _local_path(output_root, "output_root")
    paths = _state_paths(root)
    evaluated_at = _utc_datetime(as_of, "as_of")
    if paths["state"].is_file():
        return _run_crypto_tournament_v2_forward_shadow_state_locked(
            output_root=root,
            as_of=evaluated_at,
            write_artifacts=write_artifacts,
        )

    activation = run_crypto_tournament_v2_forward_shadow_readiness(
        tournament_root=tournament_root,
        output_root=root,
        as_of=evaluated_at,
        write_artifacts=False,
    )
    if activation.get("classification") != (
        "ready_to_activate_no_submit_forward_shadow"
    ):
        return _dormant_packet(activation, evaluated_at)
    validated_activation = (
        validate_crypto_tournament_v2_forward_shadow_activation(activation)
    )
    context_packet = export_crypto_tournament_v2_selected_shadow_context(
        output_root=tournament_root,
        as_of=evaluated_at,
    )
    candidate = dict(
        _mapping(
            validated_activation.get("selected_candidate"),
            "validated_activation.selected_candidate",
        )
    )
    source_binding = dict(
        _mapping(
            validated_activation.get("source_binding"),
            "validated_activation.source_binding",
        )
    )
    _validate_context_binding(
        context_packet,
        candidate=candidate,
        activation_source=source_binding,
    )
    context_rows = tuple(
        _bar_from_canonical(item, expected_symbol=str(candidate["symbol"]))
        for item in _mapping_sequence(
            context_packet.get("context_rows"),
            "context_packet.context_rows",
        )
    )
    if len(context_rows) != CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_CONTEXT_ROWS:
        raise ValidationError("forward-shadow context must contain 169 bars.")
    _validate_context_rows(
        context_rows,
        symbol=str(candidate["symbol"]),
    )
    if (
        context_packet.get("context_row_count")
        != CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_CONTEXT_ROWS
        or context_packet.get("context_sha256") != _rows_hash(context_rows)
    ):
        raise ValidationError("forward-shadow context identity mismatch.")

    window = _mapping(
        validated_activation.get("shadow_window"),
        "validated_activation.shadow_window",
    )
    shadow_start = _utc_datetime(window.get("start"), "shadow_window.start")
    shadow_end = _utc_datetime(
        window.get("end_exclusive"),
        "shadow_window.end_exclusive",
    )
    warmup_start = _utc_datetime(OOS_END_EXCLUSIVE, "oos_end_exclusive")
    if shadow_start < warmup_start:
        raise ValidationError("forward-shadow starts before tournament OOS end.")
    empty_rows: tuple[_Bar, ...] = ()
    ledger: dict[str, object] = {
        "schema_version": CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_STATE_SCHEMA_VERSION,
        "record_type": "crypto_tournament_v2_forward_shadow_receipt_ledger",
        "receipts": [],
    }
    checkpoint_ledger = _checkpoint_ledger(())
    preregistration = (
        build_crypto_tournament_v2_forward_shadow_preregistration()
    )
    terminal_source = _local_path(
        Path(
        _required_text(
            _mapping(context_packet.get("source_binding"), "source_binding").get(
                "terminal_packet_path"
            ),
            "terminal_packet_path",
        )
        ),
        "terminal_packet_path",
    )
    if (
        not terminal_source.is_file()
        or _file_sha256(terminal_source)
        != source_binding["terminal_packet_sha256"]
    ):
        raise ValidationError("forward-shadow source terminal packet mismatch.")

    if write_artifacts:
        root.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(paths["preregistration"], preregistration)
        _write_json_atomic(paths["activation"], activation)
        _write_bytes_atomic(
            paths["source_terminal_packet"],
            terminal_source.read_bytes(),
        )
        _write_rows_atomic(paths["context"], context_rows)
        _write_rows_atomic(paths["activation_warmup"], empty_rows)
        _write_rows_atomic(paths["shadow_raw"], empty_rows)
        _write_rows_atomic(paths["shadow_normalized"], empty_rows)
        _write_json_atomic(paths["ledger"], ledger)
        _write_json_lines_atomic(paths["decision_log"], ())
        _write_json_atomic(paths["checkpoint_ledger"], checkpoint_ledger)

    state: dict[str, object] = {
        "schema_version": CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_STATE_SCHEMA_VERSION,
        "record_type": "crypto_tournament_v2_forward_shadow_frozen_state",
        "preregistration_fingerprint": (
            CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PREREGISTRATION_FINGERPRINT
        ),
        "activation_fingerprint": validated_activation[
            "activation_fingerprint"
        ],
        "source_terminal_packet_sha256": source_binding[
            "terminal_packet_sha256"
        ],
        "source_terminal_evidence_fingerprint": source_binding[
            "terminal_evidence_fingerprint"
        ],
        "source_state_fingerprint": source_binding["state_fingerprint"],
        "source_terminal_closed_at": source_binding["terminal_closed_at"],
        "candidate": candidate,
        "selected_symbol": candidate["symbol"],
        "initialized_at": evaluated_at.isoformat(),
        "updated_at": evaluated_at.isoformat(),
        "activation_warmup_start": warmup_start.isoformat(),
        "shadow_start": shadow_start.isoformat(),
        "shadow_end_exclusive": shadow_end.isoformat(),
        "expected_shadow_hourly_bars": FORWARD_SHADOW_HOURLY_BARS,
        "context_row_count": len(context_rows),
        "context_sha256": _rows_hash(context_rows),
        "activation_warmup_raw_rows": 0,
        "shadow_raw_rows": 0,
        "shadow_normalized_rows": 0,
        "decision_log_rows": 0,
        "completed_checkpoint_hours": [],
        "terminal_outcome_closed": False,
        "terminal_classification": "",
        "terminal_closed_at": "",
        "terminal_packet_sha256": "",
        "terminal_evidence_fingerprint": "",
        "terminal_scoring_performed": False,
        "artifact_sha256": _artifact_hashes(
            paths, write_artifacts=write_artifacts
        ),
    }
    state["state_fingerprint"] = _stable_hash(state)
    if write_artifacts:
        _write_json_atomic(paths["state"], state)

    packet = _build_operating_packet(
        root=root,
        state=state,
        activation_warmup=empty_rows,
        shadow_raw=empty_rows,
        shadow_normalized=empty_rows,
        ledger=ledger,
        decision_log=(),
        checkpoint_ledger=checkpoint_ledger,
        warmup_quality=_empty_quality(
            "activation_warmup",
            warmup_start,
            shadow_start,
        ),
        shadow_quality=_empty_quality(
            "shadow",
            shadow_start,
            shadow_start,
        ),
        as_of=evaluated_at,
        operation_network_access=False,
        operation_market_data_fetch=False,
    )
    if write_artifacts:
        _write_operating_packet(paths, packet)
    return packet


def run_crypto_tournament_v2_forward_shadow_state(
    *,
    output_root: Path | str = (
        CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT
    ),
    as_of: datetime | str,
    delta_history_path: Path | str | None = None,
    delta_receipt_path: Path | str | None = None,
    operation_network_access: bool = False,
    operation_market_data_fetch: bool = False,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Accrue or inspect under one recoverable generation lock."""

    root = _local_path(output_root, "output_root")
    with _exclusive_state_lock(root):
        paths = _state_paths(root)
        _recover_pending_transaction(paths)
        return _run_crypto_tournament_v2_forward_shadow_state_locked(
            output_root=root,
            as_of=as_of,
            delta_history_path=delta_history_path,
            delta_receipt_path=delta_receipt_path,
            operation_network_access=operation_network_access,
            operation_market_data_fetch=operation_market_data_fetch,
            write_artifacts=write_artifacts,
        )


def _run_crypto_tournament_v2_forward_shadow_state_locked(
    *,
    output_root: Path | str = (
        CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT
    ),
    as_of: datetime | str,
    delta_history_path: Path | str | None = None,
    delta_receipt_path: Path | str | None = None,
    operation_network_access: bool = False,
    operation_market_data_fetch: bool = False,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Accrue one guarded selected-symbol delta or inspect frozen state."""

    if (delta_history_path is None) != (delta_receipt_path is None):
        raise ValidationError(
            "shadow delta history and receipt paths must be supplied together."
        )
    if operation_market_data_fetch and not operation_network_access:
        raise ValidationError(
            "shadow market-data fetch cannot occur without network access."
        )
    if delta_history_path is not None and not write_artifacts:
        raise ValidationError(
            "forward-shadow delta previews cannot claim a frozen state."
        )
    root = _local_path(output_root, "output_root")
    paths = _state_paths(root)
    if not paths["state"].is_file():
        raise ValidationError("forward-shadow state is not initialized.")
    evaluated_at = _utc_datetime(as_of, "as_of")
    (
        state,
        context,
        activation_warmup,
        shadow_raw,
        shadow_normalized,
        ledger,
        decision_log,
        checkpoint_ledger,
    ) = _load_and_validate_state(paths)
    updated_at = _utc_datetime(state.get("updated_at"), "state.updated_at")
    if evaluated_at < updated_at:
        raise ValidationError("forward-shadow as_of cannot regress state time.")
    if bool(state.get("terminal_outcome_closed", False)):
        if delta_history_path is not None:
            raise ValidationError(
                "forward-shadow terminal outcome rejects later deltas."
            )
        if operation_network_access or operation_market_data_fetch:
            raise ValidationError(
                "closed forward shadow cannot report a new fetch."
            )
        packet = _load_terminal_packet(paths, state)
        packet["status_checked_at"] = evaluated_at.isoformat()
        packet["frozen_state"] = _state_summary(state)
        packet["next_refresh"] = {
            "classification": "terminal_window_closed",
            "requested_start": "",
            "requested_end": "",
            "as_of": _floor_hour(evaluated_at).isoformat(),
        }
        if write_artifacts:
            _write_operating_packet(paths, packet)
        return packet

    candidate = _mapping(state.get("candidate"), "state.candidate")
    symbol = _required_text(state.get("selected_symbol"), "selected_symbol")
    warmup_start = _utc_datetime(
        state.get("activation_warmup_start"),
        "activation_warmup_start",
    )
    shadow_start = _utc_datetime(state.get("shadow_start"), "shadow_start")
    shadow_end = _utc_datetime(
        state.get("shadow_end_exclusive"),
        "shadow_end_exclusive",
    )
    next_ledger = dict(ledger)
    next_warmup = activation_warmup
    next_shadow_raw = shadow_raw

    if delta_history_path is not None and delta_receipt_path is not None:
        history_path = _local_path(delta_history_path, "delta_history_path")
        receipt_path = _local_path(delta_receipt_path, "delta_receipt_path")
        provenance = _validate_selected_receipt(
            history_path=history_path,
            receipt_path=receipt_path,
            selected_symbol=symbol,
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
        if receipt_start < warmup_start or receipt_end >= shadow_end:
            raise ValidationError(
                "shadow delta receipt falls outside activation/winner window."
            )
        if receipt_as_of > _floor_hour(evaluated_at):
            raise ValidationError("shadow receipt is later than evaluation as-of.")
        delta = _load_rows(
            history_path,
            allow_symbol_superset=False,
            allow_imputed=False,
            latest_allowed_timestamp=receipt_end,
        )
        if not delta or any(row.symbol != symbol for row in delta):
            raise ValidationError(
                "shadow delta must contain exactly the selected symbol."
            )
        if any(
            row.timestamp < receipt_start or row.timestamp > receipt_end
            for row in delta
        ):
            raise ValidationError(
                "shadow delta contains rows outside its guarded receipt."
            )
        if any(row.timestamp >= _floor_hour(evaluated_at) for row in delta):
            raise ValidationError("shadow delta contains an incomplete hour.")
        prior_imputed = {
            _utc_datetime(item.get("timestamp"), "decision.timestamp")
            for item in decision_log
            if item.get("imputed") is True
        }
        existing_raw_timestamps = {
            row.timestamp for row in tuple(next_warmup) + tuple(next_shadow_raw)
        }
        if any(
            row.timestamp in prior_imputed
            and row.timestamp not in existing_raw_timestamps
            for row in delta
        ):
            raise ValidationError(
                "shadow delta cannot retroactively replace an imputed decision."
            )
        warmup_delta = tuple(
            row for row in delta if warmup_start <= row.timestamp < shadow_start
        )
        shadow_delta = tuple(
            row for row in delta if shadow_start <= row.timestamp < shadow_end
        )
        next_warmup, warmup_new, warmup_duplicates = _merge_selected_rows(
            next_warmup, warmup_delta
        )
        next_shadow_raw, shadow_new, shadow_duplicates = _merge_selected_rows(
            next_shadow_raw, shadow_delta
        )
        receipt_entry = {
            "receipt_sha256": provenance["receipt_sha256"],
            "output_sha256": provenance["output_sha256"],
            "requested_start": provenance["requested_start"],
            "requested_end": provenance["requested_end"],
            "receipt_as_of": provenance["receipt_as_of"],
            "selected_symbol": symbol,
            "accepted_row_count": len(delta),
            "new_row_count": warmup_new + shadow_new,
            "exact_duplicate_row_count": (
                warmup_duplicates + shadow_duplicates
            ),
            "data_intake_only": True,
            "strategy_evidence_evaluation_performed": False,
        }
        receipts = list(
            _mapping_sequence(next_ledger.get("receipts"), "ledger.receipts")
        )
        receipt_key = (
            receipt_entry["receipt_sha256"],
            receipt_entry["output_sha256"],
        )
        if not any(
            (item.get("receipt_sha256"), item.get("output_sha256"))
            == receipt_key
            for item in receipts
        ):
            receipts.append(receipt_entry)
        next_ledger = {**next_ledger, "receipts": receipts}

    available_shadow_end = max(
        shadow_start,
        min(_floor_hour(evaluated_at), shadow_end),
    )
    warmup_normalized, warmup_quality, warmup_errors = (
        _normalize_selected_window(
            next_warmup,
            symbol=symbol,
            start=warmup_start,
            end_exclusive=shadow_start,
            phase="activation_warmup",
            strict_complete=True,
        )
    )
    available_shadow_rows = tuple(
        row for row in next_shadow_raw if row.timestamp < available_shadow_end
    )
    _, shadow_quality, shadow_errors = (
        _normalize_selected_window(
            available_shadow_rows,
            symbol=symbol,
            start=shadow_start,
            end_exclusive=available_shadow_end,
            phase="shadow",
            strict_complete=False,
        )
    )
    expected_available = _hour_count(shadow_start, available_shadow_end)
    admitted_shadow_end = _admissible_shadow_end(
        next_shadow_raw,
        start=shadow_start,
        available_end_exclusive=available_shadow_end,
    )
    admitted_shadow_rows = tuple(
        row for row in next_shadow_raw if row.timestamp < admitted_shadow_end
    )
    candidate_shadow_normalized, _, admission_errors = (
        _normalize_selected_window(
            admitted_shadow_rows,
            symbol=symbol,
            start=shadow_start,
            end_exclusive=admitted_shadow_end,
            phase="shadow",
            strict_complete=False,
        )
    )
    blocking_admission_errors = tuple(
        error
        for error in admission_errors
        if error
        not in {
            "shadow_raw_coverage_below_threshold",
            "shadow_positive_volume_below_threshold",
        }
    )
    if (
        not warmup_errors
        and not blocking_admission_errors
        and len(warmup_normalized)
        == _hour_count(warmup_start, shadow_start)
    ):
        candidate_decision_log, evidence = _build_decision_evidence(
            context=context,
            activation_warmup=warmup_normalized,
            shadow_rows=candidate_shadow_normalized,
            candidate=candidate,
        )
        _validate_append_only_evidence(
            persisted_normalized=shadow_normalized,
            persisted_decisions=decision_log,
            candidate_normalized=candidate_shadow_normalized,
            candidate_decisions=candidate_decision_log,
        )
        next_shadow_normalized = candidate_shadow_normalized
        next_decision_log = candidate_decision_log
    else:
        if shadow_normalized or decision_log:
            raise ValidationError(
                "forward-shadow evidence cannot destructively regress."
            )
        next_shadow_normalized = ()
        next_decision_log = ()
        evidence = _empty_evidence(0)
    next_checkpoint_ledger = _checkpoint_ledger(next_decision_log)

    if delta_history_path is not None:
        staged = _stage_mutable_generation(
            paths,
            base_state=state,
            as_of=evaluated_at,
            activation_warmup=next_warmup,
            shadow_raw=next_shadow_raw,
            shadow_normalized=next_shadow_normalized,
            ledger=next_ledger,
            decision_log=next_decision_log,
            checkpoint_ledger=next_checkpoint_ledger,
        )
        artifact_sha256 = dict(
            _mapping(state.get("artifact_sha256"), "artifact_sha256")
        )
        artifact_sha256.update(
            {name: _file_sha256(path) for name, path in staged.items()}
        )
        next_state = _updated_state(
            state,
            paths=paths,
            as_of=evaluated_at,
            activation_warmup=next_warmup,
            shadow_raw=next_shadow_raw,
            shadow_normalized=next_shadow_normalized,
            decision_log=next_decision_log,
            checkpoint_ledger=next_checkpoint_ledger,
            write_artifacts=True,
            artifact_sha256=artifact_sha256,
        )
        _commit_state_transaction(
            paths,
            base_state=state,
            target_state=next_state,
            staged=staged,
        )
        state = next_state

    packet = _build_operating_packet(
        root=root,
        state=state,
        activation_warmup=next_warmup,
        shadow_raw=next_shadow_raw,
        shadow_normalized=next_shadow_normalized,
        ledger=next_ledger,
        decision_log=next_decision_log,
        checkpoint_ledger=next_checkpoint_ledger,
        warmup_quality=warmup_quality,
        shadow_quality=shadow_quality,
        as_of=evaluated_at,
        operation_network_access=operation_network_access,
        operation_market_data_fetch=operation_market_data_fetch,
    )

    terminal_receipt_bound = any(
        item.get("requested_end") == (shadow_end - _ONE_HOUR).isoformat()
        for item in _mapping_sequence(next_ledger.get("receipts"), "ledger.receipts")
    )
    terminal_ready = evaluated_at >= shadow_end and terminal_receipt_bound
    if terminal_ready and not write_artifacts:
        packet.update(
            {
                "classification": "terminal_shadow_finalize_required",
                "phase": "terminal_evaluation_ready_for_locked_commit",
                "terminal_scoring_performed": False,
                "terminal_metrics": {},
                "terminal_evidence_fingerprint": "",
                "next_refresh": {
                    "classification": "terminal_finalize_required",
                    "requested_start": "",
                    "requested_end": "",
                    "as_of": _floor_hour(evaluated_at).isoformat(),
                },
            }
        )
        return packet
    if terminal_ready:
        terminal_errors = list(warmup_errors + shadow_errors)
        if len(next_shadow_normalized) != FORWARD_SHADOW_HOURLY_BARS:
            terminal_errors.append("shadow_normalized_grid_incomplete")
        if len(next_decision_log) != FORWARD_SHADOW_HOURLY_BARS:
            terminal_errors.append("shadow_decision_log_incomplete")
        terminal_errors = list(dict.fromkeys(terminal_errors))
        if terminal_errors:
            packet.update(
                {
                    "classification": "terminal_shadow_input_quality_gate",
                    "phase": "terminal_closed_without_valid_shadow_metrics",
                    "terminal_scoring_performed": False,
                    "terminal_metrics": {},
                    "terminal_input_quality": {
                        "activation_warmup": warmup_quality,
                        "shadow": shadow_quality,
                        "errors": terminal_errors,
                    },
                }
            )
        else:
            packet.update(
                {
                    "classification": (
                        "evidence_complete_for_bounded_paper_probe_review"
                    ),
                    "phase": "terminal_shadow_evidence_sealed",
                    "terminal_scoring_performed": True,
                    "terminal_metrics": evidence,
                    "terminal_input_quality": {
                        "activation_warmup": warmup_quality,
                        "shadow": shadow_quality,
                        "errors": [],
                    },
                }
            )
        packet["terminal_evidence_fingerprint"] = (
            _compute_terminal_evidence_fingerprint(
                state=state,
                activation_warmup=warmup_normalized,
                shadow_normalized=next_shadow_normalized,
                decision_log=next_decision_log,
                classification=str(packet["classification"]),
                terminal_input_quality=_mapping(
                    packet["terminal_input_quality"],
                    "terminal_input_quality",
                ),
                terminal_metrics=_mapping(
                    packet["terminal_metrics"],
                    "terminal_metrics",
                ),
            )
        )
        packet["next_refresh"] = {
            "classification": "terminal_window_closed",
            "requested_start": "",
            "requested_end": "",
            "as_of": _floor_hour(evaluated_at).isoformat(),
        }
        packet["terminal_closure"] = {
            "terminal_outcome_closed": True,
            "terminal_classification": packet["classification"],
            "terminal_closed_at": evaluated_at.isoformat(),
            "terminal_scoring_performed": packet[
                "terminal_scoring_performed"
            ],
            "terminal_evidence_fingerprint": packet[
                "terminal_evidence_fingerprint"
            ],
        }
        packet.pop("frozen_state", None)
        staged_terminal = {
            "terminal_packet": _stage_json_payload(
                paths,
                name="terminal_packet",
                payload=packet,
                transaction_id=_transaction_id(
                    state,
                    evaluated_at,
                    suffix="terminal",
                ),
            )
        }
        terminal_packet_sha = _file_sha256(
            staged_terminal["terminal_packet"]
        )
        terminal_state = _updated_state(
            state,
            paths=paths,
            as_of=evaluated_at,
            activation_warmup=next_warmup,
            shadow_raw=next_shadow_raw,
            shadow_normalized=next_shadow_normalized,
            decision_log=next_decision_log,
            checkpoint_ledger=next_checkpoint_ledger,
            write_artifacts=True,
            artifact_sha256=_mapping(
                state.get("artifact_sha256"), "artifact_sha256"
            ),
            terminal_outcome_closed=True,
            terminal_classification=str(packet["classification"]),
            terminal_closed_at=evaluated_at.isoformat(),
            terminal_packet_sha256=terminal_packet_sha,
            terminal_evidence_fingerprint=str(
                packet["terminal_evidence_fingerprint"]
            ),
            terminal_scoring_performed=bool(
                packet["terminal_scoring_performed"]
            ),
        )
        _commit_state_transaction(
            paths,
            base_state=state,
            target_state=terminal_state,
            staged=staged_terminal,
        )
        state = terminal_state
        packet["frozen_state"] = _state_summary(state)
    elif evaluated_at >= shadow_end:
        packet["classification"] = "awaiting_terminal_shadow_market_data"
        packet["phase"] = "awaiting_terminal_refresh"

    if write_artifacts:
        _write_operating_packet(paths, packet)
    return packet


def export_crypto_tournament_v2_forward_shadow_terminal_evidence(
    *,
    output_root: Path | str = (
        CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_DEFAULT_OUTPUT_ROOT
    ),
    as_of: datetime | str,
) -> dict[str, object]:
    """Export one independently validated, path-free terminal evidence packet."""

    root = _local_path(output_root, "output_root")
    evaluated_at = _utc_datetime(as_of, "as_of")
    with _exclusive_state_lock(root):
        paths = _state_paths(root)
        _recover_pending_transaction(paths)
        if not paths["state"].is_file():
            raise ValidationError("forward-shadow state is not initialized.")
        (
            state,
            context,
            activation_warmup,
            shadow_raw,
            shadow_normalized,
            _ledger,
            decision_log,
            checkpoint_ledger,
        ) = _load_and_validate_state(paths)
        updated_at = _utc_datetime(state.get("updated_at"), "state.updated_at")
        if evaluated_at < updated_at:
            raise ValidationError(
                "forward-shadow terminal export as_of cannot regress state time."
            )
        if state.get("terminal_outcome_closed") is not True:
            raise ValidationError("forward-shadow terminal evidence is not sealed.")
        terminal_packet = _load_terminal_packet(paths, state)
        return _build_terminal_evidence_export(
            state=state,
            context=context,
            activation_warmup=activation_warmup,
            shadow_raw=shadow_raw,
            shadow_normalized=shadow_normalized,
            decision_log=decision_log,
            checkpoint_ledger=checkpoint_ledger,
            terminal_packet=terminal_packet,
            as_of=evaluated_at,
        )


def render_crypto_tournament_v2_forward_shadow_state_markdown(
    packet: Mapping[str, object],
) -> str:
    """Render one compact no-submit state packet."""

    progress = _mapping(packet.get("progress"), "progress")
    candidate = _mapping(packet.get("selected_candidate"), "selected_candidate")
    next_refresh = _mapping(packet.get("next_refresh"), "next_refresh")
    return "\n".join(
        (
            "# Crypto Tournament V2 Forward Shadow",
            "",
            f"- Classification: {packet.get('classification', '')}",
            f"- Phase: {packet.get('phase', '')}",
            f"- Candidate: {candidate.get('candidate_id', '')}",
            f"- Symbol: {candidate.get('symbol', '')}",
            (
                "- Raw/normalized/decision rows: "
                f"{progress.get('shadow_raw_rows', 0)} / "
                f"{progress.get('shadow_normalized_rows', 0)} / "
                f"{progress.get('decision_log_rows', 0)}"
            ),
            (
                "- Next refresh: "
                f"{next_refresh.get('classification', '')} "
                f"{next_refresh.get('requested_start', '')} / "
                f"{next_refresh.get('requested_end', '')}"
            ),
            (
                "- Network / market-data fetch this operation: "
                f"{_bool_text(packet.get('network_access_attempted'))} / "
                f"{_bool_text(packet.get('market_data_fetch_occurred'))}"
            ),
            "- Broker, paper mutation, capital, and live authority: false",
            "- Profit claim: none",
            "",
        )
    )


def _build_decision_evidence(
    *,
    context: Sequence[_Bar],
    activation_warmup: Sequence[_Bar],
    shadow_rows: Sequence[_Bar],
    candidate: Mapping[str, object],
) -> tuple[tuple[dict[str, object], ...], dict[str, object]]:
    if not shadow_rows:
        return (), _empty_evidence(0)
    combined = tuple(context) + tuple(activation_warmup) + tuple(shadow_rows)
    spec = _spec_from_candidate(candidate)
    targets = _targets_with_imputation_hold(combined, spec, timeframe_hours=1)
    start_index = len(context) + len(activation_warmup)
    initial_exposure = targets[start_index - 1]
    shadow_targets = targets[start_index:]
    returns = _asset_returns(
        (combined[start_index - 1].close,)
        + tuple(row.close for row in shadow_rows)
    )[1:]
    timestamps = tuple(row.timestamp for row in shadow_rows)
    base_points = _simulate_window(
        initial_exposure=initial_exposure,
        timestamps=timestamps,
        asset_returns=returns,
        targets=shadow_targets,
        fee_bps=BASE_FEE_BPS,
        slippage_bps=BASE_SLIPPAGE_BPS,
    )
    stress_points = _simulate_window(
        initial_exposure=initial_exposure,
        timestamps=timestamps,
        asset_returns=returns,
        targets=shadow_targets,
        fee_bps=STRESS_FEE_BPS,
        slippage_bps=STRESS_SLIPPAGE_BPS,
    )
    buy_hold_targets = tuple(_ONE for _ in shadow_rows)
    buy_hold_base_points = _simulate_window(
        initial_exposure=_ONE,
        timestamps=timestamps,
        asset_returns=returns,
        targets=buy_hold_targets,
        fee_bps=BASE_FEE_BPS,
        slippage_bps=BASE_SLIPPAGE_BPS,
    )
    buy_hold_stress_points = _simulate_window(
        initial_exposure=_ONE,
        timestamps=timestamps,
        asset_returns=returns,
        targets=buy_hold_targets,
        fee_bps=STRESS_FEE_BPS,
        slippage_bps=STRESS_SLIPPAGE_BPS,
    )
    rows: list[dict[str, object]] = []
    for bar, base, stress in zip(shadow_rows, base_points, stress_points):
        rows.append(
            {
                "schema_version": (
                    CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PACKET_SCHEMA_VERSION
                ),
                "record_type": "crypto_tournament_v2_shadow_hourly_decision",
                "timestamp": bar.timestamp.isoformat(),
                "symbol": bar.symbol,
                "candidate_id": candidate.get("candidate_id", ""),
                "candidate_fingerprint": candidate.get(
                    "candidate_fingerprint", ""
                ),
                "close": _decimal_text(bar.close),
                "volume": _decimal_text(bar.volume),
                "imputed": bar.imputed,
                "target_exposure": _decimal_text(base.target_exposure),
                "applied_exposure": _decimal_text(base.applied_exposure),
                "asset_return": _decimal_text(base.asset_return),
                "boundary_transition_delta": _decimal_text(
                    base.boundary_transition_delta
                ),
                "signal_transition_delta": _decimal_text(
                    base.signal_transition_delta
                ),
                "transition_delta": _decimal_text(base.transition_delta),
                "completed_round_trip": base.completed_round_trip,
                "base_transaction_cost": _decimal_text(
                    base.transaction_cost
                ),
                "base_net_return": _decimal_text(base.net_return),
                "stress_transaction_cost": _decimal_text(
                    stress.transaction_cost
                ),
                "stress_net_return": _decimal_text(stress.net_return),
                "hypothetical_only": True,
                "paper_or_broker_eligible": False,
            }
        )
    base_metrics = _window_metrics(base_points)
    stress_metrics = _window_metrics(stress_points)
    buy_hold_base = _window_metrics(buy_hold_base_points)
    buy_hold_stress = _window_metrics(buy_hold_stress_points)
    gross_buy_hold = _compound_returns(returns)
    evidence = {
        "initial_exposure": _decimal_text(initial_exposure),
        "base_metrics": base_metrics,
        "stress_metrics": stress_metrics,
        "cash_total_return": "0",
        "same_symbol_buy_hold": {
            "gross_total_return": _decimal_text(gross_buy_hold),
            "base_metrics": buy_hold_base,
            "stress_metrics": buy_hold_stress,
        },
        "base_excess_vs_buy_hold": _decimal_text(
            _decimal(base_metrics["total_return"])
            - _decimal(buy_hold_base["total_return"])
        ),
        "stress_excess_vs_buy_hold": _decimal_text(
            _decimal(stress_metrics["total_return"])
            - _decimal(buy_hold_stress["total_return"])
        ),
        "decision_log_expected_rows": FORWARD_SHADOW_HOURLY_BARS,
        "decision_log_observed_rows": len(rows),
        "decision_log_missing_rows": max(
            0, FORWARD_SHADOW_HOURLY_BARS - len(rows)
        ),
        "decision_log_duplicate_rows": 0,
        "decision_log_complete": len(rows) == FORWARD_SHADOW_HOURLY_BARS,
        "no_forced_terminal_liquidation": True,
        "paper_probe_authorized": False,
        "live_probe_authorized": False,
    }
    return tuple(rows), evidence


def _build_operating_packet(
    *,
    root: Path,
    state: Mapping[str, object],
    activation_warmup: Sequence[_Bar],
    shadow_raw: Sequence[_Bar],
    shadow_normalized: Sequence[_Bar],
    ledger: Mapping[str, object],
    decision_log: Sequence[Mapping[str, object]],
    checkpoint_ledger: Mapping[str, object],
    warmup_quality: Mapping[str, object],
    shadow_quality: Mapping[str, object],
    as_of: datetime,
    operation_network_access: bool,
    operation_market_data_fetch: bool,
) -> dict[str, object]:
    start = _utc_datetime(state.get("shadow_start"), "shadow_start")
    end = _utc_datetime(
        state.get("shadow_end_exclusive"), "shadow_end_exclusive"
    )
    warmup_start = _utc_datetime(
        state.get("activation_warmup_start"), "activation_warmup_start"
    )
    candidate = dict(_mapping(state.get("candidate"), "state.candidate"))
    next_refresh = _next_refresh_payload(
        activation_warmup=activation_warmup,
        shadow_raw=shadow_raw,
        selected_symbol=str(state.get("selected_symbol", "")),
        warmup_start=warmup_start,
        shadow_start=start,
        shadow_end=end,
        as_of=as_of,
    )
    if next_refresh["classification"] == "waiting_for_calendar_hour":
        classification = "collecting_no_submit_forward_shadow"
        phase = "waiting_for_next_completed_hour"
    elif next_refresh["classification"] == (
        "ready_for_explicit_read_only_market_data_fetch"
    ):
        classification = "collecting_no_submit_forward_shadow"
        phase = "selected_symbol_data_accrual"
    else:
        classification = "shadow_window_data_complete"
        phase = "awaiting_terminal_evaluation"
    if as_of < start:
        classification = "shadow_initialized_waiting_for_start"
        phase = "activation_signal_warmup"
    latest = dict(decision_log[-1]) if decision_log else {}
    return {
        "schema_version": (
            CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PACKET_SCHEMA_VERSION
        ),
        "record_type": "crypto_tournament_v2_forward_shadow_packet",
        "as_of": as_of.isoformat(),
        "output_root": str(root),
        "classification": classification,
        "phase": phase,
        "preregistration_fingerprint": state[
            "preregistration_fingerprint"
        ],
        "activation_fingerprint": state["activation_fingerprint"],
        "selected_candidate": candidate,
        "shadow_window": {
            "start": start.isoformat(),
            "end_exclusive": end.isoformat(),
            "hourly_bars": FORWARD_SHADOW_HOURLY_BARS,
            "checkpoint_hours": list(FORWARD_SHADOW_CHECKPOINT_HOURS),
        },
        "progress": {
            "activation_warmup_expected_rows": _hour_count(
                warmup_start, start
            ),
            "activation_warmup_raw_rows": len(activation_warmup),
            "shadow_expected_rows": FORWARD_SHADOW_HOURLY_BARS,
            "shadow_raw_rows": len(shadow_raw),
            "shadow_normalized_rows": len(shadow_normalized),
            "decision_log_rows": len(decision_log),
            "completed_checkpoint_hours": list(
                checkpoint_ledger.get("completed_checkpoint_hours", [])
            ),
        },
        "activation_warmup_quality": dict(warmup_quality),
        "shadow_quality": dict(shadow_quality),
        "receipt_count": len(
            _mapping_sequence(ledger.get("receipts"), "ledger.receipts")
        ),
        "latest_decision": latest,
        "next_refresh": next_refresh,
        "terminal_scoring_performed": False,
        "terminal_metrics": {},
        "terminal_evidence_fingerprint": "",
        "frozen_state": _state_summary(state),
        "strategy_evidence_evaluation_performed": bool(decision_log),
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
        "paper_or_broker_eligible": False,
        "paper_planning_eligibility": "not_eligible",
        "bounded_paper_probe_review_permitted": False,
        "paper_or_live_execution_authorized": False,
        "capital_allocation_authorized": False,
        "live_authorized": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "profit_claim": "none",
    }


def _validate_selected_receipt(
    *,
    history_path: Path,
    receipt_path: Path,
    selected_symbol: str,
) -> dict[str, str]:
    packet = _read_json_mapping(receipt_path)
    required = {
        "schema_version": _EXPECTED_RECEIPT_SCHEMA,
        "record_type": "crypto_history_refresh_adapter_packet",
        "classification": "market_data_refresh_ready",
        "coverage_gate_classification": "not_evaluated_data_intake_only",
        "mode": "market_data_fetch",
        "authorization_status": "authorized",
        "endpoint_safety_status": "passed_non_live_endpoint_check",
        "data_source": _EXPECTED_SOURCE,
        "timeframe": "1Hour",
        "loc": "us",
        "schema_validation_status": "passed",
        "duplicate_timestamp_status": "passed",
        "duplicate_timestamp_status_after_normalization": "passed",
        "profit_claim": "none",
    }
    for field_name, expected in required.items():
        if packet.get(field_name) != expected:
            raise ValidationError(
                f"guarded shadow receipt field mismatch: {field_name}."
            )
    if (
        packet.get("market_data_fetch_occurred") is not True
        or packet.get("network_access_attempted") is not True
        or packet.get("data_intake_only") is not True
        or packet.get("strategy_evidence_evaluation_performed") is not False
        or packet.get("paper_planning_promotion_allowed") is not False
    ):
        raise ValidationError(
            "guarded shadow receipt lacks exact data-only fetch proof."
        )
    for field_name in _FALSE_RECEIPT_FIELDS:
        if field_name not in packet or packet.get(field_name) is not False:
            raise ValidationError(
                f"guarded shadow receipt safety field mismatch: {field_name}."
            )
    requested = _string_sequence(packet.get("requested_symbols"))
    fetched = _string_sequence(packet.get("fetched_symbols"))
    if requested != (selected_symbol,) or fetched != (selected_symbol,):
        raise ValidationError(
            "guarded shadow receipt does not bind the selected symbol."
        )
    if _string_sequence(packet.get("missing_symbols")):
        raise ValidationError("guarded shadow receipt reports a missing symbol.")
    if Path(str(packet.get("output_path", ""))).resolve() != history_path.resolve():
        raise ValidationError("guarded shadow receipt output path mismatch.")
    if Path(str(packet.get("packet_path", ""))).resolve() != receipt_path.resolve():
        raise ValidationError("guarded shadow receipt packet path mismatch.")
    output_sha = _file_sha256(history_path)
    if str(packet.get("output_sha256", "")).lower() != output_sha:
        raise ValidationError("guarded shadow receipt output SHA-256 mismatch.")
    start = _utc_datetime(packet.get("requested_start"), "requested_start")
    end = _utc_datetime(packet.get("requested_end"), "requested_end")
    receipt_as_of = _utc_datetime(packet.get("as_of"), "receipt_as_of")
    if end < start or end + _ONE_HOUR != receipt_as_of:
        raise ValidationError(
            "guarded shadow receipt must end at its last completed hour."
        )
    if any(
        value.minute or value.second or value.microsecond
        for value in (start, end, receipt_as_of)
    ):
        raise ValidationError("guarded shadow receipt must align to UTC hours.")
    rows_per_symbol = _mapping(
        packet.get("rows_per_symbol_after_normalization"),
        "rows_per_symbol_after_normalization",
    )
    if set(rows_per_symbol) != {selected_symbol}:
        raise ValidationError("guarded shadow receipt row-count symbols mismatch.")
    return {
        "receipt_sha256": _file_sha256(receipt_path),
        "output_sha256": output_sha,
        "requested_start": start.isoformat(),
        "requested_end": end.isoformat(),
        "receipt_as_of": receipt_as_of.isoformat(),
    }


def _normalize_selected_window(
    rows: Sequence[_Bar],
    *,
    symbol: str,
    start: datetime,
    end_exclusive: datetime,
    phase: str,
    strict_complete: bool,
) -> tuple[tuple[_Bar, ...], dict[str, object], tuple[str, ...]]:
    expected = tuple(_hour_grid(start, end_exclusive))
    if not expected:
        return (), _empty_quality(phase, start, end_exclusive), ()
    observed = {row.timestamp: row for row in rows if row.symbol == symbol}
    errors: list[str] = []
    if len(observed) != len(rows):
        errors.append(f"{phase}_unexpected_symbol")
    expected_set = set(expected)
    if set(observed) - expected_set:
        errors.append(f"{phase}_outside_window")
    missing = [item for item in expected if item not in observed]
    raw_count = len(expected) - len(missing)
    coverage = Decimal(raw_count) / Decimal(len(expected))
    raw_rows = tuple(observed[item] for item in expected if item in observed)
    positive_fraction = (
        Decimal(sum(row.volume > _ZERO for row in raw_rows)) / Decimal(raw_count)
        if raw_count
        else _ZERO
    )
    maximum_gap = _maximum_consecutive_gap(expected, set(missing))
    minimum_coverage = _ONE if strict_complete else _decimal(
        MINIMUM_RAW_HOURLY_COVERAGE
    )
    allowed_gap = 0 if strict_complete else MAXIMUM_CONSECUTIVE_MISSING_HOURS
    if coverage < minimum_coverage:
        errors.append(f"{phase}_raw_coverage_below_threshold")
    if positive_fraction < _decimal(MINIMUM_POSITIVE_RAW_VOLUME_FRACTION):
        errors.append(f"{phase}_positive_volume_below_threshold")
    if maximum_gap > allowed_gap:
        errors.append(f"{phase}_consecutive_gap_exceeded")
    if expected[0] in missing or expected[-1] in missing:
        errors.append(f"{phase}_boundary_bar_missing")
    normalized: list[_Bar] = []
    for timestamp in expected:
        row = observed.get(timestamp)
        if row is not None:
            normalized.append(row)
            continue
        if not normalized:
            continue
        prior = normalized[-1]
        normalized.append(
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
    quality = {
        "phase": phase,
        "status": "passed" if not errors else "failed",
        "symbol": symbol,
        "start": start.isoformat(),
        "end_exclusive": end_exclusive.isoformat(),
        "expected_raw_rows": len(expected),
        "observed_raw_rows": raw_count,
        "raw_coverage": _decimal_text(coverage),
        "positive_raw_volume_fraction": _decimal_text(positive_fraction),
        "missing_timestamps": [item.isoformat() for item in missing],
        "maximum_consecutive_missing_hours": maximum_gap,
        "imputed_rows": sum(row.imputed for row in normalized),
        "isolated_gap_fill": "prior_close_ohlc_zero_volume",
    }
    return tuple(normalized), quality, tuple(dict.fromkeys(errors))


def _admissible_shadow_end(
    rows: Sequence[_Bar],
    *,
    start: datetime,
    available_end_exclusive: datetime,
) -> datetime:
    """Return the longest causal prefix ending on a raw boundary bar."""

    observed = {
        row.timestamp
        for row in rows
        if start <= row.timestamp < available_end_exclusive
    }
    expected = _hour_grid(start, available_end_exclusive)
    if not expected or expected[0] not in observed:
        return start
    admitted_end = start
    missing_run_start: datetime | None = None
    missing_run = 0
    for timestamp in expected:
        if timestamp in observed:
            missing_run = 0
            missing_run_start = None
            admitted_end = timestamp + _ONE_HOUR
            continue
        if missing_run == 0:
            missing_run_start = timestamp
        missing_run += 1
        if missing_run > MAXIMUM_CONSECUTIVE_MISSING_HOURS:
            if missing_run_start is None:  # pragma: no cover - defensive
                raise ValidationError("shadow gap boundary is unavailable.")
            return missing_run_start
    return admitted_end


def _validate_append_only_evidence(
    *,
    persisted_normalized: Sequence[_Bar],
    persisted_decisions: Sequence[Mapping[str, object]],
    candidate_normalized: Sequence[_Bar],
    candidate_decisions: Sequence[Mapping[str, object]],
) -> None:
    if len(persisted_normalized) != len(persisted_decisions):
        raise ValidationError(
            "forward-shadow persisted evidence artifacts are misaligned."
        )
    if (
        len(candidate_normalized) < len(persisted_normalized)
        or len(candidate_decisions) < len(persisted_decisions)
    ):
        raise ValidationError(
            "forward-shadow evidence cannot destructively regress."
        )
    for persisted, candidate in zip(
        persisted_normalized,
        candidate_normalized,
    ):
        if persisted.canonical() != candidate.canonical():
            raise ValidationError(
                "forward-shadow normalized evidence prefix drifted."
            )
    if tuple(persisted_decisions) != tuple(
        candidate_decisions[: len(persisted_decisions)]
    ):
        raise ValidationError(
            "forward-shadow decision evidence prefix drifted."
        )


@contextmanager
def _exclusive_state_lock(root: Path) -> Iterator[None]:
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".forward_shadow_state.lock"
    stream = lock_path.open("a+b")
    try:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        _lock_stream(stream)
    except OSError as exc:
        stream.close()
        raise ValidationError(
            "another forward-shadow state cycle holds the exclusive lock."
        ) from exc
    try:
        yield
    finally:
        try:
            stream.seek(0)
            _unlock_stream(stream)
        finally:
            stream.close()


def _lock_stream(stream: BinaryIO) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        return
    import fcntl  # pragma: no cover - exercised on non-Windows hosts

    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_stream(stream: BinaryIO) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl  # pragma: no cover - exercised on non-Windows hosts

    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _transaction_id(
    state: Mapping[str, object],
    as_of: datetime,
    *,
    suffix: str,
) -> str:
    return _stable_hash(
        {
            "base_state_fingerprint": state.get("state_fingerprint", ""),
            "as_of": as_of.isoformat(),
            "suffix": suffix,
        }
    )[:24]


def _pending_artifact_path(
    paths: Mapping[str, Path],
    *,
    name: str,
    transaction_id: str,
) -> Path:
    if name not in _TRANSACTION_ENTRY_NAMES:
        raise ValidationError("unsupported forward-shadow transaction artifact.")
    root = paths["state"].parent
    return root / f".{transaction_id}.{paths[name].name}.pending"


def _stage_mutable_generation(
    paths: Mapping[str, Path],
    *,
    base_state: Mapping[str, object],
    as_of: datetime,
    activation_warmup: Sequence[_Bar],
    shadow_raw: Sequence[_Bar],
    shadow_normalized: Sequence[_Bar],
    ledger: Mapping[str, object],
    decision_log: Sequence[Mapping[str, object]],
    checkpoint_ledger: Mapping[str, object],
) -> dict[str, Path]:
    transaction_id = _transaction_id(
        base_state,
        as_of,
        suffix="evidence",
    )
    staged = {
        name: _pending_artifact_path(
            paths,
            name=name,
            transaction_id=transaction_id,
        )
        for name in _MUTABLE_ARTIFACT_NAMES
    }
    _write_rows_atomic(staged["activation_warmup"], activation_warmup)
    _write_rows_atomic(staged["shadow_raw"], shadow_raw)
    _write_rows_atomic(staged["shadow_normalized"], shadow_normalized)
    _write_json_atomic(staged["ledger"], ledger)
    _write_json_lines_atomic(staged["decision_log"], decision_log)
    _write_json_atomic(staged["checkpoint_ledger"], checkpoint_ledger)
    return staged


def _stage_json_payload(
    paths: Mapping[str, Path],
    *,
    name: str,
    payload: Mapping[str, object],
    transaction_id: str,
) -> Path:
    staged = _pending_artifact_path(
        paths,
        name=name,
        transaction_id=transaction_id,
    )
    _write_json_atomic(staged, payload)
    return staged


def _commit_state_transaction(
    paths: Mapping[str, Path],
    *,
    base_state: Mapping[str, object],
    target_state: Mapping[str, object],
    staged: Mapping[str, Path],
) -> None:
    current_state = _read_json_mapping(paths["state"])
    if current_state.get("state_fingerprint") != base_state.get(
        "state_fingerprint"
    ):
        raise ValidationError(
            "forward-shadow state changed before generation commit."
        )
    transaction_id = str(target_state.get("state_fingerprint", ""))[:24]
    staged_state = _stage_json_payload(
        paths,
        name="state",
        payload=target_state,
        transaction_id=transaction_id,
    )
    all_staged = {**dict(staged), "state": staged_state}
    ordered_names = [
        name for name in _TRANSACTION_ENTRY_NAMES if name in all_staged
    ]
    entries: list[dict[str, object]] = []
    for name in ordered_names:
        canonical = paths[name]
        pending = all_staged[name]
        if pending.parent.resolve() != canonical.parent.resolve():
            raise ValidationError(
                "forward-shadow pending artifact left the state root."
            )
        entries.append(
            {
                "name": name,
                "canonical_file": canonical.name,
                "pending_file": pending.name,
                "old_sha256": (
                    _file_sha256(canonical) if canonical.is_file() else ""
                ),
                "new_sha256": _file_sha256(pending),
            }
        )
    manifest: dict[str, object] = {
        "schema_version": (
            CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_STATE_SCHEMA_VERSION
        ),
        "record_type": "crypto_tournament_v2_forward_shadow_pending_transaction",
        "base_state_fingerprint": base_state.get("state_fingerprint", ""),
        "target_state_fingerprint": target_state.get("state_fingerprint", ""),
        "entries": entries,
    }
    manifest["transaction_fingerprint"] = _stable_hash(manifest)
    _write_json_atomic(paths["transaction"], manifest)
    try:
        _publish_pending_transaction(paths, manifest)
    except Exception:
        _recover_pending_transaction(paths)


def _recover_pending_transaction(paths: Mapping[str, Path]) -> None:
    transaction_path = paths["transaction"]
    if not transaction_path.is_file():
        return
    manifest = _read_json_mapping(transaction_path)
    fingerprint = str(manifest.get("transaction_fingerprint", ""))
    unsigned = dict(manifest)
    unsigned.pop("transaction_fingerprint", None)
    if (
        manifest.get("schema_version")
        != CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_STATE_SCHEMA_VERSION
        or manifest.get("record_type")
        != "crypto_tournament_v2_forward_shadow_pending_transaction"
        or fingerprint != _stable_hash(unsigned)
    ):
        raise ValidationError("forward-shadow transaction manifest is invalid.")
    current_state = _read_json_mapping(paths["state"])
    current_fingerprint = current_state.get("state_fingerprint", "")
    if current_fingerprint not in {
        manifest.get("base_state_fingerprint", ""),
        manifest.get("target_state_fingerprint", ""),
    }:
        raise ValidationError(
            "forward-shadow transaction base state no longer matches."
        )
    _publish_pending_transaction(paths, manifest)


def _publish_pending_transaction(
    paths: Mapping[str, Path],
    manifest: Mapping[str, object],
) -> None:
    root = paths["state"].parent.resolve()
    entries = _mapping_sequence(manifest.get("entries"), "transaction.entries")
    names = tuple(str(entry.get("name", "")) for entry in entries)
    if (
        not entries
        or names[-1] != "state"
        or len(names) != len(set(names))
        or any(name not in _TRANSACTION_ENTRY_NAMES for name in names)
    ):
        raise ValidationError("forward-shadow transaction entries are invalid.")
    pending_paths: dict[str, Path] = {}
    for entry in entries:
        name = str(entry["name"])
        canonical = paths[name]
        if entry.get("canonical_file") != canonical.name:
            raise ValidationError(
                "forward-shadow transaction canonical path drifted."
            )
        pending = root / _required_text(
            entry.get("pending_file"), "transaction.pending_file"
        )
        if pending.parent.resolve() != root:
            raise ValidationError(
                "forward-shadow transaction pending path escaped state root."
            )
        pending_paths[name] = pending
        old_sha = str(entry.get("old_sha256", ""))
        new_sha = str(entry.get("new_sha256", ""))
        current_sha = _file_sha256(canonical) if canonical.is_file() else ""
        if current_sha == new_sha:
            if pending.is_file() and _file_sha256(pending) == new_sha:
                try:
                    pending.unlink()
                except OSError:
                    # Publication is already complete for this entry.  Retry
                    # verified cleanup after the whole generation is checked.
                    pass
            continue
        if current_sha != old_sha:
            raise ValidationError(
                f"forward-shadow transaction conflict: {name}."
            )
        if not pending.is_file() or _file_sha256(pending) != new_sha:
            raise ValidationError(
                f"forward-shadow transaction pending artifact mismatch: {name}."
            )
        _replace_staged_file(pending, canonical)
    for entry in entries:
        name = str(entry["name"])
        if _file_sha256(paths[name]) != entry.get("new_sha256"):
            raise ValidationError(
                f"forward-shadow transaction publish mismatch: {name}."
            )
    target_state = _read_json_mapping(paths["state"])
    if target_state.get("state_fingerprint") != manifest.get(
        "target_state_fingerprint"
    ):
        raise ValidationError("forward-shadow transaction state did not publish.")
    for entry in entries:
        name = str(entry["name"])
        pending = pending_paths[name]
        if (
            pending.is_file()
            and _file_sha256(pending) == entry.get("new_sha256")
        ):
            try:
                pending.unlink()
            except OSError as exc:
                raise ValidationError(
                    "forward-shadow transaction could not clear a verified "
                    f"staged artifact: {name}."
                ) from exc
    try:
        paths["transaction"].unlink()
    except OSError as exc:
        raise ValidationError(
            "forward-shadow transaction could not clear its journal."
        ) from exc


def _replace_staged_file(source: Path, target: Path) -> None:
    source.replace(target)


def _load_and_validate_state(
    paths: Mapping[str, Path],
) -> tuple[
    dict[str, object],
    tuple[_Bar, ...],
    tuple[_Bar, ...],
    tuple[_Bar, ...],
    tuple[_Bar, ...],
    dict[str, object],
    tuple[dict[str, object], ...],
    dict[str, object],
]:
    state = _read_json_mapping(paths["state"])
    if not state:
        raise ValidationError("forward-shadow frozen state is missing.")
    fingerprint = str(state.get("state_fingerprint", ""))
    unsigned = dict(state)
    unsigned.pop("state_fingerprint", None)
    if fingerprint != _stable_hash(unsigned):
        raise ValidationError("forward-shadow state fingerprint mismatch.")
    if state.get("preregistration_fingerprint") != (
        CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PREREGISTRATION_FINGERPRINT
    ):
        raise ValidationError("forward-shadow preregistration mismatch.")
    if (
        state.get("schema_version")
        != CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_STATE_SCHEMA_VERSION
        or state.get("record_type")
        != "crypto_tournament_v2_forward_shadow_frozen_state"
    ):
        raise ValidationError("forward-shadow state schema mismatch.")
    if _read_json_mapping(paths["preregistration"]) != (
        build_crypto_tournament_v2_forward_shadow_preregistration()
    ):
        raise ValidationError("forward-shadow frozen preregistration drifted.")
    activation = _read_json_mapping(paths["activation"])
    validated = validate_crypto_tournament_v2_forward_shadow_activation(activation)
    if validated["activation_fingerprint"] != state.get("activation_fingerprint"):
        raise ValidationError("forward-shadow activation binding mismatch.")
    activation_candidate = dict(
        _mapping(validated.get("selected_candidate"), "selected_candidate")
    )
    activation_source = _mapping(
        validated.get("source_binding"), "source_binding"
    )
    activation_window = _mapping(
        validated.get("shadow_window"), "shadow_window"
    )
    state_bindings = {
        "candidate": activation_candidate,
        "selected_symbol": activation_candidate.get("symbol"),
        "source_terminal_packet_sha256": activation_source.get(
            "terminal_packet_sha256"
        ),
        "source_terminal_evidence_fingerprint": activation_source.get(
            "terminal_evidence_fingerprint"
        ),
        "source_state_fingerprint": activation_source.get(
            "state_fingerprint"
        ),
        "source_terminal_closed_at": activation_source.get(
            "terminal_closed_at"
        ),
        "activation_warmup_start": _utc_datetime(
            OOS_END_EXCLUSIVE, "oos_end_exclusive"
        ).isoformat(),
        "shadow_start": activation_window.get("start"),
        "shadow_end_exclusive": activation_window.get("end_exclusive"),
        "expected_shadow_hourly_bars": FORWARD_SHADOW_HOURLY_BARS,
        "context_row_count": (
            CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_CONTEXT_ROWS
        ),
    }
    for field_name, expected in state_bindings.items():
        if state.get(field_name) != expected:
            raise ValidationError(
                f"forward-shadow state binding mismatch: {field_name}."
            )
    expected_hashes = _mapping(state.get("artifact_sha256"), "artifact_sha256")
    if set(expected_hashes) != set(_ARTIFACT_NAMES):
        raise ValidationError("forward-shadow artifact manifest mismatch.")
    for name in _ARTIFACT_NAMES:
        if (
            not paths[name].is_file()
            or _file_sha256(paths[name]) != expected_hashes.get(name)
        ):
            raise ValidationError(
                f"forward-shadow frozen artifact mismatch: {name}."
            )
    if _file_sha256(paths["source_terminal_packet"]) != activation_source.get(
        "terminal_packet_sha256"
    ):
        raise ValidationError("forward-shadow terminal source binding mismatch.")
    symbol = _required_text(state.get("selected_symbol"), "selected_symbol")
    context = _load_rows(
        paths["context"],
        allow_symbol_superset=False,
        allow_imputed=True,
    )
    activation_warmup = _load_rows(
        paths["activation_warmup"],
        allow_symbol_superset=False,
        allow_imputed=False,
    )
    shadow_raw = _load_rows(
        paths["shadow_raw"],
        allow_symbol_superset=False,
        allow_imputed=False,
    )
    shadow_normalized = _load_rows(
        paths["shadow_normalized"],
        allow_symbol_superset=False,
        allow_imputed=True,
    )
    if any(
        row.symbol != symbol
        for row in context + activation_warmup + shadow_raw + shadow_normalized
    ):
        raise ValidationError("forward-shadow artifact symbol drifted.")
    if (
        len(context) != CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_CONTEXT_ROWS
        or _rows_hash(context) != state.get("context_sha256")
    ):
        raise ValidationError("forward-shadow causal context drifted.")
    _validate_context_rows(context, symbol=symbol)
    ledger = _read_json_mapping(paths["ledger"])
    decision_log = _read_json_lines(paths["decision_log"])
    checkpoint_ledger = _read_json_mapping(paths["checkpoint_ledger"])
    if len(activation_warmup) != state.get("activation_warmup_raw_rows"):
        raise ValidationError("forward-shadow warmup row count drifted.")
    if len(shadow_raw) != state.get("shadow_raw_rows"):
        raise ValidationError("forward-shadow raw row count drifted.")
    if len(shadow_normalized) != state.get("shadow_normalized_rows"):
        raise ValidationError("forward-shadow normalized row count drifted.")
    if len(decision_log) != state.get("decision_log_rows"):
        raise ValidationError("forward-shadow decision row count drifted.")
    if bool(state.get("terminal_outcome_closed", False)):
        _load_terminal_packet(paths, state)
    return (
        state,
        context,
        activation_warmup,
        shadow_raw,
        shadow_normalized,
        ledger,
        decision_log,
        checkpoint_ledger,
    )


def _updated_state(
    state: Mapping[str, object],
    *,
    paths: Mapping[str, Path],
    as_of: datetime,
    activation_warmup: Sequence[_Bar],
    shadow_raw: Sequence[_Bar],
    shadow_normalized: Sequence[_Bar],
    decision_log: Sequence[Mapping[str, object]],
    checkpoint_ledger: Mapping[str, object],
    write_artifacts: bool,
    artifact_sha256: Mapping[str, object] | None = None,
    terminal_outcome_closed: bool | None = None,
    terminal_classification: str | None = None,
    terminal_closed_at: str | None = None,
    terminal_packet_sha256: str | None = None,
    terminal_evidence_fingerprint: str | None = None,
    terminal_scoring_performed: bool | None = None,
) -> dict[str, object]:
    updated = dict(state)
    updated.pop("state_fingerprint", None)
    updated["updated_at"] = as_of.isoformat()
    updated["activation_warmup_raw_rows"] = len(activation_warmup)
    updated["shadow_raw_rows"] = len(shadow_raw)
    updated["shadow_normalized_rows"] = len(shadow_normalized)
    updated["decision_log_rows"] = len(decision_log)
    updated["completed_checkpoint_hours"] = list(
        checkpoint_ledger.get("completed_checkpoint_hours", [])
    )
    if terminal_outcome_closed is not None:
        updated["terminal_outcome_closed"] = terminal_outcome_closed
    if terminal_classification is not None:
        updated["terminal_classification"] = terminal_classification
    if terminal_closed_at is not None:
        updated["terminal_closed_at"] = terminal_closed_at
    if terminal_packet_sha256 is not None:
        updated["terminal_packet_sha256"] = terminal_packet_sha256
    if terminal_evidence_fingerprint is not None:
        updated["terminal_evidence_fingerprint"] = terminal_evidence_fingerprint
    if terminal_scoring_performed is not None:
        updated["terminal_scoring_performed"] = terminal_scoring_performed
    updated["artifact_sha256"] = (
        {str(key): str(value) for key, value in artifact_sha256.items()}
        if artifact_sha256 is not None
        else _artifact_hashes(paths, write_artifacts=write_artifacts)
    )
    updated["state_fingerprint"] = _stable_hash(updated)
    return updated


def _next_refresh_payload(
    *,
    activation_warmup: Sequence[_Bar],
    shadow_raw: Sequence[_Bar],
    selected_symbol: str,
    warmup_start: datetime,
    shadow_start: datetime,
    shadow_end: datetime,
    as_of: datetime,
) -> dict[str, object]:
    observed = {
        row.timestamp for row in tuple(activation_warmup) + tuple(shadow_raw)
    }
    available_end = min(_floor_hour(as_of), shadow_end)
    missing = next(
        (
            timestamp
            for timestamp in _hour_grid(warmup_start, shadow_end)
            if timestamp not in observed
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
            "phase": (
                "activation_warmup_only" if missing < shadow_start else "shadow"
            ),
        }
    return {
        "classification": "ready_for_explicit_read_only_market_data_fetch",
        "requested_start": missing.isoformat(),
        "requested_end": (available_end - _ONE_HOUR).isoformat(),
        "as_of": available_end.isoformat(),
        "symbols": [selected_symbol],
        "timeframe": "1Hour",
        "phase": (
            "activation_warmup_only" if missing < shadow_start else "shadow"
        ),
        "no_submit": True,
        "paper_mutation_authorized": False,
    }


def _validate_context_binding(
    context_packet: Mapping[str, object],
    *,
    candidate: Mapping[str, object],
    activation_source: Mapping[str, object],
) -> None:
    if context_packet.get("candidate") != candidate:
        raise ValidationError("forward-shadow context candidate mismatch.")
    source = _mapping(context_packet.get("source_binding"), "source_binding")
    for field_name in (
        "terminal_packet_sha256",
        "terminal_evidence_fingerprint",
        "state_fingerprint",
        "terminal_closed_at",
    ):
        if source.get(field_name) != activation_source.get(field_name):
            raise ValidationError(
                f"forward-shadow context source mismatch: {field_name}."
            )
    for field_name in (
        "network_access_attempted",
        "broker_read_occurred",
        "broker_mutation_occurred",
        "paper_or_live_execution_authorized",
        "live_authorized",
    ):
        if context_packet.get(field_name) is not False:
            raise ValidationError(
                f"forward-shadow context safety field must be false: {field_name}."
            )
    if context_packet.get("profit_claim") != "none":
        raise ValidationError("forward-shadow context profit claim must be none.")


def _validate_context_rows(
    rows: Sequence[_Bar],
    *,
    symbol: str,
) -> None:
    expected_end = _utc_datetime(OOS_END_EXCLUSIVE, "oos_end_exclusive")
    expected_start = expected_end - (
        CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_CONTEXT_ROWS * _ONE_HOUR
    )
    expected_timestamps = _hour_grid(expected_start, expected_end)
    if tuple(row.timestamp for row in rows) != expected_timestamps:
        raise ValidationError(
            "forward-shadow context must be the final continuous 169-hour grid."
        )
    if any(row.symbol != symbol for row in rows):
        raise ValidationError("forward-shadow context symbol drifted.")
    if rows[-1].imputed:
        raise ValidationError(
            "forward-shadow context requires a raw final boundary bar."
        )


def _bar_from_canonical(
    value: Mapping[str, object],
    *,
    expected_symbol: str,
) -> _Bar:
    symbol = _required_text(value.get("symbol"), "context.symbol")
    if symbol != expected_symbol:
        raise ValidationError("forward-shadow context symbol mismatch.")
    bar = _Bar(
        timestamp=_utc_datetime(value.get("timestamp"), "context.timestamp"),
        symbol=symbol,
        open=_positive_decimal(value.get("open"), "context.open"),
        high=_positive_decimal(value.get("high"), "context.high"),
        low=_positive_decimal(value.get("low"), "context.low"),
        close=_positive_decimal(value.get("close"), "context.close"),
        volume=_non_negative_decimal(value.get("volume"), "context.volume"),
        imputed=_required_bool(value.get("imputed"), "context.imputed"),
    )
    if (
        bar.low > min(bar.open, bar.close)
        or bar.high < max(bar.open, bar.close)
        or bar.low > bar.high
    ):
        raise ValidationError("forward-shadow context OHLC is inconsistent.")
    return bar


def _merge_selected_rows(
    existing: Sequence[_Bar],
    incoming: Sequence[_Bar],
) -> tuple[tuple[_Bar, ...], int, int]:
    merged = {row.timestamp: row for row in existing}
    added = 0
    duplicate = 0
    for row in incoming:
        current = merged.get(row.timestamp)
        if current is None:
            merged[row.timestamp] = row
            added += 1
        elif current.canonical() == row.canonical():
            duplicate += 1
        else:
            raise ValidationError("conflicting rewrite of an accrued shadow bar.")
    return tuple(sorted(merged.values(), key=lambda row: row.timestamp)), added, duplicate


def _checkpoint_ledger(
    decision_log: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    completed = [
        hour for hour in FORWARD_SHADOW_CHECKPOINT_HOURS if len(decision_log) >= hour
    ]
    return {
        "schema_version": CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_STATE_SCHEMA_VERSION,
        "record_type": "crypto_tournament_v2_forward_shadow_checkpoint_ledger",
        "completed_checkpoint_hours": completed,
        "checkpoints": [
            {
                "hour": hour,
                "status": "complete" if hour in completed else "pending",
                "decision_timestamp": (
                    decision_log[hour - 1].get("timestamp", "")
                    if hour in completed
                    else ""
                ),
                "promotion_or_early_stop_allowed": False,
            }
            for hour in FORWARD_SHADOW_CHECKPOINT_HOURS
        ],
    }


def _compute_terminal_evidence_fingerprint(
    *,
    state: Mapping[str, object],
    activation_warmup: Sequence[_Bar],
    shadow_normalized: Sequence[_Bar],
    decision_log: Sequence[Mapping[str, object]],
    classification: str,
    terminal_input_quality: Mapping[str, object],
    terminal_metrics: Mapping[str, object],
) -> str:
    return _stable_hash(
        {
            "preregistration_fingerprint": state[
                "preregistration_fingerprint"
            ],
            "activation_fingerprint": state["activation_fingerprint"],
            "context_sha256": state["context_sha256"],
            "activation_warmup_hash": _rows_hash(activation_warmup),
            "shadow_hash": _rows_hash(shadow_normalized),
            "decision_log": list(decision_log),
            "classification": classification,
            "terminal_input_quality": dict(terminal_input_quality),
            "terminal_metrics": dict(terminal_metrics),
        }
    )


def _build_terminal_evidence_export(
    *,
    state: Mapping[str, object],
    context: Sequence[_Bar],
    activation_warmup: Sequence[_Bar],
    shadow_raw: Sequence[_Bar],
    shadow_normalized: Sequence[_Bar],
    decision_log: Sequence[Mapping[str, object]],
    checkpoint_ledger: Mapping[str, object],
    terminal_packet: Mapping[str, object],
    as_of: datetime,
) -> dict[str, object]:
    eligible_classification = (
        "evidence_complete_for_bounded_paper_probe_review"
    )
    quality_classification = "terminal_shadow_input_quality_gate"
    classification = _required_text(
        state.get("terminal_classification"),
        "terminal_classification",
    )
    if classification not in {
        eligible_classification,
        quality_classification,
    }:
        raise ValidationError(
            "forward-shadow terminal classification is not exportable."
        )
    scoring_performed = _required_bool(
        state.get("terminal_scoring_performed"),
        "terminal_scoring_performed",
    )
    if scoring_performed is not (classification == eligible_classification):
        raise ValidationError(
            "forward-shadow terminal classification/scoring mismatch."
        )
    if (
        terminal_packet.get("schema_version")
        != CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PACKET_SCHEMA_VERSION
        or terminal_packet.get("record_type")
        != "crypto_tournament_v2_forward_shadow_packet"
        or terminal_packet.get("classification") != classification
        or terminal_packet.get("terminal_scoring_performed")
        is not scoring_performed
        or terminal_packet.get("terminal_evidence_fingerprint")
        != state.get("terminal_evidence_fingerprint")
        or terminal_packet.get("preregistration_fingerprint")
        != state.get("preregistration_fingerprint")
        or terminal_packet.get("activation_fingerprint")
        != state.get("activation_fingerprint")
    ):
        raise ValidationError(
            "forward-shadow terminal packet identity mismatch."
        )

    candidate = dict(_mapping(state.get("candidate"), "state.candidate"))
    symbol = _required_text(state.get("selected_symbol"), "selected_symbol")
    if (
        terminal_packet.get("selected_candidate") != candidate
        or candidate.get("symbol") != symbol
    ):
        raise ValidationError(
            "forward-shadow terminal candidate binding mismatch."
        )
    warmup_start = _utc_datetime(
        state.get("activation_warmup_start"),
        "activation_warmup_start",
    )
    shadow_start = _utc_datetime(state.get("shadow_start"), "shadow_start")
    shadow_end = _utc_datetime(
        state.get("shadow_end_exclusive"),
        "shadow_end_exclusive",
    )
    expected_window = {
        "start": shadow_start.isoformat(),
        "end_exclusive": shadow_end.isoformat(),
        "hourly_bars": FORWARD_SHADOW_HOURLY_BARS,
        "checkpoint_hours": list(FORWARD_SHADOW_CHECKPOINT_HOURS),
    }
    if terminal_packet.get("shadow_window") != expected_window:
        raise ValidationError(
            "forward-shadow terminal window binding mismatch."
        )

    progress = _mapping(terminal_packet.get("progress"), "progress")
    completed_checkpoints = list(
        checkpoint_ledger.get("completed_checkpoint_hours", [])
    )
    expected_progress = {
        "activation_warmup_expected_rows": _hour_count(
            warmup_start,
            shadow_start,
        ),
        "activation_warmup_raw_rows": len(activation_warmup),
        "shadow_expected_rows": FORWARD_SHADOW_HOURLY_BARS,
        "shadow_raw_rows": len(shadow_raw),
        "shadow_normalized_rows": len(shadow_normalized),
        "decision_log_rows": len(decision_log),
        "completed_checkpoint_hours": completed_checkpoints,
    }
    if dict(progress) != expected_progress:
        raise ValidationError(
            "forward-shadow terminal progress binding mismatch."
        )
    if completed_checkpoints != list(
        state.get("completed_checkpoint_hours", [])
    ):
        raise ValidationError(
            "forward-shadow terminal checkpoint binding mismatch."
        )
    if (
        classification == eligible_classification
        and completed_checkpoints != list(FORWARD_SHADOW_CHECKPOINT_HOURS)
    ):
        raise ValidationError(
            "forward-shadow terminal checkpoints are incomplete."
        )

    warmup_normalized, warmup_quality, warmup_errors = (
        _normalize_selected_window(
            activation_warmup,
            symbol=symbol,
            start=warmup_start,
            end_exclusive=shadow_start,
            phase="activation_warmup",
            strict_complete=True,
        )
    )
    recomputed_shadow, shadow_quality, shadow_errors = (
        _normalize_selected_window(
            shadow_raw,
            symbol=symbol,
            start=shadow_start,
            end_exclusive=shadow_end,
            phase="shadow",
            strict_complete=False,
        )
    )
    terminal_errors = list(warmup_errors + shadow_errors)
    if len(shadow_normalized) != FORWARD_SHADOW_HOURLY_BARS:
        terminal_errors.append("shadow_normalized_grid_incomplete")
    if len(decision_log) != FORWARD_SHADOW_HOURLY_BARS:
        terminal_errors.append("shadow_decision_log_incomplete")
    expected_input_quality = {
        "activation_warmup": warmup_quality,
        "shadow": shadow_quality,
        "errors": list(dict.fromkeys(terminal_errors)),
    }
    terminal_input_quality = dict(
        _mapping(
            terminal_packet.get("terminal_input_quality"),
            "terminal_input_quality",
        )
    )
    if (
        terminal_input_quality != expected_input_quality
        or terminal_packet.get("activation_warmup_quality") != warmup_quality
        or terminal_packet.get("shadow_quality") != shadow_quality
    ):
        raise ValidationError(
            "forward-shadow terminal input-quality evidence drifted."
        )
    terminal_metrics = dict(
        _mapping(terminal_packet.get("terminal_metrics"), "terminal_metrics")
    )

    if classification == eligible_classification:
        if terminal_errors:
            raise ValidationError(
                "eligible forward-shadow terminal evidence has quality errors."
            )
        if (
            len(shadow_raw) != FORWARD_SHADOW_HOURLY_BARS
            or len(shadow_normalized) != FORWARD_SHADOW_HOURLY_BARS
            or len(decision_log) != FORWARD_SHADOW_HOURLY_BARS
            or [row.canonical() for row in recomputed_shadow]
            != [row.canonical() for row in shadow_normalized]
        ):
            raise ValidationError(
                "eligible forward-shadow terminal grid is incomplete."
            )
        regenerated_decisions, regenerated_metrics = _build_decision_evidence(
            context=context,
            activation_warmup=warmup_normalized,
            shadow_rows=shadow_normalized,
            candidate=candidate,
        )
        if tuple(decision_log) != regenerated_decisions:
            raise ValidationError(
                "forward-shadow terminal decisions failed regeneration."
            )
        if terminal_metrics != regenerated_metrics:
            raise ValidationError(
                "forward-shadow terminal metrics failed regeneration."
            )
    elif terminal_metrics:
        raise ValidationError(
            "input-quality terminal evidence cannot publish strategy metrics."
        )

    evidence_fingerprint = _compute_terminal_evidence_fingerprint(
        state=state,
        activation_warmup=warmup_normalized,
        shadow_normalized=shadow_normalized,
        decision_log=decision_log,
        classification=classification,
        terminal_input_quality=terminal_input_quality,
        terminal_metrics=terminal_metrics,
    )
    if evidence_fingerprint != state.get("terminal_evidence_fingerprint"):
        raise ValidationError(
            "forward-shadow terminal evidence fingerprint failed regeneration."
        )

    false_fields = (
        "broker_read_occurred",
        "broker_mutation_authorized",
        "broker_mutation_occurred",
        "paper_submit_authorized",
        "paper_submit_occurred",
        "paper_cancel_occurred",
        "paper_replace_occurred",
        "paper_close_occurred",
        "paper_liquidate_occurred",
        "paper_or_broker_eligible",
        "bounded_paper_probe_review_permitted",
        "paper_or_live_execution_authorized",
        "capital_allocation_authorized",
        "live_authorized",
        "live_endpoint_touched",
        "credential_values_exposed",
    )
    for field_name in false_fields:
        if terminal_packet.get(field_name) is not False:
            raise ValidationError(
                f"forward-shadow terminal safety field must be false: {field_name}."
            )
    if (
        terminal_packet.get("paper_planning_eligibility") != "not_eligible"
        or terminal_packet.get("profit_claim") != "none"
    ):
        raise ValidationError(
            "forward-shadow terminal authority boundary drifted."
        )
    source_network = _required_bool(
        terminal_packet.get("network_access_attempted"),
        "network_access_attempted",
    )
    source_market_data = _required_bool(
        terminal_packet.get("market_data_fetch_occurred"),
        "market_data_fetch_occurred",
    )

    artifact_sha256 = dict(
        _mapping(state.get("artifact_sha256"), "artifact_sha256")
    )
    source_binding = {
        "preregistration_fingerprint": state["preregistration_fingerprint"],
        "state_schema_version": state["schema_version"],
        "packet_schema_version": terminal_packet["schema_version"],
        "activation_fingerprint": state["activation_fingerprint"],
        "activation_source_state_fingerprint": state[
            "source_state_fingerprint"
        ],
        "state_fingerprint": state["state_fingerprint"],
        "context_sha256": state["context_sha256"],
        "terminal_packet_sha256": state["terminal_packet_sha256"],
        "terminal_evidence_fingerprint": evidence_fingerprint,
        "terminal_closed_at": state["terminal_closed_at"],
        "artifact_sha256": artifact_sha256,
    }
    safety = {
        "source_network_access_attempted": source_network,
        "source_market_data_fetch_occurred": source_market_data,
        "broker_read_occurred": False,
        "broker_mutation_authorized": False,
        "broker_mutation_occurred": False,
        "paper_probe_authorized": False,
        "paper_mutation_authorized": False,
        "capital_allocation_authorized": False,
        "live_authorized": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "profit_claim": "none",
    }
    basis: dict[str, object] = {
        "classification": classification,
        "review_eligible_source": classification == eligible_classification,
        "terminal_scoring_performed": scoring_performed,
        "selected_candidate": candidate,
        "selected_symbol": symbol,
        "shadow_window": expected_window,
        "progress": expected_progress,
        "terminal_input_quality": terminal_input_quality,
        "terminal_metrics": terminal_metrics,
        "source_binding": source_binding,
        "safety": safety,
    }
    identity_basis = {
        "schema_version": (
            CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_TERMINAL_EVIDENCE_SCHEMA_VERSION
        ),
        "record_type": (
            "crypto_tournament_v2_forward_shadow_terminal_evidence"
        ),
        **basis,
    }
    return {
        **identity_basis,
        "as_of": as_of.isoformat(),
        "evidence_export_fingerprint": _stable_hash(identity_basis),
    }


def _load_terminal_packet(
    paths: Mapping[str, Path],
    state: Mapping[str, object],
) -> dict[str, object]:
    expected_sha = _required_text(
        state.get("terminal_packet_sha256"), "terminal_packet_sha256"
    )
    if (
        not paths["terminal_packet"].is_file()
        or _file_sha256(paths["terminal_packet"]) != expected_sha
    ):
        raise ValidationError("forward-shadow terminal packet hash mismatch.")
    packet = _read_json_mapping(paths["terminal_packet"])
    closure = _mapping(packet.get("terminal_closure"), "terminal_closure")
    if (
        closure.get("terminal_outcome_closed") is not True
        or closure.get("terminal_classification")
        != state.get("terminal_classification")
        or closure.get("terminal_closed_at") != state.get("terminal_closed_at")
        or closure.get("terminal_scoring_performed")
        is not state.get("terminal_scoring_performed")
        or closure.get("terminal_evidence_fingerprint")
        != state.get("terminal_evidence_fingerprint")
    ):
        raise ValidationError("forward-shadow terminal closure binding mismatch.")
    return packet


def _state_summary(state: Mapping[str, object]) -> dict[str, object]:
    return {
        key: state.get(key)
        for key in (
            "schema_version",
            "state_fingerprint",
            "preregistration_fingerprint",
            "activation_fingerprint",
            "source_terminal_packet_sha256",
            "source_terminal_evidence_fingerprint",
            "source_state_fingerprint",
            "selected_symbol",
            "initialized_at",
            "updated_at",
            "shadow_start",
            "shadow_end_exclusive",
            "context_row_count",
            "activation_warmup_raw_rows",
            "shadow_raw_rows",
            "shadow_normalized_rows",
            "decision_log_rows",
            "completed_checkpoint_hours",
            "terminal_outcome_closed",
            "terminal_classification",
            "terminal_closed_at",
            "terminal_packet_sha256",
            "terminal_evidence_fingerprint",
            "terminal_scoring_performed",
        )
    }


def _dormant_packet(
    activation: Mapping[str, object],
    as_of: datetime,
) -> dict[str, object]:
    return {
        "schema_version": CRYPTO_TOURNAMENT_V2_FORWARD_SHADOW_PACKET_SCHEMA_VERSION,
        "record_type": "crypto_tournament_v2_forward_shadow_packet",
        "as_of": as_of.isoformat(),
        "classification": activation.get("classification", ""),
        "phase": "dormant_before_terminal_winner",
        "principal_blocker": activation.get("principal_blocker", ""),
        "selected_candidate": {},
        "shadow_state_initialized": False,
        "activation_fingerprint": "",
        "next_action": activation.get("next_action", ""),
        "network_access_attempted": False,
        "market_data_fetch_occurred": False,
        "broker_read_occurred": False,
        "broker_mutation_authorized": False,
        "broker_mutation_occurred": False,
        "paper_submit_authorized": False,
        "paper_submit_occurred": False,
        "paper_cancel_occurred": False,
        "paper_replace_occurred": False,
        "paper_close_occurred": False,
        "paper_liquidate_occurred": False,
        "paper_or_broker_eligible": False,
        "paper_or_live_execution_authorized": False,
        "capital_allocation_authorized": False,
        "live_authorized": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "profit_claim": "none",
    }


def _empty_quality(
    phase: str,
    start: datetime,
    end_exclusive: datetime,
) -> dict[str, object]:
    return {
        "phase": phase,
        "status": "pending" if end_exclusive > start else "passed",
        "start": start.isoformat(),
        "end_exclusive": end_exclusive.isoformat(),
        "expected_raw_rows": _hour_count(start, end_exclusive),
        "observed_raw_rows": 0,
        "raw_coverage": "0",
        "positive_raw_volume_fraction": "0",
        "missing_timestamps": [],
        "maximum_consecutive_missing_hours": 0,
        "imputed_rows": 0,
    }


def _empty_evidence(observed_rows: int) -> dict[str, object]:
    return {
        "base_metrics": {},
        "stress_metrics": {},
        "same_symbol_buy_hold": {},
        "cash_total_return": "0",
        "decision_log_expected_rows": FORWARD_SHADOW_HOURLY_BARS,
        "decision_log_observed_rows": observed_rows,
        "decision_log_missing_rows": max(
            0, FORWARD_SHADOW_HOURLY_BARS - observed_rows
        ),
        "decision_log_duplicate_rows": 0,
        "decision_log_complete": False,
        "paper_probe_authorized": False,
        "live_probe_authorized": False,
    }


def _artifact_hashes(
    paths: Mapping[str, Path],
    *,
    write_artifacts: bool,
) -> dict[str, str]:
    if not write_artifacts:
        return {name: "" for name in _ARTIFACT_NAMES}
    return {name: _file_sha256(paths[name]) for name in _ARTIFACT_NAMES}


def _state_paths(root: Path) -> dict[str, Path]:
    return {
        "preregistration": root / "frozen_preregistration.json",
        "activation": root / "frozen_activation.json",
        "source_terminal_packet": root / "source_terminal_packet.json",
        "context": root / "signal_context.csv",
        "activation_warmup": root / "activation_warmup_history.csv",
        "shadow_raw": root / "accrued_shadow_history.csv",
        "shadow_normalized": root / "normalized_shadow_history.csv",
        "ledger": root / "receipt_ledger.json",
        "decision_log": root / "hourly_decision_log.jsonl",
        "checkpoint_ledger": root / "checkpoint_ledger.json",
        "state": root / "frozen_state.json",
        "terminal_packet": root / "terminal_packet.json",
        "transaction": root / "pending_transaction.json",
        "packet_json": root / "operating_packet.json",
        "packet_markdown": root / "operating_packet.md",
    }


def _write_operating_packet(
    paths: Mapping[str, Path],
    packet: Mapping[str, object],
) -> None:
    _write_json_atomic(paths["packet_json"], packet)
    _write_text_atomic(
        paths["packet_markdown"],
        render_crypto_tournament_v2_forward_shadow_state_markdown(packet),
    )


def _write_json_lines_atomic(
    path: Path,
    rows: Sequence[Mapping[str, object]],
) -> None:
    text = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )
    _write_text_atomic(path, text)


def _read_json_lines(path: Path) -> tuple[dict[str, object], ...]:
    if not path.is_file():
        raise ValidationError(f"missing JSONL artifact: {path}.")
    rows: list[dict[str, object]] = []
    try:
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, Mapping):
                raise ValidationError(
                    f"JSONL row {line_number} must be an object."
                )
            rows.append(dict(value))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid JSONL artifact: {path}.") from exc
    return tuple(rows)


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_bytes(payload)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be an object.")
    return value


def _mapping_sequence(
    value: object,
    field_name: str,
) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValidationError(f"{field_name} must be a list of objects.")
    return tuple(_mapping(item, field_name) for item in value)


def _string_sequence(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value)


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be non-empty text.")
    return value.strip()


def _required_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{field_name} must be boolean.")
    return value


def _utc_datetime(value: datetime | str | object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str) and value.strip():
        text = value.strip().replace("Z", "+00:00")
        try:
            result = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be ISO-8601.") from exc
    else:
        raise ValidationError(f"{field_name} must be a UTC timestamp.")
    if result.tzinfo is None or result.utcoffset() != timedelta(0):
        raise ValidationError(f"{field_name} must include UTC offset.")
    return result.astimezone(UTC)


def _floor_hour(value: datetime) -> datetime:
    return value.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def _hour_grid(start: datetime, end_exclusive: datetime) -> tuple[datetime, ...]:
    count = _hour_count(start, end_exclusive)
    return tuple(start + (index * _ONE_HOUR) for index in range(count))


def _hour_count(start: datetime, end_exclusive: datetime) -> int:
    count = int((end_exclusive - start) / _ONE_HOUR)
    if count < 0 or start + (count * _ONE_HOUR) != end_exclusive:
        raise ValidationError("forward-shadow window must align to UTC hours.")
    return count


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


def _decimal(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValidationError("invalid forward-shadow decimal value.") from exc
    if not result.is_finite():
        raise ValidationError("forward-shadow decimal must be finite.")
    return result


def _positive_decimal(value: object, field_name: str) -> Decimal:
    result = _decimal(value)
    if result <= _ZERO:
        raise ValidationError(f"{field_name} must be positive.")
    return result


def _non_negative_decimal(value: object, field_name: str) -> Decimal:
    result = _decimal(value)
    if result < _ZERO:
        raise ValidationError(f"{field_name} must be non-negative.")
    return result


def _compound_returns(values: Sequence[Decimal]) -> Decimal:
    equity = _ONE
    for value in values:
        equity *= _ONE + value
    return equity - _ONE


def _stable_hash(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _local_path(value: Path | str, field_name: str) -> Path:
    path = Path(value)
    if str(path).startswith(("\\\\", "//")):
        raise ValidationError(f"{field_name} must be a local path.")
    return path


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"
