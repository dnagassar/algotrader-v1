# Phase 33 Step 23 - Broad ETF Cash / Benchmark Return Treatment Boundary

## Purpose

This document defines cash and benchmark return-treatment questions for the
broad-ETF simple moving-average candidate before any reproduction planning.

It exists to prevent premature approval of a benchmark, cash proxy,
cash-rate series, source, ETF universe, return construction,
no-lookahead/as-of protocol, methodology, parameter, data policy,
reproduction protocol, implementation, evaluator behavior, signal definition,
or trading use.

It also preserves no-lookahead/as-of discipline and the project rule that
normal `python -m pytest` remains offline, credential-free, deterministic, and
free of FRED calls, vendor API calls, broker API calls, live data, online
sources, account state, subscription state, runtime behavior, notebook
behavior, prototype behavior, or trading-path dependencies.

## Current Boundary

No cash/benchmark return treatment is approved.

This phase defines a planning boundary only. No benchmark, cash proxy,
cash-rate series, source, ETF universe, return-construction policy,
no-lookahead/as-of protocol, survivorship/inception/delisting policy,
methodology, parameter, final data policy, reproduction protocol, code, tests,
notebooks, fixtures, signal definition, evaluator, validated artifact, or
trading use is approved.

## Benchmark Comparison Candidates

Benchmark comparison candidates remain unresolved and non-approved:

| Candidate | Possible role | Unresolved requirements | Current status |
| --- | --- | --- | --- |
| Buy-and-hold version of any later selected ETF universe | Same-universe comparison if a universe is later approved. | Requires approved ETF universe, source, return basis, inception handling, rebalancing or weighting convention, missing-data handling, and no-lookahead/as-of alignment. | Candidate only, not approved. |
| Broad U.S. equity benchmark candidate | External broad-market comparison if later justified. | May overlap the U.S. equity ETF bucket; benchmark identity, source fields, dividend treatment, total-return versus price-return basis, and sample alignment remain unresolved. | Candidate only, not approved. |
| Asset-class-matched benchmark candidates | Possible comparisons for equity, bond, Treasury-duration, international, emerging-market, gold, or commodity buckets if later approved. | Requires asset-class definitions, comparable return bases, source support, calendar alignment, inception handling, and limitations for duplicate exposure or unsuitable structures. | Candidate only, not approved. |
| Cash/T-bill proxy comparison | Possible out-of-market, risk-free, or context comparison. | Requires selected series, source route, publication timing, revision/vintage handling, frequency conversion, day count, compounding, and alignment with ETF and benchmark returns. | Candidate only, not approved. |
| Zero-return placeholder | Last-resort methodology placeholder for docs-only rule-shape discussion. | Not realistic cash, not a risk-free proxy, not a benchmark, and not a substitute for rate-source review. | Placeholder only, not approved. |

No benchmark identity, benchmark source, buy-and-hold convention, weighting
rule, return basis, comparison target, or benchmark alignment rule is
approved.

## Cash / T-Bill Proxy Candidates

Cash and T-bill proxy candidates remain unresolved and non-approved:

| Candidate | Possible role | Unresolved requirements | Current status |
| --- | --- | --- | --- |
| FRED `TB3MS` | Candidate T-bill or cash-rate context already named in prior Phase 33 docs. | Rate definition, monthly frequency treatment, publication timing, vintage/revision behavior, annualized-rate conversion, compounding, day count, and alignment to ETF decision/action dates remain unresolved. | Candidate only, not approved. |
| FRED `DGS3MO` | Candidate Treasury/cash-rate context already named in prior Phase 33 docs. | Rate definition, daily frequency treatment, holidays, missing observations, publication timing, vintage/revision behavior, annualized-rate conversion, compounding, day count, and monthly aggregation remain unresolved. | Candidate only, not approved. |
| Other FRED Treasury or cash-rate candidates | Possible later alternatives only if separately identified and reviewed. | Prior relevant Phase 33 docs reviewed for this boundary name `TB3MS` and `DGS3MO`; any other series would need source identity, field meaning, frequency, release, revision, conversion, and limitation review before use. | Not selected, not approved. |
| Zero-return cash placeholder | Possible sensitivity/context placeholder only if a later docs-only protocol explicitly allows it. | Does not represent realistic cash return, Treasury bills, collateral return, broker sweep yield, money-market yield, or risk-free return. | Placeholder only, not approved. |

Future review must resolve whether a rate is a discount rate, investment
basis, yield, index level, or other quoted form; whether the observation is
daily, monthly, averaged, end-of-period, or released with lag; whether values
are revised or vintaged; and how a quoted annualized rate would become a
period return without using future information.

No FRED series, cash proxy, risk-free proxy, rate type, conversion method,
frequency rule, publication-lag rule, revision/vintage rule, or cash-return
assumption is approved.

## Required Decision Areas

A later approval boundary would need to resolve all of these areas before any
reproduction protocol, result review, code, data acquisition, or fixture work:

- benchmark return basis: price return, adjusted return, explicit total
  return, or vendor-provided total return
- cash return basis and whether annualized rates become period returns through
  simple, daily, monthly, continuously compounded, or other compounding
- daily versus monthly frequency alignment across ETF, benchmark, and cash
  data
- ETF signal cadence versus benchmark and cash cadence
- date alignment across ETF observations, benchmark observations, cash-rate
  observations, decision timestamps, action timestamps, and return windows
- FRED publication timing, revision behavior, vintage availability, and
  as-of handling
- treatment of non-trading days, exchange holidays, bank holidays, weekends,
  missing observations, stale observations, and month-end calendar mismatches
- whether cash earns return while the strategy is out of market
- whether idle cash, transaction costs, spreads, slippage, taxes, fund
  expenses, rebalance costs, or cash drag are included, excluded, or deferred
- inflation or real-return treatment, if any
- whether zero-return cash is allowed only as sensitivity/context rather than
  as a realistic cash, T-bill, or risk-free assumption

No decision area above is resolved in this phase.

## No-Lookahead And As-Of Constraints

Any later cash/benchmark policy must preserve these constraints:

- cash and benchmark data must be available as of the decision or evaluation
  timestamp that uses them
- FRED series may have publication timing, vintage timing, correction
  behavior, and revision history that must be documented before use
- benchmark and cash series must not be aligned using hindsight convenience,
  later-corrected values, unavailable observations, future benchmark values,
  future rate observations, or post-result sample adjustments
- monthly cash returns must not use future daily data or future month-end data
  unavailable at the decision timestamp
- same-period benchmark and cash comparisons require explicit observation,
  decision, action, and measured-return rules
- benchmark and cash comparisons must use the same no-lookahead discipline as
  ETF strategy returns
- normal `python -m pytest` must not call FRED, vendor APIs, broker APIs,
  online sources, live data feeds, account endpoints, subscriptions, notebook
  runtimes, prototype tools, or trading-path services

No no-lookahead/as-of protocol is approved.

## Relationship To Prior Gates

This boundary depends on prior Phase 33 gates only as non-approving context:

- Step 33.20 return-construction boundary keeps raw close, adjusted close,
  explicit total return, vendor total return, cash/T-bill return series, and
  zero-return placeholders unresolved.
- Step 33.21 no-lookahead/as-of boundary requires cash-rate availability,
  benchmark alignment, publication/revision timing, signal/action timing, and
  same-period comparisons to be explicit before use.
- Step 33.22 survivorship/inception/delisting boundary requires ETF
  inception dates, first usable observations, inactive/delisted fund handling,
  symbol identity, and universe membership timing before benchmark/cash
  comparisons can be interpreted.
- Step 33.6 universe/benchmark shortlist names buy-and-hold, broad U.S.
  equity benchmark, FRED `TB3MS`/`DGS3MO`, and zero-return placeholder
  candidates only, with no approval.
- Step 33.8 final source shortlist keeps FRED a cash/risk-free proxy
  candidate only and keeps Stooq, Yahoo Finance / yfinance, issuer pages,
  secondary/check sources, and broker data non-approved.
- Step 33.9 data storage/fixture policy boundary keeps local-data,
  snapshot, fixture, provenance, and normal-pytest rules unresolved for any
  later source data.

No prior gate approves a source, ETF universe, benchmark, cash proxy,
cash-rate series, return construction, no-lookahead/as-of protocol,
survivorship/inception/delisting policy, data storage policy, reproduction
protocol, code, tests, notebooks, fixtures, evaluator behavior, signal
definition, or trading use.

## Required Future Approval Criteria

A later benchmark/cash approval boundary would need at minimum:

- selected benchmark definition
- selected cash or risk-free proxy
- selected source and series identifiers
- documented frequency and conversion method
- documented publication, revision, vintage, and as-of handling
- documented alignment with the ETF universe, ETF inception handling, and
  return construction
- documented treatment of non-trading days, holidays, missing values, stale
  values, and month-end mismatches
- documented assumptions for out-of-market cash return, idle cash,
  transaction costs, spreads, slippage, rebalance costs, taxes, and fund
  expenses, or explicit deferral to a separate approved cost/friction gate
- documented limitations and non-claims
- deterministic fixture or local-data policy if data is used later

Any deterministic fixture or local-data policy must keep normal pytest
offline, credential-free, provider-free, broker-free, notebook-free,
prototype-free, and independent of live data.

## Decision

Decision: cash/benchmark return treatment remains blocked for approval.

This phase creates a partial planning boundary only. Prior Phase 33 documents
support the need to define benchmark identity, buy-and-hold comparison
treatment, cash/T-bill proxy treatment, FRED publication/revision handling,
frequency conversion, compounding, date alignment, and zero-return placeholder
limits, but they do not approve any benchmark, cash proxy, source, ETF
universe, return-construction policy, no-lookahead/as-of protocol,
survivorship/inception/delisting policy, methodology, parameter, data policy,
reproduction protocol, deterministic example, implementation, evaluator,
signal definition, or trading use.

This phase does not make the broad-ETF candidate ready for data acquisition,
schemas, notebooks, scripts, fixtures, backtests, reproduction, result
review, evaluators, signal definitions, validated artifacts, implementation,
or trading-path work.

## Recommended Next Routing

Recommended next route: cost/friction assumptions boundary.

That is the narrowest next gate because cash and benchmark comparability still
depends on whether out-of-market cash earns return, whether idle cash is
modeled, and whether transaction costs, spreads, slippage, taxes, fund
expenses, opening gaps, turnover, and rebalance friction are included,
excluded, or deferred without approving a benchmark, cash proxy, source,
return construction, reproduction, implementation, or trading use.

Conservative alternates remain:

- source field verification boundary
- result-review template boundary
- benchmark/cash approval readiness boundary
- pause before code

No route may approve source use, data acquisition, an ETF universe, benchmark,
cash proxy, cash-rate series, methodology, parameter, data policy, return
construction, no-lookahead/as-of protocol, survivorship/inception/delisting
policy, reproduction, validation, implementation, evaluator behavior, signal
computation, or trading use.

## Explicit Non-Goals

This phase does not perform or authorize:

- benchmark/cash proxy approval
- cash-rate series approval
- source approval
- universe approval
- return-construction approval
- no-lookahead/as-of approval
- survivorship/inception/delisting approval
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
- no approved benchmark definition
- no approved buy-and-hold comparison convention
- no approved asset-class-matched benchmark convention
- no approved cash/risk-free proxy
- no approved cash-rate series
- no approved FRED publication/revision/as-of handling
- no approved cash-rate conversion or compounding rule
- no approved benchmark return basis
- no approved benchmark/cash frequency-alignment rule
- no approved benchmark/cash date-alignment rule
- no approved non-trading-day or holiday policy
- no approved out-of-market cash return assumption
- no approved idle-cash assumption
- no approved inflation or real-return treatment
- no approved zero-return placeholder policy
- no result-review template
- no reproduction protocol
- no promotion/rejection decision
- no trading implication or production threshold
