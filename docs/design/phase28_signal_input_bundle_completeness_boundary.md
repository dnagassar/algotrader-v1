# Phase 28 Signal Input Bundle Completeness Boundary Design

## 1. Purpose

Phase 28 Step 4 documented the future completeness validation boundary between
`SignalEvaluationInputSnapshot.required_input_names` and
`SignalInputBundle.values`. Phase 28 Step 5 adds the minimal immutable
completeness result contract and one pure validation function for that
boundary. Phase 28 Step 6 hardens traceability with tests and documentation
only; no production behavior is added.

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

Step 5 implements the smallest deterministic subset: it compares required input
names with bundle value names, reports missing names in snapshot order, reports
extra names in bundle order, and treats the bundle as complete when no required
names are missing. Extra names are reported but do not make the result
incomplete in this phase. Snapshot id equality and `as_of` equality are not
enforced yet.

Step 6 proves that behavior remains name-only, metadata-only, non-mutating,
deterministic, and isolated from trading-path behavior. It pins that
completeness validation does not inspect `SignalInputValue.value`, compare
`SignalInputValue.source_id`, compare `SignalInputValue.observed_at`, perform
lookahead validation, read wall-clock time, read environment variables, depend
on random state, access live data, or call broker/runtime/persistence/ML/LLM
systems.

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

The boundary can be designed several ways:

- constructor-level validation inside `SignalInputBundle`
- a pure function such as
  `validate_signal_input_bundle_completeness(snapshot, bundle)`
- a separate immutable validation result contract
- an evaluator precondition check before any real evaluator consumes a bundle

Phase 28 Step 5 chooses a small pure validation boundary before evaluator use,
rather than expanding the `SignalInputBundle` constructor. The bundle
constructor remains focused on grouping explicit values, preserving
deterministic traceability, rejecting duplicate names, and enforcing lookahead
safety. Completeness depends on a second contract, so keeping it in a separate
pure boundary makes the comparison explicit and easy to test.

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

Phase 28 Step 5 implements `SignalInputBundleCompletenessResult` and
`validate_signal_input_bundle_completeness(...)` as metadata-only validation
surface. The result represents only whether an explicit bundle has all required
names for an explicit snapshot according to the minimal Step 5 policy. It is
not a signal result, trading recommendation, risk verdict, execution intent, or
broker-facing request.

Phase 28 Step 6 hardens that surface with tests that pin the exact result field
set, frozen/slotted dataclass behavior, tuple field immutability, deterministic
missing and extra name ordering, snapshot id and bundle snapshot id
traceability, input non-mutation, and the absence of advisory, evaluator,
feature, risk, execution, broker, runtime, persistence, ML, and LLM concepts.

## 5. Missing Input Behavior

Phase 28 Step 5 returns missing inputs in an immutable validation result.
Missing inputs do not raise by themselves in this phase. Missing input names are
ordered according to `snapshot.required_input_names`.

Future phases may still decide whether stricter missing-input behavior should:

- raise a validation error immediately
- be represented as advisory diagnostics

The current Step 5 behavior is explicit and deterministic, but it is still a
minimal boundary rather than final evaluator admission policy.

## 6. Extra Input Behavior

Phase 28 Step 5 reports bundle values whose names are not in
`snapshot.required_input_names` through `extra_input_names`. Extra names are
ordered according to `bundle.values` and do not make the result incomplete in
this phase.

Future phases may still decide whether extra names should be:

- warned about through diagnostics
- rejected
- controlled by an explicit policy later

The Step 5 policy is intentionally explicit: extra inputs are visible to callers
but not rejected. If a later phase rejects extras, the reported names should
remain deterministic.

Phase 28 Step 6 keeps this policy unchanged: extra inputs remain non-blocking
and continue to be reported deterministically.

## 7. Snapshot/Bundle Time Compatibility

Snapshot and bundle time compatibility remains open. Phase 28 Step 5 does not
enforce `bundle.as_of == snapshot.as_of` or any other `as_of` compatibility
rule. Later phases should decide whether validation requires:

- `bundle.as_of == snapshot.as_of`
- `bundle.as_of <= snapshot.as_of`
- `bundle.as_of >= snapshot.as_of`
- a different explicit compatibility rule

Strict equality may be the simplest first rule because both contracts already
carry explicit UTC-aware `as_of` timestamps. However, Step 5 does not make that
a production decision. Any non-equality rule would need careful design so it
does not weaken lookahead safety or make evaluator availability ambiguous.

Lookahead safety must remain preserved. `SignalInputBundle` already rejects
values with `observed_at > bundle.as_of`; a future compatibility rule must not
allow a bundle to satisfy a snapshot in a way that makes values appear
available before they were actually observed.

Phase 28 Step 6 keeps this boundary unchanged. Completeness validation still
does not compare `observed_at` values and does not perform lookahead validation;
that remains the bundle constructor's responsibility.

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
validation logic, completeness result, or a real evaluator. Phase 28 Step 5
adds only minimal completeness validation. Phase 28 Step 6 adds only
traceability hardening tests and docs for that validation boundary. Any future
evaluator output remains advisory and pre-risk. LLMs remain outside the trading
hot path and must not compute live signal outputs, approve trades, mutate
execution plans, or interact with brokers.

## 11. Explicitly Out Of Scope

Phase 28 Step 6 does not add:

- production behavior
- bundle constructor changes
- completeness fields on `SignalInputBundle`
- completeness fields on `SignalEvaluationInputSnapshot`
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

1. Phase 29 Step 1: first real evaluator design, docs-only.
2. A later phase: minimal deterministic evaluator for one validated signal
   definition.

This sketch is non-binding. Any future work must remain contract-first,
test-first, deterministic, offline-safe, credential-free, broker-isolated,
advisory, pre-risk, and outside the LLM trading hot path.
