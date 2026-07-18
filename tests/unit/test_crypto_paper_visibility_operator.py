from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
import pytest

from algotrader.config import AlpacaPaperConfig, DEFAULT_ALPACA_PAPER_BASE_URL
from algotrader.errors import ValidationError
from algotrader.execution.crypto_paper_visibility_operator import (
    crypto_visibility_environment_preflight,
    render_crypto_visibility_text,
    run_crypto_paper_visibility_cycle,
)


GENERATED_AT = datetime(2026, 7, 3, 2, tzinfo=UTC)
SENSITIVE_KEY = "paper-key-value-not-for-output"
SENSITIVE_SECRET = "paper-secret-value-not-for-output"


class FakeReadOnlyCryptoAssetsClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def get_all_assets(self) -> list[dict[str, object]]:
        self.calls.append("get_all_assets")
        return [
            {
                "symbol": "ETH/USD",
                "asset_class": "crypto",
                "tradable": True,
                "marginable": False,
                "fractionable": True,
                "status": "active",
                "min_order_size": "0.001",
            },
            {
                "symbol": "BTC/USD",
                "asset_class": "crypto",
                "tradable": True,
                "marginable": False,
                "fractionable": True,
                "status": "active",
                "min_order_size": "0.0001",
                "min_trade_increment": "0.00000001",
                "min_notional": "10.00",
            },
        ]


class FakeSolReadOnlyCryptoAssetsClient(FakeReadOnlyCryptoAssetsClient):
    def get_all_assets(self) -> list[dict[str, object]]:
        return [
            *super().get_all_assets(),
            {
                "symbol": "SOL/USD",
                "asset_class": "crypto",
                "tradable": True,
                "marginable": False,
                "fractionable": True,
                "status": "active",
                "min_order_size": "0.01",
                "min_trade_increment": "0.000001",
                "min_notional": "1.00",
            },
        ]


def test_visibility_operator_uses_apca_aliases_for_read_only_observed_assets(
    tmp_path: Path,
) -> None:
    bars_csv = _write_crypto_bars(tmp_path, symbol="BTC/USD", posture="risk_on")
    fake_client = FakeReadOnlyCryptoAssetsClient()
    factory_configs: list[AlpacaPaperConfig] = []
    env = {
        "APP_PROFILE": "paper",
        "APCA_API_KEY_ID": SENSITIVE_KEY,
        "APCA_API_SECRET_KEY": SENSITIVE_SECRET,
        "ALPACA_PAPER_BASE_URL": DEFAULT_ALPACA_PAPER_BASE_URL,
    }

    def factory(config: AlpacaPaperConfig) -> FakeReadOnlyCryptoAssetsClient:
        factory_configs.append(config)
        return fake_client

    record = run_crypto_paper_visibility_cycle(
        output_root=tmp_path / "out",
        bars_csv=bars_csv,
        timestamp=GENERATED_AT,
        env=env,
        sdk_client_factory=factory,
        write_artifacts=False,
    )
    rendered = render_crypto_visibility_text(record)

    assert fake_client.calls == ["get_all_assets"]
    assert factory_configs[0].alpaca_api_key == SENSITIVE_KEY
    assert factory_configs[0].alpaca_secret_key == SENSITIVE_SECRET
    assert record["broker_read_requested"] is True
    assert record["broker_read_performed"] is True
    assert record["broker_state_mode"] == "alpaca_paper_observed"
    assert record["capability_source"] == "observed"
    assert record["crypto_trading_supported"] is True
    assert record["target_symbol"] == ""
    assert record["target_scoped"] is False
    assert record["eligible_crypto_symbols"] == ["ETHUSD", "BTCUSD"]
    assert record["selected_symbol"] == "BTCUSD"
    assert record["selected_symbol_tradable"] is True
    assert record["selected_symbol_marginable"] is False
    assert record["selected_symbol_fractionable"] is True
    assert record["min_notional"] == "10.00"
    assert record["action_decision"] == "preview_buy/no_submit"
    assert record["no_submit_mode"] is True
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False
    assert record["live_mutation_performed"] is False
    assert "paper-key-value" not in rendered
    assert "target_scoped=false" in rendered
    assert "paper-secret-value" not in rendered

def test_visibility_operator_target_symbol_is_the_sole_preference(
    tmp_path: Path,
) -> None:
    bars_csv = _write_crypto_bars(tmp_path, symbol="SOLUSD", posture="risk_on")
    fake_client = FakeSolReadOnlyCryptoAssetsClient()
    env = {
        "APP_PROFILE": "paper",
        "APCA_API_KEY_ID": SENSITIVE_KEY,
        "APCA_API_SECRET_KEY": SENSITIVE_SECRET,
        "ALPACA_PAPER_BASE_URL": DEFAULT_ALPACA_PAPER_BASE_URL,
    }

    record = run_crypto_paper_visibility_cycle(
        output_root=tmp_path / "out",
        bars_csv=bars_csv,
        timestamp=GENERATED_AT,
        target_symbol="SOLUSD",
        env=env,
        sdk_client_factory=lambda _: fake_client,
        write_artifacts=False,
    )
    rendered = render_crypto_visibility_text(record)

    assert fake_client.calls == ["get_all_assets"]
    assert record["target_symbol"] == "SOLUSD"
    assert record["target_scoped"] is True
    assert record["eligible_crypto_symbols"] == ["ETHUSD", "BTCUSD", "SOLUSD"]
    assert record["selected_symbol"] == "SOLUSD"
    assert record["selected_symbol_tradable"] is True
    assert record["min_order_size"] == "0.01"
    assert "target_symbol=SOLUSD" in rendered


def test_visibility_operator_target_symbol_has_no_fallback(
    tmp_path: Path,
) -> None:
    bars_csv = _write_crypto_bars(tmp_path, symbol="BTCUSD", posture="risk_on")
    fake_client = FakeReadOnlyCryptoAssetsClient()

    record = run_crypto_paper_visibility_cycle(
        output_root=tmp_path / "out",
        bars_csv=bars_csv,
        timestamp=GENERATED_AT,
        target_symbol="SOLUSD",
        env={
            "APP_PROFILE": "paper",
            "APCA_API_KEY_ID": SENSITIVE_KEY,
            "APCA_API_SECRET_KEY": SENSITIVE_SECRET,
            "ALPACA_PAPER_BASE_URL": DEFAULT_ALPACA_PAPER_BASE_URL,
        },
        sdk_client_factory=lambda _: fake_client,
        write_artifacts=False,
    )

    assert fake_client.calls == ["get_all_assets"]
    assert record["target_symbol"] == "SOLUSD"
    assert record["target_scoped"] is True
    assert record["selected_symbol"] == ""
    assert record["crypto_trading_supported"] is False
    assert "no_eligible_crypto_symbols_observed" in record["blockers"]


@pytest.mark.parametrize(
    "target_symbol",
    ("btcusd", "DOGEUSD", "BTC/USD", " BTCUSD", "BTCUSD "),
)
def test_visibility_operator_rejects_invalid_target_before_sdk_factory(
    tmp_path: Path,
    target_symbol: str,
) -> None:
    factory_called = False

    def factory(config: AlpacaPaperConfig) -> FakeReadOnlyCryptoAssetsClient:
        nonlocal factory_called
        factory_called = True
        return FakeReadOnlyCryptoAssetsClient()

    with pytest.raises(ValidationError, match="target_symbol must be exactly"):
        run_crypto_paper_visibility_cycle(
            output_root=tmp_path / "out",
            bars_csv=tmp_path / "unused.csv",
            target_symbol=target_symbol,
            env={"APP_PROFILE": "paper"},
            sdk_client_factory=factory,
            write_artifacts=False,
        )

    assert factory_called is False



def test_visibility_operator_without_paper_shell_reports_not_observed(
    tmp_path: Path,
) -> None:
    bars_csv = _write_crypto_bars(tmp_path, symbol="BTCUSD", posture="risk_on")

    record = run_crypto_paper_visibility_cycle(
        output_root=tmp_path / "out",
        bars_csv=bars_csv,
        timestamp=GENERATED_AT,
        env={"APP_PROFILE": "dev"},
        sdk_client_factory=lambda _: (_ for _ in ()).throw(AssertionError("no sdk")),
        write_artifacts=False,
    )

    assert record["operator_preflight"]["APP_PROFILE_is_paper"] is False
    assert record["broker_read_requested"] is False
    assert record["broker_read_performed"] is False
    assert record["capability_source"] == "not_observed"
    assert record["readiness_status"] == "readiness_blocked_capability_not_observed"
    assert "capability_not_observed" in record["blockers"]
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False


def test_visibility_operator_live_endpoint_blocks_before_sdk_factory(
    tmp_path: Path,
) -> None:
    bars_csv = _write_crypto_bars(tmp_path, symbol="BTCUSD", posture="risk_on")
    factory_called = False
    env = {
        "APP_PROFILE": "paper",
        "ALPACA_API_KEY": SENSITIVE_KEY,
        "ALPACA_SECRET_KEY": SENSITIVE_SECRET,
        "ALPACA_PAPER_BASE_URL": "https://api.alpaca.markets",
    }

    def factory(config: AlpacaPaperConfig) -> FakeReadOnlyCryptoAssetsClient:
        nonlocal factory_called
        factory_called = True
        return FakeReadOnlyCryptoAssetsClient()

    record = run_crypto_paper_visibility_cycle(
        output_root=tmp_path / "out",
        bars_csv=bars_csv,
        timestamp=GENERATED_AT,
        env=env,
        sdk_client_factory=factory,
        write_artifacts=False,
    )

    assert factory_called is False
    assert record["operator_preflight"]["live_endpoint_indicator"] is True
    assert record["broker_read_requested"] is False
    assert record["broker_read_performed"] is False
    assert record["readiness_status"] == "readiness_blocked_live_endpoint_indicator"
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False


def test_visibility_preflight_reports_booleans_only_for_credentials() -> None:
    preflight = crypto_visibility_environment_preflight(
        {
            "APP_PROFILE": "paper",
            "ALPACA_API_KEY": SENSITIVE_KEY,
            "ALPACA_SECRET_KEY": SENSITIVE_SECRET,
            "ALPACA_PAPER_BASE_URL": DEFAULT_ALPACA_PAPER_BASE_URL,
        }
    )

    assert preflight["APP_PROFILE_is_paper"] is True
    assert preflight["ALPACA_API_KEY_present"] is True
    assert preflight["ALPACA_SECRET_KEY_present"] is True
    assert preflight["paper_credentials_present"] is True
    assert all(isinstance(value, bool) for value in preflight.values())


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
