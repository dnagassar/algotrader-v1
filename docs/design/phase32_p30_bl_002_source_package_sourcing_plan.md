# Phase 32 Step 2 — P30-BL-002 Source Package Sourcing Plan

## Purpose

Phase 32 Step 2 defines what `P30-BL-002` must produce before any formal
review can begin.

This phase is documentation-only. It does not collect sources, review sources,
approve evidence, validate a candidate, promote a candidate, or implement
anything. It defines the sourcing requirements and rejection/replacement
criteria for a later source-package collection phase.

## Prior state

`P30-BL-001`, "Simple scalar threshold indicator definition", remains
mechanics-only dispositioned. It is non-validated, unapproved, not
production-ready, not implementation-ready, and not threshold-justified. It
does not provide dataset-specific validation, a production threshold
value/source, predictive evidence, profitability evidence, an exact
`ValidatedResearchArtifact`, an exact `ValidatedSignalDefinition`, or evaluator
implementation readiness.

Phase 32 Step 1 selected dataset-specific threshold or validation evidence
sourcing as the next research route. `P30-BL-002`, "Threshold sanity check for
`indicator_value`", is only the current sourcing target handle. It remains
unsourced, unreviewed, unvalidated, unapproved, not production-ready, not
implementation-ready, and not threshold-justified.

If `P30-BL-002` cannot produce a concrete source package that satisfies this
plan, a better sourced P0 replacement should be selected before formal review.

## Required source package

A later source-package collection phase must produce a normalized package with
all of the following fields before formal review can begin:

- source/provenance: stable access path or local access note, source type,
  publisher or repository context, access date, and any license or use notes
  relevant to reproducibility
- title/reference: exact title, report name, notebook name, paper name, or
  benchmark identifier
- author/source: authors, source owner, institution, vendor, repository owner,
  or report maintainer
- date/version: publication date, revision date, code/notebook version,
  dataset version, or explicit statement that the version is unavailable
- dataset scope: asset universe, market, geography, date range, sampling
  frequency, data vendor/source assumptions, survivorship assumptions,
  corporate-action assumptions, exclusions, and missing-data scope
- asset class/universe: equities, ETFs, futures, crypto, or other scoped
  universe, including whether the source covers single assets, broad markets,
  sectors, or a screened subset
- timeframe: observation frequency, validation period, training/selection
  window, holdout window, walk-forward windows, and any rebalance cadence
- point-in-time assumptions: timestamp meaning, when each input is observable,
  universe membership timing, feature availability, label timing, and `as_of`
  alignment assumptions
- data quality assumptions: missing data handling, stale data handling,
  outlier treatment, split/dividend/corporate-action handling, survivorship
  controls, and data-cleaning order
- explicit input definition: exact input name, formula or construction method,
  required raw fields, units, expected value type, comparator semantics, and
  whether values are observed or derived
- threshold or parameter rationale: exact threshold, parameter family, or
  tuning method; rationale for why the value is not arbitrary; and whether the
  rationale is dataset-specific or only methodological
- validation design: in-sample/out-of-sample structure, holdout method,
  walk-forward method, metric definitions, sensitivity checks, and transaction
  cost or liquidity assumptions if performance is discussed
- no-lookahead controls: feature timing, label timing, split timing,
  rebalancing timing, universe-selection timing, preprocessing timing, and
  controls against future data leakage
- reproducibility notes: deterministic rerun requirements, code/notebook
  availability, formulas, preprocessing steps, dependency versions, dataset
  access constraints, random seed handling, and known nondeterminism
- robustness or out-of-sample evidence: holdout results, walk-forward checks,
  cross-period sensitivity, cross-universe sensitivity, parameter sensitivity,
  or explicit statement that such evidence is absent
- limitations: dataset limits, market-regime limits, asset-universe limits,
  liquidity/transaction-cost limits, stale-data risks, known biases, and
  conditions under which the evidence should not be reused
- non-claims: explicit statements that the package does not establish live
  trading suitability, production readiness, risk approval, order approval,
  profitability, or actionability unless later review proves otherwise
- future binding notes: whether the material might later support a
  `ValidatedResearchArtifact` or `ValidatedSignalDefinition`, without creating
  either one and without implying approval
- unresolved gaps: missing fields, weak assumptions, reproducibility blockers,
  validation blockers, review questions, and reasons the package might fail or
  be replaced

Missing, vague, or non-dataset-specific answers must remain visible in the
package. They must not be hidden behind summary language.

## Acceptable source types

Acceptable source material may include:

- reproducible research notebooks or papers with explicit formulas, dataset
  scope, timestamp assumptions, validation design, and limitations
- dataset-specific validation reports with clear input definitions,
  thresholds or parameters, point-in-time assumptions, and robustness notes
- methodology papers with a directly usable validation design that can be
  bound to a specific later source package without inventing missing evidence
- documented backtests with clear dataset scope, preprocessing steps,
  no-lookahead controls, parameter rationale, and reproducibility notes
- benchmark studies with explicit inputs, thresholds or parameter families,
  validation windows, robustness checks, and limitations

Acceptable sources must be traceable and concrete enough for a later reviewer
to decide what was actually tested, on what data, with what inputs, under what
timing assumptions, and with what limitations.

## Unacceptable source types

Unacceptable source material includes:

- generic indicator tutorials that explain a formula but do not provide
  dataset-specific validation evidence
- undocumented blog claims, summaries, or social posts that cannot be
  reproduced or audited
- screenshots, charts, images, or tables without reproducible methodology
- marketing claims, vendor claims, or strategy descriptions that do not expose
  inputs, timing assumptions, validation design, and limitations
- profitability claims without dataset scope, methodology, point-in-time
  controls, and reproducibility notes
- sources without no-lookahead controls or with ambiguous feature/label timing
- sources that do not bind to a specific input definition, threshold rationale,
  parameter rationale, or validation design
- model-generated summaries unless they only assist discovery and are replaced
  by traceable primary or reviewable source material
- generic threshold examples that would make `indicator_value >= threshold`
  mechanically expressible but still arbitrary
- sources that imply live-trading readiness, order approval, risk approval, or
  actionability without a later formal project review

Unacceptable material may be recorded as a search dead end in a later phase,
but it must not be promoted into a review-ready package.

## Minimum review-readiness criteria

Formal Phase 32 review can start only when the source package:

- names the candidate id and title, or explicitly names a replacement P0
  candidate that supersedes `P30-BL-002`
- identifies traceable source/provenance, title/reference, author/source, and
  date/version details
- defines dataset scope, asset class/universe, timeframe, and point-in-time
  assumptions with enough specificity to check for lookahead risk
- defines the exact input, threshold or parameter rationale, comparator
  semantics, validation design, and no-lookahead controls
- records reproducibility notes and data quality assumptions rather than
  relying on prose claims
- includes robustness or out-of-sample evidence; absence of such evidence means
  the package is not review-ready for threshold validation
- records limitations, non-claims, possible future binding notes, and
  unresolved gaps
- is narrow enough that a later reviewer can accept, reject, or classify it as
  informational only without inventing missing evidence

If any required field is missing or too vague to audit, the package is not
review-ready.

## Rejection and replacement criteria

`P30-BL-002` should be rejected or replaced before formal review if sourcing
finds that:

- no traceable, reproducible, dataset-specific material can be produced
- available material is only a generic indicator tutorial, formula reference,
  unsupported claim, or marketing-style assertion
- dataset scope, asset universe, timeframe, or data source assumptions remain
  unknown
- point-in-time assumptions or no-lookahead controls are missing or impossible
  to reconstruct
- the source does not define the exact input, comparator, threshold, parameter
  rationale, or validation design
- the evidence depends on non-reproducible screenshots, private summaries, or
  inaccessible methodology
- robustness, out-of-sample evidence, or sensitivity analysis is absent and no
  conservative limitation can make the material reviewable
- the source's claims depend on actionability, live-trading suitability, risk
  approval, or profitability claims that cannot be separated from the proposed
  advisory input definition
- a different P0 candidate has a stronger traceable source package with clearer
  dataset scope, timing assumptions, threshold rationale, validation design,
  reproducibility, and limitations

Replacement is preferred over forcing a weak `P30-BL-002` package forward. A
replacement P0 candidate remains a candidate only; it would still require
source-package normalization and formal review before any validation,
promotion, binding, or implementation could be considered.

## Explicit non-claims

This phase does not validate a signal, threshold, edge, profitability,
robustness, or implementation readiness.

This phase does not approve a production threshold or parameter. It does not
create a `ValidatedResearchArtifact`, create a `ValidatedSignalDefinition`,
bind a signal definition to an artifact, or authorize evaluator
implementation.

This phase does not collect or cite actual research sources. It does not add a
real signal evaluator, signal computation, scoring, ranking, direction,
confidence, probability, actionability, broker behavior, Alpaca behavior,
runtime behavior, scheduler behavior, persistence, ML, or LLM trading-path
behavior.

## Remaining blockers

Evaluator implementation remains blocked until later phases resolve all of the
following:

- a concrete `P30-BL-002` source package or better P0 replacement source
  package exists
- the package satisfies the minimum review-readiness criteria in this plan
- formal review against the Phase 30 evidence standard is complete
- any review gaps needed for promotion are resolved
- an exact `ValidatedResearchArtifact` exists
- an exact `ValidatedSignalDefinition` exists and binds to the accepted
  artifact
- threshold/config provenance is explicit and reviewed
- point-in-time and no-lookahead controls are reviewed for the proposed
  dataset and input definitions
- robustness or out-of-sample evidence is reviewed and limitations are
  recorded
- implementation scope is explicitly approved
- production evaluator tests are scoped and ready to be written
- the implementation phase remains narrow, deterministic, offline-safe,
  broker-isolated, credential-free, and outside the LLM trading hot path

## Verification

Verification after Phase 32 Step 2:

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
 M docs/design/phase32_dataset_specific_validation_candidate_selection.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_p30_bl_002_source_package_sourcing_plan.md
```

Manual documentation checks:

- edited markdown files have no trailing whitespace
- edited markdown files have exactly one final newline
- edited markdown files were inspected for completeness and were not truncated
