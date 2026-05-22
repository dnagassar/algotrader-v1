"""Synthetic candidate research result dossier fixture."""

from __future__ import annotations

from algotrader.research.candidate_result_dossier import (
    CandidateResearchResultDossier,
    build_candidate_research_result_dossier,
)
from algotrader.research.research_return_input_package import (
    build_research_return_input_package,
)
from algotrader.research.research_return_input_result_adapter import (
    build_synthetic_research_result_from_return_input_package,
)
from tests.fixtures.research_return_input import (
    build_synthetic_research_return_input_snapshot,
)

__all__ = [
    "build_synthetic_candidate_research_result_dossier",
    "expected_synthetic_candidate_research_result_dossier_dict",
]


def build_synthetic_candidate_research_result_dossier() -> (
    CandidateResearchResultDossier
):
    """Return the deterministic synthetic candidate result dossier."""

    snapshot = build_synthetic_research_return_input_snapshot()
    package = build_research_return_input_package(snapshot)
    result = build_synthetic_research_result_from_return_input_package(package)
    return build_candidate_research_result_dossier(package, result)


def expected_synthetic_candidate_research_result_dossier_dict() -> (
    dict[str, object]
):
    """Return the stable primitive dossier payload emitted by the contract."""

    return build_synthetic_candidate_research_result_dossier().to_dict()
