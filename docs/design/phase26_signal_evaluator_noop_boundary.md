# Phase 26 Signal Evaluator No-Op Boundary Design

## 1. Purpose And Definition

Phase 26 Step 1 defines a documentation-only boundary for a future no-op signal
evaluator. That step added no evaluator implementation, production code, tests,
runtime behavior, signal computation, feature computation, strategy logic, risk
approval, execution behavior, broker behavior, persistence, live data, ML, or
LLM trading-path logic.

Phase 26 Step 2 reviews whether the existing `SignalEvaluationResult` contract
can safely represent a future no-op evaluator result. It adds no evaluator
implementation, no production behavior, no result contract changes, no no-op
marker, and no runtime or trading-path behavior. The review strengthens only
contract-surface tests to pin existing metadata-only facts.

For this project, a signal evaluator is a narrow deterministic boundary that
may later receive already-validated signal metadata, explicit input snapshot
metadata, and explicit UTC-aware timestamps, then construct advisory
`SignalEvaluationResult` metadata from those inputs.

A signal evaluator is not:

- a strategy
- a feature computer
- a signal generator
- a predictor
- a ranker
- a risk gate
- a trade decision-maker
- an execution planner
- a broker client
- a runtime or scheduler component
- a persistence writer
- an ML or LLM caller

At this stage, the future no-op evaluator is only a conceptual deterministic
metadata-producing boundary. It may later construct advisory
`SignalEvaluationResult` objects from explicit inputs, but it must not compute
real signals or imply any trading action.

## 2. Why Docs First

The word "evaluator" is semantically risky. It can easily drift into signal
computation, feature computation, strategy logic, ranking, risk approval,
execution intent creation, or trading decisions. Those behaviors belong behind
separate explicit contracts and later design reviews.

This phase documents the no-op boundary before implementation so the first
evaluator-shaped component remains deterministic, offline-safe, advisory, and
pre-risk. The design exists to prevent a no-op proof from quietly becoming a
signal engine or trading decision point.

## 3. Conceptual Future Inputs

A future no-op evaluator may conceptually accept:

- `ValidatedSignalDefinition`
- `SignalEvaluationInputSnapshot`
- explicit UTC-aware `as_of`
- explicit UTC-aware `evaluated_at`
- deterministic metadata already available through existing contracts

Those inputs must be supplied explicitly. The evaluator must not discover
inputs by reading live data clients, broker adapters, account state, runtime
state, environment variables, databases, files, caches, notebooks, research
scripts, ML outputs, or LLM responses.

This phase introduces no new production fields and no new contracts. Any future
input expansion must be handled by a later contract-first phase.

## 4. Conceptual Future Output

The future output may be:

- `SignalEvaluationResult`

The result is advisory metadata only. It is pre-risk. It is not a signal
firing, not a recommendation, not a trade approval, not an execution intent,
not an order request, and must not imply actionability.

A `SignalEvaluationResult` produced by any evaluator, including a future no-op
evaluator, is advisory metadata. Its existence does not constitute a signal
firing, recommendation, risk approval, execution instruction, or order request.

The output must remain traceable to explicit inputs and timestamps. It must not
approve trades, size trades, rank candidates, create execution intents, mutate
execution plans, reserve cash, access portfolio state, submit orders, or
interact with a broker.

## 5. No-Op Specialization

The future evaluator is "no-op" only because it proves the deterministic
input/output boundary without real signal behavior.

A future no-op evaluator does not:

- compute real signal values
- inspect live market data
- compute features
- rank candidates
- score candidates
- infer direction
- approve or reject trades
- create execution intents
- mutate execution plans
- submit or prepare orders

It exists only to prove that explicit deterministic inputs can produce explicit
advisory metadata output without hidden state or trading behavior.

Phase 26 Step 1 recorded an open design point: if `SignalEvaluationResult`
could not safely represent a no-op result without ambiguity, then the next
implementation phase should harden `SignalEvaluationResult` first instead of
adding an evaluator.

Phase 26 Step 2 resolves that point for the minimal future no-op evaluator:
the existing `SignalEvaluationResult` contract is sufficient. It already has
the metadata-only fields needed to preserve signal definition identity/version,
source artifact identity/version, input snapshot identity through
`input_fingerprint`, explicit `as_of`, explicit `evaluated_at`, advisory
`output_value`, `reason_code`, `diagnostics`, `assumptions`, and
`limitations`.

The future no-op result does not need `score`, `direction`, `confidence`,
`actionable`, `should_trade`, a no-op marker, `result_kind`, or
`evaluator_kind`. Adding those fields before a concrete need would create more
semantic surface area than the no-op boundary requires.

A future no-op result is not structurally distinguishable from a later real
evaluator result by field shape. That is acceptable for the first no-op
boundary because both remain advisory metadata. If distinction is needed, it
should come from explicit metadata values such as `evaluation_id`,
`input_fingerprint`, `output_value`, `reason_code`, `diagnostics`,
`assumptions`, and `limitations`, not from a field that invites branching or
actionability semantics.

No no-op marker is needed before a minimal no-op evaluator implementation. A
marker or kind field is not inherently trading behavior, but it risks becoming
a decision switch or actionability proxy if introduced too early. The safer
path is to keep the first no-op evaluator result empty/advisory in meaning
while using only the existing metadata fields.

## 6. Timestamp And Lookahead Invariants

`as_of` is the logical time the result describes. `evaluated_at` is the
UTC-aware time the evaluation occurred.

Future evaluator behavior must enforce:

```text
evaluated_at >= as_of
```

The evaluator must not consult any input whose `as_of` or observation timestamp
is greater than the result `as_of`. No lookahead bias is permitted.

The no-op evaluator trivially satisfies input-observation rules because it does
not inspect payload values, but it must still preserve explicit timestamps and
validate the timestamp relationship. It must not fill in missing timestamps
from wall-clock time.

## 7. Deterministic Guarantees

Future evaluator behavior must be:

- deterministic for identical inputs
- offline-safe
- credential-free
- free of hidden wall-clock access
- free of random behavior
- free of environment-variable driven behavior
- free of network calls
- free of file, database, or cache writes
- free of broker, account, position, order, or fill access
- free of input mutation
- free of ML inference or training
- free of LLM calls

The evaluator must not depend on mutable module globals, process-local
counters, random UUIDs, unordered external query results, machine-local
configuration, current working directory, scheduler state, open broker
connections, or available credentials.

## 8. Import And Dependency Boundaries

Future evaluator modules must not import from:

- broker modules
- Alpaca modules
- execution modules
- risk modules
- runtime or scheduler modules
- persistence modules
- ML modules
- LLM or agent modules

If any later evaluator needs one of these imports, that is a phase-scope
violation requiring a new design review.

## 9. Forbidden Result And Config Fields

Future no-op evaluator result/config surfaces must not contain fields or
concepts such as:

- score
- probability
- confidence
- rank
- priority
- signal_direction
- side
- buy, sell, long, or short action
- should_trade
- actionable
- fire or fired
- weight
- quantity
- notional
- cash
- buying_power
- portfolio
- position
- risk_approved
- approved or rejected
- risk_score
- execution_intent
- execution_plan
- order
- broker_order_id
- client_order_id
- account_id
- fill_id
- pnl
- return or performance
- feature values
- computed inputs
- ML model id, version, or prediction
- LLM prompt, output, or trace
- broker credentials or endpoints
- scheduler settings
- persistence paths, tables, or buckets
- live or paper trading mode toggles

Equivalent concepts are also forbidden even if named differently. A future
no-op evaluator must not expose trading action, ranking, sizing, risk,
execution, broker, persistence, runtime, ML, or LLM semantics through renamed
fields.

## 10. Advisory-Only Wording

A `SignalEvaluationResult` produced by any evaluator, including a future no-op
evaluator, is advisory metadata. Its existence does not constitute a signal
firing, recommendation, risk approval, execution instruction, or order request.

## 11. Pre-Risk Wording

Evaluator output is strictly pre-risk. No sizing decision, exposure
calculation, cash reservation, buying-power check, or portfolio-level reasoning
has occurred when a result is returned.

## 12. Future Phase Sketch

This sequence is non-binding:

1. Phase 26 Step 3 option A: add a minimal no-op evaluator contract using the
   existing `SignalEvaluationResult` fields.
2. Phase 26 Step 3 option B: if later review finds ambiguity not visible in
   this readiness review, harden `SignalEvaluationResult` before adding an
   evaluator.
3. A later phase: harden no-op evaluator traceability after any minimal
   evaluator contract exists.

Any future implementation phase must remain contract-first, test-first,
offline-safe, credential-free, broker-isolated, advisory, pre-risk, and outside
the LLM trading hot path.

## 13. Explicitly Out Of Scope

This phase does not add:

- production code
- signal evaluator implementation
- no-op evaluator class
- evaluator protocol
- result contract changes
- no-op marker
- signal computation
- feature computation
- strategy logic
- ranking or priority behavior
- signal-to-risk conversion
- risk approval
- execution intent creation
- execution-plan mutation
- portfolio mutation
- broker or Alpaca behavior
- order submission
- scheduler or runtime behavior
- persistence
- live data ingestion
- ML training or inference
- LLM trading-path logic
