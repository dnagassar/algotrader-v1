from __future__ import annotations

import ast
from copy import deepcopy
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import socket

import pytest

import algotrader.cli as cli_module
from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_local_bars_cycle_proof import (
    EtfSmaLocalBarsCycleProofConfig,
    build_etf_sma_local_bars_cycle_proof,
    write_etf_sma_local_bars_cycle_proof_jsonl,
)
from algotrader.execution.etf_sma_paper_lab_review_packet import (
    EtfSmaPaperLabReviewPacketConfig,
    build_etf_sma_paper_lab_review_packet,
    write_etf_sma_paper_lab_review_packet_jsonl,
)
from algotrader.research.local_daily_bars import LOCAL_DAILY_BARS_CSV_COLUMNS


MODULE_PATH = Path("src/algotrader/execution/etf_sma_paper_lab_review_packet.py")
AS_OF = "2026-06-05"
AS_OF_DATE = date.fromisoformat(AS_OF)
GENERATED_AT = "2026-06-05T00:00:00+00:00"
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
    "ExecutionIntent",
    "ExecutionPlan",
    "cancel_order",
    "close_all_positions",
    "close_position",
    "connect",
    "create_connection",
    "create_order",
    "download",
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


def test_200_bar_ready_buy_preview_produces_ready_for_operator_review(
    tmp_path,
) -> None:  # noqa: ANN001
    proof_log, proof, input_csv, canonical_csv = _write_m401_proof(tmp_path, 200)
    run_log = tmp_path / "m402_200.jsonl"

    payload = build_etf_sma_paper_lab_review_packet(
        _config(proof_log, run_log=run_log)
    )
    result = write_etf_sma_paper_lab_review_packet_jsonl(payload, run_log)
    records = _read_jsonl(run_log)

    assert result.record_count == 1
    assert records == [payload]
    assert run_log.read_text(encoding="utf-8").count("\n") == 1
    assert payload["record_type"] == "etf_sma_paper_lab_review_packet"
    assert payload["command"] == "etf-sma-paper-lab-review-packet"
    assert payload["run_id"] == "unit_m402_paper_lab_review_packet"
    assert payload["symbol"] == "SPY"
    assert payload["generated_at"] == GENERATED_AT
    assert payload["source_proof_run_id"] == proof["run_id"]
    assert payload["source_proof_log"] == str(proof_log)
    assert payload["input_sha256"] == _sha256(input_csv)
    assert payload["canonical_sha256"] == _sha256(canonical_csv)
    assert payload["input_sha256"] == proof["input_sha256"]
    assert payload["canonical_sha256"] == proof["canonical_sha256"]
    assert payload["required_usable_bars"] == 200
    assert payload["usable_bar_count"] == 200
    assert payload["missing_usable_bars"] == 0
    assert payload["readiness_state"] == "ready"
    assert payload["readiness_reason"] == "sma_usable_bars_ready"
    assert payload["cycle_decision"] == "buy_preview"
    assert payload["cycle_decision_reason"] == "risk_on_no_position"
    assert payload["cycle_next_allowed_action"] == (
        "offline_research_or_operator_review_only"
    )
    assert payload["review_state"] == "ready_for_operator_review"
    assert payload["review_reason"] == (
        "m401_local_bars_proof_ready_buy_preview_operator_review_only"
    )
    assert payload["blockers"] == []
    assert payload["operator_handoff"]["recommended_next_action"] == (
        "operator_may_run_separate_read_only_paper_snapshot_reconciliation_"
        "before_any_paper_submit"
    )
    assert payload["operator_handoff"][
        "separate_read_only_paper_snapshot_reconciliation_required"
    ] is True
    assert payload["evidence_summary"]["offline_evidence_source"] == (
        "m401_local_bars_etf_sma_cycle_proof"
    )
    _assert_safety_booleans_false(payload)


def test_199_bar_insufficient_history_blocks_review_packet(tmp_path) -> None:  # noqa: ANN001
    proof_log, proof, _, _ = _write_m401_proof(tmp_path, 199)
    run_log = tmp_path / "m402_199.jsonl"

    payload = build_etf_sma_paper_lab_review_packet(
        _config(proof_log, run_log=run_log)
    )
    write_etf_sma_paper_lab_review_packet_jsonl(payload, run_log)

    assert _read_jsonl(run_log) == [payload]
    assert payload["source_proof_run_id"] == proof["run_id"]
    assert payload["required_usable_bars"] == 200
    assert payload["usable_bar_count"] == 199
    assert payload["missing_usable_bars"] == 1
    assert payload["readiness_state"] == "insufficient_history"
    assert payload["readiness_reason"] == "sma_insufficient_history"
    assert payload["cycle_decision"] == "insufficient_history"
    assert payload["cycle_decision_reason"] == "sma_insufficient_history"
    assert payload["review_state"] == "blocked_insufficient_history"
    assert payload["operator_handoff"]["recommended_next_action"] == (
        "refresh_or_import_more_local_bars_offline"
    )
    assert "missing_usable_bars" in payload["blockers"]
    _assert_safety_booleans_false(payload)


@pytest.mark.parametrize(
    ("field_name", "expected_blocker"),
    (
        ("submitted", "source_submitted_true"),
        ("mutated", "source_mutated_true"),
        ("live_authorized", "source_live_authorized_true"),
        ("network_access_attempted", "source_network_access_attempted_true"),
        ("credential_access_attempted", "source_credential_access_attempted_true"),
    ),
)
def test_source_safety_flags_block_or_fail_closed(
    tmp_path,
    field_name: str,
    expected_blocker: str,
) -> None:  # noqa: ANN001
    proof_log, proof, _, _ = _write_m401_proof(tmp_path, 200)
    unsafe = deepcopy(proof)
    unsafe[field_name] = True
    _write_jsonl(proof_log, unsafe)

    payload = build_etf_sma_paper_lab_review_packet(
        _config(proof_log, run_log=tmp_path / f"m402_{field_name}.jsonl")
    )

    assert payload["review_state"] == "blocked_safety_violation"
    assert expected_blocker in payload["blockers"]
    assert payload["operator_handoff"]["recommended_next_action"] == (
        "stop_and_rebuild_m401_proof_with_false_safety_flags_before_review"
    )
    _assert_safety_booleans_false(payload)


def test_source_broker_action_flag_blocks_review_packet(tmp_path) -> None:  # noqa: ANN001
    proof_log, proof, _, _ = _write_m401_proof(tmp_path, 200)
    unsafe = deepcopy(proof)
    unsafe["broker_action_flags"]["submit"] = True
    _write_jsonl(proof_log, unsafe)

    payload = build_etf_sma_paper_lab_review_packet(
        _config(proof_log, run_log=tmp_path / "m402_submit_flag.jsonl")
    )

    assert payload["review_state"] == "blocked_safety_violation"
    assert "source_broker_action_flag_submit_true" in payload["blockers"]
    _assert_safety_booleans_false(payload)


def test_non_spy_symbol_blocks_review_packet(tmp_path) -> None:  # noqa: ANN001
    proof_log, proof, _, _ = _write_m401_proof(tmp_path, 200)
    unsafe = deepcopy(proof)
    unsafe["symbol"] = "QQQ"
    _write_jsonl(proof_log, unsafe)

    payload = build_etf_sma_paper_lab_review_packet(
        EtfSmaPaperLabReviewPacketConfig(
            run_id="unit_m402_paper_lab_review_packet",
            symbol="QQQ",
            proof_log=proof_log,
            run_log=tmp_path / "m402_qqq.jsonl",
            generated_at=GENERATED_AT,
        )
    )

    assert payload["symbol"] == "QQQ"
    assert payload["source_proof_symbol"] == "QQQ"
    assert payload["review_state"] == "blocked_symbol_not_allowed"
    assert "symbol_not_spy" in payload["blockers"]
    assert "source_symbol_not_spy" in payload["blockers"]
    assert payload["operator_handoff"]["recommended_next_action"] == (
        "use_spy_only_current_allowlist"
    )
    _assert_safety_booleans_false(payload)


def test_missing_proof_log_fails_closed_without_packet(tmp_path) -> None:  # noqa: ANN001
    missing_log = tmp_path / "missing_m401.jsonl"
    run_log = tmp_path / "m402_missing.jsonl"

    with pytest.raises(ValidationError, match="existing JSONL"):
        EtfSmaPaperLabReviewPacketConfig(
            run_id="unit_m402_paper_lab_review_packet",
            symbol="SPY",
            proof_log=missing_log,
            run_log=run_log,
            generated_at=GENERATED_AT,
        )

    assert not run_log.exists()


def test_invalid_proof_log_fails_closed_without_packet(tmp_path) -> None:  # noqa: ANN001
    proof_log = tmp_path / "invalid_m401.jsonl"
    proof_log.write_text("{not-json}\n", encoding="utf-8")
    run_log = tmp_path / "m402_invalid.jsonl"

    with pytest.raises(ValidationError, match="invalid JSON"):
        build_etf_sma_paper_lab_review_packet(_config(proof_log, run_log=run_log))

    assert not run_log.exists()


def test_latest_proof_record_is_used_and_exactly_one_packet_is_written(
    tmp_path,
) -> None:  # noqa: ANN001
    proof_log, ready_proof, _, _ = _write_m401_proof(tmp_path, 200)
    first = deepcopy(ready_proof)
    first["run_id"] = "older_insufficient_history_proof"
    first["readiness_state"] = "insufficient_history"
    first["cycle_decision"] = "insufficient_history"
    first["usable_bar_count"] = 199
    first["missing_usable_bars"] = 1
    first["blockers"] = ["missing_usable_bars"]
    _write_jsonl(proof_log, first, ready_proof)
    run_log = tmp_path / "m402_latest.jsonl"

    payload = build_etf_sma_paper_lab_review_packet(
        _config(proof_log, run_log=run_log)
    )
    write_etf_sma_paper_lab_review_packet_jsonl(payload, run_log)

    assert payload["source_proof_run_id"] == ready_proof["run_id"]
    assert payload["source_proof_record_count"] == 2
    assert payload["source_proof_record_line"] == 2
    assert payload["review_state"] == "ready_for_operator_review"
    assert len(_read_jsonl(run_log)) == 1
    assert run_log.read_text(encoding="utf-8").count("\n") == 1
    _assert_safety_booleans_false(payload)


def test_cli_review_packet_smoke_avoids_runtime_config_broker_and_network(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:  # noqa: ANN001
    for name in SCRUBBED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    def forbidden_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("review packet must not load runtime config")

    def forbidden_broker(*args: object, **kwargs: object) -> object:
        raise AssertionError("review packet must not build a broker")

    def forbidden_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("review packet must not open sockets")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)
    monkeypatch.setattr(socket, "socket", forbidden_socket)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    proof_log, _, _, _ = _write_m401_proof(tmp_path, 200)
    run_log = tmp_path / "m402_cli.jsonl"

    exit_code = cli_module.main(
        (
            "etf-sma-paper-lab-review-packet",
            "--symbol",
            "SPY",
            "--proof-log",
            str(proof_log),
            "--run-id",
            "unit_m402_paper_lab_review_packet",
            "--run-log",
            str(run_log),
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
    assert payload["record_type"] == "etf_sma_paper_lab_review_packet"
    assert payload["review_state"] == "ready_for_operator_review"
    _assert_safety_booleans_false(payload)


def test_review_packet_parser_registration() -> None:
    parser = _review_packet_parser()
    options = {
        action.dest: action
        for action in parser._actions
        if getattr(action, "option_strings", ())
    }

    assert options["symbol"].required is False
    assert options["proof_log"].required is True
    assert options["run_id"].required is True
    assert options["run_log"].required is True
    assert options["generated_at"].required is True


def test_review_packet_module_imports_no_broker_sdk_credentials_network_or_mutation_calls() -> None:
    imports = _import_references(MODULE_PATH)

    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names(MODULE_PATH).isdisjoint(FORBIDDEN_CALL_NAMES)


def _config(
    proof_log: Path,
    *,
    run_log: Path,
    **overrides: object,
) -> EtfSmaPaperLabReviewPacketConfig:
    values = {
        "run_id": "unit_m402_paper_lab_review_packet",
        "symbol": "SPY",
        "proof_log": proof_log,
        "run_log": run_log,
        "generated_at": GENERATED_AT,
    }
    values.update(overrides)
    return EtfSmaPaperLabReviewPacketConfig(**values)


def _write_m401_proof(
    tmp_path: Path,
    bar_count: int,
) -> tuple[Path, dict[str, object], Path, Path]:
    input_csv = _write_daily_bars_csv(
        tmp_path / f"operator_spy_{bar_count}.csv",
        _daily_rows(bar_count),
    )
    canonical_csv = tmp_path / f"canonical_{bar_count}" / "spy_daily_bars.csv"
    run_log = tmp_path / f"m401_{bar_count}.jsonl"

    payload = build_etf_sma_local_bars_cycle_proof(
        EtfSmaLocalBarsCycleProofConfig(
            run_id=f"unit_m401_local_bars_cycle_proof_{bar_count}",
            symbol="SPY",
            input_csv=input_csv,
            canonical_csv=canonical_csv,
            as_of=AS_OF,
            run_log=run_log,
        )
    )
    write_etf_sma_local_bars_cycle_proof_jsonl(payload, run_log)
    return run_log, payload, input_csv, canonical_csv


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


def _write_jsonl(path: Path, *records: dict[str, object]) -> None:
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_safety_booleans_false(payload: dict[str, object]) -> None:
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
    handoff = payload["operator_handoff"]
    assert handoff["paper_execution_authorized"] is False
    assert handoff["submit_authorized"] is False
    assert handoff["broker_mutation_authorized"] is False
    assert handoff["submitted"] is False
    assert handoff["mutated"] is False
    assert handoff["live_authorized"] is False


def _review_packet_parser():
    parser = cli_module.build_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", {}) or {}
        if "etf-sma-paper-lab-review-packet" in choices:
            return choices["etf-sma-paper-lab-review-packet"]
    raise AssertionError("etf-sma-paper-lab-review-packet parser not found")


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
