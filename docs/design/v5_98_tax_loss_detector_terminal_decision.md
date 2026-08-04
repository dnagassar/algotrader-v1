# V5.98 tax-loss forced-seller detector terminal decision

Status: terminally closed. Route `close_detector_without_tuning`. Protocol
frozen at `d80eb47`, engine at `0e9f6f3` — both before any return, metric, or
count existed.

- Universe: 45 held ETFs, unbroken coverage `2006-06-26`..`2026-07-31`.
- Panel: 5,056 common sessions; 19 complete formation cycles, 2007-2025.
- Network requests: **zero**. Every symbol was already held.
- Result SHA-256:
  `7f6a2710dae7dec960e9eaafa39a5d1939c84018f1e42882f2d16171d16fa4f5`.
- Two replays byte-identical.

## Gate outcome

| Gate | Result | Outcome |
| --- | ---: | --- |
| December pressure years | 12 / 19 | pass |
| Mean December excess negative | `-0.003163649396` | pass |
| Median January excess positive | `+0.001691037463` | pass |
| Replay and integrity | — | pass |
| **January reversal (5 bps)** | **10 / 19** | **fail** (14 required) |
| **January reversal (15 bps)** | **9 / 19** | **fail** |

## Half the mechanism is there. The tradeable half is not.

This is the most scientifically interesting result the program has produced,
because it is a *partial* confirmation rather than a flat null.

**The forced selling is visible.** Year-to-date losers underperformed the
universe into year-end in 12 of 19 Decembers, with a mean December excess of
`-0.003163649396` and a median of `-0.004835391288`. That is the footprint the
tax-code mechanism predicts, and it is present.

**The reversal is not.** January excess was positive in 10 of 19 years —
binomial `p = 0.500000000000`, an exact coin flip. At stress costs it falls to
9 of 19. Whatever pressure December applies, liquid ETFs do not reliably
rebound from it in January.

**The two legs are linked, which corroborates the mechanism without rescuing
the trade.** Correlation between December and January excess is
`-0.418862185790`: the harder losers were pushed down in December, the harder
they bounced in January. 2022 is the clearest case — the largest December
pressure of the sample at `-0.038994835676` and the largest January reversal at
`+0.043687147162`. The mechanism is real and it shows up in the cross-section
of years. It is simply too unreliable, year to year, to trade.

## The protocol did the job it was designed for

The preregistration required *both* legs specifically so a January-only result
would fail. It received the mirror image — a December-only result — and failed
that too, which is the correct and symmetric outcome. A weaker protocol would
have reported "tax-loss selling pressure confirmed, mean −32 bps, 12 of 19
years" and buried the fact that none of it converts into a return.

Note also that the December gate passing at 12 of 19 is *not* itself
statistically strong: `p = 0.179641723633`. It was preregistered as a coherence
check, not as evidence, and it should not be quoted as though it were the
latter.

## What this does and does not establish

- It does **not** refute tax-loss selling. The effect is documented strongest
  in small, illiquid, heavily-lossed individual equities. This test ran on
  liquid ETFs precisely because a clean small-cap universe is unavailable
  without survivorship-contaminated symbol lists, and that substitution was
  disclosed in advance as a reason a null could occur even if the mechanism is
  real.
- It **does** establish that the ETF-level expression of the effect is not
  tradeable on this universe over 19 cycles at realistic costs.
- The universe was not vault-fresh, which was disclosed at registration. That
  weakens a positive result, not a negative one, so it does not affect this
  closure.

## Boundary

Historical evidence only. No validated alpha, no forward-shadow slot claimed,
no paper or live authority. The quintile cut, formation date, holding window,
universe, and thresholds are frozen; the detector is not re-run on a different
universe or a different holding period.

## Safety

Fully offline. No network access, no credential access, no broker or account
access, no paper mutation, no live activity. Existing caps, receipts,
reconciliation, and live prohibitions are unchanged.
