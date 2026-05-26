"""Deterministic metadata manifest for primitive research observations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import hashlib
import json
import math

from algotrader.errors import ValidationError

__all__ = [
    "ResearchObservationManifestEntry",
    "ResearchObservationManifest",
    "build_research_observation_manifest",
]

_MANIFEST_TYPE = "research_observation_manifest"
_SCHEMA_VERSION = "1"
_ADVISORY_SCOPE = "research_observation_metadata_only"
_ENTRY_KEYS = frozenset(("observation_name", "payload"))
_DIGEST_LENGTH = 64


@dataclass(frozen=True, slots=True)
class ResearchObservationManifestEntry:
    """Deterministic metadata for one primitive observation payload."""

    observation_name: str
    observation_type: str | None
    payload_key_count: int
    payload_digest_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observation_name",
            _require_observation_name(self.observation_name),
        )
        object.__setattr__(
            self,
            "observation_type",
            _require_optional_observation_type(self.observation_type),
        )
        object.__setattr__(
            self,
            "payload_key_count",
            _require_non_negative_int(
                self.payload_key_count,
                "payload_key_count",
            ),
        )
        object.__setattr__(
            self,
            "payload_digest_sha256",
            _require_sha256_digest(self.payload_digest_sha256),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only entry metadata."""

        return {
            "observation_name": self.observation_name,
            "observation_type": self.observation_type,
            "payload_key_count": self.payload_key_count,
            "payload_digest_sha256": self.payload_digest_sha256,
        }


@dataclass(frozen=True, slots=True)
class ResearchObservationManifest:
    """In-memory manifest for primitive research observation payloads."""

    manifest_type: str
    schema_version: str
    advisory_scope: str
    entry_count: int
    entries: tuple[ResearchObservationManifestEntry, ...]

    def __post_init__(self) -> None:
        if self.manifest_type != _MANIFEST_TYPE:
            raise ValidationError(
                "manifest_type must be exactly research_observation_manifest."
            )
        if self.schema_version != _SCHEMA_VERSION:
            raise ValidationError("schema_version must be exactly 1.")
        if self.advisory_scope != _ADVISORY_SCOPE:
            raise ValidationError(
                "advisory_scope must be exactly "
                "research_observation_metadata_only."
            )

        entries = _require_manifest_entries(self.entries)
        entry_count = _require_non_negative_int(self.entry_count, "entry_count")
        if entry_count != len(entries):
            raise ValidationError("entry_count must match entries length.")
        _reject_duplicate_names(entries)

        object.__setattr__(self, "entry_count", entry_count)
        object.__setattr__(self, "entries", entries)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only manifest metadata."""

        return {
            "manifest_type": self.manifest_type,
            "schema_version": self.schema_version,
            "advisory_scope": self.advisory_scope,
            "entry_count": self.entry_count,
            "entries": [entry.to_dict() for entry in self.entries],
        }


def build_research_observation_manifest(
    entries: Iterable[object] | Mapping[str, object],
) -> ResearchObservationManifest:
    """Build an in-memory manifest for primitive observation payloads."""

    manifest_entries = tuple(
        _build_manifest_entry(name, payload)
        for name, payload in _iter_named_payloads(entries)
    )
    _reject_duplicate_names(manifest_entries)

    return ResearchObservationManifest(
        manifest_type=_MANIFEST_TYPE,
        schema_version=_SCHEMA_VERSION,
        advisory_scope=_ADVISORY_SCOPE,
        entry_count=len(manifest_entries),
        entries=manifest_entries,
    )


def _iter_named_payloads(
    entries: Iterable[object] | Mapping[str, object],
) -> tuple[tuple[object, object], ...]:
    if isinstance(entries, Mapping):
        return tuple(entries.items())
    if isinstance(entries, (str, bytes)) or not isinstance(entries, Iterable):
        raise ValidationError("entries must contain named observation payloads.")

    return tuple(_unpack_entry(entry) for entry in entries)


def _unpack_entry(entry: object) -> tuple[object, object]:
    if isinstance(entry, Mapping):
        if set(entry) != _ENTRY_KEYS:
            raise ValidationError(
                "manifest entries must contain observation_name and payload."
            )
        return entry["observation_name"], entry["payload"]

    if type(entry) is tuple and len(entry) == 2:
        return entry[0], entry[1]

    raise ValidationError(
        "manifest entries must be named observation payload pairs."
    )


def _build_manifest_entry(
    observation_name: object,
    payload: object,
) -> ResearchObservationManifestEntry:
    name = _require_observation_name(observation_name)
    primitive_payload = _require_payload(payload)
    serialized = json.dumps(
        primitive_payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    return ResearchObservationManifestEntry(
        observation_name=name,
        observation_type=_payload_observation_type(primitive_payload),
        payload_key_count=len(primitive_payload),
        payload_digest_sha256=hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest(),
    )


def _require_observation_name(value: object) -> str:
    if type(value) is not str:
        raise ValidationError("observation_name must be a non-empty string.")
    if value.strip() == "":
        raise ValidationError("observation_name must be a non-empty string.")

    return value


def _require_optional_observation_type(value: object) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise ValidationError("observation_type must be a string when present.")

    return value


def _require_payload(value: object) -> dict[str, object]:
    if type(value) is not dict:
        raise ValidationError("observation payload must be a dictionary.")
    if any(type(key) is not str for key in value):
        raise ValidationError("observation payload keys must be strings.")
    if not _primitive_json_value(value):
        raise ValidationError("observation payload must be primitive JSON.")

    return value


def _payload_observation_type(payload: dict[str, object]) -> str | None:
    if "observation_type" not in payload:
        return None

    return _require_optional_observation_type(payload["observation_type"])


def _primitive_json_value(value: object) -> bool:
    if value is None or type(value) in (str, int, bool):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_primitive_json_value(item) for item in value)
    if type(value) is dict:
        return all(
            type(key) is str and _primitive_json_value(item)
            for key, item in value.items()
        )

    return False


def _require_non_negative_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be a non-negative integer.")
    if value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer.")

    return value


def _require_sha256_digest(value: object) -> str:
    if type(value) is not str:
        raise ValidationError("payload_digest_sha256 must be a SHA-256 digest.")
    if len(value) != _DIGEST_LENGTH:
        raise ValidationError("payload_digest_sha256 must be a SHA-256 digest.")
    if any(character not in "0123456789abcdef" for character in value):
        raise ValidationError("payload_digest_sha256 must be a SHA-256 digest.")

    return value


def _require_manifest_entries(
    entries: object,
) -> tuple[ResearchObservationManifestEntry, ...]:
    if not isinstance(entries, tuple):
        raise ValidationError("entries must be a tuple of manifest entries.")
    if any(type(entry) is not ResearchObservationManifestEntry for entry in entries):
        raise ValidationError("entries must be ResearchObservationManifestEntry.")

    return entries


def _reject_duplicate_names(
    entries: tuple[ResearchObservationManifestEntry, ...],
) -> None:
    names = [entry.observation_name for entry in entries]
    if len(set(names)) != len(names):
        raise ValidationError("observation_name values must be unique.")
