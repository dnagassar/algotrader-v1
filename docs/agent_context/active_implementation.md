# Active Implementation

## Ownership and takeover

- Writer: Codex, sole implementation writer for this working tree.
- Working tree:
  `C:\Users\danie\.codex\worktrees\c029\algo_trader`.
- Branch: `codex/v5.62-nexustrade-source-data-unblock`.
- Takeover HEAD:
  `4e3112bc10ef78c948d37fcac9115f36a13f34a8`.
- The branch, HEAD, status, staged diff, unstaged diff, untracked files, and
  this handoff were inspected before any change.
- Takeover was clean: staged, unstaged, and untracked sets were empty.
- No reset, clean, stash, restore, rebase, branch switch, new branch, or new
  worktree occurred.
- Codex remained the only writer. No subagent was used.
- Dirty-file owner before the final local commit: Codex owns exactly the files
  listed under "Tracked implementation slice."
- Next action after this handoff update: final hygiene inspection, stage the
  coherent slice, commit locally, and verify a clean status.

## Decision

The deterministic canonical adjusted-daily data gate is cleared. The authentic
NexusTrade historical replay remains at a demonstrated source-evidence hard
gate.

An existing ignored dotenv in the primary checkout supplied the already
configured Tiingo credential through the repository's scoped `--dotenv-path`
loader. The dotenv and key were not copied, printed, returned, persisted in an
artifact, or exported to the implementation or test process.

Twelve exact-host read-only Tiingo EOD requests completed for:

`AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, GS, JPM, BRK-B, COST, SPY`.

All symbols have deterministic provider mappings, complete coverage, identical
observed SPY EOD sessions, authoritative documented adjustment semantics,
input hashes, and one deterministic combined local CSV.

The exact NexusTrade article and candidate-specific evidence still do not state:

1. the historical run's underlying bar/data mode;
2. the historical run's slippage assumption; or
3. whether the stated 365-day minimum uses calendar days or trading sessions.

Generic NexusTrade daily/intraday and exact-price-fill documentation cannot
substitute for candidate-specific authority. No values were inferred. Therefore
V5.58, the monthly strategy-family adapter, standalone replay, and real paired
composite remain intentionally unrun.

## Source evidence

- Exact article:
  `https://nexustrade.io/blog/this-strategy-has-beaten-the-market-for-over-5-years-heres-how-i-created-it-20250329`.
- Public candidate configuration image:
  `https://miro.medium.com/v2/resize:fit:1400/1*7WvMV_UXMia6SaLOC1IPHQ.png`.
- The public configuration confirms the source training dates and stock trading
  fee of `0.01% of trade`.
- Other accepted article screenshots confirm the candidate rules, source/OOS
  dates, and the stateful condition of at least 30 days since the last filled
  buy OR filled sell.
- Candidate-specific historical bar/data mode: absent and unverified.
- Candidate-specific historical slippage assumption: absent and unverified.
- Authentic 365-day warm-up clock: absent and unverified.
- A bounded structured search of available anonymized zero-cost NexusTrade
  material produced no exact candidate match.
- Subscriber-only, refused, anonymized, obfuscated, and client-rendered paths
  were not retried or worked around.
- No author contact, purchase, subscription, copy, fork, create, build,
  backtest, deploy, apply, or portfolio mutation occurred.
- External source metrics remain `untrusted_external_evidence`.
- The `29.64%` table versus `29.41%` chart discrepancy remains preserved.
- External metrics were not used for ranking, promotion, or local decisions.

## Canonical adjusted-data evidence

Provider and adjustment contract:

- Provider: Tiingo EOD.
- Provider documentation:
  `https://www.tiingo.com/documentation/end-of-day`.
- Provider symbology documentation:
  `https://www.tiingo.com/documentation/general`.
- Canonical price field: `adjusted_close`.
- Provider source field: `adjClose`.
- Tiingo documents CRSP-style split-and-dividend adjustment semantics for its
  EOD adjusted prices.
- Raw provider `open`, `high`, `low`, `close`, and `volume` are preserved.
- Adjusted OHLCV claimed: `false`.
- `BRK-B` canonical-to-provider mapping: `BRK-B->BRK-B`.
- Session reference: observed Tiingo SPY EOD dates; this is not represented as
  an independent official exchange calendar.

Exact chronological contract:

- Acquisition and warm-up coverage:
  `2019-01-02` through `2025-03-28`.
- Source training:
  `2021-12-31` through `2024-03-24`.
- Untouched OOS:
  `2024-03-24` through `2025-03-28`.
- Observed contract sessions per symbol: `1,569`.
- Pretraining sessions per symbol: `756`.
- Training sessions per symbol: `559`.
- OOS sessions per symbol: `254`.
- All twelve symbols match the observed SPY EOD session set.
- Missing or unexpected sessions: none.
- Weekend rows: none.
- Coverage supports both at least 365 calendar days and at least 365 observed
  sessions before source training.
- Authentic source interpretation of 365 days remains unresolved.

Generated ignored artifacts:

- Manifest:
  `runs/v5_63_nexustrade_canonical_data/canonical_data_manifest.json`.
- Manifest size: `12,314` bytes.
- Manifest SHA-256:
  `e204a8a1824e5b49ce4d457f12884bfc284d52f99ad3ba07072c978d7223d8e1`.
- Combined CSV:
  `runs/operator_input/multi_etf_adjusted_daily_canonical.csv`.
- Combined size: `1,234,759` bytes.
- Combined rows: `18,828`.
- Combined SHA-256:
  `d296138a95a86546bdc92678af479e8c8e204b138e2db43f54979a19921c9575`.
- Canonical data ready: `true`.
- Valid symbols: all twelve.
- Blocked symbols: none.

Per-symbol canonical SHA-256:

- AAPL:
  `dad21d2c16f29dee23499649e7c2f59bba8ac4ce4649fb695cdaccd902da59f4`.
- MSFT:
  `50c6629e173b55effa6f0ef889c0fc32e65df7af28a3e0aa958e2067196e2568`.
- GOOGL:
  `52bf16d74f7854978d3cc23340c8759894aa75956244950ae2e6ec8875bd3475`.
- AMZN:
  `881680fe05f846696a77d2ade097082ece4bef0ffc02e1ede7e3200b94f54515`.
- META:
  `5751c91728886f24f66789e1c490acac4ea651c3cecb91638f42925a106de012`.
- NVDA:
  `7523c2d3a9f305e33b9b634381e7fc512de92e55bb7c14b5bc756a5342ec5fb4`.
- TSLA:
  `0a75fc4000d45ba2de13fcdea55d6ebaeaaae75d77ab8b6112822f6281ddca4e`.
- GS:
  `43cd4220a5efd6632d96a6bdf606a9e1b480c52fc1bcc6a726f32945275383e6`.
- JPM:
  `74a1422d433b6d97fc85e3f4352ca50090d5878a2c54d64f1ba2cb796dbe49b1`.
- BRK-B:
  `e373de0c85cfbd0a95690df70ed27e4eff8a43e8857e0e33a4fe28c5e123d683`.
- COST:
  `ff9a6e7f552de8b016293dd19647c9e5c920d96f52265ee2f08c93eeb135cf1d`.
- SPY:
  `8db8e1c6215120e96c616ad795ccc6c4051f5b78b784833e6ea5f3a3ded8e608`.

## Credential and acquisition audit

- Current worktree `.env` present: `false`.
- Primary checkout ignored `.env` present: `true`.
- Primary checkout `TIINGO_API_KEY` declaration present: `true`.
- Primary checkout `TIINGO_API_KEY` nonempty: `true`.
- Credential value inspected, printed, returned, or persisted: `false`.
- Credential copied into this worktree: `false`.
- Credential exported into the implementation shell: `false`.
- Acquisition-child Tiingo token lookup attempted: `true`.
- Acquisition-child Tiingo token loaded: `true`.
- Acquisition-child token printed or written: `false`.
- Tiingo token loaded in offline verification/default pytest process: `false`.
- Market-data network requests: twelve read-only exact-host Tiingo EOD GETs.
- Fetch retries after the local manifest CLI defect: none. All data requests
  had completed; the manifest defect was fixed and replayed offline.
- Broker credential provider access: `false`.
- Broker account/order/position access: `false`.
- Broker mutation: none.
- Paper mutation: none.
- Live authorization: `false`.

## V5.58, adapter, and pairing outcome

- V5.58 rerun: not performed because source gates remain.
- Monthly equal-weight dynamic stock-filter adapter: not implemented.
- Source train/OOS/warm-up replay: not run.
- Standalone replay: not run.
- Composite preregistration: not performed.
- Composite replay: not run.
- SPY baseline, chronological OOS, walk-forward, cost sensitivity, and
  cross-asset portfolio gates: not run.
- `preview_review` route: not produced.
- No-submit shadow design: not supported by this result.
- No source rule, cost, fill, date, trade count, metric, or lineage was
  manufactured.

## Safety state

- Preflight before offline verification:
  - `APP_PROFILE` loaded: `false`;
  - `APP_PROFILE=paper`: `false`;
  - broker credential/endpoint aliases loaded: `false`;
  - process `TIINGO_API_KEY` loaded: `false`.
- Repository tests and offline verification network access: `false`.
- Broker and paper access during implementation and verification: `false`.
- Receipt status: not applicable.
- Reconciliation status: not required; no broker operation occurred.
- Live broker, live orders, live trading, and live capital remain prohibited.
- V5.57 sleeve ownership, reconciliation, auditing, and caps are unchanged:
  - `$25.00` maximum entry-order notional;
  - `$60.00` maximum aggregate marked SPY entry exposure;
  - one broker order per secure cycle; and
  - two sleeve intents per UTC day.
- No third sleeve was added.

## Verification

Acquisition/determinism checks:

- Twelve-symbol dry-run: passed; credential and network access both `false`.
- Twelve-symbol authorized read-only acquisition: all twelve requests and
  canonical intakes succeeded.
- Offline manifest replay after CLI fix:
  `nexustrade_monthly_adjusted_data_manifest_status=ready`.

Focused and dependency/import verification:

`python -m pytest tests\unit\test_import_safety.py tests\unit\test_dependency_direction.py tests\unit\test_nexustrade_strategy_intake.py tests\unit\test_etf_sma_local_bars_canonicalization.py tests\unit\test_multi_etf_adjusted_data_manifest.py tests\unit\test_spy_adjusted_data_refresh.py tests\unit\test_etf_sma_adjusted_spy_bars_refresh_intake.py tests\unit\test_nexustrade_monthly_adjusted_data_manifest.py`

- `158 passed` in `52.93s`.

Mandatory offline verification:

- `.\scripts\verify_offline.ps1`
- `109 passed` in `127.47s`.
- Result: `PASS`.
- The script explicitly skipped the full default suite.

Full default verification:

- First `python -m pytest`: `10,170 passed`, `5 skipped`, `1 failed` in
  `2,339.94s`; the failure was an exact safety-comment substring split across
  lines.
- Focused correction check:
  `python -m pytest tests\unit\test_spy_adjusted_data_refresh.py`.
- Focused correction result: `45 passed` in `2.14s`.
- Clean full rerun `python -m pytest`:
  `10,171 passed`, `5 skipped` in `2,311.02s`.
- Final failures and errors: zero.
- The five skips are credential-gated paper integration tests.

Final `git diff --check`, `git status --short`,
`git diff --name-only HEAD -- src`, and
`git ls-files --others --exclude-standard src tests` are run after this
handoff update and immediately before staging/commit.

## Tracked implementation slice

- `docs/OPERATOR_RUNBOOK.md`
- `docs/agent_context/active_implementation.md`
- `docs/deterministic_core.md`
- `scripts/refresh_nexustrade_monthly_adjusted_data.ps1`
- `scripts/refresh_spy_adjusted_data.ps1`
- `src/algotrader/execution/etf_sma_adjusted_spy_bars_refresh_intake.py`
- `src/algotrader/execution/etf_sma_adjusted_spy_data_refresh.py`
- `src/algotrader/research/nexustrade_monthly_adjusted_data_manifest.py`
- `tests/unit/test_etf_sma_adjusted_spy_bars_refresh_intake.py`
- `tests/unit/test_nexustrade_monthly_adjusted_data_manifest.py`
- `tests/unit/test_spy_adjusted_data_refresh.py`

Compatibility limitation:

- Existing M446 adapter and record names retain `ETF`/`SPY` terminology for
  backward compatibility even when the explicit research-only equity allowlist
  is used.

## Next milestone

No operator action or manual CSV placement is required. Do not request or expose
the Tiingo key and do not contact the source merely to force progress.

The authentic-source route may resume only if new candidate-specific
authoritative public material explicitly states the historical bar/data mode,
slippage assumption, and 365-day clock. Generic current documentation is not
sufficient.

If the operator later accepts a different research claim, a separately scoped
milestone may preregister an explicitly independent replication with disclosed
assumptions. That would not be represented as an authentic replay of the
March 2025 NexusTrade run and must not inherit its source metrics or lineage.
