# V5.90 forward-shadow infrastructure

This implements Route 2 of the V5.89 alpha-program diagnosis: the only route
that can produce evidence this program has not already contaminated. It then
attacks the obvious objection to that route — that waiting six months to learn
nothing is an unacceptable price.

## Why this exists

Every scored window in this repository suffers the same defect. The rule was
selected after its history was visible, so a good backtest is partly a record
of our own hindsight. Sixteen families were tested that way and none passed,
but even a pass would have carried that asterisk.

A forward shadow removes the asterisk by construction: register a hypothesis at
a known instant, score it only on sessions that did not exist yet. There is
nothing to overfit to, because the data had not happened.

The hard part is not the idea. It is making the discipline survive contact with
a motivated operator six months later, and making the wait short enough to be
worth taking. Five properties are therefore enforced mechanically.

## 1. Gates are cryptographically bound to the registration

Hypothesis, universe, benchmark, rule fingerprint, cost assumption, decision
requirement, sequential boundaries, and cohort multiplicity all hash into a
single `registration_fingerprint`. Every load recomputes it from the stored
fields. Editing any of them afterward changes the hash and the ledger fails
closed, so moving the goalposts becomes a loud error rather than a silent
rewrite.

## 2. Backfill is structurally impossible

An observation is admissible only inside

```
registration_date < session <= recorded_at
```

A session on or before the registration date is rejected as backfill; a session
later than the moment of recording is rejected as a future session. Sessions
must strictly increase, so a gap cannot be filled in later with a conveniently
chosen day. The first observation starts from a flat book and pays a real entry
transition, forgoing any move that predates the shadow.

## 3. Evidence is counted in decisions, not days

This is the correction that matters most, and the original design got it wrong.

A monthly rule observed for 126 sessions has made **six decisions**, not 126.
The days in between are one decision being marked to market. A verdict computed
off 126 correlated daily returns looks statistically substantial and is not.

Every observation therefore carries an explicit `is_decision` flag — required,
never inferred, because a rule that re-evaluates and deliberately keeps its
previous target has still made a decision and only the adapter knows that. A
non-decision session may not change target weights.

Gates and the sequential test run on **completed decision intervals**: a
decision at session *d* takes effect the next session and is held through the
next decision session inclusive. An open position never contributes evidence.
This is what stops a low-frequency rule borrowing significance from days it
merely held.

## 4. Waiting is bounded by evidence, not the calendar

A pre-registered Wald SPRT runs on per-decision excess return against the
benchmark, testing `H0: mean excess = 0` against
`H1: mean excess = minimum_excess_per_decision`, with boundaries

```
efficacy: log((1 - beta) / effective_alpha)
futility: log(beta / (1 - effective_alpha))
```

Crossing the futility boundary closes the hypothesis early. This directly
answers the objection that a forward window might consume six months and return
nothing: a dead hypothesis announces itself in weeks, and the calendar cost is
paid only by hypotheses still plausibly alive.

Two deliberate choices:

- The test uses **magnitude**, not hit rate. A win-rate test would be simpler
  and would wrongly execute trend-following rules, which are legitimately
  low-win-rate and high-payoff.
- `reference_excess_sigma` is **declared at registration**, not estimated from
  the data it will judge. That is a preregistration commitment; estimating it
  later would let the boundary drift toward whatever the data wanted.

Stopping is refused before `minimum_decisions_before_stopping`, so a boundary
cannot fire on two lucky decisions.

## 5. Multiplicity is priced before the fact

Running eight hypotheses in parallel costs the same wall-clock as one, which is
the cheapest available speedup — but eight independent tests at alpha 0.05
produce a false positive about a third of the time.

A cohort therefore freezes its `planned_member_count` **before any member
registers**, and the Bonferroni divisor comes from that frozen count. Members
beyond it are refused. Registering twenty hypotheses and reporting the best as
though one had been tested is the exact abuse this prevents. The resulting
`effective_alpha` is frozen into each member's registration fingerprint and
feeds the sequential boundaries directly.

## Peeking still cannot produce a verdict

Until a frozen stopping condition fires — either the planned decision count or
a sequential boundary — evaluation returns an accrual packet with no return,
Sharpe, drawdown, benchmark delta, or gate outcome. Those keys are **absent**,
not null, and the rendered receipt says only that metrics are withheld. No flag
unlocks them. The realistic failure mode is not fraud; it is an honest person
checking at week three, seeing red, and quietly deciding the window was badly
chosen.

## Tamper evidence

The ledger is append-only JSONL hash-chained from the registration fingerprint:
each entry stores the prior entry's hash and its own hash covers its content.
Editing, reordering, or truncating breaks the chain and every later load fails
closed. Tests exercise edited, truncated, gate-mutated, and cohort-mutated
ledgers directly.

## The vault: buying breadth instead of time

Contamination is a property of what the analyst has seen, not of the calendar.
A market this repository has never requested is, for our own selection bias,
equivalent to data that has not happened — and it is available immediately.

That claim is only worth something if it can be checked. Every acquisition here
leaves a receipt, so the touched set is enumerable.
`forward_shadow_vault.scan_acquired_symbols` walks refresh receipts, canonical
and raw artifact filenames, and data manifests, and
`assert_vault_eligible` fails closed on any evidence. The scan is deliberately
over-inclusive: a false "already acquired" costs one discarded candidate, while
a false "never acquired" silently readmits the bias the vault exists to
exclude.

At the time of writing this repository has acquired **55 distinct symbols**.
The large untouched region is the single-country equity ETF universe, which
offers a genuine cross-section rather than one more time series.

The limits are real and stated in the report itself. The scan proves no
acquisition receipt exists **in this repository**. It cannot prove no human
ever looked at a chart elsewhere, and — the sharper limit — it cannot undo the
fact that a *published* rule's author saw global market history when choosing
the rule. The vault is clean for hypotheses we generate ourselves and only
partial for published families. Correlated markets are also not independent
tests: forty equity ETFs fall together.

## Operating it

```bash
pwsh ./scripts/run_forward_shadow.ps1 -Command policy
```

```bash
pwsh ./scripts/run_forward_shadow.ps1 -Command vault -Symbol EWZ,THD
```

```bash
pwsh ./scripts/run_forward_shadow.ps1 -Command status -Root runs/forward_shadow/<id> -AsOf 2026-08-10T22:00:00+00:00
```

Registration, cohort registration, and observation appending are library calls
(`register_forward_shadow_cohort`, `register_forward_shadow`,
`append_forward_shadow_observation`) so a strategy adapter supplies causal
target weights while this module owns accounting, the temporal envelope,
multiplicity, and the chain. The wrapper refuses to run in any
credential-bearing environment. The intended cadence is one append per
completed trading session, from the canonical panel the existing EOD job
already refreshes.

## Contract summary

- Policy fingerprint:
  `ccd2cb78a81bd746692d20077541cfbdc7902b138cbb778595a3b7685d25d332`
  (`build_forward_shadow_policy` raises on drift).
- Schema: `v5_90_forward_shadow_registry_v2`.
- Artifacts: `cohort.json`, `cohort_members.jsonl`, `registration.json`,
  `observations.jsonl`, `status.json`, `status.md`.
- Accounting mirrors the tournament engines: drift between actions, one-way
  turnover as half the absolute weight change including implicit cash, a frozen
  bps cost, zero-return implicit cash. `Decimal` quantized to twelve places so
  the chain is platform-stable.
- Authority: network, credential, broker, paper mutation, capital allocation,
  and live are false in the policy, the registration, and every ledger entry. A
  pass — including an efficacy stop — routes only to operator review and
  authorizes neither paper nor live.

## What is deliberately not done here

No hypothesis is registered and no cohort is opened. Choosing what to shadow is
an operator decision, and the V5.89 diagnosis is explicit that the most
tempting candidate — the `no_canary_g4_always_offensive` ablation that beat SPY
on return — is contaminated *as a historical claim* because we saw its result
inside a scored run. Registering it as a **forward** hypothesis is legitimate,
since the forward window is untouched. That is a deliberate on-record choice,
not a side effect of building the tool.

## Honest limitations

- Sequential testing trades a little power for speed: stopping early on a real
  but modest edge is possible. The futility side is the cheap win; the efficacy
  side should be read as "worth operator review", never as proof.
- Bonferroni is conservative. With many correlated hypotheses it will
  under-reject; that is the safe direction, but it is not free.
- The raw ledger is readable on disk. What is enforced is that no scored
  verdict is derivable early and that gates cannot be edited afterward.
- One window over a handful of decisions has modest power regardless of
  machinery. A pass is evidence worth acting on, not proof.
- Adjusted closes remain research marks, not executable fills.
