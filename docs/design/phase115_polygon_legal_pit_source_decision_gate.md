# Phase 115 - Polygon/Massive Legal/PIT Source Decision Gate

## Purpose

This document records a narrow docs-only decision gate for Polygon/Massive
after candidate schema/interface planning and one tiny synthetic reference
ticker fixture.

Phase 115 decides routing only. It determines whether further
Polygon/Massive candidate-only schema/interface work can continue safely, or
whether unresolved legal, storage, point-in-time, and source-quality blockers
should pause additional synthetic artifacts before they create false
confidence.

This phase does not browse, reopen provider pages, call APIs, download data,
inspect raw observations, add fixtures, implement parsers, add production
schemas, change tests, change production behavior, start ingestion, create
local snapshots, or approve Polygon/Massive.

## Decision Gate Boundary

Phase 115 may decide routing only.

It must not approve:

- Polygon
- Massive
- any endpoint
- any flat file
- any source
- any data
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

Any route named by this gate is a documentation route only. It does not
authorize API calls, downloads, local snapshots, raw-row storage, repository
storage, source use, endpoint use, flat-file use, universe construction,
benchmark construction, cash proxy construction, return construction,
corporate-action math, no-lookahead claims, scoring, ranking, strategy
validation, or trading behavior.

Schema existence must not imply source approval. Synthetic fixture existence
must not imply endpoint approval, data approval, source-quality approval,
return-basis approval, point-in-time approval, or legal approval.

## Current Polygon/Massive Evidence

Current advisory evidence from prior phases:

- Polygon/Massive is the strongest technical ETF price-source candidate
  reviewed so far.
- Its public documentation record is richer than the Alpha Vantage and Stooq
  records reviewed so far.
- Phase 108 recorded public-doc leads for aggregates, grouped daily
  aggregates, trades, quotes, splits, dividends, reference tickers, ticker
  events, flat files, API-key requirements, plan/pricing structure,
  split-adjusted aggregates, and Market Data Terms non-redistribution
  language.
- Phase 110 recorded deeper public-doc leads around Market Data Terms,
  individual-use terms, redistribution limits, flat-file research/backtesting
  workflow docs, unadjusted flat files, REST adjusted aggregates, reference
  tickers, active as-of and delisted ticker lookup leads, ticker events, ETF
  profile surfaces, and corporate actions.
- Phase 112 defined candidate-only schema/interface planning surfaces and
  metadata questions. It did not implement schemas, production contracts,
  clients, parsers, ingestion, or local snapshots.
- Phase 113 added one tiny synthetic-only Polygon/Massive-style reference
  ticker metadata fixture. The fixture is safe because it uses primitive
  placeholder values only, no real vendor data, no market-data rows, no API
  calls or downloads, no credentials, no `.data/` paths, no vendor/runtime
  imports, and byte-stable JSON.
- Phase 114 inspected the fixture and concluded it is useful but narrow. More
  synthetic Polygon/Massive fixtures are not useful enough yet when they touch
  aggregates, splits, dividends, flat files, prices, corporate actions,
  return construction, adjustment, or point-in-time semantics.

Current limitations:

- No real Polygon/Massive data exists in the repository.
- No production Polygon/Massive schema exists.
- No production Polygon/Massive contract, client, parser, ingestion path, or
  local snapshot workflow exists.
- No legal approval exists.
- No source approval exists.
- No data approval exists.
- No endpoint approval exists.
- No flat-file approval exists.
- No point-in-time or vintage approval exists.

## Legal And Storage Blockers

The following legal and storage blockers remain unresolved before any real
Polygon/Massive data use, local snapshot workflow, raw-row storage, or
production integration:

- Personal versus business/commercial use remains unresolved for the intended
  workflow.
- Local storage and archival rights remain unresolved.
- Post-termination deletion obligations remain unresolved.
- Private Git storage of vendor-derived files, examples, schemas, manifests,
  or metadata remains unresolved.
- Public sample or raw-row sharing remains unresolved and may be restricted.
- Redistribution restrictions remain unresolved.
- Derived metadata, manifests, checksums, reports, signals, transformed rows,
  and related artifacts have unresolved status.
- Exchange and vendor pass-through terms remain unresolved.
- Plan, product, entitlement, and use-case limits remain unresolved.
- Legal review is still required before any real Polygon/Massive source,
  endpoint, flat-file, data, storage, archival, derived-artifact, sharing, or
  redistribution use.

These blockers are controlling blockers. Technical documentation richness does
not resolve them.

## PIT And Source-Quality Blockers

The following point-in-time and source-quality blockers remain unresolved
before any price, corporate-action, return, universe, benchmark, cash-proxy,
or local snapshot use:

- Full point-in-time or vintage support is not confirmed.
- As-of history for aggregates is not confirmed.
- As-of history for corporate actions is not confirmed.
- As-of history for reference surfaces is not confirmed.
- Revision, correction, finalization, and last-updated metadata remain
  unresolved.
- ETF lifecycle completeness remains unresolved.
- Delisted ETF retention remains unresolved.
- Ticker-event completeness remains unresolved.
- Symbol continuity across fund events, ticker changes, mergers,
  liquidations, closures, and delistings remains unresolved.
- ETF distribution taxonomy remains unresolved.
- Adjusted aggregates split-only behavior versus broader adjustment behavior
  remains unresolved where relevant.
- No dividend-adjusted or total-return series approval exists.
- Timestamp, timezone, market-calendar, holiday, half-day, halt, missing-bar,
  and stale-bar behavior remain unresolved.
- Flat-file revision or replacement behavior remains unresolved.
- Endpoint and flat-file consistency remain unresolved.
- ETF profile/history point-in-time behavior remains unresolved.

These blockers mean that synthetic examples for aggregates, splits, dividends,
or flat files would risk encoding unresolved semantics before the project has a
source-quality decision.

## Decision Rules

Use the following conservative routing rules after Phase 115:

- Further synthetic Polygon/Massive schema fixtures may proceed only if they
  are metadata-only or pure schema-shape-only and do not touch prices,
  returns, corporate-action math, adjustment math, flat-file ingestion, or
  endpoint clients.
- Price and corporate-action fixtures such as aggregates, grouped aggregates,
  splits, dividends, distribution rows, or flat files should pause until this
  decision gate is cleared or a concrete safety reason exists in a separately
  scoped phase.
- No production contracts, production schemas, endpoint clients, parsers,
  ingestion paths, local snapshots, storage workflows, or manifest-to-data
  bridges may be added until legal, storage, point-in-time, and source-quality
  blockers are separately addressed.
- Schema existence must not imply source approval.
- Fixture existence must not imply data approval.
- Endpoint documentation must not imply endpoint approval.
- Flat-file documentation must not imply download, archival, or storage
  approval.
- Reference-shape metadata must not imply ETF universe, survivorship, or
  lifecycle approval.
- Corporate-action field names must not imply corporate-action methodology,
  total-return, adjustment, or return-construction approval.
- Normal pytest must remain offline, credential-free, source-free,
  vendor-free, and independent from real data.

## Recommended Decision

Recommended decision:

- Pause additional Polygon/Massive synthetic fixtures that involve price,
  corporate-action, adjustment, flat-file, or return semantics.
- Allow only metadata/reference-shape work if a concrete consumer emerges.
- Do not implement ingestion.
- Do not call APIs.
- Do not download data.
- Do not approve Polygon/Massive.
- If continuing source work, route to terms/legal review or another
  public-source candidate review.
- If continuing implementation work, keep it synthetic and source-agnostic.

The tiny Phase 113 reference ticker fixture remains acceptable because it is
primitive, synthetic, metadata-only, source-free, data-free, network-free,
credential-free, and does not encode prices, returns, adjustment math, or
corporate-action semantics.

## Allowed Next Steps

Allowed next steps after Phase 115:

- legal review outside the repository
- terms review outside the repository
- deeper public-doc review only for a concrete missing official page
- another source candidate review, such as Nasdaq Data Link, under the Phase
  93 evidence intake discipline
- source-agnostic synthetic contracts unrelated to real vendor data
- tiny metadata-only reference-shape fixture work only if there is a real
  consumer and the phase explicitly preserves all non-claims

Forbidden next steps after Phase 115:

- API calls
- downloads
- real data
- ingestion
- production clients
- parser implementation
- local snapshots
- raw-row storage
- endpoint approval
- flat-file approval
- source approval
- data approval
- price fixture expansion without a separate gate
- corporate-action fixture expansion without a separate gate
- return-semantics fixture expansion without a separate gate
- universe approval
- benchmark approval
- cash proxy approval
- strategy validation
- trading behavior

## Relationship To Prior Phases

Phase 108 normalized the initial Polygon/Massive public-doc gap review. Phase
115 preserves its unresolved license, storage, ETF/source-quality,
adjustment, and point-in-time caveats.

Phase 110 normalized deeper Polygon/Massive public-doc findings. Phase 115
uses that stronger technical record as evidence that Polygon/Massive is the
strongest technical candidate reviewed so far, but it does not convert that
record into legal, source, data, endpoint, flat-file, point-in-time, or
return-construction approval.

Phase 111 routed the project toward candidate-only Polygon/Massive
schema/interface planning only if it remained metadata-only and synthetic-only.
Phase 115 tightens that route by pausing price, corporate-action, flat-file,
and return-semantics fixtures until legal/storage/PIT/source-quality blockers
are addressed or a separate concrete safety reason exists.

Phase 112 defined the candidate schema/interface planning boundary. Phase 115
keeps the Phase 112 surfaces candidate-only and confirms that field/category
planning does not authorize production contracts, parsers, ingestion, local
snapshots, or real data.

Phase 113 added one tiny synthetic-only reference ticker fixture. Phase 115
keeps that fixture acceptable as a narrow metadata/reference-shape proof while
rejecting any inference that more price or corporate-action fixtures are safe
by default.

Phase 114 inspected the Phase 113 fixture and made no file changes. Phase 115
records the Phase 114 usefulness conclusion as the routing decision gate:
reference-shape metadata may be useful when there is a concrete consumer, but
aggregates, splits, dividends, and flat files should pause because they would
approach unresolved price, adjustment, point-in-time, return-construction, and
corporate-action semantics.

Across these phases:

- richer public docs do not approve source use
- schema/interface planning does not approve Polygon/Massive
- synthetic fixtures do not approve endpoint or data use
- reference metadata does not solve ETF universe or survivorship
- adjusted aggregate language does not solve dividend-adjusted or total-return
  construction
- flat-file documentation does not approve downloads, archival, local
  snapshots, or repo storage
- legal review remains required before real Polygon/Massive data use
- normal pytest must remain offline, credential-free, source-free,
  vendor-free, and independent from real data

## Explicit Non-Claims

Phase 115 is:

- not Polygon approval
- not Massive approval
- not endpoint approval
- not flat-file approval
- not source approval
- not data approval
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

It adds no Polygon approval, Massive approval, source approval, data approval,
endpoint approval, flat-file approval, vendor approval, universe approval,
benchmark approval, cash proxy approval, methodology approval, parameter
approval, evidence approval, return-construction approval, no-lookahead
approval, cost/friction approval, liquidity approval, strategy validation,
production schema, production dataclass, parser, endpoint client, API call,
download, credential, real data, data file, fixture, local snapshot workflow,
ingestion, persistence, ETF ticker selection, benchmark comparison, ranking,
scoring, recommendation, replay metric, manifest-to-planning bridge,
signal/evaluator behavior, broker/order/fill/portfolio/runtime behavior, LLM
call, network call, market-data call, paper behavior, live behavior, or
trading behavior.

## Decision

Decision: Polygon/Massive legal/PIT source decision gate only.

Pause additional Polygon/Massive synthetic fixtures involving prices,
corporate actions, adjustment, flat files, or return semantics. Allow only
metadata/reference-shape work if a concrete consumer emerges and the work
remains synthetic, source-free, data-free, endpoint-free, network-free,
credential-free, and non-approving.

All sources remain unresolved. No source or data was approved. No production
code or tests changed. No fixtures changed. No real data was added. No API
calls or downloads occurred. Normal pytest remains offline and
credential-free.

## Remaining Blockers

- no approved Polygon use
- no approved Massive use
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
- no approved corporate-action methodology
- no approved total-return or dividend-adjusted policy
- no strategy-validation claim
- no trading-readiness claim

## Follow-Up Recommendation

If source work continues, route to Polygon/Massive terms/legal review or a
different public-source candidate review such as Nasdaq Data Link. If
implementation work continues, keep it synthetic and source-agnostic rather
than expanding Polygon/Massive price, corporate-action, flat-file, or return
fixtures.
