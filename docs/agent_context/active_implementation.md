# Active Implementation Checkpoint

## Current Baseline — V5.31A Closed-Hour Scheduling Semantics Repaired and Verified

- Checkpoint date: `2026-07-19`, America/New_York.
- Branch: `antigravity/v5.31a-deterministic-oos-scheduler`.
- Current committed HEAD: `426f81332864e345643bbd9f96f9b236a738bab7`.
- Sole implementation writer: Antigravity.
- The V5.31A scheduler timing repairs and safety hardness modifications are complete, locally verified, and pass the canonical sharded offline verifier.
- Independent review status: pending independent Claude re-review
- Push status: not pushed (do not push, do not open a pull request)
- Exactly one implementation writer may continue this checkout. Inspect branch, HEAD, status, staged and unstaged diffs before editing. Do not reset, clean, stash, restore, rebase, or switch branches during takeover.

## Implemented Contract

V5.31A provides a deterministic scheduled execution layer for tournament-v2 OOS accrual without active agents or polling loops:

- **Timing Semantics**: Hourly bar timestamps represent the **opening time** of the bar, not its completion/publication time (e.g. bar covering `20:00:00Z` to `21:00:00Z` is labeled `20:00:00Z`). It closes at `21:00:00Z` and is eligible with a 5-minute publication grace period at `21:05:00Z`.
- **Trigger Logic**: The scheduled task runs 5 minutes after every UTC hour boundary. Thus, a trigger at `21:05:00Z` schedules the prior hour's bar-open timestamp (`20:00:00Z`), not `21:00:00Z`.
- **Forming Bar Protection**: The scheduler strictly filters out any currently forming bar. A forming bar (at hour `HH:00` for a tick at `HH:MM`) will never be requested or dispatched.
- **Database Storage**: Uses schema `v5_31a_scheduler_schema_v2` with renamed columns to prevent timing ambiguity (`requested_start_bar_open`, `requested_end_bar_open`, `provider_as_of_boundary`, `accepted_frontier_bar_open`, `expected_frontier_bar_open`).
- **Subprocess Dispatch Mapping**: The real command dispatcher maps `--as-of` to `provider_as_of_boundary` (`requested_end_bar_open + 1 hour`).
- **Receipt Model**: Records explicit timing/boundary keys separately (`clock_time_utc`, `publication_grace_seconds`, `accepted_frontier_bar_open`, `requested_start_bar_open`, `requested_end_bar_open`, `provider_as_of_boundary`, `expected_frontier_bar_open`, `next_eligible_scheduler_time`). No-op receipts state that no post-frontier bar is eligible.
- **Stale Job and Failure Policy**: Stale RUNNING jobs (older than 15 minutes) are recovered to FAILED. FAILED/BLOCKED jobs never auto-retry. A subsequent distinct eligible window is not blocked, but overlapping windows cannot be silently skipped. Operator action is required to resolve historical failures.

## Verification Evidence

Credential/profile preflight remained safe:

- `APP_PROFILE=paper`: false.
- `ALPACA_API_KEY`, `ALPACA_API_SECRET_KEY`, `ALPACA_SECRET_KEY`, `APCA_API_KEY_ID`, and `APCA_API_SECRET_KEY`: absent.
- Network-test switches: false/absent.
- No credential value was printed.

Focused evidence from this exact working tree:

- Python Version: `3.13.2`
- Focused scheduler aggregate: `53 passed` (composed of: `test_crypto_tournament_v2_oos_scheduler.py` [23], `test_crypto_tournament_v2_oos_scheduler_task.py` [4], `test_crypto_tournament_v2_oos_scheduler_repairs.py` [8], `test_crypto_tournament_v2_forward_oos.py` [18])
- Safety aggregate: `63 passed, 1 skipped` (composed of: `test_dependency_direction.py`, `test_broker_mutation_surface_invariant.py`, `test_paper_integration_gate.py`, `test_default_pytest_network_guard.py`)
- Full canonical release gate: `.\scripts\verify_offline.ps1 -Full` (aggregate result: `tests:9527,passed:9522,skipped:5,failures:0,errors:0`)
- Verification execution outcome: PASS (offline, deterministic, credential-free, broker-free, network-free)
- Verified pre-commit source tree hash (staged repair code & tests, excluding active_implementation.md): `20d18096c8aa2d11ec631581879c0180224d34f5`

## Current Real Readiness

- The scheduler is disabled by default. No scheduled Windows tasks have been registered on the machine (Task Registered: False).
- Real command dispatcher remains disabled.
- Live-capital readiness is false.

## Implementation-Owned Files Staged for Commit

- `docs/OPERATOR_RUNBOOK.md`
- `docs/agent_context/active_implementation.md`
- `docs/design/crypto_tournament_v2_oos_scheduler_task.xml`
- `scripts/run_crypto_tournament_v2_oos_scheduler.ps1`
- `src/algotrader/orchestration/crypto_tournament_v2_oos_scheduler.py`
- `tests/unit/test_crypto_tournament_v2_oos_scheduler_task.py`
- `tests/unit/test_crypto_tournament_v2_oos_scheduler_repairs.py`

## Protected Dirty Work

- Preserve `docs/project_checkpoint.md` exactly as unrelated modified operator work.
- Preserve `docs/design/v5_20_3_crypto_frozen_state_reset_baseline.md` exactly as unrelated untracked operator work.
- Do not edit, stage, commit, reset, clean, stash, restore, rebase, or switch over either protected file.
- The frozen legacy producer remains byte-identical.

## Recommended Next Milestone

1. V5.31B — immutable strategy registry and frozen champion–challenger shadow cohort. Adapt the useful strategy-lifecycle concepts from Vibe-Trading while preserving algo_trader's stricter evidence and safety model.
