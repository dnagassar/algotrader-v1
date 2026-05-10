# Phase 30 Research Artifact Candidate Sourcing Plan

## 1. Purpose

Phase 30 Step 4 defines a research artifact sourcing plan and backlog
boundary. It describes how future candidate research artifacts should be
identified, prioritized, and routed into the Phase 30 evidence standard and
candidate review template.

This phase reviews no candidate artifact, approves no artifact, creates no
validated research artifact, creates no validated signal definition, implements
no evaluator, and adds no signal computation. The goal is to define how future
research candidates will be sourced and triaged before any artifact review or
implementation readiness work occurs.

The sourcing plan is documentation-only. It does not admit any research into
the deterministic core, promote any threshold, or make any evaluator output
actionable.

Phase 30 Step 5 creates an initial unreviewed candidate backlog in
[`phase30_research_artifact_candidate_backlog.md`](phase30_research_artifact_candidate_backlog.md).
Those backlog entries are intake records only. They are not evidence, do not
validate any artifact, and do not authorize evaluator implementation.

Phase 30 Step 6 selects the first candidate to source in
[`phase30_first_research_candidate_source_selection.md`](phase30_first_research_candidate_source_selection.md).
Source selection is not validation. The selected candidate remains unreviewed
until source/provenance is collected and the candidate passes through the
evidence standard and review template.

## 2. Why A Sourcing Plan Is Needed

The project should not invent research evidence just because evaluator
mechanics are becoming clearer. A simple threshold-style evaluator can still
encode a trading assumption, so research must be sourced deliberately and
reviewed before any implementation work.

The sourcing plan is intended to prevent:

- ad hoc strategy invention
- arbitrary thresholds
- cherry-picked examples
- undocumented research sources
- unreviewed papers or notebooks entering the core
- evaluator implementation before evidence exists

Sourcing creates a backlog candidate only. It does not validate the candidate,
approve a signal definition, or authorize evaluator implementation.

## 3. Candidate Artifact Categories

Future candidate research artifacts worth sourcing may include:

- mechanical indicator definitions
- threshold sanity-check studies
- regime indicator studies
- predictive relationship studies
- risk filter studies
- data-quality or feature-validity studies
- backtesting methodology references
- no-lookahead or bias-control references

Candidates in these categories remain informational until reviewed against the
Phase 30 Step 2 evidence standard and documented with the Phase 30 Step 3
candidate review template.

## 4. Threshold Evaluator Candidate Needs

For the future threshold-style advisory evaluator, sourced artifacts should
ideally support:

- exact input meaning for `indicator_value`
- why `Decimal` input is appropriate
- why a threshold condition is meaningful
- why the chosen comparator is justified
- how the threshold value or source is determined
- what claim type is being made
- why output remains advisory only
- what the artifact does not prove

If sourced material cannot address these needs, it may still be useful
background research, but it should not be treated as sufficient to unblock
evaluator implementation.

## 5. Sourcing Criteria

Future candidate artifacts should be prioritized when they have:

- clear provenance
- reproducible method
- explicit dataset description
- explicit time window
- explicit asset universe
- clear input definitions
- clear threshold rationale
- no-lookahead controls
- survivorship-bias awareness
- documented assumptions
- documented limitations
- explicit non-claims
- relevance to deterministic offline evaluation

The strongest candidates are those that can plausibly support offline,
credential-free, deterministic review without relying on broker, account,
portfolio, runtime, ML, or LLM trading-path behavior.

## 6. Rejection And Deprioritization Criteria

Candidate artifacts should be deprioritized or rejected when they rely on:

- vague screenshots or social-media claims
- undocumented datasets
- unclear indicator formulas
- unclear time windows
- hidden preprocessing
- manual cherry-picking
- live-only behavior
- broker, account, or portfolio state
- LLM-generated strategy claims without evidence
- ML predictions without deterministic validation
- profitability claims without reproducibility
- threshold values with no provenance

Rejected or deprioritized candidates may still be recorded for auditability,
but they must not support production code, production thresholds, or evaluator
implementation.

## 7. Candidate Backlog Format

A future candidate backlog entry should capture:

- candidate title
- source type
- source or provenance
- candidate artifact category
- related evaluator candidate, if any
- related signal idea, if any
- expected input names
- expected input value types
- expected threshold or config relevance
- dataset scope summary
- claim type
- known limitations
- review priority
- status: unsourced / sourcing target / sourced / needs review /
  informational only
- next action

The backlog is an intake queue, not a validation record. A backlog entry does
not become a `ValidatedResearchArtifact` until a later review explicitly
passes the candidate through the evidence standard and review template.

## 8. Priority Levels

Suggested priority levels:

- P0: directly required to unblock the threshold evaluator.
- P1: useful for near-term research validation.
- P2: useful later for broader feature or evaluator work.
- P3: informational only.

Priority is not evidence quality. A P0 candidate can still fail review, and a
P3 candidate can still be useful for background understanding without entering
the deterministic core.

## 9. Intake Routing

Future candidate sourcing should follow this route:

1. Candidate source identified.
2. Backlog entry created.
3. Candidate artifact collected or summarized.
4. Candidate reviewed using the Phase 30 evidence standard.
5. Review documented using the candidate review template.
6. Only then considered for `ValidatedResearchArtifact`.
7. Only then considered for `ValidatedSignalDefinition`.
8. Only then considered for evaluator implementation readiness.

Any skipped step keeps implementation blocked.

## 10. Relationship To Proposals

Future broader strategy ideas may live under `docs/proposals/` if that pattern
is established by later documentation work. This Phase 30 sourcing plan is not
a proposal file and does not create proposal artifacts.

This document is a design boundary for research evidence admission. It defines
how candidate research should enter the backlog before review, not how to
invent strategies or promote ideas into the deterministic core.

## 11. Explicit Implementation Blockers

Evaluator implementation remains blocked until:

- at least one candidate artifact is sourced
- the candidate artifact is reviewed against the evidence standard
- the candidate passes or conditionally passes with resolved gaps
- an exact `ValidatedResearchArtifact` exists
- an exact `ValidatedSignalDefinition` exists
- threshold or config provenance is explicit
- implementation scope is approved
- tests are written or ready

The threshold-style advisory evaluator remains viable but unimplemented.

## 12. Explicitly Out Of Scope

Phase 30 Step 4 does not add:

- actual research artifact
- candidate artifact review
- validated research artifact
- validated signal definition
- evaluator implementation
- evaluator protocol
- signal computation
- feature computation
- strategy logic
- score, direction, confidence, or actionability
- ranking or probability
- risk approval
- execution intent creation
- broker or Alpaca behavior
- order submission
- runtime or scheduler behavior
- persistence
- live data ingestion
- ML or LLM trading-path behavior

Normal pytest must remain offline, credential-free, and safe.

## 13. Non-Binding Future Phase Sketch

Possible future phases include:

1. Phase 30 Step 5: populate candidate research backlog, docs-only.
2. Phase 30 Step 6: select first candidate source target, docs-only.
3. Phase 30 Step 7: collect/summarize the selected candidate source,
   docs-only.
4. Phase 30 Step 8: first candidate research artifact review, docs-only, only
   when a candidate exists.
5. Phase 30 Step 9: candidate validated signal definition review and artifact
   binding.
6. Phase 30 Step 10: implementation scope approval review.
7. Later: minimal threshold evaluator implementation only if all blockers are
   resolved.

This sketch is non-binding. Any future work must remain contract-first,
test-first, deterministic, offline-safe, credential-free, broker-isolated,
advisory, pre-risk, and outside the LLM trading hot path.
