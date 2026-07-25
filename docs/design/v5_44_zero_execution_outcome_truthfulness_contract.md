# V5.44 Zero-Execution Outcome Truthfulness Contract

## Status And Scope

- Milestone: `V5.44 — zero-execution outcome truthfulness in the gated offline
  autonomy executor and self-refresh cycle`.
- Parent milestones: `V5.39 — gated offline autonomy executor`
  (`docs/design/v5_39_gated_offline_autonomy_executor.md`) and
  `V5.42 — offline autonomy self-refresh cycle`
  (`docs/design/v5_42_offline_autonomy_self_refresh_cycle.md`).
- Recorded as deferred, out-of-scope work in two prior contracts:
  `docs/design/v5_38a_planner_state_vocabulary_fail_closed_contract.md`
  ("Out Of Scope, Recorded") and
  `docs/design/v5_42a_whole_system_rollup_truthfulness_contract.md`
  ("Out Of Scope (recorded, not repaired)").
- Accepted implementation base: `135da69` on
  `worktree-v544-zero-execution-truthfulness`, forked from the accepted
  `V5.43` main/frontier reconciliation.
- This contract authorizes offline implementation and verification only. It
  grants no credential read, network access, broker access, paper mutation,
  order operation, scheduler operation, capital allocation, or trading
  effect. Neither module gains a subprocess call, an import, or an
  executable path it does not already have.

## Deterministic Defect Evidence

`build_offline_execution_ledger` in
`src/algotrader/execution/autonomy_offline_executor.py` computes:

```python
execution_count = len(executed)
all_succeeded = all(record["exit_code"] == 0 for record in executed)
```

Python's `all()` over an empty iterable returns `True`. Whenever
`execution_count == 0`, `all_executions_succeeded` is `True` by construction,
regardless of *why* zero commands ran. Three distinct, independently
reachable causes collapse into that one vacuous `True`:

1. **Dry run** (`apply=False`, the default). `executed` is never populated
   in this branch, so every dry-run ledger reports
   `all_executions_succeeded=true` alongside `dry_run=true`. `apply` and
   `dry_run` already disambiguate this case for a careful reader, and the
   V5.39 CLI (`src/algotrader/cli.py:6170`) already gates on
   `eligible_count` rather than the succeeded flag for a dry run, so this
   cause is currently harmless but still shares the same misleading field
   value.
2. **Genuine no-op** (`apply=True`, preflight passes, `eligible_count == 0`).
   Nothing needed to run and nothing failed. This is the state the current
   lane registry always reaches today — proven by
   `test_allowlisted_actions_are_unreachable_from_current_lane_registry` in
   `tests/unit/test_autonomy_offline_executor.py`, which shows no lane's
   `next_actions` maps to the sole `AUTONOMY_EXECUTOR_ALLOWLIST` entry,
   `rerun_offline_daily_cycle_chain`. `all_executions_succeeded=true` is a
   defensible claim here, but only vacuously: nothing was attempted, so
   "succeeded" is not really a fact about anything that happened.
3. **Preflight refusal** (`apply=True`, `preflight_ok=False`). Execution was
   refused for a safety reason — a paper/live profile or a credential/
   network-test variable was loaded — and `execution_refused_reason` is set
   to `"preflight_failed"`. `all_executions_succeeded` still reports `true`
   here. This is the sharpest case: a caller reading only the boolean, not
   the accompanying `execution_refused_reason` string, sees a field that
   spells `true` next to a *safety refusal*, which is the opposite of a
   trustworthy signal. This state is reachable independently of lane
   registry inertness (`test_apply_refuses_when_preflight_fails` in the same
   file), and independently of `eligible_count`.

`autonomy_self_refresh_cycle.build_self_refresh_cycle` inherits the same
value verbatim (`all_succeeded = bool(ledger["all_executions_succeeded"])`,
`autonomy_self_refresh_cycle.py:134`) and republishes it at the cycle's top
level. `_classify_outcome` (`autonomy_self_refresh_cycle.py:193`) currently
reads `execution_count == 0` *before* it ever consults `all_succeeded`, so no
`cycle_outcome` is presently corrupted by the vacuous value — this matches
what the two prior contracts recorded. But the raw ledger field, and the
cycle's copy of it, are both published in the JSON/text record schema and
are not merely internal classification inputs; an external consumer of
either record (an operator, a log scraper, a future automation layer) can
read `all_executions_succeeded=true` directly and reasonably conclude
"nothing went wrong," which is not always true of cause 3 above.

## Design Question And Resolution

The recorded next action asked whether zero executions needs a distinct
not-applicable/unknown representation, or an explicit `false`.

**`false` is rejected.** Zero executions is not a failure. Encoding it as
`false` would replace one misleading claim ("everything that ran
succeeded," vacuously true) with another ("something failed," which did
not happen — nothing was even attempted). `false` would also collide with
cause 3 in a confusing way: a caller cannot tell `false` meaning "an
executed command exited non-zero" apart from `false` meaning "no command
was even attempted," which is a strictly worse loss of information than the
status quo for exactly the case (preflight refusal) this contract is most
concerned with.

**A distinct not-applicable representation is adopted.** `all_executions_succeeded`
becomes tri-state: `True`, `False`, or `None`.

- `None` ("not applicable") if and only if `execution_count == 0` — no
  command was executed, for any reason (dry run, genuine no-op, or preflight
  refusal alike). The three causes remain distinguishable from each other
  through the fields that already exist for that purpose
  (`apply`/`dry_run`, `eligible_count`, `execution_refused_reason`); this
  contract does not ask the boolean to do that disambiguation.
- `True` or `False`, exactly as today, if and only if `execution_count > 0`
  — computed from the real exit codes of the commands that actually ran.
  This branch is unchanged.

This is the same shape of fix already accepted twice in this codebase for
adjacent problems: `AUTONOMY_SUPERVISOR_STATES`/`_system_rank` refuse to
default an unrankable status rather than silently pick one course, and
`_classify_outcome` refuses to guess at an unranked status. Representing
"no claim can honestly be made" as a third value rather than forcing a
binary answer is the established fail-closed idiom here, not a new one.

## Required Behavior

1. `build_offline_execution_ledger` must compute `all_executions_succeeded`
   as `None` when `executed` is empty, and as
   `all(record["exit_code"] == 0 for record in executed)` (a real `bool`)
   when `executed` is non-empty. `execution_count == 0` and
   `all_executions_succeeded is None` must be equivalent for every ledger
   this module can produce.
2. `build_self_refresh_cycle` must forward that tri-state value verbatim —
   not coerce it with `bool(...)` — into its own top-level
   `all_executions_succeeded` field, preserving the same
   `execution_count == 0 <=> value is None` equivalence at the cycle level.
3. `_classify_outcome`'s `all_succeeded` parameter accepts `bool | None`.
   Because it already returns `OUTCOME_NOOP_NO_ACTION` for
   `execution_count == 0` before it reads `all_succeeded`, the only branch
   that inspects the value is reached exclusively when `execution_count > 0`
   — where the contract guarantees a real `bool`, never `None`. That branch
   must test `all_succeeded is not True` rather than `not all_succeeded`, so
   that if the producer invariant above is ever violated (a future defect
   lets `None` reach this branch with `execution_count > 0`), the cycle
   fails closed to `OUTCOME_EXECUTION_FAILED` instead of silently treating
   an absent claim as success.
4. `OUTCOME_NOOP_NO_ACTION` classification is unchanged: it is still
   selected purely by `execution_count == 0` after the `apply` and
   `evidence_required` checks, independent of the new tri-state value.
5. `execution_preflight`, `CREDENTIAL_PREFLIGHT_ENV_KEYS`,
   `execution_refused_reason`, `evidence_required`, `converged`, and every
   existing exit-code and fail-closed branch in `cli.py`'s
   `_run_autonomy_apply_plan`/`_run_autonomy_self_refresh_cycle` are
   unchanged in behavior. The CLI's existing
   `payload["execution_count"] > 0 and not payload["all_executions_succeeded"]`
   guards are updated to the same `is not True` fail-closed comparison as
   (3) for consistency, with no observable change to any exit code, since
   both guards are already short-circuited by `execution_count > 0`.
6. Text rendering (`render_offline_execution_ledger_text`,
   `render_self_refresh_cycle_text`) must render the tri-state value
   distinctly from `true`/`false` — as `not_applicable` — rather than
   silently rendering `None` as `false` through the shared boolean-only
   `_bool_text` helper. Every other rendered boolean field is unaffected.
7. JSON rendering needs no code change: `None` already serializes to JSON
   `null` through the existing `json.dumps`/`_json_safe` path, and `null` is
   a value already tri-state-safe for any consumer that inspects the parsed
   type before branching.

## Safety Invariants

The repair must not:

- change any lane's classification, gate, gate detail, command, required
  operator inputs, or preconditions;
- change `AUTONOMY_EXECUTOR_ALLOWLIST`, the eligible/skip partition, the
  documented executor inertness, or any `plan_class`/`cycle_outcome` value
  reachable from the current lane registry;
- change `evidence_required`, `converged`, `allow_empty_lab` semantics, or
  the `no_lane_evidence` fail-closed default;
- change any exit code the CLI currently returns for any input this
  contract's test matrix or the existing suites exercise;
- introduce an import of `os`, `socket`, `subprocess` (beyond the executor's
  existing, already-reviewed use), `urllib`, `requests`, `httpx`, or any
  broker SDK, any wall-clock read, or any credential/profile load into
  either module; or
- alter the fixed `False` safety booleans, `paper_lab_only`,
  `not_live_authorized`, or `profit_claim=none` on any record.

## Verification Contract

Credential-free offline tests must prove:

1. `build_offline_execution_ledger(..., apply=False)` (dry run) reports
   `all_executions_succeeded is None`.
2. `build_offline_execution_ledger(..., apply=True)` against a clean
   checkout (no eligible actions, preflight passes) reports
   `all_executions_succeeded is None` with `execution_count == 0` and
   `execution_refused_reason == ""`.
3. `build_offline_execution_ledger(..., apply=True)` under a loaded profile
   or credential variable reports `all_executions_succeeded is None` with
   `execution_count == 0` and `execution_refused_reason == "preflight_failed"`.
4. `build_offline_execution_ledger(..., apply=True)` with at least one
   eligible action still reports a real `bool` — `True` when every executed
   command exits `0`, `False` when any does not — unchanged from today.
5. `build_self_refresh_cycle` forwards the same tri-state value at its own
   top level for the dry-run, no-op, and preflight-refusal cases, and a real
   `bool` for the executed-action cases, mirroring (1)-(4).
6. `_classify_outcome` still returns `OUTCOME_NOOP_NO_ACTION` for every
   `execution_count == 0` case regardless of the (now `None`)
   `all_succeeded` value, and still returns `OUTCOME_EXECUTION_FAILED` for
   `execution_count > 0` with `all_succeeded=False`, and additionally
   returns `OUTCOME_EXECUTION_FAILED` (fail closed) for the contract-violating
   combination `execution_count > 0` with `all_succeeded=None`.
7. `render_offline_execution_ledger_text` and `render_self_refresh_cycle_text`
   render `all_executions_succeeded: not_applicable` for every
   `execution_count == 0` case and `true`/`false` unchanged for
   `execution_count > 0`.
8. `render_offline_execution_ledger_json` and `render_self_refresh_cycle_json`
   round-trip `all_executions_succeeded` as JSON `null` for every
   `execution_count == 0` case, and as JSON `true`/`false` unchanged for
   `execution_count > 0`.
9. The CLI exit codes for `autonomy-apply-plan` and
   `autonomy-self-refresh-cycle` are unchanged across the existing dry-run,
   clean-checkout-apply, preflight-refusal, and no-lane-evidence test cases.
10. The full existing `test_autonomy_offline_executor.py` and
    `test_autonomy_self_refresh_cycle.py` suites pass with no regressions,
    and `tests/unit/test_dependency_direction.py` and the offline verifier
    remain credential-free, network-free, broker-free, mutation-free,
    order-free, and trading-free.

## Documentation Contract

- `docs/design/v5_38a_planner_state_vocabulary_fail_closed_contract.md` and
  `docs/design/v5_42a_whole_system_rollup_truthfulness_contract.md` are not
  edited: their "Out Of Scope" sections correctly recorded a then-open item
  and remain accurate historical record of that decision; this document is
  the promised follow-up, not a correction to either.
- `docs/design/v5_39_gated_offline_autonomy_executor.md` and
  `docs/design/v5_42_offline_autonomy_self_refresh_cycle.md` are not edited
  by this contract: neither currently states `all_executions_succeeded`'s
  type or vacuous-true behavior, so neither makes a claim this repair
  falsifies. A future editor extending either document's field reference
  should describe the tri-state value this contract defines.
- `docs/agent_context/active_implementation.md` is updated in place, per the
  standing one-file mutable-handoff rule, to record this contract's
  acceptance and the resulting next action.

## Review And Operator Route

An independent reviewer must inspect the implementation commit against this
contract on top of `135da69`. No operational action follows: the executor's
documented inertness is untouched, no new lane action becomes reachable, and
the change only replaces a vacuously-true claim with an explicit
not-applicable value in a record schema that already existed.
