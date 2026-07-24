# V5.39 Gated Offline Autonomy Executor Contract

## Purpose

V5.37 observes the autonomy lanes and V5.38 plans the next action per lane, but
neither one *acts*. The operator explicitly authorized one narrow, gated step
that can act on the plan: run the strictly-offline, fully-defaulted subset of it,
behind a hard safety gate. V5.39 adds that executor. It is the single seam
through which any autonomous command execution passes, and it fails closed
everywhere else.

`autonomy-apply-plan` builds the V5.38 plan and partitions its actions into an
eligible set (offline-runnable *and* on the frozen allowlist) and a skipped set
(everything else, with a reason). It is **dry-run by default**: without `--apply`
it reports what would run and executes nothing. With `--apply`, after a passing
credential/profile preflight, it runs each eligible allowlisted command with a
sanitized child environment and records a deterministic action ledger.

## Non-Negotiable Safety Contract

- The executor runs only commands on the frozen `AUTONOMY_EXECUTOR_ALLOWLIST`.
  An action not on the allowlist is never executed; `_execute` re-checks the
  allowlist and the resolved argv before every run (defence in depth).
- Every allowlisted command is a fully-defaulted offline CLI subcommand whose
  producing module was verified to import no network, broker, credential, or
  profile surface.
- It is dry-run by default. Dry run spawns no subprocess at all.
- Before any execution it runs `execution_preflight` over the environment and
  refuses (`execution_refused_reason=preflight_failed`, zero executions) if
  `APP_PROFILE` is `paper`/`live` or any Alpaca credential or network-test
  variable is loaded. Preflight reasons name the offending variable only; no
  value is ever read into the ledger.
- Each command runs with a child environment that strips every
  credential/profile variable, so a child can neither authenticate nor reach a
  broker. `PYTHONPATH` is set to the repo `src` so the CLI imports; nothing else
  is added.
- The executor performs and exposes no submit/cancel/replace/close/liquidation/
  paper-mutation/capital/live action of its own. Every ledger record fixes
  `submitted`, `mutated`, `broker_action_performed`, `broker_actions_performed`,
  `broker_mutation_allowed`, `network_access_attempted`,
  `credential_access_attempted`, and `live_authorized` to false with
  `profit_claim=none`. (`mutated` here is broker/paper-account state; an
  executed offline command may write local `runs/` evidence, which is its
  purpose and not a broker mutation.)
- A source-scan test forbids every network/broker/credential-SDK import
  (`aiohttp`, `alpaca*`, `httpx`, `requests`, `socket`, `ssl`, `urllib`) and
  every broker mutation call name; `os`, `sys`, and `subprocess` are permitted
  because execution requires them, and the allowlist plus the dry-run/apply tests
  bound how they are used.

## Module And Command Surface

- Module: `src/algotrader/execution/autonomy_offline_executor.py`.
- CLI: `python -m algotrader.cli autonomy-apply-plan` (add `--apply` to execute).
- Wrapper: `scripts/run_autonomy_apply_plan.ps1` (`-Apply` switch; refuses under
  a loaded profile/credential, defence in depth over the module preflight).
- `build_offline_execution_ledger(config, *, apply=False, plan_report=None,
  environ=None, runner=None)` is the pure entry point; `runner` is an injectable
  subprocess runner for tests, `plan_report` accepts an already-built plan or
  supervisor report.
- Rendering is deterministic: `render_offline_execution_ledger_json` (sorted-key,
  newline-free), `render_offline_execution_ledger_text`, and
  `write_offline_execution_ledger_jsonl` (exactly one newline-terminated record).

## Frozen Allowlist

`AUTONOMY_EXECUTOR_ALLOWLIST` maps a V5.38 action token to the exact argv the
executor may run:

| action token | argv | eligibility |
| --- | --- | --- |
| `rerun_offline_daily_cycle_chain` | `etf-sma-offline-daily-cycle-rerun-m446` | fully-defaulted offline; verified no network/broker/credential/profile import |

The seed command `etf-sma-offline-daily-cycle-run` is intentionally **absent**:
it requires operator-supplied inputs (`--validated-at`, `--daily-bars-csv`), so
it is never eligible for unattended execution. Its plan action is skipped with
reason `requires_operator_input`. Operator-gated actions are skipped with
`not_offline_runnable`.

## Exit Codes

- `2` — input-validation error, or `--apply` refused by a failed preflight
  (a safety refusal).
- `1` — an executed action returned non-zero, or a dry run has eligible offline
  work pending.
- `0` — nothing eligible, or every executed action succeeded.

## Honest Current Limitation

The sole allowlisted command's trigger is the `stale` state of the SPY offline
daily cycle lane. That lane sets `max_age_hours=0` in the frozen supervisor
registry (staleness disabled, by V5.37 design, so healthy waiting is not
misreported), so the supervisor cannot currently emit
`rerun_offline_daily_cycle_chain`. Consequently, wired to the real supervisor,
the executor's eligible set is **empty today** and `--apply` executes nothing —
which is the correct, safe, fail-closed outcome. The executor is nonetheless the
reviewed, tested seam that all future autonomous execution must pass through, and
it becomes active the moment a stale-capable offline lane (or another
fully-defaulted offline command) is added to the allowlist. Whether to give the
daily-cycle lane a staleness bound, or to add an operator-supplied-input
execution path for the seed, are operator decisions, not autonomous ones.

## What This Milestone Does Not Do

- It does not execute anything in dry-run mode, and never executes a
  non-allowlisted command.
- It does not read, pass, or expose any credential, and does not run under a
  loaded profile.
- It does not perform, authorize, or name any broker/paper/live action.
- It does not schedule itself (no Task Scheduler), and it reads no wall clock.
- It does not add operator-supplied-input execution; the seed stays operator-run.

## Verification

- Focused suite `tests/unit/test_autonomy_offline_executor.py` proves the
  allowlist contents, preflight pass/refuse (including that credential values are
  never echoed), dry-run inertness, apply-runs-only-allowlisted-argv,
  failed-execution recording, child-env credential stripping and PYTHONPATH via a
  patched `subprocess.run`, the defence-in-depth argv re-check, deterministic
  JSON/text rendering, single-record JSONL write, input validation, CLI dry-run
  default and exit codes, and a source-scan proving no forbidden import or call.
- The V5.37 supervisor, V5.38 planner, and dependency-direction suites and the
  targeted offline verifier remain green with the module and command in place.
