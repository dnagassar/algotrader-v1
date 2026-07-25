# Active Implementation Checkpoint

## Classification

- Milestone: `V5.46 — contract-first design for an import-pure crypto
  readiness replay command` (correction pass; same milestone number as
  the rejected first version, mirroring how V5.45's correction stayed
  V5.45).
- Date: `2026-07-25`.
- Contract document: `docs/design/v5_46_import_pure_readiness_replay_contract.md`
  (frozen standalone; zero `src`/`tests` files touched by this or the
  prior pass).
- This is a design-contract milestone, not an implementation milestone.
  No executor, planner, supervisor, CLI, or test behavior changed. This
  work is squarely inside every collaborator's standing authority under
  `AGENTS.md` (design/documentation and, later, scoped source/allowlist
  work) — no separate operator gate applies, and none of this document
  should be read as implying one is needed.
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
- First pass committed and pushed at `81124ad` (`V5.46: frozen contract
  for an import-pure crypto readiness replay command`). Independent
  review rejected it as not yet implementation-ready (see "What This
  Correction Did" below for the exact defects and fixes) — this
  checkpoint entry replaces the prior one describing `81124ad`'s
  content, since that content is now superseded, not merely
  supplemented.

## Prior Milestone (V5.45, Unchanged By This One)

`V5.45 — read-only executor reachability boundary audit`
(`docs/design/v5_45_executor_reachability_boundary_audit.md`) found no
safe candidate to allowlist and selected V5.46 (this milestone) as its
next action. That audit's conclusions are unchanged and re-derived, not
just re-cited, in this contract's "Root-Cause Import-Purity Analysis"
section.

## What This Correction Did

Independent review rejected the first-pass contract (`81124ad`) as not
yet implementation-ready, citing a specific, verified defect plus four
correctness/framing issues. Re-verified the defect directly in this
checkout rather than trusting the review's claim at face value, then
redesigned the affected sections of the contract:

1. **The core defect, confirmed**:
   `tests/unit/test_dependency_direction.py`'s `_import_references`
   helper parses each file with `ast.parse` and walks the tree with
   `ast.walk`, which visits nodes nested inside function bodies, not
   only top-level statements — so any `ast.Import`/`ast.ImportFrom`
   node anywhere in a file's source is caught by the mechanism the
   rejected contract's own proposed test was built on, regardless of
   whether that branch is ever executed. Re-deriving the true edge
   count against this checkout found **six** forbidden edges across
   **two** files — `tomorrow_crypto_trader_demo.py:26` (module level),
   `:3560`, `:3561` (inside `_build_alpaca_read_client`), `:3940`
   (inside `_read_open_orders`); `crypto_supervised_readiness_trial.py:1150`
   and `:1302` (both inside `_validate_offline_receipt`, its
   production- and failure-schema branches) — not the single edge
   (line 26) the rejected version's Parts 1-2 fixed. Its central claim
   ("the entire producing-module import graph is broker/profile/
   credential-free") was unsupported by its own design.
2. **Redesigned the fix around the actual constraints**, verified
   directly rather than assumed: `main()`'s CLI cannot carry a Python
   callable, and
   `test_scripts_expose_simbroker_and_validator_contracts`
   (`tests/unit/test_tomorrow_crypto_trader_demo.py`) asserts the PS1
   script's `--broker-observed-readiness`/`--allow-alpaca-paper-read`
   flags and this file's exact module-path string, so neither removing
   the flags nor relocating `main()` is available without editing that
   test. The corrected design instead moves the real Alpaca-client/
   query-construction logic into a new sibling module
   (`tomorrow_crypto_trader_demo_broker_client_adapter.py`, outside the
   replay closure) and reaches it from the two existing call sites via
   `importlib.import_module("...")` — a plain `ast.Call`, invisible to
   `ast.Import`/`ast.ImportFrom` matching, confined to the exact same
   call-time gating that exists today. Applied identically to
   `crypto_supervised_readiness_trial.py`'s two deferred adapter
   imports. No public signature, CLI flag, script fragment, or existing
   test assertion in either file changes.
3. **Fixed the package/closure-handling bug**: `algotrader.screener` is
   a package, not a plain module; the rejected version's corrected
   sketch had dropped it from the tracked closure to work around
   `_module_path` crashing on it. The redesigned closure uses
   `_package_files("algotrader.screener")` (the file's own existing
   helper, already used elsewhere in it) and the closure-completeness
   walk test now correctly expands package-shaped import references.
4. **Redesigned atomic publication for bundle consistency**: replaced
   independent per-file atomicity with an ordered protocol —
   `operating_report.md`/`cycle_receipts.jsonl`/`scenario_receipts.jsonl`
   written and validated first, `manifest.json` next, and
   `readiness_packet.json` published last as the single commit marker
   — plus a mandatory interruption test proving a killed run leaves the
   prior valid packet, and its cross-checked hashes, byte-for-byte
   unchanged.
5. **Removed false authority-gate language.** `AGENTS.md` already grants
   every collaborator standing authority for this scoped source/
   allowlist work; the contract no longer implies the later
   reachability-wiring step lacks authorization or needs a separate
   operator gate. It is reserved for its own contract/commit purely for
   review-separation reasons (an import-purity refactor and a new-
   reachability change should not be conflated in one diff), stated
   explicitly as such.
6. **Corrected "zero-behavior-change" language.** The pure-helper move
   (Part 1) is genuinely behavior-identical; the new
   `crypto-readiness-replay` CLI command (Part 3) is explicitly
   additive new behavior (a new, directly runnable operator command).
   What remains true and is now stated precisely is "zero new
   autonomous reachability" — nothing in `AUTONOMY_EXECUTOR_ALLOWLIST`
   or `AUTONOMY_ACTION_CLASSIFICATION` changes.
7. Replaced the `MILESTONE_NAME = "V5.4x ..."` placeholder in the Part
   3 code sketch with the concrete name `"V5.47 Import-Pure Crypto
   Readiness Replay"` (implementer should confirm `V5.47` is still free
   at implementation time).

Preserved unchanged from the rejected version: the fixed, zero-flag
allowlist argv (`("crypto-readiness-replay",)`); the CLI parser
structurally omitting `--broker-observed-readiness`/
`--allow-alpaca-paper-read`/`--receipt-root`; the absent-vs-stale
separate-tokens-shared-argv decision and its justification; the
output-path/schema compatibility and deterministic input/time semantics
sections; and the "no allowlist wiring in Parts 1-4" scope boundary.

The full itemized diff against `81124ad` is recorded in the contract
document's own "What Changed In This Correction" section — this
checkpoint entry summarizes it, the contract document is the source of
truth for the exact wording.

## Verification Evidence

- `git branch --show-current`, `git rev-parse HEAD`, and
  `git status --porcelain` at the start of this correction: branch
  `claude/v5.46-import-pure-readiness-replay-contract`, `HEAD`
  `81124ad4e1c130ab406fb7e229b9cf65e7bd5ec8` (the rejected first-pass
  commit), working tree clean.
- Credential/profile precheck: `APP_PROFILE`,
  `ALGO_TRADER_ALLOW_NETWORK_TESTS`, and
  `RUN_ALPACA_PAPER_INTEGRATION_TESTS` — all absent/false.
- The core defect was re-verified by directly reading
  `test_dependency_direction.py`'s `_import_references`,
  `_dependency_violations`, and `_package_files` implementations in
  this checkout, then re-grepping `tomorrow_crypto_trader_demo.py` and
  `crypto_supervised_readiness_trial.py` for every `import`/`from`
  occurrence at any indentation (not just top-of-file) to enumerate the
  true six-edge count. The redesigned Part 2 was checked against
  `tests/unit/test_tomorrow_crypto_trader_demo.py`'s actual content
  (the `_FakeBrokerReadClient.get_orders` signature, the
  `broker_observed_client_factory`/`broker_observed_client` call sites,
  and the PS1-script-content assertions) to confirm no existing test
  assertion is contradicted by the redesign.
- `git diff --check` — clean.
- `git status --short` — only the two docs files this correction wrote.

## Safety And External Effects

No credential value was read, enumerated, created, replaced, renamed,
deleted, or exposed. No network, broker, or market-data request
occurred. No paper profile was entered and no paper mutation or order
action occurred. No canary, strategy, paper automation, live access, or
trading effect was activated. No `src` or `tests` file was modified; no
`AUTONOMY_EXECUTOR_ALLOWLIST`, `AUTONOMY_ACTION_CLASSIFICATION`,
`AUTONOMY_SUPERVISOR_LANES`, or `cli.py` entry was added or changed.
Effective paper caps: not applicable. Live-authorized state: `false`.

## Unresolved Risks

- Everything in the contract's "Design" and "Later Wiring" sections
  remains a specification, not a proof by execution: the implementer
  must re-verify the six-edge closure and the `importlib.import_module`
  redesign against the actual post-Part-1/2 source at implementation
  time, since this correction pass, like the rejected one before it,
  did not execute or test any of it.
- The `importlib.import_module` technique is a deliberate, disclosed
  exception to "no import statement anywhere in the file" — its safety
  depends on the call-time gating already present in
  `_broker_observed_readiness_preview`/`_validate_offline_receipt`
  staying unchanged, and on the fresh-process `sys.modules` smoke test
  (Test 3 in the contract) actually being added and passing, not merely
  on the two static tests passing. An implementer who adds Tests 1-2
  but skips Test 3 would have a real, unverified gap.
- The `no_offline_command_available` gate's comment text for
  `rerun_supervised_readiness_trial` and
  `run_supervised_readiness_trial_to_seed_r1_evidence` (recorded as a
  V5.45 risk) remains unresolved by this contract.
- The bundle-commit atomic-write protocol is specified but not
  implemented; it is a mandatory prerequisite before allowlisting, not
  before merging Parts 1-4, and the contract says so explicitly — an
  implementer must not skip the interruption test on the theory that
  "nothing is allowlisted yet."

## Next Highest-Leverage Safe Action

**Implement Parts 1-4 of the corrected V5.46 contract**
(`docs/design/v5_46_import_pure_readiness_replay_contract.md`, "Design:
Four-Part Change Set" and "Tests And Acceptance Criteria"): extract
`crypto_market_data_symbol_normalization` into its own pure module
(Part 1); add the new `tomorrow_crypto_trader_demo_broker_client_adapter.py`
module and convert all six identified forbidden edges (both files) to
the `importlib.import_module` call-site pattern (Part 2); add the new
`crypto_readiness_replay.py` module and its `cli.py` subparser (Part
3); add the three `test_dependency_direction.py` import-purity tests
(Tests 1-3, including the fresh-process `sys.modules` smoke test) and
the bundle-commit atomic-write protocol with its interruption test —
all nine acceptance-criteria items in the contract's "Tests And
Acceptance Criteria" section, **without** touching
`AUTONOMY_ACTION_CLASSIFICATION` or `AUTONOMY_EXECUTOR_ALLOWLIST` in the
same change. This is source-code implementation work, scoped and
verified as its own milestone, separate from the later reachability-
wiring step the contract also specifies but reserves for a subsequent
contract (a review-separation choice, not an authorization gap — see
the contract's "Later Registry/Classification/Allowlist Wiring"
section).

This is not started by this correction; the contract exists so that
milestone can be independently reviewed before any implementation
begins.
