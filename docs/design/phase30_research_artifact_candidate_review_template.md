# Phase 30 Research Artifact Candidate Review Template

## 1. Purpose

Phase 30 Step 3 defines a candidate research artifact review template and
intake boundary. The template gives future reviewers a consistent structure
for applying the Phase 30 Step 2 evidence standard to a candidate
`ValidatedResearchArtifact`.

This phase creates no actual research artifact, approves no artifact, creates
no validated signal definition, implements no evaluator, and adds no signal
computation. The goal is to make future artifact review consistent,
auditable, and independent of any convenient candidate.

Phase 30 Step 4 defines how future candidates are sourced before review in
[`phase30_research_artifact_candidate_sourcing_plan.md`](phase30_research_artifact_candidate_sourcing_plan.md).
This template is applied only after a candidate artifact exists. Sourcing a
candidate does not validate it, approve it, or authorize evaluator
implementation.

The template is documentation-only. It does not make any evaluator output
actionable, production-ready, risk-approved, execution-ready, portfolio-aware,
or broker-aware.

## 2. Why A Template Is Needed

Future research artifacts must be measured against the Phase 30 Step 2
evidence standard, not judged ad hoc. Without a fixed intake shape, reviewers
could accidentally reverse-engineer the evidence bar from whatever a candidate
already contains.

The template is intended to prevent:

- reverse-engineering the evidence bar from a convenient candidate
- accepting vibes-based thresholds
- accepting unclear datasets
- accepting non-reproducible analysis
- accepting hidden lookahead
- accepting advisory outputs as trading instructions

The template should be filled out only when a real candidate artifact exists.
An empty or partially filled template is not a validated artifact and does not
authorize implementation.

## 3. Candidate Artifact Intake Fields

A future candidate review must capture the following intake fields before any
pass/fail decision is made:

- candidate artifact title
- proposed artifact id
- proposed artifact version
- author, source, or provenance
- creation or review date
- repo commit or reproducibility reference, if available
- research question
- supported signal candidate
- supported evaluator candidate, if any
- dataset or source description
- dataset window
- asset universe
- timeframe or bar size
- input definitions
- threshold or config candidates
- metric definitions
- assumptions
- limitations
- non-claims
- reviewer name and date, if applicable

If a required field is unknown, the review should record it as missing rather
than filling it by inference.

## 4. Evidence Checklist Mapping

The future review checklist maps directly to the Phase 30 Step 2 evidence
standard.

- [ ] Provenance: candidate title, artifact id/version, author/source,
  creation or review date, and review reference are documented.
- [ ] Reproducibility: required inputs, regeneration path, code/notebook/script,
  data version, output stability, and randomness handling are documented.
- [ ] Dataset scope: source, dataset window, asset universe, timeframe/bar
  size, and sample size limitations are documented.
- [ ] Data quality: data cleaning, missing observations, stale observations,
  corporate actions, timezone/session handling, and resampling rules are
  documented where applicable.
- [ ] Bias controls: point-in-time correctness, survivorship bias, delisting
  bias, no future data in indicators, no future data in labels, and no feature
  leakage are addressed.
- [ ] Input definition: input names, value types, source data, timestamp
  assumptions, and indicator inputs are explicit.
- [ ] Threshold rationale: proposed threshold/config values, comparator,
  source, rationale, and evidence are documented.
- [ ] Metric definitions: every metric is defined and does not imply
  unsupported score, rank, confidence, probability, direction, actionability,
  risk, execution, broker, or portfolio semantics.
- [ ] Statistical claim type: the supported claim category is explicitly
  selected and scoped.
- [ ] Assumptions: market, data, indicator, threshold, evaluation, and
  operational assumptions are listed.
- [ ] Limitations: known gaps, invalid conditions, sample constraints, and
  unresolved questions are listed.
- [ ] Non-claims: the candidate states what it does not prove, including that
  it is not a trade recommendation, risk approval, live-trading claim,
  execution readiness, broker-aware claim, or portfolio-aware claim.
- [ ] Signal-definition binding: signal id/version candidate, artifact
  id/version, input names, input types, indicator semantics, threshold
  semantics, comparator semantics, assumptions, and limitations match.
- [ ] No-lookahead evidence: timestamp handling and feature/label construction
  demonstrate that future information was not used.
- [ ] Deterministic suitability: the artifact can support offline,
  credential-free, deterministic normal pytest semantics if implementation is
  later approved.
- [ ] Advisory-only confirmation: any supported evaluator output remains
  advisory, pre-risk, not actionable, and outside execution, broker,
  portfolio, runtime, ML, and LLM trading-path behavior.
- [ ] Implementation blockers: all unresolved gaps are listed before any
  implementation scope is considered.

Unchecked items should become explicit review findings or blockers. A future
review should not treat absence of evidence as acceptance.

## 5. Required Pass/Fail Assessment

Each future candidate review must end with one of these outcomes:

- pass: artifact may support a later validated signal definition review.
- conditional pass: specific gaps must be resolved.
- fail: artifact cannot support evaluator implementation.
- informational only: artifact may inform research but cannot support
  production code.

A pass does not authorize evaluator implementation by itself. It only means
the artifact may proceed to a later `ValidatedSignalDefinition` review and
artifact-binding review.

## 6. Claim Classification

Reviewers must classify the artifact's claim as one or more of:

- mechanical transformation only
- threshold sanity check
- regime indicator
- predictive relationship
- risk filter
- profitability claim
- robustness claim

Stronger claims require stronger evidence. Predictive, profitability,
risk-filter, and robustness claims require more validation than a mechanical
transformation or threshold sanity check. The review must state whether any
threshold is merely a deterministic advisory condition or whether it claims
predictive or profitability value.

## 7. Non-Claims

Every candidate review must explicitly state what the artifact does not prove.
Expected non-claims include:

- not a profitability guarantee
- not a risk-adjusted return claim unless separately validated
- not a live-trading claim
- not a trade recommendation
- not risk approval
- not execution readiness
- not portfolio-aware
- not broker-aware

Missing non-claims should block implementation planning until corrected.

## 8. Signal-Definition Binding

The review must document whether the candidate artifact can bind to a future
`ValidatedSignalDefinition`.

The review should check:

- signal id/version candidate
- required input names
- input value types
- indicator semantics
- threshold and comparator semantics
- assumptions and limitations
- whether the artifact evidence supports this exact signal definition or only
  a related idea

If the artifact only supports a related idea, the outcome should be
conditional pass, fail, or informational only, depending on the gap. Loose
conceptual similarity is not enough to support evaluator implementation.

## 9. Threshold And Config Provenance

The review must document any proposed threshold or config values and the
evidence supporting them.

Threshold/config values must not come from:

- ad hoc manual tuning inside evaluator code
- runtime state
- environment variables
- broker or account state
- portfolio state
- hidden config files
- LLM output
- ML inference

Acceptable future values must be traceable to reviewed evidence and must carry
the artifact id/version and signal id/version that justify their use. Test-only
placeholders remain isolated from production semantics.

## 10. Implementation Blockers

The review must list blockers before implementation planning. Common blockers
include:

- missing validated research artifact fields
- missing reproducibility information
- unclear dataset window
- unresolved bias controls
- unclear signal binding
- unsupported threshold value
- unclear output semantics
- missing no-lookahead evidence
- missing deterministic suitability evidence
- missing advisory-only non-claims

Any unresolved blocker prevents evaluator implementation until a later review
resolves it explicitly.

## 11. Relationship To Existing Contracts

`ValidatedResearchArtifact` remains the evidence boundary. This template is
the intake shape for reviewing a future candidate before it can be considered
validated research.

`ValidatedSignalDefinition` remains the promoted signal metadata boundary. A
candidate artifact review can only support a later signal-definition review if
the artifact binds exactly to the signal id/version, input names, input value
types, indicator semantics, threshold semantics, assumptions, and limitations.

`SignalEvaluationInputSnapshot` records explicit required input names and
`as_of` timestamps. The candidate artifact must support those input names and
timestamp assumptions before evaluator implementation can be considered.

`SignalInputValue` carries explicit observed scalar values. The template does
not allow future evaluators to compute, fetch, infer, normalize, rank, score,
or transform values.

`SignalInputBundle` groups explicit input values and preserves bundle-level
lookahead checks. Candidate review must confirm that any future evaluator can
operate only on explicit, already observed inputs.

`SignalInputBundleCompletenessResult` and
`validate_signal_input_bundle_completeness(...)` remain the name-only
completeness boundary. Candidate review does not relax missing-input,
extra-input, snapshot, or timestamp questions.

`SignalEvaluationResult` remains advisory output only. Candidate review does
not add score, rank, confidence, probability, direction, actionability, risk,
execution, broker, portfolio, order, or runtime fields.

The threshold evaluator constants and output semantics remain design
semantics only until exact research artifact and signal-definition support
exist. Placeholder thresholds remain non-production.

The Phase 30 Step 2 research validation evidence standard defines the evidence
bar. This Phase 30 Step 3 template defines how a future candidate review should
apply that bar.

Future evaluator implementation gates remain blocked until a candidate
artifact passes review, a validated signal definition binds to that artifact,
threshold/config provenance is explicit, implementation scope is approved, and
implementation tests are written or ready.

## 12. Explicitly Out Of Scope

Phase 30 Step 3 does not add:

- actual research artifact
- validated signal definition
- evaluator implementation
- evaluator protocol
- signal computation
- feature computation
- strategy logic
- score, direction, confidence, or actionability
- ranking or probability
- risk approval
- execution intent creation
- broker or Alpaca behavior
- order submission
- runtime or scheduler behavior
- persistence
- live data ingestion
- ML or LLM trading-path behavior

Normal pytest must remain offline, credential-free, and safe.

## 13. Non-Binding Future Phase Sketch

Possible future phases include:

1. Phase 30 Step 4: research artifact candidate sourcing plan and backlog
   boundary, docs-only.
2. Phase 30 Step 5: populate candidate research backlog, docs-only.
3. Phase 30 Step 6: candidate `ValidatedResearchArtifact` review using this
   template, docs-only, only when a candidate artifact exists.
4. Phase 30 Step 7: candidate `ValidatedSignalDefinition` review and artifact
   binding, docs-only.
5. Phase 30 Step 8: implementation scope approval review.
6. Later: minimal threshold evaluator implementation only if all blockers are
   resolved.

This sketch is non-binding. Any future work must remain contract-first,
test-first, deterministic, offline-safe, credential-free, broker-isolated,
advisory, pre-risk, and outside the LLM trading hot path.
