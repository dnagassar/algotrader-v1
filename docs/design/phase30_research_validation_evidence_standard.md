# Phase 30 Research Validation Evidence Standard

## 1. Purpose

Phase 30 Step 2 defines a reusable research validation checklist and evidence
standard for any future research artifact that may support a real evaluator.

This phase creates no research artifact, creates no validated signal
definition, implements no evaluator, and adds no signal computation. The
standard exists so future `ValidatedResearchArtifact` candidates are reviewed
against a fixed yardstick before they can support a
`ValidatedSignalDefinition` review or any evaluator implementation.

The standard is documentation-only. It does not make any advisory evaluator
actionable, production-ready, risk-approved, execution-ready, broker-aware, or
portfolio-aware.

## 2. Why An Evidence Standard Is Needed First

Reviewing a candidate artifact before defining "validated" risks lowering the
evidence bar to fit whatever the candidate already contains. A fixed standard
keeps the review independent of any one candidate artifact, threshold, dataset,
indicator, or strategy idea.

The standard is intended to prevent:

- vibes-based thresholds
- unsupported indicator logic
- hidden lookahead
- survivorship bias
- unclear datasets
- non-reproducible research
- accidental profitability claims
- advisory outputs being mistaken for trade instructions

The safest sequence is standard first, candidate artifact review second,
validated signal-definition binding third, and implementation only after all
blockers are resolved.

## 3. Required Research Artifact Evidence

A future `ValidatedResearchArtifact` candidate must document enough evidence
for reviewers to understand exactly what was studied, how it was studied, what
claim it supports, and what it does not claim.

Required evidence includes:

- artifact id
- artifact version
- author, source, or provenance
- creation date or review date if supported
- repo commit or reproducibility reference if available
- dataset or source description
- dataset window
- asset universe
- timeframe or bar size
- point-in-time assumptions
- survivorship-bias handling
- lookahead-bias controls
- data cleaning assumptions
- missing-data handling
- input definition
- indicator formula or transformation
- threshold rationale
- metric definitions
- validation procedure
- assumptions
- limitations
- non-claims

Missing evidence does not automatically mean a candidate is useless for
research discussion, but it prevents that candidate from supporting production
evaluator implementation until the gap is resolved or the review outcome is
explicitly classified as informational only.

## 4. Reproducibility Requirements

A future artifact should explain whether it can be regenerated
deterministically and what would be required to regenerate it.

The artifact should document:

- whether it can be regenerated deterministically
- what inputs are required to regenerate it
- what code, notebook, or script produced it, if applicable
- what data version or sample was used
- whether outputs are stable across runs
- whether randomness was used
- if randomness was used, whether it was explicitly seeded and documented

If an artifact cannot be regenerated, the review must state that limitation and
classify the artifact accordingly. Non-reproducible material may inform
research direction, but it must not be treated as sufficient evidence for a
production evaluator threshold.

## 5. Dataset And Bias Controls

The artifact must discuss data scope and bias controls in enough detail for a
reviewer to audit the result without guessing.

The review should verify discussion of:

- point-in-time correctness
- no future data in indicators
- no future data in labels
- no leakage through feature construction
- survivorship bias
- delisting bias where applicable
- corporate action handling where applicable
- timezone and session handling
- resampling rules
- stale or missing observations
- sample size limitations

Any uncertainty in these controls should be treated as an implementation
blocker for evaluator code. Hidden future data, ambiguous universe membership,
or unclear timestamp handling is incompatible with the deterministic core.

## 6. Statistical Claim Classification

A future artifact must classify what kind of claim it supports. Stronger
claims require stronger evidence, more careful validation, and clearer
limitations.

Possible claim categories:

- mechanical transformation only
- threshold sanity check
- regime indicator
- predictive relationship
- risk filter
- profitability claim
- robustness claim

For the threshold-style advisory evaluator, the artifact must be clear about
whether the threshold is merely a deterministic advisory condition or whether
it claims predictive or profitability value. A deterministic advisory condition
can support a narrow evaluator boundary only if its threshold is traceable and
its non-claims are explicit. Predictive, profitability, risk-filter, and
robustness claims require stronger evidence than a mechanical transformation
or threshold sanity check.

## 7. Non-Claims Section

Every future research artifact should explicitly state what it does not prove.
This prevents advisory metadata from being read as trading authorization.

Expected non-claims include:

- not a profitability guarantee
- not a risk-adjusted return claim unless separately validated
- not a live-trading claim
- not a trade recommendation
- not risk approval
- not execution readiness
- not portfolio-aware
- not broker-aware

If a candidate artifact does not include explicit non-claims, future reviewers
should require them before the artifact can support evaluator implementation.

## 8. Binding To `ValidatedSignalDefinition`

A research artifact must bind clearly to the specific signal definition it
supports. The evidence must support that signal definition, not a loosely
related idea.

Future review should verify:

- the signal id matches the artifact
- the signal version matches the artifact
- the required input names match
- the input types match
- the indicator semantics match
- threshold and comparator semantics match
- assumptions and limitations match
- artifact evidence supports this signal definition directly

If the signal definition changes input names, value types, indicator formulas,
threshold semantics, comparator semantics, assumptions, or limitations, the
artifact binding must be re-reviewed.

## 9. Threshold And Config Provenance

Any future production threshold value must be traceable to reviewed research
evidence. The threshold must have an explicit source and must preserve the
artifact id/version that supports it.

The threshold must not come from:

- ad hoc manual tuning inside evaluator code
- runtime state
- environment variables
- broker or account state
- portfolio state
- hidden config files
- LLM output
- ML inference

Acceptable future threshold sources may include:

- explicit reviewed evaluator config tied to artifact id/version
- evaluator-local constant only if tied to artifact id/version
- test-only placeholder values that are clearly isolated from production
  semantics

Test-only placeholders such as `Decimal("1")` remain non-production
semantics. They must not be promoted into a real evaluator threshold unless a
later review ties the production threshold to exact validated research and a
validated signal definition.

## 10. Advisory-Only Doctrine

Research validation does not make evaluator output actionable. Even a
research-supported signal remains:

- advisory
- pre-risk
- not a recommendation
- not a trade instruction
- not risk approval
- not execution-ready
- not portfolio-aware
- not broker-aware

Validated research may support a deterministic advisory evaluation boundary.
It must not authorize signal-to-risk conversion, execution intent creation,
portfolio mutation, broker behavior, order submission, runtime scheduling,
live data ingestion, ML inference, or LLM trading-path logic.

## 11. Review Checklist

Future reviewers can use this checklist when reviewing a candidate
`ValidatedResearchArtifact`.

- [ ] Provenance: artifact id, version, author/source, date, and review
  reference are clear.
- [ ] Reproducibility: regeneration path, required inputs, code/notebook/script,
  data version, output stability, and randomness handling are documented.
- [ ] Dataset scope: dataset source, window, universe, timeframe/bar size, and
  sample size limitations are documented.
- [ ] Data quality: cleaning assumptions, missing-data handling, stale
  observations, corporate actions, timezone/session handling, and resampling
  rules are documented where applicable.
- [ ] Bias controls: point-in-time correctness, no future data in indicators,
  no future data in labels, no leakage through feature construction,
  survivorship bias, and delisting bias are addressed.
- [ ] Input definition: required inputs, input names, input types, source data,
  and timestamp assumptions are explicit.
- [ ] Threshold rationale: threshold value, comparator, source, and reason for
  choosing the threshold are documented.
- [ ] Metric definitions: all reported metrics are defined without implying
  unsupported profitability, ranking, confidence, or probability semantics.
- [ ] Statistical claim type: the artifact classifies its claim as mechanical
  transformation, threshold sanity check, regime indicator, predictive
  relationship, risk filter, profitability claim, robustness claim, or another
  explicitly scoped category.
- [ ] Assumptions: all required market, data, indicator, threshold, and
  evaluation assumptions are listed.
- [ ] Limitations: known gaps, invalid conditions, sample constraints, and
  unresolved questions are listed.
- [ ] Non-claims: the artifact states what it does not prove, including that it
  is not a trade recommendation, risk approval, execution readiness, live
  trading claim, broker-aware claim, or portfolio-aware claim.
- [ ] Signal-definition binding: signal id/version, artifact id/version,
  required input names, input types, indicator semantics, threshold semantics,
  comparator semantics, assumptions, and limitations match.
- [ ] No-lookahead evidence: timestamp handling and feature/label construction
  demonstrate no future information was used.
- [ ] Deterministic suitability: the artifact can support offline,
  credential-free, deterministic normal pytest semantics if implementation is
  later approved.
- [ ] Advisory-only confirmation: the artifact keeps evaluator output advisory,
  pre-risk, not actionable, and outside execution, broker, portfolio, runtime,
  ML, and LLM trading-path behavior.
- [ ] Implementation blockers: unresolved gaps are listed before any
  implementation scope is considered.

Unchecked items should be treated as review findings. A future reviewer should
not fill gaps by inference when evaluator implementation depends on them.

## 12. Pass/Fail Guidance

Possible review outcomes:

- pass: the artifact can support a later validated signal-definition review,
  subject to the artifact's stated assumptions and limitations.
- conditional pass: specific gaps must be resolved before the artifact can
  support a validated signal-definition review or implementation planning.
- fail: the artifact cannot support evaluator implementation.
- informational only: the artifact may inform research direction but cannot
  support production code, a production threshold, or evaluator implementation.

A pass is not implementation approval. It only means the artifact is suitable
to be considered during a later validated signal-definition review.

## 13. Relationship To Existing Contracts

`ValidatedResearchArtifact` is the evidence boundary. This standard defines
the minimum documentation expected before an artifact can be treated as
validated research for evaluator-support purposes.

`ValidatedSignalDefinition` is the promoted signal metadata boundary. This
standard requires exact binding between a signal definition and the artifact
that supports it before any real evaluator implementation can be considered.

`SignalEvaluationInputSnapshot` records the explicit required input names and
`as_of` timestamp for future evaluator traceability. The evidence standard
requires artifact and signal-definition semantics to match those required
inputs before evaluator code is added.

`SignalInputValue` carries explicit observed scalar values. This standard does
not permit an evaluator to compute, fetch, infer, normalize, rank, score, or
transform missing inputs.

`SignalInputBundle` groups explicit values and preserves bundle-level
lookahead checks. The evidence standard requires future evaluator use to stay
within explicit input values and documented `as_of` semantics.

`SignalInputBundleCompletenessResult` and
`validate_signal_input_bundle_completeness(...)` remain the name-only
completeness boundary. Research validation does not relax missing-input,
extra-input, snapshot, or timestamp rules.

`SignalEvaluationResult` remains advisory output only. Research validation
does not add score, rank, confidence, probability, direction, actionability,
risk, execution, broker, portfolio, order, or runtime fields.

The Phase 29 threshold evaluator constants and output semantics remain design
semantics only. Placeholder constants and test thresholds are non-production
until tied to an exact validated research artifact and exact validated signal
definition.

Future evaluator implementation gates remain blocked until validated research,
validated signal-definition support, threshold/config provenance, explicit
scope approval, and implementation tests are all ready.

## 14. Explicitly Out Of Scope

Phase 30 Step 2 does not add:

- actual research artifact
- validated signal definition
- evaluator implementation
- evaluator protocol changes
- signal computation
- feature computation
- strategy logic
- score, direction, confidence, or actionability
- ranking or probability
- risk approval
- execution intent creation
- signal-to-risk conversion
- broker or Alpaca behavior
- order submission
- runtime or scheduler behavior
- persistence
- live data ingestion
- ML or LLM trading-path behavior

Normal pytest must remain offline, credential-free, and safe.

## 15. Non-Binding Future Phase Sketch

Possible future phases include:

1. Phase 30 Step 3: candidate `ValidatedResearchArtifact` review against this
   standard, docs-only.
2. Phase 30 Step 4: candidate `ValidatedSignalDefinition` review and artifact
   binding, docs-only.
3. Phase 30 Step 5: implementation scope approval review.
4. Later: minimal threshold evaluator implementation only if all blockers are
   resolved.

This sketch is non-binding. Any future work must remain contract-first,
test-first, deterministic, offline-safe, credential-free, broker-isolated,
advisory, pre-risk, and outside the LLM trading hot path.
