from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
import subprocess

from algotrader.orchestration.crypto_paper_fill_exit_ingestion import (
    CERTIFICATION_STATUS_BLOCKED,
    CERTIFICATION_STATUS_CERTIFIED_FILL_EXIT_FLAT,
    READ_ONLY_RECONCILIATION_REQUIRED,
    REQUIRED_LABELS,
    run_crypto_paper_fill_exit_ingestion,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT
    / "src"
    / "algotrader"
    / "orchestration"
    / "crypto_paper_fill_exit_ingestion.py"
)
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_crypto_paper_fill_exit_ingestion.ps1"
AS_OF = "2026-07-05T23:35:25.720683+00:00"
ENTRY_CLIENT_ORDER_ID = "v510-btcusd-entry-31147aa0135b0e92"
EXIT_CLIENT_ORDER_ID = "v510-btcusd-exit-a32677e4399a7c86"


def test_successful_filled_exit_confirmed_ingests_as_certified_fill_exit_flat(
    tmp_path: Path,
) -> None:
    result = _run_ingestion(tmp_path)

    assert result["certification_status"] == CERTIFICATION_STATUS_CERTIFIED_FILL_EXIT_FLAT
    assert result["certified_scope"] == "BTCUSD bounded paper entry/exit only"
    assert result["symbol"] == "BTCUSD"
    assert result["approved_max_notional"] == "25"
    assert result["prior_entry_client_order_id"] == ENTRY_CLIENT_ORDER_ID
    assert result["prior_exit_client_order_id"] == EXIT_CLIENT_ORDER_ID
    assert result["prior_entry_attempt_count"] == "1"
    assert result["prior_exit_attempt_count"] == "1"
    assert result["prior_entry_final_status"] == "filled"
    assert result["prior_exit_final_status"] == "filled"
    assert result["prior_entry_filled_qty"] == "0.00038542"
    assert result["prior_exit_filled_qty"] == "0.000384456"
    assert result["prior_residual_position_status"] == (
        "flat_or_no_BTCUSD_position_observed"
    )
    assert result["blockers"] == []
    assert result["live_authorized"] is False
    assert result["autonomous_submit_authorized"] is False
    assert result["broker_mutation_authorized_by_this_packet"] is False
    assert result["broker_read_performed_current_run"] is False
    assert result["broker_mutation_performed_current_run"] is False
    assert result["paper_submit_performed_current_run"] is False

    request = result["read_only_reconciliation_request"]
    assert request["read_only_reconciliation_status"] == READ_ONLY_RECONCILIATION_REQUIRED
    assert request["requested_scope"] == "BTCUSD paper read-only flat reconciliation"
    assert request["symbol"] == "BTCUSD"
    assert request["broker_read_performed_current_run"] is False
    assert request["broker_mutation_authorized_by_this_packet"] is False
    assert request["paper_submit_authorized"] is False
    assert "no_open_BTCUSD_orders" in request["required_checks"]
    assert "no_residual_BTCUSD_position" in request["required_checks"]

    artifact_paths = result["artifact_paths"]
    assert set(artifact_paths) == {
        "fill_exit_ingestion_json",
        "fill_exit_ingestion_md",
        "read_only_reconciliation_request_json",
        "operating_record",
        "manifest",
    }
    payload = json.loads(
        Path(artifact_paths["fill_exit_ingestion_json"]).read_text(encoding="utf-8")
    )
    manifest = json.loads(Path(artifact_paths["manifest"]).read_text(encoding="utf-8"))
    operating_record = json.loads(
        Path(artifact_paths["operating_record"]).read_text(encoding="utf-8")
    )
    assert payload["certification_status"] == CERTIFICATION_STATUS_CERTIFIED_FILL_EXIT_FLAT
    assert manifest["generated_under_runs"] is True
    assert operating_record["prior_entry_client_order_id"] == ENTRY_CLIENT_ORDER_ID
    assert operating_record["cycle_decision"] == "flat_reconciliation_request"
    assert set(REQUIRED_LABELS).issubset(payload["labels"])


def test_missing_certification_result_blocks_ingestion(tmp_path: Path) -> None:
    result = run_crypto_paper_fill_exit_ingestion(
        certification_result_path=tmp_path / "missing.json",
        output_root=tmp_path
        / "runs"
        / "crypto_paper_fill_exit_ingestion"
        / "latest",
        write_artifacts=True,
    )

    assert result["certification_status"] == CERTIFICATION_STATUS_BLOCKED
    assert "fill_exit_certification_result_missing" in result["blockers"]
    assert (
        result["read_only_reconciliation_request"]["read_only_reconciliation_status"]
        == "blocked_certification_not_ready"
    )


def test_entry_attempt_count_not_one_blocks(tmp_path: Path) -> None:
    result = _run_ingestion(tmp_path, {"entry_attempt_count": 2})

    assert result["certification_status"] == CERTIFICATION_STATUS_BLOCKED
    assert "entry_attempt_count_not_1" in result["blockers"]


def test_exit_attempt_count_not_one_blocks(tmp_path: Path) -> None:
    result = _run_ingestion(tmp_path, {"exit_attempt_count": 0})

    assert result["certification_status"] == CERTIFICATION_STATUS_BLOCKED
    assert "exit_attempt_count_not_1" in result["blockers"]


def test_entry_status_not_filled_blocks(tmp_path: Path) -> None:
    result = _run_ingestion(tmp_path, {"entry_final_status": "canceled"})

    assert result["certification_status"] == CERTIFICATION_STATUS_BLOCKED
    assert "entry_final_status_not_filled" in result["blockers"]


def test_exit_status_not_filled_blocks(tmp_path: Path) -> None:
    result = _run_ingestion(tmp_path, {"exit_final_status": "rejected"})

    assert result["certification_status"] == CERTIFICATION_STATUS_BLOCKED
    assert "exit_final_status_not_filled" in result["blockers"]


def test_residual_btcusd_position_blocks_flat_certification(tmp_path: Path) -> None:
    payload = _fill_exit_result()
    payload["final_position"] = {
        "symbol": "BTCUSD",
        "qty": "0.000000001",
        "side": "long",
    }

    result = _run_ingestion(tmp_path, payload=payload)

    assert result["certification_status"] == CERTIFICATION_STATUS_BLOCKED
    assert "residual_BTCUSD_position_observed" in result["blockers"]


def test_residual_status_not_flat_blocks(tmp_path: Path) -> None:
    result = _run_ingestion(
        tmp_path,
        {"residual_position_status": "residual_BTCUSD_position_observed"},
    )

    assert result["certification_status"] == CERTIFICATION_STATUS_BLOCKED
    assert "residual_position_status_not_flat_or_no_BTCUSD_position" in result["blockers"]


def test_live_endpoint_touched_true_blocks(tmp_path: Path) -> None:
    result = _run_ingestion(tmp_path, {"live_endpoint_touched": True})

    assert result["certification_status"] == CERTIFICATION_STATUS_BLOCKED
    assert "live_endpoint_touched_true" in result["blockers"]


def test_credential_values_exposed_true_blocks(tmp_path: Path) -> None:
    result = _run_ingestion(tmp_path, {"credential_values_exposed": True})

    assert result["certification_status"] == CERTIFICATION_STATUS_BLOCKED
    assert "credential_values_exposed_true" in result["blockers"]


def test_non_btcusd_symbol_blocks(tmp_path: Path) -> None:
    result = _run_ingestion(tmp_path, {"symbol": "ETHUSD"})

    assert result["certification_status"] == CERTIFICATION_STATUS_BLOCKED
    assert "symbol_not_BTCUSD" in result["blockers"]


def test_max_notional_above_25_blocks(tmp_path: Path) -> None:
    result = _run_ingestion(tmp_path, {"approved_max_notional": "25.000001"})

    assert result["certification_status"] == CERTIFICATION_STATUS_BLOCKED
    assert "approved_max_notional_exceeds_25" in result["blockers"]


def test_read_only_reconciliation_request_does_not_authorize_mutation(
    tmp_path: Path,
) -> None:
    result = _run_ingestion(tmp_path)
    request = result["read_only_reconciliation_request"]

    assert request["broker_read_authorized_by_this_packet"] is False
    assert request["broker_mutation_authorized_by_this_packet"] is False
    assert request["paper_submit_authorized"] is False
    assert request["paper_entry_authorized"] is False
    assert request["paper_exit_authorized"] is False
    assert request["no_submit_mode"] is True
    assert request["paper_shell_credentials_required_for_actual_read"] is True
    assert request["credential_values_required_in_artifact"] is False
    assert request["broker_read_performed_current_run"] is False
    assert request["broker_mutation_performed_current_run"] is False
    assert request["paper_submit_performed_current_run"] is False
    assert request["paper_cancel_performed_current_run"] is False
    assert request["paper_replace_performed_current_run"] is False
    assert request["paper_close_performed_current_run"] is False
    assert request["paper_liquidate_performed_current_run"] is False
    for action in ("submit", "cancel", "replace", "close", "liquidate", "retry"):
        assert action in request["forbidden_actions"]
    assert "-Format text" in request["exact_operator_command"]


def test_generated_runs_artifacts_remain_untracked() -> None:
    result = subprocess.run(
        ["git", "ls-files", "runs"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert "runs/" in (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")


def test_normal_pytest_path_is_offline_broker_free_and_credential_free() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    forbidden_prefixes = (
        "alpaca",
        "alpaca_trade_api",
        "httpx",
        "requests",
        "socket",
        "urllib",
        "algotrader.execution",
    )
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    forbidden_calls = {
        "cancel_order",
        "close_position",
        "connect",
        "create_order",
        "delete",
        "liquidate",
        "replace_order",
        "request",
        "socket.socket",
        "submit_order",
        "urlopen",
    }
    source_text = MODULE_PATH.read_text(encoding="utf-8")

    assert not any(
        module == prefix or module.startswith(f"{prefix}.")
        for module in imported_modules
        for prefix in forbidden_prefixes
    )
    assert call_names.isdisjoint(forbidden_calls)
    assert "os.environ" not in source_text
    assert "getenv" not in source_text


def test_runner_prepares_only_and_never_authorizes_submit_or_mutation() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "$CertificationResultPath" in script
    assert "$OutputRoot" in script
    assert "algotrader.orchestration.crypto_paper_fill_exit_ingestion" in script
    assert "broker_read_performed_current_run=false" in script
    assert "broker_mutation_performed_current_run=false" in script
    assert "paper_submit_performed_current_run=false" in script
    assert "paper_cancel_performed_current_run=false" in script
    assert "paper_replace_performed_current_run=false" in script
    assert "paper_close_performed_current_run=false" in script
    assert "paper_liquidate_performed_current_run=false" in script
    assert "submit_order" not in script
    assert "cancel_order" not in script
    assert "replace_order" not in script
    assert "close_position" not in script
    assert "liquidate_order" not in script
    assert "delete_order" not in script


def _run_ingestion(
    tmp_path: Path,
    updates: dict[str, object] | None = None,
    *,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    source = payload or _fill_exit_result()
    if updates:
        source.update(updates)
    source_path = _write_fill_exit_result(tmp_path, source)
    return run_crypto_paper_fill_exit_ingestion(
        certification_result_path=source_path,
        output_root=tmp_path / "runs" / "crypto_paper_fill_exit_ingestion" / "latest",
        as_of="2026-07-06T00:00:00+00:00",
        write_artifacts=True,
    )


def _write_fill_exit_result(tmp_path: Path, payload: dict[str, object]) -> Path:
    source_path = (
        tmp_path
        / "runs"
        / "crypto_paper_fill_exit_certification"
        / "latest"
        / "fill_exit_certification_result.json"
    )
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return source_path


def _fill_exit_result() -> dict[str, object]:
    return copy.deepcopy(
        {
            "schema_version": "v5_10_crypto_paper_fill_exit_certification_v1",
            "as_of": AS_OF,
            "outcome_classification": "filled_exit_confirmed",
            "symbol": "BTCUSD",
            "approved_max_notional": "25",
            "entry_client_order_id": ENTRY_CLIENT_ORDER_ID,
            "exit_client_order_id": EXIT_CLIENT_ORDER_ID,
            "entry_attempt_count": 1,
            "exit_attempt_count": 1,
            "entry_final_status": "filled",
            "entry_filled_qty": "0.00038542",
            "entry_filled_avg_price": "63588.7",
            "position_after_entry": {
                "symbol": "BTCUSD",
                "qty": "0.000384456",
                "side": "long",
            },
            "exit_final_status": "filled",
            "exit_filled_qty": "0.000384456",
            "exit_filled_avg_price": "63575.36",
            "final_position": {},
            "residual_position_status": "flat_or_no_BTCUSD_position_observed",
            "broker_read_observed": True,
            "broker_mutation_performed": True,
            "paper_submit_performed": True,
            "live_endpoint_touched": False,
            "credential_values_exposed": False,
            "entry_final_order": {
                "client_order_id": ENTRY_CLIENT_ORDER_ID,
                "symbol": "BTCUSD",
                "status": "filled",
                "filled_qty": "0.00038542",
                "filled_avg_price": "63588.7",
            },
            "exit_final_order": {
                "client_order_id": EXIT_CLIENT_ORDER_ID,
                "symbol": "BTCUSD",
                "status": "filled",
                "filled_qty": "0.000384456",
                "filled_avg_price": "63575.36",
            },
        }
    )


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""
