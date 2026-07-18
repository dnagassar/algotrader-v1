# Active Implementation Checkpoint

## Current Baseline — V5.30 Bounded Crypto Paper-Probe Lifecycle Complete And Verified

- Checkpoint date: `2026-07-18`, America/New_York.
- Branch: `antigravity/v5.30-bounded-paper-probe-lifecycle`.
- Current committed HEAD: `731eff8aa3ef38952bd0b1cf78aadab188720a3b`
  (`Finalize V5.30 implementation handoff`).
- Sole implementation writer: Antigravity.
- The V5.30 digest-binding repair is complete, locally verified, and passes the
  canonical full offline verifier. The final repair commit hash is supplied in the
  final closeout report; the branch remains verified at pre-commit.
- Independent review status: pending re-review
- Push status: not pushed
- Exactly one implementation writer may continue this checkout. Inspect branch,
  HEAD, status, staged and unstaged diffs before editing. Do not reset, clean,
  stash, restore, rebase, or switch branches during takeover.

## Implemented Contract

V5.30 now supplies a complete, dormant-before-winner paper lifecycle and target
evidence path without weakening any live, capital, credential, or broker gate.

- The offline planner exports or verifies the complete current V5.25 terminal
  mapping, pins the exact selected winner, and binds target venue evidence,
  frozen safety evidence, expected paper-account identity, deterministic IDs,
  a 15-minute entry window, and the runtime source bundle. Before an accepted
  terminal winner it remains dormant and reads no environment, credentials, or
  broker state.
- The exact lifecycle operator uses durable one-shot submit and cancel
  coordination. Its fixed envelope is one USD 10 crypto market/GTC entry, one
  exact filled-quantity market/GTC risk-reducing exit, at most one entry, one
  exit, and one cancel attempt total, and zero replacement, close, or
  liquidation attempts.
- Direct lookup, all-orders fallback lookup, durable observation, account-wide
  cancel snapshots, final receipts, and target capability normalization bind
  exact client and broker identity plus symbol, side, crypto asset class,
  market type, GTC time in force, no limit price, and exact quantity/notional
  shape. Fully re-fingerprinted semantic drift still fails closed.
- Broker-response loss and lookup ambiguity converge through durable state and
  cannot resubmit. An open entry can only be observed or canceled through the
  same plan, grant, journal, safety state, and deterministic IDs.
- The credential-bearing lifecycle shell accepts an exact grant only from the
  fixed operator-owned `%LOCALAPPDATA%\algo_trader\operator_grants` root. It
  rejects repository paths, planner request artifacts, reparse points across
  the complete path, non-regular/empty/oversized/non-UTF-8 input, and delivers
  grant text only over stdin.
- Both credential-bearing Python wrappers resolve an absolute registered,
  validly signed Python Software Foundation interpreter, run it with `-I`, and
  remove Python startup-injection variables from the child environment.
- The closeout wrapper uses the already-running trusted PowerShell executable,
  performs the independent flat read first, scrubs every credential, profile,
  account, endpoint, network-test, and Python-startup variable, then runs target
  capability production, sealed review, and pinned replay.
- Target capability production accepts only the complete target evidence
  family. Partial, mixed, extra, or legacy-fallback layouts fail closed. Legacy
  production remains explicitly selectable and the frozen legacy producer bytes
  remain unchanged.
- Pinned terminal evidence is compared with a newly exported canonical terminal
  mapping, ignoring only `as_of`; winner, metrics, progress, quality, safety, or
  source drift is rejected.
- V5.29 flat collection now requires a regular non-reparse, at-most-1-MiB,
  strict-UTF-8, duplicate-free canonical target lifecycle receipt and validates
  the complete V5.30 success contract before client construction. Account block
  fields are exact booleans, account binding is exact, open-order truncation
  fails closed, and trusted read-completion time cannot regress.

## Verification Evidence

Credential/profile preflight remained safe:

- `APP_PROFILE=paper`: false.
- `ALPACA_API_KEY`, `ALPACA_API_SECRET_KEY`, `ALPACA_SECRET_KEY`,
  `APCA_API_KEY_ID`, and `APCA_API_SECRET_KEY`: absent.
- Network-test switches: false/absent.
- No credential value was printed.

Focused evidence from this exact working tree:

- Lifecycle operator and adversarial order-shape matrix: `62 passed`.
- Lifecycle shell trusted-grant/interpreter matrix: `26 passed`.
- Independent-flat operator and hardened wrapper matrix: `40 passed`.
- Closeout trusted-shell/scrub/pointer matrix: `13 passed`.
- Target production, replay, and lifecycle integration: `94 passed`.
- Decisive targeted repair verification: `32 passed` (across `test_crypto_tournament_v2_bounded_paper_probe_capability_producer_v530.py` and `test_crypto_tournament_v2_generation_replay.py`).
- Broader targeted offline safety suite: `298 passed, 1 skipped` (zero failures, zero errors).

Canonical release gate:

- `scripts/verify_offline.ps1 -Full`: PASS.
- Targeted offline safety guards: `98 passed`.
- Full exact-node collection equivalence: PASS for 9,492 tests across 471 files.
- Four shards: 2,373 tests each; every shard exit 0 and no timeout.
- Aggregate: `9,488 passed`, `4 skipped`, zero failures, zero errors.
- Execution equivalence: PASS.
- `git diff --check`: PASS.
- No real network request, market-data fetch, broker/account read, broker
  mutation, submit, cancel, replace, close, liquidation, paper mutation, live
  endpoint, credential loading, or capital action occurred in this slice.

## Current Real Readiness

- Tournament v2 real state remains at 48 of 672 untouched-OOS hours per symbol,
  frontier `2026-07-17T23:00:00Z`, with no metrics, qualified candidate,
  selection, or winner. Its fixed terminal endpoint remains
  `2026-08-13T00:00:00Z`.
- V5.25 remains `waiting_for_tournament_terminal`; no accepted 168-hour shadow
  exists.
- Capability production remains candidate-deferred and sealed review still
  waits for V5.25 terminal evidence.
- No genuine V5.30 terminal/plan/lifecycle/manifest quartet and no genuine V5.29
  independent-flat trio exists.
- Live-capital readiness is false. Paper success evidence, a separate
  live-readiness review, stronger executable attestation, explicit capital
  allocation, live credentials/endpoints, and exact live authorization remain
  hard gates.

## Implementation-Owned Files Awaiting Scoped Staging

- `docs/OPERATOR_RUNBOOK.md`
- `docs/deterministic_core.md`
- `docs/agent_context/active_implementation.md`
- `scripts/build_crypto_tournament_v2_bounded_paper_probe_lifecycle_plan.ps1`
- `scripts/run_crypto_bounded_probe_independent_flat_operator.ps1`
- `scripts/run_crypto_tournament_v2_bounded_paper_probe_closeout.ps1`
- `scripts/run_crypto_tournament_v2_bounded_paper_probe_lifecycle.ps1`
- `scripts/run_crypto_tournament_v2_capability_pipeline.ps1`
- `src/algotrader/certification/crypto_tournament_v2_bounded_paper_probe_generation_replay.py`
- `src/algotrader/core/crypto_bounded_probe_lifecycle.py`
- `src/algotrader/execution/alpaca_client.py`
- `src/algotrader/execution/crypto_bounded_probe_independent_flat_operator.py`
- `src/algotrader/execution/crypto_bounded_probe_independent_flat_reconciliation.py`
- `src/algotrader/execution/crypto_tournament_v2_bounded_paper_probe_lifecycle_operator.py`
- `src/algotrader/orchestration/crypto_tournament_v2_bounded_paper_probe_capability_producer_v530.py`
- `src/algotrader/orchestration/crypto_tournament_v2_bounded_paper_probe_lifecycle.py`
- `src/algotrader/orchestration/crypto_tournament_v2_bounded_paper_probe_review.py`
- `tests/unit/test_broker_mutation_surface_invariant.py`
- `tests/unit/test_build_crypto_tournament_v2_bounded_paper_probe_lifecycle_plan_script.py`
- `tests/unit/test_crypto_bounded_probe_independent_flat_operator.py`
- `tests/unit/test_crypto_bounded_probe_independent_flat_reconciliation.py`
- `tests/unit/test_crypto_tournament_v2_bounded_paper_probe_capability_producer_v530.py`
- `tests/unit/test_crypto_tournament_v2_bounded_paper_probe_lifecycle.py`
- `tests/unit/test_crypto_tournament_v2_bounded_paper_probe_lifecycle_operator.py`
- `tests/unit/test_crypto_tournament_v2_capability_producer.py`
- `tests/unit/test_crypto_tournament_v2_generation_replay.py`
- `tests/unit/test_run_crypto_tournament_v2_bounded_paper_probe_closeout_script.py`
- `tests/unit/test_run_crypto_tournament_v2_bounded_paper_probe_lifecycle_script.py`
- `tests/unit/test_run_crypto_tournament_v2_capability_pipeline_script.py`

## Protected Dirty Work

- Preserve `docs/project_checkpoint.md` exactly as unrelated modified operator
  work. Recorded SHA-256:
  `4FB473115578E2F25B353F50C409CD7566932ED5CC609DDDF19F7D6B9C34AF17`.
- Preserve `docs/design/v5_20_3_crypto_frozen_state_reset_baseline.md` exactly as
  unrelated untracked operator work. Recorded SHA-256:
  `602304A0D55369573B2AF4147850C7271EE518EB097D4AD86DB05D6FD50B4900`.
- Do not edit, stage, commit, reset, clean, stash, restore, rebase, or switch over
  either protected file.
- The frozen legacy producer remains byte-identical at SHA-256
  `31919E9D787C90FA0F5B9444726035F919ED7A57D4BCA378D7BCF0941F7EFABA`.
  Note: The prior recorded `E5B0F1F8501D969BD740A3DD8C7E4B3930D233D734646b613b9aa61dc02c19ef` digest
  did not match the committed legacy-producer bytes (due to CRLF line ending differences).

## Already-Selected Next Action

1. Continue receipt-bound tournament-v2 OOS accrual without early scoring. If a
   genuine winner exists at the fixed endpoint, complete the accepted V5.25
   168-hour shadow, refresh exact winner venue evidence, build the offline plan,
   obtain a separate exact operator grant, run the paper lifecycle, and run
   closeout. Do not cross any live, capital, credential-exposure, or nonexact
   operation gate.
