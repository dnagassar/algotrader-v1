# V5.42 Offline Autonomy Self-Refresh Cycle Contract (Stage 3)

## Purpose

V5.37–V5.39 gave the autonomy program its three layers — observe (supervisor),
decide (planner), act (gated offline executor) — but as three separate commands.
Stage 3 closes them into one loop. `autonomy-self-refresh-cycle` runs a single
deterministic observe → decide → act → re-observe cycle and reports whether the
system converged to a healthy steady state.

It also gives the loop a real trigger. The V5.37 supervisor lane
`spy_offline_daily_cycle` previously disabled staleness (`max_age_hours=0`), so
its refresh action was never emitted and the executor was inert. V5.42 sets that
lane's `max_age_hours=30`: a *daily* cycle whose latest accepted evidence carries
a timestamp older than 30h is now `stale`, which the planner turns into
`rerun_offline_daily_cycle_chain` (an allowlisted, fully-defaulted offline
command the executor may run). Records without a timestamp are never stale, so
seeded/absent evidence is unaffected.

## The Cycle

`build_self_refresh_cycle(config, *, apply=False, environ=None, runner=None)`:

1. **Observe** — `build_autonomy_supervisor_report(config)` → `before`.
2. **Decide** — `build_autonomy_next_plan_from_report(before)`.
3. **Act** — `build_offline_execution_ledger(config, apply=apply, plan_report=…)`.
   Dry-run by default (executes nothing); `apply=True` runs the eligible
   allowlisted offline commands behind the executor's credential/profile
   preflight.
4. **Re-observe** — `build_autonomy_supervisor_report(config)` → `after`.

The record carries `before_system_status`, `after_system_status`, the plan
summary, the full execution ledger, compact before/after lane summaries, a
`cycle_outcome`, and `converged`.

## Outcomes

- `dry_run_preview` — `apply=False`; nothing executed, `before == after`.
- `noop_no_action` — `apply=True` but no eligible offline action; system already
  steady.
- `refreshed` — `apply=True`, an action executed successfully, and the
  re-observed system status is strictly less severe than before.
- `still_pending` — executed successfully but the system status did not improve.
- `execution_failed` — an executed action returned non-zero.

`converged` is `True` when the re-observed `system_status` is `nominal`,
`waiting`, or `no_lane_evidence` (nothing needs attention). Exit code: `2` on
validation error; `1` on execution failure or a non-converged cycle; `0`
otherwise.

## Non-Negotiable Safety Contract

- The cycle performs no work of its own beyond orchestration. All side effects
  are the executor's, which only runs frozen-allowlist offline commands behind a
  preflight that refuses under a loaded paper/live profile or any credential/
  network-test variable.
- Dry-run is fully inert (spawns no subprocess).
- The module imports no `os`, `socket`, `urllib`, `requests`, `subprocess`, or
  broker SDK, and reads no wall clock (time is the caller `as_of`); a source-scan
  test enforces this.
- Every record fixes `submitted`, `mutated`, `broker_action_performed`,
  `broker_actions_performed`, `broker_mutation_allowed`,
  `network_access_attempted`, `credential_access_attempted`, and
  `live_authorized` to false with `profit_claim=none`.

## Behaviour Change To Note

Enabling daily-cycle staleness means that in an environment with real but aged
daily-cycle evidence, the supervisor will now report that lane `stale` and the
whole-system status `attention_required`, and a self-refresh cycle run with
`--apply` will attempt the offline rerun. That is the intended closed loop; it is
the correct escalation for a daily cycle that has not been refreshed within ~a
day. It changes no live-capital, paper-mutation, credential, or network
authority — the rerun is a local offline command.

## Verification

- `tests/unit/test_autonomy_self_refresh_cycle.py` proves dry-run inertness, the
  full stale→execute→converge loop closure (`refreshed`), failed-refresh
  non-convergence, noop when nothing is eligible, executor preflight refusal
  under a live signal, deterministic JSON/text rendering, single-record JSONL
  write, input validation, CLI dry-run and exit codes, and a source-scan.
- `tests/unit/test_autonomy_supervisor.py` adds daily-cycle staleness tests
  (stale after 30h, fresh nominal, no-timestamp never stale).
- The V5.37–V5.41a suites and the targeted offline verifier remain green.
