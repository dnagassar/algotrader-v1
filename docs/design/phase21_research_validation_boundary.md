# Phase 21 Research/Validation Boundary Design

## 1. Purpose

Phase 21 Step 1 defines a documentation-only boundary for how historical
research, validation, feature work, backtesting, and approved research signals
may eventually feed the deterministic trading core.

Phase 21 Step 2 adds the smallest production contract for representing a
validated research artifact as metadata and evidence only. It adds no runtime
wiring, strategy implementation, feature computation, backtest engine, live
data ingestion, ML training, broker behavior, execution-plan mutation, order
submission, scheduler/runtime behavior, persistence implementation, or LLM
trading-path logic.

The core rule is:

```text
Research can propose.
Validation can approve.
The deterministic core can consume only explicit approved inputs.
```

Backtests, notebooks, research scripts, and LLM-assisted summaries are advisory
until a later implementation promotes their outputs through explicit
deterministic contracts.

## 2. Current System Context

The current trading core is deterministic, offline-safe in normal tests, and
broker-isolated. It works from explicit `Bar + Quote` inputs through signal,
risk, execution-intent, execution-plan, and planning-policy boundaries without
calling live brokers, schedulers, model services, or external network state.

The current pre-broker orchestration path is intentionally narrow:

```text
Synthetic Bar + Quote candidates
  -> deterministic screener output
  -> deterministic signal evaluation
  -> deterministic risk evaluation
  -> risk-approved row selection
  -> ExecutionIntent construction
  -> ExecutionPlan construction
  -> deterministic planning policy
  -> future broker-facing request construction
```

Phase 21 does not move that path. It documents how future research work may
produce evidence and candidate definitions without becoming trading behavior by
accident.

## 3. Research vs Validation vs Deterministic Core

### Research Layer

The research layer is where ideas are explored. It may include historical data
exploration, feature research, backtesting, walk-forward validation, regime
analysis, strategy notebooks, ad hoc scripts, experiment journals, and
LLM-assisted research summaries.

Research may generate hypotheses, candidate features, candidate signals,
backtest reports, charts, notebooks, and written analysis. Research output is
not trading logic. It must not directly import into the deterministic core,
mutate execution plans, approve orders, or interact with brokers.

### Validated Artifacts Layer

The validated artifacts layer is where research results become explicit,
reviewable records. It may contain approved feature definitions, approved signal
definitions, validated strategy configs, documented assumptions, evaluation
metrics, acceptance criteria, versioned research outputs, and review notes.

Validated artifacts are still not runtime behavior by themselves. They are the
evidence package used to justify a later deterministic implementation.

Phase 21 Step 2 introduces this minimal metadata-only contract in
`src/algotrader/research/validated_artifact.py`:

```text
ResearchMetric(name, value)

ValidatedResearchArtifact(
    artifact_id,
    name,
    version,
    description,
    validated_at,
    metrics,
    assumptions,
    limitations,
    approved_for,
)
```

The contract is immutable and slotted. Tuple fields are stored immutably and
preserve input order. Required strings reject empty values. The artifact does
not create signals, approve trades, mutate execution plans, interact with
brokers, ingest live data, persist records, or put LLMs in the trading hot path.

Phase 21 Step 3 hardens this traceability contract with focused tests and
documentation only. The hardened tests prove that `ResearchMetric` object
identity is preserved inside `ValidatedResearchArtifact.metrics`, metrics,
assumptions, limitations, and approved advisory uses preserve deterministic
order, tuple fields cannot be mutated after construction, and the artifact
does not expose trading-path fields or depend on broker, execution,
orchestration, runtime, scheduler, persistence, Alpaca, ML, LLM, execution
planning, or risk-evaluation types.

### Deterministic Core

The deterministic core consumes only approved, explicit, validated inputs. It
must remain offline-safe in normal tests, credential-free by default,
broker-isolated, and dependency-direction safe.

The core must not directly depend on notebooks, exploratory scripts,
backtesting engines, data-mining tools, LLM clients, live data ingestion, or ML
training workflows. Any future research-derived behavior must enter through
small deterministic contracts, types, configs, fixtures, and pure functions
that can be tested without credentials or network access.

## 4. Allowed Research Activities

Allowed research activities include:

- historical data exploration
- feature research and candidate feature comparison
- strategy notebooks and scripts
- backtesting with documented assumptions
- walk-forward validation
- regime analysis
- sensitivity analysis
- robustness checks
- transaction-cost and slippage assumptions
- experiment journaling
- LLM-assisted hypothesis generation
- LLM-assisted research narration and summaries
- post-experiment explanation of what changed and why

These activities may use tools and dependencies that are inappropriate for the
deterministic core, but they must remain outside the trading hot path.

Research outputs must be recorded as advisory evidence. They cannot directly
cause order approval, execution-plan mutation, broker submission, or portfolio
mutation.

## 5. Validated Artifact Requirements

A research output should not be considered eligible for deterministic
implementation until it has a reviewed artifact package.

Minimum validated artifact contents should include:

- a stable artifact identifier and version
- the research question or hypothesis
- the dataset identifiers, date ranges, symbols, and selection rules
- feature definitions with exact formulas and input requirements
- signal definitions with exact trigger rules and thresholds
- strategy configuration values with units and bounds
- assumptions for spreads, fees, slippage, liquidity, and execution timing
- train, validation, test, and walk-forward period definitions where relevant
- market-regime definitions or the reason regime analysis was not used
- evaluation metrics and acceptance criteria
- benchmark or baseline comparisons
- failure cases and rejected variants
- evidence that lookahead bias, survivorship bias, overfitting, data leakage,
  and hindsight-driven changes were considered
- reviewer notes and approval status

The artifact package must make clear whether a result is experimental,
validated for further engineering, approved for deterministic implementation,
or rejected.

## 6. Promotion Path From Research To Deterministic Core

Promotion should be explicit and staged:

1. Record the research output with versioned assumptions, metrics, and source
   data references.
2. Review the output against acceptance criteria and bias controls.
3. Approve a narrow feature, signal, or strategy config as a validated artifact.
4. Design the deterministic contract before runtime wiring.
5. Add tests first for the contract, edge cases, dependency direction, and
   offline behavior.
6. Implement the smallest pure deterministic function or type needed.
7. Keep runtime/broker wiring in a later explicitly approved phase.

What may cross into the deterministic core:

- approved feature definitions with exact formulas
- approved signal definitions with exact deterministic rules
- validated strategy config values
- bounded deterministic parameters
- documented assumptions that are encoded as explicit config or tests
- validated research artifact metadata used for traceability
- small fixture data needed for deterministic tests
- version identifiers for traceability

What must never cross directly into the deterministic core:

- notebooks
- exploratory scripts
- ad hoc DataFrame pipelines
- mutable research objects
- raw backtest result blobs as decision inputs
- unreviewed feature or signal definitions
- validated artifact metadata as direct signal-generation behavior
- validated artifact metadata as risk approval
- live data clients
- broker clients or broker credentials
- LLM prompts, completions, agents, tool calls, or approvals
- ML training jobs or training-time model objects
- scheduler/runtime loops
- persistence writers
- order submission behavior

Backtests and research outputs remain advisory until promoted through explicit
deterministic interfaces.

## 7. Bias And Leakage Controls

Future research must record controls for common failure modes before a signal
or strategy can affect execution flow.

Lookahead bias controls:

- define the timestamp at which each input becomes available
- avoid using revised future data for past decisions unless explicitly modeled
- ensure feature windows use only information available at the decision time
- test boundary timestamps around opens, closes, and corporate events

Survivorship bias controls:

- document symbol universe construction
- include delisted or inactive symbols when the claim depends on a historical
  universe
- distinguish current tradable universe tests from historical universe tests

Overfitting controls:

- separate exploratory, validation, and final holdout periods
- limit repeated threshold tuning on the same validation period
- record rejected variants and failed hypotheses
- compare against simple baselines
- require robustness checks across periods, symbols, and regimes

Data leakage controls:

- prevent target labels, future returns, future fills, or future rankings from
  entering features
- record joins and alignment rules
- test missing data and delayed data behavior
- keep evaluation code separate from feature computation contracts

Hindsight-driven strategy change controls:

- record strategy changes before re-running evaluation
- version every material definition change
- avoid changing rules after seeing out-of-sample failures without creating a
  new experiment record
- keep rejected or superseded configurations traceable

## 8. LLM Boundary

LLMs may assist with:

- research narration
- experiment summaries
- hypothesis generation
- journaling
- literature or documentation summaries
- explaining charts and backtest reports for human review

LLMs must not:

- generate live trade decisions
- mutate execution plans
- approve orders
- bypass risk checks
- create or modify broker-facing requests
- interact with brokers
- consume live account state in the trading path
- write portfolio mutations
- decide whether an order should be submitted
- replace deterministic acceptance criteria

LLM output is research commentary unless a human-approved artifact later
promotes a deterministic rule through explicit contracts and tests. The trading
hot path must remain free of LLM, LangGraph, LangChain, OpenAI, Anthropic, or
similar model-service dependencies.

## 9. Explicitly Out Of Scope

Phase 21 Step 3 does not add production source changes or design runtime
behavior for:

- broker behavior
- Alpaca changes
- `submit_order`
- scheduler/runtime loops
- persistence implementation
- idempotency or `client_order_id`
- cash reservation
- same-symbol conflict policy
- duplicate or competing order policy
- priority/ranking implementation
- portfolio mutation
- fills
- ML training implementation
- live data ingestion
- LLM trading-path logic
- changes to `src/`

It also does not approve any specific feature, signal, strategy, dataset,
backtest engine, validation framework, notebook layout, storage mechanism, or
artifact registry implementation.

## 10. Future Implementation Phases

Future implementation should be test-first and should begin with contracts and
types before runtime wiring.

Safe later phases could include:

- a documented research artifact schema
- versioned feature-definition records
- versioned signal-definition records
- deterministic tests for approved feature formulas
- deterministic tests for approved signal rules
- validation report fixtures for documentation examples
- dependency-direction tests that keep research tools out of `src/algotrader`
- explicit promotion metadata linking deterministic code to reviewed artifacts

Unsafe shortcuts to avoid:

- wiring a backtest result directly into execution flow
- letting notebooks import or mutate production execution plans
- treating LLM summaries as approvals
- tuning thresholds after seeing final-period failures without a new artifact
- adding live data ingestion before deterministic contracts exist
- combining research promotion with broker submission work

Research should make the system smarter over time, but only through deliberate,
reviewed, deterministic boundaries.
