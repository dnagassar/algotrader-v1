# Phase 30 Research Artifact Candidate Backlog

## 1. Purpose

Phase 30 Step 5 populates the initial research artifact candidate backlog.
The backlog is an intake queue for future sourcing and review work.

This phase is documentation-only. It creates starter candidate entries that
may later be sourced, reviewed, rejected, or promoted through the Phase 30
evidence standard and candidate review template.

This phase does not review any candidate artifact, approve any artifact,
create a validated research artifact, create a validated signal definition,
implement an evaluator, add signal computation, add feature computation, or
make any evaluator output actionable. Entries are unreviewed or partially
reviewed candidates only until a later review explicitly promotes or rejects
them.

## 2. Backlog Status Doctrine

Every entry in the backlog may use one of:

- unsourced
- sourcing target
- source-package-ready
- tier-a-reviewed
- mechanics-only conditional
- mechanics-only dispositioned
- sourced
- needs review
- informational only

No entry may be marked validated, approved, production-ready,
implementation-ready, evidence accepted, or threshold justified in this phase.

A backlog entry records a possible future review target. It does not prove a
claim, justify a threshold, support a production signal, or unblock evaluator
implementation.

## 3. Candidate Backlog Table

| Candidate id | Title | Category | Source/provenance | Related evaluator candidate | Related signal idea | Expected inputs | Expected value types | Threshold relevance | Dataset scope | Claim type | Known limitations | Priority | Status | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P30-BL-001 | Simple scalar threshold indicator definition | mechanical indicator definitions | Normalized source package: [`phase31_p30_bl_001_source_package.md`](phase31_p30_bl_001_source_package.md); Tier A review: [`phase31_p30_bl_001_tier_a_review.md`](phase31_p30_bl_001_tier_a_review.md); evidence gap routing plan: [`phase31_p30_bl_001_evidence_gap_routing_plan.md`](phase31_p30_bl_001_evidence_gap_routing_plan.md); mechanics-only summary: [`phase31_p30_bl_001_mechanics_only_review_summary.md`](phase31_p30_bl_001_mechanics_only_review_summary.md); final disposition: [`phase31_p30_bl_001_final_disposition.md`](phase31_p30_bl_001_final_disposition.md) | future threshold-style advisory evaluator | scalar threshold advisory state | `indicator_value`, comparator, threshold | `Decimal` for `indicator_value`; explicit comparator and threshold metadata | Directly relevant to `indicator_value >= threshold` mechanics | not applicable for mechanical sources; no dataset-specific validation | mechanical transformation only / methodology support only | Tier A conditionally supports mechanics and methodology only; Step 6 records mechanics-only conditional support; Step 7 dispositioned mechanics-only support only; no validated artifact, no validated signal definition, no production threshold rationale, no dataset validation, no implementation approval | P0 | mechanics-only dispositioned | Route next work toward a candidate or research task with dataset-specific threshold or validation evidence, such as `P30-BL-002` or a better sourced replacement; do not review, validate, or implement that candidate in this phase |
| P30-BL-002 | Threshold sanity check for `indicator_value` | threshold sanity-check studies | unsourced | future threshold-style advisory evaluator | scalar threshold advisory state | `indicator_value`, threshold, comparator, `as_of` | `Decimal`; UTC-aware timestamp metadata if applicable | Directly relevant to non-arbitrary threshold selection | unknown | threshold sanity check | No reviewed threshold, no comparator evidence, no validation window | P0 | unsourced | Source a candidate artifact that explains threshold choice and non-claims |
| P30-BL-003 | Deterministic scalar indicator feature-validity reference | data-quality / feature-validity studies | unsourced | future threshold-style advisory evaluator | deterministic scalar indicator input validity | raw source fields, derived scalar name, observation timestamp | deterministic scalar values such as `Decimal`, `int`, or `bool` as scoped | Indirectly relevant to whether `indicator_value` is a valid observed input | unknown | mechanical transformation only / data-quality claim | No source, no feature formula, no data-quality controls | P1 | unsourced | Source a candidate that documents feature construction, timestamp, and validity rules |
| P30-BL-004 | No-lookahead bias-control reference | no-lookahead / bias-control references | unsourced | any future real evaluator | point-in-time signal evaluation | feature timestamps, label timestamps, `as_of` | UTC-aware datetimes plus explicit feature values | Indirectly relevant to evaluator timestamp and bundle rules | unknown | robustness claim / bias-control reference | No exact source, no asset universe, no tested artifact | P1 | unsourced | Source a point-in-time/no-lookahead methodology reference for template review |
| P30-BL-005 | Survivorship-bias and data-quality reference | data-quality / feature-validity studies | unsourced | any future real evaluator | data-quality safeguards for research inputs | universe membership, corporate actions, delistings, stale/missing observations | explicit dataset metadata and scalar values | Indirectly relevant to research artifact admissibility | unknown | data-quality claim / bias-control reference | No source, no dataset scope, no correction method | P1 | unsourced | Source a data-quality reference that can be checked against the evidence standard |
| P30-BL-006 | Moving-average based regime filter study | regime indicator studies | unsourced | possible later regime-aware evaluator, not the current threshold candidate unless narrowed | regime filter idea | price series, moving-average values, observation timestamps | `Decimal` price or indicator values; explicit window lengths | Not directly relevant until a specific threshold and signal definition are proposed | unknown | regime indicator | Generic idea only, no formula choice, no dataset, no no-lookahead review | P2 | unsourced | Source a candidate study only if a future regime-filter evaluator is scoped |
| P30-BL-007 | Momentum or trend-following indicator study | predictive relationship studies | unsourced | possible later momentum evaluator, not current threshold candidate unless narrowed | momentum or trend indicator idea | price/return series, indicator value, timestamp | deterministic scalar values; exact formula unknown | Indirect; may inform future threshold semantics but does not justify current placeholder | unknown | predictive relationship | Generic idea only, no evidence, no profitability claim accepted | P2 | unsourced | Source a candidate study and classify claims conservatively before review |
| P30-BL-008 | Risk filter study for advisory signal gating | risk filter studies | unsourced | possible later pre-risk advisory evaluator or risk-adjacent validation, not risk approval | risk filter idea | volatility, drawdown, spread, liquidity, or exposure proxy inputs | deterministic scalar values only if later scoped | Not directly relevant to current threshold evaluator implementation | unknown | risk filter | Could blur advisory output with risk approval if not tightly scoped | P2 | unsourced | Source only as advisory research; ensure review states no risk approval |
| P30-BL-009 | Backtesting methodology reference | backtesting methodology references | unsourced | any future evaluator review | research validation methodology | dataset window, universe, feature/label construction, metrics | metadata and explicit values as applicable | Indirectly relevant to reproducibility and evidence review | unknown | informational only / robustness claim | Informational until tied to a concrete candidate artifact | P3 | informational only | Use as background only unless a specific reviewable artifact is sourced |

## 4. Initial Candidate Categories

The starter backlog intentionally spans only a small set of reviewable
categories:

- mechanical indicator definitions
- threshold sanity-check studies
- regime indicator studies
- predictive relationship studies
- risk filter studies
- data-quality / feature-validity studies
- backtesting methodology references
- no-lookahead / bias-control references

The backlog is deliberately small. It is meant to create review pressure in
the right direction, not to accumulate broad strategy ideas faster than the
project can review them.

## 5. Candidate Examples Included

The initial examples are placeholders and sourcing targets, not validated
evidence. They include:

- a mechanical definition of a simple threshold indicator over a scalar input
- a threshold sanity-check candidate for `indicator_value`
- a feature-validity candidate for deterministic scalar indicators
- a no-lookahead bias-control reference target
- a survivorship-bias / data-quality reference target
- a backtesting methodology reference target
- moving-average regime-filter research as a later-scope candidate
- momentum / trend-following research as a later-scope candidate

When exact source/provenance is unknown, the entry is marked `unsourced`.
Generic entries must not be treated as sourced evidence merely because the
topic is familiar.

## 6. Priority Guidance

Priorities are conservative:

- P0: directly required to unblock the threshold evaluator.
- P1: useful for near-term research validation.
- P2: useful later for broader evaluator or feature work.
- P3: informational only.

Priority is routing metadata only. It is not evidence quality, approval, or
implementation readiness. A P0 candidate can still fail review.

Phase 30 Step 6 selects `P30-BL-001` as the first sourcing target only. Phase
31 Step 3 normalizes the `P30-BL-001` source package and moves it to
source-package-ready only. Phase 31 Step 4 reviews Tier A sources and moves it
to tier-a-reviewed only. Phase 31 Step 5 routes the Tier A result and
recommends a formal mechanics-only candidate artifact review summary. Phase 31
Step 6 records that summary and moves `P30-BL-001` to mechanics-only
conditional. Phase 31 Step 7 records the final disposition and moves
`P30-BL-001` to mechanics-only dispositioned. These statuses do not validate,
approve, justify a production threshold, or make the candidate
implementation-ready.

## 7. Non-Validation Warning

Backlog inclusion does not mean:

- artifact reviewed
- evidence accepted
- signal validated
- threshold justified
- evaluator implementation approved
- strategy claim accepted
- profitability claim accepted
- production readiness
- implementation readiness

No entry in this backlog may be used to justify production code, production
thresholds, signal computation, risk approval, execution behavior, broker
behavior, order submission, runtime behavior, persistence, ML inference, or
LLM trading-path behavior.

## 8. Routing To Future Review

Future routing is:

```text
backlog entry
  -> source collected
  -> source package normalized
  -> candidate review using Phase 30 template
  -> pass / conditional pass / fail / informational only
  -> possible ValidatedResearchArtifact
  -> possible ValidatedSignalDefinition
  -> possible implementation readiness review
  -> only then evaluator implementation
```

Any skipped step keeps implementation blocked. A reviewed artifact can still
fail or remain informational only.

## 9. Relationship To Existing Docs

The Phase 30 research validation evidence standard defines the evidence bar.
This backlog does not lower that bar, fill missing evidence, or convert
unsourced ideas into acceptable support.

The Phase 30 candidate review template is the required review shape. Every
candidate that might support a validated artifact must pass through that
template before promotion is considered.

The Phase 30 sourcing plan defines how candidate sources should be collected,
triaged, prioritized, and routed. This backlog is the first small population
of that queue.

The Phase 31 `P30-BL-001` source package records normalized source candidates,
source tiers, grouping, known gaps, and next routing only. It does not lower
the evidence bar or validate the candidate.

The Phase 31 Tier A review records a conditional mechanics and methodology
outcome only. It does not create a validated research artifact, create a
validated signal definition, justify a production threshold, or authorize
evaluator implementation.

The Phase 31 evidence gap and routing plan preserves `P30-BL-001` as
unvalidated and recommends a formal mechanics-only candidate artifact review
summary before any production threshold, validated signal definition, or
evaluator implementation route is considered.

The Phase 31 mechanics-only candidate artifact review summary records
`P30-BL-001` as mechanics-only conditional. It does not create a validated
research artifact, create a validated signal definition, justify a production
threshold, or authorize evaluator implementation.

The Phase 31 final disposition records `P30-BL-001` as mechanics-only
dispositioned. This closes the candidate only for mechanics-only support and
does not validate the candidate, approve a production threshold, create a
validated research artifact, create a validated signal definition, or authorize
evaluator implementation.

The Phase 30 threshold evaluator research-support boundary remains the
implementation blocker. The threshold evaluator remains unimplemented until a
candidate is reviewed and promoted into exact validated research and exact
validated signal-definition support.

The Phase 29 threshold evaluator constants/output semantics remain design
semantics only. Placeholder names such as `indicator_value`, placeholder
comparator semantics, and placeholder threshold examples remain non-production
until tied to exact reviewed evidence.

A future `ValidatedResearchArtifact` may only be created after a candidate
passes review. A future `ValidatedSignalDefinition` may only bind to exact
artifact support and must preserve advisory, pre-risk semantics.

## 10. Explicitly Out Of Scope

Phase 30 Step 5 does not add:

- actual reviewed research artifact
- validated research artifact
- validated signal definition
- evaluator implementation
- evaluator protocol
- signal computation
- feature computation
- strategy logic
- score, direction, confidence, or actionability
- ranking or probability
- signal-to-risk conversion
- risk approval
- execution intent creation
- execution-plan mutation
- portfolio mutation
- broker or Alpaca behavior
- order submission
- runtime or scheduler behavior
- persistence
- live data ingestion
- network calls from production code
- ML or LLM trading-path behavior

Normal pytest must remain offline, credential-free, and safe.

## 11. Non-Binding Future Phase Sketch

Possible future phases include:

1. Future step: next-candidate sourcing or routing for dataset-specific
   threshold or validation evidence, docs-only.
2. Later step: candidate validated signal definition review and artifact
   binding, docs-only, only if later evidence supports it.
3. Later step: implementation scope approval review.
4. Later: minimal threshold evaluator implementation only if all blockers are
   resolved.

Historical Phase 30 sketch before Phase 31 normalization was:

1. Phase 30 Step 6: select first candidate source target, docs-only.
2. Phase 30 Step 7: collect/summarize the selected candidate source,
   docs-only.
3. Phase 30 Step 8: first candidate research artifact review using the
   template, docs-only.
4. Phase 30 Step 9: candidate validated signal definition review and artifact
   binding.
5. Phase 30 Step 10: implementation scope approval review.
6. Later: minimal threshold evaluator implementation only if all blockers are
   resolved.

This sketch is non-binding. Any future work must remain contract-first,
test-first, deterministic, offline-safe, credential-free, broker-isolated,
advisory, pre-risk, and outside the LLM trading hot path.
