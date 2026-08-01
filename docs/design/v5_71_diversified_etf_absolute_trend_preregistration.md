# V5.71 Diversified ETF Absolute-Trend Preregistration

## Decision scope

V5.71 evaluates exactly one materially new alpha family: a long-or-cash,
monthly absolute-trend allocation across the repository-approved ETF proxy
universe `SPY`, `QQQ`, `IWM`, `TLT`, and `GLD`.

This protocol is outcome-blind. It must be committed before candidate-specific
market data are acquired or candidate returns are inspected. No parameter,
symbol, timing, cost, fold, benchmark, or gate variant may be added after that
inspection. The only terminal routes are `preview_review` and
`close_diversified_etf_absolute_trend`.

V5.71 is not part of the closed NexusTrade stock-filter family. It does not
reuse that family's eligibility rule, state machine, equity universe, source
metrics, pairing, or outcome evidence.

## Independent methodology evidence

The methodology lead is Mebane T. Faber, *A Quantitative Approach to Tactical
Asset Allocation*:

- SSRN: `https://papers.ssrn.com/sol3/papers.cfm?abstract_id=962461`
- author-hosted paper:
  `https://mebfaber.com/wp-content/uploads/2016/05/SSRN-id962461.pdf`
- repository review:
  `docs/design/phase33_broad_etf_faber_limited_formal_evidence_review.md`

The reviewed source supports only the following methodological building
blocks: monthly observations, an unoptimized 10-month simple moving average,
independent long-or-cash treatment, and equal sleeve weights. Source returns,
implementation claims, same-close fills, costs, cash returns, universe
validity, and performance figures are not admitted.

This is not an authentic Faber replication. The fixed repository proxy
universe contains three overlapping US-equity exposures plus long Treasuries
and gold; it does not reproduce the paper's five original asset-class index
series. All V5.71 results must retain the label
`repository_proxy_not_faber_replication`.

## Frozen universe and data contract

The universe and order are fixed:

1. `SPY` - broad US large-cap equity proxy
2. `QQQ` - US Nasdaq-100 equity proxy
3. `IWM` - US small-cap equity proxy
4. `TLT` - long-duration US Treasury ETF proxy
5. `GLD` - gold ETF proxy

No substitute, optional asset, survivorship replacement, pre-inception index,
or post-outcome deletion is allowed. Each symbol must map to itself.

The sole admissible market-data path is the existing authenticated Tiingo EOD
read-only adapter. The required field is Tiingo `adjClose`, normalized to
`adjusted_close`. It is treated as a split/dividend-adjusted price-return
input under the adapter's documented semantics; adjusted OHLCV, executable
fills, point-in-time corporate-action vintages, and a separately constructed
total-return series are not claimed.

Required contract:

- requested range: `2004-11-18` through `2026-07-31` inclusive;
- one unique positive adjusted close per symbol and session;
- strict ascending dates per symbol;
- all five symbols valid and nonempty;
- evaluation uses only the intersection of observed sessions across all five
  symbols;
- exact coverage, per-symbol hashes, row counts, common-session counts, field
  semantics, retrieval date, credential booleans, and combined-data hash must
  be recorded in a metadata-only receipt;
- the receipt must be committed before result computation;
- no manual CSV, hand-normalized bar, alternate provider, synthetic market
  data, or silent missing-session fill is permitted.

The endpoint `2026-07-31` is frozen even if later data become available.

## Frozen chronology

The complete chronology is fixed before data access:

- indicator warm-up: `2004-11-18` through `2005-08-31`;
- non-promotional reference/training window: `2005-09-01` through
  `2015-12-31`;
- untouched chronological OOS: `2016-01-04` through `2026-07-31`;
- OOS fold 1: `2016-01-04` through `2019-06-28`;
- OOS fold 2: `2019-07-01` through `2022-12-30`;
- OOS fold 3: `2023-01-03` through `2026-07-31`.

The folds must exactly partition every common OOS session without a gap or
overlap. Training results are descriptive only and cannot rank, tune, repair,
or promote the candidate.

## Frozen signal and action mechanics

For each calendar month, the observation session is the last common session
in that month. For each symbol:

1. Compute the arithmetic mean of exactly the most recent ten month-end
   `adjusted_close` observations, including the current observation.
2. Set the symbol's desired sleeve weight to `0.20` only when its current
   month-end adjusted close is strictly greater than that mean.
3. Set the sleeve weight to zero when the price is less than or equal to the
   mean or when ten month-end observations are unavailable.
4. Hold the residual portfolio weight as non-accruing cash.

The decision occurs only after the observation session's close. The target is
applied after the next common session's close, after that session's return and
the applicable modeled cost; the new target is effective for the following
close-to-close interval. This deliberate one-session lag forbids the source's
same-close signal/fill assumption.

Targets are reconsidered only after a month-end observation. No threshold,
buffer, stop, rank, volatility scaler, relative-momentum overlay, leverage,
shorting, dynamic universe, or intramonth rule is allowed.

## Frozen friction model

Costs are local stress assumptions, not source claims. Each rate is charged
against one-way portfolio weight turnover at the action close:

- zero: `0` basis points;
- moderate: `2` basis points (`1` fee plus `1` local slippage assumption);
- severe: `5` basis points (`1` fee plus `4` local slippage assumption).

Turnover is the sum of absolute target-weight changes, including cash entry
and exit through changes in risky weights. Market impact, taxes, borrow,
broker-specific charges, bid/ask histories, and executable fills are not
claimed.

## Frozen comparators

Two genuine comparators use the same common sessions, first eligible action
date, close-to-close return timing, and cost rates:

- `static_equal_weight`: monthly rebalanced `0.20` in each of the five ETFs;
- `spy_buy_and_hold`: `1.00` in SPY after the first eligible action and no
  later rebalance.

Cash accrues zero. This is a conservative local placeholder, not a T-bill,
risk-free, or realistic brokerage cash-return claim.

## Frozen metrics

For the candidate and both comparators, report for training, full OOS, and
each OOS fold:

- total and annualized return;
- annualized volatility and zero-cash Sharpe-like ratio;
- maximum drawdown;
- one-way turnover and annualized one-way turnover;
- invested-session fraction.

Also report OOS contribution by symbol, distinct symbols held, positive
contributors, and the largest absolute contribution share. Source performance
metrics cannot enter any calculation, ranking, or decision.

## Terminal gates

All gates are evaluated on the moderate-cost candidate unless explicitly
stated. Every gate must pass for `preview_review`.

### Data and replay integrity

- all five data contracts pass and all hashes match the committed receipt;
- chronology and folds match this protocol exactly;
- a second replay produces byte-identical preregistration, result, summary,
  and manifest artifacts.

### OOS viability

- full-OOS total return and annualized return are strictly positive;
- full-OOS maximum drawdown is no greater than `0.30`;
- every OOS fold has strictly positive total return;
- no OOS fold has maximum drawdown greater than `0.25`.

### Static-equal-weight value

The candidate must satisfy one of these two full-OOS paths:

- return-dominant: annualized-return delta is nonnegative, maximum-drawdown
  delta is no worse than `0.02`, and Sharpe delta is no worse than `-0.05`; or
- risk-dominant: annualized-return delta is at least `-0.02`, maximum drawdown
  improves by at least `0.05`, and Sharpe improves by at least `0.10`.

At least two of three OOS folds must have a nonnegative Sharpe delta versus
static equal weight.

### SPY value

Against SPY on full OOS, the candidate must have a nonnegative Sharpe delta,
a maximum-drawdown improvement of at least `0.05`, and an annualized-return
delta of at least `-0.03`.

### Friction stability

- severe-cost full-OOS total return remains strictly positive;
- severe-cost annualized return is no more than `0.005` below moderate cost;
- moderate-cost annualized one-way turnover is no greater than `4.0`.

### Diversification

- all five symbols are held at least once during OOS;
- at least three symbols have positive OOS contribution;
- no symbol exceeds `0.60` of total absolute OOS contribution.

## Terminal routing

If every gate passes, emit `preview_review`. That route authorizes only a
locally produced, no-submit design review. It does not authorize a paper
strategy, paper mutation, broker access, new sleeve, live activity, or capital.

If any required gate fails, emit
`close_diversified_etf_absolute_trend`. Failure closes this exact five-ETF,
10-month candidate. It cannot be repaired with another lookback, lag, cost,
symbol subset, cash proxy, threshold, or fold after outcome inspection.

Blocked data, provenance, credential-boundary, chronology, or reproducibility
evidence produces `blocked`, not a performance failure and not a promotion.

## Safety invariants

V5.71 is offline research after the bounded market-data acquisition step. It
must not access NexusTrade, brokers, accounts, orders, positions, or paper
state. It creates no third sleeve and changes no V5.57 execution ownership or
caps. Live remains unauthorized.
