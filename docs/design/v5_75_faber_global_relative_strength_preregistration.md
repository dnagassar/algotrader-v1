# V5.75 Faber global relative-strength preregistration

Status: frozen before V5.75 data acquisition, implementation, or outcome
inspection. This source-selected top-two global-asset-class family was
recommended independently before V5.74 outcomes existed.

## Candidate and source

- Candidate ID: `faber_global_asset_relative_strength_top2_12m_proxy`.
- Label: `repository_etf_proxy_not_faber_index_replication`.
- Primary authority: Mebane T. Faber, *Relative Strength Strategies for
  Investing*, April 2010:
  <https://mebfaber.com/wp-content/uploads/2016/05/SSRN-id1585517.pdf>.

The paper ranks total-return series monthly, invests equally in the top X, and
replaces assets that leave top X at the next monthly rebalance. It reports the
method across five global asset classes. Source performance, fills, costs, and
historical index lineage are untrusted and cannot enter a gate.

The repository's fixed ETF proxies are:

- `SPY`: U.S. equities;
- `EFA`: developed ex-U.S. equities;
- `IEF`: intermediate U.S. Treasuries;
- `VNQ`: U.S. REITs; and
- `DBC`: broad commodities.

This is an investable ETF proxy, not the paper's reconstructed index history.
ETF fees, tracking, inception, adjusted-close timing, and the U.S.-only REIT
proxy are material limitations.

## Exact fixed rule

At every common month-end:

1. calculate each ETF's compounded total return over the twelve immediately
   preceding complete month-end intervals, with no skipped month;
2. rank descending and resolve an exact return tie by ticker ascending;
3. select the top two and set each target to 50%; and
4. make the target effective for the close-to-close return of the first common
   session after formation, then let weights drift until the next rebalance.

Always fully invested. No cash filter, moving average, absolute-momentum test,
sell buffer, alternative horizon, top count, combined score, leverage, or
shorting is allowed. The paper's same-close convention is not claimed; the
repository uses a conservative next-session lag.

## Data and chronology

- Provider: Tiingo EOD through the secure GET-only adjusted-data adapter.
- Field: `adjClose` to `adjusted_close`; split/dividend-adjusted close.
- Identity symbols: `SPY,EFA,IEF,VNQ,DBC`.
- Requested coverage: `2007-07-26` through `2026-07-31`.
- SPY and IEF may be reused only after their admitted source and normalized
  hashes validate. EFA, VNQ, and DBC must be newly acquired into V5.75.
- Exact common sessions, positive unique rows, mappings, semantics, coverage,
  and hashes are required. Manual/synthetic/broker data and execution-price,
  adjusted-OHLCV, or point-in-time vintage claims are forbidden.

Frozen evaluation:

- reference/warm-up through `2010-12-31`;
- untouched post-first-draft OOS `2011-01-03` through `2026-07-31`;
- fold 1 `2011-01-03` through `2016-03-31`;
- fold 2 `2016-04-01` through `2021-06-30`;
- fold 3 `2021-07-01` through `2026-07-31`.

Boundaries must be common sessions; folds exactly partition OOS; twelve prior
complete month-end intervals are mandatory. No fitting or date repair exists.

## Costs, baselines, composite, and gates

- One-way turnover: `0.5 * sum(abs(target-prior))`, including cash.
- Cost tiers: 0, 5, and 15 bps; 5 bps decides and 15 bps stresses.
- Metrics use 252-session annualization and zero-risk-free daily Sharpe.
- Baselines: static equal-weight five-proxy portfolio, SPY buy and hold, and
  static equal-weight `SPY,QQQ,IWM,TLT,GLD` cross-asset core.
- Genuine composite: 80% static cross-asset core plus 20% actual candidate;
  candidate sleeve costs scale to 20%.

All common gates must pass:

1. two replays byte-identical;
2. full and every fold positive at 5 bps;
3. full Sharpe at least `0.75`;
4. 15-bps annualized return positive and no more than 1 point below 5 bps;
5. no fold supplies more than 70% of compounded log return;
6. exact rank, lag, two-asset weights, costs, and metrics pass tests; and
7. source metrics are unused.

All candidate-specific gates must pass at 5 bps:

1. annualized return exceeds static five-proxy equal weight by at least 1 point;
2. Sharpe exceeds static five-proxy equal weight by at least `0.10`;
3. drawdown is no more than 2 points worse than static five-proxy equal weight;
4. Sharpe exceeds SPY by at least `0.05`, drawdown improves on SPY by at least
   5 points, and annualized return is within 3 points of SPY;
5. at least two folds beat static five-proxy equal weight on Sharpe;
6. at 15 bps, annualized return remains above static five-proxy equal weight;
7. at least four of five assets receive a target and no asset supplies more
   than 55% of positive gross contribution.

All composite gates must pass:

1. Sharpe improves on the core by at least `0.02`;
2. annualized return is no more than 1 point lower; and
3. drawdown or annualized return improves by at least 0.5 point.

All gates passing yields `validated_alpha_candidate` and only new untouched
no-submit shadow eligibility. Failure closes the exact proxy without repair.
Outcome calculation is forbidden until protocol and metadata-only receipt are
committed. No strategy registration, broker access, paper mutation, or live
activity is authorized; live authorization remains false.
