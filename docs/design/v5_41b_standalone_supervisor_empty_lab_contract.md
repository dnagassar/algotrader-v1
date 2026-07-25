# V5.41b Standalone Supervisor Fail-Closed Empty-Lab Contract

## Purpose

The V5.37 standalone cross-lane supervisor
(`autonomy-supervisor-status`) classifies an all-absent lane set as
`no_lane_evidence` and exits `0`. A scheduled invocation against a lab that
produced no evidence at all is therefore indistinguishable, by exit code and by
`system_attention_required`, from a healthy lab. That is a false green: the one
condition most likely to mean "the scheduled work never ran" is the condition
the command reports as fine.

V5.41b aligns the standalone supervisor with the fail-closed empty-lab contract
already defined for the self-refresh cycle: absence of evidence is a failure
unless the caller explicitly declares the empty lab intentional.

## Non-Negotiable Safety Contract

1. **Default fail-closed.** With no explicit declaration, a
   `no_lane_evidence` rollup sets `evidence_required` to `True`,
   `system_attention_required` to `True`, and exits `1`.

2. **Explicit empty lab.** The caller may declare an intentionally empty lab
   through `--allow-empty-lab` (`-AllowEmptyLab` in the wrapper). Only that
   explicit declaration returns `no_lane_evidence` to exit `0` with
   `evidence_required` `False`. The declaration is never inferred from the
   environment, from the lanes root, or from a prior run.

3. **Declaration is narrow.** `--allow-empty-lab` affects only the all-absent
   rollup. It never suppresses a `blocked`, `unknown`, `attention_required`,
   or `stale` lane, never changes lane normalization, staleness, or safety-flag
   escalation, and cannot move any lane or the system toward a healthier
   classification than the evidence supports.

4. **`system_blocked` is unchanged.** A missing-evidence system is
   `attention_required`, not `blocked`. `system_blocked` stays reserved for a
   `blocked` lane.

5. **Reporting-surface safety is unchanged.** The command remains offline,
   deterministic, credential-free, network-free, and broker-free. It reads no
   wall clock; `--as-of` remains the only time source. All safety booleans
   remain fixed `False`.

## Report Fields

| Field | Type | Description |
| :--- | :--- | :--- |
| `allow_empty_lab` | `bool` | Echo of the caller's explicit declaration. Default `False`. |
| `evidence_required` | `bool` | `True` when `system_status` is `no_lane_evidence` and `allow_empty_lab` is `False`. |

`system_attention_required` becomes
`system_status in ("blocked", "attention_required") or evidence_required`.

## Whole-System Rollup

`system_status` derivation is unchanged:

- any `blocked` lane → `blocked`
- else any `unknown`, `attention_required`, or `stale` lane → `attention_required`
- else any `waiting` lane → `waiting`
- else any `nominal` lane → `nominal`
- else (all `absent`) → `no_lane_evidence`

What changes is the disposition of the last case.

## CLI Exit Codes

- `0` — `nominal`, `waiting`, or `no_lane_evidence` with `--allow-empty-lab`.
- `1` — `attention_required`, `blocked`, or `no_lane_evidence` without
  `--allow-empty-lab`.
- `2` — input validation error.

## API and Module Surface

**Reconciliation note (V5.43):** this contract originally specified
`allow_empty_lab` as a field on `AutonomySupervisorConfig`. The V5.43
main/frontier reconciliation
(`docs/design/v5_43_main_frontier_reconciliation_contract.md`) instead
retained the frontier's keyword-argument interface, because the frontier's
V5.42 self-refresh cycle forwards `allow_empty_lab` into two supervisor
observations built from one shared config, and a config field would give
that value two independent homes with nothing binding them — the same defect
class V5.37a/V5.38a/V5.42a exist to close at other seams. The observable
contract below (exit codes, report fields, non-rescue guarantees) is
unchanged; only the surface below is corrected to match the code that is
actually in the repository.

- **Module**: `src/algotrader/execution/autonomy_supervisor.py`
- **API**: `allow_empty_lab: bool = False` is a keyword-only parameter on
  `build_autonomy_supervisor_report` and
  `build_autonomy_supervisor_report_from_records` (and on the internal
  `_aggregate`), validated as a strict `bool`. It is not a field on
  `AutonomySupervisorConfig`.
- **CLI**: `python -m algotrader.cli autonomy-supervisor-status [--allow-empty-lab]`
- **Wrapper**: `.\scripts\run_autonomy_supervisor.ps1 [-AllowEmptyLab]`

Both report builders (`build_autonomy_supervisor_report` and
`build_autonomy_supervisor_report_from_records`) honor the flag identically, so
an in-memory caller and a filesystem caller cannot disagree.

## Compatibility

`allow_empty_lab` defaults to `False`, so the behavior change is deliberate and
one-directional: a previously exit-`0` empty lab now exits `1` until an operator
either seeds evidence or declares the empty lab. No previously failing state
becomes passing.

`autonomy-next-plan` and `autonomy-apply-plan` consume `system_status` and
`recommended_next_action`, neither of which changes shape. Their behavior is
unaffected by this slice.

## Verification

`tests/unit/test_autonomy_supervisor.py` must prove:

1. all-absent without the flag → `evidence_required` `True`,
   `system_attention_required` `True`, `system_blocked` `False`;
2. all-absent with the flag → `evidence_required` `False`,
   `system_attention_required` `False`;
3. CLI exits `1` for an empty lab and `0` with `--allow-empty-lab`;
4. the flag does not rescue a blocked, unknown, or stale lane;
5. both report builders agree on the flag; and
6. the existing AST scan still proves no forbidden import or call.
