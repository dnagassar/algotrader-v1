# V5.86 Clare risk-parity trend proxy preregistration

Status: frozen before candidate-specific URTH acquisition, implementation,
historical outcome inspection, or scoring. This document is authority for the
exact V5.86 experiment only. It grants no shadow, paper, broker, or
live-capital authority.

## Independent primary rationale and translation

The sole candidate is motivated by Clare, Seaton, Smith, and Thomas, *The
Trend Is Our Friend: Risk Parity, Momentum and Trend Following in Global Asset
Allocation* (Journal of Behavioral and Experimental Finance 9, 2016), DOI
<https://doi.org/10.1016/j.jbef.2016.01.002>. The authors evaluate five broad
asset classes, one-year inverse-volatility weights, and a 10-month moving
average trend filter that transfers a down-trending asset's weight to U.S.
Treasury bills.

The candidate ID is clare_five_asset_inverse_vol_10m_trend_proxy. It is a
tradable ETF proxy, not an index replication. The source uses MSCI World, MSCI
Emerging Markets, Citigroup World Government Bond, DJ-UBS Commodity, and
FTSE/EPRA Global REIT indices. It also mixes price, excess-return, and
total-return series for trend signals. V5.86 instead uses one consistent,
auditable split-and-dividend-adjusted ETF close per sleeve. BND is a U.S.
aggregate-bond proxy rather than a world-government-bond index, VNQ is U.S.
rather than global real estate, VWO and DBC track different investable index
families, and adjusted closes are not the source's mixed signal fields. No
source return, Sharpe, drawdown, alpha, or transaction-cost result controls a
gate or route.

This exact rule family has not been implemented or scored in the repository.
Previously closed trend, relative-strength, inverse-variance, and
style-momentum candidates remain closed and are not tuned or recombined here.

## Exact universe and data

Risky sleeves, in canonical order, are URTH,VWO,BND,DBC,VNQ. BIL is the
defensive sleeve. Baseline-only assets are SPY,IEF. All provider mappings are
identity mappings.

- Provider: authenticated Tiingo End-of-Day through the repository's GET-only,
  destination-allowlisted adapter.
- Exact URTH request: 2012-01-10 through 2026-07-31, inclusive.
- Existing pinned inputs may be reused only from the admitted V5.72, V5.73,
  V5.74, and V5.75 canonical artifacts; they may not be refreshed after the
  protocol is frozen.
- Provider field: adjClose, normalized as adjusted_close.
- Semantics: provider split- and dividend-adjusted close; not adjusted OHLCV,
  an executable fill, or a point-in-time corporate-action vintage.
- Required receipt: exact endpoints, symbol mappings, raw URTH response hash,
  normalized per-symbol hashes, one common-session intersection, combined
  canonical hash, row/session counts, and credential/network safety booleans.

An absent endpoint, missing symbol/session, duplicate, nonpositive value,
schema or mapping drift, cross-source value mismatch, or hash mismatch blocks
the experiment. Manual bars, hand normalization, broker data, synthetic
history, alternate providers, or symbol substitution are forbidden.

## Exact candidate rule

Signals form after the last common-session close of each calendar month t. For
each risky sleeve independently:

1. Sample its adjusted close on the last common session of each completed
   month.
2. Calculate the preceding 12 monthly total returns, including the return into
   month t; exactly 13 consecutive month-end levels are required.
3. Calculate sample standard deviation (n-1) of those 12 returns. A zero or
   nonfinite volatility is a hard failure.
4. Assign the pre-filter weight proportional to inverse volatility across all
   five risky sleeves, normalized to sum to one.
5. Calculate the arithmetic mean of the 10 month-end adjusted closes ending at
   t. A sleeve is risk-on only when its level at t is strictly greater than
   that mean.
6. Preserve each risk-on sleeve's pre-filter weight. Transfer each risk-off
   sleeve's full weight to BIL. Do not renormalize surviving risky sleeves.

The pending target trades at the next common-session close t+1, after the t to
t+1 return, pays turnover cost there, and first earns the t+1 to t+2 return.
The portfolio is long-only, unlevered, fully allocated, and re-forms monthly.
There is no parameter grid, optimization, volatility target, weight cap,
shorting, stop loss, intramonth override, discretionary exclusion, or second
candidate.

## Chronology

- Authentic warm-up/reference: 2012-01-10 through 2016-03-31.
- Post-publication historical OOS: 2016-04-01 through 2026-07-31.
- Fold 1: 2016-04-01 through 2019-09-30.
- Fold 2: 2019-10-01 through 2023-03-31.
- Fold 3: 2023-04-03 through 2026-07-31.

Every boundary must be an admitted common session. The signal formed after the
2016-03-31 close supplies the first pending OOS action. One continuous
holdings/equity path spans OOS; folds slice it and never reset holdings,
pending targets, costs, or equity. There is no half split, fold-local warm-up,
endpoint repair, or date exclusion.

## Holdings, costs, metrics, and controls

The portfolio starts OOS in implicit cash. The first transition is charged.
Between actions, holdings drift with asset returns. Immediately before a trade,
one-way turnover is 0.5 times the sum of absolute target-minus-drifted-weight
changes across every risky sleeve, BIL, and implicit cash. Costs are 0, 5, and
15 basis points per unit of one-way turnover; 5 bps is the decision tier and 15
bps is stress.

Required full/fold metrics are total and annualized return, annualized
volatility, zero-risk-free-rate Sharpe, maximum drawdown, turnover, risky
invested fraction, monthly action count, per-asset holding/contribution,
maximum risky target, and target divergence. Nonfinite values, nonpositive
equity, or contribution/reconciliation mismatch are hard failures.

Controls use identical sessions, lag, drift, initial transition, and costs:

1. inverse_volatility_no_trend, the closest ablation;
2. monthly equal weight across the five risky sleeves;
3. BIL buy and hold;
4. SPY buy and hold; and
5. monthly constant 60% SPY / 40% IEF.

The genuine portfolio test blends actual targets: 80% of the 60/40 parent plus
20% of actual candidate targets. Metadata-only pairing is invalid.

## Frozen terminal gates

At 5 bps the candidate must pass every gate:

1. annualized return is positive, Sharpe is at least 0.60, and maximum drawdown
   is at most 30%;
2. every fold has positive compounded return;
3. at 15 bps annualized return is positive and Sharpe is at least 0.50;
4. no fold supplies more than 70% of positive full-period compounded log
   return;
5. all hashes, chronology, lag, drift, cost, initial-transition, weight-sum,
   and contribution identities pass;
6. every risky sleeve receives positive weight at least once, at least three
   risky sleeves contribute positively, no risky target exceeds 60%, and no
   sleeve supplies more than 60% of total positive contribution; and
7. two complete replays produce byte-identical result and manifest bytes.

Against monthly equal weight, candidate Sharpe must improve by at least 0.05,
drawdown may be no more than 2 percentage points worse, and candidate Sharpe
must win in at least two folds.

Against inverse_volatility_no_trend, candidate Sharpe must improve by at least
0.05, maximum drawdown must improve by at least 10% relatively, annual return
drag may not exceed 1 percentage point, and candidate targets must diverge in
at least 12 monthly decisions.

The candidate must pass one SPY route:

- defensive: annualized return is no more than 1 percentage point below SPY,
  Sharpe improves by at least 0.10, and drawdown is at least 20% smaller; or
- growth: annualized return exceeds SPY by at least 1 percentage point, Sharpe
  is not below SPY, and drawdown is no more than 2 percentage points worse.

At 5 bps, the 80/20 composite versus the 60/40 parent must improve full Sharpe
by at least 0.02, reduce annualized return by no more than 0.75 percentage
point, improve drawdown or annualized return by at least 0.5 percentage point,
improve Sharpe in at least two folds, and have nonnegative fold-3 Sharpe
improvement. At 15 bps full composite Sharpe improvement must remain
nonnegative. No fold may supply more than 70% of positive full-period composite
log-return improvement.

Passing every gate routes only to
provisional_historical_validated_alpha_candidate and a newly fingerprinted,
current-clock no-submit forward shadow with no backfill. Any failure closes
this exact route without tuning, rescue, substitution, or relabeling. Only a
completed passing forward shadow may earn an unqualified validated-alpha
label.

## Safety

V5.86 is offline research. The only permitted network operation is the exact
URTH market-data GET. NexusTrade mutation, broker/account/order/position
access, paper mutation, and live activity are out of scope. Existing SPY sleeve
ownership, receipts, reconciliation, auditing, live prohibitions, and finite
paper caps remain unchanged and do not transfer to this candidate.