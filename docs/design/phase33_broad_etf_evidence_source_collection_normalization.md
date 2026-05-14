# Phase 33 Step 12 - Broad ETF Evidence Source Collection Normalization

## Purpose

This document normalizes externally collected moving-average evidence-source
candidates into the project research trail for the broad-ETF simple
moving-average candidate.

The external Perplexity collection is treated as scout and intake material
only. It is not evidence approval, source-of-truth material, methodology
validation, parameter approval, data approval, universe approval, benchmark
approval, reproduction approval, validation approval, implementation approval,
or trading approval.

This phase adds no data, fixture, notebook, script, schema, test, source code,
evaluator, signal computation, signal scoring, broker behavior, OMS behavior,
runtime behavior, scheduler behavior, persistence behavior, portfolio
behavior, ledger behavior, reconciliation behavior, Alpaca behavior, ML
behavior, vectorbt behavior, QuantConnect behavior, notebook runtime behavior,
or LLM trading-path behavior.

## External Artifact Status

External artifact intake record:

- Artifact title: Perplexity moving-average evidence-source collection report.
- Source/tool: external Perplexity research.
- Date reviewed in this phase: 2026-05-14.
- Files/links reviewed in this repository: none. The project received an
  external report summary; no raw report, source PDF, notebook, data file, or
  citation export is added here.
- Source type: external-tool inference and scout research.
- Allowed status: scout, context, candidate evidence only after later
  primary-source verification, or reject for direct evidence.
- Repository placement: normalized into `docs/design` as a reviewed boundary
  document, not as raw external output.
- Normal pytest impact: none.

Phase 34 artifact-intake rules apply:

- Primary-source candidates must be separated from secondary summaries,
  practitioner context, external-tool inference, and unresolved claims.
- LLM or hosted-tool claims are not evidence by themselves.
- Exact source identity, citation, authorship, version, access date, and
  primary text remain unresolved until later verification.
- Any claim about performance, methodology, benchmark, data treatment,
  costs/frictions, robustness, or broad-ETF transfer remains unaccepted until
  reviewed against primary material and project constraints.

## Normalized Source Groups

Academic/formal methodology candidates:

- `MA-ACADEMIC-001`: "Simple Market Timing with Moving Averages".
- `MA-ACADEMIC-002`: "Time Series Momentum".
- `MA-ACADEMIC-003`: AQR time-series momentum factor data or methodology
  documentation.
- `MA-ACADEMIC-004`: "Simple and Effective Market Timing with Tactical Asset
  Allocation".
- `MA-ACADEMIC-005`: reported time-series momentum across equity and commodity
  markets.
- `MA-ACADEMIC-006`: reported adaptive versus simple moving-average trading
  systems.

ETF-specific candidates:

- `ETF-ACADEMIC-001`: "Testing moving average trading strategies on ETFs".
- `ETF-ACADEMIC-002`: reported ETF-specific benchmark, friction, or
  implementation-context references, exact citations still unresolved.

Practitioner and tactical allocation candidates:

- `MA-PRACT-001`: Faber, "A Quantitative Approach To Tactical Asset
  Allocation".
- Other practitioner references remain context only until primary methods,
  data, costs, limitations, and citation details are verified.

Benchmark, cash, and risk-metric candidates:

- `MA-BENCH-001`: reported benchmark, buy-and-hold, cash proxy, risk-free, or
  risk-metric references from the external report, exact citations still
  unresolved.

Friction and cost candidates:

- `MA-FRICTION-001`: reported transaction-cost, spread, slippage, turnover,
  expense, tax, or rebalance-friction references from the external report,
  exact citations still unresolved.

Bias, no-lookahead, and backtest-bias candidates:

- `MA-BIAS-001`: reported no-lookahead, survivorship, data-snooping,
  overfitting, and backtest-bias references from the external report, exact
  citations still unresolved.

Context-only or weak sources:

- ETFdb strategy articles.
- ETFtrends articles.
- Schwab educational content.
- ETFreplay pages or tool examples.
- Personal blogs.
- Secondary summaries and search-result style writeups.

Rejected or unsupported direct-evidence sources:

- The Perplexity report text itself as direct evidence.
- Any blog, tool, marketing, educational, or secondary source used as direct
  performance evidence without primary-source support.
- Any source that cannot identify rule definitions, universe, period,
  frequency, return construction, benchmark, costs/frictions, and bias
  controls well enough for later review.

## Candidate Intake Table

Rows below are intake records only. They do not approve sources, evidence,
claims, methodology, parameters, data, universe, benchmark, cash proxy,
reproduction, validation, implementation, evaluator behavior, signal behavior,
or trading use.

| Source ID | Title / citation | Source type | Category | Strategy / rule discussed | Universe / asset class | Period / frequency if known | Key claim to verify later | Evidence-quality label | Bias-control relevance | Cost/friction relevance | Broad ETF relevance | Current disposition | Follow-up required |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ETF-ACADEMIC-001 | "Testing moving average trading strategies on ETFs"; full citation unresolved | Academic/formal candidate | ETF-specific | Moving-average timing rules on ETFs | ETFs; exact universe unresolved | Unknown from scout summary | Verify exact rules, ETF set, sample period, frequency, benchmark, costs, and reported limitations | High-priority formal review candidate; requires primary-source verification | Potentially direct; controls unknown | Potentially direct; assumptions unknown | Direct candidate, not approved | Review candidate | Obtain full text; verify citation, authorship, data construction, costs, bias controls, and transfer limits |
| MA-ACADEMIC-001 | "Simple Market Timing with Moving Averages"; full citation unresolved | Academic/formal candidate | Core moving-average methodology | Simple moving-average timing | Broad market or asset-class context unresolved | Unknown from scout summary | Verify whether rule definitions, parameter rationale, return treatment, and benchmark handling are usable for methodology review | High-priority formal review candidate; requires primary-source verification | Unknown until full text | Unknown until full text | Possible methodology transfer only | Review candidate | Obtain full text; extract exact rule, universe, frequency, benchmark, limitations, and non-claims |
| MA-ACADEMIC-002 | "Time Series Momentum"; full citation unresolved | Academic/formal candidate | Time-series trend-following methodology | Time-series momentum or trend-following rules | Multi-asset or futures context reported; exact universe unresolved | Unknown from scout summary | Verify trend-following method, robustness, OOS treatment, and what cannot transfer to ETFs | High-priority formal review candidate; requires primary-source verification | Potentially relevant; controls to verify | Potentially relevant; assumptions to verify | Indirect methodology context unless ETF transfer is later justified | Review candidate | Obtain full text; separate methodology evidence from broad-ETF inference |
| MA-ACADEMIC-003 | AQR time-series momentum factor data or methodology documentation; exact citation unresolved | Official data or methodology candidate | Time-series momentum data/methodology context | TSMOM factor construction or documentation | AQR factor universe unresolved | Unknown from scout summary | Verify official methodology, factor construction, data terms, and whether it is context only | Methodology context; requires primary-source verification | Potentially relevant for construction notes | Unknown until documentation review | Indirect context only | Review candidate | Verify official source, terms, fields, construction, and non-transfer limits |
| MA-ACADEMIC-004 | "Simple and Effective Market Timing with Tactical Asset Allocation"; full citation unresolved | Academic/formal candidate | Tactical allocation methodology | Tactical allocation with market-timing rules | Asset allocation universe unresolved | Unknown from scout summary | Verify rule definitions, asset universe, benchmark, costs, robustness, and parameter discipline | Review candidate; requires primary-source verification | Unknown until full text | Unknown until full text | Possible methodology context only | Review candidate | Obtain full text; extract rule, universe, frequency, benchmark, costs, and bias controls |
| MA-ACADEMIC-005 | Reported time-series momentum across equity and commodity markets; full citation unresolved | Academic/formal candidate | Cross-asset trend-following methodology | Time-series momentum across reported equity and commodity markets | Equity and commodity markets reported; exact instruments unresolved | Unknown from scout summary | Verify asset classes, sample, signal timing, robustness, and ETF transfer limits | Review candidate; requires primary-source verification | Potentially relevant; controls to verify | Potentially relevant; assumptions to verify | Indirect context only | Review candidate | Obtain full text; verify whether claims are methodology, performance, or transfer claims |
| MA-ACADEMIC-006 | Reported adaptive versus simple moving-average trading systems; full citation unresolved | Academic/formal candidate | Moving-average system comparison | Adaptive and simple moving-average systems | Universe unresolved | Unknown from scout summary | Verify whether comparisons are parameter-sensitive, data-snooped, or useful only as cautionary context | Review candidate; requires primary-source verification | Potentially relevant for parameter-sensitivity questions | Unknown until full text | Indirect context only | Review candidate | Obtain full text; extract methodology, sample, parameter-selection discipline, and limitations |
| MA-PRACT-001 | Faber, "A Quantitative Approach To Tactical Asset Allocation"; version and citation unresolved | Practitioner research candidate | Tactical allocation and trend-following | Moving-average based tactical allocation | Asset classes or ETFs unresolved from scout summary | Unknown from scout summary | Verify exact rules, return series, benchmark, costs, rebalance timing, and limitations | Review candidate; methodology context; requires primary-source verification | Unknown until full text | Unknown until full text | Possible methodology context only | Review candidate | Obtain reviewed version; identify rule definitions, data construction, and non-claims |
| ETF-ACADEMIC-002 | Reported ETF benchmark or friction reference(s); exact citation unresolved | Academic/formal or methodology candidate | ETF-specific benchmark/friction | Benchmark, cost, or implementation assumptions for ETF studies | ETFs or market benchmarks unresolved | Unknown from scout summary | Verify whether the reference supports benchmark/cash/friction review rather than performance evidence | Benchmark/friction context; requires primary-source verification | Unknown until source identified | Potentially direct; assumptions to verify | Possible direct context, not approved | Requires primary-source verification | Identify exact source(s); then extract benchmark, cost, spread, slippage, turnover, expense, and tax assumptions |
| MA-BENCH-001 | Selected benchmark, cash, or risk-metric references from external report; exact citations unresolved | Benchmark/methodology candidate | Benchmark, cash, and risk metrics | Buy-and-hold, cash proxy, risk-free, or risk metrics | Universe depends on source | Unknown from scout summary | Verify benchmark definitions, cash proxy treatment, compounding, frequency alignment, and limitations | Benchmark/friction context; requires primary-source verification | Indirect | Possible cash or metric assumptions | Context for broad-ETF review only | Requires primary-source verification | Identify exact sources; extract benchmark and cash-proxy construction before any comparison route |
| MA-FRICTION-001 | Selected transaction-cost and friction references from external report; exact citations unresolved | Friction/cost candidate | Costs and frictions | Transaction costs, spreads, slippage, turnover, expenses, taxes, rebalance friction | Universe depends on source | Unknown from scout summary | Verify cost models and whether they apply to broad ETFs without overclaiming | Benchmark/friction context; requires primary-source verification | Indirect | Direct context if source is suitable | Context for broad-ETF review only | Requires primary-source verification | Identify exact sources; extract cost assumptions, dates, markets, and limitations |
| MA-BIAS-001 | Selected no-lookahead, survivorship, data-snooping, or backtest-bias references from external report; exact citations unresolved | Bias-control candidate | Bias and robustness controls | Bias-control methodology, not a trading rule | General research methodology or market data context | Unknown from scout summary | Verify controls for lookahead, survivorship, data snooping, overfitting, OOS, and parameter sensitivity | Bias-control context; requires primary-source verification | Direct methodology context | Indirect | Required guardrail context, not direct ETF evidence | Requires primary-source verification | Identify exact sources; extract checklist items and limitations for later review |
| MA-CONTEXT-001 | ETFdb, ETFtrends, Schwab educational content, ETFreplay, personal blogs, and secondary summaries | Secondary, educational, marketing, tool, or blog context | Context only | Strategy terminology, examples, source discovery, or tool framing | Usually ETFs or broad market examples; exact scope varies | Varies | Verify only whether they point to primary sources or clarify terminology; do not use direct performance claims | Context only; reject for direct evidence | Weak unless they cite primary bias controls | Weak unless they cite primary cost assumptions | Terminology/source-discovery only | Context only; reject for direct performance evidence | Use only to locate primary sources or define review questions |
| EXT-SCOUT-001 | Perplexity evidence-source collection report summary supplied externally | External-tool inference | Scout research | Source discovery and preliminary grouping | Not applicable | 2026-05-14 project intake | Verify every cited source, inferred claim, and classification before any reliance | Requires primary-source verification; external-tool inference | Not evidence | Not evidence | Scout input only | Scout only; not evidence | Preserve as intake context; do not cite as support for methodology, performance, or implementation |

## Strongest Candidates For Later Formal Review

The strongest review candidates are:

- `ETF-ACADEMIC-001`
- `MA-ACADEMIC-001`
- `MA-ACADEMIC-002` and `MA-ACADEMIC-003`
- `MA-ACADEMIC-004`
- `MA-ACADEMIC-005`
- `MA-ACADEMIC-006`
- `MA-PRACT-001`
- `ETF-ACADEMIC-002` and selected benchmark/friction references, only after
  exact citations are identified

Inclusion means review candidate only. It does not approve the source, accept
the source's claims, validate moving-average methodology, approve a parameter,
approve broad-ETF transfer, approve data, approve a benchmark or cash proxy,
approve costs, approve reproduction, approve validation, or authorize
implementation.

## Context-Only / Weak-Source Handling

Blog, tool, marketing, educational, and secondary sources may be useful for:

- terminology
- examples of how practitioners describe moving-average timing
- discovering primary sources
- identifying questions for later review
- spotting benchmark, friction, or bias-control topics to verify elsewhere

They must not be used as direct performance evidence, methodology approval,
parameter justification, source approval, benchmark approval, cash-proxy
approval, broad-ETF transfer proof, validation evidence, implementation
guidance, or trading support.

If a context-only source makes a performance or implementation-readiness claim,
that claim is rejected for direct evidence unless a later phase verifies the
underlying primary source and records the exact claim, data, method, costs,
bias controls, and limitations.

## Required Follow-Up Before Formal Review

Before any formal review, the project must:

- obtain or inspect full primary texts
- verify citations and authorship
- extract exact rule definitions
- extract universe, date range, frequency, and benchmark
- verify price-return versus total-return treatment
- identify dividend, split, and corporate-action handling
- identify transaction-cost and friction assumptions
- identify OOS, robustness, and parameter-sensitivity treatment
- identify lookahead, survivorship, and data-snooping controls
- identify what can transfer to broad ETFs
- record limitations and non-claims

Any missing item remains a blocker. Unknowns must not be inferred into
approval.

## Evidence Grading Proposal

Provisional grading vocabulary for later intake:

| Label | Meaning |
| --- | --- |
| high-priority formal review candidate | Source appears highly relevant for later review, but no claim is accepted. |
| review candidate | Source appears worth later review after citation and primary-text checks. |
| methodology context | Source may frame rule-definition, cadence, parameter, robustness, or transfer questions. |
| bias-control context | Source may frame lookahead, survivorship, data-snooping, overfitting, OOS, or robustness checks. |
| benchmark/friction context | Source may frame benchmark, cash proxy, risk metric, cost, spread, slippage, turnover, expense, tax, or rebalance-friction questions. |
| context only | Source may support terminology, examples, or source discovery only. |
| reject for direct evidence | Source or claim must not support performance, methodology, validation, or implementation directly. |
| requires primary-source verification | Overlay label meaning no reliance is permitted until primary material is inspected and cited. |

These labels support routing only. They do not approve evidence, methodology,
parameters, source data, universe, benchmark, cash proxy, data acquisition,
reproduction, validation, implementation, evaluator behavior, signal behavior,
production thresholds, or trading use.

## Relationship To Prior Gates

This normalization depends on and preserves these gates:

- Phase 33 Step 10, the broad-ETF moving-average evidence source package,
  defined evidence categories and review questions but did not collect or
  approve sources.
- Phase 33 Step 11, the broad-ETF moving-average evidence intake plan,
  defined how sources should be collected, classified, downgraded, and
  dispositioned before formal review.
- Phase 34 Step 1, the external research integration boundary, keeps
  Perplexity and similar tools advisory only.
- Phase 34 Step 2, the external research artifact intake checklist, requires
  metadata, evidence labels, review questions, routing, and non-goals before
  external artifacts can influence decisions.
- Phase 34 Step 3, the notebook/prototype policy boundary, keeps notebooks,
  prototype scripts, hosted outputs, vectorbt, QuantConnect, spreadsheets,
  charts, copied snippets, and external reports exploratory unless later
  promoted through a deterministic path.
- Phase 33 Step 9, the data storage and fixture policy boundary, still blocks
  data acquisition, data files, fixtures, local snapshots, and normal pytest
  dependencies until later scoped approval.

This phase does not weaken prior evidence, data, source, universe, benchmark,
cash proxy, storage, fixture, reproduction, validation, implementation, or
trading gates.

## Recommended Next Gate

Recommended next route: pause until full primary texts are obtained or
inspectable for at least one to three high-priority candidates.

The project should not start the first limited methodology evidence review
from the Perplexity summary alone. If full primary texts become available, the
next docs-only gate may be a first limited methodology evidence review using a
small set such as `ETF-ACADEMIC-001`, `MA-ACADEMIC-001`, and either
`MA-ACADEMIC-002` or `MA-ACADEMIC-003`.

Bias/no-lookahead and benchmark/friction reviews should wait until their exact
candidate sources and primary texts are identified.

## Explicit Non-Goals

This phase does not perform or authorize:

- evidence approval
- methodology approval
- parameter approval
- universe approval
- source approval
- benchmark approval
- cash proxy approval
- data acquisition
- data download
- data ingestion
- data files
- fixtures
- schema, code, notebook, or script
- backtest
- reproduction
- evaluator or signal implementation
- signal computation
- signal scoring, ranking, direction, confidence, or actionability
- `ValidatedResearchArtifact`
- `ValidatedSignalDefinition`
- new contract type
- production threshold
- profitability claim
- production-readiness claim
- implementation-readiness claim
- trading implication
- broker, OMS, runtime, scheduler, persistence, portfolio, ledger,
  reconciliation, Alpaca, ML, vectorbt, QuantConnect, notebook runtime, or LLM
  trading-path behavior

## Remaining Blockers

Evaluator implementation and any production route remain blocked by all of the
following:

- no `ValidatedResearchArtifact`
- no `ValidatedSignalDefinition`
- no approved evidence review
- no approved methodology or parameters
- no approved ETF universe
- no selected/approved data source
- no approved benchmark/cash proxy
- no approved final data storage/fixture policy
- no acquired data
- no project-local deterministic reproduction
- no no-lookahead audit
- no production threshold/config provenance
- no implementation-scope approval
- no evaluator tests
- no source-specific primary-text verification
- no verified citation metadata for the external source list
- no reviewed practitioner-source classification
- no approved total-return versus price-return decision
- no approved dividend/reinvestment treatment
- no approved corporate-action handling policy
- no approved correction/revision policy
- no approved point-in-time/as-of policy
- no approved transaction cost, slippage, spread, rebalance, fund-expense, tax,
  or friction assumption
- no robustness or parameter-sensitivity review
- no benchmark/cash/risk-metric review
- no result-review template
- no promotion/rejection decision
- no trading implication or production threshold
