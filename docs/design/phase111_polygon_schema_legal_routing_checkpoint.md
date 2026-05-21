# Phase 111 - Polygon Schema / Legal Routing Checkpoint

## Purpose

This document records a narrow docs-only routing checkpoint after the Phase
108 initial Polygon/Massive public-doc gap review, Phase 109 source candidate
comparison, and Phase 110 deeper Polygon/Massive public-doc normalization.

Phase 111 decides only which route should come next. It does not reopen
provider pages, browse, call APIs, download data, inspect raw observations,
draft production interfaces, create fixtures, add dependencies, change tests,
change production behavior, or approve any source or data use.

## Checkpoint Boundary

Phase 111 may route next steps only.

It must not approve:

- Polygon/Massive
- Alpha Vantage
- Stooq
- Nasdaq Data Link
- any source
- any data
- any endpoint
- any flat file
- any ETF universe
- any benchmark
- any cash proxy
- any methodology
- any parameter
- any evidence
- any return-construction policy
- any no-lookahead policy
- any cost/friction model
- any strategy validation
- any trading use

Any route named by this checkpoint is a documentation route only. It does not
authorize API calls, downloads, local snapshots, raw-row storage, repo storage,
fixtures, source use, endpoint use, flat-file use, universe construction,
benchmark construction, cash proxy construction, return construction,
no-lookahead claims, scoring, ranking, strategy validation, or trading
behavior.

## Polygon/Massive Status

Polygon/Massive remains unresolved and non-approved.

Current advisory status:

- It is the strongest technical ETF price-source candidate reviewed so far.
- Its public docs record is richer than the Alpha Vantage and Stooq records
  reviewed so far.
- Documented surfaces appear to include richer endpoint, reference-data,
  corporate-action, ticker-event, ETF-profile, and flat-file leads.
- Flat-file workflow documentation appears more concrete than the earlier
  Alpha Vantage and Stooq public-doc records.
- REST aggregate adjustment, flat-file adjustment state, reference tickers,
  active-as-of, delisted lookup, ticker events, splits, and dividends are
  useful schema/interface leads only.

Controlling unresolved gaps:

- legal, storage, archival, redistribution, derived-artifact, repo-storage,
  pass-through, and intended-use rights
- point-in-time, vintage, revision, correction, finalization, and as-of
  behavior
- ETF lifecycle completeness, ETF coverage guarantees, inactive and delisted
  ETF history, symbol continuity, fund closures, mergers, liquidations, and
  survivorship
- total-return, dividend-adjusted, ETF distribution, return-of-capital,
  capital-gains distribution, special-distribution, and exact return-basis
  behavior
- timestamp, timezone, session, calendar, holiday, half-day, stale-bar, and
  missing-bar semantics

No Polygon/Massive approval exists.

## Route Options

The table compares next-route options only. It does not select or approve any
source, endpoint, flat file, data set, universe, benchmark, cash proxy,
methodology, evidence, no-lookahead treatment, validation result, or trading
use.

| route_option | resolves_real_blocker | documentation_churn_risk | preserves_offline_pytest_and_no_real_data_constraints |
| --- | --- | --- | --- |
| Candidate-only Polygon/Massive schema/interface normalization planning | Partially. It can normalize documented shapes and future interface questions, but it does not resolve legal, storage, point-in-time, ETF lifecycle, survivorship, or return-basis blockers. | Moderate. It is useful only if tightly scoped to metadata-only and synthetic-only planning; it becomes churn if it drifts into parser, ingestion, or source-use design. | Yes, if it uses no API calls, no downloads, no real data, no fixtures with real rows, no credentials, and no production runtime behavior. |
| Polygon/Massive terms/legal review | Yes. It directly addresses the controlling storage, redistribution, archival, private/public repo, derived artifact, intended-use, and pass-through blockers before any real data use. | Moderate. It needs a precise intended workflow; otherwise the review can produce broad unresolved notes. | Yes, if it remains docs-only/legal-review-only and does not trigger API access, downloads, data acquisition, or normal-pytest dependencies. |
| Nasdaq Data Link primary-source review | Potentially. It could identify a better or clearer candidate source before more Polygon/Massive-specific work. | Moderate. It risks repeating broad candidate discovery unless constrained to primary-source public docs and Phase 93 evidence labels. | Yes, if it remains external/public-doc, docs-only, non-approving, credential-free, and data-free. |
| Pause source work | No. It avoids churn and preserves safety but leaves all source, data, and local snapshot blockers unresolved. | Low. It prevents repeated documentation loops while there is no appetite for legal review or new source review. | Yes. Pausing source work keeps normal pytest offline, credential-free, and independent from real data. |
| Antigravity read-only review | Partially. It can provide an independent critique of the routing decision and identify missed public-doc/legal questions. | Moderate to high if it repeats Phase 108/110 findings without a narrower prompt. | Yes, if explicitly read-only, docs-only, no API calls, no downloads, no source approval, no real data, and no repo data files. |

## Recommended Routing Decision

Recommended default:

Proceed with candidate-only Polygon/Massive schema/interface normalization
planning only if it remains metadata-only and synthetic-only.

That route may document candidate shapes, field names, interface questions,
schema risks, synthetic example requirements, and future review gates around
documented Polygon/Massive surfaces. It must not approve or implement
Polygon/Massive use.

Required constraints for that route:

- no API calls
- no downloads
- no real data
- no source approval
- no data approval
- no endpoint approval
- no flat-file approval
- no ingestion
- no production API implementation
- no local snapshot workflow
- no data files
- no credentials
- normal pytest remains offline and credential-free

Terms/legal review remains required before any real Polygon/Massive data use.
No local snapshot workflow may start yet. No data files may be added. No
implementation against real APIs may start.

Alternative:

If schema/interface planning is judged premature, the next best route is an
external Nasdaq Data Link primary-source review under the Phase 93 evidence
intake framework. That review must remain docs-only, primary-source-first,
non-approving, data-free, download-free, and credential-free.

## Allowed Next Steps

Allowed next steps after Phase 111:

- docs-only candidate Polygon/Massive schema/interface planning
- synthetic-only schema fixtures later, if separately scoped
- Polygon/Massive terms review
- Polygon/Massive legal review
- external Nasdaq Data Link public-doc review
- Antigravity read-only review

Forbidden next steps after Phase 111:

- API calls
- downloads
- real data
- ingestion
- source approval
- data approval
- endpoint approval
- flat-file approval
- local snapshot workflow
- data files
- production runtime behavior
- broker/runtime behavior
- signal/evaluator behavior
- strategy validation
- trading behavior

## Relationship To Prior Phases

Phase 83 defined broad ETF source-path and local snapshot readiness criteria.
Phase 111 does not approve a source path, local snapshot route, storage rule,
or manifest-to-data workflow.

Phase 93 defined the broad ETF source evidence intake plan. Phase 111 keeps all
candidate routes inside that evidence discipline and does not convert
documentation leads into approvals.

Phase 104 and Phase 105 normalized Alpha Vantage primary-source and public-doc
findings. Phase 111 keeps Alpha Vantage unresolved and non-approved.

Phase 106 normalized Stooq public-doc findings. Phase 111 keeps Stooq
unresolved and non-approved.

Phase 108 normalized the initial Polygon/Massive public-doc gap review. Phase
111 preserves its unresolved license, storage, ETF/source-quality, adjustment,
and point-in-time caveats.

Phase 109 compared Alpha Vantage, Stooq, and Polygon/Massive. Phase 111
continues the routing decision after that comparison while keeping all
candidates unresolved and non-approved.

Phase 110 normalized the deeper Polygon/Massive public-doc findings. Phase 111
uses that stronger technical record to decide whether candidate-only
schema/interface planning is safe, while preserving terms/legal, point-in-time,
ETF lifecycle, survivorship, and return-basis blockers.

Across these phases:

- source evidence does not approve source use
- endpoint documentation does not approve endpoint use
- flat-file documentation does not approve downloads, archival, or storage
- reference and ticker-event surfaces do not solve ETF universe or
  survivorship
- adjusted aggregate language does not solve dividend-adjusted or total-return
  construction
- terms/legal review remains required before real Polygon/Massive data use
- normal pytest must remain offline, credential-free, source-free, vendor-free,
  and independent from real data

## Explicit Non-Claims

Phase 111 is:

- not Polygon approval
- not Massive approval
- not source approval
- not data approval
- not endpoint approval
- not flat-file approval
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

It adds no Polygon approval, Massive approval, Alpha Vantage approval, Stooq
approval, Nasdaq Data Link approval, source approval, data approval, endpoint
approval, flat-file approval, vendor approval, universe approval, benchmark
approval, cash proxy approval, methodology approval, parameter approval,
evidence approval, return-construction approval, no-lookahead approval,
cost/friction approval, liquidity approval, strategy validation, real data
ingestion, raw external data, local data file, Polygon API call, Massive API
call, Alpha Vantage API call, Stooq download, Nasdaq Data Link call, flat-file
download, credential, ETF ticker selection, benchmark comparison, ranking,
scoring, recommendation, candidate-discovery behavior in code, replay metric,
manifest-to-planning bridge, signal/evaluator behavior, broker/order/fill/
portfolio/runtime behavior, LLM call, network call, market-data call,
dashboard/advisory/AI integration, paper behavior, live behavior, or trading
behavior.

## Decision

Decision: Polygon schema/legal routing checkpoint only.

The recommended next route is candidate-only Polygon/Massive schema/interface
normalization planning, but only as metadata-only, synthetic-only, docs-only
planning with no API calls, no downloads, no real data, no ingestion, no local
snapshot workflow, no production API implementation, and no source or data
approval.

Terms/legal review remains required before any real Polygon/Massive data use.
If schema/interface planning is considered premature, external Nasdaq Data
Link primary-source public-doc review is the preferred alternative.

All sources remain unresolved. No source or data was approved. No production
code or tests changed. No real data was added. No API calls or downloads
occurred. Normal pytest remains offline and credential-free.

## Remaining Blockers

- no approved Alpha Vantage use
- no approved Stooq use
- no approved Polygon use
- no approved Massive use
- no approved Nasdaq Data Link use
- no approved source
- no approved data
- no approved endpoint
- no approved flat file
- no approved ETF universe
- no approved benchmark
- no approved cash proxy
- no approved methodology
- no approved parameter
- no approved evidence
- no approved return-construction policy
- no approved no-lookahead/as-of policy
- no approved cost/friction model
- no approved liquidity assumption
- no approved local snapshot
- no approved storage policy for real market data
- no approved redistribution policy
- no approved legal terms interpretation
- no approved point-in-time or vintage procedure
- no approved ETF lifecycle or survivorship policy
- no approved total-return or dividend-adjusted policy
- no strategy-validation claim
- no trading-readiness claim

## Follow-Up Recommendation

Next phase should either begin candidate-only Polygon/Massive
schema/interface normalization planning under metadata-only and synthetic-only
constraints, or, if that feels premature, perform an external Nasdaq Data Link
primary-source public-doc review under the Phase 93 intake framework.
