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

## Settled Design Decisions

- **Crypto readiness staleness is permanently dormant by design** (operator
  decision, 2026-07-26). This was previously carried as an unresolved risk
  pending a V5.49 freshness contract; that contract was frozen, reviewed,
  and **closed without implementation**. The readiness replay is a pure
  function of fixed constants with no time-varying input, so any freshness
  timestamp would attest re-execution recency rather than readiness
  recency — a weak regression canary bought at the cost of extending the
  import-purity envelope, changing a staleness resolver shared by every
  lane, and adding a field readers would over-trust. Readiness evidence is
  **timeless**: proven once, deterministically; re-running proves nothing
  new.
  - `rerun_supervised_readiness_trial` therefore stays **deliberately dead
    code paired with a live registration**. It remains in
    `AUTONOMY_ACTION_CLASSIFICATION` and `AUTONOMY_EXECUTOR_ALLOWLIST`
    because V5.48's exact two-way set-equality invariants require every
    producer token to be classified. Deleting the mapping as "dead code"
    would break those invariants.
  - Enforced, not merely documented, by three tests in
    `tests/unit/test_autonomy_supervisor.py`
    (`test_readiness_staleness_is_permanently_dormant_by_design`,
    `test_readiness_lane_never_goes_stale_at_any_evaluation_time`,
    `test_readiness_stale_token_stays_registered_while_unreachable`).
  - Reopen only if the readiness computation gains a genuinely time-varying
    input (live market data, broker-observed state, or account state), and
    then freeze a new contract rather than resurrecting the closed one.
  - Rejected design record:
    `docs/design/v5_49_authenticated_readiness_freshness_contract.md`.

## Unresolved Risks

- Full pytest run on this host takes on the order of 80+ minutes and
  approached tight memory headroom (~8% free at peak); no failures or
  hangs occurred this run, but this remains a slow, resource-sensitive gate
  worth revisiting if it starts timing out.

## Independent Re-Verification (orchestrator, 2026-07-26)

Re-verified the V5.48 acceptance report against a clean checkout of
`claude/algo-trader-orchestrator-verify-a35353` at `600bf72`.

- Working tree clean: no staged diff, no unstaged diff, no untracked files.
- `HEAD == origin/main == 600bf72` (zero commits either side).
- Contract commit `d6e408e`, implementation commit `6d4838b`, and evidence
  commit `38399df` are all ancestors of `HEAD`.
- Reran the six V5.48 suites (supervisor, next_plan, offline_executor,
  self_refresh_cycle, crypto_readiness_replay, dependency_direction) →
  **216 passed**, exactly matching the reported 174 + 42.
- `.\scripts\verify_offline.ps1` → **PASS**; all nine credential/profile
  precheck booleans false; 107 targeted safety-guard tests passed.
- Source confirms the report's structural claims:
  `rerun_offline_daily_cycle_chain` is absent from `src/` (present only as
  negative assertions in tests); `AUTONOMY_EXECUTOR_ALLOWLIST` maps both
  readiness tokens to `CANONICAL_REPLAY_ARGV`; canonical
  root/cwd/lanes-root/packet validation exists independently in both
  planner and executor; `cli.py:_run_crypto_readiness_replay` refuses an
  explicit `--profile` via the already-parsed argv record without loading
  a profile.
- The stale-token risk disclosure is confirmed honest at the source level:
  the readiness `LaneSpec` sets `max_age_hours=0`
  (`autonomy_supervisor.py:346`) and the staleness predicate requires
  `lane.max_age_hours > 0`, so `rerun_supervised_readiness_trial` cannot
  fire at runtime. The packet additionally carries no `generated_at`/`as_of`
  field at all, which blocks it a second time.

Not independently reproduced: the reported full-suite run
(**10033 passed, 5 skipped**, ~83.5 min). The targeted and safety-gate
evidence above was reproduced in full; the full-suite figure remains
single-sourced from the implementation lane.

Also noted: `claude/agent-handoff-execution-579196@cd7e919` remains the one
frontier tip not reachable from `main`. Its two commits are doc-only (the
V5.43 integration contract plus a handoff), and the substantive V5.43
reconciliation merge `52e0018` *is* in `main`, so this is a stale
documentation branch, not unmerged capability.

## V5.49 Lifecycle (closed)

Frozen `44f5e32` → reviewed `fad3b82` (REQUEST CHANGES, four defects found
and corrected) → **closed unimplemented by operator decision, 2026-07-26**.

The round-1 review escalated a gating question: whether the milestone was
worth building at all, given that the readiness replay is a pure function of
fixed constants and a freshness field would therefore attest re-execution
recency rather than readiness recency. The operator adjudicated: it is not.
V5.49 is closed, the contract is retained as a rejected design record, and
the stale token is now permanently dormant by design and pinned by test.

Two defects found during that review are worth carrying forward as general
lessons, independent of V5.49:

1. `_compute_bundle_id` in `crypto_supervised_readiness_trial_core.py`
   hashes the **entire** readiness packet minus only `artifact_paths`,
   `artifact_integrity`, and `bundle_id` — and `bundle_id` names a
   generation **directory**. Any future packet field that varies between
   runs must join that exclusion list, or content-addressed idempotency
   breaks and generation directories accumulate per run.
2. `_staleness` resolves `as_of_fields` by **flat top-level lookup**, and
   that resolver is shared by every lane. Nested paths are unsupported;
   adding them is a cross-lane change needing per-lane regression proof.

## V5.50 Lane Eligibility Analysis (blocked, 2026-07-26)

Operator directed broadening offline autonomy to a second lane. Surveyed
all six registry lanes at `8406aef`. **No second lane is eligible.** Full
analysis: `docs/design/v5_50_offline_autonomy_lane_eligibility_analysis.md`.

The binding criterion is **input self-containment**: the offline executor
can only auto-execute an action whose inputs live entirely in the repository
and its frozen constants. The crypto readiness replay satisfies this
uniquely — it is a pure function of constants and takes no external input.
Every other lane's artifact is a function of real-world data:

- `spy_market_data_soak` — live market-data fetch, ineligible by definition.
- `spy_offline_daily_cycle` — closest candidate and the only other lane
  already `offline_runnable=True`, but requires an operator-supplied
  adjusted SPY bars CSV. Following the chain upstream does not help:
  `local-daily-bars-intake`'s own root input is documented
  "Operator-supplied". The pipeline canonicalizes data; it does not
  originate it. The only committed CSVs are synthetic SMA test fixtures, and
  wiring those in as production input would fabricate market data.
- `crypto_forward_shadow_cycle`, `crypto_bounded_paper_probe_review`,
  `crypto_capability_production` — all report
  `no_offline_command_available`. Producer modules exist and are local-only,
  so they look like V5.48-shaped wiring jobs, but they require frozen V5.25
  terminal evidence which **does not exist anywhere in the checkout** (only
  a design doc), and `runs/crypto_strategy_tournament/` is absent entirely.
  Producing that evidence requires the tournament, which requires market
  data.

**Structural consequence, and the correction this produces:** offline
autonomy cannot be broadened by wiring at all. It can only be broadened by
giving the system a safe, authorized way to *acquire* external inputs. The
two tracks offered after the V5.49 closure are therefore **not
independent** — broadening offline autonomy is gated on the
market-data/paper track, not parallel to it. The earlier recommendation to
do (1) before (2) was wrong on that point.

Note the symmetry with V5.49: the readiness replay could be automated
*because* it is a pure function of constants, and its freshness was
meaningless *because* it is a pure function of constants. Same fact, both
conclusions.

## Next Action

Operator decision between three options (detail in the V5.50 analysis):

1. **Accept the ceiling.** Record offline autonomy as complete at one
   action; further breadth requires external input. Costs nothing, and is
   the honest default if the market-data track is not ready to start.
2. **Authorize the market-data intake path**, then revisit
   `spy_offline_daily_cycle`. The only route that broadens autonomy over
   existing lanes, and the only one that advances trading capability. It
   crosses the network gate and needs its own frozen contract and an
   undivided review pass — it should be started deliberately as the
   market-data track, not disguised as an autonomy milestone.
3. **Add a new self-contained lane** — e.g. an offline determinism
   /regression canary over the repository. Unlike V5.49's rejected freshness
   field, its evidence would vary with real code changes, so it would attest
   something. Broadens executor breadth without touching the network gate,
   but advances self-observation rather than trading. Invents new scope.

Recommendation: 1 or 3, depending on whether self-observation is worth a
milestone now.

Unchanged hard gate: **live capital remains operator-gated until burn-in
completes.** Nothing in V5.48, the V5.49 closure, or this analysis touches
that.
