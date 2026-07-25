# V5.38a Planner State-Vocabulary Fail-Closed Contract

## Status And Scope

- Milestone:
  `V5.38a — fail closed on an unrankable lane state in the offline autonomy
  next-action planner`.
- Parent milestone:
  `V5.38 — offline autonomy next-action planner`
  (`docs/design/v5_38_offline_autonomy_next_action_planner.md`).
- Sibling repair, same defect class:
  `V5.37a — all-absent aggregate recommended action`
  (`docs/design/v5_37a_all_absent_aggregate_recommendation_contract.md`).
- Accepted implementation base:
  `979bca9` on `claude/v5.42-stage3-self-refresh`.
- This contract authorizes offline implementation and verification only.
- It grants no credential read, network access, broker access, paper mutation,
  order operation, scheduler operation, capital allocation, or trading effect.
  The planner remains a read-only planning surface that spawns no subprocess.

## Deterministic Defect Evidence

`_plan_lane` in `src/algotrader/execution/autonomy_next_plan.py` accepts a lane's
`normalized_state` as any non-empty string. `_highest_priority_action` then
selects the next offline action by iterating the planner's `_STATE_SEVERITY`
tuple and matching `action["normalized_state"]` against it. A lane whose state is
outside that vocabulary matches nothing, so it is silently skipped by the
selector — while `offline_lanes` and therefore `plan_class` are computed from
`offline_runnable` alone and still count it.

The result is a self-contradictory plan record. Reproduced against the frozen
registry by taking a real all-absent supervisor report, setting one lane's
`normalized_state` to `healthy` (outside the vocabulary) with an offline-runnable
`next_action`, and planning it:

```
plan_class                : offline_action_available
offline_runnable_lanes    : ['spy_offline_daily_cycle']
next_offline_action_lane  : ''
next_offline_action       : None
operator_summary          : No offline action is available; 5 lane(s) are gated
                            on the operator ...
```

`plan_class` and `offline_runnable_lanes` assert an offline action exists;
`next_offline_action`, `next_offline_action_lane`, and `operator_summary` assert
none does. `docs/design/v5_38_offline_autonomy_next_action_planner.md` documents
both fields independently ("`offline_action_available` — at least one lane is
offline-runnable"; "`next_offline_action` ... or `null` when none exists") and
never states the invariant that ties them together, so neither field is
individually wrong — the record simply contradicts itself.

Reachability: the two public library entry points that accept a caller-supplied
report, `build_autonomy_next_plan_from_report(report)` and
`build_offline_execution_ledger(config, plan_report=report)`. Reports built
internally through `build_autonomy_next_plan(config)` always carry vocabulary
states, so the CLI path is not affected. The planner already fails closed on an
unrecognized *action token* (to an operator-review gate) and on an unknown *lane
id* (`ValidationError`); it has no equivalent guard on the *state* vocabulary it
ranks by, which is the gap.

Contributing cause: the planner re-declares its own `_STATE_SEVERITY` tuple from
the imported `STATE_*` constants rather than sharing the supervisor's frozen
ordering. Two independently maintained copies of one vocabulary can drift, and a
state added to the supervisor but not the planner would reintroduce exactly this
silent-skip behavior on the normal internal path.

## Required Behavior

1. The supervisor must export its frozen normalized-state vocabulary as a public
   constant `AUTONOMY_SUPERVISOR_STATES`, ordered most to least severe, and its
   internal `_STATE_SEVERITY` must be that same object rather than a second
   literal.
2. The planner must consume `AUTONOMY_SUPERVISOR_STATES` as its severity order
   and must not declare its own copy, so the ranking vocabulary and the
   supervisor vocabulary cannot drift.
3. `_plan_lane` must reject a `normalized_state` that is not in that vocabulary
   with a `ValidationError`, consistent with the existing unknown-lane-id
   rejection in `_report_lanes`. A lane state the severity loop cannot rank must
   never be silently dropped from selection.
4. The invariant `plan_class == offline_action_available` if and only if
   `next_offline_action is not None` (equivalently, `next_offline_action_lane`
   non-empty) must hold for every plan the module can produce.
5. `operator_summary` must never assert "no offline action is available" for a
   record whose `plan_class` is `offline_action_available`.
6. Action-token classification behavior is unchanged: an unrecognized token still
   fails closed to the `unclassified_action_operator_review` gate rather than
   raising. Only the state vocabulary becomes a hard input contract.

## Safety Invariants

The repair must not:

- change any lane's classification, gate, gate detail, command, required
  operator inputs, or preconditions;
- change `plan_class` values, severity ordering, registry-order tie-breaking, or
  exit codes (`0` all-nominal-or-waiting, `1` pending action, `2` validation
  error);
- change `AUTONOMY_ACTION_CLASSIFICATION` contents or the operator-gated
  classification of any token;
- add, widen, or activate any executable path: `AUTONOMY_EXECUTOR_ALLOWLIST`,
  the V5.39 eligible/skip partition, and the documented executor inertness are
  out of scope and must be untouched;
- introduce an import of `os`, `socket`, `subprocess`, `urllib`, `requests`,
  `httpx`, or any broker SDK, any wall-clock read, or any credential/profile
  load into the planner or supervisor; or
- alter the fixed false safety booleans, `paper_lab_only`,
  `not_live_authorized`, or `profit_claim=none` on any record.

## Verification Contract

Credential-free offline tests must prove:

1. a report carrying an out-of-vocabulary `normalized_state` raises
   `ValidationError` from `build_autonomy_next_plan_from_report`, replacing the
   previously silent self-contradictory plan;
2. the same input raises through `build_offline_execution_ledger(...,
   plan_report=report)`, so the executor's external-plan seam inherits the guard
   and no ledger is produced from an unrankable plan;
3. the `plan_class` / `next_offline_action` invariant holds across a matrix of
   valid lane states, including all-absent, all-nominal, and mixed reports;
4. every state in `AUTONOMY_SUPERVISOR_STATES` is accepted by the planner, so the
   guard rejects only genuinely out-of-vocabulary values;
5. the planner's severity order is the supervisor's exported vocabulary, so a
   future state added to the supervisor cannot silently bypass ranking;
6. all existing planner, executor, self-refresh, and supervisor behavior is
   unchanged — the full existing `test_autonomy_next_plan.py`,
   `test_autonomy_offline_executor.py`, `test_autonomy_self_refresh_cycle.py`,
   and `test_autonomy_supervisor.py` suites pass, with the single exception of
   any test that asserted the old silent-skip behavior (none is known to exist);
   and
7. `tests/unit/test_dependency_direction.py` and the full offline verifier remain
   credential-free, network-free, broker-free, mutation-free, order-free, and
   trading-free.

## Documentation Contract

- `docs/design/v5_38_offline_autonomy_next_action_planner.md` must state the
  `plan_class` / `next_offline_action` invariant and the state-vocabulary input
  contract alongside the existing unclassified-token rule.
- `docs/design/v5_39_gated_offline_autonomy_executor.md`'s "Honest Current
  Limitation" section states the executor is inert because the SPY offline
  daily-cycle lane sets `max_age_hours=0`. That reason is stale: V5.42 Stage 3
  set that lane to `max_age_hours=30`, and the lane's `stale` action now routes
  to the operator-gated `operator_refresh_offline_daily_cycle_inputs`. The
  conclusion (inert today) is still correct and must stand; only the stated
  mechanism must be corrected, so no future reader re-enables staleness expecting
  it to activate the executor.

## Out Of Scope, Recorded

`build_offline_execution_ledger` computes `all_executions_succeeded` as
`all(...)` over an empty `executed_actions` list, so a ledger with
`apply=true`, a passing preflight, and zero eligible actions reports
`all_executions_succeeded=true` with `execution_count=0` and an empty
`execution_refused_reason`. That is vacuously true rather than wrong, and the
V5.42 self-refresh cycle already checks `execution_count == 0` before consulting
it, so no false `refreshed` outcome results. Changing that boolean's semantics
would alter the reviewed V5.39 record schema and a V5.42 consumer, so it belongs
in its own contract and review rather than this repair.

## Review And Operator Route

An independent reviewer must inspect the implementation commit against this
contract on top of `979bca9`. No operational action follows: the planner remains
read-only, the executor's documented inertness is untouched, and the change only
converts a silently self-contradictory record into a fail-closed rejection.
