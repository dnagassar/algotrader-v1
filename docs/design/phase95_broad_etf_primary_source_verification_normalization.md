# Phase 95 - Broad ETF Primary Source Verification Normalization

## Purpose

This document normalizes external primary-source verification findings for
Stooq, Alpha Vantage, and FRED into the deterministic repo documentation trail
as advisory verification material only.

The external Codex verification output is stronger than the earlier scout
output because it reportedly focused on official or primary provider pages
where available, but it is still external verification input. It is not source
approval, data approval, legal review, storage-rights approval, benchmark
approval, cash-proxy approval, return-construction approval, no-lookahead
approval, strategy validation, or trading readiness.

This phase is documentation-only. It does not browse, call APIs, download,
scrape, inspect real data, add source credentials, add ETF tickers, add
notebooks, add screenshots, add tests, or add production behavior.

## Normalization Boundary

Phase 95 may normalize external primary-source verification findings only.

It must not approve:

- Stooq
- Alpha Vantage
- FRED
- any source
- any data
- any vendor
- any benchmark
- any cash proxy
- any universe
- any methodology
- any parameter set
- any evidence
- any return-construction policy
- any no-lookahead policy
- any cost/friction model
- any strategy validation
- any trading use

Official documentation being reportedly found does not approve use of a
source. Official terms being reportedly found does not complete legal,
storage-rights, archival, redistribution, public-repo, entitlement, or
provider-support review. Official fields being reportedly found does not solve
return construction, adjustment interpretation, dividend/distribution
treatment, survivorship, benchmark/cash timing, or point-in-time safety.

## Normalized Confidence And Next-Step Vocabulary

Allowed `primary_source_confidence` values in this document are:

- `primary_docs_found`
- `partial_primary_docs_found`
- `terms_unclear`
- `insufficient_primary_docs`

Allowed `allowed_next_step` values in this document are:

- `reject_for_now`
- `needs_terms_review`
- `needs_provider_support_question`
- `candidate_for_repo_normalization_only`

Forbidden table values are:

- `approved`
- `validated`
- `source_approved`
- `data_approved`
- `point_in_time_safe`
- `strategy_ready`
- `trading_ready`

The allowed values are routing labels only. They do not authorize data
acquisition, raw-row storage, repo storage, local snapshot use, fixture use,
ingestion, return construction, benchmark/cash use, universe membership,
replay, scoring, ranking, recommendation, strategy validation, or trading
behavior.

## Normalized Three-Source Verification Table

| normalized_id | source_name | candidate_use | source_category | official_docs_status | terms_or_license_status | fields_status | coverage_status | adjustment_status | corporate_action_status | revision_status | timestamp_asof_status | survivorship_status | storage_rights_status | credentials_or_limits_status | primary_source_confidence | blockers | allowed_next_step | non_claims |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phase95_stooq | Stooq | Possible free/manual or exported broad ETF price snapshot route for later review only. | public web/downloaded file; API-exported local snapshot | Official historical and bulk pages reportedly found. | Terms URL reportedly found, but terms content was not verifiably readable; terms remain unclear. | Historical file or export fields reportedly exist, but exact field definitions remain unresolved. | ETF coverage, inactive coverage, symbol continuity, and delisted coverage remain unresolved. | Adjustment policy remains unresolved. | Dividend, distribution, split, and corporate-action handling remain unresolved. | Revision and correction policy remain unresolved. | Download/export timestamp, publication timing, and as-of semantics remain unresolved. | Inactive, delisted, merged, renamed, and liquidated ETF coverage remain unresolved. | Personal local research rights, raw-row storage, public repo rights, redistribution, local archival rights, storage rights, and third-party data rights remain unresolved. | Operational access may be low-friction, but automated access, bulk limits, and provider constraints remain unresolved. | `terms_unclear` | Terms content not verifiably readable; storage and third-party rights unresolved; adjustment, as-of, revision, and survivorship semantics unresolved. | `needs_provider_support_question`; `needs_terms_review` | Not source approval; not data approval; not vendor approval; not point-in-time safe; not trading ready. |
| phase95_alpha_vantage | Alpha Vantage | Possible retail API-exported local snapshot route for later review only. | API-exported local snapshot | Official API documentation reportedly found. | Official Terms reportedly found; detailed entitlement, archival, redistribution, and public repo implications remain unresolved. | Daily raw OHLCV, daily adjusted, dividends, splits, ETF profile, and listing status were reportedly found. | ETF profile and listing-status support were reportedly found, but ETF coverage completeness and inactive history remain unresolved. | Daily adjusted endpoint or fields reportedly found; exact methodology and future revision handling remain unresolved. | Dividends and splits were reportedly found; future dividend/distribution handling and corporate-action revisions remain unresolved. | Equity point-in-time behavior, row revision/correction proof, and historical endpoint revision policy remain unresolved. | API response timing, publication/update timing, export as-of meaning, and no-lookahead semantics remain unresolved. | Listing-status support does not prove survivorship-safe price history; inactive/delisted ETF price history and symbol continuity remain unresolved. | Local archival rights, raw-row storage, public repo restrictions, redistribution, and derived-output restrictions remain unresolved. | API key, rate limits, premium entitlements, subscription tiers, and endpoint-access constraints remain unresolved. | `primary_docs_found` | Terms review, premium entitlements, local archival/public repo rights, equity point-in-time/revision proof, future dividends handling, and survivorship-safe price history remain unresolved. | `needs_terms_review` | Not source approval; not API approval; not data approval; not point-in-time safe; not strategy ready. |
| phase95_fred | FRED | Benchmark/cash/rate normalization candidate only; not ETF price data. | benchmark/rate source for cash proxy only; API-exported local snapshot | Official API docs, observations docs, real-time-period docs, and API-key docs reportedly found. | Official Terms reportedly found; per-series rights and series-specific licensing still need review. | Observations reportedly include `realtime_start`, `realtime_end`, `date`, and `value`. | Series coverage is per-series; exact benchmark/cash/rate series choice, discontinuation behavior, and continuity remain unresolved. | Not an ETF adjusted-price source; rate units, compounding, frequency conversion, holidays, and missing observations remain unresolved. | Not an ETF corporate-action source; no ETF dividend, split, distribution, or corporate-action claim. | Vintage and as-of behavior appears strongest among the three, but exact per-series revision behavior still needs review. | Real-time period and vintage/as-of concepts were reportedly found and appear strongest among the three; exact selected-series timing rules remain unresolved. | Not an ETF universe or survivorship source; series discontinuation and replacement questions remain per-series. | Per-series rights, local archival rights, raw-row storage, public repo restrictions, redistribution, and citation requirements remain unresolved. | API-key docs reportedly found; key requirements, rate limits, quotas, and access constraints still need review. | `primary_docs_found` | Per-series rights, exact series selection, citation, local storage, rate conversion, publication timing, and benchmark/cash policy remain unresolved. | `candidate_for_repo_normalization_only` | Not ETF price data; not benchmark approval; not cash proxy approval; not rate-series approval; not point-in-time approval for ETF data. |

## Candidate-Specific Normalization

### Stooq

Stooq is normalized as `terms_unclear`.

The external verification output reportedly found official historical and bulk
pages, plus a terms URL. The terms content was not verifiably readable in that
output, so Phase 95 treats terms, storage rights, redistribution rights,
third-party data rights, local archival rights, and public-repo restrictions
as unresolved blockers.

Adjustment methodology, dividend/distribution handling, split handling,
corporate-action handling, timestamp/as-of semantics, revision/correction
policy, inactive/delisted ETF coverage, symbol continuity, survivorship risk,
and normal-pytest independence also remain unresolved.

Allowed later review is limited to direct terms review and/or a provider
support question. No Stooq source use, data use, local storage, local snapshot,
fixture, ingestion, return construction, no-lookahead claim, strategy
validation, or trading use is approved.

### Alpha Vantage

Alpha Vantage is normalized as `primary_docs_found`, but not source-approved.

The external verification output reportedly found official API documentation
and Terms. It also reportedly found daily raw OHLCV, daily adjusted output,
dividends, splits, ETF profile, and listing-status support.

Unresolved blockers include terms review, premium entitlements, API-key and
rate-limit constraints, local archival rights, raw-row storage rights, public
repo restrictions, redistribution restrictions, equity point-in-time proof,
revision/correction policy, future dividend/distribution handling, adjusted
methodology details, survivorship-safe price history, inactive/delisted ETF
coverage, symbol continuity, and normal-pytest independence.

Listing-status support is useful as a later documentation lead, but it does
not prove survivorship-safe price history. Official fields are useful as later
documentation leads, but they do not approve return construction or no-lookahead
semantics.

Allowed later review is limited to terms review and focused provider
documentation review. No Alpha Vantage source use, API use, data use, local
storage, local snapshot, fixture, ingestion, return construction,
no-lookahead claim, strategy validation, or trading use is approved.

### FRED

FRED is normalized as `primary_docs_found` for benchmark/cash/rate candidate
use only. It is not normalized as ETF price data.

The external verification output reportedly found official API documentation,
observations documentation, real-time-period documentation, API-key
documentation, and Terms. Observations reportedly include `realtime_start`,
`realtime_end`, `date`, and `value`. Vintage/as-of behavior appears strongest
among the three reviewed candidates.

Unresolved blockers include per-series rights, series-specific licensing,
exact series selection, citation requirements, local archival rights, raw-row
storage rights, public repo restrictions, redistribution restrictions, API-key
and rate-limit constraints, publication timing, revision behavior by series,
rate-unit interpretation, compounding, frequency conversion, holidays, missing
observations, and normal-pytest independence.

FRED vintage/as-of tools do not make ETF price data point-in-time safe. FRED
does not approve any benchmark, cash proxy, rate series, cash-return
convention, return construction, no-lookahead rule, strategy validation, or
trading use.

Allowed later review may treat FRED as `candidate_for_repo_normalization_only`
for benchmark/cash/rate normalization readiness. That later review remains
non-approving unless a separate phase explicitly resolves the required gates.

## Unresolved Questions

At minimum, later review must still answer:

- What personal local research rights apply?
- Can raw rows be stored locally outside normal pytest?
- Are raw rows or derived snapshots forbidden from public repo commits?
- What public repo restrictions apply?
- What redistribution restrictions apply?
- What citation or attribution requirements apply?
- What local archival rights apply?
- What adjustment methodology is used for adjusted price fields?
- How are dividends and distributions represented, applied, and revised?
- How are splits and other corporate actions represented, applied, and revised?
- What revision or correction policy applies to historical rows?
- What timestamp, publication-time, export-time, and as-of semantics apply?
- Does coverage include inactive, delisted, merged, renamed, or liquidated ETFs?
- Does listing-status support actually connect to survivorship-safe price
  history?
- What rate limits, quotas, premium entitlements, account requirements, API-key
  requirements, or provider constraints apply?
- Can normal `python -m pytest` remain offline, credential-free, source-free,
  and independent from all reviewed providers?
- Can any future local snapshot remain outside normal pytest and avoid real
  data in tests?
- Does the provider documentation separate price return, total return,
  dividend/distribution return, split adjustment, and rate/cash treatment?
- Does the provider documentation support no-lookahead handling for universe,
  benchmark, cash, cost/friction, and return-construction decisions?
- Do per-series or third-party rights override general provider terms?

Unanswered questions remain blockers. Positive answers would still not approve
source use without a separate approval phase.

## Later-Review Ordering Recommendation

Recommended order for later review, not approval:

1. FRED first, limited to benchmark/cash/rate normalization only, because
   official vintage/as-of concepts are clearer and the review does not touch
   ETF price-source approval.
2. Alpha Vantage second, because official docs and Terms were reportedly
   found, but equity point-in-time, revision, entitlement, legal, storage, and
   survivorship questions remain.
3. Stooq third, because terms readability, adjustment methodology,
   survivorship coverage, timestamp/as-of semantics, revision policy, storage
   rights, and third-party rights remain unclear despite operational
   attractiveness.

This is a later-review ordering only. It does not rank, score, select, approve,
recommend for use, validate, or reject any provider for data acquisition,
research use, strategy validation, or trading use.

## Relationship To Prior Phases

Phase 83 defined broad ETF source-path and local snapshot readiness criteria.
Phase 95 adds only advisory primary-source verification normalization. It does
not approve any source path or local snapshot.

Phase 84 added the metadata-only `LocalSnapshotManifest`. Phase 95 does not
change that contract, does not instantiate it for real data, and does not
connect it to planning or replay.

Phase 88 defined return-basis and as-of interpretation boundaries. Official
provider fields do not solve return construction, adjusted-price
interpretation, distribution treatment, total-return construction, or
no-lookahead timing.

Phase 89 defined universe, inception, and survivorship boundaries. Listing
status support does not prove survivorship-safe price history, inactive
coverage, delisting treatment, symbol continuity, inception eligibility, or
universe approval.

Phase 90 defined benchmark and cash timing boundaries. FRED documentation and
vintage/as-of tools may support later benchmark/cash/rate normalization review,
but they do not approve a benchmark, cash proxy, rate series, publication
timing rule, revision rule, compounding rule, or cash-return convention.

Phase 91 defined cost and friction assumptions. Primary-source verification
does not supply an approved cost model, spread assumption, slippage rule,
liquidity threshold, turnover rule, rebalance-cost rule, expense treatment, or
trading-readiness claim.

Phase 93 defined the broad ETF source evidence intake plan. Phase 95 is a
narrower normalization step for external primary-source verification input
under that plan.

Phase 94 normalized earlier source-discovery output as advisory intake
material. Phase 95 records a stronger but still advisory verification layer for
Stooq, Alpha Vantage, and FRED. Primary-source verification does not approve
source use. Official docs do not solve legal or storage rights automatically.
Official fields do not solve return construction. Listing-status support does
not prove survivorship-safe price history. FRED vintage/as-of tools do not
make ETF price data point-in-time safe.

None of this changes normal pytest boundaries. Normal `python -m pytest` must
remain offline, credential-free, source-free, vendor-free, and independent from
real market data.

## Explicit Non-Claims

Phase 95 is:

- not source approval
- not data approval
- not vendor approval
- not benchmark approval
- not cash proxy approval
- not universe approval
- not methodology approval
- not parameter approval
- not evidence approval
- not return-construction approval
- not no-lookahead approval
- not cost/friction approval
- not liquidity approval
- not strategy validation
- not trading readiness

It adds no source approval, data approval, vendor approval, benchmark
approval, cash proxy approval, universe approval, methodology approval,
parameter approval, evidence approval, return-construction approval,
no-lookahead approval, cost/friction approval, liquidity approval, strategy
validation, real data ingestion, raw external data, ETF ticker selection,
benchmark comparison, ranking, scoring, recommendation, candidate discovery
behavior, replay metric, manifest-to-planning bridge, signal/evaluator
behavior, broker/order/fill/portfolio/runtime behavior, LLM call, network
call, market-data call, dashboard/advisory/AI integration, paper behavior,
live behavior, or trading behavior.

## Decision

Decision: advisory primary-source verification normalization only.

Stooq is routed as `terms_unclear`. Alpha Vantage is routed as
`primary_docs_found`, but not source-approved. FRED is routed as
`primary_docs_found` for benchmark/cash/rate normalization review only, not ETF
price data. No source, data, vendor, benchmark, cash proxy, universe,
methodology, parameter, evidence, return-construction policy, no-lookahead
policy, cost/friction model, strategy validation, or trading use is approved.

## Remaining Blockers

- no approved source
- no approved data
- no approved vendor
- no approved benchmark
- no approved cash proxy
- no approved ETF universe
- no approved methodology
- no approved parameter set
- no approved evidence
- no approved return-construction policy
- no approved no-lookahead/as-of policy
- no approved survivorship policy
- no approved benchmark/cash timing policy
- no approved cost/friction model
- no approved liquidity rule
- no approved local snapshot
- no approved raw-row storage policy
- no approved public-repo storage policy
- no strategy-validation claim
- no trading-readiness claim
