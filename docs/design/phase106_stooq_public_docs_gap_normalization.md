# Phase 106 - Stooq Public Docs Gap Normalization

## Purpose

This document normalizes externally produced Stooq public-doc and public-source
gap review output into the deterministic repo documentation trail as advisory
verification material only.

The external review reportedly inspected public Stooq pages and found useful
documentation leads around CSV downloads, bulk ASCII or Metastock-style files,
asset categories, ETF categories, U.S. ETF categories, index categories,
generation timestamps, third-party providers, and dividend or split adjustment
controls. Phase 106 does not independently reopen those pages, download Stooq
data, inspect raw observations, create local data files, add screenshots, add
credentials, add tests, add production behavior, or change any source, replay,
broker, advisory, governance, or runtime code.

The Perplexity output remains external advisory input. It is not legal review,
source approval, data approval, download-path approval, universe approval,
return-construction approval, point-in-time proof, strategy validation, or
trading readiness.

## Normalization Boundary

Phase 106 may normalize Stooq public-doc gap findings only.

It must not approve:

- Stooq
- any Stooq download path
- any data source
- any data
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

Reported public documentation, public download surfaces, terms-page existence,
asset-category listings, generated archive pages, third-party provider
references, schema hints, UI controls, or operational convenience are
documentation leads only. They do not approve Stooq source use, download use,
local storage, local snapshots, repo storage, fixtures, return construction,
point-in-time treatment, no-lookahead treatment, strategy validation, or trading
use.

## Allowed Classification Vocabulary

Allowed `risk_level` values in this document are:

- `low_documented`
- `partially_documented`
- `unclear`
- `high_unresolved`

Allowed `allowed_next_step` values in this document are:

- `needs_repo_normalization`
- `needs_more_primary_docs`
- `needs_terms_review`
- `needs_support_question`
- `reject_for_now`

Forbidden `allowed_next_step` values are:

- `approved`
- `validated`
- `source_approved`
- `data_approved`
- `point_in_time_safe`
- `strategy_ready`
- `trading_ready`

The allowed values route later review only. They do not authorize Stooq
downloads, bulk file use, local snapshots, fixture use, raw-row storage, source
use, universe membership, benchmark use, cash proxy use, return construction,
no-lookahead claims, scoring, ranking, recommendation, strategy validation, or
trading behavior.

## Normalized Public-Docs Gap Table

The table records public-doc findings as advisory gap-normalization context
only. Findings are normalized into repo language; they are not independently
proven by this phase.

| normalized_id | question_area | official_source_status | documented_answer_summary | unresolved_gap | support_question_needed | risk_level | allowed_next_step | non_claims |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phase106_stooq_csv_downloads | Per-instrument CSV downloads | Public Stooq pages reportedly expose per-instrument CSV download paths. | CSV downloads appear available for individual instruments and may include OHLCV-style fields. | Rights, automation rules, storage rights, schema stability, adjustment state, timestamp semantics, and point-in-time behavior remain unresolved. | Ask whether per-instrument CSV downloads may be used for private research, archived locally, stored in private Git, shared publicly, or downloaded by automation. | `partially_documented` | `needs_terms_review` | Not Stooq approval; not download-path approval; not source approval; not data approval. |
| phase106_stooq_bulk_ascii_files | Bulk ASCII and Metastock-style files | Public Stooq archive or database pages reportedly expose bulk ASCII or Metastock-style files. | Bulk files appear operationally attractive for manual local snapshot review. | Terms, bulk-download frequency or volume limits, redistribution, upstream pass-through restrictions, formal schema guarantees, archive mutability, and PIT behavior remain unresolved. | Ask whether bulk files may be downloaded, retained, checksummed, versioned, redistributed, or used for one-time local ETF snapshot review. | `partially_documented` | `needs_terms_review` | Not bulk-download approval; not local snapshot approval; not ingestion approval. |
| phase106_stooq_asset_categories | Public asset categories | Public Stooq pages reportedly list broad asset categories. | Listed categories reportedly include ETFs, U.S. ETFs, indices, equities, crypto, bonds, futures, currencies, and macro-style series. | Category presence does not prove coverage completeness, history depth, rights, ETF survivorship, or source-quality fitness. | Ask whether listed categories have complete histories, inactive coverage, consistent schemas, and use rights for research archival. | `partially_documented` | `needs_support_question` | Not universe approval; not ticker selection; not benchmark approval; not cash proxy approval. |
| phase106_stooq_etf_us_etf_categories | ETF and U.S. ETF category presence | Public Stooq pages reportedly list ETF categories and U.S. ETF categories. | ETF category presence is a documentation lead for later source review. | ETF coverage completeness, inception histories, delisted ETF retention, symbol continuity, mergers, closures, liquidation handling, and PIT universe membership remain unresolved. | Ask whether ETF and U.S. ETF categories include complete active and inactive histories, old symbols, symbol changes, closures, mergers, and inception metadata. | `partially_documented` | `needs_support_question` | Not ETF universe approval; not survivorship approval; not strategy validation. |
| phase106_stooq_indices_categories | Index category presence | Public Stooq pages reportedly list index categories. | Index category presence is a documentation lead for possible later benchmark research. | Index methodology, index membership history, investability, survivorship, data rights, revisions, and benchmark suitability remain unresolved. | Ask whether index data includes methodology, membership history, licensing terms, point-in-time availability, and redistribution limits. | `partially_documented` | `needs_support_question` | Not benchmark approval; not methodology approval; not point-in-time proof. |
| phase106_stooq_ohlcv_schema | CSV, ASCII, and OHLCV-style schema | Public download surfaces reportedly expose CSV or ASCII OHLCV-style data. | Open, high, low, close, volume, or similar historical fields appear available through public file formats. | Formal schema stability, exact column definitions, data types, missing-value handling, timezone conventions, calendar conventions, and adjustment defaults remain unresolved. | Ask for official field definitions, data types, schema-change policy, missing-value policy, timezone/calendar rules, and default adjustment state. | `unclear` | `needs_more_primary_docs` | Not schema approval; not parser approval; not data-quality approval. |
| phase106_stooq_archive_generation_timestamps | Archive generation timestamps | Stooq database or archive pages reportedly show generation timestamps. | Generation timestamps appear to identify when some archive files were produced. | Generation timestamps do not prove immutability, prior vintage access, correction policy, as-of reconstruction, or point-in-time safety. | Ask whether historical generated files are immutable, whether prior vintages are retained, and how corrections or backfills are communicated. | `unclear` | `needs_support_question` | Not point-in-time proof; not no-lookahead approval; not archive approval. |
| phase106_stooq_third_party_providers | Third-party upstream providers | Public Stooq pages reportedly identify third-party providers such as Infront, Barchart, CoinAPI, and others. | Stooq appears to rely on or reference upstream providers for at least some content. | Provider-specific pass-through restrictions, redistribution limits, attribution requirements, category-level source mapping, and conflicts between Stooq terms and upstream terms remain unresolved. | Ask which provider terms apply to ETF, index, equity, crypto, futures, currency, bond, and macro-style data and whether pass-through restrictions limit archival or sharing. | `high_unresolved` | `needs_terms_review` | Not upstream-license clearance; not redistribution approval; not source approval. |
| phase106_stooq_terms_unreadable | Terms-page access and readability | A Stooq terms page reportedly exists, but the external pass did not read or verify the terms text. | Terms existence is a review lead only. | Personal use, commercial use, long-term local archival, raw-row storage, private Git storage, public repo storage, redistribution, automated downloads, attribution, and legal review needs remain unresolved. | Review readable terms text if accessible, then ask Stooq and legal counsel to classify intended research, archival, sharing, and automation behavior. | `high_unresolved` | `needs_terms_review` | Not legal approval; not storage approval; not automation approval. |
| phase106_stooq_automation_limits | Automated download and volume rules | Public download surfaces appear available, but automation rules were not resolved by the external pass. | Manual operational access appears plausible from public pages. | Automated download or scraping rights, frequency limits, volume limits, rate limits, robots policy, account requirements, and bulk-refresh rules remain unresolved. | Ask whether scripted one-time or repeated downloads are allowed and what limits apply before any local snapshot review. | `high_unresolved` | `needs_support_question` | Not automation approval; not download approval; not ingestion approval. |
| phase106_stooq_adjustment_controls | Dividend and split adjustment controls | Public UI reportedly includes controls such as skip dividends and skip splits. | UI controls suggest users may request different dividend or split adjustment behavior. | Default adjustment state, exact meaning of controls, raw versus split-adjusted versus dividend-adjusted versus total-return behavior, and ETF-specific distribution treatment remain unresolved. | Ask for official adjustment methodology, default settings, formula, split treatment, dividend treatment, ETF distribution treatment, and total-return interpretation. | `high_unresolved` | `needs_support_question` | Not return-construction approval; not adjustment-methodology approval; not total-return approval. |
| phase106_stooq_etf_distributions | ETF distributions and fund actions | Public docs in the external pass did not resolve ETF distribution taxonomy. | ETF price/history surfaces appear possible, but fund-action behavior is not documented enough for return construction. | ETF distributions, return of capital, capital gains distributions, special distributions, fund actions, and corporate-action event availability remain unresolved. | Ask whether Stooq exposes ETF distribution events and how each distribution type is reflected in prices, adjusted prices, CSV files, and bulk files. | `high_unresolved` | `needs_support_question` | Not ETF distribution approval; not evidence approval; not methodology approval. |
| phase106_stooq_revisions_mutability | Revisions, backfills, and file mutability | Generation timestamps appear on some archive pages, but revision semantics were not resolved. | Public files may be generated or refreshed, but correction and backfill policy is unclear. | Revisions, corrections, backfills, historical file mutability, immutable archive status, prior vintages, as-of history, missing values, and stale values remain unresolved. | Ask how Stooq handles corrections, whether historical files can change, whether old vintages are preserved, and how missing or stale records are identified. | `high_unresolved` | `needs_support_question` | Not point-in-time safe; not no-lookahead approval; not archive approval. |
| phase106_stooq_delisted_symbol_history | Delisted, inactive, and symbol-change handling | Public asset categories do not resolve inactive security history. | ETF and U.S. ETF category presence is not enough to prove historical universe behavior. | Delisted and inactive ETF handling, old symbol retention, symbol changes, mergers, closures, liquidations, and PIT universe membership remain unresolved. | Ask whether inactive ETFs remain downloadable, how old symbols are retained, how corporate reorganizations are represented, and whether PIT universe membership can be reconstructed. | `high_unresolved` | `needs_support_question` | Not universe approval; not survivorship approval; not ETF ticker selection. |
| phase106_stooq_timezones_calendars | Timezone, calendar, and timestamp semantics | Public CSV or ASCII availability does not resolve timestamp conventions in the external pass. | Daily and possibly intraday data may be downloadable, but exact temporal semantics are not documented enough for modeling. | Timezone conventions, exchange calendar rules, holiday handling, intraday timestamp semantics, availability timing, and decision-time suitability remain unresolved. | Ask for official timezone, calendar, timestamp, session, and publication-timing rules by asset category. | `high_unresolved` | `needs_support_question` | Not no-lookahead approval; not replay approval; not strategy-ready evidence. |
| phase106_stooq_operational_fit | Operational attractiveness | Public Stooq download and archive surfaces appear convenient for manual local snapshots. | Stooq appears operationally attractive relative to sources requiring API keys or complicated endpoint stitching. | Operational convenience does not resolve terms, storage, upstream licensing, schema, adjustment, revisions, PIT, survivorship, or ETF distribution gaps. | Ask legal/support questions before considering any local snapshot route; review more official documentation first. | `unclear` | `needs_terms_review` | Not recommendation to download; not implementation recommendation; not source approval. |
| phase106_stooq_candidate_disposition | Candidate disposition | Public docs appear to answer some availability questions but leave controlling rights, data-quality, PIT, and survivorship gaps. | Stooq remains unresolved, not approved, and not rejected solely from this pass. | Terms text, use rights, storage, redistribution, automation, upstream licensing, schema stability, adjustment methodology, revisions, PIT, and ETF universe behavior remain unresolved. | Ask Stooq support and legal questions and review additional official docs before any future local snapshot review. | `high_unresolved` | `needs_support_question` | Not Stooq approval; not ingestion recommendation; not trading readiness. |

## Questions Answered By Public Docs

As advisory external findings only, Phase 106 records that public Stooq pages
reportedly answer or partially answer these questions:

- per-instrument CSV downloads appear available
- bulk ASCII or Metastock-style files appear available
- broad asset categories are listed
- ETF categories are listed
- U.S. ETF categories are listed
- index categories are listed
- OHLCV-style data appears available
- database or archive pages show generation timestamps
- third-party providers are identified on Stooq pages
- dividend and split adjustment controls appear in the UI

These findings are documentation leads only. They do not approve Stooq, any
download path, any source, any data, any local storage, any repo storage, any
local snapshot, any return construction, any universe, any benchmark, any cash
proxy, any strategy validation, or any trading use.

## Unresolved License And Storage Questions

Phase 106 records these unresolved license and storage questions:

- terms text was not verified or readable in the external pass
- personal non-commercial use
- commercial use
- long-term local archival
- raw row storage
- private Git storage
- public repo storage
- redistribution or sharing of raw rows
- shared examples
- automated download or scraping rules
- bulk download frequency or volume limits
- third-party provider pass-through restrictions
- attribution requirements
- legal review needs

These questions are controlling blockers. No Stooq page, CSV download, bulk
file, raw-row storage, fixture creation, local snapshot, private repo storage,
public repo storage, publication, redistribution, automation, or normal-pytest
dependency is approved by this phase.

## Unresolved Data And Source-Quality Questions

Phase 106 records these unresolved data and source-quality questions:

- formal schema stability
- exact column definitions and types
- timezone and calendar conventions
- intraday timestamp semantics
- coverage depth and start dates per symbol
- ETF coverage completeness
- U.S. ETF completeness
- delisted or inactive ETF retention
- old symbol retention
- symbol changes, mergers, closures, and liquidations
- point-in-time universe membership
- index methodology and membership history

Public category lists and OHLCV-style files are not enough for universe
approval, survivorship-safe price history, ETF ticker selection, benchmark
selection, cash proxy selection, strategy validation, or trading use.

## Unresolved Adjustment And Point-In-Time Questions

Phase 106 records these unresolved adjustment and point-in-time questions:

- default adjustment state
- meaning of skip dividends and skip splits
- raw versus split-adjusted versus dividend-adjusted versus total-return
  behavior
- ETF distributions
- return of capital
- capital gains distributions
- special distributions
- corporate-action event availability
- revisions, corrections, and backfills
- historical file mutability
- immutable archive status
- prior vintages and as-of history
- missing or stale values
- point-in-time reconstruction

Adjustment UI controls do not approve return construction, total-return
interpretation, ETF distribution treatment, vintage handling, no-lookahead
modeling, or strategy validation.

## Candidate Disposition

Stooq disposition remains unresolved.

It is:

- not approved
- not rejected solely from this pass
- operationally attractive but documentation and terms gaps remain large
- `needs_terms_review`
- `needs_support_question`
- `needs_more_primary_docs`

Phase 106 does not recommend ingestion, implementation, parser work, downloads,
fixtures, real data files, local snapshots, source approval, data approval,
universe construction, return construction, benchmark construction, cash proxy
construction, strategy validation, or trading use.

## Allowed Next Steps

Allowed next steps after Phase 106:

- Stooq terms review if terms can be accessed
- Stooq support questions
- legal review
- additional official-doc review
- no downloads yet
- no ingestion
- no repo fixtures or data
- no implementation

Support questions should be drafted outside production code and outside normal
pytest. They should not include credentials or trigger network calls from repo
code.

## Relationship To Prior Phases

Phase 83 defined broad ETF source-path and local snapshot readiness criteria.
Phase 106 adds only advisory Stooq public-doc gap normalization. It does not
approve Stooq as a source path or local snapshot route.

Phase 88 defined return-basis and as-of interpretation boundaries. Stooq CSV,
ASCII, OHLCV-style data, and adjustment controls do not solve return
construction, adjusted-price interpretation, ETF distribution treatment,
total-return construction, or no-lookahead timing.

Phase 89 defined universe, inception, and survivorship boundaries. ETF category
presence, U.S. ETF category presence, and public download availability do not
solve ETF universe approval, inactive coverage, delisting treatment, symbol
continuity, inception eligibility, or survivorship-safe price history.

Phase 91 defined cost and friction assumptions. Stooq public documentation does
not supply an approved cost model, spread assumption, slippage rule, liquidity
threshold, turnover rule, rebalance-cost rule, expense treatment, or
trading-readiness claim.

Phase 93 defined the broad ETF source evidence intake plan. Phase 106 remains
inside that framework and records external Stooq public-doc review as advisory
material only.

Phase 94 normalized earlier source-discovery output as advisory intake
material. Phase 106 continues that separation between scout/documentation
leads and approval.

Phase 95 normalized primary-source verification output for Stooq, Alpha
Vantage, and FRED. Phase 106 expands only the Stooq public-doc gap portion and
keeps Stooq unresolved.

Phase 104 and Phase 105 normalized Alpha Vantage primary-source and public-doc
gap review output. Phase 106 applies the same advisory-only treatment to Stooq:
public availability and operational attractiveness are useful leads, not
approval.

Across these phases:

- public download availability does not approve source use
- CSV or ASCII availability does not approve data use
- ETF category presence does not solve ETF universe or survivorship
- adjustment UI controls do not solve return construction
- terms remain unresolved
- Stooq data must not enter normal pytest through files or downloads

Normal `python -m pytest` must remain offline, credential-free, source-free,
vendor-free, and independent from Stooq.

## Explicit Non-Claims

Phase 106 is:

- not Stooq approval
- not download-path approval
- not source approval
- not data approval
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

It adds no Stooq approval, download-path approval, source approval, data
approval, vendor approval, universe approval, benchmark approval, cash proxy
approval, methodology approval, parameter approval, evidence approval,
return-construction approval, no-lookahead approval, cost/friction approval,
liquidity approval, strategy validation, real data ingestion, raw external data,
local data file, Stooq download, Stooq API or web call, credential, ETF ticker
selection, benchmark comparison, ranking, scoring, recommendation, candidate
discovery behavior in code, replay metric, manifest-to-planning bridge,
signal/evaluator behavior, broker/order/fill/portfolio/runtime behavior, LLM
call, network call, market-data call, dashboard/advisory/AI integration, paper
behavior, live behavior, or trading behavior.

## Decision

Decision: advisory Stooq public-doc gap normalization only.

Stooq remains unresolved. It is not approved and not rejected solely from this
pass. It requires terms review, support questions, legal review as needed, and
more primary-document review before any future local snapshot review can be
considered.

No Stooq source use, download-path use, data use, local storage, local snapshot,
repo storage, fixture, ingestion, universe construction, return construction,
no-lookahead claim, strategy validation, or trading use is approved.

No production code or tests changed. No real data was added. No Stooq downloads
occurred. Normal pytest remains offline and credential-free.

## Remaining Blockers

- no approved Stooq use
- no approved Stooq download path
- no approved source
- no approved data
- no approved ETF universe
- no approved benchmark
- no approved cash proxy
- no approved methodology
- no approved parameter set
- no approved evidence
- no approved return-construction policy
- no approved no-lookahead/as-of policy
- no approved survivorship policy
- no approved delisted or inactive ETF policy
- no approved old-symbol retention policy
- no approved symbol-change, merger, closure, or liquidation policy
- no approved point-in-time universe policy
- no approved adjustment methodology
- no approved ETF dividend or distribution treatment
- no approved return-of-capital treatment
- no approved capital-gains distribution treatment
- no approved split treatment
- no approved total-return interpretation
- no approved revision or correction policy
- no approved vintage procedure
- no approved timestamp/as-of semantics
- no approved timezone or calendar policy
- no approved local snapshot
- no approved raw-row storage policy
- no approved private-repo storage policy
- no approved public-repo storage policy
- no approved redistribution policy
- no approved commercial/internal research policy
- no approved automated-download policy
- no approved third-party provider pass-through policy
- no approved normal-pytest Stooq dependency
- no strategy-validation claim
- no trading-readiness claim

## Follow-Up Recommendation

The likely next step should be a routing checkpoint comparing Alpha Vantage
versus Stooq unresolved gaps and deciding whether to draft support questions,
review another source, or pause source work before more documentation churn.
