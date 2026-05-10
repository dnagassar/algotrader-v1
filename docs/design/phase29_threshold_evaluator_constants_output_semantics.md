# Phase 29 Threshold Evaluator Constants And Output Semantics Design

## 1. Purpose

Phase 29 Step 6 is constants and output semantics design only for the future
threshold-style advisory evaluator.

This phase adds no evaluator implementation, no signal computation, and no
production behavior changes. The goal is to lock down the safest minimal
semantics before any later implementation phase is considered.

This design narrows evaluator-local constants and advisory result semantics. It
does not invent production research evidence, promote a strategy, or authorize
production evaluator code.

## 2. Candidate Recap

The future evaluator remains:

- threshold-style advisory evaluator
- one explicit scalar `SignalInputValue`
- preferred value type: `Decimal`
- comparator candidate: `>=`
- explicit deterministic threshold
- output through advisory `SignalEvaluationResult`
- no trade direction
- no confidence or probability
- no ranking
- no actionability
- no risk approval
- no execution behavior

The evaluator may only describe whether one explicit scalar satisfies one
documented advisory threshold condition. It must not produce a recommendation,
trade instruction, risk approval, execution intent, order request, broker
payload, or portfolio decision.

## 3. Constants To Resolve

Recommended future evaluator constants:

| Constant | Decision |
| --- | --- |
| required input name | `indicator_value` |
| accepted value type | `Decimal` only |
| comparator | `>=` |
| threshold source | explicit evaluator configuration or evaluator-local constant only |
| threshold value | `Decimal("1")` as a harmless future unit-test placeholder only |
| condition met reason code | `THRESHOLD_CONDITION_MET` |
| condition not met reason code | `THRESHOLD_CONDITION_NOT_MET` |
| missing input reason code | `THRESHOLD_INPUT_MISSING` |
| invalid input type reason code | `THRESHOLD_INPUT_INVALID_TYPE` |

The threshold source must not be live data, runtime state, broker state,
portfolio state, environment variables, current wall-clock time, persistence,
ML output, or LLM output.

`Decimal("1")` is not a trading strategy, not a research-supported signal
threshold, and not a production recommendation. It is a harmless deterministic
placeholder suitable only for future unit tests if no validated strategy
threshold has been promoted yet. A production threshold remains blocked until
it is tied to an exact validated signal definition and supporting research
artifact.

## 4. Output Value Semantics

`SignalEvaluationResult` must not change.

Possible `output_value` representations considered:

- textual advisory state
- boolean-like result
- `Decimal` result
- structured metadata encoded through existing fields

Recommended future `output_value` values:

- `threshold_condition_met`
- `threshold_condition_not_met`

These textual values are safer than booleans or numbers because they avoid
looking like scores, confidence, ranking, direction, or actionability. They are
still advisory only. They do not mean buy, sell, long, short, bullish, bearish,
recommended, approved, risk-approved, execution-ready, or broker-ready.

Missing or invalid input should be rejected deterministically before a normal
advisory result is produced. If a future implementation chooses to return an
advisory failure result instead, that behavior must be explicitly scoped and
tested before production code.

## 5. Diagnostics, Assumptions, And Limitations

Future diagnostics should be deterministic and testable. They should identify:

- required input name: `indicator_value`
- accepted value type: `Decimal`
- comparator: `>=`
- threshold source: explicit evaluator configuration or evaluator-local
  constant
- threshold value used by the test or configured evaluator

Future assumptions should state:

- the input value was precomputed before evaluation
- the input value was supplied explicitly
- the input bundle was checked for completeness before evaluator use
- timestamps were explicit and UTC-aware
- the input was available at or before evaluator `as_of`

Future limitations should state:

- no feature computation occurred
- no ranking occurred
- no direction was inferred
- no recommendation was made
- no risk approval occurred
- no execution behavior occurred
- no broker, portfolio, runtime, persistence, ML, or LLM behavior occurred

The exact strings should be stable enough for deterministic tests.

## 6. Missing Input Policy

Recommended policy:

- completeness validation is required before evaluator use
- missing `indicator_value` is an invalid precondition
- if incomplete input reaches the evaluator anyway, reject deterministically
- do not infer missing inputs
- do not substitute defaults
- do not fetch missing inputs

`THRESHOLD_INPUT_MISSING` is reserved as the deterministic reason code or error
code for this failure path. The future implementation must decide whether this
appears in an exception, validation result, or advisory failure result before
code is added.

## 7. Extra Input Policy

Recommended policy:

- extra inputs may be present because current completeness validation reports
  them as non-blocking
- the evaluator must read only `indicator_value` by exact name
- extras must not affect output
- extras must not be interpreted
- extras must not be normalized, ranked, scored, or converted into features

Future tests must prove output invariance when an extra input is present.

## 8. Snapshot Id Compatibility

Recommended first implementation policy:

- require `snapshot.snapshot_id == bundle.snapshot_id`
- preserve the exact snapshot id in the result input fingerprint or reference
  field
- reject mismatch deterministically

Strict equality is the safest first rule because it is easy to audit and avoids
ambiguous input provenance. A looser compatibility rule would require another
design phase.

## 9. As-Of Compatibility

Recommended first implementation policy:

- require evaluator `as_of == snapshot.as_of`
- require evaluator `as_of == bundle.as_of`
- rely on `SignalInputBundle` to enforce every value
  `observed_at <= bundle.as_of`
- require `evaluated_at >= as_of`
- require both `as_of` and `evaluated_at` to be UTC-aware

The evaluator must not call wall-clock APIs, fetch newer data, or use runtime
state to resolve timestamp ambiguity.

## 10. Completeness Flow

Recommended flow:

- caller performs `validate_signal_input_bundle_completeness(...)` before
  evaluator use
- the future evaluator-specific implementation makes this precondition explicit
- incomplete results are rejected deterministically
- extras remain non-blocking but ignored by the evaluator
- hidden validation ambiguity is avoided

The future implementation may either receive a precomputed
`SignalInputBundleCompletenessResult` or use an explicit wrapper that validates
immediately before evaluation. The chosen call shape must be documented before
code is added. This phase does not implement that flow.

## 11. Validated Signal And Research Artifacts

Exact `ValidatedSignalDefinition` and `ValidatedResearchArtifact` identities
are not available in this phase.

Implementation remains blocked until the project defines:

- exact validated signal definition identity
- exact validated signal definition version
- exact supporting research artifact identity
- exact supporting research artifact version
- evidence that the threshold is supported by the validated artifact

This phase must not invent production research evidence and must not promote an
unsupported strategy into code.

## 12. Updated Readiness Decision

Recommendation: Option B.

The evaluator remains blocked for implementation because exact validated
signal and research artifacts are missing. Step 6 resolves safe local constants,
recommended output semantics, and compatibility policies, but it does not
provide the validated research support required for production evaluator code.

The candidate remains viable and selected. A later docs/tests planning phase
may prepare the implementation prompt or test scaffold, but production
implementation should not begin until validated signal and research artifacts
are available and explicitly tied to the threshold semantics.

## 13. Required Future Tests

Future implementation tests must cover:

- exact input name `indicator_value`
- exact `Decimal` value type acceptance
- unsupported value type rejection
- `Decimal("1")` placeholder threshold behavior if used for tests
- `>=` threshold comparison below, equal, and above threshold
- `threshold_condition_met` output value
- `threshold_condition_not_met` output value
- `THRESHOLD_CONDITION_MET` reason code
- `THRESHOLD_CONDITION_NOT_MET` reason code
- `THRESHOLD_INPUT_MISSING` failure behavior
- `THRESHOLD_INPUT_INVALID_TYPE` failure behavior
- missing input behavior
- extra input invariance
- snapshot id mismatch behavior
- evaluator `as_of` versus snapshot `as_of` mismatch behavior
- evaluator `as_of` versus bundle `as_of` mismatch behavior
- `evaluated_at >= as_of`
- no-lookahead behavior
- traceability preservation
- deterministic repeated output
- forbidden output fields
- no side effects or dependency violations
- no input mutation

These tests must run in normal pytest without credentials, network access,
broker accounts, paper trading opt-ins, model services, or LLM clients.

## 14. Explicitly Out Of Scope

Phase 29 Step 6 does not add:

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

## 15. Non-Binding Future Phase Sketch

Possible future phases based on this design include:

1. Phase 29 Step 7: final implementation prompt/test scaffold design,
   docs-only.
2. Phase 29 Step 8: minimal threshold evaluator implementation, only if
   validated signal/research artifacts and semantics are ready.
3. Phase 29 Step 9: threshold evaluator traceability/no-lookahead hardening.

This sketch is non-binding. Any future work must remain contract-first,
test-first, deterministic, offline-safe, credential-free, broker-isolated,
advisory, pre-risk, and outside the LLM trading hot path.
