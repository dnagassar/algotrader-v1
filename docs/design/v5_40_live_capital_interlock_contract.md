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
