"""Section records for advisory operating brief content bundles."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_content_bundle import (
    AdvisoryOperatingBriefContentBundle,
)

__all__ = [
    "AdvisoryOperatingBriefSection",
    "build_advisory_operating_brief_sections",
]

_SECTION_STATE = "candidate_only"
_DIAGNOSTIC_KEY = "diagnostic_issues"
_DEFAULT_LIMITATIONS = (
    "metadata-only section record for present advisory content branch",
    "describes branch presence and item count only",
    "does not render content or mutate advisory content bundles",
)
_DIAGNOSTIC_LIMITATIONS = (
    *_DEFAULT_LIMITATIONS,
    "diagnostic messages are copied from existing issue records",
)
_SECTION_DEFINITIONS = (
    ("candidate_research_briefs", "Candidate research brief metadata"),
    ("strategy_eligibility_briefs", "Strategy eligibility brief metadata"),
    ("risk_authority_briefs", "Risk authority brief metadata"),
    ("research_queue_briefs", "Research queue brief metadata"),
    (
        "sma_research_observation_briefs",
        "SMA research observation brief metadata",
    ),
    (
        "research_return_observation_briefs",
        "Research return observation brief metadata",
    ),
    (
        "research_return_summary_observation_briefs",
        "Research return summary observation brief metadata",
    ),
    (
        "sma_research_summary_observations",
        "SMA research summary observation metadata",
    ),
    (
        "research_data_source_readiness",
        "Research data-source readiness diagnostic metadata",
    ),
    (
        "research_data_source_readiness_summaries",
        "Research data-source readiness summary diagnostic metadata",
    ),
    (_DIAGNOSTIC_KEY, "Diagnostic issue metadata"),
)


@dataclass(frozen=True, slots=True)
class AdvisoryOperatingBriefSection:
    """Metadata-only advisory section for a present content bundle branch."""

    section_key: str
    section_title: str
    section_state: str
    source_branches: tuple[str, ...]
    item_count: int
    diagnostic_messages: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        section_key = _section_key(self.section_key)
        section_title = _required_string(self.section_title, "section_title")
        section_state = _section_state(self.section_state)
        source_branches = _source_branches_tuple(self.source_branches)
        item_count = _positive_int(self.item_count, "item_count")
        diagnostic_messages = _string_tuple(
            self.diagnostic_messages,
            "diagnostic_messages",
            allow_empty=True,
        )
        limitations = _string_tuple(
            self.limitations,
            "limitations",
            allow_empty=True,
        )

        if section_title != _section_title(section_key):
            raise ValidationError("section_title must match section_key.")
        if source_branches != (section_key,):
            raise ValidationError("source_branches must match section_key.")
        if section_key == _DIAGNOSTIC_KEY:
            if len(diagnostic_messages) != item_count:
                raise ValidationError(
                    "diagnostic_messages must match diagnostic issue count."
                )
        elif diagnostic_messages:
            raise ValidationError(
                "diagnostic_messages must be empty for non-diagnostic sections."
            )

        object.__setattr__(self, "section_key", section_key)
        object.__setattr__(self, "section_title", section_title)
        object.__setattr__(self, "section_state", section_state)
        object.__setattr__(self, "source_branches", source_branches)
        object.__setattr__(self, "item_count", item_count)
        object.__setattr__(self, "diagnostic_messages", diagnostic_messages)
        object.__setattr__(self, "limitations", limitations)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive section metadata."""

        return {
            "section_key": self.section_key,
            "section_title": self.section_title,
            "section_state": self.section_state,
            "source_branches": list(self.source_branches),
            "item_count": self.item_count,
            "diagnostic_messages": list(self.diagnostic_messages),
            "limitations": list(self.limitations),
        }


def build_advisory_operating_brief_sections(
    bundle: AdvisoryOperatingBriefContentBundle,
) -> tuple[AdvisoryOperatingBriefSection, ...]:
    """Build deterministic section records for present bundle branches."""

    content_bundle = _content_bundle(bundle)
    sections: list[AdvisoryOperatingBriefSection] = []

    for section_key, section_title in _SECTION_DEFINITIONS:
        branch_items = getattr(content_bundle, section_key)
        if not branch_items:
            continue
        sections.append(
            AdvisoryOperatingBriefSection(
                section_key=section_key,
                section_title=section_title,
                section_state=_SECTION_STATE,
                source_branches=(section_key,),
                item_count=len(branch_items),
                diagnostic_messages=_diagnostic_messages(
                    section_key,
                    branch_items,
                ),
                limitations=_section_limitations(section_key),
            )
        )

    return tuple(sections)


def _content_bundle(value: object) -> AdvisoryOperatingBriefContentBundle:
    if type(value) is not AdvisoryOperatingBriefContentBundle:
        raise ValidationError(
            "bundle must be an AdvisoryOperatingBriefContentBundle."
        )

    return value


def _diagnostic_messages(
    section_key: str,
    items: tuple[object, ...],
) -> tuple[str, ...]:
    if section_key != _DIAGNOSTIC_KEY:
        return ()

    return tuple(item.diagnostic_message for item in items)


def _section_limitations(section_key: str) -> tuple[str, ...]:
    if section_key == _DIAGNOSTIC_KEY:
        return _DIAGNOSTIC_LIMITATIONS

    return _DEFAULT_LIMITATIONS


def _section_key(value: object) -> str:
    section_key = _required_string(value, "section_key")
    if not _is_supported_section_key(section_key):
        raise ValidationError("section_key must be a supported branch key.")

    return section_key


def _is_supported_section_key(value: str) -> bool:
    for section_key, unused_title in _SECTION_DEFINITIONS:
        if value == section_key:
            return True

    return False


def _section_title(value: str) -> str:
    for section_key, section_title in _SECTION_DEFINITIONS:
        if value == section_key:
            return section_title

    raise ValidationError("section_key must be a supported branch key.")


def _section_state(value: object) -> str:
    section_state = _required_string(value, "section_state")
    if section_state != _SECTION_STATE:
        raise ValidationError("section_state must be exactly candidate_only.")

    return section_state


def _source_branches_tuple(values: object) -> tuple[str, ...]:
    branches = _string_tuple(values, "source_branches", allow_empty=False)
    if len(branches) != 1:
        raise ValidationError("source_branches must contain one branch key.")

    return branches


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
