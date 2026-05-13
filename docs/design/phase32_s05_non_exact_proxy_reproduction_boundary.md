# Phase 32 Step 18 - S05 Non-Exact Proxy Reproduction Boundary

## Purpose

This document defines a possible future non-exact proxy reproduction boundary
for `P30-BL-002-S05`.

It does not select data, acquire data, ingest data, reproduce results, validate
S05, approve a provider, approve a dataset, design schema, authorize
implementation, or create any production or trading-path behavior.

This phase is documentation-only. It adds no schema, notebook, script, code,
test, backtest, evaluator, signal computation, signal scoring, production
threshold, `ValidatedResearchArtifact`, or `ValidatedSignalDefinition`.

## Definition

A non-exact proxy reproduction is a controlled approximation intended to test
methodology mechanics and research workflow discipline. It is not an attempt to
recreate S05 exactly, and it cannot establish that the original S05 evidence,
edge, universe, data, or results have been reproduced.

The current boundary distinguishes four different uses:

| Route | Meaning | Current status |
| --- | --- | --- |
| Exact S05 reproduction | Rebuild the S05 candidate claim against the original-style futures/forwards universe, period, data semantics, timing, and comparison targets closely enough to evaluate exact project-local reproduction. | Paused. No source, dataset, schema, or implementation is approved. |
| Partial reproduction | Reproduce only a documented subset of the S05 universe, period, method, or comparison target while recording unresolved gaps. | Planning-only candidate route. It cannot validate S05 or approve implementation. |
| Proxy reproduction | Use substitute data, a reduced universe, factor-level context, or manually reconstructed public tables to rehearse mechanics and governance. | Planning-only candidate route. It can test workflow discipline but cannot prove S05 results. |
| Methodology-only/context use | Use S05, AQR material, PIT/no-lookahead controls, or public tables as conceptual context without calculation claims. | Allowed only as documentation context and guardrail framing. |

No proxy route may be described as S05 replication, and no proxy result may be
treated as validation of S05.

## Allowed Proxy Routes For Planning Only

The following routes may be considered only in future documentation planning:

- modern futures subset using a public-doc-supported vendor category, with no
  vendor or dataset selected
- reduced-universe futures proxy with explicit exclusions and non-claims
- ETF/index proxy universe for methodology rehearsal only
- AQR factor-level calibration or context check, not raw instrument-level S05
  reproduction
- manually reconstructed published-table checks for public-table arithmetic or
  qualitative comparison only

These routes are not approved data sources. They do not authorize subscription,
purchase, download, ingestion, schema design, reproduction implementation,
validation, promotion, or trading use.

## What Proxy Reproduction Could Support

A future proxy plan, if separately approved as documentation and later as
research-only work, could support:

- deterministic research workflow testing
- no-lookahead and `as_of` discipline testing
- data handling and provenance discipline
- rough methodology sanity checks
- comparison of broad behavior against published context
- future decision-making about whether deeper data investment is worthwhile

These uses would remain research-process evidence only. They would not be
validated signal evidence.

## What Proxy Reproduction Cannot Support

Proxy reproduction cannot support:

- exact S05 replication
- `ValidatedResearchArtifact`
- `ValidatedSignalDefinition`
- production threshold or config approval
- live or paper trading readiness
- profitability claim
- generalization claim
- implementation approval
- claim that S05's original edge has been reproduced
- provider, dataset, license, or subscription approval
- broker, runtime, OMS, portfolio, ledger, reconciliation, ML, or LLM
  trading-path behavior

Any future proxy result must carry these non-claims before it is reviewed.

## Proxy Evidence Standards

Any future proxy plan must define all of the following before calculation,
validation discussion, or implementation discussion:

- explicit universe definition
- explicit date range
- explicit data source and provenance
- offline snapshot and versioning plan
- no-lookahead and `as_of` assumptions
- survivorship and missing-data assumptions
- cost and slippage assumptions if relevant
- clear comparison target
- limitations and non-claims
- deterministic reproducibility requirement
- normal `python -m pytest` remains offline and credential-free

The plan must also state whether the route is a partial reproduction, proxy
reproduction, or methodology-only/context use. Ambiguous routes should default
to the weaker label.

## Future Phase Gates

Before any code, schema, data, or result review, future docs-only gates should
include:

1. Proxy route selection boundary.
2. Proxy dataset schema/design boundary.
3. Proxy fixture/data-storage policy boundary.
4. Proxy reproduction protocol boundary.
5. Proxy result-review template.
6. Promotion/rejection decision boundary.

Each gate must preserve the distinction between proxy workflow rehearsal and
validated S05 evidence.

## Recommended Next Routing

The safest current route is to keep S05 in proxy/partial planning only and not
implement it.

The next phase may be either:

- a docs-only proxy route selection boundary that compares planning routes
  without choosing a provider, dataset, subscription, schema, or
  implementation; or
- evaluation of another candidate with easier data availability.

Do not implement from this boundary.

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
- no approved proxy route
- no approved proxy data-storage policy
- no approved proxy reproduction protocol
- no deterministic offline snapshot path for any candidate source
- no resolved exact S05 universe, 1965-2009 instrument coverage, raw contract,
  roll, PIT/as-of, correction-history, or versioning basis

## Verification

Verification after Phase 32 Step 18:

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
?? docs/design/phase32_s05_non_exact_proxy_reproduction_boundary.md
```

Manual documentation checks confirmed that edited markdown files have no
trailing whitespace, exactly one final newline, no truncation, and intact final
sections.
