# V5.98 tax-loss forced-seller detector preregistration

Status: frozen before any V5.98 return, metric, count, or route was computed.

This is the program's first **structural** hypothesis. Every prior milestone
tested a formula — a rule someone published because it backtested well. This
one tests a situation where a specific group of market participants is
**compelled to sell for a reason unrelated to price**, on a known calendar, by
the tax code.

## 1. The structural claim

Investors holding a losing position have a tax incentive to realise the loss
before the calendar year ends, offsetting gains elsewhere. That selling is
forced by tax treatment rather than by any view on value. It concentrates in
December, and it stops on 1 January.

If that mechanism is real and material, it implies **two** things, not one:

1. **December pressure.** Positions already down on the year should
   *underperform* into year-end as the harvesting sells hit.
2. **January reversal.** Once the deadline passes and the artificial supply
   disappears, those same positions should *outperform*.

Requiring both is the point. A curve-fitter hunting the January effect would
find the reversal alone and stop. A genuine forced-seller mechanism must leave
its fingerprint on the December side too. A January-only result therefore
**fails** this protocol, however profitable it looks.

## 2. Universe, defined mechanically

Every symbol already held in this repository with unbroken daily coverage from
`2006-06-26` through `2026-07-31`. That rule selects exactly **45** ETFs and
involves no hand-picking:

`EWA,EWC,EWD,EWG,EWH,EWI,EWK,EWL,EWM,EWN,EWO,EWP,EWQ,EWS,EWT,EWU,EWW,EWY,EWZ,`
`EZA,FXA,FXB,FXC,FXE,FXF,GDX,GLD,IJR,IWM,QQQ,SLV,SMH,SPY,TLT,USO,VBK,`
`XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY`

- No new data is acquired. This milestone performs **zero network requests**.
- Provider semantics are unchanged: Tiingo EOD `adjClose` to `adjusted_close`.

### Disclosure: this universe is not vault-fresh

Most of these symbols were scored by V5.91, V5.92, V5.93, V5.96, or V5.97. This
is therefore **not** a Tier A cohort and is not presented as one.

What makes it admissible anyway: no December, January, or any calendar-seasonal
statistic has ever been computed in this repository, on these symbols or any
others. The prior examinations were trend, volatility sizing, short-term
reversal, and regime conditioning — all orthogonal to year-end seasonality. The
universe was selected by a mechanical coverage rule, not by any tax-loss result,
because none exists.

The residual risk is real and stated: these are symbols this program chose to
acquire at some point, and that choice was not random.

### Disclosure: survivorship

Liquid ETFs rarely delist, so this universe is far cleaner than an equivalent
small-cap study would be — which is precisely why the test is run on ETFs
rather than on the small caps where the tax-loss effect is documented to be
strongest. The honest cost of that substitution: if the effect lives mainly in
small illiquid names, this test may find nothing even if the mechanism is real.
A null result here does **not** refute tax-loss selling in general.

## 3. Exact rule

For each formation year `Y` from **2007 through 2025** (19 complete cycles):

- **Formation date** `F(Y)`: the last common session of November in year `Y`.
- **Year-to-date return**: from the last common session of December `Y-1` to
  `F(Y)`, using adjusted closes.
- **Loser basket**: the bottom quintile by that return — exactly **9** of 45
  symbols, equal-weighted. Ties break by the frozen universe order above.
- **December leg**: `F(Y)` to `E(Y)`, the last common session of December `Y`.
- **January leg**: `E(Y)` to `J(Y)`, the last common session of January `Y+1`.
- **Benchmark**: the equal-weight return of all 45 symbols over the identical
  window.
- **Excess**: loser-basket return minus benchmark return, per leg, per year.

Selection uses only information available at `F(Y)`; both legs are measured
strictly afterwards. There is no skip, no filter, no second ranking, no
volatility adjustment, and no override.

## 4. Costs

The strategy is charged and the benchmark is not — deliberately conservative.
The loser basket pays one round trip per cycle: entry at `E(Y)` and exit at
`J(Y)`, at 5 basis points per one-way turnover for the decision case and 15
basis points for stress. The passive benchmark pays nothing.

## 5. Frozen gates

**Primary.** January excess is positive in at least **14 of 19** years. Exact
one-sided binomial against `p = 0.5` gives `p = 0.03178`. Thirteen years gives
`p = 0.08353` and fails.

**Secondary, all required:**

- **Structural coherence:** December excess is negative in at least **12 of 19**
  years, *and* the mean December excess is negative. Without this the January
  result is a seasonal anomaly with no forced-seller mechanism behind it, and
  the milestone closes regardless of how large the January number is.
- **Cost robustness:** the January leg still clears 14 of 19 at 15 bps.
- **Magnitude:** the median January excess is strictly positive.
- **Integrity:** two complete replays byte-identical; formation strictly
  precedes both legs; no lookahead in ranking.

**Reported but not gated:** per-year excesses for both legs, loser-basket
composition each year, mean and median excess, and the correlation between the
December and January legs.

## 6. Routes

A complete pass routes to
`structural_evidence_supports_forward_shadow_registration` — an argument that
this mechanism deserves a forward window, and nothing more. It is historical
evidence, it is not validated alpha, and it authorises no paper or live
activity.

Any failure routes to `close_detector_without_tuning`. The quintile cut,
formation date, holding window, universe, and thresholds may not be adjusted
afterwards, and the detector is not re-run on a different universe.

## 7. Expected outcome

Twenty-two milestones, zero validated alpha. The tax-loss effect is well
documented in individual small-cap equities and much weaker in liquid ETFs, so
the most likely result is a null. The value of running it is that it is the
first hypothesis here with a *reason* to work that does not depend on a pattern
someone found in a backtest — and the December leg makes it falsifiable in a
way a pure seasonality study is not.

## 8. Safety

Fully offline. No network access, no credential access, no broker or account
access, no paper mutation, no live activity. Live capital remains an operator
hard gate untouched by this document.
