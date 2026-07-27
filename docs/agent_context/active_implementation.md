# Active Implementation Checkpoint

## Classification

- Milestone: `V5.51 — read-only SPY market-data network refresh reachability contract`.
- Frozen contract:
  `docs/design/v5_51_read_only_spy_market_data_network_refresh_reachability_contract.md`.
- Review status: **Round-5 orchestrator review of `db2b646` REQUESTED CHANGES (2 P1, 1 P2, 1 P3 — see "Round-5 Orchestrator Review" below). Correction implemented, verified, committed (`0acc5df`, `c0d1176`, plus the call-operator fix). NOT self-accepted — awaiting independent acceptance per charter.**
- Implementation status: **Full default pytest PASS on the corrected tree (`c0d1176`): 10071 passed, 5 skipped, exit 0, 26:54. The prior HEAD `db2b646` did NOT pass (1 failed).**

## Scope and Implementations Completed

### Commit A — Adapter Hardening (`e2e40b4`)
- Hardened `src/algotrader/execution/etf_sma_adjusted_spy_data_refresh.py`:
  - Added `_MAX_RESPONSE_BYTES = 8_388_608` (8 MiB) byte limit to `_tiingo_http_get`.
  - Added `_MAX_PROVIDER_ROWS = 20_000` row limit to `_read_provider_json_bytes`.
  - Enforced fail-closed behavior emitting `MarketDataFetchError("provider_response_too_large")` and `ValidationError("provider_row_count_exceeded")`.
- Added unit tests in `tests/unit/test_spy_adjusted_data_refresh.py`.

### Commit B — Seam Implementation & Planner Reachability (`af1b377`)
- Created in-process seam `src/algotrader/execution/autonomy_read_only_network_executor.py`.
- Updated planner `src/algotrader/execution/autonomy_next_plan.py` with `EXECUTION_AUTHORIZED_NETWORK_READ_ONLY` and narrow `ActionClass.__post_init__` carve-out.
- Created host wrapper script `scripts/run_spy_read_only_network_executor.ps1`.
- Updated scheduled task template `docs/design/spy_eod_market_data_refresh_scheduled_task.xml`.

### Orchestrator Review Remediation (`a0ce62d`, `9471e87`)
1. **Finding 1 (P1) — Strict UTC `--as-of` Validation & Clean CLI Errors**:
   - Updated `_parse_as_of` to enforce explicit timezone-aware UTC datetime (`dt.tzinfo is not None` and `dt.utcoffset() == timedelta(0)`), failing closed with `as_of_invalid` (exit 2) for missing, naive, or non-UTC offset strings.
   - Updated `main()` with custom `_SanitizedArgumentParser` to catch missing/invalid CLI args cleanly and emit exit 2 with JSON `{"action_token": ..., "refusal_category": "parser_invalid_argument", "exit_code": 2}` without uncaught `SystemExit`.
   - Added unit tests `test_as_of_validation_strict_utc_refusals` and `test_cli_main_handles_missing_or_invalid_args_cleanly`.
2. **Finding 2 (P1) & Edge Case Hardening — Comprehensive Ledger Validation**:
   - Updated `_read_and_validate_ledger` to fail closed as `ledger_corrupt` (exit 2, zero ledger write) if `ledger_path` exists but is a directory.
   - Enforced exact 24-key frozen schema check, shared constant checks, and per-status type/value invariant checks (`"pending"`, `"completed"`, `"refused"`).
   - Enforced strict reservation linkage: every `"completed"` event MUST reference a preceding `"pending"` reservation for the same session; duplicate or orphan completions fail closed as `ledger_corrupt`. Rejects duplicate pending reservation IDs as `ledger_corrupt`.
   - Enforced matching metadata between pending reservation and completion event (`session_id`, `as_of`, `attempt_number`, `interlock_verdict`, `credential_present`).
   - Rejects empty lines or whitespace-mismatched lines as `ledger_corrupt`.
   - Preserved crash-surviving unmatched `"pending"` reservations as valid and budget-consuming.
3. **Finding 3 (P1) — Credential Provider Single-Load & Secret-Free Output Proof**:
   - Added `test_credential_provider_loads_dotenv_token_exactly_once_and_emits_secret_free_output` asserting `load_tiingo_api_key_from_dotenv` is called **exactly once** per apply invocation and that the secret token value is nowhere in result dict, JSON, ledger JSON, or stdout/stderr.
4. **Finding 4 (P2) — Lock Path Protection & Handoff Alignment**:
   - Wrapped `lock_path.parent.mkdir(...)` and file creation in `_acquire_lock` in try/except returning `None` on OS/Permission errors (fail closed as `ledger_lock_unavailable`).
   - Corrected test counts: 145 targeted unit tests across 4 files (43 adapter, 19 executor, 40 planner, 43 dependency direction).
   - Recorded pre-correction PID 23256 as superseded.

## Round-5 Orchestrator Review (`db2b646`) — REQUEST CHANGES

Corrected in `0acc5df` and `c0d1176`.

1. **Finding 1 (P1) — `EXECUTION_AUTHORIZED_NETWORK_READ_ONLY` fell out of every
   plan aggregate, producing a false green.** The plan rollup buckets lanes into
   `offline_runnable_lanes`, `operator_gated_lanes`, and `noop_lanes` only; a
   lane in the new class joined none of them. Reproduced by execution: with the
   soak lane absent and every other lane nominal/waiting, `plan_class` read
   `all_nominal_or_waiting`, `operator_summary` read "no next action is
   pending", bucket coverage was 5 of 6, and `algotrader autonomy-next-plan`
   exited `0` — while that lane carried a runnable standing-authority refresh
   command. Before V5.51 the same scenario reported
   `operator_authority_required`, so this was a regression, and the fourth
   instance of the V5.37a/V5.38a/V5.42a defect class (a derived aggregate left
   behind when a new class is added).
   - Fix: added `PLAN_AUTHORIZED_NETWORK_ACTION_AVAILABLE` (ranked below offline,
     which needs no network, and above operator-gated, which is genuinely
     blocked), the `authorized_network_lanes` bucket, and
     `next_authorized_network_action{,_lane}` mirroring the offline pair.
   - Guard against recurrence: `test_every_lane_lands_in_exactly_one_plan_bucket`
     asserts the four bucket lists partition the lanes, so the next class added
     without a bucket fails rather than disappearing.
2. **Finding 2 (P1) — the full suite did not pass at `db2b646`.**
   `test_spy_eod_refresh_schedule_is_isolated_tiingo_only` failed: commit B
   repointed the scheduled-task template to
   `run_spy_read_only_network_executor.ps1` exactly as the frozen contract
   specifies ("Windows Scheduled Task Update"), but the test still asserted the
   old `refresh_spy_adjusted_data.ps1` command line. The targeted 4-file run
   recorded below did not include this file. The stale assertions were the only
   place any test pinned the unattended refresh to a read-only Tiingo-only shape
   (`-Provider tiingo`, `-Mode live_market_data_fetch`,
   `-LiveMarketDataFetchAuthorized`, `-RevisionLookbackDays 10`,
   `-StartDate auto`, `-SoakRequiredSessions 5`, four canonical paths), and
   nothing re-asserted them after the move, so they were re-anchored to the
   seam's `ETFAdjustedDataRefreshConfig` rather than deleted with the test.
   New coverage also pins the wrapper's single `UtcNow` capture — a second
   timestamp resolution inside Python could straddle the session cutoff and
   target a different NYSE session than the wrapper started for.
3. **Finding 3 (P2) — CLI blamed the command line for internal failures.**
   `main()` mapped any escaping `ValidationError` to `parser_invalid_argument`,
   and its `as_of_invalid` arm was unreachable (that refusal is returned in the
   result dict, never raised). Now reports `unexpected_validation_error`.

4. **Finding 4 (P3, raised as informational, then adjudicated by the operator as
   required) — wrapper invocation form did not match the frozen contract.** The
   wrapper called `python -m ...` bare where "Windows Scheduled Task Update"
   freezes the form as PowerShell's call operator against the literal captured
   string. The invariant that clause protects — one timestamp capture, never
   re-resolved — was already satisfied, so this was form rather than behavior;
   the operator ruled the frozen form binding. Now
   `& python -m algotrader.execution.autonomy_read_only_network_executor
   --as-of $asOfUtc --apply --format json`, asserted verbatim by
   `test_spy_eod_refresh_wrapper_invokes_the_seam_with_one_utc_capture`.
   Verified out-of-band that the script parses with zero errors and that the
   call operator delivers the captured timestamp as exactly one argv entry.

## Authority And Safety Boundaries

- Paper-only, read-only market-data fetch path.
- No live trading, live orders, live capital, or credential values exposed.
- All default pytest suites remain network-free and credential-free.
- Fail-closed interlock evaluation at every execution step.

## Checkout And Ownership

- Working tree: `C:\Users\danie\Desktop\algo_trader\.claude\worktrees\v551-readonly-market-data-contract`.
- Branch: `claude/v5.51-readonly-spy-market-data-contract`.
- Implementation writer through `db2b646`: Antigravity AI collaborator.
- Round-5 correction (`0acc5df`, `c0d1176`): Claude Code, acting as orchestrator
  and implementing agent under the frozen charter. Because Claude Code authored
  these commits, it cannot also accept them.

## Verification Evidence

### At `db2b646` (pre-round-5-correction)

- Targeted unit tests: 145/145 passed across 4 files (`test_spy_adjusted_data_refresh.py` [43], `test_autonomy_read_only_network_executor.py` [19], `test_autonomy_next_plan.py` [40], `test_dependency_direction.py` [43]). **This targeted set was not sufficient — it omitted the file that actually failed.**
- Full default pytest: **NOT PASS** — `1 failed, 10062 passed, 5 skipped in 1790.46s (0:29:50)`, exit 1. Failure: `tests/unit/test_spy_eod_market_data_refresh_schedule.py::test_spy_eod_refresh_schedule_is_isolated_tiingo_only` (round-5 finding 2).

### At `26c4fb3` (round-5 correction; evidence recorded in child commit `824f265`, the review target)

- Full default pytest, credential-free from a clean tree: **PASS** — `10071 passed, 5 skipped in 1649.55s (0:27:29)`, exit 0, 10076 collected. (Same result at `c0d1176`, before the finding-4 call-operator fix: `10071 passed, 5 skipped in 1614.41s (0:26:54)`, exit 0.)
- Offline verification script `verify_offline.ps1`: **PASS** (108/108 offline safety guard tests).
- Preflight credential/profile check: clean — `APP_PROFILE_is_paper: False`, `ALPACA_API_KEY_loaded: False`, `ALPACA_API_SECRET_KEY_loaded: False`, `ALPACA_SECRET_KEY_loaded: False`, `APCA_API_KEY_ID_loaded: False`, `APCA_API_SECRET_KEY_loaded: False`, `RUN_ALPACA_PAPER_INTEGRATION_TESTS_enabled: False`. No `.env` in the working tree; no `TIINGO_API_KEY` in the environment.
- Targeted: 151 passed across the original 4 files (was 145); 201 passed across all autonomy-keyed tests; 25 passed across the two schedule/seam files.
- Correction commits: `a0ce62d`, `9471e87` (round 4); `0acc5df`, `c0d1176`, `26c4fb3` (round 5).
- Wrapper invocation verified out-of-band: PowerShell parse errors 0; call operator yields argv `["--as-of", "<captured UTC>", "--apply", "--format", "json"]`.
- `git diff --check`: clean (zero whitespace errors).
- `git status --short`: clean.
- `git diff --name-only HEAD~4 -- src`: exact expected modified/created source files.
- `git ls-files --others --exclude-standard src tests`: clean (no untracked junk).

## Round-6 Independent Acceptance Review — REQUEST-CHANGES (2026-07-27)

Independent reviewer: Codex/GPT. **Do not promote. Do not fast-forward `main`.**
All three findings independently reproduced by claude-code before acceptance.

1. **F1 (contract violation) — the seam imports a module the frozen contract
   forbids, and the test was widened to admit it.** The contract permits only
   `etf_sma_adjusted_spy_data_refresh` (adapter) and `live_capital_interlock`
   (safety closure) among internal `algotrader.execution` imports, but the seam
   also imports `algotrader.execution.exchange_session`, and
   `test_dependency_direction.py`'s `allowed_internal_modules` lists it.
   *Confirmed:* contract rule at ~line 1264 vs the test allowlist. Introduced in
   `af1b377`; the round-5 review checked for defects but never diffed the seam's
   imports against the contract's permitted list. A test broadened to accommodate
   a deviation is worse than the deviation — it converts a violation into a
   passing suite.
2. **F2 (ledger) — `session_id` / `attempt_number` / `run_id` are not held in the
   frozen relationship, so a duplicate reservation can be written.** A ledger
   holding one pending record numbered `2` validates as count `1`; the next
   generated `run_id` collides with the existing `network-<session>-2` and the
   duplicate reservation is appended *before* the network is reached. Should be
   `ledger_corrupt`, zero writes.
   *Reproduced exactly:* `prior_count=1`, `next run_id=network-2026-07-24-2`,
   `COLLIDES=True`.
3. **F3 (guard strength) — the fourth-recurrence fix is sampled, not total.**
   `test_every_lane_lands_in_exactly_one_plan_bucket` iterates three report
   fixtures rather than asserting an invariant over the execution-class table. A
   future class used only in an unrepresented lane state can still fall out of
   every bucket, so it does not reliably prevent a fifth recurrence.
   *Confirmed by inspection.* This is a correct critique of the round-5 fix: it
   is stronger than the point fixes that preceded it, but weaker than the total
   invariant it was described as.

Confirmed strengths (reviewer, independently verified): `ledger_corrupt` and
`ledger_lock_unavailable` write zero events; the seam is broker/mutation-disjoint
with finite bounds (1 GET per invocation, 4 reservations per session, 5s lock
timeout, 8 MiB response cap, 20,000-row cap); the stale schedule protections were
genuinely re-anchored to the seam configuration and wrapper; 156 targeted passed;
108/108 offline guards; full suite 10,076 collected, 10,071 passed, 5 skipped,
exit 0; preflight all-false, no `.env`, no network or broker operation.

## Round-6 Corrections Implemented (`efdcebc`, `c2b8c22`)

- **F2 — `efdcebc`.** `_read_and_validate_ledger` now enforces the frozen
  identity relationship: every record must carry
  `run_id == network-<session_id>-<attempt_number>`, and a session's
  reservations must number exactly 1..N. The reviewer's repro raises
  `ledger_corrupt` instead of colliding, and the apply path refuses with zero
  additional writes.
- **F3 — `efdcebc`.** Buckets derive from one total mapping,
  `PLAN_BUCKET_BY_EXECUTION_CLASS`, checked against the class vocabulary at
  import time, replacing four independent comprehensions. A class added without
  a bucket now fails at import regardless of which lane states any fixture
  builds. The sampled partition test is kept as its companion: the invariant
  proves the mapping is total, the sample proves the builder uses it.
- **F1 — `c2b8c22`, resolved by operator decision as a contract amendment.**
  The direct-import rule now names three modules. Rationale recorded in the
  contract: the two-module rule was not carrying the safety weight it appeared
  to — the stated property is proved by the closure purity check across all
  seven files, and `exchange_session` has been inside that purity-checked
  closure since the adapter began importing it in `9ba2925`, long before this
  milestone, so the seam's direct import widens the blast radius by nothing.
  Conforming instead would have moved this contract's own 20:10 ET
  expected-session semantics into an adapter shared by four unrelated modules.
  The amendment is narrow and exhaustive (three named modules, not a category)
  and, per operator instruction, carries the same independent-review
  requirement as any implementation change.
  `test_dependency_direction.py` now mirrors the contract as a frozen
  three-entry set with a size guard and a comment recording that it may never
  again be widened to match an implementation — that drift, not the extra
  import, was the actual defect F1 identified.

### Verification status — INCOMPLETE, do not read as verified

- Targeted: **154 passed** across the four V5.51 suites, at `c2b8c22`.
- Full default pytest at `c2b8c22`: **NOT COMPLETED.** The run was interrupted
  at ~29% with zero failures recorded (it had cleared
  `test_dependency_direction.py`, the file F1 changed). No complete full-suite
  run exists for the round-6 tree.
- Full default pytest at `efdcebc` (F2/F3 only, before the F1 commit):
  `1 failed, 10072 passed, 5 skipped`, 2366s. The failure was
  `test_v536_windows_host_canary.py::test_concurrent_execution_allows_one_real_dispatch_and_immutable_duplicates`.
  Neither changed module is referenced by that test or its subject module, and
  it passes 3/3 in isolation; that run took 2366s against 1614s/1650s for
  earlier runs because other commands were executing concurrently. The evidence
  points to a load-sensitive flake in an 8-worker thread-pool test rather than a
  regression, but **this is unconfirmed** — a clean full run is what would
  settle it.
- **Required before re-review:** one clean, credential-free full
  `python -m pytest` from `c2b8c22` with nothing else running on the host, plus
  `verify_offline.ps1`. Targeted-green is not verification — this milestone has
  already been bitten once by exactly that substitution (round-5 finding 2).

## Next Action

run one clean full `python -m pytest` plus `verify_offline.ps1` from `c2b8c22`, then return to Codex/GPT for round-6 re-review. **V5.51 is NOT accepted and must not be promoted.**

Re-review scope: the three corrections above **and the contract amendment
itself**, which the operator directed be reviewed as a change in its own right
rather than accepted implicitly along with the code.

Claude Code authored the round-5 and round-6 corrections and Antigravity
implemented through `db2b646`, so neither may accept the result.
