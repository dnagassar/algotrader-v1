"""V5.34 Bounded Alpaca paper account baseline cleanup module.

Performs exactly one bounded, exact-order-bound cleanup attempt against the
configured Alpaca paper endpoint and expected paper account to restore a
clean, flat baseline (0 open orders, 0 positions) before paper-observed OOS
burn-in.

Mutation contract:

* every mutation is bound to a pre-observed exact order id or exact position
  symbol — no account-wide bulk cancellation or bulk liquidation calls;
* each order and each position receives at most one mutation attempt;
* submission acceptance is never treated as completion — completion is proven
  only through subsequent bounded reconciliation reads;
* an existing close (exposure-reducing) order is never duplicated: the
  position it covers receives no additional close submission and the cleanup
  stops blocked if it does not resolve;
* every operation persists an exact per-operation classification, and the
  cleanup stops on the first ambiguous broker result.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from algotrader.config import AlpacaPaperConfig
from algotrader.execution.alpaca_client import AlpacaRecentOrderQuery
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient
from algotrader.execution.crypto_read_only_paper_observation_adapter import (
    EXPECTED_PAPER_ENDPOINT,
    PreflightCheckError,
    _get_attr_or_key,
    _to_string_value,
    _validate_account,
    get_production_preflight_inputs,
    get_source_provenance,
    validate_preflight_gates,
)

CLEANUP_SCHEMA_VERSION = "v5_34_paper_account_cleanup_receipt_v2"
DEFAULT_CLEANUP_OUTPUT_ROOT = Path("runs/v5_34_paper_cleanup/latest")
RECONCILIATION_MAX_READS = 10
RECONCILIATION_POLL_SECONDS = 1.0


def run_crypto_paper_account_cleanup(
    *,
    output_root: Path | str = DEFAULT_CLEANUP_OUTPUT_ROOT,
    paper_cleanup_authorized: bool = False,
    allow_network: bool = False,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Execute one bounded exact-order-bound paper account baseline cleanup."""
    root_dir = Path(repo_root or Path.cwd()).resolve()
    out_dir = Path(output_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = out_dir / "cleanup_result.json"

    result: dict[str, Any] = {
        "schema_version": CLEANUP_SCHEMA_VERSION,
        "started_at_utc": datetime.now(UTC).isoformat(),
        "completed_at_utc": None,
        "classification": "in_progress",
        "paper_cleanup_authorized": paper_cleanup_authorized,
        "allow_network": allow_network,
        "endpoint_matched": False,
        "expected_account_matched": False,
        "account_active_unblocked": False,
        "positions_before": [],
        "open_orders_before": [],
        "cancel_operations": [],
        "close_operations": [],
        "preserved_close_orders": [],
        "cancel_attempt_count": 0,
        "cancel_completion_count": 0,
        "close_attempt_count": 0,
        "close_completion_count": 0,
        "reconciliation_read_count": 0,
        "positions_after_count": None,
        "open_orders_after_count": None,
        "flatness_reconciled": False,
        "broker_mutation_performed": False,
        "source_commit_sha": None,
        "source_tree_sha": None,
        "source_worktree_clean": False,
    }

    try:
        inputs = get_production_preflight_inputs()
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

        # 1. Verify account identity and safety before any mutation.
        raw_account = client.get_account()
        acc_err = _validate_account(raw_account, inputs["expected_account_id"])
        if acc_err == "account_mismatch":
            return _finish(receipt_path, result, "account_mismatch")
        if acc_err is not None:
            return _finish(receipt_path, result, f"account_validation_failed_{acc_err}")

        result["expected_account_matched"] = True
        result["account_active_unblocked"] = True

        # 2. Pre-observe exact broker state; mutations bind only to this.
        positions_before = _normalize_positions(client.get_positions() or [])
        orders_before = _normalize_orders(_read_open_orders(client))
        if positions_before is None:
            return _finish(receipt_path, result, "positions_observation_ambiguous")
        if orders_before is None:
            return _finish(receipt_path, result, "orders_observation_ambiguous")

        result["positions_before"] = positions_before
        result["open_orders_before"] = orders_before

        # 3. Classify pre-observed orders: preserve existing close orders.
        position_signs = {p["symbol"]: _qty_sign(p["quantity"]) for p in positions_before}
        cancel_targets: list[dict[str, Any]] = []
        for order in orders_before:
            if _is_existing_close_order(order, position_signs):
                result["preserved_close_orders"].append(
                    {
                        "order_id": order["order_id"],
                        "symbol": order["symbol"],
                        "classification": "preserved_existing_close_order",
                    }
                )
            else:
                cancel_targets.append(order)

        raw_trading_client = client.raw_trading_client

        # 4. Exact-order-bound cancellation: one attempt per pre-observed order.
        for order in cancel_targets:
            result["cancel_attempt_count"] += 1
            result["broker_mutation_performed"] = True
            operation = {
                "order_id": order["order_id"],
                "symbol": order["symbol"],
                "classification": None,
            }
            result["cancel_operations"].append(operation)
            try:
                _cancel_exact_order(raw_trading_client, order["order_id"])
            except Exception as exc:
                operation["classification"] = (
                    f"cancel_request_failed_{exc.__class__.__name__}"
                )
                return _finish(receipt_path, result, "cleanup_blocked_cancel_failed")
            operation["classification"] = "cancel_request_accepted"

        # 5. Reconcile cancellations through bounded reads before any close.
        if cancel_targets:
            target_ids = {order["order_id"] for order in cancel_targets}

            def _uncanceled_target_ids() -> set[str]:
                orders_now = _normalize_orders(_read_open_orders(client))
                if orders_now is None:
                    raise _AmbiguousObservation()
                return target_ids & {order["order_id"] for order in orders_now}

            remaining = _reconcile_until(result, _uncanceled_target_ids)
            if remaining is None:
                return _finish(
                    receipt_path, result, "cleanup_blocked_cancel_reconciliation_ambiguous"
                )
            if remaining:
                return _finish(
                    receipt_path, result, "cleanup_blocked_cancel_unresolved"
                )
            result["cancel_completion_count"] = len(cancel_targets)

        # 6. Exact close per pre-observed position; never duplicate an
        #    existing close order for the same symbol.
        preserved_symbols = {
            entry["symbol"] for entry in result["preserved_close_orders"]
        }
        for position in positions_before:
            operation = {
                "symbol": position["symbol"],
                "classification": None,
                "close_order_id": None,
            }
            result["close_operations"].append(operation)
            if position["symbol"] in preserved_symbols:
                operation["classification"] = "close_skipped_existing_close_order_pending"
                continue
            result["close_attempt_count"] += 1
            result["broker_mutation_performed"] = True
            try:
                close_order = _close_exact_position(
                    raw_trading_client, position["symbol"]
                )
            except Exception as exc:
                operation["classification"] = (
                    f"close_request_failed_{exc.__class__.__name__}"
                )
                return _finish(receipt_path, result, "cleanup_blocked_close_failed")
            operation["classification"] = "close_request_accepted"
            close_order_id = _get_attr_or_key(close_order, "id") or _get_attr_or_key(
                close_order, "order_id"
            )
            operation["close_order_id"] = (
                str(close_order_id) if close_order_id else None
            )

        # 7. Prove flatness through bounded reconciliation reads only.
        def _residual_exposure() -> set[str]:
            positions_now = _normalize_positions(client.get_positions() or [])
            orders_now = _normalize_orders(_read_open_orders(client))
            if positions_now is None or orders_now is None:
                raise _AmbiguousObservation()
            result["positions_after_count"] = len(positions_now)
            result["open_orders_after_count"] = len(orders_now)
            return {p["symbol"] for p in positions_now} | {
                o["order_id"] for o in orders_now
            }

        residual = _reconcile_until(result, _residual_exposure)
        if residual is None:
            return _finish(
                receipt_path, result, "cleanup_blocked_reconciliation_ambiguous"
            )
        if residual:
            if preserved_symbols:
                return _finish(
                    receipt_path,
                    result,
                    "cleanup_blocked_existing_close_order_pending",
                )
            return _finish(receipt_path, result, "cleanup_reconciliation_unresolved")

        result["close_completion_count"] = result["close_attempt_count"]
        result["flatness_reconciled"] = True
        return _finish(receipt_path, result, "cleanup_successful")

    except PreflightCheckError as exc:
        return _finish(receipt_path, result, str(exc))
    except Exception as exc:
        return _finish(
            receipt_path, result, f"cleanup_exception_{exc.__class__.__name__}"
        )


class _AmbiguousObservation(Exception):
    pass


def _cancel_exact_order(raw_trading_client: Any, order_id: str) -> Any:
    return raw_trading_client.cancel_order_by_id(order_id)


def _close_exact_position(raw_trading_client: Any, symbol: str) -> Any:
    return raw_trading_client.close_position(symbol)


def _read_open_orders(client: AlpacaSdkClient) -> Any:
    query = AlpacaRecentOrderQuery(status_filter="open", limit=100, direction="desc")
    return client.get_orders(query) or []


def _reconcile_until(
    result: dict[str, Any],
    residual_reader: Any,
    *,
    max_reads: int = RECONCILIATION_MAX_READS,
    poll_seconds: float = RECONCILIATION_POLL_SECONDS,
) -> set[str] | None:
    """Poll residual state through bounded reads; return the final residual.

    Returns ``None`` when any read is ambiguous or fails; callers must stop.
    """
    residual: set[str] = set()
    for read_index in range(max_reads):
        result["reconciliation_read_count"] += 1
        try:
            residual = residual_reader()
        except Exception:
            return None
        if not residual:
            return set()
        if read_index + 1 < max_reads:
            time.sleep(poll_seconds)
    return residual


def _normalize_positions(raw_positions: Any) -> list[dict[str, Any]] | None:
    normalized: list[dict[str, Any]] = []
    for position in raw_positions:
        symbol = _get_attr_or_key(position, "symbol")
        qty = _get_attr_or_key(position, "qty")
        if not symbol or qty is None:
            return None
        try:
            quantity = str(Decimal(str(qty)).normalize())
        except (InvalidOperation, ValueError, TypeError):
            return None
        normalized.append(
            {"symbol": str(symbol).replace("/", "").upper(), "quantity": quantity}
        )
    return normalized


def _normalize_orders(raw_orders: Any) -> list[dict[str, Any]] | None:
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for order in raw_orders:
        order_id = _get_attr_or_key(order, "order_id") or _get_attr_or_key(order, "id")
        symbol = _get_attr_or_key(order, "symbol")
        side = _to_string_value(_get_attr_or_key(order, "side"))
        status = _to_string_value(_get_attr_or_key(order, "status"))
        if not order_id or not symbol or not side or not status:
            return None
        order_id_str = str(order_id)
        if order_id_str in seen_ids:
            return None
        seen_ids.add(order_id_str)
        normalized.append(
            {
                "order_id": order_id_str,
                "symbol": str(symbol).replace("/", "").upper(),
                "side": side.lower(),
                "status": status.lower(),
            }
        )
    return normalized


def _qty_sign(quantity: str) -> int:
    try:
        value = Decimal(quantity)
    except (InvalidOperation, ValueError):
        return 0
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _is_existing_close_order(
    order: dict[str, Any], position_signs: dict[str, int]
) -> bool:
    """True when the pre-observed order reduces a pre-observed position."""
    sign = position_signs.get(order["symbol"])
    if sign is None or sign == 0:
        return False
    if sign > 0:
        return order["side"] == "sell"
    return order["side"] == "buy"


def _finish(
    receipt_path: Path, result: dict[str, Any], classification: str
) -> dict[str, Any]:
    result["classification"] = classification
    result["completed_at_utc"] = datetime.now(UTC).isoformat()
    temp_path = receipt_path.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True)
    temp_path.replace(receipt_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bounded exact-order Alpaca paper account baseline cleanup."
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_CLEANUP_OUTPUT_ROOT),
        help="Output directory path.",
    )
    parser.add_argument(
        "--paper-cleanup-authorized",
        action="store_true",
        help="Authorize paper account cleanup.",
    )
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Allow network access to paper endpoint.",
    )
    args = parser.parse_args()

    res = run_crypto_paper_account_cleanup(
        output_root=args.output_root,
        paper_cleanup_authorized=args.paper_cleanup_authorized,
        allow_network=args.allow_network,
    )
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
