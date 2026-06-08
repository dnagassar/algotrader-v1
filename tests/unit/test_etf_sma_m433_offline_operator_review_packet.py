from __future__ import annotations

import ast
import json
from pathlib import Path

import algotrader.cli as cli_module
from algotrader.execution.etf_sma_m433_offline_operator_review_packet import (
    EtfSmaM433OfflineOperatorReviewPacketConfig,
    build_etf_sma_m433_offline_operator_review_packet,
    render_etf_sma_m433_offline_operator_review_packet_json,
    write_etf_sma_m433_offline_operator_review_packet_jsonl,
)


MODULE_PATH = Path(
    "src/algotrader/execution/etf_sma_m433_offline_operator_review_packet.py"
)
_COMMAND = "etf-sma-m433-offline-operator-review-packet"
_TARGET_CLIENT_ORDER_ID = "paper-order-close-m376_spy_paper_close_submit"
_TARGET_BROKER_ORDER_ID = "dbb32dd3-58bf-49ea-b9b1-9aa44e85002d"
_READY_DECISION = "ready_for_separate_operator_authorized_paper_buy_submit_milestone"
_READY_NEXT_MILESTONE = "M434_operator_authorized_tiny_spy_paper_buy_submit"
_SAFETY_FALSE_FIELDS = (
    "submit_authorized",
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_read_only",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_ALLOWED_IMPORTS = {
    "__future__",
    "collections.abc",
    "dataclasses",
    "decimal",
    "json",
    "pathlib",
    "typing",
    "algotrader.errors",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "alpaca_trade_api",
    "algotrader.execution.alpaca_adapter",
    "algotrader.execution.alpaca_broker",
    "algotrader.execution.alpaca_client",
    "algotrader.execution.alpaca_sdk_client",
    "algotrader.runtime",
    "httpx",
    "os",
    "requests",
    "socket",
    "urllib",
)
_FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_all_positions",
    "close_position",
    "connect",
    "create_connection",
    "create_order",
    "delete",
    "getenv",
    "liquidate",
    "load_config",
    "replace_order",
    "request",
    "retry",
    "socket",
    "socket.socket",
    "submit_order",
    "urlopen",
}


def test_terminal_filled_flat_buy_preview_is_ready_for_separate_m434(
    tmp_path: Path,
) -> None:
    reconciliation_path = _write_jsonl(
        tmp_path / "m432_reconciliation.jsonl",
        _m432_reconciliation(),
    )
    preview_path = _write_jsonl(tmp_path / "m432_preview.jsonl", _m432_preview())

    payload = build_etf_sma_m433_offline_operator_review_packet(
        _config(reconciliation_path, preview_path)
    )

    assert payload["run_id"] == "unit_m433"
    assert payload["milestone"] == "M433"
    assert payload["review_scope"] == "offline_operator_review_packet"
    assert payload["source_reconciliation_artifact"] == str(reconciliation_path)
    assert payload["source_preview_artifact"] == str(preview_path)
    assert payload["target_client_order_id"] == _TARGET_CLIENT_ORDER_ID
    assert payload["target_broker_order_id"] == _TARGET_BROKER_ORDER_ID
    assert payload["m376_reconciliation_decision"] == "m376_terminal_filled"
    assert payload["m376_terminal_state"] == "terminal_filled"
    assert payload["m376_observed_order_status"] == "filled"
    assert payload["m376_observed_filled_qty"] == "0.033172072"
    assert payload["m376_observed_remaining_qty"] == "0E-9"
    assert payload["open_order_count"] == 0
    assert payload["open_spy_order_count"] == 0
    assert payload["spy_position_present"] is False
    assert payload["spy_position_qty"] == "0"
    assert payload["unexpected_position_symbols"] == []
    assert payload["cycle_preview_status"] == "offline_cycle_preview_computed"
    assert payload["cycle_decision"] == "buy_preview"
    assert payload["sma_posture"] == "risk_on"
    assert payload["paper_preview_computed"] is True
    assert payload["readiness_decision"] == _READY_DECISION
    assert payload["next_required_milestone"] == _READY_NEXT_MILESTONE
    assert payload["operator_approval_required"] is True
    assert payload["blockers"] == []
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"
    _assert_m433_offline_only(payload)


def test_nonterminal_or_open_m376_blocks(tmp_path: Path) -> None:
    reconciliation = _m432_reconciliation(
        observed_order_status="new",
        observed_filled_qty="0",
        observed_remaining_qty="0.033172072",
        open_order_count=1,
        open_spy_order_count=1,
        reconciliation_decision="m376_order_nonterminal",
        terminal_state=False,
    )
    reconciliation_path = _write_jsonl(tmp_path / "m432_reconciliation.jsonl", reconciliation)
    preview_path = _write_jsonl(tmp_path / "m432_preview.jsonl", _m432_preview())

    payload = build_etf_sma_m433_offline_operator_review_packet(
        _config(reconciliation_path, preview_path)
    )

    assert payload["readiness_decision"] == "blocked_open_order_present"
    assert "open_order_present" in payload["blockers"]
    assert "m376_order_nonterminal" in payload["blockers"]
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    _assert_m433_offline_only(payload)


def test_missing_m432_reconciliation_blocks_as_ambiguous(tmp_path: Path) -> None:
    preview_path = _write_jsonl(tmp_path / "m432_preview.jsonl", _m432_preview())

    payload = build_etf_sma_m433_offline_operator_review_packet(
        _config(tmp_path / "missing_reconciliation.jsonl", preview_path)
    )

    assert (
        payload["readiness_decision"]
        == "blocked_m432_evidence_incomplete_or_ambiguous"
    )
    assert "m432_reconciliation_artifact_not_found" in payload["blockers"]
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    _assert_m433_offline_only(payload)


def test_order_not_found_without_terminal_proof_blocks_as_ambiguous(
    tmp_path: Path,
) -> None:
    reconciliation = _m432_reconciliation(
        exact_order_found=False,
        observed_order_found=False,
        reconciliation_decision="m376_order_not_found",
        observed_order_status="",
        terminal_state=False,
    )
    reconciliation_path = _write_jsonl(tmp_path / "m432_reconciliation.jsonl", reconciliation)
    preview_path = _write_jsonl(tmp_path / "m432_preview.jsonl", _m432_preview())

    payload = build_etf_sma_m433_offline_operator_review_packet(
        _config(reconciliation_path, preview_path)
    )

    assert (
        payload["readiness_decision"]
        == "blocked_m432_evidence_incomplete_or_ambiguous"
    )
    assert "m376_terminal_filled_not_proven" in payload["blockers"]
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    _assert_m433_offline_only(payload)


def test_non_buy_preview_does_not_produce_submit_readiness(tmp_path: Path) -> None:
    reconciliation_path = _write_jsonl(
        tmp_path / "m432_reconciliation.jsonl",
        _m432_reconciliation(),
    )
    preview_path = _write_jsonl(
        tmp_path / "m432_preview.jsonl",
        _m432_preview(cycle_decision="hold/noop", sma_posture="risk_off"),
    )

    payload = build_etf_sma_m433_offline_operator_review_packet(
        _config(reconciliation_path, preview_path)
    )

    assert payload["cycle_decision"] == "hold/noop"
    assert payload["readiness_decision"] == "no_submit_path_from_current_preview"
    assert payload["readiness_decision"] != _READY_DECISION
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    _assert_m433_offline_only(payload)


def test_preview_incompatible_blocks_as_ambiguous(tmp_path: Path) -> None:
    reconciliation_path = _write_jsonl(
        tmp_path / "m432_reconciliation.jsonl",
        _m432_reconciliation(),
    )
    preview = _m432_preview()
    preview.update({"paper_preview_computed": False, "blockers": ["preview_not_computed"]})
    preview_path = _write_jsonl(tmp_path / "m432_preview.jsonl", preview)

    payload = build_etf_sma_m433_offline_operator_review_packet(
        _config(reconciliation_path, preview_path)
    )

    assert (
        payload["readiness_decision"]
        == "blocked_m432_evidence_incomplete_or_ambiguous"
    )
    assert "m432_preview_paper_preview_computed_not_true" in payload["blockers"]
    assert "m432_preview_blockers_present" in payload["blockers"]
    _assert_m433_offline_only(payload)


def test_m433_output_is_offline_only_even_when_m432_read_used_network(
    tmp_path: Path,
) -> None:
    reconciliation = _m432_reconciliation()
    reconciliation["broker_read_only"] = True
    reconciliation["network_access_attempted"] = True
    reconciliation["credential_access_attempted"] = True
    reconciliation_path = _write_jsonl(tmp_path / "m432_reconciliation.jsonl", reconciliation)
    preview_path = _write_jsonl(tmp_path / "m432_preview.jsonl", _m432_preview())

    payload = build_etf_sma_m433_offline_operator_review_packet(
        _config(reconciliation_path, preview_path)
    )

    assert payload["readiness_decision"] == _READY_DECISION
    _assert_m433_offline_only(payload)


def test_writes_exactly_one_deterministic_jsonl_record(tmp_path: Path) -> None:
    reconciliation_path = _write_jsonl(
        tmp_path / "m432_reconciliation.jsonl",
        _m432_reconciliation(),
    )
    preview_path = _write_jsonl(tmp_path / "m432_preview.jsonl", _m432_preview())
    payload = build_etf_sma_m433_offline_operator_review_packet(
        _config(reconciliation_path, preview_path)
    )
    output_path = tmp_path / "m433.jsonl"

    result = write_etf_sma_m433_offline_operator_review_packet_jsonl(
        payload,
        output_path,
    )
    records = _read_jsonl(output_path)

    assert result.record_count == 1
    assert result.submit_authorized is False
    assert result.submitted is False
    assert result.mutated is False
    assert result.broker_read_only is False
    assert records == [payload]
    assert render_etf_sma_m433_offline_operator_review_packet_json(payload) == (
        render_etf_sma_m433_offline_operator_review_packet_json(payload)
    )


def test_cli_writes_packet_before_runtime_config_loading(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    reconciliation_path = _write_jsonl(
        tmp_path / "m432_reconciliation.jsonl",
        _m432_reconciliation(),
    )
    preview_path = _write_jsonl(tmp_path / "m432_preview.jsonl", _m432_preview())
    run_log = tmp_path / "m433_cli.jsonl"

    def forbidden_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("M433 offline command must not load runtime config")

    def forbidden_broker(*args: object, **kwargs: object) -> object:
        raise AssertionError("M433 offline command must not build a broker")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)

    assert cli_module.main(
        [
            _COMMAND,
            "--m432-reconciliation",
            str(reconciliation_path),
            "--m432-preview",
            str(preview_path),
            "--run-log",
            str(run_log),
            "--run-id",
            "unit_m433_cli",
            "--format",
            "json",
        ]
    ) == 0

    payload = json.loads(run_log.read_text(encoding="utf-8"))
    stdout = capsys.readouterr().out
    assert json.loads(stdout) == payload
    assert payload["run_id"] == "unit_m433_cli"
    assert payload["readiness_decision"] == _READY_DECISION
    _assert_m433_offline_only(payload)


def test_module_imports_no_broker_sdk_credentials_network_or_mutation_calls() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _config(
    reconciliation_path: Path,
    preview_path: Path,
) -> EtfSmaM433OfflineOperatorReviewPacketConfig:
    return EtfSmaM433OfflineOperatorReviewPacketConfig(
        run_id="unit_m433",
        m432_reconciliation_path=reconciliation_path,
        m432_preview_path=preview_path,
    )


def _m432_reconciliation(
    *,
    observed_order_status: str = "filled",
    observed_filled_qty: str = "0.033172072",
    observed_remaining_qty: str = "0E-9",
    open_order_count: int = 0,
    open_spy_order_count: int = 0,
    reconciliation_decision: str = "m376_terminal_filled",
    terminal_state: object = True,
    exact_order_found: bool = True,
    observed_order_found: bool = True,
) -> dict[str, object]:
    return {
        "account_observation_available": True,
        "blockers": [],
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_order_id": _TARGET_BROKER_ORDER_ID,
        "broker_read_only": True,
        "client_order_id": _TARGET_CLIENT_ORDER_ID,
        "credential_access_attempted": True,
        "credentials_redacted": True,
        "exact_order_found": exact_order_found,
        "live_authorized": False,
        "milestone": "M432",
        "mismatches": [],
        "mutated": False,
        "network_access_attempted": True,
        "observed_filled_qty": observed_filled_qty,
        "observed_order_found": observed_order_found,
        "observed_order_status": observed_order_status,
        "observed_remaining_qty": observed_remaining_qty,
        "open_order_count": open_order_count,
        "open_order_present": open_order_count > 0,
        "open_spy_order_count": open_spy_order_count,
        "open_spy_order_present": open_spy_order_count > 0,
        "paper_lab_only": True,
        "profit_claim": "none",
        "reconciliation_decision": reconciliation_decision,
        "record_type": "m432_m376_read_only_reconciliation_refresh",
        "run_id": "m432_m376_read_only_reconciliation_refresh",
        "schema_version": "1",
        "source_terminal_state": "terminal" if terminal_state is True else "nonterminal",
        "spy_position_present": False,
        "spy_position_qty": "0",
        "submitted": False,
        "symbol": "SPY",
        "target_broker_order_id": _TARGET_BROKER_ORDER_ID,
        "target_client_order_id": _TARGET_CLIENT_ORDER_ID,
        "terminal_state": terminal_state,
        "trade_recommendation": "none",
        "unexpected_position_symbols": [],
    }


def _m432_preview(
    *,
    cycle_decision: str = "buy_preview",
    sma_posture: str = "risk_on",
) -> dict[str, object]:
    return {
        "blockers": [],
        "broker_action_performed": False,
        "broker_state_loaded": False,
        "command": "etf-sma-authorized-offline-cycle-preview",
        "credential_access_attempted": False,
        "cycle_decision": cycle_decision,
        "cycle_preview_status": "offline_cycle_preview_computed",
        "live_authorized": False,
        "milestone": "M431",
        "mutated": False,
        "network_access_attempted": False,
        "paper_preview_computed": True,
        "profit_claim": "none",
        "record_type": "etf_sma_authorized_offline_cycle_preview",
        "run_id": "m432_authorized_offline_cycle_preview_rerun",
        "schema_version": "1",
        "sma_posture": sma_posture,
        "spy_position_present": False,
        "spy_position_qty": "",
        "submitted": False,
        "symbol": "SPY",
        "trade_recommendation": "none",
    }


def _write_jsonl(path: Path, *records: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record, sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _assert_m433_offline_only(payload: dict[str, object]) -> None:
    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False
    assert payload["operator_approval_required"] is True
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"


def _tree() -> ast.AST:
    return ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))


def _import_references() -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def _matches_forbidden_prefix(module: str, prefixes: tuple[str, ...]) -> bool:
    return any(
        module == prefix or module.startswith(f"{prefix}.")
        for prefix in prefixes
    )


def _call_names() -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""
