# Active Implementation

## Ownership and takeover

- Writer: Codex, sole implementation writer for this working tree.
- Branch: `codex/v5.60-nexustrade-monthly-adapter-gates`.
- Required V5.59 branch:
  `codex/v5.59-nexustrade-authentic-composite`.
- Required and observed takeover commit:
  `44571a75b9097a85b9643f78dfecc97e251c488e`.
- The worktree opened detached at the required commit. The required V5.59
  branch ref pointed to the same commit.
- Staged, unstaged, and untracked sets were empty. The prior handoff was read
  before any change. No reset, clean, stash, restore, rebase, or takeover
  branch switch occurred.
- After the clean takeover was proven, the new V5.60 feature branch was
  created from the exact required commit.
- Codex remained the only writer. Three bounded subagents performed read-only
  source, data-contract, and lineage reviews; none edited files or Git state.

## Decision

V5.60 reached a demonstrated hard gate. Do not implement the monthly
cross-sectional family adapter or a paired composite from this state.

Both exact source-evidence fields remain absent, the current worktree has no
canonical bars, and the approved adjusted-data provider cannot acquire the
eleven-stock universe. The final V5.58 intake therefore has four blockers,
not solely `needs_local_adapter`. Per the implementation gate, no production
adapter, date-window evaluator, composite, fake replay, or metadata-only pair
was created.

## Authenticated NexusTrade evidence

- NexusTrade OAuth MCP authenticated: `true`.
- Raw NexusTrade bearer/API-key environment alias loaded: `false`.
- Exact founder-authored article:
  `https://nexustrade.io/blog/this-strategy-has-beaten-the-market-for-over-5-years-heres-how-i-created-it-20250329`.
- Authenticated `search_articles` identified article ID
  `this-strategy-has-beaten-the-market-for-over-5-years-heres-how-i-created-it-20250329`,
  short ID `rbXUPvf9o`, author Austin Starks, and publication timestamp
  `2025-03-29T08:54:48.906Z`.
- Authenticated `get_article` returned the full article and the exact
  standalone universe/rules, source periods, source metrics, linked
  conversation, and linked public portfolio.
- One bounded exact-article extractor request returned provider HTTP 500. It
  was not retried or worked around.
- The linked conversation and public portfolio are client-rendered. No
  browser session was available for further visual inspection.
- Current generic NexusTrade backtesting documentation distinguishes
  `OHLC (Daily)` from minute-level `Intraday`, but does not identify the mode
  used by this exact March 2025 run.
- Current generic troubleshooting documentation says backtests assume exact
  execution price, which is consistent with no modeled slippage, but it is
  neither candidate-specific nor contemporaneous proof of this exact run.
- Final exact-source fields:
  - underlying bar/data mode: absent and unverified;
  - slippage assumption for this candidate/backtest: absent and unverified.
- Monthly cadence and day-based indicators were not treated as authority to
  infer `daily_ohlc`; current generic exact-price documentation was not used
  to invent `slippage_bps=0`.
- Provider anonymization, obfuscation, client-rendering, and retrieval
  boundaries were respected without retry or workaround.

No NexusTrade create, build, backtest, deploy, apply-corpus, fork, subscribe,
purchase, portfolio mutation, paper mutation, broker, order, or live action
occurred.

## Authentic candidate and source-metric trust

The source candidate remains the fixed AAPL, MSFT, GOOGL, AMZN, META, NVDA,
TSLA, GS, JPM, BRK-B, and COST universe. At an equal-weight monthly
rebalance, a stock qualifies only when exactly one or two of these conditions
are true:

1. price is above its 30-day SMA;
2. price divided by its 365-day minimum price is at most `1.05`; or
3. the stock's 14-day RSI is below `28` while SPY's 14-day RSI is above `33`.

The source screenshot evidence also records constant-1 descending sort and an
at-least-30-days-since-last-filled-buy OR filled-sell condition across the
universe. That stateful source rule is not equivalent to the current local
factory's first-session-of-a-new-calendar-month helper.

The source training period is `2021-12-31` through `2024-03-24`; the untouched
holdout is `2024-03-24` through `2025-03-28`. Source stock fee `0.01%` is
normalized to 1 bp. Source performance remains
`untrusted_external_evidence`; it was not used for ranking or promotion.

The holdout source table reports `29.64%`, while its chart displays
`+$2,946.31 (29.41%)`. The discrepancy remains unresolved and reinforces that
source-reported performance cannot control any local decision.

Authenticated public-portfolio/profile discovery found the linked shared
portfolio with one strategy and obfuscated internals. The article names no
parent or ancestor. Therefore no authentic parent was claimed. A real
composite would need an explicit signal/rebalance rule that changes target
weights; `parent_strategy_ids` and `pairing_role` alone are metadata and were
not treated as a paired result.

## V5.58 offline intake

Generated capture:

`runs/v5_60_nexustrade_monthly_adapter_gate/authenticated_monthly_dynamic_stock_filter_capture.json`

- SHA-256:
  `6ed15b6faadd58c5c67e26d19781ffd9fbd6e1014bd95e1726ddda9edba62935`.
- `source_backtest.data_mode=null`.
- `source_backtest.slippage_bps=null`.
- Source fee is 1 bp; source metrics remain untrusted.

Generated final report:

`runs/v5_60_nexustrade_monthly_adapter_gate/authenticated_intake/nexustrade_intake_report.json`

- SHA-256:
  `531bc5c165912143e005561b6321d33d01f2313903d1b987e04e724d38c7822a`.
- `eligible_candidate_count=0`.
- `local_replay.status=not_run_no_eligible_candidates`.
- route `repair_intake_blockers`.
- source metrics used for ranking: `false`.
- source metrics used for promotion: `false`.
- paper promotion allowed: `false`.
- offline-intake network, broker access, broker mutation, and live mutation:
  all `false`.

Exact blockers:

- `source_data_mode_missing`;
- `source_cost_assumptions_missing`;
- `local_timeframe_adapter_required`; and
- `local_strategy_family_adapter_required`.

One earlier wrapper invocation failed closed before classification because the
transport grouping label contained an underscore disallowed by the existing
symbol syntax. The final capture uses the schema-valid grouping label
`STOCKBASKET`; the exact eleven-symbol universe remains explicit and
unchanged. No replay occurred in either invocation.

## Canonical data gate

- The new worktree initially contained no `runs/` or `.data/` directory.
- The configured
  `runs/operator_input/multi_etf_adjusted_daily_canonical.csv` is absent.
- Consequently, the current worktree has zero canonical rows for AAPL, MSFT,
  GOOGL, AMZN, META, NVDA, TSLA, GS, JPM, BRK-B, COST, or SPY.
- All twelve symbols are missing across training
  `2021-12-31`–`2024-03-24` and untouched OOS
  `2024-03-24`–`2025-03-28`.
- Pre-training warm-up is also wholly absent. The source does not establish
  whether the 365-day minimum means calendar days or 365 underlying bars, so
  the authentic earliest warm-up boundary cannot be invented.
- The canonical loader requires exact local columns
  `symbol,date,open,high,low,close,adjusted_close,volume`, ISO dates, positive
  Decimal prices, coherent OHLC, nonnegative integer volume, no duplicate
  symbol/date rows, and no extra columns.
- The existing manifest adds SHA-256, earliest/latest dates, freshness, and
  the `adjusted_close_price_return` basis, but both manifest and refresh
  contracts are restricted to SPY, QQQ, IWM, TLT, and GLD.
- The only repository-approved adjusted-data provider is the fixed-host,
  HTTPS Tiingo GET path. It maps provider `adjClose` to canonical
  `adjusted_close`, uses only `TIINGO_API_KEY`, and is isolated from broker
  access.
- That approved path rejects all eleven candidate stocks. BRK-B provider
  identifier normalization is also not established.
- `TIINGO_API_KEY` loaded: `false`. No market-data credential was requested
  or connected, and no market-data fetch was attempted.
- The available Alpaca connector exposes historical OHLCV but no explicit
  adjusted-close/adjustment selection in its callable contract. It was not
  used to fabricate canonical adjusted data.
- No non-approved vendor, hand normalization, synthetic corporate action,
  or cross-worktree generated artifact was used.

Even if a generic combined CSV appeared, the current challenger factory's
half-sample later-test and three equal index folds cannot express the exact
source training and untouched-OOS boundaries. Exact date-window and
warm-up-support contracts would be part of the future gated adapter slice,
not evidence that the present gate is clear.

## Pairing and replay outcome

- Standalone local replay: not run.
- Composite local replay: not run.
- SPY baseline, exact chronological OOS, walk-forward, cost sensitivity, and
  cross-asset gates: not run because there was no eligible candidate or
  canonical data.
- No `preview_review` route was produced.
- No later no-submit shadow design is recommended from this result.
- No metadata-only pairing, synthetic fills, invented costs, fabricated
  metrics, or fake lineage was created.

## Credential, network, broker, and safety state

- `APP_PROFILE` loaded: `false`; `APP_PROFILE=paper`: `false`.
- Alpaca credential aliases loaded: `false`.
- Alpaca endpoint/account-identity aliases loaded: `false`.
- Tiingo credential alias loaded: `false`.
- raw NexusTrade credential aliases loaded: `false`.
- paper-integration test flag loaded: `false`.
- Only boolean presence was inspected. No credential value, token, API key,
  account identifier, response payload, or broker data was requested,
  printed, copied, persisted, or returned.
- Network reads: authenticated NexusTrade article/profile/public metadata and
  authoritative public NexusTrade article/docs only.
- Repository offline intake network access: `false`.
- Broker or broker credential provider access: `false`.
- Paper submit/cancel/replace/close/liquidate or other mutation: none.
- Receipt status: not applicable.
- Reconciliation status: not required; no broker operation occurred.
- Live-authorized state: `false`; live broker, live orders, and live capital
  remain prohibited.
- V5.57 sleeve ownership, reconciliation, auditing, and limits are unchanged:
  `$25.00` maximum entry-order notional, `$60.00` maximum aggregate marked
  SPY entry exposure, one broker order per secure cycle, and two sleeve
  intents per UTC day.
- No third paper sleeve was added.

## Verification

- Focused intake/challenger/local-bars/dependency suites:
  93 passed in 68.25 seconds.
- Mandatory `scripts/verify_offline.ps1`:
  109 passed in 103.64 seconds; result `PASS`.
- The mandatory script skipped the full suite.
- Full default suite:
  10,162 passed and 5 skipped in 2,518.04 seconds; zero failures and zero
  errors.
- Verification was credential-free, network-free, and broker-free.
- Final `git diff --check`, status, exact `src` diff, and untracked
  `src/tests` hygiene are run after this handoff update and before commit.

## Files and generated state

Tracked change:

- `docs/agent_context/active_implementation.md` only.

Ignored generated evidence:

- `runs/v5_60_nexustrade_monthly_adapter_gate/`.

There are no production `src` changes, no test changes, and no untracked
`src` or `tests` files.

## Next milestone

Resume this exact milestone only after both gates are supplied without
credential disclosure:

1. candidate-specific authoritative NexusTrade evidence for the historical
   run's bar/data mode and slippage assumption; and
2. an approved deterministic adjusted-daily acquisition/normalization path
   for AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, GS, JPM, BRK-B, COST, and
   SPY with explicit provider symbol mapping, adjustment semantics, hashes,
   complete source-period coverage, and authenticated warm-up semantics.

Then rerun V5.58. Implement the smallest operational adapter only when the
authentic candidate is blocked solely by local adapter requirements. The
implementation must preserve the exact 30-day stateful rebalance rule and
exact source train/OOS dates, add meaningful portfolio-level cross-asset
gating, and replay standalone plus a preregistered real composite under
identical local assumptions. Only a locally produced `preview_review` route
may support a later no-submit shadow design.
