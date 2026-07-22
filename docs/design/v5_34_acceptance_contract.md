# V5.34 Acceptance Contract (Frozen — Repair Cycle 1)

Reconstructed 2026-07-22 on `relay/v5.34-readiness-recovery` from: the intended capability
recorded at `7ad6120` (superseded checkpoint), the accepted baseline `9d40560`, the V5.34 test
surface at base (`tests/unit/test_v534_unattended_paper_observed_oos_burnin.py`, 4 tests /
226 lines), repository safety invariants (`test_broker_mutation_surface_invariant.py`,
provenance and credential-isolation suites), and the frozen Operating Charter (2026-07-22).

This contract is frozen for the single owner-led repair cycle. Criteria may not be added,
removed, or reinterpreted after observing candidate implementations or interim results.

## Intended capability (from `7ad6120`, claims not accepted)

Unattended paper-observed OOS burn-in: an hourly, idempotent, no-submit operating cycle that
binds clean-source provenance → completed-hour OOS accrual → genuine bounded paper observation
→ flat reconciliation → canonical decision (`hold_evidence_incomplete`) → truthful burn-in
status packet, operable via a Windows Scheduled Task wrapper, with a bounded milestone-authorized
paper-account cleanup (Phase A) as the only mutation surface.

## Mandatory acceptance criteria

- **AC1 — Observation result binding.** The production paper-observation result is consumed by
  schema/named contract, not fragile positional unpacking; cycle tests exercise the real adapter
  return contract.
- **AC2 — Clean-source admission ordering.** Exact clean-source provenance is verified before
  scheduler construction, OOS state initialization, market-data access, and broker-client
  construction. A dirty source tree yields exactly one immutable blocked receipt and zero side
  effects, zero network/broker calls.
- **AC3 — Secret and identity privacy.** No identity-derived value (account fingerprint or
  digest) in receipts, logs, stdout, or exceptions; credential presence recorded as booleans
  only; no plaintext secret-loading path, no hard-coded checkout fallback, no secret alias
  duplication; least-privilege child environments preserved (Charter: never weaken credential
  controls to obtain a pass).
- **AC4 — Composite evidence binding.** Burn-in evidence binds exact source commit/tree, window
  bars, provider as-of, market-data and scheduler receipt hashes, OOS frontier and state
  fingerprints, broker receipt hashes, stage counters, readiness, decision, and blocker.
- **AC5 — Same-window idempotency.** Cycle receipts are write-once; a duplicate invocation in
  the same accepted window emits a separate no-op receipt referencing the original by path and
  hash, keyed by exact scheduler job identity and accepted window.
- **AC6 — Truthful status packet.** Burn-in status is derived from hash-validated immutable
  receipts and a real bounded scheduler query; no fabricated healthy defaults; blocked states
  classified truthfully.
- **AC7 — Bounded cleanup mutation surface.** Phase A cleanup mutates only by exact order id
  (`cancel_order_by_id`) and exact symbol (`close_position`), with bounded attempts,
  per-operation classification, read-based reconciliation, duplicate-close prevention, and
  registration in the broker mutation surface invariants. No bulk account-wide mutation.
- **AC8 — No-submit invariant.** Zero order submissions anywhere in V5.34; the broker mutation
  surface invariant suite passes unchanged in intent.
- **AC9 — Scheduler contract alignment.** The Task Scheduler XML, wrapper script, and contract
  test agree on one invocation path (offline-verifiable). Registering or enabling the task is
  **not** part of this repair.
- **AC10 — Deterministic continuity.** A multi-cycle (24) progression test runs the real
  executor with persistent state and restart between invocations, fully offline-deterministic.
- **AC11 — Exact verification.** Focused V5.34 + affected safety suites and
  `.\scripts\verify_offline.ps1 -Full` pass on the exact final commit/tree, with commands, exit
  codes, and counts recorded.

## Explicitly out of scope for this repair cycle

- Any real broker/network observation (separately gated on credentials; recorded as a blocked
  gate if unavailable — not simulated).
- Enabling, registering, or modifying the state of the `crypto-tournament-v2-oos-scheduler`
  scheduled task (its `Ready`→`Disabled` transition remains an unresolved anomaly unless proven
  to block an AC).
- Attribution/reconciliation of the reported SPY paper exposure (cached claim from `7ad6120`,
  not re-observed; Charter §9 work, later milestone).
- Relay lease/takeover test battery (separate capability-coupled work item).
- Any functionality present in a candidate but not required by AC1–AC11 ("do not expand the
  milestone merely because either candidate implemented additional functionality").

## Candidates under comparison

- Antigravity `3495dd8` (+ staged WIP in its worktree, preserved untouched).
- Claude `50cb567` (branch `claude/v5.34r-truthful-burnin-repair`).

Both remain preserved exactly as found; the repair is a selective reproduction onto
`relay/v5.34-readiness-recovery`, not a merge of either history.
