# Phase 17 Execution-Intent Boundary Design

## Purpose

Phase 17 Step 1 is a no-code design phase. It defines a future internal
execution-intent boundary after risk-approved row selection and before any
execution layer, broker adapter, scheduler, persistence path, or live trading
behavior.

The current deterministic pre-execution pipeline is:

```text
Screener
  -> Signal evaluation
  -> Risk evaluation
  -> risk-approved row selection
```

`select_risk_approved_evaluations(...)` returns only
`risk_approved` `SignalRiskEvaluation` rows while preserving order and object
identity. Those selected rows are permission signals only. They are eligible
for future execution-boundary consideration, but they are not execution
intents, submitted orders, broker-routed orders, fills, persisted broker
events, scheduler actions, runtime actions, or live trading decisions.

A separate execution-intent boundary is needed because risk approval answers
only one question: did deterministic risk policy allow the proposed order? A
future execution-intent layer would answer a different question: what internal,
deterministic, broker-agnostic instruction candidates should be prepared for a
later execution layer? Keeping those responsibilities separate prevents risk
approval from being accidentally treated as order submission or broker
acceptance.

## Non-goals

Phase 17 Step 1 does not add:

- `ExecutionIntent` dataclass
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

## Proposed Future Boundary

A later phase may choose to implement a future function conceptually named:

```text
build_execution_intents_from_risk_approved(...)
```

This name is conceptual only. Phase 17 Step 1 does not add the function, its
signature, its return type, tests, imports, or runtime behavior.

A future function may eventually consume:

- selected risk-approved `SignalRiskEvaluation` rows
- a deterministic execution-intent policy/config object
- explicit provenance input if that is designed later

The future function must not directly consume screener rank in a way that
affects sizing, idempotency, or broker routing. Current `SignalRiskEvaluation`
does not carry screener rank or original input index, and this design must not
assume those fields exist.

## Future ExecutionIntent Semantics

A future `ExecutionIntent` would be an internal deterministic instruction
candidate produced after risk approval but before any broker adapter.

It may contain order-like fields copied from the approved proposed order, but
it would still not be submitted. It would not be a broker order, broker
acknowledgement, accepted order, fill, ledger event, scheduler command, or
runtime trading action.

A future `ExecutionIntent` should be:

- deterministic
- immutable
- auditable
- broker-agnostic
- free of network behavior
- free of SDK objects
- free of Alpaca-specific types
- independent of LLM output

A future `ExecutionIntent` should not contain:

- live broker response data
- fill data
- account mutation
- broker-specific order IDs
- SDK-native objects
- side effects

## Traceability Requirements

Future execution-intent creation should preserve enough traceability to explain:

- which `SignalRiskEvaluation` produced an intent
- why `no_signal` rows were skipped
- why `risk_rejected` rows were skipped
- which proposed order was risk-approved
- which risk verdict allowed it
- what deterministic policy produced the intent

This design does not invent new provenance fields yet. If additional
traceability fields, provenance records, or audit envelopes are needed, they
should be designed explicitly in a later phase. Current `SignalRiskEvaluation`
does not carry screener rank or original index, so future traceability must not
assume those values are already present.

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

These concerns remain future work. Phase 17 Step 1 does not solve them.

## Dependency Direction

Future execution-intent construction must live in orchestration. It must not
live in screener, signals, risk, portfolio, broker, Alpaca, execution,
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

## Acceptance Criteria for Future Implementation

A later Phase 17 Step 2 could be test-first if the internal object is approved
for implementation. Possible future tests:

- empty input returns an empty tuple
- only risk-approved rows produce intents
- order is preserved
- `no_signal` and `risk_rejected` rows are represented or traceable according
  to the design
- output is immutable
- inputs are not mutated
- no broker object is required
- no execution object is required
- no Alpaca import is required
- no `submit_order` call is made
- no scheduler/runtime behavior is added
- no persistence is added
- deterministic idempotency policy is either absent or explicitly injected, not
  implicit

## Explicit Exclusions

Phase 17 Step 1 explicitly excludes:

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
