# V5.72 primary-source alpha tournament preregistration

Status: frozen before candidate data acquisition, implementation, or outcome
inspection. This document is authority for the exact V5.72 experiment only.
It grants no preview, paper, broker, or live-capital route by itself.

## Decision and purpose

V5.72 evaluates exactly two independently motivated, fixed-rule, long/cash or
long-only ETF candidates. The objective is to find a small, credible alpha
candidate set without a parameter search, manual data construction, inherited
source performance, or outcome-driven repair.

The terminal routes are:

1. `validated_alpha_candidate` when every candidate-specific gate and every
   common integrity gate passes;
2. `close_candidate` when any required gate fails; or
3. `blocked_evidence_or_data` when authoritative evidence, deterministic data,
   or an exact replay cannot be established.

`validated_alpha_candidate` means eligible for a new, untouched no-submit
shadow qualification. It does not mean paper promotion, live readiness, a
profit guarantee, or permission to trade.

## Primary-source evidence and translation boundary

### Candidate 1: SPY turn of month

- Candidate ID: `spy_turn_of_month_last_plus_first_three`.
- Primary authority: John J. McConnell and Wei Xu, *Equity Returns at the Turn
  of the Month*, Financial Analysts Journal 64(2), 2008. Author-hosted paper:
  <https://business.purdue.edu/faculty/mcconnell/publications/Equity-Returns-at-the-Turn-of-the-Month.pdf>.
- Source rule being tested: the four-session interval comprising the last
  trading day of a calendar month and the first three trading days of the next
  calendar month.
- Repository translation: target SPY exposure is 1.0 for each close-to-close
  return whose ending session is one of those four sessions, and 0.0 otherwise.
  The target is known and set using the exchange calendar before the return
  begins. This execution convention is local and is not attributed to the
  paper. Cash return is fixed at zero. The result label is
  `repository_proxy_not_crsp_index_replication` because SPY adjusted closes are
  neither the paper's CRSP indices nor guaranteed market-on-close fills.
- No holidays, quarter ends, year ends, volatility states, weekdays, or
  alternate windows are selected or excluded.

### Candidate 2: nine-sector 6x6 industry-momentum proxy

- Candidate ID: `nine_sector_long_only_industry_momentum_6x6_proxy`.
- Primary authority: Tobias J. Moskowitz and Mark Grinblatt, *Do Industries
  Explain Momentum?*, Journal of Finance 54(4), 1999, DOI
  <https://doi.org/10.1111/0022-1082.00146>.
- Source construction motivating the rule: rank 20 value-weighted industries
  on their prior six monthly returns with no skipped month, hold equal-weight
  top-three and bottom-three legs for six months, and combine six overlapping
  monthly cohorts.
- Repository translation: this is
  `repository_proxy_not_moskowitz_grinblatt_replication`. The universe is the
  nine original Select Sector SPDR ETFs `XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY`.
  At each common month-end, rank the nine ETFs by the compounded return across
  the six immediately preceding complete month-end intervals, with no skipped
  month. Form a cohort holding the top three in equal weights. Each cohort is
  held for six complete monthly intervals. The live target for a session is
  the equal combination of all six active cohorts and becomes effective on the
  first common session after formation. Cash is zero; no short leg exists.
  Exact ranking ties resolve by canonical ticker ascending.
- The original 20-industry universe is translated to nine tradable sector
  funds, so the selected fraction changes from 3/20 to 3/9. The original short
  leg and stock-level value weighting are absent. No source metric, alpha,
  return, or significance claim transfers to this proxy.
- `XLC` and `XLRE` are excluded because they do not share the original funds'
  1998 inception and because adding them would create a point-in-time universe
  change not defined by this protocol.

No third candidate may be added to V5.72. The Crypto Tournament V2 candidates
remain separately sealed and may not be scored or used to revise V5.72 before
`2026-08-13T00:00:00Z`.

## Canonical data contract

- Provider: Tiingo End-of-Day through the repository's secure, GET-only,
  allowlisted adjusted-data adapter.
- Field: provider `adjClose`, normalized as `adjusted_close`.
- Adjustment claim: the provider's split- and dividend-adjusted close. No
  adjusted OHLCV, point-in-time constituent, survivorship-free stock universe,
  or execution-price claim is made.
- Symbols: `SPY,QQQ,IWM,TLT,GLD,XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY`.
- Requested coverage: `2004-11-18` through `2026-07-31`, inclusive.
- Evaluation requires one exact intersection of valid sessions across all 14
  symbols. Duplicate symbol/date rows, missing values, nonpositive prices,
  symbol substitutions, and incomplete required coverage are hard failures.
- The five already admitted ETF files may be imported only when their hashes
  and prior V5.71 manifest validate exactly. The nine sector files must be
  acquired by the same secure adapter. Manual CSV placement, hand-normalized
  bars, broker data, and credential exposure are forbidden.
- Provider symbol mapping is identity for every V5.72 symbol and must be
  recorded in a committed receipt. Credential state is reported only as
  booleans. Credential values may not appear in commands, output, artifacts,
  source, Git, or reports.

## Frozen chronology and warm-up

- Reference and warm-up: first common admitted session through `2008-12-31`.
  It is used only to initialize the sector candidate's monthly rankings and six
  overlapping cohorts. There is no fit, search, or selection.
- Untouched chronological OOS: `2009-01-02` through `2026-07-31`, inclusive.
- Fold 1: `2009-01-02` through `2014-12-31`.
- Fold 2: `2015-01-02` through `2020-12-31`.
- Fold 3: `2021-01-04` through `2026-07-31`.
- The engine must fail closed unless all boundary dates are admitted sessions
  and every fold contains data. No half-split, rolling optimization, date
  repair, fold repair, or endpoint extension is permitted.

Signals formed from a session close may first affect the following common
session's close-to-close return. The turn-of-month calendar schedule is known
before its applicable return begins. The sector candidate requires six
complete ranking months and six already formed cohorts before OOS; otherwise
the experiment is blocked rather than partially invested.

## Frozen cost, metrics, and comparators

- One-way turnover is `0.5 * sum(abs(target_weight - prior_weight))`, including
  cash implicitly.
- Cost tiers are 0, 5, and 15 basis points per unit of one-way turnover. Five
  basis points is the decision tier and 15 basis points is stress.
- Daily candidate return uses prior target weights and close-to-close adjusted
  returns, less transition cost. There is no same-close execution advantage.
- Annualization uses 252 sessions. Sharpe uses zero risk-free rate. Maximum
  drawdown is peak-to-trough on the compounded daily equity curve.
- Required metrics: total and annualized return, annualized volatility, Sharpe,
  maximum drawdown, annualized one-way turnover, invested fraction, and each
  fold's return, Sharpe, and drawdown.

Comparators under identical sessions and no cost are:

1. SPY buy and hold;
2. static equal weight of the nine sector ETFs; and
3. a constant-weight SPY/cash portfolio whose SPY weight is the turn-of-month
   candidate's calendar-derived OOS invested fraction; and
4. static equal weight of `SPY,QQQ,IWM,TLT,GLD` as the cross-asset core.

For each candidate, the genuine portfolio composite allocates 80% to the
static cross-asset core and 20% to the candidate's actual time-varying target
weights. Unused candidate allocation remains cash. Composite costs apply only
to the 20% candidate sleeve. Metadata-only pairing is forbidden.

## Common integrity gates

Every candidate must pass all of these gates independently:

1. two canonical replays produce byte-identical result and manifest bytes;
2. full and every fold have positive net return at 5 bps;
3. full net Sharpe at 5 bps is at least `0.50`;
4. the full 15-bps annualized return is positive and no more than 2 percentage
   points below the 5-bps annualized return;
5. no fold contributes more than 70% of full compounded log return;
6. dates, lagging, costs, weights, and all metric identities pass deterministic
   tests; and
7. no source metric participates in ranking, gating, or promotion.

## Candidate-specific alpha gates

### SPY turn of month

At the 5-bps tier, all must hold:

1. full Sharpe exceeds both SPY buy and hold and the exposure-matched SPY/cash
   comparator by at least `0.10`;
2. annualized return exceeds the exposure-matched comparator by at least 1
   percentage point;
3. maximum drawdown is no more than 2 percentage points worse than the
   exposure-matched comparator;
4. at least two of three folds beat the exposure-matched comparator on both
   return and Sharpe;
5. the separately reported `2024-01-02` through `2026-07-31` subwindow is
   positive net and beats the exposure-matched comparator on return; and
6. average invested fraction is between 12% and 25%, proving the exact sparse
   schedule rather than continuous market exposure.

### Nine-sector 6x6 proxy

At the 5-bps tier, all must hold:

1. annualized return exceeds both static nine-sector equal weight and SPY by at
   least 1 percentage point;
2. Sharpe exceeds both static nine-sector equal weight and SPY by at least
   `0.10`;
3. maximum drawdown is no more than 2 percentage points worse than the better
   of those comparators;
4. at least two of three folds beat both comparators on cumulative return;
5. the 15-bps annualized-return edge over static nine-sector equal weight
   remains positive;
6. all nine sectors receive a positive target weight at least once during OOS,
   no target weight exceeds the structural `1/3` cap, and no single sector
   contributes more than 45% of full-OOS positive gains.

## Portfolio-level gate

For a candidate's 80/20 composite at the 5-bps tier, all must hold against the
static cross-asset core:

1. Sharpe improves by at least `0.02`;
2. annualized return is no more than 1 percentage point lower; and
3. either maximum drawdown improves by at least 0.5 percentage point or
   annualized return improves by at least 0.5 percentage point.

This gate is mandatory. Standalone significance or a source narrative cannot
substitute for portfolio-level value.

## Outcome discipline and terminal authority

- Candidate returns, rankings, metrics, and charts may not be inspected until
  this document is committed and the canonical data receipt is separately
  committed.
- No parameter grid, alternative window, alternative winner count, alternate
  cost, subperiod exclusion, or gate change is permitted after inspection.
- Failure closes the exact candidate. It does not authorize tuning or a renamed
  retry.
- A pass creates only a `validated_alpha_candidate` evidence object and a
  recommendation for a new untouched no-submit shadow protocol.
- External performance is untrusted. The result must explicitly record that no
  source return, alpha, Sharpe, drawdown, trade count, or significance statistic
  controlled the decision.

Offline research only. NexusTrade, broker, account, order, position, paper
mutation, and live activity are all out of scope. Existing paper interlocks,
reconciliation, auditing, sleeve ownership, and finite caps remain unchanged.
Live authorization remains false.
