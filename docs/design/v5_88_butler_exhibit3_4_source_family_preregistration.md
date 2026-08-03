# V5.88 Butler Exhibit 3/4 source-family preregistration

Status: frozen before any V5.88 candidate target, return, metric, gate, rank, or
route was computed. This is the preordered third source family after V5.86 and
V5.87 closed without tuning. The two candidates below are revealed atomically;
no later rescue, alternate lookback, universe substitution, or parameter search
is allowed. This document grants no shadow, paper, broker, or live authority.

## Primary evidence and claim boundary

The primary rule source is Adam Butler's May 10, 2012 author publication,
*Adaptive Asset Allocation: A True Revolution in Portfolio Management*,
<https://www.gestaltu.com/2012/05/adaptive-asset-allocation-a-true-revolution-in-portfolio-management.html/>, and
the official ReSolve paper, *Adaptive Asset Allocation: A Primer*,
<https://www.investresolve.com/inc/uploads/pdf/Adaptive-Asset-Allocation-Whitepaper.pdf>. The
author material defines a ten-asset global universe and two explicit building
blocks:

1. Exhibit 3 selects the top five assets by prior six-month performance each
   month and holds them at equal 20% weights.
2. Exhibit 4 selects the same top five, estimates each asset's daily volatility
   over the prior 60 days, sizes each to contribute the same 1% daily nominal
   risk, and caps total exposure at 100%.

Exhibit 5's minimum-variance optimizer is excluded because the public material
does not fully specify solver, covariance-window, bound, and degeneracy
semantics. V5.88 therefore does not claim to reproduce integrated or production
Adaptive Asset Allocation.

The original Exhibit 3/4 publication names asset classes rather than tickers.
The author's March 28, 2014 research disclosure,
<https://www.gestaltu.com/2014/03/half-life-of-optimal-lookback-horizon.html/>,
identifies the exact ten-ETF
research universe `DBC,EEM,EWJ,GLD,ICF,IEF,RWX,TLT,VGK,VTI`, back-extended in
the source research with index data. V5.88 uses those ETFs only, without the
source's unavailable pre-inception splices, and starts OOS after that mapping
was public. The candidate IDs are:

- `butler_exhibit3_top5_6m_equal_weight_proxy`;
- `butler_exhibit4_top5_6m_one_pct_volatility_proxy`.

All source performance is untrusted. No reported source return, Sharpe,
drawdown, trade count, cost, or chart value controls ranking or promotion.

## Exact data contract

Canonical candidate order is `DBC,EEM,EWJ,GLD,ICF,IEF,RWX,TLT,VGK,VTI`.
SPY is baseline-only. No cash ETF is introduced; unallocated Exhibit 4 exposure
is explicit zero-return cash.

- Provider: authenticated Tiingo End-of-Day through the repository's GET-only,
  destination-allowlisted adapter.
- Field: `adjClose` normalized to `adjusted_close`.
- Semantics: provider split- and dividend-adjusted close only.
- Exact common coverage: 2007-07-26 through 2026-07-31.
- Identity mappings only.
- Exact new requests: EEM, EWJ, ICF, RWX, and VGK, once each, for the exact
  coverage above.
- Reusable pinned symbols: DBC, GLD, IEF, TLT, VTI, and baseline SPY.
- Existing source-file SHA-256 values are respectively
  `8720fa2256e971ae5004b5fb92d095d699d122fe68d51f37d61a9665cb8054b1`,
  `1986eef43145ea6ae1f51cbc7decfb9d711bd740b18d207bd6ecc50a4e86f88e`,
  `091989173cb245146cfa2ffb88dcdf3e4f728a4e2ab753e191221b518596e56f`,
  `5ce0e67de4c1be5e5e85b292444bc5aac0ce937587a7fc60ca00e402f67dbfae`,
  `e8af3a7ea965e72861210be889b390b046684c1f82fff14f94274b453df1af47`,
  and
  `9ba2d58f5c1c58096fd473eaad1ea370e6023c63b524a21d286e4d5effaef5fb`.

The outcome-blind receipt must pin every source path and receipt, request and
refresh artifact, exact endpoint, row count, per-symbol and normalized-subset
hash, one identical ordered common-session sequence, combined canonical bytes,
and manifest bytes. Missing, duplicate, nonpositive, nonfinite, stale,
substituted, or session-mismatched rows block. Manual bars, hand normalization,
synthetic history, source back-extension, broker data, and alternate providers
are forbidden.

## Exact candidate rules

Signals form after the final common-session adjusted close of calendar month
t. Let t-6 be the final common-session close six completed calendar-month
intervals before t. Six-month return is
`adjusted_close(t) / adjusted_close(t-6) - 1`.

Rank all ten ETFs from highest return to lowest. Exact return ties receive
average ordinal ranks; the top-five cutoff and any final tie resolve by the
published author-universe order above. There is no skip month, absolute-return
filter, trend filter, cash substitution, optimizer, leverage, discretionary
override, or second lookback.

Exhibit 3 assigns exactly 20% to each selected ETF and zero to the other five.
It is fully invested.

Exhibit 4 uses the same selected set. For each selected ETF, calculate the 60
most recent daily simple adjusted-close returns ending at t and their sample
standard deviation (n-1). Raw weight is `0.01 / daily_standard_deviation`.
When raw weights sum above one, divide every raw weight by their sum; otherwise
retain the raw weights and hold the remainder as implicit zero-return cash.
This is the deterministic repository translation of equal 1% daily nominal-risk
contribution capped at 100% exposure. A nonpositive or nonfinite estimate
blocks.

The sources specify monthly formation for the next month but not an exact
execution price, tie convention, adjustment field, standard-deviation divisor,
cash yield, or slippage. V5.88 uses the explicit conventions above and trades
at the next common-session adjusted close t+1, after the t-to-t+1 return. The
new target first earns t+1-to-t+2. This is a close-only causal proxy, not a
source-fill replication.

## Chronology

- Warm-up/reference: 2007-07-26 through 2014-03-31.
- Conservative mapped historical OOS: 2014-04-01 through 2026-07-31.
- Fold 1: 2014-04-01 through 2018-05-31 (50 action months).
- Fold 2: 2018-06-01 through 2022-06-30 (49 action months).
- Fold 3: 2022-07-01 through 2026-07-31 (49 action months).

The March 31, 2014 signal supplies the first April 1 action. The receipt must
prove every session boundary and exact fold partition. One continuous path
spans OOS; folds never reset targets, holdings, cash, equity, or costs.

## Costs, controls, and genuine composite

Every portfolio starts in implicit cash and pays its initial transition.
Holdings drift between monthly actions. One-way turnover is half the absolute
target-minus-drifted-weight change across all eleven ETFs plus implicit cash.
Costs are 0, 5, and 15 basis points per unit of one-way turnover; 5 bps is the
decision cost and 15 bps is stress. These are repository assumptions, not
source claims.

Controls use identical sessions, lag, drift, cash, and costs:

1. `static_equal_ten_monthly`, the exact feature-removal ablation for Exhibit 3
   and static candidate-universe baseline;
2. `spy_buy_and_hold`; and
3. `spy_ief_60_40_monthly`.

Exhibit 3 is the closest ablation for Exhibit 4. The genuine portfolio test is
80% of actual monthly 60/40 parent targets plus 20% of actual candidate targets,
including any implicit cash. Metadata pairing is invalid.

## Frozen terminal gates

At 5 bps, each candidate must have positive annualized return, Sharpe at least
0.60, maximum drawdown no greater than 30%, and positive total return in every
fold. At 15 bps, annualized return must remain positive and Sharpe at least
0.50. No fold may supply more than 70% of positive full compounded log return.

Every candidate-universe ETF must be held, at least five must contribute
positively, and no sleeve may supply more than 60% of total positive
contribution. Exhibit 3 target weight may not exceed 20%; Exhibit 4 target
weight may not exceed 60% and total ETF exposure may not exceed 100%. All data,
lag, rank, volatility, target, drift, cash, turnover, contribution, fold, hash,
and nonpositive-equity checks must pass. Two complete replays must produce
byte-identical result and manifest bytes.

Both candidates must beat static equal ten by at least 0.05 Sharpe, have
maximum drawdown no more than 2 percentage points worse, win Sharpe in at least
two folds, and diverge on at least 12 monthly targets.

Exhibit 4 must also diverge from Exhibit 3 on at least 12 monthly targets and
add sizing value: either Sharpe improves by at least 0.03, or drawdown improves
by at least 5% relatively while annualized-return drag is no more than 1
percentage point.

Each candidate must pass one SPY route:

- defensive: annualized return no more than 1 point below SPY, Sharpe at least
  0.10 higher, and drawdown at least 20% smaller; or
- growth: annualized return at least 1 point above SPY, Sharpe not below SPY,
  and drawdown no more than 2 points worse.

At 5 bps each actual 80/20 composite versus 60/40 must improve full Sharpe by
at least 0.02, reduce annualized return by no more than 0.75 point, improve
drawdown or annualized return by at least 0.5 point, improve Sharpe in at least
two folds, and have nonnegative fold-3 Sharpe improvement. At 15 bps full
composite Sharpe improvement must be nonnegative. No fold may supply more than
70% of positive full composite log-return improvement.

Candidates are revealed atomically. If both pass, select exactly one by, in
order: higher 5-bps composite Sharpe improvement, higher standalone Sharpe,
higher annualized return, then candidate ID. A complete pass routes only to
`provisional_historical_validated_alpha_candidate` and a newly fingerprinted
current-clock no-submit shadow with no backfill. Failure closes the exact route
without tuning. Only a completed passing forward shadow can earn an unqualified
validated-alpha label.

## Safety

V5.88 is offline research plus the five exact authorized GET-only market-data
requests. NexusTrade mutation, broker/account/order/position access, paper
mutation, and live activity are forbidden. Existing paper sleeves,
reconciliation, receipts, finite caps, and live prohibitions remain unchanged.
