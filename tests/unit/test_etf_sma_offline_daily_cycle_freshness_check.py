from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import socket

import algotrader.cli as cli_module
import pytest
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_offline_daily_cycle_freshness_check import (
    EtfSmaOfflineDailyCycleFreshnessCheckConfig,
    build_etf_sma_offline_daily_cycle_freshness_check,
    render_etf_sma_offline_daily_cycle_freshness_check_json,
    run_etf_sma_offline_daily_cycle_freshness_check,
    write_etf_sma_offline_daily_cycle_freshness_check_jsonl,
)


MODULE_PATH = Path(
    "src/algotrader/execution/etf_sma_offline_daily_cycle_freshness_check.py"
)
RUN_ID = "m445_unit_offline_daily_cycle_freshness_check"
EXPECTED_DATE = "2026-06-07"
MISSING = object()
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


def test_accepts_current_clean_m444_and_equal_latest_local_bar_date(
    tmp_path,
) -> None:  # noqa: ANN001
    payload, paths = _freshness_for_record_with_paths(tmp_path)

    assert payload["record_type"] == "etf_sma_offline_daily_cycle_freshness_check"
    assert payload["command"] == "etf-sma-offline-daily-cycle-freshness-check"
    assert payload["milestone"] == "M445"
    assert payload["run_id"] == RUN_ID
    assert payload["freshness_state"] == "accepted_current_local_bars"
    assert payload["expected_latest_bar_date"] == EXPECTED_DATE
    assert payload["latest_local_bar_date"] == EXPECTED_DATE
    assert payload["source_m444_path"] == str(paths["m444"])
    assert payload["source_m444_sha256"] == _sha256(paths["m444"])
    assert payload["source_daily_bars_csv_path"] == str(paths["daily_bars_csv"])
    assert payload["source_daily_bars_csv_sha256"] == _sha256(
        paths["daily_bars_csv"]
    )
    assert payload["daily_chain_state"] == "accepted_observe_hold_noop"
    assert payload["readiness_cycle_decision"] == "hold/noop"
    assert payload["validation_state"] == "accepted_current_cycle_hold_noop"
    assert payload["daily_wrapper_state"] == "accepted_observe_hold_noop"
    assert payload["recommended_operator_action"] == "observe_hold_noop"
    assert payload["freshness_blockers"] == []
    assert payload["freshness_warnings"] == []
    _assert_never_authorizes_or_mutates(payload)


def test_emits_exactly_one_m445_freshness_record(tmp_path) -> None:  # noqa: ANN001
    payload, paths = _freshness_for_record_with_paths(tmp_path)

    result = write_etf_sma_offline_daily_cycle_freshness_check_jsonl(
        payload,
        paths["output"],
    )

    assert result.record_count == 1
    assert len(_read_jsonl(paths["output"])) == 1
    assert paths["output"].read_text(encoding="utf-8").count("\n") == 1
    assert paths["output"].read_text(encoding="utf-8").endswith("\n")


def test_accepts_local_bars_ahead_of_expected_with_warning(
    tmp_path,
) -> None:  # noqa: ANN001
    payload = _freshness_for_record(
        tmp_path,
        csv_dates=("2026-06-06", "2026-06-08"),
    )

    assert payload["freshness_state"] == "accepted_local_bars_ahead_of_expected"
    assert payload["latest_local_bar_date"] == "2026-06-08"
    assert payload["freshness_blockers"] == []
    assert payload["freshness_warnings"] == ["latest_local_bar_date_after_expected"]
    _assert_never_authorizes_or_mutates(payload)


def test_blocks_stale_local_bars_before_expected_date(tmp_path) -> None:  # noqa: ANN001
    payload = _freshness_for_record(
        tmp_path,
        csv_dates=("2026-06-05", "2026-06-06"),
    )

    assert payload["freshness_state"] == "blocked_stale_local_bars"
    assert payload["latest_local_bar_date"] == "2026-06-06"
    assert "latest_local_bar_date_before_expected" in payload["freshness_blockers"]
    assert payload["freshness_warnings"] == []
    _assert_never_authorizes_or_mutates(payload)


def test_fails_closed_if_m444_manifest_is_missing(tmp_path) -> None:  # noqa: ANN001
    payload = _freshness_for_record(tmp_path, m444_record=MISSING)

    assert payload["freshness_state"] == "blocked_m444_manifest"
    assert "source_m444_missing" in payload["freshness_blockers"]
    _assert_never_authorizes_or_mutates(payload)


def test_fails_closed_if_m444_manifest_is_malformed(tmp_path) -> None:  # noqa: ANN001
    payload = _freshness_for_m444_text(tmp_path, "{not-json}\n")

    assert payload["freshness_state"] == "blocked_m444_manifest"
    assert "source_m444_malformed" in payload["freshness_blockers"]
    _assert_never_authorizes_or_mutates(payload)


def test_fails_closed_if_m444_manifest_has_zero_records(tmp_path) -> None:  # noqa: ANN001
    payload = _freshness_for_m444_records(tmp_path)

    assert payload["freshness_state"] == "blocked_m444_manifest"
    assert "source_m444_zero_records" in payload["freshness_blockers"]
    _assert_never_authorizes_or_mutates(payload)


def test_fails_closed_if_m444_manifest_has_multiple_records(
    tmp_path,
) -> None:  # noqa: ANN001
    payload = _freshness_for_m444_records(tmp_path, _m444_record(), _m444_record())

    assert payload["freshness_state"] == "blocked_m444_manifest"
    assert "source_m444_multiple_records" in payload["freshness_blockers"]
    _assert_never_authorizes_or_mutates(payload)


def test_fails_closed_if_m444_chain_blockers_are_non_empty(
    tmp_path,
) -> None:  # noqa: ANN001
    payload = _freshness_for_record(
        tmp_path,
        m444_record=_m444_record(chain_blockers=["manual_review_required"]),
    )

    assert payload["freshness_state"] == "blocked_m444_manifest"
    assert "source_m444_chain_blockers_present" in payload["freshness_blockers"]
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
    ),
)
def test_fails_closed_if_m444_unsafe_authorization_or_mutation_flag_drifts(
    field_name,
    tmp_path,
) -> None:  # noqa: ANN001
    payload = _freshness_for_record(
        tmp_path,
        m444_record=_m444_record(**{field_name: True}),
    )

    assert payload["freshness_state"] == "blocked_m444_manifest"
    assert f"source_m444_{field_name}_not_false" in payload["freshness_blockers"]
    _assert_never_authorizes_or_mutates(payload)


@pytest.mark.parametrize(
    "field_name",
    (
        "network_access_attempted",
        "credential_access_attempted",
    ),
)
def test_fails_closed_if_m444_network_or_credential_flag_drifts(
    field_name,
    tmp_path,
) -> None:  # noqa: ANN001
    payload = _freshness_for_record(
        tmp_path,
        m444_record=_m444_record(**{field_name: True}),
    )

    assert payload["freshness_state"] == "blocked_m444_manifest"
    assert f"source_m444_{field_name}_not_false" in payload["freshness_blockers"]
    _assert_never_authorizes_or_mutates(payload)


def test_fails_closed_if_m444_live_authorized_drifts(tmp_path) -> None:  # noqa: ANN001
    payload = _freshness_for_record(
        tmp_path,
        m444_record=_m444_record(live_authorized=True),
    )

    assert payload["freshness_state"] == "blocked_m444_manifest"
    assert "source_m444_live_authorized_not_false" in payload["freshness_blockers"]
    _assert_never_authorizes_or_mutates(payload)


def test_fails_closed_if_m444_profit_claim_drifts(tmp_path) -> None:  # noqa: ANN001
    payload = _freshness_for_record(
        tmp_path,
        m444_record=_m444_record(profit_claim="positive_return_expected"),
    )

    assert payload["freshness_state"] == "blocked_m444_manifest"
    assert "source_m444_profit_claim_not_none" in payload["freshness_blockers"]
    _assert_never_authorizes_or_mutates(payload)


@pytest.mark.parametrize(
    ("field_name", "bad_value", "expected_blocker"),
    (
        (
            "daily_chain_state",
            "blocked_offline_daily_cycle_run",
            "source_m444_daily_chain_state_not_accepted_observe_hold_noop",
        ),
        (
            "readiness_cycle_decision",
            "operator_review",
            "source_m444_readiness_cycle_decision_not_hold_noop",
        ),
        (
            "validation_state",
            "accepted_current_cycle_observe_only",
            "source_m444_validation_state_not_accepted_current_cycle_hold_noop",
        ),
        (
            "daily_wrapper_state",
            "blocked_daily_validated_cycle_summary",
            "source_m444_daily_wrapper_state_not_accepted_observe_hold_noop",
        ),
        (
            "recommended_operator_action",
            "operator_review_only",
            "source_m444_recommended_operator_action_not_observe_hold_noop",
        ),
        (
            "validation_cycle_decision",
            "operator_review",
            "source_m444_validation_cycle_decision_not_hold_noop",
        ),
    ),
)
def test_fails_closed_if_m444_expected_cycle_state_drifts(
    field_name,
    bad_value,
    expected_blocker,
    tmp_path,
) -> None:  # noqa: ANN001
    payload = _freshness_for_record(
        tmp_path,
        m444_record=_m444_record(**{field_name: bad_value}),
    )

    assert payload["freshness_state"] == "blocked_m444_manifest"
    assert expected_blocker in payload["freshness_blockers"]
    _assert_never_authorizes_or_mutates(payload)


def test_config_requires_expected_latest_bar_date(tmp_path) -> None:  # noqa: ANN001
    values = _config_values(tmp_path)
    values["expected_latest_bar_date"] = ""

    with pytest.raises(ValidationError, match="expected_latest_bar_date is required"):
        EtfSmaOfflineDailyCycleFreshnessCheckConfig(**values)


def test_config_rejects_non_iso_expected_latest_bar_date(tmp_path) -> None:  # noqa: ANN001
    values = _config_values(tmp_path)
    values["expected_latest_bar_date"] = "2026-6-7"

    with pytest.raises(
        ValidationError,
        match="expected_latest_bar_date must be a YYYY-MM-DD date",
    ):
        EtfSmaOfflineDailyCycleFreshnessCheckConfig(**values)


def test_parser_requires_expected_date_and_defaults_to_m445_paths() -> None:
    parser = _freshness_check_parser()
    options = {
        action.dest: action
        for action in parser._actions
        if getattr(action, "option_strings", ())
    }

    assert options["expected_latest_bar_date"].required is True
    assert options["run_id"].default == "m445_offline_daily_cycle_freshness_check"
    assert options["source_m444_path"].default == (
        "runs/paper_lab/m444_offline_daily_cycle_run_manifest.jsonl"
    )
    assert options["source_daily_bars_csv_path"].default == (
        "runs/operator_input/spy_daily_tiingo_adjusted_canonical_20260607.csv"
    )
    assert options["output_jsonl"].default == (
        "runs/paper_lab/m445_offline_daily_cycle_freshness_check.jsonl"
    )


def test_cli_dispatch_avoids_runtime_config_broker_and_network(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:  # noqa: ANN001
    def forbidden_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("M445 freshness check must not load runtime config")

    def forbidden_broker(*args: object, **kwargs: object) -> object:
        raise AssertionError("M445 freshness check must not build a broker")

    def forbidden_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("M445 freshness check must not open sockets")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)
    monkeypatch.setattr(socket, "socket", forbidden_socket)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    paths = _write_inputs(tmp_path)
    exit_code = cli_module.main(
        (
            "etf-sma-offline-daily-cycle-freshness-check",
            "--run-id",
            RUN_ID,
            "--source-m444-manifest",
            str(paths["m444"]),
            "--daily-bars-csv",
            str(paths["daily_bars_csv"]),
            "--expected-latest-bar-date",
            EXPECTED_DATE,
            "--output-jsonl",
            str(paths["output"]),
            "--format",
            "json",
        )
    )
    printed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert printed["freshness_state"] == "accepted_current_local_bars"
    assert _read_jsonl(paths["output"]) == [printed]
    _assert_never_authorizes_or_mutates(printed)


def test_run_writes_one_m445_artifact(tmp_path) -> None:  # noqa: ANN001
    paths = _write_inputs(tmp_path)
    config = _config(
        tmp_path,
        source_m444_path=paths["m444"],
        source_daily_bars_csv_path=paths["daily_bars_csv"],
        output_jsonl=paths["output"],
    )

    payload = run_etf_sma_offline_daily_cycle_freshness_check(config)

    assert _read_jsonl(paths["output"]) == [payload]
    assert payload["freshness_state"] == "accepted_current_local_bars"


def test_freshness_json_is_deterministic(tmp_path) -> None:  # noqa: ANN001
    first = _freshness_for_record(tmp_path)
    second = _freshness_for_record(tmp_path)

    assert first == second
    assert render_etf_sma_offline_daily_cycle_freshness_check_json(first) == (
        render_etf_sma_offline_daily_cycle_freshness_check_json(second)
    )


def test_runner_module_imports_no_broker_sdk_credentials_network_or_mutation_calls() -> None:
    imports = _import_references(MODULE_PATH)

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names(MODULE_PATH).isdisjoint(FORBIDDEN_CALL_NAMES)


def _freshness_for_record(
    tmp_path: Path,
    *,
    m444_record: object | None = None,
    csv_dates: tuple[str, ...] = ("2026-06-05", EXPECTED_DATE),
    expected_latest_bar_date: str = EXPECTED_DATE,
) -> dict[str, object]:
    payload, _paths = _freshness_for_record_with_paths(
        tmp_path,
        m444_record=m444_record,
        csv_dates=csv_dates,
        expected_latest_bar_date=expected_latest_bar_date,
    )
    return payload


def _freshness_for_record_with_paths(
    tmp_path: Path,
    *,
    m444_record: object | None = None,
    csv_dates: tuple[str, ...] = ("2026-06-05", EXPECTED_DATE),
    expected_latest_bar_date: str = EXPECTED_DATE,
) -> tuple[dict[str, object], dict[str, Path]]:
    paths = _write_inputs(tmp_path, m444_record=m444_record, csv_dates=csv_dates)
    payload = build_etf_sma_offline_daily_cycle_freshness_check(
        _config(
            tmp_path,
            source_m444_path=paths["m444"],
            source_daily_bars_csv_path=paths["daily_bars_csv"],
            output_jsonl=paths["output"],
            expected_latest_bar_date=expected_latest_bar_date,
        )
    )
    return payload, paths


def _freshness_for_m444_text(tmp_path: Path, text: str) -> dict[str, object]:
    paths = _write_inputs(tmp_path)
    paths["m444"].write_text(text, encoding="utf-8")
    return build_etf_sma_offline_daily_cycle_freshness_check(
        _config(
            tmp_path,
            source_m444_path=paths["m444"],
            source_daily_bars_csv_path=paths["daily_bars_csv"],
            output_jsonl=paths["output"],
        )
    )


def _freshness_for_m444_records(
    tmp_path: Path,
    *records: dict[str, object],
) -> dict[str, object]:
    paths = _write_inputs(tmp_path)
    _write_jsonl(paths["m444"], *records)
    return build_etf_sma_offline_daily_cycle_freshness_check(
        _config(
            tmp_path,
            source_m444_path=paths["m444"],
            source_daily_bars_csv_path=paths["daily_bars_csv"],
            output_jsonl=paths["output"],
        )
    )


def _config(
    tmp_path: Path,
    **overrides: object,
) -> EtfSmaOfflineDailyCycleFreshnessCheckConfig:
    return EtfSmaOfflineDailyCycleFreshnessCheckConfig(
        **_config_values(tmp_path, **overrides)
    )


def _config_values(tmp_path: Path, **overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "run_id": RUN_ID,
        "source_m444_path": tmp_path / "m444_manifest.jsonl",
        "source_daily_bars_csv_path": tmp_path / "spy_daily_bars.csv",
        "output_jsonl": tmp_path / "m445_freshness.jsonl",
        "expected_latest_bar_date": EXPECTED_DATE,
    }
    values.update(overrides)
    return values


def _write_inputs(
    tmp_path: Path,
    *,
    m444_record: object | None = None,
    csv_dates: tuple[str, ...] = ("2026-06-05", EXPECTED_DATE),
) -> dict[str, Path]:
    paths = {
        "m444": tmp_path / "m444_manifest.jsonl",
        "daily_bars_csv": tmp_path / "spy_daily_bars.csv",
        "output": tmp_path / "m445_freshness.jsonl",
    }
    if m444_record is not MISSING:
        _write_jsonl(
            paths["m444"],
            _m444_record() if m444_record is None else m444_record,
        )
    _write_daily_bars_csv(paths["daily_bars_csv"], csv_dates)
    return paths


def _m444_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "chain_blockers": [],
        "command": "etf-sma-offline-daily-cycle-run",
        "credential_access_attempted": False,
        "daily_chain_state": "accepted_observe_hold_noop",
        "daily_wrapper_state": "accepted_observe_hold_noop",
        "live_authorized": False,
        "milestone": "M444 - Offline daily cycle chain runner",
        "mutated": False,
        "network_access_attempted": False,
        "paper_action_authorized": False,
        "paper_submit_authorized": False,
        "profit_claim": "none",
        "readiness_cycle_decision": "hold/noop",
        "recommended_operator_action": "observe_hold_noop",
        "record_type": "etf_sma_offline_daily_cycle_run_manifest",
        "run_id": "m444_offline_daily_cycle_run",
        "submitted": False,
        "submit_authorized": False,
        "summary_cycle_decision": "hold/noop",
        "validation_cycle_decision": "hold/noop",
        "validation_state": "accepted_current_cycle_hold_noop",
    }
    record.update(overrides)
    return record


def _write_daily_bars_csv(path: Path, dates: tuple[str, ...]) -> Path:
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
    for index, day in enumerate(dates, 1):
        lines.append(
            ",".join(
                (
                    "SPY",
                    day,
                    str(100 + index),
                    str(101 + index),
                    str(99 + index),
                    str(100 + index),
                    str(100 + index),
                    "1000",
                )
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


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
        "network_access_attempted",
        "credential_access_attempted",
        "live_authorized",
    ):
        assert payload[field_name] is False
    assert payload["profit_claim"] == "none"


def _freshness_check_parser():
    parser = cli_module.build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", {}) or {}
        if "etf-sma-offline-daily-cycle-freshness-check" in choices:
            return choices["etf-sma-offline-daily-cycle-freshness-check"]
    raise AssertionError("etf-sma-offline-daily-cycle-freshness-check parser not found")


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
