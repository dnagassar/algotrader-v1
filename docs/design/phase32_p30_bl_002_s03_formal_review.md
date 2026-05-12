# Phase 32 Step 7 — P30-BL-002-S03 Formal Review: Sullivan/Timmermann/White Data-Snooping Negative Control

## Purpose

This document formally reviews `P30-BL-002-S03` only. The review scope is
limited to whether the source can be used as a negative-control /
data-snooping / out-of-sample guardrail reference.

This review does not validate a trading signal, approve a production
threshold, create a validated artifact, create a validated signal definition,
or imply implementation readiness. Negative-control usefulness is not signal
validation.

## Prior state

- `P30-BL-001` is mechanics-only dispositioned. It is not validated,
  approved, production-ready, threshold-justified, or implementation-ready.
- `P30-BL-002` remains a sourcing and review-track handle only.
- Phase 32 Step 3 normalized `P30-BL-002-S01` through `P30-BL-002-S23` from
  supplied scout reports. Those entries remained candidate-only, unreviewed,
  unvalidated, unapproved, and not implementation-ready.
- Phase 32 Step 4 verified selected primary-source identities and found
  `P30-BL-002-S03` eligible only for limited negative-control /
  data-snooping methodology review intake.
- Phase 32 Step 5 scheduled `P30-BL-002-S03` as the second formal review,
  after `P30-BL-002-S01` and before `P30-BL-002-S05` and `P30-BL-002-S08`.
- Phase 32 Step 6 reviewed `P30-BL-002-S01` only and passed it only for
  limited negative-control/no-lookahead use. That S01 pass does not support
  production threshold approval, signal validation, or implementation
  readiness.

## Source identity

| Field | Review record |
| --- | --- |
| Normalized source id | `P30-BL-002-S03` |
| Title | "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap" |
| Author/source | Ryan Sullivan, Allan Timmermann, and Halbert White; Journal of Finance / American Finance Association publication record; SSRN record |
| Date/version | Step 4 records SSRN as posted May 18, 1999, with a prior UCSD discussion-paper version posted March 8, 1998; Journal of Finance volume 54, issue 5, October 1999, pages 1647-1691 |
| Primary-source link or citation text | SSRN abstract page at <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=160330>; Journal of Finance issue page at <https://afajof.org/issue/volume-54-issue-5/>; DOI `10.1111/0022-1082.00163` |
| Source type | Peer-reviewed empirical finance paper and working-paper record |
| Verified source identity status | Primary SSRN identity plus Journal of Finance publication details verified by Step 4; full article access, exact rule tables, exact sample dates, OOS details, transaction-cost assumptions, bootstrap assumptions, and reproducibility path remain unresolved in repository docs |

## Review scope

This review is limited to:

- data-snooping bias
- technical trading-rule universe
- multiple-testing / Reality Check framing
- in-sample versus out-of-sample expectations
- negative-control usefulness
- validation guardrail relevance

This review excludes:

- production threshold approval
- strategy validation
- profitability assessment
- predictive-edge assessment
- signal-definition binding
- implementation approval
- any real evaluator, signal computation, ranking, scoring, direction,
  confidence, probability, or actionability

## Evidence reviewed

This review uses the Phase 32 Step 4 primary-source verification gate and the
Phase 32 Step 5 intake plan as the source of truth for S03 identity and review
scope. It also checks the Step 3 source package only as normalized
candidate-discovery context.

The repository documents support the following:

- Rule universe: Step 4 verifies at abstract level that the source expands the
  Brock, Lakonishok, and LeBaron rule universe and applies rules to 100 years
  of daily Dow Jones Industrial Average data. Step 3 records candidate context
  for filter, moving-average, support/resistance, channel, and OBV rules, but
  exact rule tables, rule count, parameter grids, and selection process remain
  unresolved.
- Data-snooping issue: Step 4 verifies direct relevance to data snooping
  across technical-rule universes and multiple-comparison adjustment.
- Bootstrap / Reality Check method: Step 4 verifies that the source uses
  White's Reality Check bootstrap methodology to evaluate technical trading
  rules while quantifying data-snooping bias. Bootstrap assumptions, test
  statistics, and dependence handling remain unresolved.
- In-sample versus out-of-sample structure: Step 3 records candidate context
  describing in-sample selection and separate OOS evaluation. Step 4 does not
  fully verify the claimed strict post-selection OOS extension, so exact OOS
  dates, design, and result are unresolved and unaccepted.
- Dataset/timeframe: Step 4 verifies 100 years of daily DJIA data at abstract
  level. Exact start/end dates and any separate out-of-sample window remain
  unresolved.
- Reproducibility materials: Step 4 records that SSRN states "Not Available
  for Download" and that no open code or packaged dataset was verified.
- Negative-control relevance: Step 4 classifies the source as a
  data-snooping methodology and technical-rule-universe negative-control
  candidate.
- Limitations: available repo evidence supports source identity and
  methodology relevance, not implementation. Single-index historical focus,
  lack of verified public code/package, unresolved rule tables, unresolved
  exact OOS design, and unresolved deterministic reproducibility all remain
  blocking gaps for any stronger use.

## Review findings

| Criterion from Step 5 | Finding |
| --- | --- |
| Exact data-snooping finding | Verified only at the source-role level: S03 is directly about data snooping across technical trading-rule universes. Repo docs do not fully verify exact p-values, tables, rule-level results, or the final empirical finding from the full article. |
| Trading-rule universe | Partially identified. Step 4 verifies an expanded Brock/Lakonishok/LeBaron technical-rule universe on daily DJIA data. Step 3 records candidate details for rule families and a large parameter universe, but exact rule tables, grids, and selection process remain unresolved. |
| Data-snooping adjustment method | Relevant and verified at method-name level. Step 4 verifies use of White's Reality Check bootstrap methodology to quantify data-snooping bias. Exact implementation details remain unresolved. |
| Bootstrap / Reality Check method | Suitable for guardrail framing only. The source can support a requirement that future optimized rule evidence must account for multiple testing, but it cannot bind this project to a specific bootstrap implementation, p-value calculation, or acceptance threshold without additional sourcing. |
| In-sample versus out-of-sample structure | Useful as an OOS guardrail expectation only. Step 3 records candidate context for in-sample selection and separate OOS evaluation, while Step 4 leaves the strict post-selection OOS extension, exact sample dates, and OOS result unverified. |
| Limitations | Single-index historical focus, unresolved full-text details, no verified public code/package, unresolved transaction costs, unresolved exact sample windows, unresolved OOS details, and no deterministic reproduction path. |
| Negative-control suitability | Passes narrowly for negative-control/data-snooping/OOS guardrail use only. S03 may be cited to require falsification pressure, multiple-testing awareness, Reality Check-style skepticism, and explicit post-selection OOS expectations for later evidence. |
| Production-threshold unsuitability | Not suitable. The review finds no approved production threshold, no accepted comparator evidence, no accepted predictive edge, no accepted profitability claim, no accepted robust OOS result, no validated artifact, and no implementation-ready signal definition. |

## Pass/fail outcome

Outcome: pass for negative-control/data-snooping/OOS guardrail use only.

The pass is deliberately narrow. `P30-BL-002-S03` may support falsification,
multiple-testing awareness, data-snooping guardrail design, and
out-of-sample negative-control expectations only. It may be used to require
that later optimized technical-rule or threshold-style evidence explicitly
separate in-sample selection from post-selection evaluation and account for
multiple comparisons before any stronger claim is considered.

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
- exact OOS result acceptance
- implementation readiness
- paper trading readiness
- live trading readiness

## Routing update

Because S03 passes only for negative-control/data-snooping/OOS guardrail use,
the default next route is to proceed to `P30-BL-002-S05` formal review as the
first limited candidate-evidence source.

`P30-BL-002-S08` may still be reviewed before S05 only if the project decides
to lock point-in-time methodology before reviewing candidate evidence. This
S03 review does not require that reorder.

Additional S03 evidence collection is not required before starting S05,
because S03 has passed only for the narrow negative-control/data-snooping/OOS
guardrail role. A later phase must collect more S03 evidence before using it
for exact rule reproduction, exact bootstrap method binding, exact OOS result
claims, deterministic test binding, threshold comparison, or any stronger
claim.

`P30-BL-002` remains candidate-only, unvalidated, unapproved, not promoted,
not production-ready, and not implementation-ready.

## Remaining blockers

Evaluator implementation remains blocked by all of the following:

- `P30-BL-002-S05` review not completed
- `P30-BL-002-S08` methodology review not completed
- no `ValidatedResearchArtifact`
- no `ValidatedSignalDefinition`
- no approved threshold/config provenance
- no implementation scope approval
- no evaluator tests
- no deterministic production contract binding
- unresolved S03 full-text, exact rule tables, exact sample windows, exact OOS
  design, transaction-cost assumptions, bootstrap assumptions, public
  code/data availability, and deterministic reproduction details for any exact
  use beyond narrow negative-control/data-snooping/OOS guardrail framing

## Verification

Verification after Phase 32 Step 7:

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
?? docs/design/phase32_p30_bl_002_s03_formal_review.md
```

Manual documentation checks:

- edited markdown files have no trailing whitespace
- edited markdown files have exactly one final newline
- edited markdown files were inspected for completeness and were not truncated
