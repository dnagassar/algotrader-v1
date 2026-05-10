# Project Checkpoint

## Current Milestone

The project is at the 681-passed / 4-skipped deterministic core checkpoint. The
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
pre-submission, and not executable by itself. Phase 18 Step 1 is a no-code
execution-planning boundary design phase after `ExecutionIntent` construction.
Execution planning is conceptual only and no runtime behavior changed. Phase 18
Step 2 adds a minimal immutable `ExecutionPlan` batch container and pure
builder while leaving all execution-planning policy unresolved. Phase 18 Step 3
hardens `ExecutionPlan` traceability with tests and documentation only. Phase 19
Step 1 is a no-code execution-planning policy design phase. It designs the
future policy layer conceptually while leaving `ExecutionIntent` source-only,
`ExecutionPlan` as a minimal immutable batch container, and runtime behavior
unchanged. Phase 19 Step 2 adds the minimal immutable
`PlanningPolicyResult` / `SkippedExecutionIntent` boundary and a no-op
pass-through policy. Phase 19 Step 3 hardens planning-policy-result
traceability with tests and documentation only. Phase 20 Step 1 is a no-code
design phase for a future maximum accepted intents per plan policy. Runtime
behavior is unchanged: `PlanningPolicyResult` remains a pre-broker result
container, `apply_noop_execution_planning_policy(...)` remains pass-through
only, and the max-intents policy is designed conceptually but not implemented.
Phase 20 Step 2 adds the first real planning policy:
`MaxAcceptedIntentsPolicyConfig`,
`MAX_INTENTS_PER_PLAN_EXCEEDED_REASON`, and
`apply_max_intents_execution_planning_policy(...)`. The policy requires an
explicit positive integer cap, rejects `bool` and `None`, accepts the first `N`
intents, skips the rest with deterministic reason text, and preserves intent
and source-evaluation identity.
Phase 20 Step 3 hardens max-intents traceability with tests and documentation
only. It adds no production source changes and confirms accepted/skipped
identity, ordering, deterministic skip reasons, source-evaluation reachability,
input plan non-mutation, and absence of forbidden policy leakage fields.
Phase 21 Step 1 is a documentation-only research/validation boundary design.
It records how future historical research, validation, backtesting, features,
approved research signals, and LLM-assisted research narration may eventually
feed the deterministic core only through explicit validated contracts. No
production behavior changed. Phase 21 Step 2 adds the minimal immutable,
slotted validated research artifact metadata contract. The contract is evidence
only; it does not create signals, approve trades, mutate execution plans, or
touch brokers, runtime, persistence, live data, ML, or LLM trading-path logic.
Phase 21 Step 3 hardens validated research artifact traceability with tests
and documentation only; no production source changed.
Phase 22 Step 1 is a documentation-only validated signal definition boundary
design. It defines how validated research artifact metadata may eventually
support an approved deterministic signal definition without adding signal
computation, strategy behavior, broker behavior, execution-plan mutation,
runtime wiring, persistence, ML, or LLM trading-path logic.
Phase 22 Step 2 adds the minimal immutable, slotted validated signal definition
metadata contract. It does not evaluate signals, create execution intents,
approve trades, mutate execution plans, or touch broker, Alpaca,
scheduler/runtime, persistence, live data, ML, or LLM trading-path logic.
Phase 22 Step 3 hardens validated signal definition traceability with tests and
documentation only; no production source changed.
Phase 23 Step 1 is a documentation-only signal evaluation, clock, and as-of
boundary design. It defines how a future deterministic evaluator may consume
validated signal definition metadata plus explicit input snapshots while
preventing lookahead bias and keeping evaluations advisory, reproducible,
clock-explicit, broker-free, risk-approval-free, execution-free, and LLM-free
in the trading hot path.
Phase 23 Step 2 adds a minimal deterministic time contract:
`require_utc_datetime(...)`, `Clock`, `FixedClock`, and
`assert_not_after_as_of(...)`. It validates explicit UTC-aware datetimes,
provides an injectable fixed clock for deterministic tests, and adds a tiny
lookahead-prevention helper without evaluating signals, reading system time,
fetching live data, approving trades, mutating execution plans, touching
brokers, or adding scheduler/runtime behavior.
Phase 23 Step 3 hardens clock/timestamp traceability with tests and
documentation only. It changes no production source and pins UTC-aware
timestamp identity, repeated fixed-clock identity, immutability, naive and
non-UTC rejection, lookahead prevention, dependency independence, absence of
trading-path fields, and absence of hidden nondeterministic API calls.
Phase 24 Step 1 is a documentation-only `SignalEvaluationResult` boundary
design. It defines future advisory deterministic signal-evaluation output while
keeping signal evaluation separate from risk approval, execution intent
creation, execution planning, broker requests, portfolio mutation, ranking or
priority decisions, and LLM trading-path logic.
Phase 24 Step 2 adds the minimal immutable `SignalEvaluationResult` advisory
metadata contract. It validates explicit UTC-aware `as_of` and `evaluated_at`
timestamps, preserves deterministic trace fields and ordered tuple metadata,
and still does not evaluate signals, create execution intents, approve trades,
mutate execution plans, touch brokers, or add runtime behavior.
Phase 24 Step 3 hardens `SignalEvaluationResult` traceability with tests and
documentation only. It changes no production source and pins datetime identity,
tuple ordering and immutability, exact trace string preservation, advisory-only
surface area, forbidden trading-path field absence, and dependency isolation.
Phase 25 Step 1 is documentation-only. It records the future deterministic
signal evaluator boundary and states that no evaluator exists yet, signal
evaluation remains advisory and pre-risk, no production source or runtime
behavior changed, and LLMs remain outside the trading hot path.
Phase 25 Step 2 adds only a minimal immutable signal-evaluation input
snapshot/reference contract. It provides deterministic input traceability for a
future evaluator and still adds no evaluator, signal computation, live data
access, risk approval, execution behavior, broker behavior, runtime behavior,
persistence, ML, or LLM trading-path logic.
Phase 25 Step 3 hardens `SignalEvaluationInputSnapshot` traceability with
tests and documentation only. It changes no production source and adds no
production behavior. The snapshot remains metadata/reference-only and exists
only to provide deterministic input traceability for a future evaluator.
Phase 26 Step 1 is documentation-only. It records the future no-op signal
evaluator boundary and states that no evaluator implementation exists yet,
evaluator output remains advisory and pre-risk, no production source or runtime
behavior changed, no runtime or trading-path behavior was added, and LLMs
remain outside the trading hot path.
Phase 26 Step 2 reviews `SignalEvaluationResult` no-op readiness and concludes
the existing metadata-only result contract is sufficient for a future minimal
no-op evaluator. It adds no production source changes, no result contract
changes, no no-op marker, no evaluator implementation, no runtime behavior, and
no trading-path behavior. Focused tests now pin that no score, direction,
confidence, actionability, result-kind, evaluator-kind, risk, execution,
broker, runtime, persistence, ML, or LLM fields are present.
Phase 26 Step 3 adds the minimal frozen, slotted `NoOpSignalEvaluator`
contract as the first evaluator-shaped code. It only constructs advisory
`SignalEvaluationResult` metadata from explicit deterministic inputs and adds
no real signal computation, feature computation, scoring, ranking, direction,
actionability, risk approval, execution behavior, broker behavior, runtime
behavior, persistence, live data access, ML, or LLM trading-path logic.
Phase 26 Step 4 hardens `NoOpSignalEvaluator` traceability with tests and
documentation only. It adds no production behavior. The evaluator remains
deterministic and advisory-only, proves the evaluator input/output boundary
without real signal computation, and preserves traceability without
actionability.
Phase 27 Step 1 is documentation-only. It records admission criteria for any
future real deterministic signal evaluator and states that no real evaluator or
signal computation may be added until an explicit deterministic input-value
contract, timestamp/lookahead rules, advisory output semantics, and
side-effect/dependency guardrails are documented and implemented.
Phase 27 Step 2 is documentation-only. It records the future deterministic
signal input-value boundary and states that no input-value contract exists yet,
`SignalEvaluationInputSnapshot` remains reference metadata only, and no real
evaluator or signal computation was added.
Phase 27 Step 3 adds the minimal immutable `SignalInputValue` contract. It
carries one explicit observed value with UTC-aware timestamp and source
traceability only, and adds no real evaluator, signal computation, feature
computation, scoring, ranking, direction, actionability, risk approval,
execution behavior, broker behavior, runtime behavior, persistence, ML, or LLM
trading-path logic.
Phase 27 Step 4 hardens `SignalInputValue` traceability with tests and
documentation only. It adds no production behavior. The contract remains
immutable, scalar-only, non-computational, and isolated from trading-path
behavior.
The latest full-suite result is:

```text
681 passed, 4 skipped
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
status remain reachable only through `intent.source_evaluation`. Phase 18 Step
1 documents a future execution-planning boundary as a deterministic
batch-level, pre-broker concept. Phase 18 Step 2 adds the minimal
`ExecutionPlan` container and `build_execution_plan(...)` builder. The plan
preserves `ExecutionIntent` order and identity only; no broker routing,
idempotency, persistence, order submission, or runtime behavior has been
implemented. Phase 18 Step 3 keeps the implementation unchanged and hardens
that plan traceability flows through `plan.intents[n].source_evaluation`.
Phase 19 Step 1 documents the future execution-planning policy boundary after
minimal plan construction and before broker-facing request construction. That
policy is conceptual only: no policy object, accepted/skipped buckets, cash
reservation, same-symbol handling, priority/ranking, idempotency, persistence,
broker routing, order submission, runtime behavior, ML, or LLM trading-path
logic has been implemented. Phase 19 Step 2 adds the minimal deterministic
policy-result boundary and a no-op pass-through policy. All intents are
currently accepted, skipped intents are only a future traceability shape, and
no real planning policy decisions have been added. Phase 19 Step 3 keeps the
implementation unchanged and hardens the contract that accepted and skipped
traceability flows through `ExecutionIntent.source_evaluation`, not through
direct convenience fields on the policy result. Phase 20 Step 1 documents the
future maximum accepted intents per plan policy as the first real
execution-planning policy concept. It is documentation-only: `ExecutionPlan`
remains a container, the no-op policy still accepts every intent, and no
runtime behavior, broker-facing request construction, cash reservation,
idempotency, same-symbol handling, priority/ranking, persistence, order
submission, ML, or LLM trading-path logic has been added. Phase 20 Step 2 adds
the pure max-intents policy implementation while keeping no-op pass-through
separate for no-cap behavior. The max-intents policy performs only deterministic
plan-order capping; it adds no broker routing, order submission, cash or
buying-power reservation, same-symbol conflict handling, deduplication,
priority/ranking, idempotency, persistence, scheduler/runtime behavior, ML, or
LLM trading-path logic. Phase 20 Step 3 keeps production source unchanged and
hardens the max-intents traceability contract with tests and documentation
only. Phase 21 Step 1 documents the future Research -> Validation ->
Deterministic Core boundary. Research, backtesting, and LLM-assisted summaries
remain advisory until promoted through reviewed artifacts, explicit
deterministic contracts, and test-first implementation. Phase 21 Step 2 adds
the first tiny validated research artifact contract as metadata/evidence only;
it remains upstream and advisory and has no execution, broker, risk approval,
signal generation, persistence, live-data, ML, or LLM trading-path behavior.
Phase 21 Step 3 keeps that implementation unchanged and hardens traceability
and ordering guarantees with tests and documentation only. Phase 22 Step 1
documents the future validated signal definition boundary; validated signal
definitions are future promoted contracts, not execution decisions. Phase 22
Step 2 adds the minimal `ValidatedSignalDefinition` metadata contract while
keeping signal evaluation, risk approval, execution intent creation, broker
behavior, persistence, runtime behavior, ML, and LLM trading-path logic out.
Phase 22 Step 3 keeps production source unchanged and hardens source-artifact
traceability, deterministic tuple ordering, metadata-only boundaries, and
independence from execution, risk, broker, runtime, scheduler, persistence,
ML, and LLM trading-path modules.
Phase 23 Step 1 documents the future signal evaluation, clock, and as-of
boundary. Validated signal definitions remain metadata-only, and future signal
evaluations remain advisory reports rather than execution decisions. The
deterministic core may consume only explicit promoted contracts, explicit input
snapshots, and explicit timezone-aware timestamps. Broker behavior remains
isolated, and LLMs remain out of the hot path.
Phase 23 Step 2 adds only deterministic time primitives in the core layer.
`FixedClock` is injectable and deterministic; no system clock, live data, risk,
execution, broker, scheduler/runtime, persistence, ML, or LLM behavior was
introduced.
Phase 23 Step 3 keeps those primitives unchanged and hardens their
traceability with tests/docs only. UTC-aware timestamp enforcement and
`observed_at <= as_of` lookahead-prevention behavior are now pinned more
explicitly.
Phase 24 Step 1 documents the future `SignalEvaluationResult` boundary after
validated signal definitions and explicit clock/as-of rules. The future result
is advisory deterministic output only: it may carry signal ids, source
artifact references, input snapshot fingerprints, explicit UTC-aware `as_of`
and `evaluated_at` timestamps, deterministic output values, reason codes,
diagnostics, assumptions, and limitations. It must not carry orders, broker
requests, risk approvals, execution intents, execution plans, portfolio
mutation, ranking or priority decisions, Alpaca behavior, or LLM-generated
trade decisions.
Phase 24 Step 2 implements that minimal advisory result contract in
`src/algotrader/signals/signal_evaluation_result.py`. The object stores only
evaluation id, signal id/version, source artifact id/version, explicit
UTC-aware `as_of` and `evaluated_at`, input fingerprint, output value, reason
code, diagnostics, assumptions, and limitations. It is frozen, slotted, and
metadata-only.
Phase 24 Step 3 keeps that implementation unchanged and hardens the tests and
docs around traceability. `SignalEvaluationResult` remains advisory metadata
only and does not evaluate signals, compute features, implement strategies,
create execution intents, approve risk, mutate execution plans, route to
brokers, interact with Alpaca, submit orders, touch scheduler/runtime or
persistence, train or run ML, or put LLMs in the trading path.
Phase 25 Step 1 documents the future signal evaluator boundary only. No
evaluator implementation, signal computation, production behavior, runtime
behavior, broker behavior, ML behavior, or LLM trading-path behavior was added.
Phase 25 Step 2 adds only `SignalEvaluationInputSnapshot` as deterministic
input snapshot/reference metadata for a future evaluator. It does not compute
signals or features, access live data, approve risk, create execution intents,
mutate execution plans, route to brokers, interact with Alpaca, use
scheduler/runtime or persistence behavior, train or run ML, or put LLMs in the
trading path.
Phase 25 Step 3 keeps that contract unchanged and hardens traceability with
tests/docs only. The snapshot remains metadata/reference-only, not a signal
evaluator, not signal computation, not feature computation, not risk approval,
not execution behavior, not broker or Alpaca behavior, not runtime/persistence
behavior, and not ML or LLM trading-path behavior.
Phase 26 Step 1 documents the future no-op signal evaluator boundary only. No
no-op evaluator implementation, evaluator protocol, result contract change,
no-op marker, signal computation, production behavior, runtime behavior,
trading-path behavior, broker behavior, ML behavior, or LLM trading-path
behavior was added. Future evaluator modules must not import broker, Alpaca,
execution, risk, runtime/scheduler, persistence, ML, or LLM modules.
Phase 26 Step 2 concludes that the existing `SignalEvaluationResult` fields are
sufficient for a future minimal no-op evaluator. A future no-op result can
preserve traceability through signal definition identity/version, source
artifact identity/version, input fingerprint, explicit UTC-aware `as_of`,
explicit UTC-aware `evaluated_at`, `output_value`, `reason_code`,
`diagnostics`, `assumptions`, and `limitations` without adding score,
direction, confidence, actionability, `should_trade`, no-op marker,
`result_kind`, or `evaluator_kind` fields.
Phase 26 Step 3 adds `NoOpSignalEvaluator` in the signal layer. It proves the
explicit deterministic input/output boundary only. It accepts a
`ValidatedSignalDefinition`, a `SignalEvaluationInputSnapshot`, explicit
UTC-aware `as_of`, and explicit UTC-aware `evaluated_at`, then returns advisory
`SignalEvaluationResult` metadata. It does not compute signals, inspect source
payloads, access live data, score, rank, infer direction, recommend trades,
approve risk, create execution intents, mutate execution plans, route to
brokers, submit orders, use scheduler/runtime/persistence behavior, run ML, or
call LLMs.
Phase 26 Step 4 hardens that boundary with tests/docs only. It adds no
production source or behavior. The no-op evaluator remains deterministic,
offline-safe, credential-free, advisory-only, broker-isolated, and traceable
without implying a signal fired, a recommendation exists, risk was approved, or
execution readiness exists.
Phase 27 Step 1 adds the real evaluator admission boundary as documentation
only. No production code, tests, runtime behavior, real evaluator, or signal
computation was added. Real evaluator work remains blocked until deterministic
input values, observation timestamps, no-lookahead proofs, advisory output
meaning, side-effect tests, and trading-path dependency tests are explicit.
Phase 27 Step 2 adds the deterministic signal input-value boundary as
documentation only. No production code, tests, runtime behavior, input-value
contract, real evaluator, or signal computation was added.
Phase 27 Step 3 adds `SignalInputValue` as a minimal signal-layer contract for
one explicit observed value. It validates only its own metadata and timestamp;
lookahead validation against evaluator `as_of` remains future work.
Phase 27 Step 4 hardens that contract with tests/docs only. No production code
or runtime behavior changed.

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

At the Phase 20 Step 1 checkpoint, the full suite remained:

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

## Phase 18 Step 1 Execution-Planning Boundary Design

Phase 18 Step 1 started and completed as a documentation-only design phase. It
adds:

```text
docs/design/phase18_execution_planning_boundary.md
```

The design defines the future execution-planning boundary after
`build_execution_intents_from_risk_approved(...)` and before any broker adapter,
broker-facing request construction, order submission, persistence write,
scheduler/runtime behavior, or live trading behavior.

`ExecutionIntent` remains source-only and pre-submission. It still has exactly
one dataclass field, `source_evaluation`, and proposed orders, risk verdicts,
and status remain reachable only through that source evaluation. A future
`ExecutionPlan` is described only conceptually as a deterministic batch-level
artifact that may later consume `ExecutionIntent` objects and produce a
pre-broker decision set.

This phase documents unresolved batch-level concerns for later work, including
collective affordability, cash or buying-power reservation, same-symbol
conflicts, duplicate or competing orders, ordering policy, partial acceptance
versus all-or-nothing policy, stale quote or risk snapshots, changed portfolio
snapshots, and future idempotency or `client_order_id` design. None of those
policies were implemented.

No production Python code, imports, tests, broker routing, Alpaca changes,
`submit_order`, order submission, idempotency implementation,
client-order-id generation, batch cash reservation, same-symbol conflict
resolution, persistence writes, audit logging writes, scheduler/runtime
behavior, portfolio mutation, fills, reconciliation changes, ML, or LLM
trading-path logic was added.

The full-suite checkpoint remains:

```text
python -m pytest
321 passed, 4 skipped
```

## Phase 18 Step 2 Minimal ExecutionPlan Contract

Phase 18 Step 2 adds the smallest implemented execution-planning contract in:

```text
src/algotrader/orchestration/execution_planning_flow.py
```

The new `ExecutionPlan` is an immutable, slotted dataclass with one field:
`intents: tuple[ExecutionIntent, ...]`. It is only an immutable batch container
for internal `ExecutionIntent` objects. It preserves input intent order and
preserves each exact `ExecutionIntent` object by identity.

`build_execution_plan(...)` accepts any iterable of `ExecutionIntent` objects
and returns `ExecutionPlan(intents=tuple(...))`. Empty input returns
`ExecutionPlan(intents=())`. The builder does not mutate inputs, unwrap source
`SignalRiskEvaluation` objects, copy proposed orders, compute batch cash,
resolve same-symbol conflicts, generate idempotency keys or client order IDs,
call brokers, submit orders, use schedulers, persist anything, mutate
portfolios, create fills, or call ML/LLM trading-path logic.

Traceability remains source-driven. Proposed orders and risk verdicts are still
reachable through
`plan.intents[n].source_evaluation.order` and
`plan.intents[n].source_evaluation.risk`. `ExecutionPlan` has no direct order,
risk, status, broker, account, venue, submission, fill, idempotency, client
order ID, cash reservation, priority, SDK, Alpaca, or persistence fields.

Dependency-direction guardrails now include
`algotrader.orchestration.execution_planning_flow` in the pre-execution
orchestration boundary checks and add a narrow AST guard against broker/runtime
call names in that module.

No broker routing, paper or live order submission, Alpaca changes,
`submit_order`, scheduler/runtime behavior, persistence writes, idempotency,
client-order-id generation, batch cash reservation, same-symbol conflict
resolution, portfolio mutation, fills, reconciliation changes, ML, or LLM
trading-path logic was added.

The full suite is now:

```text
python -m pytest
341 passed, 4 skipped
```

## Phase 18 Step 3 ExecutionPlan Traceability Hardening

Phase 18 Step 3 is tests and documentation only. It hardens the
`ExecutionPlan` contract without changing production Python code.

`ExecutionPlan` remains an immutable, slotted, pre-broker batch container with
exactly one dataclass field: `intents`. Each plan entry preserves the exact
original `ExecutionIntent` object by identity. Each intent still preserves the
exact original `SignalRiskEvaluation` object by identity.

Traceability flows through:

```text
plan.intents[n].source_evaluation
```

Proposed orders, risk verdicts, and statuses remain reachable through
`plan.intents[n].source_evaluation.order`,
`plan.intents[n].source_evaluation.risk`, and
`plan.intents[n].source_evaluation.status`; no convenience fields such as
`plan.orders`, `plan.risks`, `plan.statuses`, `plan.selected`,
`plan.rejected`, or `plan.skipped` were added.

Additional tests pin that no selected/rejected/skipped/accepted intent fields,
broker IDs, broker names, account IDs, venue fields, client order IDs,
idempotency keys, submission timestamps, fill fields, cash or buying-power
reservation fields, priority/rank fields, Alpaca-specific fields, SDK/native
objects, or persistence metadata are exposed on `ExecutionPlan`.

The builder remains a pure batch-container builder. It still preserves input
order, preserves duplicate and same-symbol intents without deduplication or
conflict resolution, performs no batch-level cash reservation or collective
affordability check, applies no priority/ranking policy, mutates no inputs, and
requires no portfolio, risk engine, broker, execution object,
scheduler/runtime object, or persistence handle.

No broker routing, paper or live order submission, Alpaca changes,
`submit_order`, scheduler/runtime behavior, persistence writes, idempotency,
client-order-id generation, batch cash reservation, same-symbol conflict
resolution, duplicate/competing order policy, priority/ranking policy,
portfolio mutation, fills, reconciliation changes, ML, or LLM trading-path
logic was added.

The full suite is now:

```text
python -m pytest
349 passed, 4 skipped
```

## Phase 19 Step 1 Execution-Planning Policy Design

Phase 19 Step 1 is documentation-only. It adds
[`docs/design/phase19_execution_planning_policy.md`](design/phase19_execution_planning_policy.md)
as the no-code design record for a future execution-planning policy layer after
minimal `ExecutionPlan` construction.

The design clarifies that `ExecutionIntent` remains a single source-only,
pre-submission candidate and that `ExecutionPlan` remains an immutable batch
container with exactly one dataclass field: `intents`. A future planning policy
may later decide which intents remain eligible after deterministic batch-level
checks, but no policy has been implemented in this step.

The design records unresolved policy questions around batch cash affordability,
buying-power reservation, same-symbol conflicts, duplicate or competing
intents, partial acceptance versus all-or-nothing behavior, stale quote or risk
snapshots, priority/ranking, idempotency separation, persistence/audit
separation, and broker/execution separation.

No production Python code, tests, imports, runtime behavior, broker routing,
paper or live order submission, Alpaca changes, `submit_order`,
scheduler/runtime behavior, persistence writes, audit logging writes,
idempotency, client-order-id generation, batch cash reservation, buying-power
reservation, same-symbol conflict resolution, duplicate/competing order policy,
priority/ranking policy, portfolio mutation, fills, reconciliation changes, ML,
or LLM trading-path logic was added.

The full suite remains:

```text
python -m pytest
349 passed, 4 skipped
```

Normal pytest remains offline and credential-free.

## Phase 19 Step 2 Minimal Planning Policy Contract

Phase 19 Step 2 adds a narrow pre-broker planning policy result boundary in
`src/algotrader/orchestration/execution_planning_policy.py`.

The new immutable result shapes are:

```text
SkippedExecutionIntent(intent: ExecutionIntent, reason: str)
PlanningPolicyResult(
    accepted_intents: tuple[ExecutionIntent, ...],
    skipped_intents: tuple[SkippedExecutionIntent, ...],
)
```

`apply_noop_execution_planning_policy(...)` accepts an `ExecutionPlan` and
returns a `PlanningPolicyResult`. It accepts every intent from the input plan in
the original order, preserves each `ExecutionIntent` object by identity, keeps
each source `SignalRiskEvaluation` reachable by identity through
`accepted_intents[n].source_evaluation`, and returns
`skipped_intents=()`.

`skipped_intents` exists only as a future traceability shape for deterministic
skip reasons. Phase 19 Step 2 does not add real skip logic, partial acceptance
policy, rejection policy, cash reservation, buying-power reservation,
same-symbol conflict handling, duplicate/competing order policy,
priority/ranking policy, idempotency, client-order-id generation,
broker-facing request construction, broker routing, order submission,
persistence writes, audit logging writes, scheduler/runtime behavior, portfolio
mutation, fills, reconciliation changes, ML, or LLM trading-path logic.

Dependency-direction tests now include
`algotrader.orchestration.execution_planning_policy` in the pre-execution
orchestration boundary and in the narrow AST guard against broker/runtime
imports, names, and calls.

The full suite is now:

```text
python -m pytest
374 passed, 4 skipped
```

## Phase 19 Step 3 PlanningPolicyResult Traceability Hardening

Phase 19 Step 3 is tests and documentation only. It hardens the minimal
planning policy result contract without changing production Python code.

`PlanningPolicyResult` remains an immutable, pre-broker result container with
exactly two dataclass fields: `accepted_intents` and `skipped_intents`.
`SkippedExecutionIntent` remains an immutable traceability wrapper with exactly
two dataclass fields: `intent` and `reason`.

Accepted-intent traceability flows through:

```text
result.accepted_intents[n].source_evaluation
```

Skipped-intent traceability flows through:

```text
result.skipped_intents[n].intent.source_evaluation
```

Proposed orders, risk verdicts, and statuses remain reachable through the
source `SignalRiskEvaluation` object, not through direct fields or convenience
properties on `PlanningPolicyResult` or `SkippedExecutionIntent`.

The no-op policy still accepts every input intent in order, preserves
`ExecutionIntent` object identity, preserves source `SignalRiskEvaluation`
object identity, and returns `skipped_intents=()`. Manually constructed skipped
results are covered only to pin the future traceability shape; no skip policy
logic was added.

No broker routing, paper or live order submission, Alpaca changes,
`submit_order`, scheduler/runtime behavior, persistence writes, audit logging
writes, idempotency, client-order-id generation, batch cash reservation,
buying-power reservation, same-symbol conflict resolution, duplicate/competing
order policy, priority/ranking policy, portfolio mutation, fills,
reconciliation changes, ML, or LLM trading-path logic was added.

The full suite is now:

```text
python -m pytest
379 passed, 4 skipped
```

## Phase 20 Step 1 Maximum Intents Planning Policy Design

Phase 20 Step 1 is documentation-only. It adds
[`docs/design/phase20_max_intents_policy.md`](design/phase20_max_intents_policy.md)
as the no-code design record for a future maximum accepted intents per plan
policy after minimal `ExecutionPlan` construction.

The design clarifies that a future max-intents policy may accept the first `N`
intents from an `ExecutionPlan`, preserve original plan order and object
identity, and wrap later intents in `SkippedExecutionIntent` with deterministic
reason text such as `"max_intents_per_plan_exceeded"`. This is a pre-broker,
batch-level planning decision only.

`PlanningPolicyResult` remains a pre-broker result container with
`accepted_intents` and `skipped_intents`. `SkippedExecutionIntent` remains a
traceability wrapper with `intent` and `reason`. `ExecutionIntent` and
`ExecutionPlan` remain unchanged. The current
`apply_noop_execution_planning_policy(...)` function remains pass-through only:
it accepts every input intent and returns `skipped_intents=()`.

No production Python code, tests, imports, runtime behavior, policy config
object, max-intents policy function, broker routing, Alpaca changes,
`submit_order`, order submission, idempotency, `client_order_id` generation,
batch cash reservation, buying-power reservation, same-symbol conflict
resolution, duplicate/competing order policy, priority/ranking policy,
persistence writes, audit logging writes, scheduler/runtime behavior,
portfolio mutation, fills, reconciliation changes, ML, or LLM trading-path
logic was added.

The full suite remains:

```text
python -m pytest
379 passed, 4 skipped
```

## Phase 20 Step 2 Max Intents Planning Policy Contract

Phase 20 Step 2 adds the first real execution-planning policy contract in:

```text
src/algotrader/orchestration/execution_planning_policy.py
```

The new immutable config is:

```text
MaxAcceptedIntentsPolicyConfig(max_accepted_intents: int)
```

`max_accepted_intents` must be exactly an `int` greater than or equal to `1`.
`bool` is rejected even though it is an `int` subclass, and `None`, `0`,
negative values, `float`, `str`, and `Decimal` values are rejected. `None` does
not mean no cap; `apply_noop_execution_planning_policy(...)` remains the
separate no-cap pass-through policy.

The new deterministic reason constant is:

```text
MAX_INTENTS_PER_PLAN_EXCEEDED_REASON = "max_intents_per_plan_exceeded"
```

`apply_max_intents_execution_planning_policy(plan, config)` accepts the first
`config.max_accepted_intents` intents in existing `ExecutionPlan` order and
wraps remaining intents in `SkippedExecutionIntent` with the deterministic
reason above. Accepted and skipped `ExecutionIntent` object identity is
preserved, and each source `SignalRiskEvaluation` remains traceable through
`source_evaluation`.

The policy is pure, deterministic, offline, broker-agnostic, and pre-broker. It
does not mutate the input plan, intents, or source evaluations. It does not
perform cash reservation, buying-power reservation, same-symbol conflict
handling, duplicate/competing order policy, deduplication, priority/ranking,
idempotency, `client_order_id` generation, broker routing, order submission,
persistence writes, audit logging writes, scheduler/runtime behavior,
portfolio mutation, fills, reconciliation changes, ML, or LLM trading-path
logic.

Focused validation:

```text
python -m pytest tests/unit/test_execution_planning_policy.py
64 passed

python -m pytest tests/unit/test_dependency_direction.py
6 passed
```

The full suite is now:

```text
python -m pytest
413 passed, 4 skipped
```

## Phase 20 Step 3 Max Intents Policy Traceability Hardening

Phase 20 Step 3 is tests and documentation only. It adds focused max-intents
traceability hardening coverage in:

```text
tests/unit/test_execution_planning_policy.py
```

The added tests prove that `apply_max_intents_execution_planning_policy(...)`
preserves accepted `ExecutionIntent` identity, preserves skipped
`ExecutionIntent` identity through `SkippedExecutionIntent.intent`, preserves
deterministic accepted and skipped ordering, uses the deterministic
`"max_intents_per_plan_exceeded"` skip reason, and does not mutate the original
`ExecutionPlan`.

Traceability remains source-driven. Accepted source evaluations remain
reachable through `result.accepted_intents[n].source_evaluation`, and skipped
source evaluations remain reachable through
`result.skipped_intents[n].intent.source_evaluation`. Proposed orders, risk
verdicts, and statuses remain reachable only through those source evaluations.

The hardening tests also pin that forbidden broker, execution, runtime,
persistence, idempotency, `client_order_id`, cash, buying-power,
priority/ranking, direct order/risk/status, and skip provenance fields are not
exposed by the max-intents policy result surface.

No production Python code, imports, runtime behavior, broker routing, Alpaca
changes, `submit_order`, order submission, idempotency, `client_order_id`
generation, batch cash reservation, buying-power reservation, same-symbol
conflict resolution, duplicate/competing order policy, priority/ranking policy,
persistence writes, audit logging writes, scheduler/runtime behavior, portfolio
mutation, fills, reconciliation changes, ML, or LLM trading-path logic was
added.

The full suite is now:

```text
python -m pytest
415 passed, 4 skipped
```

## Phase 21 Step 1 Research/Validation Boundary Design

Phase 21 Step 1 started and completed as documentation-only. It adds the new
design boundary in:

```text
docs/design/phase21_research_validation_boundary.md
```

The design separates historical research, feature exploration, backtesting,
walk-forward validation, regime analysis, strategy notebooks/scripts, and
LLM-assisted research summaries from validated artifacts and the deterministic
trading core.

Research outputs remain advisory. A signal, feature, or strategy can affect
execution flow only after a reviewed artifact records the hypothesis, dataset
scope, assumptions, exact definitions, metrics, acceptance criteria, bias and
leakage controls, and approval status. Future implementation should begin with
contracts and types, then test-first pure deterministic logic, before any
runtime wiring.

The deterministic core remains separate from research/backtesting/LLM
workflows. It consumes only approved, explicit, validated inputs; normal pytest
remains offline and credential-free; and research outputs must be promoted
through explicit deterministic contracts before they can influence execution.

LLMs may assist with research narration, experiment summaries, hypothesis
generation, and journaling. LLMs must not generate live trade decisions, mutate
execution plans, approve orders, bypass risk checks, interact with brokers, or
enter the trading hot path.

No production code, tests, runtime behavior, broker behavior, Alpaca changes,
`submit_order`, scheduler/runtime behavior, persistence implementation,
idempotency, `client_order_id`, cash reservation, same-symbol conflict policy,
duplicate/competing order policy, priority/ranking implementation, portfolio
mutation, fills, ML training implementation, live data ingestion, or LLM
trading-path logic was added.

The Phase 21 Step 1 full-suite checkpoint was:

```text
python -m pytest
415 passed, 4 skipped
```

## Phase 21 Step 2 Validated Research Artifact Contract

Phase 21 Step 2 adds the minimal validated research artifact contract in:

```text
src/algotrader/research/validated_artifact.py
src/algotrader/research/__init__.py
```

The new contracts are immutable, slotted dataclasses:

```text
ResearchMetric(name, value)
ValidatedResearchArtifact(
    artifact_id,
    name,
    version,
    description,
    validated_at,
    metrics,
    assumptions,
    limitations,
    approved_for,
)
```

`ValidatedResearchArtifact` is a metadata/evidence contract only. It records a
reviewed artifact identifier, version, validation timestamp, metrics,
assumptions, limitations, and approved advisory uses. Tuple fields are stored
immutably and preserve metric, assumption, limitation, and approval order.
Empty required strings are rejected.

The focused tests live in:

```text
tests/unit/test_validated_research_artifact.py
tests/unit/test_dependency_direction.py
```

They prove immutability, slots, tuple storage, input order preservation, empty
string validation, absence of forbidden trading-path fields, no broker or
Alpaca behavior, no order, submit, fill, client-order-id, cash, portfolio, or
ranking behavior, no I/O, network, broker, or ingestion calls, and dependency
independence from execution planning, risk, broker, runtime, and persistence
modules.

This phase does not create signals, approve trades, mutate execution plans,
interact with broker, Alpaca, scheduler/runtime, persistence, or live data, or
put LLMs in the trading hot path.

Focused validation:

```text
python -m pytest tests/unit/test_validated_research_artifact.py
25 passed

python -m pytest tests/unit/test_dependency_direction.py
7 passed
```

The full suite is now:

```text
python -m pytest
441 passed, 4 skipped
```

## Phase 21 Step 3 Validated Research Artifact Traceability Hardening

Phase 21 Step 3 is tests and documentation only. It changes no production
source and keeps `ResearchMetric` and `ValidatedResearchArtifact` as
metadata/evidence contracts only.

The hardened tests live in:

```text
tests/unit/test_validated_research_artifact.py
```

They prove that metric object identity is preserved inside
`ValidatedResearchArtifact.metrics`, metrics preserve deterministic order,
assumptions preserve deterministic order, limitations preserve deterministic
order, approved advisory uses preserve deterministic order, and tuple fields
cannot be mutated after construction.

The tests also pin that validated research artifacts remain advisory metadata
only. They do not expose trading-path fields such as symbols, sides,
quantities, orders, order IDs, client order IDs, broker or Alpaca fields,
submission fields, fills, cash, buying power, reservations, portfolio,
positions, risk approval, execution plans, priority, rank, or score. They
remain independent from `ExecutionPlan`, `ExecutionIntent`,
`PlanningPolicyResult`, and risk-evaluation types.

Validated research artifacts do not create signals, approve trades, mutate
execution plans, interact with broker, Alpaca, scheduler/runtime, persistence,
or live data, add ML training, or put LLMs in the trading hot path.

Focused validation:

```text
python -m pytest tests/unit/test_validated_research_artifact.py
34 passed

python -m pytest tests/unit/test_dependency_direction.py
7 passed
```

The full suite is now:

```text
python -m pytest
450 passed, 4 skipped
```

## Phase 22 Step 1 Validated Signal Definition Boundary Design

Phase 22 Step 1 is documentation-only. It adds the new design boundary in:

```text
docs/design/phase22_validated_signal_definition_boundary.md
```

The design defines a future validated signal definition as a reviewed,
versioned, deterministic signal-rule contract supported by a validated research
artifact. A validated signal definition is not raw research output, not a
backtest result, not a feature, not a strategy, not an execution intent, not an
execution plan, and not a broker order.

The future metadata may include a signal id, name, version, description, source
validated research artifact id/version, required inputs, output type,
deterministic evaluation rule reference, allowed advisory use, assumptions,
limitations, and validation evidence references.

The design explicitly excludes symbol-specific live recommendations, side,
quantity, order type, broker fields, Alpaca fields, `submit_order`, cash or
buying-power reservation, portfolio mutation, risk approval, ranking/priority
behavior, execution-plan mutation, fills, and LLM-generated trade decisions.

The intended promotion path is:

```text
research hypothesis
  -> validated research artifact
  -> approved signal definition
  -> future deterministic signal evaluator
  -> future signal-to-risk flow
```

Validated research artifacts remain advisory. Validated signal definitions are
not execution decisions, do not create signals by themselves, do not approve
trades, do not mutate execution plans, and do not interact with broker, Alpaca,
scheduler/runtime, persistence, or live data. LLMs may summarize research and
document hypotheses, but they may not generate live signal outputs, approve
trades, mutate execution plans, bypass deterministic risk checks, or enter the
trading hot path.

No production code, tests, runtime behavior, signal computation, strategy
implementation, feature computation, ranking/priority policy, broker behavior,
execution-plan mutation, order submission, scheduler/runtime behavior,
persistence implementation, live data ingestion, ML training, or LLM
trading-path logic was added.

The latest full-suite checkpoint remains:

```text
python -m pytest
450 passed, 4 skipped
```

## Phase 22 Step 2 Validated Signal Definition Contract

Phase 22 Step 2 adds the minimal validated signal definition contract in:

```text
src/algotrader/signals/validated_signal_definition.py
src/algotrader/signals/__init__.py
```

The new contract is an immutable, slotted dataclass:

```text
ValidatedSignalDefinition(
    signal_id,
    name,
    version,
    description,
    source_artifact_id,
    source_artifact_version,
    required_inputs,
    output_type,
    evaluation_rule_ref,
    approved_for,
    assumptions,
    limitations,
)
```

`ValidatedSignalDefinition` is definition metadata only. It records stable
signal identity, source validated research artifact id/version strings,
required input names, expected output type, deterministic evaluation rule
reference, approved advisory uses, assumptions, and limitations. Tuple fields
are stored immutably and preserve required-input, approved-use, assumption, and
limitation order. Empty required strings are rejected.

The focused tests live in:

```text
tests/unit/test_validated_signal_definition.py
tests/unit/test_dependency_direction.py
```

They prove immutability, slots, tuple storage, input order preservation, empty
string validation, metadata-only fields, absence of forbidden trading-path
fields, no buy/sell/hold recommendation behavior, no I/O, network, broker,
ingestion, or scheduling calls, independence from execution planning, risk,
broker, and runtime modules, and stable id/version-only references to validated
research artifacts.

This phase does not evaluate signals, create execution intents, approve trades,
mutate execution plans, interact with broker, Alpaca, scheduler/runtime,
persistence, or live data, add ML training, or put LLMs in the trading hot
path.

Focused validation:

```text
python -m pytest tests/unit/test_validated_signal_definition.py
29 passed

python -m pytest tests/unit/test_dependency_direction.py
7 passed
```

The full suite is now:

```text
python -m pytest
479 passed, 4 skipped
```

## Phase 22 Step 3 Validated Signal Definition Traceability Hardening

Phase 22 Step 3 is tests and documentation only. It changes no production
source and keeps `ValidatedSignalDefinition` as definition metadata only.

The hardened tests live in:

```text
tests/unit/test_validated_signal_definition.py
```

They prove that `source_artifact_id` and `source_artifact_version` are
preserved exactly, `required_inputs` preserve deterministic order,
`approved_for` preserves deterministic order, `assumptions` preserve
deterministic order, `limitations` preserve deterministic order, and tuple
fields cannot be mutated after construction.

The tests also pin that validated signal definitions remain metadata-only. They
do not expose trading-path fields such as symbols, sides, quantities, orders,
order IDs, client order IDs, broker or Alpaca fields, submission fields, fills,
cash, buying power, reservations, portfolio, positions, risk approval,
execution intents, execution plans, priority, rank, or score. They remain
independent from `ValidatedResearchArtifact` runtime objects, `ExecutionPlan`,
`ExecutionIntent`, `PlanningPolicyResult`, risk-evaluation types, broker
modules, runtime/scheduler modules, and persistence modules.

Validated signal definitions do not evaluate signals, produce buy/sell/hold
outputs, create execution intents, approve trades, mutate execution plans,
interact with broker, Alpaca, scheduler/runtime, persistence, or live data, add
ML training, or put LLMs in the trading hot path.

Focused validation:

```text
python -m pytest tests/unit/test_validated_signal_definition.py
38 passed

python -m pytest tests/unit/test_dependency_direction.py
7 passed
```

The full suite is now:

```text
python -m pytest
488 passed, 4 skipped
```

## Phase 23 Step 1 Signal Evaluation Clock Boundary Design

Phase 23 Step 1 is documentation-only. It adds the new design boundary in:

```text
docs/design/phase23_signal_evaluation_clock_boundary.md
```

The design defines future deterministic signal evaluation as a pure advisory
boundary that may consume approved `ValidatedSignalDefinition` metadata plus
explicit feature/input snapshots, explicit observation timestamps, an explicit
`as_of` timestamp, deterministic context, and snapshot fingerprints.

Future evaluator outputs may include only advisory metadata such as signal
id/version, evaluation timestamp, as-of timestamp, deterministic signal value,
score or bucket, reason or explanation code, input snapshot fingerprint,
evaluation fingerprint/id, and assumptions or limitations references.

The design explicitly excludes `ProposedOrder`, orders, order IDs, client order
IDs, broker requests, symbol-specific order instructions, execution-command
side, quantity, cash or buying-power reservation, portfolio mutation, risk
approval, execution intents, execution plans, fills, ranking/priority
decisions, and LLM-generated trade decisions.

Clock and as-of rules are explicit. Future deterministic signal, risk, and
orchestration layers should receive time as data, reject naive datetimes, prefer
UTC internally, and avoid direct calls to wall-clock APIs, random generators,
UUID randomness, or environment-variable reads except in explicit boundary
modules.

Lookahead-bias prevention is part of the future contract: input observations
after `as_of` must be rejected, snapshots must be explicit, feature values must
be timestamped or traceable to timestamped windows, hidden live data fetches and
implicit data revisions are forbidden, and retrospective parameter changes
require a new version.

No production code, tests, runtime behavior, signal evaluator implementation,
clock implementation, signal computation, feature computation, strategy engine,
Signal -> Risk bridge, ranking/priority policy, broker behavior, Alpaca
changes, order submission, scheduler/runtime behavior, persistence
implementation, live data ingestion, ML training, or LLM trading-path logic was
added.

The full suite remains:

```text
python -m pytest
488 passed, 4 skipped
```

## Phase 23 Step 2 Minimal Clock / Timestamp Contract

Phase 23 Step 2 adds the minimal deterministic time contract in:

```text
src/algotrader/core/time.py
```

The new contract includes:

```text
require_utc_datetime(value: datetime) -> datetime
Clock.now() -> datetime
FixedClock(timestamp).now() -> datetime
assert_not_after_as_of(observed_at, as_of) -> None
```

`require_utc_datetime(...)` accepts only timezone-aware UTC datetimes and
returns the original datetime object when valid. It rejects naive datetimes,
non-datetime values, and non-UTC aware datetimes instead of normalizing them.

`Clock` is an injectable protocol only. `FixedClock` is a frozen, slotted
dataclass that stores one validated UTC timestamp and returns exactly that
stored object from `now()`. It does not call `datetime.now`,
`datetime.utcnow`, `time.time`, `time.monotonic`, random generators, UUID
randomness, environment variables, I/O, network, brokers, scheduler/runtime, or
persistence.

`assert_not_after_as_of(...)` validates both timestamps and rejects
`observed_at > as_of`. It is a lookahead-prevention helper only, not a signal
evaluator.

Focused validation:

```text
python -m pytest tests/unit/test_time_contracts.py
21 passed

python -m pytest tests/unit/test_dependency_direction.py
8 passed
```

This phase does not evaluate signals, compute features, implement a strategy,
rank or prioritize candidates, approve trades, create execution intents, mutate
execution plans, interact with broker, Alpaca, scheduler/runtime, persistence,
or live data, add ML training, or put LLMs in the trading hot path.

The full suite is now:

```text
python -m pytest
510 passed, 4 skipped
```

## Phase 23 Step 3 Clock / Timestamp Traceability Hardening

Phase 23 Step 3 is tests and documentation only. It changes no production
source and keeps `src/algotrader/core/time.py` unchanged.

The hardened tests live in:

```text
tests/unit/test_time_contracts.py
tests/unit/test_dependency_direction.py
```

They prove that `require_utc_datetime(...)` preserves the exact valid UTC
datetime object, `FixedClock.now()` repeatedly returns the exact stored
datetime object, `FixedClock` remains frozen and slotted, naive datetimes are
rejected, non-UTC aware datetimes are rejected, `assert_not_after_as_of(...)`
allows equality and earlier observations, and `observed_at > as_of` is
rejected.

The tests also pin that the time module remains independent from signals,
research, risk, orchestration, execution, broker, Alpaca, scheduler/runtime,
persistence, ML, and LLM modules. It exposes no trading-path fields or behavior
such as symbol, side, quantity, order, order id, client order id, broker,
Alpaca, `submit_order`, fill, cash, buying power, portfolio, risk approval,
execution plan, priority, rank, or score. It does not call hidden
nondeterministic APIs such as `datetime.now`, `datetime.utcnow`, `time.time`,
`time.monotonic`, random generators, UUID randomness, or `os.environ`.

Time contracts remain deterministic primitives only. They do not evaluate
signals, fetch live data, read system time in deterministic paths, approve
trades, mutate execution plans, interact with broker, Alpaca,
scheduler/runtime, persistence, ML, or LLM trading-path logic.

Focused validation:

```text
python -m pytest tests/unit/test_time_contracts.py
26 passed

python -m pytest tests/unit/test_dependency_direction.py
8 passed
```

The full suite is now:

```text
python -m pytest
515 passed, 4 skipped
```

## Phase 24 Step 1 Signal Evaluation Result Boundary Design

Phase 24 Step 1 is documentation only. It creates the future
`SignalEvaluationResult` boundary in:

```text
docs/design/phase24_signal_evaluation_result_boundary.md
```

The design defines `SignalEvaluationResult` as the future advisory deterministic
output of applying a validated signal definition to explicit input snapshots at
an explicit `as_of` boundary. It is traceable to signal definition id/version,
source artifact id/version, input snapshot id or fingerprint, UTC-aware
`as_of`, UTC-aware `evaluated_at`, deterministic output values, reason codes,
diagnostics, assumptions, and limitations.

The design also defines what the result is not: it is not an order, broker
request, risk approval, execution intent, execution plan, portfolio mutation,
ranking or priority decision, or LLM decision. Future result fields must not
include `ProposedOrder`, order ids, client order ids, broker or Alpaca fields,
`submit_order`, symbol-specific order instructions, side as an execution
command, quantity, cash, buying power, reservations, portfolio or position
mutation, `risk_approved`, execution intent, execution plan, fills, priority,
rank as execution priority, or LLM-generated decisions.

The future result boundary reaffirms the Phase 23 clock contract: `as_of` must
be explicit, `evaluated_at` must be explicit or provided by an injected
deterministic clock in a future implementation, all timestamps must be
UTC-aware, naive datetimes must be rejected, hidden system time reads are not
allowed, and no input observation timestamp may be after `as_of`.

Reproducibility remains required. The same signal definition, same inputs, and
same `as_of` timestamp must produce the same future advisory result.
Evaluation ids should eventually be deterministic, input snapshot fingerprints
should eventually be content-addressable, and future evaluation must not depend
on network calls, broker calls, LLM calls, or mutable global state.

This phase adds no production code, tests, runtime behavior,
`SignalEvaluationResult` implementation, signal evaluator implementation,
signal computation, strategy implementation, feature computation, ranking or
priority behavior, execution-plan mutation, risk approval behavior, broker
behavior, Alpaca behavior, order submission, scheduler/runtime behavior,
persistence implementation, live data ingestion, ML training, or LLM
trading-path logic.

## Phase 24 Step 2 Minimal SignalEvaluationResult Contract

Phase 24 Step 2 adds the minimal advisory signal-evaluation result contract in:

```text
src/algotrader/signals/signal_evaluation_result.py
src/algotrader/signals/__init__.py
```

The new contract is an immutable, slotted dataclass:

```text
SignalEvaluationResult(
    evaluation_id,
    signal_id,
    signal_version,
    source_artifact_id,
    source_artifact_version,
    as_of,
    evaluated_at,
    input_fingerprint,
    output_value,
    reason_code,
    diagnostics,
    assumptions,
    limitations,
)
```

`SignalEvaluationResult` is advisory evaluation metadata only. It records stable
evaluation identity, signal definition id/version, source artifact id/version,
explicit UTC-aware `as_of`, explicit UTC-aware `evaluated_at`, input
fingerprint, deterministic advisory output value, reason code, diagnostics,
assumptions, and limitations. Tuple fields are stored immutably and preserve
diagnostic, assumption, and limitation order. Empty required strings are
rejected.

The focused tests live in:

```text
tests/unit/test_signal_evaluation_result.py
tests/unit/test_dependency_direction.py
```

They prove immutability, slots, tuple storage, tuple order preservation, empty
string validation, naive and non-UTC datetime rejection, UTC-aware datetime
identity preservation, advisory metadata-only fields, absence of forbidden
trading-path fields, no I/O, network, broker, ingestion, or scheduling calls,
and independence from execution planning, risk, broker, runtime, persistence,
ML, and LLM modules.

This phase does not evaluate signals, compute features, implement strategies,
rank or prioritize candidates, create execution intents, approve trades, mutate
execution plans, interact with broker, Alpaca, scheduler/runtime, persistence,
or live data, add ML training, or put LLMs in the trading hot path.

Focused validation:

```text
python -m pytest tests/unit/test_signal_evaluation_result.py
33 passed

python -m pytest tests/unit/test_dependency_direction.py
8 passed
```

The full suite is now:

```text
python -m pytest
548 passed, 4 skipped
```

## Phase 24 Step 3 SignalEvaluationResult Traceability Hardening

Phase 24 Step 3 is tests and documentation only. It changes no production
source and keeps `SignalEvaluationResult` as a minimal advisory metadata
contract.

The hardened tests live in:

```text
tests/unit/test_signal_evaluation_result.py
tests/unit/test_dependency_direction.py
```

They prove exact identity preservation of `as_of`, exact identity preservation
of `evaluated_at`, deterministic ordering for `diagnostics`, `assumptions`, and
`limitations`, tuple immutability after construction, exact preservation of
trace string fields, advisory-only surface area, absence of forbidden
trading-path fields, no signal output behavior, no strategy behavior, no
execution intent creation, no risk approval behavior, no execution-plan
mutation behavior, no broker/account/order/fill fields, no
scheduler/runtime/persistence fields, no ML or LLM trading-path fields, and no
dependency on execution, risk, broker, runtime, persistence, ML, or LLM
modules.

This phase does not evaluate signals, compute features, implement strategies,
rank or prioritize candidates, create execution intents, approve trades, mutate
execution plans, interact with broker, Alpaca, scheduler/runtime, persistence,
or live data, add ML training or inference, or put LLMs in the trading hot
path.

Focused validation:

```text
python -m pytest tests/unit/test_signal_evaluation_result.py
40 passed

python -m pytest tests/unit/test_dependency_direction.py
8 passed
```

The full suite is now:

```text
python -m pytest
555 passed, 4 skipped
```

## Phase 25 Step 1 Signal Evaluator Boundary Design

Phase 25 Step 1 is documentation-only. It creates the future deterministic
signal evaluator boundary in:

```text
docs/design/phase25_signal_evaluator_boundary.md
```

The design defines a future evaluator as an offline-safe deterministic boundary
that may later transform `ValidatedSignalDefinition` metadata plus explicit
deterministic input snapshots, an explicit UTC-aware `as_of` timestamp, and an
explicit UTC-aware `evaluated_at` timestamp or deterministic clock into
advisory `SignalEvaluationResult` objects.

The future output remains traceable to signal definition id/version, source
validated research artifact id/version, input snapshot identity or fingerprint,
`as_of`, and `evaluated_at`. It remains advisory metadata only: not an
execution signal, not a trade approval, not an order request, not risk
approval, not an execution intent, not an execution plan, and not a broker
payload.

The boundary requires deterministic guarantees: same inputs produce the same
result, no hidden wall-clock access, no environment-variable driven behavior,
no random behavior, no network calls, no file or database writes, no broker,
account, position, order, or fill access, no input mutation, no LLM calls, and
no ML training or inference unless later promoted through explicit
deterministic contracts.

The design records the as-of and lookahead rule that all observations used by
evaluation must satisfy `observed_at <= as_of`. Future observations must be
rejected, and the future evaluator should use the existing deterministic time
contract with explicit UTC-aware timestamps.

This phase does not add production code, tests, runtime behavior, signal
evaluator implementation, signal computation, feature computation, strategy
logic, ranking or priority behavior, signal-to-risk conversion, risk approval,
execution intent creation, execution-plan mutation, portfolio mutation, broker
or Alpaca behavior, order submission, scheduler/runtime behavior, persistence,
live data ingestion, ML training or inference, or LLM trading-path logic.

The latest full-suite checkpoint remains:

```text
python -m pytest
555 passed, 4 skipped
```

## Phase 25 Step 2 Minimal Signal Evaluation Input Snapshot Contract

Phase 25 Step 2 adds the minimal signal-evaluation input snapshot/reference
contract in:

```text
src/algotrader/signals/signal_evaluation_input.py
src/algotrader/signals/__init__.py
```

The new contract is an immutable, slotted dataclass:

```text
SignalEvaluationInputSnapshot(
    snapshot_id,
    as_of,
    required_input_names,
    source_ids,
)
```

`SignalEvaluationInputSnapshot` is metadata/reference-only. It records stable
snapshot identity, an explicit UTC-aware `as_of` timestamp, ordered required
input names, and ordered source identifiers. It exists only to provide
deterministic, explicit input traceability for a future evaluator.

The contract validates `as_of` with the existing deterministic time contract,
rejects naive and non-UTC datetimes, rejects empty or blank trace strings,
converts iterable metadata fields into tuples, preserves tuple ordering,
preserves accepted string values exactly, and is frozen and slotted.

The focused tests live in:

```text
tests/unit/test_signal_evaluation_input.py
tests/unit/test_dependency_direction.py
```

They prove contract existence, exact field set, immutability, slots, valid
construction, UTC-aware `as_of` validation, naive and non-UTC datetime
rejection, `as_of` identity preservation, tuple coercion, deterministic tuple
ordering, tuple immutability, string validation, exact string preservation,
metadata/reference-only surface area, absence of signal output fields, absence
of score/direction/confidence/order/risk/execution fields, dependency
independence, and absence of hidden wall-clock, random, network, filesystem
write, environment, broker, runtime, persistence, ML, and LLM calls.

This phase does not add a signal evaluator, signal computation, feature
computation, strategy logic, ranking or priority behavior, signal-to-risk
conversion, risk approval, execution intent creation, execution-plan mutation,
portfolio mutation, broker or Alpaca behavior, order submission,
scheduler/runtime behavior, persistence writes, live data ingestion, network
calls, ML training or inference, or LLM trading-path logic.

Focused validation:

```text
python -m pytest tests/unit/test_signal_evaluation_input.py
29 passed

python -m pytest tests/unit/test_dependency_direction.py
9 passed
```

The full suite is now:

```text
python -m pytest
585 passed, 4 skipped
```

## Phase 25 Step 3 Signal Evaluation Input Snapshot Traceability Hardening

Phase 25 Step 3 is tests and documentation only. It changes no production
source and keeps `SignalEvaluationInputSnapshot` as a minimal
metadata/reference-only input traceability contract for a future evaluator.

The hardened tests live in:

```text
tests/unit/test_signal_evaluation_input.py
tests/unit/test_dependency_direction.py
```

They prove exact `as_of` identity preservation, exact `snapshot_id` string
preservation, exact `required_input_names` string preservation, exact
`source_ids` string preservation, deterministic ordering of both tuple fields,
tuple immutability after construction, and isolation from later mutation of
the original input lists.

The tests also pin that the snapshot has no signal output behavior, no
score/direction/confidence fields, no order/risk/execution fields, no
broker/account/position/fill fields, no portfolio/cash/buying-power fields, no
scheduler/runtime/persistence fields, no ML/LLM fields, and no dependency on
`SignalEvaluationResult`, risk, execution, broker, runtime, persistence, ML,
or LLM modules.

Hidden access remains forbidden: no wall-clock calls, random calls,
network/socket access, filesystem writes, environment-variable reads, broker
SDK imports, or Alpaca imports are allowed in the contract.

This phase does not add a signal evaluator, signal computation, feature
computation, strategy logic, ranking or priority behavior, signal-to-risk
conversion, risk approval, execution intent creation, execution-plan mutation,
portfolio mutation, broker or Alpaca behavior, order submission,
scheduler/runtime behavior, persistence, live data ingestion, ML training or
inference, or LLM trading-path logic.

Focused validation:

```text
python -m pytest tests/unit/test_signal_evaluation_input.py
47 passed

python -m pytest tests/unit/test_dependency_direction.py
9 passed
```

The full suite is now:

```text
python -m pytest
603 passed, 4 skipped
```

## Phase 26 Step 1 Signal Evaluator No-Op Boundary Design

Phase 26 Step 1 is documentation-only. It creates the future no-op signal
evaluator boundary in:

```text
docs/design/phase26_signal_evaluator_noop_boundary.md
```

The design defines a signal evaluator narrowly for this project: a future
deterministic boundary that may later receive `ValidatedSignalDefinition`,
`SignalEvaluationInputSnapshot`, explicit UTC-aware `as_of`, explicit
UTC-aware `evaluated_at`, and deterministic metadata already available through
existing contracts, then construct advisory `SignalEvaluationResult` metadata.

The future no-op specialization exists only to prove that deterministic
input/output boundary. It must not compute real signal values, inspect live
market data, compute features, rank, score, infer direction, approve or reject
trades, create execution intents, mutate execution plans, prepare orders,
interact with brokers, call ML, or call LLMs.

Evaluator output remains strictly advisory and pre-risk. A
`SignalEvaluationResult` produced by any evaluator, including a future no-op
evaluator, does not constitute a signal firing, recommendation, risk approval,
execution instruction, execution intent, order request, or broker payload. No
sizing decision, exposure calculation, cash reservation, buying-power check, or
portfolio-level reasoning has occurred when a result is returned.

The design records timestamp invariants for future implementation: `as_of` is
the logical time the result describes, `evaluated_at` is the UTC-aware time the
evaluation occurred, future evaluator behavior must enforce
`evaluated_at >= as_of`, no input `as_of` or observation timestamp may be after
the result `as_of`, and no lookahead bias is permitted.

Future evaluator behavior must remain deterministic for identical inputs,
offline-safe, credential-free, free of hidden wall-clock access, free of random
or environment-variable driven behavior, network-free, write-free, broker-free,
input-immutable, ML-free, and LLM-free. Future evaluator modules must not import
broker, Alpaca, execution, risk, runtime/scheduler, persistence, ML, or LLM
modules.

The design also records an open design point: if `SignalEvaluationResult`
cannot safely represent a no-op result without ambiguity, the next
implementation phase should harden `SignalEvaluationResult` first instead of
adding an evaluator. This phase does not add that marker and does not modify
`SignalEvaluationResult`.

This phase does not add production code, tests, runtime behavior, signal
evaluator implementation, no-op evaluator class, evaluator protocol, result
contract changes, signal computation, feature computation, strategy logic,
ranking or priority behavior, signal-to-risk conversion, risk approval,
execution intent creation, execution-plan mutation, portfolio mutation, broker
or Alpaca behavior, order submission, scheduler/runtime behavior, persistence,
live data ingestion, ML training or inference, or LLM trading-path logic.

The latest full-suite checkpoint remains:

```text
python -m pytest
603 passed, 4 skipped
```

## Phase 26 Step 2 SignalEvaluationResult No-Op Readiness Review

Phase 26 Step 2 reviews whether the existing `SignalEvaluationResult` contract
can safely represent a future no-op evaluator result without adding ambiguous
signal, strategy, risk, execution, or actionability semantics.

The review conclusion is that the current metadata-only contract is sufficient
for a future minimal no-op evaluator. It already preserves signal definition
identity/version, source artifact identity/version, input snapshot identity
through `input_fingerprint`, explicit UTC-aware `as_of`, explicit UTC-aware
`evaluated_at`, advisory `output_value`, `reason_code`, `diagnostics`,
`assumptions`, and `limitations`.

No no-op marker, `result_kind`, or `evaluator_kind` is needed before evaluator
implementation. A future no-op result does not need `score`, `direction`,
`confidence`, `actionable`, or `should_trade` fields. A no-op marker is not
inherently trading behavior, but adding one too early risks creating a decision
switch or actionability proxy. The safer path is to keep the first no-op
evaluator result empty/advisory in meaning while using only existing metadata
fields.

A future no-op evaluator result is not structurally distinguishable from a
later real evaluator result by field shape. That is acceptable for the first
no-op boundary because both are advisory metadata. If distinction is needed, it
should come from explicit trace metadata values such as `evaluation_id`,
`input_fingerprint`, `output_value`, `reason_code`, `diagnostics`,
`assumptions`, and `limitations`, not from trading-path or actionability
fields.

This phase strengthens contract-surface tests in:

```text
tests/unit/test_signal_evaluation_result.py
```

The focused additions pin that `SignalEvaluationResult` has no score,
direction, confidence, probability, actionability, `should_trade`, no-op marker,
`result_kind`, `evaluator_kind`, risk, execution, broker, order, runtime,
persistence, ML, or LLM fields, and that existing metadata fields can preserve a
metadata-only no-op trace without implying actionability.

This phase does not change production source and does not add runtime behavior,
signal evaluator implementation, no-op evaluator class, evaluator protocol,
result contract changes, signal computation, feature computation, strategy
logic, ranking or priority behavior, signal-to-risk conversion, risk approval,
execution intent creation, execution-plan mutation, portfolio mutation, broker
or Alpaca behavior, order submission, scheduler/runtime behavior, persistence,
live data ingestion, ML training or inference, or LLM trading-path logic.

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

## Phase 26 Step 3 Minimal No-Op Signal Evaluator Contract

Phase 26 Step 3 adds the first evaluator-shaped production code in:

```text
src/algotrader/signals/noop_signal_evaluator.py
```

The new contract is a frozen, slotted class:

```text
NoOpSignalEvaluator.evaluate(
    definition,
    input_snapshot,
    *,
    as_of,
    evaluated_at,
) -> SignalEvaluationResult
```

`NoOpSignalEvaluator` accepts a `ValidatedSignalDefinition`, a
`SignalEvaluationInputSnapshot`, and explicit UTC-aware `as_of` and
`evaluated_at` timestamps. It validates timestamps through the deterministic
time contract, rejects naive and non-UTC datetimes, rejects
`evaluated_at < as_of`, rejects an input snapshot whose `as_of` is after the
result `as_of`, and returns an advisory `SignalEvaluationResult`.

The returned result preserves signal definition id/version, source artifact
id/version, input snapshot id through `input_fingerprint`, and accepted
timestamp object identity. Repeated calls with identical inputs produce equal
results. The evaluator does not mutate the signal definition or input snapshot.

The no-op output uses existing `SignalEvaluationResult` fields only. It uses
`NOOP_SIGNAL_EVALUATOR` as a non-actionable reason code and
`NO_SIGNAL_COMPUTED` as a non-numeric advisory output value. Diagnostics,
assumptions, and limitations state that no signal computation occurred and the
result is not a signal firing, recommendation, risk approval, or
execution-ready output.

This phase does not add `result_kind`, `evaluator_kind`, `is_noop`, or any
no-op marker field. It does not add real signal computation, feature
computation, strategy logic, scoring, ranking, confidence/probability, signal
direction, actionability flags, `should_trade`, signal-to-risk conversion,
risk approval, execution intent creation, execution-plan mutation, portfolio
mutation, broker or Alpaca behavior, order submission, scheduler/runtime
behavior, persistence writes, live data ingestion, network calls, ML training
or inference, or LLM trading-path logic.

Focused tests live in:

```text
tests/unit/test_noop_signal_evaluator.py
```

They prove existence, frozen/slotted shape, valid result construction, advisory
metadata wording, identity/version/input/timestamp preservation, UTC-aware
timestamp validation, `evaluated_at >= as_of`, input snapshot as-of guard,
deterministic repeated calls, input non-mutation, absence of score/confidence/
probability/direction/rank/priority/actionability/risk/execution/order/broker/
runtime/persistence/ML/LLM fields, and absence of forbidden imports or hidden
I/O, network, wall-clock, random, environment, broker, Alpaca, database,
persistence, ML, or LLM calls.

Phase 26 Step 3 focused validation at the time:

```text
python -m pytest tests/unit/test_noop_signal_evaluator.py
22 passed

python -m pytest tests/unit/test_dependency_direction.py
9 passed
```

At the end of Step 3, the full suite was:

```text
python -m pytest
627 passed, 4 skipped
```

## Phase 26 Step 4 No-Op Signal Evaluator Traceability Hardening

Phase 26 Step 4 is traceability hardening only. It strengthens
`tests/unit/test_noop_signal_evaluator.py` and updates documentation. No
production source code or production behavior was added.

`NoOpSignalEvaluator` remains deterministic and advisory-only. It proves the
evaluator input/output boundary without real signal computation and preserves
traceability without actionability. The hardened tests prove exact signal
definition id/version preservation, exact source validated research artifact
id/version preservation, exact input snapshot id preservation through
`input_fingerprint`, exact `as_of` and `evaluated_at` object identity, exact
`NOOP_SIGNAL_EVALUATOR` reason-code preservation, and deterministic ordering of
diagnostics, assumptions, and limitations.

The tests also harden determinism and side-effect boundaries: repeated calls
with identical inputs produce equal results, advisory tuple ordering is stable,
results do not depend on wall-clock APIs, environment variables, or random
state, and input definitions, snapshots, and tuple fields are not mutated.
Timestamp/lookahead coverage now explicitly accepts input snapshots at or
before the result `as_of` and rejects snapshots after the result `as_of`.

The no-op evaluator still does not score, rank, infer direction, set
confidence/probability, recommend trades, expose actionability, approve risk,
create execution intents, mutate execution plans, access live data, route to
brokers or Alpaca, submit orders, use scheduler/runtime/persistence behavior,
run ML, or use LLMs in the trading path. Normal pytest remains offline,
credential-free, and safe.

Focused validation:

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

## Phase 27 Step 1 Real Signal Evaluator Admission Boundary Design

Phase 27 Step 1 is documentation-only. It adds:

```text
docs/design/phase27_real_signal_evaluator_admission_boundary.md
```

The new design defines the admission boundary for any future real deterministic
signal evaluator. The system has a no-op evaluator seam, but real signal
computation remains forbidden until explicit admission criteria are met.

The boundary records why real evaluator work is risky: it is the first place
the system could accidentally introduce strategy logic, feature computation,
predictive behavior, ranking, direction, actionability, risk-like semantics,
lookahead bias, or hidden data access. The document requires future real
evaluator work to name the validated signal definition, supporting validated
research artifact, exact deterministic inputs, observation timestamps,
availability proof at or before `as_of`, advisory output meaning, assumptions,
limitations, and tests for determinism, lookahead prevention, no side effects,
and no trading-path dependencies.

The design also records the important current limitation:
`SignalEvaluationInputSnapshot` provides metadata/reference traceability only
through `snapshot_id`, `as_of`, `required_input_names`, and `source_ids`. It
does not carry actual feature values or market observations. A future real
evaluator likely needs a separate deterministic input-value contract before it
can compute anything, but that contract is not designed or implemented here.

Even a future real evaluator output remains advisory and pre-risk. It is not a
recommendation, not trade approval, not an execution intent, not an order
request, not portfolio-aware, not broker-aware, and not actionability by
itself. Score, direction, or confidence would require a separate design phase
and must remain advisory only if ever admitted.

This phase adds no production code, tests, runtime behavior, real evaluator,
signal computation, feature computation, strategy logic, ranking, priority,
signal-to-risk conversion, risk approval, execution intent creation,
execution-plan mutation, portfolio mutation, broker or Alpaca behavior, order
submission, scheduler/runtime behavior, persistence, live data ingestion, ML
training or inference, or LLM trading-path logic. Normal pytest remains
offline, credential-free, and safe.

Verification after Phase 27 Step 1:

```text
python -m pytest
634 passed, 4 skipped
```

## Phase 27 Step 2 Deterministic Signal Input Value Boundary Design

Phase 27 Step 2 is documentation-only. It adds:

```text
docs/design/phase27_signal_input_value_boundary.md
```

The new design defines the future deterministic signal input-value boundary
needed before any real evaluator can compute signals. It records the difference
between `SignalEvaluationInputSnapshot` and future input values:
`SignalEvaluationInputSnapshot` is reference metadata only, preserving
`snapshot_id`, UTC-aware `as_of`, `required_input_names`, and `source_ids`; it
does not carry actual observed market values, feature values, bar payloads,
quote payloads, or computed inputs.

A future input-value contract is described conceptually as a small immutable
contract for explicit deterministic observed values, observation timestamps,
source traceability, value type constraints, and no-lookahead validation
support. The design discusses possible value subjects such as market prices,
bar fields, quote fields, volume, separately promoted feature values, and
timestamped static metadata without defining a final production contract.

The design records candidate fields for a future contract, including input
name, observed value, `observed_at`, source id, optional symbol or instrument
identity, optional value type or unit metadata, and optional quality or status
metadata. These remain design candidates only.

Timestamp rules require future `observed_at` values to be UTC-aware, reject
naive and non-UTC datetimes, and support validation that every observation used
by an evaluator satisfies `observed_at <= evaluator as_of`. The design also
forbids hidden wall-clock reads, fetching newer data internally, and inference
from data unavailable at `as_of`.

The value representation questions remain open: whether values should be
`Decimal`, `int`, `str`, `bool`, or a constrained union; whether floats should
be forbidden or isolated; whether bars and quotes should be referenced by
domain objects or flattened; whether feature values need a separate feature
contract first; how missing values, units, currency, timeframe, and ordering
should be represented.

This phase adds no production code, tests, input-value implementation, real
evaluator, signal computation, feature computation, strategy logic, ranking,
priority, score, direction, confidence, actionability, signal-to-risk
conversion, risk approval, execution intent creation, execution-plan mutation,
portfolio mutation, broker or Alpaca behavior, order submission,
scheduler/runtime behavior, persistence, live data ingestion, ML training or
inference, or LLM trading-path logic. Normal pytest remains offline,
credential-free, and safe.

Verification after Phase 27 Step 2:

```text
python -m pytest
634 passed, 4 skipped
```

## Phase 27 Step 3 Minimal Signal Input Value Contract

Phase 27 Step 3 adds the first minimal signal input-value production contract:

```text
src/algotrader/signals/signal_input_value.py
```

The new `SignalInputValue` contract is a frozen, slotted dataclass with exactly
four fields:

```text
name
value
observed_at
source_id
```

It carries one explicit observed value with source and timestamp traceability.
It validates `observed_at` as UTC-aware using the deterministic time contract,
rejects naive and non-UTC datetimes, rejects empty or blank `name` and
`source_id`, preserves accepted string values exactly, preserves accepted
`observed_at` identity, and stores the value without computation or
interpretation.

The first value surface accepts deterministic scalar values only: `Decimal`,
`int`, `str`, and `bool`. Mutable values, tuples, floats, and `None` are not
part of this minimal contract. Optional unit, quality, symbol, and instrument
fields remain deferred.

`SignalInputValue` does not perform lookahead validation against evaluator
`as_of`; it has no `as_of` field. Lookahead validation belongs to a later
assembly or evaluator-input boundary.

Focused tests live in:

```text
tests/unit/test_signal_input_value.py
```

They prove the contract exists, exposes the exact field set, is frozen and
slotted, validates UTC-aware `observed_at`, rejects naive and non-UTC
datetimes, preserves timestamp identity and exact accepted strings, preserves
values without computation, accepts the deterministic scalar value set, rejects
unsupported or mutable values, exposes no signal output/scoring/direction/
confidence/actionability surface, exposes no risk/execution/order/broker/
portfolio/runtime/persistence/ML/LLM fields, imports no forbidden downstream or
external modules, and makes no hidden wall-clock, random, network,
filesystem-write, environment-variable, or broker calls.

This phase adds no real evaluator, signal computation, feature computation,
strategy logic, scoring, ranking, confidence/probability, signal direction,
actionability flags, signal-to-risk conversion, risk approval, execution intent
creation, execution-plan mutation, portfolio mutation, broker or Alpaca
behavior, order submission, scheduler/runtime behavior, persistence writes,
live data ingestion, network calls, ML training or inference, or LLM
trading-path logic. Normal pytest remains offline, credential-free, and safe.

Focused validation:

```text
python -m pytest tests/unit/test_signal_input_value.py
30 passed

python -m pytest tests/unit/test_dependency_direction.py
9 passed
```

The full suite is now:

```text
python -m pytest
664 passed, 4 skipped
```

## Phase 27 Step 4 Signal Input Value Traceability Hardening

Phase 27 Step 4 hardens `SignalInputValue` traceability with tests and
documentation only. No production source or runtime behavior changed.

`SignalInputValue` remains an immutable observed-value contract. It carries one
explicit observed scalar value with `name`, `observed_at`, and `source_id`
traceability. It does not compute, normalize, rank, score, infer direction,
recommend trades, approve risk, create execution intents, mutate execution
plans, access live data, route to brokers or Alpaca, submit orders, use
scheduler/runtime/persistence, run ML, or use LLMs in the trading path.

The hardened tests prove exact `name` string preservation, exact `source_id`
string preservation, exact `observed_at` identity preservation, exact
`Decimal`, `int`, `str`, and `bool` value preservation, and that `bool` remains
distinct from `int` even though both are supported scalar value types. Accepted
values are stored exactly without normalization, rounding, conversion, or
interpretation.

The tests also strengthen immutability and value-surface guarantees: the
contract is frozen, slotted, has no `__dict__`, fields cannot be reassigned,
mutable values are rejected, floats are rejected, arbitrary objects are
rejected, and `None` remains unsupported.

Timestamp coverage now explicitly proves UTC-aware `observed_at` is accepted,
naive and non-UTC timestamps are rejected, the contract does not compare to an
evaluator `as_of`, does not perform lookahead validation internally, and does
not call wall-clock APIs. Lookahead validation belongs to later assembly or
evaluator phases with an explicit `as_of`.

Surface and dependency tests now pin that `SignalInputValue` exposes no signal
output, score, probability, confidence, rank, priority, direction,
actionability, approval, risk, execution, order, broker, Alpaca, account,
position, fill, portfolio, cash, buying-power, scheduler, runtime, persistence,
database, cache, ML/model/prediction, LLM/agent/prompt/output, or evaluator
behavior. AST checks guard against hidden wall-clock, random, environment,
network/socket, filesystem-write, database/cache/persistence, broker SDK,
Alpaca SDK, ML, LLM, and agent dependencies.

Focused validation:

```text
python -m pytest tests/unit/test_signal_input_value.py
47 passed

python -m pytest tests/unit/test_dependency_direction.py
9 passed
```

The full suite is now:

```text
python -m pytest
681 passed, 4 skipped
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
- real execution-planning policy decisions beyond no-op pass-through and the
  max-intents cap
- accepted/rejected/skipped execution-planning policy logic beyond the
  max-intents cap
- accepted/rejected/skipped execution-planning decisions beyond the max-intents
  cap
- direct `ExecutionPlan` order/risk/status convenience fields
- execution-intent broker routing or adapter integration
- broker-facing request construction
- order submission
- client-order-id generation
- idempotency implementation
- batch cash reservation
- buying-power reservation
- same-symbol execution conflict handling
- duplicate or competing order policy implementation
- priority or ranking policy implementation
- research/backtesting outputs as direct trading logic
- notebooks or exploratory scripts in the deterministic core
- validated artifact metadata as signal generation
- validated artifact metadata as risk approval
- validated artifact persistence implementation
- validated signal definitions as live signal outputs
- validated signal definitions as execution decisions
- validated signal definitions as broker orders
- validated signal definitions as execution intents
- validated signal definitions as risk approvals
- signal evaluation input snapshots as signal computation
- signal evaluation input snapshots as live data access
- signal evaluation input snapshots as risk approvals
- signal evaluation input snapshots as execution intents or execution plans
- signal evaluation outputs as orders
- signal evaluation outputs as risk approvals
- signal evaluation outputs as execution intents or execution plans
- signal evaluator implementation beyond the minimal no-op metadata boundary
- real signal evaluator implementation
- evaluator protocol
- `SignalEvaluationResult` behavior beyond minimal advisory metadata
- no-op marker on `SignalEvaluationResult`
- signal evaluator registry
- signal computation from validated signal definitions
- system clock implementation
- signal input value collection or evaluator input bundle
- lookahead validation across input values and evaluator `as_of`
- SignalInputValue behavior beyond minimal observed scalar traceability
- feature computation
- strategy engine
- signal-evaluation-to-risk bridge
- input snapshot persistence implementation
- live data ingestion
- ML training implementation
- persistence writes
- audit logging writes
- LangGraph
- ML
- LLM trading-path logic

## Next Recommended Steps

Keep avoiding real Alpaca SDK work until explicitly approved.

Safe next tasks include:

- small deterministic screener polish with synthetic inputs only
- a small config cleanup audit
- documentation polish
- explicit research artifact contracts/types before any runtime wiring
- first real evaluator design as docs-only before any real evaluator behavior
- explicit future execution-planning policy decisions only after their config
  and result semantics are designed
- deeper broker contract tests around error paths and reconciliation boundaries
- further fake-only Alpaca contract coverage

Any future real SDK integration must be behind explicit opt-in safety gates,
paper-profile checks, credential redaction, skipped-by-default integration tests,
and no-network defaults for normal test runs.
