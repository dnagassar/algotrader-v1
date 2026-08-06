# V6.05 continuously-held funding carry — forward shadow preregistration

Frozen before any observation exists. This is the first hypothesis ever
registered in the V5.90 forward-shadow registry, which was built in V5.90 and
left pointing at nothing.

**This is not a fix to V6.00.** V6.00's rule is closed and may not be re-run
with a different entry condition. This is a separate hypothesis with its own
gates, its own window, and its own way of failing.

## Why this hypothesis and not another

Across twenty-eight milestones this is the only one whose *economics* were
confirmed while only the implementation failed. V6.00 measured, on synchronised
marks:

- funding positive in **72% / 65% / 59%** of intervals for BTC / ETH / SOL
- cumulative funding collected of **21-49%** over 4.4 years
- a mildly favourable basis leg
- and a net loss caused entirely by churn — the frozen signal flipped whenever
  funding crossed zero, **667-733 times**, at two legs per flip

The premise is real and collectable. The question this shadow asks is the one
V6.00 could not: does it survive when you stop trading it?

## The hypothesis

**Holding the perpetual funding carry continuously, rather than switching on the
sign of funding, earns a positive risk-adjusted excess after costs.**

Direction is never consulted. The position is entered once and held; the only
decisions are monthly renewals.

## How it is represented, and why that representation is honest

The registry models long-only weights over symbols whose returns come from local
daily bars, with weights non-negative and summing to at most one. A short-perpetual
carry cannot be written as a negative weight, so it is represented as a **long
position in a synthetic carry index**:

| symbol | series |
| --- | --- |
| `BTCCARRY` | cumulative delta-neutral carry for BTC: funding received, plus basis convergence, minus financing and costs |
| `ETHCARRY` | the same for ETH |
| `SOLCARRY` | the same for SOL |
| `USDCASH` | constant series, the benchmark |

A daily change in `BTCCARRY` **is** the carry earned that day on a one-unit
delta-neutral book. Holding weight `1/3` in each of the three earns exactly the
equal-weighted carry. The registry's arithmetic is then faithful rather than
approximate — it is not modelling price drift and calling it carry.

`USDCASH` is flat, so benchmark deltas equal the strategy's own figures. That is
the correct benchmark for a market-neutral book: the alternative to running it is
holding cash, not holding crypto.

**The index construction is frozen here.** Per symbol, per session, on Deribit
data via the existing `perp_funding_refresh_adapter`, using V6.00's
`_PERP_TICK_OFFSET_MS` alignment and its `validate_signal_to_noise` precondition:

```
carry_return(t) = funding_received(t) + (basis(t) - basis(t-1)) - cost(t)
index(t)        = index(t-1) * (1 + carry_return(t))
```

with `cost(t)` charged only on the monthly renewal at 5 bps per one-way leg. Any
session failing the signal-to-noise precondition is **not observed** rather than
observed as zero — a blocked panel is missing evidence, not flat evidence.

## Decisions, and why monthly

A continuously-held rule makes no daily choices, so counting days as evidence
would be false power — the exact failure the registry's decision model exists to
prevent. A decision here is a **monthly renewal**: the book is re-struck, costs
are paid, and the rule may exit on a risk gate. Eight decisions is therefore
about eight months.

## Frozen gates

| gate | value | why this value |
| --- | --- | --- |
| minimum decisions | `8` | eight monthly renewals before any terminal verdict |
| minimum annualised return | `0.020000000000` | must beat cash by enough to be worth balance-sheet risk |
| minimum Sharpe | `0.500000000000` | a real carry should be high-Sharpe; below this it is not worth the tail |
| maximum drawdown | `0.150000000000` | V6.00's ceiling for the same economics, kept rather than loosened |
| minimum benchmark annualised delta | `0.020000000000` | against flat cash, so identical to the return gate |
| minimum benchmark Sharpe delta | `0.500000000000` | same, stated explicitly rather than inherited |
| cost | `5.000000000000` bps per one-way leg | as V6.00 |

Sequential boundaries, Wald SPRT on per-decision excess:
`alpha 0.05`, `beta 0.20`, `minimum excess per decision 0.010000000000`
(one point a month), `reference sigma 0.040000000000`, no stopping before eight
decisions. Sigma is declared in advance as a commitment, not fitted later.

## The tail risk, stated before the fact

A permanently held short-perpetual position carries a real hazard the switching
rule did not: in a violent rally, funding can invert and stay inverted while the
short leg is marked against the book. V6.00 never held long enough to face it.

This is why the drawdown ceiling is `0.15` and not the registry's `0.30` default,
and why it is a hard gate rather than a preference. **If the shadow breaches it,
the hypothesis fails — it is not re-run with a stop-loss.**

## How this fails

Stated now so the failure cannot be renegotiated later:

- fewer than eight completed decisions in the window: **no verdict**, not a
  provisional one
- SPRT crosses the futility boundary: **closed early**, and closed means closed
- any terminal gate missed: **failed**, with no partial credit for the others
- drawdown ceiling breached: **failed**, and not re-run with risk management
  bolted on
- signal-to-noise precondition blocking a majority of sessions: **void**, as
  V5.99 was, rather than reported on thin data

A negative result here is a real result. It would be the first uncontaminated
one this program has produced.

## What is not yet built

Registration is the commitment; it does not create evidence. Feeding this shadow
needs a daily collector that produces the four canonical series above. That is
the single follow-on task, and it is deliberately the only one — no further
hypotheses may be registered until this window closes.

The ledger will therefore begin whenever the collector starts, not at
registration. The registry forbids backfilling that gap, which is correct: the
window measures what was observed forward, not what could be reconstructed.

## Safety

Research-only. The registry cannot reach a network, load a credential, read a
broker, plan an order, mutate a paper account, or authorise capital, and records
all twelve zero-authority booleans on every write. No live capital, no order
submission, no profit claim.
