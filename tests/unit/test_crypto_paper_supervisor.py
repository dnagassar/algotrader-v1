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
                marginable=False,
                fractionable=True,
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
    assert receipt.selected_symbol_tradable is True
    assert receipt.selected_symbol_marginable is False
    assert receipt.selected_symbol_fractionable is True
    assert receipt.min_order_size == "0.0001"
    assert receipt.min_trade_increment == "0.00000001"
    assert receipt.min_notional == "10.00"
    assert receipt.paper_only_mode is True
    assert receipt.live_endpoint_indicator is False
    assert receipt.capability_source == "observed"
    assert receipt.blockers == ()


def test_crypto_capability_merges_allowlisted_model_attrs_missing_from_dump() -> None:
    asset = FakePartialDumpCryptoAsset(
        model_dump_fields=(
            "symbol",
            "asset_class",
            "tradable",
            "fractionable",
            "status",
            "min_order_size",
            "min_trade_increment",
        ),
        symbol="BTC/USD",
        asset_class="AssetClass.CRYPTO",
        tradable=True,
        fractionable=True,
        status="AssetStatus.ACTIVE",
        min_order_size="0.000016268",
        min_trade_increment="1E-9",
        min_notional="10.00",
        api_key="must-not-be-serialized",
    )

    receipt = discover_crypto_paper_capability(
        assets=(asset,),
        capability_source="observed",
    )

    assert receipt.capability_source == "observed"
    assert receipt.selected_symbol == "BTCUSD"
    assert receipt.selected_symbol_tradable is True
    assert receipt.selected_symbol_fractionable is True
    assert receipt.min_notional == "10.00"
    assert receipt.min_order_size == "0.000016268"
    assert Decimal(receipt.min_trade_increment) == Decimal("0.000000001")
    assert "api_key" not in receipt.to_dict()


def test_crypto_capability_does_not_default_missing_min_notional() -> None:
    receipt = discover_crypto_paper_capability(
        assets=(
            CryptoAsset(
                symbol="BTC/USD",
                fractionable=True,
                min_order_size="0.000016268",
                min_trade_increment="1E-9",
            ),
        ),
        capability_source="observed",
    )

    assert receipt.capability_source == "observed"
    assert receipt.selected_symbol == "BTCUSD"
    assert receipt.min_order_size == "0.000016268"
    assert Decimal(receipt.min_trade_increment) == Decimal("0.000000001")
    assert receipt.min_notional == ""


def test_crypto_capability_not_observed_does_not_select_symbol() -> None:
    receipt = discover_crypto_paper_capability()

    assert receipt.broker_read_performed is False
    assert receipt.crypto_trading_supported is False
    assert receipt.eligible_crypto_symbols == ()
    assert receipt.selected_symbol == ""
    assert receipt.capability_source == "not_observed"
    assert receipt.blockers == ("crypto_capability_not_observed",)


def test_crypto_capability_handles_enum_like_asset_class_values() -> None:
    receipt = discover_crypto_paper_capability(
        assets=(
            {
                "symbol": "BTC/USD",
                "asset_class": EnumLikeValue("crypto"),
                "tradable": True,
                "status": EnumLikeValue("active"),
            },
        ),
        capability_source="observed",
    )

    assert receipt.capability_source == "observed"
    assert receipt.crypto_trading_supported is True
    assert receipt.selected_symbol == "BTCUSD"


def test_crypto_capability_blocks_when_only_non_preferred_symbol_is_observed() -> None:
    receipt = discover_crypto_paper_capability(
        assets=(CryptoAsset(symbol="DOGE/USD"),),
        capability_source="observed",
    )

    assert receipt.capability_source == "observed"
    assert receipt.crypto_trading_supported is False
    assert receipt.eligible_crypto_symbols == ("DOGEUSD",)
    assert receipt.selected_symbol == ""
    assert receipt.selected_symbol_tradable is False
    assert receipt.blockers == ("no_eligible_crypto_symbols_observed",)


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
    assert record["capability_source"] == "observed"
    assert record["crypto_trading_supported"] is True
    assert record["selected_symbol_tradable"] is True
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


def test_capability_not_observed_blocks_visibility_readiness(tmp_path: Path) -> None:
    bars_csv = _write_crypto_bars(tmp_path, symbol="BTCUSD", posture="risk_on")

    record = run_crypto_paper_supervisor(
        CryptoPaperSupervisorConfig(
            output_root=tmp_path / "out",
            bars_csv=bars_csv,
        ),
        timestamp=GENERATED_AT,
        write_artifacts=False,
    )

    assert record["broker_read_performed"] is False
    assert record["capability_source"] == "not_observed"
    assert record["readiness_status"] == "readiness_blocked_capability_not_observed"
    assert "capability_not_observed" in record["blockers"]
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False


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
    assert record["readiness_status"] == "readiness_blocked_unsupported_crypto_capability"
    assert "unsupported_crypto_capability" in record["blockers"]
    assert "strategy_adapter_unsupported_symbol" in record["blockers"]
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False


def test_crypto_no_submit_blocks_mutation_readiness_even_without_buy(
    tmp_path: Path,
) -> None:
    bars_csv = _write_crypto_bars(tmp_path, symbol="BTCUSD", posture="risk_off")

    record = run_crypto_paper_supervisor(
        CryptoPaperSupervisorConfig(
            output_root=tmp_path / "out",
            bars_csv=bars_csv,
        ),
        assets=(CryptoAsset(symbol="BTCUSD"),),
        timestamp=GENERATED_AT,
        write_artifacts=False,
    )

    assert record["strategy_posture"] == "risk_off"
    assert record["strategy_intended_action"] == "hold"
    assert record["readiness_status"] == "readiness_blocked_crypto_preview_only_no_submit"
    assert record["action_decision"] == "observe/no_action"
    assert "crypto_preview_only_no_submit" in record["blockers"]
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
    marginable: bool | None = None
    fractionable: bool | None = None
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


class FakePartialDumpCryptoAsset:
    def __init__(
        self,
        *,
        model_dump_fields: tuple[str, ...],
        **fields: object,
    ) -> None:
        self._fields = dict(fields)
        self._model_dump_fields = model_dump_fields
        for key, value in fields.items():
            setattr(self, key, value)

    def model_dump(self, *args: object, **kwargs: object) -> dict[str, object]:
        return {
            key: self._fields[key]
            for key in self._model_dump_fields
            if key in self._fields
        }

    @property
    def model_fields(self) -> object:
        raise AssertionError("model_fields must not be read from asset instances")


@dataclass(frozen=True)
class EnumLikeValue:
    value: str


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
