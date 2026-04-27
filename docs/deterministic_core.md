# Deterministic Trading Core

This project currently implements a small local trading core for deterministic
paper-trading experiments. The core takes explicit inputs and returns structured
results without reaching out to brokers, schedulers, model services, or external
state.

## Current Status

- `103` tests are passing.
- A deterministic scenario harness exists for named local demo/test cases.
- The `demo-core` command can run selected named scenarios.
- `LocalBroker` is the working deterministic broker reference implementation.
- Broker contract tests define expected broker behavior.
- `AlpacaPaperBroker` exists only as an inert future adapter skeleton.
- `InMemoryLedger` remains available for fast local event history.
- `JsonlLedger` adds optional append-only JSONL persistence.
- `LocalBroker` can use either ledger through the existing optional `ledger=`
  argument.
- There are still no real broker API calls or external network dependencies.

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

## Current Local Safety Foundation

```text
signal rule
  -> RiskEngine.check()
  -> LocalBroker
  -> paper simulator
  -> portfolio update
  -> quote-map valuation
  -> reconciliation
  -> InMemoryLedger or JsonlLedger
  -> broker contract tests
  -> inert AlpacaPaperBroker skeleton
```

## CLI-Facing Scenarios

These scenarios are exposed through the `demo-core` CLI command and use fixed
sample inputs.

- `approved_and_filled`: proves a valid signal can produce an order, pass risk,
  fill in the paper simulator, update portfolio state, and produce valuation.
- `rejected_insufficient_cash`: proves a generated order can be stopped by risk
  before execution when cash is not sufficient.
- `no_signal`: proves the signal layer can return no order and exit cleanly.
- `unfilled_limit_order`: proves a limit order can pass risk but remain open
  when it is not marketable, leaving portfolio state unchanged.

Run them with:

```powershell
python -m algotrader demo-core --scenario approved_and_filled
python -m algotrader demo-core --scenario rejected_insufficient_cash
python -m algotrader demo-core --scenario no_signal
python -m algotrader demo-core --scenario unfilled_limit_order
```

## Internal Broker Scenarios

These scenarios are internal harness cases. They are separate from the
CLI-facing scenario list.

- `broker_approved_and_filled`: proves an approved order can be submitted to
  `LocalBroker`, filled by the paper simulator, and reflected in local portfolio
  state.
- `broker_rejected_insufficient_cash`: proves an order rejected by
  `RiskEngine.check()` is not submitted to the broker.
- `broker_unfilled_limit_order`: proves an approved but non-marketable limit
  order can be submitted to `LocalBroker` without mutating cash or positions.

## Broker Boundary

`LocalBroker` is an in-memory fake/local broker. It prepares the shape of a
future broker adapter while keeping the current project fully local and
deterministic.

- `LocalBroker` requires an approved `RiskVerdict` by default.
- It uses the existing paper execution simulator internally.
- It mutates local `PortfolioState` only when a fill occurs.
- It returns structured `BrokerOrderResult` values.
- It does not call Alpaca or any external API.
- It does not require credentials.

`AlpacaPaperBroker` is not operational yet and must not be used for trading. It
currently defines `submit_order(...)`, `get_account()`, and `get_positions()`,
but each method raises `BrokerNotImplementedError`. A future implementation must
satisfy the broker contract tests before it enters the trading path.

## Broker Contract Tests

Broker contract tests live at:

```text
tests/contracts/test_broker_contract.py
```

The contract currently verifies that a broker exposes account and position
reads, refuses missing or rejected risk approval, accepts approved orders, fills
marketable orders through the local paper behavior, leaves cash and positions
unchanged for unfilled limits, returns `BrokerOrderResult`, and preserves
deterministic supplied order IDs.

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

Ledger modes:

- `InMemoryLedger`: fast local in-memory event history for tests and flows.
- `JsonlLedger`: append-only JSONL event history that survives process exit.

`JsonlLedger` behavior:

- Appends one JSON object per line.
- Serializes timestamps using `isoformat()`.
- Reads events back in order.
- Filters events by `order_id`.
- Returns no events for a missing file.
- Raises `ValidationError` on malformed ledger lines.

## Explicitly Not Included

- Database
- SQLite migrations
- Alpaca implementation
- Alpaca credentials
- Network calls
- Broker API calls
- Websocket fills
- Reconciliation loop against external broker state
- Scheduler or runtime loop
- LangGraph
- ML models
- LLM logic in the trading path
- Live trading

## Next Recommended Phase

The next phase should be a pre-Alpaca implementation plan or checklist before
adding any real Alpaca SDK imports or API calls.

The checklist should cover broker contract expectations, risk-verdict handling,
order ID handling, ledger behavior, reconciliation expectations, error handling,
credential boundaries, network boundaries, and dry-run/demo boundaries.

## Alpaca Paper Planning Link

See [Alpaca Paper Integration Plan](alpaca_paper_integration_plan.md) for the safe future path toward Alpaca paper integration. That plan is documentation-only and does not add SDK dependencies, credentials, network calls, or runtime broker behavior.
