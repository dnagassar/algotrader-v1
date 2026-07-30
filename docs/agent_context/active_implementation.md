# Active Implementation

## Ownership

- Writer: Codex, sole implementation writer for this working tree.
- Branch: `codex/v5.59-nexustrade-authentic-composite`.
- Expected V5.58 base:
  `021b55c10d17757d8ec865bf37de2e39f91da8e1`.
- Current pre-handoff HEAD:
  `8fc9c9d4d27c39f745f7a60f51e7f0a85ffafc73`.
- V5.59 reached a demonstrated authenticated-source hard gate. No production
  code, test, safety-contract, or paper-runtime file was changed.

## Takeover and authentication state

- The original checkout began detached at the exact expected V5.58 commit.
- Staged, unstaged, and untracked sets were empty before the feature branch was
  created.
- After the desktop restart that activated the provider, takeover was repeated:
  the branch and pre-handoff HEAD matched the values above, and staged,
  unstaged, and untracked sets were empty.
- The remote NexusTrade MCP OAuth connection is authenticated: `true`.
- A raw NexusTrade bearer-token environment variable is configured: `false`.
- `APP_PROFILE` is loaded: `false`; `APP_PROFILE=paper`: `false`.
- All checked Alpaca and NexusTrade credential aliases are loaded: `false`.
- Only boolean presence was inspected. No credential value, token, API key, or
  account identifier was requested, printed, copied, persisted, or returned.

## Authenticated read-only discovery

Safe read-only discovery through the OAuth provider covered:

- the authenticated draft portfolio list;
- deployed paper/live portfolio metadata without positions;
- bookmarks;
- the de-identified backtest corpus;
- public portfolios and creator profiles; and
- authoritative NexusTrade articles and their source screenshots.

The authenticated draft, deployed, and bookmarked portfolio lists contained no
candidate. A precise corpus search and a broader TQQQ corpus search found exact
rules and reported metrics, but the corpus records omitted at least cost
assumptions or explicit untouched-OOS evidence. One request for an exact
materialized corpus portfolio was rejected by the provider's anonymization
boundary; the rejection was accepted without retry or workaround.

No NexusTrade create, build, backtest, deploy, paper mutation, subscription,
purchase, write, broker, order, or live action occurred.

## Strongest authentic candidate

The strongest authoritative source is the founder-authored article:

`https://nexustrade.io/blog/this-strategy-has-beaten-the-market-for-over-5-years-heres-how-i-created-it-20250329`

Its fixed universe is AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, GS, JPM,
BRK-B, and COST. At an equal-weight monthly rebalance, each stock qualifies only
when exactly one or two of these conditions are true:

1. price is above its 30-day SMA;
2. price divided by its 365-day minimum price is at most 1.05; or
3. the stock's 14-day RSI is below 28 while SPY's 14-day RSI is above 33.

The source strategy screenshot also records:

- sorting by constant 1 descending;
- at least 30 days since the last filled buy for any universe stock OR at
  least 30 days since the last filled sell for any universe stock;
- a `$10,000` starting value; and
- SPY as the baseline.

The training backtest is `2021-12-31` through `2024-03-24`. Its screenshot
reports portfolio/baseline return `37.59%/13.06%`, Sharpe `0.50/0.27`,
Sortino `0.75/0.40`, maximum drawdown `35.19%/26.29%`, average drawdown
`13.30%/10.46%`, and 154 portfolio trades.

The untouched holdout is `2024-03-24` through `2025-03-28`. Its screenshot
reports portfolio/baseline return `29.64%/10.48%`, Sharpe `0.99/0.54`,
Sortino `1.11/0.62`, maximum drawdown `15.85%/10.04%`, average drawdown
`2.81%/1.87%`, and 54 portfolio trades. The same screenshot's chart displays
`+$2,946.31 (29.41%)`, conflicting with the `29.64%` metrics table. The intake
capture preserves the table metric and this handoff records the discrepancy;
all source performance remains untrusted.

The advanced-settings screenshot reports stock trading fee value `0.01` with
type `Percentage of Trade`, normalized in the intake as 1 bp. It does not
report a slippage assumption. Neither the article nor its screenshots
explicitly identify the underlying backtest bar mode. Day-based indicators do
not authorize inventing `daily_ohlc`.

## Machine-demonstrated intake gate

Ignored generated capture:

`runs/v5_59_nexustrade_authentic_candidate_gate/authenticated_monthly_dynamic_stock_filter_capture.json`

Credential-free V5.58 report:

`runs/v5_59_nexustrade_authentic_candidate_gate/authenticated_intake/nexustrade_intake_report.json`

The input SHA-256 is
`8cb555ec7412fe71340154b91f528663f08308b51cddc959ef3edde4af47df4b`.
The wrapper completed with:

- `eligible_candidate_count=0`;
- `local_replay_status=not_run_no_eligible_candidates`;
- route `repair_intake_blockers`;
- source metrics used for ranking: `false`;
- source metrics used for promotion: `false`;
- paper promotion allowed: `false`; and
- broker access, broker mutation, network access from the offline intake, and
  live mutation all `false`.

Exact blockers:

- `source_data_mode_missing`;
- `source_cost_assumptions_missing` because source slippage is absent;
- `local_timeframe_adapter_required`; and
- `local_strategy_family_adapter_required`.

The configured canonical input
`runs/operator_input/multi_etf_adjusted_daily_canonical.csv` is absent. No
current canonical bars are available for the eleven-stock universe plus SPY.

The candidate is not blocked solely by `needs_local_adapter`, so the V5.59
implementation rule prohibits a new family adapter. With no eligible
standalone candidate and no canonical data, an actual paired/lineage composite
cannot be replayed under identical chronological OOS, walk-forward,
cost-sensitivity, baseline, and cross-asset gates. No metadata-only pairing,
synthetic fills, invented costs, inferred bar mode, or fabricated performance
was created.

## Safety and unchanged operating contract

- Offline repository research only.
- OAuth NexusTrade network reads were read-only acquisition actions.
- The repository intake attempted no network access.
- No broker or broker credential provider was accessed.
- No paper submit, cancel, replace, close, liquidate, or other mutation
  occurred; receipt status is not applicable and no reconciliation event was
  required.
- V5.57 sleeve ownership, reconciliation, auditing, and finite limits remain
  unchanged: `$25.00` maximum entry-order notional, `$60.00` maximum aggregate
  marked SPY entry exposure, one broker order per secure cycle, and two sleeve
  intents per UTC session day.
- No third paper sleeve was added.
- Live mode, live broker access, live orders, and live capital remain
  prohibited and unauthorized.
- No `preview_review` route was produced.

## Verification

The production tree is unchanged from the tree verified for this milestone:

- focused V5.58 intake suite: 19 passed;
- dependency-direction suite: 44 passed;
- mandatory `scripts/verify_offline.ps1`: 109 passed; result `PASS`;
- full default suite, required because the script skipped it: 10,162 passed
  and 5 skipped in 3,026.01 seconds; zero failures and zero errors;
- verification was credential-free, network-free, and broker-free;
- `git diff --check`: passed;
- `git diff --name-only HEAD -- src`: empty; and
- `git ls-files --others --exclude-standard src tests`: empty.

## Files and generated state

Tracked change:

- `docs/agent_context/active_implementation.md` only.

Ignored generated evidence:

- `runs/v5_59_nexustrade_authentic_candidate_gate/`.

There are no production `src` changes and no untracked `src` or `tests` files.

## Next milestone

Resume V5.59 execution only after both exact missing inputs are available
without credential disclosure:

1. authoritative NexusTrade evidence identifying the source bar mode and
   slippage assumption for this exact candidate; and
2. current canonical adjusted daily bars covering AAPL, MSFT, GOOGL, AMZN,
   META, NVDA, TSLA, GS, JPM, BRK-B, COST, and SPY across the required
   training, untouched-OOS, walk-forward, and warm-up windows.

Re-run V5.58 first. Implement the smallest monthly cross-sectional family
adapter only if the authentic candidate is then blocked solely by
`needs_local_adapter`. The paired variant must combine the candidate with its
lineage or parent as an actual composite signal and be evaluated under the
same local gates. Only a locally produced `preview_review` route may proceed
to a later no-submit shadow design.
