# Phase 12 Signal to Risk Design

## Purpose

Phase 12 is a no-code design phase. It defines the future seam between signal
evaluation and risk evaluation before any risk integration is implemented.

This phase does not implement risk integration. It does not approve orders,
execute orders, submit orders, or add runtime broker behavior.

The intent is to document the contract while `ProposedOrder` values returned
from screener-ordered signal evaluation are still proposed signal output only.

## Current Upstream State

The current upstream flow is deterministic and offline:

```text
Synthetic Bar + Quote candidates
  -> rank_by_ask_momentum(...)
  -> ordered_signal_inputs_from_screener(...)
  -> evaluate_signals_from_screener(...)
  -> ScreenerSignalEvaluation tuple
```

Current responsibilities:

- Screener ranks and filters candidates.
- `ordered_signal_inputs_from_screener(...)` preserves screener order and
  returns signal-ready `Bar + Quote` pairs.
- `evaluate_signals_from_screener(...)` applies the pure signal rule in
  screener order.

`ScreenerSignalEvaluation` may contain:

- `symbol`
- `previous_bar`
- `quote`
- `order: ProposedOrder | None`

Any `ProposedOrder` returned from `evaluate_signals_from_screener(...)` is
proposed signal output only. It is not risk-approved, not executed, and not
submitted.

## Future Bridge Concept

The future Signal -> Risk bridge should live in orchestration. It should not
live in screener, signals, risk, broker, execution, or Alpaca-specific modules.

The intended dependency direction is:

```text
orchestration -> screener
orchestration -> signals
orchestration -> risk
```

Rules:

- Risk must not import screener.
- Risk must not import signal orchestration.
- Screener must not import risk.
- Signals must not import risk.
- Future orchestration may import screener, signals, and risk.

The future bridge may evaluate proposed orders against risk policy in
screener/signal order. It should return immutable structured results and must
not submit anything.

## Allowed Future Behavior

A future Signal -> Risk bridge may:

- skip evaluations where `order is None`
- pass `ProposedOrder` values into a deterministic risk-check function
- preserve screener/signal order
- return structured risk evaluation results
- include the original `ScreenerSignalEvaluation`
- include the risk verdict
- distinguish no-signal from risk-rejected from risk-approved
- remain offline and deterministic

## Explicit Prohibitions

The future bridge must never:

- call `submit_order`
- call any broker
- call Alpaca
- execute trades
- create runtime broker wiring
- persist real broker events
- schedule anything
- poll, retry, sleep, or use websocket behavior
- use screener score as position size
- use screener rank as position size
- derive idempotency keys from screener rank
- auto-correct portfolio state
- bypass risk
- treat `ProposedOrder` as approved before a risk verdict exists

## Critical Safety Rule

`ScreenerSignalEvaluation.order` must not be passed directly into:

- `LocalBroker.submit_order(...)`
- `AlpacaPaperBroker.submit_order(...)`
- `evaluate_and_execute(...)`
- `generate_evaluate_and_execute(...)`
- any broker or execution layer

It must first pass through a separately named, deterministic risk-evaluation
function in a later phase.

Until that later phase exists, any `ScreenerSignalEvaluation.order` remains a
proposed signal output only. It is not risk-approved, not executable, and not
eligible for order submission.

## Future Implementation Sketch

If implemented later, the likely additions are:

- an orchestration-level Signal -> Risk function
- an immutable result model such as `SignalRiskEvaluation` or similar
- unit tests only, using synthetic data only

Possible future tests:

- preserves screener/signal order
- skips `order=None` safely
- risk accepts approved proposed orders
- risk rejects rejected proposed orders
- no broker object required
- no `submit_order` called
- no Alpaca imports
- input evaluations are not mutated
- output model is frozen/immutable
- normal pytest remains offline and credential-free

The bridge should remain an evaluation helper only. Order submission, execution,
broker wiring, and runtime behavior belong outside this design phase and must
remain guarded by explicit later-phase safety contracts.

## Explicit Out of Scope

- live market data
- external APIs
- Alpaca changes
- broker wiring
- order submission
- `submit_order`
- execution integration
- CLI changes
- scheduler/runtime loop
- websocket
- retries, polling, or sleep
- persistence of screener/signal/risk outputs
- ML
- LLM trading-path logic
- dependency additions
