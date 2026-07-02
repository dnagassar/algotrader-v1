"""Pure strategy-to-adapter registry for paper-preview and paper-mutation gates."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal

from algotrader.core.validation import symbol_value
from algotrader.errors import ValidationError
from algotrader.orchestration.strategy_router import (
    SMA_TRAINING_WHEEL_STRATEGY_ID,
    SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_ID,
    STRATEGY_ROUTER_REQUIRED_LABELS,
    StrategyPromotionStatus,
    StrategyRouteReceipt,
    StrategySignal,
)

StrategyAdapterMode = Literal["preview_only", "paper_mutation"]
StrategyAdapterResolutionStatus = Literal["resolved", "blocked"]
StrategyAdapterRegistryInput = (
    Mapping[str, "StrategyAdapterRegistration"]
    | Iterable["StrategyAdapterRegistration"]
)

SMA_TRAINING_WHEEL_PAPER_MUTATION_ADAPTER_ID = (
    "spy_sma_50_200_paper_mutation_adapter"
)
SPY_VOL_SCALED_TREND_PREVIEW_ADAPTER_ID = (
    "spy_vol_scaled_trend_20d_preview_adapter"
)

__all__ = [
    "DEFAULT_STRATEGY_ADAPTER_REGISTRY",
    "SMA_TRAINING_WHEEL_PAPER_MUTATION_ADAPTER_ID",
    "SPY_VOL_SCALED_TREND_PREVIEW_ADAPTER_ID",
    "StrategyAdapterMode",
    "StrategyAdapterRegistration",
    "StrategyAdapterRegistryInput",
    "StrategyAdapterResolution",
    "StrategyAdapterResolutionStatus",
    "resolve_strategy_adapter",
    "resolve_strategy_route_adapter",
]


@dataclass(frozen=True, slots=True)
class StrategyAdapterRegistration:
    """Operator-managed mapping from one promoted strategy to one adapter."""

    strategy_id: str
    promotion_status: StrategyPromotionStatus
    adapter_id: str
    adapter_mode: StrategyAdapterMode
    asset_class: str
    supported_symbols: tuple[str, ...] = ()
    universe: tuple[str, ...] = ()
    max_order_notional: Decimal | str | None = None
    enabled: bool = True
    required_labels: tuple[str, ...] = STRATEGY_ROUTER_REQUIRED_LABELS
    blocker: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "strategy_id",
            _required_string(self.strategy_id, "strategy_id"),
        )
        object.__setattr__(
            self,
            "promotion_status",
            _choice(self.promotion_status, _PROMOTION_STATUSES, "promotion_status"),
        )
        object.__setattr__(
            self,
            "adapter_id",
            _required_string(self.adapter_id, "adapter_id"),
        )
        object.__setattr__(
            self,
            "adapter_mode",
            _choice(self.adapter_mode, _ADAPTER_MODES, "adapter_mode"),
        )
        object.__setattr__(
            self,
            "asset_class",
            _required_string(self.asset_class, "asset_class").lower(),
        )
        object.__setattr__(
            self,
            "supported_symbols",
            _symbol_tuple(self.supported_symbols, "supported_symbols"),
        )
        object.__setattr__(
            self,
            "universe",
            _symbol_tuple(self.universe, "universe"),
        )
        if not self.supported_symbols and not self.universe:
            raise ValidationError("supported_symbols or universe is required.")
        object.__setattr__(
            self,
            "max_order_notional",
            _optional_positive_decimal(self.max_order_notional, "max_order_notional"),
        )
        if type(self.enabled) is not bool:
            raise ValidationError("enabled must be a boolean.")
        object.__setattr__(
            self,
            "required_labels",
            _string_tuple(self.required_labels, "required_labels"),
        )
        object.__setattr__(self, "blocker", _optional_string(self.blocker, "blocker"))

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only registration metadata."""

        return {
            "strategy_id": self.strategy_id,
            "promotion_status": self.promotion_status,
            "adapter_id": self.adapter_id,
            "adapter_mode": self.adapter_mode,
            "asset_class": self.asset_class,
            "supported_symbols": list(self.supported_symbols),
            "universe": list(self.universe),
            "max_order_notional": _decimal_text(self.max_order_notional),
            "enabled": self.enabled,
            "required_labels": list(self.required_labels),
            "blocker": self.blocker,
        }


@dataclass(frozen=True, slots=True)
class StrategyAdapterResolution:
    """Fail-closed adapter resolution receipt for a strategy signal or route."""

    resolution_status: StrategyAdapterResolutionStatus
    reason: str
    strategy_id: str
    promotion_status: str
    adapter_id: str
    adapter_mode: str
    paper_mutation_allowed: bool
    blockers: tuple[str, ...]
    adapter: StrategyAdapterRegistration | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "resolution_status",
            _choice(
                self.resolution_status,
                _RESOLUTION_STATUSES,
                "resolution_status",
            ),
        )
        object.__setattr__(self, "reason", _required_string(self.reason, "reason"))
        object.__setattr__(
            self,
            "strategy_id",
            _optional_string(self.strategy_id, "strategy_id"),
        )
        object.__setattr__(
            self,
            "promotion_status",
            _optional_string(self.promotion_status, "promotion_status"),
        )
        object.__setattr__(
            self,
            "adapter_id",
            _optional_string(self.adapter_id, "adapter_id"),
        )
        if self.adapter_mode:
            object.__setattr__(
                self,
                "adapter_mode",
                _choice(self.adapter_mode, _ADAPTER_MODES, "adapter_mode"),
            )
        if type(self.paper_mutation_allowed) is not bool:
            raise ValidationError("paper_mutation_allowed must be a boolean.")
        object.__setattr__(self, "blockers", _string_tuple(self.blockers, "blockers"))
        if self.adapter is not None and not isinstance(
            self.adapter,
            StrategyAdapterRegistration,
        ):
            raise ValidationError(
                "adapter must be a StrategyAdapterRegistration or None."
            )
        if self.resolution_status == "resolved" and self.adapter is None:
            raise ValidationError("adapter is required for resolved registrations.")
        if self.resolution_status == "resolved" and self.blockers:
            raise ValidationError("resolved registrations cannot carry blockers.")
        if self.paper_mutation_allowed and self.adapter_mode != "paper_mutation":
            raise ValidationError(
                "paper_mutation_allowed requires a paper_mutation adapter."
            )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only adapter resolution metadata."""

        return {
            "resolution_status": self.resolution_status,
            "reason": self.reason,
            "strategy_id": self.strategy_id,
            "promotion_status": self.promotion_status,
            "adapter_id": self.adapter_id,
            "adapter_mode": self.adapter_mode,
            "paper_mutation_allowed": self.paper_mutation_allowed,
            "blockers": list(self.blockers),
            "adapter": None if self.adapter is None else self.adapter.to_dict(),
        }


def resolve_strategy_route_adapter(
    route_receipt: StrategyRouteReceipt,
    *,
    registry: StrategyAdapterRegistryInput | None = None,
    adapter_mode: StrategyAdapterMode = "paper_mutation",
    requested_order_notional: Decimal | str | None = None,
) -> StrategyAdapterResolution:
    """Resolve the selected route signal through the explicit adapter registry."""

    if not isinstance(route_receipt, StrategyRouteReceipt):
        raise ValidationError("route_receipt must be a StrategyRouteReceipt.")
    checked_mode = _choice(adapter_mode, _ADAPTER_MODES, "adapter_mode")
    checked_registry = (
        DEFAULT_STRATEGY_ADAPTER_REGISTRY if registry is None else registry
    )
    if route_receipt.paper_mutation_allowed is not True:
        return _blocked_resolution(
            reason=f"strategy_router_{route_receipt.reason}",
            strategy_id="",
            promotion_status="",
            adapter_id="",
            adapter_mode=checked_mode,
        )
    if route_receipt.selected_signal is None:
        return _blocked_resolution(
            reason="strategy_router_missing_selected_signal",
            strategy_id="",
            promotion_status="",
            adapter_id="",
            adapter_mode=checked_mode,
        )
    return resolve_strategy_adapter(
        route_receipt.selected_signal,
        registry=checked_registry,
        adapter_mode=checked_mode,
        requested_order_notional=requested_order_notional,
    )


def resolve_strategy_adapter(
    signal: StrategySignal,
    *,
    registry: StrategyAdapterRegistryInput | None = None,
    adapter_mode: StrategyAdapterMode = "paper_mutation",
    requested_order_notional: Decimal | str | None = None,
) -> StrategyAdapterResolution:
    """Resolve one strategy signal to an enabled adapter, or fail closed."""

    if not isinstance(signal, StrategySignal):
        raise ValidationError("signal must be a StrategySignal.")
    checked_mode = _choice(adapter_mode, _ADAPTER_MODES, "adapter_mode")
    checked_registry = (
        DEFAULT_STRATEGY_ADAPTER_REGISTRY if registry is None else registry
    )
    registrations = _registry_by_strategy_id(checked_registry)
    registration = registrations.get(signal.strategy_id)
    if registration is None:
        return _blocked_signal_resolution(
            signal,
            reason="strategy_adapter_missing",
            adapter_mode=checked_mode,
        )
    if registration.enabled is not True:
        return _blocked_signal_resolution(
            signal,
            reason=registration.blocker or "strategy_adapter_disabled",
            adapter=registration,
            adapter_mode=registration.adapter_mode,
        )
    if registration.adapter_mode != checked_mode:
        return _blocked_signal_resolution(
            signal,
            reason="strategy_adapter_mode_mismatch",
            adapter=registration,
            adapter_mode=registration.adapter_mode,
        )

    expected_promotion_status = _PROMOTION_STATUS_BY_MODE[registration.adapter_mode]
    if registration.promotion_status != expected_promotion_status:
        return _blocked_signal_resolution(
            signal,
            reason="strategy_adapter_registration_promotion_mismatch",
            adapter=registration,
            adapter_mode=registration.adapter_mode,
        )
    if signal.promotion_status != expected_promotion_status:
        return _blocked_signal_resolution(
            signal,
            reason=(
                f"promotion_status_not_{expected_promotion_status}:"
                f"{signal.promotion_status}"
            ),
            adapter=registration,
            adapter_mode=registration.adapter_mode,
        )
    if signal.asset_class.lower() != registration.asset_class:
        return _blocked_signal_resolution(
            signal,
            reason="strategy_adapter_unsupported_asset_class",
            adapter=registration,
            adapter_mode=registration.adapter_mode,
        )

    signal_symbols = _signal_symbols(signal)
    supported_symbols = _adapter_symbols(registration)
    if not signal_symbols or any(
        symbol not in supported_symbols for symbol in signal_symbols
    ):
        return _blocked_signal_resolution(
            signal,
            reason="strategy_adapter_unsupported_symbol",
            adapter=registration,
            adapter_mode=registration.adapter_mode,
        )

    for required_label in registration.required_labels:
        if required_label not in signal.labels:
            return _blocked_signal_resolution(
                signal,
                reason=f"missing_required_label:{required_label}",
                adapter=registration,
                adapter_mode=registration.adapter_mode,
            )

    requested_notional = _optional_positive_decimal(
        requested_order_notional,
        "requested_order_notional",
    )
    if (
        requested_notional is not None
        and registration.max_order_notional is not None
        and requested_notional > registration.max_order_notional
    ):
        return _blocked_signal_resolution(
            signal,
            reason="strategy_adapter_max_order_notional_exceeded",
            adapter=registration,
            adapter_mode=registration.adapter_mode,
        )

    return StrategyAdapterResolution(
        resolution_status="resolved",
        reason="strategy_adapter_resolved",
        strategy_id=signal.strategy_id,
        promotion_status=signal.promotion_status,
        adapter_id=registration.adapter_id,
        adapter_mode=registration.adapter_mode,
        paper_mutation_allowed=registration.adapter_mode == "paper_mutation",
        blockers=(),
        adapter=registration,
    )


def _blocked_signal_resolution(
    signal: StrategySignal,
    *,
    reason: str,
    adapter_mode: str,
    adapter: StrategyAdapterRegistration | None = None,
) -> StrategyAdapterResolution:
    adapter_id = "" if adapter is None else adapter.adapter_id
    resolved_adapter_mode = adapter_mode if adapter is None else adapter.adapter_mode
    return _blocked_resolution(
        reason=reason,
        strategy_id=signal.strategy_id,
        promotion_status=signal.promotion_status,
        adapter_id=adapter_id,
        adapter_mode=resolved_adapter_mode,
        adapter=adapter,
    )


def _blocked_resolution(
    *,
    reason: str,
    strategy_id: str,
    promotion_status: str,
    adapter_id: str,
    adapter_mode: str,
    adapter: StrategyAdapterRegistration | None = None,
) -> StrategyAdapterResolution:
    return StrategyAdapterResolution(
        resolution_status="blocked",
        reason=reason,
        strategy_id=strategy_id,
        promotion_status=promotion_status,
        adapter_id=adapter_id,
        adapter_mode=adapter_mode,
        paper_mutation_allowed=False,
        blockers=(reason,),
        adapter=adapter,
    )


def _registry_by_strategy_id(
    registry: StrategyAdapterRegistryInput,
) -> dict[str, StrategyAdapterRegistration]:
    if isinstance(registry, Mapping):
        registrations = tuple(registry.values())
    elif isinstance(registry, (str, bytes)) or not isinstance(registry, Iterable):
        raise ValidationError(
            "registry must be a mapping or iterable of StrategyAdapterRegistration values."
        )
    else:
        registrations = tuple(registry)

    by_strategy_id: dict[str, StrategyAdapterRegistration] = {}
    for index, registration in enumerate(registrations):
        if not isinstance(registration, StrategyAdapterRegistration):
            raise ValidationError(
                f"registry[{index}] must be a StrategyAdapterRegistration."
            )
        if registration.strategy_id in by_strategy_id:
            raise ValidationError("registry must have unique strategy_id values.")
        by_strategy_id[registration.strategy_id] = registration
    return by_strategy_id


def _signal_symbols(signal: StrategySignal) -> tuple[str, ...]:
    if signal.symbol:
        return (signal.symbol,)
    return signal.universe


def _adapter_symbols(registration: StrategyAdapterRegistration) -> tuple[str, ...]:
    return _dedupe((*registration.supported_symbols, *registration.universe))


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _optional_string(value: object, field_name: str) -> str:
    if value in (None, ""):
        return ""
    return _required_string(value, field_name)


def _choice(value: object, allowed: tuple[str, ...], field_name: str) -> str:
    if type(value) is not str or value not in allowed:
        allowed_text = ", ".join(allowed)
        raise ValidationError(f"{field_name} must be one of: {allowed_text}.")
    return value


def _string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")
    return tuple(_required_string(value, f"{field_name}[]") for value in values)


def _symbol_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if values in (None, ""):
        return ()
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of symbols.")
    return tuple(symbol_value(value) for value in values)


def _optional_positive_decimal(value: object, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a positive decimal or None.")
    try:
        decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(
            f"{field_name} must be a positive decimal or None."
        ) from exc
    if not decimal_value.is_finite() or decimal_value <= Decimal("0"):
        raise ValidationError(f"{field_name} must be a positive decimal or None.")
    return decimal_value


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


_ADAPTER_MODES = ("preview_only", "paper_mutation")
_RESOLUTION_STATUSES = ("resolved", "blocked")
_PROMOTION_STATUSES = (
    "research_only",
    "shadow_only",
    "paper_preview_candidate",
    "paper_mutation_candidate",
)
_PROMOTION_STATUS_BY_MODE = {
    "preview_only": "paper_preview_candidate",
    "paper_mutation": "paper_mutation_candidate",
}


DEFAULT_STRATEGY_ADAPTER_REGISTRY: tuple[StrategyAdapterRegistration, ...] = (
    StrategyAdapterRegistration(
        strategy_id=SMA_TRAINING_WHEEL_STRATEGY_ID,
        promotion_status="paper_mutation_candidate",
        adapter_id=SMA_TRAINING_WHEEL_PAPER_MUTATION_ADAPTER_ID,
        adapter_mode="paper_mutation",
        asset_class="equity",
        supported_symbols=("SPY",),
        max_order_notional=Decimal("25.00"),
        enabled=True,
        required_labels=STRATEGY_ROUTER_REQUIRED_LABELS,
    ),
    StrategyAdapterRegistration(
        strategy_id=SPY_VOL_SCALED_TREND_PREVIEW_STRATEGY_ID,
        promotion_status="paper_preview_candidate",
        adapter_id=SPY_VOL_SCALED_TREND_PREVIEW_ADAPTER_ID,
        adapter_mode="preview_only",
        asset_class="equity",
        supported_symbols=("SPY",),
        max_order_notional=None,
        enabled=True,
        required_labels=(
            *STRATEGY_ROUTER_REQUIRED_LABELS,
            "paper_preview_quarantine",
        ),
    ),
)
