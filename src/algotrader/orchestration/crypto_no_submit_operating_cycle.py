"""v5.13 no-submit crypto operating cycle.

This module composes existing local no-submit crypto stages and writes a compact
operating packet. It does not read brokers, mutate brokers, submit paper orders,
load credentials, or contact the network.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from algotrader.orchestration.crypto_paper_autonomy_cadence import (
    DEFAULT_CERTIFICATION_INGESTION,
    DEFAULT_FILL_EXIT_INGESTION,
    DEFAULT_FILL_EXIT_RESULT,
    DEFAULT_SUBMIT_CANCEL_RESULT,
    run_crypto_paper_autonomy_cadence,
)
from algotrader.orchestration.crypto_paper_oms_dry_run import (
    run_crypto_paper_oms_dry_run,
)
from algotrader.orchestration.crypto_paper_oms_handoff import (
    run_crypto_paper_oms_handoff,
)
from algotrader.orchestration.crypto_qty_sizing_preview import (
    CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_NOTIONAL_CAP,
    run_crypto_qty_sizing_preview,
)
from algotrader.orchestration.crypto_universe_refresh import (
    CRYPTO_UNIVERSE_REFRESH_DEFAULT_BARS_CSV,
    CRYPTO_UNIVERSE_REFRESH_DEFAULT_VISIBILITY_STATUS,
    run_crypto_universe_refresh,
)
from algotrader.orchestration.opportunity_router import run_opportunity_router

SCHEMA_VERSION = "v5_13_crypto_no_submit_operating_cycle_v1"
CRYPTO_READINESS_PACKET_SCHEMA_VERSION = "v5_15_crypto_no_submit_operating_packet_v1"
COMMAND_NAME = "run_crypto_no_submit_operating_cycle"

DEFAULT_OUTPUT_ROOT = Path("runs/crypto_no_submit_operating_cycle/latest")
DEFAULT_CRYPTO_REFRESH_OUTPUT_ROOT = Path(
    "runs/crypto_universe_refresh/paper_read_repair_latest"
)
DEFAULT_ROUTER_OUTPUT_ROOT = Path("runs/opportunity_router/paper_read_repair_latest")
DEFAULT_SIZING_PREVIEW_OUTPUT_ROOT = Path("runs/crypto_qty_sizing_preview/latest")
DEFAULT_HANDOFF_OUTPUT_ROOT = Path("runs/crypto_paper_oms_handoff/latest")
DEFAULT_DRY_RUN_OUTPUT_ROOT = Path("runs/crypto_paper_oms_dry_run/latest")
DEFAULT_AUTONOMY_CADENCE_OUTPUT_ROOT = Path("runs/crypto_paper_autonomy_cadence/latest")

FinalState = Literal[
    "selected_candidate_no_submit_packet_ready",
    "no_trade",
    "blocked_missing_router_inputs",
    "blocked_router_decision_not_selected",
    "blocked_missing_sizing_preview",
    "blocked_missing_handoff",
    "blocked_missing_dry_run",
    "blocked_missing_lifecycle_evidence",
    "paper_read_reconciliation_required",
    "blocked",
]

NextOperatorAction = Literal[
    "review_no_submit_packet",
    "refresh_data_and_rerun_router",
    "approval_packet_required",
    "paper_read_reconciliation_required",
    "blocked",
    "no_trade",
]

FINAL_STATES: tuple[FinalState, ...] = (
    "selected_candidate_no_submit_packet_ready",
    "no_trade",
    "blocked_missing_router_inputs",
    "blocked_router_decision_not_selected",
    "blocked_missing_sizing_preview",
    "blocked_missing_handoff",
    "blocked_missing_dry_run",
    "blocked_missing_lifecycle_evidence",
    "paper_read_reconciliation_required",
    "blocked",
)

NEXT_OPERATOR_ACTIONS: tuple[NextOperatorAction, ...] = (
    "review_no_submit_packet",
    "refresh_data_and_rerun_router",
    "approval_packet_required",
    "paper_read_reconciliation_required",
    "blocked",
    "no_trade",
)

REQUIRED_LABELS = (
    "crypto_no_submit_operating_cycle",
    "paper_lab_only",
    "research_only",
    "no_submit",
    "no_broker_read",
    "no_broker_mutation",
    "not_live_authorized",
    "fresh_authorization_required_for_order",
    "profit_claim=none",
)

FALSE_SAFETY_FIELDS = (
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

ROUTER_INPUT_BLOCKERS = {
    "broker_state_not_observed",
    "history_missing",
    "insufficient_history",
    "local_artifact_missing",
    "metadata_missing",
    "metadata_not_observed",
    "missing_data",
    "missing_history",
    "stale_data",
}

__all__ = [
    "COMMAND_NAME",
    "CRYPTO_READINESS_PACKET_SCHEMA_VERSION",
    "DEFAULT_AUTONOMY_CADENCE_OUTPUT_ROOT",
    "DEFAULT_CRYPTO_REFRESH_OUTPUT_ROOT",
    "DEFAULT_DRY_RUN_OUTPUT_ROOT",
    "DEFAULT_HANDOFF_OUTPUT_ROOT",
    "DEFAULT_OUTPUT_ROOT",
    "DEFAULT_ROUTER_OUTPUT_ROOT",
    "DEFAULT_SIZING_PREVIEW_OUTPUT_ROOT",
    "FALSE_SAFETY_FIELDS",
    "FINAL_STATES",
    "NEXT_OPERATOR_ACTIONS",
    "REQUIRED_LABELS",
    "SCHEMA_VERSION",
    "build_crypto_readiness_packet",
    "build_crypto_no_submit_operating_cycle_packet",
    "main",
    "render_cycle_brief_markdown",
    "render_cycle_text",
    "run_crypto_no_submit_operating_cycle",
    "validate_crypto_readiness_packet",
    "write_crypto_no_submit_operating_cycle_artifacts",
]


def run_crypto_no_submit_operating_cycle(
    *,
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
    crypto_refresh_output_root: Path | str = DEFAULT_CRYPTO_REFRESH_OUTPUT_ROOT,
    router_output_root: Path | str = DEFAULT_ROUTER_OUTPUT_ROOT,
    sizing_preview_output_root: Path | str = DEFAULT_SIZING_PREVIEW_OUTPUT_ROOT,
    handoff_output_root: Path | str = DEFAULT_HANDOFF_OUTPUT_ROOT,
    dry_run_output_root: Path | str = DEFAULT_DRY_RUN_OUTPUT_ROOT,
    autonomy_cadence_output_root: Path | str = DEFAULT_AUTONOMY_CADENCE_OUTPUT_ROOT,
    refresh_mode: Literal["local_replay", "offline_fixture"] = "local_replay",
    bars_csv: Path | str = CRYPTO_UNIVERSE_REFRESH_DEFAULT_BARS_CSV,
    crypto_visibility_status: Path | str = CRYPTO_UNIVERSE_REFRESH_DEFAULT_VISIBILITY_STATUS,
    spy_bars_csv: Path | str | None = None,
    submit_cancel_result_path: Path | str = DEFAULT_SUBMIT_CANCEL_RESULT,
    certification_ingestion_path: Path | str = DEFAULT_CERTIFICATION_INGESTION,
    fill_exit_result_path: Path | str = DEFAULT_FILL_EXIT_RESULT,
    fill_exit_ingestion_path: Path | str = DEFAULT_FILL_EXIT_INGESTION,
    preview_notional_cap: Decimal | str = CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_NOTIONAL_CAP,
    allow_fixture_backed: bool = False,
    as_of: datetime | str | None = None,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Run the local no-submit crypto operating cycle and optionally write artifacts."""

    root = Path(output_root)
    if write_artifacts:
        root.mkdir(parents=True, exist_ok=True)

    refresh_root = Path(crypto_refresh_output_root)
    router_root = Path(router_output_root)
    sizing_root = Path(sizing_preview_output_root)
    handoff_root = Path(handoff_output_root)
    dry_run_root = Path(dry_run_output_root)
    cadence_root = Path(autonomy_cadence_output_root)

    router_decision_path = router_root / "router_decision.json"
    opportunity_candidates_path = router_root / "opportunity_candidates.json"
    crypto_router_input_manifest_path = refresh_root / "crypto_router_input_manifest.json"
    sizing_preview_path = sizing_root / "sizing_preview.json"
    handoff_path = handoff_root / "paper_oms_handoff.json"
    dry_run_path = dry_run_root / "paper_oms_dry_run.json"
    normalized_router_result_path = root / "router_result.json"

    as_of_value = _as_of_argument(as_of)
    stage_errors: list[dict[str, object]] = []

    refresh_packet = _stage_call(
        "crypto_universe_refresh",
        run_crypto_universe_refresh,
        stage_errors,
        output_root=refresh_root,
        mode=refresh_mode,
        bars_csv=bars_csv,
        crypto_visibility_status=crypto_visibility_status,
        as_of=as_of_value,
        write_artifacts=True,
    )
    router_packet = _stage_call(
        "opportunity_router",
        run_opportunity_router,
        stage_errors,
        output_root=router_root,
        spy_bars_csv=spy_bars_csv,
        crypto_bars_csv=bars_csv,
        crypto_visibility_status=crypto_visibility_status,
        crypto_router_input_manifest=crypto_router_input_manifest_path,
        as_of=as_of_value,
        write_artifacts=True,
    )
    router_result = _normalized_router_result(
        router_packet=router_packet,
        router_decision_path=router_decision_path,
        opportunity_candidates_path=opportunity_candidates_path,
    )
    if write_artifacts:
        _write_json(normalized_router_result_path, router_result)

    sizing_packet = _stage_call(
        "crypto_qty_sizing_preview",
        run_crypto_qty_sizing_preview,
        stage_errors,
        router_decision_path=router_decision_path,
        opportunity_candidates_path=opportunity_candidates_path,
        crypto_router_input_manifest_path=crypto_router_input_manifest_path,
        output_root=sizing_root,
        preview_notional_cap=preview_notional_cap,
        allow_fixture_backed=allow_fixture_backed,
        write_artifacts=True,
    )
    sizing_preview_status = _sizing_preview_status(sizing_packet)

    handoff_packet = _stage_call(
        "crypto_paper_oms_handoff",
        run_crypto_paper_oms_handoff,
        stage_errors,
        sizing_preview_path=sizing_preview_path,
        output_root=handoff_root,
        allow_fixture_backed=allow_fixture_backed,
        write_artifacts=True,
    )
    handoff_status = _paper_oms_handoff_status(handoff_packet)

    dry_run_packet = _stage_call(
        "crypto_paper_oms_dry_run",
        run_crypto_paper_oms_dry_run,
        stage_errors,
        handoff_path=handoff_path,
        output_root=dry_run_root,
        allow_fixture_backed=allow_fixture_backed,
        write_artifacts=True,
    )
    dry_run_identity_status = _dry_run_identity_status(dry_run_packet)

    cadence_packet = _stage_call(
        "crypto_paper_autonomy_cadence",
        run_crypto_paper_autonomy_cadence,
        stage_errors,
        output_root=cadence_root,
        submit_cancel_result_path=submit_cancel_result_path,
        certification_ingestion_path=certification_ingestion_path,
        fill_exit_result_path=fill_exit_result_path,
        fill_exit_ingestion_path=fill_exit_ingestion_path,
        router_decision_path=normalized_router_result_path,
        sizing_preview_path=sizing_preview_path,
        handoff_path=handoff_path,
        dry_run_path=dry_run_path,
        as_of=_text(as_of_value),
        write_artifacts=True,
    )
    autonomy_cadence_status = _autonomy_cadence_status(cadence_packet)

    packet = build_crypto_no_submit_operating_cycle_packet(
        refresh_packet=refresh_packet,
        router_result=router_result,
        sizing_preview_status=sizing_preview_status,
        paper_oms_handoff_status=handoff_status,
        dry_run_identity_status=dry_run_identity_status,
        autonomy_cadence_status=autonomy_cadence_status,
        stage_errors=stage_errors,
        output_root=root,
        stage_artifact_paths={
            "crypto_universe_refresh": refresh_root,
            "opportunity_router": router_root,
            "crypto_qty_sizing_preview": sizing_root,
            "crypto_paper_oms_handoff": handoff_root,
            "crypto_paper_oms_dry_run": dry_run_root,
            "crypto_paper_autonomy_cadence": cadence_root,
        },
        as_of=_cycle_as_of(
            as_of_value,
            dry_run_identity_status,
            handoff_status,
            sizing_preview_status,
            router_result,
            autonomy_cadence_status,
        ),
    )
    if write_artifacts:
        packet["artifact_paths"] = write_crypto_no_submit_operating_cycle_artifacts(
            root,
            packet,
        )
    return packet


def build_crypto_no_submit_operating_cycle_packet(
    *,
    refresh_packet: Mapping[str, object],
    router_result: Mapping[str, object],
    sizing_preview_status: Mapping[str, object],
    paper_oms_handoff_status: Mapping[str, object],
    dry_run_identity_status: Mapping[str, object],
    autonomy_cadence_status: Mapping[str, object],
    stage_errors: Sequence[Mapping[str, object]] = (),
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
    stage_artifact_paths: Mapping[str, object] | None = None,
    as_of: str = "",
) -> dict[str, object]:
    """Build the primitive-only cycle packet from stage payloads."""

    final_state = _classify_final_state(
        refresh_packet=refresh_packet,
        router_result=router_result,
        sizing_preview_status=sizing_preview_status,
        paper_oms_handoff_status=paper_oms_handoff_status,
        dry_run_identity_status=dry_run_identity_status,
        autonomy_cadence_status=autonomy_cadence_status,
        stage_errors=stage_errors,
    )
    next_action = _next_operator_action(final_state)
    blockers = _cycle_blockers(
        final_state=final_state,
        refresh_packet=refresh_packet,
        router_result=router_result,
        sizing_preview_status=sizing_preview_status,
        paper_oms_handoff_status=paper_oms_handoff_status,
        dry_run_identity_status=dry_run_identity_status,
        autonomy_cadence_status=autonomy_cadence_status,
        stage_errors=stage_errors,
    )
    selected_candidate_id = _first_nonempty(
        _first_text(router_result, "selected_candidate_id"),
        _first_text(sizing_preview_status, "selected_candidate_id"),
        _first_text(paper_oms_handoff_status, "selected_candidate_id"),
        _first_text(dry_run_identity_status, "selected_candidate_id"),
        _first_text(autonomy_cadence_status, "selected_candidate_id"),
    )
    crypto_readiness_packet = build_crypto_readiness_packet(
        refresh_packet=refresh_packet,
        router_result=router_result,
        sizing_preview_status=sizing_preview_status,
        paper_oms_handoff_status=paper_oms_handoff_status,
        dry_run_identity_status=dry_run_identity_status,
        autonomy_cadence_status=autonomy_cadence_status,
        final_state=final_state,
        cycle_blockers=blockers,
        selected_candidate_id=selected_candidate_id,
        as_of=as_of,
    )
    next_operator_action = _next_operator_action_payload(
        final_state=final_state,
        next_action=next_action,
        selected_candidate_id=selected_candidate_id,
        blockers=blockers,
    )
    cycle_status = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_no_submit_operating_cycle_status",
        "operator_command": COMMAND_NAME,
        "as_of": as_of,
        "final_state": final_state,
        "next_operator_action": next_action,
        "selected_candidate_id": selected_candidate_id,
        "stage_status": {
            "router_decision": _first_text(router_result, "router_decision", "decision"),
            "sizing_status": _first_text(sizing_preview_status, "sizing_status"),
            "handoff_status": _first_text(paper_oms_handoff_status, "handoff_status"),
            "dry_run_status": _first_text(dry_run_identity_status, "dry_run_status"),
            "cadence_status": _first_text(autonomy_cadence_status, "cadence_status"),
        },
        "stage_errors": [dict(error) for error in stage_errors],
        "stage_artifact_roots": {
            key: str(value) for key, value in sorted(dict(stage_artifact_paths or {}).items())
        },
        "prior_v5_8_authorization_status": "consumed_not_reusable",
        "prior_v5_10_authorization_status": "consumed_not_reusable",
        "prior_authorizations_reusable": False,
        "fresh_authorization_required_for_order": True,
        "paper_submit_currently_authorized": False,
        "broker_action_permitted": False,
        "crypto_readiness_decision": crypto_readiness_packet["readiness_decision"],
        "crypto_readiness_blocker_taxonomy": crypto_readiness_packet[
            "blocker_taxonomy"
        ],
        "crypto_readiness_blocker": crypto_readiness_packet["blocker"],
        "crypto_readiness_evidence_classification": crypto_readiness_packet[
            "evidence_classification"
        ],
        "latest_price_source": crypto_readiness_packet["latest_price_source"],
        "latest_price_basis": crypto_readiness_packet["latest_price_basis"],
        "latest_price_freshness_status": crypto_readiness_packet[
            "latest_price_freshness_status"
        ],
        "blockers": blockers,
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_no_submit_operating_cycle",
        "operator_command": COMMAND_NAME,
        "as_of": as_of,
        "output_root": str(output_root),
        "cycle_status": cycle_status,
        "router_result": dict(router_result),
        "sizing_preview_status": dict(sizing_preview_status),
        "paper_oms_handoff_status": dict(paper_oms_handoff_status),
        "dry_run_identity_status": dict(dry_run_identity_status),
        "autonomy_cadence_status": dict(autonomy_cadence_status),
        "crypto_readiness_packet": crypto_readiness_packet,
        "next_operator_action": next_operator_action,
        "stage_errors": [dict(error) for error in stage_errors],
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }


def write_crypto_no_submit_operating_cycle_artifacts(
    output_root: Path | str,
    packet: Mapping[str, object],
) -> dict[str, str]:
    """Write the cycle operating packet under the output root."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "cycle_brief": root / "cycle_brief.md",
        "cycle_status": root / "cycle_status.json",
        "router_result": root / "router_result.json",
        "sizing_preview_status": root / "sizing_preview_status.json",
        "paper_oms_handoff_status": root / "paper_oms_handoff_status.json",
        "dry_run_identity_status": root / "dry_run_identity_status.json",
        "autonomy_cadence_status": root / "autonomy_cadence_status.json",
        "crypto_readiness_packet": root / "crypto_readiness_packet.json",
        "next_operator_action": root / "next_operator_action.json",
        "operating_record": root / "operating_record.jsonl",
    }
    manifest_path = root / "manifest.json"
    artifact_paths = {key: str(path) for key, path in paths.items()}
    artifact_paths["manifest"] = str(manifest_path)

    packet_payload = {**dict(packet), "artifact_paths": artifact_paths}
    cycle_status = {**_mapping(packet.get("cycle_status")), "artifact_paths": artifact_paths}
    next_operator_action = {
        **_mapping(packet.get("next_operator_action")),
        "artifact_paths": artifact_paths,
    }

    paths["cycle_brief"].write_text(
        render_cycle_brief_markdown(packet_payload) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_json(paths["cycle_status"], cycle_status)
    _write_json(paths["router_result"], _mapping(packet.get("router_result")))
    _write_json(paths["sizing_preview_status"], _mapping(packet.get("sizing_preview_status")))
    _write_json(
        paths["paper_oms_handoff_status"],
        _mapping(packet.get("paper_oms_handoff_status")),
    )
    _write_json(
        paths["dry_run_identity_status"],
        _mapping(packet.get("dry_run_identity_status")),
    )
    _write_json(
        paths["autonomy_cadence_status"],
        _mapping(packet.get("autonomy_cadence_status")),
    )
    _write_json(
        paths["crypto_readiness_packet"],
        _mapping(packet.get("crypto_readiness_packet")),
    )
    _write_json(paths["next_operator_action"], next_operator_action)
    paths["operating_record"].write_text(
        json.dumps(
            _json_safe(_operating_record(packet_payload)),
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_no_submit_operating_cycle_manifest",
        "as_of": packet.get("as_of", ""),
        "artifact_root": str(root),
        "required_artifacts": {
            key: _artifact_entry(path) for key, path in sorted(paths.items())
        },
        "manifest": {"path": str(manifest_path)},
        "final_state": _mapping(packet.get("cycle_status")).get("final_state", ""),
        "next_operator_action": _mapping(packet.get("cycle_status")).get(
            "next_operator_action",
            "",
        ),
        "generated_under_runs": _generated_under_runs(root),
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        "prior_v5_8_authorization_status": "consumed_not_reusable",
        "prior_v5_10_authorization_status": "consumed_not_reusable",
        "prior_authorizations_reusable": False,
        "fresh_authorization_required_for_order": True,
        **_false_flags(),
    }
    _write_json(manifest_path, manifest)
    return artifact_paths


def render_cycle_brief_markdown(packet: Mapping[str, object]) -> str:
    """Render a compact operator-facing cycle brief."""

    status = _mapping(packet.get("cycle_status"))
    router = _mapping(packet.get("router_result"))
    sizing = _mapping(packet.get("sizing_preview_status"))
    handoff = _mapping(packet.get("paper_oms_handoff_status"))
    dry_run = _mapping(packet.get("dry_run_identity_status"))
    cadence = _mapping(packet.get("autonomy_cadence_status"))
    readiness = _mapping(packet.get("crypto_readiness_packet"))
    action = _mapping(packet.get("next_operator_action"))
    blockers = list(_string_sequence(status.get("blockers")))
    return "\n".join(
        [
            "# Crypto No-Submit Operating Cycle",
            "",
            f"- final state: `{status.get('final_state', '')}`",
            f"- next operator action: `{status.get('next_operator_action', '')}`",
            f"- selected candidate: `{status.get('selected_candidate_id', '')}`",
            f"- router decision: `{router.get('router_decision', '')}`",
            f"- sizing status: `{sizing.get('sizing_status', '')}`",
            f"- handoff status: `{handoff.get('handoff_status', '')}`",
            f"- dry-run status: `{dry_run.get('dry_run_status', '')}`",
            f"- cadence status: `{cadence.get('cadence_status', '')}`",
            f"- readiness decision: `{readiness.get('readiness_decision', '')}`",
            f"- readiness blocker taxonomy: `{readiness.get('blocker_taxonomy', '')}`",
            f"- readiness blocker: `{readiness.get('blocker', '')}`",
            f"- evidence classification: `{readiness.get('evidence_classification', '')}`",
            f"- latest price source: `{readiness.get('latest_price_source', '')}`",
            f"- latest price basis: `{readiness.get('latest_price_basis', '')}`",
            f"- latest price freshness: `{readiness.get('latest_price_freshness_status', '')}`",
            "- paper submit currently authorized: `false`",
            "- broker read occurred: `false`",
            "- broker mutation occurred: `false`",
            "- live endpoint touched: `false`",
            "- fresh authorization required for any order: `true`",
            f"- prior v5.8 authorization: `{status.get('prior_v5_8_authorization_status', '')}`",
            f"- prior v5.10 authorization: `{status.get('prior_v5_10_authorization_status', '')}`",
            f"- blockers: `{', '.join(blockers) if blockers else 'none'}`",
            "",
            "## Next Operator Action",
            "",
            f"- action: `{action.get('action', '')}`",
            f"- reason: `{action.get('reason', '')}`",
            "",
            "Labels: " + ", ".join(_string_sequence(status.get("labels"))),
        ]
    )


def render_cycle_text(packet: Mapping[str, object]) -> str:
    """Render compact key-value output for the PowerShell wrapper."""

    status = _mapping(packet.get("cycle_status"))
    readiness = _mapping(packet.get("crypto_readiness_packet"))
    artifacts = _mapping(packet.get("artifact_paths"))
    lines = [
        f"crypto_no_submit_operating_cycle_command={COMMAND_NAME}",
        f"final_state={_text(status.get('final_state'))}",
        f"next_operator_action={_text(status.get('next_operator_action'))}",
        f"selected_candidate_id={_text(status.get('selected_candidate_id'))}",
        f"crypto_readiness_decision={_text(readiness.get('readiness_decision'))}",
        f"crypto_readiness_blocker_taxonomy={_text(readiness.get('blocker_taxonomy'))}",
        f"crypto_readiness_blocker={_text(readiness.get('blocker'))}",
        f"crypto_evidence_classification={_text(readiness.get('evidence_classification'))}",
        f"latest_price_source={_text(readiness.get('latest_price_source'))}",
        f"latest_price_basis={_text(readiness.get('latest_price_basis'))}",
        f"latest_price_freshness_status={_text(readiness.get('latest_price_freshness_status'))}",
        "paper_submit_authorized=false",
        "broker_read_occurred=false",
        "broker_mutation_occurred=false",
        "live_endpoint_touched=false",
        "fresh_authorization_required_for_order=true",
        "prior_v5_8_authorization_status=consumed_not_reusable",
        "prior_v5_10_authorization_status=consumed_not_reusable",
        "blockers=" + ",".join(_string_sequence(status.get("blockers"))),
        "labels=" + ",".join(_string_sequence(status.get("labels"))),
    ]
    for key in (
        "cycle_brief",
        "cycle_status",
        "router_result",
        "sizing_preview_status",
        "paper_oms_handoff_status",
        "dry_run_identity_status",
        "autonomy_cadence_status",
        "crypto_readiness_packet",
        "next_operator_action",
        "operating_record",
        "manifest",
    ):
        value = _text(artifacts.get(key))
        if value:
            lines.append(f"artifact_{key}={value}")
    return "\n".join(lines)


def _stage_call(
    stage_name: str,
    function: Any,
    stage_errors: list[dict[str, object]],
    **kwargs: object,
) -> dict[str, object]:
    try:
        result = function(**kwargs)
    except Exception as exc:  # pragma: no cover - exercised through callers.
        error = {
            "stage": stage_name,
            "error_type": exc.__class__.__name__,
            "error": str(exc),
        }
        stage_errors.append(error)
        return {
            "schema_version": SCHEMA_VERSION,
            "record_type": f"{stage_name}_stage_error",
            "stage_status": "blocked",
            "blockers": [f"{stage_name}_stage_error:{exc.__class__.__name__}"],
            **_false_flags(),
        }
    return dict(result) if isinstance(result, Mapping) else {}


def _normalized_router_result(
    *,
    router_packet: Mapping[str, object],
    router_decision_path: Path,
    opportunity_candidates_path: Path,
) -> dict[str, object]:
    decision = _mapping(router_packet.get("router_decision"))
    if not decision:
        decision = _mapping(router_packet)
    status = _first_nonempty(
        _first_text(decision, "router_decision"),
        _first_text(decision, "decision"),
    )
    selected_candidate = _mapping(decision.get("selected_candidate"))
    blockers = list(_string_sequence(decision.get("blockers")))
    if not status:
        blockers.append("router_decision_missing")
    result = {
        **dict(decision),
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_no_submit_operating_cycle_router_result",
        "router_decision": status,
        "decision": status,
        "selected_candidate_id": _first_text(decision, "selected_candidate_id"),
        "selected_candidate": dict(selected_candidate),
        "selected_symbol": _first_nonempty(
            _first_text(decision, "selected_symbol"),
            _first_text(selected_candidate, "symbol"),
        ),
        "selected_asset_class": _first_nonempty(
            _first_text(decision, "selected_asset_class"),
            _first_text(selected_candidate, "asset_class"),
        ),
        "selected_strategy_id": _first_nonempty(
            _first_text(decision, "selected_strategy_id"),
            _first_text(selected_candidate, "strategy_id"),
        ),
        "source_router_decision_path": str(router_decision_path),
        "source_opportunity_candidates_path": str(opportunity_candidates_path),
        "blockers": list(_dedupe(blockers)),
        "labels": list(_merged_labels(decision.get("labels"))),
        "profit_claim": "none",
        **_false_flags(),
    }
    return result


def _sizing_preview_status(packet: Mapping[str, object]) -> dict[str, object]:
    preview = _mapping(packet.get("sizing_preview"))
    if not preview:
        preview = _mapping(packet)
    if not preview or not _first_text(preview, "sizing_status"):
        return _missing_stage_status("sizing_preview", "blocked_missing_sizing_preview")
    return {
        **dict(preview),
        "record_type": "crypto_no_submit_operating_cycle_sizing_preview_status",
        "labels": list(_merged_labels(preview.get("labels"))),
        "profit_claim": "none",
        **_false_flags(),
    }


def _paper_oms_handoff_status(packet: Mapping[str, object]) -> dict[str, object]:
    if not packet or not _first_text(packet, "handoff_status"):
        return _missing_stage_status("paper_oms_handoff", "blocked_missing_handoff")
    return {
        **dict(packet),
        "record_type": "crypto_no_submit_operating_cycle_paper_oms_handoff_status",
        "labels": list(_merged_labels(packet.get("labels"))),
        "profit_claim": "none",
        **_false_flags(),
    }


def _dry_run_identity_status(packet: Mapping[str, object]) -> dict[str, object]:
    if not packet or not _first_text(packet, "dry_run_status"):
        return _missing_stage_status("paper_oms_dry_run", "blocked_missing_dry_run")
    return {
        **dict(packet),
        "record_type": "crypto_no_submit_operating_cycle_dry_run_identity_status",
        "labels": list(_merged_labels(packet.get("labels"))),
        "profit_claim": "none",
        **_false_flags(),
    }


def _autonomy_cadence_status(packet: Mapping[str, object]) -> dict[str, object]:
    if not packet or not _first_text(packet, "cadence_status"):
        return _missing_stage_status(
            "crypto_paper_autonomy_cadence",
            "blocked_missing_lifecycle_evidence",
        )
    return {
        **dict(packet),
        "record_type": "crypto_no_submit_operating_cycle_autonomy_cadence_status",
        "labels": list(_merged_labels(packet.get("labels"))),
        "profit_claim": "none",
        **_false_flags(),
    }


def _missing_stage_status(stage_name: str, blocker: str) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": f"crypto_no_submit_operating_cycle_{stage_name}_status",
        "stage_status": "missing",
        "blockers": [blocker],
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }


def _classify_final_state(
    *,
    refresh_packet: Mapping[str, object],
    router_result: Mapping[str, object],
    sizing_preview_status: Mapping[str, object],
    paper_oms_handoff_status: Mapping[str, object],
    dry_run_identity_status: Mapping[str, object],
    autonomy_cadence_status: Mapping[str, object],
    stage_errors: Sequence[Mapping[str, object]],
) -> FinalState:
    router_status = _first_text(router_result, "router_decision", "decision")
    selected_candidate_id = _first_text(router_result, "selected_candidate_id")
    if _router_inputs_missing(refresh_packet):
        return "blocked_missing_router_inputs"
    if router_status == "no_trade":
        return "no_trade"
    if router_status != "selected" or not selected_candidate_id:
        return "blocked_router_decision_not_selected"
    if _first_text(sizing_preview_status, "sizing_status") != "preview_ready":
        return "blocked_missing_sizing_preview"
    if _first_text(paper_oms_handoff_status, "handoff_status") != "approval_required":
        return "blocked_missing_handoff"
    if _first_text(dry_run_identity_status, "dry_run_status") != "blocked_not_authorized":
        return "blocked_missing_dry_run"

    lifecycle = _mapping(autonomy_cadence_status.get("paper_lifecycle_evidence"))
    if not _is_true(autonomy_cadence_status.get("lifecycle_certified")):
        if (
            _is_true(lifecycle.get("submit_cancel_certified"))
            and _is_true(lifecycle.get("fill_exit_certified"))
            and not _is_true(lifecycle.get("final_flat_observed"))
        ):
            return "paper_read_reconciliation_required"
        return "blocked_missing_lifecycle_evidence"
    if _is_true(autonomy_cadence_status.get("current_candidate_eligible")):
        return "selected_candidate_no_submit_packet_ready"
    if stage_errors:
        return "blocked"
    return "blocked"


def _router_inputs_missing(refresh_packet: Mapping[str, object]) -> bool:
    summary = _mapping(refresh_packet.get("summary"))
    blockers = set(_top_blocker_names(summary.get("top_blockers")))
    blockers.update(_string_sequence(summary.get("blockers")))
    if not blockers.intersection(ROUTER_INPUT_BLOCKERS):
        return False
    eligible_count = _int_or_none(summary.get("eligible_input_symbol_count"))
    return eligible_count in (None, 0)


def _next_operator_action(final_state: FinalState) -> NextOperatorAction:
    return {
        "selected_candidate_no_submit_packet_ready": "review_no_submit_packet",
        "no_trade": "no_trade",
        "blocked_missing_router_inputs": "refresh_data_and_rerun_router",
        "blocked_router_decision_not_selected": "refresh_data_and_rerun_router",
        "blocked_missing_sizing_preview": "refresh_data_and_rerun_router",
        "blocked_missing_handoff": "approval_packet_required",
        "blocked_missing_dry_run": "approval_packet_required",
        "blocked_missing_lifecycle_evidence": "blocked",
        "paper_read_reconciliation_required": "paper_read_reconciliation_required",
        "blocked": "blocked",
    }[final_state]


def _next_operator_action_payload(
    *,
    final_state: FinalState,
    next_action: NextOperatorAction,
    selected_candidate_id: str,
    blockers: Sequence[str],
) -> dict[str, object]:
    reason = {
        "selected_candidate_no_submit_packet_ready": (
            "selected_candidate_sizing_handoff_dry_run_and_cadence_ready_no_submit"
        ),
        "no_trade": "router_returned_no_trade",
        "blocked_missing_router_inputs": "local_or_allowed_router_inputs_missing_or_stale",
        "blocked_router_decision_not_selected": "router_did_not_select_candidate",
        "blocked_missing_sizing_preview": "sizing_preview_missing_or_not_ready",
        "blocked_missing_handoff": "paper_oms_handoff_missing_or_not_ready",
        "blocked_missing_dry_run": "dry_run_identity_missing_or_not_ready",
        "blocked_missing_lifecycle_evidence": "v5_12_lifecycle_evidence_missing_or_invalid",
        "paper_read_reconciliation_required": "flat_state_requires_scoped_operator_read",
        "blocked": "operating_cycle_blocked",
    }[final_state]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_no_submit_operating_cycle_next_operator_action",
        "action": next_action,
        "final_state": final_state,
        "reason": reason,
        "selected_candidate_id": selected_candidate_id,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "paper_submit_currently_authorized": False,
        "broker_action_permitted": False,
        "prior_v5_8_authorization_status": "consumed_not_reusable",
        "prior_v5_10_authorization_status": "consumed_not_reusable",
        "prior_authorizations_reusable": False,
        "fresh_authorization_required_for_order": True,
        "blockers": list(blockers),
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }


def _cycle_blockers(
    *,
    final_state: FinalState,
    refresh_packet: Mapping[str, object],
    router_result: Mapping[str, object],
    sizing_preview_status: Mapping[str, object],
    paper_oms_handoff_status: Mapping[str, object],
    dry_run_identity_status: Mapping[str, object],
    autonomy_cadence_status: Mapping[str, object],
    stage_errors: Sequence[Mapping[str, object]],
) -> list[str]:
    blockers: list[str] = []
    for error in stage_errors:
        blockers.append(
            _first_nonempty(
                _first_text(error, "error"),
                _first_text(error, "error_type"),
                _first_text(error, "stage"),
            )
        )
    if final_state == "blocked_missing_router_inputs":
        summary = _mapping(refresh_packet.get("summary"))
        blockers.extend(_top_blocker_names(summary.get("top_blockers")))
        blockers.extend(_string_sequence(summary.get("blockers")))
    elif final_state == "blocked_router_decision_not_selected":
        blockers.extend(_string_sequence(router_result.get("blockers")))
        if not blockers:
            blockers.append("router_decision_not_selected")
    elif final_state == "blocked_missing_sizing_preview":
        blockers.extend(_string_sequence(sizing_preview_status.get("blockers")))
        if not blockers:
            blockers.append("sizing_preview_missing_or_not_ready")
    elif final_state == "blocked_missing_handoff":
        blockers.extend(_string_sequence(paper_oms_handoff_status.get("blockers")))
        if not blockers:
            blockers.append("paper_oms_handoff_missing_or_not_ready")
    elif final_state == "blocked_missing_dry_run":
        blockers.extend(_string_sequence(dry_run_identity_status.get("blockers")))
        if not blockers:
            blockers.append("paper_oms_dry_run_missing_or_not_ready")
    elif final_state == "blocked_missing_lifecycle_evidence":
        lifecycle = _mapping(autonomy_cadence_status.get("paper_lifecycle_evidence"))
        blockers.extend(_string_sequence(lifecycle.get("blockers")))
        blockers.extend(_string_sequence(autonomy_cadence_status.get("blockers")))
        if not blockers:
            blockers.append("lifecycle_evidence_missing_or_invalid")
    elif final_state == "paper_read_reconciliation_required":
        blockers.append("paper_read_reconciliation_required")
    elif final_state == "blocked":
        blockers.extend(_string_sequence(autonomy_cadence_status.get("blockers")))
        if not blockers:
            blockers.append("operating_cycle_blocked")
    return list(_dedupe(blockers))


def build_crypto_readiness_packet(
    *,
    refresh_packet: Mapping[str, object],
    router_result: Mapping[str, object],
    sizing_preview_status: Mapping[str, object],
    paper_oms_handoff_status: Mapping[str, object],
    dry_run_identity_status: Mapping[str, object],
    autonomy_cadence_status: Mapping[str, object],
    final_state: str,
    cycle_blockers: Sequence[str],
    selected_candidate_id: str,
    as_of: str,
) -> dict[str, object]:
    """Build the v5.15 local no-submit 24/7 crypto readiness packet."""

    summary = _mapping(refresh_packet.get("summary"))
    router_manifest = _mapping(refresh_packet.get("crypto_router_input_manifest"))
    history_manifest = _mapping(refresh_packet.get("crypto_history_manifest"))
    selected_candidate = _mapping(router_result.get("selected_candidate"))
    selected_symbol = _first_nonempty(
        _first_text(router_result, "selected_symbol"),
        _first_text(sizing_preview_status, "selected_symbol"),
        _first_text(paper_oms_handoff_status, "selected_symbol"),
        _first_text(selected_candidate, "symbol"),
        _candidate_symbol_from_id(selected_candidate_id),
    )
    candidate_symbols = _candidate_symbols(
        refresh_packet=refresh_packet,
        router_result=router_result,
        selected_symbol=selected_symbol,
    )
    source_mode = _first_nonempty(
        _first_text(summary, "source_mode"),
        _first_text(router_manifest, "source_mode"),
        _first_text(sizing_preview_status, "selected_backing"),
        "unknown",
    )
    broker_state_mode = _first_nonempty(
        _first_text(summary, "broker_state_mode"),
        _first_text(router_manifest, "broker_state_mode"),
        _first_text(selected_candidate, "broker_state_mode"),
    )
    broker_read_observed = _is_true(summary.get("broker_read_observed")) or _is_true(
        router_manifest.get("broker_read_observed")
    )
    evidence_classification = _crypto_evidence_classification(
        source_mode=source_mode,
        broker_state_mode=broker_state_mode,
        broker_read_observed=broker_read_observed,
    )
    history_record = _matching_symbol_record(
        history_manifest.get("records"),
        selected_symbol,
    )
    router_record = _matching_symbol_record(router_manifest.get("records"), selected_symbol)
    latest_price_value = _first_nonempty(
        _first_text(sizing_preview_status, "latest_price"),
        _first_text(paper_oms_handoff_status, "latest_price"),
        _first_text(dry_run_identity_status, "latest_price"),
        _latest_bar_close_text(refresh_packet, selected_symbol, as_of),
    )
    latest_price_observed_at = _first_nonempty(
        _first_text(history_record, "latest_timestamp"),
        _first_text(router_record, "latest_timestamp"),
        _latest_bar_timestamp_text(refresh_packet, selected_symbol, as_of),
    )
    latest_price_freshness = _first_nonempty(
        _first_text(history_record, "freshness_status"),
        _first_text(router_record, "freshness_status"),
        _first_text(selected_candidate, "freshness_status"),
        "unavailable",
    )
    latest_price_source = _latest_price_source_for_classification(evidence_classification)
    latest_price_basis = _latest_price_basis_for_source(source_mode, latest_price_source)
    latest_price_blocker = _latest_price_blocker(
        latest_price_value=latest_price_value,
        latest_price_observed_at=latest_price_observed_at,
        latest_price_freshness=latest_price_freshness,
    )
    bar_status = "passed" if latest_price_blocker == "none" else "blocked"
    source_table = [
        _latest_price_source_row(
            source_kind="quote",
            source="broker_observed_latest_quote",
            basis="broker_observed_latest_quote_mid",
            value="",
            observed_at="",
            freshness="unavailable",
            status="not_attempted",
            blocker="broker_read_not_authorized_for_no_submit_packet",
            selected=False,
        ),
        _latest_price_source_row(
            source_kind="trade",
            source="broker_observed_latest_trade",
            basis="broker_observed_latest_trade",
            value="",
            observed_at="",
            freshness="unavailable",
            status="not_attempted",
            blocker="broker_read_not_authorized_for_no_submit_packet",
            selected=False,
        ),
        _latest_price_source_row(
            source_kind="bar",
            source=latest_price_source,
            basis=latest_price_basis,
            value=latest_price_value,
            observed_at=latest_price_observed_at,
            freshness=latest_price_freshness,
            status=bar_status,
            blocker=latest_price_blocker,
            selected=True,
        ),
    ]
    readiness_decision, blocker_taxonomy, blocker = _crypto_readiness_decision(
        final_state=final_state,
        evidence_classification=evidence_classification,
        latest_price_blocker=latest_price_blocker,
        cycle_blockers=cycle_blockers,
    )
    next_safe_operator_action = _crypto_next_safe_operator_action(
        readiness_decision=readiness_decision,
        blocker_taxonomy=blocker_taxonomy,
    )
    payload = {
        "schema_version": CRYPTO_READINESS_PACKET_SCHEMA_VERSION,
        "record_type": "v5_15_crypto_no_submit_operating_packet",
        "operator_command": COMMAND_NAME,
        "as_of": as_of,
        "selected_candidate_id": selected_candidate_id,
        "selected_crypto_symbol": selected_symbol,
        "candidate_symbols": list(candidate_symbols),
        "source_mode": source_mode,
        "broker_state_mode": broker_state_mode,
        "broker_read_observed": broker_read_observed,
        "evidence_classification": evidence_classification,
        "fixture_or_local_replay_classification": evidence_classification,
        "latest_price_source": latest_price_source,
        "latest_price_source_selected": "bar",
        "latest_price_basis": latest_price_basis,
        "latest_price_final_selected_basis": latest_price_basis,
        "latest_price_value": latest_price_value,
        "latest_price_observed_at": latest_price_observed_at,
        "latest_price_normalized_timestamp": latest_price_observed_at,
        "latest_price_freshness_status": latest_price_freshness,
        "latest_price_final_blocker": latest_price_blocker,
        "latest_price_source_acceptability": (
            "accepted_for_no_submit_readiness_packet"
            if latest_price_blocker == "none"
            else "blocked_price_check_failed"
        ),
        "latest_price_source_table": source_table,
        "quote_trade_bar_fallback_diagnostics": {
            "selected_source": "bar",
            "sources_attempted": ["bar"],
            "quote_status": "not_attempted_no_broker_read",
            "trade_status": "not_attempted_no_broker_read",
            "bar_status": bar_status,
            "fallback_result": (
                f"{evidence_classification}_bar_selected"
                if latest_price_blocker == "none"
                else "bar_blocked"
            ),
        },
        "readiness_decision": readiness_decision,
        "blocker_taxonomy": blocker_taxonomy,
        "blocker": blocker,
        "cycle_final_state": final_state,
        "cycle_blockers": list(cycle_blockers),
        "stage_status": {
            "router_decision": _first_text(router_result, "router_decision", "decision"),
            "sizing_status": _first_text(sizing_preview_status, "sizing_status"),
            "handoff_status": _first_text(paper_oms_handoff_status, "handoff_status"),
            "dry_run_status": _first_text(dry_run_identity_status, "dry_run_status"),
            "cadence_status": _first_text(autonomy_cadence_status, "cadence_status"),
        },
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "paper_submit_currently_authorized": False,
        "broker_action_permitted": False,
        "fresh_authorization_required_for_order": True,
        "next_safe_operator_action": next_safe_operator_action,
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }
    validation_errors = validate_crypto_readiness_packet(payload)
    if validation_errors:
        payload["readiness_decision"] = "blocked_readiness_validation_failed"
        payload["blocker_taxonomy"] = "readiness_packet_validation"
        payload["blocker"] = "readiness_packet_validation_failed"
        payload["next_safe_operator_action"] = (
            "repair inconsistent crypto readiness packet fields before review; "
            "no broker action is authorized."
        )
    payload["validation_status"] = "failed" if validation_errors else "passed"
    payload["validation_errors"] = validation_errors
    return payload


def validate_crypto_readiness_packet(packet: Mapping[str, object]) -> list[str]:
    """Return deterministic v5.15 crypto readiness packet validation errors."""

    errors: list[str] = []
    source = _first_text(packet, "latest_price_source")
    basis = _first_text(packet, "latest_price_basis")
    final_basis = _first_text(packet, "latest_price_final_selected_basis")
    selected_source = _first_nonempty(
        _first_text(packet, "latest_price_source_selected"),
        _latest_price_source_kind(source),
    )
    freshness = _first_text(packet, "latest_price_freshness_status")
    observed_at = _first_text(packet, "latest_price_observed_at")
    normalized_timestamp = _first_text(packet, "latest_price_normalized_timestamp")
    blocker = _normalized_blocker(_first_text(packet, "blocker"))
    price_blocker = _normalized_blocker(_first_text(packet, "latest_price_final_blocker"))
    decision = _first_text(packet, "readiness_decision")
    classification = _first_text(packet, "evidence_classification")
    source_rows = list(_mapping_sequence(packet.get("latest_price_source_table")))

    if freshness == "fresh" and not observed_at:
        errors.append("crypto_latest_price_timestamp_missing_marked_fresh")
    if observed_at and normalized_timestamp and observed_at != normalized_timestamp:
        errors.append("crypto_latest_price_normalized_timestamp_mismatch")
    if final_basis and basis and final_basis != basis:
        errors.append("crypto_latest_price_final_basis_mismatch")
    if price_blocker != _expected_price_blocker(freshness, observed_at, packet):
        errors.append("crypto_latest_price_final_blocker_mismatch")
    if _blocker_present(price_blocker) and _blocker_present(blocker) and price_blocker != blocker:
        errors.append("crypto_readiness_blocker_price_blocker_mismatch")
    if selected_source == "bar" and "bar" not in basis:
        errors.append("crypto_latest_price_basis_source_mismatch")
    if selected_source == "quote" and "quote" not in basis:
        errors.append("crypto_latest_price_basis_source_mismatch")
    if selected_source == "trade" and "trade" not in basis:
        errors.append("crypto_latest_price_basis_source_mismatch")

    selected_rows = [
        row
        for row in source_rows
        if _is_true(row.get("selected"))
        or _first_text(row, "source_kind", "source") == selected_source
    ]
    if source_rows and not selected_rows:
        errors.append("crypto_latest_price_selected_source_missing_from_table")
    selected_freshness = freshness
    if selected_rows:
        selected_freshness = _first_nonempty(
            _first_text(selected_rows[0], "freshness"),
            selected_freshness,
        )
    for row in source_rows:
        row_freshness = _first_text(row, "freshness")
        row_observed_at = _first_text(row, "observed_at")
        if row_freshness == "fresh" and not row_observed_at:
            errors.append("crypto_latest_price_source_table_fresh_without_timestamp")
    any_fresher_fallback = any(
        not _is_true(row.get("selected"))
        and _first_text(row, "freshness") == "fresh"
        and _first_text(row, "status") == "passed"
        for row in source_rows
    )
    if selected_freshness != "fresh" and any_fresher_fallback:
        errors.append("crypto_latest_price_fresher_fallback_exists")
    if classification in {"fixture_replay", "offline_fixture"} and (
        "broker_observed_ready" in decision or source.startswith("broker_observed")
    ):
        errors.append("fixture_replay_mislabeled_broker_observed_ready")
    if classification != "broker_observed" and source.startswith("broker_observed"):
        errors.append("crypto_latest_price_source_classification_mismatch")
    if decision.startswith("broker_observed_ready") and not _is_true(
        packet.get("broker_read_observed")
    ):
        errors.append("broker_observed_ready_without_broker_read")
    if decision.endswith("_ready_no_submit") and _blocker_present(blocker):
        errors.append("crypto_readiness_ready_with_blocker")
    if decision.startswith("blocked") and not _blocker_present(blocker):
        errors.append("crypto_readiness_blocked_without_blocker")
    if freshness == "fresh" and _blocker_present(price_blocker):
        errors.append("crypto_latest_price_fresh_with_blocker")
    if freshness != "fresh" and not _blocker_present(price_blocker):
        errors.append("crypto_latest_price_not_fresh_without_blocker")
    return list(_dedupe(errors))


def _candidate_symbols(
    *,
    refresh_packet: Mapping[str, object],
    router_result: Mapping[str, object],
    selected_symbol: str,
) -> tuple[str, ...]:
    summary = _mapping(refresh_packet.get("summary"))
    manifest = _mapping(refresh_packet.get("crypto_router_input_manifest"))
    symbols: list[str] = []
    symbols.extend(_string_sequence(summary.get("eligible_input_symbols")))
    symbols.extend(_string_sequence(manifest.get("router_ready_symbols")))
    symbols.extend(_string_sequence(summary.get("symbols")))
    symbols.extend(_string_sequence(manifest.get("symbols")))
    symbols.append(_first_text(router_result, "selected_symbol"))
    symbols.append(selected_symbol)
    return _dedupe(_normalize_crypto_symbol_text(symbol) for symbol in symbols if symbol)


def _candidate_symbol_from_id(candidate_id: str) -> str:
    parts = candidate_id.split(":")
    if len(parts) >= 2 and parts[0] == "crypto":
        return parts[1]
    return ""


def _crypto_evidence_classification(
    *,
    source_mode: str,
    broker_state_mode: str,
    broker_read_observed: bool,
) -> str:
    if source_mode == "offline_fixture":
        return "fixture_replay"
    if source_mode == "local_replay":
        return "local_replay"
    if source_mode == "paper_read_only" and broker_read_observed:
        return "broker_observed"
    if "observed" in broker_state_mode and broker_read_observed:
        return "broker_observed"
    return "local_replay"


def _latest_price_source_for_classification(classification: str) -> str:
    return {
        "broker_observed": "broker_observed_latest_bar",
        "fixture_replay": "offline_fixture_latest_bar",
        "local_replay": "local_replay_latest_bar",
    }.get(classification, "local_replay_latest_bar")


def _latest_price_basis_for_source(source_mode: str, latest_price_source: str) -> str:
    if latest_price_source.startswith("broker_observed"):
        return "broker_observed_latest_bar_close"
    if source_mode == "offline_fixture":
        return "offline_fixture_latest_history_bar_close"
    if source_mode == "local_replay":
        return "local_replay_latest_history_bar_close"
    return f"{source_mode or 'unknown'}_latest_history_bar_close"


def _latest_price_blocker(
    *,
    latest_price_value: str,
    latest_price_observed_at: str,
    latest_price_freshness: str,
) -> str:
    if not latest_price_value:
        return "crypto_latest_price_missing"
    if not latest_price_observed_at:
        return "crypto_latest_price_timestamp_missing"
    if latest_price_freshness != "fresh":
        return "crypto_latest_price_stale"
    return "none"


def _crypto_readiness_decision(
    *,
    final_state: str,
    evidence_classification: str,
    latest_price_blocker: str,
    cycle_blockers: Sequence[str],
) -> tuple[str, str, str]:
    if final_state != "selected_candidate_no_submit_packet_ready":
        blocker = _first_nonempty(*_string_sequence(cycle_blockers), final_state)
        return "blocked_cycle_not_ready", "cycle_not_ready", blocker
    if latest_price_blocker != "none":
        taxonomy = (
            "latest_price_timestamp_missing"
            if latest_price_blocker == "crypto_latest_price_timestamp_missing"
            else "latest_price_missing_or_stale"
        )
        return "blocked_latest_price_not_fresh", taxonomy, latest_price_blocker
    if evidence_classification == "fixture_replay":
        return (
            "fixture_replay_preview_only",
            "fixture_replay_not_broker_observed",
            "fixture_replay_requires_real_local_or_broker_observed_refresh",
        )
    if evidence_classification == "broker_observed":
        return "broker_observed_ready_no_submit", "none", "none"
    return "local_replay_ready_no_submit", "none", "none"


def _crypto_next_safe_operator_action(
    *,
    readiness_decision: str,
    blocker_taxonomy: str,
) -> str:
    if readiness_decision == "local_replay_ready_no_submit":
        return (
            "review the local-replay no-submit packet; any order still requires "
            "fresh explicit operator authorization."
        )
    if readiness_decision == "broker_observed_ready_no_submit":
        return (
            "review the broker-observed no-submit packet; any order still requires "
            "fresh explicit operator authorization."
        )
    if readiness_decision == "fixture_replay_preview_only":
        return (
            "review fixture-only mechanics, then provide current local inputs or "
            "authorize a scoped read-only observation before treating readiness as current."
        )
    if blocker_taxonomy in {"latest_price_missing_or_stale", "latest_price_timestamp_missing"}:
        return (
            "provide fresher local crypto bars or authorize one scoped read-only "
            "market-data observation; no broker mutation or paper submit is authorized."
        )
    return "repair local no-submit inputs and rerun; no broker action is authorized."


def _latest_price_source_row(
    *,
    source_kind: str,
    source: str,
    basis: str,
    value: str,
    observed_at: str,
    freshness: str,
    status: str,
    blocker: str,
    selected: bool,
) -> dict[str, object]:
    return {
        "source_kind": source_kind,
        "source": source,
        "basis": basis,
        "value": value,
        "observed_at": observed_at,
        "freshness": freshness,
        "status": status,
        "blocker": blocker,
        "selected": selected,
    }


def _matching_symbol_record(value: object, symbol: str) -> Mapping[str, object]:
    normalized = _normalize_crypto_symbol_text(symbol)
    for record in _mapping_sequence(value):
        record_symbol = _first_text(record, "symbol", "selected_symbol")
        if record_symbol and _normalize_crypto_symbol_text(record_symbol) == normalized:
            return record
    return {}


def _latest_bar_close_text(
    refresh_packet: Mapping[str, object],
    symbol: str,
    as_of: str,
) -> str:
    bar = _latest_bar(refresh_packet, symbol, as_of)
    if bar is None:
        return ""
    close = getattr(bar, "close", None)
    if close is None and isinstance(bar, Mapping):
        close = _first_text(bar, "close", "c")
    return _text(close)


def _latest_bar_timestamp_text(
    refresh_packet: Mapping[str, object],
    symbol: str,
    as_of: str,
) -> str:
    bar = _latest_bar(refresh_packet, symbol, as_of)
    if bar is None:
        return ""
    timestamp = getattr(bar, "timestamp", None)
    if timestamp is None and isinstance(bar, Mapping):
        timestamp = _first_text(bar, "timestamp", "t", "datetime")
    parsed = _datetime_or_none(timestamp)
    return "" if parsed is None else parsed.isoformat()


def _latest_bar(
    refresh_packet: Mapping[str, object],
    symbol: str,
    as_of: str,
) -> object | None:
    normalized = _normalize_crypto_symbol_text(symbol)
    bars_by_symbol = refresh_packet.get("bars_by_symbol")
    if not isinstance(bars_by_symbol, Mapping):
        return None
    bars: object = ()
    for key, value in bars_by_symbol.items():
        if _normalize_crypto_symbol_text(key) == normalized:
            bars = value
            break
    if not isinstance(bars, Sequence) or isinstance(bars, (str, bytes)):
        return None
    as_of_dt = _datetime_or_none(as_of)
    usable: list[tuple[datetime, object]] = []
    for bar in bars:
        timestamp = getattr(bar, "timestamp", None)
        if timestamp is None and isinstance(bar, Mapping):
            timestamp = _first_text(bar, "timestamp", "t", "datetime")
        parsed = _datetime_or_none(timestamp)
        if parsed is None:
            continue
        if as_of_dt is not None and parsed > as_of_dt:
            continue
        usable.append((parsed, bar))
    if not usable:
        return None
    return max(usable, key=lambda item: item[0])[1]


def _expected_price_blocker(
    freshness: str,
    observed_at: str,
    packet: Mapping[str, object],
) -> str:
    if not _first_text(packet, "latest_price_value"):
        return "crypto_latest_price_missing"
    if not observed_at:
        return "crypto_latest_price_timestamp_missing"
    if freshness != "fresh":
        return "crypto_latest_price_stale"
    return "none"


def _latest_price_source_kind(source: str) -> str:
    if "quote" in source:
        return "quote"
    if "trade" in source:
        return "trade"
    if "bar" in source:
        return "bar"
    return ""


def _normalized_blocker(value: str) -> str:
    text = _text(value)
    return "none" if text in {"", "none"} else text


def _blocker_present(value: str) -> bool:
    return _normalized_blocker(value) != "none"


def _datetime_or_none(value: object) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _normalize_crypto_symbol_text(value: object) -> str:
    return "".join(ch for ch in _text(value).upper() if ch.isalnum())


def _operating_record(packet: Mapping[str, object]) -> dict[str, object]:
    status = _mapping(packet.get("cycle_status"))
    readiness = _mapping(packet.get("crypto_readiness_packet"))
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_no_submit_operating_cycle",
        "as_of": packet.get("as_of", ""),
        "final_state": status.get("final_state", ""),
        "next_operator_action": status.get("next_operator_action", ""),
        "selected_candidate_id": status.get("selected_candidate_id", ""),
        "stage_status": status.get("stage_status", {}),
        "prior_v5_8_authorization_status": "consumed_not_reusable",
        "prior_v5_10_authorization_status": "consumed_not_reusable",
        "prior_authorizations_reusable": False,
        "fresh_authorization_required_for_order": True,
        "crypto_readiness": {
            "readiness_decision": readiness.get("readiness_decision", ""),
            "blocker_taxonomy": readiness.get("blocker_taxonomy", ""),
            "blocker": readiness.get("blocker", ""),
            "evidence_classification": readiness.get("evidence_classification", ""),
            "latest_price_source": readiness.get("latest_price_source", ""),
            "latest_price_basis": readiness.get("latest_price_basis", ""),
            "latest_price_freshness_status": readiness.get(
                "latest_price_freshness_status",
                "",
            ),
        },
        "blockers": status.get("blockers", []),
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }


def _cycle_as_of(
    explicit: str,
    *payloads: Mapping[str, object],
) -> str:
    values = [explicit]
    values.extend(_first_text(payload, "as_of") for payload in payloads)
    return _first_nonempty(*values)


def _as_of_argument(value: datetime | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    return str(value).strip()


def _top_blocker_names(value: object) -> tuple[str, ...]:
    names: list[str] = []
    for item in _mapping_sequence(value):
        names.append(_first_text(item, "blocker"))
    return tuple(name for name in names if name)


def _merged_labels(value: object) -> tuple[str, ...]:
    return _dedupe((*_string_sequence(value), *REQUIRED_LABELS))


def _false_flags() -> dict[str, bool]:
    return {field_name: False for field_name in FALSE_SAFETY_FIELDS}


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


def _generated_under_runs(path: Path) -> bool:
    return "runs" in path.parts


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _mapping_sequence(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _string_sequence(value: object) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(item) for item in value if str(item).strip())
    if value in (None, ""):
        return ()
    return (str(value),)


def _first_text(row: Mapping[str, object], *field_names: str) -> str:
    wanted = {field_name.strip().lower() for field_name in field_names}
    for key, value in row.items():
        if str(key).strip().lower() in wanted:
            return _text(value)
    return ""


def _first_nonempty(*values: str) -> str:
    for value in values:
        if value:
            return value
    return ""


def _text(value: object) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "true" if value else "false"
    return str(value).strip()


def _is_true(value: object) -> bool:
    if type(value) is bool:
        return value
    return _text(value).lower() in {"true", "1", "yes"}


def _int_or_none(value: object) -> int | None:
    try:
        return int(_text(value))
    except ValueError:
        return None


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)


def _json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="crypto-no-submit-operating-cycle",
        description="Run the local no-submit crypto operating cycle.",
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--crypto-refresh-output-root",
        type=Path,
        default=DEFAULT_CRYPTO_REFRESH_OUTPUT_ROOT,
    )
    parser.add_argument("--router-output-root", type=Path, default=DEFAULT_ROUTER_OUTPUT_ROOT)
    parser.add_argument(
        "--sizing-preview-output-root",
        type=Path,
        default=DEFAULT_SIZING_PREVIEW_OUTPUT_ROOT,
    )
    parser.add_argument("--handoff-output-root", type=Path, default=DEFAULT_HANDOFF_OUTPUT_ROOT)
    parser.add_argument("--dry-run-output-root", type=Path, default=DEFAULT_DRY_RUN_OUTPUT_ROOT)
    parser.add_argument(
        "--autonomy-cadence-output-root",
        type=Path,
        default=DEFAULT_AUTONOMY_CADENCE_OUTPUT_ROOT,
    )
    parser.add_argument(
        "--refresh-mode",
        choices=("local_replay", "offline_fixture"),
        default="local_replay",
    )
    parser.add_argument("--bars-csv", type=Path, default=CRYPTO_UNIVERSE_REFRESH_DEFAULT_BARS_CSV)
    parser.add_argument(
        "--crypto-visibility-status",
        type=Path,
        default=CRYPTO_UNIVERSE_REFRESH_DEFAULT_VISIBILITY_STATUS,
    )
    parser.add_argument("--spy-bars-csv", type=Path, default=None)
    parser.add_argument(
        "--submit-cancel-result-path",
        type=Path,
        default=DEFAULT_SUBMIT_CANCEL_RESULT,
    )
    parser.add_argument(
        "--certification-ingestion-path",
        type=Path,
        default=DEFAULT_CERTIFICATION_INGESTION,
    )
    parser.add_argument("--fill-exit-result-path", type=Path, default=DEFAULT_FILL_EXIT_RESULT)
    parser.add_argument(
        "--fill-exit-ingestion-path",
        type=Path,
        default=DEFAULT_FILL_EXIT_INGESTION,
    )
    parser.add_argument(
        "--preview-notional-cap",
        default=str(CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_NOTIONAL_CAP),
    )
    parser.add_argument("--allow-fixture-backed", action="store_true")
    parser.add_argument("--as-of", default="")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    packet = run_crypto_no_submit_operating_cycle(
        output_root=args.output_root,
        crypto_refresh_output_root=args.crypto_refresh_output_root,
        router_output_root=args.router_output_root,
        sizing_preview_output_root=args.sizing_preview_output_root,
        handoff_output_root=args.handoff_output_root,
        dry_run_output_root=args.dry_run_output_root,
        autonomy_cadence_output_root=args.autonomy_cadence_output_root,
        refresh_mode=args.refresh_mode,
        bars_csv=args.bars_csv,
        crypto_visibility_status=args.crypto_visibility_status,
        spy_bars_csv=args.spy_bars_csv,
        submit_cancel_result_path=args.submit_cancel_result_path,
        certification_ingestion_path=args.certification_ingestion_path,
        fill_exit_result_path=args.fill_exit_result_path,
        fill_exit_ingestion_path=args.fill_exit_ingestion_path,
        preview_notional_cap=args.preview_notional_cap,
        allow_fixture_backed=args.allow_fixture_backed,
        as_of=args.as_of or None,
        write_artifacts=True,
    )
    if args.format == "json":
        print(json.dumps(_json_safe(packet), sort_keys=True))
    else:
        print(render_cycle_text(packet))
    final_state = _first_text(_mapping(packet.get("cycle_status")), "final_state")
    return 2 if final_state == "blocked" else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
