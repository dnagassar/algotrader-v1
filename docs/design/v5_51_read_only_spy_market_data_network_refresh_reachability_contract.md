# V5.51 Read-Only SPY Market-Data Network Refresh Reachability Contract

## Status

- Status: **round-1 REQUEST CHANGES corrected in place; pending independent
  round-2 review.** Round-1 findings and the corrections applied are recorded
  in "Round-1 Independent Review: Findings And Corrections" below.
- Still **no `src/` or `tests/` file has been changed by this contract
  document.** What changed this round is the contract's own precision: every
  place round-1 found ambiguous, self-contradictory, or merely illustrative
  ("e.g.", "an implementation choice") is now frozen to one exact, checkable
  rule.
- Base commit for this correction: `6797e95` (the originally frozen V5.51
  contract). Original base commit: `b79c721` (V5.50 lane eligibility analysis
  recorded).
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
  Without the explicit `--apply` switch it resolves what *would* run and
  performs no HTTP request, no credential lookup, and no runtime artifact
  write beyond one dry-run ledger record.
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
- Alpaca/broker **credential secret values** are not read, forwarded, or
  required by this seam — the adapter never looks them up. That is
  unchanged. What round-1 correctly flagged as contradictory is now fixed:
  the live-capital interlock (`evaluate_live_capital_interlock`), which
  inspects environment **shape** (profile string, endpoint classification,
  live-enable flags, live-host markers) rather than any credential secret,
  is a **mandatory** preflight step, not an excluded one (see "Mandatory
  Live-Capital Interlock Preflight"). Because the seam runs in-process
  (Execution Architecture), there is no child process/child-environment to
  isolate; the applicable defence-in-depth guarantee instead is a **static
  import-closure** test proving the seam module's transitive imports contain
  no broker SDK/client/order/position-mutation surface (see "Read-Only
  Market-Data Is Not Live Trading").
- The seam performs and exposes no submit/cancel/replace/close/liquidation/
  paper-mutation/capital/live action. Every ledger record fixes
  `broker_access_attempted`, `broker_mutation_performed`,
  `paper_submit_performed`, `live_trading_performed`, and `live_authorized`
  to `false`, with `profit_claim=none`. Unlike the offline executor's
  ledger (which fixes `network_access_attempted=false` truthfully, because
  it never touches the network), this seam's ledger must record
  `network_access_attempted` **truthfully as `true`** whenever the single
  authorized HTTP GET is actually attempted, and `false` for a dry run, a
  preflight refusal, or the session-already-qualified short-circuit. A
  ledger that hardcoded `false` here would be lying about the one thing this
  seam exists to do.

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
  `run_authorized_read_only_market_data_refresh_to_seed_soak`, the two-way
  closure/disjointness/no-false-auto-offline/reverse-reachability tests (see
  "Planner Classification"), the static import-closure purity test, and the
  Windows Task Scheduler template update (see "Windows Scheduled Task
  Update"). This commit depends on commit A's caps and must not land ahead
  of it.

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
  `algotrader.execution.etf_sma_adjusted_spy_data_refresh` (the adapter) and
  `algotrader.execution.live_capital_interlock` (the safety interlock). Its
  static transitive import closure must contain no broker SDK, broker
  client, order, position, or mutation-surface module — the same
  import-purity discipline `test_dependency_direction.py` already applies to
  the crypto-readiness-replay launcher, applied here as a new test.
- **Dry-run vs. apply.** Without `--apply`, the module performs **zero**
  credential lookup, **zero** HTTP request, and **zero** runtime artifact
  write beyond one dry-run ledger record; it may still evaluate and report
  the sanitized live-capital interlock verdict and the session/attempt-budget
  state, because both are pure environment/local-file reads with no
  credential or network involvement. With `--apply`, it additionally
  performs the credential-presence check and, if every preflight passes, the
  single authorized HTTP GET.
- **Deterministic IDs, not caller-supplied ones.** The module accepts no
  `--run-id`, `--session-id`, or path override. It derives, deterministically
  from `--as-of` and the seam's own ledger state, exactly:
  - `session_id`: the resolved NYSE session date (`YYYY-MM-DD`) that
    `--as-of` maps to under the 20:10 ET provider-publication cutoff (see
    "Deterministic Expected-Session Semantics").
  - `attempt_number`: one plus the count of prior ledger records for that
    exact `session_id` whose `network_access_attempted` field is `true`
    (i.e., prior records where the seam actually reached the point of
    issuing, or attempting to issue, the HTTP GET). Refusals and
    short-circuits do not increment it.
  - `run_id`: the fixed string `f"network-{session_id}-{attempt_number}"`.
  No caller input can substitute any of these three values.
- **One canonical, append-only ledger path**, frozen exactly:
  `runs/autonomy_network_executor/ledger.jsonl`. Unlike the offline
  executor's single-record-replace ledger, this ledger is **append-only**
  (new JSONL lines are added, never truncated or rewritten), because the
  session attempt-budget check requires reading the full prior history for a
  `session_id` across invocations. If the file exists but contains any
  malformed line, or a required read fails for a reason other than the file
  cleanly not existing, the seam refuses closed with
  `ledger_state_corrupt` rather than assuming zero prior attempts — a
  missing file is not itself corruption (it is the legitimate state before
  the first-ever invocation), but an unreadable or partially-parseable file
  is treated as an untrustworthy attempt count and must never be silently
  treated as empty.
- Root/cwd validation for this module mirrors
  `autonomy_next_plan.py`'s/`autonomy_offline_executor.py`'s canonical-root
  binding: the module refuses (`noncanonical_target`) unless the resolved
  executing root, cwd, and every one of the seven canonical paths (the six
  adapter destination paths below plus the ledger path above) resolve
  exactly as fixed here, with no symlink escape.

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

`token_lookup` is `lambda name: load_tiingo_api_key_from_dotenv(<resolved
canonical .env path>, token_env_var=name)` (see "Freeze One Credential
Source"). `http_get` is the adapter's existing internal Tiingo HTTP GET
function, passed through unchanged — the seam does not reimplement it.

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
| Authorized GET attempts per resolved NYSE session | new, seam-level, corrects round-1 finding #3 | at most **4** authorized attempts (one initial plus three retries) per `session_id`, enforced fail-closed by the seam's own canonical append-only ledger (`runs/autonomy_network_executor/ledger.jsonl`) **before** credential access or HTTP on every apply invocation. This exactly matches the existing Windows Task Scheduler template's `RestartOnFailure` policy (`Interval=PT15M`, `Count=3` — one initial run plus three restarts). The seam itself performs **no internal retry, loop, or sleep**; the four-attempt budget is spent across *separate invocations* (typically the scheduler's own restarts), never within one process's execution. |

Commit A must add the two gap rows to `etf_sma_adjusted_spy_data_refresh.py`
as part of the single implementation milestone this contract authorizes on
acceptance (see "Implementation Milestone Shape"); no second contract is
required.

### Session Attempt Budget

On every `--apply` invocation, after resolving `session_id` (and after the
session-already-qualified short-circuit — see "Retry And Idempotency
Behavior" — has been checked and found not to apply), the seam reads
`runs/autonomy_network_executor/ledger.jsonl` and counts prior records for
that exact `session_id` with `network_access_attempted=true`.

- If that count is `>= 4`, the seam refuses closed with
  `session_attempt_budget_exhausted`, writes one ledger record with
  `network_access_attempted=false`, and exits `2`. It performs no credential
  lookup and no HTTP call.
- If that count is `< 4`, the seam proceeds to the live-capital interlock and
  (if that passes) the credential-presence check and the single HTTP GET,
  recording `attempt_number = count + 1` and `network_access_attempted=true`
  in the resulting ledger record regardless of whether the HTTP GET itself
  ultimately succeeds — reaching the network is what the budget counts, not
  provider success.
- Once a session's soak evidence shows `latest_session_qualified=true`, later
  invocations for that same session no-op **before** the attempt-budget read
  and before credential access, via the session-already-qualified
  short-circuit (unchanged mechanism from the original freeze, now
  explicitly ordered ahead of the attempt-budget check).

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
  usage: if the soak report already shows `latest_session_qualified=true`
  for the session `--as-of` resolves to, the seam short-circuits to a no-op
  (`skipped_session_already_qualified`) **before** the attempt-budget check
  and **before** the live-capital interlock or credential check, performing
  zero HTTP requests. This is a network budget guard, not a correctness
  requirement — the soak layer would already record a same-session retry
  safely even without it.

## Mandatory Live-Capital Interlock Preflight

Corrects round-1 finding #1 (P0). The seam calls
`evaluate_live_capital_interlock(os.environ)`
(`algotrader.execution.live_capital_interlock`) as a **mandatory** preflight
step, in both dry-run and apply modes, before any credential access or HTTP
call. This is a pure environment-shape safety check — it reads `APP_PROFILE`,
the configured Alpaca base URL, and a fixed set of live-enable/live-host
environment variable *names*, and returns a sanitized verdict; it never reads
a credential secret and performs no order, mutation, or network action of its
own. It is not a forbidden broker surface, and the original contract's
framing that implied Alpaca/broker considerations were entirely out of scope
here was the defect; that framing is removed.

- The seam requires `verdict.paper_boundary_ok is True`: `APP_PROFILE` equal
  to the paper profile, the resolved Alpaca base URL classified as a paper
  endpoint, and no detected live-enable flag or live-host marker.
- If `paper_boundary_ok` is `False`, the seam refuses
  (`live_capital_interlock_blocked`) in both dry-run and apply mode, and
  records the verdict's own sanitized `to_dict()` output — booleans and
  blocker/variable **names** only, exactly as
  `LiveCapitalInterlockVerdict.to_dict()` already produces, never a
  credential or URL value — in the ledger record.
- On a passing verdict, dry-run mode may report the sanitized verdict as
  informational "interlock readiness" but still performs no credential
  lookup. Apply mode proceeds to the credential-presence check only after
  the verdict passes.
- This check subsumes and replaces the original contract's narrower
  `APP_PROFILE=live present -> refuse` bullet, which is now a strict subset
  of what `paper_boundary_ok` already requires.

## Freeze One Credential Source

Corrects round-1 finding #2 (P1). Exactly one credential source is frozen:
the canonical repository-root `.env` file, read through the adapter's
existing, unchanged `load_tiingo_api_key_from_dotenv` function.

- The canonical `.env` path is resolved once, from the same validated
  canonical repository root used for every other path check in this
  contract: `Path(<canonical root>, ".env").resolve()`. The resolved path's
  parent must equal the resolved canonical root exactly, with no symlink
  escape; a mismatch is a refusal (`credential_path_noncanonical`), distinct
  from the six adapter-destination-path `noncanonical_target` refusal, so a
  reviewer can tell the two apart in a ledger record.
- **Presence** is determined by calling
  `load_tiingo_api_key_from_dotenv(<resolved canonical .env path>,
  token_env_var="TIINGO_API_KEY")` on the apply path only (never on dry-run,
  per "Execution Architecture") and checking whether the result is `None`.
  If it is `None` (file absent, or present without a `TIINGO_API_KEY` entry),
  the seam refuses (`token_not_available`) and records only that boolean —
  never the file's contents or any other variable it might contain.
- **Process-environment `TIINGO_API_KEY` values are ignored by this command
  entirely.** The seam never reads `os.environ["TIINGO_API_KEY"]` for any
  purpose, preflight or otherwise. This removes the process-environment
  presence check round-1 flagged as contradicting the dotenv-sourced fetch.
- On a successful apply, the adapter reads the credential value exactly once,
  after every other preflight (root/path/action/interlock/attempt-cap) has
  passed, via the same `load_tiingo_api_key_from_dotenv` call passed through
  as `token_lookup`, and passes it only to the adapter's existing exact
  Tiingo `Authorization: Token <value>` header boundary (`_tiingo_http_get`'s
  existing header-scope validation). The seam's own ledger, argv, stdout,
  stderr, artifacts, and any handoff document receive only the boolean
  presence/outcome, never the raw value — unchanged from the original
  freeze, now grounded in one unambiguous source.

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

The seam's own execution ledger is new: one JSONL record appended per
invocation to the frozen canonical path
`runs/autonomy_network_executor/ledger.jsonl` (see "Execution Architecture").
Corrects round-1 finding #8 by naming the exact fields rather than leaving
them to implementation judgment. Each record contains exactly:

- `record_type`: fixed constant identifying this ledger's schema.
- `action_token`: fixed constant
  `"run_authorized_read_only_market_data_refresh_to_seed_soak"`.
- `run_id`, `session_id`, `attempt_number` (see "Execution Architecture").
- `as_of`: the caller-supplied `--as-of` echoed back verbatim.
- `apply`: boolean, whether `--apply` was passed.
- `network_access_attempted`: boolean, truthful per "Non-Negotiable Safety
  Contract" above.
- `session_already_qualified`: boolean.
- `attempt_budget_exhausted`: boolean.
- `interlock_verdict`: the sanitized `LiveCapitalInterlockVerdict.to_dict()`
  output (or `null` if not evaluated — it always is evaluated per "Mandatory
  Live-Capital Interlock Preflight", so this is expected to always be
  populated).
- `credential_present`: boolean or `null` (only populated on an apply
  invocation that reached the credential check; never a value).
- `refusal_category`: one of the named sanitized categories in "Fail-Closed
  Refusal Conditions", or `null` on success.
- `exit_code`: integer.
- `adapter_refresh_state`: the adapter's own `refresh_state` string, when the
  adapter was invoked.
- `broker_access_attempted`, `broker_mutation_performed`,
  `paper_submit_performed`, `live_trading_performed`, `live_authorized`: all
  fixed `false`.
- `profit_claim`: fixed `"none"`.

Never included: the token value, any raw response body, any row-level
market-data, or any Alpaca/broker credential value.

## Fail-Closed Refusal Conditions

Checks run in this fixed order; the first failing check determines the
refusal category and terminates the invocation before any later check runs:

1. Argument parsing: any argument other than `--as-of`, `--apply`, `--format`
   is a parser-level refusal, exit `2`.
2. Canonical root/cwd/path validation across all seven canonical paths (six
   adapter destination paths plus the ledger path) → `noncanonical_target`.
3. Canonical `.env` path resolution (see "Freeze One Credential Source") →
   `credential_path_noncanonical`.
4. `--as-of` missing, not UTC, or not resolvable to a valid NYSE session
   under the 20:10 ET cutoff rule → `as_of_invalid`.
5. Session-already-qualified short-circuit (not itself an error; exits `0`
   with `network_access_attempted=false` if the resolved session already
   qualifies).
6. Session attempt-budget check (apply only; see "Session Attempt Budget") →
   `session_attempt_budget_exhausted`.
7. Live-capital interlock (dry-run and apply; see "Mandatory Live-Capital
   Interlock Preflight") → `live_capital_interlock_blocked`.
8. Credential presence via the canonical `.env` (apply only; see "Freeze One
   Credential Source") → `token_not_available`.
9. The adapter's own internal preflight and fetch/normalize path, unchanged
   (`_live_market_data_fetch_preflight_blockers`, response-byte cap, row
   cap, revision-lookback enforcement, etc.).

Any refusal from steps 1-8 is exit code `2` (input/precondition refusal,
consistent with the existing planner/executor/replay exit-code convention),
records zero network access, and never performs a partial or best-effort
fetch. `symbol_scope_violation` and an explicit-`--profile`-style override
are no longer separately reachable refusal paths, because the frozen CLI (see
"Execution Architecture") has no symbol or profile argument to violate or
override in the first place; both remain as defence-in-depth internal
assertions.

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

Commit B adds:

- A new execution class constant, `EXECUTION_AUTHORIZED_NETWORK_READ_ONLY =
  "authorized_network_read_only"`, alongside the existing
  `EXECUTION_AUTO_OFFLINE`, `EXECUTION_OFFLINE_OPERATOR_INPUT`,
  `EXECUTION_OPERATOR_GATED`, `EXECUTION_NOOP` in
  `autonomy_next_plan.py`.
- `run_authorized_read_only_market_data_refresh_to_seed_soak` reclassified to
  this new class, with `offline_runnable=False` (unchanged — it must **not**
  become auto-offline-reachable), network boundary/gate value
  `network_market_data_fetch` (the existing `_GATE_NETWORK_MARKET_DATA`
  constant, unchanged — this is now a *descriptive* boundary label on a
  standing-authority class rather than a genuine blocking gate, but the
  string itself is not renamed), `command` set to the exact frozen entry
  point named in "Execution Architecture"
  (`python -m algotrader.execution.autonomy_read_only_network_executor
  --as-of <ISO8601_UTC> [--apply] --format json`), and
  `required_operator_inputs=()` — the CLI accepts no operator-supplied
  credential, path, symbol, or provider input, so there is nothing to list.
- `authorized_read_only_market_data_fetch_for_shadow_window` **stays**
  `EXECUTION_OPERATOR_GATED` — this contract does not build or authorize an
  execution seam for the shadow-window fetch; only the soak-seeding action
  gets a seam.
- A new, disjoint, one-entry allowlist, `AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST
  = {"run_authorized_read_only_market_data_refresh_to_seed_soak":
  <frozen argv/module reference>}`, separate from
  `AUTONOMY_EXECUTOR_ALLOWLIST`, checked only by the new seam module, never
  by `autonomy_offline_executor.py`.
- `EXECUTION_AUTHORIZED_NETWORK_READ_ONLY` is added to
  `_OFFLINE_RUNNABLE_CLASSES`'s complement, not to `_OFFLINE_RUNNABLE_CLASSES`
  itself — it must never be selected by `next_offline_action` or contribute
  to `plan_class == PLAN_OFFLINE_ACTION_AVAILABLE`.

Implementation acceptance criteria (commit B must add all four, mirroring the
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
   `PLAN_OFFLINE_ACTION_AVAILABLE`.
4. **Reverse reachability**: the one entry in
   `AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST` corresponds to a token that
   `classify_action` actually emits for `spy_market_data_soak`'s absent
   state today — the allowlist entry is not orphaned or stale.

## Windows Scheduled Task Update

Commit B updates the existing template,
`docs/design/spy_eod_market_data_refresh_scheduled_task.xml`, to invoke the
new seam instead of `scripts/refresh_spy_adjusted_data.ps1` directly, so that
the template's own `RestartOnFailure` retries (`Interval=PT15M`, `Count=3`)
are subject to the seam's four-attempt-per-session ledger cap rather than
bypassing it by re-running the adapter script with no shared attempt memory
between retries. The `<Actions><Exec>` command becomes an invocation of
`python -m algotrader.execution.autonomy_read_only_network_executor --as-of
<UTC timestamp resolved at trigger time> --apply --format json`, keeping the
same `WorkingDirectory` (the canonical repository root) and the same
`RestartOnFailure`/trigger/idle/battery settings unchanged.
`scripts/refresh_spy_adjusted_data.ps1` remains in the repository, unchanged,
as a manual/diagnostic entry point an operator may still invoke by hand; it
is simply no longer the unattended scheduled path once commit B lands.

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
load, import, or invoke any broker/order/position-mutation surface.** It
has no path to `alpaca_sdk_client`, `AlpacaPaperConfig`,
`require_paper_profile`, `require_live_capital_interlock`, or any
submit/cancel/replace/close/liquidate function, directly or transitively. It
*does* import `evaluate_live_capital_interlock` — a pure, read-only safety
check that itself imports no broker SDK and performs no order or mutation —
which is a permitted, indeed mandatory, exception to the "no broker-adjacent
import" rule precisely because it is the safety gate, not a capability.

A new import-purity test for
`autonomy_read_only_network_executor.py`, modeled on
`test_dependency_direction.py`'s existing crypto-readiness-replay launcher
scan, must prove this by static import-graph inspection, not by inspecting
default-argument behavior (the same distinction V5.45's audit drew when it
rejected `crypto-readiness-verify` for the offline executor on import-surface
grounds, not runtime-behavior grounds). The test must assert the module's
transitive closure contains none of: `alpaca`, `alpaca_trade_api`, any
submit/cancel/replace/close/liquidate-named callable, `AlpacaPaperConfig`,
`require_paper_profile`, or `require_live_capital_interlock` — while
explicitly allowing `evaluate_live_capital_interlock` and the adapter module
itself. Live capital remains operator-gated until burn-in completes; nothing
in this contract touches that gate.

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

Independent **round-2** review of this corrected contract. If round-2
accepts, it authorizes exactly one implementation milestone/PR with the two
ordered commits defined in "Implementation Milestone Shape" — no second
contract is required to land them. If round-2 again requests changes, the
findings must be corrected and recorded here exactly as round-1's were,
before a further review round.
