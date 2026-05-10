# Phase 28 Signal Input Bundle Boundary Design

## 1. Purpose

Phase 28 Step 1 designed the future signal input bundle boundary. The project
needs this boundary before any real evaluator can consume observed values
because a future evaluator should receive one explicit immutable bundle, not
loose lists, dictionaries, live data handles, feature stores, or runtime
objects.

Phase 28 Step 2 adds only the minimal immutable `SignalInputBundle` contract.
It groups explicit `SignalInputValue` objects for future evaluator use while
preserving supplied ordering and input value object identity. It rejects
duplicate input names and rejects lookahead values where
`SignalInputValue.observed_at > bundle.as_of`.

Step 2 still does not add completeness validation against
`SignalEvaluationInputSnapshot`. It also does not add evaluator behavior,
signal computation, feature computation, strategy logic, scoring, ranking,
confidence or probability, signal direction, actionability flags,
signal-to-risk conversion, risk approval, execution intent creation,
execution-plan mutation, portfolio mutation, broker or Alpaca behavior, order
submission, scheduler/runtime behavior, persistence writes, live data
ingestion, network calls, ML training or inference, or LLM trading-path logic.

Phase 28 Step 3 hardens traceability with tests and documentation only. It adds
no production behavior. The hardening proves the bundle continues to preserve
exact snapshot id strings, `as_of` identity, supplied value order, value object
identity, and each grouped value's name, source id, observed timestamp identity,
and payload. It also pins tuple behavior, duplicate-name rejection, lookahead
rejection, the absence of completeness validation, and isolation from evaluator,
risk, execution, broker, runtime, persistence, ML, and LLM trading-path
behavior.

Phase 28 Step 4 documents the separate completeness validation boundary in
[`docs/design/phase28_signal_input_bundle_completeness_boundary.md`](phase28_signal_input_bundle_completeness_boundary.md).
It does not implement completeness validation, change the bundle constructor, or
add evaluator behavior. Completeness remains separate from the grouping
contract: `SignalInputBundle` still only groups explicit observed values and
enforces duplicate-name and lookahead safety.

Phase 28 Step 5 adds that minimal separate completeness boundary in
`src/algotrader/signals/signal_input_bundle_completeness.py`. It adds
`SignalInputBundleCompletenessResult` and
`validate_signal_input_bundle_completeness(snapshot, bundle)`. The function
compares only `SignalEvaluationInputSnapshot.required_input_names` with
`SignalInputBundle.values[n].name`, reports missing names in snapshot order,
reports extra names in bundle order, and does not inspect or interpret values.
Extra names are reported but do not make the result incomplete in this phase.

## 2. Relationship To Existing Input Contracts

`SignalEvaluationInputSnapshot` is reference metadata. It provides:

- snapshot identity through `snapshot_id`
- required input names through `required_input_names`
- source ids through `source_ids`
- an explicit UTC-aware `as_of`
- no actual values

`SignalInputValue` is one explicit observed scalar value. It provides:

- input name through `name`
- observed value through `value`
- observation timestamp through `observed_at`
- source traceability through `source_id`

`SignalInputBundle` is an immutable collection of explicit observed values. In
Step 2, it provides:

- deterministic ordering
- duplicate-name policy
- lookahead validation against evaluator `as_of`
- source and timestamp traceability

Completeness validation against a snapshot now lives in a separate pure helper.
That boundary is separate from the bundle constructor because completeness
depends on comparing `SignalInputBundle` to `SignalEvaluationInputSnapshot`,
while the bundle itself remains a grouping contract for explicit values.

The bundle would sit between reference-only snapshots and future real
evaluators. It would not itself be a signal result or trading decision.

## 3. Why A Bundle Is Needed

A future real evaluator should not receive loose lists, dictionaries, live data
handles, feature stores, runtime objects, broker clients, or persistence
queries. Those shapes invite hidden data access and unstable ordering.

Instead, a future evaluator should receive one explicit immutable bundle that:

- contains only precomputed observed values
- is built before evaluation
- is validated against an explicit `as_of`
- can prove all values were available at or before `as_of`
- preserves deterministic ordering
- prevents hidden data access

The bundle boundary keeps observed input assembly separate from evaluation. It
also makes lookahead and completeness checks visible before any real signal
logic exists.

## 4. Implemented Minimal Fields

The Step 2 bundle contract has exactly:

- `snapshot_id`
- `as_of`
- `values: tuple[SignalInputValue, ...]`

Optional future fields should be added only if a later phase justifies them:

- source ids
- completeness status
- quality status
- value name index
- bundle fingerprint

The implemented field set is the smallest surface needed to enforce
traceability, determinism, and no-lookahead behavior before any evaluator is
introduced.

## 5. Implemented Bundle Rules

The minimal bundle:

- is frozen and slotted
- preserves input value object identity
- converts incoming iterables to tuples
- preserves supplied ordering exactly
- rejects empty bundles
- rejects duplicate input names
- validates all value `observed_at <= bundle as_of`
- validates bundle `as_of` as UTC-aware
- rejects naive and non-UTC bundle timestamps
- preserves exact value names, source ids, observed values, and observation
  timestamps
- performs no computation or interpretation
- performs no feature computation
- performs no signal computation

The bundle remains a deterministic input container. It does not
normalize values, compute features, rank inputs, infer signal direction, or
convert observations into advisory outputs.

## 6. Completeness Against SignalEvaluationInputSnapshot

Later pure validation should be able to prove whether a bundle satisfies a
`SignalEvaluationInputSnapshot` by matching required input names.

Open design questions:

- should completeness validation live in the bundle constructor?
- should completeness validation be a separate pure function?
- should missing inputs raise immediately or produce an explicit validation
  result?
- should extra inputs be allowed or rejected?
- should ordering follow snapshot `required_input_names` or supplied input
  order?

Step 3 hardened traceability only. Step 4 documented these completeness
questions in a separate design note. Step 5 implements the minimal pure
validation boundary: missing names are returned in snapshot order, extra names
are returned in bundle order, extras do not make the result incomplete, and
snapshot id or `as_of` equality is not enforced yet.

## 7. Lookahead Rules

The Step 2 bundle supports no-lookahead validation:

- every `SignalInputValue.observed_at` must be `<= bundle.as_of`
- every value must be available at or before evaluator `as_of`
- future observations are rejected
- bundle construction must not fetch newer data
- evaluator code must not fetch newer data
- no wall-clock time may be used to infer availability

This is the first place to validate a collection of input values
against an `as_of`. `SignalInputValue` validates only its own timestamp; bundle
or assembly phases should validate whether values are usable for a specific
evaluation time.

## 8. Determinism And Side-Effect Rules

Bundle contracts must:

- use only explicit `SignalInputValue` objects
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

The Step 2 bundle does not read from runtime state, credentials, broker adapters,
files, caches, databases, notebooks, model services, or LLM outputs.

## 9. Output And Advisory Boundary

A bundle is not:

- a signal result
- a recommendation
- a score
- a rank
- a direction
- a risk approval
- an execution intent
- an order request
- a portfolio decision

It is only an input container for future deterministic evaluation. Its
existence does not imply a signal was computed, a feature was computed, risk was
approved, execution is ready, or a trade should be created.

## 10. Relationship To Future Real Evaluators

A future real evaluator may eventually accept:

- `ValidatedSignalDefinition`
- `SignalEvaluationInputSnapshot`
- `SignalInputBundle`
- explicit `as_of`
- explicit `evaluated_at`

That future evaluator remains out of scope here. Phase 28 Step 2 only adds the
minimal input bundle contract needed before evaluator implementation can be
considered. Phase 28 Step 5 adds the minimal completeness boundary that may
later sit between snapshot/bundle assembly and evaluator use.

## 11. Explicitly Out Of Scope

Phase 28 Step 5 does not add:

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
- ML trading-path behavior
- LLM trading-path behavior

Normal pytest must remain offline, credential-free, and safe.

## 12. Non-Binding Future Phase Sketch

Possible future phases include:

1. Phase 28 Step 2: minimal immutable signal input bundle contract.
2. Phase 28 Step 3: signal input bundle traceability hardening.
3. Phase 28 Step 4: signal input bundle completeness boundary design.
4. Phase 28 Step 5: minimal completeness validation contract and pure function.
5. Phase 28 Step 6: completeness validation traceability hardening.
6. Phase 29 Step 1: first real evaluator design, docs-only.
7. A later phase: minimal deterministic evaluator for one validated signal
   definition.

This sequence is non-binding. Any future work must remain contract-first,
test-first, deterministic, offline-safe, credential-free, broker-isolated,
advisory, pre-risk, and outside the LLM trading hot path.
