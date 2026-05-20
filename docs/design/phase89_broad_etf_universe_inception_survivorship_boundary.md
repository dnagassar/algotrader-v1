# Phase 89 - Broad ETF Universe / Inception / Survivorship Boundary

## Purpose

This document defines policy questions and readiness gates for any future broad
ETF universe before real data, implementation, benchmark or cash policy, or
strategy validation.

It is documentation-only. It exists to prevent a future research run from
accidentally treating today's surviving ETFs, future-known membership, or
after-the-fact inception and delisting knowledge as if those facts were
point-in-time eligible research inputs.

## Boundary

Phase 89 may define universe, inception, and survivorship interpretation rules
only.

It does not approve:

- any ETF universe
- any ETF ticker
- any source
- any data
- any benchmark
- any cash proxy
- any methodology
- any parameter set
- any evidence
- any return construction
- any no-lookahead protocol
- any strategy validation
- any trading use

No real market data is added. No ETF ticker is selected. No data source,
universe membership, benchmark series, cash series, methodology, parameter, or
evidence package becomes eligible for implementation or research claims.

## Universe Membership Semantics

Future work must keep universe labels explicit. None of these universe types is
approved in this phase.

| Universe type | Meaning | Phase 89 boundary |
| --- | --- | --- |
| Candidate universe | A proposed set, bucket, or rule family that might be reviewed later. | Candidate-only; not approved for research, validation, or trading. |
| Research universe | The set of instruments a research run is allowed to consider. | Not approved; would require source, membership timing, inception, delisting, symbol, missing-data, and no-lookahead rules first. |
| Benchmark universe | The reference instrument set, index family, or comparison universe used for performance context. | Not approved; benchmark and cash policy remain separate blockers. |
| Tradable universe | The instruments a runtime or broker path may submit orders for. | Not approved; no broker, order, fill, portfolio, runtime, paper, live, or trading behavior exists here. |
| Active-only universe | A set filtered to instruments active at a selected date, often the current date. | Not approved; can be survivorship-biased if used as historical eligibility. |
| Point-in-time universe | A set whose membership is determined only from information knowable at each decision time. | Not approved; this is a required future safety target, not an achieved state. |
| Current-survivor universe | Today's surviving instruments treated as the historical opportunity set. | Not approved; this is a high-risk survivorship-biased convenience unless explicitly labeled as retrospective and non-point-in-time-safe. |

Universe membership must remain an input assumption. It must not be inferred
from inspected performance, later survival, later popularity, future liquidity,
future closure history, or any data known only after the historical decision
time.

## Inception Eligibility

Future broad ETF research must distinguish several dates before an instrument
can become eligible. None of these rules is approved here.

- ETF inception date: the date a fund is launched, listed, or otherwise begins
  existence according to later-approved metadata. It is not by itself a first
  usable research date.
- First available price date: the first row present in a future snapshot or
  source export. It may be later than inception, may be backfilled, may be
  revised, and is not automatically tradable or research-eligible.
- First usable observation date: the first observation that satisfies later
  source, schema, adjustment, return-basis, missing-data, stale-data,
  identifier, and availability rules. This may be later than the first
  available price date.
- Required warmup period for moving averages: a future moving-average method
  would need enough prior usable observations to form the first complete
  average without borrowing future data. Warmup is not approved here.
- First eligible signal date: the earliest date on which a future research run
  may compute a signal after inception, first usable observations, warmup,
  missing/stale handling, and availability timing are satisfied.
- First eligible action date: the earliest date on which a future protocol may
  act after the signal is knowable under an approved decision/action timing
  rule. It may be later than the first eligible signal date.

First available data is not automatically the first tradable date, first
eligible research date, first eligible signal date, or first eligible action
date.

## Survivorship And Delisting Risks

Future policy must address inactive instruments and corporate events before a
broad ETF universe can support point-in-time-safe claims. None of the following
treatments is approved here.

- Dead, liquidated, or merged ETFs may be missing from today's listings even
  though they existed during historical decision dates.
- Fund closures can remove future rows, create terminal-value uncertainty, or
  require a later-approved liquidation, cash, replacement, or exclusion rule.
- Mergers can combine histories or change exposure in ways a simple ticker
  string cannot describe.
- Symbol changes can break continuity or accidentally splice distinct histories
  together.
- Missing final prices can distort terminal returns, drawdowns, and exit
  assumptions if a closure or delisting occurs.
- Delisting returns require explicit treatment before any performance claim.
- Stale quotes must be detected and handled under a later missing/stale data
  policy.
- Backfilled data can make an instrument appear historically available before
  the value, adjustment, or metadata was actually knowable.
- Today's surviving ETF list is a survivorship-biased source if it is used as a
  historical opportunity set without a clear retrospective limitation.

Excluding inactive or failed funds may be acceptable only as a clearly labeled
retrospective convenience in a later analysis. It must not be presented as a
point-in-time-safe universe unless separately approved by a future boundary.

## Identifier Policy Questions

Future broad ETF universe work must document identity rules before any
implementation or research claim. This phase does not require implementation
and does not approve any identifier policy.

Questions include:

- whether ticker symbol is sufficient for display only or can serve as a stable
  research key
- how fund name is captured and whether historical names are preserved
- how issuer is captured and how issuer changes, mergers, or reorganizations
  are represented
- how exchange is captured and how exchange moves or listing changes are
  represented
- whether CUSIP, ISIN, or another durable identifier is available later and
  whether license or redistribution rules allow storing it
- how symbol changes are mapped without assuming continuity from current ticker
  alone
- how symbol reuse is detected so unrelated histories are not joined
- how identifiers map across data vendors with different symbol formats,
  historical coverage, corrections, and corporate-event conventions

Identifier metadata may help describe a future snapshot, but it must not be
treated as source approval, data approval, universe approval, or continuity
proof.

## No-Lookahead Universe Rules

Future universe membership must be knowable at the decision time used by the
research protocol.

Minimum rules for later approval include:

- future inclusion or exclusion must not affect past eligibility
- a fund's later survival must not make it eligible at earlier decision dates
- a fund's later closure, merger, liquidation, or delisting must not be used
  before that fact was knowable unless the run is explicitly labeled
  retrospective and non-point-in-time-safe
- inception, first price, first usable observation, warmup, signal, and action
  dates must be evaluated using only information available under the selected
  as-of rule
- current issuer pages, current listings, current assets, current expense
  ratios, and current liquidity must not silently define past membership
- research runs must distinguish retrospective convenience from
  point-in-time-safe claims in their manifests, reports, and limitations

This phase defines the need for no-lookahead universe rules, but it does not
approve a no-lookahead protocol.

## Minimum Future Approval Gates

Before any future broad ETF universe can be used, a later phase must document
at minimum:

- source candidate remains candidate-only until separately approved
- universe selection rule
- membership timestamp or as-of rule
- inception handling
- delisting, closure, and merger handling
- symbol identity and mapping policy
- missing and stale data policy
- warmup and eligibility rule
- normal pytest remains synthetic, offline, credential-free, provider-free,
  broker-free, and independent of real universe data

Passing these gates would still not by itself approve a source, data, universe,
benchmark, cash proxy, methodology, parameter, evidence, return construction,
no-lookahead protocol, strategy validation, implementation, or trading use.
Any approval would need a separate explicit phase.

## Relationship To Prior Phases

Phase 83 defined broad ETF source-path and local snapshot readiness criteria.
That boundary requires future universe membership and inception/survivorship
policy before local broad ETF data can be consumed, but it did not approve a
source, snapshot, universe, or data use.

Phase 84 added `LocalSnapshotManifest` as a frozen, slotted, metadata-only
contract. Manifest metadata may describe a snapshot, but it does not approve
universe membership, source rights, data quality, point-in-time eligibility, or
survivorship handling.

Phase 88 defined local snapshot return-basis and as-of interpretation rules.
Return basis and as-of metadata do not solve survivorship. A local snapshot can
be reproducible while still containing today's surviving instruments,
future-known membership, backfilled history, or after-the-fact delisting
knowledge.

Universe rules must be resolved before any broad ETF strategy claim.

## Explicit Non-Claims

Phase 89 is:

- not universe approval
- not ETF ticker approval
- not source approval
- not data approval
- not benchmark approval
- not cash proxy approval
- not methodology approval
- not parameter approval
- not evidence approval
- not return-construction approval
- not no-lookahead approval
- not strategy validation
- not trading readiness

It also adds no real data ingestion, no real market data, no real ETF tickers,
no benchmark comparison, no ranking, no scoring, no recommendation, no
candidate discovery, no replay metrics, no manifest-to-planning bridge, no
signal or evaluator behavior, no advisory integration, no governance behavior,
no broker, order, fill, portfolio, runtime, paper, live, or trading behavior,
and no LLM, network, API, provider, or market-data call.

## Decision

Decision: universe, inception, and survivorship boundary only.

The project is not ready to define or use a broad ETF universe. Future work may
continue with docs-only blockers such as benchmark/cash timing or cost/friction
assumptions, but broad ETF universe use remains blocked until a later explicit
phase resolves the approval gates above.

## Remaining Blockers

- no approved source
- no approved data
- no approved local snapshot
- no approved ETF universe
- no approved ETF ticker
- no approved benchmark
- no approved cash proxy
- no approved methodology
- no approved parameter set
- no approved evidence
- no approved adjustment policy
- no approved return basis
- no approved return construction
- no approved no-lookahead/as-of policy
- no approved universe selection rule
- no approved membership timestamp/as-of rule
- no approved inception handling
- no approved first-usable-observation rule
- no approved warmup/eligibility rule
- no approved active/inactive fund policy
- no approved closure, merger, delisting, or terminal-return treatment
- no approved stale or missing data policy
- no approved symbol identity or vendor mapping policy
- no implementation-readiness claim
- no strategy-validation claim
- no trading-readiness claim
