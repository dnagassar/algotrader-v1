# Phase 32 Step 12 - S05 Data Availability Assessment Boundary

## Purpose

This document is a data availability assessment boundary only. It defines the
data categories, availability dimensions, dataset acceptance criteria, dataset
rejection criteria, feasibility outcomes, and routing choices that would be
needed before any possible future project-local deterministic reproduction of
`P30-BL-002-S05`.

This document does not source, acquire, ingest, transform, store, validate,
reproduce, approve, implement, score, rank, or promote S05. It does not add a
dataset, notebook, script, schema, evaluator, signal computation, backtest
engine, production threshold, `ValidatedResearchArtifact`, or
`ValidatedSignalDefinition`.

No new external-source claims are introduced. This boundary depends only on the
existing Phase 32 S05 review, the S05 deterministic reproduction planning
boundary, and the S01, S03, and S08 guardrail reviews.

## Source-of-truth Documents

- [`phase32_s05_deterministic_reproduction_planning_boundary.md`](phase32_s05_deterministic_reproduction_planning_boundary.md)
- [`phase32_p30_bl_002_s05_formal_review.md`](phase32_p30_bl_002_s05_formal_review.md)
- [`phase32_p30_bl_002_s01_formal_review.md`](phase32_p30_bl_002_s01_formal_review.md)
- [`phase32_p30_bl_002_s03_formal_review.md`](phase32_p30_bl_002_s03_formal_review.md)
- [`phase32_p30_bl_002_s08_formal_review.md`](phase32_p30_bl_002_s08_formal_review.md)
- [`phase32_p30_bl_002_source_status_index.md`](phase32_p30_bl_002_source_status_index.md)

## Required Data Categories

Any future S05 data feasibility review would need to identify whether the
following categories exist, can be acquired under acceptable terms, and can be
used deterministically after acquisition:

- futures/forwards universe definition, including instruments, asset classes,
  inclusion rules, removals, replacements, start dates, and end dates
- historical prices or returns, including frequency, adjustment policy,
  timestamp convention, vendor/source identity, and sample-window coverage
- excess-return construction inputs, including price-return conversion,
  financing convention, cash return alignment, and compounding choices
- risk-free or collateral return assumptions if required by the reproduction
  design
- contract rolls / continuous futures construction, including contract
  selection, roll triggers, roll dates, stitching or return-linking method,
  back-adjustment policy, and stale-contract treatment
- currency handling, including contract denomination, FX conversion needs,
  FX timestamps, and cross-currency alignment rules
- timestamp/as-of availability, including observation timestamps, release or
  vendor availability timestamps, rebalance timestamps, and return-measurement
  timestamps
- survivorship metadata, including expired, delisted, discontinued, renamed,
  replaced, merged, or otherwise removed instruments
- restatement/revision metadata, including corrections, backfills, deleted
  observations, frozen snapshots, and latest-revised data treatment
- transaction cost, slippage, liquidity, and execution assumption inputs,
  including whether those inputs are provided, excluded, or separately modeled
- missing-data flags or quality metadata, including holidays, stale prices,
  gaps, outliers, late starts, incomplete histories, and vendor quality flags

Identifying a category as required does not mean a dataset satisfying that
category has been found or approved.

## Availability Assessment Dimensions

Each future candidate dataset should be assessed against these dimensions
before any schema, fixture, protocol, or calculation work begins:

- access class: public, paid, academic, vendor-specific, unavailable, or
  unknown
- offline replay: whether the data can be used offline after acquisition
  without credentials, network calls, or vendor runtime logic during normal
  project tests
- license fit: whether licensing permits project-local research use,
  derived-data retention, result comparison, and archival of provenance notes
- PIT/as-of coverage: whether point-in-time availability, release timing,
  revision history, and availability semantics are explicit enough for the
  intended review
- continuous-futures documentation: whether roll selection, continuous-contract
  construction, return-linking, and adjustment rules are documented and
  replayable without hidden vendor behavior
- S05 universe match: whether the existing S05 universe can be matched exactly,
  approximately, only by proxy, or not meaningfully mapped
- sample-window coverage: whether January 1965 through December 2009 can be
  covered for the required instruments and return inputs
- reproduction class: whether the best possible result would be exact, partial,
  proxy-based, methodology-only, or not feasible
- data-quality visibility: whether missing values, stale prices, corrections,
  and excluded observations can be inspected and explained
- cost/liquidity visibility: whether transaction cost, slippage, liquidity, and
  execution assumption inputs are present, separately available, or explicitly
  absent

No candidate dataset is accepted by this document.

## Candidate Dataset Acceptance Criteria

A future dataset candidate should not advance to schema/design planning unless
it satisfies all applicable criteria below or records explicit, reviewable
exceptions:

- deterministic and versioned data or snapshot identity
- locally reproducible after acquisition without default online access
- documented provenance, including source/vendor identity and acquisition path
- stable schema or export format that can be recorded and replayed
- explicit timestamps/as-of semantics for observations and availability
- clear universe membership rules, including additions, removals, replacements,
  and instrument identity changes
- clear roll/contract construction rules for futures or forward series
- explicit missing-data and data-quality handling
- documented excess-return inputs and financing/collateral assumptions where
  required
- cost/slippage assumptions either provided by the dataset or separately
  modeled as a future assumption, not silently inferred
- licensing compatible with project-local research and offline provenance
  documentation
- no default online dependency, credentials, vendor runtime, or network call
  during normal pytest

Acceptance for schema/design planning would still not validate S05, approve a
threshold, or authorize implementation.

## Dataset Rejection Criteria

A future dataset candidate should be rejected or downgraded if any of the
following prevents reliable local review:

- unclear provenance or unverifiable source identity
- impossible to run offline after acquisition
- no timestamp/as-of semantics where timing discipline is required
- survivorship bias cannot be evaluated or documented
- continuous contract construction is undocumented or hidden behind vendor
  logic
- universe cannot be mapped meaningfully to the bounded S05 candidate claim
- licensing prohibits project-local research use or required provenance
  retention
- data quality cannot be inspected, explained, or bounded
- reproduction would require hidden vendor logic, live vendor queries, or
  non-deterministic transformations
- sample coverage cannot meaningfully address January 1965 through December
  2009 where that window is required
- excess-return, collateral, cost, slippage, liquidity, or execution
  assumptions are unavailable and cannot be separately modeled as limitations

Rejected datasets may still be recorded as sourcing attempts in a future
source/vendor comparison, but this phase does not create that comparison.

## Feasibility Outcomes

Future data availability work may route S05 into one of these outcomes only:

- exact reproduction potentially feasible: the universe, window, return
  construction, roll rules, timestamp/as-of semantics, and required assumption
  inputs appear traceable enough for a later deterministic reproduction design
- partial reproduction feasible: core S05 framing can be assessed, but
  documented deviations remain for universe, window, roll, timing, cost, or
  source differences
- proxy reproduction feasible: an approximate futures/forwards universe or
  return construction can test methodology shape only, with no exact S05
  validation claim
- methodology-only reproduction feasible: data are insufficient for candidate
  result comparison, but future docs may still rehearse protocol, schema, or
  timing controls without evidence claims
- not feasible without paid/vendor data: current project constraints cannot
  resolve required data, PIT/as-of, universe, or roll details without a paid or
  vendor-specific source
- not feasible with current project constraints: licensing, offline replay,
  provenance, hidden logic, or missing required categories block useful local
  deterministic reproduction planning

These are possible routing labels only. They are not S05 validation outcomes.

## Recommended Next Routing

If data appears feasible, the next safe route is a future dataset schema/design
boundary. That phase would define data shapes and provenance expectations only;
it would still not ingest data or implement a reproduction.

If data remains uncertain, the next safe route is a future source/vendor
comparison or data-provider matrix entry that records availability, licensing,
PIT/as-of, universe, roll, and offline replay gaps.

If data appears infeasible, S05 should be downgraded to methodology or
candidate-context only for this project unless a later approved sourcing route
resolves the blockers.

No implementation is authorized by this phase.

## Explicit Non-Goals

This phase does not add or authorize:

- data acquisition
- data ingestion
- dataset storage
- schema implementation
- research script
- notebook
- backtest
- strategy implementation
- signal/evaluator implementation
- signal computation
- signal scoring, ranking, direction, confidence, or actionability
- `ValidatedResearchArtifact`
- `ValidatedSignalDefinition`
- new contract type
- production threshold or production config approval
- broker, OMS, runtime, scheduler, persistence, portfolio, ledger,
  reconciliation, Alpaca, ML, or LLM trading-path behavior
- production, paper-trading, live-trading, profitability, or trading-readiness
  implication

## Remaining Blockers

Evaluator implementation and any production route remain blocked by all of the
following:

- no exact `ValidatedResearchArtifact`
- no exact `ValidatedSignalDefinition`
- no approved dataset
- no acquired data
- no project-local deterministic reproduction
- no production threshold/config provenance
- no applied no-lookahead audit inside the project
- no implementation-scope approval
- no evaluator tests
- unresolved exact S05 universe reconstruction
- unresolved futures/forwards roll and continuous-contract rules
- unresolved PIT/as-of availability for any local source
- unresolved survivorship, restatement, and revision treatment
- unresolved transaction cost, slippage, liquidity, execution, margin,
  leverage, collateral, and financing assumptions
- unresolved licensing and offline replay path for any candidate data source
- unresolved mapping from S05 candidate evidence to this project's advisory
  pre-risk semantics

Do not start implementation from this boundary.

## Verification

Verification after Phase 32 Step 12:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
passed; Git emitted LF-to-CRLF working-copy warnings only for modified docs

git status --short
 M docs/design/phase32_p30_bl_002_source_status_index.md
 M docs/design/phase32_s05_deterministic_reproduction_planning_boundary.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_s05_data_availability_assessment_boundary.md
```

Manual documentation checks:

- edited markdown files have no trailing whitespace
- edited markdown files have exactly one final newline
- edited markdown files were inspected for completeness and were not truncated
