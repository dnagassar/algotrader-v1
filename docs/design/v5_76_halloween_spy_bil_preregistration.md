# V5.76 Halloween SPY/BIL preregistration

Status: frozen before V5.76 data admission, implementation, or outcome
inspection. This family was recommended independently before V5.74 and V5.75
outcomes existed.

## Candidate and source

- Candidate ID: `halloween_spy_bil_seasonal_proxy`.
- Label: `repository_spy_bil_proxy_not_country_index_replication`.
- Primary authority: Sven Bouman and Ben Jacobsen, *The Halloween Indicator,
  "Sell in May and Go Away": Another Puzzle*, American Economic Review 92(5),
  2002: <https://doi.org/10.1257/000282802762024683>.
- Later fixed-hypothesis evidence: Cherry Y. Zhang and Ben Jacobsen, *The
  Halloween indicator, "Sell in May and Go Away": Everywhere and all the
  time*, Journal of International Money and Finance 110, 2021:
  <https://doi.org/10.1016/j.jimonfin.2020.102268>.

The published anomaly distinguishes the November-April and May-October
half-years. The repository tests a simple investable U.S. ETF proxy. Source
performance, fills, costs, historical index lineage, and any published effect
size are untrusted and cannot enter a gate.

## Exact fixed rule

- Symbols: `SPY` and `BIL`.
- Hold 100% SPY for returns ending on every common session in November through
  April.
- Hold 100% BIL for returns ending on every common session in May through
  October.
- Switch before the close-to-close return ending on the first common session
  of May and November. The calendar is known in advance; no same-close signal
  inference or price input exists.
- Begin the admitted history in BIL because June 2007 lies in the May-October
  half-year. Carry state continuously into OOS and across folds.

No alternate switch day, month optimization, hemisphere change, cash
substitution, trend filter, leverage, shorting, or parameter search is allowed.

## Data and chronology

- Provider: Tiingo EOD through the secure GET-only adjusted-data adapter.
- Field: `adjClose` to `adjusted_close`; split/dividend-adjusted close.
- Identity symbols: `SPY,BIL`.
- Required common coverage: `2007-06-01` through `2026-07-31`.
- Reuse is allowed only after the V5.72 SPY and V5.73 BIL source and normalized
  hashes validate.
- Manual/synthetic/broker data and execution-price or point-in-time-vintage
  claims are forbidden.

Frozen evaluation:

- reference/state warm-up: `2007-06-01` through `2007-12-31`;
- full OOS: `2008-01-02` through `2026-07-31`;
- fold 1: `2008-01-02` through `2013-12-31`;
- fold 2: `2014-01-02` through `2019-12-31`;
- fold 3: `2020-01-02` through `2026-07-31`;
- explicit post-2021 publication slice: `2021-01-04` through `2026-07-31`.

Boundaries must be exact common sessions. Folds exactly partition OOS and no
state resets at a boundary.

## Costs, baselines, composite, and gates

- One-way turnover: `0.5 * sum(abs(target-prior))`, including cash.
- Cost tiers: 0, 5, and 15 bps; 5 bps decides and 15 bps stresses.
- Metrics use 252-session annualization and zero-risk-free daily Sharpe.
- Baselines: SPY buy and hold, BIL buy and hold, and a zero-cost 50/50 SPY/BIL
  portfolio rebalanced on the first common session of every calendar year and
  otherwise allowed to drift.
- Genuine composite: 80% static equal-weight
  `SPY,QQQ,IWM,TLT,GLD` core plus 20% actual candidate; candidate costs and
  turnover scale to 20%.

All common gates must pass:

1. two replays byte-identical;
2. full and every fold positive at 5 bps;
3. full Sharpe at least `0.75`;
4. 15-bps annualized return positive and no more than 1 point below 5 bps;
5. no fold supplies more than 70% of compounded log return;
6. exact calendar state, switches, drift, costs, and metrics pass tests; and
7. source metrics are unused.

All candidate-specific gates must pass at 5 bps:

1. annualized return exceeds annual-rebalanced 50/50 by at least 1 point;
2. Sharpe exceeds both annual-rebalanced 50/50 and SPY by at least `0.10`;
3. drawdown improves on SPY by at least 10 points and is no more than 2 points
   worse than annual-rebalanced 50/50;
4. at least two folds beat annual-rebalanced 50/50 on both total return and
   Sharpe;
5. the post-2021 slice has positive total return and beats annual-rebalanced
   50/50 on total return;
6. at 15 bps, annualized return is positive and remains above
   annual-rebalanced 50/50; and
7. both SPY and BIL are actually held in OOS.

All composite gates must pass:

1. Sharpe improves on the core by at least `0.02`;
2. annualized return is no more than 1 point lower; and
3. drawdown or annualized return improves by at least 0.5 point.

All gates passing yields `validated_alpha_candidate` and only new untouched
no-submit shadow eligibility. Failure closes the exact proxy without repair.
Outcome calculation is forbidden until protocol and metadata-only receipt are
committed. No strategy registration, broker access, paper mutation, or live
activity is authorized; live authorization remains false.
