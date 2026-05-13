# Phase 32 Step 15 - S05 Primary Verification Questionnaire

## Purpose

This document is a primary-verification questionnaire and outreach template
only. It is intended to support future manual outreach or primary
documentation review for candidate `P30-BL-002-S05` data sources.

This document does not select, approve, purchase, subscribe to, acquire,
download, ingest, store, transform, validate, reproduce, promote, or implement
any data source. It does not authorize a vendor decision, schema design,
notebook, script, backtest engine, evaluator, signal computation, production
threshold, `ValidatedResearchArtifact`, or `ValidatedSignalDefinition`.

No outreach is performed by this document or by project code. Any future
message must be sent manually by the project owner after separate approval.

## Source-of-Truth Inputs

This questionnaire depends on the existing controlled S05 trail:

- [`phase32_p30_bl_002_s05_formal_review.md`](phase32_p30_bl_002_s05_formal_review.md)
- [`phase32_s05_deterministic_reproduction_planning_boundary.md`](phase32_s05_deterministic_reproduction_planning_boundary.md)
- [`phase32_s05_data_availability_assessment_boundary.md`](phase32_s05_data_availability_assessment_boundary.md)
- [`phase32_s05_data_provider_source_comparison_plan.md`](phase32_s05_data_provider_source_comparison_plan.md)
- [`phase32_s05_data_provider_scout_research_normalization.md`](phase32_s05_data_provider_scout_research_normalization.md)
- [`phase32_p30_bl_002_source_status_index.md`](phase32_p30_bl_002_source_status_index.md)

Scout-level findings remain unverified. This questionnaire is a tool for
asking better questions before any future dataset-selection decision.

## Target Sources

Primary verification should focus on:

- CSI
- Pinnacle
- Norgate
- AQR
- TradeStation, only if project-owner access already exists or is expected

TradeStation is conditional. It should not be pursued as a required source path
unless access, export rights, and offline freezing are realistic for the
project owner.

## General Verification Questions

Ask or document the following before classifying any source beyond unresolved
primary-verification status:

- What exact instruments, contracts, asset classes, and exchanges are covered?
- Can coverage map materially to the S05 58 futures/forwards universe?
- Does coverage include January 1965 through December 2009?
- Does the source provide individual contracts, continuous contracts, or both?
- What roll methodology is used, and did it change over time?
- Is roll metadata provided, including roll dates, selected contracts, and
  adjustment or linking rules?
- Does the source support PIT/as-of/versioned data access or frozen historical
  snapshots?
- How are survivorship, delisting, discontinuation, renaming, and replacement
  events treated?
- How are restatements, revisions, corrections, backfills, and deleted records
  handled?
- Which inputs are available for excess-return construction, including cash,
  collateral, financing, compounding, and timing assumptions?
- How are currency denomination, FX conversion, and timestamp alignment
  handled?
- Are transaction cost, slippage, volume, open interest, liquidity, margin, or
  related fields available?
- Are missing-data flags, stale-price indicators, outlier flags, or other data
  quality metadata available?
- What license terms apply to personal local research use?
- Is private local archival of acquired exports permitted?
- Is storage or reference inside a private repository permitted?
- May derived statistics be published without raw data redistribution?
- Is offline use after acquisition permitted without recurring network,
  credential, or vendor runtime dependency?
- Can the project create a deterministic file/version snapshot with source
  date, export version, checksums, and stable provenance?
- What cost, subscription, renewal, entitlement, or access requirements apply?

Missing or ambiguous answers must remain explicit gaps.

## Source-Specific Questions

### AQR

- Is only factor-level data available, or can any raw or instrument-level
  panel be accessed?
- Are TSMOM factor construction details sufficient for calibration/context use
  without implying raw S05 reproduction?
- What instrument universe, date range, weighting, volatility scaling, return
  construction, and transaction cost assumptions are documented?
- Are there redistribution, derived-statistic, citation, or publication
  restrictions?
- Is any versioned download or archival reference available for deterministic
  offline review?

### CSI

- What contract-level futures coverage is available by market and exchange?
- What continuous-series options are available, and are they separate from
  individual contract history?
- What are the earliest reliable coverage dates by asset class?
- Which export formats, dictionaries, identifiers, and metadata files are
  available?
- How are export versioning, corrections, and historical snapshots handled?
- What are the roll methodology, back-adjustment, stitching, and return-linking
  details for continuous series?

### Pinnacle

- What are the CLC methodology details, including roll trigger, roll date,
  selected delivery month, and adjustment policy?
- What asset-class breadth exists beyond commodities?
- What historical depth is available by market, especially before 1980?
- Are individual contracts available, or only linked/continuous series?
- Are quality flags, missing-data indicators, and correction histories
  available?
- What private local research, archival, and derived-statistic publication
  rights apply?

### Norgate

- What are the start dates by market, exchange, and asset class?
- Are individual contracts available, continuous futures available, or both?
- What export and offline workflow is supported?
- Are roll rules, adjustment methods, and version identifiers documented?
- Do 1965-1980 gaps make the source partial/proxy only for S05?
- What license terms govern local archival, private repository use, and
  derived-statistics publication?

### TradeStation

TradeStation should be included only if project-owner access exists or is
expected.

- What access level, account status, entitlement, or platform subscription is
  required?
- What historical futures coverage and depth are available for export?
- Are individual contracts, continuous contracts, roll metadata, and
  adjustment rules accessible?
- What export rights apply for private local research?
- Can exported data be frozen offline with deterministic version metadata?
- Are local archival, private repository use, and derived-statistics
  publication permitted?

## Response-Capture Table

Use this table for primary documentation findings or manual responses. Do not
treat blank rows as evidence.

| Source | Question area | Answer received / documented answer | Evidence link or contact reference | Confidence | Reproduction implication | Licensing implication | Follow-up needed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CSI |  |  |  |  |  |  |  |
| Pinnacle |  |  |  |  |  |  |  |
| Norgate |  |  |  |  |  |  |  |
| AQR |  |  |  |  |  |  |  |
| TradeStation (conditional) |  |  |  |  |  |  |  |

Suggested confidence labels are `low`, `medium`, and `high`. Confidence should
reflect primary-source specificity, not optimism about the source.

## Decision Routing Rules

Use these routing labels only after primary verification is documented:

- Exact reproduction candidate: only if the S05 universe, January 1965 through
  December 2009 period, data semantics, PIT/as-of needs, roll treatment,
  reproducible export path, and licensing are materially satisfied.
- Partial candidate: coverage is strong but incomplete, with documented gaps
  that prevent exact S05 reproduction.
- Proxy candidate: the universe or period differs materially, but the
  methodology shape can be tested without S05 validation claims.
- Calibration/context only: only factor-level, summary, or construction-detail
  data is available.
- Reject: licensing, offline use, PIT/as-of support, coverage, metadata,
  quality, or deterministic snapshot gaps are unacceptable.
- Unresolved: primary verification is incomplete or contradictory.

No routing label validates S05, approves data, authorizes acquisition, or
authorizes implementation.

## Outreach Template

The project owner may adapt and send the following manually:

```text
Subject: Historical futures data coverage and local research-use questions

Hello,

I am evaluating historical futures data for a private, local research project.
Could you please clarify whether your data offering can support the following?

- Historical futures coverage by market, exchange, and asset class, including
  whether coverage can extend through January 1965 to December 2009.
- Availability of individual contract history, continuous futures history, or
  both.
- Documentation for roll methodology, back-adjustment or return-linking rules,
  roll dates, selected contracts, and whether the methodology changed over
  time.
- Point-in-time, as-of, versioning, correction, restatement, and frozen export
  support.
- Treatment of delisted, discontinued, renamed, replaced, or otherwise
  unavailable contracts.
- Available fields for returns, currency handling, transaction costs,
  slippage, liquidity, open interest, volume, missing-data flags, and quality
  metadata.
- Whether exported data may be archived locally for private research and used
  offline without ongoing network or platform access.
- Whether references or derived statistics may be stored in a private
  repository and whether derived statistics may be published without
  redistributing raw data.
- Pricing, subscription, renewal, entitlement, or account requirements.

I am not asking for redistribution rights to raw data. I am trying to
understand coverage, methodology, reproducibility, offline archival rights, and
pricing before making any dataset decision.

Thank you,
[Your name]
```

This template is vendor-neutral. It should be adjusted only by the project
owner and should not include credentials, account information, broker state, or
private repository contents.

## Explicit Non-Goals

This phase does not add or authorize:

- vendor decision
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
- unresolved roll, continuous-contract, and excess-return semantics
- unresolved PIT/as-of, survivorship, restatement, revision, and correction
  treatment
- unresolved licensing, local archival, private repository, and
  derived-statistic publication rights
- unresolved deterministic offline snapshot path for any candidate source

Do not start implementation from this questionnaire.

## Verification

Verification after Phase 32 Step 15 should include:

```text
python -m pytest
git diff --name-only HEAD -- src
git diff --check
git status --short
```

Manual documentation checks should confirm that edited markdown files have no
trailing whitespace, exactly one final newline, no truncation, and intact final
sections.
