# V5.74 Vigilant Asset Allocation G4 preregistration

Status: frozen before V5.74 data acquisition, implementation, or outcome
inspection. VAA-G4 was independently preselected before the V5.73 result and
is not a GEM parameter or threshold repair.

## Source and candidate

- Candidate ID: `vigilant_asset_allocation_g4_13612w_proxy`.
- Methodology label: `repository_etf_proxy_not_keller_keuning_replication`.
- Primary authority: Wouter J. Keller and Jan Willem Keuning, *Breadth Momentum
  and Vigilant Asset Allocation (VAA): Winning More by Losing Less*, 2017:
  <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3002624>.
- Author paper PDF:
  <https://assets.super.so/e46b77e7-ee08-445e-b43f-4ffd88ae0a0e/files/5ec03ad3-7a25-4c6e-9537-f73d50355b6a.pdf>.

The exact risky G4 universe is `SPY,VEA,VWO,BND`; the defensive C3 universe is
`SHY,IEF,LQD`. The repository uses the funds' adjusted closes, not the paper's
long synthetic/ETF-like history. No source return, cost, fill, statistic, or
lineage is imported.

## Exact fixed rule

At each common calendar month-end, calculate for every G4 and C3 asset:

`13612W = 12*(p0/p1) + 4*(p0/p3) + 2*(p0/p6) + (p0/p12) - 19`

where `p0` is the current complete month-end adjusted close and `p1`, `p3`,
`p6`, and `p12` are the adjusted closes at the corresponding prior complete
month-ends. Dividing the score by four would not affect signs or ranks and is
therefore omitted.

- If every G4 score is strictly positive, select the single highest-scored G4
  asset.
- If any G4 score is nonpositive, select the single highest-scored C3 asset.
- Resolve exact score ties by ticker ascending.
- Form a 100% single-asset target effective for the close-to-close return of
  the first common session after formation and hold until the next action.

Frozen parameters are `T=1`, `B=1`, the seven exact ETFs, the exact 13612W
weights, and the nonpositive breadth trigger. There is no candidate grid,
canary substitution, cash alternative, lookback repair, same-close fill,
volatility overlay, leverage, or shorting.

## Data and chronology

- Provider: Tiingo End-of-Day through the secure GET-only allowlisted adapter.
- Field: `adjClose` to `adjusted_close`; provider split/dividend-adjusted close.
- Exact identity symbols: `SPY,VEA,VWO,BND,SHY,IEF,LQD`.
- Requested coverage: `2007-07-26` through `2026-07-31`.
- SPY may be imported only after exact V5.72 data, manifest, and normalized-SPY
  hashes validate. The six other histories must be newly acquired into an
  isolated V5.74 path.
- Unique positive rows, exact common sessions, dates, mappings, provenance,
  adjustment semantics, and hashes are mandatory. Manual data, broker data,
  hand normalization, synthetic histories, and adjusted-OHLCV or execution-
  price claims are forbidden.

Frozen evaluation:

- reference/warm-up through `2017-12-29`;
- untouched post-publication OOS `2018-01-02` through `2026-07-31`;
- fold 1 `2018-01-02` through `2020-12-31`;
- fold 2 `2021-01-04` through `2023-12-29`;
- fold 3 `2024-01-02` through `2026-07-31`.

Every boundary must be a common session, folds must exactly partition OOS, and
12 complete month-end intervals must precede every signal. No window repair,
fit, search, exclusion, or endpoint change is allowed.

## Costs, metrics, and comparators

- One-way turnover is `0.5 * sum(abs(target-prior))`, including cash.
- Cost tiers are 0, 10, and 20 basis points; 10 is the decision tier and 20 is
  stress.
- Annualization uses 252 sessions; Sharpe uses daily returns and zero risk-free
  rate.
- Required metrics include return, volatility, Sharpe, drawdown, turnover,
  target changes, holdings, contribution shares, and exact fold metrics.

No-cost comparators on identical sessions are:

1. static equal weight G4;
2. static 60% SPY / 40% BND;
3. SPY buy and hold; and
4. static equal-weight `SPY,QQQ,IWM,TLT,GLD` cross-asset core.

The genuine composite holds 80% static cross-asset core and 20% actual VAA-G4
targets. Candidate sleeve costs are scaled to 20%. Metadata-only pairing is
forbidden.

## Frozen gates

Every common gate must pass:

1. two canonical replays are byte-identical;
2. full and every fold return are positive at 10 bps;
3. full 10-bps Sharpe is at least `0.75`;
4. 20-bps annualized return is positive and no more than 1 percentage point
   below 10-bps annualized return;
5. no fold supplies more than 70% of full compounded log return;
6. exact score, sign trigger, single-target, lag, cost, and metric identities
   pass deterministic tests; and
7. source metrics are absent from ranking and gates.

Every candidate-specific gate must pass at 10 bps:

1. annualized return exceeds static G4 and 60/40 by at least 1 percentage point;
2. Sharpe exceeds static G4 and 60/40 by at least `0.10`;
3. maximum drawdown improves on 60/40 by at least 5 percentage points and SPY
   by at least 10 percentage points;
4. at least two folds beat both diversified comparators on Sharpe;
5. at 20 bps, annualized return remains above 60/40;
6. at least three distinct assets receive OOS targets; and
7. no asset supplies more than 60% of positive OOS gross contribution.

Every composite gate must pass against the cross-asset core:

1. Sharpe improves by at least `0.02`;
2. annualized return is no more than 1 percentage point lower; and
3. drawdown improves by 0.5 percentage point or annualized return improves by
   0.5 percentage point.

## Terminal authority

All gates passing yields `validated_alpha_candidate` and only a recommendation
for a new untouched no-submit shadow. Any failure closes this exact VAA-G4
proxy; it does not authorize a universe, score, breadth, cost, fill, or gate
repair.

Outcome calculation is forbidden until this protocol and a separate metadata-
only data receipt are committed. Offline research only. No strategy registry,
broker/account/order/position access, paper mutation, or live activity is
authorized. Existing safety and finite caps remain unchanged; live
authorization is false.
