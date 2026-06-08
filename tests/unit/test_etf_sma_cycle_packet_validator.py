from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import algotrader.cli as cli_module
import pytest
from algotrader.execution.etf_sma_cycle_packet_validator import (
    EtfSmaCyclePacketValidationConfig,
    build_etf_sma_cycle_packet_validation,
    render_etf_sma_cycle_packet_validation_json,
    write_etf_sma_cycle_packet_validation_jsonl,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
MODULE_PATH = Path("src/algotrader/execution/etf_sma_cycle_packet_validator.py")
RUN_ID = "m442_unified_cycle_packet_validation"
AS_OF = "2026-06-08T20:33:47+00:00"
STALE_VALIDATED_AT = "2026-06-10T20:33:48+00:00"
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
    "urllib",
)
FORBIDDEN_CALL_NAMES = {
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
    "submit_order_request",
    "urlopen",
}


def test_packet_validator_help_and_parser_registration() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "algotrader.cli",
            "etf-sma-cycle-packet-validator",
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
    assert "etf-sma-cycle-packet-validator" in result.stdout
    assert "--source-packet" in result.stdout
    assert "--input-packet" in result.stdout
    assert "--run-log" in result.stdout
    assert "--validated-at" in result.stdout
    assert "--max-age-hours" in result.stdout

    parser = _packet_validator_parser()
    options = {
        action.dest: action
        for action in parser._actions
        if getattr(action, "option_strings", ())
    }
    assert options["source_packet_path"].default == (
        "runs/paper_lab/m441_unified_etf_sma_cycle_readiness_packet.jsonl"
    )
    assert options["run_log"].default == (
        "runs/paper_lab/m442_unified_cycle_packet_validation.jsonl"
    )


def test_valid_m441_packet_produces_accepted_current_cycle_hold_noop(
    tmp_path,
) -> None:  # noqa: ANN001
    packet_path = _write_jsonl(tmp_path / "m441_packet.jsonl", _m441_record())
    run_log = tmp_path / "m442_validation.jsonl"

    payload = build_etf_sma_cycle_packet_validation(_config(packet_path))
    result = write_etf_sma_cycle_packet_validation_jsonl(payload, run_log)
    records = _read_jsonl(run_log)

    assert result.record_count == 1
    assert records == [payload]
    assert run_log.read_text(encoding="utf-8").count("\n") == 1
    assert payload["record_type"] == "etf_sma_cycle_packet_validation"
    assert payload["command"] == "etf-sma-cycle-packet-validator"
    assert payload["run_id"] == RUN_ID
    assert payload["source_packet_path"] == str(packet_path)
    assert payload["source_packet_sha256"] == hashlib.sha256(
        packet_path.read_bytes()
    ).hexdigest()
    assert payload["source_as_of"] == AS_OF
    assert payload["validated_at"] == AS_OF
    assert payload["symbol"] == "SPY"
    assert payload["usable_spy_bars"] == 8395
    assert payload["sma50"] == "713.5118"
    assert payload["sma200"] == "681.5535044594288505"
    assert payload["posture"] == "risk_on"
    assert payload["cycle_decision"] == "hold/noop"
    assert payload["current_spy_position_qty"] == "0.033695775"
    assert payload["open_order_count"] == 0
    assert payload["unexpected_non_spy_position_present"] is False
    assert payload["validation_state"] == "accepted_current_cycle_hold_noop"
    assert payload["validation_blockers"] == []
    assert payload["recommended_operator_action"] == "observe_hold_noop"
    _assert_never_authorizes_or_mutates(payload)


def test_cli_validator_dispatch_avoids_runtime_config_broker_and_network(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:  # noqa: ANN001
    for name in SCRUBBED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    def forbidden_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("packet validator must not load runtime config")

    def forbidden_broker(*args: object, **kwargs: object) -> object:
        raise AssertionError("packet validator must not build a broker")

    def forbidden_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("packet validator must not open sockets")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)
    monkeypatch.setattr(socket, "socket", forbidden_socket)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    packet_path = _write_jsonl(tmp_path / "m441_packet.jsonl", _m441_record())
    run_log = tmp_path / "m442_validation.jsonl"

    exit_code = cli_module.main(
        (
            "etf-sma-cycle-packet-validator",
            "--source-packet",
            str(packet_path),
            "--run-log",
            str(run_log),
            "--validated-at",
            AS_OF,
            "--format",
            "json",
        )
    )
    stdout = capsys.readouterr().out.strip()
    printed = json.loads(stdout)

    assert exit_code == 0
    assert printed["validation_state"] == "accepted_current_cycle_hold_noop"
    assert _read_jsonl(run_log) == [printed]
    _assert_never_authorizes_or_mutates(printed)


def test_missing_input_fails_closed_and_writes_one_record(tmp_path) -> None:  # noqa: ANN001
    packet_path = tmp_path / "missing_m441_packet.jsonl"
    run_log = tmp_path / "m442_validation.jsonl"

    payload = build_etf_sma_cycle_packet_validation(
        _config(packet_path, validated_at=AS_OF)
    )
    result = write_etf_sma_cycle_packet_validation_jsonl(payload, run_log)

    assert result.record_count == 1
    assert _read_jsonl(run_log) == [payload]
    assert payload["validation_state"] == "blocked_unified_cycle_packet_validation"
    assert payload["validation_blockers"] == ["source_packet_missing"]
    assert payload["source_packet_found"] is False
    assert payload["source_packet_sha256"] == ""
    assert payload["recommended_operator_action"] == "resolve_validation_blockers"
    _assert_never_authorizes_or_mutates(payload)


def test_multiple_records_fail_closed(tmp_path) -> None:  # noqa: ANN001
    packet_path = _write_jsonl(
        tmp_path / "multi_m441_packet.jsonl",
        _m441_record(),
        _m441_record(),
    )

    payload = build_etf_sma_cycle_packet_validation(_config(packet_path))

    assert payload["validation_state"] == "blocked_unified_cycle_packet_validation"
    assert payload["validation_blockers"] == ["source_packet_multiple_records"]
    assert payload["source_packet_record_count"] == 2
    _assert_never_authorizes_or_mutates(payload)


def test_zero_records_fail_closed(tmp_path) -> None:  # noqa: ANN001
    packet_path = tmp_path / "empty_m441_packet.jsonl"
    packet_path.write_text("", encoding="utf-8")

    payload = build_etf_sma_cycle_packet_validation(
        _config(packet_path, validated_at=AS_OF)
    )

    assert payload["validation_state"] == "blocked_unified_cycle_packet_validation"
    assert payload["validation_blockers"] == ["source_packet_zero_records"]
    assert payload["source_packet_record_count"] == 0
    _assert_never_authorizes_or_mutates(payload)


def test_missing_sma_fails_closed(tmp_path) -> None:  # noqa: ANN001
    record = _m441_record()
    record.pop("sma50")

    payload = _validation_for_record(tmp_path, record)

    assert "sma50_missing_or_nonnumeric" in payload["validation_blockers"]
    _assert_blocked(payload)


def test_usable_bars_below_200_fails_closed(tmp_path) -> None:  # noqa: ANN001
    payload = _validation_for_record(tmp_path, _m441_record(usable_spy_bars=199))

    assert "usable_spy_bars_missing_or_below_200" in payload["validation_blockers"]
    _assert_blocked(payload)


@pytest.mark.parametrize(
    ("field_name", "blocker"),
    (
        ("submitted", "submitted_not_false"),
        ("mutated", "mutated_not_false"),
        ("broker_action_performed", "broker_action_performed_not_false"),
        ("live_authorized", "live_authorized_not_false"),
    ),
)
def test_source_mutation_or_live_flags_true_fail_closed(
    field_name,
    blocker,
    tmp_path,
) -> None:  # noqa: ANN001
    payload = _validation_for_record(tmp_path, _m441_record(**{field_name: True}))

    assert blocker in payload["validation_blockers"]
    _assert_blocked(payload)


def test_profit_claim_other_than_none_fails_closed(tmp_path) -> None:  # noqa: ANN001
    payload = _validation_for_record(tmp_path, _m441_record(profit_claim="claimed"))

    assert "profit_claim_not_none" in payload["validation_blockers"]
    assert payload["profit_claim"] == "none"
    _assert_blocked(payload)


def test_unexpected_non_spy_position_fails_closed(tmp_path) -> None:  # noqa: ANN001
    payload = _validation_for_record(
        tmp_path,
        _m441_record(unexpected_non_spy_position_present=True),
    )

    assert "unexpected_non_spy_position_present" in payload["validation_blockers"]
    _assert_blocked(payload)


def test_open_order_count_greater_than_zero_fails_closed(tmp_path) -> None:  # noqa: ANN001
    payload = _validation_for_record(tmp_path, _m441_record(open_order_count=1))

    assert "open_order_count_missing_or_positive" in payload["validation_blockers"]
    _assert_blocked(payload)


def test_source_blockers_fail_closed(tmp_path) -> None:  # noqa: ANN001
    payload = _validation_for_record(
        tmp_path,
        _m441_record(blockers=["operator_review_required"]),
    )

    assert "source_blockers_present" in payload["validation_blockers"]
    _assert_blocked(payload)


def test_stale_as_of_fails_closed(tmp_path) -> None:  # noqa: ANN001
    packet_path = _write_jsonl(tmp_path / "m441_packet.jsonl", _m441_record())

    payload = build_etf_sma_cycle_packet_validation(
        _config(packet_path, validated_at=STALE_VALIDATED_AT, max_age_hours="24")
    )

    assert "source_as_of_stale" in payload["validation_blockers"]
    _assert_blocked(payload)


def test_future_source_as_of_fails_closed_to_avoid_lookahead(tmp_path) -> None:  # noqa: ANN001
    payload = _validation_for_record(
        tmp_path,
        _m441_record(as_of="2026-06-09T20:33:47+00:00"),
        validated_at=AS_OF,
    )

    assert "source_as_of_after_validated_at" in payload["validation_blockers"]
    _assert_blocked(payload)


def test_packet_validator_module_imports_no_broker_sdk_credentials_network_or_mutation_calls() -> None:
    imports = _import_references()

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(FORBIDDEN_CALL_NAMES)


def test_validation_json_is_deterministic(tmp_path) -> None:  # noqa: ANN001
    packet_path = _write_jsonl(tmp_path / "m441_packet.jsonl", _m441_record())

    first = build_etf_sma_cycle_packet_validation(_config(packet_path))
    second = build_etf_sma_cycle_packet_validation(_config(packet_path))

    assert first == second
    assert render_etf_sma_cycle_packet_validation_json(first) == (
        render_etf_sma_cycle_packet_validation_json(second)
    )


def _config(
    packet_path: Path,
    **overrides: object,
) -> EtfSmaCyclePacketValidationConfig:
    values = {
        "run_id": RUN_ID,
        "source_packet_path": packet_path,
        "validated_at": AS_OF,
        "max_age_hours": "24",
    }
    values.update(overrides)
    return EtfSmaCyclePacketValidationConfig(**values)


def _m441_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "as_of": AS_OF,
        "blockers": [],
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_mutation_allowed": False,
        "command": "etf-sma-cycle",
        "credential_access_attempted": False,
        "current_spy_position_qty": "0.033695775",
        "cycle_decision": "hold/noop",
        "live_authorized": False,
        "mutated": False,
        "network_access_attempted": False,
        "open_order_count": 0,
        "posture": "risk_on",
        "profit_claim": "none",
        "record_type": "etf_sma_cycle_unified_preview",
        "run_id": "m441_unified_etf_sma_cycle_readiness_packet",
        "sma200": "681.5535044594288505",
        "sma50": "713.5118",
        "submitted": False,
        "symbol": "SPY",
        "unexpected_non_spy_position_present": False,
        "usable_spy_bars": 8395,
    }
    record.update(overrides)
    return record


def _validation_for_record(
    tmp_path: Path,
    record: dict[str, object],
    **config_overrides: object,
) -> dict[str, object]:
    packet_path = _write_jsonl(tmp_path / "m441_packet.jsonl", record)
    return build_etf_sma_cycle_packet_validation(
        _config(packet_path, **config_overrides)
    )


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


def _assert_blocked(payload: dict[str, object]) -> None:
    assert payload["validation_state"] == "blocked_unified_cycle_packet_validation"
    assert payload["recommended_operator_action"] == "resolve_validation_blockers"
    _assert_never_authorizes_or_mutates(payload)


def _assert_never_authorizes_or_mutates(payload: dict[str, object]) -> None:
    for field_name in (
        "paper_action_authorized",
        "submit_authorized",
        "paper_submit_authorized",
        "submitted",
        "mutated",
        "broker_action_performed",
        "broker_actions_performed",
        "network_access_attempted",
        "credential_access_attempted",
        "live_authorized",
    ):
        assert payload[field_name] is False
    assert payload["profit_claim"] == "none"


def _packet_validator_parser():
    parser = cli_module.build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", {}) or {}
        if "etf-sma-cycle-packet-validator" in choices:
            return choices["etf-sma-cycle-packet-validator"]
    raise AssertionError("etf-sma-cycle-packet-validator parser not found")


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    for name in SCRUBBED_ENV_VARS:
        env.pop(name, None)
    env["PYTHONPATH"] = str(SRC_ROOT)
    return env


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
