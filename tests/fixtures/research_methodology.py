"""Synthetic broad ETF research-methodology scope fixture."""

from __future__ import annotations

from datetime import date

from algotrader.research.research_methodology import (
    ResearchMethodologyCandidate,
    ResearchMethodologyScopeSnapshot,
    ResearchParameterSetCandidate,
)

__all__ = [
    "build_synthetic_broad_etf_methodology_scope",
    "expected_synthetic_broad_etf_methodology_scope_dict",
    "expected_synthetic_broad_etf_methodology_scope_json",
]


_LINKED_SYNTHETIC_RESEARCH_SCOPE_ID = (
    "synthetic_broad_etf_research_scope_snapshot_candidate"
)

_METHODOLOGY_ID = "synthetic_broad_etf_moving_average_trend_methodology_candidate"
_PARAMETER_SET_ID = "synthetic_broad_etf_single_window_parameter_set_candidate"

_NON_CLAIMS = (
    "not methodology approval",
    "not parameter approval",
    "not evidence approval",
    "not strategy validation",
    "not signal approval",
    "not evaluator approval",
    "not trading authority",
    "no broker/order/fill/portfolio/runtime behavior",
    "no real data ingestion",
    "no source/universe/benchmark/cash proxy approval",
)


def build_synthetic_broad_etf_methodology_scope() -> (
    ResearchMethodologyScopeSnapshot
):
    """Return a deterministic candidate-only methodology-scope fixture."""

    methodology = ResearchMethodologyCandidate(
        methodology_id=_METHODOLOGY_ID,
        methodology_name="Synthetic broad ETF moving-average methodology candidate",
        methodology_type="moving_average_trend_candidate",
        approval_state="candidate_only",
        rule_family="simple_moving_average_candidate",
        rule_description=(
            "Metadata-only candidate for comparing synthetic observations with a "
            "trailing simple moving-average window."
        ),
        cadence_policy="synthetic_only",
        action_timing_policy="synthetic_previous_exposure",
        lookahead_policy="synthetic_no_lookahead",
        return_construction_policy=(
            "synthetic convention placeholder with no calculation selected"
        ),
        adjustment_policy="synthetic adjustment placeholder only",
        cost_policy="synthetic_cost_candidate",
        linked_scope_ids=(_LINKED_SYNTHETIC_RESEARCH_SCOPE_ID,),
        evidence_refs=("synthetic_phase_75_methodology_scope_fixture",),
        blockers=(
            "Methodology evidence review is incomplete.",
            "Scope linkage review remains metadata-only.",
        ),
        limitations=(
            "Contains only synthetic methodology metadata for deterministic tests.",
            "Does not compute research outcomes.",
        ),
        required_follow_up=(
            "Complete methodology evidence and as-of protocol review before research use.",
        ),
        non_claims=_NON_CLAIMS,
    )
    parameter_set = ResearchParameterSetCandidate(
        parameter_set_id=_PARAMETER_SET_ID,
        methodology_id=methodology.methodology_id,
        parameter_set_name="Synthetic broad ETF single-window parameter candidate",
        parameter_type="single_window_candidate",
        approval_state="candidate_only",
        moving_average_windows=(200,),
        cadence_policy="synthetic_only",
        action_timing_policy="synthetic_previous_exposure",
        comparison_rule="value_gt_moving_average",
        cost_assumption_policy="synthetic_cost_candidate",
        sensitivity_notes=(
            "Single synthetic 200-window candidate only; sensitivity grid is unresolved.",
        ),
        blockers=(
            "Parameter evidence review is incomplete.",
            "Sensitivity review is incomplete.",
        ),
        limitations=(
            "Window value is synthetic metadata only.",
            "No robustness analysis is included.",
        ),
        required_follow_up=(
            "Review parameter evidence and sensitivity plan before research use.",
        ),
        non_claims=_NON_CLAIMS,
    )

    return ResearchMethodologyScopeSnapshot(
        methodology_scope_id=(
            "synthetic_broad_etf_methodology_scope_snapshot_candidate"
        ),
        as_of_date=date(2026, 1, 19),
        approval_state="candidate_only",
        methodology_candidates=(methodology,),
        parameter_set_candidates=(parameter_set,),
        blockers=(
            "Methodology and parameter reviews are incomplete.",
            "Linked research scope is referenced by synthetic id only.",
        ),
        limitations=(
            "Snapshot contains redistribution-safe synthetic metadata only.",
            "It does not include external observations or operational instructions.",
        ),
        required_follow_up=(
            "Complete methodology, parameter, and scope reviews before research use.",
        ),
        non_claims=_NON_CLAIMS,
    )


def expected_synthetic_broad_etf_methodology_scope_dict() -> dict[str, object]:
    """Return the pinned primitive payload for the synthetic methodology scope."""

    return {
        "methodology_scope_id": (
            "synthetic_broad_etf_methodology_scope_snapshot_candidate"
        ),
        "as_of_date": "2026-01-19",
        "approval_state": "candidate_only",
        "methodology_candidates": [
            {
                "methodology_id": _METHODOLOGY_ID,
                "methodology_name": (
                    "Synthetic broad ETF moving-average methodology candidate"
                ),
                "methodology_type": "moving_average_trend_candidate",
                "approval_state": "candidate_only",
                "rule_family": "simple_moving_average_candidate",
                "rule_description": (
                    "Metadata-only candidate for comparing synthetic observations with a "
                    "trailing simple moving-average window."
                ),
                "cadence_policy": "synthetic_only",
                "action_timing_policy": "synthetic_previous_exposure",
                "lookahead_policy": "synthetic_no_lookahead",
                "return_construction_policy": (
                    "synthetic convention placeholder with no calculation selected"
                ),
                "adjustment_policy": "synthetic adjustment placeholder only",
                "cost_policy": "synthetic_cost_candidate",
                "linked_scope_ids": [_LINKED_SYNTHETIC_RESEARCH_SCOPE_ID],
                "evidence_refs": [
                    "synthetic_phase_75_methodology_scope_fixture",
                ],
                "blockers": [
                    "Methodology evidence review is incomplete.",
                    "Scope linkage review remains metadata-only.",
                ],
                "limitations": [
                    "Contains only synthetic methodology metadata for deterministic tests.",
                    "Does not compute research outcomes.",
                ],
                "required_follow_up": [
                    (
                        "Complete methodology evidence and as-of protocol review "
                        "before research use."
                    ),
                ],
                "non_claims": list(_NON_CLAIMS),
            },
        ],
        "parameter_set_candidates": [
            {
                "parameter_set_id": _PARAMETER_SET_ID,
                "methodology_id": _METHODOLOGY_ID,
                "parameter_set_name": (
                    "Synthetic broad ETF single-window parameter candidate"
                ),
                "parameter_type": "single_window_candidate",
                "approval_state": "candidate_only",
                "moving_average_windows": [200],
                "cadence_policy": "synthetic_only",
                "action_timing_policy": "synthetic_previous_exposure",
                "comparison_rule": "value_gt_moving_average",
                "cost_assumption_policy": "synthetic_cost_candidate",
                "sensitivity_notes": [
                    (
                        "Single synthetic 200-window candidate only; sensitivity "
                        "grid is unresolved."
                    ),
                ],
                "blockers": [
                    "Parameter evidence review is incomplete.",
                    "Sensitivity review is incomplete.",
                ],
                "limitations": [
                    "Window value is synthetic metadata only.",
                    "No robustness analysis is included.",
                ],
                "required_follow_up": [
                    "Review parameter evidence and sensitivity plan before research use.",
                ],
                "non_claims": list(_NON_CLAIMS),
            },
        ],
        "blockers": [
            "Methodology and parameter reviews are incomplete.",
            "Linked research scope is referenced by synthetic id only.",
        ],
        "limitations": [
            "Snapshot contains redistribution-safe synthetic metadata only.",
            "It does not include external observations or operational instructions.",
        ],
        "required_follow_up": [
            "Complete methodology, parameter, and scope reviews before research use.",
        ],
        "non_claims": list(_NON_CLAIMS),
    }


def expected_synthetic_broad_etf_methodology_scope_json() -> str:
    """Return the pinned compact JSON payload for the synthetic methodology scope."""

    return _EXPECTED_SYNTHETIC_BROAD_ETF_METHODOLOGY_SCOPE_JSON


_EXPECTED_SYNTHETIC_BROAD_ETF_METHODOLOGY_SCOPE_JSON = (
    '{"methodology_scope_id":"synthetic_broad_etf_methodology_scope_snapshot_candidate",'
    '"as_of_date":"2026-01-19","approval_state":"candidate_only",'
    '"methodology_candidates":[{"methodology_id":'
    '"synthetic_broad_etf_moving_average_trend_methodology_candidate",'
    '"methodology_name":"Synthetic broad ETF moving-average methodology candidate",'
    '"methodology_type":"moving_average_trend_candidate",'
    '"approval_state":"candidate_only",'
    '"rule_family":"simple_moving_average_candidate",'
    '"rule_description":"Metadata-only candidate for comparing synthetic observations '
    'with a trailing simple moving-average window.",'
    '"cadence_policy":"synthetic_only",'
    '"action_timing_policy":"synthetic_previous_exposure",'
    '"lookahead_policy":"synthetic_no_lookahead",'
    '"return_construction_policy":"synthetic convention placeholder with no '
    'calculation selected",'
    '"adjustment_policy":"synthetic adjustment placeholder only",'
    '"cost_policy":"synthetic_cost_candidate",'
    '"linked_scope_ids":["synthetic_broad_etf_research_scope_snapshot_candidate"],'
    '"evidence_refs":["synthetic_phase_75_methodology_scope_fixture"],'
    '"blockers":["Methodology evidence review is incomplete.",'
    '"Scope linkage review remains metadata-only."],'
    '"limitations":["Contains only synthetic methodology metadata for deterministic '
    'tests.","Does not compute research outcomes."],'
    '"required_follow_up":["Complete methodology evidence and as-of protocol review '
    'before research use."],'
    '"non_claims":["not methodology approval","not parameter approval",'
    '"not evidence approval","not strategy validation","not signal approval",'
    '"not evaluator approval","not trading authority",'
    '"no broker/order/fill/portfolio/runtime behavior","no real data ingestion",'
    '"no source/universe/benchmark/cash proxy approval"]}],'
    '"parameter_set_candidates":[{"parameter_set_id":'
    '"synthetic_broad_etf_single_window_parameter_set_candidate",'
    '"methodology_id":"synthetic_broad_etf_moving_average_trend_methodology_candidate",'
    '"parameter_set_name":"Synthetic broad ETF single-window parameter candidate",'
    '"parameter_type":"single_window_candidate","approval_state":"candidate_only",'
    '"moving_average_windows":[200],"cadence_policy":"synthetic_only",'
    '"action_timing_policy":"synthetic_previous_exposure",'
    '"comparison_rule":"value_gt_moving_average",'
    '"cost_assumption_policy":"synthetic_cost_candidate",'
    '"sensitivity_notes":["Single synthetic 200-window candidate only; sensitivity '
    'grid is unresolved."],'
    '"blockers":["Parameter evidence review is incomplete.",'
    '"Sensitivity review is incomplete."],'
    '"limitations":["Window value is synthetic metadata only.",'
    '"No robustness analysis is included."],'
    '"required_follow_up":["Review parameter evidence and sensitivity plan before '
    'research use."],'
    '"non_claims":["not methodology approval","not parameter approval",'
    '"not evidence approval","not strategy validation","not signal approval",'
    '"not evaluator approval","not trading authority",'
    '"no broker/order/fill/portfolio/runtime behavior","no real data ingestion",'
    '"no source/universe/benchmark/cash proxy approval"]}],'
    '"blockers":["Methodology and parameter reviews are incomplete.",'
    '"Linked research scope is referenced by synthetic id only."],'
    '"limitations":["Snapshot contains redistribution-safe synthetic metadata only.",'
    '"It does not include external observations or operational instructions."],'
    '"required_follow_up":["Complete methodology, parameter, and scope reviews before '
    'research use."],'
    '"non_claims":["not methodology approval","not parameter approval",'
    '"not evidence approval","not strategy validation","not signal approval",'
    '"not evaluator approval","not trading authority",'
    '"no broker/order/fill/portfolio/runtime behavior","no real data ingestion",'
    '"no source/universe/benchmark/cash proxy approval"]}'
)
