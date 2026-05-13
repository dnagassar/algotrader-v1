# Phase 32 Step 19 - S05 Proxy Route Selection Boundary

## Purpose

This document compares possible `P30-BL-002-S05` proxy routes for planning
only.

It does not select or approve a dataset. It does not acquire data, design
schemas, reproduce results, validate S05, authorize implementation, or create
any production or trading-path behavior.

This phase is documentation-only. It adds no schema, notebook, script, code,
test, backtest, evaluator, signal computation, signal scoring, production
threshold, `ValidatedResearchArtifact`, or `ValidatedSignalDefinition`.

## Candidate Proxy Routes

The route labels below are planning labels only. None is a selected provider,
selected dataset, approved source, approved universe, approved schema, or
approved reproduction path.

| Route | Planning use | Main limitation |
| --- | --- | --- |
| Modern futures subset route | Rehearse futures-style methodology mechanics on a later, smaller, potentially more obtainable futures universe. | May still require licensed data, may not cover the S05 period or universe, and can be overclaimed as closer to S05 than it is. |
| Reduced-universe futures route | Rehearse futures mechanics with explicit universe exclusions and gap labels. | Similarity depends on unavailable coverage details, and exclusions can change the research question. |
| ETF/index proxy route | Rehearse workflow, no-lookahead discipline, and deterministic snapshot handling with easier-to-understand proxy instruments. | Low S05 similarity; ETF/index behavior is not futures/forwards time-series momentum evidence. |
| AQR factor-level calibration/context route | Use public factor-level or published context as calibration and methodological framing only. | Factor-level context is not raw instrument-level S05 reproduction and cannot validate project-local signal behavior. |
| Manually reconstructed published-table check route | Check public-table arithmetic, labels, and comparison framing without raw data. | It cannot test raw data handling, universe construction, roll logic, or signal implementation. |
| Pause/defer S05 and evaluate another easier-data candidate | Preserve S05 as backlog while pursuing a candidate with clearer data, licensing, and offline reproducibility. | Provides no S05 proxy mechanics, but may be safer for the broader research track. |

## Comparison Criteria

The routes are compared against these criteria:

- data availability
- offline reproducibility
- licensing uncertainty
- S05 similarity
- methodological usefulness
- no-lookahead/as-of discipline usefulness
- cost/complexity
- risk of overclaiming
- fit with normal `python -m pytest` staying offline and credential-free
- usefulness before any code implementation

## Route Comparison

For this phase, a favorable score means safer for docs-only planning. It does
not mean better for trading, validation, or implementation.

| Route | Data / offline fit | S05 similarity | Method / as-of usefulness | Cost / licensing | Overclaiming risk | Pre-code usefulness |
| --- | --- | --- | --- | --- | --- | --- |
| Modern futures subset | Unclear until a source and rights are verified; no source is selected here. | Medium, but only if futures coverage and semantics are later proven. | High for roll, contract, timestamp, and provenance questions. | Medium to high. | High if treated as S05 reproduction. | Useful for requirement writing only. |
| Reduced-universe futures | Unclear for the same reasons as the modern subset route. | Low to medium because excluded instruments can alter conclusions. | High for recording exclusions, missing data, and non-claims. | Medium to high. | High unless every exclusion is explicit. | Useful for limitation templates only. |
| ETF/index proxy | Easier in principle, but no data is selected or approved here. | Low. | Medium for `as_of`, snapshot, and workflow discipline. | Low to medium, depending on source rights. | High if treated as futures evidence. | Useful for workflow framing only. |
| AQR factor-level context | Potentially easier as context, subject to published terms and local archival limits. | Low for raw S05 reproduction; medium as broad context. | Medium for calibration labels and comparison discipline. | Low to medium. | Medium unless clearly factor-level only. | Useful for context-use rules only. |
| Published-table check | Strong offline fit if manually captured from approved public text, but no table is captured here. | Very low for raw reproduction. | Low to medium for arithmetic labels and claim discipline. | Low. | Low to medium if kept as table checking only. | Useful for review-template wording only. |
| Pause/defer S05 | Best fit for avoiding data, licensing, and offline ambiguity. | None. | Medium for governance discipline. | Lowest. | Lowest. | Useful if S05 evidence remains insufficient. |

## Route Decision

Conservative decision: keep multiple proxy routes under consideration, but do
not select a single route for data, schema, reproduction, validation, or
implementation planning.

The modern futures subset and reduced-universe futures routes are the most
methodologically relevant proxy candidates, but their data availability,
licensing, offline snapshot, and period/universe gaps remain too unresolved for
route selection beyond docs-only requirements planning.

The ETF/index route is easier to reason about but has low S05 similarity and a
high risk of false equivalence. It remains a workflow-rehearsal candidate only.

The AQR factor-level and manually reconstructed published-table routes are the
lowest-risk context routes, but they cannot test raw instrument-level
reproduction. They remain calibration/context and table-check candidates only.

S05 therefore remains in proxy/partial planning and backlog status. The
preferred planning posture is route-neutral: define the minimum requirements a
future proxy route would have to satisfy before any route can be narrowed.

## Required Decision Constraints

- Route selection is not dataset approval.
- Route selection is not source or provider approval.
- Route selection is not subscription approval.
- Route selection is not validation.
- Route selection is not reproduction approval.
- Route selection is not implementation approval.
- Route selection does not create a `ValidatedResearchArtifact`.
- Route selection does not create a `ValidatedSignalDefinition`.
- Route selection does not authorize a new contract type.
- Route selection does not imply proxy results can validate S05.

## Recommended Next Gate

Recommended next docs-only gate: proxy dataset requirement boundary.

That gate should stay route-neutral and should define minimum requirements that
any future proxy route would need before it can be narrowed further. At minimum,
it should cover universe labeling, date-range labeling, provenance, licensing
evidence, local offline snapshot expectations, `as_of` and no-lookahead
discipline, missing-data assumptions, correction/version handling, fixture or
data-storage policy constraints, comparison-target limits, and mandatory
non-claims.

If a route-neutral requirement boundary cannot be written without drifting into
dataset approval, data acquisition, schema design, or reproduction planning,
S05 should stay in backlog and the research track should evaluate another
candidate with easier data availability.

## Explicit Non-Goals

This phase does not perform or authorize:

- exact replication
- dataset selection
- data acquisition
- ingestion
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
- no selected proxy route for data planning
- no approved proxy data-storage policy
- no approved proxy reproduction protocol
- no deterministic offline snapshot path for any candidate source
- no resolved exact S05 universe, 1965-2009 instrument coverage, raw contract,
  roll, PIT/as-of, correction-history, or versioning basis
