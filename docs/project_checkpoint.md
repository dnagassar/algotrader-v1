# Project Checkpoint

## Current Milestone

The project is at the 5757-passed / 4-skipped deterministic core checkpoint. The
current system prioritizes a deterministic trading core before any real broker
connectivity.

Recent focused validation included broker/idempotency, LocalBroker rename/import,
cleanup/import suites, a shared broker-contract subset, and pre-SDK Alpaca
safety gates. Phase 1 now adds a file-scoped Alpaca SDK wrapper boundary without
real broker connectivity. A pre-Phase-2 hardening pass adds a paper URL
invariant, `paper_integration` gate tests, broader credential redaction
coverage, offline SDK factory-construction coverage, and one skipped-by-default
read-only Phase 2 paper account smoke test. Phase 3 adds one skipped-by-default
read-only account translation smoke test through the SDK wrapper, adapter,
translator, mapper, and internal `Account` path. Phase 4 adds one
skipped-by-default read-only positions translation smoke test through the same
adapter, translator, mapper, and internal `Position` path. Phase 5 documents
reconciliation-readiness policy before implementation. Phase 6 hardens
fake-only reconciliation through the Alpaca adapter path, unavailable broker
call handling, and conservative report-only tolerances. Phase 7 real-paper
reconciliation remains explicitly deferred. Phase 8 begins with a deterministic
offline screener foundation that ranks synthetic `Bar + Quote` inputs by ask
momentum versus previous close. Phase 9 adds optional deterministic screener
filters for `min_score` and `top_n` while preserving Phase 8 defaults. Phase 10
is a no-code design-only pass documenting the future Screener -> Signals bridge.
Phase 11 begins that bridge with a pure orchestration-owned adapter that
preserves screener ordering and returns signal-ready `Bar + Quote` pairs without
invoking signals yet. Phase 11 Step 2 hardens the bridge by rejecting duplicate
screener result symbols and malformed result/candidate inputs while preserving
the original `Bar` and `Quote` objects in immutable ordered pairs. Phase 11 Step
3 adds pure screener-ordered signal evaluation only; any signal output is not an
approved trade and is not submitted. Phase 12 is a no-code design-only pass
documenting the future Signal -> Risk boundary before any risk integration is
implemented. Phase 13 hardens the screener-ordered signal evaluation contract
with focused unit tests only. Phase 14 Step 1 adds test-only dependency
direction guardrails before any Signal -> Risk runtime code exists. Phase 14
Step 2 adds pure Signal -> Risk evaluation that stops at deterministic risk
verdicts. Phase 15 is a no-code design-only pass documenting the future Risk
-> Execution boundary before any execution integration is implemented. Phase 16
Step 1 adds test-only Risk -> Execution dependency guardrails before any
execution bridge exists. Phase 16 Step 2 adds a pure risk-approved row selector
that returns only `risk_approved` `SignalRiskEvaluation` rows while preserving
input order and object identity. Phase 17 Step 1 is a no-code design-only pass
documenting the future internal execution-intent boundary after risk-approved
selection. No runtime behavior changed, and risk-approved rows remain
permission signals only. Phase 17 Step 2 adds a minimal internal
`ExecutionIntent` contract and pure builder that wrap risk-approved source rows
by identity before any broker, execution adapter, scheduler, persistence, or
live trading behavior. Phase 17 Step 3 hardens execution-intent traceability
with tests and documentation only; `ExecutionIntent` remains source-only,
pre-submission, and not executable by itself. Phase 18 Step 1 is a no-code
execution-planning boundary design phase after `ExecutionIntent` construction.
Execution planning is conceptual only and no runtime behavior changed. Phase 18
Step 2 adds a minimal immutable `ExecutionPlan` batch container and pure
builder while leaving all execution-planning policy unresolved. Phase 18 Step 3
hardens `ExecutionPlan` traceability with tests and documentation only. Phase 19
Step 1 is a no-code execution-planning policy design phase. It designs the
future policy layer conceptually while leaving `ExecutionIntent` source-only,
`ExecutionPlan` as a minimal immutable batch container, and runtime behavior
unchanged. Phase 19 Step 2 adds the minimal immutable
`PlanningPolicyResult` / `SkippedExecutionIntent` boundary and a no-op
pass-through policy. Phase 19 Step 3 hardens planning-policy-result
traceability with tests and documentation only. Phase 20 Step 1 is a no-code
design phase for a future maximum accepted intents per plan policy. Runtime
behavior is unchanged: `PlanningPolicyResult` remains a pre-broker result
container, `apply_noop_execution_planning_policy(...)` remains pass-through
only, and the max-intents policy is designed conceptually but not implemented.
Phase 20 Step 2 adds the first real planning policy:
`MaxAcceptedIntentsPolicyConfig`,
`MAX_INTENTS_PER_PLAN_EXCEEDED_REASON`, and
`apply_max_intents_execution_planning_policy(...)`. The policy requires an
explicit positive integer cap, rejects `bool` and `None`, accepts the first `N`
intents, skips the rest with deterministic reason text, and preserves intent
and source-evaluation identity.
Phase 20 Step 3 hardens max-intents traceability with tests and documentation
only. It adds no production source changes and confirms accepted/skipped
identity, ordering, deterministic skip reasons, source-evaluation reachability,
input plan non-mutation, and absence of forbidden policy leakage fields.
Phase 21 Step 1 is a documentation-only research/validation boundary design.
It records how future historical research, validation, backtesting, features,
approved research signals, and LLM-assisted research narration may eventually
feed the deterministic core only through explicit validated contracts. No
production behavior changed. Phase 21 Step 2 adds the minimal immutable,
slotted validated research artifact metadata contract. The contract is evidence
only; it does not create signals, approve trades, mutate execution plans, or
touch brokers, runtime, persistence, live data, ML, or LLM trading-path logic.
Phase 21 Step 3 hardens validated research artifact traceability with tests
and documentation only; no production source changed.
Phase 22 Step 1 is a documentation-only validated signal definition boundary
design. It defines how validated research artifact metadata may eventually
support an approved deterministic signal definition without adding signal
computation, strategy behavior, broker behavior, execution-plan mutation,
runtime wiring, persistence, ML, or LLM trading-path logic.
Phase 22 Step 2 adds the minimal immutable, slotted validated signal definition
metadata contract. It does not evaluate signals, create execution intents,
approve trades, mutate execution plans, or touch broker, Alpaca,
scheduler/runtime, persistence, live data, ML, or LLM trading-path logic.
Phase 22 Step 3 hardens validated signal definition traceability with tests and
documentation only; no production source changed.
Phase 23 Step 1 is a documentation-only signal evaluation, clock, and as-of
boundary design. It defines how a future deterministic evaluator may consume
validated signal definition metadata plus explicit input snapshots while
preventing lookahead bias and keeping evaluations advisory, reproducible,
clock-explicit, broker-free, risk-approval-free, execution-free, and LLM-free
in the trading hot path.
Phase 23 Step 2 adds a minimal deterministic time contract:
`require_utc_datetime(...)`, `Clock`, `FixedClock`, and
`assert_not_after_as_of(...)`. It validates explicit UTC-aware datetimes,
provides an injectable fixed clock for deterministic tests, and adds a tiny
lookahead-prevention helper without evaluating signals, reading system time,
fetching live data, approving trades, mutating execution plans, touching
brokers, or adding scheduler/runtime behavior.
Phase 23 Step 3 hardens clock/timestamp traceability with tests and
documentation only. It changes no production source and pins UTC-aware
timestamp identity, repeated fixed-clock identity, immutability, naive and
non-UTC rejection, lookahead prevention, dependency independence, absence of
trading-path fields, and absence of hidden nondeterministic API calls.
Phase 24 Step 1 is a documentation-only `SignalEvaluationResult` boundary
design. It defines future advisory deterministic signal-evaluation output while
keeping signal evaluation separate from risk approval, execution intent
creation, execution planning, broker requests, portfolio mutation, ranking or
priority decisions, and LLM trading-path logic.
Phase 24 Step 2 adds the minimal immutable `SignalEvaluationResult` advisory
metadata contract. It validates explicit UTC-aware `as_of` and `evaluated_at`
timestamps, preserves deterministic trace fields and ordered tuple metadata,
and still does not evaluate signals, create execution intents, approve trades,
mutate execution plans, touch brokers, or add runtime behavior.
Phase 24 Step 3 hardens `SignalEvaluationResult` traceability with tests and
documentation only. It changes no production source and pins datetime identity,
tuple ordering and immutability, exact trace string preservation, advisory-only
surface area, forbidden trading-path field absence, and dependency isolation.
Phase 25 Step 1 is documentation-only. It records the future deterministic
signal evaluator boundary and states that no evaluator exists yet, signal
evaluation remains advisory and pre-risk, no production source or runtime
behavior changed, and LLMs remain outside the trading hot path.
Phase 25 Step 2 adds only a minimal immutable signal-evaluation input
snapshot/reference contract. It provides deterministic input traceability for a
future evaluator and still adds no evaluator, signal computation, live data
access, risk approval, execution behavior, broker behavior, runtime behavior,
persistence, ML, or LLM trading-path logic.
Phase 25 Step 3 hardens `SignalEvaluationInputSnapshot` traceability with
tests and documentation only. It changes no production source and adds no
production behavior. The snapshot remains metadata/reference-only and exists
only to provide deterministic input traceability for a future evaluator.
Phase 26 Step 1 is documentation-only. It records the future no-op signal
evaluator boundary and states that no evaluator implementation exists yet,
evaluator output remains advisory and pre-risk, no production source or runtime
behavior changed, no runtime or trading-path behavior was added, and LLMs
remain outside the trading hot path.
Phase 26 Step 2 reviews `SignalEvaluationResult` no-op readiness and concludes
the existing metadata-only result contract is sufficient for a future minimal
no-op evaluator. It adds no production source changes, no result contract
changes, no no-op marker, no evaluator implementation, no runtime behavior, and
no trading-path behavior. Focused tests now pin that no score, direction,
confidence, actionability, result-kind, evaluator-kind, risk, execution,
broker, runtime, persistence, ML, or LLM fields are present.
Phase 26 Step 3 adds the minimal frozen, slotted `NoOpSignalEvaluator`
contract as the first evaluator-shaped code. It only constructs advisory
`SignalEvaluationResult` metadata from explicit deterministic inputs and adds
no real signal computation, feature computation, scoring, ranking, direction,
actionability, risk approval, execution behavior, broker behavior, runtime
behavior, persistence, live data access, ML, or LLM trading-path logic.
Phase 26 Step 4 hardens `NoOpSignalEvaluator` traceability with tests and
documentation only. It adds no production behavior. The evaluator remains
deterministic and advisory-only, proves the evaluator input/output boundary
without real signal computation, and preserves traceability without
actionability.
Phase 27 Step 1 is documentation-only. It records admission criteria for any
future real deterministic signal evaluator and states that no real evaluator or
signal computation may be added until an explicit deterministic input-value
contract, timestamp/lookahead rules, advisory output semantics, and
side-effect/dependency guardrails are documented and implemented.
Phase 27 Step 2 is documentation-only. It records the future deterministic
signal input-value boundary and states that no input-value contract exists yet,
`SignalEvaluationInputSnapshot` remains reference metadata only, and no real
evaluator or signal computation was added.
Phase 27 Step 3 adds the minimal immutable `SignalInputValue` contract. It
carries one explicit observed value with UTC-aware timestamp and source
traceability only, and adds no real evaluator, signal computation, feature
computation, scoring, ranking, direction, actionability, risk approval,
execution behavior, broker behavior, runtime behavior, persistence, ML, or LLM
trading-path logic.
Phase 27 Step 4 hardens `SignalInputValue` traceability with tests and
documentation only. It adds no production behavior. The contract remains
immutable, scalar-only, non-computational, and isolated from trading-path
behavior.
Phase 28 Step 1 is documentation-only. It records the future signal input
bundle boundary and states that no bundle contract, real evaluator, signal
computation, production code, or runtime behavior was added.
Phase 28 Step 2 adds the minimal immutable `SignalInputBundle` contract. It
groups explicit `SignalInputValue` objects for future evaluator use, preserves
ordering and input value identity, rejects duplicate names, and rejects
lookahead values where `observed_at > as_of`. It does not validate
completeness against `SignalEvaluationInputSnapshot`, compute features or
signals, implement a real evaluator, score, rank, infer direction, recommend
trades, approve risk, mutate execution plans, access live data, route to
brokers, submit orders, use scheduler/runtime/persistence behavior, run ML, or
use LLMs in the trading path.
Phase 28 Step 3 hardens `SignalInputBundle` traceability with tests and
documentation only. It adds no production behavior. The bundle remains an
immutable grouping contract for explicit `SignalInputValue` objects, preserves
value ordering and object identity, rejects duplicate names and lookahead
values, and still does not validate completeness or interpret values.
Phase 28 Step 4 is documentation-only. It records the future completeness
validation boundary between `SignalEvaluationInputSnapshot.required_input_names`
and `SignalInputBundle.values`. No production code or runtime behavior changed,
and no completeness validator, real evaluator, or signal computation was added.
Phase 28 Step 5 adds the minimal immutable
`SignalInputBundleCompletenessResult` contract and pure
`validate_signal_input_bundle_completeness(...)` function. It compares required
snapshot input names with bundle value names only, reports missing and extra
names deterministically, keeps extra inputs non-failing in this phase, and adds
no real evaluator or signal computation.
Phase 28 Step 6 hardens completeness validation traceability with tests and
documentation only. No production source or runtime behavior changed.
Completeness validation remains name-only, metadata-only, deterministic,
non-mutating, separate from `SignalInputBundle` construction, and isolated from
trading-path behavior.
Phase 29 Step 1 is documentation-only. It defines the first real evaluator
design gate and states that no real evaluator or signal computation may be
implemented until a future evaluator-specific design explicitly satisfies the
gate. No production code, runtime behavior, real evaluator, signal
computation, or trading-path behavior was added.
Phase 29 Step 2 is documentation-only. It selects a first real evaluator
candidate for later design: a minimal threshold-style advisory evaluator over
one explicit scalar `SignalInputValue`. No production code or runtime behavior
changed, and no real evaluator or signal computation was added.
Phase 29 Step 3 is documentation-only. It designs the selected first evaluator
candidate contract for a future threshold-style advisory evaluator over one
explicit scalar `SignalInputValue`. No production code or runtime behavior
changed, and no real evaluator or signal computation was added.
Phase 29 Step 4 is documentation-only. It defines the first real evaluator
test matrix for the future threshold-style advisory evaluator. No production
code or runtime behavior changed, and no real evaluator or signal computation
was added.
Phase 29 Step 5 is documentation-only. It reviews implementation readiness and
recommends Option C: one more docs-only constants/output semantics design step
before any production evaluator implementation. No production code or runtime
behavior changed, and no real evaluator or signal computation was added.
Phase 29 Step 6 is documentation-only. It designs threshold evaluator constants
and output semantics and recommends Option B: implementation remains blocked
until exact validated signal and research artifacts are available. No
production code or runtime behavior changed, and no real evaluator or signal
computation was added.
Phase 30 Step 1 is documentation-only. It defines the threshold evaluator
research-support boundary and records the validated research artifact,
validated signal definition, and threshold value/source evidence required
before implementation. No production code or runtime behavior changed, and no
real evaluator or signal computation was added.
Phase 30 Step 5 is documentation-only. It creates an initial unreviewed
research candidate backlog only. No production code or runtime behavior
changed, and no research artifact, validated signal definition, real evaluator,
or signal computation was added.
Phase 30 Step 6 is documentation-only. It selects the first research candidate
sourcing target only. No production code or runtime behavior changed, and no
research artifact, validated signal definition, real evaluator, or signal
computation was added.
Phase 31 Step 1 is documentation-only. It adds a reusable Codex operating
context and resets the research-track workflow so future prompts can be
shorter while preserving deterministic safety gates. Docs, research, and
planning phases may now combine related documentation updates when low-risk and
code-free; production-code phases remain narrow, test-first, explicitly
scoped, and heavily verified. No production code or runtime behavior changed,
and no research artifact, validated signal definition, real evaluator, or
signal computation was added.
Phase 31 Step 2 is documentation-only. It adds a concise research-track next
action plan that turns the Phase 30 backlog and first source-selection work
into a practical sequence. `P30-BL-001` remains an unreviewed sourcing target,
backlog entries remain non-evidence, research agents may assist only with
source discovery and critique, and real evaluator implementation remains
blocked. No production code or runtime behavior changed, and no research
artifact, validated signal definition, real evaluator, or signal computation
was added.
Phase 31 Step 3 is documentation-only. It adds a normalized `P30-BL-001`
source package and updates the research-track routing docs. `P30-BL-001` is
source-package-ready only; it is not reviewed, validated, approved,
production-ready, implementation-ready, or a threshold/trading justification.
No production code or runtime behavior changed, and no research artifact,
validated signal definition, real evaluator, or signal computation was added.
Phase 31 Step 4 is documentation-only. It adds a formal Tier A source review
for `P30-BL-001` and updates the research-track routing docs. Tier A receives
a conditional mechanics and methodology outcome only. `P30-BL-001` remains
unvalidated, not approved, not production-ready, not implementation-ready, and
not a production threshold, profitability, predictive-edge, live-trading,
validated-signal-definition, or evaluator-implementation justification. No
production code or runtime behavior changed, and no research artifact,
validated signal definition, real evaluator, or signal computation was added.
Phase 31 Step 5 is documentation-only. It adds an evidence gap and routing
plan after the Tier A review. The plan preserves `P30-BL-001` as mechanics and
methodology support only, keeps the candidate unvalidated, and recommends a
formal mechanics-only candidate artifact review summary before any production
threshold, validated signal definition, or evaluator implementation route. No
production code or runtime behavior changed, and no research artifact,
validated signal definition, real evaluator, or signal computation was added.
Phase 31 Step 6 is documentation-only. It adds the formal mechanics-only
candidate artifact review summary for `P30-BL-001`. The summary conditionally
passes the candidate for mechanics and methodology only, keeps it unvalidated,
unapproved, not threshold-justified, not production-ready, and not
implementation-ready, and recommends research/data/backtesting validation
design or targeted production-threshold evidence as the next safe route if the
threshold evaluator remains the focus. No production code or runtime behavior
changed, and no research artifact, validated signal definition, real evaluator,
or signal computation was added.
Phase 31 Step 7 is documentation-only. It adds the final `P30-BL-001`
disposition, marks the candidate mechanics-only dispositioned only in the
mechanics-only sense, keeps it non-validated, not production-ready, and not
implementation-ready, and routes the next safest research direction toward
dataset-specific threshold or validation evidence. No production code or
runtime behavior changed, and no research artifact, validated signal
definition, real evaluator, signal computation, or implementation approval was
added.
Phase 32 Step 1 is documentation-only. It selects dataset-specific threshold
or validation evidence sourcing as the next research direction. `P30-BL-002`
is the current backlog routing handle only if sourcing can produce a concrete
evidence package; a better P0 replacement should be sourced first if it offers
stronger traceable dataset-specific evidence. No production code or runtime
behavior changed, and no research artifact, validated signal definition, real
evaluator, signal computation, formal review, validation, approval, promotion,
or implementation readiness was added.
Phase 32 Step 2 is documentation-only. It defines the `P30-BL-002`
source-package sourcing plan: required package fields, acceptable source
types, unacceptable source types, minimum review-readiness criteria, and
rejection/replacement criteria before any formal review can begin.
`P30-BL-002` remains a sourcing target only, and no sources were collected or
cited. No production code or runtime behavior changed, and no research
artifact, validated signal definition, real evaluator, signal computation,
formal review, validation, approval, promotion, threshold justification, or
implementation readiness was added.
Phase 32 Step 3 is documentation-only. It adds the `P30-BL-002`
source-package collection and normalization pass. The revised package
normalizes 23 candidate-only entries from the supplied Claude, Perplexity, and
Gemini/browser scout reports, deduplicates overlapping material, classifies
preliminary routing categories, and records source-level and package-level
gaps. It remains partial and requires primary-source verification before
formal review can rely on any entry. No production code or runtime behavior
changed, and no research artifact, validated signal definition, real
evaluator, signal computation, formal review, validation, approval, promotion,
threshold justification, or implementation readiness was added.
Phase 32 Step 4 is documentation-only. It adds the `P30-BL-002`
primary-source verification gate for selected high-value entries:
`P30-BL-002-S01`, `P30-BL-002-S03`, `P30-BL-002-S05`, and
`P30-BL-002-S08`. It verifies source identity and limited formal-review intake
eligibility only. No production code or runtime behavior changed, and no
research artifact, validated signal definition, real evaluator, signal
computation, formal review, validation, approval, promotion, threshold
justification, or implementation readiness was added.
Phase 32 Step 5 is documentation-only. It adds the `P30-BL-002` limited formal
review intake plan for the Step 4 selected candidates. It defines review order,
shared and source-specific criteria, possible pass/fail outcomes, required
review artifacts, non-claims, and remaining blockers. No production code or
runtime behavior changed, and no research artifact, validated signal
definition, real evaluator, signal computation, formal review, validation,
approval, promotion, threshold justification, or implementation readiness was
added.
Phase 32 Step 6 is documentation-only. It adds the `P30-BL-002-S01` formal
review and passes S01 only for limited negative-control/no-lookahead use. The
review records unresolved exact timing, dataset, code/data, and deterministic
reproduction gaps; routes the next formal review to `P30-BL-002-S03`; and does
not validate a signal, approve a threshold, create a validated artifact, create
a validated signal definition, add evaluator behavior, or authorize
implementation.
Phase 32 Step 7 is documentation-only. It adds the `P30-BL-002-S03` formal
review and passes S03 only for limited negative-control/data-snooping/OOS
guardrail use. The review records unresolved exact rule tables, sample windows,
OOS details, costs, bootstrap assumptions, public code/data availability, and
deterministic reproduction gaps; routes the next formal review to
`P30-BL-002-S08` before candidate-evidence review; and does not validate a
signal, approve a threshold, create a validated artifact, create a validated
signal definition, add evaluator behavior, or authorize implementation.
Phase 32 Step 8 is documentation-only. It adds the `P30-BL-002-S08` formal
review and passes S08 only for methodology-only PIT review material. The
review records point-in-time, no-lookahead, survivorship, and restatement
expectations for later candidate-evidence reviews, along with proprietary
vendor, exact FQL, cutoff, access, and local replay gaps; routes the next
formal review to `P30-BL-002-S05`; and does not validate a signal, approve a
threshold, create a validated artifact, create a validated signal definition,
add evaluator behavior, or authorize implementation.
Phase 32 Step 9 is documentation-only. It adds the `P30-BL-002-S05` formal
review and conditionally passes S05 only for limited candidate-evidence
planning. The review records a bounded time-series momentum candidate-evidence
claim for future structured evaluation planning only, plus unresolved
project-local reproduction, PIT/no-lookahead audit, roll/cost, OOS,
multiple-testing, and implementation-approval gaps; it does not validate a
signal, approve a threshold, create a validated artifact, create a validated
signal definition, add evaluator behavior, or authorize implementation.
The latest full-suite result is:

```text
778 passed, 4 skipped
```

## Architecture Summary

The core trading path remains deterministic and explicit:

```text
Bar + Quote
  -> deterministic signal rule
  -> ProposedOrder or no signal
  -> RiskEngine.check()
  -> LocalBroker.submit_order()
  -> paper execution simulator
  -> PortfolioState update
  -> quote-map valuation
  -> reconciliation
  -> event ledger
  -> structured result
```

For near-term research and evaluator planning, future prompts may use the
compressed architecture summary in
[`docs/agent_context/codex_operating_context.md`](agent_context/codex_operating_context.md):

```text
Market Data -> Features -> Screener -> Signals -> Risk -> ExecutionIntent -> ExecutionPlan -> PlanningPolicy -> future OMS/Broker -> Fills/Portfolio/Reconciliation
```

The project currently includes immutable domain models, deterministic signal and
risk checks, an offline ask-momentum screener with optional deterministic
filters, a pure orchestration-owned Screener -> Signal input bridge, local paper
execution, portfolio state transitions, quote-based valuation, local
reconciliation, and structured broker results.

The screener bridge prepares signal-ready inputs only. It does not invoke
signals yet if signals would create orders. It rejects duplicate screener
result symbols and malformed result/candidate inputs, preserves the original
`Bar` and `Quote` objects, and now supports pure screener-ordered signal
evaluation. Any signal output is not an approved trade and is not submitted.
The screener-ordered signal evaluation contract is now covered for mixed
signal/no-signal outputs, input non-mutation, immutable evaluation results, and
signal-rule exception propagation.
Dependency-direction guardrail tests now enforce the documented layering between
screener, signals, risk, orchestration, and execution.
The Signal -> Risk layer converts `ScreenerSignalEvaluation` rows into
`SignalRiskEvaluation` rows, retains no-signal rows with `risk=None`, and checks
proposed orders with `RiskEngine` only. Risk-approved means allowed by risk; it
does not mean executed, submitted, or broker-ready. This path does not call
brokers, Alpaca, execution, CLI, scheduler, ML, or LLM trading-path logic.
Phase 15 documents the future Risk -> Execution boundary and keeps
risk-approved rows as permission signals only, not execution instructions.
Phase 16 Step 1 strengthens dependency guardrails so pre-execution
orchestration modules cannot import execution, broker, Alpaca, or trade-flow
modules. Phase 16 Step 2 adds a pure risk-approved row selector that creates no
execution intents and calls no broker, execution, Alpaca, `submit_order`,
scheduler, persistence, ML, or LLM trading-path logic. Phase 17 Step 1
documents a future internal execution-intent boundary. Phase 17 Step 2 adds the
minimal internal `ExecutionIntent` wrapper and
`build_execution_intents_from_risk_approved(...)` builder. The intent remains
pre-submission and broker-agnostic, preserving the source
`SignalRiskEvaluation` by identity. No broker path, order submission,
client-order-id generation, idempotency, runtime behavior, persistence, ML, or
LLM trading-path logic was added. Phase 17 Step 3 keeps the implementation
unchanged and hardens the contract that proposed orders, risk verdicts, and
status remain reachable only through `intent.source_evaluation`. Phase 18 Step
1 documents a future execution-planning boundary as a deterministic
batch-level, pre-broker concept. Phase 18 Step 2 adds the minimal
`ExecutionPlan` container and `build_execution_plan(...)` builder. The plan
preserves `ExecutionIntent` order and identity only; no broker routing,
idempotency, persistence, order submission, or runtime behavior has been
implemented. Phase 18 Step 3 keeps the implementation unchanged and hardens
that plan traceability flows through `plan.intents[n].source_evaluation`.
Phase 19 Step 1 documents the future execution-planning policy boundary after
minimal plan construction and before broker-facing request construction. That
policy is conceptual only: no policy object, accepted/skipped buckets, cash
reservation, same-symbol handling, priority/ranking, idempotency, persistence,
broker routing, order submission, runtime behavior, ML, or LLM trading-path
logic has been implemented. Phase 19 Step 2 adds the minimal deterministic
policy-result boundary and a no-op pass-through policy. All intents are
currently accepted, skipped intents are only a future traceability shape, and
no real planning policy decisions have been added. Phase 19 Step 3 keeps the
implementation unchanged and hardens the contract that accepted and skipped
traceability flows through `ExecutionIntent.source_evaluation`, not through
direct convenience fields on the policy result. Phase 20 Step 1 documents the
future maximum accepted intents per plan policy as the first real
execution-planning policy concept. It is documentation-only: `ExecutionPlan`
remains a container, the no-op policy still accepts every intent, and no
runtime behavior, broker-facing request construction, cash reservation,
idempotency, same-symbol handling, priority/ranking, persistence, order
submission, ML, or LLM trading-path logic has been added. Phase 20 Step 2 adds
the pure max-intents policy implementation while keeping no-op pass-through
separate for no-cap behavior. The max-intents policy performs only deterministic
plan-order capping; it adds no broker routing, order submission, cash or
buying-power reservation, same-symbol conflict handling, deduplication,
priority/ranking, idempotency, persistence, scheduler/runtime behavior, ML, or
LLM trading-path logic. Phase 20 Step 3 keeps production source unchanged and
hardens the max-intents traceability contract with tests and documentation
only. Phase 21 Step 1 documents the future Research -> Validation ->
Deterministic Core boundary. Research, backtesting, and LLM-assisted summaries
remain advisory until promoted through reviewed artifacts, explicit
deterministic contracts, and test-first implementation. Phase 21 Step 2 adds
the first tiny validated research artifact contract as metadata/evidence only;
it remains upstream and advisory and has no execution, broker, risk approval,
signal generation, persistence, live-data, ML, or LLM trading-path behavior.
Phase 21 Step 3 keeps that implementation unchanged and hardens traceability
and ordering guarantees with tests and documentation only. Phase 22 Step 1
documents the future validated signal definition boundary; validated signal
definitions are future promoted contracts, not execution decisions. Phase 22
Step 2 adds the minimal `ValidatedSignalDefinition` metadata contract while
keeping signal evaluation, risk approval, execution intent creation, broker
behavior, persistence, runtime behavior, ML, and LLM trading-path logic out.
Phase 22 Step 3 keeps production source unchanged and hardens source-artifact
traceability, deterministic tuple ordering, metadata-only boundaries, and
independence from execution, risk, broker, runtime, scheduler, persistence,
ML, and LLM trading-path modules.
Phase 23 Step 1 documents the future signal evaluation, clock, and as-of
boundary. Validated signal definitions remain metadata-only, and future signal
evaluations remain advisory reports rather than execution decisions. The
deterministic core may consume only explicit promoted contracts, explicit input
snapshots, and explicit timezone-aware timestamps. Broker behavior remains
isolated, and LLMs remain out of the hot path.
Phase 23 Step 2 adds only deterministic time primitives in the core layer.
`FixedClock` is injectable and deterministic; no system clock, live data, risk,
execution, broker, scheduler/runtime, persistence, ML, or LLM behavior was
introduced.
Phase 23 Step 3 keeps those primitives unchanged and hardens their
traceability with tests/docs only. UTC-aware timestamp enforcement and
`observed_at <= as_of` lookahead-prevention behavior are now pinned more
explicitly.
Phase 24 Step 1 documents the future `SignalEvaluationResult` boundary after
validated signal definitions and explicit clock/as-of rules. The future result
is advisory deterministic output only: it may carry signal ids, source
artifact references, input snapshot fingerprints, explicit UTC-aware `as_of`
and `evaluated_at` timestamps, deterministic output values, reason codes,
diagnostics, assumptions, and limitations. It must not carry orders, broker
requests, risk approvals, execution intents, execution plans, portfolio
mutation, ranking or priority decisions, Alpaca behavior, or LLM-generated
trade decisions.
Phase 24 Step 2 implements that minimal advisory result contract in
`src/algotrader/signals/signal_evaluation_result.py`. The object stores only
evaluation id, signal id/version, source artifact id/version, explicit
UTC-aware `as_of` and `evaluated_at`, input fingerprint, output value, reason
code, diagnostics, assumptions, and limitations. It is frozen, slotted, and
metadata-only.
Phase 24 Step 3 keeps that implementation unchanged and hardens the tests and
docs around traceability. `SignalEvaluationResult` remains advisory metadata
only and does not evaluate signals, compute features, implement strategies,
create execution intents, approve risk, mutate execution plans, route to
brokers, interact with Alpaca, submit orders, touch scheduler/runtime or
persistence, train or run ML, or put LLMs in the trading path.
Phase 25 Step 1 documents the future signal evaluator boundary only. No
evaluator implementation, signal computation, production behavior, runtime
behavior, broker behavior, ML behavior, or LLM trading-path behavior was added.
Phase 25 Step 2 adds only `SignalEvaluationInputSnapshot` as deterministic
input snapshot/reference metadata for a future evaluator. It does not compute
signals or features, access live data, approve risk, create execution intents,
mutate execution plans, route to brokers, interact with Alpaca, use
scheduler/runtime or persistence behavior, train or run ML, or put LLMs in the
trading path.
Phase 25 Step 3 keeps that contract unchanged and hardens traceability with
tests/docs only. The snapshot remains metadata/reference-only, not a signal
evaluator, not signal computation, not feature computation, not risk approval,
not execution behavior, not broker or Alpaca behavior, not runtime/persistence
behavior, and not ML or LLM trading-path behavior.
Phase 26 Step 1 documents the future no-op signal evaluator boundary only. No
no-op evaluator implementation, evaluator protocol, result contract change,
no-op marker, signal computation, production behavior, runtime behavior,
trading-path behavior, broker behavior, ML behavior, or LLM trading-path
behavior was added. Future evaluator modules must not import broker, Alpaca,
execution, risk, runtime/scheduler, persistence, ML, or LLM modules.
Phase 26 Step 2 concludes that the existing `SignalEvaluationResult` fields are
sufficient for a future minimal no-op evaluator. A future no-op result can
preserve traceability through signal definition identity/version, source
artifact identity/version, input fingerprint, explicit UTC-aware `as_of`,
explicit UTC-aware `evaluated_at`, `output_value`, `reason_code`,
`diagnostics`, `assumptions`, and `limitations` without adding score,
direction, confidence, actionability, `should_trade`, no-op marker,
`result_kind`, or `evaluator_kind` fields.
Phase 26 Step 3 adds `NoOpSignalEvaluator` in the signal layer. It proves the
explicit deterministic input/output boundary only. It accepts a
`ValidatedSignalDefinition`, a `SignalEvaluationInputSnapshot`, explicit
UTC-aware `as_of`, and explicit UTC-aware `evaluated_at`, then returns advisory
`SignalEvaluationResult` metadata. It does not compute signals, inspect source
payloads, access live data, score, rank, infer direction, recommend trades,
approve risk, create execution intents, mutate execution plans, route to
brokers, submit orders, use scheduler/runtime/persistence behavior, run ML, or
call LLMs.
Phase 26 Step 4 hardens that boundary with tests/docs only. It adds no
production source or behavior. The no-op evaluator remains deterministic,
offline-safe, credential-free, advisory-only, broker-isolated, and traceable
without implying a signal fired, a recommendation exists, risk was approved, or
execution readiness exists.
Phase 27 Step 1 adds the real evaluator admission boundary as documentation
only. No production code, tests, runtime behavior, real evaluator, or signal
computation was added. Real evaluator work remains blocked until deterministic
input values, observation timestamps, no-lookahead proofs, advisory output
meaning, side-effect tests, and trading-path dependency tests are explicit.
Phase 27 Step 2 adds the deterministic signal input-value boundary as
documentation only. No production code, tests, runtime behavior, input-value
contract, real evaluator, or signal computation was added.
Phase 27 Step 3 adds `SignalInputValue` as a minimal signal-layer contract for
one explicit observed value. It validates only its own metadata and timestamp;
lookahead validation against evaluator `as_of` remains future work.
Phase 27 Step 4 hardens that contract with tests/docs only. No production code
or runtime behavior changed.
Phase 28 Step 1 adds the signal input bundle boundary as documentation only.
`SignalInputValue` remains a single observed-value contract, and no real
evaluator or signal computation exists yet.
Phase 28 Step 2 adds the minimal `SignalInputBundle` contract. It is an
immutable input container only: it groups explicit `SignalInputValue` objects,
preserves ordering and value identity, rejects duplicate names, and rejects
lookahead values where `observed_at > as_of`. Completeness validation against
`SignalEvaluationInputSnapshot` remains deferred.
Phase 28 Step 3 hardens that bundle with tests/docs only. No production code or
runtime behavior changed. The bundle remains deterministic, immutable,
traceable, lookahead-safe, non-computational, and isolated from evaluator,
risk, execution, broker, runtime, persistence, ML, and LLM trading-path
behavior.
Phase 28 Step 4 documents the separate future completeness validation boundary.
No production code or runtime behavior changed; `SignalInputBundle` remains a
grouping contract only, and no completeness validator, real evaluator, signal
computation, risk approval, execution behavior, broker behavior, persistence,
ML, or LLM trading-path logic was added.
Phase 28 Step 5 implements the minimal separate completeness boundary. The
bundle constructor is unchanged; completeness validation lives in a pure signal
module and returns metadata only. It does not inspect or interpret values,
compute signals or features, score, rank, infer direction, recommend trades,
approve risk, create execution intents, mutate execution plans, access live
data, route to brokers or Alpaca, submit orders, use scheduler/runtime or
persistence behavior, run ML, or use LLMs in the trading path.
Phase 28 Step 6 hardens that contract with tests/docs only. No production code
or runtime behavior changed. The tests prove completeness depends only on
required-name presence, not observed values, source ids, or timestamps; extra
inputs remain reported but non-blocking; snapshot id equality and `as_of`
equality are still not required; and lookahead validation remains outside the
completeness validator.

Phase 29 Step 1 defines the first real evaluator design gate. The gate requires
a future evaluator-specific design to identify the validated signal definition,
supporting research artifact, explicit inputs, completeness policy, timestamp
compatibility, advisory output semantics, assumptions, limitations, and
deterministic/no-lookahead/side-effect tests before implementation. No real
evaluator, signal computation, runtime behavior, or trading-path behavior was
added.

Phase 29 Step 2 selects the first real evaluator candidate for the next design
phase: a minimal threshold-style advisory evaluator over one explicit scalar
`SignalInputValue`. The selection does not authorize implementation; a future
evaluator-specific design must still define exact contracts, output semantics,
completeness behavior, timestamp compatibility, and tests before production
code can be considered. No production code, runtime behavior, real evaluator,
signal computation, or trading-path behavior was added.

Phase 29 Step 3 designs the selected candidate contract. The contract records
the placeholder input name `indicator_value`, preferred initial value type
`Decimal`, possible `>=` threshold semantics, advisory-only output
expectations, missing/extra input policy recommendations, strict timestamp
compatibility preference, no-lookahead rules, forbidden semantics, and required
future tests. It remains documentation-only and does not authorize
implementation. No production code, runtime behavior, real evaluator, signal
computation, or trading-path behavior was added.

Phase 29 Step 4 defines the first real evaluator test matrix. The matrix covers
future fixtures, input validation, threshold/comparator behavior,
timestamp/no-lookahead requirements, traceability, advisory-only output,
determinism, side-effect and dependency isolation, mutation safety, forbidden
behavior, open implementation questions, and go/no-go criteria. It remains
documentation-only and does not authorize implementation. No production code,
runtime behavior, real evaluator, signal computation, or trading-path behavior
was added.

Phase 29 Step 5 reviews implementation readiness for the selected candidate.
The recommendation is Option C: a small additional docs-only design phase is
needed to lock constants and output semantics before implementation. Exact
validated signal definition identity/version, supporting research artifact
identity/version, input name, threshold source, comparator, output
representation, reason codes, missing/extra input policy, snapshot/as-of
compatibility rules, and completeness flow remain unresolved. No production
code, runtime behavior, real evaluator, signal computation, or trading-path
behavior was added.

Phase 29 Step 6 designs threshold evaluator constants and output semantics.
It selects `indicator_value`, `Decimal`, `>=`, textual advisory output values
`threshold_condition_met` and `threshold_condition_not_met`, deterministic
threshold reason codes, strict snapshot/as-of compatibility, pre-use
completeness validation, deterministic missing/invalid-input rejection, and
extra-input invariance. The updated recommendation is Option B: implementation
remains blocked because exact validated signal and research artifacts are not
available. No production code, runtime behavior, real evaluator, signal
computation, or trading-path behavior was added.

Phase 30 Step 1 defines the research-support boundary for the remaining
threshold evaluator blockers. It requires an exact future
`ValidatedResearchArtifact`, exact future `ValidatedSignalDefinition`, and a
validated threshold value/source tied to supporting evidence before any
implementation may proceed. It keeps evaluator output advisory, pre-risk,
non-actionable, not broker-aware, not portfolio-aware, and outside the LLM
trading hot path. No production code, runtime behavior, real evaluator, signal
computation, or trading-path behavior was added.

Phase 30 Step 5 populates an unreviewed candidate research backlog only.
Backlog entries are not reviewed evidence and cannot support implementation
until candidate sourcing, artifact review, validated research support, and
validated signal-definition support are completed. No production code, runtime
behavior, real evaluator, signal computation, or trading-path behavior was
added.

Phase 30 Step 6 selects `P30-BL-001` as the first sourcing target only.
Selection is not source collection, artifact review, validation, approval, or
implementation readiness. No production code, runtime behavior, real
evaluator, signal computation, or trading-path behavior was added.

`LocalBroker` is the deterministic reference broker and now lives in:

```text
src/algotrader/execution/local_broker.py
```

`AlpacaPaperBroker` is an inert-by-default future broker boundary. It follows
the canonical broker-facing shape but only has operational behavior in tests
when an explicit fake adapter is injected.

## Alpaca Boundary

The normal test/runtime Alpaca preparation path is still fake-only and offline.

Current guarantees:

- bounded `alpaca-py` dependency isolated to the SDK wrapper
- no credentials
- no environment dependency for normal operation or tests
- no network calls
- no real broker connectivity
- no websocket fills
- no paper-account order submission

The current fake-only path is:

```text
fake Alpaca response
  -> TranslatedAlpaca DTO
  -> explicit mapper
  -> internal Account / Position / BrokerOrderResult
```

Translator return types are pinned:

- `TranslatedAlpacaAccount`
- `TranslatedAlpacaPosition`
- `TranslatedAlpacaOrderResult`

Mapper functions convert translated DTOs into internal models/results:

- `map_translated_account_to_account(...)`
- `map_translated_position_to_position(...)`
- `map_translated_order_result_to_broker_result(...)`

`AlpacaPaperBroker.submit_order(...)` follows the canonical broker signature:

```text
submit_order(order, quote, risk_verdict=None, order_id=None) -> BrokerOrderResult
```

Without an injected adapter, Alpaca broker operations raise
`BrokerNotImplementedError`.

## Safety Guarantees

Production code has repo-wide AST import safety coverage for forbidden
broker/network/LLM imports and dynamic import/code-execution calls. The
deterministic trading path still has no LLM logic in risk, execution, signals,
screener, portfolio, valuation, reconciliation, or feature calculation.

Current safety behaviors:

- duplicate `order_id` handling is part of broker contract expectations
- `LocalBroker` rejects duplicate order IDs with `duplicate_order_id`
- duplicate `LocalBroker` submissions do not create a second fill or ledger
  mutation
- fake Alpaca adapter rejects duplicate `client_order_id` values before a second
  fake client call
- `require_paper_profile()` defines the future pre-SDK paper-profile gate
- `require_paper_profile()` rejects obvious non-paper Alpaca URLs
- `AlpacaSdkClient` is the only production file allowed to import `alpaca`
- normal pytest exercises the `paper_integration` skip gate without calling
  Alpaca
- `RiskConfig.allow_short=True` still fails closed with
  `short_selling_not_supported`
- portfolio overdraw and oversell branches fail closed without mutating the
  original `PortfolioState`
- valuation rejects unsupported negative position quantities

## Compatibility Notes

`fake_broker.py` remains intentionally as a compatibility shim:

```text
src/algotrader/execution/fake_broker.py
```

Normal imports should use:

```python
from algotrader.execution.local_broker import LocalBroker
```

The compatibility path still re-exports the same `LocalBroker` class for older
imports.

`LedgerEventType.RECONCILIATION_CHECKED` is intentionally kept as an accepted
ledger event value.

`SignalGenerator` is intentionally kept as an exported public signal interface.

## Recent Cleanup

Recent completed work:

- pinned Alpaca translator return types
- added explicit Alpaca mapper layer
- moved fake Alpaca response handling to DTO -> mapper -> internal model/result
- aligned `AlpacaPaperBroker` with the canonical broker shape
- added broker contract idempotency expectations
- added repo-wide AST import safety tests
- moved `LocalBroker` to `local_broker.py`
- kept `fake_broker.py` as a compatibility shim
- cleaned duplicate execution package imports

## Post-Review Hygiene Checkpoint

After the Claude Opus 183-test review, a low-risk hygiene patch consolidated
duplicate fake Alpaca test clients into `tests/fakes/alpaca.py`, removed stale
pre-pin adapter test helpers, labeled the broker contract tests by state model,
and added a focused reconciliation currency-mismatch test.

`AlpacaPaperBroker.get_positions()` now delegates directly to the injected fake
adapter's `list_positions()` method after the existing inert/no-adapter guard.
This matched the existing adapter shape and did not change trading behavior.

At the Phase 20 Step 1 checkpoint, the full suite remained:

```text
python -m pytest
183 passed
```

No runtime trading behavior changed, and no SDK, credentials, environment
reads, network calls, websocket behavior, scheduler/runtime loop, real broker
connectivity, LangGraph, LangChain, OpenAI, Anthropic, ML, or LLM
trading-path logic was added.

## Shared Broker Contract Checkpoint

A test-only patch added `tests/contracts/test_broker_shared_contract.py` with
10 parametrized checks covering both `LocalBroker` and `AlpacaPaperBroker` with
an injected fake adapter. The shared subset covers missing and rejected risk
verdicts, approved submissions returning the exact internal
`BrokerOrderResult`, deterministic provided `order_id` use, and duplicate
`order_id` rejection without a second local fill or fake client submission.

Broker contract coverage is now clearer across three layers:

- portfolio-owning broker contract
- external-state-reflecting Alpaca fake protocol contract
- shared broker contract subset

The full suite is now:

```text
python -m pytest
193 passed
```

No production code changed, and no SDK, credentials, environment reads, network
calls, websocket behavior, scheduler/runtime loop, real broker connectivity,
LangGraph, LangChain, OpenAI, Anthropic, ML, or LLM trading-path logic was
added.

## Pre-SDK Safety Gate Checkpoint

A small safety-hardening patch added and tested `require_paper_profile()` as the
future gate SDK code must call before Alpaca-touching behavior. Import-safety
coverage now also blocks dynamic import and code-execution calls such as
`importlib.import_module(...)`, `__import__(...)`, `exec(...)`, and `eval(...)`.

The full suite is now:

```text
python -m pytest
198 passed
```

At that pre-SDK checkpoint, no SDK dependency, credentials, environment reads,
network calls, websocket behavior, scheduler/runtime loop, real broker
connectivity, LangGraph, LangChain, OpenAI, Anthropic, ML, or LLM trading-path
logic was added.

## Phase 1 SDK Wrapper Checkpoint

A tightly scoped Phase 1 patch declared `alpaca-py>=0.43,<0.44`, added the
file-scoped `AlpacaSdkClient` wrapper, and updated import safety so `alpaca`
imports are allowed only in that wrapper. Wrapper tests use fakes and prove
paper-profile gating, adapter compatibility, credential redaction, and
construction-time network isolation.

The full suite is now:

```text
python -m pytest
206 passed
```

No real account call, real or paper order submission, websocket behavior,
scheduler/runtime loop, real broker connectivity, LangGraph, LangChain, OpenAI,
Anthropic, ML, or LLM trading-path logic was added.

## Pre-Phase-2 Hardening Checkpoint

Before any real paper-account smoke test, small hardening patches added the
paper URL invariant, direct `paper_integration` gate tests, one skipped
paper-marker smoke test, broader SDK credential redaction coverage, a lazy SDK
import regression test, and an offline `_create_trading_client()` construction
test.

The full suite is now:

```text
python -m pytest
216 passed, 1 skipped
```

No production runtime broker behavior changed, and no real account call, real
or paper order submission, network call, websocket behavior, scheduler/runtime
loop, real broker connectivity, LangGraph, LangChain, OpenAI, Anthropic, ML, or
LLM trading-path logic was added.

## Phase 2 Account Smoke Checkpoint

Phase 2 added exactly one `paper_integration` test in
`tests/integration/test_alpaca_paper_account_smoke.py`. It is skipped by
default and, only when the explicit paper gate is enabled, constructs
`AlpacaSdkClient` from environment-backed `AlpacaPaperConfig` and calls
`get_account()` exactly once.

The full suite is now:

```text
python -m pytest
216 passed, 2 skipped
```

Normal pytest remains credential-free and offline. No orders, positions call,
websocket behavior, scheduler/runtime loop, runtime broker selection, real
broker connectivity in normal runtime, LangGraph, LangChain, OpenAI, Anthropic,
ML, or LLM trading-path logic was added.

## Phase 3 Account Translation Smoke Checkpoint

Phase 3 added exactly one `paper_integration` test in
`tests/integration/test_alpaca_paper_account_translation_smoke.py`. It is
skipped by default and, only when the explicit paper gate is enabled, validates
the real SDK account response shape through:

```text
SDK account response
  -> AlpacaSdkClient
  -> AlpacaClientAdapter
  -> alpaca_translator
  -> alpaca_mapper
  -> internal Account
```

The full suite is now:

```text
python -m pytest
216 passed, 3 skipped
```

Normal pytest remains credential-free, offline, and skipped by default for real
paper integration tests. This phase does not call positions, submit orders, add
websocket behavior, add a scheduler/runtime loop, add runtime broker selection,
enable real broker connectivity in normal runtime, or add LangGraph, LangChain,
OpenAI, Anthropic, ML, or LLM trading-path logic.

## Phase 4 Positions Translation Smoke Checkpoint

Phase 4 added exactly one `paper_integration` test in
`tests/integration/test_alpaca_paper_positions_translation_smoke.py`. It is
skipped by default and, only when the explicit paper gate is enabled, validates
the real SDK positions response shape through:

```text
SDK positions response
  -> AlpacaSdkClient
  -> AlpacaClientAdapter
  -> alpaca_translator
  -> alpaca_mapper
  -> internal Position
```

The full suite is now:

```text
python -m pytest
216 passed, 4 skipped
```

Normal pytest remains credential-free, offline, and skipped by default for real
paper integration tests. This phase does not submit orders, add runtime broker
wiring, add reconciliation logic, add websocket behavior, add a
scheduler/runtime loop, or add LangGraph, LangChain, OpenAI, Anthropic, ML, or
LLM trading-path logic.

## Phase 5 Reconciliation Readiness Checkpoint

Phase 5 is documentation-only. It updates
`docs/alpaca_paper_integration_plan.md` with a reconciliation-readiness plan
covering future inputs, local-ledger source-of-truth policy, mismatch handling,
broker call failures, explicit operator-triggered timing, and future
skipped-by-default read-only integration-test policy.

No production code, tests, order submission, runtime broker wiring,
reconciliation implementation, scheduler/runtime loop, websocket behavior,
auto-correction, real Alpaca ledger persistence, LangGraph, LangChain, OpenAI,
Anthropic, ML, or LLM trading-path logic was added.

## Phase 6 Fake-Only Reconciliation Checkpoint

Phase 6 added offline reconciliation hardening around the fake Alpaca broker
path:

```text
FakeAlpacaClient
  -> AlpacaClientAdapter
  -> AlpacaPaperBroker
  -> reconcile_portfolio(...)
```

Fake-only tests now cover matching state, cash mismatch plus unexpected
position, quantity mismatch, and missing position through that path.
`FakeAlpacaClient` can customize returned positions for deterministic mismatch
scenarios.

`ReconciliationReport` now includes:

- `available: bool = True`
- `broker_error: str = ""`

If `broker.get_account()` or `broker.get_positions()` fails, reconciliation now
returns an unavailable report with `available=False`, `ok=False`, no mismatches,
and a sanitized broker error. Both account-call and positions-call failures are
covered by fake-only tests.

Report-only tolerances now apply to cash, valuation, and unrealized P&L:

- `_CASH_MISMATCH_TOLERANCE = Decimal("0.01")`
- `_VALUATION_MISMATCH_TOLERANCE = Decimal("0.01")`
- `_UNREALIZED_PNL_MISMATCH_TOLERANCE = Decimal("0.01")`

`_within_tolerance(...)` uses `abs(expected - actual) <= tolerance`, so the
exact tolerance boundary is accepted. Quantity mismatches remain exact. Currency
divergence remains exact and is still reported as `cash_mismatch`.

The full suite is now:

```text
python -m pytest
229 passed, 4 skipped
```

No real Alpaca calls, order submission, runtime broker wiring, scheduler/runtime
loop, websocket behavior, ledger replay, ML, or LLM trading-path logic was
added.

## Phase 8 Deterministic Screener Foundation

Phase 8 begins with one small offline screener package:

```text
src/algotrader/screener/
```

The screener ranks synthetic `Bar + Quote` inputs by deterministic ask momentum
versus previous close:

```text
score = (quote.ask - previous_bar.close) / previous_bar.close
```

Results are immutable dataclasses returned as a tuple. Ranking is deterministic:
score descending, then symbol ascending as a tie-breaker. The screener reuses
the existing `Bar`, `Quote`, and `ValidationError` conventions instead of
adding duplicate market-data models.

This foundation is offline, credential-free, API-free, broker-free, and
deterministic. It does not generate orders and is not connected to signals,
risk, execution, Alpaca, or any scheduler/runtime loop.

The full suite is now:

```text
python -m pytest
240 passed, 4 skipped
```

## Phase 9 Deterministic Screener Filter Polish

Phase 9 adds optional deterministic filters to:

```text
rank_by_ask_momentum(...)
```

The screener can now keep only results with `score >= min_score` and can limit
the returned tuple with `top_n`. Defaults preserve Phase 8 behavior: no score
filter and no result limit.

Filtering remains local and deterministic. `min_score` accepts a `Decimal` or
decimal string. `top_n` must be an integer greater than or equal to 1. The
ordering remains score descending, then symbol ascending as a tie-breaker.

The Phase 9 filter contract is now pinned: `min_score` applies before `top_n`,
`min_score` is inclusive with `score >= min_score`, and default values preserve
Phase 8 behavior.

This phase still does not add live data, broker wiring, order generation, risk
integration, scheduler/runtime behavior, ML, or LLM trading-path logic.

The full suite is now:

```text
python -m pytest
256 passed, 4 skipped
```

## Phase 10 Screener to Signals Design

Phase 10 is documentation-only. It adds:

```text
docs/design/phase10_screener_to_signals.md
```

The design defines a future orchestration boundary between the deterministic
screener and deterministic signal generation. It does not implement the bridge
or add runtime behavior.

The planned dependency direction is:

```text
orchestration -> screener
orchestration -> signals
```

The design pins the rule that screener output may influence which symbols are
evaluated, their evaluation order, and whether a symbol is skipped due to
`top_n` or `min_score`. Screener output must not directly influence order side,
order type, quantity, limit price, broker selection, risk caps, position sizing,
idempotency keys, or whether `submit_order` is called.

No production code, live data, external API, Alpaca integration, broker wiring,
order creation, risk integration, scheduler/runtime behavior, ML, dependency, or
LLM trading-path logic was added.

## Phase 11 Screener to Signal Input Bridge

Phase 11 begins the Screener -> Signal path with one pure orchestration-owned
adapter:

```text
src/algotrader/orchestration/screener_signal_flow.py
```

`ordered_signal_inputs_from_screener(...)` accepts ranked
`AskMomentumResult` values plus the original `AskMomentumCandidate` values or a
candidate lookup, matches by symbol, rejects missing or duplicate candidate
symbols with `ValidationError`, and returns an immutable tuple of signal-ready
`(Bar, Quote)` pairs in the exact screener-result order.

Phase 11 Step 2 hardens the bridge further. It now rejects duplicate screener
result symbols so a future signal path cannot silently evaluate the same symbol
twice. It also rejects malformed result/candidate inputs and preserves the
original `Bar` and `Quote` objects while returning immutable ordered pairs.

Phase 11 Step 3 adds pure screener-ordered signal evaluation through
`evaluate_signals_from_screener(...)`. It applies the existing deterministic
signal rule to the ordered `(Bar, Quote)` inputs and returns immutable
`ScreenerSignalEvaluation` values in exact screener order. A returned
`ProposedOrder` is a proposed signal output only: it is not an approved trade
and is not submitted.

This phase still does not call risk, call brokers, touch Alpaca, connect to
execution, CLI, scheduler, or runtime behavior, or add ML or LLM trading-path
logic. No dependencies were added.

The full suite is now:

```text
python -m pytest
269 passed, 4 skipped
```

## Phase 12 Signal to Risk Design

Phase 12 is documentation-only. It adds:

```text
docs/design/phase12_signal_to_risk.md
```

The design defines the future orchestration boundary between
`ScreenerSignalEvaluation` outputs and deterministic risk evaluation. It pins
that any `ProposedOrder` from `evaluate_signals_from_screener(...)` remains
proposed signal output only until it passes through a separately named,
deterministic risk-evaluation function in a later phase.

The planned dependency direction is:

```text
orchestration -> screener
orchestration -> signals
orchestration -> risk
```

The design explicitly prohibits passing `ScreenerSignalEvaluation.order`
directly into `LocalBroker.submit_order(...)`,
`AlpacaPaperBroker.submit_order(...)`, `evaluate_and_execute(...)`,
`generate_evaluate_and_execute(...)`, or any broker or execution layer.

No runtime behavior, production Python code, tests, Alpaca changes, broker
wiring, order submission, execution integration, scheduler/runtime behavior,
ML, dependency, or LLM trading-path logic was added.

## Phase 13 Screener-Ordered Signal Evaluation Contract Hardening

Phase 13 is test-focused. It hardens the existing
`evaluate_signals_from_screener(...)` contract with additional unit coverage in:

```text
tests/unit/test_screener_signal_flow.py
```

The new tests pin these behaviors:

- mixed signal/no-signal results preserve exact screener order
- no-signal candidates remain represented with `order=None`
- input candidates and screener results are not mutated
- original `Bar` and `Quote` object identities are preserved
- `ScreenerSignalEvaluation` is frozen/immutable
- `signal_rule` exceptions propagate instead of being hidden as `order=None`

No production Python code changed. No risk integration, broker wiring, Alpaca
changes, order submission, execution integration, scheduler/runtime behavior,
ML, dependency, or LLM trading-path logic was added.

The full suite is now:

```text
python -m pytest
273 passed, 4 skipped
```

## Phase 14 Step 1 Dependency Direction Guardrails

Phase 14 Step 1 is test-only. It adds AST-based dependency-direction guardrails
in:

```text
tests/unit/test_dependency_direction.py
```

The tests enforce the documented layering between screener, signals, risk,
orchestration, and execution. Screener modules must not import signals, risk,
execution, portfolio, or orchestration. Signal modules must not import screener,
risk, execution, portfolio, or orchestration. Risk modules must not import
screener, signals, orchestration, or execution, while the existing risk ->
portfolio relationship remains allowed. The screener-signal orchestration bridge
must not import execution, broker, Alpaca, or trade-flow modules.

No production Python code changed. No Signal -> Risk runtime behavior, broker
wiring, Alpaca changes, execution integration, order submission,
scheduler/runtime behavior, ML, dependency, or LLM trading-path logic was
added.

The full suite is now:

```text
python -m pytest
277 passed, 4 skipped
```

## Phase 14 Step 2 Signal to Risk Evaluation

Phase 14 Step 2 adds a pure orchestration-owned Signal -> Risk evaluation layer
in:

```text
src/algotrader/orchestration/signal_risk_flow.py
```

`evaluate_risk_for_screener_signals(...)` converts
`ScreenerSignalEvaluation` rows into immutable `SignalRiskEvaluation` rows. It
preserves input order, emits one output row per input row, retains no-signal
rows with `status="no_signal"` and `risk=None`, and checks proposed orders with
`RiskEngine` only.

`SignalRiskEvaluation.status` distinguishes:

- `no_signal`
- `risk_rejected`
- `risk_approved`

Risk-approved means only that the deterministic risk verdict allowed the
proposed order. It does not mean executed, submitted, broker-ready, filled, or
persisted.

This phase also updates dependency-direction guardrails so
`algotrader.orchestration.signal_risk_flow` cannot import execution,
trade-flow, broker, or Alpaca modules.

No broker wiring, Alpaca changes, execution integration, order submission,
`submit_order`, CLI changes, scheduler/runtime behavior, persistence, ML,
dependency, or LLM trading-path logic was added.

The full suite is now:

```text
python -m pytest
288 passed, 4 skipped
```

## Phase 15 Risk to Execution Boundary Design

Phase 15 is documentation-only. It adds:

```text
docs/design/phase15_risk_to_execution.md
```

The design defines the future boundary between deterministic risk-approved
`SignalRiskEvaluation` rows and any later execution bridge. It pins that
`risk_approved` means allowed by deterministic risk policy only. It is a
permission signal, not an execution instruction, and does not mean submitted,
executed, broker-routed, filled, or persisted.

The design states that a future execution bridge must live in orchestration or
execution-facing orchestration, may consume only `risk_approved` rows, must
preserve deterministic order, must skip `no_signal` and `risk_rejected` rows for
execution eligibility without deleting them from traceability, and must not
mutate portfolio directly or assume broker success.

No runtime behavior, production Python code, tests, exports, dependencies,
execution integration, broker wiring, Alpaca changes, order submission,
scheduler/runtime behavior, persistence, ML, or LLM trading-path logic was
added.

## Phase 16 Step 1 Risk to Execution Dependency Guardrails

Phase 16 Step 1 is test-only. It strengthens AST-based dependency-direction
guardrails in:

```text
tests/unit/test_dependency_direction.py
```

The tests enforce that pre-execution orchestration modules, including
`algotrader.orchestration.screener_signal_flow` and
`algotrader.orchestration.signal_risk_flow`, do not import execution, broker,
Alpaca, or trade-flow modules. The guardrail table also now includes
`algotrader.orchestration.risk_execution_flow` as an active pre-execution
module.

No production Python code changed. No Risk -> Execution runtime behavior,
execution bridge module, broker wiring, Alpaca changes, execution integration,
order submission, scheduler/runtime behavior, persistence, ML, dependency, or
LLM trading-path logic was added.

The full suite is now:

```text
python -m pytest
289 passed, 4 skipped
```

## Phase 16 Step 2 Risk-Approved Row Selection

Phase 16 Step 2 adds the first pure Risk -> Execution boundary helper in:

```text
src/algotrader/orchestration/risk_execution_flow.py
```

`select_risk_approved_evaluations(...)` accepts existing
`SignalRiskEvaluation` rows and returns only rows with
`status="risk_approved"`. It preserves deterministic input order, returns the
same row objects rather than copies, and returns an immutable tuple. `no_signal`
and `risk_rejected` rows are skipped.

This selector does not create execution intents, derive client order IDs or
idempotency keys, call brokers, import execution, touch Alpaca, call
`submit_order`, use schedulers, persist anything, mutate portfolios, or add ML
or LLM trading-path logic. `risk_approved` remains a permission signal only,
not an execution instruction.

Known limitation: multiple rows may be individually risk-approved against the
same fixed portfolio snapshot but not collectively affordable. This step does
not solve batch-level cumulative cash handling or same-symbol conflict
resolution; those remain future execution-boundary concerns before any
execution intent or submission behavior is added.

The full suite is now:

```text
python -m pytest
303 passed, 4 skipped
```

## Phase 17 Step 1 Execution-Intent Boundary Design

Phase 17 Step 1 started and completed as a documentation-only design phase. It
adds
`docs/design/phase17_execution_intent_boundary.md` to define the future
internal execution-intent boundary after
`select_risk_approved_evaluations(...)` and before any broker adapter,
execution layer, scheduler/runtime behavior, persistence, or live trading
path.

The design clarifies that selected risk-approved rows are permission signals
only. They are eligible for future execution-boundary consideration, but they
are not execution intents, submitted orders, broker-routed orders, fills,
persisted broker events, scheduler actions, runtime actions, or live trading
decisions. A future execution intent would be a deterministic, immutable,
auditable, broker-agnostic internal instruction candidate produced before any
broker adapter, if explicitly implemented later.

This step does not add an `ExecutionIntent` dataclass, a
`build_execution_intents_from_risk_approved(...)` function, order submission,
broker routing, Alpaca changes, `submit_order`, client-order-id generation,
idempotency implementation, scheduler/runtime behavior, persistence, portfolio
mutation, fills, reconciliation changes, live trading, ML, or LLM trading-path
logic.

The full-suite checkpoint remains:

```text
python -m pytest
303 passed, 4 skipped
```

## Phase 17 Step 2 Internal Execution-Intent Contract

Phase 17 Step 2 adds the smallest internal execution-intent contract in:

```text
src/algotrader/orchestration/risk_execution_flow.py
```

`ExecutionIntent` is an immutable, slotted dataclass with one field:
`source_evaluation: SignalRiskEvaluation`. It preserves traceability by
identity without adding screener rank, original index, broker IDs,
client-order IDs, idempotency keys, venue/account fields, fill fields,
persistence metadata, SDK-native objects, Alpaca-specific fields, or LLM-derived
fields.

`build_execution_intents_from_risk_approved(...)` accepts existing
`SignalRiskEvaluation` rows, reuses risk-approved row selection, and returns an
immutable tuple of `ExecutionIntent` objects for `risk_approved` rows only. It
skips `no_signal` and `risk_rejected` rows, preserves approved-row order,
preserves the exact original `SignalRiskEvaluation` object on each intent, and
does not mutate inputs.

This phase does not add broker routing, paper or live order submission,
Alpaca changes, `submit_order`, client-order-id generation, idempotency
implementation, batch cash reservation, same-symbol conflict resolution,
portfolio mutation, fills, scheduler/runtime behavior, persistence writes, ML,
or LLM trading-path logic.

The full suite is now:

```text
python -m pytest
318 passed, 4 skipped
```

## Phase 17 Step 3 ExecutionIntent Traceability Hardening

Phase 17 Step 3 is tests and documentation only. It hardens the
`ExecutionIntent` contract without changing production Python code.

`ExecutionIntent` remains an immutable, slotted, pre-submission internal object
with exactly one dataclass field: `source_evaluation`. Traceability flows
through that source `SignalRiskEvaluation` by identity. The proposed order,
risk verdict, and status remain reachable through
`intent.source_evaluation.order`, `intent.source_evaluation.risk`, and
`intent.source_evaluation.status`; no convenience fields or properties such as
`intent.order`, `intent.risk`, `intent.symbol`, or `intent.status` were added.

Additional tests pin that no broker IDs, broker names, account IDs,
client-order IDs, idempotency keys, venue fields, submission timestamps, fill
fields, Alpaca-specific fields, SDK/native objects, or persistence metadata are
exposed on `ExecutionIntent`.

The builder remains a pure approved-row intent builder. It still skips
`no_signal` and `risk_rejected` rows, preserves approved-row order, preserves
same-symbol approved rows without conflict resolution, performs no batch-level
cash reservation or collective affordability check, mutates no inputs, and
requires no portfolio, risk engine, broker, execution object, scheduler, or
persistence handle.

No broker routing, paper or live order submission, Alpaca changes,
`submit_order`, scheduler/runtime behavior, persistence writes, idempotency,
client-order-id generation, batch cash reservation, same-symbol conflict
resolution, portfolio mutation, fills, ML, or LLM trading-path logic was added.

The full suite is now:

```text
python -m pytest
321 passed, 4 skipped
```

## Phase 18 Step 1 Execution-Planning Boundary Design

Phase 18 Step 1 started and completed as a documentation-only design phase. It
adds:

```text
docs/design/phase18_execution_planning_boundary.md
```

The design defines the future execution-planning boundary after
`build_execution_intents_from_risk_approved(...)` and before any broker adapter,
broker-facing request construction, order submission, persistence write,
scheduler/runtime behavior, or live trading behavior.

`ExecutionIntent` remains source-only and pre-submission. It still has exactly
one dataclass field, `source_evaluation`, and proposed orders, risk verdicts,
and status remain reachable only through that source evaluation. A future
`ExecutionPlan` is described only conceptually as a deterministic batch-level
artifact that may later consume `ExecutionIntent` objects and produce a
pre-broker decision set.

This phase documents unresolved batch-level concerns for later work, including
collective affordability, cash or buying-power reservation, same-symbol
conflicts, duplicate or competing orders, ordering policy, partial acceptance
versus all-or-nothing policy, stale quote or risk snapshots, changed portfolio
snapshots, and future idempotency or `client_order_id` design. None of those
policies were implemented.

No production Python code, imports, tests, broker routing, Alpaca changes,
`submit_order`, order submission, idempotency implementation,
client-order-id generation, batch cash reservation, same-symbol conflict
resolution, persistence writes, audit logging writes, scheduler/runtime
behavior, portfolio mutation, fills, reconciliation changes, ML, or LLM
trading-path logic was added.

The full-suite checkpoint remains:

```text
python -m pytest
321 passed, 4 skipped
```

## Phase 18 Step 2 Minimal ExecutionPlan Contract

Phase 18 Step 2 adds the smallest implemented execution-planning contract in:

```text
src/algotrader/orchestration/execution_planning_flow.py
```

The new `ExecutionPlan` is an immutable, slotted dataclass with one field:
`intents: tuple[ExecutionIntent, ...]`. It is only an immutable batch container
for internal `ExecutionIntent` objects. It preserves input intent order and
preserves each exact `ExecutionIntent` object by identity.

`build_execution_plan(...)` accepts any iterable of `ExecutionIntent` objects
and returns `ExecutionPlan(intents=tuple(...))`. Empty input returns
`ExecutionPlan(intents=())`. The builder does not mutate inputs, unwrap source
`SignalRiskEvaluation` objects, copy proposed orders, compute batch cash,
resolve same-symbol conflicts, generate idempotency keys or client order IDs,
call brokers, submit orders, use schedulers, persist anything, mutate
portfolios, create fills, or call ML/LLM trading-path logic.

Traceability remains source-driven. Proposed orders and risk verdicts are still
reachable through
`plan.intents[n].source_evaluation.order` and
`plan.intents[n].source_evaluation.risk`. `ExecutionPlan` has no direct order,
risk, status, broker, account, venue, submission, fill, idempotency, client
order ID, cash reservation, priority, SDK, Alpaca, or persistence fields.

Dependency-direction guardrails now include
`algotrader.orchestration.execution_planning_flow` in the pre-execution
orchestration boundary checks and add a narrow AST guard against broker/runtime
call names in that module.

No broker routing, paper or live order submission, Alpaca changes,
`submit_order`, scheduler/runtime behavior, persistence writes, idempotency,
client-order-id generation, batch cash reservation, same-symbol conflict
resolution, portfolio mutation, fills, reconciliation changes, ML, or LLM
trading-path logic was added.

The full suite is now:

```text
python -m pytest
341 passed, 4 skipped
```

## Phase 18 Step 3 ExecutionPlan Traceability Hardening

Phase 18 Step 3 is tests and documentation only. It hardens the
`ExecutionPlan` contract without changing production Python code.

`ExecutionPlan` remains an immutable, slotted, pre-broker batch container with
exactly one dataclass field: `intents`. Each plan entry preserves the exact
original `ExecutionIntent` object by identity. Each intent still preserves the
exact original `SignalRiskEvaluation` object by identity.

Traceability flows through:

```text
plan.intents[n].source_evaluation
```

Proposed orders, risk verdicts, and statuses remain reachable through
`plan.intents[n].source_evaluation.order`,
`plan.intents[n].source_evaluation.risk`, and
`plan.intents[n].source_evaluation.status`; no convenience fields such as
`plan.orders`, `plan.risks`, `plan.statuses`, `plan.selected`,
`plan.rejected`, or `plan.skipped` were added.

Additional tests pin that no selected/rejected/skipped/accepted intent fields,
broker IDs, broker names, account IDs, venue fields, client order IDs,
idempotency keys, submission timestamps, fill fields, cash or buying-power
reservation fields, priority/rank fields, Alpaca-specific fields, SDK/native
objects, or persistence metadata are exposed on `ExecutionPlan`.

The builder remains a pure batch-container builder. It still preserves input
order, preserves duplicate and same-symbol intents without deduplication or
conflict resolution, performs no batch-level cash reservation or collective
affordability check, applies no priority/ranking policy, mutates no inputs, and
requires no portfolio, risk engine, broker, execution object,
scheduler/runtime object, or persistence handle.

No broker routing, paper or live order submission, Alpaca changes,
`submit_order`, scheduler/runtime behavior, persistence writes, idempotency,
client-order-id generation, batch cash reservation, same-symbol conflict
resolution, duplicate/competing order policy, priority/ranking policy,
portfolio mutation, fills, reconciliation changes, ML, or LLM trading-path
logic was added.

The full suite is now:

```text
python -m pytest
349 passed, 4 skipped
```

## Phase 19 Step 1 Execution-Planning Policy Design

Phase 19 Step 1 is documentation-only. It adds
[`docs/design/phase19_execution_planning_policy.md`](design/phase19_execution_planning_policy.md)
as the no-code design record for a future execution-planning policy layer after
minimal `ExecutionPlan` construction.

The design clarifies that `ExecutionIntent` remains a single source-only,
pre-submission candidate and that `ExecutionPlan` remains an immutable batch
container with exactly one dataclass field: `intents`. A future planning policy
may later decide which intents remain eligible after deterministic batch-level
checks, but no policy has been implemented in this step.

The design records unresolved policy questions around batch cash affordability,
buying-power reservation, same-symbol conflicts, duplicate or competing
intents, partial acceptance versus all-or-nothing behavior, stale quote or risk
snapshots, priority/ranking, idempotency separation, persistence/audit
separation, and broker/execution separation.

No production Python code, tests, imports, runtime behavior, broker routing,
paper or live order submission, Alpaca changes, `submit_order`,
scheduler/runtime behavior, persistence writes, audit logging writes,
idempotency, client-order-id generation, batch cash reservation, buying-power
reservation, same-symbol conflict resolution, duplicate/competing order policy,
priority/ranking policy, portfolio mutation, fills, reconciliation changes, ML,
or LLM trading-path logic was added.

The full suite remains:

```text
python -m pytest
349 passed, 4 skipped
```

Normal pytest remains offline and credential-free.

## Phase 19 Step 2 Minimal Planning Policy Contract

Phase 19 Step 2 adds a narrow pre-broker planning policy result boundary in
`src/algotrader/orchestration/execution_planning_policy.py`.

The new immutable result shapes are:

```text
SkippedExecutionIntent(intent: ExecutionIntent, reason: str)
PlanningPolicyResult(
    accepted_intents: tuple[ExecutionIntent, ...],
    skipped_intents: tuple[SkippedExecutionIntent, ...],
)
```

`apply_noop_execution_planning_policy(...)` accepts an `ExecutionPlan` and
returns a `PlanningPolicyResult`. It accepts every intent from the input plan in
the original order, preserves each `ExecutionIntent` object by identity, keeps
each source `SignalRiskEvaluation` reachable by identity through
`accepted_intents[n].source_evaluation`, and returns
`skipped_intents=()`.

`skipped_intents` exists only as a future traceability shape for deterministic
skip reasons. Phase 19 Step 2 does not add real skip logic, partial acceptance
policy, rejection policy, cash reservation, buying-power reservation,
same-symbol conflict handling, duplicate/competing order policy,
priority/ranking policy, idempotency, client-order-id generation,
broker-facing request construction, broker routing, order submission,
persistence writes, audit logging writes, scheduler/runtime behavior, portfolio
mutation, fills, reconciliation changes, ML, or LLM trading-path logic.

Dependency-direction tests now include
`algotrader.orchestration.execution_planning_policy` in the pre-execution
orchestration boundary and in the narrow AST guard against broker/runtime
imports, names, and calls.

The full suite is now:

```text
python -m pytest
374 passed, 4 skipped
```

## Phase 19 Step 3 PlanningPolicyResult Traceability Hardening

Phase 19 Step 3 is tests and documentation only. It hardens the minimal
planning policy result contract without changing production Python code.

`PlanningPolicyResult` remains an immutable, pre-broker result container with
exactly two dataclass fields: `accepted_intents` and `skipped_intents`.
`SkippedExecutionIntent` remains an immutable traceability wrapper with exactly
two dataclass fields: `intent` and `reason`.

Accepted-intent traceability flows through:

```text
result.accepted_intents[n].source_evaluation
```

Skipped-intent traceability flows through:

```text
result.skipped_intents[n].intent.source_evaluation
```

Proposed orders, risk verdicts, and statuses remain reachable through the
source `SignalRiskEvaluation` object, not through direct fields or convenience
properties on `PlanningPolicyResult` or `SkippedExecutionIntent`.

The no-op policy still accepts every input intent in order, preserves
`ExecutionIntent` object identity, preserves source `SignalRiskEvaluation`
object identity, and returns `skipped_intents=()`. Manually constructed skipped
results are covered only to pin the future traceability shape; no skip policy
logic was added.

No broker routing, paper or live order submission, Alpaca changes,
`submit_order`, scheduler/runtime behavior, persistence writes, audit logging
writes, idempotency, client-order-id generation, batch cash reservation,
buying-power reservation, same-symbol conflict resolution, duplicate/competing
order policy, priority/ranking policy, portfolio mutation, fills,
reconciliation changes, ML, or LLM trading-path logic was added.

The full suite is now:

```text
python -m pytest
379 passed, 4 skipped
```

## Phase 20 Step 1 Maximum Intents Planning Policy Design

Phase 20 Step 1 is documentation-only. It adds
[`docs/design/phase20_max_intents_policy.md`](design/phase20_max_intents_policy.md)
as the no-code design record for a future maximum accepted intents per plan
policy after minimal `ExecutionPlan` construction.

The design clarifies that a future max-intents policy may accept the first `N`
intents from an `ExecutionPlan`, preserve original plan order and object
identity, and wrap later intents in `SkippedExecutionIntent` with deterministic
reason text such as `"max_intents_per_plan_exceeded"`. This is a pre-broker,
batch-level planning decision only.

`PlanningPolicyResult` remains a pre-broker result container with
`accepted_intents` and `skipped_intents`. `SkippedExecutionIntent` remains a
traceability wrapper with `intent` and `reason`. `ExecutionIntent` and
`ExecutionPlan` remain unchanged. The current
`apply_noop_execution_planning_policy(...)` function remains pass-through only:
it accepts every input intent and returns `skipped_intents=()`.

No production Python code, tests, imports, runtime behavior, policy config
object, max-intents policy function, broker routing, Alpaca changes,
`submit_order`, order submission, idempotency, `client_order_id` generation,
batch cash reservation, buying-power reservation, same-symbol conflict
resolution, duplicate/competing order policy, priority/ranking policy,
persistence writes, audit logging writes, scheduler/runtime behavior,
portfolio mutation, fills, reconciliation changes, ML, or LLM trading-path
logic was added.

The full suite remains:

```text
python -m pytest
379 passed, 4 skipped
```

## Phase 20 Step 2 Max Intents Planning Policy Contract

Phase 20 Step 2 adds the first real execution-planning policy contract in:

```text
src/algotrader/orchestration/execution_planning_policy.py
```

The new immutable config is:

```text
MaxAcceptedIntentsPolicyConfig(max_accepted_intents: int)
```

`max_accepted_intents` must be exactly an `int` greater than or equal to `1`.
`bool` is rejected even though it is an `int` subclass, and `None`, `0`,
negative values, `float`, `str`, and `Decimal` values are rejected. `None` does
not mean no cap; `apply_noop_execution_planning_policy(...)` remains the
separate no-cap pass-through policy.

The new deterministic reason constant is:

```text
MAX_INTENTS_PER_PLAN_EXCEEDED_REASON = "max_intents_per_plan_exceeded"
```

`apply_max_intents_execution_planning_policy(plan, config)` accepts the first
`config.max_accepted_intents` intents in existing `ExecutionPlan` order and
wraps remaining intents in `SkippedExecutionIntent` with the deterministic
reason above. Accepted and skipped `ExecutionIntent` object identity is
preserved, and each source `SignalRiskEvaluation` remains traceable through
`source_evaluation`.

The policy is pure, deterministic, offline, broker-agnostic, and pre-broker. It
does not mutate the input plan, intents, or source evaluations. It does not
perform cash reservation, buying-power reservation, same-symbol conflict
handling, duplicate/competing order policy, deduplication, priority/ranking,
idempotency, `client_order_id` generation, broker routing, order submission,
persistence writes, audit logging writes, scheduler/runtime behavior,
portfolio mutation, fills, reconciliation changes, ML, or LLM trading-path
logic.

Focused validation:

```text
python -m pytest tests/unit/test_execution_planning_policy.py
64 passed

python -m pytest tests/unit/test_dependency_direction.py
6 passed
```

The full suite is now:

```text
python -m pytest
413 passed, 4 skipped
```

## Phase 20 Step 3 Max Intents Policy Traceability Hardening

Phase 20 Step 3 is tests and documentation only. It adds focused max-intents
traceability hardening coverage in:

```text
tests/unit/test_execution_planning_policy.py
```

The added tests prove that `apply_max_intents_execution_planning_policy(...)`
preserves accepted `ExecutionIntent` identity, preserves skipped
`ExecutionIntent` identity through `SkippedExecutionIntent.intent`, preserves
deterministic accepted and skipped ordering, uses the deterministic
`"max_intents_per_plan_exceeded"` skip reason, and does not mutate the original
`ExecutionPlan`.

Traceability remains source-driven. Accepted source evaluations remain
reachable through `result.accepted_intents[n].source_evaluation`, and skipped
source evaluations remain reachable through
`result.skipped_intents[n].intent.source_evaluation`. Proposed orders, risk
verdicts, and statuses remain reachable only through those source evaluations.

The hardening tests also pin that forbidden broker, execution, runtime,
persistence, idempotency, `client_order_id`, cash, buying-power,
priority/ranking, direct order/risk/status, and skip provenance fields are not
exposed by the max-intents policy result surface.

No production Python code, imports, runtime behavior, broker routing, Alpaca
changes, `submit_order`, order submission, idempotency, `client_order_id`
generation, batch cash reservation, buying-power reservation, same-symbol
conflict resolution, duplicate/competing order policy, priority/ranking policy,
persistence writes, audit logging writes, scheduler/runtime behavior, portfolio
mutation, fills, reconciliation changes, ML, or LLM trading-path logic was
added.

The full suite is now:

```text
python -m pytest
415 passed, 4 skipped
```

## Phase 21 Step 1 Research/Validation Boundary Design

Phase 21 Step 1 started and completed as documentation-only. It adds the new
design boundary in:

```text
docs/design/phase21_research_validation_boundary.md
```

The design separates historical research, feature exploration, backtesting,
walk-forward validation, regime analysis, strategy notebooks/scripts, and
LLM-assisted research summaries from validated artifacts and the deterministic
trading core.

Research outputs remain advisory. A signal, feature, or strategy can affect
execution flow only after a reviewed artifact records the hypothesis, dataset
scope, assumptions, exact definitions, metrics, acceptance criteria, bias and
leakage controls, and approval status. Future implementation should begin with
contracts and types, then test-first pure deterministic logic, before any
runtime wiring.

The deterministic core remains separate from research/backtesting/LLM
workflows. It consumes only approved, explicit, validated inputs; normal pytest
remains offline and credential-free; and research outputs must be promoted
through explicit deterministic contracts before they can influence execution.

LLMs may assist with research narration, experiment summaries, hypothesis
generation, and journaling. LLMs must not generate live trade decisions, mutate
execution plans, approve orders, bypass risk checks, interact with brokers, or
enter the trading hot path.

No production code, tests, runtime behavior, broker behavior, Alpaca changes,
`submit_order`, scheduler/runtime behavior, persistence implementation,
idempotency, `client_order_id`, cash reservation, same-symbol conflict policy,
duplicate/competing order policy, priority/ranking implementation, portfolio
mutation, fills, ML training implementation, live data ingestion, or LLM
trading-path logic was added.

The Phase 21 Step 1 full-suite checkpoint was:

```text
python -m pytest
415 passed, 4 skipped
```

## Phase 21 Step 2 Validated Research Artifact Contract

Phase 21 Step 2 adds the minimal validated research artifact contract in:

```text
src/algotrader/research/validated_artifact.py
src/algotrader/research/__init__.py
```

The new contracts are immutable, slotted dataclasses:

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

`ValidatedResearchArtifact` is a metadata/evidence contract only. It records a
reviewed artifact identifier, version, validation timestamp, metrics,
assumptions, limitations, and approved advisory uses. Tuple fields are stored
immutably and preserve metric, assumption, limitation, and approval order.
Empty required strings are rejected.

The focused tests live in:

```text
tests/unit/test_validated_research_artifact.py
tests/unit/test_dependency_direction.py
```

They prove immutability, slots, tuple storage, input order preservation, empty
string validation, absence of forbidden trading-path fields, no broker or
Alpaca behavior, no order, submit, fill, client-order-id, cash, portfolio, or
ranking behavior, no I/O, network, broker, or ingestion calls, and dependency
independence from execution planning, risk, broker, runtime, and persistence
modules.

This phase does not create signals, approve trades, mutate execution plans,
interact with broker, Alpaca, scheduler/runtime, persistence, or live data, or
put LLMs in the trading hot path.

Focused validation:

```text
python -m pytest tests/unit/test_validated_research_artifact.py
25 passed

python -m pytest tests/unit/test_dependency_direction.py
7 passed
```

The full suite is now:

```text
python -m pytest
441 passed, 4 skipped
```

## Phase 21 Step 3 Validated Research Artifact Traceability Hardening

Phase 21 Step 3 is tests and documentation only. It changes no production
source and keeps `ResearchMetric` and `ValidatedResearchArtifact` as
metadata/evidence contracts only.

The hardened tests live in:

```text
tests/unit/test_validated_research_artifact.py
```

They prove that metric object identity is preserved inside
`ValidatedResearchArtifact.metrics`, metrics preserve deterministic order,
assumptions preserve deterministic order, limitations preserve deterministic
order, approved advisory uses preserve deterministic order, and tuple fields
cannot be mutated after construction.

The tests also pin that validated research artifacts remain advisory metadata
only. They do not expose trading-path fields such as symbols, sides,
quantities, orders, order IDs, client order IDs, broker or Alpaca fields,
submission fields, fills, cash, buying power, reservations, portfolio,
positions, risk approval, execution plans, priority, rank, or score. They
remain independent from `ExecutionPlan`, `ExecutionIntent`,
`PlanningPolicyResult`, and risk-evaluation types.

Validated research artifacts do not create signals, approve trades, mutate
execution plans, interact with broker, Alpaca, scheduler/runtime, persistence,
or live data, add ML training, or put LLMs in the trading hot path.

Focused validation:

```text
python -m pytest tests/unit/test_validated_research_artifact.py
34 passed

python -m pytest tests/unit/test_dependency_direction.py
7 passed
```

The full suite is now:

```text
python -m pytest
450 passed, 4 skipped
```

## Phase 22 Step 1 Validated Signal Definition Boundary Design

Phase 22 Step 1 is documentation-only. It adds the new design boundary in:

```text
docs/design/phase22_validated_signal_definition_boundary.md
```

The design defines a future validated signal definition as a reviewed,
versioned, deterministic signal-rule contract supported by a validated research
artifact. A validated signal definition is not raw research output, not a
backtest result, not a feature, not a strategy, not an execution intent, not an
execution plan, and not a broker order.

The future metadata may include a signal id, name, version, description, source
validated research artifact id/version, required inputs, output type,
deterministic evaluation rule reference, allowed advisory use, assumptions,
limitations, and validation evidence references.

The design explicitly excludes symbol-specific live recommendations, side,
quantity, order type, broker fields, Alpaca fields, `submit_order`, cash or
buying-power reservation, portfolio mutation, risk approval, ranking/priority
behavior, execution-plan mutation, fills, and LLM-generated trade decisions.

The intended promotion path is:

```text
research hypothesis
  -> validated research artifact
  -> approved signal definition
  -> future deterministic signal evaluator
  -> future signal-to-risk flow
```

Validated research artifacts remain advisory. Validated signal definitions are
not execution decisions, do not create signals by themselves, do not approve
trades, do not mutate execution plans, and do not interact with broker, Alpaca,
scheduler/runtime, persistence, or live data. LLMs may summarize research and
document hypotheses, but they may not generate live signal outputs, approve
trades, mutate execution plans, bypass deterministic risk checks, or enter the
trading hot path.

No production code, tests, runtime behavior, signal computation, strategy
implementation, feature computation, ranking/priority policy, broker behavior,
execution-plan mutation, order submission, scheduler/runtime behavior,
persistence implementation, live data ingestion, ML training, or LLM
trading-path logic was added.

The latest full-suite checkpoint remains:

```text
python -m pytest
450 passed, 4 skipped
```

## Phase 22 Step 2 Validated Signal Definition Contract

Phase 22 Step 2 adds the minimal validated signal definition contract in:

```text
src/algotrader/signals/validated_signal_definition.py
src/algotrader/signals/__init__.py
```

The new contract is an immutable, slotted dataclass:

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

`ValidatedSignalDefinition` is definition metadata only. It records stable
signal identity, source validated research artifact id/version strings,
required input names, expected output type, deterministic evaluation rule
reference, approved advisory uses, assumptions, and limitations. Tuple fields
are stored immutably and preserve required-input, approved-use, assumption, and
limitation order. Empty required strings are rejected.

The focused tests live in:

```text
tests/unit/test_validated_signal_definition.py
tests/unit/test_dependency_direction.py
```

They prove immutability, slots, tuple storage, input order preservation, empty
string validation, metadata-only fields, absence of forbidden trading-path
fields, no buy/sell/hold recommendation behavior, no I/O, network, broker,
ingestion, or scheduling calls, independence from execution planning, risk,
broker, and runtime modules, and stable id/version-only references to validated
research artifacts.

This phase does not evaluate signals, create execution intents, approve trades,
mutate execution plans, interact with broker, Alpaca, scheduler/runtime,
persistence, or live data, add ML training, or put LLMs in the trading hot
path.

Focused validation:

```text
python -m pytest tests/unit/test_validated_signal_definition.py
29 passed

python -m pytest tests/unit/test_dependency_direction.py
7 passed
```

The full suite is now:

```text
python -m pytest
479 passed, 4 skipped
```

## Phase 22 Step 3 Validated Signal Definition Traceability Hardening

Phase 22 Step 3 is tests and documentation only. It changes no production
source and keeps `ValidatedSignalDefinition` as definition metadata only.

The hardened tests live in:

```text
tests/unit/test_validated_signal_definition.py
```

They prove that `source_artifact_id` and `source_artifact_version` are
preserved exactly, `required_inputs` preserve deterministic order,
`approved_for` preserves deterministic order, `assumptions` preserve
deterministic order, `limitations` preserve deterministic order, and tuple
fields cannot be mutated after construction.

The tests also pin that validated signal definitions remain metadata-only. They
do not expose trading-path fields such as symbols, sides, quantities, orders,
order IDs, client order IDs, broker or Alpaca fields, submission fields, fills,
cash, buying power, reservations, portfolio, positions, risk approval,
execution intents, execution plans, priority, rank, or score. They remain
independent from `ValidatedResearchArtifact` runtime objects, `ExecutionPlan`,
`ExecutionIntent`, `PlanningPolicyResult`, risk-evaluation types, broker
modules, runtime/scheduler modules, and persistence modules.

Validated signal definitions do not evaluate signals, produce buy/sell/hold
outputs, create execution intents, approve trades, mutate execution plans,
interact with broker, Alpaca, scheduler/runtime, persistence, or live data, add
ML training, or put LLMs in the trading hot path.

Focused validation:

```text
python -m pytest tests/unit/test_validated_signal_definition.py
38 passed

python -m pytest tests/unit/test_dependency_direction.py
7 passed
```

The full suite is now:

```text
python -m pytest
488 passed, 4 skipped
```

## Phase 23 Step 1 Signal Evaluation Clock Boundary Design

Phase 23 Step 1 is documentation-only. It adds the new design boundary in:

```text
docs/design/phase23_signal_evaluation_clock_boundary.md
```

The design defines future deterministic signal evaluation as a pure advisory
boundary that may consume approved `ValidatedSignalDefinition` metadata plus
explicit feature/input snapshots, explicit observation timestamps, an explicit
`as_of` timestamp, deterministic context, and snapshot fingerprints.

Future evaluator outputs may include only advisory metadata such as signal
id/version, evaluation timestamp, as-of timestamp, deterministic signal value,
score or bucket, reason or explanation code, input snapshot fingerprint,
evaluation fingerprint/id, and assumptions or limitations references.

The design explicitly excludes `ProposedOrder`, orders, order IDs, client order
IDs, broker requests, symbol-specific order instructions, execution-command
side, quantity, cash or buying-power reservation, portfolio mutation, risk
approval, execution intents, execution plans, fills, ranking/priority
decisions, and LLM-generated trade decisions.

Clock and as-of rules are explicit. Future deterministic signal, risk, and
orchestration layers should receive time as data, reject naive datetimes, prefer
UTC internally, and avoid direct calls to wall-clock APIs, random generators,
UUID randomness, or environment-variable reads except in explicit boundary
modules.

Lookahead-bias prevention is part of the future contract: input observations
after `as_of` must be rejected, snapshots must be explicit, feature values must
be timestamped or traceable to timestamped windows, hidden live data fetches and
implicit data revisions are forbidden, and retrospective parameter changes
require a new version.

No production code, tests, runtime behavior, signal evaluator implementation,
clock implementation, signal computation, feature computation, strategy engine,
Signal -> Risk bridge, ranking/priority policy, broker behavior, Alpaca
changes, order submission, scheduler/runtime behavior, persistence
implementation, live data ingestion, ML training, or LLM trading-path logic was
added.

The full suite remains:

```text
python -m pytest
488 passed, 4 skipped
```

## Phase 23 Step 2 Minimal Clock / Timestamp Contract

Phase 23 Step 2 adds the minimal deterministic time contract in:

```text
src/algotrader/core/time.py
```

The new contract includes:

```text
require_utc_datetime(value: datetime) -> datetime
Clock.now() -> datetime
FixedClock(timestamp).now() -> datetime
assert_not_after_as_of(observed_at, as_of) -> None
```

`require_utc_datetime(...)` accepts only timezone-aware UTC datetimes and
returns the original datetime object when valid. It rejects naive datetimes,
non-datetime values, and non-UTC aware datetimes instead of normalizing them.

`Clock` is an injectable protocol only. `FixedClock` is a frozen, slotted
dataclass that stores one validated UTC timestamp and returns exactly that
stored object from `now()`. It does not call `datetime.now`,
`datetime.utcnow`, `time.time`, `time.monotonic`, random generators, UUID
randomness, environment variables, I/O, network, brokers, scheduler/runtime, or
persistence.

`assert_not_after_as_of(...)` validates both timestamps and rejects
`observed_at > as_of`. It is a lookahead-prevention helper only, not a signal
evaluator.

Focused validation:

```text
python -m pytest tests/unit/test_time_contracts.py
21 passed

python -m pytest tests/unit/test_dependency_direction.py
8 passed
```

This phase does not evaluate signals, compute features, implement a strategy,
rank or prioritize candidates, approve trades, create execution intents, mutate
execution plans, interact with broker, Alpaca, scheduler/runtime, persistence,
or live data, add ML training, or put LLMs in the trading hot path.

The full suite is now:

```text
python -m pytest
510 passed, 4 skipped
```

## Phase 23 Step 3 Clock / Timestamp Traceability Hardening

Phase 23 Step 3 is tests and documentation only. It changes no production
source and keeps `src/algotrader/core/time.py` unchanged.

The hardened tests live in:

```text
tests/unit/test_time_contracts.py
tests/unit/test_dependency_direction.py
```

They prove that `require_utc_datetime(...)` preserves the exact valid UTC
datetime object, `FixedClock.now()` repeatedly returns the exact stored
datetime object, `FixedClock` remains frozen and slotted, naive datetimes are
rejected, non-UTC aware datetimes are rejected, `assert_not_after_as_of(...)`
allows equality and earlier observations, and `observed_at > as_of` is
rejected.

The tests also pin that the time module remains independent from signals,
research, risk, orchestration, execution, broker, Alpaca, scheduler/runtime,
persistence, ML, and LLM modules. It exposes no trading-path fields or behavior
such as symbol, side, quantity, order, order id, client order id, broker,
Alpaca, `submit_order`, fill, cash, buying power, portfolio, risk approval,
execution plan, priority, rank, or score. It does not call hidden
nondeterministic APIs such as `datetime.now`, `datetime.utcnow`, `time.time`,
`time.monotonic`, random generators, UUID randomness, or `os.environ`.

Time contracts remain deterministic primitives only. They do not evaluate
signals, fetch live data, read system time in deterministic paths, approve
trades, mutate execution plans, interact with broker, Alpaca,
scheduler/runtime, persistence, ML, or LLM trading-path logic.

Focused validation:

```text
python -m pytest tests/unit/test_time_contracts.py
26 passed

python -m pytest tests/unit/test_dependency_direction.py
8 passed
```

The full suite is now:

```text
python -m pytest
515 passed, 4 skipped
```

## Phase 24 Step 1 Signal Evaluation Result Boundary Design

Phase 24 Step 1 is documentation only. It creates the future
`SignalEvaluationResult` boundary in:

```text
docs/design/phase24_signal_evaluation_result_boundary.md
```

The design defines `SignalEvaluationResult` as the future advisory deterministic
output of applying a validated signal definition to explicit input snapshots at
an explicit `as_of` boundary. It is traceable to signal definition id/version,
source artifact id/version, input snapshot id or fingerprint, UTC-aware
`as_of`, UTC-aware `evaluated_at`, deterministic output values, reason codes,
diagnostics, assumptions, and limitations.

The design also defines what the result is not: it is not an order, broker
request, risk approval, execution intent, execution plan, portfolio mutation,
ranking or priority decision, or LLM decision. Future result fields must not
include `ProposedOrder`, order ids, client order ids, broker or Alpaca fields,
`submit_order`, symbol-specific order instructions, side as an execution
command, quantity, cash, buying power, reservations, portfolio or position
mutation, `risk_approved`, execution intent, execution plan, fills, priority,
rank as execution priority, or LLM-generated decisions.

The future result boundary reaffirms the Phase 23 clock contract: `as_of` must
be explicit, `evaluated_at` must be explicit or provided by an injected
deterministic clock in a future implementation, all timestamps must be
UTC-aware, naive datetimes must be rejected, hidden system time reads are not
allowed, and no input observation timestamp may be after `as_of`.

Reproducibility remains required. The same signal definition, same inputs, and
same `as_of` timestamp must produce the same future advisory result.
Evaluation ids should eventually be deterministic, input snapshot fingerprints
should eventually be content-addressable, and future evaluation must not depend
on network calls, broker calls, LLM calls, or mutable global state.

This phase adds no production code, tests, runtime behavior,
`SignalEvaluationResult` implementation, signal evaluator implementation,
signal computation, strategy implementation, feature computation, ranking or
priority behavior, execution-plan mutation, risk approval behavior, broker
behavior, Alpaca behavior, order submission, scheduler/runtime behavior,
persistence implementation, live data ingestion, ML training, or LLM
trading-path logic.

## Phase 24 Step 2 Minimal SignalEvaluationResult Contract

Phase 24 Step 2 adds the minimal advisory signal-evaluation result contract in:

```text
src/algotrader/signals/signal_evaluation_result.py
src/algotrader/signals/__init__.py
```

The new contract is an immutable, slotted dataclass:

```text
SignalEvaluationResult(
    evaluation_id,
    signal_id,
    signal_version,
    source_artifact_id,
    source_artifact_version,
    as_of,
    evaluated_at,
    input_fingerprint,
    output_value,
    reason_code,
    diagnostics,
    assumptions,
    limitations,
)
```

`SignalEvaluationResult` is advisory evaluation metadata only. It records stable
evaluation identity, signal definition id/version, source artifact id/version,
explicit UTC-aware `as_of`, explicit UTC-aware `evaluated_at`, input
fingerprint, deterministic advisory output value, reason code, diagnostics,
assumptions, and limitations. Tuple fields are stored immutably and preserve
diagnostic, assumption, and limitation order. Empty required strings are
rejected.

The focused tests live in:

```text
tests/unit/test_signal_evaluation_result.py
tests/unit/test_dependency_direction.py
```

They prove immutability, slots, tuple storage, tuple order preservation, empty
string validation, naive and non-UTC datetime rejection, UTC-aware datetime
identity preservation, advisory metadata-only fields, absence of forbidden
trading-path fields, no I/O, network, broker, ingestion, or scheduling calls,
and independence from execution planning, risk, broker, runtime, persistence,
ML, and LLM modules.

This phase does not evaluate signals, compute features, implement strategies,
rank or prioritize candidates, create execution intents, approve trades, mutate
execution plans, interact with broker, Alpaca, scheduler/runtime, persistence,
or live data, add ML training, or put LLMs in the trading hot path.

Focused validation:

```text
python -m pytest tests/unit/test_signal_evaluation_result.py
33 passed

python -m pytest tests/unit/test_dependency_direction.py
8 passed
```

The full suite is now:

```text
python -m pytest
548 passed, 4 skipped
```

## Phase 24 Step 3 SignalEvaluationResult Traceability Hardening

Phase 24 Step 3 is tests and documentation only. It changes no production
source and keeps `SignalEvaluationResult` as a minimal advisory metadata
contract.

The hardened tests live in:

```text
tests/unit/test_signal_evaluation_result.py
tests/unit/test_dependency_direction.py
```

They prove exact identity preservation of `as_of`, exact identity preservation
of `evaluated_at`, deterministic ordering for `diagnostics`, `assumptions`, and
`limitations`, tuple immutability after construction, exact preservation of
trace string fields, advisory-only surface area, absence of forbidden
trading-path fields, no signal output behavior, no strategy behavior, no
execution intent creation, no risk approval behavior, no execution-plan
mutation behavior, no broker/account/order/fill fields, no
scheduler/runtime/persistence fields, no ML or LLM trading-path fields, and no
dependency on execution, risk, broker, runtime, persistence, ML, or LLM
modules.

This phase does not evaluate signals, compute features, implement strategies,
rank or prioritize candidates, create execution intents, approve trades, mutate
execution plans, interact with broker, Alpaca, scheduler/runtime, persistence,
or live data, add ML training or inference, or put LLMs in the trading hot
path.

Focused validation:

```text
python -m pytest tests/unit/test_signal_evaluation_result.py
40 passed

python -m pytest tests/unit/test_dependency_direction.py
8 passed
```

The full suite is now:

```text
python -m pytest
555 passed, 4 skipped
```

## Phase 25 Step 1 Signal Evaluator Boundary Design

Phase 25 Step 1 is documentation-only. It creates the future deterministic
signal evaluator boundary in:

```text
docs/design/phase25_signal_evaluator_boundary.md
```

The design defines a future evaluator as an offline-safe deterministic boundary
that may later transform `ValidatedSignalDefinition` metadata plus explicit
deterministic input snapshots, an explicit UTC-aware `as_of` timestamp, and an
explicit UTC-aware `evaluated_at` timestamp or deterministic clock into
advisory `SignalEvaluationResult` objects.

The future output remains traceable to signal definition id/version, source
validated research artifact id/version, input snapshot identity or fingerprint,
`as_of`, and `evaluated_at`. It remains advisory metadata only: not an
execution signal, not a trade approval, not an order request, not risk
approval, not an execution intent, not an execution plan, and not a broker
payload.

The boundary requires deterministic guarantees: same inputs produce the same
result, no hidden wall-clock access, no environment-variable driven behavior,
no random behavior, no network calls, no file or database writes, no broker,
account, position, order, or fill access, no input mutation, no LLM calls, and
no ML training or inference unless later promoted through explicit
deterministic contracts.

The design records the as-of and lookahead rule that all observations used by
evaluation must satisfy `observed_at <= as_of`. Future observations must be
rejected, and the future evaluator should use the existing deterministic time
contract with explicit UTC-aware timestamps.

This phase does not add production code, tests, runtime behavior, signal
evaluator implementation, signal computation, feature computation, strategy
logic, ranking or priority behavior, signal-to-risk conversion, risk approval,
execution intent creation, execution-plan mutation, portfolio mutation, broker
or Alpaca behavior, order submission, scheduler/runtime behavior, persistence,
live data ingestion, ML training or inference, or LLM trading-path logic.

The latest full-suite checkpoint remains:

```text
python -m pytest
555 passed, 4 skipped
```

## Phase 25 Step 2 Minimal Signal Evaluation Input Snapshot Contract

Phase 25 Step 2 adds the minimal signal-evaluation input snapshot/reference
contract in:

```text
src/algotrader/signals/signal_evaluation_input.py
src/algotrader/signals/__init__.py
```

The new contract is an immutable, slotted dataclass:

```text
SignalEvaluationInputSnapshot(
    snapshot_id,
    as_of,
    required_input_names,
    source_ids,
)
```

`SignalEvaluationInputSnapshot` is metadata/reference-only. It records stable
snapshot identity, an explicit UTC-aware `as_of` timestamp, ordered required
input names, and ordered source identifiers. It exists only to provide
deterministic, explicit input traceability for a future evaluator.

The contract validates `as_of` with the existing deterministic time contract,
rejects naive and non-UTC datetimes, rejects empty or blank trace strings,
converts iterable metadata fields into tuples, preserves tuple ordering,
preserves accepted string values exactly, and is frozen and slotted.

The focused tests live in:

```text
tests/unit/test_signal_evaluation_input.py
tests/unit/test_dependency_direction.py
```

They prove contract existence, exact field set, immutability, slots, valid
construction, UTC-aware `as_of` validation, naive and non-UTC datetime
rejection, `as_of` identity preservation, tuple coercion, deterministic tuple
ordering, tuple immutability, string validation, exact string preservation,
metadata/reference-only surface area, absence of signal output fields, absence
of score/direction/confidence/order/risk/execution fields, dependency
independence, and absence of hidden wall-clock, random, network, filesystem
write, environment, broker, runtime, persistence, ML, and LLM calls.

This phase does not add a signal evaluator, signal computation, feature
computation, strategy logic, ranking or priority behavior, signal-to-risk
conversion, risk approval, execution intent creation, execution-plan mutation,
portfolio mutation, broker or Alpaca behavior, order submission,
scheduler/runtime behavior, persistence writes, live data ingestion, network
calls, ML training or inference, or LLM trading-path logic.

Focused validation:

```text
python -m pytest tests/unit/test_signal_evaluation_input.py
29 passed

python -m pytest tests/unit/test_dependency_direction.py
9 passed
```

The full suite is now:

```text
python -m pytest
585 passed, 4 skipped
```

## Phase 25 Step 3 Signal Evaluation Input Snapshot Traceability Hardening

Phase 25 Step 3 is tests and documentation only. It changes no production
source and keeps `SignalEvaluationInputSnapshot` as a minimal
metadata/reference-only input traceability contract for a future evaluator.

The hardened tests live in:

```text
tests/unit/test_signal_evaluation_input.py
tests/unit/test_dependency_direction.py
```

They prove exact `as_of` identity preservation, exact `snapshot_id` string
preservation, exact `required_input_names` string preservation, exact
`source_ids` string preservation, deterministic ordering of both tuple fields,
tuple immutability after construction, and isolation from later mutation of
the original input lists.

The tests also pin that the snapshot has no signal output behavior, no
score/direction/confidence fields, no order/risk/execution fields, no
broker/account/position/fill fields, no portfolio/cash/buying-power fields, no
scheduler/runtime/persistence fields, no ML/LLM fields, and no dependency on
`SignalEvaluationResult`, risk, execution, broker, runtime, persistence, ML,
or LLM modules.

Hidden access remains forbidden: no wall-clock calls, random calls,
network/socket access, filesystem writes, environment-variable reads, broker
SDK imports, or Alpaca imports are allowed in the contract.

This phase does not add a signal evaluator, signal computation, feature
computation, strategy logic, ranking or priority behavior, signal-to-risk
conversion, risk approval, execution intent creation, execution-plan mutation,
portfolio mutation, broker or Alpaca behavior, order submission,
scheduler/runtime behavior, persistence, live data ingestion, ML training or
inference, or LLM trading-path logic.

Focused validation:

```text
python -m pytest tests/unit/test_signal_evaluation_input.py
47 passed

python -m pytest tests/unit/test_dependency_direction.py
9 passed
```

The full suite is now:

```text
python -m pytest
603 passed, 4 skipped
```

## Phase 26 Step 1 Signal Evaluator No-Op Boundary Design

Phase 26 Step 1 is documentation-only. It creates the future no-op signal
evaluator boundary in:

```text
docs/design/phase26_signal_evaluator_noop_boundary.md
```

The design defines a signal evaluator narrowly for this project: a future
deterministic boundary that may later receive `ValidatedSignalDefinition`,
`SignalEvaluationInputSnapshot`, explicit UTC-aware `as_of`, explicit
UTC-aware `evaluated_at`, and deterministic metadata already available through
existing contracts, then construct advisory `SignalEvaluationResult` metadata.

The future no-op specialization exists only to prove that deterministic
input/output boundary. It must not compute real signal values, inspect live
market data, compute features, rank, score, infer direction, approve or reject
trades, create execution intents, mutate execution plans, prepare orders,
interact with brokers, call ML, or call LLMs.

Evaluator output remains strictly advisory and pre-risk. A
`SignalEvaluationResult` produced by any evaluator, including a future no-op
evaluator, does not constitute a signal firing, recommendation, risk approval,
execution instruction, execution intent, order request, or broker payload. No
sizing decision, exposure calculation, cash reservation, buying-power check, or
portfolio-level reasoning has occurred when a result is returned.

The design records timestamp invariants for future implementation: `as_of` is
the logical time the result describes, `evaluated_at` is the UTC-aware time the
evaluation occurred, future evaluator behavior must enforce
`evaluated_at >= as_of`, no input `as_of` or observation timestamp may be after
the result `as_of`, and no lookahead bias is permitted.

Future evaluator behavior must remain deterministic for identical inputs,
offline-safe, credential-free, free of hidden wall-clock access, free of random
or environment-variable driven behavior, network-free, write-free, broker-free,
input-immutable, ML-free, and LLM-free. Future evaluator modules must not import
broker, Alpaca, execution, risk, runtime/scheduler, persistence, ML, or LLM
modules.

The design also records an open design point: if `SignalEvaluationResult`
cannot safely represent a no-op result without ambiguity, the next
implementation phase should harden `SignalEvaluationResult` first instead of
adding an evaluator. This phase does not add that marker and does not modify
`SignalEvaluationResult`.

This phase does not add production code, tests, runtime behavior, signal
evaluator implementation, no-op evaluator class, evaluator protocol, result
contract changes, signal computation, feature computation, strategy logic,
ranking or priority behavior, signal-to-risk conversion, risk approval,
execution intent creation, execution-plan mutation, portfolio mutation, broker
or Alpaca behavior, order submission, scheduler/runtime behavior, persistence,
live data ingestion, ML training or inference, or LLM trading-path logic.

The latest full-suite checkpoint remains:

```text
python -m pytest
603 passed, 4 skipped
```

## Phase 26 Step 2 SignalEvaluationResult No-Op Readiness Review

Phase 26 Step 2 reviews whether the existing `SignalEvaluationResult` contract
can safely represent a future no-op evaluator result without adding ambiguous
signal, strategy, risk, execution, or actionability semantics.

The review conclusion is that the current metadata-only contract is sufficient
for a future minimal no-op evaluator. It already preserves signal definition
identity/version, source artifact identity/version, input snapshot identity
through `input_fingerprint`, explicit UTC-aware `as_of`, explicit UTC-aware
`evaluated_at`, advisory `output_value`, `reason_code`, `diagnostics`,
`assumptions`, and `limitations`.

No no-op marker, `result_kind`, or `evaluator_kind` is needed before evaluator
implementation. A future no-op result does not need `score`, `direction`,
`confidence`, `actionable`, or `should_trade` fields. A no-op marker is not
inherently trading behavior, but adding one too early risks creating a decision
switch or actionability proxy. The safer path is to keep the first no-op
evaluator result empty/advisory in meaning while using only existing metadata
fields.

A future no-op evaluator result is not structurally distinguishable from a
later real evaluator result by field shape. That is acceptable for the first
no-op boundary because both are advisory metadata. If distinction is needed, it
should come from explicit trace metadata values such as `evaluation_id`,
`input_fingerprint`, `output_value`, `reason_code`, `diagnostics`,
`assumptions`, and `limitations`, not from trading-path or actionability
fields.

This phase strengthens contract-surface tests in:

```text
tests/unit/test_signal_evaluation_result.py
```

The focused additions pin that `SignalEvaluationResult` has no score,
direction, confidence, probability, actionability, `should_trade`, no-op marker,
`result_kind`, `evaluator_kind`, risk, execution, broker, order, runtime,
persistence, ML, or LLM fields, and that existing metadata fields can preserve a
metadata-only no-op trace without implying actionability.

This phase does not change production source and does not add runtime behavior,
signal evaluator implementation, no-op evaluator class, evaluator protocol,
result contract changes, signal computation, feature computation, strategy
logic, ranking or priority behavior, signal-to-risk conversion, risk approval,
execution intent creation, execution-plan mutation, portfolio mutation, broker
or Alpaca behavior, order submission, scheduler/runtime behavior, persistence,
live data ingestion, ML training or inference, or LLM trading-path logic.

Focused validation:

```text
python -m pytest tests/unit/test_signal_evaluation_result.py
42 passed

python -m pytest tests/unit/test_dependency_direction.py
9 passed
```

The full suite is now:

```text
python -m pytest
605 passed, 4 skipped
```

## Phase 26 Step 3 Minimal No-Op Signal Evaluator Contract

Phase 26 Step 3 adds the first evaluator-shaped production code in:

```text
src/algotrader/signals/noop_signal_evaluator.py
```

The new contract is a frozen, slotted class:

```text
NoOpSignalEvaluator.evaluate(
    definition,
    input_snapshot,
    *,
    as_of,
    evaluated_at,
) -> SignalEvaluationResult
```

`NoOpSignalEvaluator` accepts a `ValidatedSignalDefinition`, a
`SignalEvaluationInputSnapshot`, and explicit UTC-aware `as_of` and
`evaluated_at` timestamps. It validates timestamps through the deterministic
time contract, rejects naive and non-UTC datetimes, rejects
`evaluated_at < as_of`, rejects an input snapshot whose `as_of` is after the
result `as_of`, and returns an advisory `SignalEvaluationResult`.

The returned result preserves signal definition id/version, source artifact
id/version, input snapshot id through `input_fingerprint`, and accepted
timestamp object identity. Repeated calls with identical inputs produce equal
results. The evaluator does not mutate the signal definition or input snapshot.

The no-op output uses existing `SignalEvaluationResult` fields only. It uses
`NOOP_SIGNAL_EVALUATOR` as a non-actionable reason code and
`NO_SIGNAL_COMPUTED` as a non-numeric advisory output value. Diagnostics,
assumptions, and limitations state that no signal computation occurred and the
result is not a signal firing, recommendation, risk approval, or
execution-ready output.

This phase does not add `result_kind`, `evaluator_kind`, `is_noop`, or any
no-op marker field. It does not add real signal computation, feature
computation, strategy logic, scoring, ranking, confidence/probability, signal
direction, actionability flags, `should_trade`, signal-to-risk conversion,
risk approval, execution intent creation, execution-plan mutation, portfolio
mutation, broker or Alpaca behavior, order submission, scheduler/runtime
behavior, persistence writes, live data ingestion, network calls, ML training
or inference, or LLM trading-path logic.

Focused tests live in:

```text
tests/unit/test_noop_signal_evaluator.py
```

They prove existence, frozen/slotted shape, valid result construction, advisory
metadata wording, identity/version/input/timestamp preservation, UTC-aware
timestamp validation, `evaluated_at >= as_of`, input snapshot as-of guard,
deterministic repeated calls, input non-mutation, absence of score/confidence/
probability/direction/rank/priority/actionability/risk/execution/order/broker/
runtime/persistence/ML/LLM fields, and absence of forbidden imports or hidden
I/O, network, wall-clock, random, environment, broker, Alpaca, database,
persistence, ML, or LLM calls.

Phase 26 Step 3 focused validation at the time:

```text
python -m pytest tests/unit/test_noop_signal_evaluator.py
22 passed

python -m pytest tests/unit/test_dependency_direction.py
9 passed
```

At the end of Step 3, the full suite was:

```text
python -m pytest
627 passed, 4 skipped
```

## Phase 26 Step 4 No-Op Signal Evaluator Traceability Hardening

Phase 26 Step 4 is traceability hardening only. It strengthens
`tests/unit/test_noop_signal_evaluator.py` and updates documentation. No
production source code or production behavior was added.

`NoOpSignalEvaluator` remains deterministic and advisory-only. It proves the
evaluator input/output boundary without real signal computation and preserves
traceability without actionability. The hardened tests prove exact signal
definition id/version preservation, exact source validated research artifact
id/version preservation, exact input snapshot id preservation through
`input_fingerprint`, exact `as_of` and `evaluated_at` object identity, exact
`NOOP_SIGNAL_EVALUATOR` reason-code preservation, and deterministic ordering of
diagnostics, assumptions, and limitations.

The tests also harden determinism and side-effect boundaries: repeated calls
with identical inputs produce equal results, advisory tuple ordering is stable,
results do not depend on wall-clock APIs, environment variables, or random
state, and input definitions, snapshots, and tuple fields are not mutated.
Timestamp/lookahead coverage now explicitly accepts input snapshots at or
before the result `as_of` and rejects snapshots after the result `as_of`.

The no-op evaluator still does not score, rank, infer direction, set
confidence/probability, recommend trades, expose actionability, approve risk,
create execution intents, mutate execution plans, access live data, route to
brokers or Alpaca, submit orders, use scheduler/runtime/persistence behavior,
run ML, or use LLMs in the trading path. Normal pytest remains offline,
credential-free, and safe.

Focused validation:

```text
python -m pytest tests/unit/test_noop_signal_evaluator.py
29 passed

python -m pytest tests/unit/test_dependency_direction.py
9 passed
```

The full suite is now:

```text
python -m pytest
634 passed, 4 skipped
```

## Phase 27 Step 1 Real Signal Evaluator Admission Boundary Design

Phase 27 Step 1 is documentation-only. It adds:

```text
docs/design/phase27_real_signal_evaluator_admission_boundary.md
```

The new design defines the admission boundary for any future real deterministic
signal evaluator. The system has a no-op evaluator seam, but real signal
computation remains forbidden until explicit admission criteria are met.

The boundary records why real evaluator work is risky: it is the first place
the system could accidentally introduce strategy logic, feature computation,
predictive behavior, ranking, direction, actionability, risk-like semantics,
lookahead bias, or hidden data access. The document requires future real
evaluator work to name the validated signal definition, supporting validated
research artifact, exact deterministic inputs, observation timestamps,
availability proof at or before `as_of`, advisory output meaning, assumptions,
limitations, and tests for determinism, lookahead prevention, no side effects,
and no trading-path dependencies.

The design also records the important current limitation:
`SignalEvaluationInputSnapshot` provides metadata/reference traceability only
through `snapshot_id`, `as_of`, `required_input_names`, and `source_ids`. It
does not carry actual feature values or market observations. A future real
evaluator likely needs a separate deterministic input-value contract before it
can compute anything, but that contract is not designed or implemented here.

Even a future real evaluator output remains advisory and pre-risk. It is not a
recommendation, not trade approval, not an execution intent, not an order
request, not portfolio-aware, not broker-aware, and not actionability by
itself. Score, direction, or confidence would require a separate design phase
and must remain advisory only if ever admitted.

This phase adds no production code, tests, runtime behavior, real evaluator,
signal computation, feature computation, strategy logic, ranking, priority,
signal-to-risk conversion, risk approval, execution intent creation,
execution-plan mutation, portfolio mutation, broker or Alpaca behavior, order
submission, scheduler/runtime behavior, persistence, live data ingestion, ML
training or inference, or LLM trading-path logic. Normal pytest remains
offline, credential-free, and safe.

Verification after Phase 27 Step 1:

```text
python -m pytest
634 passed, 4 skipped
```

## Phase 27 Step 2 Deterministic Signal Input Value Boundary Design

Phase 27 Step 2 is documentation-only. It adds:

```text
docs/design/phase27_signal_input_value_boundary.md
```

The new design defines the future deterministic signal input-value boundary
needed before any real evaluator can compute signals. It records the difference
between `SignalEvaluationInputSnapshot` and future input values:
`SignalEvaluationInputSnapshot` is reference metadata only, preserving
`snapshot_id`, UTC-aware `as_of`, `required_input_names`, and `source_ids`; it
does not carry actual observed market values, feature values, bar payloads,
quote payloads, or computed inputs.

A future input-value contract is described conceptually as a small immutable
contract for explicit deterministic observed values, observation timestamps,
source traceability, value type constraints, and no-lookahead validation
support. The design discusses possible value subjects such as market prices,
bar fields, quote fields, volume, separately promoted feature values, and
timestamped static metadata without defining a final production contract.

The design records candidate fields for a future contract, including input
name, observed value, `observed_at`, source id, optional symbol or instrument
identity, optional value type or unit metadata, and optional quality or status
metadata. These remain design candidates only.

Timestamp rules require future `observed_at` values to be UTC-aware, reject
naive and non-UTC datetimes, and support validation that every observation used
by an evaluator satisfies `observed_at <= evaluator as_of`. The design also
forbids hidden wall-clock reads, fetching newer data internally, and inference
from data unavailable at `as_of`.

The value representation questions remain open: whether values should be
`Decimal`, `int`, `str`, `bool`, or a constrained union; whether floats should
be forbidden or isolated; whether bars and quotes should be referenced by
domain objects or flattened; whether feature values need a separate feature
contract first; how missing values, units, currency, timeframe, and ordering
should be represented.

This phase adds no production code, tests, input-value implementation, real
evaluator, signal computation, feature computation, strategy logic, ranking,
priority, score, direction, confidence, actionability, signal-to-risk
conversion, risk approval, execution intent creation, execution-plan mutation,
portfolio mutation, broker or Alpaca behavior, order submission,
scheduler/runtime behavior, persistence, live data ingestion, ML training or
inference, or LLM trading-path logic. Normal pytest remains offline,
credential-free, and safe.

Verification after Phase 27 Step 2:

```text
python -m pytest
634 passed, 4 skipped
```

## Phase 27 Step 3 Minimal Signal Input Value Contract

Phase 27 Step 3 adds the first minimal signal input-value production contract:

```text
src/algotrader/signals/signal_input_value.py
```

The new `SignalInputValue` contract is a frozen, slotted dataclass with exactly
four fields:

```text
name
value
observed_at
source_id
```

It carries one explicit observed value with source and timestamp traceability.
It validates `observed_at` as UTC-aware using the deterministic time contract,
rejects naive and non-UTC datetimes, rejects empty or blank `name` and
`source_id`, preserves accepted string values exactly, preserves accepted
`observed_at` identity, and stores the value without computation or
interpretation.

The first value surface accepts deterministic scalar values only: `Decimal`,
`int`, `str`, and `bool`. Mutable values, tuples, floats, and `None` are not
part of this minimal contract. Optional unit, quality, symbol, and instrument
fields remain deferred.

`SignalInputValue` does not perform lookahead validation against evaluator
`as_of`; it has no `as_of` field. Lookahead validation belongs to a later
assembly or evaluator-input boundary.

Focused tests live in:

```text
tests/unit/test_signal_input_value.py
```

They prove the contract exists, exposes the exact field set, is frozen and
slotted, validates UTC-aware `observed_at`, rejects naive and non-UTC
datetimes, preserves timestamp identity and exact accepted strings, preserves
values without computation, accepts the deterministic scalar value set, rejects
unsupported or mutable values, exposes no signal output/scoring/direction/
confidence/actionability surface, exposes no risk/execution/order/broker/
portfolio/runtime/persistence/ML/LLM fields, imports no forbidden downstream or
external modules, and makes no hidden wall-clock, random, network,
filesystem-write, environment-variable, or broker calls.

This phase adds no real evaluator, signal computation, feature computation,
strategy logic, scoring, ranking, confidence/probability, signal direction,
actionability flags, signal-to-risk conversion, risk approval, execution intent
creation, execution-plan mutation, portfolio mutation, broker or Alpaca
behavior, order submission, scheduler/runtime behavior, persistence writes,
live data ingestion, network calls, ML training or inference, or LLM
trading-path logic. Normal pytest remains offline, credential-free, and safe.

Focused validation:

```text
python -m pytest tests/unit/test_signal_input_value.py
30 passed

python -m pytest tests/unit/test_dependency_direction.py
9 passed
```

The full suite is now:

```text
python -m pytest
664 passed, 4 skipped
```

## Phase 27 Step 4 Signal Input Value Traceability Hardening

Phase 27 Step 4 hardens `SignalInputValue` traceability with tests and
documentation only. No production source or runtime behavior changed.

`SignalInputValue` remains an immutable observed-value contract. It carries one
explicit observed scalar value with `name`, `observed_at`, and `source_id`
traceability. It does not compute, normalize, rank, score, infer direction,
recommend trades, approve risk, create execution intents, mutate execution
plans, access live data, route to brokers or Alpaca, submit orders, use
scheduler/runtime/persistence, run ML, or use LLMs in the trading path.

The hardened tests prove exact `name` string preservation, exact `source_id`
string preservation, exact `observed_at` identity preservation, exact
`Decimal`, `int`, `str`, and `bool` value preservation, and that `bool` remains
distinct from `int` even though both are supported scalar value types. Accepted
values are stored exactly without normalization, rounding, conversion, or
interpretation.

The tests also strengthen immutability and value-surface guarantees: the
contract is frozen, slotted, has no `__dict__`, fields cannot be reassigned,
mutable values are rejected, floats are rejected, arbitrary objects are
rejected, and `None` remains unsupported.

Timestamp coverage now explicitly proves UTC-aware `observed_at` is accepted,
naive and non-UTC timestamps are rejected, the contract does not compare to an
evaluator `as_of`, does not perform lookahead validation internally, and does
not call wall-clock APIs. Lookahead validation belongs to later assembly or
evaluator phases with an explicit `as_of`.

Surface and dependency tests now pin that `SignalInputValue` exposes no signal
output, score, probability, confidence, rank, priority, direction,
actionability, approval, risk, execution, order, broker, Alpaca, account,
position, fill, portfolio, cash, buying-power, scheduler, runtime, persistence,
database, cache, ML/model/prediction, LLM/agent/prompt/output, or evaluator
behavior. AST checks guard against hidden wall-clock, random, environment,
network/socket, filesystem-write, database/cache/persistence, broker SDK,
Alpaca SDK, ML, LLM, and agent dependencies.

Focused validation:

```text
python -m pytest tests/unit/test_signal_input_value.py
47 passed

python -m pytest tests/unit/test_dependency_direction.py
9 passed
```

The full suite is now:

```text
python -m pytest
681 passed, 4 skipped
```

## Phase 28 Step 1 Signal Input Bundle Boundary Design

Phase 28 Step 1 is documentation-only. It adds:

```text
docs/design/phase28_signal_input_bundle_boundary.md
```

The new design defines why the project needs a future immutable signal input
bundle before any real evaluator can consume observed values. A future evaluator
should not receive loose lists, dictionaries, live data handles, feature stores,
runtime objects, broker clients, or persistence queries. It should receive one
explicit immutable bundle built before evaluation from precomputed observed
values.

The design distinguishes the existing contracts:

- `SignalEvaluationInputSnapshot`: reference metadata with `snapshot_id`,
  UTC-aware `as_of`, `required_input_names`, and `source_ids`, but no actual
  values
- `SignalInputValue`: one explicit observed scalar value with `name`, `value`,
  `observed_at`, and `source_id`
- future `SignalInputBundle`: an immutable collection of explicit observed
  values with deterministic ordering, duplicate-name policy, completeness
  validation against a snapshot, lookahead validation against evaluator `as_of`,
  and source/timestamp traceability

The candidate future field set is intentionally small: `snapshot_id`, `as_of`,
and `values: tuple[SignalInputValue, ...]`. Optional source ids, completeness
status, quality status, value name index, and bundle fingerprint remain
deferred until justified by a later phase.

Open design questions remain for completeness behavior: whether validation
lives in the constructor or a separate pure function, whether missing inputs
raise immediately or produce a validation result, whether extra inputs are
allowed, and whether ordering follows snapshot `required_input_names` or
supplied input order.

The design records future lookahead rules: every `SignalInputValue.observed_at`
must be `<= bundle.as_of`, every value must be available at or before evaluator
`as_of`, future observations must be rejected, and neither bundle construction
nor evaluator code may fetch newer data or rely on wall-clock time to infer
availability.

A bundle is only an input container. It is not a signal result,
recommendation, score, rank, direction, risk approval, execution intent, order
request, or portfolio decision. This phase adds no production code, tests,
bundle implementation, real evaluator, signal computation, feature
computation, strategy logic, scoring, ranking, confidence/probability, signal
direction, actionability, risk approval, execution intent creation,
execution-plan mutation, portfolio mutation, broker or Alpaca behavior, order
submission, scheduler/runtime behavior, persistence writes, live data
ingestion, network calls, ML training or inference, or LLM trading-path logic.

Verification after Phase 28 Step 1:

```text
python -m pytest
681 passed, 4 skipped
```

## Phase 28 Step 2 Minimal Signal Input Bundle Contract

Phase 28 Step 2 adds:

```text
src/algotrader/signals/signal_input_bundle.py
tests/unit/test_signal_input_bundle.py
```

`SignalInputBundle` is a frozen, slotted dataclass with exactly
`snapshot_id`, `as_of`, and `values`. It groups explicit `SignalInputValue`
objects for future evaluator use, coerces incoming value iterables to tuples,
preserves supplied value ordering and input value object identity, rejects empty
bundles, rejects duplicate `SignalInputValue.name` values, validates `as_of` as
UTC-aware, and rejects lookahead values where
`SignalInputValue.observed_at > bundle.as_of`.

Completeness validation against `SignalEvaluationInputSnapshot` remains
deferred to a later pure-validation phase or helper. The bundle does not compute
signals or features and does not implement a real evaluator. It does not score,
rank, infer direction, recommend trades, expose actionability, approve risk,
create execution intents, mutate execution plans, access live data, route to
brokers or Alpaca, submit orders, use scheduler/runtime/persistence behavior,
run ML, or use LLMs in the trading path.

Normal pytest remains offline, credential-free, and safe.

Verification after Phase 28 Step 2:

```text
python -m pytest
717 passed, 4 skipped
```

## Phase 28 Step 3 Signal Input Bundle Traceability Hardening

Phase 28 Step 3 is tests/docs only. No production behavior was added.

The strengthened tests harden `SignalInputBundle` traceability and safety:

- exact `snapshot_id` string preservation
- exact `as_of` identity preservation
- exact `SignalInputValue` object identity preservation
- exact value ordering, names, source ids, observed timestamp identity, and
  payload preservation through the bundle
- tuple coercion and tuple immutability
- input-list mutation isolation
- equality for bundles built from the same values in the same order
- preservation of different supplied ordering for the same values
- duplicate-name rejection, including differing source ids, observed values,
  and observation timestamps
- exact case/whitespace behavior without name normalization
- lookahead rejection for any value with `observed_at > as_of`
- no completeness validation against `SignalEvaluationInputSnapshot`
- no signal output, score, rank, direction, confidence, actionability,
  evaluator-kind, result-kind, or no-op marker surface
- no risk, execution, broker, Alpaca, runtime, persistence, ML, LLM, or agent
  trading-path surface
- no hidden wall-clock, random, environment, network, filesystem-write,
  database/cache/persistence, broker SDK, Alpaca SDK, ML, or LLM imports/calls

`SignalInputBundle` remains an immutable grouping contract for explicit
`SignalInputValue` objects. It preserves value ordering and object identity,
rejects duplicate names and lookahead values, and still does not validate
completeness against `SignalEvaluationInputSnapshot`. It does not compute
signals or features, implement a real evaluator, score, rank, infer direction,
recommend trades, approve risk, create execution intents, mutate execution
plans, access live data, route to brokers or Alpaca, submit orders, use
scheduler/runtime/persistence behavior, run ML, or use LLMs in the trading
path.

Normal pytest remains offline, credential-free, and safe.

Verification after Phase 28 Step 3:

```text
python -m pytest
733 passed, 4 skipped
```

## Phase 28 Step 4 Signal Input Bundle Completeness Boundary Design

Phase 28 Step 4 is documentation-only. It adds:

```text
docs/design/phase28_signal_input_bundle_completeness_boundary.md
```

The new design documents the future boundary for validating whether a
`SignalInputBundle` satisfies a `SignalEvaluationInputSnapshot`. It records the
questions a later pure validation phase must answer: whether all required
snapshot input names are present in the bundle, which required names are
missing, how extra bundle inputs should be handled, whether snapshot ids must
match, and whether bundle and snapshot `as_of` timestamps must match exactly or
only satisfy an explicit compatibility rule.

The design keeps the current contract roles separate:

- `SignalEvaluationInputSnapshot` defines required input names and reference
  context, but carries no values
- `SignalInputBundle` carries explicit observed values, rejects duplicate names,
  and enforces lookahead safety, but does not know whether it satisfies a
  snapshot
- future completeness validation may compare names and metadata across those
  contracts, but must not inspect, compute, normalize, or interpret values

The recommended future direction is a small pure validation boundary before
evaluator use, rather than expanding the `SignalInputBundle` constructor. A
future evaluator may eventually require a validated signal definition, input
snapshot, input bundle, successful completeness validation, explicit `as_of`,
and explicit `evaluated_at`, but no evaluator or validation logic is
implemented here.

Missing input behavior, extra input policy, snapshot id compatibility, and
`as_of` compatibility remain open design questions. Any future implementation
should report missing or extra names deterministically and preserve lookahead
safety. The boundary must remain pure, offline-safe, credential-free, and free
of network calls, live data access, broker/account/order/fill access,
scheduler/runtime access, persistence writes, ML calls, and LLM calls in the
trading path.

This phase adds no production code, tests, completeness validator
implementation, completeness result contract, bundle constructor changes, real
evaluator, signal computation, feature computation, strategy logic, score,
direction, confidence, actionability, signal-to-risk conversion, risk approval,
execution intent creation, execution-plan mutation, portfolio mutation, broker
or Alpaca behavior, order submission, runtime/scheduler behavior, persistence,
live data ingestion, ML, or LLM trading-path behavior. Normal pytest remains
offline, credential-free, and safe.

Verification after Phase 28 Step 4:

```text
python -m pytest
733 passed, 4 skipped
```

## Phase 28 Step 5 Minimal Signal Input Bundle Completeness Validation Contract

Phase 28 Step 5 adds:

```text
src/algotrader/signals/signal_input_bundle_completeness.py
tests/unit/test_signal_input_bundle_completeness.py
```

`SignalInputBundleCompletenessResult` is a frozen, slotted metadata contract
with exactly:

```text
snapshot_id
bundle_snapshot_id
is_complete
missing_input_names
extra_input_names
```

`validate_signal_input_bundle_completeness(snapshot, bundle)` is a pure
validation function. It accepts a `SignalEvaluationInputSnapshot` and a
`SignalInputBundle`, compares only
`SignalEvaluationInputSnapshot.required_input_names` with
`SignalInputBundle.values[n].name`, and returns the completeness result. It
does not mutate either input or the underlying `SignalInputValue` objects.

Missing input names are reported deterministically in
`snapshot.required_input_names` order. Extra input names are reported
deterministically in `bundle.values` order. `is_complete` is true only when no
required input names are missing. Extra inputs are reported but do not make the
bundle incomplete in this phase. The function does not require snapshot id
equality and does not require `as_of` equality. Lookahead validation remains in
the `SignalInputBundle` constructor.

The new tests cover the result contract, exact field set, immutability, slots,
tuple immutability, validation function behavior, deterministic missing/extra
ordering, extra-input reporting without incompleteness, exact snapshot id and
bundle snapshot id preservation, absence of snapshot id or `as_of` equality
requirements, input non-mutation, repeated-call determinism, advisory-only
surface area, dependency isolation, and absence of hidden wall-clock, random,
environment, network, filesystem-write, database/cache/persistence, broker,
ML, or LLM calls/imports.

This phase does not change `SignalInputBundle` constructor behavior, does not
add completeness fields to `SignalInputBundle` or
`SignalEvaluationInputSnapshot`, and does not add a real evaluator, signal
computation, feature computation, strategy logic, score, direction, confidence,
actionability, signal-to-risk conversion, risk approval, execution intent
creation, execution-plan mutation, portfolio mutation, broker or Alpaca
behavior, order submission, runtime/scheduler behavior, persistence, live data
ingestion, ML, or LLM trading-path behavior. Normal pytest remains offline,
credential-free, and safe.

Focused validation after Phase 28 Step 5:

```text
python -m pytest tests/unit/test_signal_input_bundle_completeness.py
32 passed

python -m pytest tests/unit/test_dependency_direction.py
9 passed
```

The full suite is now:

```text
python -m pytest
765 passed, 4 skipped
```

## Phase 28 Step 6 Signal Input Bundle Completeness Traceability Hardening

Phase 28 Step 6 is tests/docs only. No production source or runtime behavior
changed.

The strengthened completeness tests harden:

- exact `SignalInputBundleCompletenessResult` field set
- frozen and slotted result behavior with no `__dict__`
- tuple field type and immutability
- complete and incomplete `is_complete` semantics
- deterministic missing-name ordering from `snapshot.required_input_names`
- deterministic extra-name ordering from `bundle.values`
- empty missing and extra tuples
- repeated-call equality and ordering stability
- extra inputs remain non-blocking in this phase
- missing required inputs plus extras remain incomplete
- exact snapshot id and bundle snapshot id preservation
- no snapshot id equality requirement
- no `as_of` equality requirement
- no lookahead validation inside completeness validation
- no comparison of `SignalInputValue.value`, `source_id`, or `observed_at`
- no mutation of `SignalEvaluationInputSnapshot`, `SignalInputBundle`, or
  underlying `SignalInputValue` objects
- output independence from environment variables and random state
- absence of signal result, score, rank, direction, confidence, probability,
  actionability, result-kind, evaluator-kind, or no-op marker fields
- absence of risk, execution, order, broker, Alpaca, account, position, fill,
  portfolio, cash, buying-power, scheduler, runtime, persistence, database,
  cache, ML/model/prediction, LLM, agent, prompt, or output concepts
- absence of hidden wall-clock, random, environment, network/socket,
  filesystem-write, database/cache/persistence, broker SDK, Alpaca SDK, ML, and
  LLM/agent imports or calls

`validate_signal_input_bundle_completeness(...)` remains a pure metadata
boundary. It compares required names and bundle value names only. It does not
inspect or interpret `SignalInputValue.value`, compute signals or features,
implement a real evaluator, score, rank, infer direction, recommend trades,
approve risk, create execution intents, mutate execution plans, access live
data, route to brokers or interact with Alpaca, submit orders, use
scheduler/runtime/persistence behavior, run ML, or use LLMs in the trading
path. Normal pytest remains offline, credential-free, and safe.

Focused validation after Phase 28 Step 6:

```text
python -m pytest tests/unit/test_signal_input_bundle_completeness.py
45 passed

python -m pytest tests/unit/test_dependency_direction.py
9 passed
```

The full suite is now:

```text
python -m pytest
778 passed, 4 skipped
```

## Phase 29 Step 1 First Real Evaluator Design Gate

Phase 29 Step 1 is documentation-only. It adds:

```text
docs/design/phase29_first_real_evaluator_design_gate.md
```

The new design gate defines what must be true before the first real
deterministic signal evaluator may be implemented. The pre-evaluator input
stack is now available, but real signal computation remains forbidden until a
future evaluator-specific design satisfies the gate.

The gate requires a future design to identify the
`ValidatedSignalDefinition`, supporting `ValidatedResearchArtifact`, required
snapshot input names, expected `SignalInputValue` names and value types,
completeness policy, expected `as_of` behavior, expected `evaluated_at`
behavior, advisory output semantics, assumptions, limitations, and required
deterministic, no-lookahead, side-effect, and dependency tests.

The gate preserves open completeness questions for the evaluator-specific
design: whether callers pass a precomputed completeness result, whether the
evaluator validates completeness internally, whether missing inputs raise or
produce an advisory failure result, whether extras are ignored or rejected, and
whether snapshot id or `as_of` equality is required.

A future real evaluator must use explicit inputs only. It must not fetch live
data, query a feature store, call a broker, read runtime state, infer missing
inputs, call wall-clock APIs internally, mutate input contracts, write files or
persistence, access network/socket APIs, import broker/Alpaca, runtime,
scheduler, risk, execution, ML, or LLM modules, or produce forbidden output
fields.

This phase does not select or implement a first real evaluator. It adds no
production code, tests, evaluator implementation, evaluator protocol, signal
computation, feature computation, strategy logic, score, direction,
confidence, actionability, risk approval, execution intent creation, broker or
Alpaca behavior, order submission, runtime/scheduler behavior, persistence,
live data ingestion, ML, or LLM trading-path behavior.

The latest full-suite checkpoint remains:

```text
python -m pytest
778 passed, 4 skipped
```

## Phase 29 Step 2 First Real Evaluator Candidate Selection

Phase 29 Step 2 is documentation-only. It adds:

```text
docs/design/phase29_first_real_evaluator_candidate_selection.md
```

It also updates:

```text
docs/design/phase29_first_real_evaluator_design_gate.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

The selected candidate for the next evaluator-specific design phase is a
minimal threshold-style advisory evaluator over one explicit scalar
`SignalInputValue`. The concept uses one required input name such as
`indicator_value`, consumes a deterministic scalar value from a
`SignalInputBundle`, requires successful completeness handling, and may
eventually produce advisory `SignalEvaluationResult` output.

The candidate was selected because it has a small input surface, deterministic
scalar values, no hidden data access, straightforward missing-input behavior,
straightforward no-lookahead testing, clear advisory-only output, no ranking,
no portfolio dependence, no broker/runtime/persistence dependence, and no
ML/LLM dependence.

The selection does not choose the exact validated signal definition, supporting
research artifact, input name, accepted value type, threshold semantics,
`output_value` meaning, reason codes, diagnostics, assumptions, limitations,
missing-input behavior, extra-input behavior, snapshot id compatibility,
`as_of` compatibility, completeness-result flow, no-lookahead tests, or
forbidden-field tests. Those must be decided in a later evaluator-specific
design phase before implementation.

This phase adds no production code, tests, evaluator implementation, evaluator
protocol, signal computation, feature computation, strategy logic, score,
direction, confidence, actionability, risk approval, execution intent
creation, broker or Alpaca behavior, order submission, runtime/scheduler
behavior, persistence, live data ingestion, ML, or LLM trading-path behavior.

The latest full-suite checkpoint remains:

```text
python -m pytest
778 passed, 4 skipped
```

## Phase 29 Step 3 First Real Evaluator Candidate Contract Design

Phase 29 Step 3 is documentation-only. It adds:

```text
docs/design/phase29_first_real_evaluator_candidate_contract.md
```

It also updates:

```text
docs/design/phase29_first_real_evaluator_candidate_selection.md
docs/design/phase29_first_real_evaluator_design_gate.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

The contract design keeps the selected candidate narrow: a future minimal
threshold-style advisory evaluator over one explicit scalar `SignalInputValue`.
The placeholder required input name is `indicator_value`, subject to final
design. The preferred initial value type is `Decimal` because it is
deterministic, avoids float reproducibility issues, is already supported by
`SignalInputValue`, and fits explicit comparison semantics.

The candidate may later use an explicit deterministic `Decimal` threshold and a
`>=` comparator, but Step 3 does not implement those semantics. Any future
result remains advisory and pre-risk. The comparator would only describe
whether the supplied scalar met a documented advisory condition; it must not
mean buy, sell, bullish, bearish, long, short, actionable, approved,
risk-approved, or trade-ready.

Open questions remain before implementation: exact
`ValidatedSignalDefinition` identity/version, exact supporting
`ValidatedResearchArtifact` identity/version, final input name, accepted value
types, threshold/comparator semantics, `output_value` representation,
`reason_code` meanings, diagnostics, assumptions, limitations, missing-input
behavior, extra-input behavior, snapshot id compatibility, `as_of`
compatibility, completeness-result flow, no-lookahead tests, and
forbidden-field tests.

This phase adds no production code, tests, evaluator implementation, evaluator
protocol, signal computation, feature computation, strategy logic, score,
direction, confidence, actionability, risk approval, execution intent
creation, broker or Alpaca behavior, order submission, runtime/scheduler
behavior, persistence, live data ingestion, ML, or LLM trading-path behavior.

The latest full-suite checkpoint remains:

```text
python -m pytest
778 passed, 4 skipped
```

## Phase 29 Step 4 First Real Evaluator Test Matrix

Phase 29 Step 4 is documentation-only. It adds:

```text
docs/design/phase29_first_real_evaluator_test_matrix.md
```

It also updates:

```text
docs/design/phase29_first_real_evaluator_candidate_contract.md
docs/design/phase29_first_real_evaluator_candidate_selection.md
docs/design/phase29_first_real_evaluator_design_gate.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

This step defines a pre-implementation test matrix for the future
threshold-style advisory evaluator. No tests were added in this phase; any
future tests added before implementation must assert existing guardrails or
document placeholders without requiring production evaluator code.

The matrix records required future fixtures for a valid
`ValidatedResearchArtifact`, `ValidatedSignalDefinition`,
`SignalEvaluationInputSnapshot`, `SignalInputValue`, `SignalInputBundle`,
`SignalInputBundleCompletenessResult`, explicit UTC-aware `as_of`, and
explicit UTC-aware `evaluated_at`.

The matrix covers future tests for input validation, threshold/comparator
behavior, timestamp/no-lookahead safety, traceability preservation,
advisory-only output, determinism, side-effect and dependency isolation,
non-mutation, forbidden trading-path behavior, unresolved implementation
questions, and implementation go/no-go criteria.

The candidate remains a future threshold-style advisory evaluator over one
explicit scalar input. The placeholder required input name remains
`indicator_value`, the preferred input type remains `Decimal`, the possible
comparator remains `>=`, and the possible threshold remains an explicit
deterministic `Decimal`. None of those placeholders authorize implementation.

Open questions remain before implementation: exact
`ValidatedSignalDefinition`, exact `ValidatedResearchArtifact`, final input
name, final threshold value source, final comparator, final `output_value`
representation, final `reason_code` values, final diagnostics, assumptions,
limitations, missing-input behavior, extra-input behavior, snapshot id
compatibility, `as_of` compatibility, completeness result flow, and whether the
evaluator validates completeness internally or requires prevalidated input.

This phase adds no production code, tests, evaluator implementation, evaluator
protocol, signal computation, feature computation, strategy logic, score,
direction, confidence, actionability, risk approval, execution intent
creation, broker or Alpaca behavior, order submission, runtime/scheduler
behavior, persistence, live data ingestion, ML, or LLM trading-path behavior.
Normal pytest remains offline, credential-free, and safe.

Verification after Phase 29 Step 4:

```text
python -m pytest
778 passed, 4 skipped
```

## Phase 29 Step 5 First Real Evaluator Implementation Readiness Review

Phase 29 Step 5 is documentation-only. It adds:

```text
docs/design/phase29_first_real_evaluator_implementation_readiness.md
```

It also updates:

```text
docs/design/phase29_first_real_evaluator_test_matrix.md
docs/design/phase29_first_real_evaluator_candidate_contract.md
docs/design/phase29_first_real_evaluator_candidate_selection.md
docs/design/phase29_first_real_evaluator_design_gate.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

This step reviews whether the future threshold-style advisory evaluator is
ready for implementation. The readiness recommendation is Option C: a small
additional design phase is needed to lock constants and output semantics before
production evaluator code is allowed.

The candidate remains selected but unimplemented. It is still a future
threshold-style advisory evaluator over one explicit scalar input, with
placeholder input name `indicator_value`, preferred value type `Decimal`,
possible `>=` comparator, explicit deterministic threshold, and advisory
`SignalEvaluationResult` output only.

Implementation remains blocked because exact `ValidatedSignalDefinition`
identity/version, exact supporting `ValidatedResearchArtifact`
identity/version, exact input name, exact threshold value and source, exact
comparator, exact output representation, exact reason codes, exact
missing/extra input policy, exact snapshot/as-of compatibility rules, and exact
completeness flow are not finalized.

The review records a safe future implementation shape only conceptually: one
small module, one frozen/slotted evaluator class or one pure function, explicit
inputs only, no runtime wiring, no registry, no scheduler, no broker, no
persistence, no live data, no ML or LLM calls, and focused unit tests first.
No production implementation is drafted here.

This phase adds no production code, tests, evaluator implementation, evaluator
protocol, signal computation, feature computation, strategy logic, score,
direction, confidence, actionability, risk approval, execution intent
creation, broker or Alpaca behavior, order submission, runtime/scheduler
behavior, persistence, live data ingestion, ML, or LLM trading-path behavior.
Normal pytest remains offline, credential-free, and safe.

Verification after Phase 29 Step 5:

```text
python -m pytest
778 passed, 4 skipped
```

## Phase 29 Step 6 Threshold Evaluator Constants And Output Semantics Design

Phase 29 Step 6 is documentation-only. It adds:

```text
docs/design/phase29_threshold_evaluator_constants_output_semantics.md
```

It also updates:

```text
docs/design/phase29_first_real_evaluator_implementation_readiness.md
docs/design/phase29_first_real_evaluator_test_matrix.md
docs/design/phase29_first_real_evaluator_candidate_contract.md
docs/design/phase29_first_real_evaluator_candidate_selection.md
docs/design/phase29_first_real_evaluator_design_gate.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

This step locks safe evaluator-local constants and advisory output semantics
before any implementation phase is considered. It selects `indicator_value` as
the required input name, `Decimal` as the only accepted value type, `>=` as the
comparator, and explicit evaluator configuration or evaluator-local constants
as the only allowed threshold source.

The design allows `Decimal("1")` only as a harmless future unit-test
placeholder. It is not a trading strategy, not research evidence, not a
production recommendation, and not authorization to implement a production
signal evaluator.

The selected future advisory output values are `threshold_condition_met` and
`threshold_condition_not_met`. The selected deterministic reason codes are
`THRESHOLD_CONDITION_MET`, `THRESHOLD_CONDITION_NOT_MET`,
`THRESHOLD_INPUT_MISSING`, and `THRESHOLD_INPUT_INVALID_TYPE`.

The recommended future policies require completeness validation before
evaluator use, deterministic rejection for missing or invalid input, ignored
extra inputs that cannot affect output, strict snapshot id equality, evaluator
`as_of == snapshot.as_of`, evaluator `as_of == bundle.as_of`, bundle-enforced
`observed_at <= bundle.as_of`, UTC-aware timestamps, and `evaluated_at >=
as_of`.

The updated readiness recommendation is Option B. Implementation remains
blocked because exact `ValidatedSignalDefinition` and
`ValidatedResearchArtifact` identities and versions are not available, and a
validated production threshold has not been tied to supporting research
evidence.

This phase adds no production code, tests, evaluator implementation, evaluator
protocol, signal computation, feature computation, strategy logic, score,
direction, confidence, actionability, risk approval, execution intent
creation, broker or Alpaca behavior, order submission, runtime/scheduler
behavior, persistence, live data ingestion, ML, or LLM trading-path behavior.
Normal pytest remains offline, credential-free, and safe.

Verification after Phase 29 Step 6:

```text
python -m pytest
778 passed, 4 skipped
```

## Phase 30 Step 1 Threshold Evaluator Research Support Boundary Design

Phase 30 Step 1 is documentation-only. It adds:

```text
docs/design/phase30_threshold_evaluator_research_support_boundary.md
```

It also updates:

```text
docs/design/phase29_threshold_evaluator_constants_output_semantics.md
docs/design/phase29_first_real_evaluator_implementation_readiness.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

This step defines the research-support boundary that must be satisfied before
the future threshold-style advisory evaluator may be implemented. It states
that input contracts, drafted constants, documented test semantics, and a
simple evaluator shape do not authorize production evaluator code without exact
validated research evidence and exact validated signal-definition metadata.

A future implementation must identify an exact `ValidatedResearchArtifact`
with artifact id/version, research scope, dataset or sample description, input
definition, threshold rationale, metric definitions, assumptions, limitations,
validation date or as-of metadata if available, evidence that the threshold is
not arbitrary, and evidence that the output remains advisory and not
trade-actionable by itself.

A future implementation must also identify an exact
`ValidatedSignalDefinition` with signal id/version, source artifact id/version,
required input name `indicator_value` unless later changed, expected input type
`Decimal`, advisory output semantics, assumptions, limitations, no broker,
order, runtime, or portfolio semantics, and no actionability semantics.

The future production threshold must be tied to validated research. It must not
come from live runtime state, environment variables, broker/account state,
portfolio state, LLM output, ML inference, ad hoc evaluator tuning, hidden
files, or persistence reads. Acceptable future sources may include explicit
evaluator config produced from a reviewed design phase, an evaluator-local
constant tied to a validated research artifact, or a clearly isolated test-only
placeholder such as `Decimal("1")`.

Implementation remains blocked until the exact validated research artifact
exists, the exact validated signal definition exists, the threshold value and
source are justified by that artifact, implementation scope is explicitly
approved, and required tests are written or ready to be written.

This phase adds no production code, tests, evaluator implementation, evaluator
protocol, signal computation, feature computation, strategy logic, score,
direction, confidence, actionability, risk approval, execution intent
creation, broker or Alpaca behavior, order submission, runtime/scheduler
behavior, persistence, live data ingestion, ML, or LLM trading-path behavior.
Normal pytest remains offline, credential-free, and safe.

The latest full-suite checkpoint is preserved from Phase 29 Step 6 until tests
are rerun:

```text
python -m pytest
778 passed, 4 skipped
```

## Phase 30 Step 2 Research Validation Checklist / Evidence Standard

Phase 30 Step 2 is documentation-only. It adds:

```text
docs/design/phase30_research_validation_evidence_standard.md
```

It also updates:

```text
docs/design/phase30_threshold_evaluator_research_support_boundary.md
docs/design/phase29_threshold_evaluator_constants_output_semantics.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

This step defines the fixed research validation checklist and evidence
standard that future `ValidatedResearchArtifact` candidates must be reviewed
against before they can support a real evaluator. The standard is created
before any candidate artifact review so that candidate artifacts are measured
against a stable yardstick instead of shaping the definition of "validated"
after the fact.

The evidence standard covers required artifact evidence, reproducibility,
dataset scope, data quality, bias controls, point-in-time and no-lookahead
requirements, input definitions, threshold rationale, metric definitions,
statistical claim classification, assumptions, limitations, non-claims,
signal-definition binding, deterministic suitability, advisory-only semantics,
pass/fail outcomes, and implementation blockers.

No production code or runtime behavior changed. No research artifact,
validated signal definition, real evaluator, evaluator protocol, signal
computation, feature computation, strategy logic, score, direction,
confidence, actionability, signal-to-risk conversion, risk approval, execution
intent creation, execution-plan mutation, portfolio mutation, broker or Alpaca
behavior, order submission, runtime/scheduler behavior, persistence, live data
ingestion, ML, or LLM trading-path behavior was added.

Implementation remains blocked pending exact validated research, exact
validated signal-definition support, threshold/config provenance, explicit
implementation scope approval, and implementation tests written or ready.

Verification after Phase 30 Step 2:

```text
python -m pytest
778 passed, 4 skipped
```

## Phase 30 Step 3 Research Artifact Candidate Review Template / Intake Boundary

Phase 30 Step 3 is documentation-only. It adds:

```text
docs/design/phase30_research_artifact_candidate_review_template.md
```

It also updates:

```text
docs/design/phase30_research_validation_evidence_standard.md
docs/design/phase30_threshold_evaluator_research_support_boundary.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

This step defines the candidate research artifact review template and intake
boundary that future reviewers must use to apply the Phase 30 Step 2 evidence
standard. The template records the required intake fields, checklist mapping,
claim classification, non-claims, signal-definition binding checks,
threshold/config provenance checks, pass/fail outcomes, and implementation
blockers for a future `ValidatedResearchArtifact` candidate.

The template does not review a real artifact, approve an artifact, create a
validated signal definition, or authorize evaluator implementation. A future
candidate artifact must still pass review using the evidence standard and this
template, and a future validated signal definition must bind exactly to that
artifact before implementation can be considered.

No production code or runtime behavior changed. No research artifact,
validated signal definition, real evaluator, evaluator protocol, signal
computation, feature computation, strategy logic, score, direction,
confidence, actionability, signal-to-risk conversion, risk approval, execution
intent creation, execution-plan mutation, portfolio mutation, broker or Alpaca
behavior, order submission, runtime/scheduler behavior, persistence, live data
ingestion, ML, or LLM trading-path behavior was added.

Implementation remains blocked pending candidate artifact review, exact
validated research support, exact validated signal-definition support,
threshold/config provenance, explicit implementation scope approval, and
implementation tests written or ready.

Verification after Phase 30 Step 3:

```text
python -m pytest
778 passed, 4 skipped
```

## Phase 30 Step 4 Research Artifact Candidate Sourcing Plan / Backlog Boundary

Phase 30 Step 4 is documentation-only. It adds:

```text
docs/design/phase30_research_artifact_candidate_sourcing_plan.md
```

It also updates:

```text
docs/design/phase30_research_artifact_candidate_review_template.md
docs/design/phase30_research_validation_evidence_standard.md
docs/design/phase30_threshold_evaluator_research_support_boundary.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

This step defines the sourcing plan and backlog boundary for future candidate
research artifacts. It identifies candidate categories worth sourcing later,
sourcing and rejection criteria, threshold evaluator research needs, a future
backlog entry format, priority levels, intake routing, and explicit
implementation blockers.

The sourcing plan does not review a candidate artifact, approve an artifact,
create a validated research artifact, create a validated signal definition, or
authorize evaluator implementation. Sourced candidates remain informational
until reviewed against the Phase 30 Step 2 evidence standard and documented
with the Phase 30 Step 3 candidate review template.

No production code or runtime behavior changed. No research artifact,
validated signal definition, real evaluator, evaluator protocol, signal
computation, feature computation, strategy logic, score, direction,
confidence, actionability, risk approval, execution intent creation, broker or
Alpaca behavior, order submission, runtime/scheduler behavior, persistence,
live data ingestion, ML, or LLM trading-path behavior was added.

Implementation remains blocked pending candidate sourcing, candidate artifact
review, exact validated research support, exact validated signal-definition
support, threshold/config provenance, explicit implementation scope approval,
and implementation tests written or ready.

Verification after Phase 30 Step 4:

```text
python -m pytest
778 passed, 4 skipped
```

## Phase 30 Step 5 Populate Candidate Research Backlog

Phase 30 Step 5 is documentation-only. It adds:

```text
docs/design/phase30_research_artifact_candidate_backlog.md
```

It also updates:

```text
docs/design/phase30_research_artifact_candidate_sourcing_plan.md
docs/design/phase30_research_artifact_candidate_review_template.md
docs/design/phase30_research_validation_evidence_standard.md
docs/design/phase30_threshold_evaluator_research_support_boundary.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

This step creates a small initial backlog of unreviewed research candidate
entries. The starter queue includes mechanical indicator definitions,
threshold sanity-check studies, regime indicator studies, predictive
relationship studies, risk filter studies, data-quality / feature-validity
studies, backtesting methodology references, and no-lookahead / bias-control
references.

The backlog entries are placeholders and sourcing targets only. No candidate
artifact is reviewed, no artifact is approved, no evidence is accepted, no
threshold is justified, no strategy or profitability claim is accepted, and no
implementation readiness claim is created.

No production code or runtime behavior changed. No research artifact,
validated signal definition, real evaluator, evaluator protocol, signal
computation, feature computation, strategy logic, score, direction,
confidence, actionability, signal-to-risk conversion, risk approval, execution
intent creation, execution-plan mutation, portfolio mutation, broker or Alpaca
behavior, order submission, runtime/scheduler behavior, persistence, live data
ingestion, ML, or LLM trading-path behavior was added.

Implementation remains blocked pending candidate sourcing, artifact review
using the Phase 30 template, exact validated research support, exact validated
signal-definition support, threshold/config provenance, explicit
implementation scope approval, and implementation tests written or ready.

Verification after Phase 30 Step 5:

```text
python -m pytest
778 passed, 4 skipped
```

## Phase 30 Step 6 First Candidate Research Artifact Source Selection

Phase 30 Step 6 is documentation-only. It adds:

```text
docs/design/phase30_first_research_candidate_source_selection.md
```

It also updates:

```text
docs/design/phase30_research_artifact_candidate_backlog.md
docs/design/phase30_research_artifact_candidate_sourcing_plan.md
docs/design/phase30_research_artifact_candidate_review_template.md
docs/design/phase30_research_validation_evidence_standard.md
docs/design/phase30_threshold_evaluator_research_support_boundary.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

This step selects `P30-BL-001`, "Simple scalar threshold indicator
definition", as the first sourcing target. The candidate was chosen because it
is P0, close to threshold-style advisory evaluator mechanics, compatible with
deterministic scalar input review, likely relevant to `indicator_value` and
`Decimal`, lower complexity than predictive or performance studies, and less
likely to imply profitability or actionability.

The selected candidate remains unreviewed, unvalidated, not approved, not
production-ready, and not implementation-ready. `P30-BL-001` is marked as
`sourcing target` only. No source is collected in this phase.

Before formal review, the required evidence package must collect
source/provenance, artifact title or reference, author/source, date/version,
dataset details if applicable, input definition, threshold/config rationale if
applicable, method description, assumptions, limitations, non-claims,
reproducibility notes, no-lookahead or bias-control notes if applicable,
relevance to `indicator_value`, relevance to the threshold-style advisory
evaluator, and whether the candidate can bind to a future
`ValidatedSignalDefinition`.

No production code or runtime behavior changed. No research artifact,
validated signal definition, real evaluator, evaluator protocol, signal
computation, feature computation, strategy logic, score, direction,
confidence, actionability, signal-to-risk conversion, risk approval, execution
intent creation, execution-plan mutation, portfolio mutation, broker or Alpaca
behavior, order submission, runtime/scheduler behavior, persistence, live data
ingestion, ML, or LLM trading-path behavior was added.

Implementation remains blocked pending selected source collection, artifact
review using the Phase 30 template, exact validated research support, exact
validated signal-definition support, threshold/config provenance, explicit
implementation scope approval, and implementation tests written or ready.

Verification after Phase 30 Step 6:

```text
python -m pytest
778 passed, 4 skipped
```

## Phase 31 Step 1 Agent Workflow Compression And Research Track Reset

Phase 31 Step 1 is documentation-only. It adds:

```text
docs/agent_context/codex_operating_context.md
```

It also updates:

```text
docs/design/phase30_research_artifact_candidate_sourcing_plan.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

This step creates a reusable Codex operating context so future prompts can
reference a single project summary instead of repeating the full historical
ledger. The new context records the project goal, safety rules, current
pipeline, evaluator stack, standard files to read first, standard forbidden
behavior, and standard verification commands.

This step also resets phase granularity for the research track. Future
documentation, research, and planning phases may combine related documentation
updates when the work is low-risk and changes no production code. Production
source changes remain narrow, test-first, explicitly scoped, and heavily
verified. Any phase that adds behavior, evaluator logic, broker behavior,
runtime behavior, persistence, or trading-path behavior must remain small and
separately reviewed. Hardening phases should be used when risk justifies them,
not automatically after every documentation-only phase.

Real evaluator implementation remains blocked pending validated research
artifact, validated signal definition, threshold/config provenance, explicit
implementation scope approval, and tests written or ready.

No production code or runtime behavior changed. No tests, research artifact,
validated signal definition, real evaluator, evaluator protocol, signal
computation, feature computation, strategy logic, score, direction,
confidence, actionability, risk approval, execution intent creation,
execution-plan mutation, broker or Alpaca behavior, order submission,
runtime/scheduler behavior, persistence, live data ingestion, ML, or LLM
trading-path behavior was added.

The latest known full-suite checkpoint remains:

```text
python -m pytest
778 passed, 4 skipped
```

## Phase 31 Step 2 Research Track Next Action Plan

Phase 31 Step 2 is documentation-only. It adds:

```text
docs/design/phase31_research_track_next_action_plan.md
```

It also updates:

```text
docs/agent_context/codex_operating_context.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

This step turns the Phase 30 research backlog and first source-selection work
into a practical sequence. The recommended broader docs/research phases are:
collect and summarize the `P30-BL-001` source package, normalize the source
package for pre-review, review the candidate against the Phase 30 evidence
standard and template, plan validated signal-definition binding if evidence
supports it, and run an implementation-readiness gate before any production
code prompt.

`P30-BL-001`, "Simple scalar threshold indicator definition", remains the first
sourcing target only. It is still unreviewed, unvalidated, not approved, not
production-ready, and not implementation-ready. Backlog entries, source
selection, research-agent summaries, familiar indicator names, and unsupported
template notes are not evidence by themselves.

Before `P30-BL-001` can be reviewed, a source package must collect traceable
source/provenance, title or citation, author/source, date/version, source type,
mechanical definition, exact input meaning, value type rationale, comparator
and threshold semantics if applicable, assumptions, limitations, non-claims,
reproducibility notes, no-lookahead or bias-control notes when applicable,
relevance to the threshold-style advisory evaluator, and unresolved gaps.

Perplexity, Claude, Gemini, and similar tools may help with source discovery,
citation gathering, summaries, checklist prefill, contradiction finding,
reviewer-style critique, and missing-evidence questions. They must not define
production evaluator behavior, choose production thresholds or config, decide
score, direction, confidence, ranking, or actionability, approve research or
signal definitions, approve implementation scope, bypass tests, access trading
state for decisions, or enter the trading hot path.

Real evaluator implementation remains blocked pending a sourced and reviewed
candidate, exact validated research support, exact validated signal-definition
support, explicit threshold/config provenance, explicit implementation scope
approval, and tests written or ready.

No production code or runtime behavior changed. No tests, research artifact,
validated signal definition, real evaluator, evaluator protocol, signal
computation, feature computation, strategy logic, score, direction,
confidence, actionability, risk approval, execution intent creation,
execution-plan mutation, broker or Alpaca behavior, order submission,
runtime/scheduler behavior, persistence, live data ingestion, ML, or LLM
trading-path behavior was added.

The latest known full-suite checkpoint remains:

```text
python -m pytest
778 passed, 4 skipped
```

## Phase 31 Step 3 P30-BL-001 Source Package Normalization

Phase 31 Step 3 is documentation-only. It adds:

```text
docs/design/phase31_p30_bl_001_source_package.md
```

It also updates:

```text
docs/design/phase31_research_track_next_action_plan.md
docs/design/phase30_first_research_candidate_source_selection.md
docs/design/phase30_research_artifact_candidate_backlog.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

This step normalizes the `P30-BL-001` source package using source-discovery
material from research-agent-assisted collection. The package records source
ids, titles, organizations, source types, dates or access notes, URLs,
categories, support boundaries, non-proofs, relevance to `indicator_value`,
relevance to the threshold-style advisory evaluator, limitations, source
tiers, candidate groupings, preferred formal-review candidates, known gaps,
and next routing.

`P30-BL-001` is source-package-ready only. It remains unreviewed,
unvalidated, not approved, not production-ready, not implementation-ready, and
not a justification for a production threshold, comparator, signal definition,
evaluator implementation, scoring, ranking, direction, actionability,
profitability, or risk-adjusted-return claim.

The next research phase should be formal review of the strongest source subset
using the Phase 30 evidence standard and candidate review template. That future
review may still pass, conditionally pass with gaps, fail, or classify the
package as informational only. A favorable review would still not be
implementation approval.

No production code or runtime behavior changed. No tests, research artifact,
validated signal definition, real evaluator, evaluator protocol, signal
computation, feature computation, strategy logic, score, direction,
confidence, actionability, risk approval, execution intent creation,
execution-plan mutation, broker or Alpaca behavior, order submission,
runtime/scheduler behavior, persistence, live data ingestion, ML, or LLM
trading-path behavior was added.

The latest known full-suite checkpoint remains:

```text
python -m pytest
778 passed, 4 skipped
```

## Phase 31 Step 4 P30-BL-001 Tier A Formal Source Review

Phase 31 Step 4 is documentation-only. It adds:

```text
docs/design/phase31_p30_bl_001_tier_a_review.md
```

It also updates:

```text
docs/design/phase31_p30_bl_001_source_package.md
docs/design/phase31_research_track_next_action_plan.md
docs/design/phase30_research_artifact_candidate_backlog.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

This step formally reviews the Tier A subset from the normalized
`P30-BL-001` source package: comparator mechanics, `Decimal` scalar
representation, TA-Lib indicator function shape, no-lookahead methodology,
reproducibility, and non-claim governance. The Tier A subset receives a
conditional pass for mechanics and methodology only.

`P30-BL-001` remains unvalidated, not approved, not production-ready, not
implementation-ready, and not a justification for a production threshold,
comparator, signal definition, evaluator implementation, scoring, ranking,
direction, actionability, profitability, predictive edge, live trading, or
risk-adjusted-return claim.

No production code or runtime behavior changed. No tests, research artifact,
validated signal definition, real evaluator, evaluator protocol, signal
computation, feature computation, strategy logic, score, direction,
confidence, actionability, risk approval, execution intent creation,
execution-plan mutation, broker or Alpaca behavior, order submission,
runtime/scheduler behavior, persistence, live data ingestion, ML, or LLM
trading-path behavior was added.

Phase 31 Step 5 later routes this result and recommends a formal
mechanics-only candidate artifact review summary. Tier B support and targeted
production-threshold evidence remain later options. Validated
signal-definition binding and evaluator implementation remain blocked.

Verification after Phase 31 Step 4:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
no whitespace errors; Git emitted LF-to-CRLF working-copy warnings for
modified existing docs
```

## Phase 31 Step 5 P30-BL-001 Evidence Gap And Routing Plan

Phase 31 Step 5 is documentation-only. It adds:

```text
docs/design/phase31_p30_bl_001_evidence_gap_routing_plan.md
```

It also updates:

```text
docs/design/phase31_p30_bl_001_tier_a_review.md
docs/design/phase31_p30_bl_001_source_package.md
docs/design/phase31_research_track_next_action_plan.md
docs/design/phase30_research_artifact_candidate_backlog.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

This step routes the Tier A result without promoting it. The Tier A outcome
remains a conditional pass for mechanics and methodology only, and is
informational only for validation, threshold, trading, or implementation
claims.

Remaining blockers include no exact `ValidatedResearchArtifact`, no exact
`ValidatedSignalDefinition`, no dataset-specific validation, no production
threshold value/source, no threshold rationale tied to research evidence, no
predictive/profitability evidence, no risk-adjusted-return evidence, no
signal-definition binding, no applied no-lookahead audit, no implementation
scope approval, and no evaluator implementation tests.

The recommended next route is a formal mechanics-only candidate artifact
review summary for `P30-BL-001`. That summary may support future evaluator
mechanics, but it must explicitly state that it cannot support a production
threshold or evaluator implementation.

No production code or runtime behavior changed. No tests, research artifact,
validated signal definition, real evaluator, evaluator protocol, signal
computation, feature computation, strategy logic, score, direction,
confidence, actionability, risk approval, execution intent creation,
execution-plan mutation, broker or Alpaca behavior, order submission,
runtime/scheduler behavior, persistence, live data ingestion, ML, or LLM
trading-path behavior was added.

Verification after Phase 31 Step 5:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
clean
```

## Phase 31 Step 6 P30-BL-001 Mechanics-Only Candidate Artifact Review Summary

Phase 31 Step 6 is documentation-only. It adds:

```text
docs/design/phase31_p30_bl_001_mechanics_only_review_summary.md
```

It also updates:

```text
docs/design/phase31_p30_bl_001_evidence_gap_routing_plan.md
docs/design/phase31_p30_bl_001_tier_a_review.md
docs/design/phase31_p30_bl_001_source_package.md
docs/design/phase31_research_track_next_action_plan.md
docs/design/phase30_research_artifact_candidate_backlog.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

This step records the formal mechanics-only candidate artifact review summary
for `P30-BL-001`, "Simple scalar threshold indicator definition". The summary
is based on the normalized source package, Tier A formal source review,
evidence gap and routing plan, Phase 30 evidence standard, and Phase 30
candidate review template.

Disposition: conditional pass for mechanics/methodology only. The candidate
may support comparator mechanics, `Decimal` scalar representation,
deterministic scalar input concepts, indicator function shape, no-lookahead
methodology questions, reproducibility expectations, conservative non-claims,
and advisory-only threshold semantics.

`P30-BL-001` remains unvalidated, unapproved, not production-ready, not
implementation-ready, and not threshold-justified. It does not support a
production threshold value/source, profitability claim, predictive edge,
risk-adjusted return claim, live-trading suitability, validated signal
definition, signal-definition binding, evaluator implementation readiness,
risk approval, execution readiness, broker behavior, or portfolio behavior.

Remaining blockers include no exact `ValidatedResearchArtifact`, no exact
`ValidatedSignalDefinition`, no dataset-specific validation, no production
threshold source or rationale, no predictive/profitability/risk-adjusted-return
evidence, no signal-definition binding, no applied no-lookahead audit, no
implementation approval, and no evaluator tests.

The recommended next route is research/data/backtesting validation design or
targeted production-threshold evidence collection if the threshold evaluator
remains the focus. Implementation is not recommended.

No production code or runtime behavior changed. No tests, research artifact,
validated signal definition, real evaluator, evaluator protocol, signal
computation, feature computation, strategy logic, score, direction,
confidence, actionability, risk approval, execution intent creation,
execution-plan mutation, broker or Alpaca behavior, order submission,
runtime/scheduler behavior, persistence, live data ingestion, ML, or LLM
trading-path behavior was added.

Verification after Phase 31 Step 6:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
clean
```

## Phase 31 Step 7 P30-BL-001 Final Disposition And Next-Candidate Routing

Phase 31 Step 7 is documentation-only. It adds:

```text
docs/design/phase31_p30_bl_001_final_disposition.md
```

It also updates:

```text
docs/design/phase31_p30_bl_001_mechanics_only_review_summary.md
docs/design/phase31_p30_bl_001_evidence_gap_routing_plan.md
docs/design/phase31_research_track_next_action_plan.md
docs/design/phase30_research_artifact_candidate_backlog.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

Final disposition: `P30-BL-001` is mechanics-only dispositioned, in the
mechanics-only sense only. It remains non-validated, unapproved, not
production-ready, not implementation-ready, and not threshold-justified.

The candidate supports scalar comparator mechanics, explicit threshold
vocabulary, possible `Decimal` scalar representation, deterministic scalar
input review questions, indicator function shape, no-lookahead and
reproducibility review prompts, and advisory-only non-claim framing. Tier A
sources remain informational and methodological only.

The candidate does not support a production threshold value/source,
threshold/config provenance, profitability, predictive edge, risk-adjusted
return, live-trading suitability, exact `ValidatedResearchArtifact`, exact
`ValidatedSignalDefinition`, signal-definition binding, evaluator
implementation readiness, signal scoring, ranking, direction, confidence,
probability, actionability, risk approval, execution readiness, broker
behavior, portfolio behavior, runtime behavior, persistence, ML, or LLM
trading-path behavior.

Implementation remains blocked because there is no exact validated research
artifact, no exact validated signal definition, no dataset-specific validation,
no explicit threshold rationale tied to reviewed evidence, no out-of-sample or
robustness evidence, no applied no-lookahead audit, no performance evidence,
no risk-adjusted-return evidence, no approved implementation scope, and no
production evaluator tests.

The backlog now marks `P30-BL-001` as mechanics-only dispositioned. That status
does not mean validated, approved, production-ready, implementation-ready,
evidence accepted, or threshold justified.

The next safest research route is a candidate or research task that can supply
dataset-specific threshold or validation evidence. `P30-BL-002` remains a
possible unsourced direction, or a replacement P0 candidate may be chosen if it
offers better traceable dataset-specific threshold evidence. This phase does
not review, validate, or approve the next candidate.

No production code or runtime behavior changed. No tests, research artifact,
validated signal definition, real evaluator, evaluator protocol, signal
computation, feature computation, strategy logic, score, direction,
confidence, probability, ranking, actionability, risk approval, execution
intent creation, execution-plan mutation, broker or Alpaca behavior, order
submission, runtime/scheduler behavior, persistence, live data ingestion, ML,
or LLM trading-path behavior was added.

Verification after Phase 31 Step 7:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
passed; Git emitted LF-to-CRLF working-copy warnings only
```

## Phase 32 Step 1 Dataset-Specific Validation Candidate Selection

Phase 32 Step 1 is documentation-only. It adds:

```text
docs/design/phase32_dataset_specific_validation_candidate_selection.md
```

It also updates:

```text
docs/design/phase31_research_track_next_action_plan.md
docs/design/phase30_research_artifact_candidate_backlog.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

Selection: dataset-specific threshold or validation evidence sourcing is the
next research direction. `P30-BL-002` is the current backlog routing handle
only if sourcing can produce a concrete evidence package with dataset scope,
point-in-time assumptions, explicit input definitions, threshold or parameter
rationale, no-lookahead controls, reproducibility notes, robustness or
out-of-sample evidence, limitations, and non-claims. If that package cannot be
sourced, a better P0 replacement should be sourced before formal review.

`P30-BL-002` remains unreviewed, unvalidated, unapproved, not production-ready,
not implementation-ready, and not threshold-justified. This phase does not
review, validate, approve, promote, or implement `P30-BL-002` or any
replacement candidate.

The backlog now marks `P30-BL-002` as a sourcing target only. That status does
not mean validated, approved, production-ready, implementation-ready, evidence
accepted, or threshold justified.

The minimum evidence package before formal review includes source provenance,
dataset scope, point-in-time assumptions, explicit inputs, threshold or
parameter rationale, validation design, no-lookahead controls, reproducibility
notes, limitations, non-claims, possible future binding notes, and unresolved
gaps.

Implementation remains blocked because there is no exact validated research
artifact, no exact validated signal definition, no reviewed dataset-specific
validation, no explicit threshold rationale tied to reviewed evidence, no
out-of-sample or robustness evidence, no applied no-lookahead audit, no
approved implementation scope, and no production evaluator tests.

No production code or runtime behavior changed. No tests, research artifact,
validated signal definition, real evaluator, evaluator protocol, signal
computation, feature computation, strategy logic, score, direction,
confidence, probability, ranking, actionability, risk approval, execution
intent creation, execution-plan mutation, broker or Alpaca behavior, order
submission, runtime/scheduler behavior, persistence, live data ingestion, ML,
or LLM trading-path behavior was added.

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

## Phase 32 Step 2 P30-BL-002 Source Package Sourcing Plan

Phase 32 Step 2 is documentation-only. It adds:

```text
docs/design/phase32_p30_bl_002_source_package_sourcing_plan.md
```

It updates:

```text
docs/design/phase32_dataset_specific_validation_candidate_selection.md
docs/design/phase31_research_track_next_action_plan.md
docs/design/phase30_research_artifact_candidate_backlog.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

The plan defines what `P30-BL-002` must produce before any formal review can
begin: source/provenance, title/reference, author/source, date/version,
dataset scope, asset class/universe, timeframe, point-in-time assumptions,
data quality assumptions, explicit input definition, threshold or parameter
rationale, validation design, no-lookahead controls, reproducibility notes,
robustness or out-of-sample evidence, limitations, non-claims, future binding
notes, and unresolved gaps.

The plan also defines acceptable source categories, unacceptable source
categories, minimum review-readiness criteria, and rejection/replacement
criteria. Weak, vague, non-reproducible, or non-dataset-specific material
should reject or replace `P30-BL-002` with a better sourced P0 candidate before
formal review.

`P30-BL-002` remains unreviewed, unvalidated, unapproved, not production-ready,
not implementation-ready, and not threshold-justified. This phase does not
collect or cite actual research sources, validate a signal, approve a
threshold, create a `ValidatedResearchArtifact`, create a
`ValidatedSignalDefinition`, promote a candidate, bind a signal definition, add
evaluator behavior, add signal computation, or add runtime, broker,
persistence, ML, or LLM trading-path behavior.

The next route remains blocked on a concrete `P30-BL-002` source package or a
better P0 replacement source package, formal review, exact validated research
artifact, exact validated signal definition, threshold/config provenance, and
explicit implementation approval.

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

## Phase 32 Step 3 P30-BL-002 Source Package Collection and Normalization

Phase 32 Step 3 is documentation-only. It adds:

```text
docs/design/phase32_p30_bl_002_source_package.md
```

It updates:

```text
docs/design/phase32_dataset_specific_validation_candidate_selection.md
docs/design/phase31_research_track_next_action_plan.md
docs/design/phase30_research_artifact_candidate_backlog.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

This step normalizes the supplied Claude, Perplexity, and Gemini/browser scout
report material for `P30-BL-002`. The revised package records 23 normalized
candidate-only source entries, assigns `P30-BL-002-S01` through
`P30-BL-002-S23`, deduplicates the overlapping "Interpretable
Hypothesis-Driven Trading" candidate across Claude and Perplexity, and
quarantines bibliography-only links that lacked candidate-level metadata.

The package status is partial. It is useful for routing and possible limited
formal review intake after primary-source verification, but it is not
sufficient to validate or approve a threshold. It records package-level gaps
against the Phase 32 Step 2 sourcing plan: primary-source provenance
verification, dataset scope details, asset-universe timing, exact timeframe
boundaries, point-in-time assumptions, data quality assumptions, explicit
input definitions, threshold or parameter rationale, validation design,
no-lookahead controls, reproducibility, robustness or out-of-sample evidence,
source-specific limitations, source-specific non-claims, and future binding
notes.

The source-package readiness classification is partial but needs additional
sourcing. The most promising intake candidates are negative-control
moving-average timing, data-snooping/OOS negative-control, time-series
momentum, and point-in-time snapshot methodology entries. Several arXiv,
blog, vendor, ML-heavy, optimizer-heavy, or data-dependent entries are
methodology-only, too complex, or reject/replacement-needed candidates. That
classification is not validation, formal review, approval, promotion, or
implementation readiness.

Recommended routing is primary-source verification and limited formal review
intake for selected candidate sources, with additional sourcing or a better P0
replacement if selected entries fail provenance, dataset-scope,
point-in-time, no-lookahead, reproducibility, robustness, limitation, or
non-claim checks.

`P30-BL-002` remains a sourcing target only: unreviewed, unvalidated,
unapproved, not production-ready, not implementation-ready, and not
threshold-justified. This phase does not validate a signal, approve a
threshold, create a `ValidatedResearchArtifact`, create a
`ValidatedSignalDefinition`, add evaluator behavior, add signal computation,
or add runtime, broker, persistence, ML, or LLM trading-path behavior.

Verification after Phase 32 Step 3:

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
?? docs/design/phase32_p30_bl_002_source_package.md
```

Manual documentation checks:

- edited markdown files have no trailing whitespace
- edited markdown files have exactly one final newline
- edited markdown files were inspected for completeness and were not truncated

## Phase 32 Step 4 P30-BL-002 Primary Source Verification Gate

Phase 32 Step 4 is documentation-only. It adds:

```text
docs/design/phase32_p30_bl_002_primary_source_verification_gate.md
```

It updates:

```text
docs/design/phase32_p30_bl_002_source_package.md
docs/design/phase32_dataset_specific_validation_candidate_selection.md
docs/design/phase31_research_track_next_action_plan.md
docs/design/phase30_research_artifact_candidate_backlog.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

This step verifies selected primary-source identities and intake eligibility
for `P30-BL-002-S01`, `P30-BL-002-S03`, `P30-BL-002-S05`, and
`P30-BL-002-S08`. It corrects the `P30-BL-002-S08` title to "Accurately
Backtesting Financial Models Through Point-in-Time Consensus Estimates" and
records the source as methodology-only PIT/no-lookahead material.

The Step 4 routing result is limited. `P30-BL-002-S05`, `P30-BL-002-S03`, and
`P30-BL-002-S01` are eligible for limited formal review intake only.
`P30-BL-002-S08` is maybe eligible only as a methodology-only PIT review
candidate. Scout-only claims remain quarantined until formal review checks
them from primary sources.

`P30-BL-002` remains unreviewed, unvalidated, unapproved, not
production-ready, not implementation-ready, and not threshold-justified. This
phase does not validate a signal, approve a threshold, create a
`ValidatedResearchArtifact`, create a `ValidatedSignalDefinition`, add
evaluator behavior, add signal computation, or add runtime, broker,
persistence, ML, or LLM trading-path behavior.

Verification after Phase 32 Step 4:

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
 M docs/design/phase32_p30_bl_002_source_package.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_p30_bl_002_primary_source_verification_gate.md
```

Manual documentation checks:

- edited markdown files have no trailing whitespace
- edited markdown files have exactly one final newline
- edited markdown files were inspected for completeness and were not truncated

## Phase 32 Step 5 P30-BL-002 Limited Formal Review Intake Plan

Phase 32 Step 5 is documentation-only. It adds:

```text
docs/design/phase32_p30_bl_002_limited_formal_review_intake_plan.md
```

It updates:

```text
docs/design/phase32_p30_bl_002_primary_source_verification_gate.md
docs/design/phase32_p30_bl_002_source_package.md
docs/design/phase32_dataset_specific_validation_candidate_selection.md
docs/design/phase31_research_track_next_action_plan.md
docs/design/phase30_research_artifact_candidate_backlog.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

This step uses the Phase 32 Step 4 verification gate as the source of truth for
selected intake candidates. It admits only `P30-BL-002-S01`, `P30-BL-002-S03`,
`P30-BL-002-S05`, and `P30-BL-002-S08` into the intake plan.

The review order is deliberately conservative:

1. `P30-BL-002-S01` for moving-average timing / lookahead negative-control
   review.
2. `P30-BL-002-S03` for data-snooping / out-of-sample negative-control review.
3. `P30-BL-002-S08` for methodology-only PIT/no-lookahead infrastructure
   review.
4. `P30-BL-002-S05` for limited time-series momentum candidate-evidence
   review.

The plan records shared formal review criteria covering primary-source
identity, dataset scope, asset universe, timeframe, input/indicator definition,
threshold/parameter relevance, validation design, no-lookahead/PIT controls,
reproducibility, robustness or out-of-sample evidence, limitations,
non-claims, future binding relevance, and unresolved gaps.

The source-specific criteria keep roles narrow:

- `S01` can support only negative-control/no-lookahead review planning and
  cannot support production threshold approval.
- `S03` can support only falsification and multiple-testing guardrail review
  planning and cannot support production threshold approval.
- `S05` is the only selected source currently eligible for limited
  candidate-evidence review planning, but it remains unvalidated.
- `S08` can support only methodology-only PIT/no-lookahead review planning and
  cannot validate a signal or threshold.

Possible later formal review outcomes are pass for negative-control use only,
pass for methodology-only use only, conditional pass for limited candidate
evidence, fail/quarantine, or needs additional sourcing. No future outcome
automatically creates a `ValidatedResearchArtifact`, creates a
`ValidatedSignalDefinition`, approves a threshold, validates a signal, or
authorizes implementation.

`P30-BL-002` remains unreviewed, unvalidated, unapproved, not
production-ready, not implementation-ready, and not threshold-justified. This
phase does not validate a signal, approve a threshold, create a
`ValidatedResearchArtifact`, create a `ValidatedSignalDefinition`, add
evaluator behavior, add signal computation, or add runtime, broker,
persistence, ML, or LLM trading-path behavior.

Verification after Phase 32 Step 5:

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
 M docs/design/phase32_p30_bl_002_primary_source_verification_gate.md
 M docs/design/phase32_p30_bl_002_source_package.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_p30_bl_002_limited_formal_review_intake_plan.md
```

Manual documentation checks:

- edited markdown files have no trailing whitespace
- edited markdown files have exactly one final newline
- edited markdown files were inspected for completeness and were not truncated

## Phase 32 Step 6 P30-BL-002-S01 Formal Review

Phase 32 Step 6 is documentation-only. It adds:

```text
docs/design/phase32_p30_bl_002_s01_formal_review.md
```

It updates:

```text
docs/design/phase32_p30_bl_002_limited_formal_review_intake_plan.md
docs/design/phase32_p30_bl_002_primary_source_verification_gate.md
docs/design/phase32_p30_bl_002_source_package.md
docs/design/phase32_dataset_specific_validation_candidate_selection.md
docs/design/phase31_research_track_next_action_plan.md
docs/design/phase30_research_artifact_candidate_backlog.md
docs/deterministic_core.md
docs/project_checkpoint.md
```

This step formally reviews `P30-BL-002-S01` only, using the Phase 32 Step 4
primary-source verification gate and Phase 32 Step 5 intake plan as the source
of truth. It records the source identity as Valeriy Zakamulin's "Revisiting
the Profitability of Market Timing with Moving Averages", with the SSRN page
and DOI `10.2139/ssrn.2743119` verified by Step 4. The Wiley DOI
`10.1111/irfi.12132` remains a later citation check because the Wiley page was
not accessible during Step 4.

The S01 review outcome is: pass for negative-control/no-lookahead use only.
The pass is narrow. S01 can support falsification and moving-average
timing-bias guardrail design only. It does not support production threshold
approval, predictive-edge claims, profitability claims, validated artifact
readiness, validated signal definition readiness, implementation readiness,
paper trading readiness, or live trading readiness.

The review records unresolved S01 gaps for exact signal date, execution date,
return-measurement date, moving-average windows, comparators, price/return
transformations, dataset vendor/source, sample dates, total-return treatment,
transaction-cost assumptions, code/data access, licensing, archival path, and
deterministic rerun feasibility. Any future exact timing-rule reproduction,
deterministic test binding, threshold comparison, or stronger claim requires
additional S01 evidence.

The next routing step is `P30-BL-002-S03` formal review as the second
negative-control source. `P30-BL-002-S05` and `P30-BL-002-S08` remain
unreviewed by Step 6.

`P30-BL-002` remains candidate-only, unvalidated, unapproved, not promoted,
not production-ready, not implementation-ready, and not threshold-justified.
This phase does not create a `ValidatedResearchArtifact`, create a
`ValidatedSignalDefinition`, add evaluator behavior, add signal computation,
or add runtime, broker, persistence, ML, or LLM trading-path behavior.

Verification after Phase 32 Step 6:

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
 M docs/design/phase32_p30_bl_002_limited_formal_review_intake_plan.md
 M docs/design/phase32_p30_bl_002_primary_source_verification_gate.md
 M docs/design/phase32_p30_bl_002_source_package.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_p30_bl_002_s01_formal_review.md
```

Manual documentation checks:

- edited markdown files have no trailing whitespace
- edited markdown files have exactly one final newline
- edited markdown files were inspected for completeness and were not truncated

## Explicitly Not Included

- `alpaca-trade-api` or unrelated SDK dependencies
- credentials
- environment-dependent normal tests
- network calls
- real broker connectivity
- websocket behavior
- scheduler/runtime loop
- live trading
- screener-driven order generation
- real execution-planning policy decisions beyond no-op pass-through and the
  max-intents cap
- accepted/rejected/skipped execution-planning policy logic beyond the
  max-intents cap
- accepted/rejected/skipped execution-planning decisions beyond the max-intents
  cap
- direct `ExecutionPlan` order/risk/status convenience fields
- execution-intent broker routing or adapter integration
- broker-facing request construction
- order submission
- client-order-id generation
- idempotency implementation
- batch cash reservation
- buying-power reservation
- same-symbol execution conflict handling
- duplicate or competing order policy implementation
- priority or ranking policy implementation
- scoring, direction, confidence, or actionability semantics unless explicitly
  designed and scoped
- research/backtesting outputs as direct trading logic
- notebooks or exploratory scripts in the deterministic core
- validated artifact metadata as signal generation
- validated artifact metadata as risk approval
- validated artifact persistence implementation
- validated signal definitions as live signal outputs
- validated signal definitions as execution decisions
- validated signal definitions as broker orders
- validated signal definitions as execution intents
- validated signal definitions as risk approvals
- signal evaluation input snapshots as signal computation
- signal evaluation input snapshots as live data access
- signal evaluation input snapshots as risk approvals
- signal evaluation input snapshots as execution intents or execution plans
- signal evaluation outputs as orders
- signal evaluation outputs as risk approvals
- signal evaluation outputs as execution intents or execution plans
- signal evaluator implementation beyond the minimal no-op metadata boundary
- real signal evaluator implementation
- evaluator protocol
- `SignalEvaluationResult` behavior beyond minimal advisory metadata
- no-op marker on `SignalEvaluationResult`
- signal evaluator registry
- signal computation from validated signal definitions
- system clock implementation
- signal input bundle completeness behavior beyond minimal metadata-only name
  validation
- strict extra-input rejection for signal input bundle completeness validation
- snapshot id or `as_of` compatibility enforcement for signal input bundle
  completeness validation
- signal input bundle behavior beyond minimal grouping, tuple coercion,
  duplicate-name rejection, and lookahead validation
- real evaluator consumption of `SignalInputBundle`
- first real evaluator implementation
- evaluator behavior beyond the Phase 29 Step 6 constants/output semantics
  design
- threshold evaluator behavior beyond the Phase 30 Step 1 research-support
  boundary
- threshold evaluator behavior beyond the Phase 30 Step 2 research validation
  evidence standard
- threshold evaluator behavior beyond the Phase 30 Step 3 research artifact
  review template
- threshold evaluator behavior beyond the Phase 30 Step 4 research artifact
  sourcing plan
- threshold evaluator behavior beyond the Phase 30 Step 5 unreviewed research
  candidate backlog
- threshold evaluator behavior beyond the Phase 30 Step 6 first candidate
  source selection
- threshold evaluator behavior beyond the Phase 31 Step 2 research-track next
  action plan
- threshold evaluator behavior beyond the Phase 31 Step 3 source package
  normalization
- threshold evaluator behavior beyond the Phase 31 Step 4 Tier A formal source
  review
- threshold evaluator behavior beyond the Phase 31 Step 5 evidence gap and
  routing plan
- threshold evaluator behavior beyond the Phase 31 Step 6 mechanics-only
  candidate artifact review summary
- threshold evaluator behavior beyond the Phase 31 Step 7 final mechanics-only
  disposition and next-candidate routing
- threshold evaluator behavior beyond the Phase 32 Step 1 dataset-specific
  validation candidate selection
- threshold evaluator behavior beyond the Phase 32 Step 2 P30-BL-002 source
  package sourcing plan
- threshold evaluator behavior beyond the Phase 32 Step 3 P30-BL-002 source
  package collection attempt
- threshold evaluator behavior beyond the Phase 32 Step 4 P30-BL-002 primary
  source verification gate
- threshold evaluator behavior beyond the Phase 32 Step 5 P30-BL-002 limited
  formal review intake plan
- threshold evaluator behavior beyond the Phase 32 Step 6 P30-BL-002-S01
  limited negative-control/no-lookahead formal review
- threshold evaluator behavior beyond the Phase 32 Step 7 P30-BL-002-S03
  limited negative-control/data-snooping/OOS guardrail formal review
- threshold evaluator behavior beyond the Phase 32 Step 8 P30-BL-002-S08
  methodology-only PIT formal review
- threshold evaluator behavior beyond the Phase 32 Step 9 P30-BL-002-S05
  limited candidate-evidence planning formal review
- SignalInputValue behavior beyond minimal observed scalar traceability
- feature computation
- strategy engine
- signal-evaluation-to-risk bridge
- input snapshot persistence implementation
- live data ingestion
- ML training implementation
- persistence writes
- audit logging writes
- LangGraph
- ML
- LLM trading-path logic

## Phase 32 Step 7 P30-BL-002-S03 Formal Review

Phase 32 Step 7 is documentation-only. It adds:

```text
docs/design/phase32_p30_bl_002_s03_formal_review.md
```

It updates routing/status references in the Phase 30-32 research docs and the
top-level checkpoint/core docs. This step formally reviews
`P30-BL-002-S03` only, using the Phase 32 Step 4 primary-source verification
gate and Phase 32 Step 5 intake plan as the source of truth.

The S03 review outcome is: pass for negative-control/data-snooping/OOS
guardrail use only. The pass is narrow. S03 can support falsification,
multiple-testing awareness, data-snooping guardrail design, and out-of-sample
negative-control expectations only. It does not support production threshold
approval, predictive-edge claims, profitability claims, validated artifact
readiness, validated signal definition readiness, implementation readiness,
paper trading readiness, or live trading readiness.

The review records unresolved S03 gaps for exact rule tables, parameter grids,
selection process, exact sample dates, OOS details and result, transaction-cost
assumptions, bootstrap assumptions, public code/data availability, and
deterministic reproduction. Any future exact rule reproduction, bootstrap
binding, exact OOS result claim, deterministic test binding, threshold
comparison, or stronger claim requires additional S03 evidence.

The next routing step is `P30-BL-002-S08` methodology-only formal review so
point-in-time methodology can be locked down before candidate evidence.

`P30-BL-002` remains candidate-only, unvalidated, unapproved, not promoted,
not production-ready, not implementation-ready, and not threshold-justified.
This phase does not create a `ValidatedResearchArtifact`, create a
`ValidatedSignalDefinition`, add evaluator behavior, add signal computation,
or add runtime, broker, persistence, ML, or LLM trading-path behavior.

Verification after Phase 32 Step 7:

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
 M docs/design/phase32_p30_bl_002_limited_formal_review_intake_plan.md
 M docs/design/phase32_p30_bl_002_primary_source_verification_gate.md
 M docs/design/phase32_p30_bl_002_source_package.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_p30_bl_002_s03_formal_review.md
```

## Phase 32 Step 8 P30-BL-002-S08 Formal Review

Phase 32 Step 8 is documentation-only. It adds:

```text
docs/design/phase32_p30_bl_002_s08_formal_review.md
```

It updates routing/status references in the Phase 30-32 research docs and the
top-level checkpoint/core docs. This step formally reviews
`P30-BL-002-S08` only, using the Phase 32 Step 4 primary-source verification
gate and Phase 32 Step 5 intake plan as the source of truth.

The S08 review outcome is: pass for methodology-only PIT review material
only. The pass is narrow. S08 can support point-in-time methodology framing,
survivorship-bias awareness, restatement / historical-revision awareness,
lookahead-risk framing, and constraints for later candidate-evidence reviews
only. It does not support production threshold approval, predictive-edge
claims, profitability claims, time-series momentum validation, validated
artifact readiness, validated signal definition readiness, implementation
readiness, paper trading readiness, live trading readiness, or trading
readiness.

The review records unresolved S08 gaps for publication/version date,
license/access restrictions, exact FQL behavior, timezone/cutoff behavior under
local data constraints, deterministic local replay path, and applicability to
any future offline point-in-time store. Any future exact data-contract binding,
vendor query semantics, deterministic local replay, threshold comparison, or
stronger claim requires additional S08 or replacement PIT evidence.

The next routing step is `P30-BL-002-S05` formal review as the first limited
candidate-evidence source. S05 must be evaluated under the PIT/no-lookahead,
survivorship, and restatement expectations recorded by S08. A future S05 pass,
if any, should mean only eligible for further structured evaluation, not
implementation-ready.

`P30-BL-002` remains candidate-only, unvalidated, unapproved, not promoted,
not production-ready, not implementation-ready, and not threshold-justified.
This phase does not create a `ValidatedResearchArtifact`, create a
`ValidatedSignalDefinition`, add evaluator behavior, add signal computation,
or add runtime, broker, persistence, ML, or LLM trading-path behavior.

Verification after Phase 32 Step 8:

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
 M docs/design/phase32_p30_bl_002_limited_formal_review_intake_plan.md
 M docs/design/phase32_p30_bl_002_primary_source_verification_gate.md
 M docs/design/phase32_p30_bl_002_source_package.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_p30_bl_002_s08_formal_review.md
```

## Phase 32 Step 9 P30-BL-002-S05 Formal Review

Phase 32 Step 9 is documentation-only. It adds:

```text
docs/design/phase32_p30_bl_002_s05_formal_review.md
```

It updates routing/status references in the Phase 30-32 research docs and the
top-level checkpoint/core docs. This step formally reviews
`P30-BL-002-S05` only, using the Phase 32 Step 4 primary-source verification
gate, Phase 32 Step 5 intake plan, S01 formal review, S03 formal review, S08
formal review, and existing source-package/backlog docs as the source of
truth.

The S05 review outcome is: conditional pass for limited candidate-evidence
planning only. The pass is narrow. S05 can support a bounded time-series
momentum candidate-evidence claim, future structured evaluation planning,
possible future reproduction requirements, and constraints for any future
candidate signal-definition discussion only. It does not support
implementation approval, production threshold/config approval,
`ValidatedResearchArtifact` creation, `ValidatedSignalDefinition` creation,
profitability claims, live-trading claims, generalization of reported source
results, signal computation, signal scoring, ranking, direction, confidence,
or actionability.

The review records unresolved S05 gaps for project-local deterministic
reproduction, production threshold/config provenance, applied no-lookahead
audit inside the project, implementation-scope approval, evaluator tests,
instrument-level universe reconstruction, futures roll rules, data-vendor
access and offline PIT replay, transaction costs, slippage, liquidity, margin,
leverage, financing, parameter-selection, multiple-testing, OOS, robustness
replay, and exact mapping to this project's advisory pre-risk semantics.

The next routing step is docs-only structured local reproduction/evidence
planning for S05, or additional sourcing if the S05 blockers prevent useful
planning. `P30-BL-002` remains candidate-only, unvalidated, unapproved, not
promoted, not production-ready, not implementation-ready, and not
threshold-justified.

This phase does not create a `ValidatedResearchArtifact`, create a
`ValidatedSignalDefinition`, add evaluator behavior, add signal computation,
or add runtime, broker, persistence, ML, or LLM trading-path behavior.

Verification after Phase 32 Step 9:

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
 M docs/design/phase32_p30_bl_002_limited_formal_review_intake_plan.md
 M docs/design/phase32_p30_bl_002_primary_source_verification_gate.md
 M docs/design/phase32_p30_bl_002_source_package.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_p30_bl_002_s05_formal_review.md
```

## Phase 32 Step 10 P30-BL-002 Source Status Index

Phase 32 Step 10 is documentation-only. It adds:

```text
docs/design/phase32_p30_bl_002_source_status_index.md
```

It updates only the top-level checkpoint/core docs for navigation. This step
creates a source-status index for normalized `P30-BL-002-S01` through
`P30-BL-002-S23`. The index consolidates current status, eligible use, formal
review doc where one exists, disposition, and next action. It does not
re-review sources, change dispositions, validate evidence, promote artifacts,
approve implementation, or introduce any production behavior.

The index preserves the completed formal-review outcomes:

- `P30-BL-002-S01`: limited negative-control / no-lookahead guardrail use
  only.
- `P30-BL-002-S03`: limited data-snooping / multiple-testing / OOS
  negative-control guardrail use only.
- `P30-BL-002-S08`: methodology-only PIT review material only.
- `P30-BL-002-S05`: conditional pass for limited candidate-evidence planning
  only.

Unreviewed sources remain marked as unreviewed scout-only material,
methodology context, unresolved source leads, preliminary reject/replacement
material, or quarantined-from-current-route material according to the existing
source package and verification docs. No unreviewed source is promoted to
validated evidence.

The next routing remains docs-only: either define a project-local deterministic
reproduction plan for `P30-BL-002-S05`, or perform additional source
verification only where existing gaps require it. Do not start implementation.

Remaining blockers are unchanged: no exact `ValidatedResearchArtifact`, no
exact `ValidatedSignalDefinition`, no project-local deterministic
reproduction, no production threshold/config provenance, no applied
no-lookahead audit inside the project, no implementation-scope approval, and
no evaluator tests.

This phase does not create a `ValidatedResearchArtifact`, create a
`ValidatedSignalDefinition`, add evaluator behavior, add signal computation,
or add runtime, broker, persistence, ML, or LLM trading-path behavior.

Verification after Phase 32 Step 10:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
passed; Git emitted LF-to-CRLF working-copy warnings only for modified
existing docs

git status --short
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_p30_bl_002_source_status_index.md
```

## Phase 32 Step 11 S05 Deterministic Reproduction Planning Boundary

Phase 32 Step 11 is documentation-only. It adds:

```text
docs/design/phase32_s05_deterministic_reproduction_planning_boundary.md
```

It updates only navigation/checkpoint docs around the new boundary. This step
defines requirements for a possible future project-local deterministic
reproduction of the `P30-BL-002-S05` time-series momentum candidate-evidence
claim. It does not reproduce, validate, approve, implement, score, rank, or
promote S05.

The bounded candidate claim remains limited to the existing S05 review:
time-series momentum framing for lagged own excess returns across 58
futures/forwards, January 1965 through December 2009, monthly
formation/holding framing, sign-based lagged-return variants, robustness
targets, and unresolved data, timing, cost, and reproducibility gaps.

The planning boundary records required future assumptions for universe
definition, historical price/return data, excess-return construction,
currency/contract handling, roll or continuous-futures handling, PIT
availability, survivorship, restatements/revisions, costs/slippage, and
missing data. It records required controls from S08 PIT discipline, S03
data-snooping/multiple-testing/OOS guardrails, and S01 no-lookahead
negative-control awareness.

Future phases remain planning-only: data availability assessment, dataset
schema/design, offline fixture or prototype dataset planning, reproduction
protocol design, deterministic research notebook/script boundary, result-review
template, and a promotion decision gate.

Remaining blockers include no exact `ValidatedResearchArtifact`, no exact
`ValidatedSignalDefinition`, no project-local deterministic reproduction, no
approved dataset, no production threshold/config provenance, no applied
no-lookahead audit inside the project, no implementation-scope approval, and
no evaluator tests.

This phase does not create a `ValidatedResearchArtifact`, create a
`ValidatedSignalDefinition`, add evaluator behavior, add signal computation,
add data ingestion, add a backtest engine, or add runtime, broker, persistence,
portfolio, ledger, reconciliation, Alpaca, ML, or LLM trading-path behavior.

Verification after Phase 32 Step 11:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
passed; Git emitted LF-to-CRLF working-copy warnings only for modified
existing docs

git status --short
 M docs/design/phase32_p30_bl_002_source_status_index.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_s05_deterministic_reproduction_planning_boundary.md
```

## Phase 32 Step 12 S05 Data Availability Assessment Boundary

Phase 32 Step 12 is documentation-only. It adds:

```text
docs/design/phase32_s05_data_availability_assessment_boundary.md
```

It updates only navigation/checkpoint docs around the new boundary. This step
defines the data categories, availability dimensions, dataset
acceptance/rejection criteria, feasibility outcomes, and routing choices that
would be required before any possible future project-local deterministic
reproduction of the `P30-BL-002-S05` candidate-evidence claim.

The required data categories are futures/forwards universe definition,
historical prices or returns, excess-return construction inputs, risk-free or
collateral return assumptions if required, contract rolls / continuous futures
construction, currency handling, timestamp/as-of availability, survivorship
metadata, restatement/revision metadata, transaction cost, slippage, liquidity,
execution assumption inputs, and missing-data flags or quality metadata.

Candidate dataset acceptance remains limited to future planning gates:
deterministic and versioned data, local reproducibility after acquisition,
documented provenance, stable schema, explicit timestamps/as-of semantics,
clear universe membership rules, clear roll/contract construction rules,
explicit missing-data handling, explicit cost/slippage treatment, and no
default online dependency during normal pytest.

Candidate dataset rejection triggers include unclear provenance, inability to
run offline, missing timestamp/as-of semantics where required, unevaluable
survivorship bias, undocumented continuous-contract construction, impossible
or meaningless universe mapping, incompatible licensing, uninspectable data
quality, hidden vendor logic, insufficient sample-window coverage, or missing
assumptions that cannot be separately modeled as limitations.

Possible outcomes are routing labels only: exact reproduction potentially
feasible, partial reproduction feasible, proxy reproduction feasible,
methodology-only reproduction feasible, not feasible without paid/vendor data,
or not feasible with current project constraints.

The recommended next route is dataset schema/design if data appears feasible,
source/vendor comparison or a data-provider matrix if data remains uncertain,
or downgrade of S05 to methodology/candidate-context only if data is
infeasible. No implementation is authorized.

Remaining blockers include no exact `ValidatedResearchArtifact`, no exact
`ValidatedSignalDefinition`, no approved dataset, no acquired data, no
project-local deterministic reproduction, no production threshold/config
provenance, no applied no-lookahead audit inside the project, no
implementation-scope approval, and no evaluator tests.

This phase does not acquire data, ingest data, implement a schema, add a
research script, add a notebook, add a backtest, implement a strategy,
implement a signal/evaluator, create a validated artifact, approve a
production threshold, or add broker, OMS, runtime, scheduler, persistence,
portfolio, ledger, reconciliation, Alpaca, ML, or LLM trading-path behavior.

Verification after Phase 32 Step 12:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
passed; Git emitted LF-to-CRLF working-copy warnings only for modified docs

git status --short
 M docs/design/phase32_p30_bl_002_source_status_index.md
 M docs/design/phase32_s05_deterministic_reproduction_planning_boundary.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_s05_data_availability_assessment_boundary.md
```

## Phase 32 Step 13 S05 Data Provider / Source Comparison Plan

Phase 32 Step 13 is documentation-only. It adds:

```text
docs/design/phase32_s05_data_provider_source_comparison_plan.md
```

It updates only navigation/checkpoint docs around the new boundary. This step
defines how future data-source categories should be compared for possible
`P30-BL-002-S05` deterministic reproduction feasibility. It does not select,
purchase, subscribe to, acquire, ingest, download, transform, store, validate,
reproduce, approve, or implement any data source.

The source categories to compare are academic/paper replication data, paid
institutional futures data, retail futures/continuous futures vendors,
broker-provided historical data, public/free datasets, internally constructed
proxy datasets, and methodology-only/manual reconstruction from published
tables.

Comparison criteria include S05 universe coverage, January 1965 through
December 2009 coverage, futures/forwards support, price/return series quality,
excess-return construction support, roll/continuous contract documentation,
PIT/as-of support, survivorship and delisting treatment, restatement/revision
handling, currency handling, transaction cost/slippage/liquidity inputs,
licensing for local research use, offline reproducibility after acquisition,
deterministic versioning, cost/complexity, and fit with normal pytest remaining
offline and credential-free.

Outcome categories are routing labels only: exact reproduction candidate,
partial reproduction candidate, proxy reproduction candidate, methodology-only
support, reject / incompatible, and unresolved / needs further source
verification.

The recommended next route is dataset schema/design if at least one exact or
partial candidate is plausible, a proxy reproduction worth/cost decision if
only proxy candidates are plausible, downgrade of S05 to
methodology/candidate-context only if only methodology support is plausible, or
a future source/vendor verification step if unresolved. No implementation is
authorized.

Remaining blockers include no exact `ValidatedResearchArtifact`, no exact
`ValidatedSignalDefinition`, no selected/approved dataset, no acquired data,
no project-local deterministic reproduction, no production threshold/config
provenance, no applied no-lookahead audit inside the project, no
implementation-scope approval, and no evaluator tests.

This phase does not choose a vendor, buy a subscription, acquire data, ingest
data, implement a schema, add code/notebooks/scripts, add a backtest,
implement a strategy, implement a signal/evaluator, create a validated
artifact, approve a production threshold, or add broker, OMS, runtime,
scheduler, persistence, portfolio, ledger, reconciliation, Alpaca, ML, or LLM
trading-path behavior.

Verification after Phase 32 Step 13:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
passed; Git emitted LF-to-CRLF working-copy warnings only for modified docs

git status --short
 M docs/design/phase32_p30_bl_002_source_status_index.md
 M docs/design/phase32_s05_data_availability_assessment_boundary.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_s05_data_provider_source_comparison_plan.md
```

## Phase 32 Step 14 S05 Data Provider Scout Research Normalization

Phase 32 Step 14 is documentation-only. It adds:

```text
docs/design/phase32_s05_data_provider_scout_research_normalization.md
```

It updates research-track navigation/checkpoint docs around the new
normalization. This step records the externally provided Perplexity output as
unverified scout research only. It separates scout-reported evidence,
normalization inferences, and unresolved questions, and it requires
primary-source verification before any dataset selection, source approval,
schema design, acquisition, or reproduction planning.

The normalized executive finding records, cautiously and without verification,
that exact S05 reproduction appears unlikely under personal/offline
constraints, partial or proxy reproduction appears more realistic, AQR appears
useful for factor-level calibration/context only, CSI/Pinnacle/Norgate and
possibly TradeStation require primary verification, institutional feeds appear
theoretically strong but practically unsuitable unless access/licensing is
resolved, and broker/free APIs appear unsuitable for exact S05 reproduction.

The candidate classification table covers AQR TSMOM factor data, CSI,
Pinnacle, Norgate, TradeStation, Bloomberg/LSEG/Datastream/institutional
feeds, retail charting/futures vendors, broker-native historical APIs,
public/free datasets, ETF/index proxy universe, and manually reconstructed
published table checks. The classifications are routing labels only and do
not validate, select, approve, or acquire any source.

The primary verification checklist records future questions for exact
instrument/contract coverage, January 1965 through December 2009 coverage,
futures/forwards support, individual contracts versus continuous series, roll
methodology, PIT/as-of/versioning, survivorship/delisting treatment,
restatement/revision handling, excess-return construction, currency,
transaction cost/slippage/liquidity fields, local archival permissions,
private repo permissions, derived-statistics sharing, offline use,
deterministic snapshots, and costs/subscriptions.

The recommended next route is a vendor/source primary-verification
questionnaire or direct outreach template focused first on CSI, Pinnacle,
Norgate, and AQR. TradeStation should be included only if the project owner
already has access or expects access. Broker/free APIs remain proxy-only or
unsuitable for exact S05 reproduction unless later primary evidence changes
that. No implementation is authorized.

Remaining blockers include no exact `ValidatedResearchArtifact`, no exact
`ValidatedSignalDefinition`, no selected/approved dataset, no primary-source
vendor verification, no acquired data, no project-local deterministic
reproduction, no production threshold/config provenance, no applied
no-lookahead audit inside the project, no implementation-scope approval, and
no evaluator tests.

This phase does not choose a vendor, buy a subscription, acquire data, ingest
data, implement a schema, add code/notebooks/scripts, add a backtest,
implement a strategy, implement a signal/evaluator, create a validated
artifact, approve a production threshold, or add broker, OMS, runtime,
scheduler, persistence, portfolio, ledger, reconciliation, Alpaca, ML, or LLM
trading-path behavior.

Verification after Phase 32 Step 14:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
passed; Git emitted LF-to-CRLF working-copy warnings only for modified docs

git status --short
 M docs/design/phase31_research_track_next_action_plan.md
 M docs/design/phase32_p30_bl_002_source_status_index.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_s05_data_provider_scout_research_normalization.md
```

## Phase 32 Step 15 S05 Primary Verification Questionnaire / Outreach Template

Phase 32 Step 15 is documentation-only. It adds:

```text
docs/design/phase32_s05_primary_verification_questionnaire.md
```

It updates research-track navigation/checkpoint docs around the new
questionnaire. This step defines a primary-verification questionnaire and
manual outreach template for candidate S05 data sources. It is intended to
support future manual outreach or primary documentation review only. It does
not select, approve, purchase, acquire, ingest, store, validate, reproduce, or
implement any data source.

The questionnaire covers CSI, Pinnacle, Norgate, AQR, and conditional
TradeStation only if project-owner access already exists or is expected. Its
general verification questions cover exact instrument and contract coverage,
S05 58 futures/forwards universe mapping, January 1965 through December 2009
coverage, individual versus continuous contracts, roll methodology and roll
metadata, PIT/as-of/versioning, survivorship/delisting treatment,
restatement/revision/correction handling, excess-return construction inputs,
currency handling, cost/slippage/liquidity fields, missing-data and quality
metadata, licensing, private local archival, private repository use,
derived-statistics publication, offline use, deterministic snapshots, and
cost/subscription requirements.

Source-specific sections ask AQR whether only factor data or any raw panel is
available; ask CSI about contract-level coverage, continuous-series options,
earliest coverage, export format/versioning, and roll/back-adjustment details;
ask Pinnacle about CLC methodology, asset-class breadth, historical depth, and
individual versus linked series; ask Norgate about start dates, contract versus
continuous availability, offline export workflow, and whether 1965-1980 gaps
make it partial/proxy only; and ask TradeStation only conditionally about
access, export rights, and offline freezing.

The response-capture table records source, question area, answer, evidence or
contact reference, confidence, reproduction implication, licensing
implication, and follow-up needed. The routing rules classify a source only as
exact reproduction candidate, partial candidate, proxy candidate,
calibration/context only, reject, or unresolved. These are routing labels only
and do not validate S05 or authorize implementation.

Remaining blockers include no exact `ValidatedResearchArtifact`, no exact
`ValidatedSignalDefinition`, no selected/approved dataset, no completed
primary-source vendor verification, no acquired data, no project-local
deterministic reproduction, no production threshold/config provenance, no
applied no-lookahead audit inside the project, no implementation-scope
approval, and no evaluator tests.

This phase does not choose a vendor, buy a subscription, acquire data, ingest
data, implement a schema, add code/notebooks/scripts, add a backtest,
implement a strategy, implement a signal/evaluator, create a validated
artifact, approve a production threshold, or add broker, OMS, runtime,
scheduler, persistence, portfolio, ledger, reconciliation, Alpaca, ML, or LLM
trading-path behavior.

Verification after Phase 32 Step 15:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
passed; Git emitted LF-to-CRLF working-copy warnings only for modified docs

git status --short
 M docs/design/phase31_research_track_next_action_plan.md
 M docs/design/phase32_p30_bl_002_source_status_index.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_s05_primary_verification_questionnaire.md
```

## Phase 32 Step 16 S05 Public Documentation Verification Sweep

Phase 32 Step 16 is documentation-only. It adds:

```text
docs/design/phase32_s05_public_documentation_verification_sweep.md
```

It updates research-track navigation/checkpoint docs around the new public
documentation sweep. This step records what appears supported by public
documentation for S05 candidate data-source categories, while treating the
externally provided Perplexity report as scout research input only. It does not
replace direct vendor/source confirmation and does not select, approve,
purchase, acquire, ingest, store, validate, reproduce, or implement any data
source.

The sweep applies an evidence-quality policy that separates primary
documentation, secondary documentation, and inference. Public vendor
documentation may support cautious routing labels, but it does not equal legal
approval, signed license approval, local archival permission, private
repository permission, offline-use permission, or deterministic snapshot
support. Marketing claims remain provisional until supported by detailed
documentation or direct confirmation.

Sources reviewed include AQR TSMOM factor data, CSI, Pinnacle/CLC, Norgate
futures package, Portara/PortaraCQG, TradeStation, institutional feeds such as
Bloomberg/LSEG/Datastream at high level, broker-native historical APIs, and
public/free APIs plus ETF/index proxies.

The cautious feasibility labels are:

- AQR: calibration/context only.
- CSI: documentation-supported partial candidate.
- Pinnacle/CLC: documentation-supported partial candidate, with proxy limits
  still possible.
- Norgate: documentation-supported proxy candidate.
- Portara/PortaraCQG: documentation-supported partial candidate.
- TradeStation: likely unsuitable as a primary S05 source.
- Institutional feeds: calibration/context only under current personal/offline
  constraints.
- Broker-native historical APIs: likely unsuitable as a primary S05 source.
- Public/free APIs and ETF/index proxies: documentation-supported proxy
  candidate only.

Remaining unclear items include exact S05 universe mapping, January 1965
through December 2009 coverage by instrument, individual contract availability,
continuous contract construction, roll methodology and roll metadata, PIT/as-of
versioning, previous-version preservation after corrections, survivorship and
delisting treatment, corrections/revisions handling, missing-data and quality
flags, excess-return inputs, collateral/risk-free assumptions, currency
handling, local archival permission, private repository permission, automated
local test usage permission, derived-statistics publication permission, offline
use after acquisition, deterministic snapshot/version support, and
pricing/subscription terms.

Recommended routing is to keep CSI, Pinnacle, Norgate, and Portara in the
direct-confirmation queue; keep AQR as calibration/context unless raw
instrument-level access is verified; keep TradeStation conditional/proxy-only
unless owner access and export/archival rights are verified; and mark broker,
free API, and ETF/index proxy routes unsuitable for primary S05 reproduction.
No provider should be chosen yet, and no dataset schema should be designed
unless a later phase explicitly decides there is enough source clarity.

Remaining blockers include no exact `ValidatedResearchArtifact`, no exact
`ValidatedSignalDefinition`, no selected/approved dataset, no completed
primary-source vendor verification, no acquired data, no project-local
deterministic reproduction, no production threshold/config provenance, no
applied no-lookahead audit inside the project, no implementation-scope
approval, and no evaluator tests.

This phase does not choose a provider, buy a subscription, acquire data, ingest
data, implement a schema, add code/notebooks/scripts, add a backtest,
implement a strategy, implement a signal/evaluator, create a validated
artifact, approve a production threshold, or add broker, OMS, runtime,
scheduler, persistence, portfolio, ledger, reconciliation, Alpaca, ML, or LLM
trading-path behavior.

Verification after Phase 32 Step 16:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
passed; Git emitted LF-to-CRLF working-copy warnings only for modified docs

git status --short
 M docs/design/phase31_research_track_next_action_plan.md
 M docs/design/phase32_p30_bl_002_source_status_index.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_s05_public_documentation_verification_sweep.md
```

## Phase 32 Step 17 S05 Public-Documentation-Only Feasibility Decision

Phase 32 Step 17 is documentation-only. It adds:

```text
docs/design/phase32_s05_public_documentation_only_feasibility_decision.md
```

It updates research-track navigation/checkpoint docs around the owner decision
to avoid external vendor/source contact for now. Vendor/source direct
confirmation remains optional future work, not a current dependency.

Without direct vendor/source confirmation or acquired access, exact S05
reproduction cannot be established. No source can be selected or approved from
public documentation alone, and licensing, archival, private repo use,
derived-statistics publication, PIT/versioning, exact universe coverage,
roll metadata, correction history, and offline-use rights remain unresolved
unless public docs fully answer them.

The public-documentation-only routing remains cautious: AQR is
calibration/context only; CSI is a documentation-supported partial candidate,
not selected; Pinnacle/CLC is a documentation-supported partial/proxy
candidate, not selected; Norgate is a documentation-supported proxy candidate,
not selected; Portara/PortaraCQG is a documentation-supported partial
candidate, not selected; TradeStation is likely unsuitable as primary and only
conditional/proxy; institutional feeds are calibration/context only under
current personal/offline constraints; broker-native APIs are likely unsuitable;
and public/free APIs plus ETF/index proxies are proxy only.

The feasibility decision keeps S05 as a public-doc-supported proxy/partial
planning candidate only. Exact reproduction, source selection, dataset
approval, acquisition, schema design, validation, and implementation are paused
unless future public evidence, owner-approved direct confirmation, or
owner-approved access changes materially.

Recommended safe routes are a docs-only non-exact proxy reproduction boundary,
pausing S05 to evaluate another candidate with easier data availability, or
keeping S05 in the backlog pending future vendor contact, budget/access change,
or stronger public documentation.

This phase does not contact vendors, choose a vendor, buy a subscription,
acquire data, ingest data, add schema/code/notebooks/scripts, add a backtest,
reproduce S05, implement a strategy, implement a signal/evaluator, create a
validated artifact, approve a production threshold, or add broker, OMS,
runtime, scheduler, persistence, portfolio, ledger, reconciliation, Alpaca, ML,
or LLM trading-path behavior.

Remaining blockers include no exact `ValidatedResearchArtifact`, no exact
`ValidatedSignalDefinition`, no selected/approved dataset, no completed
primary-source vendor verification, no acquired data, no project-local
deterministic reproduction, no production threshold/config provenance, no
applied no-lookahead audit inside the project, no implementation-scope
approval, no evaluator tests, no deterministic offline snapshot path, and no
resolved exact S05 universe, 1965-2009 instrument coverage, raw contract, roll,
PIT/as-of, correction-history, or versioning basis.

Verification after Phase 32 Step 17:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
passed; Git emitted LF-to-CRLF working-copy warnings only for modified docs

git status --short
 M docs/design/phase31_research_track_next_action_plan.md
 M docs/design/phase32_p30_bl_002_source_status_index.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_s05_public_documentation_only_feasibility_decision.md
```

Manual documentation checks confirmed that edited markdown files have no
trailing whitespace, exactly one final newline, no truncation, and intact final
sections.

## Phase 32 Step 18 S05 Non-Exact Proxy Reproduction Boundary

Phase 32 Step 18 is documentation-only. It adds:

```text
docs/design/phase32_s05_non_exact_proxy_reproduction_boundary.md
```

It defines non-exact proxy reproduction as a controlled approximation intended
to test methodology mechanics and research workflow discipline, not to recreate
S05 exactly. It distinguishes exact S05 reproduction, partial reproduction,
proxy reproduction, and methodology-only/context use.

Allowed proxy routes are planning-only: modern futures subset using a
public-doc-supported vendor category with no vendor selected, reduced-universe
futures proxy, ETF/index proxy universe, AQR factor-level calibration/context
check, and manually reconstructed published-table checks.

A future proxy route could support deterministic research workflow testing,
no-lookahead/as-of discipline testing, data handling and provenance discipline,
rough methodology sanity checks, broad-behavior comparison against published
context, and a later decision about whether deeper data investment is
worthwhile.

Proxy reproduction cannot support exact S05 replication, a
`ValidatedResearchArtifact`, a `ValidatedSignalDefinition`, production
threshold/config approval, live or paper trading readiness, profitability or
generalization claims, implementation approval, or a claim that S05's original
edge has been reproduced.

Any future proxy plan still needs explicit universe, date range, source and
provenance, offline snapshot/versioning plan, no-lookahead/as-of assumptions,
survivorship and missing-data assumptions, cost/slippage assumptions if
relevant, comparison target, limitations, non-claims, deterministic
reproducibility, and normal offline credential-free pytest.

The future docs-only gates are proxy route selection boundary, proxy dataset
schema/design boundary, proxy fixture/data-storage policy boundary, proxy
reproduction protocol boundary, proxy result-review template, and
promotion/rejection decision boundary.

The recommended next route is to keep S05 in proxy/partial planning only, do
not implement, and either write a docs-only proxy route selection boundary or
evaluate another candidate with easier data availability.

This phase does not perform exact replication, select a dataset, acquire data,
ingest data, add schema/code/notebooks/scripts, add a backtest, reproduce S05,
implement a strategy, implement a signal/evaluator, create a validated
artifact, approve a production threshold, or add broker, OMS, runtime,
scheduler, persistence, portfolio, ledger, reconciliation, Alpaca, ML, or LLM
trading-path behavior.

Remaining blockers include no exact `ValidatedResearchArtifact`, no exact
`ValidatedSignalDefinition`, no selected/approved dataset, no completed
primary-source vendor verification, no acquired data, no project-local
deterministic reproduction, no production threshold/config provenance, no
applied no-lookahead audit inside the project, no implementation-scope
approval, no evaluator tests, no approved proxy route, no approved proxy
data-storage policy, no approved proxy reproduction protocol, no deterministic
offline snapshot path, and no resolved exact S05 universe, 1965-2009 instrument
coverage, raw contract, roll, PIT/as-of, correction-history, or versioning
basis.

Verification after Phase 32 Step 18:

```text
python -m pytest
778 passed, 4 skipped

git diff --name-only HEAD -- src
(no output)

git diff --check
passed; Git emitted LF-to-CRLF working-copy warnings only for modified docs

git status --short
 M docs/design/phase31_research_track_next_action_plan.md
 M docs/design/phase32_p30_bl_002_source_status_index.md
 M docs/deterministic_core.md
 M docs/project_checkpoint.md
?? docs/design/phase32_s05_non_exact_proxy_reproduction_boundary.md
```

Manual documentation checks confirmed that edited markdown files have no
trailing whitespace, exactly one final newline, no truncation, and intact final
sections.

## Phase 32 Step 19 S05 Proxy Route Selection Boundary

Phase 32 Step 19 is documentation-only. It adds:

```text
docs/design/phase32_s05_proxy_route_selection_boundary.md
```

It compares allowed non-exact S05 proxy routes for planning only: modern
futures subset, reduced-universe futures, ETF/index proxy, AQR factor-level
calibration/context, manually reconstructed published-table checks, and
pause/defer S05 while evaluating another easier-data candidate.

The comparison criteria are data availability, offline reproducibility,
licensing uncertainty, S05 similarity, methodological usefulness,
no-lookahead/as-of discipline usefulness, cost/complexity, risk of
overclaiming, fit with normal offline credential-free pytest, and usefulness
before any code implementation.

The route decision is conservative: keep multiple proxy routes under
consideration for docs-only planning, but select no single route for data,
schema, reproduction, validation, or implementation planning. The futures
routes remain most methodology-relevant but too unresolved for narrowing; the
ETF/index route remains workflow-rehearsal only; AQR and published-table routes
remain context/table-check only; and S05 remains proxy/partial planning and
backlog status.

The recommended next gate is a route-neutral proxy dataset requirement
boundary. That gate should define minimum requirements for any later proxy
route before narrowing, without selecting or approving a provider, dataset,
subscription, schema, reproduction, validation, or implementation.

This phase does not perform exact replication, select a dataset, acquire data,
ingest data, add schema/code/notebooks/scripts, add a backtest, reproduce S05,
implement a strategy, implement a signal/evaluator, create a validated
artifact, approve a production threshold, or add broker, OMS, runtime,
scheduler, persistence, portfolio, ledger, reconciliation, Alpaca, ML, or LLM
trading-path behavior.

Remaining blockers include no exact `ValidatedResearchArtifact`, no exact
`ValidatedSignalDefinition`, no selected/approved dataset, no completed
primary-source vendor verification, no acquired data, no project-local
deterministic reproduction, no production threshold/config provenance, no
applied no-lookahead audit inside the project, no implementation-scope
approval, no evaluator tests, no selected proxy route for data planning, no
approved proxy data-storage policy, no approved proxy reproduction protocol, no
deterministic offline snapshot path, and no resolved exact S05 universe,
1965-2009 instrument coverage, raw contract, roll, PIT/as-of,
correction-history, or versioning basis.

## Phase 32 Step 20 S05 Route-Neutral Proxy Dataset Requirements Boundary

Phase 32 Step 20 is documentation-only. It adds:

```text
docs/design/phase32_s05_route_neutral_proxy_dataset_requirements_boundary.md
```

It defines minimum requirements for any possible future S05 proxy dataset while
remaining route-neutral. It does not choose among modern futures, reduced
futures, ETF/index proxy, AQR factor-level context, or manually reconstructed
published-table checks.

The requirements cover universe definition, date range, frequency,
price/return fields, timestamp/as-of semantics, provenance,
versioning/snapshot discipline, missing-data handling, survivorship,
corporate-action or contract-adjustment assumptions, roll/continuous
construction assumptions, currency handling, cost/slippage/liquidity
assumptions, license/offline-use constraints, reproducibility constraints, and
comparison target.

It records route-specific notes without route selection for modern futures
subset, reduced-universe futures, ETF/index proxy, AQR factor-level
calibration/context, and manually reconstructed published-table checks. Each
route remains a planning possibility only, with special requirements and
weaknesses documented to prevent overclaiming.

Minimum future acceptance criteria include an explicit non-S05-exact label,
clear universe and date range, documented source/provenance, deterministic
local snapshot plan, explicit `as_of` and no-lookahead assumptions, explicit
survivorship and missing-data assumptions, cost/slippage assumptions where
relevant, a clear comparison target, limitations and non-claims, and normal
pytest remaining offline and credential-free.

Future proxy plans should be rejected or deferred if source/provenance is
unclear, the route is framed as exact S05 replication, data cannot be
snapshotted deterministically, license/offline-use constraints block local
use, `as_of` and no-lookahead assumptions cannot be stated, universe/date range
are ambiguous, methodology encourages overclaiming, or the plan implies
implementation or validation before reproduction review.

Required non-claims state that any future proxy dataset plan does not prove
exact S05 replication, original S05 edge, profitability, live or paper trading
readiness, production threshold validity, strategy generalization, or
implementation approval.

Future docs-only gates may include proxy route selection revisit, proxy dataset
source shortlist boundary, proxy data storage/fixture policy boundary, proxy
reproduction protocol boundary, proxy result-review template, or pausing S05
and evaluating another easier-data candidate.

The safest next routing is to keep S05 in backlog after documenting proxy
requirements. If one more S05 planning step is useful, it should be a docs-only
proxy dataset source shortlist boundary without selecting, approving,
acquiring, ingesting, or implementing data. The other safe route is to evaluate
another easier-data research candidate.

This phase does not perform exact replication, select a route, select a
dataset, acquire data, ingest data, add schema/code/notebooks/scripts, add a
backtest, reproduce S05, implement a strategy, implement a signal/evaluator,
create a validated artifact, approve a production threshold, or add broker,
OMS, runtime, scheduler, persistence, portfolio, ledger, reconciliation,
Alpaca, ML, or LLM trading-path behavior.

Remaining blockers include no exact `ValidatedResearchArtifact`, no exact
`ValidatedSignalDefinition`, no selected/approved dataset, no completed
primary-source vendor verification, no acquired data, no project-local
deterministic reproduction, no production threshold/config provenance, no
applied no-lookahead audit inside the project, no implementation-scope
approval, no evaluator tests, no selected proxy route, no approved proxy
dataset source shortlist, no approved proxy data-storage or fixture policy, no
approved proxy reproduction protocol, no deterministic offline snapshot path,
and no resolved exact S05 universe, 1965-2009 instrument coverage, raw
contract, roll, PIT/as-of, correction-history, or versioning basis.

## Phase 32 Step 21 S05 Proxy Source Shortlist and Backlog Routing Decision

Phase 32 Step 21 is documentation-only. It adds:

```text
docs/design/phase32_s05_proxy_source_shortlist_and_backlog_routing.md
```

It groups non-approving S05 proxy source categories with a backlog and
next-routing decision. It does not select a dataset, approve a source, acquire
data, design schemas, define a reproduction protocol, validate S05, or
authorize implementation.

The non-approving shortlist covers AQR factor-level data for
calibration/context, ETF/index proxy datasets, public/free market data for
methodology demos only, unselected modern futures vendor categories,
unselected reduced futures universe categories, and manually reconstructed
public-table checks.

For each category, the boundary records possible role, strengths,
limitations, overclaiming risk, Step 20 minimum-requirement status, and current
status. Every category remains candidate category only, not selected, and none
satisfies the Step 20 minimum requirements at category-only level.

The conservative backlog decision is to keep S05 in backlog and avoid another
immediate S05-specific docs-only proxy planning gate. Step 20 and Step 21 are
enough to preserve future optionality without narrowing a route, approving a
source, selecting a dataset, designing a schema, defining reproduction, or
authorizing implementation.

The easier-data candidate routing says the next research-track effort should
evaluate another candidate with public data, clear licensing, offline
reproducibility, a simpler universe, easier benchmark comparison, lower
PIT/survivorship complexity, no vendor contact dependency, and no immediate
implementation requirement.

The chosen next project route is to keep S05 in backlog and evaluate an
easier-data candidate next. Deferred gates are data storage/fixture policy,
schema/design, reproduction protocol, result-review template, and any code or
tests.

This phase does not perform exact replication, approve a route, select a
dataset, acquire data, ingest data, add schema/code/notebooks/scripts, create a
storage/fixture policy, define a reproduction protocol, add a backtest,
reproduce S05, implement a strategy, implement a signal/evaluator, create a
validated artifact, approve a production threshold, or add broker, OMS,
runtime, scheduler, persistence, portfolio, ledger, reconciliation, Alpaca, ML,
or LLM trading-path behavior.

Remaining blockers include no exact `ValidatedResearchArtifact`, no exact
`ValidatedSignalDefinition`, no selected/approved dataset, no completed
primary-source vendor verification, no acquired data, no project-local
deterministic reproduction, no production threshold/config provenance, no
applied no-lookahead audit inside the project, no implementation-scope
approval, no evaluator tests, no selected proxy route, no approved proxy source
category, source, provider, or dataset, no approved proxy data-storage or
fixture policy, no approved proxy reproduction protocol, no deterministic
offline snapshot path, and no resolved exact S05 universe, 1965-2009
instrument coverage, raw contract, roll, PIT/as-of, correction-history, or
versioning basis.

## Phase 33 Step 1 Easier-Data Research Candidate Selection Boundary

Phase 33 Step 1 is documentation-only. It adds:

```text
docs/design/phase33_easier_data_research_candidate_selection_boundary.md
```

It also updates research-track navigation/checkpoint context only. The new
boundary compares easier-data candidate families by public or easy-access data
availability, licensing clarity, offline reproducibility, simple universe
definition, PIT/as-of complexity, survivorship complexity, benchmark clarity,
deterministic-workflow usefulness, core-architecture fit, overclaiming risk,
vendor-contact dependency, and implementation distance.

The boundary keeps S05 paused in backlog. S05 remains useful as a
public-document-supported proxy/partial planning candidate, but exact
reproduction, dataset approval, schema design, project-local reproduction,
validation, and implementation remain paused.

The compared candidate families are equity index momentum/trend-following
using public index or ETF data, equity cross-sectional momentum using
public/free data with survivorship caveats, simple moving-average
trend-following on broad ETFs, volatility targeting or risk-parity style
allocation using public ETF/index data, pairs/spread research only where data
and benchmark constraints are clear, and S05 futures momentum in backlog.

The conservative decision is a docs-only shortlist for further source review:
simple moving-average trend-following on broad ETFs as the primary next
source-package candidate, plus equity index momentum/trend-following using
public index or ETF data and volatility-targeting/risk-parity style allocation
using public ETF/index data as secondary source-review candidates only. The
decision does not approve any dataset, source package, reproduction,
validation, implementation, production threshold, or trading implication.

Recommended next gate: source package for the selected easier-data candidate,
starting with simple moving-average trend-following on broad ETFs. That later
gate must still avoid data acquisition, ingestion, schema design, backtesting,
reproduction, evaluator implementation, signal computation, validated-artifact
creation, and validated signal-definition creation.

This phase does not perform or authorize implementation, data acquisition,
data ingestion, dataset approval, source approval, schema/code/notebooks/scripts,
backtesting, reproduction, signal or evaluator implementation, signal
computation, scoring, ranking, direction, confidence, actionability,
`ValidatedResearchArtifact`, `ValidatedSignalDefinition`, new contract type,
production threshold, production-readiness claim, implementation-readiness
claim, profitability claim, trading implication, or broker, OMS, runtime,
scheduler, persistence, portfolio, ledger, reconciliation, Alpaca, ML, or LLM
trading-path behavior.

Remaining blockers include no `ValidatedResearchArtifact`, no
`ValidatedSignalDefinition`, no selected/approved dataset, no selected/approved
source package, no project-local deterministic reproduction, no production
threshold/config provenance, no applied no-lookahead audit, no
implementation-scope approval, no evaluator tests, no data acquisition or
ingestion approval, no schema or storage policy approval, no
benchmark/comparison target approval, no offline snapshot approval, no
licensing/offline-use review for a selected source, no candidate-specific
source review, no validated signal definition binding, and no trading
implication or production threshold.

## Phase 33 Step 2 Broad ETF Moving-Average Source Package

Phase 33 Step 2 is documentation-only. It adds:

```text
docs/design/phase33_broad_etf_moving_average_source_package.md
```

It also updates research-track navigation/checkpoint context only. The source
package prepares source review for the broad-ETF simple moving-average
trend-following candidate. It records the bounded research question, possible
broad ETF categories, high-level methodology framing, possible public/easy
data-source categories, source-quality requirements, later evidence sources,
future docs-only review gates, explicit non-goals, and remaining blockers.

The bounded research question is whether simple moving-average
trend-following on broad liquid ETFs can be evaluated as an easier-data
research candidate under deterministic, offline-safe project standards. This
is a source-review prompt only, not a profitability, implementation-readiness,
production-readiness, or trading claim.

Possible future review categories are broad U.S. equity index ETFs, broad
international equity ETFs, broad bond ETFs, broad commodity or gold ETFs if
source quality allows, and a cash/T-bill proxy or risk-free comparison source.
No final ETF universe, ticker list, issuer, index family, benchmark, cash
proxy, inclusion rule, exclusion rule, or inception handling rule is selected.

Possible source categories for later review include Stooq, Yahoo Finance /
yfinance, Nasdaq Data Link where applicable, Alpha Vantage free or retail
APIs, broker historical data as context only and not the default source,
official ETF issuer pages for metadata, and FRED where applicable for
risk-free or cash-proxy context. All are candidates for source review only.
Public availability is not license approval, and easy access is not project
approval.

Source-quality requirements include adjusted-close or total-return handling,
dividend/split adjustment transparency, timestamp/date semantics,
survivorship caveats, delisting and inception-date handling, missing-data
handling, stable symbol identity, local snapshot/versioning possibility,
license/offline-use clarity, benchmark comparability, and confirmation that
normal `python -m pytest` remains deterministic, offline, credential-free, and
independent of any data-source account or network access.

Future review gates remain docs-only and include public data source
feasibility review, ETF universe definition boundary, benchmark/cash proxy
boundary, methodology-only moving-average review, no-lookahead/as-of review,
reproduction protocol boundary, result-review template, and promotion or
rejection decision boundary.

This phase does not perform or authorize ETF universe approval, data source
approval, data acquisition, data ingestion, schema/code/notebooks/scripts,
backtesting, reproduction, strategy implementation, evaluator or signal
implementation, signal computation, validated artifacts, validated signal
definitions, production thresholds, production-readiness claims,
implementation-readiness claims, profitability claims, trading implications,
or broker, OMS, runtime, scheduler, persistence, portfolio, ledger,
reconciliation, Alpaca, ML, or LLM trading-path behavior.

Remaining blockers include no `ValidatedResearchArtifact`, no
`ValidatedSignalDefinition`, no approved ETF universe, no selected/approved
data source, no acquired data, no project-local deterministic reproduction,
no benchmark/cash proxy approval, no no-lookahead audit, no production
threshold/config provenance, no implementation-scope approval, no evaluator
tests, no approved dataset/source package/offline snapshot policy, no
license/offline-use approval, no methodology-only moving-average review, no
reproduction protocol approval, no result-review template approval, no
promotion/rejection decision, and no trading implication or production
threshold.

## Phase 33 Step 3 Broad ETF Data Feasibility, Universe, and Benchmark Boundary

Phase 33 Step 3 is documentation-only. It adds:

```text
docs/design/phase33_broad_etf_data_feasibility_universe_benchmark_boundary.md
```

It also updates research-track navigation/checkpoint context only. The grouped
boundary evaluates candidate public/easy data source feasibility, defines
future ETF universe requirements, and defines future benchmark/cash proxy
requirements for the broad-ETF simple moving-average trend-following
candidate.

The candidate remains the primary easier-data source-review candidate only. It
is not validated, implemented, production-ready, trading-ready, or actionable.

The data source feasibility comparison covers Stooq, Yahoo Finance / yfinance,
Nasdaq Data Link where applicable, Alpha Vantage free/retail APIs, official
ETF issuer pages, FRED where applicable, and broker historical data as context
only. Each category records possible role, strengths, weaknesses,
adjusted-price or total-return support, local snapshot possibility,
licensing/offline-use clarity, fit with normal offline credential-free pytest,
and cautious current status. All categories remain candidate or context
sources only, not approved.

Future ETF universe requirements include broad, liquid, simple instruments,
clear inception dates, stable symbol identity, sufficient history,
survivorship-bias controls, anti-cherry-picking controls, inactive/delisted
handling where applicable, asset class categories before performance
inspection, and preference for broad-market exposures over niche/thematic
ETFs. No final ETF list or universe rule is approved.

Future benchmark/cash proxy requirements include buy-and-hold comparison
definition, cash or T-bill proxy definition, FRED as a candidate risk-free
series source only where applicable, date alignment, ETF inception handling,
total-return versus price-return caveats, and transaction cost/friction
assumptions to define later. No benchmark or cash proxy is approved.

Source-quality requirements include adjusted close/corporate-action handling,
dividend and split adjustment transparency, timestamp/date semantics,
missing-data handling, local snapshot/versioning, provenance and citation,
license/offline-use review, deterministic reproducibility, explicit
no-lookahead assumptions, and normal pytest remaining offline and
credential-free.

The allowed cautious feasibility labels are promising for source review,
usable only as secondary/check source, proxy/context only, unresolved / needs
documentation review, and likely unsuitable. They are routing labels only and
do not approve any data source, universe, benchmark, or implementation.

The recommended next docs-only gate is a public-source documentation
verification sweep. A methodology-only moving-average review should wait until
basic source documentation questions are clearer. If the source route cannot
remain public/easy, license-reviewable, offline-safe, and non-claiming, the
candidate should remain in backlog or route to another easier-data candidate.

This phase does not perform or authorize data approval, ETF universe approval,
benchmark approval, data acquisition, data ingestion, schema/code/notebooks/scripts,
backtesting, reproduction, methodology approval, moving-average parameter
approval, strategy implementation, evaluator or signal implementation, signal
computation, validated artifacts, validated signal definitions, production
thresholds, profitability claims, trading implications, or broker, OMS,
runtime, scheduler, persistence, portfolio, ledger, reconciliation, Alpaca, ML,
or LLM trading-path behavior.

Remaining blockers include no `ValidatedResearchArtifact`, no
`ValidatedSignalDefinition`, no approved ETF universe, no selected/approved
data source, no approved benchmark/cash proxy, no acquired data, no
project-local deterministic reproduction, no no-lookahead audit, no production
threshold/config provenance, no implementation-scope approval, no evaluator
tests, no approved methodology, no approved moving-average parameters, no
approved data license/offline-use path, no approved local snapshot/versioning
policy, no source-documentation approval or terms/license resolution, no
total-return versus price-return comparison decision, no transaction
cost/friction review, no result-review template, no promotion/rejection
decision, and no trading implication or production threshold.

## Phase 33 Step 4 Broad ETF Public-Source Documentation Verification Sweep

Phase 33 Step 4 is documentation-only. It adds:

```text
docs/design/phase33_broad_etf_public_source_documentation_verification_sweep.md
```

It also updates research-track navigation/checkpoint context only. The sweep
records what appears supported by public documentation for broad ETF data, ETF
metadata, and cash/benchmark candidates while preserving the boundary that
public documentation is not legal, license, redistribution, private-repository,
offline-use, data, universe, benchmark, methodology, reproduction, validation,
or implementation approval.

The evidence-quality policy separates primary documentation, secondary
documentation, and inference. It treats the external Perplexity report as
public-documentation scout research only, not as source of truth, and does not
promote marketing, third-party, client-library, search-snippet, or scout-report
claims into verified project facts without official documentation support.

The sweep covers Stooq, Yahoo Finance / yfinance, Nasdaq Data Link, Alpha
Vantage, official ETF issuer pages such as iShares/BlackRock, Vanguard,
SPDR/State Street, and Invesco, FRED, and broker historical data as context
only. It assigns the allowed cautious feasibility labels only: promising for
source review, usable only as secondary/check source, proxy/context only,
unresolved / needs documentation review, and likely unsuitable.

The assigned routing labels are cautious and non-approving:

- Stooq: promising for source review, with adjusted/dividend/revision/license
  details unresolved.
- Yahoo Finance / yfinance: promising for source review, with automation, API
  stability, cache/archive, adjustment methodology, and private-repo terms
  unresolved.
- Nasdaq Data Link: usable only as secondary/check source unless specific ETF
  coverage and terms are later clarified.
- Alpha Vantage: usable only as secondary/check source because rate limits,
  ETF coverage, adjustment detail, and archival terms remain unresolved.
- ETF issuer pages: proxy/context only for metadata such as inception dates,
  expense ratios, distributions, holdings, objectives, and index context, not
  primary historical price data.
- FRED: proxy/context only for cash/T-bill/risk-free comparison review, with
  `TB3MS` and `DGS3MO` carried forward as candidate series only.
- Broker historical data: context only, not the default project source.

The sweep records ETF universe documentation notes for broad U.S. equity ETFs,
broad international equity ETFs, broad bond ETFs, broad commodity/gold ETFs,
and cash/T-bill proxy candidates. No ETF universe, ticker list, asset-class
mix, issuer set, inclusion rule, exclusion rule, inception rule,
inactive-fund policy, metadata source, benchmark, or cash proxy is approved.

The direct follow-up backlog carries forward adjusted-close methodology,
total-return versus price-plus-dividend assumptions, dividend/reinvestment
treatment, split/corporate-action handling, correction/revision policies,
point-in-time/as-of semantics, local archival permission, private repo
permission, derived-stat publication permission, API rate limits, long-term
reproducibility, and terms/license review.

Recommended routing after the sweep is to keep Stooq and Yahoo Finance /
yfinance in the candidate source queue for further docs-only review; keep
Nasdaq Data Link and Alpha Vantage as secondary/check candidates only; keep
ETF issuer pages as metadata/context only; keep FRED as a cash/risk-free proxy
candidate only; keep broker historical data as context only; and approve no
source. The next docs-only gate should be methodology-only moving-average
review, no-lookahead/as-of review, or ETF universe shortlist boundary.

This phase does not perform or authorize source approval, data approval, ETF
universe approval, benchmark approval, cash proxy approval, methodology
approval, moving-average parameter approval, data acquisition, data ingestion,
schema/code/notebooks/scripts, backtesting, reproduction, strategy
implementation, evaluator or signal implementation, signal computation,
signal scoring/ranking/direction/confidence/actionability, validated
artifacts, validated signal definitions, new contract types, production
thresholds, profitability claims, implementation-readiness claims,
production-readiness claims, trading implications, or broker, OMS, runtime,
scheduler, persistence, portfolio, ledger, reconciliation, Alpaca, ML, or LLM
trading-path behavior.

Remaining blockers include no `ValidatedResearchArtifact`, no
`ValidatedSignalDefinition`, no approved ETF universe, no selected/approved
data source, no approved benchmark/cash proxy, no acquired data, no
project-local deterministic reproduction, no no-lookahead audit, no production
threshold/config provenance, no implementation-scope approval, no evaluator
tests, no approved methodology, no approved moving-average parameters, no
approved data license/offline-use path, no approved local snapshot/versioning
policy, no total-return versus price-return comparison decision, no
dividend/reinvestment treatment, no corporate-action handling policy, no
correction/revision policy, no point-in-time/as-of policy, no source-specific
local archival/private-repo/derived-stat publication permission, no
transaction cost/friction review, no result-review template, no
promotion/rejection decision, and no trading implication or production
threshold.

## Phase 33 Step 5 Broad ETF Methodology and No-Lookahead Review Boundary

Phase 33 Step 5 is documentation-only. It adds:

```text
docs/design/phase33_broad_etf_methodology_no_lookahead_review_boundary.md
```

It also updates research-track navigation/checkpoint context only. The
boundary defines methodology-review and no-lookahead/as-of requirements for
the broad-ETF simple moving-average candidate. It does not approve
methodology, parameters, data, an ETF universe, a benchmark, a cash proxy,
reproduction, validation, implementation, or trading use.

The candidate remains an easier-data research candidate for review only. It is
not validated, implemented, trading-ready, production-ready, or actionable.

The methodology-review scope requires future review of the moving-average
trend-following concept, price-only versus total-return inputs, daily versus
monthly evaluation cadence, signal observation date versus action date,
cash/benchmark comparison rules, cost/friction assumptions, parameter
discipline, performance-driven parameter-selection safeguards, and
anti-cherry-picking controls for ETF universe construction.

The no-lookahead/as-of boundary requires future protocols to use only prices
available as of the decision timestamp, treat adjusted close and corporate
action data carefully, respect ETF inception and first usable observation
dates, align benchmark/cash proxy data by availability date and frequency,
define universe membership before result inspection, avoid same-day
close-to-close assumptions unless later justified, lag action timing after
signal observation, and keep normal `python -m pytest` offline and
credential-free.

The methodology evidence standards require source references, cadence
rationale, parameter rationale, comparison target, non-claims, limitations,
sensitivity/robustness expectations, OOS or holdout expectations where
applicable, and an explanation of suitability for deterministic research
workflow.

Required non-claims include no profitability, live or paper trading readiness,
production threshold validity, strategy generalization,
`ValidatedResearchArtifact` eligibility, `ValidatedSignalDefinition`
eligibility, or implementation approval.

Step 5 ties back to Step 4 by preserving Stooq and Yahoo Finance / yfinance as
source-review candidates only, Nasdaq Data Link and Alpha Vantage as
secondary/check candidates only, ETF issuer pages as metadata/context only,
FRED as a cash/risk-free proxy candidate only, and broker historical data as
context only. No source is approved.

The recommended next docs-only gate is an ETF universe shortlist boundary.
Benchmark/cash proxy shortlist review and moving-average evidence source
packaging remain possible docs-only gates. A reproduction protocol boundary
should wait until data, universe, and benchmark/cash proxy are later approved.

This phase does not perform or authorize methodology approval, moving-average
parameter approval, data approval, ETF universe approval, benchmark approval,
cash proxy approval, data acquisition, data ingestion, schema/code/notebooks/scripts,
backtesting, reproduction, strategy implementation, evaluator or signal
implementation, signal computation, signal scoring/ranking/direction/confidence/actionability,
validated artifacts, validated signal definitions, new contract types,
production thresholds, profitability claims, implementation-readiness claims,
production-readiness claims, trading implications, or broker, OMS, runtime,
scheduler, persistence, portfolio, ledger, reconciliation, Alpaca, ML, or LLM
trading-path behavior.

Remaining blockers include no `ValidatedResearchArtifact`, no
`ValidatedSignalDefinition`, no approved ETF universe, no selected/approved
data source, no approved benchmark/cash proxy, no approved methodology or
parameters, no acquired data, no project-local deterministic reproduction, no
no-lookahead audit, no production threshold/config provenance, no
implementation-scope approval, no evaluator tests, no data license or
offline-use approval, no local snapshot/versioning policy, no point-in-time
policy, no cost/friction assumptions, no result-review template, no
promotion/rejection decision, and no trading implication or production
threshold.

## Phase 33 Step 6 Broad ETF Universe and Benchmark/Cash Proxy Shortlist Boundary

Phase 33 Step 6 is documentation-only. It adds:

```text
docs/design/phase33_broad_etf_universe_benchmark_shortlist_boundary.md
```

It also updates research-track navigation/checkpoint context only. The
boundary defines non-approving shortlists for ETF universe candidates and
benchmark/cash proxy candidates for the broad-ETF simple moving-average
candidate. It does not approve an ETF universe, benchmark, cash proxy, data
source, methodology, reproduction, validation, signal definition, evaluator,
implementation, or trading use.

The candidate remains an easier-data research candidate for review only. It is
not validated, implemented, trading-ready, production-ready, or actionable.

The ETF universe shortlist principles require broad, liquid, simple ETFs only;
avoid thematic, niche, leveraged, inverse, thinly traded, complex, or
performance-selected exposures; define asset-class buckets before result
inspection; respect inception/listing dates and first usable observations;
preserve symbol identity; record expense ratio and index tracked where
available; record survivorship, closure, merger, ticker-change, and delisting
caveats; and prefer instruments with public issuer documentation.

The candidate buckets are broad U.S. equity, broad international developed
equity, broad emerging-market equity, broad U.S. aggregate bond,
long-duration Treasury or Treasury bond exposure, optional broad commodity or
gold exposure only if source quality and methodology caveats are acceptable,
and cash/T-bill proxy handled separately.

The candidate examples are `SPY` / `IVV` / `VOO` for broad U.S. equity,
`EFA` / `VEA` for developed international equity, `EEM` / `VWO` for
emerging-market equity, `AGG` / `BND` for aggregate bond exposure, `TLT` /
`IEF` for Treasury-duration exposure, and `GLD` / `IAU` or broad commodity
ETF/ETN candidates only if source quality and methodology caveats are
acceptable. All examples are candidates only and are not approved final
tickers or selected based on known performance.

The benchmark/cash proxy shortlist records the buy-and-hold version of a later
selected ETF universe, a broad U.S. equity benchmark candidate, FRED T-bill or
cash-rate candidates such as `TB3MS` or `DGS3MO`, and a zero-return cash
placeholder only as a last-resort methodology placeholder. No benchmark, cash
proxy, risk-free proxy, return convention, or comparison target is approved.

Any future benchmark/cash proxy proposal must document date alignment,
frequency alignment, availability-date/as-of assumptions, monthly versus daily
rate treatment, conversion assumptions if later needed, total-return versus
price-return caveats, cash proxy limitations, unequal histories, and deferred
transaction-cost/friction assumptions.

The rejection criteria defer or reject candidates when inception history is
too short, symbol identity is unstable or ambiguous, source quality is unclear,
corporate-action/dividend treatment cannot be documented, the candidate is
thematic/niche or performance-selected, benchmark frequency cannot align with
candidate data, cash proxy assumptions cannot be stated, or the route
encourages overclaiming.

Step 6 ties back to Step 4 and Step 5. Stooq and Yahoo Finance / yfinance
remain source-review candidates only; Nasdaq Data Link and Alpha Vantage
remain secondary/check candidates only; ETF issuer pages remain
metadata/context only; FRED remains a cash/risk-free proxy candidate only; and
no source is approved.

The recommended next docs-only gate is a data-source terms/license review
boundary, with a moving-average evidence source package as an acceptable
alternate. A reproduction protocol boundary should wait until source,
universe, benchmark, and cash proxy choices are later approved. A result-review
template should wait until a protocol is later approved.

This phase does not perform or authorize universe approval, benchmark
approval, cash proxy approval, source approval, methodology approval,
moving-average parameter approval, data acquisition, data ingestion,
schema/code/notebooks/scripts, backtesting, reproduction, strategy
implementation, evaluator or signal implementation, signal computation,
signal scoring/ranking/direction/confidence/actionability, validated
artifacts, validated signal definitions, new contract types, production
thresholds, profitability claims, implementation-readiness claims,
production-readiness claims, trading implications, or broker, OMS, runtime,
scheduler, persistence, portfolio, ledger, reconciliation, Alpaca, ML, or LLM
trading-path behavior.

Remaining blockers include no `ValidatedResearchArtifact`, no
`ValidatedSignalDefinition`, no approved ETF universe, no selected/approved
data source, no approved benchmark/cash proxy, no approved methodology or
parameters, no acquired data, no project-local deterministic reproduction, no
no-lookahead audit, no production threshold/config provenance, no
implementation-scope approval, no evaluator tests, no data license or
offline-use approval, no local snapshot/versioning policy, no total-return
versus price-return decision, no dividend/reinvestment treatment, no
corporate-action handling policy, no correction/revision policy, no
point-in-time/as-of policy, no inactive-fund or ticker-change policy, no
benchmark/cash-proxy frequency alignment rule, no cash-rate conversion rule,
no cost/friction assumptions, no result-review template, no promotion/rejection
decision, and no trading implication or production threshold.

## Phase 33 Step 7 Broad ETF Data-Source Terms / License Review Boundary

Phase 33 Step 7 is documentation-only. It adds:

```text
docs/design/phase33_broad_etf_data_source_terms_license_review_boundary.md
```

It also updates research-track navigation/checkpoint context only. The
boundary reviews public terms, license, and offline-use constraints for
candidate broad-ETF data and metadata sources. It does not provide legal
advice and does not approve data, a data source, an ETF universe, benchmark,
cash proxy, methodology, reproduction, validation, signal definition,
evaluator, implementation, or trading use.

The reviewed source categories are Stooq, Yahoo Finance / yfinance / Yahoo
API terms, Nasdaq Data Link, Alpha Vantage, FRED, ETF issuer pages such as
iShares, Vanguard, SPDR, and Invesco, and broker historical data as context
only.

The boundary records terms-risk labels only: low apparent terms risk pending
final review, moderate terms uncertainty, high terms uncertainty, likely
unsuitable for project-local archival, and context only. Stooq is labeled
moderate terms uncertainty; Yahoo Finance / yfinance / Yahoo API terms are
labeled high terms uncertainty; Nasdaq Data Link and Alpha Vantage are labeled
moderate terms uncertainty and secondary/check only; FRED is labeled low
apparent terms risk pending final review for cash/risk-free proxy review only;
ETF issuer pages and broker historical data remain context only.

Source-specific cautions include that Stooq terms reviewed do not explicitly
allow local archival/private-repo use; Yahoo/yfinance has personal-use,
automation, storage, and redistribution uncertainty; Nasdaq Data Link terms may
vary by dataset; Alpha Vantage rate limits and terms must be respected; FRED
requires API, series-owner, archival, and citation review; ETF issuer pages
are metadata/context only; and broker data remains context only because
credentials, subscriptions, terms, and runtime access conflict with default
offline testing if used directly.

The required conclusions are that no source is approved, any future approved
source must permit deterministic local snapshotting or have an explicit
fixture/storage policy that avoids normal pytest network or credential access,
future derived-stat publication must avoid raw-data redistribution and follow
source terms, and normal `python -m pytest` must remain offline and
credential-free.

The recommended next docs-only gate is a final source shortlist decision
boundary. Acceptable later gates include a broad ETF evidence/source package
for moving-average literature, a data storage/fixture policy boundary only
after source terms are acceptable, and a reproduction protocol boundary only
after source, universe, benchmark, and data policy approval.

This phase does not perform or authorize legal advice, source approval,
universe approval, benchmark approval, cash proxy approval, methodology
approval, moving-average parameter approval, data acquisition, data ingestion,
schema/code/notebooks/scripts, backtesting, reproduction, strategy
implementation, evaluator or signal implementation, signal computation,
validated artifacts, validated signal definitions, new contract types,
production thresholds, profitability claims, implementation-readiness claims,
production-readiness claims, trading implications, or broker, OMS, runtime,
scheduler, persistence, portfolio, ledger, reconciliation, Alpaca, ML, or LLM
trading-path behavior.

Remaining blockers include no `ValidatedResearchArtifact`, no
`ValidatedSignalDefinition`, no approved ETF universe, no selected/approved
data source, no approved benchmark/cash proxy, no approved methodology or
parameters, no approved data storage/fixture policy, no acquired data, no
project-local deterministic reproduction, no no-lookahead audit, no production
threshold/config provenance, no implementation-scope approval, no evaluator
tests, no approved data license/offline-use path, no approved local
snapshot/versioning policy, no approved redistribution or derived-stat
publication policy, no approved API rate-limit/access policy, no result-review
template, no promotion/rejection decision, and no trading implication or
production threshold.

## Phase 33 Step 8 Broad ETF Final Source Shortlist Decision Boundary

Phase 33 Step 8 is documentation-only. It adds:

```text
docs/design/phase33_broad_etf_final_source_shortlist_decision_boundary.md
```

It also updates research-track navigation/checkpoint context only. The
boundary records a final non-approving source shortlist decision for future
broad-ETF simple moving-average planning. It does not approve sources, data,
an ETF universe, benchmark, cash proxy, methodology, reproduction, validation,
signal definition, evaluator, implementation, or trading use.

The decision vocabulary is limited to primary planning candidate,
secondary/check candidate, metadata/context only, cash/risk-free proxy
candidate, not default source, and unresolved / requires further review.

The candidate routing keeps Stooq as a possible primary planning candidate for
ETF price data, but not approved, with terms and adjusted-data questions still
open. Yahoo Finance / yfinance / Yahoo API terms remain secondary/check or
unresolved due to high terms uncertainty and are not a default source. Nasdaq
Data Link and Alpha Vantage remain secondary/check only. FRED remains a
cash/risk-free proxy candidate only, not approved, with fixture/storage,
citation, archival, revision, and frequency-alignment handling still required.
ETF issuer pages remain metadata/context only. Broker historical data remains
context only and not a default source.

The rationale ties the routing to the Phase 33 Step 4 public-source
documentation sweep, Phase 33 Step 6 universe/benchmark shortlist, Phase 33
Step 7 terms/license review, offline reproducibility requirements, terms
uncertainty, adjusted-price and total-return uncertainty, and normal
`python -m pytest` remaining offline and credential-free.

The non-approval statement records that no source is approved, no data may be
acquired, no dataset may be added to the repository, no source may be used in
normal pytest, and no candidate source may be used before a later explicit
data storage/fixture policy and/or source approval phase.

Remaining source-specific blockers include Stooq adjustment/dividend/revision
and license clarity; Yahoo/yfinance personal-use, automation, storage, and
redistribution clarity; FRED archival, API, citation, revision, release, and
frequency alignment; Nasdaq/Alpha Vantage dataset-specific terms and rate
limits; ETF issuer metadata reuse and historical metadata limits; and broker
data credential/runtime/terms conflicts with offline default tests.

The recommended next docs-only gate is a data storage/fixture policy boundary.
A moving-average evidence/source package remains an alternate if methodology
evidence should be strengthened first. A reproduction protocol boundary should
wait until source, universe, benchmark, cash proxy, and data storage/fixture
policy choices are later approved by explicit phases.

This phase does not perform or authorize legal advice, source approval,
universe approval, benchmark approval, cash proxy approval, methodology
approval, moving-average parameter approval, data acquisition, ingestion,
schema/code/notebooks/scripts, backtesting, reproduction, strategy
implementation, evaluator or signal implementation, signal computation,
validated artifacts, validated signal definitions, new contract types,
production thresholds, profitability claims, implementation-readiness claims,
production-readiness claims, trading implications, or broker, OMS, runtime,
scheduler, persistence, portfolio, ledger, reconciliation, Alpaca, ML, or LLM
trading-path behavior.

Remaining blockers include no `ValidatedResearchArtifact`, no
`ValidatedSignalDefinition`, no approved ETF universe, no selected/approved
data source, no approved benchmark/cash proxy, no approved methodology or
parameters, no approved data storage/fixture policy, no acquired data, no
project-local deterministic reproduction, no no-lookahead audit, no production
threshold/config provenance, no implementation-scope approval, no evaluator
tests, no approved data license/offline-use path, no approved local
snapshot/versioning policy, no approved source-specific archival/private-repo
policy, no approved redistribution or derived-stat publication policy, no
approved API rate-limit/access policy, no approved adjusted-price semantics,
no approved total-return versus price-return decision, no approved
dividend/reinvestment treatment, no approved corporate-action handling policy,
no approved correction/revision policy, no approved point-in-time/as-of policy,
no approved inactive-fund or ticker-change policy, no approved
benchmark/cash-proxy frequency alignment rule, no approved cash-rate
conversion rule, no cost/friction assumptions, no result-review template, no
promotion/rejection decision, and no trading implication or production
threshold.

## Phase 34 Step 1 External Research Integration Boundary

Phase 34 Step 1 is documentation-only. It adds:

```text
docs/design/phase34_external_research_integration_boundary.md
```

It also updates research-track navigation/checkpoint context only. The
boundary defines how external research tools and outputs may support the
project without becoming trusted production dependencies, source-of-truth
artifacts, normal pytest inputs, or trading-path behavior.

The tools covered include Perplexity, Claude/Gemini or other LLM reviewers,
Codex or other local implementation/documentation agents, QuantConnect,
vectorbt, notebooks, vendor/public data sources, external academic or
practitioner research, spreadsheets, CSV scratchpads, ad hoc analysis files,
and similar scout, review, sandbox, or prototype outputs.

Allowed uses are advisory only: scout research, source discovery, literature
review, methodology critique, contradiction finding, code review suggestions,
test-matrix suggestions, risk/assumption/edge-case discovery, benchmark or
context comparison, prototype experiments outside the deterministic core,
drafting docs/proposals, and identifying licensing, reproducibility,
no-lookahead, data, and overclaiming concerns.

Forbidden uses include direct production dependency, trading hot-path
dependency, live/paper order generation, direct signal/threshold approval,
direct `ValidatedResearchArtifact` or `ValidatedSignalDefinition` creation,
normal pytest runtime calls, credential/network dependency in normal pytest,
direct portfolio/broker/order/OMS/risk mutation, treating notebooks or hosted
results as validation without repo reproduction, and treating LLM output as
disposition authority.

The promotion path requires external output to be captured as proposal/scout
input, normalized into docs with evidence/inference/uncertainty separated,
reviewed for source terms and data feasibility, planned for deterministic
local reproduction, blocked from repository data entry until fixture/storage
policy approval, implemented only in a later scoped phase, enforced by tests,
and reviewed with limitations and non-claims before any future promotion
discussion.

Tool-specific boundaries keep Perplexity as scout research only,
Claude/Gemini as review/critique only, Codex as a scoped local
implementation/documentation agent subject to tests and review, QuantConnect
as external sandbox/backtest reference only, vectorbt as potential research
or prototyping engine only, notebooks as exploratory only, and vendor/public
data as candidate input requiring terms, storage, provenance, citation,
versioning, and offline policy before use.

The repository boundary keeps speculative or external-agent outputs in
`docs/proposals` only when such a route is explicitly needed, reviewed phase
boundaries in `docs/design`, `src` changes behind later scoped
implementation approval, tests only for deterministic enforcement in later
scoped phases, and data files out of the repository unless a future
storage/fixture policy approves them. No `docs/proposals` files were created
because the current repository has no `docs/proposals` directory and no
proposal artifact is needed for this boundary.

The recommended next docs-only gate is an external research artifact intake
checklist. It should define how scout outputs, LLM reviews, hosted backtest
notes, notebooks, spreadsheets, vendor/public data notes, citations, manual
observations, and prototype summaries are captured while preserving advisory
status, uncertainty labels, source verification requirements, non-claims, and
the normal pytest rule.

This phase does not perform or authorize implementation, dependency changes,
notebooks, scripts, data acquisition, data ingestion, dataset addition,
schema/code/contract changes, backtests, reproduction, QuantConnect
integration, vectorbt integration, broker/runtime/scheduler/persistence
integration, LLM runtime integration, evaluator or signal implementation,
signal computation, scoring/ranking/direction/confidence/actionability,
validated artifacts, validated signal definitions, production thresholds,
profitability claims, implementation-readiness claims, production-readiness
claims, trading implications, or broker, OMS, runtime, scheduler,
persistence, portfolio, Alpaca, ML, or LLM trading-path behavior.

Remaining blockers include no `ValidatedResearchArtifact` from external
tools, no `ValidatedSignalDefinition` from external tools, no approved
external research integration, no approved data storage/fixture policy, no
approved source/universe/benchmark/cash proxy for the Phase 33 broad-ETF
candidate, no approved methodology or parameters, no approved data
acquisition or ingestion route, no project-local deterministic reproduction,
no no-lookahead audit, no implementation-scope approval, no evaluator tests,
no approved repository policy for notebooks/scratch artifacts/hosted exports,
no result-review template, no promotion/rejection decision, and no trading
implication or production threshold.

## Phase 34 Step 2 External Research Artifact Intake Checklist

Phase 34 Step 2 is documentation-only. It adds:

```text
docs/design/phase34_external_research_artifact_intake_checklist.md
```

It also updates research-track navigation/checkpoint context only. The
checklist defines how external research artifacts enter the project trail
before they can influence decisions while preserving Git, reviewed docs, and
deterministic tests as the trust boundary.

The covered artifact types are Perplexity reports, Claude/Gemini reviews,
Codex implementation reports, QuantConnect results, vectorbt experiments,
notebooks, vendor/public data documentation, academic/practitioner papers,
spreadsheets and ad hoc analysis files, screenshots, and manual observations.

Required intake metadata includes artifact title, source/tool, date received
or reviewed, author/tool identity, prompt or query when applicable, reviewed
files/links, source type, claims made, evidence cited, assumptions,
uncertainty, proposed use, and allowed status. Allowed status values are
scout, critique, context, candidate evidence, rejected, and needs
verification.

Evidence classification labels are primary source, secondary source,
external-tool inference, local repo evidence, manual observation, unverified
claim, and rejected / unsupported claim. The checklist keeps LLM-generated
text, hosted backtest output, notebook output, screenshots, and spreadsheet
conclusions outside primary evidence unless the underlying source material is
primary and separately reviewed.

Required review questions ask what claim is being made, whether primary
evidence supports it, whether it conflicts with repo docs, whether current
source verification is needed, whether data/licensing/performance/methodology
or implementation claims are involved, whether deterministic local
reproduction is required, whether lookahead/survivorship/data-snooping/license
risk is introduced, whether code/dependency/network/credential/broker/runtime
or trading-path behavior is implied, and what is explicitly out of scope.

Routing outcomes are reject, keep as scout/context only, normalize into
`docs/design`, place in `docs/proposals` only if that speculative route exists
or is explicitly created later, require primary-source verification, require
terms/license review, require deterministic reproduction plan, require human
owner decision, or mark eligible for a later scoped phase.

Promotion constraints state that external artifacts cannot directly create or
approve `ValidatedResearchArtifact`, `ValidatedSignalDefinition`,
signal/evaluator code, production threshold/config, trading action,
broker/runtime behavior, normal pytest dependency, or source/data approval.
They also cannot directly approve notebooks as canonical, vendor/public data
as project data, hosted backtest results as reproduced, or LLM output as
project authority.

Repository placement keeps reviewed phase decisions in `docs/design`,
speculative external-agent outputs in `docs/proposals` only if that directory
exists or is explicitly created later, concise milestones in
`project_checkpoint.md`, raw vendor data and notebook outputs out of the repo
without storage/fixture policy, and `src` changes behind later scoped
implementation approval.

The reusable checklist template captures artifact metadata, evidence labels,
review questions, routing outcome, follow-up, explicit non-goals, owner,
normal pytest impact, and repository placement. Completing the template records
intake only; it does not validate, approve, promote, implement, reproduce, or
make an artifact actionable.

The recommended next docs-only gate is a notebook/prototype policy boundary.
That gate should define how notebooks, vectorbt prototypes, spreadsheets, and
other exploratory artifacts may be referenced or summarized without becoming
canonical repo artifacts, dependencies, datasets, normal pytest inputs,
validated research, signal definitions, or trading-path behavior.

This phase does not perform or authorize implementation, dependencies,
notebooks, data acquisition, data ingestion, schema/code/scripts, backtests,
reproduction, QuantConnect/vectorbt integration, LLM runtime integration,
evaluator or signal implementation, signal computation,
scoring/ranking/direction/confidence/actionability, validated artifacts,
validated signal definitions, production thresholds, source approval, data
approval, profitability claims, or trading implications.

Remaining blockers include no `ValidatedResearchArtifact` from external
artifacts, no `ValidatedSignalDefinition` from external artifacts, no approved
external research integration, no approved data storage/fixture policy, no
approved Phase 33 source/universe/benchmark/cash proxy, no project-local
deterministic reproduction, no no-lookahead audit, no implementation-scope
approval, no evaluator tests, no approved notebook/prototype policy, no
approved terms/license route for external data or hosted outputs, no approved
source/data approval route from external artifacts, no approved result-review
template for reproduced outputs, no promotion/rejection decision for any
specific external artifact, and no trading implication or production
threshold.

## Phase 34 Step 3 Notebook / Prototype Policy Boundary

Phase 34 Step 3 is documentation-only. It adds:

```text
docs/design/phase34_notebook_prototype_policy_boundary.md
```

It also updates research-track navigation/checkpoint context only. The policy
defines how notebooks, prototype scripts, vectorbt experiments, QuantConnect
outputs, spreadsheets, CSV extracts, charts, external platform reports, and
copied snippets may support research without becoming trusted project
artifacts, deterministic source of truth, production dependencies, normal
pytest inputs, or trading-path behavior.

Allowed uses are exploratory calculations, hypothesis sketching,
visualization, sanity checks, API or data-source learning outside the
deterministic core, performance-shape exploration with explicit non-claims,
generating questions for later deterministic phases, and drafting docs or
proposals. These uses create context for review only.

Forbidden uses include production source of truth, direct trading signal
source, direct threshold source, direct validation evidence, direct source/data
approval, direct normal pytest dependency, direct broker/runtime/OMS
dependency, direct portfolio mutation, direct artifact or signal-definition
creation, replacement for deterministic local reproduction, and hiding manual
edits or undocumented data cleaning.

Required metadata for future exploratory artifacts includes purpose, date,
author/tool, data source, data snapshot or retrieval date, assumptions,
dependencies/tools used, whether network or credentials were involved,
limitations, non-claims, what must be reproduced locally before trust, and
recommended routing.

The promotion path requires Phase 34 intake capture, normalized reviewed docs,
source/data terms review, approved fixture/storage policy, deterministic local
reproduction planning, later scoped implementation approval, deterministic
tests, and a result-review template recording limits and non-claims. No
notebook, script, spreadsheet, vectorbt run, QuantConnect report, chart, LLM
snippet, website snippet, or hosted result can skip this path.

Repository placement keeps reviewed policy in `docs/design`, reserves
`docs/proposals` for later explicitly scoped speculative summaries, keeps raw
data and generated outputs out of the repo until storage/fixture policy is
approved, and keeps `src` off-limits until later implementation approval.

The vectorbt boundary states that vectorbt may be considered for research
prototyping only. It is not production infrastructure, cannot be in the
trading hot path, cannot validate a signal without project-approved
deterministic reproduction, and is not added as a dependency in this phase.

The QuantConnect boundary states that QuantConnect may be used only as an
external sandbox or reference. QuantConnect results are not source of truth,
screenshots and backtest reports are external artifacts, useful findings must
be reproduced locally before trust, and no QuantConnect integration is added.

Normal `python -m pytest` remains offline, credential-free, deterministic,
free of network, credentials, SDK/platform calls, notebook/prototype runtime
dependencies, data acquisition, data ingestion, broker/runtime/OMS behavior,
vectorbt, QuantConnect, ML, LLM runtime, and trading-path behavior. Any future
integration tests must be explicitly gated and skipped by default.

The recommended next docs-only gate is to return to the Phase 33 data
storage/fixture policy boundary.

This phase does not perform or authorize implementation, dependencies,
notebooks, scripts, data acquisition, data ingestion, schema/code, backtests,
reproduction, vectorbt integration, QuantConnect integration, LLM runtime
integration, evaluator or signal implementation, signal computation,
scoring/ranking/direction/confidence/actionability, validated artifacts,
validated signal definitions, production thresholds, profitability claims, or
trading implications.

Remaining blockers include no approved notebook/prototype integration, no
approved vectorbt integration, no approved QuantConnect integration, no
approved data storage/fixture policy, no approved Phase 33
source/universe/benchmark/cash proxy, no project-local deterministic
reproduction, no no-lookahead audit, no implementation-scope approval, no
evaluator tests, no approved source/data approval route from exploratory
artifacts, no approved terms/license route for external data or hosted
outputs, no approved result-review template for reproduced outputs, no
promotion/rejection decision for any specific exploratory artifact, and no
trading implication or production threshold.

## Phase 33 Step 9 Broad ETF Data Storage / Fixture Policy Boundary

Phase 33 Step 9 is documentation-only. It adds:

```text
docs/design/phase33_broad_etf_data_storage_fixture_policy_boundary.md
```

It also updates research-track navigation/checkpoint context only. The
boundary defines future storage and fixture requirements for broad-ETF
research data while preserving normal `python -m pytest` as offline,
credential-free, deterministic, and safe.

The covered categories are raw third-party price data, downloaded CSV/API
snapshots, ETF issuer metadata, FRED cash/risk-free series, manually entered
metadata, tiny synthetic fixtures, tiny derived fixtures, checksums/manifests,
provenance records, charts/plots/results, and notebooks/prototype outputs.

Storage options are compared without approval: no raw third-party data in the
repo, local-only ignored data directories, small synthetic fixtures, small
derived fixtures only if redistribution-safe, checksum/provenance manifests,
external archival, and encrypted/private storage outside normal pytest.

Future fixtures must be deterministic, redistribution-safe, small,
credential-free, network-free, free of prohibited raw vendor data, and paired
with provenance or synthetic-generation explanations. They must not imply
strategy validation, production readiness, implementation readiness, or trading
readiness. No broad-ETF fixture is approved in this phase.

Future provenance or manifest records must include source, retrieval date,
license/terms review status, ticker/universe, date range, fields, adjustment
assumptions, checksum/hash, storage location, redistribution status, pytest
eligibility, limitations, and non-claims.

Local-only data may exist outside the repo only after future approval. It must
be ignored by Git, excluded from normal pytest, documented by provenance and
terms status, and never treated as validated evidence or a hidden dependency.
Credentials and API keys must never be required for normal pytest.

The boundary ties back to Phase 34 by keeping external research artifacts,
notebooks, vectorbt prototypes, QuantConnect outputs, spreadsheets, CSV
extracts, charts, external reports, and copied snippets exploratory only.
Those outputs cannot become canonical data or fixtures without this policy and
later scoped approval.

Terms/license constraints remain non-approving: Stooq has moderate terms
uncertainty, Yahoo/yfinance has high terms uncertainty, Nasdaq Data Link and
Alpha Vantage are secondary/check only, FRED is a cash/risk-free proxy
candidate only with low apparent terms risk pending final review, issuer pages
are metadata/context only, broker historical data is context only, and no
source is approved.

Recommended later docs-only gates are a moving-average evidence/source
package, a broad ETF source approval boundary only after refreshed source
terms and storage constraints are reviewed, a fixture policy approval boundary,
and a reproduction protocol boundary only after source, universe,
benchmark/cash proxy, methodology, and data policy choices are approved.

This phase does not approve or perform source selection, universe selection,
benchmark/cash proxy selection, methodology selection, parameter selection,
data acquisition, download, ingestion, data files, fixtures, schemas, code,
notebooks, scripts, backtests, reproduction, evaluator/signal implementation,
validated artifacts, validated signal definitions, production thresholds, or
trading implications.

Remaining blockers include no `ValidatedResearchArtifact`, no
`ValidatedSignalDefinition`, no approved ETF universe, no selected/approved
data source, no approved benchmark/cash proxy, no approved methodology or
parameters, no approved final data storage/fixture policy, no acquired data,
no project-local deterministic reproduction, no no-lookahead audit, no
production threshold/config provenance, no implementation-scope approval, no
evaluator tests, no approved pytest-eligible fixture set, and no trading
implication or production threshold.

## Phase 33 Step 10 Broad ETF Moving-Average Evidence Source Package

Phase 33 Step 10 is documentation-only. It adds:

```text
docs/design/phase33_broad_etf_moving_average_evidence_source_package.md
```

It also updates research-track navigation/checkpoint context only. The package
identifies evidence categories to collect for the broad-ETF simple
moving-average candidate before any methodology review, reproduction protocol,
validation route, implementation planning, signal-definition discussion, or
evaluator work.

Evidence categories include academic papers on moving-average
trend-following, practitioner references on time-series trend-following,
ETF-specific trend-following or tactical allocation references if available,
benchmark and buy-and-hold comparison references, transaction-cost and
friction references, data-adjustment and total-return caveat references,
no-lookahead and backtest-bias references, and robustness or
parameter-sensitivity references.

The package defines evidence-quality standards: primary sources are preferred,
secondary and practitioner sources must be labeled, blog or marketing content
is context only unless later reviewed, LLM summaries are not evidence, exact
claims require exact citations, claims must separate evidence, inference, and
uncertainty, and performance claims require reproducible data before trust.

The review questions cover the exact moving-average rule, studied universe,
date range, frequency, return construction, dividends, splits, corporate
actions, benchmark, costs/frictions, out-of-sample evidence, robustness,
parameter choice, lookahead/survivorship/data-snooping risks, limitations, and
what can or cannot transfer to broad ETFs.

The starter evidence intake table records placeholder source IDs for academic,
practitioner, ETF-specific, benchmark, friction, data-adjustment, bias-control,
and robustness references. Those rows are collection targets only; they are
not reviewed evidence and not approval.

This phase does not approve evidence, methodology, parameters, source data, an
ETF universe, benchmark, cash proxy, data acquisition, data files, fixtures,
reproduction, validation, signal definitions, evaluator behavior,
implementation, production thresholds, or trading implications.

Remaining blockers include no `ValidatedResearchArtifact`, no
`ValidatedSignalDefinition`, no approved ETF universe, no selected/approved
data source, no approved benchmark/cash proxy, no approved methodology or
parameters, no approved final data storage/fixture policy, no approved
evidence review, no acquired data, no project-local deterministic
reproduction, no no-lookahead audit, no production threshold/config
provenance, no implementation-scope approval, no evaluator tests, no
robustness or parameter-sensitivity review, no result-review template, and no
trading implication or production threshold.

## Phase 33 Step 11 Broad ETF Moving-Average Evidence Intake Plan

Phase 33 Step 11 is documentation-only. It adds:

```text
docs/design/phase33_broad_etf_moving_average_evidence_intake_plan.md
```

It also updates research-track navigation/checkpoint context only. The plan
defines how future moving-average evidence should be collected, cited,
classified, summarized, reviewed, downgraded, and dispositioned before any
formal evidence review occurs.

Intake scope covers academic moving-average papers, practitioner
trend-following references, ETF-specific references, benchmark/buy-and-hold
references, transaction-cost and friction references, data-adjustment and
total-return caveat references, no-lookahead and backtest-bias references, and
robustness or parameter-sensitivity references.

Source priority is primary academic papers or official publications, official
methodology documentation, reputable practitioner research, official data or
source documentation, secondary summaries, blogs or marketing as context only,
and LLM summaries never as evidence.

The intake workflow records citation details, classifies source type,
summarizes exact claims, separates evidence from inference and uncertainty,
captures methodology/universe/period/frequency/benchmark details, records bias
controls and costs/frictions, assesses broad-ETF transferability, preserves
limitations and non-claims, and assigns a cautious disposition.

Allowed dispositions are review candidate, methodology context,
benchmark/context, bias-control context, friction/cost context, rejected /
unsupported, requires primary-source verification, and eligible for later
formal review.

Rejection criteria cover missing primary citations, unsupported or vague
claims, performance claims without data/provenance, unclear universe/date
range/frequency, unaddressed lookahead/survivorship/data-snooping concerns,
cherry-picked parameters, marketing-only sources, implementation or trading
readiness implications, and conflicts with project constraints.

The recommended later review sequence is methodology/core moving-average
references, bias/no-lookahead references, ETF-specific or broad-market trend
references, benchmark/cash/friction references, then robustness and
parameter-sensitivity references.

The required intake table captures Source ID, Citation / reference, Source
type, Claim reviewed, Universe / data, Period / frequency, Methodology
relevance, Bias controls, Costs/frictions, ETF transferability, Limitations,
Disposition, and Follow-up needed.

The Phase 34 relationship keeps external research, notebooks, prototype
scripts, vectorbt experiments, QuantConnect outputs, spreadsheets, CSV
extracts, charts, copied snippets, and LLM outputs advisory unless normalized,
tied to traceable sources, checked against constraints, and later reproduced
through a scoped deterministic project-local protocol.

The recommended next docs-only gate is a first limited methodology evidence
review after specific candidate sources are collected externally and entered
through the intake plan. If sources are unavailable, the safer route is to
pause until candidate citations and links are collected.

This phase does not approve evidence, methodology, parameters, source data, an
ETF universe, benchmark, cash proxy, data acquisition, data files, fixtures,
reproduction, validation, signal definitions, evaluator behavior,
implementation, production thresholds, or trading implications.

Remaining blockers include no `ValidatedResearchArtifact`, no
`ValidatedSignalDefinition`, no approved evidence review, no approved
methodology or parameters, no approved ETF universe, no selected/approved data
source, no approved benchmark/cash proxy, no approved final data
storage/fixture policy, no acquired data, no project-local deterministic
reproduction, no no-lookahead audit, no production threshold/config
provenance, no implementation-scope approval, no evaluator tests, no
source-specific intake records, no collected primary evidence package, no
reviewed practitioner-source classification, no approved total-return versus
price-return decision, no approved dividend/reinvestment treatment, no
approved corporate-action handling policy, no approved correction/revision
policy, no approved point-in-time/as-of policy, no approved friction
assumptions, no robustness or parameter-sensitivity review, no result-review
template, no promotion/rejection decision, and no trading implication or
production threshold.

## Phase 33 Step 12 Broad ETF Evidence Source Collection Normalization

Phase 33 Step 12 is documentation-only. It adds:

```text
docs/design/phase33_broad_etf_evidence_source_collection_normalization.md
```

It also updates research-track navigation/checkpoint context only. The
normalization converts the externally supplied Perplexity moving-average
source collection into the project's intake trail while treating the report as
external scout material only.

The normalized groups cover academic/formal methodology candidates,
ETF-specific candidates, practitioner/tactical allocation candidates,
benchmark/cash/risk-metric candidates, friction/cost candidates,
bias/no-lookahead/backtest-bias candidates, context-only or weak sources, and
rejected or unsupported direct-evidence sources.

The intake table records source IDs, titles/citations, source types,
categories, discussed rules, universes, known period/frequency fields, claims
to verify later, evidence-quality labels, bias-control relevance,
cost/friction relevance, broad-ETF relevance, current dispositions, and
required follow-up. Rows are intake records only and do not approve any source
or claim.

The strongest later review candidates are `ETF-ACADEMIC-001`,
`MA-ACADEMIC-001`, `MA-ACADEMIC-002` / `MA-ACADEMIC-003`,
`MA-ACADEMIC-004`, `MA-ACADEMIC-005`, `MA-ACADEMIC-006`,
`MA-PRACT-001`, and selected benchmark/friction references only after exact
citations are identified. Inclusion means review candidate only, not evidence
approval.

Context-only sources such as ETFdb, ETFtrends, Schwab educational material,
ETFreplay, personal blogs, secondary summaries, and the Perplexity report text
itself may support terminology, examples, or source discovery only. They are
rejected for direct performance evidence unless later primary-source review
supports the exact claim.

Required follow-up before formal review includes obtaining or inspecting full
primary texts, verifying citations and authorship, extracting exact rule
definitions, universe, date range, frequency, benchmark, return treatment,
dividend/split/corporate-action handling, transaction-cost assumptions,
OOS/robustness/parameter-sensitivity treatment, lookahead/survivorship/data
snooping controls, broad-ETF transfer limits, limitations, and non-claims.

The evidence grading proposal includes high-priority formal review candidate,
review candidate, methodology context, bias-control context,
benchmark/friction context, context only, reject for direct evidence, and
requires primary-source verification.

The recommended next route is to pause until full primary texts are obtained
or inspectable for at least one to three high-priority candidates. The project
should not start a limited methodology evidence review from the Perplexity
summary alone.

This phase does not approve evidence, methodology, parameters, source data, an
ETF universe, benchmark, cash proxy, data acquisition, data files, fixtures,
reproduction, validation, signal definitions, evaluator behavior,
implementation, production thresholds, or trading implications.

Remaining blockers include no `ValidatedResearchArtifact`, no
`ValidatedSignalDefinition`, no approved evidence review, no approved
methodology or parameters, no approved ETF universe, no selected/approved data
source, no approved benchmark/cash proxy, no approved final data
storage/fixture policy, no acquired data, no project-local deterministic
reproduction, no no-lookahead audit, no production threshold/config
provenance, no implementation-scope approval, no evaluator tests, no
source-specific primary-text verification, no verified citation metadata for
the external source list, no reviewed practitioner-source classification, no
approved return-treatment or corporate-action handling decisions, no approved
friction assumptions, no robustness or parameter-sensitivity review, no
benchmark/cash/risk-metric review, no result-review template, no
promotion/rejection decision, and no trading implication or production
threshold.

## Phase 33 Step 13 Broad ETF Primary Evidence Text Intake Normalization

Phase 33 Step 13 is documentation-only. It adds:

```text
docs/design/phase33_broad_etf_primary_evidence_text_intake_normalization.md
```

It also updates research-track navigation/checkpoint context only. The
normalization records the second Perplexity source-gathering report as
external scout material under Phase 34 artifact-intake rules. The report is
not treated as evidence approval, source-of-truth material, methodology
validation, parameter approval, data approval, universe approval, benchmark
approval, reproduction approval, validation approval, implementation approval,
or trading approval.

The source status table covers `ETF-ACADEMIC-001`, `MA-PRACT-001`,
`MA-ACADEMIC-001 / unresolved`, related Zakamulin/SSRN-style candidates, and
the Perplexity report itself as `EXT-SCOUT-002`. Rows record reported primary
link type, cautious full-text availability status, citation verification
status, whether methodology/data/bias/cost details are available from primary
text, current status, follow-up, and conditional eligibility for later limited
formal review.

The preliminary readiness decision is conservative: pause until primary text
and citation verification is complete. Faber may be eligible later only if the
reported open PDF and citation metadata are verified. `ETF-ACADEMIC-001` may
be eligible later only if the reported SSRN working paper or official text is
accessible and citation metadata is verified. "Simple Market Timing with
Moving Averages" remains unresolved and not eligible until the exact intended
source is identified.

The document records that the Perplexity report contains mixed citation
quality and that some fields may cite secondary or unrelated pages. Exact
author/title/year/venue/DOI/SSRN/RePEc metadata must be verified from primary
pages before formal review, and source claims must be extracted from actual
primary text rather than the Perplexity summary.

Required follow-up before formal review includes verifying citation metadata,
inspecting full primary text, recording abstracts from primary sources only,
extracting exact moving-average rules, universe, period, frequency, benchmark,
cash proxy, return construction, dividend/corporate-action treatment,
costs/frictions, OOS/robustness/parameter-sensitivity treatment,
lookahead/survivorship/data-snooping controls, limitations, and non-claims.

This phase does not approve evidence, methodology, parameters, source data, an
ETF universe, benchmark, cash proxy, data acquisition, data files, PDFs,
fixtures, reproduction, validation, signal definitions, evaluator behavior,
implementation, production thresholds, or trading implications.

Remaining blockers include no `ValidatedResearchArtifact`, no
`ValidatedSignalDefinition`, no approved evidence review, no approved
methodology or parameters, no approved ETF universe, no selected/approved data
source, no approved benchmark/cash proxy, no approved final data
storage/fixture policy, no acquired data, no project-local deterministic
reproduction, no no-lookahead audit, no production threshold/config
provenance, no implementation-scope approval, no evaluator tests, no
source-specific primary-text verification, no verified citation metadata for
the second Perplexity source list, no resolved identity for "Simple Market
Timing with Moving Averages", no verified separation between related
Zakamulin/SSRN-style candidates and the unresolved `MA-ACADEMIC-001` label,
no reviewed practitioner-source classification, no approved return-treatment
or corporate-action handling decisions, no approved friction assumptions, no
robustness or parameter-sensitivity review, no benchmark/cash/risk-metric
review, no result-review template, no promotion/rejection decision, and no
trading implication or production threshold.

## Phase 33 Step 14 Broad ETF Primary Citation Verification Normalization

Phase 33 Step 14 is documentation-only. It adds:

```text
docs/design/phase33_broad_etf_primary_citation_verification_normalization.md
```

It also updates research-track navigation/checkpoint context only. The
normalization records the externally supplied Perplexity primary-source
verification report as external scout material under Phase 34 artifact-intake
rules. The report is not treated as evidence approval, source-of-truth
material, methodology validation, parameter approval, data approval, universe
approval, benchmark approval, reproduction approval, validation approval,
implementation approval, or trading approval.

The citation verification table covers `MA-PRACT-001` Faber,
`ETF-ACADEMIC-001`, `MA-ACADEMIC-001 / unresolved`, `ZAKAMULIN-2014`,
`ZAKAMULIN-2016`, and optional related Zakamulin SSRN leads. Rows record
verified title, author, year, venue, DOI/SSRN/RePEc/publisher identifiers,
reported primary links, full-text access status, citation reliability,
identity status, later limited formal review eligibility, and remaining
follow-up.

The readiness decision is conservative. Faber is eligible for later limited
formal review only if the open PDF and SSRN metadata are verified in the repo
trail. `ETF-ACADEMIC-001` is eligible only conditionally because the published
version appears restricted and working-paper/full-text access must be
confirmed. "Simple Market Timing with Moving Averages" remains unresolved and
should not be reviewed under that title. `ZAKAMULIN-2014` and
`ZAKAMULIN-2016` may become separate later review candidates only if primary
text access and exact identifiers are confirmed.

The document records citation-quality cautions: Perplexity output may mix
primary links with inferred statements, abstracts and claims must be checked
against primary pages/full text, publication metadata must be recorded before
review, formal review must use full primary text rather than summaries, and no
performance claim is accepted until independently reviewed and later
reproduced where applicable.

Required follow-up before formal review includes confirming full-text access,
verifying exact title/author/year/venue identifiers, obtaining or inspecting
primary PDF or official full text, recording DOI/SSRN/RePEc/publisher/version
metadata, extracting exact moving-average rules, universe, period, frequency,
benchmark, cash proxy, return construction, dividend/corporate-action
treatment, costs/frictions, OOS/robustness/parameter-sensitivity treatment,
lookahead/survivorship/data-snooping controls, limitations, and non-claims.

The recommended next gate is limited formal review of Faber only after the
open PDF and SSRN metadata are verified in the repo trail. Reviews of
`ETF-ACADEMIC-001` or Zakamulin candidates remain conditional pending primary
full-text access and version verification.

This phase does not approve evidence, methodology, parameters, source data, an
ETF universe, benchmark, cash proxy, data acquisition, data files, PDFs,
fixtures, reproduction, validation, signal definitions, evaluator behavior,
implementation, production thresholds, or trading implications.

Remaining blockers include no `ValidatedResearchArtifact`, no
`ValidatedSignalDefinition`, no approved evidence review, no approved
methodology or parameters, no approved ETF universe, no selected/approved data
source, no approved benchmark/cash proxy, no approved final data
storage/fixture policy, no acquired data, no project-local deterministic
reproduction, no no-lookahead audit, no production threshold/config
provenance, no implementation-scope approval, no evaluator tests, no
source-specific formal evidence review, no primary full-text verification in
the repo trail, no approved source identity for "Simple Market Timing with
Moving Averages", no verified version alignment, no extracted rule/universe/
benchmark/cash proxy from reviewed primary text, no approved return-treatment
or corporate-action handling decisions, no approved friction assumptions, no
robustness or parameter-sensitivity review, no benchmark/cash/risk-metric
review, no result-review template, no promotion/rejection decision, and no
trading implication or production threshold.

## Phase 33 Step 15 Broad ETF Faber Limited Formal Evidence Review

Phase 33 Step 15 is documentation-only. It adds:

```text
docs/design/phase33_broad_etf_faber_limited_formal_evidence_review.md
```

It also updates research-track navigation/checkpoint context only. The review
inspects Mebane T. Faber's "A Quantitative Approach to Tactical Asset
Allocation" as methodology and practitioner/TAA context for the broad-ETF
moving-average candidate. It records source identity, SSRN ID 962461, author
hosted PDF and SSRN access status, publication/update trail, full-text access
status, citation reliability, and evidence status as limited formal review
candidate only.

The methodology summary records the primary-text framing of a monthly
10-month simple moving-average rule, month-end update cadence, same-close
entry/exit statement, total-return series treatment, 90-day Treasury-bill cash
treatment, five broad index asset classes, equal-weight buy-and-hold
comparison, parameter-stability discussion, monthly rebalancing notes, and
index-proxy / ETF-inception caveats.

The relevance section keeps Faber in methodology-context territory only. It
can inform later questions about broad asset-class trend following, ETF/TAA
translation, rule design, benchmark/cash framing, parameter discipline, and
no-lookahead/as-of handling. It does not approve the paper's evidence, the
10-month parameter, the original universe, benchmark, cash proxy, data source,
return construction, reproduction route, validation route, evaluator behavior,
or implementation.

Bias and robustness considerations include the paper's post-2005
out-of-sample framing, parameter-stability discussion, same-close timing
caution, lack of project-usable survivorship handling extracted for the
five-index GTAA test, data-snooping cautions, index-proxy and ETF-inception
limits, base-test exclusion of taxes/commissions/slippage, total-return
assumptions, and unresolved project-local data-source reproducibility.

Transferability limits state that historical performance figures, original
universe validity, parameter validity, benchmark validity, cash/risk-free
proxy validity, cost/friction assumptions, total-return assumptions,
same-close timing, original index-proxy history, ETF implementation readiness,
live/paper trading readiness, and broad ETF implementation approval cannot
transfer directly.

The disposition labels are cautious only: methodology context,
practitioner/TAA context, benchmark/context, cash-treatment context,
parameter-discipline context, no-lookahead/as-of caution context, requires
project-local reproduction, not validated evidence, and not
implementation-ready.

Required follow-up includes verifying the exact reviewed version, extracting
exact tables/figures only if needed later, comparing paper assumptions to
project source/universe/benchmark/cash/storage gates, checking total-return
and corporate-action assumptions, defining any project-local reproduction and
no-lookahead action convention only in later phases, reviewing
`ETF-ACADEMIC-001` separately if full text becomes available, and reviewing
Zakamulin separately if selected as a formal candidate.

The recommended next docs-only gate is `ETF-ACADEMIC-001` full-text
verification / limited review if accessible. If that source is inaccessible,
formal evidence review should pause until more primary texts are available.

This phase does not approve evidence, methodology, parameters, source data, an
ETF universe, benchmark, cash proxy, data acquisition, data files, PDFs,
fixtures, reproduction, validation, signal definitions, evaluator behavior,
implementation, production thresholds, or trading implications.

Remaining blockers include no `ValidatedResearchArtifact`, no
`ValidatedSignalDefinition`, no approved evidence review, no approved
methodology or parameters, no approved ETF universe, no selected/approved data
source, no approved benchmark/cash proxy, no approved final data
storage/fixture policy, no acquired data, no project-local deterministic
reproduction, no no-lookahead audit, no production threshold/config
provenance, no implementation-scope approval, no evaluator tests, no approved
source identity for "Simple Market Timing with Moving Averages", no
Zakamulin full-text review, no approved return-treatment or corporate-action
handling decisions, no approved friction assumptions, no
benchmark/cash/risk-metric approval, no result-review template for
ETF-ACADEMIC-001-derived claims, no comparison synthesis with Faber, no
promotion/rejection decision, and no trading implication or production
threshold.

Phase 33 Step 16 adds the broad-ETF `ETF-ACADEMIC-001` limited formal
evidence review. It reviews Huang and Huang's "Testing moving average trading
strategies on ETFs" as ETF-specific methodology and context only, records
source identity, DOI 10.1016/j.jempfin.2019.10.002, RePEc handle
RePEc:eee:empfin:v:57:y:2020:i:c:p:16-32, SSRN working paper ID 3138690,
ScienceDirect publisher reference S0927539819300830, working-paper versus
published-version access status, no supplementary data/code found on reviewed
primary pages, moving-average and `QUIMA` framing, ETF-versus-index comparison
context, buy-and-hold and zero-return/risk-free benchmark context,
risk-adjusted evaluation context, opening-gap and transaction-cost cautions,
lag-length and data-snooping cautions, transferability limits, cautious
disposition labels, required follow-up, and remaining blockers. It recommends
a docs-only broad ETF methodology evidence synthesis boundary using Faber plus
`ETF-ACADEMIC-001`. It does not approve evidence, methodology, parameters,
data, an ETF universe, benchmark, cash proxy, reproduction, validation,
implementation, evaluator behavior, signal computation, or trading
implication.

Phase 33 Step 17 adds the broad-ETF methodology evidence synthesis boundary.
It synthesizes Faber plus `ETF-ACADEMIC-001` as limited context-only evidence,
records common moving-average, benchmark/cash, total-return, ETF-friction,
parameter-discipline, and no-lookahead/action-timing themes, separates areas
of agreement from unresolved tensions, states what the evidence can and cannot
support, lists minimum requirements before reproduction planning, and
recommends a docs-only broad ETF reproduction readiness checklist as the next
conservative gate. It does not approve evidence, methodology, parameters,
data, an ETF universe, benchmark, cash proxy, reproduction, validation,
implementation, evaluator behavior, signal computation, or trading
implication.

Phase 33 Step 18 adds the broad-ETF reproduction readiness checklist. It
enumerates unresolved gates for evidence, methodology, parameter discipline,
ETF universe, data source, terms/license, storage/fixtures, benchmark/cash
proxy, return construction, no-lookahead/as-of handling, costs/frictions,
survivorship, reproduction protocol, result review, and implementation scope.
It recommends pausing Phase 33 before code until source, data policy,
universe, benchmark, and cash-proxy choices can be made concrete. It does not
approve reproduction, methodology, parameters, data, an ETF universe,
benchmark, cash proxy, validation, implementation, evaluator behavior, signal
computation, or trading implication.

Phase 33 Step 19 adds the broad-ETF source/universe/benchmark
decision-readiness boundary. It assesses whether source, ETF universe,
benchmark/cash proxy, return-construction, and data-policy gates are ready for
concrete decisions, finds no gate approval-ready now, keeps most gates partial,
keeps return construction, survivorship/inception/delisting, reproduction
protocol, result-review template, and implementation scope blocked, and
recommends a docs-only return-construction boundary as the next narrow blocker.
It does not approve a source, universe, benchmark, cash proxy, methodology,
parameter, data policy, reproduction protocol, implementation, signal
definition, evaluator, or trading implication.

Phase 33 Step 20 adds the broad-ETF return-construction boundary. It compares
raw close returns, adjusted close returns, explicit total-return construction,
vendor-provided total-return series, cash/T-bill return series, and a
zero-return placeholder as unresolved options only. It records required
decisions for price versus total return, dividends and distributions, splits
and corporate actions, adjusted-data transparency, expenses, cash/T-bill
returns, benchmark comparability, compounding, ETF inception alignment,
missing/stale data, frequency alignment, and timing/action-date implications.
It keeps return construction blocked for approval, recommends a docs-only
no-lookahead/as-of protocol boundary next, and does not approve a return
basis, source, universe, benchmark, cash proxy, methodology, parameter, data
policy, reproduction protocol, implementation, signal definition, evaluator,
or trading implication.

## Phase 33 Step 21 Broad ETF No-Lookahead / As-Of Protocol Boundary

Phase 33 Step 21 is documentation-only. It adds:

```text
docs/design/phase33_broad_etf_no_lookahead_asof_protocol_boundary.md
```

It also updates research-track navigation/checkpoint context only. The
boundary defines the core as-of principle for the broad-ETF moving-average
candidate: signals may use only information available at the decision
timestamp, action timing must occur after signal observation, data revisions
and adjusted data must be handled explicitly, benchmark/cash availability must
be aligned by availability date, and normal `python -m pytest` must remain
offline, credential-free, deterministic, and free of live data, credentials,
network, brokers, notebooks, external providers, and runtime trading behavior.

The timing vocabulary covers observation date, decision timestamp, action
timestamp, effective trade date, close-to-close assumption, next-open
assumption, next-close assumption, monthly rebalance date, cash-rate
observation date, dividend/distribution ex-date and payment-date
implications, and data publication/revision timestamp.

The moving-average timing section records unresolved choices for prior-close
inputs, after-close signal observation, next-open versus next-close or later
action, same-close signal/action assumptions, end-of-month data availability,
holiday/non-trading-day lags, and explicit lag documentation before results.

The adjusted-data and total-return section records that adjusted close may
reflect later corporate-action information, dividend/split/other adjustment
semantics must be documented, total-return construction must define when
distributions become knowable, retroactive vendor adjustments are both
reproducibility and as-of risks, and source snapshots must record retrieval
date and adjustment assumptions.

The cash/benchmark section records that FRED or other cash-rate series may
have publication, vintage, correction, and revision timing; daily versus
monthly cash-rate alignment remains unresolved; benchmark returns must be
compared on the same availability/timing basis; zero-return placeholder is not
approved; and no benchmark or cash proxy is approved.

The ETF universe and inception section records that ETFs cannot be used before
inception or first usable observation, index proxies before ETF inception are
not approved, delisting/inactive handling remains unresolved, universe
membership must be predefined before performance inspection, and future
inclusion/exclusion rules must be documented before results.

Decision: no-lookahead/as-of protocol remains blocked for approval. Required
future approval criteria include selected observation/action timing, explicit
lag convention, selected return basis, source snapshot policy,
dividend/split/corporate-action timing policy, cash-rate availability policy,
benchmark alignment policy, universe inception/delisting policy, testable
deterministic examples, and explicit non-claims.

Recommended next route: a docs-only survivorship/inception/delisting boundary.
That is the narrowest next gate because no-lookahead review cannot become
approval-ready until ETF first-usable observations, inactive or delisted funds,
and pre-result universe membership are defined.

This phase does not approve no-lookahead/as-of protocol, return construction,
source, universe, benchmark, cash proxy, methodology, parameter, data policy,
data acquisition, ingestion, files, fixtures, schemas, code, notebooks,
scripts, backtests, reproduction, signal definitions, evaluator behavior,
validated artifacts, validated signal definitions, implementation, production
thresholds, or trading implications.

Remaining blockers include no `ValidatedResearchArtifact`, no
`ValidatedSignalDefinition`, no approved evidence review, no approved
methodology or parameters, no approved ETF universe, no selected/approved data
source, no approved benchmark/cash proxy, no approved final data
storage/fixture policy, no approved return-construction policy, no approved
no-lookahead/as-of protocol, no approved cost/friction assumptions, no
approved survivorship/inception/delisting policy, no acquired data, no
project-local deterministic reproduction, no implementation-scope approval,
no evaluator tests, no approved source fields, no approved adjusted-close
semantics, no approved total-return method, no approved cash-rate conversion,
no approved benchmark alignment, no result-review template, no reproduction
protocol, and no trading implication or production threshold.

## Phase 33 Step 22 Broad ETF Survivorship / Inception / Delisting Boundary

Phase 33 Step 22 is documentation-only. It adds:

```text
docs/design/phase33_broad_etf_survivorship_inception_delisting_boundary.md
```

It also updates research-track navigation/checkpoint context only. The
boundary defines the core pre-result universe principle for the broad-ETF
moving-average candidate: any future ETF universe must be defined before
result inspection and must avoid survivorship-biased selection, cherry-picked
winners, and retroactive inclusion rules.

The inception-date section records that ETFs cannot be used before actual
inception, inception dates must come from reliable metadata sources, first
usable observations may be later than inception, pre-inception data must be
rejected unless an explicitly approved proxy policy exists, index proxies
before ETF inception are not approved, and start dates must be aligned across
ETF, benchmark, and cash data.

The delisting/inactive section records that inactive or delisted ETF handling
remains unresolved, future sources must document whether delisted/inactive ETF
history is available, excluding delisted ETFs may create survivorship bias,
relying only on current surviving funds requires justification and limitation
labels if later used, and any later exclusion of inactive ETFs must be
documented as a limitation.

The symbol-identity section records that stable identity must be verified and
that ticker changes, fund mergers, closures, share class changes, issuer
changes, exchange changes, provider symbol formats, and index changes require
a handling policy. Current issuer metadata may not preserve historical
metadata, so symbol continuity cannot be assumed from current ticker alone.

The universe-membership section records that candidate buckets,
inclusion/exclusion rules, liquidity/expense/history filters, and replacement
rules must be fixed before performance inspection. It disallows
performance-based ETF selection and grants no final ETF universe approval.

The source implications preserve prior routing: Stooq remains a possible
planning candidate with delisting/inactive/symbol-history coverage unresolved;
Yahoo Finance / yfinance remains secondary/check or unresolved with
survivorship and reproducibility unresolved; ETF issuer pages remain
metadata/context only with historical metadata limits unresolved; broker data
remains context only and not default; and no source is approved.

The relationship section records that inception handling affects return
windows, delisting/inactive handling affects survivorship bias, symbol changes
affect adjusted-return continuity, metadata availability affects as-of
correctness, and universe membership must not use future knowledge.

Decision: survivorship/inception/delisting policy remains blocked for
approval. Required future approval criteria include approved ETF universe
construction rules, approved inception-date source, approved inactive/delisted
ETF handling, approved symbol-identity policy, approved proxy policy if any,
approved metadata snapshot/provenance policy, explicit limitations and
non-claims, and deterministic examples if fixtures are later allowed.

Recommended next route: a docs-only cash/benchmark return treatment boundary.
That is the narrowest next gate because return construction, no-lookahead
timing, and universe/inception rules still cannot be reviewed against results
until cash/risk-free series, benchmark returns, buy-and-hold comparisons,
frequency alignment, publication timing, and zero-return placeholders are
scoped without approving a benchmark or cash proxy.

This phase does not approve survivorship/inception/delisting policy, ETF
universe, source, benchmark, cash proxy, return construction,
no-lookahead/as-of protocol, methodology, parameter, data policy, data
acquisition, ingestion, files, fixtures, schemas, code, notebooks, scripts,
backtests, reproduction, signal definitions, evaluator behavior, validated
artifacts, validated signal definitions, implementation, production
thresholds, or trading implications.

Remaining blockers include no `ValidatedResearchArtifact`, no
`ValidatedSignalDefinition`, no approved evidence review, no approved
methodology or parameters, no approved ETF universe, no selected/approved data
source, no approved benchmark/cash proxy, no approved final data
storage/fixture policy, no approved return-construction policy, no approved
no-lookahead/as-of protocol, no approved cost/friction assumptions, no
approved survivorship/inception/delisting policy, no acquired data, no
project-local deterministic reproduction, no implementation-scope approval,
no evaluator tests, no approved inception-date source, no approved
first-usable-observation rule, no approved inactive/delisted ETF handling, no
approved symbol-identity policy, no approved proxy policy, no approved
metadata snapshot/provenance policy, no approved benchmark/cash return
treatment, no result-review template, no reproduction protocol, and no trading
implication or production threshold.

## Phase 33 Step 23 Broad ETF Cash / Benchmark Return Treatment Boundary

Phase 33 Step 23 is documentation-only. It adds:

```text
docs/design/phase33_broad_etf_cash_benchmark_return_treatment_boundary.md
```

It also updates research-track navigation/checkpoint context only. The
boundary defines cash and benchmark return-treatment questions before any
reproduction planning and prevents premature benchmark, cash proxy,
cash-rate series, source, ETF universe, return construction,
no-lookahead/as-of protocol, methodology, parameter, data policy,
implementation, evaluator, signal-definition, or trading-use approval.

Benchmark comparison candidates remain candidate-only: buy-and-hold versions
of any later selected ETF universe, a broad U.S. equity benchmark candidate,
asset-class-matched benchmark candidates, a cash/T-bill proxy comparison, and
a zero-return placeholder only as a last-resort methodology placeholder.

Cash/T-bill proxy candidates remain candidate-only: FRED `TB3MS`, FRED
`DGS3MO`, any other FRED Treasury/cash-rate candidates only if separately
identified and reviewed later, and zero-return cash only as an unapproved
sensitivity/context placeholder. Rate type, frequency, publication timing,
revision behavior, vintage handling, annualized-rate conversion, compounding,
day count, and period-return conversion remain unresolved.

Required decision areas include benchmark return basis, cash return basis and
compounding, daily versus monthly frequency alignment, ETF signal cadence
versus benchmark/cash cadence, date alignment across ETF, benchmark, and cash
data, FRED publication/revision/as-of timing, non-trading days and holidays,
whether cash earns return while out of market, transaction-cost and idle-cash
assumptions, inflation or real-return treatment, and zero-return cash as
sensitivity/context only.

No-lookahead/as-of constraints require cash and benchmark data to be available
as of the decision/evaluation timestamp, FRED publication/revision timing to
be documented before use, benchmark/cash alignment to avoid hindsight
convenience, monthly cash returns not to use future daily data, same-period
comparisons to define observation/action rules, and normal pytest not to call
FRED, vendor APIs, broker APIs, or online sources.

The relationship section ties this boundary back to Step 33.20 return
construction, Step 33.21 no-lookahead/as-of timing, Step 33.22
survivorship/inception/delisting, Step 33.6 universe/benchmark shortlist,
Step 33.8 final source shortlist, and Step 33.9 data storage/fixture policy.

Required future approval criteria include selected benchmark definition,
selected cash/risk-free proxy, selected source and series identifiers,
documented frequency and conversion method, documented publication/revision/
as-of handling, documented alignment with ETF universe and return
construction, documented limitations and non-claims, and a deterministic
fixture/local-data policy if data is used later.

Decision: cash/benchmark return treatment remains blocked for approval. This
phase creates a partial planning boundary only and does not make the
broad-ETF candidate ready for data acquisition, schemas, notebooks, scripts,
fixtures, backtests, reproduction, result review, evaluators, signal
definitions, validated artifacts, implementation, or trading-path work.

Recommended next route: a docs-only cost/friction assumptions boundary. That
is the narrowest next gate because cash and benchmark comparability still
depends on whether out-of-market cash earns return, whether idle cash is
modeled, and whether transaction costs, spreads, slippage, taxes, fund
expenses, opening gaps, turnover, and rebalance friction are included,
excluded, or deferred without approving a benchmark, cash proxy, source,
return construction, reproduction, implementation, or trading use.

This phase does not approve benchmark/cash proxy, cash-rate series, source,
universe, return construction, no-lookahead/as-of protocol,
survivorship/inception/delisting policy, methodology, parameter, data policy,
data acquisition, ingestion, files, fixtures, schemas, code, notebooks,
scripts, backtests, reproduction, signal definitions, evaluator behavior,
validated artifacts, validated signal definitions, implementation, production
thresholds, or trading implications.

Remaining blockers include no `ValidatedResearchArtifact`, no
`ValidatedSignalDefinition`, no approved evidence review, no approved
methodology or parameters, no approved ETF universe, no selected/approved data
source, no approved benchmark/cash proxy, no approved final data
storage/fixture policy, no approved return-construction policy, no approved
no-lookahead/as-of protocol, no approved cost/friction assumptions, no
approved survivorship/inception/delisting policy, no acquired data, no
project-local deterministic reproduction, no implementation-scope approval,
no evaluator tests, no approved benchmark definition, no approved
buy-and-hold comparison convention, no approved asset-class-matched benchmark
convention, no approved cash/risk-free proxy, no approved cash-rate series,
no approved FRED publication/revision/as-of handling, no approved cash-rate
conversion or compounding rule, no approved benchmark return basis, no
approved benchmark/cash frequency-alignment rule, no approved benchmark/cash
date-alignment rule, no approved non-trading-day or holiday policy, no
approved out-of-market cash return assumption, no approved idle-cash
assumption, no approved inflation or real-return treatment, no approved
zero-return placeholder policy, no result-review template, no reproduction
protocol, and no trading implication or production threshold.

## Phase 35 Step 1 Default Pytest Network Kill-Switch

Phase 35 Step 1 is the smallest safe enforcement implementation after the
documentation-heavy research-planning sequence. It adds a default pytest
network kill-switch in `tests/conftest.py` so normal `python -m pytest`
patches `socket.socket` and `socket.create_connection` to raise a clear
offline, credential-free failure before accidental network access can proceed.

The explicit escape hatches are `--allow-network` and
`ALGO_TRADER_ALLOW_NETWORK_TESTS=1`, reserved for future explicitly gated
integration tests only. They do not unskip existing paper integration tests by
themselves and do not add broker, Alpaca SDK, vendor API, credential,
runtime/scheduler, persistence, data acquisition, data ingestion, notebook,
portfolio, order-submission, signal, evaluator, return-construction, broad-ETF
research, live, or paper behavior.

Verification for this phase:

- `python -m pytest tests/unit/test_default_pytest_network_guard.py` -> 6 passed
- `python -m pytest tests/unit/test_dependency_direction.py` -> 9 passed
- `python -m pytest` -> 784 passed, 4 skipped

## Phase 35 Step 2 Synthetic Return Construction / As-Of Mechanics Kernel

Phase 35 Step 2 adds a tiny pure-function research mechanics kernel for
synthetic fixtures only. The new
`src/algotrader/research/return_construction.py` module exposes arithmetic
`simple_return`, immutable close-to-close return tuple construction, and
lagged observation/action-date pairs using calendar-day offsets over strictly
increasing synthetic dates.

Files changed in this phase:

- `src/algotrader/research/return_construction.py`
- `tests/unit/test_return_construction.py`
- `docs/deterministic_core.md`
- `docs/project_checkpoint.md`

The unit tests use only synthetic `Decimal` values and synthetic `date` values.
They cover simple return calculation, close-to-close tuple construction,
Decimal precision preservation, zero and negative prior-value rejection,
non-`Decimal` numeric rejection, malformed return sequences, lagged action
date construction, no same-day action when lag is positive, zero-lag mechanical
examples, immutable tuple outputs, malformed observation-date rejection, and
AST guardrails against network, broker, vendor API, data-library, strategy,
signal-definition, evaluator, backtest, portfolio, runtime, and data-file
dependencies.

Validation added in this phase rejects malformed sequences, non-`Decimal`
return inputs, zero or negative prior values, empty observation-date sequences,
non-`date` observation values, unordered or duplicate observation dates,
non-integer lag values, boolean lag values, and negative lag values.

Verification for this phase:

- `python -m pytest tests/unit/test_return_construction.py` -> 30 passed
- `python -m pytest tests/unit/test_default_pytest_network_guard.py` -> 6 passed
- `python -m pytest tests/unit/test_dependency_direction.py` -> 9 passed
- `python -m pytest` -> 814 passed, 4 skipped

Explicit non-goals remain in force: no real market data, vendor data,
Stooq/Yahoo/FRED/Alpha Vantage/Nasdaq calls, network calls, credentials, data
downloads, data files, notebooks, scripts, broker behavior, Alpaca behavior,
OMS/runtime/scheduler/persistence behavior, portfolio mutation, ledger or
reconciliation behavior, ML, LLM trading-path behavior, vectorbt,
QuantConnect, strategy implementation, broad ETF SMA implementation,
signal/evaluator implementation, order generation, `ValidatedResearchArtifact`,
`ValidatedSignalDefinition`, profitability claims, validation claims,
implementation-readiness claims, production-threshold claims, or
trading-readiness claims.

## Phase 35 Step 3 Research Fixture / Manifest Contract

Phase 35 Step 3 adds a tiny immutable research fixture manifest contract for
future synthetic fixtures, derived fixtures, and local-only snapshot metadata.
The new `src/algotrader/research/fixture_manifest.py` module exposes
`ResearchFixtureManifest`, a frozen slotted dataclass that records provenance
and eligibility metadata only.

Files changed in this phase:

- `src/algotrader/research/fixture_manifest.py`
- `tests/unit/test_fixture_manifest.py`
- `docs/deterministic_core.md`
- `docs/project_checkpoint.md`

The contract records fixture identity, fixture kind, description, source name,
source type, optional retrieval and data-range dates, field names, checksum,
normal-pytest eligibility, redistribution safety, limitations, and non-claims.
It intentionally has no broker, runtime, network, vendor, strategy, signal,
evaluator, backtest, portfolio, order, approval, profitability, validation, or
trading-readiness fields.

Validation added in this phase requires non-empty required strings, allowed
fixture kinds (`synthetic`, `derived`, `local_only`), allowed source types
(`synthetic`, `manual`, `third_party`, `local_snapshot`), immutable tuple
fields with non-empty string entries, plain `date` values rather than
`datetime`, ordered data date ranges, and plain boolean flags.
`normal_pytest_eligible=True` requires `redistribution_safe=True`, rejects
local-only fixtures, rejects third-party and local-snapshot source categories,
requires synthetic fixtures to use synthetic sources, and allows derived
normal-pytest fixtures only when their source type is synthetic or manual.

The unit tests cover valid synthetic manifest creation, valid local-only
manifest creation with `normal_pytest_eligible=False`, safe derived/manual
metadata, frozen/slotted behavior, tuple conversion and immutability, exact
metadata field names, empty required strings, unknown fixture kinds, malformed
tuple fields, `datetime` rejection, bad date ranges, local-only and external
raw-source normal-pytest rejection, redistribution-safety requirements, plain
boolean validation, forbidden import/dependency checks, and absence of broker,
network, vendor, runtime, strategy, signal, evaluator, and trading-path calls
or names.

Verification for this phase:

- `python -m pytest tests/unit/test_fixture_manifest.py` -> 33 passed
- `python -m pytest tests/unit/test_return_construction.py` -> 30 passed
- `python -m pytest tests/unit/test_default_pytest_network_guard.py` -> 6 passed
- `python -m pytest tests/unit/test_dependency_direction.py` -> 9 passed
- `python -m pytest` -> 847 passed, 4 skipped
- `git diff --check` -> passed with existing docs CRLF warnings only

Explicit non-goals remain in force: no real market data, vendor/public data
files, source approval, ETF universe approval, benchmark approval, cash-proxy
approval, data acquisition, data download, data ingestion, network calls,
credentials, notebooks, scripts, backtests, strategy implementation,
signal/evaluator implementation, broker behavior, OMS/runtime/scheduler/
persistence behavior, portfolio mutation, ledger or reconciliation behavior,
Alpaca behavior, ML, LLM trading-path behavior, vectorbt, QuantConnect,
`ValidatedResearchArtifact`, `ValidatedSignalDefinition`, production
thresholds, profitability claims, validation claims, trading-readiness claims,
or trading-path behavior.

## Phase 35 Step 4 Implementation Consolidation Checkpoint

Phase 35 Step 4 is a focused implementation checkpoint after the default
pytest network kill-switch, synthetic return construction / as-of mechanics
kernel, and `ResearchFixtureManifest` metadata contract. The review confirmed
that the Phase 35 code is still small, deterministic, offline-safe,
synthetic-only where it handles values, and outside the trading hot path.

Network guard checkpoint: normal `python -m pytest` installs the socket guard
by default and blocks `socket.socket` plus `socket.create_connection` unless
`--allow-network` or `ALGO_TRADER_ALLOW_NETWORK_TESTS=1` is explicitly used.
Those escape hatches remain explicit and reserved for gated integration tests.
The current normal test suite remains offline and credential-free; no real
network calls were found in Phase 35 tests.

Return-construction checkpoint: `algotrader.research.return_construction`
remains synthetic-only and mechanical. It uses strict `Decimal` inputs for
simple and close-to-close arithmetic returns, strict plain `date` inputs for
lagged observation/action-date examples, rejects malformed values and dates,
and returns immutable tuples where expected. It contains no strategy,
moving-average, evaluator, backtest, broker, portfolio, real-data,
adjusted-close, total-return, dividend, benchmark, cash, cost, or trading-path
logic.

Fixture manifest checkpoint: `ResearchFixtureManifest` remains a frozen,
slotted, metadata/provenance-only contract. It records fixture identity, kind,
source name/type, optional dates, field names, checksum, normal-pytest
eligibility, redistribution safety, limitations, and non-claims. It does not
approve a source, data set, ETF universe, benchmark, cash proxy, local
snapshot, third-party raw data, validation result, or trading use. Local-only
and third-party/local-snapshot source categories cannot be normal-pytest
eligible, and no data files or fixtures were added.

Dependency boundary checkpoint: the research package still imports only
standard-library helpers, core validation, and project validation errors. No
`pandas`, `numpy`, `yfinance`, `requests`, `vectorbt`, QuantConnect, broker,
network, runtime, portfolio, risk, screener, signal, execution, persistence,
database, ML, or LLM dependency entered the Phase 35 research modules. One
small test-guard gap was found and fixed: the package-level research
dependency guard now explicitly forbids common data-library, QuantConnect,
broker-alias, ML, and LLM import prefixes in addition to the existing
trading-path and network prefixes.

Architecture-fit checkpoint: Phase 35 supports the future research pipeline by
adding offline enforcement, tiny synthetic mechanics, and metadata-only
provenance vocabulary. It does not enter the signal, order, execution,
portfolio, broker, scheduler/runtime, notebook, ingestion, or backtest path.

Recommended next implementation phases, ranked by safety and usefulness:

1. Synthetic as-of examples / clock contract tests. This is the smallest useful
   next step because it can connect the existing synthetic lag mechanics to
   deterministic clock/as-of expectations without real data, sources,
   strategies, evaluators, backtests, or trading behavior.
2. Manifest serialization/deserialization for metadata only. This would make
   provenance records easier to pass through future fixture tooling while
   staying data-free if it is limited to pure metadata dictionaries and avoids
   file I/O, data loading, source approval, and fixture materialization.

Verification for this checkpoint:

- `python -m pytest tests/unit/test_fixture_manifest.py` -> 33 passed
- `python -m pytest tests/unit/test_return_construction.py` -> 30 passed
- `python -m pytest tests/unit/test_default_pytest_network_guard.py` -> 6 passed
- `python -m pytest tests/unit/test_dependency_direction.py` -> 9 passed
- `python -m pytest` -> 847 passed, 4 skipped

Explicit non-goals remain in force: no real market data, vendor/public data
files, source approval, ETF universe approval, benchmark approval, cash-proxy
approval, data acquisition, data download, data ingestion, network calls,
credentials, notebooks, scripts, backtests, strategy implementation,
signal/evaluator implementation, broker behavior, OMS/runtime/scheduler/
persistence behavior, portfolio mutation, ledger or reconciliation behavior,
Alpaca behavior, ML, LLM trading-path behavior, vectorbt, QuantConnect,
`ValidatedResearchArtifact`, `ValidatedSignalDefinition`, production
thresholds, profitability claims, validation claims, trading-readiness claims,
or trading-path behavior.

## Phase 36 Synthetic As-Of Replay Kernel

Phase 36 adds the smallest deterministic synthetic-only as-of replay kernel for
future research replay and no-lookahead enforcement. The new
`src/algotrader/research/asof.py` module exposes `AsofObservation`,
`iter_asof_available(...)`, and `next_available_asof_date(...)`.

Files changed in this phase:

- `src/algotrader/research/asof.py`
- `tests/unit/test_asof.py`
- `docs/deterministic_core.md`
- `docs/project_checkpoint.md`

Implementation summary: `AsofObservation` is a frozen slotted dataclass with
only `observation_date` and `available_after` plain `date` fields.
`iter_asof_available(...)` returns an immutable tuple of observations whose
`available_after` is on or before the caller-provided as-of date while
preserving original input order. `next_available_asof_date(...)` returns the
earliest availability date from a non-empty synthetic observation sequence.

Validation behavior: the kernel rejects `datetime`, bool, date subclasses, and
non-date values where plain dates are required; availability dates before
observation dates; malformed observation sequence inputs; non-`AsofObservation`
items; duplicate observation dates; unordered observation-date sequences;
non-date as-of values; and empty sequences when asking for the next available
as-of date.

Tests added in `tests/unit/test_asof.py` cover frozen/slotted field shape,
plain-date enforcement, availability-before-observation rejection,
no-lookahead filtering, original-order preservation, immutable tuple outputs,
empty filter results, duplicate rejection, chronological ordering enforcement,
malformed input rejection, empty-sequence rejection for next availability,
deterministic replay snapshots, earliest-availability selection, and AST
guardrails against trading-path, vendor, network, data-library, broker,
runtime, portfolio, signal, evaluator, ML, LLM, vectorbt, and QuantConnect
leakage.

Verification for this phase:

- `python -m pytest tests/unit/test_asof.py` -> 30 passed
- `python -m pytest tests/unit/test_dependency_direction.py` -> 9 passed
- `python -m pytest` -> 877 passed, 4 skipped

Normal pytest remains offline and credential-free under the default network
guard. This phase adds no backtesting engine, broker behavior, runtime
scheduling, portfolio mutation, signal evaluator logic, order generation,
real market data, data ingestion, vendor access, ML/LLM usage, network access,
source approval, validation claims, profitability claims, trading-readiness
claims, or trading-path behavior.

## Phase 37 Fixture Manifest Serialization Contract

Phase 37 adds deterministic metadata-only serialization and deserialization for
`ResearchFixtureManifest` so fixture provenance can be saved, reviewed, and
reloaded later without introducing real data ingestion, file I/O, source
approval, or trading-path behavior.

Files changed in this phase:

- `src/algotrader/research/fixture_manifest.py`
- `tests/unit/test_fixture_manifest.py`
- `tests/unit/test_dependency_direction.py`
- `docs/deterministic_core.md`
- `docs/project_checkpoint.md`

Implementation summary: `ResearchFixtureManifest.to_dict()` now returns a
deterministic JSON-compatible dictionary containing exactly the existing
manifest metadata fields. Optional plain `date` values serialize as
`YYYY-MM-DD` strings or `None`, and tuple fields serialize as lists.
`ResearchFixtureManifest.from_dict(...)` restores those dictionaries by parsing
strict ISO calendar dates, restoring list fields as immutable tuples, rejecting
unknown or missing fields, and then constructing the frozen manifest so all
existing validation still runs.

Validation behavior: deserialization rejects non-dict payloads, unknown fields,
missing required fields, malformed date strings, non-string date payloads,
non-list tuple-field payloads, bad date ranges, unsafe normal-pytest eligibility
for local-only, third-party, or local-snapshot raw fixture categories, and all
pre-existing malformed manifest values. Round-tripping preserves manifest
equality, tuple immutability, and the original manifest is not mutated by
serialized payload list changes.

Tests added in `tests/unit/test_fixture_manifest.py` cover deterministic
serialized shape and key order, successful round-trip equality, ISO date
serialization and restoration, tuple-to-list serialization and tuple
restoration, immutability after deserialization, serialized-list non-sharing,
unknown-field rejection, missing-field rejection, malformed-date rejection,
existing validation preservation, unsafe normal-pytest eligibility rejection,
and the existing AST guardrails against file I/O, network calls, vendor imports,
broker/runtime, backtesting, signal/evaluator, portfolio, ML, LLM, and trading
behavior. The dependency-direction guardrail also keeps the research package
free of network, vendor, pandas, numpy, vectorbt, QuantConnect, broker/runtime,
portfolio, signal, and ML/LLM imports.

Verification for this phase:

- `python -m pytest tests/unit/test_fixture_manifest.py` -> 48 passed
- `python -m pytest tests/unit/test_dependency_direction.py` -> 9 passed
- `python -m pytest` -> 892 passed, 4 skipped

Normal pytest remains offline and credential-free under the default network
guard. This phase adds no JSON file persistence, file reads or writes, raw data
loading, real market data, data ingestion, vendor access, source approval,
pandas, numpy, yfinance, vectorbt, QuantConnect, broker behavior, runtime
scheduling, portfolio mutation, signal evaluator logic, backtesting engine,
order generation, ML/LLM usage, validation claims, profitability claims,
trading-readiness claims, or trading-path behavior.

## Phase 38 Synthetic Research Replay Package

Phase 38 combines the existing synthetic research plumbing into one tiny
metadata-only replay snapshot package. It is intentionally not a backtest
engine and does not add strategy logic, evaluator logic, broker/runtime
behavior, portfolio mutation, order generation, real data ingestion, external
dependencies, ML, LLM, or trading behavior.

Files changed in this phase:

- `src/algotrader/research/replay.py`
- `tests/unit/test_research_replay.py`
- `docs/deterministic_core.md`
- `docs/project_checkpoint.md`

Implementation summary: `algotrader.research.replay` adds frozen, slotted
`SyntheticReplayPoint` and `SyntheticReplaySnapshot` metadata dataclasses plus
`build_synthetic_replay_snapshot(...)`. A replay point pairs an existing
`AsofObservation` with a synthetic `Decimal` value. A snapshot records the
existing `ResearchFixtureManifest`, one plain as-of date, the available replay
points, and close-to-close simple returns from the available values.

Replay behavior: snapshot construction validates the manifest and points,
delegates observation availability filtering to `iter_asof_available(...)`,
preserves original chronological order and available point object identity, and
delegates multi-point return construction to `close_to_close_returns(...)`.
Zero or one available point is allowed and produces an empty returns tuple.

Validation behavior: the package rejects malformed manifests, malformed point
sequences, non-`AsofObservation` point observations, non-`Decimal` point values,
`bool`, `datetime`, date subclass, and non-date as-of values, duplicate or
unordered observation dates through the existing as-of validation, and
available value sequences that violate the existing return-construction
validation such as non-positive prior values.

Serialization behavior: `SyntheticReplaySnapshot.to_dict()` returns
JSON-compatible primitive metadata only. It includes `manifest.to_dict()`,
serializes `asof_date`, `observation_date`, and `available_after` as
`YYYY-MM-DD` strings, serializes point values and returns as strings, uses
available point dictionaries with deterministic key ordering where practical,
and adds no `from_dict()` in this phase.

Tests added in `tests/unit/test_research_replay.py` cover successful snapshot
construction, as-of/no-lookahead filtering, return construction from available
values, zero/one available point behavior, immutable tuple outputs,
deterministic serialization shape, manifest serialization inclusion,
Decimal-string and ISO-date serialization, malformed manifest rejection,
malformed point rejection, non-Decimal rejection, invalid as-of date rejection,
duplicate/unordered observation-date rejection, input identity preservation,
input sequence non-mutation, serialized-list non-sharing, and AST guardrails
against forbidden dependencies, I/O, network, broker/runtime, data-library,
strategy, signal/evaluator, portfolio, ML, LLM, and trading behavior.

Verification for this phase:

- `python -m pytest tests/unit/test_research_replay.py` -> 29 passed
- `python -m pytest tests/unit/test_asof.py` -> 30 passed
- `python -m pytest tests/unit/test_return_construction.py` -> 30 passed
- `python -m pytest tests/unit/test_fixture_manifest.py` -> 48 passed
- `python -m pytest tests/unit/test_dependency_direction.py` -> 9 passed
- `python -m pytest` -> 921 passed, 4 skipped

Normal pytest remains offline and credential-free under the default network
guard. This phase adds no real data, ingestion, backtesting engine,
signal/evaluator behavior, broker/runtime behavior, portfolio mutation, order
generation, ML/LLM usage, or trading behavior.

## Phase 39 Synthetic Replay Summary Metrics

Phase 39 adds a tiny deterministic metrics layer for existing synthetic replay
snapshots. The layer is descriptive only: it summarizes snapshot metadata and
does not add benchmark comparison, strategy validation, signal/evaluator
behavior, backtesting, broker/runtime behavior, portfolio mutation, order
generation, real data handling, ML, LLM, or trading behavior.

Files changed in this phase:

- `src/algotrader/research/replay_metrics.py`
- `tests/unit/test_replay_metrics.py`
- `docs/deterministic_core.md`
- `docs/project_checkpoint.md`

Implementation summary: `algotrader.research.replay_metrics` adds the frozen,
slotted `SyntheticReplaySummary` dataclass plus
`summarize_synthetic_replay_snapshot(...)`. The helper requires a
`SyntheticReplaySnapshot` and reads only `snapshot.available_points` and
`snapshot.returns`.

Summary metric behavior: zero available points produce `point_count=0`,
`return_count=0`, and `None` for starting value, ending value, cumulative
simple return, min return, max return, and mean return. One available point
reports the first/last value as both starting and ending values while leaving
return-derived metrics as `None`. Snapshots with returns report return count,
minimum return, maximum return, arithmetic mean return, and cumulative simple
return as ending divided by starting, minus one.

Serialization behavior: `SyntheticReplaySummary.to_dict()` returns
JSON-compatible primitive metadata only, with deterministic key ordering where
practical. Count fields remain integers, Decimal fields serialize as strings,
and `None` remains `None`. The serialized payload contains no raw data, file
contents, credentials, broker/account/order fields, runtime state, benchmark
comparison, or strategy claims.

Validation behavior: direct summary construction rejects malformed count
fields, `bool` count values, negative counts, and non-Decimal/non-`None`
metric fields. The summarizer rejects malformed snapshots and inconsistent
snapshots that contain returns without available point values. The summary is
frozen and slotted, and summarization does not mutate the snapshot, point
tuple, return tuple, or contained points.

Tests added in `tests/unit/test_replay_metrics.py` cover zero, one, and
multiple available point summaries; return count; starting and ending values;
cumulative simple return; min, max, and mean returns; Decimal precision
preservation; deterministic `to_dict()` shape; Decimal-string serialization;
`None` serialization; immutability; direct dataclass validation; malformed
snapshot rejection; non-mutation of snapshots and points; and AST guardrails
against forbidden dependencies, I/O, network, broker/runtime, data-library,
benchmark, strategy, signal/evaluator, portfolio, ML, LLM, and trading
behavior.

Verification for this phase:

- `python -m pytest tests/unit/test_replay_metrics.py` -> 25 passed
- `python -m pytest tests/unit/test_research_replay.py` -> 29 passed
- `python -m pytest tests/unit/test_asof.py` -> 30 passed
- `python -m pytest tests/unit/test_return_construction.py` -> 30 passed
- `python -m pytest tests/unit/test_fixture_manifest.py` -> 48 passed
- `python -m pytest tests/unit/test_dependency_direction.py` -> 9 passed
- `python -m pytest` -> 946 passed, 4 skipped

Normal pytest remains offline and credential-free under the default network
guard. This phase adds no real data, ingestion, benchmark comparison,
backtesting engine, signal/evaluator behavior, broker/runtime behavior,
portfolio mutation, order generation, ML/LLM usage, or trading behavior.

## Phase 40 Synthetic Research Result Package

Phase 40 adds a tiny deterministic result package for existing synthetic replay
snapshots and their descriptive summary metrics. The package is metadata-only:
it combines already-built snapshot metadata with a computed summary and does
not add benchmark comparison, strategy validation, signal/evaluator behavior,
backtesting, broker/runtime behavior, portfolio mutation, order generation,
real data handling, ML, LLM, or trading behavior.

Files changed in this phase:

- `src/algotrader/research/replay_result.py`
- `tests/unit/test_replay_result.py`
- `docs/deterministic_core.md`
- `docs/project_checkpoint.md`

Implementation summary: `algotrader.research.replay_result` adds the frozen,
slotted `SyntheticResearchResult` dataclass plus
`build_synthetic_research_result(...)`. The helper requires a
`SyntheticReplaySnapshot`, computes a `SyntheticReplaySummary` via
`summarize_synthetic_replay_snapshot(...)`, and preserves the original
snapshot object identity.

Result behavior: a synthetic research result contains exactly the original
snapshot and its descriptive summary. Direct construction with a valid snapshot
and summary is supported, and the dataclass is immutable and slotted. The
builder and dataclass do not mutate the snapshot, available points, manifest,
returns tuple, or summary.

Serialization behavior: `SyntheticResearchResult.to_dict()` returns
JSON-compatible primitive metadata only, with deterministic key ordering where
practical. The payload contains exactly nested `snapshot.to_dict()` and
`summary.to_dict()` output. Snapshot and summary Decimal values remain
string-serialized through those existing nested serializers. The serialized
payload contains no raw data files, credentials, broker/account/order/fill
fields, runtime state, benchmark comparison, strategy approval, profitability
claim, or trading-readiness claim.

Validation behavior: `build_synthetic_research_result(...)` rejects malformed
snapshots before summarizing. Direct dataclass construction rejects malformed
snapshots and malformed summaries, ensuring `snapshot` is a
`SyntheticReplaySnapshot` and `summary` is a `SyntheticReplaySummary`.

Tests added in `tests/unit/test_replay_result.py` cover successful result
construction from a snapshot; summary computation from the snapshot; snapshot
identity preservation; direct construction with valid snapshot and summary;
malformed snapshot rejection; malformed summary rejection; immutability;
non-mutation of snapshot, points, manifest, returns, and summary; deterministic
`to_dict()` shape; nested snapshot serialization; nested summary serialization;
Decimal-string serialization through nested serializers; absence of strategy,
profitability, backtest, approval, broker/runtime, portfolio, order, credential,
and trading fields in serialized output; and AST guardrails against forbidden
dependencies, I/O, network, broker/runtime, data-library, benchmark, strategy,
signal/evaluator, portfolio, ML, LLM, and trading behavior.

Verification for this phase:

- `python -m pytest tests/unit/test_replay_result.py` -> 18 passed
- `python -m pytest tests/unit/test_replay_metrics.py` -> 25 passed
- `python -m pytest tests/unit/test_research_replay.py` -> 29 passed
- `python -m pytest tests/unit/test_asof.py` -> 30 passed
- `python -m pytest tests/unit/test_return_construction.py` -> 30 passed
- `python -m pytest tests/unit/test_fixture_manifest.py` -> 48 passed
- `python -m pytest tests/unit/test_dependency_direction.py` -> 9 passed
- `python -m pytest` -> 964 passed, 4 skipped

Normal pytest remains offline and credential-free under the default network
guard. This phase adds no real data, ingestion, benchmark comparison,
backtesting engine, signal/evaluator behavior, broker/runtime behavior,
portfolio mutation, order generation, ML/LLM usage, strategy validation, or
trading behavior.

## Phase 41 Synthetic Research Workflow Builder

Phase 41 adds a thin deterministic workflow helper for building a complete
metadata-only synthetic research result from a `ResearchFixtureManifest`,
synthetic replay points, and an explicit as-of date. The workflow composes the
existing replay snapshot builder with the existing research-result builder and
does not add duplicate replay, summary, or result-construction logic.

Files changed in this phase:

- `src/algotrader/research/workflow.py`
- `tests/unit/test_research_workflow.py`
- `docs/deterministic_core.md`
- `docs/project_checkpoint.md`

Implementation summary: `algotrader.research.workflow` adds
`build_synthetic_research_workflow_result(...)`. The helper delegates snapshot
construction to `build_synthetic_replay_snapshot(...)`, then delegates result
construction and summary computation to `build_synthetic_research_result(...)`.
It returns a `SyntheticResearchResult` and preserves manifest, observation, and
available replay point identity where the existing builders preserve it.

Workflow behavior: the helper accepts only metadata-only synthetic inputs,
applies existing no-lookahead as-of filtering through the replay builder, uses
available points only for return construction, allows empty input sequences
where replay allows them, and returns valid zero-point or one-point results
with empty returns and the existing summary semantics.

Validation behavior: malformed manifests, malformed replay points, invalid
as-of dates, duplicate observation dates, unordered observation dates, and
invalid return-construction values are rejected by the existing validated
builders. Plain `date` as-of values are required; `datetime`, bool, non-date
values, and date subclasses are rejected through the delegated replay
validation.

Serialization behavior: no new serialization type was added.
`SyntheticResearchResult.to_dict()` remains the serialization path. Nested
manifest, snapshot, and summary serializers continue to provide deterministic
JSON-compatible metadata, and Decimal values remain serialized as strings.

Tests added in `tests/unit/test_research_workflow.py` cover successful
workflow construction; returned result type; snapshot construction; summary
computation; delegated-builder equivalence; no-lookahead as-of filtering;
returns from available points only; empty, zero-available, and one-available
point behavior; nested `to_dict()` serialization; Decimal-string
serialization; forbidden serialized fields; malformed manifest rejection;
malformed point rejection; invalid as-of date rejection; duplicate and
unordered observation rejection through existing validation; invalid value
rejection through return construction; non-mutation of manifests, point
sequences, observations, values, result payloads, snapshots, and summaries; and
AST guardrails against forbidden dependencies, I/O, network, broker/runtime,
data-library, benchmark, strategy, signal/evaluator, portfolio, ML, LLM, and
trading behavior.

Verification for this phase:

- `python -m pytest tests/unit/test_research_workflow.py` -> 23 passed
- `python -m pytest tests/unit/test_replay_result.py` -> 18 passed
- `python -m pytest tests/unit/test_replay_metrics.py` -> 25 passed
- `python -m pytest tests/unit/test_research_replay.py` -> 29 passed
- `python -m pytest tests/unit/test_asof.py` -> 30 passed
- `python -m pytest tests/unit/test_return_construction.py` -> 30 passed
- `python -m pytest tests/unit/test_fixture_manifest.py` -> 48 passed
- `python -m pytest tests/unit/test_dependency_direction.py` -> 9 passed
- `python -m pytest` -> 987 passed, 4 skipped

Normal pytest remains offline and credential-free under the default network
guard. This phase adds no real data, ingestion, benchmark comparison,
backtesting engine, signal/evaluator behavior, broker/runtime behavior,
portfolio mutation, order generation, ML/LLM usage, strategy validation, or
trading behavior.

## Phase 42 External Research Intake Workflow

Phase 42 adds a small metadata-only intake contract for external research
outputs so QuantConnect, vectorbt, notebooks, Perplexity, Claude/Gemini,
papers, manual notes, and other exploratory sources can be recorded as
advisory inputs without becoming trusted strategy validation, production
dependencies, or trading-path behavior.

Files changed in this phase:

- `src/algotrader/research/external_intake.py`
- `tests/unit/test_external_intake.py`
- `docs/deterministic_core.md`
- `docs/project_checkpoint.md`

Implementation summary: `algotrader.research.external_intake` adds
`ExternalResearchIntake`, a frozen slotted dataclass with exactly source name,
source type, strategy name, summary, universe, timeframe, assumptions,
limitations, evidence links, creation date, and `advisory_only` metadata. The
module also exposes `EXTERNAL_RESEARCH_SOURCE_TYPES` for the allowed
source-type vocabulary.

Intake behavior: source types are limited to `quantconnect`, `vectorbt`,
`notebook`, `perplexity`, `claude`, `gemini`, `paper`, `manual`, and `other`.
All scalar strings are stripped and required to be non-empty. Universe,
assumptions, limitations, and evidence links are copied into immutable tuples,
and `advisory_only` must be exactly `True`.

Serialization/deserialization behavior: `to_dict()` emits deterministic
JSON-compatible primitive metadata only, with tuples serialized as lists and
`created_at` serialized as `YYYY-MM-DD`. `from_dict(...)` rejects non-dict
payloads, unknown fields, missing fields, malformed dates, non-list serialized
tuple fields, unsafe advisory flags, and any payload that violates normal
construction validation.

Validation behavior: the contract rejects unknown source types, empty strings,
single-string tuple payloads, malformed tuple entries, `datetime`, bool,
non-date, and date-subclass creation dates, and non-advisory content such as
result metrics, benchmark-comparison claims, broker/account/order/fill/runtime
state, order instructions, position sizing, capital allocation, credentials,
approval status, profitability claims, validation claims, and trading-readiness
claims. It also rejects unknown payload fields such as broker/order identifiers
instead of storing them.

Tests added in `tests/unit/test_external_intake.py` cover valid construction;
all allowed source types; unknown source-type rejection; `advisory_only`
strictness; frozen/slotted behavior; tuple conversion, immutability, and
non-mutation of input sequences; empty string rejection; malformed tuple-value
rejection; plain `date` enforcement; deterministic `to_dict()` shape; from-dict
round trip; ISO date serialization/restoration; non-dict payload rejection;
unknown-field rejection; missing-field rejection; malformed-date rejection;
payload list non-sharing; forbidden field/content guardrails; exact metadata
field shape; absence of trading-path/result attributes; and AST guardrails
against forbidden dependencies, I/O, network, broker/runtime, data-library,
benchmark, signal/evaluator, portfolio, ML, LLM, result-metric, credential, and
trading behavior.

Verification for this phase:

- `python -m pytest tests/unit/test_external_intake.py` -> 58 passed
- `python -m pytest tests/unit/test_dependency_direction.py` -> 9 passed
- `python -m pytest` -> 1045 passed, 4 skipped

Normal pytest remains offline and credential-free under the default network
guard. This phase adds no real data, ingestion, benchmark comparison,
backtesting engine, signal/evaluator behavior, broker/runtime behavior,
portfolio mutation, order generation, ML/LLM runtime usage, strategy
validation, or trading behavior.

## Phase 43 Research Intake + Synthetic Workflow Consolidation

Phase 43 adds a small consolidation checkpoint confirming that the external
advisory intake path and the deterministic synthetic local workflow path remain
separate metadata-only research routes that can coexist without crossing into
strategy approval, profitability, benchmark, order, runtime, portfolio, signal,
backtest, real-data, ML, LLM, or trading behavior.

Files changed in this phase:

- `tests/unit/test_research_intake_workflow_boundary.py`
- `docs/deterministic_core.md`
- `docs/project_checkpoint.md`

Boundary behavior confirmed: `ExternalResearchIntake` remains advisory-only and
is not a `SyntheticResearchResult`; `SyntheticResearchResult` is not an
`ExternalResearchIntake`; external intake rejects strategy approval,
profitability, benchmark-comparison, order-instruction, position-sizing, and
trading-readiness claims; and synthetic workflow output serializes only
snapshot/summary metadata without approval, profitability, or trading fields.

Tests added in `tests/unit/test_research_intake_workflow_boundary.py` cover
external advisory source types, mutual contract separation, coexistence in one
research package, metadata-only synthetic output fields, and AST guardrails for
the external intake plus synthetic manifest/as-of/replay/summary/result/workflow
path. The guardrails reject broker/runtime/scheduler/portfolio/signal/evaluator/
backtest/real-data imports, pandas, numpy, yfinance, vectorbt, QuantConnect,
network clients, ML libraries, LLM runtimes, I/O calls, network calls, vendor
downloads, and trading/order calls.

Verification for this phase:

- `python -m pytest tests/unit/test_research_intake_workflow_boundary.py` -> 21 passed
- `python -m pytest tests/unit/test_external_intake.py` -> 58 passed
- `python -m pytest tests/unit/test_research_workflow.py` -> 23 passed
- `python -m pytest tests/unit/test_replay_result.py` -> 18 passed
- `python -m pytest tests/unit/test_dependency_direction.py` -> 9 passed
- `python -m pytest` -> 1066 passed, 4 skipped

Normal pytest remains offline and credential-free under the default network
guard. This phase adds no real data, ingestion, benchmark comparison,
backtesting engine, signal/evaluator behavior, broker/runtime behavior,
portfolio mutation, order generation, ML/LLM runtime usage, strategy
validation, profitability claim, or trading behavior.

## Next Recommended Steps

Keep avoiding real Alpaca SDK work until explicitly approved.

Safe next tasks include:

- future Codex prompts that reference
  `docs/agent_context/codex_operating_context.md` plus only the relevant phase
  docs
- broader docs-only research or planning updates when they are low-risk,
  code-free, and preserve all safety gates
- use `docs/design/phase31_research_track_next_action_plan.md` as the
  research-track roadmap
- easier-data candidate evaluation while keeping S05 in backlog, using
  `docs/design/phase32_s05_public_documentation_verification_sweep.md` and
  `docs/design/phase32_s05_public_documentation_only_feasibility_decision.md`
  plus
  `docs/design/phase32_s05_non_exact_proxy_reproduction_boundary.md` as
  cautious routing context plus
  `docs/design/phase32_s05_proxy_route_selection_boundary.md` as the
  route-selection boundary and
  `docs/design/phase32_s05_route_neutral_proxy_dataset_requirements_boundary.md`
  as the requirements boundary plus
  `docs/design/phase32_s05_proxy_source_shortlist_and_backlog_routing.md` as
  the current backlog/easier-data routing decision; preserve the owner decision
  to avoid vendor/source contact for now, preserve S01 and S03 as limited
  negative-control support only, preserve S08 as methodology-only PIT support,
  preserve S05 as limited candidate-evidence planning only, keep all proxy
  source categories unselected, and avoid provider choice, acquisition, schema
  design, reproduction approval, validation, or implementation approval
- docs-only methodology and no-lookahead/as-of review for the Phase 33
  selected broad-ETF moving-average candidate is now recorded in Phase 33 Step
  5; the grouped universe and benchmark/cash proxy shortlist boundary is now
  recorded in Phase 33 Step 6; the data-source terms/license review boundary
  is now recorded in Phase 33 Step 7; the final source shortlist decision
  boundary is now recorded in Phase 33 Step 8; and the data storage/fixture
  policy boundary is now recorded in Phase 33 Step 9; the moving-average
  evidence source package is now recorded in Phase 33 Step 10; the
  moving-average evidence intake plan is now recorded in Phase 33 Step 11; the
  externally collected evidence source normalization is now recorded in Phase
  33 Step 12; and the primary evidence text intake normalization is now
  recorded in Phase 33 Step 13; and the primary citation verification
  normalization is now recorded in Phase 33 Step 14; and the Faber limited
  formal evidence review is now recorded in Phase 33 Step 15; and the
  `ETF-ACADEMIC-001` limited formal evidence review is now recorded in Phase
  33 Step 16; and the broad ETF methodology evidence synthesis boundary is now
  recorded in Phase 33 Step 17; and the broad ETF reproduction readiness
  checklist is now recorded in Phase 33 Step 18; and the broad ETF source,
  universe, and benchmark decision-readiness boundary is now recorded in Phase
  33 Step 19; and the broad ETF return-construction boundary is now recorded
  in Phase 33 Step 20; and the broad ETF no-lookahead/as-of protocol boundary
  is now recorded in Phase 33 Step 21; and the broad ETF
  survivorship/inception/delisting boundary is now recorded in Phase 33 Step
  22; and the broad ETF cash/benchmark return treatment boundary is now
  recorded in Phase 33 Step 23. The next docs-only route should pause Phase 33
  before code and prefer a cost/friction assumptions boundary because cash and
  benchmark comparability still depends on whether out-of-market cash earns
  return, whether idle cash is modeled, and whether transaction costs, spreads,
  slippage, taxes, fund expenses, opening gaps, turnover, and rebalance
  friction are included, excluded, or deferred without approving a benchmark,
  cash proxy, source, return construction, reproduction, implementation, or
  trading use. Do not proceed to a fixture policy approval boundary,
  benchmark/cash approval boundary, source/universe/benchmark approval
  boundary, no-lookahead/as-of approval boundary,
  survivorship/inception/delisting approval boundary, reproduction protocol,
  evaluator route, or implementation route while keeping all evidence, source,
  universe, benchmark, cash proxy, cash-rate series, data, return
  construction, no-lookahead/as-of protocol, survivorship/inception/delisting
  policy, methodology, validation, implementation, secondary shortlist, and
  S05 backlog statuses non-approving
- Phase 34 Step 1 records the external research integration boundary; Phase 34
  Step 2 now records the intake checklist that Step 1 recommended, while
  keeping Perplexity, Claude/Gemini, Codex, QuantConnect, vectorbt, notebooks,
  vendor/public data, external research, spreadsheets, and ad hoc analysis
  advisory-only and outside normal pytest, production dependencies, validated
  artifacts, validated signal definitions, and trading-path behavior
- Phase 34 Step 2 records the external research artifact intake checklist, and
  Phase 34 Step 3 records the notebook/prototype policy boundary that followed
  it, while keeping notebooks, vectorbt prototypes, spreadsheets, screenshots,
  manual observations, hosted outputs, vendor/public data notes, and LLM
  outputs exploratory or advisory only and outside normal pytest, production
  dependencies, validated artifacts, validated signal definitions, and
  trading-path behavior
- Phase 34 Step 3 now records that notebook/prototype policy boundary; Phase
  33 Step 9 ties those exploratory outputs back to data storage and fixture
  controls while keeping notebooks, prototype scripts, vectorbt experiments,
  QuantConnect outputs, spreadsheets, CSV extracts, charts, external reports,
  and copied snippets exploratory only and outside normal pytest, production
  dependencies, validated artifacts, validated signal definitions, and
  trading-path behavior
- Phase 42 now provides a code-level external research intake metadata
  contract for those advisory outputs. Future external research notes can use
  `ExternalResearchIntake` only as metadata and must still avoid raw data,
  ingestion, benchmark comparison, backtesting, evaluator logic, production
  dependencies, strategy approval, and trading-path behavior
- Phase 43 confirms that `ExternalResearchIntake` and the deterministic
  synthetic workflow result path coexist as separate metadata-only research
  routes, with external advisory inputs kept distinct from synthetic local
  replay results and both paths kept outside runtime, vendor, backtest,
  evaluator, portfolio, order, ML/LLM, and trading behavior
- Phase 44 adds a deterministic local historical price snapshot loader for
  ignored CSV files such as `.data/research_snapshots/`; it validates local
  daily OHLCV rows and deterministic fingerprints only, while keeping raw data
  out of git and avoiding network access, vendor dependencies, ingestion
  pipelines, benchmark comparison, backtesting, signal/evaluator behavior,
  broker/runtime behavior, portfolio mutation, order generation, ML/LLM
  runtime usage, strategy validation, and trading behavior
- Phase 45 adds a pinned local price snapshot manifest that records source
  metadata, file hashes, snapshot fingerprints, date ranges, row counts,
  adjustment policy, local-only status, normal-pytest ineligibility, and
  limitations without reading files, committing raw data, adding persistence,
  connecting to vendor/data dependencies, or introducing ingestion, benchmark,
  backtest, signal/evaluator, broker/runtime, portfolio, order, ML/LLM,
  strategy validation, or trading behavior
- Phase 46 adds a minimal deterministic daily backtest harness over already
  loaded `HistoricalPriceSnapshot` data and precomputed `DailyExposure` flags,
  producing a local Decimal equity curve, no-lookahead return application,
  simple fee/slippage costs, basic descriptive metrics, and primitive
  serialization while adding no real data, file I/O, network access,
  ingestion pipeline, benchmark comparison, signal/evaluator behavior,
  broker/runtime behavior, portfolio engine, order generation, ML/LLM runtime,
  strategy validation, or trading behavior
- Phase 47 adds a deterministic research-only SMA-200 exposure generator over
  already loaded `HistoricalPriceSnapshot` data, emitting one immutable
  `DailyExposure` per bar date with `Decimal("0")` before 200 bars and
  `Decimal("1")` only when the current adjusted close is strictly greater than
  the trailing 200-day adjusted-close mean including that current bar; the
  helper preserves the daily backtest's previous-exposure no-lookahead rule and
  adds no real data, file I/O, network access, ingestion pipeline, benchmark
  comparison, production signal/evaluator behavior, broker/runtime behavior,
  portfolio engine, order generation, ML/LLM runtime, strategy validation,
  profitability claim, or trading behavior
- Phase 48 adds the first local SPY SMA-200 research-run script and markdown
  log template. The path requires an explicit ignored CSV snapshot, records
  only metadata, hashes, assumptions, rule text, aggregate SMA-200 and
  same-snapshot buy-and-hold baseline metrics, limitations, and an advisory
  verdict, emits a sibling deterministic JSON sidecar when a markdown output
  path is supplied, labels returns as price-return unless the snapshot
  adjustment policy is explicitly `total_return`, and keeps raw data,
  network/API/vendor access, external benchmark comparison, production
  signal/evaluator behavior, broker/runtime behavior, portfolio engine
  behavior beyond the existing local equity curve, order generation, ML/LLM
  runtime usage, strategy validation, profitability claims, and trading
  behavior out of scope
- Phase 49 adds an explicitly gated Alpaca Market Data daily snapshot fetcher
  under `scripts/research/`. The path requires `--allow-network`, explicit
  start/end dates, explicit output path, environment-only credentials, ignored
  `.data/research_snapshots/` output by default, `--overwrite` before
  replacement, strict OHLCV/date/volume response validation, and a local
  SHA-256 report. It writes only the existing snapshot-loader CSV columns and
  labels the `adjusted_close = close` fallback as an adjustment-policy
  limitation without claiming total-return accuracy. It adds no `src`
  ingestion pipeline, `alpaca-py`, broker/trading endpoint call,
  account/position/order/fill access, order submission, scheduler/runtime
  service, production signal/evaluator, portfolio engine, ML/LLM runtime,
  strategy validation, profitability claim, or trading behavior; normal pytest
  remains offline and credential-free with mocked unit payloads only
- Phase 50 adds local-only environment setup hygiene: `.env` and `.env.*`
  remain ignored while `.env.example` is tracked with placeholders only, and
  `scripts/dev/load_env.ps1` can load a repo-root `.env` into a local
  PowerShell process without printing values. Local usage is manual: copy the
  example to `.env`, fill values only in that ignored file, and run
  `. .\scripts\dev\load_env.ps1` from a PowerShell session that needs those
  process environment variables. This adds no automatic runtime dotenv
  loading, dependencies, network calls, broker/trading behavior, production
  credential flow, or weakened pytest network/credential gates
- Phase 51 updates the gated Alpaca Market Data daily snapshot fetcher with an
  explicit `--feed` option defaulting to `iex`, preserving `sip` and
  `delayed_sip` as opt-in request feeds and adding metadata-only feed reporting.
  HTTP 403 failures now return credential-redacted troubleshooting guidance for
  invalid/stale keys, missing market-data permissions, unavailable selected
  feeds, and trying `--feed iex` for basic access, while normal pytest remains
  mocked, offline, and credential-free
- Phase 44B makes local research adjustment semantics explicit: unknown
  adjustment snapshots default to price-return reporting, `adjusted_close` is
  labeled as a close-price fallback when true adjusted semantics are not
  confirmed, JSON sidecars carry the same basis/provenance labels, and
  unsupported policies or unusable total-return adjusted-close values fail
  before report output
- Phase 45 - External SPY Price Parity Check adds a local-only
  `scripts/research/check_spy_price_parity.py` utility that compares
  close-price calendar-year returns between an explicit local snapshot CSV and
  an explicit manually supplied reference CSV, prints an advisory markdown
  table with basis-point differences, optionally writes only that markdown
  report, and adds no raw external data, automatic fetch, vendor abstraction,
  normal-pytest network call, data-directory dependency, strategy validation,
  total-return construction, dividend/corporate-action handling, or trading
  recommendation
- Phase 45 - AI Operating Brief / Candidate Dossier Foundation adds the
  `algotrader.advisory.operating_brief` metadata contracts for future advisory
  briefs: immutable candidate dossiers with explicit uncertainty and failure
  modes, strategy eligibility status, risk authority status, and operating
  brief bundles. The contracts normalize sequence inputs to tuples, reject
  malformed identifiers and non-string advisory entries, keep research/watchlist
  labels safe without actionability, and require explicit strategy and risk
  support before paper, live-probe, or live-authorized labels can be represented
  in a brief. This adds no generator, AI prompt layer, LLM/API call,
  market-data path, strategy scorer, evaluator, dashboard, broker access,
  order/fill/execution/OMS/account/position/portfolio behavior, runtime,
  scheduler, persistence, strategy validation claim, trading recommendation, or
  capital-layer mutation
- Phase 46 - Advisory Operating Brief Serialization / Display Snapshot adds
  deterministic `to_dict()` methods for the existing advisory contracts. The
  serializers emit primitive JSON-compatible dictionaries only, convert advisory
  labels to strings, tuple fields to lists, nested advisory objects through
  their own deterministic dictionaries, and operating brief dates to ISO
  `YYYY-MM-DD` strings while preserving dossier/status ordering and leaving
  source objects unchanged. This adds no markdown generator, dashboard, AI
  prompt layer, brief generator, market-data path, strategy scoring, evaluator,
  alternate constructor, persistence, broker access, order/fill/execution/OMS,
  account/position/portfolio behavior, runtime, scheduler, LLM/API call,
  network call, strategy validation claim, trading recommendation, or
  capital-layer mutation
- Phase 47 - Deterministic Advisory Operating Brief Markdown Renderer adds
  `render_operating_brief_markdown(...)` for already constructed
  `OperatingBrief` instances. It formats existing advisory metadata into a
  stable Markdown snapshot with the as-of date, advisory-only disclaimer,
  candidate dossiers, strategy eligibility, risk authority, uncertainty,
  failure modes, blocking reasons, limitations, and deterministic non-claims
  while preserving source ordering and leaving source objects unchanged. This
  adds no AI brief generation, prompt layer, market-data ingestion, candidate
  discovery, strategy scoring, recommendation logic, dashboard code,
  persistence, broker access, order/fill/execution/OMS,
  account/position/portfolio behavior, signal/evaluator behavior, runtime,
  scheduler, LLM/API call, network call, strategy validation claim, trading
  recommendation, or capital-layer mutation
- Phase 48 - Advisory Operating Brief Board Summary adds
  `build_operating_brief_board_summary(...)` for already constructed
  `OperatingBrief` instances. It derives immutable display metadata with the
  as-of date, source-order candidate ids grouped by advisory label, counts for
  every label including empty groups, paper/live-probe/live-authorized board
  ids, live-authorization source status, existing strategy and risk blockers,
  uncertainty, failure modes, source limitations, and advisory-only non-claims.
  The summary serializes to deterministic primitive JSON-compatible
  dictionaries and leaves source objects unchanged. This adds no AI brief
  generation, prompt layer, market-data ingestion, candidate generation,
  strategy scoring, ranking, recommendation logic, dashboard code,
  persistence, broker access, order/fill/execution/OMS,
  account/position/portfolio behavior, signal/evaluator behavior, runtime,
  scheduler, LLM/API call, network call, strategy validation claim, trading
  recommendation, or capital-layer mutation
- Phase 49 - Advisory Board Summary Markdown Renderer adds
  `render_operating_brief_board_summary_markdown(...)` for already constructed
  `OperatingBriefBoardSummary` instances. It formats the summary as a stable
  Markdown board with the as-of date, advisory-only disclaimer, every advisory
  label count, grouped candidate ids, research queue, watchlist,
  paper-eligible ids, live-probe-eligible ids, live-authorized source metadata,
  strategy and risk blockers, uncertainty, failure modes, limitations, source
  summary non-claims, and fixed board non-claims while preserving summary
  ordering and leaving source objects unchanged. This adds no AI brief
  generation, prompt layer, market-data ingestion, candidate generation,
  strategy scoring, ranking, recommendation logic, dashboard code, persistence,
  broker access, order/fill/execution/OMS, account/position/portfolio behavior,
  signal/evaluator behavior, runtime, scheduler, LLM/API call, network call,
  strategy validation claim, trading recommendation, or capital-layer mutation
- Phase 50 - Advisory Layer Review Hardening adds review-response regression
  tests for advisory board count completeness, repeated serialization and
  Markdown byte stability, non-actionable label authority despite live-authorized
  strategy/risk source statuses, dataclass repr safety, and safety-boundary
  terms. Direct `OperatingBriefBoardSummary` construction now rejects negative
  `candidate_counts_by_label` values without changing builder-generated
  summaries. This adds no new advisory feature, strategy mandate integration,
  synthetic fixtures, dashboard display adapter, AI/LLM generation,
  market-data ingestion, persistence, candidate discovery, scoring, ranking,
  recommendation, broker/order/fill/execution/OMS, account/position/portfolio
  behavior, runtime, scheduler, network call, trading behavior, or capital-layer
  mutation
- Phase 51 - Synthetic Advisory Operating Brief Example Fixture adds
  `tests.fixtures.advisory_operating_brief` as a canonical local-only synthetic
  example for future advisory operating-brief tests and documentation. The
  fixture builds one deterministic `OperatingBrief`, derives its
  `OperatingBriefBoardSummary`, and pins literal expected Markdown for both
  renderers. It covers all five advisory labels, uncertainty, failure modes,
  research questions, limitations, non-claims, blocked/paper/live-probe/live
  strategy and risk metadata, constructor-gated live authorization, and a
  watchlist candidate whose source label remains authoritative despite more
  permissive strategy/risk metadata. The focused tests pin deterministic
  serialization, primitive JSON-compatible output, exact Markdown, source
  immutability, safety terms, and AST dependency guardrails. This adds no AI
  brief generation, market-data ingestion, candidate generation, strategy
  scoring, ranking, recommendation logic, dashboard code, persistence,
  broker/order/fill/execution/OMS, account/position/portfolio behavior,
  runtime, scheduler, LLM/API call, network call, market-data provider access,
  trading behavior, or capital-layer mutation
- Phase 52 - Governance Status Snapshot Contracts adds
  `algotrader.governance.status_snapshot` as a deterministic, metadata-only
  source-contract layer for future advisory inputs. `StrategyMandateSnapshot`
  records strategy mandate, evidence, paper, live-probe, live-authorization,
  validated artifact, requirement, blocker, limitation, uncertainty,
  failure-mode, and non-claim metadata. `RiskAuthoritySnapshot` records
  risk-side paper, live-probe, live, kill-switch, policy, constraint,
  requirement, blocker, limitation, uncertainty, failure-mode, and non-claim
  metadata. Both contracts are frozen/slotted, accept only explicit plain
  dates, normalize sequence fields to tuples, serialize to primitive
  JSON-compatible dictionaries, enforce deterministic paper/probe/live gates,
  and are covered by focused construction, serialization, source immutability,
  safety surface, and AST dependency guardrail tests. This adds no advisory
  adapter, AI brief generation, market-data ingestion, candidate discovery,
  strategy scoring, ranking, recommendation logic, dashboard code,
  persistence, broker/order/fill/execution/OMS, account/position/portfolio
  behavior, runtime, scheduler, LLM/API call, network call, market-data
  provider access, trading behavior, or capital-layer mutation
- Phase 53 - Governance Snapshot to Advisory Status Adapter adds
  `algotrader.advisory.governance_status_adapter` as a tiny deterministic
  downstream adapter from the Phase 52 governance snapshots into the existing
  advisory status contracts. The strategy adapter accepts an explicit
  candidate id and maps `StrategyMandateSnapshot` into
  `StrategyEligibilityStatus` through the existing advisory constructor. The
  risk adapter accepts an explicit candidate id and maps `RiskAuthoritySnapshot`
  into `RiskAuthorityStatus` through the existing advisory constructor. The
  adapter preserves only supported advisory fields, carries evidence refs from
  validated research and signal definition ids, does not infer candidate
  identity from strategy/mandate/authority ids, does not upgrade authority
  beyond snapshot booleans, and lets existing advisory validation reject
  inconsistent conversions. Focused tests cover type safety, candidate-id
  validation, constructor usage, tuple ordering, deterministic conversion and
  serialization, source non-mutation, safety surface, and dependency direction.
  This adds no full `OperatingBrief` assembly, `ResearchCandidateDossier`
  construction, `AdvisoryLabel` inference, AI brief generation, market-data
  ingestion, candidate discovery, strategy scoring, ranking, recommendation
  logic, dashboard code, persistence, broker/order/fill/execution/OMS,
  account/position/portfolio behavior, runtime, scheduler, LLM/API call,
  network call, market-data provider access, trading behavior, or capital-layer
  mutation
- Phase 54 - Advisory Candidate Dossier Source Snapshot adds
  `algotrader.advisory.candidate_snapshot.CandidateDossierSnapshot` as a
  deterministic metadata-only upstream source contract for future
  `ResearchCandidateDossier` adaptation. It records candidate source metadata,
  source refs, proposed advisory label, label source/rationale,
  strategy/mandate refs, universe/evidence refs, uncertainty, failure modes,
  next questions, limitations, and non-claims. The contract is frozen/slotted,
  accepts only explicit plain dates, normalizes sequences to tuples, serializes
  to primitive JSON-compatible dictionaries, validates source type and label
  source allowlists, and gates elevated labels to deterministic/reviewed
  sources. `live_authorized` requires strategy id, mandate id, evidence refs,
  and explicit non-claims; `live_probe_eligible` requires strategy id, mandate
  id, and explicit non-claims; `paper_eligible` requires strategy id and
  explicit non-claims. Focused tests cover construction, validation,
  serialization, source immutability, safety terms, and AST guardrails keeping
  the module independent from governance, broker/execution/portfolio/runtime,
  LLM/network/market-data, persistence, notebooks, file I/O, clocks, random,
  and subprocess dependencies. This adds no `OperatingBrief` assembly,
  `ResearchCandidateDossier` construction, candidate discovery, AI generation,
  market-data ingestion, scoring, ranking, recommendation logic, dashboard,
  persistence, broker/order/fill/account/position/portfolio behavior, runtime,
  scheduler, LLM/API call, network call, trading behavior, or capital-layer
  mutation
- Phase 55 - Candidate Snapshot to Research Candidate Dossier Adapter adds
  `algotrader.advisory.candidate_dossier_adapter` as a pure deterministic
  bridge from already-validated `CandidateDossierSnapshot` metadata into the
  existing `ResearchCandidateDossier` contract. The adapter accepts only
  candidate dossier snapshots, rejects other inputs with `ValidationError`,
  and uses the existing dossier constructor as the validation boundary. It
  preserves only fields supported by the current dossier: candidate id, title,
  summary, the exact proposed advisory label, uncertainty factors, failure
  modes, next questions, and limitations, with tuple ordering unchanged. It
  does not infer, upgrade, downgrade, or rewrite labels; source ids, source and
  label metadata, strategy/mandate refs, universe/evidence refs, and
  non-claims remain unsupported by the current dossier contract and are not
  invented in the output. Focused tests cover research/watchlist/elevated-label
  conversion, constructor usage, deterministic repeated conversion and
  primitive serialization, source immutability, snapshot-enforced elevated
  label restrictions, safety surface, and AST guardrails. This adds no
  `OperatingBrief` assembly, strategy/risk status construction, governance
  import in the adapter, candidate discovery, AI generation, market-data
  ingestion, scoring, ranking, recommendation logic, dashboard, persistence,
  broker/order/fill/account/position/portfolio behavior, runtime, scheduler,
  LLM/API call, network call, trading behavior, or capital-layer mutation
- Phase 56 - Advisory Operating Brief Assembly from Prepared Parts adds
  `algotrader.advisory.operating_brief_assembly` as a pure deterministic
  assembler for already-built advisory objects. It accepts an explicit plain
  `date`, prepared `ResearchCandidateDossier` objects, prepared
  `StrategyEligibilityStatus` objects, and prepared `RiskAuthorityStatus`
  objects; normalizes iterables to tuples; preserves ordering; rejects empty
  dossier inputs, duplicate candidate ids, orphan statuses, and mismatched
  exposed `as_of_date` values; requires matching prepared statuses for
  elevated labels; and calls the existing `OperatingBrief` constructor as the
  final validation boundary. It does not consume snapshots, call adapters,
  infer labels, create dossiers/statuses, discover candidates, or upgrade
  research/watchlist labels from permissive statuses. Focused tests cover
  successful assembly, constructor usage, deterministic equality, type and
  candidate-id validation, elevated-label gating, non-actionable label
  authority, serialization/rendering/summary compatibility, safety surface,
  and AST guardrails. This adds no snapshot-to-brief assembly, AI generation,
  market-data ingestion, scoring, ranking, recommendation logic, dashboard,
  persistence, broker/order/fill/account/position/portfolio behavior, runtime,
  scheduler, LLM/API call, network call, trading behavior, or capital-layer
  mutation
- Phase 57 - Synthetic Advisory Pipeline Fixture adds
  `tests.fixtures.advisory_pipeline` as a deterministic test-only fixture that
  explicitly composes the existing advisory pieces: candidate snapshots to
  `ResearchCandidateDossier`, governance snapshots to prepared strategy/risk
  statuses with explicit candidate ids, prepared parts to `OperatingBrief`, and
  the existing board summary plus Markdown renderers to pinned literal output.
  The fixture uses only synthetic identifiers/prose, fixed date `2026-01-16`,
  all five advisory labels, research-only without strategy/risk support,
  watchlist-only with more permissive optional support, and one valid
  live-authorized path with matching prepared support. Focused tests cover
  deterministic construction, source non-mutation, label preservation,
  ordering, elevated-label gates, non-actionable label authority, primitive
  serialization, exact Markdown rendering, safety content, and AST guardrails.
  This adds no production snapshot-to-brief assembler, production pipeline
  function, AI generation, market-data ingestion, candidate discovery, scoring,
  ranking, recommendation logic, dashboard, persistence,
  broker/order/fill/account/position/portfolio behavior, runtime, scheduler,
  LLM/API call, network call, trading behavior, or capital-layer mutation
- Phase 58 - Advisory Pipeline Review Hardening adds review-response
  regression guardrails only. Tests now pin governance-to-advisory import
  direction, advisory dataclass field-name safety, hash-seed determinism for
  `OperatingBrief.to_dict()`, `OperatingBriefBoardSummary.to_dict()`, and both
  Markdown renderers, compact JSON round-trip determinism for brief and board
  summary payloads, reverse-direction rejection when elevated dossier labels
  lack matching prepared strategy/risk support, and continued non-actionable
  label authority despite permissive support metadata. A docstring clarifies
  that `live_authorized` is advisory metadata only. This changes no validation
  behavior and adds no production snapshot-to-brief assembler, OperatingBrief
  generation service, candidate discovery, label inference, adapter, renderer,
  assembly behavior, market-data ingestion, scoring, ranking, recommendation
  logic, dashboard, persistence, broker/order/fill/account/position/portfolio
  behavior, runtime, scheduler, LLM/API call, network call, trading behavior,
  or capital-layer mutation
- Phase 59 - SPY SMA-200 Research Runner Mechanics Hardening returns to the
  existing local-only research runner without promoting any strategy. The
  runner report now includes deterministic SMA mechanics metadata in Markdown
  and JSON: the fixed 200-observation window, minimum observations, fully
  formed SMA observation count, insufficient-observation status, and
  same-close metadata with previous-exposure backtest timing. It also emits
  explicit non-claims for advisory/research-only use, not validated evidence,
  no trading recommendation, no approved signal, no live or paper trading
  authority, and no broker/order/fill/account/position/portfolio/allocation/
  target-weight behavior. Focused tests use only synthetic tmp CSV fixtures,
  not `.data/` or real SPY data, and pin input validation, insufficient-data
  reporting, no-lookahead SMA mechanics, adjustment/return-basis honesty,
  byte-identical Markdown/JSON output, JSON payload field safety, and AST
  guardrails excluding broker/execution/portfolio/runtime, network/http/socket,
  LLM/API, market-data provider, notebook/vectorbt, persistence, random,
  subprocess, environment, scoring, ranking, recommendation,
  candidate-discovery, order/fill, and portfolio behavior. This changes report
  metadata only and adds no advisory expansion, source or data approval, real
  market data, strategy validation, profitability claim, signal definition,
  evaluator behavior, trading recommendation, live/paper trading authority,
  broker/order/fill/execution/OMS behavior, account/position/portfolio
  behavior, runtime/scheduler behavior, LLM/API call, network call,
  market-data ingestion, scoring, ranking, recommendation, or
  candidate-discovery behavior
- Phase 60 - SPY SMA-200 Synthetic Output Contract Snapshot adds one canonical
  synthetic regression test for the local research runner output contract. The
  test builds a deterministic `tmp_path` CSV, runs the runner with explicit
  synthetic input, explicit Markdown output, an explicit custom JSON sidecar
  path, fixed local assumptions, and `allow_outside_data_dir=True`, then pins
  stable Markdown sections, JSON top-level keys, exact SMA mechanics payload,
  unknown-adjustment/price-return honesty, non-claims, forbidden payload-field
  safety, raw-row/path exclusion, and byte-identical Markdown/JSON output
  across repeated runs. The runner now accepts optional
  `json_output_path`/`--json-output` while preserving the default sibling JSON
  sidecar when only Markdown output is supplied; validation requires a Markdown
  output path, a `.json` suffix, non-`.data/` output, and a sidecar path
  separate from the Markdown report. This adds no profitability validation,
  strategy approval, signal definition, advisory expansion, source or data
  approval, real market data, market-data ingestion, broker/order/fill/
  execution/OMS behavior, account/position/portfolio/allocation/target-weight
  behavior, runtime/scheduler behavior, LLM/API call, network call, scoring,
  ranking, recommendation, candidate-discovery behavior, paper/live behavior,
  trading authority, or trading behavior
- Phase 61 - SPY SMA-200 Synthetic Metric Semantics Contract pins exact metric
  semantics for the local research runner on deterministic synthetic CSVs only.
  Tests now cover a 205-row flat series where the SMA fully forms,
  insufficient observations are false, close never exceeds the trailing SMA,
  strategy exposure and turnover remain zero, strategy and buy-and-hold price
  returns remain zero, buy-and-hold exposure remains one, unknown adjustment
  stays `price_return`, and repeated Markdown/JSON outputs are byte-identical
  without raw rows or local paths. A controlled breakout series proves that the
  first close above the SMA changes exposure under the existing same-close rule
  but earns no same-bar strategy profit under the previous-exposure backtest
  convention; only the following bar reflects prior exposure, and revised
  future closes do not alter earlier exposure. This changes no runner behavior
  or validation behavior and adds no profitability validation, strategy
  approval, signal definition, advisory expansion, source or data approval,
  real market data, market-data ingestion, broker/order/fill/execution/OMS
  behavior, account/position/portfolio/allocation/target-weight behavior,
  runtime/scheduler behavior, LLM/API call, network call, scoring, ranking,
  recommendation, candidate-discovery behavior, paper/live behavior, trading
  authority, or trading behavior
- Phase 62 - Synthetic Moving-Average Research Mechanics Kernel adds a small
  reusable `algotrader.research.moving_average` contract for synthetic-only
  offline mechanics. It introduces frozen/slotted metadata dataclasses for
  dated positive `Decimal` values and per-row moving-average observations, plus
  a pure trailing simple moving-average builder that normalizes iterable inputs
  to immutable tuple output, preserves ordering, rejects malformed dates,
  values, windows, duplicate dates, unordered dates, empty input, and malformed
  entries, computes only from prior/current observations, marks the first
  `window - 1` rows unavailable, and treats equality as not above. Focused
  tests pin window 1, window 200 synthetic input, Decimal arithmetic,
  repeated-call determinism, no input mutation, no-lookahead future-value
  behavior, and AST/field guardrails excluding broker/order/fill/execution/
  portfolio/runtime/LLM/network/market-data/notebook/vectorbt/persistence/
  filesystem/pandas/numpy/scoring/ranking/recommendation/candidate-discovery/
  signal/evaluator/trading behavior. This does not modify the SPY runner and
  adds no strategy validation, approved signal, source/universe/benchmark
  approval, real data, broad ETF implementation, advisory integration,
  dashboard, AI brief generation, paper/live behavior, trading authority, or
  trading behavior
- Phase 63 - Synthetic Moving-Average Exposure State Kernel adds a small
  reusable `algotrader.research.moving_average_exposure` contract for
  synthetic-only offline exposure metadata. It introduces a frozen/slotted
  `MovingAverageExposureState` dataclass and a pure
  `build_previous_exposure_states` builder over already-built
  `MovingAverageObservation` rows. The builder normalizes iterable input to
  immutable tuple output, preserves ordering, rejects empty input, malformed
  entries, duplicate dates, unordered dates, and mixed windows, and uses a
  previous-row convention where the first `current_exposure` is zero, each
  row's `next_exposure` comes only from the current observation, and the next
  row's `current_exposure` reflects the prior row's `next_exposure`.
  Unavailable moving averages, equality, below-average rows, and missing
  above-average metadata all produce zero `next_exposure`; above-average rows
  produce one. Focused tests pin direct validation, previous-exposure
  mechanics, no-lookahead behavior, repeated-call determinism, source
  non-mutation, immutable output, and AST/field guardrails excluding broker/
  order/fill/execution/portfolio/runtime/LLM/network/market-data/notebook/
  vectorbt/persistence/filesystem/pandas/numpy/scoring/ranking/recommendation/
  candidate-discovery/signal/evaluator/trading behavior. This does not modify
  the SPY runner, compute returns, validate a strategy, define a signal, add
  source approval, real data, broad ETF implementation, advisory integration,
  dashboard, AI brief generation, paper/live behavior, trading authority, or
  trading behavior
- Phase 64 - Synthetic Exposure-Applied Return Kernel adds a small reusable
  `algotrader.research.exposure_returns` contract for synthetic-only offline
  return metadata. It introduces a frozen/slotted
  `ExposureReturnObservation` dataclass and a pure
  `build_exposure_applied_returns` builder over ordered `MovingAverageInput`
  values and `MovingAverageExposureState` rows. The builder normalizes
  iterable inputs to immutable tuple output, preserves ordering, rejects empty
  inputs, malformed entries, length mismatches, date mismatches, duplicate
  dates, and unordered dates, marks the first row return unavailable, and uses
  Decimal-only close-to-close simple returns. Later rows apply the row's
  `current_exposure`, so zero exposure produces zero exposure return, one
  exposure preserves the asset return, and a same-row breakout cannot create
  same-row exposure-applied return. Focused tests pin direct validation,
  previous-exposure mechanics, Decimal preservation, negative asset returns,
  no-lookahead future changes, repeated-call determinism, source non-mutation,
  immutable output, and AST/field guardrails excluding broker/order/fill/
  execution/portfolio/runtime/LLM/network/market-data/notebook/vectorbt/
  persistence/filesystem/pandas/numpy/scoring/ranking/recommendation/
  candidate-discovery/signal/evaluator/trading behavior. This does not modify
  the SPY runner, compute cumulative returns, equity curves, performance
  metrics, costs, slippage, fees, benchmarks, portfolio accounting,
  allocation, target weights, position sizing, orders, fills, signals,
  execution plans, validate a strategy, define a signal, add advisory
  integration, source approval, real data, broad ETF implementation, paper/live
  behavior, trading authority, or trading behavior
- Phase 65 - Synthetic Cumulative Exposure Return Path Kernel adds a small
  reusable `algotrader.research.cumulative_returns` contract for synthetic-only
  offline cumulative return metadata from already-built
  `ExposureReturnObservation` rows. It introduces a frozen/slotted
  `CumulativeReturnObservation` dataclass and a pure
  `build_cumulative_return_path` builder that normalizes iterable input to
  immutable tuple output, preserves ordering, rejects empty input, malformed
  entries, duplicate dates, unordered dates, malformed return fields,
  non-Decimal cumulative values, and bypassed malformed exposure-return rows,
  and uses Decimal-only cumulative return arithmetic. The first row remains a
  zero cumulative baseline while preserving source return availability and
  return fields. Later available rows compound asset cumulative return from
  `asset_return` and exposure cumulative return from `exposure_return`;
  unavailable rows preserve prior cumulative values without inventing returns.
  Focused tests pin direct validation, flat and two-return paths,
  previous-exposure breakout mechanics, no-lookahead future changes, Decimal
  preservation, repeated-call determinism, source non-mutation, immutable
  output, and AST/field guardrails excluding broker/order/fill/execution/
  portfolio/runtime/LLM/network/market-data/notebook/vectorbt/persistence/
  filesystem/pandas/numpy/equity/PnL/Sharpe/CAGR/drawdown/alpha/beta/
  benchmark/scoring/ranking/recommendation/candidate-discovery/signal/
  evaluator/trading behavior. This does not modify the SPY runner, compute
  equity curves, starting capital, PnL, Sharpe, CAGR, drawdown, volatility,
  alpha, beta, benchmark comparisons, win rate, performance scores, costs,
  slippage, fees, benchmarks, portfolio accounting, allocation, target weights,
  position sizing, orders, fills, signals, execution plans, validate a strategy,
  define a signal, add advisory integration, source approval, real data, broad
  ETF implementation, paper/live behavior, trading authority, or trading
  behavior
- Phase 66 - Synthetic Cumulative Return Path Summary adds a small reusable
  `algotrader.research.cumulative_return_summary` contract for deterministic
  research-only summaries over already-built `CumulativeReturnObservation`
  rows. It introduces a frozen/slotted `CumulativeReturnPathSummary` dataclass
  and pure `summarize_cumulative_return_path` builder that normalizes iterable
  input, preserves source ordering for first/last/final-row semantics, rejects
  empty input, non-cumulative-return entries, duplicate dates, unordered dates,
  and malformed direct construction, and copies the last row's asset and
  exposure cumulative return values without recomputing the path. The summary
  records only observation dates, total and available/unavailable row counts,
  final asset and exposure cumulative returns, a has-available-returns flag,
  and research-only limitations/non-claims. Its deterministic `to_dict()`
  emits dates as `YYYY-MM-DD`, Decimals as strings, tuples as lists, and
  counts/booleans as primitives. Focused tests pin constructor validation,
  iterable normalization, source non-mutation, flat and mixed path summaries,
  full synthetic moving-average to cumulative-path integration, previous-
  exposure/no-same-row visibility through the final exposure cumulative value,
  JSON round-tripping, and AST/field guardrails excluding broker/order/fill/
  execution/portfolio/runtime/LLM/network/market-data/notebook/vectorbt/
  persistence/filesystem/pandas/numpy/equity/PnL/Sharpe/CAGR/drawdown/alpha/
  beta/benchmark/scoring/ranking/recommendation/candidate-discovery/signal/
  evaluator/trading behavior. This does not modify the SPY runner, compute
  Sharpe, CAGR, drawdown, volatility, alpha, beta, benchmark comparisons, win
  rate, performance scores, equity curves, starting capital, PnL, costs,
  slippage, fees, benchmark returns, portfolio accounting, allocation, target
  weights, position sizing, orders, fills, signals, execution plans,
  optimization metrics, validate a strategy, define a signal, add advisory
  integration, source approval, real data, broad ETF implementation, paper/live
  behavior, trading authority, or trading behavior
- Phase 67 - Synthetic Moving-Average Replay Package adds a small reusable
  `algotrader.research.moving_average_replay` contract for deterministic
  research-only replay packaging over the existing synthetic mechanics chain:
  `MovingAverageInput`, `MovingAverageObservation`,
  `MovingAverageExposureState`, `ExposureReturnObservation`,
  `CumulativeReturnObservation`, and `CumulativeReturnPathSummary`. It
  introduces a frozen/slotted `MovingAverageReplayPackage` dataclass and pure
  `build_moving_average_replay_package` builder that composes the existing
  moving-average, previous-exposure, exposure-return, cumulative-return, and
  summary kernels in order. The package records replay id, plain as-of date,
  moving-average window, immutable tuple outputs for every mechanics stage, the
  summary, and replay-level limitations/non-claims. Direct construction
  validates sequence types, matching lengths, matching ordered dates, matching
  windows, summary/path consistency, required non-claims, and exact agreement
  with the existing kernels. Its deterministic `to_dict()` emits dates as
  `YYYY-MM-DD`, Decimals as strings, tuples as lists, and nested mechanics rows
  as primitive dictionaries. Focused tests pin constructor validation, kernel
  call ordering, source non-mutation, repeated-call equality, flat and breakout
  paths, JSON round-tripping, no-lookahead behavior, and AST/field guardrails
  excluding broker/order/fill/execution/portfolio/runtime/LLM/network/
  market-data/notebook/vectorbt/persistence/filesystem/pandas/numpy/equity/
  PnL/Sharpe/CAGR/drawdown/alpha/beta/benchmark/scoring/ranking/
  recommendation/candidate-discovery/signal/evaluator/trading behavior. This
  does not modify the SPY runner, compute performance metrics beyond summary
  final cumulative path values and counts, validate a strategy, define a
  signal, add advisory integration, source approval, real data, broad ETF
  implementation, paper/live behavior, trading authority, or trading behavior
- Phase 68 - Synthetic Moving-Average Replay JSON Contract Fixture freezes the
  existing Phase 67 `MovingAverageReplayPackage.to_dict()` output by content
  with two committed compact JSON fixtures:
  `tests/fixtures/moving_average_replay_contract_flat.json` and
  `tests/fixtures/moving_average_replay_contract_breakout.json`. The flat
  fixture uses only deterministic positive Decimal values and locks zero final
  asset and exposure cumulative returns. The breakout fixture uses only
  synthetic values that form an SMA, break above it, and prove previous-row
  exposure behavior through later rows. Contract tests byte-compare compact
  insertion-order JSON, round-trip fixture bytes through `json.loads`/
  `json.dumps`, assert primitive-only serialized values, and reject object
  repr artifacts. Review-hardening tests now pin direct
  `MovingAverageObservation` construction validation, strict below-SMA exit
  behavior, equality-after-true exposure reset behavior, exact current reason
  strings, Decimal-context stability for the exact fixture path, and the
  cumulative-return/simple-return validation asymmetry. Replay and summary
  non-claims explicitly state that exposure is a `0/1` research indicator and
  not allocation, target weight, position size, or a portfolio instruction.
  This does not modify the SPY runner, add strategy validation, define a
  signal, add performance metrics, use real data, add broker/order/fill/
  portfolio/runtime/LLM/network/market-data behavior, or add scoring, ranking,
  recommendation, candidate-discovery, advisory, paper/live, or trading
  behavior
- Phase 69 - SPY Runner / Moving-Average Replay Synthetic Parity Probe adds
  tests-only parity coverage between the existing local SPY SMA-200 research
  runner and the generic `MovingAverageReplayPackage` mechanics. The new tests
  use deterministic synthetic CSV files under `tmp_path`, run the SPY runner
  with explicit synthetic input, Markdown output, JSON output,
  `allow_outside_data_dir=True`, and unknown adjustment policy, and build the
  generic replay package from the same CSV close values with `window=200`.
  Coverage spans a flat 205-row series, a controlled breakout series, and an
  insufficient-observation series. It compares stable mechanics fields: SMA
  window behavior, fully formed SMA counts, previous-exposure/no-same-row
  return behavior, exposure-applied returns, final asset/exposure cumulative
  returns where the runner exposes equivalent metrics, deterministic repeated
  output, research-only non-claims, forbidden-field absence, external-source
  marker absence, and the normal offline, credential-free pytest boundary. This
  does not refactor the SPY runner, adapt it to the generic kernel, change
  generic research kernels, validate a strategy, define a signal, add a
  backtesting engine, add broad ETF implementation, add performance metrics,
  ingest real data, read `.data/`, add broker/order/fill/portfolio/runtime/
  LLM/network/market-data behavior, or add scoring, ranking, recommendation,
  candidate-discovery, advisory, paper/live, or trading behavior
- Phase 70 - SPY SMA-200 Runner Generic Replay Integration Probe performs a
  narrow output-preserving refactor of the local SPY runner. The runner now
  builds a `MovingAverageReplayPackage` from loaded snapshot adjusted-close
  values via `MovingAverageInput` and
  `build_moving_average_replay_package(..., window=200)`, then converts replay
  `next_exposure` states back into the existing `DailyExposure` shape. Public
  Markdown and JSON sidecar keys remain unchanged, unknown adjustment remains
  `unknown` / `price_return`, explicit JSON sidecar behavior remains unchanged,
  and synthetic `tmp_path` coverage keeps normal pytest offline and free of
  `.data/` or real market-data dependencies. The existing `run_daily_backtest`
  path still owns the runner-specific output metric envelope and fee/slippage
  behavior because the generic replay package intentionally does not model
  costs, max drawdown, exposure ratio, turnover, or ending-equity presentation.
  This does not change generic research kernels, validate a strategy, define a
  signal, add a backtesting engine, add cost/slippage support to the generic
  kernel, add performance metrics, ingest real data, read `.data/`, add
  advisory integration, add broker/order/fill/account/position/portfolio/
  allocation/target-weight/runtime/LLM/network/market-data behavior, or add
  scoring, ranking, recommendation, candidate-discovery, paper/live, or trading
  behavior
- Phase 71 - SPY Runner Generic Replay Integration Guardrails adds focused
  regression coverage around the Phase 70 integration. Tests now prove the SPY
  exposure builder calls the generic moving-average replay package with
  adjusted-close `MovingAverageInput` values and `window=200`, then converts
  replay `next_exposure` states back into `DailyExposure`. Nonzero fee/slippage
  coverage pins that runner-specific `run_daily_backtest` metrics are not
  replaced by generic no-cost replay summary values. The canonical synthetic
  report path pins the JSON assumptions payload, sidecar top-level keys,
  explicit and default JSON sidecar behavior, absence of raw generic replay
  payloads and runtime/dataclass repr leaks, unknown-adjustment `price_return`
  honesty, research-only non-claims, safety-field absence, and AST import
  boundaries for the allowed local research modules. This adds no generic
  kernel changes, advisory expansion, strategy validation, source approval, real
  data, broker/order/fill/portfolio/runtime/LLM/network/market-data behavior,
  scoring, ranking, recommendation, candidate-discovery, paper/live, or trading
  behavior
- Phase 72 - Research Scope Candidate Snapshot Contracts adds a small
  metadata-only `algotrader.research.research_scope` module for future broad
  ETF / moving-average research planning. It defines frozen/slotted candidate
  dataclasses for data sources, universes, benchmarks, and cash proxies, plus
  an optional `ResearchScopeSnapshot` bundling one or more of each candidate
  type. The contracts reject `approval_state="approved"`, normalize sequence
  fields to tuples, reject malformed strings and malformed candidate entries,
  reject duplicate ids inside each snapshot candidate group, require explicit
  non-approval non-claims, and emit deterministic primitive dictionaries with
  dates as `YYYY-MM-DD` strings. Focused tests cover construction, tuple
  normalization, allowed-value validation, plain-date enforcement, duplicate
  detection, primitive JSON serialization, byte-identical compact JSON
  round-tripping, no real ticker requirement, safety field absence, and AST
  guardrails. This adds no SPY runner changes, generic moving-average kernel
  changes, advisory expansion, governance expansion, source/universe/benchmark/
  cash proxy approval, methodology approval, parameter approval, data
  acquisition path, strategy validation, signal/evaluator behavior, backtest,
  broad ETF implementation, real data ingestion, broker/order/fill/portfolio/
  runtime/LLM/network/market-data behavior, scoring, ranking, recommendation,
  candidate-discovery, paper/live, or trading behavior
- Phase 73 - Synthetic Broad ETF Research Scope Fixture adds a deterministic
  test/documentation fixture in `tests.fixtures.research_scope` using the Phase
  72 candidate contracts. It builds one synthetic broad ETF-style
  `ResearchScopeSnapshot` as of `2026-01-18`, with one synthetic source
  candidate, one `broad_etf_candidate` universe containing only synthetic asset
  ids, one synthetic benchmark candidate, one synthetic cash proxy candidate,
  explicit blockers, limitations, required follow-up, and the required
  research-scope non-claims. The fixture also pins the expected primitive
  dictionary and compact JSON payload. Focused tests cover construction,
  nested candidate types, non-approved approval states, exact serialization,
  JSON round-tripping, repeated determinism, no real ETF tickers, no raw market
  data, no URLs, credentials, or real vendor/source identifiers, no runtime or
  selection fields, no affirmative approval/authority claims, and AST
  guardrails excluding broker/execution/portfolio/runtime/network/LLM/
  market-data/dataframe/random/file-I/O dependencies. This adds no source,
  universe, benchmark, cash proxy, methodology, parameter, or data acquisition
  approval; no strategy validation, signal/evaluator behavior, backtest, broad
  ETF strategy implementation, real data ingestion, SPY runner change, generic
  moving-average kernel change, advisory/governance expansion, broker/order/
  fill/portfolio/runtime/LLM/network/market-data behavior, scoring, ranking,
  recommendation, candidate-discovery, paper/live, or trading behavior
- Phase 74 - Research Methodology / Parameter Candidate Snapshot Contracts adds
  a small metadata-only `algotrader.research.research_methodology` module for
  future broad ETF / moving-average research planning. It defines frozen/slotted
  candidate dataclasses for methodologies and parameter sets, plus an optional
  `ResearchMethodologyScopeSnapshot` bundling one or more of each candidate
  type. The contracts reject `approval_state="approved"`, normalize sequence
  fields to tuples, validate allowed candidate type and policy strings, reject
  malformed strings and malformed candidate entries, require positive unique
  moving-average window metadata, reject duplicate ids and orphan parameter-set
  methodology references, require explicit non-approval non-claims, and emit
  deterministic primitive dictionaries with dates as `YYYY-MM-DD` strings.
  Focused tests cover construction, tuple normalization, allowed-value
  validation, plain-date enforcement, duplicate detection, methodology linkage,
  primitive JSON serialization, byte-identical compact JSON round-tripping, no
  real ticker requirement, safety field absence, no approval/authority claims,
  and AST guardrails. This adds no SPY runner changes, generic moving-average
  kernel changes, advisory expansion, governance expansion, methodology
  approval, parameter approval, source/universe/benchmark/cash proxy approval,
  data acquisition path, strategy validation, signal/evaluator behavior,
  backtest, broad ETF implementation, real data ingestion, broker/order/fill/
  portfolio/runtime/LLM/network/market-data behavior, scoring, ranking,
  recommendation, candidate-discovery, paper/live, or trading behavior
- Phase 75 - Synthetic Broad ETF Methodology Scope Fixture adds a deterministic
  test/documentation fixture in `tests.fixtures.research_methodology` using the
  Phase 74 methodology and parameter candidate contracts. It builds one
  candidate-only `ResearchMethodologyScopeSnapshot` as of `2026-01-19`, with
  one `moving_average_trend_candidate` methodology candidate, one
  `single_window_candidate` parameter-set candidate containing only the
  synthetic 200-window metadata value, and a link to the Phase 73 synthetic
  broad ETF research-scope fixture by synthetic scope id only. The fixture
  includes explicit blockers, limitations, required follow-up, required
  methodology non-claims, and pinned primitive dictionary and compact JSON
  payloads. Focused tests cover construction, nested candidate types,
  non-approved approval states, methodology-to-parameter linkage,
  synthetic-scope id linkage, exact serialization, JSON round-tripping,
  repeated determinism, no real ETF tickers, no raw market data, no URLs,
  credentials, or real vendor/source identifiers, no runtime or selection
  fields, no affirmative approval/authority claims, and AST guardrails
  excluding broker/execution/portfolio/runtime/network/LLM/market-data/
  dataframe/random/file-I/O dependencies. This adds no methodology, parameter,
  source, universe, benchmark, cash proxy, or data acquisition approval; no
  trading rule, strategy validation, signal/evaluator behavior, backtest, broad
  ETF strategy implementation, real data ingestion, SPY runner change, generic
  moving-average kernel change, advisory/governance expansion, broker/order/
  fill/portfolio/runtime/LLM/network/market-data behavior, scoring, ranking,
  recommendation, candidate-discovery, paper/live, or trading behavior
- Phase 76 - Synthetic Broad ETF Research Planning Package Fixture adds a
  deterministic test/documentation package fixture in
  `tests.fixtures.research_planning` using the Phase 73 synthetic research
  scope fixture and Phase 75 synthetic methodology scope fixture. It returns a
  primitive dictionary as of `2026-01-20` with a fixed synthetic planning
  package id, embedded primitive research-scope and methodology-scope payloads,
  limitations, and explicit non-claims. Focused tests cover construction,
  fixed dates, methodology linked-scope reference to the synthetic research
  scope id, non-approved candidate states, required non-claims, exact compact
  JSON serialization, byte-identical JSON round-tripping, primitive-only
  payload safety, no real ETF tickers, no raw market data, no URLs,
  credentials, vendor/source identifiers, or account ids, no runtime or
  selection fields, no affirmative approval/authority claims, and AST
  guardrails excluding broker/execution/portfolio/runtime/network/LLM/
  market-data/dataframe/random/file-I/O dependencies. This adds no source,
  universe, benchmark, cash proxy, methodology, parameter, or data acquisition
  approval; no strategy validation, signal/evaluator behavior, broad ETF
  strategy implementation, real data ingestion, SPY runner change, generic
  moving-average kernel change, advisory/governance expansion, broker/order/
  fill/portfolio/runtime/LLM/network/market-data behavior, scoring, ranking,
  recommendation, candidate-discovery, paper/live, or trading behavior
- Phase 77 - Research Planning Review Hardening consolidates duplicated
  research-planning validators into internal
  `algotrader.research._planning_validation` helpers while preserving the
  public scope and methodology contract surfaces. Methodology non-claims now
  explicitly include `not evidence approval`, with the synthetic methodology
  and planning fixture compact JSON updated only for that added non-claim.
  Focused tests add allowed-state completeness for candidate-only, blocked,
  and deferred states across scope and methodology contracts; rejection of
  `approved`, ` approved `, and `Approved`; parameter/methodology linkage
  ordering regression coverage; local primitive planning-package linked-scope
  mismatch failure coverage; a return/returns substring guard around
  `return_construction_policy`; and AST guardrails for the new internal helper.
  The planning package remains a primitive dictionary only. This adds no
  source, universe, benchmark, cash proxy, methodology, parameter, or evidence
  approval; no strategy validation, signal/evaluator behavior, broad ETF
  strategy implementation, real data ingestion, SPY runner change, generic
  moving-average kernel change, advisory/governance expansion, broker/order/
  fill/portfolio/runtime/LLM/network/market-data behavior, scoring, ranking,
  recommendation, candidate-discovery, paper/live, or trading behavior
- Phase 78 - Synthetic Planning Fixture Replay Consumer adds
  `tests.fixtures.research_planning_replay` and
  `tests/unit/test_research_planning_replay_fixture.py` as a synthetic-only
  fixture consumer for the Phase 76 primitive planning package. It copies the
  planning metadata, consumes only synthetic ids, `linked_scope_ids`,
  `evidence_refs`, and the single candidate moving-average window, then builds
  an existing moving-average replay package through the public replay builder
  using deterministic synthetic observations. The output remains a primitive
  dict and proves fixture shape usability only. It is not a production planning
  package contract, strategy validation artifact, source/universe/benchmark/
  cash proxy/methodology/parameter/evidence approval, evidence validation,
  trading-readiness claim, signal definition, evaluator, or trading path.
  Focused tests cover deterministic primitive JSON behavior, candidate/blocked/
  deferred approval-state limits, `not evidence approval`, paired synthetic
  linked-scope ids, planning/replay non-mutation, existing replay shape
  preservation, no new replay metrics, no real data, ETF tickers, vendor names,
  URLs, credentials, or market-data paths, and no broker/order/fill/portfolio/
  runtime/LLM/network/market-data/scoring/ranking/recommendation/
  candidate-discovery/signal/evaluator/trading behavior. Normal pytest remains
  offline and credential-free
- Phase 79 - Synthetic Planning Replay Report Shape adds
  `tests.fixtures.research_planning_replay_report` and
  `tests/unit/test_research_planning_replay_report_fixture.py` as a primitive
  synthetic-only report/result fixture around the Phase 78 planning replay
  consumer. It summarizes only synthetic scope ids, `linked_scope_ids`,
  metadata-only `evidence_refs`, methodology non-claims, non-approved planning
  states, the selected synthetic moving-average window, and existing replay
  package shape metadata. It remains fixture-level and non-validating: it does
  not approve any source, universe, benchmark, cash proxy, methodology,
  parameter, or evidence; does not add replay metrics; does not add signal,
  evaluator, or trading behavior; and does not add broker/order/fill/portfolio/
  runtime/LLM/network/market-data behavior. Normal pytest remains offline and
  credential-free
- Phase 81 - Research Planning Fixture Guardrail Consolidation keeps the
  Phase 72-79 synthetic planning/replay/report fixture chain test-only while
  consolidating repeated guardrail assertions into shared test helpers for
  non-approved planning states, primitive JSON shape, negative-term screening,
  metadata-only evidence non-claims, and real ticker/vendor/path/credential
  exclusion. No production code changed, no fixture output semantics changed,
  and normal pytest remains offline and credential-free
- Phase 83 - Broad ETF Data Source Policy / Local Snapshot Readiness Boundary
  adds a documentation-only readiness boundary for future broad ETF source
  paths and local snapshots. It defines candidate source-path categories, local
  snapshot metadata requirements, adjustment/return-basis questions,
  no-lookahead/as-of implications, repository/storage constraints, minimum
  future implementation gates, and explicit non-claims. No source, data,
  universe, benchmark, cash proxy, methodology, parameter, evidence, strategy
  validation, or trading use was approved; no real data was added; no
  production code or tests changed; and normal pytest remains offline and
  credential-free
- Phase 84 - Local Snapshot Manifest Metadata Contract adds a tiny
  deterministic metadata-only `LocalSnapshotManifest` for describing future
  local research snapshots without reading files, hashing files, checking
  paths, ingesting data, or making local snapshots normal-pytest inputs. The
  contract validates plain dates, observation date ordering, conservative
  source/adjustment/return-basis allowlists, lowercase SHA-256 checksum shape,
  immutable tuple metadata, required non-claims, and
  `normal_pytest_eligible=False`; it serializes to and from deterministic
  primitive dictionaries. No source, data, universe, benchmark, cash proxy,
  methodology, parameter, evidence, strategy validation, or trading use was
  approved; no real data or ETF tickers were added; no broker/order/fill/
  portfolio/runtime/LLM/network/market-data/scoring/ranking/recommendation/
  candidate-discovery/signal/evaluator/rendering/trading behavior was added;
  and normal pytest remains offline and credential-free
- Phase 86 - Synthetic Local Snapshot Manifest Fixture adds
  `tests.fixtures.local_snapshot_manifest` as a tiny synthetic-only consumer
  proving `LocalSnapshotManifest` can be constructed, serialized, and
  round-tripped deterministically in normal pytest. No production code changed,
  no real data or local snapshot files were added, and the fixture remains
  metadata-only and non-approving. Normal pytest remains offline and
  credential-free
- Phase 88 - Local Snapshot Return-Basis / As-Of Boundary adds a docs-only
  interpretation boundary for future local snapshot metadata. It defines date
  semantics, adjustment-policy interpretation, return-basis interpretation,
  no-lookahead/as-of risks, future approval gates, and the relationship to the
  metadata-only `LocalSnapshotManifest`. No source or data was approved, no
  production code or tests changed, no real data was added, no manifest-to-
  planning bridge was added, and normal pytest remains offline and
  credential-free
- Phase 89 - Broad ETF Universe / Inception / Survivorship Boundary adds a
  docs-only boundary for future broad ETF universe membership, inception
  eligibility, survivorship and delisting risks, identifier questions,
  no-lookahead universe rules, and minimum future approval gates. No universe
  or ETF tickers were approved, no production code or tests changed, no real
  data was added, and normal pytest remains offline and credential-free
- Phase 90 - Broad ETF Benchmark / Cash Timing Boundary adds a docs-only
  boundary for future benchmark and cash-proxy interpretation. It defines
  benchmark roles, benchmark return-basis requirements, cash proxy roles, cash
  timing/publication risks, benchmark/cash no-lookahead rules, and future
  approval gates. No benchmark or cash proxy was approved, no production code
  or tests changed, no real data was added, and normal pytest remains offline
  and credential-free
- Phase 91 - Broad ETF Cost / Friction Assumptions Boundary adds a docs-only
  boundary for future transaction-cost, spread, slippage, liquidity, turnover,
  rebalance, expense-ratio, tax, and implementation-friction assumptions. No
  cost model or liquidity rule was approved, no production code or tests
  changed, no real data was added, and normal pytest remains offline and
  credential-free
- Phase 93 - Broad ETF Source Evidence Intake Plan adds a docs-only intake
  plan for future review of candidate broad ETF source paths before any local
  snapshot use. It defines candidate source-path categories, required source
  evidence, source-review questions, intake evidence labels, allowed review
  outcomes, forbidden approval outcomes, a starter intake table, and explicit
  non-claims. No source or data was approved, no production code or tests
  changed, no real data was added, and normal pytest remains offline and
  credential-free
- Phase 94 - Broad ETF Source Evidence Normalization adds a docs-only
  normalization of externally discovered broad ETF source-discovery output as
  advisory intake material under the Phase 93 framework. It records candidate
  source paths, separates primary-source needs from secondary/scout
  observations, routes strongest and weaker later-review candidates, and
  records unresolved primary-source questions. No source or data was approved,
  no production code or tests changed, no real data was added, and normal
  pytest remains offline and credential-free
- Phase 95 - Broad ETF Primary Source Verification Normalization adds a
  docs-only normalization of external primary-source verification output for
  Stooq, Alpha Vantage, and FRED as advisory material only. It records reported
  official docs and terms status, unresolved rights and methodology questions,
  candidate confidence, and later-review ordering. No source, data, vendor,
  benchmark, cash proxy, universe, methodology, parameter, evidence,
  return-construction, no-lookahead, cost/friction, liquidity, strategy
  validation, or trading use was approved; no production code or tests changed;
  no real data was added; and normal pytest remains offline and credential-free
- Phase 96 - FRED Benchmark / Cash Rate Normalization Readiness adds a
  docs-only readiness boundary for reviewing FRED as a future benchmark/cash/
  rate source candidate only. It captures candidate use cases, Phase 95
  advisory official-doc findings, unresolved FRED questions, no-lookahead
  risks, future review gates, allowed next steps, and explicit non-claims. No
  FRED series, cash proxy, benchmark, rate source, source, data, universe,
  methodology, parameter, evidence, return-construction, no-lookahead,
  cost/friction, liquidity, strategy validation, or trading use was approved;
  no production code or tests changed; no real data was added; and normal
  pytest remains offline and credential-free
- Phase 97 - FRED Candidate Series Intake Plan adds a docs-only intake plan
  for future review of possible FRED benchmark/cash/rate candidate series. It
  defines candidate series roles, required per-series evidence, intake labels,
  allowed candidate statuses, review questions, a placeholder starter intake
  table, and future approval gates. No FRED series or cash proxy was approved,
  no production code or tests changed, no real data was added, and normal
  pytest remains offline and credential-free
- Phase 98 - FRED Candidate Series Discovery Normalization adds a docs-only
  normalization of externally produced FRED candidate series discovery output
  as advisory intake material under the Phase 97 framework. It records
  candidate series such as TB3MS, TB6MS, EFFR, OBFR, the SOFR family,
  FEDFUNDS, UNRATE, and generic non-official guide/blog references; separates
  reported official source observations from secondary/scout observations;
  routes strongest, context-only, and rejected-for-now candidates; records
  unresolved primary source, ALFRED/vintage, timing, rights, conversion, and
  normal-pytest questions; and recommends a later-review order. No FRED
  series, cash proxy, benchmark, rate source, source, data, universe,
  methodology, parameter, evidence, return-construction, no-lookahead,
  cost/friction, liquidity, strategy validation, or trading use was approved;
  no production code or tests changed; no real data was added; no FRED API
  calls or downloads occurred; and normal pytest remains offline and
  credential-free
- Phase 99 - FRED TB3MS/TB6MS Primary Verification Normalization adds a
  docs-only normalization of externally produced primary-verification output
  for `TB3MS` and `TB6MS` as advisory material only. It records reportedly
  found FRED series pages, FRED data/table pages, ALFRED pages, H.15
  source/release context, units, frequency, seasonal adjustment,
  observation-start metadata, last-updated metadata, vintage notes,
  rights/terms caveats, point-in-time questions, missing/stale questions, and
  discount-basis conversion questions. Both series remain
  `candidate_for_later_series_review`. No FRED series, cash proxy, benchmark,
  rate source, source, data, universe, methodology, parameter, evidence,
  return-construction, no-lookahead, cost/friction, liquidity, strategy
  validation, or trading use was approved; no production code or tests
  changed; no real data was added; no FRED API calls or downloads occurred;
  and normal pytest remains offline and credential-free
- Phase 101 - H.15 Discount-Basis Formula Normalization adds a docs-only
  normalization of externally produced H.15 Treasury bill discount-basis
  formula and convention discovery output as advisory methodology evidence
  only. It records the reported TreasuryDirect bill pricing formula,
  360-day-year and actual-days-to-maturity convention, H.15/FRED
  secondary-market discount-basis classification for `TB3MS` and `TB6MS`,
  monthly-average and FRED transformation uncertainties, daily quote
  construction uncertainties, conversion/compounding risks, point-in-time and
  no-lookahead risks, official source categories found, and a later-review
  recommendation. No formula implementation was added, no conversion method
  was approved, no FRED series or cash proxy was approved, no production code
  or tests changed, no real data was added, no FRED API calls or downloads
  occurred, and normal pytest remains offline and credential-free
- Phase 102 - H.15 Daily Quote / Monthly Averaging Normalization adds a
  docs-only normalization of externally produced H.15 daily quote and monthly
  averaging discovery output as advisory methodology context only. It records
  reported H.15 posting schedule and aggregate averaging findings, daily
  Treasury bill quote-construction gaps, FRED monthly provenance gaps,
  revision/missing/stale uncertainty, point-in-time and no-lookahead risks,
  the unproven relationship to Treasury daily bill-rate descriptions, and a
  later-review recommendation. No averaging implementation was added, no
  formula implementation was added, no conversion method was approved, no FRED
  series or cash proxy was approved, no production code or tests changed, no
  real data was added, no FRED/H.15 API calls or downloads occurred, and normal
  pytest remains offline and credential-free
- Phase 104 - Alpha Vantage Primary Source Verification Normalization adds a
  docs-only normalization of externally produced Alpha Vantage primary-source
  verification output as advisory material only. It records reported official
  API documentation, Terms of Service, support/rate-limit, premium/entitlement,
  and realtime/market-data policy categories; time-series endpoint findings;
  ETF coverage leads; adjustment, dividend, and split findings; survivorship,
  listing-status, timestamp, revision, no-lookahead, terms, licensing, and
  storage caveats; and an unresolved candidate disposition. Alpha Vantage
  remains unresolved. No Alpha Vantage source, data, endpoint, universe,
  benchmark, cash proxy, methodology, parameter, evidence,
  return-construction, no-lookahead, cost/friction, liquidity, strategy
  validation, or trading use was approved; no production code or tests
  changed; no real data was added; no Alpha Vantage API calls or downloads
  occurred; and normal pytest remains offline and credential-free
- Phase 105 - Alpha Vantage Public Docs Gap Normalization adds a docs-only
  normalization of additional externally produced Alpha Vantage public-doc gap
  review output as advisory material only. It records what public docs
  reportedly answer, including endpoint, ETF-symbol, terms, realtime/delayed
  policy, and listing-status leads; what remains unresolved across
  license/storage, ETF/source-quality, adjustment, revision, point-in-time,
  survivorship, and bulk-snapshot feasibility; and the support/legal questions
  needed before any future local snapshot review. Alpha Vantage remains
  unresolved. No Alpha Vantage source, data, endpoint, universe, benchmark,
  cash proxy, methodology, parameter, evidence, return-construction,
  no-lookahead, cost/friction, liquidity, strategy validation, or trading use
  was approved; no production code or tests changed; no real data was added;
  no Alpha Vantage API calls or downloads occurred; and normal pytest remains
  offline and credential-free
- Phase 106 - Stooq Public Docs Gap Normalization adds a docs-only
  normalization of externally produced Stooq public-doc gap review output as
  advisory material only. It records reported public CSV and bulk ASCII or
  Metastock-style download surfaces, listed asset categories including ETF and
  U.S. ETF categories, OHLCV-style availability, archive generation timestamps,
  third-party provider references, adjustment UI controls, unresolved terms
  and storage questions, unresolved schema/source-quality questions,
  unresolved adjustment and point-in-time questions, and an unresolved
  candidate disposition. Stooq remains unresolved. No Stooq source, data,
  download path, universe, benchmark, cash proxy, methodology, parameter,
  evidence, return-construction, no-lookahead, cost/friction, liquidity,
  strategy validation, or trading use was approved; no production code or
  tests changed; no real data was added; no Stooq downloads occurred; and
  normal pytest remains offline and credential-free
- Phase 107 - ETF Source Review Routing Checkpoint adds a docs-only routing
  record after Alpha Vantage, Stooq, and Antigravity review. It records that
  Alpha Vantage and Stooq remain unresolved, that the Antigravity review was
  advisory and read-only, and that the project will not automatically redirect
  to FRED unless a concrete ALFRED or point-in-time need emerges. No Alpha
  Vantage, Stooq, FRED, source, data, endpoint, download path, universe,
  benchmark, cash proxy, methodology, parameter, evidence, return-construction,
  no-lookahead, cost/friction, liquidity, strategy validation, or trading use
  was approved; no production code or tests changed; no real data was added;
  no API calls or downloads occurred; and normal pytest remains offline and
  credential-free
- Phase 108 - Polygon Public Docs Gap Normalization adds a docs-only
  normalization of externally provided Polygon/Massive public-doc and
  public-source verification output as advisory material only. It records
  reported public documentation for aggregates, grouped daily aggregates,
  trades, quotes, splits, dividends, reference tickers, ticker events, flat
  files, API-key requirements, plan/pricing structure, split-adjusted
  aggregates, and Market Data Terms non-redistribution language; unresolved
  license/storage, ETF/source-quality, adjustment, and point-in-time
  questions; comparison to Alpha Vantage and Stooq; and an unresolved
  candidate disposition. Polygon/Massive remains unresolved and non-approved.
  No Polygon, Massive, source, data, endpoint, flat-file path, universe,
  benchmark, cash proxy, methodology, parameter, evidence,
  return-construction, no-lookahead, cost/friction, liquidity, strategy
  validation, or trading use was approved; no production code or tests changed;
  no real data was added; no API calls or downloads occurred; and normal
  pytest remains offline and credential-free
- Phase 109 - ETF Source Candidate Comparison Checkpoint adds a docs-only
  routing comparison of Alpha Vantage, Stooq, and Polygon/Massive after their
  advisory source and public-doc reviews. It records that all candidates remain
  unresolved and non-approved, compares technical surface, documentation,
  terms/storage, adjustment/return-basis, point-in-time/revision,
  survivorship/lifecycle, operational fit, blockers, disposition, and allowed
  next steps, and recommends Polygon/Massive support/legal questions as the
  smallest useful outreach path while keeping Nasdaq Data Link as a reasonable
  external source-review alternative. No Alpha Vantage, Stooq, Polygon,
  Massive, source, data, endpoint, download path, flat file, universe,
  benchmark, cash proxy, methodology, parameter, evidence,
  return-construction, no-lookahead, cost/friction, liquidity, strategy
  validation, or trading use was approved; no production code or tests changed;
  no real data was added; no API calls or downloads occurred; and normal
  pytest remains offline and credential-free
- Phase 110 - Polygon Deep Public Docs Normalization adds a docs-only
  normalization of deeper externally provided Polygon/Massive public-doc
  verification output as advisory material only. It records stronger reported
  public-doc findings around Market Data Terms, individual-use terms,
  redistribution limits, flat-file research/backtesting workflow docs,
  unadjusted flat files, REST adjusted aggregates, reference tickers, active
  as-of and delisted ticker lookup leads, ticker events, ETF profile surfaces,
  and corporate actions while preserving unresolved storage/legal,
  point-in-time, ETF lifecycle, survivorship, adjustment, timestamp, and
  calendar gaps. Polygon/Massive remains unresolved and non-approved, is the
  technically strongest ETF price-source candidate reviewed so far, and may
  support only future candidate-only schema/interface normalization around
  documented shapes. No source or data was approved; no production code or
  tests changed; no real data was added; no API calls or downloads occurred;
  and normal pytest remains offline and credential-free
- Phase 111 - Polygon Schema / Legal Routing Checkpoint adds a docs-only
  routing decision after the deeper Polygon/Massive public-doc review. It
  records that Alpha Vantage, Stooq, Polygon/Massive, and Nasdaq Data Link
  remain unresolved and non-approved; that Polygon/Massive remains the
  strongest technical ETF price-source candidate reviewed so far; and that the
  preferred next route is candidate-only Polygon/Massive schema/interface
  normalization planning only if it remains metadata-only and synthetic-only.
  Terms/legal review remains required before any real Polygon/Massive data use,
  and Nasdaq Data Link primary-source review remains the preferred alternative
  if schema/interface planning is premature. No source or data was approved; no
  production code or tests changed; no real data was added; no API calls or
  downloads occurred; and normal pytest remains offline and credential-free
- Phase 112 - Polygon Candidate Schema / Interface Planning Boundary adds a
  docs-only, candidate-only planning boundary for possible future
  Polygon/Massive data normalization. It identifies candidate surfaces such as
  aggregates, grouped daily aggregates, trades, quotes, reference tickers,
  ticker details, ticker events, splits, dividends, flat files, ETF profile
  surfaces, and possible calendar/session data; records metadata questions,
  cross-surface risks, future implementation gates, and a future synthetic-only
  fixture boundary; and keeps Polygon/Massive unresolved and non-approved. No
  production code or tests changed; no fixtures changed; no real data was
  added; no API calls or downloads occurred; no source, data, endpoint, or
  flat-file approval was added; and normal pytest remains offline and
  credential-free
- Phase 113 - Synthetic Polygon Reference Ticker Fixture adds one tiny
  synthetic-only Polygon/Massive-style reference ticker metadata fixture and a
  focused normal-pytest unit test. The fixture uses primitive placeholder
  values only, no real vendor data, no market-data rows, no API calls or
  downloads, no credentials, and no `.data/` paths. No production code changed;
  no real data was added; no source, data, endpoint, universe, benchmark, cash
  proxy, evidence, return-construction, no-lookahead, strategy-validation, or
  trading approval was added; and normal pytest remains offline and
  credential-free
- Phase 115 - Polygon/Massive Legal/PIT Source Decision Gate adds a docs-only
  routing decision gate after the Polygon/Massive schema/interface boundary
  and synthetic reference ticker fixture. It records current evidence,
  legal/storage blockers, point-in-time/source-quality blockers, conservative
  decision rules, and a recommended pause on additional Polygon/Massive
  synthetic fixtures that involve prices, corporate actions, flat files, or
  return semantics. All sources remain unresolved; no source or data was
  approved; no production code or tests changed; no real data was added; no
  API calls or downloads occurred; and normal pytest remains offline and
  credential-free
- Phase 116 - Source-Agnostic Synthetic Market Bar Fixture adds one tiny
  source-agnostic synthetic market-bar fixture for primitive OHLCV-like
  research input shape. No production code changed; no real data was added; no
  API calls or downloads occurred; no source or data approval was added; and
  normal pytest remains offline and credential-free
- Phase 117 - Source-Agnostic Synthetic Market Bar Sequence Fixture adds one
  tiny source-agnostic synthetic market-bar sequence fixture using the Phase
  116 bar shape. No production code changed; no real data was added; no API
  calls or downloads occurred; no source or data approval was added; and normal
  pytest remains offline and credential-free
- Phase 118 - Synthetic Market Bar Sequence Return Input Consumer adds a tiny
  source-agnostic synthetic market-bar sequence return-input consumer in tests
  and fixtures only. It extracts synthetic close values and feeds existing
  close-to-close return-construction mechanics without adding production code,
  real data, API calls, downloads, or source, data, or return-construction
  approval. Normal pytest remains offline and credential-free
- Phase 120 - Source-Agnostic Research Return Input Snapshot Contract adds the
  small frozen, slotted `ResearchReturnInputSnapshot` metadata contract for
  already prepared observation dates, close values, and close-to-close returns.
  It is source-agnostic, synthetic-only, candidate-only, immutable, and
  deterministically serializes plain dates and Decimal values without adding
  real data, API calls, downloads, file reads, ingestion, persistence, source
  or data approval, return-construction approval, no-lookahead approval,
  strategy approval or validation, trading readiness, or a market-bar
  production contract. Normal pytest remains offline and credential-free
- Phase 121 - Synthetic Research Return Input Snapshot Fixture adds one tiny
  deterministic fixture for the Phase 120 `ResearchReturnInputSnapshot`
  contract. It builds a reusable synthetic-only, candidate-only snapshot and
  pins its primitive `to_dict()` representation using hard-coded artificial
  prepared observation dates, Decimal close values, Decimal close-to-close
  returns, metadata, flags, and non-claims. It does not compute returns or add
  production research, ingestion, market-bar, strategy, evaluator, signal,
  benchmark, broker, runtime, persistence, or trading behavior; no source,
  data, endpoint, universe, benchmark, cash proxy, methodology, evidence,
  return-construction, no-lookahead, strategy-validation, trading-readiness, or
  production-contract approval was added; and normal pytest remains offline and
  credential-free
- Phase 122 - Research Return Input Snapshot Consistency Checker adds one tiny
  deterministic internal checker for `ResearchReturnInputSnapshot`. It
  requires a snapshot instance, recomputes exact Decimal close-to-close returns
  from prepared close values, compares them against stored returns without
  tolerance, rounding, quantization, annualization, or inferred values, and
  returns the original object unchanged on success. Mismatched, malformed, or
  non-snapshot inputs raise the project validation error. It is only an
  arithmetic consistency aid for already prepared synthetic/candidate snapshots
  and adds no data access, source approval, endpoint approval, universe
  approval, benchmark or cash proxy approval, methodology approval, evidence
  approval, strategy, evaluator, signal, broker, runtime, persistence,
  portfolio mutation, order generation, live/paper trading, trading readiness,
  market-bar production contract, real data, vendor SDK, dependency, network
  call, credential, or file I/O behavior; normal pytest remains offline and
  credential-free
- Phase 123 - Research Return Input Snapshot Fingerprint adds one tiny
  deterministic SHA-256 helper for `ResearchReturnInputSnapshot`. It validates
  through the Phase 122 consistency checker, hashes only the snapshot's existing
  primitive `to_dict()` payload using sorted-key compact JSON, and returns a
  lowercase hex digest. Repeated calls, round-tripped snapshots, and unchanged
  synthetic fixture content produce the same digest; different valid synthetic
  content changes it. This is provenance support only and adds no data access,
  source approval, endpoint approval, universe approval, benchmark or cash proxy
  approval, methodology approval, evidence approval, signal, evaluator,
  strategy, broker, runtime, persistence, portfolio mutation, order generation,
  live/paper trading, trading readiness, production market-bar contract, real
  data, vendor SDK, dependency, network call, credential, timestamp, local path,
  environment lookup, or file I/O behavior; normal pytest remains offline and
  credential-free
- Phase 124 - Research Return Input Fingerprint / Serialization Hardening
  clarifies the existing Phase 120-123 contracts and adds focused tests only.
  `ResearchReturnInputSnapshot.from_dict()` is documented as
  serialization/schema shape validation only, with no arithmetic consistency
  check. The consistency helper is documented as an exact arithmetic check over
  already-prepared snapshots with no rounding, tolerance, inference, or
  approval, and it still returns the original snapshot object on success. The
  fingerprint helper is documented as a deterministic content hash for
  candidate-only snapshots only; it does not certify source, methodology, data,
  strategy, or downstream use. Tests now pin digest stability through
  `to_dict()`/`from_dict()` round trips, primitive payload mutation behavior,
  shape-valid arithmetic inconsistency acceptance by `from_dict()`,
  consistency/fingerprint rejection of inconsistent snapshots, and the existing
  Phase 121 fixture digest. No production behavior, ingestion, runner,
  market-bar, strategy, evaluator, signal, broker/runtime, persistence,
  portfolio mutation, order generation, trading behavior, real data,
  dependency, network call, credential, or file I/O behavior was added; normal
  pytest remains offline and credential-free
- Phase 125 - Verified Research Return Input Package adds a tiny deterministic
  `ResearchReturnInputPackage` contract that binds a
  `ResearchReturnInputSnapshot` to its verified Phase 123 fingerprint after
  Phase 122 consistency validation. The builder preserves the original snapshot
  object, returns an immutable package, and exposes only a primitive
  deterministic `to_dict()` wrapper over the existing snapshot serialization and
  fingerprint. Direct construction validates the snapshot type, lowercase
  SHA-256 fingerprint shape, arithmetic consistency, and fingerprint match.
  This is provenance and plumbing only; it adds no research runner, ingestion
  path, market-bar production contract, strategy, signal, evaluator, benchmark
  or cash proxy logic, backtest, broker/runtime behavior, persistence,
  scheduler behavior, portfolio mutation, order generation, live/paper trading,
  trading readiness, real data, dependency, network call, credential, or file
  I/O behavior; normal pytest remains offline and credential-free
- Phase 126 - Verified Research Return Input Package Deserialization adds
  narrow deterministic `ResearchReturnInputPackage.from_dict()` plumbing for
  primitive package payloads shaped only as `snapshot` plus `fingerprint`. It
  reconstructs the nested snapshot through
  `ResearchReturnInputSnapshot.from_dict()` and then uses the existing package
  validation path, rejecting non-dicts, missing or unknown package fields,
  malformed nested snapshots, malformed lowercase SHA-256 fingerprint values,
  fingerprint mismatches, and arithmetic-inconsistent reconstructed snapshots.
  This preserves current builder behavior and the existing `to_dict()` output
  shape, and adds no research runner, ingestion path, market-bar production
  contract, strategy, signal, evaluator, benchmark or cash proxy logic,
  backtest, broker/runtime behavior, persistence, scheduler behavior, portfolio
  mutation, order generation, live/paper trading, trading readiness, real data,
  dependency, network call, credential, timestamp, environment lookup, local
  path, or file I/O behavior; normal pytest remains offline and credential-free
- Phase 127 - Verified Return Input Package Replay Adapter adds one narrow
  deterministic adapter from `ResearchReturnInputPackage` into the existing
  `SyntheticReplaySnapshot` metadata contract. It requires an already valid
  package, copies only prepared observation dates, prepared close values, and
  stored close-to-close `Decimal` returns into replay metadata, and avoids the
  existing replay builder because that builder recomputes returns from values.
  The existing snapshot contract has no dedicated package provenance field, so
  the adapted manifest carries the package snapshot id as `fixture_id` and the
  package fingerprint as `checksum`; manifest limitations record that required
  `available_after` values mirror observation dates as candidate metadata only.
  This is deterministic metadata plumbing only and adds no research runner,
  ingestion path, file I/O, persistence, market-bar production contract,
  strategy, signal, evaluator, benchmark or cash proxy logic, broker/runtime
  behavior, scheduler behavior, portfolio mutation, order generation,
  live/paper trading, trading readiness, real data, dependency, network call,
  credential, timestamp, environment lookup, local path, source approval, data
  approval, endpoint approval, universe approval, methodology approval,
  evidence approval, return-construction approval, no-lookahead approval,
  strategy validation, or production-contract approval; normal pytest remains
  offline and credential-free
- Phase 128 - Verified Return Input Package Research Result Adapter adds one
  narrow deterministic adapter from `ResearchReturnInputPackage` into the
  existing `SyntheticResearchResult` contract. It reuses the Phase 127
  package-to-replay adapter first, preserving the package-derived replay
  manifest provenance convention where the snapshot id is the manifest
  `fixture_id` and the package fingerprint is the manifest `checksum`, then
  delegates summary and metric construction to the existing synthetic result
  builder. It adds no manual metrics, does not recompute returns from prices,
  does not infer missing values, and introduces no benchmarks, cash returns,
  costs, positions, signals, orders, trades, strategy state, or portfolio state.
  This remains synthetic candidate-only plumbing and does not approve source,
  methodology, no-lookahead status, strategy validity, trading readiness, or
  downstream use. It adds no research runner, ingestion path, file I/O,
  persistence, market-bar production contract, evaluator behavior,
  broker/runtime behavior, scheduler behavior, portfolio mutation, order
  generation, live/paper trading, real data, dependency, network call,
  credential, timestamp, environment lookup, local path, or production-contract
  approval; normal pytest remains offline and credential-free
- Phase 129 - Synthetic Return Input Result Fixture adds a tiny deterministic
  test fixture that builds `SyntheticResearchResult` support through the
  existing Phase 121 synthetic return-input snapshot fixture, the Phase 125
  verified package builder, and the Phase 128 package-to-result adapter. It
  exposes `build_synthetic_return_input_research_result()` and
  `expected_synthetic_return_input_research_result_dict()`, with expected
  primitive output delegated to stable `SyntheticResearchResult.to_dict()`
  serialization. Provenance keeps the Phase 127 convention: the package
  snapshot id becomes manifest `fixture_id`, and manifest `checksum` is
  `sha256:{package.fingerprint}`. It does not compute returns from prices,
  infer missing values, add metrics manually, mutate the source snapshot,
  package, replay snapshot, or result, or introduce benchmarks, cash returns,
  costs, positions, signals, orders, trades, strategy state, broker/runtime
  state, portfolio state, ingestion, file I/O, persistence, runner behavior,
  real data, network access, credentials, dependencies, or production-contract
  approval; normal pytest remains offline and credential-free
- Phase 130 - Return Input Research Result Provenance Verifier adds one narrow
  deterministic verifier for confirming that an existing
  `SyntheticResearchResult` matches a specific `ResearchReturnInputPackage`
  under the Phase 127 provenance convention. It requires the package and result
  contract types, checks only that manifest `fixture_id` equals the package
  snapshot id and manifest `checksum` equals `sha256:{package.fingerprint}`,
  and returns the original result object unchanged on success. Mismatched or
  malformed inputs raise the project validation error. It does not rebuild
  results, recompute returns, infer missing values, mutate the package or
  result, introduce benchmarks, cash returns, costs, positions, orders, trades,
  signals, strategy state, broker/runtime fields, portfolio state, ingestion,
  file I/O, persistence, runner behavior, real data, network access,
  credentials, dependencies, or production-contract approval. It does not
  certify source, methodology, no-lookahead status, strategy validity, trading
  readiness, or downstream use; normal pytest remains offline and
  credential-free
- Phase 131 - Return Input Research Chain Regression Guard adds a test-only
  end-to-end regression guard over the existing Phase 120-130 return-input
  support chain. It composes the Phase 121 synthetic snapshot fixture, Phase
  122 consistency validation, the Phase 123 fingerprint helper pinned to
  `07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2`,
  Phase 125 package construction, Phase 126 package deserialization, Phase 127
  replay adaptation, Phase 128 result adaptation, the Phase 129 result fixture,
  and the Phase 130 provenance verifier. The guard verifies original snapshot
  identity on consistency validation, package snapshot identity preservation,
  package primitive round-trip fingerprint and snapshot equality, replay
  observation order and stored return preservation, result fixture and adapter
  equality, provenance verifier object identity on success, the Phase 127
  `fixture_id` and `sha256:{package.fingerprint}` checksum convention, repeated
  construction determinism, copied primitive mutation rejection, absence of
  disallowed payload fields, and a self-audit of the new test module for
  forbidden imports, calls, and literal real-world content. It adds no
  production behavior, src changes, runner, ingestion path, file I/O,
  persistence, market-bar production contract, strategy, signal, evaluator,
  benchmark or cash proxy logic, broker/runtime behavior, scheduler behavior,
  portfolio mutation, order generation, live/paper trading, real data,
  dependency, network call, credential, approval, validation claim, trading
  readiness, or production-contract approval; normal pytest remains offline and
  credential-free
- Phase 132 - Candidate Research Result Dossier adds a frozen/slotted,
  metadata-only `CandidateResearchResultDossier` and builder that wrap an
  existing `ResearchReturnInputPackage` and matching `SyntheticResearchResult`
  only after the Phase 130 provenance verifier accepts the pair. It preserves
  package and result object identity, fixes status to advisory `candidate_only`,
  validates immutable non-empty limitations, and requires non-claims covering no
  source approval, data approval, endpoint approval, universe approval,
  benchmark approval, cash proxy approval, methodology approval, evidence
  approval, return-construction approval, no-lookahead approval, strategy
  validation, trading readiness, production use, broker/runtime use, order
  generation, or portfolio/allocation authority. `to_dict()` emits only
  deterministic primitive metadata for the package fingerprint, package
  snapshot id, result manifest fixture id, result manifest checksum, status,
  limitations, and non-claims. It adds no `from_dict()`, runner, ingestion path,
  file I/O, persistence, market-bar production contract, strategy, signal,
  evaluator, benchmark or cash proxy logic, broker/runtime behavior, scheduler
  behavior, portfolio mutation, allocation behavior, order generation,
  live/paper trading, real data, dependency, network call, credential, approval
  status, validation claim, trading readiness, or production-contract approval;
  normal pytest remains offline and credential-free
- Phase 133 - Synthetic Candidate Research Result Dossier Fixture adds only a
  tiny deterministic test fixture for `CandidateResearchResultDossier`. It
  composes the Phase 121 synthetic return-input snapshot fixture, Phase 125
  package builder, Phase 128 result adapter, and Phase 132 dossier builder,
  exposing `build_synthetic_candidate_research_result_dossier()` and
  `expected_synthetic_candidate_research_result_dossier_dict()`. The expected
  payload matches `CandidateResearchResultDossier.to_dict()` exactly. Tests pin
  the Phase 123 fingerprint
  `07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2`,
  preserve the Phase 127 manifest fixture-id and
  `sha256:{package.fingerprint}` checksum convention, verify advisory
  `candidate_only` status plus deterministic limitations and non-claims, check
  object identity preservation where applicable, and self-audit the fixture
  module for forbidden imports, calls, and real-world literals. It adds no
  production behavior, `src/` changes, runner, ingestion path, file I/O,
  persistence, market-bar production contract, strategy, signal, evaluator,
  benchmark or cash proxy logic, broker/runtime behavior, scheduler behavior,
  portfolio mutation, allocation behavior, order generation, live/paper
  trading, real data, dependency, network call, credential, approval,
  validation claim, trading readiness, or production-contract approval; normal
  pytest remains offline and credential-free
- Phase 134 - Candidate Research Brief Item adds a frozen/slotted,
  metadata-only `CandidateResearchBriefItem` plus builder for deriving advisory
  display metadata from an existing `CandidateResearchResultDossier`. It
  preserves dossier object identity, fixes `item_type` to
  `candidate_research_result`, fixes status to `candidate_only`, derives a
  deterministic headline and summary points from dossier/package/result
  metadata only, and carries forward dossier limitations and non-claims. Direct
  construction validates the dossier type, fixed item type, fixed status,
  non-empty headline, immutable non-empty summary points, immutable non-empty
  limitations, immutable non-empty non-claims, and preservation of the dossier's
  required non-claims. `to_dict()` emits only deterministic primitive metadata
  for item type, status, headline, summary points, package fingerprint, package
  snapshot id, result manifest fixture id, result manifest checksum,
  limitations, and non-claims. It adds no `from_dict()`, package re-export,
  runner, ingestion path, file I/O, persistence, market-bar production
  contract, strategy, signal, evaluator, benchmark or cash proxy logic,
  broker/runtime behavior, scheduler behavior, portfolio mutation, allocation
  behavior, order generation, live/paper trading, real data, dependency,
  network call, credential, approval status, validation claim, trading
  readiness, recommendation, action, or production-contract approval; normal
  pytest remains offline and credential-free
- Phase 135 - Synthetic Candidate Research Brief Item Fixture adds only a tiny
  deterministic test fixture for `CandidateResearchBriefItem`. It composes the
  Phase 133 synthetic candidate dossier fixture with the Phase 134 brief item
  builder, exposing `build_synthetic_candidate_research_brief_item()` and
  `expected_synthetic_candidate_research_brief_item_dict()`. The expected
  payload matches `CandidateResearchBriefItem.to_dict()` exactly. Tests verify
  the fixed `candidate_research_result` item type, advisory `candidate_only`
  status, deterministic non-actionable headline and summary points,
  carried-forward limitations and non-claims, required non-claim coverage, the
  Phase 123 fingerprint
  `07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2`, and the
  Phase 127 manifest fixture-id and `sha256:{package.fingerprint}` checksum
  convention. It self-audits the fixture module for forbidden imports, calls,
  and real-world literals, and repeated construction stays deterministic
  without mutating source objects or primitive payloads. It adds no production
  behavior, `src/` changes, runner, ingestion path, file I/O, persistence,
  market-bar production contract, strategy, signal, evaluator, benchmark or
  cash proxy logic, broker/runtime behavior, scheduler behavior, portfolio
  mutation, allocation behavior, order generation, live/paper trading, real
  data, dependency, network call, credential, approval status, validation claim,
  trading readiness, recommendation, action, or production-contract approval;
  normal pytest remains offline and credential-free
- Phase 136 - Candidate Research Brief Section adds a frozen/slotted
  `CandidateResearchBriefSection` plus
  `build_candidate_research_brief_section()`. It fixes the section type to
  `candidate_research_results`, keeps advisory `candidate_only` status, and
  uses the deterministic non-actionable title `Candidate research results
  metadata`. The builder accepts existing `CandidateResearchBriefItem` objects,
  normalizes them to an immutable tuple, preserves object identity and
  caller-provided sequence exactly, rejects empty or non-item payloads, and
  rejects duplicate item identities. Section limitations and non-claims are
  deterministic metadata only, carry item guardrails forward, and require the
  existing advisory non-claims to remain present. `to_dict()` emits primitive
  deterministic metadata only: section type, status, title, item count, item
  payloads, limitations, and non-claims; no `from_dict()` is added. Tests cover
  direct construction validation, serialization determinism, mutation
  resistance, required non-claim coverage, forbidden field absence, and
  module-level import/call/text audits. The section is not re-exported from
  package `__init__` and adds no LLM/agent, runner, ingestion, file I/O,
  persistence, market-bar production contract, strategy, signal, evaluator,
  benchmark or cash proxy logic, broker/runtime behavior, scheduler behavior,
  portfolio mutation, allocation behavior, order generation, live/paper
  trading, real data, dependency, network call, credential, approval status,
  validation claim, trading readiness, recommendation, action, or
  production-contract approval; normal pytest remains offline and
  credential-free
- Phase 137 - Synthetic Candidate Research Brief Section Fixture adds only a
  tiny deterministic test fixture for `CandidateResearchBriefSection`. It
  composes the Phase 135 synthetic candidate research brief item fixture with
  the Phase 136 section builder, exposing
  `build_synthetic_candidate_research_brief_section()` and
  `expected_synthetic_candidate_research_brief_section_dict()`. The expected
  payload matches `CandidateResearchBriefSection.to_dict()` exactly. Tests
  verify the fixed `candidate_research_results` section type, advisory
  `candidate_only` status, deterministic non-actionable title,
  carried-forward limitations and non-claims, required non-claim coverage,
  preserved item identity and ordering, the Phase 123 fingerprint
  `07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2`, and
  the Phase 127 manifest fixture-id and `sha256:{package.fingerprint}`
  checksum convention inside the section dict. The fixture self-audits for
  forbidden imports, calls, and real-world literals, and repeated construction
  stays deterministic without mutating source objects or primitive payloads.
  It adds no production behavior, `src/` changes, LLM/agent behavior, runner,
  ingestion path, file I/O, persistence, market-bar production contract,
  strategy, signal, evaluator, benchmark or cash proxy logic, broker/runtime
  behavior, scheduler behavior, portfolio mutation, allocation behavior,
  order generation, live/paper trading, real data, dependency, network call,
  credential, approval status, validation claim, trading readiness,
  recommendation, action, ranking/scoring, or production-contract approval;
  normal pytest remains offline and credential-free
- Phase 138 - Candidate Research Brief Container adds only a tiny
  deterministic, metadata-only `CandidateResearchBrief` in
  `src/algotrader/research/candidate_research_brief.py` with focused coverage
  in `tests/unit/test_candidate_research_brief.py`. It groups existing
  `CandidateResearchBriefSection` objects for future operating-brief and
  research-queue surfaces without changing section, item, dossier, package,
  result, snapshot, or manifest behavior. `build_candidate_research_brief()`
  requires at least one section, normalizes input to an immutable tuple,
  preserves section object identity and input order exactly, rejects duplicate
  section identities, fixes `brief_type` to `candidate_research_brief`, fixes
  `status` to `candidate_only`, and carries deterministic limitations plus
  required advisory non-claims forward. Direct construction validates the fixed
  brief type and status, non-empty title, non-empty immutable section tuple,
  non-empty immutable limitations and non-claims, section limitation/non-claim
  carry-forward, and required non-claim coverage. `to_dict()` emits only
  primitive deterministic metadata: brief type, status, title, section count,
  section payloads, limitations, and non-claims; no `from_dict()` is added.
  Tests verify determinism, identity/order preservation, no mutation,
  primitive-only serialization, constructor rejection paths, forbidden
  import/call absence, real-world literal absence, and absence of benchmark,
  cost, cash return, position, order, trade, signal, strategy, broker/runtime,
  portfolio/allocation, approval, recommendation, ranking/scoring, or
  trading-readiness fields. This phase adds no LLM/agent behavior, runner,
  ingestion, file I/O, persistence, database behavior, scheduler, runtime,
  notebook behavior, external-tool behavior, market-bar production contract,
  strategy behavior, signal behavior, evaluator behavior, benchmark or cash
  proxy logic, broker/runtime behavior, portfolio mutation, allocation
  behavior, order generation, live/paper trading, real data, dependency,
  network call, credential, approval status, validation claim, trading
  readiness, recommendation, action, ranking/scoring, or production-contract
  approval; normal pytest remains offline and credential-free
- Phase 139 - Synthetic Candidate Research Brief Fixture adds only a tiny
  deterministic test fixture for `CandidateResearchBrief`. It composes the
  Phase 137 synthetic candidate research brief section fixture with the Phase
  138 brief builder, exposing
  `build_synthetic_candidate_research_brief()` and
  `expected_synthetic_candidate_research_brief_dict()`. The expected payload
  matches `CandidateResearchBrief.to_dict()` exactly. Tests verify the fixed
  `candidate_research_brief` brief type, advisory `candidate_only` status,
  deterministic non-actionable title, carried-forward limitations and
  non-claims, required non-claim coverage, preserved section identity and
  ordering, fixed section and item advisory types/statuses, the Phase 123
  fingerprint
  `07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2`, and
  the Phase 127 manifest fixture-id and `sha256:{package.fingerprint}`
  checksum convention inside the brief dict. The fixture self-audits for
  forbidden imports, calls, and real-world literals, and repeated construction
  stays deterministic without mutating source objects or primitive payloads.
  It adds no production behavior, `src/` changes, LLM/agent behavior, runner,
  ingestion path, file I/O, persistence, market-bar production contract,
  strategy, signal, evaluator, benchmark or cash proxy logic, broker/runtime
  behavior, scheduler behavior, portfolio mutation, allocation behavior,
  order generation, live/paper trading, real data, dependency, network call,
  credential, approval status, validation claim, trading readiness,
  recommendation, action, ranking/scoring, or production-contract approval;
  normal pytest remains offline and credential-free
- Phase 140 - Candidate Research Brief Chain Regression Guard adds only a
  test-only end-to-end regression guard in
  `tests/unit/test_candidate_research_brief_chain_regression.py`. The guard
  composes the existing Phase 132 `CandidateResearchResultDossier`, Phase 133
  synthetic dossier fixture, Phase 134 brief item, Phase 135 brief item
  fixture, Phase 136 brief section, Phase 137 brief section fixture, Phase
  138 brief container, and Phase 139 brief fixture, then proves the synthetic
  candidate research result dossier reaches the final brief dict without
  drift. Tests pin the Phase 123 fingerprint
  `07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2`,
  preserve the Phase 127 manifest fixture-id and
  `sha256:{package.fingerprint}` checksum convention, verify fixed
  `candidate_research_brief`, `candidate_research_results`,
  `candidate_research_result`, and `candidate_only` advisory values, and
  confirm limitations plus required non-claims remain present at dossier,
  item, section, and brief levels. The regression guard also checks fixture
  determinism, builder identity/order preservation, repeated full-chain
  determinism, primitive payload copy isolation, absence of forbidden
  advisory/trading/runtime fields, and absence of forbidden imports, calls,
  real-world literals, paths, credentials, dependencies, and provider markers
  in the new test module. It adds no production behavior, `src/` changes,
  LLM/agent behavior, runner, ingestion path, file I/O, persistence,
  market-bar production contract, strategy, signal, evaluator, benchmark or
  cash proxy logic, broker/runtime behavior, scheduler behavior, portfolio
  mutation, allocation behavior, order generation, live/paper trading, real
  data, dependency, network call, credential, approval status, validation
  claim, trading readiness, recommendation, action, ranking/scoring, or
  production-contract approval; normal pytest remains offline and
  credential-free
- Phase 141 - Research Return Input Provenance Contract adds only the frozen
  `ResearchReturnInputProvenance` value object plus focused tests. The
  contract explicitly encodes the Phase 127 convention that
  `manifest.fixture_id == package.snapshot.snapshot_id` and
  `manifest.checksum == sha256:{package.fingerprint}` while preserving the
  existing manifest fields and all public payload shapes. The Phase 127
  replay adapter now uses the provenance builder internally when assigning
  those same manifest values, and the Phase 130 result provenance verifier
  now uses the same contract internally while preserving its public signature
  and return object behavior. Tests cover builder output,
  direct-construction validation, immutability, package/provenance matching,
  mismatch rejection, adapter manifest output, result verifier identity
  preservation, regression-chain payload stability, no mutation, and
  source-audit checks for forbidden imports, calls, literals, dependencies,
  paths, credentials, and runtime or trading concepts. It adds no ingestion,
  persistence, runner, operating brief, LLM/agent behavior, market-bar
  production contract, strategy, signal, evaluator, benchmark or cash proxy
  logic, broker/runtime behavior, portfolio mutation, allocation behavior,
  order generation, live/paper trading, real data, dependency, network call,
  credential, approval status, validation claim, trading readiness,
  recommendation, action, ranking/scoring, or production-contract approval;
  normal pytest remains offline and credential-free
- Phase 142 - Advisory Operating Brief Container adds only the frozen/slotted,
  metadata-only `AdvisoryOperatingBrief` in
  `src/algotrader/research/advisory_operating_brief.py` with focused coverage
  in `tests/unit/test_advisory_operating_brief.py`. It groups existing
  `CandidateResearchBrief` objects for future operating-brief display surfaces,
  fixes `operating_brief_type` to `advisory_operating_brief`, fixes status to
  advisory `candidate_only`, preserves candidate brief object identity and
  caller-provided sequence exactly, rejects empty inputs, non-brief inputs,
  duplicate brief identities, forbidden brief types, approval-like statuses,
  and malformed title, limitations, or non-claims. The builder carries
  candidate brief limitations and non-claims forward without adding approval
  semantics, and `to_dict()` emits only deterministic primitive metadata:
  operating brief type, status, title, candidate brief count, nested candidate
  brief payloads, limitations, and non-claims. Tests prove determinism,
  primitive serialization, input non-mutation, Phase 123 digest visibility,
  Phase 127/141 provenance visibility, no package `__init__` re-export, and
  source-level import/call/text guardrails. It adds no `from_dict()`, LLM/agent
  behavior, ingestion, persistence, file I/O, local snapshot loading,
  scheduler, CLI, runtime behavior, market-bar production contract, strategy,
  signal, evaluator, benchmark or cash proxy logic, backtesting engine,
  broker/runtime behavior, portfolio mutation, allocation behavior, order
  generation, live/paper trading, real data, dependency, network call,
  credential, source approval, data approval, methodology approval, evidence
  approval, strategy validation, trading readiness, recommendation,
  ranking/scoring, or production-contract approval; normal pytest remains
  offline and credential-free
- Phase 143 - Synthetic Advisory Operating Brief Fixture replaces the older
  broad test fixture in `tests/fixtures/advisory_operating_brief.py` with a
  tiny deterministic fixture for the Phase 142 `AdvisoryOperatingBrief`
  surface and adds focused coverage in
  `tests/unit/test_advisory_operating_brief_fixture.py`. It builds only through
  the Phase 139 synthetic candidate research brief fixture and Phase 142
  `build_advisory_operating_brief()` builder, preserves candidate brief object
  identity and input sequence where applicable, and exposes
  `build_synthetic_advisory_operating_brief()` plus
  `expected_synthetic_advisory_operating_brief_dict()`. The expected payload is
  exactly `AdvisoryOperatingBrief.to_dict()`, including the fixed
  `advisory_operating_brief` type, advisory `candidate_only` status,
  deterministic non-actionable title, nested candidate brief/section/item
  advisory values, carried-forward limitations and non-claims, Phase 123 digest
  `07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2`, and the
  Phase 127/141 manifest convention that the fixture id comes from the package
  snapshot id and the checksum is `sha256:{package.fingerprint}`. Tests prove
  repeated-call determinism, primitive serialization copy isolation,
  source-object non-mutation, absence of forbidden payload/object fields, and
  fixture-module import/call/text guardrails. It adds no `src/` changes,
  LLM/agent behavior, ingestion, persistence, runner, file I/O, local snapshot
  loading, CLI, scheduler, runtime behavior, market-bar production contract,
  strategy, signal, evaluator, benchmark or cash proxy logic, backtesting
  engine, broker/runtime behavior, portfolio mutation, allocation behavior,
  order generation, live/paper trading, real data, dependency, network call,
  credential, source approval, endpoint approval, universe approval,
  methodology approval, evidence approval, validation claim, trading readiness,
  recommendation, ranking/scoring, or production-contract approval; normal
  pytest remains offline and credential-free
- Phase 144 - Advisory Operating Brief Chain Regression Guard adds only focused
  coverage in
  `tests/unit/test_advisory_operating_brief_chain_regression.py`. It proves the
  Phase 139 synthetic candidate research brief fixture can pass through the
  Phase 142 `AdvisoryOperatingBrief` contract and Phase 143 synthetic advisory
  operating brief fixture without payload drift. It pins the Phase 123 digest
  `07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2`, verifies
  the Phase 127/141 manifest convention in the final operating brief dict,
  checks fixed advisory type/status values through the operating brief,
  candidate brief, section, item, and dossier chain, and proves limitations and
  non-claims remain present. Tests also cover repeated full-chain determinism,
  object identity and sequence preservation where applicable, primitive payload
  copy isolation, absence of forbidden advisory or trading payload fields, and
  source-level import/call/text guardrails for the new test module. It adds no
  `src/` changes, production behavior, LLM/agent behavior, ingestion,
  persistence, runner, file I/O, local snapshot loading, CLI, scheduler,
  runtime behavior, market-bar production contract, strategy, signal,
  evaluator, benchmark or cash proxy logic, broker/runtime behavior, portfolio
  mutation, allocation behavior, order generation, live/paper trading, real
  data, dependency, network call, credential, source approval, endpoint
  approval, universe approval, methodology approval, evidence approval,
  validation claim, trading readiness, recommendation, ranking/scoring, or
  production-contract approval; normal pytest remains offline and
  credential-free
- Phase 145 - Advisory Operating Brief Text Renderer adds one narrow
  display-only helper in
  `src/algotrader/research/advisory_operating_brief_renderer.py` and focused
  coverage in `tests/unit/test_advisory_operating_brief_renderer.py`. It
  requires an existing `AdvisoryOperatingBrief`, reads only its deterministic
  `to_dict()` payload, emits stable plain text with fixed headings, and
  preserves the existing candidate brief, section, and item sequence exactly.
  The rendered text includes fixed advisory type/status metadata, limitations,
  non-claims, the Phase 123 digest, and the Phase 127/141 manifest convention
  fields when those values are visible in nested payloads. Tests prove fixture
  acceptance, invalid input rejection, repeated-render determinism, sequence
  preservation, non-mutation, source-level import/call/text guardrails, no
  package `__init__` re-export, and output based only on existing operating
  brief data. It adds no parser, `from_text`, markdown writer, CLI, dashboard,
  notebook, persistence, file I/O, local snapshot loading, scheduler, runtime
  behavior, LLM/agent behavior, ingestion, market-bar production contract,
  strategy, signal, evaluator, benchmark or cash proxy logic, backtesting
  engine, broker/runtime behavior, portfolio mutation, allocation behavior,
  order generation, live/paper trading, real data, dependency, network call,
  credential, source approval, endpoint approval, universe approval,
  methodology approval, evidence approval, validation claim, trading readiness,
  recommendation, ranking/scoring, or production-contract approval; normal
  pytest remains offline and credential-free
- Phase 146 - Advisory Operating Brief Rendered Text Regression Guard adds a
  test-only exact rendered-text pin in
  `tests/unit/test_advisory_operating_brief_renderer_regression.py` using the
  Phase 143 synthetic advisory operating brief fixture and Phase 145 renderer.
  It compares the full deterministic line tuple, proves repeated renders are
  byte-for-byte identical, checks fixed advisory type/status values, preserves
  nested candidate brief/section/item sequence, carries through the Phase 123
  digest and Phase 127/141 manifest fixture/checksum convention, confirms
  limitations and non-claims remain visible, proves copied text and copied
  primitive payload edits do not mutate the source operating brief, and keeps
  import/call/literal guardrails in the test module. It adds no `src/` changes,
  production behavior, parser, `from_text`, markdown writer, CLI, dashboard,
  notebook, persistence, file I/O, local snapshot loading, scheduler, runtime
  behavior, LLM/agent behavior, ingestion, market-bar production contract,
  strategy, signal, evaluator, benchmark or cash proxy logic, backtesting
  engine, broker/runtime behavior, portfolio mutation, allocation behavior,
  order generation, live/paper trading, real data, dependency, network call,
  credential, source approval, endpoint approval, universe approval,
  methodology approval, evidence approval, validation claim, trading readiness,
  recommendation, ranking/scoring, or production-contract approval; normal
  pytest remains offline and credential-free
- Phase 147 - Advisory Operating Brief In-Memory Export Helper adds a tiny
  export-format helper in
  `src/algotrader/research/advisory_operating_brief_export.py` with focused
  coverage in `tests/unit/test_advisory_operating_brief_export.py`. It requires
  an existing `AdvisoryOperatingBrief`, snapshots its deterministic primitive
  `to_dict()` payload, emits compact sorted-key JSON with
  `json.dumps(..., sort_keys=True, separators=(",", ":"))`, and delegates
  rendered text to the existing Phase 145 renderer. Tests prove Phase 143
  fixture acceptance, invalid input rejection, frozen export fields, primitive
  payload equality and copy isolation from source objects, byte-for-byte JSON
  determinism, sorted/compact JSON behavior, JSON round-trip equality in tests,
  rendered-text equivalence, repeated export determinism, Phase 123 digest
  visibility, Phase 127/141 provenance convention visibility, fixed advisory
  type/status visibility, no package `__init__` re-export, and source-level
  import/call/literal guardrails. It adds no file I/O, parser, deserializer,
  CLI, dashboard, notebook, persistence, local snapshot loading, scheduler,
  runtime behavior, LLM/agent behavior, ingestion, market-bar production
  contract, strategy, signal, evaluator, benchmark or cash proxy logic,
  backtesting engine, broker/runtime behavior, portfolio mutation, allocation
  behavior, order generation, live/paper trading, real data, dependency,
  network call, credential, source approval, endpoint approval, universe
  approval, methodology approval, evidence approval, validation claim, trading
  readiness, recommendation, ranking/scoring, or production-contract approval;
  normal pytest remains offline and credential-free
- Phase 148 - Advisory Operating Brief Export Regression Guard adds a
  test-only exact-output pin in
  `tests/unit/test_advisory_operating_brief_export_regression.py` using the
  Phase 143 synthetic advisory operating brief fixture and the Phase 147
  in-memory export helper. It pins the compact JSON string, rendered line
  tuple, payload key shape, repeated byte-for-byte export determinism, JSON
  round-trip equality to the primitive payload, renderer equivalence to the
  Phase 145 renderer, exported-payload copy isolation from source objects,
  Phase 123 digest visibility, Phase 127/141 provenance convention visibility,
  fixed advisory type/status values, limitations, non-claims, and test-module
  import/call/literal guardrails. It changes no `src/` files and adds no
  production behavior, file I/O, parser, deserializer, CLI, dashboard,
  notebook, persistence, local snapshot loading, scheduler, runtime behavior,
  LLM/agent behavior, ingestion, market-bar production contract, strategy,
  signal, evaluator, benchmark or cash proxy logic, backtesting engine,
  broker/runtime behavior, portfolio mutation, allocation behavior, order
  generation, live/paper trading, real data, dependency, network call,
  credential, source approval, endpoint approval, universe approval,
  methodology approval, evidence approval, validation claim, trading readiness,
  recommendation, ranking/scoring, or production-contract approval; normal
  pytest remains offline and credential-free
- Phase 149 - Advisory Operating Brief CLI Preview adds a tiny developer
  preview subcommand, `algotrader advisory-operating-brief-preview`, plus the
  narrow production-safe synthetic preview builder in
  `src/algotrader/research/advisory_operating_brief_cli.py`. The command builds
  the same synthetic advisory operating brief payload as the Phase 143 fixture
  without importing `tests.fixtures` from production code, exports it through
  the Phase 147 in-memory helper, and writes only the selected export view to
  stdout: rendered text by default or compact JSON with `--format json`.
  Focused tests in `tests/unit/test_advisory_operating_brief_cli.py` prove
  parser registration, Phase 143 fixture equivalence, byte-for-byte
  deterministic text and JSON output, no file/path arguments, no file I/O, no
  environment reads, no network access, no broker/runtime/vendor/LLM imports
  during preview invocation, fixed type/status visibility, Phase 123 digest
  visibility, Phase 127/141 provenance visibility, limitations and non-claims
  visibility, no extra decision language, source-object non-mutation, and
  source-level import/call/literal guardrails. It remains synthetic, offline,
  credential-free, and advisory only; it adds no file output, input path,
  config/env loading, current time/date, random value, real data loading,
  ingestion, persistence, scheduler/runtime behavior, dashboard behavior,
  notebook behavior, external-tool behavior, LLM/agent behavior,
  broker/runtime behavior, strategy/signal/evaluator behavior, recommendation,
  ranking/scoring, allocation, order generation, source approval, endpoint
  approval, universe approval, methodology approval, evidence approval,
  validation claim, trading readiness, live/paper trading, or
  production-contract approval
- Phase 150 - Advisory Operating Brief CLI Preview Regression Guard adds a
  test-only exact-output pin in
  `tests/unit/test_advisory_operating_brief_cli_regression.py` for the
  synthetic developer preview command. It invokes the existing CLI entrypoint,
  proves default stdout equals the Phase 145 renderer pin, proves
  `--format json` stdout equals the Phase 147 compact JSON pin, parses the JSON
  back to the expected primitive export payload, checks repeated CLI
  invocations are byte-for-byte deterministic, and verifies fixed advisory
  type/status values, the Phase 123 digest, Phase 127/141 provenance fields,
  limitations, non-claims, parser-surface boundaries, no mutation of the
  synthetic brief object, no added decision language outside the payload, and
  test-module import/call/literal guardrails. It changes no `src/` files and
  adds no production behavior, file I/O, path argument, file output, local
  snapshot loading, persistence, database behavior, scheduler/runtime behavior,
  dashboard behavior, notebook behavior, external-tool behavior, LLM/agent
  behavior, broker/runtime behavior, strategy/signal/evaluator behavior,
  benchmark or cash logic, portfolio/allocation mutation, order generation,
  real data, ingestion, vendor API, credential, dependency, source approval,
  endpoint approval, universe approval, methodology approval, evidence
  approval, validation claim, no-lookahead claim, trading readiness,
  recommendation, ranking/scoring, or production-contract approval; normal
  pytest remains offline, deterministic, and credential-free
- Phase 151 - Advisory Operating Brief Review Checklist Contract adds
  `src/algotrader/research/advisory_operating_brief_review.py` and focused
  coverage in `tests/unit/test_advisory_operating_brief_review.py`. It accepts
  only an existing Phase 147/150 in-memory advisory operating brief export,
  validates malformed export objects strictly, and returns a frozen, slotted,
  metadata-only `AdvisoryOperatingBriefReviewChecklist` with fixed
  `review_type` and `candidate_only` status. The checklist records
  deterministic booleans for candidate-only status, advisory-only type shape,
  limitations, non-claims, the Phase 123 fingerprint, and Phase 127/141
  provenance convention; any blocked capital-authority field or language paths
  are findings only. `to_dict()` is primitive-only and deterministic, tuple
  fields remain immutable, repeated construction produces identical
  dictionaries, and the source export payload is not mutated. It adds no CLI
  behavior, file I/O, local snapshot loading, persistence, database behavior,
  dashboard behavior, scheduler/runtime behavior, notebook behavior,
  external-tool behavior, LLM/agent behavior, broker/runtime behavior,
  strategy/signal/evaluator behavior, benchmark or cash logic,
  portfolio/allocation mutation, order generation, ranking/scoring,
  recommendation, approval, real data, ingestion, vendor API, credential, or
  dependency
- Phase 152 - Advisory Operating Brief Review Checklist Regression Guard adds
  a test-only exact-output pin in
  `tests/unit/test_advisory_operating_brief_review_regression.py` for the
  Phase 151 checklist contract. It builds the checklist only from the existing
  synthetic Phase 147/150 in-memory export chain, pins the exact deterministic
  `to_dict()` payload, separately pins source export candidate/advisory
  metadata, limitations, non-claims, the Phase 123 fingerprint, and the Phase
  127/141 provenance convention, proves repeated construction is dict-equal and
  byte-identical, proves tuple fields serialize to primitive lists, and proves
  checklist construction does not mutate the source export payload or text
  views. Injected capital-authority metadata remains checklist findings only,
  and test-module import/call/literal guardrails prevent accidental broker,
  order, allocation, approval, or trading-authority language outside explicit
  forbidden findings and negative non-claims. It changes no `src/` files and
  adds no CLI behavior, file I/O, persistence, dashboard behavior,
  runtime/scheduler behavior, network/socket access, credentials, vendor API
  access, notebooks, LLM/agent behavior, broker/runtime behavior,
  strategy/signal/evaluator behavior, ranking/scoring, recommendations,
  allocation authority, orders, portfolio mutation, trading readiness, source
  approval, methodology approval, validation approval, trading authority, or
  dependency; normal pytest remains offline, credential-free, deterministic,
  and safe
- Phase 153 - Advisory Strategy Eligibility Status Contract adds
  `src/algotrader/research/strategy_eligibility_status.py` and focused
  coverage in `tests/unit/test_strategy_eligibility_status.py`. It defines a
  frozen, slotted, metadata-only `StrategyEligibilityStatus` plus
  `build_strategy_eligibility_status(...)` for a strategy candidate's current
  advisory eligibility state, pins `eligibility_type` to
  `strategy_eligibility_status`, `authority` to `advisory_only`, and
  `capital_authority` to `False`, and permits only `research_only`,
  `watchlist_only`, and `blocked`. It rejects paper, live, authorized,
  trading-ready, approval-like, and trading-action states; validates required
  non-empty strings and tuple/list metadata; rejects bools where strings are
  expected; copies source collections into immutable tuples; emits exact
  primitive deterministic dictionaries from `to_dict()`; and requires explicit
  non-claims that it is not validation, not paper readiness, not live
  readiness, not a trading recommendation, not allocation authority, and not
  order authority. It adds no strategy execution behavior, signal/evaluator
  behavior, backtesting, broker/runtime behavior, order generation, allocation,
  portfolio mutation, reconciliation mutation, scheduler behavior, dashboard
  behavior, CLI behavior, file I/O, persistence, network/socket access,
  credentials, vendor API, LLM/agent behavior, notebooks, source/universe/
  benchmark/methodology/validation approval, paper readiness, live readiness,
  trading recommendation, trading authority, or dependency; normal pytest
  remains offline, credential-free, deterministic, and safe
- Phase 154 - Synthetic Strategy Eligibility Status Fixture adds
  `tests/fixtures/strategy_eligibility_status.py` and focused coverage in
  `tests/unit/test_strategy_eligibility_status_fixture.py`. It builds one
  deterministic synthetic `research_only` `StrategyEligibilityStatus` through
  the Phase 153 public `build_strategy_eligibility_status(...)` helper and
  provides an exact expected primitive dictionary helper for future advisory
  operating brief composition tests. The fixture pins stable synthetic
  strategy id/name, reasons, limitations, negative non-claims, evidence refs,
  blockers, and required next steps; verifies primitive list serialization
  from tuple fields; proves repeated construction is dict-identical and compact
  JSON byte-identical; and returns fresh helper lists so primitive payload
  mutation cannot affect fixture source collections. Its non-claims state that
  it is not validation, not paper readiness, not live readiness, not a trading
  recommendation, not allocation authority, not order authority, not
  profitability evidence, not approval, and not capital authority. Guardrails
  pin allowed imports/calls and prove no broker/order/allocation/trading
  authority fields, states, or runtime paths were added. It changes no `src/`
  files and adds no CLI behavior, file I/O, persistence, dashboard behavior,
  runtime/scheduler behavior, network/socket access, credentials, vendor APIs,
  notebooks, LLM/agent behavior, broker/runtime behavior,
  strategy/signal/evaluator behavior, backtesting behavior, ranking/scoring,
  recommendations, allocation authority, orders, portfolio mutation, trading
  readiness, source approval, methodology approval, validation approval,
  trading authority, or dependency; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 155 - Advisory Strategy Eligibility Brief Item adds
  `src/algotrader/research/strategy_eligibility_brief_item.py` and focused
  coverage in `tests/unit/test_strategy_eligibility_brief_item.py`. It defines
  a frozen, slotted, metadata-only `StrategyEligibilityBriefItem` plus
  `build_strategy_eligibility_brief_item(...)`, requires an exact
  `StrategyEligibilityStatus` source object, preserves source object identity,
  pins `item_type` to `strategy_eligibility_brief_item`, `status` to
  `candidate_only`, `authority` to `advisory_only`, and `capital_authority` to
  `False`, and carries forward strategy id/name, eligibility state, reasons,
  limitations, non-claims, evidence refs, blockers, and required next steps.
  Its deterministic `headline` and `summary` are generated from safe source
  metadata counts and remain advisory-only. `to_dict()` emits primitive-only
  metadata with tuple fields serialized as lists and includes the nested source
  status `to_dict()` payload. Tests pin exact Phase 154 fixture-derived
  dictionaries and compact JSON; prove repeated construction is deterministic;
  prove source status objects are not mutated; reject non-status and malformed
  status-like objects; reject direct constructor metadata that diverges from the
  source; and prove paper/live/approved and trading-ready states remain
  impossible through this item. AST guardrails prove no `from_dict()`, no
  forbidden runtime/vendor/network/file/dependency imports or calls, and no
  actionable broker/order/allocation/portfolio/trading authority fields were
  added. It adds no strategy execution behavior, signal/evaluator behavior,
  backtesting, broker/runtime behavior, order generation, allocation, portfolio
  mutation, reconciliation mutation, scheduler behavior, dashboard behavior,
  CLI behavior, file I/O, persistence, network/socket access, credentials,
  vendor API, LLM/agent behavior, notebooks, source/universe/benchmark/
  methodology/validation approval, paper readiness, live readiness, trading
  recommendation, trading authority, or dependency; normal pytest remains
  offline, credential-free, deterministic, and safe
- Phase 156 - Synthetic Strategy Eligibility Brief Item Fixture adds
  `tests/fixtures/strategy_eligibility_brief_item.py` and focused coverage in
  `tests/unit/test_strategy_eligibility_brief_item_fixture.py`. It composes the
  Phase 154 `build_synthetic_strategy_eligibility_status()` fixture through the
  Phase 155 public `build_strategy_eligibility_brief_item(...)` helper so the
  synthetic brief item remains validation-backed and source-status-derived.
  The expected helper returns the exact primitive brief item payload with fresh
  top-level lists and the exact Phase 154 expected status dictionary nested as
  `source_status`. Tests prove it builds a `StrategyEligibilityBriefItem` with
  a `StrategyEligibilityStatus` source, pins `item_type`, `candidate_only`
  status, `advisory_only` authority, `capital_authority=False`, headline,
  summary, tuple/list serialization, exact dictionaries, compact JSON bytes,
  carried-forward limitations and non-claims, source object immutability, and
  fresh helper payloads. Guardrails prove no forbidden broker/order/allocation/
  trading-authority fields, imports, calls, or literals were added. It changes
  no `src/` files and adds no CLI behavior, file I/O, persistence, dashboard
  behavior, runtime/scheduler behavior, network/socket access, credentials,
  vendor APIs, notebooks, LLM/agent behavior, broker/runtime behavior,
  strategy/signal/evaluator behavior, backtesting behavior, ranking/scoring,
  recommendations, allocation authority, orders, portfolio mutation, trading
  readiness, source approval, methodology approval, validation approval,
  trading authority, or dependency; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 157 - Advisory Strategy Eligibility Brief Section adds
  `src/algotrader/research/strategy_eligibility_brief_section.py` and focused
  coverage in `tests/unit/test_strategy_eligibility_brief_section.py`. It
  defines a frozen, slotted, metadata-only
  `StrategyEligibilityBriefSection` plus
  `build_strategy_eligibility_brief_section(...)`, requires at least one exact
  `StrategyEligibilityBriefItem`, rejects non-items, malformed item-like
  objects, empty collections, and duplicate item identities, converts item
  collections to immutable tuples, and preserves source item identity and input
  sequence. Fixed metadata is pinned to
  `section_type=strategy_eligibility_brief_section`, `status=candidate_only`,
  `authority=advisory_only`, and `capital_authority=False`. Tests pin the
  deterministic advisory-only title and summary, exact primitive `to_dict()`
  output, compact JSON, nested Phase 156 expected item dictionary, repeated
  construction determinism, carried-forward limitations and non-claims with
  exact duplicate strings removed, and source item immutability. Guardrails
  prove no forbidden paper/live/approved/trading-ready states, broker/order/
  allocation/trading-authority fields, imports, calls, literals, file I/O,
  persistence, network/socket access, credentials, vendor APIs, dashboard,
  scheduler/runtime, ML, LLM/agent, pandas, numpy, vectorbt, QuantConnect,
  strategy execution, signal/evaluator, backtesting, portfolio mutation, or
  new dependency behavior were added; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 158 - Synthetic Strategy Eligibility Brief Section Fixture adds
  `tests/fixtures/strategy_eligibility_brief_section.py` and focused coverage
  in `tests/unit/test_strategy_eligibility_brief_section_fixture.py`. It
  composes the Phase 156
  `build_synthetic_strategy_eligibility_brief_item()` fixture through the
  Phase 157 public `build_strategy_eligibility_brief_section(...)` helper, so
  the synthetic section remains validation-backed and item-derived. The
  expected helper returns the exact primitive brief section payload with the
  exact Phase 156 expected item dictionary nested in `items`, plus fresh
  section-level limitation and non-claim lists. Tests prove it builds a
  `StrategyEligibilityBriefSection` containing the Phase 156
  `StrategyEligibilityBriefItem`, pins `section_type`, `candidate_only`
  status, `advisory_only` authority, `capital_authority=False`, title,
  summary, tuple/list serialization, exact dictionaries, compact JSON bytes,
  carried-forward limitations and non-claims, source object immutability, and
  fresh helper payloads. Guardrails prove no forbidden broker/order/allocation/
  trading-authority fields, imports, calls, or literals were added. It changes
  no `src/` files and adds no CLI behavior, file I/O, persistence, dashboard
  behavior, runtime/scheduler behavior, network/socket access, credentials,
  vendor APIs, notebooks, LLM/agent behavior, broker/runtime behavior,
  strategy/signal/evaluator behavior, backtesting behavior, ranking/scoring,
  recommendations, allocation authority, orders, portfolio mutation, trading
  readiness, source approval, methodology approval, validation approval,
  trading authority, or dependency; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 159 - Advisory Strategy Eligibility Brief Container adds
  `src/algotrader/research/strategy_eligibility_brief.py` and focused coverage
  in `tests/unit/test_strategy_eligibility_brief.py`. It defines a frozen,
  slotted, metadata-only `StrategyEligibilityBrief` plus
  `build_strategy_eligibility_brief(...)`, requires at least one exact
  `StrategyEligibilityBriefSection`, rejects non-sections, malformed
  section-like objects, empty collections, and duplicate section identities,
  converts section collections to immutable tuples, and preserves source
  section identity and input sequence. Fixed metadata is pinned to
  `brief_type=strategy_eligibility_brief`, `status=candidate_only`,
  `authority=advisory_only`, and `capital_authority=False`. Tests pin the
  deterministic advisory-only title and summary, exact primitive `to_dict()`
  output, compact JSON, nested Phase 158 expected section dictionary, repeated
  construction determinism, carried-forward limitations and non-claims with
  exact duplicate strings removed, and source section immutability. Guardrails
  prove no forbidden paper/live/approved/trading-ready states, broker/order/
  allocation/trading-authority fields, imports, calls, literals, file I/O,
  persistence, network/socket access, credentials, vendor APIs, dashboard,
  scheduler/runtime, ML, LLM/agent, pandas, numpy, vectorbt, QuantConnect,
  strategy execution, signal/evaluator, backtesting, portfolio mutation, or
  new dependency behavior were added; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 160 - Synthetic Strategy Eligibility Brief Fixture adds
  `tests/fixtures/strategy_eligibility_brief.py` and focused coverage in
  `tests/unit/test_strategy_eligibility_brief_fixture.py`. It composes the
  Phase 158 `build_synthetic_strategy_eligibility_brief_section()` fixture
  through the Phase 159 public `build_strategy_eligibility_brief(...)` helper,
  so the synthetic brief remains validation-backed and section-derived. The
  expected helper returns the exact primitive brief payload with the exact
  Phase 158 expected section dictionary nested in `sections`, plus fresh
  top-level limitation and non-claim lists. Tests prove it builds a
  `StrategyEligibilityBrief` containing the Phase 158
  `StrategyEligibilityBriefSection`, pins `brief_type`, `candidate_only`
  status, `advisory_only` authority, `capital_authority=False`, title,
  summary, tuple/list serialization, exact dictionaries, compact JSON bytes,
  carried-forward limitations and non-claims, source object immutability, and
  fresh helper payloads. Guardrails prove no forbidden broker/order/allocation/
  trading-authority fields, imports, calls, or literals were added. It changes
  no `src/` files and adds no CLI behavior, file I/O, persistence, dashboard
  behavior, runtime/scheduler behavior, network/socket access, credentials,
  vendor APIs, notebooks, LLM/agent behavior, broker/runtime behavior,
  strategy/signal/evaluator behavior, backtesting behavior, ranking/scoring,
  recommendations, allocation authority, orders, portfolio mutation, trading
  readiness, source approval, methodology approval, validation approval,
  trading authority, or dependency; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 161 - Advisory Operating Brief Content Bundle Contract adds
  `src/algotrader/research/advisory_operating_brief_content_bundle.py` and
  focused coverage in
  `tests/unit/test_advisory_operating_brief_content_bundle.py`. It defines a
  frozen, slotted, metadata-only `AdvisoryOperatingBriefContentBundle` plus
  `build_advisory_operating_brief_content_bundle(...)` for grouping existing
  `CandidateResearchBrief` and `StrategyEligibilityBrief` objects for later
  operating brief composition without changing the current
  `AdvisoryOperatingBrief`, renderer, export, or CLI behavior. The bundle
  requires at least one total source brief, allows either family to be empty,
  rejects non-brief and malformed brief-like inputs, converts source
  collections to immutable tuples, preserves source object identity and input
  sequence within each family, and rejects duplicate identities through one
  shared identity guard. It pins `bundle_type`, `candidate_only` status,
  `advisory_only` authority, and `capital_authority=False`, derives only
  advisory title/summary metadata, carries forward limitations and non-claims
  with exact duplicate strings removed, and serializes nested source
  `to_dict()` payloads in deterministic primitive dictionaries. Tests pin the
  combined synthetic dictionary and compact JSON, exact nested Phase 160
  strategy eligibility expected dictionary, exact nested candidate research
  expected dictionary, repeated determinism, source immutability, impossible
  paper/live/approved/trading-ready states, and AST/literal guardrails. It adds
  no strategy execution, signal/evaluator behavior, backtesting behavior,
  broker/runtime behavior, order generation, allocation, portfolio mutation,
  reconciliation mutation, scheduler behavior, dashboard behavior, CLI
  behavior, file I/O, persistence, network/socket access, credentials, vendor
  APIs, LLM/agent behavior, notebooks, or new dependencies; normal pytest
  remains offline, credential-free, deterministic, and safe
- Phase 162 - Synthetic Advisory Operating Brief Content Bundle Fixture adds
  `tests/fixtures/advisory_operating_brief_content_bundle.py` and focused
  coverage in
  `tests/unit/test_advisory_operating_brief_content_bundle_fixture.py`. It
  composes the existing synthetic `CandidateResearchBrief` fixture, the Phase
  160 `build_synthetic_strategy_eligibility_brief()` fixture, and the Phase
  161 `build_advisory_operating_brief_content_bundle(...)` helper, so the
  synthetic bundle remains validation-backed and does not bypass the contract.
  The expected helper nests the existing expected synthetic candidate research
  brief dictionary and the exact Phase 160
  `expected_synthetic_strategy_eligibility_brief_dict()` payload, then pins
  `bundle_type`, `candidate_only` status, `advisory_only` authority,
  `capital_authority=False`, title, summary, counts, tuple/list serialization,
  exact dictionaries, compact JSON bytes, and fresh carried-forward
  limitations and non-claims. Tests prove it builds an
  `AdvisoryOperatingBriefContentBundle` containing exactly one
  `CandidateResearchBrief` and one `StrategyEligibilityBrief`, does not mutate
  source briefs, does not share mutable helper payload state, and adds no
  forbidden broker/order/allocation/trading-authority fields, imports, calls,
  or literals. It changes no `src/` files and adds no CLI behavior, file I/O,
  persistence, dashboard behavior, runtime/scheduler behavior, network/socket
  access, credentials, vendor APIs, notebooks, LLM/agent behavior,
  broker/runtime behavior, strategy/signal/evaluator behavior, backtesting
  behavior, ranking/scoring, recommendations, allocation authority, orders,
  portfolio mutation, trading readiness, source approval, methodology
  approval, validation approval, trading authority, or dependency; normal
  pytest remains offline, credential-free, deterministic, and safe
- Phase 163 - Advisory Operating Brief Content Bundle Text Renderer adds
  `src/algotrader/research/advisory_operating_brief_content_bundle_renderer.py`
  and focused coverage in
  `tests/unit/test_advisory_operating_brief_content_bundle_renderer.py`. The
  renderer exposes the pure
  `render_advisory_operating_brief_content_bundle_text(...)` function,
  requires an exact `AdvisoryOperatingBriefContentBundle`, rejects non-bundle
  and bundle-like inputs, and renders only the primitive `bundle.to_dict()`
  payload. Its fixed headings and fixed line sequencing include bundle
  metadata, title, summary, candidate research brief content, strategy
  eligibility brief content, carried-forward limitations, and carried-forward
  non-claims while preserving source branch order. The pinned synthetic output
  represents existing candidate research payload content plus the Phase 160
  strategy eligibility payload, including eligibility state, reasons, evidence
  refs, blockers, required next steps, limitations, non-claims, and source
  status metadata. Tests prove byte-for-byte deterministic repeated rendering,
  source bundle immutability, fixed advisory metadata, branch order
  preservation, and rejection of non-bundle or malformed bundle-like inputs.
  AST and literal guardrails prove the renderer adds no forbidden
  broker/order/allocation/trading-authority fields, imports, calls, or
  literals, and no CLI behavior, file I/O, persistence, dashboard behavior,
  runtime/scheduler behavior, network/socket access, credentials, vendor APIs,
  notebooks, LLM/agent behavior, ML behavior, pandas/numpy/vectorbt/
  QuantConnect dependency behavior, broker/runtime behavior,
  strategy/signal/evaluator behavior, backtesting behavior, ranking/scoring,
  recommendations, allocation authority, orders, portfolio mutation, trading
  readiness, source approval, methodology approval, validation approval, or
  trading authority. Existing `AdvisoryOperatingBrief`, renderer, export, and
  CLI behavior remain unchanged, and normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 164 - Advisory Operating Brief Content Bundle Renderer Regression Guard
  adds the test-only
  `tests/unit/test_advisory_operating_brief_content_bundle_renderer_regression.py`
  guard for the Phase 163 content bundle text renderer. It uses the Phase 162
  synthetic content bundle fixture, calls only
  `render_advisory_operating_brief_content_bundle_text(...)`, pins the exact
  rendered line tuple, proves repeated rendering is byte-for-byte identical,
  and verifies fixed bundle metadata, candidate research branch content,
  strategy eligibility branch content, limitations, non-claims, advisory-only
  authority markers, and preserved candidate/strategy branch order. It also
  proves the source bundle `to_dict()` payload is unchanged before and after
  rendering. Authority-sensitive rendered terms are allowed only as explicit
  source metadata non-claims or cautions, with no approval, recommendation,
  paper readiness, live readiness, allocation authority, order authority,
  trading authority, actionable readiness fields, or old
  `AdvisoryOperatingBrief` renderer/export/CLI chain behavior introduced. The
  test's AST guard keeps the regression file test-only and free of forbidden
  dependency imports or calls. This phase changes no `src/` files and adds no
  CLI behavior, file I/O, persistence, dashboard behavior, runtime/scheduler
  behavior, network/socket access, credentials, vendor APIs, notebooks,
  LLM/agent behavior, broker/runtime behavior, strategy/signal/evaluator
  behavior, backtesting behavior, ranking/scoring, recommendations, allocation
  authority, orders, portfolio mutation, trading readiness, source approval,
  methodology approval, validation approval, trading authority, or dependency;
  normal pytest remains offline, credential-free, deterministic, and safe
- Phase 165 - Advisory Operating Brief Content Bundle Export Contract adds
  `src/algotrader/research/advisory_operating_brief_content_bundle_export.py`
  and focused coverage in
  `tests/unit/test_advisory_operating_brief_content_bundle_export.py`. It
  defines the frozen, slotted
  `AdvisoryOperatingBriefContentBundleExport` dataclass and pure
  `export_advisory_operating_brief_content_bundle(...)` builder. The builder
  requires an exact `AdvisoryOperatingBriefContentBundle`, rejects non-bundle,
  malformed bundle-like, and subclass inputs, and exposes only in-memory
  metadata/output views: the primitive `bundle.to_dict()` payload, compact
  sorted JSON text with `separators=(",", ":")`, and the exact Phase 163
  `render_advisory_operating_brief_content_bundle_text(bundle)` rendered text.
  Tests pin the Phase 162 synthetic payload and compact JSON, verify JSON
  round-tripping and rendered text equivalence, prove repeated export is
  byte-for-byte deterministic, prove source bundle `to_dict()` stability, and
  cover payload mutation isolation. AST and literal guardrails prove the module
  adds no forbidden paper/live/approved/trading-ready authority fields, file
  I/O, paths, CLI behavior, persistence, dashboard behavior, runtime/scheduler
  behavior, network/socket access, credentials, vendor APIs, notebooks,
  LLM/agent behavior, ML behavior, pandas/numpy/vectorbt/QuantConnect
  dependency behavior, broker/runtime behavior, strategy/signal/evaluator
  behavior, backtesting behavior, ranking/scoring, recommendations, allocation
  authority, orders, portfolio mutation, trading readiness, source approval,
  methodology approval, validation approval, trading authority, or new
  dependency behavior. Existing `AdvisoryOperatingBrief`, advisory operating
  brief renderer/export/CLI behavior, and content bundle renderer behavior
  remain unchanged; normal pytest remains offline, credential-free,
  deterministic, and safe
- Phase 166 - Advisory Operating Brief Content Bundle Export Regression Guard
  adds
  `tests/unit/test_advisory_operating_brief_content_bundle_export_regression.py`
  as a test-only guard for the Phase 165 in-memory export contract. It uses the
  Phase 162 synthetic content bundle fixture, exports through
  `export_advisory_operating_brief_content_bundle(...)`, pins the exact compact
  JSON export text, pins the exact rendered line tuple, derives the expected
  primitive payload from the pinned JSON, verifies JSON round-tripping, and
  verifies rendered text equality with
  `render_advisory_operating_brief_content_bundle_text(bundle)`. The guard also
  proves repeated exports are byte-for-byte deterministic, exported payload
  mutation is isolated from the source bundle and later exports, and source
  bundle `to_dict()` remains unchanged before and after export. It pins fixed
  advisory metadata (`bundle_type`, `status`, `authority`, and
  `capital_authority`), verifies candidate research and strategy eligibility
  branches remain present and ordered, verifies limitations and non-claims are
  present, and checks approval/readiness/recommendation/allocation/order/
  trading-authority language appears only as explicit non-claims/cautions from
  source metadata. Self-inspection guardrails prove the test itself adds no
  forbidden file I/O, paths, CLI behavior, persistence, runtime/scheduler
  behavior, network/socket access, credentials, vendor APIs, notebooks,
  LLM/agent behavior, broker/runtime behavior, strategy/signal/evaluator
  behavior, backtesting behavior, ranking/scoring, recommendations, allocation
  authority, orders, portfolio mutation, trading readiness, source approval,
  methodology approval, validation approval, trading authority, production-code
  changes, new dependencies, or existing `AdvisoryOperatingBrief`
  renderer/export/CLI chain behavior; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 167 - Advisory Operating Brief Content Bundle CLI Preview adds
  `src/algotrader/research/advisory_operating_brief_content_bundle_cli.py`,
  wires `algotrader advisory-operating-brief-content-bundle-preview` in
  `src/algotrader/cli.py`, and adds
  `tests/unit/test_advisory_operating_brief_content_bundle_cli.py`. The command
  builds a production-safe synthetic `AdvisoryOperatingBriefContentBundle`
  using only public builders, matches the Phase 162 synthetic content bundle
  fixture payload exactly, and exports through the Phase 165
  `export_advisory_operating_brief_content_bundle(...)` contract. It supports
  only default text output, `--format text`, and `--format json`; text stdout
  is exactly `export.rendered_text`; JSON stdout is exactly compact
  `export.json_text`; repeated text and JSON invocations are byte-for-byte
  deterministic; and JSON round-trips to the expected primitive payload. Tests
  also prove the command exposes no file/path/source/vendor/broker/runtime
  options, production preview code imports no `tests` or `tests.fixtures`, the
  existing `advisory-operating-brief-preview` command remains unchanged, and
  AST/literal guardrails add no forbidden file I/O, persistence,
  runtime/scheduler behavior, dashboard behavior, network/socket access,
  credentials, vendor APIs, notebooks, LLM/agent behavior, broker/runtime
  behavior, strategy/signal/evaluator behavior, backtesting behavior,
  ranking/scoring, recommendations, allocation authority, orders, portfolio
  mutation, trading readiness, source approval, methodology approval,
  validation approval, trading authority, actionable paper/live/approved/
  trading-ready authority fields, or dependency behavior. Normal pytest remains
  offline, credential-free, deterministic, and safe
- Phase 168 - Advisory Operating Brief Content Bundle CLI Regression Guard adds
  `tests/unit/test_advisory_operating_brief_content_bundle_cli_regression.py`
  as a test-only guard for the Phase 167 preview command. It invokes the
  command through the existing `main([...])` pattern; pins default text stdout,
  `--format text` stdout, and `--format json` stdout exactly against the Phase
  165 export pins for the Phase 162 synthetic content bundle; verifies default
  text equals explicit text; verifies JSON round-trips exactly to the expected
  primitive payload; and proves repeated text and JSON invocations are
  byte-for-byte deterministic. The guard verifies candidate research and
  strategy eligibility branches, advisory/candidate-only metadata, limitations,
  and non-claims remain present; verifies approval/readiness/recommendation/
  allocation/order/trading-authority language remains confined to explicit
  caution metadata; verifies no file/path/source/vendor/broker/runtime options
  are exposed; confirms existing `advisory-operating-brief-preview` text and
  JSON pins remain unchanged; and self-inspects the guard plus production
  preview module for no forbidden file I/O, persistence, network/socket,
  credential, vendor, broker, runtime/scheduler, dashboard, notebook, LLM/agent,
  strategy/signal/evaluator, backtesting, ranking/scoring, recommendation,
  allocation, order, portfolio mutation, readiness, approval, trading-authority,
  production-code, dependency, or content bundle renderer/export/CLI behavior
  changes. Normal pytest remains offline, credential-free, deterministic, and
  safe
- Phase 169 - Advisory Risk Authority Status Contract adds
  `src/algotrader/research/risk_authority_status.py` and
  `tests/unit/test_risk_authority_status.py`. It defines the frozen, slotted
  `RiskAuthorityStatus` dataclass and pure
  `build_risk_authority_status(...)` builder with fixed metadata
  `authority_type="risk_authority_status"`, `status="candidate_only"`,
  `authority="advisory_only"`, and `capital_authority=False`. Only
  `not_authorized`, `blocked`, and `research_only` are valid authority states.
  The contract stores only primitive advisory metadata, converts tuple/list
  inputs to immutable tuples, copies caller collections, and serializes through
  deterministic primitive `to_dict()` output with compact JSON pins. Required
  non-claims explicitly state that this is not risk approval, not allocation
  authority, not order authority, not paper readiness, not live readiness, not
  broker authority, not portfolio mutation authority, not capital authority,
  and not trading authority. Tests reject empty or malformed strings and
  collections, unknown states, and paper/live/authorized/trading-ready/
  allocation/order/broker/account/portfolio authority-like states. AST and
  literal guardrails prove the module adds no actionable trading-authority
  fields and no risk engine behavior, strategy/signal/evaluator behavior,
  backtesting behavior, broker/runtime behavior, order generation, allocation,
  portfolio mutation, reconciliation mutation, scheduler behavior, dashboard
  behavior, CLI behavior, file I/O, persistence, network/socket access,
  credentials, vendor APIs, LLM/agent behavior, notebooks, or dependencies;
  normal pytest remains offline, credential-free, deterministic, and safe
- Phase 170 - Synthetic Risk Authority Status Fixture adds
  `tests/fixtures/risk_authority_status.py` and
  `tests/unit/test_risk_authority_status_fixture.py`. The fixture uses the
  Phase 169 public `build_risk_authority_status(...)` builder to produce a
  deterministic `RiskAuthorityStatus` with `authority_state="not_authorized"`.
  Fixed advisory metadata remains pinned to
  `authority_type="risk_authority_status"`, `status="candidate_only"`,
  `authority="advisory_only"`, and `capital_authority=False`. The payload
  includes only synthetic reasons, blockers, required next steps, limitations,
  non-claims, evidence refs, and related strategy ids. Non-claims explicitly
  deny risk approval, allocation authority, order authority, paper readiness,
  live readiness, broker authority, portfolio mutation authority, capital
  authority, trading authority, trading recommendation, order placement,
  broker access, and portfolio mutation. Tests pin exact primitive dictionary
  output, compact JSON bytes, tuple storage/list serialization, repeated
  construction determinism, fresh expected-helper list state, source collection
  non-mutation, public-builder usage, and AST/literal guardrails proving no
  forbidden broker/order/allocation/portfolio/trading-authority fixture fields
  or imports were added. No `src/` production code, CLI behavior, risk engine
  behavior, strategy execution behavior, signal/evaluator behavior,
  backtesting behavior, broker/runtime behavior, order generation, allocation,
  portfolio mutation, reconciliation mutation, scheduler behavior, dashboard
  behavior, file I/O, persistence, network/socket access, credentials, vendor
  APIs, LLM/agent behavior, notebooks, or dependencies changed; normal pytest
  remains offline, credential-free, deterministic, and safe
- Phase 171 - Advisory Risk Authority Brief Item adds
  `src/algotrader/research/risk_authority_brief_item.py` and
  `tests/unit/test_risk_authority_brief_item.py`. The contract defines the
  frozen, slotted `RiskAuthorityBriefItem` dataclass and pure
  `build_risk_authority_brief_item(...)` builder for deterministic
  advisory-only composition around an existing exact `RiskAuthorityStatus`.
  The item preserves source status object identity, rejects non-status inputs,
  malformed status-like objects, and subclass instances, and pins fixed
  metadata to `item_type="risk_authority_brief_item"`,
  `status="candidate_only"`, `authority="advisory_only"`, and
  `capital_authority=False`. It carries forward authority state, reasons,
  blockers, required next steps, limitations, non-claims, evidence refs, and
  related strategy ids; adds deterministic advisory-only headline/summary
  text; and includes the nested source status `to_dict()` payload. Tests pin
  exact primitive dictionary output, compact JSON output, tuple storage/list
  serialization, repeated construction determinism, nested Phase 170 fixture
  payload equality, source status non-mutation, direct constructor rejection
  when carried metadata diverges from the source, absence of `from_dict()`, and
  AST/literal guardrails proving no actionable authority fields or forbidden
  imports/calls were added. The item does not create risk approval,
  recommendation, paper readiness, live readiness, allocation authority, order
  authority, broker authority, portfolio mutation authority, capital authority,
  or trading authority. No risk engine behavior, strategy execution behavior,
  signal/evaluator behavior, backtesting behavior, broker/runtime behavior,
  order generation, allocation, portfolio mutation, reconciliation mutation,
  scheduler behavior, dashboard behavior, CLI behavior, file I/O, persistence,
  network/socket access, credentials, vendor APIs, LLM/agent behavior,
  notebooks, or dependencies changed; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 172 - Synthetic Risk Authority Brief Item Fixture adds
  `tests/fixtures/risk_authority_brief_item.py` and
  `tests/unit/test_risk_authority_brief_item_fixture.py`. The fixture composes
  Phase 170 `build_synthetic_risk_authority_status()` with the Phase 171
  `build_risk_authority_brief_item(...)` builder so validation is preserved and
  the source status remains the Phase 170 `RiskAuthorityStatus`. The expected
  helper composes from `expected_synthetic_risk_authority_status_dict()`, pins
  the nested source status dictionary exactly, and returns fresh primitive list
  state for top-level and nested payloads. Fixed metadata remains
  `item_type="risk_authority_brief_item"`, `status="candidate_only"`,
  `authority="advisory_only"`, and `capital_authority=False`; deterministic
  advisory-only headline/summary text is pinned; and authority state, reasons,
  blockers, required next steps, limitations, non-claims, evidence refs, and
  related strategy ids are carried forward. Non-claims deny risk approval,
  allocation authority, order authority, paper readiness, live readiness,
  broker authority, portfolio mutation authority, capital authority, trading
  authority, trading recommendation, order placement, broker access, and
  portfolio mutation. Tests pin exact dictionary output, compact JSON bytes,
  tuple storage/list serialization, repeated construction determinism, nested
  Phase 170 equality, source non-mutation, expected-helper freshness, and
  AST/literal guardrails proving no forbidden broker/order/allocation/
  portfolio/trading-authority fixture fields or imports were added. No `src/`
  production code, CLI behavior, risk engine behavior, strategy execution
  behavior, signal/evaluator behavior, backtesting behavior, broker/runtime
  behavior, order generation, allocation, portfolio mutation, reconciliation
  mutation, scheduler behavior, dashboard behavior, file I/O, persistence,
  network/socket access, credentials, vendor APIs, LLM/agent behavior,
  notebooks, or dependencies changed; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 173 - Advisory Risk Authority Brief Section adds
  `src/algotrader/research/risk_authority_brief_section.py` and
  `tests/unit/test_risk_authority_brief_section.py`. The contract defines the
  frozen, slotted `RiskAuthorityBriefSection` dataclass and pure
  `build_risk_authority_brief_section(...)` builder for deterministic
  metadata-only grouping of one or more exact `RiskAuthorityBriefItem` objects.
  It preserves source item object identity and input ordering, converts item
  collections to immutable tuples, rejects empty collections, malformed
  item-like objects, subclass instances, and duplicate item identities, and
  pins fixed metadata to `section_type="risk_authority_brief_section"`,
  `status="candidate_only"`, `authority="advisory_only"`, and
  `capital_authority=False`. Title and summary text are derived from item
  metadata and remain advisory-only; limitations and non-claims are carried
  forward in deterministic first-seen order with exact duplicates removed; and
  nested item `to_dict()` payloads are included in original order. Tests pin
  exact primitive dictionary output, compact JSON bytes, nested Phase 172 item
  equality, repeated construction determinism, source item non-mutation,
  direct constructor rejection when section metadata diverges from items,
  absence of `from_dict()`, and AST/literal guardrails proving no actionable
  authority fields, forbidden imports, forbidden calls, or runtime behavior
  were added. The section does not create risk approval, recommendation, paper
  readiness, live readiness, allocation authority, order authority, broker
  authority, portfolio mutation authority, capital authority, or trading
  authority. No risk engine behavior, strategy execution behavior,
  signal/evaluator behavior, backtesting behavior, broker/runtime behavior,
  order generation, allocation, portfolio mutation, reconciliation mutation,
  scheduler behavior, dashboard behavior, CLI behavior, file I/O, persistence,
  network/socket access, credentials, vendor APIs, LLM/agent behavior,
  notebooks, or dependencies changed; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 174 - Synthetic Risk Authority Brief Section Fixture adds
  `tests/fixtures/risk_authority_brief_section.py` and
  `tests/unit/test_risk_authority_brief_section_fixture.py`. The fixture
  composes the Phase 172 `build_synthetic_risk_authority_brief_item()` fixture
  with the Phase 173 `build_risk_authority_brief_section(...)` builder, so
  validation is preserved and the nested item remains the deterministic Phase
  172 `RiskAuthorityBriefItem`. The expected helper composes from
  `expected_synthetic_risk_authority_brief_item_dict()`, pins the nested item
  dictionary exactly, returns fresh primitive list state, and keeps fixed
  metadata at `section_type="risk_authority_brief_section"`,
  `status="candidate_only"`, `authority="advisory_only"`, and
  `capital_authority=False`. Title and summary text remain deterministic and
  advisory-only; limitations and non-claims are carried forward; and
  non-claims deny risk approval, allocation authority, order authority, paper
  readiness, live readiness, broker authority, portfolio mutation authority,
  capital authority, and trading authority. Tests pin exact dictionary output,
  nested Phase 172 item equality, compact JSON bytes, tuple storage/list
  serialization, repeated construction determinism, expected-helper freshness,
  source item non-mutation, and AST/literal guardrails proving no forbidden
  broker, order, allocation, portfolio, trading-authority fields, imports, or
  calls were added. No `src/` production code, CLI behavior, risk engine
  behavior, strategy execution behavior, signal/evaluator behavior,
  backtesting behavior, broker/runtime behavior, order generation, allocation,
  portfolio mutation, reconciliation mutation, scheduler behavior, dashboard
  behavior, file I/O, persistence, network/socket access, credentials, vendor
  APIs, LLM/agent behavior, notebooks, or dependencies changed; normal pytest
  remains offline, credential-free, deterministic, and safe
- Phase 175 - Advisory Risk Authority Brief Container adds
  `src/algotrader/research/risk_authority_brief.py` and
  `tests/unit/test_risk_authority_brief.py`. The contract defines the frozen,
  slotted `RiskAuthorityBrief` dataclass and pure
  `build_risk_authority_brief(...)` builder for deterministic metadata-only
  grouping of one or more exact `RiskAuthorityBriefSection` objects. It
  preserves source section object identity and input ordering, converts section
  collections to immutable tuples, rejects empty collections, malformed
  section-like objects, subclass instances, and duplicate section identities,
  and pins fixed metadata to `brief_type="risk_authority_brief"`,
  `status="candidate_only"`, `authority="advisory_only"`, and
  `capital_authority=False`. Title and summary text are derived from section
  metadata and remain advisory-only; limitations and non-claims are carried
  forward in deterministic first-seen order with exact duplicates removed; and
  nested section `to_dict()` payloads are included in original order. Tests pin
  exact primitive dictionary output, compact JSON bytes, nested Phase 174
  section equality, repeated construction determinism, source section
  non-mutation, direct constructor rejection when brief metadata diverges from
  sections, absence of `from_dict()`, and AST/literal guardrails proving no
  actionable authority fields, forbidden imports, forbidden calls, or runtime
  behavior were added. The brief does not create risk approval,
  recommendation, paper readiness, live readiness, allocation authority, order
  authority, broker authority, portfolio mutation authority, capital
  authority, or trading authority. No risk engine behavior, strategy execution
  behavior, signal/evaluator behavior, backtesting behavior, broker/runtime
  behavior, order generation, allocation, portfolio mutation, reconciliation
  mutation, scheduler behavior, dashboard behavior, CLI behavior, file I/O,
  persistence, network/socket access, credentials, vendor APIs, LLM/agent
  behavior, notebooks, or dependencies changed; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 176 - Synthetic Risk Authority Brief Fixture adds
  `tests/fixtures/risk_authority_brief.py` and
  `tests/unit/test_risk_authority_brief_fixture.py`. The fixture composes the
  Phase 174 `build_synthetic_risk_authority_brief_section()` fixture with the
  Phase 175 `build_risk_authority_brief(...)` builder, preserving validation
  and keeping the nested section as the deterministic Phase 174
  `RiskAuthorityBriefSection`. The expected helper composes from
  `expected_synthetic_risk_authority_brief_section_dict()`, pins the nested
  section dictionary exactly, returns fresh primitive list state, and keeps
  fixed metadata at `brief_type="risk_authority_brief"`,
  `status="candidate_only"`, `authority="advisory_only"`, and
  `capital_authority=False`. Title and summary text remain deterministic and
  advisory-only; limitations and non-claims are carried forward; and
  non-claims deny risk approval, allocation authority, order authority, paper
  readiness, live readiness, broker authority, portfolio mutation authority,
  capital authority, and trading authority. Tests pin exact dictionary output,
  nested Phase 174 section equality, compact JSON bytes, tuple storage/list
  serialization, repeated construction determinism, expected-helper freshness,
  source section non-mutation, and AST/literal guardrails proving no forbidden
  broker, order, allocation, portfolio, trading-authority fields, imports, or
  calls were added. No `src/` production code, CLI behavior, risk engine
  behavior, strategy execution behavior, signal/evaluator behavior,
  backtesting behavior, broker/runtime behavior, order generation, allocation,
  portfolio mutation, reconciliation mutation, scheduler behavior, dashboard
  behavior, file I/O, persistence, network/socket access, credentials, vendor
  APIs, LLM/agent behavior, notebooks, or dependencies changed; normal pytest
  remains offline, credential-free, deterministic, and safe
- Phase 177 - Advisory Operating Brief Content Bundle Risk Authority Branch
  extends `AdvisoryOperatingBriefContentBundle` in
  `src/algotrader/research/advisory_operating_brief_content_bundle.py` with an
  optional exact `RiskAuthorityBrief` family alongside existing candidate
  research and strategy eligibility families. The contract remains
  metadata-only: candidate and strategy behavior stays backward-compatible,
  any one or two families may be empty, at least one total brief is required,
  all collections are stored as immutable tuples, object identity and
  per-family input ordering are preserved, and duplicate object identities are
  rejected across supported collections. The risk branch rejects non-risk
  inputs, malformed risk-authority-like objects, and subclass instances.
  Fixed bundle metadata remains
  `bundle_type="advisory_operating_brief_content_bundle"`,
  `status="candidate_only"`, `authority="advisory_only"`, and
  `capital_authority=False`. Limitations and non-claims now carry forward from
  candidate research, strategy eligibility, and risk authority branches in
  deterministic first-seen order with exact duplicates removed. `to_dict()`
  stays primitive-only and deterministic; risk authority counts and nested risk
  authority brief payloads are emitted only when risk authority briefs are
  present, preserving existing serialized output for the prior synthetic
  candidate-plus-strategy fixture and leaving renderer/export/CLI regression
  behavior unchanged. Tests pin risk-only and all-family synthetic cases,
  nested Phase 176 risk brief equality, compact JSON, repeated construction
  determinism, source brief non-mutation, fixed metadata, and AST/literal
  guardrails. No existing `AdvisoryOperatingBrief` behavior, renderer/export/
  CLI behavior, risk engine behavior, strategy/signal/evaluator behavior,
  backtesting behavior, broker/runtime behavior, scheduler behavior, dashboard
  behavior, file I/O, persistence, network/socket access, credentials, vendor
  APIs, notebooks, LLM/agent behavior, dependencies, recommendation,
  allocation, order, portfolio mutation, paper-readiness, live-readiness,
  capital, or trading-authority behavior changed; normal pytest remains
  offline, credential-free, deterministic, and safe
- Phase 178 - Synthetic Advisory Operating Brief Content Bundle With Risk
  Fixture extends `tests/fixtures/advisory_operating_brief_content_bundle.py`
  with additive risk-inclusive fixture helpers and adds
  `tests/unit/test_advisory_operating_brief_content_bundle_with_risk_fixture.py`.
  The existing Phase 162 synthetic candidate-plus-strategy fixture functions
  and serialized output remain unchanged. The new fixture composes the
  existing synthetic `CandidateResearchBrief`, the Phase 160 synthetic
  `StrategyEligibilityBrief`, the Phase 176 synthetic `RiskAuthorityBrief`,
  and the Phase 177 `build_advisory_operating_brief_content_bundle(...)`
  builder, preserving validation. The expected helper pins fixed advisory
  metadata at `bundle_type="advisory_operating_brief_content_bundle"`,
  `status="candidate_only"`, `authority="advisory_only"`, and
  `capital_authority=False`; pins deterministic advisory-only title and
  summary text; carries limitations and non-claims forward from candidate
  research, strategy eligibility, and risk authority branches; and pins the
  nested Phase 176 risk authority dictionary exactly. Tests pin exact
  primitive dictionary output, compact JSON bytes, nested candidate, strategy,
  and risk payload equality, tuple storage/list serialization, repeated
  construction determinism, expected-helper fresh mutable list state, source
  brief non-mutation, old Phase 162 fixture compatibility, and AST/literal
  guardrails proving no forbidden broker, order, allocation, portfolio, or
  trading-authority fixture fields, imports, or calls were added. No `src/`
  production code, existing `AdvisoryOperatingBrief` behavior, renderer/export/
  CLI behavior, risk engine behavior, strategy/signal/evaluator behavior,
  backtesting behavior, broker/runtime behavior, scheduler behavior, dashboard
  behavior, file I/O, persistence, network/socket access, credentials, vendor
  APIs, notebooks, LLM/agent behavior, dependencies, recommendation,
  allocation, order, portfolio mutation, paper-readiness, live-readiness,
  capital, or trading-authority behavior changed; normal pytest remains
  offline, credential-free, deterministic, and safe
- Phase 179 - Advisory Operating Brief Content Bundle Renderer Risk Authority
  Branch extends
  `src/algotrader/research/advisory_operating_brief_content_bundle_renderer.py`
  so `render_advisory_operating_brief_content_bundle_text(...)` renders risk
  authority branch metadata only when `risk_authority_briefs` are present in
  `bundle.to_dict()`. It keeps exact
  `AdvisoryOperatingBriefContentBundle` input validation, renders only from
  the primitive `to_dict()` payload, preserves the Phase 162 no-risk
  candidate-plus-strategy text byte-for-byte, and keeps deterministic fixed
  headings, candidate, strategy, and risk branch order, and repeated byte
  output. The risk branch renders advisory-only brief, section, item, and
  source-status metadata including title, summary, `authority_state`, reasons,
  blockers, required next steps, evidence references, related strategy ids,
  limitations, and non-claims, with bundle-level limitations and non-claims
  still rendered after branch content. Tests pin the exact risk-inclusive line
  tuple, source bundle non-mutation, fixed metadata, all-branch limitations
  and non-claims, rejected non-bundle and subclass inputs, and AST/literal
  guardrails proving no forbidden network, vendor, broker, pandas, numpy,
  vectorbt, QuantConnect, ML, LLM, file I/O, persistence, scheduler/runtime,
  dashboard, CLI, dependency, or actionable authority output fields were
  added. No existing `AdvisoryOperatingBrief` behavior, existing renderer/
  export/CLI behavior, content bundle export/CLI behavior, risk engine
  behavior, strategy/signal/evaluator behavior, backtesting behavior,
  broker/runtime behavior, recommendation, allocation, order, portfolio
  mutation, paper-readiness, live-readiness, capital, or trading-authority
  behavior changed; normal pytest remains offline, credential-free,
  deterministic, and safe
- Phase 180 - Advisory Operating Brief Content Bundle Export Risk-Branch
  Regression Guard adds
  `tests/unit/test_advisory_operating_brief_content_bundle_export_with_risk_regression.py`
  as test-only coverage for the existing in-memory export path after the
  Phase 179 renderer update. The guard uses the Phase 178 risk-inclusive
  fixture and expected dictionary, pins export payload equality, compact sorted
  JSON, JSON round-trip behavior, rendered-text parity with
  `render_advisory_operating_brief_content_bundle_text(...)`, repeated
  byte-for-byte determinism, risk authority count and nested metadata
  presence, branch sequence with candidate and strategy content before risk
  authority, limitations/non-claims preservation, and source bundle
  non-mutation. It also self-inspects the new test file for forbidden imports,
  calls, and authority-state terms. No `src/` production code, existing
  `AdvisoryOperatingBrief` behavior, content bundle/renderer/export/CLI
  behavior, risk engine behavior, strategy/signal/evaluator behavior,
  backtesting behavior, broker/runtime behavior, scheduler behavior, dashboard
  behavior, file I/O, persistence, network/socket access, credentials, vendor
  APIs, notebooks, ML, LLM/agent behavior, dependencies, allocation, order,
  portfolio mutation, paper/live readiness, capital, or trading-authority
  behavior changed; normal pytest remains offline, credential-free,
  deterministic, and safe
- Phase 181 - Advisory Operating Brief Content Bundle CLI Risk Preview extends
  `algotrader advisory-operating-brief-content-bundle-preview` with the
  explicit synthetic-only `--include-risk-authority` flag. Without the flag,
  default text, `--format text`, and compact `--format json` output remain
  byte-for-byte identical to the existing no-risk preview. With the flag, the
  CLI composes candidate research, strategy eligibility, and risk authority
  branches using only public production builders, exports through
  `export_advisory_operating_brief_content_bundle(...)`, renders text by
  default, and emits compact sorted JSON with `--format json`. Tests prove the
  risk branch text is present, JSON includes `risk_authority_briefs` and
  `risk_authority_brief_count`, risk-inclusive invocations are byte-for-byte
  deterministic and JSON round-trips, production CLI modules import no
  `tests` or `tests.fixtures`, no file/path/source/vendor/broker/network/
  runtime/credential options were introduced, and no paper/live/approved/
  trading-ready/actionable authority states or fields were added. No real
  data, ingestion, persistence, file I/O, network/socket access, credentials,
  vendor APIs, scheduler/dashboard behavior, notebooks, ML, LLM/agent
  behavior, strategy/signal/evaluator behavior, backtesting, ranking/scoring,
  recommendations, allocation/order/portfolio mutation, risk approval,
  paper/live readiness, capital authority, or trading authority changed;
  normal pytest remains offline, credential-free, deterministic, and safe
- Phase 182 - Advisory Research Queue Brief Family adds a metadata-only
  research queue branch in `src/algotrader/research/research_queue_status.py`,
  `src/algotrader/research/research_queue_brief_item.py`,
  `src/algotrader/research/research_queue_brief_section.py`, and
  `src/algotrader/research/research_queue_brief.py`. It models unresolved
  research work, blockers, required next steps, evidence gaps, related
  strategy ids, limitations, and advisory non-claims while pinning all levels
  to `candidate_only`, `advisory_only`, and `capital_authority=False`. Tests
  cover builders, direct-constructor validation, immutability, slots, tuple
  conversion and input non-mutation, deterministic primitive-only `to_dict()`,
  identity/order preservation, duplicate identity rejection, malformed input,
  required non-claims, forbidden language/state rejection, and AST/import
  guardrails. No existing content bundle, renderer, export, CLI,
  source/data approval, methodology approval, signal/evaluator behavior,
  strategy execution, backtesting, ranking/scoring, recommendations,
  allocation/order/portfolio mutation, broker/runtime behavior,
  scheduler/dashboard behavior, paper/live readiness, capital authority,
  trading authority, file I/O, persistence, network/socket access,
  credentials, vendor APIs, notebooks, ML, LLM/agent behavior, or dependency
  behavior changed; normal pytest remains offline, credential-free,
  deterministic, and safe
- Phase 183 - Synthetic Research Queue Brief Fixture adds
  `tests/fixtures/research_queue_brief.py` and
  `tests/unit/test_research_queue_brief_fixture.py` as deterministic
  fixture-only support for the Phase 182 research queue family. The synthetic
  broad ETF SMA queue item is unresolved advisory metadata, not approved
  strategy evidence: it records blockers, required next steps, evidence gaps,
  related synthetic/advisory strategy ids, internal advisory evidence refs,
  limitations, and explicit non-claims. Expected dictionary helpers match
  `to_dict()` exactly, return fresh mutable primitive copies, and repeated
  construction is byte-for-byte deterministic. Tests prove exact Phase 182
  production types, item/source status identity, section item identity/order,
  brief section identity/order, fixed advisory metadata, limitation/non-claim
  carry-forward, absence of actionable authority states, and fixture
  AST/import/call/literal guardrails. No `src/`, content bundle, renderer,
  export, CLI, source/data approval, methodology approval, signal/evaluator,
  strategy execution, backtesting, ranking/scoring, recommendation,
  allocation/order/portfolio mutation, broker/runtime, scheduler/dashboard,
  paper/live readiness, capital authority, trading authority, file I/O,
  persistence, network/socket, credential, vendor API, notebook, ML,
  LLM/agent, or dependency behavior changed; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 184 - Advisory Operating Brief Content Bundle Research Queue
  Integration adds the Phase 182/183 `ResearchQueueBrief` family as an
  optional fourth branch in
  `src/algotrader/research/advisory_operating_brief_content_bundle.py`. The
  bundle still pins
  `bundle_type="advisory_operating_brief_content_bundle"`,
  `status="candidate_only"`, `authority="advisory_only"`, and
  `capital_authority=False`. The builder accepts candidate research, strategy
  eligibility, risk authority, and research queue brief iterables; each branch
  may be empty, but at least one total brief is required. Tests prove exact
  type validation, malformed input rejection, object identity/order
  preservation within every branch, duplicate identity rejection across all
  branches, first-seen limitation/non-claim de-duplication, deterministic
  primitive-only serialization, and no `from_dict()`. Existing Phase 162
  candidate+strategy and Phase 178 candidate+strategy+risk fixture payloads
  remain exactly unchanged, while the new
  `build_synthetic_advisory_operating_brief_content_bundle_with_research_queue()`
  and
  `expected_synthetic_advisory_operating_brief_content_bundle_with_research_queue_dict()`
  helpers compose candidate, strategy, risk, and research queue branches
  through the production builder and emit `research_queue_brief_count` plus
  `research_queue_briefs`. Renderer, export, CLI, source/data approval,
  methodology approval, signal/evaluator, strategy execution, backtesting,
  ranking/scoring, recommendation, allocation/order/portfolio mutation,
  risk approval, broker/runtime, scheduler/dashboard, paper/live readiness,
  capital authority, trading authority, file I/O, persistence, network/socket,
  credential, vendor API, notebook, ML, LLM/agent, and dependency behavior are
  unchanged; normal pytest remains offline, credential-free, deterministic,
  and safe
- Phase 185 - Advisory Operating Brief Content Bundle Renderer Research Queue
  Branch extends
  `src/algotrader/research/advisory_operating_brief_content_bundle_renderer.py`
  to conditionally render the Phase 184 `research_queue_briefs` branch from
  `bundle.to_dict()` only. Existing Phase 162 candidate+strategy and Phase 178
  candidate+strategy+risk renderer output remains byte-for-byte unchanged.
  Research-queue-inclusive rendering now includes deterministic branch,
  brief, section, item, and source status metadata: queue id, title, research
  state, priority bucket, topic, hypothesis, blockers, required next steps,
  evidence gaps, related strategy ids, evidence refs, limitations, and
  non-claims. Tests prove candidate, strategy, risk, and research queue branch
  order; repeated byte-for-byte deterministic rendering; source bundle and
  payload non-mutation; dictionary-only renderer access for the new branch;
  and AST/import/call/literal guardrails. Content bundle construction, export,
  CLI, source/data approval, methodology approval, signal/evaluator, strategy
  execution, backtesting, ranking/scoring, recommendation,
  allocation/order/portfolio mutation, risk approval, broker/runtime,
  scheduler/dashboard, paper/live readiness, capital authority, trading
  authority, file I/O, persistence, network/socket, credential, vendor API,
  notebook, ML, LLM/agent, and dependency behavior are unchanged; normal pytest
  remains offline, credential-free, deterministic, and safe
- Phase 186 - Advisory Operating Brief Content Bundle Export Research Queue
  Regression Guard adds
  `tests/unit/test_advisory_operating_brief_content_bundle_export_with_research_queue_regression.py`
  as a test-only guard around the existing in-memory export path for the
  Phase 184/185 research-queue-inclusive content bundle. It uses the synthetic
  research queue content bundle builder and expected dictionary helper, pins
  `export.payload` exactly, pins compact deterministic JSON with
  `sort_keys=True` and `separators=(",", ":")`, verifies JSON round-trip
  behavior, and confirms `export.rendered_text` still equals
  `render_advisory_operating_brief_content_bundle_text(bundle)`. Tests also
  prove repeated exports are byte-for-byte deterministic; candidate, strategy,
  risk, and research queue branches are all present; `research_queue_brief_count`
  and `research_queue_briefs` are emitted; nested research queue
  brief/section/item/source-status metadata is preserved; branch sequence is
  deterministic; limitations and explicit non-claims are preserved in payload
  and rendered output; exported payload mutation does not mutate the source
  bundle or later exports; and the new test file imports/calls no forbidden
  behavior. No `src/`, content bundle, renderer, export, CLI, source/data
  approval, methodology approval, signal/evaluator, strategy execution,
  backtesting, ranking/scoring, recommendation, allocation/order/portfolio
  mutation, risk approval, broker/runtime, scheduler/dashboard, paper/live
  readiness, capital authority, trading authority, file I/O, persistence,
  network/socket, credential, vendor API, notebook, ML, LLM/agent, or
  dependency behavior changed; normal pytest remains offline, credential-free,
  deterministic, and safe
- Phase 187 - Advisory Operating Brief Content Bundle CLI Research Queue
  Preview adds the explicit synthetic-only `--include-research-queue` flag to
  `algotrader advisory-operating-brief-content-bundle-preview`. The existing
  default text/JSON preview remains candidate research plus strategy
  eligibility only, and the existing `--include-risk-authority` text/JSON
  preview remains byte-for-byte unchanged. The new flag composes candidate,
  strategy, and research queue branches; combining it with
  `--include-risk-authority` composes candidate, strategy, risk, and research
  queue branches. The CLI continues to return
  `export_advisory_operating_brief_content_bundle(...).rendered_text` for text
  and compact deterministic `json_text` for JSON. Tests prove parser
  acceptance, branch presence/omission, both-flag branch composition, JSON
  round-trip behavior, repeated byte-for-byte deterministic CLI output, no
  production imports from `tests` or `tests.fixtures`, no file/path/source/
  vendor/broker/network/runtime/credential options, and no paper/live/
  approved/trading-ready/actionable authority states. No real data, ingestion,
  persistence, file I/O, network/socket, credential, vendor API,
  scheduler/dashboard, notebook, ML, LLM/agent, dependency, source/data
  approval, methodology approval, strategy/signal/evaluator, backtesting,
  ranking/scoring, recommendation, allocation/order/portfolio mutation, risk
  approval, paper/live readiness, capital authority, or trading authority
  behavior changed; normal pytest remains offline, credential-free,
  deterministic, and safe
- Phase 188 - Advisory Operating Brief Package Contract adds
  `src/algotrader/research/advisory_operating_brief_package.py` with frozen/
  slotted `AdvisoryOperatingBriefPackage` and
  `build_advisory_operating_brief_package(...)`. The builder requires an exact
  `AdvisoryOperatingBriefContentBundle`, preserves source bundle identity,
  builds `content_bundle_export` through the existing
  `export_advisory_operating_brief_content_bundle(...)`, pins
  `package_type="advisory_operating_brief_package"`,
  `status="candidate_only"`, `authority="advisory_only"`, and
  `capital_authority=False`, and carries forward bundle limitations and
  non-claims with first-seen dedupe. `to_dict()` emits deterministic
  primitive-only package metadata, `content_bundle.to_dict()`, a primitive
  `content_bundle_export` dictionary with `payload`, `json_text`, and
  `rendered_text`, plus limitations and non-claims. Tests cover builder and
  direct construction, frozen/slots behavior, exact-type rejection for
  subclasses and lookalikes, export value matching, repeated determinism,
  source bundle and export payload non-mutation, primitive-only serialization,
  absence of `from_dict()`, malformed metadata rejection, positive
  authority-like language rejection, no production imports from `tests` or
  `tests.fixtures`, and AST/import/call guardrails. Existing
  `AdvisoryOperatingBrief`, content bundle, renderer, export, CLI, real data,
  ingestion, persistence, file I/O, network/socket, credential, vendor API,
  broker/runtime, scheduler/dashboard, notebook, ML, LLM/agent, dependency,
  source/data approval, methodology approval, strategy/signal/evaluator,
  backtesting, ranking/scoring, recommendation, allocation/order/portfolio
  mutation, risk approval, paper/live readiness, capital authority, and
  trading authority behavior are unchanged; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 189 - Synthetic Advisory Operating Brief Package Fixture adds the
  test-only `tests/fixtures/advisory_operating_brief_package.py` helper pair
  and `tests/unit/test_advisory_operating_brief_package_fixture.py`. The
  builder composes the existing research-queue-inclusive synthetic content
  bundle through `build_advisory_operating_brief_package(...)` with fixed
  metadata:
  `package_id="advisory-operating-brief-package:synthetic:2026-01-20"`,
  `title="Synthetic advisory operating brief package"`, advisory-only
  synthetic package summary text, and `as_of="2026-01-20"`. The expected dict
  helper returns the exact `to_dict()` payload as fresh mutable primitive
  copies. Tests prove repeated construction and compact JSON bytes are
  deterministic; nested `content_bundle` equals the expected candidate,
  strategy, risk, and research queue bundle; nested
  `content_bundle_export.payload`, `json_text`, and `rendered_text` match the
  existing export and renderer behavior; source content bundle identity is
  preserved; fixed metadata, carried limitations, carried non-claims, and
  absence of `from_dict()` are pinned; and fixture AST/import/call/literal
  guardrails exclude file I/O, persistence, network/socket, credential, vendor
  API, broker/account/order/fill/allocation/portfolio mutation, runtime,
  scheduler/dashboard, notebook, ML, LLM/agent, ranking/scoring,
  approval/readiness/trading authority, and actionable behavior. No `src/`,
  existing `AdvisoryOperatingBrief`, content bundle, renderer, export, CLI,
  package production, source/data approval, methodology approval,
  strategy/signal/evaluator, backtesting, recommendation, allocation/order/
  portfolio mutation, risk approval, paper/live readiness, capital authority,
  or trading authority behavior changed; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 190 - Advisory Operating Brief Package Text Renderer adds
  `src/algotrader/research/advisory_operating_brief_package_renderer.py` with
  `render_advisory_operating_brief_package_text(package)`. The renderer
  accepts only the exact `AdvisoryOperatingBriefPackage` type, rejects
  subclasses, lookalikes, dictionaries, and `None`, and renders from
  `package.to_dict()` only. It emits package type, package id, title, summary,
  as-of, status, authority, and capital authority in deterministic order,
  then a content bundle section containing the stored
  `content_bundle_export.rendered_text` exactly, followed by package-level
  limitations and non-claims. Tests pin the exact rendered line tuple, prove
  byte-for-byte repeated determinism, confirm rendering does not mutate the
  source package dictionary, nested content bundle identity, or stored export
  payload, and verify candidate research, strategy eligibility, risk
  authority, and research queue branches flow through the nested rendered
  content bundle. Production AST/import/call guardrails prove no imports from
  `tests` or `tests.fixtures`, no `from_dict()`, no direct reads from nested
  package objects, and no file I/O, persistence, network/socket, credential,
  vendor API, broker/account/order/fill/allocation/portfolio mutation,
  runtime, scheduler/dashboard, notebook, ML, LLM/agent, ranking/scoring,
  approval/readiness/trading authority, or actionable behavior. Existing
  `AdvisoryOperatingBrief`, package, package fixture, content bundle, content
  bundle renderer, content bundle export, and CLI behavior are unchanged;
  normal pytest remains offline, credential-free, deterministic, and safe
- Phase 191 - Advisory Operating Brief Package Export Contract adds
  `src/algotrader/research/advisory_operating_brief_package_export.py` with
  frozen/slotted `AdvisoryOperatingBriefPackageExport` and
  `export_advisory_operating_brief_package(package)`. The builder accepts
  only the exact `AdvisoryOperatingBriefPackage`, rejects subclasses,
  lookalikes, dictionaries, and `None`, sets payload from `package.to_dict()`,
  emits compact deterministic JSON with `sort_keys=True` and
  `separators=(",", ":")`, and uses
  `render_advisory_operating_brief_package_text(package)` for rendered text.
  Direct construction requires a non-empty primitive payload dictionary,
  non-empty compact JSON text that round-trips to the payload, and non-empty
  rendered text. The stored payload is defensively copied and repeated
  `payload` access returns fresh primitive copies. Tests prove Phase 189
  fixture acceptance, payload/json/rendered parity, byte-for-byte repeated
  determinism, package `to_dict()` non-mutation, nested content bundle
  identity preservation, nested content bundle export non-mutation,
  frozen/slotted behavior, exact type rejection, absence of `from_dict()`,
  no production imports from `tests` or `tests.fixtures`, and
  AST/import/call/source guardrails. Existing `AdvisoryOperatingBrief`,
  package, package fixture, package renderer, content bundle, content bundle
  renderer/export, and CLI behavior are unchanged; no file I/O, persistence,
  network/socket, credential, vendor API, broker/account/order/fill/
  allocation/portfolio mutation, runtime, scheduler/dashboard, notebook, ML,
  LLM/agent, ranking/scoring, approval/readiness/trading authority, or
  actionable behavior was added; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 192 - Advisory Operating Brief Package CLI Preview adds
  `src/algotrader/research/advisory_operating_brief_package_cli.py` and
  registers `algotrader advisory-operating-brief-package-preview`. The command
  is synthetic-only, accepts only `--format text` or `--format json`, defaults
  to text, builds a deterministic production-builder package with candidate
  research, strategy eligibility, risk authority, and research queue content in
  the nested bundle, pins
  `package_id="advisory-operating-brief-package:synthetic:2026-01-20"`,
  `title="Synthetic advisory operating brief package"`, advisory-only
  synthetic summary text, and `as_of="2026-01-20"`, and prints the rendered
  text or compact JSON from `export_advisory_operating_brief_package(...)`.
  Tests prove default/text parity, export rendered and JSON parity, JSON
  round-trip to the expected payload, byte-for-byte repeated determinism,
  package metadata visibility, nested candidate/strategy/risk/research-queue
  branch visibility, unchanged existing content-bundle CLI behavior, no
  production imports from `tests` or `tests.fixtures`, no external input
  options, no paper/live/approved/trading-ready/actionable authority states,
  and no file I/O, persistence, network/socket, credential, vendor API,
  broker/account/order/fill/allocation/portfolio mutation, runtime,
  scheduler/dashboard, notebook, ML, LLM/agent, ranking/scoring,
  approval/readiness/trading authority, actionable behavior, or dependency
  additions. Existing `AdvisoryOperatingBrief`, package, package renderer/
  export, content bundle, content bundle renderer/export, and content bundle
  CLI behavior are unchanged; normal pytest remains offline, credential-free,
  deterministic, and safe
- Phase 193 - Advisory Operating Brief Package CLI Regression Guard adds
  `tests/unit/test_advisory_operating_brief_package_cli_regression.py` as a
  test-only pin for `algotrader advisory-operating-brief-package-preview`.
  The guard compares default text, explicit text, and compact JSON stdout
  against `export_advisory_operating_brief_package(...)` using the current
  package preview builder, proves JSON round-trips to the exported preview
  payload, checks package
  metadata, nested candidate research, strategy eligibility, risk authority,
  research queue, advisory-only/candidate-only/capital-authority-false
  metadata, limitations, and non-claims, and proves repeated default/text/JSON
  invocations are byte-for-byte deterministic. It also verifies the package
  preview exposes only `--format text|json`, no file/path/source/vendor/
  broker/network/runtime/credential options are present, existing content
  bundle preview default, risk, research queue, and combined-flag outputs are
  unchanged, and AST/import/call/source guardrails add no file I/O,
  persistence, network/socket, credential, vendor API, broker/account/order/
  fill/allocation/portfolio mutation, runtime, scheduler/dashboard, notebook,
  ML, LLM/agent, ranking/scoring, recommendations, approval/readiness/trading
  authority, actionable behavior, or dependencies. Production package,
  package renderer/export, content bundle, content bundle renderer/export, and
  CLI behavior are unchanged; normal pytest remains offline, credential-free,
  deterministic, and safe
- Phase 194 - Advisory Operating Brief Package Synthetic Preview Alignment
  adds
  `src/algotrader/research/advisory_operating_brief_package_synthetic.py` with
  `build_synthetic_advisory_operating_brief_package_preview()` as the single
  production-safe synthetic package preview builder. The builder composes the
  production synthetic content bundle preview with candidate research, strategy
  eligibility, risk authority, and research queue branches, then calls
  `build_advisory_operating_brief_package(...)` with
  `package_id="advisory-operating-brief-package:synthetic:2026-01-20"`,
  `title="Synthetic advisory operating brief package"`, advisory-only
  synthetic summary text, and `as_of="2026-01-20"`. The package CLI preview
  renders from this canonical builder, and the package fixture delegates to it
  while returning fresh primitive `to_dict()` payloads. Fixture, CLI, and Phase
  193 regression tests now pin default text, explicit text, compact JSON, and
  export payloads against the fixture package, proving fixture/CLI byte parity
  and repeated deterministic output. Guardrails cover the production synthetic
  module with no imports from `tests` or `tests.fixtures`, no new external
  input options, no paper/live/approved/trading-ready/actionable states, and no
  file I/O, persistence, network/socket, credential, vendor API,
  broker/account/order/fill/allocation/portfolio mutation, runtime,
  scheduler/dashboard, notebook, ML, LLM/agent, ranking/scoring,
  recommendations, approval/readiness/trading authority, actionable behavior,
  or dependencies. Existing `AdvisoryOperatingBrief`, package contract,
  renderer/export, content bundle contract, content bundle renderer/export, and
  content bundle CLI behavior are unchanged; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 195 - Synthetic SMA Research Observation Mechanics adds
  `src/algotrader/research/sma_research_observation.py` with frozen/slotted
  `SmaResearchPricePoint`, frozen/slotted `SmaResearchObservation`, and pure
  `build_sma_research_observation(...)`. The builder is fixture-only research
  mechanics: it validates ISO `YYYY-MM-DD` dates with standard library parsing,
  sorts price points deterministically by date, rejects duplicate dates,
  non-price-point inputs, non-positive closes, empty symbol/as-of strings,
  malformed limitations/non-claims, and invalid windows, uses only samples with
  `date <= as_of`, counts later samples as ignored, and computes a Decimal SMA
  from the latest eligible window only. Below-window observations emit
  `position_vs_sma="insufficient_history"` with SMA and distance fields set to
  `None`; complete windows emit `above`, `below`, or `equal` based only on
  Decimal distance from the SMA. `to_dict()` is deterministic and
  primitive-only, serializing Decimals as strings and tuples as lists, with no
  `from_dict()`. Required non-claims deny strategy approval, source/data
  approval, predictive validity, profitability, recommendation,
  signal/evaluator behavior, allocation/order authority, broker authority,
  portfolio mutation authority, paper/live readiness, capital authority, and
  trading authority. Tests prove exact above/below/equal/insufficient payloads,
  future-sample ignoring, malformed input rejection, frozen/slotted behavior,
  repeated deterministic construction, primitive serialization, no actionable
  payload keys, no imports from tests or fixtures, and AST/import guardrails
  against file I/O, persistence, network/socket, vendor APIs, broker/runtime
  behavior, scheduler/dashboard, notebook, ML, LLM/agent, ranking/scoring,
  recommendations, approvals/readiness, allocation/order/portfolio mutation,
  capital authority, trading authority, or new dependencies. Advisory package,
  package synthetic builder, package CLI, content bundle, renderer, export, and
  existing CLI behavior are unchanged; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 196 - Synthetic SMA Research Observation Fixture adds
  `tests/fixtures/sma_research_observation.py` and
  `tests/unit/test_sma_research_observation_fixture.py` as a tests-only layer
  over the Phase 195 SMA observation contract. The fixture exposes
  deterministic synthetic broad ETF SMA-like price points for
  `symbol="SYNTH_ETF"`, `as_of="2026-01-20"`, and `window=3`, exact expected
  primitive dictionaries for price points, the primary above-SMA observation,
  and an insufficient-history observation. The primary fixture pins one
  ignored future sample, three eligible samples, `latest_close="110.00"`,
  `sma_value="100.00"`, `distance_from_sma="10.00"`,
  `distance_from_sma_pct="0.1"`, and `position_vs_sma="above"`. The
  insufficient-history fixture has fewer eligible samples than the window,
  preserves `latest_close="101.00"`, emits
  `position_vs_sma="insufficient_history"`, and leaves SMA and distance fields
  as `None`. Tests prove exact Phase 195 production types, `.to_dict()` parity,
  fresh mutable primitive expected dict copies, repeated deterministic
  construction, deterministic compact JSON bytes, pinned future-sample counts,
  fixed advisory metadata, required limitations and non-claims, absence of
  paper/live/approved/trading-ready/actionable authority states, and
  AST/import/call/source guardrails against broker/account/order/fill/
  allocation/portfolio mutation behavior, file I/O, persistence,
  network/socket access, vendor APIs, credentials, runtime/scheduler/dashboard
  behavior, notebooks, ML, LLM/agent behavior, ranking/scoring,
  recommendations, approval/readiness/trading authority language outside
  explicit non-claims, and `from_dict()`. No `src` files, advisory operating
  brief package, package synthetic builder, package CLI, content bundle,
  renderer, export, existing CLI behavior, real data ingestion, evaluator,
  backtesting, strategy execution, or dependencies changed; normal pytest
  remains offline, credential-free, deterministic, and safe
- Phase 197 - SMA Research Observation Brief Item adds
  `src/algotrader/research/sma_research_observation_brief.py` with
  frozen/slotted `SmaResearchObservationBriefItem` and
  `build_sma_research_observation_brief_item(observation)`. The wrapper
  accepts only the exact Phase 195 `SmaResearchObservation`, preserves source
  observation identity, pins `item_type="sma_research_observation_brief_item"`,
  `status="candidate_only"`, `authority="advisory_only"`, and
  `capital_authority=False`, maps `position_vs_sma` to
  `above_sma_observation`, `below_sma_observation`,
  `equal_sma_observation`, or `insufficient_history`, and generates
  deterministic non-actionable headline and summary text from observation
  metadata only. It carries source limitations and non-claims forward with
  first-seen de-dupe, validates direct construction against the source
  observation, rejects malformed lookalikes and subclasses, emits
  primitive-only deterministic `to_dict()` output with nested
  `source_observation.to_dict()`, does not mutate the source observation, and
  adds no `from_dict()`. Tests cover above-SMA and insufficient-history fixture
  wrapping, exact source identity, fixed metadata, mechanical mapping,
  headline/summary determinism, non-claim carry-forward, compact JSON byte
  determinism, source non-mutation, frozen/slotted behavior, no public
  buy/sell/hold/signal/evaluator/order/allocation/broker/portfolio/
  trading-authority payload fields, no production imports from `tests` or
  `tests.fixtures`, and AST/import/call/source guardrails against file I/O,
  persistence, network/socket access, vendor APIs, credentials,
  broker/runtime behavior, scheduler/dashboard behavior, notebooks, ML,
  LLM/agent behavior, ranking/scoring, recommendations, approval/readiness,
  allocation/order/portfolio mutation, capital authority, trading authority,
  or dependencies. SMA research observation mechanics and fixtures, advisory
  operating brief package, package synthetic builder, package CLI, content
  bundle, renderer, export, and existing CLI behavior are unchanged; normal
  pytest remains offline, credential-free, deterministic, and safe
- Phase 198 - Synthetic SMA Research Observation Brief Fixture adds
  `tests/fixtures/sma_research_observation_brief.py` and
  `tests/unit/test_sma_research_observation_brief_fixture.py` as a tests-only
  layer over the Phase 197 brief item. The primary fixture builds from
  `build_synthetic_sma_research_observation()`, preserves the source
  observation carried by the wrapper, pins
  `mechanical_state="above_sma_observation"`, and nests
  `source_observation` matching
  `expected_synthetic_sma_research_observation_dict()`. The
  insufficient-history fixture builds from
  `build_synthetic_insufficient_history_sma_research_observation()`, pins
  `mechanical_state="insufficient_history"`, and nests
  `source_observation` matching
  `expected_synthetic_insufficient_history_sma_research_observation_dict()`.
  Expected dict helpers return fixed
  `item_type="sma_research_observation_brief_item"`,
  candidate-only/advisory-only/capital-authority-false metadata,
  deterministic headline/summary text, source limitations, source non-claims,
  and fresh primitive nested payload copies. Tests prove exact Phase 197
  production type construction, `.to_dict()` parity, fresh mutable primitive
  expected dicts, deterministic repeated construction, compact JSON byte
  determinism, Phase 196 nested payload parity, source observation identity
  preservation through the wrapper, limitation/non-claim carry-forward, no
  `from_dict()`, no paper/live/approved/trading-ready/actionable authority
  states outside explicit non-claims, and fixture AST/import/call/source
  guardrails against broker/account/order/fill/allocation/portfolio mutation
  behavior, file I/O, persistence, network/socket access, vendor APIs,
  credentials, runtime/scheduler/dashboard behavior, notebooks, ML, LLM/agent
  behavior, ranking/scoring, recommendations, approval/readiness/trading
  authority language outside explicit non-claims, or dependencies. No `src`
  files, SMA mechanics, SMA observation fixtures, advisory operating brief
  package, package synthetic builder, package CLI, content bundle, renderer,
  export, or existing CLI behavior changed; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 199 - SMA Research Observation Brief Section adds
  `src/algotrader/research/sma_research_observation_brief_section.py` with
  frozen/slotted `SmaResearchObservationBriefSection` and
  `build_sma_research_observation_brief_section(section_id, title, summary,
  items)`. The section is a deterministic metadata-only advisory container for
  exact Phase 197 `SmaResearchObservationBriefItem` objects. It pins
  `section_type="sma_research_observation_brief_section"`,
  candidate-only/advisory-only/capital-authority-false metadata, requires
  non-empty advisory-safe section id/title/summary text, requires at least one
  exact brief item, rejects malformed lookalikes and subclasses, rejects
  duplicate item identities, and preserves item identity and order. The builder
  carries item limitations and non-claims forward with first-seen de-dupe;
  direct construction validates fixed metadata and item-derived
  limitations/non-claims. `to_dict()` emits primitive-only deterministic output
  with item count, nested `item.to_dict()` payloads, limitations, and
  non-claims without mutating source items. Tests build a two-item section from
  the Phase 198 above-SMA and insufficient-history fixtures, prove
  identity/order preservation, empty/duplicate/exact-type rejection, fixed
  advisory metadata, de-duped limitation/non-claim carry-forward, compact JSON
  byte determinism, source item non-mutation, frozen/slotted behavior, no
  `from_dict()`, no public buy/sell/hold/signal/evaluator/order/allocation/
  broker/portfolio/trading-authority payload fields, no production imports
  from `tests` or `tests.fixtures`, and AST/import/call/source guardrails
  against file I/O, persistence, network/socket access, vendor APIs,
  credentials, broker/runtime behavior, scheduler/dashboard behavior,
  notebooks, ML, LLM/agent behavior, ranking/scoring, recommendations,
  approval/readiness, allocation/order/portfolio mutation, capital authority,
  trading authority, or dependencies. SMA mechanics, SMA observation fixtures,
  SMA observation brief item behavior, advisory operating brief package,
  package synthetic builder, package CLI, content bundle, renderer, export,
  and existing CLI behavior are unchanged; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 200 - Synthetic SMA Research Observation Brief Section Fixture adds
  `tests/fixtures/sma_research_observation_brief_section.py` and
  `tests/unit/test_sma_research_observation_brief_section_fixture.py` as a
  tests-only layer over the Phase 199 section container. The fixture builds
  from the Phase 198 above-SMA and insufficient-history brief item fixtures,
  uses
  `section_id="sma-research-observation-section:synthetic:broad-etf-sma"`,
  `title="Synthetic broad ETF SMA observation summary"`, and a deterministic
  summary stating the section is advisory-only synthetic SMA observation
  content. It preserves exact item identity and order, contains exactly two
  items (`above_sma_observation` followed by `insufficient_history`), carries
  item limitations and non-claims forward with first-seen de-dupe, and emits
  fixed `section_type="sma_research_observation_brief_section"`,
  candidate-only/advisory-only/capital-authority-false metadata. The expected
  dict helper composes nested item payloads from the Phase 198 expected brief
  item dictionaries and returns fresh primitive copies. Tests prove exact Phase
  199 production type construction, `.to_dict()` parity, fresh mutable
  primitive expected dictionaries, deterministic repeated construction,
  compact JSON byte determinism, nested Phase 198 payload parity, item identity
  preservation through the section builder, limitation/non-claim carry-forward,
  no `from_dict()`, no paper/live/approved/trading-ready/actionable authority
  states outside explicit non-claims, and fixture AST/import/call/source
  guardrails against broker/account/order/fill/allocation/portfolio mutation
  behavior, file I/O, persistence, network/socket access, vendor APIs,
  credentials, runtime/scheduler/dashboard behavior, notebooks, ML, LLM/agent
  behavior, ranking/scoring, recommendations, approval/readiness/trading
  authority language outside explicit non-claims, or dependencies. No `src`
  files, SMA mechanics, SMA observation fixtures, SMA observation brief item
  behavior, SMA observation brief section behavior, advisory operating brief
  package, package synthetic builder, package CLI, content bundle, renderer,
  export, or existing CLI behavior changed; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 201 - SMA Research Observation Brief Container adds
  `src/algotrader/research/sma_research_observation_brief_container.py` with
  frozen/slotted `SmaResearchObservationBrief` and
  `build_sma_research_observation_brief(brief_id, title, summary, sections)`.
  The module stays separate from `sma_research_observation_brief.py` so the
  Phase 197 item module remains item-only and avoids section/container import
  cycles. The container accepts only exact Phase 199
  `SmaResearchObservationBriefSection` objects, requires at least one section,
  rejects malformed lookalikes and subclasses, rejects duplicate section
  identities, preserves section identity and order, pins
  `brief_type="sma_research_observation_brief"`,
  candidate-only/advisory-only/capital-authority-false metadata, requires
  non-empty advisory-safe brief id/title/summary text, and carries section
  limitations and non-claims forward with first-seen de-dupe. Direct
  construction validates fixed metadata and section-derived
  limitations/non-claims; `to_dict()` emits primitive-only deterministic output
  with section count, nested `section.to_dict()` payloads, limitations, and
  non-claims without mutating source sections. Tests build a brief from the
  Phase 200 synthetic section fixture, prove exact section identity/order,
  empty/duplicate/exact-type rejection, fixed advisory metadata, compact JSON
  byte determinism, source section non-mutation, frozen/slotted behavior, no
  `from_dict()`, no public buy/sell/hold/signal/evaluator/order/allocation/
  broker/portfolio/trading-authority payload fields, no production imports
  from `tests` or `tests.fixtures`, and AST/import/call/source guardrails
  against file I/O, persistence, network/socket access, vendor APIs,
  credentials, broker/runtime behavior, scheduler/dashboard behavior,
  notebooks, ML, LLM/agent behavior, ranking/scoring, recommendations,
  approval/readiness, allocation/order/portfolio mutation, capital authority,
  trading authority, or dependencies. SMA mechanics, SMA observation fixtures,
  SMA observation brief item behavior, SMA observation brief section behavior,
  SMA section fixtures, advisory operating brief package, package synthetic
  builder, package CLI, content bundle, renderer, export, and existing CLI
  behavior are unchanged; normal pytest remains offline, credential-free,
  deterministic, and safe
- Phase 202 - Synthetic SMA Research Observation Brief Container Fixture adds
  `tests/fixtures/sma_research_observation_brief_container.py` and
  `tests/unit/test_sma_research_observation_brief_container_fixture.py` as a
  tests-only layer over the Phase 201 brief container. The fixture builds from
  the Phase 200 synthetic section fixture, uses
  `brief_id="sma-research-observation-brief:synthetic:broad-etf-sma"`,
  `title="Synthetic broad ETF SMA research observation brief"`, and a
  deterministic summary stating the brief is advisory-only synthetic SMA
  observation content. It preserves exact section identity and order, contains
  exactly one Phase 200 section, carries section limitations and non-claims
  forward, and emits fixed `brief_type="sma_research_observation_brief"`,
  candidate-only/advisory-only/capital-authority-false metadata. The expected
  dict helper composes the nested section payload from the Phase 200 expected
  section dictionary and returns fresh primitive copies. Tests prove exact
  Phase 201 production type construction, `.to_dict()` parity, fresh mutable
  primitive expected dictionaries, deterministic repeated construction,
  compact JSON byte determinism, nested Phase 200 payload parity, section
  identity preservation through the container builder, limitation/non-claim
  carry-forward, no `from_dict()`, no paper/live/approved/trading-ready/
  actionable authority states outside explicit non-claims, and fixture
  AST/import/call/source guardrails against broker/account/order/fill/
  allocation/portfolio mutation behavior, file I/O, persistence,
  network/socket access, vendor APIs, credentials, runtime/scheduler/dashboard
  behavior, notebooks, ML, LLM/agent behavior, ranking/scoring,
  recommendations, approval/readiness/trading authority language outside
  explicit non-claims, or dependencies. No `src` files, SMA mechanics, SMA
  observation fixtures, SMA observation brief item behavior, SMA observation
  brief section behavior, SMA section fixtures, SMA brief container behavior,
  advisory operating brief package, package synthetic builder, package CLI,
  content bundle, renderer, export, or existing CLI behavior changed; normal
  pytest remains offline, credential-free, deterministic, and safe
- Phase 203 - SMA Research Observation Brief Text Renderer adds
  `src/algotrader/research/sma_research_observation_brief_renderer.py` with
  `render_sma_research_observation_brief_text(brief)` and
  `tests/unit/test_sma_research_observation_brief_renderer.py`. The renderer
  accepts only exact Phase 201 `SmaResearchObservationBrief` objects, rejects
  malformed lookalikes, dictionaries, `None`, and subclasses, and renders
  solely from `brief.to_dict()` so source brief, section, item, and nested
  observation objects are not mutated. It emits deterministic plain text for
  brief metadata, sections, items, nested source observation mechanics,
  limitations, and non-claims; preserves section and item sequence; includes
  ignored future sample counts; renders insufficient-history SMA and distance
  mechanics as `null`; and keeps output byte-for-byte stable across repeated
  renders. Tests pin exact output for the Phase 202 synthetic brief fixture,
  prove source `.to_dict()` and nested identities are unchanged, verify both
  `above_sma_observation` and `insufficient_history`, reject invalid inputs,
  and guard production imports, calls, source literals, public renderer
  concepts, and rendered text against broker/account/order/fill/allocation/
  portfolio mutation behavior, file I/O, persistence, network/socket access,
  vendor APIs, credentials, runtime/scheduler/dashboard behavior, notebooks,
  ML, LLM/agent behavior, ranking/scoring, recommendations, approval/readiness
  or trading authority language outside explicit non-claims, or dependencies.
  SMA mechanics, SMA fixtures, brief item behavior, section behavior,
  container behavior, advisory operating brief package, package synthetic
  builder, package CLI, content bundle, renderer, export, and existing CLI
  behavior are unchanged; normal pytest remains offline, credential-free,
  deterministic, and safe
- Phase 204 - SMA Research Observation Brief Export Contract adds
  `src/algotrader/research/sma_research_observation_brief_export.py` with
  frozen/slotted `SmaResearchObservationBriefExport` and
  `export_sma_research_observation_brief(brief)`, plus
  `tests/unit/test_sma_research_observation_brief_export.py`. The export
  accepts only exact Phase 201 `SmaResearchObservationBrief` objects, rejects
  malformed lookalikes, dictionaries, `None`, and subclasses, and produces
  only in-memory primitive `payload`, compact deterministic `json_text`, and
  Phase 203 `rendered_text`. Direct construction requires a non-empty
  primitive payload dictionary, non-empty compact JSON text that round-trips
  to the payload, and non-empty rendered text. Payload access returns fresh
  primitive copies, repeated exports are byte-for-byte deterministic, and
  source brief, section, item, and nested observation identities plus
  `.to_dict()` outputs remain unchanged. Tests prove builder acceptance of the
  Phase 202 synthetic fixture, compact JSON settings, rendered text parity
  with the Phase 203 renderer, frozen/slotted behavior, invalid input and
  malformed direct-construction rejection, no `from_dict()`, no production
  imports from tests or fixtures, no public buy/sell/hold/signal/evaluator/
  order/allocation/broker/portfolio/trading-authority export concepts, and
  AST/import/call/source/text guardrails against file I/O, persistence,
  network/socket access, vendor APIs, credentials, runtime/scheduler/dashboard
  behavior, notebooks, ML, LLM/agent behavior, ranking/scoring,
  recommendations, approvals/readiness/trading authority language outside
  explicit non-claims, or dependencies. SMA mechanics, fixtures, brief item
  behavior, section behavior, container behavior, renderer behavior, advisory
  operating brief package, package synthetic builder, package CLI, content
  bundle, renderer, export, and existing CLI behavior are unchanged; normal
  pytest remains offline, credential-free, deterministic, and safe
- Phase 205 - Advisory Operating Brief Content Bundle SMA Research Observation
  Branch extends
  `src/algotrader/research/advisory_operating_brief_content_bundle.py` with an
  optional `sma_research_observation_briefs` branch for exact Phase 201
  `SmaResearchObservationBrief` objects. The bundle keeps fixed
  `bundle_type="advisory_operating_brief_content_bundle"`,
  candidate-only/advisory-only/capital-authority-false metadata, requires at
  least one total brief across all supported branches, preserves object
  identity and order within each branch, rejects malformed inputs and
  subclasses, rejects duplicate identities across all branches, and carries
  limitations/non-claims forward with first-seen de-dupe. `to_dict()` adds
  `sma_research_observation_brief_count` and
  `sma_research_observation_briefs` only when populated, preserving existing
  no-risk, risk-inclusive, and research-queue-inclusive fixture payloads
  byte-for-byte. The new synthetic fixture helper composes candidate research,
  strategy eligibility, risk authority, research queue, and SMA research
  observation branches through the production bundle builder, and its expected
  dictionary nests the Phase 202 expected SMA brief payload. Tests prove
  existing fixture compatibility, new SMA branch payload presence, nested SMA
  payload parity, branch identity/order preservation, cross-branch duplicate
  rejection, deterministic repeated construction, fresh mutable primitive
  expected dictionaries, and unchanged renderer/export/CLI behavior. No real
  data ingestion, broker/runtime behavior, file I/O, persistence,
  network/socket access, credentials, scheduler/dashboard behavior, notebooks,
  ML, LLM/agent behavior, ranking/scoring, recommendations,
  approval/readiness/trading authority behavior, dependencies, or `from_dict()`
  are added; normal pytest remains offline, credential-free, deterministic,
  and safe
- Phase 206 - Advisory Operating Brief Content Bundle Renderer SMA Research
  Observation Branch extends
  `src/algotrader/research/advisory_operating_brief_content_bundle_renderer.py`
  to conditionally render `sma_research_observation_briefs` solely from the
  bundle `to_dict()` payload. Existing no-SMA renderer output for the Phase
  162 candidate-plus-strategy fixture, Phase 178 risk-inclusive fixture, and
  Phase 184/185 research-queue-inclusive fixture remains byte-for-byte pinned.
  The SMA branch renders after candidate research, strategy eligibility, risk
  authority, and research queue branches, and before aggregate
  limitations/non-claims. It emits deterministic brief, section, item, and
  nested source-observation metadata, including ignored future sample counts,
  null SMA/distance mechanics for insufficient history, limitations, and
  non-claims. Tests prove both `above_sma_observation` and
  `insufficient_history`, repeated SMA-inclusive rendering stability, unchanged
  source `.to_dict()` output and object identities, dictionary-only renderer
  access, no export/CLI/package/SMA export coupling, and AST/import/call/source
  guardrails. Content bundle construction, content bundle export, content
  bundle CLI, package behavior, SMA mechanics, SMA brief renderer, SMA brief
  export, and existing CLI behavior remain unchanged. No real data ingestion,
  broker/runtime behavior, file I/O, persistence, network/socket access,
  credentials, scheduler/dashboard behavior, notebooks, ML, LLM/agent
  behavior, ranking/scoring, recommendations, approval/readiness/trading
  authority behavior, dependencies, or `from_dict()` are added; normal pytest
  remains offline, credential-free, deterministic, and safe
- Phase 207 - Advisory Operating Brief Content Bundle Export SMA Branch
  Regression Guard adds
  `tests/unit/test_advisory_operating_brief_content_bundle_export_with_sma_research_observation_regression.py`
  as a test-only regression for the existing export path over the Phase
  205/206 SMA-inclusive synthetic content bundle. The guard proves the export
  payload equals the pinned SMA-inclusive expected dictionary, compact JSON
  uses `sort_keys=True` and `separators=(",", ":")`, JSON round-trips to the
  expected dictionary, rendered text equals
  `render_advisory_operating_brief_content_bundle_text(bundle)`, and repeated
  exports are byte-for-byte deterministic. It pins candidate, strategy, risk,
  research queue, and SMA branches together, including
  `sma_research_observation_brief_count`,
  `sma_research_observation_briefs`, nested SMA observation metadata,
  `above_sma_observation`, `insufficient_history`, ignored future sample
  counts, null SMA/distance fields for insufficient history, branch sequence,
  limitations, non-claims, and source-bundle mutation isolation. No source
  files, renderer/export/CLI/package behavior, SMA mechanics, SMA brief
  renderer/export behavior, existing CLI behavior, real data ingestion, broker
  or runtime behavior, file I/O, persistence, network/socket access,
  credentials, scheduler/dashboard behavior, notebooks, ML, LLM/agent
  behavior, recommendations, ranking/scoring, approvals/readiness/trading
  authority behavior outside explicit non-claims, dependencies, or
  `from_dict()` are added; normal pytest remains offline, credential-free,
  deterministic, and safe
- Phase 208 - Advisory Operating Brief Content Bundle CLI SMA Research
  Observation Preview exposes the existing SMA-inclusive synthetic content
  bundle through `algotrader advisory-operating-brief-content-bundle-preview`
  with the hidden synthetic-only `--include-sma-research-observation` flag.
  Default, text/json, risk-inclusive, research-queue-inclusive, and combined
  risk plus research-queue preview outputs remain byte-for-byte unchanged. The
  new flag composes candidate research, strategy eligibility, and SMA research
  observation branches, and includes risk and/or research queue branches only
  when their existing flags are also present. The helper uses production SMA
  observation and brief builders only and routes text/JSON through
  `export_advisory_operating_brief_content_bundle(...)`. Tests pin compact
  JSON round-tripping, repeated byte-identical SMA-inclusive CLI invocations,
  branch combinations, `above_sma_observation`, `insufficient_history`,
  ignored future sample counts, null SMA/distance fields for insufficient
  history, no production imports from tests or fixtures, no new file/path/
  source/vendor/broker/network/runtime/credential options, and no actionable
  authority states. No real data ingestion, broker/runtime behavior, file I/O,
  persistence, network/socket access, credentials, scheduler/dashboard
  behavior, notebooks, ML, LLM/agent behavior, ranking/scoring,
  recommendations, approvals/readiness/trading authority behavior,
  dependencies, or `from_dict()` are added; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 209 - Advisory Operating Brief Package Synthetic SMA Branch Alignment
  updates `build_synthetic_advisory_operating_brief_package_preview()` so the
  canonical package preview now uses the existing SMA-inclusive content bundle
  builder with risk authority and research queue enabled. Package metadata
  stays pinned to
  `advisory-operating-brief-package:synthetic:2026-01-20`, the synthetic
  advisory title/summary, `as_of="2026-01-20"`, `status="candidate_only"`,
  `authority="advisory_only"`, and `capital_authority=False`. The package
  fixture still delegates to the production-safe synthetic builder, while
  fixture/export/renderer/CLI/regression tests pin candidate research,
  strategy eligibility, risk authority, research queue, and SMA research
  observation branches together. The tests prove
  `sma_research_observation_brief_count`,
  `sma_research_observation_briefs`, nested content bundle export equality,
  stored nested rendered text, compact JSON round-tripping, fixture-export-CLI
  parity, and repeated byte-for-byte deterministic output. Content bundle
  preview behavior and package preview options remain unchanged. No new
  file/path/source/vendor/broker/network/runtime/credential options, real data
  ingestion, broker/runtime behavior, file I/O, persistence,
  scheduler/dashboard behavior, notebooks, ML, LLM/agent behavior,
  recommendations, ranking/scoring, approval/readiness/trading authority
  behavior, dependencies, or `from_dict()` are added; normal pytest remains
  offline, credential-free, deterministic, and safe
- Phase 210 - Synthetic Close-to-Close Research Return Observation Mechanics
  adds `algotrader.research.research_return_observation` as a tiny
  synthetic-fixture-only, offline-safe, advisory-only, non-trading research
  mechanics artifact. It defines frozen/slotted synthetic price points,
  close-to-close return points, and a candidate-only/advisory-only return
  series observation with `capital_authority=False`,
  `return_method="close_to_close_simple_return"`, and
  `price_basis="synthetic_close"`. The builder validates strict `YYYY-MM-DD`
  dates, sorts samples deterministically, ignores and counts future samples,
  rejects duplicate dates and non-positive closes, and constructs only
  consecutive simple returns with
  `(end_close / start_close) - Decimal("1")`; fewer than two eligible samples
  produce zero returns. Serialization is deterministic primitive-only output
  with Decimal values as strings, tuple fields as lists, nested deterministic
  return dictionaries, required negative non-claims, and no `from_dict()`.
  Tests pin positive, negative, and zero returns, deterministic sorting,
  future-sample exclusion, empty-return behavior, validation failures,
  immutability/slots, byte-stable compact JSON, primitive-only payloads,
  forbidden public payload keys, no tests/fixture production imports, and
  AST/import/call/reference guardrails against file I/O, network/socket access,
  vendor APIs, broker/runtime/scheduler/dashboard behavior, persistence,
  credentials, notebooks, ML, LLM/agent behavior, recommendations,
  ranking/scoring, approvals/readiness, allocation/order/portfolio mutation,
  capital authority, trading authority, dependencies, and real data ingestion;
  normal pytest remains offline, credential-free, deterministic, and safe
- Phase 211 - Synthetic Research Return Observation Fixture adds
  `tests/fixtures/research_return_observation.py` and
  `tests/unit/test_research_return_observation_fixture.py` as a deterministic
  fixture layer over the Phase 210 close-to-close observation mechanics. The
  primary fixture uses synthetic broad ETF-like closes only, pins
  `symbol="SYNTH_ETF"`, `as_of="2026-01-20"`,
  `return_method="close_to_close_simple_return"`,
  `price_basis="synthetic_close"`, `status="candidate_only"`,
  `authority="advisory_only"`, and `capital_authority=False`, and includes
  five samples with one ignored future sample plus positive, negative, and
  zero consecutive eligible simple returns. The insufficient fixture has
  fewer than two eligible samples, counts one ignored future sample, and emits
  `return_count=0` with `returns=[]`. Expected dictionary helpers match
  `.to_dict()` exactly while returning fresh primitive mutable copies, and
  repeated construction plus compact JSON bytes remain deterministic. Tests
  pin fixed advisory metadata, limitations, required non-claims including
  source/data, adjusted-close/corporate-action, methodology, predictive,
  profitability, recommendation, signal/evaluator, backtesting, allocation/
  order, broker, portfolio mutation, paper/live, capital, and trading denials,
  absence of `from_dict()`, absence of paper/live/approved/trading-ready/
  actionable authority states, and AST/import/call/literal guardrails against
  real data ingestion, file I/O, persistence, network/socket access, vendor
  APIs, credentials, broker/account/order/fill/allocation/portfolio mutation
  behavior, runtime/scheduler/dashboard behavior, notebooks, ML, LLM/agent
  behavior, recommendations, ranking/scoring, approval/readiness/trading
  authority behavior outside explicit non-claims, dependencies, or production
  imports from tests. No source files, advisory package, synthetic package
  builder, package CLI, content bundle, renderer/export, SMA mechanics, SMA
  brief renderer/export, or existing CLI behavior changed; normal pytest
  remains offline, credential-free, deterministic, and safe
- Phase 212 - Research Return Observation Brief Item adds
  `algotrader.research.research_return_observation_brief` as a tiny
  metadata-only advisory wrapper around Phase 210 research return
  observations. It defines frozen/slotted
  `ResearchReturnObservationBriefItem` and
  `build_research_return_observation_brief_item()` with fixed
  `item_type="research_return_observation_brief_item"`,
  `status="candidate_only"`, `authority="advisory_only"`, and
  `capital_authority=False`. The builder accepts only exact
  `ResearchReturnSeriesObservation` instances, preserves source observation
  identity, maps `return_count=0` to `insufficient_return_history` and
  nonzero return counts to `returns_constructed`, deterministically counts
  positive, negative, and zero simple returns, and carries limitations plus
  non-claims forward with first-seen de-duplication. Headline and summary text
  are deterministic advisory research content generated from source metadata
  and return direction counts only, while authority/actionability wording is
  rejected outside explicit non-claims. Serialization is primitive-only and
  deterministic with nested `source_observation.to_dict()`, tuple fields as
  lists, fixed metadata, mechanical state, return direction counts, and no
  `from_dict()`. Tests pin the Phase 211 primary and insufficient fixtures,
  exact source type rejection for malformed lookalikes/subclasses, source
  non-mutation, frozen/slotted behavior, compact JSON byte determinism,
  forbidden public payload keys, no production imports from tests, and
  AST/import/call/literal guardrails against file I/O, network/socket access,
  vendor APIs, broker/runtime/scheduler/dashboard behavior, persistence,
  credentials, notebooks, ML, LLM/agent behavior, recommendations,
  ranking/scoring, approval/readiness, allocation/order/portfolio mutation,
  capital authority, trading authority, dependencies, or real data ingestion.
  Research return mechanics, fixtures, advisory packages, synthetic package
  builders, package CLI/content bundle/renderer/export, SMA mechanics/brief
  rendering/export, and existing CLI behavior remain unchanged; normal pytest
  remains offline, credential-free, deterministic, and safe
- Phase 213 - Synthetic Research Return Observation Brief Fixture adds
  `tests/fixtures/research_return_observation_brief.py` and
  `tests/unit/test_research_return_observation_brief_fixture.py` as a
  deterministic fixture layer over the Phase 212 brief item. The primary
  helper builds from the Phase 211 synthetic return observation, preserves the
  exact source observation object inside the Phase 212 item, pins
  `mechanical_state="returns_constructed"`, and pins positive/negative/zero
  return counts to `1/1/1`. The insufficient-history helper builds from the
  Phase 211 insufficient return observation, preserves source identity, pins
  `mechanical_state="insufficient_return_history"`, and pins all return
  direction counts to zero. Expected dictionary helpers match `.to_dict()`
  exactly while returning fresh mutable primitive copies; nested
  `source_observation` payloads match the Phase 211 expected observation
  payloads, including fixed candidate-only/advisory-only metadata,
  limitations, and non-claims. Tests prove repeated construction and compact
  JSON bytes are deterministic, no `from_dict()` exists, no paper/live/
  approved/trading-ready/actionable authority states appear, and fixture
  AST/import/call/literal guardrails exclude broker/account/order/fill/
  allocation/portfolio mutation behavior, file I/O, network/socket access,
  vendor APIs, credentials, runtime/scheduler/dashboard behavior, notebooks,
  ML, LLM/agent behavior, recommendations, ranking/scoring, approval/
  readiness/trading authority language outside explicit non-claims, new
  dependencies, and production imports from tests. No source files, research
  return mechanics, Phase 211 observation fixtures, advisory package,
  synthetic package builder, package CLI, content bundle, renderer/export, SMA
  mechanics, SMA brief renderer/export, or existing CLI behavior changed;
  normal pytest remains offline, credential-free, deterministic, and safe
- Phase 214 - Research Return Observation Brief Section adds
  `algotrader.research.research_return_observation_brief_section` as a frozen,
  slotted, metadata-only advisory grouping for exact Phase 212
  `ResearchReturnObservationBriefItem` objects. The builder accepts a section
  id, title, summary, and one or more exact brief items; preserves item object
  identity and order; rejects empty collections, duplicate item identities,
  malformed lookalikes, and subclasses; and pins
  `section_type="research_return_observation_brief_section"`,
  `status="candidate_only"`, `authority="advisory_only"`, and
  `capital_authority=False`. It carries item limitations and non-claims
  forward with first-seen de-duplication while rejecting authority/
  actionability wording outside explicit non-claims. Serialization is
  deterministic primitive-only metadata with fixed section fields, item count,
  nested `item.to_dict()` payloads, list-form tuple fields, and no
  `from_dict()`. Tests build from the Phase 213 primary and
  insufficient-history fixtures, prove source item `.to_dict()` outputs are
  unchanged before and after construction/serialization, pin compact JSON byte
  determinism, verify frozen/slotted behavior, confirm public payload keys
  avoid action/trading fields, and enforce AST/import/call/literal guardrails
  against file I/O, network/socket access, vendor APIs, broker/runtime/
  scheduler/dashboard behavior, persistence, credentials, notebooks, ML,
  LLM/agent behavior, recommendations, ranking/scoring, approvals/readiness,
  allocation/order/portfolio mutation, capital authority, trading authority,
  new dependencies, and production imports from tests. Research return
  mechanics, observation fixtures, brief item behavior, advisory package,
  package synthetic builder, package CLI, content bundle, renderer/export, SMA
  mechanics, SMA brief renderer/export, and existing CLI behavior remain
  unchanged; normal pytest remains offline, credential-free, deterministic,
  and safe
- Phase 215 - Synthetic Research Return Observation Brief Section Fixture adds
  `tests/fixtures/research_return_observation_brief_section.py` and
  `tests/unit/test_research_return_observation_brief_section_fixture.py` as a
  tests-only fixture layer over the Phase 214 section container. The fixture
  builds from the Phase 213 primary and insufficient-history brief item
  fixtures, uses
  `section_id="research-return-observation-section:synthetic:broad-etf-return-construction"`,
  `title="Synthetic broad ETF return observation summary"`, and a deterministic
  summary stating the section is advisory-only synthetic close-to-close return
  observation content. Its expected dictionary helper matches `.to_dict()`
  exactly while returning fresh mutable primitive copies, nests the exact Phase
  213 `returns_constructed` item payload followed by the
  `insufficient_return_history` item payload, pins candidate-only/
  advisory-only/capital-authority-false metadata, carries limitations and
  non-claims forward with first-seen de-duplication, and preserves item
  identity through the Phase 214 builder. Tests prove repeated construction and
  compact JSON bytes are deterministic, nested return-count and
  insufficient-history metadata remain present, no `from_dict()` exists, no
  paper/live/approved/trading-ready/actionable authority states appear, and
  fixture AST/import/call/literal guardrails exclude broker/account/order/fill/
  allocation/portfolio mutation behavior, file I/O, persistence,
  network/socket access, vendor APIs, credentials, runtime/scheduler/dashboard
  behavior, notebooks, ML, LLM/agent behavior, recommendations,
  ranking/scoring, approval/readiness/trading authority language outside
  explicit non-claims, and new dependencies. No source files, research return
  mechanics, research return observation fixtures, research return brief item
  behavior, research return brief section behavior, advisory package, package
  synthetic builder, package CLI, content bundle, renderer/export, SMA
  mechanics, SMA brief renderer/export, or existing CLI behavior changed;
  normal pytest remains offline, credential-free, deterministic, and safe
- Phase 216 - Research Return Observation Brief Container adds
  `algotrader.research.research_return_observation_brief_container` as a
  frozen, slotted, metadata-only advisory top-level grouping for exact Phase
  214 `ResearchReturnObservationBriefSection` objects. The builder accepts a
  brief id, title, summary, and one or more exact sections; preserves section
  object identity and order; rejects empty collections, duplicate section
  identities, malformed lookalikes, and subclasses; and pins
  `brief_type="research_return_observation_brief"`, `status="candidate_only"`,
  `authority="advisory_only"`, and `capital_authority=False`. It carries
  section limitations and non-claims forward with first-seen de-duplication
  while rejecting authority/actionability wording outside explicit non-claims.
  Serialization is deterministic primitive-only metadata with fixed brief
  fields, section count, nested `section.to_dict()` payloads, list-form tuple
  fields, and no `from_dict()`. Tests build from the Phase 215 synthetic
  section fixture, prove source section `.to_dict()` output is unchanged before
  and after construction/serialization, pin compact JSON byte determinism,
  verify frozen/slotted behavior, confirm public payload keys avoid action/
  trading fields, and enforce AST/import/call/literal guardrails against file
  I/O, network/socket access, vendor APIs, broker/runtime/scheduler/dashboard
  behavior, persistence, credentials, notebooks, ML, LLM/agent behavior,
  recommendations, ranking/scoring, approvals/readiness, allocation/order/
  portfolio mutation, capital authority, trading authority, new dependencies,
  and production imports from tests. Research return mechanics, observation
  fixtures, brief item behavior, brief item fixtures, brief section behavior,
  brief section fixtures, advisory package, package synthetic builder, package
  CLI, content bundle, renderer/export, SMA mechanics, SMA brief renderer/
  export, and existing CLI behavior remain unchanged; normal pytest remains
  offline, credential-free, deterministic, and safe
- Phase 217 - Synthetic Research Return Observation Brief Container Fixture
  adds `tests/fixtures/research_return_observation_brief_container.py` and
  `tests/unit/test_research_return_observation_brief_container_fixture.py` as a
  deterministic synthetic fixture layer for the Phase 216 advisory brief
  container. The fixture builds exactly one Phase 215 synthetic section,
  preserves that section's identity and order through the production builder,
  and emits the fixed advisory metadata
  `brief_id="research-return-observation-brief:synthetic:broad-etf-return-construction"`,
  `title="Synthetic broad ETF return observation brief"`,
  `brief_type="research_return_observation_brief"`,
  `status="candidate_only"`, `authority="advisory_only"`, and
  `capital_authority=False`. Its expected-dict helper mirrors `.to_dict()`
  exactly with fresh primitive mutable copies, deterministic compact JSON
  bytes, one nested section payload matching the Phase 215 expected section
  dict, nested positive/negative/zero return-count metadata, the
  insufficient-history state, and carried-forward limitations and non-claims.
  Tests confirm there is no `from_dict()`, no positive approval/readiness/
  actionability/trading authority state, and fixture-module AST/import/call/
  literal guardrails against broker, account, order, fill, allocation,
  portfolio mutation, file I/O, network/socket access, vendor APIs,
  credentials, runtime/scheduler/dashboard behavior, notebooks, ML, LLM/agent
  behavior, recommendations, ranking/scoring, approvals, or trading authority.
  No src files, research return mechanics, observation fixtures, brief item
  behavior or fixtures, brief section behavior or fixtures, container behavior,
  advisory/package/CLI/content/render/export paths, SMA paths, or existing CLI
  behavior changed; normal pytest remains offline, credential-free,
  deterministic, and safe
- Phase 218 - Research Return Observation Brief Text Renderer adds
  `algotrader.research.research_return_observation_brief_renderer` with
  `render_research_return_observation_brief_text(brief)` as a deterministic
  plain-text view over the Phase 216/217 synthetic advisory brief. The renderer
  accepts only exact `ResearchReturnObservationBrief` instances, rejects
  subclasses, dictionaries, malformed lookalikes, and `None`, and renders
  solely from `brief.to_dict()` without touching source objects. Output pins
  top-level brief metadata, section metadata, item metadata, positive/
  negative/zero return-count metadata, nested close-to-close synthetic source
  observation mechanics, each nested return point in source order,
  deterministic empty-return wording for `insufficient_return_history`, and
  item/section/brief limitations and non-claims. Tests pin the rendered text
  exactly, prove repeated byte-for-byte determinism, verify source `.to_dict()`
  output and nested section/item/source observation/return-point identities
  remain unchanged, and enforce AST/import/call/literal guardrails. The
  renderer imports no tests or fixtures, adds no `from_dict()`, and does not
  add real data ingestion, vendor/broker/runtime behavior, file I/O,
  persistence, network/socket access, credentials, scheduler/dashboard
  behavior, notebooks, ML, LLM/agent behavior, scoring, ranking,
  recommendations, approval/readiness claims, trading authority, capital
  authority beyond the existing false metadata field, or new dependencies.
  Research return mechanics, observation fixtures, brief item/section/container
  behavior and fixtures, advisory/package/CLI/content bundle paths, existing
  renderer/export paths, SMA paths, and existing CLI behavior remain unchanged;
  normal pytest remains offline, credential-free, deterministic, and safe
- Phase 219 - Research Return Observation Brief Export Contract adds
  `algotrader.research.research_return_observation_brief_export` with frozen,
  slotted `ResearchReturnObservationBriefExport` and
  `export_research_return_observation_brief(brief)` as a deterministic
  in-memory export view over the Phase 216/217/218 research return observation
  brief. The builder accepts only exact `ResearchReturnObservationBrief`
  instances, rejects subclasses, dictionaries, malformed lookalikes, and
  `None`, sets `payload` from `brief.to_dict()`, sets `json_text` with compact
  deterministic JSON (`sort_keys=True`, `separators=(",", ":")`), and sets
  `rendered_text` from the Phase 218 renderer. Direct construction requires a
  non-empty primitive payload dictionary, non-empty compact JSON text that
  round-trips to the payload, and non-empty rendered text; payload access
  returns fresh primitive copies, the export is frozen/slotted, and no
  `from_dict()` is added. Tests prove repeated byte-for-byte determinism,
  unchanged source `.to_dict()` output, stable section/item/source observation/
  return-point identities, exact fixture equality, renderer equality, and
  production imports with no tests or fixtures. AST/import/call/literal
  guardrails confirm the export adds no file I/O, persistence, network/socket
  access, vendor APIs, credentials, broker/runtime/scheduler/dashboard
  behavior, notebooks, ML, LLM/agent behavior, recommendations,
  ranking/scoring, approval/readiness claims, source/data approval,
  methodology approval, adjusted-close completeness claims, signal/evaluator
  behavior, allocation/order/portfolio mutation, capital authority beyond
  existing false metadata, trading authority, new dependencies, real data
  ingestion, or CLI behavior. Research return mechanics, observation fixtures,
  brief item/section/container behavior and fixtures, renderer behavior,
  advisory/package/CLI/content bundle paths, SMA paths, and existing CLI
  behavior remain unchanged; normal pytest remains offline, credential-free,
  deterministic, and safe
- Phase 220 - Advisory Operating Brief Content Bundle Research Return
  Observation Branch extends
  `algotrader.research.advisory_operating_brief_content_bundle` with optional
  `research_return_observation_briefs` support for exact
  `ResearchReturnObservationBrief` instances. The bundle still preserves fixed
  metadata (`bundle_type="advisory_operating_brief_content_bundle"`,
  `status="candidate_only"`, `authority="advisory_only"`, and
  `capital_authority=False`), accepts empty individual branches, requires at
  least one total brief across candidate research, strategy eligibility, risk
  authority, research queue, SMA research observation, and research return
  observation branches, rejects subclasses and malformed lookalikes, preserves
  per-branch identity/order, rejects duplicate identities across all branches,
  and carries limitations/non-claims forward with first-seen de-dupe. The
  `to_dict()` output adds `research_return_observation_brief_count` and
  `research_return_observation_briefs` only when that optional branch is
  populated, preserving existing no-risk, risk-inclusive, research-queue-
  inclusive, and SMA-inclusive fixture payloads byte-for-byte. The new fixture
  helper composes candidate research, strategy eligibility, risk authority,
  research queue, SMA research observation, and research return observation
  branches through the production bundle builder, exposing the synthetic
  close-to-close return-construction observation payload for later operating
  brief rendering/export/CLI phases. Tests pin the nested research return
  observation payload, including `returns_constructed`,
  `insufficient_return_history`, positive/negative/zero return counts,
  `close_to_close_simple_return`, `synthetic_close`, ignored future sample
  count, and return points. No `from_dict()` is added, and renderer/export/CLI/
  package paths, package synthetic builder paths, research return mechanics and
  renderer/export paths, SMA mechanics and renderer/export paths, and existing
  CLI behavior remain unchanged; normal pytest remains offline,
  credential-free, deterministic, and safe
- Phase 221 - Advisory Operating Brief Content Bundle Renderer Research Return
  Observation Branch extends
  `algotrader.research.advisory_operating_brief_content_bundle_renderer` to
  conditionally render Phase 220 `research_return_observation_briefs` from
  `bundle.to_dict()` only. The renderer preserves candidate research, strategy
  eligibility, risk authority, research queue, SMA research observation,
  research return observation, and aggregate limitations/non-claims branch
  order. The new branch renders deterministic brief, section, and item
  metadata; positive/negative/zero return-count metadata; nested close-to-close
  synthetic source observation mechanics; return points in source order;
  deterministic insufficient-history empty-return wording; and item, section,
  and brief limitations/non-claims. Tests preserve Phase 162, Phase 178,
  Phase 184/185, and Phase 205/206 no-return-branch renderer output, pin the
  SMA-inclusive renderer bytes by length and SHA-256, prove repeated research-
  return-inclusive rendering is byte-for-byte deterministic, verify source
  `.to_dict()` payloads and nested objects remain unchanged, and enforce
  AST/import/call/literal guardrails. No content bundle contract, export, CLI,
  package, synthetic builder, research return mechanics, research return
  renderer/export, SMA mechanics, SMA renderer/export, existing CLI behavior,
  real data ingestion, vendor data, broker/runtime behavior, file I/O,
  persistence, network/socket access, credentials, scheduler/dashboard
  behavior, notebooks, ML, LLM/agent behavior, scoring, ranking,
  recommendations, approval/readiness claims, allocation/order/portfolio
  mutation, capital authority beyond existing false metadata, trading
  authority, new dependencies, or `from_dict()` are added; normal pytest
  remains offline, credential-free, deterministic, and safe
- Phase 222 - Advisory Operating Brief Content Bundle Export Research Return
  Observation Regression Guard adds a test-only regression for the existing
  `export_advisory_operating_brief_content_bundle(...)` path over the Phase
  220/221 research-return-inclusive synthetic content bundle. The guard uses
  the existing research-return-inclusive builder and expected dictionary, pins
  payload equality, compact deterministic JSON (`sort_keys=True`,
  `separators=(",", ":")`), JSON round-tripping, rendered text equality with
  `render_advisory_operating_brief_content_bundle_text(bundle)`, and repeated
  byte-for-byte export determinism. It also proves candidate, strategy, risk,
  research queue, SMA, and research return branches are present; pins
  `research_return_observation_brief_count` and
  `research_return_observation_briefs`; verifies nested research return brief,
  section, item, source observation, and return point metadata; covers
  `returns_constructed`, `insufficient_return_history`, positive/negative/zero
  return counts, `close_to_close_simple_return`, `synthetic_close`, ignored
  future sample count, ordered return points, deterministic empty-return
  representation, branch sequence, limitations/non-claims preservation, and
  source-bundle mutation isolation. The new file self-checks imports, calls,
  and source terms to stay isolated from broker/account/order/fill/allocation/
  portfolio mutation behavior, file I/O, network/socket, vendor APIs,
  credentials, runtime/scheduler/dashboard paths, notebooks, ML, LLM/agent
  behavior, recommendation/ranking/scoring/approval/readiness/trading authority
  behavior, and `from_dict()`. No source files, content bundle, renderer,
  export, CLI, package, package synthetic builder, package CLI, research return
  mechanics, research return brief renderer/export, SMA mechanics, SMA brief
  renderer/export, or existing CLI behavior are changed; normal pytest remains
  offline, credential-free, deterministic, and safe
- Phase 223 - Advisory Operating Brief Content Bundle CLI Research Return
  Observation Preview adds the hidden synthetic-only
  `--include-research-return-observation` flag to
  `algotrader advisory-operating-brief-content-bundle-preview`. The default,
  text/json, risk-inclusive, research-queue-inclusive, SMA-inclusive, and
  existing risk+research-queue+SMA preview bytes remain unchanged. The new flag
  composes candidate research, strategy eligibility, and research return
  observation branches, and combines with risk, research queue, and SMA only
  when those flags are explicitly present. The preview uses public production
  builders with deterministic synthetic close samples, still exports through
  `export_advisory_operating_brief_content_bundle(...)`, preserves compact JSON,
  and tests branch presence, JSON round-tripping, repeated byte determinism,
  `returns_constructed`, `insufficient_return_history`,
  positive/negative/zero counts, `close_to_close_simple_return`,
  `synthetic_close`, ignored future sample count, ordered return points, and
  deterministic empty-return wording. Production CLI modules still import no
  tests/fixtures and add no file/path/source/vendor/broker/network/runtime/
  credential options, real data ingestion, persistence, network/socket access,
  credentials, scheduler/dashboard behavior, notebooks, ML, LLM/agent behavior,
  approval/readiness claims, recommendations, allocation/order/portfolio
  mutation, risk approval, paper/live readiness, capital authority beyond
  existing false metadata, trading authority, new dependencies, runtime
  timestamps, or `from_dict()`; normal pytest remains offline, credential-free,
  deterministic, and safe
- Phase 224 - Advisory Operating Brief Package Synthetic Research Return
  Branch Alignment updates the canonical synthetic package preview to build
  the nested content bundle from the existing research-return-inclusive
  production helper. The package now carries candidate research, strategy
  eligibility, risk authority, research queue, SMA research observation, and
  research return observation branches through the stored nested content bundle
  payload, nested content bundle export payload, compact JSON, and rendered
  text. Fixed package metadata remains
  `advisory-operating-brief-package:synthetic:2026-01-20`, the existing title,
  advisory-only summary, `as_of`, `candidate_only`, `advisory_only`, and
  `capital_authority=False`; the fixture still delegates to the production-safe
  synthetic builder. Package fixture, export, renderer, CLI, and CLI regression
  tests pin byte-for-byte deterministic parity against the updated package
  export, while content bundle preview behavior remains unchanged and package
  preview still exposes only `--format text|json`. No package contract,
  renderer/export/CLI production code, content bundle contract, research return
  mechanics, SMA mechanics, new input options, file/env/network/socket access,
  credentials, scheduler/dashboard behavior, notebooks, ML, LLM/agent behavior,
  approval/readiness claims, recommendations, allocation/order/portfolio
  mutation, risk approval, paper/live readiness, capital authority beyond
  existing false metadata, trading authority, dependencies, runtime timestamps,
  or `from_dict()` are added; normal pytest remains offline, credential-free,
  deterministic, and safe
- Phase 225 - Research Return Summary Observation Mechanics adds
  `algotrader.research.research_return_summary_observation` as a tiny frozen,
  slotted, deterministic descriptive summary over exact Phase 210
  `ResearchReturnSeriesObservation` objects. The builder rejects subclasses,
  dictionaries, malformed lookalikes, and non-observations; preserves source
  observation identity; pins `observation_type` to
  `research_return_summary_observation`; keeps `candidate_only`,
  `advisory_only`, and `capital_authority=False`; and records source symbol,
  `as_of`, return method, price basis, source return count,
  positive/negative/zero return counts, and Decimal-only min/max/mean simple
  return values. Return-bearing observations use
  `summary_state="returns_summarized"`; empty return histories use
  `summary_state="insufficient_return_history"` with `None` min/max/mean.
  `to_dict()` emits primitive-only deterministic payloads, serializes Decimals
  as strings and `None` as JSON null, nests `source_observation.to_dict()`,
  converts tuples to lists, preserves source `.to_dict()` output, carries
  limitations/non-claims forward with first-seen de-dupe, and adds no
  `from_dict()`. Tests pin Phase 211 primary and insufficient fixtures,
  exact Decimal strings, fixed metadata, exact-type validation, frozen/slotted
  behavior, deterministic compact JSON bytes, import/source guardrails, and
  absence of action/trading authority payload keys. No research return
  mechanics, research return brief item/section/container/renderer/export,
  advisory package, package synthetic builder, package CLI, content bundle,
  renderer/export/CLI, SMA mechanics, SMA brief renderer/export, existing CLI
  behavior, real data ingestion, vendor data, broker/runtime behavior, file
  I/O, persistence, network/socket access, credentials, scheduler/dashboard
  behavior, notebooks, ML, LLM/agent behavior, approval/readiness claims,
  signal/evaluator behavior, strategy execution, backtesting behavior,
  ranking/scoring, recommendations, allocation/order/portfolio mutation, risk
  approval, paper/live readiness, capital authority beyond fixed false
  metadata, trading authority, dependencies, runtime timestamps, or trading
  behavior are added; normal pytest remains offline, credential-free,
  deterministic, and safe
- Phase 226-230 - Research Return Summary Observation Advisory Integration adds
  a bounded synthetic advisory branch for the committed Phase 225 summary
  observation. It adds
  `tests/fixtures/research_return_summary_observation.py` with constructed and
  insufficient-history summary fixtures plus exact expected primitive dict
  helpers matching `.to_dict()`. It also adds
  `algotrader.research.research_return_summary_observation_brief` with a
  frozen/slotted `ResearchReturnSummaryObservationBrief`, deterministic text
  rendering, and in-memory export views. The brief preserves exact source
  summary observation identities, includes the summary state, return counts,
  min/max/mean simple return values, advisory metadata, limitations,
  non-claims, and nested source observation payloads, and adds no `from_dict()`.
  The branch is wired into the existing advisory content bundle, renderer,
  export, hidden synthetic CLI preview, and package synthetic preview only as an
  optional additive branch after the existing research return observation
  branch. Existing branch ordering and exact-output regressions are preserved.
  The packet remains synthetic-fixture-only, metadata-only, advisory-only,
  offline-safe, deterministic, and non-actionable; it adds no real market data,
  raw vendor/public data, network/socket/API access, credentials, file I/O,
  broker/execution/portfolio/runtime/scheduler/dashboard/persistence behavior,
  ML, LLM/agent/notebook paths, signal/evaluator/backtesting behavior, strategy
  approval, validation/recommendation/ranking/scoring/readiness claims,
  allocation/order authority, paper/live eligibility, capital authority beyond
  fixed false metadata, or trading authority
- Phase 231-236 - Tiny Synthetic SMA Mechanics Seed adds a tests-only
  regression seed over the existing Phase 195 synthetic SMA mechanics instead
  of adding a duplicate object. The seed pins a four-row synthetic close-price
  series through `SmaResearchObservation` and
  `build_sma_research_observation`, exact Decimal SMA arithmetic,
  explicit `as_of` filtering with later samples ignored, deterministic
  insufficient-history non-formation, repeated compact JSON stability,
  primitive-only `.to_dict()` output, source price-point non-mutation, and
  absence of action/trading authority payload fields. No SMA production
  mechanics, fixtures, advisory package paths, renderer/export/CLI behavior,
  research return mechanics, real data ingestion, vendor/public data handling,
  file I/O, network/socket/API access, credentials, broker/execution/portfolio/
  runtime/scheduler/dashboard behavior, ML, LLM/agent behavior,
  signal/evaluator/backtesting behavior, strategy approval, validation/
  recommendation/ranking/scoring/readiness claims, allocation/order authority,
  paper/live eligibility, capital authority beyond fixed false metadata,
  trading authority, dependencies, or deserialization paths are added; normal
  pytest remains offline, credential-free, deterministic, and safe
- Phase 237 - SMA Research Summary Observation Mechanics adds
  `algotrader.research.sma_research_summary_observation` as a tiny frozen,
  slotted, deterministic, advisory-only summary over exact existing
  `SmaResearchObservation` objects. The builder accepts only tuple/list inputs
  containing exact observations, rejects subclasses, lookalikes, dictionaries,
  raw price points, and non-observations, preserves source observation identity
  and input ordering, and pins `candidate_only`, `advisory_only`,
  `research_only`, and `capital_authority=False`. The summary records only
  primitive descriptive metadata counts: total source observations, above-SMA,
  below-SMA, equal-SMA, and insufficient-history counts. Non-empty inputs use
  `summary_state="observations_summarized"`; empty inputs use
  `summary_state="empty_insufficient_observations"` with zero counts and
  explicit limitations/non-claims. `to_dict()` emits deterministic
  primitive-only output, nests source observation payloads, returns fresh lists,
  and adds no `from_dict()`. No existing SMA mechanics, advisory bundle,
  renderer, package, export, CLI, signal/evaluator, portfolio, trading,
  real-data, file/path/source/vendor/broker/network/runtime/credential,
  persistence, socket, scheduler/dashboard, ML, LLM/agent, recommendation,
  ranking/scoring, readiness/approval, allocation/order/fill, paper/live,
  dependency, timestamp, capital-authority, or trading-authority behavior is
  added; normal pytest remains offline, credential-free, deterministic, and safe
- Phase 238 - Advisory Content Bundle SMA Summary Observation Preview wires the
  Phase 237 `SmaResearchSummaryObservation` into the synthetic advisory
  operating brief content bundle preview path behind hidden
  `--include-sma-research-summary-observation`. The preview builder constructs
  the summary from the same synthetic SMA observations used by the existing SMA
  observation preview branch, carries it through content bundle export and text
  rendering as advisory metadata only, and omits the branch unless the hidden
  synthetic-only flag is explicitly supplied. Default content bundle preview
  output and package preview output remain unchanged. The branch stays
  `candidate_only`, `advisory_only`, `research_only`, and
  `capital_authority=False`; no strategy validation, signal, evaluator,
  recommendation, ranking/scoring, readiness state, allocation/order/fill,
  paper/live, trading authority, broker/runtime/vendor option, real data,
  persistence, network/socket/API access, scheduler/dashboard, ML, LLM/agent,
  dependency, runtime timestamp, or deserialization behavior is added.
  Verification: `python -m pytest` -> 4644 passed, 4 skipped
- Phase 239 - Advisory Package SMA Summary Alignment promotes the Phase 238 SMA
  summary branch into the canonical synthetic advisory operating brief package
  path. The package synthetic builder now requests the content-bundle
  `SmaResearchSummaryObservation`, carries the exact summary object into the
  rebuilt package content bundle, and pins the package fixture/export/render/CLI
  regression path around the new nested
  `sma_research_summary_observations` branch. The branch is advisory metadata
  only: it remains `candidate_only`, `advisory_only`, `research_only`, and
  `capital_authority=False`, exports/renders source-observation counts without
  changing SMA mechanics, and adds no strategy approval, validation/readiness,
  recommendation, ranking/scoring, signal/evaluator behavior, allocation/order/
  fill authority, broker/runtime/vendor option, real data input, persistence,
  network/socket/API access, scheduler/dashboard, ML, LLM/agent behavior,
  dependency, runtime timestamp, paper/live eligibility, capital authority
  beyond fixed false metadata, trading authority, or deserialization behavior.
  Verification: `python -m pytest` -> 4644 passed, 4 skipped
- Phase 240 - Research-Only SMA Return Alignment Mechanics adds
  `algotrader.research.sma_return_alignment_observation` with frozen/slotted
  `SmaReturnAlignmentPeriod` and `SmaReturnAlignmentObservation` contracts plus
  a pure `build_sma_return_alignment_observation(...)` builder. The artifact
  aligns existing SMA research observation state to existing close-to-close
  return periods by selecting the latest SMA observation whose `as_of` is on or
  before each return `start_date`, explicitly represents periods with no prior
  SMA state, preserves source observation identity, rejects duplicate SMA
  `as_of` inputs, and emits primitive-only deterministic payloads. This phase
  remains research metadata only and adds no strategy-return computation,
  equity curve, benchmark comparison, cost model, trade order, position,
  allocation, portfolio state, readiness, approval, recommendation, signal or
  evaluator behavior, broker/runtime/vendor option, real data input,
  persistence, network/socket/API access, scheduler/dashboard behavior, ML,
  LLM/agent behavior, capital authority, trading authority, or deserialization
  behavior. Verification: `python -m pytest` -> 4658 passed, 4 skipped
- Phase 241 - SMA Return Alignment Summary Observation adds
  `algotrader.research.sma_return_alignment_summary_observation` with a
  frozen/slotted `SmaReturnAlignmentSummaryObservation` contract plus a pure
  `build_sma_return_alignment_summary_observation(...)` builder. The artifact
  preserves the existing Phase 240 source alignment object and emits
  primitive-only deterministic summary metadata for alignment-period count,
  aligned return count, periods with no prior SMA state, aligned periods using
  insufficient-history SMA observations, and aligned above/below/equal SMA
  state counts. It also derives a fixed summary state for all, partial, none,
  or empty return-period alignment while keeping source identity and nested
  source payloads auditable. This phase remains advisory research metadata
  only and adds no strategy-return computation, equity curve, exposure
  calculation, cash behavior, benchmark comparison, trade order, position,
  allocation, portfolio state, readiness, approval, recommendation, signal or
  evaluator behavior, broker/runtime/vendor option, real data input,
  persistence, network/socket/API access, scheduler/dashboard behavior, ML,
  LLM/agent behavior, capital authority, trading authority, or deserialization
  behavior. Verification: `python -m pytest` -> 4671 passed, 4 skipped
- Phase 242 - Research-Only SMA Conditional Return Selection Observation adds
  `algotrader.research.sma_conditional_return_selection_observation` with
  frozen/slotted `SmaConditionalReturnSelectionPeriod` and
  `SmaConditionalReturnSelectionObservation` contracts plus a pure
  `build_sma_conditional_return_selection_observation(...)` builder. The
  artifact consumes the existing Phase 240 `SmaReturnAlignmentObservation`,
  preserves source alignment observation and period identity, and classifies
  each aligned return period under the fixed
  `include_when_sma_state_is_above` rule. Aligned `above` SMA periods are
  marked `included`; below, equal, insufficient-history, and no-prior-SMA
  periods are marked `excluded` with deterministic reason counts. This phase
  remains advisory research metadata only and adds no strategy-return
  computation, compounded-return computation, equity curve, cash return,
  benchmark comparison, portfolio state, exposure calculation, trade order,
  position, allocation, readiness, approval, recommendation, signal or
  evaluator behavior, broker/runtime/vendor option, real data input,
  persistence, network/socket/API access, scheduler/dashboard behavior, ML,
  LLM/agent behavior, capital authority, trading authority, or deserialization
  behavior. Verification: `python -m pytest` -> 4685 passed, 4 skipped
- Phase 243 - SMA Conditional Return Selection Summary Observation adds
  `algotrader.research.sma_conditional_return_selection_summary_observation`
  with a frozen/slotted
  `SmaConditionalReturnSelectionSummaryObservation` contract plus a pure
  `build_sma_conditional_return_selection_summary_observation(...)` builder.
  The artifact consumes the existing Phase 242
  `SmaConditionalReturnSelectionObservation`, preserves the source selection
  object, and emits primitive-only deterministic summary metadata for
  selection-period count, included count, excluded count, no-prior-SMA
  excluded count, insufficient-history excluded count, below-SMA excluded
  count, and equal-SMA excluded count. It also derives a fixed summary state
  for mixed, all-included, all-excluded, or empty classification sets. This
  phase remains advisory research metadata only and adds no return
  calculation, profit calculation, equity curve, trade order, position,
  allocation, portfolio state, readiness, approval, recommendation, signal or
  evaluator behavior, broker/runtime/vendor option, real data input,
  persistence, network/socket/API access, scheduler/dashboard behavior, ML,
  LLM/agent behavior, capital authority, trading authority, or deserialization
  behavior. Verification: `python -m pytest` -> 4698 passed, 4 skipped
- Phase 244 - SMA Selected Source Return Series Observation adds
  `algotrader.research.sma_selected_source_return_series_observation` with
  frozen/slotted `SmaSelectedSourceReturnPoint` and
  `SmaSelectedSourceReturnSeriesObservation` contracts plus a pure
  `build_sma_selected_source_return_series_observation(...)` builder. The
  artifact consumes the existing Phase 242
  `SmaConditionalReturnSelectionObservation`, preserves the source selection
  object and selected period identity, and emits primitive-only selected source
  return rows only for periods marked `included` by the above-SMA rule. Each
  row carries the source simple return value and return period dates from the
  included source period. This phase remains advisory research metadata only
  and adds no strategy-return calculation, compounded-return calculation,
  equity curve, cash return, benchmark comparison, portfolio state, exposure
  calculation, trade order, position, allocation, readiness, approval,
  recommendation, signal or evaluator behavior, broker/runtime/vendor option,
  real data input, persistence, network/socket/API access, scheduler/dashboard
  behavior, ML, LLM/agent behavior, capital authority, trading authority, or
  deserialization behavior. Verification: `python -m pytest` -> 4712 passed,
  4 skipped
- Phase 245 - SMA Selected Source Return Summary Observation adds
  `algotrader.research.sma_selected_source_return_summary_observation` with a
  frozen/slotted `SmaSelectedSourceReturnSummaryObservation` contract plus a
  pure `build_sma_selected_source_return_summary_observation(...)` builder.
  The artifact consumes the Phase 244
  `SmaSelectedSourceReturnSeriesObservation`, preserves the source selected
  source return series object, and emits primitive-only selected source return
  count, minimum selected source return, maximum selected source return, and
  arithmetic mean selected source return metadata. Empty selected source
  return inputs deterministically report no selected source returns and
  `None` for selected source return minimum, maximum, and arithmetic mean
  fields. This phase remains advisory research metadata only and does not
  compound selected source returns or convert selected source returns into any
  strategy, portfolio, invested, backtest, cash, benchmark, exposure,
  position, order, allocation, readiness, approval, recommendation, signal,
  evaluator behavior, broker/runtime/vendor option, real data input,
  persistence, network/socket/API access, scheduler/dashboard behavior, ML,
  LLM/agent behavior, capital authority, trading authority, or deserialization
  behavior. Verification: `python -m pytest` -> 4724 passed, 4 skipped
- Phase 246 - SMA Return Research Pipeline Observation adds
  `algotrader.research.sma_return_research_pipeline_observation` with a
  frozen/slotted `SmaReturnResearchPipelineObservation` contract plus a pure
  `build_sma_return_research_pipeline_observation(...)` builder. The artifact
  accepts the existing Phase 240 alignment observation, Phase 241 alignment
  summary, Phase 242 above-SMA selection observation, Phase 243 selection
  summary, Phase 244 selected source return series, and Phase 245 selected
  source return summary. It validates the identity-preserved derivation chain
  across all six source artifacts, emits primitive-only top-level source-count
  and summary-state metadata, and nests each source artifact in stable pipeline
  order. This phase remains advisory research metadata only and adds no new
  return math, strategy-return calculation, selected source return compounding,
  backtest behavior, equity curve, cash return, benchmark comparison,
  portfolio state, exposure calculation, trade order, position, allocation,
  readiness, approval, recommendation, signal or evaluator behavior,
  broker/runtime/vendor option, real data input, persistence,
  network/socket/API access, scheduler/dashboard behavior, ML, LLM/agent
  behavior, capital authority, trading authority, or deserialization behavior.
  Verification: `python -m pytest` -> 4737 passed, 4 skipped
- Phase 247 - Research Return Construction Policy Contract adds
  `algotrader.research.research_return_construction_policy` with a
  frozen/slotted `ResearchReturnConstructionPolicy` contract plus a pure
  `build_research_return_construction_policy()` builder. The contract pins the
  conservative research-only answer before future return-construction code:
  selected periods may carry source return observations only, excluded periods
  remain excluded without zero/cash/strategy mapping, missing periods are not
  imputed, no cash proxy exists, costs and slippage are not included,
  compounding is not allowed, and strategy-return, portfolio-return,
  cash-return, equity-curve, and backtest outputs are all disallowed. This
  phase is policy metadata only and does not accept source observations, apply
  the policy, calculate strategy returns, calculate portfolio returns,
  calculate cash returns, calculate equity curves, compound selected source
  returns, map excluded periods to cash or zero, create a benchmark comparison,
  create a backtest result, touch portfolio state, create exposure, create
  positions or orders, add allocation/readiness/approval/recommendation/signal
  or evaluator behavior, add broker/runtime/vendor behavior, add real data
  input, persistence, network/socket/API access, scheduler/dashboard behavior,
  ML, LLM/agent behavior, capital authority, trading authority, or
  deserialization behavior. Verification: `python -m pytest` -> 4747 passed,
  4 skipped
- Phase 248 - Research Return Construction Policy Observation Mechanics adds
  `algotrader.research.research_return_construction_policy_observation` with
  a frozen/slotted `ResearchReturnConstructionPolicyObservation` plus a pure
  `build_research_return_construction_policy_observation()` builder. The
  observation accepts only the exact Phase 247
  `ResearchReturnConstructionPolicy` type, preserves source policy identity,
  records deterministic zero audit counts for selected periods, excluded
  periods, source return observations, and forbidden outputs, and nests the
  source policy's existing primitive `to_dict()` payload unchanged. This phase
  is advisory audit metadata only and does not accept period inputs, construct
  returns, calculate strategy/portfolio/cash returns, calculate equity curves,
  compound returns, map excluded periods to cash or zero, create a benchmark
  comparison, create a backtest result, touch portfolio state, create
  exposure, create positions or orders, add allocation/readiness/approval/
  recommendation/signal/evaluator behavior, add broker/runtime/vendor
  behavior, add real data input, persistence, network/socket/API access,
  scheduler/dashboard behavior, ML, LLM/agent behavior, capital authority,
  trading authority, or deserialization behavior. Verification:
  `python -m pytest` -> 4761 passed, 4 skipped
- Phase 249 - SMA Return Research Pipeline Construction Policy Observation
  Attachment extends the existing
  `algotrader.research.sma_return_research_pipeline_observation` payload with
  a `return_construction_policy_observation` child. The pipeline builder
  constructs the Phase 247 `ResearchReturnConstructionPolicy` first, then
  constructs the Phase 248 `ResearchReturnConstructionPolicyObservation` from
  that exact policy object, preserving the pipeline -> policy observation ->
  source policy identity chain and nesting the policy observation's primitive
  `to_dict()` payload unchanged. This phase remains advisory metadata only and
  does not change the Phase 247 or Phase 248 contracts, expose CLI/package
  behavior, add broker/runtime/vendor behavior, real data input, persistence,
  network/socket/API access, scheduler/dashboard behavior, ML, LLM/agent
  behavior, evaluator/signal/trading behavior, portfolio/cash/equity/PnL
  state, allocation/order/fill behavior, benchmark comparison, backtest output,
  approval/readiness authority, timestamps, randomness, global state, hidden
  I/O, capital authority, trading authority, or deserialization behavior.
  Verification: `python -m pytest` -> 4762 passed, 4 skipped
- Phase 250 - Advisory Package SMA Return Pipeline Serialization Alignment
  pins the canonical synthetic advisory package/export fixture path to the
  Phase 249 `SmaReturnResearchPipelineObservation` payload. The package payload
  carries the existing SMA return research pipeline dictionary unchanged,
  including the nested Phase 248 `return_construction_policy_observation`
  generated from the same Phase 247 policy object, while content-bundle branch
  ordering and package CLI flags remain unchanged. This phase is serialization
  alignment only and adds no advisory conclusion, ranking, readiness/approval
  state, trading behavior, broker/runtime/vendor dependency, real data input,
  persistence, network/socket/API access, scheduler/dashboard behavior, ML,
  LLM/agent behavior, portfolio/cash/equity/PnL state, allocation/order/fill
  behavior, benchmark comparison, backtest output, timestamps, randomness,
  global state, hidden I/O, capital authority, trading authority, or
  deserialization behavior.
- Phase 251 - Advisory Package CLI SMA Pipeline Serialization Regression Guard
  adds a focused CLI/export test pin for the existing synthetic advisory
  package JSON path. The guard proves the
  `advisory-operating-brief-package-preview` command with `--format json`
  preserves the Phase 250 `sma_return_research_pipeline_observation` payload
  byte-deterministically, including exactly one nested
  `return_construction_policy_observation` matching the canonical
  package/export fixture policy observation. This phase is a regression guard
  only and adds no new CLI flags, commands, renderer branches, package
  behavior, advisory conclusions, ranking, readiness/approval state, trading
  behavior, broker/runtime/vendor dependency, real data input, persistence,
  network/socket/API access, scheduler/dashboard behavior, ML, LLM/agent
  behavior, portfolio/cash/equity/PnL state, allocation/order/fill behavior,
  benchmark comparison, backtest output, timestamps, randomness, global state,
  hidden I/O, capital authority, trading authority, or deserialization
  behavior.
- Phase 252 - SMA Return Research Pipeline Observation Export Snapshot adds
  `algotrader.research.sma_return_research_pipeline_observation_export` with
  `export_synthetic_sma_return_research_pipeline_observation_snapshot()`. The
  helper constructs the existing deterministic synthetic SMA return research
  pipeline through production research builders and returns the pipeline
  observation's primitive `to_dict()` payload unchanged, including exactly one
  nested `return_construction_policy_observation`. This phase is an export
  snapshot convenience only and adds no CLI/package behavior, evaluator/signal/
  trading behavior, portfolio/cash/equity/PnL state, allocation/order/fill
  behavior, benchmark comparison, backtest output, approval/readiness
  authority, broker/runtime/vendor dependency, real data input, persistence,
  network/socket/API access, scheduler/dashboard behavior, ML, LLM/agent
  behavior, timestamps, randomness, global state, hidden I/O, capital
  authority, trading authority, or deserialization behavior.
- Phase 253 - SMA Return Pipeline Export Snapshot Fixture Regression adds
  `tests.fixtures.sma_return_research_pipeline_observation_export` with
  expected dict and compact sorted-key JSON helpers for the Phase 252
  standalone export snapshot. The fixture reuses the canonical synthetic
  `SmaReturnResearchPipelineObservation.to_dict()` payload and pins exactly one
  nested `return_construction_policy_observation`. This phase is test/fixture
  regression coverage only and changes no production source, CLI/package
  behavior, renderer branch, evaluator/signal/trading behavior,
  portfolio/cash/equity/PnL state, allocation/order/fill behavior, benchmark
  comparison, backtest output, approval/readiness authority,
  broker/runtime/vendor dependency, real data input, persistence,
  network/socket/API access, scheduler/dashboard behavior, ML, LLM/agent
  behavior, timestamps, randomness, global state, hidden I/O, capital
  authority, trading authority, or deserialization behavior.
- Phase 254 - SMA Return Pipeline Export Snapshot Import Guard adds a focused
  file-based AST/source guard for the Phase 252 export snapshot and Phase 253
  expected fixture. It pins the export source to deterministic research
  contracts/builders, pins the fixture to expected fixture helpers, rejects
  forbidden CLI/package/broker/runtime/vendor/network/file/path/env/credential/
  trading imports or tokens, keeps the export signature zero-argument, and
  preserves the expected primitive payload. This phase is test/guard coverage
  only and changes no production source, CLI commands, CLI flags, package
  behavior, renderer branch, evaluator/signal/trading behavior,
  portfolio/cash/equity/PnL state, allocation/order/fill behavior, benchmark
  comparison, backtest output, approval/readiness authority,
  broker/runtime/vendor dependency, real data input, persistence,
  network/socket/API access, scheduler/dashboard behavior, ML, LLM/agent
  behavior, timestamps, randomness, global state, hidden I/O, capital
  authority, trading authority, or deserialization behavior.
- Phase 255 - Research Observation Manifest Contract adds
  `algotrader.research.research_observation_manifest`, a generic in-memory
  metadata manifest for primitive research observation payload dictionaries.
  It preserves input entry ordering, rejects malformed or duplicate named
  payloads, records top-level payload key counts, and hashes payloads with
  compact sorted-key JSON SHA-256. The manifest remains generic and does not
  import the SMA export snapshot module. This phase adds no file paths,
  persistence, CLI/package/renderer behavior, evaluator/signal/trading
  behavior, portfolio/cash/equity/PnL state, allocation/order/fill behavior,
  benchmark comparison, backtest output, approval/readiness authority,
  broker/runtime/vendor dependency, real data input, network/socket/API access,
  scheduler/dashboard behavior, ML, LLM/agent behavior, timestamps,
  randomness, global state, hidden I/O, capital authority, trading authority,
  or deserialization behavior.
- Phase 256 - SMA Export Snapshot Manifest Fixture Integration adds
  `tests.fixtures.research_observation_manifest` with expected dict and compact
  sorted-key JSON helpers for representing the Phase 253 SMA return research
  pipeline export snapshot as a one-entry Phase 255 generic metadata manifest.
  The fixture pins the stable observation name, payload key count, payload
  observation type, compact sorted-key JSON SHA-256 digest, primitive
  round-trippable `to_dict()` output, and repeated-call byte determinism. This
  phase is fixture/test integration only and changes no production source,
  CLI/package/renderer behavior, evaluator/signal/trading behavior,
  portfolio/cash/equity/PnL state, allocation/order/fill behavior, benchmark
  comparison, backtest output, approval/readiness authority,
  broker/runtime/vendor dependency, real data input, persistence,
  network/socket/API access, scheduler/dashboard behavior, ML, LLM/agent
  behavior, timestamps, randomness, global state, hidden I/O, capital
  authority, trading authority, or deserialization behavior. The production
  manifest remains generic and does not import SMA export modules.
- Phase 257 - Research Observation Manifest Import Guard adds
  `tests.unit.test_research_observation_manifest_dependency`, a focused
  test-only AST/source guard for the Phase 255 manifest, Phase 256 manifest
  fixture, and SMA manifest integration test. It pins the production manifest
  to generic deterministic dependencies, pins the fixture to the generic
  manifest contract and Phase 253 expected payload fixture, rejects SMA
  production/export coupling from the production manifest, and checks that the
  guarded files add no CLI/package/renderer/storage/file-I/O/runtime/broker/
  vendor surface. This phase changes no production source, CLI commands, CLI
  flags, package behavior, renderer behavior, storage behavior,
  evaluator/signal/trading behavior, portfolio/cash/equity/PnL state,
  allocation/order/fill behavior, benchmark comparison, backtest output,
  approval/readiness authority, broker/runtime/vendor dependency, real data
  input, persistence, network/socket/API access, scheduler/dashboard behavior,
  ML, LLM/agent behavior, timestamps, randomness, global state, hidden I/O,
  capital authority, trading authority, or deserialization behavior.
- Phase 258 - Research Observation Manifest Export Snapshot adds
  `algotrader.research.research_observation_manifest_export`, a tiny generic
  in-memory helper that accepts the Phase 255 manifest entry shape, builds the
  generic manifest, and returns `to_dict()` unchanged. Focused tests cover
  validation delegation, primitive JSON round-tripping, repeated-call and
  compact sorted-key JSON determinism, builder-defined ordering, SMA fixture
  compatibility through tests only, and import/source guardrails. This phase
  adds no SMA production coupling, CLI commands, CLI flags, package behavior,
  renderer behavior, storage behavior, file I/O, evaluator/signal/trading
  behavior, portfolio/cash/equity/PnL state, allocation/order/fill behavior,
  benchmark comparison, backtest output, approval/readiness authority,
  broker/runtime/vendor dependency, real data input, persistence,
  network/socket/API access, scheduler/dashboard behavior, ML, LLM/agent
  behavior, timestamps, randomness, global state, hidden I/O, capital
  authority, trading authority, or deserialization behavior.
- Phase 259 - Research Observation Manifest Export Import Guard adds
  `tests.unit.test_research_observation_manifest_export_dependency`, a focused
  test-only AST/source guard for the generic export helper. It pins imports to
  `__future__`, `collections.abc`, and the generic manifest builder; rejects
  SMA/package/CLI/renderer/runtime/broker/portfolio/vendor/network/storage/ML/
  LLM/trading dependencies and file/path/env/config/network helper surfaces;
  and verifies the helper returns
  `build_research_observation_manifest(entries).to_dict()` unchanged with
  compact sorted-key JSON determinism. This phase changes no production source,
  CLI/package/renderer behavior, storage behavior, file I/O,
  evaluator/signal/trading behavior, portfolio/cash/equity/PnL state,
  allocation/order/fill behavior, benchmark comparison, backtest output,
  approval/readiness authority, broker/runtime/vendor dependency, real data
  input, persistence, network/socket/API access, scheduler/dashboard behavior,
  ML, LLM/agent behavior, timestamps, randomness, global state, hidden I/O,
  capital authority, trading authority, or deserialization behavior.
- Phase 260 - Advisory Package Research Observation Manifest Attachment extends
  `AdvisoryOperatingBriefPackage` with an optional exact
  `ResearchObservationManifest` metadata-only audit field. The field preserves
  object identity, remains absent from `to_dict()` when unset, and emits the
  primitive manifest payload when present. The synthetic package preview now
  includes a one-entry manifest named
  `sma_return_research_pipeline_observation`, built from the included synthetic
  SMA return research pipeline observation's primitive `to_dict()` payload, so
  its digest deterministically matches that payload. This phase adds no CLI
  flags, renderer behavior, storage behavior, file/path/env inputs,
  evaluator/signal/trading behavior, portfolio/cash/equity/PnL state,
  allocation/order/fill behavior, benchmark comparison, backtest output,
  approval/readiness authority, broker/runtime/vendor dependency, real data
  input, persistence, network/socket/API access, scheduler/dashboard behavior,
  ML, LLM/agent behavior, timestamps, randomness, global state, hidden I/O,
  capital authority, trading authority, or deserialization behavior.
- Phase 261 - Advisory Package Research Observation Manifest Dependency Guard
  adds
  `tests.unit.test_advisory_operating_brief_package_manifest_dependency`, a
  focused test-only AST/source guard for the Phase 260 package and synthetic
  preview manifest attachment. It pins the package builder to the generic
  `ResearchObservationManifest` contract without manifest snapshot or SMA export
  coupling, rejects runtime/broker/vendor/network/storage/path/config/trading
  surfaces, checks the optional manifest exact-type boundary and optional
  serialization, verifies the synthetic preview builds the one-entry manifest
  from the included SMA return research pipeline observation payload, and
  asserts compact sorted-key JSON determinism. This phase changes no production
  source, CLI flags, renderer behavior, storage behavior, file/path/env/config/
  network inputs, evaluator/signal/trading behavior, portfolio/cash/equity/PnL
  state, allocation/order/fill behavior, benchmark comparison, backtest output,
  approval/readiness/recommendation authority, broker/runtime/vendor dependency,
  real data input, persistence, network/socket/API access, scheduler/dashboard
  behavior, ML, LLM/agent behavior, timestamps, randomness, global state,
  hidden I/O, capital authority, trading authority, or deserialization behavior.
- Phase 262 - Advisory Package Manifest CLI Serialization Regression Guard
  extends
  `tests.unit.test_advisory_operating_brief_package_cli_regression` to prove the
  existing `advisory-operating-brief-package-preview --format json` path carries
  the Phase 260 research observation manifest deterministically. It checks the
  one-entry manifest metadata, recomputes the compact sorted-key JSON SHA-256
  digest for the included SMA return research pipeline observation payload,
  asserts repeated JSON CLI output is byte-for-byte stable, keeps the preview
  CLI surface limited to the existing `--format text|json` option set, and
  guards that default/text rendering does not expose raw manifest internals.
  This phase changes no production source, CLI flags, renderer behavior, storage
  behavior, file/path/env/config/network inputs, evaluator/signal/trading
  behavior, portfolio/cash/equity/PnL state, allocation/order/fill behavior,
  benchmark comparison, backtest output, approval/readiness/recommendation
  authority, broker/runtime/vendor dependency, real data input, persistence,
  network/socket/API access, scheduler/dashboard behavior, ML, LLM/agent
  behavior, timestamps, randomness, global state, hidden I/O, capital authority,
  trading authority, or deserialization behavior.
- Phase 263 - Advisory Package Research Observation Manifest Export Helper adds
  `export_advisory_operating_brief_package_research_observation_manifest`, a
  tiny deterministic package-level helper that accepts only exact
  `AdvisoryOperatingBriefPackage` objects, requires an existing
  `research_observation_manifest`, and returns the manifest's primitive
  `to_dict()` payload unchanged. Focused tests prove exact-type rejection,
  unchanged manifest payload export, identity preservation, primitive JSON
  round-tripping, compact sorted-key JSON determinism, the single
  `sma_return_research_pipeline_observation` entry, digest alignment with the
  included SMA observation payload, and dependency-boundary constraints. This
  phase adds no CLI flags, renderer behavior, package builder behavior,
  synthetic builder behavior, storage behavior, file/path/env/config/network
  inputs, evaluator/signal/trading behavior, portfolio/cash/equity/PnL state,
  allocation/order/fill behavior, benchmark comparison, backtest output,
  approval/readiness/recommendation authority, broker/runtime/vendor dependency,
  real data input, persistence, network/socket/API access, scheduler/dashboard
  behavior, ML, LLM/agent behavior, timestamps, randomness, global state,
  hidden I/O, capital authority, trading authority, or deserialization behavior.
- Phase 264 - Advisory Package Manifest Export Dependency Guard adds
  `tests.unit.test_advisory_operating_brief_package_manifest_export_dependency`,
  a focused test-only AST/source guard for the Phase 263 package manifest export
  helper. It pins the helper to `ValidationError` and exact
  `AdvisoryOperatingBriefPackage` imports only, verifies the single-helper
  public surface, exact package and manifest validation, unchanged attached-
  manifest `to_dict()` export, no manifest builder/export helper calls, no I/O/
  runtime/broker/vendor/network/storage/path/config/ML/LLM/agent surfaces, no
  package or manifest mutation, and deterministic one-entry synthetic manifest
  export. This phase changes no production source, CLI flags, renderer
  behavior, package builder behavior, synthetic builder behavior, storage
  behavior, file/path/env/config/network inputs, evaluator/signal/trading
  behavior, portfolio/cash/equity/PnL state, allocation/order/fill behavior,
  benchmark comparison, backtest output, approval/readiness/recommendation
  authority, broker/runtime/vendor dependency, real data input, persistence,
  network/socket/API access, scheduler/dashboard behavior, ML, LLM/agent
  behavior, timestamps, randomness, global state, hidden I/O, capital
  authority, trading authority, or deserialization behavior.
- Phase 265 - Advisory Package Manifest Export Snapshot Fixture adds
  `tests.fixtures.advisory_operating_brief_package_manifest_export` plus
  `tests.unit.test_advisory_operating_brief_package_manifest_export_fixture` as
  a test-only reusable expected primitive payload and compact sorted-key JSON
  snapshot for the Phase 263 package manifest export helper. The fixture builds
  the existing synthetic package preview and returns the helper export
  unchanged; focused tests prove one-entry SMA pipeline metadata, SHA-256 digest
  alignment with the included synthetic observation payload, deterministic JSON
  round-tripping, no approval/readiness/trading-authority claims, and bounded
  fixture imports. This phase changes no production source and adds no CLI/
  renderer/broker/runtime/vendor/network/persistence/trading behavior.
- Phase 266 - Advisory Package Manifest Export Fixture Dependency Guard adds
  `tests.unit.test_advisory_operating_brief_package_manifest_export_fixture_dependency`,
  a focused test-only AST/source guard for the Phase 265 snapshot fixture. It
  pins fixture imports and `__all__`, proves the dict helper remains a thin
  synthetic-package build plus Phase 263 helper export, proves the JSON helper
  keeps compact sorted-key serialization, rejects direct generic manifest, SMA,
  CLI, renderer, runtime, broker, vendor, network, storage, path, config,
  ML/LLM/agent, I/O, digest, credential, authority, and trading tokens, and
  rechecks deterministic one-entry fixture output. This phase changes no
  production source and adds no CLI/renderer/broker/runtime/vendor/network/
  persistence/trading behavior.
- Phase 267 - Advisory Package Audit Snapshot Export Helper adds
  `export_advisory_operating_brief_package_audit_snapshot`, a tiny
  metadata-only package audit snapshot helper. It accepts only exact
  `AdvisoryOperatingBriefPackage` objects with an attached research observation
  manifest, composes the Phase 263 manifest export helper, and returns
  deterministic package identity metadata, the manifest payload, and compact
  sorted-key JSON SHA-256 digests for the package and manifest payloads.
  Focused tests guard exact type rejection, primitive JSON round-tripping,
  byte-stable synthetic output, no mutation, one-entry SMA pipeline manifest
  metadata, bounded imports, and no CLI/renderer/broker/runtime/vendor/network/
  persistence/data-ingestion/trading behavior changes.
- Phase 268 - Advisory Package Audit Snapshot Export Dependency Guard adds
  `tests.unit.test_advisory_operating_brief_package_audit_snapshot_export_dependency`,
  a test-only AST/source guard for the Phase 267 audit snapshot helper. It
  pins the helper to metadata-only imports, the Phase 263 manifest export
  helper, compact sorted-key JSON SHA-256 digests, exact snapshot keys,
  deterministic synthetic behavior, and no production source, CLI/renderer/
  broker/runtime/vendor/network/persistence/data-ingestion/trading behavior
  changes.
- Phase 269 - Research Data Source Readiness Contract adds
  `ResearchDataSourceReadiness` and
  `build_research_data_source_readiness` as a small frozen/slotted
  metadata-only contract for future research data source candidate review. It
  pins fixed metadata, computes missing controls deterministically, validates
  readiness states, duplicate-free controls/scopes/evidence refs, negative
  non-claims, primitive `to_dict()` output, deterministic compact JSON, and
  source guardrails against file/path/env/network/vendor/broker/runtime/
  persistence/portfolio/order/fill/backtest/ML/LLM/notebook/vectorbt/
  QuantConnect surfaces. It adds no real data ingestion, source approval, CLI/
  renderer/broker/runtime/vendor/network/persistence/backtest/trading
  behavior, strategy evaluation, or capital authority.
- Phase 270 - Research Data Source Readiness Dependency Guard adds
  `tests.unit.test_research_data_source_readiness_dependency`, a focused
  test-only AST/source guard for the Phase 269 contract. It pins imports,
  public surface, frozen/slotted dataclass shape, keyword-only builder metadata,
  fixed contract metadata, exact readiness states, derived missing controls,
  duplicate and unknown-control rejection, required limitations and negative
  non-claims, negative-only authority/trading language, primitive deterministic
  `to_dict()` output, and no file/path/env/network/vendor/broker/runtime/
  persistence/backtest/trading dependency tokens. This phase changes no
  production source and adds no real data ingestion, CLI/renderer/broker/
  runtime/vendor/network/persistence/backtest/trading behavior, approval
  authority, or capital authority.
- Phase 271 - Research Data Source Readiness Synthetic Fixture adds
  `tests.fixtures.research_data_source_readiness` and
  `tests.unit.test_research_data_source_readiness_fixture` as reusable
  metadata-only candidate readiness fixture coverage for the Phase 269
  contract. It builds through `build_research_data_source_readiness`, exposes
  the object, primitive dict, and compact sorted-key JSON unchanged, pins
  derived missing controls plus synthetic/internal evidence refs and negative
  non-claims, and changes no production source. It adds no real data ingestion,
  CLI/renderer/broker/runtime/vendor/network/persistence/backtest/trading
  behavior, data-source authorization, approval authority, or capital
  authority.
- Phase 272 - Research Data Source Readiness Export Snapshot adds test-only
  export snapshot helpers on the synthetic readiness fixture and
  `tests.unit.test_research_data_source_readiness_export`. The snapshot dict is
  exactly the existing primitive `to_dict()` payload, the JSON helper keeps
  compact sorted-key serialization, and focused tests pin byte stability,
  fresh equal payloads, builder-derived missing controls, and absence of
  wrapper, clock, digest, or raw payload fields. This phase changes no
  production source and adds no real data ingestion, CLI/renderer/broker/
  runtime/vendor/network/persistence/backtest/trading behavior.
- Phase 273 - Advisory Operating Brief Data Source Readiness Branch adds an
  optional `ResearchDataSourceReadiness` diagnostic branch to the advisory
  operating brief content bundle and synthetic package preview. Existing bundle
  outputs stay unchanged unless a fixture or synthetic package builder supplies
  the branch. The branch serializes through the existing readiness `to_dict()`
  contract, preserves builder-derived `missing_controls`, renders required,
  satisfied, and missing controls as diagnostic metadata, pins compact JSON and
  text output, and adds no real data ingestion, source/vendor approval, CLI
  options, broker/order/fill/portfolio/backtest/runtime/persistence/credential/
  network, or trading behavior.
- Phase 274 - Advisory Content Bundle CLI Data Source Readiness Preview adds a
  hidden synthetic-only `--include-research-data-source-readiness` flag to the
  advisory operating brief content bundle preview. Defaults stay byte-stable;
  the explicit flag renders or exports the existing readiness diagnostic branch
  with builder-computed `missing_controls`, deterministic branch order, and
  compact sorted-key JSON. Focused tests pin default stability, text/JSON
  output, repeated determinism, visible option-surface restrictions, and no
  broker/order/fill/portfolio/backtest/runtime/vendor/network/credential
  fields. This phase adds no real data ingestion, source selection, vendor
  access, approval semantics, runtime, persistence, broker, network, backtest,
  or trading behavior.
- Phase 275 - Advisory Package CLI Data Source Readiness Regression adds
  package-preview regression coverage for the existing synthetic research data
  source readiness diagnostic branch. The tests pin package synthetic output,
  package CLI text diagnostics, compact sorted-key package JSON with
  builder-computed `missing_controls`, repeated byte-for-byte text and JSON
  determinism, and the absence of new package input-bearing options beyond
  existing `--format text|json`. This phase changes no production source and
  adds no real data ingestion, source/vendor selection, approval semantics,
  runtime, persistence, broker, network, backtest, or trading behavior.
- Phase 276 - Research Data Source Readiness Advisory Integration Dependency
  Guard adds focused test-only coverage for the advisory content bundle
  readiness branch, renderer diagnostic wording, package synthetic readiness
  inclusion, and hidden content-bundle CLI preview flag. It pins
  metadata-only imports, synthetic-only readiness inclusion where applicable,
  hidden boolean-only non-input CLI handling, diagnostic/negative rendering,
  and no broker/runtime/vendor/network/persistence/backtest/trading calls or
  tokens.
  This phase changes no production source and adds no real data ingestion,
  source selection, source/vendor approval, runtime, persistence, broker,
  network, backtest, or trading behavior.
- Phase 277 - Research Data Source Readiness Summary Observation adds
  `ResearchDataSourceReadinessSummary`, a tiny metadata-only summary over an
  exact `ResearchDataSourceReadiness` object. It preserves source object
  identity, mirrors readiness state into `summary_state`, counts required,
  satisfied, and builder-computed missing controls from existing source fields
  only, and emits sorted diagnostic limitations as primitive deterministic
  metadata without nesting the source payload. Focused tests pin exact type
  rejection, frozen/slotted shape, primitive deterministic output, repeated
  build equality with distinct source identities, and dependency/import/call/
  token guardrails. This phase adds no real data ingestion, source selection,
  source/vendor approval, runtime, persistence, broker, network, backtest, or
  trading behavior.
- Phase 278 - Research Data Source Readiness Summary Fixture and Export
  Snapshot adds synthetic fixture helpers and focused export snapshot coverage
  for `ResearchDataSourceReadinessSummary`. The helpers build through the
  production summary builder supplied by the caller, use the existing
  synthetic `ResearchDataSourceReadiness` fixture, preserve source object
  identity when a source fixture is supplied, and export primitive snapshot
  dicts equal to `summary.to_dict()`. Focused tests pin compact sorted-key
  JSON, byte-stable repeated output, summary state, required/satisfied/missing
  control counts, diagnostic limitations, fresh primitive payload copies, and
  absence of source wrappers, raw payloads, clocks, digests, approval fields,
  broker/order/fill/portfolio/backtest/runtime fields, or trading behavior.
  This phase changes no production source and adds no real data ingestion,
  source selection, source/vendor approval, runtime, persistence, broker,
  network, backtest, or trading behavior.
- Phase 279 - Advisory Content Bundle Data Source Readiness Summary Branch
  adds an optional metadata-only `ResearchDataSourceReadinessSummary` branch to
  advisory content bundles. The branch is absent unless explicitly supplied,
  accepts exact summary objects only, serializes through `summary.to_dict()`,
  renders compact diagnostic counts and limitations, and is included
  deterministically by the synthetic advisory package builder beside the
  existing readiness diagnostic branch. Focused tests pin absent-by-default
  behavior, exact type rejection for subclasses/lookalikes/non-summary
  objects, renderer wording, compact sorted-key JSON determinism,
  byte-for-byte repeated text/JSON output, deterministic package branch order,
  and absence of broker/order/fill/portfolio/backtest/runtime/vendor/network/
  credential fields. This phase adds no real data ingestion, source
  selection, source/vendor approval, runtime, persistence, broker, network,
  backtest, or trading behavior.
- Phase 280 - Advisory Content Bundle CLI Data Source Readiness Summary
  Preview adds a hidden synthetic-only
  `--include-research-data-source-readiness-summary` flag to the advisory
  operating brief content bundle preview. Defaults remain byte-stable; the
  explicit flag renders or exports only the compact summary diagnostic branch
  with `summary_state`, required/satisfied/missing control counts, and
  diagnostic limitations. Focused tests pin text and compact sorted-key JSON
  output, byte-for-byte repeated determinism, hidden boolean-only non-input
  handling, visible option-surface restrictions, deterministic branch order
  when paired with the existing readiness diagnostic branch, and absence of
  broker/order/fill/portfolio/backtest/runtime/vendor/network/credential
  fields. This phase changes only the synthetic content-bundle preview CLI
  path and adds no real data ingestion, source selection, source/vendor
  approval, runtime, persistence, broker, network, backtest, or trading
  behavior.
- Phase 281 - Advisory Package CLI Data Source Readiness Summary Regression
  adds test-only package-preview regression coverage for the existing
  synthetic `ResearchDataSourceReadinessSummary` diagnostic branch. It pins
  package synthetic inclusion, package CLI text summary state and
  required/satisfied/missing control counts, diagnostic limitations, compact
  sorted-key JSON with deterministic summary count fields, repeated
  byte-for-byte text/JSON determinism, unchanged content bundle preview
  behavior, and no new package input-bearing options beyond existing
  `--format text|json`. This phase changes no production source and adds no
  real data ingestion, source selection, source/vendor approval, runtime,
  persistence, broker, network, backtest, or trading behavior.
- Phase 282 - Advisory Readiness Summary Integration Dependency Guard adds
  test-only source/AST dependency guard coverage for
  `ResearchDataSourceReadinessSummary` integration paths. It pins the content
  bundle summary branch as metadata-only, renderer output as diagnostic and
  negative, package synthetic inclusion as deterministic and authority-free,
  CLI preview handling as hidden boolean-only and non-input-bearing, and
  forbidden import/token/call/vocabulary scans across the targeted paths. This
  phase changes no production source and adds no real data ingestion, source
  selection, source/vendor approval, runtime, persistence, broker, network,
  backtest, or trading behavior.
- Phase 283 - Advisory Operating Brief Diagnostic Issue List adds a tiny
  metadata-only issue-record builder for advisory operating brief content
  bundles. It returns deterministic frozen/slotted
  `AdvisoryOperatingBriefDiagnosticIssue` records from existing research data
  source readiness and readiness summary diagnostic branches, carrying only
  source branch, issue code, issue state, diagnostic message, blocking
  controls, and limitations. Focused tests pin paired synthetic
  readiness/readiness-summary inputs, missing controls as diagnostic controls
  rather than approvals, deterministic branch ordering, frozen/slotted
  immutability, primitive-only `to_dict()` output, repeated-build equality,
  and absence of broker/order/fill/portfolio/backtest/runtime/vendor/network/
  credential fields or approval/trading vocabulary. This phase adds no real
  data ingestion, source selection, source/vendor approval, runtime,
  persistence, broker, network, backtest, or trading behavior.
- Phase 284 - Advisory Diagnostic Issue Fixture and Export Snapshot adds
  test-only synthetic fixture helpers and export snapshot coverage for
  advisory operating brief diagnostic issues. The fixture composes the existing
  synthetic advisory content bundle with readiness/readiness-summary
  diagnostics, builds records through the production diagnostic issue builder,
  and exposes only the issue `to_dict()` payload list plus compact sorted-key
  JSON. Focused tests pin snapshot equality with issue payloads, deterministic
  branch ordering, expected source branch/issue code/state/message/blocking
  controls/limitations, repeated fixture equality, fresh primitive payload
  copies, and absence of raw data, timestamps, digest fields, wrapper fields,
  approval fields, or broker/order/fill/portfolio/backtest/runtime/vendor/
  network behavior. This phase changes no production source and adds no real
  data ingestion, source selection, source/vendor approval, runtime,
  persistence, broker, network, backtest, or trading behavior.
- Phase 285 - Advisory Content Bundle Diagnostic Issues Branch adds an
  optional metadata-only `diagnostic_issues` branch to advisory operating brief
  content bundles. The branch is absent from payloads unless explicitly
  supplied, accepts only exact `AdvisoryOperatingBriefDiagnosticIssue` records,
  preserves supplied issue order, and serializes each issue through
  `issue.to_dict()`. Rendering emits diagnostic issue metadata only: source
  branch, issue code, issue state, diagnostic message, blocking controls, and
  limitations. Export keeps compact sorted-key JSON determinism, and the
  synthetic advisory package preview explicitly includes the existing
  diagnostic issues derived from its readiness diagnostics. Focused tests pin
  default absence, exact type rejection for subclasses/lookalikes, repeated
  text and JSON byte determinism, synthetic package inclusion, and no new
  execution, vendor, network, persistence, backtest, or trading behavior.
- Phase 286 - Advisory Content Bundle CLI Diagnostic Issues Preview adds a
  hidden synthetic-only `--include-diagnostic-issues` flag to the advisory
  operating brief content bundle preview. The default preview remains
  byte-for-byte unchanged, while the explicit flag derives existing
  deterministic diagnostic issue records from the synthetic readiness
  diagnostics and exposes only the `diagnostic_issues` branch. Focused CLI
  regression tests pin text and JSON issue fields, repeated byte-for-byte
  determinism, hidden boolean-only non-input handling, visible option-surface
  restrictions, compact sorted-key JSON determinism, preserved issue order, and
  no broker/order/fill/portfolio/backtest/runtime/vendor/network/credential
  fields or ranking/scoring/recommendation/approval vocabulary in the
  diagnostic issue branch. This phase changes only synthetic preview CLI
  plumbing and adds no real data ingestion, source selection, source/vendor
  approval, runtime, persistence, broker, network, backtest, or trading
  behavior.
- Phase 287 - Advisory Package CLI Diagnostic Issues Regression adds test-only
  package-preview coverage proving the existing synthetic `diagnostic_issues`
  branch is carried through the canonical advisory package path. It pins
  package synthetic inclusion, package CLI text output for source branch,
  issue code, issue state, diagnostic message, blocking controls, and
  limitations, compact sorted-key JSON output, nested content-bundle export
  payload inclusion, repeated byte-for-byte text/JSON determinism, no new
  package input-bearing options beyond existing `--format text|json`, and no
  broker/order/fill/portfolio/backtest/runtime/vendor/network/credential
  fields or ranking/scoring/recommendation/approval vocabulary in the
  diagnostic issue branch. This phase changes no production source and adds no
  real data ingestion, source selection, source/vendor approval, runtime,
  persistence, broker, network, backtest, or trading behavior.
- Phase 288 - Advisory Diagnostic Issues Integration Dependency Guard adds
  focused test-only dependency/source guard coverage proving the diagnostic
  issue content bundle, renderer, synthetic package builder, CLI preview, and
  package export integrations remain metadata-only, diagnostic-only,
  deterministic, and free of broker/runtime/vendor/network/trading behavior.
  The guards pin hidden boolean-only CLI handling, diagnostic/negative
  renderer wording, deterministic synthetic issue ordering, package export
  branch shape without wrappers/timestamps/digests/authority fields, and
  forbidden import/token/call/vocabulary scans. This phase changes no
  production source and adds no real data ingestion, source selection,
  source/vendor approval, runtime, persistence, broker, network, backtest, or
  trading behavior.
- Phase 289 - Advisory Operating Brief Section Records adds an unexported
  metadata-only section layer for existing advisory operating brief content
  bundles. The builder accepts only exact
  `AdvisoryOperatingBriefContentBundle` objects, emits frozen/slotted
  `AdvisoryOperatingBriefSection` records for present branches in fixed
  branch order, and records only section key/title/state, source branch key,
  item count, diagnostic messages for diagnostic issues, and section-layer
  limitations. Focused tests pin deterministic ordering, primitive-only
  `to_dict()` copies, repeated-build equality, source-bundle non-mutation,
  exact-type rejection, frozen/slotted immutability, package non-exposure,
  and no broker/order/fill/portfolio/backtest/runtime/vendor/network/
  credential fields or ranking/scoring/recommendation/approval/trading
  vocabulary. This phase does not wire the layer into CLI, renderer, package,
  preview, data, or runtime paths and adds no real data ingestion, source
  selection, source/vendor approval, persistence, broker, network, backtest,
  or trading behavior.
- Phase 290 - Advisory Section Fixture and Export Snapshot adds test-only
  synthetic fixture helpers for `AdvisoryOperatingBriefSection` records. The
  fixture composes the existing synthetic advisory content bundle and
  diagnostic issue fixtures, then builds section records only through
  `build_advisory_operating_brief_sections()`. Snapshot helpers return exactly
  each section `to_dict()` payload and compact sorted-key JSON, preserving
  present-branches-only behavior, deterministic section ordering, diagnostic
  messages, and limitations without wrapper fields, timestamps, digests, or raw
  branch payloads. Focused tests pin repeated-build equality, byte-for-byte JSON
  determinism, primitive fresh-copy payloads, fixture dependency bounds, and no
  broker/order/fill/portfolio/backtest/runtime/vendor/network/credential fields
  or ranking/scoring/recommendation/approval/trading vocabulary. This phase
  changes no production source and adds no real data ingestion, source
  selection, source/vendor approval, persistence, broker, network, backtest, or
  trading behavior.
- Phase 291 - Advisory Content Bundle Sections Branch adds an explicit optional
  `advisory_sections` branch to advisory operating brief content bundles. The
  branch is absent unless supplied, accepts only exact
  `AdvisoryOperatingBriefSection` records, preserves supplied ordering, does not
  make an otherwise empty bundle valid, serializes each section through
  `section.to_dict()`, and contributes only section limitations to aggregate
  bundle limitations. Rendering emits section metadata only after diagnostic
  issues and before aggregate limitations, while the synthetic package preview
  derives sections from its diagnostic-inclusive bundle and explicitly includes
  them in the final synthetic package content bundle. This phase adds no
  content-bundle CLI surface and no real data ingestion, source selection,
  source/vendor approval, persistence, runtime, broker, network, backtest, or
  trading behavior.
- Phase 292 - Advisory Content Bundle CLI Sections Preview adds a hidden
  synthetic-only `--include-advisory-sections` boolean flag to
  `advisory-operating-brief-content-bundle-preview`. Default output stays
  byte-for-byte unchanged; with the flag, the preview builds deterministic
  section records from the existing synthetic diagnostic section source and
  attaches only the `advisory_sections` branch. Text and compact sorted-key
  JSON output preserve builder ordering and expose only section key/title/state,
  source branches, item count, diagnostic messages, and limitations. Focused
  tests pin hidden non-input-bearing CLI handling, repeated text/JSON
  determinism, compact JSON, no file/path/source/vendor/broker/network/
  credential options, and no broker/order/fill/portfolio/backtest/runtime/
  vendor/network/credential fields or ranking/scoring/recommendation/approval
  vocabulary in the advisory sections branch. This phase adds no real data
  ingestion, source selection, source/vendor approval, persistence, runtime,
  broker, network, backtest, or trading behavior.
- Phase 293 - Advisory Package CLI Sections Regression adds test-only
  package-preview coverage proving the existing synthetic `advisory_sections`
  branch is carried through the canonical advisory package path. It pins text
  output for section key/title/state, source branches, item count, diagnostic
  messages, and metadata-only limitations; compact sorted-key JSON output;
  nested content-bundle export payload inclusion; repeated byte-for-byte text
  and JSON determinism; unchanged package input-bearing options; and no
  broker/order/fill/portfolio/backtest/runtime/vendor/network/credential fields
  or ranking/scoring/recommendation/approval vocabulary in the section branch.
  This phase changes no production source and adds no real data ingestion,
  source selection, source/vendor approval, persistence, runtime, broker,
  network, backtest, or trading behavior.
- Phase 294 - Advisory Sections Integration Dependency Guard adds focused
  test-only source and payload guard coverage for the `advisory_sections`
  integration path across content bundle serialization, renderer wording,
  synthetic package construction, hidden content-bundle CLI preview handling,
  and package export payload shape. The guards pin metadata-only renderer
  fields, hidden boolean-only CLI wiring, deterministic synthetic package
  section order, compact JSON stability, and no wrapper/timestamp/digest/
  authority/broker/order/fill/portfolio/runtime/vendor/network/credential
  fields or ranking/scoring/recommendation/approval/trading vocabulary. This
  phase changes no production source and adds no real data ingestion, source
  selection, source/vendor approval, persistence, runtime, broker, network,
  backtest, or trading behavior.
- Phase 295 - Advisory Operating Brief View Records adds
  `src/algotrader/research/advisory_operating_brief_view.py`, a tiny
  metadata-only advisory view model over existing
  `AdvisoryOperatingBriefSection` records. The builder accepts either one exact
  section record or a tuple of exact section records, rejects subclasses and
  lookalikes, preserves supplied section order, and emits frozen/slotted
  `AdvisoryOperatingBriefView` records with only view key/title/state, section
  count, section keys, metadata summary lines, diagnostic messages, and
  limitations. `to_dict()` returns fresh primitive-only deterministic payloads
  without wrapper/timestamp/digest/raw-payload fields. Focused unit coverage
  pins synthetic section fixture composition, exact-type validation,
  immutability, source-section non-mutation, repeated-build equality,
  diagnostic-only wording, and no broker/order/fill/portfolio/backtest/runtime/
  vendor/network/credential fields or ranking/scoring/recommendation/approval/
  trading vocabulary. This phase adds no renderer, CLI, package, dashboard,
  scheduler, persistence, runtime, broker, vendor, network, backtest, or
  trading behavior.
- Phase 296 - Advisory View Fixture and Export Snapshot adds test-only
  synthetic fixture helpers for `AdvisoryOperatingBriefView`. The fixture uses
  the existing synthetic advisory section fixtures and builds only through
  `build_advisory_operating_brief_view()`. Snapshot helpers return exactly
  `view.to_dict()` plus compact sorted-key JSON, preserving supplied section
  order and present-sections-only behavior. Focused tests pin view key/title/
  state, section count, section keys, summary lines, diagnostic messages,
  limitations, repeated-build equality, fresh primitive payload copies, fixture
  dependency bounds, and no raw data, timestamps, digests, wrappers, source
  payloads, broker/order/fill/portfolio/backtest/runtime fields, or actionable
  trading vocabulary. This phase changes no production source and adds no
  package, CLI, renderer, dashboard, scheduler, persistence, runtime, broker,
  vendor, network, backtest, or trading behavior.
- Phase 297 - Advisory Content Bundle View Branch adds an optional
  `advisory_view` branch to advisory operating brief content bundles. The
  branch is absent by default, accepts only an exact
  `AdvisoryOperatingBriefView`, serializes through `view.to_dict()`, and renders
  only view key/title/state, section count, section keys, summary lines,
  diagnostic messages, and limitations. The synthetic package preview includes
  the view built from its existing synthetic advisory sections; content-bundle
  CLI behavior remains unchanged. Focused tests pin exact-type rejection,
  compact sorted-key JSON and text determinism, package export inclusion,
  metadata-only shape, and no broker/order/fill/portfolio/backtest/runtime/
  vendor/network/credential fields or ranking/scoring/recommendation/approval
  vocabulary. This phase adds no real data ingestion, source selection,
  source/vendor approval, persistence, runtime, broker, network, backtest, or
  trading behavior.
- Phase 300 - Synthetic Research MVP Operating Brief adds
  `advisory-operating-brief-mvp-preview` as a deterministic local CLI command
  that composes the existing synthetic advisory package, content bundle,
  advisory view, sections, diagnostic issues, data-source readiness records,
  and SMA/return research observation surfaces into a human-readable terminal
  report. The report shows advisory summary, present sections, diagnostic and
  readiness blockers, synthetic observations, and explicit blocked/missing
  items before real strategy, backtest, or trading use. Focused tests pin CLI
  registration, text readability, compact JSON consistency, byte determinism,
  compatibility with existing preview commands, no file/environment/network
  access, and no broker/credential/live/vendor runtime behavior. This phase
  adds no real data ingestion, persistence, scheduler, dashboard, broker,
  orders, fills, portfolio/reconciliation mutation, ranking, scoring,
  recommendation, approval, backtest execution, or trading authority.
- Phase 301 / Milestone 301 - Synthetic Operating Brief Work Queue extends the
  MVP preview with a deterministic `Work Queue / Next Non-Trading Work Items`
  section and matching JSON records derived from existing synthetic package,
  diagnostic, readiness, research observation, blocked, and missing surfaces.
  Each item records label, reason, state, and protected boundary for
  data-source gaps, source/universe/benchmark/cash controls, real data approval
  gaps, no-lookahead implementation, deterministic backtest readiness,
  validation/reproduction evidence, diagnostic blockers, advisory-only
  research observations, and absent trading authority. This phase adds no real
  data ingestion, persistence, scheduler, dashboard, broker, orders, fills,
  portfolio/reconciliation mutation, ranking, scoring, recommendation,
  approval, backtest execution, or trading authority.
- Phase 302 / Milestone 302 - Synthetic Backtest Readiness Gate extends the MVP
  preview with a deterministic `Backtest Readiness Gate` section and compact
  JSON `backtest_readiness_gate` records. The gate reports real strategy
  backtesting as blocked/not ready and enumerates project-control records for
  real data source approval, source/universe/benchmark/cash policy,
  no-lookahead protocol, return construction, validation/reproduction evidence,
  strategy approval, and trading authority. This phase is reporting-only and
  adds no real data ingestion, persistence, scheduler, dashboard, broker,
  orders, fills, portfolio/reconciliation mutation, ranking, scoring,
  recommendation, approval, actual backtest execution, or trading authority.
- Phase 303 / Milestone 303 - Synthetic Strategy Candidate Dossier Report
  extends the MVP preview with a deterministic `Strategy Candidate Dossier`
  section and compact JSON `strategy_candidate_dossiers` records for the
  synthetic broad ETF SMA trend-following pipeline-validation candidate. The
  dossier is synthetic-only and advisory-only, records research purpose,
  synthetic observation state, missing evidence and controls, blocked/not-ready
  backtest state, not-approved strategy state, no trading authority, and the
  next non-trading control step, and adds no real data ingestion, persistence,
  scheduler, dashboard, broker, orders, fills, portfolio/reconciliation
  mutation, ranking, scoring, recommendation, approval, actual backtest
  execution, or trading authority.
- Phase 309 / Milestone 309 - Logged Paper Lab Revalidation Brief adds
  `paper-lab-revalidation-brief` as a deterministic local read-only CLI command
  for summarizing an existing paper-lab snapshot JSONL run log. It reports run
  ids, selected/latest run event counts, account cash/currency availability,
  position count and symbols, recent order count and safe order-status fields,
  missing observations, unavailable/error events with secret-safe details,
  redaction markers, advisory labels, `profit_claim = none`, and the states
  `usable_for_manual_review`, `insufficient_observation`,
  `observation_unavailable`, and `invalid_run_log`. This milestone adds no
  real equity, crypto, or options order submission, broker write path, live
  profile behavior, credentials, network access, scheduler, autonomous loop,
  market-data ingestion, portfolio/reconciliation mutation, ranking, scoring,
  recommendation, trading authority, or trading hot-path LLM behavior.
- Phase 311 / Milestone 311 - Crypto Paper Submit Gate Enablement opens only
  the tiny BTCUSD crypto paper-lab submit harness through the existing
  `paper-order-probe` machinery. Crypto submit is paper-profile-only,
  buy-only, market-only, `time_in_force=gtc`, notional-only, capped by
  `notional <= max_notional` and `max_notional <= 5.00`, and requires both
  `--submit` and `--i-mean-it`; live profile and live URL remain rejected.
  The SPY equity paper submit contract is preserved and still waits for market
  hours, options submit remains disabled, and crypto paper observations are a
  shared broker-path harness only, not proof of equity behavior. This
  milestone uses fake-only deterministic coverage and does not run a real
  broker submit; normal pytest remains offline, credential-free,
  deterministic, and safe.
- Phase 313 / Milestone 313 - Crypto Paper Submit Adapter Diagnostic records
  M312 as a failed-safe BTCUSD tiny probe: read-only snapshots observed
  `2000 USD` cash, zero positions, zero recent orders, no broker receipt, and
  an `observation_unavailable` revalidation state after two failed submit
  sequences. The M312 run log is contaminated and must not be reused for
  another submit. The fake-backed hotfix preserves the SPY equity path and
  disabled options submit, keeps crypto as a broker-path harness rather than
  proof of equity behavior, improves sanitized adapter/SDK diagnostics for
  request construction versus pre-response submit failures, fixes crypto
  notional quantity gate wording, and adds no network, credentials, live URL,
  scheduler, autonomous trading, research-layer direct submission, or broker
  retry behavior. No confirmed broker-side crypto order exists from M312; the
  next broker action should wait for a fresh run id/log after the hotfix.
- Phase 315 / Milestone 315 - BTCUSD Crypto Paper Submit APIError Diagnostic
  inspects the M314 loaded-env BTCUSD run log without reusing it for another
  submit. M314 shows one guarded submit attempt, no broker response, and a
  pre-response SDK `APIError` after paper profile and policy gates passed. The
  hotfix keeps the paper policy unchanged and carries sanitized APIError
  diagnostics through SDK, adapter, CLI JSON, and paper-lab JSONL failure rows:
  submit stage, exception class, HTTP status code when exposed, Alpaca error
  code when exposed, URL/token-redacted message text, and request shape summary.
  It preserves false broker-response flags and unknown submitted/accepted/filled
  state, adds only fake-backed deterministic tests, and performs no real
  BTCUSD, equity, crypto, or options submit.
- Phase 317 / Milestone 317 - Crypto Minimum Notional Policy Gate converts the
  M316 `BTCUSD` paper observation into deterministic local policy. The fresh
  M316 log shows one `BTCUSD` crypto submit attempt with `notional=1.00` and
  `max_notional=5.00`; all local gates passed, then Alpaca returned sanitized
  `APIError` status `403`, code `40310000`, and `cost basis must be >= minimal
  amount of order 10` before any broker receipt. The crypto paper lane now
  requires `min_notional=10.00`, reports
  `notional_below_crypto_min_notional` locally before submit, includes the
  required minimum in JSON/JSONL output, and supports the future user-approved
  safe path `notional=10.00` with `max_notional=10.00`. Paper profile, paper
  URL, buy-only, market/GTC, notional-only, `BTCUSD` allowlist, disabled
  options submit, SPY equity behavior, no retries, no scheduler, and
  offline/credential-free normal pytest behavior are preserved; M317 submits no
  real orders.
- Phase 319 / Milestone 319 - Crypto Paper Receipt + Position/Reconciliation
  Observation extends the local-file-only `paper-lab-revalidation-brief` with a
  deterministic `submit_observation` summary for paper-order probe run logs. It
  connects submit attempt count, receipt presence, broker response flags,
  submitted/accepted/filled, raw and normalized status/reason, order shape,
  pre/post cash, Decimal cash delta, pre/post position counts, target BTCUSD
  position details, recent-order target visibility, order-list gap,
  unavailable observations, and redaction markers. The added taxonomy separates
  accepted receipt + position, accepted receipt + position with an order-list
  gap, receipt without position, position without receipt, broker rejection,
  submit failed before response, unavailable observation, insufficient
  observation, and invalid run-log states. The M318 BTCUSD log now classifies
  as `receipt_and_position_observed_with_order_list_gap`: one accepted
  `BTCUSD` crypto buy receipt at `notional=10.00`, cash moved from `2000` to
  `1990.19`, a BTCUSD position appeared, and `recent_orders` stayed empty. This
  milestone is analysis/local-summary only and adds no submit command, Alpaca
  call, live profile/live URL behavior, credential access, broker write path,
  scheduler, autonomous loop, research-layer submission, or unsafe pytest
  behavior.
- Phase 320 / Milestone 320 - Crypto Paper Order-List Gap Diagnostics keeps
  the M319 `receipt_and_position_observed_with_order_list_gap` classification
  and adds deterministic local reasons for the M318 order-list gap. Snapshot
  output now records recent-order query attempted/available flags, returned
  count, and currently unspecified limit/status/asset/symbol/time-window
  filters. Recent-order observations preserve safe `order_id` and
  `client_order_id` fields when exposed by the fake/SDK boundary. The
  revalidation brief now reports target receipt correlation fields, target
  recent-order match status, match basis (`client_order_id`, `broker_order_id`,
  `symbol_side_notional`, or `none`), and `order_list_gap_reason` values such
  as `recent_order_query_returned_empty`,
  `target_order_not_in_recent_order_results`,
  `receipt_missing_correlation_id`, `order_query_unavailable`, and
  `insufficient_order_query_metadata`. For the M318 shape, the state remains
  `receipt_and_position_observed_with_order_list_gap` and the local reason is
  `recent_order_query_returned_empty`. This milestone adds no submit command,
  close/sell order, Alpaca call, network use, live profile/live URL behavior,
  credential access, broker write path, scheduler, autonomous loop,
  research-layer submission, or unsafe pytest behavior.
- Phase 321 / Milestone 321 - Paper Recent-Order Query Contract adds a
  deterministic fake/local-only query contract before any future paper close or
  exit probe. `AlpacaRecentOrderQuery` is versioned as
  `paper_recent_order_query_v1` and defaults to open orders, limit `100`,
  descending direction, `nested=false`, no symbol/asset-class/side filters, no
  after/until window, no sort key, and source
  `alpaca_sdk_client.get_orders`. Only the approved SDK boundary converts that
  internal contract to alpaca-py's `GetOrdersRequest`; fake clients receive the
  internal query object directly. Snapshot JSON/JSONL/text and revalidation
  output now record the contract fields plus
  `recent_order_query_metadata_complete` and
  `recent_order_query_metadata_missing_fields`. M318/M320-shaped logs still
  classify as `receipt_and_position_observed_with_order_list_gap` with
  `order_list_gap_reason=recent_order_query_returned_empty`, but incomplete
  metadata is explicit: local query metadata proves only what the snapshot
  layer requested or recorded, not external broker order state. This milestone
  adds no submit command, close/sell order, Alpaca call, network use, live
  profile/live URL behavior, credential access, broker write path, scheduler,
  autonomous loop, research-layer submission, or unsafe pytest behavior.
- Phase 322 / Milestone 322 - Post-Receipt Paper Reconciliation Brief adds a
  deterministic `post_receipt_reconciliation` section to the local
  `paper-lab-revalidation-brief` JSON/text output. It summarizes sanitized
  receipt flags, status, order shape, pre/post cash, Decimal cash delta, target
  position quantity and average price, recent-order query contract metadata,
  target recent-order match basis, order-list gap diagnostics, confidence,
  limitations, and read-only next operator action. Confidence values are
  `high_receipt_position_cash_observed`,
  `medium_receipt_position_observed_order_gap`, `low_receipt_only`,
  `low_position_only`, `unavailable`, and `invalid`. For the old M318/M321
  shape, the state remains
  `receipt_and_position_observed_with_order_list_gap`,
  `order_list_gap_reason=recent_order_query_returned_empty`,
  `recent_order_query_metadata_complete=false`,
  `reconciliation_confidence=medium_receipt_position_observed_order_gap`, and
  `recommended_next_operator_action=read_only_fresh_snapshot_before_any_close_probe`.
  The brief preserves `paper_lab_only`, `not_live_authorized`, and
  `profit_claim=none`, and adds no submit command, close/sell order, Alpaca
  call, network use, live profile/live URL behavior, credential access, broker
  write path, scheduler, autonomous loop, research-layer submission, or unsafe
  pytest behavior.
- Phase 323 / Milestone 323 - Fresh Paper Snapshot Operator Checklist adds a
  deterministic `fresh_snapshot_operator_checklist` section to the local
  `paper-lab-revalidation-brief` JSON/text output. It records pre-run operator
  checks for a separate paper-profile shell, credential-free normal pytest,
  `APP_PROFILE=paper` only in the snapshot shell, a fresh run log path and run
  id, and read-only `paper-lab-snapshot` only. It exposes the fixed command
  template (`python -m algotrader paper-lab-snapshot --run-log runs/paper_lab/<fresh_id>.jsonl --run-id <fresh_id> --format json`), post-run
  evidence checks for profile gate, ok/mutated/submitted, account/positions/
  orders observations, BTCUSD position presence/details, recent-order query
  metadata, unavailable observations, redaction marker, live-profile evidence,
  and credential-like evidence. Old M318/M321-shaped logs remain conservative:
  the checklist reports `blocked_query_metadata_incomplete` and keeps
  `read_only_fresh_snapshot_before_any_close_probe`. Synthetic future fresh
  read-only logs with complete query metadata and complete observations report
  `read_only_snapshot_completed_for_manual_review`. The checklist preserves
  `paper_lab_only`, `not_live_authorized`, and `profit_claim=none`, and adds no
  submit command, close/sell order, Alpaca call, network use, live profile/live
  URL behavior, credential access, broker write path, scheduler, autonomous
  loop, research-layer submission, close-order design, profit inference, or
  unsafe pytest behavior.
- Phase 325 / Milestone 325 - BTCUSD Close/Exit Probe Design Preview adds a
  deterministic local/fake-only `paper_close_preview_v1` contract and
  `paper-close-preview` CLI for designing a BTCUSD paper close preview from a
  local fresh read-only snapshot run log. It gates the design on
  `asset_class=crypto`, `symbol=BTCUSD`, `side=sell`, market/GTC order shape,
  positive requested quantity, requested quantity within the observed BTCUSD
  position, no-shorting, fresh checklist status
  `read_only_snapshot_completed_for_manual_review`, complete recent-order query
  metadata, `mutated=false`, and `submitted=false`. The revalidation brief now
  reports `close_exit_probe_design` as design-ready only for manual review. This
  milestone preserves `paper_lab_only`, `not_live_authorized`,
  `profit_claim=none`, and `manual_review_required`; it is not a broker order
  receipt, does not claim a close, and adds no submit command, close/sell order
  placement, Alpaca call, network use, live profile/live URL behavior,
  credential access, broker write path, cancel/replace/liquidate behavior,
  options behavior, portfolio mutation, profit inference, or unsafe pytest
  behavior.
- Phase 326 / Milestone 326 - BTCUSD Close Action Eligibility Checklist adds a
  deterministic local-only `close_action_eligibility_checklist` section to
  `paper-lab-revalidation-brief` JSON/text output. It classifies whether a
  later broker-side BTCUSD paper close probe may be considered for explicit
  operator approval, while preserving `broker_action_performed=false` and
  `close_order_submitted=false`. Eligibility requires a completed fresh
  read-only snapshot checklist and an observed successful
  `paper_close_preview_designed` event with preview-only/manual-review labels,
  crypto/BTCUSD/sell shape, positive quantity within the observed BTCUSD
  position, no-shorting passed, no mutation, no submit, complete query metadata,
  redaction evidence, no live-profile evidence, and no credential-leak evidence.
  Snapshot-only evidence remains blocked with `blocked_missing_close_preview`;
  complete evidence reports `eligible_for_explicit_operator_approval` and
  recommends `prepare_explicit_paper_close_probe_prompt_but_do_not_submit`.
  This milestone adds no submit command, close/sell order placement, Alpaca
  call, network use, live profile/live URL behavior, credential access, broker
  write path, cancel/replace/liquidate behavior, options behavior, portfolio
  mutation, profit inference, or unsafe pytest behavior.
- Phase 327 / Milestone 327 - Explicit BTCUSD Paper Close Probe Preparation
  adds a deterministic local-only `future_close_probe_preparation` section to
  `paper-lab-revalidation-brief` JSON/text output. It is manual-review-only,
  preserves `manual_review_only=true`, `broker_action_performed=false`, and
  `close_order_submitted=false`, and reports whether the evidence is ready for
  future prompt generation. The section lists required operator confirmations,
  required pre-submit snapshot evidence, required BTCUSD position quantity,
  required recent-order query metadata, required close-preview evidence,
  required M326 eligibility status, blocking reasons, and the recommended next
  operator action. It remains blocked unless M326 reports
  `eligible_for_explicit_operator_approval`; eligible evidence recommends
  `draft_explicit_paper_close_probe_command_for_operator_review_only`. Any
  future template is review-only/unsafe until separate manual authorization and
  uses `<EXPLICIT_SUBMIT_FLAG_NOT_INCLUDED>` instead of a submit flag. This
  milestone adds no submit command, close/sell/cancel/liquidation behavior,
  Alpaca call, network use, live profile/live URL support, credential access,
  broker write path, scheduler, autonomous loop, research-layer authorization,
  portfolio mutation, profit inference, or unsafe pytest behavior.
- Phase 328 / Milestone 328 - Explicit BTCUSD Paper Close Probe Prompt Review
  adds a deterministic local-only `explicit_close_probe_prompt_review` section
  to `paper-lab-revalidation-brief` JSON/text output. It is
  operator-review-only, preserves `manual_review_only=true`,
  `broker_action_performed=false`, and `close_order_submitted=false`, and
  reports prompt readiness, whether the section was generated from M327
  `future_close_probe_preparation`, observed M327 readiness, observed M326
  eligibility status, observed BTCUSD symbol/quantity, recent-order query
  metadata completeness, required final fresh pre-submit snapshot, required
  final operator confirmation, future probe scope, blocking reasons,
  recommended operator action, review-only prompt text, and a non-submit future
  command template. It becomes ready only when M327 is ready, M326 reports
  `eligible_for_explicit_operator_approval`, close-preview evidence exists, the
  fresh snapshot checklist is complete, recent-order query metadata is
  complete, and the `credentials_redacted` marker is present. Eligible evidence
  recommends
  `review_explicit_paper_close_probe_prompt_and_decide_whether_to_authorize_separate_m329`;
  blocked evidence recommends
  `complete_future_close_probe_preparation_before_prompt_review`. This
  milestone adds no submit command, broker-side close/sell/cancel/liquidation
  behavior, Alpaca call, network use, live profile/live URL support, credential
  access, broker write path, scheduler, autonomous loop, research-layer
  authorization, portfolio mutation, profit inference, or unsafe pytest
  behavior.
- Phase 329A / Milestone 329A - Missing BTCUSD Close-Preview Evidence Repair
  wires the existing local-only `paper-close-preview` command to optionally
  append a durable `paper_close_preview_designed` JSONL event via
  `--output-run-log` and `--output-run-id`. The command still reads local
  run-log evidence only, does not load runtime config, does not build a broker,
  and has no submit flag. The event records the preview-only BTCUSD sell shape,
  including `quantity`, `max_quantity`, `observed_position_quantity`,
  `remaining_quantity_after_preview`, `no_shorting_gate=passed`,
  `submitted=false`, `mutated=false`, `broker_action_performed=false`, and
  `close_order_submitted=false`, so M326/M327/M328 revalidation can consume the
  same evidence without introducing broker-side close behavior.
- Phase 334 / Milestone 334 - BTCUSD Paper Lifecycle Manual Review records a
  manual, local-evidence-only review of
  `runs/paper_lab/m331_btcusd_close_probe.jsonl` and
  `runs/paper_lab/m333_credentialed_post_close_followup_snapshot.jsonl`. The
  first BTCUSD paper lifecycle is operationally reviewed as broker-lifecycle
  evidence only, not strategy performance evidence, not profitability
  validation, and not a final settlement claim. Broker action count remains
  exactly one explicit M331 BTCUSD paper close probe. M333 is treated as
  read-only post-close follow-up evidence with `ok=true`, `mutated=false`,
  `submitted=false`, BTCUSD absent, remaining BTCUSD quantity `0`, recent open
  orders `0`, account/positions/orders observed, cash `1999.9 USD`, complete
  recent-order query metadata, `credentials_redacted`, no unavailable
  observations, and no credential-leak evidence. The reconciliation state is
  `accepted_close_response_position_absent_no_open_orders` with
  `reconciliation_confidence=medium_position_absent_order_lifecycle_incomplete`.
  The limitations remain binding: the submit response did not report
  `filled=true`, the broker order id was not exposed by the normalized mapper,
  reconciliation is position-based only, and final settlement must not be
  claimed.
- The next paper-lab operating rule is now explicit: future paper experiments
  require a fresh read-only snapshot before submit, exactly one explicit broker
  action per approved probe, and a post-action read-only snapshot after that
  action. Ambiguous broker response means stop and collect read-only evidence.
  No retry, cancel, liquidate, close, fix-forward, or other broker/account/
  portfolio mutation may occur without a separate explicit milestone. M334 adds
  no broker call, submit, cancel/liquidation/retry/fix-forward behavior, live
  profile/live URL support, credential access, scheduler/autonomous behavior,
  research-layer broker authority, profit inference, or unsafe pytest behavior.
- Phase 335 / Milestone 335 - Simple ETF/SMA Research-to-Paper Candidate v1
  adds the first strategy-producing artifact after the BTCUSD paper lifecycle
  review. The new `etf_sma_research_to_paper_candidate` contract is a pure
  research-layer broad ETF SMA trend/crossover candidate using deterministic
  caller-supplied local bars and an explicit `as_of` date. It computes only from
  bars available at or before `as_of`, reports latest close, short SMA, long
  SMA, posture, evidence summary, limitations, labels, eligibility, and next
  operator action, and labels the artifact `research_only`,
  `paper_lab_candidate`, `not_live_authorized`, and `profit_claim=none`.
  Eligibility remains
  `separate_plan_required_before_paper_experiment`; the next action is a
  separate paper-lab experiment plan, not a broker action. The artifact is
  offline-only, credential-free, not paper-submission authorized, not live
  authorized, and adds no Alpaca call, broker adapter call, market-data fetch,
  scheduler/autonomous behavior, order submission, or broker/order/fill/account/
  credential/portfolio mutation fields.
- Phase 336 / Milestone 336 - ETF/SMA Paper-Lab Experiment Plan v1 adds the
  separate review-only plan contract for the M335 ETF/SMA candidate. The new
  `etf_sma_paper_experiment_plan` contract preserves `research_only`,
  `paper_lab_candidate`, `not_live_authorized`, and `profit_claim=none`, and
  emits `paper_experiment_plan_drafted`, `requires_operator_review`, and
  `not_broker_authorized` statuses. It carries forward symbol, strategy name,
  `as_of`, SMA windows, latest close, short SMA, long SMA, candidate posture,
  metadata-only cap policy, required pre-submit checks, limitations, source
  candidate metadata, safeguards, and next operator action. Bullish candidates
  become review-only `candidate_long_bias`, defensive candidates become
  review-only `candidate_defensive_bias`, and insufficient-history candidates
  become `observe_only`.
- M336 encodes the M334 paper-lab safeguards in the plan: fresh read-only
  snapshot before any future submit, max one broker action per separately
  approved future probe, post-action read-only snapshot, stop on ambiguous
  broker response, and no retry/cancel/liquidate/close/fix-forward without a
  separate explicit milestone. It authorizes no broker action, broker preview or
  staging, `ExecutionIntent`, `ExecutionPlan`, credentials, network,
  market-data fetch, live profile/live URL, scheduler/autonomous behavior, or
  order/fill/account/portfolio mutation. The next milestone may create a
  preview-only local policy/checklist, not a submit path.
- Phase 337 / Milestone 337 - ETF/SMA Offline Backtest Summary v1 adds the
  first deterministic measurement artifact for the M335/M336 ETF/SMA path. The
  new `etf_sma_offline_backtest_summary` contract consumes only deterministic
  caller-supplied local or synthetic bars, an immutable config, and an explicit
  `as_of` date. It ignores future bars, computes SMA signals from closes
  available at or before each signal bar, applies exposure only to later return
  intervals with a one-bar delay, and reports bar counts, signal/exposure/
  defensive counts, posture changes, strategy total return, buy-and-hold
  benchmark total return, max drawdown, and latest posture.
- M337 preserves `research_only`, `paper_lab_candidate`,
  `not_live_authorized`, and `profit_claim=none`, with eligibility fixed at
  `research_measurement_only`. Its required limitations are
  `synthetic_or_local_input_only`, `zero_cost_or_declared_cost_model`,
  `no_slippage_model_unless_explicitly_added`,
  `no_live_or_paper_authorization`, and `not_profit_evidence`. It authorizes no
  broker action, broker preview or staging, `ExecutionIntent`, `ExecutionPlan`,
  credentials, network, market-data fetch, live profile/live URL,
  scheduler/autonomous behavior, or order/fill/account/portfolio mutation. The
  next step is local data snapshot validation or a gated preview packet before
  any paper-lab experiment, not broker submission.
- Phase 338 / Milestone 338 - ETF/SMA Research-to-Paper Evidence Packet v1 adds
  the first deterministic packet tying together the M335 ETF/SMA research
  candidate, the M336 paper-lab experiment plan, and the M337 offline backtest
  summary. The new `etf_sma_research_to_paper_evidence_packet` contract
  preserves source labels, source eligibility, latest posture, bar/signal/
  exposure/defensive counts, posture changes, ignored future bar count,
  strategy total return, buy-and-hold benchmark total return, max drawdown,
  limitations, blocking reasons, required next action, and evidence summary.
- M338 preserves `research_only`, `paper_lab_candidate`,
  `not_live_authorized`, and `profit_claim=none`. The best allowed status is
  `ready_for_paper_lab_preview_design`; conservative inputs such as missing
  paper-lab-candidate labels, `live_authorized` source labels, insufficient
  history, zero bars, zero signal count, observe-only plan posture, or
  defensive plan posture produce `blocked_from_paper_lab_preview_design`.
  Required packet limitations are `not_profit_evidence`,
  `offline_research_only`, `paper_preview_requires_separate_milestone`,
  `no_broker_action_authorized`, and `not_live_authorized`. The required next
  action is `draft_separate_paper_lab_preview_plan`, a separate design artifact
  and not a broker path. M338 authorizes no broker action, broker preview or
  staging, `ExecutionIntent`, `ExecutionPlan`, credentials, network,
  market-data fetch, live profile/live URL, scheduler/autonomous behavior, LLM
  or agent runtime dependency, profit claim, or order/fill/account/portfolio
  mutation.
- Phase 339 / Milestone 339 - ETF/SMA Paper-Lab Preview Design v1 adds the
  deterministic offline design contract that consumes only the M338 ETF/SMA
  research-to-paper evidence packet plus static local config. The new
  `etf_sma_paper_lab_preview_design` contract preserves source packet status,
  source eligibility, source required next action, source labels, symbol,
  strategy name, `as_of`, latest posture, bar/signal/exposure/defensive counts,
  posture changes, strategy total return, buy-and-hold benchmark total return,
  max drawdown, source limitations, blocking reasons, required future operator
  checks, and required next action.
- M339 preserves `research_only`, `paper_lab_candidate`,
  `not_live_authorized`, and `profit_claim=none`. The best allowed status is
  `ready_for_paper_lab_preview_prompt_review`; blocked inputs produce
  `blocked_from_paper_lab_preview_prompt_review`. Ready designs require a ready
  M338 packet, required source labels, no `live_authorized` label or status, no
  profit claim other than `profit_claim=none`, and bullish research posture.
  Source blockers, insufficient history, observe-only posture, defensive
  posture, missing paper-lab-candidate labels, live authorization, and non-none
  profit claims all remain blockers. Required limitations are
  `offline_design_only`, `not_profit_evidence`,
  `no_broker_preview_authorized`, `no_broker_action_authorized`,
  `paper_preview_requires_separate_milestone`,
  `submit_requires_separate_explicit_milestone`, and `not_live_authorized`.
  Required future operator checks include a fresh read-only paper snapshot
  before any future broker-facing preview, paper profile only, explicit
  operator approval before any future broker-facing preview, separate milestone
  before broker-facing preview, separate milestone before any submit, no live
  trading authorization, and no retry/cancel/liquidate/fix-forward behavior from
  this design. M339 authorizes no broker action, broker preview or staging,
  `ExecutionIntent`, `ExecutionPlan`, credentials, network, market-data fetch,
  live profile/live URL, scheduler/autonomous behavior, LLM or agent runtime
  dependency, profit claim, or order/fill/account/portfolio mutation.
- Phase 340 / Milestone 340 - ETF/SMA Paper-Lab Preview Prompt Review v1 adds
  the deterministic offline prompt-review contract that consumes only the M339
  ETF/SMA paper-lab preview design plus static local config. The new
  `etf_sma_paper_lab_preview_prompt_review` contract preserves source design
  status, source required next action, source labels, symbol, strategy name,
  `as_of`, latest posture, strategy and benchmark total returns, max drawdown,
  bar/signal/exposure/defensive/posture-change counts, source limitations,
  blocking reasons, future operator checklist, future prompt template,
  future-prompt readiness, and required next action.
- M340 preserves `research_only`, `paper_lab_candidate`,
  `not_live_authorized`, and `profit_claim=none`. The best allowed status is
  `prompt_ready_for_operator_review`; blocked inputs produce
  `blocked_from_prompt_review`. Ready reviews require a ready M339 design,
  required source labels, no live authorization label or status, no profit
  claim other than `profit_claim=none`, and bullish research posture. Source
  design blockers, insufficient history, observe-only posture, defensive
  posture, missing paper-lab-candidate labels, live authorization, and non-none
  profit claims all remain blockers. The ready next action is
  `operator_review_before_separate_paper_preview_milestone`; the blocked next
  action is `resolve_paper_preview_design_blockers`.
- M340 required limitations are `offline_prompt_review_only`,
  `not_profit_evidence`, `no_broker_preview_authorized`,
  `no_broker_action_authorized`, `paper_preview_requires_separate_milestone`,
  `submit_requires_separate_explicit_milestone`, and `not_live_authorized`.
  Required future operator checklist values include paper profile only, a
  fresh read-only paper snapshot before any future broker-facing preview, no
  open conflicting orders before a future preview, explicit operator approval
  before a broker-facing preview, separate milestones before broker-facing
  preview and before any submit, no live trading authorization, stop on
  ambiguous broker response, and no retry/cancel/liquidate/fix-forward without
  a separate explicit milestone.
- The M340 future prompt template is review-only and non-executable. It
  contains `<FUTURE_SEPARATE_MILESTONE_REQUIRED>`,
  `<BROKER_PREVIEW_COMMAND_NOT_INCLUDED>`, `<SUBMIT_FLAG_NOT_INCLUDED>`,
  `<PAPER_PROFILE_REQUIRED>`, and `<FRESH_READ_ONLY_SNAPSHOT_REQUIRED>`, and no
  submit flag or broker execution command. M340 authorizes no broker action,
  broker preview or staging, `ExecutionIntent`, `ExecutionPlan`, credentials,
  network, market-data fetch, live profile/live URL, scheduler/autonomous
  behavior, LLM or agent runtime dependency, profit claim, or order/fill/
  account/portfolio mutation.
- Phase 341 / Milestone 341 - ETF/SMA Paper Preview Operator Review v1 adds
  the deterministic offline operator-review contract that consumes only the
  M340 ETF/SMA paper-preview prompt-review output plus static local config. The
  new `etf_sma_paper_preview_operator_review` contract preserves M340 source
  readiness, required next action, source labels, upstream source labels,
  symbol, strategy name, `as_of`, latest posture, strategy and benchmark total
  returns, max drawdown, bar/signal/exposure/defensive/posture-change counts,
  source limitations, source blocking reasons, derived blocking reasons,
  required future operator checks, a non-executable future review template, and
  required next action.
- M341 preserves `research_only`, `paper_lab_candidate`,
  `not_live_authorized`, and `profit_claim=none`. The best allowed status is
  `authorize_separate_paper_preview_milestone`; blocked inputs produce
  `blocked_from_separate_paper_preview_milestone`. Ready operator reviews
  require M340 to be `prompt_ready_for_operator_review`, required source labels,
  source future-prompt readiness, no live authorization label or status, no
  profit claim other than `profit_claim=none`, no M340 blockers, and bullish
  research posture. Prompt-review blockers, missing `paper_lab_candidate`,
  insufficient history, defensive posture, live authorization, and non-none
  profit claims all remain blockers.
- M341 hard-codes `authorize_paper_preview_now=false`,
  `authorize_broker_action=false`, `broker_action_performed=false`,
  `broker_preview_performed=false`, and `submit_allowed=false`. It requires
  manual operator review before any future separate paper-preview milestone and
  a fresh read-only paper snapshot before any later broker-facing preview/probe
  milestone. The ready next action is
  `prepare_separate_etf_sma_paper_preview_milestone`; the blocked next action
  is `resolve_prompt_review_blockers`.
- M341 limitations include `offline_operator_review_only`,
  `manual_operator_review_required`,
  `fresh_read_only_paper_snapshot_required_before_later_broker_facing_preview`,
  `not_live_authorization`, `not_profit_evidence`, `not_strategy_validation`,
  `not_execution_authority`, `no_broker_preview_authorized`,
  `no_broker_action_authorized`, `paper_preview_requires_separate_milestone`,
  and `submit_requires_separate_explicit_milestone`. M341 authorizes no broker
  action, broker preview or staging, `ExecutionIntent`, `ExecutionPlan`,
  credentials, network, market-data fetch, live profile/live URL,
  scheduler/autonomous behavior, LLM dependency, strategy validation, profit
  evidence, or order/fill/account/portfolio mutation.
- M342 adds a deterministic offline
  `etf_sma_paper_preview_evidence_packet` contract that consumes only M341
  operator-review output plus static local config. It preserves M341 status,
  required next action, operator-review blockers, upstream source blockers,
  operator-review limitations, upstream source limitations, operator labels,
  source labels, upstream labels, symbol, strategy name, `as_of`, latest
  posture, strategy and benchmark total returns, max drawdown, and
  bar/signal/exposure/defensive/posture-change counts.
- M342 emits `ready_for_separate_paper_preview_preparation` only when M341 is
  `authorize_separate_paper_preview_milestone`, M341 readiness is true, there
  are no M341 or upstream source blockers, required research-only labels are
  preserved, there is no live authorization label or status, the profit claim
  remains `profit_claim=none`, and posture is bullish. Blocked inputs emit
  `blocked_from_separate_paper_preview_preparation`. Missing
  `paper_lab_candidate`, non-none profit claims, live authorization,
  insufficient history, defensive posture, source blockers, and false M341
  readiness all block preparation.
- M342 hard-codes `evidence_packet_version` to
  `etf_sma_paper_preview_evidence_packet_v1`, `evidence_scope` to
  `local_research_to_paper_preview_preparation_only`, `broker_facing=false`,
  and `executable=false`. It preserves `authorize_paper_preview_now=false`,
  `authorize_broker_action=false`, `broker_action_performed=false`,
  `broker_preview_performed=false`, and `submit_allowed=false`. Required future
  prerequisites are manual operator review, a fresh read-only paper snapshot, a
  separate paper-preview milestone, and explicit operator approval before any
  broker-facing preview. Ready packets recommend
  `draft_separate_etf_sma_paper_preview_milestone`; blocked packets recommend
  `resolve_operator_review_blockers`.
- M342 limitations include `local_advisory_evidence_only`,
  `not_live_authorized`, `not_profit_evidence`, `not_strategy_validation`,
  `not_execution_authority`, `not_broker_order_fill_account_portfolio_evidence`,
  `paper_preview_requires_separate_milestone`,
  `broker_facing_preview_requires_separate_milestone`, and
  `submit_requires_separate_explicit_milestone`. M342 authorizes no broker
  action, broker preview or staging, `ExecutionIntent`, `ExecutionPlan`,
  credentials, network, market-data fetch, live profile/live URL,
  scheduler/autonomous behavior, LLM dependency, strategy validation, profit
  evidence, or order/fill/account/portfolio mutation.
- M343 adds a deterministic offline
  `etf_sma_paper_preview_milestone_draft` contract that consumes only the M342
  ETF/SMA paper-preview evidence packet plus static local config. It preserves
  M342 packet status, recommended next action, evidence-packet blockers,
  operator-review blockers, upstream source blockers, evidence-packet
  limitations, operator-review limitations, upstream source limitations,
  evidence labels, operator-review labels, source labels, upstream labels,
  symbol, strategy name, `as_of`, latest posture, strategy and benchmark total
  returns, max drawdown, and bar/signal/exposure/defensive/posture-change
  counts.
- M343 emits `ready_for_operator_review_of_paper_preview_milestone` only when
  M342 is `ready_for_separate_paper_preview_preparation`, M342 preparation
  readiness is true, M342 is not broker-facing or executable, all broker/submit
  action flags remain false, required research-only labels are preserved, there
  is no live authorization label or status, the profit claim remains
  `profit_claim=none`, there are no M342/source blockers, and posture is
  bullish. Blocked inputs emit
  `blocked_from_operator_review_of_paper_preview_milestone`. Missing
  `paper_lab_candidate`, non-none profit claims, live authorization,
  insufficient history, defensive posture, source blockers,
  broker-facing/executable evidence, and true broker/submit action flags all
  block operator review.
- M343 hard-codes `paper_preview_performed=false`,
  `broker_action_performed=false`, `broker_preview_performed=false`,
  `submit_allowed=false`, `executable=false`, and `broker_facing=false`.
  Required future prerequisites are committing M343 before any future
  milestone, running a fresh read-only paper snapshot before any broker-facing
  preview/probe, explicit operator approval before any broker-facing preview, a
  market-hours/session check for equities before any broker-facing preview, and
  stopping if market/session/broker behavior is ambiguous. Ready drafts
  recommend `operator_review_m343_then_prepare_m344_fresh_read_only_snapshot`;
  blocked drafts recommend `resolve_evidence_packet_blockers`.
- M343 draft text explicitly states `research_only`, `paper_lab_candidate`,
  `not_live_authorized`, `profit_claim=none`, not execution authority, not
  strategy validation, not live authorization, no broker command included, no
  submit flag included, and that normal pytest must remain offline,
  credential-free, deterministic, and safe. M343 authorizes no broker action,
  broker preview or staging, `ExecutionIntent`, `ExecutionPlan`, credentials,
  network, market-data fetch, live profile/live URL, scheduler/autonomous
  behavior, LLM dependency, strategy validation, profit evidence, or
  order/fill/account/portfolio mutation.
- M345 adds the first practical offline ETF/SMA signal evaluator in
  `algotrader.signals.etf_sma_evaluator`. It consumes only deterministic
  in-memory `Bar` objects plus immutable config through
  `EtfSmaSignalEvaluator` or `evaluate_etf_sma_signal`, enforces UTC `as_of`
  and bar timestamps, rejects invalid windows and mixed symbols, sorts bars
  deterministically, ignores and counts future bars, computes SMA50/SMA200,
  and emits frozen/slotted `EtfSmaSignalResult` posture:
  `bullish_risk_on`, `defensive_risk_off`, or `insufficient_history`.
- M345 is signal evaluation only. Labels are `paper_lab_only`,
  `signal_evaluation_only`, `not_live_authorized`, and `profit_claim=none`;
  `profit_claim=none`, `broker_action_performed=false`, and
  `submit_allowed=false` are fixed; and `next_action` points to
  `m346_offline_etf_sma_signal_to_risk_execution_preview_bridge_no_broker_action`.
  It authorizes no paper orders, no broker or Alpaca calls, no credentials, no
  network or market-data fetch, no `ExecutionIntent`, no `ExecutionPlan`, no
  risk/planning policy invocation, no portfolio/account/order/fill mutation,
  no scheduler/autonomous behavior, no live profile/live URL, and no LLM
  trading-path dependency. M344 remains prior paper-lab evidence only; M345
  did not run a fresh paper snapshot.
- M346 adds the first offline ETF/SMA signal-to-execution-preview bridge in
  `algotrader.orchestration.etf_sma_execution_preview_bridge`. It consumes
  only an M345 `EtfSmaSignalResult` plus immutable local preview config and
  emits a frozen/slotted `EtfSmaExecutionPreview` artifact. Bullish/risk-on SPY
  within the SPY-only allowlist and `max_notional <= 25.00` is accepted as an
  offline paper-lab preview candidate; defensive, insufficient-history, and
  non-allowlisted signals skip deterministically.
- M346 remains fully offline and pre-broker. It calls no broker, Alpaca,
  network, credential reader, paper snapshot command, paper order probe, risk
  engine, execution-planning policy, scheduler/runtime loop, or LLM trading
  path. It authorizes no paper submit, creates no broker order,
  `ExecutionIntent`, or `ExecutionPlan`, and mutates no portfolio, account,
  order, fill, or position state. Its hard-false flags are
  `broker_action_performed=false`, `broker_preview_performed=false`,
  `submit_allowed=false`, and `mutated=false`; `profit_claim=none`,
  `not_live_authorized`, SPY-only, and `max_notional <= 25.00` stay fixed.
  M344 remains prior paper context only and is not consumed as runtime input.
- M347 adds the local offline ETF/SMA preview JSONL artifact layer in
  `algotrader.orchestration.etf_sma_preview_jsonl_artifact`. It consumes only
  M346 `EtfSmaExecutionPreview` output, builds frozen/slotted
  `EtfSmaPreviewJsonlRecord` objects, and writes one deterministic
  newline-terminated JSON object per call to an explicit caller-provided path.
  Default mode creates a new file only; appending and parent directory creation
  are opt-in configuration choices.
- M347 records preserve source signal symbol, asset class, `as_of`, M345
  posture, SMA windows, M346 accepted/skipped preview status, deterministic
  skip reason, max notional, allowlist decision, source labels, and source
  preview payload. Labels preserve `paper_lab_only`,
  `offline_execution_preview_only`, `not_live_authorized`, and
  `profit_claim=none`; source signal labels preserve `signal_evaluation_only`.
  The artifact hard-codes `broker_action_performed=false`,
  `broker_preview_performed=false`, `submit_allowed=false`,
  `capital_mutated=false`, and `broker_mutated=false`, rejects live-authorized
  labels and non-none profit claims, and points next action to
  `m348_fresh_read_only_paper_snapshot_before_broker_facing_preview`.
- M347 performs no broker action, broker preview or staging, submit/cancel/
  close/liquidate behavior, credential loading, network or market-data fetch,
  `ExecutionIntent` or `ExecutionPlan` creation, scheduler/autonomous behavior,
  LLM trading-path work, or portfolio/account/order/fill mutation. Tests use
  `tmp_path` for file writes and normal pytest remains offline,
  credential-free, deterministic, and safe.
- M349 adds `algotrader.orchestration.etf_sma_paper_broker_preview` plus the
  `etf-sma-paper-preview-only` CLI. It consumes M347 ETF/SMA preview evidence
  and an M348 fresh read-only paper snapshot revalidation. Only bullish SPY,
  equity, notional-only, `market`/`day`, and `max_notional <= 25.00` can render
  a local broker-shaped payload preview; defensive, insufficient-history,
  non-SPY, unsafe notional, or unsafe source-label cases skip before payload.
- M349 blocks before preview if the M348 snapshot is not
  `usable_for_manual_review`, if positions or recent open orders are present,
  if recent-order query metadata is incomplete, if observations are
  unavailable, or if live-profile, credential-leak, prior submit, or prior
  mutation evidence appears. It hard-codes `submit_allowed=false`,
  `submitted=false`, `mutated=false`, `broker_action_performed=false`,
  `broker_preview_performed=false`, `not_live_authorized`, and
  `profit_claim=none`. Because no true non-mutating broker preview API is
  available, M349 performs only a local payload render and writes the local
  JSONL run log when explicitly requested.
- M349 performs no broker action, broker preview endpoint call, order staging,
  submit, cancel, close, liquidate, retry, Alpaca/network/market-data call,
  scheduler/runtime behavior, `ExecutionIntent`, `ExecutionPlan`, credential
  persistence/printing, LLM trading-path work, or portfolio/account/order/fill
  mutation. The next action is
  `m350_operator_review_before_any_tiny_spy_paper_probe`.
- M350 adds
  `algotrader.orchestration.etf_sma_paper_probe_operator_review`, a frozen
  deterministic operator-review checkpoint for the M349 SPY preview evidence.
  It reads one local M349 JSONL preview record, reviews the embedded M348
  fresh read-only snapshot evidence, and emits either
  `ready_for_separate_tiny_spy_paper_probe_milestone` or
  `blocked_from_tiny_spy_paper_probe_milestone`.
- M350 requires M348 `usable_for_manual_review`, observed account/positions/
  recent orders, zero positions, zero recent open orders, complete recent-order
  metadata, no unavailable observations, and no live-profile, credential-leak,
  submit, or mutation evidence. It requires M349 SPY/equity/buy,
  `market`/`day`, `notional <= 25.00`, `not_live_authorized`,
  `profit_claim=none`, no live-authorized status, no non-none profit claim,
  and all submit/broker/mutation flags false.
- M350 is review-only and authorizes only scoping a separate future M351 tiny
  SPY paper probe milestone; it does not authorize submit now. It hard-codes
  `operator_review_required=true`,
  `separate_future_probe_milestone_required=true`, `submit_allowed=false`,
  `submitted=false`, `mutated=false`, `broker_action_performed=false`,
  `broker_preview_performed=false`, `paper_probe_performed=false`, and
  `live_authorized=false`. The checked M349 evidence reviews as
  `ready_for_separate_tiny_spy_paper_probe_milestone` with no blockers and
  next action
  `m351_separate_tiny_spy_paper_probe_scope_if_operator_approves`.
- M351 is the explicit operator-approved tiny SPY paper probe. It remains
  paper-profile gated, SPY allowlisted, equity-only, `market`/`day`, notional
  sized, and capped at `25.00`. It records deterministic local JSONL evidence
  for the single SPY buy and does not authorize another buy, retry,
  cancellation, liquidation, scheduler behavior, live endpoint, or live order.
- M352 is a read-only SPY settlement snapshot after M351. It records account,
  positions, recent orders, SPY fractional quantity and average price, recent
  open order count, `mutated=false`, `submitted=false`, and credential
  redaction without broker mutation.
- M353 adds `paper-lab-order-traceability-review`, a read-only SPY
  traceability command that loads M351/M352 local evidence and reads account,
  positions, and bounded SPY buy order lists for open, all, and closed
  statuses. The ready state requires the SPY position, zero recent open SPY
  buy orders, one filled M351-correlated SPY buy order, complete recent-order
  metadata, `mutated=false`, `submitted=false`, and credential redaction.
- M354 adds `paper-lab-spy-close-preview`, a broker-facing close-preview
  readiness command for the observed fractional SPY paper position. It consumes
  M353 traceability evidence, then performs fresh read-only account, position,
  and open-SPY-order observations and writes a deterministic JSONL artifact
  such as `runs/paper_lab/m354_spy_cleanup_close_preview.jsonl`.
- M354 emits `ready_for_separate_spy_paper_close_submit_milestone` only when
  M353 evidence is present and ready, fresh SPY position quantity and average
  price still match M353, SPY is the only position, recent open SPY orders are
  zero across sides, account/position/order observations are available,
  order-query metadata is complete, SPY/equity/sell/market/day metadata is
  complete, quantity is positive and within the observed SPY position, the
  paper-profile gate passes, and all submit/broker/mutation/live flags remain
  false. Otherwise it emits
  `blocked_from_spy_paper_close_submit_milestone`.
- M354 is preview/readiness only. Blocked artifacts list stale-evidence,
  open-order, unexpected-position, and unavailable-observation blockers and
  leave preview `quantity` blank. It performs no submit, cancel, close,
  liquidate, replace, retry, second SPY buy, live-profile/live-endpoint
  behavior, autonomous scheduling, credential printing, or live trading. The
  next milestone is M355 explicit operator-approved SPY paper close submit and
  immediate read-only reconciliation, only if M354 is ready.
- M355 adds `paper-lab-spy-close-submit`, the explicit paper-only SPY cleanup
  close command. It consumes the ready M354 artifact, performs fresh read-only
  account, position, and open/all/closed SPY order observations, blocks
  duplicate `paper-order-close-m355_spy_paper_close_submit` evidence, and
  submits exactly one SPY equity sell `market`/`day` quantity order only when
  all gates pass.
- The M355 paper run wrote
  `runs/paper_lab/m355_spy_paper_close_submit.jsonl`, submitted exactly once
  with quantity `0.032905647`, and received broker status `accepted` for order
  `56a2f690-f4ad-4572-bcf4-1a479398fe55`. Immediate post-submit read-only
  observation found the SPY position still present at `0.032905647`, one open
  SPY sell order for the M355 client order id, no fill from the submit
  response, and final state `close_submit_accepted_pending_reconciliation`.
  M355 authorizes no retry, cancel, replace, liquidate, close-position endpoint
  usage, additional orders, live trading, or autonomous follow-up. The next
  milestone should be M356 read-only cleanup/revalidation.
- M363 records the operator review decision for the stale accepted M355 SPY
  paper close order. It reviews repo evidence only and performs no broker
  mutation, paper-profile command, direct SDK query, Alpaca UI corrective action,
  cancel, replace, retry, close-position endpoint, liquidation, second sell, or
  buy.
- M363 evidence treats M358, M359, M361, and M362 as the valid read-only chain:
  each observed the same open accepted unfilled SPY sell order matched by both
  `paper-order-close-m355_spy_paper_close_submit` and
  `56a2f690-f4ad-4572-bcf4-1a479398fe55`; SPY remained present at
  `0.032905647`; order status remained `accepted` /
  `OrderStatus.ACCEPTED`; order quantity remained `0.032905647`; filled
  quantity remained `0`; and filled timestamp remained blank. M360 is excluded
  as settlement evidence because it failed the profile gate. M362 is the latest
  valid diagnostic, had no unavailable observations or blockers, and estimated
  the accepted order age at about 11.9 hours from the
  `2026-06-01T21:49:57.297904+00:00` submitted timestamp.
- M363 inference: the M355 close order is stale enough to require an explicit
  operator decision before corrective action. The system must not
  autonomously cancel, replace, retry, liquidate, submit another close order, or
  mutate broker/account/portfolio state. Any corrective action must be a
  separate explicitly approved paper-only milestone.
- M363 operator options are: Option A keep waiting and run another read-only
  check later; Option B prepare a separate cancel-only preview/review milestone
  with no immediate cancel in M363; Option C prepare a separate
  cancel-and-replace design/preview milestone with no immediate cancel or
  replacement in M363; Option D perform manual Alpaca paper UI
  broker/account investigation, read-only first; and Option E stop paper-lab
  progression until the stale-order cause is understood.
- M363 recommends Option B as the next safest executable path: a separate
  paper-only cancel-readiness/preview milestone for the stale accepted close
  order. That next milestone still must not cancel unless it is explicitly
  scoped as a cancel-submit milestone with hard operator confirmation.
- M363 hard gate: any future cancel, replace, retry, close-position, or
  liquidation action requires a new separate milestone. Any future
  cancel-submit milestone must first run a fresh read-only snapshot and verify
  paper profile ready, SPY position still present, exactly one matching open
  stale M355 sell order, no other conflicting open SPY orders, no filled or
  terminal state since M362, normal shell credential-free before and after, and
  no live profile or live endpoint.
- M364 corrects the repo-hygiene and no-mutation invariant gate before any
  M365 work. It adds `.gitattributes` with LF as the text default and CRLF for
  PowerShell scripts. The pre-work short status and CR-at-EOL ignored diff were
  empty, so no functional dirty diff was restored or hidden inside line-ending
  cleanup.
- M364 adds `tests/unit/test_broker_mutation_surface_invariant.py`, an offline
  credential-free AST and runtime public-surface test over the Alpaca SDK
  wrapper, adapter, broker, client protocol, and base broker protocol. It fails
  on cancel, cancel-order, replace, replace-order, close-position,
  close-all-positions, liquidate, liquidation, or delete names in checked
  modules, classes, protocols, methods, properties, assignments, or annotated
  assignments. The current intentional broker mutation boundary remains the
  existing `submit_order` path only; those forbidden mutation surfaces require a
  future explicit operator-approved milestone plus a deliberate safety-test
  update.
- M364 records that the M355 SPY paper sell-to-close was an after-hours equity
  `market`/`day` order submitted after the June 1 regular session close.
  Existing observations prove only accepted/unfilled overnight and pre-session
  state, not accepted status after a complete regular session following
  submission. The M364 post-session read-only diagnostic remains pending unless
  the operator enters a scoped transient paper shell and runs only the existing
  read-only snapshot path with run id `m364_post_session_diagnostic` and run
  log `runs/paper_lab/m364_post_session_diagnostic.jsonl`.
- M365 cancel-readiness remains blocked until the M364 post-session read-only
  diagnostic is complete and the no-mutation invariant passes. M364 preserves
  `paper_lab_only`, `not_live_authorized`, and `profit_claim=none`; it performs
  no submit, cancel, replace, close-position, liquidation, delete,
  broker/network command, credential printing, live trading, autonomous
  scheduling, or LLM/agent trading-path behavior.
- M364C adds an offline-only
  `algotrader.execution.paper_lab_snapshot_classifier` helper for interpreting
  already-produced paper-lab snapshot records. It classifies target-order
  records as `terminal_filled`, `terminal_canceled_or_expired`,
  `still_open_or_accepted_after_full_session`, or
  `ambiguous_or_incomplete` using only snapshot content: target-order matching,
  status, filled quantity/timestamp, positions/orders availability, query
  metadata, `mutated=false`, and `submitted=false`.
- M364C is pure local interpretation code. It imports no Alpaca SDK, broker
  clients, network modules, subprocess path, credential/config loader, CLI, or
  execution mutation module, and it does not submit, cancel, replace,
  close-position, liquidate, delete, print credentials, call a broker, authorize
  live trading, or enter the trading hot path. Labels remain `paper_lab_only`,
  `offline_only`, `not_live_authorized`, and `profit_claim=none`.
- M364C does not replace M364B. The M364B broker-facing read-only
  post-session snapshot remains required after the June 2, 2026 regular-session
  close, and M365 remains blocked until M364B produces complete post-session
  evidence and the M364 no-mutation invariant remains passing.
- M364B-1 ran exactly one intraday read-only paper snapshot during the
  June 2, 2026 regular session with run id
  `m364b1_intraday_spy_close_snapshot` and ignored local run log
  `runs/paper_lab/m364b1_intraday_spy_close_snapshot.jsonl`. The paper profile
  gate passed; account, orders, and positions observations were complete; safe
  account cash/currency evidence was `1999.81` USD; positions reported
  `position_count=0`, no position symbols, and no SPY position; the recent
  open-order query metadata was complete with `status_filter=open`; and the
  returned recent open-order count was `0`.
- M364B-1 preserved `mutated=false`, `submitted=false`, and
  `redaction=credentials_redacted`. The M355 broker order id
  `56a2f690-f4ad-4572-bcf4-1a479398fe55` and client order id
  `paper-order-close-m355_spy_paper_close_submit` were not present in the
  returned open-order set, so target order status, submitted timestamp, filled
  quantity, filled timestamp, time in force, side, and type were not captured.
  The offline M364C classifier returned `ambiguous_or_incomplete` with reason
  `target_order_not_found`, `metadata_complete=true`,
  `target_order_found=false`, and `target_position_found=false`. The SPY
  position is absent/zero in this snapshot, but M355 terminal state is not
  proven. M365 remains blocked, and M364B-2 post-close read-only evidence is
  still required. Labels: `paper_lab_only`, `read_only`,
  `not_live_authorized`, `profit_claim=none`.
- M364B-1A ran a targeted read-only M355 order-history diagnostic with run id
  `m364b1a_m355_target_order_history` and ignored local run log
  `runs/paper_lab/m364b1a_m355_target_order_history.jsonl`. It used a scoped
  transient paper shell, local env helper credential loading, and the existing
  read-only broker order-history query surface for SPY `open`, `all`, and
  `closed` scopes. No source, test, CLI, adapter, SDK wrapper, policy,
  credential/config, submit, cancel, replace, close-position, liquidation,
  retry, delete, or live-trading behavior changed.
- M364B-1A found M355 absent from `open` orders but present in both `all` and
  `closed` history. The target broker order id
  `56a2f690-f4ad-4572-bcf4-1a479398fe55` and client order id
  `paper-order-close-m355_spy_paper_close_submit` matched a SPY `sell`
  `market`/`day` order for quantity `0.032905647`, created at
  `2026-06-01T21:49:57.297904+00:00`, broker `submitted_at`
  `2026-06-02T13:23:01.929464+00:00`, `filled_at`
  `2026-06-02T13:30:00.744662+00:00`, `filled_quantity=0.032905647`,
  `filled_average_price=757.16`, and status `filled` / `OrderStatus.FILLED`.
  Account, positions, and order-history observations were available; query
  metadata was complete; `mutated=false`; `submitted=false`;
  `broker_action_performed=false`; and `close_order_submitted=false`.
- The M364C classifier returned `terminal_filled` with reason
  `filled_order_with_complete_metadata`. SPY position classification is
  absent/zero with `position_count=0`. M365 cancel-readiness is not needed for
  M355 because the target order is terminal filled and no target open order
  remains to cancel. Labels: `paper_lab_only`, `read_only`,
  `not_live_authorized`, `profit_claim=none`.
- M365 closes the M355 stale-order investigation as a filled-close
  reconciliation and paper-lab reset review. Existing M364B-1A evidence shows
  the target SPY sell-to-close order filled at the next regular-session open
  on June 2, 2026, with `filled_at`
  `2026-06-02T13:30:00.744662+00:00` and filled quantity `0.032905647`; SPY
  paper position remains absent/zero; and the target order is absent from open
  history.
- M365 retires the prior M365 cancel-readiness path for M355 because there is
  no open M355 order left to cancel. It adds no order mutation capability and
  performs no submit, cancel, replace, close-position, liquidation, retry,
  delete, broker/network command, credential printing, live trading,
  autonomous scheduling, or LLM/agent trading-path behavior. The M364
  no-mutation invariant remains active.
- The next safe paper-lab direction is a new operator-reviewed paper
  experiment path, not cleanup, cancel-readiness, or cancel tooling.
- M366 starts that next paper-lab cycle with one fresh read-only paper snapshot
  after the M355 filled-close reconciliation. The run id is
  `m366_fresh_paper_lab_reset_snapshot`, and the ignored local run log is
  `runs/paper_lab/m366_fresh_paper_lab_reset_snapshot.jsonl`.
- M366 used the existing `paper-lab-snapshot` command only. Account, positions,
  and recent open orders were all observed; no observations were unavailable;
  cash/currency were safely reported as `1999.81` USD; buying power was not
  exposed by the existing snapshot payload; `position_count=0`;
  `position_symbols=[]`; no SPY position was present; no non-SPY positions were
  present; and `recent_order_count=0` with complete open-order query metadata.
- The M366 reset classification is `paper_lab_flat_clean`. The snapshot
  preserved `mutated=false`, `submitted=false`, and
  `redaction=credentials_redacted`. M366 remains `paper_lab_only`,
  `read_only`, `not_live_authorized`, and `profit_claim=none`; it performed no
  submit, cancel, replace, close-position call, liquidation, retry, delete,
  broker mutation, live trading, autonomous scheduling, or LLM/agent
  trading-path behavior.
- The paper lab is ready only for a separate M367 offline/operator-reviewed SPY
  ETF/SMA next-experiment preview packet. M366 does not authorize a
  broker-facing order preview or any new paper order.
- M367 adds `algotrader.research.etf_sma_next_experiment_review` as a pure
  offline SPY ETF/SMA next-experiment review packet using only explicit caller
  inputs. The contract records the M366 source evidence id
  `m366_fresh_paper_lab_reset_snapshot`, reset classification, optional
  cash/currency evidence, position and open-order counts, SPY/equity scope,
  SPY-only allowlist, offline signal status, target cap, safety labels,
  blockers, required next milestone, whether a separate broker-facing preview
  milestone is allowed, and `submit_authorized=false`.
- M367 decisions are `ready_for_separate_broker_preview_milestone`,
  `blocked_reset_not_clean`, `blocked_symbol_not_allowed`,
  `blocked_cap_invalid`, `blocked_signal_not_actionable`, and
  `operator_review_required`. Readiness requires `paper_lab_flat_clean`, zero
  positions, zero open orders, `symbol=SPY`, `asset_class=equity`, allowlist
  exactly `("SPY",)`, positive cap no greater than USD 25.00, default M367
  safety labels, and an actionable offline ETF/SMA risk-on status. Risk-off,
  insufficient-history, missing, stale, or otherwise non-actionable signal
  status blocks offline.
- M367 remains `paper_lab_only`, `offline_only`, `research_only`,
  `not_live_authorized`, and `profit_claim=none`. It imports no broker, Alpaca
  SDK, network, credential, runtime trading, orchestration, execution,
  portfolio, risk, screener, or signal module. It performs no submit, cancel,
  replace, close-position call, liquidation, retry, delete, broker/network
  command, credential printing, live trading, autonomous scheduling, or
  LLM/agent trading-path behavior.
- If M367 is ready, the only recommended next path is
  `M368 - SPY ETF/SMA broker-facing preview-only milestone`; M367 does not
  authorize that broker-facing preview itself and never authorizes a paper
  order. If M367 is blocked, resolve the blocker offline before any
  paper-facing work.
- M368A adds
  `algotrader.research.etf_sma_next_experiment_review_artifact` as a pure
  offline JSONL materialization layer for the M367 review. It uses explicit
  M366-style reset evidence and explicit offline SPY ETF/SMA signal evidence,
  imports no broker, Alpaca SDK, network, credential, runtime trading,
  orchestration, execution, portfolio, risk, screener, or signal module, and
  writes only a caller-specified local JSONL artifact.
- The local ignored M368A run log is
  `runs/paper_lab/m368a_offline_spy_etf_sma_next_experiment_review.jsonl`.
  It records run id `m368a_offline_spy_etf_sma_next_experiment_review`,
  evidence ids `m366_fresh_paper_lab_reset_snapshot` and
  `m368a_offline_spy_etf_sma_fixture_signal`, SPY/equity scope, cap `25.00`,
  default M367 labels, reset classification `paper_lab_flat_clean`,
  cash/currency `1999.81` USD, zero positions, zero recent/open orders, SPY
  absent/zero, `mutated=false`, and `submitted=false`.
- The offline signal evidence in M368A is deterministic fixture evidence, not
  live market data and not profitability evidence. It records
  `status=bullish_risk_on`, `as_of=2025-07-20T00:00:00+00:00`, SMA50
  available at `20`, SMA200 available at `12.5`, `usable_bar_count=200`,
  `ignored_future_bar_count=0`, and `actionable_risk_on=true`.
- M368A answers the offline eligibility question as
  `ready_for_separate_broker_preview_milestone` with no blockers and required
  next milestone `M368 - SPY ETF/SMA broker-facing preview-only milestone`.
  `separate_preview_milestone_required=true`,
  `separate_broker_preview_milestone_allowed=true`,
  `submit_authorized=false`, `broker_action_performed=false`,
  `broker_preview_performed=false`, `mutated=false`, and `submitted=false`.
  It performs no broker preview, submit, cancel, replace, close-position call,
  liquidation, retry, delete, broker/network command, credential printing, live
  trading, autonomous scheduling, or LLM/agent trading-path behavior.
- M368 adds `algotrader.execution.etf_sma_paper_preview` and the
  `etf-sma-m368-broker-preview-only` CLI command as a local SPY ETF/SMA
  broker-facing preview-only milestone. It reads local M368A ready-review JSONL
  evidence and explicit flat/clean paper snapshot evidence, then renders only a
  deterministic possible future SPY paper buy shape: SPY/equity, buy,
  market/day, notional cap `25.00`, allowlist `["SPY"]`, and labels
  `paper_lab_only`, `preview_only`, `not_live_authorized`, and
  `profit_claim=none`.
- M368 ready output records
  `decision=ready_for_operator_review_before_tiny_spy_paper_submit` and
  `required_next_milestone=M369 - Explicit operator review for tiny SPY paper
  submit`. It always records `submit_authorized=false`, `submitted=false`,
  `mutated=false`, `broker_action_performed=false`, and
  `broker_preview_performed=false`; source or snapshot gaps block before a
  preview payload is rendered.
- M368B supplies the fresh read-only paper snapshot evidence for M368. The
  snapshot artifact is
  `runs/paper_lab/m368b_fresh_read_only_paper_snapshot.jsonl`, and the
  refreshed preview artifact is
  `runs/paper_lab/m368b_spy_etf_sma_broker_preview_only.jsonl`. The refreshed
  preview remains preview-only and requires
  `M369 - Explicit operator review for tiny SPY paper submit` before any
  submit.
- M369 adds the explicit offline operator-review artifact for the tiny SPY
  paper submit path in
  `algotrader.execution.etf_sma_m369_operator_review`. It consumes only the
  local M368B preview and fresh read-only snapshot JSONL evidence, verifies the
  M368A linkage, flat/clean snapshot, SPY/equity buy market/day shape, notional
  cap `25.00`, zero positions, zero open/recent orders, and non-mutating flags,
  and writes the ignored local artifact
  `runs/paper_lab/m369_tiny_spy_paper_submit_operator_review.jsonl`.
- M369 ready output records
  `decision=ready_for_separate_tiny_spy_paper_submit_milestone`,
  `required_next_milestone=M370 - Tiny SPY paper submit only after explicit
  operator approval`, `operator_review_ready=true`,
  `separate_submit_milestone_required=true`, `submit_authorized=false`,
  `submitted=false`, and `mutated=false`. It is `paper_lab_only`,
  `operator_review_only`, `not_live_authorized`, and `profit_claim=none`; it
  performs no submit, broker preview, cancel, replace, close, liquidation,
  retry, delete, live profile, live trading, broker mutation, autonomous
  scheduling, LLM/agent trading-path behavior, credential access, or network
  call. M368A signal evidence remains deterministic fixture evidence only, not
  live market data or profitability/live-authorization evidence. Missing,
  malformed, ambiguous, stale, blocked, non-SPY, over-cap, positioned,
  open-order, submitted, or mutated M368B evidence fails closed.
- The local ignored M368 artifact path is
  `runs/paper_lab/m368_spy_etf_sma_broker_preview_only.jsonl`. M368 adds no
  submit, cancel, replace, close-position call, liquidation, retry, delete,
  live profile, live trading, broker mutation, autonomous scheduling,
  LLM/agent trading path, credential leakage, or normal-test network
  dependency.
- M371 adds `algotrader.execution.paper_order_lifecycle_replay` as a pure
  deterministic offline replay harness for local paper-order lifecycle events.
  It consumes caller-supplied `PaperOrderLifecycleEvent` observations in source
  order, preserves those observations in the result, and classifies
  `not_seen`, `submitted_seen`, `accepted_open_unfilled`,
  `partially_filled_open`, `filled_terminal`, `rejected_terminal`,
  `canceled_terminal`, `ambiguous_after_submit`, and
  `inconsistent_lifecycle`.
- The M371 replay harness covers the M355-style path of submit observed,
  accepted/open/unfilled across one or more read-only snapshots, and later
  filled terminal. It also blocks missing client-order IDs, unknown statuses,
  broker-order ID conflicts, filled-quantity decreases, active/open regressions
  after terminal states, and contradictory filled-quantity/status metadata.
- M371 is capability-only, offline-only, and credential-free. It performs no
  broker calls, Alpaca SDK calls, credential loading, paper/live order
  submission, cancel, replace, close-position call, liquidation, retry, delete,
  broker mutation, network command, live trading, autonomous scheduling, or
  LLM/agent trading-path behavior. It does not expand `Broker` or
  `LocalBroker`; the submit-only broker mutation invariant remains intact.
  Ambiguous submit exception evidence blocks repeat submission until later
  read-only order evidence resolves it. The harness makes no profitability,
  execution-quality, or live-readiness claim. M370B remains a separate pending
  ACTION leaf requiring regular equity-session conditions and explicit operator
  approval.
- M372 hardens the existing M370 tiny SPY paper-submit gate with deterministic
  freshness checks only. The gate now requires an explicit evaluation clock,
  timezone-aware market-session `observed_at` evidence no older than 15 minutes
  by default, no materially future-dated session evidence beyond a 60-second
  default tolerance, and timezone-aware pre-submit broker snapshot
  `observed_at` evidence no older than 5 minutes by default. Missing, invalid,
  timezone-naive, stale, or future-dated freshness evidence fails closed with
  deterministic blockers; evaluation-clock and market-session failures stop
  before broker construction, and pre-submit snapshot failures stop before
  submit. Operator text now displays `evaluated_at`, market-session
  `observed_at`, and pre-submit snapshot `observed_at` in UTC-normalized form.
  M372 does not authorize broker submit, does not add an operating brief
  generator, and adds no Alpaca SDK call, credential loading, network access,
  retry, cancel, replace, close, liquidation, delete, or broker protocol
  expansion. M370B remains the separate pending regular-session ACTION leaf.
- M370B attempted the regular-session tiny SPY paper-submit action in a scoped
  paper shell during an Alpaca paper clock-open window. A fresh read-only
  paper-lab snapshot first observed USD cash `1999.8`, zero positions, zero
  open orders, complete order-query metadata, `mutated=false`, and
  `submitted=false` in
  `runs/paper_lab/m370b_pre_submit_read_only_snapshot.jsonl`. The installed
  `etf-sma-m370-paper-submit` command then wrote
  `runs/paper_lab/m370b_regular_session_tiny_spy_paper_submit.jsonl` and
  failed closed before broker construction with blockers
  `market_session_gate_failed` and `evaluation_clock_missing`; the command
  surface does not expose the explicit evaluation clock required by M372. No
  M370 broker submit was attempted: `ok=false`, `submitted=false`,
  `mutated=false`, and `submit_call_count=0`.
- M373 repairs that command surface offline. `etf-sma-m370-paper-submit` now
  exposes `--evaluated-at` and passes the supplied timezone-aware ISO-8601
  evaluation clock into the M370 paper-submit gate. Missing, invalid, or
  timezone-naive evaluation clocks still fail closed before broker construction.
  When the broker snapshot path is reached, the pre-submit snapshot
  `observed_at` is captured by the command-owned snapshot clock, validated by
  the existing freshness rules, and rendered in JSON and operator text
  alongside `evaluated_at` and market-session `observed_at`. Legacy explicit
  pre-submit timestamp evidence, when supplied, is validated as additional
  evidence but cannot override the command-owned snapshot timestamp. The
  existing market-session and pre-submit snapshot stale, future-dated, invalid,
  and timezone-naive protections remain fail-closed. M373 authorizes no paper
  submit rerun and adds no live trading, retry, cancel, replace, close,
  liquidation, delete, scheduler, operating brief generator, credential
  printing, or network requirement to normal pytest.
- M370C reattempted the regular-session tiny SPY paper-submit action on
  June 3, 2026 in a scoped paper shell. Alpaca paper clock evidence was
  recorded in `runs/paper_lab/m370c_alpaca_paper_clock.jsonl` with
  `is_open=true`, no clock blockers, observed timestamp evidence around
  `2026-06-03T14:35Z`, and next close at `2026-06-03T20:00:00Z`. A fresh
  read-only snapshot in
  `runs/paper_lab/m370c_pre_submit_read_only_snapshot.jsonl` observed account,
  positions, and open-order metadata successfully, with zero positions, zero
  recent open orders, complete recent-order query metadata, `submitted=false`,
  and `mutated=false`. The installed `etf-sma-m370-paper-submit` command was
  invoked once with explicit `--evaluated-at`, wrote
  `runs/paper_lab/m370c_regular_session_tiny_spy_paper_submit.jsonl`, and
  failed closed before broker construction because the wrapper passed
  market-session `observed_at` as a locale PowerShell timestamp without
  timezone information. The result is `ok=false`, `submitted=false`,
  `mutated=false`, `submit_call_count=0`, with blockers
  `market_session_gate_failed` and `market_session_observed_at_invalid`. No
  M370 broker submit was attempted, and there was no retry, cancel, replace,
  close, liquidation, delete, live profile, credential printing, scheduler, or
  trading hot-path change.
- M375 adds `etf-sma-m375-spy-close-preview`, a broker-facing preview-only
  readiness gate for the expected M370C SPY paper position. It requires the
  paper profile, performs read-only account, positions, and account-wide open
  order observations through the existing Alpaca paper boundary, and writes
  `runs/paper_lab/m375_spy_position_close_preview.jsonl`. The artifact records
  `milestone=M375`, paper-lab/not-live/profit-none/close-preview-only labels,
  `submitted=false`, `mutated=false`, `submit_authorized=false`,
  `close_submit_authorized=false`, `broker_mutation_authorized=false`, the
  expected M370C quantity `0.033172072`, observed SPY quantity and average
  entry price when available, non-SPY/open-order flags, order-query metadata
  completeness, and a readiness classification. A ready record previews only
  the later M376 SPY sell intent for quantity `0.033172072`; M375 submits
  nothing. In this local Codex run no Alpaca paper credentials were loaded, so
  the scoped command wrote `blocked_profile_gate_failed` before broker
  construction. No fresh broker observation, submit, cancel, replace, close,
  liquidation, delete, retry, scheduler, live profile, credential printing, or
  trading hot-path behavior occurred.
- M376A repairs the existing `paper-lab-spy-close-submit` command offline for
  the fresh M375C close-preview evidence. The stale default bug was that the
  command still loaded M354 evidence fields and built the M355 close request:
  client order id `paper-order-close-m355_spy_paper_close_submit` and quantity
  `0.032905647`. The repaired path accepts
  `--close-preview-run-log runs/paper_lab/m375c_spy_position_close_preview_fresh_paper.jsonl`
  with `--run-id m376_spy_position_close_submit`, derives the SPY sell quantity
  `0.033172072` from the fresh preview record, and resolves the submit request
  client order id to `paper-order-close-m376_spy_paper_close_submit`. Missing
  `--submit` or `--i-mean-it`, stale M354 evidence, submitted/mutated/live or
  not-ready preview evidence, profile/halt failures, open orders, duplicates,
  unavailable observations, or quantity-over-position conditions still fail
  closed before broker construction. The SPY quantity close does not use the
  entry notional-cap gate. Verification for M376A passed
  `python -m pytest tests/unit/test_paper_lab_cli_smoke.py`,
  `python -m pytest tests/unit/test_dependency_direction.py`,
  `python -m pytest tests/unit/test_broker_mutation_surface_invariant.py`,
  `python -m pytest tests/unit/test_default_pytest_network_guard.py`, and
  `python -m pytest` with normal pytest remaining offline and credential-free.
  No real broker submit happened during M376A.
- Velocity Slice 1 adds `etf-sma-cycle-preview`, the smallest SPY ETF/SMA
  daily paper-lab operating-loop preview. The command evaluates caller-supplied
  daily SPY bars, reads paper account/position/open-SPY-order observations only
  after the paper profile gate passes, and appends one JSONL preview record to
  the requested run log. The expected invocation is
  `algotrader etf-sma-cycle-preview --symbol SPY --run-log runs/paper_lab/spy_etf_sma_cycle_preview.jsonl --run-id spy_etf_sma_cycle_preview`,
  with optional `--bars-csv` or `--bars-jsonl`; absent bars default to
  `data/local/spy_daily_bars.csv` and evaluate as insufficient history. The
  artifact records `paper_lab_only`, `not_live_authorized`,
  `profit_claim=none`, `submitted=false`, `mutated=false`, and
  `broker_action_performed=false`; SMA posture/status; account observation
  availability and cash when observed; SPY quantity when observed; open-order
  count when observed; blockers; decision; and preview-only order fields only
  for `buy_preview` or `sell_preview`. Existing SPY paper position state is
  valid: bullish plus held SPY is `hold`, risk-off plus held SPY is
  `sell_preview`, risk-off plus no SPY is `hold`, and bullish plus no SPY is
  `buy_preview` using the small paper cap. An observed open SPY order,
  including the pending M376 order, is `decision=blocked` with
  `open_order_present` and no second order preview. Verification passed the
  focused cycle-preview test, dependency-direction test, broker mutation
  surface invariant, default pytest network guard, and full `python -m pytest`
  with normal pytest remaining offline and credential-free.
- M377A attempted the read-only SPY ETF/SMA cycle preview exactly once with
  `algotrader etf-sma-cycle-preview --symbol SPY --run-log runs/paper_lab/m377a_spy_etf_sma_cycle_preview_paper.jsonl --run-id m377a_spy_etf_sma_cycle_preview_paper`.
  Normal-shell masked preflight was credential-free, and the target JSONL did
  not already exist. The scoped local env loader populated Alpaca key booleans
  but did not set `APP_PROFILE=paper` or `ALPACA_PAPER_BASE_URL`, so the command
  wrote one blocked artifact before broker construction. The record has
  `sma_status=insufficient_history`, `sma_posture=insufficient_history`,
  `bars_source=data\local\spy_daily_bars.csv`, `bars_input_available=false`,
  `decision=blocked`, `decision_reason=paper_profile_required`, no account
  observation, no SPY position observation, no open-order observation, no M376
  order status observation, no `preview_order`, `submitted=false`,
  `mutated=false`, and `broker_action_performed=false`. No second preview was
  run, and no submit, cancel, replace, close, liquidation, delete, retry, live
  profile, credential printing, or broker mutation occurred. M377A is therefore
  safe but not a clean paper-profile broker observation.
- M377B corrected the scoped paper shell for the same read-only SPY ETF/SMA
  cycle preview by loading local credentials through `scripts/dev/load_env.ps1`,
  setting `APP_PROFILE=paper`, aliasing the loaded Alpaca secret into the
  repo's `ALPACA_SECRET_KEY` gate variable without printing it, and setting
  `ALPACA_PAPER_BASE_URL` to the paper endpoint. The command was run exactly
  once with
  `algotrader etf-sma-cycle-preview --symbol SPY --run-log runs/paper_lab/m377b_spy_etf_sma_cycle_preview_paper.jsonl --run-id m377b_spy_etf_sma_cycle_preview_paper`.
  The artifact records available account, position, and open-order
  observations; cash `1974.8`; SPY quantity `0.033172072`; one open SPY order;
  `sma_status=insufficient_history`; `sma_posture=insufficient_history`;
  `decision=blocked`; `decision_reason=open_order_present`;
  `blockers=["open_order_present"]`; no `preview_order`; and
  `submitted=false`, `mutated=false`, and `broker_action_performed=false`.
  The current cycle-preview artifact serializes open SPY order count/symbols
  rather than a client-order-id-specific M376 status, so M376 remains treated as
  open/not terminal from the visible open-SPY-order blocker. Normal shells
  before and after the scoped paper command remained credential-free. No second
  preview, submit, cancel, replace, close, liquidation, delete, retry, live
  profile, credential printing, market-data fetch, or broker mutation occurred.
- M378 adds `etf-sma-backtest`, an offline local-CSV SPY ETF/SMA backtest
  command that writes one deterministic JSONL artifact with posture history,
  equity curve, trades, and stats. The command is parameterized by symbol,
  bars CSV, run log, run id, initial cash, fast window, and slow window, and is
  dispatched before runtime config/profile loading. The contract computes SMA
  posture from bars available through as-of date T and models any target no
  earlier than the next input bar close. It starts flat, remains long-only,
  uses no leverage or shorting, records explicit zero commission/slippage
  assumptions, and preserves `submitted=false`, `mutated=false`,
  `broker_action_performed=false`, `live_authorized=false`, and
  `profit_claim=none`. Missing local CSV input writes a deterministic blocked
  artifact and performs no market-data fetch. No Alpaca SDK, broker, execution,
  paper profile, credentials, network, submit, cancel, replace, close,
  liquidation, retry, live path, or live-readiness/profitability claim is
  added.
- M379 adds `paper-order-reconcile`, a reusable read-only paper order
  reconciliation command for exact client-order-id plus broker-order-id
  lineage. The M376 invocation records the SPY close order request
  identifiers, expected side and quantity, paper/profile booleans, exact order
  source, observed status/fill fields, conservative terminal classification,
  SPY position and open-order context, blockers, and the next-submit decision
  into one deterministic JSONL record. Exact open/accepted evidence remains
  nonterminal and blocking; exact filled evidence is terminal and does not by
  itself block; missing, mismatched, unavailable, or conflicting evidence is
  conservative and blocking. The command uses only read-only account,
  position, and order observations, preserves `submitted=false`,
  `mutated=false`, `broker_action_performed=false`, `live_authorized=false`,
  and credential redaction, and adds no submit or broker mutation path. M379
  also extends `etf-sma-cycle-preview` artifacts with open-order client ids,
  broker ids, statuses, sides, quantities, and filled quantities so future
  open-order blockers have exact lineage.
- M382 adds the generic offline `etf-sma-cycle` command. It runs before runtime
  profile loading, reads only deterministic local inputs such as market-data
  CSV, explicit offline broker-state values, or an order-reconciliation JSONL
  artifact, and writes exactly one JSONL cycle record with ETF/SMA config and
  posture, allowlist result, paper-lab/signal-evaluation labels, broker/account
  state from offline inputs, blockers, next allowed/forbidden actions, and hard
  safety booleans: `submitted=false`, `mutated=false`,
  `broker_action_performed=false`, `broker_mutation_allowed=false`,
  `live_authorized=false`, `network_access_attempted=false`, and
  `credential_access_attempted=false`. The local M382 run
  `algotrader etf-sma-cycle --symbol SPY --run-id m382_etf_sma_cycle_offline --run-log runs/paper_lab/m382_etf_sma_cycle_offline.jsonl --order-reconciliation-log runs/paper_lab/m381_m376_spy_close_order_reconciliation.jsonl --format json`
  consumes the M381 reconciliation artifact and records
  `decision=blocked/open_order_present` with `m376_order_nonterminal` and
  `open_order_present` blockers. M376 remains nonterminal/open, so SPY submits
  stay forbidden until terminal read-only reconciliation.
- M383 reran the M376 SPY close-order reconciliation in a scoped paper shell
  with `python -m algotrader paper-order-reconcile --symbol SPY --client-order-id paper-order-close-m376_spy_paper_close_submit --broker-order-id dbb32dd3-58bf-49ea-b9b1-9aa44e85002d --expected-side sell --expected-qty 0.033172072 --run-log runs/paper_lab/m383_m376_spy_close_order_reconciliation.jsonl --run-id m383_m376_spy_close_order_reconciliation --format json`.
  Normal-shell booleans before and after the paper shell were clean, and the
  paper-shell checks printed booleans only. The fresh artifact contains one
  record: the exact M376 order is still found in open orders with
  `observed_status=accepted`, `terminal_state=nonterminal`,
  `reconciliation_decision=m376_nonterminal_open`, SPY position quantity
  `0.033172072`, one open SPY order, no non-SPY positions, and
  `submitted=false`, `mutated=false`, and `broker_action_performed=false`.
  The refreshed offline cycle command
  `python -m algotrader etf-sma-cycle --symbol SPY --run-id m383_etf_sma_cycle_after_reconciliation --run-log runs/paper_lab/m383_etf_sma_cycle_after_reconciliation.jsonl --order-reconciliation-log runs/paper_lab/m383_m376_spy_close_order_reconciliation.jsonl --format json`
  writes exactly one record with `decision=blocked/open_order_present`,
  blockers `m376_order_nonterminal` and `open_order_present`,
  `next_allowed_action=offline_work_or_read_only_reconciliation`,
  `spy_submit_until_m376_terminal` still forbidden, and all offline safety flags
  false for submit, mutation, broker action, network access, and credential
  access. No submit, cancel, replace, close, liquidation, delete, retry, live
  profile, credential printing, source change, or test change occurred.
- M384 adds `paper-lab-daily-preview`, an offline-only daily preview entrypoint
  for the SPY ETF/SMA paper lab. It runs before runtime config loading,
  requires an explicit local order-reconciliation JSONL path, writes exactly
  one replacing JSONL operator artifact, and reuses the offline `etf-sma-cycle`
  builder for the cycle decision. The M384 command shape is
  `python -m algotrader paper-lab-daily-preview --symbol SPY --run-id m384_paper_lab_daily_preview --run-log runs/paper_lab/m384_paper_lab_daily_preview.jsonl --order-reconciliation-log runs/paper_lab/m383_m376_spy_close_order_reconciliation.jsonl --format json`.
  Missing, malformed, ambiguous, or conflicting reconciliation input fails
  closed with `missing_or_invalid_order_reconciliation`; non-SPY position
  evidence fails closed with `unexpected_non_spy_position`. While M376 remains
  nonterminal/open, the preview reports `daily_preview_status=blocked`,
  `cycle_decision=blocked/open_order_present`, blockers
  `m376_order_nonterminal` and `open_order_present`,
  `next_allowed_action=offline_work_or_read_only_reconciliation`, and
  `spy_submit_until_m376_terminal` forbidden. The command preserves false
  safety flags for submit, mutation, broker action, broker mutation allowance,
  network access, credential access, and live authorization, and adds no Alpaca
  SDK import, socket/network path, credential access, broker construction,
  submit, cancel, replace, close, liquidation, delete, retry, live profile, or
  non-SPY action.
- small deterministic screener polish with synthetic inputs only
- a small config cleanup audit
- documentation polish
- explicit research artifact contracts/types before any runtime wiring
- first candidate research artifact review against the Phase 30 Step 2
  evidence standard and Phase 30 Step 3 template, docs-only, only after a
  candidate source package exists
- validated signal definition candidate review before any real evaluator
  implementation
- explicit future execution-planning policy decisions only after their config
  and result semantics are designed
- deeper broker contract tests around error paths and reconciliation boundaries
- further fake-only Alpaca contract coverage
- M351 separate tiny SPY paper probe scope, only if operator approves

Any future real SDK integration must be behind explicit opt-in safety gates,
paper-profile checks, credential redaction, skipped-by-default integration tests,
and no-network defaults for normal test runs.
