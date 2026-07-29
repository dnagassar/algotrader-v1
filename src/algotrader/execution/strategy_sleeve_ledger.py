"""Durable strategy-owned quantity sleeves for the shared SPY paper account."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import json
import sqlite3

from algotrader.core.time import require_utc_datetime
from algotrader.errors import ValidationError
from algotrader.orchestration.strategy_router import (
    SMA_TRAINING_WHEEL_STRATEGY_ID,
    SPY_RSI_MEAN_REVERSION_PAPER_STRATEGY_ID,
)


STRATEGY_SLEEVE_SCHEMA_VERSION = 1
STRATEGY_SLEEVE_SYMBOL = "SPY"
STRATEGY_SLEEVE_IDS = (
    SMA_TRAINING_WHEEL_STRATEGY_ID,
    SPY_RSI_MEAN_REVERSION_PAPER_STRATEGY_ID,
)
_TERMINAL_ORDER_STATUSES = frozenset(
    {"filled", "rejected", "canceled", "cancelled", "expired"}
)
_OPEN_INTENT_STATE = "reserved"
_EPOCH = "1970-01-01T00:00:00+00:00"


@dataclass(frozen=True, slots=True)
class StrategySleeveSnapshot:
    """Immutable aggregate and active-sleeve quantity view."""

    generation: int
    active_strategy_id: str
    active_quantity: Decimal
    total_quantity: Decimal
    pending_intent_count: int
    sleeves: tuple[tuple[str, Decimal], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "generation": self.generation,
            "active_strategy_id": self.active_strategy_id,
            "active_quantity": str(self.active_quantity),
            "total_quantity": str(self.total_quantity),
            "pending_intent_count": self.pending_intent_count,
            "sleeves": [
                {"strategy_id": strategy_id, "quantity": str(quantity)}
                for strategy_id, quantity in self.sleeves
            ],
        }


@dataclass(frozen=True, slots=True)
class StrategySleeveIntent:
    """One durable strategy-to-order ownership reservation."""

    client_order_id: str
    strategy_id: str
    symbol: str
    side: str
    requested_quantity: Decimal | None
    requested_notional: Decimal | None
    quantity_before: Decimal
    state: str
    filled_quantity: Decimal
    terminal_status: str
    session_key: str
    created_at: datetime
    updated_at: datetime

    @property
    def pending(self) -> bool:
        return self.state == _OPEN_INTENT_STATE

    def to_dict(self) -> dict[str, object]:
        return {
            "client_order_id": self.client_order_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "side": self.side,
            "requested_quantity": _decimal_text(self.requested_quantity),
            "requested_notional": _decimal_text(self.requested_notional),
            "quantity_before": str(self.quantity_before),
            "state": self.state,
            "filled_quantity": str(self.filled_quantity),
            "terminal_status": self.terminal_status,
            "session_key": self.session_key,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class SqliteStrategySleeveLedger:
    """Transactional sleeve ledger independent of broker credentials and SDKs."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS sleeve_metadata "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            existing = connection.execute(
                "SELECT value FROM sleeve_metadata WHERE key = 'schema_version'"
            ).fetchone()
            if existing is None:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    self._create_schema(connection)
                    connection.executemany(
                        "INSERT INTO strategy_sleeves("
                        "strategy_id, symbol, quantity, updated_at"
                        ") VALUES(?, ?, '0', ?)",
                        (
                            (strategy_id, STRATEGY_SLEEVE_SYMBOL, _EPOCH)
                            for strategy_id in STRATEGY_SLEEVE_IDS
                        ),
                    )
                    connection.execute(
                        "INSERT INTO sleeve_metadata(key, value) "
                        "VALUES('schema_version', ?)",
                        (str(STRATEGY_SLEEVE_SCHEMA_VERSION),),
                    )
                    connection.execute(
                        "INSERT INTO sleeve_metadata(key, value) "
                        "VALUES('generation', '0')"
                    )
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
                return
            if str(existing["value"]) != str(STRATEGY_SLEEVE_SCHEMA_VERSION):
                raise ValidationError("strategy sleeve schema version is unsupported.")
            self._require_schema(connection)

    def snapshot(self, active_strategy_id: str) -> StrategySleeveSnapshot:
        strategy_id = _strategy_id(active_strategy_id)
        self.initialize()
        with self._connect() as connection:
            return self._snapshot(connection, strategy_id)

    def adopt_existing_position(
        self,
        *,
        strategy_id: str,
        broker_quantity: Decimal | str,
        occurred_at: datetime,
    ) -> StrategySleeveSnapshot:
        checked_strategy_id = _strategy_id(strategy_id)
        quantity = _positive_decimal(broker_quantity, "broker_quantity")
        timestamp = _utc_datetime(occurred_at)
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                snapshot = self._snapshot(connection, checked_strategy_id)
                if snapshot.generation != 0 or snapshot.total_quantity != 0:
                    raise ValidationError(
                        "strategy sleeve adoption requires a pristine zero ledger."
                    )
                if snapshot.pending_intent_count:
                    raise ValidationError(
                        "strategy sleeve adoption requires no pending intents."
                    )
                connection.execute(
                    "UPDATE strategy_sleeves SET quantity = ?, updated_at = ? "
                    "WHERE strategy_id = ?",
                    (str(quantity), timestamp.isoformat(), checked_strategy_id),
                )
                generation = self._increment_generation(connection)
                self._append_event(
                    connection,
                    event_type="existing_position_adopted",
                    strategy_id=checked_strategy_id,
                    quantity_delta=quantity,
                    generation=generation,
                    occurred_at=timestamp,
                    details={"paper_only": True, "explicit_adoption": True},
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return self.snapshot(checked_strategy_id)

    def reserve_intent(
        self,
        *,
        client_order_id: str,
        strategy_id: str,
        side: str,
        requested_quantity: Decimal | str | None,
        requested_notional: Decimal | str | None,
        expected_quantity_before: Decimal | str,
        occurred_at: datetime,
        max_orders_per_session: int,
    ) -> StrategySleeveIntent:
        checked_client_order_id = _nonempty(client_order_id, "client_order_id")
        checked_strategy_id = _strategy_id(strategy_id)
        checked_side = _side(side)
        quantity = _optional_positive_decimal(
            requested_quantity,
            "requested_quantity",
        )
        notional = _optional_positive_decimal(
            requested_notional,
            "requested_notional",
        )
        if (quantity is None) == (notional is None):
            raise ValidationError(
                "exactly one of requested_quantity or requested_notional is required."
            )
        quantity_before = _non_negative_decimal(
            expected_quantity_before,
            "expected_quantity_before",
        )
        timestamp = _utc_datetime(occurred_at)
        if type(max_orders_per_session) is not int or max_orders_per_session <= 0:
            raise ValidationError("max_orders_per_session must be a positive integer.")
        session_key = timestamp.date().isoformat()
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = self._select_intent(
                    connection,
                    checked_client_order_id,
                )
                if existing is not None:
                    if not _same_intent(
                        existing,
                        strategy_id=checked_strategy_id,
                        side=checked_side,
                        requested_quantity=quantity,
                        requested_notional=notional,
                    ):
                        raise ValidationError(
                            "strategy sleeve client order identity conflicts."
                        )
                    connection.commit()
                    return existing
                if connection.execute(
                    "SELECT COUNT(*) AS count FROM strategy_sleeve_intents "
                    "WHERE state = ?",
                    (_OPEN_INTENT_STATE,),
                ).fetchone()["count"]:
                    raise ValidationError(
                        "strategy sleeve pending intent must reconcile first."
                    )
                session_count = int(
                    connection.execute(
                        "SELECT COUNT(*) AS count FROM strategy_sleeve_intents "
                        "WHERE session_key = ?",
                        (session_key,),
                    ).fetchone()["count"]
                )
                if session_count >= max_orders_per_session:
                    raise ValidationError(
                        "strategy sleeve session order cap exceeded."
                    )
                sleeve = self._select_sleeve(connection, checked_strategy_id)
                if sleeve != quantity_before:
                    raise ValidationError(
                        "strategy sleeve quantity changed before reservation."
                    )
                if checked_side == "sell" and (
                    quantity is None or quantity > quantity_before
                ):
                    raise ValidationError(
                        "strategy sleeve sell exceeds owned quantity."
                    )
                connection.execute(
                    """
                    INSERT INTO strategy_sleeve_intents(
                        client_order_id, strategy_id, symbol, side,
                        requested_quantity, requested_notional, quantity_before,
                        state, filled_quantity, terminal_status, session_key,
                        created_at, updated_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, '0', '', ?, ?, ?)
                    """,
                    (
                        checked_client_order_id,
                        checked_strategy_id,
                        STRATEGY_SLEEVE_SYMBOL,
                        checked_side,
                        _decimal_text(quantity) or None,
                        _decimal_text(notional) or None,
                        str(quantity_before),
                        _OPEN_INTENT_STATE,
                        session_key,
                        timestamp.isoformat(),
                        timestamp.isoformat(),
                    ),
                )
                self._append_event(
                    connection,
                    event_type="intent_reserved",
                    strategy_id=checked_strategy_id,
                    quantity_delta=Decimal("0"),
                    generation=self._generation(connection),
                    occurred_at=timestamp,
                    details={
                        "client_order_id": checked_client_order_id,
                        "side": checked_side,
                    },
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        intent = self.get_intent(checked_client_order_id)
        if intent is None:
            raise ValidationError("strategy sleeve intent reservation was not stored.")
        return intent

    def reconcile_intent(
        self,
        client_order_id: str,
        *,
        terminal_status: str,
        filled_quantity: Decimal | str | None,
        occurred_at: datetime,
    ) -> StrategySleeveIntent:
        checked_client_order_id = _nonempty(client_order_id, "client_order_id")
        status = _nonempty(terminal_status, "terminal_status").lower()
        if status not in _TERMINAL_ORDER_STATUSES:
            raise ValidationError(
                "strategy sleeve reconciliation requires a terminal order."
            )
        filled = _optional_non_negative_decimal(
            filled_quantity,
            "filled_quantity",
        ) or Decimal("0")
        if status == "filled" and filled <= 0:
            raise ValidationError(
                "filled strategy sleeve reconciliation requires positive quantity."
            )
        timestamp = _utc_datetime(occurred_at)
        self.initialize()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                intent = self._select_intent(
                    connection,
                    checked_client_order_id,
                )
                if intent is None:
                    raise ValidationError("strategy sleeve intent is missing.")
                if not intent.pending:
                    if (
                        intent.terminal_status != status
                        or intent.filled_quantity != filled
                    ):
                        raise ValidationError(
                            "strategy sleeve reconciliation conflicts with stored result."
                        )
                    connection.commit()
                    return intent
                current_quantity = self._select_sleeve(
                    connection,
                    intent.strategy_id,
                )
                if current_quantity != intent.quantity_before:
                    raise ValidationError(
                        "strategy sleeve quantity changed before reconciliation."
                    )
                if intent.side == "buy":
                    updated_quantity = current_quantity + filled
                else:
                    if filled > current_quantity:
                        raise ValidationError(
                            "strategy sleeve fill exceeds owned quantity."
                        )
                    updated_quantity = current_quantity - filled
                generation = self._generation(connection)
                if filled > 0:
                    connection.execute(
                        "UPDATE strategy_sleeves SET quantity = ?, updated_at = ? "
                        "WHERE strategy_id = ?",
                        (
                            str(updated_quantity),
                            timestamp.isoformat(),
                            intent.strategy_id,
                        ),
                    )
                    generation = self._increment_generation(connection)
                state = "applied" if filled > 0 else "terminal_no_fill"
                connection.execute(
                    "UPDATE strategy_sleeve_intents "
                    "SET state = ?, filled_quantity = ?, terminal_status = ?, "
                    "updated_at = ? WHERE client_order_id = ?",
                    (
                        state,
                        str(filled),
                        status,
                        timestamp.isoformat(),
                        checked_client_order_id,
                    ),
                )
                self._append_event(
                    connection,
                    event_type="intent_reconciled",
                    strategy_id=intent.strategy_id,
                    quantity_delta=(
                        filled if intent.side == "buy" else -filled
                    ),
                    generation=generation,
                    occurred_at=timestamp,
                    details={
                        "client_order_id": checked_client_order_id,
                        "terminal_status": status,
                    },
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        reconciled = self.get_intent(checked_client_order_id)
        if reconciled is None:
            raise ValidationError("strategy sleeve reconciliation was not stored.")
        return reconciled

    def get_intent(self, client_order_id: str) -> StrategySleeveIntent | None:
        checked = _nonempty(client_order_id, "client_order_id")
        self.initialize()
        with self._connect() as connection:
            return self._select_intent(connection, checked)

    def pending_intents(self) -> tuple[StrategySleeveIntent, ...]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM strategy_sleeve_intents WHERE state = ? "
                "ORDER BY created_at, client_order_id",
                (_OPEN_INTENT_STATE,),
            ).fetchall()
        return tuple(_intent_from_row(row) for row in rows)

    def session_intent_count(self, occurred_at: datetime) -> int:
        """Return durable sleeve intents recorded for the UTC session date."""

        session_key = _utc_datetime(occurred_at).date().isoformat()
        self.initialize()
        with self._connect() as connection:
            return int(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM strategy_sleeve_intents "
                    "WHERE session_key = ?",
                    (session_key,),
                ).fetchone()["count"]
            )

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE strategy_sleeves(
                strategy_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                quantity TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE strategy_sleeve_intents(
                client_order_id TEXT PRIMARY KEY,
                strategy_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                requested_quantity TEXT,
                requested_notional TEXT,
                quantity_before TEXT NOT NULL,
                state TEXT NOT NULL,
                filled_quantity TEXT NOT NULL,
                terminal_status TEXT NOT NULL,
                session_key TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(strategy_id) REFERENCES strategy_sleeves(strategy_id)
            )
            """
        )
        connection.execute(
            "CREATE INDEX strategy_sleeve_intents_session_idx "
            "ON strategy_sleeve_intents(session_key, client_order_id)"
        )
        connection.execute(
            """
            CREATE TABLE strategy_sleeve_events(
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                strategy_id TEXT NOT NULL,
                quantity_delta TEXT NOT NULL,
                generation INTEGER NOT NULL,
                occurred_at TEXT NOT NULL,
                details_json TEXT NOT NULL
            )
            """
        )

    @staticmethod
    def _require_schema(connection: sqlite3.Connection) -> None:
        required = {
            "strategy_sleeves",
            "strategy_sleeve_intents",
            "strategy_sleeve_events",
        }
        existing = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        if not required <= existing:
            raise ValidationError("strategy sleeve schema is corrupt.")
        if connection.execute(
            "SELECT COUNT(*) AS count FROM strategy_sleeves"
        ).fetchone()["count"] != len(STRATEGY_SLEEVE_IDS):
            raise ValidationError("strategy sleeve registry is corrupt.")

    def _snapshot(
        self,
        connection: sqlite3.Connection,
        active_strategy_id: str,
    ) -> StrategySleeveSnapshot:
        rows = connection.execute(
            "SELECT strategy_id, quantity FROM strategy_sleeves "
            "WHERE symbol = ? ORDER BY strategy_id",
            (STRATEGY_SLEEVE_SYMBOL,),
        ).fetchall()
        sleeves = tuple(
            (
                str(row["strategy_id"]),
                _non_negative_decimal(row["quantity"], "stored_quantity"),
            )
            for row in rows
        )
        quantities = dict(sleeves)
        if active_strategy_id not in quantities:
            raise ValidationError("active strategy sleeve is missing.")
        pending_count = int(
            connection.execute(
                "SELECT COUNT(*) AS count FROM strategy_sleeve_intents "
                "WHERE state = ?",
                (_OPEN_INTENT_STATE,),
            ).fetchone()["count"]
        )
        return StrategySleeveSnapshot(
            generation=self._generation(connection),
            active_strategy_id=active_strategy_id,
            active_quantity=quantities[active_strategy_id],
            total_quantity=sum(quantities.values(), Decimal("0")),
            pending_intent_count=pending_count,
            sleeves=sleeves,
        )

    @staticmethod
    def _select_sleeve(
        connection: sqlite3.Connection,
        strategy_id: str,
    ) -> Decimal:
        row = connection.execute(
            "SELECT quantity FROM strategy_sleeves WHERE strategy_id = ?",
            (strategy_id,),
        ).fetchone()
        if row is None:
            raise ValidationError("strategy sleeve is missing.")
        return _non_negative_decimal(row["quantity"], "stored_quantity")

    @staticmethod
    def _select_intent(
        connection: sqlite3.Connection,
        client_order_id: str,
    ) -> StrategySleeveIntent | None:
        row = connection.execute(
            "SELECT * FROM strategy_sleeve_intents WHERE client_order_id = ?",
            (client_order_id,),
        ).fetchone()
        return None if row is None else _intent_from_row(row)

    @staticmethod
    def _generation(connection: sqlite3.Connection) -> int:
        row = connection.execute(
            "SELECT value FROM sleeve_metadata WHERE key = 'generation'"
        ).fetchone()
        if row is None:
            raise ValidationError("strategy sleeve generation is missing.")
        try:
            value = int(row["value"])
        except (TypeError, ValueError) as exc:
            raise ValidationError("strategy sleeve generation is corrupt.") from exc
        if value < 0:
            raise ValidationError("strategy sleeve generation is corrupt.")
        return value

    @classmethod
    def _increment_generation(cls, connection: sqlite3.Connection) -> int:
        generation = cls._generation(connection) + 1
        connection.execute(
            "UPDATE sleeve_metadata SET value = ? WHERE key = 'generation'",
            (str(generation),),
        )
        return generation

    @staticmethod
    def _append_event(
        connection: sqlite3.Connection,
        *,
        event_type: str,
        strategy_id: str,
        quantity_delta: Decimal,
        generation: int,
        occurred_at: datetime,
        details: dict[str, object],
    ) -> None:
        connection.execute(
            """
            INSERT INTO strategy_sleeve_events(
                event_type, strategy_id, quantity_delta, generation,
                occurred_at, details_json
            ) VALUES(?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                strategy_id,
                str(quantity_delta),
                generation,
                occurred_at.isoformat(),
                json.dumps(details, sort_keys=True, separators=(",", ":")),
            ),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection


def _intent_from_row(row: sqlite3.Row) -> StrategySleeveIntent:
    return StrategySleeveIntent(
        client_order_id=str(row["client_order_id"]),
        strategy_id=_strategy_id(row["strategy_id"]),
        symbol=str(row["symbol"]),
        side=_side(row["side"]),
        requested_quantity=_optional_positive_decimal(
            row["requested_quantity"],
            "stored_requested_quantity",
        ),
        requested_notional=_optional_positive_decimal(
            row["requested_notional"],
            "stored_requested_notional",
        ),
        quantity_before=_non_negative_decimal(
            row["quantity_before"],
            "stored_quantity_before",
        ),
        state=str(row["state"]),
        filled_quantity=_non_negative_decimal(
            row["filled_quantity"],
            "stored_filled_quantity",
        ),
        terminal_status=str(row["terminal_status"]),
        session_key=str(row["session_key"]),
        created_at=_parse_datetime(row["created_at"], "created_at"),
        updated_at=_parse_datetime(row["updated_at"], "updated_at"),
    )


def _same_intent(
    intent: StrategySleeveIntent,
    *,
    strategy_id: str,
    side: str,
    requested_quantity: Decimal | None,
    requested_notional: Decimal | None,
) -> bool:
    return (
        intent.strategy_id == strategy_id
        and intent.side == side
        and intent.requested_quantity == requested_quantity
        and intent.requested_notional == requested_notional
    )


def _strategy_id(value: object) -> str:
    strategy_id = _nonempty(value, "strategy_id")
    if strategy_id not in STRATEGY_SLEEVE_IDS:
        raise ValidationError("strategy_id is not supported by the sleeve ledger.")
    return strategy_id


def _side(value: object) -> str:
    side = _nonempty(value, "side").lower()
    if side not in {"buy", "sell"}:
        raise ValidationError("side must be buy or sell.")
    return side


def _nonempty(value: object, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{field_name} is required.")
    return value.strip()


def _positive_decimal(value: object, field_name: str) -> Decimal:
    result = _decimal(value, field_name)
    if result <= 0:
        raise ValidationError(f"{field_name} must be positive.")
    return result


def _non_negative_decimal(value: object, field_name: str) -> Decimal:
    result = _decimal(value, field_name)
    if result < 0:
        raise ValidationError(f"{field_name} must be non-negative.")
    return result


def _optional_positive_decimal(
    value: object,
    field_name: str,
) -> Decimal | None:
    if value in (None, ""):
        return None
    return _positive_decimal(value, field_name)


def _optional_non_negative_decimal(
    value: object,
    field_name: str,
) -> Decimal | None:
    if value in (None, ""):
        return None
    return _non_negative_decimal(value, field_name)


def _decimal(value: object, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a finite decimal.")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a finite decimal.") from exc
    if not result.is_finite():
        raise ValidationError(f"{field_name} must be a finite decimal.")
    return result


def _decimal_text(value: Decimal | None) -> str:
    return "" if value is None else str(value)


def _utc_datetime(value: datetime) -> datetime:
    try:
        return require_utc_datetime(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("occurred_at must be timezone-aware UTC.") from exc


def _parse_datetime(value: object, field_name: str) -> datetime:
    try:
        return _utc_datetime(datetime.fromisoformat(str(value)))
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"stored {field_name} is corrupt.") from exc


__all__ = [
    "STRATEGY_SLEEVE_IDS",
    "STRATEGY_SLEEVE_SCHEMA_VERSION",
    "STRATEGY_SLEEVE_SYMBOL",
    "SqliteStrategySleeveLedger",
    "StrategySleeveIntent",
    "StrategySleeveSnapshot",
]
