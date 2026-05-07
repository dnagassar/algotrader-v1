# Phase 19 Execution-Planning Policy Design

## 1. Purpose

Phase 19 Step 1 designs a future execution-planning policy layer after the
minimal `ExecutionPlan` container and before any broker-facing execution request
is created. This phase is documentation-only. It does not implement the policy
layer.

`ExecutionIntent` is a single internal pre-submission candidate. It is
broker-agnostic, source-only, and not executable by itself. Its current contract
has exactly one dataclass field:

```text
source_evaluation: SignalRiskEvaluation
```

`ExecutionPlan` is currently only an immutable batch container for
`ExecutionIntent` objects. Its current contract has exactly one dataclass field:

```text
intents: tuple[ExecutionIntent, ...]
```

The minimal plan answers only this question: which intent objects are grouped
together in order? It does not decide whether the batch is collectively
affordable, whether same-symbol intents conflict, whether duplicates should be
kept, or which intents should proceed when a limit is exceeded.

A future execution-planning policy may eventually operate on an `ExecutionPlan`
and decide which intents remain eligible after batch-level checks. Those policy
decisions must remain deterministic, offline, broker-agnostic, and auditable.
They must not depend on live broker state, network calls, credentials, runtime
schedulers, ML, or LLM trading-path output.

## 2. Boundary Position

The conceptual path is:

```text
Screener
  -> Signal evaluation
  -> Risk evaluation
  -> risk-approved row selection
  -> ExecutionIntent construction
  -> ExecutionPlan construction
  -> future execution planning policy
  -> future broker-facing execution request construction
  -> future broker adapter / execution layer
```

Phase 19 Step 1 designs only the future policy boundary. The implemented
deterministic pre-execution path still stops at immutable `ExecutionPlan`
construction.

The future policy boundary sits after source-only internal intent grouping and
before any broker-facing request shape exists. It should therefore be able to
make deterministic eligibility decisions without importing broker adapters,
Alpaca SDK types, execution modules, scheduler/runtime code, persistence
writers, or network clients.

## 3. Non-goals

Phase 19 Step 1 does not add:

- policy implementation
- `ExecutionPlan` field changes
- `ExecutionIntent` field changes
- accepted/rejected/skipped intent buckets
- batch cash reservation implementation
- buying-power reservation implementation
- same-symbol conflict resolution implementation
- duplicate/competing order policy implementation
- priority/ranking implementation
- `client_order_id` generation
- idempotency implementation
- persistence
- audit logging writes
- broker routing
- order submission
- Alpaca changes
- `submit_order`
- scheduler/runtime behavior
- portfolio mutation
- fills
- reconciliation changes
- live trading
- ML
- LLM trading-path logic

## 4. Future Policy Responsibilities

A future execution-planning policy may eventually address:

- batch-level cash affordability
- buying-power reservation
- same-symbol conflicts
- duplicate or competing intents
- partial acceptance versus all-or-nothing behavior
- maximum intents per plan
- maximum exposure per symbol
- maximum exposure per sector or asset class
- priority when too many intents are eligible
- how to handle stale quote snapshots
- how to handle stale risk snapshots
- what to do if portfolio state changes after risk approval
- whether screener order may influence selection priority
- whether risk verdict metadata may influence selection priority
- how to preserve traceability for accepted and skipped intents

These are possible future responsibilities only. Phase 19 Step 1 does not
implement any of them.

## 5. Policy Output Concept

A future policy may need to return a deterministic decision artifact rather than
mutating `ExecutionPlan`. Possible future output shapes include:

- a planned decision artifact that references the source `ExecutionPlan`
- a policy result object that separates policy decisions from the input plan
- accepted intents plus skipped intents with deterministic reasons
- an all-or-nothing plan approval result
- a partial acceptance plan result

No output shape is selected in Phase 19 Step 1. These examples are tentative
design options, not implementation commitments.

The current `ExecutionPlan` must remain unchanged in this phase. It remains a
minimal immutable container with only `intents`, and it does not gain decision
buckets, policy metadata, ranking fields, cash reservation records,
idempotency fields, or broker-facing request data.

## 6. Batch Cash / Buying-Power Policy Design Questions

Unresolved design questions:

- Should cash reservation happen in planning or later execution-request
  construction?
- Should buying power be reserved per intent or at the batch level?
- Should the policy support partial acceptance?
- Should the policy fail the whole plan if any intent is unaffordable?
- Should affordability use the current portfolio snapshot, the risk snapshot,
  or a fresh deterministic state snapshot?
- How should stale quotes be handled?
- How should options buying power be handled later if options are introduced?

No batch cash or buying-power policy is implemented in Phase 19 Step 1.

## 7. Same-Symbol And Duplicate Policy Design Questions

Unresolved design questions:

- Should multiple intents for the same symbol be allowed?
- Should duplicate intents be preserved, deduplicated, or rejected?
- Should opposite-side intents conflict?
- Should same-symbol same-side intents aggregate or remain separate?
- Should the earliest intent win?
- Should screener order decide priority?
- Should risk score or confidence decide priority?
- Should all such policy be explicit and injected rather than implicit?

No same-symbol, duplicate, or competing-order policy is implemented in Phase 19
Step 1.

## 8. Priority / Ranking Policy Design Questions

Unresolved design questions:

- Should `ExecutionPlan` preserve input order only, or should a future policy
  reorder?
- Should screener rank influence priority?
- Should screener rank be allowed to influence sizing?
- Should risk verdict metadata influence priority?
- Should signal strength influence priority?
- Should policy have deterministic tie-breakers?
- Should priority be represented as a separate policy result rather than as
  fields on `ExecutionIntent` or `ExecutionPlan`?

No priority field exists yet. No rank field exists yet. No sizing policy exists
yet. Screener rank must not implicitly create idempotency keys or
`client_order_id` values.

## 9. Idempotency Separation

Idempotency remains a separate future design phase.

Current constraints:

- no `client_order_id` exists yet
- no `idempotency_key` exists yet
- `ExecutionIntent` must not gain idempotency fields during planning policy
  design
- `ExecutionPlan` must not gain idempotency fields during planning policy
  design
- idempotency should be deterministic
- idempotency must not depend on LLM output
- idempotency should not be derived implicitly from screener order alone
- idempotency should be designed before broker-facing request construction

The execution-planning policy design should preserve enough traceability for a
later idempotency design, but it must not invent keys, hashes, client order IDs,
or broker-facing identifiers in this phase.

## 10. Persistence And Audit Separation

Persistence and audit remain unresolved.

Phase 19 Step 1 adds:

- no persistence writes
- no audit logging writes

A future audit design may need to record accepted intents, skipped intents,
policy reasons, source evaluations, plan IDs, and deterministic policy
configuration. That future design should decide what is pure decision data and
what is durable audit state.

Audit and persistence should not be mixed into pure planning policy functions
unless an explicit boundary is designed. A pure policy may return auditable data
later; a separate persistence or audit layer can decide whether and how to write
it.

## 11. Broker And Execution Separation

Future planning policy remains pre-broker.

Forbidden at this boundary:

- broker adapters
- Alpaca SDK
- native broker order objects
- `submit_order`
- network clients
- live account mutation
- fills
- reconciliation mutation
- scheduler/runtime execution

Broker-facing request construction remains a later phase. Planning policy
should not import execution modules, know Alpaca-specific types, route orders,
submit orders, acknowledge orders, observe fills, reconcile broker state, mutate
accounts, or mutate portfolios.

## 12. Dependency Direction

Allowed conceptual dependency direction:

- orchestration -> `risk_execution_flow`
- orchestration -> `execution_planning_flow`
- orchestration -> future policy module
- orchestration -> deterministic config/model modules

Forbidden for a future planning policy boundary:

- execution modules
- broker modules
- Alpaca modules
- scheduler/runtime modules
- persistence writes
- LLM/LangGraph calls
- network clients

The future policy module should stay in orchestration or another deterministic
pre-broker layer. It should depend on source models and explicit deterministic
configuration, not on execution-side behavior.

## 13. Future Test-First Acceptance Criteria

A later Phase 19 Step 2 could test a policy object or function if implementation
is explicitly approved. Possible future tests include:

- empty plan behavior is deterministic
- accepted/skipped result shape is immutable
- input `ExecutionPlan` is not mutated
- `ExecutionIntent` objects are preserved by identity
- source `SignalRiskEvaluation` objects are preserved by identity
- policy requires explicit config
- policy does not implicitly use screener rank
- policy does not generate `client_order_id`
- policy does not implement idempotency
- policy does not call brokers
- policy does not call `submit_order`
- policy does not write persistence
- policy does not mutate portfolio state
- policy does not import Alpaca
- same-symbol behavior is explicit once designed
- batch cash behavior is explicit once designed
- priority behavior is explicit once designed

Those tests should keep any implementation deterministic, offline,
credential-free, broker-free, SDK-free, and independent of ML or LLM
trading-path output.

## 14. Explicit Exclusions

Phase 19 Step 1 explicitly excludes:

- no paper order submission
- no live order submission
- no broker routing
- no Alpaca changes
- no execution adapter integration
- no scheduler/runtime execution
- no persistence writes
- no audit logging writes
- no portfolio mutation
- no fills
- no reconciliation changes
- no idempotency implementation
- no `client_order_id` generation
- no batch cash reservation implementation
- no buying-power reservation implementation
- no same-symbol conflict resolution implementation
- no duplicate/competing order policy implementation
- no priority/ranking policy implementation
- no ML
- no LLM trading-path logic
