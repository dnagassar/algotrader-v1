"""Metadata-only manifests for future local research snapshots."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from algotrader.errors import ValidationError
from algotrader.research._planning_validation import (
    allowed_string as _allowed_string,
    date_to_iso as _date_to_iso,
    plain_date as _plain_date,
    required_non_claims as _validate_required_non_claims,
    required_string as _required_string,
    unique_required_string_tuple as _unique_required_string_tuple,
)

__all__ = [
    "ADJUSTMENT_POLICIES",
    "LOCAL_SNAPSHOT_SOURCE_TYPES",
    "LocalSnapshotManifest",
    "REQUIRED_LOCAL_SNAPSHOT_NON_CLAIMS",
    "RETURN_BASES",
]


LOCAL_SNAPSHOT_SOURCE_TYPES = (
    "manual_local_snapshot",
    "vendor_exported_local_snapshot",
    "broker_exported_local_snapshot",
    "public_downloaded_file",
    "api_exported_local_snapshot",
)
ADJUSTMENT_POLICIES = (
    "unknown",
    "raw_close",
    "adjusted_close",
    "split_adjusted",
    "total_return_vendor",
    "explicit_total_return_construction",
)
RETURN_BASES = (
    "unknown",
    "price_return",
    "adjusted_price_return",
    "total_return",
)
REQUIRED_LOCAL_SNAPSHOT_NON_CLAIMS = (
    "not source approval",
    "not data approval",
    "not universe approval",
    "not benchmark approval",
    "not cash proxy approval",
    "not methodology approval",
    "not parameter approval",
    "not evidence approval",
    "not strategy validation",
    "not trading readiness",
)
_MANIFEST_FIELD_NAMES = (
    "snapshot_id",
    "source_name",
    "source_type",
    "acquisition_date",
    "observation_start_date",
    "observation_end_date",
    "as_of_date",
    "symbols_policy",
    "schema_name",
    "fields",
    "adjustment_policy",
    "return_basis",
    "checksum_sha256",
    "storage_uri",
    "redistribution_status",
    "license_note",
    "provenance_note",
    "limitations",
    "non_claims",
    "normal_pytest_eligible",
)
_DATE_FIELD_NAMES = frozenset(
    (
        "acquisition_date",
        "observation_start_date",
        "observation_end_date",
        "as_of_date",
    )
)
_TUPLE_FIELD_NAMES = frozenset(("fields", "limitations", "non_claims"))
_SHA256_HEX_CHARS = frozenset("0123456789abcdef")


@dataclass(frozen=True, slots=True)
class LocalSnapshotManifest:
    """Metadata-only provenance record for a future local research snapshot."""

    snapshot_id: str
    source_name: str
    source_type: str
    acquisition_date: date
    observation_start_date: date
    observation_end_date: date
    as_of_date: date
    symbols_policy: str
    schema_name: str
    fields: tuple[str, ...]
    adjustment_policy: str
    return_basis: str
    checksum_sha256: str
    storage_uri: str
    redistribution_status: str
    license_note: str
    provenance_note: str
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]
    normal_pytest_eligible: bool

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-compatible primitive manifest metadata."""

        payload: dict[str, object] = {}
        for field_name in _MANIFEST_FIELD_NAMES:
            value = getattr(self, field_name)
            if field_name in _DATE_FIELD_NAMES:
                payload[field_name] = _date_to_iso(value, field_name)
            elif field_name in _TUPLE_FIELD_NAMES:
                payload[field_name] = list(value)
            else:
                payload[field_name] = value

        return payload

    @classmethod
    def from_dict(cls, payload: object) -> "LocalSnapshotManifest":
        """Restore a manifest from strict JSON-compatible primitive metadata."""

        if not isinstance(payload, dict):
            raise ValidationError("local snapshot manifest payload must be a dict.")

        _validate_manifest_payload_fields(payload)
        values: dict[str, object] = {}
        for field_name in _MANIFEST_FIELD_NAMES:
            value = payload[field_name]
            if field_name in _DATE_FIELD_NAMES:
                values[field_name] = _deserialize_plain_date(value, field_name)
            elif field_name in _TUPLE_FIELD_NAMES:
                values[field_name] = _deserialize_string_list(value, field_name)
            else:
                values[field_name] = value

        return cls(**values)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "snapshot_id",
            _required_string(self.snapshot_id, "snapshot_id"),
        )
        object.__setattr__(
            self,
            "source_name",
            _required_string(self.source_name, "source_name"),
        )
        object.__setattr__(
            self,
            "source_type",
            _allowed_string(
                self.source_type,
                "source_type",
                LOCAL_SNAPSHOT_SOURCE_TYPES,
            ),
        )
        object.__setattr__(
            self,
            "acquisition_date",
            _plain_date(self.acquisition_date, "acquisition_date"),
        )
        object.__setattr__(
            self,
            "observation_start_date",
            _plain_date(self.observation_start_date, "observation_start_date"),
        )
        object.__setattr__(
            self,
            "observation_end_date",
            _plain_date(self.observation_end_date, "observation_end_date"),
        )
        object.__setattr__(
            self,
            "as_of_date",
            _plain_date(self.as_of_date, "as_of_date"),
        )
        object.__setattr__(
            self,
            "symbols_policy",
            _required_string(self.symbols_policy, "symbols_policy"),
        )
        object.__setattr__(
            self,
            "schema_name",
            _required_string(self.schema_name, "schema_name"),
        )
        object.__setattr__(
            self,
            "fields",
            _unique_string_tuple(self.fields, "fields"),
        )
        object.__setattr__(
            self,
            "adjustment_policy",
            _allowed_string(
                self.adjustment_policy,
                "adjustment_policy",
                ADJUSTMENT_POLICIES,
            ),
        )
        object.__setattr__(
            self,
            "return_basis",
            _allowed_string(self.return_basis, "return_basis", RETURN_BASES),
        )
        object.__setattr__(
            self,
            "checksum_sha256",
            _sha256_value(self.checksum_sha256, "checksum_sha256"),
        )
        object.__setattr__(
            self,
            "storage_uri",
            _required_string(self.storage_uri, "storage_uri"),
        )
        object.__setattr__(
            self,
            "redistribution_status",
            _required_string(self.redistribution_status, "redistribution_status"),
        )
        object.__setattr__(
            self,
            "license_note",
            _required_string(self.license_note, "license_note"),
        )
        object.__setattr__(
            self,
            "provenance_note",
            _required_string(self.provenance_note, "provenance_note"),
        )
        object.__setattr__(
            self,
            "limitations",
            _unique_string_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "non_claims",
            _required_non_claims(self.non_claims),
        )
        object.__setattr__(
            self,
            "normal_pytest_eligible",
            _required_false(
                self.normal_pytest_eligible,
                "normal_pytest_eligible",
            ),
        )
        _validate_observation_date_range(
            self.observation_start_date,
            self.observation_end_date,
        )


def _unique_string_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    return _unique_required_string_tuple(values, field_name)


def _required_non_claims(values: Iterable[str]) -> tuple[str, ...]:
    items = _validate_required_non_claims(
        values,
        REQUIRED_LOCAL_SNAPSHOT_NON_CLAIMS,
        "non_claims must include required local snapshot non-claims.",
    )
    if len(frozenset(items)) != len(items):
        raise ValidationError("non_claims must not contain duplicates.")

    return items


def _sha256_value(value: str, field_name: str) -> str:
    normalized = _required_string(value, field_name)
    if (
        len(normalized) != 64
        or normalized != normalized.lower()
        or any(character not in _SHA256_HEX_CHARS for character in normalized)
    ):
        raise ValidationError(f"{field_name} must be a lowercase sha256 hex string.")

    return normalized


def _required_false(value: bool, field_name: str) -> bool:
    if value is not False:
        raise ValidationError(f"{field_name} must be exactly False.")

    return value


def _validate_observation_date_range(
    observation_start_date: date,
    observation_end_date: date,
) -> None:
    if observation_start_date > observation_end_date:
        raise ValidationError(
            "observation_start_date must be on or before observation_end_date."
        )


def _deserialize_plain_date(value: object, field_name: str) -> date:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be an ISO date string.")

    text = value.strip()
    if text != value or len(text) != 10 or text[4] != "-" or text[7] != "-":
        raise ValidationError(f"{field_name} must use YYYY-MM-DD date format.")

    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be an ISO date string.") from exc

    if parsed.isoformat() != text:
        raise ValidationError(f"{field_name} must use YYYY-MM-DD date format.")

    return parsed


def _deserialize_string_list(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list of strings.")

    return tuple(value)


def _validate_manifest_payload_fields(payload: dict[object, object]) -> None:
    unknown_fields = tuple(
        field_name for field_name in payload if field_name not in _MANIFEST_FIELD_NAMES
    )
    if unknown_fields:
        unknown = ", ".join(str(field_name) for field_name in unknown_fields)
        raise ValidationError(f"unknown local snapshot manifest field(s): {unknown}.")

    missing_fields = tuple(
        field_name for field_name in _MANIFEST_FIELD_NAMES if field_name not in payload
    )
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValidationError(f"missing local snapshot manifest field(s): {missing}.")
