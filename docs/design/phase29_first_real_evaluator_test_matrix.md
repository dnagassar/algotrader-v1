# Phase 29 First Real Evaluator Test Matrix

## 1. Purpose

Phase 29 Step 4 is a pre-implementation test matrix for the future
threshold-style advisory evaluator.

This phase adds no evaluator implementation, no signal computation, and no
production behavior changes. It defines the future tests that must be satisfied
before any implementation phase begins.

The matrix is binding on future implementation scope. It does not authorize
production evaluator code, evaluator protocol changes, runtime wiring, or any
trading-path behavior.

## 2. Candidate Under Test

The future candidate remains:

- threshold-style advisory evaluator
- one explicit scalar input
- placeholder input name: `indicator_value`
- preferred input type: `Decimal`
- possible comparator: `>=`
- possible threshold: deterministic `Decimal`
- output: advisory `SignalEvaluationResult`
- no scoring
- no ranking
- no direction
- no actionability
- no confidence or probability

The comparator may only describe whether a supplied explicit scalar satisfies a
documented advisory condition. It must not imply buy, sell, long, short,
recommendation, approval, or execution readiness.

## 3. Required Fixture Matrix

A future implementation test suite must build explicit fixtures for:

- valid `ValidatedResearchArtifact`
- valid `ValidatedSignalDefinition`
- valid `SignalEvaluationInputSnapshot` requiring `indicator_value`
- valid `SignalInputValue(name="indicator_value", value=Decimal(...),
  observed_at=...)`
- valid `SignalInputBundle`
- valid `SignalInputBundleCompletenessResult`
- explicit UTC-aware `as_of`
- explicit UTC-aware `evaluated_at`

These fixtures must be deterministic, offline, credential-free, and free of
network, broker, persistence, runtime, ML, or LLM dependencies.

## 4. Input Validation Tests

A future implementation must test:

- valid `Decimal` input accepted
- unsupported value type rejected
- missing required input rejected or handled exactly as designed
- extra input behavior matches design
- duplicate value names remain impossible through `SignalInputBundle`
- incomplete bundle behavior is explicit
- completeness result behavior is explicit
- snapshot id compatibility behavior is explicit
- `as_of` compatibility behavior is explicit

The evaluator must not infer missing values, substitute defaults, fetch data,
compute features, normalize values, or inspect hidden state unless a later
design explicitly permits a specific behavior.

## 5. Threshold And Comparator Tests

A future implementation must test:

- value below threshold
- value equal to threshold
- value above threshold
- threshold comparison is deterministic
- `Decimal` comparison is exact
- no float coercion
- no string parsing unless explicitly designed
- no numeric normalization unless explicitly designed

These outputs must not be defined as buy, sell, long, short, bullish, bearish,
trade-ready, risk-approved, or execution-ready states.

## 6. Timestamp And No-Lookahead Tests

A future implementation must test:

- UTC-aware `as_of` accepted
- naive `as_of` rejected
- non-UTC `as_of` rejected
- UTC-aware `evaluated_at` accepted
- naive `evaluated_at` rejected
- non-UTC `evaluated_at` rejected
- `evaluated_at < as_of` rejected
- value observed after evaluator `as_of` rejected
- bundle `as_of` compatibility enforced according to design
- snapshot `as_of` compatibility enforced according to design
- no wall-clock API calls

The evaluator must rely only on explicit timestamps supplied by the caller.
It must not call current-time APIs, fetch newer data, or infer availability from
runtime state.

## 7. Traceability Tests

A future implementation must test that returned `SignalEvaluationResult`
preserves:

- signal definition id and version
- source research artifact id and version
- input snapshot id, fingerprint, or reference
- `as_of`
- `evaluated_at`
- deterministic reason code
- diagnostics
- assumptions
- limitations

Trace values must be explicit and deterministic. They must not be derived from
environment variables, wall-clock time, random state, broker state, or runtime
state.

## 8. Advisory-Only Output Tests

A future implementation must test that output:

- is advisory only
- is pre-risk
- is not a recommendation
- is not a trade approval
- is not execution-ready
- is not portfolio-aware
- is not broker-aware
- does not contain `should_trade`
- does not contain `actionable`
- does not contain `approved`
- does not contain `risk_approved`
- does not contain buy, sell, long, or short fields
- does not contain order or execution fields

The result may describe an advisory threshold condition only. It must not
create a bridge to risk, execution, portfolio, broker, or order behavior.

## 9. Determinism Tests

A future implementation must test:

- repeated calls with identical inputs produce equal results
- output ordering of diagnostics, assumptions, and limitations is deterministic
- no dependency on environment variables
- no dependency on random state
- no dependency on current wall-clock time
- no hidden input mutation

The evaluator must be a pure deterministic transformation of explicit input
contracts into advisory output metadata.

## 10. Side-Effect And Dependency Tests

A future implementation must test:

- no network or socket access
- no file, database, or cache writes
- no broker or Alpaca imports
- no runtime or scheduler imports
- no persistence imports
- no ML imports
- no LLM or agent imports
- no risk or execution imports
- no portfolio imports
- no order, fill, account, or position concepts

Normal pytest must remain offline, credential-free, and safe. Any future
integration test that requires external services must be skipped by default and
outside this evaluator implementation path.

## 11. Mutation Tests

A future implementation must test no mutation of:

- `ValidatedResearchArtifact`
- `ValidatedSignalDefinition`
- `SignalEvaluationInputSnapshot`
- `SignalInputValue`
- `SignalInputBundle`
- `SignalInputBundleCompletenessResult`
- returned `SignalEvaluationResult`

The tests should preserve object identity where relevant and verify tuple
ordering and immutable metadata remain stable before and after evaluation.

## 12. Forbidden Behavior Matrix

The following behavior remains forbidden for this evaluator candidate:

| Forbidden behavior | Required future test posture |
| --- | --- |
| signal-to-risk conversion | absent from evaluator output and dependencies |
| risk approval | absent from evaluator output and dependencies |
| execution intent creation | absent from evaluator output and dependencies |
| execution plan mutation | absent from evaluator output and dependencies |
| order submission | absent from evaluator output and dependencies |
| broker interaction | absent from evaluator output and dependencies |
| portfolio mutation | absent from evaluator output and dependencies |
| live data fetching | absent from evaluator output and dependencies |
| scheduler or runtime behavior | absent from evaluator output and dependencies |
| persistence writes | absent from evaluator output and dependencies |
| ML inference or training | absent from evaluator output and dependencies |
| LLM trading-path calls | absent from evaluator output and dependencies |

If any implementation requires one of these behaviors, it is not this
threshold-style advisory evaluator and must be rejected or moved to a separate
design gate.

## 13. Open Questions Before Implementation

These items must be answered before production code begins:

- exact `ValidatedSignalDefinition`
- exact `ValidatedResearchArtifact`
- final input name
- final threshold value source
- final comparator
- final `output_value` representation
- final `reason_code` values
- final diagnostics, assumptions, and limitations
- missing-input behavior
- extra-input behavior
- snapshot id compatibility
- `as_of` compatibility
- completeness result flow
- whether evaluator validates completeness internally or requires prevalidated
  input

Until these questions are resolved, the candidate remains selected but
unimplemented.

## 14. Implementation Go/No-Go Criteria

Implementation may begin only when:

- candidate contract is finalized
- test matrix is accepted
- exact input name and type are fixed
- threshold semantics are fixed
- output semantics are fixed
- missing and extra input policy is fixed
- snapshot and `as_of` compatibility is fixed
- required tests are ready to be implemented
- implementation scope explicitly forbids trading-path behavior

If any criterion is unresolved, the correct decision is no-go for production
evaluator code.

## 15. Explicitly Out Of Scope

Phase 29 Step 4 does not add:

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

## 16. Non-Binding Future Phase Sketch

Possible future phases include:

1. Phase 29 Step 5: finalize evaluator-specific constants and contract
   decisions, docs-only.
2. Phase 29 Step 6: minimal threshold evaluator implementation, only if all
   gate and test matrix conditions are satisfied.
3. Phase 29 Step 7: threshold evaluator traceability/no-lookahead hardening.

This sketch is non-binding. Any future work must remain contract-first,
test-first, deterministic, offline-safe, credential-free, broker-isolated,
advisory, pre-risk, and outside the LLM trading hot path.
