"""Advisory-only metadata contracts."""

from algotrader.advisory.candidate_dossier_adapter import (
    candidate_snapshot_to_research_candidate_dossier,
)
from algotrader.advisory.candidate_snapshot import CandidateDossierSnapshot
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
    "CandidateDossierSnapshot",
    "OperatingBrief",
    "OperatingBriefBoardSummary",
    "ResearchCandidateDossier",
    "RiskAuthorityStatus",
    "StrategyEligibilityStatus",
    "build_operating_brief_board_summary",
    "candidate_snapshot_to_research_candidate_dossier",
    "risk_authority_snapshot_to_risk_authority_status",
    "render_operating_brief_board_summary_markdown",
    "render_operating_brief_markdown",
    "strategy_mandate_snapshot_to_strategy_eligibility_status",
]
