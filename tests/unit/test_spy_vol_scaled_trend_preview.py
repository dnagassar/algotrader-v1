from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
import json
from pathlib import Path

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL
from algotrader.core.types import Bar
from algotrader.execution.paper_autopilot_loop import (
    PaperAutopilotLoopConfig,
    run_paper_autopilot_loop,
)
from algotrader.orchestration.strategy_adapter_registry import (
    DEFAULT_STRATEGY_ADAPTER_REGISTRY,
    SMA_TRAINING_WHEEL_PAPER_MUTATION_ADAPTER_ID,
    SPY_VOL_SCALED_TREND_PREVIEW_ADAPTER_ID,
    resolve_strategy_adapter,
)
from algotrader.orchestration.strategy_router import (
    SMA_TRAINING_WHEEL_STRATEGY_ID,
    SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_FAMILY,
    SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_ID,
    route_strategy_signals,
    strategy_signal_from_spy_vol_scaled_trend_result,
)
from algotrader.signals.spy_vol_scaled_trend import (
    SPY_VOL_SCALED_TREND_STRATEGY_ID,
    SPYVolScaledTrendSignalConfig,
    evaluate_spy_vol_scaled_trend_signal,
)


AS_OF = datetime(2026, 8, 8, tzinfo=UTC)
GENERATED_AT = "2026-06-26T14:00:00+00:00"
EXPECTED_ACCOUNT_ID = "expected-paper-account-id"


def test_vol_scaled_trend_emits_preview_strategy_signal_contract() -> None:
    result = evaluate_spy_vol_scaled_trend_signal(
        _bars(AS_OF, posture="risk_on"),
        SPYVolScaledTrendSignalConfig(as_of=AS_OF),
    )
    signal = strategy_signal_from_spy_vol_scaled_trend_result(result)
    receipt = route_strategy_signals((signal,))

    assert result.strategy_id == SPY_VOL_SCALED_TREND_STRATEGY_ID
    assert result.strategy_family == SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_FAMILY
    assert result.posture == "trend_on_full_exposure"
    assert result.target_exposure == Decimal("1")
    assert result.submit_allowed is False
    assert result.broker_action_performed is False
    assert signal.strategy_id == SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_ID
    assert signal.strategy_family == SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_FAMILY
    assert signal.symbol == "SPY"
    assert signal.asset_class == "equity"
    assert signal.promotion_status == "paper_preview_candidate"
    assert signal.intended_action == "buy"
    assert "paper_preview_quarantine" in signal.labels
    assert "not_live_authorized" in signal.labels
    assert receipt.paper_mutation_allowed is False
    assert receipt.selected_signal is None
    assert receipt.blocked_signal_ids == (SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_ID,)


def test_default_registry_resolves_vol_scaled_only_to_preview_mode() -> None:
    signal = strategy_signal_from_spy_vol_scaled_trend_result(
        evaluate_spy_vol_scaled_trend_signal(
            _bars(AS_OF, posture="risk_on"),
            SPYVolScaledTrendSignalConfig(as_of=AS_OF),
        )
    )
    preview_resolution = resolve_strategy_adapter(signal, adapter_mode="preview_only")
    mutation_resolution = resolve_strategy_adapter(signal, adapter_mode="paper_mutation")
    mutation_registrations = [
        registration
        for registration in DEFAULT_STRATEGY_ADAPTER_REGISTRY
        if registration.enabled and registration.adapter_mode == "paper_mutation"
    ]

    assert preview_resolution.resolution_status == "resolved"
    assert preview_resolution.adapter_id == SPY_VOL_SCALED_TREND_PREVIEW_ADAPTER_ID
    assert preview_resolution.adapter_mode == "preview_only"
    assert preview_resolution.paper_mutation_allowed is False
    assert mutation_resolution.resolution_status == "blocked"
    assert mutation_resolution.reason == "strategy_adapter_mode_mismatch"
    assert mutation_resolution.paper_mutation_allowed is False
    assert [item.strategy_id for item in mutation_registrations] == [
        SMA_TRAINING_WHEEL_STRATEGY_ID
    ]
    assert mutation_registrations[0].adapter_id == (
        SMA_TRAINING_WHEEL_PAPER_MUTATION_ADAPTER_ID
    )


def test_supervisor_receipt_shows_preview_disagreement_without_mutation(
    tmp_path: Path,
) -> None:
    bars_csv = _write_bars_csv(tmp_path, posture="risk_on")
    broker = _FakePreviewBroker(
        positions=({"symbol": "SPY", "qty": Decimal("0.05"), "market_value": "30"},)
    )

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(output_root=tmp_path / "out", bars_csv=bars_csv),
        env=_paper_env(),
        broker_client_factory=lambda _config: broker,
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
        update_history=False,
    )
    receipt_path = Path(record["artifact_paths"]["supervisor_receipt"])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8").splitlines()[-1])

    assert record["execution_plan_action"] == "hold"
    assert record["preview_action_decision"] == "hold/noop"
    assert record["paper_submit_performed"] is False
    assert record["broker_mutation_performed"] is False
    assert broker.submitted_requests == []
    assert [
        state["strategy_id"]
        for state in receipt["strategy_signal_states"]
        if state["strategy_id"]
        in {
            SMA_TRAINING_WHEEL_STRATEGY_ID,
            SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_ID,
        }
    ] == [
        SMA_TRAINING_WHEEL_STRATEGY_ID,
        SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_ID,
    ]
    assert receipt["strategy_preview_states"][0]["strategy_id"] == (
        SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_ID
    )
    assert receipt["strategy_preview_states"][0]["promotion_status"] == (
        "paper_preview_candidate"
    )
    assert receipt["strategy_preview_adapter_resolutions"][0]["adapter_mode"] == (
        "preview_only"
    )
    assert (
        receipt["strategy_preview_adapter_resolutions"][0]["paper_mutation_allowed"]
        is False
    )
    assert receipt["strategy_action_disagreements"] == [
        {
            "strategy_id": SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_ID,
            "promotion_status": "paper_preview_candidate",
            "preview_intended_action": "buy",
            "paper_execution_plan_action": "hold",
            "selected_strategy_id": SMA_TRAINING_WHEEL_STRATEGY_ID,
            "selected_strategy_intended_action": "buy",
            "paper_mutation_allowed": False,
            "reason": "preview_candidate_disagrees_with_paper_execution_plan",
        }
    ]


def test_supervisor_receipt_shows_preview_no_action_state(tmp_path: Path) -> None:
    bars_csv = _write_short_bars_csv(tmp_path)

    record = run_paper_autopilot_loop(
        PaperAutopilotLoopConfig(output_root=tmp_path / "out", bars_csv=bars_csv),
        env={},
        broker_client_factory=_forbidden_factory,
        daily_lab_runner=_fake_daily_lab,
        timestamp=GENERATED_AT,
        update_history=False,
    )

    assert record["broker_mutation_performed"] is False
    assert record["paper_submit_performed"] is False
    assert record["strategy_preview_states"][0]["strategy_id"] == (
        SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_ID
    )
    assert record["strategy_preview_states"][0]["signal_state"] == (
        "insufficient_evidence"
    )
    assert record["strategy_preview_states"][0]["intended_action"] == "no_action"
    assert record["strategy_preview_adapter_resolutions"][0]["adapter_mode"] == (
        "preview_only"
    )
    assert (
        record["strategy_preview_adapter_resolutions"][0]["paper_mutation_allowed"]
        is False
    )


class _FakePreviewBroker:
    def __init__(
        self,
        *,
        positions: tuple[dict[str, object], ...] = (),
    ) -> None:
        self.positions = positions
        self.submitted_requests: list[object] = []

    def get_account(self) -> dict[str, object]:
        return {
            "account_id": EXPECTED_ACCOUNT_ID,
            "status": "ACTIVE",
            "tradable": True,
            "trading_blocked": False,
            "currency": "USD",
            "cash": "1000",
            "buying_power": "1000",
        }

    def get_positions(self) -> tuple[dict[str, object], ...]:
        return self.positions

    def get_orders(self, _query: object) -> tuple[dict[str, object], ...]:
        return ()

    def submit_order(self, request: object) -> object:
        self.submitted_requests.append(request)
        raise AssertionError("preview candidate must not submit")


def _paper_env() -> dict[str, str]:
    return {
        "APP_PROFILE": "paper",
        "APCA_API_KEY_ID": "fake-paper-key",
        "APCA_API_SECRET_KEY": "fake-paper-secret",
        "ALPACA_EXPECTED_PAPER_ACCOUNT_ID": EXPECTED_ACCOUNT_ID,
        "ALPACA_PAPER_BASE_URL": DEFAULT_ALPACA_PAPER_BASE_URL,
    }


def _fake_daily_lab(_config: object) -> dict[str, object]:
    return {
        "daily_cycle_blocker_status": "none",
        "daily_cycle_latest_bar_date": "2026-08-08",
        "daily_cycle_data_freshness_status": "accepted_data_current",
        "daily_cycle_data_refresh_status": "no_refresh_required",
    }


def _forbidden_factory(_config: object) -> object:
    raise AssertionError("broker factory must not be called")


def _bars(as_of: datetime, *, posture: str) -> tuple[Bar, ...]:
    first = as_of - timedelta(days=219)
    bars: list[Bar] = []
    for index in range(220):
        close = Decimal("100") + Decimal(index)
        if posture == "risk_off":
            close = Decimal("500") - Decimal(index)
        timestamp = first + timedelta(days=index)
        bars.append(
            Bar(
                symbol="SPY",
                timestamp=timestamp,
                open=close,
                high=close,
                low=close,
                close=close,
                volume=Decimal("1000"),
            )
        )
    return tuple(bars)


def _write_bars_csv(tmp_path: Path, *, posture: str) -> Path:
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


def _write_short_bars_csv(tmp_path: Path) -> Path:
    path = tmp_path / "insufficient.csv"
    start = date(2026, 1, 1)
    rows = ["date,symbol,open,high,low,close,adjusted_close,volume"]
    for index in range(30):
        current = start + timedelta(days=index)
        close = Decimal("100") + Decimal(index)
        rows.append(
            f"{current.isoformat()},SPY,{close},{close},{close},{close},{close},1000"
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path
