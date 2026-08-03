# V5.90 forward-shadow infrastructure

This implements Route 2 of the V5.89 alpha-program diagnosis: the only route
that can produce evidence this program has not already contaminated.

## Why this exists

Every scored window in this repository suffers the same defect. The rule was
selected after its history was visible, so a good backtest is partly a record
of our own hindsight. Sixteen families were tested that way and none passed,
but even a pass would have carried that asterisk.

A forward shadow removes the asterisk by construction. A hypothesis is
registered at a known instant, and it is scored only on sessions that did not
exist when it was registered. There is nothing to overfit to, because the data
had not happened yet.

The hard part is not the idea, it is making the discipline survive contact
with a motivated operator six months later. This module therefore enforces
three properties mechanically rather than by convention.

## The three enforced properties

### 1. Gates are cryptographically bound to the registration

The hypothesis statement, universe, benchmark, rule fingerprint, cost
assumption, required observation count, and every terminal threshold are
hashed into a single `registration_fingerprint`. Every subsequent load
recomputes that hash from the stored fields and compares. Editing any gate
after seeing data changes the hash, and the ledger fails closed rather than
scoring against the edited target. Moving the goalposts becomes a loud error
instead of a silent rewrite.

### 2. Backfill is structurally impossible

An observation is admissible only inside

```
registration_date < session <= recorded_at
```

A session on or before the registration date is rejected as backfill, and a
session later than the moment of recording is rejected as a future session.
Sessions must also strictly increase, so a gap cannot later be filled in with
a conveniently chosen day. The first observation begins from a flat book, so
the shadow pays a real entry transition and forgoes any move that occurred
before it existed.

### 3. Peeking early cannot produce a verdict

Before `minimum_observation_sessions` is reached, `evaluate_forward_shadow`
returns an accrual packet that contains no return, Sharpe, drawdown, benchmark
delta, or gate outcome — those keys are absent from the payload, not merely
set to null, and the rendered receipt says only that metrics are withheld.
There is no flag, argument, or override that unlocks them early. The only way
to obtain a verdict is to let the frozen window complete.

This matters because the failure mode is not usually fraud. It is an honest
person checking at week three, seeing red, and quietly deciding the window was
badly chosen.

### Tamper evidence

The ledger is append-only JSONL, hash-chained from the registration
fingerprint: each entry stores the prior entry's hash, and its own hash covers
its full content. Editing a past entry, reordering, or truncating the file
breaks the chain and every later load fails closed. The tests exercise edited,
truncated, and gate-mutated ledgers directly.

## Contract summary

- Policy fingerprint: `62f48951559bbc91193cca0a9d3309e9f06ddf7770ea414d735cc7cc59fefed3`
  (`build_forward_shadow_policy` raises on any drift).
- Schema: `v5_90_forward_shadow_registry_v1`.
- Artifacts per shadow root: `registration.json` (immutable),
  `observations.jsonl` (append-only, chained), `status.json`, `status.md`.
- Accounting mirrors the tournament engines exactly: holdings drift between
  actions, one-way turnover is half the absolute weight change including
  implicit cash, cost is a frozen bps rate, and unallocated weight is
  zero-return cash. Arithmetic is `Decimal` quantized to twelve places so the
  hash chain is stable across platforms.
- Authority: network, credential, broker read/mutation, paper mutation,
  capital allocation, and live are all false in the policy, the registration,
  and every ledger entry. A completed pass routes only to operator review; it
  authorizes neither paper nor live.

## Operating it

```bash
pwsh ./scripts/run_forward_shadow.ps1 -Command policy
```

```bash
pwsh ./scripts/run_forward_shadow.ps1 -Command status -Root runs/forward_shadow/<id> -AsOf 2026-08-10T22:00:00+00:00
```

Registration and observation appending are library calls
(`register_forward_shadow`, `append_forward_shadow_observation`) so that a
strategy adapter supplies the causal target weights and this module owns the
accounting, the temporal envelope, and the chain. The wrapper refuses to run
in any credential-bearing environment.

The intended daily cadence is one `append_forward_shadow_observation` per
completed trading session, using the canonical adjusted-close panel refreshed
by the existing EOD job, with targets computed causally from data through the
prior session.

## What is deliberately not done here

No hypothesis is registered. Choosing what to shadow is an operator decision
with real consequences, and the V5.89 diagnosis is explicit that the most
tempting candidate — the `no_canary_g4_always_offensive` ablation that beat SPY
on return — is outcome-contaminated precisely because we saw its result inside
a scored run. Registering it because it looked good would reintroduce the bias
this infrastructure exists to eliminate.

Registering it as a *forward* hypothesis is legitimate, because the forward
window is untouched. But that is a choice to make deliberately and on the
record, not a side effect of building the tool.

## Honest limitations

- The raw ledger is readable on disk. What is enforced is that no *scored
  verdict* can be derived early and that gates cannot be edited afterward; a
  determined operator can still eyeball equity. The protection is against
  quiet goalpost-shifting, not against curiosity.
- A forward shadow is slow by construction. A 126-session window is roughly
  six months. That is the cost of uncontaminated evidence.
- Statistical power over one window is modest. A pass is evidence worth acting
  on, not proof; the frozen route is operator review, not automatic promotion.
- Adjusted closes remain research marks, not executable fills. Shadow results
  do not model real fills, and no paper or live authority follows from them.
