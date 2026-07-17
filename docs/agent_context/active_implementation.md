# Active Implementation Checkpoint

## Current Slice — V5.27 Release Closure Ready For Local Commit

- Checkpoint date: `2026-07-17`, America/New_York.
- Branch: `codex/crypto-frozen-state-reset-workflow`.
- Current HEAD: `8345234` (`Implement durable crypto bounded probe safety`).
- The V5.27 capability producer, certifiers, replay validator, wrappers,
  integration tests, and reconciled documentation have passed their final
  offline verification and are staged for the scoped local commit.
- Exactly one implementation writer may continue this checkout. Inspect branch,
  HEAD, status, staged and unstaged diffs before editing. Do not reset, clean,
  stash, restore, rebase, or switch branches during takeover.

## Verified Baseline

- Tournament v1 remains terminal and closed. None of its evidence may be reused
  to rescue or retune tournament v2.
- Tournament v2 remains preregistered for exactly BTCUSD, ETHUSD, and SOLUSD
  under the existing frozen fingerprints and untouched-OOS rules.
- The latest real pipeline observation verified on 2026-07-17 remained
  `candidate_deferred_pending_terminal_winner` with blocker
  `v5_25_terminal_winner_not_available`. No V5.25 terminal winner, ranking, or
  selected subject is available. Recheck current generated state; do not infer
  a calendar outcome from elapsed wall time.
- V5.26 bounded-probe preregistration remains frozen at
  `3b82ebcaf3c80b9c1fbda5797623b2e616dfef0a3ed38d2cc52c0b1d3151efb5`.
- V5.27 bounded-probe safety policy remains frozen at
  `c0abbc047f7bdf01f19d46e06d3824acd980016b4bd992d78dd4994db6d2c407`.
- No real capability bundle or eligible review packet has been emitted. The
  positive tests use synthetic or locally generated canonical fixtures only.

## Capability Implemented In The Current Worktree

V5.27 materially closes the gap between a future terminal strategy winner and
a trustworthy, no-submit operational-capability review.

- `crypto_bounded_probe_safety.py` is a durable, local-only safety kernel with a
  restart-latched USD 2 loss halt; exact USD 10 principal/notional envelope;
  long/cash, one-symbol, one-position, one-open-order, one-entry, one-exit,
  one-cancel, zero-replacement limits; entry expiry; broker-ambiguity denial;
  and risk-reducing cancel/exit behavior while new entries are halted.
- Paper-account identity is domain-separated and normalized without persisting
  raw account identifiers. ACTIVE/unblocked observations and expected-account
  matching are mandatory.
- Independent flat reconciliation requires explicit successful account,
  position, and open-order reads; zero positions and open orders; matching
  account binding; read-only behavior; no mutation; no live endpoint; and exact
  freshness.
- The safety certifier binds the exact local kernel, certifier, and focused-test
  bytes to deterministic passing receipts for BTCUSD, ETHUSD, and SOLUSD.
- The candidate-deferred capability producer resolves canonical local bytes and
  historical lifecycle artifacts before emitting anything. It snapshots raw
  sources only after the entire bundle validates.
- Venue evidence requires exact paper-read identity, selected-symbol uniqueness,
  active/tradable orderability, minimum notional at or below USD 10, positive
  size/trade increments, exact primary-to-broker/runtime cross-binding, exact
  optional increment agreement, exact alternate-minimum agreement, and a
  positive derived minimum no greater than USD 10 when present.
- Lifecycle validation binds V5.6 through V5.10 chronology, manifests, hashes,
  sizes, summaries, labels, account state, authorization fields, one-shot
  attempt counts, V5.8 zero fill and empty residual state, V5.9 canonical packet
  schema and operator phrase, and V5.10 positive entry/exit fills.
- Independent flat evidence must occur after the broker-reported V5.10 exit
  order `filled_at`, not merely after the V5.10 run-start `as_of`. Entry and exit
  submit/fill timestamps must be timezone-aware, ordered, nonfuture, and
  cross-bound to the nested final-order quantities and statuses.
- The canonical V5.9 writer is exercised end to end: its persisted packet and
  manifest bytes are consumed by the public V5.27 producer and linked through
  the downstream V5.10 fixture. This proves actual serialization, artifact
  paths, hashes, sizes, labels, schema, and summary compatibility.
- The sealed V5.26 review independently re-derives venue semantics and verifies
  final-mutation-to-flat ordering from the normalized capability upstreams. It
  rejects unexpected authority-, permission-, credential-, occurrence-,
  performance-, attempt-, and endpoint-shaped fields.
- Immutable capability generations and review publications are replayed from
  pinned bytes with exact fingerprints. Waiting generations remain
  candidate-deferred and do not replace the last qualifying publication.
- Both PowerShell wrappers are offline, local-artifact-only, no-submit,
  no-paper-mutation, no-live, and credential rejecting.

## Current Verification Evidence

Credential-safe preflight on 2026-07-17:

- `APP_PROFILE=paper`: false.
- `ALPACA_API_KEY`, `ALPACA_API_SECRET_KEY`, `ALPACA_SECRET_KEY`,
  `APCA_API_KEY_ID`, and `APCA_API_SECRET_KEY`: absent.
- No credential value was printed.

Final V5.27 release checks from this exact worktree:

- Complete producer/review/replay/wrapper matrix: `160 passed in 214.78s`.
- Dependency direction: `33 passed in 19.27s`.
- `scripts/verify_offline.ps1`: PASS, including `97 passed in 155.32s`.
- Bounded exact-node full suite: collection equivalence PASS for 9,271 tests;
  `9,267 passed`, `4 skipped`, zero failures/errors, execution equivalence PASS.
- The direct monolithic `python -m pytest` attempt exceeded the 15-minute tool
  ceiling without a result; the repository's exact-node bounded runner above is
  the completed full-suite evidence.
- Real local-only pipeline: `candidate_deferred_pending_terminal_winner` with
  blocker `v5_25_terminal_winner_not_available` and every authority field false.
- Final source audit found no remaining lifecycle, canonical V5.9, independent
  review, replay-pinning, or authority-denial defect.
- `git diff --check` passed after documentation reconciliation.
- No network request, market-data fetch, broker/account read, broker mutation,
  submit, cancel, replace, close, liquidation, paper mutation, live endpoint,
  or capital action was executed during this slice.

## Strategic Classification And Trajectory

- Current classification:
  `material_end_to_end_research_to_paper_operational_autonomy`.
- Autonomy impact: materially positive. Once genuine V5.25 terminal evidence
  names a winner, the system can now produce and replay a source-bound
  operational bundle and default-denied review without routine management.
- Strategy-evidence impact: none. No new alpha, untouched OOS, or forward-shadow
  decision evidence was created. The calendar-bound evidence remains the
  principal strategy-selection gate and must not be fabricated or shortened.
- Infrastructure balance: V5.27 is targeted execution-readiness evidence, not
  generic orchestration accumulation. It still does not prove profitability,
  paper performance, or live readiness.
- Adding Claude, Antigravity, QuantConnect, another retrieval source, or another
  external API is not the principal bottleneck. The next leverage comes from
  exact winner-scoped operational observations and paper evidence, not more
  information plumbing.
- Live-capital readiness remains false. A genuine terminal winner, fresh
  target-specific venue and flat observations, successful bounded paper
  evidence, a separate live-readiness review, explicit capital allocation,
  live credentials/endpoints, and exact operator authorization remain required.

## Unresolved Risks And Hard Gates

- Tournament v2 may terminate with no winner or with an input-quality/economic
  rejection. No retuning, window extension, rescue ranking, or fingerprint
  reuse is authorized.
- V5.27 is release-green; only scoped staging and its local commit remain.
- Fresh venue evidence must be exact-winner-scoped. The next implementation
  milestone should add an optional validated `target_symbol` for exactly
  BTCUSD/ETHUSD/SOLUSD to the read-only visibility path, with no symbol fallback
  and validation before any SDK factory or broker read.
- Running a fresh paper broker/account/venue read requires a credential-loaded
  paper shell and exact scoped operator authorization. It is not authorized by
  this checkpoint.
- Any paper submit/cancel/fill/exit mutation requires exact operation-specific
  operator authorization. No paper mutation is currently authorized.
- Live credentials, live endpoints, capital allocation, and any live order are
  hard operator gates. The repository remains paper-only and not live
  authorized.

## Worktree Ownership

Committed at HEAD as part of V5.27:

- `src/algotrader/execution/crypto_bounded_probe_safety.py`
- `tests/unit/test_crypto_bounded_probe_safety.py`

Owned uncommitted implementation/doc slice:

- `src/algotrader/core/paper_account_binding.py`
- `src/algotrader/execution/crypto_bounded_probe_independent_flat_reconciliation.py`
- `src/algotrader/execution/crypto_bounded_probe_safety_certification.py`
- `src/algotrader/orchestration/crypto_tournament_v2_bounded_paper_probe_capability_producer.py`
- `src/algotrader/orchestration/crypto_tournament_v2_bounded_paper_probe_review.py`
- `src/algotrader/certification/__init__.py`
- `src/algotrader/certification/crypto_tournament_v2_bounded_paper_probe_generation_replay.py`
- `scripts/run_crypto_tournament_v2_capability_pipeline.ps1`
- `scripts/replay_crypto_tournament_v2_bounded_paper_probe_review.ps1`
- `tests/unit/test_crypto_bounded_probe_independent_flat_reconciliation.py`
- `tests/unit/test_crypto_bounded_probe_safety_certification.py`
- `tests/unit/test_crypto_tournament_v2_capability_producer.py`
- `tests/unit/test_crypto_tournament_v2_bounded_paper_probe_review.py`
- `tests/unit/test_crypto_tournament_v2_generation_replay.py`
- `tests/unit/test_run_crypto_tournament_v2_capability_pipeline_script.py`
- `tests/unit/test_dependency_direction.py`
- `docs/design/v5_27_crypto_tournament_v2_capability_production_and_replay.md`
- `docs/design/v5_26_crypto_tournament_v2_bounded_paper_probe_review.md`
- `docs/deterministic_core.md`
- `docs/OPERATOR_RUNBOOK.md`
- `docs/agent_context/codex_operating_context.md`
- `docs/agent_context/active_implementation.md`

## Protected Dirty Work

- Preserve `docs/project_checkpoint.md` as unrelated modified operator work at
  SHA-256
  `4FB473115578E2F25B353F50C409CD7566932ED5CC609DDDF19F7D6B9C34AF17`.
- Preserve `docs/design/v5_20_3_crypto_frozen_state_reset_baseline.md` as
  unrelated untracked operator work at SHA-256
  `602304A0D55369573B2AF4147850C7271EE518EB097D4AD86DB05D6FD50B4900`.
- Do not reset, clean, stash, restore, rebase, switch branches, stage, commit,
  or edit either file without explicit ownership transfer.

## Already-Selected Next Action

Stage only the owned V5.27 slice, inspect it, and create one coherent local
commit without pushing.

Then implement V5.28 target-scoped read-only venue visibility:

1. Accept only an
   exact optional target symbol in BTCUSD/ETHUSD/SOLUSD, validate it before any
   client construction/read, use it as the sole preferred symbol with no
   fallback, and thread it through the Python visibility operator and both
   PowerShell wrappers.
2. Keep offline implementation and tests credential-free and broker-free. A
