# Phase 32 Step 16 - S05 Public Documentation Verification Sweep

## Purpose

This document records what appears supported by public documentation for S05
candidate data sources.

It does not replace direct vendor, source-owner, or license confirmation. It
does not select, approve, purchase, subscribe to, acquire, download, ingest,
store, transform, validate, reproduce, promote, or implement any data source.
It does not authorize a provider decision, dataset schema, notebook, script,
backtest engine, evaluator, signal computation, production threshold,
`ValidatedResearchArtifact`, or `ValidatedSignalDefinition`.

The externally provided Perplexity public-documentation research report is
treated as external scout research input only. It is not a source of truth, not
a license approval, not a vendor confirmation, and not a dataset decision.

## Source-of-Truth Inputs

This sweep depends on the existing controlled S05 trail:

- [`phase32_p30_bl_002_s05_formal_review.md`](phase32_p30_bl_002_s05_formal_review.md)
- [`phase32_s05_deterministic_reproduction_planning_boundary.md`](phase32_s05_deterministic_reproduction_planning_boundary.md)
- [`phase32_s05_data_availability_assessment_boundary.md`](phase32_s05_data_availability_assessment_boundary.md)
- [`phase32_s05_data_provider_source_comparison_plan.md`](phase32_s05_data_provider_source_comparison_plan.md)
- [`phase32_s05_data_provider_scout_research_normalization.md`](phase32_s05_data_provider_scout_research_normalization.md)
- [`phase32_s05_primary_verification_questionnaire.md`](phase32_s05_primary_verification_questionnaire.md)
- [`phase32_p30_bl_002_source_status_index.md`](phase32_p30_bl_002_source_status_index.md)

This sweep normalizes public-documentation signals reported externally. It does
not independently certify the completeness, accuracy, currentness, licensing,
or contract semantics of any source.

## Evidence-Quality Policy

Evidence quality must be separated before any routing label is read:

- Primary documentation means public material from the source owner, vendor,
  exchange, academic data-library owner, or platform owner.
- Secondary documentation means third-party summaries, articles, user reports,
  forum posts, reseller descriptions, or comparative writeups.
- Inference means the project-level conclusion drawn from documentation, scout
  summaries, or missing evidence.

Public vendor documentation may support cautious routing labels, but it does
not equal legal approval, signed license approval, local archival permission,
private repository permission, offline-use permission, or deterministic
snapshot support. Marketing claims remain provisional until supported by
detailed documentation or direct vendor/source confirmation.

Perplexity output is external research input only. It may point to public
documentation or summarize it, but its conclusions are not verified project
facts unless a later phase checks them against primary sources and records the
evidence.

## Sources Reviewed

This sweep covers the following S05 candidate data-source categories:

- AQR TSMOM factor data
- CSI
- Pinnacle / CLC
- Norgate futures package
- Portara / PortaraCQG
- TradeStation
- Institutional feeds such as Bloomberg, LSEG, and Datastream at high level
  only
- Broker-native historical APIs
- Public/free APIs and ETF/index proxies

No data was acquired, downloaded, sampled, ingested, or stored.

## Verification Sweep Table

| Source/category | Public documentation reviewed | Source quality | What appears documentation-supported | What remains unclear | S05 coverage implication | PIT/as-of implication | Offline reproducibility implication | Licensing implication | Pricing/access implication | Current feasibility label | Still requires direct confirmation | Allowed next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AQR TSMOM factor data | Public AQR factor/data-library and TSMOM construction material reported by the external scout research | Primary documentation for public factor availability; inference for S05 suitability | Factor-level time-series momentum context appears publicly documented | Raw instrument-level futures/forwards panel access, exact instrument mapping, versioning, and redistribution terms remain unverified | Useful for calibration, context, or high-level comparison only unless raw panel access is later verified | Public factor series do not establish PIT/as-of source-data replay for project-local instrument observations | Possible offline use of public files must still be checked against terms and versioning; not raw deterministic reproduction | Public availability is not license approval for local archive, private repo use, or derived publication | Public access may exist for factor files, but deeper/raw access is unknown | calibration/context only | Raw panel availability, S05 universe mapping, construction inputs, versioning, local archive rights, private repo rights, and derived-statistics rights | Keep as calibration/context unless raw instrument-level access is directly verified |
| CSI | Public vendor documentation for historical futures and continuous contract products reported by the external scout research | Primary documentation plus project inference | Long-history futures products and continuous-series tooling appear documentation-supported | Exact S05 universe mapping, January 1965 through December 2009 coverage by instrument, individual contract access, roll rules, PIT/versioning, corrections, licensing, and archival rights remain unresolved | Potential partial S05 candidate, but exact reproduction is not established | PIT/as-of and historical-version preservation are unresolved | Export and local replay may be possible only after entitlement, export, version, and archival rights are confirmed | Public docs do not establish signed permission for local archive, private repository reference, automated tests, or publication of derived statistics | Pricing, subscription, entitlement, and renewal terms require confirmation | documentation-supported partial candidate | Coverage by instrument, raw contracts, continuous construction, roll metadata, correction history, PIT/as-of/versioning, local archive rights, private repo rights, automated local test rights, and price | Keep in direct-confirmation queue; use Step 15 questionnaire before any dataset decision |
| Pinnacle / CLC | Public Pinnacle/CLC documentation and product descriptions reported by the external scout research | Primary documentation plus inference | Continuous futures and commodity history appear documentation-supported | Exact cross-asset S05 coverage, asset-class breadth beyond commodities, individual contract availability, roll methodology, PIT/versioning, corrections, and license terms remain unresolved | Useful partial/proxy candidate for continuous futures and commodities; exact S05 replication is not established | PIT/as-of and method-change history remain unresolved | Offline deterministic replay depends on export rights, version references, and roll metadata | License must directly allow local archive, private repo reference, local tests, and derived-statistics publication | Pricing and access terms require confirmation | documentation-supported partial candidate | Cross-asset coverage, raw contract availability, historical depth, CLC roll details, method changes over time, versioning, local archival rights, and pricing | Keep in direct-confirmation queue; treat as partial/proxy until confirmed |
| Norgate futures package | Public Norgate product documentation reported by the external scout research | Primary documentation plus inference | Futures package and modern research workflow support appear documentation-supported | Exact 1965-2009 S05 coverage, early-history depth, raw contract availability, continuous construction, PIT/versioning, and licensing remain unresolved | Likely more realistic for a modern or reduced-universe study than exact 1965-2009 S05 replication | PIT/as-of semantics and prior-version preservation require confirmation | Offline workflow and snapshot support require license and export confirmation | Public docs do not establish local archive, private repo, automated test, or derived-statistics permission | Product access, subscription terms, and entitlement details require confirmation | documentation-supported proxy candidate | Start dates by instrument, raw versus continuous access, roll methodology, versioning, correction handling, offline rights, and pricing | Keep in direct-confirmation queue; route as modern/reduced-universe proxy unless stronger evidence appears |
| Portara / PortaraCQG | Public Portara and PortaraCQG product documentation reported by the external scout research | Primary documentation plus inference | Deep futures history and professional futures-data tooling appear documentation-supported at a public-doc level | S05 mapping, instrument-by-instrument history, roll methodology, roll metadata, PIT/versioning, corrections, license terms, pricing, and local archival rights remain unresolved | Potential partial candidate if the historical breadth maps to S05; no exact S05 claim is established | PIT/as-of and correction-version preservation require direct confirmation | Deterministic local replay depends on exported files, metadata, checksums, and permission to keep snapshots | License must directly confirm offline archive, private repo, automated local tests, and derived-statistics publication | Pricing and access are unresolved | documentation-supported partial candidate | Exact universe coverage, January 1965 through December 2009 depth, raw contracts, roll metadata, method changes, versioning, correction handling, offline rights, and cost | Keep in direct-confirmation queue; do not treat deep-history claims as enough for source approval |
| TradeStation | Public platform and historical-data documentation reported by the external scout research | Primary documentation plus inference | Platform historical data access appears documented for some use cases | Owner access, futures history depth, export rights, offline archival, roll semantics, individual contract coverage, and reproducibility remain unresolved | Likely unsuitable as a primary S05 source; may be a lightweight recent-period proxy/check source only if rights and access are verified | PIT/as-of semantics and version preservation are not established | Online/platform dependency may conflict with offline deterministic replay unless exports can be frozen legally | Export, local archive, private repo, and derived-statistics rights must be confirmed | Account, entitlement, platform, and data-subscription requirements may apply | likely unsuitable | Owner access, export rights, history depth, roll metadata, offline archive permission, and pricing | Keep conditional/proxy-only unless project-owner access and export/archival rights are verified |
| Institutional feeds: Bloomberg, LSEG, Datastream | High-level public institutional-feed documentation and external scout summary | Primary documentation at a category level plus inference | Broad institutional coverage, metadata, and professional history may be available in theory | Personal access, cost, license restrictions, redistribution, local export, private repo use, PIT/versioning, and reproducible offline replay remain unresolved | Theoretically strong, but out of current personal/offline project scope unless access and licensing change materially | PIT/as-of support may exist in some products but is not confirmed for this project | Offline deterministic replay is blocked until export, archival, and version rights are explicit | Institutional licenses may restrict storage, redistribution, and private repo usage | Pricing and entitlement requirements are likely material blockers | calibration/context only | Specific product entitlement, export rights, PIT/versioning, local archive rights, private repo rights, automated test rights, derived-statistics rights, and cost | Record as high-level context only; do not pursue unless access/licensing becomes realistic |
| Broker-native historical APIs | Public broker/API documentation and external scout summary | Primary documentation at platform level plus inference | Recent historical bars or contract data may be documented for some broker/platform APIs | Long-history depth, futures/forwards breadth, PIT/as-of/versioning, local archival rights, roll metadata, and credential-free offline replay remain unresolved or unlikely | Unsuitable as primary S05 reproduction source under current constraints | PIT/as-of and correction-version support are not established | Normal project tests must stay credential-free and offline; broker APIs imply runtime/network/account dependencies unless frozen exports are separately licensed | Broker data licenses may restrict storage, reuse, and redistribution | Access may require accounts, credentials, subscriptions, or entitlements | likely unsuitable | Historical depth, futures coverage, export rights, offline archive permission, roll semantics, versioning, and credential-free local replay | Mark unsuitable for primary S05 reproduction; consider only separately approved proxy checks |
| Public/free APIs and ETF/index proxies | Public API, index, and ETF documentation categories reported by the external scout research | Primary or secondary documentation by source; inference for S05 suitability | Some proxy series, ETFs, indexes, or recent market data may be publicly documented | Exact futures/forwards universe, pre-1980 history, roll construction, excess-return inputs, survivorship, licensing, corrections, and deterministic versioning remain unresolved | Proxy-only; not primary S05 reproduction data | PIT/as-of and prior-version replay are generally unresolved for this purpose | Offline snapshots may be possible only after terms, checksums, and version references are verified | Free/public access does not imply archive, repo, automated test, or publication rights | Pricing may be low or free, but quality, limits, and terms remain constraints | documentation-supported proxy candidate | Instrument list, inception dates, license, construction methods, revision handling, versioning, offline archive rights, and publication rights | Keep proxy-only; do not use for serious S05 futures replication |

## Direct Confirmation Backlog

The following questions remain open for direct vendor, source-owner, or
license confirmation:

- exact S05 universe mapping
- January 1965 through December 2009 coverage by instrument
- individual contract availability
- continuous contract construction
- roll methodology and roll metadata
- whether roll methods changed over time
- PIT/as-of/versioning
- preservation of previous versions after corrections
- survivorship/delisting handling
- corrections/revisions handling
- missing-data and quality flags
- excess-return inputs
- collateral/risk-free assumptions
- currency handling
- local archival permission
- private repo permission
- automated local test usage permission
- derived-statistics publication permission
- offline use after acquisition
- deterministic snapshot/version support
- pricing/subscription terms

No source can move beyond cautious routing until these gaps are answered
clearly enough for the intended use.

## Recommended Next Routing

Do not choose a provider yet.

Keep CSI, Pinnacle, Norgate, and Portara in the direct-confirmation queue.
Keep AQR as calibration/context unless raw instrument-level access is verified.
Keep TradeStation conditional and proxy-only unless project-owner access plus
export, archival, and offline-use rights are verified.

Mark broker-native APIs, public/free APIs, and ETF/index proxies as unsuitable
for primary S05 reproduction. They may be considered only for separately
approved proxy checks or methodology rehearsal, without S05 validation claims.

Do not design a dataset schema yet unless a later phase explicitly decides
there is enough source clarity. Do not acquire data, ingest data, approve
reproduction, validate S05, or authorize implementation from this sweep.

## Explicit Non-Goals

This phase does not add or authorize:

- provider choice
- purchase
- subscription decision
- data acquisition
- data download
- data ingestion
- dataset storage
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
- production-readiness claim
- implementation-readiness claim
- profitability, actionability, or trading implication
- broker, OMS, runtime, scheduler, persistence, portfolio, ledger,
  reconciliation, Alpaca, ML, or LLM trading-path behavior

## Remaining Blockers

Evaluator implementation and any production route remain blocked by all of the
following:

- no exact `ValidatedResearchArtifact`
- no exact `ValidatedSignalDefinition`
- no selected/approved dataset
- no completed primary-source vendor verification
- no acquired data
- no project-local deterministic reproduction
- no production threshold/config provenance
- no applied no-lookahead audit inside the project
- no implementation-scope approval
- no evaluator tests
- unresolved exact S05 universe reconstruction
- unresolved instrument-level January 1965 through December 2009 coverage
- unresolved raw contract versus continuous-contract availability
- unresolved roll methodology and roll metadata
- unresolved PIT/as-of/versioning and correction history
- unresolved survivorship, delisting, missing-data, and quality-flag handling
- unresolved excess-return, collateral, risk-free, and currency assumptions
- unresolved licensing, local archival, private repository, automated test,
  and derived-statistics publication rights
- unresolved deterministic offline snapshot path for any candidate source
- unresolved pricing and subscription terms

Do not start implementation from this sweep.

## Verification

Verification after Phase 32 Step 16:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
passed; Git emitted LF-to-CRLF working-copy warnings only for modified docs

git status --short
 M docs/design/phase31_research_track_next_action_plan.md
 M docs/design/phase32_p30_bl_002_source_status_index.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_s05_public_documentation_verification_sweep.md
```

Manual documentation checks confirmed that edited markdown files have no
trailing whitespace, exactly one final newline, no truncation, and intact final
sections.
