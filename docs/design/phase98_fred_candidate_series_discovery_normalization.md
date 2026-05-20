# Phase 98 - FRED Candidate Series Discovery Normalization

## Purpose

This document normalizes externally produced FRED candidate series discovery
output into the deterministic repo documentation trail as advisory intake
material only.

The external discovery output reportedly included possible candidate series
such as `OBFR`, `EFFR`, `TB3MS`, `TB6MS`, `FEDFUNDS`, `SOFR`,
`SOFR30DAYAVG`, `SOFR90DAYAVG`, `UNRATE`, and generic non-official guide or
blog references. Some references were reportedly official FRED, NY Fed, or
Federal Reserve pages; others were secondary tutorials, third-party guides,
articles, repository references, or general directories. Phase 98 treats all
of that material as discovery input only, not verified primary-source evidence
and not approval.

This phase is documentation-only. It does not browse, call FRED APIs, call
NY Fed APIs, call Federal Reserve APIs, download data, inspect observations,
create local data files, add credentials, add tests, add production behavior,
or change any source, replay, broker, advisory, or governance code.

## Normalization Boundary

Phase 98 may normalize FRED candidate series discovery only.

It must not approve:

- FRED
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

Reported official pages are discovery leads only. A reported FRED series ID is
not a cash proxy, benchmark, source approval, data approval, conversion rule,
publication-timing rule, no-lookahead proof, or strategy input. Reported
secondary or tutorial references are scout material only and cannot support
approval.

## Candidate Role Vocabulary

Phase 98 preserves the Phase 97 role framework:

- `cash_risk_free_proxy_candidate`: cash/risk-free proxy candidate for later
  review only.
- `t_bill_proxy_candidate`: T-bill proxy candidate for later review only.
- `short_rate_context_candidate`: short-rate context candidate only.
- `benchmark_cash_timing_context_candidate`: benchmark/cash timing context
  candidate only.
- `macro_context_candidate`: macro context candidate only.
- `rejected_out_of_scope_candidate`: rejected or out-of-scope candidate.

Roles are routing labels, not approvals. A series may be a strong later-review
candidate and still remain not approved, not validated, not a cash proxy, not a
benchmark, not point-in-time safe, and not strategy-ready.

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
calls, NY Fed API calls, data downloads, local snapshots, fixture use, raw-row
storage, source use, benchmark/cash comparison, return construction,
no-lookahead claims, scoring, ranking, recommendation, strategy validation, or
trading behavior.

## Official Source Versus Scout Source Labels

The external discovery output is normalized with these evidence-status labels:

| Label | Phase 98 treatment |
| --- | --- |
| official FRED series page reportedly found | Discovery lead only. The page must be reopened and reviewed in a later primary-source phase before it can support any stronger claim. |
| official source/release page reportedly found | Discovery lead only. Source, release, methodology, and timing documentation still need direct later review. |
| official terms/rights page reportedly found | Discovery lead only. Terms, attribution, local storage, raw-row storage, public repo, and redistribution questions remain unresolved. |
| official ALFRED/realtime-vintage evidence still needed | Controlling blocker for point-in-time and revision questions until reviewed per exact series. |
| secondary/tutorial/source-discovery reference only | Scout context only. Tutorials, blog posts, GitHub repositories, Reddit posts, generic directories, guides, or commentary are not sufficient evidence. |
| unresolved primary-source confirmation needed | Controlling blocker for every row in this phase. |

No row below treats third-party tutorials, blog posts, GitHub, Reddit, general
database directories, or commentary articles as sufficient evidence for FRED,
series, source, data, benchmark, cash proxy, rate-source, methodology,
evidence, return-construction, no-lookahead, strategy, or trading approval.

## Normalized Candidate Series Table

The table records external discovery as advisory intake material only. Series
titles, source/release notes, unit/frequency notes, and support status are
reported leads, not independently verified Phase 98 evidence.

| normalized_id | candidate_series_id | fred_series_id | series_title | candidate_role | source_or_release | units_frequency_summary | realtime_vintage_status | publication_timing_status | revision_status | conversion_question | rights_terms_status | scout_status | normalized_status | primary_source_status | blockers | allowed_next_step | non_claims |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phase98_tb3ms | fred_tb3ms | `TB3MS` | Reported as 3-month Treasury bill secondary market rate, discount basis; not independently reviewed. | `t_bill_proxy_candidate`; `cash_risk_free_proxy_candidate` for later review only. | Reported official FRED series page and H.15 source/release leads; not independently reviewed. | Reported monthly/annualized rate style; exact units, frequency, seasonal status, and discount-basis meaning require official review. | Official ALFRED/realtime-vintage evidence still needed for this exact series. | H.15 release timing, observation date versus availability date, and known-before-decision timing unresolved. | Revision, correction, backfill, stale, and missing-value behavior unresolved. | Discount-basis to daily/monthly cash return conversion, compounding, accrual calendar, and valid use remain unresolved. | Official terms/rights page reportedly found only at provider level; per-series rights, attribution, local storage, and redistribution unresolved. | Official FRED/source pages reportedly found; secondary references remain scout-only. | `candidate_for_later_series_review` | Unresolved primary-source confirmation needed; official series, source/release, terms, and ALFRED evidence still need later review. | No direct primary-source review in repo; conversion, timing, rights, vintage, missing/stale, and normal-pytest independence unresolved. | Docs-only primary-source verification of FRED series page, H.15 source/release, ALFRED/vintage, rights, and timing; no API call or download. | Not FRED approval; not series approval; not cash proxy approval; not benchmark approval; not point-in-time safe. |
| phase98_tb6ms | fred_tb6ms | `TB6MS` | Reported as 6-month Treasury bill secondary market rate, discount basis; not independently reviewed. | `t_bill_proxy_candidate`; `cash_risk_free_proxy_candidate` for later review only. | Reported official FRED series page and H.15 source/release leads; not independently reviewed. | Reported monthly/annualized rate style; exact units, frequency, seasonal status, and discount-basis meaning require official review. | Official ALFRED/realtime-vintage evidence still needed for this exact series. | H.15 release timing, observation date versus availability date, and known-before-decision timing unresolved. | Revision, correction, backfill, stale, and missing-value behavior unresolved. | Discount-basis to daily/monthly cash return conversion, compounding, accrual calendar, and valid use remain unresolved. | Official terms/rights page reportedly found only at provider level; per-series rights, attribution, local storage, and redistribution unresolved. | Official FRED/source pages reportedly found; secondary references remain scout-only. | `candidate_for_later_series_review` | Unresolved primary-source confirmation needed; official series, source/release, terms, and ALFRED evidence still need later review. | No direct primary-source review in repo; conversion, timing, rights, vintage, missing/stale, and normal-pytest independence unresolved. | Docs-only primary-source verification of FRED series page, H.15 source/release, ALFRED/vintage, rights, and timing; no API call or download. | Not FRED approval; not series approval; not cash proxy approval; not benchmark approval; not point-in-time safe. |
| phase98_effr | fred_effr | `EFFR` | Reported as Effective Federal Funds Rate; not independently reviewed. | `short_rate_context_candidate`; possible `benchmark_cash_timing_context_candidate` for later review only. | Reported official FRED series page and official Federal Reserve or NY Fed methodology/source leads; not independently reviewed. | Reported overnight rate; exact units, frequency, calculation method, and publication cadence require official review. | Official ALFRED/realtime-vintage evidence still needed for this exact series. | Publication timing and whether values are known before modeled decisions are unresolved. | Revision, correction, and methodology-change behavior unresolved. | Overnight rate conversion to cash return, accrual timing, compounding, weekends, and holidays unresolved. | Official terms/rights page reportedly found only at provider level; per-series rights, attribution, local storage, and redistribution unresolved. | Official-source observations reportedly found, but all secondary/tutorial material remains scout-only. | `candidate_for_later_series_review` | Unresolved primary-source confirmation needed; exact official series/source/release, NY Fed/Federal Reserve method, terms, and ALFRED evidence need later review. | Publication timing, revision behavior, conversion, rights, and normal-pytest independence unresolved. | Docs-only primary-source verification of official series, methodology/release, ALFRED/vintage, rights, and timing; no API call or download. | Not rate-source approval; not cash proxy approval; not benchmark approval; not point-in-time safe. |
| phase98_obfr | fred_obfr | `OBFR` | Reported as Overnight Bank Funding Rate; not independently reviewed. | `short_rate_context_candidate`; possible `benchmark_cash_timing_context_candidate` for later review only. | Reported official FRED series page and NY Fed official source/methodology leads; not independently reviewed. | Reported overnight rate; exact units, frequency, calculation method, and publication cadence require official review. | Official ALFRED/realtime-vintage evidence still needed for this exact series. | NY Fed publication timing, observation date versus availability date, and known-before-decision timing unresolved. | Revision, correction, methodology-change, stale, and missing-value behavior unresolved. | Overnight rate conversion to cash return, compounding, weekends, holidays, and whether conversion is valid unresolved. | Official terms/rights page reportedly found only at provider level; per-series rights, attribution, local storage, and redistribution unresolved. | Official-source observations reportedly found, but all secondary/tutorial material remains scout-only. | `candidate_needs_more_evidence` | Unresolved primary-source confirmation needed; official series/source/release, terms, NY Fed methodology, and ALFRED evidence need later review. | Less direct cash-proxy fit than T-bill candidates; timing, conversion, revision, rights, and normal-pytest independence unresolved. | Docs-only primary-source verification of official series, methodology/release, ALFRED/vintage, rights, and timing; no API call or download. | Not rate-source approval; not cash proxy approval; not benchmark approval; not strategy-ready. |
| phase98_sofr | fred_sofr | `SOFR` | Reported as Secured Overnight Financing Rate; not independently reviewed. | `short_rate_context_candidate`; `benchmark_cash_timing_context_candidate` for later review only. | Reported official FRED series page and NY Fed official source/methodology leads; not independently reviewed. | Reported overnight secured financing rate; exact units, frequency, publication cadence, and calculation method require official review. | Official ALFRED/realtime-vintage evidence still needed for this exact series. | NY Fed publication timing, observation date versus availability date, and known-before-decision timing unresolved. | Revision, correction, methodology-change, stale, and missing-value behavior unresolved. | Overnight rate conversion, compounding, repo-market context, weekend/holiday accrual, and whether cash-return use is valid unresolved. | Official terms/rights page reportedly found only at provider level; per-series rights, attribution, local storage, and redistribution unresolved. | Official-source observations reportedly found, but all secondary/tutorial material remains scout-only. | `context_only` | Unresolved primary-source confirmation needed; official series/source/release, terms, NY Fed methodology, and ALFRED evidence need later review. | Benchmark/cash use is more complex than discovery supports; conversion, timing, rights, vintage, and normal-pytest independence unresolved. | Keep as context/timing candidate unless a later docs-only primary-source phase justifies stronger review; no API call or download. | Not cash proxy approval; not benchmark approval; not rate-source approval; not point-in-time safe. |
| phase98_sofr30dayavg | fred_sofr30dayavg | `SOFR30DAYAVG` | Reported as 30-day average SOFR; not independently reviewed. | `benchmark_cash_timing_context_candidate`; `short_rate_context_candidate` for later review only. | Reported official FRED series page and NY Fed SOFR average source/methodology leads; not independently reviewed. | Reported rolling-window average; exact units, frequency, compounding basis, and window mechanics require official review. | Official ALFRED/realtime-vintage evidence still needed for this exact series. | Publication timing, window end date, observation date versus availability date, and known-before-decision timing unresolved. | Revision, correction, methodology-change, stale, and missing-value behavior unresolved. | Rolling-window average conversion to daily/monthly cash return may double count or misalign accrual; compounding convention unresolved. | Official terms/rights page reportedly found only at provider level; per-series rights, attribution, local storage, and redistribution unresolved. | Official-source observations reportedly found, but all secondary/tutorial material remains scout-only. | `candidate_needs_more_evidence` | Unresolved primary-source confirmation needed; official series/source/release, terms, NY Fed methodology, and ALFRED evidence need later review. | Rolling-window and compounding complexity; timing, revision, rights, and normal-pytest independence unresolved. | Docs-only primary-source verification only after T-bill and overnight-rate candidates; no API call or download. | Not cash proxy approval; not benchmark approval; not return-construction approval; not strategy-ready. |
| phase98_sofr90dayavg | fred_sofr90dayavg | `SOFR90DAYAVG` | Reported as 90-day average SOFR; not independently reviewed. | `benchmark_cash_timing_context_candidate`; `short_rate_context_candidate` for later review only. | Reported official FRED series page and NY Fed SOFR average source/methodology leads; not independently reviewed. | Reported rolling-window average; exact units, frequency, compounding basis, and window mechanics require official review. | Official ALFRED/realtime-vintage evidence still needed for this exact series. | Publication timing, window end date, observation date versus availability date, and known-before-decision timing unresolved. | Revision, correction, methodology-change, stale, and missing-value behavior unresolved. | Rolling-window average conversion to daily/monthly cash return may double count or misalign accrual; compounding convention unresolved. | Official terms/rights page reportedly found only at provider level; per-series rights, attribution, local storage, and redistribution unresolved. | Official-source observations reportedly found, but all secondary/tutorial material remains scout-only. | `candidate_needs_more_evidence` | Unresolved primary-source confirmation needed; official series/source/release, terms, NY Fed methodology, and ALFRED evidence need later review. | Rolling-window and compounding complexity; timing, revision, rights, and normal-pytest independence unresolved. | Docs-only primary-source verification only after T-bill and overnight-rate candidates; no API call or download. | Not cash proxy approval; not benchmark approval; not return-construction approval; not strategy-ready. |
| phase98_fedfunds | fred_fedfunds | `FEDFUNDS` | Reported as Federal Funds Effective Rate; not independently reviewed. | `short_rate_context_candidate`; `benchmark_cash_timing_context_candidate` for context only unless later review justifies another role. | Reported official FRED series page and official Federal Reserve source/release leads; not independently reviewed. | Reported policy/short-rate context; exact units, frequency, and aggregation require official review. | Official ALFRED/realtime-vintage evidence still needed for this exact series. | Monthly or release aggregation timing, observation date versus availability date, and known-before-decision timing unresolved. | Revision, correction, stale, and missing-value behavior unresolved. | Context-only unless later review proves conversion and timing; monthly or aggregated rate use for cash returns unresolved. | Official terms/rights page reportedly found only at provider level; per-series rights, attribution, local storage, and redistribution unresolved. | Official-source observations reportedly found, but all secondary/tutorial material remains scout-only. | `context_only` | Unresolved primary-source confirmation needed; official series/source/release, terms, and ALFRED evidence need later review. | Current disposition is context-only; no cash proxy role, conversion, timing, rights, or normal-pytest independence resolved. | Keep as context-only unless a later docs-only primary-source phase justifies another role; no API call or download. | Not cash proxy approval; not benchmark approval; not rate-source approval; not strategy validation. |
| phase98_unrate | fred_unrate | `UNRATE` | Reported as Unemployment Rate; not independently reviewed. | `macro_context_candidate` only. | Reported official FRED series page and official labor/macro release leads; not independently reviewed. | Reported macro percentage series; exact units, frequency, seasonal adjustment, and release semantics require official review if ever needed. | Official ALFRED/realtime-vintage evidence still needed for this exact series. | Macro release timing, observation month versus release date, revisions, and known-before-decision timing unresolved. | Revision and benchmark-revision behavior unresolved. | No cash-return conversion role in this phase; macro context only. | Official terms/rights page reportedly found only at provider level; per-series rights, attribution, local storage, and redistribution unresolved. | Official-source observations reportedly found, but all secondary/tutorial material remains scout-only. | `context_only` | Unresolved primary-source confirmation needed if later macro review needs it. | Not relevant to cash/risk-free proxy selection; rights, vintage, release timing, and normal-pytest independence unresolved. | Keep as macro context-only unless later research needs a separate macro-overlay review; no API call or download. | Not benchmark approval; not cash proxy approval; not methodology approval; not strategy validation. |
| phase98_generic_non_official_guides | generic_non_official_guides_blogs | N/A | N/A; non-series scout references. | `rejected_out_of_scope_candidate` | Third-party tutorials, guides, blogs, GitHub repositories, Reddit posts, general directories, or commentary. | N/A. | N/A; no official ALFRED or realtime-vintage evidence. | N/A; no official publication timing evidence. | N/A; no official revision evidence. | N/A. | No official rights/terms evidence for FRED series approval. | Secondary/tutorial/source-discovery reference only. | `reject_for_now` | Secondary/tutorial/source-discovery reference only; unresolved primary-source confirmation needed. | Non-official references cannot approve FRED, a FRED series, source, data, rights, timing, conversion, no-lookahead, or strategy use. | Reject for now as evidence; at most use as a clue to locate official primary pages later. | Not evidence approval; not source approval; not FRED approval; not data approval. |

## Candidate Disposition Summary

Strongest later-review buckets, not approval:

| Bucket | Candidate series | Phase 98 disposition |
| --- | --- | --- |
| H.15 T-bill rates | `TB3MS`, `TB6MS` | `candidate_for_later_series_review`; natural T-bill and cash/risk-free proxy candidates for later review, but discount-basis conversion, H.15 timing, ALFRED/vintage, rights, and no-lookahead questions remain unresolved. |
| Overnight policy/reference rates | `EFFR`, `OBFR` | `EFFR` is routed to `candidate_for_later_series_review`; `OBFR` is routed to `candidate_needs_more_evidence`. Both need official methodology, release timing, revision, conversion, and rights review. |
| SOFR family | `SOFR`, `SOFR30DAYAVG`, `SOFR90DAYAVG` | `SOFR` is context-only in this phase; rolling SOFR averages need more evidence. These remain context/timing candidates only because benchmark/cash use, rolling-window interpretation, and compounding are more complex. |

Each bucket remains not approved, not validated, not a cash proxy, not a
benchmark, not point-in-time safe, and not strategy-ready.

Context-only or rejected items:

| Item | Phase 98 disposition | Rationale |
| --- | --- | --- |
| `FEDFUNDS` | `context_only` | Short-rate or benchmark/cash timing context only unless later primary-source review justifies another role. |
| `UNRATE` | `context_only` | Macro context-only; not a cash, benchmark, or rate-source approval path. |
| `SOFR` as a duplicate macro/context lead | `context_only` | Useful as SOFR context/timing material only in this phase. |
| Generic non-official guides or blogs | `reject_for_now` | Secondary/tutorial/source-discovery material cannot approve source, data, rights, timing, conversion, no-lookahead, or strategy use. |

These dispositions do not rank, score, select, recommend for use, approve, or
reject any series for trading or research implementation.

## Unresolved Primary-Source Questions

At minimum, later review must answer:

- Is ALFRED or other realtime/vintage history available and meaningful for
  each exact series?
- Has the official FRED series page been reviewed for each exact series?
- What official source, release, methodology, and field documentation applies?
- What terms, rights, attribution, local storage, raw-row storage, public repo,
  redistribution, and citation requirements apply?
- What publication, release, and update timing applies?
- How does observation date differ from availability date?
- What revision, correction, backfill, benchmark-revision, or methodology
  change policy applies?
- How should missing, stale, delayed, discontinued, or suppressed values be
  handled?
- How should rate calendars align with ETF calendars, market holidays,
  strategy decision timestamps, action timestamps, and cash accrual windows?
- What unit and frequency conversion is required, if any?
- How should discount-basis T-bill rates be converted, if conversion is valid?
- What compounding convention applies for overnight rates, T-bill rates, and
  rolling SOFR averages?
- Was each value known before the modeled decision timestamp?
- Can normal `python -m pytest` remain offline, credential-free, source-free,
  provider-free, and independent from FRED, NY Fed, Federal Reserve, and real
  rate observations?

Unanswered questions remain blockers. Positive answers would still not approve
FRED, any series, source, data, benchmark, cash proxy, return construction,
no-lookahead handling, strategy validation, or trading use without a separate
explicit approval phase.

## Later-Review Ordering Recommendation

Recommended order for later review, not approval:

1. `TB3MS` and `TB6MS` first as T-bill candidates, because they are natural
   cash/risk-free review candidates but require discount-basis conversion and
   H.15 timing review.
2. `EFFR` and `OBFR` second as overnight rate candidates, because publication
   timing, Federal Reserve or NY Fed methodology, revision behavior, and
   overnight accrual conventions matter.
3. `SOFR`, `SOFR30DAYAVG`, and `SOFR90DAYAVG` third as context/timing
   candidates, because rolling-window, compounding, benchmark-use, and
   cash-return complexities are higher.
4. `FEDFUNDS` and `UNRATE` as context-only unless later research needs macro
   overlays or a separate policy-rate context review.

This is an ordering for docs-only primary-source review. It does not rank,
score, recommend for use, select, approve, validate, or make any series ready
for data acquisition, local storage, return construction, no-lookahead claims,
strategy validation, or trading.

## Relationship To Prior Phases

Phase 90 defined benchmark and cash timing boundaries. Phase 98 does not
approve a benchmark, cash proxy, cash-rate series, publication-timing rule,
revision rule, compounding rule, or cash-return convention.

Phase 96 defined FRED benchmark/cash/rate normalization readiness. Phase 98
normalizes exact candidate series leads under that readiness boundary, but it
does not approve FRED, any FRED series, any rate source, source use, data use,
or no-lookahead handling.

Phase 97 defined the FRED candidate series intake plan. Phase 98 applies that
intake framework to external discovery output only. Candidate discovery does
not approve FRED. Candidate discovery does not approve any series. A FRED
series ID is not a cash proxy. Official series pages do not solve conversion,
timing, rights, revision, missing-value, or no-lookahead questions.

FRED data must not enter normal pytest through network calls, downloaded files,
local data files, fixtures, credentials, or real observations. Normal
`python -m pytest` must remain offline and credential-free.

## Explicit Non-Claims

Phase 98 is:

- not FRED approval
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

It adds no FRED approval, FRED series approval, benchmark approval, cash proxy
approval, rate-source approval, source approval, data approval, vendor
approval, universe approval, methodology approval, parameter approval, evidence
approval, return-construction approval, no-lookahead approval, cost/friction
approval, liquidity approval, strategy validation, real data ingestion, real
data files, FRED API call, NY Fed API call, Federal Reserve API call, data
download, raw FRED observation, ETF ticker selection, benchmark comparison,
ranking, scoring, recommendation, candidate-discovery behavior in code, replay
metric, manifest-to-planning bridge, signal/evaluator behavior,
broker/order/fill/portfolio/runtime behavior, LLM call, network call,
market-data call, dashboard/advisory/AI integration, paper behavior, live
behavior, or trading behavior.

## Decision

Decision: advisory FRED candidate series discovery normalization only.

`TB3MS` and `TB6MS` are routed as strongest later-review T-bill candidates.
`EFFR` and `OBFR` are routed as overnight rate candidates with unresolved
methodology, timing, revision, conversion, and rights questions. The SOFR
family remains context/timing material only or needs more evidence.
`FEDFUNDS` and `UNRATE` remain context-only. Generic non-official guides and
blogs are rejected for now as evidence.

No FRED series, cash proxy, benchmark, rate source, source, data, methodology,
parameter, evidence, return-construction policy, no-lookahead policy,
cost/friction model, liquidity rule, strategy validation, or trading use is
approved.

## Remaining Blockers

- no approved FRED use
- no approved FRED series
- no approved source
- no approved data
- no approved benchmark
- no approved cash proxy
- no approved rate source
- no approved official per-series review
- no approved source/release review
- no approved rights, terms, local storage, public repo, redistribution, or
  citation policy
- no approved ALFRED/realtime/vintage behavior for a selected series
- no approved publication, release, observation, or revision timing policy
- no approved unit, frequency, conversion, compounding, or accrual convention
- no approved discount-basis conversion for T-bill rates
- no approved missing or stale value policy
- no approved calendar alignment policy
- no approved known-before-decision rule
- no approved return-construction policy
- no approved no-lookahead/as-of policy
- no approved normal-pytest FRED dependency
- no approved strategy-validation claim
- no approved trading-readiness claim
