# Alpaca Paper Integration Plan

## Purpose

`AlpacaPaperBroker` currently exists only as an inert skeleton. This document defines the safe path toward a future Alpaca paper-trading integration without adding SDK dependencies, credentials, network calls, or runtime broker behavior yet.

The goal is to preserve the deterministic trading core while preparing a clear adapter boundary for a future paper broker.

## Current Status

Current checkpoint after the offline pre-Phase-2 cleanup patch:

```text
216 passed, 1 skipped
```

The safe Alpaca preparation layers currently include:

- mocked Alpaca client boundary added
- pure fake-response translation helpers with pinned DTO return types added
- explicit translated-DTO to internal-model mapper added
- fake-only injected client adapter wiring added
- test-only injected adapter delegation added to `AlpacaPaperBroker`
- explicit pre-SDK broker safety contract tests added
- fake-only broker protocol integration coverage added for `AlpacaPaperBroker`
- shared broker contract subset added for `LocalBroker` and fake-adapter
  `AlpacaPaperBroker`
- repo-wide AST import safety coverage for production code added
- dynamic import and code-execution calls blocked by import safety coverage
- explicit `require_paper_profile()` safety gate added and tested
- bounded `alpaca-py>=0.43,<0.44` dependency declared
- file-scoped `AlpacaSdkClient` wrapper added
- import-safety allow-list permits `alpaca` only in the SDK wrapper
- `paper_integration` marker and default skip gate added for future opt-in tests
- paper URL invariant added to `require_paper_profile()`
- `paper_integration` gate behavior is covered by normal tests
- credential redaction coverage includes both Alpaca key fields
- SDK wrapper import remains lazy and does not load `alpaca` during normal tests
- default SDK factory construction is covered by an offline unit test
- duplicate order-id idempotency is covered by broker contract tests
- duplicate fake-adapter order IDs are rejected before a second fake client call
- no `alpaca-trade-api` dependency
- no credentials
- no network calls
- no broker implementation
- no real account calls
- no paper order submission
- `AlpacaPaperBroker` remains inert

## Current Broker Architecture

The current working broker is `LocalBroker` in `src/algotrader/execution/local_broker.py`. It is the deterministic reference implementation for the system and uses the existing local paper execution simulator internally.

Current state:

- `LocalBroker` keeps an in-memory `PortfolioState`.
- `LocalBroker` requires an approved `RiskVerdict` by default before submission.
- `LocalBroker` applies fills with `apply_fill()`.
- `LocalBroker` does not mutate cash or positions for unfilled limit orders.
- Broker contract tests define the expected broker behavior.
- `AlpacaPaperBroker` has broker-shaped methods but currently raises `BrokerNotImplementedError`.
- No real Alpaca SDK calls exist.
- No credentials are loaded.
- No network calls are made.

The deterministic safety rule remains:

```text
No LLM logic in risk, execution, signals, screener, portfolio, valuation, reconciliation, or feature calculation.
```

## Required Future Environment Variables

A future Alpaca paper integration will likely require environment or configuration values similar to:

```text
ALPACA_API_KEY
ALPACA_SECRET_KEY
ALPACA_PAPER_BASE_URL
APP_PROFILE=paper
```

These values are represented by a small offline configuration boundary for future Alpaca paper readiness checks. That boundary must not install the Alpaca SDK, instantiate clients, make network calls, or expose secret values in string output.

Credentials must never be committed to the repository.

## Current Config Boundary Status

The current app config API remains:

- `TradingConfig`
- `load_config`

These names are stable app-facing contracts used by existing imports, CLI behavior, and tests.

The Alpaca-specific config boundary is:

- `AlpacaPaperConfig`
- `AlpacaPaperConfig.from_env()`
- `validate_alpaca_paper_ready()`

`validate_alpaca_paper_ready()` is explicit and opt-in. Normal development config and normal `python -m pytest` runs remain credential-free and offline.

Future Alpaca work should extend the existing config model instead of replacing stable public config APIs.

`require_paper_profile()` now defines the explicit paper-profile gate future SDK
code must call before Alpaca-touching behavior. It does not create clients, read
environment variables, import Alpaca SDKs, or perform network calls.

## SDK Plan Preconditions

Before SDK work starts, `require_paper_profile()` must exist and be covered by
tests. Import-safety coverage must also block dynamic imports and
code-execution calls such as `importlib.import_module(...)`, `__import__(...)`,
`exec(...)`, and `eval(...)`.

The Phase 0 SDK plan remained documentation-only until Phase 1 was explicitly
approved. Phase 1 now declares the bounded SDK dependency and wrapper boundary,
but still adds no credentials, environment read, network call, or real
paper-account connectivity.

## Import-Safety Allow-List Strategy

When `alpaca` first becomes a legal production import, do not globally relax
`FORBIDDEN_IMPORT_ROOTS`. Instead, add a narrow allow-list mechanism to
`tests/unit/test_import_safety.py`.

The allow-list should permit exactly one future SDK wrapper file, likely:

```text
src/algotrader/execution/alpaca_sdk_client.py
```

No other production file may import `alpaca` or `alpaca_trade_api`. Phase 1's
first SDK PR must include both the new wrapper file and the import-safety
allow-list update. The safety perimeter must remain file-scoped, not repo-wide.

## Non-Negotiable Safety Rules

Every future Alpaca-touching SDK code path must call
`require_paper_profile(config)` before creating or using a real client.

Normal unit tests must never make real network calls. Real SDK tests must be
opt-in only, separately marked or skipped, and excluded from normal
`python -m pytest` runs unless a deliberate integration flag is present.

Credentials must never appear in `repr`, logs, fixtures, committed docs, test
output, exceptions, CLI output, or ledger records. Fake-only tests remain the
default safety and development path.

## Wrapper API Contract

The Phase 1 SDK wrapper must implement the existing
`algotrader.execution.alpaca_client.AlpacaClient` protocol.

It may expose only:

- `get_account()`
- `get_positions()`
- `submit_order(request)`

It must not expose broad SDK objects directly. It must be constructible only
from `AlpacaPaperConfig`, and its constructor must call
`require_paper_profile(config)` before creating or using any SDK client.

The wrapper must remain compatible with the existing `AlpacaClientAdapter`.
Replacing the fake client with the future wrapper must not require broker-side
changes.

## Config Compatibility Rule

Future Alpaca integration must preserve existing public APIs unless the same change intentionally migrates all callers and tests.

Stable app contracts include config imports and fields used by the CLI, tests, and deterministic core. If a future change needs to rename, remove, or reshape one of those contracts, that migration should be deliberate, documented, and covered by updated tests in the same change.

The safe default is:

```text
extend existing app contracts; do not replace them
```

## Compatibility Shim Removal Schedule

`src/algotrader/execution/fake_broker.py` remains in place for now as a
compatibility shim that re-exports `LocalBroker`.

Its removal is pinned to a future explicit milestone: after the first explicitly
approved, gated, read-only paper SDK path exists and the compatibility path is
no longer needed. It must not be removed as part of pre-SDK cleanup.

## Regression Lesson

The first Alpaca config boundary repair loop caught an import regression caused by breaking the expected `TradingConfig` and `load_config` API. Follow-up CLI failures also showed that stable fields such as profile, log level, data directory, starting cash, and paper exchange are part of the existing config contract.

Future changes should treat those app-facing contracts as compatibility surfaces. Alpaca-specific settings should be added alongside them, not in place of them.

## Current Mocked Client Boundary Status

A small offline Alpaca client boundary exists for future paper broker work. It defines the future shape for account, position, and order-submission behavior without requiring the real Alpaca SDK.

The boundary includes typed request and response structures plus a minimal protocol for:

- `get_account()`
- `get_positions()`
- `submit_order(...)`

The boundary is intentionally internal and inert. It does not import `alpaca-py`, instantiate a real Alpaca client, load credentials, or make network calls.

Current fake-client tests prove that account-like, position-like, and order-submission-like data can be exercised without credentials or network access. This gives future `AlpacaPaperBroker` work a typed adapter target before the SDK wrapper is used against real Alpaca.

This matters because future adapter work can first translate fake Alpaca-like responses into internal models such as `Account`, `Position`, and `BrokerOrderResult`. That translation can be tested deterministically before touching real Alpaca.

Normal `python -m pytest` runs must remain offline, credential-free, and deterministic. Real SDK or network integration can be added later only behind explicit flags, paper-profile checks, and safety gates.

## Current Translation Layer Status

Pure Alpaca response translation helpers exist for fake Alpaca-like responses. They translate dict or dataclass-style inputs into internal account, position, and broker-result-like models.

Current translation helpers:

- `translate_alpaca_account(...)`
- `translate_alpaca_position(...)`
- `translate_alpaca_order_result(...)`

These helpers are deterministic and offline. They do not import `alpaca-py`, instantiate a client, read credentials, or make network calls.

This layer matters because future `AlpacaPaperBroker` work can first prove response translation against fake Alpaca-like payloads. Account, position, accepted-order, and rejected-order behavior can be mapped into internal models before touching real Alpaca SDK objects or paper-account connectivity.

## Current Fake-Only Adapter Wiring Status

A thin fake-only adapter layer exists between an injected Alpaca-like client and the pure translation helpers.

Current adapter methods:

- `get_account()`
- `list_positions()`
- `submit_order(...)`

The adapter uses dependency injection only. It does not create a real Alpaca client, import `alpaca-py`, read environment variables, read credentials, or make network calls.

This layer proves that future broker work can call a client boundary, receive fake Alpaca-like responses, and translate them into internal models. It is not a broker implementation. `AlpacaPaperBroker` remains inert until a later explicit implementation phase.

The fake-only adapter also rejects duplicate `client_order_id` values locally.
That prevents duplicate fake submissions before any future real SDK integration
exists.

Shared deterministic fake Alpaca clients now live in `tests/fakes/alpaca.py` so
adapter, broker-delegation, safety-contract, and fake-protocol tests exercise
the same fake response shapes.

## Current Translation And Mapping Boundary

The pre-SDK response path is now explicit:

```text
fake Alpaca response
  -> TranslatedAlpaca DTO
  -> explicit mapper
  -> internal domain/broker model
```

Translator return types are pinned:

- `translate_alpaca_account(...) -> TranslatedAlpacaAccount`
- `translate_alpaca_position(...) -> TranslatedAlpacaPosition`
- `translate_alpaca_order_result(...) -> TranslatedAlpacaOrderResult`

The translator no longer performs dynamic model resolution, module probing, constructor reflection, or fallback construction of internal models.

Internal model conversion is handled by direct mapper functions:

- `map_translated_account_to_account(...)`
- `map_translated_position_to_position(...)`
- `map_translated_order_result_to_broker_result(...)`

This keeps fake Alpaca parsing separate from internal domain model construction, making the adapter boundary easier to test before any real SDK integration.

## Current AlpacaPaperBroker Delegation Status

`AlpacaPaperBroker` remains inert by default. When constructed without an injected adapter, operational methods still raise `BrokerNotImplementedError`.

For tests only, `AlpacaPaperBroker` can accept an injected fake adapter and delegate:

- `get_account()`
- `get_positions()` / `list_positions()`
- `submit_order(...)`

The injected adapter path allows broker -> adapter -> translator behavior to be tested using fake Alpaca-like responses. This is still not real Alpaca integration. The broker does not create a real client, import `alpaca-py`, read environment variables, read credentials, make network calls, or connect to a paper account.

Real SDK and paper-account connectivity remain future work behind explicit safety gates.

## Current Pre-SDK Safety Contract

The current `AlpacaPaperBroker` safety contract is locked down by explicit tests.

The tests prove:

- `AlpacaPaperBroker` remains inert by default.
- operational methods without an injected adapter raise `BrokerNotImplementedError`.
- importing and constructing the broker does not require `alpaca-py`.
- constructing the broker does not require credentials.
- constructing the broker does not read environment variables.
- broker tests do not make network calls.
- no real client is created internally.
- adapter or client behavior must be injected explicitly for operational behavior.
- the injected fake adapter path can return account, position, accepted-order, and rejected-order results.

This is the required baseline before future real SDK work. Any real Alpaca SDK or paper-account connectivity must be added later behind explicit opt-in flags, paper-profile checks, credential safety checks, and no-network defaults for normal tests.

## Current Fake-Only Broker Protocol Coverage

`AlpacaPaperBroker` also has fake-only protocol coverage for the supported pre-SDK broker-facing behavior.

The tests prove that an injected fake adapter can support:

- account retrieval
- position retrieval
- accepted deterministic order submission using the canonical broker signature
- rejected deterministic order submission using the canonical broker signature
- missing risk approval rejection
- rejected risk verdict handling
- duplicate order ID rejection without a second fake client call
- clear adapter/client failure propagation
- internal `Account`, `Position`, and `BrokerOrderResult` compatibility

These tests still use fake Alpaca-like responses only. They do not create a real client, read credentials, read environment variables, import `alpaca-py`, make network calls, or connect to a paper account.

The supported fake-only path now follows the existing broker-facing submission shape:

```text
submit_order(
  order: ProposedOrder,
  quote: Quote,
  risk_verdict: RiskVerdict | None = None,
  order_id: str | None = None,
) -> BrokerOrderResult
```

`AlpacaPaperBroker` remains inert by default. The injected fake adapter remains the only operational path.
Its fake-only broker-facing path follows the same duplicate order-id expectation
as the deterministic broker contract: the first fixed `order_id` can be
accepted, and a second submission with the same `order_id` is rejected with
`duplicate_order_id` before another fake client call.

## Future AlpacaPaperBroker Responsibilities

A future `AlpacaPaperBroker` implementation must eventually provide the same broker-facing behavior as the deterministic broker boundary, while keeping Alpaca-specific details isolated inside the adapter.

Expected responsibilities:

- Implement `submit_order(...)`.
- Implement `get_account()`.
- Implement `get_positions()`.
- Translate internal `ProposedOrder` values into Alpaca-compatible order requests.
- Translate Alpaca account responses back into the internal `Account` model.
- Translate Alpaca position responses back into internal `Position` models.
- Return internal broker result models instead of leaking Alpaca SDK response objects through the core.
- Fail safely on broker, API, network, validation, timeout, or authentication errors.
- Preserve deterministic supplied order IDs where the external API allows it.
- Never bypass `RiskEngine`.
- Never approve, size, transform, or submit orders using LLM logic.

The adapter should be a boundary around Alpaca, not a new source of trading decisions.

## Broker Contract Alignment

The existing broker contract tests are the compatibility target for future broker implementations.

Future `AlpacaPaperBroker` work should either:

- satisfy the existing broker contract tests through mocked or fake Alpaca responses, or
- intentionally adapt the contract where real broker behavior cannot exactly match `LocalBroker`.

Any intentional contract difference should be documented before implementation. The default expectation is that `AlpacaPaperBroker` follows the same core broker interface as `LocalBroker`.

Important contract behaviors to preserve:

- expose `get_account()`
- expose `get_positions()`
- refuse submission without required risk approval
- refuse submission with rejected `RiskVerdict`
- accept approved orders
- return a `BrokerOrderResult`
- preserve deterministic supplied order IDs where applicable
- reject duplicate supplied order IDs before duplicate fills, local mutations,
  or duplicate fake client calls
- avoid mutating local expected state for unfilled orders

## Testing Plan

Normal test runs must remain deterministic and offline.

Recommended test layers:

- Unit tests with a mocked Alpaca client.
- Contract-style tests using fake Alpaca account, position, and order responses.
- No-network tests by default.
- Existing shared broker contracts continue to run against fakes.
- Opt-in integration tests are separately marked and skipped by default.
- No network modules should appear outside an explicitly allowed future SDK
  boundary.
- Error-path tests for rejected orders, API failures, authentication failures, malformed responses, and timeouts.
- Optional integration tests only when credentials are explicitly provided.
- Optional integration tests skipped unless a deliberate environment flag is enabled.
- Normal `python -m pytest` must never require real Alpaca credentials.
- Normal `python -m pytest` must never make network calls.

Suggested future test controls:

```text
ALPACA_API_KEY
ALPACA_SECRET_KEY
ALPACA_PAPER_BASE_URL
APP_PROFILE=paper
RUN_ALPACA_PAPER_INTEGRATION_TESTS=1
```

Real paper integration tests must use the pytest marker `paper_integration`.
A future `tests/conftest.py` skip rule must skip all `paper_integration` tests
unless all of these are true:

- `RUN_ALPACA_PAPER_INTEGRATION_TESTS=1`
- `APP_PROFILE=paper`
- required `ALPACA_*` credential/config environment values are non-empty

Normal `python -m pytest` must never run paper integration tests. CI must not
set `RUN_ALPACA_PAPER_INTEGRATION_TESTS`; the flag is intended only for an
operator's local machine. Missing credentials must skip integration tests, not
fail normal test runs.

## Credential Redaction Surface Test

Phase 1's first SDK PR must add a redaction test using a recognizable fake
secret such as:

```text
sensitive-test-api-key-NEVER-LOG
```

The test must assert that the literal secret never appears in:

- `repr(...)`
- `str(...)`
- expected exception messages
- logs
- CLI output, if Phase 1 touches CLI
- ledger records, if Phase 1 touches ledger
- captured test output

The wrapper must never serialize or log any `AlpacaPaperConfig` field marked
`repr=False`. Credential redaction must be proven by tests, not only promised
in prose.

## Safety Gates Before First Real API Call

Before any real Alpaca paper API call is added or enabled, confirm:

- all current tests are passing
- broker contract tests are still green
- Alpaca SDK usage is isolated behind the broker adapter
- credentials are loaded only from environment or explicit local configuration
- no credentials are committed
- no credentials are printed in logs, exceptions, CLI output, or ledger events
- the application is running in an explicit paper profile
- live trading is unavailable
- real network tests are skipped unless explicitly enabled
- order submission still requires `RiskEngine` approval
- mocked tests cover success, rejection, and broker/API failure paths
- reconciliation behavior is defined before trusting broker-reported state
- ledger behavior is defined before recording external broker events

The first real API call should be read-only if possible, such as `get_account()` against a paper account. Order submission should come later, after mocked coverage and reconciliation expectations are in place.

## Phased SDK Integration Plan

Phase 0: Documentation-only plan. No SDK dependency, no `pyproject.toml`
change, no runtime code, no credentials, and no network behavior.

Phase 1: Add the SDK dependency and a tiny client wrapper. The dependency must
be pinned with both lower and upper bounds. The wrapper must require an
`AlpacaPaperConfig`, call `require_paper_profile(config)` in its constructor
before any real client is created or used, redact configuration in all output,
and avoid any default network call. Tests in this phase should use fake or
mocked SDK objects only.

Phase 1 status: the wrapper boundary now exists, but normal tests still use
fakes only. No real paper-account call, paper order submission, websocket,
scheduler, runtime loop, or broker runtime selection has been added.

Phase 1 definition of done:

- the 198 existing tests still pass
- import-safety allow-list passes and remains file-scoped
- credential-redaction surface test passes
- network-isolation test proves wrapper construction does not trigger a network
  call
- no broker order-submission behavior is added
- no `paper_integration` tests run in normal `python -m pytest`

Phase 2: Add an opt-in read-only paper account smoke test. It must be skipped
unless an explicit integration flag is present, must not run in normal
`python -m pytest`, and must not print or snapshot credentials.

Phase 3: Add read-only account and positions mapping through the existing
translator and mapper boundary. This phase may exercise real SDK response
shapes only behind opt-in controls. There is still no order submission.

Phase 4: Add paper order submission only after read-only paths are stable. The
implementation must preserve the canonical broker signature, continue requiring
pre-trade risk approval, preserve deterministic order-id/idempotency behavior,
return internal `BrokerOrderResult` values, and remain gated and opt-in.

Phase 5: Consider deprecating or removing `fake_broker.py` only after the first
explicitly approved, gated, read-only paper SDK path exists and the
compatibility shim is no longer needed.

## Reconciliation Plan

Future real broker integration will introduce two separate views of state:

```text
local expected state
broker-reported state
```

The local reconciliation layer should compare these views and report differences clearly.

Future Alpaca reconciliation should check:

- cash mismatch
- missing expected position
- unexpected broker position
- position quantity mismatch
- optional quote-based valuation mismatch
- pending or partially filled orders when those states are introduced

The system should not silently trust broker-reported state or silently overwrite local expected state. Differences should be reported first, then handled by explicit policy.

## Future Ledger Behavior

`JsonlLedger` and `InMemoryLedger` already provide local event recording. Future Alpaca integration should keep broker-event recording structured and deterministic.

Potential future events:

- order submitted to Alpaca paper
- order accepted by broker
- order rejected by broker
- order filled
- order partially filled
- order canceled
- broker account snapshot checked
- broker positions snapshot checked
- reconciliation checked

Ledger records should avoid secrets and raw credentials. If raw Alpaca responses are useful for debugging, store only sanitized fields needed for traceability.

## Explicit Exclusions

This plan does not implement or enable:

- real Alpaca API calls
- `alpaca-trade-api` or unrelated SDK dependencies
- real credentials
- broker implementation
- websocket fills
- scheduler or runtime loop
- automated execution loop
- live trading
- LangGraph
- LangChain
- OpenAI
- Anthropic
- ML
- LLM logic in the trading path
- automatic order approval
- options, margin, or short-selling expansion
- real broker connectivity during normal tests

## Next Future SDK Code Patch Proposal

The next future SDK code patch should stay isolated and boring:

- keep the SDK dependency and wrapper isolated
- keep requiring `AlpacaPaperConfig` in the wrapper constructor
- keep calling `require_paper_profile(config)` immediately before creating or
  using any real client
- make no default network call during import or construction tests
- include a network-isolation test proving wrapper construction does not make a
  network call
- keep normal tests fake-only or mocked
- avoid changing broker submission behavior
- avoid touching runtime loops, schedulers, order sizing, risk, portfolio,
  valuation, reconciliation, or ledger behavior

That patch should prove the wrapper can be imported, constructed with validated
paper config, and tested with fake or mocked SDK objects before any real account
connectivity is attempted.

## Recommended Implementation Sequence

This checklist is subordinate to the canonical Phase 0-5 plan above.
Recommended future order within those phases:

1. Keep the small Alpaca configuration object offline and credential-safe.
2. Keep the Alpaca SDK dependency isolated to the wrapper boundary.
3. Keep the thin Alpaca client adapter replaceable by fakes in tests.
4. Add mocked client tests for account-response translation.
5. Implement `get_account()` using mocked responses only.
6. Add mocked client tests for position-response translation.
7. Implement `get_positions()` using mocked responses only.
8. Add mocked client tests for order-request translation and broker error handling.
9. Implement `submit_order()` using mocked responses only.
10. Run broker contract tests against fake Alpaca responses.
11. Add optional paper integration tests behind an explicit environment flag.
12. Start with read-only paper-account connectivity.
13. Only after read-only connectivity is stable, consider paper order submission.

At each phase, normal tests should remain deterministic, offline, and credential-free.

## Rollback Criteria

Stop and revert or split the patch if any of the following occur:

- credentials could appear in logs, repr output, fixtures, docs, exceptions,
  test output, CLI output, or ledger records
- normal `python -m pytest` attempts a network call
- import-safety fails or forbidden network/LLM imports leak into production code
- real SDK behavior bypasses the translator and mapper boundary
- order submission bypasses risk approval, canonical broker result shape, or
  duplicate order-id/idempotency expectations
- SDK setup creates clients or touches Alpaca before `require_paper_profile()`
  has passed

## Success Criteria For The Current Safe Boundary

The current safe boundary is preserved when:

- this document exists
- configuration-only code remains offline and credential-safe
- no dependencies were added
- no credentials were added
- no network calls were introduced
- the deterministic core remains the source of truth
