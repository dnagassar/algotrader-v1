# V5.42a Whole-System Rollup Truthfulness Contract

## Scope

This contract is frozen before implementation. It covers the whole-system
derived values of two modules only:

- `algotrader.execution.autonomy_supervisor` — the `_aggregate` rollup booleans
  and the system-status vocabulary it exports.
- `algotrader.execution.autonomy_self_refresh_cycle` — `_SYSTEM_SEVERITY` and
  the `cycle_outcome` improvement test that consumes it.

It adds no lane, command, action token, allowlist entry, executor authority,
credential path, network path, broker path, paper mutation, or live authority.
Per-lane classification, staleness, the action registry, the executor allowlist,
`converged`, and every exit code stay exactly as V5.37/V5.37a/V5.38a/V5.42 froze
them.

## Defect Class

This is the third instance of one class already repaired twice on this branch: an
**aggregate computed by one rule and a detail selected by another, with no guard
binding them**. V5.37a repaired it between the supervisor's `system_status` and
its `recommended_next_action`. V5.38a repaired it between the planner's
`plan_class` and its `next_offline_action`. The audit recorded as the V5.38a
next action swept the two remaining layers and found three more instances,
below.

## Finding 1 — `evidence_required` Does Not Imply Attention (live)

`_aggregate` computes `evidence_required` from `system_status ==
no_lane_evidence and not allow_empty_lab`, but computes
`system_attention_required` independently from `system_status in (blocked,
attention_required)`. `no_lane_evidence` is in neither tuple.

Reachable today with no override at all: a supervisor run against an empty or
wrong `lanes_root` emits

- `system_status = no_lane_evidence`
- `evidence_required = true`
- `system_attention_required = false`
- `aggregate_blockers = []`

The CLI exit code is correct (`1`, keyed off `evidence_required`), so the
false green is confined to the record — but the record is the artifact other
lanes, wrappers, and future consumers read. A consumer that asks the record's
own "does this need attention" boolean is told no, and a consumer that reads
`aggregate_blockers` is told nothing blocks. That is precisely the V5.37a shape:
the verdict and the remedy disagree.

### Required behaviour

1. `evidence_required` implies `system_attention_required`. The boolean becomes
   `system_status in (blocked, attention_required) or evidence_required`.
2. `evidence_required` contributes the aggregate blocker
   `system_no_lane_evidence`, so the blocker list is non-empty exactly when
   something blocks.
3. `system_status`, `system_blocked`, `evidence_required`, `allow_empty_lab`,
   the lane lists, `recommended_next_action`, `recommended_next_action_lane`,
   and every exit code are unchanged. A declared empty lab
   (`allow_empty_lab=true`) keeps `evidence_required=false`, therefore keeps
   `system_attention_required=false` and adds no blocker.
4. No previously passing state becomes failing, and no previously failing state
   becomes passing.

This is the same repair `main` landed independently as V5.41b (`3fa2acb`). This
contract adopts `main`'s semantics verbatim so the two lines converge instead of
diverging further; see Merge Interaction below.

## Finding 2 — `no_lane_evidence` Ranked As The Healthiest State (latent, wrong)

`_SYSTEM_SEVERITY` in the self-refresh cycle ranks `no_lane_evidence` at `0`,
strictly *less severe* than `nominal` at `1`. The map's only consumer is the
improvement test that separates `refreshed` from `still_pending`:

```
if after_rank < before_rank: return OUTCOME_REFRESHED
return OUTCOME_STILL_PENDING
```

Under that ranking, a cycle whose lane evidence *disappeared* between observe and
re-observe scores as the largest possible improvement. Every transition into
`no_lane_evidence` from any other status yields `cycle_outcome=refreshed`, and
the genuine improvement `no_lane_evidence -> nominal` yields `still_pending`.
Both are backwards.

The V5.42 contract asserts these paths "stay correct but are currently
unreachable". The unreachability is true (Finding 4). The correctness claim is
not, so the frozen document currently overstates what the code guarantees.

### Required behaviour

`no_lane_evidence` becomes the **most severe** rank. Rationale: a blocked lane is
evidence — the system knows what is wrong and can name it. `no_lane_evidence` is
the absence of any proof whatsoever, which is why V5.37/V5.42 already make it
fail closed. Ordering it first makes both directions correct by construction:

- any status `-> no_lane_evidence` can never report `refreshed` — losing
  evidence is not an improvement;
- `no_lane_evidence -> ` any other status reports `refreshed` — any evidence
  beats none.

Frozen severity order, most to least severe:

```
no_lane_evidence > blocked > attention_required > waiting > nominal
```

This order is a *severity* ranking for consumers. It is deliberately **not** the
supervisor's `_system_status` precedence, which walks lane counts in the order
blocked, attention, waiting, nominal and returns `no_lane_evidence` only as the
terminal fallback. The two orders answer different questions and must not be
conflated.

`converged` is not computed from this map and does not change: a declared empty
lab still converges, and no exit code moves.

## Finding 3 — The Severity Map Fails Open On An Unrankable Status (latent)

`_SYSTEM_SEVERITY` is a locally declared dict, read through
`_SYSTEM_SEVERITY.get(status, 0)`. A system status the supervisor can emit but
the map does not contain silently takes the default rank. Paired with Finding 2's
ordering that default was the healthiest rank; corrected, it would still be an
invented answer rather than a refusal.

The same module also re-declares `_CONVERGED_STATES` locally, and that one fails
*closed* on an unknown status (an unlisted status is simply not converged). One
module, one vocabulary, two opposite failure directions — the exact drift V5.38a
removed from the planner, where the fix was to consume the supervisor's exported
`AUTONOMY_SUPERVISOR_STATES` instead of a local copy and to reject an unrankable
value.

### Required behaviour

1. The supervisor exports `AUTONOMY_SUPERVISOR_SYSTEM_STATUSES`: the frozen
   whole-system status vocabulary, ordered most to least severe per Finding 2,
   and public for exactly the reason `AUTONOMY_SUPERVISOR_STATES` is.
2. A test proves that tuple is exactly the set of `SYSTEM_*` constants the
   module defines and exactly the set `_system_status` can return, so adding a
   status without ranking it fails the suite instead of degrading a consumer.
3. The cycle derives `_SYSTEM_SEVERITY` from that tuple rather than restating
   it, and resolves a rank through a helper that raises `ValidationError` on an
   unrankable status instead of defaulting. Fail closed, matching
   `_required_state` in the planner.
4. `_CONVERGED_STATES` keeps its current membership (`nominal`, `waiting`) and
   its current fail-closed behaviour; it is now stated against the exported
   vocabulary rather than an independent literal set.

## Finding 4 — Act-Phase Outcomes Unreachable (documented non-defect)

The recorded next action asked whether every `_classify_outcome` branch can be
produced from real evidence. Verified answer: `evidence_required`,
`dry_run_preview`, and `noop_no_action` are reachable; `execution_failed`,
`refreshed`, and `still_pending` are not.

Proof chain, all from the frozen registries: `AUTONOMY_EXECUTOR_ALLOWLIST` has
exactly one key, `rerun_offline_daily_cycle_chain`; no `next_actions` entry of
any lane in `AUTONOMY_SUPERVISOR_LANES` maps any normalized state to that token;
therefore `_partition_actions` yields an empty eligible set for every possible
lane artifact content, `execution_count` is always `0`, and `_classify_outcome`
always returns before reaching the three act-phase branches.

This is already documented in `v5_39_gated_offline_autonomy_executor.md` and
`v5_42_offline_autonomy_self_refresh_cycle.md` and asserted by an explicit
inertness test. It is not repaired here and requires no repair: the executor is
truthfully inert. Findings 2 and 3 make the unreachable code correct rather than
making it reachable, and add no executor authority.

## Out Of Scope (recorded, not repaired)

`all_executions_succeeded` is `all([])` — vacuously `true` when nothing executed.
The prior audit recorded this and deliberately deferred it; it remains deferred.
`_classify_outcome` tests `execution_count == 0` before reading the flag, so no
`cycle_outcome` depends on the vacuous value, and no change here touches it.

## Merge Interaction With `main`

`main@6b5dde6` already carries Finding 1's repair as V5.41b, with identical
semantics and the identical `system_no_lane_evidence` blocker token, reached
independently. After this slice both lines agree on the rollup booleans, which
removes one of the two overlapping edits in `autonomy_supervisor.py` recorded as
the standing reconciliation risk.

`main` does not carry Findings 2 and 3: it has no `autonomy_self_refresh_cycle.py`
at all. Those changes are additive from `main`'s perspective.

`main` also does not carry V5.37a or V5.38a. A merge that favours `main` in
`autonomy_supervisor.py` still silently reintroduces those two defects. This
contract narrows that risk; it does not close it, and the reconciliation remains
an operator sequencing decision.

## Verification Required

- Supervisor: an undeclared empty lab reports `evidence_required=true`,
  `system_attention_required=true`, and `system_no_lane_evidence` in
  `aggregate_blockers`; a declared empty lab reports all three as before
  (`false`, `false`, absent); a blocked or attention lane set is unchanged; a
  waiting or nominal lane set still reports `system_attention_required=false`.
- Vocabulary: `AUTONOMY_SUPERVISOR_SYSTEM_STATUSES` equals the `SYSTEM_*`
  constant set and covers every `_system_status` return.
- Cycle: `_SYSTEM_SEVERITY` is derived from the exported tuple; an unrankable
  status raises `ValidationError`; `no_lane_evidence` outranks `blocked`; a
  transition into `no_lane_evidence` never reports `refreshed`; the transition
  out of it to `nominal` reports `refreshed`; existing outcome parametrization
  still passes.
- Cycle/supervisor coherence: the cycle forwards `allow_empty_lab` into both
  supervisor observations so the embedded reports agree with the cycle's own
  declaration. Output-neutral today because `_report_summary` projects neither
  rollup boolean; it prevents the inconsistency from surfacing if that
  projection grows.
- Both focused suites, the planner and executor suites, dependency direction,
  and `.\scripts\verify_offline.ps1`.
- Safety: preflight booleans false; no credential, network, broker, scheduler,
  paper-mutation, order, or live path added.
