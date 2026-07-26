# Active Implementation Checkpoint

## Classification

- Milestone: `V5.51 — read-only SPY market-data network refresh
  reachability contract`.
- Frozen contract:
  `docs/design/v5_51_read_only_spy_market_data_network_refresh_reachability_contract.md`.
- Review status: **round-1 REQUEST CHANGES, corrections applied, pending
  independent round-2 review.** Round-1 findings (1 P0, 4 P1, 3 P2) and their
  corrections are recorded in the contract's own "Round-1 Independent
  Review: Findings And Corrections" section, per orchestrator adjudication
  that every finding is required.
- Implementation status: **still contract-only. No `src/` or `tests/` file
  was changed. No implementation is authorized until round-2 review
  accepts.** On acceptance, the contract now authorizes exactly one
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

## Authority And Safety Boundaries

- `AGENTS.md` was updated this round (narrow, canonical edit) to state
  standing, provider-generic authority explicitly: every collaborator,
  regardless of agent/model/tool, may within an explicitly scoped task load
  and use an approved read-only market-data provider credential through the
  minimum trusted provider boundary and perform exact-destination read-only
  market-data GETs through repository adapters, bounded by positive finite
  request/time/response-byte/row caps, deterministic preflight, sanitized
  provenance/receipt/audit, credential nondisclosure, and fail-closed exact
  endpoint/method validation. This does not authorize broker/account
  mutation, live-broker access, trading, orders, positions, or live capital.
  `TIINGO_API_KEY`/approved-provider-credential presence was added to the
  credential-free default-test preflight, and a stop condition was added for
  endpoint/method/cap/audit/provenance failure.
- This milestone performed **zero** network access, credential load,
  broker access, or paper/live mutation. It is doc-only, same as the
  original freeze.
- The corrected contract binds the future implementation to a materially
  more precise safety envelope than the original freeze: an in-process
  (no child process) module with a three-flag CLI
  (`--as-of`/`--apply`/`--format`), a mandatory
  `evaluate_live_capital_interlock` preflight in both dry-run and apply
  mode, a single canonical `.env`-sourced credential path (process-env
  `TIINGO_API_KEY` explicitly ignored), a session-scoped four-attempt ledger
  budget (one initial plus three retries, matching the scheduled task's own
  `RestartOnFailure` policy) replacing the original's conflicting
  one-per-UTC-day cap, a 20:10 America/New_York provider-publication cutoff
  for expected-session resolution, exact numeric caps (8,388,608 response
  bytes; 20,000 provider rows), and a new, truthful planner execution class
  (`EXECUTION_AUTHORIZED_NETWORK_READ_ONLY`) replacing the stale
  `EXECUTION_OPERATOR_GATED` label for the one action that now has a real,
  seam-exercisable path. No live-broker or live-capital access is
  authorized. Live capital remains operator-gated until burn-in completes.

## Checkout And Ownership

- Implementation worktree (this session):
  `C:\Users\danie\Desktop\algo_trader\.claude\worktrees\v551-readonly-market-data-contract`,
  branch `claude/v5.51-readonly-spy-market-data-contract`.
- Verified base for this round's remediation: `6797e95` (originally frozen
  V5.51 contract, itself based on `b79c721`), clean working tree, upstream
  `origin/claude/v5.51-readonly-spy-market-data-contract` up to date at
  takeover.
- Sole implementation writer for this round's contract-remediation-only
  milestone; Codex remains orchestrator/reviewer per operator instruction.
- Preflight (presence-only, no values): `APP_PROFILE` not set; no
  Alpaca/APCA credential alias set; no `TIINGO_API_KEY` set; no
  network-test alias set. Re-checked before commit.

## Files Changed This Round

- `AGENTS.md` (narrow edit: standing provider-generic read-only
  market-data authority paragraph; `TIINGO_API_KEY`/provider-credential
  added to the credential-free default-test preflight bullet; one new stop
  condition for market-data fetch endpoint/method/cap/audit/provenance
  failure).
- `docs/design/v5_51_read_only_spy_market_data_network_refresh_reachability_contract.md`
  (substantially rewritten: new "Round-1 Independent Review: Findings And
  Corrections" section recording all 8 findings and their fixes; new
  "Implementation Milestone Shape", "Execution Architecture", "Fixed
  Internal Adapter Configuration", "Mandatory Live-Capital Interlock
  Preflight", "Freeze One Credential Source", "Session Attempt Budget",
  "Planner Classification: `authorized_network_read_only`", and "Windows
  Scheduled Task Update" sections; "Deterministic Expected-Session
  Semantics", "Finite Caps", "Retry And Idempotency Behavior", "Sanitized
  Receipt And Provenance", and "Fail-Closed Refusal Conditions" rewritten to
  remove every "e.g."/"implementation choice" ambiguity round-1 flagged).
- `docs/agent_context/active_implementation.md` (this file, overwritten in
  place; no historical handoff copy created).

No `src/` or `tests/` file was read for any purpose other than grounding the
contract's corrections precisely in the existing adapter
(`etf_sma_adjusted_spy_data_refresh.py`: `run_spy_adjusted_data_refresh`,
`ETFAdjustedDataRefreshConfig`, `load_tiingo_api_key_from_dotenv`,
`_tiingo_http_get`, `_HTTP_TIMEOUT_SECONDS`,
`_default_expected_latest_bar_date`), the live-capital interlock
(`live_capital_interlock.py`: `evaluate_live_capital_interlock`,
`LiveCapitalInterlockVerdict.to_dict`), the planner/executor registries
(`autonomy_next_plan.py`, `autonomy_offline_executor.py`:
`EXECUTION_*` constants, `AUTONOMY_EXECUTOR_ALLOWLIST`,
`_GATE_NETWORK_MARKET_DATA`), the existing import-purity test pattern
(`tests/unit/test_dependency_direction.py`'s crypto-readiness-replay launcher
scan), the Windows Task Scheduler template
(`docs/design/spy_eod_market_data_refresh_scheduled_task.xml`: confirmed
`RestartOnFailure Interval=PT15M Count=3`, i.e. one initial run plus three
retries — the exact basis for the corrected four-attempt session budget),
and the operator runbook's existing 20:10 America/New_York boundary
(`docs/OPERATOR_RUNBOOK.md`'s "Authoritative SPY EOD Market-Data Refresh"
section). None of those files was modified.

## Verification Evidence

This is a doc-only change, so no test suite exercises new behavior. Ran the
checks applicable to doc-only work per `AGENTS.md`:

- `git status --short` → reports exactly the three files listed above before
  commit.
- `git diff --check` → clean (no whitespace-conflict markers).
- `git diff --name-only HEAD -- src` → empty (no `src/` change).
- `git ls-files --others --exclude-standard src tests` → empty (no
  untracked `src`/`tests` files).
- Presence-only credential/profile preflight (`APP_PROFILE`, Alpaca/APCA
  aliases, `TIINGO_API_KEY`, network-test aliases) confirmed absent before
  and after.
- No network or broker command was run. `.\scripts\verify_offline.ps1` and
  the default pytest suite were not required to change and were not
  re-run for a documentation-only diff with no source impact; this is
  recorded rather than claimed as evidence, unchanged from the original
  freeze's practice.

## Unresolved Risks

- The corrected contract is now precise enough to implement, but it has not
  yet been independently re-reviewed. A round-2 reviewer may still find a
  gap in, for example, the exact ledger-corruption handling
  (`ledger_state_corrupt`) or the early-close 20:10 ET cutoff reasoning; both
  are new judgment calls this round introduced to close round-1's gaps and
  neither was independently checked before this commit.
- `docs/OPERATOR_RUNBOOK.md`'s V5.38 section (`auto_offline` example
  `etf-sma-offline-daily-cycle-rerun-m446`) still describes a pre-V5.48
  allowlist shape that no longer matches
  `AUTONOMY_EXECUTOR_ALLOWLIST`'s current two-readiness-token contents.
  Not touched by this milestone (out of scope), unchanged from the original
  freeze's note.
- Commit A (adapter caps) and commit B (executor/planner/scheduled-task)
  are specified precisely but neither has been written; the exact Python
  implementation of the 20:10 ET cutoff, the ledger corruption check, and
  the import-purity test's forbidden-symbol list are contract-level
  specifications, not yet code, and could still surface an unanticipated
  edge case once written against the real adapter internals.

## Next Action

Independent **round-2** review of the corrected V5.51 contract
(`docs/design/v5_51_read_only_spy_market_data_network_refresh_reachability_contract.md`).
No implementation is authorized until that review accepts. On acceptance,
the contract itself now authorizes exactly one implementation milestone/PR
with two ordered commits reviewed together — no separate implementation
contract is needed.

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
