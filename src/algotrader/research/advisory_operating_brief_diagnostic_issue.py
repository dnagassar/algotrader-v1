"""Metadata-only diagnostic issues for advisory operating brief bundles."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_content_bundle import (
    AdvisoryOperatingBriefContentBundle,
)
from algotrader.research.research_data_source_readiness import (
    ResearchDataSourceReadiness,
)
from algotrader.research.research_data_source_readiness_summary import (
    ResearchDataSourceReadinessSummary,
)

__all__ = [
    "AdvisoryOperatingBriefDiagnosticIssue",
    "build_advisory_operating_brief_diagnostic_issues",
]

_READINESS_BRANCH = "research_data_source_readiness"
_READINESS_SUMMARY_BRANCH = "research_data_source_readiness_summary"
_SOURCE_BRANCHES = (_READINESS_BRANCH, _READINESS_SUMMARY_BRANCH)
_ISSUE_CODE = "missing_diagnostic_controls"
_READINESS_MESSAGE = "Readiness branch reports missing diagnostic controls."
_READINESS_SUMMARY_MESSAGE = (
    "Readiness summary branch reports missing diagnostic controls."
)


@dataclass(frozen=True, slots=True)
class AdvisoryOperatingBriefDiagnosticIssue:
    """Plain advisory issue metadata derived from existing diagnostics."""

    source_branch: str
    issue_code: str
    issue_state: str
    diagnostic_message: str
    blocking_controls: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        source_branch = _source_branch(self.source_branch)
        object.__setattr__(self, "source_branch", source_branch)
        object.__setattr__(self, "issue_code", _issue_code(self.issue_code))
        object.__setattr__(
            self,
            "issue_state",
            _required_string(self.issue_state, "issue_state"),
        )
        object.__setattr__(
            self,
            "diagnostic_message",
            _required_string(self.diagnostic_message, "diagnostic_message"),
        )
        object.__setattr__(
            self,
            "blocking_controls",
            _string_tuple(
                self.blocking_controls,
                "blocking_controls",
                require_item=True,
            ),
        )
        object.__setattr__(
            self,
            "limitations",
            _string_tuple(self.limitations, "limitations", require_item=True),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only issue metadata."""

        return {
            "source_branch": self.source_branch,
            "issue_code": self.issue_code,
            "issue_state": self.issue_state,
            "diagnostic_message": self.diagnostic_message,
            "blocking_controls": list(self.blocking_controls),
            "limitations": list(self.limitations),
        }


def build_advisory_operating_brief_diagnostic_issues(
    content_bundle: AdvisoryOperatingBriefContentBundle,
) -> tuple[AdvisoryOperatingBriefDiagnosticIssue, ...]:
    """Build advisory issue records from existing content bundle diagnostics."""

    bundle = _content_bundle(content_bundle)
    issues: list[AdvisoryOperatingBriefDiagnosticIssue] = []

    for readiness in bundle.research_data_source_readiness:
        issues.extend(_readiness_issues(readiness))
    for summary in bundle.research_data_source_readiness_summaries:
        issues.extend(_readiness_summary_issues(summary))

    return tuple(issues)


def _readiness_issues(
    readiness: ResearchDataSourceReadiness,
) -> tuple[AdvisoryOperatingBriefDiagnosticIssue, ...]:
    if not readiness.missing_controls:
        return ()

    return (
        AdvisoryOperatingBriefDiagnosticIssue(
            source_branch=_READINESS_BRANCH,
            issue_code=_ISSUE_CODE,
            issue_state=readiness.readiness_state,
            diagnostic_message=_READINESS_MESSAGE,
            blocking_controls=readiness.missing_controls,
            limitations=readiness.limitations,
        ),
    )


def _readiness_summary_issues(
    summary: ResearchDataSourceReadinessSummary,
) -> tuple[AdvisoryOperatingBriefDiagnosticIssue, ...]:
    if summary.missing_control_count == 0:
        return ()

    return (
        AdvisoryOperatingBriefDiagnosticIssue(
            source_branch=_READINESS_SUMMARY_BRANCH,
            issue_code=_ISSUE_CODE,
            issue_state=summary.summary_state,
            diagnostic_message=_READINESS_SUMMARY_MESSAGE,
            blocking_controls=summary.source_readiness.missing_controls,
            limitations=summary.diagnostic_limitations,
        ),
    )


def _content_bundle(value: object) -> AdvisoryOperatingBriefContentBundle:
    if type(value) is not AdvisoryOperatingBriefContentBundle:
        raise ValidationError(
            "content_bundle must be an AdvisoryOperatingBriefContentBundle."
        )

    return value


def _source_branch(value: object) -> str:
    source_branch = _required_string(value, "source_branch")
    if source_branch in _SOURCE_BRANCHES:
        return source_branch

    raise ValidationError(
        "source_branch must be a supported advisory diagnostic branch."
    )


def _issue_code(value: object) -> str:
    issue_code = _required_string(value, "issue_code")
    if issue_code == _ISSUE_CODE:
        return issue_code

    raise ValidationError(
        "issue_code must be exactly missing_diagnostic_controls."
    )


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value


def _string_tuple(
    values: object,
    field_name: str,
    *,
    require_item: bool,
) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    if require_item and not items:
        raise ValidationError(f"{field_name} must contain at least one string.")

    for index, value in enumerate(items):
        _required_string(value, f"{field_name}[{index}]")

    return items
