# Phase 32 Step 11 - S05 Deterministic Reproduction Planning Boundary

## Purpose

This document is a planning boundary only. It defines requirements for a
possible future project-local deterministic reproduction of
`P30-BL-002-S05`.

This document does not reproduce, validate, approve, implement, score, rank,
or promote S05. It does not create a `ValidatedResearchArtifact`, create a
`ValidatedSignalDefinition`, approve a production threshold, approve
production config provenance, or authorize any `src/` changes.

No new external sources are introduced. This boundary depends only on the
existing Phase 32 S05 review plus the S01, S03, and S08 guardrail reviews.

## Source-of-truth documents

- [`phase32_p30_bl_002_s05_formal_review.md`](phase32_p30_bl_002_s05_formal_review.md)
- [`phase32_p30_bl_002_s01_formal_review.md`](phase32_p30_bl_002_s01_formal_review.md)
- [`phase32_p30_bl_002_s03_formal_review.md`](phase32_p30_bl_002_s03_formal_review.md)
- [`phase32_p30_bl_002_s08_formal_review.md`](phase32_p30_bl_002_s08_formal_review.md)
- [`phase32_p30_bl_002_source_status_index.md`](phase32_p30_bl_002_source_status_index.md)

## Candidate Claim To Reproduce

The bounded candidate-evidence claim from S05 is that Moskowitz, Ooi, and
Pedersen report historical time-series momentum evidence based on lagged own
excess returns across a multi-asset futures/forwards universe.

For planning purposes only, the existing docs support this candidate framing:

- universe: 58 liquid futures and forward contracts
- sample window: January 1965 through December 2009, with primary evaluation
  from 1985 onward recorded in the S05 review
- frequency: monthly formation and holding framing
- inputs: lagged own excess returns
- candidate form: sign-based lagged-return variants using cumulative excess
  return over selected lookbacks
- parameter context: lookback and holding grids recorded by the S05 review,
  including 1, 3, 6, 9, 12, 24, 36, and 48 months
- robustness targets: pooled regressions, asset-class decomposition, factor
  regressions, parameter comparisons, cross-asset checks,
  contract-maturity checks, volatility-scaling checks, parameter checks, and
  subperiod checks as future review targets only

This planning boundary does not accept the S05 result as profitable, robust,
generalizable, implementation-ready, threshold-approved, signal-ready, or
validated for this project.

## Required Data Assumptions

Any future deterministic reproduction plan would need to define and record all
of the following before calculation work begins:

- asset universe definition, including exact instruments, asset classes,
  inclusion rules, start dates, end dates, and removal treatment
- historical price or return series, including vendor/source identity,
  frequency, timestamp convention, adjustment policy, and availability window
- excess-return construction, including cash rate or collateral assumptions,
  financing convention, return compounding, and timing alignment
- currency and contract handling if applicable, including currency conversion,
  FX timestamps, contract multiplier assumptions, and denomination changes
- roll and continuous-futures assumptions if applicable, including contract
  selection, roll trigger, roll date, back-adjustment or return-linking method,
  stale contract handling, and replayability of historical roll rules
- point-in-time availability, including what was known at each `as_of` point
  and what data are excluded because they were unavailable then
- survivorship treatment, including delisted, expired, discontinued, renamed,
  or replaced contracts and forward series
- restatement and historical-revision treatment, including latest-revised data,
  corrected data, deleted observations, vendor backfills, and frozen snapshots
- transaction-cost and slippage assumptions, including whether costs are
  excluded, modeled, or scenario-tested and how that choice limits claims
- missing data handling, including holidays, stale prices, incomplete windows,
  contract gaps, late starts, outliers, and exclusion criteria

None of these assumptions is approved by this document. Each is a future
reproduction requirement.

## Required Methodology Controls

Any future reproduction design would need to include these controls before any
stronger evidence claim is considered:

- no-lookahead and `as_of` discipline that separates observation timestamp,
  lookback end, signal timestamp, rebalance timestamp, execution timestamp,
  and return-measurement timestamp
- S08-based PIT controls for snapshot semantics, survivorship handling,
  restatement/revision awareness, stale or corrected data, and local replay
  feasibility
- S03-based data-snooping and multiple-testing guardrails for lookback grids,
  holding-window grids, asset-class decomposition, post-selection evaluation,
  and robustness interpretation
- S01-based negative-control awareness that timing conventions can invalidate
  apparent technical-rule evidence if observation, signal, execution, and
  return-measurement dates are conflated
- out-of-sample and robustness expectations that separate selection from
  evaluation and do not treat reported source robustness as project validation
- deterministic parameter and config recording for universe, lookbacks,
  holding windows, return definitions, volatility settings, costs, and
  exclusions
- reproducibility requirements for offline inputs, deterministic calculations,
  stable fixtures, exact command recording, hashable artifacts where useful,
  and no credential or network dependency under normal pytest
- explicit non-claims stating that reproduction planning is not validation,
  profitability acceptance, threshold approval, implementation approval, or
  trading readiness

## Proposed Future Reproduction Phases

The following are planning-level phases only:

1. Data availability assessment: determine whether exact or acceptable
   substitute historical futures/forwards data can be obtained with clear
   provenance, offline replay, and licensing compatible with project use.
   Phase 32 Step 12 records this assessment boundary as documentation only.
2. Dataset schema/design: define project-local schema requirements for
   instruments, contract metadata, prices or returns, excess-return inputs,
   `as_of` timestamps, revisions, and data-quality flags.
3. Offline fixture or prototype dataset planning: specify a small deterministic
   fixture shape for methodology rehearsal without claiming source
   reproduction or signal validity.
4. Reproduction protocol design: write a protocol for universe reconstruction,
   roll handling, excess-return construction, lookback/holding windows, costs,
   robustness checks, and comparison targets.
5. Deterministic research notebook or script boundary: define a future
   research-only execution boundary that stays outside production code and does
   not add evaluator, signal, broker, runtime, or persistence behavior.
6. Result-review template: design a docs-only template for recording results,
   deviations from S05, assumptions, limitations, no-lookahead checks,
   multiple-testing controls, and non-claims.
7. Promotion decision gate: require a later explicit review before any
   `ValidatedResearchArtifact`, `ValidatedSignalDefinition`, threshold,
   config, implementation, or test-binding discussion.

## Future Reproduction Acceptance Criteria

A future reproduction would need all of the following before it could support
any stronger review:

- deterministic inputs available without credentials or network calls in
  normal pytest
- documented data provenance, license/access notes, vendor or source identity,
  and version or snapshot semantics
- explicit `as_of` timestamps and timing definitions for observations,
  signals, rebalances, executions, and return measurement
- reproducible calculations with deterministic commands, stable configuration,
  and recorded parameter choices
- clear comparison target against the bounded S05 candidate claim, including
  which source result, table, statistic, period, or qualitative claim is being
  compared
- documented deviations from S05, including universe differences, missing
  instruments, data vendor differences, roll differences, timing differences,
  costs, and frequency differences
- costs, slippage, liquidity, financing, leverage, and margin assumptions
  stated as assumptions or exclusions, not accepted production facts
- limitations and non-claims recorded before any promotion review

## Explicit Non-Goals

This phase does not add or authorize:

- strategy implementation
- evaluator implementation
- data ingestion implementation
- backtest engine
- signal computation
- trading signal, score, direction, confidence, rank, probability, or
  actionability
- `ValidatedResearchArtifact`
- `ValidatedSignalDefinition`
- new contract type
- production threshold or production config approval
- broker, OMS, runtime, scheduler, persistence, portfolio, ledger,
  reconciliation, Alpaca, ML, or LLM trading-path behavior
- portfolio mutation
- live-trading or paper-trading implication

## Remaining Blockers

Evaluator implementation and any production route remain blocked by all of the
following:

- no exact `ValidatedResearchArtifact`
- no exact `ValidatedSignalDefinition`
- no project-local deterministic reproduction
- no approved dataset
- no production threshold/config provenance
- no applied no-lookahead audit inside the project
- no implementation-scope approval
- no evaluator tests
- unresolved instrument-level S05 universe reconstruction
- unresolved futures roll rules and contract selection
- unresolved data-vendor access and offline PIT replay path
- unresolved transaction-cost, slippage, liquidity, margin, leverage, and
  financing assumptions
- unresolved parameter-selection, multiple-testing, OOS, and robustness replay
- unresolved exact mapping from S05 candidate evidence to this project's
  advisory pre-risk semantics

## Routing Outcome

The only outcome of this phase is a documentation-only planning boundary for a
possible future deterministic reproduction. Phase 32 Step 12 adds the
documentation-only data availability assessment boundary. The next safe route
remains documentation-only: dataset schema/design if data appears feasible,
source/vendor comparison or a data-provider matrix if data remains uncertain,
or downgrade of S05 to methodology/candidate-context only if data is infeasible
under current project constraints.

Do not start implementation from this boundary.

## Verification

Verification after Phase 32 Step 11:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
passed; Git emitted LF-to-CRLF working-copy warnings only for modified
existing docs

git status --short
 M docs/design/phase32_p30_bl_002_source_status_index.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_s05_deterministic_reproduction_planning_boundary.md
```

Manual documentation checks:

- edited markdown files have no trailing whitespace
- edited markdown files have exactly one final newline
- edited markdown files were inspected for completeness and were not truncated
