# Active Implementation Checkpoint

## Classification

- Milestone: `V5.48 — crypto readiness replay reachability`.
- Frozen contract:
  `docs/design/v5_48_crypto_readiness_replay_reachability_contract.md`.
- Accepted contract commit:
  `d6e408e8d747f7af82ff2d3b2f7978289e7fa5c6`.
- Implementation status: **accepted and promoted. `origin/main` fast-forwarded
  to evidence commit `38399df` (which carries implementation commit
  `6d4838b`).**
- Implementation commit:
  `6d4838b` ("Implement V5.48 crypto readiness replay reachability") on
  `codex/v5.48-readiness-replay-reachability`, parent
  `3c050a58c4a50edd4a4815867f99798682890337`.
- Evidence/promotion commit:
  `38399df9a018430d61c9dce20e170a258a0ed315` ("Record V5.48 implementation
  evidence and handoff") — fast-forward promoted to `origin/main`.
- Independent acceptance: static review found no P0-P2 findings. Orchestrator
  independently reran the planner/executor/supervisor/self-refresh suite
  (158 passed), the exact central-launcher purity test (1 passed), and three
  static launcher/evasion tests, all passing.

## Checkout And Ownership

- Implementation worktree:
  `C:\Users\danie\Desktop\algo_trader\.claude\worktrees\v547-import-pure-readiness-replay`.
- Branch: `codex/v5.48-readiness-replay-reachability`.
- Implementation ownership was explicitly transferred from Codex to Claude
  (operator instruction) to preserve Codex credits; Codex remains
  orchestrator/reviewer. Claude took over an already-dirty checkout
  (uncommitted changes in the same 10 files this commit now contains),
  inspected it against the frozen contract, found it contract-conformant,
  ran full verification, collected manual isolated-worktree evidence, and
  committed it as a single coherent commit.
- Takeover preflight (presence-only, no values): `APP_PROFILE` not set; no
  Alpaca/APCA credential alias set; no network-test alias set.

## Files Changed

- `src/algotrader/execution/autonomy_next_plan.py`
- `src/algotrader/execution/autonomy_offline_executor.py`
- `src/algotrader/cli.py` (replay-specific explicit `--profile` refusal)
- `tests/unit/test_autonomy_next_plan.py`
- `tests/unit/test_autonomy_offline_executor.py`
- `tests/unit/test_autonomy_self_refresh_cycle.py`
- `tests/unit/test_crypto_readiness_replay.py`
- `tests/unit/test_dependency_direction.py` (exact central-launcher
  eager-import purity scan)
- `docs/design/v5_38_offline_autonomy_next_action_planner.md`
- `docs/design/v5_39_gated_offline_autonomy_executor.md`

All within the contract's frozen implementation scope. No file outside
that list was touched.

## Contract Conformance Summary

- Both readiness tokens (`run_supervised_readiness_trial_to_seed_r1_evidence`
  absent, `rerun_supervised_readiness_trial` stale) are classified
  `EXECUTION_AUTO_OFFLINE`, `gate=""`, `command="python -m algotrader.cli
  crypto-readiness-replay"`, `required_operator_inputs=()`, exactly per the
  frozen `ActionClass` shape.
- `rerun_offline_daily_cycle_chain` removed from both
  `AUTONOMY_ACTION_CLASSIFICATION` and the executor allowlist; the M446 CLI
  command remains manually runnable.
- Exact two-way closure holds: `set(AUTONOMY_ACTION_CLASSIFICATION) ==
  producer_tokens` and `set(AUTONOMY_EXECUTOR_ALLOWLIST) ==
  auto_offline_tokens` (proven by dedicated tests).
- `AUTONOMY_EXECUTOR_ALLOWLIST` maps both readiness tokens to exactly
  `("crypto-readiness-replay",)`.
- Planner (`autonomy_next_plan.py`) and executor
  (`autonomy_offline_executor.py`) each independently verify: executing
  repository root has `.git` + `src/algotrader/cli.py`; process cwd equals
  that root; `lanes_root` resolves to `<root>/runs`; the crypto lane's
  `artifact_path` resolves to
  `<root>/runs/crypto_supervised_readiness_trial/latest/readiness_packet.json`;
  no symlink escape; lane id/state/action/classification/command agree. Any
  mismatch raises `ValidationError` before any runner call.
- Executor re-derives the canonical plan from `AutonomySupervisorConfig` and
  requires exact equality with any supplied plan/report before proceeding
  (stricter than the contract's "agree on at least" list).
- `src/algotrader/cli.py`'s `_run_crypto_readiness_replay` rejects an
  explicit `--profile`/`--profile=...` (any value) using the already-parsed
  `_argv_items` record — it does not load a profile to decide — returning
  exit `2` before `run_crypto_readiness_replay` is called.
- New `tests/unit/test_dependency_direction.py` cases statically prove
  `algotrader.cli`'s only non-stdlib top-level import is
  `algotrader.execution.paper_order_policy` (stdlib-only itself), walk the
  full eager first-party closure (`algotrader/__init__.py`,
  `algotrader/execution/__init__.py`), and scan the replay dispatch path and
  handler for forbidden imports/mutation calls, with synthetic
  evasion-detection negatives.
- New `tests/unit/test_crypto_readiness_replay.py::
  test_exact_central_launcher_is_protected_and_import_pure` spawns the
  literal `<sys.executable> -m algotrader.cli crypto-readiness-replay` from
  an isolated copied repository with a `sitecustomize`-based protected
  environment trap and post-run `sys.modules` audit; asserts zero protected
  accesses and zero forbidden modules loaded.
- `autonomy_self_refresh_cycle` tests were updated to reflect truthful
  absent-reachability: dry-run reports the crypto action eligible but
  unexecuted (no refresh claim); apply with an injected successful runner
  executes once, re-observes nominal, and a second cycle no longer sees the
  action eligible (no repeat); a failed child never claims
  `refreshed`/`converged`; every canonical-target refusal proves zero
  runner calls.

## Verification Evidence

All commands run from
`C:\Users\danie\Desktop\algo_trader\.claude\worktrees\v547-import-pure-readiness-replay`
with `PYTHONPATH=src`, no `APP_PROFILE`, no credential/network-test alias
loaded (presence-only, confirmed before and after).

- `python -m pytest tests/unit/test_autonomy_supervisor.py
  tests/unit/test_autonomy_next_plan.py
  tests/unit/test_autonomy_offline_executor.py
  tests/unit/test_autonomy_self_refresh_cycle.py
  tests/unit/test_crypto_readiness_replay.py` → **174 passed**.
- `python -m pytest tests/unit/test_dependency_direction.py` → **42
  passed**.
- `.\scripts\verify_offline.ps1` → **PASS** (hygiene, credential/profile
  precheck all false, targeted offline safety-guard tests 107 passed; full
  pytest skipped by the script itself, pending `-Full`).
- `python -m pytest` (full default suite, since the verifier skipped it) →
  **10033 passed, 5 skipped**, in ~83.5 minutes (5011.51s). Exit 0.
- `git diff --check` → clean (exit 0).
- `git status --short` → clean tree after commit `6d4838b`.
- `git diff --name-only HEAD -- src` → n/a post-commit (matches the 3
  committed `src` files vs. parent).
- `git ls-files --others --exclude-standard src tests` → empty (no
  untracked src/tests files).

## Manual Isolated-Worktree Evidence (V5.48-specific)

Fresh temporary Git worktree created via `git worktree add --detach` at
implementation commit `6d4838b`, empty canonical `runs/` confirmed absent
before use, all runs from that worktree's own root as cwd. Presence-only
credential/profile preflight confirmed empty before both the dry-run and
the apply.

1. **Dry-run**
   (`autonomy-apply-plan --run-id v5_48_absent_dry_run --as-of
   2026-07-26T12:00:00Z --lanes-root runs --format json`): exit `1`;
   `dry_run=true`; `eligible_count=1`; `execution_count=0`; only the crypto
   absent token eligible with argv `["crypto-readiness-replay"]`;
   `lanes_root="runs"` (canonical); all broker/paper/live booleans false.
2. **Apply**
   (`autonomy-apply-plan --run-id v5_48_absent_apply --as-of
   2026-07-26T12:00:00Z --lanes-root runs --apply --format json`): exit
   `0`; `eligible_count=1`; `execution_count=1`; executed argv exactly
   `["crypto-readiness-replay"]`; child `exit_code=0`;
   `all_executions_succeeded=true`; resulting
   `runs/crypto_supervised_readiness_trial/latest/readiness_packet.json`
   has `trial_classification="accepted"`; no credential value in any
   output.
3. **Second dry-run** (same worktree, after the accepted packet exists):
   `eligible_count=0`; crypto lane now reports
   `r1_deterministic_readiness_proven_continue` (noop, nominal);
   `supervisor_system_status="nominal"`. Other operator-input lane work
   (SPY seed) correctly remains reported, not misclassified as executed.
4. **Negative: noncanonical `--lanes-root /tmp/not-canonical` with
   `--apply`** → `ValidationError` ("lanes_root must be the canonical
   repository runs path."), exit `2`, zero runner calls.
5. **Negative: non-repository cwd** (invoked from a directory outside any
   Git checkout with `PYTHONPATH` pointed at the worktree's `src`) →
   `ValidationError` ("process cwd must equal the executing repository
   root."), exit `2`, zero runner calls.
6. **Negative: noncanonical readiness `--lane` override**
   (`--lane crypto_supervised_readiness_trial=runs/other_location/readiness_packet.json`
   with `--apply`) → `ValidationError` ("crypto readiness lane override
   must equal the canonical packet."), exit `2`, zero runner calls.
7. **Negative: explicit root `--profile paper` before `crypto-readiness-replay`**
   → `crypto_readiness_replay_validation_error=explicit_profile_option_not_permitted`,
   exit `2`, replay never invoked.
8. **Negative: broker/receipt/paper-read flags**
   (`--broker-observed-readiness`, `--receipt-root foo`,
   `--allow-alpaca-paper-read`) → each rejected by the parser, exit `2`.
9. **Exact fresh-process launcher proof**: literal
   `<sys.executable> -m algotrader.cli crypto-readiness-replay` run from
   the same isolated canonical worktree with a `sitecustomize`-based
   protected-environment trap (raises on access to `APP_PROFILE` and all
   Alpaca/APCA/network-test keys) and a post-run `sys.modules` audit → exit
   `0`; exact V5.47 text output
   (`v5_47_trial_classification=accepted`, ... `v5_47_live_authorized=false`);
   `protected_environment_accesses=[]`; `forbidden_modules_loaded=[]`
   (checked against the same forbidden-module set used in the automated
   test: alpaca/broker/credential/LLM modules); accepted canonical packet
   confirmed on disk.

Temporary worktree and harness directories were removed after evidence
collection (`git worktree remove --force`); no generated `runs/` artifact
from manual evidence is tracked or committed.

## Safety Outcomes

- No network, market-data, broker, or paper-account access at any point.
- No credential value requested, read, printed, logged, persisted, or
  exposed; only variable *names* ever appear in preflight/refusal output.
- No order submit/cancel/replace/close/liquidation; no broker/paper
  mutation.
- `live_authorized=false` throughout; no live access or real-capital
  activity.
- Local deterministic artifact writes under `runs/` (ignored, untracked)
  were the only side effect of `--apply`/the manual launcher run.
- No LLM or agent in the executable hot path (dependency-direction scan
  passed with new synthetic-evasion negatives).
- Paper caps/receipt/reconciliation: not applicable — no paper action
  performed.

## Unresolved Risks

- Real age-based staleness for the crypto readiness lane remains
  unimplemented by design (`max_age_hours=0`; V5.47 packet has no
  authenticated freshness field). The stale token's V5.48 evidence is
  structural (registry/classification/allowlist/planner-selection from a
  constructed summary) only, not live reachability — as the contract
  requires. A later, separately frozen contract is needed to introduce an
  authenticated freshness field before stale can become truly reachable.
- Full pytest run on this host takes on the order of 80+ minutes and
  approached tight memory headroom (~8% free at peak); no failures or
  hangs occurred this run, but this remains a slow, resource-sensitive gate
  worth revisiting if it starts timing out.

## Next Action

Freeze and independently review a separate V5.49 authenticated
readiness-freshness contract before any implementation. That future
contract must:

- Honestly define an integrity-bound freshness timestamp/clock-injection
  mechanism and a positive, finite max age, without reusing the fixed
  `decision_start` or weakening V5.47's deterministic/import-pure defaults.
- Only then make the stale token's refresh converge through the existing
  exact replay (`python -m algotrader.cli crypto-readiness-replay`) — and
  only if a safe, fixed/validated argv design exists for doing so.
- Introduce no broker/network/credentials/paper/live access and no LLM in
  the executable hot path.

No other next action is open on V5.48.
