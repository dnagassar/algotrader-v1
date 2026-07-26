# Active Implementation Checkpoint

## Classification

- Milestone: `V5.51 — read-only SPY market-data network refresh
  reachability contract`.
- Frozen contract:
  `docs/design/v5_51_read_only_spy_market_data_network_refresh_reachability_contract.md`.
- Review status: **round-2 REQUEST CHANGES, corrections applied, pending
  independent round-3 review. No implementation is authorized.** Round-1
  findings (1 P0, 4 P1, 3 P2) remain recorded in the contract's "Round-1
  Independent Review" section. Round-2 findings (1 P0, 3 P1, 3 P2) and their
  corrections are recorded in the contract's new "Round-2 Independent
  Review: Findings And Corrections" section, per orchestrator adjudication
  that every finding is required.
- Implementation status: **still contract-only. No `src/` or `tests/` file
  was changed. No implementation is authorized until an independent review
  round accepts.** On acceptance, the contract authorizes exactly one
  implementation milestone/PR with two ordered, jointly reviewed commits
  (adapter caps + safety preflight, then executor/planner/scheduled-task
  reachability) — no second contract is required for that pair.
- This milestone is the operator's selected **option 2** from
  `docs/design/v5_50_offline_autonomy_lane_eligibility_analysis.md`
  (authorize the read-only market-data intake path); unchanged from the
  original freeze.
- Prior active milestone, now superseded as the checkpoint but still
  promoted to `origin/main`: `V5.48 — crypto readiness replay
  reachability` (evidence commit `38399df`, implementation `6d4838b`). See
  "History: V5.32-V5.50" below for the retained prior record.

## Round-2 Findings Corrected This Round

| # | Severity | Finding | Correction |
| --- | --- | --- | --- |
| 1 | P0 | Import-purity test banned `AlpacaPaperConfig`/`require_paper_profile` outright, but the mandatory `evaluate_live_capital_interlock` preflight transitively requires both; the contract's claim that the interlock "never reads a credential secret" was also false. | "Read-Only Market-Data Is Not Live Trading" now permits `AlpacaPaperConfig`/`require_paper_profile` only as members of `live_capital_interlock`'s own closure, never a direct seam import; "Mandatory Live-Capital Interlock Preflight" now states truthfully that the interlock loads repr-hidden Alpaca credential strings into memory but never logs/serializes/discloses/forwards/uses them for Tiingo or broker access, and the seam's own code never touches a secret field directly. |
| 2 | P1 | `load_tiingo_api_key_from_dotenv` was specified to run once for the presence check and again via `token_lookup` — two dotenv reads per apply. | "Freeze One Credential Source" now freezes one private, cached credential-provider object that reads the dotenv file exactly once per apply invocation and serves both the presence check and `token_lookup` from that cached value; the executor process itself never holds the token as a plain string outside that object. |
| 3 | P1 | The Task Scheduler `<Actions><Exec>` command embedded `<UTC timestamp resolved at trigger time>` — non-executable prose — with no wrapper/fallback mechanism, while wrapper/fallback mechanisms are otherwise banned. | "Windows Scheduled Task Update" freezes a new reviewed wrapper, `scripts/run_spy_read_only_network_executor.ps1`, that captures `[DateTimeOffset]::UtcNow.ToUniversalTime().ToString('o', [CultureInfo]::InvariantCulture)` exactly once and invokes the Python module with that literal value; the XML now invokes this exact wrapper, no placeholder anywhere executable. "In-process" is clarified to mean the Python module spawns no adapter/network child; Task Scheduler launching the PS-to-Python host wrapper is unaffected by that guarantee. |
| 4 | P1 | The four-attempt session ledger budget was read-then-append with no concurrency control — two racing invocations could both read the same prior count. | New "Concurrency And Ledger Locking" section freezes an exclusive OS advisory lock (`runs/autonomy_network_executor/ledger.lock`, stdlib `msvcrt.locking`/`fcntl.flock` wrapper, 5s timeout, `ledger_lock_unavailable` on timeout) held from ledger validation through provider load, reservation write (flush+fsync), the HTTP call, and completion write (flush+fsync), released in `finally`. Budget now counts unique reservation ids (pending or completed), so a crash between reservation and completion still fail-closed consumes budget. |
| 5 | P2 | Ambiguous whether dry-run writes a ledger record ("no artifact write beyond one dry-run ledger record" contradicted "fully side-effect-free"). | Dry-run is now specified as fully side-effect-free: zero ledger/lock/artifact write of any kind, zero credential/HTTP access. Every "beyond one dry-run ledger record" phrase removed. |
| 6 | P2 | Unspecified whether a failing live-capital interlock verdict should hard-refuse dry-run the way it hard-refuses apply. | Dry-run always evaluates the interlock for informational `apply_eligible` reporting but never hard-refuses on a failing/unset verdict; only apply mode hard-refuses (`live_capital_interlock_blocked`, exit `2`). |
| 7 | P2 | No exit-code scheme distinguished success, already-qualified no-op, pending dry-run, and an apply that reached the network but ended in an audited blocked outcome. | New "Exit Codes" section: `0` accepted apply or already-qualified/no-action; `1` pending valid dry-run, or apply after an actual HTTP attempt ending in a fully audited blocked outcome; `2` any pre-HTTP refusal (parser/root/path/as-of/lock/ledger/interlock/credential/attempt-cap). |

## Authority And Safety Boundaries

- `AGENTS.md` was given one further narrow edit this round: the
  credential-preflight sentence now states that credential presence is not
  a *per-operation* gate for an explicitly scoped paper operation **or** an
  explicitly scoped, authorized read-only market-data operation (previously
  named only the paper case), while unchanged elsewhere — no live
  prohibition weakened, no endpoint/method scope broadened.
- This milestone performed **zero** network access, credential load,
  broker access, or paper/live mutation. It is doc-only, same as prior
  rounds.
- The round-2-corrected contract closes a real safety-claim defect (the
  interlock's dependency closure does read Alpaca credential strings into
  memory, even though it never discloses them) rather than merely adding
  precision; the import-purity test is now satisfiable and enforces
  reachability (only through `live_capital_interlock`) rather than a
  blanket name ban that contradicted the seam's own mandatory dependency.
  It also adds a real concurrency control (OS advisory lock) that did not
  exist in the round-1-corrected text, and a complete exit-code contract.
  No live-broker or live-capital access is authorized. Live capital remains
  operator-gated until burn-in completes.

## Checkout And Ownership

- Implementation worktree (this session):
  `C:\Users\danie\Desktop\algo_trader\.claude\worktrees\v551-readonly-market-data-contract`,
  branch `claude/v5.51-readonly-spy-market-data-contract`.
- Verified base for this round's remediation: `9cfc183` (round-1-corrected
  V5.51 contract, itself based on `6797e95`/`b79c721`), clean working tree,
  upstream `origin/claude/v5.51-readonly-spy-market-data-contract` up to
  date at takeover.
- **Round-2 remediation committed and pushed: `703615f`** (`git log -1
  --format="%H %cI"` → `703615f752f7acec6efa9c4e0eaf1d07649d433e
  2026-07-26T18:40:13-04:00`). Post-push checkout evidence, re-verified this
  pass: `git rev-parse --abbrev-ref HEAD` → `claude/v5.51-readonly-spy-market-data-contract`;
  `git rev-parse --abbrev-ref --symbolic-full-name @{u}` →
  `origin/claude/v5.51-readonly-spy-market-data-contract`; `git status
  --porcelain=v2 --branch` → `branch.ab +0 -0` (local exactly matches
  upstream, nothing ahead or behind, working tree clean).
- **Post-commit re-read for internal contradictions (this pass):** read the
  full corrected contract (1123 lines) end to end, specifically checking the
  "Read-Only Market-Data Is Not Live Trading" section near the end for the
  stale, unsatisfiable transitive-import ban round-2 finding #1 targeted.
  Confirmed the live text (lines 988-1062) already carries the round-2
  correction — the ban is scoped to *direct* seam imports and to
  `require_live_capital_interlock`/broker-SDK/mutation-callables with no
  exception, while `AlpacaPaperConfig`/`require_paper_profile` are
  permitted only as members of `live_capital_interlock`'s own transitive
  closure. Grepped every remaining `AlpacaPaperConfig`/`require_paper_profile`
  occurrence (11 hits) and every remaining `seven canonical`/`beyond one
  dry-run ledger record`/`<UTC timestamp resolved at trigger time>`/`1 per
  UTC day` occurrence: all surviving hits are inside the "Round-1/Round-2
  Independent Review" finding tables or the "Windows Scheduled Task Update"
  correction note, describing the *prior, superseded* wording for the
  historical record — none remain in live specification text. No
  contradiction found; no further edit to the contract or `AGENTS.md` was
  needed or made this pass.
- Sole implementation writer for this round's contract-remediation-only
  milestone; Codex remains orchestrator/reviewer per operator instruction.
- Preflight (presence-only, no values), re-run this pass: `APP_PROFILE` not
  set; no Alpaca/APCA credential alias set (`ALPACA_API_KEY`,
  `ALPACA_API_KEY_ID`, `APCA_API_KEY_ID`, `ALPACA_SECRET_KEY`,
  `ALPACA_API_SECRET_KEY`, `APCA_API_SECRET_KEY`); no `TIINGO_API_KEY` set.

## Files Changed This Round

- `AGENTS.md` (one-sentence narrow edit: the default-test credential
  preflight sentence now names both the paper-operation and the
  read-only-market-data-operation case for the "not a per-operation gate"
  statement; no other line changed).
- `docs/design/v5_51_read_only_spy_market_data_network_refresh_reachability_contract.md`
  (substantially corrected: new "Round-2 Independent Review: Findings And
  Corrections" section recording all 7 findings and their fixes; new
  "Concurrency And Ledger Locking" and "Exit Codes" sections; "Read-Only
  Market-Data Is Not Live Trading" rewritten around a satisfiable,
  reachability-based import-purity rule; "Mandatory Live-Capital Interlock
  Preflight" corrected to truthfully describe credential-string loading and
  the dry-run non-hard-refusal rule; "Freeze One Credential Source"
  rewritten around one cached dotenv read; "Session Attempt Budget",
  "Retry And Idempotency Behavior", "Fail-Closed Refusal Conditions",
  "Execution Architecture", "Windows Scheduled Task Update", and the
  ledger-field list in "Sanitized Receipt And Provenance" updated for
  locking, reservation/completion semantics, and the new exit-code scheme;
  "seven canonical paths" corrected to "eight" throughout to include the
  new lock file).
- `docs/agent_context/active_implementation.md` (this file, overwritten in
  place; no historical handoff copy created).

No `src/` or `tests/` file was read for any purpose other than grounding
this round's corrections precisely in the existing code: confirmed
`live_capital_interlock.py` imports `AlpacaPaperConfig` and
`require_paper_profile` from `algotrader.config` and calls
`AlpacaPaperConfig.from_env(source)` and `require_paper_profile(config)`;
confirmed `AlpacaPaperConfig.from_env` reads
`ALPACA_API_KEY`/`ALPACA_API_KEY_ID`/`APCA_API_KEY_ID` and
`ALPACA_SECRET_KEY`/`ALPACA_API_SECRET_KEY`/`APCA_API_SECRET_KEY`-family
values into `alpaca_api_key`/`alpaca_secret_key` fields declared
`field(repr=False)` (hidden from `repr()`/`str()`, but genuinely populated).
None of those files was modified.

## Verification Evidence

This is a doc-only change, so no test suite exercises new behavior. Ran the
checks applicable to doc-only work per `AGENTS.md`, both at commit time and
re-run this pass after the commit/push to confirm the pushed state matches:

- **At commit time (round-2 remediation, `703615f`):** `git status --short`
  reported exactly the three files listed under "Files Changed This Round"
  staged; `git diff --check` clean; `git diff --name-only HEAD -- src`
  empty; `git ls-files --others --exclude-standard src tests` empty;
  presence-only preflight confirmed all seven variables (`APP_PROFILE`, six
  Alpaca/APCA aliases, `TIINGO_API_KEY`) absent.
- **This pass (post-push re-verification, no contract edit made):**
  `git status --short` → empty (nothing staged or unstaged — the working
  tree exactly matches `703615f`); `git diff --check` → clean; `git diff
  --name-only HEAD -- src` → empty; `git ls-files --others
  --exclude-standard src tests` → empty; presence-only preflight re-run,
  all seven variables confirmed absent again, no values printed either
  time.
- No network or broker command was run in either pass.
  `.\scripts\verify_offline.ps1` and the default pytest suite were **not
  run**: this remains a documentation-only diff with no `src`/`tests`
  impact (confirmed again this pass — `git diff --name-only HEAD -- src`
  and the untracked-file check are both empty), so per `AGENTS.md`'s
  "Preflight and Verification" section there is no changed `src`/`tests`
  behavior for them to exercise. Recorded truthfully as "not run" rather
  than claimed as passing evidence, consistent with prior rounds' practice.

## Unresolved Risks

- The contract is now precise and its two P0/P1-class safety claims
  (import-purity satisfiability, credential-secret truthfulness,
  single-dotenv-read, executable scheduler command, and lock-based
  concurrency) have been corrected, but it has not yet been independently
  re-reviewed. A round-3 reviewer may still find a gap in, for example, the
  exact lock-timeout interaction with the adapter's own 20-second HTTP
  timeout (the lock is held across the HTTP call, so a slow attempt can make
  a genuinely legitimate second invocation wait the full 5-second lock
  timeout and refuse — this is intentional fail-closed serialization per the
  operator's remediation instructions, but is a new judgment call this round
  introduced and has not been independently checked).
- `docs/OPERATOR_RUNBOOK.md`'s V5.38 section (`auto_offline` example
  `etf-sma-offline-daily-cycle-rerun-m446`) still describes a pre-V5.48
  allowlist shape that no longer matches
  `AUTONOMY_EXECUTOR_ALLOWLIST`'s current two-readiness-token contents.
  Not touched by this milestone (out of scope), unchanged from prior
  rounds' note.
- Commit A (adapter caps) and commit B (executor/planner/scheduled-task,
  now including the lock mechanism, the cached credential provider, and the
  new PowerShell wrapper) are specified precisely but neither has been
  written; the exact Python implementation of the 20:10 ET cutoff, the
  `msvcrt.locking`/`fcntl.flock` wrapper, the ledger corruption/schema
  check, and the import-purity test's allowed-path-through-interlock
  assertion are contract-level specifications, not yet code, and could
  still surface an unanticipated edge case once written against the real
  adapter internals.

## Next Action

Independent **round-3** review of the corrected V5.51 contract
(`docs/design/v5_51_read_only_spy_market_data_network_refresh_reachability_contract.md`).
No implementation is authorized until that review accepts. On acceptance,
the contract itself authorizes exactly one implementation milestone/PR with
two ordered commits reviewed together — no separate implementation contract
is needed.

Unchanged hard gate: **live capital remains operator-gated until burn-in
completes.** Nothing in this milestone touches that.

---

## History: V5.32-V5.50 (condensed)

Full detail for each milestone below remains in its own frozen contract
under `docs/design/` and in git history; this section is a condensed
index, not the authoritative record.

- **V5.48 — crypto readiness replay reachability.** Accepted and
  promoted to `origin/main` at evidence commit `38399df` (implementation
  `6d4838b`, contract `d6e408e`). Both readiness tokens
  (`run_supervised_readiness_trial_to_seed_r1_evidence`,
  `rerun_supervised_readiness_trial`) classified `EXECUTION_AUTO_OFFLINE`
  with fixed command `python -m algotrader.cli crypto-readiness-replay`;
  `AUTONOMY_EXECUTOR_ALLOWLIST` maps both to that exact argv; planner and
  executor independently verify canonical root/cwd/target binding; a
  fresh-process, import-purity-audited launcher test proves zero
  protected-environment access and zero forbidden modules loaded.
  Independently re-verified by the orchestrator against `600bf72`: 216
  targeted tests passed, `verify_offline.ps1` passed, structural claims
  confirmed at the source level. The reported full 10033-test suite run
  was not independently reproduced.
- **V5.49 — authenticated readiness freshness contract.** Frozen
  (`44f5e32`), reviewed with REQUEST CHANGES and four defects corrected
  (`fad3b82`), then **closed unimplemented by operator decision**: the
  readiness replay is a pure function of fixed constants, so a freshness
  field would attest re-execution recency, not readiness recency.
  `rerun_supervised_readiness_trial` remains deliberately dead-but-registered
  (required by V5.48's two-way set-equality invariants), pinned by three
  tests in `test_autonomy_supervisor.py`. Rejected design record:
  `docs/design/v5_49_authenticated_readiness_freshness_contract.md`. Two
  general lessons carried forward: (1) `_compute_bundle_id` in
  `crypto_supervised_readiness_trial_core.py` must exclude any future
  packet field that varies between runs or idempotency breaks; (2)
  `_staleness`'s `as_of_fields` resolver is flat/top-level and shared
  across all lanes — nested paths need a cross-lane regression pass, not a
  local fix.
- **V5.50 — offline autonomy lane eligibility analysis.** Surveyed all
  six registry lanes at `8406aef`: no second lane is eligible for
  `EXECUTION_AUTO_OFFLINE` (binding criterion: input self-containment —
  every other lane's artifact is a function of real-world data:
  live market-data fetch, an operator-supplied CSV, or frozen V5.25
  terminal evidence that does not exist in the checkout). Structural
  conclusion: offline autonomy cannot be broadened by wiring alone; it is
  gated on a safe way to *acquire* external input. Three options were
  offered; **the operator selected option 2** (authorize the market-data
  intake path), now frozen as V5.51 above. Full analysis (eligibility
  finding preserved, options/next-action corrected to reflect the
  decision):
  `docs/design/v5_50_offline_autonomy_lane_eligibility_analysis.md`.
- **V5.51 — read-only SPY market-data network refresh reachability
  contract.** Frozen (`6797e95`), reviewed round-1 REQUEST CHANGES and
  corrected (`9cfc183`), reviewed round-2 REQUEST CHANGES and corrected
  (this commit). Still contract-only; pending independent round-3 review.
  See "Classification" and "Round-2 Findings Corrected This Round" above.
