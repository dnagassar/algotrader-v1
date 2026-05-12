# Phase 31 Research Track Next Action Plan

## 1. Purpose

Phase 31 Step 2 turns the Phase 30 candidate backlog and first source-selection
work into a practical research-track sequence.

Phase 31 Step 3 adds the normalized `P30-BL-001` source package in
[`phase31_p30_bl_001_source_package.md`](phase31_p30_bl_001_source_package.md).
That package is source normalization only. It is not formal review,
validation, approval, production readiness, or implementation readiness.

Phase 31 Step 4 adds the Tier A formal source review in
[`phase31_p30_bl_001_tier_a_review.md`](phase31_p30_bl_001_tier_a_review.md).
That review conditionally passes Tier A for mechanics and methodology only.
It does not validate `P30-BL-001`, approve a threshold, create a validated
signal definition, or authorize evaluator implementation.

Phase 31 Step 5 adds the evidence gap and routing plan in
[`phase31_p30_bl_001_evidence_gap_routing_plan.md`](phase31_p30_bl_001_evidence_gap_routing_plan.md).
That plan preserves the Tier A outcome as mechanics/methodology support only
and recommends a formal mechanics-only candidate artifact review summary
before any validated artifact, signal-definition binding, or implementation.

Phase 31 Step 6 adds that mechanics-only candidate artifact review summary in
[`phase31_p30_bl_001_mechanics_only_review_summary.md`](phase31_p30_bl_001_mechanics_only_review_summary.md).
The summary conditionally passes `P30-BL-001` for mechanics/methodology only,
keeps it unvalidated and unapproved, and recommends research/data/backtesting
validation design or targeted production-threshold evidence as the next safe
route if the threshold evaluator remains the focus.

Phase 31 Step 7 adds the final mechanics-only disposition in
[`phase31_p30_bl_001_final_disposition.md`](phase31_p30_bl_001_final_disposition.md).
The disposition closes `P30-BL-001` only in the mechanics-only sense, keeps it
non-validated, not production-ready, and not implementation-ready, and routes
the next research direction toward dataset-specific threshold or validation
evidence without approving implementation.

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
- `P30-BL-001` now has a normalized source package and a Tier A formal source
  review.
- The Tier A review conditionally supports mechanics and methodology only.
- The Step 5 routing plan keeps the Tier A result mechanics-only.
- The Step 6 mechanics-only summary records a conditional pass for
  mechanics/methodology only and does not promote the candidate.
- The Step 7 final disposition records `P30-BL-001` as mechanics-only
  dispositioned, in the mechanics-only sense only.
- `P30-BL-001` remains unvalidated, not approved, not production-ready, not
  threshold-justified, and not implementation-ready.
- Backlog entries are intake records only. They are not evidence.
- No candidate artifact has been accepted.
- No `ValidatedResearchArtifact` supports the threshold-style evaluator.
- No `ValidatedSignalDefinition` binds to an accepted artifact.
- No production threshold/config provenance exists.
- Real evaluator implementation remains blocked.

## 3. Recommended Broader Research Phases

Future docs/research phases may combine related documentation work when safe.
Recommended next phases:

1. Phase 31 Step 3: `P30-BL-001` source package normalization.
   Normalize source/provenance, primary references, mechanical definition
   details, non-claims, source tiers, groupings, preferred review candidates,
   and review gaps. This may include research-agent assistance, but produces
   only a source package, not validation.
2. Phase 31 Step 4: Tier A formal source review.
   Review comparator mechanics, `Decimal`, TA-Lib function shape,
   no-lookahead methodology, reproducibility, and non-claim governance. This
   step is complete and conditionally supports mechanics and methodology only.
3. Phase 31 Step 5: next routing after Tier A review.
   This step is complete. It recommends a formal mechanics-only candidate
   artifact review summary that may support future evaluator mechanics but
   explicitly cannot support a production threshold or evaluator
   implementation.
4. Phase 31 Step 6: mechanics-only candidate artifact review summary.
   This step is complete. It keeps `P30-BL-001` unvalidated and conditionally
   useful for mechanics/methodology only.
5. Phase 31 Step 7: final mechanics-only disposition and next-candidate
   routing.
   This step is complete. It closes `P30-BL-001` only in the mechanics-only
   sense and recommends routing next work toward dataset-specific threshold or
   validation evidence.
6. Future route: research/data/backtesting validation design or targeted
   production-threshold evidence collection if the threshold evaluator remains
   the focus. `P30-BL-002` or a replacement P0 candidate may be sourced only
   if it can provide traceable dataset-specific threshold or validation
   evidence. Validated signal-definition binding remains deferred until exact
   evidence supports it.
7. Later route: implementation readiness gate.
   Review whether exact validated research, exact validated signal-definition
   support, threshold/config provenance, implementation scope, and tests are
   all ready. Any production implementation remains a later narrow,
   test-first phase.

These phase labels are non-binding. A later prompt may combine adjacent
docs-only research tasks when the work remains low-risk and code-free.

## 4. Evidence Required Before Reviewing `P30-BL-001`

Phase 31 Step 3 normalized a source package for `P30-BL-001`, and Phase 31
Step 4 reviewed the Tier A subset. Before any future review can promote
anything, the reviewer still needs to check or collect:

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

- `P30-BL-001` or another candidate has a collected and normalized source
  package. `P30-BL-001` now satisfies this source-package-ready routing step
  only.
- The candidate has been reviewed against the Phase 30 evidence standard.
  Tier A review is complete for mechanics and methodology only; full candidate
  validation remains incomplete. Phase 31 Step 5 routes the result and Phase
  31 Step 6 summarizes it as mechanics-only. Phase 31 Step 7 dispositioned it
  only in the mechanics-only sense. None of these steps validates the
  candidate.
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
Future Step -- Next Candidate Dataset-Specific Threshold Evidence Route

Read first:
- docs/agent_context/codex_operating_context.md
- docs/design/phase31_research_track_next_action_plan.md
- docs/design/phase31_p30_bl_001_source_package.md
- docs/design/phase31_p30_bl_001_tier_a_review.md
- docs/design/phase31_p30_bl_001_evidence_gap_routing_plan.md
- docs/design/phase31_p30_bl_001_mechanics_only_review_summary.md
- docs/design/phase31_p30_bl_001_final_disposition.md
- docs/design/phase30_research_artifact_candidate_backlog.md
- docs/design/phase30_research_validation_evidence_standard.md
- docs/design/phase30_research_artifact_candidate_review_template.md

Scope: documentation-only routing for a next candidate that can supply
dataset-specific threshold or validation evidence. Preserve P30-BL-001 as
mechanics-only dispositioned and unvalidated. Do not review or validate the
next candidate unless that is explicitly scoped in a later phase.
Forbidden: production code, tests, evaluator behavior, signal computation,
broker/runtime behavior, persistence, ML, and LLM trading-path logic.
Verification: python -m pytest; git diff --name-only HEAD -- src; git diff --check.
```
