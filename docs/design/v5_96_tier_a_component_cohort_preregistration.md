# V5.96 Tier A component cohort preregistration

Status: frozen before any component is scored. This registers the first cohort
under the V5.95 ensemble contract. No component below has ever been scored in
this repository, and none of their data has ever been acquired here.

## 1. Cohort plan, frozen before any member registers

- Cohort ID: `tier_a_cohort_1`.
- Planned component count: **4**. Registering a fifth is refused.
- Regime count: **4**, fixed by V5.95 section 2.
- Multiplicity: `4 x 4 = 16` hypotheses. Family-wise alpha
  `0.050000000000`; Bonferroni-adjusted per-hypothesis alpha
  `0.003125000000`.
- Each component is declared against **exactly one** regime, chosen from its
  mechanism before any outcome was computed. A component may not be re-declared
  against a different regime after scoring.

## 2. Disclosed selection bias

Honesty requires naming a weaker contamination than Tier B, which this cohort
does carry.

No rule below has been scored here, and no data below has been acquired here,
so no component's own outcome is known. That is what Tier A means and it holds.
What is *not* clean: the choice to avoid timing overlays entirely was informed
by nineteen milestones of accumulated negative results at the family level. That
is family-level knowledge, not component-level knowledge, and it is disclosed
rather than hidden.

The practical consequence: these components are deliberately **not** timing
rules. Each is a persistent exposure whose mechanism is expected to pay in one
specific state, which is what the ensemble restructure was built to evaluate and
what the previous harness could not express.

## 3. Components

Every component holds an equal-weight basket of its named assets while its
declared regime is active, and zero-return cash otherwise. Weights are equal
within the basket, monthly rebalanced, executed at the next common session close
after the month-end signal, with the same drift, turnover, and cost conventions
used throughout this repository.

### `flight_to_quality_duration` → regime `stressed_down`

- Assets: `VGLT`, `EDV`, `GOVT`.
- Mechanism: long-duration sovereign debt has historically absorbed capital
  fleeing equity risk during stressed declines. The claim is about *when* it is
  held, not that duration outperforms in general.
- Benchmark: equal-weight buy-and-hold of the same three assets across the whole
  scored window.

### `defensive_quality_equity` → regime `stressed_up`

- Assets: `USMV`, `SPHD`, `NOBL`.
- Mechanism: low-volatility and dividend-persistence tilts are documented to
  lag in calm advances and hold up in volatile ones. Stressed uptrends are the
  state where that asymmetry should be visible.
- Benchmark: equal-weight buy-and-hold of the same three assets.

### `short_duration_credit_carry` → regime `calm_down`

- Assets: `VCSH`, `BKLN`, `FLOT`.
- Mechanism: short-duration and floating-rate credit earn spread with limited
  rate sensitivity, which should be a positive-carry place to sit through
  orderly declines that are not credit events.
- Benchmark: equal-weight buy-and-hold of the same three assets.

### `momentum_growth_participation` → regime `calm_up`

- Assets: `MTUM`, `SMH`, `VBK`.
- Mechanism: momentum, semiconductors, and small-cap growth are high-beta
  expressions expected to capture more of a calm advance than a broad basket.
- Benchmark: equal-weight buy-and-hold of the same three assets.

Each component's benchmark is its **own** basket held continuously. The
component therefore cannot win merely by holding good assets; it wins only if
*conditioning on its regime* beats holding the same assets always. This is a
deliberately harder test than beating cash or beating SPY, and it isolates the
regime claim from the asset-selection claim.

## 4. Data contract

- Twelve symbols: `VGLT,EDV,GOVT,USMV,SPHD,NOBL,VCSH,BKLN,FLOT,MTUM,SMH,VBK`.
- All twelve confirmed vault-eligible before this document was written; the
  repository had touched 109 distinct symbols at that scan and none were among
  them.
- Regime reference `SPY` is already held and is used only as a market-state
  classifier, never as a component or benchmark.
- Provider: authenticated Tiingo EOD, free tier, GET-only through the
  destination-allowlisted adapter. Field `adjClose` to `adjusted_close`,
  identity mappings only.
- Requested coverage: 2005-01-03 through 2026-07-31, one request per symbol.
- Admitted panel: the exact common-session intersection of the twelve component
  symbols and SPY, which must contain at least `2,600` sessions **after** the
  1,320-session regime warm-up. Fewer blocks the cohort rather than shrinking
  the test.

## 5. Gates

The V5.95 component gates apply unchanged, plus the multiplicity term this
cohort makes concrete:

- Episode wins must be significant at the Bonferroni-adjusted alpha
  `0.003125000000`, by exact one-sided binomial test against `p = 0.5` on
  scoreable episodes.

This gate is additive and strictly tightening. It is being specified now,
before any component has been scored, precisely so that it cannot later be
described as a threshold chosen to fit a result.

A component passes only if **every** V5.95 gate and this one hold. A cohort
member that fails is closed without tuning; its regime declaration, assets, and
thresholds may not be adjusted and it may not be re-registered.

## 6. Expected outcome

Stated in advance so it cannot be claimed afterward: the base rate of this
program is nineteen consecutive family-level failures. The most likely result is
that some or all four components fail, and the honest value of this cohort is
that it tests the ensemble machinery on real Tier A data with a real
possibility of a clean negative.

Passing components are admitted to a historical ensemble only. Admission is not
validated alpha, authorizes no paper or live activity, and does not shorten the
forward-shadow requirement for anything in Tier B.

## 7. Safety

Offline research plus twelve exact authorized GET-only market-data requests.
Broker, account, order, and position access, paper mutation, and live activity
are forbidden. No credential value is requested, printed, returned, or persisted
outside the trusted adapter boundary. Live capital remains an operator hard gate
untouched by this document.
