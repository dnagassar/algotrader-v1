# Active Implementation Checkpoint

## Classification

- Milestone: `V5.48 — crypto readiness replay reachability`.
- Frozen contract:
  `docs/design/v5_48_crypto_readiness_replay_reachability_contract.md`.
- Accepted contract commit:
  `d6e408e8d747f7af82ff2d3b2f7978289e7fa5c6`.
- Independent review: accepted with no P0-P2 findings.
- Promotion: verified fast-forward to `origin/main` at
  `d6e408e8d747f7af82ff2d3b2f7978289e7fa5c6`.
- V5.48 implementation has not started. The accepted contract grants the next
  writer the exact implementation scope; it does not itself prove autonomous
  reachability.

## Checkout And Ownership

- Contract worktree:
  `C:\Users\danie\Desktop\algo_trader\.claude\worktrees\v547-import-pure-readiness-replay`.
- Contract branch:
  `codex/v5.48-readiness-replay-reachability-contract`.
- Contract and promoted-main commit were equal at takeover:
  `d6e408e8d747f7af82ff2d3b2f7978289e7fa5c6`.
- Contract review and promotion are complete; they are no longer risks or
  pending actions.
- This post-promotion handoff update changes only this file. No source, test,
  script, frozen-contract, broker, paper, or live behavior is changed.

## Exact Capability Boundary To Implement

1. Make the existing absent-readiness token
   `run_supervised_readiness_trial_to_seed_r1_evidence` canonically reachable
   through `EXECUTION_AUTO_OFFLINE` and exact argv
   `("crypto-readiness-replay",)`.
2. Bind the distinct existing stale token
   `rerun_supervised_readiness_trial` to the same class/argv structurally, but
   do not claim real stale reachability. The lane has `max_age_hours=0`, and
   the V5.47 packet has no authenticated freshness field; stale remains
   dormant.
3. Remove the dead, non-emittable
   `rerun_offline_daily_cycle_chain` classification/allowlist promise while
   preserving the underlying manually runnable M446 command.
4. Enforce exact two-way closure:
   supervisor producer tokens equal classification keys, and emitted
   `EXECUTION_AUTO_OFFLINE` tokens equal executor allowlist keys.
5. Use truthful standing-authority semantics:
   `EXECUTION_AUTO_OFFLINE` has `gate=""` and no required operator inputs.
   `AGENTS.md` already grants scoped offline authority; the exact allowlist,
   canonical-target validation, credential/profile preflight, dry-run default,
   and explicit `--apply` are controls, not missing-authority gates.
6. Prefer a canonical `EXECUTION_AUTO_OFFLINE` action over
   `EXECUTION_OFFLINE_OPERATOR_INPUT`, while preserving the fail-closed
   all-absent aggregate recommendation and its separate safe per-lane action.
7. Restrict eligibility and apply execution to the exact packet under the
   verified executing repository root:
   `runs/crypto_supervised_readiness_trial/latest/readiness_packet.json`.
   The fixed argv has no output-root and no output propagation may be invented.
8. Planner and executor independently reject noncanonical `--lanes-root`,
   readiness `--lane` override, cwd/root, path/symlink escape,
   supplied-plan/report mismatch, action/command/argv drift, and
   non-repository execution before any runner call or refresh claim.
9. Copy the supervisor lane's existing `artifact_path` into the plan action
   only for validation. Executor compares it with top-level `lanes_root`,
   config/overrides, a freshly re-derived report/plan, and the module-derived
   canonical packet. It never becomes an output argument.
10. Reject explicit replay `--profile` before replay dispatch; broker,
    paper-read, receipt, credential-looking, network, paper, and live options
    remain unavailable.
11. Prove the exact executable launcher
    `python -m algotrader.cli crypto-readiness-replay`, not only the V5.47
    replay-module closure. Evidence must cover the central CLI's eager pure
    `paper_order_policy` and package dependencies, fresh-process protected
    environment traps, exact dispatch, canonical artifact, and post-run
    forbidden-`sys.modules` audit.
12. Keep LLMs and agents outside the executable hot path.

## Required Safety Posture

- Default tests remain offline, deterministic, credential-free, network-free,
  and broker-free.
- No credential value may be requested, read, printed, logged, persisted, or
  exposed.
- No network, market-data, broker, or paper profile is used.
- No order is submitted, cancelled, replaced, closed, or liquidated.
- No broker or paper-account mutation occurs.
- Paper quantity/notional caps: not applicable; no paper action.
- Broker receipt/reconciliation: not applicable; no broker operation.
- `live_authorized=false`; live access, live trading, and real-capital activity
  remain prohibited.
- Generated readiness and manual evidence stays ignored under `runs/`.

## Verification And Yield Requirements

Follow the frozen contract exactly, including:

- focused supervisor/planner/executor/self-refresh/replay/CLI tests;
- producer/classification/allowlist closure tests;
- all canonical-target and supplied-plan/report negative cases, proving zero
  runner calls and no refresh/convergence claim;
- exact-launcher static and fresh-process evidence;
- isolated canonical-worktree dry-run and real apply-plan evidence;
- dependency-direction gate;
- `.\scripts\verify_offline.ps1`;
- full default pytest when the verifier skips it;
- `git diff --check`;
- `git status --short`;
- `git diff --name-only HEAD -- src`;
- `git ls-files --others --exclude-standard src tests`;
- exact reporting required by `AGENTS.md` and the frozen contract.

Before yielding, update this file with exact implementation ownership, changed
files, test/manual evidence, safety outcomes, dirty state, commit, push state,
unresolved risks, and the single next action.

## Single Next Highest-Leverage Safe Action

From promoted `origin/main` commit
`d6e408e8d747f7af82ff2d3b2f7978289e7fa5c6`, create a new implementation
feature branch (recommended:
`codex/v5.48-readiness-replay-reachability-implementation`) and implement the
accepted frozen V5.48 contract with exactly one implementation writer.

Do not implement on the contract branch. Do not merge or promote the
implementation before independent review and acceptance.
