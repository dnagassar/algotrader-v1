# Phase 29 First Real Evaluator Implementation Readiness Review

## 1. Purpose

Phase 29 Step 5 is a documentation-only implementation-readiness review for
the future threshold-style advisory evaluator.

This phase adds no evaluator implementation, no signal computation, and no
production behavior changes. The goal is to decide whether the future
threshold-style evaluator is ready for implementation, blocked, or needs
another design step before production evaluator code is allowed.

The review is intentionally conservative. If exact constants, trace identities,
input policy, or output semantics are unresolved, implementation must wait.

Phase 29 Step 6 resolves or explicitly defers constants and output semantics in
[`docs/design/phase29_threshold_evaluator_constants_output_semantics.md`](phase29_threshold_evaluator_constants_output_semantics.md).
That design narrows evaluator-local constants and advisory output semantics,
but implementation is still not ready unless validated signal and research
support are also available.

Phase 30 Step 1 defines the research-support boundary for those remaining
blockers in
[`docs/design/phase30_threshold_evaluator_research_support_boundary.md`](phase30_threshold_evaluator_research_support_boundary.md).
It does not authorize implementation; it clarifies the evidence and
signal-definition metadata required before implementation can be considered.

## 2. Current Candidate Recap

The selected future candidate remains:

- threshold-style advisory evaluator
- one explicit scalar input
- placeholder input name: `indicator_value`
- preferred input type: `Decimal`
- possible comparator: `>=`
- explicit deterministic threshold
- advisory `SignalEvaluationResult`
- no trade direction
- no confidence or probability
- no ranking
- no actionability
- no risk approval
- no execution behavior

The candidate is still advisory and pre-risk only. It must not create trade
recommendations, execution intents, risk approvals, orders, broker payloads, or
portfolio decisions.

## 3. Readiness Checklist

| Item | Status | Review |
| --- | --- | --- |
| exact `ValidatedSignalDefinition` | Blocked | The definition identity and version are not selected. |
| exact supporting `ValidatedResearchArtifact` | Blocked | The supporting artifact identity and version are not selected. |
| final required input name | Ready as design | Step 6 selects `indicator_value`. |
| final accepted value type | Ready as design | Step 6 selects `Decimal` only. |
| final threshold source | Ready as design | Step 6 requires explicit evaluator configuration or evaluator-local constant only. |
| final comparator | Ready as design | Step 6 selects `>=`. |
| final `output_value` representation | Ready as design | Step 6 selects textual advisory values. |
| final `reason_code` values | Ready as design | Step 6 names deterministic threshold reason codes. |
| final diagnostics/assumptions/limitations | Ready as design | Step 6 defines deterministic metadata expectations. |
| missing-input behavior | Ready as design | Step 6 requires pre-call completeness and deterministic rejection if missing input reaches the evaluator. |
| extra-input behavior | Ready as design | Step 6 allows non-blocking extras but requires output invariance and exact-name reads only. |
| snapshot id compatibility | Ready as design | Step 6 recommends strict snapshot id equality. |
| snapshot `as_of` compatibility | Ready as design | Step 6 recommends evaluator `as_of == snapshot.as_of`. |
| bundle `as_of` compatibility | Ready as design | Step 6 recommends evaluator `as_of == bundle.as_of`. |
| completeness result flow | Ready as design | Step 6 requires explicit pre-use completeness validation and deterministic rejection of incomplete input. |
| no-lookahead policy | Ready as design | Step 6 defines strict timestamp compatibility and keeps wall-clock access forbidden. |
| forbidden output fields | Ready | Step 4 matrix explicitly forbids trading-path fields. |
| side-effect/dependency tests | Ready | Step 4 matrix defines the required dependency-isolation tests. |
| mutation tests | Ready | Step 4 matrix defines non-mutation coverage for all inputs and output. |
| deterministic repeated-output tests | Ready | Step 4 matrix defines repeated-call determinism coverage. |

The ready items are ready as design requirements. They do not mean
implementation is ready, because exact validated signal and research artifacts
remain unresolved.

## 4. Recommended Readiness Decision

Original Step 5 recommendation: Option C.

At Step 5 time, a small additional design phase was needed to lock constants
and output semantics before implementation. Implementation was not ready for a
narrowly scoped implementation phase because the exact
`ValidatedSignalDefinition`, exact `ValidatedResearchArtifact`, threshold value
source, and output semantics were unresolved.

Option A was rejected because production evaluator code would have needed to
invent unresolved constants or semantics during implementation. Option B was
too strong at Step 5 time because the candidate itself remained viable and
needed one more design-only narrowing step rather than abandonment.

Step 6 update: Option B.

Phase 29 Step 6 resolves safe evaluator-local constants and output semantics,
but implementation remains blocked because exact validated signal and research
artifacts are still missing. The candidate remains viable and selected, but
production evaluator code must not begin until validated support is available.

## 5. Items That Must Be Fixed Before Implementation

Before production evaluator code begins, a later design phase must still
resolve:

- exact validated signal definition identity and version
- exact validated research artifact identity and version
- validated production threshold value and source, if `Decimal("1")` remains
  only a harmless unit-test placeholder
- explicit tie between the validated artifacts and threshold semantics

These decisions must be documented before production evaluator code is added.
Phase 30 Step 1 narrows the research and validated signal-definition evidence
expected for these unresolved items, but the exact artifacts and production
threshold remain absent.

## 6. Safe Minimal Implementation Shape, If Later Allowed

If a later phase allows implementation, the safe shape should be conceptualized
as:

- one small module
- one frozen/slotted evaluator class or one pure function
- explicit inputs only
- no runtime wiring
- no registry
- no scheduler
- no broker
- no persistence
- no live data
- no ML or LLM calls
- focused unit tests first

The future implementation should consume already-built deterministic contracts
and return advisory metadata only. This phase does not implement that shape.

## 7. Conditions For A Future Implementation Phase

If a later implementation phase is allowed, it must explicitly define:

- allowed files
- forbidden behavior
- required tests
- exact expected result semantics
- exact verification commands
- confirmation that normal pytest remains offline and credential-free

The implementation phase must not draft production behavior beyond those
approved boundaries. It must not add runtime wiring, registries, broker paths,
persistence, live data access, ML calls, LLM calls, risk approval, execution
intent creation, or order behavior.

## 8. Explicitly Out Of Scope

Phase 29 Step 5 does not add:

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

## 9. Non-Binding Future Phase Sketch

Possible future phases based on this readiness review include:

1. Phase 29 Step 7: final implementation prompt/test scaffold design,
   docs-only.
2. Phase 29 Step 8: minimal threshold evaluator implementation, only if
   validated signal/research artifacts and semantics are ready.
3. Phase 29 Step 9: threshold evaluator traceability/no-lookahead hardening.

This sketch is non-binding. Any future work must remain contract-first,
test-first, deterministic, offline-safe, credential-free, broker-isolated,
advisory, pre-risk, and outside the LLM trading hot path.
