# Project Checkpoint

## Current Milestone

The project is at the 778-passed / 4-skipped deterministic core checkpoint. The
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
policy, no source-documentation verification sweep, no total-return versus
price-return comparison decision, no transaction cost/friction review, no
result-review template, no promotion/rejection decision, and no trading
implication or production threshold.

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
- docs-only source feasibility review for the Phase 33 selected broad-ETF
  moving-average candidate is now grouped in Phase 33 Step 3; the next
  docs-only gate should be a public-source documentation verification sweep
  while keeping the secondary shortlist and S05 backlog status non-approving
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

Any future real SDK integration must be behind explicit opt-in safety gates,
paper-profile checks, credential redaction, skipped-by-default integration tests,
and no-network defaults for normal test runs.
