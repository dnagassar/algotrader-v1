# Phase 20 Maximum Intents Planning Policy Design

## 1. Purpose

Phase 20 Step 1 designed the first real execution-planning policy concept:
maximum accepted intents per plan. Step 1 was documentation-only. Phase 20 Step
2 adds the narrow test-first implementation of that policy while preserving the
existing planning result shapes. Phase 20 Step 3 hardens the traceability
contract with focused tests and documentation only.

A maximum-intents policy is a safe first real planning policy because it is
deterministic, simple, and batch-level. It does not require portfolio math,
cash or buying-power reservation, broker calls, idempotency keys, same-symbol
conflict resolution, or priority scoring when existing plan order is preserved.

`ExecutionPlan` is currently only an immutable container for ordered
`ExecutionIntent` objects. It is not executable by itself. The current
`apply_noop_execution_planning_policy(...)` function still accepts every intent
in the plan, preserves order and object identity, and returns no skipped
intents. It remains the explicit no-cap pass-through policy.

`apply_max_intents_execution_planning_policy(...)` caps accepted intents
deterministically and wraps the remaining intents with deterministic skip
reasons. That decision remains a pre-broker, batch-level planning decision. It
does not route orders, construct broker-native requests, submit orders, reserve
cash, mutate portfolios, or create fills.

Phase 20 Step 3 does not change production source. It pins that the max-intents
policy preserves accepted and skipped `ExecutionIntent` identity, preserves
deterministic accepted and skipped ordering, uses deterministic skip reasons,
does not mutate the original `ExecutionPlan`, and keeps traceability flowing
through `source_evaluation`.

## 2. Boundary Position

The conceptual path is:

```text
Screener
  -> Signal evaluation
  -> Risk evaluation
  -> risk-approved row selection
  -> ExecutionIntent construction
  -> ExecutionPlan construction
  -> no-op planning policy or max-intents planning policy
  -> future broker-facing execution request construction
  -> future broker adapter / execution layer
```

Phase 20 Step 1 designed the future max-intents planning policy. Phase 20 Step
2 implements that pure policy function. The existing no-op policy remains
available and separate for no-cap pass-through behavior, and no broker-facing
execution request construction exists yet. Phase 20 Step 3 adds tests and docs
only; the boundary position does not move.

The max-intents policy boundary sits after source-only internal intent grouping
and before any broker-facing request shape exists. It remains deterministic,
offline, broker-agnostic, and independent of runtime schedulers, persistence
writers, network clients, ML, or LLM trading-path output.

## 3. Non-goals

Phase 20 Step 3 does not add:

- production source changes
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

## 4. Max-Intents Policy Semantics

The max-intents policy accepts the first `N` intents from an `ExecutionPlan`
and skips the remaining intents with deterministic reason text. It returns the
existing `PlanningPolicyResult` shape:

```text
PlanningPolicyResult(
    accepted_intents: tuple[ExecutionIntent, ...],
    skipped_intents: tuple[SkippedExecutionIntent, ...],
)
```

Current behavior:

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

## 5. Why Input Order Is Enough For The First Policy

The max-intents policy uses existing `ExecutionPlan` order as the deterministic
selection order. This avoids introducing priority and ranking before those
policies have their own design.

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

## 6. Policy Configuration

Phase 20 Step 2 adds this immutable config:

```text
MaxAcceptedIntentsPolicyConfig(max_accepted_intents: int)
```

The config is a frozen, slotted dataclass with exactly one field:
`max_accepted_intents`. The value must be exactly an `int` and must be greater
than or equal to `1`. `bool` is rejected even though `bool` is an `int` subclass
in Python. `None`, `0`, negative values, `float`, `str`, and `Decimal` values
are rejected.

`None` does not mean no cap. The explicit no-cap policy remains
`apply_noop_execution_planning_policy(...)`.

Remaining future questions:

- Should skipped reason text remain a plain string forever?
- Should skipped reason text later become an enum?
- Should later policy configs share a common protocol or remain independent?

## 7. Skipped Reason Semantics

Phase 20 Step 2 adds this deterministic string constant:

```text
MAX_INTENTS_PER_PLAN_EXCEEDED_REASON = "max_intents_per_plan_exceeded"
```

Skipped intents produced by `apply_max_intents_execution_planning_policy(...)`
use exactly that reason. Phase 20 Step 2 does not add indexes, provenance
fields, enum reasons, configured-limit fields, original-plan-index fields, or
new fields on `SkippedExecutionIntent`. The result shape remains:

```text
SkippedExecutionIntent(intent: ExecutionIntent, reason: str)
```

## 8. Traceability Requirements

Accepted-intent traceability preserves object identity:

```text
result.accepted_intents[n] is original_intent
result.accepted_intents[n].source_evaluation is original_signal_risk_evaluation
```

Accepted source evaluation remains reachable through:

```text
result.accepted_intents[n].source_evaluation
```

Skipped-intent traceability also preserves object identity:

```text
result.skipped_intents[n].intent is original_intent
result.skipped_intents[n].intent.source_evaluation is original_signal_risk_evaluation
```

Skipped source evaluation remains reachable through:

```text
result.skipped_intents[n].intent.source_evaluation
```

The skip reason is deterministic. Proposed order, risk verdict, and status
remain reachable only through the source evaluation. The max-intents policy
does not add direct proposed-order, risk, status, symbol, quantity, side,
broker, account, venue, idempotency, cash-reservation, priority, fill, SDK,
Alpaca, audit, or persistence fields to the policy result.

Phase 20 Step 3 hardens this contract with focused tests that prove:

- accepted intent identity is preserved
- skipped intent identity is preserved through `SkippedExecutionIntent.intent`
- accepted ordering is deterministic
- skipped ordering is deterministic
- skipped reasons are deterministic
- the original `ExecutionPlan` is not mutated
- accepted and skipped source evaluations remain reachable by identity
- forbidden broker, execution, runtime, persistence, idempotency, cash,
  buying-power, priority/ranking, and direct order/risk/status fields are not
  exposed

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

Phase 20 Step 2 adds no persistence writes and no audit logging writes.

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

Forbidden dependencies for the max-intents policy:

- execution modules
- broker modules
- Alpaca modules
- scheduler/runtime modules
- persistence writes
- LLM/LangGraph calls
- network clients

The policy stays in the deterministic pre-broker orchestration boundary. It
depends on source models and explicit deterministic configuration, not on
broker or execution behavior.

## 16. Test-First Acceptance Criteria

Phase 20 Step 2 adds focused tests for:

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

Those tests keep the implementation deterministic, offline, credential-free,
broker-free, SDK-free, and independent of ML or LLM trading-path output.

Phase 20 Step 3 adds traceability-hardening tests only. It does not alter the
policy implementation, config, reason constant, result shapes, no-op policy, or
dependency guardrails.

## 17. Explicit Exclusions

Phase 20 Step 3 explicitly excludes:

- no production source changes
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
