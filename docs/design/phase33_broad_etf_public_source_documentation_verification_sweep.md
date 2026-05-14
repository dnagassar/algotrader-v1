# Phase 33 Step 4 - Broad ETF Public-Source Documentation Verification Sweep

## Purpose

This document records what appears supported by public documentation for broad
ETF price data, ETF metadata, and cash/benchmark candidates for the broad-ETF
simple moving-average research candidate.

It does not replace terms, licensing, redistribution, private-repository, or
offline-use review.

It does not approve data, an ETF universe, a benchmark, a cash proxy,
methodology, reproduction, validation, implementation, trading use, or any
moving-average parameter.

This phase is documentation-only. It adds no data, notebook, script, schema,
test, source code, evaluator, signal computation, trading-path behavior,
broker behavior, runtime behavior, scheduler behavior, persistence behavior,
portfolio behavior, ledger behavior, reconciliation behavior, Alpaca behavior,
ML behavior, or LLM trading-path behavior.

## Evidence-Quality Policy

This sweep separates source quality into three classes:

- Primary documentation: official provider, issuer, or source-owner pages,
  API docs, product docs, series pages, help pages, or terms pages.
- Secondary documentation: client-library docs, third-party tutorials,
  community notes, or summaries about a provider.
- Inference: project routing conclusions derived from public documentation,
  external scout research, or unresolved documentation gaps.

Public documentation can support cautious routing labels only. It does not
equal legal, licensing, redistribution, local archival, private-repository, or
offline-use approval.

The externally supplied Perplexity report is external public-documentation
scout research only. It is not a source of truth, a licensing decision, a data
approval, a methodology approval, or an implementation decision. Claims from
the scout report must remain provisional unless supported by official
documentation reviewed in this or a later phase.

Marketing pages, third-party tutorials, client-library behavior, search
snippets, and agent summaries must remain provisional unless supported by
official source-owner documentation. Secondary-source claims must not be
promoted into verified project facts.

## Public Documentation Reviewed

This sweep used public documentation and public-doc search results available
on May 13, 2026. It did not download datasets or acquire historical market
data.

| Source/category | Documentation reviewed in this sweep | Evidence quality used |
| --- | --- | --- |
| Stooq | Stooq "Free Historical Market Data" page showing daily/hourly/5-minute bulk folders, including U.S., U.K., and ETF folders; Stooq symbol historical-data pages as documentation context only. | Primary for public bulk/folder existence; inference for adjustment, dividend, revision, and license gaps. |
| Yahoo Finance / yfinance | yfinance official documentation, including its legal disclaimer, `download(...)` parameters, `auto_adjust`, and `actions`; Yahoo legal/API terms pages linked from yfinance; Yahoo Finance historical-download help page identified by search result but not relied on as a verified project fact. | Secondary for yfinance client behavior; primary only for Yahoo legal/API terms pages; inference for Yahoo Finance historical-data support unless later official Yahoo documentation is captured directly. |
| Nasdaq Data Link | Nasdaq Data Link documentation home, data organization/access/authentication docs, API/table docs, help-center API-key and rate-limit pages. | Primary for platform/API/authentication/product-page structure; unresolved at dataset-specific ETF coverage and license level. |
| Alpha Vantage | Alpha Vantage API documentation for time series, adjusted daily data, split/dividend fields, API-key examples, and related endpoints. | Primary for API shape, adjusted endpoint existence, and key requirement; unresolved for exact adjustment methodology, ETF coverage, and license/offline use. |
| Official ETF issuer pages | Public issuer pages and fact sheets from iShares/BlackRock, Vanguard, SPDR/State Street, and Invesco showing fund metadata, holdings, fees, distributions, index/objective text, and performance context. | Primary for issuer metadata/context; not primary historical price-data documentation for this project. |
| FRED | FRED API documentation, FRED/ALFRED vintage-date documentation, TB3MS series page, and DGS3MO series page. | Primary for series identity, frequency/units context, citation, vintage/revision documentation, and candidate cash/risk-free context. |
| Broker historical data | Alpaca Market Data API public documentation and FAQ as broker-source context only, including authentication, subscription, feed, historical bar, and timestamp examples. | Primary for broker API context; not a default project source and not a research data approval. |

## Verification Table

| Source/category | Public documentation reviewed | Source quality | What appears documentation-supported | What remains unclear | Adjusted-price support | Total-return/dividend support | Timestamp/as-of implication | Offline snapshot implication | Licensing/offline-use implication | Current feasibility label | Still requires follow-up | Allowed next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Stooq | Official Stooq historical market-data pages, including bulk folders and ETF categories. | Primary for access shape; inference for research suitability. | Public docs show bulk historical market-data folders and ETF folders across markets, including U.S. exchange ETF categories. | Adjustment methodology, dividend handling, split handling, data corrections, revision policy, symbol identity over time, archive terms, redistribution, private repo use, and support expectations. | Unresolved. Do not assume adjusted close or adjusted OHLC semantics. | Unresolved. Do not assume total-return or reinvestment support. | Daily files imply dated observations, but market-close timing, timezone, correction timing, and as-of semantics remain unresolved. | Possible only after terms permit a frozen local snapshot with access date, hashes, source version notes, and replay boundaries. | Unresolved; public availability and bulk files are not license/offline-use approval. | promising for source review | Direct terms/license review; adjustment/dividend/split methodology; correction/revision policy; symbol and ETF coverage checks. | Keep in candidate source queue for further docs-only source review. |
| Yahoo Finance / yfinance | yfinance docs, Yahoo terms pages, and Yahoo historical-download help search result as unverified context. | Secondary for client behavior; primary for Yahoo terms; inference for Yahoo Finance data support. | yfinance documents Yahoo data access, default `auto_adjust=True`, optional dividend/split actions, date range/frequency parameters, and explicitly says it is unofficial and points users to Yahoo terms. | Yahoo Finance automation terms, API stability, official historical-data documentation capture, adjusted-close methodology, correction policy, long-term cache/archive permission, private repo use, and redistribution/derived-stat publication. | yfinance supports auto-adjusted output behavior, but official Yahoo adjusted-close methodology remains unresolved. | yfinance can request actions, but total-return equivalence and reinvestment semantics remain unresolved. | yfinance date ranges and interval behavior are documented; official Yahoo publication timing, corrections, timezone, and as-of semantics remain unresolved. | Possible only if Yahoo terms and project policy permit a frozen snapshot; yfinance behavior must not be a normal pytest dependency. | Unresolved; yfinance itself warns users to consult Yahoo terms and is not Yahoo-endorsed. | promising for source review | Official Yahoo historical-data docs and terms review; API stability; cache/archive rights; adjustment and corporate-action methodology. | Keep in candidate source queue for further docs-only source review, with yfinance treated as client/tooling documentation only. |
| Nasdaq Data Link | Official Data Link docs for platform organization, APIs, tables, authentication, product pages, and rate limits. | Primary for platform/API structure; inference for ETF source fit. | Docs show Data Link has dataset product pages, API routes, table/CSV-style delivery, authentication, API keys, and rate-limit concerns. | Specific ETF historical-price dataset coverage, free versus premium access, adjustment fields, dividend/split handling, product-specific terms, versioning, and offline archival rights. | Varies by dataset; not established for the broad-ETF candidate. | Varies by dataset; not established. | Product-specific; table docs mention daily updates for many table datasets but not candidate-specific as-of semantics. | Possible only for a specific approved dataset with snapshot rights and deterministic replay rules. | Unresolved and dataset-specific; API-key and account terms likely matter. | usable only as secondary/check source | Identify exact ETF dataset candidates, coverage, fields, terms, adjustment docs, and export/snapshot rights. | Keep as secondary/check candidate only unless a specific ETF dataset and terms are later clarified. |
| Alpha Vantage | Official API docs for daily adjusted time series, split/dividend event fields, API-key examples, and listing/status-style endpoints. | Primary for endpoint shape; inference for broad-ETF source fit. | Docs show adjusted daily endpoint availability, raw and adjusted values, historical split/dividend events, API-key request pattern, and documented field families. | ETF coverage depth, free-tier availability, rate limits for project needs, exact adjustment methodology, correction/revision policy, archive/private-repo permission, and long-term reproducibility. | Endpoint-level support appears documented, but exact methodology and coverage remain unresolved. | Split/dividend event fields appear documented; total-return or reinvestment support must not be assumed. | API output is request-time provider state unless later archived; exact publication/correction/as-of semantics remain unresolved. | Possible only after terms permit snapshotting and replay; API calls must stay outside normal pytest. | Unresolved; API-key/account/terms review required. | usable only as secondary/check source | Rate limits; ETF coverage; field definitions; adjustment methodology; local archival and private repo terms. | Keep as secondary/check candidate only. |
| Official ETF issuer pages | iShares/BlackRock, Vanguard, SPDR/State Street, and Invesco public fund pages/fact sheets. | Primary for issuer metadata/context. | Issuer pages/fact sheets can document fund identity, issuer, objective/index, inception/listing dates, expense ratios, holdings, distributions, performance context, and liquidity/fee context. | Page versioning, archival terms, historical metadata revisions, point-in-time fund metadata, distribution history completeness, benchmark changes, and private repo use. | Not a primary adjusted-price source for this candidate. | Distribution tables/context may exist, but they do not by themselves provide project-approved total-return series. | Issuer pages are current or as-of dated; historical point-in-time metadata requires separate capture and versioning review. | Possible only for cited metadata snapshots if terms permit; not a price-history snapshot route. | Issuer-specific terms and redistribution/offline-use review required. | proxy/context only | Metadata citation policy; issuer-specific terms; as-of dates; historical index/objective changes; distribution table scope. | Keep as metadata/context only for universe and benchmark documentation. |
| FRED | FRED API docs, ALFRED/vintage-date docs, TB3MS, and DGS3MO series pages. | Primary for series identity and macro-series documentation. | FRED documents API access and vintage-date/revision concepts. TB3MS appears as a monthly 3-month Treasury bill secondary-market discount-rate series; DGS3MO appears as a daily 3-month Treasury constant-maturity market-yield series. | Terms/offline archival, API-key policy if used programmatically, release timing, revision handling, frequency conversion, holiday alignment, compounding, and mapping to ETF signal dates. | Not applicable to ETF adjusted prices. | Not an ETF total-return source; cash/risk-free conversion assumptions remain unresolved. | FRED/ALFRED documentation supports vintage/revision review, but project-specific as-of and release-lag rules remain unresolved. | Possible only after terms permit a cited, versioned local snapshot with access date, hashes, and series metadata. | Public/citation signals exist, but legal/offline-use review still required. | proxy/context only | Terms/license review; vintage/revision policy; daily/monthly alignment; compounding and cash-return convention. | Keep as cash/risk-free proxy candidate only. |
| Broker historical data | Alpaca Market Data API docs and FAQ as broker-source context only. | Primary for broker API context; inference for project suitability. | Docs show historical bars exist, API credentials are generally required, subscriptions/feed choices matter, and timestamps/feed differences can matter. | Broker terms, account dependence, feed entitlements, adjustment semantics, archive rights, reproducibility, and trading-path isolation. | Varies by broker/feed; not established for this candidate. | Varies by broker/feed; not established. | Broker docs show timestamp/feed semantics can be explicit, but account/feed state can influence returned data. | Poor default fit because credentials, subscription state, and broker account context would contaminate normal pytest if used directly. | Unresolved and likely unsuitable for default source approval without strict isolation and terms review. | proxy/context only | Broker terms; feed entitlements; adjustment fields; credential isolation; snapshot rights. | Keep as context only, not default project source. |

## Cautious Feasibility Labels

Use only these labels in this phase:

- promising for source review
- usable only as secondary/check source
- proxy/context only
- unresolved / needs documentation review
- likely unsuitable

Assigned labels:

| Source/category | Current feasibility label | Rationale |
| --- | --- | --- |
| Stooq | promising for source review | Public docs show broad/bulk historical market-data access and ETF folders, but adjusted, dividend, revision, symbol, and license details remain unresolved. |
| Yahoo Finance / yfinance | promising for source review | yfinance documents useful access behavior and adjusted/action options, but Yahoo official automation terms, API stability, cache/archive rights, and methodology remain unresolved. |
| Nasdaq Data Link | usable only as secondary/check source | Platform docs are clearer than ad hoc scraping, but ETF coverage, product-specific terms, and adjustment fields are unresolved. |
| Alpha Vantage | usable only as secondary/check source | API docs show adjusted daily and split/dividend fields, but rate limits, coverage, adjustment detail, and archival rights remain unresolved. |
| Official ETF issuer pages | proxy/context only | Issuer docs are useful for metadata and distributions context, not primary historical price data. |
| FRED | proxy/context only | FRED is candidate-only for cash/T-bill or risk-free comparison context, not ETF price data. |
| Broker historical data | proxy/context only | Broker data may explain account/feed constraints, but it is not a default deterministic, offline, credential-free project source. |

No source is approved by this labeling.

## ETF Universe Documentation Notes

Public issuer, provider, and source documentation appear sufficient to justify
future docs-only universe review categories, not an approved universe.

| Candidate universe category | What public docs appear to support | What remains unresolved |
| --- | --- | --- |
| Broad U.S. equity ETFs | Issuer pages and Stooq/Yahoo-style symbol coverage can support later identification of broad U.S. equity ETF candidates, inception dates, expense ratios, benchmark/index metadata, holdings, and distributions context. | No ticker list, inclusion rule, inactive-fund policy, survivorship control, minimum history, liquidity threshold, price source, or benchmark is approved. |
| Broad international equity ETFs | Issuer pages can support later metadata for global or ex-U.S. broad equity exposures, and public price-source coverage may exist. | Currency, domicile, withholding/distribution treatment, exchange/session calendars, coverage history, survivorship, and benchmark comparability remain unresolved. |
| Broad bond ETFs | Issuer pages can support later metadata for broad Treasury, aggregate bond, investment-grade, or duration-based ETF candidates. | Total-return needs, income/distribution treatment, duration/credit/index changes, rate benchmark alignment, and adjusted-price adequacy remain unresolved. |
| Broad commodity/gold ETFs | Issuer pages can support later metadata for gold or broad commodity ETF candidates where source quality allows. | Commodity structure, roll/spot exposure, tax/issuer structure, distribution assumptions, benchmark comparability, and price-history support remain unresolved. |
| Cash/T-bill proxy | FRED documentation supports candidate review of Treasury bill or short-rate series such as TB3MS and DGS3MO. | Series choice, frequency alignment, compounding, release timing, vintage/revision policy, local snapshot rights, and benchmark/cash proxy definition remain unresolved. |

No ETF universe, ticker list, asset-class mix, issuer set, index family,
inclusion rule, exclusion rule, inception rule, inactive-fund policy, or
metadata source is approved in this phase.

## Benchmark And Cash Proxy Notes

FRED remains candidate-only for cash/T-bill or risk-free proxy review. The
externally supplied scout report and reviewed FRED pages support carrying
forward at least these candidate series for docs-only review:

- `TB3MS`: 3-month Treasury bill secondary-market rate, monthly, discount
  basis.
- `DGS3MO`: 3-month Treasury constant-maturity market yield, daily,
  investment basis.

The project has not approved either series as a benchmark, cash proxy,
risk-free proxy, or return-construction input.

Unresolved benchmark/cash proxy questions include buy-and-hold comparison
target, cash return convention, frequency conversion, holiday alignment,
release timing, vintage/revision handling, compounding, daily versus monthly
signal-date alignment, and whether public documentation permits a local
versioned snapshot.

No benchmark, cash proxy, T-bill series, buy-and-hold comparison, date
alignment rule, total-return convention, or cost/friction assumption is
approved in this phase.

## Direct Follow-Up Backlog

Carry forward these unresolved questions before any source approval, universe
approval, benchmark approval, reproduction, validation, or implementation:

- adjusted-close methodology
- total-return versus price-plus-dividend assumptions
- dividend/reinvestment treatment
- split/corporate-action handling
- correction/revision policies
- point-in-time/as-of semantics
- local archival permission
- private repo permission
- derived-stat publication permission
- API rate limits
- long-term reproducibility
- terms/license review
- ETF coverage depth by source
- stable symbol identity and ticker-change handling
- issuer metadata versioning and historical changes
- benchmark/cash proxy frequency alignment
- normal pytest isolation from network, credentials, accounts, provider state,
  and wall-clock state

Any unresolved item blocks data approval, ETF universe approval, benchmark
approval, reproduction approval, signal-definition review, and
implementation-scope review.

## Recommended Next Routing

Recommended routing after this sweep:

- Keep Stooq and Yahoo Finance / yfinance in the candidate source queue for
  further docs-only review.
- Keep Nasdaq Data Link and Alpha Vantage as secondary/check candidates only.
- Keep official ETF issuer pages as metadata/context only.
- Keep FRED as a cash/risk-free proxy candidate only.
- Keep broker historical data as context only, not a default project source.
- Do not approve any source yet.

Phase 33 Step 5 adds the methodology and no-lookahead/as-of review boundary in
[`phase33_broad_etf_methodology_no_lookahead_review_boundary.md`](phase33_broad_etf_methodology_no_lookahead_review_boundary.md).
That boundary groups methodology-review scope, no-lookahead/as-of constraints,
methodology evidence standards, required non-claims, and remaining blockers
without approving methodology, parameters, data, an ETF universe, a benchmark,
reproduction, validation, implementation, or trading use.

Phase 33 Step 6 adds the grouped ETF universe and benchmark/cash proxy
shortlist boundary in
[`phase33_broad_etf_universe_benchmark_shortlist_boundary.md`](phase33_broad_etf_universe_benchmark_shortlist_boundary.md).
That boundary keeps candidate ETF buckets, example tickers, benchmark/cash
proxy candidates, rejection criteria, and next routing non-approving.

Phase 33 Step 7 adds the data-source terms/license review boundary in
[`phase33_broad_etf_data_source_terms_license_review_boundary.md`](phase33_broad_etf_data_source_terms_license_review_boundary.md).
That boundary keeps public terms, license, caching, private-repo,
redistribution, derived-publication, API, and offline-use findings
non-approving.

Other possible docs-only gates remain:

1. final source shortlist decision boundary
2. moving-average evidence source package
3. data storage/fixture policy boundary only after source terms are acceptable
4. reproduction protocol boundary only if data, universe, and benchmark/cash
   proxy are later approved

None of those gates may acquire data, ingest data, approve data, approve an
ETF universe, approve a benchmark, approve a cash proxy, approve methodology,
approve parameters, reproduce results, validate a signal, or authorize
implementation unless a later phase explicitly scopes those approvals.

## Explicit Non-Goals

This phase does not perform or authorize:

- source approval
- data approval
- ETF universe approval
- benchmark approval
- cash proxy approval
- methodology approval
- moving-average parameter approval
- data acquisition
- data ingestion
- dataset approval
- schema, code, notebook, or script
- backtest
- reproduction
- strategy implementation
- evaluator or signal implementation
- signal computation
- signal scoring, ranking, direction, confidence, or actionability
- `ValidatedResearchArtifact`
- `ValidatedSignalDefinition`
- new contract type
- production threshold
- production-readiness claim
- implementation-readiness claim
- profitability claim
- trading implication
- broker, OMS, runtime, scheduler, persistence, portfolio, ledger,
  reconciliation, Alpaca, ML, or LLM trading-path behavior

## Remaining Blockers

Evaluator implementation and any production route remain blocked by all of the
following:

- no `ValidatedResearchArtifact`
- no `ValidatedSignalDefinition`
- no approved ETF universe
- no selected/approved data source
- no approved benchmark/cash proxy
- no acquired data
- no project-local deterministic reproduction
- no no-lookahead audit
- no production threshold/config provenance
- no implementation-scope approval
- no evaluator tests
- no approved methodology
- no approved moving-average parameters
- no approved data license or offline-use path
- no approved local snapshot/versioning policy
- no total-return versus price-return comparison decision
- no dividend/reinvestment treatment
- no corporate-action handling policy
- no correction/revision policy
- no point-in-time/as-of policy
- no source-specific local archival/private-repo/derived-stat publication
  permission
- no transaction cost, slippage, spread, or friction assumption review
- no result-review template
- no promotion/rejection decision
- no trading implication or production threshold
