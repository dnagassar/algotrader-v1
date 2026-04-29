# Project Checkpoint

## Current Milestone

The project is at the 183-test deterministic core milestone. The current system
prioritizes a deterministic trading core before any real broker connectivity.

Recent focused validation included broker/idempotency, LocalBroker rename/import,
and cleanup/import suites. The latest full-suite result is:

```text
183 passed
```

## Architecture Summary

The core trading path remains deterministic and explicit:

```text
Bar + Quote
  -> deterministic signal rule
  -> ProposedOrder or no signal
  -> RiskEngine.check()
  -> LocalBroker.submit_order()
  -> paper execution simulator
  -> PortfolioState update
  -> quote-map valuation
  -> reconciliation
  -> event ledger
  -> structured result
```

The project currently includes immutable domain models, deterministic signal and
risk checks, local paper execution, portfolio state transitions, quote-based
valuation, local reconciliation, and structured broker results.

`LocalBroker` is the deterministic reference broker and now lives in:

```text
src/algotrader/execution/local_broker.py
```

`AlpacaPaperBroker` is an inert-by-default future broker boundary. It follows
the canonical broker-facing shape but only has operational behavior in tests
when an explicit fake adapter is injected.

## Alpaca Boundary

The Alpaca preparation layer is still fake-only and offline.

Current guarantees:

- no `alpaca-py`
- no credentials
- no environment dependency for normal operation or tests
- no network calls
- no real broker connectivity
- no websocket fills
- no paper-account order submission

The current fake-only path is:

```text
fake Alpaca response
  -> TranslatedAlpaca DTO
  -> explicit mapper
  -> internal Account / Position / BrokerOrderResult
```

Translator return types are pinned:

- `TranslatedAlpacaAccount`
- `TranslatedAlpacaPosition`
- `TranslatedAlpacaOrderResult`

Mapper functions convert translated DTOs into internal models/results:

- `map_translated_account_to_account(...)`
- `map_translated_position_to_position(...)`
- `map_translated_order_result_to_broker_result(...)`

`AlpacaPaperBroker.submit_order(...)` follows the canonical broker signature:

```text
submit_order(order, quote, risk_verdict=None, order_id=None) -> BrokerOrderResult
```

Without an injected adapter, Alpaca broker operations raise
`BrokerNotImplementedError`.

## Safety Guarantees

Production code has repo-wide AST import safety coverage for forbidden
broker/network/LLM imports. The deterministic trading path still has no LLM
logic in risk, execution, signals, screener, portfolio, valuation,
reconciliation, or feature calculation.

Current safety behaviors:

- duplicate `order_id` handling is part of broker contract expectations
- `LocalBroker` rejects duplicate order IDs with `duplicate_order_id`
- duplicate `LocalBroker` submissions do not create a second fill or ledger
  mutation
- fake Alpaca adapter rejects duplicate `client_order_id` values before a second
  fake client call
- `RiskConfig.allow_short=True` still fails closed with
  `short_selling_not_supported`
- portfolio overdraw and oversell branches fail closed without mutating the
  original `PortfolioState`
- valuation rejects unsupported negative position quantities

## Compatibility Notes

`fake_broker.py` remains intentionally as a compatibility shim:

```text
src/algotrader/execution/fake_broker.py
```

Normal imports should use:

```python
from algotrader.execution.local_broker import LocalBroker
```

The compatibility path still re-exports the same `LocalBroker` class for older
imports.

`LedgerEventType.RECONCILIATION_CHECKED` is intentionally kept as an accepted
ledger event value.

`SignalGenerator` is intentionally kept as an exported public signal interface.

## Recent Cleanup

Recent completed work:

- pinned Alpaca translator return types
- added explicit Alpaca mapper layer
- moved fake Alpaca response handling to DTO -> mapper -> internal model/result
- aligned `AlpacaPaperBroker` with the canonical broker shape
- added broker contract idempotency expectations
- added repo-wide AST import safety tests
- moved `LocalBroker` to `local_broker.py`
- kept `fake_broker.py` as a compatibility shim
- cleaned duplicate execution package imports

The most recent cleanup was naming/import hygiene only and did not change
runtime behavior.

## Explicitly Not Included

- real Alpaca SDK dependency
- credentials
- environment-dependent normal tests
- network calls
- real broker connectivity
- websocket behavior
- scheduler/runtime loop
- live trading
- LangGraph
- ML
- LLM trading-path logic

## Next Recommended Steps

Keep avoiding real Alpaca SDK work until explicitly approved.

Safe next tasks include:

- a small config cleanup audit
- documentation polish
- deeper broker contract tests around error paths and reconciliation boundaries
- further fake-only Alpaca contract coverage

Any future real SDK integration must be behind explicit opt-in safety gates,
paper-profile checks, credential redaction, skipped-by-default integration tests,
and no-network defaults for normal test runs.
