# Phase 33 Step 21 - Broad ETF No-Lookahead / As-Of Protocol Boundary

## Purpose

This document defines no-lookahead and as-of questions for the broad-ETF
simple moving-average candidate before any reproduction planning.

It exists to prevent premature approval of timing assumptions, same-close
logic, adjusted-data use, cash-rate alignment, benchmark alignment,
signal/action timing, return construction, data acquisition, implementation,
evaluator behavior, signal definitions, or trading use.

It also preserves the project rule that normal `python -m pytest` remains
offline, credential-free, deterministic, and free of live data, provider,
broker, account, subscription, runtime, notebook, prototype, or trading-path
dependencies.

## Current Boundary

No no-lookahead/as-of protocol is approved.

This phase defines a planning boundary only. No source, ETF universe,
benchmark, cash proxy, methodology, parameter, final data policy,
return-construction policy, reproduction protocol, code, tests, notebooks,
fixtures, signal definition, evaluator, validated artifact, or trading use is
approved.

## Core As-Of Principle

Any future research protocol must ensure all of the following:

- signals use only information available at the decision timestamp
- action timing occurs after signal observation
- data revisions and adjusted data are handled explicitly
- benchmark and cash data availability is aligned by availability date
- normal `python -m pytest` never depends on live data, credentials, network,
  brokers, notebooks, external providers, or runtime trading behavior

This principle is a requirement for later review, not an approved protocol.

## Timing Concepts

These terms are defined only to make later decisions auditable.

| Concept | Boundary definition | Approval status |
| --- | --- | --- |
| Observation date | The date a source value describes, such as an ETF market session, ETF close, cash-rate period, dividend event, or benchmark value. It is not automatically the date the value was available. | Not approved as a usable timestamp by itself. |
| Decision timestamp | The explicit instant when a protocol evaluates the moving-average condition. Every input used by the signal must be available on or before this timestamp. | Required later; not selected. |
| Action timestamp | The explicit instant when a hypothetical order, allocation change, or return-window transition would occur after signal observation. | Required later; not selected. |
| Effective trade date | The market date on which an action convention would begin exposure or return measurement. It may differ from observation date and decision timestamp. | Required later; not selected. |
| Close-to-close assumption | A return measurement convention between closes. It does not by itself prove the close was available before the signal or action. | Not approved. |
| Next-open assumption | A possible action convention where a signal observed after one session acts at the next available open. It requires open availability, holiday, gap, and fill assumptions. | Not approved. |
| Next-close assumption | A possible action convention where a signal observed after one close acts at a later close. It requires explicit lag, holding-window, and missed-return treatment. | Not approved. |
| Monthly rebalance date | The calendar or trading date on which a monthly signal would be observed and later acted on. End-of-month data must not be used before it is available. | Not approved. |
| Cash-rate observation date | The date or period a cash/risk-free series describes. Publication, vintage, revision, compounding, and alignment rules remain separate. | Not approved. |
| Dividend/distribution ex-date and payment-date implications | The ex-date may affect market price and entitlement; the payment date may affect cash receipt or reinvestment. Availability and total-return treatment must be explicit. | Not approved. |
| Data publication/revision timestamp | The provider, vendor, exchange, issuer, or macro-source timestamp when a value or correction became available, where applicable. | Required later when available; not selected. |

## Moving-Average Signal Timing

The moving-average signal timing remains unresolved.

Future work must decide whether:

- the moving average is computed from prior close data only
- the current session close can be observed after market close
- action occurs at the next open, next close, or later
- same-close signal/action is forbidden unless a later approval boundary
  explicitly justifies data availability and action feasibility without
  lookahead
- monthly signals use only end-of-month data after that data is actually
  available
- month-end, holiday, non-trading-day, and source publication lags are
  documented before any result is computed
- the decision lag is written down as part of the protocol rather than inferred
  after results are inspected

No signal definition, moving-average parameter, signal direction, fill rule,
return window, score, ranking, confidence, or actionability is approved.

## Adjusted-Data And Total-Return Timing

Adjusted data and total-return construction remain timing risks.

Any later policy must address:

- adjusted close may reflect later corporate-action information and is not
  assumed point-in-time safe
- dividend, distribution, split, and other corporate-action adjustments must
  be source-specific and documented
- total-return construction must define when distributions become knowable and
  whether ex-date, record-date, payment-date, reinvestment date, or another
  convention controls availability
- retroactive vendor adjustments, corrections, and restatements create both
  reproducibility risk and as-of risk
- source snapshots must record retrieval date, source identity, field
  definitions, adjustment assumptions, and known limitations
- adjusted-price, raw-price, distribution, and total-return fields must not be
  mixed without an approved availability and comparability policy

No return basis, adjusted-close field, dividend treatment, split treatment,
total-return method, source snapshot policy, or data file is approved.

## Cash / Benchmark As-Of Timing

Cash and benchmark timing remain unresolved.

Any later policy must address:

- FRED or other cash-rate series may have publication timing, vintage timing,
  correction behavior, and revision history
- daily versus monthly cash-rate alignment remains unresolved
- cash-rate conversion, day-count, compounding, and holiday alignment remain
  unresolved
- benchmark returns must be compared on the same availability and timing basis
  as strategy returns
- a buy-and-hold benchmark must not use future benchmark data, later-corrected
  values, future constituents, or post-hoc availability assumptions
- zero-return placeholder treatment is not approved as a benchmark, cash proxy,
  risk-free proxy, or realistic out-of-market return
- no benchmark or cash proxy is approved

## ETF Universe And Inception Timing

Universe timing remains a separate blocker.

Any later policy must address:

- ETFs cannot be used before inception or before their first usable
  observation under the selected source policy
- index proxies before ETF inception are not approved
- delisting, closure, merger, ticker change, inactive fund, and missing-history
  handling remains unresolved
- universe membership must be predefined before performance inspection
- inclusion and exclusion rules must be documented before results are
  computed
- optional or substitute assets must not be added after inspecting performance
  unless a later non-claim review explicitly treats them as separate research
  candidates

No ETF universe, survivorship policy, inception policy, delisting policy, or
proxy substitution rule is approved.

## Required Future Approval Criteria

A later no-lookahead/as-of approval boundary would need at minimum:

- selected observation/action timing
- explicit lag convention
- selected return basis
- source snapshot policy
- dividend/split/corporate-action timing policy
- cash-rate availability policy
- benchmark alignment policy
- universe inception/delisting policy
- testable deterministic examples
- non-claims that exclude profitability, validation, implementation-readiness,
  production-readiness, and trading-readiness claims

The deterministic examples must be project-local, offline, credential-free,
provider-free, broker-free, notebook-free, and independent of live data.

## Decision

Decision: no-lookahead/as-of protocol remains blocked for approval.

This phase creates a partial planning boundary only. The prior Phase 33
documents define enough unresolved timing questions to scope a future approval
review, but they do not approve observation timing, action timing, lagging,
return basis, source snapshots, dividend/distribution timing, cash-rate
availability, benchmark alignment, universe inception/delisting handling, or
deterministic test examples.

This phase does not make the broad-ETF candidate ready for data acquisition,
schemas, notebooks, scripts, backtests, reproduction, result review,
evaluators, signal definitions, validated artifacts, implementation, or
trading-path work.

## Recommended Next Routing

Recommended next route: survivorship/inception/delisting boundary.

That is the narrowest next gate because no-lookahead review cannot be made
approval-ready until the candidate defines whether every ETF is usable only
after inception, how first usable observations are selected, how inactive or
delisted funds are treated, and how universe membership is fixed before any
performance inspection.

Conservative alternates remain:

- cash/benchmark return treatment boundary
- source field verification boundary
- cost/friction assumptions boundary
- result-review template boundary
- pause before code

No route may approve source use, data acquisition, an ETF universe, benchmark,
cash proxy, methodology, parameter, data policy, return construction,
no-lookahead/as-of protocol, reproduction, validation, implementation,
evaluator behavior, signal computation, or trading use.

## Explicit Non-Goals

This phase does not perform or authorize:

- no-lookahead/as-of approval
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
- no approved missing-data, stale-price, or non-trading-day policy
- no approved timing/action-date policy
- no approved source snapshot/retrieval-date policy
- no approved data revision/correction policy
- no result-review template
- no reproduction protocol
- no promotion/rejection decision
- no trading implication or production threshold
