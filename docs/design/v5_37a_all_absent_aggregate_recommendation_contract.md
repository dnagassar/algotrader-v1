# V5.37a All-Absent Aggregate Recommendation Contract

## Status And Scope

- Milestone:
  `V5.37a — all-absent aggregate recommended action for the offline cross-lane
  autonomy supervisor`.
- Parent milestone:
  `V5.37 — offline cross-lane autonomy supervisor`
  (`docs/design/v5_37_offline_cross_lane_autonomy_supervisor.md`), as corrected
  by the standalone fail-closed `no_lane_evidence` repair.
- Accepted implementation base:
  `4b07cd9c6b2a624573a70b34b3a7a5e75f250bc2`.
- This contract authorizes offline implementation and verification only.
- It grants no credential read, network access, broker access, paper mutation,
  order operation, scheduler operation, capital allocation, or trading effect.
  The supervisor remains read-only reporting over local evidence artifacts.

## Deterministic Defect Evidence

`_aggregate` in `src/algotrader/execution/autonomy_supervisor.py` declares an
aggregate fallback recommendation for a lab with no lane evidence at all:

```python
"recommended_next_action": highest["next_action"] if highest else (
    "all_lanes_absent_run_lane_commands_to_seed_evidence"
),
```

That fallback is unreachable. `_highest_priority_lane` skips `absent` in its
severity loop with the comment "An all-absent system is handled by the aggregate
default action", but then falls through to a second loop that returns the first
`absent` summary. It therefore returns `None` only for an empty
`lane_summaries` list, and `lane_summaries` is built by iterating the non-empty
frozen `AUTONOMY_SUPERVISOR_LANES` registry in both public entry points
(`build_autonomy_supervisor_report`,
`build_autonomy_supervisor_report_from_records`). `highest` is always truthy, so
the fallback never renders and the second loop is reachable only in exactly the
case the first loop was written to defer — an all-absent lane set.

Observable consequence on a completely empty lab
(`system_status=no_lane_evidence`): the report recommends the first registry
lane's absent action, `run_authorized_read_only_market_data_refresh_to_seed_soak`
on `spy_market_data_soak`, with `recommended_next_action_lane` naming that one
lane. That is a misleading single-lane instruction for a whole-system condition
in which every lane needs seeding, and it is the exact state the fail-closed
`no_lane_evidence`/`allow_empty_lab` contract exists to describe truthfully.

The V5.38 planner already anticipates the intended output: its frozen
`AUTONOMY_ACTION_CLASSIFICATION` registry classifies
`all_lanes_absent_run_lane_commands_to_seed_evidence` as operator-gated
("all lanes absent; per-lane seeding is operator-driven"), under the comment
"Aggregate fallback the supervisor emits only if it has no lane". That entry is
today unexercised because the supervisor cannot emit the token.

## Required Behavior

V5.37a resolves the defect by making the all-absent case actually use the
aggregate recommendation (option (a)); the dead fallback is not deleted:

1. `_highest_priority_lane` must return a lane summary only for a lane whose
   normalized state is not `absent`. Its fall-through loop that returns the
   first `absent` summary is removed, so it returns `None` when no lane carries
   a non-`absent` state.
2. When `_highest_priority_lane` returns `None`, the report must carry
   `recommended_next_action = "all_lanes_absent_run_lane_commands_to_seed_evidence"`
   and `recommended_next_action_lane = ""` (no single lane is named, because no
   single lane is the remedy).
3. The condition in (2) is exactly `system_status == no_lane_evidence` for any
   report built through a public entry point: every lane is `absent`, so
   `_system_status` returns `no_lane_evidence` and the two facts cannot drift.
4. Any report with at least one non-`absent` lane must keep naming that
   highest-severity lane and its per-lane action, with severity order and
   registry-order tie-breaking unchanged. Partially-seeded labs are unaffected;
   an `absent` lane is never the recommendation while any other lane has
   evidence.
5. The fallback token must become an exported module constant of
   `autonomy_supervisor` rather than an inline literal, so the emitted token and
   the V5.38 classification registry key are one declared contract rather than
   two duplicated strings.
6. `recommended_next_action` must remain non-empty for every reachable report,
   and every emitted token must remain classified by
   `AUTONOMY_ACTION_CLASSIFICATION`.

## Safety Invariants

The repair must not:

- change any per-lane normalization, staleness, safety-flag, blocker, or
  escalation rule, or the `stale_requires_operator_action` waiting semantics;
- change `system_status`, `system_blocked`, `system_attention_required`,
  `evidence_required`, `allow_empty_lab`, or any CLI exit code, including the
  fail-closed `no_lane_evidence` exit `1` without `--allow-empty-lab`;
- weaken the all-absent fail-closed default into a "nothing to do" reading, or
  make an unseeded lane root appear healthy or actionable;
- emit a recommendation that names a mutation, submit, cancel, replace, close,
  liquidation, capital, or live action; the emitted aggregate token stays
  operator-gated and offline-unrunnable in the V5.38 planner, so the V5.39
  executor gains no new executable action from this change;
- introduce an import of `os`, `socket`, `urllib`, `requests`, `httpx`, or any
  broker SDK, any wall-clock read, or any credential/profile load into the
  supervisor module; or
- alter the fixed false safety booleans, `paper_lab_only`,
  `not_live_authorized`, or `profit_claim=none` on any record.

## Verification Contract

Credential-free offline tests must prove:

1. an all-absent lab reports
   `recommended_next_action == "all_lanes_absent_run_lane_commands_to_seed_evidence"`
   with `recommended_next_action_lane == ""`, while retaining
   `system_status=no_lane_evidence`, `evidence_required=true`, and all-false
   safety booleans;
2. the same all-absent lab with `allow_empty_lab=true` keeps the aggregate
   recommendation (the assertion changes `evidence_required`, not the remedy);
3. a lab with exactly one seeded lane recommends that lane, not the aggregate
   token, and never names an `absent` lane while another lane has evidence;
4. severity ordering and registry-order tie-breaking for non-`absent` lanes are
   unchanged, including the existing blocked/attention/waiting/stale lane
   expectations;
5. the exported fallback constant is classified by the V5.38
   `AUTONOMY_ACTION_CLASSIFICATION` registry as not offline-runnable, so the
   supervisor and planner cannot drift;
6. the standalone `autonomy-supervisor-status` CLI still exits `1` on an
   all-absent lane set without `--allow-empty-lab` and `0` with it, and renders
   the aggregate recommendation with an empty recommendation lane in both text
   and JSON; and
7. `tests/unit/test_autonomy_supervisor.py`,
   `tests/unit/test_autonomy_next_plan.py`,
   `tests/unit/test_dependency_direction.py`, and the full offline verifier
   remain credential-free, network-free, broker-free, mutation-free, order-free,
   and trading-free.

## Documentation Contract

`docs/design/v5_37_offline_cross_lane_autonomy_supervisor.md`,
`docs/deterministic_core.md`, and `docs/OPERATOR_RUNBOOK.md` each state that the
recommended action comes from the highest-severity lane. Each must record the
all-absent exception: no lane is named and the whole-system seeding
recommendation is emitted instead.

## Review And Operator Route

An independent reviewer must inspect the exact implementation commit on top of
the accepted base. No operational action follows from this contract or its
implementation: the supervisor remains read-only, the all-absent case remains
fail-closed by default, and per-lane seeding remains operator-driven.
