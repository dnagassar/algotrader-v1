# Phase 32 Step 13 - S05 Data Provider / Source Comparison Plan

## Purpose

This document is a data-provider/source comparison plan only. It defines how
future data-source categories should be compared for possible
`P30-BL-002-S05` deterministic reproduction feasibility.

This document does not select, purchase, subscribe to, acquire, ingest,
download, transform, store, validate, reproduce, approve, implement, score,
rank, or promote any data source. It does not add a vendor integration,
dataset, schema, notebook, script, backtest engine, evaluator, signal
computation, production threshold, `ValidatedResearchArtifact`, or
`ValidatedSignalDefinition`.

No new external-source or vendor-specific claims are introduced. This boundary
depends only on the existing S05 formal review, the S05 deterministic
reproduction planning boundary, the S05 data availability assessment boundary,
and the S01, S03, and S08 guardrail reviews.

## Source-of-truth Documents

- [`phase32_s05_data_availability_assessment_boundary.md`](phase32_s05_data_availability_assessment_boundary.md)
- [`phase32_s05_deterministic_reproduction_planning_boundary.md`](phase32_s05_deterministic_reproduction_planning_boundary.md)
- [`phase32_p30_bl_002_s05_formal_review.md`](phase32_p30_bl_002_s05_formal_review.md)
- [`phase32_p30_bl_002_s01_formal_review.md`](phase32_p30_bl_002_s01_formal_review.md)
- [`phase32_p30_bl_002_s03_formal_review.md`](phase32_p30_bl_002_s03_formal_review.md)
- [`phase32_p30_bl_002_s08_formal_review.md`](phase32_p30_bl_002_s08_formal_review.md)
- [`phase32_p30_bl_002_source_status_index.md`](phase32_p30_bl_002_source_status_index.md)

## Source Categories To Compare

Future source comparison should consider categories only until an explicit
source-verification phase is approved:

- academic/paper replication data
- paid institutional futures data
- retail futures/continuous futures vendors
- broker-provided historical data
- public/free datasets
- internally constructed proxy datasets
- methodology-only/manual reconstruction from published tables

Category inclusion does not mean any category is available, licensed,
sufficient, selected, or approved.

## Comparison Criteria

Each future candidate source category should be compared against these
criteria before any dataset, schema, fixture, protocol, or calculation work is
routed:

- coverage of S05 universe, including instrument identity, asset classes,
  additions, removals, replacements, and discontinued contracts
- coverage of January 1965 through December 2009
- futures/forwards support, including contract-level metadata where required
- price/return series quality, including adjustment policy, frequency,
  stale-price handling, gaps, outliers, and quality flags
- excess-return construction support, including cash, collateral, financing,
  compounding, and timing alignment inputs
- roll/continuous contract documentation, including roll trigger, roll date,
  contract selection, stitching, back-adjustment, and return-linking rules
- PIT/as-of support, including observation, vendor availability, revision,
  rebalance, and return-measurement timestamps
- survivorship and delisting treatment for expired, delisted, discontinued,
  renamed, replaced, or unavailable instruments
- restatement/revision handling, including frozen snapshots, corrections,
  backfills, deleted observations, and latest-revised data treatment
- currency handling, including contract denomination, FX conversion, and
  timestamp alignment
- transaction cost/slippage/liquidity inputs or explicit support for recording
  them as separate assumptions or limitations
- licensing for local research use, derived data, provenance notes, and
  offline archival where needed
- offline reproducibility after acquisition without default network calls,
  credentials, vendor runtime logic, or online services during normal pytest
- deterministic versioning, including snapshot identity, export version,
  source date, checksums, or other stable identifiers where applicable
- cost/complexity, including acquisition effort, manual reconstruction burden,
  licensing friction, and long-term replay burden
- fit with normal pytest remaining offline and credential-free

No comparison criterion authorizes implementation or validates S05.

## Lightweight Source-Category Matrix

| Source category | Possible support target | Criteria to verify first | Outcome if verification fails |
| --- | --- | --- | --- |
| Academic/paper replication data | Exact or partial reproduction candidate if it contains the needed universe, returns, assumptions, and timing notes | S05 universe match, Jan 1965-Dec 2009 coverage, excess-return construction, roll rules, license, offline replay, and versioning | Unresolved, proxy-only, or methodology-only support |
| Paid institutional futures data | Exact or partial reproduction candidate if contract history, PIT/as-of semantics, rolls, quality flags, and licensing are adequate | Contract-level history, continuous-futures construction, survivorship, revisions, currency, costs/liquidity, license, offline exports, and deterministic snapshots | Source/vendor verification needed, or reject if hidden logic/offline limits block replay |
| Retail futures/continuous futures vendors | Partial or proxy reproduction candidate if documented continuous series and enough window coverage exist | Universe mapping, window coverage, roll documentation, adjustment method, quality flags, licensing, and offline reproducibility | Proxy-only, methodology-only, or reject if construction is undocumented |
| Broker-provided historical data | Proxy or limited partial candidate only if historical depth, contract metadata, and offline export terms are sufficient | Historical depth, futures/forwards support, roll/continuous support, PIT/as-of semantics, license, and no credential/network dependency under normal pytest | Reject or methodology-only if online dependency, limited history, or missing roll/PIT details block replay |
| Public/free datasets | Proxy or methodology-only support unless exact universe, window, and construction details are verified | Provenance, completeness, license, universe mapping, sample window, roll rules, data quality, and versioning | Reject or methodology-only if provenance, license, quality, or coverage is insufficient |
| Internally constructed proxy datasets | Proxy reproduction candidate for methodology rehearsal only, not S05 validation | Explicit source inputs, deterministic construction, documented deviations, no-lookahead controls, license, and limitations | Methodology-only or reject if inputs cannot be justified or replayed |
| Methodology-only/manual reconstruction from published tables | Methodology-only support for protocol and review framing, not result reproduction | Published table scope, exact statistic definitions, assumptions, limitations, and inability to reconstruct underlying observations | Methodology-only or reject if even protocol framing cannot be bounded |

This matrix is intentionally category-level. It does not name, rank, select, or
approve any vendor, dataset, subscription, or acquisition path.

## Comparison Outcome Categories

Future comparison work may classify a candidate source only as:

- exact reproduction candidate: category/source appears able to support an
  exact S05-like universe, window, roll, return, timing, and assumption replay
- partial reproduction candidate: category/source can support a bounded
  comparison with documented deviations from S05
- proxy reproduction candidate: category/source can support methodology-shape
  testing only, with no exact S05 validation claim
- methodology-only support: category/source can inform protocol, table
  interpretation, timing controls, or documentation, but not reproduce results
- reject / incompatible: category/source fails provenance, licensing, offline
  replay, PIT/as-of, universe, roll, or quality requirements
- unresolved / needs further source verification: category/source cannot be
  classified without a later approved verification step

These are routing labels only. They are not evidence validation outcomes.

## Recommended Next Routing

If at least one exact or partial candidate is plausible, the next safe route is
a future dataset schema/design boundary. That boundary would define data shapes
and provenance expectations only; it would still not select, acquire, ingest,
or implement a source.

If only proxy candidates are plausible, a future docs-only decision should
decide whether proxy reproduction is worth the sourcing, documentation, and
maintenance cost.

If only methodology-only support is plausible, S05 should be downgraded from a
reproduction candidate to methodology/candidate-context only for this project
unless later approved sourcing resolves the gaps.

If the comparison remains unresolved, the next safe route is a future
source/vendor verification step that records source identity, license,
coverage, PIT/as-of, roll, offline replay, and quality gaps without acquiring
or ingesting data by default.

No implementation is authorized by this phase.

## Explicit Non-Goals

This phase does not add or authorize:

- vendor choice
- subscription or purchase decision
- data acquisition
- data download
- data ingestion
- dataset storage
- schema implementation
- code, notebook, or script
- backtest
- reproduction
- strategy implementation
- evaluator/signal implementation
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
- no selected/approved dataset
- no acquired data
- no project-local deterministic reproduction
- no production threshold/config provenance
- no applied no-lookahead audit inside the project
- no implementation-scope approval
- no evaluator tests
- unresolved exact S05 universe reconstruction
- unresolved source category or provider verification
- unresolved futures/forwards roll and continuous-contract rules
- unresolved PIT/as-of availability for any local source
- unresolved survivorship, restatement, and revision treatment
- unresolved transaction cost, slippage, liquidity, execution, margin,
  leverage, collateral, and financing assumptions
- unresolved licensing and offline replay path for any candidate source
- unresolved mapping from S05 candidate evidence to this project's advisory
  pre-risk semantics

Do not start implementation from this boundary.

## Verification

Verification after Phase 32 Step 13:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
passed; Git emitted LF-to-CRLF working-copy warnings only for modified docs

git status --short
 M docs/design/phase32_p30_bl_002_source_status_index.md
 M docs/design/phase32_s05_data_availability_assessment_boundary.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_s05_data_provider_source_comparison_plan.md
```

Manual documentation checks:

- edited markdown files have no trailing whitespace
- edited markdown files have exactly one final newline
- edited markdown files were inspected for completeness and were not truncated
