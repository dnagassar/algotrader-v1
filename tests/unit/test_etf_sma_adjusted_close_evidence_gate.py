from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import algotrader.cli as cli_module
from algotrader.research.etf_sma_adjusted_close_evidence_gate import (
    ETF_SMA_ADJUSTED_CLOSE_EVIDENCE_GATE_LABELS,
    EtfSmaAdjustedCloseEvidenceGateConfig,
    build_etf_sma_adjusted_close_evidence_gate,
    render_etf_sma_adjusted_close_evidence_gate_json,
    write_etf_sma_adjusted_close_evidence_gate_jsonl,
)


MODULE_PATH = Path("src/algotrader/research/etf_sma_adjusted_close_evidence_gate.py")
FIXED_GENERATED_AT = "2026-06-06T00:00:00+00:00"
_COMMAND = "etf-sma-adjusted-close-evidence-gate"
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
    "os",
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


def test_valid_blocked_gate_without_adjusted_close_operator_input(tmp_path) -> None:  # noqa: ANN001
    evidence_rollup_log = _write_jsonl(tmp_path / "m413.jsonl", _m413_record())

    payload = build_etf_sma_adjusted_close_evidence_gate(
        _config(tmp_path, evidence_rollup_log)
    )

    assert payload["record_type"] == "etf_sma_adjusted_close_evidence_gate"
    assert payload["command"] == _COMMAND
    assert payload["milestone"] == "M414"
    assert (
        payload["adjusted_close_gate_state"]
        == "blocked_missing_adjusted_close_operator_input"
    )
    assert payload["blockers"] == ["missing_adjusted_close_operator_input"]
    assert payload["labels"] == list(ETF_SMA_ADJUSTED_CLOSE_EVIDENCE_GATE_LABELS)
    assert payload["source_artifacts"]["evidence_rollup_log"]["parsed"] is True
    assert payload["prior_evidence_rollup_state"] == "offline_evidence_rollup_ready"
    assert payload["prior_data_basis"] == "raw_close_price_return"
    assert payload["target_data_basis"] == "adjusted_close_price_return"
    assert payload["total_return_claim"] == "none"
    assert payload["profit_claim"] == "none"
    assert payload["evidence_scope"] == "signal_backtest_pipeline_only"
    assert payload["raw_close_limitation_preserved"] is True
    assert payload["adjusted_close_evidence_available"] is False
    assert payload["operator_input_required"] is True
    assert "operator_supply_adjusted_close_csv_and_manifest" in payload["next_allowed_actions"]
    assert all("submit" not in action for action in payload["next_allowed_actions"])
    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False


def test_valid_adjusted_close_operator_input_opens_gate(tmp_path) -> None:  # noqa: ANN001
    evidence_rollup_log = _write_jsonl(tmp_path / "m413.jsonl", _m413_record())
    csv_path = _write_adjusted_csv(tmp_path / "adjusted.csv")
    manifest_path = _write_manifest(tmp_path / "manifest.json", csv_path)

    payload = build_etf_sma_adjusted_close_evidence_gate(
        _config(
            tmp_path,
            evidence_rollup_log,
            adjusted_bars_csv=csv_path,
            provenance_manifest=manifest_path,
        )
    )

    assert payload["adjusted_close_gate_state"] == "adjusted_close_evidence_gate_ready"
    assert payload["blockers"] == []
    assert payload["adjusted_close_evidence_available"] is True
    assert payload["operator_input_required"] is False
    assert payload["source_artifacts"]["adjusted_bars_csv"]["valid"] is True
    assert payload["source_artifacts"]["provenance_manifest"]["valid"] is True
    assert all("submit" not in action for action in payload["next_allowed_actions"])


def test_missing_m413_rollup_blocks(tmp_path) -> None:  # noqa: ANN001
    payload = build_etf_sma_adjusted_close_evidence_gate(
        _config(tmp_path, tmp_path / "missing.jsonl")
    )

    assert payload["adjusted_close_gate_state"] == "blocked_invalid_prior_evidence_rollup"
    assert payload["prior_evidence_rollup_state"] == "missing"
    assert "evidence_rollup_artifact_path_not_found" in payload["blockers"]
    assert payload["paper_submit_authorized"] is False


def test_m413_profit_claim_other_than_none_blocks(tmp_path) -> None:  # noqa: ANN001
    record = _m413_record()
    record["profit_claim"] = "profitable"
    evidence_rollup_log = _write_jsonl(tmp_path / "m413.jsonl", record)

    payload = build_etf_sma_adjusted_close_evidence_gate(
        _config(tmp_path, evidence_rollup_log)
    )

    assert payload["adjusted_close_gate_state"] == "blocked_invalid_prior_evidence_rollup"
    assert "prior_evidence_rollup_profit_claim_not_none" in payload["blockers"]
    assert payload["profit_claim"] == "none"


def test_m413_submitted_or_mutated_true_blocks(tmp_path) -> None:  # noqa: ANN001
    for field_name in ("submitted", "mutated"):
        record = _m413_record()
        record[field_name] = True
        evidence_rollup_log = _write_jsonl(tmp_path / f"{field_name}.jsonl", record)

        payload = build_etf_sma_adjusted_close_evidence_gate(
            _config(tmp_path, evidence_rollup_log)
        )

        assert payload["adjusted_close_gate_state"] == "blocked_invalid_prior_evidence_rollup"
        assert f"prior_evidence_rollup_{field_name}_not_false" in payload["blockers"]
        assert payload["submitted"] is False
        assert payload["mutated"] is False


def test_m413_broker_network_or_credential_flags_true_block(tmp_path) -> None:  # noqa: ANN001
    for field_name in (
        "broker_network_access",
        "credential_access",
        "network_access_attempted",
        "credential_access_attempted",
    ):
        record = _m413_record()
        record[field_name] = True
        evidence_rollup_log = _write_jsonl(tmp_path / f"{field_name}.jsonl", record)

        payload = build_etf_sma_adjusted_close_evidence_gate(
            _config(tmp_path, evidence_rollup_log)
        )

        assert payload["adjusted_close_gate_state"] == "blocked_invalid_prior_evidence_rollup"
        assert f"prior_evidence_rollup_{field_name}_not_false" in payload["blockers"]
        assert payload["broker_network_access"] is False
        assert payload["credential_access"] is False
        assert payload["network_access_attempted"] is False
        assert payload["credential_access_attempted"] is False


def test_m413_paper_live_or_broker_authorization_true_blocks(tmp_path) -> None:  # noqa: ANN001
    for field_name in (
        "paper_submit_authorized",
        "live_authorized",
        "broker_mutation_authorized",
    ):
        record = _m413_record()
        record[field_name] = True
        evidence_rollup_log = _write_jsonl(tmp_path / f"{field_name}.jsonl", record)

        payload = build_etf_sma_adjusted_close_evidence_gate(
            _config(tmp_path, evidence_rollup_log)
        )

        assert payload["adjusted_close_gate_state"] == "blocked_invalid_prior_evidence_rollup"
        assert f"prior_evidence_rollup_{field_name}_not_false" in payload["blockers"]
        assert payload["paper_submit_authorized"] is False
        assert payload["live_authorized"] is False
        assert payload["broker_mutation_authorized"] is False


def test_m413_data_basis_not_raw_close_blocks(tmp_path) -> None:  # noqa: ANN001
    record = _m413_record()
    record["data_basis"] = "adjusted_close_price_return"
    evidence_rollup_log = _write_jsonl(tmp_path / "m413.jsonl", record)

    payload = build_etf_sma_adjusted_close_evidence_gate(
        _config(tmp_path, evidence_rollup_log)
    )

    assert payload["adjusted_close_gate_state"] == "blocked_invalid_prior_evidence_rollup"
    assert "prior_evidence_rollup_data_basis_not_raw_close" in payload["blockers"]
    assert payload["prior_data_basis"] == "raw_close_price_return"
    assert (
        payload["prior_evidence_rollup_declared_data_basis"]
        == "adjusted_close_price_return"
    )


def test_adjusted_csv_without_manifest_blocks(tmp_path) -> None:  # noqa: ANN001
    evidence_rollup_log = _write_jsonl(tmp_path / "m413.jsonl", _m413_record())
    csv_path = _write_adjusted_csv(tmp_path / "adjusted.csv")

    payload = build_etf_sma_adjusted_close_evidence_gate(
        _config(tmp_path, evidence_rollup_log, adjusted_bars_csv=csv_path)
    )

    assert (
        payload["adjusted_close_gate_state"]
        == "blocked_invalid_adjusted_close_operator_input"
    )
    assert "adjusted_bars_csv_without_provenance_manifest" in payload["blockers"]
    assert payload["adjusted_close_evidence_available"] is False


def test_manifest_without_adjusted_csv_blocks(tmp_path) -> None:  # noqa: ANN001
    evidence_rollup_log = _write_jsonl(tmp_path / "m413.jsonl", _m413_record())
    csv_path = _write_adjusted_csv(tmp_path / "adjusted.csv")
    manifest_path = _write_manifest(tmp_path / "manifest.json", csv_path)

    payload = build_etf_sma_adjusted_close_evidence_gate(
        _config(tmp_path, evidence_rollup_log, provenance_manifest=manifest_path)
    )

    assert (
        payload["adjusted_close_gate_state"]
        == "blocked_invalid_adjusted_close_operator_input"
    )
    assert "provenance_manifest_without_adjusted_bars_csv" in payload["blockers"]
    assert payload["adjusted_close_evidence_available"] is False


def test_invalid_manifest_sha256_blocks(tmp_path) -> None:  # noqa: ANN001
    evidence_rollup_log = _write_jsonl(tmp_path / "m413.jsonl", _m413_record())
    csv_path = _write_adjusted_csv(tmp_path / "adjusted.csv")
    manifest_path = _write_manifest(
        tmp_path / "manifest.json",
        csv_path,
        expected_input_sha256="A" * 64,
    )

    payload = build_etf_sma_adjusted_close_evidence_gate(
        _config(
            tmp_path,
            evidence_rollup_log,
            adjusted_bars_csv=csv_path,
            provenance_manifest=manifest_path,
        )
    )

    assert (
        payload["adjusted_close_gate_state"]
        == "blocked_invalid_adjusted_close_operator_input"
    )
    assert "invalid_expected_input_sha256" in payload["blockers"]


def test_csv_hash_mismatch_blocks(tmp_path) -> None:  # noqa: ANN001
    evidence_rollup_log = _write_jsonl(tmp_path / "m413.jsonl", _m413_record())
    csv_path = _write_adjusted_csv(tmp_path / "adjusted.csv")
    manifest_path = _write_manifest(
        tmp_path / "manifest.json",
        csv_path,
        expected_input_sha256="0" * 64,
    )

    payload = build_etf_sma_adjusted_close_evidence_gate(
        _config(
            tmp_path,
            evidence_rollup_log,
            adjusted_bars_csv=csv_path,
            provenance_manifest=manifest_path,
        )
    )

    assert (
        payload["adjusted_close_gate_state"]
        == "blocked_invalid_adjusted_close_operator_input"
    )
    assert "expected_input_sha256_mismatch" in payload["blockers"]


def test_manifest_data_basis_not_adjusted_close_blocks(tmp_path) -> None:  # noqa: ANN001
    evidence_rollup_log = _write_jsonl(tmp_path / "m413.jsonl", _m413_record())
    csv_path = _write_adjusted_csv(tmp_path / "adjusted.csv")
    manifest_path = _write_manifest(
        tmp_path / "manifest.json",
        csv_path,
        data_basis="raw_close_price_return",
    )

    payload = build_etf_sma_adjusted_close_evidence_gate(
        _config(
            tmp_path,
            evidence_rollup_log,
            adjusted_bars_csv=csv_path,
            provenance_manifest=manifest_path,
        )
    )

    assert (
        payload["adjusted_close_gate_state"]
        == "blocked_invalid_adjusted_close_operator_input"
    )
    assert "manifest_data_basis_not_adjusted_close_price_return" in payload["blockers"]


def test_ambiguous_or_non_strict_csv_schema_blocks(tmp_path) -> None:  # noqa: ANN001
    evidence_rollup_log = _write_jsonl(tmp_path / "m413.jsonl", _m413_record())
    csv_path = _write_text(
        tmp_path / "adjusted.csv",
        "date,close,adj_close,volume\n2020-01-02,100,99,10\n",
    )
    manifest_path = _write_manifest(tmp_path / "manifest.json", csv_path)

    payload = build_etf_sma_adjusted_close_evidence_gate(
        _config(
            tmp_path,
            evidence_rollup_log,
            adjusted_bars_csv=csv_path,
            provenance_manifest=manifest_path,
        )
    )

    assert (
        payload["adjusted_close_gate_state"]
        == "blocked_invalid_adjusted_close_operator_input"
    )
    assert "adjusted_bars_csv_schema_non_strict_or_ambiguous" in payload["blockers"]


def test_forbidden_provenance_terms_block(tmp_path) -> None:  # noqa: ANN001
    evidence_rollup_log = _write_jsonl(tmp_path / "m413.jsonl", _m413_record())
    csv_path = _write_adjusted_csv(tmp_path / "adjusted.csv")
    manifest_path = _write_manifest(
        tmp_path / "manifest.json",
        csv_path,
        source_notes="Codex generated synthetic sample data",
    )

    payload = build_etf_sma_adjusted_close_evidence_gate(
        _config(
            tmp_path,
            evidence_rollup_log,
            adjusted_bars_csv=csv_path,
            provenance_manifest=manifest_path,
        )
    )

    assert (
        payload["adjusted_close_gate_state"]
        == "blocked_invalid_adjusted_close_operator_input"
    )
    assert (
        "provenance_rejected_generated_sample_fixture_test_synthetic_codex"
        in payload["blockers"]
    )


def test_output_json_and_jsonl_write_are_deterministic(tmp_path) -> None:  # noqa: ANN001
    evidence_rollup_log = _write_jsonl(tmp_path / "m413.jsonl", _m413_record())
    config = _config(tmp_path, evidence_rollup_log)
    payload_a = build_etf_sma_adjusted_close_evidence_gate(config)
    payload_b = build_etf_sma_adjusted_close_evidence_gate(config)
    output_a = tmp_path / "a.jsonl"
    output_b = tmp_path / "b.jsonl"

    json_a = render_etf_sma_adjusted_close_evidence_gate_json(payload_a)
    json_b = render_etf_sma_adjusted_close_evidence_gate_json(payload_b)
    write_etf_sma_adjusted_close_evidence_gate_jsonl(payload_a, output_a)
    write_etf_sma_adjusted_close_evidence_gate_jsonl(payload_b, output_b)

    assert payload_a == payload_b
    assert json_a == json_b
    assert output_a.read_bytes() == output_b.read_bytes()
    assert output_a.read_text(encoding="utf-8").count("\n") == 1
    assert json.loads(output_a.read_text(encoding="utf-8")) == json.loads(json_a)


def test_cli_writes_gate_before_runtime_config_loading(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:  # noqa: ANN001
    evidence_rollup_log = _write_jsonl(tmp_path / "m413.jsonl", _m413_record())
    run_log = tmp_path / "m414.jsonl"

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("adjusted-close gate must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    exit_code = cli_module.main(
        [
            _COMMAND,
            "--run-id",
            "unit_m414_adjusted_close_gate",
            "--run-log",
            str(run_log),
            "--evidence-rollup-log",
            str(evidence_rollup_log),
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
    assert _read_jsonl(run_log)[0]["run_id"] == "unit_m414_adjusted_close_gate"


def test_adjusted_close_gate_command_has_parameterized_paths_and_no_stale_defaults() -> None:
    parser = _adjusted_close_gate_parser()
    defaults = {
        action.dest: action.default
        for action in parser._actions
        if getattr(action, "option_strings", ())
    }

    assert defaults["run_id"] is None
    assert defaults["run_log"] is None
    assert defaults["evidence_rollup_log"] is None
    assert defaults["adjusted_bars_csv"] is None
    assert defaults["provenance_manifest"] is None
    assert defaults["generated_at"] is None


def test_adjusted_close_gate_module_imports_no_broker_sdk_network_or_runtime_deps() -> None:
    imports = _import_references()

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _config(
    tmp_path: Path,
    evidence_rollup_log: Path,
    *,
    adjusted_bars_csv: Path | None = None,
    provenance_manifest: Path | None = None,
) -> EtfSmaAdjustedCloseEvidenceGateConfig:
    return EtfSmaAdjustedCloseEvidenceGateConfig(
        run_id="unit_m414_adjusted_close_gate",
        symbol="SPY",
        run_log=tmp_path / "m414.jsonl",
        evidence_rollup_log=evidence_rollup_log,
        adjusted_bars_csv=adjusted_bars_csv,
        provenance_manifest=provenance_manifest,
        generated_at=FIXED_GENERATED_AT,
    )


def _m413_record() -> dict[str, object]:
    return {
        "milestone": "M413",
        "record_type": "etf_sma_evidence_rollup",
        "command": "etf-sma-evidence-rollup",
        "run_id": "m413_spy_etf_sma_offline_evidence_rollup_from_m411_m412",
        "symbol": "SPY",
        "strategy": "spy_etf_sma_50_200_daily_long_only",
        "rollup_state": "offline_evidence_rollup_ready",
        "artifact_consistency_state": "m411_m412_artifacts_consistent",
        "data_basis": "raw_close_price_return",
        "raw_close_price_return_evidence_only": True,
        "evidence_scope": "signal_backtest_pipeline_only",
        "profit_claim": "none",
        "blockers": [],
        "submitted": False,
        "mutated": False,
        "submit_authorized": False,
        "submit_path_allowed": False,
        "paper_submit_approved": False,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "broker_action_performed": False,
        "broker_actions_performed": False,
        "broker_network_access": False,
        "credential_access": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "market_data_fetch_performed": False,
        "live_authorized": False,
    }


def _write_adjusted_csv(path: Path) -> Path:
    return _write_text(
        path,
        (
            "date,close,adjusted_close,volume\n"
            "2020-01-02,100.00,99.50,1000\n"
            "2020-01-03,101.00,100.75,1100\n"
        ),
    )


def _write_manifest(
    path: Path,
    csv_path: Path,
    *,
    expected_input_sha256: str | None = None,
    data_basis: str = "adjusted_close_price_return",
    source_notes: str = "operator supplied adjusted close evidence",
) -> Path:
    manifest = {
        "symbol": "SPY",
        "input_csv": str(csv_path),
        "expected_input_sha256": (
            _sha256_file(csv_path)
            if expected_input_sha256 is None
            else expected_input_sha256
        ),
        "data_basis": data_basis,
        "adjustment_policy": "vendor adjusted close policy documented by operator",
        "source_notes": source_notes,
        "operator_attested": True,
        "attested_by": "operator",
        "attested_at": "2026-06-06",
        "timeframe": "daily",
        "contains_synthetic_data": False,
        "contains_fixture_data": False,
        "contains_sample_data": False,
        "contains_test_data": False,
        "total_return_claim": "none",
    }
    path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return path


def _write_jsonl(path: Path, *records: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record, sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")
    return path


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _adjusted_close_gate_parser():
    parser = cli_module.build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", {}) or {}
        if _COMMAND in choices:
            return choices[_COMMAND]
    raise AssertionError("etf-sma-adjusted-close-evidence-gate parser not found")


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
