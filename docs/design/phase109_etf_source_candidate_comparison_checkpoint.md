# Phase 109 - ETF Source Candidate Comparison Checkpoint

## Purpose

This document records a narrow ETF source-candidate comparison checkpoint
after the advisory Alpha Vantage, Stooq, and Polygon/Massive public-doc and
source-review phases.

Phase 109 does not reopen provider pages, browse, call APIs, download data,
inspect raw observations, draft vendor emails for use, create local data
files, add fixtures, add tests, add dependencies, add credentials, or change
production behavior. It compares candidate status and routes the smallest safe
next step only.

## Checkpoint Boundary

Phase 109 may compare candidate status and route next steps only.

It must not approve:

- Alpha Vantage
- Stooq
- Polygon/Massive
- any source
- any data
- any endpoint
- any download path
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

Any comparison, routing option, or candidate named in this checkpoint is a
documentation route only. It does not authorize API calls, downloads, flat-file
use, local snapshots, raw-row storage, fixtures, source use, universe
construction, benchmark construction, cash proxy construction, return
construction, no-lookahead claims, scoring, ranking, source-use
recommendation, strategy validation, or trading behavior.

## Allowed Disposition Vocabulary

Allowed `current_disposition` values in this document are:

- `unresolved`
- `reject_for_now`
- `context_only`
- `candidate_needs_more_evidence`

Forbidden `current_disposition` values are:

- `approved`
- `validated`
- `source_approved`
- `data_approved`
- `strategy_ready`
- `trading_ready`

The allowed values route later review only. They do not approve any candidate,
source, data, endpoint, download path, flat file, universe, benchmark, cash
proxy, methodology, parameter, evidence, return construction, no-lookahead
policy, cost/friction model, liquidity assumption, strategy validation, or
trading use.

## Alpha Vantage Summary

Alpha Vantage remains unresolved.

Phase 109 records this status:

- endpoint documentation exists
- ETF support is implied but incomplete
- adjusted data exists, but formula, exact return basis, and point-in-time
  behavior remain unresolved
- listing/status support is partially documented, but not enough to establish
  survivorship-safe histories or point-in-time ETF universe membership
- terms, storage, commercial-use, local archival, redistribution, and repo
  storage questions remain unresolved
- no Alpha Vantage source, data, endpoint, universe, return construction,
  evidence, no-lookahead policy, strategy validation, or trading use is
  approved

Alpha Vantage is not rejected solely from the current advisory evidence, but
the public-doc record is not strong enough to support a local snapshot,
ingestion path, or implementation path.

## Stooq Summary

Stooq remains unresolved.

Phase 109 records this status:

- Stooq remains operationally attractive as a manual or bulk CSV/ASCII-style
  source candidate
- ETF and U.S. ETF categories are documented as public-doc leads
- terms remain unreadable or unverified in the recorded review trail
- adjustment defaults and ETF distribution handling remain unresolved
- point-in-time behavior, archive immutability, corrections, revisions, and
  prior vintages remain unresolved
- survivorship, delisted ETF handling, old-symbol retention, and ETF lifecycle
  handling remain unresolved
- third-party provider restrictions and pass-through obligations remain
  unresolved
- no Stooq source, data, download path, universe, return construction,
  evidence, no-lookahead policy, strategy validation, or trading use is
  approved

Stooq is not rejected solely from the current advisory evidence, but terms and
data-quality gaps are too large for any local snapshot or implementation path.

## Polygon/Massive Summary

Polygon/Massive remains unresolved.

Phase 109 records this status:

- Polygon/Massive is technically richer than Alpha Vantage and Stooq in the
  public-doc surfaces captured by Phase 108
- documented surfaces include aggregates, grouped daily aggregates, trades,
  quotes, reference tickers, splits, dividends, ticker events, and flat files
- API-key, plan/pricing, and Market Data Terms leads are documented
- split-adjusted aggregate behavior appears documented, but dividend-adjusted
  or total-return behavior is not approved
- point-in-time behavior, prior vintages, corrections, finalization timing,
  and as-of snapshot reconstruction remain unresolved
- ETF lifecycle completeness, delisted ETF coverage, ticker-event
  completeness, fund closures, mergers, liquidations, and survivorship remain
  unresolved
- storage, redistribution, commercial-use, derived metadata, manifest,
  checksum, exchange pass-through, vendor pass-through, and legal terms remain
  unresolved
- no Polygon/Massive source, data, endpoint, flat-file path, universe, return
  construction, evidence, no-lookahead policy, strategy validation, or trading
  use is approved

Polygon/Massive is not rejected solely from the current advisory evidence, but
its richer technical surface still needs targeted support and legal review
before any future source-use discussion.

## Candidate Comparison Table

The table compares only current advisory-review status. It does not score,
rank, approve, validate, or select any candidate for use.

| candidate | technical_surface_strength | documentation_strength | terms_storage_status | adjustment_return_basis_status | PIT_revision_status | survivorship_lifecycle_status | operational_fit | key_blockers | current_disposition | allowed_next_step |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Alpha Vantage | Moderate endpoint surface for time series and adjusted data. | Endpoint docs and ETF-support leads exist, but ETF completeness and methodology detail remain incomplete. | Terms, storage, commercial use, archival, private/public repo storage, and redistribution remain unresolved. | Adjusted data exists, but formulas, ETF distribution handling, dividend/total-return interpretation, and PIT adjustment state remain unresolved. | Revisions, corrections, finalization, and prior vintages remain unresolved. | Listing/status support is partially documented but not enough for survivorship-safe histories, delisted ETF history, or PIT universe membership. | Convenient API candidate, but API-key and entitlement boundaries remain unresolved. | Terms/storage, adjustment formulas, PIT behavior, survivorship, ETF lifecycle, and local snapshot rights. | `unresolved` | Vendor support questions only if Alpha Vantage is kept alive; otherwise pause. |
| Stooq | Moderate for manual/bulk CSV or ASCII-style OHLCV access. | Public download/category leads exist, including ETF categories, but schema and terms evidence are weak. | Terms are unreadable or unverified; storage, redistribution, automation, and third-party provider pass-through restrictions remain unresolved. | Adjustment controls exist as leads, but defaults, formulas, ETF distributions, dividend adjustment, split adjustment, and total-return treatment remain unresolved. | Archive timestamps exist as leads, but archive immutability, corrections, revisions, prior vintages, and as-of reconstruction remain unresolved. | ETF categories exist as leads, but delisted ETFs, inactive coverage, old symbols, closures, mergers, liquidations, and PIT membership remain unresolved. | Operationally attractive for manual or bulk snapshots, but rights and methodology gaps dominate. | Terms readability, provider restrictions, adjustment/distribution handling, PIT/archive immutability, survivorship, and lifecycle gaps. | `unresolved` | Vendor support or terms review only if Stooq is kept alive; otherwise pause. |
| Polygon/Massive | Stronger technical surface across aggregates, trades, quotes, reference data, corporate actions, ticker events, and flat files. | Richer public-doc surface than Alpha Vantage/Stooq, but still incomplete for exact ETF snapshot approval. | Market Data Terms non-redistribution language is a controlling lead; storage, archival, redistribution, commercial use, derived metadata, manifests, checksums, and pass-through obligations remain unresolved. | Split-adjusted aggregate behavior appears documented, but dividend-adjusted prices, total return, ETF distribution taxonomy, exact formulas, and return-basis approval remain unresolved. | PIT/vintage access, prior as-of snapshots, finalization timestamps, corrections, revisions, missing/stale bars, and calendar behavior remain unresolved. | Reference and ticker-event surfaces exist, but explicit ETF coverage guarantees, delisted ETF coverage, closures, mergers, liquidations, and PIT universe membership remain unresolved. | Best fit for targeted support/legal questions because the technical surface is richer and more concrete, but no use is approved. | Legal/storage, PIT/vintage, ETF lifecycle completeness, survivorship, redistribution, pass-through obligations, and return-basis gaps. | `unresolved` | Targeted Polygon/Massive support questions and legal/terms review; no downloads or ingestion. |

## Routing Options

Phase 109 compares routing options only. It does not approve any action beyond
docs-only follow-up planning.

| route_option | blocker addressed | churn risk | Phase 109 routing note |
| --- | --- | --- | --- |
| Alpha Vantage vendor support questions | Could clarify ETF coverage, adjusted data formulas, listing/status, revisions, terms, storage, and commercial use. | High unless the project specifically wants to keep Alpha Vantage alive. | Lower priority than Polygon/Massive because the technical surface is less complete for ETF lifecycle and flat-file style review. |
| Stooq vendor support questions | Could clarify terms, storage, automation, third-party provider restrictions, adjustment defaults, ETF distributions, archive immutability, inactive coverage, and symbol continuity. | High because terms readability and support path remain uncertain. | Useful only if the project wants to preserve Stooq as an operationally attractive manual/bulk source candidate. |
| Polygon/Massive vendor support questions | Could clarify ETF coverage, aggregate adjustment, dividend and distribution handling, ticker-event completeness, delisted ETF coverage, PIT/vintage behavior, flat-file retention, and finalization/correction policy. | Moderate if questions are drafted without legal workflow facts. | Best near-term candidate for targeted support questions because the documented technical surface is richest, while still non-approved. |
| Legal or terms review | Directly addresses storage, redistribution, commercial/internal use, private/public Git storage, derived metadata, manifests, checksums, exchange pass-through, and vendor pass-through blockers. | Moderate unless the intended workflow is described precisely. | Most useful paired with Polygon/Massive because terms language and plan/flat-file surfaces are concrete enough to review. |
| Review Nasdaq Data Link | Could find a candidate with clearer licensing, historical ETF coverage, survivorship, PIT/vintage, and redistribution documentation. | Moderate if it repeats broad scout discovery without primary-source normalization. | Reasonable next external source review if vendor/legal outreach is not desired for Polygon/Massive. |
| Pause ETF source work | Avoids repeated documentation churn while all candidates remain unresolved. | Low operational risk, but leaves source decisions open. | Acceptable if the project is not ready for vendor/legal outreach or another primary-source review. |
| Return to synthetic implementation only if source decisions are no longer blocking | Could advance source-independent deterministic contracts or fake-only mechanics. | High if it implicitly assumes future real data/source decisions. | Only safe if explicitly scoped to synthetic, source-free work that does not depend on approving any candidate. Not an immediate source-review approval path. |

## Recommended Routing Decision

Recommended decision:

- keep Alpha Vantage unresolved and paused unless the user wants vendor support
  questions for that source specifically
- keep Stooq unresolved and paused unless the user wants vendor support or
  terms review for that source specifically
- treat Polygon/Massive as the best candidate for targeted support/legal
  questions because it has the richest technical surface among the three
  reviewed candidates
- keep Polygon/Massive non-approved until support/legal answers resolve the
  controlling gaps
- use Nasdaq Data Link as a reasonable next external primary-source review if
  vendor/legal outreach is not desired
- avoid implementation, ingestion, downloads, fixtures, real data, API calls,
  or local snapshots

Smallest safe next step: draft Polygon/Massive support questions and/or route
the intended workflow facts to legal/terms review, with no code, data, API
calls, downloads, fixtures, or source approval.

## Allowed Next Steps

Allowed next steps after Phase 109:

- Polygon/Massive support-question drafting
- legal or terms review for Polygon/Massive
- external Nasdaq Data Link primary-source review
- no downloads
- no ingestion
- no implementation
- no data fixtures

Support questions and legal-review notes should remain outside production code
and outside normal pytest. They should not include credentials or trigger
network calls from repo code.

## Relationship To Prior Phases

Phase 93 defined the broad ETF source evidence intake plan. Phase 109 keeps
source comparison inside that framework and records routing only.

Phase 94 normalized broad ETF source evidence as advisory intake material.
Phase 109 continues the separation between external source leads and source
approval.

Phase 95 normalized primary-source verification output for Alpha Vantage,
Stooq, and FRED. Phase 109 does not change those non-approval dispositions.

Phase 104 normalized Alpha Vantage primary-source verification. Phase 105
normalized Alpha Vantage public-doc gap review. Phase 109 keeps Alpha Vantage
unresolved and non-approved.

Phase 106 normalized Stooq public-doc gap review. Phase 109 keeps Stooq
unresolved and non-approved.

Phase 107 recorded ETF source-review routing after Alpha Vantage, Stooq, and
Antigravity review. Phase 109 continues that routing work after the
Polygon/Massive pass.

Phase 108 normalized Polygon/Massive public-doc gap review. Phase 109 compares
that richer but still unresolved candidate against Alpha Vantage and Stooq.

## Explicit Non-Claims

Phase 109 is:

- not Alpha Vantage approval
- not Stooq approval
- not Polygon approval
- not Massive approval
- not source approval
- not data approval
- not endpoint approval
- not download-path approval
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

It adds no Alpha Vantage approval, Stooq approval, Polygon approval, Massive
approval, source approval, data approval, endpoint approval, download-path
approval, flat-file approval, vendor approval, universe approval, benchmark
approval, cash proxy approval, methodology approval, parameter approval,
evidence approval, return-construction approval, no-lookahead approval,
cost/friction approval, liquidity approval, strategy validation, real data
ingestion, raw external data, local data file, API call, flat-file download,
credential, ETF ticker selection, benchmark comparison, ranking, scoring,
source-use recommendation, candidate-discovery behavior in code, replay
metric, manifest-to-planning bridge, signal/evaluator behavior, broker/order/
fill/portfolio/runtime behavior, LLM call, network call, market-data call,
dashboard/advisory/AI integration, paper behavior, live behavior, or trading
behavior.

## Decision

Decision: ETF source-candidate comparison checkpoint only.

Alpha Vantage, Stooq, and Polygon/Massive all remain unresolved and
non-approved. Polygon/Massive has the richest technical surface among the
reviewed candidates and is the smallest useful support/legal outreach target,
but it is still blocked by point-in-time/vintage, legal/storage,
redistribution, ETF lifecycle, survivorship, and return-basis gaps.

No source or data was approved. No production code or tests changed. No real
data was added. No API calls or downloads occurred. Normal pytest remains
offline and credential-free.

## Remaining Blockers

- no approved Alpha Vantage use
- no approved Stooq use
- no approved Polygon use
- no approved Massive use
- no approved source
- no approved data
- no approved endpoint
- no approved download path
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
- no approved survivorship policy
- no approved delisted or inactive ETF policy
- no approved ETF lifecycle policy
- no approved ETF distribution treatment
- no approved adjustment methodology
- no approved revision or correction policy
- no approved archive immutability policy
- no approved point-in-time source policy
- no approved local snapshot
- no approved raw-row storage policy
- no approved private-repo storage policy
- no approved public-repo storage policy
- no approved derived metadata, manifest, or checksum policy
- no approved redistribution policy
- no approved commercial/internal research policy
- no approved exchange or vendor pass-through policy
- no approved API-key or credential workflow
- no approved normal-pytest source dependency
- no strategy-validation claim
- no trading-readiness claim

## Follow-Up Recommendation

The next useful step is Polygon/Massive support-question drafting and/or
Polygon/Massive legal/terms review. If vendor/legal outreach is not desired,
the next source-review path should be external Nasdaq Data Link primary-source
review under the same docs-only, non-approving rules.
