# V5.89 Keller Bold Asset Allocation preregistration

Status: frozen before any V5.89 data request, candidate target, return,
metric, gate, rank, or route was computed. This is the operator-directed
final-push family after V5.86, V5.87, and V5.88 closed without tuning. The two
candidates below are revealed atomically; no later rescue, alternate lookback,
universe substitution, or parameter search is allowed. This document grants no
shadow, paper, broker, or live authority.

## Primary evidence and claim boundary

The primary rule source is Wouter J. Keller and Jan Willem Keuning, *Relative
and Absolute Momentum in Times of Rising/Low Yields: Bold Asset Allocation
(BAA)*, SSRN abstract 4166845, listed July 2022
(<https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4166845>, mirrored at
<https://www.researchgate.net/publication/362263377>). The SSRN host blocks
automated retrieval, so the exact rule transcription below was fixed from two
independent public transcriptions before any outcome was computed:

- Allocate Smartly, *Bold Asset Allocation*,
  <https://allocatesmartly.com/bold-asset-allocation/> (ordered rule steps);
- TuringTrader, *Keller's Bold Asset Allocation*,
  <https://www.turingtrader.com/portfolios/keller-bold-asset-allocation/>.

One transcription conflict was found and resolved before freezing: a casual
secondary article claims the BIL cash-substitution rule applies in both modes;
the ordered Allocate Smartly steps apply it only to defensive selections.
V5.89 freezes the defensive-only reading. All source and tracker performance
figures are untrusted; no reported return, Sharpe, drawdown, or chart value
controls ranking, gates, or promotion.

The candidate IDs are:

- `baa_g4_aggressive_proxy`;
- `baa_g12_balanced_proxy`.

## Exact data contract

Seventeen ETFs, canonical order
`SPY,QQQ,IWM,VGK,EWJ,EEM,VNQ,DBC,GLD,TLT,HYG,LQD,EFA,AGG,TIP,BIL,IEF`.

- Provider: authenticated Tiingo End-of-Day through the repository's GET-only,
  destination-allowlisted adapter; free tier; no new paid service.
- Field: `adjClose` normalized to `adjusted_close`; provider split- and
  dividend-adjusted close only; identity mappings only.
- Exact requested coverage: 2007-07-26 through 2026-07-31, one request per
  symbol. Every listed ETF traded on or before 2007-07-26.
- The outcome-blind receipt must pin every raw response, normalized and
  canonical per-symbol artifact, exact endpoint, row count, per-symbol
  SHA-256, one identical ordered common-session sequence, combined canonical
  bytes, and manifest bytes. Missing, duplicate, nonpositive, nonfinite,
  stale, substituted, or session-mismatched rows block. Manual bars, hand
  normalization, synthetic history, source back-extension, broker data, and
  alternate providers are forbidden.

The common-session grid is the intersection of all seventeen symbols'
sessions. Exact session and action counts are frozen in the engine at
admission time, before any price-derived metric is computed.

## Exact candidate rules

All monthly quantities use adjusted closes on the final common session of each
calendar month. For month-end t, `p0` is the adjusted close at t and `pK` is
the adjusted close at the final common session K calendar months earlier.

- Canary momentum (13612W):
  `12*(p0/p1 - 1) + 4*(p0/p3 - 1) + 2*(p0/p6 - 1) + 1*(p0/p12 - 1)`.
- Relative momentum (SMA13 ratio): `p0 / mean(p0, p1, ..., p12)`.
- Canary universe: `SPY, EFA, EEM, AGG`. Offensive mode holds if and only if
  every canary asset's 13612W momentum is strictly positive; otherwise the
  month is defensive. Breadth is one bad canary.
- Offensive selection, `baa_g4_aggressive_proxy`: from `QQQ, EEM, EFA, AGG`
  select the single asset with the highest relative momentum at weight
  `1.000000000000`.
- Offensive selection, `baa_g12_balanced_proxy`: from
  `SPY, QQQ, IWM, VGK, EWJ, EEM, VNQ, DBC, GLD, TLT, HYG, LQD` select the six
  assets with the highest relative momentum at `1/6` each.
- Defensive selection (both candidates): from
  `TIP, DBC, BIL, IEF, TLT, LQD, AGG` select the three assets with the
  highest relative momentum at `1/3` each; then, for each selected asset
  whose relative momentum is strictly less than BIL's relative momentum,
  move that `1/3` to implicit zero-return cash. A selected BIL sleeve is held
  as the BIL ETF. No substitution applies in offensive mode.
- Exact ties in any relative-momentum ranking resolve by the frozen universe
  order above. Nonfinite momentum blocks.
- There is no leverage, short position, optimizer, discretionary override,
  second lookback, or renormalization. Weights are exactly the grammar above;
  unallocated remainder is implicit zero-return cash.

Signals form at month-end common session t; the portfolio trades at the next
common session t+1 at adjusted close, after earning the t-to-t+1 return on
prior holdings; the new target first earns t+1-to-t+2. The sources specify
month-end execution at the signal close; V5.89 keeps the repository's causal
t+1 convention and is a close-only causal proxy, not a source-fill
replication.

## Chronology

- Data/warm-up: 2007-07-26 through 2022-08-31.
- Post-publication OOS: 2022-09-01 through 2026-07-31. The first OOS action
  follows the 2022-08-31 signal, the first month-end signal formed entirely
  after both the SSRN listing (July 2022) and tracker coverage (August 2022)
  were public. Earlier history is in-sample to the source and is not scored.
- Fold 1: 2022-09-01 through 2023-12-31 (16 action months).
- Fold 2: 2024-01-01 through 2025-04-30 (16 action months).
- Fold 3: 2025-05-01 through 2026-07-31 (15 action months).

One continuous path spans OOS; folds never reset targets, holdings, cash,
equity, or costs. The 47-month OOS window is short; that is a frozen,
disclosed weakness of this family, not a reason to relax gates, and any pass
earns only a forward no-submit shadow.

## Costs, controls, and genuine composite

Every portfolio starts in implicit cash and pays its initial transition.
Holdings drift between monthly actions. One-way turnover is half the absolute
target-minus-drifted-weight change across all seventeen ETFs plus implicit
cash. Costs are 0, 5, and 15 basis points per unit of one-way turnover; 5 bps
is the decision cost and 15 bps is stress. These are repository assumptions,
not source claims.

Controls use identical sessions, lag, drift, cash, and costs:

1. `no_canary_g4_always_offensive`: top-1 of the G4 offensive universe every
   month (canary feature removed) — closest ablation for
   `baa_g4_aggressive_proxy`;
2. `no_canary_g12_always_offensive`: top-6 of the G12 offensive universe every
   month — closest ablation for `baa_g12_balanced_proxy`;
3. `static_equal_g12_monthly`: all twelve G12 offensive assets at `1/12`
   monthly — the static baseline for both candidates;
4. `spy_buy_and_hold`; and
5. `spy_ief_60_40_monthly`.

The genuine portfolio test is 80% of actual monthly 60/40 parent targets plus
20% of actual candidate targets, including any implicit cash. Metadata
pairing is invalid.

## Frozen terminal gates

At 5 bps, each candidate must have positive annualized return, Sharpe at
least 0.60, maximum drawdown no greater than 30%, and positive total return
in every fold. At 15 bps, annualized return must remain positive and Sharpe
at least 0.50. No fold may supply more than 70% of positive full compounded
log return.

Weight-grammar integrity must hold on every action: G4 weights in
{0, 1}, G12 weights in {0, 1/6}, defensive weights in {0, 1/3}, total ETF
exposure at most 100%, nonnegative implicit cash. At least three of the
seventeen ETFs must contribute positively over full OOS. The prior sleeve
concentration and all-assets-held gates from diversified-selection families
are inapplicable to a top-1/top-6 rotation grammar and are replaced by the
grammar, breadth, and divergence gates here; this substitution is frozen
before any outcome reveal. All data, lag, rank, momentum, target, drift,
cash, turnover, contribution, fold, hash, and nonpositive-equity checks must
pass. Two complete replays must produce byte-identical result and manifest
bytes.

Each candidate must beat `static_equal_g12_monthly` by at least 0.05 Sharpe,
have maximum drawdown no more than 2 percentage points worse, and win Sharpe
in at least two folds.

Each candidate must diverge from its closest no-canary ablation on at least 8
of the 47 monthly targets and the canary feature must add value: either
Sharpe improves by at least 0.03, or drawdown improves by at least 5%
relatively while annualized-return drag is no more than 1 percentage point.

Each candidate must pass one SPY route:

- defensive: annualized return no more than 1 point below SPY, Sharpe at
  least 0.10 higher, and drawdown at least 20% smaller; or
- growth: annualized return at least 1 point above SPY, Sharpe not below SPY,
  and drawdown no more than 2 points worse.

At 5 bps each actual 80/20 composite versus 60/40 must improve full Sharpe by
at least 0.02, reduce annualized return by no more than 0.75 point, improve
drawdown or annualized return by at least 0.5 point, improve Sharpe in at
least two folds, and have nonnegative fold-3 Sharpe improvement. At 15 bps
full composite Sharpe improvement must be nonnegative. No fold may supply
more than 70% of positive full composite log-return improvement.

Candidates are revealed atomically. If both pass, select exactly one by, in
order: higher 5-bps composite Sharpe improvement, higher standalone Sharpe,
higher annualized return, smaller maximum drawdown, then candidate ID. A
complete pass routes only to
`provisional_historical_validated_alpha_candidate` and a newly fingerprinted
current-clock no-submit shadow with no backfill. Failure closes the exact
route without tuning. Only a completed passing forward shadow can earn an
unqualified validated-alpha label.

## Safety

V5.89 is offline research plus the seventeen exact authorized GET-only
market-data requests. NexusTrade mutation, broker/account/order/position
access, paper mutation, and live activity are forbidden. No credential value
is requested, printed, returned, or persisted outside the trusted adapter
boundary. Existing paper sleeves, reconciliation, receipts, finite caps, and
live prohibitions remain unchanged.
