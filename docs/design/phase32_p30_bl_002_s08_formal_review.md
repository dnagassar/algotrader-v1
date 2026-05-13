# Phase 32 Step 8 - P30-BL-002-S08 Formal Review: FactSet PIT Methodology-Only Intake

## Purpose

This document formally reviews `P30-BL-002-S08` only. The review scope is
limited to whether the source can be used as methodology-only point-in-time
data material for future review discipline.

This review is not candidate-edge evidence. It is not a validation artifact,
does not validate a trading signal, does not approve a production threshold,
does not create a validated artifact, does not create a validated signal
definition, and does not imply implementation readiness. Methodology usefulness
is not signal validation.

## Prior state

- `P30-BL-001` is mechanics-only dispositioned. It is not validated,
  approved, production-ready, threshold-justified, or implementation-ready.
- `P30-BL-002` remains a sourcing and review-track handle only.
- Phase 32 Step 3 normalized `P30-BL-002-S01` through `P30-BL-002-S23` from
  supplied scout reports. Those entries remained candidate-only, unreviewed,
  unvalidated, unapproved, and not implementation-ready.
- Phase 32 Step 4 verified selected primary-source identities and found
  `P30-BL-002-S08` maybe eligible only for methodology-only PIT review intake.
- Phase 32 Step 5 scheduled `P30-BL-002-S08` as a methodology-only reference.
- Phase 32 Step 6 reviewed `P30-BL-002-S01` only and passed it only for
  limited negative-control/no-lookahead use.
- Phase 32 Step 7 reviewed `P30-BL-002-S03` only and passed it only for
  limited negative-control/data-snooping/OOS guardrail use.
- This Step 8 review is intentionally performed before `P30-BL-002-S05` so
  the project records point-in-time, no-lookahead, survivorship, and
  restatement expectations before candidate-evidence review begins.

This review does not revise the S01 or S03 dispositions. Any later use of S08
to revisit S01 or S03 would require a separately scoped future follow-up.

## Source identity

| Field | Review record |
| --- | --- |
| Normalized source id | `P30-BL-002-S08` |
| Title | "Accurately Backtesting Financial Models Through Point-in-Time Consensus Estimates" |
| Author/source | Annabel Hudson, Richard Dutheil, and Juliana Germain; FactSet |
| Date/version | Step 4 records no explicit publication date verified in the PDF; the PDF states that the point-in-time database is not available before December 2009 and describes consensus methodology as of September 9, 2017 |
| Primary-source link or citation text | FactSet PDF at <https://www.insight.factset.com/hubfs/Resources%20Section/White%20Papers/ID11996_point_in_time.pdf> |
| Source type | Vendor white paper / methodology document |
| Verified source identity status | Primary FactSet PDF verified by Step 4; publication/version date, license/access restrictions, exact FQL behavior, timezone/cutoff behavior under local data constraints, and applicability to any future offline point-in-time store remain unresolved |

## Source-of-truth documents used

This review uses these repository documents as the source of truth:

- Phase 32 Step 4 primary source verification gate:
  [`phase32_p30_bl_002_primary_source_verification_gate.md`](phase32_p30_bl_002_primary_source_verification_gate.md)
- Phase 32 Step 5 limited formal review intake plan:
  [`phase32_p30_bl_002_limited_formal_review_intake_plan.md`](phase32_p30_bl_002_limited_formal_review_intake_plan.md)
- Existing `P30-BL-002` source package:
  [`phase32_p30_bl_002_source_package.md`](phase32_p30_bl_002_source_package.md)
- Existing backlog and routing docs as status context only.

No new sources are introduced by this review. Scout report claims remain
candidate-discovery context only unless already normalized and bounded in the
existing S01-S23 package and Step 4 gate.

## Review scope

This review is limited to methodology-only PIT material:

- point-in-time data methodology framing
- snapshot semantics and `as_of` discipline
- survivorship-bias awareness
- restatement / historical revision awareness
- deletion, correction, currency-change, and late-entry awareness
- lookahead-risk framing
- constraints for later candidate-evidence reviews that use historical equity
  data, including any future `P30-BL-002-S05` review

This review excludes:

- candidate-edge evidence
- production threshold approval
- time-series momentum validation
- strategy validation
- profitability assessment
- predictive-edge assessment
- threshold approval
- signal-definition binding
- implementation readiness
- trading readiness
- any real evaluator, signal computation, ranking, scoring, direction,
  confidence, probability, or actionability

## Evidence reviewed

This review uses the Phase 32 Step 4 gate and Phase 32 Step 5 intake plan as
the source of truth for S08 identity and scope. It checks the Step 3 source
package only as normalized candidate-discovery context.

The repository documents support the following:

- Dataset scope: Step 4 identifies FactSet point-in-time consensus estimates
  snapshots for covered companies, including estimate items, statistics,
  consensus windows, and related FactSet estimate fields.
- Asset universe: Step 4 identifies the FactSet Estimates universe / listed
  equities covered by the vendor database, while noting that exact licensed
  universe depends on access.
- Snapshot semantics: Step 4 records daily local-midnight company snapshots
  and exclusion of data entered after that snapshot from that date's consensus
  calculation.
- Revision awareness: Step 4 records that the source explains why later
  corrections, deletions, currency changes, and local-time cutoffs can alter
  historical backtests.
- Input timing relevance: Step 4 classifies S08 as methodology-only relevance
  to `as_of`, input timestamp, and snapshot semantics, not a signal-threshold
  source.
- Reproducibility limits: Step 4 records that proprietary FactSet access is
  required and that the PDF lists FQL and Screening function identifiers but
  does not provide open data or open code.
- Strategy evidence: Step 4 records no strategy robustness evidence. The
  source is infrastructure/methodology evidence only.

## Review findings

| Criterion from Step 5 | Finding |
| --- | --- |
| Snapshot semantics | Useful for methodology-only framing. Later reviews must distinguish snapshot date, local cutoff, company coverage, observed value, data-release timing, and whether a record reflects information available at the review `as_of`. Exact local implementation remains unresolved. |
| Survivorship-bias awareness | Supported only as a methodology expectation. Later candidate-evidence reviews involving historical equities must state universe membership timing, coverage changes, deletions, exclusions, and whether dead or removed entities remain observable. S08 does not supply this project's dataset. |
| Restatement / historical revision awareness | Supported as review discipline. Later reviews must identify whether inputs are latest-revised, historically corrected, deleted, currency-adjusted, or frozen as known at the historical observation time. S08 does not approve any specific restatement policy for this repo. |
| Lookahead-risk framing | Passes narrowly for methodology framing. Later reviews must separate observation timestamp, source entry timestamp, release or availability timestamp, snapshot timestamp, signal timestamp, execution timestamp, and return-measurement timestamp before stronger claims can be considered. |
| Reproducibility and access | Blocking for implementation. Proprietary FactSet access, license terms, exact FQL behavior, and absence of open replay data mean S08 cannot provide a deterministic local dataset, code path, or reproduction package. |
| Candidate-evidence relevance | Indirect only. S08 can constrain later evidence reviews, including S05, by requiring PIT/no-lookahead/survivorship/restatement discipline. It cannot itself support any candidate edge, threshold, signal definition, or trading rule. |
| Production-threshold unsuitability | Not suitable. The review finds no approved threshold, no accepted comparator evidence, no validated dataset window, no profitability evidence, no OOS or robustness acceptance for implementation, no validated artifact, and no implementation-ready signal definition. |

## Methodology expectations for later candidate-evidence reviews

Any later candidate-evidence review involving historical equity data must
record, at minimum:

- whether data are point-in-time or latest-revised
- the meaning of `as_of`, observation timestamp, release timestamp, source
  entry timestamp, and local snapshot timestamp
- universe membership timing and survivorship handling
- corporate-action, restatement, deletion, correction, exclusion, and
  currency-change handling
- missing, stale, late-entered, and corrected data handling
- feature timing, label timing, rebalance timing, and execution timing
- whether code/data can be replayed deterministically without credentials,
  network calls, or vendor runtime access under normal pytest
- whether any unresolved vendor or data-contract gap blocks promotion,
  validation, tests, or implementation

These expectations are review constraints only. They do not create an
implementation path or production data contract.

## Pass/fail outcome

Outcome: pass for methodology-only PIT review material only.

The pass is deliberately narrow. `P30-BL-002-S08` may support point-in-time
data methodology framing, survivorship-bias awareness, restatement /
historical-revision awareness, lookahead-risk framing, and constraints for
later candidate-evidence reviews.

This outcome does not create a `ValidatedResearchArtifact`, create a
`ValidatedSignalDefinition`, approve a threshold, validate a signal, accept a
profitable strategy claim, approve paper trading, approve live trading, or
authorize implementation. It must not be promoted to `ValidatedResearchArtifact`
and must not authorize any `src/` changes.

## What S08 does not support

S08 does not support:

- profitability claims
- time-series momentum validation
- threshold approval
- signal definition
- implementation readiness
- trading readiness
- strategy validation
- predictive-edge claims
- production config provenance
- evaluator tests
- broker, OMS, runtime, scheduler, persistence, portfolio, ledger,
  reconciliation, Alpaca, ML, or LLM trading-path behavior

## Impact on S05

The later `P30-BL-002-S05` review must be evaluated under the PIT,
no-lookahead, survivorship, and restatement expectations recorded here.

For S05, the later review must not accept candidate evidence unless it
explicitly records how the reviewed source handles:

- data availability through time
- instrument or universe membership through time
- vendor or source revisions
- stale or corrected data
- lookback and holding-window lag structure
- signal, rebalance, execution, and return-measurement timing
- deterministic reproduction limits

Even if S05 later passes, that pass should mean only "eligible for further
structured evaluation." It would not mean implementation-ready, signal-ready,
threshold-approved, trading-ready, or promoted to a validated artifact.

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
- exact PIT data contract
- exact OOS result acceptance
- implementation readiness
- paper trading readiness
- live trading readiness

## Routing update

After this S08-only methodology review, the next route is to proceed to
`P30-BL-002-S05` formal review as the first limited candidate-evidence source,
using this S08 review as a PIT/no-lookahead/survivorship/restatement
methodology constraint.

Additional S08 evidence collection is not required before starting S05 because
S08 has passed only for methodology-only PIT framing. A later phase must
collect more S08 or replacement PIT evidence before using it for exact data
contract binding, exact vendor query semantics, deterministic local replay, or
any stronger claim.

`P30-BL-002` remains candidate-only, unvalidated, unapproved, not promoted,
not production-ready, and not implementation-ready.

## Remaining blockers

Evaluator implementation remains blocked by all of the following:

- no `P30-BL-002-S05` formal review
- no exact `ValidatedResearchArtifact`
- no exact `ValidatedSignalDefinition`
- no dataset-specific reproduction
- no production threshold/config provenance
- no applied no-lookahead audit
- no robustness/out-of-sample review accepted for implementation
- no evaluator tests
- no implementation approval
- unresolved S08 publication/version date, license/access restrictions, exact
  FQL behavior, timezone/cutoff behavior under local data constraints,
  deterministic local replay path, and applicability to any future offline
  point-in-time store

## Verification

Verification after Phase 32 Step 8:

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
?? docs/design/phase32_p30_bl_002_s08_formal_review.md
```

Manual documentation checks:

- edited markdown files have no trailing whitespace
- edited markdown files have exactly one final newline
- edited markdown files were inspected for completeness and were not truncated
