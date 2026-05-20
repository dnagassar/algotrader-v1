# Phase 83 - Broad ETF Data Source Policy / Local Snapshot Readiness Boundary

## Purpose

This document defines the readiness boundary for any future broad ETF data
source path or local snapshot.

It is documentation-only. It may define policy gates and review criteria, but
it must not approve, select, acquire, ingest, transform, validate, or use any
real data.

## Decision Boundary

Phase 83 may define readiness criteria only.

It does not approve:

- any data source
- any ETF universe
- any benchmark
- any cash proxy
- any methodology
- any parameter set
- any evidence
- any strategy validation
- any trading use

No source path is selected as approved. No local snapshot is approved. No
snapshot format is implemented. No manifest contract is added. No real market
data, real ETF ticker, benchmark series, cash series, provider export, broker
export, downloaded file, API response, or local data file is added.

## Candidate Source-Path Categories

The following categories are policy-level categories only. They may support a
later candidate-only review, but none is approved here.

| Category | Policy-level description | Phase 83 status |
| --- | --- | --- |
| Manual local snapshot | A human places a local file outside normal repository fixtures after a documented acquisition step. | Candidate category only; not approved. |
| Vendor-exported local snapshot | A file exported from a paid or free data vendor interface and stored locally under a later storage rule. | Candidate category only; not approved. |
| Broker-exported local snapshot | A historical data export from a broker account, feed, or platform. | Candidate category only; not approved. |
| Public web/downloaded file | A manually downloaded public file or web export. | Candidate category only; not approved. |
| API-based source | A scripted or manual API retrieval path. | Candidate category only; not approved; normal pytest must remain offline. |
| Synthetic fixture | Project-authored artificial data with no real market-data content. | Allowed only under existing synthetic-fixture rules; not evidence. |
| Derived tiny approved fixture | A future tiny derived fixture, if a later policy explicitly approves derivation, storage, license, and normal-pytest eligibility. | Candidate category only; not approved. |

No category wins by default. A future phase may choose the smallest
candidate-only path to prepare, but that later choice would still be
non-approval unless an explicit approval boundary says otherwise.

## Local Snapshot Readiness Requirements

Any future local broad ETF snapshot must have a documented manifest or
equivalent metadata record before it can be consumed by research code. At
minimum, the record must include:

- source name
- source type
- acquisition date
- as-of date or observation date range
- symbol identity policy
- field schema
- adjustment policy
- return basis
- checksum
- storage location rule
- redistribution status
- license/terms note
- provenance note
- limitations/non-claims
- normal-pytest eligibility status

The readiness record must also state whether the snapshot is raw,
vendor-exported, broker-exported, public-web/downloaded, API-derived,
synthetic, or derived. It must identify whether the file is third-party data,
project-authored synthetic data, or a later approved tiny derived fixture.

Raw third-party market data must stay out of the repository unless a later
storage and fixture policy explicitly approves a narrow exception. Local
snapshots belong outside normal repository fixtures by default, and `.data/`
remains local-only.

Normal `python -m pytest` must not depend on local snapshots. A local snapshot
must not be silently treated as validated data, approved evidence, approved
universe membership, approved benchmark input, approved cash proxy input, or
trading-ready material.

## Adjustment And Return-Basis Questions

Any future source-path review must resolve adjustment and return-basis
questions before implementation consumes local broad ETF data.

Unresolved choices include:

- raw close: whether raw close is usable for a price-return-only path, and how
  splits and corporate actions are handled
- adjusted close: whether the adjustment methodology is documented enough to
  use, and whether later revisions create point-in-time risk
- total return: whether a total-return series is source-provided or
  constructed, and whether its methodology and timing are documented
- unknown adjustment: whether unknown adjustment semantics force a
  research-only limitation or block use entirely
- split, dividend, distribution, and corporate-action ambiguity: whether the
  source exposes enough information to distinguish price moves from
  adjustments and distributions
- vendor revision risk: whether historical values can change after initial
  acquisition and how checksums, retrieval dates, and limitations capture that
  risk
- price-return-only fallback: whether a future phase allows a price-return-only
  fallback and what non-claims must accompany it
- explicit total-return construction: unresolved unless separately approved
  with distribution fields, availability timing, reinvestment assumptions,
  compounding rules, and no-lookahead treatment

Phase 83 does not solve return construction. It records that a future
implementation gate must decide the return basis and adjustment policy before
any local broad ETF data is consumed.

## No-Lookahead And As-Of Implications

Any future source path or local snapshot must preserve no-lookahead discipline.
At minimum, later policy must distinguish:

- source acquisition timestamp
- observation date or observation date range
- decision timestamp
- action timestamp
- adjusted-data revision risk
- stale or missing data
- holiday and calendar alignment
- publication and revision timing if rates, cash proxies, benchmark inputs, or
  other macro-like series are used later

Observation dates are not automatically availability dates. Acquisition dates
are not automatically decision dates. Adjusted historical data may include
later split, dividend, distribution, or correction information, so it cannot be
assumed point-in-time safe without source-specific review.

Future policy must also decide how to handle stale observations, missing
sessions, non-trading days, calendar mismatches, revised fields, and any
publication lag before a research protocol computes results.

## Repository And Storage Policy

The default storage policy remains conservative:

- no raw vendor, broker, or public market data in the repository by default
- `.data/` is local-only and is not an input to normal pytest
- normal pytest must remain offline, credential-free, provider-free, and
  independent of local snapshots
- tiny synthetic fixtures are allowed in normal pytest when they contain no
  real market-data content and carry explicit non-claims
- tiny derived fixtures require a future approval policy before they can enter
  the repository or normal pytest
- checksums and manifests should describe local data without embedding raw
  third-party market data
- manifests should be safe to commit only if they do not disclose restricted
  raw data, account data, credentials, proprietary export contents, or
  redistribution-prohibited material

Local snapshot metadata may document source identity, dates, schema, checksum,
terms notes, limitations, and storage location rules, but it must not smuggle
raw third-party rows into committed docs, fixtures, tests, reports, or code.

## Minimum Future Implementation Gates

Before any future implementation consumes local broad ETF data, the project
must have a later decision-readiness or approval boundary that resolves at
least:

- source candidate selected as candidate-only
- storage rule documented
- snapshot manifest contract or manifest-reuse decision
- adjustment and return-basis policy decided
- no-lookahead and as-of policy decided
- universe membership and inception/survivorship policy decided
- benchmark and cash handling decided
- test path remains synthetic and offline by default

These gates are prerequisites for implementation planning only. Satisfying a
gate does not by itself approve source use, data use, evidence, strategy
validation, or trading use.

## Explicit Non-Claims

Phase 83 is:

- not source approval
- not data approval
- not universe approval
- not benchmark approval
- not cash proxy approval
- not methodology approval
- not parameter approval
- not evidence approval
- not strategy validation
- not trading readiness

It also adds no real data ingestion, no real market data, no real ETF tickers,
no benchmark comparison, no ranking, no scoring, no recommendation, no
candidate discovery, no replay metrics, no report rendering, no signal or
evaluator behavior, no advisory integration, no governance behavior, no broker,
order, fill, portfolio, runtime, paper, live, or trading behavior, and no LLM,
network, API, provider, or market-data call.

## Decision

Decision: readiness boundary only.

The project is not ready to consume local broad ETF data. The next narrow step,
if pursued, should be a decision-readiness checkpoint that chooses the smallest
candidate-only source path to prepare for later, probably a local snapshot
manifest/provenance contract. That future step should still avoid data
ingestion, source approval, data approval, universe approval, benchmark
approval, cash proxy approval, methodology approval, parameter approval,
evidence approval, strategy validation, and trading behavior.

## Remaining Blockers

- no approved source
- no approved data
- no approved local snapshot
- no approved manifest contract
- no approved storage rule for raw third-party market data
- no approved ETF universe
- no approved benchmark
- no approved cash proxy
- no approved methodology
- no approved parameter set
- no approved evidence
- no approved adjustment policy
- no approved return basis
- no approved total-return construction
- no approved no-lookahead/as-of policy
- no approved inception/survivorship policy
- no approved redistribution policy
- no implementation-readiness claim
- no strategy-validation claim
- no trading-readiness claim
