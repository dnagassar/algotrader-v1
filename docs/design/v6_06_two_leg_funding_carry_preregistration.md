# V6.06 continuously-held funding carry, two legs — forward shadow preregistration

Frozen before any observation exists. Identical hypothesis, gates, index
construction and decision model to
[V6.05](v6_05_continuously_held_funding_carry_preregistration.md); the universe
is BTC and ETH only.

## Disclosure, first, because it is the reason this document exists

**V6.05's three-leg shadow was registered and then blocked**, because
`SOL_USDC-PERPETUAL` fails the mandated signal-to-noise precondition at a
basis-to-funding ratio of `11.07` against a `10.0` ceiling. V6.05 stays
registered and stays blocked; it is not withdrawn, edited, or re-pointed.

**This exclusion is not clean, and pretending otherwise would be worse than the
contamination.** Before the precondition was wired into the collector, a live
run wrote all three legs and their ten-day carry levels were visible to the
author:

| leg | ten-day carry, annualised | later ratio | retained here |
| --- | ---: | ---: | --- |
| `BTCCARRY` | `+0.0165` | 4.17 | yes |
| `ETHCARRY` | `-0.0039` | 5.09 | yes |
| `SOLCARRY` | `-0.0452` | 11.07 | **no** |

So the worst ten-day performer is the one dropped, and no amount of argument
makes that look like coincidence. What can be said, and checked:

- **The stated criterion is outcome-blind.** `basis / funding` measures whether
  the two price legs are synchronised. It never touches the carry's sign or
  size, and the ceiling of `10.0` was frozen in V5.99, long before these
  instruments were compared.
- **The retained set is not the profitable set.** `ETHCARRY` was mildly
  *negative* over the same ten days and is retained. A performance-driven
  exclusion would have dropped it too.
- **Ten days is noise, not a result.** At roughly 4% annualised funding, ten
  days carries about 0.1% of signal against basis moves an order of magnitude
  larger. None of the three figures above is evidence of anything.
- **The window is forward regardless.** The first admissible session falls
  strictly after this registration, so nothing observed before it can enter.

The honest summary: the criterion is defensible, the sequence is not, and a
reader is entitled to discount this registration accordingly. It is recorded
here rather than in a commit message so it cannot be read without it.

## The hypothesis

**Holding the perpetual funding carry continuously, rather than switching on the
sign of funding, earns a positive risk-adjusted excess after costs.**

Unchanged from V6.05. Direction is never consulted. The position is entered once
and held; the only decisions are monthly renewals.

## Universe and weights

| symbol | weight | series |
| --- | ---: | --- |
| `BTCCARRY` | `0.500000000000` | cumulative delta-neutral carry for BTC |
| `ETHCARRY` | `0.500000000000` | the same for ETH |
| `USDCASH` | benchmark | constant series |

Two legs rather than three means less diversification and a noisier per-decision
excess. The gates are **not** loosened to compensate; a two-leg book that cannot
clear the same bar has not earned a weaker one.

## Frozen construction, gates and decisions

Identical to V6.05 and repeated here so this document stands alone.

```
carry_return(t) = funding(t) + basis(t) - cost(t)
index(t)        = index(t-1) * (1 + carry_return(t))
```

`basis(t)` is V6.00's per-interval delta-neutral term,
`(index_t/index_{t-1} - 1) - (perp_t/perp_{t-1} - 1)`, used verbatim. Funding is
added because the book is short the perpetual. Cost is charged only on the
monthly renewal, at two legs, 5 bps each. Sessions failing
`validate_signal_to_noise` are **not observed**, never observed as zero.

| gate | value |
| --- | --- |
| minimum decisions | `8` |
| minimum annualised return | `0.020000000000` |
| minimum Sharpe | `0.500000000000` |
| maximum drawdown | `0.150000000000` |
| minimum benchmark annualised delta | `0.020000000000` |
| minimum benchmark Sharpe delta | `0.500000000000` |
| cost | `5.000000000000` bps per one-way leg |

Wald SPRT on per-decision excess: `alpha 0.05`, `beta 0.20`, minimum excess
`0.010000000000`, reference sigma `0.040000000000`, no stopping before eight
decisions. A decision is a monthly renewal, so eight decisions is about eight
months.

## The tail risk, stated before the fact

A permanently held short perpetual can face funding inverting and staying
inverted while the short leg is marked against the book. V6.00's switching rule
never held long enough to meet it. That is why the drawdown ceiling is `0.15`
rather than the registry default of `0.30`, and why it is a hard gate. **If it
is breached the hypothesis fails; it is not re-run with a stop-loss.**

## How this fails

- fewer than eight completed decisions: **no verdict**, not a provisional one
- SPRT crosses futility: **closed early**, and closed means closed
- any terminal gate missed: **failed**, with no partial credit
- drawdown ceiling breached: **failed**, not re-run with risk management added
- the precondition blocking a majority of sessions: **void**, as V5.99 was

## Relationship to V6.05

V6.05 remains registered, blocked, and unedited. If `SOLCARRY` later clears the
precondition, V6.05 begins accruing on its own terms from that point, and the
two shadows are then separate hypotheses on overlapping data — which must be
disclosed as multiplicity if both ever report, not quietly treated as one
confirmation.

**No third funding-carry shadow may be registered.** Two is already one more
than the discipline intended.
