"""Compact operational health and alert classification for paper autopilot."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def paper_autopilot_health(record: Mapping[str, Any]) -> dict[str, object]:
    blocker = str(record.get("blocker_status", ""))
    reconciliation = record.get("reconciliation")
    reconciliation = reconciliation if isinstance(reconciliation, Mapping) else {}
    alerts: list[str] = []
    if record.get("operator_paused") is True:
        alerts.append("operator_pause_active")
    if blocker == "blocked/live_safety":
        alerts.append("live_safety_violation")
    if reconciliation.get("reconciliation_required") is True:
        alerts.append("order_reconciliation_required")
    if reconciliation.get("order_journal_state") == "unknown":
        alerts.append("ambiguous_order_state")
    if reconciliation.get("reconciliation_status") == (
        "reconciled_nonterminal_partially_filled"
    ):
        alerts.append("partial_fill_open")
    if blocker.startswith("blocked/stale") or blocker in {
        "blocked/accepted_but_stale",
        "blocked/blocked_future_dated_local_data",
    }:
        alerts.append("market_data_unusable")
    if blocker == "blocked/durable_spy_order_state_unresolved":
        alerts.append("durable_order_state_unresolved")

    if "live_safety_violation" in alerts:
        severity = "critical"
    elif alerts:
        severity = "attention"
    elif blocker not in {"", "none", "action/submitted"}:
        severity = "attention"
        alerts.append("runtime_blocked")
    else:
        severity = "healthy"
    return {
        "schema_version": "paper_autopilot_health_v1",
        "run_id": str(record.get("run_id", "")),
        "generated_at": str(record.get("generated_at", "")),
        "severity": severity,
        "healthy": severity == "healthy",
        "attention_required": severity != "healthy",
        "alert_codes": alerts,
        "blocker_status": blocker,
        "operator_paused": record.get("operator_paused") is True,
        "network_alert_delivery_attempted": False,
    }


__all__ = ["paper_autopilot_health"]
