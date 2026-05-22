"""Synthetic return-input research result fixture."""

from __future__ import annotations

from algotrader.research.replay_result import SyntheticResearchResult
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
    "build_synthetic_return_input_research_result",
    "expected_synthetic_return_input_research_result_dict",
]


def build_synthetic_return_input_research_result() -> SyntheticResearchResult:
    """Return the deterministic synthetic result built from return-input support."""

    snapshot = build_synthetic_research_return_input_snapshot()
    package = build_research_return_input_package(snapshot)
    return build_synthetic_research_result_from_return_input_package(package)


def expected_synthetic_return_input_research_result_dict() -> dict[str, object]:
    """Return the stable primitive result payload emitted by the result contract."""

    return build_synthetic_return_input_research_result().to_dict()
