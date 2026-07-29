# Active Implementation

## Ownership

- Writer: Codex orchestrator, sole writer for this working tree.
- Branch: `codex/v5.57-strategy-paper-sleeves`.
- Base HEAD: `49e4fdbe286a87b75b662b66059bd6cc7e86e0e9`, the
  committed V5.56 selectable RSI paper lane.
- V5.57 is a coherent local feature commit; no dirty-file owner remains after
  yield.
- The separate V5.51 worktree at
  `.claude/worktrees/v551-readonly-market-data-contract` was not modified.

## Takeover and stale-claim audit

- Takeover inspection found the V5.56 branch clean with empty staged,
  unstaged, and untracked sets.
- The inherited handoff correctly stated that concurrent SMA and RSI mutation
  was unsafe against one aggregate SPY position. Its branch and ownership
  section became stale after V5.57 branched from the clean V5.56 commit.
- Recent V5.55 and V5.56 work produced real operational capabilities: a
  secure unattended paper cycle and selectable RSI strategy. V5.57 therefore
  did not add another review packet, research artifact, or hardening-only
  milestone. It removes the remaining single-strategy operating constraint.

## New operational capability

The shared paper account now has durable strategy-owned virtual SPY quantity
sleeves for:

- `spy_sma_50_200_training_wheel`; and
- `spy_rsi_14_mean_reversion_paper`.

The broker remains authoritative for the physical paper position. Before
planning, its aggregate SPY quantity must exactly equal the sum of both
sleeves. The active strategy uses only its owned quantity for buy/hold/close
decisions, and a close cannot exceed that sleeve. This prevents either
strategy from closing the other's SPY exposure.

The SQLite sleeve ledger records generation, ownership, durable mutation
intent, session-order count, terminal status, and exact filled quantity. A
terminal fill must have positive filled quantity. Missing, ambiguous,
nonterminal, conflicting, or cross-sleeve evidence fails closed and leaves
later mutation blocked until reconciliation.

The no-submit readiness packet and second pass bind the strategy ID, sleeve
generation, active and aggregate quantities, broker-match result, and finite
caps. Strategy-specific client-order IDs remove SMA/RSI identity collision.
The canonical risk path supports a second sleeve entry only inside the
aggregate entry-exposure cap while still allowing an exposure-reducing close
up to the active sleeve's exact owned quantity.

Effective finite bounds are:

- one broker order per secure cycle;
- `$25.00` maximum entry-order notional;
- `$60.00` maximum aggregate marked SPY exposure for a new entry; and
- two sleeve order intents per UTC session day.

## Observable paper evidence

- One secure paper-only bootstrap opened the account-bound credential lease,
  observed the matched paper account, and assigned the existing aggregate SPY
  position to the SMA sleeve locally. The first wrapper receipt failed closed
  because the loop's true broker-match evidence was omitted from the operator
  rollup. No broker submit or mutation occurred.
- The rollup propagation defect was fixed and covered by a regression test.
- A subsequent real SMA cycle returned `healthy_no_action`, selected SMA,
  proved exact sleeve/broker equality, and performed no submit or mutation.
- A subsequent real RSI cycle returned `healthy_no_action`, selected RSI,
  proved the same exact aggregate equality, and performed no submit or
  mutation.
- An exact-value scan covered 454 generated secure-cycle and state files and
  found zero credential or account-value matches.

No credential value, account identifier, order identifier, quantity, price,
or raw broker payload is recorded in this handoff.

## Host task commissioning

Both exact checked-in least-privilege tasks are installed and `Ready`:

- SMA: weekdays at 09:31 ET with three 15-minute retries; next run observed
  `2026-07-30T09:31:00-04:00`.
- RSI: weekdays at 09:38 ET with three 15-minute retries; next run observed
  `2026-07-30T09:38:00-04:00`.

Both tasks use `IgnoreNew`, network-required execution, no catch-up, no
on-demand start, a ten-minute process limit, explicit strategy IDs, the same
runtime lease/order journal/sleeve ledger, and the finite caps above. The SMA
task retains its historical prior result; the new RSI task has not yet reached
its first scheduled trigger.

## Verification

- Default-test preflights found no paper profile, broker credential alias,
  network-test flag, or paper-integration flag loaded.
- Affected implementation and safety suites: 145 passed.
- Post-proof history/operator/secure regression suite: 44 passed.
- Repository offline verification: 109 safety guards passed.
- Final exact-node full suite:
  - 10,148 canonical nodes across 502 files;
  - collection equivalence passed;
  - execution equivalence passed;
  - 10,144 passed and 4 skipped;
  - zero failures, zero errors, and zero shard timeouts.
- `git diff --check` passed before final staging.

## Files

Execution and durable state:

- `src/algotrader/execution/strategy_sleeve_ledger.py`
- `src/algotrader/execution/paper_runtime_planning.py`
- `src/algotrader/execution/paper_autopilot_loop.py`
- `src/algotrader/execution/paper_autopilot_history.py`
- `src/algotrader/execution/paper_autopilot_operator.py`
- `src/algotrader/execution/secure_spy_paper_cycle.py`

Host operations and documentation:

- `scripts/run_secure_spy_paper_cycle.ps1`
- `scripts/register_secure_spy_paper_cycle_task.ps1`
- `docs/design/secure_spy_paper_cycle_task.xml`
- `docs/design/secure_spy_rsi_paper_cycle_task.xml`
- `docs/deterministic_core.md`
- `docs/OPERATOR_RUNBOOK.md`
- this sole mutable handoff.

Verification:

- `tests/unit/test_strategy_sleeve_ledger.py`
- `tests/unit/test_paper_runtime_planning.py`
- `tests/unit/test_paper_autopilot_loop.py`
- `tests/unit/test_paper_autopilot_history.py`
- `tests/unit/test_secure_spy_paper_cycle.py`

## Next action

Observe both first scheduled V5.57 cycles on `2026-07-30`. Require each task
to end in `healthy_no_action`, `paper_action_reconciled`, or
`revalidated_no_action`; exact sleeve/broker equality; no pending sleeve
intent; terminal broker and sleeve reconciliation after any paper submit; and
all live flags false. Stop on any mismatch rather than editing the sleeve
ledger or bypassing readiness.
