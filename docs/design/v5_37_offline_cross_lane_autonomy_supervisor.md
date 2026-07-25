# V5.37 Offline Cross-Lane Autonomy Supervisor Contract

## Purpose

The repository now runs several independent autonomy lanes, each of which fails
closed on its own and writes its own local evidence artifact. There was no
single offline command that reported the state of the whole system, what each
lane is blocked or waiting on, and the one next eligible action per lane. An
operator or orchestrator had to poll many lane-specific status commands to know
whether the system was healthy or silently stalled. That manual polling burden
is the binding constraint on supervisable end-to-end autonomy.

V5.37 adds one deterministic, offline supervisor that reads the local latest
evidence artifact for each known lane, normalizes each lane's declared state
into a strict supervisory vocabulary, computes staleness against an explicit
caller `as_of`, and aggregates one whole-system readiness record. It is a
read-only reporting surface. It grants no new authority.

## Non-Negotiable Safety Contract

- The supervisor reads only caller-supplied or default-located local files.
- It loads no runtime profile, reads no environment variable, and inspects no
  credential.
- It imports no broker SDK, constructs no broker client, and opens no socket or
  network connection.
- It reads no wall clock. All time comparisons use the explicit `as_of` input,
  keeping the output deterministic.
- It performs no submit, cancel, replace, close, liquidation, paper mutation,
  capital allocation, or live action, and exposes no seam that could.
- Every emitted record carries `submitted`, `mutated`, `broker_action_performed`,
  `broker_actions_performed`, `broker_mutation_allowed`,
  `network_access_attempted`, `credential_access_attempted`, and
  `live_authorized` fixed to `false`, plus `profit_claim=none` and the labels
  `paper_lab_only` and `not_live_authorized`.
- Missing, unreadable, or ambiguous artifacts fail closed. The supervisor never
  invents a healthy or actionable lane state from absent or malformed evidence.

## Module And Command Surface

- Module: `src/algotrader/execution/autonomy_supervisor.py`.
- CLI: `python -m algotrader.cli autonomy-supervisor-status`.
- Wrapper: `scripts/run_autonomy_supervisor.ps1`.
- The module is pure: `build_autonomy_supervisor_report(config, *, allow_empty_lab=False)`
  reads local artifacts; `build_autonomy_supervisor_report_from_records(config,
  records, *, allow_empty_lab=False)` accepts already-parsed latest records for
  deterministic evaluation and tests. `allow_empty_lab` is keyword-only and
  defaults to `False`, so every existing caller (`autonomy-next-plan`,
  `autonomy-self-refresh-cycle`) keeps its prior fail-closed behavior for
  `no_lane_evidence` unless it explicitly opts in.
- Rendering is deterministic: `render_autonomy_supervisor_json` emits one
  sorted-key newline-free object; `render_autonomy_supervisor_text` emits a
  compact operator summary; `write_autonomy_supervisor_jsonl` writes exactly one
  newline-terminated record, replacing any prior file contents.
- CLI flag: `--allow-empty-lab` (wrapper: `-AllowEmptyLab`) forwards to
  `allow_empty_lab`; see "Whole-System Rollup" below for the exact exit-code
  contract.

## Normalized State Vocabulary

Each lane resolves to exactly one normalized state, ordered most to least
severe:

- `blocked` — lane reached a blocked or failed state, its artifact is
  unreadable, or a safety boolean in its record was not `false`.
- `unknown` — a state value was present but is not in the lane's declared
  vocabulary and carries no cautionary token, or no state field was present.
- `attention_required` — lane reached an operator-review or decision point, or
  its record set `operator_action_required=true`.
- `stale` — a `nominal` or `waiting` lane whose latest evidence is older than
  its declared `max_age_hours` relative to `as_of` (staleness disabled when
  `max_age_hours=0`).
- `waiting` — lane is healthily waiting on wall-clock time or upstream evidence.
- `nominal` — lane's latest evidence is accepted or healthy and fresh.
- `absent` — no evidence artifact is present for the lane yet.

An unmapped raw state that contains a cautionary token (`blocked`, `failed`,
`error`, `conflict`) fails closed to `blocked`. Any other unmapped value
normalizes to `unknown`. Staleness and safety escalations can only move a lane
toward more attention, never toward `nominal`.

## Whole-System Rollup

`system_status` is derived from the per-lane counts:

- any `blocked` lane → `blocked`
- else any `unknown`, `attention_required`, or `stale` lane → `attention_required`
- else any `waiting` lane → `waiting`
- else any `nominal` lane → `nominal`
- else (all `absent`) → `no_lane_evidence`

`recommended_next_action` is taken from the highest-severity lane that has
evidence, breaking ties by registry order. `absent` lanes are excluded from that
selection, so an absent lane is never recommended while another lane has
evidence. When *every* lane is `absent` there is no lane to name: the report
carries `recommended_next_action_lane=""` and the whole-system aggregate action
`all_lanes_absent_run_lane_commands_to_seed_evidence` (exported as
`ALL_LANES_ABSENT_ACTION`, classified operator-gated by the V5.38 planner), so a
lab with nothing seeded is not answered with one arbitrary lane's seeding
instruction. See
`docs/design/v5_37a_all_absent_aggregate_recommendation_contract.md`.

An all-absent lane set (`no_lane_evidence`) fails closed by default: the report
carries `evidence_required=true` and the `autonomy-supervisor-status` CLI exits
`1`, so an empty or wrong `--lanes-root` cannot read as healthy to an unattended
caller. A caller that intentionally runs against a fresh, not-yet-seeded lab may
pass `--allow-empty-lab` (`build_autonomy_supervisor_report(..., allow_empty_lab=True)`
at the library level; `-AllowEmptyLab` on the PowerShell wrapper) to record that
assertion explicitly on the report (`allow_empty_lab=true`,
`evidence_required=false`) and receive exit `0` for that case. This mirrors the
V5.42 self-refresh cycle's `allow_empty_lab` exception (see
`docs/design/v5_42_offline_autonomy_self_refresh_cycle.md`).

The command exits `0` for `nominal` and `waiting`; `0` for `no_lane_evidence`
only when `--allow-empty-lab` is passed (otherwise `1`); `1` for
`attention_required` and `blocked`; and `2` on input validation error.

## Frozen Lane Registry

`AUTONOMY_SUPERVISOR_LANES` is the frozen classification contract. Each lane
declares a default artifact path under the local `runs` root, a reader kind, the
candidate state field names (first present wins), candidate `as_of` fields for
staleness, a `max_age_hours` threshold, an explicit raw-value-to-normalized-state
map, per-state next actions, and blocker fields to surface. Default paths are
best-effort canonical locations; a missing default simply reads `absent`, and an
operator or wrapper may point a lane at its exact latest artifact with a
`--lane LANE_ID=PATH` override.

| lane_id | state field(s) | key raw values → normalized |
| --- | --- | --- |
| `spy_market_data_soak` | `evidence_state` | `accepted_unattended_market_data_soak`→nominal; `collecting_unattended_market_data_soak`→waiting; `blocked_latest_expected_session_not_accepted`→blocked |
| `spy_offline_daily_cycle` | `daily_chain_state`/`daily_wrapper_state`/`validation_state`/`state_rollup_status` | `accepted_observe_hold_noop`→nominal; `review_only`→nominal |
| `crypto_supervised_readiness_trial` | `trial_classification` | `accepted`→nominal (R1) |
| `crypto_forward_shadow_cycle` | `classification` | `waiting_for_tournament_terminal`/`state_initialization_required`→waiting; `market_data_refresh_ready`→attention |
| `crypto_bounded_paper_probe_review` | `classification` | `waiting_for_v5_25_terminal_evidence`→waiting; `eligible_for_operator_review_only`→attention; `blocked_by_operational_evidence`→blocked |
| `crypto_capability_production` | `classification` | `candidate_deferred_pending_terminal_winner`→waiting |

The `spy_market_data_soak` lane uses a 96-hour staleness bound so a stalled
unattended refresh task surfaces as `stale`. The research and probe lanes are
gated on wall-clock or upstream evidence and disable staleness
(`max_age_hours=0`) so healthy waiting is not misreported as stale.

## What This Milestone Does Not Do

- It does not replace, re-derive, or second-guess any lane's internal logic. It
  normalizes the state field each lane already writes.
- It does not fetch or generate lane evidence. In a clean checkout, all lanes
  read `absent`, which is the correct and safe default; lane commands must run
  first to seed evidence.
- It adds no strategy-performance evidence and changes no live-capital,
  paper-mutation, credential, network, or Task Scheduler authority.
- Its recommended next actions are always offline, read-only, or
  operator-review follow-ups. They never name a broker mutation.

## Verification

- Focused suite `tests/unit/test_autonomy_supervisor.py` proves absent, nominal,
  waiting, attention, blocked, unknown, stale, safety-flag, malformed-artifact,
  file-reading, determinism, config-validation, CLI exit-code, and source-scan
  (no forbidden import or call, including no clock read) behaviors.
- The targeted offline verifier (`scripts/verify_offline.ps1`) safety guards
  remain green with the module and CLI command in place.
