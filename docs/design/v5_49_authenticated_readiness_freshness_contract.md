# V5.49 Authenticated Readiness Freshness Contract

## Status And Scope

- Status: **frozen contract, pending independent review. No implementation is
  authorized by this document.**
- Milestone: `V5.49 — authenticated readiness freshness`.
- Base commit: `600bf7285f1d1fd451941a6cf047fa7deb19d5e8` (`origin/main`,
  which carries V5.48 implementation `6d4838b` and evidence `38399df`).
- Predecessor contract:
  `docs/design/v5_48_crypto_readiness_replay_reachability_contract.md`.
- This contract exists because V5.48 closed absent-state reachability but
  deliberately left the `rerun_supervised_readiness_trial` (stale) token
  **structurally bound and dormant**. V5.48's own "Absent Versus Stale
  Reachability Boundary" section requires exactly this follow-on contract
  before staleness may become real.

The purpose of V5.49 is narrow: give the crypto readiness lane a **real,
integrity-bound freshness basis** so that `stale` is an honest observable
state, and so that the already-frozen exact replay argv can genuinely
converge it — without weakening any V5.47/V5.48 determinism, import-purity,
or safety guarantee.

## Problem Statement

Three facts in the current checkout jointly make stale unreachable:

1. `src/algotrader/execution/crypto_supervised_readiness_trial_core.py`
   builds the readiness packet with **no generation timestamp**. The
   readiness lane's `as_of_fields=("generated_at", "as_of")` therefore find
   nothing.
2. `autonomy_supervisor.py` staleness evaluation returns early when the
   resolved `as_of_value` is `""` — no timestamp, no age, no staleness.
3. The readiness `LaneSpec` sets `max_age_hours=0`
   (`autonomy_supervisor.py:346`), and the staleness predicate requires
   `lane.max_age_hours > 0`.

Any one of these alone blocks stale. All three must be addressed together,
or the change is cosmetic.

The hard constraint is that the packet is a **determinism artifact**. It
carries `receipt_chain.final_receipt_hash` and
`receipt_chain.deterministic_replay_chain_hash`, and V5.47 proved the replay
is import-pure and default-path deterministic. A naive wall-clock
`generated_at` written into the hashed payload would destroy replay-hash
equality and invalidate the entire acceptance basis.

V5.49 resolves this by **separating the deterministic evidence core from the
freshness attestation**, and binding them together by hash rather than by
inclusion.

## Frozen Design: Attested Freshness Block

### Packet shape

The readiness packet gains exactly one new top-level key,
`readiness_freshness`, an object with exactly these keys:

```
"readiness_freshness": {
  "algorithm": "sha256_canonical_json",
  "generated_at": "<RFC3339 UTC instant, 'Z'-suffixed, second precision>",
  "clock_source": "injected_explicit" | "cli_system_utc",
  "attests_final_receipt_hash": "<packet.receipt_chain.final_receipt_hash>",
  "attests_deterministic_replay_chain_hash":
      "<packet.receipt_chain.deterministic_replay_chain_hash>",
  "attestation_sha256": "<sha256 over canonical JSON of the five fields above>"
}
```

`attestation_sha256` is computed over the canonical JSON of the object
consisting of exactly `algorithm`, `generated_at`, `clock_source`,
`attests_final_receipt_hash`, and `attests_deterministic_replay_chain_hash`
— the block itself minus `attestation_sha256`. The existing
`_sha256_json` canonical-JSON helper must be reused; no new hashing scheme
may be introduced.

### Why this is integrity-bound and not decorative

- The timestamp is cryptographically bound to the **exact deterministic
  evidence** it attests. A `generated_at` cannot be lifted from one packet
  and pasted onto another without `attests_final_receipt_hash` disagreeing
  with the packet's own `receipt_chain.final_receipt_hash`.
- The attestation covers the timestamp, so a stored `generated_at` cannot be
  edited forward to fake freshness without recomputing
  `attestation_sha256` — which a consumer recomputes and compares.
- The block is **excluded** from every determinism hash, so
  `final_receipt_hash` and `deterministic_replay_chain_hash` remain
  byte-stable across runs at different instants. Replay determinism survives
  intact.

This is deliberately *not* a claim of unforgeable provenance. Anyone able to
write the packet file can recompute a consistent block. The guarantee is
**internal consistency and non-transplantability**, which is exactly what is
needed to stop a stale packet from silently presenting as fresh, and to stop
an unrelated packet's timestamp from being reused. Any implementation report
must state this limitation in these terms and must **not** describe the
field as tamper-proof, signed, or authenticated against an external root of
trust.

### Ordering requirement

`readiness_freshness` must be computed **after** the deterministic core is
final, and inserted without mutating any other key. A test must prove that
removing `readiness_freshness` from a V5.49 packet yields a payload
byte-identical to the corresponding V5.48-era packet core for the same
inputs.

### Mandatory bundle_id exclusion

`_compute_bundle_id` in `crypto_supervised_readiness_trial_core.py` hashes
the **entire packet** minus exactly `artifact_paths`, `artifact_integrity`,
and `bundle_id`. `readiness_freshness` **must** be added to that exclusion
list. This is not optional and is not scope creep — it is the established
pattern for packet keys that are not part of content identity.

Omitting it is a P0 defect, because `bundle_id` is used as a **directory
name** (`generation_dir = generations_dir / bundle_id`). Today the replay is
content-addressed and idempotent: re-running reuses the same generation
directory. A time-varying `bundle_id` combined with the 24-hour auto-refresh
below would create a new generation directory on every run, forever.

A test must prove that two replay runs at different instants produce the
**same** `bundle_id` and reuse the **same** generation directory.

### What this field does and does not attest

The replay is a pure function of fixed constants (`DEFAULT_DECISION_START`,
`DEFAULT_CYCLE_COUNT`, all broker/paper flags false). It has **no
time-varying input**. Two runs a year apart produce byte-identical evidence;
only the attested timestamp differs.

`readiness_freshness` therefore attests **when the deterministic computation
was last re-executed** — a regression canary proving the code still runs and
still classifies `accepted`. It does **not** attest that readiness was
recently confirmed against current market, broker, or account conditions,
because nothing in the replay observes those.

Every implementation report, CLI output line, and status field must use
language consistent with the weaker claim. Wording such as "readiness
confirmed fresh" or "recently verified readiness" is prohibited;
"readiness replay last re-executed at ..." is the required framing. An
implementation that ships the stronger reading is a rejection under the same
false-green standard as V5.37a/V5.38a/V5.42a.

## Clock Injection Contract

### The core stays deterministic

`run_crypto_supervised_readiness_trial` in
`crypto_supervised_readiness_trial_core.py` gains a keyword-only parameter:

```
generated_at: datetime | str | None = None
```

Rules, all mandatory:

- The core **must never call** `datetime.now`, `time.time`,
  `datetime.utcnow`, or any equivalent wall-clock read. A static test must
  prove the core module contains no such call.
- When `generated_at` is provided, it is validated (timezone-aware UTC,
  RFC3339, second precision after normalization) and used verbatim, with
  `clock_source="injected_explicit"`.
- When `generated_at` is `None`, the core **must raise `ValidationError`**
  if `write_artifacts=True`. The core may not invent a timestamp. A packet
  written to disk always carries an explicit attested instant supplied by
  its caller.
- `generated_at` must be rejected if it is not timezone-aware, not UTC, or
  not parseable. Fail-closed, before any artifact write.

### The CLI supplies the instant

`_run_crypto_readiness_replay` in `src/algotrader/cli.py` reads the system
clock exactly once, at handler entry, and passes it down:

- exactly one `datetime.now(UTC)` call, in the handler, not at import time;
- `clock_source="cli_system_utc"`;
- the value is normalized to second precision UTC before use.

A clock read is not a credential read, a network access, a broker access, or
an environment-protection violation. The V5.48 exact-launcher purity proof
(`protected_environment_accesses=[]`, `forbidden_modules_loaded=[]`) must
therefore still pass **unchanged**, and V5.49 must re-run it as evidence
rather than relaxing it.

### Argv stays frozen

`CANONICAL_REPLAY_ARGV` remains exactly `("crypto-readiness-replay",)`.

V5.49 **must not** add any timestamp option, environment variable, or extra
argument to the replay command. The freshness basis advances because the
handler reads the clock at run time, not because the caller passes a value.
This is what preserves the V5.48 executor allowlist, the exact-argv
invariant, and the two-way closure tests without modification.

Adding `--generated-at` or equivalent to the replay CLI is **out of scope
and prohibited**, because it would create an argv surface through which a
falsified freshness basis could be injected by whatever invokes the
executor.

## Supervisor Consumption Contract

### Reading the freshness basis

The readiness `LaneSpec` (`autonomy_supervisor.py:338-360`) is amended:

- `as_of_fields` gains the attested path so the supervisor reads
  `readiness_freshness.generated_at`. The existing resolver in `_staleness`
  uses a **flat top-level lookup** (`if field_name in record`) and
  definitively cannot express a nested path, so extending it is
  **mandatory**, not conditional. Flattening `generated_at` to the packet
  root is **prohibited**: it would reintroduce an unattested field that
  looks authoritative.
- That resolver is **shared by every lane**. The extension must be
  backward-compatible for flat field names, and the implementation must
  prove by regression test that each existing lane's staleness behaviour is
  unchanged — not merely that the crypto lane works. This shared blast
  radius is the main implementation risk in V5.49.
- `max_age_hours` changes from `0` to **`24`**.
- `stale_requires_operator_action` remains **`False`** for this lane, so the
  stale token stays `EXECUTION_AUTO_OFFLINE` and auto-refreshable, matching
  the V5.48 `ActionClass` that is already frozen and allowlisted.

The value `24` is chosen because the replay is fully offline, deterministic,
and cheap, so a daily refresh floor costs nothing and keeps the evidence
recent. It must be a named module constant, not a literal at the call site.

### Verification before trust — fail-closed

Before the supervisor may use `readiness_freshness.generated_at` as an age
basis, it must verify the block. The three outcomes are frozen:

1. **Block absent entirely** (a legacy V5.47/V5.48 packet) → the lane
   normalizes to `STATE_STALE`. Rationale: this is a benign
   version-skew condition, and the remedy — re-running the offline
   deterministic replay — is safe and self-healing. This is the one case
   where auto-refresh is correct.
2. **Block present but structurally invalid, or `attestation_sha256`
   mismatched, or `attests_final_receipt_hash` /
   `attests_deterministic_replay_chain_hash` disagreeing with the packet's
   own `receipt_chain`** → the lane normalizes to `STATE_ATTENTION` and the
   action is `operator_review_readiness_trial`. This is a possible-tampering
   or corruption signal and **must never trigger automatic execution**.
3. **Block present and fully valid** → `generated_at` is the age basis, and
   normal `max_age_hours` staleness applies.

Case 2 must not be collapsed into case 1. An implementation that treats a
mismatched attestation as merely stale, and auto-refreshes it, silently
overwrites the evidence of tampering with a fresh packet — that is exactly
the false-green class this project has repaired three times (V5.37a, V5.38a,
V5.42a) and it is an automatic rejection.

### Reference clock

Age is computed against the supervisor's existing injected `config.as_of`.
V5.49 introduces no new reference clock and must not read wall time in the
supervisor.

`--as-of` is `required=True` on all four autonomy commands, so there is no
hidden default and no silent fallback. But this also means **staleness is
only as truthful as the caller's `--as-of`**: a driver that passes a fixed
or stale timestamp makes the lane permanently fresh and leaves V5.49 as
dormant as V5.48.

The implementation report must therefore state explicitly which driver
supplies `--as-of` in unattended operation and demonstrate that it passes a
real wall-clock instant. If no such driver exists yet, the report must say
so plainly and classify V5.49's stale reachability as **proven on demand but
not yet exercised autonomously** — it must not claim autonomous staleness
that nothing actually triggers.

## Convergence Contract

With the above in place, the stale path becomes genuinely reachable and
must be proven end to end:

1. a valid packet whose attested `generated_at` is older than 24 hours
   relative to the supervisor's `--as-of` normalizes to `stale`;
2. the supervisor emits `rerun_supervised_readiness_trial`;
3. the planner classifies it `EXECUTION_AUTO_OFFLINE` with command
   `python -m algotrader.cli crypto-readiness-replay` and
   `required_operator_inputs=()`, subject to all V5.48 canonical-target
   validation, unchanged;
4. the executor resolves the exact allowlisted argv
   `("crypto-readiness-replay",)`, unchanged;
5. `--apply` runs the replay, which stamps a **new** attested
   `generated_at` from the CLI clock;
6. re-observation at the same `--as-of` sees the lane `nominal`;
7. a second cycle finds `eligible_count=0` — no repeat execution.

Step 6 is the point of the milestone. Step 7 is the anti-thrash guarantee.

## Determinism Preservation Contract

The complete set of packet-level identity values that must remain stable
across instants is: `receipt_chain.final_receipt_hash`,
`receipt_chain.deterministic_replay_chain_hash`, **and `bundle_id`**. Any
implementation that treats the first two as the whole set is incorrect —
see "Mandatory bundle_id exclusion" above.

V5.49 must prove, by test, that:

- two replay runs at **different** injected instants produce **equal**
  `receipt_chain.final_receipt_hash`, equal
  `receipt_chain.deterministic_replay_chain_hash`, and equal `bundle_id`;
- those two runs reuse the **same** generation directory (idempotency
  preserved; no per-run directory growth);
- those same two runs produce **different** `readiness_freshness.generated_at`
  and **different** `readiness_freshness.attestation_sha256`;
- `trial_classification` is `accepted` in both;
- a V5.49 packet with `readiness_freshness` removed is byte-identical to the
  V5.48-era core for the same inputs;
- the packet self-verification path (`manifest_bundle_id_mismatch`,
  `bundle_id_mismatch`, `packet_manifest_mismatch`) reports no errors for a
  freshly written V5.49 packet.

Any existing test that asserts whole-packet byte equality across runs must be
retargeted at the deterministic core, and the retarget must be visible in the
diff. Deleting such an assertion without replacing it is a rejection.

## Safety And Authority Invariants

Unchanged from V5.48 and re-proven, not assumed:

- No network access, no market-data fetch, no broker connection, no paper
  account access, no live access.
- No credential value read, printed, logged, or persisted; only variable
  names may ever appear.
- No order submit / cancel / replace / close / liquidation; no broker or
  paper mutation.
- `live_authorized=false` throughout.
- No LLM and no agent in the executable hot path; the
  `test_dependency_direction.py` scans, including the synthetic
  evasion negatives, must pass unchanged.
- The only permitted side effect remains deterministic local artifact writes
  under `runs/` (git-ignored, untracked).
- The only new capability granted to the hot path is **reading the system
  clock in the CLI handler**. Nothing else.

## Frozen Implementation Scope

Only these files may be touched:

- `src/algotrader/execution/crypto_supervised_readiness_trial_core.py`
  (attested block construction, `generated_at` parameter, validation)
- `src/algotrader/execution/crypto_readiness_replay.py`
  (thread `generated_at` through; no default clock read)
- `src/algotrader/cli.py` (single handler-entry clock read)
- `src/algotrader/execution/autonomy_supervisor.py`
  (LaneSpec `max_age_hours`, nested as-of resolution, attestation
  verification and the three-outcome normalization)
- `tests/unit/test_crypto_readiness_replay.py`
- `tests/unit/test_crypto_supervised_readiness_trial.py`
- `tests/unit/test_autonomy_supervisor.py`
- `tests/unit/test_autonomy_self_refresh_cycle.py`
- `tests/unit/test_dependency_direction.py` (static no-wall-clock-in-core
  scan)
- `docs/design/v5_49_authenticated_readiness_freshness_contract.md`
- `docs/agent_context/active_implementation.md`

`autonomy_next_plan.py` and `autonomy_offline_executor.py` must **not**
change. If the implementation finds it needs to change them, that is a
signal the design is wrong — stop and re-freeze rather than widening scope.

## Tests And Acceptance Criteria

### Attested block
- exact key set and key order-independent canonical hashing;
- `attestation_sha256` recomputation matches;
- non-UTC, naive, unparseable, and sub-second `generated_at` all rejected
  with `ValidationError` before any write;
- `generated_at=None` with `write_artifacts=True` raises.

### Determinism
- the four assertions in "Determinism Preservation Contract" above.

### Supervisor normalization
- absent block → `stale`;
- valid block, age ≤ 24h → `nominal`;
- valid block, age > 24h → `stale`;
- tampered `generated_at` (attestation stale) → `attention_required`;
- transplanted block from a different packet (receipt-hash mismatch) →
  `attention_required`;
- structurally malformed block (missing key, wrong type) →
  `attention_required`;
- each `attention_required` case proves the planner does **not** classify it
  `EXECUTION_AUTO_OFFLINE` and the executor performs **zero** runner calls.

### Purity
- `crypto_supervised_readiness_trial_core.py` contains no wall-clock call
  (static scan, with a synthetic evasion negative);
- exactly one wall-clock call on the replay CLI handler path;
- the V5.48 exact-launcher fresh-process proof
  (`test_exact_central_launcher_is_protected_and_import_pure`) still passes
  with `protected_environment_accesses=[]` and
  `forbidden_modules_loaded=[]`.

### Closure (regression, must be unchanged)
- `set(AUTONOMY_ACTION_CLASSIFICATION) == producer_tokens`;
- `set(AUTONOMY_EXECUTOR_ALLOWLIST) == auto_offline_tokens`;
- both readiness tokens map to exactly `("crypto-readiness-replay",)`.

### Self-refresh truthfulness
- stale → apply → nominal → second cycle `eligible_count=0`;
- a failed child never claims `refreshed` or `converged`;
- dry-run executes nothing and claims no refresh.

## Required Manual Evidence

From a fresh `git worktree add --detach` at the implementation commit, with
presence-only credential/profile preflight confirmed empty before and after,
cwd equal to that worktree root:

1. Seed an accepted packet via the exact launcher; record its
   `readiness_freshness` block and confirm `attestation_sha256` verifies.
2. Observe at an `--as-of` within 24h of `generated_at` → lane `nominal`,
   `eligible_count=0`.
3. Observe at an `--as-of` more than 24h after `generated_at` → lane
   `stale`, exactly one eligible action, argv
   `["crypto-readiness-replay"]`, `execution_count=0` on dry-run.
4. `--apply` at that same far `--as-of` → `execution_count=1`, child exit
   `0`, new `generated_at` stamped, lane re-observes `nominal`.
5. Second cycle at the same `--as-of` → `eligible_count=0`.
6. Hand-edit `generated_at` forward in the packet without fixing
   `attestation_sha256` → lane `attention_required`, `eligible_count=0`,
   zero runner calls, exit non-zero.
7. Copy a valid block onto a packet with a different receipt chain → lane
   `attention_required`, zero runner calls.
8. Delete the block entirely → lane `stale`, auto-refreshable, and one
   `--apply` restores an attested packet.
9. Re-run the exact fresh-process launcher purity proof; record
   `protected_environment_accesses=[]` and `forbidden_modules_loaded=[]`.

Every step must record: exit code, the relevant JSON fields, and the
broker/paper/live safety booleans. Temporary worktrees are removed after
collection; no generated `runs/` artifact is committed.

## Required Verification

- Focused: `test_crypto_readiness_replay.py`,
  `test_crypto_supervised_readiness_trial.py`,
  `test_autonomy_supervisor.py`, `test_autonomy_next_plan.py`,
  `test_autonomy_offline_executor.py`,
  `test_autonomy_self_refresh_cycle.py`.
- `tests/unit/test_dependency_direction.py`.
- `.\scripts\verify_offline.ps1` → PASS with all credential/profile
  booleans false.
- Full `python -m pytest`. Note: this run takes 80+ minutes on the current
  host and approaches tight memory headroom. If it cannot complete, that
  must be reported as a **blocked gate**, not silently omitted.
- `git diff --check` clean; clean tree after commit; no untracked
  `src`/`tests` files.

## Stop Conditions

Stop and report rather than proceeding if:

- the nested as-of resolution cannot be implemented without flattening the
  timestamp to the packet root, or cannot be made backward-compatible for
  the existing flat-field lanes;
- preserving identity-hash equality across instants requires excluding any
  packet key **other than** `readiness_freshness` from `_compute_bundle_id`.
  Adding `readiness_freshness` itself to that exclusion list is **required
  and expected** — it is not a stop condition;
- any change appears necessary in `autonomy_next_plan.py` or
  `autonomy_offline_executor.py`;
- the exact-launcher purity proof regresses;
- the full suite cannot complete on this host.

## Out Of Scope

- Any broker, network, credential, paper, or live capability.
- Any change to `CANONICAL_REPLAY_ARGV` or the executor allowlist.
- Any new CLI option on `crypto-readiness-replay`.
- Cryptographic signing, external timestamp authorities, or any claim of
  provenance beyond internal consistency.
- Enabling staleness on any lane other than
  `crypto_supervised_readiness_trial`.
- Real-capital authorization, which remains a hard operator gate.

## Review Record

### Round 1 — Claude orchestrator, 2026-07-26: REQUEST CHANGES

Reviewed against the checkout at `600bf72`. The core design was upheld:
hash-binding the block to `receipt_chain` while excluding it from identity
hashes, injected clock with no core wall-clock read, frozen
`CANONICAL_REPLAY_ARGV`, and the three-outcome fail-closed split.

Four defects were found and are now corrected in this document:

1. **P1 — incomplete identity-hash enumeration.** The original text named
   only `final_receipt_hash` and `deterministic_replay_chain_hash`, missing
   `_compute_bundle_id`, which hashes the whole packet. Because `bundle_id`
   names a generation directory, this would have broken content-addressed
   idempotency and grown a directory per run under daily refresh. Fixed by
   the mandatory `bundle_id` exclusion section and expanded determinism
   tests.
2. **P1 — overclaiming field name.** The replay has no time-varying input,
   so the field attests re-execution recency, not readiness recency. Fixed
   by the "What this field does and does not attest" section, with required
   wording.
3. **P2 — nested as-of extension understated.** `_staleness` uses a flat
   lookup shared by all lanes; the extension is mandatory and needs
   per-lane regression proof. Fixed.
4. **P3 — no truthful `--as-of` requirement.** Fixed by the reference-clock
   addition requiring the report to name the driver or classify stale
   reachability as not yet autonomously exercised.

The original stop condition would have spuriously halted the correct
`bundle_id` fix; it has been recalibrated.

**Process caveat:** this review was performed by the same agent that
authored the contract. Self-review is a weak control, and finding 2 in
particular is a judgement call about honest framing rather than a
mechanical defect. An independent reviewer should still adjudicate it.

## Next Action

Independent (non-authoring) review of the corrected contract. That review
must adjudicate:

1. whether the freshness field is worth building at all, given that it
   attests only re-execution of a time-invariant computation — the
   alternative being to leave the stale token dormant and honestly
   documented as such;
2. whether the absent-block → `stale` decision is right, or whether version
   skew should also demand operator review;
3. whether `24` hours is the correct floor, given that a shorter interval
   buys nothing when inputs never change;
4. whether a single CLI-handler clock read is an acceptable widening of the
   import-purity envelope established by V5.47/V5.48.

Question 1 is now the gating question. If the answer is "not worth it," the
correct outcome is to close V5.49 without implementation and record the
stale token as permanently dormant by design — which is a legitimate and
cheaper result than building attestation machinery around a constant.

No implementation is authorized until that review records an explicit
verdict.
