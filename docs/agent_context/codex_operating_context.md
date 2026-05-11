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

## 4. Current Signal/Evaluator Stack

The current evaluator-related stack is advisory, deterministic, and bounded:

- `SignalEvaluationResult`: advisory output metadata only.
- `SignalEvaluationInputSnapshot`: deterministic input snapshot/reference
  metadata.
- `NoOpSignalEvaluator`: evaluator-shaped no-op boundary that constructs
  advisory metadata without real signal computation.
- `SignalInputValue`: one explicit observed scalar value with UTC-aware
  timestamp and source traceability.
- `SignalInputBundle`: immutable ordered grouping of `SignalInputValue`
  objects with duplicate-name and lookahead checks.
- `SignalInputBundleCompletenessResult`: metadata-only completeness result.
- `validate_signal_input_bundle_completeness(...)`: pure name-only comparison
  between required snapshot input names and bundle value names.

Phase 29 and Phase 30 gates block any real evaluator implementation until there
is a validated research artifact, a validated signal definition,
threshold/config provenance, explicit implementation scope approval, and tests
written or ready.

The current research-track next action plan is
`docs/design/phase31_research_track_next_action_plan.md`. It keeps
`P30-BL-001` as the first unreviewed sourcing target and confirms that backlog
entries, source-selection decisions, and research-agent summaries are not
evidence by themselves.

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

- `docs/agent_context/codex_operating_context.md`
- `docs/project_checkpoint.md`
- `docs/design/phase31_research_track_next_action_plan.md` for research-track
  planning
- relevant phase or design docs only

Avoid reading every historical design document unless the current phase depends
on that older context.

## 8. Standard Forbidden Behavior

Unless explicitly scoped by the current phase, do not add:

- real evaluator implementation
- signal computation
- feature computation
- strategy logic
- scoring, ranking, direction, or actionability
- risk approval
- execution intent creation
- execution plan mutation
- broker or Alpaca behavior
- order submission
- scheduler or runtime behavior
- persistence writes
- live data ingestion
- network calls
- ML training or inference
- LLM trading-path logic

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
