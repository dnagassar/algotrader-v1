"""Account-bound exact-ID, read-only reconciliation for the M376 SPY order."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any

from algotrader.config import AlpacaPaperConfig, DEFAULT_ALPACA_PAPER_BASE_URL
from algotrader.errors import ValidationError
from algotrader.execution.alpaca_client import AlpacaRecentOrderQuery
from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient
from algotrader.execution.paper_order_reconciliation import (
    PaperOrderReconciliationConfig,
    reconcile_paper_order,
    write_paper_order_reconciliation_jsonl,
)
from algotrader.execution.secure_credential_provider import (
    CredentialFamily,
    CredentialProvider,
    CredentialProviderError,
    CredentialReference,
    WINDOWS_PROVIDER_NAME,
    provider_from_name,
)

SCHEMA_VERSION = "v5_85_secure_m376_reconciliation_v1"
CREDENTIAL_REFERENCE = (
    "wincred:algotrader/v5.35/alpaca-paper-observation/production"
)
DEFAULT_OUTPUT_ROOT = "runs/paper_lab/secure_m376_reconciliation"
DEFAULT_RECONCILIATION_LOG = (
    "runs/paper_lab/m432_m376_read_only_reconciliation_refresh.jsonl"
)
M376_SYMBOL = "SPY"
M376_CLIENT_ORDER_ID = "paper-order-close-m376_spy_paper_close_submit"
M376_BROKER_ORDER_ID = "dbb32dd3-58bf-49ea-b9b1-9aa44e85002d"
M376_EXPECTED_QTY = "0.033172072"
_PAPER_ENDPOINT = DEFAULT_ALPACA_PAPER_BASE_URL.rstrip("/")
_FORBIDDEN_ENV = (
    "APP_PROFILE",
    "ALPACA_API_KEY",
    "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
    "ALPACA_EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_PAPER_ACCOUNT_ID",
    "APCA_EXPECTED_PAPER_ACCOUNT_ID",
    "EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_PAPER_BASE_URL",
    "ALPACA_BASE_URL",
    "ALPACA_LIVE_BASE_URL",
    "APCA_API_BASE_URL",
)
_TERMINAL = frozenset(
    {"filled", "canceled", "cancelled", "expired", "rejected"}
)
Clock = Callable[[], datetime]
ClientFactory = Callable[[AlpacaPaperConfig], object]


@dataclass(frozen=True, slots=True)
class SecureM376ReconciliationConfig:
    output_root: Path | str = DEFAULT_OUTPUT_ROOT
    reconciliation_log_path: Path | str = DEFAULT_RECONCILIATION_LOG
    paper_credential_reference: CredentialReference | str = CREDENTIAL_REFERENCE

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "output_root",
            _path(self.output_root, "output_root"),
        )
        object.__setattr__(
            self,
            "reconciliation_log_path",
            _path(self.reconciliation_log_path, "reconciliation_log_path"),
        )
        reference = (
            self.paper_credential_reference
            if isinstance(self.paper_credential_reference, CredentialReference)
            else CredentialReference(self.paper_credential_reference)
        )
        if reference.family is not CredentialFamily.ALPACA_PAPER_OBSERVATION:
            raise ValidationError("paper credential reference family is invalid.")
        object.__setattr__(self, "paper_credential_reference", reference)


class _ExactOrderReadOnlyBroker:
    def __init__(
        self,
        account: object,
        positions: Sequence[object],
        order: object,
        open_orders: Sequence[object],
    ):
        self.account = account
        self.positions = tuple(positions)
        self.order = _normalized_order(order)
        self.open_orders = tuple(_normalized_order(item) for item in open_orders)
        self.status = _status(self.order["status"])

    def get_account(self) -> object:
        return self.account

    def get_positions(self) -> tuple[object, ...]:
        return self.positions

    def get_recent_orders(
        self,
        query: AlpacaRecentOrderQuery,
    ) -> tuple[object, ...]:
        if query.status_filter == "open":
            return self.open_orders
        if query.status_filter == "closed":
            return (self.order,) if self.status in _TERMINAL else ()
        return (self.order,)


def run_secure_m376_reconciliation(
    config: SecureM376ReconciliationConfig | None = None,
    *,
    env: Mapping[str, str] | None = None,
    credential_provider: CredentialProvider | None = None,
    client_factory: ClientFactory | None = None,
    clock: Clock | None = None,
) -> dict[str, Any]:
    """Read M376 by exact ID and classify it with bounded open-SPY context."""
    resolved = config or SecureM376ReconciliationConfig()
    now = _utc((clock or (lambda: datetime.now(UTC)))())
    run_id = "v5_85_m376_" + now.strftime("%Y%m%dT%H%M%S%fZ")
    public_env = dict(os.environ if env is None else env)
    common: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "observed_at": now.isoformat(),
        "symbol": M376_SYMBOL,
        "client_order_id": M376_CLIENT_ORDER_ID,
        "broker_order_id": M376_BROKER_ORDER_ID,
        "paper_endpoint": _PAPER_ENDPOINT,
        "credential_provider": WINDOWS_PROVIDER_NAME,
        "credential_values_persisted": False,
        "credential_access_attempted": False,
        "credential_lease_consumed": False,
        "expected_account_matched": False,
        "paper_broker_read_attempted": False,
        "paper_broker_read_performed": False,
        "open_spy_order_read_attempted": False,
        "open_spy_order_read_performed": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "live_authorized": False,
        "live_access_attempted": False,
        "reconciliation": {},
        "blockers": [],
    }
    loaded = tuple(name for name in _FORBIDDEN_ENV if public_env.get(name))
    if loaded:
        return _persist(
            resolved,
            {
                **common,
                "state": "blocked_secure_preflight",
                "forbidden_environment_variable_count": len(loaded),
                "blockers": ["forbidden_environment_variables_loaded"],
            },
            run_id,
        )

    provider = credential_provider or provider_from_name(WINDOWS_PROVIDER_NAME)
    if getattr(provider, "provider_name", None) != WINDOWS_PROVIDER_NAME:
        return _persist(
            resolved,
            {
                **common,
                "state": "blocked_credential_provider",
                "blockers": ["credential_provider_mismatch"],
            },
            run_id,
        )
    try:
        lease = provider.open(
            resolved.paper_credential_reference,
            expected_family=CredentialFamily.ALPACA_PAPER_OBSERVATION,
        )
    except CredentialProviderError as exc:
        return _persist(
            resolved,
            {
                **common,
                "state": "blocked_credential_provider",
                "credential_access_attempted": True,
                "blockers": [exc.classification],
            },
            run_id,
        )

    def observe(
        key: str,
        secret: str,
        expected_account: str | None,
    ) -> dict[str, Any]:
        secrets = (key, secret, expected_account or "")
        if not expected_account:
            return {
                **common,
                "state": "blocked_expected_account",
                "credential_access_attempted": True,
                "credential_lease_consumed": True,
                "blockers": ["expected_account_missing"],
            }

        paper_config = AlpacaPaperConfig(
            app_profile="paper",
            alpaca_api_key=key,
            alpaca_secret_key=secret,
            alpaca_paper_base_url=_PAPER_ENDPOINT,
        )
        client = (
            client_factory(paper_config)
            if client_factory is not None
            else AlpacaSdkClient(
                paper_config,
                interlock_env={
                    "APP_PROFILE": "paper",
                    "APCA_API_KEY_ID": key,
                    "APCA_API_SECRET_KEY": secret,
                    "EXPECTED_PAPER_ACCOUNT_ID": expected_account,
                    "ALPACA_PAPER_BASE_URL": _PAPER_ENDPOINT,
                },
            )
        )
        common["paper_broker_read_attempted"] = True
        account = client.get_account()
        common["paper_broker_read_performed"] = True
        if expected_account not in _account_identities(account):
            receipt = {
                **common,
                "state": "blocked_expected_account",
                "credential_access_attempted": True,
                "credential_lease_consumed": True,
                "paper_broker_read_performed": True,
                "blockers": ["expected_account_mismatch"],
            }
            _assert_safe(receipt, secrets)
            return receipt
        if _status(_field(account, "status")) != "active":
            return {
                **common,
                "state": "blocked_paper_account",
                "credential_access_attempted": True,
                "credential_lease_consumed": True,
                "expected_account_matched": True,
                "paper_broker_read_performed": True,
                "blockers": ["paper_account_not_active"],
            }

        positions = tuple(client.get_positions())
        common["open_spy_order_read_attempted"] = True
        open_orders = tuple(
            client.get_orders(
                AlpacaRecentOrderQuery(
                    status_filter="open",
                    limit=100,
                    symbol_filter=M376_SYMBOL,
                )
            )
        )
        common["open_spy_order_read_performed"] = True
        order = client.get_order_by_id(M376_BROKER_ORDER_ID)
        broker = _ExactOrderReadOnlyBroker(
            account,
            positions,
            order,
            open_orders,
        )
        reconciliation = reconcile_paper_order(
            PaperOrderReconciliationConfig(
                run_id=run_id,
                symbol=M376_SYMBOL,
                client_order_id=M376_CLIENT_ORDER_ID,
                broker_order_id=M376_BROKER_ORDER_ID,
                expected_side="sell",
                expected_qty=M376_EXPECTED_QTY,
                expected_sizing_mode="qty",
                profile_gate_passed=True,
                paper_profile_ready=True,
                live_url_detected=False,
                order_history_coverage_complete=True,
            ),
            broker=broker,
            query_factory=lambda value: AlpacaRecentOrderQuery(
                status_filter=value,
                limit=100 if value == "open" else 1,
                symbol_filter=M376_SYMBOL,
            ),
            redactor=lambda value: _redact(value, secrets),
        )
        _assert_safe(reconciliation, secrets)
        write_paper_order_reconciliation_jsonl(
            reconciliation,
            resolved.reconciliation_log_path,
        )
        decision = str(reconciliation.get("reconciliation_decision") or "")
        blocked = reconciliation.get("next_spy_submit_blocked") is True
        if decision in {"m376_terminal_filled", "m376_terminal_nonfilled"}:
            state = (
                "m376_terminal_context_blocked"
                if blocked
                else "m376_terminal_reconciled"
            )
        elif decision == "m376_nonterminal_open":
            state = "m376_nonterminal_blocked"
        else:
            state = "m376_reconciliation_blocked"
        receipt = {
            **common,
            "state": state,
            "credential_access_attempted": True,
            "credential_lease_consumed": True,
            "expected_account_matched": True,
            "paper_broker_read_performed": True,
            "open_spy_order_read_performed": True,
            "reconciliation": reconciliation,
            "blockers": list(reconciliation.get("blockers") or ()),
        }
        _assert_safe(receipt, secrets)
        return receipt

    try:
        receipt = lease.use(observe)
    except CredentialProviderError as exc:
        receipt = {
            **common,
            "state": "blocked_credential_provider",
            "credential_access_attempted": True,
            "credential_lease_consumed": lease.closed,
            "blockers": [exc.classification],
        }
    except Exception as exc:
        receipt = {
            **common,
            "state": "blocked_paper_read",
            "credential_access_attempted": True,
            "credential_lease_consumed": lease.closed,
            "blockers": [f"paper_read_failed:{exc.__class__.__name__}"],
        }
    return _persist(resolved, receipt, run_id)


def exit_status(receipt: Mapping[str, Any]) -> int:
    return 0 if receipt.get("state") == "m376_terminal_reconciled" else 2


def render(receipt: Mapping[str, Any]) -> str:
    detail = receipt.get("reconciliation")
    detail = detail if isinstance(detail, Mapping) else {}
    rows = (
        ("schema_version", receipt.get("schema_version", "")),
        ("state", receipt.get("state", "")),
        (
            "expected_account_matched",
            _bool(receipt.get("expected_account_matched")),
        ),
        (
            "paper_broker_read_attempted",
            _bool(receipt.get("paper_broker_read_attempted")),
        ),
        (
            "paper_broker_read_performed",
            _bool(receipt.get("paper_broker_read_performed")),
        ),
        (
            "open_spy_order_read_attempted",
            _bool(receipt.get("open_spy_order_read_attempted")),
        ),
        (
            "open_spy_order_read_performed",
            _bool(receipt.get("open_spy_order_read_performed")),
        ),
        ("exact_order_found", _bool(detail.get("exact_order_found"))),
        ("observed_status", detail.get("observed_status", "")),
        ("terminal_state", detail.get("terminal_state", "")),
        (
            "reconciliation_decision",
            detail.get("reconciliation_decision", ""),
        ),
        ("open_order_count", detail.get("open_order_count", "")),
        (
            "next_spy_submit_blocked",
            _bool(detail.get("next_spy_submit_blocked")),
        ),
        (
            "paper_submit_performed",
            _bool(receipt.get("paper_submit_performed")),
        ),
        (
            "broker_mutation_performed",
            _bool(receipt.get("broker_mutation_performed")),
        ),
        ("live_authorized", _bool(receipt.get("live_authorized"))),
        (
            "blockers",
            ",".join(str(item) for item in receipt.get("blockers", [])),
        ),
    )
    return "\n".join(f"{key}={value}" for key, value in rows) + "\n"


def _persist(
    config: SecureM376ReconciliationConfig,
    receipt: Mapping[str, Any],
    run_id: str,
) -> dict[str, Any]:
    payload = dict(receipt)
    text = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    root = Path(config.output_root)
    paths = (
        root / "cycles" / run_id / "receipt.json",
        root / "latest_receipt.json",
    )
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(text, encoding="utf-8", newline="\n")
        temporary.replace(path)
    return payload


def _object_data(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        result = dump()
        if isinstance(result, Mapping):
            return dict(result)
    return {
        name: getattr(value, name)
        for name in dir(value)
        if not name.startswith("_") and not callable(getattr(value, name, None))
    }


def _field(value: object, name: str) -> object:
    return _object_data(value).get(name)


def _normalized_order(value: object) -> dict[str, object]:
    data = _object_data(value)

    def first(*names: str) -> object:
        for name in names:
            candidate = data.get(name)
            if candidate is not None and str(candidate).strip():
                return candidate
        return ""

    return {
        "id": str(first("id", "order_id", "broker_order_id")),
        "client_order_id": str(first("client_order_id")),
        "symbol": str(first("symbol")).upper(),
        "side": _status(first("side")),
        "status": _status(first("status", "normalized_status")),
        "qty": first("qty", "quantity"),
        "filled_qty": first("filled_qty", "filled_quantity"),
        "filled_avg_price": first(
            "filled_avg_price",
            "filled_average_price",
        ),
        "submitted_at": first("submitted_at", "created_at"),
        "filled_at": first("filled_at"),
        "canceled_at": first("canceled_at", "cancelled_at"),
        "expired_at": first("expired_at"),
    }


def _account_identities(account: object) -> frozenset[str]:
    data = _object_data(account)
    return frozenset(
        str(data.get(name) or "").strip()
        for name in ("account_id", "id", "account_number")
        if str(data.get(name) or "").strip()
    )


def _status(value: object) -> str:
    return (
        str(getattr(value, "value", value) or "")
        .strip()
        .lower()
        .rsplit(".", 1)[-1]
    )


def _redact(value: str, secrets: Sequence[str]) -> str:
    result = str(value)
    for secret in secrets:
        if secret:
            result = result.replace(secret, "<redacted>")
    return result


def _assert_safe(payload: Mapping[str, Any], secrets: Sequence[str]) -> None:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    if any(secret and secret in encoded for secret in secrets):
        raise RuntimeError("credential_or_account_value_in_receipt")


def _path(value: object, field_name: str) -> Path:
    path = value if isinstance(value, Path) else Path(str(value))
    if not str(path).strip():
        raise ValidationError(f"{field_name} is required.")
    return path


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError("clock must return a timezone-aware datetime.")
    return value.astimezone(UTC)


def _bool(value: object) -> str:
    return "true" if value is True else "false"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Secure exact read-only M376 reconciliation."
    )
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--reconciliation-log-path",
        default=DEFAULT_RECONCILIATION_LOG,
    )
    parser.add_argument(
        "--paper-credential-reference",
        default=CREDENTIAL_REFERENCE,
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    receipt = run_secure_m376_reconciliation(
        SecureM376ReconciliationConfig(
            output_root=args.output_root,
            reconciliation_log_path=args.reconciliation_log_path,
            paper_credential_reference=args.paper_credential_reference,
        )
    )
    output = (
        json.dumps(receipt, sort_keys=True, separators=(",", ":"))
        if args.format == "json"
        else render(receipt)
    )
    print(output, end="\n" if args.format == "json" else "")
    return exit_status(receipt)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "M376_BROKER_ORDER_ID",
    "M376_CLIENT_ORDER_ID",
    "SCHEMA_VERSION",
    "SecureM376ReconciliationConfig",
    "exit_status",
    "render",
    "run_secure_m376_reconciliation",
]