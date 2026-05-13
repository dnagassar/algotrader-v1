# Phase 32 Step 5 - P30-BL-002 Limited Formal Review Intake Plan

## Purpose

This document defines the limited formal review intake plan for selected
`P30-BL-002` candidates before any formal source review occurs. It records
review order, review criteria, possible pass/fail outcomes, and evidence
requirements for a later review phase.

This phase is intake planning only. It does not formally review, approve,
validate, promote, implement, or mark `P30-BL-002` or any selected source as
implementation-ready.

## Prior state

- `P30-BL-001` is mechanics-only dispositioned. It is not validated, approved,
  threshold-justified, production-ready, or implementation-ready.
- `P30-BL-002` remains a sourcing handle only.
- Phase 32 Step 3 normalized `P30-BL-002-S01` through `P30-BL-002-S23` from the
  supplied scout reports. The package remains partial, candidate-only,
  unreviewed, unvalidated, unapproved, and not implementation-ready.
- Phase 32 Step 4 verified selected primary-source identities and limited
  formal-review intake eligibility for `P30-BL-002-S01`, `P30-BL-002-S03`,
  `P30-BL-002-S05`, and `P30-BL-002-S08`.
- Phase 32 Step 4 is the source of truth for which selected candidates may
  enter this intake plan.

## Intake scope

Only the Step 4 selected candidates are in scope:

| Source id | Intake role | Scope boundary |
| --- | --- | --- |
| `P30-BL-002-S01` | Negative-control/no-lookahead intake only | May support later review of lookahead and moving-average timing failure modes only |
| `P30-BL-002-S03` | Negative-control/data-snooping/OOS intake only | May support later review of falsification, multiple-testing, and out-of-sample guardrails only |
| `P30-BL-002-S05` | Limited candidate-evidence intake | May support later review as a direct time-series momentum candidate, subject to unresolved evidence gaps |
| `P30-BL-002-S08` | Methodology-only PIT/no-lookahead infrastructure intake | May support later review of point-in-time snapshot semantics only |

No other `P30-BL-002` source is admitted by this plan.

## Boundary separation

| Stage | Meaning | Current status |
| --- | --- | --- |
| Intake planning | Define the review queue, evidence checklist, and allowed review outcomes | This document only |
| Formal review | Inspect each selected source against the review criteria and record findings | Not started |
| Validation | Decide whether reviewed evidence can support an accepted research artifact or signal definition | Not started |
| Implementation readiness | Decide whether exact validated artifacts, signal definitions, tests, and scope permit production code | Blocked |

Formal-review intake eligibility is not formal-review success. Formal-review
success would not automatically create a `ValidatedResearchArtifact` or
`ValidatedSignalDefinition`.

## Review order

Later formal review should use this order:

1. `P30-BL-002-S01` - Zakamulin moving-average timing / lookahead negative
   control.
2. `P30-BL-002-S03` - Sullivan/Timmermann/White data-snooping /
   out-of-sample negative control.
3. `P30-BL-002-S08` - FactSet PIT methodology-only reference.
4. `P30-BL-002-S05` - Time-series momentum candidate.

Negative-control sources should be reviewed before any candidate-evidence
source because they define failure modes that can invalidate apparent threshold
or strategy evidence. The later review should first establish no-lookahead,
timing, multiple-testing, and out-of-sample guardrails, then apply those
guardrails to any direct candidate-evidence source.

`P30-BL-002-S08` should be reviewed before `P30-BL-002-S05` when the project
needs to lock point-in-time methodology before reviewing candidate evidence.
S08 is methodology-only and proprietary. It may inform future point-in-time
data-contract expectations, but it cannot validate a strategy, threshold, or
signal definition.

## Shared formal review criteria

Every later formal review entry must check and record:

- primary-source identity: exact title, author/source owner, publisher or
  venue, date/version, DOI or stable link, and local archival notes
- dataset scope: market, dataset source, data fields, sampling frequency,
  survivorship, corporate-action, roll, deletion, revision, and exclusion
  assumptions
- asset universe: instruments, asset classes, universe construction, inclusion
  timing, and changes through time
- timeframe: exact sample windows, subperiods, in-sample windows,
  out-of-sample windows, and any lookback/holding windows
- input/indicator definition: formulas, lag structure, comparator semantics,
  units, missing/stale data handling, and observed-value timing
- threshold/parameter relevance: whether parameters are rule definitions,
  tuned values, negative-control settings, or methodology-only references
- validation design: in-sample/OOS structure, holdout, walk-forward,
  bootstrap, robustness, sensitivity, and transaction-cost treatment
- no-lookahead / PIT controls: signal timing, execution timing, label timing,
  data-release timing, snapshot semantics, and universe-selection timing
- reproducibility/code/data availability: code, data, license, vendor access,
  deterministic rerun feasibility, and any non-open dependency
- robustness or out-of-sample evidence: what was tested, what was not tested,
  and whether the source separates selection from evaluation
- limitations: source-specific constraints that block generalization,
  production use, or implementation readiness
- non-claims: explicit statements about what the source does not prove
- future binding relevance: whether the source might later support a
  `ValidatedResearchArtifact`, a `ValidatedSignalDefinition`, methodology
  guardrails, or no binding at all
- unresolved gaps: missing evidence that must block validation, promotion, or
  implementation

## Source-specific review criteria

### S01 - Zakamulin MA timing negative control

The later formal review must check:

- exact lookahead-bias finding and the simulation convention that caused it
- corrected timing convention, including signal date, execution date, and
  return-measurement date
- moving-average and crossover rule definitions, windows, comparators, and
  any price/return transformations
- dataset, asset universe, sample dates, frequency, total-return treatment,
  and transaction-cost assumptions
- R code, data files, license, deterministic rerun feasibility, and any
  archival limitations
- whether the source can support only negative-control/no-lookahead testing
  for this project
- why it cannot support production threshold approval, profitability claims,
  strategy validation, or implementation readiness

S01 may be useful only to falsify unsafe timing assumptions. It is not positive
evidence for a production threshold.

### S03 - Sullivan/Timmermann/White data-snooping negative control

The later formal review must check:

- exact technical-rule universe, including rule families, parameter grids, and
  selection process
- data-snooping adjustment and how White's Reality Check is applied
- bootstrap method, assumptions, test statistics, and dependence handling
- in-sample versus out-of-sample structure, including exact sample dates and
  any post-selection evaluation window
- transaction-cost assumptions, daily-rule timing, index data handling, and
  reproducibility constraints
- limitations from single-index focus, historical data construction, and lack
  of verified open code/data
- why the source can support falsification and multiple-testing guardrails only
- why it cannot support production threshold approval, strategy validation, or
  implementation readiness

S03 may be useful only to constrain later claims about optimized technical
rules. It is not positive threshold evidence.

### S05 - Time-series momentum candidate

The later formal review must check:

- exact asset universe, instrument list, asset-class grouping, contract
  maturity selection, roll methodology, and instrument availability through
  time
- lookback and holding-window definitions, including lag structure and rebalance
  timing
- threshold rule shape, including the sign of lagged excess return, the zero
  comparator, and any volatility scaling
- return construction, excess-return definition, collateral assumptions,
  currency handling, leverage/margin assumptions, and monthly timing
- transaction-cost handling, liquidity assumptions, and whether reported
  evidence survives realistic frictions
- out-of-sample, subperiod, cross-asset, parameter-sensitivity, and factor
  regression evidence, without accepting any claim until reviewed
- reproducibility limitations from vendor data, futures roll choices, missing
  public code, and deterministic local data reconstruction
- whether later evidence might support a future `ValidatedResearchArtifact`
  route, without creating one in the review
- what would still be required before any signal-definition binding, including
  exact input contract, threshold/config provenance, PIT data contract,
  no-lookahead tests, and implementation scope approval

S05 is the only selected candidate currently eligible for limited
candidate-evidence review. That eligibility does not validate the source.

### S08 - FactSet PIT methodology reference

The later formal review must check:

- snapshot semantics, including snapshot date, local cutoff, company coverage,
  and whether records reflect data available at the time
- revision, restatement, deletion, currency, consensus-window, and correction
  handling
- data availability timing, including local midnight behavior, timezone
  implications, and late-entered estimate exclusion
- applicability to this project's future offline data contracts, especially
  `as_of`, observation timestamp, data-release timestamp, and reproducible
  snapshot construction
- vendor/proprietary limitations, license/access constraints, FQL semantics,
  and absence of open deterministic replay data
- why this can support methodology-only PIT/no-lookahead review
- why it cannot validate a signal, threshold, edge, strategy, or production
  implementation

S08 may be useful only as methodology context for future data contracts. It is
not a strategy source.

## Pass/fail outcomes

Possible later formal review outcomes are:

- pass for negative-control use only: the source can be used to define
  falsification, no-lookahead, timing, OOS, or multiple-testing guardrails, but
  not positive signal evidence
- pass for methodology-only use only: the source can inform data-contract,
  point-in-time, or review-methodology requirements, but not validate any
  strategy, threshold, or signal
- conditional pass for limited candidate evidence: the source has reviewable
  candidate evidence, but validation and any future binding remain blocked by
  named gaps and later approval gates
- fail / quarantine: the source cannot be safely relied on for the intended
  review role and its claims must remain quarantined
- needs additional sourcing: the source may remain a lead, but the review lacks
  enough primary-source, dataset, code/data, PIT, or reproducibility evidence
  to classify it

No future formal review outcome automatically creates a
`ValidatedResearchArtifact`, creates a `ValidatedSignalDefinition`, approves a
threshold, validates a signal, or authorizes implementation.

## Required review artifacts

A later formal review must produce, for each selected source:

- source-specific review summary
- evidence classification: negative-control, methodology-only, limited
  candidate evidence, fail/quarantine, or additional sourcing needed
- explicit non-claims
- unresolved gaps
- recommendation for next routing
- explicit statement that implementation remains blocked unless separately
  approved by a later phase

If a source is reviewed in a later phase, that phase must keep the review
artifact separate from validation and separate from any implementation-readiness
decision.

## Phase 32 Step 6 follow-up

Phase 32 Step 6 adds the S01-only formal review in
[`phase32_p30_bl_002_s01_formal_review.md`](phase32_p30_bl_002_s01_formal_review.md).
That review passes `P30-BL-002-S01` only for limited
negative-control/no-lookahead use. The pass is narrow and does not create
validation, approve a threshold, bind a signal definition, or authorize
implementation.

The review queue after S01 proceeds to `P30-BL-002-S03` as the second
negative-control source. `P30-BL-002-S05` and `P30-BL-002-S08` remain
unreviewed by Step 6.

## Phase 32 Step 7 follow-up

Phase 32 Step 7 adds the S03-only formal review in
[`phase32_p30_bl_002_s03_formal_review.md`](phase32_p30_bl_002_s03_formal_review.md).
It passes `P30-BL-002-S03` only for limited
negative-control/data-snooping/OOS guardrail use. The pass is narrow and does
not create validation, threshold approval, signal-definition support, or
implementation readiness.

The review queue after S03 proceeds to `P30-BL-002-S08` first so
point-in-time methodology can be locked down before the first limited
candidate-evidence source, `P30-BL-002-S05`.

## Phase 32 Step 8 follow-up

Phase 32 Step 8 adds the S08-only formal review in
[`phase32_p30_bl_002_s08_formal_review.md`](phase32_p30_bl_002_s08_formal_review.md).
It passes `P30-BL-002-S08` only for methodology-only PIT review material. The
pass is narrow and supports point-in-time data methodology framing,
survivorship-bias awareness, restatement / historical-revision awareness,
lookahead-risk framing, and constraints for later candidate-evidence reviews
only. It does not create validation, threshold approval, signal-definition
support, implementation readiness, or trading readiness.

The review queue after S08 proceeds to `P30-BL-002-S05` as the first limited
candidate-evidence source. S05 must be reviewed under the PIT/no-lookahead,
survivorship, and restatement expectations recorded by S08. A future S05 pass
would mean only eligible for further structured evaluation, not
implementation-ready.

## Explicit non-claims

This phase does not validate a signal, threshold, edge, profitability,
robustness, production threshold, config value, or implementation readiness.

This phase does not create a `ValidatedResearchArtifact`, create a
`ValidatedSignalDefinition`, bind a signal definition to an artifact, formally
review `P30-BL-002`, promote `P30-BL-002`, or make it implementation-ready.

This phase does not approve, validate, or promote `P30-BL-002-S01`,
`P30-BL-002-S03`, `P30-BL-002-S05`, or `P30-BL-002-S08`.

This phase does not add a real signal evaluator, signal computation, scoring,
ranking, direction, confidence, probability, actionability, broker behavior,
Alpaca behavior, runtime behavior, scheduler behavior, persistence, ML, or LLM
trading-path behavior.

## Remaining blockers

Evaluator implementation remains blocked by all of the following:

- no `P30-BL-002-S05` formal review
- the `P30-BL-002-S08` review is methodology-only PIT material and does not
  validate a signal, threshold, artifact, signal definition, or implementation
- the `P30-BL-002-S01` review is negative-control/no-lookahead only and does
  not validate a signal, threshold, artifact, signal definition, or
  implementation
- no `ValidatedResearchArtifact`
- no `ValidatedSignalDefinition`
- no approved threshold/config provenance
- no implementation scope approval
- no evaluator tests
- no deterministic production contract binding
- no accepted point-in-time/no-lookahead review for any proposed dataset and
  input definition
- no deterministic reproducibility path for any candidate source

## Verification

Verification after Phase 32 Step 5:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
passed; Git emitted LF-to-CRLF working-copy warnings only for modified
existing docs

git status --short
 M docs/design/phase30_research_artifact_candidate_backlog.md
 M docs/design/phase31_research_track_next_action_plan.md
 M docs/design/phase32_dataset_specific_validation_candidate_selection.md
 M docs/design/phase32_p30_bl_002_primary_source_verification_gate.md
 M docs/design/phase32_p30_bl_002_source_package.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_p30_bl_002_limited_formal_review_intake_plan.md
```

Manual documentation checks:

- edited markdown files have no trailing whitespace
- edited markdown files have exactly one final newline
- edited markdown files were inspected for completeness and were not truncated
