"""Synthetic broad ETF research-scope fixture for tests and documentation."""

from __future__ import annotations

from datetime import date

from algotrader.research.research_scope import (
    ResearchBenchmarkCandidate,
    ResearchCashProxyCandidate,
    ResearchDataSourceCandidate,
    ResearchScopeSnapshot,
    ResearchUniverseCandidate,
)

__all__ = [
    "build_synthetic_broad_etf_research_scope",
    "expected_synthetic_broad_etf_research_scope_dict",
    "expected_synthetic_broad_etf_research_scope_json",
]


_NON_CLAIMS = (
    "not source approval",
    "not universe approval",
    "not benchmark approval",
    "not cash proxy approval",
    "not strategy validation",
    "not signal approval",
    "not trading authority",
    "no broker/order/fill/portfolio/runtime behavior",
    "no real data ingestion",
)


def build_synthetic_broad_etf_research_scope() -> ResearchScopeSnapshot:
    """Return a deterministic candidate-only broad ETF research scope."""

    return ResearchScopeSnapshot(
        scope_id="synthetic_broad_etf_research_scope_snapshot_candidate",
        as_of_date=date(2026, 1, 18),
        approval_state="candidate_only",
        source_candidates=(
            ResearchDataSourceCandidate(
                source_id="synthetic_broad_etf_metadata_source_candidate",
                source_name="Synthetic broad ETF metadata source candidate",
                source_type="synthetic",
                approval_state="candidate_only",
                data_kind="synthetic research-scope metadata only",
                terms_status="terms review absent for this fixture",
                storage_policy="metadata fixture only",
                adjustment_policy="adjustment review absent for this fixture",
                revision_policy="revision review absent for this fixture",
                blockers=(
                    "Source terms review is incomplete.",
                    "Acquisition-path review is incomplete.",
                ),
                limitations=(
                    "Contains only metadata labels for deterministic tests.",
                    "Does not identify any external source.",
                ),
                required_follow_up=(
                    "Review source terms before any use beyond this fixture.",
                ),
                non_claims=_NON_CLAIMS,
            ),
        ),
        universe_candidates=(
            ResearchUniverseCandidate(
                universe_id="synthetic_broad_etf_universe_candidate",
                universe_name="Synthetic broad ETF universe candidate",
                universe_type="broad_etf_candidate",
                approval_state="candidate_only",
                asset_ids=(
                    "synthetic_us_equity_etf_candidate",
                    "synthetic_developed_ex_us_etf_candidate",
                    "synthetic_emerging_market_etf_candidate",
                    "synthetic_treasury_duration_etf_candidate",
                ),
                inclusion_rules=(
                    "Use only the four synthetic asset ids listed in this fixture.",
                ),
                exclusion_rules=(
                    "Exclude real listings, issuers, observations, and external identifiers.",
                ),
                survivorship_policy="survivorship review absent for this fixture",
                inception_policy="inception review absent for this fixture",
                delisting_policy="delisting review absent for this fixture",
                blockers=(
                    "Universe membership review is incomplete.",
                    "Lifecycle policy review is incomplete.",
                ),
                limitations=(
                    "Synthetic asset ids do not represent tradable instruments.",
                    "No membership methodology is selected.",
                ),
                required_follow_up=(
                    "Define and review universe methodology before any research use.",
                ),
                non_claims=_NON_CLAIMS,
            ),
        ),
        benchmark_candidates=(
            ResearchBenchmarkCandidate(
                benchmark_id="synthetic_broad_etf_benchmark_candidate",
                benchmark_name="Synthetic broad ETF benchmark candidate",
                benchmark_type="synthetic",
                approval_state="candidate_only",
                return_basis="not computed; comparison basis review is incomplete",
                comparison_role="placeholder comparison metadata only",
                blockers=(
                    "Benchmark definition review is incomplete.",
                    "Comparison-basis review is incomplete.",
                ),
                limitations=(
                    "No index, fund, level, or observation data is included.",
                    "No comparison methodology is selected.",
                ),
                required_follow_up=(
                    "Select and review benchmark methodology before any comparison.",
                ),
                non_claims=_NON_CLAIMS,
            ),
        ),
        cash_proxy_candidates=(
            ResearchCashProxyCandidate(
                cash_proxy_id="synthetic_cash_proxy_candidate",
                cash_proxy_name="Synthetic cash proxy candidate",
                cash_proxy_type="synthetic",
                approval_state="candidate_only",
                return_basis="not computed; cash basis review is incomplete",
                availability_policy="placeholder availability metadata only",
                blockers=(
                    "Cash proxy definition review is incomplete.",
                    "Availability review is incomplete.",
                ),
                limitations=(
                    "No yield, fund, or observation data is included.",
                    "No cash treatment methodology is selected.",
                ),
                required_follow_up=(
                    "Select and review cash proxy treatment before any comparison.",
                ),
                non_claims=_NON_CLAIMS,
            ),
        ),
        blockers=(
            "Every candidate review remains incomplete.",
            "No data acquisition, methodology, or operational path is selected.",
        ),
        limitations=(
            "Fixture is for tests and documentation only.",
            "Contains no external observations or tradable identifiers.",
        ),
        required_follow_up=(
            "Review each candidate contract before any research or operational use.",
        ),
        non_claims=_NON_CLAIMS,
    )


def expected_synthetic_broad_etf_research_scope_dict() -> dict[str, object]:
    """Return the pinned primitive payload for the synthetic scope fixture."""

    return {
        "scope_id": "synthetic_broad_etf_research_scope_snapshot_candidate",
        "as_of_date": "2026-01-18",
        "approval_state": "candidate_only",
        "source_candidates": [
            {
                "source_id": "synthetic_broad_etf_metadata_source_candidate",
                "source_name": "Synthetic broad ETF metadata source candidate",
                "source_type": "synthetic",
                "approval_state": "candidate_only",
                "data_kind": "synthetic research-scope metadata only",
                "terms_status": "terms review absent for this fixture",
                "storage_policy": "metadata fixture only",
                "adjustment_policy": "adjustment review absent for this fixture",
                "revision_policy": "revision review absent for this fixture",
                "blockers": [
                    "Source terms review is incomplete.",
                    "Acquisition-path review is incomplete.",
                ],
                "limitations": [
                    "Contains only metadata labels for deterministic tests.",
                    "Does not identify any external source.",
                ],
                "required_follow_up": [
                    "Review source terms before any use beyond this fixture.",
                ],
                "non_claims": list(_NON_CLAIMS),
            },
        ],
        "universe_candidates": [
            {
                "universe_id": "synthetic_broad_etf_universe_candidate",
                "universe_name": "Synthetic broad ETF universe candidate",
                "universe_type": "broad_etf_candidate",
                "approval_state": "candidate_only",
                "asset_ids": [
                    "synthetic_us_equity_etf_candidate",
                    "synthetic_developed_ex_us_etf_candidate",
                    "synthetic_emerging_market_etf_candidate",
                    "synthetic_treasury_duration_etf_candidate",
                ],
                "inclusion_rules": [
                    "Use only the four synthetic asset ids listed in this fixture.",
                ],
                "exclusion_rules": [
                    "Exclude real listings, issuers, observations, and external identifiers.",
                ],
                "survivorship_policy": "survivorship review absent for this fixture",
                "inception_policy": "inception review absent for this fixture",
                "delisting_policy": "delisting review absent for this fixture",
                "blockers": [
                    "Universe membership review is incomplete.",
                    "Lifecycle policy review is incomplete.",
                ],
                "limitations": [
                    "Synthetic asset ids do not represent tradable instruments.",
                    "No membership methodology is selected.",
                ],
                "required_follow_up": [
                    "Define and review universe methodology before any research use.",
                ],
                "non_claims": list(_NON_CLAIMS),
            },
        ],
        "benchmark_candidates": [
            {
                "benchmark_id": "synthetic_broad_etf_benchmark_candidate",
                "benchmark_name": "Synthetic broad ETF benchmark candidate",
                "benchmark_type": "synthetic",
                "approval_state": "candidate_only",
                "return_basis": "not computed; comparison basis review is incomplete",
                "comparison_role": "placeholder comparison metadata only",
                "blockers": [
                    "Benchmark definition review is incomplete.",
                    "Comparison-basis review is incomplete.",
                ],
                "limitations": [
                    "No index, fund, level, or observation data is included.",
                    "No comparison methodology is selected.",
                ],
                "required_follow_up": [
                    "Select and review benchmark methodology before any comparison.",
                ],
                "non_claims": list(_NON_CLAIMS),
            },
        ],
        "cash_proxy_candidates": [
            {
                "cash_proxy_id": "synthetic_cash_proxy_candidate",
                "cash_proxy_name": "Synthetic cash proxy candidate",
                "cash_proxy_type": "synthetic",
                "approval_state": "candidate_only",
                "return_basis": "not computed; cash basis review is incomplete",
                "availability_policy": "placeholder availability metadata only",
                "blockers": [
                    "Cash proxy definition review is incomplete.",
                    "Availability review is incomplete.",
                ],
                "limitations": [
                    "No yield, fund, or observation data is included.",
                    "No cash treatment methodology is selected.",
                ],
                "required_follow_up": [
                    "Select and review cash proxy treatment before any comparison.",
                ],
                "non_claims": list(_NON_CLAIMS),
            },
        ],
        "blockers": [
            "Every candidate review remains incomplete.",
            "No data acquisition, methodology, or operational path is selected.",
        ],
        "limitations": [
            "Fixture is for tests and documentation only.",
            "Contains no external observations or tradable identifiers.",
        ],
        "required_follow_up": [
            "Review each candidate contract before any research or operational use.",
        ],
        "non_claims": list(_NON_CLAIMS),
    }


def expected_synthetic_broad_etf_research_scope_json() -> str:
    """Return the pinned compact JSON payload for the synthetic scope fixture."""

    return _EXPECTED_SYNTHETIC_BROAD_ETF_RESEARCH_SCOPE_JSON


_EXPECTED_SYNTHETIC_BROAD_ETF_RESEARCH_SCOPE_JSON = (
    '{"scope_id":"synthetic_broad_etf_research_scope_snapshot_candidate",'
    '"as_of_date":"2026-01-18","approval_state":"candidate_only",'
    '"source_candidates":[{"source_id":"synthetic_broad_etf_metadata_source_candidate",'
    '"source_name":"Synthetic broad ETF metadata source candidate","source_type":"synthetic",'
    '"approval_state":"candidate_only","data_kind":"synthetic research-scope metadata only",'
    '"terms_status":"terms review absent for this fixture",'
    '"storage_policy":"metadata fixture only",'
    '"adjustment_policy":"adjustment review absent for this fixture",'
    '"revision_policy":"revision review absent for this fixture",'
    '"blockers":["Source terms review is incomplete.",'
    '"Acquisition-path review is incomplete."],'
    '"limitations":["Contains only metadata labels for deterministic tests.",'
    '"Does not identify any external source."],'
    '"required_follow_up":["Review source terms before any use beyond this fixture."],'
    '"non_claims":["not source approval","not universe approval",'
    '"not benchmark approval","not cash proxy approval","not strategy validation",'
    '"not signal approval","not trading authority",'
    '"no broker/order/fill/portfolio/runtime behavior","no real data ingestion"]}],'
    '"universe_candidates":[{"universe_id":"synthetic_broad_etf_universe_candidate",'
    '"universe_name":"Synthetic broad ETF universe candidate",'
    '"universe_type":"broad_etf_candidate","approval_state":"candidate_only",'
    '"asset_ids":["synthetic_us_equity_etf_candidate",'
    '"synthetic_developed_ex_us_etf_candidate",'
    '"synthetic_emerging_market_etf_candidate",'
    '"synthetic_treasury_duration_etf_candidate"],'
    '"inclusion_rules":["Use only the four synthetic asset ids listed in this fixture."],'
    '"exclusion_rules":["Exclude real listings, issuers, observations, and external identifiers."],'
    '"survivorship_policy":"survivorship review absent for this fixture",'
    '"inception_policy":"inception review absent for this fixture",'
    '"delisting_policy":"delisting review absent for this fixture",'
    '"blockers":["Universe membership review is incomplete.",'
    '"Lifecycle policy review is incomplete."],'
    '"limitations":["Synthetic asset ids do not represent tradable instruments.",'
    '"No membership methodology is selected."],'
    '"required_follow_up":["Define and review universe methodology before any research use."],'
    '"non_claims":["not source approval","not universe approval",'
    '"not benchmark approval","not cash proxy approval","not strategy validation",'
    '"not signal approval","not trading authority",'
    '"no broker/order/fill/portfolio/runtime behavior","no real data ingestion"]}],'
    '"benchmark_candidates":[{"benchmark_id":"synthetic_broad_etf_benchmark_candidate",'
    '"benchmark_name":"Synthetic broad ETF benchmark candidate","benchmark_type":"synthetic",'
    '"approval_state":"candidate_only",'
    '"return_basis":"not computed; comparison basis review is incomplete",'
    '"comparison_role":"placeholder comparison metadata only",'
    '"blockers":["Benchmark definition review is incomplete.",'
    '"Comparison-basis review is incomplete."],'
    '"limitations":["No index, fund, level, or observation data is included.",'
    '"No comparison methodology is selected."],'
    '"required_follow_up":["Select and review benchmark methodology before any comparison."],'
    '"non_claims":["not source approval","not universe approval",'
    '"not benchmark approval","not cash proxy approval","not strategy validation",'
    '"not signal approval","not trading authority",'
    '"no broker/order/fill/portfolio/runtime behavior","no real data ingestion"]}],'
    '"cash_proxy_candidates":[{"cash_proxy_id":"synthetic_cash_proxy_candidate",'
    '"cash_proxy_name":"Synthetic cash proxy candidate","cash_proxy_type":"synthetic",'
    '"approval_state":"candidate_only",'
    '"return_basis":"not computed; cash basis review is incomplete",'
    '"availability_policy":"placeholder availability metadata only",'
    '"blockers":["Cash proxy definition review is incomplete.",'
    '"Availability review is incomplete."],'
    '"limitations":["No yield, fund, or observation data is included.",'
    '"No cash treatment methodology is selected."],'
    '"required_follow_up":["Select and review cash proxy treatment before any comparison."],'
    '"non_claims":["not source approval","not universe approval",'
    '"not benchmark approval","not cash proxy approval","not strategy validation",'
    '"not signal approval","not trading authority",'
    '"no broker/order/fill/portfolio/runtime behavior","no real data ingestion"]}],'
    '"blockers":["Every candidate review remains incomplete.",'
    '"No data acquisition, methodology, or operational path is selected."],'
    '"limitations":["Fixture is for tests and documentation only.",'
    '"Contains no external observations or tradable identifiers."],'
    '"required_follow_up":["Review each candidate contract before any research or operational use."],'
    '"non_claims":["not source approval","not universe approval","not benchmark approval",'
    '"not cash proxy approval","not strategy validation","not signal approval",'
    '"not trading authority","no broker/order/fill/portfolio/runtime behavior",'
    '"no real data ingestion"]}'
)
