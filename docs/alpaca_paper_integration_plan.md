# Alpaca Paper Integration Plan

## Purpose

`AlpacaPaperBroker` currently exists only as an inert skeleton. This document defines the safe path toward a future Alpaca paper-trading integration without adding SDK dependencies, credentials, network calls, or runtime broker behavior yet.

The goal is to preserve the deterministic trading core while preparing a clear adapter boundary for a future paper broker.

## Current Broker Architecture

The current working broker is `LocalBroker`. It is the deterministic reference implementation for the system and uses the existing local paper execution simulator internally.

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
- avoid mutating local expected state for unfilled orders

## Testing Plan

Normal test runs must remain deterministic and offline.

Recommended test layers:

- Unit tests with a mocked Alpaca client.
- Contract-style tests using fake Alpaca account, position, and order responses.
- No-network tests by default.
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

The integration-test flag should be opt-in. Missing credentials should skip integration tests, not fail the full suite.

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
- Alpaca SDK dependency installation
- credentials
- websocket fills
- scheduler or runtime loop
- live trading
- LangGraph
- ML
- LLM logic in the trading path
- automatic order approval
- real broker connectivity during normal tests

## Recommended Implementation Sequence

Recommended future order:

1. Keep the small Alpaca configuration object offline and credential-safe.
2. Add Alpaca SDK dependency in an isolated change.
3. Create a thin Alpaca client adapter that can be replaced by fakes in tests.
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

## Success Criteria For The Current Safe Boundary

The current safe boundary is preserved when:

- this document exists
- configuration-only code remains offline and credential-safe
- no dependencies were added
- no credentials were added
- no network calls were introduced
- the deterministic core remains the source of truth
