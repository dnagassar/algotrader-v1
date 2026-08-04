# Active implementation handoff

## Standing operating decision

The V5.85 operating posture is unchanged: the SPY SMA 50/200 and RSI(14)
paper lanes operate in real-paper no-submit visibility mode with enabled
Windows tasks, sleeves reconcile, and canonical adjusted SPY data refreshes
at 20:10 ET. Crypto Tournament V2 remains preserved with its unattended
collector operator-disabled; do not resume it without a new explicit operator
request. Validated alpha remains zero, no profitability claim is made, and
live capital remains prohibited behind a separate operator hard gate.

## Checkout and writer ownership

- Writer checkout: `C:\Users\danie\.codex\worktrees\c029\algo_trader`.
- Branch: `claude/v5.92-vault-volatility-managed-triage`, branched from the
  V5.91 tip after that merged to `main`.
- Exactly one implementation writer at a time.

## V5.90 forward-shadow infrastructure (built)

Implements Route 2 of the V5.89 diagnosis — the only route that can produce
evidence this program has not already contaminated.

- `src/algotrader/research/forward_shadow_registry.py`: strategy-agnostic
  registry and append-only observation ledger.
- `tests/unit/test_forward_shadow_registry.py`: seventeen tests.
- `scripts/run_forward_shadow.ps1`: credential-fail-closed CLI wrapper.
- `docs/design/v5_90_forward_shadow_infrastructure.md`: contract, operating
  instructions, and honest limitations.

Three properties are enforced mechanically, not by convention:

1. Gates, universe, costs, and the required observation count are hashed into
   an immutable `registration_fingerprint`; editing any of them afterward
   makes every later load fail closed.
2. Backfill is impossible — an observation is admissible only inside
   `registration_date < session <= recorded_at`, with strictly increasing
   sessions.
3. Peeking early cannot produce a verdict — before the frozen observation
   count is reached the status payload omits every metric and gate outcome
   entirely, with no override.

The ledger is hash-chained from the registration fingerprint, so editing,
reordering, or truncating it is detected. Policy fingerprint:
`62f48951559bbc91193cca0a9d3309e9f06ddf7770ea414d735cc7cc59fefed3`.

**No hypothesis is registered.** Choosing what to shadow is an operator
decision, and the tempting candidate — the V5.89
`no_canary_g4_always_offensive` ablation — is outcome-contaminated as a
historical claim. Registering it as a *forward* hypothesis is legitimate
because the forward window is untouched, but that is a deliberate on-record
choice, not a side effect of building the tool.

## Repository consolidation (done)

`origin/main` was fast-forwarded `600bf72..6035d68` after
`verify_offline.ps1 -Full -Shards 8` returned PASS at that tip. This
consolidated roughly thirty previously local-only lane commits spanning
V5.53 through V5.88. Local `main` and `origin/main` now agree at `6035d68`,
and every `codex/*` lane tip is an ancestor of `origin/main`. The push was a
clean fast-forward; no force, no history rewrite, no lost work. Older
`antigravity/*`, `relay/*`, and legacy `claude/*` branches remain
deliberately unmerged and untouched.

## V5.89 Keller Bold Asset Allocation (closed)

Operator-directed final alpha push, executed under the standing constraints:
no credential exposure, no paid services, no live capital.

- `docs/design/v5_89_final_alpha_push_plan.md` and
  `..._preregistration.md` (`e77eede`): frozen plan and protocol.
- `7dc2439`: HYG and TIP added to the adjusted-EOD allowlist across both
  execution modules, the refresh script, and their contract tests.
- `scripts/refresh_v589_baa_data.ps1`: seventeen exact GET-only Tiingo EOD
  requests through the existing adapter.
- `src/algotrader/research/baa_data_manifest.py`: outcome-blind admission.
- `src/algotrader/research/baa_tournament.py`,
  `tests/unit/test_baa_tournament.py`,
  `scripts/run_v589_baa_tournament.ps1` (`722363a`): frozen replay engine,
  thirteen tests, credential-fail-closed wrapper — all committed *before*
  the reveal, closing the disclosure gap V5.88 had to carry.
- `docs/design/v5_89_keller_bold_asset_allocation_terminal_decision.md` and
  `..._data_receipt.md`: closure and outcome-blind data evidence.

Route: `no_candidate_passed`. Both BAA-G4 and BAA-G12 failed all five gate
groups. The decisive finding is mechanistic: the canary defensive overlay
fired in 22 of 47 months and, versus an otherwise identical no-canary
ablation, cost the aggressive variant 18.14 annualized points and 0.821
Sharpe while buying no meaningful drawdown relief.

## Program diagnosis

`docs/design/v5_89_alpha_program_terminal_diagnosis.md` records the
program-level conclusion across sixteen tested families: zero validated alpha,
with a single dominant structural cause — every tested family is a
diversification or defense rule, and every scoreable OOS window is dominated
by an exceptional concentrated US-equity advance that the frozen SPY value
route requires candidates to match. The recommendation is to stop enumerating
published families and instead build forward-shadow infrastructure so one
registered hypothesis can accumulate uncontaminated evidence. Restating the
objective away from "beat SPY" is available but is an explicit operator
decision, not a retrofit.

## V5.91 vault cross-sectional trend triage (closed)

First use of the V5.90 vault: buying statistical breadth from markets never
acquired here instead of buying it from calendar time.

- `docs/design/v5_91_..._preregistration.md` (`09cf026`): frozen protocol.
- `7f3ade7`: eighteen single-country ETFs added to the adjusted-EOD allowlist.
- `559a5ef`: engine, tests, admission, and outcome-blind receipt, all committed
  before the reveal.
- `docs/design/v5_91_..._terminal_decision.md`: closure evidence.

Route: `close_triage_without_tuning`. The primary breadth gate passed at
exactly its threshold — 13 of 18 markets, binomial p `0.048126220703` — but two
secondary gates failed and the protocol requires all of them.

The failures are diagnostic, not noise. Post-2007 Sharpe wins were **6 of 18**
against 13 of 18 over the full window, so essentially the whole edge lives in
2001-2007. Raising costs from 5 bps to 15 bps dropped wins from 13 to 10.
Drawdown improved in **18 of 18** markets, but annualized return was lower than
buy-and-hold in 13 of 18 — the same buy-protection-with-return trade V5.88 and
V5.89 documented. Mean pairwise excess correlation was `0.630936283855`, so the
nominal p overstated significance, exactly as the protocol disclosed in advance.

Cost: one session, 5,454 decisions across eighteen markets. V5.89 rested on 47
decisions; a six-month forward shadow of a monthly rule would give six. The
triage layer did its job — a published effect was screened out in hours rather
than after a forward window.

## V5.92 vault volatility-managed triage (closed)

Second and final vault triage, on the eighteen single-country markets left
untouched after V5.91 spent the first eighteen. Deliberately a **different
mechanism**, not a re-run: V5.91's protocol forbids adjusting the universe after
a failure, so re-testing absolute trend on a fresh cohort would have been
universe-shopping. V5.92 tests volatility-managed sizing, which never consults
direction at all.

- `docs/design/v5_92_..._preregistration.md` (`a24198f`): frozen protocol,
  including an explicit disclosure that the mechanism was chosen because V5.77
  was the strongest prior candidate.
- `b67aa35`: eighteen markets added to the adjusted-EOD allowlist.
- `5ec8dd7`: engine, tests, admission, receipt — committed before the reveal.
- `docs/design/v5_92_..._terminal_decision.md`: closure evidence.

Route: `close_triage_without_tuning`, decisively. Sharpe wins **2 of 18**
(binomial p `0.999927520752` — evidence in the opposite direction), **0 of 18**
in the second half, median Sharpe delta `-0.050266420387`, stress 1 of 18.
Drawdown improved in 17 of 18. Average target weight ran 0.52-0.87 because
emerging-market volatility sits far above the frozen 15% target, so the rule was
persistently under-invested and paid for its drawdown protection in return.

**Caveat that governs interpretation:** the repository forbids leverage, so the
frozen rule capped weight at 1.0 and could only de-risk. Moreira-Muir's
published construction also levers *up* in calm periods, which is where much of
the source effect originates. This therefore closes "volatility-capped exposure
without leverage", not volatility-managed portfolios as published. Do not
report it as a refutation of the paper.

## Replicated cross-triage finding

Across V5.91 and V5.92 — two different mechanisms, 36 disjoint never-acquired
markets — the same result holds: drawdown improves almost universally (18/18 and
17/18), annualized return falls in the large majority, and neither clears a
cost-robust, regime-consistent Sharpe bar. Defensive overlays buy drawdown
reduction and pay in return; at realistic costs the exchange has not been
favorable. This is the same trade V5.88 and V5.89 found on contaminated
US-centric data, now confirmed on clean data. V5.92's mean pairwise excess
correlation of `0.422316794291` is well below V5.91's `0.630936283855`, so this
negative is closer to independent and correspondingly stronger.

**The single-country equity vault is now spent.** 91 distinct symbols acquired.
Any further triage needs a different asset class or a genuinely new hypothesis;
the remaining vault is non-equity.

## V5.94-V5.96 regime-conditional ensemble restructure

The operator restated the program objective on 2026-08-03: the goal is an
ensemble of regime-conditional components, not a standalone SPY-beater. The
prior harness was structurally hostile to that — its calendar-wide consistency
gate rejected specialists by construction, and its closure rule prevented any
finding from composing into a system.

- `v5_94_...restructure.md`: design rationale, ADOPTED.
- `v5_95_ensemble_objective_and_regime_preregistration.md`: the binding
  contract. Objective is **maximize Sharpe subject to a hard 0.20 drawdown
  ceiling**; four causal regimes on trend x volatility from SPY; component
  gates including occurrence-based consistency.
- `src/algotrader/research/regime_classifier.py`, `ensemble_harness.py`,
  `tier_a_cohort_scoring.py` plus tests.
- `v5_96_..._preregistration.md` / `..._terminal_decision.md`: first Tier A
  cohort, four components, one per regime.

**Key repair:** consistency is measured across *regime occurrences*, never
calendar periods. A bear-regime component is judged on bear-market episodes and
is never penalized for sitting flat elsewhere.

**Cohort result: 0 of 4 admitted** (`cohort_closed_no_component_admitted`).
`defensive_quality_equity` posted a +0.126 aggregate in-regime Sharpe edge that
cleared the threshold and would have been admitted by a naive regime harness —
but won only 2 of 19 episodes. The occurrence gate and its Bonferroni binomial
test rejected it. That discrimination is the restructure working.

## Two harness defects to fix before a second cohort

Recorded in the V5.96 terminal decision, both blocking:

1. **Regime occupancy was never checked.** `calm_down` occupied 17 of 3,220
   sessions, giving zero scoreable episodes, so
   `short_duration_credit_carry` was untestable rather than tested. Add an
   outcome-blind occupancy precondition to regime registration.
2. **Monthly actions scored against daily labels.** Components act at
   month-end but episodes are daily-label runs, so a component can be scored
   over an episode it did not hold. Out-of-regime drag was positive for all
   four despite each being nominally in cash. This means the +0.126 vs 2/19
   divergence cannot be attributed between genuine inconsistency and
   misalignment. Align the granularities, frozen before any rescoring.

Neither fix may rescore this cohort; those four components are closed under the
contract they were registered against.

## V5.97 harness repair and Tier A cohort 2 (closed)

Both V5.96 defects repaired, then cohort 2 run against them.

- **Occupancy precondition** (`regime_occupancy`): a regime must clear a
  minimum scoreable-episode count on the intended panel before any component
  may be declared against it. Outcome-blind — depends on dates and labels only.
  `calm_down` measured 1 episode against a required 8 and was excluded.
- **Scoring aligned to holdings** (`effective_action_labels`): targets form on
  raw month-end labels; scoring conditions on the effective labels those
  targets imply. Contract fingerprint moved to
  `9b5e97b43e7d59578fdcce38eee0b22b04cfa5b6971361720ef94e1e3a2ea564`.

Route: `cohort_closed_no_component_admitted`, **0 of 3**.
`value_size_factor_tilt` +0.0012 edge / 6-of-13 episodes;
`convertible_crossover_credit` -0.075 / 4-of-15;
`precious_metals_crisis_hedge` -0.118 / 3-of-8. Two of three had negative
in-regime edges: conditioning was worse than always-holding.

**A third defect was found while verifying the second repair.** The first
cohort-2 run passed effective labels to both target formation and scoring,
double-lagging the component. Out-of-regime drag stayed nonzero — the exact
symptom the repair should have removed — so the number was interrogated rather
than accepted. `precious_metals_crisis_hedge` scored +0.353 under the double
lag and -0.118 corrected: a 0.47 sign-reversing swing. Run
`5b29717230fc692b0699439620af1ee15796e773703ffc32b5258215c5f32bda` is **void**.

Residual out-of-regime drag is now small and **two-sided** (-0.0026, +0.0068,
-0.00005) versus uniformly positive under V5.96. Mixed signs are the signature
of the one-session exit under causal t+1 execution, not misattribution.

## V5.98 tax-loss forced-seller detector (closed)

The program's first **structural** hypothesis: a group compelled to sell for a
reason unrelated to price (tax treatment of realised losses) on a known
calendar. Every prior milestone tested a published formula instead.

45 held ETFs, 5,056 sessions, 19 cycles (2007-2025), **zero network requests**.
Bottom-quintile year-to-date losers at the November close, measured over a
December leg and a January leg against the equal-weight universe.

Route: `close_detector_without_tuning`.

- **December pressure present:** losers underperformed in 12 of 19 Decembers,
  mean excess `-0.003163649396`. The forced-selling footprint is visible.
- **January reversal absent:** positive in 10 of 19 years, binomial
  `p = 0.500000000000` — an exact coin flip. 9 of 19 at stress costs.
- **Legs are linked:** correlation `-0.418862185790`; harder December pressure
  produced a bigger January bounce. 2022 was the extreme on both sides
  (`-0.0390` then `+0.0437`). The mechanism is real; it is not tradeable here.

The protocol required both legs precisely so a January-only result would fail.
It received the mirror image and failed that too. Note the December gate itself
is `p = 0.179641723633` — a preregistered coherence check, never evidence.

## Where the structural direction stands

Of four candidate structural edges, exactly one was testable without paid data
and it is now closed. The other three — index rebalances, genuinely small
illiquid names, operationally annoying situations — all require corporate-action
feeds or delisted-inclusive universes. **Data access, not engineering, is the
binding constraint on this direction.** The ETF substitution used here was
disclosed in advance as a reason a null could occur even if the mechanism is
real, and that is roughly what happened.

## Verification

- Credential preflight: zero ambient credential-bearing environment
  variables before every offline run.
- `verify_offline.ps1 -Full -Shards 8` at `6035d68`: PASS
  (`bounded_full_suite=PASS`, offline guards 109 passed); `src`, `tests`, and
  `scripts` at that tip were byte-identical to what was pushed.
- Allowlist contract suites after the HYG/TIP change: 113 passed.
- `tests/unit/test_baa_tournament.py`: 13 passed.
- Tournament wrapper exited 0; two full replays byte-identical.
- `verify_offline.ps1 -Full -Shards 8` at the V5.89 tip `f3b81c3`: PASS
  (10,421 collected, 10,416 passed, 5 skipped, 0 failures, 0 errors, all
  eight shards exit 0, collection and execution equivalence PASS). `main` was
  fast-forwarded to `f3b81c3` and pushed on that evidence.
- `tests/unit/test_forward_shadow_registry.py`: 29 passed;
  `test_forward_shadow_vault.py`: 10 passed.
- `tests/unit/test_vault_cross_sectional_trend_triage.py`: 13 passed.
- `tests/unit/test_ensemble_harness.py`: 32 passed.
- `verify_offline.ps1 -Full -Shards 4` at `a88622e`: PASS (10,553 collected,
  10,548 passed, 5 skipped, 0 failures).
- `verify_offline.ps1 -Full -Shards 4` at `8f70cec`: PASS (10,553 collected,
  10,548 passed, 5 skipped, 0 failures).
- `verify_offline.ps1 -Full -Shards 4` at `261766d`: PASS (10,542 collected,
  10,537 passed, 5 skipped, 0 failures).
- `tests/unit/test_vault_volatility_managed_triage.py`: 14 passed.
- V5.92 allowlist contract suites: 121 passed.
- `verify_offline.ps1 -Full -Shards 4` at the V5.91 tip `6eb1579`: PASS
  (10,477 collected, 10,472 passed, 5 skipped, 0 failures, 0 errors).
- V5.91 allowlist contract suites: 117 passed.
- Architecture and safety invariants after V5.90: 69 passed
  (dependency direction, broker mutation surface, network guard).
- The V5.90 forward-shadow wrapper was confirmed to exit 2 with
  `blocked_unsafe_environment` under a credential-bearing environment without
  echoing the sentinel value.

## Safety and trust

- Seventeen market-data requests were GET-only, destination-allowlisted, and
  recorded `token_value_recorded`, `market_data_token_value_printed`, and
  `market_data_token_value_written` as `false`. The credential was loaded only
  inside the trusted adapter boundary from a dotenv outside this checkout and
  was never read, printed, or persisted by any tool.
- No broker, account, order, or position access; no paper mutation; no live
  activity; no paid service.
- External source and tracker performance figures remained untrusted and
  controlled no rank, gate, or route.
- Existing caps, receipts, reconciliation, sleeve ownership, and live
  prohibitions are unchanged.

## Exact next action

This is an operator decision, not an implementation task. Twenty-three
milestones, zero validated alpha, and the free-data search space is close to
exhausted. Three options, stated without preference:

1. **Acquire event data** (corporate actions, point-in-time universe including
   delisted names). This is the only path that unlocks the three remaining
   structural edges, which are the better ideas. It buys the ability to look;
   it does not promise an edge.
2. **Continue on free data.** No further free structural hypothesis is
   currently identified that is worth the effort.
3. **Stop.** The system is honest and has reported clearly that no edge exists
   in what it can currently see.

If work continues, the standing engineering priority from V5.97 is unchanged:
raise test coverage of the ensemble scoring path before running a third cohort.
Three defects shipped into that harness across two milestones and two would
have produced false positives.

Standing prohibitions unchanged: V5.96's four and V5.97's three components are
closed and may not be rescored under any corrected harness; V5.98's detector may
not be re-run on a different universe or holding period; `calm_down` hosts no
component until a panel where it occurs; Tier B requires a forward shadow.

Live capital remains an operator hard gate that no work in this session moved.
