# Active Implementation

## Ownership

- Writer: Codex orchestrator, sole writer for this working tree.
- Branch: `codex/v5.54-spy-decision-time-shadow`.
- Base HEAD: `5c14053e33c96d21246708c2b876a1af56626b03`, the clean V5.53
  integration commit.
- Dirty-file owner before the V5.54 commit: Codex orchestrator.
- Yield state after the V5.54 commit: implementation, operational capture, and
  verification complete; no dirty-file owner remains.
- The separate V5.51 worktree at
  `.claude/worktrees/v551-readonly-market-data-contract` was not modified.

## Takeover and stale-claim audit

- Takeover inspection found branch `codex/v5.53-integrated-spy-refresh-cycle`
  at the base HEAD above with empty staged, unstaged, and untracked sets.
- The V5.53 handoff correctly described a later-session integrated Tiingo/M444
  proof. That claim was not stale, but the repository clock resolved only the
  already-qualified `2026-07-27` session until the `2026-07-28` provider cutoff
  at 20:10 America/New_York.
- The operator explicitly authorized V5.54 while that proof was time-gated.
  This changed milestone priority only; it did not broaden credential, broker,
  paper-mutation, cap, or live authority.
- No further review packet, design handoff copy, authority edit, or workflow
  artifact was added. `AGENTS.md` remains unchanged.

## Milestone

V5.54 adds a paper-only SPY decision-time shadow. During an active NYSE
session it:

1. requires canonical adjusted history through the previous completed session;
2. opens the existing one-use Windows Credential Manager
   `alpaca-market-data` lease;
3. performs one exact-host `SPY` snapshot GET with explicit IEX feed,
   10-second timeout, and 256 KiB response cap;
4. requires an in-session latest trade no more than five minutes old;
5. appends that trade in memory as a provisional adjusted-close proxy;
6. evaluates the existing immutable SMA50/200 signal; and
7. writes one idempotent advisory receipt for the session.

The provisional decision is `target_long`, `target_cash`, or `no_decision`.
It never creates an `ExecutionIntent`, `ExecutionPlan`, broker order, or submit
authority. The default intended window is the next NYSE session open.

After an accepted V5.53 authoritative Tiingo refresh and M444 convergence,
`autonomy_spy_refresh_cycle` automatically runs credential-free reconciliation.
It evaluates the authoritative adjusted close, writes `matched` or `diverged`,
and cannot block the authoritative refresh when no provisional receipt exists.

## Observable operational proof

The explicitly authorized production capture ran on `2026-07-28`:

- observed at `2026-07-28T14:54:53.687348+00:00`;
- latest IEX trade at `2026-07-28T14:54:51.501588+00:00`;
- data age: 2 seconds;
- provisional close: `739.44`;
- SMA50: `743.957002866540322`;
- SMA200: `696.1708003802596115`;
- posture: `bullish_risk_on`;
- advisory decision: `target_long`;
- intended execution time: `2026-07-29T13:30:00+00:00`;
- result: `state=provisional_decision_recorded`, exit 0.

The process used one bounded market-data GET and one secure credential lease.
No broker endpoint, account, position, order, paper mutation, or live operation
was accessed. `execution_intent_created`, `execution_plan_created`,
`broker_access_attempted`, `broker_mutation_performed`,
`paper_submit_performed`, and `live_authorized` were all false.

The generated receipt is
`runs/paper_lab/spy_decision_time_shadow/2026-07-28/provisional.json`.
One file was scanned against the exact leased credential values in memory;
zero matches were found. A second production-wrapper invocation returned
`provisional_decision_already_recorded` with both credential and network access
false. Credential-free reconciliation currently returns
`pending_authoritative_adjusted_bar` because the canonical CSV still ends on
`2026-07-27`; no reconciliation receipt was written.

## Verification

- Every default-test preflight found `APP_PROFILE`, all checked Alpaca/APCA
  credential aliases, `TIINGO_API_KEY`, and network/paper integration flags
  absent.
- Focused V5.54 behavior and V5.53 integration: 24 passed.
- Affected transport, integration, Tiingo, secure-provider, interlock,
  adjusted-history, evaluator, dependency, and import-safety surface:
  204 passed.
- Standard offline verification: 109 safety guards passed and
  `git diff --check` passed.
- A plain full pytest invocation exceeded the one-hour outer runner ceiling
  without reporting a failing node.
- A five-shard exact-node run collected 10,113 nodes. One unrelated V5.36
  PowerShell wrapper test hit its internal 60-second timeout under contention;
  that exact node passed alone in 49.44 seconds.
- Final four-shard exact-node run: 10,113 canonical nodes across 500 files;
  10,109 passed, 4 skipped, 0 failures, 0 errors. Collection and execution
  equivalence passed; no shard timed out.

## Files and contracts

New:

- `src/algotrader/execution/spy_decision_time_shadow.py`
- `scripts/run_spy_decision_time_shadow.ps1`
- `tests/unit/test_spy_decision_time_shadow.py`

Updated:

- `src/algotrader/execution/autonomy_spy_refresh_cycle.py`
- `tests/unit/test_autonomy_spy_refresh_cycle.py`
- `docs/deterministic_core.md`
- `docs/OPERATOR_RUNBOOK.md`
- this sole mutable handoff.

Generated `runs/` receipts remain ignored state and are not authority sources.

## Next implementation action

At or after `2026-07-28 20:10 America/New_York`, run the already-authorized
V5.53 integrated cycle once. Require the same invocation to report a new
`2026-07-28` network attempt, `observable_outcome=m444_refreshed_nominal`, and
`decision_time_shadow.state=reconciled` with a truthful `matched` or `diverged`
classification. Do not change V5.54, expand caps, install a task, or add another
review artifact unless that operational proof exposes a concrete defect.
