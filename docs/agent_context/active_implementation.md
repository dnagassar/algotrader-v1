# Active Implementation Checkpoint

## Current Slice — V5.24 Tournament V2 Forward-Shadow Activation

- Execution date: `2026-07-15` America/New_York.
- Branch: `codex/crypto-frozen-state-reset-workflow`.
- Parent HEAD: `affcbc18e196786c255040cbaa69f0370a8624c6`
  (`Implement crypto tournament v2 accrual`).
- Exactly one implementation writer owned the checkout.
- Protected operator-owned files were not edited, staged, or committed.

## Verified Baseline Locked By This Slice

- The operator's exact read-only BTCUSD/ETHUSD/SOLUSD refresh succeeded for
  `2026-07-15T00:00:00Z` through `2026-07-15T23:00:00Z`.
- The refresh packet is `market_data_refresh_ready`, `data_intake_only=true`,
  and `strategy_evidence_evaluation_performed=false`.
- Refresh output SHA-256:
  `480931a8ca4cdd0a342ce8348605fb1cafa04b9a14829cf38d532ee2320f3e99`.
- Raw response SHA-256:
  `207de6f7cbc315948bcf8d5cffb44f6979757fb06b3dc07ddef92df2b2e54f69`.
- Embargo is complete at 24 rows per symbol and 72 rows total through
  `2026-07-15T23:00:00Z`.
- Tournament v2 is `collecting_untouched_oos`; zero OOS rows was correct at
  the fetch timestamp because no first OOS calendar hour had completed.
- Receipt count is 2. Candidate evaluations, ranking, and selected candidate
  remain empty. Terminal scoring has not occurred.
- Current tournament state fingerprint:
  `78bbfba22e75fabbe0570571a81436bf686448ceb0b7e23a2b0c5e1fa4bb7371`.
- Tournament v2 preregistration fingerprint remains
  `2ed9489543d8d21ab00d9f2f4000927b8012decf39882cb721cb2d1ce0b9376b`.
- Tournament v1 remains closed; no v1 candidate or OOS evidence was reused.

## Principal Bottleneck And Implemented Milestone

The immediate bottleneck is decision evidence, not another API or OMS layer.
The repository already has bounded paper submit/cancel, durable journal,
reconciliation, and certification machinery. It does not yet have a proven
crypto strategy that may feed those controls.

V5.24 removes the highest-leverage delegated downstream stop before a winner
is known. It freezes the single-winner no-submit forward-shadow activation
contract under fingerprint
`7ff152e69bd00eb8da9376d1f2be15194fbd04ed6a420151e30c3c46bec82436`.
The contract requires the sealed terminal packet hash, terminal evidence and
state fingerprints, exact eligible terminal classification, and exact
candidate ID/fingerprint from the frozen v2 manifest. It derives 168 untouched
future hourly observations beginning no earlier than the first complete UTC
hour after terminal closure and the tournament endpoint.

The real local readiness run at `2026-07-16T00:45:19.200229Z` classified
`waiting_for_tournament_terminal`, bound the current tournament state
fingerprint, selected no candidate, created no activation fingerprint or
shadow window, and performed no strategy evaluation, network operation,
broker read, broker mutation, or paper/live action. This is the correct
nonterminal baseline.

## Strategic Trajectory

- Recent market-data scheduling and OMS work materially increased operational
  autonomy but did not prove alpha.
- The frozen ADA forward-OOS rejection and v1 input-quality closure produced
  decision-quality negative evidence rather than deployable strategy support.
- Tournament v2 is the first current lane actively accumulating a sufficiently
  long, untouched, multi-candidate crypto decision dataset. It is evidence
  progress, not merely orchestration progress, but no result exists yet.
- V5.24 is targeted evidence plumbing: it prevents post-selection gate drift
  and removes delay after a terminal winner. It does not itself add performance
  evidence or justify paper/live capital.
- Adding Claude, Antigravity, QuantConnect, another retrieval API, or another
  execution framework would not remove the principal bottleneck. The limiting
  input is untouched causal market evidence from the already frozen strategy
  family.

## Unresolved Risks

- Tournament v2 may produce no qualifying candidate or may close at its input
  quality gate. That outcome must not be rescue-tuned or window-extended.
- The untouched OOS window remains incomplete and is exposed to provider gaps,
  volume-quality failure, weak fold stability, cost sensitivity, excessive
  drawdown, benchmark underperformance, or insufficient transitions/round
  trips.
- The 168-hour forward-shadow accrual/evaluation state machine and its
  selected-symbol guarded refresh bridge are not implemented yet. V5.24 locks
  their contract and activation boundary only.
- Even a successful terminal tournament and complete forward shadow would
  justify only a bounded paper-probe review. Paper mutation still requires an
  exact operator authorization; live credentials, capital allocation, live
  endpoints, and live trading remain unauthorized repository hard gates.
- No real small-capital loss budget, venue-specific live order constraints,
  live reconciliation acceptance packet, or live rollback/kill procedure has
  been approved. These remain later work after strategy and paper evidence.

## Safety And Verification Receipt

- Preflight and every verifier found `APP_PROFILE=paper` false and all six
  checked Alpaca credential aliases absent; no values were printed.
- This slice performed no network request, market-data fetch, broker/account
  read, broker mutation, submit, cancel, replace, close, liquidation, paper
  mutation, or live-endpoint access.
- New focused forward-shadow tests: 11 passed in 0.82 seconds.
- Expanded tournament/adapter/forward-shadow matrix: 47 passed in 47.38
  seconds.
- Dependency-direction gate: 33 passed in 10.20 seconds.
- Standard repository offline verifier: 97 passed in 106.91 seconds; `PASS`.
- The first bounded-full attempt reached the default 300-second Windows shard
  collection limit before execution; no test node failed.
- Established 600-second collection rerun: canonical 9,018 nodes across 454
  files; collection and execution equivalence passed; 9,014 passed, 4 skipped,
  0 failures, 0 errors; bounded full suite `PASS`.
- `git diff --check`: passed before handoff update and must be rerun before
  commit.
- Generated readiness state remains ignored under
  `runs/crypto_strategy_tournament/v2/forward_shadow/latest`.
- Protected user files remain byte-for-byte unchanged at SHA-256
  `4FB473115578E2F25B353F50C409CD7566932ED5CC609DDDF19F7D6B9C34AF17`
  and `602304A0D55369573B2AF4147850C7271EE518EB097D4AD86DB05D6FD50B4900`.

## Files Owned By This Slice

- `src/algotrader/research/crypto_tournament_v2_forward_shadow.py`
- `scripts/run_crypto_tournament_v2_forward_shadow.ps1`
- `tests/unit/test_crypto_tournament_v2_forward_shadow.py`
- `docs/design/v5_24_crypto_tournament_v2_forward_shadow.md`
- `docs/deterministic_core.md`
- `docs/OPERATOR_RUNBOOK.md`
- `docs/agent_context/active_implementation.md`

## Already-Selected Next Action

While tournament v2 continues its exact receipt-bound hourly OOS accrual,
implement the V5.24 contract's local forward-shadow state machine and thin
selected-symbol data-intake bridge. It must remain dormant until the public v2
state machine returns one sealed eligible terminal winner, then accept only
that immutable activation, accrue exactly 168 future one-hour observations,
emit causal hypothetical target/position/transition logs, apply the frozen
40/80 bps costs and cash/same-symbol benchmarks, and stop at evidence complete
for bounded-paper-probe review. It must not authorize or invoke paper mutation,
broker access, capital allocation, or live trading.

The independent operating action remains the next exact read-only v2 market
data refresh after at least one additional UTC hour has completed. Execute that
only in the isolated credential-loaded paper market-data shell already
documented in the runbook, then close that shell before development or tests.

## Prior Slice — V5.23 Preregistered Crypto Tournament V2

- Execution date: `2026-07-15`.
- Branch: `codex/crypto-frozen-state-reset-workflow`.
- Parent HEAD: `08fd6073b5bdd04c180baa54acd35c3f53342b83` (`Freeze v2 embargo warmup semantics`).
- Frozen preregistration commits: `298a2c8` and `08fd607`.
- Tournament v2 fingerprint: `2ed9489543d8d21ab00d9f2f4000927b8012decf39882cb721cb2d1ce0b9376b`.
- Tournament v1 remains closed under fingerprint `1475d35634750a7f00832f0a540fbaac3e28e7ed82ac7dbd8ef2d60e08f09097`.
- Exactly one implementation writer owned the checkout. Delegated reviews were read-only.

## Current Implementation Result

- Added a receipt-bound forward-OOS state machine limited to BTCUSD, ETHUSD, and SOLUSD.
- Discovery is fixed at `2026-01-16T00:00:00Z` through `2026-07-15T00:00:00Z` exclusive.
- The embargo is fixed at 24 hours for signal warmup only. The untouched OOS window is fixed at `2026-07-16T00:00:00Z` through `2026-08-13T00:00:00Z` exclusive in four 168-hour folds.
- Interim accrual emits no targets, returns, drawdowns, rankings, selections, or promotion evidence.
- Added a guarded `data_intake_only` refresh mode. It validates OHLCV and provenance but cannot invoke the legacy strategy evidence battery.
- New delta receipts must prove exact symbols/window/as-of/output paths, explicit data-only status, no strategy evaluation, a market-data fetch, and every no-mutation/live safety field as false.
- Inclusive one-hour refresh windows are supported.
- OOS return accounting uses the final embargo signal for the embargo-close to first-OOS-close return, charges the OOS boundary entry, holds the prior target on imputed bars in both 1h and 4h views, and excludes embargo round trips.
- Terminal success and terminal input-quality failure both seal one immutable SHA-bound terminal packet. Canonical terminal bytes contain a non-circular closure summary, replay without mutation, reject later deltas/rescoring, and fail on tampering.
- If multiple candidates qualify, the deterministic ranking selects exactly one no-submit shadow candidate. No result is paper- or broker-eligible.

## Current Local State

- Ignored state exists under `runs/crypto_strategy_tournament/v2/latest`.
- Discovery contains 12,960 normalized rows, 4,320 per symbol, with three explicit isolated-gap imputations.
- At status as-of `2026-07-15T21:00:00Z`, embargo and OOS raw rows remain zero and candidate evidence remains empty.
- The exact bounded next read-only window was `2026-07-15T00:00:00Z` through `2026-07-15T20:00:00Z` for BTCUSD/ETHUSD/SOLUSD.
- Readiness correctly classified `blocked_market_data_credentials_or_profile` because the normal process has no paper profile, paper market-data credentials, or explicit paper base URL.

## Current Safety Receipt

- `APP_PROFILE=paper` and all five Alpaca credential variables were absent before implementation and verification; no values were printed.
- This slice performed no network request, broker/account read, broker mutation, submit, cancel, replace, close, liquidation, paper mutation, or live-endpoint access.
- The refresh bridge remains fixed-host HTTPS GET market data only and requires both explicit network and market-data-fetch authorization.
- Paper planning, paper mutation, live trading, capital allocation, and profit claims remain unauthorized.
- Generated state remains ignored under `runs/`; no generated artifact is tracked or staged.

## Current Verification Receipt

- Expanded tournament-v2, adapter, and PowerShell wrapper matrix: 36 passed in 48.79 seconds.
- Final terminal-integrity matrix after the serialization fix: 21 passed in 64.21 seconds.
- Dependency-direction gate: 33 passed in 9.29 seconds.
- Final repository offline verifier: 97 passed in 136.62 seconds; result `PASS`.
- Canonical collection: 9,007 tests in 14.43 seconds.
- A single-process full default run reached its 1,204-second bound without producing a result; this was a timeout, not a failing test node. The required safety verifier and all modified-node tests passed.
- Independent final reviews found no remaining material defect in the research state machine, terminal sealing, data-only adapter, or orchestration boundary.
- `git diff --check`: passed.
- Protected user work remains byte-for-byte unchanged at SHA-256 `4FB473115578E2F25B353F50C409CD7566932ED5CC609DDDF19F7D6B9C34AF17` and `602304A0D55369573B2AF4147850C7271EE518EB097D4AD86DB05D6FD50B4900`.

## Files Owned by This Slice

- `src/algotrader/research/crypto_tournament_v2_forward_oos.py`
- `src/algotrader/orchestration/crypto_tournament_v2_forward_oos.py`
- `src/algotrader/execution/crypto_history_refresh_adapter.py`
- `scripts/run_crypto_tournament_v2_forward_oos.ps1`
- `scripts/refresh_multi_symbol_crypto_history.ps1`
- `tests/unit/test_crypto_tournament_v2_forward_oos.py`
- `tests/unit/test_run_crypto_tournament_v2_forward_oos_script.py`
- `tests/unit/test_crypto_history_refresh_adapter.py`
- `tests/unit/test_refresh_multi_symbol_crypto_history_script.py`
- `docs/design/v5_23_crypto_preregistered_tournament_v2.md`
- `docs/deterministic_core.md`
- `docs/OPERATOR_RUNBOOK.md`
- `docs/agent_context/active_implementation.md`

## Exact Next Action / True Gate

The implementation is complete and the frozen state is running. The remaining action is an exact read-only market-data fetch, which is a true operator credential gate under `AGENTS.md`.

In one isolated process, load `APP_PROFILE=paper`, paper Alpaca market-data credentials, and `APCA_API_BASE_URL=https://paper-api.alpaca.markets` without printing values. Then run:

    .\scripts\run_crypto_tournament_v2_forward_oos.ps1 -Mode market_data_fetch -AsOf <CURRENT_UTC_TIMESTAMP> -MarketDataFetchAuthorized -AllowNetwork

The wrapper computes the earliest missing through latest completed inclusive hour and restricts the call to BTCUSD/ETHUSD/SOLUSD. After it exits, clear the paper profile and credential variables before any test or ordinary local command. Do not manually edit the window, receipt, output, symbols, or generated state.

## Prior Slice — V5.22 Crypto Tournament Intake Verdict

- Execution date: `2026-07-15`.
- Branch: `codex/crypto-frozen-state-reset-workflow`.
- Preregistration commit frozen before the long-history fetch: `1def8ebe55baefffe99e95e7d98d9b216c17a3ee` (`Preregister crypto strategy tournament`).
- Preregistration fingerprint remains `1475d35634750a7f00832f0a540fbaac3e28e7ed82ac7dbd8ef2d60e08f09097`.
- Scope: execute the accepted one-year, one-hour, read-only Alpaca backfill for the fixed BTC/ETH/SOL/ADA tournament, run the unchanged intake gate, and stop only on decision-changing evidence or a true gate.
- Exactly one implementation writer owned the checkout. Delegated reviews were read-only.

## Current Implementation Result

- Corrected the tournament reader to accept the guarded adapter's actual normalized seven-column CSV while retaining authoritative receipt/path/SHA/source/schema/safety binding.
- Corrected the provider's inclusive end-time contract: request end `2026-07-14T23:00:00Z`, as-of `2026-07-15T00:00:00Z`, and require the final timestamp to equal the inclusive request end.
- Required exact refresh receipt schema `v5_22_crypto_history_refresh_adapter_receipt_v2`.
- Preserved validation of optional `asset_class`, `basis`, and `source` columns when they exist; normalized files report that source identity is receipt-bound rather than CSV-attested.
- Made the final normalized-history replacement atomic and added failure-preservation coverage.
- Candidate identities, parameters, costs, benchmarks, OOS windows, promotion thresholds, minimum rows, minimum positive-volume fraction, no-submit scope, and preregistration fingerprint did not change after data inspection.

## Current Authoritative Data Verdict

- Fixed read-only request completed for `2025-07-15T00:00:00Z` through inclusive `2026-07-14T23:00:00Z`.
- Bound normalized output SHA-256: `65db4f1aa09b8c45a8d8fcaf9f4e2b965a7d5814c859fa3125416d7497908137`.
- Bound raw-response SHA-256: `c8c21dba961a8312bec7b31808e4ce0ea2e01494a6a258a3ae686aef6f9a7054`.
- Receipt hashes match the generated files.
- BTCUSD: 8,759 rows, 8,729 positive-volume rows, positive-volume fraction `0.996575`, one non-hourly discontinuity.
- ETHUSD: 8,758 rows, 8,641 positive-volume rows, positive-volume fraction `0.986641`, two non-hourly discontinuities.
- SOLUSD: 8,753 rows, 8,490 positive-volume rows, positive-volume fraction `0.969953`, five non-hourly discontinuities.
- ADAUSD: 3,635 rows, 2,299 positive-volume rows, positive-volume fraction `0.632462`, starts `2026-02-13T12:00:00Z`, and has one non-hourly discontinuity.
- ADAUSD is 685 rows below the immutable 4,320-hour minimum and 31.754 percentage points below the immutable 95% positive-volume floor.
- Offline tournament intake terminated with `positive-volume coverage below tournament threshold for ADAUSD`.
- The row deficit and unequal/gapped common grid independently prevent the fixed four-symbol tournament from reaching strategy scoring.
- Terminal classification: `blocked_by_authoritative_input_history_quality`.
- No candidate was evaluated, ranked, selected, promoted, shadow-enabled, paper-planned, or made broker-eligible. No profit claim exists.

## Current Safety Receipt

- Paper market-data credentials were loaded only in the isolated authorized refresh process; values were never printed.
- Network access was limited to four sequential HTTPS `GET` requests on the fixed Alpaca crypto-bars market-data host/path.
- Market-data fetch occurred. Broker/account read, broker mutation, submit, cancel, replace, close, liquidation, live authorization, and live-endpoint access did not occur.
- Exact-value scan of the normalized CSV, refresh receipt, and raw response found no credential value.
- The normal implementation and test environment is credential-free.
- Generated evidence remains under ignored `runs/`; no generated artifact is tracked or staged.

## Current Verification Receipt

- Focused tournament, refresh-adapter, and evidence-battery matrix: 48 passed in 15.54 seconds.
- Dependency-direction gate: 33 passed in 6.63 seconds.
- Repository offline verifier: 97 passed in 85.68 seconds; result `PASS`.
- The full verifier safety prelude repeated 97 passes in 83.01 seconds.
- Canonical full collection: 8,978 exact nodes across 450 files.
- The first four-shard collection attempt hit the default 300-second Windows collection timeout; this was an infrastructure timeout, not a failed test.
- The exact suite was rerun with the same four shards and a 600-second collection allowance. Execution began only after canonical/shard collection equivalence passed.
- Completed JUnit receipts: 8,974 passed, 4 skipped, 0 failures, 0 errors across all 8,978 nodes.
- `git diff --check`: passed.
- Protected user work remained byte-for-byte unchanged at SHA-256 `4FB473115578E2F25B353F50C409CD7566932ED5CC609DDDF19F7D6B9C34AF17` and `602304A0D55369573B2AF4147850C7271EE518EB097D4AD86DB05D6FD50B4900`.

## Files Owned by This Slice

- `src/algotrader/research/crypto_preregistered_tournament.py`
- `src/algotrader/research/crypto_strategy_evidence_battery.py`
- `tests/unit/test_crypto_preregistered_tournament.py`
- `tests/unit/test_crypto_history_refresh_adapter.py`
- `tests/unit/test_crypto_strategy_evidence_battery.py`
- `docs/design/v5_22_crypto_preregistered_tournament.md`
- `docs/OPERATOR_RUNBOOK.md`
- `docs/agent_context/active_implementation.md`

## Exact Next Action / True Gate

Do not weaken, retune, or remove ADA from tournament v1 after seeing this data. The v1 intake verdict is terminal.

Continuing immediately requires a new scope decision because either path changes the frozen evidence contract:

1. Preferred fast path: explicitly authorize a new preregistered `tournament_v2` liquid universe containing BTCUSD, ETHUSD, and SOLUSD only, keep v1 closed, assign a new fingerprint, and reserve a new untouched OOS window; or
2. Supply or authorize an independent authoritative ADA hourly-history source that can prove at least 4,320 consecutive common hours and at least 95% positive-volume coverage under a new receipt-bound intake contract.

This is a true evidence/scope gate, not routine workflow management. No additional Alpaca retry, model API, paper-account mutation, or live-capital action can repair the frozen v1 evidence.

## Prior Slice — Frozen ADA Forward-OOS Verdict

- Execution date: `2026-07-15`.
- Branch at takeover: `codex/crypto-frozen-state-reset-workflow`.
- Parent HEAD at takeover: `c06b416dc45535aa7616659b104a8f082874ea0c` (`Automate market data evidence soak`).
- Scope: execute the already-selected, exact-window, read-only Alpaca crypto-bars refresh for the immutable candidate `crypto:ADAUSD:trend_momentum_24h_repair`, then classify its untouched forward-OOS evidence without retuning or authorizing paper mutation.
- The inherited SPY market-data soak remains active and unchanged; crypto is the accelerated research lane, not an automatically promoted paper-capital lane.
- Exactly one implementation writer owned this checkout. Delegated repository audits were read-only.

## Current Evidence Verdict

- Readiness classification before fetch: `ready_for_explicit_read_only_market_data_fetch` with no blockers.
- Authorized window: `2026-07-10T01:00:00Z` through `2026-07-15T14:23:14Z`, strictly after the frozen discovery cutoff `2026-07-09T16:00:00Z`.
- Provider observations accrued: 142 hourly rows per symbol for `BTCUSD`, `ETHUSD`, `SOLUSD`, and `ADAUSD`; 568 normalized rows total.
- Final classification: `fresh_oos_rejected`.
- Frozen ADA candidate: `-0.03577738` total return, `0.05794141` maximum drawdown, 13 trades/turnover transitions.
- Required benchmarks: cash `0`, ADA buy-and-hold `-0.00657559`, equal-weight BTC/ETH/SOL/ADA basket `0.02961488`.
- Rejection reasons: `cash_underperformance`, `buy_and_hold_underperformance`, and `basket_underperformance`.
- Rows still required by the legacy 26-row gate: `0`.
- Paper-planning and repair eligibility: `not_eligible`.
- This is a decision-quality strategy rejection. Discovery snapshot, frozen-candidate identity, chronology, duplicate, fixture, leakage, and accrued-state integrity checks all passed.
- Do not rescue-tune, rename, or paper-probe this frozen candidate. Any future configuration is a new preregistered candidate with a new identity and untouched evaluation windows.

## Current Safety Receipt

- Broker credentials and `APP_PROFILE=paper` were absent from the normal implementation/test environment.
- Existing locally stored paper market-data settings were loaded only into isolated readiness/fetch processes after exact operator authorization; no values were printed or written to artifacts.
- Network access was limited to the adapter's fixed-host Alpaca crypto-bars HTTPS `GET` path. Market-data fetch occurred; broker read, broker mutation, submit, cancel, replace, close, liquidation, and live-endpoint access did not occur.
- Artifact scan confirmed no locally stored credential value appears in the readiness, refresh, raw-response, normalized-bar, accrued-OOS, or operating-packet artifacts.
- Generated state remains under ignored `runs/`; no generated run artifact is tracked.

## Current Verification Receipt

- Focused adapter, frozen-OOS, and dependency-direction matrix: 77 passed in 14.78 seconds before the network call.
- Independent delegated focused matrix: 85 passed in 17.60 seconds.
- Repository offline verifier: 97 passed in 94.72 seconds; final result `PASS`.
- `git diff --check`: passed.
- No changed or untracked files under `src/` or `tests/`.
- Protected user work remained byte-for-byte unchanged.

## Current Files Owned by This Slice

- `docs/agent_context/active_implementation.md`
- Ignored/generated evidence under `runs/crypto_repair_forward_oos_accrual/latest/` (never authority and never staged).

## Inherited Baseline Context

## Verified Repository Baseline

- Repository: `C:\Users\danie\Desktop\algo_trader`.
- Branch: `codex/crypto-frozen-state-reset-workflow`.
- Parent HEAD at takeover: `658c2b24d0dee2003f47f04663e22c237345a8a0` (`Clarify readiness verification evidence`).
- Preflight before implementation and verification found `APP_PROFILE` and all five Alpaca credential variables absent; no values were printed.
- The implementation inherited two unrelated user-owned dirty artifacts and preserved them byte-for-byte.
- Exactly one implementation writer owned this checkout; all delegated audit work was read-only.

## Files Owned by This Slice

- `.env.example`
- `src/algotrader/execution/etf_sma_adjusted_spy_data_refresh.py`
- `src/algotrader/execution/etf_sma_adjusted_spy_bars_refresh_intake.py`
- `src/algotrader/execution/exchange_session.py`
- `scripts/refresh_spy_adjusted_data.ps1`
- `scripts/run_daily_paper_lab_cycle.ps1`
- `docs/design/spy_eod_market_data_refresh_scheduled_task.xml`
- `docs/deterministic_core.md`
- `docs/OPERATOR_RUNBOOK.md`
- `tests/unit/test_spy_adjusted_data_refresh.py`
- `tests/unit/test_spy_eod_market_data_refresh_schedule.py`
- `src/algotrader/execution/etf_sma_market_data_soak.py`
- `tests/unit/test_spy_market_data_soak.py`
- `tests/unit/test_run_daily_paper_lab_cycle_script.py`
- `docs/agent_context/active_implementation.md`

## Capability Actually Proven

- The existing Tiingo adjusted daily-bars adapter is now the sole authoritative refresh path; no parallel ingestion stack was added.
- An actual fetch still requires both `live_market_data_fetch` mode and the explicit `LiveMarketDataFetchAuthorized` switch. Default mode remains network-free `dry_run`.
- Production transport permits only HTTPS `GET` to authority `api.tiingo.com`, exact path `/tiingo/daily/{approved_symbol}/prices`, approved ETF symbols, and the three expected query keys. HTTP, alternate hosts, suffix hosts, user info, ports, other paths, extra query keys, and non-Token headers fail before connection.
- `TIINGO_API_KEY` is the only token variable accepted by configuration or the scoped dotenv loader. The adapter contains no broker credential variable names and performs no broker credential lookup.
- `APP_PROFILE=paper` and unrelated broker variables may coexist with the isolated Tiingo capability. `APP_PROFILE=live` remains blocked.
- `start_date=auto` now re-fetches a bounded ten-calendar-day trailing window. Equal-latest provider data is validated and compared instead of skipped; provider data older than the canonical latest date still fails closed.
- Manifests record revision-window bounds, overlap/new/unchanged/revised/removed counts, revised dates, provider-response SHA-256, prior canonical SHA-256, normalized candidate SHA-256, final canonical SHA-256, and a typed revision outcome.
- Existing rows inside the fetched interval are authoritatively replaced while rows outside the interval are preserved.
- Raw provider bytes, normalized candidate CSV, canonical CSV, and one-record manifests use same-volume atomic replacement with cleanup. Validation and replace failures preserve the previous canonical bytes.
- Default expected-date resolution now uses the latest actually completed NYSE session, including pre-close fallback and weekend/holiday catch-up.
- The isolated Task Scheduler template runs at 20:10 host-local America/New_York time on weekdays, requires network availability, ignores overlapping instances, retries three times at fifteen-minute intervals, and calls only the Tiingo refresh. It is deliberately separate from the paper-mutation supervisor.
- The local `TIINGO_API_KEY` was found in the untracked `.env`, loaded only inside the scoped adapter, and was never printed or written to an artifact.
- The Windows user-level task `spy-eod-market-data-refresh` is registered, `Ready`, and scheduled for 20:10 host-local Eastern time on weekdays. Its first on-demand run completed with Task Scheduler result `0`.
- PowerShell string registration required removing the XML byte-encoding declaration; a regression test now pins that Windows compatibility contract.
- Each configured live attempt now appends a compact secret-free receipt and atomically regenerates a readiness report; same-session retries cannot inflate the distinct-session streak.
- A failed latest expected session resets the current streak until that session succeeds, so retries improve recovery without manufacturing evidence.
- The registered task is soak-enabled and its on-demand seed completed with result `0`: one qualifying session, four remaining, next expected session `2026-07-15`.

## Verification Receipt

- Focused soak/refresh/scheduler matrix: 49 passed in 2.83 seconds.
- Focused soak/refresh/scheduler/dependency/import matrix: 86 passed in 24.66 seconds.
- Repository targeted offline verifier: 97 passed in 79.15 seconds; final result `PASS`.
- Full verifier repeated the 97 safety tests in 77.43 seconds and then collected and executed 8,960 tests across four exact shards with collection and execution equivalence:
  - shard 1: 2,240 tests, exit `0`, no timeout
  - shard 2: 2,240 tests, exit `0`, no timeout
  - shard 3: 2,240 tests, exit `0`, no timeout
  - shard 4: 2,240 tests, exit `0`, no timeout
  - aggregate: 8,956 passed, 4 skipped, 0 failures, 0 errors; bounded full suite `PASS`
- `git diff --check`: passed.
- No tracked `runs/` artifacts were created.
- Three authorized exact-destination Tiingo HTTPS `GET` refreshes have occurred across activation and verification; the latest was the soak-enabled Task Scheduler seed.
- The seed receipt qualified expected session `2026-07-14`, left canonical SHA-256 `46B540097449EA9FA8A7018A8E547DC62ADABD2E713C0477DA8D4F18B764F9E2` unchanged, and produced `collecting_unattended_market_data_soak` at 1/5 with next expected session `2026-07-15`.
- Task Scheduler returned `0`; the receipt recorded token printed/written false and broker access/mutation false.
- No broker SDK, broker credential lookup, broker read, broker mutation, submit, cancel, replace, close, liquidation, or live-capital action occurred.

## Classification and Trajectory Impact

- Task classification: `authoritative_read_only_market_data_vertical_slice`.
- Evidence classification remains `operational_data_provenance_capability` at 1/5. The deterministic report alone promotes it to `unattended_authoritative_market_data_proven` after five consecutive qualifying expected sessions; neither state is strategy evidence or an alpha result.
- Autonomy impact: positive but bounded. The system can prepare and audit authoritative adjusted bars on a schedule without an operator hand-editing CSVs. It still cannot establish that SPY SMA 50/200 or any challenger has deployable edge.
- Safety/orchestration impact: narrower and materially useful rather than another general framework. Destination, method, credential, artifact, and schedule scope are explicit and tested.
- Live-capital impact: none. The repository remains paper-only and not live-authorized.

## Protected Dirty Work

- Preserve `docs\project_checkpoint.md` as an unrelated modified historical checkpoint owned by the operator/user.
- Preserve `docs\design\v5_20_3_crypto_frozen_state_reset_baseline.md` as an unrelated untracked report owned by the operator/user.
- Their takeover and post-verification SHA-256 values remain:
  - `4FB473115578E2F25B353F50C409CD7566932ED5CC609DDDF19F7D6B9C34AF17`
  - `602304A0D55369573B2AF4147850C7271EE518EB097D4AD86DB05D6FD50B4900`
- Do not reset, clean, stash, restore, rebase, switch branches, stage, or commit either artifact without explicit ownership transfer.

## Active Safety Boundaries

- Default pytest remains offline, deterministic, credential-free, socket-blocked, broker-free, and network-free.
- Paper market-data access is read-only and exact-destination. No broker trading endpoint is reachable through this adapter.
- Paper mutation, live-broker access, paper/live mode changes, capital allocation, and all live-capital activity remain outside this slice.
- `ExecutionIntent` is not a broker order; `ExecutionPlan` remains immutable and pre-broker. Agents and LLMs remain outside the trading hot path.

## Exact Next Action

Treat `crypto:ADAUSD:trend_momentum_24h_repair` as closed and rejected. Do not retune it or authorize a paper probe.

The next implementation milestone is a new, preregistered crypto evidence tournament while the SPY operational soak continues independently:

- backfill at least 180 days (`4,320` hourly bars per symbol) for `BTCUSD`, `ETHUSD`, `SOLUSD`, and `ADAUSD`, with one year preferred
- use 1-hour bars as the primary research timeframe and 4-hour aggregation only as a robustness check; do not add sub-hour strategies
- freeze candidate identities and parameters before OOS evaluation
- compare every candidate with cash, symbol buy-and-hold, and the equal-weight basket
- add realistic taker-fee/slippage base and doubled-cost stress cases
- require multi-window untouched OOS stability, drawdown and profit-concentration gates, and minimum trade/sample thresholds before no-submit shadow eligibility
- preserve the existing no-submit, paper-mutation, broker, credential, network-default, and live-capital boundaries

No new model API, retrieval source, execution framework, or paper-account mutation is justified by this verdict. The next writer should implement the tournament/backfill slice on the current branch after repeating the credential-free preflight and preserving the two protected user-owned artifacts below.
