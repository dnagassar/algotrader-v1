"""Deterministic in-memory export for advisory operating brief packages."""

from __future__ import annotations

from dataclasses import dataclass
import json

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_package import (
    AdvisoryOperatingBriefPackage,
)
from algotrader.research.advisory_operating_brief_package_renderer import (
    render_advisory_operating_brief_package_text,
)

__all__ = [
    "AdvisoryOperatingBriefPackageExport",
    "export_advisory_operating_brief_package",
]


@dataclass(frozen=True, slots=True)
class AdvisoryOperatingBriefPackageExport:
    """Primitive payload, compact JSON, and rendered text for a package."""

    payload: dict[str, object]
    json_text: str
    rendered_text: str

    def __post_init__(self) -> None:
        payload = _validate_payload(object.__getattribute__(self, "payload"))
        json_text = _validate_json_text(
            object.__getattribute__(self, "json_text"),
            payload,
        )
        rendered_text = _validate_required_text(
            object.__getattribute__(self, "rendered_text"),
            "rendered_text",
        )

        object.__setattr__(self, "payload", payload)
        object.__setattr__(self, "json_text", json_text)
        object.__setattr__(self, "rendered_text", rendered_text)

    def __getattribute__(self, name: str) -> object:
        value = object.__getattribute__(self, name)
        if name == "payload":
            return _primitive_payload_copy(value)

        return value


def export_advisory_operating_brief_package(
    package: AdvisoryOperatingBriefPackage,
) -> AdvisoryOperatingBriefPackageExport:
    """Return deterministic in-memory export views for an existing package."""

    if type(package) is not AdvisoryOperatingBriefPackage:
        raise ValidationError(
            "package must be exactly an AdvisoryOperatingBriefPackage."
        )

    payload = package.to_dict()
    return AdvisoryOperatingBriefPackageExport(
        payload=payload,
        json_text=json.dumps(payload, sort_keys=True, separators=(",", ":")),
        rendered_text=render_advisory_operating_brief_package_text(package),
    )


def _validate_payload(value: object) -> dict[str, object]:
    if type(value) is not dict or not value:
        raise ValidationError("payload must be a non-empty primitive dictionary.")

    return _primitive_payload_copy(value)


def _validate_json_text(value: object, payload: dict[str, object]) -> str:
    json_text = _validate_required_text(value, "json_text")
    expected = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    if json_text != expected:
        raise ValidationError("json_text must match compact deterministic payload JSON.")

    try:
        round_tripped = json.loads(json_text)
    except ValueError as exc:
        raise ValidationError("json_text must be valid JSON.") from exc

    if round_tripped != payload:
        raise ValidationError("json_text must round-trip to payload.")

    return json_text


def _validate_required_text(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value


def _primitive_payload_copy(value: object) -> dict[str, object]:
    if type(value) is not dict:
        raise ValidationError("payload must be a primitive dictionary.")

    copied: dict[str, object] = {}
    for key, item in value.items():
        if type(key) is not str:
            raise ValidationError("payload keys must be strings.")
        copied[key] = _primitive_value_copy(item, f"payload[{key}]")

    return copied


def _primitive_value_copy(value: object, field_name: str) -> object:
    if type(value) is dict:
        return _primitive_payload_copy(value)

    if type(value) is list:
        return [
            _primitive_value_copy(item, f"{field_name}[{index}]")
            for index, item in enumerate(value)
        ]

    if value is None or type(value) in (str, int, float, bool):
        return value

    raise ValidationError(f"{field_name} must contain only primitive values.")
