# V5.97 harness repair and Tier A cohort 2 preregistration

Status: frozen before any cohort-2 component is scored. Records the two V5.96
harness repairs and registers the second Tier A cohort against them.

## 1. Repair one: regime occupancy precondition

V5.96 declared `short_duration_credit_carry` against `calm_down`, which
occupied 17 of 3,220 sessions and produced **zero** scoreable episodes. The
component was untestable rather than tested, and it consumed a cohort slot and
a multiplicity share for no information.

`regime_classifier.regime_occupancy` now reports, per regime, session count,
scoreable episode count, and sufficiency against declared minimums. Occupancy
is a function of dates and labels only — never of returns — so running it
before declaring components is outcome-blind.

**Measured occupancy** on the 2013-10-10..2026-07-31 panel, minimum 8 episodes
of at least 10 sessions, under the repaired label basis:

| Regime | Sessions | Scoreable episodes | Sufficient |
| --- | ---: | ---: | --- |
| `calm_up` | 1,614 | 13 | yes |
| `stressed_up` | 1,066 | 15 | yes |
| `stressed_down` | 503 | 8 | yes |
| `calm_down` | 21 | 1 | **no** |

`calm_down` is excluded from cohort 2. No component may be declared against it
until a panel is found where it occurs; that is a property of the window, not a
judgement about the regime.

## 2. Repair two: scoring conditions on holdings, not raw labels

V5.96 formed targets at month-end but scored against *daily* labels, so a
component could be graded across an episode it never held, and could book
returns on sessions labelled out-of-regime because it was still holding from
the prior month-end. Out-of-regime drag was positive for all four components
despite each being nominally in cash — the direct symptom.

`regime_classifier.effective_action_labels` maps each session to the label
observed at the most recent **prior** month-end, which is the label that
determined the target now in force. Conditioning and holding therefore
coincide by construction, and the transform stays causal.

Scoring uses effective labels from this point forward. The ensemble contract
records the change and its fingerprint moved from
`7cb91fae9224ad635a172740dc11494c6cdc1d8a517ab2fdf376349bb6ff02a8` to
`9b5e97b43e7d59578fdcce38eee0b22b04cfa5b6971361720ef94e1e3a2ea564`.

**Neither repair may be used to rescore V5.96.** Those four components are
closed under the contract they were registered against. Rescoring a closed
cohort under a friendlier harness is the exact move this program forbids.

## 3. Cohort plan, frozen before any member registers

- Cohort ID: `tier_a_cohort_2`.
- Planned component count: **3**, one per qualifying regime. A fourth is
  refused.
- Regime count remains **4** as frozen by V5.95, even though only three
  qualify. The multiplicity divisor uses the frozen regime set, not the
  surviving subset, so excluding a regime cannot loosen the bar.
- Multiplicity: `3 x 4 = 12` hypotheses. Family-wise alpha `0.050000000000`;
  Bonferroni-adjusted per-hypothesis alpha `0.004166666667`.
- A side effect worth noting: at this alpha a perfect 8-of-8 episode record
  scores `p = 0.00390625` and now **passes**, where under cohort 1's stricter
  `0.003125` it could not. This is a consequence of a smaller planned cohort,
  fixed in advance, not a threshold relaxed to fit a result.

## 4. Components

Every component holds an equal-weight basket while its declared regime's
**effective** label is active, and zero-return cash otherwise. Monthly
formation, next-session execution, standard drift, turnover, and cost
conventions. Each benchmark is the same basket held continuously, so a
component wins only if conditioning beats always-holding.

### `precious_metals_crisis_hedge` → `stressed_down`
- Assets: `GDX`, `GDXJ`, `PPLT`.
- Mechanism: precious metals and their miners have historically attracted
  flows during equity stress, and unlike duration they carry no rate risk.

### `convertible_crossover_credit` → `stressed_up`
- Assets: `CWB`, `ANGL`, `EMLC`.
- Mechanism: convertibles hold equity upside with a bond floor, and
  fallen-angel and local-currency emerging credit carry spreads that compress
  as stress resolves upward. Deliberately not another low-volatility equity
  tilt, so this is not V5.96's defensive sleeve in a new basket.

### `value_size_factor_tilt` → `calm_up`
- Assets: `VLUE`, `SIZE`, `IJR`.
- Mechanism: the value and size premia are long-documented and should express
  in sustained calm advances rather than in stress.

## 5. Data contract

- Nine component symbols plus `SPY` as regime reference:
  `GDX,GDXJ,PPLT,CWB,ANGL,EMLC,VLUE,SIZE,IJR,SPY`.
- All nine confirmed vault-eligible before this document was written. None was
  used by V5.96; reusing a scored component's assets would carry that
  component's known conditional behaviour.
- Provider: authenticated Tiingo EOD, free tier, GET-only, `adjClose` to
  `adjusted_close`, identity mappings.
- Requested coverage: 2005-01-03 through 2026-07-31.
- Admitted panel: the exact common-session intersection, at least `2,600`
  sessions, all of which must fall after the 1,320-session regime warm-up.

## 6. Gates

Unchanged from V5.95 and V5.96 except the alpha above, and now enforced on
effective labels. All required, including occupancy sufficiency for the
declared regime, in-regime Sharpe edge, cost robustness at 15 bps,
occurrence-based win rate, Bonferroni-corrected episode significance,
out-of-regime neutrality, non-redundancy, marginal ensemble contribution, and
the hard 0.20 drawdown ceiling.

## 7. Expected outcome

Twenty milestones, zero validated alpha, and cohort 1 admitted none of four.
The most likely result here is again zero admissions. The repairs make the
test *fair*, not easier: the occupancy gate removes an untestable slot and the
label alignment removes attribution noise in both directions. Neither creates
an edge that is not there.

## 8. Boundary

Historical evidence only. A passing component is admitted to a historical
ensemble and nothing more — no validated-alpha claim, no forward-shadow slot,
no paper or live authority. Tier B still requires a forward shadow. Live
capital remains an operator hard gate untouched by this document.
