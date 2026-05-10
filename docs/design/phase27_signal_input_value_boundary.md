# Phase 27 Signal Input Value Boundary Design

## 1. Purpose

Phase 27 Step 2 designs the future deterministic signal input-value boundary.
The project needs this boundary before any real evaluator can compute signals
because the current evaluator input snapshot records references only, not the
observed values a real evaluator would consume.

This phase only designs the boundary. It does not implement input values,
input-value contracts, evaluator behavior, signal computation, feature
computation, strategy logic, ranking or priority behavior, signal-to-risk
conversion, risk approval, execution intent creation, execution-plan mutation,
portfolio mutation, broker or Alpaca behavior, order submission,
scheduler/runtime behavior, persistence, live data ingestion, ML training or
inference, or LLM trading-path logic.

Phase 27 Step 3 adds the first minimal immutable input-value contract:
`SignalInputValue`. It carries one explicit observed value with source and
timestamp traceability only. It does not implement a real evaluator, compute
signals or features, score, rank, infer direction, recommend trades, approve
risk, create execution intents, mutate execution plans, access live data, route
to brokers or Alpaca, submit orders, use scheduler/runtime/persistence, run ML,
or use LLMs in the trading path.

## 2. Snapshot References Versus Input Values

`SignalEvaluationInputSnapshot` is reference metadata. It provides:

- snapshot identity through `snapshot_id`
- required input names through `required_input_names`
- source ids through `source_ids`
- an explicit UTC-aware `as_of`
- no actual observed values

It can prove which inputs and sources were referenced, but it cannot support
real signal computation by itself.

A future deterministic input-value contract would represent actual
deterministic observed values. Conceptually, it would provide:

- explicit observed values
- observation timestamps
- source traceability
- value type constraints
- no-lookahead validation support
- a shape suitable for future real evaluator computation

This distinction matters: a real evaluator must compute only from explicit
observed values that are proven available at or before its `as_of`, not from
reference names that imply values exist elsewhere.

## 3. What Future Input Values May Represent

Future input values may represent deterministic, precomputed, explicit
observations such as:

- market prices
- bar fields
- quote fields
- volume
- feature values, only if feature computation is separately designed and
  promoted
- static metadata, if timestamped and source-traceable

This phase does not define a final production contract. The list is conceptual
and exists to frame the next design step without admitting computation or live
data access.

## 4. Candidate Fields For A Future Contract

A future minimal immutable contract should likely consider:

- input name
- observed value
- `observed_at` timestamp
- source id
- maybe symbol or instrument id if already supported by existing domain
  contracts
- maybe value type or unit metadata
- maybe quality or status metadata

These are design candidates, not implementation requirements. The next phase
must decide the smallest safe field set before production code is added.

Phase 27 Step 3 chooses the first minimal field set only:

- `name`
- `value`
- `observed_at`
- `source_id`

Optional unit, quality, symbol, and instrument fields remain deferred. The
first value surface is limited to deterministic scalar values and does not
model collections, bars, quotes, feature vectors, unavailable values, units, or
timeframes.

## 5. Timestamp And Lookahead Rules

Future input values must support strict timestamp validation:

- `observed_at` must be UTC-aware
- naive datetimes must be rejected
- non-UTC datetimes must be rejected
- every `observed_at` used by an evaluator must satisfy
  `observed_at <= evaluator as_of`
- future observations must be rejected
- hidden wall-clock reads are forbidden
- fetching newer data internally is forbidden
- inference from unavailable future data is forbidden

The input-value boundary must make lookahead checks simple, explicit, and
testable. No evaluator may fill missing observation timestamps from the system
clock or silently accept untimestamped values.

`SignalInputValue` validates only its own `observed_at` timestamp. It does not
perform lookahead validation against an evaluator `as_of` because it has no
`as_of` field. Assembly-level lookahead validation remains future work.

## 6. Determinism Rules

Future input-value contracts and evaluators must:

- use only explicit inputs
- preserve ordering where ordering matters
- preserve exact value identity or exact value representation where appropriate
- be immutable
- avoid mutable containers
- avoid environment-variable driven behavior
- avoid random behavior
- avoid network calls
- avoid file writes
- avoid database writes
- avoid cache writes
- avoid broker, account, position, order, or fill access
- avoid ML calls in the trading path
- avoid LLM calls in the trading path

The contract should make accidental side effects difficult. A deterministic
input value is data already admitted into the deterministic core, not a handle
to fetch data later.

## 7. Value Representation Design Questions

The production representation is intentionally undecided. The next design phase
should answer questions such as:

- should values be `Decimal`, `int`, `str`, `bool`, or a constrained union?
- should floats be forbidden or isolated because of reproducibility concerns?
- should bars and quotes be referenced by existing domain objects or flattened
  into metadata?
- should feature values require a separate feature contract first?
- how should missing or unavailable values be represented?
- how should units, currency, and timeframe be represented?
- how should input ordering be preserved?

The current project docs do not force a final answer yet. Avoiding speculative
final decisions keeps the eventual implementation small and testable.

## 8. Relationship To Existing Contracts

`ValidatedResearchArtifact` remains supporting evidence. It can explain where
a future signal came from and what assumptions or limitations apply, but it
does not provide runtime input values.

`ValidatedSignalDefinition` remains promoted signal metadata. It may name
required inputs, output type, advisory use, assumptions, and limitations, but
it does not carry observed market values.

`SignalEvaluationInputSnapshot` remains reference metadata. It can identify a
snapshot id, required input names, source ids, and `as_of`, but it does not
contain actual values suitable for computation.

`SignalEvaluationResult` remains advisory output metadata. It can preserve the
trace from a future evaluator result, but it is not a recommendation, risk
approval, execution intent, order request, or broker payload.

`NoOpSignalEvaluator` remains the only evaluator-shaped implementation. It
proves the input/output seam without real signal computation and does not
consume input values.

The deterministic time contracts provide UTC-aware timestamp validation and
lookahead helpers. A future input-value contract should use those timestamp
rules so evaluator tests can prove every observation was available at or before
`as_of`.

Future real signal evaluators remain blocked until deterministic input values
exist and the real evaluator admission criteria are met. Future feature
contracts, if needed, must be designed separately before feature values are
promoted into evaluator inputs.

`SignalInputValue` is now the minimal observed-value contract. It is not an
input collection, not an evaluator input bundle, not a feature contract, not a
real evaluator, and not sufficient by itself to admit real signal computation.

## 9. Explicitly Out Of Scope

Phase 27 Step 2 does not add:

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

Phase 27 Step 3 adds only the minimal `SignalInputValue` implementation. It
still does not add evaluator implementation, signal computation, feature
computation, strategy logic, score/direction/confidence/actionability behavior,
risk approval, execution intent creation, broker or Alpaca behavior, order
submission, runtime/scheduler behavior, persistence, live data ingestion, ML,
or LLM trading-path behavior.

## 10. Non-Binding Future Phase Sketch

Possible future phases include:

1. Phase 27 Step 4: input value traceability and lookahead hardening.
2. Phase 28 Step 1: first real evaluator design, still docs-only.
3. A later phase: minimal deterministic evaluator for one validated signal
   definition.

This sequence is non-binding. Any future work must remain contract-first,
test-first, deterministic, offline-safe, credential-free, broker-isolated,
advisory, pre-risk, and outside the LLM trading hot path.
