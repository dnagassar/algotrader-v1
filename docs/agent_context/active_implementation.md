# Active Implementation Checkpoint

## Classification

- Milestone: `V5.38a — fail closed on an unrankable lane state in the offline
  autonomy next-action planner`.
- Review disposition: not yet independently reviewed.
- Contract commit: `4506a42` (`V5.38a: freeze planner state-vocabulary
  fail-closed contract`).
- Implementation commit: `86c394f` (`V5.38a: fail closed on an unrankable lane
  state in the planner`).
- Preceding accepted milestone on this branch: `V5.37a` (contract `029825c`,
  implementation `85b289e`, handoff `979bca9`) — independently accepted
  (operator-asserted 2026-07-25, no committed review artifact) and pushed.
- Operator action required for this offline implementation: `false`.
- Merge to `main`: not performed. `origin/main@6b5dde6` does not contain either
  V5.37a or V5.38a.
- This is not strategy-profit, paper-order, broker-mutation, activation, or
  live-trading evidence.

## Current Checkout And Ownership

- Worktree `.claude/worktrees/quirky-goodall-7f8d71`, local branch
  `claude/v5.41c-empty-lab-aggregate`, based on
  `origin/claude/v5.42-stage3-self-refresh`. The branch name predates both
  milestones on it (V5.37a, V5.38a) and matches neither; treat it as a label.
  The pushed frontier branch is the canonical location of this work.
- Takeover-protocol state verified before any edit this session: branch, HEAD
  (`979bca9`, identical to the pushed frontier tip), clean `git status --short`,
  empty staged and unstaged diffs, no untracked `src`/`tests` files, and
  `AGENTS.md` current for this branch (last changed by `c3d86d2`, in history).
  No reset, clean, stash, rebase, restore, or branch switch was performed.
- No dirty-file owner remains: clean at the handoff commit.
- Environment note still in force: `scripts\verify_offline.ps1 -Full` binds the
  shared registered interpreter's editable `algotrader` install to whichever
  worktree runs it. It is currently bound to this worktree (rebound from
  `.claude/worktrees/controlled-implementation-takeover-6808bf` during the V5.37a
  slice). An agent resuming elsewhere must re-run its own `-Full` or the binding
  script before trusting in-process imports.

## Capability Actually Proven

### The audit that was the recorded next action

The V5.37a handoff recorded one next action: audit V5.38 `autonomy-next-plan` and
V5.39 `autonomy-apply-plan` for the defect class V5.37a fixed — declared branches
no reachable input can produce, and per-lane values that can disagree with
whole-system values. That audit was executed. Four results:

1. **Real defect, repaired (V5.38a).** `_plan_lane` accepted any non-empty
   `normalized_state`, while `_highest_priority_action` ranked lanes by a severity
   tuple the planner re-declared locally from the imported `STATE_*` constants. A
   lane state outside that vocabulary matched nothing in the ranking loop and was
   silently skipped by selection, yet still counted toward `offline_runnable_lanes`
   and therefore `plan_class`. Reproduced against the frozen registry by setting
   one lane to `normalized_state="healthy"` with an offline-runnable
   `next_action`: `plan_class=offline_action_available`,
   `offline_runnable_lanes=['spy_offline_daily_cycle']`, but
   `next_offline_action=None`, `next_offline_action_lane=""`, and an
   `operator_summary` reading "No offline action is available". Neither field was
   individually wrong — the V5.38 design doc documents both independently and
   never stated the invariant that binds them — so the record simply contradicted
   itself, and nothing failed closed.
2. **Documented non-defect, untouched.** `rerun_offline_daily_cycle_chain` is the
   only `auto_offline` classification in `AUTONOMY_ACTION_CLASSIFICATION` and the
   only `AUTONOMY_EXECUTOR_ALLOWLIST` entry, and no state of any lane in the
   frozen registry emits it, so the executor's eligible set is always empty when
   wired to real lane evidence. Verified against the docs before treating it as a
   bug: `docs/design/v5_39_gated_offline_autonomy_executor.md` and
   `docs/design/v5_42_offline_autonomy_self_refresh_cycle.md` both document this
   inertness as the intended, fail-closed posture. Not changed. Registry
   reachability was also checked in the reverse direction:
   `rerun_offline_daily_cycle_chain` is the only classified token no lane can
   emit, and no emittable token is unclassified.
3. **Stale documentation claim, corrected.** V5.39's "Honest Current Limitation"
   attributed the inertness to `spy_offline_daily_cycle` having
   `max_age_hours=0`. V5.42 Stage 3 changed that lane to `max_age_hours=30`, so
   it does reach `stale`; its stale action routes to the operator-gated
   `operator_refresh_offline_daily_cycle_inputs` because the pinned M446 rerun
   reproduces one historical dataset and writes a different artifact. The
   conclusion (inert today) was still true; the stated mechanism was not. Left
   uncorrected, a future reader could re-enable or widen a staleness bound
   expecting it to activate the executor, which it would not.
4. **Out of scope, recorded in the contract.**
   `build_offline_execution_ledger` computes `all_executions_succeeded` as
   `all(...)` over an empty `executed_actions` list, so `apply=true` with a
   passing preflight and zero eligible actions reports
   `all_executions_succeeded=true` with `execution_count=0` and an empty
   `execution_refused_reason`. Vacuously true rather than wrong, and V5.42's
   `_classify_outcome` checks `execution_count == 0` before consulting it, so no
   false `refreshed` outcome results. Changing that boolean's semantics would
   alter the reviewed V5.39 record schema and a V5.42 consumer, so it needs its
   own contract and review.

### What V5.38a changed

- The supervisor now exports its frozen normalized-state vocabulary as
  `AUTONOMY_SUPERVISOR_STATES` (most to least severe); its private
  `_STATE_SEVERITY` is that same object, not a second literal.
- The planner ranks by that exported tuple. Its duplicated local tuple and its
  now-unused individual `STATE_*` imports are gone, so the ranking vocabulary and
  the supervisor vocabulary cannot drift — a state added to the supervisor but
  not the planner can no longer become silently unrankable.
- `_plan_lane` rejects a `normalized_state` outside the vocabulary with a
  `ValidationError`, consistent with the existing unknown-lane-id rejection in
  `_report_lanes`. Both public seams that accept a caller-supplied report now
  fail closed: `build_autonomy_next_plan_from_report(report)` and
  `build_offline_execution_ledger(config, plan_report=report)`.
- Invariant now declared and tested: `plan_class == offline_action_available` if
  and only if `next_offline_action` is non-null and `next_offline_action_lane` is
  non-empty, and `operator_summary` never claims no offline action is available
  for such a plan.
- Unchanged: action-token classification (an unrecognized token still fails
  closed to the `unclassified_action_operator_review` gate rather than raising),
  every lane's classification/gate/command/inputs/preconditions, `plan_class`
  values, severity ordering, registry-order tie-breaking, all CLI exit codes, the
  executor allowlist and eligible/skip partition, and every fixed false safety
  boolean. The CLI path is unaffected because internally built reports always
  carry vocabulary states.

## Files In This Slice

- `docs/design/v5_38a_planner_state_vocabulary_fail_closed_contract.md` (new,
  frozen first in `4506a42`)
- `src/algotrader/execution/autonomy_supervisor.py`
- `src/algotrader/execution/autonomy_next_plan.py`
- `tests/unit/test_autonomy_next_plan.py`
- `tests/unit/test_autonomy_offline_executor.py`
- `docs/design/v5_38_offline_autonomy_next_action_planner.md`
- `docs/design/v5_39_gated_offline_autonomy_executor.md`

## Verification Evidence

- Credential/profile preflight (booleans only, no values read or printed):
  `APP_PROFILE_is_paper=false`; `ALPACA_API_KEY_loaded=false`;
  `ALPACA_API_SECRET_KEY_loaded=false`; `ALPACA_SECRET_KEY_loaded=false`;
  `APCA_API_KEY_ID_loaded=false`; `APCA_API_SECRET_KEY_loaded=false`;
  `ALGO_TRADER_ALLOW_NETWORK_TESTS_enabled=false`;
  `PYTEST_ADDOPTS_allow_network=false`;
  `RUN_ALPACA_PAPER_INTEGRATION_TESTS_enabled=false`.
- Targeted suites (`PYTHONPATH=src`): `test_autonomy_next_plan.py`,
  `test_autonomy_offline_executor.py`, `test_autonomy_supervisor.py`,
  `test_autonomy_self_refresh_cycle.py`, `test_dependency_direction.py`:
  `149 passed`. Five new tests: out-of-vocabulary state rejected by the planner,
  the same rejected through the executor's `plan_report` seam, every
  `AUTONOMY_SUPERVISOR_STATES` value accepted, the planner's severity order is
  the supervisor's exported tuple, and the
  `plan_class`/`next_offline_action`/`operator_summary` invariant across five
  report shapes (all-absent, single nominal, blocked, mixed waiting, seeded
  daily cycle).
- No pre-existing test asserted the old silent-skip behavior. Every other test
  that hand-sets `normalized_state` uses a valid vocabulary value, including the
  executor's `_stale_rerun_plan` helper (`stale`), which is why the allowlisted
  `auto_offline` token remains exercised through a directly supplied plan.
- `scripts\verify_offline.ps1` (non-`-Full`): `PASS`, targeted guard suite
  `99 passed`, clean preflight and repository-hygiene checks.
- `scripts\verify_offline.ps1 -Full` (backgrounded, ~16 min wall): exit `0`,
  `offline verification result PASS`, `bounded_full_suite=PASS`.
  `canonical_nodeids=9957` across `canonical_files=494` in `shard_count=8`;
  `collection_equivalence=PASS`; `execution_equivalence=PASS`;
  `aggregate_result=tests:9957,passed:9952,skipped:5,failures:0,errors:0`. All
  eight shards exited `0` with `timeout:false` (wall seconds 772.89, 947.96,
  801.77, 809.29, 809.84, 849.95, 1006.11, 868.60). Full transcript captured this
  run — the V5.37a handoff's missing-metrics caveat does not apply here.
- `git diff --check`: clean. `git status --short`: clean after commit.
  `git diff --name-only HEAD -- src`: empty after commit.
  `git ls-files --others --exclude-standard src tests`: empty.
- Network/broker access during this work: none. Paper mutation: none. Effective
  paper caps: not applicable (no order or paper-mutation path touched).
  Receipts/reconciliation: not applicable. Live-authorized state: `false`,
  unchanged. The unmodified forbidden-import/forbidden-call source scans in
  `test_autonomy_next_plan.py` and `test_autonomy_offline_executor.py` still pass
  against the edited modules.

## Safety And Authority Posture

- Offline, deterministic, credential-free, network-free, broker-free, and
  mutation-free, exactly as scoped. No credentials were loaded at any point.
- No dependency-direction, network-guard, or broker-mutation-surface invariant was
  touched or weakened.
- The change only tightens an input contract: a previously accepted,
  self-contradictory plan input is now rejected. No execution path was added,
  widened, or activated; the executor's documented inertness is unchanged.

## Unresolved Risks

- V5.38a has not been independently reviewed. Review should inspect `86c394f`
  against the frozen contract `4506a42`.
- **`main` still carries the V5.37a defect and now also the V5.38a one.**
  `origin/main@6b5dde6` was verified during the V5.37a slice to retain the
  unreachable fallback and the `absent` fall-through loop in
  `_highest_priority_lane`; it likewise predates V5.38a. `main` reached the same
  empty-lab fail-closed contract independently as V5.41b (`9f3d77a`, `3fa2acb`,
  `docs/design/v5_41b_standalone_supervisor_empty_lab_contract.md`) while this
  frontier did it as V5.37 (`f3a9757`), so the two lines overlap in
  `autonomy_supervisor.py` and `cli.py`. A merge that favors `main` silently
  reintroduces both defects. Milestone numbering also overlaps for the same
  subject matter (V5.37/V5.37a/V5.38a here vs V5.40a/V5.41b on `main`).
- The `all_executions_succeeded` vacuous-true aggregate (audit result 4 above)
  remains open by deliberate scope choice.
- `--allow-empty-lab` remains a caller assertion rather than proof of intent.
- These milestones prove control-plane reporting truthfulness and input
  fail-closure, not research alpha, portfolio construction, paper order
  submission, burn-in, or live readiness.

## Contribution Toward The Autonomous Research Trader

V5.37a made the observe layer's whole-system verdict agree with its recommended
remedy. V5.38a does the same one layer up, for the decide layer: the plan's
whole-system class and the single action it names are now provably two views of
one fact, and a report the planner cannot rank is refused instead of silently
half-processed. Both defects were the same shape — an aggregate computed by one
rule and a detail selected by another, with no guard binding them — which is why
the audit that found the second one is worth continuing.

## Next Highest-Leverage Safe Action

Extend the same audit to the two layers not yet swept: V5.42
`autonomy_self_refresh_cycle.py` and the V5.37 supervisor's own remaining
aggregates. Concretely, all offline and read-only:

- `autonomy_self_refresh_cycle.py`: `_classify_outcome`'s branch reachability
  (can every one of `evidence_required`, `dry_run_preview`, `noop_no_action`,
  `execution_failed`, `refreshed`, `still_pending` be produced from real
  evidence, given the executor is inert today?), and whether `converged` can
  disagree with `after_system_status` the way `plan_class` disagreed with
  `next_offline_action`.
- The `_SYSTEM_SEVERITY` ranking in that module: confirm it covers every
  `system_status` the supervisor can emit, which is the same drift risk V5.38a
  removed from the planner — and now fixable the same way, by consuming an
  exported constant rather than a local copy.
- The supervisor's remaining derived booleans (`system_attention_required`,
  `evidence_required`) against `system_status`, for any combination that cannot
  occur or that contradicts the lane counts.

Treat any finding under the two-stage rule: freeze a contract doc first, then
implement, then verify with the targeted suites plus `scripts\verify_offline.ps1`.

The `main`-vs-frontier reconciliation remains the largest standing integration
risk and is recorded under Unresolved Risks rather than here, because it is an
operator sequencing decision rather than an implementation slice. An explicitly
scoped paper-order or broker-facing milestone may proceed under the standing
authority in `AGENTS.md` once its paper endpoint, finite caps, receipts,
reconciliation, and audit boundaries are proven. Live activity remains prohibited.
