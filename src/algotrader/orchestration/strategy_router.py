"""Pure strategy-routing contract for paper-mutation eligibility."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from algotrader.core.time import require_utc_datetime
from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError
from algotrader.signals.etf_sma_evaluator import EtfSmaSignalResult
from algotrader.signals.spy_rsi_mean_reversion import (
    SPYRsiMeanReversionSignalResult,
)

StrategySignalState = Literal[
    "trade_candidate",
    "no_trade",
    "blocked",
    "insufficient_evidence",
    "inactive_regime",
]
StrategyIntendedAction = Literal["buy", "sell_close", "hold", "no_action"]
StrategyIntendedSide = Literal["", "buy", "sell"]
StrategyPromotionStatus = Literal[
    "research_only",
    "shadow_only",
    "paper_preview_candidate",
    "paper_mutation_candidate",
]
StrategyRouteStatus = Literal["action_routed", "no_action_required", "blocked"]

STRATEGY_ROUTER_REQUIRED_LABELS = (
    "paper_lab_only",
    "not_live_authorized",
    "profit_claim=none",
)
STRATEGY_ROUTER_LABEL = "strategy_router_contract"
SMA_TRAINING_WHEEL_STRATEGY_FAMILY = "long_only_broad_etf_sma_trend_filter"
SMA_TRAINING_WHEEL_STRATEGY_ID = "spy_sma_50_200_training_wheel"
SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_FAMILY = "mean_reversion"
SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_ID = "spy_rsi_14_mean_reversion_shadow"

__all__ = [
    "SMA_TRAINING_WHEEL_STRATEGY_FAMILY",
    "SMA_TRAINING_WHEEL_STRATEGY_ID",
    "SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_FAMILY",
    "SPY_RSI_MEAN_REVERSION_SHADOW_STRATEGY_ID",
    "STRATEGY_ROUTER_LABEL",
    "STRATEGY_ROUTER_REQUIRED_LABELS",
    "StrategyIntendedAction",
    "StrategyIntendedSide",
    "StrategyPromotionStatus",
    "StrategyRouteReceipt",
    "StrategyRouteStatus",
    "StrategySignal",
    "StrategySignalState",
    "route_strategy_signals",
    "strategy_signal_from_etf_sma_result",
    "strategy_signal_from_spy_rsi_mean_reversion_result",
]


@dataclass(frozen=True, slots=True)
class StrategySignal:
    """Immutable strategy output before routing or paper-supervisor planning."""

    strategy_id: str
    strategy_family: str
    asset_class: str
    signal_state: StrategySignalState
    intended_action: StrategyIntendedAction
    intended_side: StrategyIntendedSide
    expected_holding_period: str
    max_loss_model: str
    risk_budget: str
    data_as_of: datetime
    promotion_status: StrategyPromotionStatus
    labels: tuple[str, ...]
    blockers: tuple[str, ...] = ()
    symbol: str = ""
    universe: tuple[str, ...] = ()
    evidence_score: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "strategy_id",
            _required_string(self.strategy_id, "strategy_id"),
        )
        object.__setattr__(
            self,
            "strategy_family",
            _required_string(self.strategy_family, "strategy_family"),
        )
        object.__setattr__(
            self,
            "asset_class",
            _required_string(self.asset_class, "asset_class"),
        )
        object.__setattr__(
            self,
            "signal_state",
            _choice(self.signal_state, _SIGNAL_STATES, "signal_state"),
        )
        object.__setattr__(
            self,
            "intended_action",
            _choice(self.intended_action, _INTENDED_ACTIONS, "intended_action"),
        )
        object.__setattr__(
            self,
            "intended_side",
            _choice(self.intended_side, _INTENDED_SIDES, "intended_side"),
        )
        object.__setattr__(
            self,
            "expected_holding_period",
            _required_string(
                self.expected_holding_period,
                "expected_holding_period",
            ),
        )
        object.__setattr__(
            self,
            "max_loss_model",
            _required_string(self.max_loss_model, "max_loss_model"),
        )
        object.__setattr__(
            self,
            "risk_budget",
            _required_string(self.risk_budget, "risk_budget"),
        )
        object.__setattr__(
            self,
            "data_as_of",
            _utc_datetime(self.data_as_of, "data_as_of"),
        )
        object.__setattr__(
            self,
            "promotion_status",
            _choice(self.promotion_status, _PROMOTION_STATUSES, "promotion_status"),
        )
        object.__setattr__(
            self,
            "labels",
            _string_tuple(self.labels, "labels"),
        )
        object.__setattr__(
            self,
            "blockers",
            _string_tuple(self.blockers, "blockers"),
        )
        object.__setattr__(self, "symbol", _optional_symbol(self.symbol))
        object.__setattr__(
            self,
            "universe",
            _symbol_tuple(self.universe, "universe"),
        )
        object.__setattr__(
            self,
            "evidence_score",
            _optional_evidence_score(self.evidence_score),
        )
        _validate_signal_consistency(self)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only route input metadata."""

        return {
            "strategy_id": self.strategy_id,
            "strategy_family": self.strategy_family,
            "symbol": self.symbol,
            "universe": list(self.universe),
            "asset_class": self.asset_class,
            "signal_state": self.signal_state,
            "intended_action": self.intended_action,
            "intended_side": self.intended_side,
            "evidence_score": _decimal_text(self.evidence_score),
            "expected_holding_period": self.expected_holding_period,
            "max_loss_model": self.max_loss_model,
            "risk_budget": self.risk_budget,
            "data_as_of": self.data_as_of.isoformat(),
            "promotion_status": self.promotion_status,
            "labels": list(self.labels),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True, slots=True)
class StrategyRouteReceipt:
    """Immutable router decision for a set of strategy signals."""

    route_status: StrategyRouteStatus
    route_action: str
    paper_mutation_allowed: bool
    reason: str
    signals: tuple[StrategySignal, ...]
    selected_signal: StrategySignal | None
    candidate_signal_ids: tuple[str, ...]
    blocked_signal_ids: tuple[str, ...]
    labels: tuple[str, ...]
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "route_status",
            _choice(self.route_status, _ROUTE_STATUSES, "route_status"),
        )
        object.__setattr__(
            self,
            "route_action",
            _required_string(self.route_action, "route_action"),
        )
        if type(self.paper_mutation_allowed) is not bool:
            raise ValidationError("paper_mutation_allowed must be a boolean.")
        object.__setattr__(self, "reason", _required_string(self.reason, "reason"))
        object.__setattr__(
            self,
            "signals",
            _signal_tuple(self.signals),
        )
        if self.selected_signal is not None and not isinstance(
            self.selected_signal,
            StrategySignal,
        ):
            raise ValidationError("selected_signal must be a StrategySignal or None.")
        object.__setattr__(
            self,
            "candidate_signal_ids",
            _string_tuple(self.candidate_signal_ids, "candidate_signal_ids"),
        )
        object.__setattr__(
            self,
            "blocked_signal_ids",
            _string_tuple(self.blocked_signal_ids, "blocked_signal_ids"),
        )
        object.__setattr__(self, "labels", _string_tuple(self.labels, "labels"))
        object.__setattr__(
            self,
            "blockers",
            _string_tuple(self.blockers, "blockers"),
        )
        if self.paper_mutation_allowed and self.selected_signal is None:
            raise ValidationError(
                "selected_signal is required when paper_mutation_allowed is true."
            )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only router receipt metadata."""

        return {
            "route_status": self.route_status,
            "route_action": self.route_action,
            "paper_mutation_allowed": self.paper_mutation_allowed,
            "reason": self.reason,
            "selected_signal_id": (
                None if self.selected_signal is None else self.selected_signal.strategy_id
            ),
            "selected_signal": (
                None if self.selected_signal is None else self.selected_signal.to_dict()
            ),
            "candidate_signal_ids": list(self.candidate_signal_ids),
            "blocked_signal_ids": list(self.blocked_signal_ids),
            "labels": list(self.labels),
            "blockers": list(self.blockers),
            "signals": [signal.to_dict() for signal in self.signals],
        }


def route_strategy_signals(
    signals: Iterable[StrategySignal],
    *,
    required_labels: Iterable[str] = STRATEGY_ROUTER_REQUIRED_LABELS,
) -> StrategyRouteReceipt:
    """Route strategy signals to at most one paper-mutation candidate."""

    signal_values = _signal_tuple(signals)
    required_label_values = _string_tuple(required_labels, "required_labels")
    labels = _dedupe(
        label
        for signal in signal_values
        for label in (*signal.labels, STRATEGY_ROUTER_LABEL)
    )
    candidate_signals: list[StrategySignal] = []
    blocked_signal_ids: list[str] = []
    route_blockers: list[str] = []

    for signal in signal_values:
        signal_blockers = _paper_mutation_blockers(signal, required_label_values)
        if signal_blockers:
            blocked_signal_ids.append(signal.strategy_id)
            route_blockers.extend(
                f"{signal.strategy_id}:{blocker}" for blocker in signal_blockers
            )
            continue
        if signal.signal_state == "trade_candidate":
            candidate_signals.append(signal)

    if not signal_values:
        return _receipt(
            route_status="no_action_required",
            route_action="no_action_required",
            paper_mutation_allowed=False,
            reason="no_strategy_signals",
            signals=signal_values,
            selected_signal=None,
            candidate_signal_ids=(),
            blocked_signal_ids=(),
            labels=labels,
            blockers=(),
        )

    if len(candidate_signals) == 1:
        selected = candidate_signals[0]
        return _receipt(
            route_status="action_routed",
            route_action=selected.intended_action,
            paper_mutation_allowed=True,
            reason="single_promoted_candidate_routed",
            signals=signal_values,
            selected_signal=selected,
            candidate_signal_ids=(selected.strategy_id,),
            blocked_signal_ids=tuple(blocked_signal_ids),
            labels=labels,
            blockers=tuple(route_blockers),
        )

    if len(candidate_signals) > 1:
        blocker = _candidate_conflict_blocker(candidate_signals)
        return _receipt(
            route_status="blocked",
            route_action="blocked",
            paper_mutation_allowed=False,
            reason=blocker,
            signals=signal_values,
            selected_signal=None,
            candidate_signal_ids=tuple(signal.strategy_id for signal in candidate_signals),
            blocked_signal_ids=tuple(blocked_signal_ids),
            labels=labels,
            blockers=tuple((*route_blockers, blocker)),
        )

    status: StrategyRouteStatus = (
        "blocked" if route_blockers or blocked_signal_ids else "no_action_required"
    )
    reason = "all_candidates_blocked" if status == "blocked" else "no_valid_candidate"
    return _receipt(
        route_status=status,
        route_action="no_action_required",
        paper_mutation_allowed=False,
        reason=reason,
        signals=signal_values,
        selected_signal=None,
        candidate_signal_ids=(),
        blocked_signal_ids=tuple(blocked_signal_ids),
        labels=labels,
        blockers=tuple(route_blockers),
    )


def strategy_signal_from_etf_sma_result(
    result: EtfSmaSignalResult,
    *,
    promotion_status: StrategyPromotionStatus = "paper_mutation_candidate",
) -> StrategySignal:
    """Adapt the existing ETF/SMA posture result into the router contract."""

    if not isinstance(result, EtfSmaSignalResult):
        raise ValidationError("result must be an EtfSmaSignalResult.")

    if result.posture == "bullish_risk_on":
        signal_state: StrategySignalState = "trade_candidate"
        intended_action: StrategyIntendedAction = "buy"
        intended_side: StrategyIntendedSide = "buy"
        blockers: tuple[str, ...] = ()
    elif result.posture == "defensive_risk_off":
        signal_state = "trade_candidate"
        intended_action = "sell_close"
        intended_side = "sell"
        blockers = ()
    else:
        signal_state = "insufficient_evidence"
        intended_action = "no_action"
        intended_side = ""
        blockers = ("insufficient_history",)

    return StrategySignal(
        strategy_id=(
            f"{result.symbol.lower()}_sma_"
            f"{result.short_window}_{result.long_window}_training_wheel"
        ),
        strategy_family=result.strategy_type,
        symbol=result.symbol,
        asset_class=result.asset_class,
        signal_state=signal_state,
        intended_action=intended_action,
        intended_side=intended_side,
        expected_holding_period="daily_trend_filter_until_next_signal",
        max_loss_model="not_modeled_in_router_contract",
        risk_budget="bounded_paper_notional",
        data_as_of=result.as_of,
        promotion_status=promotion_status,
        labels=tuple(_dedupe((*result.labels, STRATEGY_ROUTER_LABEL))),
        blockers=blockers,
        evidence_score=None,
    )


def strategy_signal_from_spy_rsi_mean_reversion_result(
    result: SPYRsiMeanReversionSignalResult,
) -> StrategySignal:
    """Adapt the SPY RSI mean-reversion result into a shadow-only route signal."""

    if not isinstance(result, SPYRsiMeanReversionSignalResult):
        raise ValidationError("result must be a SPYRsiMeanReversionSignalResult.")

    if result.posture == "oversold_buy_candidate":
        signal_state: StrategySignalState = "trade_candidate"
        intended_action: StrategyIntendedAction = "buy"
        intended_side: StrategyIntendedSide = "buy"
        blockers: tuple[str, ...] = ()
    elif result.posture == "overbought_cash_candidate":
        signal_state = "trade_candidate"
        intended_action = "sell_close"
        intended_side = "sell"
        blockers = ()
    elif result.posture == "insufficient_history":
        signal_state = "insufficient_evidence"
        intended_action = "no_action"
        intended_side = ""
        blockers = ("insufficient_history",)
    else:
        signal_state = "no_trade"
        intended_action = "no_action"
        intended_side = ""
        blockers = ()

    return StrategySignal(
        strategy_id=(
            f"{result.symbol.lower()}_rsi_"
            f"{result.lookback_window}_mean_reversion_shadow"
        ),
        strategy_family=result.strategy_type,
        symbol=result.symbol,
        asset_class=result.asset_class,
        signal_state=signal_state,
        intended_action=intended_action,
        intended_side=intended_side,
        expected_holding_period="daily_mean_reversion_shadow_until_next_signal",
        max_loss_model="not_modeled_shadow_signal_only",
        risk_budget="none_shadow_only_no_allocation",
        data_as_of=result.as_of,
        promotion_status="shadow_only",
        labels=tuple(_dedupe((*result.labels, STRATEGY_ROUTER_LABEL))),
        blockers=blockers,
        evidence_score=None,
    )


def _receipt(
    *,
    route_status: StrategyRouteStatus,
    route_action: str,
    paper_mutation_allowed: bool,
    reason: str,
    signals: tuple[StrategySignal, ...],
    selected_signal: StrategySignal | None,
    candidate_signal_ids: tuple[str, ...],
    blocked_signal_ids: tuple[str, ...],
    labels: tuple[str, ...],
    blockers: tuple[str, ...],
) -> StrategyRouteReceipt:
    return StrategyRouteReceipt(
        route_status=route_status,
        route_action=route_action,
        paper_mutation_allowed=paper_mutation_allowed,
        reason=reason,
        signals=signals,
        selected_signal=selected_signal,
        candidate_signal_ids=candidate_signal_ids,
        blocked_signal_ids=blocked_signal_ids,
        labels=labels,
        blockers=tuple(_dedupe(blockers)),
    )


def _paper_mutation_blockers(
    signal: StrategySignal,
    required_labels: tuple[str, ...],
) -> tuple[str, ...]:
    blockers: list[str] = list(signal.blockers)
    if signal.signal_state in {"no_trade", "inactive_regime"}:
        return tuple(blockers)
    if signal.signal_state == "blocked":
        blockers.append("signal_blocked")
    if signal.signal_state == "insufficient_evidence":
        blockers.append("insufficient_evidence")
    if signal.signal_state != "trade_candidate":
        return tuple(_dedupe(blockers))
    if signal.promotion_status != "paper_mutation_candidate":
        blockers.append(
            f"promotion_status_not_paper_mutation_candidate:{signal.promotion_status}"
        )
    for label in required_labels:
        if label not in signal.labels:
            blockers.append(f"missing_required_label:{label}")
    if signal.intended_action in {"hold", "no_action"}:
        blockers.append("trade_candidate_without_paper_action")
    return tuple(_dedupe(blockers))


def _candidate_conflict_blocker(candidates: list[StrategySignal]) -> str:
    route_keys = {
        (
            candidate.symbol,
            candidate.universe,
            candidate.asset_class,
            candidate.intended_action,
            candidate.intended_side,
        )
        for candidate in candidates
    }
    if len(route_keys) > 1:
        return "conflict_requires_review"
    return "multiple_promoted_candidates_require_review"


def _signal_tuple(values: Iterable[StrategySignal]) -> tuple[StrategySignal, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Iterable):
        raise ValidationError("signals must be an iterable of StrategySignal values.")

    signals = tuple(values)
    seen_ids: set[str] = set()
    for index, signal in enumerate(signals):
        if not isinstance(signal, StrategySignal):
            raise ValidationError(f"signals[{index}] must be a StrategySignal.")
        if signal.strategy_id in seen_ids:
            raise ValidationError("signals must have unique strategy_id values.")
        seen_ids.add(signal.strategy_id)
    return signals


def _validate_signal_consistency(signal: StrategySignal) -> None:
    if not signal.symbol and not signal.universe:
        raise ValidationError("symbol or universe is required.")
    if signal.intended_action == "buy" and signal.intended_side != "buy":
        raise ValidationError("buy action requires buy side.")
    if signal.intended_action == "sell_close" and signal.intended_side != "sell":
        raise ValidationError("sell_close action requires sell side.")
    if signal.intended_action in {"hold", "no_action"} and signal.intended_side:
        raise ValidationError("hold and no_action require an empty intended_side.")
    if signal.signal_state == "trade_candidate" and signal.intended_action in {
        "hold",
        "no_action",
    }:
        raise ValidationError("trade_candidate requires a paper action.")
    if signal.signal_state != "trade_candidate" and signal.intended_action not in {
        "hold",
        "no_action",
    }:
        raise ValidationError("non-trade signals cannot carry a paper action.")


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _choice(value: object, allowed: tuple[str, ...], field_name: str) -> str:
    if type(value) is not str or value not in allowed:
        allowed_text = ", ".join(allowed)
        raise ValidationError(f"{field_name} must be one of: {allowed_text}.")
    return value


def _optional_symbol(value: object) -> str:
    if value in (None, ""):
        return ""
    if type(value) is not str:
        raise ValidationError("symbol must be a string.")
    return symbol_value(value)


def _symbol_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if values in (None, ""):
        return ()
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of symbols.")
    return tuple(symbol_value(value) for value in values)


def _string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")
    return tuple(_required_string(value, f"{field_name}[]") for value in values)


def _optional_evidence_score(value: object) -> Decimal | None:
    if value is None:
        return None
    if type(value) is not Decimal or not value.is_finite():
        raise ValidationError("evidence_score must be a finite Decimal or None.")
    if value < Decimal("0") or value > Decimal("1"):
        raise ValidationError("evidence_score must be between 0 and 1.")
    return value


def _utc_datetime(value: object, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError(f"{field_name} must be a timezone-aware UTC datetime.")
    try:
        return require_utc_datetime(value)
    except ValidationError as exc:
        raise ValidationError(
            f"{field_name} must be a timezone-aware UTC datetime."
        ) from exc


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    items: list[str] = []
    for value in values:
        item = _required_string(value, "value")
        if item not in seen:
            seen.add(item)
            items.append(item)
    return tuple(items)


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


_SIGNAL_STATES = (
    "trade_candidate",
    "no_trade",
    "blocked",
    "insufficient_evidence",
    "inactive_regime",
)
_INTENDED_ACTIONS = ("buy", "sell_close", "hold", "no_action")
_INTENDED_SIDES = ("", "buy", "sell")
_PROMOTION_STATUSES = (
    "research_only",
    "shadow_only",
    "paper_preview_candidate",
    "paper_mutation_candidate",
)
_ROUTE_STATUSES = ("action_routed", "no_action_required", "blocked")
