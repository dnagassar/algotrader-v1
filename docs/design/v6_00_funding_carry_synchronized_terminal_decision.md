# V6.00 funding carry, synchronized marks — terminal decision

Status: terminally closed. Route `close_detector_without_tuning`. Protocol
frozen at `ed86af5b`, engine at `a1634e2`, both before any V6.00 return existed.

Unlike V5.99, **this measurement is valid and the result stands.**

## The alignment fix worked

| | V5.99 (void) | V6.00 |
| --- | ---: | ---: |
| Basis-to-funding ratio | 65.5 | **3.4 – 4.2** |
| Worst single interval | `-0.069865275549` | `-0.002564089013` |

The signal-to-noise guard passed for all three symbols. A worst interval of
0.26% is what a delta-neutral book should look like; the 7% of V5.99 never was.
The perpetual mark is now the chart close at tick `T − 1h`, established by level
agreement (3.8 basis points mean premium) before any strategy return was
computed.

## Result

- Panel: 4,796 eight-hour intervals, `2022-03-16`..`2026-08-01`.
- Annualised `-0.061849041342` at decision costs, `-0.317041910069` at stress.
- Maximum drawdown `0.245661428187`, against a `0.15` ceiling.
- Positive quarters: 1 of 4. Positive symbols: 0 of 3.
- Five of six gates fail; only replay integrity passes.
- Result SHA-256:
  `6c648fe15e03e3afd640522c675200c713fd093aebabfa792be20163216ff12f`.

## The carry is real. The rule destroys it.

Decomposing each symbol's cumulative profit and loss settles the mechanism
rather than leaving it to inference:

| Symbol | Position flips | Cost at 5 bps | Funding collected | Basis P&L | Net |
| --- | ---: | ---: | ---: | ---: | ---: |
| BTC-PERPETUAL | 685 | `-0.6850` | `+0.2569` | `+0.0648` | `-0.3634` |
| ETH-PERPETUAL | 733 | `-0.7330` | `+0.2128` | `+0.0749` | `-0.4453` |
| SOL_USDC-PERPETUAL | 667 | `-0.6670` | `+0.4870` | `+0.1502` | `-0.0298` |

Every component of the structural claim survives. Funding was positive in 72%,
65%, and 59% of intervals. It was collected in size — 26%, 21%, and 49%
cumulative. The basis leg was even mildly *favourable*, contributing between
`+0.0648` and `+0.1502`.

The loss is entirely transaction costs. The preregistered signal — hold whenever
funding is positive, otherwise flat — flipped position **667 to 733 times** over
4.4 years, roughly every seventh interval, because funding oscillates around
zero. At two legs per flip that is 67 to 73 percentage points of cost against
21 to 49 points of funding. The trade earns what the structure says it should
and then hands back three times as much in fees.

This is a rare and clean outcome: a hypothesis where the economic premise is
confirmed and the *implementation* is what fails. The negative Sharpe of
`-4.251310220835` on a `-0.002564089013` worst interval is the signature — a
steady low-variance bleed, not tail risk.

## Not rescued, deliberately

A continuously-held variant that ignores funding's sign would avoid nearly all
of this churn, and the table above makes it obvious that it would look far
better. That is precisely why it is not run here.

The signal rule, holding interval, cost assumptions, and thresholds were frozen
before the data was scored. Changing the entry rule after seeing which
component caused the loss is the definition of the tuning this program forbids,
and the fact that the fix looks obvious in hindsight is what makes the
prohibition worth having. A continuously-held carry is a **different
hypothesis**; it needs its own preregistration, its own untouched evaluation,
and honest accounting for the tail risk that permanent exposure carries — the
risk this rule was, however expensively, avoiding.

## Boundary

Historical evidence only. No validated alpha. No forward-shadow slot claimed.
No paper, broker, or live authority; execution would additionally require
derivatives venue access this repository does not have and is not seeking.
Liquidation remains unmodelled, so the true tail of any perpetual-short strategy
is worse than reported.

## Trust and safety

Offline scoring over already-acquired public data; no new network access. No
credentials requested, loaded, printed, or persisted. No broker, account, order,
or position access. No paper mutation. No live activity. Live capital remains an
operator hard gate.
