# Phase 102 - H.15 Daily Quote / Monthly Averaging Normalization

## Purpose

This document normalizes externally produced H.15 daily quote and monthly
averaging discovery output into the deterministic repo documentation trail as
advisory methodology context only.

The external output reportedly used official or primary source categories where
available, including Federal Reserve H.15 pages, H.15 Technical Q&A material,
Federal Reserve Data Download Program context, FRED `TB3MS`/`TB6MS` context,
and Treasury daily bill-rate descriptions. Phase 102 does not independently
reopen those pages, call FRED, call Federal Reserve services, call Treasury
services, download data, inspect observations, create local data files, add
credentials, add tests, add production behavior, implement averaging,
implement formulas, or change any source, replay, broker, advisory,
governance, or runtime code.

The Perplexity output remains external advisory input. It is not approval,
legal review, source approval, data approval, methodology approval,
point-in-time proof, cash-proxy approval, benchmark approval, rate-source
approval, return-construction approval, strategy validation, or trading
readiness.

## Normalization Boundary

Phase 102 may normalize H.15 daily quote and monthly averaging findings only.

It must not approve:

- FRED
- H.15
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

Reported H.15 averaging and posting findings are documentation context only.
They do not approve FRED, H.15, any series, any source, any data, any
implementation, any conversion method, any return construction, any
point-in-time treatment, any no-lookahead treatment, or any trading use.

## Allowed Next-Step Vocabulary

Allowed `allowed_next_step` values in this document are:

- `needs_repo_normalization`
- `needs_more_primary_docs`
- `needs_support_question`
- `reject_for_now`

Forbidden `allowed_next_step` values are:

- `approved`
- `validated`
- `cash_proxy_approved`
- `return_construction_approved`
- `point_in_time_safe`
- `strategy_ready`
- `trading_ready`

The allowed values route later review only. They do not authorize FRED API
calls, Federal Reserve API calls, Treasury API calls, data downloads, local
snapshots, fixture use, raw-row storage, source use, benchmark/cash comparison,
return construction, no-lookahead claims, scoring, ranking, recommendation,
strategy validation, or trading behavior.

## Normalized Findings Table

The table records reported official-source findings as advisory methodology
context only. Findings are normalized into repo language; they are not
independently proven by this phase.

| normalized_id | topic | official_source_status | finding_summary | applies_to_daily_H15 | applies_to_TB3MS | applies_to_TB6MS | remaining_uncertainty | allowed_next_step | non_claims |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phase102_h15_posting_schedule | H.15 posting schedule | H.15 daily page or Board release context reportedly found. | H.15 is reportedly posted each business day, Monday through Friday, at 4:15 p.m. | Yes, as publication-time context only. | Context only; does not prove FRED monthly availability. | Context only; does not prove FRED monthly availability. | Posting time is not the underlying quote observation time and does not resolve revisions, FRED ingestion, or point-in-time safety. | `needs_repo_normalization` | Not H.15 approval; not FRED approval; not source approval; not no-lookahead approval. |
| phase102_h15_averaging_technical_qa | H.15 weekly and monthly averaging | H.15 Technical Q&A reportedly found. | The Technical Q&A reportedly says weekly and monthly averages are averages of all non-missing values during the period. | Yes, for official H.15 aggregate averages as documentation context. | Context only; does not prove `TB3MS` FRED transformation or availability. | Context only; does not prove `TB6MS` FRED transformation or availability. | Missing-value exclusion is reported, but missing detection, stale detection, partial periods, revisions, and FRED provenance remain unresolved. | `needs_repo_normalization` | Not averaging implementation; not return-construction approval; not point-in-time proof. |
| phase102_h15_business_day_average | H.15 business-day averages | H.15 daily page reportedly found. | The H.15 page reportedly says weekly, monthly, and annual rates are averages of business days unless otherwise noted. | Yes, for official H.15 aggregate averages as documentation context. | Context only; candidate remains unapproved. | Context only; candidate remains unapproved. | Need direct primary-source review or support-confirmable confirmation before implementation; does not define daily quote construction. | `needs_more_primary_docs` | Not methodology approval; not data approval; not cash proxy approval. |
| phase102_h15_t_bill_discount_basis_scope | H.15 Treasury bill scope | H.15 page reportedly found. | H.15 reportedly includes 4-week, 3-month, 6-month, and 1-year Treasury bill secondary-market rates quoted on a discount basis. | Yes, as classification context only. | Relevant as candidate-only classification context. | Relevant as candidate-only classification context. | Discount-basis classification does not define return conversion, quote side, quote source, maturity mapping, or FRED monthly provenance. | `needs_more_primary_docs` | Not TB3MS approval; not TB6MS approval; not conversion approval. |
| phase102_daily_t_bill_quote_construction_gap | Daily Treasury bill quote construction | Current official methodology detail reportedly remains incomplete. | Daily T-bill rate construction remains unresolved: input source, executed trades versus quotes, quote side, time of day, averaging versus representative quote, fallback, cleaning, unusual-market-day treatment, and maturity mapping. | Yes, unresolved. | Unresolved for the daily observations that may feed the candidate. | Unresolved for the daily observations that may feed the candidate. | Need archived/current Board H.15 methodology notes or support-confirmable Board/Federal Reserve answer. | `needs_support_question` | Not daily quote construction approval; not source approval; not data approval. |
| phase102_fred_monthly_provenance_gap | FRED monthly provenance | FRED/H.15 context exists from prior phases, but provenance remains unresolved. | It remains unresolved whether FRED `TB3MS`/`TB6MS` are direct Board monthly packages or FRED-constructed monthly transformations. | Context only; H.15 aggregate rule does not settle FRED handling. | Unresolved. | Unresolved. | FRED transformation, ingestion timing, vintage mapping, missing-day handling, and partial-period handling remain unresolved; numeric resemblance is not proof of identity. | `needs_more_primary_docs` | Not FRED approval; not FRED series approval; not point-in-time proof. |
| phase102_revision_missing_stale_gap | Revision, missing, and stale uncertainty | No explicit H.15 Treasury bill daily-rate revision, correction, or stale-quote policy was reportedly found. | Missing values are reportedly excluded from aggregates, but missing/stale detection rules, correction behavior, and discontinued-series implications remain unresolved. | Yes, unresolved. | Unresolved for candidate use. | Unresolved for candidate use. | Discontinued Data Download Program availability does not prove stable definitions for active bill series. | `needs_more_primary_docs` | Not revision policy approval; not missing-value policy approval; not stale-value policy approval. |
| phase102_pit_no_lookahead_gap | PIT and no-lookahead risk | H.15 posting and FRED/ALFRED context exists from prior phases, but availability remains unresolved. | Monthly averages may not be available until after the period ends; daily 4:15 p.m. posting does not prove earlier decision-time availability; FRED ingestion and ALFRED vintage selection remain separate blockers. | Yes, unresolved for modeled decision timing. | Unresolved. | Unresolved. | Revised current series may not equal real-time available data. | `needs_more_primary_docs` | Not no-lookahead approval; not point-in-time safe; not strategy validation. |
| phase102_treasury_daily_bill_rate_relationship | Treasury daily bill-rate relationship | Treasury primary-source pages may describe Daily Treasury Bill Rates, but linkage to H.15 remains unproven. | Treasury pages may describe indicative closing market bid quotations on recently auctioned Treasury bills. Do not treat that description as definitive H.15 methodology without more primary confirmation. | Possible context only. | Possible context only; unproven. | Possible context only; unproven. | Need primary confirmation connecting Treasury daily bill-rate descriptions to H.15 secondary-market T-bill series, if such a connection exists. | `needs_more_primary_docs` | Not H.15 methodology approval; not source approval; not evidence approval. |

## Official Averaging Findings

As advisory external findings only, Phase 102 records:

- H.15 Technical Q&A reportedly says weekly and monthly averages are averages
  of all non-missing values during the period.
- H.15 daily-page context reportedly says weekly, monthly, and annual rates
  are averages of business days unless otherwise noted.
- These findings support treating official H.15 weekly and monthly aggregate
  rates as simple arithmetic averages of non-missing business-day values at
  the documentation level.
- This does not approve any implementation, return construction, conversion,
  availability rule, or point-in-time treatment.

No averaging implementation, formula implementation, FRED transformation rule,
cash-return rule, benchmark rule, or no-lookahead rule is approved.

## H.15 Posting Schedule

As advisory external publication-context findings only, Phase 102 records:

- H.15 is reportedly posted daily Monday through Friday at 4:15 p.m.
- The H.15 posting time is not the same as the underlying quote observation
  time.
- The H.15 posting time does not resolve revision behavior, FRED ingestion
  timing, ALFRED vintage selection, or point-in-time safety.

No value may be treated as known before a modeled decision solely because H.15
has a reported daily posting schedule.

## Daily Treasury Bill Quote Construction Gaps

Phase 102 records these unresolved questions about daily H.15 Treasury bill
secondary-market rates:

- input source for daily T-bill secondary-market rates
- executed trades versus dealer quotes versus survey input
- bid, ask, mid, or other quote side
- time of day of quote selection
- whether daily values are averages, representative quotes, or single
  observations
- fallback rules
- data cleaning rules
- unusual-market-day treatment
- maturity mapping for 3-month and 6-month bills
- current official methodology note availability

H.15 documents constant-maturity Treasury methodology more fully, but that
does not automatically apply to Treasury bill secondary-market discount-basis
series. No daily quote construction rule is approved.

## Monthly Averaging And Provenance Gaps

Phase 102 records:

- official H.15 aggregate rates appear to use averages of non-missing
  business-day values
- it remains unresolved whether `TB3MS` and `TB6MS` on FRED are direct Board
  monthly packages or FRED-constructed monthly transformations
- FRED transformation and provenance remain unresolved
- missing-day and partial-period handling remain incompletely specified
- numeric resemblance between a computed monthly average and a published FRED
  value is not proof of transformation identity

`TB3MS` and `TB6MS` remain candidate-only. H.15 aggregate averaging context
does not approve FRED, either FRED series, a cash proxy, a benchmark, a rate
source, a source, data, conversion, return construction, or no-lookahead
treatment.

## Revision, Missing, And Stale Uncertainty

Phase 102 records:

- no explicit H.15 revision or correction policy for Treasury bill daily rates
  was reportedly found
- no explicit stale quote policy was reportedly found
- missing values are reportedly excluded from aggregate averages, but
  missing/stale detection rules remain unresolved
- discontinued Data Download Program availability does not prove stable
  definitions for active Treasury bill series

No revision policy, correction policy, missing-value policy, stale-value
policy, carry-forward rule, interpolation rule, blocking rule, or replacement
rule is approved.

## No-Lookahead And Point-In-Time Risks

Phase 102 records these no-lookahead and point-in-time risks:

- monthly averages may not be available until after the period ends
- using monthly values during the month would violate no-lookahead
- daily posting at 4:15 p.m. does not prove earlier decision-time availability
- FRED ingestion timing remains a separate blocker
- ALFRED vintage selection remains a separate blocker
- revised current series may not equal real-time available data

No `TB3MS` or `TB6MS` value may affect a future strategy-relative,
cash-return, excess-return, or benchmark/cash claim until a later phase proves
the value was available under the selected as-of rule before the relevant
modeled decision.

## Relationship To Treasury Daily Bill-Rate Description

Phase 102 records that Treasury primary-source pages may describe Daily
Treasury Bill Rates as indicative closing market bid quotations on recently
auctioned Treasury bills.

The relationship between Treasury daily bill-rate descriptions and H.15 bill
series remains unproven in this phase. Treasury descriptions must not be
treated as definitive H.15 methodology without more primary confirmation.

No Treasury page, H.15 page, or FRED page is approved as a source, data feed,
methodology, evidence package, return-construction input, cash proxy, or
benchmark in this phase.

## Later-Review Recommendation

Recommended later-review path, not approval:

1. Normalize the official H.15 averaging rule as documentation context only.
2. Keep daily T-bill quote construction unresolved.
3. Next external work should either search for archived/current H.15
   methodology notes or a Board support-confirmable answer on daily T-bill
   quote construction, or pause FRED and return to broader ETF source work if
   further H.15 docs become churn.
4. Do not implement averaging or conversions yet.
5. Keep ALFRED vintage mapping separate and later.

This recommendation does not rank, score, select, recommend for use, approve,
validate, or make FRED, H.15, `TB3MS`, `TB6MS`, any FRED series, any source,
any data, any benchmark, any cash proxy, any rate source, any conversion, any
return construction, any no-lookahead policy, any strategy, or any trading
path ready for implementation.

## Relationship To Prior Phases

Phase 90 defined benchmark and cash timing boundaries. Phase 102 does not
approve a benchmark, cash proxy, cash-rate series, publication-timing rule,
revision rule, compounding rule, or cash-return convention.

Phase 96 defined FRED benchmark/cash/rate normalization readiness. Phase 102
normalizes reported H.15 averaging and daily quote construction findings under
that readiness boundary, but it does not approve FRED, H.15, any series, any
rate source, source use, data use, conversion, or no-lookahead handling.

Phase 97 defined the FRED candidate series intake plan. Phase 102 supplies
methodology-context material for later candidate review only. Candidate intake
does not approve FRED. Candidate intake does not approve any series. A series
ID is not a cash proxy.

Phase 98 normalized FRED candidate series discovery output. Phase 102 narrows
from candidate discovery to reported H.15 daily posting, aggregate averaging,
and daily T-bill quote construction gaps. H.15 averaging context does not solve
legal, vintage, timing, missing, stale, conversion, or data-use questions.

Phase 99 normalized reported `TB3MS`/`TB6MS` primary-verification findings.
Phase 102 adds advisory averaging and daily quote construction context for
those candidate series only. It does not prove that `TB3MS` or `TB6MS` are
point-in-time safe.

Phase 101 normalized H.15 discount-basis formula and convention findings.
Phase 102 complements that formula context with aggregate averaging context
and daily quote construction gaps. H.15 averaging context does not approve
return construction, and the series IDs remain not cash proxies.

FRED/H.15 data must not enter normal pytest through network calls, downloaded
files, local data files, fixtures, credentials, or real observations. Normal
`python -m pytest` must remain offline and credential-free.

## Explicit Non-Claims

Phase 102 is:

- not FRED approval
- not H.15 approval
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

It adds no FRED approval, H.15 approval, TB3MS approval, TB6MS approval, FRED
series approval, benchmark approval, cash proxy approval, rate-source
approval, source approval, data approval, vendor approval, universe approval,
methodology approval, parameter approval, evidence approval,
return-construction approval, no-lookahead approval, cost/friction approval,
liquidity approval, strategy validation, real data ingestion, real data files,
FRED API call, Federal Reserve API call, Treasury API call, data download, raw
FRED observation, H.15 observation, averaging implementation, formula
implementation, conversion method, return construction, ETF ticker selection,
benchmark comparison, ranking, scoring, recommendation, candidate-discovery
behavior in code, replay metric, manifest-to-planning bridge,
signal/evaluator behavior, broker/order/fill/portfolio/runtime behavior, LLM
call, network call, market-data call, dashboard/advisory/AI integration, paper
behavior, live behavior, or trading behavior.

## Decision

Decision: advisory H.15 daily quote and monthly averaging normalization only.

The reported H.15 averaging rules are normalized as documentation context
only. Daily Treasury bill quote construction remains unresolved. `TB3MS` and
`TB6MS` remain candidate-only. They are not approved, validated, selected,
point-in-time safe, cash proxies, benchmarks, rate sources, data sources,
return-construction inputs, strategy inputs, or trading inputs.

No averaging implementation was added. No formula implementation was added. No
conversion method was approved. No FRED series or cash proxy was approved. No
production code or tests changed. No real data was added. No FRED/H.15 API
calls or downloads occurred. Normal pytest remains offline and
credential-free.

## Remaining Blockers

- no approved FRED use
- no approved H.15 use
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
- no approved current H.15 technical methodology note
- no approved daily quote construction rule
- no approved daily quote time, input type, quote side, fallback, or cleaning
  rule
- no approved unusual-market-day treatment
- no approved T-bill maturity mapping rule
- no approved FRED transformation or monthly availability rule
- no approved H.15 publication timing alignment
- no approved FRED ingestion timing
- no approved ALFRED/vintage procedure
- no approved pre-2002 point-in-time handling
- no approved revision behavior
- no approved missing or stale value policy
- no approved discount-basis conversion
- no approved bond-equivalent yield, effective yield, daily return, or monthly
  return conversion
- no approved calendar alignment, maturity, roll, or compounding convention
- no approved known-before-decision rule
- no approved return-construction policy
- no approved no-lookahead/as-of policy
- no approved normal-pytest FRED or H.15 dependency
- no approved strategy-validation claim
- no approved trading-readiness claim

## Follow-Up Recommendation

The likely next step should be an inspection checkpoint deciding whether to
search for deeper H.15 quote-construction methodology, map ALFRED vintage
procedure, or pause FRED work and return to broader ETF source review.
