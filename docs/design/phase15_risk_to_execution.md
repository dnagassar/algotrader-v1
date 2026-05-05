# Phase 15 Risk to Execution Boundary Design

## Purpose

Phase 15 is a no-code design phase. It defines the future seam between
risk-approved evaluations and execution before any execution or broker
integration is implemented.

This phase does not implement execution. It does not call brokers, submit
orders, route orders, persist events, or add runtime behavior.

The intent is to document the contract while `risk_approved` rows remain
deterministic risk outputs only.

## Current Upstream Flow

The current upstream flow is deterministic and offline:

```text
Synthetic Bar + Quote candidates
  -> rank_by_ask_momentum(...)
  -> ordered_signal_inputs_from_screener(...)
  -> evaluate_signals_from_screener(...)
  -> ScreenerSignalEvaluation tuple
  -> evaluate_risk_for_screener_signals(...)
  -> SignalRiskEvaluation tuple
```

Current responsibilities:

- Screener ranks and filters candidates.
- Signal evaluation creates proposed signal outputs only.
- Signal -> Risk evaluation creates `SignalRiskEvaluation` rows.

`SignalRiskEvaluation.status` may be:

- `no_signal`
- `risk_rejected`
- `risk_approved`

`risk_approved` means allowed by deterministic risk policy only.

## Core Safety Rule

`risk_approved` is a permission signal, not an execution instruction.

It does not mean:

- submitted
- executed
- broker-routed
- broker-accepted
- filled
- persisted

Risk approval must not be treated as broker acceptance, execution success, or
authorization to submit without a later explicitly approved execution phase.

## Future Risk to Execution Boundary

A future Risk -> Execution bridge, if implemented later, must live in
orchestration or execution-facing orchestration.

The future bridge may consume only `risk_approved` `SignalRiskEvaluation` rows.
It must preserve deterministic order. It must skip `no_signal` and
`risk_rejected` rows for execution eligibility.

The future bridge must not mutate portfolio directly, assume broker success, or
treat local simulated fills as real fills. It must not convert risk approval
into submission without a later explicitly approved execution phase.

## Traceability

`no_signal` and `risk_rejected` rows may be skipped for execution eligibility.
Skipping means not sending them to execution.

Skipping must not mean deleting them from reports, traceability, or future
review structures. Future results should keep enough source context to explain
why a row did or did not become execution-eligible.

## Future Allowed Behavior

A later implementation may:

- select `risk_approved` rows deterministically
- preserve source `SignalRiskEvaluation` context
- return immutable internal results
- prepare internal execution-intent objects only if explicitly approved later
- remain deterministic and offline in normal tests
- use fake/local execution only if explicitly approved in a later phase

## Execution-Intent Caution

Any future execution-intent object must remain internal, deterministic, and
non-submitting until a later explicitly approved execution phase.

An execution-intent object must not be treated as a broker order, broker
acknowledgement, fill, persisted event, or runtime instruction.

## Explicit Prohibitions

The future boundary must not:

- call Alpaca
- call real brokers
- call `submit_order`
- wire runtime broker selection
- start scheduler/runtime loops
- use websocket behavior
- retry, poll, or sleep
- persist real broker events
- silently drop `risk_rejected` or `no_signal` rows without traceability
- mutate portfolio directly
- treat risk approval as broker acceptance
- treat local simulated fills as real fills
- bypass idempotency rules
- use screener rank or score for position sizing
- derive `client_order_id` or idempotency keys from screener rank, score, or
  evaluation index

## Future Test Expectations

If implemented later, tests should cover:

- `no_signal` rows are not sent to execution
- `risk_rejected` rows are not sent to execution
- `risk_approved` rows are selected deterministically
- ordering is preserved
- no broker object is required in the first execution-boundary test
- no Alpaca imports
- no `submit_order` call
- no portfolio mutation unless explicitly scoped
- outputs are immutable
- inputs are not mutated
- normal pytest remains offline and credential-free

## Dependency-Direction Expectations

Dependency direction must keep deterministic layers separated:

- screener must not import signals, risk, execution, or orchestration
- signals must not import screener, risk, execution, or orchestration
- risk must not import screener, signals, orchestration, or execution
- `signal_risk_flow` must not import execution or broker layers
- any future execution bridge must not import Alpaca directly
- real Alpaca must remain behind the existing Alpaca SDK boundary only

## Explicit Out of Scope

- live market data
- external APIs
- Alpaca changes
- broker wiring
- `submit_order`
- order submission
- execution integration
- runtime loop
- scheduler
- websocket
- retries, polling, or sleep
- persistence
- ML
- LLM trading-path logic
- dependency additions
