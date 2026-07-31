# V5.66 NexusTrade High-Volatility Defense Attribution Preregistration

## Status and authority boundary

This diagnostic is preregistered before computing or inspecting any V5.66
counterfactual path, attribution component, transition ledger, drawdown path,
or diagnostic classification.

V5.64 and V5.65 are frozen. V5.66 does not alter, tune, rank, relabel, or
promote either protocol. It creates no strategy candidate, challenger route,
preview review, shadow design, execution intent, paper path, or live path.

The purpose is limited to explaining why the fixed V5.65 high-volatility
defense lost return and worsened drawdown versus its frozen V5.64 parent. The
diagnostic decomposes the effect of:

1. the high-volatility classification and cash exposure itself;
2. the preregistered next-session-close execution delay; and
3. the interaction between overlay fills and the stateful 30-calendar-day
   filled-buy/filled-sell rebalance rule.

This remains an independent local diagnostic, not an authentic replay of the
March 2025 NexusTrade historical run. Source metrics are untrusted and unused.
The `29.64%` table versus `29.41%` chart discrepancy remains unresolved.

The diagnostic is offline, research-only, credential-free, network-free,
broker-free, and no-submit.

## Fixed identity

- Protocol ID:
  `v5_66_nexustrade_high_volatility_attribution_v1`.
- Diagnostic ID:
  `nexustrade_high_volatility_defense_attribution_only`.
- Frozen parent path ID:
  `nexustrade_monthly_independent_spy_sma_50_200_regime_filter`.
- Frozen actual path ID:
  `nexustrade_monthly_independent_spy_sma_50_200_high_volatility_defense`.
- Delayed stateless diagnostic path ID:
  `diagnostic_high_volatility_defense_delayed_parent_state`.
- Immediate stateless diagnostic path ID:
  `diagnostic_high_volatility_defense_immediate_parent_state`.
- Output root:
  `runs/v5_66_nexustrade_high_volatility_attribution`.

The two diagnostic counterfactual paths are not candidates and must never be
registered, ranked, routed, shadowed, or promoted.

## Pinned dependency contract

- Canonical adjusted-daily CSV:
  `runs/operator_input/multi_etf_adjusted_daily_canonical.csv`.
- Required CSV SHA-256:
  `d296138a95a86546bdc92678af479e8c8e204b138e2db43f54979a19921c9575`.
- V5.63 canonical-data manifest:
  `runs/v5_63_nexustrade_canonical_data/canonical_data_manifest.json`.
- Required V5.63 manifest SHA-256:
  `e204a8a1824e5b49ce4d457f12884bfc284d52f99ad3ba07072c978d7223d8e1`.
- Frozen V5.64 protocol SHA-256:
  `f24c98daa03462fccd0e73163abfe42f597ab601db83b331ecd4b487e31f4ee0`.
- Frozen V5.64 engine SHA-256:
  `66d73e4e0cd6160c8f07febe3a80b90eb4eebdd1ea7375b7fb3b23cadeef87f5`.
- Frozen V5.65 protocol SHA-256:
  `1b614cb9d9e310704a0f8adcda224a4c540054a70af2731bcd3ec9c9b44db0c5`.
- Frozen V5.65 engine SHA-256:
  `fbc37e7c5cda052951c9406c7666cf346fa6d814edbf41d9842c80f4c2516a3c`.
- Frozen V5.65 preregistration-artifact SHA-256:
  `8ab8fb25edf1ccb9803465fbc568b4b5348776c472b58c447a189ee677723190`.
- Frozen V5.65 result SHA-256:
  `e30c9c6f9d90f0d87c33607c71d1ec3e7c0055a245b88d06a469bfbc33709611`.
- Frozen V5.65 summary SHA-256:
  `1ff76c5c3fcb840794fbcd2e501f7300976f34557dd9aad3dcea35ebdd3f936e`.
- Frozen V5.65 manifest SHA-256:
  `99c52a97d2f8d6ef88df844356dbd38e88859d2804c4db9cf166ae55cad48814`.

Every hash must validate before canonical data is loaded or a diagnostic path
is computed. The recomputed frozen parent and actual V5.65 path metrics must
also match the pinned V5.65 result artifact for every cost/window field used by
the diagnostic.

## Frozen data, chronology, rule, and cost semantics

The diagnostic reuses without change:

- Tiingo EOD `adjClose` as canonical `adjusted_close`;
- the twelve-symbol V5.63 data contract and `BRK-B->BRK-B` mapping;
- coverage `2019-01-02` through `2025-03-28`;
- training `2021-12-31` through `2024-03-24`;
- OOS `2024-03-24` through `2025-03-28`;
- OOS folds:
  - `2024-03-25` through `2024-07-24`;
  - `2024-07-25` through `2024-11-21`;
  - `2024-11-22` through `2025-03-28`;
- the frozen V5.64 stock eligibility, 30-calendar-day filled-event state,
  drift, SPY SMA50/200 gate, and next-session adjusted-close fill model;
- the frozen V5.65 20-session SPY realized-volatility regime, expanding
  prior-only nearest-rank 33/67 thresholds, and 252-observation minimum;
- continuous state with no reset at evaluation boundaries; and
- zero, source-fee-only, low-friction, and moderate-friction costs.

The primary attribution case is `moderate_friction`. The source-fee-only case
is also reported to distinguish turnover/cost effects.

## Fixed path definitions

### Frozen parent path P

Recompute the frozen V5.64 SPY SMA50/200 composite exactly. Its stock
filled-event state is updated only by its own actual fills.

### Frozen actual V5.65 path A

Recompute the frozen V5.65 stateful, next-session-close high-volatility defense
exactly. Overlay-induced fills update its own filled-event state.

### Delayed stateless diagnostic path D

Maintain a separate frozen-parent state machine. The diagnostic portfolio:

- uses the parent state machine's eligible stock set and rebalance events;
- applies the fixed high-volatility cash gate;
- schedules target changes for the next observed close; and
- does not allow diagnostic overlay fills to modify the parent state machine.

This isolates the high-volatility classification plus next-session execution
while removing overlay-induced stateful carry.

### Immediate stateless diagnostic path I

Use the same frozen-parent state machine and high-volatility gate as D, but
apply a changed diagnostic target at the current signal close for the next
close-to-close return interval. The current signal uses only information
available through that close.

This deliberately differs from the frozen source/V5.65 fill assumption and is
an attribution-only timing counterfactual. It is not a valid replay, candidate,
or proposed execution model. The same turnover cost is charged at that close.

## Exact additive return decomposition

For each reporting window and cost case, use total-return differences:

- classification effect: `I - P`;
- next-session execution-delay effect: `D - I`;
- stateful-carry effect: `A - D`;
- total V5.65 effect: `A - P`.

Require exact reconciliation within decimal tolerance:

`(I - P) + (D - I) + (A - D) = A - P`.

Effects are signed from V5.65's perspective. Negative values are harm;
positive values are benefit. Harm magnitudes are the negated effects.

Drawdown is path-dependent and is not additively decomposed. Report each
path's maximum drawdown, peak date, trough date, recovery date when present,
and deltas versus P for full OOS and every fold.

## Session, constituent, transition, and cost attribution

For full OOS and every fold, report:

- high-volatility session count;
- parent-risk-on high-volatility session count;
- A-versus-P target-divergence count;
- A-versus-D target-divergence count, labeled stateful-carry divergence;
- D-versus-I posttrade-weight-divergence count, labeled execution-delay
  divergence;
- first and last date for each nonempty divergence class;
- per-path invested-session percentage, trade count, and one-way turnover;
- source-fee-only and moderate-cost return degradation; and
- turnover and trade-count deltas for A, D, and I versus P.

For each stock and each window, sum gross daily contribution differences:

- classification contribution: `I contribution - P contribution`;
- execution-delay contribution: `D contribution - I contribution`;
- stateful-carry contribution: `A contribution - D contribution`;
- total contribution: `A contribution - P contribution`.

Require per-symbol and aggregate arithmetic reconciliation within decimal
tolerance. Classify negative contributions as missed return and positive
contributions as avoided loss/benefit. These arithmetic contribution sums do
not replace compounded portfolio-return attribution.

Create a deterministic volatility-transition ledger containing signal date,
next observed fill date, transition into/out of `high_vol`, parent desired
exposure, and P/A/D/I posttrade exposure and turnover on the fill date. Do not
invent fills beyond the four defined paths.

## Fixed diagnostic classification

Use moderate-cost full-OOS total returns. Define net harm as `P - A`.

- `no_material_harm`: net harm is at most `0.005`.
- Otherwise compute positive harm components:
  - classification harm: `max(0, P - I)`;
  - execution-delay harm: `max(0, I - D)`;
  - stateful-carry harm: `max(0, D - A)`.
- `classification_primary`: classification harm is the largest positive
  component, is at least `0.005`, and is at least 50% of net harm.
- `execution_delay_primary`: execution-delay harm meets the same conditions.
- `stateful_carry_primary`: stateful-carry harm meets the same conditions.
- `mixed_harm`: net harm exceeds `0.005` but no component qualifies as primary.
- `blocked`: any pinned hash, coverage, reproduction, reconciliation, or
  deterministic-output check fails.

If positive harm components exceed net harm because another component is a
benefit, report shares against net harm without clipping and retain the fixed
largest-component rule.

The classification is explanatory only. It creates no route and cannot
authorize a candidate or follow-up strategy change.

## Output and safety contract

Write deterministic ignored artifacts:

- `preregistration.json` before loading canonical prices;
- `attribution_results.json`;
- `attribution_summary.md`;
- `manifest.json`.

The manifest hashes the other three outputs and every pinned local dependency.
Its own hash is reported only after writing.

Every artifact must state:

- diagnostic only and no candidate created;
- V5.64 and V5.65 frozen;
- parameter search false;
- source metrics untrusted and unused;
- network, credential, broker, paper mutation, and live activity false;
- paper promotion, submission, preview review, and shadow creation false;
- V5.57 sleeve ownership, reconciliation, auditing, and finite caps unchanged.
