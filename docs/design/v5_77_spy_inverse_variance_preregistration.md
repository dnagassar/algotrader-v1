# V5.77 SPY inverse-variance long/cash preregistration

Status: frozen before V5.77 data admission, implementation, or outcome
inspection. This family was recommended independently before V5.75 and V5.76
outcomes existed.

## Candidate and source

- Candidate ID: `spy_inverse_variance_long_cash_proxy`.
- Label: `repository_long_cash_proxy_not_moreira_muir_factor_replication`.
- Primary authority: Alan Moreira and Tyler Muir, *Volatility-Managed
  Portfolios*, Journal of Finance 72(4), 2017:
  <https://doi.org/10.1111/jofi.12513>.

The source scales next-period portfolio exposure inversely with prior realized
variance. The repository tests a capped long-only SPY/cash translation, not the
paper's uncapped factor portfolios. Source performance, fitted constants,
leverage, fills, costs, and effect sizes are untrusted and cannot enter a gate.

## Exact fixed rule

- Symbol: `SPY`; residual allocation is zero-return cash.
- Daily return: split/dividend-adjusted close total return.
- For each calendar month, calculate population variance from every daily SPY
  return ending in that month.
- Freeze `c` as the median of monthly population variances from `2004-12-01`
  through `2016-12-30`.
- Target next-month SPY weight is `min(1, c / prior_month_variance)`; cash
  weight is `1 - SPY weight`. A zero prior variance maps to weight 1.
- Form at the completed month-end and activate before the return ending on the
  first common session of the following month.
- Begin 2017 at 100% SPY until the first lagged January action; carry state and
  drift continuously into OOS and across folds.

No leverage, shorting, direction filter, volatility threshold, alternative
estimator, rolling calibration, target-volatility search, or parameter grid is
allowed.

## Data and chronology

- Provider: Tiingo EOD through the secure GET-only adjusted-data adapter.
- Field: `adjClose` to `adjusted_close`; split/dividend-adjusted close.
- Identity symbol: `SPY->SPY`.
- Required coverage: `2004-11-18` through `2026-07-31`.
- Reuse is allowed only after the V5.72 source, combined-data, manifest, and
  normalized SPY hashes validate.
- Manual/synthetic/broker data and execution-price or point-in-time-vintage
  claims are forbidden.

Frozen evaluation:

- calibration and state warm-up: `2004-11-18` through `2017-05-31`;
- untouched post-publication OOS: `2017-06-01` through `2026-07-31`;
- fold 1: `2017-06-01` through `2020-05-29`;
- fold 2: `2020-06-01` through `2023-05-31`;
- fold 3: `2023-06-01` through `2026-07-31`.

Boundaries must be exact sessions. Folds exactly partition OOS and no state
resets at a boundary. The calibration constant is computed once from only the
fixed pre-2017 months and is never revised.

## Costs, baseline, composite, and gates

- One-way turnover: `0.5 * sum(abs(target-prior))`, including cash.
- Cost tiers: 0, 5, and 15 bps; 5 bps decides and 15 bps stresses.
- Metrics use 252-session annualization and zero-risk-free daily Sharpe.
- Baseline: SPY buy and hold under identical sessions.
- Genuine composite: 80% static equal-weight
  `SPY,QQQ,IWM,TLT,GLD` core plus 20% actual candidate; candidate costs and
  turnover scale to 20%.

All common gates must pass:

1. two replays byte-identical;
2. full and every fold positive at 5 bps;
3. full Sharpe at least `0.75`;
4. 15-bps annualized return positive and no more than 1 point below 5 bps;
5. no fold supplies more than 70% of compounded log return;
6. exact calibration, month lag, capped weights, drift, costs, and metrics pass
   tests; and
7. source metrics are unused.

All candidate-specific gates must pass at 5 bps:

1. Sharpe exceeds SPY by at least `0.10`;
2. maximum drawdown improves on SPY by at least 20% relatively and at least 3
   percentage points absolutely;
3. annualized return trails SPY by no more than 2 percentage points;
4. at least two folds beat SPY on both Sharpe and maximum drawdown;
5. at 15 bps, annualized return remains positive and within 2 percentage
   points of the decision-cost return; and
6. OOS includes at least twelve distinct monthly target weights, at least one
   weight below 0.5, and no weight outside `[0,1]`.

All composite gates must pass:

1. Sharpe improves on the core by at least `0.02`;
2. annualized return is no more than 1 point lower; and
3. drawdown or annualized return improves by at least 0.5 point.

All gates passing yields `validated_alpha_candidate` and only new untouched
no-submit shadow eligibility. Failure closes the exact proxy without repair.
Outcome calculation is forbidden until protocol and metadata-only receipt are
committed. No strategy registration, broker access, paper mutation, or live
activity is authorized; live authorization remains false.
