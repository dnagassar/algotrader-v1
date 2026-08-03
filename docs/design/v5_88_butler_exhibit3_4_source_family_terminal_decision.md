# V5.88 Butler Exhibit 3/4 source-family terminal decision

Status: terminally closed without tuning. The corrected v2 protocol was frozen
at `cd99b9f` and the outcome-blind data admission was committed at `b4d6aee`
and `7e9c672` before any candidate target, return, metric, gate, rank, or
route was computed. The implementation session was interrupted before the
engine's own pre-reveal commit, so the engine, tests, and wrapper enter
history together with this closure; the engine is pinned by SHA-256 in the
artifact manifest, validates every frozen input hash before scoring, and was
not modified after the first outcome reveal. No failed parameter was changed,
rescued, substituted, or relabeled.

## Immutable evidence

- Protocol: `v5_88_butler_exhibit3_4_source_family_v2`.
- Protocol SHA-256:
  `fecab8bc4233afc71fd95324c913a0380b72607e14232f2e20663327b27fa0ff`.
- Data receipt SHA-256:
  `e14ead322a5c48a1d48281928ffb4c36c51f8a17285b78aaf5de904f772f10f0`.
- Canonical data SHA-256:
  `157c1b2ba18e440730c65e38173ab836aeb8805806a1ecbb45be28b6d90206d0`.
- Outcome-blind data manifest SHA-256:
  `58a9efafd610db5ba11272d32dac4cc9fe8681be8a832a8a3b89fd320cc81b56`.
- Engine SHA-256:
  `f067dc1834f4be6a05ed8ecb7b18584a1a38534ebde613a4bd2bc0157fa5f496`.
- Evaluation result SHA-256:
  `16df4950e06848346c434f6c54b3bd9e73b995efe195064ac61e81eabea62166`.
- Artifact manifest SHA-256:
  `a0427681bfde7216fe2595cf5a7786dd41f8711ed345bdfdbb6d3017f406fa3c`.
- Two complete result and manifest replays were byte-identical.

## Decision-cost evidence

At 5 basis points per unit of one-way turnover over the 2014-04-01 through
2026-07-31 OOS window:

- `butler_exhibit3_top5_6m_equal_weight_proxy`: annualized return
  `0.084224208466`, Sharpe `0.789530970921`, maximum drawdown
  `0.205276496335`, total return `1.705823080204`. Fold total returns were
  `0.286403188155`, `0.398483633180`, and `0.504059098229`. Stress-cost
  annualized return `0.081681424663`, stress Sharpe `0.768244001881`.
- `butler_exhibit4_top5_6m_capped_volatility_proxy`: annualized return
  `0.072378513608`, Sharpe `0.756182315746`, maximum drawdown
  `0.171571105580`, total return `1.363582175276`. Fold total returns were
  `0.278040396491`, `0.266137497587`, and `0.460646942386`. Stress-cost
  annualized return `0.069629079058`, stress Sharpe `0.730223216041`.
- SPY buy-and-hold: annualized return `0.137397873648`, Sharpe
  `0.831767405652`, maximum drawdown `0.336999404706`.

Both candidates passed the common viability and static-baseline gates.
Exhibit 3 diverged from `constant_score_top5_equal_weight` on 147 of 148
monthly decisions and passed its closest-ablation gate (Sharpe delta
`0.156124999975`, drawdown improvement `0.049071375854`). Exhibit 4 diverged
from Exhibit 3 on 104 decisions but failed its closest-ablation value gate:
volatility sizing reduced Sharpe by `0.033348655175`, failing the 0.03
Sharpe-improvement path, and although its drawdown improvement of
`0.033705390755` met the 5% relative threshold, the annualized-return drag of
`0.011845694858` exceeded the 1-point allowance, failing the alternative
path.

Both candidates failed the SPY value route and the portfolio-level value
gate:

- Versus SPY, Exhibit 3's annualized return delta was `-0.053173665182` and
  Sharpe delta `-0.042236434731`; Exhibit 4's were `-0.065019360040` and
  `-0.075585089906`. Neither the defensive nor the growth route's return and
  Sharpe conditions were met, despite drawdown improvements of
  `0.131722908371` and `0.165428299126`.
- The genuine 80% 60/40 parent plus 20% candidate composites improved full
  Sharpe by only `0.013591429317` (Exhibit 3) and `0.011231891400`
  (Exhibit 4), below the required `0.02`, and the positive composite
  log-return improvement was fold-concentrated beyond the 70% ceiling.

The exact route is `no_candidate_passed`. Both candidates are ineligible for
shadow, paper, broker, or live promotion. This closes the third preordered
source family after V5.86 and V5.87; validated alpha remains zero.

## Trust and safety

All external source performance figures remained untrusted and controlled no
rank or gate. The tournament replay was offline and credential-free; the
wrapper fails closed if any credential-bearing environment variable is
present, and the credential preflight observed zero ambient aliases. Network,
NexusTrade, broker/account/order/position access, paper mutation, and live
activity were all false. Existing execution caps, reconciliation, receipts,
sleeve ownership, and live prohibitions were unchanged.
