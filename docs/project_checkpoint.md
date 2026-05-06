# Project Checkpoint

## Current Milestone

The project is at the 321-passed / 4-skipped deterministic core checkpoint. The
current system prioritizes a deterministic trading core before any real broker
connectivity.

Recent focused validation included broker/idempotency, LocalBroker rename/import,
cleanup/import suites, a shared broker-contract subset, and pre-SDK Alpaca
safety gates. Phase 1 now adds a file-scoped Alpaca SDK wrapper boundary without
real broker connectivity. A pre-Phase-2 hardening pass adds a paper URL
invariant, `paper_integration` gate tests, broader credential redaction
coverage, offline SDK factory-construction coverage, and one skipped-by-default
read-only Phase 2 paper account smoke test. Phase 3 adds one skipped-by-default
read-only account translation smoke test through the SDK wrapper, adapter,
translator, mapper, and internal `Account` path. Phase 4 adds one
skipped-by-default read-only positions translation smoke test through the same
adapter, translator, mapper, and internal `Position` path. Phase 5 documents
reconciliation-readiness policy before implementation. Phase 6 hardens
fake-only reconciliation through the Alpaca adapter path, unavailable broker
call handling, and conservative report-only tolerances. Phase 7 real-paper
reconciliation remains explicitly deferred. Phase 8 begins with a deterministic
offline screener foundation that ranks synthetic `Bar + Quote` inputs by ask
momentum versus previous close. Phase 9 adds optional deterministic screener
filters for `min_score` and `top_n` while preserving Phase 8 defaults. Phase 10
is a no-code design-only pass documenting the future Screener -> Signals bridge.
Phase 11 begins that bridge with a pure orchestration-owned adapter that
preserves screener ordering and returns signal-ready `Bar + Quote` pairs without
invoking signals yet. Phase 11 Step 2 hardens the bridge by rejecting duplicate
screener result symbols and malformed result/candidate inputs while preserving
the original `Bar` and `Quote` objects in immutable ordered pairs. Phase 11 Step
3 adds pure screener-ordered signal evaluation only; any signal output is not an
approved trade and is not submitted. Phase 12 is a no-code design-only pass
documenting the future Signal -> Risk boundary before any risk integration is
implemented. Phase 13 hardens the screener-ordered signal evaluation contract
with focused unit tests only. Phase 14 Step 1 adds test-only dependency
direction guardrails before any Signal -> Risk runtime code exists. Phase 14
Step 2 adds pure Signal -> Risk evaluation that stops at deterministic risk
verdicts. Phase 15 is a no-code design-only pass documenting the future Risk
-> Execution boundary before any execution integration is implemented. Phase 16
Step 1 adds test-only Risk -> Execution dependency guardrails before any
execution bridge exists. Phase 16 Step 2 adds a pure risk-approved row selector
that returns only `risk_approved` `SignalRiskEvaluation` rows while preserving
input order and object identity. Phase 17 Step 1 is a no-code design-only pass
documenting the future internal execution-intent boundary after risk-approved
selection. No runtime behavior changed, and risk-approved rows remain
permission signals only. Phase 17 Step 2 adds a minimal internal
`ExecutionIntent` contract and pure builder that wrap risk-approved source rows
by identity before any broker, execution adapter, scheduler, persistence, or
live trading behavior. Phase 17 Step 3 hardens execution-intent traceability
with tests and documentation only; `ExecutionIntent` remains source-only,
pre-submission, and not executable by itself.
The latest full-suite result is:

```text
321 passed, 4 skipped
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
risk checks, an offline ask-momentum screener with optional deterministic
filters, a pure orchestration-owned Screener -> Signal input bridge, local paper
execution, portfolio state transitions, quote-based valuation, local
reconciliation, and structured broker results.

The screener bridge prepares signal-ready inputs only. It does not invoke
signals yet if signals would create orders. It rejects duplicate screener
result symbols and malformed result/candidate inputs, preserves the original
`Bar` and `Quote` objects, and now supports pure screener-ordered signal
evaluation. Any signal output is not an approved trade and is not submitted.
The screener-ordered signal evaluation contract is now covered for mixed
signal/no-signal outputs, input non-mutation, immutable evaluation results, and
signal-rule exception propagation.
Dependency-direction guardrail tests now enforce the documented layering between
screener, signals, risk, orchestration, and execution.
The Signal -> Risk layer converts `ScreenerSignalEvaluation` rows into
`SignalRiskEvaluation` rows, retains no-signal rows with `risk=None`, and checks
proposed orders with `RiskEngine` only. Risk-approved means allowed by risk; it
does not mean executed, submitted, or broker-ready. This path does not call
brokers, Alpaca, execution, CLI, scheduler, ML, or LLM trading-path logic.
Phase 15 documents the future Risk -> Execution boundary and keeps
risk-approved rows as permission signals only, not execution instructions.
Phase 16 Step 1 strengthens dependency guardrails so pre-execution
orchestration modules cannot import execution, broker, Alpaca, or trade-flow
modules. Phase 16 Step 2 adds a pure risk-approved row selector that creates no
execution intents and calls no broker, execution, Alpaca, `submit_order`,
scheduler, persistence, ML, or LLM trading-path logic. Phase 17 Step 1
documents a future internal execution-intent boundary. Phase 17 Step 2 adds the
minimal internal `ExecutionIntent` wrapper and
`build_execution_intents_from_risk_approved(...)` builder. The intent remains
pre-submission and broker-agnostic, preserving the source
`SignalRiskEvaluation` by identity. No broker path, order submission,
client-order-id generation, idempotency, runtime behavior, persistence, ML, or
LLM trading-path logic was added. Phase 17 Step 3 keeps the implementation
unchanged and hardens the contract that proposed orders, risk verdicts, and
status remain reachable only through `intent.source_evaluation`.

`LocalBroker` is the deterministic reference broker and now lives in:

```text
src/algotrader/execution/local_broker.py
```

`AlpacaPaperBroker` is an inert-by-default future broker boundary. It follows
the canonical broker-facing shape but only has operational behavior in tests
when an explicit fake adapter is injected.

## Alpaca Boundary

The normal test/runtime Alpaca preparation path is still fake-only and offline.

Current guarantees:

- bounded `alpaca-py` dependency isolated to the SDK wrapper
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
broker/network/LLM imports and dynamic import/code-execution calls. The
deterministic trading path still has no LLM logic in risk, execution, signals,
screener, portfolio, valuation, reconciliation, or feature calculation.

Current safety behaviors:

- duplicate `order_id` handling is part of broker contract expectations
- `LocalBroker` rejects duplicate order IDs with `duplicate_order_id`
- duplicate `LocalBroker` submissions do not create a second fill or ledger
  mutation
- fake Alpaca adapter rejects duplicate `client_order_id` values before a second
  fake client call
- `require_paper_profile()` defines the future pre-SDK paper-profile gate
- `require_paper_profile()` rejects obvious non-paper Alpaca URLs
- `AlpacaSdkClient` is the only production file allowed to import `alpaca`
- normal pytest exercises the `paper_integration` skip gate without calling
  Alpaca
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

## Post-Review Hygiene Checkpoint

After the Claude Opus 183-test review, a low-risk hygiene patch consolidated
duplicate fake Alpaca test clients into `tests/fakes/alpaca.py`, removed stale
pre-pin adapter test helpers, labeled the broker contract tests by state model,
and added a focused reconciliation currency-mismatch test.

`AlpacaPaperBroker.get_positions()` now delegates directly to the injected fake
adapter's `list_positions()` method after the existing inert/no-adapter guard.
This matched the existing adapter shape and did not change trading behavior.

The full suite remains:

```text
python -m pytest
183 passed
```

No runtime trading behavior changed, and no SDK, credentials, environment
reads, network calls, websocket behavior, scheduler/runtime loop, real broker
connectivity, LangGraph, LangChain, OpenAI, Anthropic, ML, or LLM
trading-path logic was added.

## Shared Broker Contract Checkpoint

A test-only patch added `tests/contracts/test_broker_shared_contract.py` with
10 parametrized checks covering both `LocalBroker` and `AlpacaPaperBroker` with
an injected fake adapter. The shared subset covers missing and rejected risk
verdicts, approved submissions returning the exact internal
`BrokerOrderResult`, deterministic provided `order_id` use, and duplicate
`order_id` rejection without a second local fill or fake client submission.

Broker contract coverage is now clearer across three layers:

- portfolio-owning broker contract
- external-state-reflecting Alpaca fake protocol contract
- shared broker contract subset

The full suite is now:

```text
python -m pytest
193 passed
```

No production code changed, and no SDK, credentials, environment reads, network
calls, websocket behavior, scheduler/runtime loop, real broker connectivity,
LangGraph, LangChain, OpenAI, Anthropic, ML, or LLM trading-path logic was
added.

## Pre-SDK Safety Gate Checkpoint

A small safety-hardening patch added and tested `require_paper_profile()` as the
future gate SDK code must call before Alpaca-touching behavior. Import-safety
coverage now also blocks dynamic import and code-execution calls such as
`importlib.import_module(...)`, `__import__(...)`, `exec(...)`, and `eval(...)`.

The full suite is now:

```text
python -m pytest
198 passed
```

At that pre-SDK checkpoint, no SDK dependency, credentials, environment reads,
network calls, websocket behavior, scheduler/runtime loop, real broker
connectivity, LangGraph, LangChain, OpenAI, Anthropic, ML, or LLM trading-path
logic was added.

## Phase 1 SDK Wrapper Checkpoint

A tightly scoped Phase 1 patch declared `alpaca-py>=0.43,<0.44`, added the
file-scoped `AlpacaSdkClient` wrapper, and updated import safety so `alpaca`
imports are allowed only in that wrapper. Wrapper tests use fakes and prove
paper-profile gating, adapter compatibility, credential redaction, and
construction-time network isolation.

The full suite is now:

```text
python -m pytest
206 passed
```

No real account call, real or paper order submission, websocket behavior,
scheduler/runtime loop, real broker connectivity, LangGraph, LangChain, OpenAI,
Anthropic, ML, or LLM trading-path logic was added.

## Pre-Phase-2 Hardening Checkpoint

Before any real paper-account smoke test, small hardening patches added the
paper URL invariant, direct `paper_integration` gate tests, one skipped
paper-marker smoke test, broader SDK credential redaction coverage, a lazy SDK
import regression test, and an offline `_create_trading_client()` construction
test.

The full suite is now:

```text
python -m pytest
216 passed, 1 skipped
```

No production runtime broker behavior changed, and no real account call, real
or paper order submission, network call, websocket behavior, scheduler/runtime
loop, real broker connectivity, LangGraph, LangChain, OpenAI, Anthropic, ML, or
LLM trading-path logic was added.

## Phase 2 Account Smoke Checkpoint

Phase 2 added exactly one `paper_integration` test in
`tests/integration/test_alpaca_paper_account_smoke.py`. It is skipped by
default and, only when the explicit paper gate is enabled, constructs
`AlpacaSdkClient` from environment-backed `AlpacaPaperConfig` and calls
`get_account()` exactly once.

The full suite is now:

```text
python -m pytest
216 passed, 2 skipped
```

Normal pytest remains credential-free and offline. No orders, positions call,
websocket behavior, scheduler/runtime loop, runtime broker selection, real
broker connectivity in normal runtime, LangGraph, LangChain, OpenAI, Anthropic,
ML, or LLM trading-path logic was added.

## Phase 3 Account Translation Smoke Checkpoint

Phase 3 added exactly one `paper_integration` test in
`tests/integration/test_alpaca_paper_account_translation_smoke.py`. It is
skipped by default and, only when the explicit paper gate is enabled, validates
the real SDK account response shape through:

```text
SDK account response
  -> AlpacaSdkClient
  -> AlpacaClientAdapter
  -> alpaca_translator
  -> alpaca_mapper
  -> internal Account
```

The full suite is now:

```text
python -m pytest
216 passed, 3 skipped
```

Normal pytest remains credential-free, offline, and skipped by default for real
paper integration tests. This phase does not call positions, submit orders, add
websocket behavior, add a scheduler/runtime loop, add runtime broker selection,
enable real broker connectivity in normal runtime, or add LangGraph, LangChain,
OpenAI, Anthropic, ML, or LLM trading-path logic.

## Phase 4 Positions Translation Smoke Checkpoint

Phase 4 added exactly one `paper_integration` test in
`tests/integration/test_alpaca_paper_positions_translation_smoke.py`. It is
skipped by default and, only when the explicit paper gate is enabled, validates
the real SDK positions response shape through:

```text
SDK positions response
  -> AlpacaSdkClient
  -> AlpacaClientAdapter
  -> alpaca_translator
  -> alpaca_mapper
  -> internal Position
```

The full suite is now:

```text
python -m pytest
216 passed, 4 skipped
```

Normal pytest remains credential-free, offline, and skipped by default for real
paper integration tests. This phase does not submit orders, add runtime broker
wiring, add reconciliation logic, add websocket behavior, add a
scheduler/runtime loop, or add LangGraph, LangChain, OpenAI, Anthropic, ML, or
LLM trading-path logic.

## Phase 5 Reconciliation Readiness Checkpoint

Phase 5 is documentation-only. It updates
`docs/alpaca_paper_integration_plan.md` with a reconciliation-readiness plan
covering future inputs, local-ledger source-of-truth policy, mismatch handling,
broker call failures, explicit operator-triggered timing, and future
skipped-by-default read-only integration-test policy.

No production code, tests, order submission, runtime broker wiring,
reconciliation implementation, scheduler/runtime loop, websocket behavior,
auto-correction, real Alpaca ledger persistence, LangGraph, LangChain, OpenAI,
Anthropic, ML, or LLM trading-path logic was added.

## Phase 6 Fake-Only Reconciliation Checkpoint

Phase 6 added offline reconciliation hardening around the fake Alpaca broker
path:

```text
FakeAlpacaClient
  -> AlpacaClientAdapter
  -> AlpacaPaperBroker
  -> reconcile_portfolio(...)
```

Fake-only tests now cover matching state, cash mismatch plus unexpected
position, quantity mismatch, and missing position through that path.
`FakeAlpacaClient` can customize returned positions for deterministic mismatch
scenarios.

`ReconciliationReport` now includes:

- `available: bool = True`
- `broker_error: str = ""`

If `broker.get_account()` or `broker.get_positions()` fails, reconciliation now
returns an unavailable report with `available=False`, `ok=False`, no mismatches,
and a sanitized broker error. Both account-call and positions-call failures are
covered by fake-only tests.

Report-only tolerances now apply to cash, valuation, and unrealized P&L:

- `_CASH_MISMATCH_TOLERANCE = Decimal("0.01")`
- `_VALUATION_MISMATCH_TOLERANCE = Decimal("0.01")`
- `_UNREALIZED_PNL_MISMATCH_TOLERANCE = Decimal("0.01")`

`_within_tolerance(...)` uses `abs(expected - actual) <= tolerance`, so the
exact tolerance boundary is accepted. Quantity mismatches remain exact. Currency
divergence remains exact and is still reported as `cash_mismatch`.

The full suite is now:

```text
python -m pytest
229 passed, 4 skipped
```

No real Alpaca calls, order submission, runtime broker wiring, scheduler/runtime
loop, websocket behavior, ledger replay, ML, or LLM trading-path logic was
added.

## Phase 8 Deterministic Screener Foundation

Phase 8 begins with one small offline screener package:

```text
src/algotrader/screener/
```

The screener ranks synthetic `Bar + Quote` inputs by deterministic ask momentum
versus previous close:

```text
score = (quote.ask - previous_bar.close) / previous_bar.close
```

Results are immutable dataclasses returned as a tuple. Ranking is deterministic:
score descending, then symbol ascending as a tie-breaker. The screener reuses
the existing `Bar`, `Quote`, and `ValidationError` conventions instead of
adding duplicate market-data models.

This foundation is offline, credential-free, API-free, broker-free, and
deterministic. It does not generate orders and is not connected to signals,
risk, execution, Alpaca, or any scheduler/runtime loop.

The full suite is now:

```text
python -m pytest
240 passed, 4 skipped
```

## Phase 9 Deterministic Screener Filter Polish

Phase 9 adds optional deterministic filters to:

```text
rank_by_ask_momentum(...)
```

The screener can now keep only results with `score >= min_score` and can limit
the returned tuple with `top_n`. Defaults preserve Phase 8 behavior: no score
filter and no result limit.

Filtering remains local and deterministic. `min_score` accepts a `Decimal` or
decimal string. `top_n` must be an integer greater than or equal to 1. The
ordering remains score descending, then symbol ascending as a tie-breaker.

The Phase 9 filter contract is now pinned: `min_score` applies before `top_n`,
`min_score` is inclusive with `score >= min_score`, and default values preserve
Phase 8 behavior.

This phase still does not add live data, broker wiring, order generation, risk
integration, scheduler/runtime behavior, ML, or LLM trading-path logic.

The full suite is now:

```text
python -m pytest
256 passed, 4 skipped
```

## Phase 10 Screener to Signals Design

Phase 10 is documentation-only. It adds:

```text
docs/design/phase10_screener_to_signals.md
```

The design defines a future orchestration boundary between the deterministic
screener and deterministic signal generation. It does not implement the bridge
or add runtime behavior.

The planned dependency direction is:

```text
orchestration -> screener
orchestration -> signals
```

The design pins the rule that screener output may influence which symbols are
evaluated, their evaluation order, and whether a symbol is skipped due to
`top_n` or `min_score`. Screener output must not directly influence order side,
order type, quantity, limit price, broker selection, risk caps, position sizing,
idempotency keys, or whether `submit_order` is called.

No production code, live data, external API, Alpaca integration, broker wiring,
order creation, risk integration, scheduler/runtime behavior, ML, dependency, or
LLM trading-path logic was added.

## Phase 11 Screener to Signal Input Bridge

Phase 11 begins the Screener -> Signal path with one pure orchestration-owned
adapter:

```text
src/algotrader/orchestration/screener_signal_flow.py
```

`ordered_signal_inputs_from_screener(...)` accepts ranked
`AskMomentumResult` values plus the original `AskMomentumCandidate` values or a
candidate lookup, matches by symbol, rejects missing or duplicate candidate
symbols with `ValidationError`, and returns an immutable tuple of signal-ready
`(Bar, Quote)` pairs in the exact screener-result order.

Phase 11 Step 2 hardens the bridge further. It now rejects duplicate screener
result symbols so a future signal path cannot silently evaluate the same symbol
twice. It also rejects malformed result/candidate inputs and preserves the
original `Bar` and `Quote` objects while returning immutable ordered pairs.

Phase 11 Step 3 adds pure screener-ordered signal evaluation through
`evaluate_signals_from_screener(...)`. It applies the existing deterministic
signal rule to the ordered `(Bar, Quote)` inputs and returns immutable
`ScreenerSignalEvaluation` values in exact screener order. A returned
`ProposedOrder` is a proposed signal output only: it is not an approved trade
and is not submitted.

This phase still does not call risk, call brokers, touch Alpaca, connect to
execution, CLI, scheduler, or runtime behavior, or add ML or LLM trading-path
logic. No dependencies were added.

The full suite is now:

```text
python -m pytest
269 passed, 4 skipped
```

## Phase 12 Signal to Risk Design

Phase 12 is documentation-only. It adds:

```text
docs/design/phase12_signal_to_risk.md
```

The design defines the future orchestration boundary between
`ScreenerSignalEvaluation` outputs and deterministic risk evaluation. It pins
that any `ProposedOrder` from `evaluate_signals_from_screener(...)` remains
proposed signal output only until it passes through a separately named,
deterministic risk-evaluation function in a later phase.

The planned dependency direction is:

```text
orchestration -> screener
orchestration -> signals
orchestration -> risk
```

The design explicitly prohibits passing `ScreenerSignalEvaluation.order`
directly into `LocalBroker.submit_order(...)`,
`AlpacaPaperBroker.submit_order(...)`, `evaluate_and_execute(...)`,
`generate_evaluate_and_execute(...)`, or any broker or execution layer.

No runtime behavior, production Python code, tests, Alpaca changes, broker
wiring, order submission, execution integration, scheduler/runtime behavior,
ML, dependency, or LLM trading-path logic was added.

## Phase 13 Screener-Ordered Signal Evaluation Contract Hardening

Phase 13 is test-focused. It hardens the existing
`evaluate_signals_from_screener(...)` contract with additional unit coverage in:

```text
tests/unit/test_screener_signal_flow.py
```

The new tests pin these behaviors:

- mixed signal/no-signal results preserve exact screener order
- no-signal candidates remain represented with `order=None`
- input candidates and screener results are not mutated
- original `Bar` and `Quote` object identities are preserved
- `ScreenerSignalEvaluation` is frozen/immutable
- `signal_rule` exceptions propagate instead of being hidden as `order=None`

No production Python code changed. No risk integration, broker wiring, Alpaca
changes, order submission, execution integration, scheduler/runtime behavior,
ML, dependency, or LLM trading-path logic was added.

The full suite is now:

```text
python -m pytest
273 passed, 4 skipped
```

## Phase 14 Step 1 Dependency Direction Guardrails

Phase 14 Step 1 is test-only. It adds AST-based dependency-direction guardrails
in:

```text
tests/unit/test_dependency_direction.py
```

The tests enforce the documented layering between screener, signals, risk,
orchestration, and execution. Screener modules must not import signals, risk,
execution, portfolio, or orchestration. Signal modules must not import screener,
risk, execution, portfolio, or orchestration. Risk modules must not import
screener, signals, orchestration, or execution, while the existing risk ->
portfolio relationship remains allowed. The screener-signal orchestration bridge
must not import execution, broker, Alpaca, or trade-flow modules.

No production Python code changed. No Signal -> Risk runtime behavior, broker
wiring, Alpaca changes, execution integration, order submission,
scheduler/runtime behavior, ML, dependency, or LLM trading-path logic was
added.

The full suite is now:

```text
python -m pytest
277 passed, 4 skipped
```

## Phase 14 Step 2 Signal to Risk Evaluation

Phase 14 Step 2 adds a pure orchestration-owned Signal -> Risk evaluation layer
in:

```text
src/algotrader/orchestration/signal_risk_flow.py
```

`evaluate_risk_for_screener_signals(...)` converts
`ScreenerSignalEvaluation` rows into immutable `SignalRiskEvaluation` rows. It
preserves input order, emits one output row per input row, retains no-signal
rows with `status="no_signal"` and `risk=None`, and checks proposed orders with
`RiskEngine` only.

`SignalRiskEvaluation.status` distinguishes:

- `no_signal`
- `risk_rejected`
- `risk_approved`

Risk-approved means only that the deterministic risk verdict allowed the
proposed order. It does not mean executed, submitted, broker-ready, filled, or
persisted.

This phase also updates dependency-direction guardrails so
`algotrader.orchestration.signal_risk_flow` cannot import execution,
trade-flow, broker, or Alpaca modules.

No broker wiring, Alpaca changes, execution integration, order submission,
`submit_order`, CLI changes, scheduler/runtime behavior, persistence, ML,
dependency, or LLM trading-path logic was added.

The full suite is now:

```text
python -m pytest
288 passed, 4 skipped
```

## Phase 15 Risk to Execution Boundary Design

Phase 15 is documentation-only. It adds:

```text
docs/design/phase15_risk_to_execution.md
```

The design defines the future boundary between deterministic risk-approved
`SignalRiskEvaluation` rows and any later execution bridge. It pins that
`risk_approved` means allowed by deterministic risk policy only. It is a
permission signal, not an execution instruction, and does not mean submitted,
executed, broker-routed, filled, or persisted.

The design states that a future execution bridge must live in orchestration or
execution-facing orchestration, may consume only `risk_approved` rows, must
preserve deterministic order, must skip `no_signal` and `risk_rejected` rows for
execution eligibility without deleting them from traceability, and must not
mutate portfolio directly or assume broker success.

No runtime behavior, production Python code, tests, exports, dependencies,
execution integration, broker wiring, Alpaca changes, order submission,
scheduler/runtime behavior, persistence, ML, or LLM trading-path logic was
added.

## Phase 16 Step 1 Risk to Execution Dependency Guardrails

Phase 16 Step 1 is test-only. It strengthens AST-based dependency-direction
guardrails in:

```text
tests/unit/test_dependency_direction.py
```

The tests enforce that pre-execution orchestration modules, including
`algotrader.orchestration.screener_signal_flow` and
`algotrader.orchestration.signal_risk_flow`, do not import execution, broker,
Alpaca, or trade-flow modules. The guardrail table also now includes
`algotrader.orchestration.risk_execution_flow` as an active pre-execution
module.

No production Python code changed. No Risk -> Execution runtime behavior,
execution bridge module, broker wiring, Alpaca changes, execution integration,
order submission, scheduler/runtime behavior, persistence, ML, dependency, or
LLM trading-path logic was added.

The full suite is now:

```text
python -m pytest
289 passed, 4 skipped
```

## Phase 16 Step 2 Risk-Approved Row Selection

Phase 16 Step 2 adds the first pure Risk -> Execution boundary helper in:

```text
src/algotrader/orchestration/risk_execution_flow.py
```

`select_risk_approved_evaluations(...)` accepts existing
`SignalRiskEvaluation` rows and returns only rows with
`status="risk_approved"`. It preserves deterministic input order, returns the
same row objects rather than copies, and returns an immutable tuple. `no_signal`
and `risk_rejected` rows are skipped.

This selector does not create execution intents, derive client order IDs or
idempotency keys, call brokers, import execution, touch Alpaca, call
`submit_order`, use schedulers, persist anything, mutate portfolios, or add ML
or LLM trading-path logic. `risk_approved` remains a permission signal only,
not an execution instruction.

Known limitation: multiple rows may be individually risk-approved against the
same fixed portfolio snapshot but not collectively affordable. This step does
not solve batch-level cumulative cash handling or same-symbol conflict
resolution; those remain future execution-boundary concerns before any
execution intent or submission behavior is added.

The full suite is now:

```text
python -m pytest
303 passed, 4 skipped
```

## Phase 17 Step 1 Execution-Intent Boundary Design

Phase 17 Step 1 started and completed as a documentation-only design phase. It
adds
`docs/design/phase17_execution_intent_boundary.md` to define the future
internal execution-intent boundary after
`select_risk_approved_evaluations(...)` and before any broker adapter,
execution layer, scheduler/runtime behavior, persistence, or live trading
path.

The design clarifies that selected risk-approved rows are permission signals
only. They are eligible for future execution-boundary consideration, but they
are not execution intents, submitted orders, broker-routed orders, fills,
persisted broker events, scheduler actions, runtime actions, or live trading
decisions. A future execution intent would be a deterministic, immutable,
auditable, broker-agnostic internal instruction candidate produced before any
broker adapter, if explicitly implemented later.

This step does not add an `ExecutionIntent` dataclass, a
`build_execution_intents_from_risk_approved(...)` function, order submission,
broker routing, Alpaca changes, `submit_order`, client-order-id generation,
idempotency implementation, scheduler/runtime behavior, persistence, portfolio
mutation, fills, reconciliation changes, live trading, ML, or LLM trading-path
logic.

The full-suite checkpoint remains:

```text
python -m pytest
303 passed, 4 skipped
```

## Phase 17 Step 2 Internal Execution-Intent Contract

Phase 17 Step 2 adds the smallest internal execution-intent contract in:

```text
src/algotrader/orchestration/risk_execution_flow.py
```

`ExecutionIntent` is an immutable, slotted dataclass with one field:
`source_evaluation: SignalRiskEvaluation`. It preserves traceability by
identity without adding screener rank, original index, broker IDs,
client-order IDs, idempotency keys, venue/account fields, fill fields,
persistence metadata, SDK-native objects, Alpaca-specific fields, or LLM-derived
fields.

`build_execution_intents_from_risk_approved(...)` accepts existing
`SignalRiskEvaluation` rows, reuses risk-approved row selection, and returns an
immutable tuple of `ExecutionIntent` objects for `risk_approved` rows only. It
skips `no_signal` and `risk_rejected` rows, preserves approved-row order,
preserves the exact original `SignalRiskEvaluation` object on each intent, and
does not mutate inputs.

This phase does not add broker routing, paper or live order submission,
Alpaca changes, `submit_order`, client-order-id generation, idempotency
implementation, batch cash reservation, same-symbol conflict resolution,
portfolio mutation, fills, scheduler/runtime behavior, persistence writes, ML,
or LLM trading-path logic.

The full suite is now:

```text
python -m pytest
318 passed, 4 skipped
```

## Phase 17 Step 3 ExecutionIntent Traceability Hardening

Phase 17 Step 3 is tests and documentation only. It hardens the
`ExecutionIntent` contract without changing production Python code.

`ExecutionIntent` remains an immutable, slotted, pre-submission internal object
with exactly one dataclass field: `source_evaluation`. Traceability flows
through that source `SignalRiskEvaluation` by identity. The proposed order,
risk verdict, and status remain reachable through
`intent.source_evaluation.order`, `intent.source_evaluation.risk`, and
`intent.source_evaluation.status`; no convenience fields or properties such as
`intent.order`, `intent.risk`, `intent.symbol`, or `intent.status` were added.

Additional tests pin that no broker IDs, broker names, account IDs,
client-order IDs, idempotency keys, venue fields, submission timestamps, fill
fields, Alpaca-specific fields, SDK/native objects, or persistence metadata are
exposed on `ExecutionIntent`.

The builder remains a pure approved-row intent builder. It still skips
`no_signal` and `risk_rejected` rows, preserves approved-row order, preserves
same-symbol approved rows without conflict resolution, performs no batch-level
cash reservation or collective affordability check, mutates no inputs, and
requires no portfolio, risk engine, broker, execution object, scheduler, or
persistence handle.

No broker routing, paper or live order submission, Alpaca changes,
`submit_order`, scheduler/runtime behavior, persistence writes, idempotency,
client-order-id generation, batch cash reservation, same-symbol conflict
resolution, portfolio mutation, fills, ML, or LLM trading-path logic was added.

The full suite is now:

```text
python -m pytest
321 passed, 4 skipped
```

## Explicitly Not Included

- `alpaca-trade-api` or unrelated SDK dependencies
- credentials
- environment-dependent normal tests
- network calls
- real broker connectivity
- websocket behavior
- scheduler/runtime loop
- live trading
- screener-driven order generation
- execution-intent broker routing or adapter integration
- batch-level cumulative cash enforcement
- same-symbol execution conflict handling
- LangGraph
- ML
- LLM trading-path logic

## Next Recommended Steps

Keep avoiding real Alpaca SDK work until explicitly approved.

Safe next tasks include:

- small deterministic screener polish with synthetic inputs only
- a small config cleanup audit
- documentation polish
- future design for batch-level cash and same-symbol handling before execution
- deeper broker contract tests around error paths and reconciliation boundaries
- further fake-only Alpaca contract coverage

Any future real SDK integration must be behind explicit opt-in safety gates,
paper-profile checks, credential redaction, skipped-by-default integration tests,
and no-network defaults for normal test runs.
