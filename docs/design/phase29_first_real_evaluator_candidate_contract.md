# Phase 29 First Real Evaluator Candidate Contract Design

## 1. Purpose

Phase 29 Step 3 is evaluator-candidate contract design only.

The selected candidate is a future minimal threshold-style advisory evaluator
over one explicit scalar `SignalInputValue`. This phase does not implement
that evaluator. It adds no production code, tests, evaluator protocol changes,
signal computation, feature computation, strategy logic, scoring, ranking,
confidence or probability, signal direction, actionability, signal-to-risk
conversion, risk approval, execution intent creation, execution-plan mutation,
portfolio mutation, broker or Alpaca behavior, order submission,
scheduler/runtime behavior, persistence writes, live data ingestion, network
calls, ML training or inference, or LLM trading-path logic.

This document narrows the candidate contract questions that a later
implementation phase must answer. It does not authorize implementation.

Phase 29 Step 4 defines the implementation test matrix only in
[`docs/design/phase29_first_real_evaluator_test_matrix.md`](phase29_first_real_evaluator_test_matrix.md).
Creating that matrix does not authorize implementation. The candidate remains
unimplemented until a later implementation phase is explicitly scoped and all
gate and matrix criteria are satisfied.

Phase 29 Step 5 reviews implementation readiness in
[`docs/design/phase29_first_real_evaluator_implementation_readiness.md`](phase29_first_real_evaluator_implementation_readiness.md).
That review linked the then-unresolved constants and output semantics in this
contract to a recommended docs-only follow-up before implementation.

Phase 29 Step 6 documents constants and output semantics in
[`docs/design/phase29_threshold_evaluator_constants_output_semantics.md`](phase29_threshold_evaluator_constants_output_semantics.md).
It selects `indicator_value`, `Decimal`, `>=`, textual advisory output values,
and deterministic threshold reason codes for a future implementation, while
keeping production evaluator code blocked until exact validated signal and
research artifacts are available.

## 2. Candidate Summary

The future evaluator concept is:

- consumes one explicit scalar `SignalInputValue`
- requires a complete `SignalInputBundle`
- is tied to a `ValidatedSignalDefinition`
- is supported by a `ValidatedResearchArtifact`
- returns advisory `SignalEvaluationResult`
- does not create trades, execution intents, risk approvals, or orders

The evaluator would receive all inputs explicitly. It would not fetch data,
compute features, inspect broker state, inspect portfolio state, consult
runtime state, or infer missing values.

## 3. Required Future Inputs

A future evaluator-specific design may require:

- `ValidatedSignalDefinition`
- `SignalEvaluationInputSnapshot`
- `SignalInputBundle`
- `SignalInputBundleCompletenessResult` or a successful call to
  `validate_signal_input_bundle_completeness(...)`
- explicit UTC-aware `as_of`
- explicit UTC-aware `evaluated_at`

The required input name selected for the future candidate is:

- `indicator_value`

Step 6 selects this name for the future threshold evaluator design. This does
not authorize implementation and does not make any output actionable.

## 4. Accepted Value Type

The future candidate should consume a deterministic scalar value.

Preferred initial value type:

- `Decimal`

Rationale:

- deterministic representation
- avoids float reproducibility issues
- already supported by `SignalInputValue`
- fits explicit threshold comparison semantics

`int` may be acceptable only as a scalar input compatible with comparison, but
the first evaluator should avoid broad unions unless a later design clearly
justifies them. A narrow first implementation is easier to test exhaustively
and less likely to hide normalization or coercion rules.

This phase does not implement type handling.

## 5. Threshold And Comparator Semantics

Step 6 later selected these recommended future semantics:

- comparator: `>=`
- threshold source: explicit evaluator configuration or evaluator-local
  constant only
- harmless future unit-test threshold placeholder: `Decimal("1")`
- output values: `threshold_condition_met` and
  `threshold_condition_not_met`

The comparator would describe only whether the supplied scalar met a documented
advisory condition. It must not mean buy, sell, bullish, bearish, long, short,
actionable, approved, risk-approved, or trade-ready.

The future evaluator-specific design must document the threshold source,
comparison rule, equality behavior, accepted value type, and output meaning
before implementation.

## 6. Output Semantics

A future evaluator may produce `SignalEvaluationResult`.

Candidate output semantics:

- `output_value` should be advisory and non-actionable.
- It may represent a neutral textual or metadata result, such as whether the
  threshold condition was met.
- It must not be a score, confidence, probability, direction, rank, or
  recommendation unless separately designed later.
- `reason_code` should be deterministic and documented.
- diagnostics, assumptions, and limitations should explain the advisory-only
  nature.

Step 6 selects textual advisory `output_value` values:

- `threshold_condition_met`
- `threshold_condition_not_met`

These values are not recommendations, scores, confidence, direction, ranking,
actionability, risk approval, or execution readiness.

## 7. Missing Input Behavior

Future design options:

- require successful completeness validation before evaluator call
- evaluator rejects missing input with a validation error
- evaluator returns an advisory failure result

Recommendation:

- Prefer precondition validation before the evaluator call, with missing-input
  behavior explicitly tested in the evaluator-specific implementation phase.

The evaluator should not infer missing inputs, substitute defaults, fetch
values, consult runtime state, or continue as though the input were present.

This phase does not implement missing-input behavior.

## 8. Extra Input Behavior

Future policy options:

- extras are allowed but ignored
- extras are rejected
- extras are reported only by completeness validation

Recommendation:

- For the first evaluator, prefer allowing extras only if completeness
  validation already reports them and the evaluator reads exactly one required
  input by name.

This keeps the evaluator's input surface small while preserving visibility into
extra names. Step 6 recommends keeping extras non-blocking, ignored by the
evaluator, and incapable of affecting output.

This phase does not implement extra-input behavior.

## 9. Snapshot Id And As-Of Compatibility

Step 6 recommends strict equality:

- require `snapshot.snapshot_id == bundle.snapshot_id`
- require evaluator `as_of == bundle.as_of`
- require evaluator `as_of == snapshot.as_of`

Strict equality is the easiest initial rule to explain, audit, and test. Any
non-equality rule must prove it does not weaken lookahead safety or make input
availability ambiguous.

This phase does not implement snapshot id or `as_of` compatibility checks.

## 10. Timestamp And No-Lookahead Rules

Future evaluator-specific design must require:

- `as_of` UTC-aware
- `evaluated_at` UTC-aware
- `evaluated_at >= as_of`
- every `SignalInputValue.observed_at <= bundle.as_of`
- bundle `as_of` compatible with evaluator `as_of`
- no wall-clock reads inside evaluator
- no fetching newer data
- no inference from unavailable future data

`SignalInputBundle` already rejects values observed after bundle `as_of`. The
future evaluator-specific design must still decide how bundle `as_of`,
snapshot `as_of`, and evaluator `as_of` relate to each other.

## 11. Determinism And Side-Effect Rules

Future evaluator must:

- use only explicit inputs
- produce deterministic output for identical inputs
- not mutate definitions, snapshots, bundles, values, completeness results, or
  output contracts
- avoid environment-variable behavior
- avoid random behavior
- avoid network calls
- avoid file, database, or cache writes
- avoid broker, account, position, order, or fill access
- avoid scheduler or runtime access
- avoid ML or LLM calls in the trading path

Any future evaluator that needs hidden state, external services, persistence,
model inference, LLM output, broker state, account state, or portfolio state is
outside this candidate contract.

## 12. Forbidden Semantics

Even for this future threshold candidate, the following remain forbidden:

- `should_trade`
- `actionable`
- `approved`
- `risk_approved`
- buy, sell, long, or short trade instructions
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

## 13. Required Future Tests Before Implementation

A future implementation must include tests for:

- required input name lookup
- valid `Decimal` input behavior
- unsupported value type rejection
- complete bundle behavior
- missing input behavior
- extra input behavior
- snapshot id compatibility
- `as_of` compatibility
- UTC timestamp validation
- `evaluated_at >= as_of`
- no-lookahead behavior
- deterministic repeated outputs
- exact traceability preservation
- no mutation of input contracts
- no hidden wall-clock access
- no random behavior
- no environment-variable reads
- no network or socket access
- no file, database, or cache writes
- no broker or Alpaca imports
- no runtime or scheduler imports
- no persistence imports
- no ML or LLM imports
- no risk or execution imports
- no forbidden output fields

These tests must run in normal pytest without credentials, live services,
broker accounts, paper trading opt-ins, network access, model services, or LLM
clients.

## 14. Relationship To Existing Contracts

`ValidatedResearchArtifact` is the supporting evidence boundary. The future
threshold evaluator must identify the exact artifact that supports the
candidate before implementation. The artifact remains evidence only, not a
signal computation or trading decision.

`ValidatedSignalDefinition` is the promoted signal metadata boundary. The
future evaluator must identify the exact definition and version it implements
before implementation. The definition does not itself evaluate the threshold or
approve trades.

`SignalEvaluationInputSnapshot` names the required input and preserves
reference metadata. For this candidate, Step 6 selects the required input name
`indicator_value` for the future evaluator design.

`SignalInputValue` carries the explicit observed scalar value. The preferred
future value type is `Decimal`. The evaluator must not fetch or compute this
value internally.

`SignalInputBundle` groups explicit input values, validates bundle `as_of`,
rejects duplicate names, and rejects values observed after bundle `as_of`. The
future evaluator should consume the required value from the bundle by explicit
name.

`SignalInputBundleCompletenessResult` records metadata-only completeness. The
future evaluator-specific design must decide whether a precomputed result is
passed in or completeness is recomputed immediately before evaluation.

`validate_signal_input_bundle_completeness(...)` compares required names to
bundle value names only. The future evaluator should not be the first boundary
to discover missing required inputs.

`SignalEvaluationResult` is the advisory output contract. The future evaluator
may return it, but the result remains pre-risk and is not a recommendation,
trade approval, execution intent, order request, broker payload, or portfolio
decision.

`NoOpSignalEvaluator` proves the evaluator-shaped input/output seam without
real computation. The threshold candidate should keep the same advisory,
offline-safe, broker-isolated posture while adding only the smallest approved
deterministic threshold comparison in a later implementation phase.

Deterministic time contracts provide UTC-aware timestamp validation,
fixed-clock testing support, and lookahead helpers. The future evaluator must
use explicit `as_of` and `evaluated_at` values and must not call wall-clock APIs
internally.

## 15. Explicitly Out Of Scope

Phase 29 Step 3 does not add:

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

## 16. Non-Binding Future Phase Sketch

Possible future phases include:

1. Phase 29 Step 7: final implementation prompt/test scaffold design,
   docs-only.
2. Phase 29 Step 8: minimal threshold evaluator implementation only if
   validated signal/research artifacts and semantics are ready.
3. Phase 29 Step 9: threshold evaluator traceability/no-lookahead hardening.

This sketch is non-binding. Any future work must remain contract-first,
test-first, deterministic, offline-safe, credential-free, broker-isolated,
advisory, pre-risk, and outside the LLM trading hot path.
