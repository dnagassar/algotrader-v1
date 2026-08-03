# V5.87 Keller flexible asset allocation preregistration

Status: corrected and re-frozen before candidate-specific performance
inspection or scoring. The first committed draft and data snapshot used
SPY/DBC availability proxies; late primary-source verification showed that the
paper explicitly supplies VTI/GSG ETF mappings. That unscored snapshot is
superseded. The exact VTI/GSG contract below controls V5.87. V5.87 was the
pre-ordered second candidate; V5.86 outcomes did not select or alter its rule.
This document grants no shadow, paper, broker, or live-capital authority.

## Primary source and repository translation

The sole candidate is Keller and van Putten, *Generalized Momentum and Flexible
Asset Allocation (FAA): An Heuristic Approach*, dated December 24, 2012 and
posted on SSRN December 25, 2012, DOI
<https://doi.org/10.2139/ssrn.2193735>. The primary paper specifies a
seven-fund universe, a four-month lookback, monthly selection of three equal
sleeves, and a combined loss rank using return, volatility, and correlation.
It uses weights 1.0, 0.5, and 0.5 respectively and replaces a selected fund
whose four-month return is negative with its short-Treasury cash proxy.

The candidate ID is keller_faa_ravc_4m_top3_proxy. The exact candidate
universe is the paper's own ETF mapping: VTI,VEA,VWO,SHY,BND,GSG,VNQ.
Adjusted closes replace the source's unspecified daily closing-price
adjustment convention. No source performance metric, optimized variant,
leverage result, or transaction-cost result controls a gate.

Previously closed relative-strength, dual-momentum, VAA, Faber, factor-style,
and Clare routes remain closed. No parameter from those outcomes is reused or
tuned. This new externally specified rule may earn only provisional historical
validation until new current-clock observations accrue.

## Exact data contract

Candidate and cash universe: VTI,VEA,VWO,SHY,BND,GSG,VNQ. Baseline-only
symbols: SPY,IEF. Canonical symbol order is
VTI,VEA,VWO,SHY,BND,GSG,VNQ,SPY,IEF.

- Provider: authenticated Tiingo End-of-Day through the repository's GET-only,
  destination-allowlisted adapter.
- Exact new requests: VTI and GSG from 2007-07-26 through 2026-07-31.
- VEA,VWO,SHY,BND,VNQ,SPY,IEF may be reused only from pinned V5.72, V5.74,
  and V5.75 canonical evidence.
- Provider field: adjClose normalized to adjusted_close.
- Semantics: provider split- and dividend-adjusted close.
- Exact coverage request for the V5.87 assembly: 2007-07-26 through
  2026-07-31.
- All mappings are identity mappings.
- No request beyond the two exact VTI/GSG GETs, manual bar, hand normalization,
  synthetic history, broker data, alternate provider, or symbol substitution
  is allowed.

The outcome-blind receipt must pin every source, the imported receipts,
per-symbol hashes, one identical common-session sequence, combined canonical
bytes, and safety booleans. Missing or duplicate sessions, nonpositive values,
mapping or schema drift, hash mismatch, or endpoint mismatch blocks.

## Exact fixed rule

Signals form after the last common-session close of each calendar month t.

1. Let t-4 be the last common-session close of the calendar month four
   completed month-end intervals before t.
2. For each of the seven candidate symbols, four-month return is
   adjusted_close(t) / adjusted_close(t-4) - 1.
3. For each symbol, calculate daily simple adjusted-close returns strictly
   after t-4 through t. Volatility is their sample standard deviation (n-1).
4. Calculate the sample Pearson correlation for every pair over those identical
   daily returns. A symbol's correlation measure is its arithmetic mean
   correlation with the other six symbols. Daily correlation frequency is a
   preregistered inference from the paper's daily dataset and common
   four-month factor window; the paper does not restate the frequency in its
   correlation section.
5. Assign ranks 1 through 7 with higher return better, volatility ranks with
   lower volatility better, and correlation ranks with lower average
   correlation better. Exact factor ties receive their average ordinal rank.
6. Score each symbol as return_rank + 0.5 * volatility_rank + 0.5 *
   correlation_rank. Lower score is better; final equal-score ties resolve by
   the paper's published ETF order VTI,VEA,VWO,SHY,BND,GSG,VNQ. The paper does
   not specify ties; these are deterministic repository conventions.
7. Select the three lowest-score symbols. Each owns exactly one third.
8. For each selected symbol whose four-month return is strictly negative,
   transfer its full one-third sleeve to SHY. Zero return is not negative.
   Multiple transfers accumulate in SHY.

The source trades at the next month's first-session open. Because the
admitted consistent adjusted field is close-only, this repository translation
trades at the next common-session close t+1, after the t-to-t+1 return, pays
turnover cost there, and first earns t+1-to-t+2. It is not an exact source-fill
replication. The target is long-only, unlevered, and fully allocated. There is
no parameter grid, optimizer, covariance
shrinkage, leverage, volatility target, alternate score weight, top count,
lookback, tie rule, discretionary override, or second candidate.

## Chronology

- Warm-up/reference: 2007-07-26 through 2013-01-31.
- Post-publication historical OOS: 2013-02-01 through 2026-07-31.
- Fold 1: 2013-02-01 through 2017-06-30.
- Fold 2: 2017-07-03 through 2022-01-03.
- Fold 3: 2022-01-04 through 2026-07-31.

Every boundary must be an admitted common session. The signal formed after the
2013-01-31 month-end close supplies the exact first OOS action on 2013-02-01.
One continuous path spans OOS; folds never reset holdings, actions, equity, or
costs.

## Holdings, costs, metrics, and controls

Every portfolio starts OOS in implicit cash and pays its full initial
transition. Holdings drift between monthly actions. One-way turnover is half
the absolute target-minus-drifted-weight change across all eight symbols and
implicit cash. Costs are 0, 5, and 15 basis points per unit of one-way
turnover; 5 bps is decision and 15 bps stress.

Required full/fold metrics are total and annualized return, annualized
volatility, zero-rate Sharpe, maximum drawdown, turnover, risky exposure,
actions, per-asset holding/contribution, target concentration, and divergence.
Nonfinite metrics, nonpositive equity, or contribution mismatch block.

Controls use identical chronology, drift, and costs:

1. relative_absolute_momentum_top3_4m: rank by four-month return only, select
   top three, equal weight, and apply the identical negative-return SHY
   substitution;
2. static_equal_seven_monthly;
3. SHY buy and hold;
4. SPY buy and hold; and
5. monthly constant 60% SPY / 40% IEF.

The genuine portfolio test is 80% of actual 60/40 parent targets plus 20% of
actual candidate targets. Metadata pairing is invalid.

## Frozen terminal gates

At 5 bps the candidate must pass every common gate:

1. annualized return positive, Sharpe at least 0.60, and maximum drawdown no
   greater than 30%;
2. every fold total return positive;
3. at 15 bps annualized return positive and Sharpe at least 0.50;
4. no fold supplies more than 70% of positive full compounded log return;
5. every non-cash asset is held, at least three non-cash assets contribute
   positively, no non-cash target exceeds one third, and no sleeve supplies
   more than 60% of total positive contribution;
6. all data, lag, rank, correlation, weight, drift, cost, contribution, and
   fold identities pass; and
7. two complete replays produce byte-identical results and manifests.

Against static equal seven, Sharpe must improve by at least 0.05, drawdown may
be no more than 2 percentage points worse, and Sharpe must win in at least two
folds.

Against relative_absolute_momentum_top3_4m, targets must diverge on at least 12
monthly decisions and the RAVC factors must add value: either Sharpe improves
by at least 0.03, or drawdown improves by at least 5% relatively while annual
return drag is no more than 1 percentage point.

The candidate must pass one SPY route:

- defensive: annual return no more than 1 point below SPY, Sharpe at least 0.10
  higher, and drawdown at least 20% smaller; or
- growth: annual return at least 1 point above SPY, Sharpe not below SPY, and
  drawdown no more than 2 points worse.

At 5 bps the 80/20 composite versus 60/40 must improve full Sharpe by at least
0.02, reduce annual return by no more than 0.75 point, improve drawdown or
annual return by at least 0.5 point, improve Sharpe in at least two folds, and
have nonnegative fold-3 Sharpe improvement. At 15 bps full composite Sharpe
improvement must be nonnegative. No fold may supply more than 70% of positive
full composite log-return improvement.

A complete pass routes only to
provisional_historical_validated_alpha_candidate and a newly fingerprinted
current-clock no-submit shadow with no backfill. Any failure closes the exact
route without tuning, rescue, substitution, or relabeling. Only a completed
passing forward shadow may earn an unqualified validated-alpha label.

## Safety

V5.87 is offline, network-free research. NexusTrade mutation,
broker/account/order/position access, paper mutation, and live activity are out
of scope. Existing paper sleeves, reconciliation, receipts, live prohibitions,
and finite caps remain unchanged and do not transfer.