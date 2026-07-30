# V5.64 NexusTrade Monthly Independent Replication Preregistration

## Status and claim boundary

This protocol is preregistered before computing or inspecting any strategy
return, trade, allocation, contribution, or gate outcome from the canonical
bars.

This is an independent local replication inspired by the preserved public
rules for the NexusTrade `Monthly Equal-Weight Dynamic Stock Filter`. It is not
an authentic replay of the March 2025 historical NexusTrade run. It does not
resolve or infer that run's missing data mode, slippage assumption, indicator
warm-up clock, fill behavior, or lineage.

External performance metrics are untrusted. They cannot control ranking,
promotion, route selection, or any gate. The reported `29.64%` OOS table value
and `29.41%` chart value remain an unresolved source discrepancy.

The replication is offline, research-only, no-submit, broker-free,
credential-free, and network-free. It cannot authorize paper or live activity.

## Fixed identities

- Protocol ID:
  `v5_64_nexustrade_monthly_independent_replication_v1`.
- Standalone candidate ID:
  `nexustrade_monthly_independent_daily_close_365_session`.
- Composite candidate ID:
  `nexustrade_monthly_independent_spy_sma_50_200_regime_filter`.
- Parent strategy ID:
  `spy_sma_50_200_baseline`.
- Composite role:
  `risk_regime_filter`.
- Baseline ID:
  `spy_sma_50_200_baseline`.
- Cross-asset comparator ID:
  `static_equal_weight_11_stock_buy_hold`.
- Output root:
  `runs/v5_64_nexustrade_monthly_independent_replication`.

## Fixed data contract

- Local input:
  `runs/operator_input/multi_etf_adjusted_daily_canonical.csv`.
- Data provenance manifest:
  `runs/v5_63_nexustrade_canonical_data/canonical_data_manifest.json`.
- Price field:
  `adjusted_close`, sourced from Tiingo EOD `adjClose`.
- Required common session range:
  `2019-01-02` through `2025-03-28`.
- Required stock universe:
  `AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, GS, JPM, BRK-B, COST`.
- Regime and baseline symbol:
  `SPY`.
- `BRK-B` provider mapping:
  `BRK-B->BRK-B`.
- Session reference:
  observed Tiingo SPY EOD dates. No independent exchange-calendar claim is
  made.
- All twelve symbols must share the exact session set and pass the V5.63
  canonical manifest before replay.

## Fixed chronological boundaries

- Indicator-only pretraining:
  `2019-01-02` through `2021-12-30`.
- Source-aligned training:
  `2021-12-31` through `2024-03-24`.
- Untouched chronological OOS:
  `2024-03-24` through `2025-03-28`.
- First observed OOS session:
  `2024-03-25`.
- Last observed OOS session:
  `2025-03-28`.
- OOS session count:
  `254`.

The simulation warms indicators before training, starts portfolio accounting
on the first observed training session, carries all holdings and filled-event
state continuously into OOS, and never resets state at an evaluation boundary.
Window metrics rebase equity to `10000` but use the already-produced continuous
daily return path.

The three fixed, contiguous OOS walk-forward reporting folds are:

1. `oos_walk_forward_1`: `2024-03-25` through `2024-07-24`, 84 sessions;
2. `oos_walk_forward_2`: `2024-07-25` through `2024-11-21`, 85 sessions;
3. `oos_walk_forward_3`: `2024-11-22` through `2025-03-28`, 85 sessions.

No parameter fitting, ranking, or selection occurs in any training or
walk-forward window.

## Preserved stock eligibility rules

For each stock, compute the following three Boolean conditions from information
available through the current signal session:

1. current adjusted close is greater than its 30-session simple moving average;
2. current adjusted close divided by its minimum adjusted close over the latest
   365 observed sessions is at most `1.05`;
3. the stock's 14-period RSI is below `28` and SPY's 14-period RSI is above
   `33`.

A stock is eligible only when at least one and at most two conditions are true.
An eligible set is equal weighted. A constant sort value of `1`, descending,
does not alter the set. If no stock is eligible, the target is cash.

The 30-session SMA includes the signal session. The 365-session minimum includes
the signal session. RSI uses the repository's simple rolling RSI convention:
the arithmetic mean of gains and losses over the latest 14 close-to-close
changes, RSI `50` when both are zero, and RSI `100` when average loss is zero.

The 365 observed-session interpretation is a disclosed local assumption. It is
not represented as the source's authentic warm-up clock.

## Stateful rebalance and fill model

The source rule is preserved as state, not replaced by first-session-of-month
logic:

`at least 30 calendar days since the last filled buy across the universe OR at
least 30 calendar days since the last filled sell across the universe`.

Fixed local mechanics:

- A missing prior filled-event timestamp satisfies its elapsed-time condition.
- The rule is evaluated every observed session after any pending fill is
  applied.
- A qualifying session computes a desired eligible equal-weight target.
- The desired target is filled at the next observed session's adjusted close.
- Signals never fill on the same close used to compute them.
- A weight increase greater than deterministic decimal tolerance is a filled
  buy; a weight decrease is a filled sell.
- Filled buy and sell dates are the actual next-session fill date.
- Rebalancing to the same post-return weights creates no fill and does not
  update filled-event state.
- Holdings drift with constituent returns between fills.
- Cash earns zero.
- No fractional-share, lot-size, liquidity, tax, borrow, or intraday model is
  claimed.

## Genuine paired composite

The composite maintains the same stock eligibility and filled-event state
machine. On each signal session:

- when SPY SMA50 is greater than SPY SMA200, its target is the current
  standalone eligible equal-weight target;
- otherwise its target is all cash.

SPY SMA50 and SMA200 include the signal session. The overlay target is filled
at the next observed session's adjusted close. All overlay-induced constituent
fills update the composite's own last-filled-buy and last-filled-sell state.

The composite is genuine only if at least one OOS session has target weights
different from the standalone. Parent metadata without target-weight
differences fails the composite-integrity gate.

## Fixed comparators

All candidates and comparators use identical sessions, next-session-close
timing, portfolio accounting, cost assumptions, and evaluation windows.

`spy_sma_50_200_baseline`:

- long SPY when SMA50 is greater than SMA200, otherwise cash;
- signal through the current close and fill at the next observed close;
- training-start portfolio accounting and continuous state into OOS.

`static_equal_weight_11_stock_buy_hold`:

- equal weight all eleven stocks at the first observed training session;
- no discretionary rebalance after entry;
- constituent weights drift with returns;
- cash is zero after entry.

## Fixed cost sensitivity

Costs apply to one-way portfolio turnover:

`sum(abs(target_weight - pretrade_drifted_weight))`.

Equity after a fill is multiplied by:

`1 - turnover * (fee_bps + slippage_bps) / 10000`.

All strategies and comparators use the same four cases:

1. `zero_cost`: fee `0` bps, slippage `0` bps;
2. `source_fee_only`: fee `1` bp, slippage `0` bps;
3. `low_friction`: fee `1` bp, slippage `1` bp;
4. `moderate_friction`: fee `1` bp, slippage `4` bps.

`source_fee_only` is the primary reporting case. `moderate_friction` is the
promotion-gate cost case. The zero-slippage primary case is a disclosed local
modeling assumption, not a claim about the source historical run.

## Fixed metrics

For training, full OOS, and every walk-forward fold, report:

- starting and ending equity;
- total return;
- calendar-day annualized return using `365.25`;
- maximum drawdown;
- annualized sample volatility using `sqrt(252)`;
- zero-cash-rate Sharpe-like annualized return divided by annualized
  volatility;
- evaluated session-return count;
- one-way turnover;
- constituent buy-fill and sell-fill counts;
- invested-session percentage.

Portfolio asset contributions are the sum of each constituent's pretrade
weight multiplied by its daily return. Contribution shares use absolute
contributions and are undefined only when aggregate absolute contribution is
zero.

## Preregistered gates

### Baseline OOS window gate

For a candidate to pass a window against the same-cost SPY SMA50/200 baseline:

- total-return delta must be greater than `0`;
- maximum-drawdown delta must be at most `0.01`; and
- Sharpe delta must be at least `-0.05` when both Sharpes are available.

The exact OOS gate passes only if the full OOS window and all three OOS
walk-forward folds pass under `source_fee_only`.

### Cost gate

The cost gate passes only if, under `moderate_friction`:

- full OOS total return is positive;
- full OOS total-return delta versus the same-cost SPY baseline is positive;
- the full OOS edge versus the SPY baseline does not change from positive under
  `source_fee_only` to nonpositive under `moderate_friction`; and
- the candidate's total-return degradation from `source_fee_only` to
  `moderate_friction` is less than `0.02`.

### Portfolio-level cross-asset gate

Under `moderate_friction`, the portfolio-level cross-asset gate passes only if:

- full OOS total return exceeds the same-cost static equal-weight eleven-stock
  comparator;
- each of the three OOS walk-forward fold returns exceeds that comparator;
- at least six of eleven stock symbols have nonzero OOS target weight on at
  least one session;
- at least four stock symbols have positive aggregate OOS return contribution;
  and
- no single stock exceeds `0.50` of aggregate absolute OOS contribution.

This gate evaluates the actual multi-stock portfolio. It does not relabel a
single-symbol replay as cross-asset evidence.

### Composite integrity and value gate

The composite passes only if:

- at least one OOS target vector differs from the standalone;
- all baseline OOS, cost, and portfolio-level cross-asset gates pass; and
- versus the standalone under `moderate_friction`, full OOS:
  - total-return delta is at least `-0.01`;
  - maximum-drawdown delta is at most `0.01`;
  - Sharpe delta is at least `-0.05` when available; and
  - at least one of total return, maximum drawdown, or Sharpe strictly improves.

### Route

- `preview_review`: every applicable preregistered gate passes.
- `reject`: full OOS return is nonpositive and the candidate fails the SPY
  baseline gate in all four OOS windows.
- `continue_local_research`: every other completed, valid result.
- `blocked`: input, provenance, coverage, deterministic replay, or integrity
  validation fails.

No route permits paper promotion or submission. Only a locally produced
`preview_review` route may support a later, separately authorized no-submit
shadow design.

## Output and safety contract

The implementation must write deterministic, secret-free ignored artifacts:

- `preregistration.json`;
- `replication_results.json`;
- `replication_summary.md`;
- `manifest.json`.

The preregistration artifact must include this tracked document's SHA-256 and
must be written before the result artifact. The manifest must hash the other
three output artifacts plus the canonical input and provenance manifest. The
manifest's own SHA-256 is computed and reported externally after it is written;
the manifest does not contain a self-referential hash.

Every artifact must state:

- independent replication, not authentic source replay;
- source metrics untrusted and unused;
- network, credential, broker, paper mutation, and live activity false;
- paper promotion and submission false;
- V5.57 sleeve ownership, reconciliation, auditing, and finite caps unchanged.
