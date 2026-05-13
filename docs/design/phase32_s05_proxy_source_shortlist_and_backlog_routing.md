# Phase 32 Step 21 - S05 Proxy Source Shortlist and Backlog Routing Decision

## Purpose

This document groups a non-approving `P30-BL-002-S05` proxy source shortlist
with a backlog and next-routing decision.

It does not select a dataset, approve a source, acquire data, design schemas,
define a reproduction protocol, validate S05, or authorize implementation.

This phase is documentation-only. It adds no schema, notebook, script, code,
test, data fixture, data storage policy, backtest, evaluator, signal
computation, signal scoring, production threshold, `ValidatedResearchArtifact`,
or `ValidatedSignalDefinition`.

## Non-Approving Proxy Source Shortlist

The categories below are source categories only. They are not selected
providers, approved datasets, approved universes, approved schemas, or
approved reproduction paths. None satisfies the Phase 32 Step 20 minimum
requirements at category-only level.

### AQR Factor-Level Data For Calibration/Context

- Possible role: broad factor-level calibration, published context, and
  comparison-language discipline.
- Strengths: may be more publicly documented than raw futures data and may
  help frame methodology or reported factor behavior.
- Limitations: factor-level files are not raw instrument-level S05 data and
  cannot test project-local futures universe construction, roll logic,
  contract handling, missing-data handling, or signal implementation.
- Overclaiming risk: medium to high if treated as S05 reproduction or as
  evidence that project-local signal behavior has been validated.
- Step 20 minimum requirements: not satisfied at category level; a later plan
  would need exact file identity, access date, license/offline-use terms,
  versioning, timestamp/publication semantics, comparison target, and
  context-only non-claims.
- Current status: candidate category only, not selected.

### ETF/Index Proxy Datasets

- Possible role: workflow rehearsal for deterministic snapshots,
  no-lookahead/as-of discipline, and simpler comparison mechanics.
- Strengths: may have clearer public access paths, easier instrument
  identification, and simpler local offline replay than futures data.
- Limitations: low S05 similarity; ETFs and indexes are not the original
  futures/forwards universe and may introduce inception, corporate-action,
  survivorship, expense, and index-methodology differences.
- Overclaiming risk: high if framed as futures time-series momentum evidence
  rather than workflow-only proxy work.
- Step 20 minimum requirements: not satisfied at category level; a later plan
  would need exact instruments, date range, adjusted-price semantics,
  provenance, license/offline-use terms, survivorship assumptions, and
  workflow-only comparison limits.
- Current status: candidate category only, not selected.

### Public/Free Market Data For Methodology Demos Only

- Possible role: lightweight methodology demonstration, deterministic local
  replay rehearsal, or documentation examples if separately approved.
- Strengths: potentially easy access, no vendor contact dependency, and
  suitable for demonstrating process discipline without S05 claims.
- Limitations: likely incomplete for futures-style S05 replication, may have
  unclear licensing, unstable endpoints, weak point-in-time/version history,
  and inconsistent adjustment semantics.
- Overclaiming risk: high if demo data is treated as candidate evidence,
  validation evidence, or a production threshold basis.
- Step 20 minimum requirements: not satisfied at category level; a later plan
  would need stable source identity, archival permission, deterministic
  snapshot discipline, timestamp semantics, license review, and demo-only
  comparison targets.
- Current status: candidate category only, not selected.

### Modern Futures Vendor Category, Unselected

- Possible role: possible later partial or proxy futures-style methodology
  route if source rights, coverage, and local snapshot support are resolved.
- Strengths: highest methodological similarity among proxy categories if
  contract-level coverage, roll semantics, timestamps, and offline rights are
  later proven.
- Limitations: likely licensing, subscription, universe coverage, historical
  depth, versioning, roll-construction, and offline archival uncertainty.
- Overclaiming risk: high if a modern subset is treated as exact S05
  reproduction or as evidence for the 1965-2009 original universe.
- Step 20 minimum requirements: not satisfied at category level; a later plan
  would need exact vendor/product identity, universe, contract coverage, date
  range, roll rules, PIT/as-of semantics, local archival rights, and comparison
  limits.
- Current status: candidate category only, not selected.

### Reduced Futures Universe Category, Unselected

- Possible role: possible later partial futures-style proxy where unavailable
  instruments or periods are explicitly excluded.
- Strengths: may reduce data access complexity while preserving some futures
  mechanics if coverage and rights are later verified.
- Limitations: exclusions can change the research question and make
  comparability fragile; missing instruments, shortened periods, and changed
  composition must be treated as material limitations.
- Overclaiming risk: high if a reduced universe is treated as a faithful S05
  reproduction or used to infer original-universe evidence.
- Step 20 minimum requirements: not satisfied at category level; a later plan
  would need explicit inclusion/exclusion rules, date ranges, gap labels,
  contract/roll assumptions, provenance, rights, and reduced-scope
  non-claims.
- Current status: candidate category only, not selected.

### Manually Reconstructed Public-Table Checks

- Possible role: narrow arithmetic and citation checks against public tables
  only, if a later review approves exact table identities and transcription
  rules.
- Strengths: strong offline fit when the source text is public and manually
  captured; can help prevent claim drift around published figures.
- Limitations: cannot test raw data sourcing, universe construction, roll
  logic, PIT/no-lookahead mechanics, missing-data handling, or implementation
  behavior.
- Overclaiming risk: low to medium if kept as table checking only; high if
  treated as reproduction or validation.
- Step 20 minimum requirements: not satisfied at category level; a later plan
  would need exact table/page identity, source citation, access date,
  transcription rules, arithmetic scope, and table-check-only comparison
  target.
- Current status: candidate category only, not selected.

## Backlog Decision

Conservative decision: S05 should remain in backlog and should not proceed to
another S05-specific docs-only proxy planning gate immediately.

The Step 20 requirements boundary and this non-approving shortlist are enough
to preserve future optionality. Evidence remains insufficient to narrow a
route, approve a source, select a dataset, design a schema, define
reproduction, or authorize implementation.

S05 may be reopened only by a later explicitly scoped docs-only prompt or by a
material change in evidence, access, licensing, budget, or owner preference.

## Easier-Data Candidate Routing

The next research-track effort should evaluate another easier-data candidate
instead of continuing S05-specific planning now.

A different candidate is easier when it has:

- publicly available data
- clear licensing
- offline reproducibility
- simpler universe
- easier benchmark comparison
- lower PIT/survivorship complexity
- no vendor contact dependency
- no immediate implementation requirement

The easier-data candidate should still be treated as unreviewed until it has a
source package, review artifact, non-claims, and deterministic offline
reproducibility assessment.

## Next Recommended Project Route

Chosen route: keep S05 in backlog and evaluate an easier-data candidate next.

This route preserves S05 as a future research option without spending another
near-term phase on proxy-specific narrowing that cannot yet approve data,
reproduction, validation, or implementation.

## Explicitly Deferred Gates

The following gates are intentionally deferred:

- data storage/fixture policy boundary
- schema/design boundary
- reproduction protocol boundary
- result-review template
- any code or tests

## Explicit Non-Goals

This phase does not perform or authorize:

- exact replication
- route approval
- dataset selection
- data acquisition
- ingestion
- schema, code, notebook, or script
- storage/fixture policy
- reproduction protocol
- backtest
- reproduction
- strategy implementation
- evaluator or signal implementation
- signal computation
- signal scoring, ranking, direction, confidence, or actionability
- `ValidatedResearchArtifact`
- `ValidatedSignalDefinition`
- production threshold
- profitability, actionability, or trading implication
- broker, OMS, runtime, scheduler, persistence, portfolio, ledger,
  reconciliation, Alpaca, ML, or LLM trading-path behavior

Proxy source categories do not imply that proxy results can validate S05.

## Remaining Blockers

Evaluator implementation and any production route remain blocked by all of the
following:

- no exact `ValidatedResearchArtifact`
- no exact `ValidatedSignalDefinition`
- no selected/approved dataset
- no completed primary-source vendor verification
- no acquired data
- no project-local deterministic reproduction
- no production threshold/config provenance
- no applied no-lookahead audit inside the project
- no implementation-scope approval
- no evaluator tests
- no selected proxy route
- no approved proxy source category, source, provider, or dataset
- no approved proxy data-storage or fixture policy
- no approved proxy reproduction protocol
- no deterministic offline snapshot path for any candidate source
- no resolved exact S05 universe, 1965-2009 instrument coverage, raw contract,
  roll, PIT/as-of, correction-history, or versioning basis
