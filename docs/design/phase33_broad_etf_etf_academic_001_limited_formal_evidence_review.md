# Phase 33 Step 16 - Broad ETF ETF-ACADEMIC-001 Limited Formal Evidence Review

## Purpose

This document records a limited formal evidence review of Huang and Huang,
"Testing moving average trading strategies on ETFs," for ETF-specific
methodology and context only.

The review determines what `ETF-ACADEMIC-001` can and cannot contribute to
the broad-ETF moving-average research candidate. It extracts source identity,
ETF-specific moving-average framing, benchmark and comparison framing,
risk-adjusted evaluation context, implementation and friction cautions,
bias-control considerations, transferability limits, and follow-up items.

This phase does not approve evidence, methodology, parameters, data, ETF
universe, benchmark, cash proxy, reproduction, validation, implementation, or
trading use. It adds no production code, tests, dependency, lockfile, data,
fixture, PDF, raw report, notebook, script, schema, backtest, evaluator,
signal definition, broker behavior, runtime behavior, persistence behavior,
or trading-path behavior.

## Primary Sources Reviewed

Primary source references reviewed on 2026-05-14:

- SSRN working-paper page:
  `https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3138690`
- SSRN working-paper delivery reference reported by the primary page:
  `https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID3138690_code451942.pdf?abstractid=3138690&mirid=1&type=2`
- ScienceDirect publisher page:
  `https://www.sciencedirect.com/science/article/pii/S0927539819300830`
- RePEc / EconPapers record:
  `https://econpapers.repec.org/RePEc:eee:empfin:v:57:y:2020:i:c:p:16-32`
- IDEAS/RePEc record:
  `https://ideas.repec.org/a/eee/empfin/v57y2020icp16-32.html`
- Penn State Pure publication record:
  `https://pure.psu.edu/en/publications/testing-moving-average-trading-strategies-on-etfs/`

No PDF, raw report, data file, citation export, notebook, script, or fixture
was added to the repository. The source was inspected only to support this
bounded documentation review. The published Elsevier full text appears
restricted; the SSRN working paper appears openly accessible, but final
published tables, figures, text, or definitions may differ from the working
paper and remain a required follow-up before any later promotion.

## Source Identity

| Field | Review record |
| --- | --- |
| Source ID | `ETF-ACADEMIC-001` |
| Title | "Testing moving average trading strategies on ETFs" |
| Authors | Jing-Zhi Huang; Zhijian (James) Huang |
| Year | 2020 published article; SSRN working paper dated March 12, 2018 |
| Venue | Journal of Empirical Finance, Elsevier, volume 57(C), pages 16-32 |
| DOI | 10.1016/j.jempfin.2019.10.002 |
| RePEc handle | RePEc:eee:empfin:v:57:y:2020:i:c:p:16-32 |
| SSRN working paper ID | 3138690 |
| ScienceDirect publisher reference | S0927539819300830 |
| Working-paper versus published-version access status | SSRN working-paper page and delivery reference appear openly accessible; published Elsevier full text appears restricted / ScienceDirect-subscriber-only |
| Supplementary data/code status | No supplementary data or code was found on the reviewed primary pages |
| Citation reliability | High for title, authors, venue, DOI, RePEc handle, SSRN ID, publisher reference, and publication year |
| Evidence status | Limited formal review candidate only; ETF-specific methodology/context evidence only; not validated evidence |

## Methodology Summary

Extracted methodology context, limited to accessible primary-page text,
verified abstract text, and the reported accessible SSRN working-paper route:

- Moving-average strategy framing: the paper tests moving-average technical
  trading rules in long-only ETF portfolios. The publisher introduction frames
  the basic variable holding length moving-average rule as a crossover rule:
  buy when a short-term moving average crosses above a long-term moving
  average and sell when it crosses below.
- ETF implementation framing: the paper focuses on whether moving-average
  evidence from non-tradable indices, portfolios, or factors transfers to
  tradable ETFs. The reviewed text explicitly distinguishes ETF
  implementation from backtests on non-tradable index or factor series.
- Traditional MA versus QUIMA framing: the paper contrasts a standard daily
  moving-average strategy that trades at the close of a trading day with a
  quasi-intraday moving-average strategy, `QUIMA`, that responds immediately
  after observing crossover signals. This is implementation-friction context
  only, not a project execution rule.
- Buy-and-hold comparison: the paper compares moving-average strategies
  against a passive buy-and-hold benchmark and reports that benchmark choice
  matters for interpretation.
- Zero-return or risk-free benchmark discussion: the publisher abstract notes
  that earlier moving-average evidence often uses zero return or the risk-free
  rate as the benchmark. This is useful benchmark-context framing only and
  does not approve a project cash proxy.
- Risk-adjusted evaluation framing: the paper evaluates ETF moving-average
  strategies using multiple risk-adjusted performance measures and highlights
  factor-adjusted performance measures such as CAPM alpha. The publisher page
  also mentions appraisal ratio context. No project metric is approved.
- ETF/index comparison framing: the publisher page describes comparison of
  moving-average strategies implemented on non-tradable indices with the same
  strategies implemented on corresponding ETFs.
- Opening-gap / implementation-friction framing: the SSRN abstract reports
  that documented index-based moving-average profitability is reduced on ETFs,
  mainly due to more frequent and larger ETF opening gaps than index opening
  gaps. This is a timing and friction caution, not a project result.
- Transaction-cost framing: the publisher page says the strategy section
  presents a simple time-varying transaction cost model to estimate intraday
  transaction cost. Exact cost definitions were not promoted or implemented.
- MA lag-length / parameter framing: the reviewed abstract-level text reports
  that `QUIMA` outperforms the standard close-only version when the long-term
  moving-average lag length is not too long, with the published abstract
  identifying no more than 50 days. The SSRN abstract also flags the 10-day MA
  as having lower performance than neighboring lag lengths. These are
  parameter-discipline cautions only.
- Data-snooping / robustness framing: the SSRN page lists data-snooping bias
  as a keyword and RePEc references include data-snooping literature. Exact
  data-snooping tests, robustness controls, and persistence procedures remain
  follow-up items because this phase does not promote abstract-level claims
  into validated evidence.
- Data framing available at primary-page level: the publisher page indicates
  that the study considers S&P 500, DJIA, and NASDAQ-100 indices with
  corresponding ETFs SPY, DIA, and QQQ/QQQQ, retrieves daily index and ETF
  data from CRSP, and references a broader CRSP ETF sample before
  2016-12-31. Exact universe, filters, sample periods, delisting treatment,
  and return-construction details remain follow-up items.

## Evidence Relevance

`ETF-ACADEMIC-001` is relevant to the broad-ETF moving-average candidate only
as ETF-specific methodology and evaluation context:

- ETF-specific evidence relevance: unlike Faber's reviewed GTAA context, this
  paper explicitly studies moving-average rules on ETFs and asks whether
  index-based evidence survives when applied to tradable ETF instruments.
- ETFs versus non-tradable indices: the ETF/index comparison is directly
  relevant to the project question because it warns against treating index
  backtests as automatically transferable to ETFs.
- Benchmark and risk-adjusted evaluation relevance: the paper's contrast
  between zero-return/risk-free-rate benchmarks, buy-and-hold comparison, and
  factor-adjusted performance measures provides useful review questions for
  later benchmark, cash-proxy, and metric-selection gates.
- Implementation/friction relevance: opening-gap, intraday-response, close
  trading, transaction-cost, and liquidity-related framing identify timing and
  friction issues that a broad-ETF project-local reproduction would need to
  define explicitly.
- Parameter-discipline relevance: the 10-day MA caution and long-term
  lag-length discussion argue against adopting a lag length from the paper
  without project-local design, reproduction, sensitivity review, and
  validation gates.
- No-lookahead/as-of relevance: the standard close-only versus immediate
  `QUIMA` comparison is useful timing context because it separates signal
  observation, trade timing, opening gaps, and return measurement. It does not
  create a project-safe action convention.

No relevance statement above validates the paper's evidence, approves any
rule, approves `QUIMA`, approves a lag length, approves an ETF universe,
approves CRSP or any data source, approves a benchmark, approves a cash proxy,
or authorizes implementation.

## Bias And Robustness Considerations

Extracted review considerations:

- Data-snooping: data-snooping bias is explicitly part of the source's
  keyword framing, and the citation trail references data-snooping literature.
  This indicates that later review must extract the paper's exact controls,
  but this phase does not treat them as validated or sufficient.
- Parameter sensitivity: the reviewed text flags long-term moving-average
  lag-length dependence and a specific 10-day MA concern. These facts are
  useful as parameter-discipline warnings, not as evidence for selecting or
  rejecting any project parameter.
- ETF opening-gap and trading-timing concerns: the paper's reported
  ETF-versus-index performance reduction is tied to more frequent and larger
  ETF opening gaps. Any later project rule must separately define signal
  observation time, action time, fill convention, open/close assumptions, and
  no-lookahead handling.
- Survivorship handling: the publisher page references CRSP ETF data and a
  broad ETF sample, but this phase did not extract a project-usable
  survivorship, delisting, inception, liquidation, or selection-bias control.
  Those controls remain blockers.
- Lookahead handling: the close-only versus `QUIMA` distinction is relevant to
  as-of review, but it does not prove project-safe lookahead controls. A later
  phase must audit signal availability, price availability, corporate-action
  adjustment timing, return construction, and trade timing.
- Transaction-cost/friction handling: the publisher page reports a simple
  time-varying transaction cost model for intraday transaction cost, but exact
  assumptions, estimates, spreads, slippage, fund expenses, taxes, and
  rebalance handling were not promoted to project policy.
- Working-paper versus published-version limits: the accessible SSRN working
  paper path supports limited review, while the final Elsevier text appears
  restricted. Any exact tables, figures, definitions, parameter grids, and
  performance values must be rechecked against the final published version if
  materiality matters later.

## Transferability Limits

The following cannot be transferred directly from this paper to the project:

- performance figures
- ETF universe validity
- specific moving-average lag-length validity
- `QUIMA` implementation readiness
- benchmark validity
- zero-return, risk-free-rate, or cash-proxy validity
- CAPM alpha, appraisal ratio, Sharpe ratio, or factor-model metric approval
- transaction-cost, spread, slippage, liquidity, tax, or fund-expense
  assumptions
- same-day, open, close, intraday, or immediate-response timing assumptions
- opening-gap treatment
- return construction, dividend, distribution, split, or corporate-action
  treatment
- data source validity
- CRSP availability or suitability for this project
- survivorship or delisting handling
- data-snooping or robustness adequacy
- production signal readiness
- trading readiness

Any later use would require project-local source, universe, benchmark,
cash-proxy, data, storage, no-lookahead, friction, reproduction, validation,
and implementation gates.

## Disposition

Cautious disposition labels for `ETF-ACADEMIC-001`:

- ETF-specific methodology context
- benchmark/risk-adjusted-evaluation context
- ETF-versus-index transferability context
- implementation-friction context
- parameter-discipline context
- no-lookahead/timing caution context
- requires project-local reproduction
- not validated evidence
- not implementation-ready

This disposition does not approve the source as validated evidence, approve
any methodology, approve any parameter, approve any ETF universe, approve any
data source, approve any benchmark or cash proxy, approve any reproduction
route, approve any evaluator, or imply trading readiness.

## Required Follow-Up

Before any later promotion, the project must:

- verify whether the SSRN working paper and final published version differ
  materially
- inspect the full working-paper methodology if not already fully reviewed
- extract the exact ETF universe and sample period if needed later
- extract the exact moving-average rules and parameter grid
- extract return construction and dividend/corporate-action treatment
- extract benchmark and cash proxy definitions
- extract costs, frictions, liquidity treatment, and opening-gap assumptions
- extract data-snooping and robustness controls
- extract survivorship, delisting, inception, and sample-construction controls
- extract no-lookahead, as-of, same-day, open, close, and intraday timing
  assumptions
- define project-local reproduction only in a later phase
- compare with the Faber review in a later synthesis

## Recommended Next Gate

Recommended next docs-only gate: broad ETF methodology evidence synthesis
boundary using Faber plus `ETF-ACADEMIC-001`.

Rationale: Faber now supplies limited practitioner/TAA methodology context,
and `ETF-ACADEMIC-001` supplies ETF-specific methodology, benchmark,
risk-adjusted-evaluation, and implementation-friction context. A synthesis
boundary can compare what these two reviewed sources do and do not support
without approving sources, methods, parameters, universe, benchmark, data,
reproduction, validation, implementation, or trading use.

Alternative docs-only gates remain available:

- `ZAKAMULIN-2014` full-text verification / limited review if accessible
- benchmark/friction evidence review
- pause formal evidence review until more primary texts are available

No recommended gate approves evidence, methodology, parameters, data,
universe, benchmark, cash proxy, reproduction, validation, implementation, or
trading use.

## Explicit Non-Goals

This phase does not perform or authorize:

- evidence validation
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
- PDFs added
- fixtures
- schema, code, notebook, or script
- dependency or lockfile changes
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
- no approved source identity for "Simple Market Timing with Moving Averages"
- no Zakamulin full-text review
- no approved total-return versus price-return decision
- no approved dividend/reinvestment treatment
- no approved corporate-action handling policy
- no approved correction/revision policy
- no approved point-in-time/as-of policy
- no approved transaction cost, slippage, spread, rebalance, fund-expense,
  tax, or friction assumption
- no benchmark/cash/risk-metric approval
- no result-review template for ETF-ACADEMIC-001-derived claims
- no comparison synthesis with Faber
- no promotion/rejection decision
- no trading implication or production threshold
