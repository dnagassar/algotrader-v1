"""v5.11 BTCUSD paper fill/exit certification-result ingestion.

This module consumes the local v5.10 BTCUSD paper fill/exit certification
artifact and writes durable no-submit certification records. It does not read a
broker, submit orders, cancel orders, close positions, or touch credentials.
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


SCHEMA_VERSION = "v5_11_crypto_paper_fill_exit_ingestion_v1"
COMMAND_NAME = "run_crypto_paper_fill_exit_ingestion"
DEFAULT_FILL_EXIT_CERTIFICATION_RESULT = Path(
    "runs/crypto_paper_fill_exit_certification/latest/"
    "fill_exit_certification_result.json"
)
DEFAULT_OUTPUT_ROOT = Path("runs/crypto_paper_fill_exit_ingestion/latest")

CERTIFICATION_STATUS_CERTIFIED_FILL_EXIT_FLAT = "certified_fill_exit_flat"
CERTIFICATION_STATUS_BLOCKED = "blocked"
CERTIFIED_SCOPE = "BTCUSD bounded paper entry/exit only"
SYMBOL_BTCUSD = "BTCUSD"
MAX_APPROVED_NOTIONAL = Decimal("25")
READ_ONLY_RECONCILIATION_REQUIRED = "flat_reconciliation_required"
READ_ONLY_RECONCILIATION_BLOCKED = "blocked_certification_not_ready"
READ_ONLY_RECONCILIATION_SCOPE = "BTCUSD paper read-only flat reconciliation"
READ_ONLY_RECONCILIATION_RUN_ID = "v511_btcusd_flat_read_only_reconciliation"

REQUIRED_LABELS = (
    "paper_lab_only",
    "signal_evaluation_only",
    "not_live_authorized",
    "profit_claim=none",
    "certification_result_ingestion_only",
    "btcusd_only",
    "fill_exit_certified",
    "flat_reconciliation_required",
    "no_submit_mode",
)

FORBIDDEN_ACTIONS = (
    "submit",
    "cancel",
    "replace",
    "close",
    "liquidate",
    "delete",
    "retry",
    "broker_mutation",
    "paper_submit",
    "live_trading",
    "live_endpoint",
    "credential_exposure",
)

__all__ = [
    "CERTIFICATION_STATUS_BLOCKED",
    "CERTIFICATION_STATUS_CERTIFIED_FILL_EXIT_FLAT",
    "CERTIFIED_SCOPE",
    "COMMAND_NAME",
    "DEFAULT_FILL_EXIT_CERTIFICATION_RESULT",
    "DEFAULT_OUTPUT_ROOT",
    "READ_ONLY_RECONCILIATION_REQUIRED",
    "REQUIRED_LABELS",
    "SCHEMA_VERSION",
    "build_crypto_paper_fill_exit_ingestion",
    "main",
    "render_crypto_paper_fill_exit_ingestion_markdown",
    "render_crypto_paper_fill_exit_ingestion_text",
    "run_crypto_paper_fill_exit_ingestion",
    "write_crypto_paper_fill_exit_ingestion_artifacts",
]


def run_crypto_paper_fill_exit_ingestion(
    *,
    certification_result_path: Path | str = DEFAULT_FILL_EXIT_CERTIFICATION_RESULT,
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
    max_notional: Decimal | str = MAX_APPROVED_NOTIONAL,
    as_of: str = "",
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Read the v5.10 fill/exit result and write v5.11 artifacts."""

    source_path = Path(certification_result_path)
    max_notional_decimal = _decimal_value(max_notional, "max_notional")
    read_result = _read_json_mapping(source_path)
    ingestion = build_crypto_paper_fill_exit_ingestion(
        certification_result=read_result["payload"],
        certification_result_source=source_path,
        certification_result_read_error=_text(read_result["error"]),
        max_notional=max_notional_decimal,
        as_of=as_of,
    )
    if write_artifacts:
        ingestion["artifact_paths"] = write_crypto_paper_fill_exit_ingestion_artifacts(
            output_root,
            ingestion,
        )
    return ingestion


def build_crypto_paper_fill_exit_ingestion(
    *,
    certification_result: Mapping[str, object],
    certification_result_source: Path | str,
    certification_result_read_error: str = "",
    max_notional: Decimal | str = MAX_APPROVED_NOTIONAL,
    as_of: str = "",
) -> dict[str, object]:
    """Build a durable no-submit v5.11 certification record."""

    source_path = Path(certification_result_source)
    max_notional_decimal = _decimal_value(max_notional, "max_notional")
    prior = _prior_fill_exit_summary(
        certification_result,
        source_path=source_path,
        read_error=certification_result_read_error,
    )
    blockers = _certification_blockers(
        certification_result,
        read_error=certification_result_read_error,
        prior=prior,
        max_notional=max_notional_decimal,
    )
    certification_status = (
        CERTIFICATION_STATUS_CERTIFIED_FILL_EXIT_FLAT
        if not blockers
        else CERTIFICATION_STATUS_BLOCKED
    )
    record_as_of = as_of or _text(certification_result.get("as_of"))
    read_only_request = _build_read_only_reconciliation_request(
        certification_status=certification_status,
        blockers=blockers,
        prior=prior,
        as_of=record_as_of,
    )
    labels = list(REQUIRED_LABELS)
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_paper_fill_exit_ingestion",
        "operator_command": COMMAND_NAME,
        "as_of": record_as_of,
        "certification_result_source": str(source_path),
        "certification_result_readable": not certification_result_read_error,
        "certification_result_read_error": certification_result_read_error,
        "certification_result_sha256": prior["source_sha256"],
        "certification_status": certification_status,
        "certified_scope": (
            CERTIFIED_SCOPE
            if certification_status == CERTIFICATION_STATUS_CERTIFIED_FILL_EXIT_FLAT
            else ""
        ),
        "symbol": prior["symbol"],
        "approved_max_notional": prior["approved_max_notional"],
        "approved_max_notional_cap": _decimal_text(max_notional_decimal),
        "blockers": blockers,
        "prior_fill_exit_certification": prior,
        "prior_outcome_classification": prior["outcome_classification"],
        "prior_entry_client_order_id": prior["entry_client_order_id"],
        "prior_exit_client_order_id": prior["exit_client_order_id"],
        "prior_entry_attempt_count": prior["entry_attempt_count"],
        "prior_exit_attempt_count": prior["exit_attempt_count"],
        "prior_entry_final_status": prior["entry_final_status"],
        "prior_exit_final_status": prior["exit_final_status"],
        "prior_entry_filled_qty": prior["entry_filled_qty"],
        "prior_entry_filled_avg_price": prior["entry_filled_avg_price"],
        "prior_position_after_entry": prior["position_after_entry"],
        "prior_exit_filled_qty": prior["exit_filled_qty"],
        "prior_exit_filled_avg_price": prior["exit_filled_avg_price"],
        "prior_final_position": prior["final_position"],
        "prior_residual_position_status": prior["residual_position_status"],
        "prior_broker_read_observed": prior["broker_read_observed"],
        "prior_broker_mutation_performed": prior["broker_mutation_performed"],
        "prior_paper_submit_performed": prior["paper_submit_performed"],
        "prior_live_endpoint_touched": prior["live_endpoint_touched"],
        "prior_credential_values_exposed": prior["credential_values_exposed"],
        "read_only_reconciliation_status": read_only_request[
            "read_only_reconciliation_status"
        ],
        "read_only_reconciliation_request": read_only_request,
        "live_authorized": False,
        "autonomous_submit_authorized": False,
        "broker_mutation_authorized_by_this_packet": False,
        "paper_submit_authorized": False,
        "paper_entry_authorized": False,
        "paper_exit_authorized": False,
        "broker_read_performed_current_run": False,
        "broker_mutation_performed_current_run": False,
        "paper_submit_performed_current_run": False,
        "paper_cancel_performed_current_run": False,
        "paper_replace_performed_current_run": False,
        "paper_close_performed_current_run": False,
        "paper_liquidate_performed_current_run": False,
        "live_endpoint_touched_current_run": False,
        "live_mutation_performed_current_run": False,
        "credential_values_exposed": False,
        "network_access_attempted": False,
        "profit_claim": "none",
        "labels": labels,
        "next_operator_action": _next_operator_action(certification_status),
    }


def write_crypto_paper_fill_exit_ingestion_artifacts(
    output_root: Path | str,
    ingestion: Mapping[str, object],
) -> dict[str, str]:
    """Write ignored runtime artifacts for the v5.11 ingestion."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "fill_exit_ingestion_json": root / "fill_exit_ingestion.json",
        "fill_exit_ingestion_md": root / "fill_exit_ingestion.md",
        "read_only_reconciliation_request_json": (
            root / "read_only_reconciliation_request.json"
        ),
        "operating_record": root / "operating_record.jsonl",
    }
    artifact_paths = {key: str(path) for key, path in paths.items()}
    manifest_path = root / "manifest.json"
    artifact_paths["manifest"] = str(manifest_path)

    ingestion_payload = {**dict(ingestion), "artifact_paths": artifact_paths}
    request = {
        **_mapping(ingestion_payload.get("read_only_reconciliation_request")),
        "artifact_paths": artifact_paths,
    }
    _write_json(paths["fill_exit_ingestion_json"], ingestion_payload)
    paths["fill_exit_ingestion_md"].write_text(
        render_crypto_paper_fill_exit_ingestion_markdown(ingestion_payload) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_json(paths["read_only_reconciliation_request_json"], request)
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
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_paper_fill_exit_ingestion_manifest",
        "as_of": ingestion_payload.get("as_of", ""),
        "artifact_root": str(root),
        "required_artifacts": {
            key: _artifact_entry(path)
            for key, path in sorted(paths.items())
        },
        "manifest": {"path": str(manifest_path)},
        "input_artifacts": {
            "fill_exit_certification_result": {
                "path": _text(ingestion_payload.get("certification_result_source")),
                "sha256": _text(ingestion_payload.get("certification_result_sha256")),
            },
        },
        "certification_status": ingestion_payload.get("certification_status", ""),
        "read_only_reconciliation_status": ingestion_payload.get(
            "read_only_reconciliation_status",
            "",
        ),
        "generated_under_runs": _generated_under_runs(root),
        "live_authorized": False,
        "autonomous_submit_authorized": False,
        "broker_mutation_authorized_by_this_packet": False,
        "paper_submit_authorized": False,
        "broker_read_performed_current_run": False,
        "broker_mutation_performed_current_run": False,
        "paper_submit_performed_current_run": False,
        "live_endpoint_touched_current_run": False,
        "credential_values_exposed": False,
        "network_access_attempted": False,
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
    }
    _write_json(manifest_path, manifest)
    return artifact_paths


def render_crypto_paper_fill_exit_ingestion_markdown(
    ingestion: Mapping[str, object],
) -> str:
    """Render an operator-readable v5.11 certification summary."""

    blockers = list(_string_sequence(ingestion.get("blockers")))
    request = _mapping(ingestion.get("read_only_reconciliation_request"))
    return "\n".join(
        [
            "# Crypto Paper Fill/Exit Ingestion",
            "",
            f"- certification result source: `{ingestion.get('certification_result_source', '')}`",
            f"- certification status: `{ingestion.get('certification_status', '')}`",
            f"- certified scope: `{ingestion.get('certified_scope', '')}`",
            f"- symbol: `{ingestion.get('symbol', '')}`",
            (
                "- prior outcome classification: "
                f"`{ingestion.get('prior_outcome_classification', '')}`"
            ),
            (
                "- prior entry client order id: "
                f"`{ingestion.get('prior_entry_client_order_id', '')}`"
            ),
            (
                "- prior exit client order id: "
                f"`{ingestion.get('prior_exit_client_order_id', '')}`"
            ),
            (
                "- prior entry/exit final statuses: "
                f"`{ingestion.get('prior_entry_final_status', '')}` / "
                f"`{ingestion.get('prior_exit_final_status', '')}`"
            ),
            (
                "- prior residual position status: "
                f"`{ingestion.get('prior_residual_position_status', '')}`"
            ),
            f"- blockers: `{','.join(blockers)}`",
            "",
            "## Safety",
            "",
            "- live authorized: `false`",
            "- autonomous submit authorized: `false`",
            "- broker mutation authorized by this packet: `false`",
            "- broker read performed current run: `false`",
            "- broker mutation performed current run: `false`",
            "- paper submit performed current run: `false`",
            "- live endpoint touched current run: `false`",
            "- credential values exposed: `false`",
            "",
            "## Read-Only Reconciliation",
            "",
            (
                "- request status: "
                f"`{request.get('read_only_reconciliation_status', '')}`"
            ),
            f"- requested scope: `{request.get('requested_scope', '')}`",
            f"- exact operator command: `{request.get('exact_operator_command', '')}`",
            "",
            "Labels: " + ", ".join(_string_sequence(ingestion.get("labels"))),
        ]
    )


def render_crypto_paper_fill_exit_ingestion_text(
    ingestion: Mapping[str, object],
) -> str:
    """Render compact key-value output for the PowerShell wrapper."""

    request = _mapping(ingestion.get("read_only_reconciliation_request"))
    artifacts = _mapping(ingestion.get("artifact_paths"))
    lines = [
        f"crypto_paper_fill_exit_ingestion_command={COMMAND_NAME}",
        "crypto_paper_fill_exit_ingestion_scope=local_v5_10_result_ingestion_only",
        f"certification_status={_text(ingestion.get('certification_status'))}",
        f"certified_scope={_text(ingestion.get('certified_scope'))}",
        f"symbol={_text(ingestion.get('symbol'))}",
        (
            "prior_outcome_classification="
            f"{_text(ingestion.get('prior_outcome_classification'))}"
        ),
        (
            "prior_entry_client_order_id="
            f"{_text(ingestion.get('prior_entry_client_order_id'))}"
        ),
        (
            "prior_exit_client_order_id="
            f"{_text(ingestion.get('prior_exit_client_order_id'))}"
        ),
        (
            "prior_entry_final_status="
            f"{_text(ingestion.get('prior_entry_final_status'))}"
        ),
        (
            "prior_exit_final_status="
            f"{_text(ingestion.get('prior_exit_final_status'))}"
        ),
        (
            "prior_residual_position_status="
            f"{_text(ingestion.get('prior_residual_position_status'))}"
        ),
        f"blockers={','.join(_string_sequence(ingestion.get('blockers')))}",
        (
            "read_only_reconciliation_status="
            f"{_text(ingestion.get('read_only_reconciliation_status'))}"
        ),
        (
            "read_only_reconciliation_exact_operator_command="
            f"{_text(request.get('exact_operator_command'))}"
        ),
        "live_authorized=false",
        "autonomous_submit_authorized=false",
        "broker_mutation_authorized_by_this_packet=false",
        "broker_read_performed_current_run=false",
        "broker_mutation_performed_current_run=false",
        "paper_submit_performed_current_run=false",
        "paper_cancel_performed_current_run=false",
        "paper_replace_performed_current_run=false",
        "paper_close_performed_current_run=false",
        "paper_liquidate_performed_current_run=false",
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
        f"labels={','.join(_string_sequence(ingestion.get('labels')))}",
    ]
    for key in (
        "fill_exit_ingestion_json",
        "fill_exit_ingestion_md",
        "read_only_reconciliation_request_json",
        "operating_record",
        "manifest",
    ):
        if key in artifacts:
            lines.append(f"artifact_{key}={artifacts[key]}")
    return "\n".join(lines)


def _prior_fill_exit_summary(
    result: Mapping[str, object],
    *,
    source_path: Path,
    read_error: str,
) -> dict[str, object]:
    source_sha256 = _file_sha256(source_path) if source_path.is_file() else ""
    entry_order = _mapping(result.get("entry_final_order"))
    exit_order = _mapping(result.get("exit_final_order"))
    return {
        "source_path": str(source_path),
        "source_sha256": source_sha256,
        "read_error": read_error,
        "schema_version": _first_text(result, "schema_version"),
        "as_of": _first_text(result, "as_of"),
        "outcome_classification": _first_text(result, "outcome_classification"),
        "symbol": _normalize_symbol(
            _first_nonempty_text(
                _first_text(result, "symbol"),
                _text(entry_order.get("symbol")),
                _text(exit_order.get("symbol")),
            )
        ),
        "approved_max_notional": _first_text(result, "approved_max_notional"),
        "entry_client_order_id": _first_nonempty_text(
            _first_text(result, "entry_client_order_id"),
            _text(entry_order.get("client_order_id")),
        ),
        "exit_client_order_id": _first_nonempty_text(
            _first_text(result, "exit_client_order_id"),
            _text(exit_order.get("client_order_id")),
        ),
        "entry_attempt_count": _first_text(result, "entry_attempt_count"),
        "exit_attempt_count": _first_text(result, "exit_attempt_count"),
        "entry_final_status": _normalize_status(
            _first_nonempty_text(
                _first_text(result, "entry_final_status"),
                _text(entry_order.get("status")),
            )
        ),
        "exit_final_status": _normalize_status(
            _first_nonempty_text(
                _first_text(result, "exit_final_status"),
                _text(exit_order.get("status")),
            )
        ),
        "entry_filled_qty": _decimal_text_or_empty(
            _decimal_or_none(
                _first_nonempty_text(
                    _first_text(result, "entry_filled_qty"),
                    _text(entry_order.get("filled_qty")),
                )
            )
        ),
        "entry_filled_avg_price": _decimal_text_or_empty(
            _decimal_or_none(
                _first_nonempty_text(
                    _first_text(result, "entry_filled_avg_price"),
                    _text(entry_order.get("filled_avg_price")),
                )
            )
        ),
        "position_after_entry": _json_safe(_mapping(result.get("position_after_entry"))),
        "exit_filled_qty": _decimal_text_or_empty(
            _decimal_or_none(
                _first_nonempty_text(
                    _first_text(result, "exit_filled_qty"),
                    _text(exit_order.get("filled_qty")),
                )
            )
        ),
        "exit_filled_avg_price": _decimal_text_or_empty(
            _decimal_or_none(
                _first_nonempty_text(
                    _first_text(result, "exit_filled_avg_price"),
                    _text(exit_order.get("filled_avg_price")),
                )
            )
        ),
        "final_position": _json_safe(_mapping(result.get("final_position"))),
        "residual_position_status": _first_text(result, "residual_position_status"),
        "broker_read_observed": _is_true(result.get("broker_read_observed")),
        "broker_mutation_performed": _is_true(result.get("broker_mutation_performed")),
        "paper_submit_performed": _is_true(result.get("paper_submit_performed")),
        "live_endpoint_touched": _is_true(result.get("live_endpoint_touched")),
        "credential_values_exposed": _is_true(result.get("credential_values_exposed")),
    }


def _certification_blockers(
    result: Mapping[str, object],
    *,
    read_error: str,
    prior: Mapping[str, object],
    max_notional: Decimal,
) -> list[str]:
    blockers: list[str] = []
    if read_error:
        blockers.append(read_error)
        return blockers

    if _text(prior.get("outcome_classification")) != "filled_exit_confirmed":
        blockers.append("outcome_classification_not_filled_exit_confirmed")
    if _int_or_none(prior.get("entry_attempt_count")) != 1:
        blockers.append("entry_attempt_count_not_1")
    if _int_or_none(prior.get("exit_attempt_count")) != 1:
        blockers.append("exit_attempt_count_not_1")
    if _text(prior.get("entry_final_status")) != "filled":
        blockers.append("entry_final_status_not_filled")
    if _text(prior.get("exit_final_status")) != "filled":
        blockers.append("exit_final_status_not_filled")

    if _text(prior.get("symbol")) != SYMBOL_BTCUSD:
        blockers.append("symbol_not_BTCUSD")

    approved_max = _decimal_or_none(prior.get("approved_max_notional"))
    if approved_max is None:
        blockers.append("missing_or_invalid_approved_max_notional")
    elif approved_max > max_notional:
        blockers.append("approved_max_notional_exceeds_25")

    if _has_residual_btcusd_position(prior.get("final_position")):
        blockers.append("residual_BTCUSD_position_observed")

    residual_status = _text(prior.get("residual_position_status"))
    if not _residual_status_is_flat(residual_status):
        blockers.append("residual_position_status_not_flat_or_no_BTCUSD_position")

    if _is_true(result.get("live_endpoint_touched")):
        blockers.append("live_endpoint_touched_true")
    elif not _is_false(result.get("live_endpoint_touched")):
        blockers.append("live_endpoint_touched_not_false")

    if _is_true(result.get("credential_values_exposed")):
        blockers.append("credential_values_exposed_true")
    elif not _is_false(result.get("credential_values_exposed")):
        blockers.append("credential_values_exposed_not_false")

    return list(_dedupe(blockers))


def _build_read_only_reconciliation_request(
    *,
    certification_status: str,
    blockers: Sequence[str],
    prior: Mapping[str, object],
    as_of: str,
) -> dict[str, object]:
    status = (
        READ_ONLY_RECONCILIATION_REQUIRED
        if certification_status == CERTIFICATION_STATUS_CERTIFIED_FILL_EXIT_FLAT
        else READ_ONLY_RECONCILIATION_BLOCKED
    )
    exact_command = (
        "pwsh -NoProfile -ExecutionPolicy Bypass -File "
        ".\\scripts\\run_crypto_paper_fill_exit_ingestion.ps1 "
        "-CertificationResultPath "
        '"runs\\crypto_paper_fill_exit_certification\\latest\\'
        'fill_exit_certification_result.json" '
        "-OutputRoot "
        '"runs\\crypto_paper_fill_exit_ingestion\\latest" '
        "-Format text"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "btcusd_read_only_flat_reconciliation_request",
        "run_id": READ_ONLY_RECONCILIATION_RUN_ID,
        "as_of": as_of,
        "symbol": SYMBOL_BTCUSD,
        "requested_scope": READ_ONLY_RECONCILIATION_SCOPE,
        "read_only_reconciliation_status": status,
        "certification_status": certification_status,
        "certification_blockers": list(blockers),
        "source_fill_exit_certification_result": prior.get("source_path", ""),
        "source_fill_exit_certification_sha256": prior.get("source_sha256", ""),
        "prior_entry_client_order_id": prior.get("entry_client_order_id", ""),
        "prior_exit_client_order_id": prior.get("exit_client_order_id", ""),
        "required_checks": [
            "expected_paper_account_guard_passes",
            "live_endpoint_absent",
            "no_open_BTCUSD_orders",
            "no_residual_BTCUSD_position",
        ],
        "normal_shell_status": "blocked_until_scoped_paper_shell_credentials_loaded",
        "exact_operator_command": exact_command,
        "paper_shell_credentials_required_for_actual_read": True,
        "credential_values_required": False,
        "credential_values_required_in_artifact": False,
        "credential_values_must_not_be_printed": True,
        "broker_read_performed_current_run": False,
        "broker_mutation_performed_current_run": False,
        "paper_submit_performed_current_run": False,
        "paper_cancel_performed_current_run": False,
        "paper_replace_performed_current_run": False,
        "paper_close_performed_current_run": False,
        "paper_liquidate_performed_current_run": False,
        "live_endpoint_touched_current_run": False,
        "network_access_attempted": False,
        "live_authorized": False,
        "autonomous_submit_authorized": False,
        "broker_read_authorized_by_this_packet": False,
        "broker_mutation_authorized_by_this_packet": False,
        "paper_submit_authorized": False,
        "paper_entry_authorized": False,
        "paper_exit_authorized": False,
        "no_submit_mode": True,
        "forbidden_actions": list(FORBIDDEN_ACTIONS),
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        "next_operator_action": (
            "operator_may_run_separate_scoped_read_only_btcusd_flat_reconciliation"
            if status == READ_ONLY_RECONCILIATION_REQUIRED
            else "repair_fill_exit_ingestion_blockers_before_read_only_reconciliation"
        ),
    }


def _next_operator_action(certification_status: str) -> str:
    if certification_status == CERTIFICATION_STATUS_CERTIFIED_FILL_EXIT_FLAT:
        return "run_or_attach_scoped_read_only_btcusd_flat_reconciliation"
    return "repair_v5_10_fill_exit_certification_artifact_before_reconciliation"


def _operating_record(ingestion: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_paper_fill_exit_ingestion",
        "review_state": (
            "ready_for_operator_review"
            if ingestion.get("certification_status")
            == CERTIFICATION_STATUS_CERTIFIED_FILL_EXIT_FLAT
            else "blocked"
        ),
        "cycle_decision": "flat_reconciliation_request",
        "as_of": ingestion.get("as_of", ""),
        "symbol": SYMBOL_BTCUSD,
        "certification_result_source": ingestion.get("certification_result_source", ""),
        "certification_result_sha256": ingestion.get(
            "certification_result_sha256",
            "",
        ),
        "certification_status": ingestion.get("certification_status", ""),
        "certified_scope": ingestion.get("certified_scope", ""),
        "prior_outcome_classification": ingestion.get(
            "prior_outcome_classification",
            "",
        ),
        "prior_entry_client_order_id": ingestion.get(
            "prior_entry_client_order_id",
            "",
        ),
        "prior_exit_client_order_id": ingestion.get("prior_exit_client_order_id", ""),
        "prior_entry_final_status": ingestion.get("prior_entry_final_status", ""),
        "prior_exit_final_status": ingestion.get("prior_exit_final_status", ""),
        "prior_residual_position_status": ingestion.get(
            "prior_residual_position_status",
            "",
        ),
        "read_only_reconciliation_status": ingestion.get(
            "read_only_reconciliation_status",
            "",
        ),
        "blockers": ingestion.get("blockers", []),
        "broker_read_performed_current_run": False,
        "broker_mutation_performed_current_run": False,
        "paper_submit_performed_current_run": False,
        "live_endpoint_touched_current_run": False,
        "credential_values_exposed": False,
        "network_access_attempted": False,
        "live_authorized": False,
        "paper_submit_authorized": False,
        "broker_mutation_authorized_by_this_packet": False,
        "profit_claim": "none",
        "labels": list(REQUIRED_LABELS),
    }


def _read_json_mapping(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {"payload": {}, "error": "fill_exit_certification_result_missing"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "payload": {},
            "error": f"fill_exit_certification_result_invalid_json:{exc.msg}",
        }
    except OSError:
        return {"payload": {}, "error": "fill_exit_certification_result_unreadable"}
    if not isinstance(payload, Mapping):
        return {"payload": {}, "error": "fill_exit_certification_result_not_json_object"}
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


def _has_residual_btcusd_position(value: object) -> bool:
    if value in (None, "", (), [], {}):
        return False
    if isinstance(value, Mapping):
        symbol = _normalize_symbol(value.get("symbol"))
        if symbol and symbol != SYMBOL_BTCUSD:
            return False
        qty = _decimal_or_none(
            _first_nonempty_text(
                _text(value.get("qty")),
                _text(value.get("quantity")),
                _text(value.get("position_qty")),
            )
        )
        if qty is None:
            return bool(value)
        side = _normalize_status(value.get("side"))
        signed_qty = -qty if side == "short" and qty > Decimal("0") else qty
        return signed_qty != Decimal("0")
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_has_residual_btcusd_position(item) for item in value)
    return True


def _residual_status_is_flat(value: str) -> bool:
    normalized = value.strip().lower()
    return bool(
        normalized
        and "flat" in normalized
        and ("no_btcusd" in normalized or "no btcusd" in normalized)
    )


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


def _json_safe(value: Any) -> Any:
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
            "Ingest a local v5.10 BTCUSD paper fill/exit certification result "
            "and build a no-submit v5.11 certification record."
        ),
    )
    parser.add_argument(
        "--certification-result-path",
        type=Path,
        default=DEFAULT_FILL_EXIT_CERTIFICATION_RESULT,
        help="Path to v5.10 fill_exit_certification_result.json.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Output root for ignored ingestion artifacts.",
    )
    parser.add_argument("--max-notional", default=_decimal_text(MAX_APPROVED_NOTIONAL))
    parser.add_argument("--as-of", default="")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    ingestion = run_crypto_paper_fill_exit_ingestion(
        certification_result_path=args.certification_result_path,
        output_root=args.output_root,
        max_notional=args.max_notional,
        as_of=args.as_of,
        write_artifacts=True,
    )
    if args.format == "json":
        print(json.dumps(_json_safe(ingestion), sort_keys=True))
    else:
        print(render_crypto_paper_fill_exit_ingestion_text(ingestion))
    if (
        ingestion.get("certification_status")
        == CERTIFICATION_STATUS_CERTIFIED_FILL_EXIT_FLAT
    ):
        return 0
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
