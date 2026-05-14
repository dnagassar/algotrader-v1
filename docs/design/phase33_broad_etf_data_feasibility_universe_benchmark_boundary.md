# Phase 33 Step 3 - Broad ETF Data Feasibility, Universe, And Benchmark Boundary

## Purpose

This document groups public data feasibility, ETF universe requirements, and
benchmark/cash proxy requirements for the broad-ETF simple moving-average
candidate.

It does not approve data, an ETF universe, a benchmark, a cash proxy,
methodology, reproduction, validation, or implementation.

This phase is documentation-only. It adds no data, notebook, script, schema,
test, source code, evaluator, signal computation, trading-path behavior,
broker behavior, runtime behavior, or persistence behavior.

## Candidate Restatement

Broad-ETF simple moving-average trend-following is the primary easier-data
candidate for further review only.

The candidate is not validated, implemented, production-ready, trading-ready,
or actionable. It has no approved data source, ETF universe, benchmark, cash
proxy, moving-average parameter, signal definition, reproduction protocol, or
implementation path.

## Feasibility Labels

Use only cautious source-feasibility labels:

- promising for source review
- usable only as secondary/check source
- proxy/context only
- unresolved / needs documentation review
- likely unsuitable

These labels are routing aids only. They do not approve a source, dataset,
license, local snapshot, benchmark, universe, or implementation.

## Public/Easy Data Source Feasibility

The source categories below remain candidate categories only. Public
availability is not license approval, and easy access is not project approval.
Every category needs source-documentation, licensing, provenance, versioning,
and offline-use review before any project use.

| Source category | Possible role | Strengths | Weaknesses | Adjusted-price / total-return support | Local snapshot possibility | Licensing/offline-use clarity | Fit with normal offline pytest | Current status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Stooq | Candidate ETF price-history source for source review. | Public/easy access, no obvious credential dependency for review, simple price-history orientation. | Coverage, symbol identity, adjustment semantics, data corrections, and terms need verification. | Adjusted-price semantics must be documented; total-return support must not be assumed. | Possible only if terms permit a versioned local snapshot with access date and hashes. | Unresolved; needs documentation review before use. | Fits only if no tests fetch network data and any future snapshot is approved separately. | Promising for source review; candidate source only, not approved. |
| Yahoo Finance / yfinance | Candidate retail-access price-history source or cross-check source. | Broad ticker coverage, familiar adjusted-close and corporate-action fields, low friction for manual review. | Provider terms, yfinance as an unofficial client, API stability, adjustment semantics, and redistribution/offline use need review. | Adjusted close and corporate-action fields may be available but require verification; total-return equivalence must not be assumed. | Possible only if terms allow snapshotting and replay; client behavior must not become a test dependency. | Unresolved; likely needs stricter terms review than the data access suggests. | Not acceptable for normal pytest network/API use; possible only as later approved static snapshot or secondary check. | Usable only as secondary/check source; candidate source only, not approved. |
| Nasdaq Data Link, where applicable | Candidate dataset-discovery or source-review route for relevant public or low-friction datasets. | Dataset-level documentation may be clearer than ad hoc web scraping, depending on dataset. | Coverage, credentials, rate limits, dataset-specific terms, versioning, and update behavior vary by dataset. | Varies by dataset and must be documented exactly before use. | Possible only if a specific dataset permits deterministic local archival. | Unresolved at category level; needs dataset-specific documentation review. | Credentialed or network access must stay out of normal pytest; static fixtures would need later approval. | Unresolved / needs documentation review; candidate source only, not approved. |
| Alpha Vantage free/retail APIs | Candidate API source or secondary/check source for price history. | Documented retail API shape and common adjusted daily data route may support review. | API key, rate limits, throttling, terms, field definitions, corrections, and long-horizon ETF coverage need review. | Adjusted fields may be available in some endpoints, but dividend/split and total-return handling must be verified. | Possible only if API terms permit local snapshotting and replay without redistribution issues. | Unresolved; API-key and terms review required. | Normal pytest must never require an API key or network call; possible only as later approved static snapshot/check source. | Usable only as secondary/check source; candidate source only, not approved. |
| Official ETF issuer pages | Candidate metadata source for fund identity, inception, distributions, fees, benchmark index, holdings summaries, and issuer changes. | Authoritative for fund-level metadata and useful for symbol/inception checks. | Not a uniform price-history source; pages change, metadata dates vary, and redistribution/offline-use terms need review. | May document distributions and fund metadata but does not by itself provide an approved adjusted price or total-return series. | Possible only for cited metadata snapshots if terms and provenance rules permit. | Unresolved; issuer-specific review required. | Fits as manually reviewed metadata only; no normal pytest network dependency. | Proxy/context only; candidate metadata source only, not approved. |
| FRED, where applicable | Candidate T-bill, risk-free, or cash-proxy context source. | Public macro/time-series orientation and series documentation may support cash-proxy review. | Series definitions, release timing, revisions, frequency conversion, calendar alignment, and terms need review. | Not an ETF adjusted-price source; risk-free or cash proxy only. | Possible only if terms permit a cited, versioned local snapshot with access date and series metadata. | Unresolved; needs series-specific and offline-use review. | Fits only as later approved static snapshot; normal pytest must not fetch FRED. | Promising for source review as cash-proxy context; candidate source only, not approved. |
| Broker historical data | Context source only, not the default project source for this research route. | May be useful later to understand broker-provided fields and trading-account context. | Requires broker/vendor terms, credentials, network access, account context, and trading-path isolation; field semantics vary. | Varies by broker and must not be assumed to match adjusted or total-return research needs. | Possible only if terms and account controls allow, but not suitable for default deterministic research setup. | Unresolved and likely unsuitable for this default docs-only route. | Poor fit for normal offline, credential-free pytest; must not introduce broker/runtime dependencies. | Proxy/context only and likely unsuitable as default project source; not approved. |

## ETF Universe Boundary

Any future ETF universe must be defined before looking at performance. A later
universe proposal must document:

- broad, liquid, simple instruments
- explicit inclusion and exclusion rules
- clear fund inception dates and first usable observation dates
- stable symbol identity across ticker changes, issuer changes, share classes,
  exchanges, and provider symbol formats
- sufficient history for any later methodology review, without treating short
  history as validation
- a plan to avoid survivorship-biased universe construction
- a plan to avoid cherry-picked winners or retrospectively convenient funds
- inactive, delisted, merged, liquidated, or ticker-changed fund handling where
  applicable
- asset class categories before performance inspection
- preference for simple broad-market exposures over niche, leveraged,
  inverse, thematic, or thinly traded ETFs
- treatment of funds with changed benchmark indexes, mandates, or fee
  structures
- liquidity, spread, and tradability metadata requirements for later review
  only, without risk or execution approval

No final ETF list, ticker, issuer, index family, asset class mix, inclusion
rule, exclusion rule, inception rule, or inactive-fund policy is approved in
this phase.

## Benchmark / Cash Proxy Boundary

Any future benchmark or cash proxy must be defined before reviewing results. A
later proposal must document:

- buy-and-hold comparison target, including whether it is a single ETF, each
  ETF in the universe, a blended universe benchmark, or a separately defined
  reference
- cash, T-bill, or risk-free proxy definition
- risk-free series source, with FRED as a candidate only where applicable
- benchmark and candidate date alignment, including holidays, missing
  sessions, month-end dates, and publication timing
- handling of ETF inception dates and unequal available histories
- total-return versus price-return comparison caveats
- dividend, distribution, and split treatment for both candidate and
  benchmark paths
- frequency conversion rules for cash or T-bill series if daily ETF data is
  compared with lower-frequency macro series
- transaction cost, spread, slippage, rebalance, and friction assumptions to
  define later
- benchmark limitations and non-claims

No benchmark, cash proxy, T-bill series, buy-and-hold comparison, date
alignment rule, total-return convention, or cost/friction assumption is
approved in this phase.

## Source-Quality Requirements

A later source package or verification gate must document:

- adjusted close, adjusted open/high/low/close, or total-return handling
- dividend and split adjustment transparency
- whether distribution and split fields are separately available and
  internally consistent with adjusted fields
- timestamp/date semantics, including market close, publication timing,
  timezone, holidays, missing sessions, and stale observations
- missing-data handling, duplicate-date handling, bad-tick handling, and
  cross-source discrepancy handling
- local snapshot and versioning plan, including access date, source version,
  file hashes, immutable storage expectations, and replay scope
- provenance and citation requirements for every source, series, symbol, and
  metadata field
- license, redistribution, and offline-use review before any local fixture,
  repository artifact, or project-local data use
- deterministic reproducibility without implicit network, credentials, account
  state, current provider behavior, or wall-clock dependence
- explicit no-lookahead assumptions for prices, corporate actions, fund
  metadata, benchmark series, risk-free series, and universe membership
- normal `python -m pytest` remains offline, deterministic,
  credential-free, and independent of data-provider accounts or network
  access

Any unresolved source-quality item blocks data approval, ETF universe approval,
benchmark approval, reproduction approval, signal-definition review, and
implementation-scope review.

## Public-Source Documentation Verification Sweep

Phase 33 Step 4 adds the public-source documentation verification sweep in
[`phase33_broad_etf_public_source_documentation_verification_sweep.md`](phase33_broad_etf_public_source_documentation_verification_sweep.md).
That sweep normalizes public documentation and external scout-report findings
for Stooq, Yahoo Finance / yfinance, Nasdaq Data Link, Alpha Vantage, official
ETF issuer pages, FRED, and broker historical data as cautious routing context
only.

Step 4 does not approve a source, ETF universe, benchmark, cash proxy,
methodology, reproduction, validation, implementation, or trading implication.
It keeps Stooq and Yahoo Finance / yfinance in the candidate source queue,
keeps Nasdaq Data Link and Alpha Vantage as secondary/check candidates only,
keeps issuer pages as metadata/context only, keeps FRED as a cash/risk-free
proxy candidate only, and keeps broker historical data as context only.

## Methodology And No-Lookahead Review Boundary

Phase 33 Step 5 adds the methodology and no-lookahead/as-of review boundary in
[`phase33_broad_etf_methodology_no_lookahead_review_boundary.md`](phase33_broad_etf_methodology_no_lookahead_review_boundary.md).
That boundary defines what a future methodology review must cover before any
reproduction, including moving-average concept, price-only versus total-return
inputs, daily versus monthly cadence, signal observation date versus action
date, benchmark/cash comparison rules, cost/friction assumptions, parameter
discipline, and anti-cherry-picking controls.

Step 5 also defines no-lookahead/as-of constraints for future protocols,
including decision-time price availability, adjusted data caution,
inception-date handling, benchmark/cash availability alignment, corporate
actions, universe membership timing, no same-day close-to-close assumption
without later justification, lagged action timing, and normal offline,
credential-free pytest.

Step 5 does not approve methodology, parameters, data, an ETF universe, a
benchmark, a cash proxy, reproduction, validation, implementation, or trading
implication.

## Recommended Next Gate

Phase 33 Step 6 adds the grouped ETF universe and benchmark/cash proxy
shortlist boundary in
[`phase33_broad_etf_universe_benchmark_shortlist_boundary.md`](phase33_broad_etf_universe_benchmark_shortlist_boundary.md).
It defines candidate buckets, example tickers, benchmark/cash proxy
candidates, rejection criteria, and next routing as non-approving review
context only.

That boundary remains documentation-only unless a later phase explicitly
approves a narrower scope. It must not acquire data, ingest data, approve a
source, approve a universe, approve a benchmark, approve a cash proxy,
reproduce results, validate, backtest, implement methodology, implement an
evaluator, compute signals, or create trading implications.

Recommended next docs-only gate after Step 6: data-source terms/license review
boundary or moving-average evidence source package. A reproduction protocol
boundary should wait until data, universe, and benchmark/cash proxy are later
approved.

## Explicit Non-Goals

This phase does not perform or authorize:

- data approval
- ETF universe approval
- benchmark approval
- cash proxy approval
- data acquisition
- data ingestion
- dataset approval
- schema, code, notebook, or script
- backtest
- reproduction
- methodology approval
- moving-average parameter approval
- strategy implementation
- evaluator or signal implementation
- signal computation
- signal scoring, ranking, direction, confidence, or actionability
- `ValidatedResearchArtifact`
- `ValidatedSignalDefinition`
- new contract type
- production threshold
- profitability claim
- production-readiness claim
- implementation-readiness claim
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
- no source-documentation approval or terms/license resolution
- no total-return versus price-return comparison decision
- no transaction cost, slippage, spread, or friction assumption review
- no result-review template
- no promotion/rejection decision
- no trading implication or production threshold
