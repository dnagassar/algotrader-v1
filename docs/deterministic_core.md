# Deterministic Trading Core

This project currently implements a small local trading core for deterministic
paper-trading experiments. The core takes explicit inputs and returns structured
results without reaching out to brokers, schedulers, model services, or external
state.

## Current Status

- `303` tests are passing, with `4` skipped paper-integration tests by default.
- A deterministic offline screener foundation ranks synthetic `Bar + Quote`
  inputs by ask momentum versus previous close, with optional deterministic
  `min_score` and `top_n` filters.
- A pure orchestration-owned Screener -> Signal input bridge preserves screener
  ordering, returns signal-ready `Bar + Quote` pairs, rejects duplicate screener
  result symbols and malformed result/candidate inputs, and preserves original
  `Bar` and `Quote` objects.
- Pure screener-ordered signal evaluation now applies the existing deterministic
  signal rule to ordered inputs only. Any signal output is not an approved trade
  and is not submitted.
- Screener-ordered signal evaluation contract tests now cover mixed
  signal/no-signal preservation, input non-mutation, immutable
  `ScreenerSignalEvaluation` results, and signal-rule exception propagation.
- Dependency-direction guardrails now enforce documented layering between
  screener, signals, risk, orchestration, and execution.
- Pure Signal -> Risk evaluation converts `ScreenerSignalEvaluation` rows into
  immutable `SignalRiskEvaluation` rows without execution or submission.
- Phase 15 documents the future Risk -> Execution boundary while keeping
  `risk_approved` as a permission signal only.
- Phase 16 Step 1 adds test-only Risk -> Execution dependency guardrails for
  pre-execution orchestration modules.
- Phase 16 Step 2 adds a pure risk-approved row selector that returns only
  `risk_approved` `SignalRiskEvaluation` rows while preserving order and object
  identity.
- Phase 17 Step 1 documents the future execution-intent boundary after
  risk-approved row selection. No execution intent has been implemented yet.
- A deterministic scenario harness exists for named local demo/test cases.
- The `demo-core` command can run selected named scenarios.
- `LocalBroker` is the working deterministic broker reference implementation in
  `src/algotrader/execution/local_broker.py`.
- Broker contract tests define expected broker behavior.
- `AlpacaPaperBroker` exists only as an inert future adapter skeleton.
- `InMemoryLedger` remains available for fast local event history.
- `JsonlLedger` adds optional append-only JSONL persistence.
- `LocalBroker` can use either ledger through the existing optional `ledger=`
  argument.
- Repo-wide AST import safety tests guard production code against broker SDK,
  network, and LLM imports.
- Duplicate order IDs are rejected before a second fill or ledger mutation can
  occur.
- Broker contract coverage now includes duplicate order-id idempotency.
- Short selling is not modeled end-to-end yet, so risk checks fail closed even
  if `RiskConfig.allow_short=True`.
- There are still no real broker API calls or external network dependencies.

## Current Deterministic Path

The offline screener path is separate from trading:

```text
Synthetic Bar + Quote candidates
  -> rank_by_ask_momentum(..., min_score=None, top_n=None)
  -> immutable AskMomentumResult tuple
  -> ordered_signal_inputs_from_screener(...)
  -> immutable signal-ready (Bar, Quote) tuple
  -> evaluate_signals_from_screener(...)
  -> immutable ScreenerSignalEvaluation tuple
  -> evaluate_risk_for_screener_signals(...)
  -> immutable SignalRiskEvaluation tuple
  -> select_risk_approved_evaluations(...)
  -> immutable risk-approved SignalRiskEvaluation tuple
```

The screener-to-signal segment does not call risk, broker, Alpaca, execution,
CLI, scheduler, ML, or LLM trading-path logic. Any `ProposedOrder` returned by
signal evaluation is a proposed signal output only. The Signal -> Risk layer
then checks proposed orders with `RiskEngine` only, keeps no-signal rows with
`risk=None`, and returns risk verdicts without executing or submitting anything.
Risk-approved means allowed by risk, not executed, submitted, or broker-ready.
The risk-approved selector keeps only those permission rows in order and still
does not create execution intents or call brokers.
Phase 17 Step 1 documents a future execution-intent boundary after this
selector, but no `ExecutionIntent` object, builder function, broker routing,
submission, scheduler/runtime behavior, persistence, ML, or LLM trading-path
logic exists in this path.
The bridge also rejects duplicate screener result symbols and malformed
result/candidate inputs while preserving the original `Bar` and `Quote` objects.

The current trading path remains:

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
offline screener ranking
  -> synthetic Bar + Quote inputs only
  -> pure orchestration input bridge
  -> signal-ready Bar + Quote pairs
  -> pure screener-ordered signal evaluation
  -> proposed signal outputs only, not approved or submitted trades
  -> no risk, broker, Alpaca, execution, CLI, scheduler, ML, or LLM
     trading-path logic

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

`LocalBroker` is an in-memory deterministic reference broker. It prepares the
shape of a future broker adapter while keeping the current project fully local
and deterministic.

- `LocalBroker` requires an approved `RiskVerdict` by default.
- It uses the existing paper execution simulator internally.
- It mutates local `PortfolioState` only when a fill occurs.
- It rejects duplicate order IDs without applying another fill or recording
  another ledger event.
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
deterministic supplied order IDs. It also verifies that duplicate order IDs are
rejected with `duplicate_order_id` before a second fill or ledger mutation can
occur.

## Short Selling

Short selling is intentionally not supported yet. `RiskConfig.allow_short`
remains a reserved configuration field for future work, but `RiskEngine`
currently rejects sell orders that exceed the held position even when
`allow_short=True`. This keeps risk and portfolio behavior aligned until short
positions, borrow rules, margin, valuation, and reconciliation are modeled
end-to-end.

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

## Deterministic Screener Foundation

The Phase 8 screener lives in:

```text
src/algotrader/screener/momentum.py
```

It ranks synthetic `Bar + Quote` candidates using ask momentum versus the
previous close:

```text
score = (quote.ask - previous_bar.close) / previous_bar.close
```

Results are immutable and returned as a tuple. Ordering is deterministic by
score descending and then symbol ascending. The screener is offline,
credential-free, API-free, broker-free, and deterministic.

Phase 9 adds optional deterministic polish filters. `min_score` keeps only
results with `score >= min_score`, and `top_n` limits the returned tuple after
ranking and score filtering. Defaults preserve Phase 8 behavior.

Phase 10 documents the future Screener -> Signals bridge as a design-only
orchestration boundary in
[`docs/design/phase10_screener_to_signals.md`](design/phase10_screener_to_signals.md).

Phase 11 begins that path with a pure orchestration-owned input bridge in:

```text
src/algotrader/orchestration/screener_signal_flow.py
```

`ordered_signal_inputs_from_screener(...)` accepts ranked `AskMomentumResult`
values plus the original `AskMomentumCandidate` values or a candidate lookup,
matches by symbol, rejects missing or duplicate candidate symbols with
`ValidationError`, and returns an immutable tuple of signal-ready `(Bar, Quote)`
pairs in the exact screener-result order.

Phase 11 Step 2 hardens the bridge by rejecting duplicate screener result
symbols, rejecting malformed result/candidate inputs, and preserving the
original `Bar` and `Quote` objects while returning immutable ordered pairs.

Phase 11 Step 3 adds pure screener-ordered signal evaluation through
`evaluate_signals_from_screener(...)`. It applies the existing deterministic
signal rule to the ordered `(Bar, Quote)` inputs and returns immutable
`ScreenerSignalEvaluation` values in exact screener order. Any `ProposedOrder`
is a proposed signal output only: it is not an approved trade and is not
submitted.

This bridge still does not call risk, call brokers, touch Alpaca, connect to
execution, CLI, scheduler, or runtime behavior, or add ML or LLM trading-path
logic.

Phase 12 documents the future Signal -> Risk boundary as a design-only
orchestration contract in
[`docs/design/phase12_signal_to_risk.md`](design/phase12_signal_to_risk.md).
It does not implement risk integration, approve orders, submit orders, or add
runtime behavior.

Phase 13 hardens the screener-ordered signal evaluation contract with focused
unit tests only. Mixed signal/no-signal results preserve screener order,
no-signal candidates remain represented with `order=None`, inputs are not
mutated, `ScreenerSignalEvaluation` is immutable, and `signal_rule` exceptions
propagate instead of being hidden as `order=None`.

No risk, broker, execution, Alpaca, order submission, scheduler, ML, dependency,
or LLM trading-path logic was added.

Phase 14 Step 1 adds test-only AST dependency-direction guardrails. These tests
enforce the documented layering between screener, signals, risk, orchestration,
and execution before any Signal -> Risk runtime code exists.

No Signal -> Risk runtime behavior, broker wiring, Alpaca changes, execution
integration, order submission, scheduler/runtime behavior, ML, dependency, or
LLM trading-path logic was added.

Phase 14 Step 2 adds pure Signal -> Risk evaluation in
`src/algotrader/orchestration/signal_risk_flow.py`.
`evaluate_risk_for_screener_signals(...)` converts
`ScreenerSignalEvaluation` rows into immutable `SignalRiskEvaluation` rows,
retains no-signal rows with `risk=None`, and checks proposed orders with
`RiskEngine` only.

Risk-approved means only allowed by risk. The function does not call brokers,
execution, Alpaca, `submit_order`, CLI, scheduler, persistence, ML, or LLM
trading-path logic.

Phase 15 documents the future Risk -> Execution boundary in
[`docs/design/phase15_risk_to_execution.md`](design/phase15_risk_to_execution.md).
It clarifies that `risk_approved` rows are still not executed, submitted,
broker-routed, filled, or persisted. A future execution bridge must preserve
order, keep `no_signal` and `risk_rejected` rows traceable even when they are
not execution-eligible, and remain separated from broker, Alpaca, scheduler,
persistence, ML, and LLM trading-path behavior until a later explicitly
approved phase.

Phase 16 Step 1 strengthens AST dependency-direction tests so pre-execution
orchestration modules do not import execution, broker, Alpaca, or trade-flow
modules. It adds no Risk -> Execution runtime behavior, execution bridge,
broker wiring, order submission, scheduler, persistence, ML, dependency, or LLM
trading-path logic.

Phase 16 Step 2 adds pure risk-approved row selection in
`src/algotrader/orchestration/risk_execution_flow.py`.
`select_risk_approved_evaluations(...)` returns only
`SignalRiskEvaluation` rows with `status="risk_approved"`, preserves input
order, preserves object identity, and returns an immutable tuple. `no_signal`
and `risk_rejected` rows are skipped.

The selector does not create execution intents, call brokers, import execution,
touch Alpaca, call `submit_order`, use schedulers, persist anything, mutate
portfolios, add dependencies, or add ML or LLM trading-path logic.
`risk_approved` remains a permission signal only, not an execution instruction.

Known limitation: rows can be individually risk-approved against the same fixed
portfolio snapshot while not being collectively affordable. This selector does
not solve batch-level cumulative cash handling or same-symbol conflict
resolution; those remain future execution-boundary concerns before any
execution intent or order submission behavior is added.

Phase 17 Step 1 documents the future execution-intent boundary in
[`docs/design/phase17_execution_intent_boundary.md`](design/phase17_execution_intent_boundary.md).
It distinguishes selected risk-approved rows from future execution intents:
risk-approved rows are permission signals only, while a future execution intent
would be a deterministic, immutable, auditable, broker-agnostic internal
instruction candidate prepared before any broker adapter. No execution intent,
execution-intent builder, broker routing, Alpaca change, scheduler/runtime
behavior, persistence, ML, or LLM trading-path logic has been implemented.

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
- Screener-driven order generation
- Screener wiring into risk or execution
- Approved or submitted trades from screener signal evaluation
- Execution-intent objects
- Execution-intent builder functions
- Batch-level cumulative cash enforcement
- Same-symbol execution conflict handling
- Reconciliation loop against external broker state
- Scheduler or runtime loop
- LangGraph
- ML models
- LLM logic in the trading path
- Live trading

## Next Recommended Phase

The next phase should keep any execution-boundary work pure and synthetic unless
explicitly approved otherwise. Safe follow-up work could design batch-level cash
and same-symbol handling before any execution intent, broker wiring, order
submission, scheduler, persistence, ML, or LLM trading-path logic exists.

Real Alpaca SDK work and Phase 7 reconciliation remain deferred unless
explicitly approved.

## Alpaca Paper Planning Link

See [Alpaca Paper Integration Plan](alpaca_paper_integration_plan.md) for the safe future path toward Alpaca paper integration. That plan is documentation-only and does not add SDK dependencies, credentials, network calls, or runtime broker behavior.
