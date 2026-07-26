"""Unit tests for crypto_supervised_readiness_trial_core and generational publication."""

from __future__ import annotations

import ast
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil
from unittest.mock import MagicMock, patch

import pytest

from algotrader.execution.crypto_supervised_readiness_trial_core import (
    OFFLINE_PAPER_ENVIRONMENT,
    _run_scenario_matrix,
    run_crypto_supervised_readiness_trial,
    validate_crypto_supervised_readiness_trial,
)


def test_core_receipt_root_without_validator_fails_closed(tmp_path: Path) -> None:
    output_root = tmp_path / "trial_output"
    receipt_root = tmp_path / "fake_receipt_root"
    packet = run_crypto_supervised_readiness_trial(
        output_root=output_root,
        cycle_count=8,
        receipt_root=receipt_root,
        receipt_validator=None,
        write_artifacts=True,
    )
    assert packet["trial_classification"] != "accepted"
    assert (
        packet["broker_observed_result"]["classification"]
        == "blocked_receipt_validator_not_provided"
    )


def test_core_injected_validator_called(tmp_path: Path) -> None:
    output_root = tmp_path / "trial_output"
    receipt_root = tmp_path / "receipt_root"
    mock_validator = MagicMock(return_value={
        "valid": True,
        "classification": "fixture_replay_validated",
        "broker_state_observed": False,
        "network_used": False,
        "broker_read_occurred": False,
        "receipt": {},
    })

    packet = run_crypto_supervised_readiness_trial(
        output_root=output_root,
        cycle_count=8,
        receipt_root=receipt_root,
        receipt_validator=mock_validator,
        write_artifacts=True,
    )

    mock_validator.assert_called_once_with(receipt_root)
    assert packet["trial_classification"] == "accepted"
    assert (
        packet["broker_observed_result"]["classification"]
        == "fixture_replay_validated"
    )


def test_scenario_matrix_forwards_broker_factory_and_environment(
    tmp_path: Path,
) -> None:
    factory = MagicMock(name="broker_factory")
    environment = {"APP_PROFILE": "", "ALPACA_API_KEY": False}
    receipts = [
        {
            "decision_classification": "offline_simulated_trade_only",
            "receipt_hash": "eligible",
        },
        {
            "decision_classification": "hold_noop_position_unchanged",
            "receipt_hash": "hold",
        },
        {
            "decision_classification":
                "blocked_no_trade_all_candidates_failed_gates",
            "receipt_hash": "blocked",
        },
    ]
    broker_packet = {
        "broker_observed_readiness_preview": {
            "broker_observed_readiness_decision":
                "blocked_adapter_unavailable",
            "broker_state_observed": False,
            "broker_read_blocked": True,
            "broker_read_occurred": False,
            "network_used": False,
        },
        "safety": {
            "paper_submit_occurred": False,
            "broker_mutation_occurred": False,
        },
        "blockers": ["blocked_adapter_unavailable"],
    }
    helper_receipt = {
        "scenario_id": "helper",
        "acceptance_passed": True,
    }
    with (
        patch(
            "algotrader.execution.crypto_supervised_readiness_trial_core."
            "run_tomorrow_crypto_trader_demo",
            return_value=broker_packet,
        ) as demo,
        patch(
            "algotrader.execution.crypto_supervised_readiness_trial_core."
            "_state_injection_scenario",
            return_value=helper_receipt,
        ) as state_scenario,
        patch(
            "algotrader.execution.crypto_supervised_readiness_trial_core."
            "_duplicate_intent_scenario",
            return_value=helper_receipt,
        ) as duplicate_scenario,
    ):
        matrix = _run_scenario_matrix(
            root=tmp_path,
            decision_start=datetime(2026, 7, 19, 12, tzinfo=UTC),
            primary_receipts=receipts,
            broker_observed_readiness=True,
            allow_alpaca_paper_read=True,
            broker_observed_client_factory=factory,
            paper_environment=environment,
        )

    assert len(matrix) == 8
    assert demo.call_args.kwargs["broker_observed_client_factory"] is factory
    assert demo.call_args.kwargs["paper_environment"] is environment
    assert all(
        call.kwargs["paper_environment"] is environment
        for call in state_scenario.call_args_list
    )
    assert (
        duplicate_scenario.call_args.kwargs["paper_environment"]
        is environment
    )


def test_all_six_demo_calls_forward_the_same_environment_name() -> None:
    import algotrader.execution.crypto_supervised_readiness_trial_core as core

    tree = ast.parse(Path(core.__file__).read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "run_tomorrow_crypto_trader_demo"
    ]
    assert len(calls) == 6
    for call_node in calls:
        keyword = next(
            (
                item
                for item in call_node.keywords
                if item.arg == "paper_environment"
            ),
            None,
        )
        assert keyword is not None
        assert isinstance(keyword.value, ast.Name)
        assert keyword.value.id == "paper_environment"


def test_generational_publication_and_interruption_recovery(tmp_path: Path) -> None:
    output_root = tmp_path / "generational_output"

    # Step 1: Initial run (Generational Publish A)
    packet_a = run_crypto_supervised_readiness_trial(
        output_root=output_root,
        cycle_count=8,
        write_artifacts=True,
    )
    assert packet_a["trial_classification"] == "accepted"

    val_a = validate_crypto_supervised_readiness_trial(output_root)
    assert val_a["validation_status"] == "passed"

    root_packet_file = output_root / "readiness_packet.json"
    root_packet_bytes_a = root_packet_file.read_bytes()
    bundle_id_a = packet_a["bundle_id"]

    # Verify generation directory A exists
    gen_dir_a = output_root / "generations" / bundle_id_a
    assert gen_dir_a.is_dir()
    assert (gen_dir_a / "operating_report.md").is_file()
    assert (gen_dir_a / "manifest.json").is_file()

    # Step 2: Simulate interrupted run (Generation B written, but os.replace faulted)
    with patch("os.replace", side_effect=RuntimeError("Simulated interruption before os.replace")):
        with pytest.raises(RuntimeError, match="Simulated interruption"):
            run_crypto_supervised_readiness_trial(
                output_root=output_root,
                cycle_count=9,
                write_artifacts=True,
            )

    # After interruption, root packet MUST remain unchanged and equal to Generation A
    assert root_packet_file.read_bytes() == root_packet_bytes_a
    val_after_fault = validate_crypto_supervised_readiness_trial(output_root)
    assert val_after_fault["validation_status"] == "passed"

    # The same root-validity assertion detects the rejected in-place writer.
    rejected_packet = json.loads(root_packet_bytes_a)
    rejected_report_path = Path(
        rejected_packet["artifact_paths"]["operating_report"]
    )
    rejected_report_bytes = rejected_report_path.read_bytes()

    def rejected_in_place_publish() -> None:
        rejected_report_path.write_text(
            "new support bytes published before the root packet\n",
            encoding="utf-8",
        )
        raise RuntimeError("Simulated interruption before root packet replace")

    try:
        with pytest.raises(AssertionError):
            try:
                rejected_in_place_publish()
            except RuntimeError:
                pass
            assert (
                validate_crypto_supervised_readiness_trial(output_root)[
                    "validation_status"
                ]
                == "passed"
            )
    finally:
        rejected_report_path.write_bytes(rejected_report_bytes)
    assert (
        validate_crypto_supervised_readiness_trial(output_root)[
            "validation_status"
        ]
        == "passed"
    )

    # Step 3: Clean retry (Generational Publish B)
    packet_b = run_crypto_supervised_readiness_trial(
        output_root=output_root,
        cycle_count=9,
        write_artifacts=True,
    )
    assert packet_b["trial_classification"] == "accepted"
    val_b = validate_crypto_supervised_readiness_trial(output_root)
    assert val_b["validation_status"] == "passed"
    assert packet_b["bundle_id"] != bundle_id_a


def test_generational_validator_rejects_tampering_and_escapes(tmp_path: Path) -> None:
    output_root = tmp_path / "tamper_output"
    packet = run_crypto_supervised_readiness_trial(
        output_root=output_root,
        cycle_count=8,
        write_artifacts=True,
    )
    assert validate_crypto_supervised_readiness_trial(output_root)["validation_status"] == "passed"

    bundle_id = packet["bundle_id"]
    gen_dir = output_root / "generations" / bundle_id
    report_path = gen_dir / "operating_report.md"
    manifest_path = gen_dir / "manifest.json"
    packet_path = output_root / "readiness_packet.json"
    original_report = report_path.read_bytes()
    original_manifest = manifest_path.read_bytes()
    original_packet = packet_path.read_bytes()

    # 1. Content artifact tampering (without updating manifest or packet)
    report_path.write_text("tampered content\n", encoding="utf-8")
    val_tamper1 = validate_crypto_supervised_readiness_trial(output_root)
    assert val_tamper1["validation_status"] == "failed"
    assert "artifact_hash_mismatch:operating_report" in val_tamper1["errors"]

    # 2. Coordinated support + manifest tampering still fails at the root trust packet.
    coordinated_report = b"coordinated support and manifest tamper\n"
    report_path.write_bytes(coordinated_report)
    manifest = json.loads(original_manifest)
    manifest["artifacts"]["operating_report"]["sha256"] = hashlib.sha256(
        coordinated_report
    ).hexdigest()
    manifest["artifacts"]["operating_report"]["size"] = len(coordinated_report)
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    val_tamper2 = validate_crypto_supervised_readiness_trial(output_root)
    assert val_tamper2["validation_status"] == "failed"
    assert "artifact_hash_mismatch:manifest" in val_tamper2["errors"]
    assert "packet_manifest_mismatch:operating_report" in val_tamper2["errors"]

    # Restore support bytes and prove direct root-integrity mismatch fails closed.
    report_path.write_bytes(original_report)
    manifest_path.write_bytes(original_manifest)
    root_mismatch = json.loads(original_packet)
    root_mismatch["artifact_integrity"]["manifest"]["sha256"] = "0" * 64
    packet_path.write_text(json.dumps(root_mismatch), encoding="utf-8")
    val_root_mismatch = validate_crypto_supervised_readiness_trial(output_root)
    assert val_root_mismatch["validation_status"] == "failed"
    assert "artifact_hash_mismatch:manifest" in val_root_mismatch["errors"]

    # 3. Path escape in readiness_packet
    packet_path.write_bytes(original_packet)
    pkt_data = json.loads(original_packet)
    pkt_data["artifact_paths"]["operating_report"] = "C:\\Windows\\System32\\cmd.exe"
    packet_path.write_text(json.dumps(pkt_data), encoding="utf-8")

    val_escape = validate_crypto_supervised_readiness_trial(output_root)
    assert val_escape["validation_status"] == "failed"
    assert any("path_escape" in err for err in val_escape["errors"])


def test_validator_rejects_invalid_generations_structure_and_mixed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_root = tmp_path / "structure_output"
    packet = run_crypto_supervised_readiness_trial(
        output_root=output_root,
        cycle_count=8,
        write_artifacts=True,
    )
    assert validate_crypto_supervised_readiness_trial(output_root)["validation_status"] == "passed"

    generations_dir = output_root / "generations"
    # Unreferenced completed generations are valid after a process interruption.
    (generations_dir / "extra_legacy_dir").mkdir()
    val_extra = validate_crypto_supervised_readiness_trial(output_root)
    assert val_extra["validation_status"] == "passed"

    selected_report = Path(packet["artifact_paths"]["operating_report"])
    original_is_symlink = Path.is_symlink
    with monkeypatch.context() as context:
        context.setattr(
            Path,
            "is_symlink",
            lambda path: path == selected_report or original_is_symlink(path),
        )
        val_symlink = validate_crypto_supervised_readiness_trial(output_root)
    assert val_symlink["validation_status"] == "failed"
    assert (
        "path_escape_or_generation_mismatch:operating_report"
        in val_symlink["errors"]
    )

    # But a root packet may not mix its selected generation with another one.
    packet_path = output_root / "readiness_packet.json"
    root_packet = json.loads(packet_path.read_text(encoding="utf-8"))
    mixed_report = generations_dir / "extra_legacy_dir" / "operating_report.md"
    source_report = Path(root_packet["artifact_paths"]["operating_report"])
    mixed_report.write_bytes(source_report.read_bytes())
    root_packet["artifact_paths"]["operating_report"] = str(mixed_report)
    packet_path.write_text(json.dumps(root_packet), encoding="utf-8")
    val_mixed = validate_crypto_supervised_readiness_trial(output_root)
    assert val_mixed["validation_status"] == "failed"
    assert (
        "path_escape_or_generation_mismatch:operating_report"
        in val_mixed["errors"]
    )

def test_in_place_rerun_idempotency_regression(tmp_path: Path) -> None:
    output_root = tmp_path / "inplace_output"

    packet1 = run_crypto_supervised_readiness_trial(
        output_root=output_root,
        cycle_count=8,
        write_artifacts=True,
    )
    assert packet1["trial_classification"] == "accepted"
    bundle1 = packet1["bundle_id"]

    # In-place rerun with identical parameters must succeed and reuse existing generation
    packet2 = run_crypto_supervised_readiness_trial(
        output_root=output_root,
        cycle_count=8,
        write_artifacts=True,
    )
    assert packet2["trial_classification"] == "accepted"
    assert packet2["bundle_id"] == bundle1
    assert validate_crypto_supervised_readiness_trial(output_root)["validation_status"] == "passed"

    # Legacy fixed-root packets with no artifact_integrity remain valid.
    legacy_root = tmp_path / "legacy_output"
    legacy_root.mkdir()
    legacy_paths = {
        "readiness_packet": legacy_root / "readiness_packet.json",
        "operating_report": legacy_root / "operating_report.md",
        "cycle_receipts": legacy_root / "cycle_receipts.jsonl",
        "scenario_receipts": legacy_root / "scenario_receipts.jsonl",
        "manifest": legacy_root / "manifest.json",
    }
    for name in ("operating_report", "cycle_receipts", "scenario_receipts"):
        shutil.copyfile(Path(packet2["artifact_paths"][name]), legacy_paths[name])
    legacy_packet = json.loads(
        (output_root / "readiness_packet.json").read_text(encoding="utf-8")
    )
    legacy_packet.pop("bundle_id", None)
    legacy_packet.pop("artifact_integrity", None)
    legacy_packet["artifact_paths"] = {
        name: str(path) for name, path in legacy_paths.items()
    }
    legacy_paths["readiness_packet"].write_text(
        json.dumps(legacy_packet, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    legacy_manifest = {
        "artifacts": {
            name: {
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size": path.stat().st_size,
            }
            for name, path in legacy_paths.items()
            if name != "manifest"
        }
    }
    legacy_paths["manifest"].write_text(
        json.dumps(legacy_manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    assert (
        validate_crypto_supervised_readiness_trial(legacy_root)[
            "validation_status"
        ]
        == "passed"
    )
