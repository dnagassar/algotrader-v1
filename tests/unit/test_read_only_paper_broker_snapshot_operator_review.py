from __future__ import annotations

import ast
import json
from pathlib import Path
import socket

import pytest

import algotrader.cli as cli_module
from algotrader.execution.read_only_paper_broker_snapshot_operator_review import (
    READ_ONLY_PAPER_BROKER_SNAPSHOT_OPERATOR_REVIEW_COMMAND,
    ReadOnlyPaperBrokerSnapshotOperatorReviewConfig,
    build_read_only_paper_broker_snapshot_operator_review,
    render_read_only_paper_broker_snapshot_operator_review_json,
    write_read_only_paper_broker_snapshot_operator_review_jsonl,
)


MODULE_PATH = Path(
    "src/algotrader/execution/read_only_paper_broker_snapshot_operator_review.py"
)
GENERATED_AT = "2026-06-06T00:00:00+00:00"
RUN_ID = "unit_m405_m404_read_only_broker_snapshot_operator_review"
SENSITIVE_ACCOUNT_ID = "raw-account-id-must-not-escape"
SENSITIVE_BALANCE = "999999.99-raw-balance"
SENSITIVE_BROKER_ORDER_ID = "raw-broker-order-id-must-not-escape"
SENSITIVE_CLIENT_ORDER_ID = "raw-client-order-id-must-not-escape"
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
    "algotrader.execution.alpaca_adapter",
    "algotrader.execution.alpaca_broker",
    "algotrader.execution.alpaca_client",
    "algotrader.execution.alpaca_sdk_client",
    "algotrader.execution.broker_base",
    "algotrader.execution.fake_broker",
    "algotrader.execution.local_broker",
    "algotrader.runtime",
    "http",
    "http.client",
    "httpx",
    "requests",
    "socket",
    "urllib",
)
FORBIDDEN_CALL_NAMES = {
    "_build_paper_broker",
    "cancel_order",
    "close_all_positions",
    "close_position",
    "connect",
    "create_connection",
    "create_order",
    "download",
    "get_account",
    "get_orders",
    "get_positions",
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


def test_clean_m404_snapshot_produces_clean_operator_review_packet(tmp_path) -> None:  # noqa: ANN001
    source_log = _write_source_snapshot(tmp_path, _clean_source_record())
    run_log = tmp_path / "m405.jsonl"

    payload = build_read_only_paper_broker_snapshot_operator_review(
        _config(source_log, run_log)
    )
    result = write_read_only_paper_broker_snapshot_operator_review_jsonl(
        payload,
        run_log,
    )

    assert result.record_count == 1
    assert _read_jsonl(run_log) == [payload]
    assert run_log.read_text(encoding="utf-8").count("\n") == 1
    assert payload["record_type"] == (
        "paper_lab_read_only_broker_snapshot_operator_review"
    )
    assert payload["schema_version"] == 1
    assert payload["command"] == READ_ONLY_PAPER_BROKER_SNAPSHOT_OPERATOR_REVIEW_COMMAND
    assert payload["run_id"] == RUN_ID
    assert payload["source_snapshot_log"] == str(source_log)
    assert payload["source_run_id"] == (
        "m404_credentialed_read_only_paper_broker_snapshot_reconciliation"
    )
    assert payload["source_reconciliation_state"] == "ready_for_operator_review"
    assert payload["review_state"] == "operator_review_complete"
    assert payload["operator_review_result"] == "clean_flat_no_open_orders"
    assert payload["next_action"] == "no_submit_operator_review_complete"
    assert payload["blockers"] == []
    assert payload["position_observation_summary"] == {
        "positions_observed": True,
        "position_count": 0,
        "position_symbols": [],
        "spy_position_present": False,
    }
    assert payload["open_order_observation_summary"] == {
        "open_orders_observed": True,
        "open_order_count": 0,
        "open_order_symbols": [],
        "open_spy_order_count": 0,
    }
    assert payload["recent_order_context_summary"] == {
        "recent_orders_observed": True,
        "recent_order_count": 2,
        "recent_order_symbols": ["BTC/USD", "SPY"],
        "recent_spy_order_count": 1,
        "recent_orders_are_context_only": True,
    }
    assert payload["operator_decision"] == {
        "paper_submit_approved": False,
        "paper_submit_requires_separate_milestone": True,
        "broker_observed_state_clean": True,
    }
    _assert_m405_safety(payload)


@pytest.mark.parametrize(
    ("source_factory", "expected_blocker"),
    (
        (lambda tmp_path: tmp_path / "missing_m404.jsonl", "source_snapshot_log_missing"),
        (lambda tmp_path: _invalid_json_source(tmp_path), "source_snapshot_log_invalid_json"),
        (lambda tmp_path: _invalid_identity_source(tmp_path), "source_record_type_unexpected"),
    ),
)
def test_source_record_missing_or_invalid_writes_blocked_packet(
    tmp_path,
    source_factory,
    expected_blocker: str,
) -> None:  # noqa: ANN001
    source_log = source_factory(tmp_path)
    run_log = tmp_path / "m405_blocked.jsonl"
    payload = build_read_only_paper_broker_snapshot_operator_review(
        _config(source_log, run_log)
    )
    write_read_only_paper_broker_snapshot_operator_review_jsonl(payload, run_log)

    assert _read_jsonl(run_log) == [payload]
    assert payload["review_state"] == "blocked_operator_review"
    assert expected_blocker in payload["blockers"]
    assert payload["operator_decision"]["broker_observed_state_clean"] is False
    _assert_m405_safety(payload)


@pytest.mark.parametrize(
    ("mutator", "expected_blocker"),
    (
        (lambda record: record.__setitem__("submitted", True), "source_submitted_true"),
        (lambda record: record.__setitem__("mutated", True), "source_mutated_true"),
        (
            lambda record: record.__setitem__("live_authorized", True),
            "source_live_authorized_true",
        ),
        (
            lambda record: record.__setitem__("broker_mutation_authorized", True),
            "source_broker_mutation_authorized_true",
        ),
        (
            lambda record: record.__setitem__(
                "reconciliation_state",
                "blocked_open_order_present",
            ),
            "source_reconciliation_state_not_ready_for_operator_review",
        ),
        (
            lambda record: record.__setitem__("blockers", ["open_order_present"]),
            "source_blockers_present",
        ),
        (
            lambda record: record.__setitem__("positions_observed", False),
            "positions_not_observed",
        ),
        (
            lambda record: record.__setitem__("open_orders_observed", False),
            "open_orders_not_observed",
        ),
        (
            lambda record: record.__setitem__("spy_position_present", True),
            "spy_position_present",
        ),
        (
            lambda record: record.__setitem__("position_count", 1),
            "position_count_nonzero",
        ),
        (
            lambda record: record.__setitem__("open_order_count", 1),
            "open_order_count_nonzero",
        ),
        (
            lambda record: record.__setitem__("open_spy_order_count", 1),
            "open_spy_order_count_nonzero",
        ),
        (
            lambda record: record.pop("read_only_broker_observation"),
            "source_read_only_broker_observation_missing_or_false",
        ),
    ),
)
def test_blocked_review_states_from_m404_source_invariants(
    tmp_path,
    mutator,
    expected_blocker: str,
) -> None:  # noqa: ANN001
    source = _clean_source_record()
    mutator(source)
    source_log = _write_source_snapshot(tmp_path, source)
    run_log = tmp_path / f"m405_{expected_blocker}.jsonl"

    payload = build_read_only_paper_broker_snapshot_operator_review(
        _config(source_log, run_log)
    )
    write_read_only_paper_broker_snapshot_operator_review_jsonl(payload, run_log)

    assert _read_jsonl(run_log) == [payload]
    assert payload["review_state"] == "blocked_operator_review"
    assert payload["operator_review_result"] == f"blocked_{payload['blockers'][0]}"
    assert payload["next_action"] == "resolve_blockers_before_any_paper_submit_review"
    assert expected_blocker in payload["blockers"]
    assert payload["operator_decision"]["paper_submit_approved"] is False
    assert payload["operator_decision"]["broker_observed_state_clean"] is False
    _assert_m405_safety(payload)


def test_recent_historical_orders_are_context_only_unless_open(tmp_path) -> None:  # noqa: ANN001
    source = _clean_source_record()
    source["recent_orders"] = (
        {"symbol": "BTC/USD", "status": "filled", "id": SENSITIVE_BROKER_ORDER_ID},
        {"symbol": "SPY", "status": "canceled", "id": "filled-spy-order-id"},
    )
    source_log = _write_source_snapshot(tmp_path, source)

    payload = build_read_only_paper_broker_snapshot_operator_review(
        _config(source_log, tmp_path / "m405_recent_context.jsonl")
    )

    assert payload["review_state"] == "operator_review_complete"
    assert payload["recent_order_context_summary"]["recent_orders_are_context_only"] is True
    assert payload["blockers"] == []


def test_recent_open_order_context_blocks_even_when_summary_counts_are_clean(
    tmp_path,
) -> None:  # noqa: ANN001
    source = _clean_source_record()
    source["recent_orders"] = ({"symbol": "SPY", "status": "accepted"},)
    source_log = _write_source_snapshot(tmp_path, source)

    payload = build_read_only_paper_broker_snapshot_operator_review(
        _config(source_log, tmp_path / "m405_recent_open.jsonl")
    )

    assert payload["review_state"] == "blocked_operator_review"
    assert "recent_order_context_contains_open_status" in payload["blockers"]
    assert "recent_spy_order_context_contains_open_status" in payload["blockers"]
    _assert_m405_safety(payload)


def test_output_is_deterministic_dict_and_json(tmp_path) -> None:  # noqa: ANN001
    source_log = _write_source_snapshot(tmp_path, _clean_source_record())
    config = _config(source_log, tmp_path / "m405_deterministic.jsonl")

    first = build_read_only_paper_broker_snapshot_operator_review(config)
    second = build_read_only_paper_broker_snapshot_operator_review(config)
    first_json = render_read_only_paper_broker_snapshot_operator_review_json(first)
    second_json = render_read_only_paper_broker_snapshot_operator_review_json(second)

    assert first == second
    assert first_json == second_json
    assert json.loads(first_json) == first


def test_packet_excludes_raw_account_balances_and_broker_order_ids(tmp_path) -> None:  # noqa: ANN001
    source = _clean_source_record()
    source["account"] = {
        "id": SENSITIVE_ACCOUNT_ID,
        "cash": SENSITIVE_BALANCE,
        "buying_power": SENSITIVE_BALANCE,
    }
    source["cash"] = SENSITIVE_BALANCE
    source["buying_power"] = SENSITIVE_BALANCE
    source["recent_orders"] = (
        {
            "id": SENSITIVE_BROKER_ORDER_ID,
            "client_order_id": SENSITIVE_CLIENT_ORDER_ID,
            "symbol": "SPY",
            "status": "filled",
            "filled_avg_price": SENSITIVE_BALANCE,
        },
    )
    source_log = _write_source_snapshot(tmp_path, source)
    run_log = tmp_path / "m405_redacted.jsonl"

    payload = build_read_only_paper_broker_snapshot_operator_review(
        _config(source_log, run_log)
    )
    write_read_only_paper_broker_snapshot_operator_review_jsonl(payload, run_log)

    rendered = (
        render_read_only_paper_broker_snapshot_operator_review_json(payload)
        + run_log.read_text(encoding="utf-8")
    )
    for raw_value in (
        SENSITIVE_ACCOUNT_ID,
        SENSITIVE_BALANCE,
        SENSITIVE_BROKER_ORDER_ID,
        SENSITIVE_CLIENT_ORDER_ID,
    ):
        assert raw_value not in rendered
    assert payload["review_state"] == "operator_review_complete"
    assert payload["recent_order_context_summary"]["recent_order_symbols"] == [
        "BTC/USD",
        "SPY",
    ]


def test_cli_operator_review_smoke_avoids_runtime_config_broker_and_network(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:  # noqa: ANN001
    for name in SCRUBBED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    def forbidden_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("M405 operator review must not load runtime config")

    def forbidden_broker(*args: object, **kwargs: object) -> object:
        raise AssertionError("M405 operator review must not build a broker")

    def forbidden_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("M405 operator review must not open sockets")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)
    monkeypatch.setattr(socket, "socket", forbidden_socket)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    source_log = _write_source_snapshot(tmp_path, _clean_source_record())
    run_log = tmp_path / "m405_cli.jsonl"

    exit_code = cli_module.main(
        (
            READ_ONLY_PAPER_BROKER_SNAPSHOT_OPERATOR_REVIEW_COMMAND,
            "--source-snapshot-log",
            str(source_log),
            "--run-id",
            RUN_ID,
            "--run-log",
            str(run_log),
            "--format",
            "json",
        )
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert _read_jsonl(run_log) == [payload]
    assert payload["review_state"] == "operator_review_complete"
    assert payload["generated_at"] == GENERATED_AT
    _assert_m405_safety(payload)


def test_operator_review_parser_registration() -> None:
    parser = _operator_review_parser()
    options = {
        action.dest: action
        for action in parser._actions
        if getattr(action, "option_strings", ())
    }

    assert options["source_snapshot_log"].required is True
    assert options["run_id"].required is True
    assert options["run_log"].required is True
    assert options["generated_at"].required is False


def test_operator_review_module_imports_no_broker_sdk_credentials_network_or_mutation_calls() -> None:
    imports = _import_references(MODULE_PATH)

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names(MODULE_PATH).isdisjoint(FORBIDDEN_CALL_NAMES)


def _config(
    source_snapshot_log: Path,
    run_log: Path,
    **overrides: object,
) -> ReadOnlyPaperBrokerSnapshotOperatorReviewConfig:
    values = {
        "run_id": RUN_ID,
        "source_snapshot_log": source_snapshot_log,
        "run_log": run_log,
        "generated_at": None,
    }
    values.update(overrides)
    return ReadOnlyPaperBrokerSnapshotOperatorReviewConfig(**values)


def _clean_source_record() -> dict[str, object]:
    return {
        "milestone": "M404 - Read-only paper broker snapshot reconciliation",
        "record_type": "read_only_paper_broker_snapshot_reconciliation",
        "command": "paper-lab-read-only-broker-snapshot-reconciliation",
        "run_id": "m404_credentialed_read_only_paper_broker_snapshot_reconciliation",
        "generated_at": GENERATED_AT,
        "reconciliation_state": "ready_for_operator_review",
        "blockers": [],
        "positions_observed": True,
        "position_count": 0,
        "position_symbols": [],
        "spy_position_present": False,
        "open_orders_observed": True,
        "open_order_count": 0,
        "open_order_symbols": [],
        "open_spy_order_count": 0,
        "recent_orders_observed": True,
        "recent_order_count": 2,
        "recent_order_symbols": ["BTC/USD", "SPY"],
        "recent_spy_order_count": 1,
        "submitted": False,
        "mutated": False,
        "submit_authorized": False,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "broker_mutation_allowed": False,
        "paper_execution_authorized": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "live_authorized": False,
        "read_only_broker_observation": True,
        "network_access_attempted": True,
        "credential_access_attempted": True,
        "profit_claim": "none",
        "broker_action_flags": {
            "submit": False,
            "cancel": False,
            "replace": False,
            "close": False,
            "liquidate": False,
            "mutation": False,
        },
    }


def _invalid_json_source(tmp_path: Path) -> Path:
    path = tmp_path / "invalid_m404.jsonl"
    path.write_text("{not-json}\n", encoding="utf-8")
    return path


def _invalid_identity_source(tmp_path: Path) -> Path:
    source = _clean_source_record()
    source["record_type"] = "unexpected_record"
    return _write_source_snapshot(tmp_path, source)


def _write_source_snapshot(
    tmp_path: Path,
    *records: dict[str, object],
) -> Path:
    path = tmp_path / "m404_snapshot.jsonl"
    _write_jsonl(path, *records)
    return path


def _write_jsonl(path: Path, *records: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _assert_m405_safety(payload: dict[str, object]) -> None:
    assert payload["paper_execution_authorized"] is False
    assert payload["paper_submit_authorized"] is False
    assert payload["submit_authorized"] is False
    assert payload["broker_mutation_authorized"] is False
    assert payload["broker_mutation_allowed"] is False
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["broker_actions_performed"] is False
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is False
    assert payload["live_authorized"] is False
    assert payload["not_live_authorized"] is True
    assert payload["profit_claim"] == "none"
    assert payload["broker_action_flags"] == {
        "submit": False,
        "cancel": False,
        "replace": False,
        "close": False,
        "liquidate": False,
        "mutation": False,
    }
    assert payload["safety_attestations"] == {
        "submitted": False,
        "mutated": False,
        "submit_authorized": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "credential_access_attempted": False,
        "network_access_attempted": False,
        "offline_review_only": True,
    }
    assert payload["operator_decision"]["paper_submit_approved"] is False
    assert payload["operator_decision"]["paper_submit_requires_separate_milestone"] is True


def _operator_review_parser():
    parser = cli_module.build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", {}) or {}
        if READ_ONLY_PAPER_BROKER_SNAPSHOT_OPERATOR_REVIEW_COMMAND in choices:
            return choices[READ_ONLY_PAPER_BROKER_SNAPSHOT_OPERATOR_REVIEW_COMMAND]
    raise AssertionError("M405 operator-review parser not found")


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
