# Active Implementation Checkpoint

## Classification

- Milestone: `V5.46 — contract-first design for an import-pure crypto
  readiness replay command`.
- Date: `2026-07-25`.
- Contract document: `docs/design/v5_46_import_pure_readiness_replay_contract.md`
  (frozen standalone; zero `src`/`tests` files touched).
- This is a design-contract milestone, not an implementation milestone.
  No executor, planner, supervisor, CLI, or test behavior changed. No
  operator gate applies (design/documentation is standing collaborator
  authority under `AGENTS.md`).
- Not strategy-profit, paper-order, broker-mutation, activation, or
  live-trading evidence.

## Current Checkout And Ownership

- Worktree
  `C:\Users\danie\Desktop\algo_trader\.claude\worktrees\v546-import-pure-readiness-replay-contract`,
  branch `claude/v5.46-import-pure-readiness-replay-contract`.
- Implementation writer: `Claude Code`. Scope of claim: this working
  tree only.
- Started at `9f0d45d` (`V5.45 correction: fix base-commit claim and
  reachability enumeration errors`), verified before any edit: branch,
  `HEAD`, `git status`, staged/unstaged/untracked diffs, and
  credential/profile presence booleans were all clean/absent/false.
  This worktree/branch carries the full accepted V5.45 history
  (`...1394be0 -> c1311b6 -> 9f0d45d`) — it was not forked fresh from
  `main`, and no rebase or branch switch was performed.

## Prior Milestone (V5.45, Unchanged By This One)

`V5.45 — read-only executor reachability boundary audit`
(`docs/design/v5_45_executor_reachability_boundary_audit.md`) found no
safe candidate to allowlist and selected V5.46 (this milestone) as its
next action. That audit's conclusions are unchanged and re-derived, not
just re-cited, in this contract's "Root-Cause Import-Purity Analysis"
section.

## What This Milestone Did

Wrote `docs/design/v5_46_import_pure_readiness_replay_contract.md`, a
frozen, standalone contract for the command V5.45 identified as the
"only structurally sound way to create real reachability without
weakening an invariant." Re-derived, not re-cited, the exact import
defect: walked the full transitive module-level import closure of
`tomorrow_crypto_trader_demo.py` file-by-file in this checkout and
proved the **sole** impure edge in the entire chain is one line
(`tomorrow_crypto_trader_demo.py:26-28`, importing
`crypto_market_data_symbol_normalization` from `alpaca_sdk_client`,
which pulls in `algotrader.config`/`live_capital_interlock`/
`alpaca_client` at module level purely by being imported). Also traced,
at the runtime level, that the one scenario probe that calls
`run_tomorrow_crypto_trader_demo(broker_observed_readiness=True, ...)`
returns at an early `if not broker_read_authorized` guard
(`tomorrow_crypto_trader_demo.py:3343-3349`) before ever reaching the
deferred `AlpacaPaperConfig`/`AlpacaSdkClient` import — confirming the
new command's fixed `allow_alpaca_paper_read=False` makes that import
provably dead code on its path, not merely usually-untaken.

The contract specifies a three-part change set for the *next*
milestone (none executed here):

1. Extract `crypto_market_data_symbol_normalization` (function,
   dataclass, two constants) out of `alpaca_sdk_client.py` into a new
   pure leaf module, with a compatibility re-export so
   `tests/unit/test_alpaca_sdk_client.py`'s existing imports keep
   working unmodified.
2. Repoint `tomorrow_crypto_trader_demo.py`'s one import to the new pure
   module — the single line that, once changed, makes
   `tomorrow_crypto_trader_demo.py` (and therefore
   `crypto_supervised_readiness_trial.py`, which imports nothing else
   non-stdlib) import-pure at module level.
3. Add a new, narrowly-scoped module `crypto_readiness_replay.py` and
   CLI subcommand `crypto-readiness-replay` that calls
   `run_crypto_supervised_readiness_trial` with
   `broker_observed_readiness=False, allow_alpaca_paper_read=False,
   receipt_root=None` hardcoded (no corresponding CLI flags exist at
   all, not merely defaulted) — a stronger invariant than reusing the
   existing `crypto-readiness-verify` command directly, whose argparse
   surface could in principle grow a dangerous flag later without this
   command being affected.

The contract also specifies, in full: the exact CLI argv and allowlist
argv (`("crypto-readiness-replay",)`, zero flags); output-path/schema
compatibility (writes the identical `readiness_packet.json` shape at
the identical `runs/crypto_supervised_readiness_trial/latest` path, so
the lane reader needs zero changes); deterministic input/time semantics
(inherited unchanged, plus confirmation that hardcoding
`receipt_root=None` makes the one wall-clock-reading validation branch
unreachable); a two-test import-purity proof pattern for
`test_dependency_direction.py` (one asserting the named closure is
broker/credential/profile-free, one asserting the tracked closure is
exhaustive, since the first test alone only checks modules it is told
to check); the dependency-direction analysis; a specified (not yet
implemented) atomic-write hardening for `_write_trial_artifacts`, since
this command is meant for unattended execution unlike today's manual
`crypto-readiness-verify`; fail-closed exit-code inheritance; and every
existing safety invariant this contract preserves unmodified (fixed argv
allowlisting, executor preflight, sanitized child environment, zero
network/broker/credential/profile access, no paper mutation,
`live_authorized=false`).

**Resolved the absent-vs-stale token question**: separate tokens,
sharing one eventual allowlist argv. `LaneSpec.next_actions` already
carries two distinct keys for this lane
(`STATE_STALE: "rerun_supervised_readiness_trial"` vs.
`STATE_ABSENT: "run_supervised_readiness_trial_to_seed_r1_evidence"`,
`autonomy_supervisor.py:353,357`) — collapsing them would be a
regression in existing diagnostic resolution, not a simplification this
contract introduces, and it would repeat the exact "distinguishable
system states collapsed onto one value" defect class this branch's
history (V5.37a/V5.38a/V5.42a/V5.44) has repeatedly found and fixed.
Only the `absent` token is planned for reclassification in the later
wiring step, because `crypto_supervised_readiness_trial`'s
`max_age_hours=0` (`autonomy_supervisor.py:346`) makes `stale`
structurally unreachable for this lane today; the `stale` token is left
classified as-is (operator-gated, no-offline-command) since
reclassifying an unreachable branch would be speculative, untestable
wiring.

The contract's own "Later Registry/Classification/Allowlist Wiring"
section fully specifies, but does not perform, the exact
`AUTONOMY_ACTION_CLASSIFICATION` entry, the one
`AUTONOMY_EXECUTOR_ALLOWLIST` entry, the `cli.py` subparser, and the
tests to re-derive at that time — explicitly deferred as its own,
separately-reviewed step so an import-purity refactor and a
reachability-scope change are never bundled into one diff.

## Verification Evidence

- `git branch --show-current`, `git rev-parse HEAD`, and
  `git status --porcelain=v1` at session start: branch
  `claude/v5.46-import-pure-readiness-replay-contract`, `HEAD`
  `9f0d45d9d02ed77aae157a619c2319df82939a1d`, working tree clean.
- Credential/profile precheck at session start: `APP_PROFILE`,
  `ALPACA_API_KEY_ID`, `ALPACA_API_SECRET_KEY`,
  `ALPACA_PAPER_API_KEY_ID`, `ALPACA_PAPER_API_SECRET_KEY`,
  `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`,
  `ALGO_TRADER_ALLOW_NETWORK_TESTS`, and
  `RUN_ALPACA_PAPER_INTEGRATION_TESTS` — all absent/false.
- Every import-graph claim in the contract was verified by directly
  reading each cited file's `import`/`from` block in this checkout
  (`alpaca_sdk_client.py`, `tomorrow_crypto_trader_demo.py`,
  `crypto_supervised_readiness_trial.py`, every
  `orchestration`/`risk`/`portfolio`/`signals`/`screener`/`core` module
  in the transitive closure, and `autonomy_next_plan.py`/
  `autonomy_offline_executor.py`/`autonomy_supervisor.py`/`cli.py` for
  the wiring sections) — not re-derived from memory or re-cited from
  the V5.45 audit without independent re-checking.
- `git diff --check` — clean.
- `git status --short` — only the two docs files this milestone wrote.

## Safety And External Effects

No credential value was read, enumerated, created, replaced, renamed,
deleted, or exposed. No network, broker, or market-data request
occurred. No paper profile was entered and no paper mutation or order
action occurred. No canary, strategy, paper automation, live access, or
trading effect was activated. No `src` or `tests` file was modified; no
`AUTONOMY_EXECUTOR_ALLOWLIST`, `AUTONOMY_ACTION_CLASSIFICATION`,
`AUTONOMY_SUPERVISOR_LANES`, or `cli.py` entry was added or changed.
Effective paper caps: not applicable (no paper operation was
attempted). Live-authorized state: `false`.

## Unresolved Risks

- Everything in this contract's "Design" and "Later Wiring" sections is
  a specification, not a proof by execution: the implementer must
  re-derive the import closure against the actual post-Part-1/2 source
  (this contract says so explicitly) rather than trusting this
  document's closure list unchecked, since Parts 1-2 change two files
  the closure depends on.
- The `no_offline_command_available` gate's comment text for
  `rerun_supervised_readiness_trial` and
  `run_supervised_readiness_trial_to_seed_r1_evidence` (recorded as a
  V5.45 risk) is still unresolved by this contract — the later wiring
  step reclassifies `run_supervised_readiness_trial_to_seed_r1_evidence`
  but leaves `rerun_supervised_readiness_trial`'s comment text
  unchanged, since its underlying gate reason (structurally unreachable
  `stale` state) is unaffected by this contract.
- The atomic-write hardening for `_write_trial_artifacts` is specified
  but not implemented; if a future implementer allowlists
  `crypto-readiness-replay` for unattended execution before adding that
  hardening, a killed-mid-write process could leave a partially-written
  `readiness_packet.json` for the supervisor lane to read. The contract
  flags this explicitly as a should-fix-before-allowlisting item, not a
  should-fix-before-merging-the-command item.

## Next Highest-Leverage Safe Action

**Implement Parts 1-3 of the V5.46 contract**
(`docs/design/v5_46_import_pure_readiness_replay_contract.md`, "Design:
Three-Part Change Set" and "Tests And Acceptance Criteria"): extract
`crypto_market_data_symbol_normalization` into its own pure module,
repoint `tomorrow_crypto_trader_demo.py`'s one import, and add the new
`crypto_readiness_replay.py` module plus its `cli.py` subparser and the
two new `test_dependency_direction.py` import-purity tests — all nine
acceptance-criteria items in the contract's "Tests And Acceptance
Criteria" section 1-9, **without** touching
`AUTONOMY_ACTION_CLASSIFICATION` or `AUTONOMY_EXECUTOR_ALLOWLIST` in the
same change. This is source-code implementation work (not
design/documentation), so it should be scoped, executed, and verified
(targeted tests + `test_dependency_direction.py` + `verify_offline.ps1`)
as its own milestone, separate from the later reachability-wiring step
this contract also specifies but explicitly defers.

This is not started by this milestone; the contract exists so that
milestone can be independently reviewed before any implementation
begins.
