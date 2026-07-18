# V5.25 Tournament V2 Forward-Shadow State

## Purpose

V5.25 implements the already-preregistered V5.24 single-winner forward shadow.
It removes post-selection workflow delay without changing the V5.24 contract or
its fingerprint:

`7ff152e69bd00eb8da9376d1f2be15194fbd04ed6a420151e30c3c46bec82436`

The implementation remains dormant until tournament v2 seals exactly one
eligible winner. It does not create current strategy evidence while the
tournament is nonterminal, and it cannot authorize a paper probe or live
capital.

## Immutable Activation

Initialization accepts only the public V5.24 activation validator. The frozen
state binds:

- the V5.24 preregistration and activation fingerprints
- the source tournament terminal packet SHA-256, terminal evidence
  fingerprint, state fingerprint, classification, and closure timestamp
- the exact selected candidate and full frozen manifest entry
- exactly 169 normalized selected-symbol causal context bars
- the fixed 168-hour shadow start, exclusive end, and checkpoints at hours 24,
  72, and 168
- every persisted research artifact by SHA-256 and the state itself by a stable
  fingerprint

If terminal closure is delayed beyond the tournament endpoint, the intervening
completed hours are collected as `activation_warmup_only`. They bridge causal
signal and return context but are never scored.

## Monotonic Evidence Accrual

Only the selected symbol, `1Hour`, `us`, and the exact state-requested inclusive
window are accepted. Every delta requires a guarded adapter receipt whose
on-disk JSON matches the returned receipt, whose output SHA-256 matches the
canonical CSV, and whose broker, mutation, submit, live, and credential
exposure fields are false.

Normalized history and hourly decisions are append-only:

- a committed prefix must end on a real raw boundary bar
- a single proven interior missing hour may be filled with prior-close OHLC and
  zero volume; its target holds the prior target and creates no transition
- a current missing trailing hour is never committed as an imputed decision
- more than one consecutive missing hour stops the committed prefix before the
  gap
- every later replay must reproduce all previously committed normalized rows
  and decisions exactly
- a later raw row cannot replace an already committed imputed decision
- exact duplicate bars and receipts are idempotent; conflicting rewrites fail
  closed

Each mutable evidence generation is published under a process-exclusive state
lock through a fingerprinted recovery journal. All staged artifacts are
SHA-256 checked, the prior state fingerprint is compared before publication,
and `frozen_state.json` is replaced last. A later invocation completes a
partially published generation before loading state. Read-only status reports
the persisted state identity, initialization cannot mint a nonpersisted state
identity, and verified staging files are removed after commit or recovery.

The locked minimum raw coverage is `0.995`. Therefore one missing hour in the
168-hour terminal window yields `167/168 = 0.99404762` and closes at the input
quality gate even though deterministic imputation and target-hold semantics are
implemented.

## Causal Hypothetical Accounting

For each scored hour, the prior hour's target is the applied exposure. The
current close may change only the next target. Boundary entry starts from
hypothetical cash, and the existing tournament-v2 return engine applies the
frozen 40 bps base and 80 bps stress transition costs.

Terminal evidence includes base and stress return/drawdown/transition metrics,
completed round trips, turnover, cash, same-symbol buy-and-hold under gross,
base, and stress accounting, excess returns, decision-log completeness, and
input-quality evidence. No forced liquidation is added at hour 168.

Checkpoints are completeness receipts only. They cannot promote, stop, extend,
or change the shadow. At the fixed end, a final receipt through the last hour
seals exactly one of:

- `evidence_complete_for_bounded_paper_probe_review`
- `terminal_shadow_input_quality_gate`

Both are no-submit outcomes. A sealed packet replays by hash and rejects later
deltas or rescoring.

## Operating Bridge

The research module has no execution, orchestration, network, credential,
broker, or account import. A separate orchestration module is the sole bridge
to the existing read-only crypto-bars adapter.

The bridge auto-initializes persisted state after an eligible winner appears,
derives the selected symbol and request window exclusively from frozen state,
and requires both explicit market-data authorization switches. Fetch
preparation is non-mutating. Adapter exceptions and receipt or state-validation
failures report conservatively and preserve the frozen state.

One separate process-exclusive operating-cycle lock spans status, the exact
selected-symbol fetch, receipt validation, and state accrual. A concurrent
network-capable cycle fails closed before invoking the adapter, so shared
refresh artifacts cannot be overwritten by an overlapping generation. The
inner state lock remains independent and protects every local state load and
commit.

The existing V5.24 readiness-only PowerShell command remains unchanged. The new
operating command is:

```powershell
.\scripts\run_crypto_tournament_v2_forward_shadow_cycle.ps1 -Mode status -AsOf <CURRENT_UTC_TIMESTAMP>
```

Only an explicitly authorized isolated paper market-data shell may use
`-Mode market_data_fetch -MarketDataFetchAuthorized -AllowNetwork`.

## Authority Boundary

V5.25 authorizes no broker read, account read, paper mutation, submit, cancel,
replace, close, liquidation, capital allocation, live endpoint, or live trading.
Even successful terminal evidence permits only a later bounded-paper-probe
review under a separate exact operator decision.
