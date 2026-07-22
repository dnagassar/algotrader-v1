# V5.34 Repair Cycle 1 — Candidate Comparison and Synthesis Record

Owner-led single repair cycle on `relay/v5.34-readiness-recovery` (base `7ad6120`), governed by
the frozen contract in `v5_34_acceptance_contract.md`. Candidates compared semantically, per
file, against AC1–AC11. Neither candidate's history was merged; selected changes are reproduced
as a new commit. Both candidates remain preserved exactly as found
(`3495dd8` + staged WIP in `antigravity-current`; `50cb567` in `claude-current`).

## Per-surface decisions

| Surface | Selected | Reason |
|---|---|---|
| `crypto_read_only_paper_observation_adapter.py` | Claude | Both remove the identity-derived fingerprint identically (AC3). Claude additionally restores matched-pair credential resolution (no cross-family key/secret mixing) and adds the `expected_account_configured` presence boolean — both within AC3. |
| Wrapper scripts (×3) | Claude | AC3 requires removal of plaintext `.env` loading, the hard-coded primary-checkout fallback, and secret alias duplication. Antigravity removes only the fallback and keeps plaintext loading + alias duplication. Claude removes all three, adds `-InvocationSource` (needed by AC9), and truthfully classifies unattended activation as `blocked_unattended_secret_loading`. |
| `crypto_paper_account_cleanup.py` | Claude | AC7 forbids bulk account-wide mutation. Antigravity retains bulk `cancel_orders()`/`close_all_positions()` behind a blunt pending-close heuristic, reduces reconciliation to a single read, and imports `_write_receipt_atomically` from `algotrader.cli` inside an execution module (dependency-direction risk). Claude implements exact-order `cancel_order_by_id` / exact-symbol `close_position`, bounded attempts, per-operation classification, read-based reconciliation (10 bounded reads), and duplicate-close prevention. |
| `test_broker_mutation_surface_invariant.py` | Claude | Replaces the base's bulk `close_all_positions` registration with the two exact-scoped registered mutations (AC7/AC8). |
| `v534_burn_in_status.py` | Claude | AC6 requires hash-validated receipt admission — Claude validates `canonical_receipt_sha256` per receipt; Antigravity filters by schema string only. Claude's scheduler query is injectable for deterministic offline tests and yields truthful blocked classifications with next actions; no execution→cli import. |
| `v534_unattended_cycle.py` | Claude | AC1: Antigravity swaps the reversed positional unpack but stays positional; Claude binds receipts by schema. AC5: Antigravity's replay receipt **overwrites** the original window receipt (breaks write-once); Claude emits a separate `duplicate_window_no_op` receipt referencing the original path and hash. AC2/AC4 satisfied by both; Claude's file is selected as the coherent unit. |
| `crypto_tournament_v2_oos_scheduler.py` | Claude | Byte-identical revert to the accepted baseline `9d40560` blob (verified by hash `4239077…`), removing V5.34's secret-alias duplication into child environments and raw subprocess output in receipts (AC3). Not new behavior. |
| `cli.py` | Claude | `--invocation-source` plumb-through (AC9) and truthful exit-code set from `COMPLETED_CYCLE_CLASSIFICATIONS` (AC6/AC5). |
| `crypto_tournament_v2_oos_scheduler_task.xml` + task contract test | Claude | Aligns XML, wrapper, and contract test on one invocation path with `-InvocationSource scheduled` (AC9). No task registration or enabling. |
| V5.34 test suite | Claude | Expands 4 thin tests to full AC coverage, including the real-executor 24-cycle persistent-state continuity test with restart (AC10) and regression tests rejecting identity-derived values (AC3). |

## Rejected

- **Antigravity `3495dd8` code changes** — per-surface reasons above; no surface was stronger
  than the selected alternative.
- **Antigravity `tests/unit/test_v534r_contract_repairs.py`** — bound to the rejected
  candidate's APIs (its status-module signature, cycles-root layout, and classification
  vocabulary); would not compile against the selected implementation. Equivalent coverage
  exists in the selected suite.
- **Antigravity staged WIP** (typing import + checkpoint doc rewrite) — incomplete follow-on
  work; preserved untouched in its worktree.
- **Both candidates' `docs/agent_context/active_implementation.md` versions** — superseded by
  the relay-lane checkpoint convention (human view generated from `.agent_relay/`).

## Explicitly not done in this cycle

No scheduled task registered/enabled; no broker or network call; no order submitted or
canceled; no paper exposure mutated; SPY exposure and the scheduler `Ready`→`Disabled`
anomaly remain outside the repair (neither blocks an AC — AC9 is offline-verifiable and
AC7 is exercised only under tests).
