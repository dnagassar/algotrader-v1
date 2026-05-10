# Phase 28 Signal Input Bundle Completeness Boundary Design

## 1. Purpose

Phase 28 Step 4 documents the future completeness validation boundary between
`SignalEvaluationInputSnapshot.required_input_names` and
`SignalInputBundle.values`. It is documentation-only and adds no production
code, tests, validator, validation result, evaluator, signal computation, or
runtime behavior.

Completeness validation is needed before a future real evaluator can consume a
`SignalInputBundle` because a bundle can be well-formed, immutable,
lookahead-safe, and traceable while still failing to satisfy the input names
declared by a snapshot. A future evaluator should not have to discover missing
inputs while computing a signal. The pre-evaluator boundary should answer,
using only explicit contracts:

- are all required input names from the snapshot present in the bundle?
- are any required inputs missing?
- are extra bundle inputs allowed or rejected?
- does `bundle.snapshot_id` need to match `snapshot.snapshot_id`?
- does `bundle.as_of` need to match `snapshot.as_of`, or only be compatible?

This phase records those questions and candidate rules without making final
production decisions.

## 2. Current Contract Roles

`SignalEvaluationInputSnapshot` is reference metadata. It defines the required
input names for a future evaluation, identifies the snapshot/reference context
through `snapshot_id`, carries source ids, and preserves an explicit UTC-aware
`as_of`. It does not carry actual observed values.

`SignalInputBundle` carries actual observed `SignalInputValue` objects. It
preserves value ordering and object identity, rejects duplicate names, validates
bundle `as_of` as UTC-aware, and rejects lookahead values where
`SignalInputValue.observed_at > bundle.as_of`. It does not know whether it
satisfies a `SignalEvaluationInputSnapshot`.

Future completeness validation would compare names and compatibility metadata
across the snapshot and bundle. It must not inspect, compute, normalize, or
interpret values. It must not calculate features, produce signals, score, rank,
infer direction, decide actionability, approve risk, or create execution
behavior.

## 3. Where Completeness Validation Should Live

The boundary can be designed several ways in a later implementation phase:

- constructor-level validation inside `SignalInputBundle`
- a pure function such as
  `validate_signal_input_bundle_completeness(snapshot, bundle)`
- a separate immutable validation result contract
- an evaluator precondition check before any real evaluator consumes a bundle

The preferred direction is a small pure validation boundary before evaluator
use, rather than expanding the `SignalInputBundle` constructor too much. The
bundle constructor should remain focused on grouping explicit values,
preserving deterministic traceability, rejecting duplicate names, and enforcing
lookahead safety. Completeness depends on a second contract, so keeping it in a
separate pure boundary would make the comparison explicit and easier to test.

An evaluator precondition may later require successful completeness validation,
but the evaluator should not be the first place where missing names, extra
names, or snapshot/bundle metadata compatibility are discovered.

## 4. Candidate Future Validation Rules

Future completeness validation may check:

- every `snapshot.required_input_names` entry is present in `bundle.values`
- missing input names are reported deterministically
- duplicate value names remain rejected by `SignalInputBundle` itself
- extra input policy is explicit
- `snapshot_id` compatibility is explicit
- `as_of` compatibility is explicit
- reported missing and extra names use deterministic ordering
- validation does not interpret values
- validation does not normalize values
- validation does not compute features
- validation does not compute signals
- validation does not score, rank, infer direction, or imply actionability

If a later phase adds a validation result, the result should represent only
whether an explicit bundle satisfies an explicit snapshot according to the
chosen policy. It should not be reused as a signal result, trading
recommendation, risk verdict, execution intent, or broker-facing request.

## 5. Missing Input Behavior

Missing input behavior remains an open design question. Later phases should
decide whether missing inputs should:

- raise a validation error immediately
- return an immutable validation result
- be represented as advisory diagnostics
- be ordered according to `snapshot.required_input_names`

The current docs already imply that completeness validation should be explicit
and deterministic, but they do not require a final production shape. A minimal
future implementation could start strict and small, but this phase does not
choose that behavior.

## 6. Extra Input Behavior

Extra input behavior also remains open. Later phases should decide whether
bundle values whose names are not in `snapshot.required_input_names` should be:

- allowed
- ignored
- warned about through diagnostics
- rejected
- reported deterministically
- controlled by an explicit policy later

The policy should not be implicit. If extra inputs are allowed, that allowance
should be visible at the validation boundary so a future evaluator does not
quietly consume hidden or irrelevant values. If extra inputs are rejected, the
reported names should be deterministic.

## 7. Snapshot/Bundle Time Compatibility

Snapshot and bundle time compatibility remains open. Later phases should decide
whether validation requires:

- `bundle.as_of == snapshot.as_of`
- `bundle.as_of <= snapshot.as_of`
- `bundle.as_of >= snapshot.as_of`
- a different explicit compatibility rule

Strict equality may be the simplest first rule because both contracts already
carry explicit UTC-aware `as_of` timestamps. However, this phase does not make
that a production decision. Any non-equality rule would need careful design so
it does not weaken lookahead safety or make evaluator availability ambiguous.

Lookahead safety must remain preserved. `SignalInputBundle` already rejects
values with `observed_at > bundle.as_of`; a future compatibility rule must not
allow a bundle to satisfy a snapshot in a way that makes values appear
available before they were actually observed.

## 8. Determinism And Side-Effect Rules

Future completeness validation must:

- use only explicit `SignalEvaluationInputSnapshot` and `SignalInputBundle`
  inputs
- avoid network calls
- avoid live data access
- avoid file writes
- avoid database writes
- avoid cache writes
- avoid environment-variable driven behavior
- avoid random behavior
- avoid broker, account, position, order, or fill access
- avoid scheduler/runtime access
- avoid ML calls in the trading path
- avoid LLM calls in the trading path

The validation boundary must be pure and offline-safe. It should be safe in
normal pytest without credentials, live services, brokers, runtime state,
schedulers, caches, databases, model services, or notebooks.

## 9. Advisory/Non-Computational Boundary

Completeness validation is not:

- a signal result
- a recommendation
- a score
- a rank
- a direction
- a confidence or probability
- an actionability flag
- a risk approval
- an execution intent
- an order request
- a portfolio decision

It only verifies whether an explicit bundle can satisfy an explicit input
snapshot. Passing validation would mean only that required inputs and
compatibility metadata met the chosen boundary rules. It would not mean a signal
exists, a trade is advisable, risk has approved anything, or execution is
allowed.

## 10. Relationship To Future Real Evaluators

A future real evaluator may eventually require:

- `ValidatedSignalDefinition`
- `SignalEvaluationInputSnapshot`
- `SignalInputBundle`
- successful completeness validation
- explicit `as_of`
- explicit `evaluated_at`

That evaluator is not implemented here. Phase 28 Step 4 does not implement
validation logic, does not implement a completeness result, and does not add a
real evaluator. Any future evaluator output remains advisory and pre-risk. LLMs
remain outside the trading hot path and must not compute live signal outputs,
approve trades, mutate execution plans, or interact with brokers.

## 11. Explicitly Out Of Scope

Phase 28 Step 4 does not add:

- completeness validator implementation
- completeness result contract
- bundle constructor changes
- evaluator implementation
- signal computation
- feature computation
- strategy logic
- score, direction, confidence, or actionability
- ranking or priority behavior
- signal-to-risk conversion
- risk approval
- execution intent creation
- execution-plan mutation
- portfolio mutation
- broker or Alpaca behavior
- order submission
- runtime or scheduler behavior
- persistence
- live data ingestion
- network calls
- ML trading-path behavior
- LLM trading-path behavior

Normal pytest must remain offline, credential-free, and safe.

## 12. Non-Binding Future Phase Sketch

Possible future phases include:

1. Phase 28 Step 5: minimal completeness validation contract or pure function.
2. Phase 28 Step 6: completeness validation traceability hardening.
3. Phase 29 Step 1: first real evaluator design, docs-only.
4. A later phase: minimal deterministic evaluator for one validated signal
   definition.

This sketch is non-binding. Any future work must remain contract-first,
test-first, deterministic, offline-safe, credential-free, broker-isolated,
advisory, pre-risk, and outside the LLM trading hot path.
