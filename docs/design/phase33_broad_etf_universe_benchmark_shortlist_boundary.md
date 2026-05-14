# Phase 33 Step 6 - Broad ETF Universe And Benchmark/Cash Proxy Shortlist Boundary

## Purpose

This document defines non-approving shortlists for ETF universe candidates and
benchmark/cash proxy candidates for the broad-ETF simple moving-average
candidate.

It does not approve an ETF universe, benchmark, cash proxy, data source,
methodology, reproduction, validation, signal definition, evaluator,
implementation, or trading use.

This phase is documentation-only. It adds no data, notebook, script, schema,
test, source code, evaluator, signal computation, trading-path behavior,
broker behavior, runtime behavior, scheduler behavior, persistence behavior,
portfolio behavior, ledger behavior, reconciliation behavior, Alpaca behavior,
ML behavior, or LLM trading-path behavior.

## Candidate Restatement

Broad-ETF simple moving-average trend-following remains an easier-data
research candidate for review only.

The candidate is not validated, implemented, trading-ready, production-ready,
or actionable. It has no approved ETF universe, benchmark, cash proxy, data
source, methodology, moving-average parameter, reproduction protocol,
validation route, signal definition, evaluator, or implementation path.

## ETF Universe Shortlist Principles

Any future ETF universe proposal must follow these principles before result
inspection:

- use broad, liquid, simple ETFs only
- avoid thematic, niche, leveraged, inverse, thinly traded, or complex
  exposures
- avoid performance-driven selection and avoid selecting instruments because
  of known historical returns
- define asset-class buckets before any future result inspection
- respect ETF inception dates, listing dates, and first usable observation
  dates
- preserve symbol identity across ticker changes, issuer changes, exchange
  changes, provider symbol formats, mergers, liquidations, and delistings
- record expense ratio and index tracked where available
- record survivorship, closure, merger, ticker-change, and delisting caveats
- prefer instruments with public issuer documentation for objective, index,
  inception, expense, holdings, distribution, and metadata context
- keep all ticker lists candidate-only until a later approval gate

No final ETF universe, ticker list, bucket mix, issuer set, index family,
inclusion rule, exclusion rule, inception rule, inactive-fund policy, or
metadata source is approved in this phase.

## Candidate ETF Buckets

The buckets below are candidate review buckets only. They are not an approved
universe, benchmark, allocation set, or implementation target.

| Candidate bucket | Possible role | Source/metadata candidates | Key caveats | Inception/date-range consideration | Current status |
| --- | --- | --- | --- | --- | --- |
| Broad U.S. equity | Domestic broad-market equity exposure for later universe review. | Stooq or Yahoo/yfinance as source-review candidates; issuer pages for metadata; Nasdaq Data Link or Alpha Vantage only as secondary/check candidates. | Price adjustment, dividend treatment, symbol identity, data-source terms, benchmark comparability, and total-return versus price-return treatment remain unresolved. | Later review must record each candidate fund's inception/listing date and first usable observation before any common sample is considered. | Candidate only, not approved. |
| Broad international developed equity | Developed ex-U.S. equity exposure for later universe review. | Same candidate source categories, with issuer pages for fund objective, index, expense, holdings, and distribution context. | Currency, domicile, withholding/distribution treatment, regional index changes, exchange calendars, and data-provider coverage remain unresolved. | Later review must avoid pretending a longer history exists than the actual fund and source history support. | Candidate only, not approved. |
| Broad emerging-market equity | Emerging-market equity exposure for later universe review. | Same candidate source categories, with issuer pages for index, country exposure, expense, holdings, and distribution context. | Higher data-quality, calendar, closure, index-change, withholding, liquidity, and tracking-difference caveats may apply. | Later review must record inception/listing dates and account for unequal history versus developed-market candidates. | Candidate only, not approved. |
| Broad U.S. aggregate bond | Core bond exposure for later universe review. | Same candidate source categories, with issuer pages for index, duration, credit, distribution, and expense context. | Income/distribution treatment, total-return needs, duration/credit changes, and adjusted-price adequacy remain unresolved. | Later review must define whether bond ETF price-only series are even suitable before any sample window is chosen. | Candidate only, not approved. |
| Long-duration Treasury or Treasury bond exposure | Interest-rate duration exposure for later universe review. | Same candidate source categories, with issuer pages for Treasury maturity/duration and index context. | Duration drift, distribution treatment, interest-rate regime dependence, and benchmark/cash comparison rules remain unresolved. | Later review must respect inception and first usable observations separately from aggregate bond candidates. | Candidate only, not approved. |
| Broad commodity or gold exposure, if source quality allows | Optional diversifier bucket only if source, structure, and methodology caveats are acceptable. | Same candidate source categories; issuer pages for structure, objective, expenses, holdings, and distribution context. | Commodity structure, roll exposure, grantor trust or ETN structure, tax context, spot versus futures exposure, and benchmark comparability remain unresolved. | Later review must defer or reject the bucket if reliable source and structure documentation cannot support it. | Candidate only, not approved. |
| Cash/T-bill proxy | Handled separately as benchmark/cash proxy review, not as an ETF universe bucket. | FRED as cash/risk-free proxy candidate only. | Series definition, frequency, release timing, vintage/revision policy, conversion, and alignment remain unresolved. | Later review must align availability dates and frequency before any use. | Candidate only, not approved. |

## Candidate ETF Examples

The examples below are candidate examples for later review only. They are not
approved final tickers, not an approved universe, and not selected based on
known performance.

| Example candidates | Possible role | Source/metadata candidates | Key caveats | Inception/date-range consideration | Current status |
| --- | --- | --- | --- | --- | --- |
| `SPY` / `IVV` / `VOO` | Broad U.S. equity candidates. | Stooq and Yahoo/yfinance remain source-review candidates only; issuer pages remain metadata/context only; Nasdaq Data Link and Alpha Vantage remain secondary/check candidates only. | Multiple similar funds may create duplicate exposure; source terms, adjusted prices, dividend handling, expense/index metadata, symbol identity, and total-return comparability remain unresolved. | Later review must record each fund's inception/listing date and first usable observation; choosing among them must not be performance-driven. | Candidate only, not approved. |
| `EFA` / `VEA` | Developed international equity candidates. | Same candidate source and metadata categories. | Coverage, currency, withholding/distributions, benchmark-index differences, regional exposure differences, and source quality remain unresolved. | Later review must handle unequal inception dates and source coverage without lookahead or cherry-picking. | Candidate only, not approved. |
| `EEM` / `VWO` | Emerging-market equity candidates. | Same candidate source and metadata categories. | Index construction, country exposure, liquidity, distribution treatment, tracking difference, and data quality remain unresolved. | Later review must record inception/listing dates and avoid selecting the longer or better-performing history by hindsight. | Candidate only, not approved. |
| `AGG` / `BND` | Broad U.S. aggregate bond candidates. | Same candidate source and metadata categories. | Income treatment, duration/credit changes, total-return needs, adjusted-price adequacy, and benchmark comparability remain unresolved. | Later review must determine whether price-only or adjusted data can support the intended methodology before any sample window is set. | Candidate only, not approved. |
| `TLT` / `IEF` | Treasury-duration candidates. | Same candidate source and metadata categories. | Duration choice, interest-rate exposure, distributions, volatility, and cash-proxy comparison rules remain unresolved. | Later review must respect each fund's inception and avoid parameter or duration selection based on known results. | Candidate only, not approved. |
| `GLD` / `IAU` or broad commodity ETF/ETN candidates | Optional gold or broad commodity exposure only if source quality and methodology caveats are acceptable. | Same candidate source and metadata categories, with issuer documentation especially important for structure and objective. | Commodity, grantor-trust, futures-roll, ETN credit, tax, distribution, and benchmark-comparison caveats may make the bucket unsuitable. | Later review must reject or defer this bucket if source, structure, or methodology assumptions cannot be documented before result inspection. | Candidate only, not approved. |

## Benchmark / Cash Proxy Shortlist

The benchmark and cash proxy candidates below are review candidates only. They
do not approve a benchmark, cash proxy, risk-free proxy, return convention, or
comparison target.

| Candidate | Possible role | Source/metadata candidates | Key caveats | Current status |
| --- | --- | --- | --- | --- |
| Buy-and-hold version of selected ETF universe | Future comparison against the same candidate universe if a universe is later approved. | Same approved-later ETF data source would be required; issuer pages may provide metadata only. | Cannot be defined until the universe, source, adjustment policy, and total-return versus price-return treatment are approved. | Candidate only, not approved. |
| Broad U.S. equity benchmark candidate | Possible broad-market comparison candidate, separate from or overlapping with the universe only if later justified. | Stooq/Yahoo as source-review candidates; issuer pages as metadata/context only; secondary/check sources as documented later. | Could duplicate the U.S. equity universe bucket; benchmark identity, dividend treatment, and total-return comparability remain unresolved. | Candidate only, not approved. |
| FRED T-bill or cash-rate series such as `TB3MS` or `DGS3MO` | Candidate cash, T-bill, or risk-free context for later review. | FRED remains a cash/risk-free proxy candidate only. | Monthly versus daily frequency, discount versus investment basis, release timing, vintage/revision handling, compounding, and alignment remain unresolved. | Candidate only, not approved. |
| Zero-return cash placeholder | Last-resort methodology placeholder only if a later docs-only protocol needs a neutral illustrative placeholder. | No data source. | Not realistic cash, not approved, not a benchmark, and not a substitute for T-bill/risk-free source review. | Candidate-only placeholder, not approved. |

## Benchmark/Cash Proxy Requirements

Any future benchmark or cash proxy proposal must document:

- date alignment between ETF observations, benchmark observations, cash proxy
  observations, holidays, missing sessions, and month-end dates
- frequency alignment between daily ETF data and daily or monthly benchmark
  or cash series
- availability-date and as-of assumptions, including publication timing,
  release lag, and vintage/revision handling where applicable
- treatment of monthly versus daily rates, including whether values are held,
  interpolated, lagged, or converted
- conversion assumptions if rates must later become return inputs, including
  compounding, day count, discount versus investment basis, and annualization
  treatment
- total-return versus price-return comparison caveats for both candidate and
  benchmark paths
- cash proxy limitations and what cash proxy cannot prove
- treatment of unequal inception dates, unequal histories, and missing data
- transaction-cost, spread, slippage, rebalance, fund-expense, tax, and
  friction assumptions as deferred methodology questions
- explicit non-claims and no benchmark approval

No benchmark, cash proxy, risk-free proxy, return-construction rule, date
alignment rule, frequency-conversion rule, total-return convention, or
friction assumption is approved in this phase.

## Universe And Benchmark Rejection Criteria

Reject or defer a universe, ETF, benchmark, or cash proxy candidate if any of
the following apply:

- inception date or first usable observation is too late for meaningful later
  review
- symbol identity is unstable, ambiguous, or cannot be reconciled across
  provider and issuer documentation
- data source quality, adjustment semantics, dividend treatment, correction
  policy, or revision policy is unclear
- corporate action, distribution, or dividend treatment cannot be documented
- candidate is thematic, niche, leveraged, inverse, thinly traded, complex,
  or performance-selected
- benchmark frequency cannot align with candidate data without unsupported
  assumptions
- cash proxy assumptions, release timing, conversion, or vintage/revision
  handling cannot be stated
- route encourages profitability, trading-readiness, implementation-readiness,
  production-threshold, or validation overclaims

Any rejected or deferred candidate may only return through a later explicit
docs-only gate that resolves the rejection reason without using inspected
performance results.

## Relationship To Prior Gates

Phase 33 Step 4 remains the current public-source documentation sweep. It
records source-review context only:

- Stooq and Yahoo Finance / yfinance remain source-review candidates only.
- Nasdaq Data Link and Alpha Vantage remain secondary/check candidates only.
- ETF issuer pages remain metadata/context only.
- FRED remains a cash/risk-free proxy candidate only.
- Broker historical data remains context only, not a default project source.

Phase 33 Step 5 remains the methodology and no-lookahead/as-of review
boundary. It defines what later methodology review and no-lookahead controls
must cover before any reproduction or implementation route.

This Step 6 shortlist boundary depends on those prior gates only as
non-approving routing context. No source is approved. No ETF universe is
approved. No benchmark or cash proxy is approved. Public availability,
familiar tickers, issuer metadata, FRED documentation, or client-library
support does not approve data use, local snapshots, redistribution,
reproduction, validation, implementation, or trading use.

## Recommended Next Gate

Phase 33 Step 7 adds the data-source terms/license review boundary in
[`phase33_broad_etf_data_source_terms_license_review_boundary.md`](phase33_broad_etf_data_source_terms_license_review_boundary.md).
It reviews public terms, license, caching, private-repo, redistribution,
derived-publication, API, and offline-use constraints for candidate source
categories without approving any source.

Recommended next docs-only gate after Step 7: final source shortlist decision
boundary. An acceptable alternate next docs-only gate is a moving-average
evidence intake plan after an evidence/source package if the next prompt
prioritizes methodology literature before source narrowing. A data
storage/fixture policy boundary should wait until source terms are acceptable.
A reproduction protocol boundary should wait until source, universe,
benchmark, cash proxy, and data policy choices are later approved. A
result-review template should wait until a protocol is later approved.

No next gate may acquire data, ingest data, approve a source, approve a
universe, approve a benchmark, approve a cash proxy, approve methodology,
approve parameters, reproduce, validate, backtest, compute signals, implement
an evaluator, or create trading implications unless a later phase explicitly
scopes and approves that narrower work.

## Explicit Non-Goals

This phase does not perform or authorize:

- universe approval
- benchmark approval
- cash proxy approval
- source approval
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
- no approved methodology or parameters
- no acquired data
- no project-local deterministic reproduction
- no no-lookahead audit
- no production threshold/config provenance
- no implementation-scope approval
- no evaluator tests
- no approved data license or offline-use path
- no approved local snapshot/versioning policy
- no approved total-return versus price-return decision
- no approved dividend/reinvestment treatment
- no approved corporate-action handling policy
- no approved correction/revision policy
- no approved point-in-time/as-of policy
- no approved ETF universe shortlist
- no approved inactive-fund, delisting, merger, or ticker-change policy
- no approved benchmark/cash-proxy frequency alignment rule
- no approved cash-rate conversion or compounding rule
- no approved transaction cost, slippage, spread, rebalance, fund-expense, or
  friction assumption
- no result-review template
- no promotion/rejection decision
- no trading implication or production threshold
