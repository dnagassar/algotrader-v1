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
- The module is pure: `build_autonomy_supervisor_report(config)` reads local
  artifacts; `build_autonomy_supervisor_report_from_records(config, records)`
  accepts already-parsed latest records for deterministic evaluation and tests.
- Rendering is deterministic: `render_autonomy_supervisor_json` emits one
  sorted-key newline-free object; `render_autonomy_supervisor_text` emits a
  compact operator summary; `write_autonomy_supervisor_jsonl` writes exactly one
  newline-terminated record, replacing any prior file contents.

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

`recommended_next_action` is taken from the highest-severity lane, breaking ties
by registry order. The command exits `0` for `nominal`, `waiting`, and
`no_lane_evidence`; `1` for `attention_required` and `blocked`; and `2` on input
validation error.

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
