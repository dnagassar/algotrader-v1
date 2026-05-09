# Phase 24 Signal Evaluation Result Boundary Design

## 1. Purpose

Phase 24 Step 1 defines a documentation-only boundary for a future
`SignalEvaluationResult` contract. The goal is to describe the advisory output
of deterministic signal evaluation before any evaluator, registry, feature
computation, strategy engine, signal-to-risk bridge, execution behavior, broker
behavior, persistence, runtime scheduling, ML, or LLM trading-path logic is
implemented.

Phase 24 Step 2 adds only the smallest immutable
`SignalEvaluationResult` contract for future advisory signal evaluation output.
It still adds no signal evaluator implementation, signal computation, strategy
implementation, feature computation, ranking or priority behavior,
execution-plan mutation, risk approval behavior, broker behavior, Alpaca
behavior, order submission, scheduler/runtime behavior, persistence
implementation, live data ingestion, ML training, or LLM trading-path logic.

The core rule is:

```text
ValidatedResearchArtifact is evidence.
ValidatedSignalDefinition is approved metadata.
SignalEvaluationResult is advisory deterministic output metadata.
Risk, execution, and broker layers remain separate.
```

## 2. What SignalEvaluationResult Represents

`SignalEvaluationResult` represents advisory deterministic output metadata from
applying a validated signal definition to explicit input snapshots at an
explicit as-of boundary. Phase 24 Step 2 adds the minimal metadata contract;
the evaluator that would produce it remains future work.

It may eventually record:

- which signal definition was evaluated
- which validated research artifact or source artifact supports that
  definition
- which explicit input snapshot or fingerprint was used
- what as-of timestamp bounded the admissible information
- when the evaluation report was produced
- what deterministic advisory output value, score, bucket, reason code,
  diagnostics, assumptions, and limitations were produced

The result is a report about one deterministic evaluation. It is timestamped,
as-of bounded, reproducible, and traceable to the signal definition id/version
and input snapshot or input fingerprint.

The result is advisory metadata only. It may inform a later explicitly designed
signal-to-risk bridge, but it does not approve a trade, create an order, create
an execution intent, mutate an execution plan, or interact with a broker.

## 3. What It Is Not

A future `SignalEvaluationResult` is not:

- an order
- a broker request
- a risk approval
- an execution intent
- an execution plan
- a portfolio mutation
- a ranking or priority decision
- an LLM decision

It also is not a strategy engine, not a feature computation result, not a live
recommendation, not a broker payload, not a persistence record by itself, and
not runtime scheduling behavior.

Any future field named score, bucket, reason, or diagnostic must remain
advisory signal metadata. It must not be interpreted as an execution priority,
trade approval, sizing instruction, or broker routing command.

## 4. Future Advisory Fields

A future result contract may include fields such as:

- `evaluation_id`
- `signal_id`
- `signal_version`
- `source_artifact_id`
- `source_artifact_version`
- `as_of`
- `evaluated_at`
- `input_snapshot_id`
- `input_fingerprint`
- `output_value`
- `score`, if deterministic and advisory
- `bucket`, if deterministic and advisory
- `reason_code`
- diagnostics or trace references
- assumptions
- limitations

Phase 24 Step 2 introduces the minimal implemented field set:

```text
SignalEvaluationResult(
    evaluation_id,
    signal_id,
    signal_version,
    source_artifact_id,
    source_artifact_version,
    as_of,
    evaluated_at,
    input_fingerprint,
    output_value,
    reason_code,
    diagnostics,
    assumptions,
    limitations,
)
```

The contract is frozen and slotted. Required strings reject empty values.
`diagnostics`, `assumptions`, and `limitations` are stored as immutable tuples
and preserve caller-provided order.

The field set should stay narrow. Fields should identify the evaluated
definition, the explicit inputs, the time boundary, and the advisory output.
They should not collapse downstream risk, execution, broker, portfolio,
ranking, persistence, or LLM concepts into the signal-evaluation layer.

`evaluation_id` should eventually be deterministic. A safe future derivation
could use stable normalized content such as the signal id, signal version,
source artifact id/version, input fingerprint, explicit `as_of`, evaluator
contract version, and deterministic output value. It should not come from
random UUIDs, mutable counters, hidden wall-clock reads, process state, or
network state.

## 5. Forbidden Fields And Behavior

A future `SignalEvaluationResult` must not include:

- `ProposedOrder`
- `order`
- `order_id`
- `client_order_id`
- `broker`
- `alpaca`
- `submit_order`
- symbol-specific order instruction
- side as execution command
- quantity
- cash
- buying_power
- reservation
- portfolio
- position mutation
- `risk_approved`
- `execution_intent`
- `execution_plan`
- fill
- priority
- rank as execution priority
- LLM-generated decision

It also must not include broker credentials, broker-native request or response
objects, account mutation state, venue routing fields, idempotency keys,
scheduler handles, persistence handles, live data clients, model prompts, model
completions, or references to mutable global state.

The absence of these fields is part of the contract. Signal evaluation produces
advisory outputs; downstream layers remain responsible for their own decisions
and traceability.

## 6. Clock And As-Of Requirements

The future result must carry an explicit `as_of` timestamp. The `as_of`
timestamp is the information boundary: no input observation used by the
evaluation may be after `as_of`.

The future result must also carry an explicit `evaluated_at` timestamp or
receive it from an injected deterministic clock in a future implementation.
Deterministic evaluation code must not read hidden system time to populate this
field.

All timestamps must be UTC-aware. Future contracts should reject naive
datetimes and non-UTC aware datetimes instead of normalizing them silently.

A future implementation should continue to use the shared Phase 23 time
boundary:

```text
require_utc_datetime(value) -> datetime
Clock.now() -> datetime
FixedClock(timestamp).now() -> datetime
assert_not_after_as_of(observed_at, as_of) -> None
```

Phase 24 Step 2 validates `as_of` and `evaluated_at` with
`require_utc_datetime(...)` and preserves the accepted datetime objects. It
does not define an ordering relation between `as_of` and `evaluated_at`; for
now they are independently required to be explicit UTC-aware timestamps.

The result boundary must not introduce hidden calls to:

- `datetime.now`
- `datetime.utcnow`
- `time.time`
- `time.monotonic`
- random generators
- UUID randomness
- environment-variable reads

Boundary code outside deterministic evaluation may obtain current time and pass
it in explicitly. Once inside deterministic signal evaluation, time is data.

## 7. Reproducibility Requirements

A future signal evaluation must be reproducible:

```text
same signal definition
+ same signal definition version
+ same source artifact reference
+ same input snapshot
+ same explicit input values
+ same as_of timestamp
+ same deterministic context
= same SignalEvaluationResult
```

The same signal definition, same inputs, and same `as_of` timestamp must
produce the same advisory result.

Future input snapshot fingerprints should be content-addressable. They should
identify the exact normalized input values, observation timestamps,
data-quality flags, and snapshot metadata used for the evaluation. If data is
revised, adjusted, restated, backfilled, or otherwise changed, the fingerprint
should change.

Future evaluation ids should be deterministic and traceable to stable content,
not random or process-local state.

Future evaluation must not depend on:

- network calls
- broker calls
- LLM calls
- live data calls
- mutable global state
- hidden database reads
- process-local caches that can change the result
- environment variables read inside deterministic layers
- random number generators
- non-deterministic ordering of mappings, sets, files, or external queries

If future evaluation needs configuration, that configuration should be
explicit, immutable for the evaluation, versioned, and included in
fingerprinting or traceability.

## 8. Relationship To The Future Pipeline

The future pipeline relationship is:

```text
ValidatedResearchArtifact
  -> ValidatedSignalDefinition
  -> explicit input snapshot + explicit UTC-aware time
  -> future SignalEvaluationResult
  -> future explicitly designed signal-to-risk bridge
  -> risk approval remains in the risk layer
  -> execution intent and plan creation remain in the execution layer
  -> broker behavior remains isolated
```

`ValidatedResearchArtifact` is evidence. It records reviewed research,
validation metadata, assumptions, limitations, metrics, and approved advisory
uses.

`ValidatedSignalDefinition` is approved metadata. It identifies a deterministic
signal rule candidate, its source artifact id/version, required inputs,
evaluation rule reference, approved advisory uses, assumptions, and
limitations.

`SignalEvaluationResult` is future advisory deterministic output. It reports
what happened when one validated signal definition was applied to explicit
inputs at an explicit `as_of` boundary.

A future signal-to-risk bridge may consume `SignalEvaluationResult` only after
a separate design and implementation phase defines that bridge. The risk layer
remains responsible for risk approval. The execution layer remains responsible
for execution intents and execution plans. The broker layer remains isolated
behind broker-specific boundaries.

## 9. LLM Boundary

LLMs may assist with:

- explaining completed evaluation reports
- summarizing assumptions and limitations for human review
- drafting research narration
- helping humans inspect diagnostics after deterministic evaluation is done

LLMs may not:

- compute live signal outputs
- generate live trade decisions
- approve trades
- mutate execution plans
- rank execution candidates
- bypass deterministic risk checks
- access live broker state in the trading process
- access live quote state in the trading process
- create broker requests
- submit orders
- mutate portfolio state

LLM output remains research, documentation, review commentary, or report
narration unless a human-reviewed deterministic artifact later promotes a rule
through explicit contracts and tests. LLMs remain out of the trading hot path.

## 10. Dependency Direction

The future result boundary should sit after validated signal definition
metadata and before any future signal-to-risk bridge. It remains advisory and
deterministic.

Allowed conceptual direction:

```text
validated research artifact metadata
  -> validated signal definition metadata
  -> explicit input snapshot
  -> explicit clock/as-of boundary
  -> future SignalEvaluationResult
  -> future explicitly designed Signal -> Risk bridge
```

Forbidden direct dependencies for a future `SignalEvaluationResult` contract:

- broker modules
- Alpaca modules
- execution modules
- execution-planning modules
- risk approval modules
- portfolio mutation modules
- scheduler/runtime modules
- persistence writers
- live data clients
- backtest engines
- ML training modules
- LLM clients or agents

The deterministic core consumes only explicit promoted contracts. A future
result object must remain an advisory report until later phases explicitly
define how advisory evaluations may cross into risk.

## 11. Explicitly Out Of Scope

Phase 24 Step 2 does not add:

- signal evaluator registry
- signal evaluator implementation
- signal computation
- feature computation
- strategy engine
- signal-to-risk bridge
- ranking or priority policy
- risk approval
- execution intent creation
- execution planning changes
- broker integration
- Alpaca changes
- order submission
- scheduler/runtime behavior
- persistence implementation
- live data ingestion
- ML training
- LLM trading-path logic

It also does not add runtime configuration, system-time reads, data ingestion,
broker behavior, credentials, network calls, or normal-pytest dependency on
external services.

## 12. Future Implementation Phases

Future implementation should stay contract-first and test-first. A safe future
sequence would be:

1. Add synthetic input snapshot contracts and deterministic fingerprinting
   rules.
2. Add focused tests proving reproducibility, clock injection, forbidden-field
   absence, and dependency independence.
3. Add a small evaluator registry only after result and snapshot contracts are
   stable.
4. Add one deterministic evaluator implementation with explicit synthetic
   inputs only.
5. Only later design a signal-to-risk bridge for advisory evaluation outputs.

No future implementation should combine signal evaluation with broker wiring,
runtime scheduling, persistence, live data ingestion, feature computation, ML
training, order submission, risk approval bypasses, execution-plan mutation,
ranking or priority policy, or LLM trading-path behavior.
