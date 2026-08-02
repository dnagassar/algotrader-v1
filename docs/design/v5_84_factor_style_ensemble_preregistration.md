# V5.84 factor-momentum style proxy preregistration

Status: frozen before candidate-specific data acquisition, implementation,
historical outcome inspection, or ranking. This document is authority for the
exact V5.84 experiment only. It grants no shadow, paper, broker, or live-capital
authority.

## Independent primary rationale and scope

V5.84 tests whether momentum exists across tradable U.S. equity style proxies.
Its independent primary authorities are:

- Ehsani and Linnainmaa, *Factor Momentum and the Momentum Factor*, Journal of
  Finance 77 (2022), DOI <https://doi.org/10.1111/jofi.13131>; and
- Arnott, Kalesnik, and Linnainmaa, *Factor Momentum*, Review of Financial
  Studies 36 (2023), DOI <https://doi.org/10.1093/rfs/hhad006>.

The sources motivate time-series and cross-sectional factor momentum. The
repository implementation is a new tradable ETF proxy, not a replication of
the papers' latent factors, long-short portfolios, samples, or performance.

The price-momentum mechanisms overlap with previously closed V5.71/V5.75
research. That overlap is disclosed rather than renamed away. No prior result,
failed gate, source performance number, or Crypto Tournament V2 outcome selected
this universe, horizon, candidate, gate, or comparator. V5.84 uses newly
admitted candidate-specific bytes and fixed ex-ante rules, reports closest-rule
ablations, and makes only a provisional historical-validation claim. Only a
later current-clock no-submit shadow can provide genuinely new forward evidence.

## Exact universe

Risk/style proxies:

- `IWD`: U.S. large-cap value;
- `IWF`: U.S. large-cap growth;
- `RSP`: equal-weight S&P 500;
- `VBR`: U.S. small-cap value;
- `VIG`: U.S. dividend growth; and
- `SPLV`: U.S. low volatility.

Defensive sleeve: `SHY`. Baseline-only assets: `SPY` and `IEF`.

All mappings are identity mappings. The universe is fixed for the whole
experiment. No symbol may be added, removed, substituted, or selected after
acquisition. These funds are tradable proxies, not point-in-time factor-index
replications or survivorship-free constituent histories.

## Exact fixed candidates

Signals use only adjusted closes available through decision session `t` and
form after that close on the last common session of each calendar month. The
pending target trades at the following common-session close `t+1`, pays
turnover cost there, and first earns the `t+1` to `t+2` close-to-close return.
No target formed at `t` can affect the `t` to `t+1` return. Candidates,
ablations, comparators, and composites use this identical action lag. This is a
causal research convention, not an executable fill claim.

For every asset and integer lookback `L`:

- `R_L(t) = P(t) / P(t-L) - 1`, requiring exactly `L+1` closes;
- the only signal horizon is `L=252`; and
- ranking ties resolve by canonical ticker ascending.

### A. `style_factor_momentum_timeseries_12m`

Every risk/style proxy with `R_252(t) > 0` is eligible. If `n` proxies are
eligible, each receives `min(1/n, 0.35)`; SHY receives the residual. With no
eligible proxy, SHY receives 100%. This is a long/defensive time-series
factor-momentum proxy with a fixed 35% risk-sleeve concentration cap.

### B. `style_factor_momentum_cross_section_top2_12m`

Rank all six risk/style proxies by `R_252(t)`. Retain at most the top two whose
return is strictly positive. Each retained proxy receives 50%; if only one is
retained it receives 50%; SHY receives the residual. With no retained proxy,
SHY receives 100%.

### C. `style_factor_momentum_ensemble_50_50`

This is a genuine target-weight composite, not metadata pairing. Each monthly
target is exactly 50% of A's target plus 50% of B's target for every risk and
defensive sleeve.

There is no parameter grid, fitting, optimization, volatility sizing, moving
average, leverage, shorting, options, stop loss, intramonth rebalance, regime
override, discretionary exclusion, or fourth candidate.

## Closest-rule ablations and distinctness

The engine must report, under identical chronology and costs:

1. `static_equal_style_monthly`: monthly equal-weight targets across all six
   risk/style proxies;
2. `rank_only_top2_12m`: monthly 50/50 top-two targets without the positive
   return filter; and
3. `shy_buy_and_hold`.

A must be compared with static equal style. B must be compared with rank-only
top two, isolating the positive factor-momentum filter. C must be compared with
both components. Exact target-weight paths and the count of divergent monthly
decisions must be reported. B is ineligible if it never diverges from rank-only.
C is ineligible if it has fewer than 12 divergent monthly decisions from either
A or B. Ablations are controls only and can never be promoted.

A, B, C, and all controls are evaluated in one atomic terminal reveal. No
candidate or control result may be inspected sequentially and used to repair
another rule.

## Canonical data contract

- Provider: authenticated Tiingo End-of-Day through the repository's GET-only,
  destination-allowlisted adjusted-data adapter.
- Exact symbols: `IWD,IWF,RSP,VBR,VIG,SPLV,SHY,SPY,IEF`.
- Requested dates: `2011-05-05` through `2026-07-31`, inclusive.
- Provider field: `adjClose`, normalized as `adjusted_close`.
- Adjustment semantics: provider split- and dividend-adjusted close.
- Required output: one exact common-session intersection, deterministic
  per-symbol files, a combined canonical CSV, outcome-blind manifest,
  per-file SHA-256 bindings, and a committed data receipt.
- Hard failures: an absent exact requested endpoint, missing symbol, duplicate
  symbol/date, nonpositive or missing value, mapping drift, session mismatch,
  response/schema drift, or hash mismatch.
- Non-claims: adjusted OHLCV, executable fills, point-in-time corporate-action
  vintage, factor-index constituent history, or survivorship-free exposure.

The receipt must prove the exact first common session; the requested
`2011-05-05` start is not assumed admitted. Any missing endpoint blocks the
experiment rather than shifting chronology.

The adapter may be extended only with the six new style ETF identities and a
V5.84-specific acquisition/manifest wrapper. Credential values may not be
requested, displayed, logged, persisted, put in commands, or copied into
artifacts. Only `TIINGO_API_KEY` may cross the trusted provider boundary.
Manual CSV placement, hand normalization, broker data, and substitute providers
are forbidden.

## Frozen chronology

The engine uses the exact common-session intersection admitted by the receipt.

- Warm-up/reference: exact first common session through `2012-12-31`.
- Candidate-specific historical OOS: `2013-01-02` through
  `2026-07-31`.
- Fold 1: `2013-01-02` through `2016-12-30`.
- Fold 2: `2017-01-03` through `2020-12-31`.
- Fold 3: `2021-01-04` through `2026-07-31`.

Every boundary must be an admitted common session and every fold must be
nonempty. A 252-session return requires 253 authentic closes. No half split,
endpoint repair, backfill, future observation, or candidate-specific date
exclusion is permitted.

These dates are candidate-specific historical OOS because V5.84 settings and
bytes were not inspected before freezing. They are not described as globally
untouched future data. A passing result still requires a new current-clock
forward shadow.

## Holdings, drift, costs, and metrics

Every portfolio starts OOS in 100% implicit cash. The target formed from the
last warm-up month-end trades at the first OOS session close, pays its complete
initial transition cost, and first earns the next common session's return.

Between monthly actions, shares/holdings drift with asset returns and there is
no free daily rebalance. Immediately before a monthly trade, pre-trade weights
are the normalized drifted holdings. One-way turnover is
`0.5 * sum(abs(target_weight - pretrade_weight))` across every risk sleeve,
SHY, and implicit cash. After trading, cash is zero because targets sum to one.
Costs are 0, 5, and 15 basis points per unit of one-way turnover; 5 bps is the
decision tier and 15 bps is stress.

SPY and SHY buy-and-hold pay the initial transition and never rebalance.
Static equal style and constant 60% SPY / 40% IEF rebalance monthly using the
same drift, turnover, initial-cost, and timing rules. The 80/20 composite uses
80% of the monthly 60/40 parent target plus 20% of actual candidate targets,
then follows the same drift and cost accounting.

The complete holdings/action path runs continuously across OOS. Fold metrics
slice that path; folds never reset holdings, pending actions, equity, or costs.

Required metrics are total and annualized return, annualized volatility, Sharpe
with zero risk-free rate, maximum drawdown, annualized turnover, risk-asset
invested fraction, per-asset holding/contribution, monthly target divergence,
and full/fold metrics. Zero volatility, undefined Sharpe, nonfinite values, or
a nonpositive equity curve are hard gate failures.

## Exact comparators and portfolio composite

Comparators under identical candidate-specific OOS sessions are:

1. SPY buy and hold;
2. static equal weight of the six risk/style proxies, rebalanced monthly;
3. constant 60% SPY / 40% IEF, rebalanced monthly;
4. SHY buy and hold; and
5. the closest-rule ablations above.

The genuine portfolio composite is 80% of actual 60/40 parent targets plus 20%
of actual candidate targets. Metadata-only pairing is forbidden.

## Frozen terminal gates

Every candidate must pass all common gates at the 5-bps tier:

1. full annualized return positive, Sharpe at least 0.60, and maximum drawdown
   no greater than 30%;
2. every fold has positive compounded return;
3. 15-bps annualized return is positive and Sharpe at least 0.50;
4. no fold contributes more than 70% of full positive compounded log return;
5. all chronology, lag, drift, cost, initial transition, weight-sum, cap, and
   hash identities pass;
6. every risk/style proxy receives positive weight at least once; and
7. two canonical replays produce byte-identical result and manifest bytes.

Every candidate must pass the style-baseline gate:

- Sharpe exceeds static equal-style Sharpe by at least 0.05;
- maximum drawdown is no more than 2 percentage points worse; and
- at least two of three folds beat static equal style on Sharpe.

It must pass at least one preregistered SPY value route:

- defensive route: annualized return is no more than 1 percentage point below
  SPY, Sharpe exceeds SPY by at least 0.10, and maximum drawdown is at least 20%
  smaller relative to SPY; or
- growth route: annualized return exceeds SPY by at least 1 percentage point,
  Sharpe is not below SPY, and drawdown is no more than 2 percentage points
  worse.

Candidate B must additionally either improve Sharpe over rank-only top two by
at least 0.03 or reduce maximum drawdown by at least 5% relatively while
reducing annualized return by no more than 1 percentage point.

At 5 bps, the 80/20 composite must, versus the 60/40 parent:

1. improve full-period Sharpe by at least 0.02;
2. reduce annualized return by no more than 0.75 percentage point;
3. either improve maximum drawdown by at least 0.5 percentage point or improve
   annualized return by at least 0.5 percentage point;
4. have positive Sharpe improvement in at least two of three folds; and
5. have nonnegative Sharpe improvement in fold 3.

At 15 bps, full composite Sharpe improvement must remain nonnegative. No fold
may contribute more than 70% of positive full-period composite log-return
improvement. If full improvement is nonpositive, this last condition fails.

No source or prior performance metric controls ranking or promotion. A
candidate passing every gate is
`provisional_historical_validated_alpha_candidate`; otherwise its exact route
closes without tuning, rescue, or relabeling. If multiple candidates pass,
select at most one shadow winner by highest 5-bps composite Sharpe improvement,
then candidate Sharpe, annualized return, smaller drawdown, and canonical ID.

## Safety and downstream authority

V5.84 is offline research only. Data acquisition is market-data GET only.
NexusTrade mutation, broker/account/order/position access, paper mutation, and
live activity are out of scope.

A terminal winner is eligible only for a new current-clock no-submit shadow.
It is not paper-ready, live-ready, or guaranteed profitable. Strategy adapter,
candidate-owned sleeve, finite caps, orderability, fill/exit evidence,
independent reconciliation, aggregate risk, durable alert/recovery, M376
resolution, and later operator/live authority remain separate hard gates.
Existing V5.57 SPY limits do not transfer.
