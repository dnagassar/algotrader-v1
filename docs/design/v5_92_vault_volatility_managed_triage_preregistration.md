# V5.92 vault volatility-managed exposure triage preregistration

Status: frozen before any V5.92 data request, per-market target, return, metric,
gate, count, or route was computed. Second use of the V5.90 vault, on the
eighteen single-country markets that remain untouched after V5.91 spent the
first eighteen.

## Why this is not a re-run of V5.91

V5.91 closed absolute trend following at `close_triage_without_tuning`. Its
protocol forbids re-running that rule with an adjusted lookback, cost, window,
or **universe member**. Applying the same 200-session moving-average rule to
these eighteen markets would be exactly that prohibited move — shopping for a
universe that produces a pass — and it is not done here.

This tests a different mechanism. V5.91 asked a binary directional question:
*is this market trending up?* V5.92 asks a continuous risk question: *given how
volatile this market currently is, how much of it should be held?* Direction is
never consulted. A falling market with calm volatility stays fully held, which
is precisely the case absolute trend would exit.

## Disclosed selection

The mechanism was chosen because V5.77 `spy_inverse_variance_long_cash_proxy`
was the strongest candidate this program has produced — it exceeded SPY Sharpe
by 0.102 and improved drawdown by 15.42 points, closing only on return capture
and fold consistency. That is a selection made by us, from our own prior
results, and it is disclosed rather than hidden.

What makes this a legitimate new question rather than a rescue: no V5.77
parameter is being adjusted to manufacture a pass. V5.77 asked whether one
volatility-managed sleeve on one market could beat SPY as a portfolio
candidate. V5.92 asks whether volatility management improves risk-adjusted
return *broadly*, market by market, against each market's own buy-and-hold, on
data this repository has never seen. A published effect that is real should be
broad; one that survives only in the market where it was discovered should not
be trusted.

## Primary evidence

Moreira and Muir, *Volatility-Managed Portfolios*, Journal of Finance 2017,
<https://doi.org/10.1111/jofi.12513>. All external performance figures remain
untrusted and control no rank, gate, or route.

## Exact universe

Canonical order, eighteen symbols, every one confirmed vault-eligible by
`algotrader.research.forward_shadow_vault` before this document was written:

`ARGT,ECH,EDEN,EFNL,EIDO,EIRL,EIS,ENZL,EPHE,EPOL,EPU,EWT,EZA,GREK,INDA,NORW,THD,TUR`

- Provider: authenticated Tiingo End-of-Day through the repository's GET-only,
  destination-allowlisted adapter; free tier; no new paid service.
- Field: `adjClose` normalized to `adjusted_close`; identity mappings only.
- Requested coverage: 2000-01-03 through 2026-07-31, one request per symbol.
- Admitted panel: the exact common-session intersection. Launch dates differ
  widely across this cohort, so the intersection — not the request — defines
  the scored window, and the receipt pins whatever it proves to be.
- The intersection must contain at least 3,000 common sessions and must end at
  2026-07-31. Fewer blocks the milestone rather than shrinking the test.
- Missing, duplicate, nonpositive, nonfinite, stale, substituted, or
  session-mismatched rows block. Manual bars, hand normalization, synthetic
  history, back-extension, broker data, and alternate providers are forbidden.

This cohort launched largely between 2007 and 2012, so the scored window will
be almost entirely post-2008. That is a deliberate virtue: V5.91's apparent
edge lived in 2001-2007 and vanished afterward. No result here can be produced
by early-history regimes, because there is no early history in the panel.

## Exact rule

One rule, no variants, applied identically to every market.

- Realized volatility: on the final common session `t` of each calendar month,
  `sigma(t)` is the sample standard deviation (n-1) of the trailing 60 daily
  simple adjusted-close returns ending at `t`, annualized by `sqrt(252)`.
- Target: `w(t) = min(1.0, 0.15 / sigma(t))`. The 0.15 annualized volatility
  target is a frozen constant declared in advance; it is not fitted, optimized,
  or tuned per market.
- No leverage: the cap of 1.0 binds whenever `sigma(t) <= 0.15`. The unheld
  remainder is implicit zero-return cash.
- A nonpositive or nonfinite `sigma(t)` blocks.
- Direction, trend, momentum, and moving averages are never consulted.
- Execution: the target formed at `t` takes effect at the next common session
  `t+1` close, after the `t`-to-`t+1` return is earned by prior holdings.
- Warm-up: the first 61 common sessions form no signal and are not scored.
- Benchmark: 100% buy-and-hold of the same market, entered at the first scored
  session and never rebalanced. Both start flat and pay an identical entry
  transition.
- Costs: 0, 5, and 15 basis points per unit of one-way turnover; 5 bps is the
  decision cost and 15 bps is stress. Repository assumptions, not source claims.

Volatility management rebalances continuously rather than switching, so it will
carry materially higher turnover than V5.91's binary rule. The 15 bps stress
gate is therefore load-bearing, not decorative.

## Frozen gates

Carried forward deliberately from V5.91, where the cost-robustness and
regime-consistency gates were the two that caught an effect the primary gate
would have waved through.

**Primary.** At 5 bps, the rule must beat its own market's buy-and-hold on
Sharpe ratio in at least **13 of 18** markets. Under independence this is an
exact one-sided binomial test with `p = 0.04813`. Twelve wins gives `p =
0.11894` and fails.

**Secondary, all required:**

- At 15 bps, at least 13 of 18 Sharpe wins.
- At 5 bps, the rule improves maximum drawdown in at least 13 of 18 markets.
- At 5 bps, the median per-market Sharpe improvement is strictly positive.
- Regime consistency: over the **second half** of the scored window — defined
  deterministically as the sessions from the midpoint index onward, with no
  discretionary date — at least 12 of 18 Sharpe wins at 5 bps.
- Integrity: two complete replays produce byte-identical result and manifest
  bytes; causal lag, warm-up exclusion, weight grammar, drift, cash, turnover,
  and hash identities all verify.

**Reported but not gated:** mean pairwise correlation of the per-market excess
return series, per-market Sharpe and drawdown deltas, average target weight,
and realized turnover.

As in V5.91, the binomial gate assumes independence that correlated equity
markets do not have, so it overstates significance. The realized excess
correlation must be reported alongside the result. It is disclosure, not an
adjustment knob: a low correlation does not upgrade a fail and a high one does
not annul a pass.

## Routes

A complete pass routes to
`cross_sectional_evidence_supports_forward_shadow_registration` and nothing
further. It authorizes no paper, no broker, no live, and no validated-alpha
label, because this is historical evidence uncontaminated by *our* selection
but not by the calendar.

Any failure routes to `close_triage_without_tuning`. No threshold, volatility
target, lookback, universe member, cost, or window may be adjusted afterward,
and the rule is not re-run on a third cohort.

## Safety

V5.92 is offline research plus eighteen exact authorized GET-only market-data
requests. Broker, account, order, and position access, paper mutation, and live
activity are forbidden. No credential value is requested, printed, returned, or
persisted outside the trusted adapter boundary. Existing paper sleeves,
reconciliation, receipts, caps, and live prohibitions are unchanged.
