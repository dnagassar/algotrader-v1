from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL
from algotrader.execution.paper_autopilot_operator import (
    PaperAutopilotOperatorConfig,
    paper_autopilot_operator_exit_status,
    render_paper_autopilot_operator_summary,
    run_paper_autopilot_operator,
)


GENERATED_AT = "2026-06-26T14:00:00+00:00"
PAPER_KEY = "paper-key-value"
PAPER_SECRET = "paper-secret-value"
EXPECTED_ACCOUNT_ID = "paper-account-id-should-not-serialize"


def test_operator_healthy_hold_noop_returns_zero(tmp_path: Path) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker(
        positions=({"symbol": "SPY", "qty": Decimal("0.05"), "market_value": "30"},)
    )

    result = _run_operator(tmp_path, bars_csv, broker)

    summary = result["operator_summary"]
    assert summary["classification"] == "healthy_hold_noop"
    assert summary["anomaly_classification"] == "healthy_hold_noop"
    assert summary["action_decision"] == "hold/noop"
    assert summary["paper_submit_performed"] is False
    assert summary["broker_mutation_performed"] is False
    assert summary["live_mutation_performed"] is False
    assert paper_autopilot_operator_exit_status(result) == 0
    assert result["rollup"]["history_count"] == 1
    rendered = render_paper_autopilot_operator_summary(summary)
    assert "classification=healthy_hold_noop" in rendered
    assert "operator_exit_code=0" in rendered
    _assert_history_artifacts(result)


def test_operator_healthy_paper_action_reconciled_returns_zero(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker()

    result = _run_operator(tmp_path, bars_csv, broker)

    summary = result["operator_summary"]
    assert summary["classification"] == "healthy_paper_action_reconciled"
    assert summary["action_decision"] == "paper_buy_allowed"
    assert summary["paper_submit_performed"] is True
    assert summary["broker_mutation_performed"] is True
    assert summary["reconciliation_status"] == "reconciled_submit_observed"
    assert paper_autopilot_operator_exit_status(result) == 0


def test_operator_broker_state_not_observed_is_explicit_nonzero(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")

    result = run_paper_autopilot_operator(
        PaperAutopilotOperatorConfig(output_root=tmp_path / "out", bars_csv=bars_csv),
        env={},
        broker_client_factory=_forbidden_factory,
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )

    summary = result["operator_summary"]
    assert summary["classification"] == "broker_state_not_observed"
    assert summary["broker_state_mode"] == "broker_state_not_observed"
    assert summary["blocker_status"] == "blocked/broker_state_not_observed"
    assert paper_autopilot_operator_exit_status(result) == 1


def test_operator_live_safety_blocked_is_hard_stop_nonzero(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")

    result = run_paper_autopilot_operator(
        PaperAutopilotOperatorConfig(output_root=tmp_path / "out", bars_csv=bars_csv),
        env={
            **_paper_env(),
            "APP_PROFILE": "live",
            "ALPACA_PAPER_BASE_URL": "https://api.alpaca.markets",
        },
        broker_client_factory=_forbidden_factory,
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )

    summary = result["operator_summary"]
    assert summary["classification"] == "live_safety_blocked"
    assert summary["blocker_status"] == "blocked/live_safety"
    assert result["rollup"]["hard_stop"] is True
    assert paper_autopilot_operator_exit_status(result) == 2


def test_operator_reconciliation_required_is_nonzero(tmp_path: Path) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker(hide_submitted_order_from_reconciliation=True)

    result = _run_operator(tmp_path, bars_csv, broker)

    summary = result["operator_summary"]
    assert summary["classification"] == "reconciliation_required"
    assert summary["blocker_status"] == "blocked/reconciliation_required"
    assert summary["paper_submit_performed"] is True
    assert summary["broker_mutation_performed"] is True
    assert summary["reconciliation_status"] == "reconciliation_required"
    assert paper_autopilot_operator_exit_status(result) == 1


def test_operator_unexpected_non_spy_position_is_nonzero(tmp_path: Path) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker(
        positions=({"symbol": "QQQ", "qty": Decimal("1"), "market_value": "400"},)
    )

    result = _run_operator(tmp_path, bars_csv, broker)

    summary = result["operator_summary"]
    assert summary["classification"] == "unexpected_position_blocked"
    assert summary["blocker_status"] == "blocked/unexpected_non_spy_position"
    assert summary["broker_mutation_performed"] is False
    assert paper_autopilot_operator_exit_status(result) == 1


def test_operator_open_spy_order_conflict_is_nonzero(tmp_path: Path) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker(
        open_orders=(
            {
                "id": "open-order-1",
                "client_order_id": "existing-spy-order",
                "symbol": "SPY",
                "side": "buy",
                "status": "accepted",
            },
        )
    )

    result = _run_operator(tmp_path, bars_csv, broker)

    summary = result["operator_summary"]
    assert summary["classification"] == "open_order_conflict_blocked"
    assert summary["blocker_status"] == "blocked/open_order_present"
    assert summary["broker_mutation_performed"] is False
    assert paper_autopilot_operator_exit_status(result) == 1


def test_operator_no_submit_buy_intent_is_visibility_only_nonzero(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker()

    result = run_paper_autopilot_operator(
        PaperAutopilotOperatorConfig(
            output_root=tmp_path / "out",
            bars_csv=bars_csv,
            no_submit=True,
        ),
        env=_paper_env(),
        broker_client_factory=_factory(broker),
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )

    summary = result["operator_summary"]
    assert summary["classification"] == "mutation_would_be_required_no_submit_mode"
    assert summary["blocker_status"] == "blocked/mutation_would_be_required_no_submit_mode"
    assert summary["action_decision"] == "paper_buy_blocked_no_submit_mode"
    assert summary["no_submit_mode"] is True
    assert summary["paper_submit_performed"] is False
    assert summary["broker_mutation_performed"] is False
    assert result["rollup"]["broker_read_performed"] is True
    assert result["rollup"]["intended_mutation_action"] == "buy"
    assert result["rollup"]["mutation_would_be_required_without_no_submit"] is True
    assert broker.submitted_requests == []
    assert "submit_order" not in broker.calls
    assert paper_autopilot_operator_exit_status(result) == 1


def test_operator_missing_latest_status_artifact_is_nonzero(tmp_path: Path) -> None:
    def no_status_loop(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return {"run_id": "loop-returned-without-status"}

    result = run_paper_autopilot_operator(
        PaperAutopilotOperatorConfig(
            output_root=tmp_path / "out",
            bars_csv=tmp_path / "unused.csv",
        ),
        loop_runner=no_status_loop,
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )

    summary = result["operator_summary"]
    assert summary["classification"] == "stale_or_missing_status_artifact"
    assert summary["run_id"] == ""
    assert paper_autopilot_operator_exit_status(result) == 1


class FakeAutopilotBroker:
    def __init__(
        self,
        *,
        positions: tuple[dict[str, object], ...] = (),
        open_orders: tuple[dict[str, object], ...] = (),
        recent_orders: tuple[dict[str, object], ...] = (),
        hide_submitted_order_from_reconciliation: bool = False,
    ) -> None:
        self.positions = positions
        self.open_orders = list(open_orders)
        self.recent_orders = list(recent_orders)
        self.hide_submitted_order_from_reconciliation = (
            hide_submitted_order_from_reconciliation
        )
        self.submitted_requests = []
        self.calls: list[str] = []

    def get_account(self) -> dict[str, object]:
        self.calls.append("get_account")
        return {
            "account_id": EXPECTED_ACCOUNT_ID,
            "status": "ACTIVE",
            "tradable": True,
            "cash": Decimal("100000"),
            "buying_power": Decimal("100000"),
            "currency": "USD",
        }

    def get_positions(self) -> tuple[dict[str, object], ...]:
        self.calls.append("get_positions")
        return self.positions

    def get_orders(self, query) -> tuple[dict[str, object], ...]:  # noqa: ANN001
        self.calls.append(f"get_orders:{query.status_filter}:{query.symbol_filter}")
        rows = list(self.open_orders if query.status_filter == "open" else self.recent_orders)
        if query.status_filter == "all":
            rows.extend(self.open_orders)
        if query.symbol_filter:
            rows = [
                row
                for row in rows
                if str(row.get("symbol", "")).upper() == query.symbol_filter
            ]
        return tuple(rows)

    def submit_order(self, request) -> dict[str, object]:  # noqa: ANN001
        self.calls.append("submit_order")
        self.submitted_requests.append(request)
        order = {
            "id": "paper-order-1",
            "client_order_id": request.client_order_id,
            "symbol": request.symbol,
            "side": request.side,
            "status": "accepted",
            "type": request.order_type,
            "time_in_force": request.time_in_force,
            "notional": request.notional,
            "qty": request.qty,
            "filled_qty": Decimal("0"),
        }
        if not self.hide_submitted_order_from_reconciliation:
            self.recent_orders.append(order)
        return order


def _run_operator(
    tmp_path: Path,
    bars_csv: Path,
    broker: FakeAutopilotBroker,
) -> dict[str, object]:
    return run_paper_autopilot_operator(
        PaperAutopilotOperatorConfig(output_root=tmp_path / "out", bars_csv=bars_csv),
        env=_paper_env(),
        broker_client_factory=_factory(broker),
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )


def _paper_env() -> dict[str, str]:
    return {
        "APP_PROFILE": "paper",
        "APCA_API_KEY_ID": PAPER_KEY,
        "APCA_API_SECRET_KEY": PAPER_SECRET,
        "ALPACA_EXPECTED_PAPER_ACCOUNT_ID": EXPECTED_ACCOUNT_ID,
        "ALPACA_PAPER_BASE_URL": DEFAULT_ALPACA_PAPER_BASE_URL,
    }


def _factory(fake_broker: FakeAutopilotBroker):
    def build(_config):  # noqa: ANN001
        return fake_broker

    return build


def _forbidden_factory(_config):  # noqa: ANN001
    raise AssertionError("broker factory must not be called")


def _fake_daily_lab(config):  # noqa: ANN001
    return {
        "preview_decision": "fake_daily_cycle_ran",
        "blocker_status": "none",
        "next_operator_action": "none",
        "latest_bar_date": "2026-08-08",
        "data_freshness_status": "accepted_data_current",
        "data_refresh_status": "no_refresh_required",
        "expected_latest_bar_date": "2026-08-08",
        "data_freshness_plan_path": str(
            Path(config.output_root) / "data_freshness_plan.json"
        ),
        "data_refresh_bridge_path": str(
            Path(config.output_root) / "data_refresh_bridge.json"
        ),
        "data_refresh_dry_run_path": str(
            Path(config.output_root) / "data_refresh_dry_run.json"
        ),
        "output_root": str(config.output_root),
    }


def _write_bars(tmp_path: Path, *, posture: str) -> Path:
    path = tmp_path / f"{posture}.csv"
    start = date(2026, 1, 1)
    rows = ["date,symbol,open,high,low,close,adjusted_close,volume"]
    for index in range(220):
        current = start + timedelta(days=index)
        close = Decimal("100") + Decimal(index)
        if posture == "risk_off":
            close = Decimal("500") - Decimal(index)
        rows.append(
            f"{current.isoformat()},SPY,{close},{close},{close},{close},{close},1000"
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def _assert_history_artifacts(result: dict[str, object]) -> None:
    artifact_paths = result["rollup"]["artifact_paths"]
    assert Path(artifact_paths["operating_history"]).is_file()
    assert Path(artifact_paths["latest_rollup"]).is_file()
    assert Path(artifact_paths["operating_summary"]).is_file()
    latest_rollup = json.loads(
        Path(artifact_paths["latest_rollup"]).read_text(encoding="utf-8")
    )
    assert latest_rollup["classification"] == result["operator_summary"]["classification"]
