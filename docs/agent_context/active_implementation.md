# Active Implementation Checkpoint

## Current Slice — V5.25 Tournament V2 Forward-Shadow State

- Execution span: `2026-07-15` through `2026-07-16`, America/New_York.
- Branch: `codex/crypto-frozen-state-reset-workflow`.
- Parent HEAD: `dd12290c83bb7d7c071f1d81f4fc23e24eb63690`
  (`Preregister crypto winner forward shadow`).
- Exactly one implementation writer owned the checkout. Read-only reviewers
  inspected state and intake semantics.
- Protected operator-owned files were not edited, staged, or committed.

## Verified Baseline

- Tournament v1 remains terminal and closed. No v1 candidate, OOS result, or
  ADA rescue tuning was reused.
- Tournament v2 remains the frozen BTCUSD/ETHUSD/SOLUSD lane under
  preregistration fingerprint
  `2ed9489543d8d21ab00d9f2f4000927b8012decf39882cb721cb2d1ce0b9376b`.
- The current generated v2 state remains unchanged at fingerprint
  `78bbfba22e75fabbe0570571a81436bf686448ceb0b7e23a2b0c5e1fa4bb7371`:
  72 embargo rows, zero OOS rows, no terminal outcome, no candidate metrics,
  no ranking, and no selected candidate.
- No forward-shadow frozen state exists, which is correct before one sealed
  eligible v2 terminal winner.
- The V5.24 candidate-agnostic forward-shadow contract remains locked under
  fingerprint
  `7ff152e69bd00eb8da9376d1f2be15194fbd04ed6a420151e30c3c46bec82436`.

## Capability Implemented And Proven

V5.25 implements the selected-winner no-submit forward shadow without changing
the V5.24 fingerprint or thresholds.

- Activation validation now binds the source state fingerprint, rejects source
  broker-read activity, and requires real terminal scoring for an eligible
  winner.
- The public tournament boundary exports exactly 169 validated, normalized,
  selected-symbol context bars ending on the raw OOS boundary.
- Initialization remains dormant before a winner. After one winner, it freezes
  the activation, byte-bound terminal source, exact manifest candidate, context,
  fixed 168-hour window, checkpoints, artifact hashes, and state fingerprint.
- Delayed activation hours are receipt-bound signal warmup only and are never
  scored.
- Raw, normalized, and decision evidence is monotonic. A committed prefix ends
  on a raw bar; missing trailing data cannot create decisions or checkpoints;
  one proven interior gap is imputed once with prior-target hold; excessive gaps
  stop the prefix; backfill of a committed imputation and conflicting rewrites
  fail closed.
- Mutable evidence generations are serialized and journaled. Staged SHA-256
  identities and the prior state fingerprint are verified, frozen state is
  published last, interrupted publication is completed before the next load,
  and only hash-matching pending files are cleaned. Status preserves the exact
  persisted state identity, and initialization cannot mint one without writing
  it.
- Causal returns reuse the tournament-v2 one-bar-lag engine, 40/80 bps costs,
  cash and same-symbol buy-and-hold benchmarks, and no forced terminal
  liquidation.
- Hour 24 and 72 checkpoints cannot promote, stop, extend, or mutate the
  strategy. Hour 168 seals either evidence for bounded-paper-probe review or a
  terminal input-quality gate. Sealed state rejects later deltas and rescoring.
- A separate operating bridge auto-initializes when appropriate and derives
  exactly one symbol and exact inclusive completed-hour window from frozen
  state. It requires both explicit market-data switches, performs a non-writing
  preparation read, validates returned and on-disk receipts plus output hashes,
  and preserves state on failure.
- A distinct process lock spans the full network-capable status, fetch, receipt,
  and accrual cycle. Overlap fails before a second adapter call, and UNC output
  roots fail before a lock file or network filesystem can be touched.
- The original V5.24 readiness wrapper remains offline and unchanged. The new
  operating wrapper exposes no symbol, submit, mutation, broker-read, account,
  or live option.

## Classification And Strategic Trajectory

- Task classification:
  `material_end_to_end_research_autonomy_and_future_evidence_pipeline`.
- Autonomy impact: materially positive. After selection, the system can
  initialize, request only the missing selected-symbol data, accrue causal
  evidence, checkpoint, and seal terminal evidence without routine management.
- Decision-evidence impact today: none yet. The candidate and all 168 future
  observations do not exist until tournament v2 closes and the future calendar
  window elapses. V5.25 prevents delay and gate drift; it does not manufacture
  alpha evidence.
- Safety/orchestration balance: this is targeted infrastructure directly tied
  to future evidence, not another general framework. It closes the previously
  identified post-selection implementation gap.
- New Claude, Antigravity, QuantConnect, retrieval, OMS, or broker APIs do not
  remove the principal bottleneck. The missing input is untouched causal market
  evidence under the already frozen strategy family.
- Live-capital readiness remains false. No current evidence supports even a
  bounded paper probe, and no paper result supports a live test.

## Unresolved Risks And Hard Gates

- Tournament v2 can still close with no winner or at its input-quality gate.
  It must not be rescue-tuned, endpoint-extended, or re-fingerprinted.
- Future tournament and shadow data remain exposed to gaps, low volume,
  benchmark underperformance, cost sensitivity, drawdown, concentration, and
  insufficient transition/round-trip evidence.
- The locked shadow coverage threshold is `0.995`; one missing hour over 168 is
  `0.99404762` and therefore terminally disqualifying.
- A successful shadow permits review only. A crypto-specific bounded paper
  probe admission packet, explicit maximum notional/loss budget, venue-specific
  order constraints, reconciliation acceptance, kill/rollback evidence, and a
  later live-readiness review remain to be implemented and proven.
- Paper mutation still requires exact operator authorization for the exact
  operation. Credentials are not present in the development shell. Capital
  allocation, live credentials/endpoints, and live trading remain hard operator
  gates.

## Safety And Verification Receipt

- Preflight found `APP_PROFILE=paper` false and all checked Alpaca credential
  aliases absent; values were never printed.
- No network request, market-data fetch, broker/account read, broker mutation,
  submit, cancel, replace, close, liquidation, paper mutation, live endpoint, or
  capital action occurred in this slice.
- Final focused forward-shadow plus dependency-direction matrix: 80 passed in
  21.15s.
- Required offline verifier: 97 passed in 88.29s; `PASS`.
- Default full verifier canonical collection: 9,054 nodes across 456 files.
- Four-worker execution was terminated simultaneously by Windows status
  `0x40010004` after collection equivalence passed; no test failure was
  reported. This was resolved without changing code by using one bounded
  worker.
- Authoritative one-worker exact-node run: collection and execution equivalence
  passed; 9,054 executed, 9,050 passed, 4 skipped, 0 failures, 0 errors;
  `bounded_full_suite=PASS`.
- `git diff --check`: passed before this handoff update and must be repeated
  after it.
- No tracked `runs/` artifact was created.

## Files Owned By This Slice

- `src/algotrader/research/crypto_tournament_v2_forward_oos.py`
- `src/algotrader/research/crypto_tournament_v2_forward_shadow.py`
- `src/algotrader/research/crypto_tournament_v2_forward_shadow_state.py`
- `src/algotrader/orchestration/crypto_tournament_v2_forward_shadow.py`
- `scripts/run_crypto_tournament_v2_forward_shadow_cycle.ps1`
- `tests/unit/test_crypto_tournament_v2_forward_shadow.py`
- `tests/unit/test_crypto_tournament_v2_forward_shadow_state.py`
- `tests/unit/test_run_crypto_tournament_v2_forward_shadow_cycle_script.py`
- `docs/design/v5_25_crypto_tournament_v2_forward_shadow_state.md`
- `docs/deterministic_core.md`
- `docs/OPERATOR_RUNBOOK.md`
- `docs/agent_context/active_implementation.md`

## Protected Dirty Work

- Preserve `docs/project_checkpoint.md` as unrelated modified operator work at
  SHA-256
  `4FB473115578E2F25B353F50C409CD7566932ED5CC609DDDF19F7D6B9C34AF17`.
- Preserve `docs/design/v5_20_3_crypto_frozen_state_reset_baseline.md` as
  unrelated untracked operator work at SHA-256
  `602304A0D55369573B2AF4147850C7271EE518EB097D4AD86DB05D6FD50B4900`.
- Do not reset, clean, stash, restore, rebase, switch branches, stage, or commit
  either file without explicit ownership transfer.

## Already-Selected Next Action

Continue tournament-v2 receipt-bound OOS accrual through the existing isolated
paper market-data command whenever an exact read-only refresh is authorized;
that operation is independent of offline development and requires the loaded
paper shell documented in the runbook.

The next implementation milestone is a candidate-agnostic, default-denied
crypto bounded-paper-probe review and admission contract that remains dormant
until V5.25 seals `evidence_complete_for_bounded_paper_probe_review`. It should
bind the terminal shadow identity and metrics, define an immutable very-small
notional and maximum-loss envelope, require venue/order/reconciliation/kill
evidence, and emit only a review/admission artifact. It must not load
credentials, contact a broker, mutate the paper account, allocate capital, or
authorize live trading. This removes downstream design delay while the calendar
evidence accrues and is the highest-leverage delegated step toward an eventual
explicitly authorized small-capital live test.
