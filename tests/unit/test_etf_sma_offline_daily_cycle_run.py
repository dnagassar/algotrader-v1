from __future__ import annotations

import ast
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import socket

import algotrader.cli as cli_module
import pytest
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_offline_daily_cycle_run import (
    EtfSmaOfflineDailyCycleRunConfig,
    build_etf_sma_offline_daily_cycle_run_manifest,
    render_etf_sma_offline_daily_cycle_run_json,
    run_etf_sma_offline_daily_cycle_run,
    write_etf_sma_offline_daily_cycle_run_jsonl,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = Path("src/algotrader/execution/etf_sma_offline_daily_cycle_run.py")
RUN_ID = "m444_unit_offline_daily_cycle_run"
VALIDATED_AT = "2026-06-08T20:33:47+00:00"
QUANTITY = "0.033695775"
CLIENT_ORDER_ID = "paper-order-m435_spy_etf_sma_tiny_buy_submit"
BROKER_ORDER_ID = "4553f69a-748b-4ce4-a7bb-a9bac1ade9fb"
MISSING = object()
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


def test_accepts_current_clean_m441_to_m442_to_m443_hold_noop_chain(
    tmp_path,
) -> None:  # noqa: ANN001
    inputs = _write_clean_inputs(tmp_path)
    config = _config(
        tmp_path,
        daily_bars_csv=inputs["daily_bars_csv"],
        order_reconciliation_log=inputs["order_reconciliation_log"],
    )

    payload = run_etf_sma_offline_daily_cycle_run(config)
    records = _read_jsonl(config.manifest_output_jsonl)

    assert records == [payload]
    assert payload["record_type"] == "etf_sma_offline_daily_cycle_run_manifest"
    assert payload["command"] == "etf-sma-offline-daily-cycle-run"
    assert payload["milestone"] == "M444 - Offline daily cycle chain runner"
    assert payload["run_id"] == RUN_ID
    assert payload["validated_at"] == VALIDATED_AT
    assert payload["daily_chain_state"] == "accepted_observe_hold_noop"
    assert payload["readiness_record_count"] == 1
    assert payload["validation_record_count"] == 1
    assert payload["summary_record_count"] == 1
    assert payload["symbol"] == "SPY"
    assert payload["usable_spy_bars"] == 200
    assert payload["sma50"] == "274.5"
    assert payload["sma200"] == "199.5"
    assert payload["posture"] == "risk_on"
    assert payload["readiness_cycle_decision"] == "hold/noop"
    assert payload["validation_cycle_decision"] == "hold/noop"
    assert payload["summary_cycle_decision"] == "hold/noop"
    assert payload["validation_state"] == "accepted_current_cycle_hold_noop"
    assert payload["daily_wrapper_state"] == "accepted_observe_hold_noop"
    assert payload["recommended_operator_action"] == "observe_hold_noop"
    assert payload["profit_claim"] == "none"
    assert payload["chain_blockers"] == []
    _assert_never_authorizes_or_mutates(payload)


def test_emits_exactly_one_m444_manifest_record(tmp_path) -> None:  # noqa: ANN001
    inputs = _write_clean_inputs(tmp_path)
    config = _config(
        tmp_path,
        daily_bars_csv=inputs["daily_bars_csv"],
        order_reconciliation_log=inputs["order_reconciliation_log"],
    )
    payload = run_etf_sma_offline_daily_cycle_run(config)
    result = write_etf_sma_offline_daily_cycle_run_jsonl(
        payload,
        config.manifest_output_jsonl,
    )

    assert result.record_count == 1
    assert len(_read_jsonl(config.manifest_output_jsonl)) == 1
    assert Path(config.manifest_output_jsonl).read_text(encoding="utf-8").count("\n") == 1
    assert Path(config.manifest_output_jsonl).read_text(encoding="utf-8").endswith("\n")


def test_parser_requires_operator_clock_and_explicit_output_paths() -> None:
    parser = _offline_daily_cycle_run_parser()
    options = {
        action.dest: action
        for action in parser._actions
        if getattr(action, "option_strings", ())
    }

    assert options["validated_at"].required is True
    assert options["daily_bars_csv"].required is True
    assert options["readiness_output_jsonl"].required is True
    assert options["validation_output_jsonl"].required is True
    assert options["summary_output_jsonl"].required is True
    assert options["manifest_output_jsonl"].required is True
    assert options["run_id"].default == "m444_offline_daily_cycle_run"
    assert options["order_reconciliation_log"].default == (
        "runs/paper_lab/m439_m436_spy_buy_fresh_read_only_reconciliation.jsonl"
    )


@pytest.mark.parametrize(
    ("field_name", "error_text"),
    (
        ("validated_at", "validated_at is required"),
        ("daily_bars_csv", "daily_bars_csv is required"),
        ("readiness_output_jsonl", "readiness_output_jsonl is required"),
        ("validation_output_jsonl", "validation_output_jsonl is required"),
        ("summary_output_jsonl", "summary_output_jsonl is required"),
        ("manifest_output_jsonl", "manifest_output_jsonl is required"),
    ),
)
def test_config_requires_operator_clock_and_explicit_paths(
    field_name,
    error_text,
    tmp_path,
) -> None:  # noqa: ANN001
    values = _config_values(tmp_path)
    values[field_name] = ""

    with pytest.raises(ValidationError, match=error_text):
        EtfSmaOfflineDailyCycleRunConfig(**values)


def test_cli_dispatch_avoids_runtime_config_broker_and_network(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:  # noqa: ANN001
    for name in SCRUBBED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    def forbidden_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("M444 runner must not load runtime config")

    def forbidden_broker(*args: object, **kwargs: object) -> object:
        raise AssertionError("M444 runner must not build a broker")

    def forbidden_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("M444 runner must not open sockets")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)
    monkeypatch.setattr(socket, "socket", forbidden_socket)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    inputs = _write_clean_inputs(tmp_path)
    readiness_path = tmp_path / "m441.jsonl"
    validation_path = tmp_path / "m442.jsonl"
    summary_path = tmp_path / "m443.jsonl"
    manifest_path = tmp_path / "m444.jsonl"

    exit_code = cli_module.main(
        (
            "etf-sma-offline-daily-cycle-run",
            "--run-id",
            RUN_ID,
            "--validated-at",
            VALIDATED_AT,
            "--daily-bars-csv",
            str(inputs["daily_bars_csv"]),
            "--order-reconciliation-log",
            str(inputs["order_reconciliation_log"]),
            "--readiness-output-jsonl",
            str(readiness_path),
            "--validation-output-jsonl",
            str(validation_path),
            "--summary-output-jsonl",
            str(summary_path),
            "--manifest-output-jsonl",
            str(manifest_path),
            "--format",
            "json",
        )
    )
    printed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert printed["daily_chain_state"] == "accepted_observe_hold_noop"
    assert _read_jsonl(manifest_path) == [printed]
    _assert_never_authorizes_or_mutates(printed)


@pytest.mark.parametrize(
    ("label", "expected_blocker"),
    (
        ("readiness", "readiness_output_missing"),
        ("validation", "validation_output_missing"),
        ("summary", "summary_output_missing"),
    ),
)
def test_fails_closed_if_child_artifact_is_missing(
    label,
    expected_blocker,
    tmp_path,
) -> None:  # noqa: ANN001
    payload = _manifest_with_child_override(tmp_path, label, MISSING)

    assert payload["daily_chain_state"] == "blocked_offline_daily_cycle_run"
    assert expected_blocker in payload["chain_blockers"]
    _assert_never_authorizes_or_mutates(payload)


@pytest.mark.parametrize(
    ("label", "expected_blocker"),
    (
        ("readiness", "readiness_output_zero_records"),
        ("validation", "validation_output_zero_records"),
        ("summary", "summary_output_zero_records"),
    ),
)
def test_fails_closed_if_child_artifact_has_zero_records(
    label,
    expected_blocker,
    tmp_path,
) -> None:  # noqa: ANN001
    payload = _manifest_with_child_override(tmp_path, label, ())

    assert expected_blocker in payload["chain_blockers"]
    _assert_never_authorizes_or_mutates(payload)


@pytest.mark.parametrize(
    ("label", "expected_blocker"),
    (
        ("readiness", "readiness_output_multiple_records"),
        ("validation", "validation_output_multiple_records"),
        ("summary", "summary_output_multiple_records"),
    ),
)
def test_fails_closed_if_child_artifact_has_more_than_one_record(
    label,
    expected_blocker,
    tmp_path,
) -> None:  # noqa: ANN001
    record = _record_for_label(label)
    payload = _manifest_with_child_override(tmp_path, label, (record, record))

    assert expected_blocker in payload["chain_blockers"]
    _assert_never_authorizes_or_mutates(payload)


def test_fails_closed_if_m441_cycle_decision_does_not_match_m442(
    tmp_path,
) -> None:  # noqa: ANN001
    payload = _manifest_for_records(
        tmp_path,
        readiness=_m441_record(cycle_decision="sell_preview"),
    )

    assert "readiness_validation_cycle_decision_mismatch" in payload["chain_blockers"]
    _assert_never_authorizes_or_mutates(payload)


def test_fails_closed_if_m442_cycle_decision_does_not_match_m443(
    tmp_path,
) -> None:  # noqa: ANN001
    payload = _manifest_for_records(
        tmp_path,
        validation=_m442_record(cycle_decision="operator_review"),
    )

    assert "validation_summary_cycle_decision_mismatch" in payload["chain_blockers"]
    _assert_never_authorizes_or_mutates(payload)


def test_fails_closed_if_validation_state_is_not_accepted_hold_noop(
    tmp_path,
) -> None:  # noqa: ANN001
    payload = _manifest_for_records(
        tmp_path,
        validation=_m442_record(validation_state="accepted_current_cycle_observe_only"),
    )

    assert "validation_state_not_accepted_current_cycle_hold_noop" in (
        payload["chain_blockers"]
    )
    _assert_never_authorizes_or_mutates(payload)


def test_fails_closed_if_daily_wrapper_state_is_not_accepted_observe_hold_noop(
    tmp_path,
) -> None:  # noqa: ANN001
    payload = _manifest_for_records(
        tmp_path,
        summary=_m443_record(daily_wrapper_state="blocked_daily_validated_cycle_summary"),
    )

    assert "daily_wrapper_state_not_accepted_observe_hold_noop" in (
        payload["chain_blockers"]
    )
    _assert_never_authorizes_or_mutates(payload)


def test_fails_closed_if_recommended_operator_action_is_not_observe_hold_noop(
    tmp_path,
) -> None:  # noqa: ANN001
    payload = _manifest_for_records(
        tmp_path,
        summary=_m443_record(recommended_operator_action="operator_review_only"),
    )

    assert "recommended_operator_action_not_observe_hold_noop" in (
        payload["chain_blockers"]
    )
    _assert_never_authorizes_or_mutates(payload)


def test_fails_closed_if_validation_blockers_are_non_empty(
    tmp_path,
) -> None:  # noqa: ANN001
    payload = _manifest_for_records(
        tmp_path,
        validation=_m442_record(validation_blockers=["source_blockers_present"]),
    )

    assert "validation_validation_blockers_present" in payload["chain_blockers"]
    _assert_never_authorizes_or_mutates(payload)


def test_fails_closed_if_child_chain_blockers_are_non_empty(
    tmp_path,
) -> None:  # noqa: ANN001
    payload = _manifest_for_records(
        tmp_path,
        summary=_m443_record(chain_blockers=["manual_review_required"]),
    )

    assert "summary_chain_blockers_present" in payload["chain_blockers"]
    _assert_never_authorizes_or_mutates(payload)


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
def test_fails_closed_if_any_required_safety_flag_is_true(
    field_name,
    tmp_path,
) -> None:  # noqa: ANN001
    payload = _manifest_for_records(
        tmp_path,
        validation=_m442_record(**{field_name: True}),
    )

    assert f"validation_{field_name}_true" in payload["chain_blockers"]
    _assert_never_authorizes_or_mutates(payload)


def test_records_child_artifact_sha256_values(tmp_path) -> None:  # noqa: ANN001
    payload, paths = _manifest_for_records_with_paths(tmp_path)

    assert payload["readiness_output_sha256"] == _sha256(paths["readiness"])
    assert payload["validation_output_sha256"] == _sha256(paths["validation"])
    assert payload["summary_output_sha256"] == _sha256(paths["summary"])
    assert payload["daily_chain_state"] == "accepted_observe_hold_noop"


def test_manifest_json_is_deterministic(tmp_path) -> None:  # noqa: ANN001
    first = _manifest_for_records(tmp_path)
    second = build_etf_sma_offline_daily_cycle_run_manifest(_config(tmp_path))

    assert first == second
    assert render_etf_sma_offline_daily_cycle_run_json(first) == (
        render_etf_sma_offline_daily_cycle_run_json(second)
    )


def test_runner_module_imports_no_broker_sdk_credentials_network_or_mutation_calls() -> None:
    imports = _import_references(MODULE_PATH)

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names(MODULE_PATH).isdisjoint(FORBIDDEN_CALL_NAMES)


def _config(
    tmp_path: Path,
    **overrides: object,
) -> EtfSmaOfflineDailyCycleRunConfig:
    return EtfSmaOfflineDailyCycleRunConfig(**_config_values(tmp_path, **overrides))


def _config_values(tmp_path: Path, **overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "run_id": RUN_ID,
        "validated_at": VALIDATED_AT,
        "daily_bars_csv": tmp_path / "spy_daily_bars.csv",
        "order_reconciliation_log": tmp_path / "reconciliation.jsonl",
        "readiness_output_jsonl": tmp_path / "m441_readiness.jsonl",
        "validation_output_jsonl": tmp_path / "m442_validation.jsonl",
        "summary_output_jsonl": tmp_path / "m443_summary.jsonl",
        "manifest_output_jsonl": tmp_path / "m444_manifest.jsonl",
    }
    values.update(overrides)
    return values


def _write_clean_inputs(tmp_path: Path) -> dict[str, Path]:
    daily_bars_csv = _write_daily_bars_csv(
        tmp_path / "spy_daily_bars.csv",
        _daily_rows_with_close_adjusted_trend(200),
    )
    order_reconciliation_log = _write_jsonl(
        tmp_path / "reconciliation.jsonl",
        _terminal_reconciliation_record_with_position(),
    )
    return {
        "daily_bars_csv": daily_bars_csv,
        "order_reconciliation_log": order_reconciliation_log,
    }


def _manifest_with_child_override(
    tmp_path: Path,
    label: str,
    value: object,
) -> dict[str, object]:
    records: dict[str, object] = {
        "readiness": _m441_record(),
        "validation": _m442_record(),
        "summary": _m443_record(),
    }
    records[label] = value
    return _manifest_for_records(
        tmp_path,
        readiness=records["readiness"],
        validation=records["validation"],
        summary=records["summary"],
    )


def _manifest_for_records(
    tmp_path: Path,
    *,
    readiness: object | None = None,
    validation: object | None = None,
    summary: object | None = None,
) -> dict[str, object]:
    payload, _paths = _manifest_for_records_with_paths(
        tmp_path,
        readiness=readiness,
        validation=validation,
        summary=summary,
    )
    return payload


def _manifest_for_records_with_paths(
    tmp_path: Path,
    *,
    readiness: object | None = None,
    validation: object | None = None,
    summary: object | None = None,
) -> tuple[dict[str, object], dict[str, Path]]:
    readiness_value = _m441_record() if readiness is None else readiness
    validation_value = _m442_record() if validation is None else validation
    summary_value = _m443_record() if summary is None else summary
    paths = {
        "readiness": tmp_path / "m441_readiness.jsonl",
        "validation": tmp_path / "m442_validation.jsonl",
        "summary": tmp_path / "m443_summary.jsonl",
    }
    _write_child(paths["readiness"], readiness_value)
    _write_child(paths["validation"], validation_value)
    _write_child(paths["summary"], summary_value)
    payload = build_etf_sma_offline_daily_cycle_run_manifest(_config(tmp_path))
    return payload, paths


def _write_child(path: Path, value: object) -> None:
    if value is MISSING:
        return
    if isinstance(value, tuple):
        _write_jsonl(path, *value)
        return
    if isinstance(value, list):
        _write_jsonl(path, *value)
        return
    _write_jsonl(path, value)


def _record_for_label(label: str) -> dict[str, object]:
    if label == "readiness":
        return _m441_record()
    if label == "validation":
        return _m442_record()
    if label == "summary":
        return _m443_record()
    raise AssertionError(f"unknown child label {label}")


def _m441_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "as_of": VALIDATED_AT,
        "blockers": [],
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_mutation_allowed": False,
        "command": "etf-sma-cycle",
        "credential_access_attempted": False,
        "current_spy_position_qty": QUANTITY,
        "cycle_decision": "hold/noop",
        "daily_bars_csv": "runs/operator_input/spy_daily_tiingo_adjusted_canonical_20260607.csv",
        "live_authorized": False,
        "mutated": False,
        "network_access_attempted": False,
        "open_order_count": 0,
        "posture": "risk_on",
        "profit_claim": "none",
        "record_type": "etf_sma_cycle_unified_preview",
        "run_id": "m441_unified_etf_sma_cycle_readiness_packet",
        "sma200": "199.5",
        "sma50": "274.5",
        "submitted": False,
        "symbol": "SPY",
        "unexpected_non_spy_position_present": False,
        "usable_spy_bars": 200,
    }
    record.update(overrides)
    return record


def _m442_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "command": "etf-sma-cycle-packet-validator",
        "credential_access_attempted": False,
        "current_spy_position_qty": QUANTITY,
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
        "sma200": "199.5",
        "sma50": "274.5",
        "source_as_of": VALIDATED_AT,
        "source_packet_error": "",
        "source_packet_found": True,
        "source_packet_parsed": True,
        "source_packet_path": (
            "runs\\paper_lab\\m441_unified_etf_sma_cycle_readiness_packet.jsonl"
        ),
        "source_packet_record_count": 1,
        "source_packet_sha256": "readiness-sha",
        "submit_authorized": False,
        "submitted": False,
        "symbol": "SPY",
        "unexpected_non_spy_position_present": False,
        "usable_spy_bars": 200,
        "validated_at": VALIDATED_AT,
        "validation_blockers": [],
        "validation_state": "accepted_current_cycle_hold_noop",
    }
    record.update(overrides)
    return record


def _m443_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "command": "etf-sma-daily-validated-cycle-summary",
        "credential_access_attempted": False,
        "current_spy_position_qty": QUANTITY,
        "cycle_decision": "hold/noop",
        "daily_wrapper_blockers": [],
        "daily_wrapper_state": "accepted_observe_hold_noop",
        "live_authorized": False,
        "milestone": "M443 - Offline daily validated cycle wrapper",
        "mutated": False,
        "network_access_attempted": False,
        "open_order_count": 0,
        "paper_action_authorized": False,
        "paper_submit_authorized": False,
        "posture": "risk_on",
        "profit_claim": "none",
        "recommended_operator_action": "observe_hold_noop",
        "record_type": "etf_sma_daily_validated_cycle_summary",
        "run_id": "m443_daily_validated_cycle_summary",
        "sma200": "199.5",
        "sma50": "274.5",
        "source_as_of": VALIDATED_AT,
        "source_validation_error": "",
        "source_validation_found": True,
        "source_validation_parsed": True,
        "source_validation_record_count": 1,
        "source_validation_sha256": "validation-sha",
        "submit_authorized": False,
        "submitted": False,
        "symbol": "SPY",
        "unexpected_non_spy_position_present": False,
        "validated_at": VALIDATED_AT,
        "validation_blockers": [],
        "validation_state": "accepted_current_cycle_hold_noop",
    }
    record.update(overrides)
    return record


def _terminal_reconciliation_record_with_position() -> dict[str, object]:
    return {
        "run_id": "m439_m436_spy_buy_fresh_read_only_reconciliation",
        "symbol": "SPY",
        "client_order_id": CLIENT_ORDER_ID,
        "broker_order_id": BROKER_ORDER_ID,
        "expected_side": "buy",
        "expected_qty": "",
        "observed_status": "filled",
        "observed_symbol": "SPY",
        "observed_side": "buy",
        "observed_qty": "",
        "observed_filled_qty": QUANTITY,
        "observed_remaining_qty": "0E-9",
        "exact_order_found": True,
        "exact_order_source": "all",
        "terminal_state": "terminal",
        "terminal_reason": "status_filled",
        "reconciliation_decision": "m376_terminal_filled",
        "next_spy_submit_blocked": False,
        "reason": "status_filled",
        "spy_position_qty": QUANTITY,
        "open_order_count": 0,
        "spy_open_order_count": 0,
        "open_order_symbols": [],
        "open_order_client_order_ids": [],
        "open_order_broker_order_ids": [],
        "open_order_statuses": [],
        "open_order_sides": [],
        "open_order_quantities": [],
        "open_order_filled_quantities": [],
        "non_spy_positions": [],
        "blockers": [],
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "account_observation_available": True,
        "positions_observation_available": True,
        "orders_observation_available": True,
    }


def _write_daily_bars_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = (
        "symbol",
        "date",
        "open",
        "high",
        "low",
        "close",
        "adjusted_close",
        "volume",
    )
    lines = [",".join(columns)]
    lines.extend(",".join(row[column] for column in columns) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _daily_rows_with_close_adjusted_trend(count: int) -> list[dict[str, str]]:
    start = date(2025, 1, 1)
    return [
        _daily_row_with_close_adjusted(
            "SPY",
            start + timedelta(days=index),
            raw_close=1000 - index,
            adjusted_close=100 + index,
        )
        for index in range(count)
    ]


def _daily_row_with_close_adjusted(
    symbol: str,
    day: date,
    *,
    raw_close: int,
    adjusted_close: int,
) -> dict[str, str]:
    return {
        "symbol": symbol,
        "date": day.isoformat(),
        "open": str(raw_close),
        "high": str(raw_close),
        "low": str(raw_close),
        "close": str(raw_close),
        "adjusted_close": str(adjusted_close),
        "volume": "1000",
    }


def _write_jsonl(path: Path, *records: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record, sort_keys=True) for record in records]
    if lines:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        path.write_text("", encoding="utf-8")
    return path


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _offline_daily_cycle_run_parser():
    parser = cli_module.build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", {}) or {}
        if "etf-sma-offline-daily-cycle-run" in choices:
            return choices["etf-sma-offline-daily-cycle-run"]
    raise AssertionError("etf-sma-offline-daily-cycle-run parser not found")


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
