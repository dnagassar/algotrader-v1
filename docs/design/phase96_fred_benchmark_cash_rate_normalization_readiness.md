# Phase 96 - FRED Benchmark / Cash Rate Normalization Readiness

## Purpose

This document defines a narrow readiness boundary for reviewing FRED as a
future benchmark, cash, or rate source candidate only.

It is documentation-only. It does not browse, call APIs, download data, create
local data files, select a series, approve a cash proxy, approve a benchmark,
approve a source, approve data use, or change production code or tests.

## Boundary

Phase 96 may define FRED benchmark, cash, and rate normalization readiness
only.

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
- any strategy validation
- any trading use

FRED remains a candidate review topic only. Official documentation being
reported in earlier external verification does not approve FRED, any series,
any rights, any local storage, any benchmark/cash role, any no-lookahead
handling, or any strategy behavior.

## Candidate FRED Use Cases

FRED may be reviewed later only for candidate benchmark, cash, and rate
normalization contexts:

- cash or risk-free proxy context, such as a future out-of-market cash-return
  assumption or risk-free-relative research reference
- benchmark and cash timing context, such as publication, revision, and
  availability rules for later comparability work
- rate-vintage or as-of research context, such as checking whether a selected
  series can be queried or documented point-in-time
- macro context, if later broad ETF research needs macro background and a
  separate phase keeps that use non-trading and non-approving

FRED is not ETF price data. FRED does not solve ETF source approval, ETF
universe or survivorship questions, source/data rights for ETF prices,
adjusted-price methodology, dividend or distribution treatment, or strategy
validation. FRED vintage/as-of support, even if confirmed later for a selected
series, would not make ETF price data point-in-time safe.

## Phase 95 Official-Doc Findings

Phase 95 recorded external primary-source verification output as advisory
material only. For FRED, that external verification reportedly found:

- FRED API overview documentation
- observations documentation
- real-time-period documentation
- API-key documentation
- Terms of Use
- observation fields that can include `realtime_start`, `realtime_end`,
  `date`, and `value`
- vintage/as-of support that appears stronger than the ETF price candidates

These are advisory findings inherited from the Phase 95 normalization. Phase
96 does not independently verify the official pages, does not call FRED, does
not inspect any FRED series, and does not convert those findings into approval.
Any future use must re-check the specific official series notes, terms,
rights, timing, and vintage behavior before implementation.

## Unresolved FRED Questions

Future review must still answer at least:

- What per-series rights or licensing terms apply?
- Which exact candidate series, if any, is being reviewed?
- What attribution or citation requirements apply?
- What local storage rights apply to raw rows, cached responses, and derived
  outputs?
- What redistribution or public repo restrictions apply?
- Is an API key required for the intended access path?
- What rate limits, quotas, access limits, account constraints, or service
  tiers apply?
- Does vintage data exist for the chosen series?
- How does the observation date differ from the release or publication date?
- What do revision dates, `realtime_start`, and `realtime_end` mean for the
  chosen series?
- How should daily, weekly, monthly, annual, or irregular observations be
  converted, if conversion is needed?
- What compounding convention applies to any annualized or periodic rate?
- How are missing, stale, discontinued, or delayed values handled?
- How are FRED calendars aligned with ETF return windows, market holidays,
  strategy decision timestamps, action timestamps, and cash accrual windows?
- Were values known before the modeled decision timestamp?

Unresolved answers remain blockers. Positive answers would still not approve
FRED-backed use without a separate explicit approval phase.

## FRED No-Lookahead Risks

Future FRED-backed research must treat these risks as unresolved until a later
review documents and tests them:

- using current revised values as if they were known historically
- confusing an observation date with the date the value became available
- using vintage endpoints incorrectly or without proving selected-series
  semantics
- creating lookahead through daily, weekly, monthly, or annual frequency
  conversion
- applying monthly or delayed rates before their release or publication time
- misaligning FRED holidays, weekends, or publication calendars with ETF return
  calendars
- treating cash accrual timing as obvious when the decision date, action date,
  holding interval, weekend handling, and accrual convention are still
  ambiguous

No FRED observation may affect a future strategy-relative, cash-return, excess
return, or benchmark/cash claim until a later phase proves that the value was
available under the selected as-of rule before the relevant modeled decision.

## Future Review Gates

Before any future FRED-backed cash, benchmark, or rate use, a later phase must
document at minimum:

- the selected series remains candidate-only until separately approved
- official series notes were reviewed for the exact selected series
- Terms, rights, licensing, local storage, public repo, redistribution, and
  citation requirements were reviewed
- vintage and realtime behavior were reviewed for the exact selected series
- publication, release, observation-date, and revision timing were reviewed
- conversion and compounding rules were documented
- missing and stale value handling was documented
- alignment with strategy decision timing and action timing was documented
- normal `python -m pytest` remains synthetic, offline, credential-free, and
  free of FRED calls

Passing these gates would still not by itself approve FRED, any series, any
benchmark, any cash proxy, any rate source, any data, any source, any
return-construction policy, any no-lookahead policy, any strategy validation,
or any trading use. Approval would require a separate explicit phase.

## Allowed Next Steps

Allowed follow-up work:

- primary-source review of specific FRED series notes
- Terms of Use and rights review
- docs-only normalization of FRED series candidates
- support or library documentation review, if later needed to understand
  access mechanics without calling FRED

Forbidden follow-up work in this phase:

- FRED API calls
- data downloads
- local data files
- source approval
- cash proxy approval
- benchmark approval
- strategy validation
- code implementation

Normal pytest must remain offline and credential-free. Any future integration
or support-library review must not introduce repo code that calls FRED,
requires credentials, or reaches the network during normal tests.

## Relationship To Prior Phases

Phase 90 defined benchmark and cash timing boundaries. Phase 96 narrows the
next readiness question to FRED as a possible future benchmark/cash/rate
candidate only; it does not approve any benchmark, cash proxy, rate source, or
timing rule.

Phase 93 defined the broad ETF source evidence intake plan. FRED readiness is
not ETF price-source intake approval and cannot approve ETF price data, ETF
source paths, local snapshots, or source evidence.

Phase 94 normalized source-discovery output as advisory intake material. Phase
96 does not add source discovery behavior, ranking, scoring, or provider
selection.

Phase 95 normalized external primary-source verification output for Stooq,
Alpha Vantage, and FRED. Phase 96 follows the Phase 95 ordering recommendation
by reviewing FRED first, but only for benchmark/cash/rate readiness. FRED
vintage support still requires selected-series review, and FRED cannot enter
normal pytest through network calls.

## Explicit Non-Claims

Phase 96 is:

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
- not strategy validation
- not trading readiness

It adds no FRED approval, FRED series approval, benchmark approval, cash proxy
approval, rate-source approval, source approval, data approval, vendor
approval, universe approval, methodology approval, parameter approval, evidence
approval, return-construction approval, no-lookahead approval, cost/friction
approval, liquidity approval, strategy validation, real data ingestion, real
data files, ETF ticker selection, benchmark comparison, ranking, scoring,
recommendation, candidate-discovery behavior, replay metric,
manifest-to-planning bridge, signal/evaluator behavior, broker/order/fill/
portfolio/runtime behavior, LLM call, network call, market-data call,
dashboard/advisory/AI integration, paper behavior, live behavior, or trading
behavior.

## Decision

Decision: FRED benchmark, cash, and rate normalization readiness only.

FRED remains candidate-only and non-approved. No FRED series, benchmark, cash
proxy, rate source, source, data, methodology, parameter, evidence,
return-construction policy, no-lookahead policy, strategy validation, or
trading use is approved.

## Remaining Blockers

- no approved FRED use
- no approved FRED series
- no approved source
- no approved data
- no approved benchmark
- no approved cash proxy
- no approved rate source
- no approved per-series rights review
- no approved local storage or public repo policy
- no approved attribution or citation policy
- no approved publication, release, observation, or revision timing policy
- no approved vintage or realtime behavior for a selected series
- no approved conversion or compounding convention
- no approved missing or stale value policy
- no approved calendar alignment policy
- no approved known-before-decision rule
- no approved return-construction policy
- no approved no-lookahead/as-of policy
- no approved strategy-validation claim
- no approved trading-readiness claim
