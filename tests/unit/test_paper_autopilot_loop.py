from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL
from algotrader.execution.paper_autopilot_loop import (
    PaperAutopilotLoopConfig,
    paper_autopilot_client_order_id,
    run_paper_autopilot_loop,
)


GENERATED_AT = "2026-06-26T14:00:00+00:00"
PAPER_KEY = "paper-key-value"
PAPER_SECRET = "paper-secret-value"


def test_paper_autopilot_noop_when_already_positioned_risk_on(tmp_path: Path) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker(
        positions=({"symbol": "SPY", "qty": Decimal("0.05"), "market_value": "30"},)
    )

    record = _run(tmp_path, bars_csv, broker)

    assert record["sma_posture"] == "risk_on"
    assert record["preview_action_decision"] == "hold/noop"
    assert record["blocker_status"] == "none"
    assert (
        record["daily_cycle"]["daily_cycle_data_freshness_status"]
        == "accepted_data_current"
    )
    assert (
        record["daily_cycle"]["daily_cycle_data_refresh_status"]
        == "no_refresh_required"
    )
    assert record["paper_submit_authorized"] is False
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False
    assert broker.calls == [
        "get_account",
        "get_positions",
        "get_orders:open:SPY",
        "get_orders:all:SPY",
    ]
    _assert_artifacts(record)
    _assert_no_sensitive_values(record)


def test_paper_autopilot_buy_when_risk_on_without_position_or_order(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker()

    record = _run(tmp_path, bars_csv, broker)

    assert record["preview_action_decision"] == "paper_buy_allowed"
    assert record["blocker_status"] == "action/submitted"
    assert record["paper_submit_authorized"] is True
    assert record["paper_submit_performed"] is True
    assert record["broker_mutation_performed"] is True
    assert record["live_mutation_performed"] is False
    assert record["reconciliation_status"] == "reconciled_submit_observed"
    request = broker.submitted_requests[0]
    assert request.symbol == "SPY"
    assert request.side == "buy"
    assert request.notional == Decimal("25.00")
    assert request.qty is None
    assert request.client_order_id.startswith("pa-v207-spy-buy-")
    _assert_no_sensitive_values(record)


def test_paper_autopilot_sell_close_when_risk_off_with_spy_position(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_off")
    broker = FakeAutopilotBroker(
        positions=({"symbol": "SPY", "qty": Decimal("0.04"), "market_value": "24"},)
    )

    record = _run(tmp_path, bars_csv, broker)

    assert record["sma_posture"] == "risk_off"
    assert record["preview_action_decision"] == "paper_sell_close_allowed"
    assert record["paper_submit_authorized"] is True
    assert record["paper_submit_performed"] is True
    request = broker.submitted_requests[0]
    assert request.side == "sell"
    assert request.qty == Decimal("0.04")
    assert request.notional is None
    assert request.client_order_id.startswith("pa-v207-spy-close-")
    _assert_no_sensitive_values(record)


def test_paper_autopilot_blocks_when_open_spy_order_present(tmp_path: Path) -> None:
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

    record = _run(tmp_path, bars_csv, broker)

    assert record["blocker_status"] == "blocked/open_order_present"
    assert record["paper_submit_authorized"] is False
    assert record["broker_mutation_performed"] is False
    assert broker.submitted_requests == []


def test_paper_autopilot_blocks_unexpected_non_spy_position(tmp_path: Path) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    broker = FakeAutopilotBroker(
        positions=({"symbol": "QQQ", "qty": Decimal("1"), "market_value": "400"},)
    )

    record = _run(tmp_path, bars_csv, broker)

    assert record["blocker_status"] == "blocked/unexpected_non_spy_position"
    assert record["paper_submit_authorized"] is False
    assert broker.submitted_requests == []


def test_paper_autopilot_blocks_when_broker_state_not_observed(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(output_root=tmp_path / "out", bars_csv=bars_csv),
        env={},
        broker_client_factory=_forbidden_factory,
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )

    assert record["blocker_status"] == "blocked/broker_state_not_observed"
    assert record["broker_state_observed"] is False
    assert "broker_state_not_observed" in record["safety_labels"]
    assert record["paper_submit_authorized"] is False
    assert record["paper_submit_performed"] is False


def test_paper_autopilot_blocks_live_safety_before_broker_build(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(output_root=tmp_path / "out", bars_csv=bars_csv),
        env={
            **_paper_env(),
            "APP_PROFILE": "live",
            "ALPACA_PAPER_BASE_URL": "https://api.alpaca.markets",
        },
        broker_client_factory=_forbidden_factory,
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
    )

    assert record["blocker_status"] == "blocked/live_safety"
    assert record["preflight"]["live_endpoint_or_profile_detected"] is True
    assert record["paper_submit_authorized"] is False
    assert record["broker_mutation_performed"] is False


def test_paper_autopilot_blocks_duplicate_client_order_id(tmp_path: Path) -> None:
    bars_csv = _write_bars(tmp_path, posture="risk_on")
    as_of_date = "2026-08-08"
    client_order_id = paper_autopilot_client_order_id(
        action="buy",
        symbol="SPY",
        as_of_date=as_of_date,
        data_sha256=hashlib.sha256(bars_csv.read_bytes()).hexdigest(),
    )
    broker = FakeAutopilotBroker(
        recent_orders=(
            {
                "id": "prior-order-1",
                "client_order_id": client_order_id,
                "symbol": "SPY",
                "side": "buy",
                "status": "filled",
            },
        )
    )

    record = _run(tmp_path, bars_csv, broker)

    assert record["execution_plan"]["client_order_id"] == client_order_id
    assert record["blocker_status"] == "blocked/duplicate_client_order_id"
    assert record["paper_submit_authorized"] is False
    assert record["paper_submit_performed"] is False
    assert broker.submitted_requests == []


def test_runs_artifacts_remain_gitignored() -> None:
    assert "runs/" in Path(".gitignore").read_text(encoding="utf-8")


class FakeAutopilotBroker:
    def __init__(
        self,
        *,
        positions: tuple[dict[str, object], ...] = (),
        open_orders: tuple[dict[str, object], ...] = (),
        recent_orders: tuple[dict[str, object], ...] = (),
    ) -> None:
        self.positions = positions
        self.open_orders = list(open_orders)
        self.recent_orders = list(recent_orders)
        self.submitted_requests = []
        self.calls: list[str] = []

    def get_account(self) -> dict[str, object]:
        self.calls.append("get_account")
        return {
            "account_id": "paper-account-id-should-not-serialize",
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
        self.recent_orders.append(order)
        return order


def _run(tmp_path: Path, bars_csv: Path, broker: FakeAutopilotBroker) -> dict[str, object]:
    return run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(output_root=tmp_path / "out", bars_csv=bars_csv),
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


def _assert_artifacts(record: dict[str, object]) -> None:
    paths = record["artifact_paths"]
    assert Path(paths["operating_brief"]).is_file()
    assert Path(paths["operating_record"]).is_file()
    assert Path(paths["manifest"]).is_file()
    assert Path(paths["latest_status"]).is_file()
    latest = json.loads(Path(paths["latest_status"]).read_text(encoding="utf-8"))
    assert latest["run_id"] == record["run_id"]
    record_lines = Path(paths["operating_record"]).read_text(encoding="utf-8").splitlines()
    assert json.loads(record_lines[-1])["run_id"] == record["run_id"]


def _assert_no_sensitive_values(record: dict[str, object]) -> None:
    rendered = json.dumps(record, sort_keys=True)
    assert PAPER_KEY not in rendered
    assert PAPER_SECRET not in rendered
    assert "paper-account-id-should-not-serialize" not in rendered
    assert record["credential_values_exposed"] is False
