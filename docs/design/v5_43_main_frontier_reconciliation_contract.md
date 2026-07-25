# V5.43 Main/Frontier Reconciliation Contract

## Purpose

`origin/main@6b5dde6` and this branch's accepted autonomy frontier
(`0917083`, carrying V5.37/V5.37a/V5.38a/V5.42/V5.42a) diverged from a common
ancestor `82b1e07` (V5.41a). Neither side has the other's work. This contract
is frozen *before* any conflict is resolved, per the two-stage rule, so
resolution follows a predetermined rule rather than ad hoc judgment made while
editing.

## Read-Only Audit Evidence

- Merge base: `82b1e07f7dfda5ec9e289cfe196bbd4456c3ae0b` (V5.41a).
- Frontier-only commits (`origin/main..HEAD`): 21, from `38b9083` (V5.42 Stage
  3) through `0917083` (accept V5.42a), including V5.37, V5.37a, V5.38a,
  V5.42, V5.42a and their handoffs.
- Main-only commits (`HEAD..origin/main`): 7 — `9b56e9e` (docs), `9f3d77a`
  (V5.41b contract), `3fa2acb` (V5.41b implementation), `c25e509` (Windows
  `find.exe` test pin), `572de3f` (docs), `ba92ca7` (V5.40a secure-provider
  interlock), `6b5dde6` (docs).
- `git merge-tree --write-tree origin/main HEAD` conflicts in exactly 7 files:
  `docs/OPERATOR_RUNBOOK.md`, `docs/agent_context/active_implementation.md`,
  `docs/design/v5_37_offline_cross_lane_autonomy_supervisor.md`,
  `scripts/run_autonomy_supervisor.ps1`, `src/algotrader/cli.py`,
  `src/algotrader/execution/autonomy_supervisor.py`,
  `tests/unit/test_autonomy_supervisor.py`.
- 4 main-only files auto-merge cleanly with no conflict and are gained
  as-is: `src/algotrader/execution/crypto_history_refresh_adapter.py`,
  `tests/unit/test_v535_secure_dispatcher.py`,
  `docs/design/v5_40_live_capital_interlock_contract.md`,
  `tests/unit/test_run_daily_paper_lab_cycle_script.py` (V5.40a capability,
  zero semantic overlap with the autonomy-supervisor surface).
- `src/algotrader/execution/autonomy_next_plan.py`,
  `src/algotrader/execution/autonomy_offline_executor.py`,
  `src/algotrader/execution/autonomy_self_refresh_cycle.py`, and
  `docs/deterministic_core.md` are untouched by any main-only commit: V5.38a
  and the V5.42a self-refresh-cycle findings (Findings 2 and 3) face zero
  merge risk.

## Root Cause Of Every Conflict

Both lineages independently repaired the identical defect: the standalone
`autonomy-supervisor-status` supervisor read an all-absent lane set as
healthy. Main's route was V5.41b (`3fa2acb`, contract `9f3d77a`). Frontier's
route was V5.37 (`f3a9757`, initial fail-closed) refined by V5.42a Finding 1
(`c828307`, binding `evidence_required` to `system_attention_required`).
Both land on the same observable contract:

| Behavior | Main V5.41b | Frontier V5.37+V5.42a |
| --- | --- | --- |
| `evidence_required` on all-absent, undeclared | `True` | `True` |
| `system_attention_required` on all-absent, undeclared | `True` | `True` |
| `system_no_lane_evidence` in `aggregate_blockers` | present | present |
| Exit code, undeclared | `1` | `1` |
| `--allow-empty-lab` / `-AllowEmptyLab` flag name | identical | identical |
| Exit code, declared | `0` | `0` |
| `system_blocked` reserved for a blocked lane only | yes | yes |

The two implementations differ only in **wiring**, not in observable
contract: main added `allow_empty_lab` as a field on
`AutonomySupervisorConfig` (validated by a `_strict_bool` helper it added);
frontier threads `allow_empty_lab` as an explicit keyword parameter to
`build_autonomy_supervisor_report` / `build_autonomy_supervisor_report_from_records`
/ `_aggregate` (validated by its existing `_bool` helper). A naive textual
merge auto-resolves most of this file with no conflict marker at all — and in
doing so silently grafts main's unused `allow_empty_lab` config field onto
frontier's dataclass (dead: nothing reads `config.allow_empty_lab`) and
duplicates the `"allow_empty_lab"` / `"evidence_required"` dict-literal
insertion into the aggregate payload at two different positions. Checkout
evidence (a scratch `git merge-tree` trial), not either side's narrative,
is what exposed this; it must be treated as part of the conflict set even
though `git` does not mark it.

## Resolution Rule (Frozen Before Any Edit)

1. **API shape: frontier wins outright.** `AutonomySupervisorConfig` gains no
   `allow_empty_lab` field. `allow_empty_lab` remains solely a keyword
   parameter on the two report builders and on `_aggregate`. Main's
   `_strict_bool` helper is dropped; frontier's `_bool` helper is the sole
   validator. Rationale: two authorities for one boolean is a strictly worse
   contract than one, and frontier's shape is what V5.42a's own fixes
   (Findings 1-3) and every existing frontier test already depend on.
2. **Silent auto-merge artifacts are conflicts too.** The duplicated
   `"allow_empty_lab"` / `"evidence_required"` dict-key insertion and the
   dead config field must be removed by hand even where `git` reports no
   conflict marker, restoring `src/algotrader/execution/autonomy_supervisor.py`
   to be textually identical to its current frontier (`HEAD`) content — main
   contributes no net new line to this file, only confirms frontier's
   content is correct.
3. **`src/algotrader/cli.py`, `scripts/run_autonomy_supervisor.ps1`:**
   resolve to `HEAD` (frontier) content. Functional argument wiring is
   already identical on both sides; only prose/comment wording differs, and
   `HEAD`'s wording is the more precise of the two (states the exit code
   explicitly).
4. **Docs (`docs/OPERATOR_RUNBOOK.md`,
   `docs/design/v5_37_offline_cross_lane_autonomy_supervisor.md`):** resolve
   to `HEAD` (frontier) prose, which is the accurate superset (covers V5.37a
   aggregate recommendation, the actionable-vs-operator-gated stale split,
   and the V5.42a rollup-truthfulness amendment that main's side never made).
   Append one provenance sentence noting that `main`'s V5.41b
   (`docs/design/v5_41b_standalone_supervisor_empty_lab_contract.md`, gained
   whole from `origin/main`) independently reached the identical
   `evidence_required`/`system_attention_required`/`system_no_lane_evidence`
   fix, as corroborating evidence rather than a competing claim.
5. **`tests/unit/test_autonomy_supervisor.py`:** resolve to `HEAD` (frontier)
   as the base — it already exercises this contract end to end against the
   retained API. Port exactly 5 main-only tests that assert scenarios
   frontier's suite does not otherwise cover, rewritten against the
   retained (frontier) API:
   - `test_declared_empty_lab_does_not_rescue_a_blocked_lane`
   - `test_declared_empty_lab_does_not_rescue_an_unknown_lane`
   - `test_both_report_builders_agree_on_empty_lab_flag`
   - `test_text_render_surfaces_empty_lab_contract`
   - `test_cli_declared_empty_lab_still_fails_on_blocked_lane`
   Do not port `test_declared_empty_lab_clears_evidence_required` (duplicate
   of `test_no_lane_evidence_allows_explicit_empty_lab`),
   `test_allow_empty_lab_rejects_non_bool` (duplicate of
   `test_rejects_non_bool_allow_empty_lab`), or any other main-only test
   whose assertion is already made by an existing frontier test — added
   coverage must be net new, not duplicated.
6. **`docs/agent_context/active_implementation.md`:** resolve the merge
   commit itself to `HEAD` content (this branch's own accepted handoff); it
   is overwritten in a separate, later commit with the final reconciliation
   handoff regardless, per the standing one-file-handoff rule.
7. **Everything else main-only** (V5.40a's
   `crypto_history_refresh_adapter.py` change, its test, its contract doc,
   and the `find.exe` test pin): take as-is. Zero semantic overlap with the
   autonomy-supervisor surface; this is a pure capability gain.
8. **No rebase, reset, clean, stash, restore, or branch switch.** Resolution
   happens inside a normal `git merge origin/main` (non-fast-forward, no
   `--ff-only`) on this branch, producing one merge commit that preserves
   both histories.

## Acceptance Matrix

Preserved (must remain true after merge, proven by the named test):

| Contract | Proof |
| --- | --- |
| V5.37a: all-absent lanes recommend whole-system seeding, not one lane | `test_all_lanes_absent_recommends_whole_system_seeding`, `test_absent_lane_is_never_recommended_while_evidence_exists` |
| V5.38a: planner fails closed on an unrankable caller-supplied lane state | full `tests/unit/test_autonomy_next_plan.py` (file untouched by any main-only commit — zero merge risk) |
| V5.42a Finding 1: `evidence_required` implies `system_attention_required` and the `system_no_lane_evidence` blocker | `test_evidence_required_implies_attention_and_blocker` |
| V5.42a Finding 2: `no_lane_evidence` ranks most severe in `_SYSTEM_SEVERITY` | `tests/unit/test_autonomy_self_refresh_cycle.py` (file untouched by any main-only commit — zero merge risk) |
| V5.42a Finding 3: unrankable system status fails closed via `AUTONOMY_SUPERVISOR_SYSTEM_STATUSES` | `test_system_status_vocabulary_is_exactly_the_exported_tuple`, self-refresh-cycle severity-resolution tests |
| Main V5.41b: empty-lab declaration never rescues a blocked or unknown lane | ported `test_declared_empty_lab_does_not_rescue_a_blocked_lane`, `test_declared_empty_lab_does_not_rescue_an_unknown_lane` |
| Main V5.41b: both report builders agree on the empty-lab flag | ported `test_both_report_builders_agree_on_empty_lab_flag` |

Gained (main-only capability now present on this branch):

| Capability | Source |
| --- | --- |
| V5.40a secure-provider interlock profile conflict resolution in `crypto_history_refresh_adapter.py` | `ba92ca7`, proven by `tests/unit/test_v535_secure_dispatcher.py` |
| Windows `find.exe`-pinned daily paper-lab shim test | `c25e509` |
| V5.41b standalone-supervisor empty-lab contract doc (historical/provenance) | `9f3d77a` |

Explicitly not a gate for this reconciliation: milestone-number duplication
between the two lineages (main's V5.40a/V5.41b vs. this branch's
V5.37/V5.37a/V5.38a/V5.42a numbering both existing for related but distinct
subject matter). A textual conflict is not itself an operator gate under this
task's instructions; every conflict enumerated above is resolved by the rule
in this contract, not escalated.

## Verification Required After Resolution

- `tests/unit/test_autonomy_supervisor.py` +
  `tests/unit/test_autonomy_self_refresh_cycle.py`
- `tests/unit/test_autonomy_next_plan.py` +
  `tests/unit/test_autonomy_offline_executor.py` +
  `tests/unit/test_verify_offline_script.py`
- `tests/unit/test_v535_secure_dispatcher.py` +
  `tests/unit/test_run_daily_paper_lab_cycle_script.py`
- `tests/unit/test_dependency_direction.py`
- `.\scripts\verify_offline.ps1`
- `.\scripts\verify_offline.ps1 -Full`
- `git diff --check`; `git status --short`; `git diff --name-only HEAD -- src`;
  `git ls-files --others --exclude-standard src tests`

## Safety

This contract changes no credential path, network path, broker path,
scheduler path, paper mutation, order action, or live authority. It resolves
a reporting-surface merge only. Default tests remain offline, deterministic,
credential-free, network-free, and broker-free throughout.
