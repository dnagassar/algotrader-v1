# V5.32 End-to-End Supervised Crypto Readiness Trial

## Purpose

V5.32 provides one durable, reproducible proof that the existing crypto lab can
operate across sequential decisions. It composes the existing deterministic
fixture, supervised router, risk-to-intent, immutable execution-plan, planning
policy, simulation-broker, reconciliation, paper-readiness, and receipt
contracts. It adds no strategy, strategy tuning, retry loop, broker mutation,
capital, or live authority.

The accepted V5.31A scheduler commit
`f9d3a64e02b5e29a01fd26e7bd64891b59a605a3` is the branch dependency until its
PR is merged.

## One-command contract

From a normal credential-free shell:

```powershell
.\scripts\run_crypto_supervised_readiness_trial.ps1
```

The default command runs 24 hourly decisions twice from canonical initial
state. Each operating-cycle call reloads state from disk, so continuity is
tested across a restart boundary rather than retained only in memory. The two
replays must produce identical canonical cycle receipts, final semantic state
hashes, and receipt-chain hashes.

Decision time is one hour after the input cutoff. The newest input timestamp
must equal the completed-hour frontier and remain strictly earlier than the
decision time. This explicitly proves that no forming or future bar is used.

## End-to-end path

Each cycle binds this existing path:

```text
offline fixture CSV and SHA-256
-> completed-bar and provenance validation
-> existing BTCUSD/ETHUSD/SOLUSD strategy candidates
-> supervised router selection
-> immutable ExecutionIntent
-> immutable pre-broker ExecutionPlan
-> risk and max-intents planning gates
-> deterministic simulation observation
-> persisted-state reconciliation
-> no paper submit
-> chained machine-readable cycle receipt
```

Simulation-only fills demonstrate local state transitions; they are not paper
orders. Every cycle records `paper_submit_authorized=false`,
`submit_performed=false`, and `broker_mutation_performed=false`.

## Sequential and scenario evidence

The 24-cycle pattern exercises eligible, hold, blocked, exit, flat, and bad-data
states. The router must continue when one candidate has no trade, restart must
not duplicate a deterministic intent, the frontier must advance exactly one
completed hour, and every invocation records `retry_count=0`.

The same command also emits eight named scenario receipts:

1. eligible candidate with no conflicting exposure;
2. no eligible candidate or hold;
3. open-order or duplicate-intent block;
4. broker unobserved or unavailable block;
5. unexpected unauthorized position or symbol block;
6. restart/idempotency replay;
7. stale or mismatched evidence block;
8. normal no-submit readiness decision.

Generated scenario corruption is confined to isolated ignored `runs/` state
and is explicitly hash-bound as a test injection. Unexpected or mismatched
state must fail reconciliation without a fill or paper action.

## Durable packet

The output root contains:

- `readiness_packet.json`: consolidated branch, provenance, input hashes,
  candidate/router inputs, intent/plan/risk facts, broker-observation status,
  reconciliation, readiness rung, safety booleans, and R4 blockers;
- `cycle_receipts.jsonl`: the canonical SHA-256 receipt chain;
- `scenario_receipts.jsonl`: the eight required machine-readable outcomes;
- `operating_report.md`: the eight human operating questions;
- `manifest.json`: hashes and sizes for every outer evidence artifact.

All runtime evidence remains ignored under `runs/` and is never authority.

## Broker-observed lane

The normal result without inherited credentials is
`blocked_credentials_unavailable`; this does not block R1 acceptance. A later
already-authorized, exact paper-read shell may run:

```powershell
.\scripts\run_crypto_supervised_readiness_trial.ps1 `
  -BrokerObservedReadiness `
  -AllowAlpacaPaperRead
```

The wrapper prints presence booleans only, rejects live profile/endpoints, and
passes through the existing read-only broker-observed lane. It exposes no paper
mutation switch. A successful observation may establish R2 but still performs
no submission.

## Readiness classification

- R0: the underlying components existed before V5.32.
- R1: accepted when the two sequential replays and all eight scenarios pass.
- R2: requires an exact authorized read-only paper observation bound to this
  path.
- R3: requires a separately granted exact bounded paper lifecycle.
- R4: remains a later supervised human decision and is not authorized here.

The packet reports at most three highest-leverage R4 blockers and selects one
next milestone from the weakest evidenced gate.
