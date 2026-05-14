# Phase 33 Step 5 - Broad ETF Methodology And No-Lookahead Review Boundary

## Purpose

This document defines methodology-review and no-lookahead/as-of requirements
for the broad-ETF simple moving-average candidate.

It does not approve methodology, parameters, data, an ETF universe, a
benchmark, a cash proxy, reproduction, validation, implementation, or trading
use.

This phase is documentation-only. It adds no data, notebook, script, schema,
test, source code, evaluator, signal computation, trading-path behavior,
broker behavior, runtime behavior, scheduler behavior, persistence behavior,
portfolio behavior, ledger behavior, reconciliation behavior, Alpaca behavior,
ML behavior, or LLM trading-path behavior.

## Candidate Restatement

Broad-ETF simple moving-average trend-following remains an easier-data
research candidate for review only.

The candidate is not validated, implemented, trading-ready, production-ready,
or actionable. It has no approved methodology, moving-average parameter, ETF
universe, data source, benchmark, cash proxy, reproduction protocol,
validation route, signal definition, evaluator, or implementation path.

## Methodology Review Scope

Before any future reproduction, a methodology review must document and assess
at least the following items:

- moving-average trend-following concept
- price-only versus total-return input decision
- daily versus monthly evaluation cadence
- signal observation date versus action date
- cash/benchmark comparison rules
- transaction-cost, spread, slippage, rebalance, fund-expense, and friction
  assumptions
- parameter-selection discipline
- safeguards against performance-driven parameter choice
- safeguards against cherry-picked ETF universe construction
- how universe, benchmark, source, and parameter decisions are separated from
  result inspection
- limitations of applying a simple moving-average rule to broad ETFs
- criteria that would keep the method methodology-only rather than
  reproduction-ready

No moving-average window, price field, cadence, rebalance rule, comparison
rule, cost/friction assumption, universe rule, benchmark rule, cash-proxy rule,
or parameter is approved in this phase.

## No-Lookahead / As-Of Requirements

Any future protocol must satisfy these no-lookahead and as-of requirements
before data use, reproduction, validation, or implementation can be considered:

- signals must use only prices available as of the decision timestamp
- adjusted close and adjusted OHLC data must be treated carefully because
  provider adjustments, corrections, dividends, splits, and corporate-action
  handling may be revised or restated
- ETF inception dates, first usable observations, listing dates, fund closures,
  mergers, ticker changes, and delistings must be respected
- benchmark and cash-proxy data must be aligned by availability date,
  publication timing, frequency, holiday calendar, and revision/vintage rules
- dividend and split adjustments must not introduce future information
  silently
- universe membership must be defined before result inspection
- no same-day close-to-close assumption is allowed unless explicitly justified
  in a later protocol
- action timing must be lagged after signal observation in any future protocol
- source timestamps, timezones, market sessions, missing sessions, stale
  observations, duplicate dates, and correction timing must be documented
- normal `python -m pytest` must remain offline, deterministic,
  credential-free, and independent of network access, data-provider accounts,
  broker accounts, provider state, and wall-clock state

No no-lookahead audit is completed in this phase.

## Methodology Evidence Standards

Any future methodology review must document:

- source references for moving-average trend-following
- selected cadence rationale
- selected parameter rationale
- comparison target, such as buy-and-hold, cash, T-bill, or another benchmark
  candidate
- non-claims, including no profitability, trading-readiness,
  implementation-readiness, or production-threshold claim
- limitations
- sensitivity and robustness expectations
- out-of-sample or holdout expectations if applicable
- why the method is suitable for a deterministic research workflow
- how parameter, universe, source, and benchmark choices were made before
  result inspection
- how no-lookahead, survivorship, corporate-action, and revision risks would
  be audited later
- why normal project tests would remain offline, credential-free, and free of
  data-provider or broker dependencies

Evidence may support future review routing only. It cannot by itself approve a
methodology, parameter, source, universe, benchmark, reproduction, validation,
signal definition, evaluator, or implementation.

## Required Future Non-Claims

Any future methodology review must state that it cannot prove:

- profitability
- live or paper trading readiness
- production threshold validity
- strategy generalization
- `ValidatedResearchArtifact` eligibility
- `ValidatedSignalDefinition` eligibility
- implementation approval
- source approval
- ETF universe approval
- benchmark or cash-proxy approval
- moving-average parameter approval
- data license, archival, private-repository, or offline-use approval

## Relationship To Current Data-Source Findings

Phase 33 Step 4 remains the current public-source documentation context:

- Stooq and Yahoo Finance / yfinance remain source-review candidates only.
- Nasdaq Data Link and Alpha Vantage remain secondary/check candidates only.
- ETF issuer pages remain metadata/context only.
- FRED remains a cash/risk-free proxy candidate only.
- Broker historical data remains context only, not a default project source.

No source is approved. Public availability, client-library support, issuer
metadata, API documentation, or macro-series documentation does not approve
data use, a local snapshot, redistribution, private-repository storage,
reproduction, validation, implementation, or trading use.

## Recommended Next Gate

Recommended next docs-only gate: ETF universe shortlist boundary.

That gate should define candidate universe shortlist requirements and
exclusion rules before any performance review. It must not approve a final ETF
universe, acquire data, inspect results, reproduce, validate, implement, or
create signal/evaluator behavior.

Phase 33 Step 6 adds that grouped ETF universe and benchmark/cash proxy
shortlist boundary in
[`phase33_broad_etf_universe_benchmark_shortlist_boundary.md`](phase33_broad_etf_universe_benchmark_shortlist_boundary.md).
It records candidate buckets, example tickers, benchmark/cash proxy
candidates, rejection criteria, relationship to prior gates, explicit
non-goals, and remaining blockers without approving a universe, benchmark,
cash proxy, source, methodology, reproduction, validation, implementation, or
trading use.

Other possible docs-only gates remain:

- benchmark/cash proxy shortlist boundary
- moving-average evidence source package
- reproduction protocol boundary only if data, universe, and benchmark/cash
  proxy are later approved

## Explicit Non-Goals

This phase does not perform or authorize:

- methodology approval
- moving-average parameter approval
- data approval
- ETF universe approval
- benchmark approval
- cash proxy approval
- data acquisition
- data ingestion
- dataset approval
- schema, code, notebook, or script
- backtest
- reproduction
- strategy implementation
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
  reconciliation, Alpaca, ML, or LLM trading-path behavior

## Remaining Blockers

Evaluator implementation and any production route remain blocked by all of the
following:

- no `ValidatedResearchArtifact`
- no `ValidatedSignalDefinition`
- no approved ETF universe
- no selected/approved data source
- no approved benchmark/cash proxy
- no approved methodology or parameters
- no acquired data
- no project-local deterministic reproduction
- no no-lookahead audit
- no production threshold/config provenance
- no implementation-scope approval
- no evaluator tests
- no approved data license or offline-use path
- no approved local snapshot/versioning policy
- no approved total-return versus price-return decision
- no approved dividend/reinvestment treatment
- no approved corporate-action handling policy
- no approved correction/revision policy
- no approved point-in-time/as-of policy
- no approved ETF universe shortlist or inactive-fund handling policy
- no approved benchmark/cash-proxy frequency alignment rule
- no approved transaction cost, slippage, spread, rebalance, or friction
  assumption
- no result-review template
- no promotion/rejection decision
- no trading implication or production threshold
