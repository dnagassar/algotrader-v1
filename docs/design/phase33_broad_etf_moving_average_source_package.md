# Phase 33 Step 2 - Broad ETF Moving-Average Source Package

## Purpose

This document prepares source review for a broad-ETF simple moving-average
trend-following candidate.

It does not validate, reproduce, backtest, implement, approve, or make the
candidate actionable. It does not approve any ETF universe, data source,
dataset, benchmark, parameter, signal definition, schema, reproduction
protocol, `ValidatedResearchArtifact`, or `ValidatedSignalDefinition`.

This phase is documentation-only. It adds no data, notebook, script, schema,
test, source code, evaluator, signal computation, trading-path behavior,
broker behavior, runtime behavior, or persistence behavior.

## Candidate Research Question

Bounded research question for later review:

Can simple moving-average trend-following on broad liquid ETFs be evaluated as
an easier-data research candidate under deterministic, offline-safe project
standards?

This question is a source-review prompt only. It is not a profitability claim,
implementation-readiness claim, production-readiness claim, or trading
recommendation.

## Candidate Scope

Possible broad ETF categories for future review only:

- broad U.S. equity index ETFs
- broad international equity ETFs
- broad bond ETFs
- broad commodity or gold ETFs if source quality allows
- cash, T-bill proxy, or risk-free comparison source

No final ETF universe is selected. No ticker, issuer, index family, asset
class mix, benchmark, cash proxy, inclusion rule, exclusion rule, inception
handling rule, or source package is approved in this phase.

## Candidate Methodology Framing

The candidate methodology is framed only at a high level:

- moving-average trend-following concept over broad ETF price history
- possible price-only trend signal family
- possible monthly or daily evaluation cadence
- possible comparison to buy-and-hold or a cash-style proxy
- possible use as deterministic research workflow practice

This phase does not approve moving-average windows, price fields, rebalance
cadence, comparison rules, transaction-cost assumptions, risk settings,
signal direction, score, confidence, rank, actionability, or any executable
strategy definition.

No parameter is approved. No signal definition is approved.

## Possible Public Or Easy Data Sources To Review

The source categories below are candidates for later source review only. They
are not approved sources, approved datasets, approved licenses, or approved
offline-use paths.

| Source category | Possible later review use | Required caution |
| --- | --- | --- |
| Stooq | Candidate ETF price history review where coverage and adjusted-price semantics can be documented. | Must verify symbol identity, adjustments, timestamp/date semantics, licensing, and offline snapshot permission. |
| Yahoo Finance / yfinance | Candidate retail-access price history review where adjusted close and corporate-action fields are documented enough for source review. | Must not assume provider terms, yfinance behavior, adjusted-close semantics, redistribution rights, or stability are acceptable. |
| Nasdaq Data Link, where applicable | Candidate source review for public or low-friction datasets relevant to ETF prices or reference series. | Must verify dataset identity, terms, update/version behavior, credential requirements, and offline-use limits. |
| Alpha Vantage free or retail APIs | Candidate API source review for price data if terms, throttling, adjustment fields, and snapshot feasibility are acceptable. | Must verify credentials, rate limits, license terms, adjusted fields, and whether normal project tests remain credential-free and offline. |
| Broker historical data | Context source only, not the default source for this research route. | Must not introduce broker, account, credential, runtime, or trading-path dependencies. |
| Official ETF issuer pages | Candidate metadata source for fund inception, benchmark index, distributions, fees, holdings summary, and fund identity. | Must verify metadata date, version, redistribution rights, and whether issuer pages can support deterministic local review. |
| FRED, where applicable | Candidate risk-free, T-bill, or cash-proxy context source. | Must verify series definitions, release timing, revision behavior, frequency, timestamp semantics, and offline-use terms. |

Public availability is not license approval. Easy access is not project
approval. A later source-review gate must verify terms, provenance, update
behavior, and offline snapshot constraints before any data can be used.

## Source-Quality Requirements

A later source review must document, at minimum:

- adjusted close or total-return handling expectations
- dividend and split adjustment transparency
- whether raw, adjusted, distribution, and split fields are separately
  available and internally consistent
- timestamp and date semantics, including market close, publication,
  timezone, holiday, and missing-session behavior
- survivorship caveats for any ETF list, index proxy, or available-history
  subset
- delisting, fund closure, ticker change, and inception-date handling
- missing-data handling, stale observations, bad ticks, duplicate dates, and
  calendar alignment expectations
- stable symbol identity across providers, tickers, exchanges, share classes,
  and issuer changes
- local snapshot and versioning possibility, including access date, source
  version, file hashing, and deterministic replay expectations
- license, redistribution, and offline-use clarity before any repository or
  local fixture use
- benchmark comparability across buy-and-hold, ETF benchmark, index proxy,
  cash proxy, or T-bill proxy contexts
- normal `python -m pytest` remains deterministic, offline, credential-free,
  and independent of any data-source account or network access

Any unresolved source-quality item blocks dataset approval, reproduction
approval, signal-definition review, and implementation-scope review.

## Evidence Sources To Collect Later

Later phases may collect and review:

- academic or practitioner references on moving-average trend-following
- public ETF metadata sources
- source documentation for candidate price-data providers
- benchmark and cash-proxy definitions
- transaction-cost, bid-ask spread, slippage, and fund-expense references
- no-lookahead, point-in-time, survivorship, and data-snooping methodology
  references

This phase does not perform a full literature review and does not accept any
evidence source as sufficient for validation.

## Review Gates

Future docs-only gates should remain separate and non-promoting:

1. Public data source feasibility review.
2. ETF universe definition boundary.
3. Benchmark and cash-proxy boundary.
4. Methodology-only moving-average review.
5. No-lookahead and as-of review.
6. Reproduction protocol boundary.
7. Result-review template.
8. Promotion or rejection decision boundary.

Passing any early gate must not imply that later gates are passed. No gate may
promote the candidate into implementation without explicit approval of exact
validated research, exact signal-definition binding, deterministic
reproduction, benchmark/cash proxy treatment, no-lookahead controls,
production-threshold or parameter provenance, and implementation scope.

## Explicit Non-Goals

This phase does not perform or authorize:

- ETF universe approval
- data source approval
- data acquisition
- data ingestion
- dataset approval
- source approval
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
- production-readiness claim
- implementation-readiness claim
- profitability claim
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
- no acquired data
- no project-local deterministic reproduction
- no benchmark/cash proxy approval
- no no-lookahead audit
- no production threshold/config provenance
- no implementation-scope approval
- no evaluator tests
- no approved dataset, source package, or offline snapshot policy
- no license/offline-use approval
- no methodology-only moving-average review
- no reproduction protocol approval
- no result-review template approval
- no promotion/rejection decision
- no trading implication or production threshold
