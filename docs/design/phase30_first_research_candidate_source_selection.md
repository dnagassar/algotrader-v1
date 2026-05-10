# Phase 30 First Research Candidate Source Selection

## 1. Purpose

Phase 30 Step 6 selects the first research candidate to source next and
defines the evidence that must be collected before formal review.

This phase is source selection only. It reviews no research artifact, approves
no artifact, creates no validated research artifact, creates no validated
signal definition, implements no evaluator, and adds no signal computation.
The goal is to choose the first candidate to source and define what evidence
must be collected before the candidate can be reviewed against the Phase 30
evidence standard and candidate review template.

The selected candidate remains unreviewed, unvalidated, not approved, and not
implementation-ready.

## 2. Selection Criteria

The first sourcing target should satisfy as many of these criteria as possible:

- highest relevance to the threshold-style advisory evaluator
- minimal complexity
- deterministic input compatibility
- likely ability to support `indicator_value`
- likely ability to support `Decimal`
- clear threshold or config relevance
- availability of provenance
- likelihood of reproducibility
- usefulness for near-term research validation
- low risk of actionability or strategy overreach

These criteria prioritize narrow, auditable source collection before broader
strategy research. They do not validate the selected candidate.

## 3. Recommended First Candidate

Recommended first sourcing target:

| Field | Decision |
| --- | --- |
| candidate id | `P30-BL-001` |
| title | Simple scalar threshold indicator definition |
| category | mechanical indicator definitions |
| priority | P0 |
| Step 6 status | sourcing target |
| related evaluator candidate | future threshold-style advisory evaluator |
| related signal idea | scalar threshold advisory state |

`P30-BL-001` remains unreviewed, unvalidated, not approved, not
production-ready, and not implementation-ready. Selecting it only means it is
the first candidate whose source/provenance should be collected.

This selection does not validate `indicator_value`, justify any production
threshold, approve the `>=` comparator, or authorize evaluator implementation.

## 4. Why This Candidate First

`P30-BL-001` is the safest first sourcing target because it has a small
evidence surface. A mechanical scalar threshold definition can be sourced and
reviewed without first accepting a market-data dataset, predictive claim,
profitability claim, trading strategy, broker behavior, or portfolio
assumption.

It is also close to the threshold evaluator needs:

- it can clarify what `indicator_value` means
- it can clarify whether `Decimal` is an appropriate explicit value type
- it can clarify threshold/comparator terminology
- it can help keep output advisory-only
- it is easier to review against the evidence standard than broader
  predictive or profitability material
- it has fewer market-data assumptions than regime, momentum, risk-filter, or
  backtesting candidates
- it is less likely to imply actionability than a threshold performance study

This candidate is not sufficient by itself to unblock implementation. A later
threshold sanity-check candidate, such as `P30-BL-002`, is still likely needed
to justify any non-arbitrary production threshold value.

## 5. Evidence To Collect Before Review

Before `P30-BL-001` can enter formal review, the source package should collect:

- source/provenance
- artifact title or reference
- author/source
- date or version
- dataset description, if applicable
- dataset window, if applicable
- asset universe, if applicable
- timeframe or bar size, if applicable
- input definition
- threshold/config rationale, if applicable
- method description
- assumptions
- limitations
- non-claims
- reproducibility notes
- no-lookahead or bias-control notes, if applicable
- relevance to `indicator_value`
- relevance to the threshold-style advisory evaluator
- whether it can bind to a future `ValidatedSignalDefinition`

For a purely mechanical definition, dataset fields may be not applicable, but
the evidence package must say that explicitly rather than leaving them
ambiguous. If any threshold value is proposed, the source package must record
whether it is mechanical, illustrative, test-only, or evidence-backed.

## 6. Source Collection Workflow

Future workflow:

```text
selected backlog candidate
  -> collect source/provenance
  -> summarize evidence package
  -> verify it is reviewable
  -> review using Phase 30 evidence standard and candidate review template
  -> pass / conditional pass / fail / informational only
  -> only then consider ValidatedResearchArtifact
  -> only then consider ValidatedSignalDefinition
```

Any skipped step keeps implementation blocked. A selected candidate can still
fail review or remain informational only.

## 7. What Not To Collect As Evidence

The following are insufficient by themselves:

- social media claims
- screenshots without methodology
- unaudited LLM-generated claims
- vague strategy descriptions
- unexplained thresholds
- performance claims without reproducibility
- live-only claims
- broker, account, or portfolio anecdotes
- untraceable data samples
- cherry-picked examples

Such material may be recorded as a rejected or informational lead, but it must
not support a validated artifact, signal definition, threshold, implementation
scope, or production code.

## 8. Backlog Update Rules

Allowed backlog statuses after this phase are:

- unsourced
- sourcing target
- sourced
- needs review
- informational only

This phase updates only the selected candidate, `P30-BL-001`, to `sourcing
target`. That status means the candidate is next in line for source collection
only.

No candidate may be marked:

- validated
- approved
- production-ready
- implementation-ready

## 9. Relationship To Existing Docs

The research candidate backlog records candidate intake status. This phase
updates the backlog by selecting one first sourcing target.

The sourcing plan defines how candidates should be collected and routed. This
phase applies that plan to choose the first target but does not collect the
source yet.

The evidence standard remains the fixed yardstick. Source selection does not
lower the evidence bar or fill missing evidence.

The candidate review template remains mandatory. The selected candidate must
pass formal review before it can support a validated artifact.

The threshold evaluator research-support boundary remains the implementation
gate. The future threshold-style advisory evaluator remains blocked pending
source collection, artifact review, exact validated research support, exact
validated signal-definition support, explicit threshold/config provenance, and
implementation scope approval.

A future `ValidatedResearchArtifact` may only be considered after the selected
candidate is sourced and reviewed. A future `ValidatedSignalDefinition` may
only be considered after exact artifact binding is reviewed.

## 10. Remaining Blockers

Evaluator implementation remains blocked until:

- selected candidate source is collected
- candidate is reviewed against the evidence standard
- candidate passes or conditionally passes with resolved gaps
- exact `ValidatedResearchArtifact` exists
- exact `ValidatedSignalDefinition` exists
- threshold/config provenance is explicit
- implementation scope is approved
- tests are written or ready

The threshold-style advisory evaluator remains viable but unimplemented.

## 11. Explicitly Out Of Scope

Phase 30 Step 6 does not add:

- tests
- actual reviewed research artifact
- validated research artifact
- validated signal definition
- evaluator implementation
- evaluator protocol changes
- signal computation
- feature computation
- strategy logic
- scoring
- signal direction
- confidence or probability
- actionability flags
- ranking
- signal-to-risk conversion
- risk approval
- execution intent creation
- execution-plan mutation
- portfolio mutation
- broker or Alpaca behavior
- order submission
- runtime or scheduler behavior
- persistence writes
- live data ingestion
- network calls from production code
- ML training or inference
- LLM trading-path behavior

Normal pytest must remain offline, credential-free, and safe.

## 12. Non-Binding Future Phase Sketch

Possible future phases include:

1. Phase 30 Step 7: collect/summarize the selected candidate source,
   docs-only.
2. Phase 30 Step 8: first candidate research artifact review using the
   template, docs-only.
3. Phase 30 Step 9: candidate validated signal definition review and artifact
   binding.
4. Phase 30 Step 10: implementation scope approval review.
5. Later: minimal threshold evaluator implementation only if all blockers are
   resolved.

This sketch is non-binding. Any future work must remain contract-first,
test-first, deterministic, offline-safe, credential-free, broker-isolated,
advisory, pre-risk, and outside the LLM trading hot path.
