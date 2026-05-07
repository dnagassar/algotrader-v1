# Phase 20 Maximum Intents Planning Policy Design

## 1. Purpose

Phase 20 Step 1 designs the first real execution-planning policy concept:
maximum accepted intents per plan. This step is documentation-only. It does not
implement the policy, add configuration, change runtime behavior, or alter the
existing planning result shapes.

A maximum-intents policy is a safe first real planning policy because it is
deterministic, simple, and batch-level. It does not require portfolio math,
cash or buying-power reservation, broker calls, idempotency keys, same-symbol
conflict resolution, or priority scoring when existing plan order is preserved.

`ExecutionPlan` is currently only an immutable container for ordered
`ExecutionIntent` objects. It is not executable by itself. The current
`apply_noop_execution_planning_policy(...)` function accepts every intent in
the plan, preserves order and object identity, and returns no skipped intents.

A future max-intents policy would cap accepted intents deterministically and
wrap the remaining intents with deterministic skip reasons. That decision would
remain a pre-broker, batch-level planning decision. It would not route orders,
construct broker-native requests, submit orders, reserve cash, mutate
portfolios, or create fills.

## 2. Boundary Position

The conceptual path is:

```text
Screener
  -> Signal evaluation
  -> Risk evaluation
  -> risk-approved row selection
  -> ExecutionIntent construction
  -> ExecutionPlan construction
  -> future max-intents planning policy
  -> future broker-facing execution request construction
  -> future broker adapter / execution layer
```

Phase 20 Step 1 designs only the future max-intents planning policy. The
implemented deterministic pre-execution path still uses the no-op planning
policy, and no broker-facing execution request construction exists yet.

The future max-intents policy boundary would sit after source-only internal
intent grouping and before any broker-facing request shape exists. It must
remain deterministic, offline, broker-agnostic, and independent of runtime
schedulers, persistence writers, network clients, ML, or LLM trading-path
output.

## 3. Non-goals

Phase 20 Step 1 does not add:

- max-intents policy implementation
- policy config object
- changes to `PlanningPolicyResult`
- changes to `SkippedExecutionIntent`
- changes to `ExecutionPlan`
- changes to `ExecutionIntent`
- broker routing
- order submission
- Alpaca changes
- `submit_order`
- `client_order_id` generation
- idempotency implementation
- batch cash reservation
- buying-power reservation
- same-symbol conflict resolution
- duplicate/competing order policy
- priority/ranking implementation
- persistence
- audit logging writes
- scheduler/runtime behavior
- portfolio mutation
- fills
- reconciliation changes
- live trading
- ML
- LLM trading-path logic

## 4. Future Max-Intents Policy Semantics

A future max-intents policy may accept the first `N` intents from an
`ExecutionPlan` and skip the remaining intents with deterministic reason text.
It should return the existing `PlanningPolicyResult` shape:

```text
PlanningPolicyResult(
    accepted_intents: tuple[ExecutionIntent, ...],
    skipped_intents: tuple[SkippedExecutionIntent, ...],
)
```

Conceptual future behavior:

- preserve the accepted `ExecutionIntent` objects by identity
- preserve skipped `ExecutionIntent` objects by identity through
  `SkippedExecutionIntent.intent`
- preserve original plan order
- return accepted intents first in original order
- return skipped intents in original order after the accepted limit is reached
- use only explicit deterministic policy configuration
- use deterministic skip reason text

Example:

```text
max_accepted_intents = 3
plan has 5 intents

accepted: first 3 intents
skipped: final 2 intents
reason: "max_intents_per_plan_exceeded"
```

This behavior is conceptual only. Phase 20 Step 1 does not implement it.

## 5. Why Input Order Is Enough For The First Policy

The first max-intents policy may use existing `ExecutionPlan` order as the
deterministic selection order. This avoids introducing priority and ranking
before those policies have their own design.

Current constraints:

- no priority field exists yet
- no rank field exists yet
- no policy score exists yet
- no screener-rank field exists on `ExecutionIntent`
- no screener-rank field exists on `ExecutionPlan`
- screener order must not influence sizing
- screener order must not create idempotency keys

Preserving plan order is enough for the first cap because the cap answers only
one narrow question: how many intents may remain accepted in this batch?
Future priority or ranking policy remains separate and should be designed
explicitly before any reordering or scoring is introduced.

## 6. Future Policy Configuration Questions

Unresolved design questions:

- Should the config be a frozen dataclass?
- Should the future config be named `MaxAcceptedIntentsPolicyConfig`?
- Should the field be named `max_accepted_intents`?
- Should the value require `int >= 1`?
- Should `bool` be rejected even though `bool` is an `int` subclass in Python?
- Should `max_accepted_intents=None` mean no cap?
- Should the no-op policy remain separate instead of using `None` for no cap?
- Should reason text be a fixed constant?
- Should skipped reason text be human-readable, machine-readable, or both?

No config object is implemented in Phase 20 Step 1.

## 7. Future Skipped Reason Semantics

Unresolved skip-reason questions:

- Should reason be a string constant?
- Should the future reason be `"max_intents_per_plan_exceeded"`?
- Should reason include the configured limit?
- Should reason include the original plan index?
- Should index/provenance be added later?
- Should index/provenance be avoided for now?
- Should reason be an enum later?
- Should reason remain a plain deterministic string for now?

Phase 20 Step 1 does not add indexes, provenance fields, enum reasons, or new
fields on `SkippedExecutionIntent`. The current result shape remains:

```text
SkippedExecutionIntent(intent: ExecutionIntent, reason: str)
```

## 8. Traceability Requirements

Future accepted-intent traceability must preserve object identity:

```text
result.accepted_intents[n] is original_intent
result.accepted_intents[n].source_evaluation is original_signal_risk_evaluation
```

Accepted source evaluation remains reachable through:

```text
result.accepted_intents[n].source_evaluation
```

Future skipped-intent traceability must also preserve object identity:

```text
result.skipped_intents[n].intent is original_intent
result.skipped_intents[n].intent.source_evaluation is original_signal_risk_evaluation
```

Skipped source evaluation remains reachable through:

```text
result.skipped_intents[n].intent.source_evaluation
```

The skip reason must be deterministic. Proposed order, risk verdict, and status
remain reachable only through the source evaluation. The future max-intents
policy should not add direct proposed-order, risk, status, symbol, quantity,
side, broker, account, venue, idempotency, cash-reservation, priority, fill,
SDK, Alpaca, audit, or persistence fields to the policy result.

## 9. Separation From Cash And Buying-Power Policy

The max-intents policy does not check affordability. It does not reserve cash,
reserve buying power, inspect portfolio state, recalculate risk, or decide
whether the accepted intents are collectively affordable.

Cash and buying-power planning remain later phases. They should be designed as
separate deterministic planning concerns before any broker-facing request
construction or order submission path exists.

## 10. Separation From Same-Symbol And Duplicate Policy

The max-intents policy does not resolve same-symbol conflicts. It does not
deduplicate intents, aggregate same-symbol intents, collapse duplicate source
evaluations, or decide whether competing orders should be kept or skipped.

Duplicate and conflict policy remain later phases. A future duplicate or
same-symbol policy may also use `PlanningPolicyResult`, but it should be
designed separately from the simple max-intents cap.

## 11. Separation From Priority/Ranking Policy

The max-intents policy may preserve existing plan order. It does not compute
priority, reorder intents, add priority fields, add rank fields, or attach
policy scores.

Priority and ranking policy remain later phases. Those phases should decide
whether screener rank, signal strength, risk metadata, or deterministic
tie-breakers may influence selection. Until then, existing `ExecutionPlan`
order is the only selection order considered by this conceptual cap.

## 12. Separation From Idempotency

The max-intents policy does not generate `client_order_id` values. It does not
generate `idempotency_key` values, request IDs, broker IDs, or broker-safe
correlation identifiers.

Accepted and skipped decisions must not be treated as broker-safe request IDs.
They are planning decisions only. Idempotency remains a separate future design
phase and should be resolved before broker-facing execution requests are
constructed.

## 13. Persistence And Audit Separation

Phase 20 Step 1 adds no persistence writes and no audit logging writes.

A future audit design may record accepted intents, skipped intents, skip
reasons, source evaluations, plan identifiers, and deterministic policy
configuration. That future audit/persistence design must remain separate from
pure policy functions unless a boundary is explicitly designed later.

A pure planning policy may return auditable data. A separate persistence or
audit layer can decide whether and how to write it.

## 14. Broker And Execution Separation

The max-intents policy remains pre-broker. It must not import broker modules,
import Alpaca modules, call `submit_order`, construct broker-native order
objects, mutate live account state, observe fills, or produce fills.

Broker-facing request construction, broker routing, broker adapters, execution
adapter integration, order acknowledgement, fill handling, and reconciliation
remain later phases.

## 15. Dependency Direction

Allowed conceptual dependency direction:

- orchestration -> `execution_planning_flow`
- orchestration -> `execution_planning_policy`
- orchestration -> deterministic config/model modules

Forbidden dependencies for a future max-intents policy:

- execution modules
- broker modules
- Alpaca modules
- scheduler/runtime modules
- persistence writes
- LLM/LangGraph calls
- network clients

The future policy should stay in the deterministic pre-broker orchestration
boundary. It should depend on source models and explicit deterministic
configuration, not on broker or execution behavior.

## 16. Future Test-First Acceptance Criteria

A later Phase 20 Step 2 could test a real max-intents policy before
implementation. Possible tests:

- `max_accepted_intents` must be `int >= 1`
- `bool` is rejected
- empty plan returns empty accepted and skipped tuples
- plan length less than or equal to max accepts all intents
- plan length greater than max accepts first `N` intents
- skipped intents are wrapped in `SkippedExecutionIntent`
- skipped reason is deterministic
- accepted order is preserved
- skipped order is preserved
- accepted intent object identity is preserved
- skipped intent object identity is preserved
- source `SignalRiskEvaluation` identity is preserved
- input `ExecutionPlan` is not mutated
- no cash or buying-power check occurs
- no same-symbol conflict handling occurs
- no deduplication occurs
- no priority/ranking occurs
- no `client_order_id` or idempotency behavior occurs
- no broker calls occur
- no `submit_order` call occurs
- no persistence writes occur
- no scheduler/runtime behavior occurs

Those future tests should keep the implementation deterministic, offline,
credential-free, broker-free, SDK-free, and independent of ML or LLM
trading-path output.

## 17. Explicit Exclusions

Phase 20 Step 1 explicitly excludes:

- no policy implementation in Phase 20 Step 1
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
- no batch cash reservation
- no buying-power reservation
- no same-symbol conflict resolution
- no duplicate/competing order policy
- no priority/ranking policy
- no ML
- no LLM trading-path logic
