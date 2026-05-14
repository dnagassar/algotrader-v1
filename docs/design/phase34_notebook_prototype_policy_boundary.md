# Phase 34 Step 3 - Notebook / Prototype Policy Boundary

## Purpose

This policy defines how notebooks, prototype scripts, hosted experiments,
spreadsheets, and ad hoc research files may support research without becoming
trusted project artifacts.

Exploratory artifacts may help sketch hypotheses, inspect ideas, visualize
data shapes, and draft questions for later deterministic phases. They must not
become the source of truth for project behavior, source/data approval,
validation, production thresholds, signal definitions, normal pytest behavior,
or trading-path inputs.

The local Git repository, reviewed docs, and deterministic tests remain the
project trust boundary. This phase is documentation-only and adds no notebook,
script, dependency, data, schema, production code, test, integration,
reproduction, backtest, evaluator behavior, signal computation, runtime
behavior, broker behavior, vectorbt behavior, QuantConnect behavior, ML
behavior, LLM runtime integration, or trading implication.

## Covered Artifact Types

This policy covers exploratory and external research aids, including:

- Jupyter notebooks
- ad hoc Python scripts
- vectorbt prototypes
- QuantConnect backtest exports or screenshots
- spreadsheets
- CSV extracts or manual tables
- charts and plots
- external platform reports
- copied snippets from LLM tools or websites

Coverage means the artifact is controlled by this boundary. It does not mean
the artifact is approved, canonical, trusted, reproducible, validated, or
eligible for implementation.

## Allowed Uses

Covered artifacts may be used for advisory research support such as:

- exploratory calculations
- hypothesis sketching
- visualization
- sanity checks
- API or data-source learning outside the deterministic core
- performance-shape exploration with explicit non-claims
- generating questions for later deterministic phases
- drafting docs or proposals

Allowed use creates context for review. It does not create approved evidence,
approved source/data status, validation, implementation scope, production
thresholds, or trading authority.

## Forbidden Uses

Covered artifacts must not be used as:

- production source of truth
- direct trading signal source
- direct threshold, parameter, or config source
- direct validation evidence
- direct source or data approval
- direct normal pytest dependency
- direct broker, runtime, or OMS dependency
- direct portfolio mutation mechanism
- direct artifact or signal-definition creation mechanism
- replacement for deterministic local reproduction
- place to hide manual edits or undocumented data cleaning

Covered artifacts also must not create or approve
`ValidatedResearchArtifact`, `ValidatedSignalDefinition`, evaluator behavior,
signal computation, signal scoring, ranking, direction, confidence,
actionability, production thresholds, broker behavior, runtime behavior,
portfolio behavior, persistence behavior, scheduler behavior, source/data
approval, profitability claims, implementation-readiness claims, or trading
implications.

## Required Notebook / Prototype Metadata

Any future exploratory artifact must record, in the artifact itself or in an
adjacent reviewed intake note:

- purpose
- date
- author/tool
- data source
- data snapshot or retrieval date
- assumptions
- dependencies/tools used
- whether network or credentials were involved
- limitations
- non-claims
- what must be reproduced locally before trust
- recommended routing

If any required metadata is missing, the artifact remains scratch context only.
Missing metadata must not be inferred into approval.

## Promotion Path

Exploratory work can become trusted only through a later scoped promotion path:

1. The artifact is captured through the Phase 34 external research artifact
   intake checklist.
2. Claims are normalized into reviewed docs with assumptions, evidence labels,
   uncertainty, limitations, and non-claims separated.
3. Source and data terms are reviewed before any source, dataset, fixture,
   storage, publication, or offline-use decision.
4. Fixture and storage policy is approved before raw data, generated outputs,
   notebook outputs, hosted exports, or CSV extracts enter the repository.
5. Deterministic local reproduction is planned before trust.
6. Code is implemented only under a later scoped phase that explicitly permits
   source files, tests, fixtures, and behavior.
7. Tests enforce deterministic behavior, offline safety, and side-effect
   boundaries.
8. A result-review template records limits, non-claims, unresolved gaps, and
   what the reproduced result does not authorize.

No notebook, script, spreadsheet, vectorbt run, QuantConnect report, chart, LLM
snippet, website snippet, or hosted result can skip this path.

## Repository Placement Policy

Repository placement rules:

- Exploratory notebooks and prototype scripts should not be added unless a
  later phase explicitly approves location, ownership, metadata, storage,
  execution, and review policy.
- `docs/design` stores reviewed decisions, boundaries, normalized findings,
  and project policy.
- `docs/proposals` may later store speculative summaries if that route is
  explicitly created and scoped.
- Raw data, generated outputs, hosted exports, notebook outputs, CSV extracts,
  screenshots, and manual tables require an approved storage/fixture policy
  before entering the repository.
- `src` remains off-limits until a later scoped implementation phase
  explicitly approves production code.

## vectorbt Boundary

vectorbt may be considered for research prototyping only. It is not production
infrastructure and is not part of the trading hot path.

vectorbt output cannot validate a signal, approve thresholds, approve a source,
approve data, or create a trusted artifact unless the relevant finding is
reproduced through a project-approved deterministic workflow with reviewed data
policy and tests. No vectorbt dependency, integration, notebook, script, or
runtime behavior is added in this phase.

## QuantConnect Boundary

QuantConnect may be used as an external sandbox or reference only.
QuantConnect results are not the project source of truth.

Screenshots, backtest reports, exported metrics, settings pages, and copied
QuantConnect snippets must be treated as external artifacts under the Phase 34
intake checklist. Any useful finding must be reproduced locally before trust.
No QuantConnect dependency, SDK, integration, data route, notebook, script, or
runtime behavior is added in this phase.

## Normal Pytest Rule

Normal `python -m pytest` must remain:

- offline
- credential-free
- deterministic
- free of network calls
- free of SDK or external platform calls
- free of notebook or prototype runtime dependencies
- free of data acquisition, data ingestion, or downloads
- free of broker, OMS, runtime, scheduler, persistence, portfolio, ledger,
  reconciliation, Alpaca, vectorbt, QuantConnect, ML, LLM runtime, or
  trading-path behavior

Any future integration tests involving notebooks, prototype tools, hosted
platforms, SDKs, data downloads, network, or credentials must be explicitly
gated and skipped by default.

## Recommended Next Routing

Recommended next docs-only gate: return to the Phase 33 data storage/fixture
policy boundary.

That gate should define how candidate source data, fixture scope, provenance,
hashing, versioning, exclusions, and offline replay would be controlled before
any data acquisition, ingestion, reproduction, backtest, schema, evaluator,
signal implementation, or trading-path work is considered.

## Explicit Non-Goals

This phase does not perform or authorize:

- implementation
- dependencies
- dependency lockfile changes
- notebooks
- scripts
- data acquisition
- data ingestion
- dataset addition
- schema or code
- backtest
- reproduction
- vectorbt integration
- QuantConnect integration
- LLM runtime integration
- evaluator or signal implementation
- signal computation
- signal scoring, ranking, direction, confidence, or actionability
- `ValidatedResearchArtifact`
- `ValidatedSignalDefinition`
- production threshold
- profitability claim
- trading implication

## Remaining Blockers

Evaluator implementation, validation, reproduction, production routing, and
trading use remain blocked by all of the following:

- no approved notebook/prototype integration
- no approved vectorbt integration
- no approved QuantConnect integration
- no approved data storage/fixture policy
- no approved Phase 33 source/universe/benchmark/cash proxy
- no project-local deterministic reproduction
- no no-lookahead audit
- no implementation-scope approval
- no evaluator tests
- no approved source/data approval route from exploratory artifacts
- no approved terms/license route for external data or hosted outputs
- no approved result-review template for reproduced outputs
- no promotion/rejection decision for any specific exploratory artifact
- no trading implication or production threshold
