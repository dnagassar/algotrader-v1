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
- [`src/algotrader/execution/alpaca_sdk_client.py`](file:///C:/Users/danie/Desktop/algo_trader/src/algotrader/execution/alpaca_sdk_client.py): Requires valid paper profile configuration (`require_paper_profile`).

## Verification & AST Invariants

- Dedicated Stage 2 unit test suite [`tests/unit/test_stage2_live_market_data_refresh.py`](file:///C:/Users/danie/Desktop/algo_trader/tests/unit/test_stage2_live_market_data_refresh.py) proves:
  - Interlock preflight refusal when live signals or non-paper profiles exist.
  - Successful read-only market data intake under clean paper environment.
  - Zero forbidden broker order or mutation calls via AST source code scanning.
