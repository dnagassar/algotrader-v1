# Codex Operating Context

## 1. Project Goal

This project is a deterministic, offline-safe algorithmic trading system for
personal use.

Longer term, it may support equities, crypto, and options. The near-term
priority remains research, validation, backtesting preparation, and safe
deterministic contracts before any new trading behavior.

## 2. Core Safety Rules

- Deterministic core first.
- Normal `python -m pytest` must remain offline, credential-free, and safe.
- Broker and Alpaca behavior must remain isolated behind explicit adapters or
  wrappers.
- Paper and live integration tests must be skipped by default.
- LLMs may support research, narration, journaling, and analysis only.
- LLMs must never be in the trading hot path.
- No live trading behavior is allowed unless explicitly scoped in a later
  phase.

## 3. Current Architecture Summary

The intended deterministic pipeline is:

```text
Market Data -> Features -> Screener -> Signals -> Risk -> ExecutionIntent -> ExecutionPlan -> PlanningPolicy -> future OMS/Broker -> Fills/Portfolio/Reconciliation
```

Current implemented boundaries are still intentionally conservative. Screener,
signal, risk, execution-intent, execution-plan, and planning-policy contracts
exist in narrow deterministic slices. Broker-facing and runtime behavior remain
isolated, and no research output is allowed to become trading behavior without
explicit validated contracts and tests.

## 4. Current Strategy And Evidence Lanes

- SPY daily long-only SMA 50/200 remains the initial paper-lab lane.
- Crypto tournament v1 is closed and cannot be reopened or reused for rescue
  tuning.
- Crypto tournament v2 is the primary research-to-paper lane. Its universe is
  frozen to BTCUSD, ETHUSD, and SOLUSD with a new untouched OOS window and
  separate fingerprint.
- V5.25 owns calendar-bound forward-shadow evidence, V5.26 owns the frozen
  review decision, and V5.27 owns candidate-deferred operational capability
  production and pinned replay.
- Strategy rankings, fixtures, safety certifications, and orchestration
  receipts are not return evidence. Only sealed untouched OOS/shadow outcomes
  can change the strategy classification.

## 5. Phase Granularity Policy

Going forward:

- Docs, research, and planning phases may combine related documentation updates
  when the work is low-risk and no production code changes.
- Production source changes must remain narrow, test-first, explicitly scoped,
  and heavily verified.
- Any phase that adds behavior, evaluator logic, broker behavior, runtime
  behavior, persistence, or trading-path behavior must remain small and
  separately reviewed.
- Hardening phases should be used when risk justifies them, not automatically
  after every documentation phase.
- Prefer fewer, higher-quality research/design phases over many tiny doc-only
  phases.

## 6. Codex Prompt Compression Policy

Future Codex prompts should reference this file instead of repeating the full
project history.

A normal future Codex prompt should include only:

- phase name
- goal
- files to read first
- allowed files
- forbidden behavior
- required verification
- expected report format

## 7. Standard Files To Read First

Future Codex sessions should usually start with:

- `AGENTS.md`
- `docs/deterministic_core.md`
- `docs/agent_context/codex_operating_context.md`
- `docs/agent_context/active_implementation.md`
- relevant phase or design docs only

`docs/project_checkpoint.md` is a non-authoritative historical ledger. Avoid
reading every historical design document unless the current phase depends on
that older context.

## 8. Standard Hard Gates

- Do not load or expose broker credentials during development or default tests.
- Do not perform a broker/network read without the exact scoped operator command
  and authorization required by the runbook.
- Do not submit, cancel, replace, close, liquidate, or otherwise mutate paper
  state without exact operation-specific operator authorization.
- Do not add or use live credentials/endpoints, allocate capital, or trade live.
- Do not weaken frozen strategy fingerprints, untouched windows, source
  provenance, dependency direction, or offline-default tests.
- Keep LLMs and agents outside the trading hot path.
- Scope deterministic strategy, persistence, scheduler, or broker-adapter work
  narrowly and preserve explicit safety wrappers and operator gates.

## 9. Standard Verification Commands

Use these commands unless the phase gives a narrower or broader verification
set:

```powershell
python -m pytest
git diff --name-only HEAD -- src
git diff --check
git status
```

For documentation-only phases, `git diff --name-only HEAD -- src` should return
no production source files. If full pytest is deferred, the final report must
state that clearly and preserve the latest known full-suite checkpoint.

## 10. Current Crypto Tournament V2 Operational Baseline

V5.28 is the current delegated implementation slice. It builds on V5.27's
source-bound capability production and pinned replay with exact target-scoped
read-only visibility for BTCUSD, ETHUSD, and SOLUSD. Every output remains
no-submit, no-paper-mutation, no-capital, and no-live-authority.

A nonempty target must be an exact frozen symbol and is validated before client
construction or broker reads. It becomes the supervisor's sole preference, with
no fallback when absent. Runtime receipts expose the target and scope; V5.27
normalization and the sealed review require an exact target/selected-symbol/
winner match for operational venue eligibility.

Lifecycle admission still requires V5.8 zero fill and empty residual state, the
exact canonical V5.9 packet/manifest and operator phrase, positive cross-bound
V5.10 entry and exit fills, and a flat observation no earlier than the exit
order's broker-reported `filled_at`.

The verified real offline classification remains
`candidate_deferred_pending_terminal_winner`: V5.25 has not sealed an accepted
winner, so no subject-bound capability bundle may be emitted. The next evidence
dependency is winner-specific lifecycle and independent-flat evidence,
especially if ETHUSD or SOLUSD wins because the legacy chain is BTCUSD-only.
New LLM APIs, retrieval services, QuantConnect, or additional strategy
tournaments are not the principal constraint.

Read `docs/design/v5_27_crypto_tournament_v2_capability_production_and_replay.md`
and
`docs/design/v5_28_crypto_target_scoped_read_only_venue_visibility.md` before
changing this path. Preserve the exact V5.26 preregistration and V5.27
safety-policy fingerprints, the untouched OOS/shadow calendar, immutable
source provenance, account binding, and all operator gates.
