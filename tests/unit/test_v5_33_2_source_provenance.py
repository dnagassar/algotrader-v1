"""Unit tests for V5.33.2 clean source provenance and admission controls."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from algotrader.execution.crypto_read_only_paper_observation_adapter import (
    PreflightCheckError,
    get_source_provenance,
)
from algotrader.execution.crypto_supervised_readiness_trial import _validate_offline_receipt


def test_clean_source_provenance_structure(tmp_path: Path) -> None:
    repo_root = Path(".").resolve()

    def mock_run_git(args: list[str]) -> str:
        cmd = args[0]
        if cmd == "rev-parse":
            if args[1] == "HEAD":
                return "a" * 40
            if args[1] == "HEAD^{tree}":
                return "b" * 40
            return "feature-branch"
        if cmd == "status":
            # Porcelain empty -> clean
            return ""
        if cmd == "show":
            # Return real content of files in manifest
            rel_path = args[1].split("HEAD:")[1]
            return (repo_root / rel_path).read_text(encoding="utf-8")
        return ""

    with patch("subprocess.run") as mock_sub:
        mock_sub.side_effect = lambda cmd, **kwargs: MagicMock(
            returncode=0, stdout=mock_run_git(cmd[1:])
        )
        provenance = get_source_provenance(repo_root)

        assert provenance["source_commit_sha"] == "a" * 40
        assert provenance["source_tree_sha"] == "b" * 40
        assert provenance["source_worktree_clean"] is True
        assert provenance["source_branch_or_detached"] == "feature-branch"
        assert len(provenance["adapter_source_bundle_sha256"]) == 64
        assert isinstance(provenance["source_bundle_manifest"], dict)
        assert {
            "src/algotrader/execution/secure_credential_provider.py",
            "src/algotrader/execution/v535_unattended_readonly.py",
            "src/algotrader/execution/v535_burn_in_status.py",
            "src/algotrader/execution/v536_canary_authorization.py",
            "src/algotrader/execution/v536_credential_provisioning.py",
            "src/algotrader/execution/v536_windows_task.py",
            "src/algotrader/execution/v536_windows_host_canary.py",
            "src/algotrader/execution/crypto_history_refresh_adapter.py",
            "src/algotrader/orchestration/crypto_tournament_v2_forward_oos.py",
            "src/algotrader/orchestration/crypto_tournament_v2_oos_scheduler.py",
            "scripts/run_v535_unattended_readonly.ps1",
            "scripts/run_v536_windows_host_canary.ps1",
            "scripts/provision_v536_windows_credential.ps1",
            "scripts/launch_v536_credential_provisioning.py",
            "docs/design/v5_35_secure_unattended_read_only_acceptance_contract.md",
            "docs/design/v5_35_credential_provider_and_threat_boundary.md",
            "docs/design/v5_36_windows_host_commissioning_canary_acceptance_contract.md",
            "docs/design/v5_36_credential_provisioning_and_windows_task_boundary.md",
            "docs/design/v5_36_1_credential_writer_diagnostic_repair_contract.md",
            "docs/design/v5_36_2_exact_runtime_source_binding_repair_contract.md",
            "docs/design/v5_36_3_masked_provisioning_input_repair_contract.md",
            "docs/design/crypto_tournament_v2_oos_scheduler_task.xml",
        }.issubset(provenance["source_bundle_manifest"])


def test_dirty_source_worktree_blocks_before_client_construction(tmp_path: Path) -> None:
    repo_root = Path(".").resolve()

    def mock_run_git(args: list[str]) -> str:
        cmd = args[0]
        if cmd == "rev-parse":
            if args[1] == "HEAD":
                return "a" * 40
            if args[1] == "HEAD^{tree}":
                return "b" * 40
            return "feature-branch"
        if cmd == "status":
            # Simulate porcelain output indicating modified file
            return " M src/algotrader/cli.py"
        return ""

    with patch("subprocess.run") as mock_sub:
        mock_sub.side_effect = lambda cmd, **kwargs: MagicMock(
            returncode=0, stdout=mock_run_git(cmd[1:])
        )

        with pytest.raises(PreflightCheckError, match="source_worktree_dirty"):
            get_source_provenance(repo_root)


def test_untracked_non_ignored_file_blocks_source_provenance(tmp_path: Path) -> None:
    repo_root = Path(".").resolve()

    def mock_run_git(args: list[str]) -> str:
        cmd = args[0]
        if cmd == "rev-parse":
            if args[1] == "HEAD":
                return "a" * 40
            if args[1] == "HEAD^{tree}":
                return "b" * 40
            return "feature-branch"
        if cmd == "status":
            # Simulate untracked file output
            return "?? scripts/untracked_helper.py"
        return ""

    with patch("subprocess.run") as mock_sub:
        mock_sub.side_effect = lambda cmd, **kwargs: MagicMock(
            returncode=0, stdout=mock_run_git(cmd[1:])
        )

        with pytest.raises(PreflightCheckError, match="source_worktree_dirty"):
            get_source_provenance(repo_root)


def test_provenance_failure_classifications(tmp_path: Path) -> None:
    repo_root = Path(".").resolve()

    # 1. Repository unavailable (git not installed or not a repo)
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(PreflightCheckError, match="repository_unavailable"):
            get_source_provenance(repo_root)

    # 2. Commit unresolved
    with patch("subprocess.run") as mock_sub:
        mock_sub.return_value = MagicMock(returncode=128, stdout="")
        with pytest.raises(PreflightCheckError, match="commit_unresolved"):
            get_source_provenance(repo_root)


def test_offline_consumer_validates_commit_and_tree_mismatch(tmp_path: Path) -> None:
    repo_root = Path(".").resolve()

    obs_receipt = {
        "schema_version": "v5_33_production_broker_observation_receipt_v1",
        "source_classification": "genuine_alpaca_paper_observation",
        "paper_endpoint_classification": "https://paper-api.alpaca.markets",
        "expected_account_match": True,
        "target_symbol": "BTCUSD",
        "target_asset_class": "crypto",
        "target_tradability": True,
        "target_orderability": True,
        "unexpected_exposure_classification": "clean",
        "account_status_fields": {"status": "active", "trading_blocked": False, "account_blocked": False},
        "truncation_indicators": {"positions_truncated": False, "orders_truncated": False},
        "ambiguity_indicators": {"duplicate_positions": False, "duplicate_client_order_ids": False},
        "safety_booleans": {},
    }

    import hashlib, json
    obs_str = json.dumps(obs_receipt, sort_keys=True, separators=(",", ":"))
    obs_receipt["canonical_receipt_sha256"] = hashlib.sha256(obs_str.encode("utf-8")).hexdigest()

    mock_prov = {
        "source_commit_sha": "a" * 40,
        "source_tree_sha": "b" * 40,
        "source_worktree_clean": True,
        "source_branch_or_detached": "test-branch",
        "adapter_source_bundle_sha256": "c" * 64,
        "source_bundle_manifest": {},
    }

    with patch("algotrader.execution.crypto_read_only_paper_observation_adapter.get_source_provenance", return_value=mock_prov):
        inv_receipt = {
            "schema_version": "v5_33_production_invocation_receipt_v1",
            "observation_receipt_sha256": obs_receipt["canonical_receipt_sha256"],
            "source_commit_sha": "f" * 40,  # Different commit
            "source_tree_sha": mock_prov["source_tree_sha"],
            "source_worktree_clean": True,
            "adapter_source_bundle_sha256": mock_prov["adapter_source_bundle_sha256"],
            "source_bundle_manifest": mock_prov["source_bundle_manifest"],
            "normalized_paper_endpoint": "https://paper-api.alpaca.markets",
            "call_counters": {"account_read_count": 1, "positions_read_count": 1, "orders_read_count": 1, "target_asset_read_count": 1},
            "observation_completion_utc": "2026-07-20T12:00:00+00:00",
            "safety_booleans": {},
        }
        inv_str = json.dumps(inv_receipt, sort_keys=True, separators=(",", ":"))
        inv_receipt["canonical_invocation_sha256"] = hashlib.sha256(inv_str.encode("utf-8")).hexdigest()

        receipt_dir = tmp_path / "receipts"
        receipt_dir.mkdir()
        (receipt_dir / "observation_receipt.json").write_text(json.dumps(obs_receipt), encoding="utf-8")
        (receipt_dir / "invocation_receipt.json").write_text(json.dumps(inv_receipt), encoding="utf-8")

        validation = _validate_offline_receipt(receipt_dir)
        assert validation["valid"] is False
        assert validation["classification"] == "blocked_source_commit_mismatch"
