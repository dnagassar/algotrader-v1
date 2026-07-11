"""Persistent fenced supervisor for one completed NYSE SPY session at a time."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import os
from pathlib import Path
import time
from typing import Any
from uuid import uuid4

from algotrader.errors import ValidationError
from algotrader.execution.exchange_session import NyseExchangeSessionCalendar
from algotrader.execution.order_journal import SqliteOrderJournal
from algotrader.execution.paper_autopilot_operator import (
    PaperAutopilotOperatorConfig,
    run_paper_autopilot_operator,
)

PAPER_AUTOPILOT_SUPERVISOR_SCHEMA_VERSION = "paper_autopilot_supervisor_v2"

Clock = Callable[[], datetime]
Sleeper = Callable[[float], None]
OperatorRunner = Callable[..., Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class PaperAutopilotSupervisorConfig:
    journal_path: Path | str = "runs/paper_autopilot/state/order_journal.sqlite3"
    loop_interval_seconds: int = 15
    lease_ttl_seconds: int = 60
    max_cycle_attempts: int = 2
    symbol: str = "SPY"
    output_root: Path | str = "runs/paper_autopilot/latest"
    bars_csv: Path | str = "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
    max_notional: str = "25.00"

    def __post_init__(self) -> None:
        object.__setattr__(self, "journal_path", Path(self.journal_path))
        symbol = str(self.symbol).strip().upper()
        if symbol != "SPY":
            raise ValidationError("supervisor only supports SPY ETF.")
        object.__setattr__(self, "symbol", symbol)
        for field_name in (
            "loop_interval_seconds",
            "lease_ttl_seconds",
            "max_cycle_attempts",
        ):
            value = getattr(self, field_name)
            if type(value) is not int or value <= 0:
                raise ValidationError(f"{field_name} must be a positive integer.")

    def to_operator_config(self) -> PaperAutopilotOperatorConfig:
        return PaperAutopilotOperatorConfig(
            output_root=self.output_root,
            bars_csv=self.bars_csv,
            symbol=self.symbol,
            max_notional=self.max_notional,
            order_journal_path=self.journal_path,
            runtime_lease_seconds=self.lease_ttl_seconds,
        )


class PaperAutopilotSupervisor:
    """Lease-fenced scheduler with durable completed-session idempotency."""

    def __init__(
        self,
        config: PaperAutopilotSupervisorConfig,
        *,
        env: Mapping[str, str] | None = None,
        broker_client_factory: Any | None = None,
        daily_lab_runner: Any | None = None,
        clock: Clock | None = None,
        sleeper: Sleeper | None = None,
        session_calendar: NyseExchangeSessionCalendar | None = None,
        operator_runner: OperatorRunner | None = None,
        owner_run_id: str | None = None,
    ) -> None:
        self.config = config
        self.env = env if env is not None else os.environ
        self.broker_client_factory = broker_client_factory
        self.daily_lab_runner = daily_lab_runner
        self.clock = clock or (lambda: datetime.now(UTC))
        self.sleeper = sleeper or time.sleep
        self.session_calendar = session_calendar or NyseExchangeSessionCalendar()
        self.operator_runner = operator_runner or run_paper_autopilot_operator
        self.owner_run_id = owner_run_id or f"supervisor-{os.getpid()}-{uuid4()}"
        self.journal = SqliteOrderJournal(config.journal_path)

    def run(self, max_loops: int | None = None) -> None:
        """Run until stopped, lease-fenced out, or the optional test bound is met."""

        if max_loops is not None and (type(max_loops) is not int or max_loops <= 0):
            raise ValidationError("max_loops must be a positive integer or None.")
        started_at = self._now()
        lease = self.journal.acquire_runtime_lease(
            lease_name="paper-autopilot",
            owner_run_id=self.owner_run_id,
            occurred_at=started_at,
            ttl_seconds=self.config.lease_ttl_seconds,
        )
        if not lease.acquired:
            raise ValidationError(f"Could not acquire supervisor lease: {lease.blocker}")
        token = lease.lease_token
        generation = lease.fencing_generation
        acknowledged = False
        loops = 0
        try:
            acknowledged = self.journal.acknowledge_supervisor_start(
                lease_name="paper-autopilot",
                owner_run_id=self.owner_run_id,
                lease_token=token,
                fencing_generation=generation,
                supervisor_pid=os.getpid(),
                occurred_at=started_at,
            )
            if not acknowledged:
                self.journal.update_last_blocked(started_at, "startup_lease_lost")
                return
            while True:
                occurred_at = self._now()
                control = self.journal.get_runtime_control()
                if control.stop_requested:
                    self.journal.update_last_blocked(occurred_at, "stop_requested")
                    return
                renewed = self.journal.acquire_runtime_lease(
                    lease_name="paper-autopilot",
                    owner_run_id=self.owner_run_id,
                    occurred_at=occurred_at,
                    ttl_seconds=self.config.lease_ttl_seconds,
                    lease_token=token,
                )
                if not renewed.acquired or renewed.fencing_generation != generation:
                    self.journal.update_last_blocked(occurred_at, "lease_lost")
                    return
                if not self.journal.update_heartbeat(
                    lease_name="paper-autopilot",
                    owner_run_id=self.owner_run_id,
                    lease_token=token,
                    fencing_generation=generation,
                    occurred_at=occurred_at,
                ):
                    self.journal.update_last_blocked(occurred_at, "heartbeat_lease_lost")
                    return
                if control.trading_enabled:
                    self._run_completed_session_if_eligible(
                        occurred_at=occurred_at,
                        lease_token=token,
                        fencing_generation=generation,
                    )
                loops += 1
                if max_loops is not None and loops >= max_loops:
                    return
                self.sleeper(float(self.config.loop_interval_seconds))
        finally:
            if acknowledged:
                self.journal.clear_supervisor_acknowledgment(
                    lease_name="paper-autopilot",
                    owner_run_id=self.owner_run_id,
                    lease_token=token,
                    fencing_generation=generation,
                    occurred_at=self._now(),
                )
            self.journal.release_runtime_lease(
                lease_name="paper-autopilot",
                owner_run_id=self.owner_run_id,
                lease_token=token,
            )

    def _run_completed_session_if_eligible(
        self,
        *,
        occurred_at: datetime,
        lease_token: str,
        fencing_generation: int,
    ) -> None:
        session = self.session_calendar.latest_completed_session(occurred_at)
        if session is None:
            self.journal.update_last_blocked(
                occurred_at, "no_completed_exchange_session"
            )
            return
        claim = self.journal.claim_supervisor_cycle(
            session_id=session.identity,
            occurred_at=occurred_at,
            max_attempts=self.config.max_cycle_attempts,
        )
        if not claim.acquired:
            self.journal.update_last_blocked(occurred_at, claim.status)
            return
        self.journal.update_last_attempt(occurred_at)
        try:
            result = self.operator_runner(
                self.config.to_operator_config(),
                env=self.env,
                broker_client_factory=self.broker_client_factory,
                daily_lab_runner=self.daily_lab_runner,
                timestamp=occurred_at.isoformat(),
                lease_token=lease_token,
                fencing_generation=fencing_generation,
                lease_owner_run_id=self.owner_run_id,
            )
        except Exception as exc:
            self._complete_failed_cycle(
                session.identity,
                occurred_at,
                "retryable_failure",
                exc.__class__.__name__,
            )
            return
        if _operator_succeeded(result):
            self.journal.complete_supervisor_cycle(
                session_id=session.identity,
                occurred_at=occurred_at,
                outcome="successful",
            )
            self.journal.update_last_success(occurred_at)
            return
        outcome, reason = _failure_outcome(result)
        self._complete_failed_cycle(session.identity, occurred_at, outcome, reason)

    def _complete_failed_cycle(
        self,
        session_id: str,
        occurred_at: datetime,
        outcome: str,
        reason: str,
    ) -> None:
        self.journal.complete_supervisor_cycle(
            session_id=session_id,
            occurred_at=occurred_at,
            outcome=outcome,
            error=reason,
        )
        self.journal.update_last_blocked(occurred_at, reason)

    def _now(self) -> datetime:
        value = self.clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ValidationError("supervisor clock must return an aware datetime.")
        return value.astimezone(UTC)


def _operator_succeeded(result: Mapping[str, Any]) -> bool:
    summary = result.get("operator_summary")
    if isinstance(summary, Mapping) and summary.get("operator_exit_code") == 0:
        return True
    return result.get("operator_exit_code") == 0


def _failure_outcome(result: Mapping[str, Any]) -> tuple[str, str]:
    reconciliation = result.get("reconciliation")
    action = result.get("action_result")
    summary = result.get("operator_summary")
    action = action if isinstance(action, Mapping) else {}
    reconciliation = reconciliation if isinstance(reconciliation, Mapping) else {}
    summary = summary if isinstance(summary, Mapping) else {}
    if (
        action.get("submit_response_ambiguous") is True
        or reconciliation.get("reconciliation_required") is True
        or reconciliation.get("order_journal_state") == "unknown"
    ):
        return "safety_failure", "ambiguous_order_or_reconciliation"
    blocker = str(result.get("blocker_status") or summary.get("blocker_status") or "")
    if blocker.startswith("blocked/") or blocker == "live_safety":
        return "safety_failure", blocker or "safety_blocked"
    error = str(result.get("loop_error") or result.get("error") or "operator_exit_nonzero")
    return "retryable_failure", error[:240]


__all__ = [
    "PAPER_AUTOPILOT_SUPERVISOR_SCHEMA_VERSION",
    "PaperAutopilotSupervisor",
    "PaperAutopilotSupervisorConfig",
]
