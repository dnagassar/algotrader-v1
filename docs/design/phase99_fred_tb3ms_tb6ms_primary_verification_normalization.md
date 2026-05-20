# Phase 99 - FRED TB3MS/TB6MS Primary Verification Normalization

## Purpose

This document normalizes externally produced primary-verification findings for
two FRED T-bill candidate series into the deterministic repo documentation
trail as advisory material only:

- `TB3MS`: 3-Month Treasury Bill Secondary Market Rate, Discount Basis
- `TB6MS`: 6-Month Treasury Bill Secondary Market Rate, Discount Basis

The external output reportedly used official or primary sources where
available, including FRED, ALFRED, Federal Reserve H.15, and related
documentation. Phase 99 does not independently reopen those pages, call FRED,
call Federal Reserve services, download data, inspect observations, create
local data files, add credentials, add tests, add production behavior, or
change any source, replay, broker, advisory, governance, or runtime code.

The Perplexity output remains external advisory input. It is not approval,
legal review, point-in-time proof, source approval, data approval, benchmark
approval, cash-proxy approval, rate-source approval, or trading readiness.

## Normalization Boundary

Phase 99 may normalize TB3MS/TB6MS verification findings only.

It must not approve:

- FRED
- `TB3MS`
- `TB6MS`
- any FRED series
- any benchmark
- any cash proxy
- any rate source
- any data
- any source
- any methodology
- any parameter set
- any evidence
- any return-construction policy
- any no-lookahead policy
- any cost/friction model
- any strategy validation
- any trading use

Reported official pages are primary-verification leads only. A reported FRED
series ID is not a cash proxy, benchmark, source approval, data approval,
conversion rule, publication-timing rule, no-lookahead proof, or strategy
input.

## Normalized Status Vocabulary

Allowed `normalized_status` values in this document are:

- `reject_for_now`
- `context_only`
- `candidate_needs_more_evidence`
- `candidate_for_later_series_review`

Forbidden statuses are:

- `approved`
- `validated`
- `series_approved`
- `benchmark_approved`
- `cash_proxy_approved`
- `data_approved`
- `point_in_time_safe`
- `strategy_ready`
- `trading_ready`

The allowed statuses route later review only. They do not authorize FRED API
calls, data downloads, local snapshots, fixture use, raw-row storage, source
use, benchmark/cash comparison, return construction, no-lookahead claims,
scoring, ranking, recommendation, strategy validation, or trading behavior.

## Normalized Two-Series Table

The table records reported official-source findings as advisory
primary-verification material only. Findings are normalized into repo language;
they are not treated as independently proven by this phase.

| normalized_id | fred_series_id | series_title | candidate_role | official_series_page_status | official_data_page_status | source_release_status | units_frequency_status | observation_span_status | last_updated_metadata_status | realtime_vintage_status | alfred_status | publication_timing_status | revision_status | missing_stale_status | conversion_question_status | rights_terms_status | normalized_status | blockers | allowed_next_step | non_claims |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phase99_tb3ms_primary_verification | `TB3MS` | 3-Month Treasury Bill Secondary Market Rate, Discount Basis | `t_bill_proxy_candidate`; `cash_risk_free_proxy_candidate` for later review only | FRED series page reportedly found. | FRED data/table page reportedly found. | Source reportedly Board of Governors via H.15 Selected Interest Rates. | Units reportedly Percent; frequency Monthly; seasonal adjustment Not Seasonally Adjusted; monthly average of business days; discount basis. | Observation span reportedly starts 1934-01-01. | FRED table page reportedly showed last-updated metadata. | Real-time/vintage notes reportedly identified, but exact usable as-of procedure remains unresolved. | ALFRED page reportedly found; vintages reportedly start 2002-02-04. | H.15/FRED publication timing alignment unresolved; observation month is not availability timestamp. | Revision behavior unresolved. | Missing, stale, delayed, or suppressed value handling unresolved. | Discount-basis conversion unresolved; conversion to bond-equivalent yield, effective yield, daily return, or monthly return not approved. | Rights, terms, attribution, local/internal/commercial use, raw storage, public repo redistribution, and citation remain unresolved. | `candidate_for_later_series_review` | External advisory input only; no independent repo proof; timing, vintage coverage before 2002, revisions, missing/stale handling, rights, legal clearance, conversion, compounding, calendar, and no-lookahead handling unresolved. | Docs-only later series review of official FRED, ALFRED, H.15, rights, timing, revision, missing/stale, and discount-basis conversion material; no API call or download. | Not FRED approval; not TB3MS approval; not series approval; not cash proxy approval; not benchmark approval; not rate-source approval; not data approval; not point-in-time safe. |
| phase99_tb6ms_primary_verification | `TB6MS` | 6-Month Treasury Bill Secondary Market Rate, Discount Basis | `t_bill_proxy_candidate`; `cash_risk_free_proxy_candidate` for later review only | FRED series page reportedly found. | FRED data/table page reportedly found. | Source reportedly Board of Governors via H.15 Selected Interest Rates. | Units reportedly Percent; frequency Monthly; seasonal adjustment Not Seasonally Adjusted; monthly average of business days; discount basis. | Observation span reportedly starts 1958-12-01. | FRED table page reportedly showed last-updated metadata. | Real-time/vintage notes reportedly identified, but exact usable as-of procedure remains unresolved. | ALFRED page reportedly found; vintages reportedly start 2002-02-04. | H.15/FRED publication timing alignment unresolved; observation month is not availability timestamp. | Revision behavior unresolved. | Missing, stale, delayed, or suppressed value handling unresolved. | Discount-basis conversion unresolved; conversion to bond-equivalent yield, effective yield, daily return, or monthly return not approved. | Rights, terms, attribution, local/internal/commercial use, raw storage, public repo redistribution, and citation remain unresolved. | `candidate_for_later_series_review` | External advisory input only; no independent repo proof; timing, vintage coverage before 2002, revisions, missing/stale handling, rights, legal clearance, conversion, compounding, calendar, and no-lookahead handling unresolved. | Docs-only later series review of official FRED, ALFRED, H.15, rights, timing, revision, missing/stale, and discount-basis conversion material; no API call or download. | Not FRED approval; not TB6MS approval; not series approval; not cash proxy approval; not benchmark approval; not rate-source approval; not data approval; not point-in-time safe. |

## TB3MS Normalized Findings

As advisory external verification findings only, Phase 99 records:

- the FRED series page was reportedly found
- the FRED data/table page was reportedly found
- the source is reportedly Board of Governors via H.15 Selected Interest Rates
- units are reportedly Percent
- frequency is reportedly Monthly
- seasonal adjustment is reportedly Not Seasonally Adjusted
- the observation span reportedly starts 1934-01-01
- the FRED table page reportedly showed last-updated metadata
- the ALFRED page was reportedly found
- ALFRED vintages reportedly start 2002-02-04
- the series is reportedly a monthly average of business days on a discount
  basis
- discount-basis conversion is unresolved
- H.15/FRED publication timing alignment is unresolved
- revision behavior is unresolved
- missing and stale handling is unresolved
- rights and terms remain unresolved for local, internal, and commercial use
- normalized status remains `candidate_for_later_series_review`

These findings are not TB3MS approval, FRED approval, data approval, cash-proxy
approval, benchmark approval, rate-source approval, point-in-time proof, or
trading readiness.

## TB6MS Normalized Findings

As advisory external verification findings only, Phase 99 records:

- the FRED series page was reportedly found
- the FRED data/table page was reportedly found
- the source is reportedly Board of Governors via H.15 Selected Interest Rates
- units are reportedly Percent
- frequency is reportedly Monthly
- seasonal adjustment is reportedly Not Seasonally Adjusted
- the observation span reportedly starts 1958-12-01
- the FRED table page reportedly showed last-updated metadata
- the ALFRED page was reportedly found
- ALFRED vintages reportedly start 2002-02-04
- the series is reportedly a monthly average of business days on a discount
  basis
- discount-basis conversion is unresolved
- H.15/FRED publication timing alignment is unresolved
- revision behavior is unresolved
- missing and stale handling is unresolved
- rights and terms remain unresolved for local, internal, and commercial use
- normalized status remains `candidate_for_later_series_review`

These findings are not TB6MS approval, FRED approval, data approval, cash-proxy
approval, benchmark approval, rate-source approval, point-in-time proof, or
trading readiness.

## Official-Docs-Found Summary

The external verification output reportedly found or referenced these official
or primary pages and documentation categories:

- TB3MS FRED series page
- TB3MS FRED data/table page
- TB3MS ALFRED page
- TB6MS FRED series page
- TB6MS FRED data/table page
- TB6MS ALFRED page
- FRED H.15 release page
- ALFRED H.15 release page
- Federal Reserve Board H.15 page
- Federal Reserve Board Data Download Program H.15 page
- FRED, FRED help, and ALFRED general documentation where relevant to series
  metadata, releases, vintages, terms, citation, and use guidance

This summary does not paste raw external text and does not verify page contents
inside the repo. The official-docs-found summary remains advisory until a later
phase performs direct primary-source review under an explicit scope.

## Rights And Terms Caveats

Phase 99 records these unresolved rights and terms caveats:

- FRED can include public-domain and copyrighted series.
- FRED ethical-use guidance does not equal legal clearance.
- underlying source or provider rights may control.
- H.15 data questions may need to be directed to the Board.
- attribution and citation expectations remain unresolved.
- public repo redistribution remains unresolved.
- internal or commercial algorithmic research use remains unresolved.

No legal conclusion is made. No local storage, raw-row storage, public repo
redistribution, derived-series publication, internal research use, commercial
use, or citation policy is approved.

## Point-In-Time And No-Lookahead Caveats

Phase 99 records these unresolved point-in-time and no-lookahead caveats:

- observation month is not an availability timestamp.
- monthly values are averages of business days.
- Board H.15 daily posting timing does not automatically equal FRED monthly
  availability.
- FRED last-updated metadata is not a complete point-in-time model.
- ALFRED vintage existence does not prove complete point-in-time safety.
- vintage coverage appears to start in 2002, leaving pre-2002 point-in-time
  limitations.
- revision magnitude and frequency remain unresolved.
- missing and stale handling remains unresolved.

No TB3MS or TB6MS value may affect a future strategy-relative, cash-return,
excess-return, or benchmark/cash claim until a later phase proves the value was
available under the selected as-of rule before the relevant modeled decision.

## Conversion And Compounding Caveats

Phase 99 records these unresolved conversion and compounding caveats:

- `TB3MS` and `TB6MS` are discount-basis rates, not returns.
- discount-basis rates are not directly investable cash returns.
- monthly averages are not daily paths.
- conversion to bond-equivalent yield, effective yield, daily return, or
  monthly return remains unresolved.
- any future conversion must be vintage-aware.
- any future conversion must document compounding, calendar, and availability
  timing.

No discount-basis conversion, daily accrual rule, monthly return rule,
calendar alignment, compounding convention, rate-to-return method, or
cash-proxy construction is approved.

## Later-Review Ordering Recommendation

Recommended later-review order, not approval:

1. `TB3MS` first, because its longer history and common 3-month T-bill proxy
   role make it the natural first metadata and methodology candidate.
2. `TB6MS` second or in parallel, because it shares the H.15 and
   discount-basis structure and adds tenor comparison.

This ordering does not rank, score, recommend for use, select, approve,
validate, or make either series ready for data acquisition, local storage,
return construction, no-lookahead claims, strategy validation, or trading.

## Relationship To Prior Phases

Phase 90 defined benchmark and cash timing boundaries. Phase 99 does not
approve a benchmark, cash proxy, cash-rate series, publication-timing rule,
revision rule, compounding rule, or cash-return convention.

Phase 96 defined FRED benchmark/cash/rate normalization readiness. Phase 99
normalizes reported TB3MS/TB6MS primary-verification findings under that
readiness boundary, but it does not approve FRED, either series, any rate
source, source use, data use, or no-lookahead handling.

Phase 97 defined the FRED candidate series intake plan. Phase 99 fills two
candidate records with advisory reported primary-verification findings only.
Candidate intake does not approve FRED. Candidate intake does not approve any
series. A series ID is not a cash proxy.

Phase 98 normalized FRED candidate series discovery output. Phase 99 narrows
from discovery to two T-bill candidate series and records reported official
FRED, ALFRED, and H.15 verification findings. FRED and ALFRED pages do not
solve conversion, timing, legal, revision, missing-value, or no-lookahead
issues.

FRED data must not enter normal pytest through network calls, downloaded files,
local data files, fixtures, credentials, or real observations. Normal
`python -m pytest` must remain offline and credential-free.

## Explicit Non-Claims

Phase 99 is:

- not FRED approval
- not TB3MS approval
- not TB6MS approval
- not FRED series approval
- not benchmark approval
- not cash proxy approval
- not rate-source approval
- not source approval
- not data approval
- not evidence approval
- not return-construction approval
- not no-lookahead approval
- not cost/friction approval
- not liquidity approval
- not strategy validation
- not trading readiness

It adds no FRED approval, TB3MS approval, TB6MS approval, FRED series
approval, benchmark approval, cash proxy approval, rate-source approval, source
approval, data approval, vendor approval, universe approval, methodology
approval, parameter approval, evidence approval, return-construction approval,
no-lookahead approval, cost/friction approval, liquidity approval, strategy
validation, real data ingestion, real data files, FRED API call, Federal
Reserve API call, data download, raw FRED observation, ETF ticker selection,
benchmark comparison, ranking, scoring, recommendation, candidate-discovery
behavior in code, replay metric, manifest-to-planning bridge,
signal/evaluator behavior, broker/order/fill/portfolio/runtime behavior, LLM
call, network call, market-data call, dashboard/advisory/AI integration, paper
behavior, live behavior, or trading behavior.

## Decision

Decision: advisory TB3MS/TB6MS primary-verification normalization only.

`TB3MS` and `TB6MS` remain `candidate_for_later_series_review`. They are not
approved, validated, selected, point-in-time safe, cash proxies, benchmarks,
rate sources, data sources, return-construction inputs, strategy inputs, or
trading inputs.

No production code or tests changed. No real data was added. No FRED API calls
or downloads occurred. Normal pytest remains offline and credential-free.

## Remaining Blockers

- no approved FRED use
- no approved TB3MS use
- no approved TB6MS use
- no approved FRED series
- no approved source
- no approved data
- no approved benchmark
- no approved cash proxy
- no approved rate source
- no approved per-series legal or rights review
- no approved local storage, public repo, redistribution, or citation policy
- no approved H.15 publication timing alignment
- no approved FRED monthly availability timing
- no approved ALFRED/vintage procedure
- no approved pre-2002 point-in-time handling
- no approved revision behavior
- no approved missing or stale value policy
- no approved discount-basis conversion
- no approved bond-equivalent yield, effective yield, daily return, or monthly
  return conversion
- no approved calendar alignment or compounding convention
- no approved known-before-decision rule
- no approved return-construction policy
- no approved no-lookahead/as-of policy
- no approved normal-pytest FRED dependency
- no approved strategy-validation claim
- no approved trading-readiness claim

## Follow-Up Recommendation

The likely next phase should be an inspection checkpoint deciding whether to
continue FRED documentation work with H.15 discount-basis formula
verification, ALFRED vintage procedure mapping, or to pause before more docs.
