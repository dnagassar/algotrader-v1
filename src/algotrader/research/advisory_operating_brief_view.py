"""Deterministic view records over advisory section metadata."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_section import (
    AdvisoryOperatingBriefSection,
)

__all__ = [
    "AdvisoryOperatingBriefView",
    "build_advisory_operating_brief_view",
]

_VIEW_KEY = "advisory_operating_brief_section_view"
_VIEW_TITLE = "Advisory operating brief section view"
_VIEW_STATE = "candidate_only"
_LIMITATIONS = (
    "metadata-only view over supplied advisory section records",
    "describes section keys, titles, states, counts, and diagnostics only",
    "does not render section content or change section records",
)


@dataclass(frozen=True, slots=True)
class AdvisoryOperatingBriefView:
    """Compact metadata-only view of supplied advisory section records."""

    view_key: str
    view_title: str
    view_state: str
    section_count: int
    section_keys: tuple[str, ...]
    summary_lines: tuple[str, ...]
    diagnostic_messages: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        view_key = _constant_string(
            self.view_key,
            _VIEW_KEY,
            "view_key",
        )
        view_title = _constant_string(
            self.view_title,
            _VIEW_TITLE,
            "view_title",
        )
        view_state = _constant_string(
            self.view_state,
            _VIEW_STATE,
            "view_state",
        )
        section_count = _positive_int(self.section_count, "section_count")
        section_keys = _string_tuple(
            self.section_keys,
            "section_keys",
            allow_empty=False,
        )
        summary_lines = _string_tuple(
            self.summary_lines,
            "summary_lines",
            allow_empty=False,
        )
        diagnostic_messages = _string_tuple(
            self.diagnostic_messages,
            "diagnostic_messages",
            allow_empty=True,
        )
        limitations = _string_tuple(
            self.limitations,
            "limitations",
            allow_empty=False,
        )

        if len(section_keys) != section_count:
            raise ValidationError("section_keys must match section_count.")
        if len(summary_lines) != section_count:
            raise ValidationError("summary_lines must match section_count.")
        if limitations != _LIMITATIONS:
            raise ValidationError("limitations must match advisory view limits.")

        object.__setattr__(self, "view_key", view_key)
        object.__setattr__(self, "view_title", view_title)
        object.__setattr__(self, "view_state", view_state)
        object.__setattr__(self, "section_count", section_count)
        object.__setattr__(self, "section_keys", section_keys)
        object.__setattr__(self, "summary_lines", summary_lines)
        object.__setattr__(self, "diagnostic_messages", diagnostic_messages)
        object.__setattr__(self, "limitations", limitations)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive advisory view metadata."""

        return {
            "view_key": self.view_key,
            "view_title": self.view_title,
            "view_state": self.view_state,
            "section_count": self.section_count,
            "section_keys": list(self.section_keys),
            "summary_lines": list(self.summary_lines),
            "diagnostic_messages": list(self.diagnostic_messages),
            "limitations": list(self.limitations),
        }


def build_advisory_operating_brief_view(
    sections: AdvisoryOperatingBriefSection
    | tuple[AdvisoryOperatingBriefSection, ...],
) -> AdvisoryOperatingBriefView:
    """Build a compact advisory view from exact section records."""

    section_records = _section_records(sections)

    return AdvisoryOperatingBriefView(
        view_key=_VIEW_KEY,
        view_title=_VIEW_TITLE,
        view_state=_VIEW_STATE,
        section_count=len(section_records),
        section_keys=tuple(section.section_key for section in section_records),
        summary_lines=tuple(
            _summary_line(section) for section in section_records
        ),
        diagnostic_messages=tuple(
            message
            for section in section_records
            for message in section.diagnostic_messages
        ),
        limitations=_LIMITATIONS,
    )


def _section_records(
    sections: AdvisoryOperatingBriefSection
    | tuple[AdvisoryOperatingBriefSection, ...],
) -> tuple[AdvisoryOperatingBriefSection, ...]:
    if type(sections) is AdvisoryOperatingBriefSection:
        return (sections,)

    if type(sections) is not tuple:
        raise ValidationError(
            "sections must be an AdvisoryOperatingBriefSection or tuple."
        )
    if not sections:
        raise ValidationError("sections must contain at least one section.")

    for index, section in enumerate(sections):
        if type(section) is not AdvisoryOperatingBriefSection:
            raise ValidationError(
                "sections"
                f"[{index}] must be an AdvisoryOperatingBriefSection."
            )

    return sections


def _summary_line(section: AdvisoryOperatingBriefSection) -> str:
    return (
        f"{section.section_key}: {section.section_title}; "
        f"state={section.section_state}; count={section.item_count}"
    )


def _constant_string(value: object, expected: str, field_name: str) -> str:
    string_value = _required_string(value, field_name)
    if string_value != expected:
        raise ValidationError(f"{field_name} must match advisory view metadata.")

    return string_value


def _string_tuple(
    values: object,
    field_name: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    if not allow_empty and not items:
        raise ValidationError(f"{field_name} must contain at least one string.")

    for index, value in enumerate(items):
        _required_string(value, f"{field_name}[{index}]")

    return items


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value


def _positive_int(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an integer.")
    if value < 1:
        raise ValidationError(f"{field_name} must be positive.")

    return value
