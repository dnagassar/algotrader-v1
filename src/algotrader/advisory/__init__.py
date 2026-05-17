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

__all__ = [
    "AdvisoryLabel",
    "OperatingBrief",
    "ResearchCandidateDossier",
    "RiskAuthorityStatus",
    "StrategyEligibilityStatus",
    "render_operating_brief_markdown",
]
