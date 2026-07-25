# V5.42 Offline Autonomy Self-Refresh Cycle Contract (Stage 3)

## Purpose

V5.37–V5.39 gave the autonomy program its three layers — observe (supervisor),
decide (planner), act (gated offline executor) — but as three separate commands.
Stage 3 closes them into one loop. `autonomy-self-refresh-cycle` runs a single
deterministic observe → decide → act → re-observe cycle and reports whether the
system converged to a healthy steady state.

It also gives the loop a real staleness signal. The V5.37 supervisor lane
`spy_offline_daily_cycle` previously disabled staleness (`max_age_hours=0`).
V5.42 sets that lane's `max_age_hours=30`: a *daily* cycle whose latest accepted
evidence carries a timestamp older than 30h is now `stale`. Records without a
timestamp are never stale, so seeded/absent evidence is unaffected.

### What staleness means per lane

Staleness is a signal, not automatically an action. Each lane declares
`stale_requires_operator_action`, which says whether any offline command could
cure its staleness:

- `spy_offline_daily_cycle` — **operator-curable only**. The sole command that
  writes this lane's artifact (`m444_offline_daily_cycle_run.jsonl`) is the seed
  command `etf-sma-offline-daily-cycle-run`, which requires an operator-supplied
  daily chain clock and daily-bars CSV and is deliberately not allowlisted. The
  allowlisted `etf-sma-offline-daily-cycle-rerun-m446` is a *milestone
  reproduction*: it hard-pins the expected latest bar date to `2026-06-08` and
  writes the M447 manifest, never `m444`. It therefore cannot cure staleness
  here, and stale routes to `operator_refresh_offline_daily_cycle_inputs`.
- `spy_market_data_soak` — **operator-curable only**. A stale soak means the
  scheduled refresh task stopped producing sessions; only the operator can
  restore it.

A lane that is stale *and* operator-curable-only aggregates as `waiting`, not
`attention_required`: the lane still reports `stale`, its age, and appears in
`stale_lanes`, so no signal is lost — but an autonomous loop that has no command
to run has genuinely finished its work, and says so rather than spinning. A
cross-module test keeps this flag in lockstep with the planner's classification
of each lane's stale action.

Consequence: under the current lane registry **no reachable lane state emits an
allowlisted action**, so the executor is inert and `--apply` executes nothing.
That is the truthful state today, and an explicit test asserts it so that adding
a genuinely offline-runnable refresh is a deliberate change.

## The Cycle

`build_self_refresh_cycle(config, *, apply=False, allow_empty_lab=False,
environ=None, runner=None)`:

1. **Observe** — `build_autonomy_supervisor_report(config)` → `before`.
2. **Decide** — `build_autonomy_next_plan_from_report(before)`.
3. **Act** — `build_offline_execution_ledger(config, apply=apply, plan_report=…)`.
   Dry-run by default (executes nothing); `apply=True` runs the eligible
   allowlisted offline commands behind the executor's credential/profile
   preflight.
4. **Re-observe** — `build_autonomy_supervisor_report(config)` → `after`.

The record carries `before_system_status`, `after_system_status`, the plan
summary, the full execution ledger, compact before/after lane summaries, a
`cycle_outcome`, `allow_empty_lab`, `evidence_required`, and `converged`.

## Outcomes

- `evidence_required` — the re-observed status is `no_lane_evidence` and the
  caller did not explicitly allow an intentionally empty lab; the cycle fails
  closed even in dry-run mode.
- `dry_run_preview` — `apply=False`; nothing executed, `before == after`.
- `noop_no_action` — `apply=True` but no eligible offline action; system already
  steady.
- `refreshed` — `apply=True`, an action executed successfully, and the
  re-observed system status is strictly less severe than before.
- `still_pending` — executed successfully but the system status did not improve.
- `execution_failed` — an executed action returned non-zero.

V5.42a amendment to the severity ranking behind `refreshed`/`still_pending`:
`_SYSTEM_SEVERITY` is now derived from the supervisor's exported
`AUTONOMY_SUPERVISOR_SYSTEM_STATUSES` instead of restated locally, resolves a
rank through a helper that raises `ValidationError` on an unrankable status
instead of defaulting, and ranks `no_lane_evidence` as the **most** severe
status. Previously it ranked `no_lane_evidence` as the healthiest, so a cycle
whose lane evidence disappeared would have reported `refreshed` while seeding an
empty lab reported `still_pending` — both backwards. This corrects the
unreachable act-phase paths rather than making them reachable, and the statement
below that they "stay correct" holds only from V5.42a onward. `converged`,
`evidence_required`, and every exit code are unchanged. The cycle also forwards
`allow_empty_lab` into both supervisor observations so the embedded reports agree
with the cycle's own declaration. See
`docs/design/v5_42a_whole_system_rollup_truthfulness_contract.md`.

`converged` is `True` when the re-observed `system_status` is `nominal` or
`waiting`. `no_lane_evidence` is non-converged by default and exits `1` with
`cycle_outcome=evidence_required`. An intentionally empty lab may opt in with
`allow_empty_lab=True` / `--allow-empty-lab`, which is recorded in the payload
and permits that state to converge. Exit code is `2` on validation error, `1` on
execution failure or any non-converged cycle, and `0` otherwise.

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
daily-cycle evidence, the supervisor now reports that lane `stale` and the
whole-system status `waiting`, and the plan names the two operator inputs
needed to cure it (a refreshed daily-bars CSV and a daily chain clock). The seed
command must target the canonical m444 manifest output path. A `--apply` cycle
executes nothing and exits `0`: the loop has converged on the correct
conclusion that only the operator can advance this lane. It changes no live-capital, paper-mutation, credential, or network
authority.

## Fail-Closed Empty-Lab Contract

`no_lane_evidence` is not proof of a healthy system. The self-refresh cycle now
returns `cycle_outcome=evidence_required`, `evidence_required=true`,
`converged=false`, and exit `1` by default when every registered lane is absent.
This makes a wrong or empty `--lanes-root` fail closed for unattended callers.

A deliberately empty bootstrap lab must opt in with `--allow-empty-lab` (or
`-AllowEmptyLab` through the PowerShell wrapper). The record then fixes
`allow_empty_lab=true` and may converge with `no_lane_evidence`; the explicit
exception is therefore auditable rather than inferred from an empty directory.

## Full-gate secure-provider boundary correction

Independent full-suite review exposed an inherited V5.35/V5.41a integration
conflict: the secure child deliberately strips profile and credential environment
variables and passes its validated paper profile/endpoints as explicit non-secret
arguments, while the newly added live-capital interlock read only the stripped
environment and refused the default `dev` profile. The adapter now builds a
non-secret interlock view without overriding any ambient key. It refuses ambient
profile, endpoint, or live-enable conflicts before opening the credential lease;
inside the lease callback, it binds the already-resolved values only to a
temporary in-memory view so the complete canonical paper-boundary check runs
again immediately before the read-only HTTP opener. No credential value is
persisted, logged, or returned, and no broker-mutation or live authority changes.

## Verification

- `tests/unit/test_autonomy_self_refresh_cycle.py` proves dry-run inertness,
  convergence-to-waiting on operator-curable staleness, default fail-closed
  `no_lane_evidence`, the explicit empty-lab exception, executor inertness under
  the current lane registry, full `cycle_outcome` classification coverage
  (including the `refreshed`/`still_pending`/`execution_failed` paths that stay
  correct but are currently unreachable), executor preflight refusal under a
  live signal, deterministic JSON/text rendering, single-record JSONL write,
  input validation, CLI and PowerShell-wrapper contracts, exit codes, and a
  source-scan.
- `tests/unit/test_autonomy_supervisor.py` adds daily-cycle staleness tests
  (stale after 30h, fresh nominal, no-timestamp never stale) and proves stale
  operator-curable lanes aggregate as `waiting` while still appearing in
  `stale_lanes`.
- `tests/unit/test_autonomy_next_plan.py` proves the supervisor's
  `stale_requires_operator_action` flag and the planner's classification of each
  lane's stale action cannot drift apart; the executor suite proves no action in
  the current lane registry intersects the executor allowlist.
- `tests/unit/test_v535_secure_dispatcher.py` proves the secure-provider path
  passes the full interlock at the mocked read-only HTTP boundary and refuses
  ambient live profile, live endpoint, and live-enable signals before credential
  or HTTP access.
- Combined focused autonomy/boundary/dependency suite: `163 passed` before the
  final endpoint-key test addition; focused boundary suite afterward: `73 passed`.
- Canonical standard offline verifier: `99 passed`, all profile/credential/network
  preflight booleans false, hygiene clean.
- Repository-owned bounded full suite: `9,933` collected, `9,929 passed`,
  `4 skipped`, `0 failures`, `0 errors`; collection and execution equivalence
  passed across all eight shards.
