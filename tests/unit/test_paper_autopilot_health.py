from algotrader.execution.paper_autopilot_health import paper_autopilot_health


def test_health_promotes_ambiguous_order_to_attention() -> None:
    health = paper_autopilot_health(
        {
            "run_id": "run-1",
            "generated_at": "2026-07-11T16:00:00+00:00",
            "blocker_status": "blocked/reconciliation_required",
            "reconciliation": {
                "reconciliation_required": True,
                "order_journal_state": "unknown",
            },
        }
    )

    assert health["severity"] == "attention"
    assert health["alert_codes"] == [
        "order_reconciliation_required",
        "ambiguous_order_state",
    ]
    assert health["network_alert_delivery_attempted"] is False


def test_live_safety_is_critical() -> None:
    health = paper_autopilot_health({"blocker_status": "blocked/live_safety"})

    assert health["severity"] == "critical"
    assert health["healthy"] is False
