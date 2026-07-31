# V5.68 NexusTrade-Inspired Risk-Balanced Attribution

Status: outcome-blind diagnostic preregistration. This file must be committed
before any V5.68 attribution output is produced.

Protocol ID: `v5_68_nexustrade_risk_balanced_attribution_v1`.

## Purpose and boundary

V5.68 is an attribution-only diagnostic of the frozen V5.67 result. It creates
no strategy candidate, route, preview, shadow, paper promotion, or live
authority. It performs no parameter search and cannot be used to tune V5.67.

The known parent-relative V5.67 return loss motivates this diagnostic, but the
component effects defined below are not inspected before this protocol is
committed. V5.67 remains frozen as an independently designed,
NexusTrade-inspired candidate, not an authentic NexusTrade replay or lineage
claim.

## Frozen dependencies

The implementation must fail closed unless every hash matches:

- V5.64 protocol:
  `docs/design/v5_64_nexustrade_monthly_independent_replication.md`, SHA-256
  `f24c98daa03462fccd0e73163abfe42f597ab601db83b331ecd4b487e31f4ee0`.
- V5.64 engine:
  `src/algotrader/research/nexustrade_monthly_independent_replication.py`,
  SHA-256
  `66d73e4e0cd6160c8f07febe3a80b90eb4eebdd1ea7375b7fb3b23cadeef87f5`.
- V5.67 protocol:
  `docs/design/v5_67_nexustrade_monthly_risk_balanced_allocation.md`, SHA-256
  `17f86b8eafd7e67e6816603cb1bf06fa96a734c7b7d9094d30e68ec85690505e`.
- V5.67 engine:
  `src/algotrader/research/nexustrade_monthly_risk_balanced_allocation.py`,
  SHA-256
  `2c669051c6c3fc877cd86d482579ffa711e7d68724e5dffb117d32080aef1188`.
- V5.67 preregistration artifact SHA-256:
  `6ee1e62efb4b20f94896b2e29fb022081b6c762f4c7da8de7f67f631bc747d6e`.
- V5.67 result artifact SHA-256:
  `76de6eabe410c082b53ff123af31dccdf4704f78c3380bd6d6e8e8de24b2276f`.
- V5.67 summary artifact SHA-256:
  `99fac23b5cbeae076bb0249d6741e98ca95a433b11cad994ed92abd2bcf886f1`.
- V5.67 manifest artifact SHA-256:
  `0bcf77f91d4b92a9d85f566e0e0c946fc19be4b56bd28982eeb741d23dee1519`.
- Canonical adjusted-daily CSV SHA-256:
  `d296138a95a86546bdc92678af479e8c8e204b138e2db43f54979a19921c9575`.
- V5.63 provenance manifest SHA-256:
  `e204a8a1824e5b49ce4d457f12884bfc284d52f99ad3ba07072c978d7223d8e1`.

Before attribution, the engine must reproduce the complete frozen V5.67
preregistration and result with exact structured equality and its summary with
exact text equality. It must reproduce all V5.67 candidate and frozen-parent
window metrics and target hashes across all four costs.

## Shared data, chronology, and costs

All paths use the frozen V5.67 canonical contract:

- Tiingo EOD `adjClose` normalized to split-and-dividend-adjusted
  `adjusted_close`;
- symbols
  `AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, GS, JPM, BRK-B, COST, SPY`;
- deterministic `BRK-B->BRK-B` mapping;
- observed Tiingo SPY EOD dates as the session reference;
- coverage `2019-01-02` through `2025-03-28`, exactly 1,569 common sessions;
- training `2021-12-31` through `2024-03-24`;
- untouched OOS boundary `2024-03-24` through `2025-03-28`, first observed
  OOS session `2024-03-25`, exactly 254 sessions; and
- continuous-state folds `2024-03-25`–`2024-07-24`,
  `2024-07-25`–`2024-11-21`, and `2024-11-22`–`2025-03-28`.

Folds are reporting slices only. State, weights, and equity are never reset at
training, OOS, or fold boundaries.

All paths use the same four one-way turnover cost cases:

- `zero_cost`: fee 0 bps, slippage 0 bps;
- `source_fee_only`: fee 1 bp, local slippage assumption 0 bps;
- `low_friction`: fee 1 bp, local slippage assumption 1 bp; and
- `moderate_friction`: fee 1 bp, local slippage assumption 4 bps.

Signals use the current adjusted close and fills occur at the next observed
adjusted close. Same-close fills are forbidden. Weights drift between fills
and cash return is zero. The shared SPY risk gate is adjusted-close
`SMA50>SMA200`; risk-off targets cash and transitions fill next session.

## Fixed path definitions

The path order is `P -> R -> C -> A`. `R` and `C` are diagnostic
counterfactuals, not candidates.

### P: frozen parent

`P` is the frozen V5.64 composite
`nexustrade_monthly_independent_spy_sma_50_200_regime_filter`.

It uses equal weights across the eligible stocks, full stock exposure whenever
at least one stock is eligible and SPY is risk-on, and its own filled-buy and
filled-sell state for the 30-calendar-day OR rule.

### R: pure risk-balanced sizing under parent state

`R` is
`diagnostic_inverse_volatility_sizing_parent_state`.

`R` uses the frozen `P` source-rebalance schedule and filled-event state. Its
own fills never affect that schedule. At each parent-controlled source
rebalance:

- when zero stocks are eligible, target cash;
- when one through five stocks are eligible, use the exact `P` equal-weight,
  full-exposure target; and
- when six or more stocks are eligible, use the exact V5.67 60-return inverse
  sample-volatility scores and deterministic `0.20`-capped water-fill target.

Thus `R-P` isolates inverse-volatility/capped sizing only where the cap allows
full stock exposure. It contains no fewer-than-five partial-cash effect.

### C: V5.67 allocation under parent state

`C` is `diagnostic_subfive_partial_cash_parent_state`.

`C` uses the same frozen `P` source-rebalance schedule and ignores its own
fills for scheduling. At every parent-controlled source rebalance it uses the
exact V5.67 allocation rule:

- 60 simple adjusted-close returns;
- sample standard deviation with denominator 59;
- reciprocal-volatility scores;
- `0.20` per-name cap; and
- stock exposure `min(1, 0.20 * eligible_count)`.

For one through four eligible stocks, V5.67 assigns exactly `0.20` to each and
holds the remainder as cash. `R` holds the same stocks in the same equal
proportions but at full exposure. For five eligible stocks both paths hold
`0.20` each. For six or more eligible stocks both paths use the same
inverse-volatility capped target. Therefore `C-R` isolates only the
fewer-than-five partial-cash exposure rule.

### A: frozen V5.67 actual

`A` is the frozen V5.67 candidate
`nexustrade_monthly_independent_spy_sma_50_200_inverse_volatility_capped`.

It uses the exact same allocation targets as `C`, but its own actual filled
buy and sell events—including fills caused by SPY regime transitions—control
its 30-calendar-day OR state. Therefore `A-C` isolates candidate-owned
filled-event state carry, including resulting source-rebalance timing and
stored-target differences.

## Parent-state simulation contract

`R` and `C` must each maintain an internal shadow `P` portfolio. The shadow
must reproduce the frozen parent target, posttrade weights, fills, turnover,
and returns. Only the shadow's filled buy/sell dates determine whether the
next source-rule target is ready. Diagnostic-path fills do not update that
state.

All paths independently apply the same next-session SPY transition timing.
The source eligibility clauses, adjusted-close indicators, canonical symbol
order, and Decimal tolerance remain frozen. No state or fill timestamp may be
inferred from a reporting window boundary.

## Exact attribution identities

For every cost case and each reporting window—training, full OOS, and all
three folds—the engine must record signed effects:

- pure sizing: `R - P`;
- fewer-than-five partial cash: `C - R`;
- candidate-owned state carry: `A - C`; and
- total: `A - P`.

The exact return identity is:

`(R - P) + (C - R) + (A - C) = A - P`.

The same telescoping identity is required separately for each stock's
arithmetic gross contribution. Return and contribution residuals must have
absolute value at most `1e-24`. Failure blocks result output.

Turnover and trade-count deltas use the same signed path order but are reported
descriptively; drawdown is non-additive and is reported as four complete path
values. No compounded constituent-return decomposition is claimed.

## Fixed diagnostics

For every cost/window, record:

- all four path metrics and target-vector hashes;
- signed return effects and exact residual;
- per-symbol arithmetic gross contribution effects and residuals;
- path turnover and trade counts plus signed deltas;
- maximum drawdown for every path;
- desired-target and posttrade divergence counts for `R-P`, `C-R`, and `A-C`;
  and
- first/last divergence dates where applicable.

The signal ledger must record each parent-controlled source-rebalance signal,
its eligible count, whether pure sizing changes the target, whether the
partial-cash rule changes the target, the signal date, and scheduled next
observed fill date. Aggregate OOS diagnostics must distinguish signal events
from the number of sessions over which a stored target remains different.

## Fixed moderate-cost classification

Classification uses only `moderate_friction` full OOS after all identities and
frozen reproductions pass.

Let net harm be `P-A`. Harm is material when net harm is at least `0.005`.
For each component, harm magnitude is `max(0, -signed_effect)` from the V5.67
actual perspective. Positive component effects are offsets and do not count as
harm.

When harm is not material, classify `no_material_harm`. Otherwise, a component
is primary only when it has the unique largest harm magnitude, ties resolved
within `1e-24`, and its harm magnitude is at least 50% of net harm. The fixed
primary labels are:

- `pure_sizing_primary`;
- `subfive_partial_cash_primary`; and
- `state_carry_primary`.

If no component uniquely satisfies the rule, classify `mixed_harm`. A primary
share may exceed one when another component offsets harm; that is reported,
not clipped.

Classification is explanatory only. It creates no route and cannot justify a
parameter adjustment, same-thesis candidate, preview, or shadow.

## Artifacts and safety

The ignored output root is
`runs/v5_68_nexustrade_risk_balanced_attribution` and contains exactly:

- `preregistration.json`;
- `attribution_results.json`;
- `attribution_summary.md`; and
- `manifest.json`.

Artifacts must be deterministic, local, hashed, and free of credentials,
account identifiers, broker payloads, and source-metric controls. External
performance remains `untrusted_external_evidence`; the `29.64%` table versus
`29.41%` chart discrepancy is preserved and cannot affect attribution or
classification.

V5.68 performs no NexusTrade access or mutation, market-data network access,
broker/account/order/position access, paper mutation, third-sleeve creation,
or live activity. V5.57 sleeve ownership, reconciliation, auditing, live
prohibitions, and caps remain unchanged: `$25` maximum entry-order notional,
`$60` maximum aggregate marked SPY entry exposure, one broker order per secure
cycle, and two sleeve intents per UTC day.
