"""Synthetic research data-source readiness fixture."""

import json

from algotrader.research.research_data_source_readiness import (
    ResearchDataSourceReadiness,
    build_research_data_source_readiness,
)

__all__ = [
    "expected_synthetic_research_data_source_readiness",
    "expected_synthetic_research_data_source_readiness_dict",
    "expected_synthetic_research_data_source_readiness_export_snapshot_dict",
    "expected_synthetic_research_data_source_readiness_export_snapshot_json",
    "expected_synthetic_research_data_source_readiness_json",
]


_REQUIRED_CONTROLS = (
    "terms_review_documented",
    "snapshot_provenance_defined",
    "redistribution_policy_reviewed",
    "adjustment_policy_defined",
    "fixture_policy_review_documented",
    "no_lookahead_protocol_defined",
)

_SATISFIED_CONTROLS = ("no_lookahead_protocol_defined",)

_EVIDENCE_REFS = (
    "synthetic_phase_271_readiness_fixture",
    "internal_control_gap_note",
)

_LIMITATIONS = (
    "Fixture is synthetic metadata only and not connected to real data.",
    "Fixture carries no observations, values, or external source content.",
)

_NON_CLAIMS = (
    "no source approval",
    "no data ingestion approval",
    "no trading authority",
    "no capital authority",
    "no data-source authorization",
)


def expected_synthetic_research_data_source_readiness() -> (
    ResearchDataSourceReadiness
):
    """Return the pinned synthetic readiness contract."""

    return build_research_data_source_readiness(
        source_id="synthetic-broad-etf-source-candidate",
        source_name="Synthetic broad ETF source candidate",
        asset_class_scope=("equity_etf",),
        intended_use="pipeline_validation_only",
        readiness_state="candidate_only",
        required_controls=_REQUIRED_CONTROLS,
        satisfied_controls=_SATISFIED_CONTROLS,
        evidence_refs=_EVIDENCE_REFS,
        limitations=_LIMITATIONS,
        non_claims=_NON_CLAIMS,
    )


def expected_synthetic_research_data_source_readiness_dict() -> (
    dict[str, object]
):
    """Return the synthetic readiness contract as primitive metadata."""

    return expected_synthetic_research_data_source_readiness().to_dict()


def expected_synthetic_research_data_source_readiness_json() -> str:
    """Return compact sorted-key JSON for the synthetic readiness contract."""

    payload = expected_synthetic_research_data_source_readiness_dict()

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def expected_synthetic_research_data_source_readiness_export_snapshot_dict() -> (
    dict[str, object]
):
    """Return the synthetic readiness export snapshot as primitive metadata."""

    return expected_synthetic_research_data_source_readiness_dict()


def expected_synthetic_research_data_source_readiness_export_snapshot_json() -> str:
    """Return compact sorted-key JSON for the synthetic export snapshot."""

    payload = expected_synthetic_research_data_source_readiness_export_snapshot_dict()

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
