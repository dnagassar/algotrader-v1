# Deterministic Trading Core

This project currently implements a small local trading core for deterministic
paper-trading experiments. The core takes explicit inputs and returns structured
results without reaching out to brokers, schedulers, model services, or external
state.

## Current Status

- `52` tests are passing.
- A deterministic scenario harness exists for named local demo/test cases.
- The `demo-core` command can run a selected named scenario.

## Current Deterministic Path

```text
Bar + Quote
  -> signal rule
  -> ProposedOrder or no signal
  -> RiskEngine.check()
  -> paper execution simulator
  -> portfolio update
  -> quote-based valuation
  -> structured result
```

## Scenario Harness

The scenario harness lives in the orchestration layer and uses fixed sample
inputs. Each scenario calls the existing deterministic core instead of
duplicating trading logic.

- `approved_and_filled`: proves a valid signal can produce an order, pass risk,
  fill in the paper simulator, update portfolio cash/position state, and produce
  a valuation.
- `rejected_insufficient_cash`: proves a generated order can be stopped by the
  risk engine before execution when cash is not sufficient.
- `no_signal`: proves the signal layer can return no order and the flow exits
  cleanly without risk checks or execution.
- `unfilled_limit_order`: proves a generated limit order can pass risk but remain
  open when it is not marketable, leaving portfolio state unchanged.

Run the scenarios with:

```powershell
python -m algotrader demo-core --scenario approved_and_filled
python -m algotrader demo-core --scenario rejected_insufficient_cash
python -m algotrader demo-core --scenario no_signal
python -m algotrader demo-core --scenario unfilled_limit_order
```

## Boundaries

- Signal generation only creates `ProposedOrder` objects or returns `None`.
- Risk checks do not execute orders.
- Execution simulation does not mutate portfolio state.
- Portfolio state transitions are pure functions.
- Valuation requires explicit current quotes and does not guess missing prices.
- Orchestration composes the deterministic pieces but is not a scheduler or
  runtime loop.

## Explicitly Not Included

- Broker API calls
- Scheduler
- Runtime loop
- LangGraph
- ML models
- LLM logic in the trading path
- Live trading

## Next Recommended Phase

The next phase should stay small. Good candidates are lightweight CLI polish
around scenario output or planning the first broker/data abstraction boundary.
Full paper broker wiring, live trading, or runtime scheduling should wait until
the deterministic layer remains stable under the scenario harness.
