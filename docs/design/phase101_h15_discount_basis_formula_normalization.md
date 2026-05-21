# Phase 101 - H.15 Discount-Basis Formula Normalization

## Purpose

This document normalizes externally produced H.15 Treasury bill
discount-basis formula and convention discovery output into the deterministic
repo documentation trail as advisory methodology evidence only.

The external output reportedly used official or primary source categories
where available, including TreasuryDirect bill pricing documentation,
Treasury interest-rate material, Federal Reserve H.15 pages, Federal Reserve
Data Download Program pages, historical H.15 PDF or footnote material, FRED
`TB3MS`/`TB6MS` pages, and the FRED H.15 release page. Phase 101 does not
independently reopen those pages, call FRED, call Federal Reserve services,
call Treasury services, download data, inspect observations, create local data
files, add credentials, add tests, add production behavior, implement a
formula, or change any source, replay, broker, advisory, governance, or
runtime code.

The Perplexity output remains external advisory input. It is not approval,
legal review, source approval, data approval, methodology approval,
point-in-time proof, cash-proxy approval, benchmark approval, rate-source
approval, return-construction approval, strategy validation, or trading
readiness.

## Normalization Boundary

Phase 101 may normalize H.15 discount-basis formula and convention findings
only.

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

Reported official formula or convention findings are advisory methodology
context only. A reported discount-basis pricing convention is not a cash
proxy, benchmark, source approval, data approval, return-construction rule,
publication-timing rule, no-lookahead proof, or strategy input.

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
snapshots, fixture use, raw-row storage, source use, benchmark/cash
comparison, return construction, no-lookahead claims, scoring, ranking,
recommendation, strategy validation, or trading behavior.

## Normalized Formula And Convention Table

The table records reported official-source findings as advisory
methodology-context material only. Findings are normalized into repo language;
they are not independently proven by this phase.

| normalized_id | topic | official_source_status | finding_summary | formula_or_convention | applies_to_TB3MS | applies_to_TB6MS | remaining_uncertainty | allowed_next_step | non_claims |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phase101_treasurydirect_bill_price_formula | Treasury bill price from discount rate | TreasuryDirect bill pricing documentation reportedly found. | TreasuryDirect reportedly gives a bill price formula using face value, discount rate, actual days to maturity, and a 360-day year. | Reported formula, rendered as ASCII: `Price = Face value * (1 - (discount rate * days to maturity) / 360)`. This indicates a bank-discount or discount-basis quote convention. | Contextually relevant because `TB3MS` is reportedly a secondary-market T-bill discount-basis quotation, but the exact series conversion remains unresolved. | Contextually relevant because `TB6MS` is reportedly a secondary-market T-bill discount-basis quotation, but the exact series conversion remains unresolved. | Formula page is not a complete current H.15 methodology manual; it does not define daily quote construction, monthly averaging, FRED transformation, vintages, availability timing, or return construction. | `needs_repo_normalization` | Not H.15 approval; not FRED approval; not TB3MS approval; not TB6MS approval; not cash proxy approval; not return-construction approval. |
| phase101_discount_basis_convention | Discount-basis convention | Treasury/Fed materials reportedly distinguish discount-basis bill rates from other yield and return measures. | Discount basis appears to follow the Treasury/Fed bank-discount convention with a 360-day year and actual days to maturity. | Quote/pricing convention only; not a realized return formula. | Applies as quote-methodology context only. | Applies as quote-methodology context only. | Exact Board H.15 convention wording for current daily secondary-market T-bill observations remains unresolved. | `needs_more_primary_docs` | Not methodology approval; not evidence approval; not cash proxy approval; not trading readiness. |
| phase101_h15_secondary_market_classification | H.15 secondary-market classification | Current H.15 and FRED pages reportedly label Treasury bills as secondary market and discount basis. | `TB3MS` and `TB6MS` are associated with Board of Governors / H.15 Selected Interest Rates, not Treasury auction results. | Secondary-market discount-basis quote classification. | Yes, as classification context only. | Yes, as classification context only. | Daily input construction remains unresolved, including whether observations are survey quotes, executed trades, dealer quotes, bid/ask/mid, or another input. | `needs_more_primary_docs` | Not source approval; not data approval; not rate-source approval; not series approval. |
| phase101_monthly_nsa_classification | Monthly not-seasonally-adjusted classification | FRED pages reportedly identify both series as monthly and not seasonally adjusted. | `TB3MS` and `TB6MS` are reportedly monthly, not-seasonally-adjusted averages of daily H.15 secondary-market T-bill discount-basis quotations. | Monthly average classification only; not a daily path and not a return series. | Yes, as candidate-only metadata context. | Yes, as candidate-only metadata context. | Exact monthly aggregation, missing-day handling, holiday handling, correction handling, and whether aggregation is FRED-specific or Board-published remain unresolved. | `needs_more_primary_docs` | Not point-in-time proof; not return-construction approval; not cash proxy approval. |
| phase101_not_bey_not_total_return | Distinction from BEY and return measures | Treasury/Fed materials reportedly distinguish discount-basis rates from bond-equivalent yields and investor return measures. | Official sources located do not define `TB3MS` or `TB6MS` as investable total returns, bond-equivalent yields, money-market total returns, or directly investable cash returns. | Negative classification: discount-basis quote, not BEY or total return. | Yes, as a non-claim. | Yes, as a non-claim. | Future conversion would need day-count, compounding, maturity, roll, calendar, and availability timing documentation. | `needs_more_primary_docs` | Not bond-equivalent yield approval; not effective-yield approval; not daily-return approval; not monthly-return approval. |
| phase101_daily_quote_construction_gap | Daily quote construction uncertainty | Current official material reportedly found does not fully define daily H.15 T-bill quote construction. | Daily observations remain unresolved: input type, quote time, fallback rules, cleaning rules, unusual-market-day treatment, and whether a current official methodology note exists. | No formula or construction rule approved. | Unresolved for `TB3MS`. | Unresolved for `TB6MS`. | Need current Board/Federal Reserve technical methodology note or support-confirmable answer. | `needs_support_question` | Not H.15 approval; not source approval; not data approval; not no-lookahead approval. |
| phase101_fred_transformation_gap | FRED transformation and provenance uncertainty | FRED pages and release pages reportedly found, but transformation/provenance details remain incomplete. | FRED transformation, monthly publication timing, late corrections, cleaning/interpolation, and exact monthly aggregation documentation remain unresolved. | No FRED transformation rule approved. | Unresolved for `TB3MS`. | Unresolved for `TB6MS`. | Need primary FRED/Board documentation or support-confirmable answer, separate from formula context. | `needs_more_primary_docs` | Not FRED approval; not FRED series approval; not data approval; not point-in-time proof. |
| phase101_pit_vintage_gap | PIT and vintage uncertainty | ALFRED/FRED context exists from prior phases, but the formula finding does not solve PIT handling. | H.15 publication timing, FRED ingestion timing, ALFRED vintage procedure, pre-2002 limitations, final-vintage revision risk, and last-updated metadata limits remain unresolved. | No no-lookahead, revision, or vintage procedure approved. | Unresolved for `TB3MS`. | Unresolved for `TB6MS`. | ALFRED vintage mapping should remain a separate later phase. | `needs_more_primary_docs` | Not no-lookahead approval; not point-in-time safe; not strategy validation. |
| phase101_legal_rights_gap | Legal and rights uncertainty | Official pages reportedly found, but legal and reuse questions remain unresolved. | Formula context does not settle rights, attribution, local storage, raw storage, public repo redistribution, internal use, commercial use, or citation requirements. | No rights policy approved. | Unresolved for `TB3MS`. | Unresolved for `TB6MS`. | Legal/rights review remains separate from formula review. | `needs_more_primary_docs` | Not source approval; not data approval; not legal clearance; not redistribution approval. |

## Core Formula Finding

As advisory external methodology evidence only, Phase 101 records:

- TreasuryDirect reportedly gives the bill pricing formula, rendered here as
  ASCII: `Price = Face value * (1 - (discount rate * days to maturity) / 360)`.
- This indicates a bank-discount or discount-basis convention.
- The convention uses a 360-day year.
- The convention uses actual days to maturity.
- This is a pricing or quote convention, not a realized return formula.
- This does not approve a cash proxy or return-construction method.

This formula context must not be used as a production implementation,
backtest input, cash-return input, benchmark input, or trading input.

## H.15, TB3MS, And TB6MS Classification

As advisory external classification findings only, Phase 101 records:

- H.15 and FRED reportedly identify Treasury bill series as secondary-market
  and discount-basis series.
- `TB3MS` and `TB6MS` are reportedly monthly and not seasonally adjusted.
- They are associated with Board of Governors / H.15 Selected Interest Rates.
- They are not Treasury auction results.
- They are not bond-equivalent yields.
- They are not total-return series.
- They are not directly investable cash returns.

`TB3MS` and `TB6MS` remain candidate-only. A series ID, H.15 label, or
discount-basis convention does not make either series a cash proxy, benchmark,
rate source, source, data source, return-construction input, no-lookahead
input, strategy input, or trading input.

## Monthly-Average And FRED Transformation Uncertainty

Phase 101 records these unresolved monthly-average and FRED transformation
questions:

- whether monthly values are simple arithmetic averages of daily observations
- whether the monthly construction is FRED-specific or Board-published
- how missing days and holidays are handled
- how late corrections are handled
- whether FRED performs cleaning, interpolation, or transformation beyond
  standard series handling
- whether exact monthly aggregation is documented for `TB3MS` and `TB6MS`

No monthly aggregation rule, FRED transformation rule, FRED provenance rule,
or monthly availability rule is approved.

## Daily Quote Construction Uncertainty

Phase 101 records these unresolved daily H.15 quote construction questions:

- whether H.15 daily T-bill rates are survey quotes, executed trades, dealer
  quotes, bid/ask/mid, or another input
- time of day of quote selection
- fallback rules
- data cleaning rules
- treatment of unusual market days
- whether a current official methodology note exists

No daily quote construction rule, daily data-cleaning rule, fallback rule, or
unusual-market-day rule is approved.

## Conversion And Compounding Risks

Phase 101 records these conversion and compounding risks:

- discount-basis rates are not investor returns
- discount-basis rates are not bond-equivalent yields
- discount-basis rates are not money-market total returns
- monthly averages are not daily paths
- conversion to bond-equivalent yield, effective yield, daily return, or
  monthly return remains unresolved
- any future conversion must document day-count, compounding, maturity, roll,
  calendar, and availability timing
- no conversion formula is approved

No discount-basis conversion, bond-equivalent yield conversion, effective
yield conversion, daily accrual rule, monthly return rule, calendar alignment,
compounding convention, maturity or roll assumption, rate-to-return method, or
cash-proxy construction is approved.

## No-Lookahead And Point-In-Time Risks

Phase 101 records these no-lookahead and point-in-time risks:

- formula knowledge does not solve no-lookahead
- H.15 publication timing still matters
- FRED ingestion timing still matters
- ALFRED vintage procedure still matters
- pre-2002 point-in-time limitations remain
- final-vintage values may include revisions
- FRED last-updated metadata is not a complete point-in-time model

No `TB3MS` or `TB6MS` value may affect a future strategy-relative,
cash-return, excess-return, or benchmark/cash claim until a later phase proves
the value was available under the selected as-of rule before the relevant
modeled decision.

## Official-Docs-Found Summary

The external discovery output reportedly found or referenced these official
or primary source categories:

- TreasuryDirect bill pricing documentation
- Treasury interest-rate FAQ
- Federal Reserve H.15 current pages
- Federal Reserve H.15 Data Download Program pages
- historical H.15 PDF or footnote reference
- FRED `TB3MS` and `TB6MS` pages
- FRED H.15 release page

This summary does not paste raw external text and does not verify page
contents inside the repo. The official-docs-found summary remains advisory
until a later phase performs direct primary-source review under an explicit
scope.

## Later-Review Recommendation

Recommended later-review path, not approval:

1. Normalize H.15 discount-basis convention as quote-methodology context only.
2. Do not implement conversion yet.
3. Next external work should search for a current Board/Federal Reserve H.15
   technical methodology note or support-confirmable answer on daily quote
   construction and monthly averaging.
4. ALFRED vintage procedure mapping should remain separate and later.

This recommendation does not rank, score, select, recommend for use, approve,
validate, or make FRED, H.15, `TB3MS`, `TB6MS`, any FRED series, any source,
any data, any benchmark, any cash proxy, any rate source, any conversion, any
return construction, any no-lookahead policy, any strategy, or any trading path
ready for implementation.

## Relationship To Prior Phases

Phase 90 defined benchmark and cash timing boundaries. Phase 101 does not
approve a benchmark, cash proxy, cash-rate series, publication-timing rule,
revision rule, compounding rule, or cash-return convention.

Phase 96 defined FRED benchmark/cash/rate normalization readiness. Phase 101
normalizes reported H.15 discount-basis formula and convention findings under
that readiness boundary, but it does not approve FRED, H.15, any series, any
rate source, source use, data use, conversion, or no-lookahead handling.

Phase 97 defined the FRED candidate series intake plan. Phase 101 supplies
methodology-context material for later candidate review only. Candidate intake
does not approve FRED. Candidate intake does not approve any series. A series
ID is not a cash proxy.

Phase 98 normalized FRED candidate series discovery output. Phase 101 narrows
from candidate discovery to one unresolved methodology topic: the
discount-basis quote convention for H.15 T-bill rates. Formula context does
not solve legal, vintage, timing, missing, stale, conversion, or data-use
questions.

Phase 99 normalized reported `TB3MS`/`TB6MS` primary-verification findings.
Phase 101 adds advisory formula and convention context for those candidate
series only. Discount-basis convention does not approve return construction,
and the series IDs remain not cash proxies.

Phase 100 routed the FRED/T-bill track toward external H.15 discount-basis
formula and convention discovery. Phase 101 normalizes that external discovery
output as advisory methodology evidence only and approves nothing.

FRED/H.15 data must not enter normal pytest through network calls, downloaded
files, local data files, fixtures, credentials, or real observations. Normal
`python -m pytest` must remain offline and credential-free.

## Explicit Non-Claims

Phase 101 is:

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
FRED observation, H.15 observation, formula implementation, return
construction, ETF ticker selection, benchmark comparison, ranking, scoring,
recommendation, candidate-discovery behavior in code, replay metric,
manifest-to-planning bridge, signal/evaluator behavior, broker/order/fill/
portfolio/runtime behavior, LLM call, network call, market-data call,
dashboard/advisory/AI integration, paper behavior, live behavior, or trading
behavior.

## Decision

Decision: advisory H.15 discount-basis formula and convention normalization
only.

The reported TreasuryDirect bill price formula is normalized as
quote-methodology context only. `TB3MS` and `TB6MS` remain candidate-only.
They are not approved, validated, selected, point-in-time safe, cash proxies,
benchmarks, rate sources, data sources, return-construction inputs, strategy
inputs, or trading inputs.

No formula implementation was added. No conversion method was approved. No
production code or tests changed. No real data was added. No FRED API calls or
downloads occurred. Normal pytest remains offline and credential-free.

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
- no approved daily quote time, input type, fallback, or cleaning rule
- no approved monthly averaging rule
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
- no approved normal-pytest FRED dependency
- no approved strategy-validation claim
- no approved trading-readiness claim

## Follow-Up Recommendation

The likely next external step should be discovery for a current Board/Federal
Reserve H.15 technical methodology note, or a support-confirmable answer, on
daily quote construction and monthly averaging. If that becomes documentation
churn, pause the FRED track and return to broader ETF source work.
