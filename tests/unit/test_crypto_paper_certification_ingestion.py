from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
import subprocess

from algotrader.orchestration.crypto_paper_certification_ingestion import (
    APPROVAL_PACKET_STATUS_BLOCKED,
    APPROVAL_PACKET_STATUS_READY,
    APPROVAL_STATE_NOT_AUTHORIZED,
    CERTIFICATION_STATUS_BLOCKED,
    CERTIFICATION_STATUS_CERTIFIED_NO_FILL,
    CERTIFICATION_STATUS_PRIOR_FILL_OBSERVED,
    FUTURE_FILL_APPROVAL_PACKET_REQUESTED_SCOPE,
    REQUIRED_LABELS,
    run_crypto_paper_certification_ingestion,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT
    / "src"
    / "algotrader"
    / "orchestration"
    / "crypto_paper_certification_ingestion.py"
)
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_crypto_paper_certification_ingestion.ps1"
AS_OF = "2026-07-05T20:37:03.286956+00:00"
CLIENT_ORDER_ID = "v58-btcusd-paper-cert-bfa9caadd6b57b19"


def test_successful_submitted_cancel_confirmed_result_certifies_no_fill(
    tmp_path: Path,
) -> None:
    result = _run_ingestion(tmp_path)

    assert result["certification_status"] == CERTIFICATION_STATUS_CERTIFIED_NO_FILL
    assert result["certified_scope"] == "BTCUSD paper submit/cancel only"
    assert result["live_authorized"] is False
    assert result["autonomous_submit_authorized"] is False
    assert result["paper_fill_authorized"] is False
    assert result["broker_mutation_authorized_by_this_packet"] is False
    assert result["prior_client_order_id"] == CLIENT_ORDER_ID
    assert result["prior_final_order_status"] == "canceled"
    assert result["prior_filled_qty"] == "0"
    assert result["blockers"] == []

    packet = result["paper_fill_experiment_approval_packet"]
    assert packet["approval_packet_status"] == APPROVAL_PACKET_STATUS_READY
    assert packet["approval_state"] == APPROVAL_STATE_NOT_AUTHORIZED
    assert packet["requested_future_authorization_scope"] == (
        FUTURE_FILL_APPROVAL_PACKET_REQUESTED_SCOPE
    )
    assert packet["paper_submit_authorized"] is False
    assert packet["paper_fill_authorized"] is False
    assert packet["broker_mutation_authorized_by_this_packet"] is False

    artifact_paths = result["artifact_paths"]
    assert set(artifact_paths) == {
        "certification_ingestion_json",
        "certification_ingestion_md",
        "paper_fill_experiment_approval_packet_json",
        "paper_fill_experiment_approval_packet_md",
        "operating_record",
        "manifest",
    }
    payload = json.loads(
        Path(artifact_paths["certification_ingestion_json"]).read_text(
            encoding="utf-8"
        )
    )
    manifest = json.loads(Path(artifact_paths["manifest"]).read_text(encoding="utf-8"))
    operating_record = json.loads(
        Path(artifact_paths["operating_record"]).read_text(encoding="utf-8")
    )
    assert payload["certification_status"] == CERTIFICATION_STATUS_CERTIFIED_NO_FILL
    assert manifest["generated_under_runs"] is True
    assert operating_record["prior_client_order_id"] == CLIENT_ORDER_ID
    assert set(REQUIRED_LABELS).issubset(payload["labels"])


def test_missing_certification_result_blocks_ingestion(tmp_path: Path) -> None:
    result = run_crypto_paper_certification_ingestion(
        certification_result_path=tmp_path / "missing.json",
        output_root=tmp_path / "runs" / "crypto_paper_certification_ingestion" / "latest",
        write_artifacts=True,
    )

    assert result["certification_status"] == CERTIFICATION_STATUS_BLOCKED
    assert "certification_result_missing" in result["blockers"]
    assert (
        result["paper_fill_experiment_approval_packet"]["approval_packet_status"]
        == APPROVAL_PACKET_STATUS_BLOCKED
    )


def test_submit_attempt_count_not_one_blocks(tmp_path: Path) -> None:
    result = _run_ingestion(tmp_path, {"submit_attempt_count": 2})

    assert result["certification_status"] == CERTIFICATION_STATUS_BLOCKED
    assert "submit_attempt_count_not_1" in result["blockers"]


def test_cancel_attempt_count_not_one_blocks(tmp_path: Path) -> None:
    result = _run_ingestion(tmp_path, {"cancel_attempt_count": 0})

    assert result["certification_status"] == CERTIFICATION_STATUS_BLOCKED
    assert "cancel_attempt_count_not_1" in result["blockers"]


def test_final_order_status_not_canceled_blocks(tmp_path: Path) -> None:
    result = _run_ingestion(tmp_path, {"final_order_status": "new"})

    assert result["certification_status"] == CERTIFICATION_STATUS_BLOCKED
    assert "final_order_status_not_canceled" in result["blockers"]


def test_filled_qty_not_zero_changes_certification_classification(
    tmp_path: Path,
) -> None:
    payload = _certification_result()
    payload["reconciliation"]["filled_qty"] = "0.000000001"
    payload["final_order"]["filled_qty"] = "0.000000001"

    result = _run_ingestion(tmp_path, payload=payload)

    assert result["certification_status"] == CERTIFICATION_STATUS_PRIOR_FILL_OBSERVED
    assert result["certification_status"] != CERTIFICATION_STATUS_CERTIFIED_NO_FILL
    assert "filled_qty_not_zero" in result["blockers"]
    assert (
        result["paper_fill_experiment_approval_packet"]["approval_packet_status"]
        == APPROVAL_PACKET_STATUS_BLOCKED
    )


def test_residual_position_blocks_no_fill_certification(tmp_path: Path) -> None:
    payload = _certification_result()
    payload["reconciliation"]["residual_position"] = {
        "selected_symbol_position_observed": True,
        "selected_symbol_positions": [{"symbol": "BTCUSD", "qty": "0.000000001"}],
    }

    result = _run_ingestion(tmp_path, payload=payload)

    assert result["certification_status"] == CERTIFICATION_STATUS_BLOCKED
    assert "residual_position_not_empty" in result["blockers"]


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


def test_notional_above_cap_blocks(tmp_path: Path) -> None:
    result = _run_ingestion(tmp_path, {"estimated_submit_notional": "25.000001"})

    assert result["certification_status"] == CERTIFICATION_STATUS_BLOCKED
    assert "estimated_submit_notional_exceeds_max_notional" in result["blockers"]


def test_approval_packet_does_not_authorize_submit(tmp_path: Path) -> None:
    result = _run_ingestion(tmp_path)
    packet = result["paper_fill_experiment_approval_packet"]

    assert packet["approval_state"] == APPROVAL_STATE_NOT_AUTHORIZED
    assert packet["operator_phrase_generated_for_review_only"] is True
    assert packet["operator_phrase_accepted"] is False
    assert packet["paper_submit_authorized"] is False
    assert packet["paper_entry_authorized"] is False
    assert packet["paper_exit_authorized"] is False
    assert packet["paper_fill_authorized"] is False
    assert packet["broker_action_permitted"] is False
    assert packet["broker_mutation_authorized_by_this_packet"] is False
    assert "current_paper_submit" in packet["disallowed_actions"]
    assert "current_broker_mutation" in packet["disallowed_actions"]


def test_required_operator_phrase_names_prior_certification_and_bounds(
    tmp_path: Path,
) -> None:
    result = _run_ingestion(tmp_path)
    packet = result["paper_fill_experiment_approval_packet"]
    phrase = packet["required_operator_phrase"]

    assert result["prior_certification_id"] in phrase
    assert CLIENT_ORDER_ID in phrase
    assert "BTCUSD" in phrase
    assert "max notional 25" in phrase
    assert "exactly one bounded BTCUSD Alpaca paper entry attempt" in phrase
    assert "one bounded exit/flatten attempt" in phrase
    assert "does not authorize live trading" in phrase
    assert packet["proposed_symbol"] == "BTCUSD"
    assert packet["proposed_max_notional"] == "25"


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


def test_runner_accepts_input_and_output_paths_without_authorization_switch() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "$CertificationResultPath" in script
    assert "$OutputRoot" in script
    assert "algotrader.orchestration.crypto_paper_certification_ingestion" in script
    assert "PaperSubmitAuthorized" not in script
    assert "broker_mutation_performed=false" in script
    assert "paper_submit_performed=false" in script


def _run_ingestion(
    tmp_path: Path,
    updates: dict[str, object] | None = None,
    *,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    source = payload or _certification_result()
    if updates:
        source.update(updates)
    source_path = _write_certification_result(tmp_path, source)
    return run_crypto_paper_certification_ingestion(
        certification_result_path=source_path,
        output_root=tmp_path / "runs" / "crypto_paper_certification_ingestion" / "latest",
        as_of="2026-07-05T21:00:00+00:00",
        write_artifacts=True,
    )


def _write_certification_result(
    tmp_path: Path,
    payload: dict[str, object],
) -> Path:
    source_path = (
        tmp_path
        / "runs"
        / "crypto_paper_submit_cancel_certification"
        / "latest"
        / "certification_result.json"
    )
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return source_path


def _certification_result() -> dict[str, object]:
    return copy.deepcopy(
        {
            "schema_version": "v5_8_crypto_paper_submit_cancel_certification_v1",
            "as_of": AS_OF,
            "outcome_classification": "submitted_cancel_confirmed",
            "submit_attempt_count": 1,
            "cancel_attempt_count": 1,
            "broker_read_observed": True,
            "broker_mutation_performed": True,
            "paper_submit_performed": True,
            "paper_cancel_performed": True,
            "live_endpoint_touched": False,
            "live_mutation_performed": False,
            "credential_values_exposed": False,
            "client_order_id": CLIENT_ORDER_ID,
            "symbol": "BTCUSD",
            "submit_status": "pending_new",
            "cancel_status": "requested",
            "final_order_status": "canceled",
            "expected_account_matched": True,
            "submitted_qty": "0.000396783",
            "approved_qty": "0.000396783",
            "estimated_submit_notional": "12.49999372305",
            "approved_max_notional": "25",
            "reconciliation": {
                "filled_qty": "0",
                "final_order_status": "canceled",
                "residual_position": {},
            },
            "final_order": {
                "client_order_id": CLIENT_ORDER_ID,
                "filled_qty": "0",
                "qty": "0.000396783",
                "status": "canceled",
                "symbol": "BTCUSD",
            },
            "submitted_request": {
                "client_order_id": CLIENT_ORDER_ID,
                "quantity": "0.000396783",
                "symbol": "BTCUSD",
            },
            "labels": [
                "paper_lab_only",
                "signal_evaluation_only",
                "not_live_authorized",
                "profit_claim=none",
                "bounded_paper_submit_cancel_certification",
                "one_order_attempt_only",
                "btcusd_only",
                "not_live",
                "operator_authorized_v5_8",
            ],
        }
    )


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""
