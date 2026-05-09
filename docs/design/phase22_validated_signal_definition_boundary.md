# Phase 22 Validated Signal Definition Boundary Design

## 1. Purpose

Phase 22 Step 1 defines a documentation-only boundary for future validated
signal definitions. It explains how a validated research artifact may
eventually support an approved deterministic signal definition while keeping
research, backtests, ML, LLMs, and exploratory workflows out of the trading hot
path.

Phase 22 Step 1 adds no production code, tests, runtime behavior, signal
computation, strategy implementation, feature computation, ranking or priority
policy, broker behavior, execution-plan mutation, order submission,
scheduler/runtime behavior, persistence implementation, live data ingestion, ML
training, or LLM trading-path logic.

Phase 22 Step 2 adds the smallest production contract for representing a
validated signal definition as metadata only. It adds no signal computation,
strategy implementation, feature computation, ranking or priority behavior,
execution-plan mutation, risk approval behavior, broker behavior, Alpaca
behavior, order submission, scheduler/runtime behavior, persistence
implementation, live data ingestion, ML training, or LLM trading-path logic.

Phase 22 Step 3 hardens `ValidatedSignalDefinition` traceability with focused
tests and documentation only. It changes no production source and adds no new
signal behavior.

The core rule is:

```text
Research artifacts can support a definition.
A validated signal definition can describe a deterministic rule.
Only a future deterministic evaluator can produce signal outputs.
```

## 2. What A Validated Signal Definition Is

A validated signal definition is a reviewed, versioned contract that describes
one deterministic signal rule approved for a narrow advisory use. It is not the
rule implementation itself unless a later phase explicitly adds code. It is not
a live recommendation, not a trade approval, and not an execution instruction.

A future signal definition may document:

- what inputs are required
- what deterministic rule should be evaluated
- what output shape a future evaluator may produce
- which validated research artifact supports the definition
- which assumptions and limitations apply
- which validation evidence should remain traceable

The definition is a bridge from validated evidence to future deterministic
signal code. It must remain explicit, reviewed, versioned, and testable before
it can influence any signal-to-risk flow.

## 3. What It Is Not

A validated signal definition differs from raw research output. Raw research
may include notebooks, exploratory scripts, charts, ad hoc DataFrame pipelines,
backtest experiments, and written hypotheses. Those outputs are advisory until
reviewed and promoted.

A validated signal definition differs from a backtest result. A backtest result
is evidence about historical behavior under stated assumptions. It is not a
runtime rule and must not be wired into execution flow as a decision source.

A validated signal definition differs from a feature. A feature is an input or
computed value used by a rule. A signal definition describes how approved
inputs may be evaluated to produce a deterministic signal output in a future
evaluator.

A validated signal definition differs from a strategy. A strategy may combine
signals, sizing, risk constraints, portfolio context, execution preferences,
and scheduling decisions. A signal definition is narrower: it describes one
signal rule and its metadata, not an end-to-end trading system.

A validated signal definition differs from an execution intent.
`ExecutionIntent` is an internal pre-submission wrapper for a risk-approved
source row. A signal definition must not produce or mutate execution intents.

A validated signal definition differs from an execution plan. `ExecutionPlan`
is a pre-broker batch container for execution intents. A signal definition must
not create, rank, cap, mutate, or submit execution plans.

A validated signal definition differs from a broker order. A broker order is a
broker-facing or broker-native request. A signal definition must not contain
order fields, broker fields, Alpaca fields, submission behavior, fill data, or
portfolio mutation behavior.

## 4. Future Metadata Shape

A future validated signal definition may contain metadata such as:

- signal id
- name
- version
- description
- source validated research artifact id
- source validated research artifact version
- required inputs
- output type
- deterministic evaluation rule reference
- allowed advisory use
- assumptions
- limitations
- validation evidence reference

This metadata should stay descriptive and deterministic. It should identify the
rule and its evidence, not execute the rule.

Phase 22 Step 2 introduces this minimal metadata-only contract in
`src/algotrader/signals/validated_signal_definition.py`:

```text
ValidatedSignalDefinition(
    signal_id,
    name,
    version,
    description,
    source_artifact_id,
    source_artifact_version,
    required_inputs,
    output_type,
    evaluation_rule_ref,
    approved_for,
    assumptions,
    limitations,
)
```

The contract is immutable and slotted. Iterable fields are stored as immutable
tuples and preserve input order. Required strings reject empty values. The
contract references validated research artifacts only by stable id/version
strings; it does not import research behavior or hold a research artifact
object.

Phase 22 Step 3 hardens that source-artifact traceability and ordering
contract. The tests prove that `source_artifact_id` and
`source_artifact_version` are preserved exactly, `required_inputs`,
`approved_for`, `assumptions`, and `limitations` preserve deterministic order,
tuple fields cannot be mutated after construction, and the object remains
metadata-only.

## 5. Fields And Behavior That Must Not Appear

A validated signal definition must not contain:

- symbol-specific live recommendation
- side
- quantity
- order type
- broker fields
- Alpaca fields
- `submit_order`
- cash reservation
- buying-power reservation
- portfolio mutation
- risk approval
- ranking or priority behavior
- execution-plan mutation
- fills
- LLM-generated trade decisions

It also must not contain broker order IDs, client order IDs, idempotency keys,
venue routing fields, live account state, position mutation fields, scheduler
state, persistence handles, model prompts, model completions, or runtime
credentials.

## 6. Promotion Path

The intended promotion path is:

```text
research hypothesis
  -> validated research artifact
  -> approved signal definition
  -> future deterministic signal evaluator
  -> future signal-to-risk flow
```

Each transition should be explicit and reviewed:

1. Research proposes a hypothesis and records evidence.
2. Validation promotes reviewed evidence into a validated research artifact.
3. A human-approved design phase promotes a narrow rule into an approved signal
   definition.
4. A later implementation phase adds deterministic contracts/types before
   runtime wiring.
5. A later evaluator applies the deterministic rule to explicit inputs.
6. Only future signal outputs may enter a future Signal -> Risk boundary, and
   only after tests prove the evaluator is deterministic, offline, and free of
   research, ML, LLM, broker, scheduler, and persistence dependencies.

Backtests and validated artifacts remain advisory until promoted through an
explicit signal definition and a deterministic evaluator.

## 7. Bias And Leakage Controls

Validated signal definitions should preserve evidence that common research
failure modes were controlled before any deterministic evaluator is built.

Lookahead bias controls:

- define when each required input becomes available
- ensure feature windows use only data available at evaluation time
- document how revised data, corporate actions, opens, closes, and delayed data
  are handled

Survivorship bias controls:

- document the symbol universe used during validation
- distinguish current tradable universe assumptions from historical universe
  claims
- include delisted or inactive symbols when the historical claim requires them

Label leakage controls:

- keep future returns, target labels, future rankings, future fills, and future
  portfolio state out of required inputs
- document joins, timestamp alignment, and missing-data behavior
- keep validation scoring separate from future signal evaluation inputs

Retrospective parameter controls:

- version every threshold, window, rule, and assumption change
- prohibit retrospective parameter changes without a new version
- record rejected variants and failed hypotheses
- avoid cherry-picked validation periods
- separate exploratory, validation, and final holdout evidence

## 8. LLM Boundary

LLMs may assist with:

- research summaries
- hypothesis documentation
- experiment narration
- review notes
- explaining why a signal definition was proposed

LLMs may not:

- generate live signal outputs
- generate live trade decisions
- approve trades
- mutate execution plans
- bypass deterministic risk checks
- interact with brokers
- submit orders
- create fills
- mutate portfolio state

LLM output remains research or documentation commentary unless a human-reviewed
artifact and signal definition later promote a deterministic rule through
explicit contracts and tests. LLMs must remain out of the trading hot path.

## 9. Dependency Direction

The future signal-definition boundary should be upstream of signal evaluation,
risk, execution planning, brokers, runtime scheduling, persistence, ML, and LLM
services.

Allowed conceptual direction:

```text
validated research artifact metadata
  -> approved signal definition metadata
  -> future deterministic signal evaluator
  -> future Signal -> Risk flow
```

Forbidden direct dependencies for a signal definition:

- broker modules
- Alpaca modules
- execution modules
- execution-planning modules
- risk engines or risk verdicts
- portfolio modules
- scheduler/runtime modules
- persistence modules
- live data clients
- backtest engines
- ML training modules
- LLM clients or agents

## 10. Explicitly Out Of Scope

Phase 22 Step 3 does not add production source changes or:

- feature computation
- signal evaluation
- strategy engine
- backtest engine
- broker integration
- Alpaca changes
- runtime scheduling
- persistence
- live data ingestion
- ML training
- LLM trading-path logic
- ranking or priority policy
- risk approval behavior
- execution-plan mutation
- order submission
- fills
- portfolio mutation

It also does not add buy/sell/hold recommendations, symbols, sides,
quantities, order fields, broker fields, portfolio fields, risk approval
fields, execution intent fields, execution plan fields, ranking fields, score
fields, cash reservation fields, ValidatedResearchArtifact runtime object
dependencies, or runtime research behavior imports.

## 11. Future Implementation Phases

Future implementation should stay test-first and contract-first. After Phase
22 Step 3, a safe future sequence would be:

1. Add fixture-only examples linked to validated research artifact ids and
   versions.
2. Add deterministic evaluator contracts before any evaluator implementation.
3. Add focused evaluator tests with synthetic explicit inputs.
4. Only later consider connecting evaluator outputs to Signal -> Risk flow.

No future implementation should combine signal-definition work with broker
wiring, runtime scheduling, persistence, live data ingestion, ML training, or
LLM trading-path behavior.
