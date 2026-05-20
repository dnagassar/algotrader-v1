# Phase 90 - Broad ETF Benchmark / Cash Timing Boundary

## Purpose

This document defines policy questions and readiness gates for future benchmark
and cash-proxy treatment before broad ETF research can claim comparability,
excess return, out-of-market performance, or benchmark-relative behavior.

It is documentation-only. It exists to prevent a future research run from
accidentally comparing strategy results against an inconsistent benchmark or
treating cash, T-bill, risk-free, or rate series as decision-safe without
publication timing, return basis, compounding, and calendar alignment rules.

## Boundary

Phase 90 may define benchmark and cash timing interpretation rules only.

It does not approve:

- any benchmark
- any cash proxy
- any FRED or rate series
- any ETF universe
- any ETF ticker
- any source
- any data
- any methodology
- any parameter set
- any evidence
- any return construction
- any no-lookahead protocol
- any strategy validation
- any trading use

No benchmark series, cash series, rate series, ETF ticker, universe, source,
data file, methodology, parameter, evidence package, strategy result, or
trading behavior becomes eligible for implementation or research claims.

## Benchmark Role Semantics

Future broad ETF work must label benchmark roles explicitly. None of these
roles is approved in this phase.

| Role | Meaning | Phase 90 boundary |
| --- | --- | --- |
| Primary benchmark | The main reference series used for headline comparison or relative-performance framing. | Not approved; would require separate candidate approval, return-basis documentation, timing documentation, and comparability review. |
| Secondary benchmark | An additional context series used to test sensitivity against another reference. | Not approved; must not weaken or bypass the primary benchmark gates. |
| Buy-and-hold comparison | A simple hold-through-time comparison against one instrument, index, or portfolio proxy. | Not approved; requires inception, availability, return-basis, and action-timing rules. |
| Equal-weight universe comparison | A reference constructed from equal-weighting the eligible research universe. | Not approved; requires approved universe membership, rebalancing, missing-data, survivorship, return-basis, and timing rules. |
| Asset-class-matched benchmark | A benchmark intended to reflect the same exposure class as the strategy opportunity set. | Not approved; exposure matching and methodology changes must be documented later. |
| Broad equity benchmark | A general equity-market context benchmark. | Not approved; broad context does not prove comparability to a specific ETF universe or strategy. |
| Cash-only comparison | A comparison that assumes all capital remains in a cash-like return stream. | Not approved; requires a separately approved cash proxy and accrual timing policy. |
| No-benchmark exploratory run | A run that reports strategy-shaped outputs without benchmark-relative claims. | Not approved for validation; may only be considered later if clearly labeled as exploratory and non-comparable. |

Benchmark role labels are presentation semantics only until a later phase
approves the candidate, data source, return basis, timing, calendar, and
comparability rules.

## Benchmark Return-Basis Requirements

Benchmark comparability requires matching return basis and timing assumptions
between the strategy result and the benchmark result. None of the following is
resolved or approved here.

- Price return versus total return: future reports must state whether a
  benchmark excludes or includes dividends, distributions, and reinvestment.
- Adjusted close assumptions: adjusted benchmark values may encode splits,
  distributions, corrections, and vendor methodology choices that are not
  point-in-time safe by default.
- Dividend and distribution handling: distribution inclusion, ex-date,
  payment-date, reinvestment timing, tax treatment, and fee treatment must be
  documented before economic comparison.
- Benchmark inception and availability: the first displayed benchmark value is
  not automatically the first usable comparison date or first historically
  knowable date.
- Benchmark calendar alignment: benchmark sessions, holidays, missing market
  days, rebalance dates, strategy decision dates, action dates, and cash
  accrual dates must be aligned by explicit rule.
- Benchmark missing or stale data: missing rows, stale values, suspended
  observations, unavailable constituents, and delayed publication must have a
  deterministic later policy.
- Benchmark survivorship and methodology changes: index, fund, or constructed
  benchmark histories can change membership, calculation policy, fees,
  corporate-action treatment, or constituent availability over time.
- Benchmark revision and vendor correction risk: corrected or restated
  histories must not be silently treated as originally available
  point-in-time data.

A benchmark total-return series must not be compared to a strategy
price-return series as if they share the same basis. A benchmark with
same-close labels must not imply a strategy could decide and trade at that
same close. A benchmark result is not comparable until the selected benchmark,
source, return basis, publication/as-of timing, revision policy, calendar
alignment, and missing/stale data policy are separately approved.

## Cash Proxy Roles

Future broad ETF work must label cash proxy roles explicitly. No cash proxy is
approved in this phase.

| Role | Meaning | Phase 90 boundary |
| --- | --- | --- |
| Out-of-market cash return | Return assigned to capital when a strategy is not invested in risk assets. | Not approved; requires rate source, timing, compounding, accrual, and calendar rules. |
| Risk-free comparison | A reference series used to describe excess return or risk-free-relative performance. | Not approved; no risk-free series, tenor, source, or timing convention is selected. |
| Collateral or idle cash approximation | A simplifying return assumption for uninvested or reserved capital. | Not approved; must not be treated as actual broker yield or guaranteed availability. |
| Zero-return cash fallback | A conservative placeholder that assumes no cash yield. | Not approved; even zero return requires explicit role, calendar, and compounding treatment if used in comparisons. |
| T-bill proxy | A Treasury bill-like rate or return proxy. | Not approved; tenor, auction/secondary-market source, publication lag, conversion, and revisions are unresolved. |
| Money-market proxy | A fund-like or money-market-rate-like proxy. | Not approved; fee, yield convention, availability, and source rules are unresolved. |
| Broker sweep or cash yield | Future operational context for actual account cash treatment. | Not approved; broker sweep rates are operational context only and do not authorize research or trading use. |

Cash proxy labels are assumptions, not evidence. They do not approve a source,
series, return construction, excess-return calculation, or out-of-market
performance claim.

## Cash Timing And Publication Risks

Cash and rate series have timing hazards that must be resolved before use.
None of these rules is approved here.

- Rate observation date: the date a rate claims to describe is not necessarily
  the date it became available to the strategy.
- Publication date: a rate may be released after the observation date, after
  the strategy decision timestamp, or after the action timestamp.
- Revision date: a later revision, correction, restatement, or vendor update
  can change historical values.
- Decision timestamp: the modeled time at which the strategy decides must be
  separated from rate observation, publication, and revision timestamps.
- Action timestamp: the modeled time at which a trade or allocation change
  could occur must be separated from the cash accrual period.
- Daily or monthly conversion: annualized, monthly, weekly, or quoted rates
  require an explicit conversion rule before daily strategy returns can use
  them.
- Compounding convention: simple interest, daily compounding, monthly
  compounding, continuous compounding, business-day accrual, and calendar-day
  accrual produce different results.
- Holiday and calendar alignment: rate calendars, market calendars, weekends,
  holidays, rebalance dates, and non-trading days need deterministic alignment.
- Stale rate handling: carrying forward a known rate may be reasonable only if
  a later policy defines maximum staleness and availability.
- Missing rate handling: gaps must not be filled silently; interpolation,
  carry-forward, zeroing, blocking, or dropping periods require explicit
  approval.
- Known-before-decision status: a rate value can affect a modeled cash return
  only if it was known under the selected as-of rule before the relevant
  strategy decision.
- FRED or rate-series revision and availability risk: a current downloaded
  history may include revised or backfilled values that were not available at
  historical decision times.

No FRED series, Treasury series, money-market series, broker sweep series, or
other cash proxy is selected, approved, or made implementation-ready.

## Benchmark And Cash No-Lookahead Rules

Future benchmark and cash comparisons must be point-in-time honest before they
can support research claims. This phase defines minimum rules to resolve
later; it does not approve a no-lookahead protocol.

- Benchmark and cash data must be available at the modeled decision time before
  they can affect a strategy-relative claim, cash-return claim, or excess-return
  claim.
- Future rate values cannot determine past cash returns unless the run is
  explicitly labeled retrospective and non-point-in-time-safe.
- Revised benchmark or rate series cannot be silently treated as
  point-in-time data; revision and acquisition policy must be documented.
- Same-close benchmark or cash alignment must not imply the strategy could
  observe, decide, and trade at that same close.
- Cash accrual timing must be explicit, including whether cash earns during
  the decision day, action day, holding period, weekends, holidays, and
  out-of-market intervals.
- Benchmark return windows, strategy return windows, and cash accrual windows
  must share an explicit timing convention before comparison.
- Missing, stale, corrected, or unavailable benchmark and cash observations
  must follow deterministic later-approved policies.

Benchmark-relative behavior, excess return, and out-of-market performance
remain blocked until those rules are separately approved and tested.

## Minimum Future Approval Gates

Before future broad ETF research may use benchmark or cash results, a later
phase must document at minimum:

- benchmark candidate remains candidate-only until separately approved
- cash proxy candidate remains candidate-only until separately approved
- benchmark return basis documented
- cash return basis documented
- benchmark and cash data source documented
- benchmark and cash publication/as-of timing documented
- compounding and frequency conversion documented
- calendar alignment documented
- missing and stale data policy documented
- universe and benchmark comparability documented
- normal pytest remains synthetic, offline, credential-free, provider-free,
  broker-free, and independent of real benchmark or cash data

Passing these gates would still not by itself approve a benchmark, cash proxy,
source, data, universe, methodology, parameter, evidence, return construction,
no-lookahead protocol, strategy validation, implementation, or trading use.
Any approval would need a separate explicit phase.

## Relationship To Prior Phases

Phase 83 defined broad ETF source-path and local snapshot readiness criteria.
Local snapshot metadata may describe future source or file context, but it
does not approve benchmark data, cash data, rate data, return comparability, or
out-of-market return treatment.

Phase 84 added `LocalSnapshotManifest` as a frozen, slotted, metadata-only
contract. Manifest metadata does not approve benchmark or cash data, does not
prove publication timing, and does not make benchmark or cash series
normal-pytest inputs.

Phase 88 defined local snapshot return-basis and as-of interpretation rules.
Those return-basis and as-of rules are required before benchmark or cash
comparison can be meaningful, but they do not select or approve any benchmark
or cash proxy.

Phase 89 defined broad ETF universe, inception, and survivorship boundaries.
Universe rules must be resolved before benchmark comparability claims because
benchmark choice, equal-weight universe comparison, asset-class matching, and
cash-only comparison all depend on what the research universe is allowed to
represent.

Benchmark and cash timing remain separate from strategy validation. Even a
well-described benchmark or cash proxy would not validate a strategy, approve
parameters, or authorize trading.

## Explicit Non-Claims

Phase 90 is:

- not benchmark approval
- not cash proxy approval
- not source approval
- not data approval
- not universe approval
- not methodology approval
- not parameter approval
- not evidence approval
- not return-construction approval
- not no-lookahead approval
- not strategy validation
- not trading readiness

It also adds no real data ingestion, no real market data, no real ETF tickers,
no benchmark comparison, no cash return series, no rate series, no
excess-return calculation, no ranking, no scoring, no recommendation, no
candidate discovery, no replay metrics, no report rendering, no
manifest-to-planning bridge, no signal or evaluator behavior, no advisory
integration, no governance behavior, no broker, order, fill, portfolio,
runtime, paper, live, or trading behavior, and no LLM, network, API, provider,
FRED, rate-series, or market-data call.

## Decision

Decision: benchmark and cash timing boundary only.

The project is not ready to select or use a benchmark or cash proxy. Future
work may continue with docs-only blockers such as cost and friction
assumptions, but benchmark/cash comparability remains blocked until a later
explicit phase resolves the approval gates above.

## Remaining Blockers

- no approved source
- no approved data
- no approved local snapshot
- no approved ETF universe
- no approved ETF ticker
- no approved benchmark
- no approved benchmark source
- no approved benchmark return basis
- no approved benchmark timing policy
- no approved benchmark missing or stale data policy
- no approved cash proxy
- no approved cash source
- no approved cash return basis
- no approved cash timing policy
- no approved cash compounding convention
- no approved rate observation/publication/revision policy
- no approved calendar alignment policy
- no approved universe/benchmark comparability policy
- no approved methodology
- no approved parameter set
- no approved evidence
- no approved return construction
- no approved no-lookahead/as-of policy
- no approved implementation-readiness claim
- no approved strategy-validation claim
- no approved trading-readiness claim
