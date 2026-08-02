# V5.73 global-equities dual-momentum preregistration

Status: frozen before candidate-specific V5.73 data acquisition,
implementation, or outcome inspection. This is a materially new family, not a
repair or variant of either closed V5.72 candidate.

## Candidate and authority

- Candidate ID: `global_equities_dual_momentum_12m_proxy`.
- Methodology label: `repository_etf_proxy_not_antonacci_index_replication`.
- Primary research authority: Gary Antonacci, *Risk Premia Harvesting Through
  Dual Momentum*, first posted in 2012 and subsequently published in the
  Journal of Management & Entrepreneurship. SSRN record:
  <https://papers.ssrn.com/sol3/Papers.cfm?abstract_id=2042750>.
- Author's strategy description:
  <https://www.optimalmomentum.com/global-equities-momentum/>.

The source family combines relative momentum between the S&P 500 and MSCI
ACWI ex-US with absolute momentum relative to U.S. Treasury bills, allocating
to U.S. aggregate bonds when the selected equity fails the absolute test. It
uses a 12-month lookback and monthly reevaluation.

Repository translation uses exactly these adjusted-close ETF proxies:

- `SPY`: S&P 500 equity leg;
- `VEU`: all-world ex-US equity leg;
- `BIL`: U.S. Treasury-bill comparison leg; and
- `AGG`: U.S. aggregate-bond defensive holding.

No source index return, ETF fill, transaction cost, performance statistic, or
lineage is imported. ETF tracking difference, fund fees, adjusted-close timing,
and the shorter tradable history are material limitations.

## Exact fixed rule

At every common calendar month-end:

1. calculate each of `SPY`, `VEU`, and `BIL` total return from the common
   month-end exactly 12 months earlier through the current month-end;
2. choose the higher-return equity leg between `SPY` and `VEU`, resolving an
   exact tie by ticker ascending;
3. if that selected equity return is strictly greater than `BIL` return, form a
   100% cohort in the selected equity; otherwise form a 100% cohort in `AGG`;
4. make the new target effective for the close-to-close return of the first
   common session after formation and hold it until the next monthly action.

There is no skipped month, alternate horizon, buffer, volatility target, cash
switch, top-N choice, moving average, sector input, or parameter grid. Exact
equality to `BIL` selects `AGG`. Cash return outside the target is zero, though
the rule is expected to remain fully invested after warm-up.

## Data contract

- Provider: Tiingo End-of-Day through the repository's secure, GET-only,
  symbol-allowlisted adapter.
- Field: `adjClose` normalized to `adjusted_close`.
- Semantics: provider split- and dividend-adjusted closing price.
- Symbols and provider mapping: identity for `SPY,VEU,BIL,AGG`.
- Exact requested coverage: `2007-06-01` through `2026-07-31`.
- The admitted SPY history may be imported only when its V5.72 normalized
  symbol hash and the V5.72 combined data/manifest hashes validate. `VEU`,
  `BIL`, and `AGG` must be newly acquired into an isolated V5.73 path.
- Unique positive observations, exact common sessions, coverage, hashes,
  adjustment semantics, and symbol mappings are mandatory. Manual CSVs,
  hand-normalized bars, broker data, adjusted-OHLCV claims, and point-in-time
  vintage claims are forbidden.

## Frozen chronology

- Warm-up/reference: first common admitted session through `2012-12-31`.
- Untouched post-first-publication OOS: `2013-01-02` through `2026-07-31`.
- Fold 1: `2013-01-02` through `2017-06-30`.
- Fold 2: `2017-07-03` through `2022-01-03`.
- Fold 3: `2022-01-04` through `2026-07-31`.

Every boundary must be an admitted common session. The folds must exactly
partition OOS. Twelve complete prior month-end intervals are required before
each signal. No date repair, fitting, rolling optimization, endpoint change,
or partial-window scoring is allowed.

## Frozen costs, metrics, and comparators

- One-way turnover is `0.5 * sum(abs(target-prior))`, including cash.
- Cost tiers: 0, 5, and 15 basis points per unit of one-way turnover. Five is
  the decision tier and 15 is stress.
- Metrics: total and annualized return, annualized volatility, zero-risk-free
  daily Sharpe, maximum drawdown, annualized one-way turnover, target holdings,
  transitions, and each fold's return, Sharpe, and drawdown.
- Annualization uses 252 sessions.

No-cost comparators on identical sessions are:

1. SPY buy and hold;
2. static equal weight of `SPY,VEU,AGG`; and
3. the existing static equal-weight `SPY,QQQ,IWM,TLT,GLD` cross-asset core.

The genuine portfolio composite allocates 80% to the static cross-asset core
and 20% to the candidate's actual monthly target. Candidate costs apply to the
20% sleeve. Unused sleeve capital would remain cash. Metadata-only pairing is
forbidden.

## Frozen gates

All common gates must pass:

1. two canonical replays are byte-identical;
2. full and every fold net return are positive at 5 bps;
3. full 5-bps Sharpe is at least `0.65`;
4. 15-bps annualized return remains positive and is no more than 1 percentage
   point below the 5-bps annualized return;
5. no fold contributes more than 70% of full compounded log return;
6. signal lag, target exclusivity, turnover, costs, dates, and metrics pass
   deterministic tests; and
7. source metrics are absent from ranking and gates.

All candidate-specific risk-adjusted alpha gates must pass at 5 bps:

1. Sharpe exceeds SPY by at least `0.05`;
2. maximum drawdown improves on SPY by at least 5 percentage points;
3. annualized return is no more than 2.5 percentage points below SPY;
4. Sharpe exceeds static `SPY,VEU,AGG` equal weight by at least `0.05`;
5. annualized return is no more than 1 percentage point below that static
   balanced comparator;
6. at least two of three folds beat SPY on Sharpe; and
7. `SPY`, `VEU`, and `AGG` each receive a positive target during OOS, with
   between 0.5 and 6.0 annualized target changes.

All 80/20 composite gates must pass against the cross-asset core:

1. Sharpe improves by at least `0.02`;
2. annualized return is no more than 1 percentage point lower; and
3. either maximum drawdown improves by at least 0.5 percentage point or
   annualized return improves by at least 0.5 percentage point.

## Terminal authority

Every gate passing yields `validated_alpha_candidate`, which authorizes only a
new untouched no-submit shadow protocol. Any failure yields
`close_global_equities_dual_momentum_12m_proxy`; it does not authorize a
lookback, threshold, defensive-asset, universe, or gate repair.

Outcome calculation is forbidden until this protocol and a separate metadata-
only canonical data receipt are committed. Offline research only. No strategy
adapter registration, broker/account/order/position access, paper mutation, or
live activity is authorized. Existing interlocks, reconciliation, auditing,
sleeves, and finite paper caps remain unchanged; live authorization is false.
