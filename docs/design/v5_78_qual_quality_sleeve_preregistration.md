# V5.78 static QUAL quality-sleeve preregistration

Status: frozen before V5.78 data acquisition, implementation, or outcome
inspection. This family was recommended independently before V5.75-V5.77
outcomes existed.

## Candidate and source

- Candidate ID: `static_qual_quality_sleeve_proxy`.
- Label: `investable_sector_neutral_quality_etf_not_qmj_replication`.
- Academic authority: Cliff Asness, Andrea Frazzini, and Lasse Heje Pedersen,
  *Quality Minus Junk*, Review of Accounting Studies 24, 2019:
  <https://doi.org/10.1007/s11142-018-9470-2>.
- Investable vehicle authority: iShares MSCI USA Quality Factor ETF:
  <https://www.ishares.com/us/products/256101/ishares-msci-usa-quality-factor-etf>.

The fund seeks to track the MSCI USA Sector Neutral Quality Index, using high
return on equity, stable earnings, and low debt. The repository evaluates the
fund as an investable long-only quality sleeve. It does not reconstruct
point-in-time fundamentals or claim to replicate the academic long-short QMJ
factor. Source/fund performance, fills, fees outside adjusted prices, and
effect sizes are untrusted and cannot enter a gate.

## Exact fixed rule

- Hold 100% `QUAL` throughout OOS.
- Apply one 5-bps entry cost before the return ending on the first OOS session;
  apply one 15-bps entry cost in the stress replay.
- No local fundamental reconstruction, security selection, rebalance rule,
  trend overlay, alternative quality ETF, leverage, shorting, exit, or
  parameter search is allowed.

Fund expenses, constituent changes, and internal turnover are embedded only to
the extent they appear in provider adjusted-close total returns.

## Data and chronology

- Provider: Tiingo EOD through the secure GET-only adjusted-data adapter.
- Field: `adjClose` to `adjusted_close`; split/dividend-adjusted close.
- Identity symbols: `QUAL,PBUS,SPY`.
- Requested common coverage: `2019-01-02` through `2026-07-31`.
- SPY may be reused only after its V5.72 hashes validate. QUAL and PBUS must be
  newly acquired after this protocol is committed.
- Manual/synthetic/broker data and execution-price, fundamentals-vintage, or
  index-reconstruction claims are forbidden.

Frozen evaluation:

- reference/coverage check: `2019-01-02` through `2019-12-31`;
- untouched OOS: `2020-01-02` through `2026-07-31`;
- fold 1: `2020-01-02` through `2021-12-31`;
- fold 2: `2022-01-03` through `2023-12-29`;
- fold 3: `2024-01-02` through `2026-07-31`.

Boundaries must be exact common sessions. Folds exactly partition OOS and no
state resets at a boundary.

## Costs, baselines, composite, and gates

- Cost tiers: a one-time 0, 5, or 15-bps QUAL entry at OOS start.
- Metrics use 252-session annualization and zero-risk-free daily Sharpe.
- Baselines: PBUS buy and hold as the broad U.S. equity comparator and SPY buy
  and hold, both zero-cost to keep the candidate comparison conservative.
- Genuine composite: 80% static equal-weight
  `SPY,QQQ,IWM,TLT,GLD` core plus 20% actual costed QUAL candidate.

All common gates must pass:

1. two replays byte-identical;
2. full and every fold positive at 5 bps;
3. full Sharpe at least `0.75`;
4. 15-bps annualized return positive and no more than 1 point below 5 bps;
5. no fold supplies more than 70% of compounded log return;
6. exact one-time entry cost, chronology, costs, and metrics pass tests; and
7. source metrics are unused.

All candidate-specific gates must pass:

1. 5-bps annualized return exceeds both PBUS and SPY by at least 0.75
   percentage point;
2. 5-bps Sharpe exceeds both PBUS and SPY by at least `0.10`;
3. maximum drawdown is no more than 2 percentage points worse than the lower
   drawdown of PBUS and SPY;
4. every fold is positive and at least two folds beat both PBUS and SPY on
   cumulative return; and
5. at 15 bps, the annualized-return and Sharpe rankings in conditions 1 and 2
   still hold.

All composite gates must pass:

1. Sharpe improves on the core by at least `0.02`;
2. annualized return is no more than 1 point lower; and
3. drawdown or annualized return improves by at least 0.5 point.

All gates passing yields `validated_alpha_candidate` and only new untouched
no-submit shadow eligibility. Failure closes the exact proxy without repair.
Outcome calculation is forbidden until protocol and metadata-only receipt are
committed. No strategy registration, broker access, paper mutation, or live
activity is authorized; live authorization remains false.
