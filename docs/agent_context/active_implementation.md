# Active Implementation

## Ownership and takeover

- Writer: Codex, sole implementation writer for this working tree.
- New branch: `codex/v5.61-nexustrade-monthly-exact-gates`.
- Required base branch:
  `codex/v5.60-nexustrade-monthly-adapter-gates`.
- Required and observed base commit:
  `7b988a805b0fb0f7406857c1a163e2e401f1f80a`.
- The checkout opened detached at the required commit. The required V5.60
  branch ref existed and pointed to that exact commit.
- Before any change, staged, unstaged, and untracked sets were empty, and this
  handoff matched `HEAD`.
- No reset, clean, stash, restore, rebase, or takeover branch switch occurred.
- After the clean takeover and exact branch ref were proven, the new V5.61
  branch was created directly from the required commit.
- Codex remained the only writer. No subagent edited or inspected the working
  tree.
- Dirty tracked-file owner before commit: Codex owns only this handoff update.
  Ignored `runs/` evidence is generated state, not an implementation writer.
- After the local handoff commit, no dirty tracked, staged, or untracked
  `src/tests` work should remain.

## Decision

V5.61 reached a demonstrated hard gate. Do not implement the monthly
strategy-family adapter, rerun V5.58, or preregister/replay a paired composite
from this state.

The authenticated exact article, its candidate-specific advanced-settings
screenshot, the exact linked shared conversation, and the exact linked public
portfolio still do not state the historical run's underlying bar/data mode or
slippage assumption. The current worktree also has no canonical bars, no
eligible adjusted-data acquisition credential, no established `BRK-B` provider
mapping, and no authentic indicator warm-up boundary.

The objective authorizes the V5.58 rerun and operational adapter/replay only
after every source and data gate clears. Those gates did not clear, so no local
adapter, fake replay, metadata-only pair, synthetic bars, or invented
assumption was created.

## Authenticated NexusTrade source evidence

- NexusTrade OAuth read-only provider authenticated: `true`.
- Raw NexusTrade bearer/API-key environment alias loaded: `false`.
- Exact founder-authored article:
  `https://nexustrade.io/blog/this-strategy-has-beaten-the-market-for-over-5-years-heres-how-i-created-it-20250329`.
- Authenticated `search_articles` and `get_article` identified:
  - article ID:
    `this-strategy-has-beaten-the-market-for-over-5-years-heres-how-i-created-it-20250329`;
  - short ID: `rbXUPvf9o`;
  - author: Austin Starks;
  - published timestamp: `2025-03-29T08:54:48.906Z`.
- The authenticated article text was retrieved successfully.
- The exact embedded advanced-settings screenshot was visually inspected:
  `https://miro.medium.com/v2/resize:fit:1400/1*7WvMV_UXMia6SaLOC1IPHQ.png`.
- That screenshot explicitly shows:
  - start date `12/31/2021`;
  - end date `03/24/2024`;
  - SPY stock baseline; and
  - stock fee `0.01` as a percentage of trade, normalized locally to 1 bp.
- The advanced-settings screenshot contains no bar/data-mode field and no
  slippage field.
- The exact linked shared conversation was read at
  `https://nexustrade.io/share/67e766ef84bd219ef060a689`.
  It exposes the prompts, description, and a failed initial Rebalance result,
  but no additional historical backtest mode or slippage configuration.
- The exact linked public portfolio was read at
  `https://nexustrade.io/shared-portfolio/67e7a4ad84bd219ef0619baf`.
  Its current public page marks exact rules and holdings as subscriber-only.
  No subscribe, purchase, copy, fork, or other workaround was attempted.
- The exact OOS result screenshot was visually inspected:
  `https://miro.medium.com/v2/resize:fit:1400/1*Iw4DlXOz2GYDyoN8Y-l2qQ.png`.
- Current generic NexusTrade backtesting documentation distinguishes
  `OHLC (Daily)` from minute-level `Intraday`:
  `https://nexustrade.io/docs/features/backtesting`.
- Current generic troubleshooting documentation says backtests assume exact
  execution price:
  `https://nexustrade.io/docs/faq/troubleshooting`.
- The generic current documentation is corroboration only. It is neither
  candidate-specific nor contemporaneous proof of the March 2025 run.
- Final candidate-specific source fields:
  - underlying bar/data mode: absent and unverified;
  - slippage assumption: absent and unverified.
- Monthly cadence, daily-looking indicators, generic current docs, and the
  absence of a slippage input in one screenshot were not used to infer
  `daily_ohlc` or `slippage_bps=0`.
- Client-rendering, subscriber-only obfuscation, and provider boundaries were
  respected without retry, purchase, or workaround.

No NexusTrade create, build, backtest, deploy, apply, fork, subscribe,
purchase, portfolio mutation, paper mutation, broker, order, or live tool was
called.

## Authentic candidate contract

- Strategy family: `Monthly Equal-Weight Dynamic Stock Filter`.
- Fixed universe:
  `AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, GS, JPM, BRK-B, COST`.
- Equal-weight only the stocks for which at least one and at most two of these
  source conditions are true:
  1. price is greater than its 30-day SMA;
  2. price divided by its 365-day minimum price is at most `1.05`; or
  3. the stock's 14-day RSI is below `28` while SPY's 14-day RSI is above
     `33`.
- The result screenshot also records constant-1 descending sort.
- The source state rule is:
  - at least 30 days since the last filled buy order across the universe; OR
  - at least 30 days since the last filled sell order across the universe.
- That filled-order state rule is not the current local factory's
  first-session-of-a-new-calendar-month helper and must not be substituted.
- Source training window: `2021-12-31` through `2024-03-24`.
- Untouched chronological OOS: `2024-03-24` through `2025-03-28`.
- Authentic warm-up semantics remain unverified. The source presents a
  52-week-low narrative and a 365-day minimum-price rule but does not establish
  whether that indicator uses calendar days or underlying bars. The absent
  historical bar mode prevents an authentic earliest warm-up boundary.
- The article and linked evidence name no authentic parent or ancestor.

## Source-metric trust

All external performance remains `untrusted_external_evidence`. It was not
used for local ranking or promotion.

The source training table displays:

- total return `37.59%`;
- Sharpe ratio `0.50`; and
- max drawdown `35.19%`.

The source OOS table displays:

- total return `29.64%`;
- Sharpe ratio `0.99`;
- Sortino ratio `1.11`;
- max drawdown `15.85%`;
- average drawdown `2.81%`; and
- 54 trades.

The same OOS screenshot's chart displays portfolio value `$12,963.80` but gain
`+$2,946.31 (29.41%)`. The `29.64%` table versus `29.41%` chart discrepancy
is preserved and unresolved. No external metric controlled a local outcome.

## Normalized generated evidence

Ignored evidence artifact:

`runs/v5_61_nexustrade_monthly_exact_gate/evidence_ledger.json`

- JSON schema version: `1`.
- Size: 7,271 bytes.
- SHA-256:
  `34729e0d6f140f9d8dddb4c8899de7f2f0998a9e76751350727f83650aea6cfe`.
- The ledger contains normalized public source facts and boolean capability
  state only. It contains no credential value, account identifier, broker
  payload, or raw authenticated provider response.

## Canonical adjusted-data gate

- The new worktree initially contained no `runs/` or `.data/` directory.
- Required combined canonical CSV:
  `runs/operator_input/multi_etf_adjusted_daily_canonical.csv`.
- That file is absent.
- The SPY-only Tiingo canonical path and latest normalized operator-input path
  are also absent.
- Zero canonical rows are available for:
  `AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, GS, JPM, BRK-B, COST, SPY`.
- All twelve symbols are missing across:
  - source training `2021-12-31`–`2024-03-24`;
  - untouched OOS `2024-03-24`–`2025-03-28`; and
  - the still-unverified authentic warm-up window.
- Therefore no coverage/session validation, local import, or canonical artifact
  hash can be produced.
- The local canonical loader requires exact columns
  `symbol,date,open,high,low,close,adjusted_close,volume`, ISO dates, positive
  Decimal prices, coherent OHLC, nonnegative integer volume, no duplicates,
  and no extra columns.
- The repository-approved adjusted provider path is the fixed-host HTTPS
  Tiingo GET adapter. It maps provider `adjClose` to canonical
  `adjusted_close`, loads only `TIINGO_API_KEY`, and is isolated from broker
  access.
- The local Tiingo adapter and multi-symbol manifest are intentionally limited
  to `SPY, QQQ, IWM, TLT, GLD`.
- The eleven candidate stocks are not accepted by that local adapter.
- Deterministic Tiingo mapping for `BRK-B` is not established.
- `TIINGO_API_KEY` loaded: `false`.
- No market-data credential was requested, exposed, connected, or placed in a
  command or artifact.
- No Tiingo fetch was attempted.
- The available Alpaca historical stock-bars connector contract was inspected.
  It exposes OHLCV, timeframe, dates, feed, currency, sort, and as-of fields,
  but no explicit split/dividend/all adjustment-selection parameter and no
  adjusted-close field.
- No Alpaca data call, broker call, order call, account call, or credential
  connection occurred.
- No unapproved vendor, synthetic corporate action, hand normalization, or
  cross-worktree generated artifact was used.

## V5.58, adapter, and pairing outcome

- V5.58 rerun: not performed.
- Reason: the objective permits rerun only after all source and data gates
  clear; both exact source fields and canonical data remain blocked.
- Monthly strategy-family adapter: not implemented.
- Exact source-window/warm-up adapter: not implemented.
- Standalone local replay: not run.
- Composite preregistration: not performed because the preregistration gate
  did not open.
- Composite local replay: not run.
- SPY baseline, exact chronological OOS, walk-forward, cost-sensitivity, and
  portfolio-level cross-asset gates: not run.
- No `preview_review` route was produced.
- No later no-submit shadow design is supported by this result.
- No parent metadata, pairing role, synthetic fills, invented costs,
  fabricated metrics, or fake lineage was represented as a composite.

If the gates later clear, the allowed preregistration remains a real
repository-supported composite such as parent
`spy_sma_50_200_baseline`, role `risk_regime_filter`, in which the exact source
eligible equal-weight stock set is held only while SPY SMA50 is above SMA200
and otherwise cash. It must change target weights and be replayed under the
same exact periods, costs, baseline, and portfolio-level cross-asset gates as
the standalone candidate.

## Credential, network, broker, and safety state

- `APP_PROFILE` loaded: `false`.
- `APP_PROFILE=paper`: `false`.
- Alpaca credential aliases loaded: `false`.
- Alpaca endpoint/account aliases loaded: `false`.
- Tiingo credential alias loaded: `false`.
- Raw NexusTrade credential aliases loaded: `false`.
- Paper integration flag loaded: `false`.
- Only boolean presence was inspected. No credential value, token, API key,
  account identifier, broker data, or response payload was requested, printed,
  copied, persisted, or returned.
- Network reads:
  - authenticated NexusTrade article discovery and article retrieval;
  - exact public article, embedded candidate screenshots, shared conversation,
    and public portfolio;
  - current official NexusTrade generic documentation; and
  - read-only Alpaca connector schema discovery.
- Repository tests and offline verification network access: `false`.
- Broker or broker credential-provider access: `false`.
- Paper submit/cancel/replace/close/liquidate or other mutation: none.
- Receipt status: not applicable.
- Reconciliation status: not required; no broker operation occurred.
- Live-authorized state: `false`.
- Live broker, live orders, live trading, and live capital remain prohibited.
- V5.57 sleeve ownership, reconciliation, auditing, and limits are unchanged:
  - `$25.00` maximum entry-order notional;
  - `$60.00` maximum aggregate marked SPY entry exposure;
  - one broker order per secure cycle; and
  - two sleeve intents per UTC day.
- No third sleeve was added.

## Verification

Credential/profile preflight before offline work:

- paper profile: `false`;
- broker credentials: `false`;
- Tiingo credential: `false`;
- raw NexusTrade credential: `false`;
- paper integration flag: `false`.

Focused command:

`python -m pytest tests/unit/test_nexustrade_strategy_intake.py tests/unit/test_strategy_challenger_factory.py tests/unit/test_etf_sma_local_bars_canonicalization.py tests/unit/test_spy_adjusted_data_refresh.py tests/unit/test_multi_etf_adjusted_data_manifest.py tests/unit/test_dependency_direction.py`

- 152 passed in 82.34 seconds.
- One initial short process-launch timeout produced no test result; the exact
  command was restarted once under a bounded resumable invocation and passed.

Mandatory `scripts/verify_offline.ps1`:

- 109 passed in 95.10 seconds.
- Result: `PASS`.
- The script explicitly skipped the full default suite.

Full default `python -m pytest`:

- 10,162 passed and 5 skipped in 2,312.02 seconds.
- Zero failures and zero errors.
- The five skips are credential-gated paper integration tests.

Final `git diff --check`, `git status --short`,
`git diff --name-only HEAD -- src`, and
`git ls-files --others --exclude-standard src tests` run after this handoff
update and before the local commit.

## Files and generated state

Tracked change:

- `docs/agent_context/active_implementation.md` only.

Ignored generated evidence:

- `runs/v5_61_nexustrade_monthly_exact_gate/evidence_ledger.json`.

There are no production `src` changes, no test changes, and no untracked
`src` or `tests` files.

## Next milestone

Resume this exact milestone only after both classes of gates are supplied
without credential disclosure:

1. candidate-specific authoritative NexusTrade evidence for the March 2025
   historical run's explicit bar/data mode and explicit slippage assumption;
2. an approved deterministic adjusted-daily acquisition/import path for
   AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, GS, JPM, BRK-B, COST, and SPY
   with provider-documented adjustment semantics, deterministic symbol mapping
   (especially `BRK-B`), complete source/OOS/authentic-warm-up coverage,
   session validation, and reproducible hashes.

Then rerun V5.58. Implement the smallest operational adapter only when the
candidate is blocked solely by local adapter requirements. Preserve the exact
filled-order 30-day state rule, exact train/OOS windows, and authentic warm-up.
Preregister and replay a genuine target-weight-changing composite under
identical local assumptions. Only a locally produced `preview_review` route
may support a later no-submit shadow design.
