# V5.40 Live-Capital Interlock Contract

## Purpose

The live-capital interlock is the single structural choke-point every autonomous broker-touching action must pass through before execution. It enforces the paper-only repository policy at runtime by requiring a pinned paper profile (`APP_PROFILE=paper`) and paper broker endpoint while failing closed on any live signal detected in the environment.

This interlock bridges the operator's standing charter limits and the runtime code path: autonomous execution cannot reach a live endpoint, submit a live order, or execute under a live profile while this guard stands in front of it.

## Non-Negotiable Safety Contract

1. **Paper-Only Endpoint & Profile**:
   - `APP_PROFILE` must explicitly equal `"paper"`. Any missing, default (`dev`), or live (`live`) profile is refused.
   - The resolved broker base URL must classify strictly as a paper endpoint containing `"paper"` (e.g. `https://paper-api.alpaca.markets`). Any endpoint containing `api.alpaca.markets` without the paper marker is classified as `live` and refused.

2. **Fail-Closed Live Signal Detection**:
   - Environment variables explicitly enabling live trading (`ALGO_TRADER_ALLOW_LIVE`, `ALGO_TRADER_ALLOW_LIVE_TRADING`, `ALLOW_LIVE_TRADING`, `ENABLE_LIVE_TRADING`, `LIVE_TRADING_ENABLED`) cause immediate refusal if set truthy.
   - Any environment variable pointing to the live Alpaca host without the paper marker triggers immediate refusal (`live_signals` records the variable *name* only).

3. **Zero Credential Exposure & Zero External Side Effects**:
   - Evaluates environment variable presence and URL shape only. Never reads, echoes, logs, or returns credential values.
   - Performs no network request, opens no socket, imports no broker SDK, and executes no order, mutation, or live action.
   - `live_authorized` is permanently fixed to `False`.
   - `to_dict()` output fixes `submitted`, `mutated`, `broker_action_performed`, `network_access_attempted`, and `credential_access_attempted` to `False`.

4. **Composition & Defense-in-Depth**:
   - Composes existing boundary check `algotrader.config.require_paper_profile`. Any config validation disagreement produces a explicit blocker (`config_paper_boundary_rejected`).

5. **Secure-Provider Callers (amendment)**:
   - The V5.35 secure dispatcher deliberately strips profile and credential environment variables from the child and passes its validated paper profile and endpoints as explicit non-secret arguments. Deriving the profile solely from that stripped environment made the interlock refuse a legitimate read-only path as `app_profile_not_paper:dev`.
   - `crypto_history_refresh_adapter` therefore builds a non-secret interlock view that layers the explicit `app_profile` and `paper_endpoint` arguments in **only where the environment does not already supply them**, so an ambient live signal can never be masked by an argument.
   - Before opening a credential lease it refuses any profile, endpoint, or live-enable conflict. Credential *presence* is the only condition deferred, because the lease supplies those values later.
   - Inside the lease callback the resolved credentials are bound to a temporary in-memory view so the complete canonical check runs again immediately before the read-only HTTP opener.
   - A refusal must leave both the provider open count and the HTTP call count at zero. This path grants no broker mutation and no live-capital authority.
   - Ported to `main` from `3818224` on the `claude/v5.42-stage3-self-refresh` lane.

## API and Module Surface

- **Module**: `src/algotrader/execution/live_capital_interlock.py`
- **CLI Subcommand**: `python -m algotrader.cli paper-boundary-check [--format {text,json}]`
- **Functions**:
  - `evaluate_live_capital_interlock(env: Mapping[str, str] | None = None) -> LiveCapitalInterlockVerdict`: Evaluates environment and returns a structured verdict without raising.
  - `require_live_capital_interlock(env: Mapping[str, str] | None = None) -> LiveCapitalInterlockVerdict`: Returns the verdict if `paper_boundary_ok` is `True`; raises `LiveCapitalGateError` otherwise.

## Verdict Structure (`LiveCapitalInterlockVerdict`)

| Field | Type | Description |
| :--- | :--- | :--- |
| `paper_boundary_ok` | `bool` | `True` only if profile is paper, endpoint is paper, and no live signals or blockers exist. |
| `app_profile` | `str` | Name of `APP_PROFILE` (e.g. `"paper"`, `"dev"`, `"unset"`). |
| `profile_is_paper` | `bool` | `True` if `app_profile == "paper"`. |
| `endpoint_class` | `str` | Endpoint classification (`"paper"`, `"live"`, or `"unknown"`). |
| `paper_endpoint_ok` | `bool` | `True` if endpoint is classified as `"paper"`. |
| `expected_paper_account_present` | `bool` | `True` if `EXPECTED_PAPER_ACCOUNT_ID` variable is set. |
| `live_signals` | `tuple[str, ...]` | List of variable names where live signals were detected. |
| `blockers` | `tuple[str, ...]` | List of reasons blocking paper boundary approval. |
| `live_authorized` | `bool` | **Always `False`**. |

## CLI Exit Codes

- `0` — `paper_boundary_ok` is `True` (paper boundary satisfied).
- `1` — `paper_boundary_ok` is `False` (refused fail-closed).

## Verification & AST Constraints

- Unit test suite [`tests/unit/test_live_capital_interlock.py`](file:///C:/Users/danie/Desktop/algo_trader/.claude/worktrees/algo-trader-autonomy-bd3c0a/tests/unit/test_live_capital_interlock.py) verifies:
  - Clean paper environment approval.
  - Refusal under live profile, dev profile, live base URLs, live enable flags, or non-paper endpoints.
  - Secret safety (credential values are never leaked in string representations or dictionary output).
  - Source AST scan proving zero forbidden network/broker imports (`requests`, `httpx`, `aiohttp`, `alpaca`, `socket`, `ssl`, `urllib`) and zero broker mutation calls.
