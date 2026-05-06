# Phase 18 Execution-Planning Boundary Design

## Purpose

Phase 18 Step 1 defines the future execution-planning boundary after internal
`ExecutionIntent` construction and before any broker adapter, order submission,
persistence write, scheduler/runtime behavior, or live trading behavior.

`ExecutionIntent` represents an internal pre-submission candidate. It preserves
the exact source `SignalRiskEvaluation` object by identity and remains
broker-agnostic, source-only, and not executable by itself. A future execution
plan would be a deterministic batch-level decision artifact. It may eventually
decide which `ExecutionIntent` objects are eligible to become broker-facing
execution requests, but this phase does not implement that decision.

The boundary is needed because individual intent construction answers only a
row-level question: which risk-approved source evaluations have been wrapped as
internal candidates? Execution planning would answer a separate batch-level
question: which set of candidates should proceed toward a later broker-facing
request boundary under deterministic policy? Earlier phases intentionally left
batch affordability, ordering, conflict handling, stale input policy, and
idempotency unresolved. This design records those concerns without solving them
in code.

## Boundary Position

The conceptual path is:

```text
Screener
  -> Signal evaluation
  -> Risk evaluation
  -> risk-approved row selection
  -> ExecutionIntent construction
  -> future execution planning
  -> future broker adapter / execution layer
```

Phase 18 Step 1 designs only the future execution-planning boundary. The
implemented deterministic pre-execution path still stops at immutable
`ExecutionIntent` construction.

## Non-goals

Phase 18 Step 1 does not add:

- `ExecutionPlan` dataclass
- execution-planning function
- broker routing
- order submission
- Alpaca changes
- `submit_order`
- `client_order_id` generation
- idempotency implementation
- batch cash reservation implementation
- same-symbol conflict resolution implementation
- persistence
- audit logging writes
- scheduler/runtime behavior
- portfolio mutation
- fills
- reconciliation changes
- live trading
- ML
- LLM trading-path logic

## Future ExecutionPlan Semantics

A future `ExecutionPlan` may eventually be a deterministic batch-level artifact
that consumes `ExecutionIntent` objects and produces a pre-broker decision set.
That set could distinguish accepted, skipped, or rejected intents before any
broker-facing request is constructed.

A future execution plan should remain:

- deterministic
- immutable
- auditable
- broker-agnostic
- offline
- SDK-free
- Alpaca-free
- independent of LLM output

A future execution plan should not contain:

- broker-native order objects
- live broker response data
- fill data
- account mutation
- SDK-native objects
- Alpaca-specific types
- network behavior
- persistence writes

No `ExecutionPlan` object, function, module, or test exists after Phase 18 Step
1. The term is conceptual only in this phase.

## Batch-Level Concerns To Solve Later

Execution planning may eventually handle these unresolved concerns:

- multiple individually risk-approved intents may not be collectively affordable
- cash reservation / buying-power reservation policy
- same-symbol conflicts
- duplicate or competing orders
- long/short or call/put conflict rules if options are later introduced
- ordering policy across intents
- partial acceptance versus all-or-nothing batch policy
- maximum intents per batch
- maximum exposure per symbol or sector
- priority policy when too many intents are eligible
- whether screener order may influence priority without influencing sizing or
  idempotency
- handling stale quotes or stale risk snapshots
- what happens when the portfolio snapshot changes after risk evaluation

Phase 18 Step 1 does not implement any of these policies. Until a later
test-first implementation phase exists, same-symbol approved intents remain
unresolved, batch cash is not reserved, and collectively affordable execution
sets are not computed.

## Idempotency And Client Order IDs

Idempotency and `client_order_id` design remain unresolved.

Current state:

- no idempotency keys exist yet
- no `client_order_id` generation exists yet
- `ExecutionIntent` must not gain idempotency fields without a separate design
  phase
- a future execution-planning or execution-request phase may need deterministic
  idempotency design
- idempotency should not be derived implicitly from screener rank alone
- idempotency should not depend on LLM output

Any future idempotency policy needs an explicit boundary decision before fields,
keys, hashes, request identifiers, or broker-facing IDs are added.

## Persistence And Audit Boundary

Persistence and audit logging are unresolved.

Phase 18 Step 1 adds no persistence writes. A future audit design may need to
record skipped intents, accepted intents, rejected intents, policy decisions,
batch-level reasons, input snapshots, and deterministic traceability back to
the source evaluations. That design should be separate from implementation.

Audit logging should not be mixed into pure planning functions without an
explicit boundary decision. A future pure planner could return auditable data;
a separate persistence layer could decide whether and how to write it.

## Broker And Execution Boundary

Future execution planning remains pre-broker.

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

Broker-facing request construction should be a later phase after execution
planning is designed and tested. Execution planning should not route, submit,
acknowledge, fill, reconcile, persist, or mutate accounts or portfolios.

## Dependency Direction

Expected future dependency direction:

- orchestration -> `risk_execution_flow`
- orchestration -> future execution planning module
- orchestration -> deterministic model/config modules

Forbidden for execution planning:

- execution modules
- broker modules
- Alpaca modules
- scheduler/runtime modules
- persistence writes
- LLM/LangGraph calls
- network clients

The execution-planning boundary should stay in orchestration or another
deterministic pre-broker layer. It must not depend on the broker/execution side
of the system to perform pure eligibility decisions.

## Future Test-First Implementation Acceptance Criteria

A later Phase 18 Step 2 could test a future planning object or function before
implementation. Possible acceptance criteria:

- empty input returns an empty plan or empty tuple depending on design
- approved `ExecutionIntent` objects are preserved by identity
- output is immutable
- input is not mutated
- no broker object required
- no execution object required
- no scheduler/runtime object required
- no persistence required
- no Alpaca import
- no `submit_order`
- no `client_order_id` / idempotency unless explicitly designed
- batch cash policy absent until deliberately introduced
- same-symbol conflict policy absent until deliberately introduced
- planning reasons are deterministic and traceable if designed

These tests should keep the boundary offline, credential-free, SDK-free,
broker-free, and independent of ML or LLM trading-path output.

## Explicit Exclusions

Phase 18 Step 1 explicitly excludes:

- no paper order submission
- no live order submission
- no broker routing
- no Alpaca changes
- no execution adapter integration
- no scheduler/runtime execution
- no persistence writes
- no portfolio mutation
- no fills
- no reconciliation changes
- no idempotency implementation
- no `client_order_id` generation
- no batch cash reservation implementation
- no same-symbol conflict resolution implementation
- no ML
- no LLM trading-path logic
