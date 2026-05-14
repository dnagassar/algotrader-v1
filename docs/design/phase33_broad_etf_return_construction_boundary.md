# Phase 33 Step 20 - Broad ETF Return-Construction Boundary

## Purpose

This document defines return-construction questions and constraints for the
broad-ETF simple moving-average candidate before any reproduction planning.

It exists to prevent premature approval of a data source, ETF universe,
benchmark, cash proxy, methodology, parameter, data policy, reproduction
protocol, implementation, evaluator, signal definition, or trading use.

It also preserves no-lookahead/as-of discipline and the project rule that
normal `python -m pytest` remains offline, credential-free, deterministic, and
free of provider, broker, account, subscription, runtime, notebook, prototype,
or trading-path dependencies.

## Current Boundary

Return construction is a planning blocker, not an approved policy.

No return basis is selected. No field, source, benchmark, cash proxy, cadence,
timing convention, or storage policy is approved. No data may be acquired,
downloaded, ingested, stored, snapshotted, transformed, backtested,
reproduced, validated, or used for signal computation under this phase.

## Return-Construction Options

These options are compared only as unresolved choices.

| Option | Possible role | Unresolved requirements | Current status |
| --- | --- | --- | --- |
| Raw close price returns | Simple price-only baseline for methodology discussion. | Excludes dividends and distributions, may be incomparable across income-heavy ETFs, and needs split/corporate-action handling plus timing rules. | Not approved. |
| Adjusted close returns | Possible compact field if adjustment semantics are transparent. | Requires source-specific documentation for dividend, split, distribution, corporate-action, correction, and revision treatment. | Not approved. |
| Explicit total-return construction from prices plus distributions | Possible transparent return basis if price and distribution fields are reliable. | Requires ex-date, payment-date, reinvestment, availability, split, missing-data, and compounding policies. | Not approved. |
| Vendor-provided total-return series, if available | Possible benchmark or ETF return input if terms and methodology are clear. | Requires license, field definition, point-in-time availability, revision, redistribution, and source-quality review. | Not approved. |
| Cash/T-bill return series | Possible out-of-market return, benchmark component, or risk-free comparison. | Requires series choice, release timing, revision/vintage handling, frequency conversion, day-count, compounding, and storage policy. | Not approved. |
| Zero-return placeholder | Possible methodology placeholder for discussing rule shape only. | Must not be treated as realistic cash, risk-free return, benchmark, or approved result basis. | Placeholder only; not approved. |

## Required Decision Areas

A later approval boundary would need to resolve all of these areas before any
reproduction protocol or code phase:

- price return versus total return
- dividend, distribution, and reinvestment treatment
- split and corporate-action handling
- adjusted close methodology transparency
- ETF expense ratio treatment and whether it is already reflected in fund NAV
  or market prices
- cash/T-bill return treatment
- benchmark comparability across strategy, buy-and-hold, and cash/risk-free
  legs
- daily versus monthly compounding
- ETF inception-date and first-usable-observation alignment
- missing data, stale price, holiday, and non-trading-day handling
- frequency alignment across ETFs and FRED/cash series
- signal observation, decision date, action date, fill, and measured-return
  window implications

## No-Lookahead And As-Of Constraints

Any later return-construction policy must preserve these constraints:

- signals cannot use information unavailable at the decision timestamp
- adjusted historical data may embed later corporate-action adjustments and
  cannot be assumed point-in-time safe without source-specific review
- dividends and distributions require explicit ex-date, record-date,
  payment-date, reinvestment, and availability handling if used
- cash or risk-free data must be aligned by availability date, not hindsight
  convenience
- ETF inception dates and first usable observations must be respected
- benchmark construction must not use future data, future constituents,
  future rates, later-corrected values, or post-hoc availability assumptions
- same-close signal/action assumptions remain unapproved

## Source Implications

Return construction remains tied to source readiness:

- Stooq remains a possible planning candidate for ETF price data, but
  adjustment methodology, dividend/distribution treatment, split handling,
  correction/revision behavior, and local-snapshot rights remain blockers.
- Yahoo Finance / yfinance remains secondary/check or unresolved because terms,
  automation, cache/archive rights, API stability, and adjusted-data
  methodology remain uncertain.
- FRED remains a cash/risk-free candidate only. Series choice, release timing,
  revision/vintage handling, frequency alignment, rate conversion,
  compounding, citation, and storage remain unresolved.
- ETF issuer pages remain metadata/context only for fund identity, objective,
  index, expense ratio, holdings, distributions, and issuer notes.
- No source, source field, provider route, local snapshot, or data use is
  approved.

## Benchmark And Universe Implications

ETF universe and benchmark choices depend on the return-construction path:

- universe selection depends on whether a source can support comparable,
  deterministic, as-of-safe returns for each candidate ETF
- benchmark comparison must use a comparable return basis, such as price-only
  versus price-only or total-return versus total-return
- cash proxy construction must match strategy cadence, compounding, and
  availability assumptions
- bond ETFs may require extra income/distribution, duration, credit, and fund
  expense caveats
- commodity or gold ETFs may require extra structure, tax, roll, issuer, spot
  versus futures, and distribution caveats
- optional assets should remain deferred when return construction is unclear
- no ETF universe, benchmark, buy-and-hold target, or cash proxy is approved

## Required Future Approval Criteria

A later return-construction approval boundary would need at minimum:

- selected return basis
- documented source fields
- explicit dividend, distribution, reinvestment, split, and corporate-action
  assumptions
- explicit cash-rate conversion method
- explicit benchmark alignment method
- explicit inception, first-usable-observation, missing-data, stale-price, and
  non-trading-day policy
- explicit as-of timing policy for prices, adjustments, distributions, cash
  rates, benchmark values, corrections, and revisions
- explicit non-claims, including no profitability, validation,
  implementation-readiness, production-readiness, or trading-readiness claim
- deterministic fixture or local-data policy that keeps normal pytest offline,
  credential-free, provider-free, broker-free, and reproducible

## Decision

Decision: return construction remains blocked for approval.

The prior Phase 33 documents support only a partial planning boundary. They do
not establish an approved return basis, source field set, cash-rate
conversion, benchmark alignment method, inception policy, missing-data policy,
or as-of protocol. A later docs-only approval boundary may become possible
only after the timing and source-field questions are narrowed.

This phase does not make the broad-ETF candidate ready for data acquisition,
schemas, notebooks, scripts, backtests, reproduction, result review,
evaluators, signal definitions, validated artifacts, implementation, or
trading-path work.

## Recommended Next Routing

Recommended next route: no-lookahead/as-of protocol boundary.

That is the narrowest next gate because return construction cannot be reviewed
without explicit observation time, decision time, action time, availability,
adjustment, distribution, cash-rate, correction, revision, benchmark, and
same-close assumptions.

Conservative alternates remain:

- cash/benchmark return treatment boundary
- source field verification boundary
- survivorship/inception/delisting boundary
- pause before code

No route may approve source use, data acquisition, an ETF universe, benchmark,
cash proxy, methodology, parameter, data policy, reproduction, validation,
implementation, evaluator behavior, signal computation, or trading use.

## Explicit Non-Goals

This phase does not perform or authorize:

- return-construction approval
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
- no approved source fields
- no approved adjusted-close semantics
- no approved total-return construction method
- no approved dividend/distribution availability policy
- no approved cash-rate conversion or compounding rule
- no approved benchmark alignment method
- no approved missing-data or stale-price policy
- no approved timing/action-date policy
- no result-review template
- no reproduction protocol
- no promotion/rejection decision
- no trading implication or production threshold
