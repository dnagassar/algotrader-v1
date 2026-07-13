"""Pure offline paper lifecycle adapter for cancellation planning."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
import hashlib
import json

from algotrader.core.time import require_utc_datetime
from algotrader.errors import ValidationError
from algotrader.execution.paper_order_lifecycle_replay import (
    ORDER_LIFECYCLE_AMBIGUOUS_AFTER_SUBMIT,
    ORDER_LIFECYCLE_INCONSISTENT,
    ORDER_LIFECYCLE_NOT_SEEN,
    PaperOrderLifecycleEvent,
    PaperOrderLifecycleReplayResult,
    replay_paper_order_lifecycle,
)
from algotrader.orchestration.cancellation_planning_policy import (
    CancellationOrderObservation,
    CancellationPlanningBlocker,
    CancellationPlanningRequest,
    CancellationPlanningResult,
    plan_cancellation,
)


PAPER_CANCELLATION_PLANNING_ARTIFACT_VERSION = (
    "paper_cancellation_planning_artifact_v1"
)
_CONTROL_BLOCKERS = frozenset(
    {
        CancellationPlanningBlocker.STOP_REQUESTED,
        CancellationPlanningBlocker.TRADING_PAUSED,
        CancellationPlanningBlocker.CANCELLATION_NOT_PERMITTED,
    }
)


class PaperCancellationPlanningAdapterBlocker(StrEnum):
    """Typed failures before the broker-free planning policy can evaluate."""

    LIFECYCLE_AMBIGUOUS = "lifecycle_ambiguous"
    LIFECYCLE_INCONSISTENT = "lifecycle_inconsistent"
    EVENT_TIMESTAMP_INVALID = "event_timestamp_invalid"
    EVENT_TIMESTAMP_AFTER_AS_OF = "event_timestamp_after_as_of"
    EVENT_TIMESTAMP_REGRESSION = "event_timestamp_regression"


@dataclass(frozen=True, slots=True)
class PaperCancellationPlanningArtifact:
    """Immutable no-submit evidence from local lifecycle observations."""

    artifact_id: str
    as_of: datetime
    request: CancellationPlanningRequest
    lifecycle_replay: PaperOrderLifecycleReplayResult
    latest_observation: CancellationOrderObservation | None
    planning_result: CancellationPlanningResult | None
    adapter_blocker: PaperCancellationPlanningAdapterBlocker | None

    def __post_init__(self) -> None:
        try:
            as_of = require_utc_datetime(self.as_of)
        except ValidationError as exc:
            raise ValidationError(
                "as_of must be a timezone-aware UTC datetime."
            ) from exc
        object.__setattr__(self, "as_of", as_of)
        if not isinstance(self.request, CancellationPlanningRequest):
            raise ValidationError(
                "request must be a CancellationPlanningRequest."
            )
        if not isinstance(self.lifecycle_replay, PaperOrderLifecycleReplayResult):
            raise ValidationError(
                "lifecycle_replay must be a PaperOrderLifecycleReplayResult."
            )
        if self.latest_observation is not None and not isinstance(
            self.latest_observation,
            CancellationOrderObservation,
        ):
            raise ValidationError(
                "latest_observation must be a CancellationOrderObservation or None."
            )
        if self.planning_result is not None and not isinstance(
            self.planning_result,
            CancellationPlanningResult,
        ):
            raise ValidationError(
                "planning_result must be a CancellationPlanningResult or None."
            )
        if self.adapter_blocker is not None and not isinstance(
            self.adapter_blocker,
            PaperCancellationPlanningAdapterBlocker,
        ):
            raise ValidationError(
                "adapter_blocker must be a typed adapter blocker or None."
            )
        if self.adapter_blocker is not None:
            if self.latest_observation is not None or self.planning_result is not None:
                raise ValidationError(
                    "adapter-blocked artifact cannot contain an observation or policy result."
                )
        elif self.planning_result is None:
            raise ValidationError(
                "policy-evaluated artifact requires a planning result."
            )
        if (
            self.planning_result is not None
            and self.planning_result.planned
            and self.latest_observation is None
        ):
            raise ValidationError(
                "planned artifact requires the latest local observation."
            )
        expected_artifact_id = _artifact_id(
            as_of=self.as_of,
            request=self.request,
            lifecycle_replay=self.lifecycle_replay,
            latest_observation=self.latest_observation,
            planning_result=self.planning_result,
            adapter_blocker=self.adapter_blocker,
        )
        if str(self.artifact_id).strip() != expected_artifact_id:
            raise ValidationError(
                "artifact_id does not match cancellation planning evidence."
            )
        object.__setattr__(self, "artifact_id", expected_artifact_id)

    @property
    def planned(self) -> bool:
        return bool(
            self.adapter_blocker is None
            and self.planning_result is not None
            and self.planning_result.planned
        )

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic primitive-only no-submit artifact."""

        return {
            "artifact_id": self.artifact_id,
            **_artifact_payload(
                as_of=self.as_of,
                request=self.request,
                lifecycle_replay=self.lifecycle_replay,
                latest_observation=self.latest_observation,
                planning_result=self.planning_result,
                adapter_blocker=self.adapter_blocker,
            ),
        }


def adapt_paper_lifecycle_to_cancellation_plan(
    events: Iterable[PaperOrderLifecycleEvent],
    *,
    request: CancellationPlanningRequest,
    as_of: datetime,
) -> PaperCancellationPlanningArtifact:
    """Replay explicit local events and emit one no-submit planning artifact."""

    if not isinstance(request, CancellationPlanningRequest):
        raise ValidationError("request must be a CancellationPlanningRequest.")
    try:
        evaluated_at = require_utc_datetime(as_of)
    except ValidationError as exc:
        raise ValidationError(
            "as_of must be a timezone-aware UTC datetime."
        ) from exc
    observations = tuple(events)
    if any(not isinstance(event, PaperOrderLifecycleEvent) for event in observations):
        raise ValidationError(
            "events must contain only PaperOrderLifecycleEvent values."
        )

    replay = replay_paper_order_lifecycle(observations)
    control_result = plan_cancellation(request, None)
    if control_result.blocker in _CONTROL_BLOCKERS:
        return _build_artifact(
            as_of=evaluated_at,
            request=request,
            lifecycle_replay=replay,
            planning_result=control_result,
        )

    if replay.final_state == ORDER_LIFECYCLE_INCONSISTENT:
        return _build_artifact(
            as_of=evaluated_at,
            request=request,
            lifecycle_replay=replay,
            adapter_blocker=(
                PaperCancellationPlanningAdapterBlocker.LIFECYCLE_INCONSISTENT
            ),
        )
    if replay.final_state == ORDER_LIFECYCLE_AMBIGUOUS_AFTER_SUBMIT:
        return _build_artifact(
            as_of=evaluated_at,
            request=request,
            lifecycle_replay=replay,
            adapter_blocker=(
                PaperCancellationPlanningAdapterBlocker.LIFECYCLE_AMBIGUOUS
            ),
        )
    if not observations or replay.final_state == ORDER_LIFECYCLE_NOT_SEEN:
        return _build_artifact(
            as_of=evaluated_at,
            request=request,
            lifecycle_replay=replay,
            planning_result=control_result,
        )

    parsed_times: list[datetime] = []
    for event in observations:
        parsed = _event_timestamp(event.observed_at)
        if parsed is None:
            return _build_artifact(
                as_of=evaluated_at,
                request=request,
                lifecycle_replay=replay,
                adapter_blocker=(
                    PaperCancellationPlanningAdapterBlocker.EVENT_TIMESTAMP_INVALID
                ),
            )
        if parsed > evaluated_at:
            return _build_artifact(
                as_of=evaluated_at,
                request=request,
                lifecycle_replay=replay,
                adapter_blocker=(
                    PaperCancellationPlanningAdapterBlocker.EVENT_TIMESTAMP_AFTER_AS_OF
                ),
            )
        if parsed_times and parsed < parsed_times[-1]:
            return _build_artifact(
                as_of=evaluated_at,
                request=request,
                lifecycle_replay=replay,
                adapter_blocker=(
                    PaperCancellationPlanningAdapterBlocker.EVENT_TIMESTAMP_REGRESSION
                ),
            )
        parsed_times.append(parsed)

    latest = observations[-1]
    client_order_id = _single_identity(
        event.client_order_id for event in observations
    )
    broker_order_id = _single_identity(
        event.broker_order_id for event in observations
    )
    latest_observation = CancellationOrderObservation(
        client_order_id=client_order_id,
        broker_order_id=broker_order_id,
        symbol=request.target_symbol,
        broker_status=_canonical_status(latest.status),
        observed_at=parsed_times[-1],
    )
    planning_result = plan_cancellation(request, latest_observation)
    return _build_artifact(
        as_of=evaluated_at,
        request=request,
        lifecycle_replay=replay,
        latest_observation=latest_observation,
        planning_result=planning_result,
    )


def _build_artifact(
    *,
    as_of: datetime,
    request: CancellationPlanningRequest,
    lifecycle_replay: PaperOrderLifecycleReplayResult,
    latest_observation: CancellationOrderObservation | None = None,
    planning_result: CancellationPlanningResult | None = None,
    adapter_blocker: PaperCancellationPlanningAdapterBlocker | None = None,
) -> PaperCancellationPlanningArtifact:
    return PaperCancellationPlanningArtifact(
        artifact_id=_artifact_id(
            as_of=as_of,
            request=request,
            lifecycle_replay=lifecycle_replay,
            latest_observation=latest_observation,
            planning_result=planning_result,
            adapter_blocker=adapter_blocker,
        ),
        as_of=as_of,
        request=request,
        lifecycle_replay=lifecycle_replay,
        latest_observation=latest_observation,
        planning_result=planning_result,
        adapter_blocker=adapter_blocker,
    )


def _artifact_id(
    *,
    as_of: datetime,
    request: CancellationPlanningRequest,
    lifecycle_replay: PaperOrderLifecycleReplayResult,
    latest_observation: CancellationOrderObservation | None,
    planning_result: CancellationPlanningResult | None,
    adapter_blocker: PaperCancellationPlanningAdapterBlocker | None,
) -> str:
    encoded = json.dumps(
        _artifact_payload(
            as_of=as_of,
            request=request,
            lifecycle_replay=lifecycle_replay,
            latest_observation=latest_observation,
            planning_result=planning_result,
            adapter_blocker=adapter_blocker,
        ),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()[:24]
    return f"paper_cancel_plan_artifact_{digest}"


def _artifact_payload(
    *,
    as_of: datetime,
    request: CancellationPlanningRequest,
    lifecycle_replay: PaperOrderLifecycleReplayResult,
    latest_observation: CancellationOrderObservation | None,
    planning_result: CancellationPlanningResult | None,
    adapter_blocker: PaperCancellationPlanningAdapterBlocker | None,
) -> dict[str, object]:
    return {
        "artifact_version": PAPER_CANCELLATION_PLANNING_ARTIFACT_VERSION,
        "as_of": as_of.isoformat(),
        "status": (
            "planned"
            if planning_result is not None
            and planning_result.planned
            and adapter_blocker is None
            else "blocked"
        ),
        "no_submit": True,
        "cancel_attempted": False,
        "broker_access_performed": False,
        "broker_mutation_performed": False,
        "request": _request_payload(request),
        "lifecycle_replay": _replay_payload(lifecycle_replay),
        "latest_observation": (
            {}
            if latest_observation is None
            else _observation_payload(latest_observation)
        ),
        "planning_result": (
            {} if planning_result is None else planning_result.to_dict()
        ),
        "adapter_blocker": (
            "" if adapter_blocker is None else adapter_blocker.value
        ),
    }


def _request_payload(request: CancellationPlanningRequest) -> dict[str, object]:
    return {
        "target_client_order_id": request.target_client_order_id,
        "target_broker_order_id": request.target_broker_order_id,
        "target_symbol": request.target_symbol,
        "reason": request.reason,
        "cancellation_permitted": request.cancellation_permitted,
        "snapshot_fresh": request.snapshot_fresh,
        "trading_enabled": request.trading_enabled,
        "stop_requested": request.stop_requested,
    }


def _observation_payload(
    observation: CancellationOrderObservation,
) -> dict[str, str]:
    return {
        "client_order_id": observation.client_order_id,
        "broker_order_id": observation.broker_order_id,
        "symbol": observation.symbol,
        "broker_status": observation.broker_status,
        "observed_at": observation.observed_at.isoformat(),
    }


def _replay_payload(
    replay: PaperOrderLifecycleReplayResult,
) -> dict[str, object]:
    return {
        "client_order_id": replay.client_order_id,
        "final_state": replay.final_state,
        "terminal": replay.terminal,
        "blockers": list(replay.blockers),
        "submitted": replay.submitted,
        "mutated": replay.mutated,
        "order_seen": replay.order_seen,
        "observations": [_event_payload(event) for event in replay.observations],
    }


def _event_payload(event: PaperOrderLifecycleEvent) -> dict[str, object]:
    return {
        "observed_at": _optional_text(event.observed_at),
        "client_order_id": _optional_text(event.client_order_id),
        "broker_order_id": _optional_text(event.broker_order_id),
        "status": _optional_text(event.status),
        "filled_qty": _optional_text(event.filled_qty),
        "submitted": event.submitted,
        "mutated": event.mutated,
        "source": _optional_text(event.source),
    }


def _event_timestamp(value: object) -> datetime | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


def _single_identity(values: Iterable[object]) -> str:
    identities = tuple(
        dict.fromkeys(str(value).strip() for value in values if str(value).strip())
    )
    return identities[0] if len(identities) == 1 else ""


def _canonical_status(value: object) -> str:
    status = str(value).strip().lower()
    if "." in status:
        status = status.rsplit(".", maxsplit=1)[-1]
    status = status.replace("-", "_").replace(" ", "_")
    return "partially_filled" if status == "partial_fill" else status


def _optional_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value)
    return str(value).strip()


__all__ = [
    "PAPER_CANCELLATION_PLANNING_ARTIFACT_VERSION",
    "PaperCancellationPlanningAdapterBlocker",
    "PaperCancellationPlanningArtifact",
    "adapt_paper_lifecycle_to_cancellation_plan",
]
