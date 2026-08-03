# V5.89 Keller Bold Asset Allocation terminal decision

Status: terminally closed without tuning. The protocol was frozen at `e77eede`,
the data allowlist at `7dc2439`, and the engine, tests, data admission, and
outcome-blind receipt at `722363a` — all before the first candidate target,
return, metric, gate, rank, or route was computed. Unlike V5.88, the scoring
engine entered history strictly before the reveal. No failed parameter was
changed, rescued, substituted, or relabeled.

## Immutable evidence

- Protocol: `v5_89_keller_bold_asset_allocation_v1`.
- Protocol SHA-256:
  `b000c85a4ce041a26cfe3eedace3439177456d2507d8a71c08ed8e0740262747`.
- Data receipt SHA-256:
  `bad57306a3bf9baafe2c2b2bb0422b83f66286ed686ee8f03cef41dc4109cc5c`.
- Canonical data SHA-256:
  `a8a2b4ceb6d5aa22001e8967d741e51bb6246985ade55f7ea9fc79b69d677543`.
- Outcome-blind data manifest SHA-256:
  `40b595bab9156d586302aab9595c47a38fad9d7c018dd62c612a0970242b2c77`.
- Artifact manifest SHA-256:
  `23da616de2164440937ed7b82f0232628ac84c450b4231c32292d2ede67e18ae`.
- Seventeen ETFs, 4,784 common sessions, `2007-07-26`..`2026-07-31`; OOS
  `2022-09-01`..`2026-07-31` with 981 sessions and 47 monthly actions.
- Two complete result and manifest replays were byte-identical.

## Decision-cost evidence

At 5 basis points per unit of one-way turnover over the post-publication OOS
window:

| Strategy | Annualized return | Sharpe | Max drawdown |
| --- | ---: | ---: | ---: |
| `baa_g4_aggressive_proxy` | `0.025959215654` | `0.242205405046` | `0.172615471141` |
| `baa_g12_balanced_proxy` | `0.042155760975` | `0.450180213726` | `0.125977439779` |
| `no_canary_g4_always_offensive` | `0.207342240987` | `1.063066618918` | `0.218264159654` |
| `no_canary_g12_always_offensive` | `0.152312452512` | `1.129770356469` | `0.125725113662` |
| `static_equal_g12_monthly` | `0.136478449016` | `1.157843427115` | `0.108422341806` |
| `spy_ief_60_40_monthly` | `0.120345665645` | `1.140561942395` | `0.105755776119` |
| `spy_buy_and_hold` | `0.192940267748` | `1.171451580490` | `0.187553882874` |

Both candidates failed every one of the five terminal gate groups: common
viability, static baseline, closest ablation, SPY value route, and
portfolio-level value. Fold total returns were `0.010681022539`,
`-0.078180160199`, `0.185953647286` for G4 and `-0.044450867159`,
`-0.034633318000`, `0.273103911239` for G12, so the every-fold-positive
condition failed for both. Stress-cost Sharpe was `0.201707952712` (G4) and
`0.390199007173` (G12), below the required `0.50`.

The mechanism failure is unambiguous and is the most informative result the
program has produced. The canary breadth rule placed both candidates in the
defensive universe in 22 of 47 months. Removing only that feature, holding
data, lag, drift, cash, costs, and selection identical, produced:

- G4: annualized return `0.207342240987` versus the candidate's
  `0.025959215654` — the canary overlay cost 18.14 annualized points and
  0.821 Sharpe;
- G12: annualized return `0.152312452512` versus the candidate's
  `0.042155760975` — the canary overlay cost 11.02 annualized points and
  0.680 Sharpe.

Both ablations also beat the candidates on drawdown-adjusted terms in the G12
case (`0.125725113662` versus `0.125977439779`). The published crash-protection
feature was therefore not merely unrewarded in this window; it was the single
largest source of underperformance, and it did not buy meaningful drawdown
relief. Both genuine 80/20 composites reduced parent Sharpe (`-0.148332991576`
for G4, `-0.058808999296` for G12) and parent annualized return.

The exact route is `no_candidate_passed`. Both candidates are ineligible for
shadow, paper, broker, or live promotion.

## Interpretation and boundary

This is a statement about one exactly specified rule family on one short
post-publication window, not a claim that Bold Asset Allocation is invalid.
The 47-month OOS window was disclosed in advance as short and was dominated by
a strong US equity advance, which is precisely the regime in which a
canary-triggered defensive rotation is expected to lag. That expectation does
not rescue the candidate: the gates were frozen before the reveal and they
failed, and "the regime was unfavorable" is exactly the kind of post-hoc
rationalization this protocol exists to refuse.

## Trust and safety

All external source and tracker performance figures remained untrusted and
controlled no rank or gate. The tournament replay was offline, deterministic,
and credential-free; the wrapper fails closed on any credential-bearing
environment variable. The seventeen market-data requests were GET-only,
destination-allowlisted, and recorded `token_value_recorded`,
`market_data_token_value_printed`, and `market_data_token_value_written` as
`false`. Network access by the engine, NexusTrade mutation, broker/account/
order/position access, paper mutation, and live activity were all false.
Existing execution caps, reconciliation, receipts, sleeve ownership, and live
prohibitions were unchanged.
