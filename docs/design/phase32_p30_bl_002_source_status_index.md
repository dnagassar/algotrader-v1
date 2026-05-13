# Phase 32 Step 10 - P30-BL-002 Source Status Index

## Purpose

This document is a navigation and status index only. It consolidates the
current status of normalized `P30-BL-002` sources `S01` through `S23` from the
existing repository docs.

This document does not perform new source review, validation, disposition
changes, promotion, threshold approval, signal-definition binding,
implementation approval, or trading-readiness review. Scout-only claims remain
scout-only. Formal-review outcomes remain limited to the exact roles already
recorded in their review documents.

## Source-of-truth documents

This index summarizes only the existing docs:

- [`phase32_p30_bl_002_source_package.md`](phase32_p30_bl_002_source_package.md)
- [`phase32_p30_bl_002_primary_source_verification_gate.md`](phase32_p30_bl_002_primary_source_verification_gate.md)
- [`phase32_p30_bl_002_limited_formal_review_intake_plan.md`](phase32_p30_bl_002_limited_formal_review_intake_plan.md)
- [`phase32_p30_bl_002_s01_formal_review.md`](phase32_p30_bl_002_s01_formal_review.md)
- [`phase32_p30_bl_002_s03_formal_review.md`](phase32_p30_bl_002_s03_formal_review.md)
- [`phase32_p30_bl_002_s08_formal_review.md`](phase32_p30_bl_002_s08_formal_review.md)
- [`phase32_p30_bl_002_s05_formal_review.md`](phase32_p30_bl_002_s05_formal_review.md)

Related planning boundaries:

- [`phase32_s05_deterministic_reproduction_planning_boundary.md`](phase32_s05_deterministic_reproduction_planning_boundary.md)
- [`phase32_s05_data_availability_assessment_boundary.md`](phase32_s05_data_availability_assessment_boundary.md)
- [`phase32_s05_data_provider_source_comparison_plan.md`](phase32_s05_data_provider_source_comparison_plan.md)

## Source-status table

| Source ID | Short label / topic | Current status | Eligible use | Formal review doc | Disposition | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| `P30-BL-002-S01` | Zakamulin moving-average timing / lookahead negative control | Formal review complete | Limited negative-control / no-lookahead guardrail use only | [`phase32_p30_bl_002_s01_formal_review.md`](phase32_p30_bl_002_s01_formal_review.md) | Pass for negative-control/no-lookahead use only | Collect more S01 evidence only before exact timing-rule reproduction, deterministic test binding, threshold comparison, or any stronger claim. |
| `P30-BL-002-S02` | Brock/Lakonishok/LeBaron technical rules | Unreviewed scout-normalized Category B candidate | Scout-only rule-specification context | None | No formal disposition; no validation | Primary-source verification required before any formal review or stronger use. |
| `P30-BL-002-S03` | Sullivan/Timmermann/White data-snooping / OOS negative control | Formal review complete | Limited data-snooping, multiple-testing, and OOS guardrail use only | [`phase32_p30_bl_002_s03_formal_review.md`](phase32_p30_bl_002_s03_formal_review.md) | Pass for negative-control/data-snooping/OOS guardrail use only | Collect more S03 evidence before exact rule reproduction, bootstrap binding, exact OOS result claims, deterministic test binding, or threshold comparison. |
| `P30-BL-002-S04` | Aronson evidence-based technical analysis | Unreviewed scout-normalized Category C candidate | Scout-only falsification / multiple-testing context | None | No formal disposition; not direct threshold evidence | Verify exact rule set, data, code availability, and methodology details if routed later. |
| `P30-BL-002-S05` | Moskowitz/Ooi/Pedersen time-series momentum | Formal review complete | Limited candidate-evidence planning only | [`phase32_p30_bl_002_s05_formal_review.md`](phase32_p30_bl_002_s05_formal_review.md) | Conditional pass for limited candidate-evidence planning only | Step 11 defines a docs-only deterministic reproduction planning boundary; Step 12 defines the data availability assessment boundary; Step 13 defines a source-category comparison plan. Next action is dataset schema/design if exact/partial candidates are plausible, proxy-worth decision if only proxy candidates are plausible, source/vendor verification if unresolved, or downgrade to methodology/candidate-context only if infeasible. |
| `P30-BL-002-S06` | Double-OOS crypto walk-forward optimization | Unreviewed scout-normalized Category D candidate; preprint/code/data unverified | Scout-only validation-architecture lead | None | No formal disposition; not validation evidence | Verify arXiv version, code license, data access, deterministic rerun, costs, and offline safety if pursued. |
| `P30-BL-002-S07` | Interpretable hypothesis-driven trading | Unreviewed scout-normalized Category E candidate; too complex/preprint-based for current route | Scout-only baseline / OOS design context at most | None | No current formal-review route; no evidence use | No current action unless a later research scope explicitly verifies and re-routes it. |
| `P30-BL-002-S08` | FactSet PIT consensus-estimates methodology | Formal review complete | Methodology-only PIT review material only | [`phase32_p30_bl_002_s08_formal_review.md`](phase32_p30_bl_002_s08_formal_review.md) | Pass for methodology-only PIT review material only | Collect more S08 or replacement PIT evidence before exact data-contract binding, vendor query semantics, deterministic local replay, or stronger use. |
| `P30-BL-002-S09` | Small-cap retail strategy PIT/delisting checklist | Unreviewed scout-normalized Category D candidate; weak provenance and no public code/data | Scout-only PIT/delisting checklist lead | None | No formal disposition | Verify provenance, data, code, and PIT/delisting assumptions if this route is needed. |
| `P30-BL-002-S10` | Harvey and Liu, backtesting | Unreviewed scout-normalized Category B methodology candidate | Scout-only multiple-testing methodology context | None | No formal disposition; not dataset-specific threshold evidence | Primary-source verification required before any methodology review use. |
| `P30-BL-002-S11` | Probability of Backtest Overfitting | Unreviewed scout-normalized Category B methodology candidate | Scout-only PBO/CSCV methodology context | None | No formal disposition; not dataset-specific threshold evidence | Primary-source verification required before any methodology review use. |
| `P30-BL-002-S12` | Backtest overfitting in the ML era | Unreviewed scout-normalized Category B methodology candidate; synthetic-data focus | Scout-only CV-method comparison context | None | No formal disposition; not dataset-specific threshold evidence | Verify source and scope only if later methodology context is needed. |
| `P30-BL-002-S13` | Triple-barrier meta-labeling notebook | Unreviewed scout-normalized Category E candidate; tick/ML/license/data gaps | Scout-only volatility-threshold concept context at most | None | No current formal-review route; no evidence use | No action unless a future ML/tick-data scope is explicitly approved and primary-source verified. |
| `P30-BL-002-S14` | GT-Score | Unreviewed scout-normalized Category E candidate; arXiv/yFinance/survivorship/PIT gaps | Scout-only indicator-threshold lead | None | No formal disposition; no validated evidence | Primary-source verification plus PIT and survivorship checks required before any review. |
| `P30-BL-002-S15` | Volume-price-adjusted MACD | Unreviewed scout-normalized Category E candidate; arXiv and fixed-block validation weakness | Scout-only indicator-threshold lead | None | No formal disposition; no validated evidence | Primary-source verification required if routed later. |
| `P30-BL-002-S16` | Generic SSRN backtesting paper | Scout-only Category F material with unclear author/date/provenance; quarantined from current evidence use | No eligible evidence use | None | Preliminary reject/replacement-needed triage only; no formal disposition | Replace or verify identity before any consideration. |
| `P30-BL-002-S17` | BacktestBase minimum-trades heuristic | Scout-only Category F blog/checklist material; quarantined from current evidence use | No eligible evidence use beyond heuristic context | None | Preliminary reject/replacement-needed triage only; no formal disposition | No current action; replace with stronger source if this topic is needed. |
| `P30-BL-002-S18` | Revisiting equity strategies with financial ML / CPCV | Unreviewed scout-normalized Category B methodology candidate; ML-heavy | Scout-only CPCV/purging/embargo context | None | No formal disposition; not simple-threshold evidence | Verify only if a later methodology route needs CPCV/purging context. |
| `P30-BL-002-S19` | Taming the Black Swan / AEGIS | Scout-only Category E portfolio/optimizer material; quarantined from current threshold route | No eligible P30-BL-002 threshold-evidence use | None | No current formal-review route; no evidence use | No action unless a future portfolio-scope research route is opened. |
| `P30-BL-002-S20` | Crypto confidence-threshold MLP | Scout-only Category E black-box/crypto material; quarantined from current threshold route | No eligible P30-BL-002 threshold-evidence use | None | No current formal-review route; no evidence use | No action unless a future ML/crypto research route is opened and verified. |
| `P30-BL-002-S21` | Jointly learning time-series and cross-sectional strategies | Scout-only Category E ML-heavy arXiv material; quarantined from current threshold route | Scout-only baseline / OOS design context at most | None | No current formal-review route; no evidence use | Verify only if later baseline/OOS methodology work needs it. |
| `P30-BL-002-S22` | Implementation risk in portfolio backtesting | Scout-only Category E implementation-risk material; quarantined from current threshold route | Scout-only future backtester-determinism context at most | None | No formal disposition; not signal evidence | No action for P30-BL-002 threshold sourcing; possible future implementation-risk review only. |
| `P30-BL-002-S23` | Kalman / Markov-switching adaptive signals | Scout-only Category E regime-threshold lead; too complex and data-dependent | No eligible current simple-threshold use | None | No current formal-review route; no evidence use | No action unless future regime-threshold research is opened and primary-source verified. |

## Current research-track state

`P30-BL-002` has not produced a `ValidatedResearchArtifact`.

No `ValidatedSignalDefinition` exists for `P30-BL-002`.

No implementation is approved.

No source in this index authorizes production code changes, evaluator behavior,
signal computation, signal scoring, ranking, direction, confidence,
actionability, broker behavior, runtime behavior, persistence, ML, or LLM
trading-path behavior.

## Recommended next routing

Candidate evidence remains conditional and incomplete. The narrow S05
conditional pass supports only future structured evaluation planning. Phase 32
Step 11 adds a planning boundary for a possible future local deterministic
reproduction. Phase 32 Step 12 adds a data availability assessment boundary.
Phase 32 Step 13 adds a source-category comparison plan. None of these phases
reproduce, validate, approve, or implement S05.

The next likely route should remain documentation-only and should be one of:

1. Draft dataset schema/design requirements for a future deterministic
   research-only reproduction if exact or partial source candidates are
   plausible.
2. Decide whether proxy reproduction is worth the sourcing and maintenance cost
   if only proxy source candidates are plausible.
3. Perform future source/vendor verification if source categories remain
   unresolved.
4. Downgrade S05 to methodology/candidate-context only if data availability is
   infeasible under current project constraints.

Do not start implementation from this index.

## Remaining blockers

Evaluator implementation remains blocked by all of the following:

- no exact `ValidatedResearchArtifact`
- no exact `ValidatedSignalDefinition`
- no project-local deterministic reproduction
- no selected/approved dataset
- no acquired data
- no production threshold/config provenance
- no applied no-lookahead audit inside the project
- no implementation-scope approval
- no evaluator tests

## Non-claims

This index does not validate any strategy, threshold, signal, profitability
claim, robustness claim, OOS claim, implementation path, paper-trading path,
live-trading path, or production-readiness claim.

This index does not change the dispositions for `P30-BL-002-S01`,
`P30-BL-002-S03`, `P30-BL-002-S05`, or `P30-BL-002-S08`.
