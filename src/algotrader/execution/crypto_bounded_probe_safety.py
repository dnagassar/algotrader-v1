"""Offline durable safety kernel for a future bounded crypto paper probe.

This module has no broker client, network path, credential access, or order
construction. A positive verdict means only that the supplied action satisfies
the local frozen safety policy. It never authorizes a paper or live operation.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Callable, Mapping

from algotrader.errors import ValidationError


CRYPTO_BOUNDED_PROBE_SAFETY_SCHEMA_VERSION = (
    "v5_27_crypto_bounded_probe_safety_v1"
)
CRYPTO_BOUNDED_PROBE_SAFETY_POLICY_FINGERPRINT = (
    "c0abbc047f7bdf01f19d46e06d3824acd980016b4bd992d78dd4994db6d2c407"
)
CRYPTO_BOUNDED_PROBE_SUPPORTED_SYMBOLS = ("BTCUSD", "ETHUSD", "SOLUSD")

_STATE_SCHEMA_VERSION = "v5_27_crypto_bounded_probe_state_v1"
_VERDICT_SCHEMA_VERSION = "v5_27_crypto_bounded_probe_safety_verdict_v1"
_ACTIONS = ("entry", "cancel", "exit")
_MIN_NOTIONAL_USD = Decimal("1")
_MAX_NOTIONAL_USD = Decimal("10")
_MAX_LOSS_USD = Decimal("2")
_MARKET_DATA_MAX_AGE = timedelta(hours=2)
_BROKER_SNAPSHOT_MAX_AGE = timedelta(minutes=5)
_MAX_DURATION = timedelta(hours=168)
_ZERO = Decimal("0")
_DECIMAL_QUANTUM = Decimal("0.00000001")
_FALSE_AUTHORITY = {
    "broker_read_authorized": False,
    "broker_mutation_authorized": False,
    "paper_submit_authorized": False,
    "paper_cancel_authorized": False,
    "paper_exit_authorized": False,
    "paper_mutation_authorized": False,
    "capital_allocation_authorized": False,
    "live_authorized": False,
}

__all__ = [
    "CRYPTO_BOUNDED_PROBE_SAFETY_POLICY_FINGERPRINT",
    "CRYPTO_BOUNDED_PROBE_SAFETY_SCHEMA_VERSION",
    "CRYPTO_BOUNDED_PROBE_SUPPORTED_SYMBOLS",
    "CryptoBoundedProbeObservation",
    "CryptoBoundedProbeSafetyState",
    "CryptoBoundedProbeSafetyStore",
    "build_crypto_bounded_probe_safety_policy",
    "evaluate_crypto_bounded_probe_safety",
]


def build_crypto_bounded_probe_safety_policy() -> dict[str, object]:
    """Return the immutable candidate-deferred V5.27 safety contract."""

    manifest: dict[str, object] = {
        "schema_version": CRYPTO_BOUNDED_PROBE_SAFETY_SCHEMA_VERSION,
        "record_type": "crypto_bounded_probe_safety_policy",
        "supported_symbols": list(CRYPTO_BOUNDED_PROBE_SUPPORTED_SYMBOLS),
        "environment": "alpaca_crypto_paper",
        "direction": "long_or_cash",
        "maximum_notional_usd": "10",
        "minimum_notional_usd": "1",
        "maximum_principal_at_risk_usd": "10",
        "loss_halt_usd": "2",
        "maximum_concurrent_positions": 1,
        "maximum_open_orders": 1,
        "maximum_entry_attempts": 1,
        "maximum_exit_attempts": 1,
        "maximum_cancel_attempts_per_order": 1,
        "maximum_replacements": 0,
        "time_in_force": "gtc",
        "maximum_duration_hours": 168,
        "market_data_max_age_minutes": 120,
        "broker_snapshot_max_age_minutes": 5,
        "default_paused": True,
        "loss_halt_restart_latched": True,
        "maximum_observed_loss_restart_persistent": True,
        "action_attempt_budgets_restart_persistent": True,
        "safety_evaluation_and_attempt_claim_atomic": True,
        "automatic_loss_halt_reset_allowed": False,
        "stop_execution_guarantees_realized_loss_cap": False,
        "risk_reducing_actions_allowed_while_entry_halted": [
            "cancel",
            "exit",
        ],
        "entry_fail_closed_conditions": [
            "operator_control_paused",
            "loss_context_missing",
            "loss_halt_latched",
            "loss_limit_reached",
            "market_data_stale_or_future",
            "broker_snapshot_stale_or_future",
            "capability_expired",
            "unexpected_position_or_order_state",
            "broker_ambiguity",
            "cross_symbol_exposure",
            "probe_duration_expired",
        ],
        "leverage_allowed": False,
        "margin_allowed": False,
        "shorting_allowed": False,
        "pyramiding_allowed": False,
        "cross_symbol_exposure_allowed": False,
        "network_access_authorized": False,
        "broker_read_authorized": False,
        "broker_mutation_authorized": False,
        "paper_mutation_authorized": False,
        "capital_allocation_authorized": False,
        "live_authorized": False,
        "profit_claim": "none",
    }
    fingerprint = _stable_hash(manifest)
    if (
        CRYPTO_BOUNDED_PROBE_SAFETY_POLICY_FINGERPRINT
        and fingerprint != CRYPTO_BOUNDED_PROBE_SAFETY_POLICY_FINGERPRINT
    ):
        raise RuntimeError(
            "crypto bounded-probe safety policy drift detected: "
            f"{fingerprint}"
        )
    manifest["policy_fingerprint"] = fingerprint
    return manifest


@dataclass(frozen=True)
class CryptoBoundedProbeSafetyState:
    """One durable, selected-symbol safety state snapshot."""

    schema_version: str
    policy_fingerprint: str
    selected_symbol: str
    entry_enabled: bool
    operator_control_fingerprint: str
    loss_halt_latched: bool
    cumulative_net_pnl_usd: Decimal
    maximum_observed_loss_usd: Decimal
    loss_basis_fingerprint: str
    probe_started_at: datetime | None
    probe_episode_fingerprint: str
    entry_attempt_count: int
    exit_attempt_count: int
    cancel_attempt_count: int
    last_action_fingerprint: str
    updated_at: datetime
    revision: int
    state_fingerprint: str

    def identity(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "policy_fingerprint": self.policy_fingerprint,
            "selected_symbol": self.selected_symbol,
            "entry_enabled": self.entry_enabled,
            "operator_control_fingerprint": self.operator_control_fingerprint,
            "loss_halt_latched": self.loss_halt_latched,
            "cumulative_net_pnl_usd": _decimal_text(
                self.cumulative_net_pnl_usd
            ),
            "maximum_observed_loss_usd": _decimal_text(
                self.maximum_observed_loss_usd
            ),
            "loss_basis_fingerprint": self.loss_basis_fingerprint,
            "probe_started_at": (
                ""
                if self.probe_started_at is None
                else self.probe_started_at.isoformat()
            ),
            "probe_episode_fingerprint": self.probe_episode_fingerprint,
            "entry_attempt_count": self.entry_attempt_count,
            "exit_attempt_count": self.exit_attempt_count,
            "cancel_attempt_count": self.cancel_attempt_count,
            "last_action_fingerprint": self.last_action_fingerprint,
            "updated_at": self.updated_at.isoformat(),
            "revision": self.revision,
        }

    def canonical(self) -> dict[str, object]:
        return {**self.identity(), "state_fingerprint": self.state_fingerprint}


@dataclass(frozen=True)
class CryptoBoundedProbeObservation:
    """Exact local facts supplied to one safety evaluation."""

    symbol: str
    action: str
    as_of: datetime
    broker_snapshot_as_of: datetime
    capability_valid_until: datetime
    market_data_as_of: datetime | None = None
    requested_notional_usd: Decimal = _ZERO
    requested_exit_quantity: Decimal = _ZERO
    principal_at_risk_usd: Decimal = _ZERO
    available_cash_usd: Decimal = _ZERO
    position_quantity: Decimal = _ZERO
    position_count: int = 0
    open_order_count: int = 0
    entry_attempt_count: int = 0
    exit_attempt_count: int = 0
    cancel_attempt_count: int = 0
    replacement_attempt_count: int = 0
    loss_context_complete: bool = False
    cumulative_net_pnl_usd: Decimal = _ZERO
    observed_order_fingerprint: str = ""
    cancel_target_fingerprint: str = ""
    account_trading_blocked: bool = False
    margin_used: bool = False
    broker_ambiguity: bool = False
    unexpected_symbol_exposure: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _symbol(self.symbol))
        action = str(self.action).strip().lower()
        if action not in _ACTIONS:
            raise ValidationError("unsupported bounded-probe safety action.")
        object.__setattr__(self, "action", action)
        for field_name in (
            "as_of",
            "broker_snapshot_as_of",
            "capability_valid_until",
        ):
            object.__setattr__(
                self,
                field_name,
                _utc_datetime(getattr(self, field_name), field_name),
            )
        if self.market_data_as_of is not None:
            object.__setattr__(
                self,
                "market_data_as_of",
                _utc_datetime(self.market_data_as_of, "market_data_as_of"),
            )
        for field_name in (
            "requested_notional_usd",
            "requested_exit_quantity",
            "principal_at_risk_usd",
            "available_cash_usd",
            "position_quantity",
            "cumulative_net_pnl_usd",
        ):
            object.__setattr__(
                self,
                field_name,
                _decimal(getattr(self, field_name), field_name),
            )
        for field_name in (
            "position_count",
            "open_order_count",
            "entry_attempt_count",
            "exit_attempt_count",
            "cancel_attempt_count",
            "replacement_attempt_count",
        ):
            value = getattr(self, field_name)
            if type(value) is not int or value < 0:
                raise ValidationError(f"{field_name} must be a non-negative int.")
        for field_name in (
            "loss_context_complete",
            "account_trading_blocked",
            "margin_used",
            "broker_ambiguity",
            "unexpected_symbol_exposure",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")
        if self.requested_notional_usd < _ZERO:
            raise ValidationError("requested_notional_usd cannot be negative.")
        if self.requested_exit_quantity < _ZERO:
            raise ValidationError("requested_exit_quantity cannot be negative.")
        if self.principal_at_risk_usd < _ZERO:
            raise ValidationError("principal_at_risk_usd cannot be negative.")
        if self.available_cash_usd < _ZERO:
            raise ValidationError("available_cash_usd cannot be negative.")
        for field_name in (
            "observed_order_fingerprint",
            "cancel_target_fingerprint",
        ):
            value = str(getattr(self, field_name)).strip().lower()
            if value:
                value = _sha256(value, field_name)
            object.__setattr__(self, field_name, value)


class CryptoBoundedProbeSafetyStore:
    """Small durable state store with default pause and irreversible loss latch."""

    def __init__(self, path: Path | str) -> None:
        self.path = _local_path(path)

    def initialize(
        self,
        *,
        selected_symbol: str,
        as_of: datetime | str,
    ) -> CryptoBoundedProbeSafetyState:
        symbol = _symbol(selected_symbol)
        observed_at = _utc_datetime(as_of, "as_of")
        with closing(self._connect()) as connection:
            self._create_schema(connection)
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = self._read_row(connection)
                if row is None:
                    state = _state_from_identity(
                        {
                            "schema_version": _STATE_SCHEMA_VERSION,
                            "policy_fingerprint": (
                                CRYPTO_BOUNDED_PROBE_SAFETY_POLICY_FINGERPRINT
                            ),
                            "selected_symbol": symbol,
                            "entry_enabled": False,
                            "operator_control_fingerprint": "",
                            "loss_halt_latched": False,
                            "cumulative_net_pnl_usd": "0",
                            "maximum_observed_loss_usd": "0",
                            "loss_basis_fingerprint": "",
                            "probe_started_at": "",
                            "probe_episode_fingerprint": "",
                            "entry_attempt_count": 0,
                            "exit_attempt_count": 0,
                            "cancel_attempt_count": 0,
                            "last_action_fingerprint": "",
                            "updated_at": observed_at.isoformat(),
                            "revision": 0,
                        }
                    )
                    self._insert(connection, state)
                else:
                    state = _state_from_row(row)
                    if state.selected_symbol != symbol:
                        raise ValidationError(
                            "bounded-probe state selected symbol mismatch."
                        )
                connection.commit()
                return state
            except Exception:
                connection.rollback()
                raise

    def load(self) -> CryptoBoundedProbeSafetyState:
        try:
            with closing(self._connect(create_parent=False)) as connection:
                row = self._read_row(connection)
                if row is None:
                    raise ValidationError("bounded-probe safety state is absent.")
                return _state_from_row(row)
        except sqlite3.Error as exc:
            raise ValidationError("bounded-probe safety state is unreadable.") from exc

    def record_operator_control(
        self,
        *,
        entry_enabled: bool,
        authorization_fingerprint: str,
        as_of: datetime | str,
    ) -> CryptoBoundedProbeSafetyState:
        if type(entry_enabled) is not bool:
            raise ValidationError("entry_enabled must be a boolean.")
        control_fingerprint = _sha256(
            authorization_fingerprint,
            "authorization_fingerprint",
        )
        observed_at = _utc_datetime(as_of, "as_of")

        def mutate(state: CryptoBoundedProbeSafetyState) -> dict[str, object]:
            if entry_enabled and state.loss_halt_latched:
                raise ValidationError("loss-halted state cannot enable entry.")
            started_at = state.probe_started_at
            episode_fingerprint = state.probe_episode_fingerprint
            if entry_enabled and started_at is None:
                started_at = observed_at
                episode_fingerprint = _stable_hash(
                    {
                        "policy_fingerprint": (
                            CRYPTO_BOUNDED_PROBE_SAFETY_POLICY_FINGERPRINT
                        ),
                        "selected_symbol": state.selected_symbol,
                        "authorization_fingerprint": control_fingerprint,
                        "probe_started_at": observed_at.isoformat(),
                    }
                )
            return {
                **state.identity(),
                "entry_enabled": entry_enabled,
                "operator_control_fingerprint": control_fingerprint,
                "probe_started_at": (
                    "" if started_at is None else started_at.isoformat()
                ),
                "probe_episode_fingerprint": episode_fingerprint,
                "updated_at": observed_at.isoformat(),
                "revision": state.revision + 1,
            }

        return self._update(observed_at, mutate)

    def record_loss_observation(
        self,
        *,
        cumulative_net_pnl_usd: Decimal | str,
        loss_basis_fingerprint: str,
        as_of: datetime | str,
    ) -> CryptoBoundedProbeSafetyState:
        pnl = _decimal(cumulative_net_pnl_usd, "cumulative_net_pnl_usd")
        basis_fingerprint = _sha256(
            loss_basis_fingerprint,
            "loss_basis_fingerprint",
        )
        observed_at = _utc_datetime(as_of, "as_of")

        def mutate(state: CryptoBoundedProbeSafetyState) -> dict[str, object]:
            observed_loss = max(_ZERO, -pnl)
            maximum_observed_loss = max(
                state.maximum_observed_loss_usd,
                observed_loss,
            )
            latched = (
                state.loss_halt_latched
                or maximum_observed_loss >= _MAX_LOSS_USD
            )
            return {
                **state.identity(),
                "entry_enabled": False if latched else state.entry_enabled,
                "loss_halt_latched": latched,
                "cumulative_net_pnl_usd": _decimal_text(pnl),
                "maximum_observed_loss_usd": _decimal_text(
                    maximum_observed_loss
                ),
                "loss_basis_fingerprint": basis_fingerprint,
                "updated_at": observed_at.isoformat(),
                "revision": state.revision + 1,
            }

        return self._update(observed_at, mutate)

    def evaluate_and_claim(
        self,
        observation: CryptoBoundedProbeObservation,
        *,
        claim_fingerprint: str,
    ) -> dict[str, object]:
        """Atomically evaluate and consume one local action-attempt budget.

        This records only a local safety claim. It never constructs an order,
        calls a broker, or grants paper/live authority.
        """

        claim_identity = _sha256(claim_fingerprint, "claim_fingerprint")
        try:
            with closing(self._connect(create_parent=False)) as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = self._read_row(connection)
                if row is None:
                    raise ValidationError("bounded-probe safety state is absent.")
                state = _state_from_row(row)
                if observation.as_of < state.updated_at:
                    raise ValidationError(
                        "bounded-probe safety state time cannot regress."
                    )
                verdict = evaluate_crypto_bounded_probe_safety(
                    state,
                    observation,
                )
                if not verdict["local_safety_admitted"]:
                    connection.commit()
                    return {
                        "state": state.canonical(),
                        "verdict": verdict,
                    }

                counter_name = f"{observation.action}_attempt_count"
                updated = _state_from_identity(
                    {
                        **state.identity(),
                        counter_name: getattr(state, counter_name) + 1,
                        "last_action_fingerprint": claim_identity,
                        "updated_at": observation.as_of.isoformat(),
                        "revision": state.revision + 1,
                    }
                )
                self._persist_update(connection, state.revision, updated)
                connection.commit()
                claimed_verdict = {
                    **verdict,
                    "claim_recorded": True,
                    "action_claim_fingerprint": claim_identity,
                    "claimed_state_fingerprint": updated.state_fingerprint,
                }
                claimed_verdict["verdict_fingerprint"] = _stable_hash(
                    {
                        key: value
                        for key, value in claimed_verdict.items()
                        if key != "verdict_fingerprint"
                    }
                )
                return {
                    "state": updated.canonical(),
                    "verdict": claimed_verdict,
                }
        except sqlite3.Error as exc:
            raise ValidationError(
                "bounded-probe safety action claim failed."
            ) from exc

    def _update(
        self,
        observed_at: datetime,
        mutate: Callable[
            [CryptoBoundedProbeSafetyState],
            dict[str, object],
        ],
    ) -> CryptoBoundedProbeSafetyState:
        try:
            with closing(self._connect(create_parent=False)) as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = self._read_row(connection)
                if row is None:
                    raise ValidationError("bounded-probe safety state is absent.")
                state = _state_from_row(row)
                if observed_at < state.updated_at:
                    raise ValidationError(
                        "bounded-probe safety state time cannot regress."
                    )
                identity = mutate(state)
                updated = _state_from_identity(identity)
                self._persist_update(connection, state.revision, updated)
                connection.commit()
                return updated
        except sqlite3.Error as exc:
            raise ValidationError("bounded-probe safety state update failed.") from exc

    @staticmethod
    def _persist_update(
        connection: sqlite3.Connection,
        previous_revision: int,
        updated: CryptoBoundedProbeSafetyState,
    ) -> None:
        changed = connection.execute(
            """
            UPDATE bounded_probe_state
            SET schema_version = ?, policy_fingerprint = ?,
                selected_symbol = ?, entry_enabled = ?,
                operator_control_fingerprint = ?, loss_halt_latched = ?,
                cumulative_net_pnl_usd = ?, maximum_observed_loss_usd = ?,
                loss_basis_fingerprint = ?, probe_started_at = ?,
                probe_episode_fingerprint = ?, entry_attempt_count = ?,
                exit_attempt_count = ?, cancel_attempt_count = ?,
                last_action_fingerprint = ?, updated_at = ?, revision = ?,
                state_fingerprint = ?
            WHERE singleton = 1 AND revision = ?
            """,
            _state_sql_values(updated) + (previous_revision,),
        ).rowcount
        if changed != 1:
            raise ValidationError(
                "bounded-probe safety state concurrent update detected."
            )

    def _connect(self, *, create_parent: bool = True) -> sqlite3.Connection:
        if create_parent:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        elif not self.path.is_file():
            raise ValidationError("bounded-probe safety state is absent.")
        connection = sqlite3.connect(
            self.path,
            timeout=5,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS bounded_probe_state (
                singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                schema_version TEXT NOT NULL,
                policy_fingerprint TEXT NOT NULL,
                selected_symbol TEXT NOT NULL,
                entry_enabled INTEGER NOT NULL CHECK (entry_enabled IN (0, 1)),
                operator_control_fingerprint TEXT NOT NULL,
                loss_halt_latched INTEGER NOT NULL
                    CHECK (loss_halt_latched IN (0, 1)),
                cumulative_net_pnl_usd TEXT NOT NULL,
                maximum_observed_loss_usd TEXT NOT NULL,
                loss_basis_fingerprint TEXT NOT NULL,
                probe_started_at TEXT NOT NULL,
                probe_episode_fingerprint TEXT NOT NULL,
                entry_attempt_count INTEGER NOT NULL
                    CHECK (entry_attempt_count BETWEEN 0 AND 1),
                exit_attempt_count INTEGER NOT NULL
                    CHECK (exit_attempt_count BETWEEN 0 AND 1),
                cancel_attempt_count INTEGER NOT NULL
                    CHECK (cancel_attempt_count BETWEEN 0 AND 1),
                last_action_fingerprint TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                revision INTEGER NOT NULL CHECK (revision >= 0),
                state_fingerprint TEXT NOT NULL
            )
            """
        )

    @staticmethod
    def _read_row(connection: sqlite3.Connection) -> sqlite3.Row | None:
        return connection.execute(
            "SELECT * FROM bounded_probe_state WHERE singleton = 1"
        ).fetchone()

    @staticmethod
    def _insert(
        connection: sqlite3.Connection,
        state: CryptoBoundedProbeSafetyState,
    ) -> None:
        connection.execute(
            """
            INSERT INTO bounded_probe_state (
                singleton, schema_version, policy_fingerprint, selected_symbol,
                entry_enabled, operator_control_fingerprint,
                loss_halt_latched, cumulative_net_pnl_usd,
                maximum_observed_loss_usd, loss_basis_fingerprint,
                probe_started_at, probe_episode_fingerprint,
                entry_attempt_count, exit_attempt_count,
                cancel_attempt_count, last_action_fingerprint,
                updated_at, revision, state_fingerprint
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _state_sql_values(state),
        )


def evaluate_crypto_bounded_probe_safety(
    state: CryptoBoundedProbeSafetyState,
    observation: CryptoBoundedProbeObservation,
) -> dict[str, object]:
    """Evaluate one action under the local policy without granting authority."""

    _validate_state(state)
    blockers: list[str] = []
    if observation.symbol != state.selected_symbol:
        blockers.append("selected_symbol_mismatch")
    if observation.as_of < state.updated_at:
        blockers.append("state_observation_time_regression")
    if observation.broker_snapshot_as_of > observation.as_of:
        blockers.append("broker_snapshot_from_future")
    elif (
        observation.as_of - observation.broker_snapshot_as_of
        > _BROKER_SNAPSHOT_MAX_AGE
    ):
        blockers.append("broker_snapshot_stale")
    if observation.broker_ambiguity:
        blockers.append("broker_ambiguity")
    if observation.unexpected_symbol_exposure:
        blockers.append("cross_symbol_exposure")
    if observation.replacement_attempt_count != 0:
        blockers.append("replacement_not_allowed")
    if not observation.loss_context_complete:
        blockers.append("loss_context_missing")
    elif observation.cumulative_net_pnl_usd != state.cumulative_net_pnl_usd:
        blockers.append("loss_state_mismatch")
    if observation.position_count > 1 or observation.open_order_count > 1:
        blockers.append("unexpected_position_or_order_state")
    if (
        (observation.position_count == 0 and observation.position_quantity != _ZERO)
        or (
            observation.position_count == 1
            and observation.position_quantity <= _ZERO
        )
    ):
        blockers.append("unexpected_position_quantity")
    if (
        observation.open_order_count == 0
        and observation.observed_order_fingerprint
    ) or (
        observation.open_order_count == 1
        and not observation.observed_order_fingerprint
    ):
        blockers.append("unexpected_order_identity")
    if (
        observation.entry_attempt_count,
        observation.exit_attempt_count,
        observation.cancel_attempt_count,
    ) != (
        state.entry_attempt_count,
        state.exit_attempt_count,
        state.cancel_attempt_count,
    ):
        blockers.append("attempt_state_mismatch")

    if observation.action == "entry":
        if observation.account_trading_blocked:
            blockers.append("account_trading_blocked")
        if observation.margin_used:
            blockers.append("margin_not_allowed")
        if not state.entry_enabled:
            blockers.append("operator_control_paused")
        if state.loss_halt_latched:
            blockers.append("loss_halt_latched")
        if observation.cumulative_net_pnl_usd <= -_MAX_LOSS_USD:
            blockers.append("loss_limit_reached")
        if observation.capability_valid_until < observation.as_of:
            blockers.append("capability_expired")
        if observation.market_data_as_of is None:
            blockers.append("market_data_missing")
        elif observation.market_data_as_of > observation.as_of:
            blockers.append("market_data_from_future")
        elif observation.as_of - observation.market_data_as_of > _MARKET_DATA_MAX_AGE:
            blockers.append("market_data_stale")
        if state.probe_started_at is None:
            blockers.append("probe_start_missing")
        elif observation.as_of < state.probe_started_at:
            blockers.append("probe_time_regression")
        elif observation.as_of - state.probe_started_at > _MAX_DURATION:
            blockers.append("probe_duration_expired")
        if observation.position_count != 0 or observation.open_order_count != 0:
            blockers.append("entry_requires_flat_no_open_orders")
        if (
            state.entry_attempt_count != 0
            or state.exit_attempt_count != 0
            or state.cancel_attempt_count != 0
        ):
            blockers.append("entry_attempt_budget_exhausted")
        if not (
            _MIN_NOTIONAL_USD
            <= observation.requested_notional_usd
            <= _MAX_NOTIONAL_USD
        ):
            blockers.append("entry_notional_out_of_bounds")
        if observation.available_cash_usd < observation.requested_notional_usd:
            blockers.append("insufficient_cash")
        if (
            observation.principal_at_risk_usd
            + observation.requested_notional_usd
            > _MAX_NOTIONAL_USD
        ):
            blockers.append("principal_at_risk_cap_exceeded")
        if observation.requested_exit_quantity != _ZERO:
            blockers.append("entry_exit_quantity_must_be_zero")
    elif observation.action == "cancel":
        if observation.open_order_count != 1:
            blockers.append("cancel_requires_exactly_one_open_order")
        if state.cancel_attempt_count != 0:
            blockers.append("cancel_attempt_budget_exhausted")
        if (
            not observation.cancel_target_fingerprint
            or observation.cancel_target_fingerprint
            != observation.observed_order_fingerprint
        ):
            blockers.append("cancel_target_not_exactly_observed")
        if observation.requested_notional_usd != _ZERO:
            blockers.append("cancel_notional_must_be_zero")
        if observation.requested_exit_quantity != _ZERO:
            blockers.append("cancel_exit_quantity_must_be_zero")
    else:
        if observation.position_count != 1:
            blockers.append("exit_requires_exactly_one_position")
        if observation.open_order_count != 0:
            blockers.append("exit_requires_no_open_order")
        if state.exit_attempt_count != 0:
            blockers.append("exit_attempt_budget_exhausted")
        if (
            observation.position_quantity <= _ZERO
            or observation.requested_exit_quantity
            != observation.position_quantity
        ):
            blockers.append("exit_requires_exact_full_long_position")
        if observation.requested_notional_usd != _ZERO:
            blockers.append("exit_notional_must_be_zero")

    ordered_blockers = tuple(dict.fromkeys(blockers))
    admitted = not ordered_blockers
    packet: dict[str, object] = {
        "schema_version": _VERDICT_SCHEMA_VERSION,
        "record_type": "crypto_bounded_probe_safety_verdict",
        "classification": (
            "admitted_by_local_safety_policy"
            if admitted
            else "blocked_by_local_safety_policy"
        ),
        "action": observation.action,
        "symbol": observation.symbol,
        "as_of": observation.as_of.isoformat(),
        "policy_fingerprint": (
            CRYPTO_BOUNDED_PROBE_SAFETY_POLICY_FINGERPRINT
        ),
        "state_fingerprint": state.state_fingerprint,
        "local_safety_admitted": admitted,
        "entry_admitted": admitted and observation.action == "entry",
        "risk_reducing_action_admitted": (
            admitted and observation.action in {"cancel", "exit"}
        ),
        "blockers": list(ordered_blockers),
        "claim_recorded": False,
        "action_claim_fingerprint": "",
        "claimed_state_fingerprint": "",
        **_FALSE_AUTHORITY,
        "paper_mutation_occurred": False,
        "live_endpoint_touched": False,
        "profit_claim": "none",
    }
    packet["verdict_fingerprint"] = _stable_hash(packet)
    return packet


def _state_from_row(row: Mapping[str, object]) -> CryptoBoundedProbeSafetyState:
    return _state_from_identity(
        {
            "schema_version": row["schema_version"],
            "policy_fingerprint": row["policy_fingerprint"],
            "selected_symbol": row["selected_symbol"],
            "entry_enabled": bool(row["entry_enabled"]),
            "operator_control_fingerprint": row[
                "operator_control_fingerprint"
            ],
            "loss_halt_latched": bool(row["loss_halt_latched"]),
            "cumulative_net_pnl_usd": row["cumulative_net_pnl_usd"],
            "maximum_observed_loss_usd": row[
                "maximum_observed_loss_usd"
            ],
            "loss_basis_fingerprint": row["loss_basis_fingerprint"],
            "probe_started_at": row["probe_started_at"],
            "probe_episode_fingerprint": row[
                "probe_episode_fingerprint"
            ],
            "entry_attempt_count": row["entry_attempt_count"],
            "exit_attempt_count": row["exit_attempt_count"],
            "cancel_attempt_count": row["cancel_attempt_count"],
            "last_action_fingerprint": row["last_action_fingerprint"],
            "updated_at": row["updated_at"],
            "revision": row["revision"],
        },
        state_fingerprint=str(row["state_fingerprint"]),
    )


def _state_from_identity(
    identity: Mapping[str, object],
    *,
    state_fingerprint: str | None = None,
) -> CryptoBoundedProbeSafetyState:
    if set(identity) != {
        "schema_version",
        "policy_fingerprint",
        "selected_symbol",
        "entry_enabled",
        "operator_control_fingerprint",
        "loss_halt_latched",
        "cumulative_net_pnl_usd",
        "maximum_observed_loss_usd",
        "loss_basis_fingerprint",
        "probe_started_at",
        "probe_episode_fingerprint",
        "entry_attempt_count",
        "exit_attempt_count",
        "cancel_attempt_count",
        "last_action_fingerprint",
        "updated_at",
        "revision",
    }:
        raise ValidationError("bounded-probe safety state keys drifted.")
    entry_enabled = identity["entry_enabled"]
    loss_halt_latched = identity["loss_halt_latched"]
    revision = identity["revision"]
    if type(entry_enabled) is not bool or type(loss_halt_latched) is not bool:
        raise ValidationError("bounded-probe state booleans are invalid.")
    if type(revision) is not int or revision < 0:
        raise ValidationError("bounded-probe state revision is invalid.")
    attempt_counts: dict[str, int] = {}
    for field_name in (
        "entry_attempt_count",
        "exit_attempt_count",
        "cancel_attempt_count",
    ):
        count = identity[field_name]
        if type(count) is not int or not 0 <= count <= 1:
            raise ValidationError(
                "bounded-probe state attempt counters are invalid."
            )
        attempt_counts[field_name] = count
    started_text = str(identity["probe_started_at"])
    state = CryptoBoundedProbeSafetyState(
        schema_version=str(identity["schema_version"]),
        policy_fingerprint=str(identity["policy_fingerprint"]),
        selected_symbol=_symbol(str(identity["selected_symbol"])),
        entry_enabled=entry_enabled,
        operator_control_fingerprint=str(
            identity["operator_control_fingerprint"]
        ),
        loss_halt_latched=loss_halt_latched,
        cumulative_net_pnl_usd=_decimal(
            identity["cumulative_net_pnl_usd"],
            "cumulative_net_pnl_usd",
        ),
        maximum_observed_loss_usd=_decimal(
            identity["maximum_observed_loss_usd"],
            "maximum_observed_loss_usd",
        ),
        loss_basis_fingerprint=str(identity["loss_basis_fingerprint"]),
        probe_started_at=(
            None
            if not started_text
            else _utc_datetime(started_text, "probe_started_at")
        ),
        probe_episode_fingerprint=str(
            identity["probe_episode_fingerprint"]
        ),
        entry_attempt_count=attempt_counts["entry_attempt_count"],
        exit_attempt_count=attempt_counts["exit_attempt_count"],
        cancel_attempt_count=attempt_counts["cancel_attempt_count"],
        last_action_fingerprint=str(identity["last_action_fingerprint"]),
        updated_at=_utc_datetime(identity["updated_at"], "updated_at"),
        revision=revision,
        state_fingerprint="",
    )
    computed = _stable_hash(state.identity())
    final_state = CryptoBoundedProbeSafetyState(
        **{**state.__dict__, "state_fingerprint": state_fingerprint or computed}
    )
    _validate_state(final_state)
    return final_state


def _validate_state(state: CryptoBoundedProbeSafetyState) -> None:
    if (
        state.schema_version != _STATE_SCHEMA_VERSION
        or state.policy_fingerprint
        != CRYPTO_BOUNDED_PROBE_SAFETY_POLICY_FINGERPRINT
        or state.selected_symbol not in CRYPTO_BOUNDED_PROBE_SUPPORTED_SYMBOLS
    ):
        raise ValidationError("bounded-probe safety state identity mismatch.")
    if _stable_hash(state.identity()) != state.state_fingerprint:
        raise ValidationError("bounded-probe safety state fingerprint mismatch.")
    if state.entry_enabled and not state.operator_control_fingerprint:
        raise ValidationError("enabled state lacks operator-control identity.")
    if state.operator_control_fingerprint:
        _sha256(
            state.operator_control_fingerprint,
            "operator_control_fingerprint",
        )
    if state.loss_basis_fingerprint:
        _sha256(state.loss_basis_fingerprint, "loss_basis_fingerprint")
    if state.maximum_observed_loss_usd < _ZERO:
        raise ValidationError("maximum observed loss cannot be negative.")
    if state.maximum_observed_loss_usd < max(
        _ZERO,
        -state.cumulative_net_pnl_usd,
    ):
        raise ValidationError("maximum observed loss understates current loss.")
    if state.maximum_observed_loss_usd > _ZERO and not state.loss_basis_fingerprint:
        raise ValidationError("observed loss lacks loss-basis identity.")
    if state.loss_halt_latched != (
        state.maximum_observed_loss_usd >= _MAX_LOSS_USD
    ):
        raise ValidationError("loss-halt latch disagrees with maximum loss.")
    if state.loss_halt_latched and state.entry_enabled:
        raise ValidationError("loss-halted state cannot enable entry.")
    if state.entry_enabled and state.probe_started_at is None:
        raise ValidationError("enabled state lacks probe start time.")
    if state.probe_started_at is not None and state.probe_started_at > state.updated_at:
        raise ValidationError("probe start cannot be later than state update.")
    if state.probe_started_at is None and state.probe_episode_fingerprint:
        raise ValidationError("probe episode exists without start time.")
    if state.probe_started_at is not None:
        _sha256(
            state.probe_episode_fingerprint,
            "probe_episode_fingerprint",
        )
    for attempt_count in (
        state.entry_attempt_count,
        state.exit_attempt_count,
        state.cancel_attempt_count,
    ):
        if type(attempt_count) is not int or not 0 <= attempt_count <= 1:
            raise ValidationError("bounded-probe attempt counter is invalid.")
    attempts_recorded = (
        state.entry_attempt_count
        + state.exit_attempt_count
        + state.cancel_attempt_count
    )
    if attempts_recorded and not state.last_action_fingerprint:
        raise ValidationError("recorded action lacks claim identity.")
    if state.last_action_fingerprint:
        _sha256(state.last_action_fingerprint, "last_action_fingerprint")


def _state_sql_values(state: CryptoBoundedProbeSafetyState) -> tuple[object, ...]:
    return (
        state.schema_version,
        state.policy_fingerprint,
        state.selected_symbol,
        int(state.entry_enabled),
        state.operator_control_fingerprint,
        int(state.loss_halt_latched),
        _decimal_text(state.cumulative_net_pnl_usd),
        _decimal_text(state.maximum_observed_loss_usd),
        state.loss_basis_fingerprint,
        "" if state.probe_started_at is None else state.probe_started_at.isoformat(),
        state.probe_episode_fingerprint,
        state.entry_attempt_count,
        state.exit_attempt_count,
        state.cancel_attempt_count,
        state.last_action_fingerprint,
        state.updated_at.isoformat(),
        state.revision,
        state.state_fingerprint,
    )


def _local_path(value: Path | str) -> Path:
    text = str(value).strip()
    if not text or "://" in text or text.startswith(("\\\\", "//")):
        raise ValidationError("safety store path must be a local filesystem path.")
    path = Path(text)
    if path.name in {"", ".", "..", ":memory:"}:
        raise ValidationError("safety store path must name a durable file.")
    return path


def _symbol(value: object) -> str:
    symbol = str(value).strip().upper()
    if symbol not in CRYPTO_BOUNDED_PROBE_SUPPORTED_SYMBOLS:
        raise ValidationError("unsupported bounded-probe symbol.")
    return symbol


def _utc_datetime(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be ISO-8601.") from exc
    else:
        raise ValidationError(f"{field_name} must be a datetime.")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError(f"{field_name} must be timezone-aware.")
    return parsed.astimezone(timezone.utc)


def _decimal(value: object, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a finite decimal.")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a finite decimal.") from exc
    if not parsed.is_finite() or abs(parsed) > Decimal("1000000000"):
        raise ValidationError(f"{field_name} must be a bounded finite decimal.")
    return parsed


def _decimal_text(value: Decimal) -> str:
    quantized = value.quantize(_DECIMAL_QUANTUM)
    text = format(quantized, "f").rstrip("0").rstrip(".")
    return text or "0"


def _sha256(value: object, field_name: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValidationError(f"{field_name} must be a SHA-256 digest.")
    return text


def _stable_hash(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
