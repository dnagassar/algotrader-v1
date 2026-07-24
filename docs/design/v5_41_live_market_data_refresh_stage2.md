# V5.41 Stage 2 — Live Market Data Refresh Contract

## Purpose

Stage 2 enables read-only live market data intake and refresh (crypto OHLC historical bars, paper account observations) under explicit operator authorization while remaining strictly behind the V5.40 Live-Capital Interlock.

This stage allows autonomous and operator-initiated market data refresh loops to pull fresh price data from paper/data endpoints without exposing the system to live trading or order execution risks.

## Non-Negotiable Safety Contract

1. **Strict Read-Only Enforcement**:
   - Market data intake is limited strictly to read-only endpoints (`data.alpaca.markets`, `paper-api.alpaca.markets`).
   - Zero order placement (`submit_order`), zero order replacement (`replace_order`), zero order cancellation (`cancel_order`), and zero position liquidation (`close_position`, `liquidate`).

2. **Mandatory Live-Capital Interlock Composition**:
   - Every market data refresh invocation (`crypto_history_refresh_adapter.py`, `crypto_read_only_paper_observation_adapter.py`, `v535_unattended_readonly.py`) MUST evaluate `require_live_capital_interlock()` / `evaluate_live_capital_interlock()`.
   - Preflight immediately refuses fail-closed if:
     - `APP_PROFILE` is not `"paper"`.
     - Endpoint is non-paper or classified as `"live"`.
     - Explicit live signals (`ALLOW_LIVE_TRADING`, etc.) or live host URLs (`api.alpaca.markets`) exist in the environment.

3. **Zero Credential Exposure**:
   - Evaluates boolean credential presence without echoing, printing, logging, or writing credential values.
   - All emitted audit payloads fix `live_authorized`, `submitted`, `mutated`, and `broker_action_performed` to `False`.

## Seam Integrations

- [`src/algotrader/execution/crypto_history_refresh_adapter.py`](file:///C:/Users/danie/Desktop/algo_trader/src/algotrader/execution/crypto_history_refresh_adapter.py): Composes `require_live_capital_interlock` before `_run_market_data_fetch_mode`.
- [`src/algotrader/execution/crypto_read_only_paper_observation_adapter.py`](file:///C:/Users/danie/Desktop/algo_trader/src/algotrader/execution/crypto_read_only_paper_observation_adapter.py): Composes `evaluate_live_capital_interlock` in `validate_preflight_gates`.
- [`src/algotrader/execution/alpaca_sdk_client.py`](file:///C:/Users/danie/Desktop/algo_trader/src/algotrader/execution/alpaca_sdk_client.py): Requires valid paper profile configuration (`require_paper_profile`) at construction, and — completed in the V5.41a independent-review remediation — calls `require_live_capital_interlock(os.environ)` at the top of both real network factories (`_create_trading_client`, `_create_crypto_data_client`) so every live Alpaca client construction fails closed on any live signal before alpaca-py is imported. Injected mock clients/factories (tests) bypass the real factories and are unaffected.

## V5.41a Independent-Review Remediation

An orchestrator review of the merged V5.41 found `alpaca_sdk_client.py` importing `require_live_capital_interlock` (and `os`) without calling them — the SDK-seam interlock was intended but left unwired. V5.41a completes it: the interlock is now enforced inside `_create_trading_client` and `_create_crypto_data_client`, guarding exactly the real broker-connection seams while leaving mock-injecting tests untouched. Tests: `test_alpaca_sdk_client.py` adds `test_create_trading_client_enforces_live_capital_interlock`, `test_create_crypto_data_client_enforces_live_capital_interlock`, and `test_create_trading_client_refuses_when_profile_not_paper`; the two existing default-factory construction tests now set a paper execution env first.

## Verification & AST Invariants

- Dedicated Stage 2 unit test suite [`tests/unit/test_stage2_live_market_data_refresh.py`](file:///C:/Users/danie/Desktop/algo_trader/tests/unit/test_stage2_live_market_data_refresh.py) proves:
  - Interlock preflight refusal when live signals or non-paper profiles exist.
  - Successful read-only market data intake under clean paper environment.
  - Zero forbidden broker order or mutation calls via AST source code scanning.
