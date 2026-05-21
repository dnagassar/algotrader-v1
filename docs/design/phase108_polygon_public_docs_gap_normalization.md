# Phase 108 - Polygon Public Docs Gap Normalization

## Purpose

This document normalizes externally provided Polygon/Massive public-doc and
public-source verification output into the deterministic repo documentation
trail as advisory verification material only.

Phase 108 does not independently reopen Polygon or Massive pages, browse, call
APIs, download flat files, inspect raw observations, create local data files,
add screenshots, add API keys, add fixtures, add tests, add dependencies, or
change production behavior. It only records public-doc findings and unresolved
gaps from the external advisory pass.

The Polygon/Massive output remains external advisory input. It is not legal
review, source approval, data approval, endpoint approval, flat-file approval,
universe approval, return-construction approval, point-in-time proof, strategy
validation, or trading readiness.

## Normalization Boundary

Phase 108 may normalize Polygon/Massive public-doc findings only.

It must not approve:

- Polygon
- Massive
- any source
- any data
- any endpoint
- any flat-file path
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

Reported public documentation, API endpoint existence, flat-file surfaces,
reference-data surfaces, plan or pricing pages, adjustment language, or terms
language are documentation leads only. They do not approve Polygon/Massive
source use, API use, flat-file use, downloads, local storage, repo storage,
fixtures, ingestion, return construction, point-in-time treatment,
no-lookahead treatment, strategy validation, or trading use.

## Allowed Classification Vocabulary

Allowed `risk_level` values in this document are:

- `low_documented`
- `partially_documented`
- `unclear`
- `high_unresolved`

Allowed `allowed_next_step` values in this document are:

- `needs_repo_normalization`
- `needs_more_primary_docs`
- `needs_terms_review`
- `needs_support_question`
- `reject_for_now`

Forbidden `allowed_next_step` values are:

- `approved`
- `validated`
- `source_approved`
- `data_approved`
- `endpoint_approved`
- `flat_file_approved`
- `point_in_time_safe`
- `strategy_ready`
- `trading_ready`

The allowed values route later review only. They do not authorize
Polygon/Massive API calls, flat-file downloads, local snapshots, fixture use,
raw-row storage, source use, universe membership, benchmark use, cash proxy
use, return construction, no-lookahead claims, scoring, ranking,
recommendation, strategy validation, or trading behavior.

## Normalized Public-Docs Gap Table

The table records public-doc findings as advisory gap-normalization context
only. Findings are normalized into repo language; they are not independently
proven by this phase.

| normalized_id | question_area | public_doc_status | documented_answer_summary | unresolved_gap | support_question_needed | risk_level | allowed_next_step | non_claims |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phase108_polygon_aggregates | Aggregates | Public docs reportedly document aggregates endpoints. | Aggregates appear to provide OHLCV-style bars over requested ranges and resolutions. | Endpoint existence does not resolve ETF coverage guarantees, adjustment semantics, finalization timing, corrections, historical depth, rights, storage, or point-in-time safety. | Ask Polygon/Massive to confirm ETF aggregate coverage, adjustment defaults, correction policy, finalization timing, and permitted local archival for the intended workflow. | `partially_documented` | `needs_support_question` | Not endpoint approval; not source approval; not data approval; not return-construction approval. |
| phase108_polygon_grouped_daily_aggregates | Grouped daily aggregates | Public docs reportedly document grouped daily aggregates. | Grouped daily aggregates appear to expose a market-wide daily bar surface. | Grouped daily availability does not prove complete ETF universe membership, inactive ETF inclusion, point-in-time membership, revision behavior, or redistribution rights. | Ask whether grouped daily outputs include active and inactive ETFs as of each date and how corrections or late listings are handled. | `partially_documented` | `needs_support_question` | Not universe approval; not endpoint approval; not survivorship approval. |
| phase108_polygon_trades | Trades | Public docs reportedly document trades endpoints. | Trade-level data appears available as a richer market-data surface. | Trade data is not needed for current local snapshot approval and does not resolve ETF adjusted-history, distribution, PIT, legal, or storage blockers. | Ask only if a later explicitly scoped workflow needs trade data; otherwise avoid creating a new documentation branch. | `partially_documented` | `needs_more_primary_docs` | Not tick-data approval; not implementation approval; not strategy validation. |
| phase108_polygon_quotes | Quotes | Public docs reportedly document quotes endpoints. | Quote-level data appears available as a richer market-data surface. | Quote data does not resolve historical ETF total-return construction, adjusted-bar meaning, PIT universe membership, survivorship, legal, or storage blockers. | Ask only if a later explicitly scoped workflow needs quote data; otherwise avoid widening the current ETF price-source review. | `partially_documented` | `needs_more_primary_docs` | Not quote-data approval; not liquidity approval; not cost/friction approval. |
| phase108_polygon_splits | Splits | Public docs reportedly document splits. | Split event data appears available. | Split-event existence does not prove split adjustment formulas, timing, finalization, correction policy, ETF lifecycle completeness, or all corporate/fund-action treatment. | Ask how splits are reflected in aggregate bars and whether split events are point-in-time, corrected, archived, and complete for ETFs. | `partially_documented` | `needs_support_question` | Not adjustment-methodology approval; not point-in-time proof. |
| phase108_polygon_dividends | Dividends | Public docs reportedly document dividends. | Dividend event data appears available. | Dividend events do not approve dividend-adjusted bars, total-return construction, ETF distribution taxonomy, return of capital, capital gains distributions, timing, or correction policy. | Ask which ETF distribution types are represented, how ex-dates and payment dates are handled, and whether aggregate bars include or exclude dividend adjustments. | `partially_documented` | `needs_support_question` | Not dividend-adjusted approval; not total-return approval; not ETF distribution approval. |
| phase108_polygon_reference_tickers | Reference tickers | Public docs reportedly document reference ticker data. | Reference tickers appear to provide metadata about listed instruments. | Reference metadata does not prove explicit ETF coverage guarantees, delisted ETF coverage, historical membership, old symbols, closures, mergers, liquidations, or point-in-time universe reconstruction. | Ask whether reference tickers can reconstruct ETF membership as of past dates and how inactive, renamed, merged, closed, or liquidated funds are represented. | `partially_documented` | `needs_support_question` | Not universe approval; not ETF ticker selection; not survivorship approval. |
| phase108_polygon_ticker_events | Ticker events | Public docs reportedly document ticker events. | Ticker events appear to provide history around ticker changes or related lifecycle events. | Event availability does not prove complete lifecycle coverage, point-in-time completeness, old-symbol continuity, merger/closure/liquidation handling, or delisted ETF retention. | Ask for official coverage guarantees and examples covering ETF changes, closures, mergers, liquidations, and delistings. | `partially_documented` | `needs_support_question` | Not symbol-continuity approval; not lifecycle approval; not universe approval. |
| phase108_polygon_flat_files | Flat files | Public docs reportedly document flat files. | Flat files appear to provide bulk-style access that may be operationally attractive for later snapshot review. | Flat-file availability does not resolve rights, retention, local archival, private or public Git storage, redistribution, prior vintages, checksums, corrections, or normal-pytest eligibility. | Ask whether flat files may be downloaded, retained, checksummed, archived locally, stored privately, stored publicly, or used to create metadata-only manifests. | `partially_documented` | `needs_terms_review` | Not flat-file approval; not download approval; not local snapshot approval. |
| phase108_polygon_api_key | API-key requirement | Public docs reportedly require an API key for API access. | API access appears account or key gated. | API-key existence does not approve credentials in repo code, normal pytest, CI, fixtures, docs examples, or local automation. | Ask what plan, entitlement, and key-handling rules apply to private research and whether any access path can remain outside normal pytest. | `partially_documented` | `needs_terms_review` | Not credential approval; not API-call approval; not normal-pytest dependency. |
| phase108_polygon_plan_pricing | Plan and pricing structure | Public docs reportedly describe plan or pricing tiers. | Pricing and entitlement tiers appear relevant to endpoint, history, and flat-file access. | Public plan pages do not settle intended-use rights, commercial/internal use, exchange pass-through obligations, retention, redistribution, or historical entitlement stability. | Ask which plan is required for the exact ETF historical snapshot, flat-file, retention, and private research workflow. | `partially_documented` | `needs_terms_review` | Not entitlement approval; not paid-source approval; not source recommendation. |
| phase108_polygon_split_adjusted_aggregates | Split-adjusted aggregates | Public docs reportedly describe split-adjusted aggregate behavior. | Aggregate bars may support split adjustment. | Split adjustment is narrower than dividend adjustment or total-return construction and does not settle ETF distributions, cash distributions, revisions, or point-in-time methodology. | Ask for exact split-adjustment methodology, default state, opt-out behavior, correction timing, and ETF-specific treatment. | `partially_documented` | `needs_support_question` | Not return-construction approval; not total-return approval; not methodology approval. |
| phase108_polygon_market_data_terms | Market Data Terms non-redistribution language | Public Market Data Terms reportedly include non-redistribution language. | Non-redistribution language is a controlling terms lead for any local snapshot, repo storage, sharing, or publication discussion. | Personal versus commercial use, long-term local archival, private Git storage, public Git storage, derived metadata, manifests, checksums, redistribution, and exchange/vendor pass-through obligations remain unresolved. | Route intended workflow facts to legal review and ask Polygon/Massive which storage, derived artifact, and sharing behaviors are allowed. | `high_unresolved` | `needs_terms_review` | Not legal approval; not storage approval; not redistribution approval. |
| phase108_polygon_candidate_disposition | Candidate disposition | Public docs appear richer than prior free/public candidates but do not close controlling gaps. | Polygon/Massive has documented market-data, reference-data, corporate-action, flat-file, key, pricing, and terms surfaces. | PIT/vintage, legal/storage, ETF lifecycle, survivorship, redistribution, and exact return-construction gaps remain unresolved. | Continue only through terms review, legal review, support questions, or additional official-doc review before any future local snapshot discussion. | `high_unresolved` | `needs_terms_review` | Not Polygon approval; not Massive approval; not ingestion recommendation; not trading readiness. |

## Questions Answered By Public Docs

As advisory external findings only, Phase 108 records that Polygon/Massive
public docs reportedly answer or partially answer these questions:

- aggregates are documented
- grouped daily aggregates are documented
- trades are documented
- quotes are documented
- splits are documented
- dividends are documented
- reference tickers are documented
- ticker events are documented
- flat files are documented
- API access requires an API key
- plan and pricing structure exists
- aggregate bars may support split adjustment
- Market Data Terms reportedly include non-redistribution language

These findings are documentation leads only. They do not approve
Polygon/Massive, any endpoint, any flat-file path, any source, any data, any
local storage, any repo storage, any local snapshot, any return construction,
any universe, any benchmark, any cash proxy, any strategy validation, or any
trading use.

## Unresolved License And Storage Questions

Phase 108 records these unresolved license and storage questions:

- personal use versus commercial use
- internal research use
- long-term local archival
- raw row storage
- private Git storage
- public Git storage
- redistribution or sharing of raw rows
- publication of examples derived from raw rows
- derived metadata, manifests, and checksums
- exchange pass-through obligations
- vendor pass-through obligations
- attribution requirements
- entitlement limits by plan
- API-key handling and credential restrictions
- legal review needs

These questions are controlling blockers. No Polygon/Massive endpoint, flat
file, raw-row storage, fixture creation, local snapshot, private repo storage,
public repo storage, publication, redistribution, API automation, flat-file
download, or normal-pytest dependency is approved by this phase.

## Unresolved ETF And Source-Quality Questions

Phase 108 records these unresolved ETF and source-quality questions:

- explicit ETF coverage guarantees
- ETF historical depth
- delisted ETF coverage
- inactive ETF retention
- fund closures
- fund mergers
- fund liquidations
- ticker-event completeness
- old-symbol retention
- point-in-time ETF universe membership
- reference metadata completeness by historical date
- lifecycle event completeness
- source-quality guarantees by plan or product surface

Documented reference-data and event surfaces are useful leads, but they are
not enough for ETF universe approval, survivorship-safe price history, ETF
ticker selection, benchmark selection, cash proxy selection, strategy
validation, or trading use.

## Unresolved Adjustment And Point-In-Time Questions

Phase 108 records these unresolved adjustment and point-in-time questions:

- split-only adjustment versus broader adjustment
- no dividend-adjusted price approval
- no total-return approval
- ETF distribution handling
- return of capital treatment
- capital gains distribution treatment
- special distribution treatment
- revision and correction policy
- prior vintages or as-of snapshots
- finalization timestamps
- missing bars
- stale bars
- trading-calendar behavior
- holiday behavior
- half-day behavior
- timezone and timestamp semantics
- late corrections and backfills

Split-adjusted aggregate language does not approve return construction,
dividend-adjusted interpretation, total-return interpretation, ETF
distribution treatment, vintage handling, no-lookahead modeling, or strategy
validation.

## Candidate Disposition

Polygon/Massive disposition remains unresolved.

It is:

- not approved
- not rejected solely from this pass
- technically richer than Alpha Vantage and Stooq in the public-doc surfaces
  captured by this external pass
- still blocked by point-in-time and vintage gaps
- still blocked by legal, storage, and redistribution gaps
- still blocked by ETF lifecycle, delisted-history, and survivorship gaps
- `needs_terms_review`
- `needs_support_question`
- `needs_more_primary_docs`

Phase 108 does not recommend ingestion, implementation, parser work, API calls,
flat-file downloads, fixtures, real data files, local snapshots, source
approval, data approval, universe construction, return construction, benchmark
construction, cash proxy construction, strategy validation, or trading use.

## Comparison To Alpha Vantage And Stooq

Compared with Alpha Vantage, Polygon/Massive appears to expose more public-doc
surfaces relevant to historical market data, reference data, corporate actions,
ticker events, and flat files. That richer documentation does not resolve the
same controlling blockers around terms, storage, ETF lifecycle, adjustment,
point-in-time behavior, survivorship, and strategy use.

Compared with Stooq, Polygon/Massive appears less oriented around anonymous
manual CSV convenience and more oriented around account-gated APIs, pricing
tiers, reference-data surfaces, events, and flat files. That operational shape
may be easier to interrogate through support and legal review, but it also
introduces plan entitlement, API-key, exchange pass-through, and
non-redistribution questions.

All three candidates remain unresolved and non-approved. No relative
technical richness, operational convenience, documentation breadth, pricing
page, endpoint page, or flat-file page approves a source, endpoint, data set,
download path, universe, return basis, strategy validation, or trading use.

## Allowed Next Steps

Allowed next steps after Phase 108:

- Polygon/Massive terms review
- Polygon/Massive support questions
- legal review
- additional official-doc review
- no downloads
- no ingestion
- no repo fixtures or data
- no implementation

Support questions should be drafted outside production code and outside normal
pytest. They should not include credentials or trigger network calls from repo
code.

## Relationship To Prior Phases

Phase 93 defined the broad ETF source evidence intake plan. Phase 108 remains
inside that framework and records external Polygon/Massive public-doc review
as advisory material only.

Phase 94 normalized earlier source-discovery output as advisory intake
material. Phase 108 continues the separation between documentation leads and
approval.

Phase 95 normalized primary-source verification output for Alpha Vantage,
Stooq, and FRED. Phase 108 adds only another candidate-source public-doc gap
normalization and does not alter those dispositions.

Phase 104 and Phase 105 normalized Alpha Vantage primary-source and public-doc
gap review output. Phase 106 normalized Stooq public-doc gap review output.
Phase 107 routed unresolved Alpha Vantage and Stooq work toward another
candidate source or legal/vendor review. Phase 108 follows that route by
normalizing Polygon/Massive public-doc findings without approval.

Phases 96 through 103 captured FRED and H.15 benchmark, cash, rate,
discount-basis, averaging, and point-in-time complexity. Polygon/Massive
public-doc normalization does not reopen FRED or approve any benchmark or cash
proxy.

Across these phases:

- public endpoint availability does not approve source use
- flat-file availability does not approve data use
- reference-data availability does not solve ETF universe or survivorship
- split-adjusted aggregate language does not solve total-return construction
- terms and storage remain unresolved
- Polygon/Massive data must not enter normal pytest through files, API calls,
  flat files, fixtures, or downloads

Normal `python -m pytest` must remain offline, credential-free, source-free,
vendor-free, and independent from Polygon/Massive.

## Explicit Non-Claims

Phase 108 is:

- not Polygon approval
- not Massive approval
- not source approval
- not data approval
- not endpoint approval
- not flat-file approval
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

It adds no Polygon approval, Massive approval, source approval, data approval,
endpoint approval, flat-file approval, download-path approval, vendor
approval, universe approval, benchmark approval, cash proxy approval,
methodology approval, parameter approval, evidence approval,
return-construction approval, no-lookahead approval, cost/friction approval,
liquidity approval, strategy validation, real data ingestion, raw external
data, local data file, Polygon API call, Massive API call, flat-file download,
credential, ETF ticker selection, benchmark comparison, ranking, scoring,
recommendation, candidate-discovery behavior in code, replay metric,
manifest-to-planning bridge, signal/evaluator behavior, broker/order/fill/
portfolio/runtime behavior, LLM call, network call, market-data call,
dashboard/advisory/AI integration, paper behavior, live behavior, or trading
behavior.

## Decision

Decision: advisory Polygon/Massive public-doc gap normalization only.

Polygon/Massive remains unresolved. It is not approved and not rejected solely
from this pass. It is technically richer than Alpha Vantage and Stooq in the
captured public-doc surfaces, but still blocked by point-in-time/vintage,
legal/storage, ETF lifecycle, and survivorship gaps.

No Polygon/Massive source use, endpoint use, flat-file use, data use, local
storage, local snapshot, repo storage, fixture, ingestion, universe
construction, return construction, no-lookahead claim, strategy validation, or
trading use is approved.

No production code or tests changed. No real data was added. No Polygon or
Massive API calls occurred. No downloads occurred. Normal pytest remains
offline and credential-free.

## Remaining Blockers

- no approved Polygon use
- no approved Massive use
- no approved endpoint
- no approved flat-file path
- no approved source
- no approved data
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
- no approved old-symbol retention policy
- no approved ticker-event completeness policy
- no approved fund-closure, merger, or liquidation policy
- no approved point-in-time universe policy
- no approved adjustment methodology
- no approved ETF dividend or distribution treatment
- no approved split-only adjustment interpretation
- no approved dividend-adjusted interpretation
- no approved total-return interpretation
- no approved revision or correction policy
- no approved vintage procedure
- no approved finalization timestamp policy
- no approved timestamp/as-of semantics
- no approved timezone or calendar policy
- no approved holiday or half-day policy
- no approved local snapshot
- no approved raw-row storage policy
- no approved private-repo storage policy
- no approved public-repo storage policy
- no approved derived metadata, manifest, or checksum policy
- no approved redistribution policy
- no approved commercial/internal research policy
- no approved exchange or vendor pass-through policy
- no approved API-key or credential workflow
- no approved normal-pytest Polygon/Massive dependency
- no strategy-validation claim
- no trading-readiness claim

## Follow-Up Recommendation

The next useful step is Polygon/Massive terms and legal review, Polygon/Massive
support questions, or additional official-doc review before any local snapshot
or implementation discussion. If the user wants a different candidate instead,
that work should remain external, primary-source, docs-only, and non-approving.
