# V5.51 Read-Only SPY Market-Data Network Refresh Reachability Contract

## Status

- Status: **round-3 REQUEST CHANGES corrected in place; pending independent
  round-4 review. No implementation is authorized.** Round-1 findings and
  their corrections remain recorded in "Round-1 Independent Review: Findings
  And Corrections" below; round-2 findings and their corrections are recorded
  in "Round-2 Independent Review: Findings And Corrections" below; round-3
  findings and their corrections are recorded in "Round-3 Independent Review:
  Findings And Corrections" below.
- Still **no `src/` or `tests/` file has been changed by this contract
  document.** What changed this round is, again, the contract's own
  precision: every place round-3 found an unsatisfiable validation rule, a
  short-circuit condition that read the wrong field, an unsafe ledger write
  on an untrustworthy ledger/lock state, a claimed test mechanism that does
  not exist in this codebase, or a ledger schema claim contradicted by the
  contract's own timing, is now frozen to one exact, checkable rule.
- Base commit for this correction: `703615f` (the round-2-corrected V5.51
  contract). Prior base commits: `9cfc183` (round-1-corrected contract),
  `6797e95` (originally frozen contract), `b79c721` (V5.50 lane eligibility
  analysis recorded).
- Operator authorization: the operator selected **option 2** from
  `docs/design/v5_50_offline_autonomy_lane_eligibility_analysis.md` —
  authorize the read-only market-data intake path. `AGENTS.md` now states
  this standing authority explicitly and canonically (see "Round-1
  Independent Review" finding P2-1 below): every collaborator, regardless of
  agent/model/tool, has standing authority within an explicitly scoped task
  to load and use an approved read-only market-data provider credential
  through the minimum trusted provider boundary and perform exact-destination
  read-only market-data GETs through repository adapters, bounded by finite
  caps, deterministic preflight, sanitized provenance/receipt/audit, and
  fail-closed exact endpoint/method validation. This does not authorize
  broker/account mutation, live-broker access, trading, orders, positions, or
  live capital.
- **Implementation authorization on acceptance.** Once independent round-2
  review accepts this contract (not before), it authorizes exactly **one**
  implementation milestone/PR, containing exactly two ordered commits
  reviewed together (see "Implementation Milestone Shape" below). No second
  contract is required to land those two commits. `spy_offline_daily_cycle`
  consumption of the refreshed data remains a separate, later milestone
  requiring its own frozen contract (unchanged from the original freeze).
- Not live-trading, not broker-mutating, not paper-order authority. This
  document still authorizes no network call, no credential load, and no code
  change by itself; authorization to write code is granted only by an
  accepted contract plus the two-commit milestone it opens.
  `docs/design/v5_50_offline_autonomy_lane_eligibility_analysis.md` was
  corrected alongside the original freeze (see "Correction To V5.50" below);
  its input-self-containment finding is preserved unchanged.

## Problem Statement

The V5.37/V5.38/V5.39 supervisor/planner/executor stack today classifies
`spy_market_data_soak`'s absent-state action,
`run_authorized_read_only_market_data_refresh_to_seed_soak`, as
`EXECUTION_OPERATOR_GATED` with gate `network_market_data_fetch`
(`autonomy_next_plan.py:347-351`). **This round corrects that classification**
(see "Planner Classification" below) — round-1 review did not flag the old
"unchanged" framing as wrong on its own, but it is superseded by the
operator's adjudication that the classification must become truthful under
the new standing authority: the lane is not actually blocked on the operator
today, it is blocked only on a not-yet-built execution seam. Leaving it
`EXECUTION_OPERATOR_GATED` after that seam exists would itself be a
truthfulness defect of the exact class V5.37a/V5.38a/V5.42a repaired, just
inverted (falsely claiming continued operator blockage instead of falsely
claiming auto-offline reach).

What was missing, and what this contract still exists to freeze, is not
authority — the operator has granted it for this exact narrow path — but a
**safety-bounded, auditable execution seam** for exercising it. Today the
only ways to run the read-only Tiingo refresh are: (a) an operator typing the
exact `scripts/refresh_spy_adjusted_data.ps1` invocation by hand, or (b) the
pre-existing, reviewer-inspectable Windows Task Scheduler template
(`docs/design/spy_eod_market_data_refresh_scheduled_task.xml`) at the host
level, invoking that same script directly, outside any repository-owned
execution ledger. Neither is wrong as a manual/diagnostic path, but neither
produces the same kind of frozen, allowlisted, preflight-gated,
ledger-recording seam that `autonomy_offline_executor.py` gives the crypto
readiness replay. This contract freezes that seam for the read-only network
case, **structurally disjoint** from the offline executor, so the
market-data track can be advanced without touching or weakening the
network-free offline invariant V5.39/V5.45/V5.48 built.

## Round-1 Independent Review: Findings And Corrections

Independent review of `6797e95` returned **REQUEST CHANGES**. Every finding
below was treated as required by operator adjudication; each is corrected in
this document's body, cross-referenced here.

| # | Severity | Finding | Correction (see section) |
| --- | --- | --- | --- |
| 1 | P0 | The original "Alpaca/broker credential variables are not a refusal condition" language read as excluding the live-capital interlock entirely, contradicting V5.41's standing `evaluate_live_capital_interlock` boundary. | "Mandatory Live-Capital Interlock Preflight" — the interlock call is now a required, explicit refusal condition in both dry-run (report-only) and apply mode. The corrected text distinguishes "the seam does not read Alpaca *credential secret* values" (still true) from "the seam is exempt from the live-capital interlock" (was never true and is now explicitly false). |
| 2 | P1 | The credential preflight bullet described checking `TIINGO_API_KEY` presence "by name only" against the process environment, while the bound command's `--dotenv-path .env` and the adapter's `load_tiingo_api_key_from_dotenv` read a canonical dotenv file, not `os.environ`. Presence-checking one source and reading from another is a contradiction an implementer could resolve either way. | "Freeze One Credential Source" — presence is now determined by resolving and probing the canonical repo-root `.env` via `load_tiingo_api_key_from_dotenv`, the same source the adapter reads from at fetch time. Process-environment `TIINGO_API_KEY` values are explicitly ignored by this command. |
| 3 | P1 | "at most 1 authorized attempt per UTC calendar day" conflicts with the same-session retry the soak layer already treats as legitimate and with the Windows Task Scheduler template's own three-retry/15-minute `RestartOnFailure` policy — a same-session scheduler retry would be structurally unable to succeed under a 1-per-day cap. | "Finite Caps" and "Session Attempt Budget" — the cap is now **four authorized attempts per resolved NYSE session** (one initial plus three retries), which is the exact shape of the existing scheduled task's `RestartOnFailure` (`Interval=PT15M`, `Count=3`), enforced by the seam's own ledger rather than by calendar day. |
| 4 | P1 | "in-process, or via `scripts/refresh_spy_adjusted_data.ps1`, exact mechanism is an implementation choice" left the execution architecture — and therefore every safety proof about child-process/child-environment isolation — unfrozen. | "Execution Architecture" — exactly one architecture is now frozen: an in-process, directly invoked module, `python -m algotrader.execution.autonomy_read_only_network_executor --as-of <ISO8601_UTC> [--apply] --format json`. No child process, no child-environment claim. Static import-closure purity (no broker SDK/client/order/mutation import) replaces the old child-environment defence-in-depth framing. |
| 5 | P1 | The "expected session" derivation called `NyseExchangeSessionCalendar.latest_completed_session_on_or_before(as_of)` with no time-of-day awareness, so an `--as-of` earlier in a session's own calendar day could resolve to that same-day session as "expected" even though Tiingo has not published EOD data yet. | "Deterministic Expected-Session Semantics" — a provider-publication cutoff of 20:10 America/New_York (already the scheduled task's own registration boundary, `docs/OPERATOR_RUNBOOK.md`'s "Authoritative SPY EOD Market-Data Refresh" section) is now the deterministic threshold: at or after 20:10 ET on a session date, that session is expected; before it, the prior completed session is expected. |
| 6 | P2 | Tiingo is referenced as the sole approved provider throughout this contract and the adapter, but `AGENTS.md` did not name any third-party market-data provider as canonical authority for that reliance. | `AGENTS.md` update (see "Status" above and the committed diff) adds standing, provider-generic authority for an "approved read-only market-data provider credential" and adds `TIINGO_API_KEY` / approved-provider-credential presence to the credential-free default-test preflight. |
| 7 | P2 | The response-byte and provider-row caps were phrased as examples ("e.g. 8 MiB", "e.g. 20,000 rows"), leaving the exact numeric bound to the implementer rather than to review. | "Finite Caps" — frozen at exactly 8,388,608 bytes (8 MiB) and 20,000 rows; the "e.g." language is removed. |
| 8 | P2 | "Contract-only milestone... a future implementation contract must add the two gap rows... this contract does not authorize that adapter change" implied a *second* contract-review cycle was required before any adapter change could land, but did not say whether that second cycle was this same document's implementation milestone or an entirely separate frozen contract, leaving the acceptance path ambiguous. | "Implementation Milestone Shape" — on acceptance, this single contract authorizes exactly one implementation milestone/PR with two ordered commits (A: adapter caps + safety preflight; B: executor/planner/scheduled-task seam), reviewed together. No second contract is required. |

The valid V5.50 input-self-containment finding, and the correction recording
the operator's selected option 2, are both preserved unchanged from the
original freeze (see "Correction To V5.50" below).

## Round-2 Independent Review: Findings And Corrections

Independent review of `9cfc183` returned **REQUEST CHANGES**. Every finding
below was treated as required by operator adjudication; each is corrected in
this document's body, cross-referenced here.

| # | Severity | Finding | Correction (see section) |
| --- | --- | --- | --- |
| 1 | P0 | The import-purity test forbade `AlpacaPaperConfig` and `require_paper_profile` outright, but the *mandatory* `evaluate_live_capital_interlock` call transitively imports and calls both (`live_capital_interlock.py` calls `AlpacaPaperConfig.from_env` and `require_paper_profile`). A test banning them would fail against the seam's own required safety dependency. Separately, the contract's claim that the interlock "never reads a credential secret" was false: `AlpacaPaperConfig.from_env` reads `ALPACA_API_KEY`/`ALPACA_SECRET_KEY`-family values into `alpaca_api_key`/`alpaca_secret_key` fields (`repr=False`, so never printed, but genuinely populated and held). | "Read-Only Market-Data Is Not Live Trading" and "Mandatory Live-Capital Interlock Preflight" — the import-purity test now explicitly allows the transitive safety closure (`live_capital_interlock`, `AlpacaPaperConfig`, `require_paper_profile`, and the `algotrader.config` validation dependencies reached only through that module) instead of banning it, and the contract now states truthfully that the interlock loads repr-hidden Alpaca paper credential strings into memory but never logs, serializes, discloses, forwards, or uses them for Tiingo or broker access, and that the seam itself never directly touches a secret field. |
| 2 | P1 | "Freeze One Credential Source" specified the presence check calling `load_tiingo_api_key_from_dotenv` on the apply path, and separately specified the adapter's own `token_lookup` calling the same function again at fetch time — two dotenv reads per successful apply invocation, not the "exactly once" the section's own heading implied. | "Freeze One Credential Source" — rewritten around a single frozen credential-provider object that calls `load_tiingo_api_key_from_dotenv` exactly once per apply invocation, caches the result privately, and serves both the presence check and the adapter's `token_lookup` from that one cached value. |
| 3 | P1 | "Windows Scheduled Task Update" specified the `<Actions><Exec>` command as `python -m ... --as-of <UTC timestamp resolved at trigger time> --apply --format json` — `<UTC timestamp resolved at trigger time>` is prose, not an executable argument, and the contract elsewhere bans any wrapper/fallback mechanism that could resolve it. | "Windows Scheduled Task Update" — freezes a new, reviewed wrapper script, `scripts/run_spy_read_only_network_executor.ps1`, that captures `[DateTimeOffset]::UtcNow` exactly once and invokes the Python module with that literal captured value; the XML template's `<Exec>` now invokes that exact wrapper, with no placeholder text anywhere in an executable field. "In-process" is clarified to describe the Python module's own call into the adapter (no adapter/network child process), which is distinct from Task Scheduler launching a PowerShell-to-Python host process. |
| 4 | P1 | The four-attempt session ledger budget was read-then-append with no concurrency control specified. Two invocations (a manual run racing a scheduler restart, or two overlapping scheduler retries) could both read the same prior count and both proceed, exceeding the four-attempt budget or corrupting the append. | "Concurrency And Ledger Locking" (new section) — freezes an exclusive OS advisory lock (`runs/autonomy_network_executor/ledger.lock`, a repository stdlib wrapper over `msvcrt.locking` on Windows / `fcntl.flock` on POSIX, 5-second fixed timeout, refusal `ledger_lock_unavailable` on timeout) held from ledger validation through provider load, reservation write, the HTTP call, and completion write, released in a `finally` block. Budget counting changes from "records with `network_access_attempted=true`" to "unique reservation ids (pending or completed) for the session," so a crash between reservation and completion still fail-closed consumes budget. |
| 5 | P2 | It was unclear whether a dry-run invocation writes a ledger record at all — "Non-Negotiable Safety Contract" and "Execution Architecture" both said dry-run performs no artifact write "beyond one dry-run ledger record," implying a write the "fully side-effect-free" framing elsewhere contradicted. | "Retry And Idempotency Behavior" and "Concurrency And Ledger Locking" — dry-run is now specified as fully side-effect-free: **zero** ledger writes, zero lock acquisition, zero credential/HTTP access of any kind. Every "beyond one dry-run ledger record" phrase is removed. |
| 6 | P2 | It was unspecified whether a failing or unset live-capital interlock verdict should hard-refuse a dry-run invocation (as it does for apply) or merely be reported. | "Mandatory Live-Capital Interlock Preflight" and "Exit Codes" — dry-run always evaluates the interlock for sanitized informational readiness (`apply_eligible`) but never hard-refuses on a failing verdict; only apply mode hard-refuses (`live_capital_interlock_blocked`, exit `2`). |
| 7 | P2 | No exit-code scheme distinguished a successful apply from an already-qualified no-op, a pending dry-run, or an apply that reached the network but ended in an audited blocked outcome; "Fail-Closed Refusal Conditions" only defined exit `2` for pre-HTTP refusals and left every other path unstated. | "Exit Codes" (new section) — freezes the full scheme: `0` for an accepted apply or an already-qualified/no-action outcome (dry-run or apply); `1` for a pending valid dry-run, or an apply that made the actual HTTP attempt but ended in a fully audited blocked provider/normalization outcome; `2` for any pre-HTTP refusal (parser, root/path, `--as-of`, lock, ledger, interlock, credential, attempt-cap). |

## Round-3 Independent Review: Findings And Corrections

Independent review of `703615f` returned **REQUEST CHANGES**. Every finding
below was treated as required by operator adjudication; each is corrected in
this document's body, cross-referenced here.

| # | Severity | Finding | Correction (see section) |
| --- | --- | --- | --- |
| 1 | P0 | The planner's existing `ActionClass.__post_init__` validation (`autonomy_next_plan.py`) raises whenever a non-offline-runnable class carries a non-empty `command` (`"only offline-runnable actions may carry a command"`). `EXECUTION_AUTHORIZED_NETWORK_READ_ONLY` is specified with `offline_runnable=False` *and* a required, non-empty `command` — an `ActionClass` instance for this token would always raise against the existing rule. The contract never authorized changing that rule, so it specified a class that cannot be constructed. | "Planner Classification" — commit B is now explicitly authorized to add `EXECUTION_AUTHORIZED_NETWORK_READ_ONLY` to `_EXECUTION_CLASSES` (not to `_OFFLINE_RUNNABLE_CLASSES`) and to narrowly carve out the command-carrying rule for this one class only, while the existing rejection of a non-empty `command` on every other non-offline-runnable class (`EXECUTION_OPERATOR_GATED`, `EXECUTION_NOOP`) is retained unchanged; the docstring and a dedicated test are now required. |
| 2 | P1 | "Retry And Idempotency Behavior" and "Session Attempt Budget" short-circuit on the soak report's `latest_session_qualified` boolean, which the adapter (`etf_sma_market_data_soak.py:177-179`) computes from `latest_attempted` — the most recently *attempted* session in the whole report — not from the `--as-of`-resolved `session_id` this invocation cares about. A stale or unrelated most-recent session being qualified says nothing about whether *this* `session_id` qualifies; the short-circuit as written could both wrongly fire and wrongly fail to fire. | "Retry And Idempotency Behavior" and "Session Attempt Budget" — the short-circuit condition is corrected to an exact membership test: `session_id` (the `--as-of`-resolved session, not "the latest one") must appear verbatim in the soak report's `qualifying_session_dates` list. `latest_session_qualified` is never read by the seam for any purpose. |
| 3 | P1 | "Concurrency And Ledger Locking," "Session Attempt Budget," and "Sanitized Receipt And Provenance" allowed a sanitized `"refused"` ledger event to be written for *every* refusal category once the lock was in scope, including `ledger_lock_unavailable` (lock never acquired — there is no safe, exclusive way to append) and `ledger_corrupt` (the ledger file itself is proven unreadable or schema-invalid — appending to it does not repair it and risks compounding the corruption). | "Concurrency And Ledger Locking," "Session Attempt Budget," "Sanitized Receipt And Provenance," and "Fail-Closed Refusal Conditions" — `ledger_lock_unavailable` and `ledger_corrupt` now produce a sanitized CLI-output-only exit `2`, with **zero** ledger write of any kind (no reservation, no completion, no refusal event). Only `live_capital_interlock_blocked`, `token_not_available`, and `session_attempt_budget_exhausted` — refusals reached *after* a successfully acquired lock and a validated ledger — may write the one locked, non-reservation `"refused"` event. Every pre-lock failure (steps 1-6), every dry-run invocation, and the already-qualified no-op (step 5) write zero ledger records, unchanged from round-2's fully-side-effect-free framing but now stated to cover the lock/corruption paths explicitly. |
| 4 | P1 | "Read-Only Market-Data Is Not Live Trading" claimed a test that "walks the import graph and asserts every module path reaching [`AlpacaPaperConfig`/`require_paper_profile`] passes through `live_capital_interlock`" — a whole-repository transitive-reachability prover. No such mechanism exists in this codebase: `test_dependency_direction.py`'s `DependencyRule`/`_dependency_violations` is a flat, per-file, single-hop scan of one file's own `ast.parse`-derived import statements against a forbidden-prefix list, never a multi-file graph walk proving universal reachability-through-a-single-node. The claimed test could not be written against any existing helper. | "Read-Only Market-Data Is Not Live Trading" — the generic transitive-graph claim is replaced with implementable AST rules over an explicit, hand-curated file closure (verified against the current source): the seam module's own AST names only the adapter and `live_capital_interlock` as direct internal-execution-layer imports (flat scan, existing `DependencyRule` mechanism); the adapter (`etf_sma_adjusted_spy_data_refresh.py`) and its own dependency (`etf_sma_market_data_soak.py`) carry no `algotrader.config` or broker-prefixed import (flat scan, confirmed today: the adapter imports only `algotrader.errors` and `algotrader.execution.etf_sma_market_data_soak`); and `live_capital_interlock.py` is asserted, by name, to be the sole file in this six-file hand-curated closure whose own AST imports `AlpacaPaperConfig` or `require_paper_profile` from `algotrader.config` — a per-file existence/absence check across a fixed, enumerated path list, not a graph search. |
| 5 | P1 | "Sanitized Receipt And Provenance" specified "one JSONL record appended per invocation" with a single flat field list implying every field is populated on every record — contradicted by round-2's own dry-run/short-circuit zero-write rule, by the reservation/completion split, and by the fixed refusal-ordering (an attempt-budget-exhausted refusal is written *before* the interlock step ever runs, so a field list claiming `interlock_verdict` is "expected to always be populated" is false for that exact refusal). | "Sanitized Receipt And Provenance" and "Non-Negotiable Safety Contract" — the one-record-per-invocation and all-fields-always claims are removed. Cardinality is frozen exactly: **zero** records for dry-run, the already-qualified no-op, and every pre-lock failure; **one** locked refusal event (and no other record) for `live_capital_interlock_blocked`, `token_not_available`, or `session_attempt_budget_exhausted`; **two** fsynced events — reservation then completion — for an actual attempt, with a crash between them leaving only the reservation on disk. Each of the three event shapes (reservation, completion, refusal — the `ledger_status` value is the event's type) gets its own frozen, nullable field schema: a reservation's `exit_code` and `adapter_refresh_state` are `null` and its `network_access_attempted` is `false` (the HTTP call has not yet been made when this event is written); a completion's `exit_code` is `0` or `1`, `adapter_refresh_state` is a non-null string, and `network_access_attempted` is `true`; a refusal's `exit_code` is `2`, `reservation_id` is `null`, and `network_access_attempted` is `false`. A `"pending"` reservation with no matching completion means the eventual network outcome is unknown and the attempt still consumes session budget — it is not proof the network was never reached. `interlock_verdict` is `null` on a `session_attempt_budget_exhausted` refusal (interlock is not yet evaluated at that point in the fixed order) and populated on the other two refusal categories and on both reservation and completion events. The seam's own stdout/`--format json` report (distinct from the ledger) carries an analogous `interlock_verdict`-shaped field that is `null` for an already-qualified short-circuit (interlock is never reached — the short-circuit check precedes it in the fixed order) and populated, informationally, for a pending (non-short-circuited) dry-run. |

## Non-Negotiable Safety Contract

- The new execution seam is a **distinct module**,
  `src/algotrader/execution/autonomy_read_only_network_executor.py`, never a
  code path inside `autonomy_offline_executor.py`, and it is never imported
  by `autonomy_offline_executor.py`, `autonomy_self_refresh_cycle.py`, or any
  caller of `AUTONOMY_EXECUTOR_ALLOWLIST`. The offline executor's own
  docstring guarantee ("verified to import no network ... surface") must
  remain true of every module reachable from it; the new seam is reachable
  only as an independent, directly-invoked sibling command (see "Execution
  Architecture").
- `AUTONOMY_EXECUTOR_ALLOWLIST` is untouched: it still contains exactly the
  two crypto readiness tokens mapped to `CANONICAL_REPLAY_ARGV`. The new
  seam defines its **own**, separately named allowlist,
  `AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST` (one entry), that must never be
  merged into, imported by, or checked against
  `AUTONOMY_EXECUTOR_ALLOWLIST`. A dedicated test must assert the two
  allowlists' key sets are disjoint (see "Planner Classification").
- The V5.37/V5.38 supervisor's normalized-state reporting for
  `spy_market_data_soak` is unchanged. What changes, corrected this round, is
  the **planner's** classification of
  `run_authorized_read_only_market_data_refresh_to_seed_soak`: it moves from
  `EXECUTION_OPERATOR_GATED` to a new, distinct execution class,
  `EXECUTION_AUTHORIZED_NETWORK_READ_ONLY` (see "Planner Classification"). It
  keeps `offline_runnable=False` and stays outside `next_offline_action` and
  `plan_class == PLAN_OFFLINE_ACTION_AVAILABLE` — it must never cause the
  plan to report this lane as auto-offline-reachable. That invariant (no
  false-green auto-offline claim) is unchanged from the original freeze and
  remains the single most important thing this contract protects; only the
  class name changes, to stop mislabeling standing, seam-exercisable
  authority as a genuine operator blocker.
- The seam reuses the **existing** Tiingo adjusted-bars adapter
  (`src/algotrader/execution/etf_sma_adjusted_spy_data_refresh.py`), calling
  its existing public `run_spy_adjusted_data_refresh` function and
  `ETFAdjustedDataRefreshConfig` dataclass **in-process**, unchanged in their
  current fetch/normalize/canonicalize logic beyond the two caps commit A
  adds (response-byte cap, provider-row cap). It does not invent a new
  provider, a new HTTP client, or a parallel normalization path. The
  Windows Task Scheduler template's script wrapper
  (`scripts/refresh_spy_adjusted_data.ps1`) remains available unchanged as a
  manual/diagnostic entry point (see "Windows Scheduled Task Update"); it is
  not the unattended scheduled path after commit B.
- It is **dry-run by default**, matching `autonomy-apply-plan`'s shape.
  Without the explicit `--apply` switch it resolves what *would* run and is
  **fully side-effect-free**: no HTTP request, no credential lookup, no
  ledger read or write, no lock acquisition, and no runtime artifact write of
  any kind (corrects round-2 finding #5).
- Before any HTTP call it runs preflight in the fixed order defined in
  "Fail-Closed Refusal Conditions" below, which now explicitly includes: a
  canonical-target check, session resolution under the 20:10 ET
  provider-publication cutoff, a session-already-qualified short-circuit, a
  session attempt-budget check against the seam's own ledger, the mandatory
  live-capital interlock, and (apply-only) a canonical-`.env`-sourced
  credential presence check. `TIINGO_API_KEY` presence is checked against the
  resolved canonical `.env` file, never against the process environment; the
  seam itself never reads the token value, only the boolean the adapter's
  own `load_tiingo_api_key_from_dotenv` returns at the moment of the single
  authorized HTTP call.
- The seam is scoped to exactly `SPY`. Its own CLI accepts no caller-supplied
  symbol, path, or provider argument at all (see "Execution Architecture"),
  so `symbol_scope_violation` is a defence-in-depth internal assertion
  against a code defect, not a normally reachable refusal path.
- The seam itself is not, and never becomes, a place that reads, forwards, or
  requires an Alpaca/broker credential secret value — the adapter never
  looks one up, and the seam's own code never accesses an
  `alpaca_api_key`/`alpaca_secret_key`-shaped field directly. What round-1
  correctly flagged as contradictory is fixed: the live-capital interlock
  (`evaluate_live_capital_interlock`), which is a **mandatory** preflight
  step in both dry-run and apply mode (see "Mandatory Live-Capital Interlock
  Preflight"), inspects environment **shape** (profile string, endpoint
  classification, live-enable flags, live-host markers). Round-2 corrects a
  further inaccuracy: that mandatory call transitively constructs
  `AlpacaPaperConfig.from_env`, which **does** read the raw
  `ALPACA_API_KEY`/`ALPACA_SECRET_KEY`-family values from the environment
  into `repr=False` fields, and calls `require_paper_profile`, which
  validates those fields' presence/shape. This is truthfully described as:
  the interlock's own dependency closure loads repr-hidden credential
  strings into memory, but neither the interlock nor the seam ever logs,
  prints, serializes, discloses, forwards, or uses those values for a
  Tiingo or broker network call — the seam's own code path never reaches
  into `AlpacaPaperConfig`'s fields directly, only through the interlock's
  already-reviewed, secret-nondisclosing verdict object. Because the seam
  runs in-process (Execution Architecture), there is no child
  process/child-environment to isolate; the applicable defence-in-depth
  guarantee is a **static import-closure** test proving the seam module's
  transitive imports contain no broker SDK/client/order/position-mutation
  surface *outside* the interlock's own required safety closure (see
  "Read-Only Market-Data Is Not Live Trading").
- The seam performs and exposes no submit/cancel/replace/close/liquidation/
  paper-mutation/capital/live action. Every ledger record fixes
  `broker_access_attempted`, `broker_mutation_performed`,
  `paper_submit_performed`, `live_trading_performed`, and `live_authorized`
  to `false`, with `profit_claim=none`. Unlike the offline executor's
  ledger (which fixes `network_access_attempted=false` truthfully, because
  it never touches the network), this seam's ledger records
  `network_access_attempted` **truthfully as of the moment each event is
  written** (round-3 correction, finding #5): `false` on the reservation
  event (written *before* the HTTP call is made), `true` on the completion
  event (written after the HTTP call has resolved, success or a fully
  audited blocked outcome), and `false` on every refusal event and on a dry
  run or the session-already-qualified short-circuit (none of which ever
  reach the HTTP call). A ledger that hardcoded `false` on the completion
  event, or `true` on the reservation event, would be lying about the one
  thing this seam exists to do or about when it happened. A crash between
  the reservation and completion events leaves only the `false`-recording
  reservation on disk; that `false` describes only what was true at write
  time, not a guarantee the network was never subsequently reached — see
  "Sanitized Receipt And Provenance" for the full per-event schema.

## Implementation Milestone Shape

On acceptance, this contract authorizes exactly **one** implementation
milestone/PR, containing exactly two ordered commits, reviewed together as a
single review pass (not two separate review cycles, and not a second frozen
contract):

- **Commit A — adapter hardening.** Adds the two finite caps identified as
  gaps ("Finite Caps" below: an exact 8,388,608-byte response ceiling and an
  exact 20,000-row provider-row ceiling) to
  `etf_sma_adjusted_spy_data_refresh.py`, each failing closed with the
  sanitized categories `provider_response_too_large` and
  `provider_row_count_exceeded` respectively, plus targeted tests. This
  commit touches only the existing adapter; it adds no new module and wires
  no new command.
- **Commit B — executor/planner/scheduled-task reachability.** Adds the new
  in-process seam module
  (`src/algotrader/execution/autonomy_read_only_network_executor.py`), the
  new `AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST`, the new
  `EXECUTION_AUTHORIZED_NETWORK_READ_ONLY` planner classification for
  `run_authorized_read_only_market_data_refresh_to_seed_soak`, the narrow
  `ActionClass.__post_init__` command-carve-out and updated class docstring
  (round-3 correction, finding #1 — see "Planner Classification"), the
  two-way closure/disjointness/no-false-auto-offline/reverse-reachability
  tests plus the carve-out-is-narrow tests (see "Planner Classification,"
  Implementation Acceptance Criteria 1-5), the hand-curated-closure
  import-purity tests (round-3 correction, finding #4 — see "Read-Only
  Market-Data Is Not Live Trading"), the exclusive ledger-lock mechanism and
  reservation/completion/refused ledger writer with the corrected
  zero/one/two-record cardinality and per-event-type nullable schema
  (round-3 corrections, findings #3 and #5 — see "Concurrency And Ledger
  Locking" and "Sanitized Receipt And Provenance"), the exact-membership
  `qualifying_session_dates` short-circuit check (round-3 correction,
  finding #2 — see "Retry And Idempotency Behavior"), the single-cached-read
  credential provider object (see "Freeze One Credential Source"), the new
  `scripts/run_spy_read_only_network_executor.ps1` wrapper, and the Windows
  Task Scheduler template update (see "Windows Scheduled Task Update"). This
  commit depends on commit A's caps and must not land ahead of it.

Both commits land in the same PR and are reviewed together against this
contract in one pass. `spy_offline_daily_cycle` consumption of the refreshed
data remains outside this milestone's scope and requires its own future
frozen contract, exactly as originally stated (see "Explicit Non-Goal"
below) — this milestone shape does not expand that boundary.

## Execution Architecture

Exactly one execution architecture is frozen; it is not an implementation
choice:

- **Entry point:** an in-process, directly invoked Python module,
  `src/algotrader/execution/autonomy_read_only_network_executor.py`, run as
  `python -m algotrader.execution.autonomy_read_only_network_executor --as-of
  <ISO8601_UTC> [--apply] --format json`. These three flags
  (`--as-of`, `--apply`, `--format`) are the **entire** CLI surface; the
  parser refuses (exit code `2`) on any other argument, including any
  attempted `--profile`, path, symbol, or provider override — there is no
  caller-substitutable input besides the timestamp and the apply switch.
- **No child process.** The module does not `subprocess.run`, `spawn`, or
  otherwise launch a separate interpreter or script; it imports and calls the
  adapter's existing public `run_spy_adjusted_data_refresh` function and
  `ETFAdjustedDataRefreshConfig` dataclass directly, in the same process. It
  therefore makes no child-environment isolation claim of any kind — there is
  no child environment. The applicable safety guarantee is a **static
  import-closure** test (see "Read-Only Market-Data Is Not Live Trading"),
  not a spawned-process environment sanitization test.
- **Allowed imports.** The module may import
  `algotrader.execution.etf_sma_adjusted_spy_data_refresh` (the adapter),
  `algotrader.execution.live_capital_interlock` (the safety interlock), and
  `algotrader.execution.exchange_session` (the NYSE session calendar the seam
  needs to resolve the session its own ledger is keyed by — **round-6
  amendment**, rationale under "Direct-import scope"). Its
  static import closure — an explicit, hand-curated, seven-file list, not a
  generic whole-repository transitive-graph claim (round-3 correction,
  finding #4) — must contain no broker SDK, broker client, order, position,
  or mutation-surface module, proved by the flat-scan AST rules in
  "Read-Only Market-Data Is Not Live Trading," the same
  `DependencyRule`/`_dependency_violations` mechanism
  `test_dependency_direction.py` already applies to comparably-scoped
  adapters, applied here as new tests.
- **Dry-run vs. apply (round-2 corrects finding #5).** Without `--apply`,
  the module is **fully side-effect-free**: **zero** credential lookup,
  **zero** HTTP request, **zero** ledger lock acquisition, and **zero**
  ledger or runtime artifact write of any kind (no `"pending"`,
  `"completed"`, or `"refused"` ledger record is ever written in dry-run
  mode). It first reads the adapter's existing soak report (not the seam's
  own ledger) to determine the exact-membership session-already-qualified
  short-circuit (round-3 correction, finding #2 — see "Retry And
  Idempotency Behavior"); if that short-circuits, the invocation exits `0`
  without ever evaluating the interlock. Otherwise (a **pending** dry run),
  it evaluates and reports the sanitized live-capital interlock verdict,
  purely in-memory, as an informational `apply_eligible` signal (round-2
  corrects finding #6: a failing verdict never hard-refuses a dry run — see
  "Mandatory Live-Capital Interlock Preflight," refined by round-3
  correction #5) and exits `1`. Both paths are read-only and involve no
  credential or network access. With `--apply`, it additionally acquires
  the ledger lock, performs the ledger validation/attempt-budget check, the
  credential-presence check, and, if every preflight passes, the single
  authorized HTTP GET.
- **Deterministic IDs, not caller-supplied ones.** The module accepts no
  `--run-id`, `--session-id`, or path override. It derives, deterministically
  from `--as-of` and the seam's own ledger state, exactly:
  - `session_id`: the resolved NYSE session date (`YYYY-MM-DD`) that
    `--as-of` maps to under the 20:10 ET provider-publication cutoff (see
    "Deterministic Expected-Session Semantics").
  - `attempt_number`: one plus the count of prior unique `reservation_id`s
    recorded for that exact `session_id` with `ledger_status` in
    `{"pending", "completed"}` (round-2 correction — previously counted only
    `network_access_attempted=true` records, undercounting a crash-pending
    attempt; see "Concurrency And Ledger Locking"). Refusals
    (`ledger_status="refused"`) and short-circuits do not increment it. This
    count is read only on the apply path, under the ledger lock; dry-run
    never computes a ledger-derived `attempt_number`.
  - `run_id`: the fixed string `f"network-{session_id}-{attempt_number}"`,
    also used as `reservation_id`.
  No caller input can substitute any of these three values.
- **One canonical, append-only ledger path**, frozen exactly:
  `runs/autonomy_network_executor/ledger.jsonl`, with one canonical sidecar
  lock file, frozen exactly: `runs/autonomy_network_executor/ledger.lock`
  (new in round-2, see "Concurrency And Ledger Locking"). Unlike the offline
  executor's single-record-replace ledger, this ledger is **append-only**
  (new JSONL lines are added, never truncated or rewritten), because the
  session attempt-budget check requires reading the full prior history for a
  `session_id` across invocations. Every line is validated against the
  ledger's own fixed schema (see "Sanitized Receipt And Provenance") as it
  is read; if the file exists but contains any malformed line, any line
  failing schema validation, or a required read fails for a reason other
  than the file cleanly not existing, the seam refuses closed with
  `ledger_corrupt` (renamed from round-1's `ledger_state_corrupt` for
  consistency with the sibling `ledger_lock_unavailable` category) rather
  than assuming zero prior attempts — a missing file is not itself
  corruption (it is the legitimate state before the first-ever invocation),
  but an unreadable, partially-parseable, or schema-invalid file is treated
  as an untrustworthy attempt count and must never be silently treated as
  empty.
- Root/cwd validation for this module mirrors
  `autonomy_next_plan.py`'s/`autonomy_offline_executor.py`'s canonical-root
  binding: the module refuses (`noncanonical_target`) unless the resolved
  executing root, cwd, and every one of the eight canonical paths (the six
  adapter destination paths below, the ledger path, and the ledger lock path
  above) resolve exactly as fixed here, with no symlink escape. (Round-2
  corrects this from "seven" to "eight" canonical paths to include the new
  lock file.)

## Fixed Internal Adapter Configuration

The seam constructs a fully-defaulted, fixed `ETFAdjustedDataRefreshConfig`
in-process — no caller-substituted path, symbol, or provider field — and
calls `run_spy_adjusted_data_refresh(config, token_lookup=..., http_get=...)`
exactly as the adapter's own `main()` already does for
`--mode live_market_data_fetch --live-market-data-fetch-authorized`. Every
field below is a canonical constant the seam must validate byte-for-byte
before the call; a mismatch anywhere is a refusal
(`noncanonical_target`), not a substitution:

| `ETFAdjustedDataRefreshConfig` field | Fixed value |
| --- | --- |
| `provider` | `"tiingo"` |
| `symbol` | `"SPY"` |
| `mode` | `"live_market_data_fetch"` |
| `live_fetch_authorized` | `True` (apply path only; the config is never constructed with this `True` on a dry run) |
| `output_csv` | `.data/operator_inputs/spy_tiingo_adjusted_refresh_latest.csv` |
| `canonical_csv` | `runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv` |
| `run_log` | `runs/paper_lab/m446_adjusted_spy_bars_refresh_manifest.jsonl` |
| `raw_response_path` | `runs/paper_lab/tiingo_spy_adjusted_raw_latest.json` |
| `soak_ledger` | `runs/paper_lab/spy_adjusted_market_data_soak_ledger.jsonl` |
| `soak_report` | `runs/paper_lab/spy_adjusted_market_data_soak_report.json` |
| `soak_required_sessions` | `5` |
| `start_date` | `"auto"` |
| `revision_lookback_days` | `10` |
| `token_env_var` | `"TIINGO_API_KEY"` |
| `expected_latest_bar_date` | the deterministic `session_id` resolved from `--as-of` (see "Deterministic Expected-Session Semantics") |
| `run_id` | the seam's own deterministic `run_id` (`network-<session_id>-<attempt_number>`), passed through so the adapter's own manifest records the same identifier as the seam's ledger |

`token_lookup` is `lambda name: <cached value from the seam's single
credential-provider object>` — the provider object calls
`load_tiingo_api_key_from_dotenv(<resolved canonical .env path>,
token_env_var=name)` exactly once per apply invocation and serves both the
presence check and this `token_lookup` from that one cached result (see
"Freeze One Credential Source"; corrects round-2 finding #2). `http_get` is
the adapter's existing internal Tiingo HTTP GET function, passed through
unchanged — the seam does not reimplement it.

The six destination paths above are unchanged from the original freeze; only
their framing changed, from PowerShell/CLI argv to in-process config fields,
to match the frozen in-process architecture.

## Deterministic Expected-Session Semantics

The adapter's own CLI (`etf_sma_adjusted_spy_data_refresh.main`) falls back
to `datetime.now(UTC)` when `--expected-latest-bar-date` is omitted
(`_default_expected_latest_bar_date`, reading the wall clock). The seam
**must never rely on that fallback and must never omit the field**; it always
passes an explicit, derived `--expected-latest-bar-date` equivalent into the
adapter's config.

The seam requires its own caller-supplied, explicit `--as-of` (an ISO-8601
UTC timestamp), exactly mirroring the `-AsOf` requirement already frozen for
the supervisor/planner/executor (`docs/OPERATOR_RUNBOOK.md`'s V5.37/V5.38
sections: "`-AsOf` is required and is the only time source"). Round-1 found
the original derivation — directly calling
`NyseExchangeSessionCalendar.latest_completed_session_on_or_before(as_of)`
with no time-of-day awareness — insufficient, because it could treat a
same-day, pre-close, or pre-publication `--as-of` as if that day's session
were already expected. This round freezes an explicit
**provider-publication cutoff**, matching the boundary
`docs/OPERATOR_RUNBOOK.md`'s "Authoritative SPY EOD Market-Data Refresh"
section already documents for the scheduled task's own registration time
(20:10 America/New_York, chosen because Tiingo documents most EOD prices near
17:30 ET with corrections through 20:00 ET):

1. Convert `--as-of` (UTC) to America/New_York wall-clock time.
2. Let `calendar_session` be the NYSE session date (if any) matching that
   converted date. (If the converted date is not itself a NYSE session — a
   weekend or holiday — treat step 2 as producing no same-day candidate and
   proceed as if the converted wall-clock time were before the cutoff.)
3. If the converted wall-clock time is **at or after 20:10 ET** on
   `calendar_session`, the expected session is `calendar_session`.
4. Otherwise (including when `calendar_session` does not exist), the expected
   session is `NyseExchangeSessionCalendar.latest_completed_session_on_or_before`
   evaluated at a timestamp one full day before the converted date's midnight
   — i.e., the most recent NYSE session date strictly before the converted
   calendar date.
5. **Early-close sessions use the same fixed 20:10 ET cutoff as every other
   session.** This is deliberate: the cutoff models *when Tiingo has
   published data*, not the session's own close-plus-offset. An early close
   does not make provider publication happen any earlier.
6. The same `--as-of` input always resolves to the same expected session
   (pure function of the input, no other state).

If, after this resolution, the provider's response still lacks the expected
session's row (a real-world publication delay beyond the modeled cutoff), the
adapter's existing `expected_latest_bar_date` mismatch handling fails that
attempt closed exactly as it does today; a later, separately capped retry
(within the same session's four-attempt budget, see "Finite Caps") may
recover once the provider actually publishes.

## Finite Caps

| Cap | Existing? | Bound |
| --- | --- | --- |
| HTTP timeout | yes (`_HTTP_TIMEOUT_SECONDS = 20.0`) | 20 seconds, no retry inside `_tiingo_http_get` |
| HTTP requests per invocation | yes (implicit — exactly one `http_get` call per `_build_refresh_payload` run) | exactly 1 |
| Response byte size | **no — commit A gap** | fixed at exactly **8,388,608 bytes (8 MiB)**; `response.read()` must be capped to this ceiling and fail closed with sanitized category `provider_response_too_large`, not an unbounded read |
| Accepted provider row count | **no — commit A gap** | fixed at exactly **20,000 rows** (comfortably above a full 1993-to-date SPY daily history, on the order of 8,000 rows); a parsed response exceeding this must be rejected with sanitized category `provider_row_count_exceeded` |
| Revision lookback window | yes (`RevisionLookbackDays`, 1-31, default 10) | unchanged, adapter-enforced, fixed at **10 days** by the seam's config |
| Authorized GET attempts per resolved NYSE session | new, seam-level, corrects round-1 finding #3 | at most **4** authorized attempts (one initial plus three retries) per `session_id`, counted as unique reservation ids (pending or completed) and enforced fail-closed, under an exclusive ledger lock (round-2, see "Concurrency And Ledger Locking"), by the seam's own canonical append-only ledger (`runs/autonomy_network_executor/ledger.jsonl`) **before** credential access or HTTP on every apply invocation. This exactly matches the existing Windows Task Scheduler template's `RestartOnFailure` policy (`Interval=PT15M`, `Count=3` — one initial run plus three restarts). The seam itself performs **no internal retry, loop, or sleep**; the four-attempt budget is spent across *separate invocations* (typically the scheduler's own restarts), never within one process's execution, and the lock guarantees those separate invocations cannot race each other. |

Commit A must add the two gap rows to `etf_sma_adjusted_spy_data_refresh.py`
as part of the single implementation milestone this contract authorizes on
acceptance (see "Implementation Milestone Shape"); no second contract is
required.

### Session Attempt Budget

On every `--apply` invocation, after resolving `session_id` (and after the
session-already-qualified short-circuit — see "Retry And Idempotency
Behavior" — has been checked and found not to apply), the seam acquires the
ledger lock (see "Concurrency And Ledger Locking") and, while holding it,
reads `runs/autonomy_network_executor/ledger.jsonl` and counts **unique
reservation ids** recorded for that exact `session_id`, whether `pending` or
`completed` (round-2 correction, finding #4 — previously counted only
records with `network_access_attempted=true`, which undercounted a
crash-interrupted attempt as if it had never happened).

- If that count is `>= 4`, the seam refuses closed with
  `session_attempt_budget_exhausted`, releases the lock, and exits `2`. It
  performs no credential lookup and no HTTP call, writes no reservation, and
  writes exactly one locked, non-reservation `"refused"` ledger event (the
  ledger is already known-valid and the lock is already held at this point,
  unlike `ledger_lock_unavailable`/`ledger_corrupt` — see "Concurrency And
  Ledger Locking," round-3 correction #3); that event's `interlock_verdict`
  is `null`, because this refusal is reached before the interlock step ever
  runs (see "Fail-Closed Refusal Conditions" and "Sanitized Receipt And
  Provenance," round-3 correction #5).
- If that count is `< 4`, the seam proceeds, still holding the lock, to the
  live-capital interlock and (if that passes) the credential-presence check,
  then writes the reservation record (`attempt_number = count + 1`,
  `reservation_id = run_id`, `ledger_status = "pending"`), flushes and
  `fsync`s it, and only then performs the single HTTP GET. On completion
  (success or a fully audited blocked outcome) it appends a completion
  record referencing the same `reservation_id` (`ledger_status =
  "completed"`), flushes and `fsync`s it, and releases the lock in a
  `finally` block. **Round-3 correction (finding #5, P1):** the reservation
  record's `network_access_attempted` is `false` — truthful as of the
  moment that event is written, since the HTTP call has not yet been made
  — and the completion record's `network_access_attempted` is `true`,
  written only after the HTTP call has actually resolved. The prior text's
  claim that `network_access_attempted=true` is "recorded in the
  reservation the moment it is written" was temporally backwards (the
  reservation precedes the HTTP call by construction) and is removed. The
  attempt-budget count itself is unaffected by this correction: it counts
  unique `reservation_id`s with `ledger_status` in `{"pending",
  "completed"}`, never the `network_access_attempted` boolean — reaching
  the network is what the budget counts, not provider success, and budget
  consumption is already fully captured by a `"pending"` reservation
  existing at all.
- **Crash-pending reservations consume budget, fail-closed.** If the process
  is killed after the reservation record is written (and fsynced) but before
  the completion record is written, that reservation's `ledger_status`
  remains `"pending"` on disk. A later invocation reading the ledger counts
  it toward the same session's four-attempt budget exactly as it would count
  a completed one; the budget is never silently refunded by a crash. A later
  read of that reservation always reports the same `"pending"` state
  deterministically until (if ever) a subsequent invocation's completion
  record is appended for that same `reservation_id`.
- Once a session's soak evidence shows the exact `session_id` present in
  `qualifying_session_dates` (round-3 correction, finding #2 — never
  `latest_session_qualified` alone, see "Retry And Idempotency Behavior"),
  later invocations for that same session no-op **before** the
  attempt-budget read, before lock acquisition, and before credential
  access, via the session-already-qualified short-circuit (mechanism
  unchanged from the original freeze, now explicitly ordered ahead of the
  attempt-budget check and explicitly keyed on exact-session membership
  rather than a report-wide boolean).

## Concurrency And Ledger Locking

New in round-2, correcting finding #4 (P1): the four-attempt budget above is
enforced under a mandatory exclusive lock, so two invocations (a manual run
racing a scheduler restart, or two overlapping scheduler retries) can never
both observe the same prior count and both proceed.

- **Lock file**: one canonical sidecar path, frozen exactly:
  `runs/autonomy_network_executor/ledger.lock` (see "Execution Architecture"
  — this is now one of the eight canonical paths the module validates before
  any other step).
- **Mechanism**: an exclusive OS-level advisory lock obtained through a
  repository stdlib wrapper — `msvcrt.locking` on Windows, `fcntl.flock` on
  POSIX — never a third-party locking library and never a purely
  application-level "check a marker file's existence" convention, which
  would not be atomic across processes.
- **Timeout**: a fixed 5-second wait for the lock. If it cannot be acquired
  within 5 seconds, the seam refuses closed with `ledger_lock_unavailable`,
  performs no ledger read, no credential lookup, no HTTP call, and **zero
  ledger write of any kind** (round-3 correction, finding #3, P1 — there is
  no exclusive-lock-protected way to append safely when the lock itself
  could not be acquired, so the seam does not attempt one; the refusal is
  reported only in the sanitized CLI/`--format json` output, never
  persisted), and exits `2`.
- **Scope**: the lock is acquired once the session-already-qualified
  short-circuit has been checked and found not to apply, and is held
  continuously across: ledger validation and the attempt-budget read, the
  live-capital interlock, the credential-provider load (see "Freeze One
  Credential Source"), the reservation append (flush + `fsync`), the single
  HTTP GET, and the completion append (flush + `fsync`). It is released in a
  `finally` block — on success, on any refusal reached while holding it, and
  on an unhandled exception — so a crash never leaves the OS-level lock held
  past process exit (the OS releases the underlying file lock when the
  process dies; only the ledger's own `"pending"` reservation state persists
  across the crash, which is the fail-closed budget behavior described
  above, not a stuck lock).
- **Effect**: a second, genuinely concurrent invocation for the same or a
  different session blocks for up to 5 seconds and then either proceeds
  (once the first invocation releases the lock) or refuses closed with
  `ledger_lock_unavailable` — it can never interleave a read and a write
  with the first invocation. Direct/manual invocations and Task
  Scheduler-triggered invocations are both bound by the same lock file, so a
  manual retry cannot race a scheduled retry, and two scheduled retries
  (e.g., a slow first attempt still running when a second `RestartOnFailure`
  trigger fires) cannot race each other.
- **Ledger validation**: every line read from `ledger.jsonl` is checked
  against the ledger's own fixed schema (see "Sanitized Receipt And
  Provenance"). Any malformed line, any line failing schema validation, or
  any read failure other than the file cleanly not existing yet, refuses
  closed with `ledger_corrupt` rather than silently treating the ledger as
  empty (renamed in round-2 from `ledger_state_corrupt` for naming
  consistency with `ledger_lock_unavailable`; no behavior change from
  round-1's intent). **Round-3 correction (finding #3, P1):** a
  `ledger_corrupt` refusal performs **zero ledger write of any kind** — the
  seam does not append a "refused" event (or any other event) to a file it
  has just proven is malformed, unreadable, or schema-invalid; appending to
  an already-corrupt file would compound the corruption rather than record
  anything trustworthy. The refusal is reported only in the sanitized
  CLI/`--format json` output, exit `2`, exactly like `ledger_lock_unavailable`.

## Retry And Idempotency Behavior

- Within one seam invocation: **zero retries**. A failed HTTP attempt,
  invalid JSON, or blocked normalization ends that invocation in a
  `blocked_*` refresh state; the previous canonical file is preserved
  (existing adapter behavior — `previous_canonical_preserved_on_failure`).
- Across invocations: the soak evidence layer
  (`etf_sma_market_data_soak.py`) already deduplicates by **expected NYSE
  session**, not by attempt, so re-invoking the seam again after a failure,
  within the same session's four-attempt budget, is a legitimate same-session
  retry, not a duplicate — this existing behavior is preserved unchanged.
  Round-1 correctly flagged that the original "1 per UTC day" cap could
  conflict with this; the corrected "Session Attempt Budget" above resolves
  it by budgeting per session across up to four invocations instead of per
  calendar day.
- The seam's own narrower idempotency check, purely to bound *network*
  usage: **round-3 correction (finding #2, P1)** — the seam validates the
  soak report and short-circuits to a no-op
  (`skipped_session_already_qualified`) if, and only if, the exact
  `session_id` that `--as-of` resolves to for *this* invocation appears
  verbatim in the soak report's `qualifying_session_dates` list. The seam
  never reads or branches on `latest_session_qualified` for this or any
  other purpose: that field (`etf_sma_market_data_soak.py`'s
  `build_adjusted_market_data_soak_report`) describes only whether the
  report's own most-recently-*attempted* session qualified, which need not
  be, and is not required to be, the same session this invocation's
  `--as-of` resolves to — branching on it would both wrongly short-circuit
  (a different, unrelated session happens to be the latest-qualified one)
  and wrongly fail to short-circuit (the resolved `session_id` already
  qualified in an earlier, non-latest report entry). The corrected,
  membership-exact check happens **before** ledger lock acquisition, the
  attempt-budget check, the live-capital interlock, or the credential
  check, performing zero HTTP requests and zero ledger writes, in both
  dry-run and apply mode. This is a network budget guard, not a correctness
  requirement — the soak layer would already record a same-session retry
  safely even without it.

## Mandatory Live-Capital Interlock Preflight

Corrects round-1 finding #1 (P0). The seam calls
`evaluate_live_capital_interlock(os.environ)`
(`algotrader.execution.live_capital_interlock`) as a **mandatory** preflight
step, in both dry-run and apply modes, before any credential access or HTTP
call. This is an environment-shape safety check — it reads `APP_PROFILE`,
the configured Alpaca base URL, and a fixed set of live-enable/live-host
environment variable *names*, and returns a sanitized verdict; it performs no
order, mutation, or network action of its own. It is not a forbidden broker
surface, and the original contract's framing that implied Alpaca/broker
considerations were entirely out of scope here was the defect; that framing
is removed.

**Round-2 correction (finding #1, P0):** the claim that this check "never
reads a credential secret" was itself false and is now removed.
`evaluate_live_capital_interlock` constructs `AlpacaPaperConfig.from_env`,
which reads the raw `ALPACA_API_KEY`/`ALPACA_API_KEY_ID`/`APCA_API_KEY_ID`
and `ALPACA_SECRET_KEY`/`ALPACA_API_SECRET_KEY`/`APCA_API_SECRET_KEY`-family
values into `alpaca_api_key`/`alpaca_secret_key` dataclass fields
(`field(repr=False)` — excluded from `repr()`/`str()`, but genuinely
populated and held in memory for the duration of the call), and calls
`require_paper_profile`, which validates those fields' presence/shape. The
truthful, corrected claim is narrower and still true: the interlock and its
dependency closure never **log, print, serialize, return, disclose, forward,
or use** an Alpaca credential value for any Tiingo or broker network
operation — `LiveCapitalInterlockVerdict.to_dict()` and every field the seam
persists contain only booleans and blocker/variable **names**, never a
credential or URL value — and the seam's own code never directly accesses an
`AlpacaPaperConfig` field. See "Read-Only Market-Data Is Not Live Trading"
for the corresponding import-purity test correction.

- The seam requires `verdict.paper_boundary_ok is True`: `APP_PROFILE` equal
  to the paper profile, the resolved Alpaca base URL classified as a paper
  endpoint, and no detected live-enable flag or live-host marker.
- **Apply mode**: if `paper_boundary_ok` is `False`, the seam hard-refuses
  (`live_capital_interlock_blocked`), performs no credential lookup and no
  HTTP call, exits `2` (see "Exit Codes"), and — because this refusal occurs
  after the lock is held and the ledger has already been validated (see
  "Concurrency And Ledger Locking," round-3 correction #3), unlike
  `ledger_lock_unavailable`/`ledger_corrupt` — writes exactly **one**
  locked, non-reservation `"refused"` ledger event recording the verdict's
  own sanitized `to_dict()` output (booleans and blocker/variable names
  only, never a credential or URL value); that event does not consume
  session attempt budget.
- **Dry-run mode (round-2 correction, finding #6, P2; refined by round-3
  correction, finding #5):** for a **pending** (non-short-circuited) dry
  run, the interlock is evaluated for sanitized informational readiness,
  but a failing or unset `paper_boundary_ok` verdict **does not hard-refuse
  a dry run**. The dry-run output sets `apply_eligible=false` and includes
  the sanitized verdict so an operator can see why an eventual `--apply`
  would be refused, but the dry-run invocation itself still completes with
  exit `1` per "Exit Codes," never `2` on interlock grounds alone. For an
  **already-qualified short-circuit** dry run, the interlock is **never
  evaluated** — the short-circuit check (step 5) precedes the interlock
  check (step 8) in the fixed order in "Fail-Closed Refusal Conditions," so
  execution never reaches step 8 — and the dry-run output's
  `interlock_verdict`-shaped informational field is `null`, exit `0`. Only
  apply mode hard-refuses on interlock grounds.
- This check subsumes and replaces the original contract's narrower
  `APP_PROFILE=live present -> refuse` bullet, which is now a strict subset
  of what `paper_boundary_ok` already requires.

## Freeze One Credential Source

Corrects round-1 finding #2 (P1) and round-2 finding #2 (P1). Exactly one
credential source is frozen, and it is read from that source **exactly once
per apply invocation**: the canonical repository-root `.env` file, via the
adapter's existing, unchanged `load_tiingo_api_key_from_dotenv` function.

- The canonical `.env` path is resolved once, from the same validated
  canonical repository root used for every other path check in this
  contract: `Path(<canonical root>, ".env").resolve()`. The resolved path's
  parent must equal the resolved canonical root exactly, with no symlink
  escape; a mismatch is a refusal (`credential_path_noncanonical`), distinct
  from the six adapter-destination-path `noncanonical_target` refusal, so a
  reviewer can tell the two apart in a ledger record.
- **Round-2 correction: a single frozen credential-provider object, not two
  calls.** After every noncredential preflight step has passed (root/path,
  `--as-of`/session, already-qualified short-circuit, attempt-budget check —
  see "Fail-Closed Refusal Conditions") and while the seam still holds the
  ledger lock (see "Concurrency And Ledger Locking"), the seam constructs
  exactly one private, module-internal credential-provider object that calls
  `load_tiingo_api_key_from_dotenv(<resolved canonical .env path>,
  token_env_var="TIINGO_API_KEY")` **exactly once**. That single call's
  result is cached inside the provider object, which:
  - never appears in a `repr()`, log line, ledger record, argv, stdout,
    stderr, artifact, or handoff document;
  - exposes to the rest of the seam (including whatever emits the executor's
    own audit/report output) only a derived `available: bool` — `True` if
    the cached value is not `None`, `False` otherwise — never the cached
    string itself;
  - supplies `token_lookup=lambda name: <cached value>` to the adapter's
    `run_spy_adjusted_data_refresh` call (see "Fixed Internal Adapter
    Configuration"), returning the already-cached value without calling
    `load_tiingo_api_key_from_dotenv` again.
  This means the executor process itself never receives or holds the token
  as a plain string outside that one provider object's private field; it
  only ever observes the `available` boolean.
- **Presence** is this cached `available` boolean. If it is `False` (file
  absent, or present without a `TIINGO_API_KEY` entry), the seam refuses
  (`token_not_available`), performs no HTTP call, and writes exactly **one**
  locked, non-reservation `"refused"` ledger event recording only the
  boolean — never the file's contents or any other variable it might
  contain (this refusal is reached after the lock is held and the ledger
  validated, like `live_capital_interlock_blocked` and
  `session_attempt_budget_exhausted`, unlike `ledger_lock_unavailable`/
  `ledger_corrupt`; see "Concurrency And Ledger Locking," round-3 correction
  #3). This check, and the one dotenv read backing it, occur only on the
  apply path (never on dry-run, per "Execution Architecture" and the
  fully side-effect-free dry-run contract in "Non-Negotiable Safety
  Contract").
- **Process-environment `TIINGO_API_KEY` values are ignored by this command
  entirely.** The seam never reads `os.environ["TIINGO_API_KEY"]` for any
  purpose, preflight or otherwise. This removes the process-environment
  presence check round-1 flagged as contradicting the dotenv-sourced fetch.
- On a successful apply, the adapter obtains the credential value from the
  provider object's cached `token_lookup`, after every other preflight
  (root/path/action/interlock/attempt-cap/credential-presence) has passed,
  and passes it only to the adapter's existing exact Tiingo `Authorization:
  Token <value>` header boundary (`_tiingo_http_get`'s existing header-scope
  validation). The seam's own ledger, argv, stdout, stderr, artifacts, and
  any handoff document receive only the boolean presence/outcome, never the
  raw value. A targeted test must assert `load_tiingo_api_key_from_dotenv`
  (or the file I/O it performs) is invoked exactly once per apply
  invocation, and that no seam-emitted output contains the token value.

## Sanitized Receipt And Provenance

The seam does not invent a new receipt shape for the adapter's own output.
It relies entirely on the existing, already-implemented chain:

- the refresh manifest's provider/canonical/output hashes
  (`source_sha256`, `current_canonical_sha256`, `normalized_output_sha256`,
  `canonical_csv_sha256`);
- the existing safety-false fields (`token_value_recorded=false`,
  `market_data_token_value_printed=false`,
  `market_data_token_value_written=false`, `broker_access_attempted=false`,
  etc., already emitted by `_manifest`);
- the existing soak receipt/report builders
  (`build_adjusted_market_data_soak_receipt`,
  `build_adjusted_market_data_soak_report`), which already exclude every
  credential value and already assert a hash-bearing, secret-free record.

The seam's own execution ledger is new, appended to the frozen canonical path
`runs/autonomy_network_executor/ledger.jsonl` (see "Execution Architecture").
Corrects round-1 finding #8 by naming the exact fields rather than leaving
them to implementation judgment.

**Round-3 correction (finding #5, P1):** the prior text specified "one JSONL
record appended per invocation" with a single flat field list, implying
every field is populated on every record. That is both wrong (dry-run and
several refusal categories write zero records; some fields are null on some
event shapes by construction, not by omission) and internally contradicted
by round-2's own zero-write dry-run/short-circuit rule and by the
fixed-ordering rule that puts `session_attempt_budget_exhausted` before the
interlock step. The corrected, exact cardinality is:

| Path | Ledger records written |
| --- | --- |
| Dry-run (any outcome) | **zero** |
| Already-qualified short-circuit (dry-run or apply) | **zero** |
| Any pre-lock failure — steps 1-4 (parser, root/path, credential-path, `--as-of`) | **zero** |
| `ledger_lock_unavailable` (step 6) | **zero** (round-3 correction #3 — no safe append without the lock) |
| `ledger_corrupt` (step 7) | **zero** (round-3 correction #3 — the file is already proven untrustworthy) |
| `session_attempt_budget_exhausted` (step 7), `live_capital_interlock_blocked` (step 8), or `token_not_available` (step 9) | **exactly one** — a single, non-reservation `"refused"` event; no reservation is ever written for these |
| An actual attempt (step 10 reached) | **exactly two**, fsynced in order — one `"pending"` reservation event (written and fsynced *before* the HTTP call), then one `"completed"` event (written and fsynced after the HTTP call resolves, referencing the same `reservation_id`) |
| Process killed after the reservation event but before the completion event | **one** — the `"pending"` reservation persists on disk; no completion is ever appended for that `reservation_id`. The reservation still consumes session attempt budget (see "Session Attempt Budget"); a `"pending"` status means the eventual network outcome is unknown, **not** proof the network was never reached — the crash could equally have occurred immediately before or immediately after the actual HTTP call. |

The `ledger_status` value **is** the event's type, and each of the three
types has its own frozen, nullable field schema. Every event fixes
`record_type="autonomy_network_execution_ledger_event"`,
`schema_version=1`,
`action_token="run_authorized_read_only_market_data_refresh_to_seed_soak"`,
`apply=true`, and `session_already_qualified=false`. All three also share
`run_id`, `session_id`, `attempt_number`, `as_of`,
`attempt_budget_exhausted`,
`broker_access_attempted=false`, `broker_mutation_performed=false`,
`paper_submit_performed=false`, `live_trading_performed=false`,
`live_authorized=false`, `profit_claim="none"`):

- **`"pending"` (reservation event)**: `reservation_id` = `run_id`;
  `exit_code` = `null` (the invocation has not concluded); `adapter_refresh_state`
  = `null` (the adapter has not been called yet); `network_access_attempted`
  = `false` (accurate as of this event's write time — the HTTP call has not
  yet been made; see "Non-Negotiable Safety Contract"); `interlock_verdict`
  = the sanitized passing verdict (interlock has already passed, since it
  precedes reservation in the fixed order); `credential_present` = `true`
  (credential presence has already passed); `refusal_category` = `null`.
- **`"completed"` (completion event)**: `reservation_id` = the same `run_id`
  as its reservation; `exit_code` = `0` or `1` (per "Exit Codes"; never `2`
  — a completion event only exists once the HTTP call has actually resolved);
  `adapter_refresh_state` = the adapter's own `refresh_state` string,
  non-null; `network_access_attempted` = `true` (the HTTP call has now
  actually resolved, success or a fully audited blocked outcome);
  `interlock_verdict` = the same passing verdict as its reservation;
  `credential_present` = `true`; `refusal_category` = `null`.
- **`"refused"` (locked, non-reservation refusal event — only for
  `session_attempt_budget_exhausted`, `live_capital_interlock_blocked`, or
  `token_not_available`)**: `attempt_number` = the deterministic
  would-be next ordinal (`count + 1`) and `run_id` =
  `f"network-{session_id}-{attempt_number}"`, computed under the validated
  ledger lock; `reservation_id` = `null` (the ordinal identifies the
  refusal event but never reserves or consumes an attempt slot, and repeated
  refusals may therefore repeat that ordinal); `exit_code` = `2`;
  `adapter_refresh_state` =
  `null` (the adapter is never invoked); `network_access_attempted` =
  `false`; `interlock_verdict` = `null` for `session_attempt_budget_exhausted`
  (this refusal is reached *before* the interlock step ever runs) and the
  sanitized verdict (passing, for `token_not_available`, or failing, for
  `live_capital_interlock_blocked`) for the other two; `credential_present`
  = `null` for `session_attempt_budget_exhausted` and
  `live_capital_interlock_blocked` (the credential step is never reached)
  and `false` for `token_not_available`; `refusal_category` = the one named
  category that produced this event. `attempt_budget_exhausted` is `true`
  only for `session_attempt_budget_exhausted` and `false` for the other two
  refusal types; it is `false` on every reservation and completion event.

`ledger_lock_unavailable` and `ledger_corrupt` never produce any ledger
event of any type (round-3 correction #3) — their refusal is visible only in
the seam's sanitized CLI/`--format json` output, never persisted.

The seam's own stdout/`--format json` report (distinct from, and emitted on
every invocation regardless of whether a ledger event is written) carries an
analogous `interlock_verdict`-shaped informational field: it is `null` for
an already-qualified short-circuit (dry-run or apply — the short-circuit
check precedes the interlock step in the fixed order, so the interlock is
never evaluated) and populated, informationally, for a pending
(non-short-circuited) dry-run (per "Mandatory Live-Capital Interlock
Preflight," the interlock is always evaluated for `apply_eligible` reporting
in that case).

Never included in any ledger event or report: the token value, any raw
response body, any row-level market-data, or any Alpaca/broker credential
value.

## Fail-Closed Refusal Conditions

Checks run in this fixed order; the first failing check determines the
refusal category and terminates the invocation before any later check runs.
Steps marked **(apply only, under lock)** occur after the ledger lock (see
"Concurrency And Ledger Locking") has been acquired; steps marked **(dry-run
and apply)** run in both modes without ever acquiring the lock or touching
the ledger in dry-run mode.

1. Argument parsing: any argument other than `--as-of`, `--apply`, `--format`
   is a parser-level refusal, exit `2`.
2. Canonical root/cwd/path validation across all eight canonical paths (six
   adapter destination paths, the ledger path, and the ledger lock path —
   round-2 corrects this from seven to eight to include the lock file) →
   `noncanonical_target`, exit `2`.
3. Canonical `.env` path resolution (see "Freeze One Credential Source") →
   `credential_path_noncanonical`, exit `2`.
4. `--as-of` missing, not UTC, or not resolvable to a valid NYSE session
   under the 20:10 ET cutoff rule → `as_of_invalid`, exit `2`.
5. Session-already-qualified short-circuit (dry-run and apply; reads only
   the adapter's existing soak report, never the seam's own ledger; not
   itself an error) → exits `0` with `network_access_attempted=false` and,
   in apply mode, no ledger write at all (the short-circuit itself writes
   nothing; only a refused/attempted apply writes a ledger record).
6. **(apply only)** Ledger lock acquisition (round-2 addition; see
   "Concurrency And Ledger Locking") → `ledger_lock_unavailable` on a
   5-second timeout, exit `2`, **zero ledger write** (round-3 correction,
   finding #3 — the lock was never acquired, so no safe append is
   attempted). Not evaluated in dry-run mode.
7. **(apply only, under lock)** Ledger validation and session attempt-budget
   check (see "Session Attempt Budget" and "Concurrency And Ledger
   Locking") → either `ledger_corrupt` (malformed/schema-invalid/unreadable
   ledger; exit `2`, **zero ledger write** — round-3 correction, finding
   #3, appending to a proven-corrupt file is not attempted) or
   `session_attempt_budget_exhausted` (valid ledger, budget spent; exit
   `2`, **exactly one** locked, non-reservation `"refused"` event, with
   `interlock_verdict=null` since this step precedes the interlock — see
   "Sanitized Receipt And Provenance," round-3 correction #5). Not
   evaluated in dry-run mode.
8. Live-capital interlock (dry-run and apply; see "Mandatory Live-Capital
   Interlock Preflight") — **apply mode**: a failing verdict is a hard
   refusal, `live_capital_interlock_blocked`, exit `2`, exactly one locked,
   non-reservation `"refused"` event. **Dry-run mode**: a failing verdict
   never refuses; it only sets the dry-run report's `apply_eligible=false`
   (round-2 correction, finding #6) — dry-run never writes a ledger record.
9. **(apply only, under lock)** Credential presence via the canonical `.env`
   (see "Freeze One Credential Source") → `token_not_available`, exit `2`,
   exactly one locked, non-reservation `"refused"` event. Not evaluated in
   dry-run mode (dry-run never reads `.env`).
10. **(apply only, under lock)** The adapter's own internal preflight and
    fetch/normalize path, unchanged (`_live_market_data_fetch_preflight_blockers`,
    response-byte cap, row cap, revision-lookback enforcement, etc.). This is
    the step that actually issues the HTTP GET; its outcome determines exit
    `0` (accepted) or exit `1` (a fully audited blocked outcome), never exit
    `2` — by the time this step runs, every pre-HTTP refusal has already
    passed (see "Exit Codes").

Any refusal from steps 1-4 or 6-9 is exit code `2` (pre-HTTP,
input/precondition refusal), records zero network access, and never
performs a partial or best-effort fetch. Within that set, steps 1-4 and 6-7's
`ledger_lock_unavailable`/`ledger_corrupt` write **zero** ledger records
(round-3 correction, finding #3); steps 7's `session_attempt_budget_exhausted`,
8's `live_capital_interlock_blocked`, and 9's `token_not_available` each write
exactly **one** locked, non-reservation `"refused"` ledger event — see
"Sanitized Receipt And Provenance" for the exact per-event schema (round-3
correction, finding #5). `symbol_scope_violation` and an
explicit-`--profile`-style override are no longer separately reachable
refusal paths, because the frozen CLI (see "Execution Architecture") has no
symbol or profile argument to violate or override in the first place; both
remain as defence-in-depth internal assertions.

## Exit Codes

New in round-2, correcting finding #7 (P2) — the full exit-code scheme,
covering every path through the seam, dry-run and apply:

| Exit code | Meaning | Reached from |
| --- | --- | --- |
| `0` | Accepted apply (the HTTP GET was attempted and the adapter's own outcome is `refresh_state="accepted"`, i.e., success), **or** an already-qualified/no-action outcome. | Step 5's session-already-qualified short-circuit (dry-run or apply); or step 10's adapter outcome being a success in apply mode. |
| `1` | A pending valid dry-run (the invocation is well-formed, the session is not yet qualified, and an eventual `--apply` would attempt the network — regardless of the informational `apply_eligible` value), **or** an apply invocation that made the actual HTTP attempt (step 10) but the adapter's own outcome is a fully audited blocked state (`provider_response_too_large`, `provider_row_count_exceeded`, an `expected_latest_bar_date` mismatch, a malformed/non-JSON response, or any other existing `blocked_*` `refresh_state`). | Dry-run mode, after step 8, when step 5 did not short-circuit; or apply mode, step 10, on any blocked adapter outcome. |
| `2` | Any pre-HTTP refusal: parser (step 1), root/path (step 2), credential-path (step 3), `--as-of` (step 4), ledger lock (step 6), ledger corruption or attempt-budget exhaustion (step 7), live-capital interlock in apply mode (step 8), or credential absence (step 9). | Steps 1-4 and 6-9, apply or (for steps 1-5, 8) dry-run as applicable. |

Dry-run mode can only ever exit `0` (already-qualified) or `1` (pending) —
it never reaches step 6 onward, so it can never exit `2` on lock, ledger,
credential, or attempt-cap grounds, and (per finding #6) never exits `2` on
interlock grounds either. Only a malformed invocation (steps 1-4) makes
dry-run exit `2`.

## Planner Classification: `authorized_network_read_only`

Corrects the truthfulness gap the operator adjudication identified: leaving
`run_authorized_read_only_market_data_refresh_to_seed_soak` classified
`EXECUTION_OPERATOR_GATED` after this seam exists would mislabel standing,
already-granted authority as a genuine operator blocker, alongside actions
that are genuinely blocked pending operator review or host-health checks
(`operator_review_market_data_soak_evidence`,
`operator_check_scheduled_market_data_refresh_task_health`, etc., which
**keep** their `EXECUTION_OPERATOR_GATED` classification unchanged — this
correction is scoped to the one token that now has a real, seam-exercisable
execution path).

**Round-3 correction (finding #1, P0):** `autonomy_next_plan.py`'s existing
`ActionClass.__post_init__` unconditionally raises
`"only offline-runnable actions may carry a command"` whenever
`offline_runnable is False` and `command != ""`. Every table below still
requires `offline_runnable=False` and a non-empty `command` for the new
class — that combination cannot construct today. Commit B is authorized to
make exactly one, narrowly scoped change to that validation rule, not a
general relaxation: the `not self.offline_runnable and self.command != ""`
check becomes `not self.offline_runnable and self.command != "" and
self.execution_class != EXECUTION_AUTHORIZED_NETWORK_READ_ONLY`. Every other
non-offline-runnable class (`EXECUTION_OPERATOR_GATED`, `EXECUTION_NOOP`)
keeps rejecting a non-empty `command` exactly as today — the carve-out names
this one new class and no other. `ActionClass`'s class docstring must be
updated in the same commit so it no longer states unqualified that `command`
"is empty when no offline command exists" (see "Implementation Acceptance
Criteria" below, criterion 5, for the required test).

Commit B adds:

- A new execution class constant, `EXECUTION_AUTHORIZED_NETWORK_READ_ONLY =
  "authorized_network_read_only"`, added to `_EXECUTION_CLASSES` (so
  `ActionClass.__post_init__`'s membership check accepts it) but **not** to
  `_OFFLINE_RUNNABLE_CLASSES` (so `expected_runnable` for this class remains
  `False`), alongside the existing `EXECUTION_AUTO_OFFLINE`,
  `EXECUTION_OFFLINE_OPERATOR_INPUT`, `EXECUTION_OPERATOR_GATED`,
  `EXECUTION_NOOP` in `autonomy_next_plan.py`.
- `run_authorized_read_only_market_data_refresh_to_seed_soak` reclassified to
  this new class, with `offline_runnable=False` (unchanged — it must **not**
  become auto-offline-reachable), a non-empty gate value
  `network_market_data_fetch` (the existing `_GATE_NETWORK_MARKET_DATA`
  constant, unchanged — required because the class falls outside the
  `(EXECUTION_AUTO_OFFLINE, EXECUTION_NOOP)` gate-forbidding branch, so
  `ActionClass.__post_init__` already requires a non-empty gate here with no
  further change; this is now a *descriptive* boundary label on a
  standing-authority class rather than a genuine blocking gate, but the
  string itself is not renamed), `command` set to the exact frozen entry
  point named in "Execution Architecture"
  (`python -m algotrader.execution.autonomy_read_only_network_executor
  --as-of <ISO8601_UTC> [--apply] --format json`, permitted only by the
  narrow carve-out above), and `required_operator_inputs=()` — the CLI
  accepts no operator-supplied credential, path, symbol, or provider input,
  so there is nothing to list.
- `authorized_read_only_market_data_fetch_for_shadow_window` **stays**
  `EXECUTION_OPERATOR_GATED` — this contract does not build or authorize an
  execution seam for the shadow-window fetch; only the soak-seeding action
  gets a seam.
- A new, disjoint, one-entry allowlist, `AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST
  = {"run_authorized_read_only_market_data_refresh_to_seed_soak":
  <frozen argv/module reference>}`, separate from
  `AUTONOMY_EXECUTOR_ALLOWLIST`, checked only by the new seam module, never
  by `autonomy_offline_executor.py`.

Implementation Acceptance Criteria (commit B must add all five, mirroring the
two-way set-equality invariant pattern V5.48 already established for
`AUTONOMY_EXECUTOR_ALLOWLIST`/`EXECUTION_AUTO_OFFLINE`):

1. **Two-way closure**: every token classified
   `EXECUTION_AUTHORIZED_NETWORK_READ_ONLY` appears in
   `AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST`, and every
   `AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST` key is classified
   `EXECUTION_AUTHORIZED_NETWORK_READ_ONLY`.
2. **Disjointness**: `AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST`'s key set and
   `AUTONOMY_EXECUTOR_ALLOWLIST`'s key set are disjoint.
3. **No-false-auto-offline**: no token classified
   `EXECUTION_AUTHORIZED_NETWORK_READ_ONLY` has `offline_runnable=True`, is
   selected as `next_offline_action`, or causes `plan_class` to report
   `PLAN_OFFLINE_ACTION_AVAILABLE` — i.e., `EXECUTION_AUTHORIZED_NETWORK_READ_ONLY
   not in _OFFLINE_RUNNABLE_CLASSES`.
4. **Reverse reachability**: the one entry in
   `AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST` corresponds to a token that
   `classify_action` actually emits for `spy_market_data_soak`'s absent
   state today — the allowlist entry is not orphaned or stale.
5. **Command carve-out is narrow, not general**: a dedicated test
   constructs (or attempts to construct) an `ActionClass` for each of
   `EXECUTION_OPERATOR_GATED` and `EXECUTION_NOOP` with a non-empty
   `command` and asserts each still raises `ValidationError`; a companion
   test constructs an `ActionClass` with
   `execution_class=EXECUTION_AUTHORIZED_NETWORK_READ_ONLY`,
   `offline_runnable=False`, a non-empty `gate`, a non-empty `command`, and
   `required_operator_inputs=()`, and asserts it constructs successfully
   with no `ValidationError`.

## Windows Scheduled Task Update

Commit B updates the existing template,
`docs/design/spy_eod_market_data_refresh_scheduled_task.xml`, to invoke the
new seam instead of `scripts/refresh_spy_adjusted_data.ps1` directly, so that
the template's own `RestartOnFailure` retries (`Interval=PT15M`, `Count=3`)
are subject to the seam's four-attempt-per-session ledger cap rather than
bypassing it by re-running the adapter script with no shared attempt memory
between retries.

**Round-2 correction (finding #3, P1):** the prior text put
`<UTC timestamp resolved at trigger time>` directly in the `<Actions><Exec>`
command — prose, not an executable argument, and no mechanism was frozen to
resolve it. Commit B instead freezes a new, reviewed wrapper script,
`scripts/run_spy_read_only_network_executor.ps1`, checked into the
repository alongside `scripts/refresh_spy_adjusted_data.ps1`, and the
`<Actions><Exec>` command becomes an invocation of that exact wrapper with
no placeholder text in any executable field:

- The wrapper validates it is running from the canonical repository root
  (mirroring the seam's own root/cwd check) and refuses non-zero before
  invoking Python if it is not.
- It captures the current UTC instant **exactly once**, as
  `[DateTimeOffset]::UtcNow.ToUniversalTime().ToString('o',
  [CultureInfo]::InvariantCulture)`, into a local variable.
- It then invokes exactly `python -m
  algotrader.execution.autonomy_read_only_network_executor --as-of
  <captured value> --apply --format json`, using PowerShell's own
  call operator against the literal captured string — never
  `Get-Date`/`datetime.now` called a second time inside the Python process,
  and never any other timestamp source.
- It propagates the Python process's exit code as its own exit code
  unchanged (see "Exit Codes"), and reads and prints no credential value —
  it passes no credential-bearing argument or environment variable of its
  own; the Python process resolves the credential itself via the canonical
  `.env` file per "Freeze One Credential Source".
- The `<Actions><Exec>` command in
  `spy_eod_market_data_refresh_scheduled_task.xml` invokes this wrapper by
  its exact frozen path (e.g. `powershell.exe -File
  <canonical root>\scripts\run_spy_read_only_network_executor.ps1`),
  keeping the same `WorkingDirectory` (the canonical repository root) and
  the same `RestartOnFailure`/trigger/idle/battery settings unchanged.
- **Clarifying "in-process":** "in-process" (see "Execution Architecture")
  describes the Python executor module calling the adapter's
  `run_spy_adjusted_data_refresh` function directly in the same Python
  process — no adapter/network child process is spawned by the executor
  itself. It does not mean Task Scheduler is forbidden from launching a
  host-level process at all: Task Scheduler launching
  `run_spy_read_only_network_executor.ps1`, which in turn launches the
  `python -m ...` process, is the normal, permitted way an OS scheduler
  starts any command; the "no child process" guarantee is scoped to what
  the executor module itself spawns once running, which remains zero.

`scripts/refresh_spy_adjusted_data.ps1` remains in the repository, unchanged,
as a manual/diagnostic entry point an operator may still invoke by hand; it
is simply no longer the unattended scheduled path once commit B lands.
`scripts/run_spy_read_only_network_executor.ps1` is a new, minimal host
wrapper — it contains no fetch/normalize/credential logic of its own, only
canonical-root validation, one timestamp capture, and the Python
invocation.

## Naming: `live_market_data_fetch` Is Not A Live-Trading Flag

The mode value `live_market_data_fetch` (the PS1 `-Mode` parameter value,
the adapter CLI's `--mode` choice, `_LIVE_MARKET_DATA_FETCH`, and
`ETFAdjustedDataRefreshConfig.mode`) uses the word "live" to mean *fetch
the current, non-fixture provider data*, not *live trading* or
*live-capital activity*. That collision is real and worth resolving
truthfully rather than by silent behavior change:

- **This contract makes no rename.** `live_market_data_fetch` stays
  exactly as spelled in every existing script parameter, CLI choice,
  constant, test assertion, and operator-runbook example. A rename now
  would be an unreviewed behavior/compatibility change smuggled into this
  milestone.
- The **binding, permanent meaning** of `live_market_data_fetch` is fixed
  by this contract as: *perform the real (non-fixture, non-dry-run)
  read-only Tiingo HTTPS GET*. It is independently and separately
  distinguished from — and never a substitute for — `APP_PROFILE=live`,
  live-broker access, live order submission, or live-capital activity,
  every one of which the same adapter already rejects
  (`_live_market_data_fetch_preflight_blockers` refuses whenever
  `APP_PROFILE=live`, and the new seam additionally requires the full
  live-capital interlock to pass) and none of which this seam gains any new
  authority over.
- **Migration rule for any future rename**: if a later, separately
  reviewed milestone decides the name is confusing enough to change (for
  example to `network_market_data_fetch` or
  `read_only_market_data_fetch`, matching the planner's own
  `_GATE_NETWORK_MARKET_DATA` gate name already in use), it must (a) keep
  `live_market_data_fetch` accepted as a permanent backward-compatible
  alias in the `ValidateSet`/`choices` list rather than removing it
  outright, (b) update every test asserting the literal string, (c) leave
  `_LIVE_MARKET_DATA_FETCH`'s external string value unchanged (only a
  Python-side constant name may change, not the wire-visible mode string),
  and (d) be reviewed as its own frozen contract, not folded into an
  unrelated feature change. No such rename is authorized or started here.

## Read-Only Market-Data Is Not Live Trading

Restated because it is the single most important boundary this contract
protects: **the read-only network seam this contract defines may never
directly load, import, or invoke any broker/order/position-mutation
surface, and its own code may never directly touch a broker credential
field.** It has no path — outside the one named safety exception below — to
`alpaca_sdk_client`, `require_live_capital_interlock`, or any
submit/cancel/replace/close/liquidate function, directly or transitively.

**Round-2 correction (finding #1, P0):** the prior wording of this section
banned `AlpacaPaperConfig` and `require_paper_profile` outright from the
seam's transitive import closure. That is unsatisfiable, because the
*mandatory* preflight step this same contract requires —
`evaluate_live_capital_interlock` (see "Mandatory Live-Capital Interlock
Preflight") — itself imports and calls both: it constructs
`AlpacaPaperConfig.from_env(source)` and calls `require_paper_profile`
internally as its own defence-in-depth check. A test that forbade those two
names anywhere in the transitive closure would fail against the seam's own
required dependency, not against a defect. The rule is corrected to be about
**reachability**, not raw name-presence:

- The seam module's own code (`autonomy_read_only_network_executor.py`)
  never imports `AlpacaPaperConfig` or `require_paper_profile` **directly**,
  never constructs an `AlpacaPaperConfig`, and never reads an
  `alpaca_api_key`/`alpaca_secret_key`-shaped field from any object it
  holds. Its only broker-adjacent import is `evaluate_live_capital_interlock`
  itself.
- `AlpacaPaperConfig`, `require_paper_profile`, and the `algotrader.config`
  validation helpers they depend on (e.g. `ConfigValidationError`,
  `_clean_optional`) are permitted **only** as part of
  `evaluate_live_capital_interlock`'s own transitive closure — i.e., reached
  through `algotrader.execution.live_capital_interlock` and no other path.
  This is the seam's one named, mandatory safety exception, not a general
  license to import broker configuration.
- `require_live_capital_interlock` (the *stricter*, order-adjacent sibling
  of `evaluate_live_capital_interlock` used by actual paper-broker mutation
  paths) remains fully forbidden, directly or transitively, exactly as
  before — the seam uses only the evaluating, non-raising verdict function,
  never the requiring/raising one.
- `alpaca`, `alpaca_trade_api`, and any submit/cancel/replace/close/
  liquidate-named callable remain fully forbidden, directly or transitively,
  through every path, including through `live_capital_interlock` — that
  module itself imports no broker SDK either, so this exclusion is not
  weakened by permitting the safety closure.

**Round-3 correction (finding #4, P1):** the prior wording of bullet 2 below
claimed a test that "walks the import graph and asserts every module path
reaching [`AlpacaPaperConfig`/`require_paper_profile`] passes through
`live_capital_interlock`" — a generic, whole-repository transitive-closure
reachability prover. No such mechanism exists in this codebase today.
`test_dependency_direction.py`'s `DependencyRule`/`_dependency_violations`
(the only import-checking helper this repository has) is a **flat, per-file,
single-hop scan**: for each file in a fixed, caller-supplied path list, it
parses that one file's own `ast.Import`/`ast.ImportFrom` statements and
checks each against a forbidden-prefix list — it never follows an import to
another file, so it cannot by itself prove a repository-wide "every path
passes through node Y" property across multiple files. A test claiming that
generic guarantee could not be written against any existing helper, and
writing a new whole-repository import-graph walker was never authorized by
this contract and is out of scope for a read-only market-data seam.

The corrected rule replaces the generic graph-reachability claim with
implementable AST rules over an **explicit, hand-curated closure** — a fixed,
enumerated list of files, verified against the current source at review
time, not discovered by a graph search at test time:

- `src/algotrader/execution/autonomy_read_only_network_executor.py` (the new
  seam module),
- `src/algotrader/execution/etf_sma_adjusted_spy_data_refresh.py` (the
  adapter — confirmed today to import only `algotrader.errors` and
  `algotrader.execution.etf_sma_market_data_soak`),
- `src/algotrader/execution/etf_sma_market_data_soak.py` (the adapter's own
  soak-report dependency — confirmed today to import only
  `algotrader.errors` and `algotrader.execution.exchange_session`),
- `src/algotrader/execution/exchange_session.py` (confirmed today to import
  only `algotrader.errors` and stdlib),
- `src/algotrader/errors.py` (confirmed today to have no imports),
- `src/algotrader/execution/live_capital_interlock.py` (the safety
  interlock — confirmed today to import `algotrader.config` and
  `algotrader.errors`),
- `src/algotrader/config.py` (confirmed today to import only stdlib —
  reached exclusively through `live_capital_interlock`, never directly by
  the seam or the adapter).

A new import-purity test for `autonomy_read_only_network_executor.py`,
modeled on `test_dependency_direction.py`'s existing
`DependencyRule`/`_dependency_violations` flat-scan mechanism (the same one
`test_crypto_read_only_paper_observation_adapter_does_not_import_downstream_layers`
already uses for a comparably-scoped adapter), must assert, by static
per-file AST inspection, not by inspecting default-argument or runtime
behavior:

1. **Direct-import scope** (flat scan of the seam module's own file only):
   the seam module's `ast.Import`/`ast.ImportFrom` statements name only
   `algotrader.execution.etf_sma_adjusted_spy_data_refresh` (the adapter),
   `algotrader.execution.live_capital_interlock` (the safety closure), and
   `algotrader.execution.exchange_session` (the NYSE session calendar —
   **round-6 amendment**, see below) among internal
   `algotrader.execution`/`algotrader.config`/broker-prefixed
   modules — proving the "three direct imports" claim in "Execution
   Architecture" by inspection of one file, using the existing
   `DependencyRule` forbidden-prefix mechanism with every other
   `algotrader.execution.*`, `algotrader.config`, `alpaca`, and
   `alpaca_trade_api` name forbidden.

   **Round-6 amendment (independent review finding F1).** As originally frozen
   this rule named two modules, and the implementation imported a third,
   `algotrader.execution.exchange_session`. Independent review found the
   deviation and, worse, found that `test_dependency_direction.py` had been
   broadened to admit it — converting a contract violation into a passing
   suite. The resolution is to amend this rule rather than to reshape the code,
   for one reason: **the two-module rule was not carrying the safety weight it
   appeared to.** The stated safety property is that the seam's closure holds
   no broker SDK, client, order, position, or mutation surface, and that is
   proved by the closure purity check across all seven files — not by counting
   the seam's own imports. `exchange_session` was already inside that
   purity-checked closure and had been since the adapter began importing it in
   `9ba2925`, long before this milestone; the seam's direct import therefore
   widens the blast radius by exactly nothing. Resolving the finding the other
   way would have meant moving this contract's own "Deterministic
   Expected-Session Semantics" (the 20:10 ET cutoff) into an adapter shared by
   four unrelated modules, growing a public surface this contract elsewhere
   requires be "reused unchanged" — paying a real architectural cost to satisfy
   a proxy for a property the closure check already proves directly.

   This amendment is **narrow and exhaustive**: exactly three named modules, not
   a category. It does not license any further `algotrader.execution.*` import,
   and it does not relax rules 2–5 below. Per operator instruction it carries
   the same independent-review requirement as any implementation change.

   **Binding on the test:** `allowed_internal_modules` in
   `test_dependency_direction.py` must mirror this list exactly and may never
   again be widened to match an implementation. Widening the test instead of
   correcting the code, or amending this rule, is the specific failure that
   produced F1.
2. **No direct config or secret identifiers** (flat scan of the seam module's
   own file): the seam module's own AST names neither `AlpacaPaperConfig`
   nor `require_paper_profile` anywhere in its own `ast.ImportFrom`
   statements or attribute/name references, and never constructs an
   `AlpacaPaperConfig` or reads an `alpaca_api_key`/`alpaca_secret_key`-shaped
   attribute.
3. **Adapter has no config or broker import** (flat scan of two files:
   `etf_sma_adjusted_spy_data_refresh.py` and `etf_sma_market_data_soak.py`):
   neither file's `ast.Import`/`ast.ImportFrom` statements name
   `algotrader.config`, `alpaca`, `alpaca_trade_api`, or any
   `algotrader.execution.broker_base`/`alpaca_*`-prefixed module (existing
   `DependencyRule` forbidden-prefix mechanism, applied to this two-file
   path list).
4. **`live_capital_interlock` is the sole permitted importer of
   `AlpacaPaperConfig`/`require_paper_profile`** within the seven-file
   hand-curated closure above: a per-file existence/absence check (not a
   graph search) asserts that `live_capital_interlock.py`'s own
   `ast.ImportFrom` statements *do* name both `AlpacaPaperConfig` and
   `require_paper_profile` from `algotrader.config`, and that none of the
   other six files in the closure names either identifier anywhere in their
   own AST.
5. **SDK client/order/mutation exclusion, flat scan across the whole
   closure**: using the existing `DependencyRule`/`_dependency_violations`
   mechanism against all seven closure files at once, none of `alpaca`,
   `alpaca_trade_api`, `require_live_capital_interlock`, or any
   submit/cancel/replace/close/liquidate-named callable is imported by any
   file in the closure — with **no exception**, including
   `live_capital_interlock.py` itself (confirmed today to import no broker
   SDK).

Because every file in the closure is named explicitly and its current
import set has been read and recorded above, this test is exact and
implementable against `_dependency_violations`/`DependencyRule` as they
exist today, with no new generic graph-walking helper required. If a future
change to any of these seven files' own imports changes this closure's
membership, that change is itself a review-visible diff to a
contract-enumerated file list, not a silent gap the test could miss.

Live capital remains operator-gated until burn-in completes; nothing in
this contract touches that gate, and this correction grants the seam no new
capability — it only replaces an unwritable generic test claim with a
precise, hand-curated one that proves the same safety property against the
actual, current source.

## Explicit Non-Goal: `spy_offline_daily_cycle` Consumption

This contract stops at seeding `spy_market_data_soak` evidence — i.e., at
successfully writing an accepted refresh manifest and advancing the soak
ledger/report. It explicitly does **not**:

- wire the refreshed canonical CSV into
  `etf-sma-offline-daily-cycle-run --daily-bars-csv`;
- change `spy_offline_daily_cycle`'s `LaneSpec` in any way;
- claim or imply that five qualifying soak sessions make the daily-cycle
  lane's operator-supplied-CSV requirement go away.

Consuming the refreshed data to feed the daily-cycle lane is a **separate,
subsequent milestone** requiring its own frozen contract and independent
review, exactly as `docs/design/v5_50_offline_autonomy_lane_eligibility_analysis.md`
already flagged ("the only route that broadens autonomy over existing
lanes... needs its own frozen contract and an undivided review pass"). This
contract does not start that milestone and grants it no authority.

## What This Contract Does Not Do

- It does not implement, execute, or test anything by itself. No `src/` or
  `tests/` file changes in this document's own commit; implementation is
  authorized only by acceptance plus the two-commit milestone it opens.
- It does not perform a network call, load `TIINGO_API_KEY`, or read any
  credential.
- It does not touch `AUTONOMY_EXECUTOR_ALLOWLIST` or
  `autonomy_offline_executor.py`.
- It does not authorize a rename of `live_market_data_fetch` or any other
  existing flag/constant.
- It does not authorize wiring `spy_offline_daily_cycle` to consume this
  data.
- It does not weaken, bypass, or relax the existing adapter's HTTPS
  destination/method/query allowlist, symbol scope, or
  `APP_PROFILE=live` rejection, or any part of the live-capital interlock.

## Correction To V5.50

`docs/design/v5_50_offline_autonomy_lane_eligibility_analysis.md`'s
lane-by-lane input-self-containment finding is unchanged and correct: no
*offline* lane besides the crypto readiness replay is eligible for
`EXECUTION_AUTO_OFFLINE`, and that remains true after this contract —
this contract adds a distinct *network* seam under a distinct execution
class (`EXECUTION_AUTHORIZED_NETWORK_READ_ONLY`), not a new offline-auto
entry. What was stale in that document is its framing of the market-data
track as a pending operator decision among three options; the operator has
since selected option 2, so that document's "Options"/"Next Action" sections
are corrected in place to record the selection and point to this contract,
without altering the eligibility analysis itself.

## Next Action

Independent **round-4** review of this corrected contract. If round-4
accepts, it authorizes exactly one implementation milestone/PR with the two
ordered commits defined in "Implementation Milestone Shape" — no second
contract is required to land them. If round-4 again requests changes, the
findings must be corrected and recorded here exactly as round-1's, round-2's,
and round-3's were, before a further review round. No implementation is
authorized until an independent round accepts this contract.
