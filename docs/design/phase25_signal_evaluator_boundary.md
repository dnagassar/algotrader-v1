# Phase 25 Signal Evaluator Boundary Design

## 1. Purpose

Phase 25 Step 1 defines a documentation-only boundary for a future deterministic
signal evaluator. No evaluator implementation exists in this phase, and no
production code, tests, runtime behavior, signal computation, strategy logic,
risk approval, execution behavior, broker behavior, persistence, live data, ML,
or LLM trading-path logic is added.

Phase 25 Step 2 adds only the smallest immutable input snapshot/reference
contract for that future evaluator boundary. It still adds no signal evaluator
implementation, signal computation, feature computation, strategy logic,
ranking or priority behavior, signal-to-risk conversion, risk approval,
execution intent creation, execution-plan mutation, portfolio mutation, broker
or Alpaca behavior, order submission, scheduler/runtime behavior, persistence
writes, live data ingestion, network calls, ML training or inference, or LLM
trading-path logic.

Phase 25 Step 3 hardens `SignalEvaluationInputSnapshot` traceability with tests
and documentation only. It changes no production source and adds no production
behavior. The snapshot remains metadata/reference-only, not a signal evaluator,
not signal computation, not feature computation, not live-data access, not risk
approval, not execution intent creation, not execution-plan mutation, not
broker or Alpaca behavior, not scheduler/runtime/persistence behavior, and not
ML or LLM trading-path logic.

The future evaluator will eventually transform a validated signal definition
plus explicit deterministic input snapshots into advisory
`SignalEvaluationResult` objects.

The boundary goal is narrow:

```text
ValidatedSignalDefinition
  + explicit deterministic input snapshot
  + explicit UTC-aware as_of timestamp
  + explicit deterministic evaluated_at timestamp or clock
  -> SignalEvaluationResult
```

The future evaluator must remain deterministic, offline-safe, and explicit. It
must use explicit as-of timestamps, prevent lookahead bias, and avoid all hidden
state. It must not reach into live data, broker state, account state, position
state, runtime state, persistence state, or LLM outputs.

`SignalEvaluationResult` remains advisory and pre-risk. A signal-evaluation
result is not a trade approval, not an execution instruction, not an order
request, and not a broker payload.

## 2. Future Inputs

Future evaluator inputs may include:

- `ValidatedSignalDefinition`
- explicit deterministic market or input snapshot references
- explicit `as_of` timestamp
- deterministic clock or explicit `evaluated_at` timestamp
- explicit input bundle or input snapshot identity
- optional parameter or config metadata, if later introduced through a small
  immutable contract

The future evaluator should receive inputs as data. It should not discover
inputs by reading live data clients, broker adapters, account state, runtime
state, environment variables, databases, files, notebooks, research scripts, or
LLM responses from inside the deterministic evaluation path.

`ValidatedSignalDefinition` should identify the approved signal metadata:
signal id, version, source validated research artifact id/version, required
inputs, deterministic evaluation rule reference, assumptions, limitations, and
approved advisory uses.

Input snapshot references should identify the exact deterministic data used for
evaluation. A future snapshot contract may include normalized observation
values, observation timestamps, data-quality flags, source identifiers,
adjustment or revision metadata, and content fingerprints.

Phase 25 Step 2 introduces the minimal implemented input snapshot contract:

```text
SignalEvaluationInputSnapshot(
    snapshot_id,
    as_of,
    required_input_names,
    source_ids,
)
```

`SignalEvaluationInputSnapshot` is metadata/reference-only. It records stable
snapshot identity, an explicit UTC-aware `as_of` timestamp, the deterministic
ordered input names required for evaluation, and deterministic ordered source
identifiers. It does not store live observations, compute features, compute
signals, open files, fetch live data, read broker state, persist anything, or
call LLMs.

`as_of` is the information boundary. It must be explicit and UTC-aware.
`evaluated_at` is the report-production timestamp. It must also be explicit and
UTC-aware, either supplied directly or obtained from an injected deterministic
clock in a future implementation.

Optional configuration, if introduced later, should be frozen, explicit,
versioned where useful, and included in traceability or fingerprinting when it
can affect the result.

## 3. Future Output

The future evaluator output should be `SignalEvaluationResult`.

The output is advisory metadata only. It should be traceable to:

- signal definition id
- signal definition version
- source validated research artifact id
- source validated research artifact version
- input snapshot id or fingerprint
- explicit `as_of`
- explicit `evaluated_at`
- deterministic output value
- reason code
- diagnostics, assumptions, and limitations

The output should preserve the Phase 24 result boundary: it reports what was
computed by applying an approved signal definition to explicit inputs at an
explicit time boundary. It does not approve risk, size a trade, rank execution
candidates, create an execution intent, mutate an execution plan, submit an
order, or interact with a broker.

A future `SignalEvaluationResult` is not:

- an execution signal
- a trade approval
- an order request
- a broker request
- an execution intent
- an execution plan
- a portfolio mutation
- a ranking or priority decision
- an LLM decision

## 4. Required Deterministic Guarantees

A future signal evaluator must guarantee:

- same inputs produce the same result
- no hidden wall-clock access
- no environment-variable driven behavior
- no random behavior
- no network calls
- no file writes
- no database writes
- no broker, account, position, order, or fill access
- no mutation of input definitions or snapshots
- no LLM calls
- no ML training or inference unless later promoted through explicit
  deterministic contracts

The evaluator must be a pure deterministic boundary over the supplied inputs.
It should not depend on mutable module globals, process-local counters, random
UUIDs, unordered external query results, local machine configuration, available
credentials, current working directory, runtime scheduler state, or open broker
connections.

If future evaluator code needs helper registries or rule lookup, those helpers
should be deterministic, explicit, offline, test-first, and bounded by small
contracts. The lookup mechanism must not become a hidden dependency on live
services, notebooks, arbitrary file loading, database state, or LLM output.

## 5. As-Of And Lookahead Rules

All observations used by evaluation must satisfy:

```text
observed_at <= as_of
```

Future observations must be rejected. The evaluator must not infer from data
after `as_of`, must not use retrospectively revised data unless the revision is
explicitly part of the supplied snapshot, and must not silently backfill or
repair inputs from live or mutable sources.

The future evaluator should use the existing deterministic time contract:

```text
require_utc_datetime(value) -> datetime
Clock.now() -> datetime
FixedClock(timestamp).now() -> datetime
assert_not_after_as_of(observed_at, as_of) -> None
```

`as_of` should be validated as explicit and UTC-aware. `evaluated_at` should be
explicit and UTC-aware. Hidden calls to `datetime.now`, `datetime.utcnow`,
`time.time`, `time.monotonic`, random generators, UUID randomness, or
environment-variable reads are not allowed in the deterministic evaluator.

If a future input snapshot contains windows, aggregates, adjusted values,
features, or derived observations, the snapshot contract should make the
observation boundaries traceable enough for the evaluator to reject lookahead
data. Derived values should be admissible only when their source observations
are all at or before `as_of`.

## 6. Boundary With Existing Contracts

`ValidatedResearchArtifact` is evidence. It records reviewed research,
validation metadata, metrics, assumptions, limitations, and approved advisory
uses. The future evaluator should not execute research artifacts or import
research workflows. It should trace to source artifact id/version through the
validated signal definition and result metadata.

`ValidatedSignalDefinition` is approved signal metadata. It identifies a
deterministic signal rule candidate, source artifact id/version, required
inputs, evaluation rule reference, approved advisory uses, assumptions, and
limitations. It does not evaluate signals by itself.

`SignalEvaluationResult` is advisory output metadata. It records the result of
one deterministic evaluation against explicit inputs and time boundaries. It is
not risk approval, execution intent creation, execution planning, broker
routing, order submission, or portfolio mutation.

The deterministic time contracts provide shared timestamp validation,
deterministic clock injection, and the `observed_at <= as_of` guard. The future
evaluator should consume those primitives instead of reading wall-clock time.

Future input snapshot contracts should sit between validated signal definitions
and `SignalEvaluationResult`. They should identify exact inputs, observation
times, snapshot identity, and fingerprints. They should be small, immutable,
explicit, offline-safe, and tested before any evaluator implementation depends
on them.

Phase 25 Step 2 starts that input side with
`SignalEvaluationInputSnapshot`. It is frozen and slotted, validates `as_of`
with the shared UTC-aware time contract, rejects naive and non-UTC datetimes,
rejects empty or blank trace strings, converts iterable metadata fields to
tuples, preserves tuple ordering, preserves accepted string values exactly, and
performs no I/O, network, broker, scheduler/runtime, persistence, environment,
wall-clock, random, ML, LLM, signal-computation, feature-computation, or
strategy behavior.

Phase 25 Step 3 pins that traceability more explicitly. Tests prove exact
`as_of` identity preservation, exact `snapshot_id` preservation, exact
`required_input_names` and `source_ids` string preservation, deterministic
ordering for both tuple fields, tuple immutability after construction, and
input-list mutation isolation. They also pin that the snapshot has no signal
output behavior, no score/direction/confidence fields, no order/risk/execution
fields, no broker/account/position/fill fields, no portfolio/cash/buying-power
fields, no scheduler/runtime/persistence fields, no ML/LLM fields, no
dependency on `SignalEvaluationResult`, no downstream risk/execution/broker or
runtime dependencies, and no hidden wall-clock, random, network/socket,
filesystem-write, environment-variable, broker SDK, or Alpaca access.

The intended conceptual flow is:

```text
ValidatedResearchArtifact
  -> ValidatedSignalDefinition
  -> SignalEvaluationInputSnapshot
  -> explicit UTC-aware as_of and evaluated_at
  -> future deterministic signal evaluator
  -> SignalEvaluationResult
  -> future explicitly designed signal-to-risk bridge
  -> risk approval remains in the risk layer
  -> execution remains in the execution layer
  -> broker behavior remains isolated
```

## 7. Explicitly Out Of Scope

Phase 25 Step 3 does not add:

- signal evaluator implementation
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

It also does not add production code, runtime configuration, evaluator
registries, file/database writes, network calls, credentials, paper/live broker
connectivity, normal-pytest integration behavior, or any behavior that can
place LLMs in the trading hot path.

## 8. Future Phase Sketch

Future work should stay non-binding, contract-first, and test-first. A safe
possible sequence is:

1. A later phase: add a minimal no-op evaluator contract only after the input
   and result boundaries are stable.
2. A later phase: add one narrow deterministic evaluator implementation with
   focused tests and documentation.

Later phases may design deterministic rule dispatch, one narrow evaluator, or a
signal-evaluation-to-risk bridge only after the input, output, time, and
traceability contracts are stable. No future phase should combine evaluator
work with live data ingestion, broker wiring, order submission, risk bypasses,
execution-plan mutation, persistence writes, ML training or inference, runtime
scheduling, or LLM trading-path decisions.
