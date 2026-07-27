# V5.38 Offline Autonomy Next-Action Planner Contract

## Purpose

The V5.37 cross-lane supervisor
(`docs/design/v5_37_offline_cross_lane_autonomy_supervisor.md`) answers *what
state is each autonomy lane in* and emits one abstract `recommended_next_action`
token per lane. It deliberately stops there: it never maps a token to a runnable
command, and it never separates an action that can be advanced inside the
offline envelope from one that is blocked on the operator. So after running the
supervisor, an operator or orchestrator still had to hand-translate every
recommendation into "is there a command I can run, what inputs does it need, or
is this blocked on me?" That translation was the binding constraint between
observing the system and acting on it.

V5.38 adds one deterministic, offline planner that consumes a supervisor report
and, for each lane, classifies the lane's declared `recommended_next_action`
against a frozen classification registry into a concrete plan: the exact offline
command to run (when one exists), the operator-supplied inputs it still
requires, its preconditions, and — when no offline path exists — the specific
operator gate that blocks autonomous progress. It then aggregates one
whole-system plan naming the single highest-leverage offline-runnable action and
the full set of operator-gated actions.

It is a read-only planning surface. It plans commands; it never executes them.
It grants no new authority.

## Non-Negotiable Safety Contract

- The planner reads only the local lane evidence the supervisor already reads
  (via `build_autonomy_next_plan`) or an already-built supervisor report (via
  `build_autonomy_next_plan_from_report`).
- It loads no runtime profile, reads no environment variable, and inspects no
  credential.
- It imports no broker SDK, constructs no broker client, opens no socket, and
  **spawns no subprocess**. It records command strings as inert data.
- It reads no wall clock. The evaluation time is the supervisor report's
  `as_of`, keeping output deterministic.
- It performs no submit, cancel, replace, close, liquidation, paper mutation,
  capital allocation, or live action, and exposes no seam that could.
- Every emitted record carries `submitted`, `mutated`, `broker_action_performed`,
  `broker_actions_performed`, `broker_mutation_allowed`,
  `network_access_attempted`, `credential_access_attempted`, and
  `live_authorized` fixed to `false`, plus `profit_claim=none` and the labels
  `paper_lab_only` and `not_live_authorized`.
- An unclassified action token fails closed to an operator-review gate. The
  planner never invents an offline-runnable path for an action it does not
  recognize.
- A lane's `normalized_state` is a hard input contract: it must be one of the
  supervisor's exported `AUTONOMY_SUPERVISOR_STATES`, and anything else is
  rejected with a `ValidationError` rather than planned. The planner ranks lanes
  by that exact exported vocabulary instead of a local copy, so a state the
  supervisor can emit can never be silently unrankable. See
  `docs/design/v5_38a_planner_state_vocabulary_fail_closed_contract.md`.

## Module And Command Surface

- Module: `src/algotrader/execution/autonomy_next_plan.py`.
- CLI: `python -m algotrader.cli autonomy-next-plan`.
- Wrapper: `scripts/run_autonomy_next_plan.ps1` (credential-free, refuses to run
  under a loaded profile or credential/network-test variable).
- The module is pure: `build_autonomy_next_plan(config)` builds the supervisor
  report internally and plans it; `build_autonomy_next_plan_from_report(report)`
  plans an already-built supervisor report for deterministic evaluation and
  tests; `classify_action(token)` exposes the single-token classification.
- Rendering is deterministic: `render_autonomy_next_plan_json` emits one
  sorted-key newline-free object; `render_autonomy_next_plan_text` emits a
  compact operator summary; `write_autonomy_next_plan_jsonl` writes exactly one
  newline-terminated record, replacing any prior file contents.

## Execution Classes

Each lane's recommended action resolves to exactly one execution class:

- `noop` — the lane is nominal or healthily waiting; nothing to run. No gate.
- `auto_offline` — a fully-defaulted offline command exists (no operator-supplied
  argument required). `offline_runnable=true`, `gate=""`, and no operator input
  is required. Standing repository authority already permits scoped offline
  execution; the exact executor allowlist, canonical-target validation,
  preflight, dry-run default, and explicit `--apply` switch are controls rather
  than missing-authority gates.
- `offline_operator_input` — an offline command exists but requires
  operator-supplied inputs (e.g. a daily-chain clock and a local adjusted
  daily-bars CSV). `offline_runnable=true`, gate `operator_supplied_inputs`.
- `operator_gated` — no offline path exists. `offline_runnable=false`, and the
  gate names why: `network_market_data_fetch`, `broker_observation`,
  `operator_review`, `task_scheduler_health`, `no_offline_command_available`, or
  `unclassified_action_operator_review`.

## Whole-System Rollup

- `plan_class`:
  - `offline_action_available` — at least one lane is offline-runnable.
  - `authorized_network_action_available` — **V5.51a correction (P1)**: no
    offline-runnable lane, but at least one lane classified
    `authorized_network_read_only`. V5.51 introduced that execution class
    without giving it a bucket, so such a lane counted toward neither
    `offline_runnable_lanes`, `operator_gated_lanes`, nor `noop_lanes`, and a
    plan whose only pending action was the authorized SPY market-data refresh
    reported `all_nominal_or_waiting` ("no next action is pending") and exited
    `0`. The lane is genuinely runnable under standing authority, so it ranks
    below offline (which needs no network at all) and above operator-gated
    (it is not blocked on the operator).
  - `operator_authority_required` — no offline-runnable lane and no authorized
    network lane, but at least one operator-gated lane.
  - `all_nominal_or_waiting` — every lane is `noop`.
- **V5.51a**: the four bucket lists — `offline_runnable_lanes`,
  `authorized_network_lanes`, `operator_gated_lanes`, `noop_lanes` — partition
  the lanes exactly; a lane in none of them is invisible to every aggregate the
  operator reads.
- **V5.51a**: `next_authorized_network_action` /
  `next_authorized_network_action_lane` name the highest-severity authorized
  network lane, mirroring `next_offline_action`. They are populated whenever
  such a lane exists, including when `plan_class` is
  `offline_action_available`.
- `next_offline_action` first selects the highest-severity `auto_offline`
  action (severity ordered blocked→unknown→attention→stale→waiting→nominal→
  absent; ties break by registry order). It falls back to the highest-severity
  operator-input offline action only when no canonical auto-offline action
  exists.
- Invariant: `plan_class` is `offline_action_available` **if and only if**
  `next_offline_action` is non-null and `next_offline_action_lane` is non-empty.
  The whole-system class and the named action are two views of one fact and can
  never disagree; `operator_summary` therefore never reports "no offline action
  is available" for an `offline_action_available` plan.
- `operator_gated_actions` lists every operator-gated lane with its gate.
- `supervisor_system_status`, `supervisor_recommended_action`, and
  `supervisor_recommended_action_lane` are carried through unchanged.
- Exit codes: `0` when `plan_class` is `all_nominal_or_waiting` (nothing
  pending); `1` when any action is pending (`offline_action_available`,
  `authorized_network_action_available`, or `operator_authority_required`);
  `2` on input-validation error. The exit code
  is deliberately a *pending-action* signal, distinct from the supervisor's
  *severity* signal, so a scheduled check can alert precisely on "there is a
  next action to take."

## Frozen Classification Registry

`AUTONOMY_ACTION_CLASSIFICATION` maps exactly the tokens the frozen supervisor
lane registry can emit, plus the all-lanes-absent aggregate token, to an
`ActionClass`. The registry is closed in both directions: no producer is
unclassified and no classification is an unreachable promise.

| supervisor action | class | command |
| --- | --- | --- |
| `run_offline_daily_cycle_chain_to_seed_evidence` | `offline_operator_input` | `etf-sma-offline-daily-cycle-run` (needs `--validated-at`, `--daily-bars-csv`) |
| `run_supervised_readiness_trial_to_seed_r1_evidence` | `auto_offline` | `crypto-readiness-replay` |
| `rerun_supervised_readiness_trial` | `auto_offline` | `crypto-readiness-replay` (structural binding; real stale remains dormant while `max_age_hours=0`) |

The historical M446 reproduction command remains manually runnable, but its
non-emittable `rerun_offline_daily_cycle_chain` autonomy classification was
removed. In an all-absent lab the supervisor still reports the fail-closed
whole-system empty-lab token and an empty aggregate lane, while the planner
selects the separate, canonical crypto per-lane absent action ahead of the SPY
operator-input seed. The two levels are complementary rather than conflicting.

## What This Milestone Does Not Do

- It does not execute, schedule, or queue any command. It emits command strings
  as data.
- It does not add, remove, or re-derive any lane or lane state. It classifies
  the action each lane already declares.
- It does not fetch or generate lane evidence, and changes no live-capital,
  paper-mutation, credential, network, or Task Scheduler authority.
- It does not second-guess the supervisor. If the supervisor recommends an
  operator review, the plan surfaces that review as an operator gate, not an
  offline action.

## Verification

- Focused suite `tests/unit/test_autonomy_next_plan.py` proves classification
  closure and internal consistency, all-absent aggregate/per-lane agreement,
  canonical absent readiness selection, structural stale-token binding,
  operator-input fallback, canonical-root/target refusal, deterministic JSON/
  text rendering, single-record JSONL write, input validation, CLI registration
  and exit codes (0/1/2), and a source-scan proving no forbidden import or call
  (including no `subprocess`, no clock read, no broker/network/credential
  surface).
- The V5.37 supervisor suite and the targeted offline verifier
  (`scripts/verify_offline.ps1`) safety guards remain green with the module and
  CLI command in place.
