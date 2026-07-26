# V5.51 Read-Only SPY Market-Data Network Refresh Reachability Contract

## Status

- Status: **frozen contract, no implementation authorized by this document.**
- This is a **contract-only milestone**. It changes no `src/` or `tests/`
  file. It defines the smallest high-leverage implementation slice that a
  later, separately reviewed milestone may build.
- Base commit: `b79c721` (V5.50 lane eligibility analysis recorded).
- Operator authorization: the operator selected **option 2** from
  `docs/design/v5_50_offline_autonomy_lane_eligibility_analysis.md` —
  authorize the read-only market-data intake path. Current `AGENTS.md`
  gives every collaborator standing authority to cause approved adapters
  to perform paper-only network operations through repository safety
  boundaries; freezing this contract is documentation work, not a network
  or broker operation, so it requires no separate operator gate. Executing
  a real fetch under the eventual implementation remains bounded by the
  caps this contract defines, not by a fresh per-operation approval.
- Not live-trading, not broker-mutating, not paper-order authority. This
  document authorizes no network call, no credential load, and no code
  change. `docs/design/v5_50_offline_autonomy_lane_eligibility_analysis.md`
  is corrected alongside this contract (see "Correction To V5.50" below);
  its input-self-containment finding is preserved unchanged.

## Problem Statement

The V5.37/V5.38/V5.39 supervisor/planner/executor stack classifies
`spy_market_data_soak`'s absent-state action,
`run_authorized_read_only_market_data_refresh_to_seed_soak`, as
`EXECUTION_OPERATOR_GATED` with gate `network_market_data_fetch`
(`autonomy_next_plan.py:347-351`). That classification is correct and
**this contract does not change it**: seeding the soak is, and remains, a
network operation outside the strictly offline executor's envelope.

What is missing is not authority — the operator has now granted it for
this exact narrow path — but a **safety-bounded, auditable execution
seam** for exercising it. Today the only ways to run the read-only Tiingo
refresh are: (a) an operator typing the exact `scripts/refresh_spy_adjusted_data.ps1`
invocation by hand, or (b) the pre-existing, reviewer-inspectable Windows
Task Scheduler template
(`docs/design/spy_eod_market_data_refresh_scheduled_task.xml`) at the host
level, outside any repository-owned execution ledger. Neither is wrong,
but neither produces the same kind of frozen, allowlisted,
preflight-gated, ledger-recording seam that `autonomy_offline_executor.py`
gives the crypto readiness replay. This contract freezes that seam for the
read-only network case, **structurally disjoint** from the offline
executor, so the market-data track can be advanced without touching or
weakening the network-free offline invariant V5.39/V5.45/V5.48 built.

## Non-Negotiable Safety Contract

- The new execution seam is a **distinct module**, never a code path
  inside `autonomy_offline_executor.py`, and it is never imported by
  `autonomy_offline_executor.py`, `autonomy_self_refresh_cycle.py`, or any
  caller of `AUTONOMY_EXECUTOR_ALLOWLIST`. The offline executor's own
  docstring guarantee ("verified to import no network ... surface") must
  remain true of every module reachable from it; the new seam is
  reachable only as an independent, directly-invoked sibling command.
- `AUTONOMY_EXECUTOR_ALLOWLIST` is untouched: it still contains exactly the
  two crypto readiness tokens mapped to `CANONICAL_REPLAY_ARGV`. The new
  seam defines its **own**, separately named allowlist
  (`AUTONOMY_NETWORK_EXECUTOR_ALLOWLIST`, one entry) that must never be
  merged into, imported by, or checked against
  `AUTONOMY_EXECUTOR_ALLOWLIST`. A dedicated test must assert the two
  allowlists' key sets are disjoint.
- The V5.37/V5.38 supervisor and planner classification of
  `run_authorized_read_only_market_data_refresh_to_seed_soak` is
  **unchanged** by this contract: it stays `EXECUTION_OPERATOR_GATED`,
  gate `network_market_data_fetch`, `offline_runnable=False`. The new
  seam is not surfaced through `autonomy-next-plan`'s `next_offline_action`
  or `plan_class` rollup, and it must never cause either to report this
  lane as auto-offline-reachable. The supervisor/planner continue to
  truthfully report "operator/network authority required"; the new seam
  is the mechanism by which that already-standing authority is exercised
  on demand, not a reclassification. A false-green regression here (the
  plan silently claiming this lane needs no operator/network authority)
  would repeat the exact defect class V5.37a/V5.38a/V5.42a repaired and is
  the single most important invariant this contract protects.
- The seam reuses the **existing** Tiingo adjusted-bars adapter
  (`src/algotrader/execution/etf_sma_adjusted_spy_data_refresh.py`) and its
  existing script wrapper (`scripts/refresh_spy_adjusted_data.ps1`)
  unchanged in their current fetch/normalize/canonicalize logic. It does
  not invent a new provider, a new HTTP client, or a parallel
  normalization path. It adds a thin, fully-defaulted invocation and
  ledger layer in front of the existing adapter, plus the two adapter-side
  caps named below that do not exist in the adapter today (response-byte
  cap, provider-row cap).
- It is **dry-run by default**, matching `autonomy-apply-plan`'s shape.
  Without an explicit apply/authorization switch it resolves what *would*
  run and performs no HTTP request, no credential lookup, and no file
  write beyond a dry-run ledger record.
- Before any execution it runs a **network preflight** distinct in kind
  from the offline executor's credential preflight (which refuses when a
  credential *is* loaded). This preflight refuses when the fetch cannot
  safely proceed:
  - `APP_PROFILE=live` present → refuse (`profile_is_live`).
  - `TIINGO_API_KEY` **absent** → refuse (`token_not_available`); presence
    is checked by name only, and the boolean is the only thing recorded —
    the value is never read by the seam itself, only by the adapter's
    existing `load_tiingo_api_key_from_dotenv`/`token_lookup` boundary at
    the moment of the single authorized HTTP call.
  - Non-canonical executing root, non-canonical cwd, or any output
    destination path that does not resolve to the exact canonical
    relpaths named below → refuse (`noncanonical_target`), mirroring the
    crypto readiness replay's root/cwd/target validation
    (`autonomy_next_plan.py`'s canonical-path checks).
  - Requested symbol other than `SPY` → refuse (`symbol_scope_violation`).
    The general adapter accepts five approved ETF symbols; this seam is
    scoped to exactly `SPY` because `spy_market_data_soak` is the only
    lane it seeds.
  - Alpaca/broker credential variables are **not** a refusal condition
    here (they may coexist per `AGENTS.md` and the adapter never reads
    them), but the seam never loads or forwards them, and a defence-in-depth
    test must prove the child environment/process the seam launches never
    receives an Alpaca/APCA variable it did not already inherit from the
    operator's own shell.
- The seam performs and exposes no submit/cancel/replace/close/liquidation/
  paper-mutation/capital/live action. Every ledger record fixes
  `broker_access_attempted`, `broker_mutation_performed`,
  `paper_submit_performed`, `live_trading_performed`, and `live_authorized`
  to `false`, with `profit_claim=none`. Unlike the offline executor's
  ledger (which fixes `network_access_attempted=false` truthfully, because
  it never touches the network), this seam's ledger must record
  `network_access_attempted` **truthfully as `true`** whenever the single
  authorized HTTP GET is actually attempted, and `false` for a dry run or
  a preflight refusal. A ledger that hardcoded `false` here would be lying
  about the one thing this seam exists to do.

## Exact Bound Command

The seam invokes the existing adapter directly (in-process, or via
`scripts/refresh_spy_adjusted_data.ps1`, exact mechanism is an
implementation choice for the next milestone, not fixed by this contract)
with a **fully-defaulted, fixed argv** — no caller-substituted path,
symbol, or provider:

```
python -m algotrader.execution.etf_sma_adjusted_spy_data_refresh
  --provider tiingo
  --symbol SPY
  --mode live_market_data_fetch
  --live-market-data-fetch-authorized
  --output-csv .data/operator_inputs/spy_tiingo_adjusted_refresh_latest.csv
  --canonical-csv runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv
  --run-log runs/paper_lab/m446_adjusted_spy_bars_refresh_manifest.jsonl
  --raw-response-path runs/paper_lab/tiingo_spy_adjusted_raw_latest.json
  --soak-ledger runs/paper_lab/spy_adjusted_market_data_soak_ledger.jsonl
  --soak-report runs/paper_lab/spy_adjusted_market_data_soak_report.json
  --soak-required-sessions 5
  --start-date auto
  --revision-lookback-days 10
  --dotenv-path .env
  --expected-latest-bar-date <deterministic session date, see below>
  --format json
```

Every path above is a canonical repository-relative constant the seam must
validate byte-for-byte before launch; an operator- or plan-supplied
override of any one of them is a refusal, not a substitution. This is the
same "canonical target binding" discipline V5.48 applied to the crypto
readiness packet path, applied here to six destination paths instead of
one.

### Deterministic Expected-Session Semantics

The adapter's own CLI (`etf_sma_adjusted_spy_data_refresh.main`) falls back
to `datetime.now(UTC)` when `--expected-latest-bar-date` is omitted
(`_default_expected_latest_bar_date`, reading the wall clock). The seam
**must never rely on that fallback**. It requires its own caller-supplied,
explicit `--as-of` (an ISO-8601 UTC timestamp), exactly mirroring the
`-AsOf` requirement already frozen for the supervisor/planner/executor
(`docs/OPERATOR_RUNBOOK.md`'s V5.37/V5.38 sections: "`-AsOf` is required
and is the only time source"). The seam derives
`--expected-latest-bar-date` from that explicit `--as-of` using the same
`NyseExchangeSessionCalendar.latest_completed_session_on_or_before` the
adapter itself uses internally, and passes the resulting date explicitly
into the adapter's own `--expected-latest-bar-date` flag. This keeps the
whole chain deterministic given the same `--as-of`, with no second,
independent wall-clock read inside the adapter.

## Finite Caps

The instruction to bind "finite time/response/row/request/timeout caps" is
only partially satisfied by the adapter as it exists today. This contract
freezes which caps already exist and which a companion adapter change (a
small, separately reviewable diff, not authorized to land under this
contract-only milestone) must add before the seam is safe to build on:

| Cap | Existing? | Bound |
| --- | --- | --- |
| HTTP timeout | yes (`_HTTP_TIMEOUT_SECONDS = 20.0`) | 20 seconds, no retry inside `_tiingo_http_get` |
| HTTP requests per invocation | yes (implicit — exactly one `http_get` call per `_build_refresh_payload` run) | exactly 1 |
| Response byte size | **no — gap** | a future adapter change must cap `response.read()` to a fixed finite byte ceiling (e.g. 8 MiB) and fail closed with a sanitized `provider_response_too_large` category, not an unbounded read |
| Accepted provider row count | **no — gap** | a future adapter change must reject a parsed response exceeding a fixed finite row ceiling (e.g. 20,000 rows — comfortably above a full 1993-to-date SPY daily history, which is on the order of 8,000 rows) with a sanitized `provider_row_count_exceeded` category |
| Seam invocations per calendar UTC day | new, seam-level | at most 1 *authorized* attempt per UTC calendar day under normal operation; the seam is not itself a scheduler and does not loop, sleep, or retry — the existing three-retry, fifteen-minute-interval behavior remains the Windows Task Scheduler's job (`spy_eod_market_data_refresh_scheduled_task.xml`), external to this seam |
| Revision lookback window | yes (`RevisionLookbackDays`, 1-31, default 10) | unchanged, adapter-enforced |

A future implementation contract must add the two gap rows to
`etf_sma_adjusted_spy_data_refresh.py` (or an explicitly documented reason
they are unnecessary, re-argued at review time) before the network seam is
built on top of it. This contract does not authorize that adapter change;
it records the gap so the next milestone cannot silently skip it.

## Retry And Idempotency Behavior

- Within one seam invocation: **zero retries**. A failed HTTP attempt,
  invalid JSON, or blocked normalization ends that invocation in a
  `blocked_*` refresh state; the previous canonical file is preserved
  (existing adapter behavior — `previous_canonical_preserved_on_failure`).
- Across invocations: the soak evidence layer
  (`etf_sma_market_data_soak.py`) already deduplicates by **expected NYSE
  session**, not by attempt, so re-invoking the seam again the same UTC
  day after a failure is a legitimate same-session retry, not a duplicate
  — this existing behavior is preserved unchanged and the seam must not
  add a second, conflicting notion of idempotency on top of it.
- The seam itself adds one narrower idempotency check purely to bound
  *network* usage, not evidence correctness: if the soak report already
  shows `latest_session_qualified=true` for the session the caller's
  `--as-of` resolves to, the seam short-circuits to a no-op
  (`skipped_session_already_qualified`) **before** the preflight even
  checks for the token, performing zero HTTP requests. This is a network
  budget guard, not a correctness requirement — the soak layer would
  already record a same-session retry safely even without it.

## Sanitized Receipt And Provenance

The seam does not invent a new receipt shape. It relies entirely on the
existing, already-implemented chain:

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

The seam's own execution ledger (new, one record per invocation, JSONL,
under a new canonical path such as
`runs/autonomy_network_executor/latest/ledger.jsonl`) adds only the
**invocation-level** facts the offline execution ledger already models for
its own commands: action token, exact argv, exit code, preflight
booleans/reasons, `network_access_attempted`, wall-clock-free `as_of`
echo, and the adapter's own `refresh_state` — never the token value,
never a raw response body, never row-level data.

## Fail-Closed Refusal Conditions

Before any HTTP call, the seam refuses (recording zero network access) on
any of:

- `APP_PROFILE=live`.
- `TIINGO_API_KEY` absent.
- non-canonical executing root or cwd (same discipline as
  `autonomy_next_plan`'s/`autonomy_offline_executor`'s root binding).
- any of the six destination paths not matching its exact canonical
  constant.
- requested symbol not exactly `SPY`.
- `--as-of` missing, not UTC, or not resolvable to a valid NYSE session on
  or before it.
- the session-already-qualified idempotency short-circuit (see above) —
  this is a refusal to call the network, not an error; it still emits a
  ledger record with `network_access_attempted=false`.
- an explicit `--profile` (or any argv both parsers would otherwise accept
  as a profile override) passed ahead of the seam's own subcommand,
  mirroring the crypto readiness replay CLI's existing explicit-`--profile`
  refusal (`cli.py`'s `_run_crypto_readiness_replay`) — this seam must
  reject the same pattern rather than silently accepting an operator- or
  caller-supplied profile switch.

Any refusal is exit code `2` (input/precondition refusal, consistent with
the existing planner/executor/replay exit-code convention), never a
partial or best-effort fetch.

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
  would be an unreviewed behavior/compatibility change smuggled into a
  contract-only milestone.
- The **binding, permanent meaning** of `live_market_data_fetch` is fixed
  by this contract as: *perform the real (non-fixture, non-dry-run)
  read-only Tiingo HTTPS GET*. It is independently and separately
  distinguished from — and never a substitute for — `APP_PROFILE=live`,
  live-broker access, live order submission, or live-capital activity,
  every one of which the same adapter already rejects
  (`_live_market_data_fetch_preflight_blockers` refuses whenever
  `APP_PROFILE=live`) and none of which this seam gains any new authority
  over.
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
submit/cancel/replace/close/liquidate function, directly or transitively.
A future import-purity test for the new module, modeled on
`test_dependency_direction.py`'s existing crypto-readiness-replay launcher
scan, must prove this by static import-graph inspection, not by
inspecting default-argument behavior (the same distinction V5.45's audit
drew when it rejected `crypto-readiness-verify` for the offline executor
on import-surface grounds, not runtime-behavior grounds). Live capital
remains operator-gated until burn-in completes; nothing in this contract
touches that gate.

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
lanes... needs its own frozen contract and an undivided review pass").
This contract does not start that milestone and grants it no authority.

## What This Contract Does Not Do

- It does not implement, execute, or test anything. No `src/` or `tests/`
  file changes.
- It does not perform a network call, load `TIINGO_API_KEY`, or read any
  credential.
- It does not touch `AUTONOMY_EXECUTOR_ALLOWLIST`,
  `autonomy_offline_executor.py`, `autonomy_next_plan.py`'s classification
  registry, or `autonomy_supervisor.py`'s lane registry.
- It does not authorize a rename of `live_market_data_fetch` or any other
  existing flag/constant.
- It does not authorize wiring `spy_offline_daily_cycle` to consume this
  data.
- It does not change the Windows Task Scheduler template or its
  registration status.
- It does not weaken, bypass, or relax the existing adapter's HTTPS
  destination/method/query allowlist, symbol scope, or
  `APP_PROFILE=live` rejection.

## Correction To V5.50

`docs/design/v5_50_offline_autonomy_lane_eligibility_analysis.md`'s
lane-by-lane input-self-containment finding is unchanged and correct: no
*offline* lane besides the crypto readiness replay is eligible for
`EXECUTION_AUTO_OFFLINE`, and that remains true after this contract —
this contract adds a distinct *network* seam, not a new offline-auto
entry. What was stale in that document is its framing of the market-data
track as a pending operator decision among three options; the operator
has since selected option 2, so that document's "Options"/"Next Action"
sections are corrected in place (see the edit accompanying this contract)
to record the selection and point to this contract, without altering the
eligibility analysis itself.

## Next Action

Independent review of this frozen contract. No implementation is
authorized until that review completes and a separate implementation
milestone is opened against it. That implementation milestone must also
land the two adapter-side caps ("Finite Caps" above) as part of its own
reviewed diff before the network seam depends on them.
