# Phase 10 Screener to Signals Design

## Purpose

Phase 10 is a no-code design phase. It defines the future boundary between the
deterministic screener and deterministic signal generation, but it does not
implement that bridge.

The intent is to document the contract before any orchestration code exists, so
future work can preserve the current safety properties: offline inputs,
deterministic behavior, no broker access, and no order submission.

## Bridge Concept

The future bridge should live in orchestration, not in the screener package.

Responsibilities should stay separate:

- Screener ranks and filters candidates.
- Signal layer evaluates one symbol at a time using existing `Bar + Quote`
  inputs.
- Future orchestration preserves screener order and calls the signal layer once
  per selected candidate.

The bridge should be pure, deterministic, offline, stateless, and oriented
toward immutable outputs. It should accept explicit in-memory inputs and return
structured results without reading external state.

## Allowed Influence

Screener output may influence:

- which symbols are evaluated by the signal layer
- the order in which symbols are evaluated
- whether a symbol is skipped due to `top_n` or `min_score` filtering

## Explicit Prohibitions

Screener output must never directly influence:

- order side
- order type
- order quantity
- limit price
- account selection
- broker selection
- risk caps
- position sizing
- idempotency keys
- whether `submit_order` is called

## Dependency Direction

The dependency direction should remain one-way from orchestration into the
deterministic components:

```text
orchestration -> screener
orchestration -> signals
```

Rules:

- `screener` must not import signals, risk, portfolio, execution, Alpaca, or
  orchestration.
- `signals` should not import screener.
- orchestration may import both screener and signals later.

This keeps the screener a pure ranking/filtering helper and keeps signal rules
independent of ranking policy.

## Future Phase 11 Implementation Sketch

If implemented later, the likely files are:

```text
src/algotrader/orchestration/screener_signal_flow.py
tests/unit/test_screener_signal_flow.py
```

Future tests should cover:

- deterministic ordering is preserved
- empty screener result short-circuits
- all-filtered result short-circuits
- signal fires on zero candidates
- signal fires on a subset of candidates
- symbol mismatch fails clearly
- bridge does not invoke broker, risk, portfolio mutation, or `submit_order`

The bridge should remain a selection-and-evaluation helper only. Any order
approval, risk checking, execution, or broker behavior belongs outside this
phase and must remain guarded by existing deterministic contracts.

## Explicit Out of Scope

- live market data
- external APIs
- Alpaca changes
- broker wiring
- order creation
- `submit_order`
- risk/order sizing integration
- CLI changes
- scheduler/runtime loop
- websocket
- retries, polling, or sleep
- persistence of screener results
- multi-strategy screener composition
- second screener strategy
- ML
- LLM trading-path logic
- new dependencies
