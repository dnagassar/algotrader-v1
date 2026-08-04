# V5.91 vault cross-sectional trend triage terminal decision

Status: terminally closed without tuning. The protocol was frozen at `09cf026`,
the allowlist at `7f3ade7`, and the engine, tests, admission, and outcome-blind
receipt at `559a5ef` — all before the first per-market return, metric, count,
or route was computed. Route: `close_triage_without_tuning`.

## Immutable evidence

- Protocol: `v5_91_vault_cross_sectional_trend_triage_v1`.
- Protocol SHA-256:
  `a1d9c90face12c565dc2b434aaa8ad5ea59754fec29c90bba761279a72938f12`.
- Data receipt SHA-256:
  `5038958d293e10c9f61b97ab2697a4cb685196cb38a77eeb7314823cab7eea65`.
- Canonical data SHA-256:
  `af28aa4d21084d62b0936b5127a8e43624482bea2c511db7cdafb8d25c637ca6`.
- Data manifest SHA-256:
  `5139ad556a405337514438688f2a2a436ce2a604730433314be3df9b310e3929`.
- Artifact manifest SHA-256:
  `31801c0f39354b787637f34bda6d586de041e797947036b7ce6a47962c1619af`.
- Eighteen vault-eligible markets, 6,550 common sessions
  (`2000-07-14`..`2026-07-31`), 6,350 scored, 303 decisions per market,
  5,454 decisions in total. Two replays byte-identical.

## Gate outcome

| Gate | Result | Outcome |
| --- | ---: | --- |
| Primary: Sharpe wins at 5 bps | 13 / 18 | **pass** (binomial p = `0.048126220703`) |
| Drawdown wins at 5 bps | 18 / 18 | pass |
| Median Sharpe improvement | `0.029579505078` | pass |
| Replay and integrity | — | pass |
| Stress Sharpe wins at 15 bps | 10 / 18 | **fail** (13 required) |
| Post-2007 Sharpe wins at 5 bps | 6 / 18 | **fail** (12 required) |

The primary gate passed at exactly its threshold. Two secondary gates failed,
and the protocol requires all of them, so the route is closure. Nothing is
re-run with a different moving average.

## What actually happened

This is the most diagnostically useful failure the program has produced,
because the two failures are not noise — they identify precisely where the
apparent edge came from.

**The effect is almost entirely pre-2008.** Over the full window the rule beat
its own market's buy-and-hold on Sharpe in 13 of 18 markets. Over the post-2007
sub-window it won in **6 of 18** — slightly worse than a coin flip. Since the
full window is the union of the two, essentially the entire cross-sectional
edge is carried by 2001-2007, a span containing the tail of the dot-com bear
market. That is exactly the regime in which absolute trend following is
expected to shine, and exactly why the consistency gate was preregistered: it
exists to detect an effect that lives entirely in early history. It did.

**The effect does not survive realistic costs.** Raising the cost assumption
from 5 bps to 15 bps per unit of one-way turnover drops Sharpe wins from 13 to
10. An edge that evaporates between two plausible cost assumptions is not a
robust edge.

**Drawdown improvement is real and universal.** All 18 of 18 markets improved
maximum drawdown, several by more than 30 percentage points (EWK
`0.460111204389`, EWI `0.377129134780`, EWY `0.363726151245`). This is the
genuine, replicable property of absolute trend following, and it replicated on
markets this repository had never touched. It is also not what the primary gate
asked for, and it is not sufficient on its own — annualized return was *lower*
than buy-and-hold in 13 of 18 markets. The rule buys drawdown protection by
giving up return, which is the same trade V5.88 and V5.89 documented.

**Independence was overstated, as disclosed.** Mean pairwise correlation of the
per-market excess return series is `0.630936283855`. Eighteen markets at that
correlation are worth far fewer than eighteen independent experiments, so the
nominal `p = 0.048` overstates significance considerably. This was preregistered
as a disclosure rather than an adjustment, and it does not change the route: the
milestone already fails on its own secondary gates. Had the primary gate been
the only test, this correlation would have been the reason to distrust it.

## What this cost and what it bought

The triage consumed roughly one working session end to end: eighteen GET-only
requests, an admission, and one scored run. It evaluated 5,454 decisions across
eighteen markets. For comparison, V5.89 rested on 47 decisions in one market,
and a six-month forward shadow of a monthly rule would have produced six.

The vault premise held mechanically. All eighteen markets were confirmed never
previously acquired before the protocol was written; EWJ was excluded because
the same scan flagged it as already touched during V5.88. This result is
therefore free of *our* selection bias, and the fast negative is precisely what
the triage layer exists to produce: a published effect was screened out in
hours rather than after a six-month forward window.

## Boundary

This is historical evidence, not forward evidence, and no validated-alpha claim
is made or implied. Absolute trend following remains a published effect whose
authors saw global market history, so author-side selection was never removed by
this design — only ours was. The closure applies to this exact rule under these
exact gates; it is not a claim that trend following "does not work," but the
narrower and more useful finding that on eighteen untouched markets it did not
clear a preregistered cost-robust, regime-consistent bar.

No forward-shadow slot is claimed. No paper, broker, or live authority follows.

## Trust and safety

Eighteen market-data requests were GET-only, destination-allowlisted, and
recorded `token_value_recorded`, `market_data_token_value_printed`, and
`market_data_token_value_written` as `false`. The scored replay was offline,
deterministic, and credential-free. Network access by the engine, broker,
account, order, and position access, paper mutation, and live activity were all
false. External source and tracker performance figures remained untrusted and
controlled no gate. Existing caps, receipts, reconciliation, sleeve ownership,
and live prohibitions are unchanged.
