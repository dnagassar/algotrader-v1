# V5.97 harness repair and Tier A cohort 2 terminal decision

Status: terminally closed. Route `cohort_closed_no_component_admitted`;
**0 of 3** components admitted. Protocol frozen at `4e0f0f9`, allowlist at
`e0e5c9a`, engine at `62b0b1a` — all before any cohort-2 outcome existed.

## Result

- Panel: 3,342 sessions, `2013-04-18`..`2026-07-31`, 10 symbols.
- Result SHA-256:
  `b3eb2cb3b3ed83dbca64968698f6876a3755158ef601f33b8b08ba2842c7ee70`.
- Two replays byte-identical.

| Component | Regime | Sharpe edge | Episodes | Verdict |
| --- | --- | ---: | ---: | --- |
| `value_size_factor_tilt` | `calm_up` | `+0.001208224604` | 6/13 | fail |
| `convertible_crossover_credit` | `stressed_up` | `-0.075298985395` | 4/15 | fail |
| `precious_metals_crisis_hedge` | `stressed_down` | `-0.117928950319` | 3/8 | fail |

## Repair one verified: occupancy precondition

`regime_occupancy` measured `calm_down` at 21 sessions and **1** scoreable
episode against a required 8, marked it insufficient, and the cohort declared
no component against it. V5.96 wasted a slot and a multiplicity share on
exactly that regime. The precondition is enforced in the engine, so a future
cohort cannot repeat it: declaring against an insufficient regime raises before
any component is scored.

## Repair two verified — after it exposed a third defect

Aligning scoring to holdings surfaced a bug I introduced while implementing it,
and the check written to verify the repair is what caught it.

The first corrected run passed **effective** labels to both target formation and
scoring. Effective labels already lag to the prior month-end, so forming targets
on them lagged the component a second time: it acted on the month-end *before*
the one that governed its scoring. Out-of-regime drag stayed stubbornly nonzero,
which is precisely the symptom the repair was supposed to eliminate, so the
number was interrogated rather than accepted.

The corrected design is explicit: **targets form on raw month-end labels;
scoring conditions on the effective labels those targets imply.**

That bug was not cosmetic. `precious_metals_crisis_hedge` scored an in-regime
Sharpe edge of `+0.352706250028` under the double lag and
`-0.117928950319` once corrected — a swing of 0.47 that reverses the sign. The
first cohort-2 run (`5b29717230fc692b0699439620af1ee15796e773703ffc32b5258215c5f32bda`)
is **void** and its numbers must not be cited. The gates, protocol, and
components were unchanged; only a defective implementation was replaced.

**Residual drag is expected and is not misalignment.** Out-of-regime drag is now
`-0.002595121768`, `+0.006846416404`, and `-0.000048360993` — small and
**two-sided**. Under V5.96's daily labels all four components showed positive
drag, the signature of systematically holding while nominally out of regime.
Mixed signs are the signature of the remaining effect: the one-session exit,
where a component earns the move into the session at which it closes its
position. That is the unavoidable cost of next-session execution, not an
attribution error, and it cannot be removed without abandoning causal lag.

## What the cohort shows

Two of three components had **negative** in-regime Sharpe edges: conditioning on
the declared regime was worse than holding the same basket continuously.
`value_size_factor_tilt` was flat at `+0.0012` with a 6-of-13 episode record —
a coin flip. `precious_metals_crisis_hedge` reached the required 8 episodes,
the minimum the occupancy gate now guarantees, and lost on 5 of them.

No mechanism showed regime-conditional skill. Combined with cohort 1, seven
components across four mechanisms and two disjoint asset sets have now been
tested under the restructure, and none has been admitted.

## What is not concluded

The harness is now measuring what it claims to measure, which cohort 1 could
not honestly assert. But two cohorts of three-to-four components is thin
evidence about regime conditioning in general, and these seven components are
closed under their own contracts rather than refuted as mechanisms.

No validated alpha. No forward-shadow slot claimed. No paper or live authority.
Tier B still requires a forward shadow.

## Trust and safety

Ten market-data requests were GET-only, destination-allowlisted, and recorded
`token_value_recorded`, `market_data_token_value_printed`, and
`market_data_token_value_written` as `false`. Scoring was offline,
deterministic, credential-free, and byte-identically replayed. Broker, account,
order, position, paper-mutation, and live activity were all false. Existing
caps, receipts, reconciliation, and live prohibitions are unchanged.
