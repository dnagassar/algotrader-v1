from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import algotrader.cli as cli_module
from algotrader.cli import main
from algotrader.core.types import Bar
from algotrader.execution.etf_sma_cycle_preview import (
    ETF_SMA_CYCLE_PREVIEW_LABELS,
    EtfSmaCycleBrokerObservation,
    EtfSmaCyclePreviewConfig,
    build_etf_sma_cycle_preview,
)


_START = datetime(2025, 1, 1, tzinfo=UTC)
_M376_CLIENT_ORDER_ID = "paper-order-close-m376_spy_paper_close_submit"
_M376_BROKER_ORDER_ID = "dbb32dd3-58bf-49ea-b9b1-9aa44e85002d"
_M376_QUANTITY = "0.033172072"


def test_bullish_no_position_builds_buy_preview_only() -> None:
    preview = _preview(_bullish_bars(), _flat_observation())
    payload = preview.to_dict()

    assert payload["decision"] == "buy_preview"
    assert payload["preview_order"] == {
        "asset_class": "equity",
        "notional": "25.00",
        "order_type": "market",
        "side": "buy",
        "symbol": "SPY",
        "time_in_force": "day",
    }
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False


def test_bullish_existing_spy_position_holds_without_order_preview() -> None:
    preview = _preview(
        _bullish_bars(),
        _spy_position_observation(quantity="0.033172072"),
    )
    payload = preview.to_dict()

    assert payload["decision"] == "hold"
    assert payload["decision_reason"] == "bullish_existing_spy_position"
    assert payload["spy_position_quantity"] == "0.033172072"
    assert "preview_order" not in payload


def test_risk_off_existing_spy_position_builds_sell_preview_only() -> None:
    preview = _preview(
        _risk_off_bars(),
        _spy_position_observation(quantity="0.033172072"),
    )
    payload = preview.to_dict()

    assert payload["decision"] == "sell_preview"
    assert payload["preview_order"] == {
        "asset_class": "equity",
        "order_type": "market",
        "quantity": "0.033172072",
        "side": "sell",
        "symbol": "SPY",
        "time_in_force": "day",
    }
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False


def test_risk_off_no_position_holds_without_order_preview() -> None:
    preview = _preview(_risk_off_bars(), _flat_observation())
    payload = preview.to_dict()

    assert payload["decision"] == "hold"
    assert payload["decision_reason"] == "risk_off_no_spy_position"
    assert "preview_order" not in payload


def test_insufficient_history_has_no_order_preview() -> None:
    preview = _preview(_bars(*(199 * ("10",))), _flat_observation())
    payload = preview.to_dict()

    assert payload["decision"] == "insufficient_history"
    assert payload["sma_status"] == "insufficient_history"
    assert payload["sma_posture"] == "insufficient_history"
    assert "preview_order" not in payload


def test_open_spy_order_blocks_without_order_preview_or_submit() -> None:
    preview = _preview(
        _bullish_bars(),
        _flat_observation(open_order_count=1, open_order_symbols=("SPY",)),
    )
    payload = preview.to_dict()

    assert payload["decision"] == "blocked"
    assert payload["decision_reason"] == "open_order_present"
    assert payload["blockers"] == ["open_order_present"]
    assert "preview_order" not in payload
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False


def test_unexpected_non_spy_position_blocks() -> None:
    preview = _preview(
        _bullish_bars(),
        EtfSmaCycleBrokerObservation(
            paper_profile_gate_passed=True,
            account_observation_available=True,
            positions_observation_available=True,
            orders_observation_available=True,
            cash=Decimal("1000"),
            currency="USD",
            position_count=1,
            position_symbols=("MSFT",),
            open_order_count=0,
        ),
    )
    payload = preview.to_dict()

    assert payload["decision"] == "blocked"
    assert payload["blockers"] == ["unexpected_non_spy_position"]
    assert "preview_order" not in payload


def test_missing_broker_observations_in_paper_facing_mode_blocks() -> None:
    preview = _preview(
        _bullish_bars(),
        EtfSmaCycleBrokerObservation(
            paper_profile_gate_passed=True,
            unavailable_observations=("account", "positions", "orders"),
        ),
    )
    payload = preview.to_dict()

    assert payload["decision"] == "blocked"
    assert "account_observation_unavailable" in payload["blockers"]
    assert "broker_observations_unavailable" in payload["blockers"]
    assert "preview_order" not in payload


def test_output_preserves_required_safety_labels() -> None:
    payload = _preview(_bullish_bars(), _flat_observation()).to_dict()

    assert payload["labels"] == list(ETF_SMA_CYCLE_PREVIEW_LABELS)
    assert "paper_lab_only" in payload["labels"]
    assert "not_live_authorized" in payload["labels"]
    assert "profit_claim=none" in payload["labels"]
    assert payload["profit_claim"] == "none"


def test_cli_dev_preview_does_not_construct_real_broker(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_dev_env(monkeypatch)

    def forbidden_build(paper_config):  # noqa: ANN001
        raise AssertionError("normal pytest must not build a paper broker")

    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_build)
    bars_csv = _write_bars_csv(tmp_path, _bullish_closes())
    run_log = tmp_path / "runs" / "paper_lab" / "cycle.jsonl"

    exit_code, payload = _run_json(
        (
            "etf-sma-cycle-preview",
            "--symbol",
            "SPY",
            "--bars-csv",
            str(bars_csv),
            "--run-log",
            str(run_log),
            "--run-id",
            "spy_etf_sma_cycle_preview",
            "--format",
            "json",
        ),
        capsys,
    )

    records = _read_jsonl(run_log)
    assert exit_code == 0
    assert payload["decision"] == "blocked"
    assert payload["decision_reason"] == "paper_profile_required"
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert len(records) == 1
    assert records[0] == payload


def test_cli_paper_preview_blocks_existing_m376_open_spy_order(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_paper_env(monkeypatch)
    fake_broker = FakeCycleBroker(
        positions=[
            {
                "average_price": "753.646",
                "quantity": _M376_QUANTITY,
                "symbol": "SPY",
            }
        ],
        open_orders=[
            {
                "asset_class": "equity",
                "client_order_id": _M376_CLIENT_ORDER_ID,
                "normalized_status": "accepted",
                "order_id": _M376_BROKER_ORDER_ID,
                "order_type": "market",
                "quantity": _M376_QUANTITY,
                "side": "sell",
                "symbol": "SPY",
                "time_in_force": "day",
            }
        ],
    )
    monkeypatch.setattr(
        cli_module,
        "_build_paper_broker",
        lambda paper_config: fake_broker,
    )
    bars_csv = _write_bars_csv(tmp_path, _bullish_closes())
    run_log = tmp_path / "runs" / "paper_lab" / "cycle.jsonl"

    exit_code, payload = _run_json(
        (
            "etf-sma-cycle-preview",
            "--symbol",
            "SPY",
            "--bars-csv",
            str(bars_csv),
            "--run-log",
            str(run_log),
            "--run-id",
            "spy_etf_sma_cycle_preview",
            "--format",
            "json",
        ),
        capsys,
    )

    assert exit_code == 0
    assert fake_broker.calls == ["get_account", "get_positions", "get_recent_orders"]
    assert fake_broker.recent_order_queries[0].status_filter == "open"
    assert fake_broker.recent_order_queries[0].symbol_filter == "SPY"
    assert fake_broker.submitted_requests == []
    assert payload["decision"] == "blocked"
    assert payload["decision_reason"] == "open_order_present"
    assert payload["open_order_count"] == 1
    assert payload["spy_position_quantity"] == _M376_QUANTITY
    assert "preview_order" not in payload
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False


def test_cli_paper_preview_blocks_when_broker_observation_fails(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    _set_paper_env(monkeypatch)

    def failing_build(paper_config):  # noqa: ANN001
        raise RuntimeError("fake read-only observation unavailable")

    monkeypatch.setattr(cli_module, "_build_paper_broker", failing_build)
    bars_csv = _write_bars_csv(tmp_path, _bullish_closes())
    run_log = tmp_path / "runs" / "paper_lab" / "cycle.jsonl"

    exit_code, payload = _run_json(
        (
            "etf-sma-cycle-preview",
            "--bars-csv",
            str(bars_csv),
            "--run-log",
            str(run_log),
            "--format",
            "json",
        ),
        capsys,
    )

    assert exit_code == 0
    assert payload["decision"] == "blocked"
    assert "broker_observations_unavailable" in payload["blockers"]
    assert "preview_order" not in payload
    assert payload["submitted"] is False


class FakeCycleBroker:
    def __init__(
        self,
        *,
        positions: list[dict[str, object]] | None = None,
        open_orders: list[dict[str, object]] | None = None,
    ) -> None:
        self.positions = positions or []
        self.open_orders = open_orders or []
        self.calls: list[str] = []
        self.recent_order_queries: list[object] = []
        self.submitted_requests: list[object] = []

    def get_account(self) -> dict[str, object]:
        self.calls.append("get_account")
        return {
            "account_id": "paper-account-1",
            "buying_power": Decimal("2000"),
            "cash": Decimal("1000"),
            "currency": "USD",
            "equity": Decimal("1000"),
            "status": "ACTIVE",
        }

    def get_positions(self) -> list[dict[str, object]]:
        self.calls.append("get_positions")
        return list(self.positions)

    def get_recent_orders(self, query) -> list[dict[str, object]]:  # noqa: ANN001
        self.calls.append("get_recent_orders")
        self.recent_order_queries.append(query)
        return list(self.open_orders)

    def submit_order(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("cycle preview must not submit")

    def submit_order_request(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("cycle preview must not submit")


def _preview(
    bars: tuple[Bar, ...],
    observation: EtfSmaCycleBrokerObservation,
):
    return build_etf_sma_cycle_preview(
        bars,
        observation,
        EtfSmaCyclePreviewConfig(
            run_id="spy_etf_sma_cycle_preview",
            bars_source="unit_test",
            bars_input_available=True,
        ),
    )


def _flat_observation(
    *,
    open_order_count: int = 0,
    open_order_symbols: tuple[str, ...] = (),
) -> EtfSmaCycleBrokerObservation:
    return EtfSmaCycleBrokerObservation(
        paper_profile_gate_passed=True,
        account_observation_available=True,
        positions_observation_available=True,
        orders_observation_available=True,
        cash=Decimal("1000"),
        currency="USD",
        position_count=0,
        position_symbols=(),
        open_order_count=open_order_count,
        open_order_symbols=open_order_symbols,
    )


def _spy_position_observation(quantity: str) -> EtfSmaCycleBrokerObservation:
    return EtfSmaCycleBrokerObservation(
        paper_profile_gate_passed=True,
        account_observation_available=True,
        positions_observation_available=True,
        orders_observation_available=True,
        cash=Decimal("1000"),
        currency="USD",
        position_count=1,
        position_symbols=("SPY",),
        spy_position_quantity=Decimal(quantity),
        open_order_count=0,
    )


def _bullish_bars() -> tuple[Bar, ...]:
    return _bars(*_bullish_closes())


def _risk_off_bars() -> tuple[Bar, ...]:
    return _bars(*(200 * ("10",)))


def _bullish_closes() -> tuple[str, ...]:
    return tuple(150 * ("10",) + 50 * ("20",))


def _bars(*closes: str) -> tuple[Bar, ...]:
    return tuple(
        _bar("SPY", _START + timedelta(days=index), close)
        for index, close in enumerate(closes)
    )


def _bar(symbol: str, timestamp: datetime, close: str) -> Bar:
    value = Decimal(close)
    return Bar(
        symbol=symbol,
        timestamp=timestamp,
        open=value,
        high=value,
        low=value,
        close=value,
        volume=Decimal("100"),
    )


def _write_bars_csv(tmp_path, closes: tuple[str, ...]):  # noqa: ANN001
    path = tmp_path / "spy_daily_bars.csv"
    lines = ["date,close\n"]
    for index, close in enumerate(closes):
        date_value = (_START + timedelta(days=index)).date().isoformat()
        lines.append(f"{date_value},{close}\n")
    path.write_text("".join(lines), encoding="utf-8")
    return path


def _set_dev_env(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("APP_PROFILE", "dev")
    for name in (
        "ALPACA_API_KEY",
        "ALPACA_SECRET_KEY",
        "ALPACA_PAPER_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)


def _set_paper_env(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("APP_PROFILE", "paper")
    monkeypatch.setenv("ALPACA_API_KEY", "paper-key-for-test")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "paper-secret-for-test")
    monkeypatch.setenv("ALPACA_PAPER_BASE_URL", "https://paper.example.test")


def _run_json(argv: tuple[str, ...], capsys) -> tuple[int, dict[str, object]]:  # noqa: ANN001
    exit_code = main(argv)
    captured = capsys.readouterr()
    assert captured.err == ""
    return exit_code, json.loads(captured.out.strip())


def _read_jsonl(path) -> list[dict[str, object]]:  # noqa: ANN001
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
