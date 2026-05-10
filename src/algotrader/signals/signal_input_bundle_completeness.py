"""Pure completeness validation for signal input bundles."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from algotrader.errors import ValidationError

from .signal_evaluation_input import SignalEvaluationInputSnapshot
from .signal_input_bundle import SignalInputBundle

__all__ = [
    "SignalInputBundleCompletenessResult",
    "validate_signal_input_bundle_completeness",
]


@dataclass(frozen=True, slots=True)
class SignalInputBundleCompletenessResult:
    """Metadata-only result for snapshot/bundle input-name completeness."""

    snapshot_id: str
    bundle_snapshot_id: str
    is_complete: bool
    missing_input_names: tuple[str, ...]
    extra_input_names: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_id",
            _required_string(self.snapshot_id, "snapshot_id"),
        )
        object.__setattr__(
            self,
            "bundle_snapshot_id",
            _required_string(self.bundle_snapshot_id, "bundle_snapshot_id"),
        )
        object.__setattr__(
            self,
            "is_complete",
            _required_bool(self.is_complete, "is_complete"),
        )
        object.__setattr__(
            self,
            "missing_input_names",
            _string_tuple(self.missing_input_names, "missing_input_names"),
        )
        object.__setattr__(
            self,
            "extra_input_names",
            _string_tuple(self.extra_input_names, "extra_input_names"),
        )


def validate_signal_input_bundle_completeness(
    snapshot: SignalEvaluationInputSnapshot,
    bundle: SignalInputBundle,
) -> SignalInputBundleCompletenessResult:
    """Compare required snapshot input names with bundle value names."""

    if not isinstance(snapshot, SignalEvaluationInputSnapshot):
        raise ValidationError("snapshot must be a SignalEvaluationInputSnapshot.")
    if not isinstance(bundle, SignalInputBundle):
        raise ValidationError("bundle must be a SignalInputBundle.")

    required_input_names = snapshot.required_input_names
    bundle_value_names = tuple(input_value.name for input_value in bundle.values)
    bundle_name_set = set(bundle_value_names)
    required_name_set = set(required_input_names)

    missing_input_names = tuple(
        name for name in required_input_names if name not in bundle_name_set
    )
    extra_input_names = tuple(
        name for name in bundle_value_names if name not in required_name_set
    )

    return SignalInputBundleCompletenessResult(
        snapshot_id=snapshot.snapshot_id,
        bundle_snapshot_id=bundle.snapshot_id,
        is_complete=not missing_input_names,
        missing_input_names=missing_input_names,
        extra_input_names=extra_input_names,
    )


def _required_string(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} is required.")
    if not value.strip():
        raise ValidationError(f"{field_name} is required.")
    return value


def _required_bool(value: bool, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a bool.")
    return value


def _string_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    if isinstance(values, str):
        raise ValidationError(f"{field_name} must be an iterable of strings.")

    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(f"{field_name} must be an iterable of strings.") from exc

    return tuple(
        _required_string(value, f"{field_name}[{index}]")
        for index, value in enumerate(items)
    )
