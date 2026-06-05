from __future__ import annotations

import ast
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import socket

import algotrader.cli as cli_module
import pytest
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_cycle_unified_preview import (
    EtfSmaCycleUnifiedPreviewConfig,
    build_etf_sma_cycle_unified_preview,
)
from algotrader.execution.etf_sma_local_bars_cycle_proof import (
    EtfSmaLocalBarsCycleProofConfig,
    build_etf_sma_local_bars_cycle_proof,
    write_etf_sma_local_bars_cycle_proof_jsonl,
)
from algotrader.research.local_daily_bars import (
    LOCAL_DAILY_BARS_CSV_COLUMNS,
    load_local_daily_bars_csv,
)
from algotrader.research.local_daily_bars_checkpoint import (
    LocalDailyBarsCheckpointConfig,
    build_local_daily_bars_checkpoint,
)


MODULE_PATH = Path("src/algotrader/execution/etf_sma_local_bars_cycle_proof.py")
AS_OF = "2026-06-05"
AS_OF_DATE = date.fromisoformat(AS_OF)
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


def test_199_bar_input_writes_proof_and_insufficient_history_chain(
    tmp_path,
) -> None:  # noqa: ANN001
    input_csv = _write_daily_bars_csv(
        tmp_path / "operator_spy_199.csv",
        _daily_rows(199),
    )
    canonical_csv = tmp_path / "canonical" / "spy_daily_bars.csv"
    run_log = tmp_path / "m401_199.jsonl"

    payload = build_etf_sma_local_bars_cycle_proof(
        _config(input_csv, canonical_csv=canonical_csv, run_log=run_log)
    )
    result = write_etf_sma_local_bars_cycle_proof_jsonl(payload, run_log)
    records = _read_jsonl(run_log)

    assert result.record_count == 1
    assert records == [payload]
    assert run_log.read_text(encoding="utf-8").count("\n") == 1
    assert canonical_csv.is_file()
    assert payload["record_type"] == "local_bars_etf_sma_cycle_proof"
    assert payload["command"] == "local-bars-etf-sma-cycle-proof"
    assert payload["run_id"] == "unit_m401_local_bars_cycle_proof"
    assert payload["symbol"] == "SPY"
    assert payload["as_of"] == AS_OF
    assert payload["input_csv"] == str(input_csv)
    assert payload["canonical_csv"] == str(canonical_csv)
    assert payload["input_sha256"] == _sha256(input_csv)
    assert payload["canonical_sha256"] == _sha256(canonical_csv)
    assert payload["intake_status"] == "canonicalized"
    assert payload["checkpoint_status"] == "insufficient_history"
    assert payload["cycle_status"] == "insufficient_history"
    assert payload["required_usable_bars"] == 200
    assert payload["usable_bar_count"] == 199
    assert payload["missing_usable_bars"] == 1
    assert payload["readiness_state"] == "insufficient_history"
    assert payload["readiness_reason"] == "sma_insufficient_history"
    assert payload["cycle_decision"] == "insufficient_history"
    assert payload["cycle_decision_reason"] == "sma_insufficient_history"
    assert payload["cycle_next_allowed_action"] == (
        "offline_research_or_operator_review_only"
    )
    assert payload["blockers"] == ["missing_usable_bars"]
    assert load_local_daily_bars_csv(
        canonical_csv,
        symbol="SPY",
        as_of=AS_OF,
    ).observed_usable_bars == 199
    _assert_artifacts_exist(payload)
    _assert_safety_booleans_false(payload)


def test_200_bar_input_writes_ready_proof_with_real_cycle_decision(
    tmp_path,
) -> None:  # noqa: ANN001
    input_csv = _write_daily_bars_csv(
        tmp_path / "operator_spy_200.csv",
        _daily_rows(200),
    )
    canonical_csv = tmp_path / "canonical" / "spy_daily_bars.csv"
    run_log = tmp_path / "m401_200.jsonl"

    payload = build_etf_sma_local_bars_cycle_proof(
        _config(input_csv, canonical_csv=canonical_csv, run_log=run_log)
    )
    write_etf_sma_local_bars_cycle_proof_jsonl(payload, run_log)

    assert _read_jsonl(run_log) == [payload]
    assert run_log.read_text(encoding="utf-8").count("\n") == 1
    assert payload["input_sha256"] == _sha256(input_csv)
    assert payload["canonical_sha256"] == _sha256(canonical_csv)
    assert payload["checkpoint_status"] == "ready"
    assert payload["cycle_status"] == "ready"
    assert payload["required_usable_bars"] == 200
    assert payload["usable_bar_count"] == 200
    assert payload["missing_usable_bars"] == 0
    assert payload["readiness_state"] == "ready"
    assert payload["readiness_reason"] == "sma_usable_bars_ready"
    assert payload["cycle_decision"] == "buy_preview"
    assert payload["cycle_decision_reason"] == "risk_on_no_position"
    assert payload["blockers"] == []
    assert payload["cycle_summary"]["source_record_type"] == "local_daily_bars_csv"
    _assert_artifacts_exist(payload)
    _assert_safety_booleans_false(payload)


def test_canonical_output_is_accepted_by_m399_checkpoint_and_m398_cycle(
    tmp_path,
) -> None:  # noqa: ANN001
    input_csv = _write_daily_bars_csv(
        tmp_path / "operator_spy_200.csv",
        _daily_rows(200),
    )
    canonical_csv = tmp_path / "spy_daily_bars.csv"
    run_log = tmp_path / "m401_chain.jsonl"

    payload = build_etf_sma_local_bars_cycle_proof(
        _config(input_csv, canonical_csv=canonical_csv, run_log=run_log)
    )
    artifacts = payload["artifact_paths"]
    checkpoint = build_local_daily_bars_checkpoint(
        LocalDailyBarsCheckpointConfig(
            run_id="unit_m399_local_daily_bars_checkpoint",
            symbol="SPY",
            daily_bars_csv=canonical_csv,
            as_of=AS_OF,
        )
    )
    cycle = build_etf_sma_cycle_unified_preview(
        EtfSmaCycleUnifiedPreviewConfig(
            run_id="unit_m398_cycle",
            symbol="SPY",
            generated_at="2026-06-05T00:00:00+00:00",
            order_reconciliation_log=artifacts["order_reconciliation_log"],
            daily_bars_csv=canonical_csv,
        )
    )

    assert checkpoint["record_type"] == "local_daily_bars_checkpoint"
    assert checkpoint["usable_bar_count"] == 200
    assert checkpoint["readiness_state"] == "ready"
    assert cycle["record_type"] == "etf_sma_cycle_unified_preview"
    assert cycle["data_readiness"]["observed_usable_bars"] == 200
    assert cycle["data_readiness"]["readiness_state"] == "ready"
    assert cycle["data_readiness"]["source_record_type"] == "local_daily_bars_csv"
    _assert_safety_booleans_false(payload)


def test_invalid_input_fails_closed_without_proof_or_artifacts(
    tmp_path,
) -> None:  # noqa: ANN001
    input_csv = tmp_path / "operator_invalid.csv"
    input_csv.write_text(
        "symbol,date,open,high,low,close,volume\n"
        "SPY,2026-06-04,100,101,99,100,1000\n",
        encoding="utf-8",
    )
    canonical_csv = tmp_path / "spy_daily_bars.csv"
    run_log = tmp_path / "m401_invalid.jsonl"

    with pytest.raises(ValidationError, match="adjusted_close"):
        build_etf_sma_local_bars_cycle_proof(
            _config(input_csv, canonical_csv=canonical_csv, run_log=run_log)
        )

    assert not canonical_csv.exists()
    assert not run_log.exists()
    assert all(not path.exists() for path in _expected_artifact_paths(run_log))


def test_duplicate_requested_symbol_dates_fail_closed(tmp_path) -> None:  # noqa: ANN001
    input_csv = _write_daily_bars_csv(
        tmp_path / "operator_duplicate_spy.csv",
        [
            _row("SPY", "2026-06-04", 100),
            _row("SPY", "2026-06-04", 101),
        ],
    )
    canonical_csv = tmp_path / "spy_daily_bars.csv"
    run_log = tmp_path / "m401_duplicate.jsonl"

    with pytest.raises(ValidationError, match="duplicates date 2026-06-04"):
        build_etf_sma_local_bars_cycle_proof(
            _config(input_csv, canonical_csv=canonical_csv, run_log=run_log)
        )

    assert not canonical_csv.exists()
    assert not run_log.exists()
    assert all(not path.exists() for path in _expected_artifact_paths(run_log))


def test_future_dated_bars_are_excluded_through_chain(tmp_path) -> None:  # noqa: ANN001
    input_csv = _write_daily_bars_csv(
        tmp_path / "operator_spy_with_future.csv",
        [
            *_daily_rows(200),
            _row("SPY", "2026-06-06", 400),
        ],
    )
    canonical_csv = tmp_path / "spy_daily_bars.csv"
    run_log = tmp_path / "m401_future.jsonl"

    payload = build_etf_sma_local_bars_cycle_proof(
        _config(input_csv, canonical_csv=canonical_csv, run_log=run_log)
    )
    rows = _read_csv_rows(canonical_csv)

    assert payload["usable_bar_count"] == 200
    assert payload["missing_usable_bars"] == 0
    assert payload["future_bar_count_excluded"] == 1
    assert payload["intake_future_bar_count_excluded"] == 1
    assert payload["checkpoint_future_bar_count_excluded"] == 0
    assert payload["cycle_future_bar_count_excluded"] == 0
    assert rows[-1][1] == AS_OF
    assert "2026-06-06" not in [row[1] for row in rows[1:]]
    assert payload["cycle_summary"]["observed_usable_bars"] == 200
    _assert_safety_booleans_false(payload)


def test_cli_local_bars_cycle_proof_smoke_avoids_runtime_config_broker_and_network(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:  # noqa: ANN001
    for name in SCRUBBED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    def forbidden_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("local-bars proof must not load runtime config")

    def forbidden_broker(*args: object, **kwargs: object) -> object:
        raise AssertionError("local-bars proof must not build a broker")

    def forbidden_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("local-bars proof must not open sockets")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)
    monkeypatch.setattr(socket, "socket", forbidden_socket)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    input_csv = _write_daily_bars_csv(
        tmp_path / "operator_spy_200.csv",
        _daily_rows(200),
    )
    canonical_csv = tmp_path / "canonical" / "spy_daily_bars.csv"
    run_log = tmp_path / "m401_cli.jsonl"

    exit_code = cli_module.main(
        (
            "local-bars-etf-sma-cycle-proof",
            "--symbol",
            "SPY",
            "--input-csv",
            str(input_csv),
            "--canonical-csv",
            str(canonical_csv),
            "--as-of",
            AS_OF,
            "--run-id",
            "unit_m401_local_bars_cycle_proof",
            "--run-log",
            str(run_log),
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
    assert canonical_csv.is_file()
    assert payload["record_type"] == "local_bars_etf_sma_cycle_proof"
    assert payload["readiness_state"] == "ready"
    assert payload["usable_bar_count"] == 200
    assert payload["cycle_decision"] == "buy_preview"
    _assert_artifacts_exist(payload)
    _assert_safety_booleans_false(payload)


def test_local_bars_cycle_proof_parser_registration() -> None:
    parser = _local_bars_cycle_proof_parser()
    options = {
        action.dest: action
        for action in parser._actions
        if getattr(action, "option_strings", ())
    }

    assert options["symbol"].required is False
    assert options["input_csv"].required is True
    assert options["canonical_csv"].required is True
    assert options["as_of"].required is True
    assert options["run_id"].required is True
    assert options["run_log"].required is True


def test_proof_module_imports_no_broker_sdk_credentials_network_or_mutation_calls() -> None:
    imports = _import_references(MODULE_PATH)

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names(MODULE_PATH).isdisjoint(FORBIDDEN_CALL_NAMES)


def _config(
    input_csv: Path,
    *,
    canonical_csv: Path,
    run_log: Path,
    **overrides: object,
) -> EtfSmaLocalBarsCycleProofConfig:
    values = {
        "run_id": "unit_m401_local_bars_cycle_proof",
        "symbol": "SPY",
        "input_csv": input_csv,
        "canonical_csv": canonical_csv,
        "as_of": AS_OF,
        "run_log": run_log,
    }
    values.update(overrides)
    return EtfSmaLocalBarsCycleProofConfig(**values)


def _write_daily_bars_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(LOCAL_DAILY_BARS_CSV_COLUMNS)]
    lines.extend(
        ",".join(row[column] for column in LOCAL_DAILY_BARS_CSV_COLUMNS)
        for row in rows
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _daily_rows(count: int) -> list[dict[str, str]]:
    first_day = AS_OF_DATE - timedelta(days=count - 1)
    return [
        _row("SPY", (first_day + timedelta(days=index)).isoformat(), 100 + index)
        for index in range(count)
    ]


def _row(symbol: str, day: str, price: int) -> dict[str, str]:
    parsed = date.fromisoformat(day)
    assert parsed.isoformat() == day
    return {
        "symbol": symbol,
        "date": day,
        "open": str(price),
        "high": str(price + 1),
        "low": str(price - 1),
        "close": str(price),
        "adjusted_close": str(price),
        "volume": "1000",
    }


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _read_csv_rows(path: Path) -> list[list[str]]:
    return [
        line.split(",")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_artifacts_exist(payload: dict[str, object]) -> None:
    artifacts = payload["artifact_paths"]
    assert set(artifacts) == {
        "intake_manifest_log",
        "checkpoint_log",
        "order_reconciliation_log",
        "cycle_log",
    }
    for path_text in artifacts.values():
        path = Path(str(path_text))
        assert path.is_file()
        assert path.read_text(encoding="utf-8").count("\n") == 1


def _assert_safety_booleans_false(payload: dict[str, object]) -> None:
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["broker_actions_performed"] is False
    assert payload["broker_mutation_allowed"] is False
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is False
    assert payload["live_authorized"] is False
    assert payload.get("not_live_authorized") is True
    assert payload["broker_action_flags"] == {
        "submit": False,
        "cancel": False,
        "replace": False,
        "close": False,
        "liquidate": False,
        "mutation": False,
    }
    safety = payload["safety_summary"]
    assert safety["submitted"] is False
    assert safety["mutated"] is False
    assert safety["network_access_attempted"] is False
    assert safety["credential_access_attempted"] is False
    assert safety["live_authorized"] is False


def _expected_artifact_paths(run_log: Path) -> tuple[Path, ...]:
    stem = run_log.stem
    return (
        run_log.parent / f"{stem}_intake_manifest.jsonl",
        run_log.parent / f"{stem}_local_daily_bars_checkpoint.jsonl",
        run_log.parent / f"{stem}_order_reconciliation.jsonl",
        run_log.parent / f"{stem}_etf_sma_cycle.jsonl",
    )


def _local_bars_cycle_proof_parser():
    parser = cli_module.build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", {}) or {}
        if "local-bars-etf-sma-cycle-proof" in choices:
            return choices["local-bars-etf-sma-cycle-proof"]
    raise AssertionError("local-bars-etf-sma-cycle-proof parser not found")


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
