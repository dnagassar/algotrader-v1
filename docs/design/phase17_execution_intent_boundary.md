# Phase 17 Execution-Intent Boundary Design

## Purpose

Phase 17 defines the internal execution-intent boundary after risk-approved row
selection and before any execution layer, broker adapter, scheduler,
persistence path, or live trading behavior. Step 1 documented the boundary with
no code changes. Step 2 adds the smallest internal deterministic contract for
that boundary. Step 3 hardens source-only traceability with tests and docs
without changing production code.

The current deterministic pre-execution pipeline is:

```text
Screener
  -> Signal evaluation
  -> Risk evaluation
  -> risk-approved row selection
  -> internal execution-intent construction
```

`select_risk_approved_evaluations(...)` still returns only
`risk_approved` `SignalRiskEvaluation` rows while preserving order and object
identity. Those selected rows are permission signals only. They are eligible
for future execution-boundary consideration, but they are not execution
intents by themselves, submitted orders, broker-routed orders, fills, persisted
broker events, scheduler actions, runtime actions, or live trading decisions.

Phase 17 Step 2 adds a minimal internal `ExecutionIntent` wrapper for selected
risk-approved rows. An `ExecutionIntent` remains pre-submission and
broker-agnostic. It only preserves the source `SignalRiskEvaluation` by
identity. Phase 17 Step 3 keeps that shape unchanged.

A separate execution-intent boundary is needed because risk approval answers
only one question: did deterministic risk policy allow the proposed order? The
execution-intent layer answers a different question: which internal,
deterministic, broker-agnostic instruction candidates are prepared for a later
execution layer? Keeping those responsibilities separate prevents risk approval
or intent construction from being accidentally treated as order submission or
broker acceptance.

## Non-goals

Phase 17 Step 2 does not add:

- order submission
- broker routing
- Alpaca changes
- `submit_order`
- `client_order_id` generation
- idempotency implementation
- scheduler/runtime behavior
- persistence
- portfolio mutation
- fills
- reconciliation changes
- live trading
- ML
- LLM trading-path logic
- `ExecutionIntent` fields beyond `source_evaluation`
- convenience `ExecutionIntent` properties for order, risk, symbol, status,
  side, or quantity

## Current Step 2 Boundary

Phase 17 Step 2 implements:

```text
build_execution_intents_from_risk_approved(...)
```

The builder accepts an iterable of `SignalRiskEvaluation` rows and returns an
immutable tuple of `ExecutionIntent` objects for `risk_approved` rows only. It
skips `no_signal` and `risk_rejected` rows, preserves approved-row order, and
preserves each source `SignalRiskEvaluation` object by identity.

The builder currently consumes only:

- `SignalRiskEvaluation` rows

It does not consume `PortfolioState`, `RiskEngine`, a broker, an execution
object, a scheduler/runtime object, persistence handles, or network clients. It
does not directly consume screener rank in a way that affects sizing,
idempotency, or broker routing. Current `SignalRiskEvaluation` does not carry
screener rank or original input index, and this design must not assume those
fields exist.

## ExecutionIntent Semantics

`ExecutionIntent` is an internal deterministic instruction candidate produced
after risk approval but before any broker adapter.

The Phase 17 Step 2 shape is intentionally minimal:

```text
ExecutionIntent(source_evaluation=SignalRiskEvaluation)
```

The intent preserves traceability by identity without inventing screener rank,
original index, broker IDs, idempotency keys, or persistence metadata. It does
not copy order-like fields yet. If a later phase adds order-like fields copied
from the approved proposed order, the intent would still not be submitted. It
would not become a broker order, broker acknowledgement, accepted order, fill,
ledger event, scheduler command, or runtime trading action.

`ExecutionIntent` is:

- deterministic
- immutable
- auditable
- broker-agnostic
- free of network behavior
- free of SDK objects
- free of Alpaca-specific types
- independent of LLM output

`ExecutionIntent` does not contain:

- live broker response data
- fill data
- account mutation
- broker-specific order IDs
- SDK-native objects
- side effects
- `client_order_id`
- idempotency keys
- venue/account fields

## Traceability Requirements

Execution-intent creation preserves enough traceability to explain:

- which `SignalRiskEvaluation` produced an intent
- why `no_signal` rows were skipped
- why `risk_rejected` rows were skipped
- which proposed order was risk-approved
- which risk verdict allowed it
- that the current deterministic policy is the simple risk-approved-only
  builder

This design still does not invent new provenance fields beyond
`source_evaluation`. If additional traceability fields, provenance records, or
audit envelopes are needed, they should be designed explicitly in a later
phase. Current `SignalRiskEvaluation` does not carry screener rank or original
index, so future traceability must not assume those values are already present.

Phase 17 Step 3 hardens this rule: proposed order, risk verdict, and status are
reachable through `intent.source_evaluation.order`,
`intent.source_evaluation.risk`, and `intent.source_evaluation.status`.
Convenience fields or properties such as `intent.order`, `intent.risk`,
`intent.symbol`, or `intent.status` should not be added without a later explicit
design phase.

## Batch-Level Concerns

The future execution-intent boundary must account for unresolved batch-level
concerns before any order submission behavior exists:

- multiple individually approved rows may not be collectively affordable
- same-symbol conflicts are unresolved
- duplicate or competing orders are unresolved
- batch-level cash reservation does not exist
- `client_order_id` / idempotency scheme does not exist
- execution ordering policy has not been finalized
- persistence/audit logging strategy has not been implemented

These concerns remain future work. Phase 17 Steps 2 and 3 do not solve them.

## Dependency Direction

Execution-intent construction lives in orchestration. It must not live in
screener, signals, risk, portfolio, broker, Alpaca, execution,
scheduler/runtime, persistence, ML, or LLM trading-path modules.

Allowed conceptual direction:

- orchestration -> `signal_risk_flow`
- orchestration -> `risk_execution_flow`
- orchestration -> deterministic models/configs

Forbidden for this boundary:

- execution modules
- broker modules
- Alpaca modules
- scheduler/runtime modules
- `submit_order`
- network clients
- persistence writes
- LLM calls

## Step 2 Acceptance Criteria

Phase 17 Step 2 is test-first around the internal object and builder. The
contract covers:

- empty input returns an empty tuple
- only risk-approved rows produce intents
- order is preserved
- `no_signal` and `risk_rejected` rows produce no intents
- output is immutable
- inputs are not mutated
- no broker object is required
- no execution object is required
- no Alpaca import is required
- no `submit_order` call is made
- no scheduler/runtime behavior is added
- no persistence is added
- deterministic idempotency policy is absent rather than implicit

## Step 3 Traceability Hardening

Phase 17 Step 3 adds tests and documentation only. It hardens that:

- `ExecutionIntent` has exactly one dataclass field: `source_evaluation`
- traceability flows through the exact source `SignalRiskEvaluation` object
- proposed order, risk verdict, and status remain reachable through the source
  evaluation
- no convenience order/risk/status/symbol/quantity/side attributes exist on the
  intent
- no broker IDs, broker names, account IDs, venue fields, Alpaca-specific
  fields, SDK/native objects, submission fields, fill fields, persistence
  fields, `client_order_id`, or idempotency keys exist on the intent
- the builder remains pure, approved-row-only, order-preserving, and free of
  same-symbol conflict resolution or batch-level affordability checks

## Explicit Exclusions

Phase 17 Steps 2 and 3 explicitly exclude:

- no paper order submission
- no live order submission
- no broker routing
- no Alpaca changes
- no execution adapter integration
- no scheduler/runtime execution
- no persistence writes
- no portfolio mutation
- no ML
- no LLM trading-path logic
