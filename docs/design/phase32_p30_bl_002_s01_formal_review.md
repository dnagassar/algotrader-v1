# Phase 32 Step 6 — P30-BL-002-S01 Formal Review: Zakamulin MA Timing Negative Control

## Purpose

This document formally reviews `P30-BL-002-S01` only. The review scope is
limited to whether the source can be used as a negative-control /
no-lookahead reference for moving-average timing guardrails.

This review does not validate a trading signal, approve a production
threshold, create a validated artifact, create a validated signal definition,
or imply implementation readiness. Negative-control usefulness is not signal
validation.

## Prior state

- `P30-BL-001` is mechanics-only dispositioned. It is not validated,
  approved, production-ready, threshold-justified, or implementation-ready.
- `P30-BL-002` remains a sourcing handle only.
- Phase 32 Step 3 normalized `P30-BL-002-S01` through `P30-BL-002-S23` from
  supplied scout reports. Those entries remained candidate-only, unreviewed,
  unvalidated, unapproved, and not implementation-ready.
- Phase 32 Step 4 verified selected primary-source identities and found
  `P30-BL-002-S01` eligible only for limited negative-control/no-lookahead
  formal review intake.
- Phase 32 Step 5 scheduled `P30-BL-002-S01` as the first formal review,
  before `P30-BL-002-S03`, `P30-BL-002-S05`, and `P30-BL-002-S08`.

## Source identity

| Field | Review record |
| --- | --- |
| Normalized source id | `P30-BL-002-S01` |
| Title | "Revisiting the Profitability of Market Timing with Moving Averages" |
| Author/source | Valeriy Zakamulin, University of Agder - School of Business and Law; SSRN working-paper record |
| Date/version | Step 4 records the SSRN page as 10 pages posted March 8, 2016, last revised September 15, 2016, with date written August 25, 2016 |
| Primary-source link or citation text | SSRN abstract page at <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2743119>; SSRN DOI `10.2139/ssrn.2743119`; publisher DOI `10.1111/irfi.12132` remains a citation check because the Wiley page was not accessible in Step 4 |
| Source type | Academic working paper / published-article candidate |
| Verified source identity status | Primary SSRN identity and core lookahead claim verified by Step 4; full text, code/data access, exact dataset, and exact timing conventions remain unresolved in repository docs |

## Review scope

This review is limited to:

- moving-average timing convention relevance
- lookahead-bias finding relevance
- corrected signal timing as an unresolved but central review topic
- negative-control usefulness
- no-lookahead guardrail relevance

This review excludes:

- production threshold approval
- strategy validation
- profitability assessment
- signal-definition binding
- implementation approval
- any real evaluator, signal computation, ranking, scoring, direction,
  confidence, probability, or actionability

## Evidence reviewed

This review uses the Phase 32 Step 4 primary-source verification gate and the
Phase 32 Step 5 intake plan as the source of truth for S01 identity and review
scope. It also checks the Step 3 source package only as normalized
candidate-discovery context.

The repository documents support the following:

- Rule type: moving-average market-timing strategy; the Step 3 source package
  describes price-versus-moving-average and moving-average crossover rules.
- Timing-bias issue: the Step 4 gate verifies that the primary SSRN abstract
  frames the contribution as removing lookahead-biased simulation.
- Corrected timing convention: Step 3 records a scout claim that corrected
  signal timing removes a lookahead convention. The exact signal date,
  execution date, and return-measurement date are not fully verified in repo
  docs.
- Dataset/timeframe: Step 4 verifies that the abstract says the paper
  reexamines the same dataset and trading rules as Glabadanidis, "Market
  Timing With Moving Averages" (2015). Exact data source, asset universe,
  sample dates, frequency, and total-return treatment remain unresolved.
- Reproducibility materials: Step 4 records that the SSRN abstract reports R
  code for reproducing reported results. Actual code access, data access,
  license, archival path, and deterministic rerun feasibility remain
  unresolved.
- No-lookahead relevance: Step 4 verifies direct relevance to moving-average
  timing and lookahead simulation risk.
- Limitations: available repo evidence is mostly source identity and
  abstract-level provenance. It is insufficient for threshold approval,
  predictive-edge claims, profitability claims, validated signal definition,
  exact test binding, or implementation readiness.

## Review findings

| Criterion from Step 5 | Finding |
| --- | --- |
| Exact lookahead-bias finding | Verified only at the core abstract level: the source is identified as re-simulating moving-average timing without lookahead bias. The exact simulation convention that caused the lookahead bias is unresolved in repo docs. |
| Corrected timing convention | Relevant but unresolved. Repo docs do not fully verify the exact signal date, execution date, or return-measurement date. Any future exact guardrail or test binding must source those details first. |
| Rule definitions | Partially identified as moving-average market-timing rules, including price-versus-moving-average and crossover descriptions from Step 3 candidate context. Exact windows, comparators, price/return transformations, and missing-data handling are unresolved. |
| Dataset and timeframe | Partially identified as a stock-market / index-timing setting that reexamines the Glabadanidis dataset and rules. Exact vendor/source, universe, sample start/end dates, frequency, total-return handling, and transaction-cost assumptions are unresolved. |
| Reproducibility materials | Reported R code is noted by the SSRN abstract per Step 4, but code retrieval, data retrieval, licensing, archival path, and deterministic rerun feasibility are unresolved. |
| Negative-control suitability | Passes narrowly for negative-control/no-lookahead use only. The source can be cited as reviewed evidence that moving-average timing simulations can be invalidated by lookahead bias and that future guardrail design must explicitly separate observation, signal, execution, and return-measurement timing. |
| Production-threshold unsuitability | Not suitable. The review finds no approved production threshold, no accepted comparator evidence, no validated dataset window, no accepted profitability evidence, no robustness acceptance, and no implementation-ready artifact. |

## Pass/fail outcome

Outcome: pass for negative-control/no-lookahead use only.

The pass is deliberately narrow. `P30-BL-002-S01` may support falsification
and timing-bias guardrail design only. It may be used to require that future
moving-average or threshold-style evidence explicitly prove no-lookahead timing
before any stronger claim is considered.

This outcome does not create a `ValidatedResearchArtifact`, create a
`ValidatedSignalDefinition`, approve a threshold, validate a signal, accept a
profitable strategy claim, approve paper trading, approve live trading, or
authorize implementation.

## Non-claims

This review does not establish:

- predictive edge
- profitability
- robust production threshold
- risk-adjusted return advantage
- signal validity
- validated artifact readiness
- validated signal definition readiness
- production threshold approval
- exact rule/test binding
- implementation readiness
- paper trading readiness
- live trading readiness

## Routing update

After this S01-only review, the next route is to proceed to
`P30-BL-002-S03` formal review as the second negative-control source.

Additional S01 evidence collection is not required before starting S03, because
S01 has passed only for the narrow negative-control/no-lookahead role. A later
phase must collect more S01 evidence before using it for exact timing-rule
reproduction, deterministic test binding, threshold comparison, or any stronger
claim.

`P30-BL-002` remains candidate-only, unvalidated, unapproved, not promoted,
not production-ready, and not implementation-ready.

## Remaining blockers

Evaluator implementation remains blocked by all of the following:

- `P30-BL-002-S03` review not completed
- `P30-BL-002-S05` review not completed
- `P30-BL-002-S08` methodology review not completed
- no `ValidatedResearchArtifact`
- no `ValidatedSignalDefinition`
- no approved threshold/config provenance
- no implementation scope approval
- no evaluator tests
- no deterministic production contract binding
- unresolved S01 exact timing convention, dataset, code/data, and
  deterministic reproduction details for any exact use beyond narrow
  negative-control framing

## Verification

Verification after Phase 32 Step 6:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
passed; Git emitted LF-to-CRLF working-copy warnings only for modified
existing docs

git status --short
 M docs/design/phase30_research_artifact_candidate_backlog.md
 M docs/design/phase31_research_track_next_action_plan.md
 M docs/design/phase32_dataset_specific_validation_candidate_selection.md
 M docs/design/phase32_p30_bl_002_limited_formal_review_intake_plan.md
 M docs/design/phase32_p30_bl_002_primary_source_verification_gate.md
 M docs/design/phase32_p30_bl_002_source_package.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_p30_bl_002_s01_formal_review.md
```

Manual documentation checks:

- edited markdown files have no trailing whitespace
- edited markdown files have exactly one final newline
- edited markdown files were inspected for completeness and were not truncated
