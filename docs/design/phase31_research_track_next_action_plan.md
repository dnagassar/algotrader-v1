# Phase 31 Research Track Next Action Plan

## 1. Purpose

Phase 31 Step 2 turns the Phase 30 candidate backlog and first source-selection
work into a practical research-track sequence.

This plan is documentation-only. It adds no production code, tests, evaluator
behavior, signal computation, feature computation, strategy logic, broker or
Alpaca behavior, runtime behavior, persistence, live data ingestion, ML, or LLM
trading-path logic.

The goal is to keep research phases broader and more useful while preserving
small, test-first, heavily verified production-code phases.

## 2. Current Research-Track Status

Current status:

- Phase 30 created a research validation evidence standard, candidate review
  template, sourcing plan, initial backlog, and first source-selection decision.
- The first sourcing target is `P30-BL-001`, "Simple scalar threshold indicator
  definition".
- `P30-BL-001` remains unreviewed, unvalidated, not approved, not
  production-ready, and not implementation-ready.
- Backlog entries are intake records only. They are not evidence.
- No candidate artifact has been accepted.
- No `ValidatedResearchArtifact` supports the threshold-style evaluator.
- No `ValidatedSignalDefinition` binds to an accepted artifact.
- No production threshold/config provenance exists.
- Real evaluator implementation remains blocked.

## 3. Recommended Broader Research Phases

Future docs/research phases may combine related documentation work when safe.
Recommended next phases:

1. Phase 31 Step 3: `P30-BL-001` source package collection and summary.
   Collect source/provenance, primary references, mechanical definition details,
   non-claims, and review gaps. This may include research-agent assistance, but
   produces only a source package, not validation.
2. Phase 31 Step 4: source package normalization and pre-review readiness.
   Convert collected material into the Phase 30 review-template shape, identify
   missing evidence, classify claims, and decide whether the package is ready
   for formal review or should remain informational.
3. Phase 31 Step 5: first candidate artifact review.
   Apply the Phase 30 evidence standard and candidate review template to
   `P30-BL-001`. The outcome may be pass, conditional pass with resolved gaps,
   fail, or informational only. A pass still does not implement an evaluator.
4. Phase 31 Step 6: validated signal-definition binding plan.
   If and only if review supports it, plan the exact future binding between a
   reviewed research artifact, input names/types, advisory output semantics,
   threshold/config provenance, assumptions, limitations, and non-claims.
5. Phase 31 Step 7: implementation readiness gate.
   Review whether exact validated research, exact validated signal-definition
   support, threshold/config provenance, implementation scope, and tests are
   all ready. Any production implementation remains a later narrow,
   test-first phase.

These phase labels are non-binding. A later prompt may combine adjacent
docs-only research tasks when the work remains low-risk and code-free.

## 4. Evidence Required Before Reviewing `P30-BL-001`

Before `P30-BL-001` enters formal review, collect an evidence package with:

- source/provenance and primary reference
- artifact title or citation
- author, publisher, or source owner
- date, version, or access date
- source type, such as textbook, paper, docs page, article, or internal note
- mechanical definition of the scalar indicator
- exact input meaning for `indicator_value`, or evidence that the placeholder
  name should change
- expected value type and why `Decimal` is or is not appropriate
- comparator terminology and threshold-condition semantics, if applicable
- threshold/config rationale, if applicable
- method description
- dataset description, window, asset universe, and timeframe when applicable
- explicit "not applicable" notes for dataset fields when the artifact is a
  purely mechanical definition
- assumptions
- limitations
- non-claims, especially no profitability or actionability claim
- reproducibility notes
- no-lookahead or bias-control notes when applicable
- relevance to the threshold-style advisory evaluator
- whether the artifact can support a future `ValidatedSignalDefinition`
- unresolved gaps that must block promotion

Backlog presence, familiarity, model output, and unverified summaries are not
evidence.

## 5. Blockers Before Evaluator Implementation

Real evaluator implementation remains blocked until all of the following are
true:

- `P30-BL-001` or another candidate has a collected source package.
- The candidate has been reviewed against the Phase 30 evidence standard.
- The review result is pass, or conditional pass with all gaps resolved.
- An exact `ValidatedResearchArtifact` exists.
- An exact `ValidatedSignalDefinition` exists and binds to that artifact.
- Threshold/config provenance is explicit and reviewed.
- Implementation scope is explicitly approved.
- Production tests are written or ready to be written.
- The implementation phase remains narrow, test-first, deterministic,
  offline-safe, broker-isolated, and outside the LLM trading hot path.

Until then, the threshold-style advisory evaluator remains viable but
unimplemented.

## 6. Research-Agent Rules

Perplexity, Claude, Gemini, and similar tools may be used as research or review
assistants only.

Allowed uses:

- source discovery
- citation gathering
- summary drafting
- evidence checklist prefill
- contradiction finding
- reviewer-style critique
- question generation for missing evidence
- plain-language explanation of already collected material

Required handling:

- Record which agent was used, when practical.
- Prefer primary sources over agent summaries.
- Keep source links, titles, dates, versions, and access notes.
- Treat agent output as untrusted notes until checked against sources.
- Preserve uncertainty, assumptions, limitations, and non-claims.
- Route every candidate through the project evidence standard and review
  template before promotion.

Forbidden uses:

- defining production evaluator behavior
- selecting production thresholds or config values
- deciding signal direction, score, confidence, ranking, or actionability
- approving a `ValidatedResearchArtifact`
- approving a `ValidatedSignalDefinition`
- approving implementation scope
- bypassing tests
- entering the trading hot path
- accessing broker, account, portfolio, runtime, or live quote state for
  trading decisions
- creating persistence writes or production runtime behavior

Research agents can help find and critique evidence. They cannot authorize
production behavior.

## 7. Non-Evidence Confirmations

- Backlog entries are not evidence.
- Source-selection decisions are not evidence.
- Research-agent summaries are not evidence by themselves.
- Familiar indicators or common trading terms are not evidence by themselves.
- A candidate review template filled with unsupported claims is not evidence.
- Evidence must come from traceable reviewed sources and pass the Phase 30
  evidence standard before promotion is considered.

## 8. Explicitly Out Of Scope

This plan does not add:

- production code
- tests
- real evaluator implementation
- evaluator protocol changes
- signal computation
- feature computation
- strategy logic
- score, direction, confidence, ranking, or actionability
- risk approval
- execution intent creation
- execution-plan mutation
- broker or Alpaca behavior
- order submission
- scheduler or runtime behavior
- persistence writes
- live data ingestion
- network calls from production code
- ML training or inference
- LLM trading-path logic

Normal `python -m pytest` must remain offline, credential-free, deterministic,
and safe.

## 9. Next Prompt Shape

A useful next prompt can reference this plan and request:

```text
Phase 31 Step 3 -- P30-BL-001 Source Package Collection

Read first:
- docs/agent_context/codex_operating_context.md
- docs/design/phase31_research_track_next_action_plan.md
- docs/design/phase30_research_artifact_candidate_backlog.md
- docs/design/phase30_first_research_candidate_source_selection.md

Scope: documentation-only source package.
Forbidden: production code, tests, evaluator behavior, signal computation,
broker/runtime behavior, persistence, ML, and LLM trading-path logic.
Verification: python -m pytest; git diff --name-only HEAD -- src; git diff --check.
```
