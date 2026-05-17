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
from algotrader.advisory.operating_brief_summary_markdown import (
    render_operating_brief_board_summary_markdown,
)
from algotrader.advisory.governance_status_adapter import (
    risk_authority_snapshot_to_risk_authority_status,
    strategy_mandate_snapshot_to_strategy_eligibility_status,
)

__all__ = [
    "AdvisoryLabel",
    "OperatingBrief",
    "OperatingBriefBoardSummary",
    "ResearchCandidateDossier",
    "RiskAuthorityStatus",
    "StrategyEligibilityStatus",
    "build_operating_brief_board_summary",
    "risk_authority_snapshot_to_risk_authority_status",
    "render_operating_brief_board_summary_markdown",
    "render_operating_brief_markdown",
    "strategy_mandate_snapshot_to_strategy_eligibility_status",
]
