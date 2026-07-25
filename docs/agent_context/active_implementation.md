# Active Implementation Checkpoint

## Classification

- Milestone: `V5.46 — contract-first design for an import-pure crypto
  readiness replay command`, third correction.
- Contract:
  `docs/design/v5_46_import_pure_readiness_replay_contract.md`.
- This is a frozen design-contract milestone, not source
  implementation. It changes no runtime capability, action
  classification, allowlist, lane registry, broker behavior, or
  autonomous reachability.
- Not strategy-profit, paper-order, broker-mutation, activation, or
  live-trading evidence.

## Current Checkout And Ownership

- Worktree:
  `C:\Users\danie\Desktop\algo_trader\.claude\worktrees\v546-import-pure-readiness-replay-contract`.
- Branch: `claude/v5.46-import-pure-readiness-replay-contract`.
- Correction base and pre-edit remote feature tip:
  `6f1566dbdfd50fba9d515fff148f3021d7bc0c9c`.
- The worktree was clean before this correction. Branch, HEAD, staged
  and unstaged diffs, untracked files, and remote feature ref were
  inspected directly. No reset, clean, stash, rebase, branch switch,
  or force operation occurred.
- Writer for this correction: Codex orchestrator. Claude was assigned
  the same bounded correction, but its service session limit terminated
  the run before it read or modified the checkout. Codex verified the
  tree was still clean before taking over.
- A separate read-only reviewer rejected the intermediate third-
  correction diff on six checkout-proven issues: incomplete price-read
  delegation, wrong packet/support trust direction, an evadable AST
  length heuristic, overbroad crash-durability wording, missing facade
  helper imports, and underspecified central CLI behavior. All six are
  corrected in the current diff. Re-review then found Decimal-unsafe
  JSON rendering and two ambient profile/credential-read paths; the
  current diff also corrects both. Independent final re-review returned
  `ACCEPT`; its sole non-blocking credential-alias reporting typo was
  corrected before commit.
- Prior contract commits remain in history:
  `81124ad` (unsound partial import proof), `9dd7e14`
  (dynamic-loading test evasion), and `6f1566d` (real dependency
  inversion but false multi-file atomicity claim).

## Prior Accepted Capability

- V5.45 remains the latest independently accepted capability in this
  stacked history: a read-only executor reachability audit with both
  reachability-difference directions empty after correction.
- V5.46 proves no runtime capability yet. It specifies the next bounded
  implementation slice and its acceptance tests.

## What This Third Correction Changes

1. Rejects `6f1566d`'s in-place packet-last protocol. The current
   validator reads the root packet and root manifest and verifies
   manifest hashes; replacing supporting files and manifest before the
   packet therefore invalidates the old bundle during the claimed safe
   interruption window.
2. Specifies immutable
   `generations/<bundle_id>/...` supporting bundles and one atomically
   replaced root `readiness_packet.json` commit marker. `bundle_id`
   commits to packet semantics plus content-artifact hashes/sizes, and
   the root packet's `artifact_integrity` commits to all four immutable
   generation files. The manifest does not hash the packet, avoiding a
   circular dependency while keeping the packet as trust root.
3. Requires a regression-capable interruption test: generation A must
   remain byte-identical and validate after a forced failure immediately
   before the B pointer replace; an un-faulted retry must commit and
   validate B; the rejected in-place algorithm must fail the same test.
4. Discloses the supporting-artifact path change, requires legacy
   fixed-root validation, and requires an implementation-time audit of
   every consumer that hard-codes the four former root paths. The
   review already found and specified the required update to
   `test_crypto_supervised_readiness_trial.py`'s hard-coded
   `operating_report.md` read.
5. Preserves the facade's exact explicit
   `run_crypto_supervised_readiness_trial` signature. The pure core
   gains injected receipt-validator, broker-client-factory, and paper-
   environment seams; the impure facade supplies all three, preserving
   the existing two-flag broker-observed path. It explicitly
   imports/re-exports existing
   tested/CLI symbols, including `SCHEMA_VERSION`, `MILESTONE_NAME`,
   `_json_safe`, and `_mapping`.
6. Requires the broker wrapper to expose all thirteen probed read-only
   names while deliberately not forwarding mutation methods.
7. Extends the paper-observation source bundle to every new/relocated
   executable module in the trial/read path.
8. Replaces the evadable length heuristic with concrete docstring-aware
   AST string folding, dynamic-import machinery bans, and positive/
   negative synthetic tests.
9. Specifies exact central CLI parser, dispatch, forwarding, text/JSON
   rendering, and exit codes, while clarifying that this correction
   commit itself adds no CLI command.
10. Limits the atomicity proof to process interruption on filesystems
    with verified same-volume atomic rename/replace semantics; power-
    loss durability is not claimed.
11. Moves ambient profile/credential-presence reads to impure
    composition roots, propagates one explicit deterministic offline
    snapshot to all six tomorrow-demo calls, makes `None` distinct from
    `{}`, and requires a runtime environment guard that raises on any
    protected-key access. The exact JSON handler uses `_json_safe` and
    is tested with a real Decimal-bearing packet.

## Verification Evidence

- Preflight at `6f1566d`: branch and remote feature ref identical;
  staged, unstaged, and untracked state clean.
- Credential/profile presence checks, without values:
  `APP_PROFILE`, `ALPACA_API_KEY`, `ALPACA_API_KEY_ID`,
  `ALPACA_API_SECRET_KEY`, `ALPACA_SECRET_KEY`, `APCA_API_KEY_ID`,
  `APCA_API_SECRET_KEY`, `ALGO_TRADER_ALLOW_NETWORK_TESTS`, and
  `RUN_ALPACA_PAPER_INTEGRATION_TESTS` all absent/false.
- Direct source inspection confirmed:
  - current validation reads `readiness_packet.json` and
    `manifest.json`, then verifies manifest artifact hashes;
  - current writing overwrites the packet and four supporting files at
    fixed paths;
  - `test_crypto_supervised_readiness_trial.py` currently hard-codes
    `output_root / "operating_report.md"` and must follow the packet's
    `artifact_paths` after generational publication;
  - the broker preview gates on `get_account`, `get_positions`,
    `get_orders`, and `list_assets`, then probes nine quote/trade/bar
    aliases for genuine price evidence;
  - `_run_scenario_matrix` forwards broker flags without a client/
    factory today and would regress if the removed self-builder were not
    replaced by facade-to-core factory injection;
  - `_environment_preflight()` reads `APP_PROFILE` and credential
    aliases three times per packet today, and both tomorrow broker/
    paper paths use `paper_environment or
    _paper_environment_from_os()`, including when broker observation is
    not requested;
  - the facade's retained `main()` calls `_json_safe` and `_mapping`;
  - the paper-observation source bundle currently binds the monolithic
    trial file and must add the relocated/new modules;
  - existing tests import `SCHEMA_VERSION`,
    `run_crypto_supervised_readiness_trial`,
    `validate_crypto_supervised_readiness_trial`, and
    `_validate_offline_receipt` from the facade.
- No source/test execution is claimed for this docs-only correction.
  Independent review returned `ACCEPT`. Final `git diff --check`,
  status, and name-only evidence is recorded immediately before commit.

## Safety And External Effects

- No credential value was read, requested, printed, logged, persisted,
  or exposed.
- No network, market-data, broker, paper, or live operation occurred.
- No order was submitted, cancelled, replaced, closed, or liquidated.
- Effective paper caps: not applicable.
- Receipt/reconciliation status: not applicable to this docs-only
  correction.
- `live_authorized=false`.
- No `src`, `tests`, script, classification, allowlist, or lane-registry
  file is changed by this correction.

## Unresolved Risks

- The corrected contract remains a design, not execution evidence. The
  pure-module split, facade, broker wrapper, CLI, generational writer,
  validator, and tests do not exist yet.
- The implementation must verify same-filesystem directory rename and
  root `os.replace` process-interruption semantics; any platform on
  which those guarantees cannot be established must fail closed.
  Power-loss/post-reboot durability is not proven by flush/close and is
  outside this slice.
- Immutable generations accumulate until a separately designed
  retention/garbage-collection policy exists. Cleanup is out of this
  slice and must never delete the generation referenced by the current
  root packet.
- Legacy fixed-root bundle support and any additional hard-coded
  supporting-path consumers must be enumerated and tested during
  implementation; one known test consumer is already specified.
- The static proof is bounded to its concrete AST rules and runtime
  smoke test; it does not prove the absence of every conceivable
  runtime code-generation technique.
- The `no_offline_command_available` comment text identified by V5.45
  remains stale and is not changed here.
- Independent review accepted this third correction; implementation
  remains unstarted.

## Next Highest-Leverage Safe Action

After independent acceptance, implement Parts 1-4 of the corrected
V5.46 contract as V5.47 in a new branch based exactly on the accepted
contract commit: extract the pure normalization helper; split the
tomorrow demo into pure logic, a thirteen-name read-only broker adapter,
and an impure CLI composition root; split the supervised trial into pure
core and exact-signature facade with all three dependency seams; extend
source-provenance binding; add the import-pure replay command and fully
specified CLI subparser/dispatch; implement the root-committed
immutable-generation publication/validator protocol and all specified
regression tests. Do not change
`AUTONOMY_ACTION_CLASSIFICATION`,
`AUTONOMY_EXECUTOR_ALLOWLIST`, or autonomous reachability in that
slice.
