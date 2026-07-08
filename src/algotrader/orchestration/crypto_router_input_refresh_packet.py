"""v5.14 deterministic crypto router input refresh packet.

This module inventories local crypto router inputs, repairs only from local or
fixture-backed sources, and reruns the existing no-submit crypto operating
cycle. It never reads a broker, mutates a broker, submits paper orders, loads
credentials, or contacts the network.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
import csv
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from algotrader.orchestration.crypto_no_submit_operating_cycle import (
    DEFAULT_AUTONOMY_CADENCE_OUTPUT_ROOT,
    DEFAULT_CRYPTO_REFRESH_OUTPUT_ROOT,
    DEFAULT_DRY_RUN_OUTPUT_ROOT,
    DEFAULT_HANDOFF_OUTPUT_ROOT,
    DEFAULT_ROUTER_OUTPUT_ROOT,
    DEFAULT_SIZING_PREVIEW_OUTPUT_ROOT,
    run_crypto_no_submit_operating_cycle,
)
from algotrader.orchestration.crypto_paper_autonomy_cadence import (
    DEFAULT_CERTIFICATION_INGESTION,
    DEFAULT_FILL_EXIT_INGESTION,
    DEFAULT_FILL_EXIT_RESULT,
    DEFAULT_SUBMIT_CANCEL_RESULT,
)
from algotrader.orchestration.crypto_qty_sizing_preview import (
    CRYPTO_QTY_SIZING_PREVIEW_DEFAULT_NOTIONAL_CAP,
)
from algotrader.orchestration.crypto_universe_refresh import (
    CRYPTO_UNIVERSE_REFRESH_DEFAULT_BARS_CSV,
    CRYPTO_UNIVERSE_REFRESH_DEFAULT_VISIBILITY_STATUS,
    run_crypto_universe_refresh,
)

SCHEMA_VERSION = "v5_14_crypto_router_input_refresh_packet_v1"
COMMAND_NAME = "run_crypto_router_input_refresh_packet"

DEFAULT_OUTPUT_ROOT = Path("runs/crypto_router_input_refresh_packet/latest")

FinalState = Literal[
    "router_inputs_ready_cycle_rerun_complete",
    "local_replay_cycle_rerun_complete",
    "fixture_backed_cycle_rerun_complete",
    "router_inputs_partially_repaired_cycle_blocked",
    "blocked_missing_local_inputs",
    "blocked_stale_local_inputs",
    "blocked_invalid_schema",
    "blocked_requires_broker_read_authorization",
    "blocked_requires_market_data_authorization",
    "blocked_requires_paid_or_new_service",
    "blocked",
]

NextOperatorAction = Literal[
    "review_no_submit_packet",
    "review_local_replay_no_submit_packet",
    "review_fixture_backed_no_submit_packet",
    "rerun_crypto_no_submit_operating_cycle",
    "provide_or_authorize_market_data_refresh",
    "authorize_scoped_paper_read",
    "repair_local_input_schema",
    "blocked",
]

ComponentClassification = Literal[
    "present_valid",
    "present_stale",
    "missing",
    "invalid_schema",
    "not_refreshable_without_authorization",
]

InputBasis = Literal[
    "broker_observed",
    "market_data_observed",
    "local_replay",
    "offline_fixture",
    "stale_local",
    "mixed",
]

FINAL_STATES: tuple[FinalState, ...] = (
    "router_inputs_ready_cycle_rerun_complete",
    "local_replay_cycle_rerun_complete",
    "fixture_backed_cycle_rerun_complete",
    "router_inputs_partially_repaired_cycle_blocked",
    "blocked_missing_local_inputs",
    "blocked_stale_local_inputs",
    "blocked_invalid_schema",
    "blocked_requires_broker_read_authorization",
    "blocked_requires_market_data_authorization",
    "blocked_requires_paid_or_new_service",
    "blocked",
)

NEXT_OPERATOR_ACTIONS: tuple[NextOperatorAction, ...] = (
    "review_no_submit_packet",
    "review_local_replay_no_submit_packet",
    "review_fixture_backed_no_submit_packet",
    "rerun_crypto_no_submit_operating_cycle",
    "provide_or_authorize_market_data_refresh",
    "authorize_scoped_paper_read",
    "repair_local_input_schema",
    "blocked",
)

COMPONENT_CLASSIFICATIONS: tuple[ComponentClassification, ...] = (
    "present_valid",
    "present_stale",
    "missing",
    "invalid_schema",
    "not_refreshable_without_authorization",
)

INPUT_BASES: tuple[InputBasis, ...] = (
    "broker_observed",
    "market_data_observed",
    "local_replay",
    "offline_fixture",
    "stale_local",
    "mixed",
)

REQUIRED_LABELS = (
    "crypto_router_input_refresh_packet",
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
    "paid_or_new_service_used",
)

ROUTER_INPUT_COMPONENTS = (
    "crypto_universe_metadata",
    "symbol_orderability_metadata",
    "history_or_feature_data",
    "candidate_generation_inputs",
    "router_decision_artifact_expectations",
)

ROUTER_READY_CYCLE_STATES = {
    "selected_candidate_no_submit_packet_ready",
    "no_trade",
}

MARKET_DATA_BLOCKERS = {
    "history_missing",
    "missing_history",
    "missing_data",
    "stale_data",
    "insufficient_history",
}

BROKER_READ_BLOCKERS = {
    "metadata_missing",
    "metadata_not_observed",
    "broker_state_not_observed",
    "metadata_missing_tradable",
    "metadata_missing_status",
    "metadata_missing_min_order_size",
    "metadata_missing_min_trade_increment",
}

__all__ = [
    "COMMAND_NAME",
    "COMPONENT_CLASSIFICATIONS",
    "DEFAULT_OUTPUT_ROOT",
    "FALSE_SAFETY_FIELDS",
    "FINAL_STATES",
    "NEXT_OPERATOR_ACTIONS",
    "REQUIRED_LABELS",
    "ROUTER_INPUT_COMPONENTS",
    "SCHEMA_VERSION",
    "build_input_inventory",
    "main",
    "render_refresh_packet_brief",
    "render_refresh_packet_text",
    "run_crypto_router_input_refresh_packet",
    "write_crypto_router_input_refresh_packet_artifacts",
]


def run_crypto_router_input_refresh_packet(
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
    allow_fixture_repair: bool = True,
    request_paper_read_repair: bool = False,
    request_market_data_refresh: bool = False,
    as_of: datetime | str | None = None,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Build the v5.14 router-input repair packet and rerun the no-submit cycle."""

    root = Path(output_root)
    if write_artifacts:
        root.mkdir(parents=True, exist_ok=True)
    as_of_value = _utc_datetime(as_of or datetime.now(UTC), "as_of")
    refresh_root = Path(crypto_refresh_output_root)
    router_root = Path(router_output_root)
    input_paths = _input_paths(
        crypto_refresh_output_root=refresh_root,
        router_output_root=router_root,
        bars_csv=Path(bars_csv),
        crypto_visibility_status=Path(crypto_visibility_status),
    )
    initial_input_inventory = build_input_inventory(
        input_paths=input_paths,
        as_of=as_of_value,
        request_paper_read_repair=request_paper_read_repair,
        request_market_data_refresh=request_market_data_refresh,
    )
    refresh_actions = _plan_refresh_actions(
        input_inventory=initial_input_inventory,
        allow_fixture_repair=allow_fixture_repair,
        request_paper_read_repair=request_paper_read_repair,
        request_market_data_refresh=request_market_data_refresh,
    )
    repair_mode = _repair_refresh_mode(refresh_actions, refresh_mode)
    repair_packet: Mapping[str, object] = {}
    repair_error = ""
    if _should_generate_refresh_packet(refresh_actions):
        try:
            repair_packet = run_crypto_universe_refresh(
                output_root=refresh_root,
                mode=repair_mode,
                bars_csv=bars_csv,
                crypto_visibility_status=crypto_visibility_status,
                as_of=as_of_value,
                write_artifacts=True,
            )
        except Exception as exc:  # pragma: no cover - defensive packet capture
            repair_error = f"{exc.__class__.__name__}: {exc}"
    if repair_packet:
        refresh_actions = _mark_repair_generated(
            refresh_actions=refresh_actions,
            repair_mode=repair_mode,
            repair_packet=repair_packet,
        )
    if repair_error:
        refresh_actions = _mark_repair_error(refresh_actions, repair_error)

    cycle_rerun_status = _rerun_cycle(
        output_root=root,
        crypto_refresh_output_root=refresh_root,
        router_output_root=router_root,
        sizing_preview_output_root=Path(sizing_preview_output_root),
        handoff_output_root=Path(handoff_output_root),
        dry_run_output_root=Path(dry_run_output_root),
        autonomy_cadence_output_root=Path(autonomy_cadence_output_root),
        refresh_mode=repair_mode,
        bars_csv=bars_csv,
        crypto_visibility_status=crypto_visibility_status,
        spy_bars_csv=spy_bars_csv,
        submit_cancel_result_path=submit_cancel_result_path,
        certification_ingestion_path=certification_ingestion_path,
        fill_exit_result_path=fill_exit_result_path,
        fill_exit_ingestion_path=fill_exit_ingestion_path,
        preview_notional_cap=preview_notional_cap,
        allow_fixture_backed=allow_fixture_repair or repair_mode == "offline_fixture",
        as_of=as_of_value,
    )
    input_inventory = build_input_inventory(
        input_paths=input_paths,
        as_of=as_of_value,
        request_paper_read_repair=request_paper_read_repair,
        request_market_data_refresh=request_market_data_refresh,
    )
    input_basis = _input_basis(
        input_inventory=input_inventory,
        refresh_actions=refresh_actions,
        cycle_rerun_status=cycle_rerun_status,
        refresh_mode=repair_mode,
    )
    router_input_blockers = _router_input_blockers(
        input_inventory=input_inventory,
        refresh_actions=refresh_actions,
        cycle_rerun_status=cycle_rerun_status,
    )
    final_state = _final_state(
        input_inventory=input_inventory,
        refresh_actions=refresh_actions,
        router_input_blockers=router_input_blockers,
        cycle_rerun_status=cycle_rerun_status,
        input_basis=input_basis,
    )
    next_operator_action = _next_operator_action_payload(
        final_state=final_state,
        router_input_blockers=router_input_blockers,
        input_basis=input_basis,
    )
    input_readiness = _input_readiness(
        final_state=final_state,
        input_inventory=input_inventory,
        refresh_actions=refresh_actions,
        router_input_blockers=router_input_blockers,
        cycle_rerun_status=cycle_rerun_status,
        next_operator_action=next_operator_action,
        output_root=root,
        as_of=as_of_value,
        input_basis=input_basis,
    )
    router_input_blockers_remaining = list(
        _mapping_sequence(router_input_blockers.get("blockers"))
    )
    packet = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_router_input_refresh_packet",
        "operator_command": COMMAND_NAME,
        "as_of": as_of_value.isoformat(),
        "output_root": str(root),
        "input_basis": input_basis,
        "data_basis": input_basis,
        "input_inventory": input_inventory,
        "input_readiness": input_readiness,
        "refresh_actions": refresh_actions,
        "router_input_blockers": router_input_blockers,
        "router_input_blocker_count": router_input_blockers.get("blocker_count", 0),
        "router_input_blockers_remaining": router_input_blockers_remaining,
        "cycle_rerun_status": cycle_rerun_status,
        "next_operator_action": next_operator_action,
        "final_state": final_state,
        "router_input_blocker_removed": input_readiness["router_input_blocker_removed"],
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }
    if write_artifacts:
        packet["artifact_paths"] = write_crypto_router_input_refresh_packet_artifacts(root, packet)
    return packet


def build_input_inventory(
    *,
    input_paths: Mapping[str, Path],
    as_of: datetime,
    request_paper_read_repair: bool = False,
    request_market_data_refresh: bool = False,
) -> dict[str, object]:
    """Inspect the local router-input locations used by v5.0-v5.13."""

    as_of_value = _utc_datetime(as_of, "as_of")
    bars_report = _inspect_crypto_bars(input_paths["bars_csv"], as_of_value)
    visibility_report = _inspect_json(input_paths["crypto_visibility_status"])
    router_manifest_report = _inspect_router_input_manifest(
        input_paths["crypto_router_input_manifest"]
    )
    orderability_report = _inspect_orderability(
        input_paths["crypto_orderability_metadata"],
        visibility_report,
    )
    history_manifest_report = _inspect_history_manifest(
        input_paths["crypto_history_manifest"],
        bars_report,
        as_of_value,
    )
    universe_report = _inspect_universe(
        input_paths["crypto_universe"],
        visibility_report,
        router_manifest_report,
    )
    candidate_report = _inspect_candidate_generation(
        router_manifest_report,
        orderability_report,
        history_manifest_report,
    )
    router_expectation_report = _inspect_router_expectations(
        input_paths["router_decision"],
        input_paths["opportunity_candidates"],
    )
    components = (
        _component(
            "crypto_universe_metadata",
            (input_paths["crypto_visibility_status"], input_paths["crypto_universe"]),
            universe_report,
            authorization_required="broker_read"
            if request_paper_read_repair and universe_report["needs_broker_read"]
            else "",
        ),
        _component(
            "symbol_orderability_metadata",
            (
                input_paths["crypto_visibility_status"],
                input_paths["crypto_orderability_metadata"],
                input_paths["crypto_router_input_manifest"],
            ),
            orderability_report,
            authorization_required="broker_read"
            if request_paper_read_repair and orderability_report["needs_broker_read"]
            else "",
        ),
        _component(
            "history_or_feature_data",
            (input_paths["bars_csv"], input_paths["crypto_history_manifest"]),
            history_manifest_report,
            authorization_required="market_data"
            if request_market_data_refresh and history_manifest_report["needs_market_data"]
            else "",
        ),
        _component(
            "candidate_generation_inputs",
            (
                input_paths["crypto_router_input_manifest"],
                input_paths["crypto_orderability_metadata"],
                input_paths["crypto_history_manifest"],
            ),
            candidate_report,
        ),
        _component(
            "router_decision_artifact_expectations",
            (input_paths["router_decision"], input_paths["opportunity_candidates"]),
            router_expectation_report,
        ),
    )
    classifications = _classification_counts(components)
    local_locations = _local_input_locations(input_paths)
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_router_input_inventory",
        "as_of": as_of_value.isoformat(),
        "inventory_scope": "v5.0-v5.13_repo_consistent_crypto_router_inputs",
        "input_locations": local_locations,
        "components": list(components),
        "classification_counts": classifications,
        "required_components": list(ROUTER_INPUT_COMPONENTS),
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }


def write_crypto_router_input_refresh_packet_artifacts(
    output_root: Path | str,
    packet: Mapping[str, object],
) -> dict[str, str]:
    """Write the v5.14 refresh packet artifacts."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "input_inventory": root / "input_inventory.json",
        "input_readiness": root / "input_readiness.json",
        "refresh_actions": root / "refresh_actions.json",
        "router_input_blockers": root / "router_input_blockers.json",
        "cycle_rerun_status": root / "cycle_rerun_status.json",
        "next_operator_action": root / "next_operator_action.json",
        "refresh_packet_brief": root / "refresh_packet_brief.md",
        "operating_record": root / "operating_record.jsonl",
    }
    manifest_path = root / "manifest.json"
    artifact_paths = {key: str(path) for key, path in paths.items()}
    artifact_paths["manifest"] = str(manifest_path)
    packet_payload = {**dict(packet), "artifact_paths": artifact_paths}

    _write_json(paths["input_inventory"], _mapping(packet.get("input_inventory")))
    _write_json(paths["input_readiness"], _mapping(packet.get("input_readiness")))
    _write_json(paths["refresh_actions"], _mapping(packet.get("refresh_actions")))
    _write_json(paths["router_input_blockers"], _mapping(packet.get("router_input_blockers")))
    _write_json(paths["cycle_rerun_status"], _mapping(packet.get("cycle_rerun_status")))
    _write_json(paths["next_operator_action"], _mapping(packet.get("next_operator_action")))
    paths["refresh_packet_brief"].write_text(
        render_refresh_packet_brief(packet_payload) + "\n",
        encoding="utf-8",
        newline="\n",
    )
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

    manifest_entries = {
        key: _artifact_entry(path) for key, path in paths.items() if path.is_file()
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_router_input_refresh_packet_manifest",
        "operator_command": COMMAND_NAME,
        "as_of": packet.get("as_of", ""),
        "output_root": str(root),
        "required_artifacts": sorted(paths),
        "artifacts": manifest_entries,
        "generated_under_runs": "runs" in root.parts,
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }
    _write_json(manifest_path, manifest)
    return artifact_paths


def render_refresh_packet_brief(packet: Mapping[str, object]) -> str:
    """Render the operator-facing markdown brief."""

    readiness = _mapping(packet.get("input_readiness"))
    blockers = _mapping(packet.get("router_input_blockers"))
    cycle = _mapping(packet.get("cycle_rerun_status"))
    next_action = _mapping(packet.get("next_operator_action"))
    return "\n".join(
        [
            "# Crypto Router Input Refresh Packet",
            "",
            f"- schema_version: `{packet.get('schema_version', '')}`",
            f"- final_state: `{readiness.get('final_state', packet.get('final_state', ''))}`",
            f"- input_basis: `{readiness.get('input_basis', packet.get('input_basis', ''))}`",
            f"- data_basis: `{readiness.get('data_basis', packet.get('data_basis', ''))}`",
            f"- router_input_blocker_removed: `{_bool_text(readiness.get('router_input_blocker_removed'))}`",
            f"- cycle_invoked: `{_bool_text(cycle.get('cycle_invoked'))}`",
            f"- cycle_final_state: `{cycle.get('cycle_final_state', '')}`",
            f"- next_operator_action: `{next_action.get('action', '')}`",
            f"- router_input_blocker_count: {blockers.get('blocker_count', 0)}",
            f"- broker_read_occurred: `{_bool_text(packet.get('broker_read_occurred'))}`",
            f"- broker_mutation_occurred: `{_bool_text(packet.get('broker_mutation_occurred'))}`",
            f"- paper_submit_occurred: `{_bool_text(packet.get('paper_submit_occurred'))}`",
            f"- live_endpoint_touched: `{_bool_text(packet.get('live_endpoint_touched'))}`",
            f"- network_access_attempted: `{_bool_text(packet.get('network_access_attempted'))}`",
            f"- fresh_authorization_required_for_order: `{_bool_text(readiness.get('fresh_authorization_required_for_order'))}`",
            f"- labels: `{', '.join(_string_sequence(packet.get('labels')))}`",
        ]
    )


def render_refresh_packet_text(packet: Mapping[str, object]) -> str:
    """Render compact console output for the PowerShell wrapper."""

    readiness = _mapping(packet.get("input_readiness"))
    cycle = _mapping(packet.get("cycle_rerun_status"))
    next_action = _mapping(packet.get("next_operator_action"))
    return "\n".join(
        [
            "crypto_router_input_refresh_packet_status=complete",
            f"final_state={readiness.get('final_state', packet.get('final_state', ''))}",
            f"input_basis={readiness.get('input_basis', packet.get('input_basis', ''))}",
            f"data_basis={readiness.get('data_basis', packet.get('data_basis', ''))}",
            f"router_input_blocker_removed={_bool_text(readiness.get('router_input_blocker_removed'))}",
            f"router_input_blocker_count={readiness.get('router_input_blocker_count', 0)}",
            f"cycle_invoked={_bool_text(cycle.get('cycle_invoked'))}",
            f"cycle_final_state={cycle.get('cycle_final_state', '')}",
            f"next_operator_action={next_action.get('action', '')}",
            "broker_read_occurred=false",
            "broker_mutation_occurred=false",
            "paper_submit_occurred=false",
            "live_endpoint_touched=false",
            "network_access_attempted=false",
            "fresh_authorization_required_for_order=true",
        ]
    )


def _input_paths(
    *,
    crypto_refresh_output_root: Path,
    router_output_root: Path,
    bars_csv: Path,
    crypto_visibility_status: Path,
) -> dict[str, Path]:
    return {
        "bars_csv": bars_csv,
        "crypto_visibility_status": crypto_visibility_status,
        "crypto_universe": crypto_refresh_output_root / "crypto_universe.json",
        "crypto_orderability_metadata": (
            crypto_refresh_output_root / "crypto_orderability_metadata.json"
        ),
        "crypto_history_manifest": crypto_refresh_output_root / "crypto_history_manifest.json",
        "crypto_history_quality_report": (
            crypto_refresh_output_root / "crypto_history_quality_report.json"
        ),
        "crypto_router_input_manifest": (
            crypto_refresh_output_root / "crypto_router_input_manifest.json"
        ),
        "router_decision": router_output_root / "router_decision.json",
        "opportunity_candidates": router_output_root / "opportunity_candidates.json",
        "v5_default_crypto_router_input_manifest": (
            Path("runs/crypto_universe_refresh/latest/crypto_router_input_manifest.json")
        ),
        "v5_default_router_decision": Path("runs/opportunity_router/latest/router_decision.json"),
        "v5_default_opportunity_candidates": (
            Path("runs/opportunity_router/latest/opportunity_candidates.json")
        ),
    }


def _local_input_locations(input_paths: Mapping[str, Path]) -> list[dict[str, object]]:
    records = []
    purposes = {
        "bars_csv": "history_or_feature_data",
        "crypto_visibility_status": "crypto_universe_metadata_and_orderability",
        "crypto_universe": "refreshed_crypto_universe_metadata",
        "crypto_orderability_metadata": "refreshed_symbol_orderability_metadata",
        "crypto_history_manifest": "refreshed_history_manifest",
        "crypto_history_quality_report": "refreshed_history_quality_report",
        "crypto_router_input_manifest": "candidate_generation_inputs",
        "router_decision": "router_decision_artifact_expectation",
        "opportunity_candidates": "candidate_generation_artifact_expectation",
        "v5_default_crypto_router_input_manifest": "v5.0-v5.13_default_router_manifest_location",
        "v5_default_router_decision": "v5.0-v5.13_default_router_decision_location",
        "v5_default_opportunity_candidates": "v5.0-v5.13_default_candidates_location",
    }
    for key, path in sorted(input_paths.items()):
        records.append(
            {
                "name": key,
                "purpose": purposes.get(key, key),
                "path": str(path),
                "exists": path.is_file(),
                "repo_consistent_location": True,
            }
        )
    return records


def _inspect_crypto_bars(path: Path, as_of: datetime) -> dict[str, object]:
    if not path.is_file():
        return {
            "exists": False,
            "classification": "missing",
            "blockers": ["history_missing", "local_artifact_missing"],
            "needs_market_data": True,
        }
    try:
        rows = _read_csv_rows(path)
    except Exception as exc:
        return {
            "exists": True,
            "classification": "invalid_schema",
            "blockers": ["invalid_schema", f"invalid_crypto_bars:{exc.__class__.__name__}"],
            "needs_market_data": False,
        }
    bars = []
    invalid_rows = 0
    for row in rows:
        parsed = _parse_bar_row(row)
        if parsed:
            bars.append(parsed)
        else:
            invalid_rows += 1
    if not bars:
        return {
            "exists": True,
            "classification": "missing",
            "row_count": len(rows),
            "valid_bar_count": 0,
            "invalid_row_count": invalid_rows,
            "blockers": ["missing_data", "missing_history"],
            "needs_market_data": True,
        }
    latest = max(item["timestamp"] for item in bars)
    latest_age = as_of - latest
    symbol_count = len({str(item["symbol"]) for item in bars})
    blockers: list[str] = []
    if latest > as_of:
        blockers.append("future_timestamp")
    if latest_age > timedelta(hours=2):
        blockers.append("stale_data")
    if len(bars) < 50:
        blockers.append("insufficient_history")
    if invalid_rows:
        blockers.append("invalid_rows_ignored")
    classification = "present_valid" if not blockers else "present_stale"
    return {
        "exists": True,
        "classification": classification,
        "row_count": len(rows),
        "valid_bar_count": len(bars),
        "invalid_row_count": invalid_rows,
        "symbol_count": symbol_count,
        "symbols": sorted({str(item["symbol"]) for item in bars}),
        "latest_timestamp": latest.isoformat(),
        "latest_age_seconds": int(latest_age.total_seconds()),
        "blockers": blockers,
        "needs_market_data": bool(set(blockers) & MARKET_DATA_BLOCKERS),
    }


def _inspect_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {
            "exists": False,
            "classification": "missing",
            "payload": {},
            "blockers": ["local_artifact_missing"],
        }
    try:
        payload = _read_json_mapping(path)
    except Exception as exc:
        return {
            "exists": True,
            "classification": "invalid_schema",
            "payload": {},
            "blockers": ["invalid_schema", f"invalid_json:{exc.__class__.__name__}"],
        }
    return {
        "exists": True,
        "classification": "present_valid",
        "payload": payload,
        "blockers": [],
        "schema_version": _text(payload.get("schema_version")),
        "as_of": _text(payload.get("as_of")),
    }


def _inspect_router_input_manifest(path: Path) -> dict[str, object]:
    report = _inspect_json(path)
    if not report["exists"] or report["classification"] == "invalid_schema":
        return {
            **report,
            "router_ready_symbols": [],
            "records": [],
            "needs_broker_read": False,
            "needs_market_data": False,
        }
    payload = _mapping(report.get("payload"))
    records = _mapping_sequence(payload.get("records"))
    ready_symbols = _string_sequence(payload.get("router_ready_symbols"))
    blockers = list(_string_sequence(payload.get("blockers")))
    for record in records:
        blockers.extend(_string_sequence(record.get("blockers")))
        blockers.extend(_string_sequence(record.get("metadata_blockers")))
        blockers.extend(_string_sequence(record.get("orderability_blockers")))
        blockers.extend(_string_sequence(record.get("history_blockers")))
    classification: ComponentClassification = "present_valid"
    if not records:
        classification = "invalid_schema"
        blockers.append("router_input_manifest_records_missing")
    elif not ready_symbols:
        classification = "missing"
        blockers.append("router_ready_symbols_missing")
    return {
        **report,
        "classification": classification,
        "router_ready_symbols": list(ready_symbols),
        "records": list(records),
        "blockers": list(_dedupe(blockers)),
        "needs_broker_read": bool(set(blockers) & BROKER_READ_BLOCKERS),
        "needs_market_data": bool(set(blockers) & MARKET_DATA_BLOCKERS),
    }


def _inspect_orderability(
    path: Path,
    visibility_report: Mapping[str, object],
) -> dict[str, object]:
    report = _inspect_json(path)
    payload = _mapping(report.get("payload"))
    records = _mapping_sequence(payload.get("records"))
    visibility_payload = _mapping(visibility_report.get("payload"))
    visibility_metadata = _mapping(visibility_payload.get("asset_metadata"))
    capability = _mapping(visibility_payload.get("crypto_capability"))
    blockers: list[str] = []
    needs_broker_read = False
    if report["classification"] == "invalid_schema" or visibility_report["classification"] == "invalid_schema":
        return {
            **report,
            "classification": "invalid_schema",
            "records": list(records),
            "blockers": list(
                _dedupe(
                    (
                        *_string_sequence(report.get("blockers")),
                        *_string_sequence(visibility_report.get("blockers")),
                    )
                )
            ),
            "needs_broker_read": False,
        }
    if records:
        valid_count = 0
        for record in records:
            status = _first_text(record, "orderability_status")
            blockers.extend(_string_sequence(record.get("orderability_blockers")))
            blockers.extend(_string_sequence(record.get("metadata_blockers")))
            if status in {
                "orderable",
                "notional_orderable",
                "qty_orderable",
                "qty_orderable_notional_unobserved",
            }:
                valid_count += 1
        if valid_count:
            return {
                **report,
                "classification": "present_valid",
                "records": list(records),
                "valid_orderability_count": valid_count,
                "blockers": list(_dedupe(blockers)),
                "needs_broker_read": False,
            }
    if visibility_metadata or capability:
        missing_increment = not _first_nonempty(
            _first_text(capability, "min_trade_increment"),
            _first_text(capability, "min_order_increment"),
        )
        missing_size = not _first_text(capability, "min_order_size")
        if missing_increment or missing_size:
            blockers.extend(["metadata_missing", "metadata_partial"])
            needs_broker_read = True
        else:
            return {
                **report,
                "classification": "present_valid",
                "records": list(records),
                "valid_orderability_count": 1,
                "blockers": [],
                "needs_broker_read": False,
            }
    else:
        blockers.extend(["metadata_missing", "metadata_not_observed"])
        needs_broker_read = True
    return {
        **report,
        "classification": "missing",
        "records": list(records),
        "valid_orderability_count": 0,
        "blockers": list(_dedupe(blockers)),
        "needs_broker_read": needs_broker_read,
    }


def _inspect_history_manifest(
    path: Path,
    bars_report: Mapping[str, object],
    as_of: datetime,
) -> dict[str, object]:
    report = _inspect_json(path)
    if report["classification"] == "invalid_schema":
        return {
            **report,
            "records": [],
            "blockers": _string_sequence(report.get("blockers")),
            "needs_market_data": False,
        }
    if bars_report.get("classification") == "invalid_schema":
        return {
            **report,
            "classification": "invalid_schema",
            "records": [],
            "blockers": list(_string_sequence(bars_report.get("blockers"))),
            "needs_market_data": False,
        }
    payload = _mapping(report.get("payload"))
    records = _mapping_sequence(payload.get("records"))
    blockers: list[str] = list(_string_sequence(bars_report.get("blockers")))
    valid_history_count = 0
    stale_count = 0
    for record in records:
        history_status = _first_text(record, "history_status")
        freshness_status = _first_text(record, "freshness_status")
        data_quality_status = _first_text(record, "data_quality_status")
        blockers.extend(_string_sequence(record.get("blockers")))
        if (
            history_status == "sufficient_history"
            and freshness_status == "fresh"
            and data_quality_status == "valid"
        ):
            valid_history_count += 1
        if freshness_status == "stale_data":
            stale_count += 1
    if bars_report.get("classification") == "present_valid" or valid_history_count:
        classification: ComponentClassification = "present_valid"
    elif bars_report.get("classification") == "present_stale" or stale_count:
        classification = "present_stale"
    elif report["exists"]:
        classification = "missing"
        blockers.append("missing_history")
    else:
        classification = "missing"
    return {
        **report,
        "classification": classification,
        "records": list(records),
        "valid_history_count": valid_history_count,
        "as_of": as_of.isoformat(),
        "blockers": list(_dedupe(blockers)),
        "needs_market_data": classification in {"missing", "present_stale"}
        or bool(set(blockers) & MARKET_DATA_BLOCKERS),
    }


def _inspect_universe(
    path: Path,
    visibility_report: Mapping[str, object],
    router_manifest_report: Mapping[str, object],
) -> dict[str, object]:
    report = _inspect_json(path)
    if report["classification"] == "invalid_schema" or visibility_report["classification"] == "invalid_schema":
        return {
            **report,
            "classification": "invalid_schema",
            "blockers": list(
                _dedupe(
                    (
                        *_string_sequence(report.get("blockers")),
                        *_string_sequence(visibility_report.get("blockers")),
                    )
                )
            ),
            "needs_broker_read": False,
        }
    payload = _mapping(report.get("payload"))
    visibility_payload = _mapping(visibility_report.get("payload"))
    manifest_symbols = _string_sequence(router_manifest_report.get("router_ready_symbols"))
    symbols = _string_sequence(payload.get("symbols")) or _string_sequence(
        visibility_payload.get("eligible_crypto_symbols")
    )
    capability = _mapping(visibility_payload.get("crypto_capability"))
    if capability:
        symbols = tuple((*symbols, *_string_sequence(capability.get("eligible_crypto_symbols"))))
    if symbols or manifest_symbols:
        return {
            **report,
            "classification": "present_valid",
            "symbols": list(_dedupe((*symbols, *manifest_symbols))),
            "blockers": [],
            "needs_broker_read": False,
        }
    return {
        **report,
        "classification": "missing",
        "symbols": [],
        "blockers": ["metadata_missing", "metadata_not_observed"],
        "needs_broker_read": True,
    }


def _inspect_candidate_generation(
    router_manifest_report: Mapping[str, object],
    orderability_report: Mapping[str, object],
    history_report: Mapping[str, object],
) -> dict[str, object]:
    blockers = list(_string_sequence(router_manifest_report.get("blockers")))
    blockers.extend(_string_sequence(orderability_report.get("blockers")))
    blockers.extend(_string_sequence(history_report.get("blockers")))
    if any(
        report.get("classification") == "invalid_schema"
        for report in (router_manifest_report, orderability_report, history_report)
    ):
        return {
            "classification": "invalid_schema",
            "blockers": list(_dedupe((*blockers, "invalid_schema"))),
            "needs_broker_read": False,
            "needs_market_data": False,
        }
    if router_manifest_report.get("router_ready_symbols"):
        return {
            "classification": "present_valid",
            "blockers": list(_dedupe(blockers)),
            "needs_broker_read": False,
            "needs_market_data": False,
        }
    if (
        orderability_report.get("classification") == "present_valid"
        and history_report.get("classification") == "present_valid"
    ):
        return {
            "classification": "missing",
            "blockers": list(_dedupe((*blockers, "router_input_manifest_missing"))),
            "needs_broker_read": False,
            "needs_market_data": False,
        }
    return {
        "classification": "missing",
        "blockers": list(_dedupe((*blockers, "candidate_generation_inputs_missing"))),
        "needs_broker_read": bool(orderability_report.get("needs_broker_read")),
        "needs_market_data": bool(history_report.get("needs_market_data")),
    }


def _inspect_router_expectations(
    router_decision_path: Path,
    candidates_path: Path,
) -> dict[str, object]:
    decision = _inspect_json(router_decision_path)
    candidates = _inspect_json(candidates_path)
    blockers: list[str] = []
    if decision["classification"] == "invalid_schema" or candidates["classification"] == "invalid_schema":
        blockers.extend(_string_sequence(decision.get("blockers")))
        blockers.extend(_string_sequence(candidates.get("blockers")))
        return {
            "classification": "invalid_schema",
            "blockers": list(_dedupe(blockers)),
            "needs_broker_read": False,
            "needs_market_data": False,
        }
    if not decision["exists"] or not candidates["exists"]:
        if not decision["exists"]:
            blockers.append("router_decision_missing")
        if not candidates["exists"]:
            blockers.append("opportunity_candidates_missing")
        return {
            "classification": "missing",
            "blockers": blockers,
            "refreshable_by_cycle_rerun": True,
            "needs_broker_read": False,
            "needs_market_data": False,
        }
    decision_payload = _mapping(decision.get("payload"))
    if _first_text(decision_payload, "decision") not in {"selected", "no_trade"}:
        return {
            "classification": "invalid_schema",
            "blockers": ["router_decision_invalid_or_missing_decision"],
            "needs_broker_read": False,
            "needs_market_data": False,
        }
    return {
        "classification": "present_valid",
        "blockers": [],
        "refreshable_by_cycle_rerun": True,
        "needs_broker_read": False,
        "needs_market_data": False,
    }


def _component(
    component: str,
    locations: Sequence[Path],
    report: Mapping[str, object],
    *,
    authorization_required: str = "",
) -> dict[str, object]:
    classification = _component_classification(report, authorization_required)
    blockers = _string_sequence(report.get("blockers"))
    return {
        "component": component,
        "classification": classification,
        "locations": [
            {
                "path": str(path),
                "exists": path.is_file(),
            }
            for path in locations
        ],
        "blockers": list(blockers),
        "authorization_required": authorization_required,
        "not_refreshable_without_authorization": (
            classification == "not_refreshable_without_authorization"
        ),
        "refreshable_from_local_or_fixture": classification
        in {"missing", "present_stale", "present_valid"},
        "details": _details_without_payload(report),
    }


def _component_classification(
    report: Mapping[str, object],
    authorization_required: str,
) -> ComponentClassification:
    if authorization_required:
        return "not_refreshable_without_authorization"
    classification = _text(report.get("classification"))
    if classification in COMPONENT_CLASSIFICATIONS:
        return classification  # type: ignore[return-value]
    return "missing"


def _details_without_payload(report: Mapping[str, object]) -> dict[str, object]:
    return {
        str(key): _json_safe(value)
        for key, value in report.items()
        if key not in {"payload", "records"} and key != "classification"
    }


def _classification_counts(components: Sequence[Mapping[str, object]]) -> dict[str, int]:
    counts = {classification: 0 for classification in COMPONENT_CLASSIFICATIONS}
    for component in components:
        classification = _text(component.get("classification"))
        if classification in counts:
            counts[classification] += 1
    return counts


def _plan_refresh_actions(
    *,
    input_inventory: Mapping[str, object],
    allow_fixture_repair: bool,
    request_paper_read_repair: bool,
    request_market_data_refresh: bool,
) -> dict[str, object]:
    components = _mapping_sequence(input_inventory.get("components"))
    actions: list[dict[str, object]] = []
    invalid = _components_with_classification(components, "invalid_schema")
    needs_auth = _components_with_classification(
        components,
        "not_refreshable_without_authorization",
    )
    missing = _components_with_classification(components, "missing")
    stale = _components_with_classification(components, "present_stale")
    local_repairable = _local_repairable(missing, stale)
    fixture_repairable = bool(missing or stale)
    if invalid:
        actions.append(
            {
                "action": "no_repair_performed",
                "reason": "invalid_schema_requires_local_schema_repair",
                "components": [str(item.get("component", "")) for item in invalid],
                "performed": False,
            }
        )
    elif needs_auth:
        for component in needs_auth:
            required = _text(component.get("authorization_required"))
            actions.append(
                {
                    "action": "not_refreshable_without_authorization",
                    "component": component.get("component", ""),
                    "authorization_required": required,
                    "operator_request": _operator_request(required),
                    "performed": False,
                    "broker_read_occurred": False,
                    "network_access_attempted": False,
                }
            )
    elif local_repairable:
        actions.append(
            {
                "action": "generate_local_replay_refresh_packet",
                "reason": "valid_local_raw_inputs_can_regenerate_router_manifest",
                "refresh_mode": "local_replay",
                "performed": False,
            }
        )
    elif fixture_repairable and allow_fixture_repair:
        actions.append(
            {
                "action": "generate_fixture_backed_refresh_packet",
                "reason": "missing_or_stale_inputs_repaired_with_deterministic_fixture_backing",
                "refresh_mode": "offline_fixture",
                "performed": False,
                "fixture_backed": True,
                "fabricates_current_market_data": False,
            }
        )
    elif request_paper_read_repair and _needs_broker_read(components):
        actions.append(
            {
                "action": "not_refreshable_without_authorization",
                "authorization_required": "broker_read",
                "operator_request": _operator_request("broker_read"),
                "performed": False,
                "broker_read_occurred": False,
            }
        )
    elif request_market_data_refresh and _needs_market_data(components):
        actions.append(
            {
                "action": "not_refreshable_without_authorization",
                "authorization_required": "market_data",
                "operator_request": _operator_request("market_data"),
                "performed": False,
                "network_access_attempted": False,
            }
        )
    else:
        actions.append(
            {
                "action": "no_repair_needed" if not missing and not stale else "no_safe_repair_available",
                "reason": (
                    "all_components_present_valid"
                    if not missing and not stale
                    else "local_inputs_missing_or_stale_and_fixture_repair_disabled"
                ),
                "performed": False,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_router_input_refresh_actions",
        "allow_fixture_repair": allow_fixture_repair,
        "request_paper_read_repair": request_paper_read_repair,
        "request_market_data_refresh": request_market_data_refresh,
        "actions": actions,
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }


def _local_repairable(
    missing: Sequence[Mapping[str, object]],
    stale: Sequence[Mapping[str, object]],
) -> bool:
    missing_names = {str(item.get("component", "")) for item in missing}
    stale_names = {str(item.get("component", "")) for item in stale}
    return (
        missing_names <= {"candidate_generation_inputs", "router_decision_artifact_expectations"}
        and not stale_names
        and bool(missing_names)
    )


def _repair_refresh_mode(
    refresh_actions: Mapping[str, object],
    default_refresh_mode: str,
) -> Literal["local_replay", "offline_fixture"]:
    for action in _mapping_sequence(refresh_actions.get("actions")):
        mode = _text(action.get("refresh_mode"))
        if mode in {"local_replay", "offline_fixture"}:
            return mode  # type: ignore[return-value]
    return "offline_fixture" if default_refresh_mode == "offline_fixture" else "local_replay"


def _should_generate_refresh_packet(refresh_actions: Mapping[str, object]) -> bool:
    return any(
        _text(action.get("action"))
        in {"generate_local_replay_refresh_packet", "generate_fixture_backed_refresh_packet"}
        for action in _mapping_sequence(refresh_actions.get("actions"))
    )


def _mark_repair_generated(
    *,
    refresh_actions: Mapping[str, object],
    repair_mode: str,
    repair_packet: Mapping[str, object],
) -> dict[str, object]:
    actions: list[dict[str, object]] = []
    artifact_paths = _mapping(repair_packet.get("artifact_paths"))
    summary = _mapping(repair_packet.get("summary"))
    for action in _mapping_sequence(refresh_actions.get("actions")):
        action_payload = dict(action)
        if _text(action_payload.get("refresh_mode")) == repair_mode:
            action_payload.update(
                {
                    "performed": True,
                    "refresh_packet_schema_version": repair_packet.get("schema_version", ""),
                    "eligible_input_symbol_count": summary.get("eligible_input_symbol_count", 0),
                    "crypto_router_input_manifest": artifact_paths.get(
                        "crypto_router_input_manifest",
                        "",
                    ),
                }
            )
        actions.append(action_payload)
    return {**dict(refresh_actions), "actions": actions}


def _mark_repair_error(
    refresh_actions: Mapping[str, object],
    repair_error: str,
) -> dict[str, object]:
    actions = []
    for action in _mapping_sequence(refresh_actions.get("actions")):
        actions.append({**dict(action), "performed": False, "error": repair_error})
    return {**dict(refresh_actions), "actions": actions}


def _rerun_cycle(
    *,
    output_root: Path,
    crypto_refresh_output_root: Path,
    router_output_root: Path,
    sizing_preview_output_root: Path,
    handoff_output_root: Path,
    dry_run_output_root: Path,
    autonomy_cadence_output_root: Path,
    refresh_mode: Literal["local_replay", "offline_fixture"],
    bars_csv: Path | str,
    crypto_visibility_status: Path | str,
    spy_bars_csv: Path | str | None,
    submit_cancel_result_path: Path | str,
    certification_ingestion_path: Path | str,
    fill_exit_result_path: Path | str,
    fill_exit_ingestion_path: Path | str,
    preview_notional_cap: Decimal | str,
    allow_fixture_backed: bool,
    as_of: datetime,
) -> dict[str, object]:
    cycle_root = output_root / "cycle_rerun"
    try:
        packet = run_crypto_no_submit_operating_cycle(
            output_root=cycle_root,
            crypto_refresh_output_root=crypto_refresh_output_root,
            router_output_root=router_output_root,
            sizing_preview_output_root=sizing_preview_output_root,
            handoff_output_root=handoff_output_root,
            dry_run_output_root=dry_run_output_root,
            autonomy_cadence_output_root=autonomy_cadence_output_root,
            refresh_mode=refresh_mode,
            bars_csv=bars_csv,
            crypto_visibility_status=crypto_visibility_status,
            spy_bars_csv=spy_bars_csv,
            submit_cancel_result_path=submit_cancel_result_path,
            certification_ingestion_path=certification_ingestion_path,
            fill_exit_result_path=fill_exit_result_path,
            fill_exit_ingestion_path=fill_exit_ingestion_path,
            preview_notional_cap=preview_notional_cap,
            allow_fixture_backed=allow_fixture_backed,
            as_of=as_of,
            write_artifacts=True,
        )
    except Exception as exc:  # pragma: no cover - defensive packet capture
        return {
            "schema_version": SCHEMA_VERSION,
            "record_type": "crypto_router_input_cycle_rerun_status",
            "cycle_invoked": True,
            "cycle_completed": False,
            "cycle_final_state": "blocked",
            "cycle_error": f"{exc.__class__.__name__}: {exc}",
            "input_basis": refresh_mode,
            "data_basis": refresh_mode,
            "router_input_blocker_removed": False,
            "labels": list(REQUIRED_LABELS),
            "profit_claim": "none",
            **_false_flags(),
        }
    cycle_status = _mapping(packet.get("cycle_status"))
    final_state = _first_text(cycle_status, "final_state")
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_router_input_cycle_rerun_status",
        "cycle_invoked": True,
        "cycle_completed": True,
        "cycle_output_root": str(cycle_root),
        "cycle_final_state": final_state,
        "cycle_next_operator_action": _first_text(cycle_status, "next_operator_action"),
        "cycle_blockers": list(_string_sequence(cycle_status.get("blockers"))),
        "input_basis": refresh_mode,
        "data_basis": refresh_mode,
        "router_input_blocker_removed": final_state in ROUTER_READY_CYCLE_STATES,
        "cycle_artifact_paths": dict(_mapping(packet.get("artifact_paths"))),
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }


def _router_input_blockers(
    *,
    input_inventory: Mapping[str, object],
    refresh_actions: Mapping[str, object],
    cycle_rerun_status: Mapping[str, object],
) -> dict[str, object]:
    blockers: list[dict[str, object]] = []
    for component in _mapping_sequence(input_inventory.get("components")):
        classification = _text(component.get("classification"))
        if classification == "present_valid":
            continue
        for blocker in _string_sequence(component.get("blockers")) or (classification,):
            blockers.append(
                {
                    "component": component.get("component", ""),
                    "blocker": blocker,
                    "classification": classification,
                    "authorization_required": component.get("authorization_required", ""),
                }
            )
    for action in _mapping_sequence(refresh_actions.get("actions")):
        if _text(action.get("action")) == "not_refreshable_without_authorization":
            blockers.append(
                {
                    "component": action.get("component", ""),
                    "blocker": "not_refreshable_without_authorization",
                    "classification": "not_refreshable_without_authorization",
                    "authorization_required": action.get("authorization_required", ""),
                    "operator_request": action.get("operator_request", ""),
                }
            )
    cycle_final_state = _text(cycle_rerun_status.get("cycle_final_state"))
    if cycle_final_state and cycle_final_state not in ROUTER_READY_CYCLE_STATES:
        cycle_blockers = _string_sequence(cycle_rerun_status.get("cycle_blockers"))
        for blocker in cycle_blockers or (cycle_final_state,):
            blockers.append(
                {
                    "component": "cycle_rerun",
                    "blocker": blocker,
                    "classification": "cycle_blocked",
                    "authorization_required": "",
                }
            )
    blockers = _dedupe_blocker_records(blockers)
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_router_input_blockers",
        "blocker_count": len(blockers),
        "blockers": blockers,
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }


def _input_basis(
    *,
    input_inventory: Mapping[str, object],
    refresh_actions: Mapping[str, object],
    cycle_rerun_status: Mapping[str, object],
    refresh_mode: str,
) -> InputBasis:
    action_modes = {
        _text(action.get("refresh_mode"))
        for action in _mapping_sequence(refresh_actions.get("actions"))
        if action.get("performed") is True
    }
    cycle_basis = _text(cycle_rerun_status.get("input_basis"))
    bases = {
        basis
        for basis in (*action_modes, cycle_basis, _text(refresh_mode))
        if basis in INPUT_BASES
    }
    if "offline_fixture" in bases:
        return "offline_fixture"
    classifications = {
        _text(component.get("classification"))
        for component in _mapping_sequence(input_inventory.get("components"))
    }
    if "present_stale" in classifications:
        return "stale_local"
    if "local_replay" in bases:
        return "local_replay"
    return "local_replay"


def _final_state(
    *,
    input_inventory: Mapping[str, object],
    refresh_actions: Mapping[str, object],
    router_input_blockers: Mapping[str, object],
    cycle_rerun_status: Mapping[str, object],
    input_basis: InputBasis,
) -> FinalState:
    components = _mapping_sequence(input_inventory.get("components"))
    actions = _mapping_sequence(refresh_actions.get("actions"))
    classifications = {str(component.get("classification", "")) for component in components}
    authorization_requirements = {
        _text(component.get("authorization_required"))
        for component in components
        if _text(component.get("authorization_required"))
    }
    authorization_requirements.update(
        _text(action.get("authorization_required"))
        for action in actions
        if _text(action.get("action")) == "not_refreshable_without_authorization"
    )
    if "invalid_schema" in classifications:
        return "blocked_invalid_schema"
    if "broker_read" in authorization_requirements:
        return "blocked_requires_broker_read_authorization"
    if "market_data" in authorization_requirements:
        return "blocked_requires_market_data_authorization"
    if "paid_or_new_service" in authorization_requirements:
        return "blocked_requires_paid_or_new_service"

    cycle_final_state = _text(cycle_rerun_status.get("cycle_final_state"))
    repair_performed = any(action.get("performed") is True for action in actions)
    router_input_blocker_count = _int_or_none(router_input_blockers.get("blocker_count")) or 0
    if repair_performed and router_input_blocker_count:
        return "router_inputs_partially_repaired_cycle_blocked"
    if "present_stale" in classifications:
        return "blocked_stale_local_inputs"
    if "missing" in classifications:
        return "blocked_missing_local_inputs"
    if router_input_blocker_count:
        return "blocked"
    if cycle_final_state in ROUTER_READY_CYCLE_STATES:
        if input_basis == "offline_fixture":
            return "fixture_backed_cycle_rerun_complete"
        if input_basis == "local_replay" and repair_performed:
            return "local_replay_cycle_rerun_complete"
        return "router_inputs_ready_cycle_rerun_complete"
    if repair_performed:
        return "router_inputs_partially_repaired_cycle_blocked"
    return "blocked"


def _next_operator_action_payload(
    *,
    final_state: FinalState,
    router_input_blockers: Mapping[str, object],
    input_basis: InputBasis,
) -> dict[str, object]:
    action: NextOperatorAction = {
        "router_inputs_ready_cycle_rerun_complete": "review_no_submit_packet",
        "local_replay_cycle_rerun_complete": "review_local_replay_no_submit_packet",
        "fixture_backed_cycle_rerun_complete": "review_fixture_backed_no_submit_packet",
        "router_inputs_partially_repaired_cycle_blocked": "rerun_crypto_no_submit_operating_cycle",
        "blocked_missing_local_inputs": "provide_or_authorize_market_data_refresh",
        "blocked_stale_local_inputs": "provide_or_authorize_market_data_refresh",
        "blocked_invalid_schema": "repair_local_input_schema",
        "blocked_requires_broker_read_authorization": "authorize_scoped_paper_read",
        "blocked_requires_market_data_authorization": "provide_or_authorize_market_data_refresh",
        "blocked_requires_paid_or_new_service": "blocked",
        "blocked": "blocked",
    }[final_state]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_router_input_next_operator_action",
        "action": action,
        "final_state": final_state,
        "input_basis": input_basis,
        "data_basis": input_basis,
        "operator_request": _operator_request_for_final_state(final_state),
        "router_input_blocker_count": router_input_blockers.get("blocker_count", 0),
        "router_input_blockers_remaining": list(
            _mapping_sequence(router_input_blockers.get("blockers"))
        ),
        "blockers": list(_mapping_sequence(router_input_blockers.get("blockers"))),
        "fresh_authorization_required_for_order": True,
        "paper_submit_currently_authorized": False,
        "broker_action_permitted": False,
        "prior_authorizations_reusable": False,
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }


def _input_readiness(
    *,
    final_state: FinalState,
    input_inventory: Mapping[str, object],
    refresh_actions: Mapping[str, object],
    router_input_blockers: Mapping[str, object],
    cycle_rerun_status: Mapping[str, object],
    next_operator_action: Mapping[str, object],
    output_root: Path,
    as_of: datetime,
    input_basis: InputBasis,
) -> dict[str, object]:
    router_input_blocker_count = router_input_blockers.get("blocker_count", 0)
    router_input_blockers_remaining = list(
        _mapping_sequence(router_input_blockers.get("blockers"))
    )
    router_input_blocker_removed = _int_or_none(router_input_blocker_count) == 0
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_router_input_readiness",
        "as_of": as_of.isoformat(),
        "output_root": str(output_root),
        "final_state": final_state,
        "input_basis": input_basis,
        "data_basis": input_basis,
        "router_input_blocker_removed": router_input_blocker_removed,
        "router_input_blocker_removed_semantics": (
            "true_only_when_router_input_blocker_count_is_zero_not_cycle_readiness"
        ),
        "router_input_blocker_status": (
            "removed"
            if router_input_blocker_removed
            else "still_blocked"
        ),
        "cycle_rerun_status": cycle_rerun_status.get("cycle_final_state", ""),
        "next_operator_action": next_operator_action.get("action", ""),
        "classification_counts": _mapping(input_inventory.get("classification_counts")),
        "refresh_action_count": len(_mapping_sequence(refresh_actions.get("actions"))),
        "router_input_blocker_count": router_input_blocker_count,
        "router_input_blockers_remaining": router_input_blockers_remaining,
        "fresh_authorization_required_for_order": True,
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }


def _operating_record(packet: Mapping[str, object]) -> dict[str, object]:
    readiness = _mapping(packet.get("input_readiness"))
    next_action = _mapping(packet.get("next_operator_action"))
    cycle = _mapping(packet.get("cycle_rerun_status"))
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "crypto_router_input_refresh_packet",
        "as_of": packet.get("as_of", ""),
        "final_state": readiness.get("final_state", packet.get("final_state", "")),
        "input_basis": readiness.get("input_basis", packet.get("input_basis", "")),
        "data_basis": readiness.get("data_basis", packet.get("data_basis", "")),
        "router_input_blocker_removed": readiness.get("router_input_blocker_removed", False),
        "router_input_blocker_count": readiness.get("router_input_blocker_count", 0),
        "router_input_blockers_remaining": list(
            _mapping_sequence(readiness.get("router_input_blockers_remaining"))
        ),
        "cycle_final_state": cycle.get("cycle_final_state", ""),
        "next_operator_action": next_action.get("action", ""),
        "fresh_authorization_required_for_order": True,
        "labels": list(REQUIRED_LABELS),
        "profit_claim": "none",
        **_false_flags(),
    }


def _operator_request_for_final_state(final_state: FinalState) -> str:
    if final_state == "blocked_requires_broker_read_authorization":
        return _operator_request("broker_read")
    if final_state in {
        "blocked_requires_market_data_authorization",
        "blocked_missing_local_inputs",
        "blocked_stale_local_inputs",
    }:
        return _operator_request("market_data")
    if final_state == "blocked_invalid_schema":
        return "repair local crypto router input schema, then rerun the refresh packet; no broker action is authorized."
    if final_state == "router_inputs_ready_cycle_rerun_complete":
        return "review the no-submit packet; any future order still requires fresh explicit authorization."
    if final_state == "local_replay_cycle_rerun_complete":
        return (
            "review the local-replay no-submit packet only; this is not fresh broker "
            "or market-data authorization for any order."
        )
    if final_state == "fixture_backed_cycle_rerun_complete":
        return (
            "review the fixture-backed no-submit packet only; fixture-backed readiness "
            "must not be treated as fresh/current broker or market-data readiness."
        )
    if final_state == "router_inputs_partially_repaired_cycle_blocked":
        return "review cycle blockers and rerun the no-submit operating cycle after local inputs are corrected."
    return "blocked; review router input blockers before any paper action."


def _operator_request(required: str) -> str:
    if required == "broker_read":
        return (
            "authorize one scoped read-only paper crypto visibility/orderability refresh; "
            "no submit, cancel, replace, close, liquidate, or live endpoint is authorized."
        )
    if required == "market_data":
        return (
            "provide a current local crypto bars CSV or authorize a scoped read-only "
            "market-data refresh; no broker mutation or paper submit is authorized."
        )
    if required == "paid_or_new_service":
        return "choose and authorize a paid or new external data service before any refresh."
    return "review_no_submit_packet"


def _components_with_classification(
    components: Sequence[Mapping[str, object]],
    classification: str,
) -> tuple[Mapping[str, object], ...]:
    return tuple(
        component
        for component in components
        if _text(component.get("classification")) == classification
    )


def _needs_broker_read(components: Sequence[Mapping[str, object]]) -> bool:
    return any(
        _text(component.get("authorization_required")) == "broker_read"
        or bool(set(_string_sequence(component.get("blockers"))) & BROKER_READ_BLOCKERS)
        for component in components
    )


def _needs_market_data(components: Sequence[Mapping[str, object]]) -> bool:
    return any(
        _text(component.get("authorization_required")) == "market_data"
        or bool(set(_string_sequence(component.get("blockers"))) & MARKET_DATA_BLOCKERS)
        for component in components
    )


def _read_csv_rows(path: Path) -> tuple[Mapping[str, str], ...]:
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        raise ValueError("CSV header is required.")
    return tuple(dict(row) for row in reader)


def _parse_bar_row(row: Mapping[str, object]) -> dict[str, object] | None:
    symbol = _first_text(row, "symbol", "S")
    timestamp_text = _first_text(row, "timestamp", "datetime", "date", "t")
    close_text = _first_text(row, "close", "c")
    if not symbol or not timestamp_text or not close_text:
        return None
    try:
        close = _positive_decimal(close_text)
        timestamp = _parse_timestamp(timestamp_text)
    except (ValueError, InvalidOperation):
        return None
    return {
        "symbol": _normalize_symbol(symbol),
        "timestamp": timestamp,
        "close": close,
    }


def _read_json_mapping(path: Path) -> Mapping[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("JSON object is required.")
    return payload


def _parse_timestamp(value: object) -> datetime:
    text = _text(value)
    if not text:
        raise ValueError("timestamp is required.")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _utc_datetime(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif type(value) is str and value.strip():
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    else:
        raise ValueError(f"{field_name} must be a timezone-aware UTC datetime.")
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must include timezone information.")
    return parsed.astimezone(UTC)


def _positive_decimal(value: object) -> Decimal:
    parsed = Decimal(str(value))
    if not parsed.is_finite() or parsed <= Decimal("0"):
        raise InvalidOperation("positive finite decimal required")
    return parsed


def _normalize_symbol(value: object) -> str:
    return "".join(ch for ch in _text(value).upper() if ch.isalnum())


def _dedupe_blocker_records(
    blockers: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    seen: set[tuple[str, str, str]] = set()
    records: list[dict[str, object]] = []
    for blocker in blockers:
        key = (
            _text(blocker.get("component")),
            _text(blocker.get("blocker")),
            _text(blocker.get("classification")),
        )
        if key in seen:
            continue
        seen.add(key)
        records.append(dict(blocker))
    return records


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
    wanted = {_field_lookup_key(field_name) for field_name in field_names}
    for key, value in row.items():
        if _field_lookup_key(key) in wanted:
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


def _field_lookup_key(value: object) -> str:
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def _false_flags() -> dict[str, bool]:
    return {field_name: False for field_name in FALSE_SAFETY_FIELDS}


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
        prog="crypto-router-input-refresh-packet",
        description="Build a no-submit crypto router input refresh packet.",
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
    parser.add_argument("--allow-fixture-repair", action="store_true")
    parser.add_argument("--request-paper-read-repair", action="store_true")
    parser.add_argument("--request-market-data-refresh", action="store_true")
    parser.add_argument("--as-of", default="")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    packet = run_crypto_router_input_refresh_packet(
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
        allow_fixture_repair=args.allow_fixture_repair,
        request_paper_read_repair=args.request_paper_read_repair,
        request_market_data_refresh=args.request_market_data_refresh,
        as_of=args.as_of or None,
        write_artifacts=True,
    )
    if args.format == "json":
        print(json.dumps(_json_safe(packet), sort_keys=True))
    else:
        print(render_refresh_packet_text(packet))
    final_state = _text(packet.get("final_state"))
    return (
        0
        if final_state
        in {
            "router_inputs_ready_cycle_rerun_complete",
            "local_replay_cycle_rerun_complete",
            "fixture_backed_cycle_rerun_complete",
        }
        else 2
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
