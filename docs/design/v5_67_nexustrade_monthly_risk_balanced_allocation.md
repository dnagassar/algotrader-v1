# V5.67 NexusTrade-Inspired Monthly Risk-Balanced Allocation

Status: outcome-blind preregistration. This file must be committed before the
V5.67 candidate is implemented or replayed against canonical outcomes.

Protocol ID:
`v5_67_nexustrade_monthly_risk_balanced_allocation_v1`.

## Claim and purpose

V5.67 is an independently designed, offline research candidate that uses the
publicly described NexusTrade stock-filter idea as a building block. It is not
an authentic NexusTrade replay, does not claim NexusTrade lineage, and does not
resolve the missing candidate-specific historical bar mode, slippage, or
365-day-clock evidence.

The fixed thesis is that inverse-volatility sizing plus an explicit per-name
cap can reduce concentration and drawdown in the successful V5.64 SPY-trend
composite without materially sacrificing return, Sharpe ratio, or transaction
cost robustness. V5.67 removes the failed V5.65 binary high-volatility cash
overlay; no V5.65 or V5.66 parameter, regime, counterfactual, or inspected
outcome is reused as a V5.67 signal.

Candidate ID:
`nexustrade_monthly_independent_spy_sma_50_200_inverse_volatility_capped`.

Frozen parent candidate:
`nexustrade_monthly_independent_spy_sma_50_200_regime_filter`.

Candidate role: `risk_balanced_portfolio_construction`.

No parameter sweep, threshold search, outcome-driven retry, or alternative
weighting rule is permitted. Training results are reported but do not select
parameters. OOS outcomes may be inspected only after this protocol is
committed.

## Frozen inputs and lineage boundary

The implementation must fail closed unless all hashes match:

- V5.64 protocol:
  `docs/design/v5_64_nexustrade_monthly_independent_replication.md`, SHA-256
  `f24c98daa03462fccd0e73163abfe42f597ab601db83b331ecd4b487e31f4ee0`.
- V5.64 engine:
  `src/algotrader/research/nexustrade_monthly_independent_replication.py`,
  SHA-256
  `66d73e4e0cd6160c8f07febe3a80b90eb4eebdd1ea7375b7fb3b23cadeef87f5`.
- V5.64 preregistration artifact SHA-256:
  `4c54d6c14de2579d1671a8257be6750bd49a586296d041fea95a3fe40e376e3c`.
- V5.64 result artifact SHA-256:
  `ca9f0177b0b42a3ec888b13799fdd3d39c5c5ae9caacedd2245a0292b42396da`.
- V5.64 summary artifact SHA-256:
  `af3b527db055c4568db7125047dad97ba9492fa55d5bbf2c3a6b6cc9002f41df`.
- V5.64 manifest artifact SHA-256:
  `96338ea291f40ea7d9a1ea4a0d45dd17ed5a60c856333150655701f64841dcf6`.
- Canonical adjusted-daily CSV:
  `runs/operator_input/multi_etf_adjusted_daily_canonical.csv`, SHA-256
  `d296138a95a86546bdc92678af479e8c8e204b138e2db43f54979a19921c9575`.
- V5.63 provenance manifest:
  `runs/v5_63_nexustrade_canonical_data/canonical_data_manifest.json`, SHA-256
  `e204a8a1824e5b49ce4d457f12884bfc284d52f99ad3ba07072c978d7223d8e1`.
- V5.66 explanatory protocol, used only to freeze the excluded failed-overlay
  lane:
  `docs/design/v5_66_nexustrade_high_volatility_attribution.md`, SHA-256
  `2a2d03030b2ec74ca3a0682ca94163ea5b28218c1b452b4f10664fc182733227`.

The replay must recompute the frozen V5.64 result and require exact structured
equality with the pinned V5.64 result artifact before writing V5.67 results.
It must also verify every pinned artifact hash. This reproduction check is a
prerequisite, not a performance gate.

## Canonical data contract

Provider and provenance remain the approved V5.63 Tiingo EOD acquisition.
The only price field is `adjusted_close`, normalized from Tiingo `adjClose`.
The field is split-and-dividend adjusted. Adjusted OHLCV is not claimed.

Symbols, in canonical order:

`AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, GS, JPM, BRK-B, COST, SPY`.

The deterministic class-share mapping is `BRK-B->BRK-B`. Required coverage is
`2019-01-02` through `2025-03-28`, with exactly 1,569 common observed sessions
per symbol and 18,828 total rows. Observed Tiingo SPY EOD dates are the session
reference; an independent official exchange calendar is not claimed.

No network acquisition, manual bar fabrication, hand normalization, broker
data, or credential-bearing process is part of V5.67.

## Frozen source-rule building block

The stock universe is the eleven non-SPY symbols above. On an eligible
rebalance signal close, a stock passes when exactly one or two of these three
clauses are true:

1. current adjusted close is strictly above the 30-observed-session simple
   moving average, including the current session;
2. current adjusted close divided by the minimum adjusted close over the last
   365 observed sessions, including the current session, is at most `1.05`;
3. the stock's 14-close-change simple RSI is strictly below `28` and SPY's
   corresponding RSI is strictly above `33`.

RSI uses arithmetic mean gains and losses, not Wilder smoothing. The frozen
V5.64 adjusted-daily and 365-observed-session choices remain explicit local
assumptions, not facts attributed to NexusTrade.

The stateful rebalance rule is unchanged: a new source-rule target may be
formed when at least 30 calendar days have elapsed since the candidate's last
filled buy **or** at least 30 calendar days have elapsed since its last filled
sell. A missing filled-event timestamp satisfies its corresponding elapsed
condition. The state is updated only by actual filled buy/sell weight changes.
There is no first-session-of-calendar-month substitution and no reset at
train, OOS, or fold boundaries.

## Fixed risk-balanced allocation

The only intentional change from the frozen V5.64 composite is the sizing of
stocks that pass the source-rule building block.

For each passing stock on the signal close:

1. compute 60 simple adjusted-close returns from exactly 61 consecutive
   observed sessions ending on the signal session;
2. compute the sample standard deviation with denominator `59`;
3. require the standard deviation to be finite and strictly positive; missing,
   non-finite, or nonpositive volatility fails the replay closed; and
4. set the raw allocation score to the reciprocal of that standard deviation.

No volatility floor, annualization, shrinkage, covariance estimate, leverage,
or forecast scaling is used.

The per-symbol target-weight cap is exactly `0.20`. The portfolio's maximum
stock exposure is `min(1, 0.20 * N)`, where `N` is the number of passing
stocks. Thus fewer than five passing stocks deliberately leaves residual cash.

Weights are produced by deterministic capped proportional water-filling:

1. start with the maximum stock exposure as remaining allocation mass;
2. allocate the mass in proportion to reciprocal-volatility scores;
3. simultaneously fix every provisional weight strictly above `0.20` at the
   cap, subtract those fixed weights, and repeat across the remaining symbols;
4. when no provisional weight exceeds the cap, accept the proportional
   weights; and
5. emit weights in canonical symbol order, with zero for every nonpassing
   stock and cash equal to one minus total stock exposure.

Exact Decimal arithmetic and canonical symbol order resolve equality and
serialization. No discretionary residual assignment or alternate tie-break is
allowed. Every target must be nonnegative, total stock exposure must not exceed
one, and no stock weight may exceed `0.20` beyond the frozen `1e-18` validation
tolerance.

## SPY trend parent, fills, and state

The frozen SPY parent remains `SPY SMA50 > SMA200` on adjusted closes. When the
condition is false, the stock target is all cash. A parent-regime transition
and an eligible source-rule rebalance each schedule the applicable target for
the next observed session.

Signals use the current session adjusted close. All initial allocation,
rebalances, and parent-regime transitions fill at the next observed session's
adjusted close. Same-close fills are forbidden. Between fills, weights drift
with adjusted-close returns. Cash return is zero.

Candidate buy and sell fills update the candidate's own 30-calendar-day state.
Changing weights may therefore change later state dates relative to the frozen
equal-weight parent; that is part of the preregistered operational candidate,
not a reason to transplant parent state.

## Chronology and costs

State is simulated continuously from the training start through the final OOS
session.

- Training: `2021-12-31` through `2024-03-24`.
- Untouched OOS: boundary `2024-03-24` through `2025-03-28`; first observed OOS
  session `2024-03-25`; exactly 254 observed sessions.
- Fold one: `2024-03-25` through `2024-07-24`, 84 sessions.
- Fold two: `2024-07-25` through `2024-11-21`, 85 sessions.
- Fold three: `2024-11-22` through `2025-03-28`, 85 sessions.

Folds are reporting slices only. State, positions, and equity are not reset at
fold boundaries.

The four fixed one-way turnover cost cases are unchanged:

- `zero_cost`: fee `0` bps, slippage `0` bps;
- `source_fee_only`: fee `1` bp, local slippage assumption `0` bps;
- `low_friction`: fee `1` bp, local slippage assumption `1` bp; and
- `moderate_friction`: fee `1` bp, local slippage assumption `4` bps.

These are local assumptions. The word `source` in `source_fee_only` refers only
to the evidenced one-basis-point stock fee and does not authenticate a
historical NexusTrade slippage setting.

## Fixed comparators and gates

The replay must include the frozen V5.64 composite parent, the repository SPY
SMA50/200 baseline, and static equal-weight buy-and-hold across the eleven
stocks under identical sessions and costs.

All four baseline windows mean full OOS plus all three folds.

### Baseline OOS gate

At `source_fee_only`, every baseline window must satisfy all of:

- candidate total-return delta versus SPY SMA50/200 is strictly positive;
- candidate maximum-drawdown delta versus SPY is at most `0.01`; and
- candidate Sharpe-ratio delta versus SPY is at least `-0.05` when both are
  defined.

### Cost gate

For full OOS at `moderate_friction`:

- candidate total return is strictly positive;
- candidate return edge over SPY SMA50/200 is strictly positive;
- a positive `source_fee_only` SPY edge is not broken; and
- candidate return degradation from `source_fee_only` is strictly below
  `0.02`.

### Portfolio-level cross-asset gate

At `moderate_friction`:

- the candidate must strictly outperform static eleven-stock equal-weight
  buy-and-hold in full OOS and all three folds;
- at least six stocks must receive a nonzero OOS target;
- at least four stocks must have positive full-OOS arithmetic gross
  contribution; and
- the largest absolute full-OOS constituent-contribution share must be at most
  `0.50`.

### Targeted risk-balance gate

At `moderate_friction`, all of the following must pass:

- at least one OOS desired-target vector differs from the frozen parent;
- every OOS candidate desired target respects the `0.20` per-stock cap and the
  total-exposure contract;
- full-OOS maximum drawdown improves versus the frozen parent by at least
  `0.01`;
- candidate maximum drawdown is no worse than the frozen parent in each of the
  three folds;
- full-OOS total-return delta versus the frozen parent is at least `-0.02`;
- full-OOS Sharpe-ratio delta versus the frozen parent is nonnegative when both
  are defined;
- full-OOS one-way-turnover delta versus the frozen parent is at most `2.0`;
  and
- the candidate's largest absolute full-OOS constituent-contribution share is
  at most `0.35` and no greater than the frozen parent's share.

### Routing

`preview_review` requires every applicable gate above. A preview route supports
only a later, separately authorized no-submit shadow design. It does not permit
paper or live promotion.

If full-OOS `source_fee_only` return is nonpositive and all four SPY baseline
windows fail, route `reject`. Otherwise a failed gate routes
`continue_local_research`. No failed result may trigger a parameter change or
same-milestone retry.

## Artifact and safety contract

The local ignored output root is
`runs/v5_67_nexustrade_monthly_risk_balanced_allocation` and contains exactly:

- `preregistration.json`;
- `risk_balanced_results.json`;
- `risk_balanced_summary.md`; and
- `manifest.json`.

Artifacts must be deterministic, hashed, offline, and contain no credentials,
account identifiers, broker payloads, or external performance controls.
External performance remains `untrusted_external_evidence`; the `29.64%` table
versus `29.41%` chart discrepancy is preserved and cannot control ranking,
gating, routing, or promotion.

V5.67 performs no NexusTrade access or mutation, market-data network access,
broker/account/order/position access, paper mutation, third-sleeve creation, or
live activity. V5.57 sleeve ownership, reconciliation, auditing, live
prohibitions, and caps remain unchanged: `$25` maximum entry-order notional,
`$60` maximum aggregate marked SPY entry exposure, one broker order per secure
cycle, and two sleeve intents per UTC day.
