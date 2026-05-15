"""Metadata-only manifests for local historical price snapshots."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from algotrader.errors import ValidationError
from algotrader.research.price_snapshot import (
    HistoricalPriceSnapshot,
    price_snapshot_fingerprint,
)

__all__ = [
    "ADJUSTMENT_POLICIES",
    "ADJUSTMENT_POLICY_ADJUSTED_CLOSE",
    "ADJUSTMENT_POLICY_RAW",
    "ADJUSTMENT_POLICY_TOTAL_RETURN",
    "ADJUSTMENT_POLICY_UNKNOWN",
    "LOCAL_PRICE_SNAPSHOT_SOURCE_TYPES",
    "LocalPriceSnapshotManifest",
    "SOURCE_TYPE_LOCAL_EXPORT",
    "SOURCE_TYPE_MANUAL_DOWNLOAD",
    "SOURCE_TYPE_SYNTHETIC_TEST",
    "SOURCE_TYPE_VENDOR_SNAPSHOT",
    "build_local_price_snapshot_manifest",
]


ADJUSTMENT_POLICY_RAW = "raw"
ADJUSTMENT_POLICY_ADJUSTED_CLOSE = "adjusted_close"
ADJUSTMENT_POLICY_TOTAL_RETURN = "total_return"
ADJUSTMENT_POLICY_UNKNOWN = "unknown"
ADJUSTMENT_POLICIES = (
    ADJUSTMENT_POLICY_RAW,
    ADJUSTMENT_POLICY_ADJUSTED_CLOSE,
    ADJUSTMENT_POLICY_TOTAL_RETURN,
    ADJUSTMENT_POLICY_UNKNOWN,
)

SOURCE_TYPE_MANUAL_DOWNLOAD = "manual_download"
SOURCE_TYPE_LOCAL_EXPORT = "local_export"
SOURCE_TYPE_VENDOR_SNAPSHOT = "vendor_snapshot"
SOURCE_TYPE_SYNTHETIC_TEST = "synthetic_test"
LOCAL_PRICE_SNAPSHOT_SOURCE_TYPES = (
    SOURCE_TYPE_MANUAL_DOWNLOAD,
    SOURCE_TYPE_LOCAL_EXPORT,
    SOURCE_TYPE_VENDOR_SNAPSHOT,
    SOURCE_TYPE_SYNTHETIC_TEST,
)

_MANIFEST_FIELD_NAMES = (
    "source_name",
    "source_type",
    "symbol",
    "file_name",
    "file_sha256",
    "snapshot_fingerprint",
    "start_date",
    "end_date",
    "row_count",
    "adjustment_policy",
    "created_at",
    "local_only",
    "normal_pytest_eligible",
    "limitations",
)
_DATE_FIELD_NAMES = frozenset(("start_date", "end_date", "created_at"))
_TUPLE_FIELD_NAMES = frozenset(("limitations",))
_SHA256_HEX_CHARS = frozenset("0123456789abcdef")


@dataclass(frozen=True, slots=True)
class LocalPriceSnapshotManifest:
    """Metadata-only provenance record for one local historical price snapshot."""

    source_name: str
    source_type: str
    symbol: str
    file_name: str
    file_sha256: str
    snapshot_fingerprint: str
    start_date: date
    end_date: date
    row_count: int
    adjustment_policy: str
    created_at: date
    local_only: bool = True
    normal_pytest_eligible: bool = False
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-compatible primitive manifest metadata."""
        payload: dict[str, object] = {}

        for field_name in _MANIFEST_FIELD_NAMES:
            value = getattr(self, field_name)
            if field_name in _DATE_FIELD_NAMES:
                payload[field_name] = _serialize_plain_date(value, field_name)
            elif field_name in _TUPLE_FIELD_NAMES:
                payload[field_name] = list(value)
            else:
                payload[field_name] = value

        return payload

    @classmethod
    def from_dict(cls, payload: object) -> "LocalPriceSnapshotManifest":
        """Restore a manifest from strict JSON-compatible primitive metadata."""
        if not isinstance(payload, dict):
            raise ValidationError("local price snapshot manifest payload must be a dict.")

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
            "source_name",
            _required_string(self.source_name, "source_name"),
        )
        object.__setattr__(
            self,
            "source_type",
            _allowed_string(
                self.source_type,
                "source_type",
                LOCAL_PRICE_SNAPSHOT_SOURCE_TYPES,
            ),
        )
        object.__setattr__(self, "symbol", _symbol_value(self.symbol, "symbol"))
        object.__setattr__(self, "file_name", _file_name_value(self.file_name))
        object.__setattr__(
            self,
            "file_sha256",
            _sha256_value(self.file_sha256, "file_sha256"),
        )
        object.__setattr__(
            self,
            "snapshot_fingerprint",
            _sha256_value(self.snapshot_fingerprint, "snapshot_fingerprint"),
        )
        object.__setattr__(
            self,
            "start_date",
            _plain_date_value(self.start_date, "start_date"),
        )
        object.__setattr__(self, "end_date", _plain_date_value(self.end_date, "end_date"))
        object.__setattr__(self, "row_count", _positive_int(self.row_count, "row_count"))
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
            "created_at",
            _plain_date_value(self.created_at, "created_at"),
        )
        object.__setattr__(
            self,
            "local_only",
            _required_true(self.local_only, "local_only"),
        )
        object.__setattr__(
            self,
            "normal_pytest_eligible",
            _required_false(
                self.normal_pytest_eligible,
                "normal_pytest_eligible",
            ),
        )
        object.__setattr__(
            self,
            "limitations",
            _string_tuple(self.limitations, "limitations"),
        )
        _validate_date_range(self.start_date, self.end_date)


def build_local_price_snapshot_manifest(
    snapshot: HistoricalPriceSnapshot,
    *,
    source_name: str,
    source_type: str,
    file_name: str,
    file_sha256: str,
    adjustment_policy: str,
    created_at: date,
    limitations: Iterable[str] = (),
) -> LocalPriceSnapshotManifest:
    """Build metadata for a validated local snapshot without reading files."""
    if not isinstance(snapshot, HistoricalPriceSnapshot):
        raise ValidationError("snapshot must be a HistoricalPriceSnapshot.")

    return LocalPriceSnapshotManifest(
        source_name=source_name,
        source_type=source_type,
        symbol=snapshot.symbol,
        file_name=file_name,
        file_sha256=file_sha256,
        snapshot_fingerprint=price_snapshot_fingerprint(snapshot),
        start_date=snapshot.bars[0].date,
        end_date=snapshot.bars[-1].date,
        row_count=len(snapshot.bars),
        adjustment_policy=adjustment_policy,
        created_at=created_at,
        limitations=limitations,
    )


def _required_string(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} is required.")

    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} is required.")

    return normalized


def _allowed_string(
    value: str,
    field_name: str,
    allowed_values: tuple[str, ...],
) -> str:
    normalized = _required_string(value, field_name).lower()
    if normalized not in allowed_values:
        allowed = ", ".join(allowed_values)
        raise ValidationError(f"{field_name} must be one of: {allowed}.")

    return normalized


def _symbol_value(value: str, field_name: str) -> str:
    return _required_string(value, field_name).upper()


def _file_name_value(value: str) -> str:
    normalized = _required_string(value, "file_name")
    if (
        normalized in {".", ".."}
        or "/" in normalized
        or "\\" in normalized
        or ":" in normalized
    ):
        raise ValidationError("file_name must be a name only.")

    return normalized


def _sha256_value(value: str, field_name: str) -> str:
    normalized = _required_string(value, field_name)
    if (
        len(normalized) != 64
        or normalized != normalized.lower()
        or any(character not in _SHA256_HEX_CHARS for character in normalized)
    ):
        raise ValidationError(f"{field_name} must be a lowercase sha256 hex string.")

    return normalized


def _plain_date_value(value: date, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a plain date.")

    return value


def _positive_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{field_name} must be an integer.")
    if value <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")

    return value


def _required_true(value: bool, field_name: str) -> bool:
    if value is not True:
        raise ValidationError(f"{field_name} must be exactly True.")

    return value


def _required_false(value: bool, field_name: str) -> bool:
    if value is not False:
        raise ValidationError(f"{field_name} must be exactly False.")

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


def _validate_date_range(start_date: date, end_date: date) -> None:
    if start_date > end_date:
        raise ValidationError("start_date must be on or before end_date.")


def _serialize_plain_date(value: object, field_name: str) -> str:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a plain date.")

    return value.isoformat()


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
        raise ValidationError(f"unknown local price snapshot manifest field(s): {unknown}.")

    missing_fields = tuple(
        field_name for field_name in _MANIFEST_FIELD_NAMES if field_name not in payload
    )
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValidationError(f"missing local price snapshot manifest field(s): {missing}.")
