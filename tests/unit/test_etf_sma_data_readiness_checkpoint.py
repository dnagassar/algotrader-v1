from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import algotrader.cli as cli_module
from algotrader.execution.etf_sma_data_readiness_checkpoint import (
    ETF_SMA_DATA_READINESS_CHECKPOINT_LABELS,
    EtfSmaDataReadinessCheckpointConfig,
    build_etf_sma_data_readiness_checkpoint,
    render_etf_sma_data_readiness_checkpoint_json,
    write_etf_sma_data_readiness_checkpoint_jsonl,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
MODULE_PATH = Path("src/algotrader/execution/etf_sma_data_readiness_checkpoint.py")
GENERATED_AT = "2026-06-05T00:00:00+00:00"
M394_RUN_ID = "m394_etf_sma_cycle_unified_offline_preview"
M395_RUN_ID = "m395_etf_sma_cycle_operator_brief"
SCRUBBED_ENV_VARS = (
    "APP_PROFILE",
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
    "ALPACA_PAPER_BASE_URL",
)
FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "alpaca_trade_api",
    "httpx",
    "os",
    "requests",
    "socket",
    "subprocess",
    "urllib",
)
FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_all_positions",
    "close_position",
    "connect",
    "create_connection",
    "create_order",
    "getenv",
    "liquidate",
    "load_config",
    "replace_order",
    "request",
    "socket",
    "socket.socket",
    "submit_order",
    "submit_order_request",
    "urlopen",
}


def test_etf_sma_data_readiness_help_and_parser_registration() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "algotrader.cli",
            "etf-sma-data-readiness",
            "--help",
        ],
        cwd=PROJECT_ROOT,
        env=_subprocess_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "etf-sma-data-readiness" in result.stdout
    assert "--run-id" in result.stdout
    assert "--run-log" in result.stdout
    assert "--cycle-log" in result.stdout
    assert "--brief-log" in result.stdout
    assert "--generated-at" in result.stdout

    parser = _etf_sma_data_readiness_parser()
    options = {
        action.dest: action
        for action in parser._actions
        if getattr(action, "option_strings", ())
    }
    assert options["run_id"].required is True
    assert options["run_log"].required is True
    assert options["cycle_log"].required is True
    assert options["brief_log"].required is False
    assert options["generated_at"].required is True


def test_insufficient_history_with_count_fields_produces_readiness_checkpoint(
    tmp_path,
) -> None:  # noqa: ANN001
    cycle_log = _write_jsonl(
        tmp_path / "m394_cycle.jsonl",
        _m394_cycle_record(
            data_readiness={
                "required_usable_bars": 200,
                "observed_usable_bars": 150,
                "missing_usable_bars": 50,
                "sma_short_window": 50,
                "sma_long_window": 200,
                "readiness_state": "insufficient_history",
                "readiness_reason": "sma_insufficient_history",
                "missing_evidence": [],
                "source": "offline_etf_sma_cycle_evidence",
            },
        ),
    )
    brief_log = _write_jsonl(tmp_path / "m395_brief.jsonl", _m395_brief_record())
    run_log = tmp_path / "m396_data_readiness.jsonl"

    payload = build_etf_sma_data_readiness_checkpoint(
        _config(cycle_log, brief_log=brief_log)
    )
    result = write_etf_sma_data_readiness_checkpoint_jsonl(payload, run_log)
    records = _read_jsonl(run_log)

    assert result.record_count == 1
    assert records == [payload]
    assert run_log.read_text(encoding="utf-8").count("\n") == 1
    assert payload["record_type"] == "etf_sma_data_readiness_checkpoint"
    assert payload["command"] == "etf-sma-data-readiness"
    assert payload["run_id"] == "unit_m396_data_readiness"
    assert payload["generated_at"] == GENERATED_AT
    assert payload["source_cycle_log"] == str(cycle_log)
    assert payload["source_brief_log"] == str(brief_log)
    assert payload["cycle_run_id"] == M394_RUN_ID
    assert payload["brief_run_id"] == M395_RUN_ID
    assert payload["labels"] == list(ETF_SMA_DATA_READINESS_CHECKPOINT_LABELS)
    assert payload["cycle_decision"] == "insufficient_history"
    assert payload["cycle_decision_reason"] == "sma_insufficient_history"
    assert payload["data_readiness_state"] == "insufficient_history"
    assert payload["required_usable_bars"] == 200
    assert payload["required_usable_bars_source"] == (
        "cycle_artifact.data_readiness.required_usable_bars"
    )
    assert payload["observed_usable_bars"] == 150
    assert payload["observed_usable_bars_source"] == (
        "cycle_artifact.data_readiness.observed_usable_bars"
    )
    assert payload["missing_usable_bars"] == 50
    assert payload["missing_evidence"] == []
    assert "sma_insufficient_history" in payload["blockers"]
    assert "missing_usable_bars" in payload["blockers"]
    assert payload["recommended_next_action"] == (
        "import_deterministic_local_daily_bars_until_sma200_has_200_usable_asof_bars"
    )
    _assert_safety_booleans_false(payload)


def test_missing_count_fields_are_reported_as_unknown_from_cycle_artifact(
    tmp_path,
) -> None:  # noqa: ANN001
    cycle_log = _write_jsonl(tmp_path / "m394_cycle.jsonl", _m394_cycle_record())
    brief_log = _write_jsonl(tmp_path / "m395_brief.jsonl", _m395_brief_record())

    payload = build_etf_sma_data_readiness_checkpoint(
        _config(cycle_log, brief_log=brief_log)
    )

    assert payload["cycle_decision"] == "insufficient_history"
    assert payload["cycle_decision_reason"] == "sma_insufficient_history"
    assert payload["data_readiness_state"] == "unknown_from_cycle_artifact"
    assert payload["required_usable_bars"] == 200
    assert payload["required_usable_bars_source"] == "configured_sma200_default"
    assert payload["observed_usable_bars"] is None
    assert payload["missing_usable_bars"] is None
    assert (
        "cycle_artifact.data_readiness.observed_usable_bars"
        in payload["missing_evidence"]
    )
    assert "cycle_artifact.market_data.usable_bar_count" in payload["missing_evidence"]
    assert "missing_observed_usable_bars" in payload["blockers"]
    assert payload["recommended_next_action"] == (
        "expose_or_import_deterministic_local_daily_bars_before_next_etf_sma_cycle"
    )
    _assert_safety_booleans_false(payload)


def test_non_insufficient_cycle_is_classified_without_broker_action(
    tmp_path,
) -> None:  # noqa: ANN001
    record = _m394_cycle_record(
        data_readiness={
            "required_usable_bars": 200,
            "observed_usable_bars": 220,
            "missing_usable_bars": 0,
            "sma_short_window": 50,
            "sma_long_window": 200,
            "readiness_state": "ready_from_cycle_artifact",
            "readiness_reason": "sma_usable_bars_ready",
            "missing_evidence": [],
            "source": "offline_etf_sma_cycle_evidence",
        },
    )
    record.update(
        {
            "cycle_decision": "risk_on/no_submit_authorized",
            "cycle_decision_reason": "sma_risk_on",
            "cycle_next_allowed_action": "offline_operator_review_only",
            "next_allowed_action": "offline_operator_review_only",
        }
    )
    cycle_log = _write_jsonl(tmp_path / "risk_on_cycle.jsonl", record)

    payload = build_etf_sma_data_readiness_checkpoint(_config(cycle_log))

    assert payload["cycle_decision"] == "risk_on/no_submit_authorized"
    assert payload["data_readiness_state"] == "ready_from_cycle_artifact"
    assert payload["required_usable_bars"] == 200
    assert payload["observed_usable_bars"] == 220
    assert payload["missing_usable_bars"] == 0
    assert payload["recommended_next_action"] == (
        "offline_operator_review_only_no_broker_action"
    )
    assert payload["broker_action_flags"] == {
        "submit": False,
        "cancel": False,
        "replace": False,
        "close": False,
        "liquidate": False,
        "mutation": False,
    }
    _assert_safety_booleans_false(payload)


def test_missing_cycle_artifact_fails_closed_with_clear_error(tmp_path) -> None:  # noqa: ANN001
    payload = build_etf_sma_data_readiness_checkpoint(
        _config(tmp_path / "missing_m394_cycle.jsonl")
    )

    assert payload["data_readiness_state"] == "blocked_missing_or_invalid_cycle_artifact"
    assert payload["cycle_record_found"] is False
    assert payload["cycle_record_parsed"] is False
    assert payload["source_artifacts"]["cycle_log"]["error"] == "path_not_found"
    assert "missing_or_invalid_cycle_artifact" in payload["blockers"]
    assert payload["recommended_next_action"] == (
        "rebuild_or_validate_cycle_artifact_before_data_readiness_review"
    )
    _assert_safety_booleans_false(payload)


def test_malformed_cycle_artifact_fails_closed_with_clear_error(tmp_path) -> None:  # noqa: ANN001
    malformed_log = tmp_path / "malformed_m394_cycle.jsonl"
    malformed_log.write_text("{not-json}\n", encoding="utf-8")

    payload = build_etf_sma_data_readiness_checkpoint(_config(malformed_log))

    assert payload["data_readiness_state"] == "blocked_missing_or_invalid_cycle_artifact"
    assert payload["cycle_record_found"] is True
    assert payload["cycle_record_parsed"] is False
    assert payload["source_artifacts"]["cycle_log"]["error"] == "invalid_jsonl_line_1"
    assert "missing_or_invalid_cycle_artifact" in payload["blockers"]
    _assert_safety_booleans_false(payload)


def test_cli_data_readiness_dispatch_avoids_runtime_config_broker_and_network(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:  # noqa: ANN001
    for name in SCRUBBED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    def forbidden_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("data readiness must not load runtime config")

    def forbidden_broker(*args: object, **kwargs: object) -> object:
        raise AssertionError("data readiness must not build a broker")

    def forbidden_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("data readiness must not open sockets")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)
    monkeypatch.setattr(socket, "socket", forbidden_socket)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    cycle_log = _write_jsonl(tmp_path / "m394_cycle.jsonl", _m394_cycle_record())
    brief_log = _write_jsonl(tmp_path / "m395_brief.jsonl", _m395_brief_record())
    run_log = tmp_path / "m396_data_readiness.jsonl"

    exit_code = cli_module.main(
        (
            "etf-sma-data-readiness",
            "--symbol",
            "SPY",
            "--run-id",
            "unit_m396_data_readiness",
            "--run-log",
            str(run_log),
            "--cycle-log",
            str(cycle_log),
            "--brief-log",
            str(brief_log),
            "--generated-at",
            GENERATED_AT,
            "--format",
            "json",
        )
    )
    captured = capsys.readouterr()
    records = _read_jsonl(run_log)
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert records == [payload]
    assert payload["record_type"] == "etf_sma_data_readiness_checkpoint"
    assert payload["data_readiness_state"] == "unknown_from_cycle_artifact"
    _assert_safety_booleans_false(payload)


def test_same_input_and_generated_at_produce_deterministic_output(tmp_path) -> None:  # noqa: ANN001
    cycle_log = _write_jsonl(tmp_path / "m394_cycle.jsonl", _m394_cycle_record())
    brief_log = _write_jsonl(tmp_path / "m395_brief.jsonl", _m395_brief_record())

    first = build_etf_sma_data_readiness_checkpoint(
        _config(cycle_log, brief_log=brief_log)
    )
    second = build_etf_sma_data_readiness_checkpoint(
        _config(cycle_log, brief_log=brief_log)
    )

    assert first == second
    assert render_etf_sma_data_readiness_checkpoint_json(first) == (
        render_etf_sma_data_readiness_checkpoint_json(second)
    )


def test_data_readiness_module_imports_no_broker_sdk_credentials_network_or_mutation_calls() -> None:
    imports = _import_references(MODULE_PATH)

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names(MODULE_PATH).isdisjoint(FORBIDDEN_CALL_NAMES)


def test_research_and_signal_layers_do_not_import_data_readiness_module() -> None:
    for package in (Path("src/algotrader/research"), Path("src/algotrader/signals")):
        for path in package.rglob("*.py"):
            assert (
                "algotrader.execution.etf_sma_data_readiness_checkpoint"
                not in _import_references(path)
            )


def _config(
    cycle_log: Path,
    **overrides: object,
) -> EtfSmaDataReadinessCheckpointConfig:
    values = {
        "run_id": "unit_m396_data_readiness",
        "symbol": "SPY",
        "generated_at": GENERATED_AT,
        "cycle_log": cycle_log,
    }
    values.update(overrides)
    return EtfSmaDataReadinessCheckpointConfig(**values)


def _m394_cycle_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "record_type": "etf_sma_cycle_unified_preview",
        "command": "etf-sma-cycle",
        "run_id": M394_RUN_ID,
        "generated_at": GENERATED_AT,
        "as_of": GENERATED_AT,
        "symbol": "SPY",
        "labels": [
            "paper_lab_only",
            "signal_evaluation_only",
            "not_live_authorized",
            "profit_claim=none",
        ],
        "cycle_decision": "insufficient_history",
        "cycle_decision_reason": "sma_insufficient_history",
        "cycle_next_allowed_action": "offline_research_or_operator_review_only",
        "next_allowed_action": "offline_research_or_operator_review_only",
        "blockers": [],
        "m376_terminal": True,
        "m376_status": "filled",
        "m376_observed_status": "filled",
        "m376_terminal_state": "terminal",
        "m376_terminal_reason": "status_filled",
        "m376_terminal_state_conflict": False,
        "m376_nonterminal": False,
        "m376_order_nonterminal": False,
        "open_order_count": 0,
        "open_order_present": False,
        "open_spy_order_present": False,
        "spy_position_qty": "",
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_mutation_allowed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "not_live_authorized": True,
    }
    record.update(overrides)
    return record


def _m395_brief_record() -> dict[str, object]:
    return {
        "record_type": "etf_sma_cycle_operator_brief",
        "command": "etf-sma-cycle-brief",
        "run_id": M395_RUN_ID,
        "generated_at": GENERATED_AT,
        "cycle_run_id": M394_RUN_ID,
        "cycle_generated_at": GENERATED_AT,
        "symbol": "SPY",
        "cycle_decision": "insufficient_history",
        "cycle_decision_reason": "sma_insufficient_history",
        "cycle_next_allowed_action": "offline_research_or_operator_review_only",
        "operator_brief_status": "review_only",
        "recommended_next_action": "offline_research_or_operator_review_only",
        "blockers": [],
        "m376_terminal": True,
        "m376_status": "filled",
        "m376_terminal_state": "terminal",
        "open_order_count": 0,
        "open_order_present": False,
        "open_spy_order_present": False,
        "spy_position_qty": "",
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_mutation_allowed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "not_live_authorized": True,
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


def _assert_safety_booleans_false(payload: dict[str, object]) -> None:
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["broker_actions_performed"] is False
    assert payload["broker_mutation_allowed"] is False
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is False
    assert payload["live_authorized"] is False
    assert payload["not_live_authorized"] is True
    assert payload["broker_action_flags"] == {
        "submit": False,
        "cancel": False,
        "replace": False,
        "close": False,
        "liquidate": False,
        "mutation": False,
    }


def _etf_sma_data_readiness_parser():
    parser = cli_module.build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", {}) or {}
        if "etf-sma-data-readiness" in choices:
            return choices["etf-sma-data-readiness"]
    raise AssertionError("etf-sma-data-readiness parser not found")


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    for name in SCRUBBED_ENV_VARS:
        env.pop(name, None)
    env["PYTHONPATH"] = str(SRC_ROOT)
    return env


def _import_references(path: Path) -> set[str]:
    imports: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            prefix = "." * node.level
            imports.add(f"{prefix}{node.module}")
    return imports


def _call_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }


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
