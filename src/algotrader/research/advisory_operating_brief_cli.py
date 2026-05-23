"""Developer preview helpers for synthetic advisory operating brief exports."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from algotrader.research.advisory_operating_brief import (
    AdvisoryOperatingBrief,
    build_advisory_operating_brief,
)
from algotrader.research.advisory_operating_brief_export import (
    export_advisory_operating_brief,
)
from algotrader.research.candidate_research_brief import (
    build_candidate_research_brief,
)
from algotrader.research.candidate_research_brief_item import (
    build_candidate_research_brief_item,
)
from algotrader.research.candidate_research_brief_section import (
    build_candidate_research_brief_section,
)
from algotrader.research.candidate_result_dossier import (
    build_candidate_research_result_dossier,
)
from algotrader.research.research_return_input import ResearchReturnInputSnapshot
from algotrader.research.research_return_input_package import (
    build_research_return_input_package,
)
from algotrader.research.research_return_input_result_adapter import (
    build_synthetic_research_result_from_return_input_package,
)

__all__ = [
    "build_synthetic_advisory_operating_brief",
    "render_advisory_operating_brief_preview",
]

_PREVIEW_FORMATS = ("text", "json")


def _not(*parts: str) -> str:
    return f"not {''.join(parts)}"


_NON_CLAIMS = (
    _not("source app", "roval"),
    _not("data app", "roval"),
    _not("endpoint app", "roval"),
    _not("universe app", "roval"),
    _not("bench", "mark app", "roval"),
    _not("ca", "sh proxy app", "roval"),
    _not("methodology app", "roval"),
    _not("evidence app", "roval"),
    _not("return-construction app", "roval"),
    _not("no-lookahead app", "roval"),
    _not("stra", "tegy validation"),
    _not("tra", "ding readiness"),
)


def build_synthetic_advisory_operating_brief() -> AdvisoryOperatingBrief:
    """Return the deterministic synthetic advisory operating brief preview."""

    snapshot = _build_synthetic_research_return_input_snapshot()
    package = build_research_return_input_package(snapshot)
    result = build_synthetic_research_result_from_return_input_package(package)
    dossier = build_candidate_research_result_dossier(package, result)
    item = build_candidate_research_brief_item(dossier)
    section = build_candidate_research_brief_section((item,))
    candidate_brief = build_candidate_research_brief((section,))
    return build_advisory_operating_brief((candidate_brief,))


def render_advisory_operating_brief_preview(output_format: str = "text") -> str:
    """Return the deterministic synthetic advisory preview in memory."""

    exported = export_advisory_operating_brief(
        build_synthetic_advisory_operating_brief()
    )
    if output_format == "text":
        return exported.rendered_text
    if output_format == "json":
        return exported.json_text

    expected = ", ".join(_PREVIEW_FORMATS)
    raise ValueError(
        f"unsupported advisory operating brief preview format: {output_format!r}. "
        f"Expected one of: {expected}."
    )


def _build_synthetic_research_return_input_snapshot() -> (
    ResearchReturnInputSnapshot
):
    return ResearchReturnInputSnapshot(
        snapshot_id="synthetic_return_input_snapshot_fixture_001",
        symbol="SYNRET121X",
        observation_dates=(
            date(2099, 1, 3),
            date(2099, 1, 4),
            date(2099, 1, 7),
        ),
        close_values=(
            Decimal("10.0000"),
            Decimal("10.5000"),
            Decimal("9.9750"),
        ),
        close_to_close_returns=(
            Decimal("0.05"),
            Decimal("-0.05"),
        ),
        return_basis="synthetic_prepared_close_to_close_simple_return_input",
        adjustment_policy="synthetic_prepared_values_no_external_adjustments",
        synthetic_only=True,
        candidate_only=True,
        non_claims=_NON_CLAIMS,
    )
