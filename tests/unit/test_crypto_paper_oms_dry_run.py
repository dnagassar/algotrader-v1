from __future__ import annotations

import ast
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.orchestration.crypto_paper_oms_dry_run import (
    CRYPTO_PAPER_OMS_DRY_RUN_REQUIRED_FALSE_FLAGS,
    CRYPTO_PAPER_OMS_DRY_RUN_REQUIRED_LABELS,
    CRYPTO_PAPER_OMS_DRY_RUN_SCHEMA_VERSION,
    run_crypto_paper_oms_dry_run,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = Path("src/algotrader/orchestration/crypto_paper_oms_dry_run.py")
SCRIPT = PROJECT_ROOT / "scripts" / "run_crypto_paper_oms_dry_run.ps1"
AS_OF = datetime(2026, 7, 4, 0, 30, tzinfo=UTC)
SENSITIVE_KEY = "crypto-dry-run-key-value-not-for-output"


def test_valid_v55_handoff_produces_blocked_not_authorized_dry_run(
    tmp_path: Path,
) -> None:
    paths = _write_handoff(tmp_path)

    record = run_crypto_paper_oms_dry_run(
        handoff_path=paths["handoff"],
        output_root=paths["output_root"],
    )

    assert record["dry_run_status"] == "blocked_not_authorized"
    assert record["approval_state"] == "not_authorized"
    assert record["broker_action_permitted"] is False
    assert record["paper_submit_authorized"] is False
    assert record["broker_mutation_performed"] is False
    assert record["intended_action"] == "buy_preview"
    assert record["asset_class"] == "crypto"
    assert record["symbol"] == "BTCUSD"
    assert record["selected_candidate_id"] == (
        "crypto:BTCUSD:crypto_vol_adjusted_momentum_24h_preview"
    )
    assert record["selected_strategy"] == "crypto_vol_adjusted_momentum_24h_preview"
    assert record["selected_backing"] == "real_local_artifact_backed"
    assert record["latest_price"] == "63006.709"
    assert record["rounded_qty"] == "0.000396783"
    assert record["derived_preview_value"] == "24.999991017147"
    assert record["preview_cap"] == "25"
    assert record["blockers"] == []
    assert set(CRYPTO_PAPER_OMS_DRY_RUN_REQUIRED_LABELS) <= set(record["labels"])
    assert "real_local_artifact_backed" in record["labels"]
    assert record["broker_neutral_preview"]["not_submittable"] is True
    assert record["broker_neutral_preview"]["pre_broker_preview_only"] is True

    written = json.loads(
        (paths["output_root"] / "paper_oms_dry_run.json").read_text("utf-8")
    )
    brief = (paths["output_root"] / "paper_oms_dry_run.md").read_text("utf-8")
    assert written["dry_run_status"] == "blocked_not_authorized"
    assert written["broker_action_permitted"] is False
    assert "no order was submitted" in brief
    assert "no broker mutation is authorized" in brief


def test_deterministic_dry_run_identity_is_stable(tmp_path: Path) -> None:
    paths = _write_handoff(tmp_path)

    first = run_crypto_paper_oms_dry_run(
        handoff_path=paths["handoff"],
        output_root=paths["output_root"],
        write_artifacts=False,
    )
    second = run_crypto_paper_oms_dry_run(
        handoff_path=paths["handoff"],
        output_root=paths["output_root"],
        write_artifacts=False,
    )
    expected = _expected_identity(_handoff())

    assert first["dry_run_id"] == second["dry_run_id"] == expected["dry_run_id"]
    assert first["pre_broker_order_id"] == second["pre_broker_order_id"]
    assert first["idempotency_key"] == second["idempotency_key"]
    assert first["idempotency_key"] == expected["idempotency_key"]
    assert first["pre_broker_order_id"].startswith("prebroker_")


def test_approval_state_not_authorized_blocks_broker_action(tmp_path: Path) -> None:
    paths = _write_handoff(tmp_path)

    record = run_crypto_paper_oms_dry_run(
        handoff_path=paths["handoff"],
        output_root=paths["output_root"],
    )

    assert record["approval_state"] == "not_authorized"
    assert record["dry_run_status"] == "blocked_not_authorized"
    assert record["broker_action_permitted"] is False
    assert record["paper_submit_authorized"] is False


@pytest.mark.parametrize(
    ("field_name", "expected_blocker"),
    (
        ("paper_submit_authorized", "paper_submit_authorized_true"),
        ("paper_submit_performed", "paper_submit_performed_true"),
        ("broker_mutation_performed", "broker_mutation_performed_true"),
        ("live_mutation_performed", "live_mutation_performed_true"),
    ),
)
def test_true_mutation_or_submit_flags_block_dry_run(
    tmp_path: Path,
    field_name: str,
    expected_blocker: str,
) -> None:
    paths = _write_handoff(tmp_path, updates={field_name: True})

    record = run_crypto_paper_oms_dry_run(
        handoff_path=paths["handoff"],
        output_root=paths["output_root"],
    )

    assert record["dry_run_status"] == "blocked_invalid_handoff"
    assert expected_blocker in record["blockers"]
    assert record["broker_action_permitted"] is False
    assert record["paper_submit_authorized"] is False
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False
    assert record["live_mutation_performed"] is False


def test_missing_required_labels_blocks_dry_run(tmp_path: Path) -> None:
    labels = [label for label in _labels() if label != "no_submit_mode"]
    paths = _write_handoff(tmp_path, updates={"labels": labels})

    record = run_crypto_paper_oms_dry_run(
        handoff_path=paths["handoff"],
        output_root=paths["output_root"],
    )

    assert record["dry_run_status"] == "blocked_invalid_handoff"
    assert "missing_required_safety_labels" in record["blockers"]
    assert "no_submit_mode" in record["missing_required_labels"]


def test_fixture_backed_input_blocks_outside_fixture_mode(tmp_path: Path) -> None:
    paths = _write_handoff(
        tmp_path,
        updates={
            "selected_backing": "fixture_backed",
            "labels": _labels(backing="fixture_backed"),
        },
    )

    record = run_crypto_paper_oms_dry_run(
        handoff_path=paths["handoff"],
        output_root=paths["output_root"],
    )

    assert record["dry_run_status"] == "blocked_invalid_handoff"
    assert "fixture_backed_handoff" in record["blockers"]


def test_invalid_qty_blocks_dry_run(tmp_path: Path) -> None:
    paths = _write_handoff(tmp_path, updates={"rounded_qty": "0"})

    record = run_crypto_paper_oms_dry_run(
        handoff_path=paths["handoff"],
        output_root=paths["output_root"],
    )

    assert record["dry_run_status"] == "blocked_invalid_handoff"
    assert "missing_or_invalid_rounded_qty" in record["blockers"]


def test_derived_preview_value_above_cap_blocks_dry_run(tmp_path: Path) -> None:
    paths = _write_handoff(tmp_path, updates={"derived_preview_value": "25.01"})

    record = run_crypto_paper_oms_dry_run(
        handoff_path=paths["handoff"],
        output_root=paths["output_root"],
    )

    assert record["dry_run_status"] == "blocked_invalid_handoff"
    assert "derived_preview_value_exceeds_cap" in record["blockers"]


def test_generated_dry_run_artifacts_include_no_submit_no_mutation_live_flags(
    tmp_path: Path,
) -> None:
    paths = _write_handoff(tmp_path)

    record = run_crypto_paper_oms_dry_run(
        handoff_path=paths["handoff"],
        output_root=paths["output_root"],
    )
    manifest = json.loads((paths["output_root"] / "manifest.json").read_text("utf-8"))
    operating_record = json.loads(
        (paths["output_root"] / "operating_record.jsonl").read_text("utf-8")
    )

    payloads = (
        record,
        record["broker_neutral_preview"],
        manifest,
        operating_record,
    )
    for payload in payloads:
        assert payload["broker_action_permitted"] is False
        for field_name in CRYPTO_PAPER_OMS_DRY_RUN_REQUIRED_FALSE_FLAGS:
            assert payload[field_name] is False
    assert record["broker_read_performed_current_run"] is False
    assert record["network_access_attempted"] is False
    assert record["profit_claim"] == "none"
    assert operating_record["profit_claim"] == "none"


def test_manifest_integrity(tmp_path: Path) -> None:
    paths = _write_handoff(tmp_path)

    record = run_crypto_paper_oms_dry_run(
        handoff_path=paths["handoff"],
        output_root=paths["output_root"],
    )
    manifest_path = Path(record["artifact_paths"]["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == CRYPTO_PAPER_OMS_DRY_RUN_SCHEMA_VERSION
    assert set(manifest["required_artifacts"]) == {
        "operating_record",
        "paper_oms_dry_run_json",
        "paper_oms_dry_run_md",
    }
    for artifact in manifest["required_artifacts"].values():
        assert Path(artifact["path"]).is_file()
        assert artifact["sha256"]
        assert artifact["size"] > 0
    assert set(manifest["input_artifacts"]) == {"paper_oms_handoff"}
    assert manifest["input_artifacts"]["paper_oms_handoff"]["sha256"]
    assert manifest["manifest"]["path"].endswith("manifest.json")


def test_generated_runs_artifacts_remain_untracked(tmp_path: Path) -> None:
    paths = _write_handoff(tmp_path)

    run_crypto_paper_oms_dry_run(
        handoff_path=paths["handoff"],
        output_root=paths["output_root"],
    )
    manifest = json.loads((paths["output_root"] / "manifest.json").read_text("utf-8"))
    git_result = subprocess.run(
        ["git", "ls-files", "runs"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert manifest["generated_under_runs"] is True
    assert "runs/" in (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert git_result.returncode == 0, git_result.stderr
    assert git_result.stdout.strip() == ""


def test_normal_pytest_path_remains_offline_broker_free_network_free() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
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
        "algotrader.broker",
        "algotrader.brokers",
        "algotrader.runtime",
    )
    call_names = {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }

    assert not any(
        module == prefix or module.startswith(f"{prefix}.")
        for module in imported_modules
        for prefix in forbidden_prefixes
    )
    assert call_names.isdisjoint(
        {
            "cancel_order",
            "close_position",
            "create_order",
            "liquidate",
            "replace_order",
            "request",
            "submit_order",
            "urlopen",
        }
    )


def test_run_crypto_paper_oms_dry_run_script_contract() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    expected_fragments = (
        "Runs the crypto Paper OMS dry-run adapter gate in no-submit mode",
        '[string]$OutputRoot = "runs\\crypto_paper_oms_dry_run\\latest"',
        '[string]$HandoffPath = "runs\\crypto_paper_oms_handoff\\latest\\paper_oms_handoff.json"',
        "crypto_paper_oms_dry_run_mode=offline/no_submit",
        "crypto_paper_oms_dry_run_no_submit_enforced=true",
        "preflight_APP_PROFILE_is_paper",
        "preflight_APP_PROFILE_is_live",
        "preflight_credential_variables_loaded",
        "preflight_network_flags_loaded",
        "preflight_live_endpoint_indicator",
        "crypto_paper_oms_dry_run_paper_submit_authorized=false",
        "crypto_paper_oms_dry_run_paper_submit_performed=false",
        "crypto_paper_oms_dry_run_broker_mutation_performed=false",
        "crypto_paper_oms_dry_run_live_mutation_performed=false",
        "algotrader.orchestration.crypto_paper_oms_dry_run",
        "--handoff-path",
        "Credential values are never printed",
    )
    for fragment in expected_fragments:
        assert fragment in script

    assert "--submit" not in script
    assert "paper_submit_authorized=true" not in script


def test_run_crypto_paper_oms_dry_run_script_invokes_offline_module(
    tmp_path: Path,
) -> None:
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(tmp_path, capture_path)

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-OutputRoot",
            str(tmp_path / "dry run latest"),
            "-HandoffPath",
            str(tmp_path / "paper_oms_handoff.json"),
            "-AllowFixtureBacked",
            "-Format",
            "json",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "crypto_paper_oms_dry_run_no_submit_enforced=true" in result.stdout
    assert "preflight_credential_variables_loaded=false" in result.stdout
    args = capture_path.read_text(encoding="utf-8")
    assert "-m algotrader.orchestration.crypto_paper_oms_dry_run" in args
    assert "--output-root" in args
    assert "--handoff-path" in args
    assert "--allow-fixture-backed" in args
    assert "--format json" in args
    assert "--submit" not in args


def test_run_crypto_paper_oms_dry_run_script_blocks_loaded_credentials(
    tmp_path: Path,
) -> None:
    capture_path = tmp_path / "python_args.txt"
    env = _fake_python_env(tmp_path, capture_path)
    env["ALPACA_API_KEY"] = SENSITIVE_KEY

    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 2, combined
    assert "preflight_credential_variables_loaded=true" in result.stdout
    assert "crypto_paper_oms_dry_run_status=blocked_unsafe_environment" in result.stdout
    assert not capture_path.exists()
    assert SENSITIVE_KEY not in combined


def _write_handoff(
    tmp_path: Path,
    *,
    updates: dict[str, object] | None = None,
) -> dict[str, Path]:
    root = tmp_path / "runs" / "crypto_paper_oms_handoff" / "latest"
    output_root = tmp_path / "runs" / "crypto_paper_oms_dry_run" / "latest"
    root.mkdir(parents=True)
    handoff = _handoff()
    if updates:
        handoff.update(updates)
    _write_json(root / "paper_oms_handoff.json", handoff)
    return {
        "handoff": root / "paper_oms_handoff.json",
        "output_root": output_root,
    }


def _handoff() -> dict[str, object]:
    symbol = "BTCUSD"
    return {
        "schema_version": "v5_5_crypto_paper_oms_handoff_v1",
        "as_of": AS_OF.isoformat(),
        "sizing_preview_source": (
            "runs/crypto_qty_sizing_preview/latest/sizing_preview.json"
        ),
        "handoff_status": "approval_required",
        "approval_state": "not_authorized",
        "intended_action": "buy_preview",
        "asset_class": "crypto",
        "symbol": symbol,
        "strategy_id": "crypto_vol_adjusted_momentum_24h_preview",
        "selected_candidate_id": (
            f"crypto:{symbol}:crypto_vol_adjusted_momentum_24h_preview"
        ),
        "selected_backing": "real_local_artifact_backed",
        "latest_price": "63006.709",
        "preview_notional_cap": "25",
        "rounded_qty": "0.000396783",
        "derived_preview_value": "24.999991017147",
        "max_preview_value": "25",
        "blockers": [],
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_mutation_performed": False,
        "broker_read_performed_current_run": False,
        "network_access_attempted": False,
        "live_endpoint_touched": False,
        "credential_values_exposed": False,
        "profit_claim": "none",
        "labels": _labels(),
        "next_operator_action": (
            "operator_review_handoff_packet_before_any_separate_paper_submit_authorization"
        ),
    }


def _labels(*, backing: str = "real_local_artifact_backed") -> list[str]:
    return [
        "paper_lab_only",
        "signal_evaluation_only",
        "not_live_authorized",
        "profit_claim=none",
        "no_submit_mode",
        "sizing_preview_only",
        backing,
        "paper_oms_handoff_only",
        "approval_required",
    ]


def _expected_identity(handoff: dict[str, object]) -> dict[str, str]:
    basis = {
        "as_of": str(handoff["as_of"]),
        "selected_candidate_id": str(handoff["selected_candidate_id"]),
        "symbol": str(handoff["symbol"]),
        "selected_strategy": str(handoff["strategy_id"]),
        "rounded_qty": str(handoff["rounded_qty"]),
        "derived_preview_value": str(handoff["derived_preview_value"]),
    }
    digest = hashlib.sha256(
        json.dumps(basis, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "dry_run_id": f"dryrun_{digest[:24]}",
        "pre_broker_order_id": f"prebroker_{digest[24:48]}",
        "idempotency_key": f"crypto_paper_oms_dry_run:{digest}",
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _fake_python_env(tmp_path: Path, capture_path: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo {\"dry_run_status\":\"blocked_not_authorized\",\"paper_submit_performed\":false}\r\n"
        "exit /B 0\r\n",
        encoding="utf-8",
        newline="",
    )

    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}{os.pathsep}{env.get('PATH', '')}"
    env["PYTHON_ARG_CAPTURE"] = str(capture_path)
    env["APP_PROFILE"] = "dev"
    for name in (
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "PYTEST_NETWORK",
        "NETWORK_TESTS",
        "ALLOW_NETWORK_TESTS",
        "ALGO_TRADER_ALLOW_NETWORK_TESTS",
        "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
        "ALPACA_BASE_URL",
        "ALPACA_PAPER_BASE_URL",
        "APCA_API_BASE_URL",
    ):
        env.pop(name, None)
    return env


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify run_crypto_paper_oms_dry_run.ps1")
    return powershell
