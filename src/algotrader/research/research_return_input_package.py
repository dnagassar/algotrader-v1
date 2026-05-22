"""Verified return-input snapshot package contract."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.research_return_input import ResearchReturnInputSnapshot
from algotrader.research.research_return_input_consistency import (
    validate_research_return_input_snapshot_consistency,
)
from algotrader.research.research_return_input_fingerprint import (
    research_return_input_snapshot_fingerprint,
)

__all__ = [
    "ResearchReturnInputPackage",
    "build_research_return_input_package",
]

_LOWERCASE_SHA256_HEX_CHARS = frozenset("0123456789abcdef")


@dataclass(frozen=True, slots=True)
class ResearchReturnInputPackage:
    """Immutable binding of a snapshot to its verified fingerprint."""

    snapshot: ResearchReturnInputSnapshot
    fingerprint: str

    def __post_init__(self) -> None:
        _validate_snapshot_instance(self.snapshot)
        _validate_fingerprint_shape(self.fingerprint)
        validate_research_return_input_snapshot_consistency(self.snapshot)

        expected_fingerprint = research_return_input_snapshot_fingerprint(self.snapshot)
        if self.fingerprint != expected_fingerprint:
            raise ValidationError("fingerprint must match snapshot fingerprint.")

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic primitive package payload."""

        return {
            "snapshot": self.snapshot.to_dict(),
            "fingerprint": self.fingerprint,
        }


def build_research_return_input_package(
    snapshot: ResearchReturnInputSnapshot,
) -> ResearchReturnInputPackage:
    """Validate a snapshot and bind it to its deterministic fingerprint."""

    validate_research_return_input_snapshot_consistency(snapshot)
    fingerprint = research_return_input_snapshot_fingerprint(snapshot)
    return ResearchReturnInputPackage(snapshot=snapshot, fingerprint=fingerprint)


def _validate_snapshot_instance(snapshot: object) -> None:
    if not isinstance(snapshot, ResearchReturnInputSnapshot):
        raise ValidationError("snapshot must be a ResearchReturnInputSnapshot.")


def _validate_fingerprint_shape(fingerprint: object) -> None:
    if not isinstance(fingerprint, str):
        raise ValidationError(
            "fingerprint must be a 64-character lowercase SHA-256 hex string."
        )

    if len(fingerprint) != 64:
        raise ValidationError(
            "fingerprint must be a 64-character lowercase SHA-256 hex string."
        )

    if any(character not in _LOWERCASE_SHA256_HEX_CHARS for character in fingerprint):
        raise ValidationError(
            "fingerprint must be a 64-character lowercase SHA-256 hex string."
        )
