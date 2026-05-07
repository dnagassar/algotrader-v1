# Deterministic Trading Core

This project currently implements a small local trading core for deterministic
paper-trading experiments. The core takes explicit inputs and returns structured
results without reaching out to brokers, schedulers, model services, or external
state.

## Current Status

- `413` tests are passing, with `4` skipped paper-integration tests by default.
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
  risk-approved row selection.
- Phase 17 Step 2 adds a minimal internal `ExecutionIntent` contract and pure
  builder that wrap approved source rows by identity without submission.
- Phase 17 Step 3 hardens `ExecutionIntent` traceability with tests and docs
  only; the object remains source-only and pre-submission.
- Phase 18 Step 1 documents the future execution-planning boundary after
  `ExecutionIntent` construction before implementation.
- Phase 18 Step 2 adds a minimal immutable `ExecutionPlan` batch container and
  pure builder; no execution-planning policy or broker behavior has been added.
- Phase 18 Step 3 hardens `ExecutionPlan` traceability with tests and docs
  only; the object remains a minimal pre-broker batch container.
- Phase 19 Step 1 documents the future execution-planning policy boundary after
  minimal `ExecutionPlan` construction; no policy implementation or runtime
  behavior has been added.
- Phase 19 Step 2 adds a minimal immutable planning policy result contract and
  no-op pass-through policy; all intents are currently accepted and no real
  planning policy decisions have been added.
- Phase 19 Step 3 hardens `PlanningPolicyResult` traceability with tests and
  docs only; accepted and skipped traceability still flows through
  `ExecutionIntent.source_evaluation`.
- Phase 20 Step 1 documents the future max-intents planning policy boundary as
  a no-code design phase; no max-intents policy implementation or runtime
  behavior has been added.
- Phase 20 Step 2 adds the first real planning policy:
  `MaxAcceptedIntentsPolicyConfig`,
  `MAX_INTENTS_PER_PLAN_EXCEEDED_REASON`, and
  `apply_max_intents_execution_planning_policy(...)`.
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
  -> build_execution_intents_from_risk_approved(...)
  -> immutable ExecutionIntent tuple
  -> build_execution_plan(...)
  -> immutable ExecutionPlan
  -> apply_noop_execution_planning_policy(...)
  -> immutable PlanningPolicyResult
  -> future broker-facing execution request construction
  -> future broker adapter / execution layer
```

Phase 20 Step 2 adds the implemented max-intents policy at the same pre-broker
policy boundary as an alternate pure policy function:

```text
immutable ExecutionPlan
  -> apply_max_intents_execution_planning_policy(...)
  -> immutable PlanningPolicyResult
  -> future broker-facing execution request construction
  -> future broker adapter / execution layer
```

The screener-to-signal segment does not call risk, broker, Alpaca, execution,
CLI, scheduler, ML, or LLM trading-path logic. Any `ProposedOrder` returned by
signal evaluation is a proposed signal output only. The Signal -> Risk layer
then checks proposed orders with `RiskEngine` only, keeps no-signal rows with
`risk=None`, and returns risk verdicts without executing or submitting anything.
Risk-approved means allowed by risk, not executed, submitted, or broker-ready.
The risk-approved selector keeps only those permission rows in order. Phase 17
Step 2 can wrap approved rows in internal `ExecutionIntent` objects, but those
intents remain pre-submission and broker-agnostic. They preserve the source
`SignalRiskEvaluation` by identity. Phase 17 Step 3 hardens that traceability:
the proposed order, risk verdict, and status are reachable through
`intent.source_evaluation.order`, `intent.source_evaluation.risk`, and
`intent.source_evaluation.status`, not through convenience fields on the
intent. Intents do not call brokers, route orders, submit orders, reserve batch
cash, resolve same-symbol conflicts, use schedulers, persist anything, mutate
portfolios, or add ML or LLM trading-path logic.
Phase 18 Step 1 documents the future execution-planning boundary after those
intents. Phase 18 Step 2 adds a minimal immutable `ExecutionPlan` batch
container for intents. The plan preserves intent order and identity only. It
does not call brokers, route orders, submit orders, reserve batch cash, resolve
same-symbol conflicts, generate idempotency keys or client order IDs, use
schedulers, persist anything, mutate portfolios, or add ML or LLM trading-path
logic.
Phase 18 Step 3 hardens that traceability: proposed orders, risk verdicts, and
statuses remain reachable through `plan.intents[n].source_evaluation.order`,
`plan.intents[n].source_evaluation.risk`, and
`plan.intents[n].source_evaluation.status`, not through convenience fields on
the plan.
Phase 19 Step 1 documents a future execution-planning policy boundary after
minimal plan construction and before broker-facing request construction. The
future policy may later make deterministic batch-level eligibility decisions,
but no policy has been implemented. `ExecutionPlan` remains a container, while
future planning policy remains the separate conceptual decision layer.
Phase 19 Step 2 adds only the first policy-result boundary:
`PlanningPolicyResult` and `SkippedExecutionIntent`, plus
`apply_noop_execution_planning_policy(...)`. The no-op policy accepts every
intent currently in the plan, preserves intent order and identity, preserves
source evaluation identity through accepted intents, and produces no skipped
intents. `skipped_intents` exists only as a future traceability shape.
Phase 19 Step 3 hardens that traceability. Accepted-intent traceability flows
through `result.accepted_intents[n].source_evaluation`. Skipped-intent
traceability flows through
`result.skipped_intents[n].intent.source_evaluation`. Proposed orders, risk
verdicts, and statuses remain reachable only through the source
`SignalRiskEvaluation` object. `PlanningPolicyResult` and
`SkippedExecutionIntent` do not expose direct broker, order, risk, status, fill,
idempotency, cash-reservation, priority, SDK, Alpaca, or persistence fields.
Phase 20 Step 1 documents a future max-intents planning policy as the first
real policy concept after minimal plan construction. Phase 20 Step 2 implements
that narrow policy. `apply_max_intents_execution_planning_policy(...)` accepts
the first `N` intents from an `ExecutionPlan`, skips later intents with the
deterministic reason `"max_intents_per_plan_exceeded"`, and preserves accepted
and skipped intent object identity. `MaxAcceptedIntentsPolicyConfig` requires an
explicit `int >= 1`; `bool` and `None` are rejected. The no-op policy remains
separate for no-cap pass-through behavior.
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
It distinguishes selected risk-approved rows from execution intents:
risk-approved rows are permission signals only, while an execution intent is a
deterministic, immutable, auditable, broker-agnostic internal instruction
candidate prepared before any broker adapter.

Phase 17 Step 2 adds `ExecutionIntent` and
`build_execution_intents_from_risk_approved(...)` in
`src/algotrader/orchestration/risk_execution_flow.py`. `ExecutionIntent` has
only `source_evaluation: SignalRiskEvaluation`, preserving the source row by
identity without inventing screener rank, original index, broker IDs,
client-order IDs, idempotency keys, persistence metadata, fill fields, SDK
objects, Alpaca-specific fields, or LLM-derived fields. The builder returns an
immutable tuple for risk-approved rows only and skips `no_signal` and
`risk_rejected` rows.

No broker routing, order submission, Alpaca change, `submit_order`,
client-order-id generation, idempotency implementation, batch cash reservation,
same-symbol conflict resolution, scheduler/runtime behavior, persistence,
portfolio mutation, fills, ML, or LLM trading-path logic has been added.

Phase 17 Step 3 hardens the traceability contract without production-code
changes. `ExecutionIntent` still has exactly one dataclass field,
`source_evaluation`; it does not expose direct `order`, `risk`, `status`,
`symbol`, `quantity`, `side`, broker, account, venue, idempotency, submission,
fill, SDK, Alpaca, or persistence fields. Convenience properties should not be
added without a later explicit design phase.

Phase 18 Step 1 documents the future execution-planning boundary in
[`docs/design/phase18_execution_planning_boundary.md`](design/phase18_execution_planning_boundary.md).
It distinguishes `ExecutionIntent` from an execution-planning boundary.
`ExecutionIntent` is an internal pre-submission source wrapper. Step 1 kept
`ExecutionPlan` conceptual only and added no broker routing, order submission,
`client_order_id` generation, idempotency implementation, persistence writes,
batch cash reservation, same-symbol conflict resolution, scheduler/runtime
behavior, portfolio mutation, fills, ML, or LLM trading-path logic.

Phase 18 Step 2 adds the minimal `ExecutionPlan` contract in
`src/algotrader/orchestration/execution_planning_flow.py`.
`ExecutionPlan` has only `intents: tuple[ExecutionIntent, ...]` and is an
immutable batch container, not an executable instruction. `build_execution_plan(...)`
accepts any iterable of `ExecutionIntent` objects and returns an immutable plan
while preserving intent order and identity. Proposed orders and risk verdicts
remain reachable through `plan.intents[n].source_evaluation.order` and
`plan.intents[n].source_evaluation.risk`.

No cash reservation, buying-power reservation, same-symbol conflict handling,
duplicate or competing order policy, priority policy, idempotency,
`client_order_id`, broker routing, order submission, persistence writes,
scheduler/runtime behavior, portfolio mutation, fills, reconciliation changes,
ML, or LLM trading-path logic has been added.

Phase 18 Step 3 hardens the `ExecutionPlan` traceability contract without
production-code changes. `ExecutionPlan` still has exactly one dataclass field:
`intents`. Each plan entry is the exact original `ExecutionIntent` object, and
each intent's `source_evaluation` remains the exact original
`SignalRiskEvaluation` object. Proposed orders, risk verdicts, and statuses are
reachable through `plan.intents[n].source_evaluation`, not through direct
`ExecutionPlan` fields.

No direct order, risk, status, symbol, quantity, side, selected/rejected/skipped
intent, broker, account, venue, submission, fill, idempotency,
`client_order_id`, cash reservation, priority/rank, SDK, Alpaca, or persistence
fields exist on `ExecutionPlan`.

Phase 19 Step 1 documents the future execution-planning policy boundary in
[`docs/design/phase19_execution_planning_policy.md`](design/phase19_execution_planning_policy.md).
That policy remains conceptual only. No policy result object, accepted/skipped
buckets, cash reservation, buying-power reservation, same-symbol conflict
handling, duplicate/competing order handling, priority/ranking behavior,
broker-facing request construction, broker routing, idempotency, persistence,
audit logging writes, order submission, runtime behavior, ML, or LLM
trading-path logic has been implemented.

Phase 19 Step 2 adds the minimal policy result contract in
`src/algotrader/orchestration/execution_planning_policy.py`. `PlanningPolicyResult`
is a deterministic pre-broker result container with `accepted_intents` and
`skipped_intents`. `SkippedExecutionIntent` stores an `ExecutionIntent` plus a
plain deterministic reason string for future traceability. The current
`apply_noop_execution_planning_policy(...)` function is pass-through only: all
input plan intents are accepted unchanged and no skipped intents are produced.

No cash reservation, buying-power reservation, same-symbol conflict handling,
duplicate or competing order policy, priority policy, idempotency,
`client_order_id`, broker routing, order submission, persistence writes,
scheduler/runtime behavior, portfolio mutation, fills, reconciliation changes,
ML, or LLM trading-path logic has been added.

Phase 19 Step 3 keeps the policy implementation unchanged and hardens the
contract with tests and documentation only. `PlanningPolicyResult` still has
only `accepted_intents` and `skipped_intents`; `SkippedExecutionIntent` still
has only `intent` and `reason`. Convenience fields or properties such as
`orders`, `risks`, `statuses`, `symbols`, `accepted_orders`, `skipped_orders`,
`client_order_ids`, `idempotency_keys`, `broker_order_ids`, `cash_reserved`,
`buying_power_reserved`, `priority`, or `rank` remain excluded.

Phase 20 Step 1 documents the future maximum accepted intents per plan policy in
[`docs/design/phase20_max_intents_policy.md`](design/phase20_max_intents_policy.md).
Phase 20 Step 2 implements that boundary as a pure policy function.
`MaxAcceptedIntentsPolicyConfig` is a frozen, slotted config with exactly one
field, `max_accepted_intents`, and the value must be exactly an `int` greater
than or equal to `1`. `None` does not mean no cap; the no-op policy remains the
explicit no-cap behavior.

`apply_max_intents_execution_planning_policy(...)` caps accepted intents
deterministically using explicit configuration and existing plan order, then
places later intents in `skipped_intents` with the deterministic reason
`"max_intents_per_plan_exceeded"`. It preserves accepted and skipped
`ExecutionIntent` identity, and source `SignalRiskEvaluation` identity remains
traceable through `source_evaluation`.

No index/provenance field, priority/ranking behavior, cash reservation,
buying-power reservation, same-symbol conflict handling, duplicate/competing
order policy, idempotency, `client_order_id` generation, broker routing,
persistence, audit logging writes, order submission, scheduler or runtime
behavior, ML, or LLM trading-path logic has been implemented.

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
- Real execution-planning policy decisions beyond no-op pass-through and the
  max-intents cap
- Accepted/rejected/skipped execution-planning policy logic beyond the
  max-intents cap
- Accepted/rejected/skipped execution-planning decisions beyond the max-intents
  cap
- Direct ExecutionPlan order/risk/status convenience fields
- Execution-intent broker routing or adapter integration
- Broker-facing request construction
- Order submission
- Client order ID generation
- Idempotency implementation
- Batch cash reservation
- Buying-power reservation
- Same-symbol execution conflict handling
- Duplicate or competing order policy implementation
- Priority or ranking policy implementation
- Persistence writes
- Audit logging writes
- Reconciliation loop against external broker state
- Scheduler or runtime loop
- LangGraph
- ML models
- LLM logic in the trading path
- Live trading

## Next Recommended Phase

The next phase should keep any execution-boundary work pure and synthetic unless
explicitly approved otherwise. A safe follow-up could design one explicit
planning policy decision at a time, while still excluding broker wiring, order
submission, scheduler/runtime behavior, persistence, cash reservation side
effects, ML, and LLM trading-path logic.

Real Alpaca SDK work and Phase 7 reconciliation remain deferred unless
explicitly approved.

## Alpaca Paper Planning Link

See [Alpaca Paper Integration Plan](alpaca_paper_integration_plan.md) for the safe future path toward Alpaca paper integration. That plan is documentation-only and does not add SDK dependencies, credentials, network calls, or runtime broker behavior.
