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
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_daily_validated_cycle_summary import (
    EtfSmaDailyValidatedCycleSummaryConfig,
    build_etf_sma_daily_validated_cycle_summary,
    render_etf_sma_daily_validated_cycle_summary_json,
    write_etf_sma_daily_validated_cycle_summary_jsonl,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
MODULE_PATH = Path(
    "src/algotrader/execution/etf_sma_daily_validated_cycle_summary.py"
)
RUN_ID = "m443_daily_validated_cycle_summary"
VALIDATED_AT = "2026-06-08T21:00:00+00:00"
SOURCE_VALIDATED_AT = "2026-06-08T20:33:47+00:00"
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


def test_daily_wrapper_help_and_parser_registration() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "algotrader.cli",
            "etf-sma-daily-validated-cycle-summary",
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
    assert "etf-sma-daily-validated-cycle-summary" in result.stdout
    assert "--validation-jsonl" in result.stdout
    assert "--output-jsonl" in result.stdout
    assert "--validated-at" in result.stdout

    parser = _daily_wrapper_parser()
    options = {
        action.dest: action
        for action in parser._actions
        if getattr(action, "option_strings", ())
    }
    assert options["validation_jsonl"].default == (
        "runs/paper_lab/m442_unified_cycle_packet_validation.jsonl"
    )
    assert options["output_jsonl"].default == (
        "runs/paper_lab/m443_daily_validated_cycle_summary.jsonl"
    )
    assert options["validated_at"].required is True


def test_accepts_current_clean_m442_hold_noop_validation_packet(tmp_path) -> None:  # noqa: ANN001
    validation_path = _write_jsonl(tmp_path / "m442_validation.jsonl", _m442_record())
    output_path = tmp_path / "m443_daily_summary.jsonl"

    payload = build_etf_sma_daily_validated_cycle_summary(_config(validation_path))
    result = write_etf_sma_daily_validated_cycle_summary_jsonl(
        payload,
        output_path,
    )
    records = _read_jsonl(output_path)

    assert result.record_count == 1
    assert records == [payload]
    assert output_path.read_text(encoding="utf-8").count("\n") == 1
    assert payload["record_type"] == "etf_sma_daily_validated_cycle_summary"
    assert payload["command"] == "etf-sma-daily-validated-cycle-summary"
    assert payload["milestone"] == "M443 - Offline daily validated cycle wrapper"
    assert payload["run_id"] == RUN_ID
    assert payload["source_validation_path"] == str(validation_path)
    assert payload["source_validation_sha256"] == hashlib.sha256(
        validation_path.read_bytes()
    ).hexdigest()
    assert payload["source_validation_record_count"] == 1
    assert payload["validated_at"] == VALIDATED_AT
    assert payload["daily_wrapper_state"] == "accepted_observe_hold_noop"
    assert payload["validation_state"] == "accepted_current_cycle_hold_noop"
    assert payload["validation_blockers"] == []
    assert payload["symbol"] == "SPY"
    assert payload["sma50"] == "713.5118"
    assert payload["sma200"] == "681.5535044594288505"
    assert payload["posture"] == "risk_on"
    assert payload["cycle_decision"] == "hold/noop"
    assert payload["current_spy_position_qty"] == "0.033695775"
    assert payload["open_order_count"] == 0
    assert payload["unexpected_non_spy_position_present"] is False
    assert payload["source_as_of"] == SOURCE_VALIDATED_AT
    assert payload["recommended_operator_action"] == "observe_hold_noop"
    _assert_never_authorizes_or_mutates(payload)


def test_cli_daily_wrapper_dispatch_avoids_runtime_config_broker_and_network(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:  # noqa: ANN001
    for name in SCRUBBED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    def forbidden_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("daily wrapper must not load runtime config")

    def forbidden_broker(*args: object, **kwargs: object) -> object:
        raise AssertionError("daily wrapper must not build a broker")

    def forbidden_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("daily wrapper must not open sockets")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)
    monkeypatch.setattr(socket, "socket", forbidden_socket)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    validation_path = _write_jsonl(tmp_path / "m442_validation.jsonl", _m442_record())
    output_path = tmp_path / "m443_daily_summary.jsonl"

    exit_code = cli_module.main(
        (
            "etf-sma-daily-validated-cycle-summary",
            "--validation-jsonl",
            str(validation_path),
            "--output-jsonl",
            str(output_path),
            "--validated-at",
            VALIDATED_AT,
            "--format",
            "json",
        )
    )
    stdout = capsys.readouterr().out.strip()
    printed = json.loads(stdout)

    assert exit_code == 0
    assert printed["daily_wrapper_state"] == "accepted_observe_hold_noop"
    assert _read_jsonl(output_path) == [printed]
    _assert_never_authorizes_or_mutates(printed)


def test_rejects_missing_validation_file(tmp_path) -> None:  # noqa: ANN001
    payload = build_etf_sma_daily_validated_cycle_summary(
        _config(tmp_path / "missing_m442_validation.jsonl")
    )

    assert payload["daily_wrapper_state"] == "blocked_daily_validated_cycle_summary"
    assert payload["daily_wrapper_blockers"] == ["source_validation_missing"]
    assert payload["source_validation_found"] is False
    assert payload["source_validation_sha256"] == ""
    _assert_never_authorizes_or_mutates(payload)


def test_rejects_malformed_jsonl(tmp_path) -> None:  # noqa: ANN001
    validation_path = tmp_path / "malformed_m442_validation.jsonl"
    validation_path.write_text("{bad\n", encoding="utf-8")

    payload = build_etf_sma_daily_validated_cycle_summary(_config(validation_path))

    assert payload["daily_wrapper_state"] == "blocked_daily_validated_cycle_summary"
    assert payload["daily_wrapper_blockers"] == ["source_validation_invalid_jsonl"]
    assert payload["source_validation_parsed"] is False
    _assert_never_authorizes_or_mutates(payload)


def test_rejects_zero_records(tmp_path) -> None:  # noqa: ANN001
    validation_path = tmp_path / "empty_m442_validation.jsonl"
    validation_path.write_text("", encoding="utf-8")

    payload = build_etf_sma_daily_validated_cycle_summary(_config(validation_path))

    assert payload["daily_wrapper_state"] == "blocked_daily_validated_cycle_summary"
    assert payload["daily_wrapper_blockers"] == ["source_validation_zero_records"]
    assert payload["source_validation_record_count"] == 0
    _assert_never_authorizes_or_mutates(payload)


def test_rejects_more_than_one_record(tmp_path) -> None:  # noqa: ANN001
    validation_path = _write_jsonl(
        tmp_path / "multi_m442_validation.jsonl",
        _m442_record(),
        _m442_record(),
    )

    payload = build_etf_sma_daily_validated_cycle_summary(_config(validation_path))

    assert payload["daily_wrapper_state"] == "blocked_daily_validated_cycle_summary"
    assert payload["daily_wrapper_blockers"] == ["source_validation_multiple_records"]
    assert payload["source_validation_record_count"] == 2
    _assert_never_authorizes_or_mutates(payload)


def test_rejects_non_accepted_validation_state(tmp_path) -> None:  # noqa: ANN001
    payload = _summary_for_record(
        tmp_path,
        _m442_record(validation_state="accepted_current_cycle_observe_only"),
    )

    assert "validation_state_not_accepted_current_cycle_hold_noop" in (
        payload["daily_wrapper_blockers"]
    )
    _assert_blocked(payload)


def test_rejects_non_empty_validation_blockers(tmp_path) -> None:  # noqa: ANN001
    payload = _summary_for_record(
        tmp_path,
        _m442_record(validation_blockers=["source_blockers_present"]),
    )

    assert "validation_blockers_present" in payload["daily_wrapper_blockers"]
    _assert_blocked(payload)


@pytest.mark.parametrize(
    "field_name",
    (
        "paper_action_authorized",
        "submit_authorized",
        "paper_submit_authorized",
        "submitted",
        "mutated",
        "broker_action_performed",
        "live_authorized",
        "network_access_attempted",
        "credential_access_attempted",
    ),
)
def test_rejects_true_safety_drift_fields(
    field_name,
    tmp_path,
) -> None:  # noqa: ANN001
    payload = _summary_for_record(tmp_path, _m442_record(**{field_name: True}))

    assert f"{field_name}_not_false" in payload["daily_wrapper_blockers"]
    assert payload[field_name] is False
    _assert_blocked(payload)


def test_preserves_cycle_decision_from_m442(tmp_path) -> None:  # noqa: ANN001
    payload = _summary_for_record(
        tmp_path,
        _m442_record(cycle_decision="operator_review"),
    )

    assert payload["cycle_decision"] == "operator_review"
    assert "cycle_decision_not_hold_noop" in payload["daily_wrapper_blockers"]
    _assert_blocked(payload)


def test_preserves_recommended_operator_action_from_m442(tmp_path) -> None:  # noqa: ANN001
    payload = _summary_for_record(
        tmp_path,
        _m442_record(recommended_operator_action="operator_review_only"),
    )

    assert payload["recommended_operator_action"] == "operator_review_only"
    assert "recommended_operator_action_not_observe_hold_noop" in (
        payload["daily_wrapper_blockers"]
    )
    _assert_blocked(payload)


def test_requires_operator_supplied_validated_at(tmp_path) -> None:  # noqa: ANN001
    validation_path = _write_jsonl(tmp_path / "m442_validation.jsonl", _m442_record())

    with pytest.raises(ValidationError, match="validated_at is required"):
        EtfSmaDailyValidatedCycleSummaryConfig(
            run_id=RUN_ID,
            validation_jsonl_path=validation_path,
            validated_at="",
        )


def test_emits_exactly_one_jsonl_record(tmp_path) -> None:  # noqa: ANN001
    validation_path = _write_jsonl(tmp_path / "m442_validation.jsonl", _m442_record())
    output_path = tmp_path / "m443_daily_summary.jsonl"
    payload = build_etf_sma_daily_validated_cycle_summary(_config(validation_path))

    result = write_etf_sma_daily_validated_cycle_summary_jsonl(
        payload,
        output_path,
    )

    assert result.record_count == 1
    assert len(_read_jsonl(output_path)) == 1
    assert output_path.read_text(encoding="utf-8").endswith("\n")
    assert output_path.read_text(encoding="utf-8").count("\n") == 1


def test_daily_wrapper_module_imports_no_broker_sdk_credentials_network_or_mutation_calls() -> None:
    imports = _import_references()

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(FORBIDDEN_CALL_NAMES)


def test_daily_wrapper_json_is_deterministic(tmp_path) -> None:  # noqa: ANN001
    validation_path = _write_jsonl(tmp_path / "m442_validation.jsonl", _m442_record())

    first = build_etf_sma_daily_validated_cycle_summary(_config(validation_path))
    second = build_etf_sma_daily_validated_cycle_summary(_config(validation_path))

    assert first == second
    assert render_etf_sma_daily_validated_cycle_summary_json(first) == (
        render_etf_sma_daily_validated_cycle_summary_json(second)
    )


def _config(
    validation_path: Path,
    **overrides: object,
) -> EtfSmaDailyValidatedCycleSummaryConfig:
    values = {
        "run_id": RUN_ID,
        "validation_jsonl_path": validation_path,
        "validated_at": VALIDATED_AT,
    }
    values.update(overrides)
    return EtfSmaDailyValidatedCycleSummaryConfig(**values)


def _m442_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "command": "etf-sma-cycle-packet-validator",
        "credential_access_attempted": False,
        "current_spy_position_qty": "0.033695775",
        "cycle_decision": "hold/noop",
        "live_authorized": False,
        "max_age_hours": "24",
        "milestone": "M442 - Offline unified cycle packet validator",
        "mutated": False,
        "network_access_attempted": False,
        "open_order_count": 0,
        "paper_action_authorized": False,
        "paper_submit_authorized": False,
        "posture": "risk_on",
        "profit_claim": "none",
        "recommended_operator_action": "observe_hold_noop",
        "record_type": "etf_sma_cycle_packet_validation",
        "run_id": "m442_unified_cycle_packet_validation",
        "sma200": "681.5535044594288505",
        "sma50": "713.5118",
        "source_as_of": SOURCE_VALIDATED_AT,
        "source_packet_error": "",
        "source_packet_found": True,
        "source_packet_parsed": True,
        "source_packet_path": (
            "runs\\paper_lab\\m441_unified_etf_sma_cycle_readiness_packet.jsonl"
        ),
        "source_packet_record_count": 1,
        "source_packet_sha256": (
            "b80f1aa0debad7f22b9991fc67be345dfd46c54fc4e0c6ed2e6e783c1f809332"
        ),
        "submit_authorized": False,
        "submitted": False,
        "symbol": "SPY",
        "unexpected_non_spy_position_present": False,
        "usable_spy_bars": 8395,
        "validated_at": SOURCE_VALIDATED_AT,
        "validation_blockers": [],
        "validation_state": "accepted_current_cycle_hold_noop",
    }
    record.update(overrides)
    return record


def _summary_for_record(
    tmp_path: Path,
    record: dict[str, object],
) -> dict[str, object]:
    validation_path = _write_jsonl(tmp_path / "m442_validation.jsonl", record)
    return build_etf_sma_daily_validated_cycle_summary(_config(validation_path))


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
    assert payload["daily_wrapper_state"] == "blocked_daily_validated_cycle_summary"
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


def _daily_wrapper_parser():
    parser = cli_module.build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", {}) or {}
        if "etf-sma-daily-validated-cycle-summary" in choices:
            return choices["etf-sma-daily-validated-cycle-summary"]
    raise AssertionError("etf-sma-daily-validated-cycle-summary parser not found")


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
