"""V5.33.1 Bounded read-only paper broker observation adapter.

This module performs a single, bounded, explicitly authorized, read-only paper
account observation for BTCUSD, producing cross-bound receipts.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence, cast

from algotrader.errors import ValidationError
from algotrader.execution.alpaca_client import PaperObservationReader

PRODUCTION_OBSERVATION_SCHEMA = "v5_33_production_broker_observation_receipt_v1"
PRODUCTION_INVOCATION_SCHEMA = "v5_33_production_invocation_receipt_v1"
OFFLINE_FIXTURE_SCHEMA = "v5_33_offline_fixture_replay_receipt_v1"
ADAPTER_VERSION = "1.0"
TARGET_SYMBOL = "BTCUSD"
SUPPORTED_ASSET_CLASS = "crypto"
EXPECTED_PAPER_ENDPOINT = "https://paper-api.alpaca.markets"

class PreflightCheckError(ValidationError):
    """Raised when any preflight safety check fails."""
    pass

class BrokerObservationError(ValidationError):
    """Raised when broker state cannot be observed or fails checks."""
    def __init__(
        self,
        message: str,
        *,
        invocation_receipt: dict[str, Any] | None = None,
        failure_receipt: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self._invocation_receipt = invocation_receipt
        self._failure_receipt = failure_receipt

    @property
    def invocation_receipt(self) -> dict[str, Any] | None:
        return self._invocation_receipt

    @property
    def failure_receipt(self) -> dict[str, Any] | None:
        return self._failure_receipt


def _canonical_account_identity(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value).lower()

    val_str = str(value).strip()
    if not val_str:
        return None

    try:
        parsed = uuid.UUID(val_str)
        return str(parsed).lower()
    except (ValueError, TypeError, AttributeError):
        pass

    return val_str


def compute_source_bundle_digest(repo_root: Path) -> tuple[str, dict[str, str]]:
    import subprocess

    relative_paths = [
        "src/algotrader/execution/crypto_read_only_paper_observation_adapter.py",
        "src/algotrader/execution/alpaca_sdk_client.py",
        "src/algotrader/execution/alpaca_client.py",
        "src/algotrader/cli.py",
        "src/algotrader/execution/crypto_supervised_readiness_trial.py",
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
        "scripts/run_crypto_paper_broker_observation.ps1",
        "scripts/run_v535_unattended_readonly.ps1",
        "scripts/run_v536_windows_host_canary.ps1",
        "scripts/provision_v536_windows_credential.ps1",
        "scripts/launch_v536_credential_provisioning.py",
        "scripts/consume_crypto_observation_receipt.ps1",
        "scripts/verify_crypto_preflight.ps1",
        "scripts/verify_crypto_readiness_replay.ps1",
        "docs/design/v5_35_secure_unattended_read_only_acceptance_contract.md",
        "docs/design/v5_35_credential_provider_and_threat_boundary.md",
        "docs/design/v5_36_windows_host_commissioning_canary_acceptance_contract.md",
        "docs/design/v5_36_credential_provisioning_and_windows_task_boundary.md",
        "docs/design/v5_36_1_credential_writer_diagnostic_repair_contract.md",
        "docs/design/v5_36_2_exact_runtime_source_binding_repair_contract.md",
        "docs/design/v5_36_3_masked_provisioning_input_repair_contract.md",
        "docs/design/crypto_tournament_v2_oos_scheduler_task.xml"
    ]
    manifest = {}
    h = hashlib.sha256()
    for rel_path in sorted(relative_paths):
        full_path = repo_root / rel_path
        if not full_path.is_file():
            raise PreflightCheckError("required_manifest_file_missing")

        content = full_path.read_bytes()
        normalized_content = content.replace(b"\r\n", b"\n")

        try:
            res = subprocess.run(
                ["git", "show", f"HEAD:{rel_path}"],
                cwd=repo_root,
                capture_output=True,
                timeout=10,
                check=False
            )
            if res.returncode == 0:
                committed_bytes = res.stdout.replace(b"\r\n", b"\n")
                if committed_bytes != normalized_content:
                    raise PreflightCheckError("source_bundle_mismatch")
        except PreflightCheckError:
            raise
        except Exception:
            pass

        file_hash = hashlib.sha256(normalized_content).hexdigest()
        manifest[rel_path] = file_hash
        h.update(f"{rel_path}:{file_hash}\n".encode("utf-8"))

    return h.hexdigest(), manifest


def get_source_provenance(repo_root: Path) -> dict[str, Any]:
    import subprocess

    def run_git(args: list[str]) -> str:
        try:
            res = subprocess.run(
                ["git"] + args,
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )
            if res.returncode != 0:
                raise RuntimeError("git_cmd_failed")
            return res.stdout.strip()
        except FileNotFoundError as exc:
            raise PreflightCheckError("repository_unavailable") from exc
        except RuntimeError as exc:
            raise exc

    try:
        commit_sha = run_git(["rev-parse", "HEAD"])
    except PreflightCheckError:
        raise
    except Exception as exc:
        raise PreflightCheckError("commit_unresolved") from exc

    if not commit_sha or len(commit_sha) != 40:
        raise PreflightCheckError("commit_unresolved")

    try:
        tree_sha = run_git(["rev-parse", "HEAD^{tree}"])
    except PreflightCheckError:
        raise
    except Exception as exc:
        raise PreflightCheckError("tree_unresolved") from exc

    if not tree_sha or len(tree_sha) != 40:
        raise PreflightCheckError("tree_unresolved")

    try:
        branch_ref = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        branch_or_detached = "detached" if branch_ref == "HEAD" or not branch_ref else branch_ref
    except Exception:
        branch_or_detached = "detached"

    try:
        porcelain = run_git(["status", "--porcelain=v1", "--untracked-files=all"])
    except PreflightCheckError:
        raise
    except Exception as exc:
        raise PreflightCheckError("repository_unavailable") from exc

    if porcelain:
        raise PreflightCheckError("source_worktree_dirty")

    try:
        bundle_digest, bundle_manifest = compute_source_bundle_digest(repo_root)
    except PreflightCheckError:
        raise
    except FileNotFoundError as exc:
        raise PreflightCheckError("required_manifest_file_missing") from exc
    except Exception as exc:
        raise PreflightCheckError("source_bundle_mismatch") from exc

    return {
        "source_commit_sha": commit_sha,
        "source_tree_sha": tree_sha,
        "source_worktree_clean": True,
        "source_branch_or_detached": branch_or_detached,
        "adapter_source_bundle_sha256": bundle_digest,
        "source_bundle_manifest": bundle_manifest,
    }



def validate_preflight_gates(
    *,
    app_profile: str | None,
    endpoint: str | None,
    key_id: str | None,
    secret_key: str | None,
    expected_account_id: str | None,
    paper_broker_read_authorized: bool,
    allow_network: bool,
) -> None:
    if not app_profile or app_profile.strip().lower() != "paper":
        raise PreflightCheckError("preflight_failed_profile_not_paper")

    if not endpoint:
        raise PreflightCheckError("preflight_failed_endpoint_missing")
    normalized_endpoint = endpoint.strip().lower().rstrip("/")
    if normalized_endpoint != EXPECTED_PAPER_ENDPOINT:
        raise PreflightCheckError("preflight_failed_endpoint_not_paper")

    if not key_id or not key_id.strip() or not secret_key or not secret_key.strip():
        raise PreflightCheckError("preflight_failed_credentials_incomplete")

    if not expected_account_id or not expected_account_id.strip():
        raise PreflightCheckError("preflight_failed_expected_account_missing")

    if not paper_broker_read_authorized:
        raise PreflightCheckError("preflight_failed_not_authorized")

    if not allow_network:
        raise PreflightCheckError("preflight_failed_network_blocked")


def get_production_preflight_inputs() -> dict[str, Any]:
    env = os.environ
    app_profile = env.get("APP_PROFILE")

    key_id = None
    secret_key = None
    if env.get("ALPACA_API_KEY") and (env.get("ALPACA_SECRET_KEY") or env.get("ALPACA_API_SECRET_KEY")):
        key_id = env.get("ALPACA_API_KEY")
        secret_key = env.get("ALPACA_SECRET_KEY") or env.get("ALPACA_API_SECRET_KEY")
    elif env.get("APCA_API_KEY_ID") and env.get("APCA_API_SECRET_KEY"):
        key_id = env.get("APCA_API_KEY_ID")
        secret_key = env.get("APCA_API_SECRET_KEY")

    expected_account_id = env.get("ALPACA_EXPECTED_PAPER_ACCOUNT_ID")

    endpoint = None
    for var_name in ("ALPACA_PAPER_BASE_URL", "APCA_API_BASE_URL", "ALPACA_BASE_URL"):
        if var_name in env:
            endpoint = env.get(var_name)
            break

    return {
        "app_profile": app_profile,
        "endpoint": endpoint,
        "key_id": key_id,
        "secret_key": secret_key,
        "expected_account_id": expected_account_id,
    }


def classify_transport_category(exc: Exception) -> str:
    cause = exc.__cause__
    target = cause if cause is not None else exc

    # Check status code properties
    status_code = None
    for attr in ("status_code", "code"):
        val = getattr(target, attr, None)
        if isinstance(val, int):
            status_code = val
            break
        elif val is not None:
            try:
                status_code = int(val)
                break
            except (ValueError, TypeError):
                pass

    if status_code is None:
        response = getattr(target, "response", None)
        if response is not None:
            val = getattr(response, "status_code", None)
            if isinstance(val, int):
                status_code = val
            elif val is not None:
                try:
                    status_code = int(val)
                except (ValueError, TypeError):
                    pass

    if status_code is not None:
        if status_code == 401:
            return "authentication_rejected"
        if status_code == 403:
            return "authorization_rejected"
        if status_code == 429:
            return "rate_limited"
        if 500 <= status_code <= 599:
            return "upstream_server_error"

    # Check exception class name (NEVER inspecting str(exc))
    class_name = target.__class__.__name__

    if class_name in (
        "TimeoutError",
        "Timeout",
        "ConnectTimeout",
        "ReadTimeout",
        "SocketTimeout",
    ) or "timeout" in class_name.lower():
        return "timeout"

    if class_name != "ValidationError":
        if class_name in (
            "ConnectionError",
            "ConnectionRefusedError",
            "ConnectionResetError",
            "ConnectionAbortedError",
            "ConnectError",
            "NewConnectionError",
            "MaxRetryError",
            "SSLError",
        ) or "connection" in class_name.lower() or "connect" in class_name.lower() or "ssl" in class_name.lower():
            return "connection_failed"

    if class_name in (
        "JSONDecodeError",
        "DecodeError",
        "ParseError",
        "ContentDecodingError",
    ) or "decode" in class_name.lower() or "parse" in class_name.lower():
        return "malformed_response"

    if class_name in ("KeyError", "AttributeError", "TypeError", "IndexError"):
        return "malformed_response"

    if class_name in ("APIError", "APIRequestError", "AlpacaSdkClientReadError"):
        return "unknown_sdk_failure"

    return "unknown_sdk_failure"


def _validate_account(raw_account: Any, expected_account_id: str | None) -> str | None:
    canon_id = _canonical_account_identity(_get_attr_or_key(raw_account, "account_id") or _get_attr_or_key(raw_account, "id"))
    canon_num = _canonical_account_identity(_get_attr_or_key(raw_account, "account_number"))

    if not canon_id and not canon_num:
        return "account_id_missing"

    if expected_account_id:
        canon_expected = _canonical_account_identity(expected_account_id)
        if not canon_expected:
            return "account_id_missing"
        account_matched = (canon_id is not None and canon_id == canon_expected) or (canon_num is not None and canon_num == canon_expected)
        if not account_matched:
            return "account_mismatch"

    status = _get_attr_or_key(raw_account, "status")
    status_str = _to_string_value(status)
    if not status_str or status_str.upper() != "ACTIVE":
        return "account_inactive"

    if _get_attr_or_key(raw_account, "trading_blocked") is not False:
        return "trading_blocked"

    if _get_attr_or_key(raw_account, "account_blocked") is not False:
        return "account_blocked"

    for suspended_key in ("suspended", "transact_blocked"):
        val = _get_attr_or_key(raw_account, suspended_key)
        if val is not None and val is not False:
            return f"account_{suspended_key}"

    return None


def _validate_positions(raw_positions: Any) -> str | None:
    if not isinstance(raw_positions, Sequence) or isinstance(raw_positions, (str, bytes)):
        return "positions_not_sequence"

    seen_symbols = set()
    for pos in raw_positions:
        p_symbol = _get_attr_or_key(pos, "symbol")
        p_qty = _get_attr_or_key(pos, "qty")
        p_avg_price = _get_attr_or_key(pos, "average_entry_price") or _get_attr_or_key(pos, "avg_entry_price")
        p_market_value = _get_attr_or_key(pos, "market_value")

        if not p_symbol:
            return "position_symbol_missing"
        if p_qty is None:
            return "position_qty_missing"

        try:
            Decimal(str(p_qty))
            Decimal(str(p_avg_price or 0))
            Decimal(str(p_market_value or 0))
        except (ValueError, TypeError):
            return "position_numeric_field_invalid"

        norm_symbol = p_symbol.replace("/", "").upper()
        if norm_symbol in seen_symbols:
            return "position_duplicate_symbol"
        seen_symbols.add(norm_symbol)

        if norm_symbol != TARGET_SYMBOL:
            return "position_unexpected_exposure"

    return None


def _validate_orders(raw_orders: Any) -> str | None:
    if not isinstance(raw_orders, Sequence) or isinstance(raw_orders, (str, bytes)):
        return "orders_not_sequence"

    seen_order_ids = set()
    seen_client_order_ids = set()
    for order in raw_orders:
        o_id = _get_attr_or_key(order, "order_id") or _get_attr_or_key(order, "id")
        o_client_id = _get_attr_or_key(order, "client_order_id")
        o_symbol = _get_attr_or_key(order, "symbol")
        o_status = _get_attr_or_key(order, "status")
        o_qty = _get_attr_or_key(order, "qty")
        o_side = _get_attr_or_key(order, "side")

        o_status_str = _to_string_value(o_status)
        o_side_str = _to_string_value(o_side)

        if not o_id:
            return "order_id_missing"
        if not o_client_id:
            return "order_client_id_missing"
        if not o_symbol:
            return "order_symbol_missing"
        if not o_status_str:
            return "order_status_missing"
        if not o_side_str:
            return "order_side_missing"

        if o_status_str.lower() not in (
            "open", "new", "accepted", "partially_filled", "pending_new", "accepted_for_bidding", "held"
        ):
            return "order_status_not_open"

        norm_symbol = o_symbol.replace("/", "").upper()
        if norm_symbol != TARGET_SYMBOL:
            return "order_unexpected_symbol"

        if o_side_str.lower() not in ("buy", "sell"):
            return "order_side_invalid"

        if o_id in seen_order_ids:
            return "order_duplicate_id"
        if o_client_id in seen_client_order_ids:
            return "order_duplicate_client_id"
        seen_order_ids.add(o_id)
        seen_client_order_ids.add(o_client_id)

    return None


def _validate_asset(raw_asset: Any) -> str | None:
    if raw_asset is None:
        return "asset_missing"

    a_symbol = _get_attr_or_key(raw_asset, "symbol")
    a_tradable = _get_attr_or_key(raw_asset, "tradable")
    a_orderable = _get_attr_or_key(raw_asset, "orderable")
    a_class = _get_attr_or_key(raw_asset, "asset_class") or _get_attr_or_key(raw_asset, "class")
    a_class_str = _to_string_value(a_class)

    if not a_symbol or a_symbol.replace("/", "").upper() != TARGET_SYMBOL:
        return "asset_symbol_mismatch"

    if not a_class_str or a_class_str.lower() != SUPPORTED_ASSET_CLASS:
        return "asset_class_invalid"

    if a_tradable is not True:
        return "asset_not_tradable"
    if a_orderable is not True:
        return "asset_not_orderable"

    return None


def perform_genuine_paper_observation(
    *,
    paper_broker_read_authorized: bool,
    allow_network: bool,
    repo_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Production entrypoint constructing concrete client after all gates pass."""
    inputs = get_production_preflight_inputs()

    # Run preflight gates
    validate_preflight_gates(
        app_profile=inputs["app_profile"],
        endpoint=inputs["endpoint"],
        key_id=inputs["key_id"],
        secret_key=inputs["secret_key"],
        expected_account_id=inputs["expected_account_id"],
        paper_broker_read_authorized=paper_broker_read_authorized,
        allow_network=allow_network,
    )

    # Establish clean source provenance BEFORE SDK client construction
    provenance = get_source_provenance(repo_root)

    # Initialize client locally after gates pass
    from algotrader.config import AlpacaPaperConfig
    from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient

    config = AlpacaPaperConfig(
        app_profile="paper",
        alpaca_api_key=inputs["key_id"],
        alpaca_secret_key=inputs["secret_key"],
        alpaca_paper_base_url=EXPECTED_PAPER_ENDPOINT,
    )
    client: PaperObservationReader = AlpacaSdkClient(config)

    invocation_id = str(uuid.uuid4())
    observation_start_utc = datetime.now(UTC)

    stage_records = {
        "account": {
            "attempt_count": 0,
            "completion_count": 0,
            "started_at_utc": None,
            "completed_at_utc": None,
            "read_classification": None,
            "validation_classification": None,
            "validation_subcode": None
        },
        "positions": {
            "attempt_count": 0,
            "completion_count": 0,
            "started_at_utc": None,
            "completed_at_utc": None,
            "read_classification": None,
            "validation_classification": None,
            "validation_subcode": None
        },
        "open_orders": {
            "attempt_count": 0,
            "completion_count": 0,
            "started_at_utc": None,
            "completed_at_utc": None,
            "read_classification": None,
            "validation_classification": None,
            "validation_subcode": None
        },
        "target_asset": {
            "attempt_count": 0,
            "completion_count": 0,
            "started_at_utc": None,
            "completed_at_utc": None,
            "read_classification": None,
            "validation_classification": None,
            "validation_subcode": None
        }
    }

    raw_account = None
    raw_positions = None
    raw_orders = None
    raw_asset = None

    terminal_failure_stage = None
    terminal_stable_classification = None
    sanitized_transport_category = "not_applicable"

    def fmt_time(dt: datetime | None) -> str | None:
        return dt.isoformat() if dt is not None else None

    try:
        # 1. Account
        stage_records["account"]["attempt_count"] += 1
        stage_records["account"]["started_at_utc"] = fmt_time(datetime.now(UTC))
        try:
            raw_account = client.get_account()
            stage_records["account"]["completion_count"] += 1
            stage_records["account"]["completed_at_utc"] = fmt_time(datetime.now(UTC))
            stage_records["account"]["read_classification"] = "success"
        except Exception as exc:
            stage_records["account"]["read_classification"] = "account_read_failed"
            terminal_failure_stage = "account"
            terminal_stable_classification = "account_read_failed"
            sanitized_transport_category = classify_transport_category(exc)
            raise BrokerObservationError("account_read_failed") from exc

        acc_err = _validate_account(raw_account, inputs["expected_account_id"])
        if acc_err is not None:
            stage_records["account"]["validation_classification"] = "account_validation_failed"
            stage_records["account"]["validation_subcode"] = acc_err
            terminal_failure_stage = "account"
            terminal_stable_classification = "account_validation_failed"
            raise BrokerObservationError("account_validation_failed")
        stage_records["account"]["validation_classification"] = "success"

        # 2. Positions
        stage_records["positions"]["attempt_count"] += 1
        stage_records["positions"]["started_at_utc"] = fmt_time(datetime.now(UTC))
        try:
            raw_positions = client.get_positions()
            stage_records["positions"]["completion_count"] += 1
            stage_records["positions"]["completed_at_utc"] = fmt_time(datetime.now(UTC))
            stage_records["positions"]["read_classification"] = "success"
        except Exception as exc:
            stage_records["positions"]["read_classification"] = "positions_read_failed"
            terminal_failure_stage = "positions"
            terminal_stable_classification = "positions_read_failed"
            sanitized_transport_category = classify_transport_category(exc)
            raise BrokerObservationError("positions_read_failed") from exc

        pos_err = _validate_positions(raw_positions)
        if pos_err is not None:
            stage_records["positions"]["validation_classification"] = "positions_validation_failed"
            stage_records["positions"]["validation_subcode"] = pos_err
            terminal_failure_stage = "positions"
            terminal_stable_classification = "positions_validation_failed"
            raise BrokerObservationError("positions_validation_failed")
        stage_records["positions"]["validation_classification"] = "success"

        # 3. Open Orders
        stage_records["open_orders"]["attempt_count"] += 1
        stage_records["open_orders"]["started_at_utc"] = fmt_time(datetime.now(UTC))
        try:
            from algotrader.execution.alpaca_client import AlpacaRecentOrderQuery
            recent_query = AlpacaRecentOrderQuery(
                status_filter="open",
                limit=100,
                direction="desc",
            )
            raw_orders = client.get_orders(recent_query)
            stage_records["open_orders"]["completion_count"] += 1
            stage_records["open_orders"]["completed_at_utc"] = fmt_time(datetime.now(UTC))
            stage_records["open_orders"]["read_classification"] = "success"
        except Exception as exc:
            stage_records["open_orders"]["read_classification"] = "open_orders_read_failed"
            terminal_failure_stage = "open_orders"
            terminal_stable_classification = "open_orders_read_failed"
            sanitized_transport_category = classify_transport_category(exc)
            raise BrokerObservationError("open_orders_read_failed") from exc

        orders_err = _validate_orders(raw_orders)
        if orders_err is not None:
            stage_records["open_orders"]["validation_classification"] = "open_orders_validation_failed"
            stage_records["open_orders"]["validation_subcode"] = orders_err
            terminal_failure_stage = "open_orders"
            terminal_stable_classification = "open_orders_validation_failed"
            raise BrokerObservationError("open_orders_validation_failed")
        stage_records["open_orders"]["validation_classification"] = "success"

        # 4. Target Asset
        stage_records["target_asset"]["attempt_count"] += 1
        stage_records["target_asset"]["started_at_utc"] = fmt_time(datetime.now(UTC))
        try:
            raw_asset = client.get_asset(TARGET_SYMBOL)
            stage_records["target_asset"]["completion_count"] += 1
            stage_records["target_asset"]["completed_at_utc"] = fmt_time(datetime.now(UTC))
            stage_records["target_asset"]["read_classification"] = "success"
        except Exception as exc:
            stage_records["target_asset"]["read_classification"] = "target_asset_read_failed"
            terminal_failure_stage = "target_asset"
            terminal_stable_classification = "target_asset_read_failed"
            sanitized_transport_category = classify_transport_category(exc)
            raise BrokerObservationError("target_asset_read_failed") from exc

        asset_err = _validate_asset(raw_asset)
        if asset_err is not None:
            stage_records["target_asset"]["validation_classification"] = "target_asset_validation_failed"
            stage_records["target_asset"]["validation_subcode"] = asset_err
            terminal_failure_stage = "target_asset"
            terminal_stable_classification = "target_asset_validation_failed"
            raise BrokerObservationError("target_asset_validation_failed")
        stage_records["target_asset"]["validation_classification"] = "success"

    except BrokerObservationError as bo_exc:
        observation_completion_utc = datetime.now(UTC)
        any_attempts = (
            stage_records["account"]["attempt_count"] > 0 or
            stage_records["positions"]["attempt_count"] > 0 or
            stage_records["open_orders"]["attempt_count"] > 0 or
            stage_records["target_asset"]["attempt_count"] > 0
        )
        inv_receipt = {
            "schema_version": PRODUCTION_INVOCATION_SCHEMA,
            "invocation_id": invocation_id,
            "adapter_version": ADAPTER_VERSION,
            "source_commit_sha": provenance["source_commit_sha"],
            "source_tree_sha": provenance["source_tree_sha"],
            "source_worktree_clean": provenance["source_worktree_clean"],
            "source_branch_or_detached": provenance["source_branch_or_detached"],
            "adapter_source_bundle_sha256": provenance["adapter_source_bundle_sha256"],
            "source_bundle_manifest": provenance["source_bundle_manifest"],
            "command_source_identity": "crypto-paper-broker-observation",
            "normalized_paper_endpoint": EXPECTED_PAPER_ENDPOINT,
            "preflight_booleans": {
                "app_profile_present": bool(inputs.get("app_profile")),
                "endpoint_present": bool(inputs.get("endpoint")),
                "key_id_present": bool(inputs.get("key_id")),
                "secret_key_present": bool(inputs.get("secret_key")),
                "expected_account_id_present": bool(inputs.get("expected_account_id")),
                "paper_broker_read_authorized": paper_broker_read_authorized,
                "allow_network": allow_network,
            },
            "observation_start_utc": fmt_time(observation_start_utc),
            "observation_completion_utc": fmt_time(observation_completion_utc),
            "call_counters": {
                "account_read_count": stage_records["account"]["completion_count"],
                "positions_read_count": stage_records["positions"]["completion_count"],
                "orders_read_count": stage_records["open_orders"]["completion_count"],
                "target_asset_read_count": stage_records["target_asset"]["completion_count"]
            },
            "stage_records": stage_records,
            "terminal_failure_stage": terminal_failure_stage,
            "terminal_stable_classification": terminal_stable_classification,
            "sanitized_transport_category": sanitized_transport_category,
            "safety_booleans": {
                "broker_read_completed": False,
                "network_access_attempted": any_attempts,
                "broker_mutation_performed": False,
                "paper_submit_performed": False,
                "live_authorized": False,
                "network_authorization_present": paper_broker_read_authorized,
                "network_access_authorized": allow_network,
            }
        }
        # Finalize and hash invocation receipt
        canonical_inv_str = json.dumps(inv_receipt, sort_keys=True, separators=(",", ":"))
        inv_receipt["canonical_invocation_sha256"] = hashlib.sha256(canonical_inv_str.encode("utf-8")).hexdigest()

        # Build failure receipt
        fail_receipt = {
            "schema_version": "v5_33_production_failure_receipt_v1",
            "invocation_id": invocation_id,
            "stable_blocked_classification": "blocked_observation_failed",
            "terminal_failure_stage": terminal_failure_stage,
            "terminal_stable_classification": terminal_stable_classification,
            "sanitized_transport_category": sanitized_transport_category,
            "invocation_receipt_sha256": inv_receipt["canonical_invocation_sha256"],
            "safety_booleans": {
                "broker_read_completed": False,
                "network_access_attempted": any_attempts,
                "broker_mutation_performed": False,
                "paper_submit_performed": False,
                "live_authorized": False
            }
        }
        # Hash failure receipt
        canonical_fail_str = json.dumps(fail_receipt, sort_keys=True, separators=(",", ":"))
        fail_receipt["canonical_receipt_sha256"] = hashlib.sha256(canonical_fail_str.encode("utf-8")).hexdigest()

        raise BrokerObservationError(
            terminal_stable_classification,
            invocation_receipt=inv_receipt,
            failure_receipt=fail_receipt
        ) from bo_exc

    # Process and sanitize observations
    observation_completion_utc = datetime.now(UTC)
    observation_receipt = _process_raw_observations(
        raw_account=raw_account,
        raw_positions=raw_positions,
        raw_orders=raw_orders,
        raw_asset=raw_asset,
        expected_account_id=inputs["expected_account_id"],
        is_fixture=False,
    )

    # Build invocation receipt for success
    inv_receipt = {
        "schema_version": PRODUCTION_INVOCATION_SCHEMA,
        "invocation_id": invocation_id,
        "adapter_version": ADAPTER_VERSION,
        "source_commit_sha": provenance["source_commit_sha"],
        "source_tree_sha": provenance["source_tree_sha"],
        "source_worktree_clean": provenance["source_worktree_clean"],
        "source_branch_or_detached": provenance["source_branch_or_detached"],
        "adapter_source_bundle_sha256": provenance["adapter_source_bundle_sha256"],
        "source_bundle_manifest": provenance["source_bundle_manifest"],
        "command_source_identity": "crypto-paper-broker-observation",
        "normalized_paper_endpoint": EXPECTED_PAPER_ENDPOINT,
        "preflight_booleans": {
            "app_profile_present": bool(inputs.get("app_profile")),
            "endpoint_present": bool(inputs.get("endpoint")),
            "key_id_present": bool(inputs.get("key_id")),
            "secret_key_present": bool(inputs.get("secret_key")),
            "expected_account_id_present": bool(inputs.get("expected_account_id")),
            "paper_broker_read_authorized": paper_broker_read_authorized,
            "allow_network": allow_network,
        },
        "observation_start_utc": fmt_time(observation_start_utc),
        "observation_completion_utc": fmt_time(observation_completion_utc),
        "call_counters": {
            "account_read_count": 1,
            "positions_read_count": 1,
            "orders_read_count": 1,
            "target_asset_read_count": 1
        },
        "stage_records": stage_records,
        "read_completion_status": {
            "account_read_completed": True,
            "positions_read_completed": True,
            "open_orders_read_completed": True,
            "exact_target_asset_read_completed": True
        },
        "safety_booleans": {
            "network_authorization_present": paper_broker_read_authorized,
            "network_access_attempted": allow_network,
            "broker_read_completed": True,
            "paper_submit_authorized": False,
            "paper_submit_performed": False,
            "broker_mutation_authorized": False,
            "broker_mutation_performed": False,
            "live_authorized": False
        },
        "observation_receipt_sha256": observation_receipt["canonical_receipt_sha256"]
    }

    # Hashing invocation receipt
    canonical_inv_str = json.dumps(inv_receipt, sort_keys=True, separators=(",", ":"))
    inv_receipt["canonical_invocation_sha256"] = hashlib.sha256(canonical_inv_str.encode("utf-8")).hexdigest()

    return observation_receipt, inv_receipt


def perform_fixture_observation_evaluation(
    mock_client: PaperObservationReader,
    *,
    expected_account_id: str | None,
    paper_broker_read_authorized: bool,
    allow_network: bool,
) -> dict[str, Any]:
    """Fixture entrypoint accepts injected client, returning fixture receipt capped at R1."""
    if not expected_account_id or not expected_account_id.strip():
        raise PreflightCheckError("preflight_failed_expected_account_missing")

    try:
        try:
            raw_account = mock_client.get_account()
        except Exception as exc:
            raise BrokerObservationError("account_read_failed") from exc

        acc_err = _validate_account(raw_account, expected_account_id)
        if acc_err is not None:
            raise BrokerObservationError("account_validation_failed")

        try:
            raw_positions = mock_client.get_positions()
        except Exception as exc:
            raise BrokerObservationError("positions_read_failed") from exc

        pos_err = _validate_positions(raw_positions)
        if pos_err is not None:
            raise BrokerObservationError("positions_validation_failed")

        try:
            raw_orders = mock_client.get_orders(None)
        except Exception as exc:
            raise BrokerObservationError("open_orders_read_failed") from exc

        orders_err = _validate_orders(raw_orders)
        if orders_err is not None:
            raise BrokerObservationError("open_orders_validation_failed")

        try:
            raw_asset = mock_client.get_asset(TARGET_SYMBOL)
        except Exception as exc:
            raise BrokerObservationError("target_asset_read_failed") from exc

        asset_err = _validate_asset(raw_asset)
        if asset_err is not None:
            raise BrokerObservationError("target_asset_validation_failed")

    except BrokerObservationError:
        raise
    except Exception as exc:
        raise BrokerObservationError("unknown_sdk_failure") from exc

    return _process_raw_observations(
        raw_account=raw_account,
        raw_positions=raw_positions,
        raw_orders=raw_orders,
        raw_asset=raw_asset,
        expected_account_id=expected_account_id,
        is_fixture=True,
    )


def _process_raw_observations(
    *,
    raw_account: Any,
    raw_positions: Sequence[Any],
    raw_orders: Sequence[Any],
    raw_asset: Any,
    expected_account_id: str,
    is_fixture: bool,
) -> dict[str, Any]:
    status = _get_attr_or_key(raw_account, "status")
    status_str = _to_string_value(status) or ""
    currency = _get_attr_or_key(raw_account, "currency") or "USD"

    account_id = _get_attr_or_key(raw_account, "account_id") or _get_attr_or_key(raw_account, "id")
    account_number = _get_attr_or_key(raw_account, "account_number")
    fingerprint_input = f"{account_id or ''}:{account_number or ''}"
    account_fingerprint = hashlib.sha256(fingerprint_input.encode("utf-8")).hexdigest()

    # Normalize positions
    normalized_positions: list[dict[str, Any]] = []
    unexpected_exposure_classification = "clean"
    for pos in raw_positions:
        p_symbol = _get_attr_or_key(pos, "symbol")
        p_qty = _get_attr_or_key(pos, "qty")
        p_avg_price = _get_attr_or_key(pos, "average_entry_price") or _get_attr_or_key(pos, "avg_entry_price")
        p_market_value = _get_attr_or_key(pos, "market_value")

        normalized_sym = p_symbol.replace("/", "").upper()
        if normalized_sym != TARGET_SYMBOL:
            unexpected_exposure_classification = "unexpected_exposure_detected"

        normalized_positions.append({
            "symbol": normalized_sym,
            "quantity": str(Decimal(str(p_qty)).normalize()),
            "average_price": str(Decimal(str(p_avg_price or 0)).normalize()),
            "market_value": str(Decimal(str(p_market_value or 0)).normalize()),
        })

    # Normalize open orders
    normalized_orders: list[dict[str, Any]] = []
    for order in raw_orders:
        o_id = _get_attr_or_key(order, "order_id") or _get_attr_or_key(order, "id")
        o_client_id = _get_attr_or_key(order, "client_order_id")
        o_symbol = _get_attr_or_key(order, "symbol")
        o_status = _get_attr_or_key(order, "status")
        o_qty = _get_attr_or_key(order, "qty")
        o_notional = _get_attr_or_key(order, "notional")
        o_side = _get_attr_or_key(order, "side")

        o_status_str = _to_string_value(o_status)
        o_side_str = _to_string_value(o_side)

        normalized_sym = o_symbol.replace("/", "").upper()
        if normalized_sym != TARGET_SYMBOL:
            unexpected_exposure_classification = "unexpected_exposure_detected"

        normalized_orders.append({
            "order_id": o_id,
            "client_order_id": o_client_id,
            "symbol": normalized_sym,
            "status": o_status_str.lower() if o_status_str else "",
            "quantity": str(Decimal(str(o_qty)).normalize()) if o_qty is not None else None,
            "notional": str(Decimal(str(o_notional)).normalize()) if o_notional is not None else None,
            "side": o_side_str.lower() if o_side_str else None,
        })

    positions_truncated = len(normalized_positions) >= 100
    orders_truncated = len(normalized_orders) >= 100

    observed_at = datetime.now(UTC)

    schema = OFFLINE_FIXTURE_SCHEMA if is_fixture else PRODUCTION_OBSERVATION_SCHEMA
    source_classification = "fixture_replay" if is_fixture else "genuine_alpaca_paper_observation"
    authority = "fixture_replay_validated" if is_fixture else None

    receipt: dict[str, Any] = {
        "schema_version": schema,
        "adapter_version": ADAPTER_VERSION,
        "observation_id": str(uuid.uuid4()),
        "observed_at_utc": observed_at.isoformat(),
        "source_classification": source_classification,
        "paper_endpoint_classification": EXPECTED_PAPER_ENDPOINT,
        "expected_account_match": True,
        "sanitized_account_fingerprint": account_fingerprint,
        "target_symbol": TARGET_SYMBOL,
        "target_asset_class": SUPPORTED_ASSET_CLASS,
        "target_tradability": True,
        "target_orderability": True,
        "account_status_fields": {
            "status": status_str.lower(),
            "trading_blocked": False,
            "account_blocked": False,
            "currency": currency.upper(),
        },
        "positions": normalized_positions,
        "open_orders": normalized_orders,
        "truncation_indicators": {
            "positions_truncated": positions_truncated,
            "orders_truncated": orders_truncated,
        },
        "ambiguity_indicators": {
            "duplicate_positions": len(raw_positions) != len({_get_attr_or_key(p, "symbol") for p in raw_positions}),
            "duplicate_client_order_ids": False,
        },
        "unexpected_exposure_classification": unexpected_exposure_classification,
        "safety_booleans": {
            "paper_submit_authorized": False,
            "paper_submit_performed": False,
            "broker_mutation_authorized": False,
            "broker_mutation_performed": False,
            "live_authorized": False,
            "network_used": not is_fixture,
        },
    }

    if authority:
        receipt["authority"] = authority

    # Generate canonical hash
    canonical_str = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    receipt["canonical_receipt_sha256"] = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    return receipt


def _get_attr_or_key(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, Mapping):
        return obj.get(key)
    try:
        return getattr(obj, key)
    except AttributeError:
        return None


def _to_string_value(val: Any) -> str | None:
    if val is None:
        return None
    if hasattr(val, "value"):
        return str(val.value)
    if hasattr(val, "name"):
        return str(val.name)
    return str(val)
