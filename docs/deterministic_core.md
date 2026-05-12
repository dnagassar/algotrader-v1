# Deterministic Trading Core

This project currently implements a small local trading core for deterministic
paper-trading experiments. The core takes explicit inputs and returns structured
results without reaching out to brokers, schedulers, model services, or external
state.

## Current Status

- `778` tests are passing, with `4` skipped paper-integration tests by default.
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
- Phase 20 Step 3 hardens max-intents traceability with tests and docs only;
  no production source or runtime behavior changed.
- Phase 21 Step 1 documents the research/validation boundary; research,
  backtesting, and LLM-assisted research workflows remain advisory until
  promoted through explicit deterministic contracts.
- Phase 21 Step 2 adds a minimal immutable, slotted validated research artifact
  metadata contract; it is evidence only and has no trading behavior.
- Phase 21 Step 3 hardens validated research artifact traceability and ordering
  guarantees with tests and docs only; no production source changed.
- Phase 22 Step 1 documents the future validated signal definition boundary;
  signal definitions remain promoted contracts, not execution decisions.
- Phase 22 Step 2 adds the minimal immutable, slotted
  `ValidatedSignalDefinition` metadata contract; it does not evaluate signals
  or create execution intents.
- Phase 22 Step 3 hardens validated signal definition traceability and tuple
  ordering with tests and docs only; no production source changed.
- Phase 23 Step 1 documents the future signal evaluation, clock, and as-of
  boundary; no production source or runtime behavior changed.
- Phase 23 Step 2 adds a minimal deterministic time contract with UTC-aware
  validation, an injectable `Clock` protocol, `FixedClock`, and an as-of helper.
- Phase 23 Step 3 hardens clock/timestamp traceability with tests and docs
  only; no production source changed.
- Phase 24 Step 1 documents the future `SignalEvaluationResult` boundary as
  advisory deterministic output only; no production source or runtime behavior
  changed.
- Phase 24 Step 2 adds the minimal immutable, slotted
  `SignalEvaluationResult` metadata contract; it does not evaluate signals,
  create execution intents, or approve trades.
- Phase 24 Step 3 hardens `SignalEvaluationResult` traceability with tests and
  docs only; no production source or runtime behavior changed.
- Phase 25 Step 1 documents the future deterministic signal evaluator boundary
  only; no evaluator exists yet, signal evaluation remains advisory and
  pre-risk, and LLMs remain outside the trading hot path.
- Phase 25 Step 2 adds the minimal immutable
  `SignalEvaluationInputSnapshot` metadata/reference contract; it provides
  deterministic input traceability only and still adds no evaluator, signal
  computation, live data access, risk approval, execution behavior, broker
  behavior, runtime behavior, persistence, ML, or LLM trading-path logic.
- Phase 25 Step 3 hardens `SignalEvaluationInputSnapshot` traceability with
  tests and docs only; no production source or runtime behavior changed.
- Phase 26 Step 1 documents the future no-op signal evaluator boundary only;
  no evaluator implementation exists yet, evaluator outputs remain advisory
  and pre-risk, evaluator modules must not import broker, execution, risk,
  runtime, persistence, ML, or LLM modules, and LLMs remain outside the trading
  hot path.
- Phase 26 Step 2 reviews `SignalEvaluationResult` no-op readiness and
  concludes the existing metadata-only result contract is sufficient for a
  future minimal no-op evaluator; no no-op marker, result kind, evaluator kind,
  evaluator implementation, production behavior, or trading-path behavior was
  added.
- Phase 26 Step 3 adds the minimal frozen, slotted `NoOpSignalEvaluator`
  contract as the first evaluator-shaped code. It only constructs advisory
  `SignalEvaluationResult` metadata from explicit deterministic inputs and
  adds no real signal computation, scoring, ranking, direction, actionability,
  risk approval, execution behavior, broker behavior, runtime behavior,
  persistence, ML, or LLM trading-path logic.
- Phase 26 Step 4 hardens `NoOpSignalEvaluator` traceability tests and docs
  only. No production behavior was added; the evaluator remains deterministic,
  advisory-only, offline-safe, broker-isolated, and traceable without implying
  actionability.
- Phase 27 Step 1 documents the real signal evaluator admission boundary only.
  No real evaluator exists yet, and actual signal computation remains forbidden
  until explicit deterministic input-value contracts and admission criteria are
  implemented.
- Phase 27 Step 2 documents the future deterministic signal input-value
  boundary only. No input-value contract exists yet,
  `SignalEvaluationInputSnapshot` remains reference metadata only, and no real
  evaluator or signal computation exists yet.
- Phase 27 Step 3 adds the minimal immutable `SignalInputValue` contract for
  one explicit observed value with UTC-aware timestamp and source traceability.
  It adds no real evaluator, signal computation, feature computation, scoring,
  ranking, direction, actionability, risk approval, execution behavior, broker
  behavior, runtime behavior, persistence, ML, or LLM trading-path logic.
- Phase 27 Step 4 hardens `SignalInputValue` traceability with tests and docs
  only. No production behavior was added; the contract remains immutable,
  scalar-only, non-computational, and isolated from trading-path behavior.
- Phase 28 Step 1 documents the future signal input bundle boundary only.
  `SignalInputValue` remains a single observed-value contract, and no real
  evaluator or signal computation exists yet.
- Phase 28 Step 2 adds the minimal immutable `SignalInputBundle` contract. It
  groups explicit `SignalInputValue` objects for future evaluator use,
  preserves ordering and input value identity, rejects duplicate names, and
  rejects lookahead values where `observed_at > as_of`. It does not validate
  completeness against `SignalEvaluationInputSnapshot`, compute features or
  signals, score, rank, infer direction, recommend trades, approve risk, mutate
  execution plans, access live data, route to brokers, submit orders, use
  scheduler/runtime/persistence behavior, run ML, or use LLMs in the trading
  path.
- Phase 28 Step 3 hardens `SignalInputBundle` traceability with tests and docs
  only. No production behavior was added; the bundle remains an immutable
  grouping contract for explicit `SignalInputValue` objects and still does not
  validate completeness or interpret values.
- Phase 28 Step 4 documents the future completeness validation boundary between
  `SignalEvaluationInputSnapshot.required_input_names` and
  `SignalInputBundle.values`. At that step, no completeness validator existed;
  the bundle remained a grouping contract only, and no real evaluator or signal
  computation existed yet.
- Phase 28 Step 5 adds the minimal immutable
  `SignalInputBundleCompletenessResult` contract and pure
  `validate_signal_input_bundle_completeness(...)` function. Completeness
  validation remains separate from `SignalInputBundle` construction, compares
  required names with bundle value names only, reports missing and extra names
  deterministically, and still adds no real evaluator or signal computation.
- Phase 28 Step 6 hardens completeness validation traceability with tests and
  docs only. No production behavior was added; completeness remains name-only,
  metadata-only, deterministic, non-mutating, separate from bundle
  construction, and isolated from trading-path behavior.
- Phase 29 Step 1 defines the first real evaluator design gate as a
  documentation-only boundary. No real evaluator exists yet, real signal
  computation remains forbidden until an evaluator-specific design satisfies
  the gate, the current explicit-input stack does not make outputs actionable,
  evaluator output remains advisory and pre-risk, and LLMs remain outside the
  trading hot path.
- Phase 29 Step 2 selects a first real evaluator candidate as documentation
  only: a minimal threshold-style advisory evaluator over one explicit scalar
  `SignalInputValue`. No real evaluator exists yet, real signal computation
  remains forbidden until evaluator-specific design and tests satisfy the gate,
  evaluator output remains advisory and pre-risk, and LLMs remain outside the
  trading hot path.
- Phase 29 Step 3 designs the selected first evaluator candidate contract as
  documentation only. The future threshold-style advisory evaluator candidate
  may consume one explicit scalar `SignalInputValue`, preferably `Decimal`, but
  no real evaluator exists yet, real signal computation remains forbidden until
  implementation is explicitly scoped, evaluator output remains advisory and
  pre-risk, and LLMs remain outside the trading hot path.
- Phase 29 Step 4 defines the first real evaluator test matrix only. No real
  evaluator exists yet, real signal computation remains forbidden until
  implementation is explicitly scoped, evaluator output remains advisory and
  pre-risk, and LLMs remain outside the trading hot path.
- Phase 29 Step 5 reviews first real evaluator implementation readiness only.
  No real evaluator exists yet, real signal computation remains forbidden
  unless explicitly scoped in a later implementation phase, evaluator output
  remains advisory and pre-risk, and LLMs remain outside the trading hot path.
- Phase 29 Step 6 designs threshold evaluator constants/output semantics only.
  No real evaluator exists yet, real signal computation remains forbidden
  unless explicitly scoped in a later implementation phase, evaluator output
  remains advisory and pre-risk, and LLMs remain outside the trading hot path.
- Phase 30 Step 1 defines the research support required before a real
  threshold-style evaluator may be implemented. No real evaluator exists yet,
  real signal computation remains forbidden, evaluator output remains advisory
  and pre-risk, and LLMs remain outside the trading hot path.
- Phase 30 Step 5 creates an unreviewed research candidate backlog only. No
  real evaluator exists yet, real signal computation remains forbidden,
  evaluator output remains advisory and pre-risk, and LLMs remain outside the
  trading hot path.
- Phase 30 Step 6 selects the first research candidate sourcing target only.
  No real evaluator exists yet, real signal computation remains forbidden,
  evaluator output remains advisory and pre-risk, and LLMs remain outside the
  trading hot path.
- Phase 31 Step 1 adds a reusable Codex operating context and resets the
  research-track workflow for shorter future prompts. Docs, research, and
  planning phases may now combine related documentation updates when low-risk
  and code-free; production-code phases remain narrow, test-first, explicitly
  scoped, and heavily verified.
- Phase 31 Step 2 adds a concise research-track next action plan. It keeps
  `P30-BL-001` as the first unreviewed sourcing target, confirms backlog
  entries are not evidence, allows research agents only as assistants, and
  keeps real evaluator implementation blocked.
- Phase 31 Step 3 normalizes the `P30-BL-001` source package. That step made
  the candidate source-package-ready only and did not validate, approve, or
  justify trading or threshold behavior.
- Phase 31 Step 4 formally reviews the Tier A `P30-BL-001` sources. Tier A
  conditionally supports mechanics and methodology only; `P30-BL-001` remains
  unvalidated, not approved, not production-ready, not implementation-ready,
  and not a trading, threshold, validated-signal-definition, or evaluator
  implementation justification.
- Phase 31 Step 5 routes the Tier A result through an evidence gap plan. It
  recommends a formal mechanics-only candidate artifact review summary and
  keeps production threshold, signal-definition, and evaluator implementation
  routes blocked.
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

For compressed future prompts and research-track work, use
[`docs/agent_context/codex_operating_context.md`](agent_context/codex_operating_context.md)
as the first-read project summary. Its high-level planning pipeline is:

```text
Market Data -> Features -> Screener -> Signals -> Risk -> ExecutionIntent -> ExecutionPlan -> PlanningPolicy -> future OMS/Broker -> Fills/Portfolio/Reconciliation
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
Phase 20 Step 3 keeps production source unchanged and hardens the traceability
contract with focused tests for accepted/skipped intent identity, accepted and
skipped ordering, deterministic skip reasons, source-evaluation reachability,
input plan non-mutation, and absence of forbidden broker/execution/planning
leakage fields.
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

Phase 20 Step 3 is tests/docs-only hardening. It adds no production source
changes and keeps the max-intents policy narrow, pure, deterministic,
pre-broker, and source-evaluation driven.

Phase 23 Step 1 documents a future signal evaluation, clock, and as-of boundary
in
[`docs/design/phase23_signal_evaluation_clock_boundary.md`](design/phase23_signal_evaluation_clock_boundary.md).
That future evaluator remains conceptual only here. It may later consume
validated signal definition metadata, explicit input snapshots, explicit
observation timestamps, an explicit `as_of` timestamp, deterministic context,
and snapshot fingerprints. It must produce advisory signal-evaluation metadata
only, not orders, risk approvals, execution intents, execution plans, ranking
or priority decisions, broker requests, portfolio mutations, or LLM-generated
trade decisions.

Time must be explicit in deterministic evaluation. Future deterministic signal,
risk, and orchestration layers should receive timezone-aware timestamps as
data, prefer UTC internally, reject naive datetimes, and avoid direct
wall-clock, randomness, UUID-randomness, or environment-variable reads except
inside explicit boundary modules.

Phase 23 Step 2 adds the minimal deterministic time primitives in
`src/algotrader/core/time.py`: `require_utc_datetime(...)`, `Clock`,
`FixedClock`, and `assert_not_after_as_of(...)`. These primitives validate
explicit UTC-aware datetimes, provide an injectable fixed clock for
deterministic tests, and reject observations after `as_of`.

This contract does not read system time, fetch live data, evaluate signals,
compute features, approve trades, mutate execution plans, interact with broker
or Alpaca, schedule runtime behavior, persist records, train ML models, or put
LLMs in the trading path.

Phase 23 Step 3 hardens the time contract with focused tests only. The tests
pin exact UTC datetime identity preservation, repeated `FixedClock.now()`
identity, fixed-clock immutability, naive and non-UTC rejection, equality and
before-`as_of` allowance, after-`as_of` rejection, dependency independence,
absence of trading-path fields, and absence of hidden nondeterministic API
calls such as wall-clock reads, random generators, UUID randomness, and
environment access.

Phase 24 Step 1 documents the future `SignalEvaluationResult` boundary in
[`docs/design/phase24_signal_evaluation_result_boundary.md`](design/phase24_signal_evaluation_result_boundary.md).
Phase 24 Step 2 adds the minimal `SignalEvaluationResult` contract in
`src/algotrader/signals/signal_evaluation_result.py`. The result is advisory
deterministic signal-evaluation metadata produced by applying a validated
signal definition to explicit input snapshots at an explicit `as_of` boundary.
It carries evaluation id, signal definition id/version, source artifact
id/version, input fingerprint, UTC-aware `as_of`, UTC-aware `evaluated_at`,
deterministic output value, reason code, diagnostics, assumptions, and
limitations.

Signal evaluation outputs are advisory. They do not create orders, broker
requests, execution intents, or execution plans. They do not approve trades,
mutate portfolios, mutate execution plans, reserve cash or buying power, submit
orders, rank execution candidates, or produce LLM-generated trading decisions.
Risk approval remains in the risk layer, execution intent and execution plan
creation remain in the execution layer, and broker behavior remains isolated.
Explicit UTC-aware time remains required: `as_of` must be explicit,
`evaluated_at` must be explicit or injected by a deterministic clock in a
future implementation, naive datetimes must be rejected, hidden system time
reads are not allowed, and no input observation may be after `as_of`.

Phase 24 Step 3 keeps production source unchanged and hardens the traceability
contract. Tests pin exact `as_of` and `evaluated_at` object identity,
deterministic ordering and immutability of all tuple fields, exact preservation
of trace string fields, advisory-only surface area, absence of trading-path
fields, and independence from execution, risk, broker, runtime, persistence,
ML, and LLM modules. `SignalEvaluationResult` is not a signal evaluator, does
not compute signals, does not approve risk, does not create execution intents,
does not mutate execution plans, does not route to brokers or Alpaca, does not
submit orders, does not touch scheduler/runtime/persistence, and does not use
ML or LLMs in the trading path.

## Research And Validation Boundary

Phase 21 Step 1 documents the future research/validation boundary in
[`docs/design/phase21_research_validation_boundary.md`](design/phase21_research_validation_boundary.md).
Phase 21 Step 2 adds the minimal validated artifact metadata contract in
`src/algotrader/research/validated_artifact.py`.
Phase 21 Step 3 hardens that contract with tests and documentation only.

Historical research, feature exploration, backtesting, walk-forward
validation, regime analysis, strategy notebooks/scripts, and LLM-assisted
research summaries are outside the deterministic trading core. They may propose
ideas, record evidence, and support human review, but their outputs are
advisory until promoted through explicit validated artifacts.

Validated artifacts may include approved feature definitions, approved signal
definitions, validated strategy configs, documented assumptions, evaluation
metrics, acceptance criteria, and versioned research outputs. These artifacts
are evidence packages, not runtime behavior by themselves.

The current production contract is intentionally tiny:
`ResearchMetric(name, value)` and `ValidatedResearchArtifact(...)`. The artifact
stores an identifier, name, version, description, validation timestamp, metrics,
assumptions, limitations, and approved advisory uses. It does not create
signals, approve trades, mutate execution plans, call risk, submit orders,
interact with broker or Alpaca, schedule runtime behavior, persist records,
ingest live data, train ML models, or put LLMs in the hot path.

The hardened traceability tests prove that metric identity is preserved inside
`ValidatedResearchArtifact.metrics`, metrics, assumptions, limitations, and
approved advisory uses preserve deterministic order, tuple fields cannot be
mutated after construction, and the artifact remains independent from
`ExecutionPlan`, `ExecutionIntent`, `PlanningPolicyResult`, and risk-evaluation
types.

The deterministic core may consume only approved, explicit, validated inputs.
Future research-derived behavior must enter through deterministic contracts,
types, configs, fixtures, and pure functions that are test-first, offline, and
credential-free. Normal `python -m pytest` must remain offline and
credential-free.

Phase 22 Step 1 documents the future validated signal definition boundary in
[`docs/design/phase22_validated_signal_definition_boundary.md`](design/phase22_validated_signal_definition_boundary.md).
Phase 22 Step 2 adds the minimal validated signal definition metadata contract
in `src/algotrader/signals/validated_signal_definition.py`.
Phase 22 Step 3 hardens that contract with tests and documentation only.
A future validated signal definition may be supported by a validated research
artifact, but it is not raw research output, not a backtest result, not a
feature, not a strategy, not an execution intent, not an execution plan, and
not a broker order. It is a promoted deterministic contract candidate for a
future signal evaluator.

Validated signal definitions are not execution decisions. They do not create
signals by themselves, approve trades, mutate execution plans, reserve cash or
buying power, rank or prioritize orders, submit orders, interact with broker or
Alpaca, schedule runtime behavior, persist records, ingest live data, train ML
models, or put LLMs in the hot path.

The current contract is definition metadata only:
`ValidatedSignalDefinition(...)` stores a signal id, name, version,
description, source validated research artifact id/version, required inputs,
output type, deterministic evaluation rule reference, approved advisory uses,
assumptions, and limitations. It references validated research artifacts by
stable strings only and does not import runtime research behavior.

The hardened traceability tests prove that source artifact id/version strings
are preserved exactly, `required_inputs`, `approved_for`, `assumptions`, and
`limitations` preserve deterministic order, tuple fields cannot be mutated
after construction, and signal definitions remain independent from
`ValidatedResearchArtifact` runtime objects, `ExecutionPlan`,
`ExecutionIntent`, `PlanningPolicyResult`, risk-evaluation types, broker,
runtime/scheduler, and persistence modules.

Phase 23 Step 1 documents the next future boundary after validated signal
definitions: deterministic signal evaluation with explicit clock and as-of
rules. Validated signal definitions remain metadata-only. Future signal
evaluations are advisory reports, not execution decisions. They may later carry
deterministic signal values, scores or buckets, reason codes, input snapshot
fingerprints, evaluation fingerprints, and assumptions or limitations
references, but they must not carry `ProposedOrder`, orders, order IDs,
client-order IDs, broker requests, symbol-specific order instructions,
execution-command sides, quantities, cash or buying-power reservations,
portfolio mutation, risk approval, execution intents, execution plans, fills,
ranking/priority decisions, or LLM-generated trade decisions.

The deterministic core consumes only explicit promoted contracts. A future
evaluator must receive explicit input snapshots and explicit timezone-aware
timestamps. Inputs observed after the supplied `as_of` timestamp should be
rejected, hidden live data fetches and implicit data revisions should be
forbidden, and parameter changes should require a new definition or context
version.

Phase 23 Step 2 implements only the tiny shared time contract that future
deterministic components can receive explicitly. It rejects naive and non-UTC
datetimes, exposes an injectable clock protocol, provides a frozen fixed clock,
and adds a lookahead-prevention helper for `observed_at <= as_of`. It does not
provide a system clock, scheduler, runtime loop, live-data fetch, signal
evaluation, risk approval, execution-plan mutation, broker behavior, Alpaca
behavior, persistence, ML, or LLM trading-path logic.

Phase 23 Step 3 keeps production source unchanged and hardens the traceability
contract. Time contracts remain deterministic primitives only. They do not
evaluate signals, fetch live data, read system time in deterministic paths,
approve trades, mutate execution plans, interact with broker, Alpaca,
scheduler/runtime, persistence, ML, or LLM trading-path logic. UTC-aware
timestamp enforcement and lookahead-prevention behavior are pinned by tests.

Phase 24 Step 1 documents the next future boundary: advisory
`SignalEvaluationResult` output. Phase 24 Step 2 adds the minimal immutable
contract for that output. `ValidatedResearchArtifact` remains evidence,
`ValidatedSignalDefinition` remains approved metadata, and
`SignalEvaluationResult` remains advisory deterministic metadata only. A future
signal-to-risk bridge may consume that output only after a separate design and
implementation phase. Signal evaluation does not create orders, approve trades,
mutate execution plans, interact with brokers, or put LLMs in the hot path.
Phase 24 Step 3 hardens this result contract with tests and documentation only;
no production behavior was added.

Phase 25 Step 1 documents the future deterministic signal evaluator boundary in
[`docs/design/phase25_signal_evaluator_boundary.md`](design/phase25_signal_evaluator_boundary.md).
The future evaluator is conceptual only: it may later transform
`ValidatedSignalDefinition` metadata plus explicit deterministic input
snapshots and explicit UTC-aware `as_of`/`evaluated_at` timestamps into
advisory `SignalEvaluationResult` objects. No evaluator exists yet, no signal
computation or runtime behavior has been added, signal evaluation remains
pre-risk and advisory, and LLMs remain outside the trading hot path.

Phase 25 Step 2 adds only the minimal input snapshot/reference contract in
`src/algotrader/signals/signal_evaluation_input.py`.
`SignalEvaluationInputSnapshot` stores `snapshot_id`, explicit UTC-aware
`as_of`, ordered `required_input_names`, and ordered `source_ids`. It exists
only to provide deterministic, explicit input traceability for a future
evaluator. It does not add a signal evaluator, compute signals or features,
access live data, approve risk, create execution intents, mutate execution
plans, route to brokers, interact with Alpaca, use scheduler/runtime or
persistence behavior, train or run ML, or use LLMs in the trading path.

Phase 25 Step 3 keeps production source unchanged and hardens the traceability
contract with focused tests and documentation only. The tests pin exact `as_of`
identity preservation, exact trace string preservation, deterministic tuple
ordering, tuple immutability, input-list mutation isolation, metadata-only
surface area, absence of signal output fields, absence of score, direction,
confidence, order, risk, execution, broker, account, position, fill, portfolio,
cash, buying-power, scheduler, runtime, persistence, ML, and LLM fields, no
dependency on `SignalEvaluationResult`, no downstream risk, execution, broker,
runtime, persistence, ML, or LLM dependencies, and no hidden wall-clock,
random, network, filesystem-write, environment-variable, broker SDK, or Alpaca
access.
`SignalEvaluationInputSnapshot` remains input traceability metadata only; it is
not a signal evaluator and does not compute signals or features.

Phase 26 Step 1 documents the future no-op signal evaluator boundary in
[`docs/design/phase26_signal_evaluator_noop_boundary.md`](design/phase26_signal_evaluator_noop_boundary.md).
No evaluator implementation exists yet. The future no-op evaluator is
conceptual only: it may later construct advisory `SignalEvaluationResult`
metadata from `ValidatedSignalDefinition`, `SignalEvaluationInputSnapshot`,
explicit UTC-aware `as_of`, explicit UTC-aware `evaluated_at`, and deterministic
metadata already available through existing contracts. It must not compute real
signal values, inspect live market data, compute features, rank, score, infer
direction, approve or reject trades, create execution intents, mutate execution
plans, or imply actionability.

Evaluator output remains strictly advisory and pre-risk. A result from any
future evaluator is not a signal firing, recommendation, risk approval,
execution instruction, execution intent, order request, or broker payload. No
sizing decision, exposure calculation, cash reservation, buying-power check, or
portfolio-level reasoning has occurred when evaluator output is returned.
Future evaluator modules must not import broker, Alpaca, execution, risk,
runtime/scheduler, persistence, ML, or LLM modules. Any need for one of those
imports is a phase-scope violation requiring a new design review. LLMs remain
outside the trading hot path.

Phase 26 Step 2 reviews whether the existing `SignalEvaluationResult` contract
can safely represent a future no-op evaluator result. The review conclusion is
that the current contract is sufficient for a minimal no-op evaluator. It
already preserves signal definition identity/version, source artifact
identity/version, input snapshot identity through `input_fingerprint`, explicit
UTC-aware `as_of`, explicit UTC-aware `evaluated_at`, `output_value`,
`reason_code`, `diagnostics`, `assumptions`, and `limitations`.

No no-op marker, `result_kind`, or `evaluator_kind` is needed before a minimal
no-op evaluator implementation. A future no-op result need not be structurally
distinguishable from a later real evaluator result by field shape because both
remain advisory metadata. The safer path is to keep any future no-op result
empty/advisory in meaning and traceable through existing metadata fields rather
than adding score, direction, confidence, actionability, or kind fields. Phase
26 Step 2 adds no evaluator implementation, no production behavior, no runtime
behavior, and no trading-path behavior.

Focused validation:

```text
python -m pytest tests/unit/test_signal_evaluation_result.py
42 passed

python -m pytest tests/unit/test_dependency_direction.py
9 passed
```

The full suite is now:

```text
python -m pytest
605 passed, 4 skipped
```

Phase 26 Step 3 adds only the minimal no-op evaluator contract in
`src/algotrader/signals/noop_signal_evaluator.py`.
`NoOpSignalEvaluator` is a frozen, slotted evaluator-shaped object with one
method:

```text
evaluate(definition, input_snapshot, *, as_of, evaluated_at)
    -> SignalEvaluationResult
```

The evaluator accepts a `ValidatedSignalDefinition`, a
`SignalEvaluationInputSnapshot`, and explicit UTC-aware `as_of` and
`evaluated_at` timestamps. It validates timestamps with the deterministic time
contract, rejects naive or non-UTC timestamps, rejects `evaluated_at < as_of`,
rejects input snapshots whose `as_of` is after the result `as_of`, and returns
advisory `SignalEvaluationResult` metadata using existing fields only.

The no-op evaluator preserves signal definition id/version, source artifact
id/version, input snapshot id through `input_fingerprint`, and timestamp object
identity in the returned result. It uses no `result_kind`, `evaluator_kind`,
`is_noop`, or no-op marker field. It does not score, rank, infer direction,
set confidence or probability, expose actionability, recommend trades, approve
risk, create execution intents, mutate execution plans, access live data, route
to brokers, submit orders, use scheduler/runtime/persistence behavior, run ML,
or call LLMs.

Current focused validation for the no-op evaluator boundary:

```text
python -m pytest tests/unit/test_noop_signal_evaluator.py
29 passed

python -m pytest tests/unit/test_dependency_direction.py
9 passed
```

The full suite is now:

```text
python -m pytest
634 passed, 4 skipped
```

Phase 26 Step 4 hardens the existing no-op evaluator contract with tests and
documentation only. No production source changed, and no production behavior was
added. `NoOpSignalEvaluator` remains deterministic and advisory-only: it proves
the evaluator input/output boundary without real signal computation and
preserves traceability without actionability.

The hardened tests pin exact signal definition id/version preservation, exact
source research artifact id/version preservation, exact input snapshot id
preservation through `input_fingerprint`, exact `as_of` and `evaluated_at`
object identity, exact no-op reason code, deterministic ordering for
diagnostics/assumptions/limitations, environment-variable independence,
random-state independence, non-mutation of input contracts and tuple fields,
accepted and rejected timestamp/lookahead edges, advisory-only surface fields,
trading-path isolation, and AST guardrails against hidden wall-clock, random,
environment, network, filesystem-write, database/cache/persistence, broker,
Alpaca, ML, LLM, agent, prompt, and output dependencies.

The no-op evaluator still does not score, rank, infer direction, recommend
trades, approve risk, create execution intents, mutate execution plans, access
live data, route to brokers or Alpaca, submit orders, use scheduler/runtime or
persistence behavior, run ML, or use LLMs in the trading path. Normal pytest
remains offline, credential-free, and safe.

Phase 27 Step 1 documents the admission criteria for any future real
deterministic signal evaluator in
[`docs/design/phase27_real_signal_evaluator_admission_boundary.md`](design/phase27_real_signal_evaluator_admission_boundary.md).
No real evaluator exists yet. Actual signal computation remains forbidden until
the project first designs and implements an explicit deterministic input-value
contract, proves observation timestamps are available at or before `as_of`, and
meets the documented admission criteria for deterministic behavior, lookahead
prevention, no side effects, and no trading-path dependencies.

Even after admission, evaluator output remains advisory and pre-risk. It is not
a recommendation, not risk approval, not an execution intent, not an order
request, not portfolio-aware, not broker-aware, and not actionability by itself.
LLMs remain outside the trading hot path.

Phase 27 Step 2 documents the future deterministic signal input-value boundary
in
[`docs/design/phase27_signal_input_value_boundary.md`](design/phase27_signal_input_value_boundary.md).
No input-value contract exists yet. `SignalEvaluationInputSnapshot` remains
reference metadata only: it preserves `snapshot_id`, UTC-aware `as_of`,
`required_input_names`, and `source_ids`, but it does not carry actual observed
market values, feature values, bar payloads, quote payloads, or computed inputs.

Future input-value contracts are expected to carry explicit deterministic
observed values, observation timestamps, source traceability, value type
constraints, and no-lookahead validation support before any real evaluator can
compute signals. This phase adds no such contract, no real evaluator, and no
signal computation. Evaluator output remains advisory and pre-risk, and LLMs
remain outside the trading hot path.

Phase 27 Step 3 adds the first minimal input-value implementation:
`SignalInputValue` in `src/algotrader/signals/signal_input_value.py`. The
contract is a frozen, slotted dataclass with `name`, `value`, `observed_at`, and
`source_id`. It preserves accepted string values exactly, stores the observed
value without computation or interpretation, validates `observed_at` as an
explicit UTC-aware timestamp, rejects naive and non-UTC timestamps, and rejects
empty or blank `name` and `source_id`.

`SignalInputValue` accepts only deterministic scalar values for the first
contract surface: `Decimal`, `int`, `str`, and `bool`. It does not perform
lookahead validation against an evaluator `as_of`; that belongs to a later
assembly or evaluator-input boundary. It does not compute signals or features,
score, rank, infer direction, recommend trades, approve risk, create execution
intents, mutate execution plans, access live data, route to brokers or Alpaca,
submit orders, use scheduler/runtime/persistence, run ML, or use LLMs in the
trading path. Normal pytest remains offline, credential-free, and safe.

Phase 27 Step 4 hardens `SignalInputValue` traceability with tests and docs
only. The tests now prove exact `name`, `source_id`, `observed_at`, `Decimal`,
`int`, `str`, and `bool` preservation; `bool` remains distinct from `int`; and
accepted values are stored without normalization, rounding, conversion, or
interpretation. They also pin immutability, slots, UTC timestamp validation,
string validation, scalar-only value support, unsupported mutable/object
rejection, no internal evaluator `as_of` or lookahead validation, and no
wall-clock, random, environment, network, filesystem-write, database/cache,
broker, Alpaca, ML, LLM, agent, prompt, or output dependencies.

`SignalInputValue` remains an immutable observed-value contract. It carries
explicit observed scalar values and source/timestamp traceability, but it does
not compute, normalize, rank, score, infer direction, recommend trades, approve
risk, create execution intents, mutate execution plans, access live data, route
to brokers or Alpaca, submit orders, use scheduler/runtime/persistence, run ML,
or use LLMs in the trading path. Normal pytest remains offline,
credential-free, and safe.

Phase 28 Step 1 documents the future signal input bundle boundary in
[`docs/design/phase28_signal_input_bundle_boundary.md`](design/phase28_signal_input_bundle_boundary.md).
Phase 28 Step 2 adds the minimal immutable `SignalInputBundle` contract in
`src/algotrader/signals/signal_input_bundle.py`. The bundle groups explicit
`SignalInputValue` objects for future evaluator use, preserves supplied value
ordering and input value object identity, rejects duplicate names, validates
`as_of` as UTC-aware, and rejects lookahead values where
`SignalInputValue.observed_at > bundle.as_of`.

Phase 28 Step 3 hardens the bundle with tests and documentation only. No
production behavior was added. The hardening pins exact `snapshot_id` string
preservation, exact `as_of` identity preservation, exact grouped value object
identity, exact value ordering, exact value names, source ids, observed
timestamp identity, payload preservation, tuple immutability, duplicate-name
rejection, and lookahead rejection. Multiple bundles built from the same values
in the same order compare equal, while different supplied orders remain
different orders.

The bundle remains an input container only. It is not a signal result,
recommendation, score, rank, direction, risk approval, execution intent, order
request, or portfolio decision. It does not yet validate completeness against
`SignalEvaluationInputSnapshot`. It does not compute signals or features,
implement a real evaluator, score, rank, infer direction, recommend trades,
approve risk, mutate execution plans, access live data, route to brokers or
Alpaca, submit orders, use scheduler/runtime/persistence behavior, run ML, or
use LLMs in the trading path. Evaluator output remains advisory and pre-risk,
and LLMs remain outside the trading hot path.

Phase 28 Step 4 documents the future completeness boundary in
[`docs/design/phase28_signal_input_bundle_completeness_boundary.md`](design/phase28_signal_input_bundle_completeness_boundary.md).
The future boundary may compare a snapshot's required input names and metadata
with a bundle's explicit values before evaluator use. Phase 28 Step 5 adds the
minimal pure validation function for that boundary:
`validate_signal_input_bundle_completeness(snapshot, bundle)` returns an
immutable `SignalInputBundleCompletenessResult` with snapshot id traceability,
bundle snapshot id traceability, `is_complete`, missing input names, and extra
input names.

The validation compares only `SignalEvaluationInputSnapshot.required_input_names`
with `SignalInputBundle.values[n].name`. Missing names are reported in snapshot
order, extra names are reported in bundle order, and extra names do not make the
result incomplete in this phase. It does not enforce snapshot id equality or
`as_of` equality yet, does not perform lookahead validation beyond the existing
bundle constructor rule, and does not inspect or interpret values.
`SignalInputBundle` remains a grouping contract only; completeness validation
remains a separate pure boundary. No real evaluator or signal computation
exists yet, evaluator output remains advisory and pre-risk, and LLMs remain
outside the trading hot path.

Phase 28 Step 6 hardens the existing completeness validation tests and docs
only. The hardening pins exact result field shape, frozen/slotted behavior,
tuple immutability, deterministic missing and extra name ordering, exact
snapshot id and bundle snapshot id traceability, input non-mutation, repeated
call determinism, environment/random independence, no hidden wall-clock access,
and no value, source id, observed timestamp, lookahead, signal, feature, score,
rank, direction, actionability, risk, execution, broker, runtime, persistence,
ML, or LLM behavior.

Phase 29 Step 1 defines the first real evaluator design gate in
[`docs/design/phase29_first_real_evaluator_design_gate.md`](design/phase29_first_real_evaluator_design_gate.md).
No real evaluator exists yet. The current input stack supports explicit
snapshots, observed values, bundles, and name-only completeness validation, but
it does not make any output actionable. Real signal computation remains
forbidden until a future evaluator-specific design satisfies the gate. Any
future evaluator output remains advisory and pre-risk, and LLMs remain outside
the trading hot path.

Phase 29 Step 2 selects the first real evaluator candidate in
[`docs/design/phase29_first_real_evaluator_candidate_selection.md`](design/phase29_first_real_evaluator_candidate_selection.md).
The selected candidate is a minimal threshold-style advisory evaluator over one
explicit scalar `SignalInputValue`. Candidate selection is documentation-only
and does not authorize implementation. No real evaluator exists yet, and real
signal computation remains forbidden until evaluator-specific design and tests
satisfy the gate. Evaluator output remains advisory and pre-risk, and LLMs
remain outside the trading hot path.

Phase 29 Step 3 designs that selected candidate contract in
[`docs/design/phase29_first_real_evaluator_candidate_contract.md`](design/phase29_first_real_evaluator_candidate_contract.md).
The contract design documents the placeholder input name `indicator_value`, the
preferred initial value type `Decimal`, possible `>=` threshold semantics,
advisory-only output expectations, completeness and timestamp questions, strict
no-lookahead rules, forbidden semantics, and required future tests. It remains
documentation-only. No real evaluator exists yet, and real signal computation
remains forbidden until implementation is explicitly scoped. Evaluator output
remains advisory and pre-risk, and LLMs remain outside the trading hot path.

Phase 29 Step 4 defines the first real evaluator implementation test matrix in
[`docs/design/phase29_first_real_evaluator_test_matrix.md`](design/phase29_first_real_evaluator_test_matrix.md).
It is documentation-only and does not add a real evaluator, signal computation,
production behavior, runtime behavior, or trading-path behavior. Real signal
computation remains forbidden until implementation is explicitly scoped.
Evaluator output remains advisory and pre-risk, and LLMs remain outside the
trading hot path.

Phase 29 Step 5 reviews implementation readiness in
[`docs/design/phase29_first_real_evaluator_implementation_readiness.md`](design/phase29_first_real_evaluator_implementation_readiness.md).
It is documentation-only and recommends one more docs-only constants/output
semantics design step before implementation. No real evaluator exists yet, and
real signal computation remains forbidden unless explicitly scoped in a later
implementation phase. Evaluator output remains advisory and pre-risk, and LLMs
remain outside the trading hot path.

Phase 29 Step 6 designs threshold evaluator constants/output semantics in
[`docs/design/phase29_threshold_evaluator_constants_output_semantics.md`](design/phase29_threshold_evaluator_constants_output_semantics.md).
It is documentation-only. It selects safe evaluator-local constants and textual
advisory output semantics, but exact validated signal and research artifacts
remain missing. No real evaluator exists yet, and real signal computation
remains forbidden unless explicitly scoped in a later implementation phase.
Evaluator output remains advisory and pre-risk, and LLMs remain outside the
trading hot path.

Phase 30 Step 1 defines the threshold evaluator research-support boundary in
[`docs/design/phase30_threshold_evaluator_research_support_boundary.md`](design/phase30_threshold_evaluator_research_support_boundary.md).
It is documentation-only. It records the validated research artifact,
validated signal definition, threshold value/source evidence, acceptance
criteria, non-actionability rule, and future test implications required before
a real threshold-style evaluator may be implemented. No real evaluator exists
yet, real signal computation remains forbidden, evaluator output remains
advisory and pre-risk, and LLMs remain outside the trading hot path.

Phase 30 Step 2 defines the research validation evidence standard in
[`docs/design/phase30_research_validation_evidence_standard.md`](design/phase30_research_validation_evidence_standard.md).
It is documentation-only and creates the fixed checklist future research
artifacts must be reviewed against before they can support a real evaluator.
No real evaluator exists yet, real signal computation remains forbidden,
evaluator output remains advisory and pre-risk, and LLMs remain outside the
trading hot path.

Phase 30 Step 3 defines the research artifact candidate review template in
[`docs/design/phase30_research_artifact_candidate_review_template.md`](design/phase30_research_artifact_candidate_review_template.md).
It is documentation-only and creates the intake shape for future artifact
reviews. No actual research artifact is approved, no real evaluator exists
yet, real signal computation remains forbidden, evaluator output remains
advisory and pre-risk, and LLMs remain outside the trading hot path.

Phase 30 Step 4 defines the research artifact candidate sourcing plan and
backlog boundary in
[`docs/design/phase30_research_artifact_candidate_sourcing_plan.md`](design/phase30_research_artifact_candidate_sourcing_plan.md).
It is documentation-only and defines how future candidates may be sourced and
triaged before review. No real evaluator exists yet, real signal computation
remains forbidden, evaluator output remains advisory and pre-risk, and LLMs
remain outside the trading hot path.

Phase 30 Step 5 populates the initial unreviewed research candidate backlog in
[`docs/design/phase30_research_artifact_candidate_backlog.md`](design/phase30_research_artifact_candidate_backlog.md).
It is documentation-only and records candidate placeholders and sourcing
targets only. No candidate artifact is reviewed or approved, no validated
research artifact or validated signal definition is created, no real evaluator
exists yet, real signal computation remains forbidden, evaluator output
remains advisory and pre-risk, and LLMs remain outside the trading hot path.

Phase 30 Step 6 selects the first research candidate sourcing target in
[`docs/design/phase30_first_research_candidate_source_selection.md`](design/phase30_first_research_candidate_source_selection.md).
It is documentation-only and selects `P30-BL-001` for future source
collection only. No source is reviewed or approved, no validated research
artifact or validated signal definition is created, no real evaluator exists
yet, real signal computation remains forbidden, evaluator output remains
advisory and pre-risk, and LLMs remain outside the trading hot path.

Phase 31 Step 1 adds the reusable operating context in
[`docs/agent_context/codex_operating_context.md`](agent_context/codex_operating_context.md).
It is documentation-only and resets research-track workflow granularity:
related docs, research, and planning updates may be combined when low-risk and
code-free, while production-code phases remain narrow, test-first, explicitly
scoped, and heavily verified. It does not validate a research artifact, create
a signal definition, implement a real evaluator, compute signals, or add any
trading-path behavior.

Phase 31 Step 2 adds the research-track next action plan in
[`docs/design/phase31_research_track_next_action_plan.md`](design/phase31_research_track_next_action_plan.md).
It is documentation-only and turns the Phase 30 backlog and source-selection
work into a practical sequence: source package collection, pre-review
normalization, first candidate review, signal-definition binding planning, and
an implementation-readiness gate. `P30-BL-001` remains unreviewed,
unvalidated, not approved, and not implementation-ready. Backlog entries,
source-selection decisions, and research-agent summaries are not evidence by
themselves. Perplexity, Claude, Gemini, and similar tools may assist with
source discovery, summaries, and critique, but they cannot define production
behavior or enter the trading path.

Phase 31 Step 3 adds the normalized `P30-BL-001` source package in
[`docs/design/phase31_p30_bl_001_source_package.md`](design/phase31_p30_bl_001_source_package.md).
It is documentation-only and makes `P30-BL-001` source-package-ready only. It
does not review, validate, approve, or implement any research artifact, signal
definition, threshold, comparator, evaluator behavior, signal computation,
feature computation, strategy logic, scoring, ranking, direction,
actionability, broker behavior, runtime behavior, persistence, ML, or LLM
trading-path behavior.

Phase 31 Step 4 adds the Tier A formal source review in
[`docs/design/phase31_p30_bl_001_tier_a_review.md`](design/phase31_p30_bl_001_tier_a_review.md).
It is documentation-only and conditionally passes Tier A for mechanics and
methodology only. It does not validate `P30-BL-001`, create or approve a
validated research artifact, create a validated signal definition, justify a
production threshold, authorize evaluator implementation, compute signals, add
features, change strategy logic, touch risk or execution, call brokers, add
runtime behavior, persist data, add ML, or put LLMs in the trading path.

Phase 31 Step 5 adds the evidence gap and routing plan in
[`docs/design/phase31_p30_bl_001_evidence_gap_routing_plan.md`](design/phase31_p30_bl_001_evidence_gap_routing_plan.md).
It is documentation-only and preserves `P30-BL-001` as unvalidated. The safest
next route is a formal mechanics-only candidate artifact review summary that
may support future evaluator mechanics but cannot support a production
threshold or evaluator implementation.

The deterministic core must not directly depend on notebooks, research scripts,
backtesting engines, exploratory data-mining tools, live data ingestion, ML
training workflows, or LLM clients. LLMs may assist with research narration,
experiment summaries, hypothesis generation, journaling, and explaining
completed evaluation reports, but must not compute live signal outputs,
generate live trade decisions, mutate execution plans, approve orders, bypass
risk checks, access live broker or quote state in the trading process,
interact with brokers, or enter the trading hot path. Broker behavior remains
isolated behind broker boundaries.

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
- Scoring, direction, confidence, or actionability semantics unless explicitly
  designed and scoped
- Research/backtesting outputs as direct trading logic
- Notebooks or exploratory scripts in the deterministic core
- Validated artifact metadata as signal generation
- Validated artifact metadata as risk approval
- Validated artifact persistence implementation
- Validated signal definitions as live signal outputs
- Validated signal definitions as execution decisions
- Validated signal definitions as broker orders
- Validated signal definitions as execution intents
- Validated signal definitions as risk approvals
- Signal evaluation input snapshots as signal computation
- Signal evaluation input snapshots as live data access
- Signal evaluation input snapshots as risk approvals
- Signal evaluation input snapshots as execution intents or execution plans
- Signal evaluation outputs as orders
- Signal evaluation outputs as risk approvals
- Signal evaluation outputs as execution intents or execution plans
- SignalEvaluationResult behavior beyond minimal advisory metadata
- Signal evaluator implementation beyond the minimal no-op metadata boundary
- Real signal evaluator implementation
- Evaluator protocol
- No-op marker on SignalEvaluationResult
- Signal evaluator registry
- Signal computation from validated signal definitions
- Signal input bundle completeness behavior beyond minimal metadata-only name
  validation
- Strict extra-input rejection for signal input bundle completeness validation
- Snapshot id or `as_of` compatibility enforcement for signal input bundle
  completeness validation
- Signal input bundle behavior beyond minimal grouping, tuple coercion,
  duplicate-name rejection, and lookahead validation
- Real evaluator consumption of SignalInputBundle
- First real evaluator implementation
- Evaluator behavior beyond the Phase 29 Step 6 constants/output semantics
  design
- Threshold evaluator behavior beyond the Phase 30 Step 1 research-support
  boundary
- Threshold evaluator behavior beyond the Phase 30 Step 2 research validation
  evidence standard
- Threshold evaluator behavior beyond the Phase 30 Step 3 research artifact
  review template
- Threshold evaluator behavior beyond the Phase 30 Step 4 research artifact
  sourcing plan
- Threshold evaluator behavior beyond the Phase 30 Step 5 unreviewed research
  candidate backlog
- Threshold evaluator behavior beyond the Phase 30 Step 6 first candidate
  source selection
- Threshold evaluator behavior beyond the Phase 31 Step 2 research-track next
  action plan
- Threshold evaluator behavior beyond the Phase 31 Step 3 source package
  normalization
- Threshold evaluator behavior beyond the Phase 31 Step 4 Tier A formal source
  review
- Threshold evaluator behavior beyond the Phase 31 Step 5 evidence gap and
  routing plan
- System clock implementation
- Feature computation
- Strategy engine
- Signal-evaluation-to-risk bridge
- Ranking or priority policy for signal evaluations
- Input snapshot persistence implementation
- Live data ingestion
- ML training implementation
- Persistence writes
- Audit logging writes
- Reconciliation loop against external broker state
- Scheduler or runtime loop
- LangGraph
- ML models
- LLM logic in the trading path
- Live trading

## Next Recommended Phase

Future Codex prompts should start from
[`docs/agent_context/codex_operating_context.md`](agent_context/codex_operating_context.md)
plus the relevant phase/design docs, especially
[`docs/design/phase31_research_track_next_action_plan.md`](design/phase31_research_track_next_action_plan.md)
for research-track work. Docs-only research and planning phases may combine
related updates when they are low-risk and code-free. Any production source
phase should stay narrow, test-first, explicitly scoped, and heavily verified.

Future threshold-evaluator work should continue by sourcing and reviewing exact
validated research and signal-definition support against the Phase 30 Step 2
evidence standard and Phase 30 Step 3 review template. The next practical
research action is the Phase 31 Step 5 recommendation: a formal mechanics-only
candidate artifact review summary for `P30-BL-001`. Tier B review or targeted
production-threshold evidence collection may follow later, but real evaluator
behavior, signal computation, test scaffolds for implementation, and wiring
signal output into risk remain blocked until those gates are explicitly
resolved.

Execution-boundary work should remain pure and synthetic unless explicitly
approved otherwise. It should still exclude broker wiring, order submission,
scheduler/runtime behavior, persistence, cash reservation side effects, ML, and
LLM trading-path logic.

Real Alpaca SDK work and Phase 7 reconciliation remain deferred unless
explicitly approved.

## Alpaca Paper Planning Link

See [Alpaca Paper Integration Plan](alpaca_paper_integration_plan.md) for the safe future path toward Alpaca paper integration. That plan is documentation-only and does not add SDK dependencies, credentials, network calls, or runtime broker behavior.
