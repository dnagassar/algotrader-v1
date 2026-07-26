# Active Implementation Checkpoint

## Classification

- Milestone: `V5.48 — crypto readiness replay reachability`.
- Contract candidate:
  `docs/design/v5_48_crypto_readiness_replay_reachability_contract.md`.
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
6. Prefer an `EXECUTION_AUTO_OFFLINE` plan action over an
   `EXECUTION_OFFLINE_OPERATOR_INPUT` action at the same or lower severity.
   In an empty lab, planner/executor therefore select the crypto replay rather
   than merely naming the SPY operator-input seed.
7. Preserve fail-closed whole-system empty-lab reporting:
   `ALL_LANES_ABSENT_ACTION`, empty aggregate lane, evidence required, and
   non-empty blocker remain unchanged. The plan separately names the safe
   per-lane executable step.
8. Reject an explicitly supplied global `--profile` option for replay before
   its runner is called. Broker, paper-read, receipt, and credential-looking
   options remain unavailable.
9. Preserve executor preflight, exact argv, sanitized child environment,
   dry-run default, safety ledger, and V5.47 import-purity/atomicity/provenance.
10. No LLM or agent enters the executable hot path.

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
- Coherent docs-only commit.
- Push only the contract branch, re-fetch, and prove local/remote equality.

## Next Highest-Leverage Safe Action

Independently review
`docs/design/v5_48_crypto_readiness_replay_reachability_contract.md`
against the current checkout. Challenge the removal of the dead M446 autonomy
entry, the two-way registry closure, planner priority, empty-lab aggregate
versus per-lane agreement, explicit-profile refusal, and the boundary between
active absent reachability and dormant stale-token binding.

Do not implement V5.48 until that independent review accepts the frozen
contract. After acceptance, route the implementation to one sole writer under
the contract's exact file and verification scope.
