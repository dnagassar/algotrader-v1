from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.crypto_paper_supervisor import (
    CRYPTO_PAPER_SUPERVISOR_SAFETY_LABELS,
    CryptoPaperSupervisorConfig,
    discover_crypto_paper_capability,
    run_crypto_paper_supervisor,
)


GENERATED_AT = datetime(2026, 7, 3, 2, tzinfo=UTC)


def test_crypto_capability_receipt_selects_preferred_observed_symbol() -> None:
    broker = FakeCryptoAssetBroker(
        assets=(
            CryptoAsset(symbol="ETH/USD"),
            CryptoAsset(
                symbol="BTC/USD",
                min_order_size="0.0001",
                min_trade_increment="0.00000001",
                min_notional="10.00",
            ),
        )
    )

    receipt = discover_crypto_paper_capability(broker=broker)

    assert broker.calls == ["list_assets"]
    assert receipt.universe == "crypto"
    assert receipt.asset_class == "crypto"
    assert receipt.broker_read_performed is True
    assert receipt.broker_state_mode == "alpaca_paper_observed"
    assert receipt.crypto_trading_supported is True
    assert receipt.eligible_crypto_symbols == ("ETHUSD", "BTCUSD")
    assert receipt.selected_symbol == "BTCUSD"
    assert receipt.min_order_size == "0.0001"
    assert receipt.min_trade_increment == "0.00000001"
    assert receipt.min_notional == "10.00"
    assert receipt.paper_only_mode is True
    assert receipt.live_endpoint_indicator is False
    assert receipt.capability_source == "observed"
    assert receipt.blockers == ()


def test_crypto_capability_not_observed_does_not_select_symbol() -> None:
    receipt = discover_crypto_paper_capability()

    assert receipt.broker_read_performed is False
    assert receipt.crypto_trading_supported is False
    assert receipt.eligible_crypto_symbols == ()
    assert receipt.selected_symbol == ""
    assert receipt.capability_source == "not_observed"
    assert receipt.blockers == ("crypto_capability_not_observed",)


def test_crypto_capability_live_indicator_blocks_before_broker_read() -> None:
    broker = FakeCryptoAssetBroker(assets=(CryptoAsset(symbol="BTCUSD"),))

    receipt = discover_crypto_paper_capability(
        broker=broker,
        env={"APP_PROFILE": "live"},
    )

    assert broker.calls == []
    assert receipt.broker_read_performed is False
    assert receipt.broker_state_mode == "blocked_live_endpoint_indicator"
    assert receipt.crypto_trading_supported is False
    assert receipt.live_endpoint_indicator is True
    assert receipt.capability_source == "not_observed"
    assert receipt.blockers == ("live_endpoint_indicator",)


def test_crypto_no_submit_supervisor_receipt_is_preview_only_and_non_mutating(
    tmp_path: Path,
) -> None:
    bars_csv = _write_crypto_bars(tmp_path, symbol="BTC/USD", posture="risk_on")
    broker = FakeCryptoAssetBroker(assets=(CryptoAsset(symbol="BTC/USD"),))

    record = run_crypto_paper_supervisor(
        CryptoPaperSupervisorConfig(
            output_root=tmp_path / "out",
            bars_csv=bars_csv,
        ),
        broker=broker,
        timestamp=GENERATED_AT,
    )

    assert broker.calls == ["list_assets"]
    assert record["universe"] == "crypto"
    assert record["asset_class"] == "crypto"
    assert record["selected_symbol"] == "BTCUSD"
    assert record["data_freshness_status"] == "current_for_24_7_crypto_lab"
    assert record["broker_state_mode"] == "alpaca_paper_observed"
    assert record["broker_read_performed"] is True
    assert record["crypto_trading_supported"] is True
    assert record["strategy_id"] == "crypto_sma_20_50_training_wheel_preview"
    assert record["strategy_posture"] == "risk_on"
    assert record["strategy_adapter_mode"] == "preview_only"
    assert record["strategy_adapter_resolution_status"] == "resolved"
    assert record["strategy_adapter_paper_mutation_allowed"] is False
    assert record["paper_mutation_allowed"] is False
    assert record["submit_allowed"] is False
    assert record["action_decision"] == "preview_buy/no_submit"
    assert record["no_submit_mode"] is True
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False
    assert record["live_mutation_performed"] is False
    assert record["readiness_status"] == "readiness_blocked_crypto_preview_only_no_submit"
    assert "crypto_preview_only_no_submit" in record["blockers"]
    assert record["final_operator_action"] == "observe_crypto_preview_no_submit"
    assert record["safety_labels"] == list(CRYPTO_PAPER_SUPERVISOR_SAFETY_LABELS)
    assert Path(record["artifact_paths"]["latest_status"]).is_file()
    assert Path(record["artifact_paths"]["supervisor_receipt"]).is_file()


def test_stale_crypto_data_blocks_supervisor_readiness(tmp_path: Path) -> None:
    bars_csv = _write_crypto_bars(
        tmp_path,
        symbol="BTCUSD",
        posture="risk_on",
        latest_at=GENERATED_AT - timedelta(hours=6),
    )

    record = run_crypto_paper_supervisor(
        CryptoPaperSupervisorConfig(
            output_root=tmp_path / "out",
            bars_csv=bars_csv,
        ),
        assets=(CryptoAsset(symbol="BTCUSD"),),
        timestamp=GENERATED_AT,
        write_artifacts=False,
    )

    assert record["data_freshness_status"] == "stale_crypto_data_preview_only"
    assert record["readiness_status"] == "readiness_blocked_stale_crypto_data"
    assert record["action_decision"] == "block/stale_crypto_data"
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False
    assert record["live_mutation_performed"] is False


def test_unsupported_crypto_symbol_blocks_at_preview_adapter(tmp_path: Path) -> None:
    bars_csv = _write_crypto_bars(tmp_path, symbol="DOGEUSD", posture="risk_on")

    record = run_crypto_paper_supervisor(
        CryptoPaperSupervisorConfig(
            output_root=tmp_path / "out",
            bars_csv=bars_csv,
            preferred_symbols=("DOGEUSD",),
        ),
        assets=(CryptoAsset(symbol="DOGEUSD"),),
        timestamp=GENERATED_AT,
        write_artifacts=False,
    )

    assert record["selected_symbol"] == "DOGEUSD"
    assert record["crypto_trading_supported"] is True
    assert record["strategy_adapter_resolution_status"] == "blocked"
    assert record["strategy_adapter_reason"] == "strategy_adapter_unsupported_symbol"
    assert record["readiness_status"] == "readiness_blocked_strategy_adapter"
    assert "strategy_adapter_unsupported_symbol" in record["blockers"]
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False


def test_crypto_supervisor_seed_lane_rejects_disabling_no_submit(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError, match="requires no_submit=True"):
        CryptoPaperSupervisorConfig(
            output_root=tmp_path / "out",
            bars_csv=tmp_path / "bars.csv",
            no_submit=False,
        )


@dataclass(frozen=True)
class CryptoAsset:
    symbol: str
    asset_class: str = "crypto"
    tradable: bool = True
    status: str = "active"
    min_order_size: str = ""
    min_trade_increment: str = ""
    min_order_increment: str = ""
    min_notional: str = ""


class FakeCryptoAssetBroker:
    def __init__(self, *, assets: tuple[CryptoAsset, ...]) -> None:
        self.assets = assets
        self.calls: list[str] = []

    def list_assets(self) -> tuple[CryptoAsset, ...]:
        self.calls.append("list_assets")
        return self.assets


def _write_crypto_bars(
    tmp_path: Path,
    *,
    symbol: str,
    posture: str,
    latest_at: datetime = GENERATED_AT,
) -> Path:
    path = tmp_path / f"{symbol.replace('/', '')}_{posture}.csv"
    first = latest_at - timedelta(hours=59)
    rows = ["timestamp,symbol,open,high,low,close,volume"]
    for index in range(60):
        close = Decimal("100") + Decimal(index)
        if posture == "risk_off":
            close = Decimal("300") - Decimal(index)
        timestamp = first + timedelta(hours=index)
        rows.append(
            ",".join(
                [
                    timestamp.isoformat(),
                    symbol,
                    str(close),
                    str(close),
                    str(close),
                    str(close),
                    "1",
                ]
            )
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    return path
