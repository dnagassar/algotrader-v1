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
CRYPTO_OBSERVED_LATEST_PRICE_MAX_AGE_SECONDS = 7200
FRESHNESS_EVALUATION_MODES = ("wall_clock", "deterministic_replay")

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
FreshnessEvaluationMode = Literal["wall_clock", "deterministic_replay"]

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
    "CRYPTO_OBSERVED_LATEST_PRICE_MAX_AGE_SECONDS",
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
    observed_latest_price_artifact_path: Path | str | None = None,
    freshness_evaluation_mode: FreshnessEvaluationMode | None = None,
    freshness_evaluated_at: datetime | str | None = None,
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
    observed_latest_price_artifact = _read_observed_latest_price_artifact(
        observed_latest_price_artifact_path
    )

    cycle_as_of = _cycle_as_of(
        as_of_value,
        dry_run_identity_status,
        handoff_status,
        sizing_preview_status,
        router_result,
        autonomy_cadence_status,
    )
    resolved_freshness_evaluation_mode = _resolve_freshness_evaluation_mode(
        freshness_evaluation_mode,
        explicit_as_of=bool(as_of_value),
    )
    resolved_freshness_evaluated_at = _resolve_freshness_evaluated_at(
        freshness_evaluated_at,
        mode=resolved_freshness_evaluation_mode,
        replay_basis=cycle_as_of,
    )

    packet = build_crypto_no_submit_operating_cycle_packet(
        refresh_packet=refresh_packet,
        router_result=router_result,
        sizing_preview_status=sizing_preview_status,
        paper_oms_handoff_status=handoff_status,
        dry_run_identity_status=dry_run_identity_status,
        autonomy_cadence_status=autonomy_cadence_status,
        observed_latest_price_artifact=observed_latest_price_artifact,
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
        as_of=cycle_as_of,
        freshness_evaluation_mode=resolved_freshness_evaluation_mode,
        freshness_evaluated_at=resolved_freshness_evaluated_at,
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
    observed_latest_price_artifact: Mapping[str, object] | None = None,
    stage_errors: Sequence[Mapping[str, object]] = (),
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
    stage_artifact_paths: Mapping[str, object] | None = None,
    as_of: str = "",
    freshness_evaluation_mode: FreshnessEvaluationMode | str | None = None,
    freshness_evaluated_at: datetime | str | None = None,
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
        observed_latest_price_artifact=observed_latest_price_artifact,
        final_state=final_state,
        cycle_blockers=blockers,
        selected_candidate_id=selected_candidate_id,
        as_of=as_of,
        freshness_evaluation_mode=freshness_evaluation_mode,
        freshness_evaluated_at=freshness_evaluated_at,
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
        "latest_price_observed_at": crypto_readiness_packet[
            "latest_price_observed_at"
        ],
        "latest_price_age_seconds": crypto_readiness_packet[
            "latest_price_age_seconds"
        ],
        "latest_price_freshness_threshold_seconds": crypto_readiness_packet[
            "latest_price_freshness_threshold_seconds"
        ],
        "latest_price_freshness_status": crypto_readiness_packet[
            "latest_price_freshness_status"
        ],
        "freshness_evaluated_at": crypto_readiness_packet["freshness_evaluated_at"],
        "freshness_evaluation_mode": crypto_readiness_packet[
            "freshness_evaluation_mode"
        ],
        "latest_price_age_basis": crypto_readiness_packet["latest_price_age_basis"],
        "operational_freshness_confirmed": crypto_readiness_packet[
            "operational_freshness_confirmed"
        ],
        "quote_trade_bar_fallback_diagnostics": crypto_readiness_packet[
            "quote_trade_bar_fallback_diagnostics"
        ],
        "observed_latest_price_artifact": crypto_readiness_packet[
            "observed_latest_price_artifact"
        ],
        "broker_observed_refresh_status": crypto_readiness_packet[
            "broker_observed_refresh_status"
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
            f"- latest price observed_at: `{readiness.get('latest_price_observed_at', '')}`",
            f"- latest price age seconds: `{readiness.get('latest_price_age_seconds', '')}`",
            f"- latest price freshness threshold seconds: `{readiness.get('latest_price_freshness_threshold_seconds', '')}`",
            f"- latest price freshness: `{readiness.get('latest_price_freshness_status', '')}`",
            f"- freshness evaluated_at: `{readiness.get('freshness_evaluated_at', '')}`",
            f"- freshness evaluation mode: `{readiness.get('freshness_evaluation_mode', '')}`",
            f"- latest price age basis: `{readiness.get('latest_price_age_basis', '')}`",
            f"- operational freshness confirmed: `{_bool_text(readiness.get('operational_freshness_confirmed'))}`",
            f"- broker observed refresh status: `{readiness.get('broker_observed_refresh_status', '')}`",
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
        f"latest_price_observed_at={_text(readiness.get('latest_price_observed_at'))}",
        f"latest_price_age_seconds={_text(readiness.get('latest_price_age_seconds'))}",
        "latest_price_freshness_threshold_seconds="
        + _text(readiness.get("latest_price_freshness_threshold_seconds")),
        f"latest_price_freshness_status={_text(readiness.get('latest_price_freshness_status'))}",
        f"freshness_evaluated_at={_text(readiness.get('freshness_evaluated_at'))}",
        f"freshness_evaluation_mode={_text(readiness.get('freshness_evaluation_mode'))}",
        f"latest_price_age_basis={_text(readiness.get('latest_price_age_basis'))}",
        "operational_freshness_confirmed="
        + _bool_text(readiness.get("operational_freshness_confirmed")),
        f"broker_observed_refresh_status={_text(readiness.get('broker_observed_refresh_status'))}",
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
    observed_latest_price_artifact: Mapping[str, object] | None,
    final_state: str,
    cycle_blockers: Sequence[str],
    selected_candidate_id: str,
    as_of: str,
    freshness_evaluation_mode: FreshnessEvaluationMode | str | None = None,
    freshness_evaluated_at: datetime | str | None = None,
) -> dict[str, object]:
    """Build the v5.15 local no-submit 24/7 crypto readiness packet."""

    freshness_mode = _resolve_freshness_evaluation_mode(
        freshness_evaluation_mode,
        explicit_as_of=True,
    )
    freshness_evaluated_at_text = _resolve_freshness_evaluated_at(
        freshness_evaluated_at,
        mode=freshness_mode,
        replay_basis=as_of,
    )
    latest_price_age_basis = _latest_price_age_basis(freshness_mode)

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
    base_evidence_classification = _crypto_evidence_classification(
        source_mode=source_mode,
        broker_state_mode=broker_state_mode,
        broker_read_observed=broker_read_observed,
    )
    history_record = _matching_symbol_record(
        history_manifest.get("records"),
        selected_symbol,
    )
    router_record = _matching_symbol_record(router_manifest.get("records"), selected_symbol)
    local_latest_price_value = _first_nonempty(
        _first_text(sizing_preview_status, "latest_price"),
        _first_text(paper_oms_handoff_status, "latest_price"),
        _first_text(dry_run_identity_status, "latest_price"),
        _latest_bar_close_text(refresh_packet, selected_symbol, as_of),
    )
    local_latest_price_observed_at = _first_nonempty(
        _first_text(history_record, "latest_timestamp"),
        _first_text(router_record, "latest_timestamp"),
        _latest_bar_timestamp_text(refresh_packet, selected_symbol, as_of),
    )
    local_latest_price_freshness = _first_nonempty(
        _first_text(history_record, "freshness_status"),
        _first_text(router_record, "freshness_status"),
        _first_text(selected_candidate, "freshness_status"),
        "unavailable",
    )
    local_latest_price_source = _latest_price_source_for_classification(
        base_evidence_classification
    )
    local_latest_price_basis = _latest_price_basis_for_source(
        source_mode,
        local_latest_price_source,
    )
    local_latest_price_blocker = _latest_price_blocker(
        latest_price_value=local_latest_price_value,
        latest_price_observed_at=local_latest_price_observed_at,
        latest_price_freshness=local_latest_price_freshness,
    )
    local_latest_price_age = _age_seconds_text(
        local_latest_price_observed_at,
        freshness_evaluated_at_text,
    )
    observed_evidence = _observed_latest_price_evidence(
        artifact=observed_latest_price_artifact,
        selected_symbol=selected_symbol,
        as_of=as_of,
        freshness_evaluation_mode=freshness_mode,
        freshness_evaluated_at=freshness_evaluated_at_text,
    )
    if _is_true(observed_evidence.get("configured")):
        evidence_classification = _first_text(
            observed_evidence,
            "evidence_classification",
        )
        latest_price_source = _first_text(observed_evidence, "latest_price_source")
        latest_price_basis = _first_text(observed_evidence, "latest_price_basis")
        latest_price_source_selected = _first_text(
            observed_evidence,
            "latest_price_source_selected",
        )
        latest_price_value = _first_text(observed_evidence, "latest_price_value")
        latest_price_observed_at = _first_text(
            observed_evidence,
            "latest_price_observed_at",
        )
        latest_price_age_seconds = _first_text(
            observed_evidence,
            "latest_price_age_seconds",
        )
        latest_price_freshness = _first_text(
            observed_evidence,
            "latest_price_freshness_status",
        )
        latest_price_blocker = _normalized_blocker(
            _first_text(observed_evidence, "latest_price_final_blocker")
        )
        source_table = list(
            _mapping_sequence(observed_evidence.get("latest_price_source_table"))
        )
        fallback_diagnostics = dict(
            _mapping(observed_evidence.get("quote_trade_bar_fallback_diagnostics"))
        )
        observed_artifact_summary = dict(
            _mapping(observed_evidence.get("observed_latest_price_artifact"))
        )
    else:
        evidence_classification = base_evidence_classification
        latest_price_source = local_latest_price_source
        latest_price_basis = local_latest_price_basis
        latest_price_source_selected = "bar"
        latest_price_value = local_latest_price_value
        latest_price_observed_at = local_latest_price_observed_at
        latest_price_age_seconds = local_latest_price_age
        latest_price_freshness = local_latest_price_freshness
        latest_price_blocker = local_latest_price_blocker
        bar_status = "passed" if latest_price_blocker == "none" else "blocked"
        source_table = [
            _latest_price_source_row(
                source_kind="quote",
                source="broker_observed_latest_quote",
                basis="broker_observed_latest_quote_mid",
                value="",
                observed_at="",
                age_seconds="",
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
                age_seconds="",
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
                age_seconds=latest_price_age_seconds,
                freshness=latest_price_freshness,
                status=bar_status,
                blocker=latest_price_blocker,
                selected=True,
            ),
        ]
        fallback_diagnostics = {
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
        }
        observed_artifact_summary = dict(
            _mapping(observed_evidence.get("observed_latest_price_artifact"))
        )
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
    operational_freshness_confirmed = (
        freshness_mode == "wall_clock"
        and latest_price_freshness == "fresh"
        and latest_price_blocker == "none"
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
        "source_artifact_broker_read_observed": _is_true(
            observed_artifact_summary.get("source_artifact_broker_read_occurred")
        ),
        "evidence_classification": evidence_classification,
        "fixture_or_local_replay_classification": evidence_classification,
        "latest_price_source": latest_price_source,
        "latest_price_source_selected": latest_price_source_selected,
        "latest_price_basis": latest_price_basis,
        "latest_price_final_selected_basis": latest_price_basis,
        "latest_price_value": latest_price_value,
        "latest_price_observed_at": latest_price_observed_at,
        "latest_price_normalized_timestamp": latest_price_observed_at,
        "latest_price_age_seconds": latest_price_age_seconds,
        "latest_price_freshness_threshold_seconds": str(
            CRYPTO_OBSERVED_LATEST_PRICE_MAX_AGE_SECONDS
        ),
        "latest_price_freshness_status": latest_price_freshness,
        "freshness_evaluated_at": freshness_evaluated_at_text,
        "freshness_evaluation_mode": freshness_mode,
        "latest_price_age_basis": latest_price_age_basis,
        "operational_freshness_confirmed": operational_freshness_confirmed,
        "latest_price_final_blocker": latest_price_blocker,
        "latest_price_source_acceptability": (
            "accepted_for_no_submit_readiness_packet"
            if latest_price_blocker == "none"
            else "blocked_price_check_failed"
        ),
        "latest_price_source_table": source_table,
        "quote_trade_bar_fallback_diagnostics": fallback_diagnostics,
        "observed_latest_price_artifact": observed_artifact_summary,
        "broker_observed_refresh_status": _first_text(
            observed_artifact_summary,
            "broker_observed_refresh_status",
        ),
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
        payload["operational_freshness_confirmed"] = False
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
    age_seconds = _first_text(packet, "latest_price_age_seconds")
    threshold_seconds = _first_text(packet, "latest_price_freshness_threshold_seconds")
    freshness_evaluated_at = _first_text(packet, "freshness_evaluated_at")
    freshness_evaluation_mode = _first_text(packet, "freshness_evaluation_mode")
    latest_price_age_basis = _first_text(packet, "latest_price_age_basis")
    blocker = _normalized_blocker(_first_text(packet, "blocker"))
    price_blocker = _normalized_blocker(_first_text(packet, "latest_price_final_blocker"))
    decision = _first_text(packet, "readiness_decision")
    classification = _first_text(packet, "evidence_classification")
    source_rows = list(_mapping_sequence(packet.get("latest_price_source_table")))
    packet_as_of = _first_text(packet, "as_of")
    expected_age_seconds = _age_seconds_text(observed_at, freshness_evaluated_at)
    expected_age_basis = _latest_price_age_basis(freshness_evaluation_mode)
    computed_age = _decimal_or_none(expected_age_seconds)
    threshold = _decimal_or_none(threshold_seconds)
    computed_freshness = ""
    if computed_age is not None and threshold is not None:
        computed_freshness = "fresh" if Decimal("0") <= computed_age <= threshold else "stale"
    operational_freshness_confirmed = _is_true(
        packet.get("operational_freshness_confirmed")
    )
    expected_operational_freshness_confirmed = (
        freshness_evaluation_mode == "wall_clock"
        and freshness == "fresh"
        and price_blocker == "none"
    )

    if not freshness_evaluated_at:
        errors.append("crypto_freshness_evaluated_at_missing")
    elif _datetime_or_none(freshness_evaluated_at) is None:
        errors.append("crypto_freshness_evaluated_at_invalid")
    if not freshness_evaluation_mode:
        errors.append("crypto_freshness_evaluation_mode_missing")
    elif freshness_evaluation_mode not in FRESHNESS_EVALUATION_MODES:
        errors.append("crypto_freshness_evaluation_mode_invalid")
    if not latest_price_age_basis:
        errors.append("crypto_latest_price_age_basis_missing")
    elif (
        expected_age_basis != "unknown_freshness_evaluation_mode"
        and latest_price_age_basis != expected_age_basis
    ):
        errors.append("crypto_latest_price_age_basis_mismatch")
    if "operational_freshness_confirmed" not in packet:
        errors.append("crypto_operational_freshness_confirmed_missing")
    if (
        freshness_evaluation_mode == "deterministic_replay"
        and operational_freshness_confirmed
    ):
        errors.append("crypto_deterministic_replay_operational_freshness_confirmed")
    if (
        freshness_evaluation_mode in FRESHNESS_EVALUATION_MODES
        and "operational_freshness_confirmed" in packet
        and operational_freshness_confirmed != expected_operational_freshness_confirmed
    ):
        errors.append("crypto_operational_freshness_confirmed_mismatch")
    if (
        freshness_evaluation_mode == "deterministic_replay"
        and packet_as_of
        and freshness_evaluated_at
        and freshness_evaluated_at != packet_as_of
    ):
        errors.append("crypto_deterministic_replay_freshness_evaluated_at_mismatch")
    if observed_at and freshness_evaluated_at and expected_age_seconds:
        if not age_seconds:
            errors.append("crypto_latest_price_age_seconds_missing")
        elif age_seconds != expected_age_seconds:
            errors.append("crypto_latest_price_age_seconds_mismatch")
    if computed_freshness and freshness == "fresh" and computed_freshness != "fresh":
        errors.append("crypto_latest_price_freshness_status_mismatch")
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
        selected_age_seconds = _first_text(selected_rows[0], "age_seconds")
        if age_seconds and selected_age_seconds and selected_age_seconds != age_seconds:
            errors.append("crypto_latest_price_source_table_age_seconds_mismatch")
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
    if classification == "local_observed_artifact_replay" and not source.startswith(
        "local_observed_artifact"
    ):
        errors.append("crypto_observed_artifact_source_classification_mismatch")
    if classification == "local_observed_artifact_replay":
        expected_refresh_status = _local_observed_artifact_refresh_status(
            freshness_evaluation_mode
        )
        actual_refresh_status = _first_text(packet, "broker_observed_refresh_status")
        if (
            freshness_evaluation_mode in FRESHNESS_EVALUATION_MODES
            and actual_refresh_status
            and actual_refresh_status != expected_refresh_status
        ):
            errors.append("crypto_observed_artifact_refresh_status_mode_mismatch")
    observed_artifact = _mapping(packet.get("observed_latest_price_artifact"))
    if (
        decision == "local_observed_artifact_ready_no_submit"
        and _first_text(observed_artifact, "status") != "accepted"
    ):
        errors.append("local_observed_artifact_ready_without_accepted_artifact")
    if decision.startswith("broker_observed_ready") and not _is_true(
        packet.get("broker_read_observed")
    ):
        errors.append("broker_observed_ready_without_broker_read")
    if decision.endswith("_ready_no_submit") and _blocker_present(blocker):
        errors.append("crypto_readiness_ready_with_blocker")
    if decision == "local_observed_artifact_ready_no_submit":
        if (
            freshness_evaluation_mode == "wall_clock"
            and computed_freshness
            and computed_freshness != "fresh"
        ):
            errors.append("local_observed_artifact_ready_with_stale_wall_clock_freshness")
        if (
            freshness_evaluation_mode == "wall_clock"
            and not operational_freshness_confirmed
        ):
            errors.append("local_observed_artifact_ready_without_operational_freshness")
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
            if latest_price_blocker
            in {
                "crypto_latest_price_timestamp_missing",
                "crypto_observed_latest_price_timestamp_missing",
            }
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
    if evidence_classification == "local_observed_artifact_replay":
        return "local_observed_artifact_ready_no_submit", "none", "none"
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
    if readiness_decision == "local_observed_artifact_ready_no_submit":
        return (
            "review the local observed-artifact no-submit packet; any order still "
            "requires fresh explicit operator authorization."
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
    age_seconds: str = "",
) -> dict[str, object]:
    return {
        "source_kind": source_kind,
        "source": source,
        "basis": basis,
        "value": value,
        "observed_at": observed_at,
        "age_seconds": age_seconds,
        "freshness": freshness,
        "status": status,
        "blocker": blocker,
        "selected": selected,
    }


def _read_observed_latest_price_artifact(path: Path | str | None) -> dict[str, object]:
    if path in (None, ""):
        return {
            "configured": False,
            "path": "",
            "status": "not_configured",
            "blocker": "broker_read_not_configured",
        }
    artifact_path = Path(path)
    if not artifact_path.is_file():
        return {
            "configured": True,
            "path": str(artifact_path),
            "status": "missing",
            "blocker": "crypto_observed_latest_price_artifact_missing",
        }
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "configured": True,
            "path": str(artifact_path),
            "status": "invalid_schema",
            "blocker": "crypto_observed_latest_price_artifact_invalid",
        }
    if not isinstance(payload, Mapping):
        return {
            "configured": True,
            "path": str(artifact_path),
            "status": "invalid_schema",
            "blocker": "crypto_observed_latest_price_artifact_invalid",
        }
    return {
        "configured": True,
        "path": str(artifact_path),
        "status": "loaded",
        "blocker": "none",
        "record_type": _first_text(payload, "record_type"),
        "payload": payload,
    }


def _observed_latest_price_evidence(
    *,
    artifact: Mapping[str, object] | None,
    selected_symbol: str,
    as_of: str,
    freshness_evaluation_mode: str,
    freshness_evaluated_at: str,
) -> dict[str, object]:
    source_artifact = _mapping(artifact)
    configured = _is_true(source_artifact.get("configured"))
    if not configured:
        return {
            "configured": False,
            "observed_latest_price_artifact": _observed_artifact_summary(
                source_artifact,
                status="not_configured",
                blocker="broker_read_not_configured",
                freshness_evaluation_mode=freshness_evaluation_mode,
            ),
        }

    payload = _mapping(source_artifact.get("payload"))
    if not payload:
        blocker = _first_nonempty(
            _first_text(source_artifact, "blocker"),
            "crypto_observed_latest_price_missing",
        )
        return _blocked_observed_latest_price_evidence(
            source_artifact=source_artifact,
            selected_symbol=selected_symbol,
            as_of=as_of,
            blocker=blocker,
            freshness_evaluation_mode=freshness_evaluation_mode,
        )

    price_payload = _observed_latest_price_payload(payload)
    source_symbol = _first_nonempty(
        _first_text(payload, "selected_crypto_symbol", "selected_symbol", "symbol"),
        _first_text(price_payload, "latest_price_symbol_internal", "latest_price_symbol"),
    )
    source_kind = _first_nonempty(
        _first_text(price_payload, "latest_price_source_selected"),
        _latest_price_source_kind(_first_text(price_payload, "latest_price_basis", "basis")),
        "bar",
    )
    source = _first_text(price_payload, "latest_price_source", "source")
    basis = _first_nonempty(
        _first_text(price_payload, "latest_price_basis", "basis"),
        f"local_observed_artifact_latest_{source_kind}",
    )
    value = _first_nonempty(
        _first_text(price_payload, "latest_price_value", "latest_price"),
        _first_text(payload, "latest_price_value", "latest_price"),
    )
    observed_at = _first_nonempty(
        _first_text(
            price_payload,
            "latest_price_observed_at",
            "latest_price_normalized_timestamp",
            "timestamp",
            "observed_at",
        ),
        _first_text(payload, "latest_price_observed_at", "latest_price_normalized_timestamp"),
    )
    blocker = _observed_latest_price_safety_blocker(payload)
    if not blocker and _normalize_crypto_symbol_text(source_symbol) != _normalize_crypto_symbol_text(
        selected_symbol
    ):
        blocker = "crypto_observed_latest_price_symbol_mismatch"
    if not blocker and source not in {
        "broker_observed",
        "provider_observed",
        "local_observed",
    }:
        blocker = "crypto_observed_latest_price_unacceptable_source"

    computed_freshness, freshness_blocker, age_seconds = _observed_price_freshness(
        latest_price_value=value,
        observed_at=observed_at,
        as_of=freshness_evaluated_at,
    )
    price_status = _first_text(price_payload, "price_evidence_status", "status")
    price_blocker = _normalized_blocker(
        _first_text(
            price_payload,
            "price_evidence_blocker",
            "latest_price_final_blocker",
            "blocker_code",
            "blocker",
        )
    )
    if not blocker and price_status == "blocked" and _blocker_present(price_blocker):
        blocker = _observed_price_blocker_from_source_blocker(price_blocker)
    if not blocker:
        blocker = freshness_blocker

    final_blocker = _normalized_blocker(blocker)
    freshness = computed_freshness
    status = "passed" if final_blocker == "none" else "blocked"
    top_level_source = f"local_observed_artifact_latest_{source_kind}"
    source_table = _observed_latest_price_source_table(
        price_payload=price_payload,
        selected_source=source_kind,
        selected_value=value,
        selected_observed_at=observed_at,
        selected_age_seconds=age_seconds,
        selected_freshness=freshness,
        selected_status=status,
        selected_blocker=final_blocker,
    )
    diagnostics = _observed_fallback_diagnostics(
        price_payload=price_payload,
        source_table=source_table,
        selected_source=source_kind,
        selected_blocker=final_blocker,
    )
    observed_summary = _observed_artifact_summary(
        source_artifact,
        status="accepted" if final_blocker == "none" else "blocked",
        blocker=final_blocker,
        payload=payload,
        source_payload=price_payload,
        freshness_evaluation_mode=freshness_evaluation_mode,
    )
    return {
        "configured": True,
        "evidence_classification": "local_observed_artifact_replay",
        "latest_price_source": top_level_source,
        "latest_price_source_selected": source_kind,
        "latest_price_basis": basis,
        "latest_price_value": value,
        "latest_price_observed_at": observed_at,
        "latest_price_age_seconds": age_seconds,
        "latest_price_freshness_status": freshness,
        "latest_price_final_blocker": final_blocker,
        "latest_price_source_table": source_table,
        "quote_trade_bar_fallback_diagnostics": diagnostics,
        "observed_latest_price_artifact": observed_summary,
    }


def _blocked_observed_latest_price_evidence(
    *,
    source_artifact: Mapping[str, object],
    selected_symbol: str,
    as_of: str,
    blocker: str,
    freshness_evaluation_mode: str,
) -> dict[str, object]:
    normalized_blocker = _normalized_blocker(blocker)
    if normalized_blocker in {
        "crypto_observed_latest_price_artifact_missing",
        "crypto_observed_latest_price_artifact_invalid",
    }:
        normalized_blocker = "crypto_observed_latest_price_missing"
    observed_summary = _observed_artifact_summary(
        source_artifact,
        status="blocked",
        blocker=normalized_blocker,
        freshness_evaluation_mode=freshness_evaluation_mode,
    )
    rows = [
        _latest_price_source_row(
            source_kind=kind,
            source=f"local_observed_artifact_latest_{kind}",
            basis=f"local_observed_artifact_latest_{kind}",
            value="",
            observed_at="",
            age_seconds="",
            freshness="unavailable",
            status="blocked" if kind == "quote" else "not_attempted",
            blocker=normalized_blocker if kind == "quote" else "not_attempted",
            selected=kind == "quote",
        )
        for kind in ("quote", "trade", "bar")
    ]
    return {
        "configured": True,
        "evidence_classification": "local_observed_artifact_replay",
        "latest_price_source": "local_observed_artifact_latest_quote",
        "latest_price_source_selected": "quote",
        "latest_price_basis": "local_observed_artifact_latest_quote",
        "latest_price_value": "",
        "latest_price_observed_at": "",
        "latest_price_age_seconds": "",
        "latest_price_freshness_status": "unavailable",
        "latest_price_final_blocker": normalized_blocker,
        "latest_price_source_table": rows,
        "quote_trade_bar_fallback_diagnostics": {
            "selected_source": "quote",
            "sources_attempted": [],
            "quote_status": "blocked",
            "trade_status": "not_attempted",
            "bar_status": "not_attempted",
            "fallback_result": "observed_artifact_blocked",
        },
        "observed_latest_price_artifact": {
            **observed_summary,
            "selected_symbol": selected_symbol,
            "as_of": as_of,
        },
    }


def _observed_latest_price_payload(payload: Mapping[str, object]) -> Mapping[str, object]:
    for key in (
        "broker_observed_price_freshness_check",
        "observed_latest_price_basis",
        "latest_price_evidence",
    ):
        nested = _mapping(payload.get(key))
        if nested:
            return {**dict(payload), **dict(nested)}
    return payload


def _observed_artifact_summary(
    source_artifact: Mapping[str, object],
    *,
    status: str,
    blocker: str,
    payload: Mapping[str, object] | None = None,
    source_payload: Mapping[str, object] | None = None,
    freshness_evaluation_mode: str = "",
) -> dict[str, object]:
    payload_map = _mapping(payload)
    source_map = _mapping(source_payload)
    return {
        "configured": _is_true(source_artifact.get("configured")),
        "path": _first_text(source_artifact, "path"),
        "status": status,
        "blocker": _normalized_blocker(blocker),
        "record_type": _first_nonempty(
            _first_text(source_artifact, "record_type"),
            _first_text(payload_map, "record_type"),
        ),
        "source_artifact_decision": _first_text(
            payload_map,
            "broker_observed_readiness_decision",
            "readiness_decision",
            "final_readiness_decision",
        ),
        "source_artifact_latest_price_source": _first_text(
            source_map,
            "latest_price_source",
            "source",
        ),
        "source_artifact_broker_read_occurred": _is_true(
            payload_map.get("broker_read_occurred")
        ),
        "source_artifact_network_used": _is_true(payload_map.get("network_used")),
        "source_artifact_live_endpoint_touched": _is_true(
            payload_map.get("live_endpoint_touched")
        ),
        "source_artifact_paper_submit_occurred": _is_true(
            payload_map.get("paper_submit_occurred")
        ),
        "source_artifact_broker_mutation_occurred": _is_true(
            payload_map.get("broker_mutation_occurred")
        ),
        "current_cycle_broker_read_occurred": False,
        "broker_observed_refresh_status": (
            "broker_read_not_configured"
            if not _is_true(source_artifact.get("configured"))
            else _local_observed_artifact_refresh_status(freshness_evaluation_mode)
        ),
    }


def _observed_latest_price_safety_blocker(payload: Mapping[str, object]) -> str:
    if _is_true(payload.get("paper_submit_occurred")):
        return "crypto_observed_latest_price_artifact_safety_violation"
    if _is_true(payload.get("broker_mutation_occurred")):
        return "crypto_observed_latest_price_artifact_safety_violation"
    if _is_true(payload.get("live_endpoint_touched")):
        return "crypto_observed_latest_price_artifact_live_endpoint"
    if _is_true(payload.get("credential_values_exposed")):
        return "crypto_observed_latest_price_artifact_safety_violation"
    return ""


def _observed_price_freshness(
    *,
    latest_price_value: str,
    observed_at: str,
    as_of: str,
) -> tuple[str, str, str]:
    if _positive_decimal_or_none(latest_price_value) is None:
        return "unavailable", "crypto_observed_latest_price_missing", ""
    observed_dt = _datetime_or_none(observed_at)
    if observed_dt is None:
        return (
            "missing_timestamp",
            "crypto_observed_latest_price_timestamp_missing",
            "",
        )
    as_of_dt = _datetime_or_none(as_of)
    if as_of_dt is None:
        return (
            "missing_timestamp",
            "crypto_observed_latest_price_timestamp_missing",
            "",
        )
    age_seconds = (as_of_dt - observed_dt).total_seconds()
    age_text = _seconds_text(age_seconds)
    if age_seconds < 0 or age_seconds > CRYPTO_OBSERVED_LATEST_PRICE_MAX_AGE_SECONDS:
        return "stale", "crypto_observed_latest_price_stale", age_text
    return "fresh", "none", age_text


def _positive_decimal_or_none(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except Exception:
        return None
    if not parsed.is_finite() or parsed <= Decimal("0"):
        return None
    return parsed


def _decimal_or_none(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except Exception:
        return None
    if not parsed.is_finite():
        return None
    return parsed


def _observed_price_blocker_from_source_blocker(blocker: str) -> str:
    normalized = _normalized_blocker(blocker)
    if normalized in {
        "broker_latest_quote_timestamp_missing",
        "broker_latest_trade_timestamp_missing",
        "broker_latest_bar_timestamp_missing",
        "broker_latest_price_timestamp_missing",
    }:
        return "crypto_observed_latest_price_timestamp_missing"
    if normalized in {
        "broker_latest_quote_stale",
        "broker_latest_trade_stale",
        "broker_latest_bar_stale",
        "broker_latest_price_stale",
        "broker_latest_price_all_sources_stale",
    }:
        return "crypto_observed_latest_price_stale"
    if normalized in {
        "broker_latest_price_missing",
        "broker_latest_price_all_sources_unavailable",
    }:
        return "crypto_observed_latest_price_missing"
    return normalized


def _observed_latest_price_source_table(
    *,
    price_payload: Mapping[str, object],
    selected_source: str,
    selected_value: str,
    selected_observed_at: str,
    selected_age_seconds: str,
    selected_freshness: str,
    selected_status: str,
    selected_blocker: str,
) -> list[dict[str, object]]:
    raw_rows = _mapping_sequence(price_payload.get("latest_price_source_table"))
    rows: list[dict[str, object]] = []
    for kind in ("quote", "trade", "bar"):
        raw = _source_row_for_kind(raw_rows, kind)
        if raw:
            raw_blocker = _normalized_blocker(_first_text(raw, "blocker"))
            raw_status = _first_nonempty(_first_text(raw, "status"), "unavailable")
            rows.append(
                _latest_price_source_row(
                    source_kind=kind,
                    source=_observed_source_name(kind),
                    basis=_first_nonempty(
                        _first_text(raw, "basis"),
                        _first_text(price_payload, "latest_price_basis", "basis"),
                    ),
                    value=_first_text(raw, "value"),
                    observed_at=_first_text(raw, "observed_at"),
                    age_seconds=_first_text(raw, "age_seconds"),
                    freshness=_first_nonempty(
                        _first_text(raw, "freshness"),
                        "unavailable",
                    ),
                    status=raw_status,
                    blocker=raw_blocker,
                    selected=kind == selected_source,
                )
            )
            continue
        rows.append(
            _latest_price_source_row(
                source_kind=kind,
                source=_observed_source_name(kind),
                basis=_observed_source_name(kind),
                value="",
                observed_at="",
                age_seconds="",
                freshness="unavailable",
                status="unavailable",
                blocker="not_available_in_observed_artifact",
                selected=kind == selected_source,
            )
        )

    selected_rows = [row for row in rows if _is_true(row.get("selected"))]
    if selected_rows:
        selected_rows[0].update(
            {
                "value": selected_value,
                "observed_at": selected_observed_at,
                "age_seconds": selected_age_seconds,
                "freshness": selected_freshness,
                "status": selected_status,
                "blocker": selected_blocker,
            }
        )
    return rows


def _source_row_for_kind(
    rows: Sequence[Mapping[str, object]],
    kind: str,
) -> Mapping[str, object]:
    for row in rows:
        source_text = _first_nonempty(
            _first_text(row, "source_kind"),
            _first_text(row, "source"),
            _first_text(row, "basis"),
        )
        if kind in source_text.lower():
            return row
    return {}


def _observed_source_name(kind: str) -> str:
    return f"local_observed_artifact_latest_{kind}"


def _observed_fallback_diagnostics(
    *,
    price_payload: Mapping[str, object],
    source_table: Sequence[Mapping[str, object]],
    selected_source: str,
    selected_blocker: str,
) -> dict[str, object]:
    status_by_kind = {
        _first_text(row, "source_kind"): _first_text(row, "status")
        for row in source_table
    }
    attempted = [
        _first_text(row, "source_kind")
        for row in source_table
        if _first_text(row, "status") not in {"", "unavailable", "not_attempted"}
    ]
    fallback_result = _first_nonempty(
        _first_text(price_payload, "latest_price_fallback_source_result"),
        f"local_observed_artifact_{selected_source}_selected"
        if selected_blocker == "none"
        else "observed_artifact_blocked",
    )
    return {
        "selected_source": selected_source,
        "sources_attempted": attempted,
        "quote_status": status_by_kind.get("quote", "unavailable"),
        "trade_status": status_by_kind.get("trade", "unavailable"),
        "bar_status": status_by_kind.get("bar", "unavailable"),
        "fallback_result": fallback_result,
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


def _age_seconds_text(observed_at: object, as_of: object) -> str:
    observed = _datetime_or_none(observed_at)
    evaluated = _datetime_or_none(as_of)
    if observed is None or evaluated is None:
        return ""
    return _seconds_text((evaluated - observed).total_seconds())


def _seconds_text(seconds: float) -> str:
    if seconds == int(seconds):
        return str(int(seconds))
    return format(Decimal(str(seconds)).quantize(Decimal("0.001")).normalize(), "f")


def _expected_price_blocker(
    freshness: str,
    observed_at: str,
    packet: Mapping[str, object],
) -> str:
    observed_artifact = (
        _first_text(packet, "evidence_classification") == "local_observed_artifact_replay"
    )
    missing_blocker = (
        "crypto_observed_latest_price_missing"
        if observed_artifact
        else "crypto_latest_price_missing"
    )
    timestamp_blocker = (
        "crypto_observed_latest_price_timestamp_missing"
        if observed_artifact
        else "crypto_latest_price_timestamp_missing"
    )
    stale_blocker = (
        "crypto_observed_latest_price_stale"
        if observed_artifact
        else "crypto_latest_price_stale"
    )
    if not _first_text(packet, "latest_price_value"):
        return missing_blocker
    if not observed_at:
        return timestamp_blocker
    if freshness != "fresh":
        return stale_blocker
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
            "freshness_evaluated_at": readiness.get("freshness_evaluated_at", ""),
            "freshness_evaluation_mode": readiness.get(
                "freshness_evaluation_mode",
                "",
            ),
            "latest_price_age_basis": readiness.get("latest_price_age_basis", ""),
            "operational_freshness_confirmed": readiness.get(
                "operational_freshness_confirmed",
                False,
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


def _resolve_freshness_evaluation_mode(
    value: object,
    *,
    explicit_as_of: bool,
) -> str:
    mode = _text(value)
    if mode:
        return mode
    return "deterministic_replay" if explicit_as_of else "wall_clock"


def _resolve_freshness_evaluated_at(
    value: datetime | str | None,
    *,
    mode: str,
    replay_basis: str,
) -> str:
    explicit = _as_of_argument(value)
    if explicit:
        return explicit
    if mode == "wall_clock":
        return datetime.now(UTC).isoformat()
    return replay_basis


def _latest_price_age_basis(freshness_evaluation_mode: str) -> str:
    if freshness_evaluation_mode == "wall_clock":
        return "freshness_evaluated_at_minus_observed_at_wall_clock"
    if freshness_evaluation_mode == "deterministic_replay":
        return "freshness_evaluated_at_minus_observed_at_replay_basis"
    return "unknown_freshness_evaluation_mode"


def _local_observed_artifact_refresh_status(freshness_evaluation_mode: str) -> str:
    if freshness_evaluation_mode == "wall_clock":
        return "local_observed_artifact_wall_clock_evaluated"
    return "local_observed_artifact_replay"


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


def _bool_text(value: object) -> str:
    return "true" if _is_true(value) else "false"


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
    parser.add_argument("--observed-latest-price-artifact", type=Path, default=None)
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
        observed_latest_price_artifact_path=args.observed_latest_price_artifact,
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
