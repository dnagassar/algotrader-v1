# V5.99 perpetual funding carry detector terminal decision

Status: **closed as INCONCLUSIVE — measurement defect. The scored numbers are
void and must not be cited.**

Protocol frozen at `cac1d912`. Two amendments were made before any scoring, both
legitimate and both recorded: the venue moved from Binance to Deribit after
Binance returned HTTP 451 from this jurisdiction, and Deribit's hourly funding
was summed inside the frozen 8-hour interval rather than changing the holding
period.

## The run, and why its output is not a finding

The detector completed and produced `close_detector_without_tuning` with
`-0.063114351251` annualised and a `0.269309734662` drawdown. **That number is
not evidence of anything.** A post-run sanity check on the two legs shows the
measurement cannot resolve the quantity it was built to measure.

| Symbol | Mean absolute 8h basis | Mean 8h funding | Ratio |
| --- | ---: | ---: | ---: |
| BTC-PERPETUAL | `0.006272` | `0.00006507` | ~96x |
| ETH-PERPETUAL | `0.008656` | `0.00004864` | ~178x |
| SOL_USDC-PERPETUAL | `0.010221` | `-0.00001450` | ~700x |

The basis term — the difference between the spot leg and the perpetual leg over
one interval — is roughly **100 times larger than the funding signal it is
supposed to be measured against.**

That is physically implausible for a genuinely delta-neutral pair. A perpetual
tracks its index within a few basis points; it does not diverge by 0.6-1.0% per
eight hours. The distribution confirms the diagnosis: the median basis is
essentially zero (`-0.000060` for BTC) while the 1st and 99th percentiles sit
near ±3%. A tight centre with fat symmetric tails is the signature of **two
price series sampled at different instants**, not of real basis dynamics.

The likely cause is that the funding record's `index_price` is stamped at the
funding instant while the chart endpoint's close is the end of an hourly bar,
so the two marks drift apart precisely when price is moving fastest. Whatever
the exact mechanism, the signal-to-noise ratio makes the result meaningless: a
1:100 signal cannot be recovered from noise of that size, and the reported
`-6.3%` is dominated by misalignment rather than by carry.

## What can and cannot be said

- The structural premise **is** confirmed on the raw data: funding was positive
  in 72% of BTC intervals, 65% of ETH, and 59% of SOL. Longs do usually pay.
  That was never in doubt and is not the contested claim.
- Whether collecting that payment is profitable after basis and costs is
  **untested**. This run did not answer it.
- The failure is in the instrument, not in the hypothesis. Nothing here argues
  for or against the funding carry.

## Deliberately not patched

A synchronised-mark fix is conceivable. It is not attempted, for a reason worth
recording.

This is the **third measurement defect I have shipped in this session**, after
the V5.96 daily-label misalignment and the V5.97 double lag. In V5.97's closure
I wrote that new scoring machinery here carries a high enough defect rate that
"more test coverage, not another cohort" was the correct next investment — and
then built two further detectors without test suites, of which this is the
second to be defective.

Continuing to patch a fourth measurement in the same session would repeat the
exact mistake the previous closure identified. The correct action is to stop,
record the defect, and treat test coverage of new scoring code as a
prerequisite rather than an afterthought.

## Standing

No route is claimed. No validated alpha. No forward-shadow slot. No paper or
live authority. The frozen protocol, symbols, thresholds, and drawdown ceiling
are untouched and may be reused by a future correctly-instrumented attempt,
which would be a new milestone with its own preregistration and its own tests.

## Trust and safety

Read-only public market data from one allowlisted host. GET only. No credentials
requested, loaded, printed, or persisted; the adapter has no code path that can
read one. No broker, account, order, or position access. No paper mutation. No
live activity. Live capital remains an operator hard gate.
