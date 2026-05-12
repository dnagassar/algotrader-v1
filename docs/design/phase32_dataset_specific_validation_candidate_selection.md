# Phase 32 Step 1 — Dataset-Specific Validation Candidate Selection

## Purpose

Phase 32 Step 1 selects the next research direction after the
`P30-BL-001` mechanics-only disposition. The project is moving away from more
mechanics-only threshold work and toward a candidate that can support
dataset-specific validation evidence before any formal review, promotion, or
implementation is considered.

This phase is documentation-only. It chooses a routing direction and evidence
standard for the next sourcing pass. It does not review, approve, validate, or
implement the next candidate.

## Prior state

`P30-BL-001`, "Simple scalar threshold indicator definition", is closed only
in the mechanics-only sense. It can support scalar comparator mechanics,
threshold vocabulary, possible `Decimal` scalar representation, deterministic
input review questions, no-lookahead and reproducibility prompts, and
advisory-only non-claim framing.

`P30-BL-001` remains non-validated, unapproved, not production-ready, not
implementation-ready, and not threshold-justified. It does not provide
dataset-specific validation, a production threshold value/source,
threshold/config provenance, predictive evidence, profitability evidence,
risk-adjusted-return evidence, an exact `ValidatedResearchArtifact`, an exact
`ValidatedSignalDefinition`, signal-definition binding, or evaluator
implementation readiness.

More mechanics-only work would mostly restate comparator and scalar-input
handling. The current blocker is not mechanical expression; it is the absence
of reviewed, dataset-specific evidence for any threshold or signal definition.

## Candidate selection criteria

The next candidate direction must be useful before formal review because it can
support source-package collection for actual validation evidence. A candidate
should be prioritized only if it can plausibly provide:

- clear dataset scope, including asset universe, market, date range, frequency,
  and data source or vendor assumptions
- point-in-time data assumptions, including timestamp meaning and how inputs
  are known at `as_of`
- explicit input definition, including the observed scalar, construction
  method, units, missing-data treatment, and expected value type
- explicit threshold or parameter rationale, including comparator semantics and
  why the proposed value is not arbitrary
- no-lookahead controls, including feature timing, label timing, and any
  universe-selection safeguards
- reproducibility notes, including formula details, dataset access notes,
  preprocessing assumptions, and deterministic rerun requirements
- robustness or out-of-sample evidence, such as holdout periods, walk-forward
  checks, sensitivity analysis, or other conservative validation controls
- limitations and non-claims, especially no claim of profitability,
  actionability, live-trading suitability, or production readiness
- a possible future path to exact binding by a `ValidatedSignalDefinition`,
  without creating or approving that binding in this phase

Backlog presence, familiar indicator names, generic threshold language, and
model-written summaries are not enough.

## Candidate options

### `P30-BL-002`

`P30-BL-002`, "Threshold sanity check for `indicator_value`", is already in
the backlog as a P0 candidate. It is directly aligned with the unresolved
threshold problem because it asks for evidence explaining threshold choice and
non-claims.

Its current weaknesses are material. It is unsourced, its dataset scope is
unknown, its comparator evidence is unreviewed, and it has no validation window
or threshold rationale. As written, `P30-BL-002` is not ready for formal
review, validation, promotion, or implementation.

The safest use of `P30-BL-002` is therefore as a sourcing handle only: source a
candidate package under this backlog id if the search finds traceable,
dataset-specific threshold or validation evidence that satisfies the selection
criteria above.

Phase 32 Step 2 adds the source-package sourcing plan in
[`phase32_p30_bl_002_source_package_sourcing_plan.md`](phase32_p30_bl_002_source_package_sourcing_plan.md).
That plan defines what `P30-BL-002` must produce before formal review can even
begin. It does not collect, review, approve, validate, or implement evidence.

Phase 32 Step 3 adds the collection and normalization attempt in
[`phase32_p30_bl_002_source_package.md`](phase32_p30_bl_002_source_package.md).
The revised package normalizes 23 candidate-only entries from the supplied
Claude, Perplexity, and Gemini/browser scout reports. It records preliminary
source categories, deduplication, source-level gaps, package-level gaps, and
non-claims. It is still not formal review, validation, approval, promotion, or
implementation readiness.

### Better sourced replacement P0 candidate

A replacement P0 candidate is safer than forcing `P30-BL-002` forward if source
discovery finds a stronger artifact first. A better replacement would have a
named study, paper, dataset report, or reproducible research package with
clearer dataset scope, point-in-time assumptions, explicit inputs, threshold or
parameter rationale, no-lookahead controls, reproducibility notes, robustness
or out-of-sample evidence, and conservative limitations.

Such a replacement would still be a candidate only. It would require source
package normalization before any formal review and could still fail, require
gaps, or be classified as informational only.

### Dataset-specific validation evidence route

The preferred direction is not a specific indicator name by itself. The
preferred direction is a dataset-specific validation evidence package that can
be reviewed later against the Phase 30 evidence standard.

This route is more useful than more mechanics-only work because it targets the
current implementation blockers: threshold rationale, point-in-time input
meaning, validation scope, no-lookahead controls, reproducibility, and
robustness. It still does not make any trading claim or authorize a real
evaluator.

## Recommended next target

Select dataset-specific threshold or validation evidence sourcing as the next
research direction.

Use `P30-BL-002` as the current backlog routing handle only if the next
sourcing pass can produce a concrete source package with dataset-specific
threshold or validation evidence. If that sourcing pass cannot produce a
sufficiently clear package, source a better P0 replacement before formal
review.

Phase 32 Step 2 narrows the next sourcing pass by defining the required source
package fields, acceptable and unacceptable source material, review-readiness
criteria, and rejection/replacement triggers for `P30-BL-002`.

Phase 32 Step 3 normalized the supplied scout-report candidates for
`P30-BL-002`. The next safest route is primary-source verification and limited
formal review intake for selected candidates, with additional sourcing or a
better P0 replacement if the selected candidates fail review-readiness checks.

This phase does not select `P30-BL-002` as a reviewed artifact. It does not
approve `P30-BL-002`, validate it, promote it, bind it to a
`ValidatedSignalDefinition`, or make it implementation-ready.

## Evidence package required before review

Before any formal review of `P30-BL-002` or a replacement P0 candidate, the
project needs a normalized evidence package containing:

- candidate id and title, with a clear note if a replacement supersedes
  `P30-BL-002`
- source/provenance: title, authors or source owner, publisher, date, version,
  access date, source type, and stable links or local access notes
- dataset scope: asset universe, market, date range, sampling frequency,
  survivorship/corporate-action assumptions, data source, and exclusions
- point-in-time assumptions: when each input was observable, timestamp
  semantics, as-of alignment, and universe membership timing
- explicit input definition: observed scalar name, construction formula,
  required fields, units, missing/stale data handling, and expected value type
- threshold or parameter rationale: exact value or parameter family,
  comparator semantics, tuning method, and why it is not arbitrary
- validation design: in-sample and out-of-sample split, holdout or walk-forward
  method, robustness checks, sensitivity analysis, and any transaction-cost or
  liquidity assumptions if performance is discussed
- no-lookahead controls: feature timing, label timing, split timing,
  rebalancing timing, and data-cleaning controls
- reproducibility notes: deterministic rerun requirements, data-access
  dependencies, formula/code references, preprocessing notes, and known
  nondeterminism
- limitations and non-claims: what the source does not prove, what conditions
  narrow its use, and why it does not imply actionability or live-trading
  suitability
- possible future binding notes: whether the artifact might later support a
  `ValidatedResearchArtifact` and `ValidatedSignalDefinition`, without
  creating either one
- unresolved gaps that must block review, promotion, or implementation

## Explicit non-claims

This phase does not validate a signal, threshold, edge, profitability,
robustness, or implementation readiness.

This phase does not approve a production threshold or config value. It does not
create a `ValidatedResearchArtifact`, create a `ValidatedSignalDefinition`,
bind a signal definition to an artifact, or authorize evaluator implementation.

This phase does not add a real signal evaluator, signal computation, scoring,
ranking, direction, confidence, probability, actionability, broker behavior,
Alpaca behavior, runtime behavior, scheduler behavior, persistence, ML, or LLM
trading-path behavior.

## Remaining blockers

Evaluator implementation remains blocked until all of the following are
resolved in later phases:

- a concrete `P30-BL-002` source package or better P0 replacement source
  package exists
- the Phase 32 Step 3 scout-normalized candidates are verified against primary
  sources or replaced by stronger sourced candidates
- the source package satisfies the Phase 32 Step 2 sourcing-plan requirements
- the package has dataset-specific evidence rather than generic mechanics only
- formal review against the Phase 30 evidence standard is complete
- all review gaps needed for promotion are resolved
- an exact `ValidatedResearchArtifact` exists
- an exact `ValidatedSignalDefinition` exists and binds to the accepted
  artifact
- threshold/config provenance is explicit and reviewed
- point-in-time and no-lookahead controls are reviewed for the proposed
  dataset and input definitions
- robustness or out-of-sample evidence is reviewed and limitations are
  recorded
- implementation scope is explicitly approved
- production evaluator tests are written or ready to be written
- the implementation phase remains narrow, deterministic, offline-safe,
  broker-isolated, credential-free, and outside the LLM trading hot path

## Verification

Verification after Phase 32 Step 1:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
passed; Git emitted LF-to-CRLF working-copy warnings only for modified
existing docs

git status --short
 M docs/design/phase30_research_artifact_candidate_backlog.md
 M docs/design/phase31_research_track_next_action_plan.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_dataset_specific_validation_candidate_selection.md
```

Manual documentation checks:

- edited markdown files have no trailing whitespace
- edited markdown files have exactly one final newline
- edited markdown files were inspected for completeness and were not truncated
