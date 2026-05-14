# Phase 33 Step 22 - Broad ETF Survivorship / Inception / Delisting Boundary

## Purpose

This document defines survivorship, inception, delisting, symbol identity, and
universe-membership risks for the broad-ETF simple moving-average candidate
before any reproduction planning.

It exists to prevent premature ETF universe approval, source approval,
benchmark/cash proxy approval, return-construction approval,
no-lookahead/as-of approval, reproduction planning, implementation, evaluator
behavior, signal definitions, or trading use.

It also preserves no-lookahead/as-of discipline and the project rule that
normal `python -m pytest` remains offline, credential-free, deterministic, and
free of live data, provider, broker, account, subscription, runtime, notebook,
prototype, or trading-path dependencies.

## Current Boundary

No survivorship/inception/delisting policy is approved.

This phase defines a planning boundary only. No ETF universe, source,
benchmark, cash proxy, methodology, parameter, final data policy,
return-construction policy, no-lookahead/as-of protocol, reproduction protocol,
code, tests, notebooks, fixtures, signal definition, evaluator, validated
artifact, or trading use is approved.

## Core Principle

Any future ETF universe must be defined before result inspection and must avoid
survivorship-biased selection, cherry-picked winners, and retroactive
inclusion rules.

Future review must treat universe membership as an input assumption, not an
outcome of inspected performance. Candidate buckets, inclusion rules,
exclusion rules, replacement rules, and limitations must be documented before
any backtest, reproduction attempt, result table, evaluator work, or signal
definition discussion.

## Inception-Date Requirements

Any later policy must address:

- ETFs cannot be used before their actual inception date.
- ETF inception dates must be recorded from reliable metadata sources.
- First usable observation may be later than inception because source coverage,
  adjusted fields, distributions, holidays, missing data, or first complete
  moving-average windows may constrain usability.
- Data before ETF inception must be rejected unless an explicitly approved
  proxy policy exists.
- Index proxies before ETF inception are not approved in this phase.
- Start dates must be aligned across ETF, benchmark, and cash data before
  result comparison.
- Unequal ETF histories must be labeled before any common-sample,
  expanding-sample, or staggered-entry convention is considered.

No inception-date source, first-usable-observation rule, proxy policy, sample
start, common window, or staggered-entry convention is approved.

## Delisting / Inactive ETF Requirements

Inactive and delisted ETF handling remains unresolved.

Any later policy must address:

- the future data source must document whether delisted and inactive ETF
  history is available
- excluding delisted ETFs may create survivorship bias
- relying only on currently surviving funds may be acceptable only if later
  justified, labeled, and treated as a limitation rather than a clean
  survivorship-safe universe
- closures, liquidations, mergers, exchange moves, halted funds, and missing
  terminal histories require explicit handling
- any later exclusion of inactive ETFs must be documented as a limitation
- replacement rules must be defined before results if an ETF closes or becomes
  unusable during a sample

No inactive-fund, delisting, closure, merger, replacement, terminal-return, or
survivorship-bias policy is approved.

## Symbol Identity And Corporate Events

Stable symbol identity must be verified before any future use.

Any later policy must address:

- ticker changes, fund mergers, closures, share class changes, issuer changes,
  exchange changes, provider symbol formats, and index changes
- whether a current ticker maps to one continuous fund history or multiple
  historical identities
- whether provider-adjusted prices remain continuous through corporate events
  without hiding as-of or reproducibility risks
- issuer metadata pages may provide current metadata only and may not preserve
  historical metadata, prior objectives, prior indexes, fee changes, mergers,
  or closure trails
- symbol continuity cannot be assumed from current ticker alone
- historical metadata snapshots and access dates must be recorded if later
  used

No symbol-identity policy, corporate-event policy, metadata snapshot policy,
or continuity assumption is approved.

## Universe Membership Timing

Universe membership remains candidate-only.

Any later policy must address:

- candidate buckets must be defined before performance inspection
- inclusion and exclusion rules must be documented before results
- liquidity, expense, history-length, asset-class, issuer, structure,
  distribution, and data-quality filters must be fixed before backtesting
- ETF selection must not be based on observed strategy performance,
  favorable historical return, favorable drawdown, favorable volatility, or
  later survival
- optional buckets or substitute ETFs must not be added after inspecting
  results unless a later review treats them as separate research candidates
- no final ETF universe, ticker list, bucket mix, inclusion rule, exclusion
  rule, filter, or replacement rule is approved in this phase

## Source Implications

Prior source routing remains non-approving:

- Stooq remains a possible planning candidate for ETF price data, but
  delisting, inactive-fund history, symbol-history coverage, adjustment
  semantics, corrections, revisions, and snapshot rights remain unresolved.
- Yahoo Finance / yfinance remains secondary/check or unresolved only.
  Survivorship handling, symbol history, adjusted-data methodology, terms,
  automation, cache/archive rights, API stability, and long-term
  reproducibility remain unresolved.
- ETF issuer pages remain metadata/context only. Current issuer pages may
  help with fund identity, objective, index, expense, holdings, distribution,
  and inception context, but historical metadata preservation remains
  unresolved.
- Broker historical data remains context only and not a default source because
  credentials, subscriptions, account state, feed terms, and runtime access
  conflict with normal offline, credential-free tests if used directly.
- No source, source field, provider route, metadata route, local snapshot, or
  data use is approved.

## Relationship To Return Construction And No-Lookahead

Survivorship and inception choices interact with return construction and
as-of timing:

- inception handling affects eligible return windows and first complete
  moving-average windows
- delisting and inactive-fund handling affects survivorship bias and terminal
  return treatment
- ticker changes, mergers, and closures affect adjusted-return continuity and
  corporate-action interpretation
- metadata availability affects as-of correctness because current pages may
  expose facts that were not available at historical decision times
- universe membership must not use future knowledge, later survival, future
  fund popularity, future liquidity, future expense ratios, or post-result
  performance
- benchmark and cash comparisons must align with the selected universe and
  sample windows before any future result review

No return-construction policy, no-lookahead/as-of protocol, benchmark/cash
policy, source snapshot policy, or reproduction protocol is approved.

## Required Future Approval Criteria

A later survivorship/inception/delisting approval boundary would need at
minimum:

- approved ETF universe construction rules
- approved inception-date source
- approved inactive/delisted ETF handling
- approved symbol-identity policy
- approved proxy policy, if any
- approved metadata snapshot/provenance policy
- explicit limitations and non-claims
- deterministic examples if fixtures are later allowed

Any deterministic examples must be project-local, synthetic or otherwise
approved by a later fixture/data policy, offline, credential-free,
provider-free, broker-free, notebook-free, and independent of live data.

## Decision

Decision: survivorship/inception/delisting policy remains blocked for
approval.

This phase creates a partial planning boundary only. Prior Phase 33 documents
support the need for inception, delisting, inactive-fund, symbol-identity, and
pre-result universe rules, but they do not approve an ETF universe, metadata
source, source fields, inactive-fund handling, delisting treatment, symbol
continuity, proxy use, sample window, or deterministic examples.

This phase does not make the broad-ETF candidate ready for data acquisition,
schemas, notebooks, scripts, backtests, reproduction, result review,
evaluators, signal definitions, validated artifacts, implementation, or
trading-path work.

## Recommended Next Routing

Recommended next route: cash/benchmark return treatment boundary.

That is the narrowest next gate because return construction, no-lookahead
timing, and universe/inception rules still cannot be reviewed against results
until the candidate defines how cash/risk-free series, benchmark returns,
buy-and-hold comparisons, frequency alignment, publication timing, and
zero-return placeholders are treated without approving a benchmark or cash
proxy.

Conservative alternates remain:

- cost/friction assumptions boundary
- source field verification boundary
- result-review template boundary
- pause before code

No route may approve source use, data acquisition, an ETF universe, benchmark,
cash proxy, methodology, parameter, data policy, return construction,
no-lookahead/as-of protocol, survivorship/inception/delisting policy,
reproduction, validation, implementation, evaluator behavior, signal
computation, or trading use.

## Explicit Non-Goals

This phase does not perform or authorize:

- survivorship/inception/delisting approval
- ETF universe approval
- source approval
- benchmark approval
- cash-proxy approval
- return-construction approval
- no-lookahead/as-of approval
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
- no approved inception-date source
- no approved first-usable-observation rule
- no approved inactive/delisted ETF handling
- no approved symbol-identity policy
- no approved proxy policy
- no approved metadata snapshot/provenance policy
- no approved benchmark/cash return treatment
- no approved source fields
- no approved adjusted-close semantics
- no approved total-return construction method
- no approved timing/action-date policy
- no result-review template
- no reproduction protocol
- no promotion/rejection decision
- no trading implication or production threshold
