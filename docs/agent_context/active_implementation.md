# Active Implementation Checkpoint

## Current Baseline — V5.29 Target-Scoped Independent Flat Collection Complete

- Checkpoint date: `2026-07-17`, America/New_York.
- Branch: `codex/crypto-frozen-state-reset-workflow`.
- Current HEAD: `f3a9bf3` (`Add target-scoped independent flat collection`).
- V5.27 is committed locally as `e56e577` (`Implement crypto capability
  production and replay`).
- V5.28 is committed locally as `380e3c9` (`Add target-scoped crypto venue
  visibility`).
- V5.29 is committed locally as `f3a9bf3` (`Add target-scoped independent
  flat collection`).
- No owned implementation changes remain uncommitted. Only the two protected
  operator-owned files listed below are dirty.
- Exactly one implementation writer may continue this checkout. Inspect branch,
  HEAD, status, staged and unstaged diffs before editing. Do not reset, clean,
  stash, restore, rebase, or switch branches during takeover.

## Verified Baseline

- Tournament v1 remains terminal and closed. None of its evidence may be reused
  to rescue or retune tournament v2.
- Tournament v2 remains preregistered for exactly BTCUSD, ETHUSD, and SOLUSD
  under the existing frozen fingerprints and untouched-OOS rules.
- The real V2 OOS state was refreshed through
  `2026-07-17T23:00:00Z`: 48 of 672 untouched-OOS hours per symbol are sealed,
  candidate metrics remain empty, and the fixed terminal endpoint remains
  `2026-08-13T00:00:00Z`. The V5.25 shadow remains
  `waiting_for_tournament_terminal`; no winner, ranking, or selected subject
  exists. Do not score, retune, or infer a calendar outcome early.
- The latest real capability pipeline remains
  `candidate_deferred_pending_terminal_winner` with blocker
  `v5_25_terminal_winner_not_available`.
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

V5.29 adds the canonical target-scoped independent-flat broker collector.

- Exact BTCUSD, ETHUSD, or SOLUSD and a same-symbol filled-exit lifecycle are
  validated before environment resolution or client construction.
- The command reads only the paper account, all positions, and all open orders;
  no submit, cancel, replace, close, liquidation, or mutation seam exists.
- Success requires exact expected-account matching, an active unblocked account,
  zero account-wide positions, zero account-wide open orders, and a read after
  the broker-reported exit fill.
- Raw account identifiers remain process-local. The sanitized receipt uses the
  domain-separated account binding and its manifest binds exact lifecycle and
  collector source bytes.
- A failed newer read moves an older mutable-latest receipt and manifest intact
  into generated superseded storage so stale evidence cannot remain active.

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
V5.28 verification from the current worktree:

- Combined target-scope and V5.27 consumer regression matrix: `186 passed in 70.22s`.
- `scripts/verify_offline.ps1`: PASS, including `97 passed in 198.74s`.
- Bounded exact-node full suite: collection/execution equivalence PASS;
  `9,279 passed`, `4 skipped`, zero failures/errors across 9,283 tests.
- No network, broker/account read, broker mutation, paper mutation, live
  endpoint, or capital action occurred in the V5.28 tests.

V5.29 verification from this exact worktree:

- Focused flat/operator, capability producer, sealed review, and dependency
  matrix: `181 passed in 24.76s`.
- Default offline verifier: PASS, including `97 passed in 125.02s`.
- Full offline verifier: PASS, including `97 passed in 95.02s`.
- Bounded exact-node full suite: 9,296 tests; `9,292 passed`, `4 skipped`,
  zero failures/errors; collection and execution equivalence PASS.
- One exact isolated read-only market-data GET refreshed BTCUSD, ETHUSD, and
  SOLUSD OOS evidence from `2026-07-16T00:00:00Z` through
  `2026-07-17T23:00:00Z`. Credentials were not exposed; no account read or
  broker/paper mutation occurred.
- All implementation verification was credential-free, network-free,
  broker-free, deterministic, and offline.

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
- Future paper broker/account/venue reads still require a credential-loaded
  isolated paper process and an exact operation scope. V5.29 does not turn the
  completed OOS refresh into standing broker-read authority.
- Any paper submit/cancel/fill/exit mutation requires exact operation-specific
  authorization bound to the selected winner, lifecycle plan, USD 10 envelope,
  account, expiry, and one-shot attempt budgets. No exact bounded lifecycle
  mutation is currently authorized or executable before the terminal winner.
- Live credentials, live endpoints, capital allocation, and any live order are
  hard operator gates. The repository remains paper-only and not live
  authorized.

## Worktree Ownership

The V5.27, V5.28, and V5.29 implementation slices are committed locally. No
owned implementation file is staged, modified, or untracked after the V5.29
commit. Only the mutable handoff is being reconciled for its checkpoint commit.

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

Continue receipt-bound V2 OOS accrual without scoring before
`2026-08-13T00:00:00Z`. The next implementation slice is the dormant exact-
winner bounded lifecycle operator: it must consume a sealed V5.25 winner,
target-scoped venue evidence, the frozen USD 10 V5.27 safety state, exact
account binding, expiry, and one-shot entry/exit/cancel budgets. It must remain
non-executable before the winner and require exact operation authorization at
mutation time.

After a confirmed filled exit, run the committed V5.29 exact-target flat
collector immediately, then source-bound capability production, sealed review,
and pinned replay. Do not add another visibility layer, infer a winner early,
reuse the BTC-only legacy lifecycle for ETHUSD/SOLUSD, or cross any live,
credential-exposure, capital, or nonexact mutation gate.
