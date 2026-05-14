# Phase 33 Step 15 - Broad ETF Faber Limited Formal Evidence Review

## Purpose

This document records a limited formal evidence review of Mebane T. Faber's
"A Quantitative Approach to Tactical Asset Allocation" for methodology and
context only.

The review determines what the paper can and cannot contribute to the
broad-ETF moving-average research candidate. It extracts source identity,
rule framing, universe, benchmark and cash treatment, methodology relevance,
limitations, bias-control considerations, and transferability constraints.

This phase does not approve evidence, methodology, parameters, data, ETF
universe, benchmark, cash proxy, reproduction, validation, implementation, or
trading use. It adds no production code, tests, dependency, lockfile, data,
fixture, PDF, raw report, notebook, script, schema, backtest, evaluator,
signal definition, broker behavior, runtime behavior, persistence behavior,
or trading-path behavior.

## Primary Source Reviewed

Primary source references reviewed on 2026-05-14:

- SSRN page:
  `https://papers.ssrn.com/sol3/papers.cfm?abstract_id=962461`
- Author-hosted PDF:
  `https://mebfaber.com/wp-content/uploads/2016/05/SSRN-id962461.pdf`

No PDF, raw report, data file, citation export, notebook, script, or fixture
was added to the repository. The source was inspected only to support this
bounded documentation review.

## Source Identity

| Field | Review record |
| --- | --- |
| Source ID | `MA-PRACT-001` |
| Title | "A Quantitative Approach to Tactical Asset Allocation" |
| Author | Mebane T. Faber |
| Year/version reviewed | Author-hosted PDF carrying May 2006 working paper, Spring 2007 Journal of Wealth Management, February 2009 update, and February 2013 update markers; SSRN page records date written February 1, 2013 and last revised March 3, 2014 |
| SSRN ID | 962461 |
| Author-hosted PDF reference | `https://mebfaber.com/wp-content/uploads/2016/05/SSRN-id962461.pdf` |
| Publication/working-paper status | Originally a working paper; published in The Journal of Wealth Management, Spring 2007; later updated in 2009 and 2013 |
| Full-text access status | Full text was inspectable through the author-hosted PDF and SSRN page during this phase; no local artifact was stored |
| Citation reliability | High for source identity, title, author, SSRN ID, and broad publication/update trail; exact archival version alignment remains a follow-up item |
| Evidence status | Limited formal review candidate only; methodology/context evidence only; not validated evidence |

## Methodology Summary

The reviewed primary text frames the method as a simple, mechanical,
price-based moving-average system using the same model and parameter across
asset classes.

Extracted methodology context:

- Moving-average rule framing: buy when the monthly price is above the
  10-month simple moving average; sell and move the allocation to cash when
  the monthly price is below the 10-month simple moving average.
- Cadence: the published model is updated once per month on the last day of
  the month; price movement during the rest of the month is ignored.
- Action timing: the paper states that entry and exit prices are taken at the
  close on the signal day. That is a review finding only, not a project-safe
  no-lookahead execution rule.
- Return construction: unless otherwise noted, the paper uses total-return
  series including dividends and income, updated monthly.
- Cash/risk-free treatment: cash returns are estimated with 90-day Treasury
  bills. Later extensions consider alternative cash management, including
  use of 10-year government bonds instead of Treasury bills.
- Costs/frictions: the base tests exclude taxes, commissions, and slippage.
  A later practical-considerations section discusses management fees,
  commissions, slippage, turnover, and taxes but does not create a
  project-approved cost model.
- Initial asset classes/index proxies: the five-asset GTAA framing uses US
  stocks, foreign stocks, bonds, real estate, and commodities. The data-source
  appendix identifies S&P 500, MSCI EAFE, US 10-year government bonds, GSCI,
  and NAREIT return series.
- Benchmark/comparison approach: the paper compares timing results to buy
  and hold, including an equal-weighted five-asset buy-and-hold portfolio.
  Each timed asset-class allocation is treated independently as either long
  the asset class or in cash.
- Parameter framing: the paper uses a 10-month SMA as the representative
  model and discusses moving-average stability across multiple lengths,
  including 3 to 12 months. This is context only and does not approve any
  project parameter.
- Rebalancing: the FAQ states that asset classes are rebalanced monthly for
  the model. Buy-and-hold rebalancing comments are separate practical context
  and not a project benchmark policy.
- Index proxy and ETF-inception caveat: the historical study is based on
  index/return-series data, including constructed or vendor-provided index
  histories, not on live ETF histories from each ETF's inception date. ETF and
  mutual-fund implementation instruments are discussed only as practical
  context.

## Evidence Relevance

This paper is relevant to the broad-ETF moving-average candidate only as
methodology and tactical-allocation context:

- Broad asset-class trend-following relevance: it gives a simple trend rule
  applied across multiple broad asset classes.
- ETF/TAA relevance: it discusses tactical allocation in a form that could
  later inform questions for broad ETF research, while the reviewed historical
  evidence itself uses index proxies rather than an approved project ETF
  universe.
- Methodology design relevance: it demonstrates a mechanical rule, shared
  parameter framing, monthly update cadence, and independent per-asset
  allocation treatment that can shape later review questions.
- Benchmark/cash treatment relevance: it highlights the need to specify
  buy-and-hold comparison construction, cash/risk-free treatment, and whether
  alternative cash management is part of the candidate or an excluded
  extension.
- Parameter-discipline relevance: its parameter-stability discussion is useful
  as a caution against relying on a single optimized lookback.
- No-lookahead/as-of relevance: the same-close signal/execution statement and
  monthly update cadence identify timing assumptions that a later project
  implementation would need to audit and probably restate as explicit
  as-of-safe rules.

No relevance statement above validates the paper's evidence, approves the
rule, approves the 10-month parameter, approves the universe, approves the
cash proxy, approves the benchmark, or authorizes implementation.

## Bias And Robustness Considerations

Extracted review considerations:

- Out-of-sample / real-time update: the 2013 update treats post-2005 returns
  as out-of-sample because the original paper used results through 2005. This
  is a paper claim and not a project validation result.
- Parameter sensitivity: the paper presents the 10-month SMA as a
  representative rule and discusses similar behavior across several moving
  average lengths. This can inform a later parameter-discipline checklist but
  cannot justify a selected project parameter.
- Lookahead controls: the paper's monthly update cadence limits signal checks
  to month-end, but the same-close entry/exit statement is not sufficient for
  project no-lookahead approval. A later phase must define an as-of-safe
  action convention before reproduction or implementation.
- Survivorship handling: no project-usable survivorship-control procedure was
  extracted for the five-index GTAA study. The literature appendix references
  other trend-following work that adjusted for survivorship and other issues,
  but that is not the same as a verified control in this paper's reviewed
  portfolio test.
- Data-snooping concerns: the text explicitly raises possible moving-average
  optimization/data-mining concerns and responds with cross-parameter and
  cross-market checks. These checks are useful context only.
- Index-proxy and ETF-inception caveats: the historical evidence depends on
  index and constructed return series, some extending long before investable
  ETF analogs existed. This blocks direct transfer to a broad ETF
  implementation candidate.
- Cost/friction assumptions: the base results exclude taxes, commissions, and
  slippage. Practical discussion of fees, turnover, taxes, commissions, and
  slippage does not substitute for a project-local friction model.
- Total-return assumptions: the paper emphasizes total-return series with
  dividends and income, which makes total-return, dividend, corporate-action,
  and adjusted-price policy a required project-local gate.
- Data-source reproducibility: the paper cites Global Financial Data and
  index providers for historical series. The project has not selected or
  approved any equivalent data source.

## Transferability Limits

The following cannot be transferred directly from this paper to the project:

- historical performance figures
- original universe validity
- specific parameter validity
- benchmark validity
- cash/risk-free proxy validity
- cost, slippage, commission, fee, turnover, or tax assumptions
- total-return assumptions
- dividend, distribution, split, or corporate-action handling
- data-source validity
- same-close signal/action timing
- out-of-sample or real-time performance claims
- original index-proxy history
- ETF implementation readiness
- live or paper trading readiness
- broad ETF implementation approval

Any later use would require project-local source, universe, benchmark,
cash-proxy, data, storage, no-lookahead, friction, reproduction, validation,
and implementation gates.

## Disposition

Cautious disposition labels for Faber:

- methodology context
- practitioner/TAA context
- benchmark/context
- cash-treatment context
- parameter-discipline context
- no-lookahead/as-of caution context
- requires project-local reproduction
- not validated evidence
- not implementation-ready

This disposition does not approve the source as evidence, approve any
methodology, approve any parameter, approve any ETF universe, approve any data
source, approve any benchmark or cash proxy, approve any reproduction route,
approve any evaluator, or imply trading readiness.

## Required Follow-Up

Before any later promotion, the project must:

- verify the exact version reviewed and decide whether SSRN metadata, author
  PDF, journal text, or another archival version is authoritative for review
- extract exact tables and figures only if needed in a later result-review
  phase
- compare paper assumptions to project source, universe, benchmark, cash
  proxy, and storage gates
- check total-return, dividend, distribution, split, and corporate-action
  assumptions against any later data source
- define any project-local reproduction only in a later phase
- define a project-safe no-lookahead action convention only in a later phase
- review ETF-ACADEMIC-001 separately if full text becomes available
- review Zakamulin separately if selected as a formal candidate
- keep "Simple Market Timing with Moving Averages" unresolved unless an exact
  primary source is later identified

## Recommended Next Gate

Recommended next docs-only gate: ETF-ACADEMIC-001 full-text verification /
limited review if accessible.

Rationale: Faber now supplies limited methodology/TAA context, but it is not
ETF-specific enough to support synthesis or implementation by itself. The next
most useful route is to determine whether the ETF-specific academic candidate
has accessible full text for a similarly limited review. If it is not
accessible, formal evidence review should pause until more primary texts are
available.

This recommendation does not approve ETF-ACADEMIC-001, Faber, Zakamulin, any
source, methodology, parameter, universe, benchmark, cash proxy, data source,
reproduction, validation, implementation, or trading use.

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
- no ETF-ACADEMIC-001 full-text review
- no Zakamulin full-text review
- no approved total-return versus price-return decision
- no approved dividend/reinvestment treatment
- no approved corporate-action handling policy
- no approved correction/revision policy
- no approved point-in-time/as-of policy
- no approved transaction cost, slippage, spread, rebalance, fund-expense,
  tax, or friction assumption
- no benchmark/cash/risk-metric approval
- no result-review template for Faber-derived claims
- no promotion/rejection decision
- no trading implication or production threshold
