# Phase 97 - FRED Candidate Series Intake Plan

## Purpose

This document defines a narrow docs-only intake plan for reviewing possible
FRED benchmark, cash, or rate series later.

It defines how candidate FRED series would be evaluated before any future use.
It does not select a series, approve a series, call FRED, browse FRED pages,
download data, create data files, add credentials, change production code, or
change tests.

## Boundary

Phase 97 may define FRED series intake requirements only.

It must not approve:

- FRED
- any FRED series
- any benchmark
- any cash proxy
- any rate source
- any data
- any source
- any methodology
- any parameter set
- any evidence
- any return-construction policy
- any no-lookahead policy
- any strategy validation
- any trading use

FRED candidate-series intake is a review process only. A completed intake
record would still be non-approving unless a later explicit approval phase
selects a series and resolves source, rights, timing, conversion, missing-data,
return-construction, and no-lookahead questions.

## Candidate Series Roles

Future FRED candidate records must label the intended role without treating the
role as approval.

Allowed candidate roles include:

- `cash_risk_free_proxy_candidate`: a possible future cash or risk-free proxy
  candidate for later review only.
- `t_bill_proxy_candidate`: a possible Treasury bill-like proxy candidate for
  later review only.
- `short_rate_context_candidate`: a short-rate context candidate that may help
  interpret rate environments without authorizing return use.
- `benchmark_cash_timing_context_candidate`: a candidate used to study
  publication, revision, and availability timing around benchmark or cash
  assumptions.
- `macro_context_candidate`: a macro context candidate that may be useful for
  background only, not benchmark or cash-return construction.
- `rejected_out_of_scope_candidate`: a candidate that is rejected for now or is
  outside the project's future benchmark/cash/rate review scope.

Roles are not approvals. One FRED series may be useful for context but not
usable for returns. No role implies point-in-time safety, cash proxy approval,
benchmark approval, return-construction approval, no-lookahead approval,
strategy validation, or trading readiness.

## Required Series Evidence

For each future candidate FRED series, intake must collect and label at least:

- FRED series ID
- series title
- official FRED series page
- source/release
- units
- frequency
- seasonal adjustment status
- observation start/end
- last updated metadata
- realtime/vintage availability
- release/publication timing
- revision behavior
- missing/stale handling concerns
- transformation/conversion needed
- rights/terms notes
- intended candidate role
- non-claims

Required evidence is intake material only. It does not approve the series,
validate the evidence, authorize FRED access, authorize local storage, approve
cash/benchmark use, approve return construction, approve no-lookahead handling,
or make the series eligible for normal pytest.

## Intake Labels

Future intake records should use these labels:

- `official_series_page`
- `source_release_note`
- `units_frequency_note`
- `seasonal_adjustment_note`
- `realtime_vintage_note`
- `publication_timing_note`
- `revision_note`
- `conversion_note`
- `missing_stale_note`
- `rights_terms_note`
- `normal_pytest_note`
- `unresolved`

Labels are descriptive tags only. They do not validate the underlying material,
approve a FRED series, approve a source, approve data, or prove point-in-time
safety.

## Candidate Statuses

Allowed candidate statuses are:

- `reject_for_now`
- `context_only`
- `candidate_needs_more_evidence`
- `candidate_for_later_series_review`

Forbidden candidate statuses are:

- `approved`
- `validated`
- `series_approved`
- `benchmark_approved`
- `cash_proxy_approved`
- `data_approved`
- `point_in_time_safe`
- `strategy_ready`
- `trading_ready`

Allowed statuses route later review only. They do not authorize FRED API calls,
data downloads, local snapshots, fixture use, source use, return construction,
benchmark/cash comparison, strategy validation, or trading behavior.

## Required Review Questions

Future review must answer these questions for each exact FRED candidate series:

- Is the series appropriate for cash/risk-free or only macro context?
- Is it a yield, rate, price, index, or other unit?
- Is the value daily, monthly, annualized, discount-basis, bond-equivalent, or
  another convention?
- How would it be converted to a daily/monthly return if ever used?
- Is conversion even valid?
- Are values revised?
- Is vintage/realtime history available for this series?
- Is the release/publication date distinguishable from observation date?
- Would the series have been known before the modeled decision timestamp?
- Are missing/stale values possible?
- What rights/attribution restrictions apply?
- Can normal pytest remain independent from FRED?

Unanswered questions remain blockers. Positive answers remain non-approving
until a later explicit phase resolves approval gates and documents any allowed
use.

## Starter Intake Table

The starter table below is an intake template, not evidence and not approval.
Every row is a placeholder only, not reviewed, and not approved. No real FRED
series IDs are selected or added in Phase 97.

| candidate_series_id | candidate_role | fred_series_id | series_title | source_release | units | frequency | realtime_vintage_status | publication_timing_status | conversion_question | current_status | blockers | allowed_next_step | non_claims |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fred_cash_risk_free_proxy_tbd | `cash_risk_free_proxy_candidate` | TBD | TBD | TBD | TBD | TBD | Not reviewed. | Not reviewed. | Conversion validity and daily/monthly return rule unresolved. | `candidate_needs_more_evidence` | Placeholder only; not reviewed; not approved; exact series, rights, timing, revision behavior, and conversion absent. | External primary-source series discovery, then docs-only normalization. | Not FRED approval; not FRED series approval; not cash proxy approval; not return-construction approval. |
| fred_t_bill_proxy_tbd | `t_bill_proxy_candidate` | TBD | TBD | TBD | TBD | TBD | Not reviewed. | Not reviewed. | Discount-basis, bond-equivalent, annualization, and accrual treatment unresolved. | `candidate_needs_more_evidence` | Placeholder only; not reviewed; not approved; exact series, source/release, units, timing, and revisions absent. | External primary-source series discovery, then docs-only normalization. | Not FRED series approval; not cash proxy approval; not rate-source approval; not no-lookahead approval. |
| fred_short_rate_context_tbd | `short_rate_context_candidate` | TBD | TBD | TBD | TBD | TBD | Not reviewed. | Not reviewed. | Context-only use may not support return conversion. | `candidate_needs_more_evidence` | Placeholder only; not reviewed; not approved; context role, rights, timing, and missing/stale behavior absent. | External primary-source series discovery, then docs-only normalization. | Not source approval; not data approval; not benchmark approval; not trading readiness. |
| fred_benchmark_cash_timing_context_tbd | `benchmark_cash_timing_context_candidate` | TBD | TBD | TBD | TBD | TBD | Not reviewed. | Not reviewed. | Timing context may not imply usable returns. | `candidate_needs_more_evidence` | Placeholder only; not reviewed; not approved; release timing, observation timing, and decision alignment absent. | External primary-source series discovery, then docs-only normalization. | Not benchmark approval; not cash proxy approval; not point-in-time safe. |
| fred_macro_context_tbd | `macro_context_candidate` | TBD | TBD | TBD | TBD | TBD | Not reviewed. | Not reviewed. | Macro context may be non-return material only. | `context_only` | Placeholder only; not reviewed; not approved; macro context purpose, rights, and timing absent. | External primary-source series discovery, then docs-only normalization if still relevant. | Not methodology approval; not evidence approval; not strategy validation. |
| fred_rejected_out_of_scope_tbd | `rejected_out_of_scope_candidate` | TBD | TBD | TBD | TBD | TBD | Not reviewed. | Not reviewed. | Conversion likely irrelevant if out of scope. | `reject_for_now` | Placeholder only; not reviewed; not approved; exact out-of-scope reason absent. | Record rationale only if a future candidate is rejected. | Not FRED series approval; not data approval; not trading readiness. |

## Future Approval Gates

Before any future FRED series can be used, a later phase must require:

- official series page reviewed
- source/release reviewed
- Terms/rights reviewed
- realtime/vintage behavior reviewed
- publication timing reviewed
- unit/frequency/conversion rule documented
- missing/stale policy documented
- decision/action timing alignment documented
- normal pytest remains synthetic/offline and does not call FRED

Passing these gates would still not by itself approve FRED, any FRED series,
any benchmark, any cash proxy, any rate source, any data, any source, any
methodology, any parameter set, any evidence, any return-construction policy,
any no-lookahead policy, any strategy validation, or any trading use. Approval
would require a separate explicit phase.

## Relationship To Prior Phases

Phase 90 defined benchmark and cash timing boundaries. Phase 97 narrows one
later review workflow for possible FRED candidate series, but it does not
approve a benchmark, cash proxy, rate source, timing rule, compounding rule, or
cash-return convention.

Phase 95 normalized external primary-source verification output for Stooq,
Alpha Vantage, and FRED as advisory material only. Phase 97 does not refresh
that verification, call FRED, select a series, or convert reported official
documentation into approval.

Phase 96 defined FRED benchmark/cash/rate readiness boundaries. Phase 97 is
the next docs-only intake template for exact candidate series review. It does
not approve FRED, does not approve any FRED series, and does not make FRED data
eligible for normal pytest through network calls.

FRED series selection remains separate from cash proxy approval, benchmark
approval, source approval, data approval, return-construction approval,
no-lookahead approval, and strategy validation.

## Explicit Non-Claims

Phase 97 is:

- not FRED approval
- not FRED series approval
- not benchmark approval
- not cash proxy approval
- not rate-source approval
- not source approval
- not data approval
- not evidence approval
- not return-construction approval
- not no-lookahead approval
- not strategy validation
- not trading readiness

It adds no FRED approval, FRED series approval, benchmark approval, cash proxy
approval, rate-source approval, source approval, data approval, vendor
approval, universe approval, methodology approval, parameter approval, evidence
approval, return-construction approval, no-lookahead approval, cost/friction
approval, liquidity approval, strategy validation, real data ingestion, real
data files, ETF ticker selection, benchmark comparison, ranking, scoring,
recommendation, candidate-discovery behavior, replay metric,
manifest-to-planning bridge, signal/evaluator behavior, broker/order/fill/
portfolio/runtime behavior, LLM call, network call, market-data call,
dashboard/advisory/AI integration, paper behavior, live behavior, or trading
behavior.

## Decision

Decision: FRED candidate series intake plan only.

No FRED series is selected, reviewed, approved, or made implementation-ready.
The next step should be an external primary-source series discovery pass for a
small set of FRED candidate series, followed by repo normalization only. No API
calls or data downloads are approved.

## Remaining Blockers

- no approved FRED use
- no approved FRED series
- no approved source
- no approved data
- no approved benchmark
- no approved cash proxy
- no approved rate source
- no approved official per-series review
- no approved source/release review
- no approved rights, terms, local storage, public repo, redistribution, or
  citation policy
- no approved realtime or vintage behavior for a selected series
- no approved publication, release, observation, or revision timing policy
- no approved unit, frequency, conversion, compounding, or accrual convention
- no approved missing or stale value policy
- no approved decision/action timing alignment
- no approved return-construction policy
- no approved no-lookahead/as-of policy
- no approved strategy-validation claim
- no approved trading-readiness claim
