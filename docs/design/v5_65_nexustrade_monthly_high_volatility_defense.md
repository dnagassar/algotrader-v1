# V5.65 NexusTrade Monthly Independent High-Volatility Defense Preregistration

## Status and claim boundary

This protocol is preregistered before computing or inspecting any V5.65
strategy return, trade, allocation, contribution, or gate outcome from the
canonical bars.

V5.64 is frozen as a completed failed-promotion hypothesis. V5.65 does not
alter, tune, relabel, or replace the V5.64 protocol or artifacts. It evaluates
one separately named, mechanistically motivated risk overlay using the
repository's existing fixed no-lookahead volatility-regime convention.

This remains an independent local study inspired by the preserved public rules
for the NexusTrade `Monthly Equal-Weight Dynamic Stock Filter`. It is not an
authentic replay of the March 2025 NexusTrade historical run. It does not
resolve or infer that run's missing data mode, slippage assumption, indicator
warm-up clock, fill behavior, or lineage.

External performance metrics are untrusted. They cannot control ranking,
promotion, route selection, or any gate. The reported `29.64%` OOS table value
and `29.41%` chart value remain an unresolved source discrepancy.

The study is offline, research-only, no-submit, broker-free, credential-free,
and network-free. It cannot authorize paper or live activity.

## Fixed identity and hypothesis

- Protocol ID:
  `v5_65_nexustrade_monthly_independent_high_volatility_defense_v1`.
- Candidate ID:
  `nexustrade_monthly_independent_spy_sma_50_200_high_volatility_defense`.
- Frozen parent candidate ID:
  `nexustrade_monthly_independent_spy_sma_50_200_regime_filter`.
- Frozen source-rule candidate ID:
  `nexustrade_monthly_independent_daily_close_365_session`.
- Parent strategy ID:
  `spy_sma_50_200_baseline`.
- Pairing role:
  `volatility_regime_filter`.
- Baseline ID:
  `spy_sma_50_200_baseline`.
- Cross-asset comparator ID:
  `static_equal_weight_11_stock_buy_hold`.
- Output root:
  `runs/v5_65_nexustrade_monthly_high_volatility_defense`.

Fixed hypothesis:

> Adding the repository's fixed prior-only high-volatility cash gate to the
> frozen V5.64 SPY trend-regime composite may repair its full-OOS and fold
> drawdown excess without sacrificing more than two percentage points of
> moderate-cost full-OOS return, while retaining enough portfolio-level return
> to beat the static eleven-stock comparator in full OOS and every fixed fold.

No parameter fitting, threshold search, ranking, or selection is allowed.

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
- Required canonical CSV SHA-256:
  `d296138a95a86546bdc92678af479e8c8e204b138e2db43f54979a19921c9575`.
- Required V5.63 manifest SHA-256:
  `e204a8a1824e5b49ce4d457f12884bfc284d52f99ad3ba07072c978d7223d8e1`.
- Frozen V5.64 protocol:
  `docs/design/v5_64_nexustrade_monthly_independent_replication.md`.
- Required frozen V5.64 protocol SHA-256:
  `f24c98daa03462fccd0e73163abfe42f597ab601db83b331ecd4b487e31f4ee0`.
- Frozen V5.64 engine:
  `src/algotrader/research/nexustrade_monthly_independent_replication.py`.
- Required frozen V5.64 engine SHA-256:
  `66d73e4e0cd6160c8f07febe3a80b90eb4eebdd1ea7375b7fb3b23cadeef87f5`.

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

The simulation warms all indicators before training, starts portfolio
accounting on the first observed training session, carries holdings and filled
event state continuously into OOS, and never resets state at an evaluation
boundary. Window metrics rebase equity to `10000` but use the already-produced
continuous daily return path.

The three fixed, contiguous OOS reporting folds are:

1. `oos_walk_forward_1`: `2024-03-25` through `2024-07-24`, 84 sessions;
2. `oos_walk_forward_2`: `2024-07-25` through `2024-11-21`, 85 sessions;
3. `oos_walk_forward_3`: `2024-11-22` through `2025-03-28`, 85 sessions.

## Frozen source-rule, state, and fill mechanics

V5.65 reuses the frozen V5.64 mechanics without changing them:

- A stock is eligible when at least one and at most two are true:
  - adjusted close is above its 30-session SMA;
  - adjusted close divided by its 365-observed-session minimum is at most
    `1.05`;
  - stock RSI14 is below `28` and SPY RSI14 is above `33`.
- The eligible set is equal weighted.
- The constant sort value `1`, descending, does not alter the eligible set.
- The stateful rebalance rule is at least 30 calendar days since the last
  filled buy across the universe OR at least 30 calendar days since the last
  filled sell across the universe.
- A missing prior filled-event timestamp satisfies its elapsed-time condition.
- Signals use information through the current adjusted close.
- Targets fill at the next observed session's adjusted close.
- Same-close fills are prohibited.
- Weights drift between fills.
- Cash earns zero.
- Overlay-induced buys and sells update the candidate's own filled-event state.

The V5.64 disclosed interpretation of the 365-day minimum as 365 observed
sessions remains a local assumption, not an authentic source claim.

## Fixed high-volatility defense

The SPY volatility regime uses the existing repository-supported v2.18/v2.19
convention:

- Input: SPY adjusted-close simple daily returns.
- Realized volatility: sample standard deviation over the latest 20 returns,
  annualized by `sqrt(252)`.
- Threshold history: expanding prior realized-volatility observations only.
- Threshold method: nearest-rank quantiles.
- Minimum threshold history: 252 prior realized-volatility observations.
- Low quantile: `0.33`.
- High quantile: `0.67`.
- A session is `high_vol` when current realized volatility is greater than or
  equal to the prior-only high threshold.
- The current realized-volatility observation is excluded from its own
  thresholds.
- Future observations are excluded.
- `insufficient_history`, `low_vol`, and `normal_vol` do not force cash.

The candidate target is the frozen source-rule eligible equal-weight set only
when both conditions are true:

1. SPY SMA50 is greater than SPY SMA200; and
2. the current SPY volatility regime is not `high_vol`.

Otherwise the target is all cash. Trend or volatility-regime changes schedule
the changed target for the next observed close and update filled-event state
only when that fill occurs.

The overlay is genuine only if at least one OOS target vector differs from the
recomputed frozen V5.64 parent. Parent metadata without target-weight
differences fails integrity.

## Fixed comparators

All candidates and comparators use identical sessions, next-session-close
timing, portfolio accounting, costs, and windows.

- Frozen parent:
  recomputed V5.64 SPY SMA50/200 composite under the same input and costs.
- `spy_sma_50_200_baseline`:
  long SPY while SMA50 is greater than SMA200, otherwise cash.
- `static_equal_weight_11_stock_buy_hold`:
  equal weight all eleven stocks at the first observed training session, then
  allow weights to drift without discretionary rebalance.

No prior V5.64 result artifact supplies a V5.65 metric or gate value.

## Fixed cost sensitivity

Costs apply to one-way portfolio turnover:

`sum(abs(target_weight - pretrade_drifted_weight))`.

Equity after a fill is multiplied by:

`1 - turnover * (fee_bps + slippage_bps) / 10000`.

The four fixed cases remain:

1. `zero_cost`: fee `0` bps, slippage `0` bps;
2. `source_fee_only`: fee `1` bp, slippage `0` bps;
3. `low_friction`: fee `1` bp, slippage `1` bp;
4. `moderate_friction`: fee `1` bp, slippage `4` bps.

`source_fee_only` is the primary reporting case. `moderate_friction` is the
promotion-gate case. Zero base slippage remains a disclosed independent
assumption, not an authentic source claim.

## Fixed metrics

For training, full OOS, and every OOS fold, report:

- starting and ending equity;
- total and calendar-day annualized return;
- maximum drawdown;
- annualized sample volatility;
- zero-cash-rate Sharpe-like ratio;
- evaluated return count;
- one-way turnover;
- constituent buy and sell fill counts;
- invested-session percentage;
- high-volatility session count;
- high-volatility forced-cash session count.

Portfolio asset contributions and concentration use the same V5.64
portfolio-level definitions.

## Preregistered gates

### SPY baseline OOS gate

For full OOS and every fixed fold under `source_fee_only`:

- total-return delta versus SPY must be greater than `0`;
- maximum-drawdown delta versus SPY must be at most `0.01`;
- Sharpe delta versus SPY must be at least `-0.05` when both are available.

The gate passes only if all four windows pass.

### Cost gate

Under `moderate_friction`:

- full-OOS total return must be positive;
- full-OOS total-return delta versus SPY must be positive;
- a positive source-fee-only SPY edge must not become nonpositive; and
- source-fee-only to moderate-cost return degradation must be below `0.02`.

### Portfolio-level cross-asset gate

Under `moderate_friction`:

- full-OOS return must exceed the static equal-weight comparator;
- each fixed fold return must exceed that comparator;
- at least six stocks must have nonzero OOS target weight;
- at least four stocks must have positive aggregate OOS contribution;
- maximum single-stock absolute contribution share must be at most `0.50`.

The fold-two comparator requirement is not softened.

### Targeted parent-repair gate

Against the recomputed frozen V5.64 parent under `moderate_friction`:

- the candidate must have at least one different OOS target vector;
- full-OOS maximum drawdown must improve by at least `0.01`;
- maximum drawdown must not worsen in any fixed fold;
- full-OOS return delta must be at least `-0.02`;
- full-OOS Sharpe delta must be nonnegative when both are available;
- at least one OOS high-volatility session must force a parent-risk-on target
  to cash.

### Route

- `preview_review`: every applicable preregistered gate passes.
- `reject`: full-OOS return is nonpositive and the candidate fails the SPY
  baseline gate in all four OOS windows.
- `continue_local_research`: every other completed, valid result.
- `blocked`: input, provenance, coverage, deterministic replay, protocol-hash,
  or integrity validation fails.

No route permits paper promotion or submission. Only a locally produced
`preview_review` route may support a later separately authorized no-submit
shadow design.

## Output and safety contract

The implementation must write deterministic, secret-free ignored artifacts:

- `preregistration.json`;
- `defense_results.json`;
- `defense_summary.md`;
- `manifest.json`.

The preregistration artifact must include this tracked document's SHA-256 and
must be written before price loading or result computation. The manifest hashes
the other three outputs plus the canonical input and provenance manifest. Its
own hash is computed only after writing and is reported externally.

Every artifact must state:

- V5.64 is frozen;
- independent study, not authentic source replay;
- source metrics untrusted and unused;
- parameter search false;
- network, credential, broker, paper mutation, and live activity false;
- paper promotion and submission false;
- V5.57 sleeve ownership, reconciliation, auditing, and finite caps unchanged.
