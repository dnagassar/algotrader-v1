"""v5.12 supervised crypto paper autonomy cadence controller.

This controller only reads local JSON artifacts and writes a no-submit
operating packet. It does not import broker SDKs, read a broker, or mutate
orders.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "v5_12_crypto_paper_autonomy_cadence_v1"
COMMAND_NAME = "run_crypto_paper_autonomy_cadence"
DEFAULT_OUTPUT_ROOT = Path("runs/crypto_paper_autonomy_cadence/latest")
DEFAULT_SUBMIT_CANCEL_RESULT = Path(
    "runs/crypto_paper_submit_cancel_certification/latest/certification_result.json"
)
DEFAULT_CERTIFICATION_INGESTION = Path(
    "runs/crypto_paper_certification_ingestion/latest/certification_ingestion.json"
)
DEFAULT_FILL_EXIT_RESULT = Path(
    "runs/crypto_paper_fill_exit_certification/latest/"
    "fill_exit_certification_result.json"
)
DEFAULT_FILL_EXIT_INGESTION = Path(
    "runs/crypto_paper_fill_exit_ingestion/latest/fill_exit_ingestion.json"
)
DEFAULT_ROUTER_DECISION = Path(
    "runs/opportunity_router/paper_read_repair_latest/router_decision.json"
)
DEFAULT_SIZING_PREVIEW = Path("runs/crypto_qty_sizing_preview/latest/sizing_preview.json")
DEFAULT_HANDOFF = Path("runs/crypto_paper_oms_handoff/latest/paper_oms_handoff.json")
DEFAULT_DRY_RUN = Path("runs/crypto_paper_oms_dry_run/latest/paper_oms_dry_run.json")

NEXT_ACTIONS = (
    "refresh_data_and_rerun_router",
    "operator_review_required",
    "approval_packet_required",
    "paper_read_reconciliation_required",
    "blocked",
    "no_trade",
)

REQUIRED_LABELS = (
    "crypto_paper_autonomy_cadence",
    "paper_lab_only",
    "no_submit",
    "no_broker_mutation",
    "not_live_authorized",
    "fresh_authorization_required_for_order",
    "profit_claim=none",
)

FALSE_AUTHORIZATION_FIELDS = (
    "paper_submit_authorized",
    "broker_mutation_authorized",
    "live_authorized",
    "broker_read_occurred",
    "broker_mutation_occurred",
    "paper_submit_occurred",
    "paper_cancel_occurred",
    "paper_replace_occurred",
    "paper_close_occurred",
    "paper_liquidate_occurred",
    "live_endpoint_touched",
    "credential_values_exposed",
    "network_access_attempted",
)

__all__ = [
    "COMMAND_NAME",
    "DEFAULT_CERTIFICATION_INGESTION",
    "DEFAULT_DRY_RUN",
    "DEFAULT_FILL_EXIT_INGESTION",
    "DEFAULT_FILL_EXIT_RESULT",
    "DEFAULT_HANDOFF",
    "DEFAULT_OUTPUT_ROOT",
    "DEFAULT_ROUTER_DECISION",
    "DEFAULT_SIZING_PREVIEW",
    "DEFAULT_SUBMIT_CANCEL_RESULT",
    "FALSE_AUTHORIZATION_FIELDS",
    "NEXT_ACTIONS",
    "REQUIRED_LABELS",
    "SCHEMA_VERSION",
    "build_crypto_paper_autonomy_cadence",
    "main",
    "render_autonomy_cadence_brief_markdown",
    "render_autonomy_cadence_text",
    "run_crypto_paper_autonomy_cadence",
    "write_crypto_paper_autonomy_cadence_artifacts",
]


def run_crypto_paper_autonomy_cadence(
    *,
    submit_cancel_result_path: Path | str = DEFAULT_SUBMIT_CANCEL_RESULT,
    certification_ingestion_path: Path | str = DEFAULT_CERTIFICATION_INGESTION,
    fill_exit_result_path: Path | str = DEFAULT_FILL_EXIT_RESULT,
    fill_exit_ingestion_path: Path | str = DEFAULT_FILL_EXIT_INGESTION,
    router_decision_path: Path | str = DEFAULT_ROUTER_DECISION,
    sizing_preview_path: Path | str = DEFAULT_SIZING_PREVIEW,
    handoff_path: Path | str = DEFAULT_HANDOFF,
    dry_run_path: Path | str = DEFAULT_DRY_RUN,
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
    as_of: str = "",
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Build and optionally write the no-submit autonomy cadence packet."""

    paths = {
        "submit_cancel_result": Path(submit_cancel_result_path),
        "certification_ingestion": Path(certification_ingestion_path),
        "fill_exit_result": Path(fill_exit_result_path),
        "fill_exit_ingestion": Path(fill_exit_ingestion_path),
        "router_decision": Path(router_decision_path),
        "sizing_preview": Path(sizing_preview_path),
        "paper_oms_handoff": Path(handoff_path),
        "paper_oms_dry_run": Path(dry_run_path),
    }
    artifacts = {
        name: _read_json_mapping(path, name) for name, path in paths.items()
    }
    cadence = build_crypto_paper_autonomy_cadence(
        artifacts={name: _mapping(read_result["payload"]) for name, read_result in artifacts.items()},
        sources={
            name: _source_record(
                path=paths[name],
                read_error=_text(read_result["error"]),
            )
            for name, read_result in artifacts.items()
        },
        as_of=as_of,
    )
    if write_artifacts:
        cadence["artifact_paths"] = write_crypto_paper_autonomy_cadence_artifacts(
            output_root,
            cadence,
        )
    return cadence


def build_crypto_paper_autonomy_cadence(
    *,
    artifacts: Mapping[str, Mapping[str, object]],
    sources: Mapping[str, Mapping[str, object]],
    as_of: str = "",
) -> dict[str, object]:
    """Build a primitive-only cadence decision from local upstream artifacts."""

    submit_cancel_result = _mapping(artifacts.get("submit_cancel_result"))
    certification_ingestion = _mapping(artifacts.get("certification_ingestion"))
    fill_exit_result = _mapping(artifacts.get("fill_exit_result"))
    fill_exit_ingestion = _mapping(artifacts.get("fill_exit_ingestion"))
    router_decision = _mapping(artifacts.get("router_decision"))
    sizing_preview = _mapping(artifacts.get("sizing_preview"))
    handoff = _mapping(artifacts.get("paper_oms_handoff"))
    dry_run = _mapping(artifacts.get("paper_oms_dry_run"))

    normalized_sources = {
        key: _mapping(value) for key, value in sources.items()
    }
    lifecycle_evidence = _paper_lifecycle_evidence(
        submit_cancel_result=submit_cancel_result,
        certification_ingestion=certification_ingestion,
        fill_exit_result=fill_exit_result,
        fill_exit_ingestion=fill_exit_ingestion,
        sources=normalized_sources,
    )
    candidate_evidence = _candidate_evidence(
        router_decision=router_decision,
        sizing_preview=sizing_preview,
        handoff=handoff,
        dry_run=dry_run,
        sources=normalized_sources,
    )
    blockers = list(
        _dedupe(
            [
                *_string_sequence(lifecycle_evidence.get("blockers")),
                *_string_sequence(candidate_evidence.get("blockers")),
            ]
        )
    )
    next_action = _classify_next_action(
        lifecycle_evidence=lifecycle_evidence,
        candidate_evidence=candidate_evidence,
    )
    status = _cadence_status(next_action=next_action, blockers=blockers)
    labels = list(REQUIRED_LABELS)
    selected_candidate_id = _text(candidate_evidence.get("selected_candidate_id"))
    action_if_authorized = _action_if_authorized(
        lifecycle_certified=_is_true(lifecycle_evidence.get("lifecycle_certified")),
        current_candidate_eligible=_is_true(
            candidate_evidence.get("current_candidate_eligible")
        ),
        selected_candidate_id=selected_candidate_id,
    )
    decision_as_of = _first_nonempty(
        as_of,
        _text(dry_run.get("as_of")),
        _text(handoff.get("as_of")),
        _text(sizing_preview.get("as_of")),
        _text(router_decision.get("as_of")),
        _text(fill_exit_ingestion.get("as_of")),
        _text(fill_exit_result.get("as_of")),
        _text(certification_ingestion.get("as_of")),
        _text(submit_cancel_result.get("as_of")),
    )
    authorization = _authorization_state()
    next_operator_action = _next_operator_action_payload(
        next_action=next_action,
        status=status,
        blockers=blockers,
        action_if_authorized=action_if_authorized,
        selected_candidate_id=selected_candidate_id,
    )
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_paper_autonomy_cadence",
        "operator_command": COMMAND_NAME,
        "as_of": decision_as_of,
        "cadence_status": status,
        "next_action": next_action,
        "next_operator_action": next_operator_action,
        "paper_lifecycle_evidence": lifecycle_evidence,
        "candidate_evidence": candidate_evidence,
        "lifecycle_certified": lifecycle_evidence["lifecycle_certified"],
        "submit_cancel_certified": lifecycle_evidence["submit_cancel_certified"],
        "fill_exit_certified": lifecycle_evidence["fill_exit_certified"],
        "final_flat_observed": lifecycle_evidence["final_flat_observed"],
        "current_router_candidate_eligible": candidate_evidence[
            "router_candidate_eligible"
        ],
        "current_candidate_eligible": candidate_evidence[
            "current_candidate_eligible"
        ],
        "selected_candidate_id": selected_candidate_id,
        "paper_submit_currently_authorized": False,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "no_submit_mode": True,
        "broker_action_permitted": False,
        "authorization": authorization,
        "prior_v5_8_authorization_status": authorization[
            "prior_v5_8_authorization_status"
        ],
        "prior_v5_10_authorization_status": authorization[
            "prior_v5_10_authorization_status"
        ],
        "prior_authorizations_reusable": False,
        "fresh_authorization_required_for_order": True,
        "would_do_next_if_authorization_granted": action_if_authorized,
        "blockers": blockers,
        "input_artifacts": normalized_sources,
        "labels": labels,
        "profit_claim": "none",
        **_false_flags(),
    }
    return payload


def write_crypto_paper_autonomy_cadence_artifacts(
    output_root: Path | str,
    cadence: Mapping[str, object],
) -> dict[str, str]:
    """Write the no-submit cadence operating packet under the output root."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "autonomy_cadence_brief": root / "autonomy_cadence_brief.md",
        "autonomy_cadence_status": root / "autonomy_cadence_status.json",
        "paper_lifecycle_evidence": root / "paper_lifecycle_evidence.json",
        "next_operator_action": root / "next_operator_action.json",
        "operating_record": root / "operating_record.jsonl",
    }
    manifest_path = root / "manifest.json"
    artifact_paths = {key: str(path) for key, path in paths.items()}
    artifact_paths["manifest"] = str(manifest_path)

    cadence_payload = {**dict(cadence), "artifact_paths": artifact_paths}
    lifecycle_evidence = {
        **_mapping(cadence.get("paper_lifecycle_evidence")),
        "artifact_paths": artifact_paths,
    }
    next_operator_action = {
        **_mapping(cadence.get("next_operator_action")),
        "artifact_paths": artifact_paths,
    }
    _write_json(paths["autonomy_cadence_status"], cadence_payload)
    paths["autonomy_cadence_brief"].write_text(
        render_autonomy_cadence_brief_markdown(cadence_payload) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_json(paths["paper_lifecycle_evidence"], lifecycle_evidence)
    _write_json(paths["next_operator_action"], next_operator_action)
    paths["operating_record"].write_text(
        json.dumps(
            _json_safe(_operating_record(cadence_payload)),
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_paper_autonomy_cadence_manifest",
        "as_of": cadence.get("as_of", ""),
        "artifact_root": str(root),
        "required_artifacts": {
            key: _artifact_entry(path) for key, path in sorted(paths.items())
        },
        "manifest": {"path": str(manifest_path)},
        "input_artifacts": cadence.get("input_artifacts", {}),
        "cadence_status": cadence.get("cadence_status", ""),
        "next_action": cadence.get("next_action", ""),
        "lifecycle_certified": cadence.get("lifecycle_certified") is True,
        "current_candidate_eligible": cadence.get("current_candidate_eligible") is True,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "generated_under_runs": _generated_under_runs(root),
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }
    _write_json(manifest_path, manifest)
    return artifact_paths


def render_autonomy_cadence_brief_markdown(cadence: Mapping[str, object]) -> str:
    """Render the operator-facing cadence brief."""

    lifecycle = _mapping(cadence.get("paper_lifecycle_evidence"))
    candidate = _mapping(cadence.get("candidate_evidence"))
    next_operator_action = _mapping(cadence.get("next_operator_action"))
    blockers = list(_string_sequence(cadence.get("blockers")))
    learned = list(_string_sequence(lifecycle.get("evidence_learned")))
    return "\n".join(
        [
            "# Crypto Paper Autonomy Cadence",
            "",
            f"- cadence status: `{cadence.get('cadence_status', '')}`",
            f"- next action: `{cadence.get('next_action', '')}`",
            f"- lifecycle certified: `{_bool_text(cadence.get('lifecycle_certified'))}`",
            (
                "- current router candidate eligible: "
                f"`{_bool_text(cadence.get('current_router_candidate_eligible'))}`"
            ),
            (
                "- current candidate eligible: "
                f"`{_bool_text(cadence.get('current_candidate_eligible'))}`"
            ),
            "- paper submit currently authorized: `false`",
            "- broker mutation authorized: `false`",
            "- live authorized: `false`",
            (
                "- if fresh authorization were granted: "
                f"`{cadence.get('would_do_next_if_authorization_granted', '')}`"
            ),
            f"- blockers: `{', '.join(blockers) if blockers else 'none'}`",
            "",
            "## Lifecycle Evidence",
            "",
            f"- submit/cancel certified: `{_bool_text(lifecycle.get('submit_cancel_certified'))}`",
            f"- fill/exit certified: `{_bool_text(lifecycle.get('fill_exit_certified'))}`",
            f"- final flat observed: `{_bool_text(lifecycle.get('final_flat_observed'))}`",
            f"- v5.8 authorization: `{cadence.get('prior_v5_8_authorization_status', '')}`",
            f"- v5.10 authorization: `{cadence.get('prior_v5_10_authorization_status', '')}`",
            "",
            "## Current Candidate",
            "",
            f"- selected candidate: `{candidate.get('selected_candidate_id', '')}`",
            f"- router decision: `{candidate.get('router_decision', '')}`",
            f"- sizing status: `{candidate.get('sizing_status', '')}`",
            f"- handoff status: `{candidate.get('handoff_status', '')}`",
            f"- dry-run status: `{candidate.get('dry_run_status', '')}`",
            "",
            "## Evidence Learned",
            "",
            ", ".join(learned) if learned else "none",
            "",
            "## Next Operator Action",
            "",
            f"- action: `{next_operator_action.get('action', '')}`",
            f"- reason: `{next_operator_action.get('reason', '')}`",
            "",
            "Labels: " + ", ".join(_string_sequence(cadence.get("labels"))),
        ]
    )


def render_autonomy_cadence_text(cadence: Mapping[str, object]) -> str:
    """Render compact key-value output for the PowerShell wrapper."""

    artifacts = _mapping(cadence.get("artifact_paths"))
    lines = [
        f"crypto_paper_autonomy_cadence_command={COMMAND_NAME}",
        f"cadence_status={_text(cadence.get('cadence_status'))}",
        f"next_action={_text(cadence.get('next_action'))}",
        f"lifecycle_certified={_bool_text(cadence.get('lifecycle_certified'))}",
        (
            "current_router_candidate_eligible="
            f"{_bool_text(cadence.get('current_router_candidate_eligible'))}"
        ),
        (
            "current_candidate_eligible="
            f"{_bool_text(cadence.get('current_candidate_eligible'))}"
        ),
        "paper_submit_authorized=false",
        "broker_mutation_authorized=false",
        "live_authorized=false",
        "prior_v5_8_authorization_status="
        + _text(cadence.get("prior_v5_8_authorization_status")),
        "prior_v5_10_authorization_status="
        + _text(cadence.get("prior_v5_10_authorization_status")),
        "fresh_authorization_required_for_order=true",
        "blockers=" + ",".join(_string_sequence(cadence.get("blockers"))),
        "labels=" + ",".join(_string_sequence(cadence.get("labels"))),
    ]
    for key in (
        "autonomy_cadence_brief",
        "autonomy_cadence_status",
        "paper_lifecycle_evidence",
        "next_operator_action",
        "operating_record",
        "manifest",
    ):
        value = _text(artifacts.get(key))
        if value:
            lines.append(f"artifact_{key}={value}")
    return "\n".join(lines)


def _paper_lifecycle_evidence(
    *,
    submit_cancel_result: Mapping[str, object],
    certification_ingestion: Mapping[str, object],
    fill_exit_result: Mapping[str, object],
    fill_exit_ingestion: Mapping[str, object],
    sources: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    submit_cancel = _submit_cancel_summary(
        submit_cancel_result,
        _mapping(sources.get("submit_cancel_result")),
    )
    certification_ingestion_summary = _certification_ingestion_summary(
        certification_ingestion,
        _mapping(sources.get("certification_ingestion")),
    )
    fill_exit = _fill_exit_summary(
        fill_exit_result,
        _mapping(sources.get("fill_exit_result")),
    )
    fill_exit_ingestion_summary = _fill_exit_ingestion_summary(
        fill_exit_ingestion,
        _mapping(sources.get("fill_exit_ingestion")),
    )

    blockers: list[str] = []
    if not _is_true(submit_cancel["certified"]):
        blockers.extend(_string_sequence(submit_cancel.get("blockers")))
    if not _is_true(certification_ingestion_summary["certified"]):
        blockers.extend(_string_sequence(certification_ingestion_summary.get("blockers")))
    if not _is_true(fill_exit["certified"]):
        blockers.extend(_string_sequence(fill_exit.get("blockers")))
    if not _is_true(fill_exit_ingestion_summary["certified"]):
        blockers.extend(_string_sequence(fill_exit_ingestion_summary.get("blockers")))

    final_flat_observed = (
        _is_true(fill_exit.get("final_flat_observed"))
        or _is_true(fill_exit_ingestion_summary.get("final_flat_observed"))
    )
    if not final_flat_observed:
        blockers.append("final_flat_not_observed_from_v5_10_or_v5_11_artifact")

    blockers = list(_dedupe(blockers))
    submit_cancel_certified = (
        _is_true(submit_cancel.get("certified"))
        and _is_true(certification_ingestion_summary.get("certified"))
    )
    fill_exit_certified = (
        _is_true(fill_exit.get("certified"))
        and _is_true(fill_exit_ingestion_summary.get("certified"))
    )
    lifecycle_certified = (
        submit_cancel_certified and fill_exit_certified and final_flat_observed
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "paper_lifecycle_evidence",
        "lifecycle_certified": lifecycle_certified,
        "submit_cancel_certified": submit_cancel_certified,
        "fill_exit_certified": fill_exit_certified,
        "final_flat_observed": final_flat_observed,
        "submit_cancel_evidence": submit_cancel,
        "certification_ingestion_evidence": certification_ingestion_summary,
        "fill_exit_evidence": fill_exit,
        "fill_exit_ingestion_evidence": fill_exit_ingestion_summary,
        "prior_v5_8_authorization_status": "consumed_not_reusable",
        "prior_v5_10_authorization_status": "consumed_not_reusable",
        "prior_authorizations_reusable": False,
        "fresh_authorization_required_for_order": True,
        "evidence_learned": [
            "v5_8_submit_cancel_certified_one_bounded_BTCUSD_paper_attempt_when_present",
            "v5_10_fill_exit_certified_one_bounded_BTCUSD_entry_exit_when_present",
            "v5_10_or_v5_11_final_flat_observed_from_certification_artifact_when_present",
            "prior_operator_authorizations_are_consumed_and_not_reusable",
        ],
        "blockers": blockers,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }


def _submit_cancel_summary(
    payload: Mapping[str, object],
    source: Mapping[str, object],
) -> dict[str, object]:
    blockers: list[str] = []
    read_error = _text(source.get("read_error"))
    if read_error:
        blockers.append(read_error)
    outcome = _first_text(payload, "outcome_classification")
    final_status = _normalize_status(
        _first_nonempty(
            _first_text(payload, "final_order_status"),
            _nested_text(payload, "reconciliation", "final_order_status"),
            _nested_text(payload, "final_order", "status"),
        )
    )
    filled_qty = _first_nonempty(
        _first_text(payload, "filled_qty"),
        _nested_text(payload, "reconciliation", "filled_qty"),
        _nested_text(payload, "final_order", "filled_qty"),
    )
    residual = _residual_position(payload)
    symbol = _normalize_symbol(
        _first_nonempty(
            _first_text(payload, "symbol"),
            _nested_text(payload, "submitted_request", "symbol"),
            _nested_text(payload, "final_order", "symbol"),
        )
    )
    if not read_error:
        if outcome != "submitted_cancel_confirmed":
            blockers.append("v5_8_outcome_not_submitted_cancel_confirmed")
        if _int_or_none(_first_text(payload, "submit_attempt_count")) != 1:
            blockers.append("v5_8_submit_attempt_count_not_1")
        if _int_or_none(_first_text(payload, "cancel_attempt_count")) != 1:
            blockers.append("v5_8_cancel_attempt_count_not_1")
        if final_status != "canceled":
            blockers.append("v5_8_final_order_status_not_canceled")
        if not _decimal_zero(filled_qty):
            blockers.append("v5_8_filled_qty_not_zero")
        if _has_residual_position(residual):
            blockers.append("v5_8_residual_position_not_empty")
        if symbol != "BTCUSD":
            blockers.append("v5_8_symbol_not_BTCUSD")
        if _is_true(payload.get("live_endpoint_touched")):
            blockers.append("v5_8_live_endpoint_touched_true")
        if _is_true(payload.get("credential_values_exposed")):
            blockers.append("v5_8_credential_values_exposed_true")
    return {
        "source": dict(source),
        "certified": not blockers,
        "outcome_classification": outcome,
        "symbol": symbol,
        "client_order_id": _first_text(payload, "client_order_id"),
        "final_order_status": final_status,
        "filled_qty": _text(filled_qty),
        "residual_position": _json_safe(residual),
        "broker_read_observed": _is_true(payload.get("broker_read_observed")),
        "broker_mutation_performed": _is_true(payload.get("broker_mutation_performed")),
        "paper_submit_performed": _is_true(payload.get("paper_submit_performed")),
        "paper_cancel_performed": _is_true(payload.get("paper_cancel_performed")),
        "live_endpoint_touched": _is_true(payload.get("live_endpoint_touched")),
        "credential_values_exposed": _is_true(payload.get("credential_values_exposed")),
        "blockers": list(_dedupe(blockers)),
    }


def _certification_ingestion_summary(
    payload: Mapping[str, object],
    source: Mapping[str, object],
) -> dict[str, object]:
    blockers: list[str] = []
    read_error = _text(source.get("read_error"))
    status = _first_text(payload, "certification_status")
    if read_error:
        blockers.append(read_error)
    elif status != "certified_submit_cancel_no_fill":
        blockers.append("v5_9_certification_status_not_certified_submit_cancel_no_fill")
    if _is_true(payload.get("paper_submit_authorized")):
        blockers.append("v5_9_paper_submit_authorized_true")
    if _is_true(payload.get("broker_mutation_authorized_by_this_packet")):
        blockers.append("v5_9_broker_mutation_authorized_true")
    return {
        "source": dict(source),
        "certified": not blockers,
        "certification_status": status,
        "prior_certification_id": _first_text(payload, "prior_certification_id"),
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "blockers": list(_dedupe(blockers)),
    }


def _fill_exit_summary(
    payload: Mapping[str, object],
    source: Mapping[str, object],
) -> dict[str, object]:
    blockers: list[str] = []
    read_error = _text(source.get("read_error"))
    entry_order = _mapping(payload.get("entry_final_order"))
    exit_order = _mapping(payload.get("exit_final_order"))
    outcome = _first_text(payload, "outcome_classification")
    symbol = _normalize_symbol(
        _first_nonempty(
            _first_text(payload, "symbol"),
            _text(entry_order.get("symbol")),
            _text(exit_order.get("symbol")),
        )
    )
    entry_status = _normalize_status(
        _first_nonempty(_first_text(payload, "entry_final_status"), _text(entry_order.get("status")))
    )
    exit_status = _normalize_status(
        _first_nonempty(_first_text(payload, "exit_final_status"), _text(exit_order.get("status")))
    )
    residual_status = _first_text(payload, "residual_position_status")
    final_position = payload.get("final_position")
    final_flat_observed = (
        False
        if read_error
        else _residual_status_is_flat(residual_status)
        or not _has_residual_position(final_position)
    )
    if read_error:
        blockers.append(read_error)
    else:
        if outcome != "filled_exit_confirmed":
            blockers.append("v5_10_outcome_not_filled_exit_confirmed")
        if _int_or_none(_first_text(payload, "entry_attempt_count")) != 1:
            blockers.append("v5_10_entry_attempt_count_not_1")
        if _int_or_none(_first_text(payload, "exit_attempt_count")) != 1:
            blockers.append("v5_10_exit_attempt_count_not_1")
        if entry_status != "filled":
            blockers.append("v5_10_entry_final_status_not_filled")
        if exit_status != "filled":
            blockers.append("v5_10_exit_final_status_not_filled")
        if symbol != "BTCUSD":
            blockers.append("v5_10_symbol_not_BTCUSD")
        if not final_flat_observed:
            blockers.append("v5_10_final_flat_not_observed")
        if _is_true(payload.get("live_endpoint_touched")):
            blockers.append("v5_10_live_endpoint_touched_true")
        if _is_true(payload.get("credential_values_exposed")):
            blockers.append("v5_10_credential_values_exposed_true")
    return {
        "source": dict(source),
        "certified": not blockers,
        "outcome_classification": outcome,
        "symbol": symbol,
        "entry_client_order_id": _first_text(payload, "entry_client_order_id"),
        "exit_client_order_id": _first_text(payload, "exit_client_order_id"),
        "entry_final_status": entry_status,
        "exit_final_status": exit_status,
        "residual_position_status": residual_status,
        "final_flat_observed": final_flat_observed,
        "broker_read_observed": _is_true(payload.get("broker_read_observed")),
        "broker_mutation_performed": _is_true(payload.get("broker_mutation_performed")),
        "paper_submit_performed": _is_true(payload.get("paper_submit_performed")),
        "live_endpoint_touched": _is_true(payload.get("live_endpoint_touched")),
        "credential_values_exposed": _is_true(payload.get("credential_values_exposed")),
        "blockers": list(_dedupe(blockers)),
    }


def _fill_exit_ingestion_summary(
    payload: Mapping[str, object],
    source: Mapping[str, object],
) -> dict[str, object]:
    blockers: list[str] = []
    read_error = _text(source.get("read_error"))
    status = _first_text(payload, "certification_status")
    residual_status = _first_text(payload, "prior_residual_position_status")
    final_flat_observed = _residual_status_is_flat(residual_status)
    if read_error:
        blockers.append(read_error)
    else:
        if status != "certified_fill_exit_flat":
            blockers.append("v5_11_certification_status_not_certified_fill_exit_flat")
        if not final_flat_observed:
            blockers.append("v5_11_final_flat_not_observed")
    if _is_true(payload.get("paper_submit_authorized")):
        blockers.append("v5_11_paper_submit_authorized_true")
    if _is_true(payload.get("broker_mutation_authorized_by_this_packet")):
        blockers.append("v5_11_broker_mutation_authorized_true")
    return {
        "source": dict(source),
        "certified": not blockers,
        "certification_status": status,
        "prior_entry_client_order_id": _first_text(payload, "prior_entry_client_order_id"),
        "prior_exit_client_order_id": _first_text(payload, "prior_exit_client_order_id"),
        "prior_residual_position_status": residual_status,
        "final_flat_observed": final_flat_observed,
        "read_only_reconciliation_status": _first_text(
            payload,
            "read_only_reconciliation_status",
        ),
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "blockers": list(_dedupe(blockers)),
    }


def _candidate_evidence(
    *,
    router_decision: Mapping[str, object],
    sizing_preview: Mapping[str, object],
    handoff: Mapping[str, object],
    dry_run: Mapping[str, object],
    sources: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    router_source = _mapping(sources.get("router_decision"))
    sizing_source = _mapping(sources.get("sizing_preview"))
    handoff_source = _mapping(sources.get("paper_oms_handoff"))
    dry_run_source = _mapping(sources.get("paper_oms_dry_run"))
    selected_candidate = _selected_candidate(router_decision, sizing_preview, handoff, dry_run)
    selected_candidate_id = _first_nonempty(
        _first_text(router_decision, "selected_candidate_id"),
        _first_text(sizing_preview, "selected_candidate_id"),
        _first_text(handoff, "selected_candidate_id"),
        _first_text(dry_run, "selected_candidate_id"),
        _first_text(selected_candidate, "candidate_id"),
    )
    symbol = _normalize_symbol(
        _first_nonempty(
            _first_text(router_decision, "symbol"),
            _first_text(selected_candidate, "symbol"),
            _first_text(sizing_preview, "symbol"),
            _first_text(handoff, "symbol"),
            _first_text(dry_run, "symbol"),
        )
    )
    asset_class = _first_nonempty(
        _first_text(selected_candidate, "asset_class"),
        _first_text(sizing_preview, "asset_class"),
        _first_text(handoff, "asset_class"),
        _first_text(dry_run, "asset_class"),
        "crypto" if selected_candidate_id.startswith("crypto:") else "",
    )
    router_status = _first_text(router_decision, "router_decision")
    sizing_status = _first_text(sizing_preview, "sizing_status")
    handoff_status = _first_text(handoff, "handoff_status")
    dry_run_status = _first_text(dry_run, "dry_run_status")
    dry_run_blockers = list(_string_sequence(dry_run.get("blockers")))

    blockers: list[str] = []
    for source_name, source in (
        ("router_decision", router_source),
        ("sizing_preview", sizing_source),
        ("paper_oms_handoff", handoff_source),
        ("paper_oms_dry_run", dry_run_source),
    ):
        read_error = _text(source.get("read_error"))
        if read_error:
            blockers.append(read_error)

    if not _text(router_source.get("read_error")):
        router_blockers = list(_string_sequence(router_decision.get("blockers")))
        blockers.extend(router_blockers)
        if router_status == "no_trade":
            blockers.append("router_decision_no_trade")
        elif router_status != "selected":
            blockers.append("router_decision_not_selected")
        if not selected_candidate_id:
            blockers.append("missing_selected_candidate")
        if asset_class != "crypto":
            blockers.append("selected_candidate_not_crypto")
        if symbol != "BTCUSD":
            blockers.append("selected_symbol_not_BTCUSD")

    if not _text(sizing_source.get("read_error")):
        blockers.extend(_string_sequence(sizing_preview.get("blockers")))
        if sizing_status != "preview_ready":
            blockers.append("sizing_status_not_preview_ready")
        for field_name in (
            "paper_submit_authorized",
            "paper_submit_performed",
            "broker_mutation_performed",
        ):
            if _is_true(sizing_preview.get(field_name)):
                blockers.append(f"sizing_{field_name}_true")

    if not _text(handoff_source.get("read_error")):
        blockers.extend(_string_sequence(handoff.get("blockers")))
        if handoff_status != "approval_required":
            blockers.append("handoff_status_not_approval_required")
        for field_name in (
            "paper_submit_authorized",
            "paper_submit_performed",
            "broker_mutation_performed",
            "live_mutation_performed",
        ):
            if _is_true(handoff.get(field_name)):
                blockers.append(f"handoff_{field_name}_true")

    if not _text(dry_run_source.get("read_error")):
        blockers.extend(dry_run_blockers)
        if dry_run_status != "blocked_not_authorized":
            blockers.append("dry_run_status_not_blocked_not_authorized")
        for field_name in (
            "paper_submit_authorized",
            "paper_submit_performed",
            "broker_mutation_performed",
            "live_mutation_performed",
        ):
            if _is_true(dry_run.get(field_name)):
                blockers.append(f"dry_run_{field_name}_true")

    blockers = list(_dedupe(blockers))
    router_candidate_eligible = (
        not _text(router_source.get("read_error"))
        and router_status == "selected"
        and bool(selected_candidate_id)
        and asset_class == "crypto"
        and symbol == "BTCUSD"
        and not list(_string_sequence(router_decision.get("blockers")))
    )
    current_candidate_eligible = (
        router_candidate_eligible
        and not _text(sizing_source.get("read_error"))
        and not _text(handoff_source.get("read_error"))
        and not _text(dry_run_source.get("read_error"))
        and sizing_status == "preview_ready"
        and handoff_status == "approval_required"
        and dry_run_status == "blocked_not_authorized"
        and not blockers
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_paper_autonomy_candidate_evidence",
        "router_candidate_eligible": router_candidate_eligible,
        "current_candidate_eligible": current_candidate_eligible,
        "router_decision": router_status,
        "sizing_status": sizing_status,
        "handoff_status": handoff_status,
        "dry_run_status": dry_run_status,
        "selected_candidate_id": selected_candidate_id,
        "asset_class": asset_class,
        "symbol": symbol,
        "strategy_id": _first_nonempty(
            _first_text(handoff, "strategy_id"),
            _first_text(dry_run, "selected_strategy"),
            _first_text(selected_candidate, "strategy_id"),
        ),
        "dry_run_id": _first_text(dry_run, "dry_run_id"),
        "pre_broker_order_id": _first_text(dry_run, "pre_broker_order_id"),
        "idempotency_key": _first_text(dry_run, "idempotency_key"),
        "rounded_qty": _first_nonempty(
            _first_text(dry_run, "rounded_qty"),
            _first_text(handoff, "rounded_qty"),
            _first_text(sizing_preview, "rounded_qty"),
        ),
        "derived_preview_value": _first_nonempty(
            _first_text(dry_run, "derived_preview_value"),
            _first_text(handoff, "derived_preview_value"),
            _first_text(sizing_preview, "derived_preview_value"),
        ),
        "sources": {
            "router_decision": dict(router_source),
            "sizing_preview": dict(sizing_source),
            "paper_oms_handoff": dict(handoff_source),
            "paper_oms_dry_run": dict(dry_run_source),
        },
        "blockers": blockers,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }


def _classify_next_action(
    *,
    lifecycle_evidence: Mapping[str, object],
    candidate_evidence: Mapping[str, object],
) -> str:
    if not _is_true(lifecycle_evidence.get("lifecycle_certified")):
        return "blocked"
    if _text(candidate_evidence.get("router_decision")) == "no_trade":
        return "no_trade"
    candidate_blockers = set(_string_sequence(candidate_evidence.get("blockers")))
    refresh_blockers = {
        "router_decision_missing",
        "router_decision_not_selected",
        "missing_selected_candidate",
        "selected_candidate_not_crypto",
        "selected_symbol_not_BTCUSD",
        "sizing_preview_missing",
        "sizing_status_not_preview_ready",
    }
    if candidate_blockers.intersection(refresh_blockers):
        return "refresh_data_and_rerun_router"
    if "paper_oms_handoff_missing" in candidate_blockers:
        return "approval_packet_required"
    if "paper_oms_dry_run_missing" in candidate_blockers:
        return "approval_packet_required"
    if not _is_true(lifecycle_evidence.get("final_flat_observed")):
        return "paper_read_reconciliation_required"
    if _is_true(candidate_evidence.get("current_candidate_eligible")):
        return "operator_review_required"
    return "blocked"


def _cadence_status(*, next_action: str, blockers: Sequence[str]) -> str:
    if next_action == "operator_review_required":
        return "ready_for_supervised_operator_review"
    if next_action == "no_trade":
        return "no_trade"
    if next_action in {
        "approval_packet_required",
        "refresh_data_and_rerun_router",
        "paper_read_reconciliation_required",
    }:
        return "action_required"
    if blockers:
        return "blocked"
    return "blocked"


def _action_if_authorized(
    *,
    lifecycle_certified: bool,
    current_candidate_eligible: bool,
    selected_candidate_id: str,
) -> str:
    if lifecycle_certified and current_candidate_eligible:
        return (
            "prepare_one_bounded_BTCUSD_paper_entry_from_dry_run_identity_for_"
            "operator_authorized_submit_flow"
        )
    if not lifecycle_certified:
        return "do_nothing_lifecycle_not_certified"
    if not selected_candidate_id:
        return "do_nothing_no_current_router_candidate"
    return "do_nothing_current_candidate_not_eligible"


def _next_operator_action_payload(
    *,
    next_action: str,
    status: str,
    blockers: Sequence[str],
    action_if_authorized: str,
    selected_candidate_id: str,
) -> dict[str, object]:
    reason = {
        "refresh_data_and_rerun_router": "router_or_sizing_inputs_missing_or_stale",
        "operator_review_required": (
            "lifecycle_certified_and_candidate_ready_but_fresh_authorization_required"
        ),
        "approval_packet_required": "handoff_or_dry_run_packet_missing",
        "paper_read_reconciliation_required": "flat_state_requires_scoped_read_review",
        "blocked": "required_lifecycle_or_candidate_evidence_missing_or_invalid",
        "no_trade": "router_selected_no_trade",
    }[next_action]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_paper_autonomy_next_operator_action",
        "action": next_action,
        "cadence_status": status,
        "reason": reason,
        "selected_candidate_id": selected_candidate_id,
        "would_do_next_if_authorization_granted": action_if_authorized,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "prior_v5_8_authorization_status": "consumed_not_reusable",
        "prior_v5_10_authorization_status": "consumed_not_reusable",
        "fresh_authorization_required_for_order": True,
        "blockers": list(blockers),
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }


def _authorization_state() -> dict[str, object]:
    return {
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "paper_submit_currently_authorized": False,
        "prior_v5_8_authorization_status": "consumed_not_reusable",
        "prior_v5_10_authorization_status": "consumed_not_reusable",
        "prior_authorizations_reusable": False,
        "fresh_authorization_required_for_order": True,
        "authorization_reuse_blockers": [
            "v5_8_authorization_was_single_use_submit_cancel_certification",
            "v5_10_authorization_was_single_use_fill_exit_certification",
            "fresh_operator_authorization_required_before_any_new_order",
        ],
    }


def _operating_record(cadence: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_paper_autonomy_cadence",
        "as_of": cadence.get("as_of", ""),
        "cadence_status": cadence.get("cadence_status", ""),
        "next_action": cadence.get("next_action", ""),
        "lifecycle_certified": cadence.get("lifecycle_certified") is True,
        "submit_cancel_certified": cadence.get("submit_cancel_certified") is True,
        "fill_exit_certified": cadence.get("fill_exit_certified") is True,
        "final_flat_observed": cadence.get("final_flat_observed") is True,
        "current_router_candidate_eligible": (
            cadence.get("current_router_candidate_eligible") is True
        ),
        "current_candidate_eligible": cadence.get("current_candidate_eligible") is True,
        "selected_candidate_id": cadence.get("selected_candidate_id", ""),
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "prior_v5_8_authorization_status": "consumed_not_reusable",
        "prior_v5_10_authorization_status": "consumed_not_reusable",
        "fresh_authorization_required_for_order": True,
        "would_do_next_if_authorization_granted": cadence.get(
            "would_do_next_if_authorization_granted",
            "",
        ),
        "blockers": cadence.get("blockers", []),
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }


def _selected_candidate(
    router_decision: Mapping[str, object],
    sizing_preview: Mapping[str, object],
    handoff: Mapping[str, object],
    dry_run: Mapping[str, object],
) -> dict[str, object]:
    for source in (
        router_decision.get("selected_candidate"),
        sizing_preview.get("selected_candidate"),
        handoff.get("selected_candidate"),
        dry_run.get("selected_candidate"),
    ):
        if isinstance(source, Mapping):
            return dict(source)
    return {}


def _source_record(*, path: Path, read_error: str) -> dict[str, object]:
    return {
        "path": str(path),
        "readable": read_error == "",
        "read_error": read_error,
        "sha256": _file_sha256(path) if path.is_file() else "",
    }


def _read_json_mapping(path: Path, artifact_name: str) -> dict[str, object]:
    if not path.is_file():
        return {"payload": {}, "error": f"{artifact_name}_missing"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"payload": {}, "error": f"{artifact_name}_invalid_json:{exc.msg}"}
    except OSError:
        return {"payload": {}, "error": f"{artifact_name}_unreadable"}
    if not isinstance(payload, Mapping):
        return {"payload": {}, "error": f"{artifact_name}_not_json_object"}
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


def _false_flags() -> dict[str, bool]:
    return {field_name: False for field_name in FALSE_AUTHORIZATION_FIELDS}


def _residual_position(payload: Mapping[str, object]) -> object:
    direct = payload.get("residual_position")
    if direct not in (None, ""):
        return direct
    reconciliation = payload.get("reconciliation")
    if isinstance(reconciliation, Mapping):
        nested = reconciliation.get("residual_position")
        if nested not in (None, ""):
            return nested
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


def _residual_status_is_flat(value: object) -> bool:
    normalized = _normalize_status(value)
    return (
        "flat" in normalized
        or "no_btcusd_position" in normalized
        or "no_btc_position" in normalized
    )


def _decimal_zero(value: object) -> bool:
    text = _text(value)
    if not text:
        return False
    try:
        return float(text) == 0.0
    except ValueError:
        return False


def _int_or_none(value: object) -> int | None:
    try:
        return int(_text(value))
    except ValueError:
        return None


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


def _first_nonempty(*values: object) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _normalize_symbol(value: object) -> str:
    return _text(value).replace("/", "").upper()


def _normalize_status(value: object) -> str:
    return _text(value).lower().replace(" ", "_")


def _is_true(value: object) -> bool:
    if type(value) is bool:
        return value
    if type(value) is str:
        return value.strip().lower() == "true"
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
            "Build a no-submit supervised crypto paper autonomy cadence packet "
            "from local artifacts."
        ),
    )
    parser.add_argument("--submit-cancel-result-path", type=Path, default=DEFAULT_SUBMIT_CANCEL_RESULT)
    parser.add_argument("--certification-ingestion-path", type=Path, default=DEFAULT_CERTIFICATION_INGESTION)
    parser.add_argument("--fill-exit-result-path", type=Path, default=DEFAULT_FILL_EXIT_RESULT)
    parser.add_argument("--fill-exit-ingestion-path", type=Path, default=DEFAULT_FILL_EXIT_INGESTION)
    parser.add_argument("--router-decision-path", type=Path, default=DEFAULT_ROUTER_DECISION)
    parser.add_argument("--sizing-preview-path", type=Path, default=DEFAULT_SIZING_PREVIEW)
    parser.add_argument("--handoff-path", type=Path, default=DEFAULT_HANDOFF)
    parser.add_argument("--dry-run-path", type=Path, default=DEFAULT_DRY_RUN)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--as-of", default="")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    cadence = run_crypto_paper_autonomy_cadence(
        submit_cancel_result_path=args.submit_cancel_result_path,
        certification_ingestion_path=args.certification_ingestion_path,
        fill_exit_result_path=args.fill_exit_result_path,
        fill_exit_ingestion_path=args.fill_exit_ingestion_path,
        router_decision_path=args.router_decision_path,
        sizing_preview_path=args.sizing_preview_path,
        handoff_path=args.handoff_path,
        dry_run_path=args.dry_run_path,
        output_root=args.output_root,
        as_of=args.as_of,
        write_artifacts=True,
    )
    if args.format == "json":
        print(json.dumps(_json_safe(cadence), sort_keys=True))
    else:
        print(render_autonomy_cadence_text(cadence))
    return 2 if cadence.get("cadence_status") == "blocked" else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
