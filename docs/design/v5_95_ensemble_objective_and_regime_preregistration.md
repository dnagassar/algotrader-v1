# V5.95 ensemble objective and regime preregistration

Status: frozen before any component is scored, registered, or admitted. This is
the binding contract for the V5.94 regime-conditional ensemble restructure,
adopted by the operator on 2026-08-03. The operator selected the drawdown-ceiling
objective and delegated the remaining parameter choices; every parameter below is
declared here, before any component outcome has been computed under it.

Nothing in this document reopens a closed milestone.

## 1. Ensemble objective

**Maximize risk-adjusted return subject to a hard maximum-drawdown ceiling.**

- Objective metric: annualized Sharpe ratio of the ensemble, at 5 bps decision
  cost.
- Hard constraint: ensemble maximum drawdown must not exceed
  `0.200000000000` over the scored window. An ensemble breaching the ceiling is
  **infeasible**, and no Sharpe value makes it admissible.
- The ceiling is declared from first principles, not fitted: 20% is a
  conventional institutional risk limit and sits materially below the drawdown
  a long-run equity holding has historically experienced. It was chosen before
  any ensemble was constructed and may not be raised afterward.

Stated plainly, and accepted as part of the decision: on the evidence this
program has gathered, optimizing under a drawdown ceiling will very likely
produce **lower total return than simply holding equity**. That is the deliberate
trade of this objective. It is not an income-maximizing objective and must never
be reported as one.

## 2. Regime set

Two causal axes, four exhaustive and disjoint regimes. The reference series is
`SPY` adjusted close. SPY is used as a *market-state classifier*, not as a
component or a benchmark for skill; that role is disclosed rather than hidden.

**Trend axis** — mechanism: persistence of directional drift.
- `up` if `adjusted_close(t-1) > SMA200(t-1)`, else `down`.
- `SMA200(t-1)` is the mean of the 200 sessions ending at `t-1` inclusive.

**Volatility axis** — mechanism: volatility clustering (Engle, ARCH).
- `realized_vol(t-1)` is the sample standard deviation (n-1) of the trailing 60
  daily simple returns ending at `t-1`, annualized by `sqrt(252)`.
- `stressed` if `realized_vol(t-1)` is strictly greater than the median of the
  trailing 1,260 daily values of `realized_vol` ending at `t-1`, else `calm`.
- The median is **trailing**, never full-sample. A full-sample median would leak
  future information into past labels and is forbidden.

**Regime labels:** `calm_up`, `calm_down`, `stressed_up`, `stressed_down`.

**Causality:** every input to the label for session `t` is observable at the
close of `t-1`. No centered windows, no hand-drawn crisis intervals, no
full-sample statistics.

**Warm-up:** the first `1,320` sessions (1,260 median window + 60 volatility
window) carry no label and are never scored.

**Immutability:** the regime count, axes, thresholds, windows, and reference
symbol are frozen by this document's hash. Adding, splitting, removing, or
re-parameterizing a regime after any component result is seen is forbidden and
will break the registration fingerprint. There is no revision path; a different
regime set is a different contract requiring its own preregistration and its own
untouched data.

## 3. Component gates

A component is registered against exactly one declared regime. All gates are
required. Thresholds are frozen here.

| Gate | Threshold |
| --- | --- |
| In-regime Sharpe edge over benchmark, 5 bps | `>= 0.100000000000` |
| Cost robustness: in-regime Sharpe edge, 15 bps | `> 0.000000000000` |
| Occurrence consistency: scoreable episodes won | `>= 0.600000000000` |
| Minimum scoreable episodes | `>= 8` |
| Minimum sessions for an episode to be scoreable | `>= 10` |
| Out-of-regime annualized return drag vs default | `>= -0.005000000000` |
| Non-redundancy: absolute in-regime excess correlation vs each admitted component | `<= 0.700000000000` |
| Marginal ensemble Sharpe improvement | `>= 0.020000000000` |
| Ensemble maximum drawdown after admission | `<= 0.200000000000` |

**Occurrence consistency is measured across contiguous episodes of the regime,
not across calendar periods.** This is the specific repair the restructure
exists to make: a bear-regime component is judged on bear-market episodes, and
is never penalized for being flat during regimes it does not claim.

An episode is a maximal contiguous run of sessions carrying the component's
declared regime label. Episodes shorter than the minimum are excluded from the
consistency count entirely rather than counted as losses, and a component with
fewer than the minimum scoreable episodes **fails for insufficient evidence** —
it does not pass on a thin sample.

## 4. Multiplicity

Testing `C` components across `R` regimes is `C x R` hypotheses. The planned
component count and regime count are frozen before any member registers, and the
Bonferroni divisor is their product, via the existing V5.90 cohort machinery.
Members beyond the frozen plan are refused. The regime count is fixed at 4 by
section 2.

## 5. Contamination tiers

Carried over from V5.94 section 7, binding:

- **Tier A** — components never previously scored in this repository, on
  vault-eligible data. Historical evaluation is admissible evidence.
- **Tier B** — every previously closed candidate, and every component suggested
  by a result already observed here, explicitly including the V5.89
  `no_canary_g4_always_offensive` ablation and the V5.91-V5.93 drawdown
  findings. Historical evaluation is **not** admissible. Tier B enters only
  through a V5.90 forward shadow scored on data that did not exist at
  registration.

The drawdown evidence that motivated this objective is itself Tier B. That is
not a contradiction: it is legitimate grounds for *choosing an objective*, and
it is not evidence that any particular component will satisfy that objective.
The distinction is load-bearing and must not be blurred.

## 6. Preserved and forbidden

Preserved unchanged: preregistration before data, hash-bound freezing of
protocol/receipt/data/engine, outcome-blind admission, no post-hoc tuning,
cost-robustness gates, byte-identical replay, vault eligibility, the full
offline verifier as a merge gate, and all credential, broker, paper, and live
safety boundaries.

Forbidden: historical promotion of Tier B; adjusting any regime, gate, ceiling,
or objective after seeing results; combining components outside this contract;
reporting a closed standalone milestone as passed; and any autonomous path to
live capital. Live remains an operator hard gate that this document does not
move.

## 7. Honest limitations

- This changes the question, not the answer. If no component has an edge in any
  regime, an ensemble of them has none either.
- Conditioning shrinks samples. A `stressed_down` component may have few
  qualifying episodes in twenty years; the minimum-episode gate exists so that
  thin evidence fails rather than flatters.
- Regimes are the largest researcher degree of freedom in this design. Section
  2's immutability rule is the only thing preventing "wrong regime" from
  becoming an unfalsifiable excuse for every failure.
- A drawdown-constrained ensemble is expected to trail equity in return. That is
  the chosen trade, not a defect.
