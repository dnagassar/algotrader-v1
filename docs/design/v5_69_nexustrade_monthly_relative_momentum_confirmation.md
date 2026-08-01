# V5.69 Monthly Relative-Momentum Confirmation Preregistration

## Status and claim boundary

This protocol is committed before implementing or inspecting any V5.69
candidate return, trade, allocation, contribution, or gate outcome.

V5.69 is an independently designed, offline research candidate. It uses the
frozen V5.64 source-rule eligibility set as a building block and tests a
different security-selection thesis: medium-term absolute and SPY-relative
momentum may confirm which currently eligible stocks retain sufficient trend
strength to hold. It is not an authentic replay of the March 2025 NexusTrade
historical run and does not infer the missing historical bar mode, slippage,
365-day clock, fill behavior, or lineage.

V5.67 inverse-volatility sizing is closed and excluded. V5.65/V5.66 volatility
defense and attribution, V5.67/V5.68 sizing and attribution, constituent
outcomes, and retrospective symbol removal supply no V5.69 signal, parameter,
ranking, gate, or exception. V5.69 keeps equal weighting among selected names.

External performance metrics are untrusted and cannot control ranking,
promotion, or route selection. The source's `29.64%` table value versus
`29.41%` chart value remains an unresolved discrepancy.

The candidate is offline, credential-free, network-free, broker-free,
research-only, no-submit, and cannot itself authorize shadow, paper, or live
activity.

## Fixed identities and dependencies

- Protocol ID:
  `v5_69_nexustrade_monthly_relative_momentum_confirmation_v1`.
- Candidate ID:
  `nexustrade_monthly_independent_spy_regime_relative_momentum_confirmation`.
- Frozen parent candidate:
  `nexustrade_monthly_independent_spy_sma_50_200_regime_filter`.
- Parent role: `source_rule_and_spy_regime_parent`.
- Candidate role: `security_selection_confirmation`.
- SPY baseline: `spy_sma_50_200_baseline`.
- Cross-asset comparator: `static_equal_weight_11_stock_buy_hold`.
- Output root:
  `runs/v5_69_nexustrade_monthly_relative_momentum_confirmation`.

The implementation must fail closed unless all hashes match:

- V5.64 protocol:
  `docs/design/v5_64_nexustrade_monthly_independent_replication.md`.
- V5.64 protocol SHA-256:
  `f24c98daa03462fccd0e73163abfe42f597ab601db83b331ecd4b487e31f4ee0`.
- V5.64 engine:
  `src/algotrader/research/nexustrade_monthly_independent_replication.py`.
- V5.64 engine SHA-256:
  `66d73e4e0cd6160c8f07febe3a80b90eb4eebdd1ea7375b7fb3b23cadeef87f5`.
- V5.64 preregistration artifact SHA-256:
  `4c54d6c14de2579d1671a8257be6750bd49a586296d041fea95a3fe40e376e3c`.
- V5.64 result artifact SHA-256:
  `ca9f0177b0b42a3ec888b13799fdd3d39c5c5ae9caacedd2245a0292b42396da`.
- V5.64 summary artifact SHA-256:
  `af3b527db055c4568db7125047dad97ba9492fa55d5bbf2c3a6b6cc9002f41df`.
- V5.64 manifest artifact SHA-256:
  `96338ea291f40ea7d9a1ea4a0d45dd17ed5a60c856333150655701f64841dcf6`.
- V5.68 exclusion protocol:
  `docs/design/v5_68_nexustrade_risk_balanced_attribution.md`.
- V5.68 exclusion protocol SHA-256:
  `d0d89a0807cf8db41cb7377a40b6af1342625b4ff32fc8e56f53b5f2d9ec5513`.

Before V5.69 results are written, the engine must recompute the complete frozen
V5.64 preregistration, result, and summary and require exact equality with the
pinned artifacts. No V5.65-V5.68 result artifact is a candidate input.

## Fixed data and chronology

- Local input:
  `runs/operator_input/multi_etf_adjusted_daily_canonical.csv`.
- Provenance manifest:
  `runs/v5_63_nexustrade_canonical_data/canonical_data_manifest.json`.
- Canonical CSV SHA-256:
  `d296138a95a86546bdc92678af479e8c8e204b138e2db43f54979a19921c9575`.
- Canonical manifest SHA-256:
  `e204a8a1824e5b49ce4d457f12884bfc284d52f99ad3ba07072c978d7223d8e1`.
- Price: Tiingo EOD `adjClose` mapped to `adjusted_close`.
- Adjustment semantics: split/dividend-adjusted EOD price; adjusted OHLCV is
  not claimed.
- Stock universe:
  `AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, GS, JPM, BRK-B, COST`.
- Regime/comparator symbol: `SPY`.
- BRK-B mapping: `BRK-B->BRK-B`.
- Common observed Tiingo SPY sessions: 1,569 from 2019-01-02 through
  2025-03-28, with 18,828 symbol rows.
- No independent exchange-calendar claim is made.

Chronology is frozen to V5.64:

- indicator-only pretraining: 2019-01-02 through 2021-12-30;
- training: 2021-12-31 through 2024-03-24;
- untouched OOS boundary: 2024-03-24 through 2025-03-28;
- first observed OOS session: 2024-03-25;
- OOS count: 254 sessions;
- fold 1: 2024-03-25 through 2024-07-24, 84 sessions;
- fold 2: 2024-07-25 through 2024-11-21, 85 sessions; and
- fold 3: 2024-11-22 through 2025-03-28, 85 sessions.

Indicators warm before training. Portfolio state, holdings, pending fills, and
filled-event timestamps run continuously from training through OOS and never
reset at a reporting boundary.

## Frozen source-rule and regime building blocks

V5.69 first computes the exact V5.64 stock-eligibility set. For each stock:

1. adjusted close is above its 30-session SMA;
2. adjusted close divided by its 365-observed-session minimum is at most 1.05;
3. stock RSI14 is below 28 and SPY RSI14 is above 33.

A stock is source-rule eligible only when exactly one or two clauses are true.
All indicator definitions, inclusive windows, and simple RSI semantics remain
frozen to V5.64.

The parent SPY regime is also unchanged: risk-on only when SPY adjusted-close
SMA50 is strictly above SMA200; risk-off target is cash.

## Independent relative-momentum selection

The only candidate change is the following deterministic selection rule:

1. On a source-rule rebalance signal, calculate 126-observed-session simple
   total return for each source-rule eligible stock and SPY as
   `current_adjusted_close / adjusted_close_126_sessions_ago - 1`.
2. Retain an eligible stock only when its 126-session return is strictly
   positive and strictly greater than SPY's 126-session return.
3. Rank retained stocks by descending excess return over SPY.
4. Break an exact score tie by the frozen canonical stock-symbol order.
5. Select at most the first five stocks.
6. Equal weight the selected stocks to total exposure 1. If none qualify, hold
   cash.

The lookback is exactly 126 observed sessions and the maximum selected count is
exactly five. There is no skip-month, volatility weighting, weight cap beyond
equal weighting, leverage, shorting, parameter sweep, training fit, optimizer,
covariance estimate, constituent exclusion, or fallback target.

## State, fills, accounting, and costs

V5.69 preserves V5.64's stateful rebalance rule:

`at least 30 calendar days since the candidate's last filled buy OR at least
30 calendar days since the candidate's last filled sell`.

The candidate owns its filled-event state. Missing timestamps satisfy their
respective condition. Signals use information through the current adjusted
close and fill at the next observed adjusted close. Filled increases update
last buy; filled decreases update last sell. Holdings drift between fills.
SPY regime transitions may independently schedule a next-session target and
their fills update the same candidate state. Cash returns zero.

All candidates and comparators use the four frozen V5.64 cost cases and the
same one-way-turnover cost model:

- `zero_cost`: 0 bp fee, 0 bp slippage;
- `source_fee_only`: 1 bp fee, 0 bp slippage;
- `low_friction`: 1 bp fee, 1 bp slippage; and
- `moderate_friction`: 1 bp fee, 4 bp slippage.

The zero-slippage primary case is a disclosed local assumption, not a claim
about the source run.

## Fixed reporting

For training, full OOS, and each fold under every cost, report the complete
V5.64 portfolio metrics, target-vector hashes, turnover, fills, exposure,
constituent gross-return contributions, held-symbol breadth, positive
contributors, and maximum absolute contribution share.

Candidate integrity additionally reports OOS target differences from the
frozen parent, selection counts, maximum selected count, nonpositive-momentum
violations, SPY-relative-momentum violations, ranking violations, and
equal-weight/exposure violations.

## Preregistered gates

### SPY baseline and cost gates

The exact V5.64 baseline and cost gates apply. Under `source_fee_only`, full
OOS and all three folds must beat the same-cost SPY SMA50/200 total return,
have maximum-drawdown delta at most 0.01, and Sharpe delta at least -0.05.
Under `moderate_friction`, full OOS return and SPY edge must remain positive,
the source-fee edge must not break, and return degradation must be below 0.02.

### Portfolio-level cross-asset gate

Under `moderate_friction`, candidate return must exceed static eleven-stock
equal weight in full OOS and every fold; at least six distinct stocks must have
nonzero candidate target weight during OOS; at least four stocks must make
positive aggregate OOS gross contribution; and no stock may exceed 0.50 of
aggregate absolute OOS contribution.

### Independent selection-value gate

Under `moderate_friction`, all of the following are required:

- at least one OOS desired target differs from the frozen V5.64 parent;
- every selected target satisfies the fixed momentum, ranking, maximum-count,
  equal-weight, exposure, and canonical tie-break contract;
- full-OOS return delta versus the frozen parent is strictly positive;
- candidate return is no worse than the parent in at least two of three folds;
- no fold return delta versus the parent is below -0.02;
- full-OOS maximum-drawdown delta versus the parent is at most 0.01;
- full-OOS Sharpe delta versus the parent is nonnegative when defined;
- one-way-turnover delta versus the parent is at most 2.0; and
- maximum absolute contribution share is at most 0.50.

### Route

- `preview_review`: every baseline, cost, cross-asset, integrity, and
  selection-value gate passes.
- `reject`: full OOS return is nonpositive and every SPY baseline OOS window
  fails.
- `continue_local_research`: every other complete, valid outcome.
- `blocked`: provenance, hash, coverage, reproduction, deterministic replay,
  or integrity validation fails.

No route permits submission or paper promotion. `preview_review` could only
support a later, separately authorized, locally produced no-submit shadow
design.

## Determinism and safety

Write deterministic, secret-free ignored artifacts only:

- `preregistration.json`;
- `relative_momentum_results.json`;
- `relative_momentum_summary.md`; and
- `manifest.json`.

The preregistration artifact is written before candidate results. The manifest
hashes the other three artifacts, canonical input, and provenance manifest.
A second replay must be byte-identical.

Every artifact states that source metrics are untrusted and unused; network,
NexusTrade access/mutation, credential use, broker access, paper mutation, and
live activity are false; and submission/paper promotion are false.

V5.57 sleeve ownership, receipt/reconciliation/audit boundaries, live
prohibitions, and caps remain unchanged: $25 entry-order notional, $60
aggregate marked SPY entry exposure, one broker order per secure cycle, and
two sleeve intents per UTC day. No third sleeve is added.
