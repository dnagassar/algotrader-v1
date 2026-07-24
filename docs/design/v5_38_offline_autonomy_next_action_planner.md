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
  argument required). `offline_runnable=true`. The remaining gate is
  `unattended_execution_authority`: the *system* running the command unattended
  is an authority the offline envelope does not grant.
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
  - `operator_authority_required` — no offline-runnable lane, but at least one
    operator-gated lane.
  - `all_nominal_or_waiting` — every lane is `noop`.
- `next_offline_action` is the highest-severity offline-runnable lane's planned
  action (severity ordered blocked→unknown→attention→stale→waiting→nominal→
  absent; ties break by registry order), or `null` when none exists.
- `operator_gated_actions` lists every operator-gated lane with its gate.
- `supervisor_system_status`, `supervisor_recommended_action`, and
  `supervisor_recommended_action_lane` are carried through unchanged.
- Exit codes: `0` when `plan_class` is `all_nominal_or_waiting` (nothing
  pending); `1` when any action is pending (`offline_action_available` or
  `operator_authority_required`); `2` on input-validation error. The exit code
  is deliberately a *pending-action* signal, distinct from the supervisor's
  *severity* signal, so a scheduled check can alert precisely on "there is a
  next action to take."

## Frozen Classification Registry

`AUTONOMY_ACTION_CLASSIFICATION` maps every `recommended_next_action` token the
frozen supervisor lane registry can emit to an `ActionClass`. Today the only
offline-runnable lane is the SPY offline daily cycle chain:

| supervisor action | class | command |
| --- | --- | --- |
| `run_offline_daily_cycle_chain_to_seed_evidence` | `offline_operator_input` | `etf-sma-offline-daily-cycle-run` (needs `--validated-at`, `--daily-bars-csv`) |
| `rerun_offline_daily_cycle_chain` | `auto_offline` | `etf-sma-offline-daily-cycle-rerun-m446` (fully defaulted; needs the refreshed M446 CSV present) |

Both underlying modules (`etf_sma_offline_daily_cycle_run`,
`etf_sma_offline_daily_cycle_rerun_m446`) were verified to import no network,
broker, credential, or profile surface. Every other supervisor action is either
`noop` (nominal/waiting) or `operator_gated` — because seeding the market-data
soak or a crypto lane needs a network market-data fetch, a broker observation, a
scheduled-task health check, or a human review, none of which the offline
envelope can perform. `test_every_supervisor_action_is_classified` proves the
registry covers every action the supervisor can emit; a new lane action cannot
silently degrade the plan.

## The Deliberate Operator Gate

In a clean checkout every lane reads `absent`, and the plan reports exactly one
offline-runnable action (`spy_offline_daily_cycle` seed) that still needs
operator-supplied inputs, plus five operator-gated lanes. **No lane can be
advanced today without either operator-supplied input or operator authority.**
That is the honest whole-system finding, and it is the hard gate at which
autonomous progress stops: this milestone plans the next action but does not,
and must not, execute it.

Autonomous (unattended) execution of even the offline daily-cycle commands is a
distinct, higher milestone. It grants the system a new standing authority to run
commands on its own — a founder-level authority expansion under the Operating
Charter — and therefore requires explicit operator authorization before it is
built. This planner is the complete advisory layer up to, but not across, that
gate.

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
  coverage and internal consistency, clean-checkout offline-seed availability,
  all-nominal no-action, operator-authority-required rollup, offline rerun
  classification, next-offline-action severity selection, deterministic JSON/
  text rendering, single-record JSONL write, input validation, CLI registration
  and exit codes (0/1/2), and a source-scan proving no forbidden import or call
  (including no `subprocess`, no clock read, no broker/network/credential
  surface).
- The V5.37 supervisor suite and the targeted offline verifier
  (`scripts/verify_offline.ps1`) safety guards remain green with the module and
  CLI command in place.
