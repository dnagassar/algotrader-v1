"""Transactional local order journal for crash-safe broker boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
import json
from pathlib import Path
import sqlite3

from algotrader.core.time import require_utc_datetime
from algotrader.core.validation import decimal_value, symbol_value
from algotrader.errors import ValidationError

__all__ = [
    "OrderJournalRecord",
    "OrderJournalState",
    "OrderReservation",
    "ReservationResult",
    "RuntimeControl",
    "RuntimeLeaseResult",
    "SqliteOrderJournal",
]

_SCHEMA_VERSION = 1


class OrderJournalState(StrEnum):
    RESERVED = "reserved"
    SUBMIT_ATTEMPTED = "submit_attempted"
    UNKNOWN = "unknown"
    ACCEPTED = "accepted"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELED = "canceled"
    EXPIRED = "expired"


_TERMINAL_STATES = frozenset(
    {
        OrderJournalState.FILLED,
        OrderJournalState.REJECTED,
        OrderJournalState.CANCELED,
        OrderJournalState.EXPIRED,
    }
)


@dataclass(frozen=True, slots=True)
class OrderReservation:
    client_order_id: str
    execution_plan_id: str
    run_id: str
    symbol: str
    side: str
    quantity: Decimal | str | None
    notional: Decimal | str | None

    def __post_init__(self) -> None:
        for field_name in ("client_order_id", "execution_plan_id", "run_id"):
            value = str(getattr(self, field_name)).strip()
            if not value:
                raise ValidationError(f"{field_name} is required.")
            object.__setattr__(self, field_name, value)
        object.__setattr__(self, "symbol", symbol_value(self.symbol))
        side = self.side.strip().lower()
        if side not in {"buy", "sell"}:
            raise ValidationError("side must be buy or sell.")
        object.__setattr__(self, "side", side)
        quantity = _optional_positive_decimal(self.quantity, "quantity")
        notional = _optional_positive_decimal(self.notional, "notional")
        if (quantity is None) == (notional is None):
            raise ValidationError("exactly one of quantity or notional is required.")
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "notional", notional)


@dataclass(frozen=True, slots=True)
class OrderJournalRecord:
    client_order_id: str
    execution_plan_id: str
    run_id: str
    symbol: str
    side: str
    quantity: Decimal | None
    notional: Decimal | None
    state: OrderJournalState
    broker_order_id: str
    broker_status: str
    filled_quantity: Decimal | None
    filled_average_price: Decimal | None
    ambiguity_reason: str
    created_at: datetime
    updated_at: datetime

    @property
    def terminal(self) -> bool:
        return self.state in _TERMINAL_STATES

    @property
    def safe_to_resubmit(self) -> bool:
        return False

    def to_dict(self) -> dict[str, object]:
        return {
            "client_order_id": self.client_order_id,
            "execution_plan_id": self.execution_plan_id,
            "run_id": self.run_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": str(self.quantity) if self.quantity is not None else "",
            "notional": str(self.notional) if self.notional is not None else "",
            "state": self.state.value,
            "broker_order_id": self.broker_order_id,
            "broker_status": self.broker_status,
            "filled_quantity": (
                str(self.filled_quantity)
                if self.filled_quantity is not None
                else ""
            ),
            "filled_average_price": (
                str(self.filled_average_price)
                if self.filled_average_price is not None
                else ""
            ),
            "ambiguity_reason": self.ambiguity_reason,
            "terminal": self.terminal,
            "safe_to_resubmit": self.safe_to_resubmit,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ReservationResult:
    status: str
    record: OrderJournalRecord

    @property
    def acquired(self) -> bool:
        return self.status == "reserved"


@dataclass(frozen=True, slots=True)
class RuntimeControl:
    trading_enabled: bool
    reason: str
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "trading_enabled": self.trading_enabled,
            "operator_paused": not self.trading_enabled,
            "reason": self.reason,
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class RuntimeLeaseResult:
    acquired: bool
    lease_name: str
    owner_run_id: str
    expires_at: datetime
    blocker: str

    def to_dict(self) -> dict[str, object]:
        return {
            "acquired": self.acquired,
            "lease_name": self.lease_name,
            "owner_run_id": self.owner_run_id,
            "expires_at": self.expires_at.isoformat(),
            "blocker": self.blocker,
        }


class SqliteOrderJournal:
    """Single-file durable journal with immediate transactions and WAL."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS journal_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS orders (
                    client_order_id TEXT PRIMARY KEY,
                    execution_plan_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity TEXT,
                    notional TEXT,
                    state TEXT NOT NULL,
                    broker_order_id TEXT NOT NULL DEFAULT '',
                    broker_status TEXT NOT NULL DEFAULT '',
                    filled_quantity TEXT,
                    filled_average_price TEXT,
                    ambiguity_reason TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS order_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_order_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    state TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY(client_order_id) REFERENCES orders(client_order_id)
                );
                CREATE INDEX IF NOT EXISTS order_events_client_id_idx
                    ON order_events(client_order_id, event_id);
                CREATE TABLE IF NOT EXISTS runtime_control (
                    singleton_id INTEGER PRIMARY KEY CHECK(singleton_id = 1),
                    trading_enabled INTEGER NOT NULL CHECK(trading_enabled IN (0, 1)),
                    reason TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runtime_leases (
                    lease_name TEXT PRIMARY KEY,
                    owner_run_id TEXT NOT NULL,
                    acquired_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
                """
            )
            existing = connection.execute(
                "SELECT value FROM journal_metadata WHERE key = 'schema_version'"
            ).fetchone()
            if existing is None:
                connection.execute(
                    "INSERT INTO journal_metadata(key, value) VALUES('schema_version', ?)",
                    (str(_SCHEMA_VERSION),),
                )
            elif existing[0] != str(_SCHEMA_VERSION):
                raise ValidationError("order journal schema version is unsupported.")

    def get_runtime_control(self) -> RuntimeControl:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT trading_enabled, reason, updated_at FROM runtime_control "
                "WHERE singleton_id = 1"
            ).fetchone()
        if row is None:
            return RuntimeControl(
                trading_enabled=True,
                reason="",
                updated_at=datetime.fromisoformat("1970-01-01T00:00:00+00:00"),
            )
        return RuntimeControl(
            trading_enabled=bool(row["trading_enabled"]),
            reason=row["reason"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def set_runtime_control(
        self,
        *,
        trading_enabled: bool,
        reason: str,
        occurred_at: datetime,
    ) -> RuntimeControl:
        if type(trading_enabled) is not bool:
            raise ValidationError("trading_enabled must be a boolean.")
        normalized_reason = reason.strip()
        if not trading_enabled and not normalized_reason:
            raise ValidationError("a reason is required to pause trading.")
        timestamp = _utc_datetime(occurred_at)
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO runtime_control(
                    singleton_id, trading_enabled, reason, updated_at
                ) VALUES(1, ?, ?, ?)
                ON CONFLICT(singleton_id) DO UPDATE SET
                    trading_enabled = excluded.trading_enabled,
                    reason = excluded.reason,
                    updated_at = excluded.updated_at
                """,
                (int(trading_enabled), normalized_reason, timestamp.isoformat()),
            )
            connection.commit()
        return self.get_runtime_control()

    def acquire_runtime_lease(
        self,
        *,
        lease_name: str,
        owner_run_id: str,
        occurred_at: datetime,
        ttl_seconds: int,
    ) -> RuntimeLeaseResult:
        name = lease_name.strip()
        owner = owner_run_id.strip()
        if not name or not owner:
            raise ValidationError("lease_name and owner_run_id are required.")
        if type(ttl_seconds) is not int or ttl_seconds <= 0:
            raise ValidationError("ttl_seconds must be a positive integer.")
        timestamp = _utc_datetime(occurred_at)
        expires_at = timestamp + timedelta(seconds=ttl_seconds)
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT owner_run_id, expires_at FROM runtime_leases "
                "WHERE lease_name = ?",
                (name,),
            ).fetchone()
            if row is not None:
                existing_expiry = datetime.fromisoformat(row["expires_at"])
                if existing_expiry > timestamp and row["owner_run_id"] != owner:
                    connection.commit()
                    return RuntimeLeaseResult(
                        acquired=False,
                        lease_name=name,
                        owner_run_id=row["owner_run_id"],
                        expires_at=existing_expiry,
                        blocker="runtime_instance_already_active",
                    )
            connection.execute(
                """
                INSERT INTO runtime_leases(
                    lease_name, owner_run_id, acquired_at, expires_at
                ) VALUES(?, ?, ?, ?)
                ON CONFLICT(lease_name) DO UPDATE SET
                    owner_run_id = excluded.owner_run_id,
                    acquired_at = excluded.acquired_at,
                    expires_at = excluded.expires_at
                """,
                (name, owner, timestamp.isoformat(), expires_at.isoformat()),
            )
            connection.commit()
        return RuntimeLeaseResult(
            acquired=True,
            lease_name=name,
            owner_run_id=owner,
            expires_at=expires_at,
            blocker="",
        )

    def release_runtime_lease(self, *, lease_name: str, owner_run_id: str) -> bool:
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "DELETE FROM runtime_leases WHERE lease_name = ? AND owner_run_id = ?",
                (lease_name.strip(), owner_run_id.strip()),
            )
            connection.commit()
            return cursor.rowcount == 1

    def force_release_runtime_lease(self, *, lease_name: str) -> bool:
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "DELETE FROM runtime_leases WHERE lease_name = ?",
                (lease_name.strip(),),
            )
            connection.commit()
            return cursor.rowcount == 1

    def reserve(
        self,
        reservation: OrderReservation,
        occurred_at: datetime,
    ) -> ReservationResult:
        if not isinstance(reservation, OrderReservation):
            raise ValidationError("reservation must be an OrderReservation.")
        timestamp = _utc_datetime(occurred_at)
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = self._select(connection, reservation.client_order_id)
            if existing is not None:
                status = (
                    "existing_same_request"
                    if _same_request(existing, reservation)
                    else "client_order_id_conflict"
                )
                connection.commit()
                return ReservationResult(status=status, record=existing)

            timestamp_text = timestamp.isoformat()
            connection.execute(
                """
                INSERT INTO orders(
                    client_order_id, execution_plan_id, run_id, symbol, side,
                    quantity, notional, state, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reservation.client_order_id,
                    reservation.execution_plan_id,
                    reservation.run_id,
                    reservation.symbol,
                    reservation.side,
                    _decimal_text(reservation.quantity),
                    _decimal_text(reservation.notional),
                    OrderJournalState.RESERVED.value,
                    timestamp_text,
                    timestamp_text,
                ),
            )
            self._append_event(
                connection,
                reservation.client_order_id,
                "reserved",
                OrderJournalState.RESERVED,
                timestamp,
                {"execution_plan_id": reservation.execution_plan_id},
            )
            connection.commit()
            record = self._select(connection, reservation.client_order_id)
            if record is None:
                raise ValidationError("order reservation was not persisted.")
            return ReservationResult(status="reserved", record=record)

    def mark_submit_attempted(
        self,
        client_order_id: str,
        occurred_at: datetime,
    ) -> OrderJournalRecord:
        return self._transition(
            client_order_id,
            occurred_at,
            allowed_from=(OrderJournalState.RESERVED,),
            target=OrderJournalState.SUBMIT_ATTEMPTED,
            event_type="submit_attempted",
        )

    def mark_submit_ambiguous(
        self,
        client_order_id: str,
        occurred_at: datetime,
        *,
        reason: str,
    ) -> OrderJournalRecord:
        return self._transition(
            client_order_id,
            occurred_at,
            allowed_from=(OrderJournalState.SUBMIT_ATTEMPTED, OrderJournalState.UNKNOWN),
            target=OrderJournalState.UNKNOWN,
            event_type="submit_ambiguous",
            updates={"ambiguity_reason": reason.strip() or "submit_response_ambiguous"},
        )

    def record_broker_observation(
        self,
        client_order_id: str,
        occurred_at: datetime,
        *,
        broker_order_id: str,
        broker_status: str,
        filled_quantity: Decimal | str | None = None,
        filled_average_price: Decimal | str | None = None,
    ) -> OrderJournalRecord:
        target = _state_from_broker_status(broker_status, filled_quantity)
        current = self.get(client_order_id)
        if current is None:
            raise ValidationError("order journal record is missing.")
        if current.terminal and current.state != target:
            raise ValidationError("terminal order journal state cannot change.")
        return self._transition(
            client_order_id,
            occurred_at,
            allowed_from=tuple(OrderJournalState),
            target=target,
            event_type="broker_observed",
            updates={
                "broker_order_id": broker_order_id.strip(),
                "broker_status": broker_status.strip().lower(),
                "filled_quantity": _decimal_text(
                    _optional_non_negative_decimal(filled_quantity, "filled_quantity")
                ),
                "filled_average_price": _decimal_text(
                    _optional_positive_decimal(
                        filled_average_price,
                        "filled_average_price",
                    )
                ),
                "ambiguity_reason": "",
            },
        )

    def get(self, client_order_id: str) -> OrderJournalRecord | None:
        self.initialize()
        with self._connect() as connection:
            return self._select(connection, client_order_id.strip())

    def unresolved(self, symbol: str | None = None) -> tuple[OrderJournalRecord, ...]:
        self.initialize()
        query = "SELECT * FROM orders WHERE state NOT IN (?, ?, ?, ?)"
        parameters: list[str] = [state.value for state in _TERMINAL_STATES]
        if symbol is not None:
            query += " AND symbol = ?"
            parameters.append(symbol_value(symbol))
        query += " ORDER BY created_at, client_order_id"
        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
            return tuple(_record_from_row(row) for row in rows)

    def backup(self, dest_path: str | Path) -> None:
        self.initialize()
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as source_conn:
            dest_conn = sqlite3.connect(dest)
            try:
                source_conn.backup(dest_conn)
            finally:
                dest_conn.close()

    def restore(self, src_path: str | Path) -> None:
        src = Path(src_path)
        if not src.is_file():
            raise ValidationError(f"Backup file not found: {src}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        src_conn = sqlite3.connect(src)
        try:
            with self._connect() as dest_conn:
                src_conn.backup(dest_conn)
        finally:
            src_conn.close()

    def _transition(
        self,
        client_order_id: str,
        occurred_at: datetime,
        *,
        allowed_from: tuple[OrderJournalState, ...],
        target: OrderJournalState,
        event_type: str,
        updates: dict[str, str | None] | None = None,
    ) -> OrderJournalRecord:
        timestamp = _utc_datetime(occurred_at)
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = self._select(connection, client_order_id.strip())
            if current is None:
                raise ValidationError("order journal record is missing.")
            if current.state not in allowed_from:
                raise ValidationError(
                    f"order journal transition from {current.state.value} is invalid."
                )
            values = {"state": target.value, "updated_at": timestamp.isoformat()}
            values.update(updates or {})
            assignments = ", ".join(f"{name} = ?" for name in values)
            connection.execute(
                f"UPDATE orders SET {assignments} WHERE client_order_id = ?",
                (*values.values(), current.client_order_id),
            )
            self._append_event(
                connection,
                current.client_order_id,
                event_type,
                target,
                timestamp,
                updates or {},
            )
            connection.commit()
            record = self._select(connection, current.client_order_id)
            if record is None:
                raise ValidationError("order journal transition was not persisted.")
            return record

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=5,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @staticmethod
    def _select(
        connection: sqlite3.Connection,
        client_order_id: str,
    ) -> OrderJournalRecord | None:
        row = connection.execute(
            "SELECT * FROM orders WHERE client_order_id = ?",
            (client_order_id,),
        ).fetchone()
        return _record_from_row(row) if row is not None else None

    @staticmethod
    def _append_event(
        connection: sqlite3.Connection,
        client_order_id: str,
        event_type: str,
        state: OrderJournalState,
        occurred_at: datetime,
        payload: dict[str, object],
    ) -> None:
        connection.execute(
            """
            INSERT INTO order_events(
                client_order_id, event_type, state, occurred_at, payload_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                client_order_id,
                event_type,
                state.value,
                occurred_at.isoformat(),
                json.dumps(payload, sort_keys=True, separators=(",", ":")),
            ),
        )


def _record_from_row(row: sqlite3.Row) -> OrderJournalRecord:
    return OrderJournalRecord(
        client_order_id=row["client_order_id"],
        execution_plan_id=row["execution_plan_id"],
        run_id=row["run_id"],
        symbol=row["symbol"],
        side=row["side"],
        quantity=_optional_decimal_text(row["quantity"]),
        notional=_optional_decimal_text(row["notional"]),
        state=OrderJournalState(row["state"]),
        broker_order_id=row["broker_order_id"],
        broker_status=row["broker_status"],
        filled_quantity=_optional_decimal_text(row["filled_quantity"]),
        filled_average_price=_optional_decimal_text(row["filled_average_price"]),
        ambiguity_reason=row["ambiguity_reason"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _same_request(record: OrderJournalRecord, reservation: OrderReservation) -> bool:
    return (
        record.execution_plan_id == reservation.execution_plan_id
        and record.symbol == reservation.symbol
        and record.side == reservation.side
        and record.quantity == reservation.quantity
        and record.notional == reservation.notional
    )


def _state_from_broker_status(
    broker_status: str,
    filled_quantity: Decimal | str | None,
) -> OrderJournalState:
    status = broker_status.strip().lower()
    normalized = {
        "new": OrderJournalState.ACCEPTED,
        "accepted": OrderJournalState.ACCEPTED,
        "pending_new": OrderJournalState.ACCEPTED,
        "open": OrderJournalState.OPEN,
        "pending_cancel": OrderJournalState.OPEN,
        "partially_filled": OrderJournalState.PARTIALLY_FILLED,
        "filled": OrderJournalState.FILLED,
        "rejected": OrderJournalState.REJECTED,
        "canceled": OrderJournalState.CANCELED,
        "cancelled": OrderJournalState.CANCELED,
        "expired": OrderJournalState.EXPIRED,
    }.get(status)
    if normalized is None:
        return OrderJournalState.UNKNOWN
    observed_filled = _optional_non_negative_decimal(filled_quantity, "filled_quantity")
    if (
        observed_filled is not None
        and observed_filled > 0
        and normalized in {OrderJournalState.ACCEPTED, OrderJournalState.OPEN}
    ):
        return OrderJournalState.PARTIALLY_FILLED
    return normalized


def _utc_datetime(value: datetime) -> datetime:
    try:
        return require_utc_datetime(value)
    except (TypeError, ValidationError) as exc:
        raise ValidationError("occurred_at must be a timezone-aware UTC datetime.") from exc


def _optional_positive_decimal(
    value: Decimal | str | None,
    field_name: str,
) -> Decimal | None:
    if value is None:
        return None
    parsed = decimal_value(value, field_name)
    if parsed <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return parsed


def _optional_non_negative_decimal(
    value: Decimal | str | None,
    field_name: str,
) -> Decimal | None:
    if value is None or value == "":
        return None
    parsed = decimal_value(value, field_name)
    if parsed < 0:
        raise ValidationError(f"{field_name} must be non-negative.")
    return parsed


def _decimal_text(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _optional_decimal_text(value: str | None) -> Decimal | None:
    return Decimal(value) if value not in (None, "") else None
