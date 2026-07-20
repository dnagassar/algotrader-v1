"""V5.34 Bounded Alpaca paper account baseline cleanup module.

Performs exactly one bounded cleanup attempt against the configured Alpaca paper
endpoint and expected paper account to restore a clean, flat baseline (0 open
orders, 0 positions) before paper-observed OOS burn-in.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json

from pathlib import Path
import time
from typing import Any

from algotrader.config import AlpacaPaperConfig
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient
from algotrader.execution.crypto_read_only_paper_observation_adapter import (
    EXPECTED_PAPER_ENDPOINT,
    PreflightCheckError,
    _canonical_account_identity,
    get_production_preflight_inputs,
    get_source_provenance,
    validate_preflight_gates,
)


CLEANUP_SCHEMA_VERSION = "v5_34_paper_account_cleanup_receipt_v1"
DEFAULT_CLEANUP_OUTPUT_ROOT = Path("runs/v5_34_paper_cleanup/latest")


def run_crypto_paper_account_cleanup(
    *,
    output_root: Path | str = DEFAULT_CLEANUP_OUTPUT_ROOT,
    paper_cleanup_authorized: bool = False,
    allow_network: bool = False,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Execute bounded paper account baseline cleanup.

    Requires explicit authorization and paper profile. Stop immediately on any
    account mismatch, endpoint mismatch, credential ambiguity, or broker safety
    failure. Performs at most ONE cleanup attempt.
    """
    root_dir = Path(repo_root or Path.cwd()).resolve()
    out_dir = Path(output_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = out_dir / "cleanup_result.json"

    started_at_utc = datetime.now(UTC).isoformat()
    inputs = get_production_preflight_inputs()

    result: dict[str, Any] = {
        "schema_version": CLEANUP_SCHEMA_VERSION,
        "started_at_utc": started_at_utc,
        "completed_at_utc": None,
        "classification": "in_progress",
        "paper_cleanup_authorized": paper_cleanup_authorized,
        "allow_network": allow_network,
        "endpoint_matched": False,
        "expected_account_matched": False,
        "account_active_unblocked": False,
        "positions_before_count": 0,
        "open_orders_before_count": 0,
        "cancel_attempt_count": 0,
        "cancel_completion_count": 0,
        "close_attempt_count": 0,
        "close_completion_count": 0,
        "positions_after_count": 0,
        "open_orders_after_count": 0,
        "flatness_reconciled": False,
        "broker_mutation_performed": False,
        "source_commit_sha": None,
        "source_tree_sha": None,
        "source_worktree_clean": False,
    }

    try:
        validate_preflight_gates(
            app_profile=inputs["app_profile"],
            endpoint=inputs["endpoint"],
            key_id=inputs["key_id"],
            secret_key=inputs["secret_key"],
            expected_account_id=inputs["expected_account_id"],
            paper_broker_read_authorized=paper_cleanup_authorized,
            allow_network=allow_network,
        )
        result["endpoint_matched"] = True

        provenance = get_source_provenance(root_dir)
        result["source_commit_sha"] = provenance["source_commit_sha"]
        result["source_tree_sha"] = provenance["source_tree_sha"]
        result["source_worktree_clean"] = provenance["source_worktree_clean"]

        config = AlpacaPaperConfig(
            app_profile="paper",
            alpaca_api_key=inputs["key_id"],
            alpaca_secret_key=inputs["secret_key"],
            alpaca_paper_base_url=EXPECTED_PAPER_ENDPOINT,
        )
        client = AlpacaSdkClient(config)

        # 1. Verify account identity & safety before any mutation
        raw_account = client.get_account()
        canon_obs_id = _canonical_account_identity(getattr(raw_account, "id", None) or getattr(raw_account, "account_id", None))
        canon_obs_num = _canonical_account_identity(getattr(raw_account, "account_number", None))
        canon_exp = _canonical_account_identity(inputs["expected_account_id"])

        account_matched = (canon_exp is not None) and (
            (canon_obs_id is not None and canon_obs_id == canon_exp)
            or (canon_obs_num is not None and canon_obs_num == canon_exp)
        )
        if not account_matched:
            result["classification"] = "account_mismatch"
            _write_receipt(receipt_path, result)
            return result

        result["expected_account_matched"] = True

        status_str = str(getattr(raw_account, "status", "")).upper()
        trading_blocked = getattr(raw_account, "trading_blocked", True)
        account_blocked = getattr(raw_account, "account_blocked", True)

        if status_str != "ACTIVE" or trading_blocked or account_blocked:
            result["classification"] = "account_safety_check_failed"
            _write_receipt(receipt_path, result)
            return result

        result["account_active_unblocked"] = True

        # 2. Inventory pre-cleanup state
        positions_before = client.get_positions() or []
        orders_before = client.get_orders() or []

        result["positions_before_count"] = len(positions_before)
        result["open_orders_before_count"] = len(orders_before)

        # 3. Perform cleanup if necessary
        raw_trading_client = client.raw_trading_client

        if len(orders_before) > 0:
            result["cancel_attempt_count"] += 1
            result["broker_mutation_performed"] = True
            try:
                raw_trading_client.cancel_orders()
                result["cancel_completion_count"] += 1
            except Exception as exc:
                result["classification"] = "cancel_orders_failed"
                _write_receipt(receipt_path, result)
                return result

        if len(positions_before) > 0:
            result["close_attempt_count"] += 1
            result["broker_mutation_performed"] = True
            try:
                raw_trading_client.close_all_positions(cancel_orders=True)
                result["close_completion_count"] += 1
            except Exception as exc:
                result["classification"] = "close_positions_failed"
                _write_receipt(receipt_path, result)
                return result

        # 4. Reconcile post-cleanup baseline
        reconciled = False
        max_attempts = 10
        positions_after: Sequence[Any] = []
        orders_after: Sequence[Any] = []

        for _ in range(max_attempts):
            positions_after = client.get_positions() or []
            orders_after = client.get_orders() or []
            if len(positions_after) == 0 and len(orders_after) == 0:
                reconciled = True
                break
            time.sleep(1.0)

        result["positions_after_count"] = len(positions_after)
        result["open_orders_after_count"] = len(orders_after)
        result["flatness_reconciled"] = reconciled

        if not reconciled:
            result["classification"] = "cleanup_reconciliation_unresolved"
            _write_receipt(receipt_path, result)
            return result

        result["classification"] = "cleanup_successful"
        result["completed_at_utc"] = datetime.now(UTC).isoformat()
        _write_receipt(receipt_path, result)
        return result

    except PreflightCheckError as exc:
        result["classification"] = str(exc)
        _write_receipt(receipt_path, result)
        return result
    except Exception as exc:
        result["classification"] = f"cleanup_exception_{exc.__class__.__name__}"
        _write_receipt(receipt_path, result)
        return result


def _write_receipt(path: Path, payload: dict[str, Any]) -> None:
    temp_path = path.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    temp_path.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded Alpaca paper account baseline cleanup.")
    parser.add_argument("--output-root", default=str(DEFAULT_CLEANUP_OUTPUT_ROOT), help="Output directory path.")
    parser.add_argument("--paper-cleanup-authorized", action="store_true", help="Authorize paper account cleanup.")
    parser.add_argument("--allow-network", action="store_true", help="Allow network access to paper endpoint.")
    args = parser.parse_args()

    res = run_crypto_paper_account_cleanup(
        output_root=args.output_root,
        paper_cleanup_authorized=args.paper_cleanup_authorized,
        allow_network=args.allow_network,
    )
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
