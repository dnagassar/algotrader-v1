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
- Agents may coordinate standing-authorized paper operations only through
  deterministic repository adapters, explicit finite caps, reconciliation, and
  audit boundaries; they must never receive or expose raw credentials.
- LLMs and agents must never be in the trading hot path.
- No live-broker access, live mode, live orders, live trading, or live-capital
  behavior is allowed.

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

## 6. Agent Prompt Compression Policy

Future implementation-agent prompts should reference this file instead of
repeating the full project history. When ChatGPT is used as an operator-facing
coordination bridge, also use
`docs/agent_context/chatgpt_workflow_settings.md`.

A normal implementation prompt should include only:

- phase name
- goal
- files to read first
- allowed files
- forbidden behavior
- required verification
- expected report format

## 7. Standard Files To Read First

Future implementation-agent sessions should usually start with:

- `AGENTS.md`
- `docs/deterministic_core.md`
- `docs/agent_context/codex_operating_context.md`
- `docs/agent_context/active_implementation.md`
- relevant phase or design docs only

ChatGPT coordination sessions should also read
`docs/agent_context/chatgpt_workflow_settings.md`. Agent roles are dynamic;
model names in generated work orders are packet audiences, not fixed authority
roles.

`docs/project_checkpoint.md` is a non-authoritative historical ledger. Avoid
reading every historical design document unless the current phase depends on
that older context.

## 8. Standard Hard Gates

- Default development and tests remain credential-free. For an explicitly scoped
  paper task, any collaborator may cause a trusted provider/adapter to load and
  use paper credentials, but must never request, print, log, persist, return, or
  otherwise expose their values.
- Paper broker/network reads and paper submit/cancel/replace/close/liquidate
  actions are standing-authorized for all collaborators through validated paper
  adapters; no per-operation reapproval is required.
- Paper operations require a proven paper profile/endpoint, explicit positive
  finite quantity/notional caps, deterministic receipts, reconciliation, and a
  complete action audit. Collaborators may define and revise those finite caps.
- Do not add or use live credentials/endpoints, enter live mode, allocate real
  capital, access a live broker, or trade live.
- Do not weaken frozen strategy fingerprints, untouched windows, source
  provenance, dependency direction, offline-default tests, or paper/live
  interlocks.
- Keep LLMs and agents outside the trading hot path.
- Scope deterministic strategy, persistence, scheduler, or broker-adapter work
  narrowly and preserve explicit safety wrappers and the canonical `AGENTS.md`
  gates.

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

## 10. Current Operational Baseline

As of 2026-07-23, `main` includes V5.33.2 clean-source provenance and account
identity canonicalization for the bounded read-only paper observation path.
The path verifies a clean production source before SDK client construction or
network access, binds receipts to source identity, canonicalizes account
identity in memory, persists no raw account identifier, and preserves
stage-specific failure evidence.

This capability remains read-only, target-scoped, and paper-only behind the
repository paper-safety boundary. Current standing paper authority does not
change what this historical path itself implements: it adds no submit, cancel,
replace, close, liquidate, capital, paper-mode-change, or live authority.
Default tests remain offline and broker-free.

Crypto tournament V2 still follows its frozen preregistration, untouched
OOS/forward-shadow calendar, and terminal decision gates. Consult the latest
validated sealed artifacts for accrued counts and classification; do not copy a
dated count into prompts or infer a winner before the fixed gate.

Before changing this path, read the relevant V5.23 through V5.33 design,
architecture, and active-handoff material selected by the current task.
Preserve source provenance, account binding, frozen fingerprints, the
untouched calendar, and every current `AGENTS.md` safety gate.

The current branch, HEAD, status, diffs, and verification results outrank this
compact narrative if they ever disagree.
