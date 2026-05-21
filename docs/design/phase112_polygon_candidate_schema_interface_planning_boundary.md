# Phase 112 - Polygon Candidate Schema / Interface Planning Boundary

## Purpose

This document defines a narrow docs-only, candidate-only schema/interface
planning boundary for possible future Polygon/Massive data normalization.

Phase 112 identifies which documented Polygon/Massive surfaces might later
need schema contracts. It does not implement schemas, define production
dataclasses, call APIs, download data, create fixtures, add dependencies,
change tests, change production behavior, start a local snapshot workflow, or
approve Polygon/Massive.

## Boundary

Phase 112 may define candidate schema/interface planning only.

It must not approve:

- Polygon
- Massive
- any endpoint
- any flat file
- any source
- any data
- any ETF universe
- any benchmark
- any cash proxy
- any methodology
- any parameter
- any evidence
- any return-construction policy
- any no-lookahead policy
- any cost/friction model
- any strategy validation
- any trading use

Any surface, field category, metadata question, implementation gate, or future
fixture idea in this document is planning material only. It does not authorize
source use, endpoint use, flat-file use, data use, local storage, repo storage,
API calls, downloads, ingestion, fixtures, return construction, universe
construction, benchmark construction, cash proxy construction, no-lookahead
claims, validation, or trading behavior.

## Candidate Interface Surfaces

The following Polygon/Massive surfaces are candidates for later schema
planning only. Each row is candidate only, not approved, not implemented,
involves no API calls, has no data downloaded, and creates no normal-pytest
dependency.

| candidate_surface | candidate_status | planning_use_only | non_claims |
| --- | --- | --- | --- |
| Aggregates / bars | Candidate only; not approved; not implemented. | Later planning may need bar-like field categories, adjustment-state notes, timestamp categories, and identifier categories. | No endpoint approval; no data approval; no return-construction approval; no API calls; no downloads; no normal-pytest dependency. |
| Grouped daily aggregates | Candidate only; not approved; not implemented. | Later planning may need market-wide daily bar shape questions and universe-membership caveats. | No universe approval; no endpoint approval; no survivorship approval; no API calls; no downloads; no normal-pytest dependency. |
| Trades | Candidate only; not approved; not implemented. | Later planning may record that trade-level fields are outside the current ETF price-source need unless separately scoped. | No trade-data approval; no liquidity approval; no cost/friction approval; no API calls; no downloads; no normal-pytest dependency. |
| Quotes | Candidate only; not approved; not implemented. | Later planning may record quote field categories only if a future cost/friction or liquidity phase separately needs them. | No quote-data approval; no liquidity approval; no spread/slippage approval; no API calls; no downloads; no normal-pytest dependency. |
| Reference tickers | Candidate only; not approved; not implemented. | Later planning may need identifier, asset-class, active/inactive, and listing metadata categories. | No ETF universe approval; no survivorship approval; no ticker selection; no API calls; no downloads; no normal-pytest dependency. |
| Ticker details | Candidate only; not approved; not implemented. | Later planning may need issuer, name, exchange, type, listing, active state, and detail timestamp categories. | No reference-data approval; no lifecycle approval; no ETF completeness claim; no API calls; no downloads; no normal-pytest dependency. |
| Ticker events | Candidate only; not approved; not implemented. | Later planning may need event-type, effective-date, old/new identifier, and lifecycle event categories. | No ticker-event completeness approval; no symbol-continuity approval; no universe approval; no API calls; no downloads; no normal-pytest dependency. |
| Splits | Candidate only; not approved; not implemented. | Later planning may need split-ratio, execution/effective date, ticker, correction, and adjustment-link categories. | No split-methodology approval; no adjusted-data approval; no point-in-time proof; no API calls; no downloads; no normal-pytest dependency. |
| Dividends | Candidate only; not approved; not implemented. | Later planning may need dividend amount, date, ticker, currency, type/category, and correction categories. | No dividend-adjusted approval; no total-return approval; no ETF distribution approval; no API calls; no downloads; no normal-pytest dependency. |
| Flat files | Candidate only; not approved; not implemented. | Later planning may need file family, schema version, compression, partition/date, checksum, and manifest categories. | No flat-file approval; no download approval; no local snapshot approval; no data files; no normal-pytest dependency. |
| ETF Global / ETF profile surfaces | Candidate only; not approved; not implemented. | Later planning may include ETF-profile field categories only if official docs and intended use make them relevant. | No ETF profile approval; no source approval; no universe approval; no API calls; no downloads; no normal-pytest dependency. |
| Market calendar/session data | Candidate only; not approved; not implemented. | Later planning may include calendar/session categories only if official docs support a relevant surface. | No calendar approval; no session/timestamp approval; no no-lookahead approval; no API calls; no downloads; no normal-pytest dependency. |

## Candidate Metadata Needs Per Surface

No production dataclasses are defined in Phase 112. Future planning for any
surface should record metadata questions, not implementation schemas.

| candidate_surface | likely_metadata_questions |
| --- | --- |
| Aggregates / bars | Endpoint/source name; source category; official documentation status; expected OHLCV-like field categories, not exact schema; timestamp fields; identifier fields; adjustment-state fields; pagination and rate-limit considerations; entitlement/plan considerations; unresolved adjustment, timestamp, stale-bar, correction, and return-basis issues; non-claims. |
| Grouped daily aggregates | Endpoint/source name; source category; official documentation status; expected market-wide daily bar categories; timestamp fields; identifier fields; universe-membership implications; adjustment/corporate-action fields if documented; pagination/rate-limit considerations; entitlement/plan considerations; unresolved active/inactive, completeness, revision, and survivorship issues; non-claims. |
| Trades | Endpoint/source name; source category; official documentation status; expected trade price, size, venue, condition, timestamp, and identifier categories only if later relevant; pagination/rate-limit considerations; entitlement/plan considerations; unresolved need, rights, volume-quality, and cost/liquidity relevance issues; non-claims. |
| Quotes | Endpoint/source name; source category; official documentation status; expected bid/ask, size, venue, condition, timestamp, and identifier categories only if later relevant; pagination/rate-limit considerations; entitlement/plan considerations; unresolved need, rights, spread/liquidity relevance, and session issues; non-claims. |
| Reference tickers | Endpoint/source name; source category; official documentation status; expected identifier, market, locale, asset type, active state, exchange, name, and date categories; lifecycle/reference fields; pagination/rate-limit considerations; entitlement/plan considerations; unresolved ETF classification, delisted retention, as-of behavior, and universe completeness issues; non-claims. |
| Ticker details | Endpoint/source name; source category; official documentation status; expected issuer/name, exchange, primary identifier, type/category, listing, active/inactive, detail timestamp, and metadata categories; lifecycle/reference fields; entitlement/plan considerations; unresolved historical details, ETF coverage, old-symbol continuity, and point-in-time detail issues; non-claims. |
| Ticker events | Endpoint/source name; source category; official documentation status; expected event category, effective date, old/new ticker or identifier, corporate/fund event, and timestamp categories; lifecycle/reference fields; pagination/rate-limit considerations; entitlement/plan considerations; unresolved event taxonomy, completeness, corrections, and ETF lifecycle mapping issues; non-claims. |
| Splits | Endpoint/source name; source category; official documentation status; expected split ratio, execution/effective date, ticker/identifier, declaration or record dates if documented, and correction categories; adjustment/corporate-action fields; pagination/rate-limit considerations; entitlement/plan considerations; unresolved split formula, timing, corrections, and point-in-time availability issues; non-claims. |
| Dividends | Endpoint/source name; source category; official documentation status; expected cash amount, currency, ex-date, record date, pay date, declaration date, ticker/identifier, and type/category fields if documented; adjustment/corporate-action fields; pagination/rate-limit considerations; entitlement/plan considerations; unresolved ETF distribution taxonomy, corrections, total-return, and point-in-time availability issues; non-claims. |
| Flat files | Source/file family name; source category; official documentation status; expected file-family, partition/date, compression, delimiter, schema version, checksum, timestamp, identifier, and adjustment-state categories, not exact file schemas; entitlement/plan considerations; unresolved storage, retention, redistribution, revision, and local snapshot issues; non-claims. |
| ETF Global / ETF profile surfaces | Endpoint/source name; source category; official documentation status; expected ETF identity, profile, issuer, fund classification, expense, holdings or distribution-profile categories only if officially documented and relevant; lifecycle/reference fields; entitlement/plan considerations; unresolved relationship to core price data, licensing, and point-in-time profile history issues; non-claims. |
| Market calendar/session data | Endpoint/source name; source category; official documentation status if later found; expected session date, open/close, holiday, half-day, timezone, and market identifier categories only if officially documented; entitlement/plan considerations; unresolved official calendar authority, session inclusion, timestamp alignment, and no-lookahead issues; non-claims. |

## Cross-Surface Unresolved Risks

The same unresolved risks apply across candidate surfaces:

- legal, storage, archival, private/public repo, and redistribution rights
- derived-data, manifest, checksum, report, signal, and publication
  restrictions
- endpoint and flat-file entitlement by plan or product
- point-in-time, prior-vintage, and as-of snapshot support
- revision, correction, finalization, and last-updated metadata
- ETF lifecycle completeness
- delisted and inactive ETF retention
- ticker-event completeness and symbol-continuity handling
- dividends and ETF distribution taxonomy
- split-only versus broader adjustment behavior
- absence of approved dividend-adjusted or total-return series
- timestamp, timezone, and session rules
- missing and stale bars
- market calendar, half-day, holiday, halt, and non-trading-day behavior

Candidate schema/interface planning does not solve these risks. Any later
surface-specific schema note must preserve the relevant caveats rather than
turn field existence into source, data, return-basis, universe, no-lookahead,
or validation approval.

## Future Implementation Gates

Before any future code, test fixture, schema contract, dataclass, parser,
manifest bridge, or interface work, a later phase must require:

- the source remains candidate-only
- no real API call in normal pytest
- no real data files in the repository
- synthetic fixtures only
- schema fields derived from official docs only
- no source or data approval from schema existence
- no endpoint or flat-file approval from schema existence
- legal, storage, redistribution, point-in-time, revision, lifecycle,
  survivorship, and return-basis caveats preserved
- dependency-direction tests remain clean
- the default pytest network guard remains active
- no vendor SDK, credential, endpoint client, ingestion, persistence,
  evaluator, signal, broker, portfolio, runtime, strategy-validation, or
  trading behavior is introduced

## Future Synthetic-Only Schema Fixture Boundary

A future synthetic-only schema fixture may be allowed only if separately
scoped.

Allowed later, only under a separate explicit phase:

- create primitive synthetic examples matching documented field categories
- validate a local dataclass or manifest shape if that contract is separately
  approved later
- test serialization determinism
- test absence of forbidden fields
- test absence of network, credential, vendor SDK, and market-data imports
- preserve source, data, endpoint, flat-file, universe, return-basis,
  no-lookahead, validation, and trading non-claims

Forbidden unless separately approved:

- real API response samples
- downloaded JSON or CSV
- vendor raw rows
- endpoint clients
- authentication
- ingestion
- persistence
- local snapshot workflow
- portfolio behavior
- evaluator behavior
- signal behavior
- broker/runtime behavior
- strategy validation
- trading behavior

## Relationship To Prior Phases

Phase 83 defined broad ETF source-path and local snapshot readiness criteria.
Phase 112 does not approve Polygon/Massive as a source path, local snapshot
route, storage rule, or manifest-to-data workflow.

Phase 93 defined the broad ETF source evidence intake plan. Phase 112 stays
inside that framework by treating documented surfaces as candidate planning
inputs only.

Phase 104 and Phase 105 normalized Alpha Vantage primary-source and public-doc
findings. Phase 112 does not change Alpha Vantage's unresolved, non-approved
status.

Phase 106 normalized Stooq public-doc findings. Phase 112 does not change
Stooq's unresolved, non-approved status.

Phase 108 and Phase 110 normalized Polygon/Massive public-doc findings. Phase
112 uses those findings only to identify possible later schema/interface
planning surfaces.

Phase 109 compared Alpha Vantage, Stooq, and Polygon/Massive. Phase 112
preserves the comparison result that Polygon/Massive is technically strongest
so far but still unresolved and non-approved.

Phase 111 routed the next step toward candidate-only Polygon/Massive
schema/interface normalization planning under metadata-only and synthetic-only
constraints. Phase 112 defines that planning boundary without starting code or
fixture work.

Across these phases:

- schema/interface planning does not approve Polygon/Massive
- endpoint documentation does not approve data use
- flat-file documentation does not approve downloads, storage, or local
  snapshots
- schema fields do not solve legal, point-in-time, vintage, revision,
  survivorship, lifecycle, or return-basis issues
- normal pytest must remain synthetic, offline, credential-free, source-free,
  vendor-free, and independent from real data

## Explicit Non-Claims

Phase 112 is:

- not Polygon approval
- not Massive approval
- not endpoint approval
- not flat-file approval
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

It adds no Polygon approval, Massive approval, endpoint approval, flat-file
approval, source approval, data approval, vendor approval, universe approval,
benchmark approval, cash proxy approval, methodology approval, parameter
approval, evidence approval, return-construction approval, no-lookahead
approval, cost/friction approval, liquidity approval, strategy validation,
production schema, production dataclass, parser, endpoint client, API call,
download, credential, real data, data file, fixture, local snapshot workflow,
ingestion, persistence, ETF ticker selection, benchmark comparison, ranking,
scoring, recommendation, replay metric, manifest-to-planning bridge,
signal/evaluator behavior, broker/order/fill/portfolio/runtime behavior, LLM
call, network call, market-data call, paper behavior, live behavior, or
trading behavior.

## Decision

Decision: Polygon/Massive candidate schema/interface planning boundary only.

Phase 112 identifies possible candidate surfaces and metadata questions for a
future schema/interface planning path, while keeping Polygon/Massive
unresolved and non-approved.

No production code or tests changed. No fixtures changed. No real data was
added. No API calls or downloads occurred. No source, data, endpoint, flat
file, universe, benchmark, cash proxy, methodology, evidence,
return-construction, no-lookahead, cost/friction, liquidity, strategy
validation, or trading approval was added. Normal pytest remains offline and
credential-free.

## Follow-Up Recommendation

Pause before code.

The next decision should be whether to add a tiny synthetic-only schema
fixture for one surface, likely reference tickers or aggregates, or whether
legal and point-in-time blockers make even synthetic schema work premature.
