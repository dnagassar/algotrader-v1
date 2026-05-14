# Phase 33 Step 8 - Broad ETF Final Source Shortlist Decision Boundary

## Purpose

This document records a final non-approving source shortlist decision for
future broad-ETF simple moving-average planning.

It does not approve sources, data, an ETF universe, a benchmark, a cash proxy,
methodology, reproduction, validation, signal definition, evaluator,
implementation, or trading use.

This phase is documentation-only. It adds no data, notebook, script, schema,
test, source code, evaluator, signal computation, trading-path behavior,
broker behavior, runtime behavior, scheduler behavior, persistence behavior,
portfolio behavior, ledger behavior, reconciliation behavior, Alpaca behavior,
ML behavior, or LLM trading-path behavior.

## Decision Vocabulary

Only these cautious routing labels are used:

- primary planning candidate
- secondary/check candidate
- metadata/context only
- cash/risk-free proxy candidate
- not default source
- unresolved / requires further review

These labels are planning labels only. They are not source approval, dataset
approval, universe approval, benchmark approval, methodology approval,
reproduction approval, validation approval, or implementation approval.

## Candidate Source Routing

| Source/category | Routing label | Current decision-boundary status |
| --- | --- | --- |
| Stooq | possible primary planning candidate; unresolved / requires further review | Possible primary planning candidate for ETF price data, but not approved. Terms, local snapshot rights, adjusted-data semantics, dividend handling, and revision questions remain unresolved. |
| Yahoo Finance / yfinance / Yahoo API terms | secondary/check candidate; unresolved / requires further review; not default source | Secondary/check candidate only or unresolved due to high terms uncertainty. It is not a default project source. |
| Nasdaq Data Link | secondary/check candidate; unresolved / requires further review | Secondary/check candidate only unless a specific dataset, coverage route, access model, and terms are later reviewed. |
| Alpha Vantage | secondary/check candidate; unresolved / requires further review | Secondary/check candidate only due to API-key access, rate limits, ETF coverage questions, adjustment-methodology gaps, and terms uncertainty. |
| FRED | cash/risk-free proxy candidate; unresolved / requires further review | Cash/risk-free proxy candidate only, not approved. Fixture/storage, citation, API, archival, revision, and frequency-alignment handling remain required. |
| ETF issuer pages | metadata/context only | Metadata/context only for fund identity, objectives, index, expenses, holdings, distributions, and issuer context. Not a project price-data source. |
| Broker historical data | metadata/context only; not default source | Context only and not a default source. Credentials, account/subscription state, feed terms, and runtime access conflict with offline default tests if used directly. |

No row in this table authorizes source use, data acquisition, data storage,
dataset addition, reproduction, validation, implementation, normal pytest
network access, or trading-path behavior.

## Decision Rationale

This routing is based on the non-approving prior gates:

- Phase 33 Step 4 public-source documentation sweep: public documentation
  supports cautious source-routing context only. It does not resolve terms,
  offline archival, adjusted-price, total-return, revision, or as-of questions.
- Phase 33 Step 6 universe/benchmark shortlist: broad ETF buckets, example
  tickers, and benchmark/cash proxy candidates remain candidate-only and
  depend on later source, data policy, and methodology gates.
- Phase 33 Step 7 terms/license review: current terms-risk labels leave Stooq
  with moderate terms uncertainty, Yahoo/yfinance/Yahoo API terms with high
  terms uncertainty, Nasdaq Data Link and Alpha Vantage with moderate
  dataset/access uncertainty, FRED with low apparent terms risk pending final
  review, and issuer/broker pages as context only.

Offline reproducibility remains a hard project constraint. Any future source
route must support deterministic local snapshotting or an explicit
fixture/storage policy that keeps normal `python -m pytest` offline,
credential-free, and independent of provider state.

Terms uncertainty prevents source approval in this phase. Public availability,
client-library support, API documentation, or familiar ETF coverage does not
resolve storage, private-repo, redistribution, automation, rate-limit,
subscription, or derived-stat publication obligations.

Adjusted-price and total-return uncertainty also prevents reproduction or
methodology approval. Later work must resolve adjusted close semantics,
dividend and distribution handling, split and corporate-action treatment,
corrections, revisions, point-in-time availability, and total-return versus
price-return conventions before result inspection.

Normal pytest must remain offline and credential-free. Direct provider API
calls, broker historical-data calls, account state, subscriptions, wall-clock
fetches, or network-dependent fixtures remain outside default test behavior.

## Non-Approval Statement

No source is approved in this phase.

No data may be acquired under this phase.

No dataset may be added to the repository under this phase.

No source may be used in normal `python -m pytest`.

No candidate source may be used before a later explicit data storage/fixture
policy and/or source approval phase records permitted use, snapshot/storage
rules, private-repo rules, citation rules, redistribution limits,
derived-stat-publication limits, API/rate-limit constraints, and deterministic
offline replay requirements.

This phase does not approve a universe, benchmark, cash proxy, methodology,
moving-average parameter, reproduction protocol, validation route, evaluator,
signal definition, strategy implementation, or trading implication.

## Remaining Source-Specific Blockers

- Stooq: adjusted price semantics, dividend handling, split/corporate-action
  treatment, correction/revision policy, symbol identity, license clarity,
  private-repo snapshot rights, and redistribution limits remain unresolved.
- Yahoo Finance / yfinance / Yahoo API terms: personal-use limits,
  automation restrictions, storage/cache limits, API stability, private-repo
  archival, redistribution, derived-stat publication, and unofficial-client
  support remain unresolved.
- FRED: archival permission, API-key/API-term handling, citation requirements,
  series-owner restrictions, vintage/revision handling, release timing,
  daily/monthly frequency alignment, and cash-rate conversion remain
  unresolved.
- Nasdaq Data Link and Alpha Vantage: dataset-specific terms, ETF coverage,
  access tier, API-key handling, rate limits, adjustment methodology,
  local snapshot permission, private-repo storage, and redistribution limits
  remain unresolved.
- ETF issuer pages: metadata reuse rights, page/fact-sheet archival,
  historical metadata availability, point-in-time fund objective/index
  changes, distribution table reuse, and issuer-specific terms remain
  unresolved.
- Broker historical data: credentials, account/subscription entitlements,
  feed terms, runtime access, redistribution limits, and broker/exchange data
  terms conflict with offline, credential-free default tests if used directly.

## Recommended Next Gate

Recommended next docs-only gate: data storage/fixture policy boundary.

That gate should define how any later source candidate would be snapshotted,
stored, cited, hashed, versioned, fixture-scoped, and excluded from normal
network or credential access. It must still avoid data acquisition, source
approval, dataset approval, schema implementation, reproduction, validation,
signal computation, evaluator implementation, and trading implications.

If the project wants to strengthen methodology evidence before moving closer
to reproducible research mechanics, the later docs-only route is a
moving-average evidence intake plan after the evidence/source package.

A reproduction protocol boundary should wait until source, universe,
benchmark, cash proxy, and data storage/fixture policy choices are later
approved by explicit phases.

## Explicit Non-Goals

This phase does not perform or authorize:

- legal advice
- source approval
- universe approval
- benchmark approval
- cash proxy approval
- methodology approval
- moving-average parameter approval
- data acquisition
- ingestion
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
- no approved data storage/fixture policy
- no acquired data
- no project-local deterministic reproduction
- no no-lookahead audit
- no production threshold/config provenance
- no implementation-scope approval
- no evaluator tests
- no approved data license or offline-use path
- no approved local snapshot/versioning policy
- no approved source-specific local archival/private-repo policy
- no approved redistribution or derived-stat publication policy
- no approved API rate-limit/access policy
- no approved adjusted-price semantics
- no approved total-return versus price-return decision
- no approved dividend/reinvestment treatment
- no approved corporate-action handling policy
- no approved correction/revision policy
- no approved point-in-time/as-of policy
- no approved inactive-fund, delisting, merger, or ticker-change policy
- no approved benchmark/cash-proxy frequency alignment rule
- no approved cash-rate conversion or compounding rule
- no approved transaction cost, slippage, spread, rebalance, fund-expense, or
  friction assumption
- no result-review template
- no promotion/rejection decision
- no trading implication or production threshold
