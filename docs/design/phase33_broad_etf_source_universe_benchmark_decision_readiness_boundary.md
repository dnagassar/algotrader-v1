# Phase 33 Step 19 - Broad ETF Source / Universe / Benchmark Decision Readiness Boundary

## Purpose

This document assesses whether broad-ETF source, universe,
benchmark/cash-proxy, return-construction, and data-policy gates are ready for
concrete decisions.

It exists to prevent premature movement into data acquisition, schemas,
notebooks, backtests, reproduction, evaluators, signal definitions, or trading
work. It does not approve any source, ETF universe, benchmark, cash proxy,
methodology, parameter, data policy, reproduction protocol, implementation,
signal definition, evaluator, or trading use.

No gate is approved in this phase. A later boundary may revisit one narrow
gate only if prior documentation and owner constraints make the decision
concrete before any code or data work.

## Current Readiness Summary

Phase 33 Step 18 concluded that reproduction planning and any code phase are
not ready.

Most readiness gates are partial because prior docs provide routing context
but no approval. Return construction is blocked. Survivorship, inception, and
delisting handling are blocked. Reproduction protocol is blocked. Result-review
template is blocked. Implementation scope is blocked. Code is not ready.

## Gate-By-Gate Readiness

Status values:

- `blocked`: a concrete decision cannot be reviewed until material upstream
  questions are resolved.
- `partial`: prior docs provide context, but no approval exists and the gate is
  not ready for a concrete decision.
- `ready for later approval review`: enough context appears to exist for a
  later docs-only approval review, while approval remains forbidden here.

| Gate | Current status | Supporting docs | Unresolved blockers | Next required document | Approval allowed now? |
| --- | --- | --- | --- | --- | --- |
| Source/data provider | partial | Steps 4, 7, 8, 9, and 18 | Stooq terms, adjustment, dividend, split, correction, revision, symbol-identity, local-snapshot, and redistribution questions remain unresolved; other providers remain secondary/check or context only. | Source approval readiness boundary after refreshed terms, adjustment, and storage constraints. | no |
| ETF universe | partial | Steps 3, 4, 6, 8, 9, and 18 | No approved ticker list, inclusion rule, inception rule, inactive-fund policy, survivorship control, source, or return-construction policy. | Universe approval readiness boundary after source, return construction, and survivorship policy are narrower. | no |
| Benchmark/cash proxy | partial | Steps 4, 6, 15, 16, 17, and 18 | Buy-and-hold target, broad-equity benchmark identity, cash-rate series, frequency conversion, compounding, release timing, and vintage/revision handling remain unresolved. | Benchmark/cash proxy detailed boundary. | no |
| Return construction | blocked | Steps 4, 6, 15, 16, 17, and 18 | No approved adjusted-close, total-return, dividend, distribution, split, corporate-action, missing-value, expense, or rebalance-period policy. | Return-construction boundary. | no |
| Terms/license | partial | Steps 7, 8, 9, and 18 | No source-specific final decision for private-repo use, local archival, redistribution, derived-stat publication, API limits, citation, or fixture eligibility. | Terms/license approval readiness boundary tied to one exact source path. | no |
| Storage/fixture policy | partial | Steps 8, 9, 18, and Phase 34 Steps 1-3 | No final storage path, fixture class, local-only data path, manifest format, checksum rule, or pytest-eligible fixture set. | Final data storage/fixture policy approval boundary after source terms narrow. | no |
| No-lookahead/as-of protocol | partial | Steps 5, 15, 16, 17, and 18 | Signal observation time, decision time, action time, fill convention, return window, release lag, correction policy, and revision policy remain unapproved. | No-lookahead/as-of protocol boundary. | no |
| Cost/friction assumptions | partial | Steps 5, 15, 16, 17, and 18 | Transaction costs, spreads, slippage, opening gaps, turnover, taxes, fund expenses, rebalance friction, and rejected simplifications remain unapproved. | Cost/friction assumption boundary. | no |
| Survivorship/inception/delisting handling | blocked | Steps 3, 4, 6, 15, 16, 17, and 18 | No policy for ETF inception, first usable observation, closures, mergers, ticker changes, delistings, stale observations, or unavailable histories. | Universe/source survivorship policy boundary. | no |
| Methodology/parameter discipline | partial | Steps 5, 15, 16, 17, and 18 | Rule family, cadence, timing semantics, fixed parameters, search discipline, sensitivity review, and rejection criteria remain unapproved. | Methodology and parameter-discipline boundary after return/timing questions narrow. | no |
| Reproduction protocol | blocked | Steps 17 and 18 | Source, universe, benchmark/cash proxy, return construction, timing, costs, survivorship, storage, and result review are not approved. | Reproduction protocol planning boundary only after upstream approvals. | no |
| Result-review template | blocked | Steps 17 and 18 | No template for assumptions, limitations, non-claims, rejection criteria, residual gaps, and no trading-readiness language. | Result-review template boundary. | no |
| Implementation scope | blocked | Steps 17 and 18 | No validated evidence, validated signal definition, approved data policy, approved protocol, implementation scope, or evaluator tests. | Implementation readiness gate only after validation and signal-definition approvals. | no |

No gate is ready for approval now. The closest future work is not code; it is a
docs-only boundary that resolves one narrow blocker.

## Source Readiness

Source routing remains cautious and non-approving:

- Stooq is a possible primary planning candidate for ETF price data, but
  terms, adjustment semantics, dividend/distribution handling, split and
  corporate-action handling, corrections, revisions, symbol identity, local
  snapshot rights, private-repo use, and redistribution questions remain.
- Yahoo Finance / yfinance remains secondary/check or unresolved. It is not a
  default source because official terms, automation, cache/archive rights,
  adjusted-data methodology, API stability, and unofficial-client support
  remain unresolved.
- Nasdaq Data Link and Alpha Vantage remain secondary/check candidates only.
  Both require exact dataset or endpoint review, access-tier review,
  rate-limit/API-key handling, adjustment-methodology review, local snapshot
  permission, and redistribution review.
- FRED remains a cash/risk-free proxy candidate only. Fixture/storage,
  citation, API-key/API-term, release-timing, vintage/revision, frequency
  alignment, and cash-rate conversion handling remain unresolved.
- ETF issuer pages remain metadata/context only for fund identity, objective,
  index, expense, holdings, distributions, and issuer context.
- Broker historical data remains context only and not a default source because
  credentials, subscriptions, account state, feed terms, and runtime access
  conflict with default offline, credential-free tests if used directly.

No source is approved.

## ETF Universe Readiness

Candidate universe buckets remain candidate-only:

| Bucket | Readiness assessment |
| --- | --- |
| Broad U.S. equity | Partial only. Familiar examples can support later review, but source, adjusted-data, dividend, benchmark-overlap, inception, and duplicate-exposure questions block approval. |
| Developed international | Partial only. Currency, domicile, withholding/distribution, regional index, calendar, source coverage, inception, and benchmark-comparability questions block approval. |
| Emerging markets | Partial only. Country/index construction, liquidity, data quality, tracking difference, distribution, calendar, inception, and unequal-history questions block approval. |
| Aggregate bonds | Blocked for concrete universe approval until income/distribution treatment, total-return needs, duration/credit changes, adjusted-price adequacy, and benchmark comparability are resolved. |
| Treasury-duration exposure | Partial only. Duration choice, distribution treatment, rate-regime sensitivity, inception, cash-proxy comparison, and parameter-selection concerns remain. |
| Optional gold/commodity exposure | Blocked or defer-only unless source quality, structure, tax/issuer form, spot/futures/roll exposure, benchmark fit, and methodology caveats are documented before result inspection. |

No ETF universe, ticker list, bucket mix, issuer set, index family, inclusion
rule, exclusion rule, inception rule, inactive-fund policy, survivorship
policy, or metadata source is approved.

## Benchmark / Cash Proxy Readiness

Benchmark and cash-proxy choices remain candidate-only:

- A buy-and-hold comparison is conceptually useful but cannot be concrete
  until the ETF universe, source, return construction, and timing conventions
  are approved.
- A broad U.S. equity benchmark remains a candidate comparison, but it may
  duplicate the U.S. equity universe bucket and still lacks source,
  adjusted-data, dividend, total-return, and benchmark-identity decisions.
- FRED `TB3MS` and `DGS3MO` remain candidate cash-rate series only. The project
  still needs series choice, release timing, vintage/revision handling,
  frequency alignment, compounding, day-count, annualization, and storage or
  citation policy.
- A zero-return placeholder is a last-resort methodology placeholder only. It
  is not realistic cash, not a benchmark, not a risk-free proxy, and not a
  substitute for FRED or other source review.

No benchmark, cash proxy, risk-free proxy, buy-and-hold target, broad-equity
benchmark, rate series, frequency-conversion rule, or cash-return convention is
approved.

## Decision

Decision: not ready for approval; pause before code.

The prior docs support candidate routing and blocker identification, not
concrete approval. The broad-ETF candidate is not ready for data acquisition,
schemas, notebooks, scripts, backtests, reproduction, result review,
evaluators, signal definitions, validated artifacts, implementation, or
trading-path work.

At most, the project is ready for another narrow docs-only boundary that
reduces one upstream blocker without approving source use, universe,
benchmark/cash proxy, methodology, parameters, data policy, reproduction, or
code.

## Recommended Next Routing

Recommended next route: return-construction boundary.

Return construction is the narrowest blocked gate that affects source choice,
ETF universe suitability, benchmark comparability, cash treatment,
survivorship handling, no-lookahead timing, result review, and any eventual
reproduction protocol. The boundary should decide what questions must be
answered about adjusted close versus total return, dividends, distributions,
splits, corporate actions, expenses, missing values, and rebalance periods.

Conservative alternates remain:

- benchmark/cash proxy detailed boundary
- source approval readiness boundary
- result-review template boundary
- pause Phase 33 before code

None of these routes may acquire data, approve data use, approve a source,
approve a universe, approve a benchmark/cash proxy, approve methodology,
approve parameters, reproduce results, validate, backtest, compute signals,
implement an evaluator, or create trading implications.

## Explicit Non-Goals

This phase does not perform or authorize:

- approval
- source approval
- universe approval
- benchmark approval
- cash-proxy approval
- methodology approval
- parameter approval
- data-policy approval
- data acquisition
- data download
- data ingestion
- data files
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
- production threshold
- profitability claim
- validation claim
- implementation-readiness claim
- production-readiness claim
- trading implication
- broker, OMS, runtime, scheduler, persistence, portfolio, ledger,
  reconciliation, Alpaca, ML, vectorbt, QuantConnect, notebook runtime, or LLM
  trading-path behavior

## Remaining Blockers

- no `ValidatedResearchArtifact`
- no `ValidatedSignalDefinition`
- no approved evidence review
- no approved methodology or parameters
- no approved ETF universe
- no selected/approved data source
- no approved benchmark/cash proxy
- no approved final data storage/fixture policy
- no approved return-construction policy
- no approved no-lookahead/as-of protocol
- no approved cost/friction assumptions
- no approved survivorship/inception/delisting policy
- no acquired data
- no project-local deterministic reproduction
- no implementation-scope approval
- no evaluator tests
- no source-specific local archival/private-repo policy
- no redistribution or derived-stat publication policy
- no exact FRED cash-rate storage/citation/revision policy
- no benchmark/cash-proxy frequency-alignment rule
- no cash-rate conversion or compounding rule
- no result-review template
- no reproduction protocol
- no promotion/rejection decision
- no trading implication or production threshold
