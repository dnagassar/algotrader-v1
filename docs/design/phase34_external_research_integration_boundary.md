# Phase 34 Step 1 - External Research Integration Boundary

## Purpose

This document defines how external research tools may support the
`algo_trader` project without becoming trusted production dependencies.

The local Git repository remains the source of truth. Tests remain the
enforcement layer. Reviewed docs remain institutional memory. External tools
remain advisory research accelerators only.

This phase is documentation-only. It adds no dependency, notebook, script,
data, schema, production code, test, external integration, evaluator, signal
computation, trading-path behavior, broker behavior, runtime behavior,
scheduler behavior, persistence behavior, portfolio behavior, OMS behavior,
QuantConnect behavior, vectorbt behavior, ML behavior, or LLM trading-path
behavior.

## External Tools Covered

This boundary covers external and semi-external research support, including:

- Perplexity
- Claude, Gemini, or other LLM reviewers
- Codex or other local implementation/documentation agents
- QuantConnect
- vectorbt
- notebooks
- vendor or public data sources
- external academic or practitioner research
- spreadsheets, CSV scratchpads, and ad hoc analysis files
- any similar tool, hosted service, sandbox, report, or generated output used
  to scout, critique, prototype, or summarize research

Coverage does not imply approval. A covered tool is not a trusted production
dependency, not a source of truth, and not part of normal pytest or the
trading hot path.

## Allowed Uses

External tools may be used for advisory research support such as:

- scout research
- source discovery
- literature review
- methodology critique
- contradiction finding
- code review suggestions
- test-matrix suggestions
- risk, assumption, and edge-case discovery
- benchmark or context comparisons
- drafting docs or proposal text for later review
- prototype experiments outside the deterministic core
- exploratory calculations outside normal pytest and outside production code
- identifying licensing, data, reproducibility, no-lookahead, or
  overclaiming concerns

Allowed use creates input for review. It does not create approved evidence,
approved behavior, implementation scope, validation, or trading authority.

## Forbidden Uses

External tools must not be used as:

- direct production dependencies
- trading hot-path dependencies
- live or paper order generators
- direct signal approval mechanisms
- direct threshold, parameter, or config approval mechanisms
- direct `ValidatedResearchArtifact` creation or approval mechanisms
- direct `ValidatedSignalDefinition` creation or approval mechanisms
- disposition authority for source, methodology, reproduction, validation, or
  implementation decisions
- normal pytest runtime calls
- network or credential dependencies for normal pytest
- direct portfolio mutation mechanisms
- broker, order, OMS, execution-plan, or risk-state mutation mechanisms
- source-of-truth notebooks, spreadsheets, screenshots, or LLM transcripts
- substitutes for project-local deterministic reproduction
- substitutes for reviewed primary sources
- substitutes for tests

Notebook results, hosted backtest results, vendor examples, LLM summaries, and
manual observations may inform a proposal only after their uncertainty is
recorded. They do not validate a candidate without repo-local review,
reproduction planning, approved data policy, and deterministic tests in later
scoped phases.

## Promotion Path

External research can become project-trusted only through a later explicit
promotion path:

1. External output is captured as proposal, scout, or review input only.
2. Claims are normalized into repo docs with evidence, inference, uncertainty,
   assumptions, limitations, and non-claims separated.
3. Primary sources, source terms, data feasibility, citation requirements,
   storage limits, and offline-use constraints are reviewed.
4. Deterministic local reproduction is planned before any implementation.
5. Fixture, storage, provenance, hashing, versioning, and exclusion-from-normal
   network access are approved before any data enters the repository.
6. Reproduction is implemented only in a later scoped phase that explicitly
   permits code, data fixtures, and tests.
7. Tests enforce deterministic behavior, offline safety, and side-effect
   boundaries.
8. A result-review template records limitations, non-claims, unresolved gaps,
   and what the result does not authorize.
9. Only after those steps can a future promotion discussion consider whether a
   reviewed result supports a validated artifact, signal definition, or
   implementation route.

No external tool can skip this path.

## Tool-Specific Boundaries

| Tool/category | Boundary |
| --- | --- |
| Perplexity | Scout research only. Citations, summaries, and source claims require verification against primary or otherwise reviewed sources before use. |
| Claude, Gemini, or other LLM reviewers | Review and critique only. They may suggest risks, contradictions, missing tests, and clearer language. They are not disposition authority. |
| Codex or other local implementation agents | Local implementation and documentation agents under scoped prompts. Changes must remain within allowed files, pass tests, and receive human review before trust. |
| QuantConnect | External sandbox or backtest reference only. It is not the project source of truth, not a runtime dependency, and not trusted unless results are reproduced locally under approved data and test policy. |
| vectorbt | Potential research or prototyping engine only. It is not production hot path infrastructure unless a future scoped phase explicitly approves use, dependency policy, deterministic behavior, and tests. |
| Notebooks | Exploratory only. They are not canonical unless later converted into deterministic scripts, tests, docs, or fixtures under explicit scope and review. |
| Vendor or public data | Candidate input only. Terms, storage, provenance, citation, versioning, offline replay, and credential/network policy must be approved before use. |
| Academic or practitioner research | Candidate evidence only. Primary sources are preferred, and claims must be normalized with uncertainty, limitations, data scope, and reproducibility gaps. |
| Spreadsheets and ad hoc analysis files | Scratch analysis only unless later normalized into reviewed docs, deterministic fixtures, and tests. They are not source-of-truth artifacts. |

## Evidence And Citation Standards

Evidence standards for external research:

- Primary sources are preferred.
- Secondary sources must be labeled as secondary and cannot replace primary
  verification when primary material is available.
- LLM-generated claims are not evidence by themselves.
- Screenshots and manual observations must record date, source, URL or
  document identity, and what was directly observed.
- Market, performance, backtest, or profitability-adjacent claims require data
  provenance, data scope, timestamp/as-of assumptions, and project-local
  reproduction before trust.
- Hosted results must identify platform, settings, data source, access date,
  assumptions, and known gaps.
- Uncertainty must be explicit. Unknown terms, hidden data treatment, adjusted
  price semantics, survivorship, revisions, and no-lookahead gaps remain
  blockers, not footnotes.

## Repository Boundaries

Repository placement rules:

- `docs/proposals` is for speculative or external-agent outputs when that
  directory and proposal route are explicitly needed.
- `docs/design` is for reviewed boundaries, phase decisions, and documented
  project policy.
- `src` changes require scoped implementation approval and remain forbidden in
  this phase.
- `tests` should change only when enforcing deterministic contracts in a later
  scoped phase.
- Data files must not enter the repository unless a later storage/fixture
  policy approves source terms, provenance, hashing, versioning, fixture scope,
  and offline replay.
- Notebooks, scratch spreadsheets, generated reports, and external exports are
  not canonical project artifacts unless a later phase explicitly normalizes
  them into reviewed repo artifacts.

No `docs/proposals` files are created or updated in this phase because no
proposal artifact is needed for this boundary, and the current repository does
not contain a `docs/proposals` directory.

## Normal Pytest Rule

Normal `python -m pytest` must remain:

- offline
- credential-free
- deterministic
- free of network calls
- free of SDK, broker, vendor, QuantConnect, vectorbt, notebook, hosted
  service, ML service, or LLM runtime calls
- free of live or paper account state
- free of external data acquisition or ingestion

If external research integrations ever exist, they must be explicitly skipped,
gated, or isolated so normal pytest never depends on network, credentials,
provider state, account state, local notebooks, hosted services, or wall-clock
data fetches.

## Recommended Next Routing

Recommended next docs-only gate: external research artifact intake checklist.

That checklist should define how scout outputs, LLM reviews, hosted backtest
notes, notebooks, spreadsheets, vendor/public data notes, citations, manual
observations, and prototype summaries are captured before any formal review.
It must preserve advisory status, uncertainty labels, source verification
requirements, non-claims, and the normal pytest rule.

## Explicit Non-Goals

This phase does not perform or authorize:

- implementation
- dependency changes
- dependency lockfile changes
- notebooks
- scripts
- data acquisition
- data ingestion
- dataset addition
- schema, code, or contract type
- backtest
- reproduction
- QuantConnect integration
- vectorbt integration
- broker integration
- runtime integration
- scheduler behavior
- persistence behavior
- LLM runtime integration
- ML behavior
- evaluator or signal implementation
- signal computation
- signal scoring, ranking, direction, confidence, or actionability
- `ValidatedResearchArtifact`
- `ValidatedSignalDefinition`
- production threshold
- profitability claim
- production-readiness claim
- implementation-readiness claim
- trading implication

## Remaining Blockers

Evaluator implementation, validation, reproduction, production routing, and
trading use remain blocked by all of the following:

- no `ValidatedResearchArtifact` from external tools
- no `ValidatedSignalDefinition` from external tools
- no approved external research integration
- no approved data storage/fixture policy
- no approved source, ETF universe, benchmark, or cash proxy for the Phase 33
  broad-ETF candidate
- no approved methodology or parameters
- no approved data acquisition or ingestion route
- no approved data license/offline-use path
- no project-local deterministic reproduction
- no no-lookahead audit
- no implementation-scope approval
- no evaluator tests
- no approved repository policy for notebooks, scratch spreadsheets, hosted
  backtest exports, or vendor/public data snapshots
- no result-review template for externally assisted research outputs
- no promotion/rejection decision
- no trading implication or production threshold
