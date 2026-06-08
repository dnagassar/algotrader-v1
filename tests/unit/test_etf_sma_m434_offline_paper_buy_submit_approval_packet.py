from __future__ import annotations

import ast
import json
from pathlib import Path

import algotrader.cli as cli_module
from algotrader.execution.etf_sma_m434_offline_paper_buy_submit_approval_packet import (
    EtfSmaM434OfflinePaperBuySubmitApprovalPacketConfig,
    build_etf_sma_m434_offline_paper_buy_submit_approval_packet,
    render_etf_sma_m434_offline_paper_buy_submit_approval_packet_json,
    write_etf_sma_m434_offline_paper_buy_submit_approval_packet_jsonl,
)


MODULE_PATH = Path(
    "src/algotrader/execution/"
    "etf_sma_m434_offline_paper_buy_submit_approval_packet.py"
)
_COMMAND = "etf-sma-m434-offline-buy-submit-approval-packet"
_READY_M433_DECISION = (
    "ready_for_separate_operator_authorized_paper_buy_submit_milestone"
)
_READY_APPROVAL_DECISION = "ready_for_explicit_operator_authorization"
_READY_NEXT_MILESTONE = "M435_operator_authorized_tiny_spy_paper_buy_submit"
_SOURCE_NEXT_MILESTONE = "M434_operator_authorized_tiny_spy_paper_buy_submit"
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


def test_ready_m433_packet_produces_m434_operator_authorization_readiness(
    tmp_path: Path,
) -> None:
    m433_path = _write_jsonl(tmp_path / "m433.jsonl", _m433_review())

    payload = build_etf_sma_m434_offline_paper_buy_submit_approval_packet(
        _config(m433_path)
    )

    assert payload["run_id"] == "unit_m434"
    assert payload["milestone"] == "M434"
    assert payload["approval_scope"] == "offline_paper_buy_submit_approval_packet"
    assert payload["source_m433_artifact"] == str(m433_path)
    assert payload["source_m433_readiness_decision"] == _READY_M433_DECISION
    assert payload["source_next_required_milestone"] == _SOURCE_NEXT_MILESTONE
    assert payload["symbol"] == "SPY"
    assert payload["side"] == "buy"
    assert payload["asset_class"] == "equity"
    assert payload["intended_order_type"] == "market"
    assert payload["intended_time_in_force"] == "day"
    assert payload["paper_only"] is True
    assert payload["operator_approval_required"] is True
    assert payload["approval_decision"] == _READY_APPROVAL_DECISION
    assert payload["next_required_milestone"] == _READY_NEXT_MILESTONE
    assert payload["blockers"] == []
    assert payload["required_single_attempt_submit"] is True
    assert "APP_PROFILE must be paper inside the scoped submit shell." in payload[
        "required_fresh_pre_submit_checks"
    ]
    assert "Symbol allowlist must be SPY only." in payload["required_submit_gates"]
    assert payload["required_duplicate_id_guard"] == [
        "Duplicate client_order_id must be checked before submit."
    ]
    assert payload["required_open_order_guard"] == ["No open SPY order may exist."]
    assert payload["required_position_guard"] == [
        "No unexpected non-SPY position may exist.",
        "SPY position must be absent/zero before a buy submit.",
    ]
    assert "Credentials may never be printed." in payload["required_redaction_check"]
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"
    _assert_m434_offline_only(payload)


def test_non_ready_m433_readiness_blocks_submit_approval(tmp_path: Path) -> None:
    m433_path = _write_jsonl(
        tmp_path / "m433.jsonl",
        _m433_review(readiness_decision="blocked_open_order_present"),
    )

    payload = build_etf_sma_m434_offline_paper_buy_submit_approval_packet(
        _config(m433_path)
    )

    assert payload["approval_decision"] == "blocked_m433_not_ready"
    assert payload["next_required_milestone"] != _READY_NEXT_MILESTONE
    assert (
        "source_m433_readiness_decision_not_ready:blocked_open_order_present"
        in payload["blockers"]
    )
    _assert_m434_offline_only(payload)


def test_m433_blockers_are_summarized_and_propagated(tmp_path: Path) -> None:
    m433_path = _write_jsonl(
        tmp_path / "m433.jsonl",
        _m433_review(blockers=["open_order_present", "spy_position_not_flat"]),
    )

    payload = build_etf_sma_m434_offline_paper_buy_submit_approval_packet(
        _config(m433_path)
    )

    assert payload["approval_decision"] == "blocked_m433_not_ready"
    assert "source_m433_blockers_present" in payload["blockers"]
    assert "source_m433_blocker:open_order_present" in payload["blockers"]
    assert "source_m433_blocker:spy_position_not_flat" in payload["blockers"]
    assert payload["submit_authorized"] is False
    assert payload["submitted"] is False
    assert payload["mutated"] is False


def test_m434_output_is_offline_only_even_when_source_is_incompatible(
    tmp_path: Path,
) -> None:
    source = _m433_review()
    source["broker_read_only"] = True
    source["network_access_attempted"] = True
    source["credential_access_attempted"] = True
    m433_path = _write_jsonl(tmp_path / "m433.jsonl", source)

    payload = build_etf_sma_m434_offline_paper_buy_submit_approval_packet(
        _config(m433_path)
    )

    assert payload["approval_decision"] == "blocked_m433_not_ready"
    assert "source_m433_broker_read_only_not_false" in payload["blockers"]
    assert "source_m433_network_access_attempted_not_false" in payload["blockers"]
    assert "source_m433_credential_access_attempted_not_false" in payload["blockers"]
    _assert_m434_offline_only(payload)


def test_m434_never_authorizes_or_records_submit_mutation(tmp_path: Path) -> None:
    m433_path = _write_jsonl(tmp_path / "m433.jsonl", _m433_review())
    payload = build_etf_sma_m434_offline_paper_buy_submit_approval_packet(
        _config(m433_path)
    )
    output_path = tmp_path / "m434.jsonl"

    result = write_etf_sma_m434_offline_paper_buy_submit_approval_packet_jsonl(
        payload,
        output_path,
    )
    records = _read_jsonl(output_path)

    assert result.record_count == 1
    assert result.paper_only is True
    assert result.operator_approval_required is True
    assert result.required_single_attempt_submit is True
    assert result.submit_authorized is False
    assert result.submitted is False
    assert result.mutated is False
    assert result.broker_action_performed is False
    assert records == [payload]
    assert render_etf_sma_m434_offline_paper_buy_submit_approval_packet_json(payload) == (
        render_etf_sma_m434_offline_paper_buy_submit_approval_packet_json(payload)
    )


def test_cli_writes_packet_before_runtime_config_loading(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    m433_path = _write_jsonl(tmp_path / "m433.jsonl", _m433_review())
    run_log = tmp_path / "m434_cli.jsonl"

    def forbidden_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("M434 offline command must not load runtime config")

    def forbidden_broker(*args: object, **kwargs: object) -> object:
        raise AssertionError("M434 offline command must not build a broker")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)

    assert cli_module.main(
        [
            _COMMAND,
            "--m433-review",
            str(m433_path),
            "--run-log",
            str(run_log),
            "--run-id",
            "unit_m434_cli",
            "--format",
            "json",
        ]
    ) == 0

    payload = json.loads(run_log.read_text(encoding="utf-8"))
    stdout = capsys.readouterr().out
    assert json.loads(stdout) == payload
    assert payload["run_id"] == "unit_m434_cli"
    assert payload["approval_decision"] == _READY_APPROVAL_DECISION
    _assert_m434_offline_only(payload)


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
    m433_review_path: Path,
) -> EtfSmaM434OfflinePaperBuySubmitApprovalPacketConfig:
    return EtfSmaM434OfflinePaperBuySubmitApprovalPacketConfig(
        run_id="unit_m434",
        m433_review_path=m433_review_path,
    )


def _m433_review(
    *,
    readiness_decision: str = _READY_M433_DECISION,
    blockers: list[str] | None = None,
) -> dict[str, object]:
    return {
        "approval_scope": "offline_operator_review_packet",
        "blockers": [] if blockers is None else blockers,
        "broker_action_performed": False,
        "broker_read_only": False,
        "command": "etf-sma-m433-offline-operator-review-packet",
        "credential_access_attempted": False,
        "live_authorized": False,
        "milestone": "M433",
        "mutated": False,
        "network_access_attempted": False,
        "next_required_milestone": _SOURCE_NEXT_MILESTONE,
        "operator_approval_required": True,
        "paper_lab_only": True,
        "profit_claim": "none",
        "readiness_decision": readiness_decision,
        "record_type": "etf_sma_m433_offline_operator_review_packet",
        "review_scope": "offline_operator_review_packet",
        "run_id": "m433_offline_operator_review_packet",
        "schema_version": "1",
        "submit_authorized": False,
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


def _assert_m434_offline_only(payload: dict[str, object]) -> None:
    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False
    assert payload["paper_only"] is True
    assert payload["operator_approval_required"] is True
    assert payload["required_single_attempt_submit"] is True
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
    return any(module == prefix or module.startswith(f"{prefix}.") for prefix in prefixes)


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
