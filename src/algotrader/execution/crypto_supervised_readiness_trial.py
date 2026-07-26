"""V5.32 end-to-end supervised crypto readiness evidence trial facade."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

import algotrader.execution.crypto_read_only_paper_observation_adapter as crypto_read_only_paper_observation_adapter
from algotrader.execution.crypto_supervised_readiness_trial_core import (
    DEFAULT_CYCLE_COUNT,
    DEFAULT_DECISION_START,
    DEFAULT_OUTPUT_ROOT,
    MILESTONE_NAME,
    SCHEMA_VERSION,
    _json_safe,
    _mapping,
    run_crypto_supervised_readiness_trial as _run_crypto_supervised_readiness_trial_core,
    validate_crypto_supervised_readiness_trial,
)
from algotrader.execution.tomorrow_crypto_trader_demo_broker_client_adapter import (
    build_alpaca_read_client,
    read_paper_environment_from_os,
)


def run_crypto_supervised_readiness_trial(
    *,
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
    decision_start: datetime | str = DEFAULT_DECISION_START,
    cycle_count: int = DEFAULT_CYCLE_COUNT,
    broker_observed_readiness: bool = False,
    allow_alpaca_paper_read: bool = False,
    write_artifacts: bool = True,
    receipt_root: Path | str | None = None,
) -> dict[str, object]:
    """Facade preserving the exact existing public signature."""
    validator = _validate_offline_receipt if receipt_root is not None else None
    broker_factory = (
        build_alpaca_read_client
        if broker_observed_readiness and allow_alpaca_paper_read
        else None
    )
    environment = read_paper_environment_from_os()
    return _run_crypto_supervised_readiness_trial_core(
        output_root=output_root,
        decision_start=decision_start,
        cycle_count=cycle_count,
        broker_observed_readiness=broker_observed_readiness,
        allow_alpaca_paper_read=allow_alpaca_paper_read,
        write_artifacts=write_artifacts,
        receipt_root=receipt_root,
        receipt_validator=validator,
        broker_observed_client_factory=broker_factory,
        paper_environment=environment,
    )


def _validate_offline_receipt(receipt_root: Path | str | None) -> dict[str, Any]:
    if not receipt_root:
        return {"valid": False, "classification": "blocked_credentials_unavailable", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

    root_path = Path(receipt_root)
    obs_path = root_path / "observation_receipt.json"
    inv_path = root_path / "invocation_receipt.json"
    fail_path = root_path / "failure_receipt.json"

    has_obs = obs_path.is_file()
    has_inv = inv_path.is_file()
    has_fail = fail_path.is_file()

    # Reject mixed layouts
    if has_obs and has_fail:
        return {"valid": False, "classification": "blocked_mixed_layouts", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

    if not has_obs and not has_fail:
        return {"valid": False, "classification": "blocked_credentials_or_expected_account_unavailable", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

    # Validate Success layout
    if has_obs:
        try:
            obs_receipt = json.loads(obs_path.read_text(encoding="utf-8"))
        except Exception:
            return {"valid": False, "classification": "blocked_malformed_receipt", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        schema_version = obs_receipt.get("schema_version")

        if schema_version == "v5_33_offline_fixture_replay_receipt_v1":
            if obs_receipt.get("source_classification") == "genuine_alpaca_paper_observation":
                return {"valid": False, "classification": "blocked_not_genuine", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            r_copy = dict(obs_receipt)
            original_hash = r_copy.pop("canonical_receipt_sha256", None)
            canonical_str = json.dumps(r_copy, sort_keys=True, separators=(",", ":"))
            expected_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
            if original_hash != expected_hash:
                return {"valid": False, "classification": "blocked_receipt_tampered", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            return {
                "valid": True,
                "classification": "fixture_replay_validated",
                "broker_state_observed": False,
                "network_used": False,
                "broker_read_occurred": False,
                "receipt": obs_receipt
            }

        elif schema_version == "v5_33_production_broker_observation_receipt_v1":
            if not has_inv:
                return {"valid": False, "classification": "blocked_invocation_receipt_missing", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            try:
                inv_receipt = json.loads(inv_path.read_text(encoding="utf-8"))
            except Exception:
                return {"valid": False, "classification": "blocked_malformed_receipt", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if inv_receipt.get("schema_version") != "v5_33_production_invocation_receipt_v1":
                return {"valid": False, "classification": "blocked_malformed_receipt", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            obs_copy = dict(obs_receipt)
            obs_original_hash = obs_copy.pop("canonical_receipt_sha256", None)
            obs_canonical_str = json.dumps(obs_copy, sort_keys=True, separators=(",", ":"))
            obs_expected_hash = hashlib.sha256(obs_canonical_str.encode("utf-8")).hexdigest()
            if obs_original_hash != obs_expected_hash:
                return {"valid": False, "classification": "blocked_receipt_tampered", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            inv_copy = dict(inv_receipt)
            inv_original_hash = inv_copy.pop("canonical_invocation_sha256", None)
            inv_canonical_str = json.dumps(inv_copy, sort_keys=True, separators=(",", ":"))
            inv_expected_hash = hashlib.sha256(inv_canonical_str.encode("utf-8")).hexdigest()
            if inv_original_hash != inv_expected_hash:
                return {"valid": False, "classification": "blocked_receipt_tampered", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if inv_receipt.get("observation_receipt_sha256") != obs_original_hash:
                return {"valid": False, "classification": "blocked_cross_bind_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if obs_receipt.get("source_classification") != "genuine_alpaca_paper_observation":
                return {"valid": False, "classification": "blocked_not_genuine", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            bundle_digest = inv_receipt.get("adapter_source_bundle_sha256")
            if not bundle_digest or bundle_digest == "0" * 64:
                return {"valid": False, "classification": "blocked_source_bundle_digest_invalid", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if inv_receipt.get("source_worktree_clean") is not True:
                return {"valid": False, "classification": "blocked_source_dirty", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            repo_root = Path(".").resolve()
            try:
                local_prov = crypto_read_only_paper_observation_adapter.get_source_provenance(repo_root)
            except crypto_read_only_paper_observation_adapter.PreflightCheckError as p_err:
                return {"valid": False, "classification": f"blocked_{str(p_err)}", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}
            except Exception:
                return {"valid": False, "classification": "blocked_source_provenance_failed", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if inv_receipt.get("source_commit_sha") != local_prov["source_commit_sha"]:
                return {"valid": False, "classification": "blocked_source_commit_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if inv_receipt.get("source_tree_sha") != local_prov["source_tree_sha"]:
                return {"valid": False, "classification": "blocked_source_tree_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if bundle_digest != local_prov["adapter_source_bundle_sha256"]:
                return {"valid": False, "classification": "blocked_source_bundle_digest_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            stored_manifest = inv_receipt.get("source_bundle_manifest", {})
            if local_prov["source_bundle_manifest"] != stored_manifest:
                return {"valid": False, "classification": "blocked_source_bundle_manifest_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if obs_receipt.get("paper_endpoint_classification") != "https://paper-api.alpaca.markets":
                  return {"valid": False, "classification": "blocked_endpoint_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}
            if inv_receipt.get("normalized_paper_endpoint") != "https://paper-api.alpaca.markets":
                  return {"valid": False, "classification": "blocked_endpoint_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if not obs_receipt.get("expected_account_match"):
                return {"valid": False, "classification": "blocked_expected_account_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if obs_receipt.get("target_symbol") != "BTCUSD":
                return {"valid": False, "classification": "blocked_target_symbol_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}
            if obs_receipt.get("target_asset_class") != "crypto":
                return {"valid": False, "classification": "blocked_target_asset_class_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if not obs_receipt.get("target_tradability") or not obs_receipt.get("target_orderability"):
                return {"valid": False, "classification": "blocked_non_tradable_or_non_orderable", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            trunc = obs_receipt.get("truncation_indicators", {})
            if trunc.get("positions_truncated") or trunc.get("orders_truncated"):
                return {"valid": False, "classification": "blocked_truncation_detected", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            if obs_receipt.get("unexpected_exposure_classification") != "clean":
                return {"valid": False, "classification": "blocked_unexpected_exposure", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            ambiguity = obs_receipt.get("ambiguity_indicators", {})
            if ambiguity.get("duplicate_positions") or ambiguity.get("duplicate_client_order_ids"):
                return {"valid": False, "classification": "blocked_ambiguity_detected", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            counters = inv_receipt.get("call_counters", {})
            expected_counters = {
                "account_read_count": 1,
                "positions_read_count": 1,
                "orders_read_count": 1,
                "target_asset_read_count": 1
            }
            if counters != expected_counters:
                return {"valid": False, "classification": "blocked_invalid_call_counts", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            obs_completion = inv_receipt.get("observation_completion_utc")
            if not obs_completion:
                return {"valid": False, "classification": "blocked_freshness_check_failed", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}
            try:
                completion_dt = datetime.fromisoformat(obs_completion.replace("Z", "+00:00"))
                age = (datetime.now(UTC) - completion_dt).total_seconds()
                if age < -60 or age > 900:
                    return {"valid": False, "classification": "blocked_stale_observation", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}
            except Exception:
                return {"valid": False, "classification": "blocked_malformed_timestamp", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            safety_obs = obs_receipt.get("safety_booleans", {})
            safety_inv = inv_receipt.get("safety_booleans", {})
            if (safety_obs.get("paper_submit_authorized") or safety_obs.get("paper_submit_performed") or
                safety_obs.get("broker_mutation_authorized") or safety_obs.get("broker_mutation_performed") or
                safety_obs.get("live_authorized") or
                safety_inv.get("paper_submit_authorized") or safety_inv.get("paper_submit_performed") or
                safety_inv.get("broker_mutation_authorized") or safety_inv.get("broker_mutation_performed") or
                safety_inv.get("live_authorized")):
                return {"valid": False, "classification": "blocked_mutation_or_live_authorized", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            status_fields = obs_receipt.get("account_status_fields", {})
            if (status_fields.get("status") != "active" or
                status_fields.get("trading_blocked") is not False or
                status_fields.get("account_blocked") is not False):
                return {"valid": False, "classification": "blocked_account_inactive_or_blocked", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

            return {
                "valid": True,
                "classification": "broker_observed_no_submit_completed",
                "broker_state_observed": True,
                "network_used": True,
                "broker_read_occurred": True,
                "receipt": obs_receipt,
                "invocation": inv_receipt
            }
        else:
            return {"valid": False, "classification": "blocked_unsupported_schema", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

    # Validate Failure layout
    if has_fail:
        if not has_inv:
            return {"valid": False, "classification": "blocked_invocation_receipt_missing", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        try:
            failure_receipt = json.loads(fail_path.read_text(encoding="utf-8"))
        except Exception:
            return {"valid": False, "classification": "blocked_malformed_receipt", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        if failure_receipt.get("schema_version") != "v5_33_production_failure_receipt_v1":
            return {"valid": False, "classification": "blocked_unsupported_schema", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        # Verify failure receipt hash
        fail_copy = dict(failure_receipt)
        fail_original_hash = fail_copy.pop("canonical_receipt_sha256", None)
        fail_canonical_str = json.dumps(fail_copy, sort_keys=True, separators=(",", ":"))
        fail_expected_hash = hashlib.sha256(fail_canonical_str.encode("utf-8")).hexdigest()
        if fail_original_hash != fail_expected_hash:
            return {"valid": False, "classification": "blocked_receipt_tampered", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        # Parse and verify invocation receipt
        try:
            inv_receipt = json.loads(inv_path.read_text(encoding="utf-8"))
        except Exception:
            return {"valid": False, "classification": "blocked_malformed_receipt", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        if inv_receipt.get("schema_version") != "v5_33_production_invocation_receipt_v1":
            return {"valid": False, "classification": "blocked_malformed_receipt", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        # Verify invocation receipt hash (popping its own hash)
        inv_copy = dict(inv_receipt)
        inv_original_hash = inv_copy.pop("canonical_invocation_sha256", None)
        inv_canonical_str = json.dumps(inv_copy, sort_keys=True, separators=(",", ":"))
        inv_expected_hash = hashlib.sha256(inv_canonical_str.encode("utf-8")).hexdigest()
        if inv_original_hash != inv_expected_hash:
            return {"valid": False, "classification": "blocked_receipt_tampered", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        # Verify invocation ID equality
        if failure_receipt.get("invocation_id") != inv_receipt.get("invocation_id"):
            return {"valid": False, "classification": "blocked_invocation_id_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        # Verify invocation hash referenced by failure receipt
        if failure_receipt.get("invocation_receipt_sha256") != inv_original_hash:
            return {"valid": False, "classification": "blocked_cross_bind_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        # Source bundle check
        bundle_digest = inv_receipt.get("adapter_source_bundle_sha256")
        if not bundle_digest or bundle_digest == "0" * 64:
            return {"valid": False, "classification": "blocked_source_bundle_digest_invalid", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        if inv_receipt.get("source_worktree_clean") is not True:
            return {"valid": False, "classification": "blocked_source_dirty", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        repo_root = Path(".").resolve()
        from algotrader.execution.crypto_read_only_paper_observation_adapter import get_source_provenance, PreflightCheckError
        try:
            local_prov = crypto_read_only_paper_observation_adapter.get_source_provenance(repo_root)
        except crypto_read_only_paper_observation_adapter.PreflightCheckError as p_err:
            return {"valid": False, "classification": f"blocked_{str(p_err)}", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}
        except Exception:
            return {"valid": False, "classification": "blocked_source_provenance_failed", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        if inv_receipt.get("source_commit_sha") != local_prov["source_commit_sha"]:
            return {"valid": False, "classification": "blocked_source_commit_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        if inv_receipt.get("source_tree_sha") != local_prov["source_tree_sha"]:
            return {"valid": False, "classification": "blocked_source_tree_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        if bundle_digest != local_prov["adapter_source_bundle_sha256"]:
            return {"valid": False, "classification": "blocked_source_bundle_digest_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        stored_manifest = inv_receipt.get("source_bundle_manifest", {})
        if local_prov["source_bundle_manifest"] != stored_manifest:
            return {"valid": False, "classification": "blocked_source_bundle_manifest_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        if inv_receipt.get("normalized_paper_endpoint") != "https://paper-api.alpaca.markets":
            return {"valid": False, "classification": "blocked_endpoint_mismatch", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

        # Return valid failure layout
        return {
            "valid": True,
            "is_failure_receipt": True,
            "classification": failure_receipt.get("terminal_stable_classification") or "blocked_observation_failed",
            "terminal_failure_stage": failure_receipt.get("terminal_failure_stage"),
            "sanitized_failure_category": failure_receipt.get("sanitized_transport_category"),
            "broker_state_observed": False,
            "network_used": inv_receipt.get("safety_booleans", {}).get("network_access_attempted", False),
            "broker_read_occurred": inv_receipt.get("safety_booleans", {}).get("network_access_attempted", False),
            "invocation": inv_receipt,
            "failure": failure_receipt
        }

    return {"valid": False, "classification": "blocked_unsupported_schema", "broker_state_observed": False, "network_used": False, "broker_read_occurred": False}

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=MILESTONE_NAME)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--decision-start", default=DEFAULT_DECISION_START.isoformat())
    parser.add_argument("--cycle-count", type=int, default=DEFAULT_CYCLE_COUNT)
    parser.add_argument("--broker-observed-readiness", action="store_true")
    parser.add_argument("--allow-alpaca-paper-read", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--receipt-root", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.validate_only:
        result = validate_crypto_supervised_readiness_trial(args.output_root)
        print(json.dumps(result, sort_keys=True) if args.format == "json" else f"v5_32_validation_status={result['validation_status']}")
        return 0 if result["validation_status"] == "passed" else 1
    packet = run_crypto_supervised_readiness_trial(
        output_root=args.output_root,
        decision_start=args.decision_start,
        cycle_count=args.cycle_count,
        broker_observed_readiness=args.broker_observed_readiness,
        allow_alpaca_paper_read=args.allow_alpaca_paper_read,
        write_artifacts=True,
        receipt_root=args.receipt_root,
    )
    if args.format == "json":
        print(json.dumps(_json_safe(packet), sort_keys=True))
    else:
        print(f"v5_32_trial_classification={packet['trial_classification']}")
        print(f"v5_32_current_readiness_rung={packet['current_readiness_rung_code']}")
        print(f"v5_32_cycle_count={packet['cycle_count']}")
        print(f"v5_32_receipt_chain_hash={_mapping(packet['receipt_chain']).get('final_receipt_hash')}")
        print(f"v5_32_broker_observed_result={_mapping(packet['broker_observed_result']).get('classification')}")
        print("v5_32_paper_submit_performed=false")
        print("v5_32_broker_mutation_performed=false")
        print("v5_32_live_authorized=false")
    return 0 if packet["trial_classification"] == "accepted" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
