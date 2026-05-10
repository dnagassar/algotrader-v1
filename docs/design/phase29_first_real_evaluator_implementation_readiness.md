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
| final required input name | Unresolved | `indicator_value` is still a placeholder. |
| final accepted value type | Unresolved | `Decimal` is preferred, but not final. |
| final threshold source | Blocked | The exact threshold value and source are not documented. |
| final comparator | Unresolved | `>=` is possible, but not final. |
| final `output_value` representation | Blocked | Textual, boolean-like, or other representation is undecided. |
| final `reason_code` values | Blocked | Deterministic reason-code names are not defined. |
| final diagnostics/assumptions/limitations | Unresolved | Required content is not finalized. |
| missing-input behavior | Unresolved | Raise, advisory failure, or precondition-only behavior is not fixed. |
| extra-input behavior | Unresolved | Ignore, reject, or report-only behavior is not fixed. |
| snapshot id compatibility | Unresolved | Exact equality or another rule is not fixed. |
| snapshot `as_of` compatibility | Unresolved | Exact timestamp compatibility is not fixed. |
| bundle `as_of` compatibility | Unresolved | Exact timestamp compatibility is not fixed. |
| completeness result flow | Unresolved | Prevalidated input versus internal validation is not fixed. |
| no-lookahead policy | Ready | Core policy is defined, but exact compatibility rules above remain unresolved. |
| forbidden output fields | Ready | Step 4 matrix explicitly forbids trading-path fields. |
| side-effect/dependency tests | Ready | Step 4 matrix defines the required dependency-isolation tests. |
| mutation tests | Ready | Step 4 matrix defines non-mutation coverage for all inputs and output. |
| deterministic repeated-output tests | Ready | Step 4 matrix defines repeated-call determinism coverage. |

The ready items are ready as requirements. They do not mean implementation is
ready, because several implementation-blocking constants and semantics are
still unresolved.

## 4. Recommended Readiness Decision

Recommendation: Option C.

A small additional design phase is needed to lock constants and output
semantics before implementation. Implementation is not ready for a narrowly
scoped Phase 29 Step 6 yet because the exact `ValidatedSignalDefinition`, exact
`ValidatedResearchArtifact`, threshold value source, and output semantics remain
unresolved.

Option A is rejected for now because production evaluator code would need to
invent unresolved constants or semantics during implementation. Option B is too
strong because the candidate itself remains viable; it needs one more
design-only narrowing step rather than abandonment.

## 5. Items That Must Be Fixed Before Implementation

Before production evaluator code begins, a later design phase must resolve:

- exact validated signal definition identity and version
- exact validated research artifact identity and version
- exact input name
- exact threshold value and source
- exact comparator
- exact output representation
- exact reason codes
- exact missing and extra input policy
- exact snapshot and `as_of` compatibility rules
- exact completeness flow

These decisions must be documented before implementation tests or production
evaluator code are added.

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

## 7. Conditions For Phase 29 Step 6

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

1. Phase 29 Step 6A: final threshold evaluator constants/output semantics
   design, docs-only.
2. Phase 29 Step 6B: minimal threshold evaluator implementation, only if
   readiness is confirmed.
3. Phase 29 Step 7: threshold evaluator traceability/no-lookahead hardening.

This sketch is non-binding. Any future work must remain contract-first,
test-first, deterministic, offline-safe, credential-free, broker-isolated,
advisory, pre-risk, and outside the LLM trading hot path.
