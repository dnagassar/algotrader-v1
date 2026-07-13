"""Offline operator control for the durable paper-autopilot kill switch."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from typing import Any
import hashlib

from algotrader.core.time import require_utc_datetime
from algotrader.errors import ValidationError
from algotrader.execution.order_journal import (
    OrderJournalRecord,
    RuntimeControl,
    SqliteOrderJournal,
)
from algotrader.execution.paper_cancellation_planning_adapter import (
    adapt_paper_lifecycle_to_cancellation_plan,
)
from algotrader.execution.paper_autopilot_operator import PaperAutopilotOperatorConfig
from algotrader.execution.paper_order_lifecycle_replay import (
    PaperOrderLifecycleEvent,
)
from algotrader.orchestration.cancellation_planning_policy import (
    CancellationPlanningRequest,
)


PAPER_AUTOPILOT_CONTROL_SCHEMA_VERSION = "paper_autopilot_control_v4"


@dataclass(frozen=True, slots=True)
class PaperAutopilotControlConfig:
    journal_path: Path | str = "runs/paper_autopilot/state/order_journal.sqlite3"
    action: str = "status"
    reason: str = ""
    backup_path: Path | str | None = None
    broker_snapshot_path: Path | str | None = None
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
    runtime_lease_seconds: int = 60
    cancellation_preview_enabled: bool = False
    cancellation_planning_permitted: bool = False
    cancellation_target_client_order_id: str = ""
    cancellation_target_broker_order_id: str = ""
    cancellation_target_symbol: str = ""
    cancellation_reason: str = ""
    cancellation_as_of: datetime | str | None = None
    cancellation_max_record_age_seconds: int = 900

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
        if action == "stop" and not reason:
            raise ValidationError("reason is required when stopping.")
        object.__setattr__(self, "reason", reason)
        if self.backup_path is not None:
            object.__setattr__(self, "backup_path", Path(self.backup_path))
        if self.broker_snapshot_path is not None:
            object.__setattr__(self, "broker_snapshot_path", Path(self.broker_snapshot_path))
        symbol = str(self.symbol).strip().upper()
        if symbol != "SPY":
            raise ValidationError("paper autopilot control is restricted to SPY.")
        object.__setattr__(self, "symbol", symbol)
        for field_name in (
            "cancellation_preview_enabled",
            "cancellation_planning_permitted",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")
        if (
            type(self.cancellation_max_record_age_seconds) is not int
            or self.cancellation_max_record_age_seconds <= 0
        ):
            raise ValidationError(
                "cancellation_max_record_age_seconds must be a positive integer."
            )
        if self.cancellation_preview_enabled:
            if action != "status":
                raise ValidationError(
                    "cancellation preview is available only for status action."
                )
            for field_name in (
                "cancellation_target_client_order_id",
                "cancellation_target_broker_order_id",
                "cancellation_target_symbol",
                "cancellation_reason",
            ):
                object.__setattr__(
                    self,
                    field_name,
                    _required_preview_text(getattr(self, field_name), field_name),
                )
            object.__setattr__(
                self,
                "cancellation_target_symbol",
                self.cancellation_target_symbol.upper(),
            )
            object.__setattr__(
                self,
                "cancellation_as_of",
                _preview_utc_datetime(self.cancellation_as_of),
            )

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
    """Read or update the local control and lease state with offline safety enforcement."""

    resolved = config or PaperAutopilotControlConfig()
    journal = SqliteOrderJournal(resolved.journal_path)
    occurred_at = timestamp or datetime.now(UTC)

    backup_path = resolved.backup_path
    if backup_path is None:
        backup_path = resolved.journal_path.parent / (resolved.journal_path.name + ".bak")

    reconciled_count = 0
    lease_acquired = False
    one_cycle_result: dict[str, Any] = {}
    backup_successful = False
    restore_successful = False
    lease_released = False
    reconciliation_result: dict[str, object] = {}

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
        if resolved.journal_path.resolve() == backup_path.resolve():
            raise ValidationError("Backup source and destination are the same path.")
        journal.backup(backup_path)
        backup_successful = True
        control = journal.get_runtime_control()
    elif resolved.action == "restore":
        control = journal.get_runtime_control()
        if control.trading_enabled:
            raise ValidationError("Restore is blocked when trading is enabled. Pause or stop first.")
        lease = journal.get_lease_details("paper-autopilot")
        if lease is not None and lease.expires_at > occurred_at:
            raise ValidationError("Restore is blocked when a valid runtime lease is active.")
        if resolved.journal_path.resolve() == backup_path.resolve():
            raise ValidationError("Source and destination databases are the same path.")
        if not backup_path.is_file():
            raise ValidationError(f"Backup file not found: {backup_path}")

        try:
            src_conn = sqlite3.connect(backup_path)
            res = src_conn.execute("PRAGMA integrity_check").fetchone()
            if res is None or res[0] != "ok":
                src_conn.close()
                raise ValidationError("Backup file integrity check failed.")
            tables = src_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = {t[0] for t in tables}
            required = {"journal_metadata", "orders", "order_events", "runtime_control", "runtime_leases"}
            if not required.issubset(table_names):
                src_conn.close()
                raise ValidationError("Backup file is missing required tables.")
            ver_row = src_conn.execute("SELECT value FROM journal_metadata WHERE key='schema_version'").fetchone()
            version = int(ver_row[0]) if ver_row is not None else 0
            if version not in {2, 3, 4}:
                src_conn.close()
                raise ValidationError(f"Unsupported backup schema version: {ver_row[0] if ver_row else 'None'}")
            if version == 4 and not {
                "cancel_intents",
                "cancel_events",
            }.issubset(table_names):
                src_conn.close()
                raise ValidationError("Schema-v4 backup is missing cancellation tables.")
            src_conn.close()
        except Exception as exc:
            if not isinstance(exc, ValidationError):
                raise ValidationError(f"Invalid backup database schema or corruption: {exc}")
            raise

        safety_path = resolved.journal_path.with_suffix(resolved.journal_path.suffix + ".pre_restore.bak")
        journal.backup(safety_path)

        try:
            journal.restore(backup_path)
            restore_successful = True
        except Exception as exc:
            journal.restore(safety_path)
            raise ValidationError(f"Restore failed, reverted to safety backup: {exc}")

        control = journal.get_runtime_control()
    elif resolved.action == "reconcile":
        if resolved.broker_snapshot_path is None:
            raise ValidationError("Broker snapshot path is required for reconciliation. Offline broker query is disabled.")

        snapshot_path = Path(resolved.broker_snapshot_path)
        if not snapshot_path.is_file():
            raise ValidationError(f"Broker snapshot file not found: {snapshot_path}")
        try:
            with open(snapshot_path, "r", encoding="utf-8") as f:
                snapshot_data = json.load(f)
        except Exception as exc:
            raise ValidationError(f"Invalid JSON in broker snapshot: {exc}")

        reconciliation_result, observations = _reconcile_local_snapshot(
            journal=journal,
            snapshot=snapshot_data,
            symbol=resolved.symbol,
            occurred_at=occurred_at,
        )
        for record, order in observations:
            journal.record_broker_observation(
                client_order_id=record.client_order_id,
                occurred_at=occurred_at,
                broker_order_id=_text(order.get("id")),
                broker_status=_text(order.get("status")),
                filled_quantity=_text(order.get("filled_qty")) or None,
                filled_average_price=_text(order.get("filled_avg_price")) or None,
            )
            reconciled_count += 1
        journal.record_reconciliation_result(reconciliation_result)
        if reconciliation_result["reconciliation_status"] != "reconciled":
            journal.update_last_blocked(
                occurred_at,
                "local_reconciliation_blocked",
            )

        control = journal.get_runtime_control()
    elif resolved.action == "one-cycle":
        lease = journal.get_lease_details("paper-autopilot")
        if lease is not None and lease.expires_at > occurred_at:
            raise ValidationError(
                "One-cycle is blocked while a supervisor lease is active."
            )

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
        control = journal.request_supervisor_start(occurred_at)

        cmd = [
            sys.executable,
            "-m",
            "algotrader.cli",
            "paper-autopilot-supervisor",
            "--order-journal-path",
            str(resolved.journal_path),
            "--loop-interval-seconds",
            str(resolved.runtime_lease_seconds // 4 or 15),
            "--lease-ttl-seconds",
            str(resolved.runtime_lease_seconds),
            "--symbol",
            resolved.symbol,
            "--output-root",
            str(resolved.output_root),
            "--bars-csv",
            str(resolved.bars_csv),
            "--max-notional",
            resolved.max_notional,
        ]

        try:
            subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
                close_fds=True,
            )
            lease_acquired = False
        except Exception as exc:
            raise ValidationError(f"Failed to spawn supervisor process: {exc}")
    elif resolved.action == "stop":
        existing_control = journal.get_runtime_control()
        control = journal.set_runtime_control(
            trading_enabled=existing_control.trading_enabled,
            reason=resolved.reason or "operator_stop",
            occurred_at=occurred_at,
            stop_requested=True,
        )
        lease_released = False
    else:
        control = journal.get_runtime_control()

    lease = journal.get_lease_details("paper-autopilot")
    lease_valid = False
    lease_owner = ""
    lease_token_sanitized = ""
    lease_expiry = ""
    heartbeat_fresh = False

    if lease is not None:
        lease_valid = lease.expires_at > occurred_at
        lease_owner = lease.owner_run_id
        if lease.lease_token:
            lease_token_sanitized = lease.lease_token[:8] + "..."
        lease_expiry = lease.expires_at.isoformat()
        if control.heartbeat_at:
            try:
                hb = datetime.fromisoformat(control.heartbeat_at)
                heartbeat_fresh = (occurred_at - hb).total_seconds() < 120
            except ValueError:
                pass

    supervisor_running = False
    if control.supervisor_pid > 0 and lease_valid and heartbeat_fresh:
        try:
            os.kill(control.supervisor_pid, 0)
            supervisor_running = True
        except OSError:
            supervisor_running = False

    result = {
        "schema_version": PAPER_AUTOPILOT_CONTROL_SCHEMA_VERSION,
        "action": resolved.action,
        "journal_path": str(resolved.journal_path),
        "control": control.to_dict(),
        "trading_enabled": control.trading_enabled,
        "operator_paused": not control.trading_enabled,
        "stop_requested": control.stop_requested,
        "control_generation": control.control_generation,
        "reason": control.reason,
        "updated_at": control.updated_at.isoformat(),
        "supervisor_running": supervisor_running,
        "lease_valid": lease_valid,
        "lease_owner": lease_owner,
        "lease_token_sanitized": lease_token_sanitized,
        "lease_expiry": lease_expiry,
        "heartbeat_fresh": heartbeat_fresh,
        "last_attempt_at": control.last_attempt_at,
        "last_success_at": control.last_success_at,
        "last_blocked_reason": control.last_blocked_reason,
        "network_access_attempted": resolved.action in {"one-cycle"},
        "broker_access_attempted": resolved.action in {"one-cycle"},
        "broker_mutation_performed": False,
        "live_authorized": False,
        "cancellation_planning_preview_enabled": (
            resolved.cancellation_preview_enabled
        ),
        "cancellation_planning_preview": _disabled_cancellation_preview(),
    }

    if resolved.cancellation_preview_enabled:
        result["cancellation_planning_preview"] = (
            _journal_cancellation_planning_preview(
                config=resolved,
                journal=journal,
                control=control,
            )
        )

    if resolved.action == "backup":
        result["backup_path"] = str(backup_path)
        result["backup_successful"] = backup_successful
    elif resolved.action == "restore":
        result["backup_path"] = str(backup_path)
        result["restore_successful"] = restore_successful
    elif resolved.action == "reconcile":
        result["reconciled_count"] = reconciled_count
        result["unresolved_order_count"] = len(journal.unresolved(resolved.symbol))
        result["reconciliation"] = reconciliation_result
    elif resolved.action == "one-cycle":
        result["one_cycle_result"] = one_cycle_result
    elif resolved.action == "start":
        result["lease_acquired"] = lease_acquired
        result["startup_requested"] = True
        result["startup_acknowledged"] = supervisor_running
    elif resolved.action == "stop":
        result["lease_released"] = lease_released

    return result


def _journal_cancellation_planning_preview(
    *,
    config: PaperAutopilotControlConfig,
    journal: SqliteOrderJournal,
    control: RuntimeControl,
) -> dict[str, object]:
    as_of = config.cancellation_as_of
    assert isinstance(as_of, datetime)
    records = journal.records()
    client_matches = tuple(
        record
        for record in records
        if record.client_order_id == config.cancellation_target_client_order_id
    )
    broker_matches = tuple(
        record
        for record in records
        if record.broker_order_id == config.cancellation_target_broker_order_id
    )
    record: OrderJournalRecord | None = None
    if len(broker_matches) <= 1:
        if len(client_matches) == 1:
            record = client_matches[0]
        elif len(broker_matches) == 1:
            record = broker_matches[0]

    events: tuple[PaperOrderLifecycleEvent, ...] = ()
    observation_symbol: str | None = None
    snapshot_fresh = False
    if record is not None:
        age_seconds = (as_of - record.updated_at).total_seconds()
        snapshot_fresh = (
            0 <= age_seconds <= config.cancellation_max_record_age_seconds
        )
        events = (
            PaperOrderLifecycleEvent(
                observed_at=record.updated_at.isoformat(),
                client_order_id=record.client_order_id,
                broker_order_id=record.broker_order_id,
                status=record.broker_status,
                filled_qty=record.filled_quantity,
                submitted=bool(record.broker_order_id),
                mutated=bool(record.broker_order_id),
                source="local_order_journal_record",
            ),
        )
        observation_symbol = record.symbol

    artifact = adapt_paper_lifecycle_to_cancellation_plan(
        events,
        request=CancellationPlanningRequest(
            target_client_order_id=config.cancellation_target_client_order_id,
            target_broker_order_id=config.cancellation_target_broker_order_id,
            target_symbol=config.cancellation_target_symbol,
            reason=config.cancellation_reason,
            cancellation_permitted=config.cancellation_planning_permitted,
            snapshot_fresh=snapshot_fresh,
            trading_enabled=control.trading_enabled,
            stop_requested=control.stop_requested,
        ),
        as_of=as_of,
        observation_symbol=observation_symbol,
    )
    return artifact.to_dict()


def _disabled_cancellation_preview() -> dict[str, object]:
    return {
        "status": "disabled",
        "no_submit": True,
        "cancel_attempted": False,
        "broker_access_performed": False,
        "broker_mutation_performed": False,
    }


def _required_preview_text(value: object, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValidationError(f"{field_name} is required when preview is enabled.")
    return text


def _preview_utc_datetime(value: datetime | str | None) -> datetime:
    parsed = value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValidationError(
                "cancellation_as_of is required when preview is enabled."
            )
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(
                "cancellation_as_of must be an ISO-8601 UTC datetime."
            ) from exc
    try:
        return require_utc_datetime(parsed)  # type: ignore[arg-type]
    except ValidationError as exc:
        raise ValidationError(
            "cancellation_as_of must be an ISO-8601 UTC datetime."
        ) from exc


__all__ = [
    "PAPER_AUTOPILOT_CONTROL_SCHEMA_VERSION",
    "PaperAutopilotControlConfig",
    "run_paper_autopilot_control",
]


_TERMINAL_ORDER_STATUSES = frozenset(
    {"filled", "rejected", "canceled", "cancelled", "expired"}
)
_KNOWN_ORDER_STATUSES = _TERMINAL_ORDER_STATUSES | frozenset(
    {"new", "accepted", "pending_new", "open", "pending_cancel", "partially_filled"}
)
_SNAPSHOT_MAX_AGE_SECONDS = 900


def _reconcile_local_snapshot(
    *,
    journal: SqliteOrderJournal,
    snapshot: object,
    symbol: str,
    occurred_at: datetime,
) -> tuple[dict[str, object], list[tuple[object, dict[str, object]]]]:
    """Compare a local immutable snapshot to the journal without broker access."""

    if not isinstance(snapshot, dict):
        raise ValidationError("Broker snapshot must be a JSON object.")
    account = snapshot.get("account")
    positions = snapshot.get("positions")
    orders = snapshot.get("orders")
    provenance = snapshot.get("provenance")
    if not isinstance(account, dict) or not isinstance(positions, list) or not isinstance(orders, list):
        raise ValidationError("Broker snapshot account, positions, and orders are required.")
    if not isinstance(provenance, dict):
        raise ValidationError("Broker snapshot provenance is required.")
    if provenance.get("schema_version") != "broker_snapshot_v1":
        raise ValidationError("Broker snapshot schema version is unsupported.")
    generated_at = _snapshot_timestamp(provenance.get("generated_at"))
    canonical_payload = {
        "account": account,
        "positions": positions,
        "orders": orders,
    }
    expected_hash = hashlib.sha256(
        json.dumps(canonical_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    supplied_hash = _text(provenance.get("snapshot_sha256"))
    findings: list[str] = []
    if supplied_hash != expected_hash:
        findings.append("snapshot_integrity_unverified")
    if generated_at > occurred_at or (occurred_at - generated_at).total_seconds() > _SNAPSHOT_MAX_AGE_SECONDS:
        findings.append("snapshot_not_fresh")

    if _text(account.get("status")).upper() != "ACTIVE":
        findings.append("account_status_not_active")
    if account.get("tradable") is not True:
        findings.append("account_not_tradable")
    if account.get("trading_blocked") is not False:
        findings.append("account_trading_blocked_or_unknown")
    if _nonnegative_decimal(account.get("cash")) is None:
        findings.append("account_cash_missing_or_invalid")
    if _nonnegative_decimal(account.get("buying_power")) is None:
        findings.append("account_buying_power_missing_or_invalid")

    position_symbols: set[str] = set()
    for position in positions:
        if not isinstance(position, dict):
            findings.append("ambiguous_position_entry")
            continue
        position_symbol = _text(position.get("symbol")).upper()
        if not position_symbol or position_symbol in position_symbols:
            findings.append("ambiguous_position_entry")
            continue
        position_symbols.add(position_symbol)
        if _nonnegative_decimal(position.get("quantity")) is None:
            findings.append(f"position_quantity_invalid:{position_symbol}")
        if position_symbol != symbol:
            findings.append(f"unexpected_symbol:{position_symbol}")

    broker_orders: dict[str, dict[str, object]] = {}
    for order in orders:
        if not isinstance(order, dict):
            findings.append("ambiguous_order_entry")
            continue
        client_order_id = _text(order.get("client_order_id"))
        status = _text(order.get("status")).lower()
        if not client_order_id or client_order_id in broker_orders:
            findings.append("ambiguous_order_entry")
            continue
        if status not in _KNOWN_ORDER_STATUSES:
            findings.append(f"unknown_order_status:{client_order_id}")
            continue
        broker_orders[client_order_id] = order
        if status not in _TERMINAL_ORDER_STATUSES:
            findings.append(f"conflicting_open_order:{client_order_id}")

    journal_records = {record.client_order_id: record for record in journal.records()}
    observations: list[tuple[object, dict[str, object]]] = []
    known_order_count = 0
    terminal_order_count = 0
    partial_fill_count = 0
    for client_order_id, record in journal_records.items():
        observed = broker_orders.get(client_order_id)
        if observed is None:
            if record.terminal:
                findings.append(f"terminal_order_missing:{client_order_id}")
                terminal_order_count += 1
            else:
                findings.append(f"journal_nonterminal_order_missing:{client_order_id}")
            continue
        known_order_count += 1
        status = _text(observed.get("status")).lower()
        filled = _nonnegative_decimal(observed.get("filled_qty"))
        if filled is None:
            findings.append(f"filled_quantity_invalid:{client_order_id}")
            continue
        if record.filled_quantity is not None and filled < record.filled_quantity:
            findings.append(f"cumulative_fill_decreased:{client_order_id}")
            continue
        if status == "partially_filled" or filled > Decimal("0") and status not in _TERMINAL_ORDER_STATUSES:
            partial_fill_count += 1
            findings.append(f"partial_fill_open:{client_order_id}")
        if status in _TERMINAL_ORDER_STATUSES:
            terminal_order_count += 1
        observations.append((record, observed))

    for client_order_id in sorted(set(broker_orders) - set(journal_records)):
        findings.append(f"broker_only_order:{client_order_id}")

    normalized_findings = sorted(set(findings))
    result: dict[str, object] = {
        "schema_version": "local_snapshot_reconciliation_v1",
        "snapshot_generated_at": generated_at.isoformat(),
        "snapshot_sha256": supplied_hash,
        "snapshot_fresh": "snapshot_not_fresh" not in normalized_findings,
        "reconciliation_status": "reconciled" if not normalized_findings else "blocked",
        "fail_closed": bool(normalized_findings),
        "findings": normalized_findings,
        "known_order_count": known_order_count,
        "broker_only_order_count": sum(
            item.startswith("broker_only_order:") for item in normalized_findings
        ),
        "journal_only_nonterminal_count": sum(
            item.startswith("journal_nonterminal_order_missing:") for item in normalized_findings
        ),
        "terminal_order_count": terminal_order_count,
        "partial_fill_count": partial_fill_count,
        "position_symbols": sorted(position_symbols),
        "cash": str(_nonnegative_decimal(account.get("cash")) or ""),
        "buying_power": str(_nonnegative_decimal(account.get("buying_power")) or ""),
        "account_status": _text(account.get("status")),
        "account_tradable": account.get("tradable") is True,
        "account_trading_blocked": account.get("trading_blocked") is True,
    }
    return result, observations


def _snapshot_timestamp(value: object) -> datetime:
    try:
        parsed = datetime.fromisoformat(_text(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError("Broker snapshot generated_at must be an ISO timestamp.") from exc
    if parsed.tzinfo is None:
        raise ValidationError("Broker snapshot generated_at must be timezone-aware.")
    return parsed.astimezone(UTC)


def _nonnegative_decimal(value: object) -> Decimal | None:
    if value is None or _text(value) == "":
        return None
    try:
        parsed = Decimal(_text(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed >= Decimal("0") else None


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""
