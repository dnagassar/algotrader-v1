from __future__ import annotations

import ast
import json
from pathlib import Path

import algotrader.cli as cli_module
from algotrader.research.etf_sma_evidence_rollup import (
    ETF_SMA_EVIDENCE_ROLLUP_LABELS,
    EtfSmaEvidenceRollupConfig,
    build_etf_sma_evidence_rollup,
    render_etf_sma_evidence_rollup_json,
    write_etf_sma_evidence_rollup_jsonl,
)


MODULE_PATH = Path("src/algotrader/research/etf_sma_evidence_rollup.py")
FIXED_GENERATED_AT = "2026-06-06T00:00:00+00:00"
_COMMAND = "etf-sma-evidence-rollup"
_M412_RAW_CLOSE_LIMITATION = (
    "Evidence is raw-close price-return evidence only; M412 does not infer "
    "adjusted-close, dividend, split, or total-return evidence."
)
_SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "broker_actions_performed",
    "broker_network_access",
    "credential_access",
    "network_access_attempted",
    "credential_access_attempted",
    "paper_submit_authorized",
    "live_authorized",
    "broker_mutation_authorized",
    "market_data_fetch_performed",
)
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    "algotrader.portfolio",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "alpaca",
    "alpaca_trade_api",
    "http",
    "httpx",
    "requests",
    "socket",
    "urllib",
    "yfinance",
)
_FORBIDDEN_CALL_NAMES = {
    "cancel_order",
    "close_position",
    "connect",
    "create_order",
    "download",
    "getenv",
    "os.getenv",
    "request",
    "socket.socket",
    "submit_order",
    "urlopen",
}


def test_valid_m411_m412_artifacts_build_successful_rollup(tmp_path) -> None:  # noqa: ANN001
    manual_log, refresh_log, brief_log = _write_valid_artifacts(tmp_path)

    payload = build_etf_sma_evidence_rollup(
        _config(manual_log, refresh_log, brief_log)
    )

    assert payload["record_type"] == "etf_sma_evidence_rollup"
    assert payload["command"] == _COMMAND
    assert payload["milestone"] == "M413"
    assert payload["rollup_state"] == "offline_evidence_rollup_ready"
    assert payload["artifact_consistency_state"] == "m411_m412_artifacts_consistent"
    assert payload["artifact_consistency"]["matching_evidence"] is True
    assert payload["blockers"] == []
    assert payload["labels"] == list(ETF_SMA_EVIDENCE_ROLLUP_LABELS)
    assert payload["source_artifacts"]["manual_import_log"]["parsed"] is True
    assert payload["source_artifacts"]["backtest_refresh_log"]["parsed"] is True
    assert payload["source_artifacts"]["operating_brief_log"]["parsed"] is True
    assert (
        payload["operator_data_provenance_status"]
        == "m411_manual_import_artifact_operator_bars_ready"
    )
    assert payload["data_basis"] == "raw_close_price_return"
    assert payload["raw_close_limitation"] == _M412_RAW_CLOSE_LIMITATION
    assert payload["evidence_scope"] == "signal_backtest_pipeline_only"
    assert payload["performance_evidence_state"] == "post_signal_returns_evaluated"
    assert payload["manual_import_state"] == "canonical_local_operator_bars_ready"
    assert payload["refresh_state"] == "backtest_evidence_refreshed"
    assert payload["brief_state"] == "m411_evidence_summarized"
    assert payload["usable_bar_count"] == 1255
    assert payload["evaluated_return_count"] == 1055
    assert payload["entry_count"] == 2
    assert payload["exit_count"] == 1
    assert payload["trade_count"] == 3
    assert payload["final_posture"] == "risk_on"
    assert payload["final_exposure"] == 1
    assert payload["final_decision"] == "hold_long"
    assert payload["broker_position_state"] == "not_observed_in_m413"
    assert payload["open_order_state"] == "not_observed_in_m413"
    assert payload["paper_action_recommendation"] == "none"
    assert payload["profit_claim"] == "none"
    assert "offline_adjusted_close_evidence_upgrade" in payload["next_allowed_actions"]
    assert all("submit" not in action for action in payload["next_allowed_actions"])
    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False


def test_missing_manual_import_log_blocks(tmp_path) -> None:  # noqa: ANN001
    refresh_log = _write_jsonl(tmp_path / "refresh.jsonl", _refresh_record())
    brief_log = _write_jsonl(tmp_path / "brief.jsonl", _brief_record())

    payload = build_etf_sma_evidence_rollup(
        _config(tmp_path / "missing_manual.jsonl", refresh_log, brief_log)
    )

    assert payload["rollup_state"] == "blocked_invalid_offline_evidence"
    assert payload["source_artifacts"]["manual_import_log"]["found"] is False
    assert "manual_import_artifact_path_not_found" in payload["blockers"]
    assert payload["paper_submit_authorized"] is False


def test_missing_backtest_refresh_log_blocks(tmp_path) -> None:  # noqa: ANN001
    manual_log = _write_jsonl(tmp_path / "manual.jsonl", _manual_record())
    brief_log = _write_jsonl(tmp_path / "brief.jsonl", _brief_record())

    payload = build_etf_sma_evidence_rollup(
        _config(manual_log, tmp_path / "missing_refresh.jsonl", brief_log)
    )

    assert payload["rollup_state"] == "blocked_invalid_offline_evidence"
    assert payload["source_artifacts"]["backtest_refresh_log"]["found"] is False
    assert "backtest_refresh_artifact_path_not_found" in payload["blockers"]
    assert payload["broker_mutation_authorized"] is False


def test_missing_operating_brief_log_blocks(tmp_path) -> None:  # noqa: ANN001
    manual_log = _write_jsonl(tmp_path / "manual.jsonl", _manual_record())
    refresh_log = _write_jsonl(tmp_path / "refresh.jsonl", _refresh_record())

    payload = build_etf_sma_evidence_rollup(
        _config(manual_log, refresh_log, tmp_path / "missing_brief.jsonl")
    )

    assert payload["rollup_state"] == "blocked_invalid_offline_evidence"
    assert payload["source_artifacts"]["operating_brief_log"]["found"] is False
    assert "operating_brief_artifact_path_not_found" in payload["blockers"]
    assert payload["live_authorized"] is False


def test_m411_refresh_and_m412_brief_mismatch_blocks(tmp_path) -> None:  # noqa: ANN001
    brief_record = _brief_record()
    brief_record["final_decision"] = "raise_cash"
    manual_log = _write_jsonl(tmp_path / "manual.jsonl", _manual_record())
    refresh_log = _write_jsonl(tmp_path / "refresh.jsonl", _refresh_record())
    brief_log = _write_jsonl(tmp_path / "brief.jsonl", brief_record)

    payload = build_etf_sma_evidence_rollup(
        _config(manual_log, refresh_log, brief_log)
    )

    assert payload["rollup_state"] == "blocked_invalid_offline_evidence"
    assert "refresh_brief_final_decision_mismatch" in payload["blockers"]
    assert payload["artifact_consistency"]["matching_evidence"] is False


def test_profit_claim_other_than_none_blocks(tmp_path) -> None:  # noqa: ANN001
    refresh_record = _refresh_record()
    refresh_record["profit_claim"] = "profitable"
    manual_log = _write_jsonl(tmp_path / "manual.jsonl", _manual_record())
    refresh_log = _write_jsonl(tmp_path / "refresh.jsonl", refresh_record)
    brief_log = _write_jsonl(tmp_path / "brief.jsonl", _brief_record())

    payload = build_etf_sma_evidence_rollup(
        _config(manual_log, refresh_log, brief_log)
    )

    assert payload["rollup_state"] == "blocked_invalid_offline_evidence"
    assert "backtest_refresh_artifact_profit_claim_not_none" in payload["blockers"]
    assert payload["profit_claim"] == "none"
    assert payload["paper_action_recommendation"] == "none"


def test_submitted_or_mutated_true_in_any_input_blocks(tmp_path) -> None:  # noqa: ANN001
    for source_name, field_name in (
        ("manual", "submitted"),
        ("manual", "mutated"),
        ("refresh", "submitted"),
        ("refresh", "mutated"),
        ("brief", "submitted"),
        ("brief", "mutated"),
    ):
        records = _records_with(source_name, field_name, True)
        payload = _payload_from_records(tmp_path, source_name, field_name, records)
        prefix = _source_prefix(source_name)

        assert payload["rollup_state"] == "blocked_invalid_offline_evidence"
        assert f"{prefix}_{field_name}_not_false" in payload["blockers"]
        assert payload["submitted"] is False
        assert payload["mutated"] is False


def test_broker_network_or_credential_flags_true_in_any_input_block(
    tmp_path,
) -> None:  # noqa: ANN001
    for source_name, field_name in (
        ("manual", "broker_network_access"),
        ("manual", "credential_access"),
        ("manual", "network_access_attempted"),
        ("manual", "credential_access_attempted"),
        ("refresh", "broker_network_access"),
        ("refresh", "credential_access"),
        ("refresh", "network_access_attempted"),
        ("refresh", "credential_access_attempted"),
        ("brief", "broker_network_access"),
        ("brief", "credential_access"),
        ("brief", "network_access_attempted"),
        ("brief", "credential_access_attempted"),
    ):
        records = _records_with(source_name, field_name, True)
        payload = _payload_from_records(tmp_path, source_name, field_name, records)
        prefix = _source_prefix(source_name)

        assert payload["rollup_state"] == "blocked_invalid_offline_evidence"
        assert f"{prefix}_{field_name}_not_false" in payload["blockers"]
        assert payload["broker_network_access"] is False
        assert payload["credential_access"] is False
        assert payload["network_access_attempted"] is False
        assert payload["credential_access_attempted"] is False


def test_paper_live_or_broker_authorization_true_in_any_input_blocks(
    tmp_path,
) -> None:  # noqa: ANN001
    for source_name, field_name in (
        ("manual", "paper_submit_authorized"),
        ("manual", "live_authorized"),
        ("manual", "broker_mutation_authorized"),
        ("refresh", "paper_submit_authorized"),
        ("refresh", "live_authorized"),
        ("refresh", "broker_mutation_authorized"),
        ("brief", "paper_submit_authorized"),
        ("brief", "live_authorized"),
        ("brief", "broker_mutation_authorized"),
    ):
        records = _records_with(source_name, field_name, True)
        payload = _payload_from_records(tmp_path, source_name, field_name, records)
        prefix = _source_prefix(source_name)

        assert payload["rollup_state"] == "blocked_invalid_offline_evidence"
        assert f"{prefix}_{field_name}_not_false" in payload["blockers"]
        assert payload["paper_submit_authorized"] is False
        assert payload["live_authorized"] is False
        assert payload["broker_mutation_authorized"] is False


def test_raw_close_limitation_is_preserved_in_output(tmp_path) -> None:  # noqa: ANN001
    manual_log, refresh_log, brief_log = _write_valid_artifacts(tmp_path)

    payload = build_etf_sma_evidence_rollup(
        _config(manual_log, refresh_log, brief_log)
    )

    assert payload["data_basis"] == "raw_close_price_return"
    assert payload["raw_close_limitation"] == _M412_RAW_CLOSE_LIMITATION
    assert payload["raw_close_price_return_evidence_only"] is True
    assert payload["evidence_scope"] == "signal_backtest_pipeline_only"


def test_adjusted_close_or_total_return_evidence_claim_blocks(tmp_path) -> None:  # noqa: ANN001
    brief_record = _brief_record()
    brief_record["data_basis"] = "adjusted_close_price_return"
    manual_log = _write_jsonl(tmp_path / "manual.jsonl", _manual_record())
    refresh_log = _write_jsonl(tmp_path / "refresh.jsonl", _refresh_record())
    brief_log = _write_jsonl(tmp_path / "brief.jsonl", brief_record)

    payload = build_etf_sma_evidence_rollup(
        _config(manual_log, refresh_log, brief_log)
    )

    assert payload["rollup_state"] == "blocked_invalid_offline_evidence"
    assert "operating_brief_artifact_data_basis_not_raw_close" in payload["blockers"]
    assert payload["data_basis"] == "raw_close_price_return"


def test_output_json_and_jsonl_write_are_deterministic(tmp_path) -> None:  # noqa: ANN001
    manual_log, refresh_log, brief_log = _write_valid_artifacts(tmp_path)
    config = _config(manual_log, refresh_log, brief_log)
    payload_a = build_etf_sma_evidence_rollup(config)
    payload_b = build_etf_sma_evidence_rollup(config)
    output_a = tmp_path / "a.jsonl"
    output_b = tmp_path / "b.jsonl"

    json_a = render_etf_sma_evidence_rollup_json(payload_a)
    json_b = render_etf_sma_evidence_rollup_json(payload_b)
    write_etf_sma_evidence_rollup_jsonl(payload_a, output_a)
    write_etf_sma_evidence_rollup_jsonl(payload_b, output_b)

    assert payload_a == payload_b
    assert json_a == json_b
    assert output_a.read_bytes() == output_b.read_bytes()
    assert output_a.read_text(encoding="utf-8").count("\n") == 1
    assert json.loads(output_a.read_text(encoding="utf-8")) == json.loads(json_a)


def test_cli_writes_evidence_rollup_before_runtime_config_loading(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:  # noqa: ANN001
    manual_log, refresh_log, brief_log = _write_valid_artifacts(tmp_path)
    run_log = tmp_path / "m413.jsonl"

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("evidence rollup must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    exit_code = cli_module.main(
        [
            _COMMAND,
            "--run-id",
            "unit_m413_evidence_rollup",
            "--run-log",
            str(run_log),
            "--manual-import-log",
            str(manual_log),
            "--backtest-refresh-log",
            str(refresh_log),
            "--operating-brief-log",
            str(brief_log),
            "--generated-at",
            FIXED_GENERATED_AT,
            "--format",
            "json",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert json.loads(captured.out) == _read_jsonl(run_log)[0]
    assert _read_jsonl(run_log)[0]["run_id"] == "unit_m413_evidence_rollup"


def test_evidence_rollup_command_has_parameterized_paths_and_no_stale_defaults() -> None:
    parser = _evidence_rollup_parser()
    defaults = {
        action.dest: action.default
        for action in parser._actions
        if getattr(action, "option_strings", ())
    }

    assert defaults["run_id"] is None
    assert defaults["run_log"] is None
    assert defaults["manual_import_log"] is None
    assert defaults["backtest_refresh_log"] is None
    assert defaults["operating_brief_log"] is None
    assert defaults["generated_at"] is None


def test_evidence_rollup_module_imports_no_broker_sdk_network_or_runtime_deps() -> None:
    imports = _import_references()

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _config(
    manual_log: Path,
    refresh_log: Path,
    brief_log: Path,
) -> EtfSmaEvidenceRollupConfig:
    return EtfSmaEvidenceRollupConfig(
        run_id="unit_m413_evidence_rollup",
        symbol="SPY",
        manual_import_log=manual_log,
        backtest_refresh_log=refresh_log,
        operating_brief_log=brief_log,
        generated_at=FIXED_GENERATED_AT,
    )


def _write_valid_artifacts(tmp_path: Path) -> tuple[Path, Path, Path]:
    return (
        _write_jsonl(tmp_path / "manual.jsonl", _manual_record()),
        _write_jsonl(tmp_path / "refresh.jsonl", _refresh_record()),
        _write_jsonl(tmp_path / "brief.jsonl", _brief_record()),
    )


def _records_with(
    source_name: str,
    field_name: str,
    value: object,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    manual_record = _manual_record()
    refresh_record = _refresh_record()
    brief_record = _brief_record()
    if source_name == "manual":
        manual_record[field_name] = value
    elif source_name == "refresh":
        refresh_record[field_name] = value
    elif source_name == "brief":
        brief_record[field_name] = value
    else:
        raise AssertionError(f"unknown source: {source_name}")
    return manual_record, refresh_record, brief_record


def _payload_from_records(
    tmp_path: Path,
    source_name: str,
    field_name: str,
    records: tuple[dict[str, object], dict[str, object], dict[str, object]],
) -> dict[str, object]:
    manual_record, refresh_record, brief_record = records
    manual_log = _write_jsonl(
        tmp_path / f"{source_name}_{field_name}_manual.jsonl",
        manual_record,
    )
    refresh_log = _write_jsonl(
        tmp_path / f"{source_name}_{field_name}_refresh.jsonl",
        refresh_record,
    )
    brief_log = _write_jsonl(
        tmp_path / f"{source_name}_{field_name}_brief.jsonl",
        brief_record,
    )
    return build_etf_sma_evidence_rollup(
        _config(manual_log, refresh_log, brief_log)
    )


def _source_prefix(source_name: str) -> str:
    if source_name == "manual":
        return "manual_import_artifact"
    if source_name == "refresh":
        return "backtest_refresh_artifact"
    if source_name == "brief":
        return "operating_brief_artifact"
    raise AssertionError(f"unknown source: {source_name}")


def _manual_record() -> dict[str, object]:
    record = _shared_record()
    record.update(
        {
            "record_type": "etf_sma_local_bars_manual_import",
            "run_id": "m411_spy_local_bars_manual_import",
            "command": "etf-sma-local-bars-manual-import",
            "manual_import_state": "canonical_local_operator_bars_ready",
            "canonical_csv_written": True,
            "refresh_rerun_performed": True,
            "broker_network_access": False,
            "credential_access": False,
            "submit_path_allowed": False,
            "operator_evidence_synthetic": False,
            "fixture_sample_synthetic_test_data_used_as_operator_evidence": False,
            "data_provenance": {
                "credential_access_attempted": False,
                "local_csv_only": True,
                "network_access_attempted": False,
                "operator_evidence_synthetic": False,
            },
            "provenance_validation": {
                "adjustment_policy": "raw close only; no adjusted close column present",
                "valid": True,
            },
        }
    )
    return record


def _refresh_record() -> dict[str, object]:
    record = _shared_record()
    record.update(
        {
            "record_type": "etf_sma_local_bars_backtest_refresh",
            "run_id": "m411_spy_local_bars_manual_import",
            "command": "etf-sma-local-bars-backtest-refresh",
            "backtest_state": "completed",
            "data_provenance": {
                "credential_access_attempted": False,
                "local_csv_only": True,
                "network_access_attempted": False,
                "operator_evidence_synthetic": False,
            },
        }
    )
    return record


def _brief_record() -> dict[str, object]:
    record = _shared_record()
    record.update(
        {
            "record_type": "etf_sma_operating_brief",
            "run_id": "m412_spy_etf_sma_operating_brief_from_m411",
            "command": "etf-sma-operating-brief",
            "milestone": "M412",
            "brief_state": "m411_evidence_summarized",
            "manual_import_state": "canonical_local_operator_bars_ready",
            "broker_network_access": False,
            "credential_access": False,
            "paper_submit_authorized": False,
            "raw_close_limitation": _M412_RAW_CLOSE_LIMITATION,
            "raw_close_price_return_evidence_only": True,
            "cycle_update_summary": {
                "entry_count": 2,
                "exit_count": 1,
                "trade_count": 3,
                "final_posture": "risk_on",
                "final_exposure": 1,
                "final_decision": "hold_long",
                "paper_submit_authorized": False,
                "live_authorized": False,
                "profit_claim": "none",
            },
        }
    )
    return record


def _shared_record() -> dict[str, object]:
    return {
        "symbol": "SPY",
        "strategy": "spy_etf_sma_50_200_daily_long_only",
        "refresh_state": "backtest_evidence_refreshed",
        "performance_evidence_state": "post_signal_returns_evaluated",
        "usable_bar_count": 1255,
        "evaluated_return_count": 1055,
        "final_posture": "risk_on",
        "final_exposure": 1,
        "final_decision": "hold_long",
        "entry_count": 2,
        "exit_count": 1,
        "trade_count": 3,
        "profit_claim": "none",
        "blockers": [],
        "submitted": False,
        "mutated": False,
        "submit_authorized": False,
        "paper_submit_approved": False,
        "broker_mutation_authorized": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "market_data_fetch_performed": False,
        "live_authorized": False,
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


def _evidence_rollup_parser():
    parser = cli_module.build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", {}) or {}
        if _COMMAND in choices:
            return choices[_COMMAND]
    raise AssertionError("etf-sma-evidence-rollup parser not found")


def _import_references() -> set[str]:
    imports: set[str] = set()
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
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
    return any(
        module == prefix or module.startswith(f"{prefix}.")
        for prefix in prefixes
    )
