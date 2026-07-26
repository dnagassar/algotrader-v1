# Active Implementation Checkpoint

## Classification

- Milestone: `V5.51 — read-only SPY market-data network refresh
  reachability contract`.
- Frozen contract:
  `docs/design/v5_51_read_only_spy_market_data_network_refresh_reachability_contract.md`.
- Review status: **round-3 REQUEST CHANGES, corrections applied, pending
  independent round-4 review. No implementation is authorized.** Round-1
  findings (1 P0, 4 P1, 3 P2) and round-2 findings (1 P0, 3 P1, 3 P2) remain
  recorded in the contract's "Round-1 Independent Review" and "Round-2
  Independent Review" sections. Round-3 findings (1 P0, 4 P1) and their
  corrections are recorded in the contract's new "Round-3 Independent
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

## Round-3 Findings Corrected This Round

| # | Severity | Finding | Correction |
| --- | --- | --- | --- |
| 1 | P0 | The planner's existing `ActionClass.__post_init__` validation (`autonomy_next_plan.py`) raises whenever a non-offline-runnable class carries a non-empty `command`. `EXECUTION_AUTHORIZED_NETWORK_READ_ONLY` was specified with `offline_runnable=False` *and* a required, non-empty `command` — that combination cannot construct against the existing rule. | "Planner Classification" now explicitly authorizes commit B to add the new class to `_EXECUTION_CLASSES` (not `_OFFLINE_RUNNABLE_CLASSES`) and to narrowly carve out the command-carrying rule for this one class only, while every other non-offline-runnable class (`EXECUTION_OPERATOR_GATED`, `EXECUTION_NOOP`) keeps rejecting a non-empty `command` unchanged; docstring update and a dedicated narrow-carve-out test are now required (Implementation Acceptance Criteria 5). |
| 2 | P1 | The session-already-qualified short-circuit branched on the soak report's `latest_session_qualified` boolean, which reflects only the report's most-recently-*attempted* session, not the `--as-of`-resolved `session_id` this invocation cares about — a stale or unrelated session being qualified could wrongly fire or wrongly fail to fire the short-circuit. | "Retry And Idempotency Behavior" and "Session Attempt Budget" now require an exact membership test: `session_id` must appear verbatim in the soak report's `qualifying_session_dates` list. `latest_session_qualified` is never read by the seam. |
| 3 | P1 | `ledger_lock_unavailable` and `ledger_corrupt` were allowed to write a sanitized `"refused"` ledger event like every other refusal, but neither an unacquired lock nor a proven-corrupt file offers a safe way to append. | "Concurrency And Ledger Locking," "Session Attempt Budget," "Sanitized Receipt And Provenance," and "Fail-Closed Refusal Conditions" now specify **zero** ledger write for these two categories (sanitized CLI/`--format json` output only); only `live_capital_interlock_blocked`, `token_not_available`, and `session_attempt_budget_exhausted` (reached after a successfully acquired lock and validated ledger) write the one locked, non-reservation `"refused"` event. |
| 4 | P1 | "Read-Only Market-Data Is Not Live Trading" claimed a test that "walks the import graph and asserts every module path reaching [`AlpacaPaperConfig`/`require_paper_profile`] passes through `live_capital_interlock`" — a whole-repository transitive-reachability prover that does not exist; `test_dependency_direction.py`'s `DependencyRule`/`_dependency_violations` is a flat, per-file, single-hop scan, never a multi-file graph walk. | Replaced with implementable AST rules over an explicit, hand-curated, seven-file closure (seam module, adapter, adapter's soak-report dependency, exchange-session calendar, errors module, `live_capital_interlock`, `config`), each file's current import set read and recorded in the contract; asserts direct-import scope, no direct config/secret identifiers in the seam, no config/broker import in the adapter, `live_capital_interlock` as sole permitted importer of the two config names, and a flat SDK/mutation-import scan across the whole closure — all provable with the existing `DependencyRule` mechanism. |
| 5 | P1 | "Sanitized Receipt And Provenance" specified "one JSONL record appended per invocation" with an all-fields-always field list — contradicted by the dry-run/short-circuit zero-write rule, the reservation/completion split, and the fixed refusal-ordering (an attempt-budget-exhausted refusal is written *before* the interlock step ever runs, so `interlock_verdict` cannot always be populated). | Cardinality frozen exactly: zero records for dry-run/no-op/pre-lock failures; one locked refusal event for the three post-lock refusal categories; two fsynced events (reservation, then completion) for an actual attempt, with a crash between them leaving only the reservation. Each of the three event shapes gets its own frozen, nullable schema — notably, the reservation's `network_access_attempted` is `false` (truthful as of write time, before the HTTP call) and only the completion's is `true`, correcting a prior claim that was temporally backwards. |

## Authority And Safety Boundaries

- This milestone performed **zero** network access, credential load,
  broker access, or paper/live mutation. It is doc-only, same as prior
  rounds.
- The round-3-corrected contract closes five real specification defects
  (an unconstructible validation state, a short-circuit reading the wrong
  field, unsafe writes on untrustworthy ledger/lock state, a claimed test
  mechanism that does not exist in this codebase, and a ledger schema
  contradicted by its own timing) rather than merely adding precision to
  already-workable text. No live-broker or live-capital access is
  authorized. Live capital remains operator-gated until burn-in completes.

## Checkout And Ownership

- Implementation worktree (this session):
  `C:\Users\danie\Desktop\algo_trader\.claude\worktrees\v551-readonly-market-data-contract`,
  branch `claude/v5.51-readonly-spy-market-data-contract`.
- Verified checkout HEAD for this round's remediation: `01cb79a`
  (post-push round-2 re-verification over the round-2-corrected contract at
  `703615f`, itself based on `9cfc183`/`6797e95`/`b79c721`), clean
  working tree, upstream `origin/claude/v5.51-readonly-spy-market-data-contract`
  up to date at takeover (confirmed via `git status --porcelain=v2 --branch`
  → `branch.ab +0 -0` before any edit this round).
- Sole implementation writer for this round's contract-remediation-only
  milestone; Codex remains orchestrator/reviewer per operator instruction.
- Preflight (presence-only, no values), this pass: `APP_PROFILE` not set;
  no Alpaca/APCA credential alias set (`ALPACA_API_KEY`, `ALPACA_API_KEY_ID`,
  `APCA_API_KEY_ID`, `ALPACA_SECRET_KEY`, `ALPACA_API_SECRET_KEY`,
  `APCA_API_SECRET_KEY`); no `TIINGO_API_KEY` set.

## Files Changed This Round

- `docs/design/v5_51_read_only_spy_market_data_network_refresh_reachability_contract.md`
  (substantially corrected: new "Round-3 Independent Review: Findings And
  Corrections" section, positioned after "Round-2 Independent Review" and
  before "Non-Negotiable Safety Contract" — chronologically correct
  ordering; "Planner Classification" rewritten to authorize the narrow
  `ActionClass` command-carve-out with an updated Implementation Acceptance
  Criteria list of five; "Retry And Idempotency Behavior" and "Session
  Attempt Budget" corrected to the exact `qualifying_session_dates`
  membership check; "Concurrency And Ledger Locking," "Session Attempt
  Budget," "Fail-Closed Refusal Conditions," and "Mandatory Live-Capital
  Interlock Preflight" corrected for the zero/one-ledger-write refusal
  split; "Read-Only Market-Data Is Not Live Trading" rewritten around the
  seven-file hand-curated closure and implementable AST rules; "Sanitized
  Receipt And Provenance" and "Non-Negotiable Safety Contract" rewritten
  around the corrected zero/one/two-record cardinality and per-event-type
  nullable schema, including the reservation-vs-completion
  `network_access_attempted` timing fix; "Execution Architecture"'s
  dry-run bullet and "Implementation Milestone Shape"'s commit B
  description updated for consistency; "Status" and "Next Action" updated
  to round-3/round-4).
- `docs/agent_context/active_implementation.md` (this file, overwritten in
  place; no historical handoff copy created).

No `src/` or `tests/` file was modified. `src/algotrader/execution/autonomy_next_plan.py`,
`etf_sma_market_data_soak.py`, `etf_sma_adjusted_spy_data_refresh.py`,
`exchange_session.py`, `errors.py`, `live_capital_interlock.py`, `config.py`,
and `tests/unit/test_dependency_direction.py` were **read** (not edited) to
ground every round-3 correction in the actual, current source: confirmed
`ActionClass.__post_init__`'s exact command/gate/operator-input validation
branches (`autonomy_next_plan.py:153-196`); confirmed
`build_adjusted_market_data_soak_report`'s `latest_session_qualified` is
derived from `latest_attempted`, not from the invocation's own resolved
`session_id` (`etf_sma_market_data_soak.py:171-211`); confirmed
`test_dependency_direction.py`'s `DependencyRule`/`_dependency_violations`
(and every other test in the file) implements only a flat, per-file,
single-hop import scan, with no multi-file transitive-graph-reachability
helper anywhere in the file; confirmed the exact import sets of the
adapter, its soak-report dependency, the exchange-session calendar, the
errors module, `live_capital_interlock`, and `config` to ground the
seven-file hand-curated closure in "Read-Only Market-Data Is Not Live
Trading".

## Verification Evidence

This is a doc-only change, so no test suite exercises new behavior.

- `git status --short` (Claude's pass, before this file's own edit): exactly
  ` M docs/design/v5_51_read_only_spy_market_data_network_refresh_reachability_contract.md`
  unstaged/modified, matching "Files Changed This Round" once this file is
  also written.
- `git diff --check` → clean (no whitespace errors).
- `git diff --name-only HEAD -- src` → empty.
- `git ls-files --others --exclude-standard src tests` → empty (no
  untracked `src`/`tests` files).
- Presence-only preflight (no values printed): `APP_PROFILE`,
  `ALPACA_API_KEY`, `ALPACA_API_KEY_ID`, `APCA_API_KEY_ID`,
  `ALPACA_SECRET_KEY`, `ALPACA_API_SECRET_KEY`, `APCA_API_SECRET_KEY`,
  `TIINGO_API_KEY` all confirmed absent.
- No network or broker command was run.
  `.\scripts\verify_offline.ps1` and the default pytest suite were **not
  run**: this remains a documentation-only diff with no `src`/`tests`
  impact (confirmed by the empty `git diff --name-only HEAD -- src` and
  untracked-file checks above), so per `AGENTS.md`'s "Preflight and
  Verification" section there is no changed `src`/`tests` behavior for them
  to exercise. Recorded truthfully as "not run" rather than claimed as
  passing evidence, consistent with prior rounds' practice.
- Orchestrator post-writer verification found and closed two documentation
  ambiguities before commit: the ledger schema now freezes the exact
  `record_type`, `schema_version`, and fixed common values, and states how a
  locked non-reservation refusal derives `run_id`/`attempt_number` without
  consuming an attempt slot; this handoff now names the actual takeover HEAD
  `01cb79a`. No source, test, policy, authority, network, credential, or
  broker behavior changed.

## Unresolved Risks

- The contract is now precise on five further specification defects a
  round-3 reviewer identified, but it has not yet been independently
  re-reviewed. A round-4 reviewer may still find a gap — for example, in
  the exact interaction between the narrow `ActionClass` command carve-out
  and any other code path that iterates `_EXECUTION_CLASSES` expecting
  every member to be either offline-runnable-with-command or
  gated-without-command (the contract's carve-out is scoped to the
  dataclass validation only; whether any other planner/report code assumes
  that same invariant has not been independently audited this round).
- `docs/OPERATOR_RUNBOOK.md`'s V5.38 section (`auto_offline` example
  `etf-sma-offline-daily-cycle-rerun-m446`) still describes a pre-V5.48
  allowlist shape that no longer matches
  `AUTONOMY_EXECUTOR_ALLOWLIST`'s current two-readiness-token contents.
  Not touched by this milestone (out of scope), unchanged from prior
  rounds' note.
- Commit A (adapter caps) and commit B (executor/planner/scheduled-task,
  now including the narrow `ActionClass` carve-out, the corrected
  short-circuit membership check, the corrected ledger-write cardinality,
  and the hand-curated-closure import-purity tests) are specified
  precisely but neither has been written; the exact Python implementation
  of every rule above is a contract-level specification, not yet code, and
  could still surface an unanticipated edge case once written against the
  real adapter/planner internals.

## Next Action

Independent **round-4** review of the corrected V5.51 contract
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
  (`703615f`), reviewed round-3 REQUEST CHANGES and corrected (this
  commit). Still contract-only; pending independent round-4 review. See
  "Classification" and "Round-3 Findings Corrected This Round" above.
