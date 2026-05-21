# Phase 107 - ETF Source Review Routing Checkpoint

## Purpose

This document records a narrow routing checkpoint after the Alpha Vantage,
Stooq, and Antigravity ETF source-review passes.

Phase 107 does not reopen provider pages, browse, call APIs, download data,
inspect raw observations, draft vendor emails for use, create local data files,
add fixtures, add tests, add source credentials, or change production
behavior. It only records how the project should route unresolved ETF
source-review work.

## Checkpoint Boundary

Phase 107 may record routing only.

It must not approve:

- Alpha Vantage
- Stooq
- FRED
- any source
- any data
- any endpoint
- any download path
- any ETF universe
- any benchmark
- any cash proxy
- any methodology
- any parameter set
- any evidence
- any return-construction policy
- any no-lookahead policy
- any cost/friction model
- any strategy validation
- any trading use

Any source-review option named in this checkpoint is a routing option only. It
does not authorize API calls, downloads, local snapshots, raw-row storage,
fixtures, source use, universe construction, benchmark construction, cash
proxy construction, return construction, no-lookahead claims, scoring,
ranking, recommendation, strategy validation, or trading behavior.

## Alpha Vantage Status

Alpha Vantage remains unresolved.

Status captured by Phase 107:

- not approved
- not rejected solely from current evidence
- endpoint docs exist
- ETF support is implied but incomplete
- terms, storage, and commercial-use questions remain unresolved
- adjustment, point-in-time, and survivorship questions remain unresolved
- support or legal questions would be needed before any future snapshot
  workflow

Phases 104 and 105 recorded useful documentation leads, including endpoint
documentation, ETF-symbol language, listing-status leads, adjusted-data fields,
terms leads, and entitlement questions. Those leads do not approve Alpha
Vantage, any endpoint, any data, any API call, any local snapshot, or any
strategy use.

## Stooq Status

Stooq remains unresolved.

Status captured by Phase 107:

- not approved
- not rejected solely from current evidence
- operationally attractive for manual, bulk CSV, or ASCII-style snapshots
- terms unreadability is a major blocker
- adjustment defaults and ETF distribution handling remain unresolved
- point-in-time behavior, revisions, and archive immutability remain
  unresolved
- survivorship and delisted ETF handling remain unresolved
- support or legal questions would be needed before any future snapshot
  workflow

Phase 106 recorded useful public-doc leads, including per-instrument CSV
surfaces, bulk ASCII or Metastock-style surfaces, ETF and U.S. ETF category
leads, OHLCV-style availability, archive generation timestamps, third-party
provider references, and adjustment controls. Those leads do not approve
Stooq, any download path, any data, any local snapshot, or any strategy use.

## Antigravity Review

Antigravity performed a read-only inspection comparing Alpha Vantage and
Stooq.

Phase 107 records the Antigravity result as advisory context only:

- no files changed
- full pytest passed
- Alpha Vantage remained unresolved
- Stooq remained unresolved
- shared blockers were confirmed, including terms and licensing, ETF corporate
  actions and distributions, point-in-time behavior and revisions, delisted ETF
  history, symbol continuity, and offline pytest constraints
- Antigravity recommended redirecting to FRED rate/cash work

Project decision: do not automatically follow the FRED redirect. Phases 96
through 103 already captured enough FRED and H.15 complexity to pause that
track unless a concrete ALFRED or point-in-time need emerges. FRED is not ETF
price data, and FRED work would not resolve the current ETF price-source
blockers around terms, ETF distributions, adjusted-price methodology,
survivorship, delisted ETF history, symbol continuity, or local snapshot
rights.

## Next-Route Options

Phase 107 compares routing options only. It does not rank, score, approve, or
select any source for use.

| route_option | blocker addressed | churn risk | Phase 107 routing note |
| --- | --- | --- | --- |
| Alpha Vantage support questions | Could clarify terms, storage, commercial use, ETF coverage, adjusted methodology, distribution handling, revisions, listing status, delisted ETF behavior, and point-in-time behavior. | High if no one is ready to contact Alpha Vantage or route answers through legal review. | Useful only if the user is willing to contact vendor support or legal counsel. Do not draft yet by default. |
| Stooq support questions | Could clarify terms, storage, automated or bulk download rights, third-party pass-through restrictions, adjustment defaults, ETF distributions, archive immutability, revisions, inactive coverage, and symbol continuity. | High if readable terms and support or legal follow-up are not available. | Useful only if the user is willing to contact Stooq or legal counsel. Do not draft yet by default. |
| Legal or terms review | Directly addresses the controlling rights, storage, redistribution, commercial-use, private-repo, public-repo, and automation blockers for Alpha Vantage or Stooq. | Moderate if performed without a concrete intended workflow, because legal review needs exact use facts. | Useful if the user wants to keep Alpha Vantage or Stooq alive. Still would not approve data or source use by itself. |
| Another ETF source candidate review | Could identify a source with clearer licensing, point-in-time, survivorship, delisted-history, adjustment, and distribution documentation. | Moderate if it repeats scout-style documentation without primary-source normalization. | Useful next source-review path if limited to external primary-source review and later docs-only normalization. Candidate examples include Polygon.io, Nasdaq Data Link, or another paid/professional data source with clearer documentation. |
| FRED ALFRED/PIT work | Could help future benchmark, cash, or rate point-in-time review if a concrete ALFRED need appears. | High for the current ETF price-source problem, because FRED does not resolve ETF price-source terms, ETF distributions, survivorship, delisted history, symbol continuity, or adjusted-price methodology. | Do not return to FRED immediately. Revisit only if a specific benchmark/cash/rate ALFRED or point-in-time question becomes the active blocker. |
| Pause ETF source work | Avoids repeated documentation churn while no vendor/legal contact or new candidate source-review target is selected. | Low operational risk, but leaves source work unresolved. | Acceptable if the project is not ready for vendor/legal outreach or another primary-source review. |

## Recommended Routing Decision

Recommended decision:

- pause Alpha Vantage and Stooq as unresolved
- do not draft support questions yet unless the user is willing to contact
  vendors or legal counsel
- do not return to FRED immediately
- make the next useful source-review path either another ETF data candidate
  with potentially clearer terms, point-in-time, and survivorship
  documentation, or a legal/terms review track if the user wants to keep Alpha
  Vantage or Stooq alive

Candidate next source-review targets may include:

- Polygon.io
- Nasdaq Data Link
- another paid or professional data source with clearer licensing,
  point-in-time, survivorship, delisted-history, adjustment, and distribution
  documentation
- broker data only if explicitly scoped later

No candidate source is approved by this checkpoint.

## Allowed Next Steps

Allowed next steps after Phase 107:

- external primary-source review for another candidate source
- legal or terms review for Alpha Vantage or Stooq
- vendor support-question drafting if the user chooses to contact vendors or
  legal counsel

Still forbidden after Phase 107:

- downloads
- ingestion
- repo fixtures or data
- real data files
- source approval
- data approval
- endpoint approval
- download-path approval
- implementation

Normal `python -m pytest` must remain offline, credential-free, source-free,
vendor-free, network-free, and independent from Alpha Vantage, Stooq, FRED,
Polygon.io, Nasdaq Data Link, broker data, and any other market-data source.

## Relationship To Prior Phases

Phase 93 defined the broad ETF source evidence intake plan. Phase 107 keeps
source-review work inside that framework and records routing only.

Phase 94 normalized broad ETF source evidence as advisory intake material.
Phase 107 continues the separation between external source leads and source
approval.

Phase 95 normalized primary-source verification output for Alpha Vantage,
Stooq, and FRED. Phase 107 records that all three remain non-approved and that
FRED is not ETF price data.

Phase 104 normalized Alpha Vantage primary-source verification. Phase 105
normalized Alpha Vantage public-doc gap review. Phase 107 keeps Alpha Vantage
unresolved and pauses it unless vendor/legal outreach is chosen.

Phase 106 normalized Stooq public-doc gap review. Phase 107 keeps Stooq
unresolved and pauses it unless vendor/legal outreach is chosen.

Phases 96 through 103 captured FRED and H.15 benchmark, cash, rate,
discount-basis, averaging, and point-in-time complexity. Phase 107 records the
project decision not to automatically redirect to FRED unless a concrete
ALFRED or point-in-time need emerges.

## Explicit Non-Claims

Phase 107 is:

- not Alpha Vantage approval
- not Stooq approval
- not FRED approval
- not source approval
- not data approval
- not endpoint approval
- not download-path approval
- not universe approval
- not benchmark approval
- not cash proxy approval
- not methodology approval
- not parameter approval
- not evidence approval
- not return-construction approval
- not no-lookahead approval
- not cost/friction approval
- not liquidity approval
- not strategy validation
- not trading readiness

It adds no Alpha Vantage approval, Stooq approval, FRED approval, source
approval, data approval, endpoint approval, download-path approval, vendor
approval, universe approval, benchmark approval, cash proxy approval,
methodology approval, parameter approval, evidence approval,
return-construction approval, no-lookahead approval, cost/friction approval,
liquidity approval, strategy validation, real data ingestion, raw external
data, local data file, API call, data download, credential, ETF ticker
selection, benchmark comparison, ranking, scoring, recommendation,
candidate-discovery behavior in code, replay metric, manifest-to-planning
bridge, signal/evaluator behavior, broker/order/fill/portfolio/runtime
behavior, LLM call, network call, market-data call, dashboard/advisory/AI
integration, paper behavior, live behavior, or trading behavior.

## Decision

Decision: ETF source-review routing checkpoint only.

Alpha Vantage and Stooq remain unresolved. Antigravity review was advisory and
read-only. No source or data was approved. No production code or tests changed.
No real data was added. No API calls or downloads occurred.

The next useful source-review path is external primary-source review for
another candidate source such as Polygon.io, Nasdaq Data Link, or another paid
or professional data source with clearer licensing and source-quality
documentation, unless the user wants vendor/legal outreach first.

Normal pytest remains offline and credential-free.

## Remaining Blockers

- no approved Alpha Vantage use
- no approved Stooq use
- no approved FRED use
- no approved source
- no approved data
- no approved endpoint
- no approved download path
- no approved ETF universe
- no approved benchmark
- no approved cash proxy
- no approved methodology
- no approved parameter set
- no approved evidence
- no approved return-construction policy
- no approved no-lookahead/as-of policy
- no approved survivorship policy
- no approved delisted or inactive ETF policy
- no approved symbol-continuity policy
- no approved ETF distribution treatment
- no approved adjustment methodology
- no approved revision or correction policy
- no approved archive immutability policy
- no approved point-in-time source policy
- no approved local snapshot
- no approved raw-row storage policy
- no approved private-repo storage policy
- no approved public-repo storage policy
- no approved redistribution policy
- no approved commercial/internal research policy
- no approved normal-pytest source dependency
- no strategy-validation claim
- no trading-readiness claim
