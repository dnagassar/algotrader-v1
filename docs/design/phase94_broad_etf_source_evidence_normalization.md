# Phase 94 - Broad ETF Source Evidence Normalization

## Purpose

This document normalizes externally discovered broad ETF source-discovery
material into the deterministic repo documentation trail as advisory intake
material only.

The external scout output is treated as source-discovery input, not verified
source evidence. Some scout citations may be secondary sources, tutorials,
GitHub or Reddit references, general guides, or other community references.
Those materials can route later questions, but they cannot approve source use,
data use, local storage, return construction, no-lookahead safety, strategy
validation, or trading use.

This phase is documentation-only. It does not browse, call APIs, download,
scrape, inspect real data, copy the raw scout report, add source credentials,
add ETF tickers, add notebooks, add screenshots, or add production behavior.

## Normalization Boundary

Phase 94 may normalize external scout findings only.

It must not approve:

- any source
- any data
- any vendor
- any broker feed
- any public download path
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

No candidate becomes selected, preferred, validated, source-approved,
data-approved, point-in-time safe, strategy-ready, trading-ready, or ready for
local snapshot acquisition under this phase.

## Source Path Categories Preserved

Phase 94 preserves the Phase 93 source-path categories:

- manual local snapshot
- vendor-exported local snapshot
- broker-exported local snapshot
- public web/downloaded file
- API-exported local snapshot
- benchmark/rate source for cash proxy only
- issuer/fund metadata source for context only

Rows may reference more than one category when the exact later route is still
unresolved. Multi-category routing is not approval of any route.

## Normalized Status Vocabulary

Allowed `normalized_status` values in this document are:

- `reject_for_now`
- `context_only`
- `candidate_needs_more_evidence`
- `candidate_for_later_primary_review`

Forbidden statuses are:

- `approved`
- `validated`
- `source_approved`
- `data_approved`
- `strategy_ready`
- `trading_ready`

The allowed statuses are routing labels only. They do not authorize source
use, data acquisition, local storage, repo storage, fixture use, ingestion,
return construction, benchmark/cash use, universe membership, replay, scoring,
ranking, recommendation, strategy validation, or trading behavior.

## Scout Evidence Labels

The scout output is advisory input. Phase 94 explicitly separates possible
evidence types as follows:

| Evidence label | Phase 94 treatment |
| --- | --- |
| primary official documentation found | Not verified in this phase. Any scout-reported official documentation must be reopened and cited in a later primary-source verification phase before it can support a stronger claim. |
| primary terms/license found | Not verified in this phase. Any scout-reported terms, license, API terms, exchange terms, redistribution terms, or account terms must be reviewed separately before source or storage decisions. |
| secondary/tutorial source only | Advisory context only. Tutorials, guides, blog posts, examples, and summaries are not sufficient evidence for source approval. |
| community/source-discovery reference only | Advisory context only. GitHub examples, Reddit posts, forum references, and community notes are discovery leads, not evidence approval. |
| unresolved primary-source confirmation needed | Controlling status for all normalized rows in this phase unless a later primary-source verification phase says otherwise. |

No row below treats secondary sources, Reddit, GitHub examples, tutorials, blog
posts, or general guides as sufficient evidence for source approval.

## Normalized Candidate Table

| normalized_id | source_or_vendor_name | source_path_category | scout_status | normalized_status | primary_source_status | likely_use | key_possible_strengths | key_blockers | primary_docs_needed | terms_or_license_needed | point_in_time_questions | survivorship_questions | adjustment_questions | storage_rights_questions | allowed_next_step | non_claims |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phase94_stooq | Stooq | public web/downloaded file; API-exported local snapshot | Externally discovered candidate route; advisory scout input only. | `candidate_for_later_primary_review` | unresolved primary-source confirmation needed | Possible free/manual broad ETF price snapshot route, subject to exact route review. | Low apparent acquisition friction; possible historical price download/export route. | Official docs, terms, adjustment policy, dividend handling, corrections, symbols, storage, and redistribution unresolved. | Official data documentation, field definitions, adjustment notes, download/export mechanics, correction policy. | Terms of use, redistribution restrictions, local archival rights, automated access terms if any. | Are rows timestamped or publication-timed; are corrections visible; what is the as-of meaning of downloaded history? | Does coverage include inactive or delisted ETFs; how are symbol changes and gaps represented? | Are adjusted fields present; how are dividends, splits, distributions, and corporate actions handled? | Can raw rows be stored locally; can checksums/derived summaries be committed; are public-repo rows forbidden? | Primary-source documentation and terms review only; no download. | Not source approval; not data approval; not return-construction approval. |
| phase94_yahoo_manual_csv | Yahoo Finance manual CSV | manual local snapshot; public web/downloaded file | Externally discovered manual CSV route; advisory scout input only. | `candidate_needs_more_evidence` | unresolved primary-source confirmation needed | Possible manual export path for local research only if rights and mechanics later resolve. | Familiar retail interface; manual CSV route may be simple to test after all gates resolve. | Terms, automation status, adjusted-close methodology, download reproducibility, storage rights, and redistribution unresolved. | Official help/docs for historical downloads, field definitions, adjustment notes, correction/revision behavior. | Website terms, download terms, personal-use limits, storage/cache restrictions, redistribution restrictions. | What date/time does a manual export represent; can historical corrections change rows; is export reproducible? | Are delisted/inactive ETFs available; are symbol changes preserved; is coverage survivorship-biased? | How are adjusted close, dividends, distributions, and splits computed or revised? | Can manually exported rows be stored locally; can they be committed; can derived artifacts be shared? | Gather primary Yahoo documentation and terms only; no CSV download. | Not source approval; not data approval; not vendor approval. |
| phase94_yfinance | yfinance package / unofficial Yahoo dependency | API-exported local snapshot | Externally discovered package route; advisory scout input only. | `reject_for_now` | secondary/tutorial or community/source-discovery references only unless later official evidence exists; unresolved primary-source confirmation needed | Context only for why unofficial dependency routes are weak under current constraints. | Convenient Python interface if it were allowed later. | Unofficial dependency on Yahoo-access mechanics, API stability, terms, caching/storage, and reproducibility unresolved. | Official upstream authorization, package docs, dependency behavior docs, adjustment notes, cache semantics. | Package license plus upstream Yahoo terms, automated access terms, local cache/storage restrictions. | Can package outputs be tied to a clear as-of/export time; do endpoints revise without notice? | Does package expose inactive/delisted ETF coverage; how are symbol changes represented? | How does the package source adjusted fields; are dividend/split/corporate-action inputs transparent? | Are downloaded/cache rows locally storable; can raw rows or cache artifacts be committed? | Keep rejected-for-now or context-only unless primary authorization and terms are reviewed; no use. | Not source approval; not API approval; not data approval. |
| phase94_alpha_vantage | Alpha Vantage | API-exported local snapshot | Externally discovered retail API route; advisory scout input only. | `candidate_for_later_primary_review` | unresolved primary-source confirmation needed | Possible retail API candidate for later local snapshot review. | Publicly documented API-style workflow may support explicit export mechanics after review. | API key, rate limits, endpoint fields, adjusted data semantics, ETF coverage, terms, and storage unresolved. | Official API docs, endpoint field docs, adjusted/unadjusted policy, coverage notes, correction policy, rate-limit docs. | API terms, subscription/free-tier terms, local storage rights, redistribution/public-repo restrictions. | What does response time mean; are historical rows revised; are endpoint timestamps and update times documented? | Are inactive/delisted ETFs covered; is ETF coverage complete enough; are symbol changes documented? | Are adjusted outputs available; how are dividends, distributions, splits, and corporate actions handled? | Can raw API rows be stored locally outside normal pytest; can derived summaries be committed? | Primary API docs and terms review only; no API call. | Not source approval; not API approval; not data approval. |
| phase94_alpaca_market_data | Alpaca Market Data | broker-exported local snapshot; API-exported local snapshot | Externally discovered broker/feed route; advisory scout input only. | `candidate_needs_more_evidence` | unresolved primary-source confirmation needed | Possible broker/feed historical export only if entitlement, rights, and offline snapshot rules resolve. | Existing project has deferred Alpaca paper-planning context; broker route may be familiar to owner. | Credentials, account entitlements, subscription tiers, exchange/feed terms, historical depth, storage rights, and normal-pytest isolation unresolved. | Official market data docs, feed coverage docs, historical endpoint docs, adjustment policy, entitlement docs, correction policy. | Broker/account terms, market-data terms, exchange terms, API terms, local storage and redistribution restrictions. | What is the as-of meaning of historical API responses; are corrections/revisions documented? | Does coverage include inactive/delisted ETFs; are symbol changes and asset metadata point-in-time? | Are adjusted bars available; how are corporate actions, distributions, and splits handled? | Can broker/feed data be stored locally; can raw rows be committed; do exchange terms restrict derived outputs? | Provider documentation and terms review only; no credential use or API call. | Not broker-feed approval; not source approval; not trading approval. |
| phase94_polygon | Polygon.io | API-exported local snapshot; vendor-exported local snapshot | Externally discovered professional API route; advisory scout input only. | `candidate_for_later_primary_review` | unresolved primary-source confirmation needed | Possible professional API candidate for later local snapshot review. | API-oriented provider may offer clearer docs, corporate-action metadata, and coverage notes after review. | Cost/access tier, ETF coverage, adjustment policy, corrections, delisted coverage, terms, storage, and redistribution unresolved. | Official API docs, aggregate/price docs, corporate-action docs, ticker/reference docs, update/correction policy, coverage docs. | Subscription terms, API terms, local storage rights, redistribution restrictions, derived-data restrictions. | Are historical rows point-in-time; can corrections change rows; are reference endpoints time-aware? | Are inactive/delisted ETFs available; are ticker events and symbol changes traceable? | How are splits, dividends, distributions, and adjusted fields represented? | Can raw API rows be stored locally; can repo metadata reference them; can derived research artifacts be public? | Primary docs and terms review only; no API call. | Not source approval; not vendor approval; not data approval. |
| phase94_nasdaq_data_link | Nasdaq Data Link | vendor-exported local snapshot; API-exported local snapshot | Externally discovered dataset aggregator route; advisory scout input only. | `candidate_for_later_primary_review` | unresolved primary-source confirmation needed | Possible dataset aggregator route if an exact dataset later satisfies rights and coverage review. | Dataset-specific docs may make exact dataset, fields, and licensing explicit after review. | Exact dataset not chosen; coverage, adjustment, point-in-time semantics, access tier, terms, storage, and redistribution unresolved. | Official platform docs, exact dataset docs, data dictionary, coverage notes, update/revision policy, export mechanics. | Dataset license, platform terms, subscription terms, redistribution and local archival restrictions. | Does the exact dataset support as-of access or only latest history; are revisions documented? | Does selected dataset include inactive/delisted ETFs; does it preserve identifier changes? | Does selected dataset include adjusted prices or corporate-action components; are methods documented? | Can exact dataset rows be stored locally; can raw rows be committed; what public/private repo limits apply? | Identify 1-2 exact datasets and review primary docs/terms only; no export. | Not dataset approval; not source approval; not data approval. |
| phase94_fred_cash_rate | FRED | benchmark/rate source for cash proxy only | Externally discovered cash/rate route; advisory scout input only. | `candidate_for_later_primary_review` | unresolved primary-source confirmation needed | Cash/rate proxy evidence review only; not ETF price data. | Public rate-series documentation may support cash-proxy timing review after primary verification. | Exact series, publication timing, revisions, vintage/as-of support, compounding, storage, and citation unresolved. | Official series docs, API/download docs, release calendar, vintage/revision docs, frequency and unit definitions. | Terms of use, API terms if used, citation requirements, local storage and redistribution restrictions. | What publication date/time is usable; are vintages available; how do revisions affect no-lookahead rules? | Not a survivorship source for ETF universe; only whether selected rate series has continuity and discontinuation issues. | Not an ETF adjustment source; must define rate conversion, compounding, holidays, and missing observations later. | Can raw rate rows be stored locally; can derived cash-return series be committed; are citation requirements satisfied? | Primary FRED docs and terms review for cash/rate only; no series download. | Not benchmark approval; not cash proxy approval; not rate-series approval. |
| phase94_issuer_metadata_pages | ETF issuer/fund metadata pages | issuer/fund metadata source for context only | Externally discovered metadata/context route; advisory scout input only. | `context_only` | unresolved primary-source confirmation needed | Fund identity, objective, expense, distribution, and context review only. | Issuer pages may be authoritative for current fund facts and policy descriptions. | Current pages may not be point-in-time; historical metadata, archive rights, issuer-specific terms, and redistribution unresolved. | Issuer official fund pages, prospectus/SAI links if later needed, distribution docs, historical documents, archive/version notes. | Issuer website terms, document use terms, redistribution and archival restrictions. | Are pages versioned; can historical facts be tied to dates; are document effective dates clear? | Do issuer pages expose inactive funds or only current funds; how are mergers/liquidations represented? | May describe distributions or splits but not necessarily price adjustment methodology. | Can pages/PDFs be stored locally; can excerpts or derived metadata be committed? | Use as context-only primary review later; no universe or data approval. | Not universe approval; not source approval; not data approval. |
| phase94_generic_broker_export | Generic broker historical export | broker-exported local snapshot | Externally discovered generic broker-export route; advisory scout input only. | `candidate_needs_more_evidence` | unresolved primary-source confirmation needed | Possible owner-specific historical export route if account/feed rights later resolve. | May be available from an already used account or platform. | Broker identity, credentials, entitlement, exchange terms, export depth, adjustment policy, offline rights, and reproducibility unresolved. | Exact broker docs, historical export docs, feed coverage docs, adjustment docs, correction policy, account entitlement docs. | Broker terms, market-data terms, exchange terms, local storage, redistribution, and derived-output restrictions. | What is the export timestamp; can history be revised; does export include availability/release timing? | Are inactive/delisted ETFs exportable; are symbol changes and corporate actions visible? | Are adjusted prices available; are dividend/distribution/split inputs and methods documented? | Can raw export rows be stored locally; can they be committed; do account/feed terms forbid repo use? | Identify exact broker/export route and review primary docs/terms only; no export. | Not broker data approval; not source approval; not trading approval. |

## Primary Evidence Versus Scout Observations

Phase 94 records source-discovery categories and routing labels only.

- Scout observations can identify candidate source paths and likely questions.
- Primary official documentation was not verified by this phase.
- Primary terms/license evidence was not verified by this phase.
- Secondary/tutorial materials remain secondary even when they describe real
  provider behavior.
- Community/source-discovery references remain leads only.
- Unresolved primary-source confirmation is a blocker for every candidate.

Any later review must cite primary provider documentation or provider terms
directly, and must keep those citations separate from tutorials, community
posts, package examples, and scout summaries.

## Candidate Disposition Summary

Strongest later-review candidates, not approval:

| Bucket | Candidate | Phase 94 disposition |
| --- | --- | --- |
| Free/manual candidate | Stooq | `candidate_for_later_primary_review`; not approved, not validated, not data-approved, not point-in-time safe, not strategy-ready. |
| Retail API candidate | Alpha Vantage | `candidate_for_later_primary_review`; not approved, not validated, not data-approved, not point-in-time safe, not strategy-ready. |
| Professional API candidate | Polygon.io | `candidate_for_later_primary_review`; not approved, not validated, not data-approved, not point-in-time safe, not strategy-ready. |
| Dataset aggregator candidate | Nasdaq Data Link | `candidate_for_later_primary_review`; not approved, not validated, not data-approved, not point-in-time safe, not strategy-ready. |
| Cash/rate candidate | FRED | `candidate_for_later_primary_review` for cash/rate proxy review only; not benchmark-approved, not cash-proxy-approved, not rate-series-approved, not point-in-time safe, not strategy-ready. |

Weaker, rejected-for-now, or context-only candidates:

| Candidate | Phase 94 disposition | Rationale |
| --- | --- | --- |
| yfinance | `reject_for_now` | Unofficial Yahoo dependency and unresolved authorization, terms, stability, storage, and reproducibility questions make it unsuitable for current source routing. This is not a legal conclusion. |
| ETF issuer websites | `context_only` | Useful for fund context and possible primary metadata review, but not a price source, universe approval, benchmark approval, or point-in-time metadata solution. |
| Yahoo Finance manual CSV | `candidate_needs_more_evidence` | Manual export may be simple, but terms, adjustment methodology, reproducibility, storage rights, and inactive coverage are unresolved. |
| Alpaca Market Data | `candidate_needs_more_evidence` | Broker/feed route depends on account entitlements, market-data terms, credentials, historical depth, storage rights, and strict offline test isolation. |
| Generic broker historical exports | `candidate_needs_more_evidence` | Exact broker, feed, export mechanics, entitlement, terms, adjustment policy, and offline/local storage rights are unknown. |

These dispositions are cautious routing labels only. They do not rank, score,
recommend, select, approve, or reject any provider for trading use.

## Unresolved Primary-Source Questions

At minimum, later primary-source review must answer:

- Can the source be used for personal local research?
- Can raw rows be stored locally outside normal pytest?
- Are raw rows forbidden from public or private repo commits?
- What redistribution, derived-output, citation, or publication restrictions
  apply?
- What adjustment methodology is used for adjusted price fields?
- How are dividends and distributions represented and revised?
- How are splits and other corporate actions represented and revised?
- What is the revision or correction policy for historical rows?
- What are the timestamp, export-time, publication-time, and as-of semantics?
- Are inactive, delisted, merged, renamed, or liquidated ETFs covered?
- What survivorship risk remains even if current symbols are covered?
- Does the source support benchmark, cash, or rate needs, and under what
  timing rules?
- Does access require an API key, broker credential, account entitlement,
  subscription, exchange permission, or manual login?
- What network, rate-limit, quota, or access-tier limits affect
  reproducibility?
- Can normal `python -m pytest` remain offline, credential-free, and
  independent from the source?
- Can a deterministic local snapshot be created later without adding real data
  to normal pytest?
- Does the source provide enough documentation to separate price return,
  total return, distribution return, split adjustment, and cash/rate treatment?
- Does the source provide enough documentation to avoid lookahead in universe,
  benchmark, cash, cost/friction, and return-construction decisions?

Unanswered questions remain blockers. Positive answers would still not approve
source use without a separate approval phase.

## Allowed Next Steps

Allowed next steps after Phase 94:

- primary-source verification for 1-3 candidates
- terms/license review for 1-3 candidates
- provider documentation review
- no local data download yet
- no ingestion
- no source approval
- no manifest-to-planning bridge

The likely next phase should verify primary official documentation and terms
for 1-3 candidates. A narrow starting batch carried forward from the Phase 94
prompt is Stooq, Alpha Vantage, and FRED, unless the next phase documents a
better ordering before review begins.

## Relationship To Prior Phases

Phase 83 defined broad ETF source-path and local snapshot readiness criteria.
Phase 94 adds only normalized advisory source-discovery intake. It does not
approve any source path or local snapshot.

Phase 84 added the metadata-only `LocalSnapshotManifest`. Phase 94 does not
change that contract, does not instantiate it for real data, and does not
connect it to planning or replay.

Phase 88 defined return-basis and as-of interpretation boundaries. Source
terms do not solve return construction, adjusted-price interpretation,
distribution treatment, total-return construction, or no-lookahead timing.

Phase 89 defined universe, inception, and survivorship boundaries. Source
coverage does not solve ETF universe membership, inactive coverage, delisting
treatment, symbol continuity, inception eligibility, or survivorship bias.

Phase 90 defined benchmark and cash timing boundaries. A source that offers
benchmark, index, rate, or cash data does not approve a benchmark, cash proxy,
publication-timing rule, revision rule, compounding rule, or cash-return
convention.

Phase 91 defined cost and friction assumptions. Source data does not supply an
approved cost model, spread assumption, slippage rule, liquidity threshold,
turnover rule, rebalance-cost rule, expense treatment, or trading-readiness
claim.

Phase 93 defined the broad ETF source evidence intake plan. Phase 94 is the
next docs-only normalization step for external scout output under that plan.
It keeps source discovery separate from source approval.

Across these phases:

- source discovery does not approve source use
- source terms do not solve return construction
- source coverage does not solve survivorship
- source timestamps do not prove no-lookahead safety
- source data must not enter normal pytest

## Explicit Non-Claims

Phase 94 is:

- not source approval
- not data approval
- not vendor approval
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

It adds no source approval, data approval, vendor approval, universe approval,
benchmark approval, cash proxy approval, methodology approval, parameter
approval, evidence approval, return-construction approval, no-lookahead
approval, cost/friction approval, liquidity approval, strategy validation, real
data ingestion, raw external data, ETF ticker selection, benchmark comparison,
ranking, scoring, recommendation, candidate discovery behavior, replay metric,
manifest-to-planning bridge, signal/evaluator behavior, broker/order/fill/
portfolio/runtime behavior, LLM call, network call, market-data call,
dashboard/advisory/AI integration, paper behavior, live behavior, or trading
behavior.

## Decision

Decision: advisory source-discovery normalization only.

The strongest later-review buckets are Stooq, Alpha Vantage, Polygon.io,
Nasdaq Data Link, and FRED for cash/rate proxy review only. None is approved.
Each still requires primary-source documentation review, terms/license review,
storage-rights review, point-in-time/as-of review, adjustment review,
survivorship review, and normal-pytest isolation review before any stronger
claim can be made.

## Remaining Blockers

- no approved source
- no approved data
- no approved vendor
- no approved broker feed
- no approved public download path
- no approved API export path
- no approved local snapshot
- no approved raw-row storage policy
- no approved ETF universe
- no approved benchmark
- no approved cash proxy
- no approved methodology
- no approved parameter set
- no approved evidence
- no approved return-construction policy
- no approved no-lookahead/as-of policy
- no approved survivorship policy
- no approved benchmark/cash timing policy
- no approved cost/friction model
- no approved liquidity rule
- no strategy-validation claim
- no trading-readiness claim
