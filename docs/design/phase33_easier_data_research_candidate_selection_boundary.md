# Phase 33 Step 1 - Easier-Data Research Candidate Selection Boundary

## Purpose

This document selects a cautious next easier-data research candidate shortlist
for documentation-only investigation after S05 was routed to backlog.

It does not validate, implement, reproduce, backtest, score, rank, approve, or
make any strategy actionable. It does not select or approve any dataset,
schema, source package, reproduction protocol, production threshold,
`ValidatedResearchArtifact`, or `ValidatedSignalDefinition`.

This phase is documentation-only. It adds no data, notebook, script, schema,
test, source code, evaluator, signal computation, trading-path behavior, or
broker/runtime behavior.

## Why S05 Is Paused

S05 remains useful as a public-document-supported proxy/partial planning
candidate. The existing S05 work records methodology interest, data-source
questions, proxy-route limits, and overclaiming controls that may be useful if
future evidence, access, budget, or owner preference changes.

S05 exact reproduction, dataset approval, schema design, project-local
reproduction, validation, and implementation remain paused. The project has
not selected a provider, source category, dataset, schema, reproduction
protocol, validation route, or implementation path for S05.

The next research-track effort should prioritize easier data availability,
clearer licensing review, simpler offline reproducibility, and stronger
non-claims before any strategy-specific implementation discussion.

## Candidate Evaluation Criteria

The criteria below are routing criteria only. They are not validation criteria
and cannot approve a strategy.

| Criterion | Desired boundary |
| --- | --- |
| Public or easy-access data availability | Candidate can plausibly be reviewed with publicly available or low-friction data sources, subject to a later exact source package. |
| Clear licensing / local research use | Candidate has a plausible path to documenting local research use, offline snapshots, and redistribution limits before any data is used. |
| Offline reproducibility | Candidate can plausibly be snapshotted and replayed locally without credentials or network access in normal `python -m pytest`. |
| Simple universe definition | Candidate can be expressed through a small, explicit universe with clear inclusion and exclusion labels. |
| Low PIT/as-of complexity | Candidate has simpler observation, publication, and availability timing than S05 futures contract data. |
| Low survivorship complexity | Candidate avoids, minimizes, or explicitly labels survivorship risk before any stronger claim. |
| Clear benchmark/comparison target | Candidate can define a comparison target without implying profitability, trading readiness, or production readiness. |
| Useful for deterministic research workflow | Candidate can exercise source-package, evidence-review, non-claim, and offline-replay discipline. |
| Fit with existing core architecture | Candidate can remain advisory, pre-risk, code-free for now, and outside broker/runtime/trading paths. |
| Low risk of overclaiming | Candidate can be framed as methodology or source-review work without implying validated edge. |
| No vendor contact dependency | Candidate should not require immediate vendor outreach, account credentials, or bespoke access negotiation. |
| No immediate implementation requirement | Candidate can proceed through docs-only source review before any code, schema, data, or tests. |

## Candidate Families Compared

The candidate-family labels below are planning labels only. They are not
selected strategies, selected datasets, approved sources, approved universes,
or implementation paths.

| Candidate family | Main planning use | Primary caution |
| --- | --- | --- |
| Equity index momentum / trend-following using public index or ETF data | Easier-data momentum review with explicit index or ETF universe labels. | Index/ETF data can still have licensing, adjustment, inception, and benchmark-definition gaps. |
| Equity cross-sectional momentum using public/free data | Compare relative momentum methodology with common public-data constraints. | Survivorship, delisting, corporate-action, and point-in-time universe issues are material. |
| Simple moving-average trend-following on broad ETFs | Cautious single-asset or small-universe trend candidate with simple rule documentation. | Familiarity can invite overclaiming before source, benchmark, and no-lookahead review. |
| Volatility targeting or risk-parity style allocation using public ETF/index data | Review deterministic allocation/risk-normalization methodology with easy price inputs. | Can blur into portfolio/risk approval if not kept as research-methodology only. |
| Pairs/spread research where data and benchmark constraints are clear | Possible later spread-methodology candidate if pair definition, benchmark, and costs are explicit. | Requires strong pair-selection discipline, cost assumptions, benchmark clarity, and overfitting controls. |
| S05 futures time-series momentum | Preserve as a future backlog candidate with high methodological interest. | Exact data, licensing, universe, roll, and offline reproduction remain unresolved. |

## Comparison Table

Favorable entries mean safer for the next docs-only source-review step. They
do not mean better expected returns, validation, implementation readiness, or
trading readiness.

| Candidate family | Data availability | Licensing clarity | Offline reproducibility | PIT/survivorship complexity | Benchmark clarity | Implementation distance | Overclaiming risk | Recommended status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Equity index momentum / trend-following using public index or ETF data | High in principle, pending exact source package | Medium; source terms must be checked | Medium to high if a snapshot policy is later approved | Low to medium; index methodology and ETF inception still matter | Medium to high if benchmark is same index/ETF family | Medium; still requires source, schema, reproduction, and review gates | Medium | Shortlist for source review only |
| Equity cross-sectional momentum using public/free data | Medium; broad free equity data exists but quality varies | Low to medium; provider and redistribution terms vary | Medium only after universe snapshot rules exist | High because survivorship, delisting, and corporate actions dominate | Medium; benchmark and universe timing can drift | Farther; needs stricter universe and PIT controls | High | Defer from first shortlist; keep as caveated later candidate |
| Simple moving-average trend-following on broad ETFs | High in principle for a small explicit ETF universe | Medium; exact data-source terms still required | High if later snapshot and access-date rules are approved | Low to medium; ETF inception and adjustment semantics remain | High if compared to buy-and-hold or cash-style reference only as methodology context | Nearest, but still no code or schema now | Low to medium with strong non-claims | Primary source-review candidate |
| Volatility targeting or risk-parity style allocation using public ETF/index data | Medium to high for broad ETFs/indexes | Medium; source and derived-stat terms must be reviewed | Medium to high if later snapshot rules are approved | Low to medium for small ETF/index universes | Medium; benchmark must avoid implying risk approval | Medium to far because allocation/risk semantics need tighter boundaries | Medium | Secondary source-review candidate |
| Pairs/spread research with clear data and benchmark constraints | Medium for simple listed instruments | Medium; source terms and derived spread use need review | Medium if exact pair and snapshot are fixed | Medium; pair selection timing and corporate actions matter | Low to medium unless benchmark is explicit | Farther; selection and cost assumptions add complexity | Medium to high | Defer unless a later prompt narrows constraints |
| S05 futures time-series momentum | Low to medium without vendor/source contact | Low until provider/source rights are resolved | Low until deterministic snapshot rights and roll semantics exist | High due futures universe, contracts, rolls, and historical coverage | Medium for paper-level context, low for local reproduction | Far | High | Keep in backlog |

## Decision

Conservative decision: choose a short list of easier-data candidates for
further docs-only source review, without approving implementation.

Shortlisted for further source review only:

1. Simple moving-average trend-following on broad ETFs.
2. Equity index momentum / trend-following using public index or ETF data.
3. Volatility targeting or risk-parity style allocation using public ETF/index
   data.

The primary first candidate for the next gate should be simple moving-average
trend-following on broad ETFs because it has the simplest universe, clearest
benchmark framing, lowest initial PIT/survivorship complexity, and shortest
path to a source-package feasibility review.

The equity index momentum and volatility-targeting/risk-parity families remain
secondary shortlist items. They should be used only if the primary candidate's
source package fails licensing, offline snapshot, or benchmark clarity checks,
or if a later prompt explicitly selects one for source review.

Equity cross-sectional momentum is not selected for the first source-review
gate because survivorship, delisting, corporate-action, and point-in-time
universe complexity are too likely to dominate the first easier-data pass.

Pairs/spread research is not selected for the first source-review gate because
pair selection, costs, benchmark definition, and overfitting controls need
tighter constraints before it can be considered easier-data.

S05 remains in backlog.

## Recommended Next Gate

Recommended next docs-only gate: source package for the selected easier-data
candidate, starting with simple moving-average trend-following on broad ETFs.

Phase 33 Step 2 adds that candidate-only source package in
[`phase33_broad_etf_moving_average_source_package.md`](phase33_broad_etf_moving_average_source_package.md).
The package prepares source review only. It does not select or approve an ETF
universe, data source, dataset, benchmark, parameter, signal definition,
schema, reproduction protocol, validation route, implementation route, or
trading implication.

That source package should identify candidate source documents or datasets,
licensing/offline-use terms, exact universe labels, benchmark/comparison
target, access-date and snapshot expectations, point-in-time assumptions,
survivorship and adjustment caveats, non-claims, and source gaps.

The next gate must still avoid data acquisition, ingestion, schema design,
backtesting, reproduction, evaluator implementation, signal computation, and
validated-artifact creation.

If the primary source package cannot stay public/easy-access, licensing-clear,
offline-safe, and non-claiming, route to a public-data feasibility review for
the remaining shortlist or backlog update only.

## Explicit Non-Goals

This phase does not perform or authorize:

- implementation
- data acquisition
- data ingestion
- dataset approval
- source approval
- schema, code, notebook, or script
- backtest
- reproduction
- signal or evaluator implementation
- signal computation
- signal scoring, ranking, direction, confidence, or actionability
- `ValidatedResearchArtifact`
- `ValidatedSignalDefinition`
- new contract type
- production threshold
- production-readiness claim
- implementation-readiness claim
- profitability, actionability, or trading implication
- broker, OMS, runtime, scheduler, persistence, portfolio, ledger,
  reconciliation, Alpaca, ML, or LLM trading-path behavior

## Remaining Blockers

Evaluator implementation and any production route remain blocked by all of the
following:

- no `ValidatedResearchArtifact`
- no `ValidatedSignalDefinition`
- no selected/approved dataset
- no selected/approved source package
- no project-local deterministic reproduction
- no production threshold/config provenance
- no applied no-lookahead audit
- no implementation-scope approval
- no evaluator tests
- no data acquisition or ingestion approval
- no schema or storage policy approval
- no benchmark/comparison target approval
- no offline snapshot approval
- no licensing/offline-use review for a selected source
- no candidate-specific source review
- no validated signal definition binding
- no trading implication or production threshold
