"""v5.9 BTCUSD paper certification-result ingestion.

This module consumes a local v5.8 BTCUSD paper submit/cancel certification
artifact and writes a durable no-submit summary plus a future fill/exit
approval packet for operator review. It never reads a broker or mutates orders.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError


CRYPTO_PAPER_CERTIFICATION_INGESTION_SCHEMA_VERSION = (
    "v5_9_crypto_paper_certification_ingestion_v1"
)
CRYPTO_PAPER_CERTIFICATION_INGESTION_COMMAND = (
    "run_crypto_paper_certification_ingestion"
)
CRYPTO_PAPER_CERTIFICATION_INGESTION_DEFAULT_CERTIFICATION_RESULT = Path(
    "runs/crypto_paper_submit_cancel_certification/latest/"
    "certification_result.json"
)
CRYPTO_PAPER_CERTIFICATION_INGESTION_DEFAULT_OUTPUT_ROOT = Path(
    "runs/crypto_paper_certification_ingestion/latest"
)

CERTIFICATION_STATUS_CERTIFIED_NO_FILL = "certified_submit_cancel_no_fill"
CERTIFICATION_STATUS_PRIOR_FILL_OBSERVED = "not_certified_prior_fill_observed"
CERTIFICATION_STATUS_BLOCKED = "blocked"
CERTIFIED_SCOPE = "BTCUSD paper submit/cancel only"
FUTURE_FILL_APPROVAL_PACKET_REQUESTED_SCOPE = (
    "bounded_btcusd_paper_fill_and_exit_certification"
)
APPROVAL_PACKET_STATUS_READY = "ready_for_operator_review"
APPROVAL_PACKET_STATUS_BLOCKED = "blocked"
APPROVAL_STATE_NOT_AUTHORIZED = "not_authorized"
SYMBOL_BTCUSD = "BTCUSD"
APPROVED_QTY = Decimal("0.000396783")
MAX_NOTIONAL = Decimal("25")

REQUIRED_LABELS = (
    "paper_lab_only",
    "signal_evaluation_only",
    "not_live_authorized",
    "profit_claim=none",
    "certification_result_ingestion_only",
    "paper_fill_approval_packet_only",
    "operator_review_required",
    "not_submittable",
    "btcusd_only",
)

DISALLOWED_ACTIONS = (
    "current_broker_read",
    "current_broker_mutation",
    "current_paper_submit",
    "current_paper_cancel",
    "current_paper_replace",
    "current_paper_close",
    "current_paper_liquidate",
    "live_trading",
    "live_submit",
    "live_cancel",
    "live_replace",
    "live_close",
    "live_liquidate",
    "additional_orders_beyond_one_entry_and_one_exit",
    "replacement",
    "liquidation_or_close_all",
    "capital_change",
    "credential_exposure",
    "paid_service_new_account_or_new_secret",
    "autonomous_submit_without_operator_authorization",
    "retry_submit",
)

__all__ = [
    "APPROVAL_PACKET_STATUS_BLOCKED",
    "APPROVAL_PACKET_STATUS_READY",
    "APPROVAL_STATE_NOT_AUTHORIZED",
    "CERTIFICATION_STATUS_BLOCKED",
    "CERTIFICATION_STATUS_CERTIFIED_NO_FILL",
    "CERTIFICATION_STATUS_PRIOR_FILL_OBSERVED",
    "CRYPTO_PAPER_CERTIFICATION_INGESTION_COMMAND",
    "CRYPTO_PAPER_CERTIFICATION_INGESTION_DEFAULT_CERTIFICATION_RESULT",
    "CRYPTO_PAPER_CERTIFICATION_INGESTION_DEFAULT_OUTPUT_ROOT",
    "CRYPTO_PAPER_CERTIFICATION_INGESTION_SCHEMA_VERSION",
    "DISALLOWED_ACTIONS",
    "FUTURE_FILL_APPROVAL_PACKET_REQUESTED_SCOPE",
    "REQUIRED_LABELS",
    "build_crypto_paper_certification_ingestion",
    "main",
    "render_crypto_paper_certification_ingestion_markdown",
    "render_crypto_paper_certification_ingestion_text",
    "render_paper_fill_experiment_approval_packet_markdown",
    "run_crypto_paper_certification_ingestion",
    "write_crypto_paper_certification_ingestion_artifacts",
]


def run_crypto_paper_certification_ingestion(
    *,
    certification_result_path: Path | str = (
        CRYPTO_PAPER_CERTIFICATION_INGESTION_DEFAULT_CERTIFICATION_RESULT
    ),
    output_root: Path | str = CRYPTO_PAPER_CERTIFICATION_INGESTION_DEFAULT_OUTPUT_ROOT,
    approved_qty: Decimal | str = APPROVED_QTY,
    max_notional: Decimal | str = MAX_NOTIONAL,
    as_of: str = "",
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Read the prior local certification result and write no-submit artifacts."""

    source_path = Path(certification_result_path)
    approved_qty_decimal = _decimal_value(approved_qty, "approved_qty")
    max_notional_decimal = _decimal_value(max_notional, "max_notional")
    read_result = _read_json_mapping(source_path)
    ingestion = build_crypto_paper_certification_ingestion(
        certification_result=read_result["payload"],
        certification_result_source=source_path,
        certification_result_read_error=_text(read_result["error"]),
        approved_qty=approved_qty_decimal,
        max_notional=max_notional_decimal,
        as_of=as_of,
    )
    if write_artifacts:
        ingestion["artifact_paths"] = (
            write_crypto_paper_certification_ingestion_artifacts(
                output_root,
                ingestion,
            )
        )
    return ingestion


def build_crypto_paper_certification_ingestion(
    *,
    certification_result: Mapping[str, object],
    certification_result_source: Path | str,
    certification_result_read_error: str = "",
    approved_qty: Decimal | str = APPROVED_QTY,
    max_notional: Decimal | str = MAX_NOTIONAL,
    as_of: str = "",
) -> dict[str, object]:
    """Build the durable certification summary and future approval packet."""

    source_path = Path(certification_result_source)
    approved_qty_decimal = _decimal_value(approved_qty, "approved_qty")
    max_notional_decimal = _decimal_value(max_notional, "max_notional")
    prior = _prior_certification_summary(
        certification_result,
        source_path=source_path,
        read_error=certification_result_read_error,
    )
    blockers = _certification_blockers(
        certification_result,
        read_error=certification_result_read_error,
        prior=prior,
        approved_qty=approved_qty_decimal,
        max_notional=max_notional_decimal,
    )
    filled_qty = _decimal_or_none(prior["filled_qty"])
    if filled_qty is not None and filled_qty > Decimal("0"):
        certification_status = CERTIFICATION_STATUS_PRIOR_FILL_OBSERVED
    elif blockers:
        certification_status = CERTIFICATION_STATUS_BLOCKED
    else:
        certification_status = CERTIFICATION_STATUS_CERTIFIED_NO_FILL

    packet = _build_paper_fill_experiment_approval_packet(
        prior=prior,
        blockers=blockers,
        certification_status=certification_status,
        max_notional=max_notional_decimal,
        as_of=as_of or _text(certification_result.get("as_of")),
    )
    return {
        "schema_version": CRYPTO_PAPER_CERTIFICATION_INGESTION_SCHEMA_VERSION,
        "record_type": "crypto_paper_certification_ingestion",
        "operator_command": CRYPTO_PAPER_CERTIFICATION_INGESTION_COMMAND,
        "as_of": as_of or _text(certification_result.get("as_of")),
        "certification_result_source": str(source_path),
        "certification_result_readable": not certification_result_read_error,
        "certification_result_read_error": certification_result_read_error,
        "certification_result_sha256": prior["source_sha256"],
        "certification_status": certification_status,
        "certified_scope": (
            CERTIFIED_SCOPE
            if certification_status == CERTIFICATION_STATUS_CERTIFIED_NO_FILL
            else ""
        ),
        "approved_qty": _decimal_text(approved_qty_decimal),
        "max_notional": _decimal_text(max_notional_decimal),
        "blockers": blockers,
        "prior_certification": prior,
        "prior_certification_id": prior["prior_certification_id"],
        "prior_client_order_id": prior["client_order_id"],
        "prior_outcome_classification": prior["outcome_classification"],
        "prior_final_order_status": prior["final_order_status"],
        "prior_filled_qty": prior["filled_qty"],
        "prior_residual_position": prior["residual_position"],
        "prior_broker_read_observed": prior["broker_read_observed"],
        "prior_broker_mutation_performed": prior["broker_mutation_performed"],
        "prior_paper_submit_performed": prior["paper_submit_performed"],
        "prior_live_endpoint_touched": prior["live_endpoint_touched"],
        "prior_credential_values_exposed": prior["credential_values_exposed"],
        "live_authorized": False,
        "autonomous_submit_authorized": False,
        "paper_fill_authorized": False,
        "broker_mutation_authorized_by_this_packet": False,
        "broker_action_permitted": False,
        "paper_submit_authorized": False,
        "paper_entry_authorized": False,
        "paper_exit_authorized": False,
        "broker_read_performed_current_run": False,
        "broker_mutation_performed_current_run": False,
        "paper_submit_performed_current_run": False,
        "paper_cancel_performed_current_run": False,
        "live_endpoint_touched_current_run": False,
        "live_mutation_performed_current_run": False,
        "credential_values_exposed": False,
        "network_access_attempted": False,
        "profit_claim": "none",
        "labels": list(REQUIRED_LABELS),
        "paper_fill_experiment_approval_packet": packet,
        "next_operator_action": _next_operator_action(certification_status),
    }


def write_crypto_paper_certification_ingestion_artifacts(
    output_root: Path | str,
    ingestion: Mapping[str, object],
) -> dict[str, str]:
    """Write ignored runtime artifacts for the ingestion and approval packet."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "certification_ingestion_json": root / "certification_ingestion.json",
        "certification_ingestion_md": root / "certification_ingestion.md",
        "paper_fill_experiment_approval_packet_json": (
            root / "paper_fill_experiment_approval_packet.json"
        ),
        "paper_fill_experiment_approval_packet_md": (
            root / "paper_fill_experiment_approval_packet.md"
        ),
        "operating_record": root / "operating_record.jsonl",
    }
    artifact_paths = {key: str(path) for key, path in paths.items()}
    manifest_path = root / "manifest.json"
    artifact_paths["manifest"] = str(manifest_path)

    packet = _mapping(ingestion.get("paper_fill_experiment_approval_packet"))
    ingestion_payload = {**dict(ingestion), "artifact_paths": artifact_paths}
    packet_payload = {
        **packet,
        "artifact_paths": artifact_paths,
    }
    _write_json(paths["certification_ingestion_json"], ingestion_payload)
    paths["certification_ingestion_md"].write_text(
        render_crypto_paper_certification_ingestion_markdown(ingestion_payload) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_json(paths["paper_fill_experiment_approval_packet_json"], packet_payload)
    paths["paper_fill_experiment_approval_packet_md"].write_text(
        render_paper_fill_experiment_approval_packet_markdown(packet_payload) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    paths["operating_record"].write_text(
        json.dumps(
            _json_safe(_operating_record(ingestion_payload)),
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    manifest = {
        "schema_version": CRYPTO_PAPER_CERTIFICATION_INGESTION_SCHEMA_VERSION,
        "record_type": "crypto_paper_certification_ingestion_manifest",
        "as_of": ingestion.get("as_of", ""),
        "artifact_root": str(root),
        "required_artifacts": {
            key: _artifact_entry(path)
            for key, path in sorted(paths.items())
        },
        "manifest": {"path": str(manifest_path)},
        "input_artifacts": {
            "certification_result": {
                "path": _text(ingestion.get("certification_result_source")),
                "sha256": _text(ingestion.get("certification_result_sha256")),
            },
        },
        "certification_status": ingestion.get("certification_status", ""),
        "approval_packet_status": packet.get("approval_packet_status", ""),
        "approval_state": APPROVAL_STATE_NOT_AUTHORIZED,
        "broker_action_permitted": False,
        "paper_submit_authorized": False,
        "paper_fill_authorized": False,
        "broker_mutation_authorized_by_this_packet": False,
        "broker_read_performed_current_run": False,
        "broker_mutation_performed_current_run": False,
        "paper_submit_performed_current_run": False,
        "live_endpoint_touched_current_run": False,
        "live_mutation_performed_current_run": False,
        "credential_values_exposed": False,
        "network_access_attempted": False,
        "generated_under_runs": _generated_under_runs(root),
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
    }
    _write_json(manifest_path, manifest)
    return artifact_paths


def render_crypto_paper_certification_ingestion_markdown(
    ingestion: Mapping[str, object],
) -> str:
    """Render a durable operator-readable certification summary."""

    blockers = list(_string_sequence(ingestion.get("blockers")))
    packet = _mapping(ingestion.get("paper_fill_experiment_approval_packet"))
    return "\n".join(
        [
            "# Crypto Paper Certification Ingestion",
            "",
            f"- certification result source: `{ingestion.get('certification_result_source', '')}`",
            f"- certification status: `{ingestion.get('certification_status', '')}`",
            f"- certified scope: `{ingestion.get('certified_scope', '')}`",
            f"- prior certification id: `{ingestion.get('prior_certification_id', '')}`",
            f"- prior client order id: `{ingestion.get('prior_client_order_id', '')}`",
            (
                "- prior outcome classification: "
                f"`{ingestion.get('prior_outcome_classification', '')}`"
            ),
            (
                "- prior final order status: "
                f"`{ingestion.get('prior_final_order_status', '')}`"
            ),
            f"- prior filled qty: `{ingestion.get('prior_filled_qty', '')}`",
            f"- blockers: `{','.join(blockers)}`",
            "",
            "## Safety",
            "",
            "- live authorized: `false`",
            "- autonomous submit authorized: `false`",
            "- paper fill authorized: `false`",
            "- broker mutation authorized by this packet: `false`",
            "- broker read performed current run: `false`",
            "- broker mutation performed current run: `false`",
            "- paper submit performed current run: `false`",
            "- live endpoint touched current run: `false`",
            "- credential values exposed: `false`",
            "",
            "## Future Packet",
            "",
            (
                "- approval packet status: "
                f"`{packet.get('approval_packet_status', '')}`"
            ),
            f"- approval state: `{packet.get('approval_state', '')}`",
            (
                "- requested future authorization scope: "
                f"`{packet.get('requested_future_authorization_scope', '')}`"
            ),
            "",
            "Labels: " + ", ".join(_string_sequence(ingestion.get("labels"))),
        ]
    )


def render_paper_fill_experiment_approval_packet_markdown(
    packet: Mapping[str, object],
) -> str:
    """Render the no-submit future fill/exit approval packet."""

    blockers = list(_string_sequence(packet.get("blockers")))
    return "\n".join(
        [
            "# BTCUSD Paper Fill Experiment Approval Packet",
            "",
            f"- packet status: `{packet.get('approval_packet_status', '')}`",
            f"- approval state: `{packet.get('approval_state', '')}`",
            (
                "- requested future authorization scope: "
                f"`{packet.get('requested_future_authorization_scope', '')}`"
            ),
            f"- prior certification result: `{packet.get('prior_certification_result_source', '')}`",
            f"- prior certification sha256: `{packet.get('prior_certification_result_sha256', '')}`",
            f"- prior certification id: `{packet.get('prior_certification_id', '')}`",
            f"- prior client order id: `{packet.get('prior_client_order_id', '')}`",
            f"- proposed symbol: `{packet.get('proposed_symbol', '')}`",
            f"- proposed max notional: `{packet.get('proposed_max_notional', '')}`",
            f"- blockers: `{','.join(blockers)}`",
            "",
            "## Required Operator Phrase",
            "",
            str(packet.get("required_operator_phrase", "")),
            "",
            "## Current Authority",
            "",
            (
                "This packet is generated for operator review only. It keeps "
                "approval_state as not_authorized, does not authorize submit, "
                "does not authorize a fill, and does not authorize broker "
                "mutation."
            ),
            "",
            "## Disallowed Actions",
            "",
            ", ".join(_string_sequence(packet.get("disallowed_actions"))),
            "",
            "Labels: " + ", ".join(_string_sequence(packet.get("labels"))),
        ]
    )


def render_crypto_paper_certification_ingestion_text(
    ingestion: Mapping[str, object],
) -> str:
    """Render compact key-value output for the PowerShell wrapper."""

    packet = _mapping(ingestion.get("paper_fill_experiment_approval_packet"))
    artifacts = _mapping(ingestion.get("artifact_paths"))
    lines = [
        f"crypto_paper_certification_ingestion_command={CRYPTO_PAPER_CERTIFICATION_INGESTION_COMMAND}",
        f"certification_status={_text(ingestion.get('certification_status'))}",
        f"certified_scope={_text(ingestion.get('certified_scope'))}",
        f"prior_certification_id={_text(ingestion.get('prior_certification_id'))}",
        f"prior_client_order_id={_text(ingestion.get('prior_client_order_id'))}",
        (
            "prior_outcome_classification="
            f"{_text(ingestion.get('prior_outcome_classification'))}"
        ),
        f"prior_final_order_status={_text(ingestion.get('prior_final_order_status'))}",
        f"prior_filled_qty={_text(ingestion.get('prior_filled_qty'))}",
        f"blockers={','.join(_string_sequence(ingestion.get('blockers')))}",
        f"approval_packet_status={_text(packet.get('approval_packet_status'))}",
        f"approval_state={_text(packet.get('approval_state'))}",
        (
            "requested_future_authorization_scope="
            f"{_text(packet.get('requested_future_authorization_scope'))}"
        ),
        "paper_submit_authorized=false",
        "paper_fill_authorized=false",
        "broker_mutation_authorized_by_this_packet=false",
        "broker_read_performed_current_run=false",
        "broker_mutation_performed_current_run=false",
        "paper_submit_performed_current_run=false",
        "live_endpoint_touched_current_run=false",
        "credential_values_exposed=false",
        f"prior_broker_read_observed={_bool_text(ingestion.get('prior_broker_read_observed'))}",
        (
            "prior_broker_mutation_performed="
            f"{_bool_text(ingestion.get('prior_broker_mutation_performed'))}"
        ),
        (
            "prior_paper_submit_performed="
            f"{_bool_text(ingestion.get('prior_paper_submit_performed'))}"
        ),
        (
            "prior_live_endpoint_touched="
            f"{_bool_text(ingestion.get('prior_live_endpoint_touched'))}"
        ),
        (
            "prior_credential_values_exposed="
            f"{_bool_text(ingestion.get('prior_credential_values_exposed'))}"
        ),
        (
            "required_operator_phrase="
            f"{_text(packet.get('required_operator_phrase'))}"
        ),
    ]
    for key in (
        "certification_ingestion_json",
        "certification_ingestion_md",
        "paper_fill_experiment_approval_packet_json",
        "paper_fill_experiment_approval_packet_md",
        "operating_record",
        "manifest",
    ):
        lines.append(f"artifact_{key}={_text(artifacts.get(key))}")
    return "\n".join(lines)


def _build_paper_fill_experiment_approval_packet(
    *,
    prior: Mapping[str, object],
    blockers: Sequence[str],
    certification_status: str,
    max_notional: Decimal,
    as_of: str,
) -> dict[str, object]:
    packet_status = (
        APPROVAL_PACKET_STATUS_READY
        if certification_status == CERTIFICATION_STATUS_CERTIFIED_NO_FILL
        else APPROVAL_PACKET_STATUS_BLOCKED
    )
    packet_blockers = list(blockers)
    required_operator_phrase = _required_operator_phrase(
        prior_certification_id=_text(prior.get("prior_certification_id")),
        client_order_id=_text(prior.get("client_order_id")),
        symbol=SYMBOL_BTCUSD,
        max_notional=_decimal_text(max_notional),
    )
    return {
        "schema_version": CRYPTO_PAPER_CERTIFICATION_INGESTION_SCHEMA_VERSION,
        "record_type": "paper_fill_experiment_approval_packet",
        "as_of": as_of,
        "approval_packet_status": packet_status,
        "approval_state": APPROVAL_STATE_NOT_AUTHORIZED,
        "requested_future_authorization_scope": (
            FUTURE_FILL_APPROVAL_PACKET_REQUESTED_SCOPE
        ),
        "prior_certification_result_source": prior.get("source_path", ""),
        "prior_certification_result_sha256": prior.get("source_sha256", ""),
        "prior_certification_result_referenced": {
            "path": prior.get("source_path", ""),
            "sha256": prior.get("source_sha256", ""),
            "schema_version": prior.get("schema_version", ""),
            "as_of": prior.get("as_of", ""),
            "outcome_classification": prior.get("outcome_classification", ""),
            "client_order_id": prior.get("client_order_id", ""),
            "final_order_status": prior.get("final_order_status", ""),
            "filled_qty": prior.get("filled_qty", ""),
        },
        "prior_certification_id": prior.get("prior_certification_id", ""),
        "prior_client_order_id": prior.get("client_order_id", ""),
        "prior_final_order_status": prior.get("final_order_status", ""),
        "prior_filled_qty": prior.get("filled_qty", ""),
        "prior_residual_position": prior.get("residual_position", {}),
        "proposed_symbol": SYMBOL_BTCUSD,
        "proposed_symbol_scope": "BTCUSD only",
        "proposed_max_notional": _decimal_text(max_notional),
        "proposed_max_notional_cap": _decimal_text(MAX_NOTIONAL),
        "proposed_notional_no_greater_than_25": max_notional <= MAX_NOTIONAL,
        "required_operator_phrase": required_operator_phrase,
        "operator_phrase_generated_for_review_only": True,
        "operator_phrase_accepted": False,
        "disallowed_actions": list(DISALLOWED_ACTIONS),
        "blockers": packet_blockers,
        "certification_status": certification_status,
        "live_authorized": False,
        "autonomous_submit_authorized": False,
        "paper_submit_authorized": False,
        "paper_entry_authorized": False,
        "paper_exit_authorized": False,
        "paper_fill_authorized": False,
        "broker_action_permitted": False,
        "broker_mutation_authorized_by_this_packet": False,
        "broker_read_performed_current_run": False,
        "broker_mutation_performed_current_run": False,
        "paper_submit_performed_current_run": False,
        "paper_cancel_performed_current_run": False,
        "live_endpoint_touched_current_run": False,
        "live_mutation_performed_current_run": False,
        "credential_values_exposed": False,
        "network_access_attempted": False,
        "profit_claim": "none",
        "labels": list(REQUIRED_LABELS),
        "next_operator_action": _next_operator_action(certification_status),
    }


def _prior_certification_summary(
    result: Mapping[str, object],
    *,
    source_path: Path,
    read_error: str,
) -> dict[str, object]:
    source_sha256 = _file_sha256(source_path) if source_path.is_file() else ""
    outcome = _first_text(result, "outcome_classification")
    client_order_id = _first_text(result, "client_order_id")
    symbol = _normalize_symbol(
        _first_nonempty_text(
            _first_text(result, "symbol"),
            _nested_text(result, "submitted_request", "symbol"),
            _nested_text(result, "final_order", "symbol"),
        )
    )
    final_status = _normalize_status(
        _first_nonempty_text(
            _first_text(result, "final_order_status"),
            _nested_text(result, "reconciliation", "final_order_status"),
            _nested_text(result, "final_order", "status"),
        )
    )
    filled_qty = _decimal_text_or_empty(
        _decimal_or_none(
            _first_nonempty_text(
                _first_text(result, "filled_qty"),
                _nested_text(result, "reconciliation", "filled_qty"),
                _nested_text(result, "final_order", "filled_qty"),
            )
        )
    )
    submitted_qty = _decimal_text_or_empty(
        _decimal_or_none(
            _first_nonempty_text(
                _first_text(result, "submitted_qty"),
                _nested_text(result, "submitted_request", "quantity"),
                _nested_text(result, "submitted_request", "qty"),
                _nested_text(result, "final_order", "qty"),
            )
        )
    )
    estimated_notional = _decimal_text_or_empty(
        _decimal_or_none(
            _first_nonempty_text(
                _first_text(result, "estimated_submit_notional"),
                _nested_text(result, "order_design", "estimated_submit_notional"),
            )
        )
    )
    residual_position = _residual_position_payload(result)
    return {
        "source_path": str(source_path),
        "source_sha256": source_sha256,
        "read_error": read_error,
        "schema_version": _first_text(result, "schema_version"),
        "as_of": _first_text(result, "as_of"),
        "outcome_classification": outcome,
        "submit_attempt_count": _first_text(result, "submit_attempt_count"),
        "cancel_attempt_count": _first_text(result, "cancel_attempt_count"),
        "submit_status": _first_text(result, "submit_status"),
        "cancel_status": _first_text(result, "cancel_status"),
        "final_order_status": final_status,
        "filled_qty": filled_qty,
        "residual_position": residual_position,
        "symbol": symbol,
        "submitted_qty": submitted_qty,
        "estimated_submit_notional": estimated_notional,
        "approved_qty": _first_text(result, "approved_qty"),
        "approved_max_notional": _first_text(result, "approved_max_notional"),
        "client_order_id": client_order_id,
        "expected_account_matched": _is_true(result.get("expected_account_matched")),
        "broker_read_observed": _is_true(result.get("broker_read_observed")),
        "broker_mutation_performed": _is_true(result.get("broker_mutation_performed")),
        "paper_submit_performed": _is_true(result.get("paper_submit_performed")),
        "paper_cancel_performed": _is_true(result.get("paper_cancel_performed")),
        "live_endpoint_touched": _is_true(result.get("live_endpoint_touched")),
        "credential_values_exposed": _is_true(result.get("credential_values_exposed")),
        "prior_certification_id": _prior_certification_id(
            source_sha256=source_sha256,
            client_order_id=client_order_id,
            outcome=outcome,
        ),
    }


def _certification_blockers(
    result: Mapping[str, object],
    *,
    read_error: str,
    prior: Mapping[str, object],
    approved_qty: Decimal,
    max_notional: Decimal,
) -> list[str]:
    blockers: list[str] = []
    if read_error:
        blockers.append(read_error)
        return blockers

    if _text(prior.get("outcome_classification")) != "submitted_cancel_confirmed":
        blockers.append("outcome_classification_not_submitted_cancel_confirmed")
    if _int_or_none(prior.get("submit_attempt_count")) != 1:
        blockers.append("submit_attempt_count_not_1")
    if _int_or_none(prior.get("cancel_attempt_count")) != 1:
        blockers.append("cancel_attempt_count_not_1")
    if _text(prior.get("final_order_status")) != "canceled":
        blockers.append("final_order_status_not_canceled")

    filled_qty = _decimal_or_none(prior.get("filled_qty"))
    if filled_qty is None:
        blockers.append("missing_or_invalid_filled_qty")
    elif filled_qty != Decimal("0"):
        blockers.append("filled_qty_not_zero")

    if _has_residual_position(prior.get("residual_position")):
        blockers.append("residual_position_not_empty")

    if _is_true(result.get("live_endpoint_touched")):
        blockers.append("live_endpoint_touched_true")
    elif not _is_false(result.get("live_endpoint_touched")):
        blockers.append("live_endpoint_touched_not_false")

    if _is_true(result.get("credential_values_exposed")):
        blockers.append("credential_values_exposed_true")
    elif not _is_false(result.get("credential_values_exposed")):
        blockers.append("credential_values_exposed_not_false")

    if _text(prior.get("symbol")) != SYMBOL_BTCUSD:
        blockers.append("symbol_not_BTCUSD")

    submitted_qty = _decimal_or_none(prior.get("submitted_qty"))
    if submitted_qty is None:
        blockers.append("missing_or_invalid_submitted_qty")
    elif submitted_qty > approved_qty:
        blockers.append("submitted_qty_exceeds_approved_qty")

    estimated_notional = _decimal_or_none(prior.get("estimated_submit_notional"))
    if estimated_notional is None:
        blockers.append("missing_or_invalid_estimated_submit_notional")
    elif estimated_notional > max_notional:
        blockers.append("estimated_submit_notional_exceeds_max_notional")

    if not _text(prior.get("client_order_id")):
        blockers.append("missing_client_order_id")
    if not _is_true(result.get("expected_account_matched")):
        blockers.append("expected_account_not_matched")

    return list(_dedupe(blockers))


def _required_operator_phrase(
    *,
    prior_certification_id: str,
    client_order_id: str,
    symbol: str,
    max_notional: str,
) -> str:
    return (
        "Authorized for future v5.10 review: using prior_certification_id "
        f"{prior_certification_id} and prior client_order_id {client_order_id}, "
        f"authorize exactly one bounded {symbol} Alpaca paper entry attempt and "
        "one bounded exit/flatten attempt for the resulting BTCUSD paper "
        f"position, with max notional {max_notional}. This does not authorize "
        "live trading, additional orders, replacement, liquidation/close-all, "
        "capital changes, credential exposure, or paid services."
    )


def _next_operator_action(certification_status: str) -> str:
    if certification_status == CERTIFICATION_STATUS_CERTIFIED_NO_FILL:
        return (
            "operator_review_required_before_any_future_bounded_btcusd_paper_"
            "fill_and_exit_certification"
        )
    return "repair_or_recheck_prior_certification_result_before_future_packet_review"


def _operating_record(ingestion: Mapping[str, object]) -> dict[str, object]:
    packet = _mapping(ingestion.get("paper_fill_experiment_approval_packet"))
    return {
        "record_type": "crypto_paper_certification_ingestion",
        "schema_version": CRYPTO_PAPER_CERTIFICATION_INGESTION_SCHEMA_VERSION,
        "as_of": ingestion.get("as_of", ""),
        "certification_result_source": ingestion.get("certification_result_source", ""),
        "certification_result_sha256": ingestion.get("certification_result_sha256", ""),
        "certification_status": ingestion.get("certification_status", ""),
        "prior_certification_id": ingestion.get("prior_certification_id", ""),
        "prior_client_order_id": ingestion.get("prior_client_order_id", ""),
        "prior_outcome_classification": ingestion.get(
            "prior_outcome_classification",
            "",
        ),
        "prior_final_order_status": ingestion.get("prior_final_order_status", ""),
        "prior_filled_qty": ingestion.get("prior_filled_qty", ""),
        "approval_packet_status": packet.get("approval_packet_status", ""),
        "approval_state": APPROVAL_STATE_NOT_AUTHORIZED,
        "requested_future_authorization_scope": (
            FUTURE_FILL_APPROVAL_PACKET_REQUESTED_SCOPE
        ),
        "blockers": ingestion.get("blockers", []),
        "broker_action_permitted": False,
        "paper_submit_authorized": False,
        "paper_fill_authorized": False,
        "broker_mutation_authorized_by_this_packet": False,
        "broker_read_performed_current_run": False,
        "broker_mutation_performed_current_run": False,
        "paper_submit_performed_current_run": False,
        "live_endpoint_touched_current_run": False,
        "credential_values_exposed": False,
        "network_access_attempted": False,
        "profit_claim": "none",
        "labels": list(REQUIRED_LABELS),
    }


def _read_json_mapping(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {"payload": {}, "error": "certification_result_missing"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"payload": {}, "error": f"certification_result_invalid_json:{exc.msg}"}
    except OSError:
        return {"payload": {}, "error": "certification_result_unreadable"}
    if not isinstance(payload, Mapping):
        return {"payload": {}, "error": "certification_result_not_json_object"}
    return {"payload": payload, "error": ""}


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(_json_safe(payload), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _artifact_entry(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "sha256": _file_sha256(path),
        "size": path.stat().st_size,
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _prior_certification_id(
    *,
    source_sha256: str,
    client_order_id: str,
    outcome: str,
) -> str:
    basis = json.dumps(
        {
            "client_order_id": client_order_id,
            "outcome": outcome,
            "source_sha256": source_sha256,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
    return f"v58_btcusd_submit_cancel_{digest}"


def _residual_position_payload(result: Mapping[str, object]) -> object:
    direct = result.get("residual_position")
    if direct not in (None, ""):
        return _json_safe(direct)
    reconciliation = result.get("reconciliation")
    if isinstance(reconciliation, Mapping):
        nested = reconciliation.get("residual_position")
        if nested not in (None, ""):
            return _json_safe(nested)
    return {}


def _has_residual_position(value: object) -> bool:
    if value in (None, "", (), [], {}):
        return False
    if isinstance(value, Mapping):
        if _is_true(value.get("selected_symbol_position_observed")):
            return True
        positions = value.get("selected_symbol_positions")
        if isinstance(positions, Sequence) and not isinstance(positions, (str, bytes)):
            return bool(positions)
        return bool(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return bool(value)
    return True


def _nested_text(row: Mapping[str, object], *path: str) -> str:
    current: object = row
    for key in path:
        if not isinstance(current, Mapping):
            return ""
        current = current.get(key, "")
    return _text(current)


def _first_text(row: Mapping[str, object], *field_names: str) -> str:
    wanted = {_field_lookup_key(field_name) for field_name in field_names}
    for key, value in row.items():
        if _field_lookup_key(key) in wanted:
            return _text(value)
    return ""


def _first_nonempty_text(*values: str) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _normalize_status(value: object) -> str:
    text = _text(value)
    if not text:
        return ""
    return text.lower().replace(" ", "_")


def _normalize_symbol(value: object) -> str:
    return _text(value).replace("/", "").upper()


def _decimal_value(value: object, field_name: str) -> Decimal:
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a finite Decimal.") from exc
    if not parsed.is_finite():
        raise ValidationError(f"{field_name} must be a finite Decimal.")
    return parsed


def _decimal_or_none(value: object) -> Decimal | None:
    text = _text(value)
    if not text:
        return None
    try:
        parsed = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    if not parsed.is_finite():
        return None
    return parsed


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _decimal_text_or_empty(value: Decimal | None) -> str:
    return "" if value is None else _decimal_text(value)


def _int_or_none(value: object) -> int | None:
    try:
        return int(_text(value))
    except ValueError:
        return None


def _is_true(value: object) -> bool:
    if type(value) is bool:
        return value
    if type(value) is str:
        return value.strip().lower() == "true"
    return False


def _is_false(value: object) -> bool:
    if type(value) is bool:
        return value is False
    if type(value) is str:
        return value.strip().lower() == "false"
    return False


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _mapping(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string_sequence(value: object) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(item) for item in value if str(item).strip())
    if value in (None, ""):
        return ()
    return (str(value),)


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)


def _text(value: object) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "true" if value else "false"
    return str(value).strip()


def _field_lookup_key(value: object) -> str:
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


def _generated_under_runs(path: Path) -> bool:
    return any(str(part).lower() == "runs" for part in path.parts)


def _json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Ingest a local v5.8 BTCUSD paper submit/cancel certification "
            "result and build a no-submit future fill approval packet."
        ),
    )
    parser.add_argument(
        "--certification-result-path",
        type=Path,
        default=CRYPTO_PAPER_CERTIFICATION_INGESTION_DEFAULT_CERTIFICATION_RESULT,
        help="Path to v5.8 certification_result.json.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=CRYPTO_PAPER_CERTIFICATION_INGESTION_DEFAULT_OUTPUT_ROOT,
        help="Output root for ignored ingestion artifacts.",
    )
    parser.add_argument("--approved-qty", default=_decimal_text(APPROVED_QTY))
    parser.add_argument("--max-notional", default=_decimal_text(MAX_NOTIONAL))
    parser.add_argument("--as-of", default="")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    ingestion = run_crypto_paper_certification_ingestion(
        certification_result_path=args.certification_result_path,
        output_root=args.output_root,
        approved_qty=args.approved_qty,
        max_notional=args.max_notional,
        as_of=args.as_of,
        write_artifacts=True,
    )
    if args.format == "json":
        print(json.dumps(_json_safe(ingestion), sort_keys=True))
    else:
        print(render_crypto_paper_certification_ingestion_text(ingestion))
    if ingestion.get("certification_status") == CERTIFICATION_STATUS_CERTIFIED_NO_FILL:
        return 0
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
