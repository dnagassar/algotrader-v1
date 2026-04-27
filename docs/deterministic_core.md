# Deterministic Trading Core

This project currently implements a small local trading core for deterministic
paper-trading experiments. The core takes explicit inputs and returns structured
results without reaching out to brokers, schedulers, model services, or external
state.

## Current Status

- `97` tests are passing.
- A deterministic scenario harness exists for named local demo/test cases.
- The `demo-core` command can run a selected named scenario.
- A `LocalBroker` abstraction exists as an in-memory fake/local broker.
- LocalBroker-backed internal scenarios exist for broker-boundary validation.
- Broker contract tests exist, with `LocalBroker` as the current reference
  implementation.
- An inert `AlpacaPaperBroker` skeleton exists only as a future adapter
  boundary.
- There is no Alpaca SDK dependency, no credentials, and no network behavior.
- A local reconciliation layer compares expected portfolio state with
  broker-reported local state.
- A local order-event ledger records deterministic broker/order events.
- `LocalBroker` can optionally record events to `InMemoryLedger`.
- The ledger is local, deterministic, and in-memory only.
- There are still no real broker API calls or external network dependencies.
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

Current broker layers:

- `LocalBroker` is the working deterministic reference implementation.
- Broker contract tests define expected broker behavior.
- `AlpacaPaperBroker` is currently inert and raises
  `BrokerNotImplementedError`.

The `AlpacaPaperBroker` skeleton currently defines these broker-shaped methods:

- `submit_order(...)`
- `get_account()`
- `get_positions()`

`AlpacaPaperBroker` is not operational yet and must not be used for trading.
Future implementation must satisfy the broker contract tests. Real Alpaca
integration should only be added intentionally in a separate phase.

## Broker Contract Tests

Broker contract tests live at:

```text
tests/contracts/test_broker_contract.py
```

`LocalBroker` is the current reference implementation for the contract. Future
broker adapters, such as an `AlpacaPaperBroker`, should be compared against the
same contract before they are allowed into the trading path.

The contract currently verifies that a broker:

- Exposes `get_account()`.
- Exposes `get_positions()`.
- Refuses submission without required risk approval.
- Refuses submission with a rejected `RiskVerdict`.
- Accepts an approved order.
- Fills marketable orders through the local paper execution behavior.
- Does not mutate cash or positions for unfilled limit orders.
- Returns `BrokerOrderResult`.
- Preserves deterministic supplied order IDs.

This matters because broker correctness is defined before external API
integration. The contract helps keep broker-specific behavior out of strategy,
signal, risk, portfolio, and valuation logic.

## Local Reconciliation

The local reconciler compares expected `PortfolioState` with state reported by a
broker-like object such as `LocalBroker`.

It can detect:

- Cash mismatch
- Missing expected position
- Unexpected broker position
- Position quantity mismatch
- Optional valuation mismatch when quote data is supplied

This is a deterministic local comparison helper only. It is not an external
broker reconciliation loop.

## Local Order-Event Ledger

The local ledger records what happened during deterministic broker/order flows.
It is append-only for the lifetime of the in-memory object and preserves event
order.

Current ledger event types:

- `order_submitted`
- `order_rejected`
- `order_filled`
- `order_not_filled`
- `portfolio_updated`
- `reconciliation_checked`

`LocalBroker` can use the ledger when one is supplied. It records submission
attempts, missing-risk or rejected-risk submissions, fills, no-fills, and
portfolio updates only when fills occur. If no ledger is supplied, existing
broker behavior is preserved.

## Current Safety Chain

```text
ProposedOrder
  -> RiskVerdict
  -> LocalBroker.submit_order()
  -> BrokerOrderResult
  -> paper execution result
  -> portfolio update
  -> quote-map valuation
  -> reconciliation report
  -> event ledger
```

## Why Reconciliation Matters

Real broker integration will eventually create two views of state:

- Local expected state maintained by the deterministic core
- Broker-reported state returned by the external broker adapter

Reconciliation is how the system detects drift between those views before
continuing. That keeps broker-specific behavior from leaking into strategy,
risk, signal, portfolio, or valuation logic.

## Boundaries

- Signal generation only creates `ProposedOrder` objects or returns `None`.
- Risk checks do not execute orders.
- Execution simulation does not mutate portfolio state.
- Portfolio state transitions are pure functions.
- Valuation requires explicit current quotes and does not guess missing prices.
- Orchestration composes the deterministic pieces but is not a scheduler or
  runtime loop.

## Explicitly Not Included

- Alpaca implementation
- Credentials
- Network calls
- Real broker API calls
- Websocket fills
- Reconciliation loop against external broker state
- Scheduler or runtime loop
- LangGraph
- ML models
- LLM logic in the trading path
- Live trading
- Persistent database ledger

## Next Recommended Phase

The next phase should pause and choose between two conservative directions:

- Plan the broker contract requirements for a future `AlpacaPaperBroker`.
- Design local persistence for ledger and reconciliation state.

Do not add real Alpaca SDK or network calls until the broker contract,
reconciliation behavior, and event history remain stable.
