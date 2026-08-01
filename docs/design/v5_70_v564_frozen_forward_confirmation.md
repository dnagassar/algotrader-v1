# V5.70 Frozen V5.64 Forward Confirmation Preregistration

## Status and terminal purpose

This protocol is committed before acquiring, inspecting, or replaying any
post-2025-03-28 price outcome. V5.70 is the single terminal forward
confirmation of the exact frozen V5.64 composite. It creates no new strategy,
parameter, ranking, repair, or lineage claim.

A pass may support only a later, separately authorized no-submit shadow
review. A failure closes the NexusTrade-inspired stock-filter family. No retry
or variant is permitted on this endpoint.

## Frozen identities

- Protocol ID: `v5_70_v564_frozen_forward_confirmation_v1`.
- Candidate ID:
  `nexustrade_monthly_independent_spy_sma_50_200_regime_filter`.
- Standalone comparator candidate:
  `nexustrade_monthly_independent_daily_close_365_session`.
- SPY baseline: `spy_sma_50_200_baseline`.
- Cross-asset comparator: `static_equal_weight_11_stock_buy_hold`.
- V5.64 protocol SHA-256:
  `f24c98daa03462fccd0e73163abfe42f597ab601db83b331ecd4b487e31f4ee0`.
- V5.64 engine SHA-256:
  `66d73e4e0cd6160c8f07febe3a80b90eb4eebdd1ea7375b7fb3b23cadeef87f5`.
- V5.64 preregistration/result/summary/manifest SHA-256:
  `4c54d6c14de2579d1671a8257be6750bd49a586296d041fea95a3fe40e376e3c`,
  `ca9f0177b0b42a3ec888b13799fdd3d39c5c5ae9caacedd2245a0292b42396da`,
  `af3b527db055c4568db7125047dad97ba9492fa55d5bbf2c3a6b6cc9002f41df`,
  `96338ea291f40ea7d9a1ea4a0d45dd17ed5a60c856333150655701f64841dcf6`.
- Frozen historical canonical CSV/manifest SHA-256:
  `d296138a95a86546bdc92678af479e8c8e204b138e2db43f54979a19921c9575`,
  `e204a8a1824e5b49ce4d457f12884bfc284d52f99ad3ba07072c978d7223d8e1`.

The engine must reproduce the frozen V5.64 preregistration, complete result,
and summary exactly on the historical contract before evaluating the forward
window.

## Outcome-blind data acquisition and admission

- Provider: Tiingo EOD through the existing read-only adjusted-data adapter.
- Credential boundary: only `TIINGO_API_KEY` may be loaded from `.env` inside
  the adapter; its value must never be printed, persisted, or copied.
- Network contract: exactly twelve sequential Tiingo EOD GETs, one each for
  AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, GS, JPM, BRK-B, COST, and SPY.
- Provider symbol mapping: exact identity mapping, including `BRK-B->BRK-B`.
- Data start: `2019-01-02`.
- Fixed terminal date: `2026-06-30`.
- Source field: Tiingo `adjClose` mapped to canonical `adjusted_close`.
- Semantics: split/dividend-adjusted EOD price; adjusted OHLCV is not claimed.
- Session reference: observed Tiingo SPY EOD dates; no independent exchange
  calendar claim.
- Generated acquisition root:
  `runs/v5_70_v564_frozen_forward_confirmation/data_acquisition`.
- Generated combined CSV:
  `runs/v5_70_v564_frozen_forward_confirmation/forward_canonical.csv`.
- Generated manifest:
  `runs/v5_70_v564_frozen_forward_confirmation/data_acquisition/canonical_data_manifest.json`.

The refresh must use the existing explicit live-market-data authorization flag
and must not access broker, account, order, position, paper, or live-trading
boundaries.

After acquisition, only provenance, coverage, dates, counts, session
alignment, symbol mapping, adjustment semantics, and hashes may be inspected.
Before any forward strategy result is computed, a tracked metadata-only data
receipt must be committed at
`docs/design/v5_70_v564_forward_data_receipt.md`. The receipt must pin the
combined CSV and manifest hashes, all twelve per-symbol canonical hashes,
exact first/last dates, session count, row count, and the three observed fold
session counts. It must contain no returns, targets, trades, contributions,
rankings, or gate outcomes.

## Fixed chronology

Portfolio simulation begins at the original V5.64 training start and carries
holdings, pending targets, and filled-event timestamps continuously across the
historical OOS boundary into the forward window. No state is reconstructed or
reset at 2025-03-28 or at a fold boundary.

- Historical warm-up start: `2019-01-02`.
- Portfolio accounting start: `2021-12-31`.
- Frozen historical OOS end: `2025-03-28`.
- Forward evaluation begins on the first observed SPY session strictly after
  `2025-03-28`.
- Forward terminal: `2026-06-30`.
- Forward fold 1 calendar bounds: `2025-03-31` through `2025-08-29`.
- Forward fold 2 calendar bounds: `2025-09-02` through `2026-01-30`.
- Forward fold 3 calendar bounds: `2026-02-02` through `2026-06-30`.

Every admitted forward SPY session must belong to exactly one fold, with no
gap between consecutive observed sessions and no overlap. Exact observed
counts are metadata learned only during admission and pinned in the receipt.

## Exactly frozen mechanics

For every stock, compute the exact V5.64 clauses:

1. adjusted close above the inclusive 30-session SMA;
2. adjusted close divided by the inclusive 365-observed-session minimum at
   most `1.05`;
3. simple RSI14 below `28` while SPY simple RSI14 is above `33`.

A stock is eligible when exactly one or two clauses are true. Hold every
eligible stock equal weight; no eligible stocks means cash.

The stateful rebalance rule remains:

`at least 30 calendar days since the candidate's last filled buy OR at least
30 calendar days since its last filled sell`.

Signals use the current adjusted close and fill at the next observed adjusted
close. Holdings drift between fills. Filled increases/decreases update the
candidate's own buy/sell timestamps. The composite holds the eligible set only
when SPY SMA50 is strictly above SMA200 and otherwise holds cash. Regime
transitions schedule next-session targets and update the same state on fill.

No symbol, threshold, lookback, state, weighting, exposure, fill, cost,
comparator, endpoint, fold, or gate may change. No volatility overlay,
inverse-volatility allocation, momentum confirmation, top-N rule, partial-cash
repair, stop, profit target, leverage, shorting, constituent removal, or
parameter sweep is allowed.

## Costs and metrics

Use the exact V5.64 four cases on one-way turnover:

- `zero_cost`: 0 bp fee, 0 bp slippage;
- `source_fee_only`: 1 bp fee, 0 bp slippage;
- `low_friction`: 1 bp fee, 1 bp slippage;
- `moderate_friction`: 1 bp fee, 4 bp slippage.

For the full forward window and every fold, report the complete V5.64 metrics,
fills, turnover, exposure, target hashes, constituent contributions, breadth,
positive contributors, and concentration. External source metrics remain
untrusted and unused; preserve the 29.64% table versus 29.41% chart
discrepancy.

## Terminal gates

Every gate must pass.

Under `source_fee_only`, the composite must beat SPY SMA50/200 in full forward
and every fold on total return, have maximum-drawdown delta at most `0.01`, and
Sharpe delta at least `-0.05` when defined.

Under `moderate_friction`, full-forward return and SPY edge must be positive,
the source-fee SPY edge must not break, and source-fee-to-moderate return
degradation must be below `0.02`.

Under `moderate_friction`, the composite must beat static eleven-stock equal
weight in full forward and every fold, hold at least six distinct stocks, have
at least four positive contributors, and have maximum absolute contribution
share at most `0.50`.

The composite must genuinely differ from the standalone on at least one
forward desired-target session. Versus the standalone under moderate friction,
full-forward return delta must be at least `-0.01`, maximum-drawdown delta at
most `0.01`, Sharpe delta at least `-0.05` when defined, and at least one of
return, drawdown, or Sharpe must strictly improve.

- `preview_review`: all gates pass; supports only later no-submit shadow review.
- `close_stock_filter_family`: any valid completed gate fails.
- `blocked`: data, provenance, coverage, hash, state continuity, reproduction,
  deterministic replay, or integrity validation fails.

There is no `continue_local_research` route.

## Determinism and safety

Write ignored, secret-free artifacts only under
`runs/v5_70_v564_frozen_forward_confirmation`: preregistration, result,
summary, and manifest. A second replay must be byte-identical.

No NexusTrade access or mutation, broker/account/order/position access, paper
mutation, third sleeve, or live activity is allowed. V5.57 safeguards remain
unchanged: $25 entry-order notional, $60 aggregate marked SPY entry exposure,
one broker order per secure cycle, and two sleeve intents per UTC day. Live
remains unauthorized.
