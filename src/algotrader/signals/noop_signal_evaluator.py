"""Minimal no-op signal evaluator boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from algotrader.core.time import require_utc_datetime
from algotrader.errors import ValidationError

from .signal_evaluation_input import SignalEvaluationInputSnapshot
from .signal_evaluation_result import SignalEvaluationResult
from .validated_signal_definition import ValidatedSignalDefinition

__all__ = [
    "NoOpSignalEvaluator",
]


@dataclass(frozen=True, slots=True)
class NoOpSignalEvaluator:
    """Construct advisory no-op signal-evaluation metadata from explicit inputs."""

    def evaluate(
        self,
        definition: ValidatedSignalDefinition,
        input_snapshot: SignalEvaluationInputSnapshot,
        *,
        as_of: datetime,
        evaluated_at: datetime,
    ) -> SignalEvaluationResult:
        definition = _validated_definition(definition)
        input_snapshot = _validated_input_snapshot(input_snapshot)
        as_of = _utc_datetime(as_of, "as_of")
        evaluated_at = _utc_datetime(evaluated_at, "evaluated_at")

        if evaluated_at < as_of:
            raise ValidationError("evaluated_at must be greater than or equal to as_of.")
        if input_snapshot.as_of > as_of:
            raise ValidationError("input_snapshot.as_of must not be after as_of.")

        return SignalEvaluationResult(
            evaluation_id=_evaluation_id(definition, input_snapshot, as_of, evaluated_at),
            signal_id=definition.signal_id,
            signal_version=definition.version,
            source_artifact_id=definition.source_artifact_id,
            source_artifact_version=definition.source_artifact_version,
            as_of=as_of,
            evaluated_at=evaluated_at,
            input_fingerprint=input_snapshot.snapshot_id,
            output_value="NO_SIGNAL_COMPUTED",
            reason_code="NOOP_SIGNAL_EVALUATOR",
            diagnostics=(
                "no signal computation performed",
                "no feature values inspected",
                "no actionability implied",
            ),
            assumptions=(
                "definition and input snapshot were supplied explicitly",
                "result is advisory metadata only",
            ),
            limitations=(
                "not a signal firing",
                "not a recommendation",
                "not risk approval",
                "not execution-ready",
            ),
        )


def _validated_definition(
    definition: ValidatedSignalDefinition,
) -> ValidatedSignalDefinition:
    if not isinstance(definition, ValidatedSignalDefinition):
        raise ValidationError("definition must be a ValidatedSignalDefinition.")
    return definition


def _validated_input_snapshot(
    input_snapshot: SignalEvaluationInputSnapshot,
) -> SignalEvaluationInputSnapshot:
    if not isinstance(input_snapshot, SignalEvaluationInputSnapshot):
        raise ValidationError(
            "input_snapshot must be a SignalEvaluationInputSnapshot."
        )
    return input_snapshot


def _utc_datetime(value: datetime, field_name: str) -> datetime:
    try:
        return require_utc_datetime(value)
    except ValidationError as exc:
        raise ValidationError(
            f"{field_name} must be a timezone-aware UTC datetime."
        ) from exc


def _evaluation_id(
    definition: ValidatedSignalDefinition,
    input_snapshot: SignalEvaluationInputSnapshot,
    as_of: datetime,
    evaluated_at: datetime,
) -> str:
    return (
        f"signal-evaluation:{definition.signal_id}:{definition.version}:"
        f"{input_snapshot.snapshot_id}:{as_of.isoformat()}:"
        f"{evaluated_at.isoformat()}"
    )
