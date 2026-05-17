"""Advisory-only metadata contracts."""

from algotrader.advisory.operating_brief import (
    AdvisoryLabel,
    OperatingBrief,
    ResearchCandidateDossier,
    RiskAuthorityStatus,
    StrategyEligibilityStatus,
)
from algotrader.advisory.operating_brief_markdown import (
    render_operating_brief_markdown,
)
from algotrader.advisory.operating_brief_summary import (
    OperatingBriefBoardSummary,
    build_operating_brief_board_summary,
)

__all__ = [
    "AdvisoryLabel",
    "OperatingBrief",
    "OperatingBriefBoardSummary",
    "ResearchCandidateDossier",
    "RiskAuthorityStatus",
    "StrategyEligibilityStatus",
    "build_operating_brief_board_summary",
    "render_operating_brief_markdown",
]
