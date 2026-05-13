# Phase 32 Step 14 - S05 Data Provider Scout Research Normalization

## Purpose

This document normalizes externally provided Perplexity scout research into the
project research trail for `P30-BL-002-S05`.

This document is not a source verification report. It is not a vendor decision.
It is not data approval. It is not reproduction approval.

This phase does not select, purchase, subscribe to, acquire, ingest, download,
transform, store, validate, reproduce, approve, implement, score, rank, or
promote any data source. It does not add a vendor integration, dataset, schema,
notebook, script, backtest engine, evaluator, signal computation, production
threshold, `ValidatedResearchArtifact`, or `ValidatedSignalDefinition`.

## Source-of-Truth Documents

This normalization depends on the existing controlled project trail:

- [`phase32_p30_bl_002_s05_formal_review.md`](phase32_p30_bl_002_s05_formal_review.md)
- [`phase32_s05_deterministic_reproduction_planning_boundary.md`](phase32_s05_deterministic_reproduction_planning_boundary.md)
- [`phase32_s05_data_availability_assessment_boundary.md`](phase32_s05_data_availability_assessment_boundary.md)
- [`phase32_s05_data_provider_source_comparison_plan.md`](phase32_s05_data_provider_source_comparison_plan.md)
- [`phase32_p30_bl_002_source_status_index.md`](phase32_p30_bl_002_source_status_index.md)

The externally provided Perplexity output is scout research only. It is not a
primary source and is not a project disposition.

## Scout Research Status

The Perplexity output is treated as external scout research. Its claims require
primary-source verification before they can be used for dataset selection,
source approval, reproduction planning, schema design, or any stronger project
claim.

Evidence currently normalized here:

- The externally supplied scout summary reports possible provider/source
  categories and feasibility concerns.
- No vendor documentation, license agreement, sample export, data dictionary,
  primary support response, or acquired dataset was reviewed in this phase.
- No project-local reproduction evidence was created.

Inferences allowed in this document:

- The scout summary can guide question routing and priority.
- Candidate categories can be classified as unverified possible routes.
- More specific primary verification should come before any provider choice.

Unresolved questions remain around point-in-time/as-of guarantees, exact
contract coverage, local archival licensing, AQR deeper data access, roll
methodology transparency, continuous-series construction, survivorship and
delisting treatment, and deterministic offline replay after acquisition.

## Normalized Executive Finding

Exact S05 reproduction appears unlikely under personal/offline constraints, but
that is an unverified scout-level finding until primary sources are checked.

Partial or proxy reproduction appears more realistic than exact reproduction.
AQR factor data appears useful as calibration or context only, not as raw
instrument-level reproduction data. CSI, Pinnacle, Norgate, and TradeStation
appear to be candidate categories requiring verification. Institutional feeds
appear theoretically strong but practically unsuitable unless access, licensing,
local archival rights, and deterministic offline use are resolved. Broker/free
APIs appear unsuitable for exact S05 reproduction under the current project
constraints.

No source is selected or approved by this finding.

## Feasibility Classification

Use these labels only as cautious routing labels:

- exact reproduction candidate: may be able to support exact S05-like universe,
  window, roll, return, timing, and assumption replay, subject to primary
  verification
- partial reproduction candidate: may support a bounded comparison with
  documented deviations from S05
- proxy reproduction candidate: may support methodology-shape testing only,
  without exact S05 validation claims
- methodology/calibration only: may inform interpretation, factor-level
  calibration, or review framing, but not raw instrument-level reproduction
- likely unsuitable: appears incompatible with exact S05 reproduction under
  current constraints unless later evidence changes that
- unresolved / needs primary verification: cannot be classified beyond scout
  routing without primary-source checks

These are not validation outcomes.

## Candidate Source Classification Table

| Source/category | Scout-reported role | Possible feasibility class | Strengths | Key gaps | Verification required | Current project status | Allowed next action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AQR TSMOM factor data | Factor-level time-series momentum context or calibration lead | Methodology/calibration only; unresolved for raw data | May align conceptually with the S05 family of evidence | Not raw instrument-level futures/forwards reproduction data in the scout summary; deeper access unclear | Confirm available series, construction notes, instrument mapping, licensing, versioning, and whether any raw/deeper dataset access exists | Unverified scout-normalized category; not selected; no data acquired | Include in primary-verification questionnaire for calibration/context only |
| CSI | Long-history futures data candidate | Partial reproduction candidate; unresolved / needs primary verification | Scout report presents it as a stronger long-history futures candidate | Exact 1965-2009 coverage, individual contracts, roll rules, PIT/as-of semantics, licensing, and archival rights unresolved | Verify contract coverage, continuous-series construction, export/version controls, local archival permission, costs, and offline replay | Unverified scout-normalized category; not selected; no data acquired | Prioritize primary-source vendor verification |
| Pinnacle | Long-history futures data candidate | Partial reproduction candidate; unresolved / needs primary verification | Scout report presents it as a stronger partial futures candidate | Exact universe fit, contract versus continuous history, roll methodology, PIT/as-of semantics, and licensing unresolved | Verify coverage, data fields, roll/adjustment policy, versioning, local archival permission, and derived-statistics sharing | Unverified scout-normalized category; not selected; no data acquired | Prioritize primary-source vendor verification |
| Norgate | Modern futures-style reproduction candidate | Partial or proxy reproduction candidate; unresolved / needs primary verification | Scout report suggests possible modern 1980+ usefulness | Likely insufficient for full 1965-2009 S05 replay in scout summary; exact contract coverage and offline rights unresolved | Verify start dates, futures support, contract history, continuous-series construction, PIT/as-of/versioning, and licensing | Unverified scout-normalized category; not selected; no data acquired | Verify after CSI/Pinnacle or in the same questionnaire batch |
| TradeStation | Partial candidate if owner already has access | Partial or proxy reproduction candidate; unresolved / needs primary verification | May be accessible if already available to the project owner | Workflow, licensing, export, offline archival, long-history coverage, and reproducibility may be less clean | Verify owner access, export rights, historical depth, contract metadata, roll behavior, and offline replay | Unverified scout-normalized category; not selected; no data acquired | Optional verification only if access already exists or is expected |
| Bloomberg/LSEG/Datastream/institutional feeds | Theoretically strong institutional data path | Exact or partial reproduction candidate in theory; likely unsuitable in practice unless access/licensing resolves | May offer broader institutional coverage and metadata | Cost, license restrictions, redistribution, local archival rights, private repo use, and deterministic offline replay likely blockers | Verify pricing, access, export rights, PIT/as-of support, versioning, local archive rights, and derived-statistics sharing | Unverified scout-normalized category; not selected; no data acquired | Record as theoretically strong but do not pursue unless access/licensing becomes realistic |
| Retail charting/futures vendors | Continuous futures or chart-history proxy candidates | Proxy reproduction candidate or likely unsuitable | May provide convenient continuous series for methodology rehearsal | Vendor logic, roll rules, long-history coverage, licensing, quality flags, and PIT/as-of semantics may be opaque | Verify universe, date range, continuous-contract construction, export/version controls, and offline use | Unverified scout-normalized category; not selected; no data acquired | Keep as proxy-only unless primary evidence supports more |
| Broker-native historical APIs | Broker/platform historical data | Proxy reproduction candidate or likely unsuitable | May be convenient where already authorized | Online/credential dependency, limited history, missing PIT/as-of semantics, limited futures/forwards support, and licensing friction | Verify offline export rights, historical depth, futures metadata, roll rules, and no default network dependency | Unverified scout-normalized category; not selected; no data acquired | Keep unsuitable for exact reproduction unless later evidence changes that |
| Public/free datasets | No-cost source leads | Proxy reproduction candidate or likely unsuitable | Low acquisition friction and possible review examples | Coverage, provenance, license, revisions, roll methodology, quality, and deterministic versioning usually unresolved | Verify source identity, license, completeness, date range, universe, roll construction, and checksums/versioning | Unverified scout-normalized category; not selected; no data acquired | Use only for proxy or methodology context after verification |
| ETF/index proxy universe | Public or paid proxy substitute for instrument-level futures/forwards | Proxy reproduction candidate | Could rehearse deterministic protocol shape without futures raw data | Not exact S05 universe, may start later, may embed product/index methodology, and cannot validate S05 | Verify instrument list, inception dates, survivorship, index construction, fees, currency, and license | Unverified proxy idea; not selected; no data acquired | Consider only after a proxy-worth decision, not as S05 reproduction |
| Manually reconstructed published table checks | Manual comparison against reported tables/statistics | Methodology/calibration only | Can sanity-check high-level results and definitions without acquiring raw data | Cannot reconstruct observations, PIT state, roll inputs, costs, or exact no-lookahead behavior | Verify table definitions, statistic formulas, sample windows, and limitations | Unverified methodology route; no reproduction evidence created | Use only for documentation checks or calibration framing |

## Primary Verification Checklist

Before any future dataset selection, source approval, schema design, or
reproduction planning, verify:

- exact instrument/contract coverage
- coverage of January 1965 through December 2009
- futures/forwards support
- individual contracts versus continuous series
- roll methodology and whether it changed over time
- PIT/as-of/versioning support
- survivorship/delisting treatment
- restatement/revision handling
- excess-return construction inputs
- currency handling
- transaction cost/slippage/liquidity fields
- local archival permissions
- private repo usage permissions
- derived-statistics sharing permissions
- offline use after acquisition
- deterministic file/version snapshot support
- costs and subscription requirements

If any item cannot be verified, that gap must be recorded before a source can
move beyond scout-normalized status.

## Recommended Next Routing

Do not choose a provider yet.

The recommended next phase is a vendor/source primary-verification
questionnaire or direct outreach template focused first on CSI, Pinnacle,
Norgate, and AQR. TradeStation should be included only if the project owner
already has access or reasonably expects access.

Broker/free APIs should remain proxy-only or unsuitable for exact S05
reproduction unless later primary evidence changes that. Institutional feeds
should remain theoretically strong but practically unsuitable unless access,
cost, licensing, local archival, and offline replay constraints are resolved.

No implementation is authorized by this phase.

## Explicit Non-Goals

This phase does not add or authorize:

- vendor decision
- purchase
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
- no primary-source vendor verification
- no acquired data
- no project-local deterministic reproduction
- no production threshold/config provenance
- no applied no-lookahead audit inside the project
- no implementation-scope approval
- no evaluator tests
- unresolved exact S05 universe reconstruction
- unresolved source/category/provider verification
- unresolved futures/forwards roll and continuous-contract rules
- unresolved PIT/as-of availability for any local source
- unresolved survivorship, restatement, and revision treatment
- unresolved transaction cost, slippage, liquidity, execution, margin,
  leverage, collateral, and financing assumptions
- unresolved licensing and offline replay path for any candidate source
- unresolved mapping from S05 candidate evidence to this project's advisory
  pre-risk semantics

Do not start implementation from this normalization.

## Verification

Verification after Phase 32 Step 14:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
passed; Git emitted LF-to-CRLF working-copy warnings only for modified docs

git status --short
 M docs/design/phase31_research_track_next_action_plan.md
 M docs/design/phase32_p30_bl_002_source_status_index.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_s05_data_provider_scout_research_normalization.md
```
