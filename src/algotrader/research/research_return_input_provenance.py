"""Return-input manifest provenance contract."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.research_return_input_package import ResearchReturnInputPackage

__all__ = [
    "ResearchReturnInputProvenance",
    "build_research_return_input_provenance",
    "validate_research_return_input_provenance_matches_package",
]

_LOWERCASE_SHA256_HEX_CHARS = frozenset("0123456789abcdef")


@dataclass(frozen=True, slots=True)
class ResearchReturnInputProvenance:
    """Immutable package-to-manifest provenance binding."""

    snapshot_id: str
    fingerprint: str
    manifest_fixture_id: str
    manifest_checksum: str

    def __post_init__(self) -> None:
        _required_exact_string(self.snapshot_id, "snapshot_id")
        _validate_fingerprint_shape(self.fingerprint)
        _required_exact_string(self.manifest_fixture_id, "manifest_fixture_id")
        _required_exact_string(self.manifest_checksum, "manifest_checksum")

        if self.manifest_fixture_id != self.snapshot_id:
            raise ValidationError("manifest_fixture_id must match snapshot_id.")

        if self.manifest_checksum != f"sha256:{self.fingerprint}":
            raise ValidationError("manifest_checksum must match fingerprint.")


def build_research_return_input_provenance(
    package: ResearchReturnInputPackage,
) -> ResearchReturnInputProvenance:
    """Build the deterministic manifest provenance for a package."""

    checked_package = _package(package)
    snapshot_id = checked_package.snapshot.snapshot_id
    fingerprint = checked_package.fingerprint
    return ResearchReturnInputProvenance(
        snapshot_id=snapshot_id,
        fingerprint=fingerprint,
        manifest_fixture_id=snapshot_id,
        manifest_checksum=f"sha256:{fingerprint}",
    )


def validate_research_return_input_provenance_matches_package(
    package: ResearchReturnInputPackage,
    provenance: ResearchReturnInputProvenance,
) -> ResearchReturnInputProvenance:
    """Verify package and provenance fields match exactly."""

    checked_package = _package(package)
    checked_provenance = _provenance(provenance)
    expected_checksum = f"sha256:{checked_package.fingerprint}"

    if checked_provenance.snapshot_id != checked_package.snapshot.snapshot_id:
        raise ValidationError("provenance snapshot_id must match package snapshot_id.")

    if checked_provenance.fingerprint != checked_package.fingerprint:
        raise ValidationError("provenance fingerprint must match package fingerprint.")

    if checked_provenance.manifest_fixture_id != checked_package.snapshot.snapshot_id:
        raise ValidationError(
            "provenance manifest_fixture_id must match package snapshot_id."
        )

    if checked_provenance.manifest_checksum != expected_checksum:
        raise ValidationError(
            "provenance manifest_checksum must match package fingerprint."
        )

    return checked_provenance


def _package(value: ResearchReturnInputPackage) -> ResearchReturnInputPackage:
    if not isinstance(value, ResearchReturnInputPackage):
        raise ValidationError("package must be a ResearchReturnInputPackage.")

    return value


def _provenance(
    value: ResearchReturnInputProvenance,
) -> ResearchReturnInputProvenance:
    if not isinstance(value, ResearchReturnInputProvenance):
        raise ValidationError(
            "provenance must be a ResearchReturnInputProvenance."
        )

    return value


def _required_exact_string(value: object, field_name: str) -> None:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    if not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    if value != value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")


def _validate_fingerprint_shape(fingerprint: object) -> None:
    if type(fingerprint) is not str:
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
