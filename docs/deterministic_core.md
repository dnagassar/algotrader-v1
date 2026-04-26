# Deterministic Trading Core

This project currently implements a small local trading core for deterministic
paper-trading experiments. The core takes explicit inputs and returns structured
results without reaching out to brokers, schedulers, model services, or external
state.

## Current Status

- `74` tests are passing.
- A deterministic scenario harness exists for named local demo/test cases.
- The `demo-core` command can run a selected named scenario.
- A `LocalBroker` abstraction exists as an in-memory fake/local broker.
- LocalBroker-backed internal scenarios exist for broker-boundary validation.
- CLI demo scenarios remain separate from internal broker scenarios.

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

## CLI-Facing Scenario Harness

The scenario harness lives in the orchestration layer and uses fixed sample
inputs. Each scenario calls the existing deterministic core instead of
duplicating trading logic. These are the scenarios exposed through the
`demo-core` CLI command.

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

## Internal Broker-Backed Scenarios

The broker-backed scenarios are internal harness cases. They are not part of the
default CLI scenario list. They prove that the broker abstraction can run the
same deterministic local pieces through `LocalBroker` without introducing real
broker calls.

- `broker_approved_and_filled`: proves an approved order can be submitted to
  `LocalBroker`, filled by the existing paper execution simulator, and reflected
  in local portfolio state.
- `broker_rejected_insufficient_cash`: proves an order rejected by
  `RiskEngine.check()` is not submitted to the broker.
- `broker_unfilled_limit_order`: proves an approved but non-marketable limit
  order can be submitted to `LocalBroker` without mutating positions or cash.

## Broker Boundary

`LocalBroker` is an in-memory fake/local broker. It exists to prepare the shape
of a future broker adapter, such as an `AlpacaPaperBroker`, while keeping the
current project fully local and deterministic.

- `LocalBroker` requires an approved `RiskVerdict` by default.
- It uses the existing paper execution simulator internally.
- It mutates local `PortfolioState` only when a fill occurs.
- It returns structured broker results for accepted, filled, open, or refused
  submissions.
- It does not call Alpaca or any external API.
- It does not require credentials.

## Boundaries

- Signal generation only creates `ProposedOrder` objects or returns `None`.
- Risk checks do not execute orders.
- Execution simulation does not mutate portfolio state.
- Portfolio state transitions are pure functions.
- Valuation requires explicit current quotes and does not guess missing prices.
- Orchestration composes the deterministic pieces but is not a scheduler or
  runtime loop.

## Explicitly Not Included

- Real broker API calls
- Alpaca credentials
- Websocket fills
- Reconciliation loop
- Scheduler or runtime loop
- LangGraph
- ML models
- LLM logic in the trading path
- Live trading

## Next Recommended Phase

The next phase should stay conservative. Good candidates are a tiny
broker-facing CLI/internal demo, if useful, or designing the
`AlpacaPaperBroker` interface contract without implementing real API calls.

Do not add real Alpaca API calls until the local broker boundary remains stable.
