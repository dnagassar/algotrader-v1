"""Deterministic broker-free policy for one cancellation plan."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from algotrader.core.time import require_utc_datetime
from algotrader.errors import ValidationError
from algotrader.orchestration.cancellation_planning_flow import (
    CANCELABLE_CANCELLATION_STATUSES,
    CancellationPlan,
    build_cancellation_plan,
)


TERMINAL_CANCELLATION_STATUSES = frozenset(
    {
        "canceled",
        "cancelled",
        "done_for_day",
        "expired",
        "filled",
        "rejected",
    }
)
UNKNOWN_CANCELLATION_STATUSES = frozenset({"", "ambiguous", "unknown"})


class CancellationPlanningStatus(StrEnum):
    PLANNED = "planned"
    BLOCKED = "blocked"


class CancellationPlanningBlocker(StrEnum):
    STOP_REQUESTED = "stop_requested"
    TRADING_PAUSED = "trading_paused"
    CANCELLATION_NOT_PERMITTED = "cancellation_not_permitted"
    OBSERVATION_MISSING = "observation_missing"
    SNAPSHOT_NOT_FRESH = "snapshot_not_fresh"
    TARGET_CLIENT_ORDER_ID_MISSING = "target_client_order_id_missing"
    TARGET_BROKER_ORDER_ID_MISSING = "target_broker_order_id_missing"
    TARGET_SYMBOL_MISSING = "target_symbol_missing"
    REASON_MISSING = "reason_missing"
    OBSERVED_CLIENT_ORDER_ID_MISSING = "observed_client_order_id_missing"
    OBSERVED_BROKER_ORDER_ID_MISSING = "observed_broker_order_id_missing"
    OBSERVED_SYMBOL_MISSING = "observed_symbol_missing"
    CLIENT_ORDER_ID_MISMATCH = "client_order_id_mismatch"
    BROKER_ORDER_ID_MISMATCH = "broker_order_id_mismatch"
    SYMBOL_MISMATCH = "symbol_mismatch"
    ORDER_STATUS_UNKNOWN = "order_status_unknown"
    ORDER_TERMINAL = "order_terminal"
    ORDER_NOT_CANCELABLE = "order_not_cancelable"


__all__ = [
    "TERMINAL_CANCELLATION_STATUSES",
    "UNKNOWN_CANCELLATION_STATUSES",
    "CancellationOrderObservation",
    "CancellationPlanningBlocker",
    "CancellationPlanningRequest",
    "CancellationPlanningResult",
    "CancellationPlanningStatus",
    "plan_cancellation",
]


@dataclass(frozen=True, slots=True)
class CancellationOrderObservation:
    """Explicit local observation supplied to cancellation planning."""

    client_order_id: str
    broker_order_id: str
    symbol: str
    broker_status: str
    observed_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "client_order_id", str(self.client_order_id).strip())
        object.__setattr__(self, "broker_order_id", str(self.broker_order_id).strip())
        object.__setattr__(self, "symbol", str(self.symbol).strip().upper())
        object.__setattr__(self, "broker_status", _normalized_status(self.broker_status))
        try:
            observed_at = require_utc_datetime(self.observed_at)
        except ValidationError as exc:
            raise ValidationError(
                "observed_at must be a timezone-aware UTC datetime."
            ) from exc
        object.__setattr__(self, "observed_at", observed_at)


@dataclass(frozen=True, slots=True)
class CancellationPlanningRequest:
    """Explicit target identity, permission, freshness, and runtime controls."""

    target_client_order_id: str
    target_broker_order_id: str
    target_symbol: str
    reason: str
    cancellation_permitted: bool
    snapshot_fresh: bool
    trading_enabled: bool
    stop_requested: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_client_order_id",
            str(self.target_client_order_id).strip(),
        )
        object.__setattr__(
            self,
            "target_broker_order_id",
            str(self.target_broker_order_id).strip(),
        )
        object.__setattr__(self, "target_symbol", str(self.target_symbol).strip().upper())
        object.__setattr__(self, "reason", str(self.reason).strip())
        for field_name in (
            "cancellation_permitted",
            "snapshot_fresh",
            "trading_enabled",
            "stop_requested",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValidationError(f"{field_name} must be a boolean.")


@dataclass(frozen=True, slots=True)
class CancellationPlanningResult:
    """One typed broker-free planning outcome."""

    status: CancellationPlanningStatus
    plan: CancellationPlan | None
    blocker: CancellationPlanningBlocker | None

    def __post_init__(self) -> None:
        if not isinstance(self.status, CancellationPlanningStatus):
            raise ValidationError("status must be a CancellationPlanningStatus.")
        if self.status is CancellationPlanningStatus.PLANNED:
            if not isinstance(self.plan, CancellationPlan) or self.blocker is not None:
                raise ValidationError("planned result requires a plan and no blocker.")
        elif self.plan is not None or not isinstance(
            self.blocker,
            CancellationPlanningBlocker,
        ):
            raise ValidationError("blocked result requires one typed blocker and no plan.")

    @property
    def planned(self) -> bool:
        return self.status is CancellationPlanningStatus.PLANNED

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "blocker": "" if self.blocker is None else self.blocker.value,
            "plan": {} if self.plan is None else self.plan.to_dict(),
        }


def plan_cancellation(
    request: CancellationPlanningRequest,
    observation: CancellationOrderObservation | None,
) -> CancellationPlanningResult:
    """Return one deterministic plan or the first fail-closed blocker."""

    if not isinstance(request, CancellationPlanningRequest):
        raise ValidationError("request must be a CancellationPlanningRequest.")
    if observation is not None and not isinstance(
        observation,
        CancellationOrderObservation,
    ):
        raise ValidationError(
            "observation must be a CancellationOrderObservation or None."
        )

    blocker = _planning_blocker(request, observation)
    if blocker is not None:
        return CancellationPlanningResult(
            status=CancellationPlanningStatus.BLOCKED,
            plan=None,
            blocker=blocker,
        )
    assert observation is not None
    return CancellationPlanningResult(
        status=CancellationPlanningStatus.PLANNED,
        plan=build_cancellation_plan(
            client_order_id=observation.client_order_id,
            broker_order_id=observation.broker_order_id,
            symbol=observation.symbol,
            broker_status=observation.broker_status,
            observed_at=observation.observed_at,
            reason=request.reason,
        ),
        blocker=None,
    )


def _planning_blocker(
    request: CancellationPlanningRequest,
    observation: CancellationOrderObservation | None,
) -> CancellationPlanningBlocker | None:
    if request.stop_requested:
        return CancellationPlanningBlocker.STOP_REQUESTED
    if not request.trading_enabled:
        return CancellationPlanningBlocker.TRADING_PAUSED
    if not request.cancellation_permitted:
        return CancellationPlanningBlocker.CANCELLATION_NOT_PERMITTED
    if observation is None:
        return CancellationPlanningBlocker.OBSERVATION_MISSING
    if not request.snapshot_fresh:
        return CancellationPlanningBlocker.SNAPSHOT_NOT_FRESH
    if not request.target_client_order_id:
        return CancellationPlanningBlocker.TARGET_CLIENT_ORDER_ID_MISSING
    if not request.target_broker_order_id:
        return CancellationPlanningBlocker.TARGET_BROKER_ORDER_ID_MISSING
    if not request.target_symbol:
        return CancellationPlanningBlocker.TARGET_SYMBOL_MISSING
    if not request.reason:
        return CancellationPlanningBlocker.REASON_MISSING
    if not observation.client_order_id:
        return CancellationPlanningBlocker.OBSERVED_CLIENT_ORDER_ID_MISSING
    if not observation.broker_order_id:
        return CancellationPlanningBlocker.OBSERVED_BROKER_ORDER_ID_MISSING
    if not observation.symbol:
        return CancellationPlanningBlocker.OBSERVED_SYMBOL_MISSING
    if observation.client_order_id != request.target_client_order_id:
        return CancellationPlanningBlocker.CLIENT_ORDER_ID_MISMATCH
    if observation.broker_order_id != request.target_broker_order_id:
        return CancellationPlanningBlocker.BROKER_ORDER_ID_MISMATCH
    if observation.symbol != request.target_symbol:
        return CancellationPlanningBlocker.SYMBOL_MISMATCH
    if observation.broker_status in UNKNOWN_CANCELLATION_STATUSES:
        return CancellationPlanningBlocker.ORDER_STATUS_UNKNOWN
    if observation.broker_status in TERMINAL_CANCELLATION_STATUSES:
        return CancellationPlanningBlocker.ORDER_TERMINAL
    if observation.broker_status not in CANCELABLE_CANCELLATION_STATUSES:
        return CancellationPlanningBlocker.ORDER_NOT_CANCELABLE
    return None


def _normalized_status(value: object) -> str:
    text = str(value).strip().lower()
    if "." in text:
        text = text.rsplit(".", maxsplit=1)[-1]
    return text.replace("-", "_").replace(" ", "_")
