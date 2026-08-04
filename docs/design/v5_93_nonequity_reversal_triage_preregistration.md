# V5.93 non-equity short-term reversal triage preregistration

Status: frozen before any V5.93 data request, per-market target, return, metric,
gate, count, or route was computed. Third vault triage, and the first outside
equities.

## Why this cohort and this rule

The two closed triages share a confound worth naming. V5.91 (absolute trend) and
V5.92 (volatility-capped sizing) were both run on single-country **equity**
markets, and the program's standing structural diagnosis is that defensive
overlays lose to a long equity advance. Equity markets rose over both windows,
so "the overlay lost because the market went up" is available as an explanation
for both failures.

Commodities, currencies, and credit do not share that property. Over the
window this cohort will produce, broad commodities were flat to negative and
developed-market currencies were range-bound against the dollar. There is no
sustained bull market for a defensive overlay to lose to. That makes this the
sharpest available test of the timing-overlay thesis: a failure here cannot be
explained away by a rising benchmark, and would generalize the finding
considerably.

The rule is **short-term reversal**, the mechanical opposite of V5.91's trend
rule. V5.91 held a market when it was above its long-run average; V5.93 holds a
market precisely when it has recently *fallen*. This is a genuinely distinct
published mechanism (Jegadeesh 1990; Lehmann 1990), not an adjusted re-run.
V5.91's closure forbids re-testing its rule on a new cohort, and that
prohibition is respected: no moving average, lookback, or threshold from V5.91
or V5.92 appears here.

A caution stated in advance so it cannot be claimed afterward: trend failing
does **not** imply reversal succeeding. Both can fail, and transaction costs
penalize both. No directional expectation is encoded in the gates.

## Exact universe

Eighteen symbols spanning three non-equity classes, canonical order, every one
confirmed vault-eligible by `algotrader.research.forward_shadow_vault` before
this document was written:

`BWX,DBA,DBB,DBO,EMB,FXA,FXB,FXC,FXE,FXF,FXY,IGOV,MBB,MUB,PFF,SLV,UNG,USO`

- Commodities: `DBA` agriculture, `DBB` base metals, `DBO` oil, `SLV` silver,
  `UNG` natural gas, `USO` crude.
- Currencies: `FXA` AUD, `FXB` GBP, `FXC` CAD, `FXE` EUR, `FXF` CHF, `FXY` JPY.
- Credit and rates: `BWX` international treasuries, `EMB` emerging sovereign,
  `IGOV` international government, `MBB` mortgage-backed, `MUB` municipal,
  `PFF` preferred.

- Provider: authenticated Tiingo End-of-Day through the repository's GET-only,
  destination-allowlisted adapter; free tier; no new paid service.
- Field: `adjClose` normalized to `adjusted_close`; identity mappings only.
- Requested coverage: 2005-01-03 through 2026-07-31, one request per symbol.
- Admitted panel: the exact common-session intersection, which must contain at
  least 3,000 sessions and end at 2026-07-31. Fewer blocks the milestone.
- Missing, duplicate, nonpositive, nonfinite, stale, substituted, or
  session-mismatched rows block. Manual bars, hand normalization, synthetic
  history, back-extension, broker data, and alternate providers are forbidden.

These are commodity- and currency-tracking ETFs. They carry roll and financing
costs and are not the spot assets they reference; `USO` and `UNG` in particular
are structurally decayed by contango. That is a property of the tradable
instrument, which is what a tradable rule must be judged on, and no attempt is
made to model the underlying instead.

## Exact rule

One rule, no variants, applied identically to every market.

- Signal: on the final common session `t` of each calendar month, compute the
  trailing 21-session simple return
  `r(t) = adjusted_close(t) / adjusted_close(t - 21) - 1`.
- Target: `1.0` if `r(t) < 0`, otherwise `0.0`. The rule buys what has recently
  fallen and holds zero-return cash otherwise.
- Exactly `r(t) == 0` yields `0.0`; the test is strict.
- No leverage, no shorting, no sizing, no second lookback, no trend filter, no
  cross-market ranking, no override.
- Execution: the target formed at `t` takes effect at the next common session
  `t+1` close, after the `t`-to-`t+1` return is earned by prior holdings.
- Warm-up: the first 22 common sessions form no signal and are not scored.
- Benchmark: 100% buy-and-hold of the same market, entered at the first scored
  session and never rebalanced. Both start flat and pay an identical entry
  transition.
- Costs: 0, 5, and 15 basis points per unit of one-way turnover; 5 bps is the
  decision cost and 15 bps is stress.

## Frozen gates

Identical in structure to V5.91 and V5.92, whose cost-robustness and
regime-consistency gates both proved load-bearing.

**Primary.** At 5 bps, the rule must beat its own market's buy-and-hold on
Sharpe in at least **13 of 18** markets. One-sided exact binomial `p = 0.04813`
under independence. Twelve wins gives `p = 0.11894` and fails.

**Secondary, all required:**

- At 15 bps, at least 13 of 18 Sharpe wins.
- At 5 bps, maximum drawdown improves in at least 13 of 18 markets.
- At 5 bps, the median per-market Sharpe improvement is strictly positive.
- Regime consistency: at least 12 of 18 Sharpe wins at 5 bps over the second
  half of the scored window, defined deterministically as the sessions from the
  midpoint index onward, with no date chosen after seeing data.
- Integrity: two complete replays byte-identical; causal lag, warm-up exclusion,
  weight grammar, drift, cash, turnover, and hash identities all verify.

**Reported but not gated:** mean pairwise correlation of per-market excess
returns, per-market deltas, and the fraction of months held.

A benchmark caveat specific to this cohort: several of these instruments have
strongly negative buy-and-hold returns. Beating a losing benchmark on Sharpe is
a weak achievement, so the median-improvement and drawdown gates are retained
precisely to stop a rule from passing merely by sitting in cash while its
benchmark decays. Cash-like behaviour must still earn its Sharpe.

## Routes

A complete pass routes to
`cross_sectional_evidence_supports_forward_shadow_registration` and nothing
more. It authorizes no paper, no broker, no live, and no validated-alpha label.

Any failure routes to `close_triage_without_tuning`. No threshold, lookback,
universe member, cost, or window may be adjusted afterward, and the rule is not
re-run on another cohort.

## Safety

V5.93 is offline research plus eighteen exact authorized GET-only market-data
requests. Broker, account, order, and position access, paper mutation, and live
activity are forbidden. No credential value is requested, printed, returned, or
persisted outside the trusted adapter boundary. Existing paper sleeves,
reconciliation, receipts, caps, and live prohibitions are unchanged.
