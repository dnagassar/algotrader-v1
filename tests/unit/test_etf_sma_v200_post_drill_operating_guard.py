from __future__ import annotations

import ast
import json
from pathlib import Path

from algotrader.execution.etf_sma_v200_post_drill_operating_guard import (
    POST_DRILL_GUARD_BLOCKED_LIVE_ACTIVITY,
    POST_DRILL_GUARD_BLOCKED_PACKET_MALFORMED,
    POST_DRILL_GUARD_BLOCKED_PACKET_MISSING,
    POST_DRILL_GUARD_BLOCKED_UNEXPECTED_MUTATION_STATE,
    POST_DRILL_GUARD_BLOCKED_UNRESOLVED_OUTCOME,
    POST_DRILL_GUARD_READY,
    POST_DRILL_GUARD_SAFETY_LABELS,
    run_v200_post_drill_operating_guard,
)


MODULE_PATH = Path(
    "src/algotrader/execution/etf_sma_v200_post_drill_operating_guard.py"
)
GENERATED_AT = "2026-06-26T21:43:57.883596+00:00"
CLIENT_ORDER_ID = "v192-spy-43fb12a5d4aa5fbf4990aa7a"
FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "os",
    "requests",
    "socket",
    "urllib",
)
FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "cancel_order_by_id",
    "connect",
    "create_connection",
    "delete",
    "getenv",
    "load_config",
    "replace_order",
    "request",
    "socket.socket",
    "submit_order",
    "submit_order_request",
    "urlopen",
}


def test_submitted_cancel_confirmed_packet_produces_ready_guard(
    tmp_path: Path,
) -> None:
    source_path = _write_source_packet(tmp_path, _source_packet())
    output_root = tmp_path / "runs" / "paper_lab" / "v200"

    packet = run_v200_post_drill_operating_guard(
        source_paper_drill_packet_path=source_path,
        output_root=output_root,
        timestamp=GENERATED_AT,
    )

    assert packet["post_drill_guard_classification"] == POST_DRILL_GUARD_READY
    assert packet["last_paper_drill_outcome"] == (
        "paper_drill_submitted_cancel_confirmed"
    )
    assert packet["last_authorization_consumed"] is True
    assert packet["authorization_consumed_evidence_present"] is True
    assert packet["client_order_id"] == CLIENT_ORDER_ID
    assert packet["submit_attempted_from_source_packet"] is True
    assert packet["submit_status_from_source_packet"] == "accepted"
    assert packet["cancel_attempted_from_source_packet"] is True
    assert packet["cancel_confirmed_from_source_packet"] is True
    assert packet["fill_status_from_source_packet"] == "unfilled"
    assert packet["final_broker_order_status_from_source_packet"] == "canceled"
    assert packet["source_broker_read_performed"] is True
    assert packet["source_broker_mutation_performed"] is True
    assert packet["source_paper_submit_performed"] is True
    assert packet["source_paper_cancel_performed"] is True
    assert packet["source_live_read_performed"] is False
    assert packet["source_live_mutation_performed"] is False
    assert packet["source_live_trading_performed"] is False
    assert packet["next_operator_action"] == (
        "new_explicit_operator_authorization_required_before_any_future_paper_action"
    )
    assert packet["safety_labels"] == list(POST_DRILL_GUARD_SAFETY_LABELS)
    _assert_guard_denies_paper_action(packet)
    _assert_artifacts(output_root, packet)


def test_missing_packet_blocks_closed(tmp_path: Path) -> None:
    packet = run_v200_post_drill_operating_guard(
        source_paper_drill_packet_path=tmp_path / "missing" / "paper_drill_packet.json",
        output_root=tmp_path / "runs" / "paper_lab" / "v200",
        timestamp=GENERATED_AT,
    )

    assert packet["post_drill_guard_classification"] == (
        POST_DRILL_GUARD_BLOCKED_PACKET_MISSING
    )
    assert packet["blocker"] == "source_v199_paper_drill_packet_missing"
    assert packet["source_paper_drill_packet_found"] is False
    assert packet["last_authorization_consumed"] is False
    _assert_guard_denies_paper_action(packet)


def test_malformed_packet_blocks_closed(tmp_path: Path) -> None:
    source_path = tmp_path / "paper_drill_packet.json"
    source_path.write_text("{not-json", encoding="utf-8")

    packet = run_v200_post_drill_operating_guard(
        source_paper_drill_packet_path=source_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v200",
        timestamp=GENERATED_AT,
    )

    assert packet["post_drill_guard_classification"] == (
        POST_DRILL_GUARD_BLOCKED_PACKET_MALFORMED
    )
    assert packet["blocker"] == "invalid_json"
    assert packet["source_paper_drill_packet_parsed"] is False
    _assert_guard_denies_paper_action(packet)


def test_unresolved_order_outcome_blocks_closed(tmp_path: Path) -> None:
    source_path = _write_source_packet(
        tmp_path,
        _source_packet(outcome_classification="paper_drill_unresolved_order_outcome"),
    )

    packet = run_v200_post_drill_operating_guard(
        source_paper_drill_packet_path=source_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v200",
        timestamp=GENERATED_AT,
    )

    assert packet["post_drill_guard_classification"] == (
        POST_DRILL_GUARD_BLOCKED_UNRESOLVED_OUTCOME
    )
    assert packet["blocker"] == "source_packet_outcome_not_post_drill_ready"
    assert packet["last_authorization_consumed"] is False
    _assert_guard_denies_paper_action(packet)


def test_unrecognized_order_outcome_blocks_closed(tmp_path: Path) -> None:
    source_path = _write_source_packet(
        tmp_path,
        _source_packet(outcome_classification="paper_drill_new_unknown_state"),
    )

    packet = run_v200_post_drill_operating_guard(
        source_paper_drill_packet_path=source_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v200",
        timestamp=GENERATED_AT,
    )

    assert packet["post_drill_guard_classification"] == (
        POST_DRILL_GUARD_BLOCKED_UNRESOLVED_OUTCOME
    )
    assert packet["blocker"] == "source_packet_unrecognized_v199_outcome"
    _assert_guard_denies_paper_action(packet)


def test_source_packet_with_live_activity_blocks_closed(tmp_path: Path) -> None:
    source = _source_packet()
    source["live_read_performed"] = True
    source_path = _write_source_packet(tmp_path, source)

    packet = run_v200_post_drill_operating_guard(
        source_paper_drill_packet_path=source_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v200",
        timestamp=GENERATED_AT,
    )

    assert packet["post_drill_guard_classification"] == (
        POST_DRILL_GUARD_BLOCKED_LIVE_ACTIVITY
    )
    assert packet["blocker"] == "source_packet_live_activity:live_read_performed"
    assert packet["last_authorization_consumed"] is False
    _assert_guard_denies_paper_action(packet)


def test_missing_authorization_consumed_evidence_blocks_closed(
    tmp_path: Path,
) -> None:
    source = _source_packet()
    del source["operator_authorized_once"]
    source["safety_labels"] = [
        label for label in source["safety_labels"] if label != "operator_authorized_once"
    ]
    source_path = _write_source_packet(tmp_path, source)

    packet = run_v200_post_drill_operating_guard(
        source_paper_drill_packet_path=source_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v200",
        timestamp=GENERATED_AT,
    )

    assert packet["post_drill_guard_classification"] == (
        POST_DRILL_GUARD_BLOCKED_UNEXPECTED_MUTATION_STATE
    )
    assert packet["blocker"] == "missing_authorization_consumed_evidence"
    assert packet["authorization_consumed_evidence_present"] is False
    assert packet["last_authorization_consumed"] is False
    _assert_guard_denies_paper_action(packet)


def test_unexpected_source_mutation_state_blocks_closed(tmp_path: Path) -> None:
    source = _source_packet()
    source["paper_cancel_performed"] = False
    source_path = _write_source_packet(tmp_path, source)

    packet = run_v200_post_drill_operating_guard(
        source_paper_drill_packet_path=source_path,
        output_root=tmp_path / "runs" / "paper_lab" / "v200",
        timestamp=GENERATED_AT,
    )

    assert packet["post_drill_guard_classification"] == (
        POST_DRILL_GUARD_BLOCKED_UNEXPECTED_MUTATION_STATE
    )
    assert packet["blocker"] == "source_paper_cancel_performed_not_true"
    assert packet["last_authorization_consumed"] is False
    _assert_guard_denies_paper_action(packet)


def test_source_directory_path_resolves_to_packet_file(tmp_path: Path) -> None:
    source_path = _write_source_packet(tmp_path, _source_packet())
    source_root = source_path.parent

    packet = run_v200_post_drill_operating_guard(
        source_paper_drill_packet_path=source_root,
        output_root=tmp_path / "runs" / "paper_lab" / "v200",
        timestamp=GENERATED_AT,
    )

    assert packet["post_drill_guard_classification"] == POST_DRILL_GUARD_READY
    assert packet["source_v199_paper_drill_packet_path"] == str(source_path)
    _assert_guard_denies_paper_action(packet)


def test_module_imports_no_broker_sdk_credentials_network_or_mutation_calls() -> None:
    imports = _import_references()

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(FORBIDDEN_CALL_NAMES)


def _source_packet(
    *,
    outcome_classification: str = "paper_drill_submitted_cancel_confirmed",
) -> dict[str, object]:
    return {
        "packet_version": "v199_authorized_bounded_spy_paper_drill_packet_v1",
        "run_id": "v199_authorized_bounded_spy_paper_drill",
        "timestamp": GENERATED_AT,
        "generated_at": GENERATED_AT,
        "outcome_classification": outcome_classification,
        "symbol": "SPY",
        "side": "buy",
        "order_type": "market",
        "time_in_force": "day",
        "notional": "25.00",
        "quantity": "",
        "cap": "25.00",
        "client_order_id": CLIENT_ORDER_ID,
        "deterministic_client_order_id": CLIENT_ORDER_ID,
        "actual_submitted_request_fields": {
            "asset_class": "equity",
            "client_order_id": CLIENT_ORDER_ID,
            "notional": "25.00",
            "order_type": "market",
            "quantity": "",
            "side": "buy",
            "symbol": "SPY",
            "time_in_force": "day",
        },
        "projected_request_fields": {
            "cap": "25.00",
            "cap_kind": "notional",
            "client_order_id": CLIENT_ORDER_ID,
            "deterministic_client_order_id": CLIENT_ORDER_ID,
            "notional": "25.00",
            "order_type": "market",
            "quantity": "",
            "side": "buy",
            "symbol": "SPY",
            "time_in_force": "day",
        },
        "submit_attempted": True,
        "submit_status": "accepted",
        "cancel_attempted": True,
        "cancel_confirmed": True,
        "fill_status": "unfilled",
        "final_broker_order_status": "canceled",
        "broker_read_performed": True,
        "broker_mutation_performed": True,
        "paper_submit_performed": True,
        "paper_cancel_performed": True,
        "live_read_performed": False,
        "live_mutation_performed": False,
        "live_trading_performed": False,
        "explicit_authorization_phrase_observed": True,
        "operator_authorized_once": True,
        "paper_lab_only": True,
        "not_live_authorized": True,
        "not_live_trading": True,
        "profit_claim": "none",
        "safety_labels": [
            "paper_lab_only",
            "bounded_paper_drill",
            "not_live_authorized",
            "not_live_trading",
            "profit_claim=none",
            "operator_authorized_once",
        ],
    }


def _write_source_packet(root: Path, payload: dict[str, object]) -> Path:
    path = root / "source" / "paper_drill_packet.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _assert_guard_denies_paper_action(packet: dict[str, object]) -> None:
    assert packet["paper_submit_authorized"] is False
    assert packet["paper_cancel_authorized"] is False
    assert packet["next_paper_action_requires_new_authorization"] is True
    assert packet["broker_read_performed"] is False
    assert packet["broker_mutation_performed"] is False
    assert packet["paper_submit_performed"] is False
    assert packet["paper_cancel_performed"] is False
    assert packet["live_read_performed"] is False
    assert packet["live_mutation_performed"] is False
    assert packet["live_trading_performed"] is False


def _assert_artifacts(output_root: Path, packet: dict[str, object]) -> None:
    paths = packet["artifact_paths"]
    for artifact_path in paths.values():
        assert Path(artifact_path).exists()
    assert json.loads(Path(paths["post_drill_guard_packet"]).read_text()) == packet
    records = [
        json.loads(line)
        for line in Path(paths["post_drill_guard_record"]).read_text().splitlines()
    ]
    assert records == [packet]
    brief = Path(paths["post_drill_guard_brief"]).read_text(encoding="utf-8")
    assert "v2.00 Post-Drill Operating Guard" in brief
    manifest = json.loads(Path(paths["manifest"]).read_text())
    assert manifest["post_drill_guard_classification"] == (
        packet["post_drill_guard_classification"]
    )
    assert manifest["paper_submit_authorized"] is False
    assert manifest["paper_cancel_authorized"] is False


def _import_references() -> set[str]:
    imports: set[str] = set()
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            prefix = "." * node.level
            imports.add(f"{prefix}{node.module}")
    return imports


def _call_names() -> set[str]:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    return {_call_name(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)}


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _matches_forbidden_prefix(module: str, prefixes: tuple[str, ...]) -> bool:
    cleaned = module.lstrip(".")
    return any(
        cleaned == prefix or cleaned.startswith(f"{prefix}.")
        for prefix in prefixes
    )
