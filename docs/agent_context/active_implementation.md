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
  review rejected it: its import-purity proof was unsound (checked only
  the one edge it fixed, not the six edges its own proposed mechanism
  would actually find).
- Second pass (first correction) committed and pushed at `9dd7e14`
  (`V5.46 correction: fix unsound import-purity proof, atomic-publish
  ordering, authority language, and behavior-change framing`). This
  fixed the edge count but tried to close the remaining five edges with
  `importlib.import_module("...")` calls confined to their existing
  call sites, reasoning that a plain `ast.Call` is invisible to
  `ast.Import`/`ast.ImportFrom` matching. Independent review rejected
  this too, correctly identifying it as test evasion (hiding a real,
  executable dependency edge from one specific checker) rather than
  import purity (removing or isolating the edge). See "What This
  Correction Did" below for the fully redesigned fix. This checkpoint
  entry replaces the prior ones describing `81124ad`'s and `9dd7e14`'s
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

Independent review rejected the first correction (`9dd7e14`) on a
single, precise, correct ground: its fix for the five deferred
forbidden imports — confining each behind an
`importlib.import_module("...")` call at its existing call site — is
invisible to the specific `ast.Import`/`ast.ImportFrom`-based checker
the proposed test used, but the dependency itself is still real and
still executes at runtime. That is test evasion, not import purity;
the instruction was to remove or isolate the edges, not to encode them
so one particular scanner can't see them. This correction deletes the
entire `importlib`-based design and replaces it with a real
dependency-inversion boundary.

**Redesign, re-verified against the actual checkout (not assumed) at
every step:**

1. `tomorrow_crypto_trader_demo.py`: `_build_alpaca_read_client` is
   **deleted outright** (not moved-and-called-dynamically). Its one
   call site now reads `client = broker_client or
   (broker_client_factory() if broker_client_factory is not None else
   None)` — when `client is None`, the **already-existing**
   `blocked_adapter_unavailable` fail-closed branch fires; no new code
   needed. `_read_open_orders` switches to a plain-keyword protocol
   call (`method(status_filter="open", symbol_filter=symbol)` instead
   of constructing `AlpacaRecentOrderQuery`), verified against
   `_FakeBrokerReadClient.get_orders(self, query=None)`'s exact
   signature to confirm the `except TypeError: return method()`
   fallback preserves every existing test's asserted outcome. `main()`
   is **removed from this file entirely** and moved verbatim to a new,
   explicitly impure composition-root module,
   `tomorrow_crypto_trader_demo_cli.py`, which imports both the pure
   core and a new `tomorrow_crypto_trader_demo_broker_client_adapter.py`
   (holding the real Alpaca-client construction, freely impure, outside
   the closure) and wires the factory in via the DI parameter that
   already exists on `run_tomorrow_crypto_trader_demo`'s public
   signature today.
2. This is a **genuine, disclosed, narrow invocation-path change**, not
   a hidden one: `main()`'s CLI cannot carry a Python callable, and
   `scripts/run_tomorrow_crypto_trader_demo.ps1`/
   `scripts/validate_tomorrow_crypto_trader_demo.ps1` (both verified by
   direct reading) invoke `python -m
   algotrader.execution.tomorrow_crypto_trader_demo` by exact module
   path — those two scripts and the one test assertion
   (`test_scripts_expose_simbroker_and_validator_contracts`'s expected
   fragment) must be updated to point at
   `tomorrow_crypto_trader_demo_cli` instead. Verified (by reading the
   test file's own import list) that **no other test** references
   `main()` or the module path in-process, so this is the only test
   change Part 2 requires.
3. `crypto_supervised_readiness_trial.py`: split into a new pure core
   (`crypto_supervised_readiness_trial_core.py`, everything except
   `_validate_offline_receipt`, with a `receipt_validator` parameter
   injected instead of an internal adapter call — failing closed with
   `blocked_receipt_validator_not_provided` when a `receipt_root` is
   given without one) and a facade (the existing file, now openly and
   statically importing the adapter, correctly, since it is outside the
   closure) that auto-supplies the validator so every existing caller
   (`cli.py`'s `crypto-readiness-verify`, this file's own `--receipt-
   root`-carrying `main()`, and existing tests) keeps working with
   **zero** test or script changes — verified this split, unlike
   `tomorrow_crypto_trader_demo.py`'s, has no `python -m <exact path>`
   constraint forcing an invocation-path change.
4. New static test added (not merely the two closure tests carried
   over): directly bans `importlib.import_module`/`__import__` calls
   and any string literal naming a forbidden module, anywhere in the
   tracked closure — closing the exact gap the rejected design
   exploited and guarding against related evasions (`getattr`-based
   indirection, string-keyed lookups).
5. Preserved unchanged from the first correction: the package-aware
   closure-completeness walker; the packet-last bundle-commit atomic-
   publication protocol with its interruption test; the equal-
   authority/no-operator-gate framing for the later wiring step;
   "additive, not zero-behavior-change" framing for the new CLI
   command; and the exact `V5.47` milestone name.

The full itemized diff against `9dd7e14` is recorded in the contract
document's own "What Changed In This Correction" section.

## Verification Evidence

- `git branch --show-current`, `git rev-parse HEAD`, and
  `git status --porcelain` at the start of this correction: branch
  `claude/v5.46-import-pure-readiness-replay-contract`, `HEAD`
  `9dd7e1478ff8ee84b50d445c57bf1e11080cc46e` (the previously-rejected
  first-correction commit), working tree clean.
- Credential/profile precheck: `APP_PROFILE`,
  `ALGO_TRADER_ALLOW_NETWORK_TESTS`, and
  `RUN_ALPACA_PAPER_INTEGRATION_TESTS` — all absent/false.
- Re-read, directly in this checkout, every call site and test this
  redesign depends on: `_read_open_orders`'s current body,
  `_broker_observed_readiness_preview`'s client-resolution branch and
  its already-existing `client is None` fail-closed path, both PS1
  scripts' exact invocation lines, `test_scripts_expose_simbroker_and_validator_contracts`'s
  exact assertions, the test file's full top-of-file import list (to
  confirm no in-process `main()` usage), `_FakeBrokerReadClient`'s
  `get_orders` signature, and every current caller of `receipt_root` on
  `run_crypto_supervised_readiness_trial` (`cli.py`, this module's own
  `main()`, and `test_crypto_read_only_paper_observation.py`) — not
  re-derived from memory or from either prior pass without independent
  re-checking.
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

- Everything in the contract's "Design" section remains a
  specification, not a proof by execution: no code was written or run
  in this or either prior pass. The implementer must re-verify every
  cited line number and test signature against the actual source at
  implementation time.
- Part 2's invocation-path change (`tomorrow_crypto_trader_demo.py` ->
  `tomorrow_crypto_trader_demo_cli.py`) is a genuine, narrow API/script
  change, not backward-compatible in the strict "same `python -m`
  target" sense — this is disclosed and justified in the contract, not
  hidden, but an implementer or reviewer expecting zero script/test
  changes anywhere should be aware this one exists and is required, not
  optional.
- The new static test banning dynamic loading and forbidden string
  literals needs careful tuning against false positives on legitimate
  documentation/comments quoting a forbidden module name — the contract
  flags this as an open implementer decision, not a solved one.
- The `no_offline_command_available` gate's comment text for
  `rerun_supervised_readiness_trial` and
  `run_supervised_readiness_trial_to_seed_r1_evidence` (recorded as a
  V5.45 risk) remains unresolved by this contract.
- The bundle-commit atomic-write protocol is specified but not
  implemented; mandatory before allowlisting, not before merging Parts
  1-4.

## Next Highest-Leverage Safe Action

**Implement Parts 1-4 of the twice-corrected V5.46 contract**
(`docs/design/v5_46_import_pure_readiness_replay_contract.md`, "Design:
Four-Part Change Set, True Dependency Inversion" and "Tests And
Acceptance Criteria"), in this order: (1) extract
`crypto_market_data_symbol_normalization` into its own pure module; (2)
in `tomorrow_crypto_trader_demo.py`, delete `_build_alpaca_read_client`
and its self-construct fallback, switch `_read_open_orders` to the
plain-keyword protocol call, and remove `main()` into a new
`tomorrow_crypto_trader_demo_cli.py` composition root backed by a new
`tomorrow_crypto_trader_demo_broker_client_adapter.py` — updating both
PS1 scripts and the one test assertion that reference the old module
path; (3) split `crypto_supervised_readiness_trial.py` into a pure core
(injected, fail-closed `receipt_validator`) and an unmodified-behavior
facade; (4) add `crypto_readiness_replay.py` (importing from the pure
core, never the facade) and its `cli.py` subparser, plus every test in
the contract's "Tests And Acceptance Criteria" (all thirteen items,
including the new dynamic-loading/string-literal ban test) —
**without** touching `AUTONOMY_ACTION_CLASSIFICATION` or
`AUTONOMY_EXECUTOR_ALLOWLIST`. This is source-code implementation work,
to be scoped, executed, and verified as its own milestone, separate
from the later reachability-wiring step the contract specifies but
reserves for a subsequent contract (a review-separation choice, not an
authorization gap).

This is not started by this correction; the contract exists so that
milestone can be independently reviewed before any implementation
begins.
