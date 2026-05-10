# Phase 27 Real Signal Evaluator Admission Boundary Design

## 1. Purpose

Phase 27 Step 1 defines an admission boundary for any future real
deterministic signal evaluator. The system now has a no-op evaluator seam, but
real signal computation remains forbidden until explicit admission criteria are
met and documented.

This phase is documentation-only. It adds no production code, tests, real
signal evaluator implementation, signal computation, feature computation,
strategy logic, ranking or priority behavior, signal-to-risk conversion, risk
approval, execution intent creation, execution-plan mutation, portfolio
mutation, broker or Alpaca behavior, order submission, scheduler/runtime
behavior, persistence, live data ingestion, ML training or inference, or LLM
trading-path logic.

## 2. Why This Boundary Is Needed

A real signal evaluator is the first evaluator-shaped component that could
accidentally become a trading decision point. Without an admission boundary, it
could quietly introduce:

- strategy logic
- feature computation
- predictive behavior
- ranking
- direction
- actionability
- risk-like semantics
- lookahead bias
- hidden data access

This phase exists to prevent that drift before implementation. A future real
evaluator must be admitted only after its inputs, timestamps, output meaning,
side-effect boundaries, and test obligations are explicit.

## 3. Required Prerequisites

Before any real evaluator is implemented, the design must require:

- a specific `ValidatedSignalDefinition`
- a supporting `ValidatedResearchArtifact`
- an explicit deterministic input contract for actual input values, not just
  references
- clear input timestamps or observation timestamps for each consumed value
- explicit UTC-aware `as_of`
- explicit UTC-aware `evaluated_at`
- deterministic behavior for identical inputs
- documented approved advisory use
- documented assumptions and limitations
- test coverage for lookahead prevention
- no broker, runtime, scheduler, or persistence dependencies

These prerequisites are admission criteria, not implementation instructions.
If any prerequisite is missing, real evaluator implementation remains out of
scope.

## 4. Input References Versus Input Values

`SignalEvaluationInputSnapshot` currently provides metadata and reference
traceability only. Its fields are:

- `snapshot_id`
- `as_of`
- `required_input_names`
- `source_ids`

It does not carry actual feature values, market observations, computed inputs,
bar payloads, quote payloads, or other values that a real evaluator could
compute from.

Therefore, a future real evaluator likely needs a separate deterministic
input-value contract before it can compute anything. That contract should
represent explicit values and observation timestamps without live data lookup,
broker access, persistence reads/writes, ML inference, or LLM calls.

This phase does not design or implement that contract. It records the need so a
future real evaluator is not built on metadata references alone.

## 5. Real Evaluator Admission Criteria

A future real evaluator may be considered only when all of the following are
documented:

- which validated signal definition it implements
- which validated research artifact supports it
- which exact deterministic inputs it consumes
- how each input is timestamped
- how each input is proven available at or before `as_of`
- what the output value means
- what the output value does not mean
- what assumptions apply
- what limitations apply
- what tests prove deterministic behavior
- what tests prove no lookahead bias
- what tests prove no side effects
- what tests prove no trading-path dependencies

Admission does not imply the evaluator may create trades. It only means the
project has enough deterministic contract surface to consider a future
advisory evaluator implementation.

## 6. Output Semantics

Even a future real evaluator output remains:

- advisory
- pre-risk
- not a recommendation
- not a trade approval
- not an execution intent
- not an order request
- not portfolio-aware
- not broker-aware
- not actionability by itself

The output may describe a deterministic advisory evaluation result, but it must
not approve a trade, size a trade, reserve cash, route to a broker, create an
execution intent, mutate an execution plan, or bypass risk checks.

## 7. Forbidden Fields And Behavior

Future evaluator outputs and configs must not include fields or concepts such
as:

- `should_trade`
- `actionable`
- `approved`
- `risk_approved`
- order fields
- broker fields
- position fields
- portfolio fields
- cash fields
- buying-power fields
- execution intent references
- execution plan references
- runtime fields
- scheduler fields
- persistence targets
- live or paper trading mode toggles
- LLM prompt, output, or trace
- broker credentials or endpoints

Equivalent concepts are also forbidden if renamed. A future evaluator must not
smuggle trading action, risk approval, broker routing, persistence behavior,
runtime behavior, or LLM trading-path logic through a different field name.

If score, direction, or confidence are ever considered, that requires a
separate design phase. Any such fields must remain advisory only and must not
be used as a direct risk approval, execution instruction, ranking policy,
broker request, or trade recommendation.

## 8. Lookahead-Bias Rules

Future real evaluators must follow strict lookahead rules:

- every input observation must have an observation timestamp
- every observation used must satisfy `observed_at <= as_of`
- the evaluator must reject any future observation
- `evaluated_at` must be UTC-aware
- `evaluated_at` must not be earlier than `as_of`
- the evaluator must not fetch newer data internally
- the evaluator must not rely on wall-clock time
- the evaluator must not infer from data unavailable at `as_of`

No evaluator may fill missing timestamps from the system clock or silently
accept untimestamped observations. Timestamp provenance must be explicit and
testable.

## 9. Determinism And Side-Effect Rules

Future real evaluators must be pure from the perspective of the deterministic
core. They must:

- use only explicit inputs
- be deterministic for identical inputs
- avoid network calls
- avoid live data access
- avoid file writes
- avoid database writes
- avoid cache writes
- avoid environment-variable driven behavior
- avoid random behavior unless explicitly seeded and approved in a later design
  phase
- avoid broker, account, position, order, or fill access
- avoid ML calls in the trading path
- avoid LLM calls in the trading path

Any future evaluator that needs runtime state, persistence, a broker, account
state, portfolio state, model inference, or LLM output is not admitted by this
boundary and requires a separate design review.

## 10. Relationship To Existing Contracts

`ValidatedResearchArtifact` is supporting evidence. It records reviewed
research metadata, assumptions, limitations, and validation context, but it is
not a live signal, a risk approval, or an execution decision.

`ValidatedSignalDefinition` is the promoted signal metadata contract. It may
describe the future advisory signal definition, but it does not compute signal
values, inspect market observations, or create execution intents.

`SignalEvaluationInputSnapshot` provides input reference traceability. It can
identify which named inputs and source ids were intended for evaluation, but it
does not carry actual deterministic input values.

`SignalEvaluationResult` is the advisory output contract. It can preserve
traceability, timestamps, diagnostics, assumptions, limitations, and advisory
output metadata, but it is not a recommendation, risk approval, execution
intent, order request, or broker payload.

`NoOpSignalEvaluator` proves the evaluator input/output seam with explicit
metadata and timestamps. It performs no real computation and remains the only
evaluator implementation at this stage.

The deterministic time contracts provide UTC-aware timestamp validation,
fixed-clock testing support, and lookahead helpers. Future real evaluator
inputs must preserve explicit observation timestamps that can be checked
against `as_of`.

Future deterministic input-value contracts are needed before real signal
computation can be admitted. They should represent actual values and their
observation times without hidden data access or trading-path dependencies.

## 11. Non-Binding Future Phase Sketch

Possible future phases include:

1. Phase 27 Step 2: deterministic signal input value boundary design.
2. Phase 27 Step 3: minimal immutable signal input value contract.
3. Phase 27 Step 4: input value traceability and lookahead hardening.
4. A later phase: first real evaluator design.
5. A later phase: first real evaluator implementation.

This sequence is non-binding. Any future work must remain contract-first,
test-first, deterministic, offline-safe, credential-free, broker-isolated,
advisory, pre-risk, and outside the LLM trading hot path.
