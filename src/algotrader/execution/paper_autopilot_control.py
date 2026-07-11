"""Offline operator control for the durable paper-autopilot kill switch."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.execution.order_journal import SqliteOrderJournal
from algotrader.execution.paper_autopilot_operator import PaperAutopilotOperatorConfig


PAPER_AUTOPILOT_CONTROL_SCHEMA_VERSION = "paper_autopilot_control_v2"


@dataclass(frozen=True, slots=True)
class PaperAutopilotControlConfig:
    journal_path: Path | str = "runs/paper_autopilot/state/order_journal.sqlite3"
    action: str = "status"
    reason: str = ""
    backup_path: Path | str | None = None
    # For one-cycle action:
    output_root: Path | str = "runs/paper_autopilot/latest"
    bars_csv: Path | str = "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
    history_root: Path | str | None = None
    as_of_date: str | None = None
    run_date: str | None = None
    symbol: str = "SPY"
    sma_fast_window: int = 50
    sma_slow_window: int = 200
    max_notional: str = "25.00"
    readiness_packet_path: Path | str | None = None
    no_submit: bool = False
    runtime_lease_seconds: int = 900

    def __post_init__(self) -> None:
        object.__setattr__(self, "journal_path", Path(self.journal_path))
        action = self.action.strip().lower()
        if action not in {
            "status",
            "pause",
            "resume",
            "backup",
            "restore",
            "reconcile",
            "one-cycle",
            "start",
            "stop",
        }:
            raise ValidationError(
                "action must be status, pause, resume, backup, restore, reconcile, one-cycle, start, or stop."
            )
        object.__setattr__(self, "action", action)
        reason = self.reason.strip()
        if action == "pause" and not reason:
            raise ValidationError("reason is required when pausing.")
        object.__setattr__(self, "reason", reason)
        if self.backup_path is not None:
            object.__setattr__(self, "backup_path", Path(self.backup_path))
        symbol = str(self.symbol).strip().upper()
        if symbol != "SPY":
            raise ValidationError("paper autopilot control is restricted to SPY.")
        object.__setattr__(self, "symbol", symbol)

    def to_operator_config(self) -> PaperAutopilotOperatorConfig:
        return PaperAutopilotOperatorConfig(
            output_root=self.output_root,
            bars_csv=self.bars_csv,
            history_root=self.history_root,
            as_of_date=self.as_of_date,
            run_date=self.run_date,
            symbol=self.symbol,
            sma_fast_window=self.sma_fast_window,
            sma_slow_window=self.sma_slow_window,
            max_notional=self.max_notional,
            no_submit=self.no_submit,
            readiness_packet_path=self.readiness_packet_path,
            order_journal_path=self.journal_path,
        )


def run_paper_autopilot_control(
    config: PaperAutopilotControlConfig | None = None,
    *,
    timestamp: datetime | None = None,
    env: Mapping[str, str] | None = None,
    broker_client_factory: Any | None = None,
    daily_lab_runner: Any | None = None,
) -> dict[str, Any]:
    """Read or update the local control and lease state with optional broker/history updates."""

    resolved = config or PaperAutopilotControlConfig()
    journal = SqliteOrderJournal(resolved.journal_path)
    occurred_at = timestamp or datetime.now(UTC)
    
    backup_path = resolved.backup_path
    if backup_path is None:
        backup_path = resolved.journal_path.parent / (resolved.journal_path.name + ".bak")

    reconciled_count = 0
    lease_acquired = False
    lease_expires_at = ""
    lease_released = False
    one_cycle_result: dict[str, Any] = {}
    backup_successful = False
    restore_successful = False

    if resolved.action == "pause":
        control = journal.set_runtime_control(
            trading_enabled=False,
            reason=resolved.reason,
            occurred_at=occurred_at,
        )
    elif resolved.action == "resume":
        control = journal.set_runtime_control(
            trading_enabled=True,
            reason=resolved.reason or "operator_resume",
            occurred_at=occurred_at,
        )
    elif resolved.action == "backup":
        journal.backup(backup_path)
        backup_successful = True
        control = journal.get_runtime_control()
    elif resolved.action == "restore":
        journal.restore(backup_path)
        restore_successful = True
        control = journal.get_runtime_control()
    elif resolved.action == "reconcile":
        from algotrader.execution.paper_autopilot_loop import (
            _normalized_env,
            _secret_values,
            _preflight,
            _observe_broker_state,
            _reconcile_journal_from_broker_snapshot,
        )
        process_env = _normalized_env(env)
        secret_values = _secret_values(process_env)
        preflight = _preflight(process_env)
        if preflight.get("paper_profile_ready") is not True:
            raise ValidationError("paper profile and credentials are not ready.")
        broker_state = _observe_broker_state(
            preflight=preflight,
            env=process_env,
            secret_values=secret_values,
            broker_client_factory=broker_client_factory,
        )
        if broker_state.get("broker_state_observed") is not True:
            raise ValidationError(
                f"broker state could not be observed: {broker_state.get('broker_error')}"
            )
        unresolved = journal.unresolved(resolved.symbol)
        reconciled_count = _reconcile_journal_from_broker_snapshot(
            journal=journal,
            unresolved=unresolved,
            broker_state=broker_state,
            occurred_at=occurred_at,
        )
        control = journal.get_runtime_control()
    elif resolved.action == "one-cycle":
        from algotrader.execution.paper_autopilot_operator import run_paper_autopilot_operator
        one_cycle_result = run_paper_autopilot_operator(
            resolved.to_operator_config(),
            env=env,
            broker_client_factory=broker_client_factory,
            daily_lab_runner=daily_lab_runner,
            timestamp=occurred_at.isoformat(),
        )
        control = journal.get_runtime_control()
    elif resolved.action == "start":
        control = journal.set_runtime_control(
            trading_enabled=True,
            reason=resolved.reason or "operator_start",
            occurred_at=occurred_at,
        )
        lease_result = journal.acquire_runtime_lease(
            lease_name="paper-autopilot",
            owner_run_id="operator-control-start",
            occurred_at=occurred_at,
            ttl_seconds=resolved.runtime_lease_seconds,
        )
        lease_acquired = lease_result.acquired
        if lease_result.expires_at:
            lease_expires_at = lease_result.expires_at.isoformat()
    elif resolved.action == "stop":
        control = journal.set_runtime_control(
            trading_enabled=False,
            reason=resolved.reason or "operator_stop",
            occurred_at=occurred_at,
        )
        lease_released = journal.force_release_runtime_lease(lease_name="paper-autopilot")
    else:
        control = journal.get_runtime_control()

    result = {
        "schema_version": PAPER_AUTOPILOT_CONTROL_SCHEMA_VERSION,
        "action": resolved.action,
        "journal_path": str(resolved.journal_path),
        "control": control.to_dict(),
        "trading_enabled": control.trading_enabled,
        "operator_paused": not control.trading_enabled,
        "reason": control.reason,
        "updated_at": control.updated_at.isoformat(),
        "network_access_attempted": resolved.action in {"reconcile", "one-cycle"},
        "broker_access_attempted": resolved.action in {"reconcile", "one-cycle"},
        "broker_mutation_performed": False,
        "live_authorized": False,
    }

    if resolved.action == "backup":
        result["backup_path"] = str(backup_path)
        result["backup_successful"] = backup_successful
    elif resolved.action == "restore":
        result["backup_path"] = str(backup_path)
        result["restore_successful"] = restore_successful
    elif resolved.action == "reconcile":
        result["reconciled_count"] = reconciled_count
        result["unresolved_order_count"] = len(journal.unresolved(resolved.symbol))
    elif resolved.action == "one-cycle":
        result["one_cycle_result"] = one_cycle_result
    elif resolved.action == "start":
        result["lease_acquired"] = lease_acquired
        result["lease_expires_at"] = lease_expires_at
    elif resolved.action == "stop":
        result["lease_released"] = lease_released

    return result


__all__ = [
    "PAPER_AUTOPILOT_CONTROL_SCHEMA_VERSION",
    "PaperAutopilotControlConfig",
    "run_paper_autopilot_control",
]
