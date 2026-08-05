# V6.00 funding carry, synchronized marks

Status: frozen before any V6.00 return, metric, or route was computed. A new
milestone, not a re-run: V5.99 closed inconclusive on a measurement defect, and
its numbers remain void.

## 1. What changed, and only this

**Every scoring rule is inherited from V5.99 unchanged**: the same three
symbols, the same short-perpetual/long-spot position taken when funding is
positive, the same 8-hour interval, the same 5 and 15 basis-point costs per leg
per side, the same 0.15 drawdown ceiling, the same four gates on annualised
return, cost robustness, quarterly consistency, and per-symbol breadth. Nothing
about the hypothesis or its thresholds has been touched.

The single change is the **timestamp alignment of the perpetual price**.

## 2. The defect and how the correction was determined

V5.99 compared the index price stamped at funding timestamp `T` against the
perpetual chart close at tick `T`. Deribit's chart ticks are bar **open**
times, so the close at tick `T` is the price at `T + 1h`. The two legs were
therefore sampled an hour apart, and in crypto an hour is a large move. The
resulting basis noise ran roughly 100x the funding signal it was meant to
measure, which is why the run was voided rather than reported.

The correct offset was established by a **physical criterion, not by optimising
any result**: a perpetual trades within a fraction of a percent of its own
index at every instant, so the true alignment is whichever offset makes the two
*levels* agree. Measured across five candidate offsets on the full history:

| Offset | BTC mean absolute premium | ETH mean absolute premium |
| --- | ---: | ---: |
| −2h | `0.003996` | `0.005300` |
| **−1h** | **`0.000376`** | **`0.000400`** |
| 0h | `0.004007` | `0.005312` |
| +1h | `0.005676` | `0.007561` |
| +2h | `0.006963` | `0.009275` |

At `−1h` the premium is 3.8 basis points, which is what a liquid perpetual's
premium should be. Every other offset is an order of magnitude worse and simply
inherits the price move over the mismatch. The conclusion is forced by the
data's own structure, and it was determined **before any V6.00 strategy return
was computed**.

Accordingly: the perpetual price at funding timestamp `T` is the chart close at
tick `T − 1h`.

## 3. Precondition retained

The V5.99 signal-to-noise guard stays in force and is not relaxed for this run.
If corrected alignment still leaves basis noise above 10x the funding signal,
the milestone blocks rather than reporting a number. The guard is what caught
this defect; loosening it to let the retry through would defeat its purpose.

## 4. Expectation

Unchanged from V5.99, and worth restating because a working measurement is not
a promising one. The funding carry is a crowded, well-known trade run at scale
by desks with better fees and cross-venue netting. The prior remains that any
surviving return is thin and is compensation for tail risk rather than
inefficiency, which is what the drawdown gate exists to detect.

Liquidation is still not modelled. Real margin calls arrive precisely when the
short-perpetual leg is worst, so the true tail is worse than anything reported
here. A pass is an upper bound on attractiveness, never a lower bound.

## 5. Safety

Offline scoring over already-acquired public data. No new network access, no
credentials, no broker, no paper mutation, no live activity. Live capital
remains an operator hard gate.
