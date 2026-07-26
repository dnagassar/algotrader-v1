# Active Implementation Checkpoint

## Classification

- Milestone: `V5.48 — crypto readiness replay reachability`.
- Contract candidate:
  `docs/design/v5_48_crypto_readiness_replay_reachability_contract.md`.
- First contract commit
  `74aa69e70d22529b717723c4ebb61943e7b98473` was independently rejected
  pending three P1 corrections. This handoff describes the corrected
  docs-only candidate; no implementation is authorized before a new
  independent acceptance.
- Contract base:
  `31b400d95e19dfc88b1a9d4d4269406ef7e152d4`, verified equal to
  `origin/main` before writing.
- Contract branch:
  `codex/v5.48-readiness-replay-reachability-contract`.
- This is a docs-only contract slice. No V5.48 runtime behavior has been
  implemented or proven.
- Accepted prerequisite: V5.47 provides the import-pure, fully-defaulted,
  deterministic `crypto-readiness-replay` command and immutable readiness
  publication. V5.48 proposes only the reviewed autonomy reachability wiring.

## Checkout And Ownership

- Worktree:
  `C:\Users\danie\Desktop\algo_trader\.claude\worktrees\v547-import-pure-readiness-replay`.
- Sole contract writer: Codex V5.48 contract agent.
- Starting tracked, staged, unstaged, and untracked state was clean.
- No reset, clean, stash, rebase, restore, force push, merge, or promotion
  occurred.
- Contract-owned files are exactly:
  `docs/design/v5_48_crypto_readiness_replay_reachability_contract.md`
  and this handoff.

## Evidence-Based Contract Decisions

1. Preserve the exact existing readiness lane tokens:
   `run_supervised_readiness_trial_to_seed_r1_evidence` for absent and
   `rerun_supervised_readiness_trial` for stale.
2. On accepted implementation, classify both as
   `EXECUTION_AUTO_OFFLINE` with exact command
   `python -m algotrader.cli crypto-readiness-replay`.
3. Allowlist both tokens to the exact argv
   `("crypto-readiness-replay",)`.
4. Remove the dead `rerun_offline_daily_cycle_chain` autonomy
   classification/allowlist entry. The underlying manual M446 command remains;
   only its unreachable autonomy promise is removed.
5. Replace one-way registry coverage with exact two-way closure:
   producer tokens equal classification keys, and auto-offline classification
   keys equal allowlist keys.
6. An `EXECUTION_AUTO_OFFLINE` action has standing repository/offline
   authority under `AGENTS.md`, so its `gate` is empty. The exact allowlist,
   canonical-target checks, preflight, dry-run default, and explicit
   `--apply` are controls, not missing-authority gates. No current prose/test
   may retain `unattended_execution_authority` as its blocker.
7. Prefer an `EXECUTION_AUTO_OFFLINE` plan action over an
   `EXECUTION_OFFLINE_OPERATOR_INPUT` action at the same or lower severity.
   In a canonical empty lab, planner/executor therefore select crypto replay
   rather than merely naming the SPY operator-input seed.
8. Preserve fail-closed whole-system empty-lab reporting:
   `ALL_LANES_ABSENT_ACTION`, empty aggregate lane, evidence required, and
   non-empty blocker remain unchanged. The plan separately names the safe
   per-lane executable step.
9. Because the exact argv has no output-root, AUTO_OFFLINE eligibility is
   restricted to the exact packet under the verified executing repository:
   `runs/crypto_supervised_readiness_trial/latest/readiness_packet.json`.
   Planner and executor independently reject noncanonical `--lanes-root`,
   readiness overrides, cwd/root, path escape, and supplied-plan/report
   mismatch before any runner call. Planner copies the existing supervisor
   lane `artifact_path` into the plan action solely for comparison; executor
   compares it with top-level `lanes_root`, its config/overrides, a freshly
   re-derived report/plan, and the module-derived canonical packet. It is never
   propagated as an output argument.
10. Reject an explicitly supplied global `--profile` option for replay before
   its runner is called. Broker, paper-read, receipt, and credential-looking
   options remain unavailable.
11. V5.47 proves only the replay-module closure, not the full
    `python -m algotrader.cli crypto-readiness-replay` launcher. V5.48 adds
    static classification of the central CLI's eager pure
    `paper_order_policy`/package dependencies plus a fresh exact-process
    protected-environment, dispatch, canonical-artifact, and post-run
    forbidden-`sys.modules` proof.
12. Preserve executor preflight, exact argv, sanitized child environment,
    dry-run default, safety ledger, and V5.47 module
    import-purity/atomicity/provenance.
13. No LLM or agent enters the executable hot path.

## Evidence Conflict Resolved

- The current crypto readiness lane has `max_age_hours=0`, and the V5.47
  packet has no `generated_at` or `as_of` freshness field. Real current
  evidence therefore cannot normalize to stale.
- V5.48 does not use the fixed replay `decision_start`, filesystem mtime, wall
  clock, hidden environment, or an argv timestamp as invented freshness.
- Absent reachability is the active end-to-end capability. The stale token is
  bound structurally to the same exact command, per the accepted V5.46
  separate-token decision, but remains dormant until a later independently
  frozen authenticated-freshness contract.
- An implementation report must not claim a real stale refresh.

## Corrected P1 Boundaries

- **Canonical target**: fixed argv plus fixed verified repository cwd is the
  only output binding. No output path is propagated or invented. Arbitrary
  lane roots/overrides and mismatched serialized plans/reports fail in both
  planner and executor, with zero runner calls and no refresh claim.
- **Authority truthfulness**: collaborators already hold standing offline
  authority. AUTO_OFFLINE has no authority gate; `--apply` is a deliberate
  control. Dead M446/unattended-authority assertions must be removed from
  current source, tests, and V5.38/V5.39 operational prose.
- **Exact launcher**: the central CLI eagerly imports the currently pure
  `paper_order_policy` module and package initialization before lazy replay
  dispatch. That larger executed path needs its own static and fresh-process
  proof; V5.47's named replay tuple must not be overclaimed.

## Safety And External Effects

- Presence-only preflight found no `APP_PROFILE` or checked Alpaca/APCA
  credential aliases. Values were never requested or printed.
- No test, network, broker, market-data, paper, order, or live operation was
  run while writing the contract.
- No order was submitted, cancelled, replaced, closed, or liquidated.
- Effective paper quantity/notional caps: not applicable.
- Broker receipt/reconciliation: not applicable.
- `live_authorized=false`; live trading and live-capital activity remain
  prohibited.

## Verification Required Before Contract Yield

- `git diff --check`.
- `git status --short`.
- `git diff --name-only HEAD -- src`.
- `git ls-files --others --exclude-standard src tests`.
- Coherent correction commit on the existing contract branch.
- Push only the contract branch, re-fetch, and prove local/remote equality.

## Next Highest-Leverage Safe Action

Independently review
`docs/design/v5_48_crypto_readiness_replay_reachability_contract.md`
against the current checkout. Challenge the removal of the dead M446 autonomy
entry, the two-way registry closure, empty AUTO_OFFLINE gate, canonical
planner/executor target checks, exact central-launcher proof, planner priority,
empty-lab aggregate versus per-lane agreement, explicit-profile refusal, and
the boundary between active absent reachability and dormant stale-token
binding.

Do not implement V5.48 until that independent review accepts the frozen
contract. After acceptance, route the implementation to one sole writer under
the contract's exact file and verification scope.
