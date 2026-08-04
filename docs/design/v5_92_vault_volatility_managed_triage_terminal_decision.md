# V5.92 vault volatility-managed triage terminal decision

Status: terminally closed without tuning. The protocol was frozen at `a24198f`,
the allowlist at `b67aa35`, and the engine, tests, admission, and outcome-blind
receipt at `5ec8dd7` — all before the first per-market return, metric, count, or
route was computed. Route: `close_triage_without_tuning`.

## Immutable evidence

- Protocol: `v5_92_vault_volatility_managed_triage_v1`.
- Protocol SHA-256:
  `156a609fde58a25dec43fa539edb7d9156079b28505f10a167daff7f416eea62`.
- Data receipt SHA-256:
  `dfce4924d29039c30c1aa885b7c0266f090ec04d99224432d6e8ec683c487257`.
- Canonical data SHA-256:
  `9adafdd074bb93850204d0cd51f37eaae9a551ad50eb8f43c98440d2745a87ca`.
- Data manifest SHA-256:
  `db54db6fdc5b108864edc28d43853e4637c202b5957585e47e74a83e2c5aef31`.
- Artifact manifest SHA-256:
  `9cabe2f6be67b299e3ac6095c2e0364ac80ff365d44b7843ebc2538eeebd6f19`.
- Eighteen vault-eligible markets, 3,643 common sessions
  (`2012-02-03`..`2026-07-31`), 3,582 scored, 170 decisions per market, 3,060
  decisions in total. Two replays byte-identical.

## Gate outcome

| Gate | Result | Outcome |
| --- | ---: | --- |
| Primary: Sharpe wins at 5 bps | 2 / 18 | **fail** (13 required) |
| Stress Sharpe wins at 15 bps | 1 / 18 | **fail** |
| Second-half Sharpe wins at 5 bps | 0 / 18 | **fail** |
| Median Sharpe improvement | `-0.050266420387` | **fail** |
| Drawdown wins at 5 bps | 17 / 18 | pass |
| Replay and integrity | — | pass |

The one-sided binomial p is `0.999927520752`. This is not a marginal miss like
V5.91; it is decisive evidence in the opposite direction. Only GREK
(`0.058196203122`) and NORW (`0.003867528488`) improved Sharpe at all, and in
the second half of the window not a single market did.

## What actually happened

The mechanism is legible in the per-market table. Average target weight ranged
from `0.5232` (TUR) to `0.8655` (ENZL). Because emerging-market realized
volatility sits far above the frozen 15% annualized target, the cap at 1.0
almost never binds and the rule is *persistently under-invested*. Annualized
return fell versus buy-and-hold in 16 of 18 markets while maximum drawdown
improved in 17 of 18.

So the rule reliably bought drawdown protection and reliably paid for it in
return — and at these exposures the exchange was Sharpe-negative. Realized
one-way turnover of roughly 0.72 to 0.93 per year compounded the cost, which is
why the stress gate collapsed to 1 of 18. The preregistration flagged that
continuous rebalancing would make the 15 bps gate load-bearing rather than
decorative; it was.

## The specification caveat that matters most

This tested a **de-risking-only** variant of volatility management, and that is
a real departure from the source.

Moreira and Muir's construction scales exposure inversely to variance in *both*
directions — it levers **up** in calm periods, which is where a substantial part
of the published effect originates. The repository forbids leverage, so the
frozen rule capped weight at 1.0. The upside half of the mechanism was
therefore never available to it.

The honest reading is consequently narrow: **volatility-capped exposure with no
leverage did not improve risk-adjusted returns on eighteen untouched markets**.
This is not a refutation of volatility-managed portfolios as published, and it
should not be reported as one. It does say that the half of the mechanism
available under this repository's constraints is not, on its own, worth having.

Two further limits: the frozen 15% target is one constant, and a higher target
would leave the rule closer to fully invested. Choosing a different constant now
would be precisely the tuning the protocol forbids, and given a 2-of-18 primary
and 0-of-18 second half, no plausible constant rescues this. Any such test is a
new hypothesis requiring fresh untouched data, and no untouched single-country
equity cohort remains.

## The pattern across both triages

V5.91 and V5.92 tested different mechanisms — binary directional trend and
continuous risk sizing — on two disjoint sets of eighteen never-acquired
markets, 36 markets in total. They agree on the finding that matters:

- Drawdown improved almost universally: 18 of 18 in V5.91, 17 of 18 in V5.92.
- Annualized return fell in the large majority of markets in both.
- Neither cleared a cost-robust, regime-consistent Sharpe bar.

That is now a replicated cross-sectional result on markets this repository had
never seen, not a single-window artifact. Defensive overlays purchase drawdown
reduction and pay for it in return, and at realistic costs the exchange has not
been favorable. It is the same trade V5.88 and V5.89 documented on contaminated
US-centric data, confirmed here on clean data.

Mean pairwise excess correlation was `0.422316794291`, materially below V5.91's
`0.630936283855` — the emerging-market cohort is closer to independent, which
strengthens rather than weakens this negative result.

## Boundary

Historical evidence, not forward evidence. No validated-alpha claim. No
forward-shadow slot is claimed, and no paper, broker, or live authority follows.
The closure applies to this exact rule under these exact gates; the rule is not
re-run on a third cohort.

## Trust and safety

Eighteen market-data requests were GET-only, destination-allowlisted, and
recorded `token_value_recorded`, `market_data_token_value_printed`, and
`market_data_token_value_written` as `false`. The scored replay was offline,
deterministic, and credential-free. Network access by the engine, broker,
account, order, and position access, paper mutation, and live activity were all
false. External performance figures remained untrusted and controlled no gate.
Existing caps, receipts, reconciliation, sleeve ownership, and live prohibitions
are unchanged.
