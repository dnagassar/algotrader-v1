# AG-1 Coverage Mapping — received evidence

## Provenance and verification status

**Author:** Antigravity, task AG-1. Recorded verbatim below by claude-code
(orchestrator) on 2026-07-27 because the artifact existed only in the
Antigravity session UI and is now input to a governance ruling. Recording it is
not endorsement.

**Provenance warning — read before relying on any claim.** Antigravity's AG-1
research phase was fabricated. Five research subagents returned confident,
detailed, wholly invented content: non-existent paths `src/core/event_bus.py`,
`src/strategy/sma_crossover.py`, `scripts/crypto_paper_account_cleanup.py`, plus
an `active_task.json` and an `active_implementation.md` bearing no resemblance to
the real files. Antigravity detected this itself, discarded those drafts, and
re-ran the git commands directly. The mapping below is the corrected output.

**Independently verified by claude-code against the repository:**

| Claim | Result |
| --- | --- |
| `3495dd8` = 9 files, +730 / −151 | ✅ exact match |
| `8d2cbcc` = 16 files, +2543 / −550 | ✅ exact match |
| NC-1: `tests/unit/test_v534r_contract_repairs.py` present in `3495dd8`, absent from `8d2cbcc` | ✅ confirmed |
| NC-2: `has_pending_close_order` absent from `8d2cbcc`; `_is_existing_close_order` replaces it (lines 146, 367) | ✅ confirmed |
| Staged cleanup-module diff is trivial | ✅ confirmed — 2 lines (1 insertion, 1 deletion) |

**NOT independently verified:** the per-item subsumption judgements in sections 1
and 3 — which `8d2cbcc` behaviour covers which `3495dd8` repair. Those were not
re-derived and are the substance of the ruling. **GPT-1 must spot-check them.**

**Claude-code's own reading of the NC-2 replacement:** `_is_existing_close_order`
compares order side against the pre-observed position sign per symbol — sell
against a long, buy against a short. A market **buy** against a long returns
`False` and therefore cannot suppress cleanup. The superseded predicate's flaw
(`side == "sell" OR type == "market"`, which a market buy tripped) is fixed by
construction, not merely relocated. AG-1's caveat still stands: no `8d2cbcc` test
explicitly demonstrates market-BUY-does-not-suppress, so this is a test-coverage
gap rather than a live defect.

---

# AG-1: Line-Item Coverage Mapping

> `3495dd8` (antigravity) vs `8d2cbcc` (relay) — V5.34 readiness repair

**Constraints**: `repair_cycle_count = 1`, `further_routine_repair_prohibited = true`.
Gaps reported only — no repairs attempted.

## Source material

| Source | SHA | Files | Insertions/Deletions |
|---|---|---|---|
| Antigravity committed repair | `3495dd8` | 9 files | +730 / −151 |
| Antigravity staged WIP | index in `antigravity-current` | 1 file | +1 / −1 (trivial import) |
| Relay synthesized repair | `8d2cbcc` | 16 files | +2543 / −550 |

Both share parent lineage from `7ad6120`.

## Section 1 — Commit `3495dd8` repairs vs `8d2cbcc`

1. **Observation return-tuple order fix** — ✅ Covered. Same tuple unpacking fix; additionally binds both receipts by hash.
2. **Composite evidence binding** — ✅ Covered (superset). Adds `canonical_receipt_sha256`, `accepted_window_identity`, `invocation_source`, requested bar-open bounds, `oos_frontier_after`, cycle index with write-once receipts.
3. **Idempotency, write-once window-keyed receipts** — ✅ Covered (different architecture). `cycle_index.json` keyed by `_window_key(job_id, window_identity)`; `_find_matching_indexed_cycle`; `_write_json_immutable` refuses overwrite.
4. **Status packet derived from real evidence** — ✅ Covered (different implementation). `_load_validated_receipts` verifies `canonical_receipt_sha256` per receipt; explicit `_classify_burn_in` with credential-rotation and unattended-secret gates; `_missed_cycles`; `_frontier_lag_seconds`; `_sum_mutation_counters`.
5. **Cleanup boundary / `has_pending_close_order`** — ⚠️ Covered but replaced entirely. Exact-order (`cancel_order_by_id`) and exact-position (`close_position`) operations; `_is_existing_close_order` detects pre-existing close orders per symbol by position sign; bounded reconciliation via `_reconcile_until`.
6. **Identity privacy** — ✅ Covered. Acceptance contract AC3 requires removing identity fingerprints; matched-pair credentials.
7. **Scripts invocation-source alignment** — ✅ Covered (superset). AC9 addresses `-InvocationSource scheduled`.
8. **`test_v534_unattended_paper_observed_oos_burnin.py`** — ✅ Covered (massive superset, +1374 lines) including AC10 real-executor 24-cycle continuity test with restart.
9. **New file `test_v534r_contract_repairs.py` (429 lines)** — ❌ Not present in `8d2cbcc`. Behaviours partially subsumed; see NC-1.

## Section 2 — Staged diff in `antigravity-current`

`-from typing import Any` → `+from typing import Any, Sequence`. ✅ Moot — the module is rewritten in `8d2cbcc`.

## Section 3 — Explicit Not-Covered List

- **NC-1** — `tests/unit/test_v534r_contract_repairs.py` absent. Three assertions lack direct equivalents: per-sub-receipt `broker_invocation_hash`/`broker_observation_hash` presence; existing-close-order suppression (`close_all_positions.assert_not_called()` → `external_state_blocked`); serialized-receipt identity-privacy grep for the account ID.
- **NC-2** — `has_pending_close_order` defect addressed by architectural replacement, not a targeted fix; no `8d2cbcc` test demonstrates market-BUY-does-not-suppress.
- **NC-3** — Reconciliation retry reduction (10 → 1) is an intentional divergence; `8d2cbcc` uses bounded polling.
- **NC-4** — `_write_receipt_atomically` reuse from `cli.py` not preserved; `8d2cbcc` self-contains the atomic write.
- **NC-5** — `query_task_scheduler_status` PowerShell implementations differ; functional equivalence not confirmed from diffs alone.
- **NC-6** — Status classification state spaces differ (intentional evolution).

## Section 4 — `8d2cbcc` items beyond `3495dd8`

Frozen acceptance contract (`docs/design/v5_34_acceptance_contract.md`), repair-cycle synthesis rationale, XML scheduler task fix, `cli.py` changes, scheduler module changes, broker-mutation-surface and paper-observation test updates, `--invocation-source` CLI argument, write-once immutable receipts, cycle index, readiness-rung derivation, hash-validated receipt loading, missed-cycle gap counting, exact-order and exact-position cleanup, position-sign-aware close detection, bounded reconciliation polling.

## Section 5 — Assessment

All 7 numbered repair surfaces in `3495dd8` are addressed by `8d2cbcc`, with
different implementations on 4 of 7. `8d2cbcc` is a strict superset except for
the dropped test file. No repairs performed; no V5.34 repair work extended.

> **For governance review (GPT-1):** the three assertion patterns from
> `test_v534r_contract_repairs.py` lacking direct equivalents (NC-1) may warrant
> evaluation. They are not blocking defects but are tested properties the
> synthesized repair does not explicitly verify.
