# V5.93 non-equity reversal triage terminal decision

Status: terminally closed without tuning. Protocol frozen at `0cc3297`
(committed), allowlist at `d1a3fa9`, engine/tests/admission/receipt at
`7518d40` — all before the first per-market return, metric, count, or route was
computed. Route: `close_triage_without_tuning`.

## Immutable evidence

- Protocol: `v5_93_nonequity_reversal_triage_v1`.
- Protocol SHA-256:
  `0cc32975be515949fe64f053cd63e5e1917eb1cd0429fdb6dd31a2e02694cd62`.
- Data receipt SHA-256:
  `e61592bab330600db2620c26ac8381ee6756bedc8426934a53886ef2df77078a`.
- Canonical data SHA-256:
  `953580d614bb3908620786e3fb9e8ee29dcdfab23dcf4cb19c2edaa0f99e1c06`.
- Data manifest SHA-256:
  `b94eac83a9378f211836d8ea1749bd8d6beeddc6ff7bfd4cb1245f5b73298291`.
- Artifact manifest SHA-256:
  `6fcb83441bd0572c23e6ee90016eed459b02aca6089a802d67a63a5e675c2a01`.
- Eighteen non-equity markets, 4,403 common sessions
  (`2009-01-29`..`2026-07-31`), 4,381 scored, 208 decisions per market, 3,744
  in total. Two replays byte-identical.

## Gate outcome

| Gate | Result | Outcome |
| --- | ---: | --- |
| Primary: Sharpe wins at 5 bps | 3 / 18 | **fail** (13 required) |
| Stress Sharpe wins at 15 bps | 2 / 18 | **fail** |
| Second-half Sharpe wins | 9 / 18 | **fail** (12 required) |
| Median Sharpe improvement | `-0.100142613067` | **fail** |
| Drawdown wins at 5 bps | 18 / 18 | pass |
| Replay and integrity | — | pass |

One-sided binomial `p = 0.999343872070`.

## Why this failure is the most informative of the three

Two properties make this the sharpest test the program has run.

**There was no bull market to lose to.** The standing explanation for V5.91 and
V5.92 was that defensive overlays underperform a rising benchmark. That
explanation is unavailable here. Buy-and-hold annualized returns across this
cohort include outright losses — `FXY` `-0.031900593776`, `USO`
`-0.025729906769`, `UNG` `-0.267741904232` — and the positives are modest. The
overlay still lost.

**The markets are nearly independent.** Mean pairwise excess correlation is
`0.195415663029`, against `0.630936283855` in V5.91 and `0.422316794291` in
V5.92. Eighteen markets at that correlation approach eighteen genuinely separate
experiments, so this negative carries far more evidential weight than the
nominal binomial figure alone suggests.

## The three wins prove the preregistered caveat

The rule beat buy-and-hold on Sharpe in exactly three markets: `FXC`
(`0.106749514523`), `FXY` (`0.255199380542`), and `UNG` (`0.182612342002`).
Those are precisely the three where buy-and-hold annualized return was
*negative*: `-0.001965151449`, `-0.031900593776`, and `-0.267741904232`.

`UNG` is the clearest case. Its apparent `+0.134526437418` annualized return
advantage is not alpha; it is the result of sitting in cash roughly 42% of the
time while a contango-eroded instrument decayed 27% per year. The
preregistration warned in advance that "beating a losing benchmark on Sharpe is
a weak achievement" and retained the median and drawdown gates specifically to
stop that from carrying a milestone. It did not carry it: the median Sharpe
delta was `-0.100142613067`.

## The finding is now replicated three times

| Milestone | Mechanism | Asset class | Sharpe wins | Drawdown wins | Excess corr. |
| --- | --- | --- | ---: | ---: | ---: |
| V5.91 | absolute trend | developed equity | 13 / 18 | 18 / 18 | 0.631 |
| V5.92 | volatility-capped sizing | emerging equity | 2 / 18 | 17 / 18 | 0.422 |
| V5.93 | short-term reversal | commodity/FX/credit | 3 / 18 | 18 / 18 | 0.195 |

Three different mechanisms — trend, risk sizing, and its own mechanical
opposite, contrarian reversal — across 54 disjoint markets this repository had
never acquired, spanning equities, commodities, currencies, and credit, in both
rising and falling regimes.

The result is consistent to the point of being structural: **timing overlays
reduce drawdown almost without exception (18/18, 17/18, 18/18) and pay for it in
risk-adjusted return.** No mechanism, asset class, or regime tested has produced
a cost-robust, regime-consistent Sharpe improvement. Given that the third test
was both the most independent and the one without a benchmark bull market, the
"unfavourable regime" defence is exhausted.

## Boundary

Historical evidence, not forward evidence. No validated-alpha claim, no
forward-shadow slot claimed, and no paper, broker, or live authority follows.
The closure applies to this exact rule under these exact gates. Reversal is not
re-run on another cohort, and neither the 21-session lookback nor the strict
sign test may be adjusted.

## Trust and safety

Eighteen market-data requests were GET-only, destination-allowlisted, and
recorded `token_value_recorded`, `market_data_token_value_printed`, and
`market_data_token_value_written` as `false`. The scored replay was offline,
deterministic, and credential-free. Network access by the engine, broker,
account, order, and position access, paper mutation, and live activity were all
false. Existing caps, receipts, reconciliation, sleeve ownership, and live
prohibitions are unchanged.
