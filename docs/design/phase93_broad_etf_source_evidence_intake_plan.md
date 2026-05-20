# Phase 93 - Broad ETF Source Evidence Intake Plan

## Purpose

This document defines a narrow evidence intake plan for future review of
candidate broad ETF data-source paths before any local snapshot use.

It is documentation-only. It defines what evidence must be collected, labeled,
and reviewed before any source path can become even a serious candidate for a
later local snapshot review.

This phase does not browse, download, scrape, call APIs, inspect real data, or
refresh source documentation. External tools such as browser LLMs, Perplexity,
Claude/Gemini, vendor docs, and source websites remain advisory until their
outputs are normalized by a later deterministic docs phase.

## Boundary

Phase 93 may define evidence and intake requirements only.

It must not approve:

- any source
- any data
- any data vendor
- any public download path
- any broker data path
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

No source path becomes selected, preferred, reviewed, approved, validated, or
ready for data acquisition under this phase. No real market data, local
snapshot file, source row, benchmark row, cash-rate row, public download,
vendor export, broker export, API response, or real ETF ticker is added.

## Candidate Source Paths To Investigate

The following source paths are categories only. They may be investigated later,
but none is approved here.

| Source path category | Future intake role | Phase 93 status |
| --- | --- | --- |
| Manual local snapshot | A human-acquired file placed locally after a separately documented acquisition step. | To investigate; not approved. |
| Vendor-exported local snapshot | A file exported from a paid or free data vendor interface for later local storage review. | To investigate; not approved. |
| Broker-exported local snapshot | A historical data export from a broker account, feed, or platform. | To investigate; not approved. |
| Public web/downloaded file | A manually downloaded public file or web export. | To investigate; not approved. |
| API-exported local snapshot | A scripted or manually triggered API export later stored locally; normal pytest must remain offline. | To investigate; not approved. |
| Benchmark/rate source for cash proxy only | A source used only for future benchmark, rate, or cash-proxy evidence review. | To investigate; not approved. |
| Issuer/fund metadata source for context only | Issuer, fund, or metadata pages used only to understand identity, objective, expenses, distributions, or fund context. | Context-only investigation; not approved. |

Prior docs already named example candidates. Phase 93 does not refresh or
review them. They remain to investigate and not approved:

| Prior-doc example | Category mapping | Phase 93 status |
| --- | --- | --- |
| Stooq | Public web/downloaded file or API-exported local snapshot, depending on a later exact route. | Prior context only; to investigate; not approved. |
| Yahoo Finance / yfinance | Public web/downloaded file or API-exported local snapshot, depending on a later exact route. | Prior context only; to investigate; not approved. |
| Nasdaq Data Link | Vendor-exported local snapshot or API-exported local snapshot, depending on a later exact dataset and route. | Prior context only; to investigate; not approved. |
| Alpha Vantage | API-exported local snapshot. | Prior context only; to investigate; not approved. |
| FRED | Benchmark/rate source for cash proxy only. | Prior context only; to investigate; not approved. |
| ETF issuer pages | Issuer/fund metadata source for context only. | Prior context only; context only; not approved. |
| Broker historical data | Broker-exported local snapshot. | Prior context only; context only; not approved. |

## Required Source Evidence

For each future candidate source path, intake must collect and label at least
the following evidence before the source can be considered a serious candidate
for later local snapshot review:

- official source documentation link or citation
- terms/license/access rights
- redistribution restrictions
- data fields available
- asset coverage
- historical coverage
- adjustment policy
- dividend/distribution handling
- split/corporate-action handling
- revision/correction policy
- timestamp/as-of semantics
- download/export mechanics
- authentication/API-key requirement
- rate limits or access limits
- local storage implications
- normal-pytest eligibility status
- known limitations
- non-claims

This evidence is intake material only. It does not approve source use, data
use, local storage, repository storage, raw-row commits, fixture eligibility,
return construction, no-lookahead safety, benchmark/cash use, universe
membership, cost/friction assumptions, strategy validation, or trading use.

## Source-Review Questions

Future review must answer these questions for each exact source path:

- Can this source legally be used for personal local research?
- Can raw rows be stored locally?
- Can raw rows be committed to the repo? The expected answer remains no unless
  a future policy explicitly approves a narrow exception.
- Are adjusted prices transparent enough for the intended later review?
- Is total-return data available or constructible?
- Are timestamps and as-of semantics clear?
- Are corrections or revisions possible?
- Are inactive or delisted ETFs available?
- Is survivorship bias likely?
- Does the source cover benchmark/cash needs or only ETF prices?
- Does using this source require credentials or network access?
- Can normal pytest remain independent from this source?
- Does the source document dividend, distribution, split, and corporate-action
  handling?
- Does the source document historical coverage start dates and gaps?
- Does the source permit deterministic local snapshotting outside normal
  pytest?
- Does the source create redistribution, private-repo, or derived-publication
  constraints?
- Does the source have access tiers, API keys, rate limits, subscriptions, or
  broker/account entitlements that would affect reproducibility?

Unanswered questions remain blockers. Positive answers are not approvals; they
only make later docs-only review more concrete.

## Intake Evidence Labels

Future intake records should use these labels:

- `official_source_doc`
- `terms_or_license`
- `data_dictionary`
- `adjustment_policy`
- `corporate_action_policy`
- `revision_policy`
- `coverage_note`
- `survivorship_note`
- `timestamp_asof_note`
- `storage_rights_note`
- `normal_pytest_note`
- `unresolved`

Labels are descriptive tags only. They do not validate the evidence or approve
the source.

## Review Outcomes

Allowed review outcomes are:

- `reject_for_now`
- `context_only`
- `candidate_needs_more_evidence`
- `candidate_for_later_local_snapshot_review`

Forbidden outcomes are:

- `approved`
- `validated`
- `source_approved`
- `data_approved`
- `strategy_ready`
- `trading_ready`

An allowed outcome routes future work only. It does not authorize data
acquisition, data storage, source use, test fixture use, implementation,
result inspection, strategy validation, or trading behavior.

## Minimal Intake Table

The starter table below is an intake template, not evidence and not approval.
Rows with `TBD` are placeholders. Rows with names are included only because
prior docs already named them; every named row remains not reviewed and not
approved in Phase 93.

| candidate_id | source_path_category | source_or_vendor_name | intended_use | evidence_needed | current_status | blockers | allowed_next_step | non_claims |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| source_path_manual_local_snapshot_tbd | manual local snapshot | TBD | Future local snapshot route review only. | All Phase 93 evidence labels. | Placeholder only; not reviewed; not approved. | Exact source, rights, fields, storage, timing, and normal-pytest status absent. | External evidence collection outside deterministic repo, then docs-only normalization. | Not source approval; not data approval. |
| source_path_vendor_export_tbd | vendor-exported local snapshot | TBD | Future vendor export review only. | All Phase 93 evidence labels. | Placeholder only; not reviewed; not approved. | Vendor identity, license, fields, coverage, revisions, and storage rights absent. | External evidence collection outside deterministic repo, then docs-only normalization. | Not vendor approval; not source approval; not data approval. |
| source_path_broker_export_tbd | broker-exported local snapshot | TBD | Future broker export review only. | All Phase 93 evidence labels. | Placeholder only; not reviewed; not approved. | Credentials, account terms, feed terms, entitlement, redistribution, and offline status absent. | External evidence collection outside deterministic repo, then docs-only normalization. | Not broker data approval; not trading approval. |
| source_path_public_download_tbd | public web/downloaded file | TBD | Future public download route review only. | All Phase 93 evidence labels. | Placeholder only; not reviewed; not approved. | Terms, redistribution, fields, adjustment semantics, revisions, and storage rights absent. | External evidence collection outside deterministic repo, then docs-only normalization. | Not public download approval; not data approval. |
| source_path_api_export_tbd | API-exported local snapshot | TBD | Future API export review only. | All Phase 93 evidence labels. | Placeholder only; not reviewed; not approved. | API terms, key/rate limits, endpoint fields, revisions, and offline snapshot status absent. | External evidence collection outside deterministic repo, then docs-only normalization. | Not API approval; normal pytest remains offline. |
| source_path_benchmark_rate_tbd | benchmark/rate source for cash proxy only | TBD | Future benchmark/rate/cash-proxy evidence review only. | All Phase 93 evidence labels. | Placeholder only; not reviewed; not approved. | Series identity, publication timing, revisions, compounding, storage, and citation absent. | External evidence collection outside deterministic repo, then docs-only normalization. | Not benchmark approval; not cash proxy approval. |
| source_path_issuer_metadata_tbd | issuer/fund metadata source for context only | TBD | Future fund identity and context review only. | All Phase 93 evidence labels. | Placeholder only; not reviewed; not approved. | Issuer terms, historical availability, archival rights, and point-in-time metadata absent. | External evidence collection outside deterministic repo, then docs-only normalization. | Not source approval; not universe approval. |
| prior_stooq | public web/downloaded file or API-exported local snapshot | Stooq | Prior-doc ETF price-data route context only. | All Phase 93 evidence labels. | Prior context only; not reviewed in Phase 93; not approved. | Terms, local snapshot rights, adjustment, dividends, corporate actions, revisions, symbol identity, and redistribution unresolved. | External source discovery and advisory evidence collection outside deterministic repo. | Not source approval; not data approval; not return-construction approval. |
| prior_yahoo_yfinance | public web/downloaded file or API-exported local snapshot | Yahoo Finance / yfinance | Prior-doc ETF price-data route context only. | All Phase 93 evidence labels. | Prior context only; not reviewed in Phase 93; not approved. | Terms, automation, storage/cache, archival, API stability, adjusted-data methodology, and redistribution unresolved. | External source discovery and advisory evidence collection outside deterministic repo. | Not source approval; not data approval; not vendor approval. |
| prior_nasdaq_data_link | vendor-exported local snapshot or API-exported local snapshot | Nasdaq Data Link | Prior-doc dataset or endpoint route context only. | All Phase 93 evidence labels. | Prior context only; not reviewed in Phase 93; not approved. | Exact dataset, access tier, terms, coverage, rate limits, adjustments, storage, and redistribution unresolved. | External source discovery and advisory evidence collection outside deterministic repo. | Not source approval; not data approval; not vendor approval. |
| prior_alpha_vantage | API-exported local snapshot | Alpha Vantage | Prior-doc API route context only. | All Phase 93 evidence labels. | Prior context only; not reviewed in Phase 93; not approved. | API key, rate limits, coverage, adjustment methodology, terms, local snapshot rights, and redistribution unresolved. | External source discovery and advisory evidence collection outside deterministic repo. | Not source approval; not data approval; not API approval. |
| prior_fred_cash_proxy | benchmark/rate source for cash proxy only | FRED | Prior-doc cash/risk-free proxy context only. | All Phase 93 evidence labels. | Prior context only; not reviewed in Phase 93; not approved. | Series choice, publication timing, revisions, frequency alignment, conversion, storage, citation, and API terms unresolved. | External source discovery and advisory evidence collection outside deterministic repo. | Not benchmark approval; not cash proxy approval; not rate-series approval. |
| prior_issuer_pages | issuer/fund metadata source for context only | ETF issuer pages | Prior-doc issuer/fund context only. | All Phase 93 evidence labels. | Prior context only; context only; not reviewed in Phase 93; not approved. | Issuer-specific terms, page archival, historical metadata, point-in-time changes, and redistribution unresolved. | External source discovery and advisory evidence collection outside deterministic repo. | Not source approval; not data approval; not universe approval. |
| prior_broker_historical_data | broker-exported local snapshot | Broker historical data | Prior-doc broker-data context only. | All Phase 93 evidence labels. | Prior context only; context only; not reviewed in Phase 93; not approved. | Credentials, account/subscription entitlements, feed terms, runtime access, exchange terms, and offline snapshot policy unresolved. | External source discovery and advisory evidence collection outside deterministic repo. | Not broker data approval; not source approval; not trading approval. |

## Relationship To Prior Phases

Phase 83 defined broad ETF source-path and local snapshot readiness criteria.
Phase 93 narrows the next docs-only step to evidence intake requirements. It
does not approve any source path or local snapshot.

Phase 84 added `LocalSnapshotManifest` as a frozen, slotted, metadata-only
contract. Phase 93 does not change that contract and does not connect it to
planning, replay, source acquisition, or real data.

Phase 88 defined return-basis and as-of interpretation boundaries. Source
terms and documentation do not solve return construction. A source can describe
fields while still leaving adjustment, total-return, revision, and availability
questions unresolved.

Phase 89 defined universe, inception, and survivorship boundaries. Source
coverage does not solve universe membership, inactive-fund availability,
delisting treatment, symbol continuity, or survivorship bias.

Phase 90 defined benchmark and cash timing boundaries. A source that offers
benchmark or rate data does not approve a benchmark, cash proxy, publication
timing rule, revision policy, compounding rule, or cash-return convention.

Phase 91 defined cost and friction assumptions. Source data does not supply an
approved cost model, spread assumption, slippage rule, liquidity threshold,
turnover rule, rebalance-cost rule, or trading-readiness claim.

Across all prior phases:

- source evidence does not approve source use
- source terms do not solve return construction
- source coverage does not solve universe or survivorship
- source timestamps do not automatically prove no-lookahead safety
- source data does not make normal pytest depend on real data

## Explicit Non-Claims

Phase 93 is:

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

It also adds no real data ingestion, no real market data, no real ETF tickers,
no benchmark comparison, no cash return series, no rate series, no
expense-ratio series, no spread series, no liquidity screen, no threshold, no
ranking, no scoring, no recommendation, no candidate discovery, no replay
metrics, no report rendering, no manifest-to-planning bridge, no signal or
evaluator behavior, no advisory integration, no governance behavior, no
broker, order, fill, portfolio, runtime, paper, live, or trading behavior, and
no LLM, network, API, provider, rate-series, or market-data call.

## Decision

Decision: source evidence intake plan only.

The project is not ready to approve or use any broad ETF source path. The next
step should likely be external source discovery outside the deterministic repo
path, followed by a later normalization/intake phase that records advisory
evidence summaries in docs only. That future phase must still avoid source
approval, data approval, universe approval, benchmark approval, cash proxy
approval, methodology approval, parameter approval, evidence approval,
return-construction approval, no-lookahead approval, cost/friction approval,
liquidity approval, strategy validation, real data ingestion, normal-pytest
real-data dependencies, and trading behavior.

## Remaining Blockers

- no approved source
- no approved data
- no approved data vendor
- no approved public download path
- no approved broker data path
- no approved local snapshot
- no approved storage rule for raw third-party market data
- no approved ETF universe
- no approved benchmark
- no approved cash proxy
- no approved methodology
- no approved parameter set
- no approved evidence
- no approved adjustment policy
- no approved return basis
- no approved return construction
- no approved no-lookahead/as-of policy
- no approved inception/survivorship policy
- no approved benchmark/cash timing
- no approved cost/friction model
- no approved liquidity rule
- no implementation-readiness claim
- no strategy-validation claim
- no trading-readiness claim
