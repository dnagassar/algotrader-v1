# Phase 30 Threshold Evaluator Research Support Boundary Design

## 1. Purpose

Phase 30 Step 1 defines the research-support boundary for the future
threshold-style advisory evaluator.

This phase adds no evaluator implementation, no signal computation, and no
production behavior changes. The goal is to define the research evidence and
validated signal-definition metadata that must exist before any implementation
phase may add threshold evaluator behavior.

This boundary keeps the future evaluator blocked until the project can point to
specific validated evidence. Input contracts, drafted constants, documented
test semantics, and a simple evaluator shape are not enough by themselves to
promote evaluator code.

Phase 30 Step 2 defines the reusable research validation evidence standard in
[`phase30_research_validation_evidence_standard.md`](phase30_research_validation_evidence_standard.md)
before any candidate artifact is reviewed. Candidate artifacts must be measured
against that fixed standard instead of shaping the standard after the fact.
Implementation remains blocked.

## 2. Why Research Support Is Required

A threshold evaluator should not enter production code simply because:

- the input contracts exist
- constants were drafted
- test semantics were documented
- the evaluator shape is simple

Even a minimal threshold comparison can encode a trading assumption. A real
evaluator therefore needs validated research evidence and a validated signal
definition before implementation. The future threshold must be traceable to
reviewed evidence, and the resulting signal metadata must preserve advisory
semantics without implying trade actionability.

## 3. Required Future Research Artifact

A future implementation must identify an exact `ValidatedResearchArtifact`.
That artifact must provide or trace to:

- artifact id
- artifact version
- research scope
- dataset or sample description
- input definition
- threshold rationale
- metric definitions
- assumptions
- limitations
- validation date or as-of metadata if supported by the contract
- evidence that the threshold is not arbitrary
- evidence that the signal remains advisory and not trade-actionable by itself

This phase does not invent the artifact, add research results, or promote
research that is not already present in the repository.

## 4. Required Future Signal Definition

A future implementation must identify an exact `ValidatedSignalDefinition`.
That definition must provide or trace to:

- signal id
- signal version
- source artifact id and version
- required input name: `indicator_value`, unless a later design changes it
- expected input type: `Decimal`
- advisory output semantics
- assumptions
- limitations
- no broker, order, runtime, or portfolio semantics
- no actionability semantics

This phase does not create a new signal definition.

## 5. Threshold Value And Source Requirements

The future production threshold must be tied to validated research. The
threshold must not come from:

- live runtime state
- environment variables
- broker or account state
- portfolio state
- LLM output
- ML inference
- ad hoc manual tuning inside the evaluator
- hidden files or persistence reads

Acceptable future threshold sources may include:

- explicit evaluator configuration produced from a reviewed design phase
- evaluator-local constant only if tied to a validated research artifact
- test-only placeholder such as `Decimal("1")`, clearly isolated from
  production semantics

`Decimal("1")` remains a harmless test placeholder only. It is not a validated
production threshold and must not be treated as trading evidence.

## 6. Research Acceptance Criteria

Before implementation, research support should answer:

- what the input represents
- why `Decimal` is appropriate
- why the threshold is chosen
- what comparator is justified
- what conditions make the threshold invalid
- what assumptions are required
- what limitations apply
- what data leakage and lookahead risks were checked
- what the output means
- what the output does not mean
- why the output remains advisory and pre-risk

The accepted research must make the evaluator easier to audit, not more
actionable. Any unresolved research question keeps implementation blocked.

## 7. Non-Actionability Rule

Even research-supported evaluator output remains:

- advisory
- pre-risk
- not a recommendation
- not a trade instruction
- not risk approval
- not execution-ready
- not portfolio-aware
- not broker-aware

The research artifact and signal definition must not authorize trading
behavior. They may only support a deterministic advisory evaluation boundary
that remains upstream of risk, execution planning, portfolios, brokers, orders,
runtime wiring, persistence, ML, and LLM trading-path logic.

## 8. Required Test Implications

A future implementation must be able to test:

- exact research artifact id and version traceability
- exact signal definition id and version traceability
- exact threshold source
- exact threshold value
- exact comparator
- exact required input name
- exact accepted input type
- deterministic repeated outputs
- no-lookahead behavior
- missing input behavior
- extra input behavior
- snapshot id equality
- `as_of` equality
- `evaluated_at >= as_of`
- no forbidden output fields
- no side effects or trading-path dependencies

These tests must run in normal pytest without credentials, network access,
broker accounts, paper-trading opt-ins, model services, or LLM clients.

## 9. Relationship To Existing Contracts

`ValidatedResearchArtifact` remains the evidence boundary. It records reviewed
research metadata and must support the future threshold without becoming signal
generation, risk approval, or trading behavior.

`ValidatedSignalDefinition` remains the promoted signal metadata boundary. It
must identify the signal id/version, source artifact id/version, required input
name, expected value type, advisory semantics, assumptions, and limitations
without adding broker, portfolio, runtime, order, execution, risk, or
actionability semantics.

`SignalEvaluationInputSnapshot` identifies required input names and the
snapshot `as_of` for future evaluator traceability. The threshold evaluator
boundary currently expects `indicator_value` unless a later design changes it.

`SignalInputValue` carries one explicit observed scalar input. The future
threshold-style evaluator may accept a `Decimal` value for `indicator_value`,
but it must not compute that value, fetch it, normalize it, or infer it.

`SignalInputBundle` groups explicit input values and enforces bundle-level
lookahead validation with `observed_at <= bundle.as_of`. The future evaluator
must read only the exact required input and ignore extras.

`SignalInputBundleCompletenessResult` and
`validate_signal_input_bundle_completeness(...)` provide the name-only
completeness boundary that should be satisfied before evaluator use.

`SignalEvaluationResult` remains the advisory output contract. Threshold
output values and reason codes must use existing fields only and must not add
score, rank, confidence, probability, direction, actionability, risk,
execution, broker, portfolio, or order fields.

The Phase 29 Step 6 threshold constants and output semantics define candidate
local names, values, reason codes, comparator, and timestamp compatibility.
Those semantics do not authorize implementation until this research-support
boundary is satisfied.

Deterministic time contracts remain required. A future implementation must use
explicit UTC-aware `as_of` and `evaluated_at` values, preserve strict
compatibility rules, and avoid hidden wall-clock access.

## 10. Explicit Blockers After This Phase

Implementation remains blocked until:

- exact validated research artifact exists
- exact validated signal definition exists
- threshold value and source are justified by that artifact
- implementation scope is explicitly approved
- required tests are written or ready to be written

The threshold-style advisory evaluator remains viable but unimplemented.

## 11. Explicitly Out Of Scope

Phase 30 Step 1 does not add:

- validated research artifact implementation
- validated signal definition implementation
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

## 12. Non-Binding Future Phase Sketch

Possible future phases based on this boundary include:

1. Phase 30 Step 2: research validation evidence standard, docs-only.
2. Phase 30 Step 3: threshold evaluator research artifact candidate review,
   docs-only.
3. Phase 30 Step 4: validated signal definition candidate review, docs-only or
   tests/docs only.
4. Phase 30 Step 5: implementation readiness re-check.
5. Later: minimal threshold evaluator implementation only if all blockers are
   resolved.

This sketch is non-binding. Any future work must remain contract-first,
test-first, deterministic, offline-safe, credential-free, broker-isolated,
advisory, pre-risk, and outside the LLM trading hot path.
