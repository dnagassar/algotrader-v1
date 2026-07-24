# Active Implementation Checkpoint

## Classification

- Milestone:
  `V5.38 — offline autonomy next-action planner` (stacked on
  `V5.37 — offline cross-lane autonomy supervisor`).
- Classification: `implemented`.
- Operator action required for implementation: `false`.
- Independent review required before merge to `main`: `true`.
- This checkpoint is not canary, broker, paper, activation, or trading
  readiness evidence. It is an offline read-only reporting/planning surface only.

## Use This One Workspace

- Implementation worktree:
  `C:\Users\danie\Desktop\algo_trader\.claude\worktrees\algo-trader-autonomy-bd3c0a`
- Branch: `claude/algo-trader-autonomy-bd3c0a`
- Base: `409391b` — the V5.37 supervisor plus the per-worktree interpreter
  binding tooling, fast-forwarded from `main@3336e9a`. This branch adds V5.38 on
  top; both V5.37 and V5.38 are additive and still require independent review
  before merge to `main`.
- The operator's `C:\Users\danie\Desktop\algo_trader` checkout on `main` was not
  modified. Review this worktree and its branch HEAD directly.

## Principal Bottleneck Addressed

V5.37 answers *what state* each autonomy lane is in and emits one abstract
`recommended_next_action` token per lane, but it deliberately never maps a token
to a runnable command and never separates an action that can be advanced inside
the offline envelope from one blocked on the operator. After running the
supervisor an operator still had to hand-translate every recommendation into "is
there a command I can run, what inputs does it need, or is this blocked on me?"
That translation was the binding constraint between observing the system and
acting on it, and it is the highest-leverage change inside the authorized
offline envelope. V5.38 closes that gap without crossing it: it plans the next
action but never executes it.

## Changed Files

- `src/algotrader/cli.py`
  (registers `autonomy-next-plan` and its handler `_run_autonomy_next_plan`)
- `src/algotrader/execution/autonomy_next_plan.py` (new pure module)
- `tests/unit/test_autonomy_next_plan.py` (new focused suite, 22 tests)
- `scripts/run_autonomy_next_plan.ps1` (new credential-free wrapper)
- `docs/design/v5_38_offline_autonomy_next_action_planner.md` (frozen contract)
- `docs/deterministic_core.md` (current-contract section)
- `docs/project_checkpoint.md` (ledger entry)
- `docs/OPERATOR_RUNBOOK.md` (operator section)
- `docs/agent_context/active_implementation.md` (this handoff)

## Contract Summary

- `autonomy-next-plan` builds a V5.37 supervisor report (or accepts one via
  `build_autonomy_next_plan_from_report`) and classifies each lane's declared
  `recommended_next_action` against the frozen registry
  `AUTONOMY_ACTION_CLASSIFICATION` into one execution class: `noop`,
  `auto_offline`, `offline_operator_input`, or `operator_gated`.
- For an offline-runnable class it records the exact offline command, the
  operator-supplied inputs still required, and any preconditions. For an
  `operator_gated` class it records the single gate that blocks autonomous
  progress: `network_market_data_fetch`, `broker_observation`,
  `operator_review`, `task_scheduler_health`, `no_offline_command_available`, or
  `unclassified_action_operator_review`.
- It aggregates one whole-system `plan_class` (`offline_action_available`,
  `operator_authority_required`, or `all_nominal_or_waiting`), the
  highest-severity `next_offline_action`, and the full set of
  `operator_gated_actions`. `supervisor_system_status` and the supervisor's
  recommendation are carried through unchanged.
- The registry provably covers every action the frozen supervisor lane registry
  can emit; an unclassified token fails closed to an operator-review gate.
- Exit code: `0` when `plan_class` is `all_nominal_or_waiting` (nothing
  pending), `1` when any action is pending, `2` on validation error.

## The Deliberate Operator Gate

Today the only offline-runnable lane is the SPY offline daily cycle chain
(`etf-sma-offline-daily-cycle-run` needs operator-supplied inputs;
`etf-sma-offline-daily-cycle-rerun-m446` is fully defaulted). Every other lane
action is `noop` or `operator_gated`, so **no lane can be advanced without
operator-supplied input or operator authority**. That is the honest whole-system
finding and the hard gate at which autonomous advance stops. Wiring the system
to run even the offline commands unattended grants it a new standing execution
authority — a founder-level authority expansion under the Operating Charter — and
therefore requires explicit operator authorization before it is built. This
milestone is the complete advisory layer up to, but not across, that gate.

## Safety And External Effects

Boolean-only preflight was clean before and during implementation and
verification:

- `APP_PROFILE=paper`: `false`
- Alpaca credential aliases loaded: `false`
- network-test enablement present: `false`

During implementation and verification:

- no credential value was loaded, read, enumerated, or exposed;
- no network, broker, or Task Scheduler access occurred;
- no paper mutation, order action, canary, or live activation occurred;
- no subprocess was spawned and no planned command was executed.

Every emitted record fixes `submitted`, `mutated`, `broker_action_performed`,
`broker_actions_performed`, `broker_mutation_allowed`, `network_access_attempted`,
`credential_access_attempted`, and `live_authorized` to false with
`profit_claim=none`. The module imports no `os`, `socket`, `urllib`, `requests`,
`subprocess`, or broker SDK, and reads no wall clock; a source-scan test enforces
this. It records command strings as inert data and never executes them.

## Verification Evidence

- Focused suite: `tests/unit/test_autonomy_next_plan.py` — `22 passed`.
- V5.37 supervisor suite: `tests/unit/test_autonomy_supervisor.py` — `25 passed`.
- Dependency direction: `tests/unit/test_dependency_direction.py` — `34 passed`.
- Targeted offline verifier (`scripts/verify_offline.ps1`, native PowerShell on
  this named branch): `PASS`, `99 passed` safety guards in 53.84s,
  credential/network preflight all false, git hygiene clean, no tracked `runs/`
  artifacts.
- Full bounded offline suite (`scripts/verify_offline.ps1 -Full`): not run in
  this session (many-minute four-shard run). Recommended before merge.
- Manual `autonomy-next-plan` run on a clean checkout returned
  `plan_class=offline_action_available` with `next_offline_action_lane=
  spy_offline_daily_cycle` (the seed command, needing operator inputs) and the
  other five lanes operator-gated, exit code `1`, all safety booleans false.

## Required Independent Review

Review this worktree and its branch HEAD. Verify:

1. the planner reads only local files (via the supervisor) and constructs no
   broker/network/credential path, spawns no subprocess, and reads no wall clock
   (source scan plus manual read);
2. it plans commands as inert data and never executes, schedules, or queues any
   command;
3. `AUTONOMY_ACTION_CLASSIFICATION` covers every action the frozen supervisor
   lane registry can emit, and an unclassified token fails closed to an
   operator-review gate;
4. the two offline-runnable commands map to real, verified-offline CLI
   subcommands (`etf-sma-offline-daily-cycle-run`,
   `etf-sma-offline-daily-cycle-rerun-m446`) and their producing modules import
   no network/broker/credential/profile surface;
5. no lane action is classified offline-runnable unless a genuine offline command
   exists; market-data-fetch, broker, scheduler, and review actions are
   operator-gated;
6. every emitted record and the write result preserve the false safety booleans
   and `profit_claim=none`;
7. `plan_class`, `next_offline_action` severity selection, and the exit-code
   contract (`0`/`1`/`2`) match this handoff.

Return one classification: `accepted`, `changes_requested`, or `blocked`, with
sanitized findings and evidence.

## Route After Review

If accepted, this additive `claude/*` branch (V5.37 + V5.38) may be merged into
`main` under the canonical layout. No merge, push to `main`, credential read,
network request, broker request, paper mutation, order action, Task Scheduler
operation, or trading activation follows automatically from this handoff.
Autonomous unattended execution of the planned offline commands is a separate,
higher milestone requiring explicit operator authorization; it is out of scope
here.
