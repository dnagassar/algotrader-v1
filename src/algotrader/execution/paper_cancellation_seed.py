"""One-shot submit-only paper order used to create an exact cancel target."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
import json
import os
from pathlib import Path
from typing import Any

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL, AlpacaPaperConfig
from algotrader.execution.alpaca_client import (
    AlpacaOrderRequest,
    AlpacaRecentOrderQuery,
)
from algotrader.execution.durable_submit import (
    DurableBrokerObservation,
    DurableSubmitCoordinator,
    DurableSubmitEvidence,
    DurableSubmitIdentity,
)
from algotrader.execution.order_journal import SqliteOrderJournal


PAPER_CANCELLATION_SEED_VERSION = "paper_cancellation_seed_v1"
PAPER_CANCELLATION_SEED_AUTHORIZATION_PHRASE = (
    "AUTHORIZE ONE SPY PAPER DAY LIMIT BUY QTY 1 LIMIT 1.00 "
    "FOR CANCELLATION SEED ONLY"
)
PAPER_CANCELLATION_SEED_CLIENT_ORDER_ID = (
    "v31-spy-drill-cancellation-seed-dceb0e7-20260713"
)
PAPER_CANCELLATION_SEED_EXECUTION_PLAN_ID = (
    "paper-cancellation-seed-spy-buy-qty-1-limit-1-day-v1"
)
PAPER_CANCELLATION_SEED_RUN_ID = "paper-cancellation-seed-20260713"
PAPER_CANCELLATION_SEED_LEASE_NAME = "paper-cancellation-seed-submit"
PAPER_CANCELLATION_SEED_LEASE_TTL_SECONDS = 300
PAPER_CANCELLATION_SEED_SYMBOL = "SPY"
PAPER_CANCELLATION_SEED_SIDE = "buy"
PAPER_CANCELLATION_SEED_QUANTITY = Decimal("1")
PAPER_CANCELLATION_SEED_LIMIT_PRICE = Decimal("1.00")
PAPER_CANCELLATION_SEED_MAXIMUM_EXPOSURE = Decimal("1.00")
PAPER_CANCELLATION_SEED_ORDER_TYPE = "limit"
PAPER_CANCELLATION_SEED_TIME_IN_FORCE = "day"
PAPER_CANCELLATION_SEED_DEFAULT_OUTPUT_PATH = Path(
    "runs/paper_cancellation_seed/latest/seed_result.json"
)
PAPER_CANCELLATION_SEED_DEFAULT_JOURNAL_PATH = Path(
    "runs/paper_autopilot/state/order_journal.sqlite3"
)
PAPER_CANCELLATION_SEED_EXPECTED_ACCOUNT_ENV = (
    "ALPACA_EXPECTED_PAPER_ACCOUNT_ID"
)

_OPEN_STATUSES = frozenset(
    {
        "accepted",
        "new",
        "partially_filled",
        "pending_cancel",
        "pending_new",
        "stopped",
    }
)
_TERMINAL_STATUSES = frozenset(
    {
        "canceled",
        "cancelled",
        "done_for_day",
        "expired",
        "filled",
        "rejected",
        "replaced",
    }
)
_LIVE_ENDPOINT_FRAGMENTS = (
    "https://api.alpaca.markets",
    "http://api.alpaca.markets",
)
_BrokerFactory = Callable[[AlpacaPaperConfig], Any]


def run_paper_cancellation_seed(
    *,
    paper_submit_authorized: bool = False,
    authorization_phrase: str = "",
    output_path: Path | str = PAPER_CANCELLATION_SEED_DEFAULT_OUTPUT_PATH,
    journal_path: Path | str = PAPER_CANCELLATION_SEED_DEFAULT_JOURNAL_PATH,
    env: Mapping[str, str] | None = None,
    occurred_at: datetime | None = None,
    broker_factory: _BrokerFactory | None = None,
) -> dict[str, object]:
    """Submit the exact authorized seed once and never request cancellation."""

    source_env = dict(os.environ if env is None else env)
    timestamp = _utc_now(occurred_at)
    output = Path(output_path)
    journal = Path(journal_path)
    result = _base_result(output, journal, timestamp)
    blockers = _configuration_blockers(
        source_env,
        paper_submit_authorized=paper_submit_authorized,
        authorization_phrase=authorization_phrase,
    )
    if blockers:
        result.update(
            outcome="blocked_before_broker_access",
            blocker=blockers[0],
            blockers=list(blockers),
        )
        return _write_result(output, result)

    paper_config = _paper_config_from_env_aliases(source_env)
    try:
        gateway = (broker_factory or _build_gateway)(paper_config)
    except Exception as exc:
        result.update(
            outcome="blocked_broker_construction_failed",
            blocker="broker_construction_failed",
            blockers=["broker_construction_failed"],
            error_type=exc.__class__.__name__,
        )
        return _write_result(output, result)

    result["broker_access_performed"] = True
    observation, blockers = _pre_submit_observation(
        gateway,
        source_env=source_env,
    )
    result["pre_submit_observation"] = observation
    if blockers:
        result.update(
            outcome="blocked_after_read_only_observation",
            blocker=blockers[0],
            blockers=list(blockers),
        )
        return _write_result(output, result)

    coordinator = DurableSubmitCoordinator(SqliteOrderJournal(journal))
    identity = _submit_identity()
    lease = None
    try:
        lease = coordinator.acquire_lease(
            lease_name=PAPER_CANCELLATION_SEED_LEASE_NAME,
            owner_run_id=PAPER_CANCELLATION_SEED_RUN_ID,
            occurred_at=timestamp,
            ttl_seconds=PAPER_CANCELLATION_SEED_LEASE_TTL_SECONDS,
        )
        result["lease_acquired"] = lease.acquired
        if not lease.acquired:
            result.update(
                outcome="blocked_durable_lease_unavailable",
                blocker=lease.blocker or "durable_submit_lease_unavailable",
                blockers=[lease.blocker or "durable_submit_lease_unavailable"],
            )
            return _write_result(output, result)

        reservation = coordinator.reserve(identity, timestamp)
        result["reservation_status"] = reservation.status
        result["reservation_acquired"] = reservation.acquired
        if not reservation.acquired:
            blocker = (
                "durable_submit_identity_conflict"
                if reservation.status == "client_order_id_conflict"
                else "durable_submit_already_reserved"
            )
            result.update(
                outcome="blocked_durable_reservation",
                blocker=blocker,
                blockers=[blocker],
                journal_state=reservation.record.state.value,
            )
            return _write_result(output, result)

        result = _submit_once(
            gateway,
            coordinator=coordinator,
            identity=identity,
            lease=lease,
            occurred_at=timestamp,
            result=result,
        )
        if result.get("outcome") != "target_ready_for_exact_cancellation":
            return _write_result(output, result)

        result = _observe_exact_order_once(
            gateway,
            coordinator=coordinator,
            occurred_at=timestamp,
            result=result,
        )
        return _write_result(output, result)
    except Exception as exc:
        result.update(
            outcome="stopped_local_boundary_failure",
            blocker="local_boundary_failure",
            blockers=["local_boundary_failure"],
            error_type=exc.__class__.__name__,
        )
        return _write_result(output, result)
    finally:
        if lease is not None and lease.acquired:
            try:
                result["lease_released"] = coordinator.release_lease(lease)
            except Exception as exc:
                result["lease_release_error_type"] = exc.__class__.__name__
            if output.exists():
                _write_result(output, result)


def _configuration_blockers(
    env: Mapping[str, str],
    *,
    paper_submit_authorized: bool,
    authorization_phrase: str,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if type(paper_submit_authorized) is not bool or not paper_submit_authorized:
        blockers.append("paper_submit_not_authorized")
    if authorization_phrase != PAPER_CANCELLATION_SEED_AUTHORIZATION_PHRASE:
        blockers.append("authorization_phrase_mismatch")
    profile = str(env.get("APP_PROFILE", "")).strip().lower()
    if profile != "paper":
        blockers.append("paper_profile_required")
    if not _first_value(env, "ALPACA_API_KEY", "APCA_API_KEY_ID"):
        blockers.append("paper_api_key_required")
    if not _first_value(
        env,
        "ALPACA_SECRET_KEY",
        "ALPACA_API_SECRET_KEY",
        "APCA_API_SECRET_KEY",
    ):
        blockers.append("paper_secret_key_required")
    expected_account = str(
        env.get(PAPER_CANCELLATION_SEED_EXPECTED_ACCOUNT_ENV, "")
    ).strip()
    if not expected_account:
        blockers.append("expected_paper_account_required")
    paper_url = str(
        env.get("ALPACA_PAPER_BASE_URL", DEFAULT_ALPACA_PAPER_BASE_URL)
    ).strip().rstrip("/").lower()
    if paper_url != DEFAULT_ALPACA_PAPER_BASE_URL:
        blockers.append("exact_paper_endpoint_required")
    for name in ("ALPACA_BASE_URL", "APCA_API_BASE_URL"):
        value = str(env.get(name, "")).strip().rstrip("/").lower()
        if value and any(fragment in value for fragment in _LIVE_ENDPOINT_FRAGMENTS):
            blockers.append(f"live_endpoint_detected:{name}")
    return tuple(blockers)


def _pre_submit_observation(
    gateway: Any,
    *,
    source_env: Mapping[str, str],
) -> tuple[dict[str, object], tuple[str, ...]]:
    try:
        account = gateway.get_account()
        asset = gateway.get_asset(PAPER_CANCELLATION_SEED_SYMBOL)
        open_orders = tuple(
            gateway.get_orders(
                AlpacaRecentOrderQuery(
                    status_filter="open",
                    symbol_filter=PAPER_CANCELLATION_SEED_SYMBOL,
                )
            )
        )
        all_orders = tuple(
            gateway.get_orders(
                AlpacaRecentOrderQuery(
                    status_filter="all",
                    symbol_filter=PAPER_CANCELLATION_SEED_SYMBOL,
                )
            )
        )
    except Exception as exc:
        return (
            {
                "account_observed": False,
                "asset_observed": False,
                "open_orders_observed": False,
                "error_type": exc.__class__.__name__,
            },
            ("paper_broker_read_failed",),
        )

    expected_account = str(
        source_env.get(PAPER_CANCELLATION_SEED_EXPECTED_ACCOUNT_ENV, "")
    ).strip()
    account_values = {
        _field(account, "id"),
        _field(account, "account_number"),
    } - {""}
    account_matched = expected_account in account_values
    account_active = _field(account, "status").lower() in {"active", ""}
    account_tradable = _bool_field(account, "tradable", default=True)
    asset_tradable = _bool_field(asset, "tradable", default=False)
    duplicate = any(
        _field(order, "client_order_id")
        == PAPER_CANCELLATION_SEED_CLIENT_ORDER_ID
        for order in all_orders
    )
    blockers: list[str] = []
    if not account_matched:
        blockers.append("expected_paper_account_mismatch")
    if not account_active:
        blockers.append("paper_account_not_active")
    if not account_tradable:
        blockers.append("paper_account_not_tradable")
    if not asset_tradable:
        blockers.append("spy_asset_not_tradable")
    if open_orders:
        blockers.append("existing_open_order_present")
    if duplicate:
        blockers.append("duplicate_seed_client_order_id_present")
    return (
        {
            "account_observed": True,
            "expected_account_configured": True,
            "expected_account_matched": account_matched,
            "account_active": account_active,
            "account_tradable": account_tradable,
            "asset_observed": True,
            "asset_tradable": asset_tradable,
            "open_orders_observed": True,
            "open_order_count": len(open_orders),
            "duplicate_client_order_id_observed": duplicate,
        },
        tuple(blockers),
    )


def _submit_once(
    gateway: Any,
    *,
    coordinator: DurableSubmitCoordinator,
    identity: DurableSubmitIdentity,
    lease: Any,
    occurred_at: datetime,
    result: dict[str, object],
) -> dict[str, object]:
    request = _exact_order_request()
    outcome = coordinator.execute(
        identity=identity,
        lease=lease,
        evidence=DurableSubmitEvidence(
            canonical_risk_allowed=True,
            snapshot_fresh=True,
        ),
        occurred_at=occurred_at,
        submit=lambda: gateway.send(request),
        observe=_durable_observation,
    )
    record = outcome.record
    updated = {
        **result,
        "broker_mutation_performed": outcome.broker_called,
        "paper_submit_performed": outcome.broker_called,
        "submit_attempted": outcome.broker_called,
        "submit_call_count": 1 if outcome.broker_called else 0,
        "journal_state": "" if record is None else record.state.value,
        "journal_error_type": outcome.journal_error_type,
    }
    if not outcome.broker_called:
        updated.update(
            outcome="blocked_before_submit_callback",
            blocker=outcome.blocker or "durable_submit_blocked",
            blockers=[outcome.blocker or "durable_submit_blocked"],
        )
        return updated
    if outcome.ambiguous or outcome.response is None:
        updated.update(
            outcome="stopped_submit_ambiguous_no_retry",
            blocker=outcome.blocker or "submit_response_ambiguous",
            blockers=[outcome.blocker or "submit_response_ambiguous"],
            error_type=outcome.error_type,
        )
        return updated

    observation = _response_payload(outcome.response)
    status = str(observation["broker_status"])
    updated.update(
        broker_order_id=observation["broker_order_id"],
        broker_status=status,
        observed_client_order_id=observation["client_order_id"],
        filled_quantity=observation["filled_quantity"],
        filled_average_price=observation["filled_average_price"],
    )
    if status == "filled":
        updated.update(
            outcome="stopped_filled_no_cancel",
            blocker="seed_order_filled",
            blockers=["seed_order_filled"],
        )
    elif status in _OPEN_STATUSES:
        updated.update(
            outcome="target_ready_for_exact_cancellation",
            blocker="",
            blockers=[],
        )
    elif status in _TERMINAL_STATUSES:
        updated.update(
            outcome="stopped_terminal_no_cancel",
            blocker=f"seed_order_terminal:{status}",
            blockers=[f"seed_order_terminal:{status}"],
        )
    else:
        updated.update(
            outcome="stopped_unrecognized_status_no_cancel",
            blocker="seed_order_status_unrecognized",
            blockers=["seed_order_status_unrecognized"],
        )
    return updated


def _observe_exact_order_once(
    gateway: Any,
    *,
    coordinator: DurableSubmitCoordinator,
    occurred_at: datetime,
    result: dict[str, object],
) -> dict[str, object]:
    updated = dict(result)
    updated["post_submit_read_attempted"] = True
    try:
        order = gateway.lookup_order_by_client_order_id(
            PAPER_CANCELLATION_SEED_CLIENT_ORDER_ID
        )
    except Exception as exc:
        updated.update(
            outcome="stopped_post_submit_read_failed_no_retry",
            blocker="post_submit_exact_order_read_failed",
            blockers=["post_submit_exact_order_read_failed"],
            post_submit_read_error_type=exc.__class__.__name__,
        )
        return updated
    if order is None:
        updated.update(
            outcome="stopped_post_submit_order_missing_no_retry",
            blocker="post_submit_exact_order_missing",
            blockers=["post_submit_exact_order_missing"],
        )
        return updated

    observation = _response_payload(order)
    if (
        observation["client_order_id"]
        != PAPER_CANCELLATION_SEED_CLIENT_ORDER_ID
        or observation["broker_order_id"] != updated.get("broker_order_id")
    ):
        updated.update(
            outcome="stopped_post_submit_identity_mismatch",
            blocker="post_submit_exact_order_identity_mismatch",
            blockers=["post_submit_exact_order_identity_mismatch"],
        )
        return updated
    try:
        record = coordinator.journal.record_broker_observation(
            PAPER_CANCELLATION_SEED_CLIENT_ORDER_ID,
            occurred_at,
            broker_order_id=str(observation["broker_order_id"]),
            broker_status=str(observation["broker_status"]),
            filled_quantity=observation["filled_quantity"] or None,
            filled_average_price=observation["filled_average_price"] or None,
        )
    except Exception as exc:
        updated.update(
            outcome="stopped_post_submit_journal_failure",
            blocker="post_submit_observation_persistence_failed",
            blockers=["post_submit_observation_persistence_failed"],
            post_submit_journal_error_type=exc.__class__.__name__,
        )
        return updated

    status = str(observation["broker_status"])
    updated.update(
        broker_status=status,
        filled_quantity=observation["filled_quantity"],
        filled_average_price=observation["filled_average_price"],
        journal_state=record.state.value,
        post_submit_read_succeeded=True,
    )
    if status == "filled":
        updated.update(
            outcome="stopped_filled_no_cancel",
            blocker="seed_order_filled",
            blockers=["seed_order_filled"],
        )
    elif status not in _OPEN_STATUSES:
        updated.update(
            outcome="stopped_terminal_no_cancel",
            blocker=f"seed_order_not_open:{status}",
            blockers=[f"seed_order_not_open:{status}"],
        )
    return updated


def _exact_order_request() -> AlpacaOrderRequest:
    return AlpacaOrderRequest(
        client_order_id=PAPER_CANCELLATION_SEED_CLIENT_ORDER_ID,
        symbol=PAPER_CANCELLATION_SEED_SYMBOL,
        side=PAPER_CANCELLATION_SEED_SIDE,
        asset_class="equity",
        qty=PAPER_CANCELLATION_SEED_QUANTITY,
        order_type=PAPER_CANCELLATION_SEED_ORDER_TYPE,
        time_in_force=PAPER_CANCELLATION_SEED_TIME_IN_FORCE,
        limit_price=PAPER_CANCELLATION_SEED_LIMIT_PRICE,
    )


def _submit_identity() -> DurableSubmitIdentity:
    return DurableSubmitIdentity(
        client_order_id=PAPER_CANCELLATION_SEED_CLIENT_ORDER_ID,
        execution_plan_id=PAPER_CANCELLATION_SEED_EXECUTION_PLAN_ID,
        reservation_run_id=PAPER_CANCELLATION_SEED_RUN_ID,
        symbol=PAPER_CANCELLATION_SEED_SYMBOL,
        side=PAPER_CANCELLATION_SEED_SIDE,
        quantity=PAPER_CANCELLATION_SEED_QUANTITY,
        notional=None,
    )


def _durable_observation(response: object) -> DurableBrokerObservation:
    payload = _response_payload(response)
    return DurableBrokerObservation(
        broker_order_id=str(payload["broker_order_id"]),
        broker_status=str(payload["broker_status"]),
        filled_quantity=payload["filled_quantity"] or None,
        filled_average_price=payload["filled_average_price"] or None,
    )


def _response_payload(response: object) -> dict[str, str]:
    return {
        "broker_order_id": _field(response, "id", "order_id"),
        "client_order_id": _field(response, "client_order_id"),
        "broker_status": _field(response, "status").lower(),
        "filled_quantity": _field(response, "filled_qty", "filled_quantity"),
        "filled_average_price": _field(
            response,
            "filled_avg_price",
            "filled_average_price",
        ),
    }


def _base_result(
    output_path: Path,
    journal_path: Path,
    occurred_at: datetime,
) -> dict[str, object]:
    return {
        "seed_version": PAPER_CANCELLATION_SEED_VERSION,
        "outcome": "not_started",
        "blocker": "",
        "blockers": [],
        "occurred_at": occurred_at.isoformat(),
        "symbol": PAPER_CANCELLATION_SEED_SYMBOL,
        "side": PAPER_CANCELLATION_SEED_SIDE,
        "quantity": str(PAPER_CANCELLATION_SEED_QUANTITY),
        "limit_price": f"{PAPER_CANCELLATION_SEED_LIMIT_PRICE:.2f}",
        "maximum_paper_exposure": f"{PAPER_CANCELLATION_SEED_MAXIMUM_EXPOSURE:.2f}",
        "order_type": PAPER_CANCELLATION_SEED_ORDER_TYPE,
        "time_in_force": PAPER_CANCELLATION_SEED_TIME_IN_FORCE,
        "client_order_id": PAPER_CANCELLATION_SEED_CLIENT_ORDER_ID,
        "broker_order_id": "",
        "broker_status": "",
        "output_path": str(output_path),
        "journal_path": str(journal_path),
        "broker_access_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "submit_attempted": False,
        "submit_call_count": 0,
        "post_submit_read_attempted": False,
        "post_submit_read_succeeded": False,
        "reservation_status": "not_attempted",
        "reservation_acquired": False,
        "lease_acquired": False,
        "lease_released": False,
        "cancel_attempted": False,
        "paper_cancel_performed": False,
        "replace_attempted": False,
        "close_attempted": False,
        "liquidate_attempted": False,
        "live_access_performed": False,
        "live_mutation_performed": False,
        "no_retry": True,
    }


def _write_result(path: Path, result: dict[str, object]) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return result


class _SdkSeedGateway:
    """Narrow SDK wrapper exposing reads and one submit-only callback."""

    def __init__(self, client: Any) -> None:
        self._client = client
        self._raw_client = client.raw_trading_client

    def get_account(self) -> object:
        return self._client.get_account()

    def get_asset(self, symbol: str) -> object:
        return self._raw_client.get_asset(symbol)

    def get_orders(self, query: AlpacaRecentOrderQuery) -> Sequence[object]:
        return self._client.get_orders(query)

    def lookup_order_by_client_order_id(self, client_order_id: str) -> object | None:
        for method_name in (
            "get_order_by_client_id",
            "get_order_by_client_order_id",
        ):
            method = getattr(self._raw_client, method_name, None)
            if callable(method):
                return method(client_order_id)
        matches = [
            order
            for order in self.get_orders(
                AlpacaRecentOrderQuery(
                    status_filter="all",
                    symbol_filter=PAPER_CANCELLATION_SEED_SYMBOL,
                )
            )
            if _field(order, "client_order_id") == client_order_id
        ]
        return matches[0] if len(matches) == 1 else None

    def send(self, request: AlpacaOrderRequest) -> object:
        return self._client.submit_order(request)


def _paper_config_from_env_aliases(
    env: Mapping[str, str],
) -> AlpacaPaperConfig:
    source = dict(env)
    if not source.get("ALPACA_API_KEY") and source.get("APCA_API_KEY_ID"):
        source["ALPACA_API_KEY"] = source["APCA_API_KEY_ID"]
    if not source.get("ALPACA_SECRET_KEY") and source.get("ALPACA_API_SECRET_KEY"):
        source["ALPACA_SECRET_KEY"] = source["ALPACA_API_SECRET_KEY"]
    if not source.get("ALPACA_SECRET_KEY") and source.get("APCA_API_SECRET_KEY"):
        source["ALPACA_SECRET_KEY"] = source["APCA_API_SECRET_KEY"]
    return AlpacaPaperConfig.from_env(source)


def _build_gateway(config: AlpacaPaperConfig) -> _SdkSeedGateway:
    from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient

    return _SdkSeedGateway(AlpacaSdkClient(config))


def _field(value: object, *names: str) -> str:
    for name in names:
        if isinstance(value, Mapping) and name in value:
            candidate = value.get(name)
        else:
            candidate = getattr(value, name, None)
        candidate = getattr(candidate, "value", candidate)
        text = "" if candidate is None else str(candidate).strip()
        if text:
            return text
    return ""


def _bool_field(value: object, name: str, *, default: bool) -> bool:
    candidate = value.get(name) if isinstance(value, Mapping) else getattr(value, name, None)
    if candidate is None:
        return default
    return candidate is True


def _first_value(env: Mapping[str, str], *names: str) -> str:
    for name in names:
        value = str(env.get(name, "")).strip()
        if value:
            return value
    return ""


def _utc_now(value: datetime | None) -> datetime:
    resolved = datetime.now(UTC) if value is None else value
    if resolved.tzinfo is None or resolved.utcoffset() != UTC.utcoffset(resolved):
        raise ValueError("occurred_at must be a timezone-aware UTC datetime.")
    return resolved


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m algotrader.execution.paper_cancellation_seed",
        description="Submit one exact SPY paper limit seed without cancellation.",
    )
    parser.add_argument("--paper-submit-authorized", action="store_true")
    parser.add_argument("--authorization-phrase", required=True)
    parser.add_argument(
        "--output-path",
        default=str(PAPER_CANCELLATION_SEED_DEFAULT_OUTPUT_PATH),
    )
    parser.add_argument(
        "--journal-path",
        default=str(PAPER_CANCELLATION_SEED_DEFAULT_JOURNAL_PATH),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_paper_cancellation_seed(
        paper_submit_authorized=args.paper_submit_authorized,
        authorization_phrase=args.authorization_phrase,
        output_path=args.output_path,
        journal_path=args.journal_path,
    )
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result.get("outcome") == "target_ready_for_exact_cancellation" else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "PAPER_CANCELLATION_SEED_AUTHORIZATION_PHRASE",
    "PAPER_CANCELLATION_SEED_CLIENT_ORDER_ID",
    "PAPER_CANCELLATION_SEED_DEFAULT_JOURNAL_PATH",
    "PAPER_CANCELLATION_SEED_DEFAULT_OUTPUT_PATH",
    "PAPER_CANCELLATION_SEED_LIMIT_PRICE",
    "PAPER_CANCELLATION_SEED_MAXIMUM_EXPOSURE",
    "PAPER_CANCELLATION_SEED_QUANTITY",
    "PAPER_CANCELLATION_SEED_VERSION",
    "build_parser",
    "main",
    "run_paper_cancellation_seed",
]
