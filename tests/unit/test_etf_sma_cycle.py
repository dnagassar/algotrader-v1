from __future__ import annotations

import ast
import json
import socket
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import algotrader.cli as cli_module
from algotrader.cli import main
from algotrader.core.types import Bar
from algotrader.execution.etf_sma_cycle import (
    EtfSmaCycleBrokerState,
    EtfSmaCycleConfig,
    EtfSmaCycleOpenOrder,
    EtfSmaCyclePosition,
    build_etf_sma_cycle,
    build_etf_sma_cycle_from_offline_inputs,
)


_START = datetime(2025, 1, 1, tzinfo=UTC)
_M376_CLIENT_ORDER_ID = "paper-order-close-m376_spy_paper_close_submit"
_M376_BROKER_ORDER_ID = "dbb32dd3-58bf-49ea-b9b1-9aa44e85002d"
_M376_QUANTITY = "0.033172072"


def test_m376_open_spy_order_input_blocks_without_preview(tmp_path) -> None:  # noqa: ANN001
    reconciliation_log = _write_jsonl(
        tmp_path / "m381_m376_spy_close_order_reconciliation.jsonl",
        _m376_nonterminal_reconciliation_record(),
    )
    bars_csv = _write_bars_csv(tmp_path, _bullish_closes())

    payload = build_etf_sma_cycle_from_offline_inputs(
        EtfSmaCycleConfig(
            run_id="m382_unit_cycle",
            symbol="SPY",
            market_data_csv=bars_csv,
            order_reconciliation_log=reconciliation_log,
        )
    )

    assert payload["decision"] == "blocked/open_order_present"
    assert payload["decision_reason"] == "open_order_present"
    assert "m376_order_nonterminal" in payload["blockers"]
    assert "open_order_present" in payload["blockers"]
    assert payload["preview_order"] is None
    assert payload["m376_order_summary"]["state"] == "nonterminal_open"
    assert payload["m376_order_summary"]["client_order_id"] == _M376_CLIENT_ORDER_ID
    assert payload["next_allowed_action"] == "offline_work_or_read_only_reconciliation"
    assert "spy_submit_until_m376_terminal" in payload["next_forbidden_action"]
    _assert_never_mutates(payload)


def test_risk_on_no_spy_position_produces_buy_preview() -> None:
    payload = _payload(_bullish_bars(), _flat_state())

    assert payload["sma_posture"] == "risk_on"
    assert payload["decision"] == "buy_preview"
    assert payload["preview_order"] == {
        "asset_class": "equity",
        "symbol": "SPY",
        "side": "buy",
        "order_type": "market",
        "time_in_force": "day",
        "notional": "25",
        "preview_only": True,
    }
    _assert_never_mutates(payload)


def test_risk_on_spy_position_produces_hold_noop() -> None:
    payload = _payload(_bullish_bars(), _spy_position_state())

    assert payload["sma_posture"] == "risk_on"
    assert payload["decision"] == "hold/noop"
    assert payload["decision_reason"] == "risk_on_existing_position"
    assert payload["preview_order"] is None


def test_risk_off_spy_position_produces_sell_preview() -> None:
    payload = _payload(_risk_off_bars(), _spy_position_state())

    assert payload["sma_posture"] == "risk_off"
    assert payload["decision"] == "sell_preview"
    assert payload["preview_order"] == {
        "asset_class": "equity",
        "symbol": "SPY",
        "side": "sell",
        "order_type": "market",
        "time_in_force": "day",
        "quantity": _M376_QUANTITY,
        "preview_only": True,
    }
    _assert_never_mutates(payload)


def test_risk_off_no_spy_position_produces_hold_noop() -> None:
    payload = _payload(_risk_off_bars(), _flat_state())

    assert payload["sma_posture"] == "risk_off"
    assert payload["decision"] == "hold/noop"
    assert payload["decision_reason"] == "risk_off_no_position"
    assert payload["preview_order"] is None


def test_insufficient_history_below_required_bars() -> None:
    payload = _payload(_bars(*(199 * ("10",))), _flat_state())

    assert payload["sma_config"] == {
        "fast_window": 50,
        "slow_window": 200,
        "required_bars": 200,
    }
    assert payload["sma_posture"] == "insufficient_history"
    assert payload["decision"] == "insufficient_history"
    assert payload["preview_order"] is None


def test_unexpected_non_spy_position_blocks() -> None:
    payload = _payload(
        _bullish_bars(),
        EtfSmaCycleBrokerState(
            source="unit",
            positions=(EtfSmaCyclePosition(symbol="MSFT", quantity="1"),),
            open_order_count=0,
        ),
    )

    assert payload["decision"] == "blocked/unexpected_non_spy_position"
    assert payload["blockers"] == ["unexpected_non_spy_position"]
    assert payload["preview_order"] is None


def test_safety_flags_are_always_false_for_outputs() -> None:
    payloads = (
        _payload(_bullish_bars(), _flat_state()),
        _payload(_bullish_bars(), _spy_position_state()),
        _payload(_risk_off_bars(), _spy_position_state()),
        _payload(_bullish_bars(), _m376_open_order_state()),
    )

    for payload in payloads:
        _assert_never_mutates(payload)


def test_cli_etf_sma_cycle_works_without_credentials_or_network(
    monkeypatch,
    capsys,
    tmp_path,
) -> None:
    for name in (
        "APP_PROFILE",
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "ALPACA_PAPER_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)

    def forbidden_config(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("offline cycle command must not load runtime config")

    def forbidden_broker(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("offline cycle command must not build a broker")

    def forbidden_socket(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("offline cycle command must not open sockets")

    monkeypatch.setattr(cli_module, "_load_runtime_config", forbidden_config)
    monkeypatch.setattr(cli_module, "_build_paper_broker", forbidden_broker)
    monkeypatch.setattr(socket, "socket", forbidden_socket)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)

    bars_csv = _write_bars_csv(tmp_path, _bullish_closes())
    run_log = tmp_path / "m382_cycle.jsonl"

    exit_code = main(
        (
            "etf-sma-cycle",
            "--symbol",
            "SPY",
            "--run-id",
            "m382_cli_unit",
            "--run-log",
            str(run_log),
            "--market-data-csv",
            str(bars_csv),
            "--position-qty",
            "0",
            "--open-order-count",
            "0",
            "--format",
            "json",
        )
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    records = _read_jsonl(run_log)

    assert exit_code == 0
    assert captured.err == ""
    assert payload["decision"] == "buy_preview"
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is False
    assert len(records) == 1
    assert records[0] == payload


def test_new_cycle_runtime_has_no_broker_sdk_or_network_imports() -> None:
    path = Path("src/algotrader/execution/etf_sma_cycle.py")
    modules = _imported_modules(path)

    assert not any(
        module == forbidden or module.startswith(f"{forbidden}.")
        for module in modules
        for forbidden in (
            "alpaca",
            "alpaca_trade_api",
            "httpx",
            "requests",
            "socket",
            "urllib",
        )
    )


def test_research_and_signal_layers_do_not_import_cycle_execution_module() -> None:
    for package in (Path("src/algotrader/research"), Path("src/algotrader/signals")):
        for path in package.rglob("*.py"):
            modules = _imported_modules(path)
            assert "algotrader.execution.etf_sma_cycle" not in modules


def test_m376_ids_and_qty_are_not_runtime_defaults() -> None:
    runtime_text = Path("src/algotrader/execution/etf_sma_cycle.py").read_text(
        encoding="utf-8"
    )

    assert _M376_CLIENT_ORDER_ID not in runtime_text
    assert _M376_BROKER_ORDER_ID not in runtime_text
    assert _M376_QUANTITY not in runtime_text


def _payload(
    bars: tuple[Bar, ...],
    state: EtfSmaCycleBrokerState,
) -> dict[str, object]:
    return build_etf_sma_cycle(
        bars,
        state,
        EtfSmaCycleConfig(
            run_id="m382_unit_cycle",
            symbol="SPY",
            bars_source="unit_test",
            bars_input_available=True,
        ),
    )


def _flat_state() -> EtfSmaCycleBrokerState:
    return EtfSmaCycleBrokerState(
        source="unit",
        account_observation_available=True,
        cash=Decimal("1000"),
        currency="USD",
        positions=(),
        open_orders=(),
        open_order_count=0,
    )


def _spy_position_state() -> EtfSmaCycleBrokerState:
    return EtfSmaCycleBrokerState(
        source="unit",
        account_observation_available=True,
        cash=Decimal("1000"),
        currency="USD",
        positions=(
            EtfSmaCyclePosition(symbol="SPY", quantity=_M376_QUANTITY),
        ),
        open_orders=(),
        open_order_count=0,
    )


def _m376_open_order_state() -> EtfSmaCycleBrokerState:
    return EtfSmaCycleBrokerState(
        source="unit",
        account_observation_available=True,
        cash=Decimal("1000"),
        currency="USD",
        positions=(EtfSmaCyclePosition(symbol="SPY", quantity=_M376_QUANTITY),),
        open_orders=(
            EtfSmaCycleOpenOrder(
                symbol="SPY",
                client_order_id=_M376_CLIENT_ORDER_ID,
                broker_order_id=_M376_BROKER_ORDER_ID,
                status="accepted",
                side="sell",
                quantity=_M376_QUANTITY,
                filled_quantity="0",
            ),
        ),
        open_order_count=1,
        source_blockers=("m376_order_nonterminal",),
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


def _write_jsonl(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _m376_nonterminal_reconciliation_record() -> dict[str, object]:
    return {
        "run_id": "m381_m376_spy_close_order_reconciliation",
        "symbol": "SPY",
        "client_order_id": _M376_CLIENT_ORDER_ID,
        "broker_order_id": _M376_BROKER_ORDER_ID,
        "expected_side": "sell",
        "expected_qty": _M376_QUANTITY,
        "observed_status": "accepted",
        "observed_symbol": "SPY",
        "observed_side": "sell",
        "observed_qty": _M376_QUANTITY,
        "observed_filled_qty": "0",
        "observed_remaining_qty": _M376_QUANTITY,
        "observed_submitted_at": "2026-06-03T23:57:14.030265+00:00",
        "exact_order_found": True,
        "exact_order_source": "open",
        "terminal_state": "nonterminal",
        "terminal_reason": "status_accepted_active",
        "reconciliation_decision": "m376_nonterminal_open",
        "next_spy_submit_blocked": True,
        "reason": "status_accepted_active",
        "spy_position_qty": _M376_QUANTITY,
        "open_order_count": 1,
        "open_order_symbols": ["SPY"],
        "open_order_client_order_ids": [_M376_CLIENT_ORDER_ID],
        "open_order_broker_order_ids": [_M376_BROKER_ORDER_ID],
        "open_order_statuses": ["accepted"],
        "open_order_sides": ["sell"],
        "open_order_quantities": [_M376_QUANTITY],
        "open_order_filled_quantities": ["0"],
        "blockers": ["m376_order_nonterminal", "open_order_present"],
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "live_authorized": False,
        "account_observation_available": True,
        "positions_observation_available": True,
        "orders_observation_available": True,
        "labels": ["paper_lab_only", "not_live_authorized", "profit_claim=none"],
    }


def _assert_never_mutates(payload: dict[str, object]) -> None:
    assert payload["submitted"] is False
    assert payload["mutated"] is False
    assert payload["broker_action_performed"] is False
    assert payload["broker_mutation_allowed"] is False
    assert payload["live_authorized"] is False
    assert payload["network_access_attempted"] is False
    assert payload["credential_access_attempted"] is False


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            level_prefix = "." * node.level
            modules.add(f"{level_prefix}{node.module}")
    return modules
