# V5.94 regime-conditional ensemble restructure

Status: **ADOPTED by the operator on 2026-08-03.** The objective restatement in
section 1 and the ensemble objective in section 6 are accepted; the operator
selected the drawdown-ceiling objective and delegated the remaining parameter
choices. The binding, hash-frozen contract derived from this document is
`docs/design/v5_95_ensemble_objective_and_regime_preregistration.md`; this
document remains the design rationale and is not itself the contract.

No prior closure is reopened by this adoption. Every closed milestone stays
closed under the question it was asked.

## 1. What this changes

The research program is being asked a new question. Until now every milestone
asked:

> Does this single rule, applied unconditionally across all regimes, beat SPY
> on a standalone basis?

The operator's actual objective, stated on 2026-08-03, is:

> Does a compilation of several alpha components, each tailored to the market
> conditions where it is expected to work, deployed autonomously, capitalize on
> those conditions?

These are different questions with different correct answers. This document
restates the objective on the record. It is **not** a relaxation of gates after
nineteen failures, and it must never be described as one: the failed milestones
stay failed under the question they were asked, and their terminal decisions
remain valid as written.

## 2. The mismatch this corrects

Three structural features of the current harness are actively hostile to an
ensemble of specialists.

**The consistency gate eliminates specialists by construction.** V5.91's
post-2007 gate rejected a rule because its effect "lived entirely in
2001-2007." Under the standalone question that was correct. Under the ensemble
question it is backwards: a component that works in bear regimes and is flat
otherwise is precisely what an ensemble wants, and a gate demanding uniform
performance across calendar time will reject every specialist ever proposed.

**The closure rule prevents accumulation.** "No re-running, no combining, no
tuning" is sound protection against self-deception, and it also guarantees that
N milestones yield N orphaned tombstones and zero systems. There is currently
no mechanism by which findings become a portfolio.

**The benchmark is wrong for a component.** A defensive sleeve judged against
SPY is a seatbelt judged on whether it makes the car faster. A component should
be judged on what it contributes, in the conditions it claims, to the portfolio
it joins.

The cost of the mismatch is measurable. Across V5.91, V5.92, and V5.93 —
three mechanisms, 54 never-acquired markets — drawdown improved in 18/18,
17/18, and 18/18 markets respectively. That is the most robust, most replicated,
most nearly-independent finding this program has produced, and the harness
recorded it as failure three times because the gate was asking a different
question. Under an objective that values drawdown control, that evidence is an
asset rather than a tombstone.

## 3. The new unit of evaluation

The unit changes from *strategy* to *component-in-regime*.

A **component** is a frozen, causal rule producing target weights. A **regime**
is a frozen, causal classifier partitioning sessions into named states. A
component is registered against exactly one declared regime and is evaluated on
three questions, in order:

1. **In-regime skill.** During sessions its regime is active, does it beat its
   declared benchmark after decision costs?
2. **Out-of-regime harmlessness.** During sessions its regime is inactive, is it
   materially neutral? A component that bleeds when idle is not a specialist,
   it is a liability with good marketing.
3. **Marginal ensemble contribution.** Does adding it to the current ensemble
   improve the ensemble's declared objective? A component that duplicates an
   existing member adds risk and no information.

All three are required. Passing (1) alone is the failure mode that produces
impressive components and mediocre portfolios.

## 4. The regime contract

Regimes are where this design can most easily deceive itself, so they carry the
strictest rules.

- **Causal.** A regime label for session `t` must be computable from data
  available at `t-1`. No centered windows, no hindsight labels, no
  "the 2008 crisis" as a hand-drawn interval.
- **Preregistered and frozen.** The full regime set, its parameters, and its
  hash are frozen before any component is scored against it. Adding, splitting,
  or re-parameterizing a regime after seeing component results is forbidden and
  breaks the registration fingerprint.
- **Small and fixed.** At most four regimes at any time. Every additional
  regime multiplies the search space; four is already 4x the multiple-testing
  burden and is priced accordingly under section 6.
- **Exhaustive and disjoint.** Every session carries exactly one label, so
  in-regime and out-of-regime partition cleanly and no session is unscored.
- **Declared from first principles, not from fit.** Regime definitions must be
  justifiable from published rationale or mechanism before any outcome is seen.
  A regime chosen because it happened to be where a candidate worked is
  curve-fitting with extra steps.

A reasonable frozen starting set — volatility state, trend state, rate/credit
state — is deliberately *not* specified here, because choosing it is part of
the operator's adoption decision and must be frozen in its own preregistration.

## 5. Component gates

Replacing the SPY value route. All required.

- **In-regime edge.** Beats its declared benchmark on the ensemble objective's
  metric during active-regime sessions, at 5 bps.
- **Cost robustness.** The in-regime edge survives at 15 bps. Retained without
  change: this gate has caught real fragility in every triage that used it and
  is not negotiable.
- **Regime-occurrence consistency.** This is the key repair. Consistency is
  measured **across occurrences of the regime, not across calendar periods**. A
  component must win in a preregistered majority of the *separate episodes* in
  which its regime was active. A bear-market specialist is therefore judged on
  bear markets, not on whether it also performed during the bull years — which
  is exactly the test V5.91's gate got wrong.
- **Out-of-regime neutrality.** Return during inactive-regime sessions must not
  fall below a preregistered floor relative to the ensemble default.
- **Non-redundancy.** Correlation of in-regime excess returns against every
  already-admitted component must sit below a frozen ceiling.
- **Marginal contribution.** Adding the component improves the ensemble
  objective by at least a preregistered margin, computed on the actual
  portfolio, not on metadata.
- **Integrity.** Byte-identical replay, causal lag, hash-bound inputs — all
  carried over unchanged.

## 6. Ensemble gates and multiplicity

The ensemble carries its own objective, declared once and frozen. The operator
must choose it; the recommendation, given the replicated drawdown evidence, is
**maximize risk-adjusted return subject to a hard drawdown ceiling**, because
that objective values what the program has actually demonstrated rather than
what it has repeatedly failed to find.

Multiplicity is priced, not ignored. Testing `C` components across `R` regimes
is `C x R` tests. The V5.90 cohort machinery already handles this: the planned
component count and regime count are frozen before any member registers, and
the Bonferroni divisor comes from that frozen product. Members beyond the plan
are refused.

## 7. Contamination tiers

We have already seen the unconditional results of roughly nineteen families.
That knowledge cannot be unseen, and pretending otherwise would forfeit the
only real asset this program has: its honesty about what it knows.

- **Tier A — clean.** Components never previously scored here, on vault-eligible
  data. Historical evaluation is valid evidence. This is the only tier that can
  produce a historical pass.
- **Tier B — contaminated.** Any previously closed candidate, and any component
  suggested by a result we have already seen — including the V5.89
  `no_canary_g4_always_offensive` ablation and every V5.91-V5.93 drawdown
  finding. Historical evaluation of these is **not** admissible evidence,
  because we chose them knowing their outcomes. They may enter the ensemble
  only through a V5.90 forward shadow, scored on data that did not exist at
  registration.

This is where the six-month cost the operator dislikes reappears, and it cannot
be engineered away. It is the price of a clean answer about strategies we have
already looked at. The sequential futility boundaries make bad Tier B
candidates fail fast, and parallel cohorts make the wait concurrent rather than
serial — that is the most the machinery can honestly do.

## 8. What is preserved

Everything that protects against self-deception, unchanged: preregistration
before data, hash-bound freezing of protocol/receipt/data/engine, outcome-blind
admission, no post-hoc tuning, cost-robustness gates, byte-identical replay,
vault eligibility scanning, the full offline verifier as a merge gate, and the
credential/broker/live safety boundaries.

None of the failures this session were caused by those properties. They were
caused by the rules genuinely underperforming — 3/18 and 2/18 are not near
misses. Loosening any of the above would not surface buried alpha; it would
surface false positives, which is strictly worse than nothing once capital is
attached.

## 9. What remains forbidden

- Reopening a closed standalone milestone as though it had passed. Closures
  stand under the question they were asked.
- Historical promotion of any Tier B component.
- Adjusting a regime definition, gate, or objective after seeing results.
- Combining components outside a preregistered ensemble contract.
- Any autonomous path to live capital. Autonomy over *paper* observation is
  already built; live remains an operator hard gate and this document does not
  move it.

## 10. Honest limitations

**This changes the question, not the answer.** If no component has an edge in
any regime, an ensemble of them has no edge either. Restructuring cannot
manufacture alpha, and adopting it is not evidence that alpha exists.

**Regimes add a large researcher degree of freedom.** The single biggest risk
in this design is that regime definitions become an unfalsifiable excuse: every
failure gets re-labelled as "wrong regime." The freeze-and-hash rules in
section 4 exist specifically to make that impossible, and they must not be
softened.

**Specialists are harder to validate, not easier.** Conditioning on a regime
reduces the sample within it. A bear-regime component may have only a handful
of episodes in twenty years, which is thin evidence regardless of how rigorous
the surrounding process looks.

**The ensemble objective is a real choice with real consequences.** Optimizing
for drawdown control will, on the evidence gathered here, produce lower returns
than holding equity outright. That is a legitimate goal and it is not the same
goal as maximizing income.

## 11. Proposed sequence

1. Operator adopts or rejects this restructure. If adopted, the objective
   statement in section 3 and the ensemble objective in section 6 are frozen
   into their own preregistration.
2. Freeze the regime set (section 4) in a separate preregistration, before any
   component is scored.
3. Build the ensemble evaluation harness: component-in-regime scoring,
   occurrence-based consistency, marginal contribution, and cohort multiplicity.
   This is new code, not a modification of the triage engines.
4. Register the first Tier A component cohort from remaining vault-eligible
   data.
5. In parallel, register Tier B candidates as forward shadows with futility
   boundaries, so contaminated-but-promising ideas accrue clean evidence while
   Tier A work proceeds.

Steps 3 and 4 are implementable immediately. Step 5 begins the clock that
cannot be shortened.
