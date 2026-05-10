# Phase 29 First Real Evaluator Design Gate

## 1. Purpose

Phase 29 Step 1 defines the first real evaluator design gate.

The pre-evaluator input stack is now available:

- `SignalEvaluationInputSnapshot` provides reference metadata.
- `SignalInputValue` provides one explicit observed scalar value.
- `SignalInputBundle` groups explicit values, rejects duplicate names, and
  rejects lookahead values after bundle `as_of`.
- `SignalInputBundleCompletenessResult` and
  `validate_signal_input_bundle_completeness(...)` provide metadata-only name
  completeness validation.

This phase does not implement a real evaluator. Real signal computation remains
forbidden until a future evaluator-specific design satisfies this gate.

This phase is documentation-only. It adds no production code, tests, evaluator
implementation, evaluator protocol changes, signal computation, feature
computation, strategy logic, scoring, ranking, confidence or probability,
signal direction, actionability flags, signal-to-risk conversion, risk
approval, execution intent creation, execution-plan mutation, portfolio
mutation, broker or Alpaca behavior, order submission, scheduler/runtime
behavior, persistence writes, live data ingestion, network calls, ML training
or inference, or LLM trading-path logic.

## 2. Why A Design Gate Is Needed

Real evaluators are the first place where the system could accidentally
introduce behavior that looks like a trading decision. Without a design gate,
an evaluator implementation could quietly add:

- actual signal computation
- feature interpretation
- strategy semantics
- output values that may be mistaken as recommendations
- direction, confidence, or ranking
- lookahead bias
- hidden data access
- risk-like behavior
- execution-adjacent behavior

This gate exists to prevent those risks before implementation. A future real
evaluator must be designed as a deterministic, advisory, pre-risk component
before any production code is added.

## 3. Minimum Prerequisites Before Any Real Evaluator

A future real evaluator design must explicitly identify:

- the `ValidatedSignalDefinition` it implements
- the supporting `ValidatedResearchArtifact`
- the required input names from `SignalEvaluationInputSnapshot`
- the expected `SignalInputValue` names and value types
- whether `SignalInputBundle` completeness validation is required
- the expected `as_of` behavior
- the expected `evaluated_at` behavior
- the exact advisory output semantics
- assumptions
- limitations
- deterministic tests required
- no-lookahead tests required
- side-effect and dependency tests required

If any prerequisite is missing, implementation remains out of scope.

## 4. Required Input Boundary

A future real evaluator must use explicit inputs only. It may conceptually
require:

- `ValidatedSignalDefinition`
- `SignalEvaluationInputSnapshot`
- `SignalInputBundle`
- `SignalInputBundleCompletenessResult` or a successful completeness
  validation check
- explicit UTC-aware `as_of`
- explicit UTC-aware `evaluated_at`

It must not fetch live data, query a feature store, call a broker, read runtime
state, read scheduler state, read account or portfolio state, or infer missing
inputs. Missing values must be handled through the evaluator-specific
precondition policy documented before implementation.

## 5. Completeness Requirements

A future real evaluator must not run unless its required input names are
present.

The current completeness boundary compares only
`SignalEvaluationInputSnapshot.required_input_names` to
`SignalInputBundle.values[n].name`, reports missing names in snapshot order,
reports extra names in bundle order, and keeps extras non-blocking in this
phase. It does not inspect values, perform lookahead validation, require
snapshot id equality, or require `as_of` equality.

Open questions for a future evaluator-specific design:

- Should evaluator callers pass a precomputed
  `SignalInputBundleCompletenessResult`?
- Should the evaluator call
  `validate_signal_input_bundle_completeness(...)` internally?
- Should missing inputs raise a validation error?
- Should missing inputs produce an advisory failure result?
- Should extra inputs be ignored or rejected?
- Should snapshot id equality be required?
- Should `as_of` equality between snapshot and bundle be required?

This gate does not decide those questions where the current contracts leave
them open. It requires the future evaluator-specific design to decide them
before implementation.

## 6. Lookahead And Timestamp Requirements

A future real evaluator design must define timestamp behavior before code is
added:

- all input values must satisfy `observed_at <= evaluator as_of`
- `SignalInputBundle` already rejects values after `bundle.as_of`
- whether evaluator `as_of` must equal bundle `as_of`
- whether evaluator `as_of` must equal snapshot `as_of`
- `evaluated_at` must be UTC-aware
- `evaluated_at` must not be earlier than `as_of`
- the evaluator must not call wall-clock APIs internally
- the evaluator must not infer from data unavailable at `as_of`

No evaluator may fill missing timestamps from the system clock. No evaluator
may silently treat runtime availability as historical availability.

## 7. Output Semantics

A future real evaluator may eventually produce `SignalEvaluationResult`, but
the result remains:

- advisory
- pre-risk
- not a recommendation
- not a signal-to-trade instruction
- not risk approval
- not an execution intent
- not an order request
- not portfolio-aware
- not broker-aware

If output values, reason codes, diagnostics, assumptions, or limitations are
used, their meaning must be documented before implementation. The output must
be understandable as a deterministic advisory evaluation result, not as
permission to trade.

## 8. What Remains Forbidden

Even for a future real evaluator, the following remain forbidden unless a later
explicit design phase permits them:

- `should_trade`
- `actionable`
- `approved`
- `risk_approved`
- side, buy, sell, long, or short trade instructions
- position sizing
- notional, quantity, cash, or buying-power logic
- execution intent creation
- execution plan mutation
- broker, order, fill, account, or position references
- scheduler or runtime behavior
- persistence writes
- live or paper trading mode toggles
- ML training or inference
- LLM prompt, output, or trace in the trading path

If score, direction, confidence, probability, or rank are ever considered, they
require a separate design phase and must remain advisory only.

## 9. Determinism And Side-Effect Rules

Future real evaluators must:

- be deterministic for identical inputs
- use only explicit input contracts
- avoid network calls
- avoid live data access
- avoid file, database, or cache writes
- avoid environment-variable driven behavior
- avoid random behavior unless explicitly seeded and separately approved
- avoid broker, account, position, order, or fill access
- avoid scheduler or runtime access
- avoid ML or LLM calls in the trading path
- avoid mutation of definitions, snapshots, bundles, values, completeness
  results, or result objects

Any evaluator design that needs runtime state, persistence, a broker, account
state, portfolio state, model inference, or LLM output is not admitted by this
gate and requires a separate design review.

## 10. Test Gate For A Future Implementation

A future real evaluator implementation must include deterministic tests for:

- deterministic repeated results
- exact input traceability preservation
- completeness precondition behavior
- missing input behavior
- extra input behavior
- snapshot id compatibility behavior
- `as_of` compatibility behavior
- `evaluated_at >= as_of`
- no-lookahead input rejection
- no hidden wall-clock access
- no environment-variable reads
- no random behavior
- no network or socket access
- no file, database, or cache writes
- no broker or Alpaca imports
- no runtime or scheduler imports
- no ML or LLM imports
- no risk or execution imports
- no forbidden output fields
- no mutation of input contracts

These tests must run in normal pytest without credentials, live services,
network access, broker accounts, paper trading opt-ins, model services, or LLM
clients.

## 11. Candidate First Real Evaluator

This phase does not select or implement a first real evaluator.

A future candidate should be chosen only after:

- the validated signal definition is already present
- required inputs are simple and deterministic
- the computation is small enough to test exhaustively
- the output semantics are advisory and clear
- no external data fetching is required

No concrete trading strategy is selected in this phase.

Phase 29 Step 2 performs candidate selection only in
[`docs/design/phase29_first_real_evaluator_candidate_selection.md`](phase29_first_real_evaluator_candidate_selection.md).
That selection does not authorize implementation. A future evaluator-specific
design is still required before any production code, real evaluator behavior,
or signal computation may be added.

Phase 29 Step 3 designs the selected candidate contract only in
[`docs/design/phase29_first_real_evaluator_candidate_contract.md`](phase29_first_real_evaluator_candidate_contract.md).
Step 3 remains design-only and preserves this implementation gate. Production
code, real evaluator behavior, and signal computation remain forbidden until a
later implementation phase is explicitly scoped and the gate remains satisfied.

Phase 29 Step 4 strengthens this gate with an implementation test matrix in
[`docs/design/phase29_first_real_evaluator_test_matrix.md`](phase29_first_real_evaluator_test_matrix.md).
The matrix is pre-implementation only. It does not authorize production code,
real evaluator behavior, or signal computation.

Phase 29 Step 5 reviews implementation readiness in
[`docs/design/phase29_first_real_evaluator_implementation_readiness.md`](phase29_first_real_evaluator_implementation_readiness.md).
Implementation remains blocked unless the readiness review explicitly clears
the candidate or a later follow-up design resolves the remaining blockers and
clears implementation scope.

## 12. Relationship To Existing Contracts

`ValidatedResearchArtifact` is supporting evidence. It records reviewed
research metadata, assumptions, limitations, and validation context, but it is
not a live signal, risk approval, or execution decision.

`ValidatedSignalDefinition` is the promoted deterministic signal metadata
contract. It may identify what a future evaluator implements, but it does not
compute signal values, approve trades, or create execution intents.

`SignalEvaluationInputSnapshot` is reference metadata. It identifies required
input names, source ids, a snapshot id, and a UTC-aware `as_of`, but carries no
actual observed values.

`SignalInputValue` carries one explicit observed scalar value with a name,
value, observation timestamp, and source id. It does not compare itself to an
evaluator `as_of` and does not compute features or signals.

`SignalInputBundle` groups explicit `SignalInputValue` objects. It preserves
ordering and object identity, rejects duplicate names, validates bundle
`as_of`, and rejects input values observed after bundle `as_of`. It remains an
input container only.

`SignalInputBundleCompletenessResult` records metadata-only completeness
results. It is not a signal result, recommendation, risk verdict, execution
intent, or broker-facing request.

`validate_signal_input_bundle_completeness(...)` compares required names and
bundle value names only. It reports missing and extra names deterministically
without inspecting values, enforcing timestamp compatibility, or requiring
snapshot id equality.

`SignalEvaluationResult` is the advisory output contract. It may eventually be
used by a real evaluator, but it remains pre-risk and is not a recommendation,
trade approval, execution intent, order request, broker payload, or portfolio
decision.

`NoOpSignalEvaluator` proves the evaluator-shaped input/output seam without
real computation. It remains the only evaluator implementation at this stage.

Deterministic time contracts provide UTC-aware timestamp validation,
fixed-clock testing support, and lookahead helpers. Future real evaluators must
continue to use explicit timestamps rather than wall-clock calls.

## 13. Explicitly Out Of Scope

Phase 29 Step 1 does not add:

- evaluator implementation
- evaluator protocol
- signal computation
- feature computation
- strategy logic
- score, direction, confidence, or actionability
- ranking or probability
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
- ML or LLM trading-path behavior

Normal pytest must remain offline, credential-free, and safe.

## 14. Non-Binding Future Phase Sketch

Possible future phases include:

1. Phase 29 Step 6A: final threshold evaluator constants/output semantics
   design, docs-only.
2. Phase 29 Step 6B: first real evaluator minimal implementation, if and only
   if readiness is confirmed.
3. Phase 29 Step 7: first real evaluator traceability/lookahead hardening.

This sketch is non-binding. Any future work must remain contract-first,
test-first, deterministic, offline-safe, credential-free, broker-isolated,
advisory, pre-risk, and outside the LLM trading hot path.
