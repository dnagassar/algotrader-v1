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
    "CycleClaimResult",
    "LeaseDetails",
    "OrderJournalRecord",
    "OrderJournalState",
    "OrderReservation",
    "SupervisorCycle",
    "ReservationResult",
    "RuntimeControl",
    "RuntimeLeaseResult",
    "SqliteOrderJournal",
]

_SCHEMA_VERSION = 3


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
class LeaseDetails:
    lease_name: str
    owner_run_id: str
    acquired_at: datetime
    expires_at: datetime
    lease_token: str
    fencing_generation: int


@dataclass(frozen=True, slots=True)
class SupervisorCycle:
    """Durable outcome for one deterministic completed exchange session."""

    session_id: str
    attempt_count: int
    last_attempt_at: datetime
    last_success_at: datetime | None
    outcome: str
    last_error: str

    @property
    def succeeded(self) -> bool:
        return self.last_success_at is not None


@dataclass(frozen=True, slots=True)
class CycleClaimResult:
    status: str
    cycle: SupervisorCycle

    @property
    def acquired(self) -> bool:
        return self.status == "claimed"


@dataclass(frozen=True, slots=True)
class RuntimeControl:
    trading_enabled: bool
    reason: str
    updated_at: datetime
    stop_requested: bool = False
    control_generation: int = 0
    last_attempt_at: str = ""
    last_success_at: str = ""
    last_blocked_reason: str = ""
    heartbeat_at: str = ""
    supervisor_pid: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "trading_enabled": self.trading_enabled,
            "operator_paused": not self.trading_enabled,
            "reason": self.reason,
            "updated_at": self.updated_at.isoformat(),
            "stop_requested": self.stop_requested,
            "control_generation": self.control_generation,
            "last_attempt_at": self.last_attempt_at,
            "last_success_at": self.last_success_at,
            "last_blocked_reason": self.last_blocked_reason,
            "heartbeat_at": self.heartbeat_at,
            "supervisor_pid": self.supervisor_pid,
        }


@dataclass(frozen=True, slots=True)
class RuntimeLeaseResult:
    acquired: bool
    lease_name: str
    owner_run_id: str
    expires_at: datetime
    blocker: str
    lease_token: str = ""
    fencing_generation: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "acquired": self.acquired,
            "lease_name": self.lease_name,
            "owner_run_id": self.owner_run_id,
            "expires_at": self.expires_at.isoformat(),
            "blocker": self.blocker,
            "lease_token": self.lease_token,
            "fencing_generation": self.fencing_generation,
        }


class SqliteOrderJournal:
    """Single-file durable journal with immediate transactions and WAL."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS journal_metadata "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            existing = connection.execute(
                "SELECT value FROM journal_metadata WHERE key = 'schema_version'"
            ).fetchone()
            if existing is None:
                has_existing_orders = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'orders'"
                ).fetchone()
                if has_existing_orders is not None:
                    raise ValidationError("order journal metadata is corrupt.")
                self._create_schema_v3(connection)
                connection.execute(
                    "INSERT INTO journal_metadata(key, value) VALUES('schema_version', ?)",
                    (str(_SCHEMA_VERSION),),
                )
                return
            try:
                version = int(existing[0])
            except (TypeError, ValueError) as exc:
                raise ValidationError("order journal schema version is corrupt.") from exc
            if version > _SCHEMA_VERSION:
                raise ValidationError("order journal schema version is unsupported.")
            if version < 1:
                raise ValidationError("order journal schema version is unsupported.")
            if version == _SCHEMA_VERSION:
                self._require_schema_v3(connection)
                return
            connection.execute("BEGIN IMMEDIATE")
            try:
                if version == 1:
                    self._migrate_v1_to_v2(connection)
                    version = 2
                if version == 2:
                    self._migrate_v2_to_v3(connection)
                    version = 3
                if version != _SCHEMA_VERSION:
                    raise ValidationError("order journal schema version is unsupported.")
                connection.commit()
            except Exception as exc:
                connection.rollback()
                if isinstance(exc, ValidationError):
                    raise
                raise ValidationError(
                    f"order journal schema migration failed: {exc}"
                ) from exc

    @staticmethod
    def _create_schema_v3(connection: sqlite3.Connection) -> None:
        statements = (
            """
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
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS order_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_order_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                state TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                FOREIGN KEY(client_order_id) REFERENCES orders(client_order_id)
            )
            """,
            "CREATE INDEX IF NOT EXISTS order_events_client_id_idx ON order_events(client_order_id, event_id)",
            """
            CREATE TABLE IF NOT EXISTS runtime_control (
                singleton_id INTEGER PRIMARY KEY CHECK(singleton_id = 1),
                trading_enabled INTEGER NOT NULL CHECK(trading_enabled IN (0, 1)),
                reason TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                stop_requested INTEGER NOT NULL DEFAULT 0 CHECK(stop_requested IN (0, 1)),
                control_generation INTEGER NOT NULL DEFAULT 0,
                last_attempt_at TEXT NOT NULL DEFAULT '',
                last_success_at TEXT NOT NULL DEFAULT '',
                last_blocked_reason TEXT NOT NULL DEFAULT '',
                heartbeat_at TEXT NOT NULL DEFAULT '',
                supervisor_pid INTEGER NOT NULL DEFAULT 0
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS runtime_leases (
                lease_name TEXT PRIMARY KEY,
                owner_run_id TEXT NOT NULL,
                acquired_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                lease_token TEXT NOT NULL DEFAULT '',
                fencing_generation INTEGER NOT NULL DEFAULT 0
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS supervisor_cycles (
                session_id TEXT PRIMARY KEY,
                attempt_count INTEGER NOT NULL,
                last_attempt_at TEXT NOT NULL,
                last_success_at TEXT NOT NULL DEFAULT '',
                outcome TEXT NOT NULL,
                last_error TEXT NOT NULL DEFAULT ''
            )
            """,
        )
        for statement in statements:
            connection.execute(statement)

    @staticmethod
    def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
        return {
            str(row["name"])
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }

    @classmethod
    def _require_columns(
        cls,
        connection: sqlite3.Connection,
        table_name: str,
        required: set[str],
    ) -> None:
        missing = required - cls._table_columns(connection, table_name)
        if missing:
            raise ValidationError(
                f"order journal {table_name} schema is corrupt: missing {sorted(missing)[0]}."
            )

    @classmethod
    def _require_schema_v3(cls, connection: sqlite3.Connection) -> None:
        cls._require_columns(
            connection,
            "orders",
            {"client_order_id", "execution_plan_id", "run_id", "symbol", "state"},
        )
        cls._require_columns(
            connection,
            "runtime_control",
            {
                "trading_enabled", "reason", "updated_at", "stop_requested",
                "control_generation", "last_attempt_at", "last_success_at",
                "last_blocked_reason", "heartbeat_at", "supervisor_pid",
            },
        )
        cls._require_columns(
            connection,
            "runtime_leases",
            {"lease_name", "owner_run_id", "expires_at", "lease_token", "fencing_generation"},
        )
        cls._require_columns(
            connection,
            "supervisor_cycles",
            {"session_id", "attempt_count", "last_attempt_at", "last_success_at", "outcome", "last_error"},
        )

    @classmethod
    def _migrate_v1_to_v2(cls, connection: sqlite3.Connection) -> None:
        cls._require_columns(
            connection,
            "runtime_control",
            {"singleton_id", "trading_enabled", "reason", "updated_at"},
        )
        cls._require_columns(
            connection,
            "runtime_leases",
            {"lease_name", "owner_run_id", "acquired_at", "expires_at"},
        )
        statements = (
            "ALTER TABLE runtime_leases ADD COLUMN lease_token TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE runtime_leases ADD COLUMN fencing_generation INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE runtime_control ADD COLUMN stop_requested INTEGER NOT NULL DEFAULT 0 CHECK(stop_requested IN (0, 1))",
            "ALTER TABLE runtime_control ADD COLUMN control_generation INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE runtime_control ADD COLUMN last_attempt_at TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE runtime_control ADD COLUMN last_success_at TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE runtime_control ADD COLUMN last_blocked_reason TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE runtime_control ADD COLUMN heartbeat_at TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE runtime_control ADD COLUMN supervisor_pid INTEGER NOT NULL DEFAULT 0",
        )
        for statement in statements:
            connection.execute(statement)
        connection.execute(
            "UPDATE journal_metadata SET value = '2' WHERE key = 'schema_version'"
        )

    @staticmethod
    def _migrate_v2_to_v3(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE supervisor_cycles (
                session_id TEXT PRIMARY KEY,
                attempt_count INTEGER NOT NULL,
                last_attempt_at TEXT NOT NULL,
                last_success_at TEXT NOT NULL DEFAULT '',
                outcome TEXT NOT NULL,
                last_error TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.execute(
            "UPDATE journal_metadata SET value = '3' WHERE key = 'schema_version'"
        )

    def get_runtime_control(self) -> RuntimeControl:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT trading_enabled, reason, updated_at, stop_requested, control_generation, "
                "last_attempt_at, last_success_at, last_blocked_reason, heartbeat_at, supervisor_pid "
                "FROM runtime_control WHERE singleton_id = 1"
            ).fetchone()
        if row is None:
            return RuntimeControl(
                trading_enabled=True,
                reason="",
                updated_at=datetime.fromisoformat("1970-01-01T00:00:00+00:00"),
                stop_requested=False,
                control_generation=0,
                last_attempt_at="",
                last_success_at="",
                last_blocked_reason="",
                heartbeat_at="",
                supervisor_pid=0,
            )
        return RuntimeControl(
            trading_enabled=bool(row["trading_enabled"]),
            reason=row["reason"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
            stop_requested=bool(row["stop_requested"]),
            control_generation=int(row["control_generation"]),
            last_attempt_at=row["last_attempt_at"],
            last_success_at=row["last_success_at"],
            last_blocked_reason=row["last_blocked_reason"],
            heartbeat_at=row["heartbeat_at"],
            supervisor_pid=int(row["supervisor_pid"]),
        )

    def set_runtime_control(
        self,
        *,
        trading_enabled: bool,
        reason: str,
        occurred_at: datetime,
        stop_requested: bool | None = None,
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
            row = connection.execute(
                "SELECT trading_enabled, stop_requested, control_generation, last_attempt_at, last_success_at, "
                "last_blocked_reason, heartbeat_at, supervisor_pid FROM runtime_control WHERE singleton_id = 1"
            ).fetchone()
            if row is not None:
                current_stop = bool(row["stop_requested"])
                current_gen = int(row["control_generation"])
                last_attempt = row["last_attempt_at"]
                last_success = row["last_success_at"]
                last_blocked = row["last_blocked_reason"]
                heartbeat = row["heartbeat_at"]
                pid = int(row["supervisor_pid"])
            else:
                current_stop = False
                current_gen = 0
                last_attempt = ""
                last_success = ""
                last_blocked = ""
                heartbeat = ""
                pid = 0

            new_stop = current_stop if stop_requested is None else stop_requested
            if new_stop != current_stop or trading_enabled != (row is not None and bool(row["trading_enabled"])):
                new_gen = current_gen + 1
            else:
                new_gen = current_gen

            connection.execute(
                """
                INSERT INTO runtime_control(
                    singleton_id, trading_enabled, reason, updated_at, stop_requested, control_generation,
                    last_attempt_at, last_success_at, last_blocked_reason, heartbeat_at, supervisor_pid
                ) VALUES(1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(singleton_id) DO UPDATE SET
                    trading_enabled = excluded.trading_enabled,
                    reason = excluded.reason,
                    updated_at = excluded.updated_at,
                    stop_requested = excluded.stop_requested,
                    control_generation = excluded.control_generation
                """,
                (
                    int(trading_enabled),
                    normalized_reason,
                    timestamp.isoformat(),
                    int(new_stop),
                    new_gen,
                    last_attempt,
                    last_success,
                    last_blocked,
                    heartbeat,
                    pid,
                ),
            )
            connection.commit()
        return self.get_runtime_control()

    def update_supervisor_state(self, *, supervisor_pid: int, stop_requested: bool, occurred_at: datetime) -> None:
        timestamp = _utc_datetime(occurred_at)
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT trading_enabled, reason, control_generation FROM runtime_control WHERE singleton_id = 1"
            ).fetchone()
            if row is not None:
                trading_enabled = int(row["trading_enabled"])
                reason = row["reason"]
                gen = int(row["control_generation"])
            else:
                trading_enabled = 1
                reason = ""
                gen = 0
            connection.execute(
                """
                INSERT INTO runtime_control(
                    singleton_id, trading_enabled, reason, updated_at, stop_requested, control_generation, supervisor_pid
                ) VALUES(1, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(singleton_id) DO UPDATE SET
                    stop_requested = excluded.stop_requested,
                    supervisor_pid = excluded.supervisor_pid,
                    updated_at = excluded.updated_at
                """,
                (trading_enabled, reason, timestamp.isoformat(), int(stop_requested), gen, supervisor_pid),
            )
            connection.commit()

    def request_supervisor_start(self, occurred_at: datetime) -> RuntimeControl:
        """Clear stale acknowledgement state without changing the trading pause."""

        timestamp = _utc_datetime(occurred_at)
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT trading_enabled, reason, control_generation FROM runtime_control WHERE singleton_id = 1"
            ).fetchone()
            trading_enabled = int(row["trading_enabled"]) if row is not None else 1
            reason = row["reason"] if row is not None else ""
            generation = int(row["control_generation"]) if row is not None else 0
            active_lease = connection.execute(
                "SELECT 1 FROM runtime_leases WHERE lease_name = ? AND expires_at > ?",
                ("paper-autopilot", timestamp.isoformat()),
            ).fetchone()
            if active_lease is not None:
                connection.commit()
                raise ValidationError("Supervisor start failed: active runtime lease exists.")
            connection.execute(
                """
                INSERT INTO runtime_control(
                    singleton_id, trading_enabled, reason, updated_at, stop_requested,
                    control_generation, heartbeat_at, supervisor_pid
                ) VALUES(1, ?, ?, ?, 0, ?, '', 0)
                ON CONFLICT(singleton_id) DO UPDATE SET
                    stop_requested = 0,
                    heartbeat_at = '',
                    supervisor_pid = 0,
                    updated_at = excluded.updated_at
                """,
                (trading_enabled, reason, timestamp.isoformat(), generation),
            )
            connection.commit()
        return self.get_runtime_control()

    def acknowledge_supervisor_start(
        self,
        *,
        lease_name: str,
        owner_run_id: str,
        lease_token: str,
        fencing_generation: int,
        supervisor_pid: int,
        occurred_at: datetime,
    ) -> bool:
        """Record startup only while the caller still owns the fenced lease."""

        if type(supervisor_pid) is not int or supervisor_pid <= 0:
            raise ValidationError("supervisor_pid must be a positive integer.")
        timestamp = _utc_datetime(occurred_at)
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if not self._lease_matches(
                connection,
                lease_name=lease_name,
                owner_run_id=owner_run_id,
                lease_token=lease_token,
                fencing_generation=fencing_generation,
                occurred_at=timestamp,
            ):
                connection.commit()
                return False
            connection.execute(
                """
                INSERT INTO runtime_control(
                    singleton_id, trading_enabled, reason, updated_at,
                    stop_requested, control_generation, heartbeat_at, supervisor_pid
                ) VALUES(1, 1, '', ?, 0, 0, ?, ?)
                ON CONFLICT(singleton_id) DO UPDATE SET
                    heartbeat_at = excluded.heartbeat_at,
                    supervisor_pid = excluded.supervisor_pid,
                    updated_at = excluded.updated_at
                """,
                (timestamp.isoformat(), timestamp.isoformat(), supervisor_pid),
            )
            connection.commit()
        return True

    def update_heartbeat(
        self,
        *,
        lease_name: str,
        owner_run_id: str,
        lease_token: str,
        fencing_generation: int,
        occurred_at: datetime,
    ) -> bool:
        """Refresh the heartbeat only for the current, unexpired lease owner."""

        timestamp = _utc_datetime(occurred_at)
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if not self._lease_matches(
                connection,
                lease_name=lease_name,
                owner_run_id=owner_run_id,
                lease_token=lease_token,
                fencing_generation=fencing_generation,
                occurred_at=timestamp,
            ):
                connection.commit()
                return False
            connection.execute(
                "UPDATE runtime_control SET heartbeat_at = ?, updated_at = ? WHERE singleton_id = 1",
                (timestamp.isoformat(), timestamp.isoformat()),
            )
            connection.commit()
        return True

    def clear_supervisor_acknowledgment(
        self,
        *,
        lease_name: str,
        owner_run_id: str,
        lease_token: str,
        fencing_generation: int,
        occurred_at: datetime,
    ) -> bool:
        """Clear the PID acknowledgement without allowing a stale owner to erase a replacement."""

        timestamp = _utc_datetime(occurred_at)
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            lease = connection.execute(
                "SELECT owner_run_id, lease_token, fencing_generation FROM runtime_leases WHERE lease_name = ?",
                (lease_name.strip(),),
            ).fetchone()
            if lease is not None and (
                lease["owner_run_id"] != owner_run_id.strip()
                or lease["lease_token"] != lease_token.strip()
                or int(lease["fencing_generation"]) != fencing_generation
            ):
                connection.commit()
                return False
            connection.execute(
                "UPDATE runtime_control SET supervisor_pid = 0, updated_at = ? WHERE singleton_id = 1",
                (timestamp.isoformat(),),
            )
            connection.commit()
        return True

    def update_last_attempt(self, occurred_at: datetime) -> None:
        timestamp = _utc_datetime(occurred_at)
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE runtime_control SET last_attempt_at = ?, updated_at = ? WHERE singleton_id = 1",
                (timestamp.isoformat(), timestamp.isoformat()),
            )
            connection.commit()

    def update_last_success(self, occurred_at: datetime) -> None:
        timestamp = _utc_datetime(occurred_at)
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE runtime_control SET last_success_at = ?, last_blocked_reason = '', updated_at = ? WHERE singleton_id = 1",
                (timestamp.isoformat(), timestamp.isoformat()),
            )
            connection.commit()

    def update_last_blocked(self, occurred_at: datetime, reason: str) -> None:
        timestamp = _utc_datetime(occurred_at)
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE runtime_control SET last_blocked_reason = ?, updated_at = ? WHERE singleton_id = 1",
                (reason.strip(), timestamp.isoformat()),
            )
            connection.commit()

    def acquire_runtime_lease(
        self,
        *,
        lease_name: str,
        owner_run_id: str,
        occurred_at: datetime,
        ttl_seconds: int,
        lease_token: str | None = None,
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
                "SELECT owner_run_id, expires_at, lease_token, fencing_generation FROM runtime_leases "
                "WHERE lease_name = ?",
                (name,),
            ).fetchone()
            if row is not None:
                existing_expiry = datetime.fromisoformat(row["expires_at"])
                existing_token = row["lease_token"]
                existing_gen = int(row["fencing_generation"])
                if existing_expiry > timestamp:
                    if (
                        lease_token is not None
                        and row["owner_run_id"] == owner
                        and existing_token == lease_token
                    ):
                        new_token = existing_token
                        new_gen = existing_gen
                    else:
                        connection.commit()
                        return RuntimeLeaseResult(
                            acquired=False,
                            lease_name=name,
                            owner_run_id=row["owner_run_id"],
                            expires_at=existing_expiry,
                            blocker="runtime_instance_already_active",
                            lease_token=existing_token,
                            fencing_generation=existing_gen,
                        )
                else:
                    import uuid
                    new_token = str(uuid.uuid4())
                    new_gen = existing_gen + 1
            else:
                import uuid
                new_token = str(uuid.uuid4())
                new_gen = 1
            connection.execute(
                """
                INSERT INTO runtime_leases(
                    lease_name, owner_run_id, acquired_at, expires_at, lease_token, fencing_generation
                ) VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(lease_name) DO UPDATE SET
                    owner_run_id = excluded.owner_run_id,
                    acquired_at = excluded.acquired_at,
                    expires_at = excluded.expires_at,
                    lease_token = excluded.lease_token,
                    fencing_generation = excluded.fencing_generation
                """,
                (name, owner, timestamp.isoformat(), expires_at.isoformat(), new_token, new_gen),
            )
            connection.commit()
        return RuntimeLeaseResult(
            acquired=True,
            lease_name=name,
            owner_run_id=owner,
            expires_at=expires_at,
            blocker="",
            lease_token=new_token,
            fencing_generation=new_gen,
        )

    def release_runtime_lease(self, *, lease_name: str, owner_run_id: str, lease_token: str) -> bool:
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT lease_token, acquired_at FROM runtime_leases WHERE lease_name = ?",
                (lease_name.strip(),),
            ).fetchone()
            if row is None or row["lease_token"] != lease_token:
                connection.commit()
                return False
            cursor = connection.execute(
                """
                UPDATE runtime_leases SET expires_at = acquired_at
                WHERE lease_name = ? AND owner_run_id = ? AND lease_token = ?
                """,
                (lease_name.strip(), owner_run_id.strip(), lease_token.strip()),
            )
            connection.commit()
            return cursor.rowcount == 1

    def get_lease_details(self, lease_name: str) -> LeaseDetails | None:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT owner_run_id, acquired_at, expires_at, lease_token, fencing_generation "
                "FROM runtime_leases WHERE lease_name = ?",
                (lease_name.strip(),),
            ).fetchone()
        if row is None:
            return None
        return LeaseDetails(
            lease_name=lease_name.strip(),
            owner_run_id=row["owner_run_id"],
            acquired_at=datetime.fromisoformat(row["acquired_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
            lease_token=row["lease_token"],
            fencing_generation=int(row["fencing_generation"]),
        )

    def claim_supervisor_cycle(
        self,
        *,
        session_id: str,
        occurred_at: datetime,
        max_attempts: int,
    ) -> CycleClaimResult:
        """Claim one durable session cycle, retrying only unfinished local failures."""

        identity = _nonempty_text(session_id, "session_id")
        if type(max_attempts) is not int or max_attempts <= 0:
            raise ValidationError("max_attempts must be a positive integer.")
        timestamp = _utc_datetime(occurred_at)
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM supervisor_cycles WHERE session_id = ?", (identity,)
            ).fetchone()
            if row is None:
                cycle = SupervisorCycle(
                    session_id=identity,
                    attempt_count=1,
                    last_attempt_at=timestamp,
                    last_success_at=None,
                    outcome="in_progress",
                    last_error="",
                )
                connection.execute(
                    """
                    INSERT INTO supervisor_cycles(
                        session_id, attempt_count, last_attempt_at, last_success_at, outcome, last_error
                    ) VALUES(?, ?, ?, '', ?, '')
                    """,
                    (identity, cycle.attempt_count, timestamp.isoformat(), cycle.outcome),
                )
                connection.commit()
                return CycleClaimResult("claimed", cycle)
            cycle = _supervisor_cycle_from_row(row)
            if cycle.succeeded:
                connection.commit()
                return CycleClaimResult("already_successful", cycle)
            if cycle.outcome in {"safety_failure", "permanent_failure"}:
                connection.commit()
                return CycleClaimResult("nonretryable_failure", cycle)
            if cycle.attempt_count >= max_attempts:
                connection.commit()
                return CycleClaimResult("retry_exhausted", cycle)
            updated = SupervisorCycle(
                session_id=cycle.session_id,
                attempt_count=cycle.attempt_count + 1,
                last_attempt_at=timestamp,
                last_success_at=None,
                outcome="in_progress",
                last_error="",
            )
            connection.execute(
                """
                UPDATE supervisor_cycles
                SET attempt_count = ?, last_attempt_at = ?, outcome = ?, last_error = ''
                WHERE session_id = ?
                """,
                (
                    updated.attempt_count,
                    timestamp.isoformat(),
                    updated.outcome,
                    identity,
                ),
            )
            connection.commit()
            return CycleClaimResult("claimed", updated)

    def complete_supervisor_cycle(
        self,
        *,
        session_id: str,
        occurred_at: datetime,
        outcome: str,
        error: str = "",
    ) -> SupervisorCycle:
        """Persist a terminal or retryable deterministic cycle outcome."""

        identity = _nonempty_text(session_id, "session_id")
        normalized_outcome = _nonempty_text(outcome, "outcome")
        if normalized_outcome not in {
            "successful",
            "retryable_failure",
            "safety_failure",
            "permanent_failure",
        }:
            raise ValidationError("supervisor cycle outcome is invalid.")
        timestamp = _utc_datetime(occurred_at)
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM supervisor_cycles WHERE session_id = ?", (identity,)
            ).fetchone()
            if row is None:
                connection.rollback()
                raise ValidationError("supervisor cycle must be claimed before completion.")
            existing = _supervisor_cycle_from_row(row)
            if existing.succeeded and normalized_outcome != "successful":
                connection.rollback()
                raise ValidationError("successful supervisor cycle cannot be changed.")
            success_at = timestamp.isoformat() if normalized_outcome == "successful" else ""
            safe_error = error.strip()[:240]
            connection.execute(
                """
                UPDATE supervisor_cycles
                SET last_success_at = ?, outcome = ?, last_error = ?
                WHERE session_id = ?
                """,
                (success_at, normalized_outcome, safe_error, identity),
            )
            connection.commit()
        cycle = self.get_supervisor_cycle(identity)
        if cycle is None:
            raise ValidationError("supervisor cycle completion was not persisted.")
        return cycle

    def get_supervisor_cycle(self, session_id: str) -> SupervisorCycle | None:
        identity = _nonempty_text(session_id, "session_id")
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM supervisor_cycles WHERE session_id = ?", (identity,)
            ).fetchone()
        return _supervisor_cycle_from_row(row) if row is not None else None

    def claim_pre_mutation_submit(
        self,
        *,
        client_order_id: str,
        execution_plan_id: str,
        reservation_run_id: str,
        lease_name: str,
        lease_owner_run_id: str,
        lease_token: str,
        fencing_generation: int,
        canonical_risk_allowed: bool,
        snapshot_fresh: bool,
        occurred_at: datetime,
    ) -> OrderJournalRecord:
        """Atomically fence and journal the final pre-broker submit transition.

        This is intentionally the one durable mutation gate.  Once it returns a
        ``SUBMIT_ATTEMPTED`` record, a caller may invoke its injected broker
        boundary exactly once; every failed predicate leaves that boundary
        untouched.
        """

        order_id = _nonempty_text(client_order_id, "client_order_id")
        plan_id = _nonempty_text(execution_plan_id, "execution_plan_id")
        run_id = _nonempty_text(reservation_run_id, "reservation_run_id")
        if type(canonical_risk_allowed) is not bool or not canonical_risk_allowed:
            raise ValidationError("canonical_risk_not_allowed")
        if type(snapshot_fresh) is not bool or not snapshot_fresh:
            raise ValidationError("required_snapshot_not_fresh")
        if type(fencing_generation) is not int or fencing_generation <= 0:
            raise ValidationError("fencing_generation_invalid")
        timestamp = _utc_datetime(occurred_at)
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            control = connection.execute(
                "SELECT trading_enabled, stop_requested FROM runtime_control WHERE singleton_id = 1"
            ).fetchone()
            if control is not None and not bool(control["trading_enabled"]):
                connection.rollback()
                raise ValidationError("trading_disabled")
            if control is not None and bool(control["stop_requested"]):
                connection.rollback()
                raise ValidationError("stop_requested")
            if not self._lease_matches(
                connection,
                lease_name=lease_name,
                owner_run_id=lease_owner_run_id,
                lease_token=lease_token,
                fencing_generation=fencing_generation,
                occurred_at=timestamp,
            ):
                connection.rollback()
                raise ValidationError("runtime_lease_fencing_mismatch")
            record = self._select(connection, order_id)
            if record is None:
                connection.rollback()
                raise ValidationError("idempotency_reservation_missing")
            if record.execution_plan_id != plan_id:
                connection.rollback()
                raise ValidationError("immutable_execution_plan_identity_mismatch")
            if record.run_id != run_id:
                connection.rollback()
                raise ValidationError("idempotency_reservation_owner_mismatch")
            if record.state is not OrderJournalState.RESERVED:
                connection.rollback()
                raise ValidationError("idempotency_reservation_not_submit_ready")
            terminal_values = tuple(state.value for state in _TERMINAL_STATES)
            placeholders = ", ".join("?" for _ in terminal_values)
            conflicts = connection.execute(
                f"""
                SELECT client_order_id, state FROM orders
                WHERE client_order_id != ?
                  AND state NOT IN ({placeholders})
                ORDER BY created_at, client_order_id
                """,
                (order_id, *terminal_values),
            ).fetchall()
            if conflicts:
                connection.rollback()
                if any(row["state"] == OrderJournalState.UNKNOWN.value for row in conflicts):
                    raise ValidationError("unknown_order_state_present")
                raise ValidationError("conflicting_nonterminal_order_state_present")
            connection.execute(
                "UPDATE orders SET state = ?, updated_at = ? WHERE client_order_id = ?",
                (
                    OrderJournalState.SUBMIT_ATTEMPTED.value,
                    timestamp.isoformat(),
                    order_id,
                ),
            )
            self._append_event(
                connection,
                order_id,
                "submit_attempted",
                OrderJournalState.SUBMIT_ATTEMPTED,
                timestamp,
                {
                    "execution_plan_id": plan_id,
                    "fencing_generation": fencing_generation,
                },
            )
            connection.commit()
            updated = self._select(connection, order_id)
        if updated is None:
            raise ValidationError("pre-mutation journal claim was not persisted.")
        return updated

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

    def records(self, symbol: str | None = None) -> tuple[OrderJournalRecord, ...]:
        """Return durable records for offline reconciliation only."""

        self.initialize()
        query = "SELECT * FROM orders"
        parameters: tuple[str, ...] = ()
        if symbol is not None:
            query += " WHERE symbol = ?"
            parameters = (symbol_value(symbol),)
        query += " ORDER BY created_at, client_order_id"
        with self._connect() as connection:
            return tuple(
                _record_from_row(row)
                for row in connection.execute(query, parameters).fetchall()
            )

    def record_reconciliation_result(self, result: dict[str, object]) -> None:
        """Persist the most recent deterministic offline reconciliation receipt."""

        if not isinstance(result, dict):
            raise ValidationError("reconciliation result must be a dictionary.")
        try:
            payload = json.dumps(result, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            raise ValidationError("reconciliation result is not JSON-safe.") from exc
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO journal_metadata(key, value) VALUES('last_reconciliation_result', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (payload,),
            )
            connection.commit()

    def last_reconciliation_result(self) -> dict[str, object] | None:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM journal_metadata WHERE key = 'last_reconciliation_result'"
            ).fetchone()
        if row is None:
            return None
        try:
            parsed = json.loads(row["value"])
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValidationError("stored reconciliation result is corrupt.") from exc
        if not isinstance(parsed, dict):
            raise ValidationError("stored reconciliation result is corrupt.")
        return parsed

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
    def _lease_matches(
        connection: sqlite3.Connection,
        *,
        lease_name: str,
        owner_run_id: str,
        lease_token: str,
        fencing_generation: int,
        occurred_at: datetime,
    ) -> bool:
        row = connection.execute(
            """
            SELECT owner_run_id, expires_at, lease_token, fencing_generation
            FROM runtime_leases WHERE lease_name = ?
            """,
            (_nonempty_text(lease_name, "lease_name"),),
        ).fetchone()
        if row is None:
            return False
        return (
            row["owner_run_id"] == _nonempty_text(owner_run_id, "lease_owner_run_id")
            and row["lease_token"] == _nonempty_text(lease_token, "lease_token")
            and int(row["fencing_generation"]) == fencing_generation
            and datetime.fromisoformat(row["expires_at"]) > occurred_at
        )

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


def _supervisor_cycle_from_row(row: sqlite3.Row) -> SupervisorCycle:
    success_text = str(row["last_success_at"] or "")
    return SupervisorCycle(
        session_id=row["session_id"],
        attempt_count=int(row["attempt_count"]),
        last_attempt_at=datetime.fromisoformat(row["last_attempt_at"]),
        last_success_at=(datetime.fromisoformat(success_text) if success_text else None),
        outcome=row["outcome"],
        last_error=row["last_error"],
    )


def _nonempty_text(value: object, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValidationError(f"{field_name} is required.")
    return text


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
