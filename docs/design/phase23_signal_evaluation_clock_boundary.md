# Phase 23 Signal Evaluation Clock Boundary Design

## 1. Purpose

Phase 23 Step 1 defines a documentation-only boundary for future deterministic
signal evaluation. It explains how a future evaluator may consume approved
`ValidatedSignalDefinition` metadata plus explicit input snapshots while
keeping time, as-of semantics, reproducibility, and lookahead-bias controls
explicit by construction.

Phase 23 Step 1 adds no production code, tests, runtime behavior, signal
evaluator implementation, signal computation, clock implementation, feature
computation, strategy implementation, ranking or priority behavior, execution
intent creation, execution-plan mutation, risk approval behavior, broker
behavior, Alpaca behavior, order submission, scheduler/runtime behavior,
persistence implementation, live data ingestion, ML training, or LLM
trading-path logic.

The core rule is:

```text
Validated signal definitions describe approved metadata.
Explicit input snapshots provide the data.
Explicit time controls what data is admissible.
Future signal evaluations are advisory metadata only.
```

## 2. What Deterministic Signal Evaluation Means

Deterministic signal evaluation means a pure future evaluator receives a
validated signal definition plus explicit inputs and produces advisory
signal-evaluation metadata. The same definition, the same input snapshot, and
the same as-of timestamp must produce the same evaluation result.

A future deterministic signal evaluator may:

- read an approved `ValidatedSignalDefinition` by id/version or object
- read explicit feature or input values supplied by the caller
- check that all input observations are admissible at the explicit `as_of`
  timestamp
- produce a deterministic signal value, score, bucket, reason code, or
  explanation code
- attach input and evaluation fingerprints for traceability

A future deterministic signal evaluator must not:

- create orders
- approve trades
- mutate execution plans
- reserve cash or buying power
- rank execution candidates
- submit broker requests
- call live data sources
- call brokers
- call LLMs
- read hidden runtime state

The output is an advisory evaluation report, not an execution decision.

## 3. Boundary Comparisons

A deterministic signal evaluation differs from a validated signal definition.
`ValidatedSignalDefinition` is metadata that describes a reviewed rule,
required inputs, source artifact ids, assumptions, and limitations. Evaluation
is the future act of applying that definition to explicit inputs at an explicit
as-of time.

A deterministic signal evaluation differs from raw research output. Raw
research may include notebooks, exploratory scripts, charts, backtests,
walk-forward experiments, LLM-assisted summaries, and hypotheses. Those outputs
remain advisory until promoted into reviewed artifacts and definitions.

A deterministic signal evaluation differs from feature computation. Feature
computation derives values from raw or windowed data. Evaluation consumes
already explicit feature or input values, or explicit references to snapshots
whose construction is separately defined.

A deterministic signal evaluation differs from strategy logic. Strategy logic
may combine multiple signals, portfolio context, sizing, timing rules,
execution preferences, and allocation decisions. Signal evaluation is narrower:
it applies one approved definition to explicit inputs and emits advisory
metadata.

A deterministic signal evaluation differs from risk evaluation. Risk evaluation
checks a proposed order or future explicit risk input against account,
portfolio, and policy constraints. Signal evaluation must not produce a risk
approval and must not bypass deterministic risk checks.

A deterministic signal evaluation differs from execution intent creation.
`ExecutionIntent` is an internal pre-submission wrapper for a risk-approved
source row. Signal evaluation must not create or mutate execution intents.

A deterministic signal evaluation differs from execution planning.
`ExecutionPlan` and planning policies operate on execution intents before any
broker-facing request is constructed. Signal evaluation must not create,
accept, skip, cap, rank, prioritize, or mutate execution plans.

A deterministic signal evaluation differs from broker order submission. Broker
submission is broker-facing behavior. Signal evaluation must not construct
broker-native orders, broker requests, Alpaca payloads, order IDs, client order
IDs, fills, or account mutations.

## 4. Future Evaluator Inputs

A future evaluator input contract may include:

- validated signal definition id and version
- validated signal definition object
- explicit feature or input values
- explicit observation timestamp for each input value or input window
- explicit `as_of` timestamp
- explicit evaluation timestamp supplied by a boundary clock or caller
- deterministic context such as regime label, market-session label, or
  data-quality flags
- input snapshot reference
- input snapshot fingerprint
- definition assumptions and limitations references

The evaluator should not discover missing inputs by reading live systems. If an
input is required by the validated definition, the caller must supply that input
or a traceable snapshot reference that is already admissible at `as_of`.

## 5. Future Evaluator Outputs

A future evaluator output contract may include only advisory metadata such as:

- signal id
- signal version
- evaluation timestamp
- as-of timestamp
- deterministic signal value
- deterministic score
- deterministic bucket
- reason code
- explanation code
- input snapshot fingerprint
- evaluation fingerprint or id
- assumptions references
- limitations references

Any future score or bucket is advisory signal metadata only. It is not an
execution ranking, not an order priority, not a risk approval, and not a broker
instruction.

## 6. Fields And Behavior That Must Not Appear

A future signal evaluation output must not include:

- `ProposedOrder`
- order
- `order_id`
- `client_order_id`
- broker request
- broker-native object
- Alpaca request or response object
- symbol-specific order instruction
- side as an execution command
- quantity
- cash reservation
- buying-power reservation
- portfolio mutation
- position mutation
- risk approval
- execution intent
- execution plan
- accepted/skipped execution-planning decision
- fill
- ranking decision
- priority decision
- LLM-generated trade decision

It also must not include broker credentials, account state, live quote state,
runtime scheduler state, persistence handles, idempotency keys, venue routing
fields, or hidden mutable state references.

## 7. Clock And As-Of Rules

Any time-dependent deterministic component must receive time explicitly. A
future evaluator must not call wall-clock or runtime-state APIs internally to
decide what data is available, which rule version is active, or what result id
to produce.

Future clock behavior should be injectable at an explicit boundary. Boundary
code may obtain the current time, convert it to a timezone-aware timestamp, and
pass it into deterministic contracts. Deterministic signal, risk, and
orchestration layers should receive that timestamp as data.

Direct calls to the following should be forbidden in deterministic signal,
risk, and orchestration layers except in explicit boundary modules:

- `datetime.now`
- `datetime.utcnow`
- `time.time`
- `time.monotonic`
- random generators
- UUID randomness
- environment-variable reads

All trading-relevant timestamps should be timezone-aware. Internal contracts
should prefer UTC. Naive datetimes should be rejected by future contracts
instead of being interpreted implicitly.

The `as_of` timestamp is the information boundary for an evaluation. Inputs
must be known, available, or traceable as of that timestamp. The observation
timestamp records when the input was observed or when the input window ended.
The evaluation timestamp records when the evaluation report was produced or
requested. These timestamps are related but not interchangeable.

## 8. Lookahead-Bias Prevention

Future evaluators must reject input observations timestamped after `as_of`.
This includes direct input values, feature values, and snapshot members whose
availability timestamp is later than the evaluation boundary.

Input snapshots must be explicit. A future evaluator should receive a snapshot
reference, fingerprint, or concrete immutable values from the caller. It should
not perform hidden live data fetches, hidden database reads, hidden quote
lookups, or hidden vendor revisions during deterministic evaluation.

Feature values must be timestamped or traceable to timestamped input windows.
For rolling-window features, the feature contract should identify the window
end, any availability lag, data quality flags, and the snapshot fingerprint
used to construct the value.

No implicit data revision is allowed. If revised historical data, adjusted
prices, restated fundamentals, corrected corporate actions, or vendor backfills
are used, the snapshot version or fingerprint must change and remain
traceable.

No retrospective parameter mutation is allowed without a new version. Changes
to thresholds, windows, filters, universe assumptions, missing-data handling,
or interpretation rules require a new definition version or a separately
versioned deterministic context.

## 9. Reproducibility Requirements

Future signal evaluation must be reproducible:

- same definition
- same definition version
- same input snapshot
- same explicit input values
- same `as_of` timestamp
- same deterministic context

must produce the same advisory evaluation result.

Evaluation ids and fingerprints should be deterministic in future contracts.
They should be derived from stable normalized content such as definition id,
definition version, input snapshot fingerprint, `as_of`, and evaluator contract
version, not from random UUIDs, process state, wall-clock calls, or mutable
global counters.

Input snapshot fingerprints should be part of future traceability. They allow a
completed evaluation to be re-run or audited against exactly the same inputs.

Future signal evaluation must not depend on:

- network calls
- broker calls
- LLM calls
- live data calls
- mutable global state
- process-local caches that can change the result
- environment variables read inside deterministic layers
- random number generators
- non-deterministic ordering of mappings, sets, files, or external queries

If a future evaluator needs configuration, that configuration should be
explicit, versioned, immutable for the evaluation, and included in
fingerprinting or traceability.

## 10. LLM Boundary

LLMs may assist with:

- summarizing research
- explaining validated signal definitions
- explaining completed evaluation reports
- drafting review notes
- helping humans inspect assumptions and limitations

LLMs may not:

- compute live signal outputs
- generate live trade decisions
- approve trades
- mutate execution plans
- bypass deterministic risk checks
- access live broker state in the trading process
- access live quote state in the trading process
- create broker requests
- submit orders
- mutate portfolio state

LLM output remains research, documentation, or report commentary unless a
human-reviewed deterministic artifact later promotes a rule through explicit
contracts and tests. LLMs must remain out of the trading hot path.

## 11. Dependency Direction

The future signal-evaluation boundary should sit after validated signal
definition metadata and before any future Signal -> Risk bridge. It remains
advisory and deterministic.

Allowed conceptual direction:

```text
validated research artifact metadata
  -> validated signal definition metadata
  -> explicit input snapshot
  -> explicit clock/as-of boundary
  -> future deterministic signal evaluation
  -> future advisory signal-evaluation report
  -> future explicitly designed Signal -> Risk bridge
```

Forbidden direct dependencies for deterministic signal evaluation:

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

The deterministic core consumes only explicit promoted contracts. Validated
signal definitions remain metadata-only. Future signal evaluations remain
advisory metadata until a later design and implementation phase explicitly
defines how any output may cross into Signal -> Risk.

## 12. Explicitly Out Of Scope

Phase 23 Step 1 does not add:

- clock implementation
- `SignalEvaluationResult` implementation
- signal evaluator registry
- signal evaluator implementation
- signal computation
- feature computation
- strategy engine
- Signal -> Risk bridge
- ranking or priority policy
- execution intent creation
- execution planning changes
- risk approval behavior
- broker integration
- Alpaca changes
- order submission
- scheduler/runtime behavior
- persistence implementation
- live data ingestion
- ML training
- LLM trading-path logic

It also does not add any production Python code, tests, imports, runtime
configuration, data ingestion, broker behavior, credentials, network calls, or
normal-pytest dependency on external services.

## 13. Future Implementation Phases

Future implementation should stay contract-first and test-first. A safe future
sequence would be:

1. Add an immutable advisory `SignalEvaluationResult` contract with explicit
   timestamps and fingerprints.
2. Add clock/as-of validation tests with timezone-aware UTC timestamps.
3. Add synthetic input snapshot fixtures and deterministic fingerprinting
   rules.
4. Add a small evaluator registry only after result and snapshot contracts are
   stable.
5. Add one deterministic evaluator implementation with explicit inputs only.
6. Only later design a Signal -> Risk bridge for advisory evaluation outputs.

No future implementation should combine signal evaluation with broker wiring,
runtime scheduling, persistence, live data ingestion, feature computation, ML
training, order submission, risk approval bypasses, execution-plan mutation, or
LLM trading-path behavior.
