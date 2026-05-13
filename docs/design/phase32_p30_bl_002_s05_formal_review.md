# Phase 32 Step 9 - P30-BL-002-S05 Formal Review: Time-Series Momentum Candidate-Evidence Intake

## Purpose

This document formally reviews `P30-BL-002-S05` only. The review scope is
limited to whether S05 can be used as limited candidate evidence for future
structured evaluation planning.

This review is not a validation artifact. It is not implementation-ready, does
not approve a production threshold, does not create a validated artifact, does
not create a validated signal definition, and does not imply trading readiness.
Candidate-evidence usefulness is not signal validation.

## Prior state

- `P30-BL-001` is mechanics-only dispositioned. It is not validated,
  approved, production-ready, threshold-justified, or implementation-ready.
- `P30-BL-002` remains a sourcing and review-track handle only.
- Phase 32 Step 3 normalized `P30-BL-002-S01` through `P30-BL-002-S23` from
  supplied scout reports. Those entries remained candidate-only, unreviewed,
  unvalidated, unapproved, and not implementation-ready.
- Phase 32 Step 4 verified selected primary-source identities and found
  `P30-BL-002-S05` eligible only for limited direct-source formal review
  intake.
- Phase 32 Step 5 scheduled `P30-BL-002-S05` as the first limited
  candidate-evidence review after negative-control and PIT methodology
  reviews.
- Phase 32 Step 6 reviewed `P30-BL-002-S01` only and passed it only for
  limited negative-control/no-lookahead use.
- Phase 32 Step 7 reviewed `P30-BL-002-S03` only and passed it only for
  limited negative-control/data-snooping/OOS guardrail use.
- Phase 32 Step 8 reviewed `P30-BL-002-S08` only and passed it only for
  methodology-only PIT review material.

This review does not revise the S01, S03, or S08 dispositions. Any need to
revisit those reviews must be recorded as a future follow-up only.

## Source identity

| Field | Review record |
| --- | --- |
| Normalized source id | `P30-BL-002-S05` |
| Title | "Time series momentum" / "Time Series Momentum" |
| Author/source | Tobias J. Moskowitz, Yao Hua Ooi, and Lasse Heje Pedersen; Journal of Financial Economics, Elsevier |
| Date/version | ScienceDirect article page reports Journal of Financial Economics volume 104, issue 2, May 2012, pages 228-250, with copyright 2011; Step 4 also records metadata from the supplied DOCX verification report |
| Primary-source link or citation text | ScienceDirect article page at <https://www.sciencedirect.com/science/article/pii/S0304405X11002613>; DOI `10.1016/j.jfineco.2011.11.003`; NYU/Stern author-hosted PDF at <https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf> |
| Source type | Peer-reviewed academic paper |
| Verified source identity status | Primary article identity and detailed TSM provenance were verified by Step 4 for limited direct-source intake; roll rules, data reconstruction, reproducibility, costs, and local PIT alignment remain unresolved |

## Source-of-truth documents used

This review uses these repository documents as the source of truth:

- Phase 32 Step 4 primary source verification gate:
  [`phase32_p30_bl_002_primary_source_verification_gate.md`](phase32_p30_bl_002_primary_source_verification_gate.md)
- Phase 32 Step 5 limited formal review intake plan:
  [`phase32_p30_bl_002_limited_formal_review_intake_plan.md`](phase32_p30_bl_002_limited_formal_review_intake_plan.md)
- S01 formal review:
  [`phase32_p30_bl_002_s01_formal_review.md`](phase32_p30_bl_002_s01_formal_review.md)
- S03 formal review:
  [`phase32_p30_bl_002_s03_formal_review.md`](phase32_p30_bl_002_s03_formal_review.md)
- S08 formal review:
  [`phase32_p30_bl_002_s08_formal_review.md`](phase32_p30_bl_002_s08_formal_review.md)
- Existing `P30-BL-002` source package:
  [`phase32_p30_bl_002_source_package.md`](phase32_p30_bl_002_source_package.md)
- Existing backlog and routing docs as status context only.

No new sources are introduced by this review. Scout report claims remain
candidate-discovery context only unless already normalized and bounded in the
existing S01-S23 package and Step 4 gate.

## Review scope

This review treats S05 as limited candidate evidence only. It evaluates whether
S05 can support future structured evaluation planning under:

- the S08 PIT/no-lookahead, survivorship, and restatement expectations
- the S01 negative-control/no-lookahead timing guardrails
- the S03 negative-control/data-snooping/OOS guardrails

This review excludes:

- validation artifact creation
- implementation approval
- production threshold/config approval
- signal-definition binding
- profitability or live-trading claims
- assumption that reported source results generalize
- any real evaluator, signal computation, signal scoring, ranking, direction,
  confidence, probability, or actionability
- broker, OMS, runtime, scheduler, persistence, portfolio, ledger,
  reconciliation, Alpaca, ML, or LLM trading-path behavior

## Exact claim under review

S05 reports a time-series momentum research claim for lagged own excess returns
in futures and forward contracts. In the bounded form usable by this review,
the claim is:

`P30-BL-002-S05` is a peer-reviewed academic source reporting historical
evidence for a time-series momentum candidate built from lagged own excess
returns, including sign-based lagged-return variants, across a multi-asset
futures/forwards universe.

This review does not accept the reported claim as profitable, robust,
generalizable, implementation-ready, or suitable for a production threshold.

## Evidence reviewed

This review uses the Phase 32 Step 4 gate and Phase 32 Step 5 intake plan as
the source of truth for S05 identity and review scope. It checks the Step 3
source package only as normalized candidate-discovery context and applies the
S01, S03, and S08 formal-review constraints.

The repository documents support the following:

- Source identity: Step 4 verifies the ScienceDirect article page, DOI, and
  NYU/Stern author-hosted PDF for the Moskowitz/Ooi/Pedersen paper.
- Dataset scope: Step 4 records 58 liquid futures and forward contracts across
  commodities, currencies, developed equity index futures, and developed
  government bond futures, with data from January 1965 through December 2009
  and primary evaluation from 1985 onward.
- Frequency: Step 4 records monthly formation and holding rules over the
  paper's historical sample.
- Input definition: Step 4 records lagged own excess returns; a sign-based
  variant uses cumulative excess return over a selected lookback and applies
  the sign of that lagged return. Step 4 records lookback and holding grids
  including 1, 3, 6, 9, 12, 24, 36, and 48 months.
- Candidate threshold relevance: Step 4 records relevance to a deterministic
  zero threshold on lagged-return sign and to lookback/holding parameter
  provenance. This relevance is not threshold approval.
- Validation-design targets: Step 4 records pooled regressions, asset-class
  decomposition, factor regressions, parameter comparisons, cross-asset,
  contract-maturity, volatility-scaling, parameter, and subperiod checks.
  These remain review targets and are not accepted as project validation.
- No-lookahead targets: Step 4 records lag-only construction and lagged
  volatility estimates intended to avoid lookahead in volatility estimation.
  Database-level PIT snapshot semantics are not the paper's focus.
- Reproducibility limits: Step 4 records that the primary paper documents data
  sources and methodology but does not provide a formal code repository or
  turnkey downloadable dataset in the PDF itself.
- Implementation limits: Step 4 records that roll mechanics, data-vendor
  reproducibility, transaction costs, margin/leverage constraints, and exact
  factor timing require formal review.

## Required review questions

| Question | Review answer |
| --- | --- |
| What exact claim is S05 making? | S05 reports historical time-series momentum evidence based on lagged own excess returns, including sign-based lagged-return variants, across a multi-asset futures/forwards universe. This review treats that as a bounded candidate-evidence claim only. |
| What asset universe, dataset, period, and frequency are involved? | Step 4 records 58 liquid futures and forward contracts across commodities, currencies, developed equity index futures, and developed government bond futures; data from January 1965 through December 2009; primary evaluation from 1985 onward; monthly formation and holding rules. Exact instrument-level starts, contract availability, and reconstruction remain unresolved. |
| Are PIT, survivorship, restatement, and lookahead controls explicit? | Partially. S05 uses lagged returns and Step 4 records lag-only construction plus lagged volatility estimates. Under S08, this is not enough for local acceptance because database-level PIT snapshots, instrument availability through time, roll revisions, stale/corrected data, and local replay semantics remain unresolved. |
| Are transaction costs, slippage, liquidity, and execution assumptions discussed? | Step 4 records that transaction costs, margin/leverage constraints, roll mechanics, and data-vendor reproducibility require formal review. The available repository evidence does not establish project-acceptable frictions, liquidity, slippage, financing, or execution assumptions. |
| Is there out-of-sample or robustness evidence? | Step 4 records cross-asset, contract-maturity, volatility-scaling, parameter, and subperiod checks as formal-review targets. Under S03, these are not accepted as project robustness or OOS evidence until selection, multiple-testing, post-selection evaluation, and deterministic reproduction are locally addressed. |
| Is the evidence reproducible from the available source material? | Not yet. The primary paper documents data sources and methodology, but Step 4 records no formal code repository or turnkey downloadable dataset in the PDF. Project-local deterministic reproduction remains absent. |
| What assumptions and limitations are unresolved? | Futures roll construction, instrument availability, data-vendor access, PIT replay, transaction costs, slippage, liquidity, leverage/margin, exact factor timing, volatility-estimator replay, multiple-testing treatment, and local deterministic reproducibility remain unresolved. |
| What would need to be reproduced locally before any future promotion? | A deterministic offline reconstruction of the eligible instrument universe, contract rolls, excess returns, lagged-return lookbacks, holding windows, lagged volatility estimates, transaction-cost assumptions, factor/regression checks, robustness checks, and no-lookahead/PIT audit would be required before any future promotion discussion. |

## Review findings

| Criterion from Step 5 and prior guardrails | Finding |
| --- | --- |
| Candidate-evidence relevance | S05 is the strongest selected direct time-series momentum source candidate. It may support limited planning around a lagged-own-excess-return candidate-evidence claim. |
| PIT/no-lookahead discipline from S08 | Conditional only. Lagged-return construction is relevant, but S05 does not itself provide this project's PIT data contract, deterministic snapshot semantics, roll-history replay, or restatement/revision policy. |
| Timing guardrail from S01 | Conditional only. Future work must explicitly separate observation, lookback end, signal timestamp, rebalance timestamp, execution timestamp, and return-measurement timestamp before any stronger claim is considered. |
| Data-snooping/OOS guardrail from S03 | Conditional only. Future work must separate parameter selection from evaluation, address multiple comparisons across lookbacks/holding windows/assets, and reproduce robustness claims locally before any stronger claim is considered. |
| Dataset and universe | Useful for planning only. The reviewed docs identify a multi-asset futures/forwards universe and historical period, but exact instrument-level availability, data vendors, roll choices, and inclusion timing are not project-local. |
| Transaction-cost and execution assumptions | Blocking for stronger use. The available repository evidence does not establish accepted costs, slippage, liquidity, margin, leverage, financing, or execution assumptions. |
| Reproducibility | Blocking for stronger use. No project-local deterministic dataset, code, replay script, or normal-pytest reproduction exists. |
| Production-threshold unsuitability | Not suitable. The review finds no exact validated artifact, no exact validated signal definition, no accepted threshold/config provenance, no applied no-lookahead audit inside the project, no evaluator tests, and no implementation-scope approval. |

## What S05 may support

If treated with the constraints above, S05 may support:

- a bounded time-series momentum candidate-evidence claim
- future structured evaluation planning
- possible future reproduction requirements
- constraints for any future candidate signal-definition discussion
- a future work item to reconstruct data, timing, costs, and robustness checks
  under deterministic offline constraints

The strongest allowed interpretation is "eligible for further structured
evaluation."

## What S05 must not support

S05 must not support:

- implementation approval
- production threshold/config approval
- `ValidatedResearchArtifact` creation
- `ValidatedSignalDefinition` creation
- profitability claims
- live-trading claims
- assumption that reported source results generalize
- signal computation, scoring, ranking, direction, confidence, probability, or
  actionability
- production config provenance
- paper-trading readiness
- broker, OMS, runtime, scheduler, persistence, portfolio, ledger,
  reconciliation, Alpaca, ML, or LLM trading-path behavior

## Pass/fail outcome

Outcome: conditional pass for limited candidate-evidence planning only.

The pass is deliberately narrow. `P30-BL-002-S05` may be used as limited
candidate evidence for further structured evaluation planning only, under the
S08 PIT/no-lookahead/survivorship/restatement expectations and the S01/S03
negative-control guardrails.

This outcome does not create a `ValidatedResearchArtifact`, create a
`ValidatedSignalDefinition`, approve a threshold, validate a signal, accept a
profitable strategy claim, approve paper trading, approve live trading, or
authorize implementation. It must not be promoted to a validated artifact and
must not authorize any `src/` changes.

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

After this S05-only limited candidate-evidence review, the next route remains
blocked from implementation. A later docs-only phase may design a structured
local reproduction plan or a stricter evidence checklist, but only after
preserving the S08 PIT expectations and the S01/S03 negative-control
guardrails.

Additional S05 evidence collection is required before using it for exact
artifact support, exact signal-definition binding, deterministic test binding,
threshold comparison, or any stronger claim.

`P30-BL-002` remains candidate-only, unvalidated, unapproved, not promoted,
not production-ready, and not implementation-ready.

## Remaining blockers

Evaluator implementation remains blocked by all of the following:

- no exact `ValidatedResearchArtifact`
- no exact `ValidatedSignalDefinition`
- no project-local deterministic reproduction
- no production threshold/config provenance
- no applied no-lookahead audit inside the project
- no accepted implementation-scope approval
- no evaluator tests
- unresolved S05 instrument-level universe reconstruction
- unresolved futures roll rules and contract selection
- unresolved data-vendor access and offline PIT replay path
- unresolved transaction-cost, slippage, liquidity, margin, leverage, and
  financing assumptions
- unresolved parameter-selection, multiple-testing, OOS, and robustness replay
- unresolved exact mapping from any candidate evidence to this project's
  advisory pre-risk semantics

## Verification

Verification after Phase 32 Step 9:

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
?? docs/design/phase32_p30_bl_002_s05_formal_review.md
```

Manual documentation checks:

- edited markdown files have no trailing whitespace
- edited markdown files have exactly one final newline
- edited markdown files were inspected for completeness and were not truncated
