# V5.96 Tier A component cohort terminal decision

Status: terminally closed. Route `cohort_closed_no_component_admitted`;
**0 of 4** components admitted. The protocol was frozen at `66aa31c`, the
allowlist at `1f0dc48`, and the scoring engine at `3fe5a47` — all before any
component outcome existed.

## Result

- Panel: 3,220 common sessions, `2013-10-10`..`2026-07-31`, 13 symbols.
- Regime sessions: `calm_up` 1,686, `stressed_up` 1,026, `stressed_down` 491,
  `calm_down` 17.
- Result SHA-256:
  `236a6b7369b9a4a30bea2a43cec8c6eef3cd01582135facda5a14e1d73ae78dc`.
- Two replays byte-identical.

| Component | Regime | Sharpe edge | Episodes | Binomial p | Verdict |
| --- | --- | ---: | ---: | ---: | --- |
| `defensive_quality_equity` | `stressed_up` | `+0.125512570265` | 2/19 | `0.99996` | fail |
| `flight_to_quality_duration` | `stressed_down` | `+0.052568450041` | 4/12 | `0.92700` | fail |
| `momentum_growth_participation` | `calm_up` | `-0.034725356906` | 3/14 | `0.99353` | fail |
| `short_duration_credit_carry` | `calm_down` | `-4.720443208367` | 0/0 | `1.00000` | fail |

## The occurrence gate earned its place immediately

`defensive_quality_equity` is the case this restructure was built to handle,
and it cuts against the restructure's own hopes.

Its aggregate in-regime Sharpe edge was `+0.125512570265`, clearing the 0.10
threshold, and it survived stress costs at `+0.095709117254`. Judged on
aggregate conditional performance — which is how a naive regime harness would
score it — this component **would have been admitted**.

It won 2 of 19 episodes.

An aggregate edge concentrated in a handful of episodes is not a regime effect;
it is a couple of good months wearing one. The occurrence-based consistency gate
and its Bonferroni-corrected binomial test both rejected it, and the rejection
is the correct call on the evidence presented.

## Two design defects this run exposed

Recorded because the cohort was as much a test of the machinery as of the
components, and both issues must be fixed before a second cohort.

**1. The regime partition is severely unbalanced on this window.**
`calm_down` occurred in **17 of 3,220 sessions** — 0.5% — yielding zero
scoreable episodes and making `short_duration_credit_carry` untestable rather
than tested. Its reported Sharpe edge of `-4.72` is an artifact of 17 scattered
sessions and carries no information. The V5.95 regime set was declared from
mechanism, which was the right principle, but it was never checked for
occupancy against a real window. A regime that barely occurs cannot host a
component, and registering one against it wasted a cohort slot and a
multiplicity share.

**2. Monthly actions are scored against daily labels.**
Components form targets at month-end and hold through the following month, but
episodes are contiguous runs of *daily* labels. A component can therefore be
scored across an episode during which it held nothing, or credited with
out-of-regime sessions where it was still holding from the prior month-end
signal. This shows up directly in the out-of-regime drag, which was positive
for all four components (`+0.0064` to `+0.0250`) despite each being nominally in
cash outside its regime.

The consequence is real: for `defensive_quality_equity` the gap between a
`+0.126` aggregate edge and a 2-of-19 episode record may reflect genuine
inconsistency, or may reflect this misalignment, and **this run cannot
distinguish the two**. That is a limitation of the harness as built, not a
finding about the component.

Neither defect changes the route. Three of four components failed on multiple
independent gates, `momentum_growth_participation` had a negative edge before
any consistency test applied, and no component came close to admission. But the
0/4 result should be read as "this cohort produced no admissible evidence"
rather than "these four mechanisms are refuted."

## What is not concluded

- These components are **not** shown to lack merit. Two were mis-scored by
  construction (`short_duration_credit_carry` untestable, all four subject to
  label misalignment).
- The regime set is **not** invalidated as a concept, but its occupancy is now
  known to be unusable for `calm_down` over this window.
- No validated alpha. No forward-shadow slot claimed. No paper or live
  authority follows.

## Required before a second cohort

1. Add an **occupancy precondition** to regime registration: a regime must
   contain a preregistered minimum number of scoreable episodes on the intended
   panel before any component may be declared against it. Occupancy is a
   property of dates, not outcomes, so checking it is outcome-blind.
2. Align the **action and scoring granularity**: either score on
   month-end-aligned episode windows, or let components act on the daily label.
   The choice must be frozen before rescoring anything.

Neither change may be used to rescore this cohort. These four components are
closed under the contract they were registered against; a corrected harness
requires new components or a Tier B forward shadow.

## Trust and safety

Thirteen market-data requests were GET-only, destination-allowlisted, and
recorded `token_value_recorded`, `market_data_token_value_printed`, and
`market_data_token_value_written` as `false`. Scoring was offline,
deterministic, credential-free, and byte-identically replayed. Broker, account,
order, position, paper-mutation, and live activity were all false. Existing
caps, receipts, reconciliation, and live prohibitions are unchanged.
