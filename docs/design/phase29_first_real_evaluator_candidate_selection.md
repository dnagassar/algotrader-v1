# Phase 29 First Real Evaluator Candidate Selection

## 1. Purpose

Phase 29 Step 2 is a candidate-selection phase only.

No real evaluator is implemented in this phase. No signal computation, feature
computation, strategy logic, scoring, ranking, confidence or probability,
signal direction, actionability, risk approval, execution intent creation,
execution-plan mutation, portfolio mutation, broker or Alpaca behavior, order
submission, runtime behavior, scheduler behavior, persistence writes, live data
ingestion, network calls, ML inference, or LLM trading-path logic is added.

The goal is to identify the safest first evaluator candidate and document why
it is or is not ready to proceed to a later evaluator-specific design phase.
Candidate selection does not authorize implementation. A later
evaluator-specific contract design must still satisfy the Phase 29 Step 1 gate
before production code can be considered.

## 2. Candidate-Selection Criteria

A first real evaluator candidate should satisfy all of these:

- supported by an existing or planned `ValidatedSignalDefinition`
- traceable to a `ValidatedResearchArtifact`
- uses a small number of explicit input names
- consumes deterministic scalar `SignalInputValue` values
- can be represented in a `SignalInputBundle`
- can pass `validate_signal_input_bundle_completeness(...)`
- requires no live data fetching
- requires no feature computation inside the evaluator
- requires no broker, account, or portfolio state
- requires no runtime or scheduler state
- has clear advisory output semantics
- is simple enough to test exhaustively
- has clear no-lookahead behavior
- does not require scoring, ranking, direction, confidence, or actionability
  semantics unless separately designed later

Any candidate that cannot satisfy these criteria remains deferred.

## 3. Candidate Types To Consider

Candidate categories that may be considered later, without implementation in
this phase, include:

- metadata passthrough evaluator
- threshold evaluator over one explicit scalar input
- equality or check evaluator over one explicit scalar input
- simple comparison evaluator over two explicit scalar inputs
- no-op-derived evaluator that only proves successful completeness handling
- existing momentum-related candidate only if it can be supported entirely by
  explicit precomputed inputs and existing validated contracts

A metadata passthrough evaluator is operationally safe, but it may not qualify
as the first real evaluator because it does not add meaningful deterministic
signal computation beyond the current no-op seam.

A no-op-derived completeness evaluator is similarly safe for proving input
preconditions, but it should remain a hardening or readiness step unless the
project explicitly decides that "successful completeness handling" is the first
real evaluator behavior. It does not provide a useful first advisory signal
calculation by itself.

A threshold evaluator over one explicit scalar input is the smallest candidate
that can exercise real deterministic advisory computation while staying inside
the existing explicit-input boundaries.

An equality or check evaluator over one explicit scalar input may also be safe,
but it risks being too artificial unless it maps cleanly to a validated signal
definition and research artifact.

A simple comparison evaluator over two explicit scalar inputs adds a larger
input surface and more compatibility cases, so it is a better later candidate
after one-input behavior is designed and tested.

An existing momentum-related candidate should not be selected unless all
momentum inputs are precomputed before evaluation and represented as explicit
`SignalInputValue` objects. The evaluator must not fetch bars or quotes,
calculate momentum features, rank symbols, read live market data, or consult
broker or portfolio state.

No candidate should be selected if it requires live market data, feature
computation, strategy ranking, broker state, account state, portfolio state, or
runtime state.

## 4. Candidate Types Rejected Or Deferred For Now

Candidates are rejected or deferred for now if they require:

- bar or quote fetching inside the evaluator
- feature computation inside the evaluator
- multi-symbol ranking
- portfolio exposure checks
- risk thresholds
- execution readiness
- broker or account state
- ML predictions
- LLM output
- runtime scheduling
- persistence or cache reads
- live data ingestion
- options Greeks or implied-volatility calculations unless separately designed
  and validated

These candidates may be reconsidered only after separate design phases define
their contracts, input provenance, timestamp rules, advisory semantics, and
test gates.

## 5. Recommended First Candidate

The recommended first future real evaluator candidate is a minimal
threshold-style advisory evaluator over one explicit scalar `SignalInputValue`.

Candidate concept:

- required input name: one explicit scalar value such as `indicator_value`
- comparator and threshold semantics: documented later, not implemented now
- output: advisory `SignalEvaluationResult`
- no trade direction
- no confidence
- no probability
- no ranking
- no actionability
- no live data fetching
- no feature computation
- no risk approval
- no execution behavior

This phase does not select the exact validated signal definition, supporting
research artifact, input name, accepted value type, threshold, comparator,
reason codes, or output-value meaning. Those details belong to the next
evaluator-specific design phase.

This recommendation is a candidate selection only. It does not authorize
production code.

## 6. Why This Candidate Is Safe

The threshold-over-one-explicit-scalar candidate is safer than the alternatives
because it has:

- a small input surface
- deterministic scalar values
- no hidden data access
- easy missing-input behavior
- easy no-lookahead testing
- clear advisory-only output
- no ranking
- no portfolio dependence
- no broker dependence
- no account dependence
- no runtime or scheduler dependence
- no persistence dependence
- no ML or LLM dependence

It also keeps feature preparation outside the evaluator. A future evaluator
would receive an already observed scalar value through `SignalInputValue` and
would not fetch, calculate, normalize, or infer upstream market features.

Compared with a metadata passthrough or no-op-derived completeness evaluator,
the threshold candidate is closer to a real advisory calculation. Compared with
two-input comparison, momentum, ranking, risk-aware, or portfolio-aware
candidates, it has fewer paths for hidden data access, lookahead bias, or
trading-path leakage.

## 7. What Remains Unresolved Before Implementation

A later evaluator-specific design phase must answer:

- exact `ValidatedSignalDefinition` identity and version
- exact supporting `ValidatedResearchArtifact` identity and version
- exact input names
- exact accepted value types
- threshold or comparison semantics, if any
- `output_value` meaning
- `reason_code` meanings
- diagnostics, assumptions, and limitations
- missing-input behavior
- extra-input behavior
- snapshot id compatibility
- `as_of` compatibility
- whether completeness result is passed in or recomputed internally
- exact no-lookahead tests
- exact forbidden-field tests

Until those questions are answered, implementation remains out of scope.

## 8. Required Future Tests Before Implementation

A future evaluator-specific implementation must include tests for:

- required input names
- complete input bundle behavior
- missing input behavior
- extra input behavior
- deterministic repeated results
- exact traceability preservation
- `as_of` and `evaluated_at` validation
- `evaluated_at >= as_of`
- no-lookahead rejection
- no hidden wall-clock access
- no random behavior
- no environment-variable reads
- no network or socket access
- no file, database, or cache writes
- no broker or Alpaca imports
- no runtime or scheduler imports
- no persistence imports
- no ML or LLM imports
- no risk or execution imports
- no forbidden output fields
- no mutation of input contracts

These tests must run in normal pytest without credentials, live services,
broker accounts, paper trading opt-ins, network access, model services, or LLM
clients.

## 9. Relationship To Existing Contracts

`ValidatedResearchArtifact` is the supporting evidence boundary. The selected
candidate still needs a specific artifact before implementation. Research
metadata is evidence only and does not compute signals or approve trades.

`ValidatedSignalDefinition` is the promoted signal metadata boundary. The
candidate still needs a specific definition before implementation. The
definition may describe the advisory signal, but it does not execute the
calculation by itself.

`SignalEvaluationInputSnapshot` names the required inputs and preserves
reference metadata. The candidate should use a small required-name set, ideally
one input name for the first evaluator-specific design.

`SignalInputValue` carries the explicit observed scalar value. The recommended
candidate consumes one such value and does not fetch or compute the value
inside the evaluator.

`SignalInputBundle` groups explicit input values, preserves ordering and object
identity, rejects duplicate names, validates bundle `as_of`, and rejects values
observed after bundle `as_of`. The recommended candidate should be representable
as a bundle containing the one required value.

`SignalInputBundleCompletenessResult` records metadata-only name completeness.
The later evaluator-specific design must decide whether the evaluator receives
this result or recomputes completeness internally.

`validate_signal_input_bundle_completeness(...)` compares required names to
bundle value names only. The recommended candidate should be able to pass this
validation with one required name and one matching bundle value.

`SignalEvaluationResult` is the advisory output contract. The recommended
candidate may eventually produce it, but the result remains pre-risk and is not
a recommendation, risk approval, execution intent, order request, broker
payload, or portfolio decision.

`NoOpSignalEvaluator` proves the evaluator-shaped input/output seam without
real computation. The recommended candidate should reuse the same safety
posture but add only the smallest deterministic advisory calculation after a
later design phase approves it.

Deterministic time contracts provide UTC-aware timestamp validation,
fixed-clock testing support, and lookahead helpers. The future evaluator must
use explicit `as_of` and `evaluated_at` values and must not call wall-clock APIs
internally.

## 10. Explicitly Out Of Scope

Phase 29 Step 2 does not add:

- evaluator implementation
- evaluator protocol
- signal computation
- feature computation
- strategy logic
- score, direction, confidence, or actionability
- ranking or probability
- signal-to-risk conversion
- risk approval
- execution intent creation
- execution-plan mutation
- portfolio mutation
- broker or Alpaca behavior
- order submission
- runtime or scheduler behavior
- persistence
- live data ingestion
- ML or LLM trading-path behavior

Normal pytest must remain offline, credential-free, and safe.

## 11. Non-Binding Future Phase Sketch

Possible future phases include:

1. Phase 29 Step 3: first real evaluator candidate contract design, docs-only.
2. Phase 29 Step 4: first real evaluator test matrix, tests/docs only if
   possible.
3. Phase 29 Step 5: minimal evaluator implementation only if the gate and
   design are satisfied.
4. Phase 29 Step 6: evaluator traceability/no-lookahead hardening.

This sketch is non-binding. Any future work must remain contract-first,
test-first, deterministic, offline-safe, credential-free, broker-isolated,
advisory, pre-risk, and outside the LLM trading hot path.
