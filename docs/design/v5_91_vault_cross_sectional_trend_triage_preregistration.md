# V5.91 vault cross-sectional trend triage preregistration

Status: frozen before any V5.91 data request, per-market target, return, metric,
gate, count, or route was computed. This is the first use of the V5.90 vault:
buying statistical breadth from markets this repository has never touched,
instead of buying it from calendar time.

## What this is, and what it is not

Sixteen published families closed at `no_candidate_passed`, all judged on one
US-dominated time series. The V5.89 diagnosis identified the structural cause
and offered two honest routes. This is the instant one.

Eighteen single-country equity ETFs are tested. Every one was confirmed
vault-eligible by `forward_shadow_vault` before this document was written: no
acquisition receipt, canonical artifact, or data manifest in this repository
references any of them. EWJ was excluded precisely because the scan flagged it
as already acquired during V5.88.

This is a **triage**, not a validation. Three limits are stated up front and are
not negotiable after the reveal:

1. It is a **historical** test. It is uncontaminated by *our* selection, not by
   the calendar. A pass therefore routes to forward-shadow registration and to
   nothing else. It cannot produce validated alpha.
2. Absolute trend following is a **published** effect. Its authors saw global
   market history, so author-side selection survives even though ours does not.
   A pass means "a published effect replicates on markets we never inspected,"
   which is informative and is not proof of future edge.
3. Single-country equity markets are **correlated**. Eighteen markets are not
   eighteen independent experiments. The binomial gate below assumes
   independence and therefore overstates significance. The realized correlation
   of the per-market excess series must be reported alongside the result, and a
   low correlation does not upgrade a fail while a high one does not annul a
   pass. It is disclosure, not an adjustment knob.

## Exact universe

Canonical order, eighteen symbols:

`EWA,EWC,EWD,EWG,EWH,EWI,EWK,EWL,EWM,EWN,EWO,EWP,EWQ,EWS,EWU,EWW,EWY,EWZ`

- Provider: authenticated Tiingo End-of-Day through the repository's GET-only,
  destination-allowlisted adapter; free tier; no new paid service.
- Field: `adjClose` normalized to `adjusted_close`; provider split- and
  dividend-adjusted close only; identity mappings only.
- Requested coverage: 1996-04-01 through 2026-07-31, one request per symbol.
- Admitted panel: the exact common-session intersection across all eighteen
  symbols. Launch dates differ, so the intersection — not the request — defines
  the window, and the receipt pins whatever it turns out to be.
- The intersection must contain at least 5,000 common sessions. Fewer blocks
  the milestone rather than shrinking the test.
- Missing, duplicate, nonpositive, nonfinite, stale, substituted, or
  session-mismatched rows block. Manual bars, hand normalization, synthetic
  history, back-extension, broker data, and alternate providers are forbidden.

## Exact rule

One rule, no variants, applied identically to every market.

- Signal: on the final common session `t` of each calendar month, market `m` is
  *on* if `adjusted_close(m, t) > SMA200(m, t)`, where `SMA200` is the mean of
  the trailing 200 common-session adjusted closes ending at `t` inclusive.
- Target: 100% of market `m` when on, otherwise 0% with the remainder held as
  implicit zero-return cash. No leverage, no shorting, no partial sizing, no
  cross-market ranking, no second lookback, no filter, no override.
- Execution: the target formed at `t` takes effect at the next common session
  `t+1` close, after the `t`-to-`t+1` return is earned by prior holdings. The
  new target first earns `t+1`-to-`t+2`. Close-only causal proxy, not a
  fill replication.
- Warm-up: the first 200 common sessions form no signal and are not scored.
- Benchmark: 100% buy-and-hold of the *same* market, entered at the first
  scored session and never rebalanced. Both the rule and the benchmark start
  flat and pay an identical entry transition, so neither is advantaged.
- Costs: 0, 5, and 15 basis points per unit of one-way turnover; 5 bps is the
  decision cost and 15 bps is stress. Repository assumptions, not source claims.

## Frozen gates

The primary test is cross-sectional breadth, not any single market's result.

**Primary.** At 5 bps, the rule must beat its own market's buy-and-hold on
Sharpe ratio in at least **13 of 18** markets. Under independence this is an
exact one-sided binomial test with `p = 0.04813` against `p = 0.5`. Twelve wins
gives `p = 0.11894` and fails.

**Secondary, all required:**

- At 15 bps, at least 13 of 18 Sharpe wins.
- At 5 bps, the rule improves maximum drawdown in at least 13 of 18 markets.
- At 5 bps, the median per-market Sharpe improvement is strictly positive.
- Consistency: over the post-2007 sub-window, at least 12 of 18 Sharpe wins at
  5 bps. This is deliberately weaker than the primary gate and exists to detect
  an effect that lives entirely in the early history; it is a consistency
  check, not a second primary test.
- Integrity: two complete replays produce byte-identical result and manifest
  bytes; causal lag, warm-up exclusion, weight grammar, drift, cash, turnover,
  and hash identities all verify.

**Reported but not gated:** mean pairwise correlation of the per-market excess
return series, per-market Sharpe and drawdown deltas, decision counts, and the
count of months each market spent on.

## Routes

A complete pass routes to
`cross_sectional_evidence_supports_forward_shadow_registration` — an argument
that this rule deserves one of the V5.90 forward-shadow slots, and nothing
further. It authorizes no paper, no broker, no live, and no validated-alpha
label.

Any failure routes to `close_triage_without_tuning`. No threshold, lookback,
universe member, cost, or window may be adjusted afterward. A failed triage is
not re-run with a different moving average.

## Safety

V5.91 is offline research plus eighteen exact authorized GET-only market-data
requests. Broker, account, order, and position access, paper mutation, and live
activity are forbidden. No credential value is requested, printed, returned, or
persisted outside the trusted adapter boundary. Existing paper sleeves,
reconciliation, receipts, caps, and live prohibitions are unchanged.
