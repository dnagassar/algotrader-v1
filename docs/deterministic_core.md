# Deterministic Trading Core

This project currently implements a small local trading core for deterministic
paper-trading experiments. The core takes explicit inputs and returns structured
results without reaching out to brokers, schedulers, model services, or external
state.

## Current Status

- `5156` tests are passing, with `4` skipped paper-integration tests by default.
- Phase 35 Step 1 adds a default pytest network kill-switch. Normal
  `python -m pytest` blocks `socket.socket` and `socket.create_connection`
  with a clear offline, credential-free failure message unless
  `--allow-network` or `ALGO_TRADER_ALLOW_NETWORK_TESTS=1` is explicitly used
  for gated integration tests.
- Phase 35 Step 2 adds a tiny synthetic-only return construction and lagged
  observation/action-date mechanics kernel. It covers arithmetic simple
  returns, close-to-close return tuple construction, and calendar-day lag
  examples only; it is not strategy logic, signal evaluation, backtesting,
  benchmark construction, or real-data approval.
- Phase 35 Step 3 adds a tiny research fixture manifest contract. It records
  fixture metadata and provenance for synthetic, derived, and local-only
  research fixtures without approving any source, data, universe, benchmark,
  cash proxy, validation result, profitability claim, or trading use.
- Phase 36 adds a deterministic synthetic-only as-of replay kernel. It records
  plain observation and availability dates, filters by availability as of a
  caller-provided plain date, preserves original ordering, and rejects malformed,
  duplicate, or unordered synthetic observation sequences without introducing
  backtesting, broker, runtime, portfolio, signal, or real-data behavior.
- Phase 37 adds metadata-only fixture manifest serialization. It round-trips
  `ResearchFixtureManifest` through deterministic JSON-compatible dictionaries,
  serializes plain dates as `YYYY-MM-DD` strings, restores tuple fields from
  lists as immutable tuples, and strictly rejects unknown fields, missing
  required fields, malformed dates, and unsafe normal-pytest eligibility without
  adding file I/O, vendor dependencies, ingestion, backtesting, broker/runtime,
  portfolio, signal/evaluator, or trading behavior.
- Phase 38 adds a tiny metadata-only synthetic replay snapshot package. It
  combines `ResearchFixtureManifest`, synthetic as-of availability filtering,
  and synthetic close-to-close Decimal return construction into immutable
  snapshot metadata without adding file I/O, persistence, real data, strategy
  logic, evaluator logic, broker/runtime behavior, portfolio mutation, order
  generation, backtesting, ML, LLM, or trading behavior.
- Phase 39 adds a tiny descriptive metrics layer for synthetic replay
  snapshots. It summarizes point counts, return counts, starting and ending
  values, cumulative simple return, and min/max/mean returns from existing
  snapshot metadata only, without adding benchmark comparison, strategy
  validation, backtesting, signal/evaluator behavior, broker/runtime behavior,
  portfolio mutation, order generation, real data handling, ML, LLM, or trading
  behavior.
- Phase 40 adds a tiny metadata-only synthetic research result package. It
  combines an existing `SyntheticReplaySnapshot` with its computed
  `SyntheticReplaySummary`, preserves snapshot identity, and serializes only
  nested primitive metadata without adding real data ingestion, benchmark
  comparison, backtesting, signal/evaluator behavior, broker/runtime behavior,
  portfolio mutation, order generation, ML, LLM, strategy validation, or
  trading behavior.
- A deterministic offline screener foundation ranks synthetic `Bar + Quote`
  inputs by ask momentum versus previous close, with optional deterministic
  `min_score` and `top_n` filters.
- A pure orchestration-owned Screener -> Signal input bridge preserves screener
  ordering, returns signal-ready `Bar + Quote` pairs, rejects duplicate screener
  result symbols and malformed result/candidate inputs, and preserves original
  `Bar` and `Quote` objects.
- Pure screener-ordered signal evaluation now applies the existing deterministic
  signal rule to ordered inputs only. Any signal output is not an approved trade
  and is not submitted.
- Screener-ordered signal evaluation contract tests now cover mixed
  signal/no-signal preservation, input non-mutation, immutable
  `ScreenerSignalEvaluation` results, and signal-rule exception propagation.
- Dependency-direction guardrails now enforce documented layering between
  screener, signals, risk, orchestration, and execution.
- Pure Signal -> Risk evaluation converts `ScreenerSignalEvaluation` rows into
  immutable `SignalRiskEvaluation` rows without execution or submission.
- Phase 15 documents the future Risk -> Execution boundary while keeping
  `risk_approved` as a permission signal only.
- Phase 16 Step 1 adds test-only Risk -> Execution dependency guardrails for
  pre-execution orchestration modules.
- Phase 16 Step 2 adds a pure risk-approved row selector that returns only
  `risk_approved` `SignalRiskEvaluation` rows while preserving order and object
  identity.
- Phase 17 Step 1 documents the future execution-intent boundary after
  risk-approved row selection.
- Phase 17 Step 2 adds a minimal internal `ExecutionIntent` contract and pure
  builder that wrap approved source rows by identity without submission.
- Phase 17 Step 3 hardens `ExecutionIntent` traceability with tests and docs
  only; the object remains source-only and pre-submission.
- Phase 18 Step 1 documents the future execution-planning boundary after
  `ExecutionIntent` construction before implementation.
- Phase 18 Step 2 adds a minimal immutable `ExecutionPlan` batch container and
  pure builder; no execution-planning policy or broker behavior has been added.
- Phase 18 Step 3 hardens `ExecutionPlan` traceability with tests and docs
  only; the object remains a minimal pre-broker batch container.
- Phase 19 Step 1 documents the future execution-planning policy boundary after
  minimal `ExecutionPlan` construction; no policy implementation or runtime
  behavior has been added.
- Phase 19 Step 2 adds a minimal immutable planning policy result contract and
  no-op pass-through policy; all intents are currently accepted and no real
  planning policy decisions have been added.
- Phase 19 Step 3 hardens `PlanningPolicyResult` traceability with tests and
  docs only; accepted and skipped traceability still flows through
  `ExecutionIntent.source_evaluation`.
- Phase 20 Step 1 documents the future max-intents planning policy boundary as
  a no-code design phase; no max-intents policy implementation or runtime
  behavior has been added.
- Phase 20 Step 2 adds the first real planning policy:
  `MaxAcceptedIntentsPolicyConfig`,
  `MAX_INTENTS_PER_PLAN_EXCEEDED_REASON`, and
  `apply_max_intents_execution_planning_policy(...)`.
- Phase 20 Step 3 hardens max-intents traceability with tests and docs only;
  no production source or runtime behavior changed.
- Phase 21 Step 1 documents the research/validation boundary; research,
  backtesting, and LLM-assisted research workflows remain advisory until
  promoted through explicit deterministic contracts.
- Phase 21 Step 2 adds a minimal immutable, slotted validated research artifact
  metadata contract; it is evidence only and has no trading behavior.
- Phase 21 Step 3 hardens validated research artifact traceability and ordering
  guarantees with tests and docs only; no production source changed.
- Phase 22 Step 1 documents the future validated signal definition boundary;
  signal definitions remain promoted contracts, not execution decisions.
- Phase 22 Step 2 adds the minimal immutable, slotted
  `ValidatedSignalDefinition` metadata contract; it does not evaluate signals
  or create execution intents.
- Phase 22 Step 3 hardens validated signal definition traceability and tuple
  ordering with tests and docs only; no production source changed.
- Phase 23 Step 1 documents the future signal evaluation, clock, and as-of
  boundary; no production source or runtime behavior changed.
- Phase 23 Step 2 adds a minimal deterministic time contract with UTC-aware
  validation, an injectable `Clock` protocol, `FixedClock`, and an as-of helper.
- Phase 23 Step 3 hardens clock/timestamp traceability with tests and docs
  only; no production source changed.
- Phase 24 Step 1 documents the future `SignalEvaluationResult` boundary as
  advisory deterministic output only; no production source or runtime behavior
  changed.
- Phase 24 Step 2 adds the minimal immutable, slotted
  `SignalEvaluationResult` metadata contract; it does not evaluate signals,
  create execution intents, or approve trades.
- Phase 24 Step 3 hardens `SignalEvaluationResult` traceability with tests and
  docs only; no production source or runtime behavior changed.
- Phase 25 Step 1 documents the future deterministic signal evaluator boundary
  only; no evaluator exists yet, signal evaluation remains advisory and
  pre-risk, and LLMs remain outside the trading hot path.
- Phase 25 Step 2 adds the minimal immutable
  `SignalEvaluationInputSnapshot` metadata/reference contract; it provides
  deterministic input traceability only and still adds no evaluator, signal
  computation, live data access, risk approval, execution behavior, broker
  behavior, runtime behavior, persistence, ML, or LLM trading-path logic.
- Phase 25 Step 3 hardens `SignalEvaluationInputSnapshot` traceability with
  tests and docs only; no production source or runtime behavior changed.
- Phase 26 Step 1 documents the future no-op signal evaluator boundary only;
  no evaluator implementation exists yet, evaluator outputs remain advisory
  and pre-risk, evaluator modules must not import broker, execution, risk,
  runtime, persistence, ML, or LLM modules, and LLMs remain outside the trading
  hot path.
- Phase 26 Step 2 reviews `SignalEvaluationResult` no-op readiness and
  concludes the existing metadata-only result contract is sufficient for a
  future minimal no-op evaluator; no no-op marker, result kind, evaluator kind,
  evaluator implementation, production behavior, or trading-path behavior was
  added.
- Phase 26 Step 3 adds the minimal frozen, slotted `NoOpSignalEvaluator`
  contract as the first evaluator-shaped code. It only constructs advisory
  `SignalEvaluationResult` metadata from explicit deterministic inputs and
  adds no real signal computation, scoring, ranking, direction, actionability,
  risk approval, execution behavior, broker behavior, runtime behavior,
  persistence, ML, or LLM trading-path logic.
- Phase 26 Step 4 hardens `NoOpSignalEvaluator` traceability tests and docs
  only. No production behavior was added; the evaluator remains deterministic,
  advisory-only, offline-safe, broker-isolated, and traceable without implying
  actionability.
- Phase 27 Step 1 documents the real signal evaluator admission boundary only.
  No real evaluator exists yet, and actual signal computation remains forbidden
  until explicit deterministic input-value contracts and admission criteria are
  implemented.
- Phase 27 Step 2 documents the future deterministic signal input-value
  boundary only. No input-value contract exists yet,
  `SignalEvaluationInputSnapshot` remains reference metadata only, and no real
  evaluator or signal computation exists yet.
- Phase 27 Step 3 adds the minimal immutable `SignalInputValue` contract for
  one explicit observed value with UTC-aware timestamp and source traceability.
  It adds no real evaluator, signal computation, feature computation, scoring,
  ranking, direction, actionability, risk approval, execution behavior, broker
  behavior, runtime behavior, persistence, ML, or LLM trading-path logic.
- Phase 27 Step 4 hardens `SignalInputValue` traceability with tests and docs
  only. No production behavior was added; the contract remains immutable,
  scalar-only, non-computational, and isolated from trading-path behavior.
- Phase 28 Step 1 documents the future signal input bundle boundary only.
  `SignalInputValue` remains a single observed-value contract, and no real
  evaluator or signal computation exists yet.
- Phase 28 Step 2 adds the minimal immutable `SignalInputBundle` contract. It
  groups explicit `SignalInputValue` objects for future evaluator use,
  preserves ordering and input value identity, rejects duplicate names, and
  rejects lookahead values where `observed_at > as_of`. It does not validate
  completeness against `SignalEvaluationInputSnapshot`, compute features or
  signals, score, rank, infer direction, recommend trades, approve risk, mutate
  execution plans, access live data, route to brokers, submit orders, use
  scheduler/runtime/persistence behavior, run ML, or use LLMs in the trading
  path.
- Phase 28 Step 3 hardens `SignalInputBundle` traceability with tests and docs
  only. No production behavior was added; the bundle remains an immutable
  grouping contract for explicit `SignalInputValue` objects and still does not
  validate completeness or interpret values.
- Phase 28 Step 4 documents the future completeness validation boundary between
  `SignalEvaluationInputSnapshot.required_input_names` and
  `SignalInputBundle.values`. At that step, no completeness validator existed;
  the bundle remained a grouping contract only, and no real evaluator or signal
  computation existed yet.
- Phase 28 Step 5 adds the minimal immutable
  `SignalInputBundleCompletenessResult` contract and pure
  `validate_signal_input_bundle_completeness(...)` function. Completeness
  validation remains separate from `SignalInputBundle` construction, compares
  required names with bundle value names only, reports missing and extra names
  deterministically, and still adds no real evaluator or signal computation.
- Phase 28 Step 6 hardens completeness validation traceability with tests and
  docs only. No production behavior was added; completeness remains name-only,
  metadata-only, deterministic, non-mutating, separate from bundle
  construction, and isolated from trading-path behavior.
- Phase 29 Step 1 defines the first real evaluator design gate as a
  documentation-only boundary. No real evaluator exists yet, real signal
  computation remains forbidden until an evaluator-specific design satisfies
  the gate, the current explicit-input stack does not make outputs actionable,
  evaluator output remains advisory and pre-risk, and LLMs remain outside the
  trading hot path.
- Phase 29 Step 2 selects a first real evaluator candidate as documentation
  only: a minimal threshold-style advisory evaluator over one explicit scalar
  `SignalInputValue`. No real evaluator exists yet, real signal computation
  remains forbidden until evaluator-specific design and tests satisfy the gate,
  evaluator output remains advisory and pre-risk, and LLMs remain outside the
  trading hot path.
- Phase 29 Step 3 designs the selected first evaluator candidate contract as
  documentation only. The future threshold-style advisory evaluator candidate
  may consume one explicit scalar `SignalInputValue`, preferably `Decimal`, but
  no real evaluator exists yet, real signal computation remains forbidden until
  implementation is explicitly scoped, evaluator output remains advisory and
  pre-risk, and LLMs remain outside the trading hot path.
- Phase 29 Step 4 defines the first real evaluator test matrix only. No real
  evaluator exists yet, real signal computation remains forbidden until
  implementation is explicitly scoped, evaluator output remains advisory and
  pre-risk, and LLMs remain outside the trading hot path.
- Phase 29 Step 5 reviews first real evaluator implementation readiness only.
  No real evaluator exists yet, real signal computation remains forbidden
  unless explicitly scoped in a later implementation phase, evaluator output
  remains advisory and pre-risk, and LLMs remain outside the trading hot path.
- Phase 29 Step 6 designs threshold evaluator constants/output semantics only.
  No real evaluator exists yet, real signal computation remains forbidden
  unless explicitly scoped in a later implementation phase, evaluator output
  remains advisory and pre-risk, and LLMs remain outside the trading hot path.
- Phase 30 Step 1 defines the research support required before a real
  threshold-style evaluator may be implemented. No real evaluator exists yet,
  real signal computation remains forbidden, evaluator output remains advisory
  and pre-risk, and LLMs remain outside the trading hot path.
- Phase 30 Step 5 creates an unreviewed research candidate backlog only. No
  real evaluator exists yet, real signal computation remains forbidden,
  evaluator output remains advisory and pre-risk, and LLMs remain outside the
  trading hot path.
- Phase 30 Step 6 selects the first research candidate sourcing target only.
  No real evaluator exists yet, real signal computation remains forbidden,
  evaluator output remains advisory and pre-risk, and LLMs remain outside the
  trading hot path.
- Phase 31 Step 1 adds a reusable Codex operating context and resets the
  research-track workflow for shorter future prompts. Docs, research, and
  planning phases may now combine related documentation updates when low-risk
  and code-free; production-code phases remain narrow, test-first, explicitly
  scoped, and heavily verified.
- Phase 31 Step 2 adds a concise research-track next action plan. It keeps
  `P30-BL-001` as the first unreviewed sourcing target, confirms backlog
  entries are not evidence, allows research agents only as assistants, and
  keeps real evaluator implementation blocked.
- Phase 31 Step 3 normalizes the `P30-BL-001` source package. That step made
  the candidate source-package-ready only and did not validate, approve, or
  justify trading or threshold behavior.
- Phase 31 Step 4 formally reviews the Tier A `P30-BL-001` sources. Tier A
  conditionally supports mechanics and methodology only; `P30-BL-001` remains
  unvalidated, not approved, not production-ready, not implementation-ready,
  and not a trading, threshold, validated-signal-definition, or evaluator
  implementation justification.
- Phase 31 Step 5 routes the Tier A result through an evidence gap plan. It
  recommends a formal mechanics-only candidate artifact review summary and
  keeps production threshold, signal-definition, and evaluator implementation
  routes blocked.
- Phase 31 Step 6 records that formal mechanics-only candidate artifact review
  summary. It conditionally passes `P30-BL-001` for mechanics/methodology only
  and keeps validated artifact, signal-definition binding, production
  threshold, and evaluator implementation routes blocked.
- Phase 31 Step 7 records the final `P30-BL-001` disposition. It closes the
  candidate only in the mechanics-only sense, keeps it non-validated, not
  production-ready, and not implementation-ready, and routes the next research
  direction toward dataset-specific threshold or validation evidence without
  approving implementation.
- Phase 32 Step 1 selects dataset-specific threshold or validation evidence
  sourcing as the next research direction. `P30-BL-002` is the current backlog
  routing handle only if sourcing can produce a concrete evidence package; a
  better P0 replacement should be sourced first if it offers stronger
  traceable dataset-specific evidence.
- Phase 32 Step 2 defines the `P30-BL-002` source-package sourcing plan. It is
  documentation-only and sets required package fields, acceptable and
  unacceptable source material, minimum review-readiness criteria, and
  rejection/replacement triggers before formal review can begin. It does not
  collect sources, validate or approve `P30-BL-002`, create a research
  artifact or signal definition, or authorize implementation.
- Phase 32 Step 3 records the revised `P30-BL-002` source-package collection
  and normalization pass. It normalizes 23 candidate-only entries from the
  supplied Claude, Perplexity, and Gemini/browser scout reports, records
  preliminary routing categories and gaps, and remains unreviewed,
  unvalidated, unapproved, not promoted, and not implementation-ready.
- Phase 32 Step 4 records the `P30-BL-002` primary-source verification gate.
  It verifies selected source identities and intake eligibility for
  `P30-BL-002-S01`, `P30-BL-002-S03`, `P30-BL-002-S05`, and `P30-BL-002-S08`
  only. It does not formally review, approve, validate, promote, or implement
  any source.
- Phase 32 Step 5 records the `P30-BL-002` limited formal review intake plan.
  It defines review order, criteria, possible outcomes, and evidence
  requirements for selected sources only. It does not formally review, approve,
  validate, promote, or implement any source.
- Phase 32 Step 6 records the `P30-BL-002-S01` formal review. It passes S01
  only for limited negative-control/no-lookahead use, records unresolved exact
  timing, dataset, code/data, and deterministic-reproduction gaps, and routes
  next review to `P30-BL-002-S03`. It does not validate a signal, approve a
  threshold, create a validated artifact, create a validated signal definition,
  or authorize implementation.
- Phase 32 Step 7 records the `P30-BL-002-S03` formal review. It passes S03
  only for limited negative-control/data-snooping/OOS guardrail use, records
  unresolved exact rule tables, sample windows, OOS details, costs, bootstrap
  assumptions, and reproducibility gaps, and routes the next review to
  `P30-BL-002-S08` before candidate-evidence review. It does not validate a
  signal, approve a threshold, create a validated artifact, create a
  validated signal definition, or authorize implementation.
- Phase 32 Step 8 records the `P30-BL-002-S08` formal review. It passes S08
  only for methodology-only PIT review material, records proprietary/vendor,
  exact FQL, cutoff, access, and local replay gaps, and routes the next review
  to `P30-BL-002-S05` under PIT/no-lookahead, survivorship, and restatement
  expectations. It does not validate a signal, approve a threshold, create
  a validated artifact, create a validated signal definition, or authorize
  implementation.
- Phase 32 Step 9 records the `P30-BL-002-S05` formal review. It
  conditionally passes S05 only for limited candidate-evidence planning,
  records unresolved project-local reproduction, PIT/no-lookahead audit,
  roll/cost, OOS, multiple-testing, and implementation-approval gaps, and
  keeps all validation and implementation routes blocked. It does not validate
  a signal, approve a threshold, create a validated artifact, create a
  validated signal definition, or authorize implementation.
- Phase 32 Step 14 normalizes external S05 data-provider scout research as
  unverified routing input only. It records cautious candidate-source
  classifications and routes next work toward primary source/vendor
  verification without choosing a vendor, acquiring data, approving
  reproduction, validating S05, or authorizing implementation.
- Phase 32 Step 15 adds an S05 primary-verification questionnaire and manual
  outreach template. It defines questions and response-capture fields only; it
  does not contact vendors, select a source, acquire data, approve
  reproduction, validate S05, or authorize implementation.
- Phase 32 Step 16 adds an S05 public-documentation verification sweep. It
  separates primary documentation, secondary documentation, and inference;
  assigns cautious feasibility labels for AQR, CSI, Pinnacle, Norgate,
  Portara, TradeStation, institutional feeds, broker APIs, and public/proxy
  sources; and carries forward direct-confirmation gaps without selecting a
  provider, acquiring data, approving reproduction, validating S05, or
  authorizing implementation.
- Phase 32 Step 17 adds an S05 public-documentation-only feasibility decision.
  It records the owner decision to avoid vendor/source contact for now, keeps
  S05 only as a public-doc-supported proxy/partial planning candidate, and
  pauses exact reproduction, source selection, dataset approval, schema design,
  validation, and implementation unless future evidence or access changes.
- Phase 32 Step 18 adds an S05 non-exact proxy reproduction boundary. It
  defines proxy reproduction as a controlled approximation for methodology
  mechanics and research workflow testing only, not exact S05 reproduction,
  validation, implementation approval, or trading readiness.
- Phase 32 Step 19 adds an S05 proxy route selection boundary. It keeps
  multiple proxy routes under consideration for docs-only planning, selects no
  provider, dataset, schema, reproduction, validation, or implementation route,
  and recommends a route-neutral proxy dataset requirement boundary.
- Phase 32 Step 20 adds an S05 route-neutral proxy dataset requirements
  boundary. It defines minimum requirements for any possible future S05 proxy
  dataset without selecting a route, provider, dataset, schema, reproduction
  protocol, validation route, or implementation path.
- Phase 32 Step 21 adds an S05 proxy source shortlist and backlog routing
  decision. It records non-approving proxy source categories, keeps every
  category unselected, keeps S05 in backlog, and recommends evaluating an
  easier-data candidate next.
- Phase 33 Step 1 adds an easier-data research candidate selection boundary.
  It compares candidate families for docs-only source-review routing,
  shortlists broad-ETF moving-average trend-following, equity index
  momentum/trend-following using public index or ETF data, and
  volatility-targeting/risk-parity style allocation using public ETF/index
  data for further source review only, and keeps S05 in backlog.
- Phase 33 Step 2 adds a broad-ETF moving-average source package for source
  review preparation only. It records candidate-only scope, possible data
  source categories, source-quality requirements, docs-only review gates, and
  blockers without approving a universe, source, dataset, benchmark,
  reproduction, validation, implementation, or trading implication.
- Phase 33 Step 3 adds a grouped broad-ETF data feasibility, universe, and
  benchmark boundary. It compares candidate source categories, defines future
  ETF universe requirements, defines future benchmark/cash proxy requirements,
  and recommends a public-source documentation verification sweep without
  approving data, a universe, a benchmark, reproduction, validation,
  implementation, or trading implication.
- Phase 33 Step 4 adds a broad-ETF public-source documentation verification
  sweep. It separates primary documentation, secondary documentation, and
  inference; assigns cautious source-routing labels; and keeps all data,
  universe, benchmark, methodology, reproduction, validation, implementation,
  and trading-use approvals blocked.
- Phase 33 Step 5 adds a broad-ETF methodology and no-lookahead/as-of review
  boundary. It defines methodology-review scope, no-lookahead/as-of
  requirements, methodology evidence standards, required non-claims, and
  next-gate routing without approving methodology, parameters, data, a
  universe, benchmark, reproduction, validation, implementation, or trading
  use.
- Phase 33 Step 6 adds a grouped broad-ETF universe and benchmark/cash proxy
  shortlist boundary. It defines non-approving ETF universe principles,
  candidate buckets and examples, benchmark/cash proxy candidates, alignment
  requirements, rejection criteria, and next-gate routing without approving a
  universe, benchmark, cash proxy, source, methodology, reproduction,
  validation, implementation, or trading use.
- Phase 33 Step 7 adds a broad-ETF data-source terms/license review boundary.
  It reviews public terms, license, caching, private-repo, redistribution,
  derived-publication, API, and offline-use constraints for candidate source
  categories without approving a source, universe, benchmark, cash proxy,
  methodology, data acquisition, reproduction, validation, implementation, or
  trading use.
- Phase 33 Step 8 adds a broad-ETF final source shortlist decision boundary.
  It routes source categories as primary planning candidate,
  secondary/check candidate, metadata/context only, cash/risk-free proxy
  candidate, not default source, or unresolved / requires further review
  without approving a source, data, universe, benchmark, cash proxy,
  methodology, reproduction, validation, implementation, or trading use.
- Phase 34 Step 1 adds an external research integration boundary. It keeps
  Perplexity, Claude/Gemini, Codex, QuantConnect, vectorbt, notebooks,
  vendor/public data, external research, and ad hoc analysis as advisory
  research accelerators only, not trusted production dependencies or normal
  pytest/runtime inputs.
- Phase 34 Step 2 adds an external research artifact intake checklist. It
  defines how Perplexity reports, Claude/Gemini reviews, Codex implementation
  reports, QuantConnect results, vectorbt experiments, notebooks,
  vendor/public data docs, papers, spreadsheets, ad hoc analyses, screenshots,
  and manual observations are captured, labeled, reviewed, and routed before
  they can influence project decisions.
- Phase 34 Step 3 adds a notebook/prototype policy boundary. It defines how
  notebooks, ad hoc scripts, vectorbt prototypes, QuantConnect outputs,
  spreadsheets, CSV extracts, charts, external reports, and copied snippets may
  support exploratory research without becoming trusted artifacts, deterministic
  source of truth, production dependencies, normal pytest inputs, or
  trading-path behavior.
- A deterministic scenario harness exists for named local demo/test cases.
- The `demo-core` command can run selected named scenarios.
- `LocalBroker` is the working deterministic broker reference implementation in
  `src/algotrader/execution/local_broker.py`.
- Broker contract tests define expected broker behavior.
- `AlpacaPaperBroker` exists only as an inert future adapter skeleton.
- `InMemoryLedger` remains available for fast local event history.
- `JsonlLedger` adds optional append-only JSONL persistence.
- `LocalBroker` can use either ledger through the existing optional `ledger=`
  argument.
- Repo-wide AST import safety tests guard production code against broker SDK,
  network, and LLM imports.
- Duplicate order IDs are rejected before a second fill or ledger mutation can
  occur.
- Broker contract coverage now includes duplicate order-id idempotency.
- Short selling is not modeled end-to-end yet, so risk checks fail closed even
  if `RiskConfig.allow_short=True`.
- There are still no real broker API calls or external network dependencies.

## Current Deterministic Path

The offline screener path is separate from trading:

```text
Synthetic Bar + Quote candidates
  -> rank_by_ask_momentum(..., min_score=None, top_n=None)
  -> immutable AskMomentumResult tuple
  -> ordered_signal_inputs_from_screener(...)
  -> immutable signal-ready (Bar, Quote) tuple
  -> evaluate_signals_from_screener(...)
  -> immutable ScreenerSignalEvaluation tuple
  -> evaluate_risk_for_screener_signals(...)
  -> immutable SignalRiskEvaluation tuple
  -> select_risk_approved_evaluations(...)
  -> immutable risk-approved SignalRiskEvaluation tuple
  -> build_execution_intents_from_risk_approved(...)
  -> immutable ExecutionIntent tuple
  -> build_execution_plan(...)
  -> immutable ExecutionPlan
  -> apply_noop_execution_planning_policy(...)
  -> immutable PlanningPolicyResult
  -> future broker-facing execution request construction
  -> future broker adapter / execution layer
```

Phase 20 Step 2 adds the implemented max-intents policy at the same pre-broker
policy boundary as an alternate pure policy function:

```text
immutable ExecutionPlan
  -> apply_max_intents_execution_planning_policy(...)
  -> immutable PlanningPolicyResult
  -> future broker-facing execution request construction
  -> future broker adapter / execution layer
```

For compressed future prompts and research-track work, use
[`docs/agent_context/codex_operating_context.md`](agent_context/codex_operating_context.md)
as the first-read project summary. Its high-level planning pipeline is:

```text
Market Data -> Features -> Screener -> Signals -> Risk -> ExecutionIntent -> ExecutionPlan -> PlanningPolicy -> future OMS/Broker -> Fills/Portfolio/Reconciliation
```

The screener-to-signal segment does not call risk, broker, Alpaca, execution,
CLI, scheduler, ML, or LLM trading-path logic. Any `ProposedOrder` returned by
signal evaluation is a proposed signal output only. The Signal -> Risk layer
then checks proposed orders with `RiskEngine` only, keeps no-signal rows with
`risk=None`, and returns risk verdicts without executing or submitting anything.
Risk-approved means allowed by risk, not executed, submitted, or broker-ready.
The risk-approved selector keeps only those permission rows in order. Phase 17
Step 2 can wrap approved rows in internal `ExecutionIntent` objects, but those
intents remain pre-submission and broker-agnostic. They preserve the source
`SignalRiskEvaluation` by identity. Phase 17 Step 3 hardens that traceability:
the proposed order, risk verdict, and status are reachable through
`intent.source_evaluation.order`, `intent.source_evaluation.risk`, and
`intent.source_evaluation.status`, not through convenience fields on the
intent. Intents do not call brokers, route orders, submit orders, reserve batch
cash, resolve same-symbol conflicts, use schedulers, persist anything, mutate
portfolios, or add ML or LLM trading-path logic.
Phase 18 Step 1 documents the future execution-planning boundary after those
intents. Phase 18 Step 2 adds a minimal immutable `ExecutionPlan` batch
container for intents. The plan preserves intent order and identity only. It
does not call brokers, route orders, submit orders, reserve batch cash, resolve
same-symbol conflicts, generate idempotency keys or client order IDs, use
schedulers, persist anything, mutate portfolios, or add ML or LLM trading-path
logic.
Phase 18 Step 3 hardens that traceability: proposed orders, risk verdicts, and
statuses remain reachable through `plan.intents[n].source_evaluation.order`,
`plan.intents[n].source_evaluation.risk`, and
`plan.intents[n].source_evaluation.status`, not through convenience fields on
the plan.
Phase 19 Step 1 documents a future execution-planning policy boundary after
minimal plan construction and before broker-facing request construction. The
future policy may later make deterministic batch-level eligibility decisions,
but no policy has been implemented. `ExecutionPlan` remains a container, while
future planning policy remains the separate conceptual decision layer.
Phase 19 Step 2 adds only the first policy-result boundary:
`PlanningPolicyResult` and `SkippedExecutionIntent`, plus
`apply_noop_execution_planning_policy(...)`. The no-op policy accepts every
intent currently in the plan, preserves intent order and identity, preserves
source evaluation identity through accepted intents, and produces no skipped
intents. `skipped_intents` exists only as a future traceability shape.
Phase 19 Step 3 hardens that traceability. Accepted-intent traceability flows
through `result.accepted_intents[n].source_evaluation`. Skipped-intent
traceability flows through
`result.skipped_intents[n].intent.source_evaluation`. Proposed orders, risk
verdicts, and statuses remain reachable only through the source
`SignalRiskEvaluation` object. `PlanningPolicyResult` and
`SkippedExecutionIntent` do not expose direct broker, order, risk, status, fill,
idempotency, cash-reservation, priority, SDK, Alpaca, or persistence fields.
Phase 20 Step 1 documents a future max-intents planning policy as the first
real policy concept after minimal plan construction. Phase 20 Step 2 implements
that narrow policy. `apply_max_intents_execution_planning_policy(...)` accepts
the first `N` intents from an `ExecutionPlan`, skips later intents with the
deterministic reason `"max_intents_per_plan_exceeded"`, and preserves accepted
and skipped intent object identity. `MaxAcceptedIntentsPolicyConfig` requires an
explicit `int >= 1`; `bool` and `None` are rejected. The no-op policy remains
separate for no-cap pass-through behavior.
Phase 20 Step 3 keeps production source unchanged and hardens the traceability
contract with focused tests for accepted/skipped intent identity, accepted and
skipped ordering, deterministic skip reasons, source-evaluation reachability,
input plan non-mutation, and absence of forbidden broker/execution/planning
leakage fields.
The bridge also rejects duplicate screener result symbols and malformed
result/candidate inputs while preserving the original `Bar` and `Quote` objects.

The current trading path remains:

```text
Bar + Quote
  -> signal rule
  -> ProposedOrder or no signal
  -> RiskEngine.check()
  -> paper execution simulator
  -> portfolio update
  -> quote-based valuation
  -> structured result
```

## Current Local Safety Foundation

```text
offline screener ranking
  -> synthetic Bar + Quote inputs only
  -> pure orchestration input bridge
  -> signal-ready Bar + Quote pairs
  -> pure screener-ordered signal evaluation
  -> proposed signal outputs only, not approved or submitted trades
  -> no risk, broker, Alpaca, execution, CLI, scheduler, ML, or LLM
     trading-path logic

signal rule
  -> RiskEngine.check()
  -> LocalBroker
  -> paper simulator
  -> portfolio update
  -> quote-map valuation
  -> reconciliation
  -> InMemoryLedger or JsonlLedger
  -> broker contract tests
  -> inert AlpacaPaperBroker skeleton
```

## CLI-Facing Scenarios

These scenarios are exposed through the `demo-core` CLI command and use fixed
sample inputs.

- `approved_and_filled`: proves a valid signal can produce an order, pass risk,
  fill in the paper simulator, update portfolio state, and produce valuation.
- `rejected_insufficient_cash`: proves a generated order can be stopped by risk
  before execution when cash is not sufficient.
- `no_signal`: proves the signal layer can return no order and exit cleanly.
- `unfilled_limit_order`: proves a limit order can pass risk but remain open
  when it is not marketable, leaving portfolio state unchanged.

Run them with:

```powershell
python -m algotrader demo-core --scenario approved_and_filled
python -m algotrader demo-core --scenario rejected_insufficient_cash
python -m algotrader demo-core --scenario no_signal
python -m algotrader demo-core --scenario unfilled_limit_order
```

## Internal Broker Scenarios

These scenarios are internal harness cases. They are separate from the
CLI-facing scenario list.

- `broker_approved_and_filled`: proves an approved order can be submitted to
  `LocalBroker`, filled by the paper simulator, and reflected in local portfolio
  state.
- `broker_rejected_insufficient_cash`: proves an order rejected by
  `RiskEngine.check()` is not submitted to the broker.
- `broker_unfilled_limit_order`: proves an approved but non-marketable limit
  order can be submitted to `LocalBroker` without mutating cash or positions.

## Broker Boundary

`LocalBroker` is an in-memory deterministic reference broker. It prepares the
shape of a future broker adapter while keeping the current project fully local
and deterministic.

- `LocalBroker` requires an approved `RiskVerdict` by default.
- It uses the existing paper execution simulator internally.
- It mutates local `PortfolioState` only when a fill occurs.
- It rejects duplicate order IDs without applying another fill or recording
  another ledger event.
- It returns structured `BrokerOrderResult` values.
- It does not call Alpaca or any external API.
- It does not require credentials.

`AlpacaPaperBroker` is not operational yet and must not be used for trading. It
currently defines `submit_order(...)`, `get_account()`, and `get_positions()`,
but each method raises `BrokerNotImplementedError`. A future implementation must
satisfy the broker contract tests before it enters the trading path.

## Broker Contract Tests

Broker contract tests live at:

```text
tests/contracts/test_broker_contract.py
```

The contract currently verifies that a broker exposes account and position
reads, refuses missing or rejected risk approval, accepts approved orders, fills
marketable orders through the local paper behavior, leaves cash and positions
unchanged for unfilled limits, returns `BrokerOrderResult`, and preserves
deterministic supplied order IDs. It also verifies that duplicate order IDs are
rejected with `duplicate_order_id` before a second fill or ledger mutation can
occur.

## Short Selling

Short selling is intentionally not supported yet. `RiskConfig.allow_short`
remains a reserved configuration field for future work, but `RiskEngine`
currently rejects sell orders that exceed the held position even when
`allow_short=True`. This keeps risk and portfolio behavior aligned until short
positions, borrow rules, margin, valuation, and reconciliation are modeled
end-to-end.

## Local Reconciliation

The local reconciler compares expected `PortfolioState` with state reported by a
broker-like object such as `LocalBroker`.

It can detect:

- Cash mismatch
- Missing expected position
- Unexpected broker position
- Position quantity mismatch
- Optional valuation mismatch when quote data is supplied

This is a deterministic local comparison helper only. It is not an external
broker reconciliation loop.

## Deterministic Screener Foundation

The Phase 8 screener lives in:

```text
src/algotrader/screener/momentum.py
```

It ranks synthetic `Bar + Quote` candidates using ask momentum versus the
previous close:

```text
score = (quote.ask - previous_bar.close) / previous_bar.close
```

Results are immutable and returned as a tuple. Ordering is deterministic by
score descending and then symbol ascending. The screener is offline,
credential-free, API-free, broker-free, and deterministic.

Phase 9 adds optional deterministic polish filters. `min_score` keeps only
results with `score >= min_score`, and `top_n` limits the returned tuple after
ranking and score filtering. Defaults preserve Phase 8 behavior.

Phase 10 documents the future Screener -> Signals bridge as a design-only
orchestration boundary in
[`docs/design/phase10_screener_to_signals.md`](design/phase10_screener_to_signals.md).

Phase 11 begins that path with a pure orchestration-owned input bridge in:

```text
src/algotrader/orchestration/screener_signal_flow.py
```

`ordered_signal_inputs_from_screener(...)` accepts ranked `AskMomentumResult`
values plus the original `AskMomentumCandidate` values or a candidate lookup,
matches by symbol, rejects missing or duplicate candidate symbols with
`ValidationError`, and returns an immutable tuple of signal-ready `(Bar, Quote)`
pairs in the exact screener-result order.

Phase 11 Step 2 hardens the bridge by rejecting duplicate screener result
symbols, rejecting malformed result/candidate inputs, and preserving the
original `Bar` and `Quote` objects while returning immutable ordered pairs.

Phase 11 Step 3 adds pure screener-ordered signal evaluation through
`evaluate_signals_from_screener(...)`. It applies the existing deterministic
signal rule to the ordered `(Bar, Quote)` inputs and returns immutable
`ScreenerSignalEvaluation` values in exact screener order. Any `ProposedOrder`
is a proposed signal output only: it is not an approved trade and is not
submitted.

This bridge still does not call risk, call brokers, touch Alpaca, connect to
execution, CLI, scheduler, or runtime behavior, or add ML or LLM trading-path
logic.

Phase 12 documents the future Signal -> Risk boundary as a design-only
orchestration contract in
[`docs/design/phase12_signal_to_risk.md`](design/phase12_signal_to_risk.md).
It does not implement risk integration, approve orders, submit orders, or add
runtime behavior.

Phase 13 hardens the screener-ordered signal evaluation contract with focused
unit tests only. Mixed signal/no-signal results preserve screener order,
no-signal candidates remain represented with `order=None`, inputs are not
mutated, `ScreenerSignalEvaluation` is immutable, and `signal_rule` exceptions
propagate instead of being hidden as `order=None`.

No risk, broker, execution, Alpaca, order submission, scheduler, ML, dependency,
or LLM trading-path logic was added.

Phase 14 Step 1 adds test-only AST dependency-direction guardrails. These tests
enforce the documented layering between screener, signals, risk, orchestration,
and execution before any Signal -> Risk runtime code exists.

No Signal -> Risk runtime behavior, broker wiring, Alpaca changes, execution
integration, order submission, scheduler/runtime behavior, ML, dependency, or
LLM trading-path logic was added.

Phase 14 Step 2 adds pure Signal -> Risk evaluation in
`src/algotrader/orchestration/signal_risk_flow.py`.
`evaluate_risk_for_screener_signals(...)` converts
`ScreenerSignalEvaluation` rows into immutable `SignalRiskEvaluation` rows,
retains no-signal rows with `risk=None`, and checks proposed orders with
`RiskEngine` only.

Risk-approved means only allowed by risk. The function does not call brokers,
execution, Alpaca, `submit_order`, CLI, scheduler, persistence, ML, or LLM
trading-path logic.

Phase 15 documents the future Risk -> Execution boundary in
[`docs/design/phase15_risk_to_execution.md`](design/phase15_risk_to_execution.md).
It clarifies that `risk_approved` rows are still not executed, submitted,
broker-routed, filled, or persisted. A future execution bridge must preserve
order, keep `no_signal` and `risk_rejected` rows traceable even when they are
not execution-eligible, and remain separated from broker, Alpaca, scheduler,
persistence, ML, and LLM trading-path behavior until a later explicitly
approved phase.

Phase 16 Step 1 strengthens AST dependency-direction tests so pre-execution
orchestration modules do not import execution, broker, Alpaca, or trade-flow
modules. It adds no Risk -> Execution runtime behavior, execution bridge,
broker wiring, order submission, scheduler, persistence, ML, dependency, or LLM
trading-path logic.

Phase 16 Step 2 adds pure risk-approved row selection in
`src/algotrader/orchestration/risk_execution_flow.py`.
`select_risk_approved_evaluations(...)` returns only
`SignalRiskEvaluation` rows with `status="risk_approved"`, preserves input
order, preserves object identity, and returns an immutable tuple. `no_signal`
and `risk_rejected` rows are skipped.

The selector does not create execution intents, call brokers, import execution,
touch Alpaca, call `submit_order`, use schedulers, persist anything, mutate
portfolios, add dependencies, or add ML or LLM trading-path logic.
`risk_approved` remains a permission signal only, not an execution instruction.

Known limitation: rows can be individually risk-approved against the same fixed
portfolio snapshot while not being collectively affordable. This selector does
not solve batch-level cumulative cash handling or same-symbol conflict
resolution; those remain future execution-boundary concerns before any
execution intent or order submission behavior is added.

Phase 17 Step 1 documents the future execution-intent boundary in
[`docs/design/phase17_execution_intent_boundary.md`](design/phase17_execution_intent_boundary.md).
It distinguishes selected risk-approved rows from execution intents:
risk-approved rows are permission signals only, while an execution intent is a
deterministic, immutable, auditable, broker-agnostic internal instruction
candidate prepared before any broker adapter.

Phase 17 Step 2 adds `ExecutionIntent` and
`build_execution_intents_from_risk_approved(...)` in
`src/algotrader/orchestration/risk_execution_flow.py`. `ExecutionIntent` has
only `source_evaluation: SignalRiskEvaluation`, preserving the source row by
identity without inventing screener rank, original index, broker IDs,
client-order IDs, idempotency keys, persistence metadata, fill fields, SDK
objects, Alpaca-specific fields, or LLM-derived fields. The builder returns an
immutable tuple for risk-approved rows only and skips `no_signal` and
`risk_rejected` rows.

No broker routing, order submission, Alpaca change, `submit_order`,
client-order-id generation, idempotency implementation, batch cash reservation,
same-symbol conflict resolution, scheduler/runtime behavior, persistence,
portfolio mutation, fills, ML, or LLM trading-path logic has been added.

Phase 17 Step 3 hardens the traceability contract without production-code
changes. `ExecutionIntent` still has exactly one dataclass field,
`source_evaluation`; it does not expose direct `order`, `risk`, `status`,
`symbol`, `quantity`, `side`, broker, account, venue, idempotency, submission,
fill, SDK, Alpaca, or persistence fields. Convenience properties should not be
added without a later explicit design phase.

Phase 18 Step 1 documents the future execution-planning boundary in
[`docs/design/phase18_execution_planning_boundary.md`](design/phase18_execution_planning_boundary.md).
It distinguishes `ExecutionIntent` from an execution-planning boundary.
`ExecutionIntent` is an internal pre-submission source wrapper. Step 1 kept
`ExecutionPlan` conceptual only and added no broker routing, order submission,
`client_order_id` generation, idempotency implementation, persistence writes,
batch cash reservation, same-symbol conflict resolution, scheduler/runtime
behavior, portfolio mutation, fills, ML, or LLM trading-path logic.

Phase 18 Step 2 adds the minimal `ExecutionPlan` contract in
`src/algotrader/orchestration/execution_planning_flow.py`.
`ExecutionPlan` has only `intents: tuple[ExecutionIntent, ...]` and is an
immutable batch container, not an executable instruction. `build_execution_plan(...)`
accepts any iterable of `ExecutionIntent` objects and returns an immutable plan
while preserving intent order and identity. Proposed orders and risk verdicts
remain reachable through `plan.intents[n].source_evaluation.order` and
`plan.intents[n].source_evaluation.risk`.

No cash reservation, buying-power reservation, same-symbol conflict handling,
duplicate or competing order policy, priority policy, idempotency,
`client_order_id`, broker routing, order submission, persistence writes,
scheduler/runtime behavior, portfolio mutation, fills, reconciliation changes,
ML, or LLM trading-path logic has been added.

Phase 18 Step 3 hardens the `ExecutionPlan` traceability contract without
production-code changes. `ExecutionPlan` still has exactly one dataclass field:
`intents`. Each plan entry is the exact original `ExecutionIntent` object, and
each intent's `source_evaluation` remains the exact original
`SignalRiskEvaluation` object. Proposed orders, risk verdicts, and statuses are
reachable through `plan.intents[n].source_evaluation`, not through direct
`ExecutionPlan` fields.

No direct order, risk, status, symbol, quantity, side, selected/rejected/skipped
intent, broker, account, venue, submission, fill, idempotency,
`client_order_id`, cash reservation, priority/rank, SDK, Alpaca, or persistence
fields exist on `ExecutionPlan`.

Phase 19 Step 1 documents the future execution-planning policy boundary in
[`docs/design/phase19_execution_planning_policy.md`](design/phase19_execution_planning_policy.md).
That policy remains conceptual only. No policy result object, accepted/skipped
buckets, cash reservation, buying-power reservation, same-symbol conflict
handling, duplicate/competing order handling, priority/ranking behavior,
broker-facing request construction, broker routing, idempotency, persistence,
audit logging writes, order submission, runtime behavior, ML, or LLM
trading-path logic has been implemented.

Phase 19 Step 2 adds the minimal policy result contract in
`src/algotrader/orchestration/execution_planning_policy.py`. `PlanningPolicyResult`
is a deterministic pre-broker result container with `accepted_intents` and
`skipped_intents`. `SkippedExecutionIntent` stores an `ExecutionIntent` plus a
plain deterministic reason string for future traceability. The current
`apply_noop_execution_planning_policy(...)` function is pass-through only: all
input plan intents are accepted unchanged and no skipped intents are produced.

No cash reservation, buying-power reservation, same-symbol conflict handling,
duplicate or competing order policy, priority policy, idempotency,
`client_order_id`, broker routing, order submission, persistence writes,
scheduler/runtime behavior, portfolio mutation, fills, reconciliation changes,
ML, or LLM trading-path logic has been added.

Phase 19 Step 3 keeps the policy implementation unchanged and hardens the
contract with tests and documentation only. `PlanningPolicyResult` still has
only `accepted_intents` and `skipped_intents`; `SkippedExecutionIntent` still
has only `intent` and `reason`. Convenience fields or properties such as
`orders`, `risks`, `statuses`, `symbols`, `accepted_orders`, `skipped_orders`,
`client_order_ids`, `idempotency_keys`, `broker_order_ids`, `cash_reserved`,
`buying_power_reserved`, `priority`, or `rank` remain excluded.

Phase 20 Step 1 documents the future maximum accepted intents per plan policy in
[`docs/design/phase20_max_intents_policy.md`](design/phase20_max_intents_policy.md).
Phase 20 Step 2 implements that boundary as a pure policy function.
`MaxAcceptedIntentsPolicyConfig` is a frozen, slotted config with exactly one
field, `max_accepted_intents`, and the value must be exactly an `int` greater
than or equal to `1`. `None` does not mean no cap; the no-op policy remains the
explicit no-cap behavior.

`apply_max_intents_execution_planning_policy(...)` caps accepted intents
deterministically using explicit configuration and existing plan order, then
places later intents in `skipped_intents` with the deterministic reason
`"max_intents_per_plan_exceeded"`. It preserves accepted and skipped
`ExecutionIntent` identity, and source `SignalRiskEvaluation` identity remains
traceable through `source_evaluation`.

No index/provenance field, priority/ranking behavior, cash reservation,
buying-power reservation, same-symbol conflict handling, duplicate/competing
order policy, idempotency, `client_order_id` generation, broker routing,
persistence, audit logging writes, order submission, scheduler or runtime
behavior, ML, or LLM trading-path logic has been implemented.

Phase 20 Step 3 is tests/docs-only hardening. It adds no production source
changes and keeps the max-intents policy narrow, pure, deterministic,
pre-broker, and source-evaluation driven.

Phase 23 Step 1 documents a future signal evaluation, clock, and as-of boundary
in
[`docs/design/phase23_signal_evaluation_clock_boundary.md`](design/phase23_signal_evaluation_clock_boundary.md).
That future evaluator remains conceptual only here. It may later consume
validated signal definition metadata, explicit input snapshots, explicit
observation timestamps, an explicit `as_of` timestamp, deterministic context,
and snapshot fingerprints. It must produce advisory signal-evaluation metadata
only, not orders, risk approvals, execution intents, execution plans, ranking
or priority decisions, broker requests, portfolio mutations, or LLM-generated
trade decisions.

Time must be explicit in deterministic evaluation. Future deterministic signal,
risk, and orchestration layers should receive timezone-aware timestamps as
data, prefer UTC internally, reject naive datetimes, and avoid direct
wall-clock, randomness, UUID-randomness, or environment-variable reads except
inside explicit boundary modules.

Phase 23 Step 2 adds the minimal deterministic time primitives in
`src/algotrader/core/time.py`: `require_utc_datetime(...)`, `Clock`,
`FixedClock`, and `assert_not_after_as_of(...)`. These primitives validate
explicit UTC-aware datetimes, provide an injectable fixed clock for
deterministic tests, and reject observations after `as_of`.

This contract does not read system time, fetch live data, evaluate signals,
compute features, approve trades, mutate execution plans, interact with broker
or Alpaca, schedule runtime behavior, persist records, train ML models, or put
LLMs in the trading path.

Phase 23 Step 3 hardens the time contract with focused tests only. The tests
pin exact UTC datetime identity preservation, repeated `FixedClock.now()`
identity, fixed-clock immutability, naive and non-UTC rejection, equality and
before-`as_of` allowance, after-`as_of` rejection, dependency independence,
absence of trading-path fields, and absence of hidden nondeterministic API
calls such as wall-clock reads, random generators, UUID randomness, and
environment access.

Phase 24 Step 1 documents the future `SignalEvaluationResult` boundary in
[`docs/design/phase24_signal_evaluation_result_boundary.md`](design/phase24_signal_evaluation_result_boundary.md).
Phase 24 Step 2 adds the minimal `SignalEvaluationResult` contract in
`src/algotrader/signals/signal_evaluation_result.py`. The result is advisory
deterministic signal-evaluation metadata produced by applying a validated
signal definition to explicit input snapshots at an explicit `as_of` boundary.
It carries evaluation id, signal definition id/version, source artifact
id/version, input fingerprint, UTC-aware `as_of`, UTC-aware `evaluated_at`,
deterministic output value, reason code, diagnostics, assumptions, and
limitations.

Signal evaluation outputs are advisory. They do not create orders, broker
requests, execution intents, or execution plans. They do not approve trades,
mutate portfolios, mutate execution plans, reserve cash or buying power, submit
orders, rank execution candidates, or produce LLM-generated trading decisions.
Risk approval remains in the risk layer, execution intent and execution plan
creation remain in the execution layer, and broker behavior remains isolated.
Explicit UTC-aware time remains required: `as_of` must be explicit,
`evaluated_at` must be explicit or injected by a deterministic clock in a
future implementation, naive datetimes must be rejected, hidden system time
reads are not allowed, and no input observation may be after `as_of`.

Phase 24 Step 3 keeps production source unchanged and hardens the traceability
contract. Tests pin exact `as_of` and `evaluated_at` object identity,
deterministic ordering and immutability of all tuple fields, exact preservation
of trace string fields, advisory-only surface area, absence of trading-path
fields, and independence from execution, risk, broker, runtime, persistence,
ML, and LLM modules. `SignalEvaluationResult` is not a signal evaluator, does
not compute signals, does not approve risk, does not create execution intents,
does not mutate execution plans, does not route to brokers or Alpaca, does not
submit orders, does not touch scheduler/runtime/persistence, and does not use
ML or LLMs in the trading path.

## Research And Validation Boundary

Phase 21 Step 1 documents the future research/validation boundary in
[`docs/design/phase21_research_validation_boundary.md`](design/phase21_research_validation_boundary.md).
Phase 21 Step 2 adds the minimal validated artifact metadata contract in
`src/algotrader/research/validated_artifact.py`.
Phase 21 Step 3 hardens that contract with tests and documentation only.

Historical research, feature exploration, backtesting, walk-forward
validation, regime analysis, strategy notebooks/scripts, and LLM-assisted
research summaries are outside the deterministic trading core. They may propose
ideas, record evidence, and support human review, but their outputs are
advisory until promoted through explicit validated artifacts.

Validated artifacts may include approved feature definitions, approved signal
definitions, validated strategy configs, documented assumptions, evaluation
metrics, acceptance criteria, and versioned research outputs. These artifacts
are evidence packages, not runtime behavior by themselves.

The current production contract is intentionally tiny:
`ResearchMetric(name, value)` and `ValidatedResearchArtifact(...)`. The artifact
stores an identifier, name, version, description, validation timestamp, metrics,
assumptions, limitations, and approved advisory uses. It does not create
signals, approve trades, mutate execution plans, call risk, submit orders,
interact with broker or Alpaca, schedule runtime behavior, persist records,
ingest live data, train ML models, or put LLMs in the hot path.

The hardened traceability tests prove that metric identity is preserved inside
`ValidatedResearchArtifact.metrics`, metrics, assumptions, limitations, and
approved advisory uses preserve deterministic order, tuple fields cannot be
mutated after construction, and the artifact remains independent from
`ExecutionPlan`, `ExecutionIntent`, `PlanningPolicyResult`, and risk-evaluation
types.

The deterministic core may consume only approved, explicit, validated inputs.
Future research-derived behavior must enter through deterministic contracts,
types, configs, fixtures, and pure functions that are test-first, offline, and
credential-free. Normal `python -m pytest` must remain offline and
credential-free.

Phase 22 Step 1 documents the future validated signal definition boundary in
[`docs/design/phase22_validated_signal_definition_boundary.md`](design/phase22_validated_signal_definition_boundary.md).
Phase 22 Step 2 adds the minimal validated signal definition metadata contract
in `src/algotrader/signals/validated_signal_definition.py`.
Phase 22 Step 3 hardens that contract with tests and documentation only.
A future validated signal definition may be supported by a validated research
artifact, but it is not raw research output, not a backtest result, not a
feature, not a strategy, not an execution intent, not an execution plan, and
not a broker order. It is a promoted deterministic contract candidate for a
future signal evaluator.

Validated signal definitions are not execution decisions. They do not create
signals by themselves, approve trades, mutate execution plans, reserve cash or
buying power, rank or prioritize orders, submit orders, interact with broker or
Alpaca, schedule runtime behavior, persist records, ingest live data, train ML
models, or put LLMs in the hot path.

The current contract is definition metadata only:
`ValidatedSignalDefinition(...)` stores a signal id, name, version,
description, source validated research artifact id/version, required inputs,
output type, deterministic evaluation rule reference, approved advisory uses,
assumptions, and limitations. It references validated research artifacts by
stable strings only and does not import runtime research behavior.

The hardened traceability tests prove that source artifact id/version strings
are preserved exactly, `required_inputs`, `approved_for`, `assumptions`, and
`limitations` preserve deterministic order, tuple fields cannot be mutated
after construction, and signal definitions remain independent from
`ValidatedResearchArtifact` runtime objects, `ExecutionPlan`,
`ExecutionIntent`, `PlanningPolicyResult`, risk-evaluation types, broker,
runtime/scheduler, and persistence modules.

Phase 23 Step 1 documents the next future boundary after validated signal
definitions: deterministic signal evaluation with explicit clock and as-of
rules. Validated signal definitions remain metadata-only. Future signal
evaluations are advisory reports, not execution decisions. They may later carry
deterministic signal values, scores or buckets, reason codes, input snapshot
fingerprints, evaluation fingerprints, and assumptions or limitations
references, but they must not carry `ProposedOrder`, orders, order IDs,
client-order IDs, broker requests, symbol-specific order instructions,
execution-command sides, quantities, cash or buying-power reservations,
portfolio mutation, risk approval, execution intents, execution plans, fills,
ranking/priority decisions, or LLM-generated trade decisions.

The deterministic core consumes only explicit promoted contracts. A future
evaluator must receive explicit input snapshots and explicit timezone-aware
timestamps. Inputs observed after the supplied `as_of` timestamp should be
rejected, hidden live data fetches and implicit data revisions should be
forbidden, and parameter changes should require a new definition or context
version.

Phase 23 Step 2 implements only the tiny shared time contract that future
deterministic components can receive explicitly. It rejects naive and non-UTC
datetimes, exposes an injectable clock protocol, provides a frozen fixed clock,
and adds a lookahead-prevention helper for `observed_at <= as_of`. It does not
provide a system clock, scheduler, runtime loop, live-data fetch, signal
evaluation, risk approval, execution-plan mutation, broker behavior, Alpaca
behavior, persistence, ML, or LLM trading-path logic.

Phase 23 Step 3 keeps production source unchanged and hardens the traceability
contract. Time contracts remain deterministic primitives only. They do not
evaluate signals, fetch live data, read system time in deterministic paths,
approve trades, mutate execution plans, interact with broker, Alpaca,
scheduler/runtime, persistence, ML, or LLM trading-path logic. UTC-aware
timestamp enforcement and lookahead-prevention behavior are pinned by tests.

Phase 24 Step 1 documents the next future boundary: advisory
`SignalEvaluationResult` output. Phase 24 Step 2 adds the minimal immutable
contract for that output. `ValidatedResearchArtifact` remains evidence,
`ValidatedSignalDefinition` remains approved metadata, and
`SignalEvaluationResult` remains advisory deterministic metadata only. A future
signal-to-risk bridge may consume that output only after a separate design and
implementation phase. Signal evaluation does not create orders, approve trades,
mutate execution plans, interact with brokers, or put LLMs in the hot path.
Phase 24 Step 3 hardens this result contract with tests and documentation only;
no production behavior was added.

Phase 25 Step 1 documents the future deterministic signal evaluator boundary in
[`docs/design/phase25_signal_evaluator_boundary.md`](design/phase25_signal_evaluator_boundary.md).
The future evaluator is conceptual only: it may later transform
`ValidatedSignalDefinition` metadata plus explicit deterministic input
snapshots and explicit UTC-aware `as_of`/`evaluated_at` timestamps into
advisory `SignalEvaluationResult` objects. No evaluator exists yet, no signal
computation or runtime behavior has been added, signal evaluation remains
pre-risk and advisory, and LLMs remain outside the trading hot path.

Phase 25 Step 2 adds only the minimal input snapshot/reference contract in
`src/algotrader/signals/signal_evaluation_input.py`.
`SignalEvaluationInputSnapshot` stores `snapshot_id`, explicit UTC-aware
`as_of`, ordered `required_input_names`, and ordered `source_ids`. It exists
only to provide deterministic, explicit input traceability for a future
evaluator. It does not add a signal evaluator, compute signals or features,
access live data, approve risk, create execution intents, mutate execution
plans, route to brokers, interact with Alpaca, use scheduler/runtime or
persistence behavior, train or run ML, or use LLMs in the trading path.

Phase 25 Step 3 keeps production source unchanged and hardens the traceability
contract with focused tests and documentation only. The tests pin exact `as_of`
identity preservation, exact trace string preservation, deterministic tuple
ordering, tuple immutability, input-list mutation isolation, metadata-only
surface area, absence of signal output fields, absence of score, direction,
confidence, order, risk, execution, broker, account, position, fill, portfolio,
cash, buying-power, scheduler, runtime, persistence, ML, and LLM fields, no
dependency on `SignalEvaluationResult`, no downstream risk, execution, broker,
runtime, persistence, ML, or LLM dependencies, and no hidden wall-clock,
random, network, filesystem-write, environment-variable, broker SDK, or Alpaca
access.
`SignalEvaluationInputSnapshot` remains input traceability metadata only; it is
not a signal evaluator and does not compute signals or features.

Phase 26 Step 1 documents the future no-op signal evaluator boundary in
[`docs/design/phase26_signal_evaluator_noop_boundary.md`](design/phase26_signal_evaluator_noop_boundary.md).
No evaluator implementation exists yet. The future no-op evaluator is
conceptual only: it may later construct advisory `SignalEvaluationResult`
metadata from `ValidatedSignalDefinition`, `SignalEvaluationInputSnapshot`,
explicit UTC-aware `as_of`, explicit UTC-aware `evaluated_at`, and deterministic
metadata already available through existing contracts. It must not compute real
signal values, inspect live market data, compute features, rank, score, infer
direction, approve or reject trades, create execution intents, mutate execution
plans, or imply actionability.

Evaluator output remains strictly advisory and pre-risk. A result from any
future evaluator is not a signal firing, recommendation, risk approval,
execution instruction, execution intent, order request, or broker payload. No
sizing decision, exposure calculation, cash reservation, buying-power check, or
portfolio-level reasoning has occurred when evaluator output is returned.
Future evaluator modules must not import broker, Alpaca, execution, risk,
runtime/scheduler, persistence, ML, or LLM modules. Any need for one of those
imports is a phase-scope violation requiring a new design review. LLMs remain
outside the trading hot path.

Phase 26 Step 2 reviews whether the existing `SignalEvaluationResult` contract
can safely represent a future no-op evaluator result. The review conclusion is
that the current contract is sufficient for a minimal no-op evaluator. It
already preserves signal definition identity/version, source artifact
identity/version, input snapshot identity through `input_fingerprint`, explicit
UTC-aware `as_of`, explicit UTC-aware `evaluated_at`, `output_value`,
`reason_code`, `diagnostics`, `assumptions`, and `limitations`.

No no-op marker, `result_kind`, or `evaluator_kind` is needed before a minimal
no-op evaluator implementation. A future no-op result need not be structurally
distinguishable from a later real evaluator result by field shape because both
remain advisory metadata. The safer path is to keep any future no-op result
empty/advisory in meaning and traceable through existing metadata fields rather
than adding score, direction, confidence, actionability, or kind fields. Phase
26 Step 2 adds no evaluator implementation, no production behavior, no runtime
behavior, and no trading-path behavior.

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

Phase 26 Step 3 adds only the minimal no-op evaluator contract in
`src/algotrader/signals/noop_signal_evaluator.py`.
`NoOpSignalEvaluator` is a frozen, slotted evaluator-shaped object with one
method:

```text
evaluate(definition, input_snapshot, *, as_of, evaluated_at)
    -> SignalEvaluationResult
```

The evaluator accepts a `ValidatedSignalDefinition`, a
`SignalEvaluationInputSnapshot`, and explicit UTC-aware `as_of` and
`evaluated_at` timestamps. It validates timestamps with the deterministic time
contract, rejects naive or non-UTC timestamps, rejects `evaluated_at < as_of`,
rejects input snapshots whose `as_of` is after the result `as_of`, and returns
advisory `SignalEvaluationResult` metadata using existing fields only.

The no-op evaluator preserves signal definition id/version, source artifact
id/version, input snapshot id through `input_fingerprint`, and timestamp object
identity in the returned result. It uses no `result_kind`, `evaluator_kind`,
`is_noop`, or no-op marker field. It does not score, rank, infer direction,
set confidence or probability, expose actionability, recommend trades, approve
risk, create execution intents, mutate execution plans, access live data, route
to brokers, submit orders, use scheduler/runtime/persistence behavior, run ML,
or call LLMs.

Current focused validation for the no-op evaluator boundary:

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

Phase 26 Step 4 hardens the existing no-op evaluator contract with tests and
documentation only. No production source changed, and no production behavior was
added. `NoOpSignalEvaluator` remains deterministic and advisory-only: it proves
the evaluator input/output boundary without real signal computation and
preserves traceability without actionability.

The hardened tests pin exact signal definition id/version preservation, exact
source research artifact id/version preservation, exact input snapshot id
preservation through `input_fingerprint`, exact `as_of` and `evaluated_at`
object identity, exact no-op reason code, deterministic ordering for
diagnostics/assumptions/limitations, environment-variable independence,
random-state independence, non-mutation of input contracts and tuple fields,
accepted and rejected timestamp/lookahead edges, advisory-only surface fields,
trading-path isolation, and AST guardrails against hidden wall-clock, random,
environment, network, filesystem-write, database/cache/persistence, broker,
Alpaca, ML, LLM, agent, prompt, and output dependencies.

The no-op evaluator still does not score, rank, infer direction, recommend
trades, approve risk, create execution intents, mutate execution plans, access
live data, route to brokers or Alpaca, submit orders, use scheduler/runtime or
persistence behavior, run ML, or use LLMs in the trading path. Normal pytest
remains offline, credential-free, and safe.

Phase 27 Step 1 documents the admission criteria for any future real
deterministic signal evaluator in
[`docs/design/phase27_real_signal_evaluator_admission_boundary.md`](design/phase27_real_signal_evaluator_admission_boundary.md).
No real evaluator exists yet. Actual signal computation remains forbidden until
the project first designs and implements an explicit deterministic input-value
contract, proves observation timestamps are available at or before `as_of`, and
meets the documented admission criteria for deterministic behavior, lookahead
prevention, no side effects, and no trading-path dependencies.

Even after admission, evaluator output remains advisory and pre-risk. It is not
a recommendation, not risk approval, not an execution intent, not an order
request, not portfolio-aware, not broker-aware, and not actionability by itself.
LLMs remain outside the trading hot path.

Phase 27 Step 2 documents the future deterministic signal input-value boundary
in
[`docs/design/phase27_signal_input_value_boundary.md`](design/phase27_signal_input_value_boundary.md).
No input-value contract exists yet. `SignalEvaluationInputSnapshot` remains
reference metadata only: it preserves `snapshot_id`, UTC-aware `as_of`,
`required_input_names`, and `source_ids`, but it does not carry actual observed
market values, feature values, bar payloads, quote payloads, or computed inputs.

Future input-value contracts are expected to carry explicit deterministic
observed values, observation timestamps, source traceability, value type
constraints, and no-lookahead validation support before any real evaluator can
compute signals. This phase adds no such contract, no real evaluator, and no
signal computation. Evaluator output remains advisory and pre-risk, and LLMs
remain outside the trading hot path.

Phase 27 Step 3 adds the first minimal input-value implementation:
`SignalInputValue` in `src/algotrader/signals/signal_input_value.py`. The
contract is a frozen, slotted dataclass with `name`, `value`, `observed_at`, and
`source_id`. It preserves accepted string values exactly, stores the observed
value without computation or interpretation, validates `observed_at` as an
explicit UTC-aware timestamp, rejects naive and non-UTC timestamps, and rejects
empty or blank `name` and `source_id`.

`SignalInputValue` accepts only deterministic scalar values for the first
contract surface: `Decimal`, `int`, `str`, and `bool`. It does not perform
lookahead validation against an evaluator `as_of`; that belongs to a later
assembly or evaluator-input boundary. It does not compute signals or features,
score, rank, infer direction, recommend trades, approve risk, create execution
intents, mutate execution plans, access live data, route to brokers or Alpaca,
submit orders, use scheduler/runtime/persistence, run ML, or use LLMs in the
trading path. Normal pytest remains offline, credential-free, and safe.

Phase 27 Step 4 hardens `SignalInputValue` traceability with tests and docs
only. The tests now prove exact `name`, `source_id`, `observed_at`, `Decimal`,
`int`, `str`, and `bool` preservation; `bool` remains distinct from `int`; and
accepted values are stored without normalization, rounding, conversion, or
interpretation. They also pin immutability, slots, UTC timestamp validation,
string validation, scalar-only value support, unsupported mutable/object
rejection, no internal evaluator `as_of` or lookahead validation, and no
wall-clock, random, environment, network, filesystem-write, database/cache,
broker, Alpaca, ML, LLM, agent, prompt, or output dependencies.

`SignalInputValue` remains an immutable observed-value contract. It carries
explicit observed scalar values and source/timestamp traceability, but it does
not compute, normalize, rank, score, infer direction, recommend trades, approve
risk, create execution intents, mutate execution plans, access live data, route
to brokers or Alpaca, submit orders, use scheduler/runtime/persistence, run ML,
or use LLMs in the trading path. Normal pytest remains offline,
credential-free, and safe.

Phase 28 Step 1 documents the future signal input bundle boundary in
[`docs/design/phase28_signal_input_bundle_boundary.md`](design/phase28_signal_input_bundle_boundary.md).
Phase 28 Step 2 adds the minimal immutable `SignalInputBundle` contract in
`src/algotrader/signals/signal_input_bundle.py`. The bundle groups explicit
`SignalInputValue` objects for future evaluator use, preserves supplied value
ordering and input value object identity, rejects duplicate names, validates
`as_of` as UTC-aware, and rejects lookahead values where
`SignalInputValue.observed_at > bundle.as_of`.

Phase 28 Step 3 hardens the bundle with tests and documentation only. No
production behavior was added. The hardening pins exact `snapshot_id` string
preservation, exact `as_of` identity preservation, exact grouped value object
identity, exact value ordering, exact value names, source ids, observed
timestamp identity, payload preservation, tuple immutability, duplicate-name
rejection, and lookahead rejection. Multiple bundles built from the same values
in the same order compare equal, while different supplied orders remain
different orders.

The bundle remains an input container only. It is not a signal result,
recommendation, score, rank, direction, risk approval, execution intent, order
request, or portfolio decision. It does not yet validate completeness against
`SignalEvaluationInputSnapshot`. It does not compute signals or features,
implement a real evaluator, score, rank, infer direction, recommend trades,
approve risk, mutate execution plans, access live data, route to brokers or
Alpaca, submit orders, use scheduler/runtime/persistence behavior, run ML, or
use LLMs in the trading path. Evaluator output remains advisory and pre-risk,
and LLMs remain outside the trading hot path.

Phase 28 Step 4 documents the future completeness boundary in
[`docs/design/phase28_signal_input_bundle_completeness_boundary.md`](design/phase28_signal_input_bundle_completeness_boundary.md).
The future boundary may compare a snapshot's required input names and metadata
with a bundle's explicit values before evaluator use. Phase 28 Step 5 adds the
minimal pure validation function for that boundary:
`validate_signal_input_bundle_completeness(snapshot, bundle)` returns an
immutable `SignalInputBundleCompletenessResult` with snapshot id traceability,
bundle snapshot id traceability, `is_complete`, missing input names, and extra
input names.

The validation compares only `SignalEvaluationInputSnapshot.required_input_names`
with `SignalInputBundle.values[n].name`. Missing names are reported in snapshot
order, extra names are reported in bundle order, and extra names do not make the
result incomplete in this phase. It does not enforce snapshot id equality or
`as_of` equality yet, does not perform lookahead validation beyond the existing
bundle constructor rule, and does not inspect or interpret values.
`SignalInputBundle` remains a grouping contract only; completeness validation
remains a separate pure boundary. No real evaluator or signal computation
exists yet, evaluator output remains advisory and pre-risk, and LLMs remain
outside the trading hot path.

Phase 28 Step 6 hardens the existing completeness validation tests and docs
only. The hardening pins exact result field shape, frozen/slotted behavior,
tuple immutability, deterministic missing and extra name ordering, exact
snapshot id and bundle snapshot id traceability, input non-mutation, repeated
call determinism, environment/random independence, no hidden wall-clock access,
and no value, source id, observed timestamp, lookahead, signal, feature, score,
rank, direction, actionability, risk, execution, broker, runtime, persistence,
ML, or LLM behavior.

Phase 29 Step 1 defines the first real evaluator design gate in
[`docs/design/phase29_first_real_evaluator_design_gate.md`](design/phase29_first_real_evaluator_design_gate.md).
No real evaluator exists yet. The current input stack supports explicit
snapshots, observed values, bundles, and name-only completeness validation, but
it does not make any output actionable. Real signal computation remains
forbidden until a future evaluator-specific design satisfies the gate. Any
future evaluator output remains advisory and pre-risk, and LLMs remain outside
the trading hot path.

Phase 29 Step 2 selects the first real evaluator candidate in
[`docs/design/phase29_first_real_evaluator_candidate_selection.md`](design/phase29_first_real_evaluator_candidate_selection.md).
The selected candidate is a minimal threshold-style advisory evaluator over one
explicit scalar `SignalInputValue`. Candidate selection is documentation-only
and does not authorize implementation. No real evaluator exists yet, and real
signal computation remains forbidden until evaluator-specific design and tests
satisfy the gate. Evaluator output remains advisory and pre-risk, and LLMs
remain outside the trading hot path.

Phase 29 Step 3 designs that selected candidate contract in
[`docs/design/phase29_first_real_evaluator_candidate_contract.md`](design/phase29_first_real_evaluator_candidate_contract.md).
The contract design documents the placeholder input name `indicator_value`, the
preferred initial value type `Decimal`, possible `>=` threshold semantics,
advisory-only output expectations, completeness and timestamp questions, strict
no-lookahead rules, forbidden semantics, and required future tests. It remains
documentation-only. No real evaluator exists yet, and real signal computation
remains forbidden until implementation is explicitly scoped. Evaluator output
remains advisory and pre-risk, and LLMs remain outside the trading hot path.

Phase 29 Step 4 defines the first real evaluator implementation test matrix in
[`docs/design/phase29_first_real_evaluator_test_matrix.md`](design/phase29_first_real_evaluator_test_matrix.md).
It is documentation-only and does not add a real evaluator, signal computation,
production behavior, runtime behavior, or trading-path behavior. Real signal
computation remains forbidden until implementation is explicitly scoped.
Evaluator output remains advisory and pre-risk, and LLMs remain outside the
trading hot path.

Phase 29 Step 5 reviews implementation readiness in
[`docs/design/phase29_first_real_evaluator_implementation_readiness.md`](design/phase29_first_real_evaluator_implementation_readiness.md).
It is documentation-only and recommends one more docs-only constants/output
semantics design step before implementation. No real evaluator exists yet, and
real signal computation remains forbidden unless explicitly scoped in a later
implementation phase. Evaluator output remains advisory and pre-risk, and LLMs
remain outside the trading hot path.

Phase 29 Step 6 designs threshold evaluator constants/output semantics in
[`docs/design/phase29_threshold_evaluator_constants_output_semantics.md`](design/phase29_threshold_evaluator_constants_output_semantics.md).
It is documentation-only. It selects safe evaluator-local constants and textual
advisory output semantics, but exact validated signal and research artifacts
remain missing. No real evaluator exists yet, and real signal computation
remains forbidden unless explicitly scoped in a later implementation phase.
Evaluator output remains advisory and pre-risk, and LLMs remain outside the
trading hot path.

Phase 30 Step 1 defines the threshold evaluator research-support boundary in
[`docs/design/phase30_threshold_evaluator_research_support_boundary.md`](design/phase30_threshold_evaluator_research_support_boundary.md).
It is documentation-only. It records the validated research artifact,
validated signal definition, threshold value/source evidence, acceptance
criteria, non-actionability rule, and future test implications required before
a real threshold-style evaluator may be implemented. No real evaluator exists
yet, real signal computation remains forbidden, evaluator output remains
advisory and pre-risk, and LLMs remain outside the trading hot path.

Phase 30 Step 2 defines the research validation evidence standard in
[`docs/design/phase30_research_validation_evidence_standard.md`](design/phase30_research_validation_evidence_standard.md).
It is documentation-only and creates the fixed checklist future research
artifacts must be reviewed against before they can support a real evaluator.
No real evaluator exists yet, real signal computation remains forbidden,
evaluator output remains advisory and pre-risk, and LLMs remain outside the
trading hot path.

Phase 30 Step 3 defines the research artifact candidate review template in
[`docs/design/phase30_research_artifact_candidate_review_template.md`](design/phase30_research_artifact_candidate_review_template.md).
It is documentation-only and creates the intake shape for future artifact
reviews. No actual research artifact is approved, no real evaluator exists
yet, real signal computation remains forbidden, evaluator output remains
advisory and pre-risk, and LLMs remain outside the trading hot path.

Phase 30 Step 4 defines the research artifact candidate sourcing plan and
backlog boundary in
[`docs/design/phase30_research_artifact_candidate_sourcing_plan.md`](design/phase30_research_artifact_candidate_sourcing_plan.md).
It is documentation-only and defines how future candidates may be sourced and
triaged before review. No real evaluator exists yet, real signal computation
remains forbidden, evaluator output remains advisory and pre-risk, and LLMs
remain outside the trading hot path.

Phase 30 Step 5 populates the initial unreviewed research candidate backlog in
[`docs/design/phase30_research_artifact_candidate_backlog.md`](design/phase30_research_artifact_candidate_backlog.md).
It is documentation-only and records candidate placeholders and sourcing
targets only. No candidate artifact is reviewed or approved, no validated
research artifact or validated signal definition is created, no real evaluator
exists yet, real signal computation remains forbidden, evaluator output
remains advisory and pre-risk, and LLMs remain outside the trading hot path.

Phase 30 Step 6 selects the first research candidate sourcing target in
[`docs/design/phase30_first_research_candidate_source_selection.md`](design/phase30_first_research_candidate_source_selection.md).
It is documentation-only and selects `P30-BL-001` for future source
collection only. No source is reviewed or approved, no validated research
artifact or validated signal definition is created, no real evaluator exists
yet, real signal computation remains forbidden, evaluator output remains
advisory and pre-risk, and LLMs remain outside the trading hot path.

Phase 31 Step 1 adds the reusable operating context in
[`docs/agent_context/codex_operating_context.md`](agent_context/codex_operating_context.md).
It is documentation-only and resets research-track workflow granularity:
related docs, research, and planning updates may be combined when low-risk and
code-free, while production-code phases remain narrow, test-first, explicitly
scoped, and heavily verified. It does not validate a research artifact, create
a signal definition, implement a real evaluator, compute signals, or add any
trading-path behavior.

Phase 31 Step 2 adds the research-track next action plan in
[`docs/design/phase31_research_track_next_action_plan.md`](design/phase31_research_track_next_action_plan.md).
It is documentation-only and turns the Phase 30 backlog and source-selection
work into a practical sequence: source package collection, pre-review
normalization, first candidate review, signal-definition binding planning, and
an implementation-readiness gate. `P30-BL-001` remains unreviewed,
unvalidated, not approved, and not implementation-ready. Backlog entries,
source-selection decisions, and research-agent summaries are not evidence by
themselves. Perplexity, Claude, Gemini, and similar tools may assist with
source discovery, summaries, and critique, but they cannot define production
behavior or enter the trading path.

Phase 31 Step 3 adds the normalized `P30-BL-001` source package in
[`docs/design/phase31_p30_bl_001_source_package.md`](design/phase31_p30_bl_001_source_package.md).
It is documentation-only and makes `P30-BL-001` source-package-ready only. It
does not review, validate, approve, or implement any research artifact, signal
definition, threshold, comparator, evaluator behavior, signal computation,
feature computation, strategy logic, scoring, ranking, direction,
actionability, broker behavior, runtime behavior, persistence, ML, or LLM
trading-path behavior.

Phase 31 Step 4 adds the Tier A formal source review in
[`docs/design/phase31_p30_bl_001_tier_a_review.md`](design/phase31_p30_bl_001_tier_a_review.md).
It is documentation-only and conditionally passes Tier A for mechanics and
methodology only. It does not validate `P30-BL-001`, create or approve a
validated research artifact, create a validated signal definition, justify a
production threshold, authorize evaluator implementation, compute signals, add
features, change strategy logic, touch risk or execution, call brokers, add
runtime behavior, persist data, add ML, or put LLMs in the trading path.

Phase 31 Step 5 adds the evidence gap and routing plan in
[`docs/design/phase31_p30_bl_001_evidence_gap_routing_plan.md`](design/phase31_p30_bl_001_evidence_gap_routing_plan.md).
It is documentation-only and preserves `P30-BL-001` as unvalidated. The safest
next route is a formal mechanics-only candidate artifact review summary that
may support future evaluator mechanics but cannot support a production
threshold or evaluator implementation.

Phase 31 Step 6 adds that formal mechanics-only candidate artifact review
summary in
[`docs/design/phase31_p30_bl_001_mechanics_only_review_summary.md`](design/phase31_p30_bl_001_mechanics_only_review_summary.md).
It is documentation-only and conditionally passes `P30-BL-001` for mechanics
and methodology only. It does not validate the candidate, approve an artifact,
create a validated research artifact, create a validated signal definition,
justify a production threshold, authorize evaluator implementation, or add
any production behavior.

Phase 31 Step 7 adds the final `P30-BL-001` disposition in
[`docs/design/phase31_p30_bl_001_final_disposition.md`](design/phase31_p30_bl_001_final_disposition.md).
It is documentation-only and marks `P30-BL-001` mechanics-only dispositioned,
in the mechanics-only sense only. It preserves Tier A sources as informational
and methodological only. It does not validate the candidate, approve an
artifact, create a validated research artifact, create a validated signal
definition, justify a production threshold, authorize evaluator implementation,
or add any production behavior. The next safest research route is a candidate
or research task that can supply dataset-specific threshold or validation
evidence; that route remains unreviewed and unapproved by this phase.

Phase 32 Step 1 adds dataset-specific validation candidate selection in
[`docs/design/phase32_dataset_specific_validation_candidate_selection.md`](design/phase32_dataset_specific_validation_candidate_selection.md).
It is documentation-only and selects dataset-specific threshold or validation
evidence sourcing as the next research direction. `P30-BL-002` is only the
current backlog routing handle, and only if sourcing can produce a concrete
evidence package with dataset scope, point-in-time assumptions, explicit
inputs, threshold or parameter rationale, no-lookahead controls,
reproducibility notes, robustness or out-of-sample evidence, limitations, and
non-claims. A better P0 replacement should be sourced first if it offers
stronger traceable evidence. This selection does not review, validate, approve,
promote, bind, or implement any candidate.

Phase 32 Step 2 adds the `P30-BL-002` source-package sourcing plan in
[`docs/design/phase32_p30_bl_002_source_package_sourcing_plan.md`](design/phase32_p30_bl_002_source_package_sourcing_plan.md).
It is documentation-only and defines the required package fields, acceptable
source types, unacceptable source types, minimum review-readiness criteria, and
rejection/replacement criteria before any formal review can begin. `P30-BL-002`
remains a sourcing target only: unreviewed, unvalidated, unapproved, not
production-ready, not implementation-ready, and not threshold-justified. This
step does not collect or cite actual research sources, create a
`ValidatedResearchArtifact`, create a `ValidatedSignalDefinition`, approve a
threshold, add evaluator behavior, add signal computation, or add runtime,
broker, persistence, ML, or LLM trading-path behavior.

Phase 32 Step 3 adds the `P30-BL-002` source-package collection and
normalization attempt in
[`docs/design/phase32_p30_bl_002_source_package.md`](design/phase32_p30_bl_002_source_package.md).
The revised package normalizes 23 candidate-only source entries from the
supplied Claude, Perplexity, and Gemini/browser scout reports. It deduplicates
overlapping candidates, records preliminary routing categories, identifies
source-level and package-level gaps, and recommends primary-source
verification before any selected entry can be used in formal review. It does
not validate a signal, approve a threshold, create a research artifact, create
a signal definition, promote `P30-BL-002`, or authorize implementation.

Phase 32 Step 4 adds the `P30-BL-002` primary-source verification gate in
[`docs/design/phase32_p30_bl_002_primary_source_verification_gate.md`](design/phase32_p30_bl_002_primary_source_verification_gate.md).
The gate verifies selected primary-source identities and limited intake
eligibility only. It routes `P30-BL-002-S05`, `P30-BL-002-S03`, and
`P30-BL-002-S01` to limited formal review intake and keeps `P30-BL-002-S08`
as maybe-eligible methodology-only PIT review material. It does not validate a
signal, approve a threshold, create a research artifact, create a signal
definition, promote `P30-BL-002`, or authorize implementation.

Phase 32 Step 5 adds the `P30-BL-002` limited formal review intake plan in
[`docs/design/phase32_p30_bl_002_limited_formal_review_intake_plan.md`](design/phase32_p30_bl_002_limited_formal_review_intake_plan.md).
The plan uses the Step 4 gate as its selected-candidate source of truth,
places negative-control sources before candidate-evidence review, and defines
shared and source-specific criteria for later review. It does not validate a
signal, approve a threshold, create a research artifact, create a signal
definition, promote `P30-BL-002`, or authorize implementation.

Phase 32 Step 6 adds the `P30-BL-002-S01` formal review in
[`docs/design/phase32_p30_bl_002_s01_formal_review.md`](design/phase32_p30_bl_002_s01_formal_review.md).
The review passes S01 only for limited negative-control/no-lookahead use. It
can support falsification and moving-average timing-bias guardrail design only;
it cannot support production threshold approval, predictive-edge claims,
profitability claims, a validated artifact, a validated signal definition,
implementation readiness, paper trading readiness, or live trading readiness.
`P30-BL-002` remains unvalidated, unapproved, not promoted, and not
implementation-ready. The next formal review route is `P30-BL-002-S03`.

Phase 32 Step 7 adds the `P30-BL-002-S03` formal review in
[`docs/design/phase32_p30_bl_002_s03_formal_review.md`](design/phase32_p30_bl_002_s03_formal_review.md).
The review passes S03 only for limited
negative-control/data-snooping/OOS guardrail use. It can support
falsification, multiple-testing awareness, data-snooping guardrail design, and
out-of-sample negative-control expectations only; it cannot support production
threshold approval, predictive-edge claims, profitability claims, a validated
artifact, a validated signal definition, implementation readiness, paper
trading readiness, or live trading readiness. `P30-BL-002` remains
unvalidated, unapproved, not promoted, and not implementation-ready. The next
formal review route is `P30-BL-002-S08` so PIT methodology can be reviewed
before candidate evidence.

Phase 32 Step 8 adds the `P30-BL-002-S08` formal review in
[`docs/design/phase32_p30_bl_002_s08_formal_review.md`](design/phase32_p30_bl_002_s08_formal_review.md).
The review passes S08 only for methodology-only PIT review material. It can
support point-in-time methodology framing, survivorship-bias awareness,
restatement / historical-revision awareness, lookahead-risk framing, and
constraints for later candidate-evidence reviews only; it cannot support
production threshold approval, predictive-edge claims, profitability claims, a
validated artifact, a validated signal definition, implementation readiness,
paper trading readiness, or live trading readiness. `P30-BL-002` remains
unvalidated, unapproved, not promoted, and not implementation-ready. The next
formal review route is `P30-BL-002-S05` under the S08 PIT/no-lookahead,
survivorship, and restatement expectations.

Phase 32 Step 9 adds the `P30-BL-002-S05` formal review in
[`docs/design/phase32_p30_bl_002_s05_formal_review.md`](design/phase32_p30_bl_002_s05_formal_review.md).
The review conditionally passes S05 only for limited candidate-evidence
planning. It can support a bounded time-series momentum candidate-evidence
claim, future structured evaluation planning, possible future reproduction
requirements, and constraints for any future candidate signal-definition
discussion only; it cannot support production threshold approval,
predictive-edge claims, profitability claims, a validated artifact, a validated
signal definition, implementation readiness, paper trading readiness, or live
trading readiness. `P30-BL-002` remains unvalidated, unapproved, not promoted,
and not implementation-ready. Later work must produce project-local
deterministic reproduction and an applied no-lookahead/PIT audit before any
stronger use.

Phase 32 Step 14 adds the S05 data-provider scout research normalization in
[`docs/design/phase32_s05_data_provider_scout_research_normalization.md`](design/phase32_s05_data_provider_scout_research_normalization.md).
It is documentation-only and treats the external Perplexity output as
unverified scout research. It records that exact S05 reproduction appears
unlikely under personal/offline constraints at scout level, partial or proxy
reproduction appears more realistic, AQR appears useful for calibration/context
only, CSI/Pinnacle/Norgate/TradeStation appear to require primary
verification, institutional feeds appear practically unsuitable unless
access/licensing is resolved, and broker/free APIs appear unsuitable for exact
reproduction. It does not verify those claims, choose a vendor, acquire data,
approve reproduction, create a validated artifact, create a validated signal
definition, or authorize implementation.

Phase 32 Step 15 adds the S05 primary-verification questionnaire in
[`docs/design/phase32_s05_primary_verification_questionnaire.md`](design/phase32_s05_primary_verification_questionnaire.md).
It is documentation-only and defines general and source-specific questions for
CSI, Pinnacle, Norgate, AQR, and conditional TradeStation. It includes a
response-capture table, decision routing rules, a vendor-neutral manual
outreach template, explicit non-goals, and remaining blockers. It does not
contact vendors, select a source, purchase data, acquire data, ingest data,
approve reproduction, create a validated artifact, create a validated signal
definition, or authorize implementation.

Phase 32 Step 16 adds the S05 public-documentation verification sweep in
[`docs/design/phase32_s05_public_documentation_verification_sweep.md`](design/phase32_s05_public_documentation_verification_sweep.md).
It is documentation-only and treats the externally provided public-documentation
research report as scout input rather than source-of-truth evidence. The sweep
separates primary documentation, secondary documentation, and inference; records
what appears documentation-supported for AQR, CSI, Pinnacle, Norgate, Portara,
TradeStation, institutional feeds, broker-native APIs, and public/free or
ETF/index proxies; assigns only cautious feasibility labels; and carries
forward direct-confirmation questions around exact S05 mapping, 1965-2009
coverage, roll/PIT/versioning, licensing, offline archival, and pricing. It
does not choose a provider, acquire data, design a schema, approve
reproduction, create a validated artifact, create a validated signal
definition, or authorize implementation.

Phase 32 Step 17 adds the S05 public-documentation-only feasibility decision in
[`docs/design/phase32_s05_public_documentation_only_feasibility_decision.md`](design/phase32_s05_public_documentation_only_feasibility_decision.md).
It is documentation-only and records the owner decision to avoid direct
vendor/source contact for now. It keeps S05 only as a public-doc-supported
proxy/partial planning candidate, pauses exact reproduction, source selection,
dataset approval, schema design, validation, and implementation, and routes
future safe work toward a docs-only non-exact proxy boundary, another
easier-data candidate, or backlog pending future contact/access changes. It
does not contact vendors, choose a vendor, acquire data, ingest data, create a
validated artifact, create a validated signal definition, approve a production
threshold, or authorize implementation.

Phase 32 Step 18 adds the S05 non-exact proxy reproduction boundary in
[`docs/design/phase32_s05_non_exact_proxy_reproduction_boundary.md`](design/phase32_s05_non_exact_proxy_reproduction_boundary.md).
It is documentation-only and defines proxy reproduction as a controlled
approximation for methodology mechanics and research workflow testing only. It
distinguishes exact S05 reproduction, partial reproduction, proxy reproduction,
and methodology-only/context use; allows only planning-level proxy routes such
as modern futures subset, reduced-universe futures, ETF/index proxy, AQR
factor-level context, or manually reconstructed published-table checks; and
keeps proxy results from supporting exact S05 replication, validated artifacts,
validated signal definitions, production thresholds, implementation approval,
profitability claims, or trading readiness.

Phase 32 Step 19 adds the S05 proxy route selection boundary in
[`docs/design/phase32_s05_proxy_route_selection_boundary.md`](design/phase32_s05_proxy_route_selection_boundary.md).
It is documentation-only and compares the modern futures subset,
reduced-universe futures, ETF/index proxy, AQR factor-level context,
manually reconstructed published-table check, and pause/defer routes. The
conservative decision keeps multiple routes under consideration, selects no
provider, dataset, subscription, schema, reproduction, validation, or
implementation route, and recommends a route-neutral proxy dataset requirement
boundary before any further route narrowing.

Phase 32 Step 20 adds the S05 route-neutral proxy dataset requirements boundary
in
[`docs/design/phase32_s05_route_neutral_proxy_dataset_requirements_boundary.md`](design/phase32_s05_route_neutral_proxy_dataset_requirements_boundary.md).
It is documentation-only and defines minimum requirements for any possible
future S05 proxy dataset. It covers universe, date range, frequency,
price/return fields, timestamp/as-of semantics, provenance, versioning,
snapshot discipline, missing data, survivorship, adjustment/roll assumptions,
currency, cost/slippage/liquidity assumptions, license/offline-use constraints,
reproducibility constraints, comparison target, route-specific notes, acceptance
criteria, rejection criteria, mandatory non-claims, future gates, recommended
routing, non-goals, and blockers. It selects no proxy route, provider, dataset,
source shortlist, schema, reproduction protocol, validation route, or
implementation path.

Phase 32 Step 21 adds the S05 proxy source shortlist and backlog routing
decision in
[`docs/design/phase32_s05_proxy_source_shortlist_and_backlog_routing.md`](design/phase32_s05_proxy_source_shortlist_and_backlog_routing.md).
It is documentation-only and groups non-approving proxy source categories:
AQR factor-level calibration/context, ETF/index proxy datasets, public/free
market data for methodology demos only, unselected modern futures vendor
categories, unselected reduced futures universe categories, and manually
reconstructed public-table checks. It records that none satisfies the Step 20
minimum requirements at category-only level, selects no route, source,
provider, dataset, schema, reproduction protocol, validation route, or
implementation path, keeps S05 in backlog, and recommends evaluating an
easier-data candidate next.

Phase 33 Step 1 adds the easier-data research candidate selection boundary in
[`docs/design/phase33_easier_data_research_candidate_selection_boundary.md`](design/phase33_easier_data_research_candidate_selection_boundary.md).
It is documentation-only and compares candidate families by public/easy data
availability, licensing clarity, offline reproducibility, simple universe
definition, PIT/survivorship complexity, benchmark clarity, deterministic
workflow usefulness, core-architecture fit, overclaiming risk, vendor-contact
dependency, and implementation distance. It shortlists broad-ETF moving-average
trend-following as the primary source-review candidate, with equity index
momentum/trend-following and volatility-targeting/risk-parity style allocation
as secondary source-review candidates only. It does not select or approve a
dataset, source package, schema, reproduction, validation, implementation,
production threshold, `ValidatedResearchArtifact`, or
`ValidatedSignalDefinition`.

Phase 33 Step 2 adds the broad-ETF moving-average source package in
[`docs/design/phase33_broad_etf_moving_average_source_package.md`](design/phase33_broad_etf_moving_average_source_package.md).
It is documentation-only and prepares source review for the broad-ETF simple
moving-average trend-following candidate. It records the bounded research
question, possible broad ETF categories, high-level methodology framing,
possible public/easy data-source categories, source-quality requirements,
later evidence sources, docs-only review gates, explicit non-goals, and
remaining blockers. It does not approve an ETF universe, data source, dataset,
benchmark, parameter, signal definition, schema, reproduction, validation,
implementation, or trading implication.

Phase 33 Step 3 adds the broad-ETF data feasibility, universe, and benchmark
boundary in
[`docs/design/phase33_broad_etf_data_feasibility_universe_benchmark_boundary.md`](design/phase33_broad_etf_data_feasibility_universe_benchmark_boundary.md).
It is documentation-only and groups public/easy data source feasibility, ETF
universe requirements, and benchmark/cash proxy requirements for the broad-ETF
moving-average candidate. It compares Stooq, Yahoo Finance / yfinance, Nasdaq
Data Link where applicable, Alpha Vantage free/retail APIs, official ETF issuer
pages, FRED where applicable, and broker historical data as candidate or
context source categories only. It defines cautious feasibility labels,
source-quality requirements, future universe and benchmark constraints, a
public-source documentation verification sweep as the next gate, explicit
non-goals, and remaining blockers. It does not approve a source, universe,
benchmark, cash proxy, methodology, data acquisition, reproduction, validation,
implementation, or trading implication.

Phase 33 Step 4 adds the broad-ETF public-source documentation verification
sweep in
[`docs/design/phase33_broad_etf_public_source_documentation_verification_sweep.md`](design/phase33_broad_etf_public_source_documentation_verification_sweep.md).
It is documentation-only and records what public documentation appears to
support for Stooq, Yahoo Finance / yfinance, Nasdaq Data Link, Alpha Vantage,
official ETF issuer pages, FRED, and broker historical data. It separates
primary documentation, secondary documentation, and inference; treats the
external Perplexity report as scout input only; assigns cautious feasibility
labels; records ETF universe and benchmark/cash proxy notes; and carries
forward direct follow-up questions. It does not approve a source, universe,
benchmark, cash proxy, methodology, data acquisition, reproduction, validation,
implementation, or trading implication.

Phase 33 Step 5 adds the broad-ETF methodology and no-lookahead/as-of review
boundary in
[`docs/design/phase33_broad_etf_methodology_no_lookahead_review_boundary.md`](design/phase33_broad_etf_methodology_no_lookahead_review_boundary.md).
It is documentation-only and defines moving-average methodology-review scope,
no-lookahead/as-of requirements, methodology evidence standards, required
future non-claims, relationship to current data-source findings, preferred ETF
universe shortlist routing, explicit non-goals, and remaining blockers. It
does not approve methodology, parameters, data, an ETF universe, benchmark,
cash proxy, reproduction, validation, implementation, or trading implication.

Phase 33 Step 6 adds the broad-ETF universe and benchmark/cash proxy shortlist
boundary in
[`docs/design/phase33_broad_etf_universe_benchmark_shortlist_boundary.md`](design/phase33_broad_etf_universe_benchmark_shortlist_boundary.md).
It is documentation-only and defines non-approving ETF universe principles,
candidate buckets and examples, benchmark/cash proxy candidates, alignment
requirements, rejection criteria, relationship to prior gates, recommended
next routing, explicit non-goals, and remaining blockers. It does not approve
a universe, benchmark, cash proxy, source, methodology, parameters,
reproduction, validation, implementation, or trading implication.

Phase 33 Step 7 adds the broad-ETF data-source terms/license review boundary
in
[`docs/design/phase33_broad_etf_data_source_terms_license_review_boundary.md`](design/phase33_broad_etf_data_source_terms_license_review_boundary.md).
It is documentation-only and reviews public terms, license, caching,
private-repo, redistribution, derived-publication, API, and offline-use
constraints for Stooq, Yahoo Finance / yfinance / Yahoo API terms, Nasdaq Data
Link, Alpha Vantage, FRED, ETF issuer pages, and broker historical data as
context only. It does not provide legal advice or approve a source, universe,
benchmark, cash proxy, methodology, data acquisition, reproduction,
validation, implementation, or trading implication.

Phase 33 Step 8 adds the broad-ETF final source shortlist decision boundary in
[`docs/design/phase33_broad_etf_final_source_shortlist_decision_boundary.md`](design/phase33_broad_etf_final_source_shortlist_decision_boundary.md).
It is documentation-only and routes Stooq as a possible primary planning
candidate, Yahoo/yfinance as secondary/check or unresolved and not default,
Nasdaq Data Link and Alpha Vantage as secondary/check only, FRED as a
cash/risk-free proxy candidate, ETF issuer pages as metadata/context only, and
broker historical data as context only and not default. It approves no source,
data, universe, benchmark, cash proxy, methodology, acquisition,
reproduction, validation, implementation, or trading implication.

Phase 34 Step 1 adds the external research integration boundary in
[`docs/design/phase34_external_research_integration_boundary.md`](design/phase34_external_research_integration_boundary.md).
It is documentation-only and defines how Perplexity, Claude/Gemini, Codex,
QuantConnect, vectorbt, notebooks, vendor/public data, external research,
spreadsheets, and ad hoc analysis may support scout research, critique,
proposals, and prototype notes without becoming source-of-truth artifacts,
production dependencies, normal pytest inputs, validated artifacts, validated
signal definitions, or trading-path behavior.

The deterministic core must not directly depend on notebooks, research scripts,
backtesting engines, exploratory data-mining tools, live data ingestion, ML
training workflows, or LLM clients. LLMs may assist with research narration,
experiment summaries, hypothesis generation, journaling, and explaining
completed evaluation reports, but must not compute live signal outputs,
generate live trade decisions, mutate execution plans, approve orders, bypass
risk checks, access live broker or quote state in the trading process,
interact with brokers, or enter the trading hot path. Broker behavior remains
isolated behind broker boundaries.

## Local Order-Event Ledger

The local ledger records what happened during deterministic broker/order flows.

Current ledger event types:

- `order_submitted`
- `order_rejected`
- `order_filled`
- `order_not_filled`
- `portfolio_updated`
- `reconciliation_checked`

`LocalBroker` can use the ledger when one is supplied. It records submission
attempts, missing-risk or rejected-risk submissions, fills, no-fills, and
portfolio updates only when fills occur. If no ledger is supplied, existing
broker behavior is preserved.

Ledger modes:

- `InMemoryLedger`: fast local in-memory event history for tests and flows.
- `JsonlLedger`: append-only JSONL event history that survives process exit.

`JsonlLedger` behavior:

- Appends one JSON object per line.
- Serializes timestamps using `isoformat()`.
- Reads events back in order.
- Filters events by `order_id`.
- Returns no events for a missing file.
- Raises `ValidationError` on malformed ledger lines.

## Explicitly Not Included

- Database
- SQLite migrations
- Alpaca implementation
- Alpaca credentials
- Network calls
- Broker API calls
- Websocket fills
- Screener-driven order generation
- Screener wiring into risk or execution
- Approved or submitted trades from screener signal evaluation
- Real execution-planning policy decisions beyond no-op pass-through and the
  max-intents cap
- Accepted/rejected/skipped execution-planning policy logic beyond the
  max-intents cap
- Accepted/rejected/skipped execution-planning decisions beyond the max-intents
  cap
- Direct ExecutionPlan order/risk/status convenience fields
- Execution-intent broker routing or adapter integration
- Broker-facing request construction
- Order submission
- Client order ID generation
- Idempotency implementation
- Batch cash reservation
- Buying-power reservation
- Same-symbol execution conflict handling
- Duplicate or competing order policy implementation
- Priority or ranking policy implementation
- Scoring, direction, confidence, or actionability semantics unless explicitly
  designed and scoped
- Research/backtesting outputs as direct trading logic
- Notebooks or exploratory scripts in the deterministic core
- Validated artifact metadata as signal generation
- Validated artifact metadata as risk approval
- Validated artifact persistence implementation
- Validated signal definitions as live signal outputs
- Validated signal definitions as execution decisions
- Validated signal definitions as broker orders
- Validated signal definitions as execution intents
- Validated signal definitions as risk approvals
- Signal evaluation input snapshots as signal computation
- Signal evaluation input snapshots as live data access
- Signal evaluation input snapshots as risk approvals
- Signal evaluation input snapshots as execution intents or execution plans
- Signal evaluation outputs as orders
- Signal evaluation outputs as risk approvals
- Signal evaluation outputs as execution intents or execution plans
- SignalEvaluationResult behavior beyond minimal advisory metadata
- Signal evaluator implementation beyond the minimal no-op metadata boundary
- Real signal evaluator implementation
- Evaluator protocol
- No-op marker on SignalEvaluationResult
- Signal evaluator registry
- Signal computation from validated signal definitions
- Signal input bundle completeness behavior beyond minimal metadata-only name
  validation
- Strict extra-input rejection for signal input bundle completeness validation
- Snapshot id or `as_of` compatibility enforcement for signal input bundle
  completeness validation
- Signal input bundle behavior beyond minimal grouping, tuple coercion,
  duplicate-name rejection, and lookahead validation
- Real evaluator consumption of SignalInputBundle
- First real evaluator implementation
- Evaluator behavior beyond the Phase 29 Step 6 constants/output semantics
  design
- Threshold evaluator behavior beyond the Phase 30 Step 1 research-support
  boundary
- Threshold evaluator behavior beyond the Phase 30 Step 2 research validation
  evidence standard
- Threshold evaluator behavior beyond the Phase 30 Step 3 research artifact
  review template
- Threshold evaluator behavior beyond the Phase 30 Step 4 research artifact
  sourcing plan
- Threshold evaluator behavior beyond the Phase 30 Step 5 unreviewed research
  candidate backlog
- Threshold evaluator behavior beyond the Phase 30 Step 6 first candidate
  source selection
- Threshold evaluator behavior beyond the Phase 31 Step 2 research-track next
  action plan
- Threshold evaluator behavior beyond the Phase 31 Step 3 source package
  normalization
- Threshold evaluator behavior beyond the Phase 31 Step 4 Tier A formal source
  review
- Threshold evaluator behavior beyond the Phase 31 Step 5 evidence gap and
  routing plan
- Threshold evaluator behavior beyond the Phase 31 Step 6 mechanics-only
  candidate artifact review summary
- Threshold evaluator behavior beyond the Phase 31 Step 7 final mechanics-only
  disposition and next-candidate routing
- Threshold evaluator behavior beyond the Phase 32 Step 1 dataset-specific
  validation candidate selection
- Threshold evaluator behavior beyond the Phase 32 Step 2 P30-BL-002 source
  package sourcing plan
- Threshold evaluator behavior beyond the Phase 32 Step 3 P30-BL-002 source
  package collection attempt
- Threshold evaluator behavior beyond the Phase 32 Step 4 P30-BL-002 primary
  source verification gate
- Threshold evaluator behavior beyond the Phase 32 Step 5 P30-BL-002 limited
  formal review intake plan
- Threshold evaluator behavior beyond the Phase 32 Step 6 P30-BL-002-S01
  limited negative-control/no-lookahead formal review
- Threshold evaluator behavior beyond the Phase 32 Step 7 P30-BL-002-S03
  limited negative-control/data-snooping/OOS guardrail formal review
- Threshold evaluator behavior beyond the Phase 32 Step 8 P30-BL-002-S08
  methodology-only PIT formal review
- Threshold evaluator behavior beyond the Phase 32 Step 9 P30-BL-002-S05
  limited candidate-evidence planning formal review
- Threshold evaluator behavior beyond the Phase 32 Step 10 P30-BL-002 source
  status index
- Threshold evaluator behavior beyond the Phase 32 Step 11 S05 deterministic
  reproduction planning boundary
- Threshold evaluator behavior beyond the Phase 32 Step 12 S05 data
  availability assessment boundary
- Threshold evaluator behavior beyond the Phase 32 Step 13 S05 data
  provider/source comparison plan
- Threshold evaluator behavior beyond the Phase 32 Step 14 S05 data provider
  scout research normalization
- Threshold evaluator behavior beyond the Phase 32 Step 15 S05 primary
  verification questionnaire
- Threshold evaluator behavior beyond the Phase 32 Step 16 S05 public
  documentation verification sweep
- Threshold evaluator behavior beyond the Phase 32 Step 17 S05
  public-documentation-only feasibility decision
- Threshold evaluator behavior beyond the Phase 32 Step 18 S05 non-exact proxy
  reproduction boundary
- Threshold evaluator behavior beyond the Phase 32 Step 19 S05 proxy route
  selection boundary
- Threshold evaluator behavior beyond the Phase 32 Step 20 S05 route-neutral
  proxy dataset requirements boundary
- Threshold evaluator behavior beyond the Phase 32 Step 21 S05 proxy source
  shortlist and backlog routing decision
- Threshold evaluator behavior beyond the Phase 33 Step 1 easier-data research
  candidate selection boundary
- Threshold evaluator behavior beyond the Phase 33 Step 2 broad-ETF
  moving-average source package
- Threshold evaluator behavior beyond the Phase 33 Step 3 broad-ETF data
  feasibility, universe, and benchmark boundary
- Threshold evaluator behavior beyond the Phase 33 Step 4 broad-ETF
  public-source documentation verification sweep
- Threshold evaluator behavior beyond the Phase 33 Step 5 broad-ETF
  methodology and no-lookahead/as-of review boundary
- Threshold evaluator behavior beyond the Phase 33 Step 6 broad-ETF universe
  and benchmark/cash proxy shortlist boundary
- Threshold evaluator behavior beyond the Phase 33 Step 7 broad-ETF
  data-source terms/license review boundary
- Threshold evaluator behavior beyond the Phase 33 Step 8 broad-ETF final
  source shortlist decision boundary
- Threshold evaluator behavior beyond the Phase 34 Step 1 external research
  integration boundary
- Threshold evaluator behavior beyond the Phase 34 Step 2 external research
  artifact intake checklist
- Threshold evaluator behavior beyond the Phase 34 Step 3 notebook/prototype
  policy boundary
- Threshold evaluator behavior beyond the Phase 33 Step 9 broad-ETF data
  storage and fixture policy boundary
- Threshold evaluator behavior beyond the Phase 33 Step 10 broad-ETF
  moving-average evidence source package
- Threshold evaluator behavior beyond the Phase 33 Step 11 broad-ETF
  moving-average evidence intake plan
- Threshold evaluator behavior beyond the Phase 33 Step 12 broad-ETF evidence
  source collection normalization
- Threshold evaluator behavior beyond the Phase 33 Step 13 broad-ETF primary
  evidence text intake normalization
- Threshold evaluator behavior beyond the Phase 33 Step 14 broad-ETF primary
  citation verification normalization
- Threshold evaluator behavior beyond the Phase 33 Step 15 broad-ETF Faber
  limited formal evidence review
- Threshold evaluator behavior beyond the Phase 33 Step 16 broad-ETF
  `ETF-ACADEMIC-001` limited formal evidence review
- Threshold evaluator behavior beyond the Phase 33 Step 17 broad-ETF
  methodology evidence synthesis boundary
- Threshold evaluator behavior beyond the Phase 33 Step 18 broad-ETF
  reproduction readiness checklist
- Threshold evaluator behavior beyond the Phase 33 Step 19 broad-ETF
  source/universe/benchmark decision-readiness boundary
- Threshold evaluator behavior beyond the Phase 33 Step 20 broad-ETF
  return-construction boundary
- Threshold evaluator behavior beyond the Phase 33 Step 21 broad-ETF
  no-lookahead/as-of protocol boundary
- Threshold evaluator behavior beyond the Phase 33 Step 22 broad-ETF
  survivorship/inception/delisting boundary
- Threshold evaluator behavior beyond the Phase 33 Step 23 broad-ETF
  cash/benchmark return treatment boundary
- System clock implementation
- Feature computation
- Strategy engine
- Signal-evaluation-to-risk bridge
- Ranking or priority policy for signal evaluations
- Input snapshot persistence implementation
- Live data ingestion
- ML training implementation
- Persistence writes
- Audit logging writes
- Reconciliation loop against external broker state
- Scheduler or runtime loop
- LangGraph
- ML models
- LLM logic in the trading path
- Live trading

## Next Recommended Phase

Future Codex prompts should start from
[`docs/agent_context/codex_operating_context.md`](agent_context/codex_operating_context.md)
plus the relevant phase/design docs, especially
[`docs/design/phase31_research_track_next_action_plan.md`](design/phase31_research_track_next_action_plan.md)
for research-track work. Docs-only research and planning phases may combine
related updates when they are low-risk and code-free. Any production source
phase should stay narrow, test-first, explicitly scoped, and heavily verified.

Future threshold-evaluator work should continue by sourcing exact research and
signal-definition support candidates for later review against the Phase 30
Step 2 evidence standard and Phase 30 Step 3 review template. Phase 32 Step 11
adds a docs-only deterministic reproduction planning boundary for
`P30-BL-002-S05`; Phase 32 Step 12 adds a docs-only data availability
assessment boundary; Phase 32 Step 13 adds a docs-only data-provider/source
comparison plan; Phase 32 Step 14 normalizes external scout research as
unverified routing input; Phase 32 Step 15 adds a primary-verification
questionnaire and manual outreach template; Phase 32 Step 16 records a
public-documentation verification sweep with cautious feasibility labels and
direct-confirmation gaps; Phase 32 Step 17 records the owner decision to avoid
vendor/source contact for now and keeps S05 only as a public-doc-supported
proxy/partial planning candidate; Phase 32 Step 18 defines a non-exact proxy
reproduction boundary for methodology mechanics and research workflow testing
only; Phase 32 Step 19 compares proxy route options and keeps multiple routes
under consideration without selecting a provider, dataset, schema,
reproduction, validation, or implementation route; Phase 32 Step 20 defines
route-neutral proxy dataset requirements before any future route narrowing; and
Phase 32 Step 21 records a non-approving proxy source shortlist plus backlog
routing decision. None of these steps reproduce, validate, approve, select a
vendor, acquire data, or implement S05. The next practical research action
after Phase 32 Step 21 is to keep S05 in backlog and evaluate an easier-data
candidate unless future vendor contact, budget/access change, stronger public
documentation, or owner preference materially changes the S05 route. S01 and
S03 remain negative-control support only, S08 remains methodology-only PIT
support only, and S05 remains limited to candidate-evidence planning unless a
later phase resolves the named blockers.

Phase 33 Step 1 adds that easier-data candidate selection boundary and routes
the next research work toward a docs-only source package for the selected
easier-data candidate, starting with simple moving-average trend-following on
broad ETFs. That gate must still avoid data acquisition, ingestion, schema
design, backtesting, reproduction, evaluator behavior, signal computation,
validated artifacts, validated signal definitions, and trading implications.
Additional sourcing or a better P0 replacement remains appropriate if
unresolved source gaps block review-readiness. Tier B review may still provide
context later, but validation, real evaluator behavior, signal computation,
test scaffolds for implementation, and wiring signal output into risk remain
blocked until those gates are explicitly resolved.

Phase 33 Step 2 adds the broad-ETF moving-average source package. It prepares
source review only by recording the bounded research question, possible broad
ETF categories, high-level methodology framing, candidate-only public/easy
data-source categories, source-quality requirements, later evidence sources,
docs-only review gates, explicit non-goals, and remaining blockers. It does
not approve an ETF universe, data source, dataset, benchmark, parameter,
signal definition, schema, reproduction, validation, implementation, or
trading implication.

Phase 33 Step 3 adds the broad-ETF data feasibility, universe, and benchmark
boundary. It groups source feasibility, future ETF universe requirements, and
future benchmark/cash proxy requirements for the selected easier-data
candidate. It recommends a docs-only public-source documentation verification
sweep before methodology review. It does not approve data, a universe, a
benchmark, a cash proxy, methodology, reproduction, validation,
implementation, or trading implication.

Phase 33 Step 4 adds the broad-ETF public-source documentation verification
sweep. It normalizes public documentation and external scout-report input for
candidate source categories, records cautious feasibility labels, and routes
next work toward a methodology-only moving-average review, no-lookahead/as-of
review, or ETF universe shortlist boundary. It does not approve a source,
universe, benchmark, cash proxy, data, methodology, reproduction, validation,
implementation, or trading implication.

Phase 33 Step 5 adds the broad-ETF methodology and no-lookahead/as-of review
boundary. It defines what any later methodology review must cover and what
no-lookahead/as-of constraints must hold before future reproduction or
implementation work. It routes the next docs-only gate toward an ETF universe
shortlist boundary. It does not approve methodology, parameters, data, a
universe, benchmark, cash proxy, reproduction, validation, implementation, or
trading implication.

Phase 33 Step 6 adds the broad-ETF universe and benchmark/cash proxy shortlist
boundary. It records candidate-only universe principles, ETF buckets and
examples, benchmark/cash proxy candidates, alignment requirements, rejection
criteria, and next routing. It does not approve a universe, benchmark, cash
proxy, source, methodology, parameters, reproduction, validation,
implementation, or trading implication.

Phase 33 Step 7 adds the broad-ETF data-source terms/license review boundary.
It records public terms/license/offline-use constraints, cautious terms-risk
labels, source-specific cautions, required conclusions, recommended next
routing, explicit non-goals, and remaining blockers. It does not provide legal
advice or approve a source, universe, benchmark, cash proxy, methodology,
parameters, data acquisition, reproduction, validation, implementation, or
trading implication.

Phase 33 Step 8 adds the broad-ETF final source shortlist decision boundary.
It records cautious final source routing labels, routes Stooq as a possible
primary planning candidate, Yahoo/yfinance as secondary/check or unresolved
and not default, Nasdaq Data Link and Alpha Vantage as secondary/check only,
FRED as a cash/risk-free proxy candidate, ETF issuer pages as metadata/context
only, and broker historical data as context only and not default. It recommends
a docs-only data storage/fixture policy boundary next and does not approve a
source, data, universe, benchmark, cash proxy, methodology, acquisition,
reproduction, validation, implementation, or trading implication.

Phase 34 Step 1 adds the external research integration boundary. It recommends
a docs-only external research artifact intake checklist next and keeps
Perplexity, Claude/Gemini, Codex, QuantConnect, vectorbt, notebooks,
vendor/public data, external research, spreadsheets, and ad hoc analysis as
advisory inputs only. It does not approve any external integration,
dependency, notebook, data, source, reproduction, validation, implementation,
validated artifact, validated signal definition, production threshold, or
trading implication.

Phase 34 Step 2 adds that external research artifact intake checklist. It
records required metadata, evidence labels, review questions, routing outcomes,
promotion constraints, repository placement rules, and a reusable markdown
template for future external research artifacts. It recommends a docs-only
notebook/prototype policy boundary next and does not approve any external
artifact, notebook, vendor/public data source, dependency, reproduction,
implementation, validated artifact, validated signal definition, production
threshold, or trading implication.

Phase 34 Step 3 adds that notebook/prototype policy boundary. It records safe
exploratory uses, forbidden uses, required metadata, promotion path,
repository placement policy, vectorbt and QuantConnect boundaries, normal
pytest rules, explicit non-goals, and remaining blockers for notebooks,
prototype scripts, vectorbt experiments, QuantConnect outputs, spreadsheets,
CSV extracts, charts, external reports, and copied snippets. It recommends
returning to the Phase 33 data storage/fixture policy boundary and does not
approve notebooks, scripts, dependencies, data acquisition, ingestion,
reproduction, backtests, vectorbt or QuantConnect integration, validated
artifacts, validated signal definitions, production thresholds, or trading
implications.

Phase 33 Step 9 adds that broad-ETF data storage and fixture policy boundary.
It defines non-approving handling rules for raw third-party price data,
downloaded CSV/API snapshots, issuer metadata, FRED cash/risk-free series,
manual metadata, tiny synthetic fixtures, tiny derived fixtures, manifests,
provenance records, charts/results, and notebook/prototype outputs. It also
compares possible future storage policies, fixture requirements,
provenance/manifest requirements, local-only data boundaries, Phase 34
relationships, terms/license constraints, future gates, non-goals, and
remaining blockers. It does not approve a source, ETF universe, benchmark,
cash proxy, methodology, parameter, final storage policy, data acquisition,
data files, fixtures, reproduction, validation, implementation, evaluator
behavior, signal computation, or trading implication.

Phase 33 Step 10 adds the broad-ETF moving-average evidence source package.
It identifies evidence categories, evidence-quality standards, review
questions, a candidate evidence intake table, non-claims, relationships to
prior Phase 33 gates, a recommended evidence-intake-plan gate, explicit
non-goals, and remaining blockers. It does not approve evidence, methodology,
parameters, source data, an ETF universe, benchmark, cash proxy, reproduction,
validation, implementation, evaluator behavior, signal computation, or trading
implication.

Phase 33 Step 11 adds the broad-ETF moving-average evidence intake plan. It
defines source priority, intake workflow, disposition vocabulary, rejection
criteria, review sequence, a required intake table, Phase 34 relationships, a
recommended first limited methodology evidence review gate, explicit
non-goals, and remaining blockers. It does not review or approve evidence,
methodology, parameters, source data, an ETF universe, benchmark, cash proxy,
reproduction, validation, implementation, evaluator behavior, signal
computation, or trading implication.

Phase 33 Step 12 adds the broad-ETF evidence source collection normalization.
It converts the externally supplied Perplexity moving-average source list into
the project intake trail, separates academic/formal, ETF-specific,
practitioner, benchmark/friction, bias-control, context-only, and unsupported
direct-evidence sources, identifies strongest later review candidates, records
required follow-up and provisional grading labels, and recommends pausing
until full primary texts are available. It does not approve evidence,
methodology, parameters, source data, an ETF universe, benchmark, cash proxy,
reproduction, validation, implementation, evaluator behavior, signal
computation, or trading implication.

Phase 33 Step 13 adds the broad-ETF primary evidence text intake
normalization. It records the second Perplexity source-gathering report as
external scout material, normalizes reported primary-text availability for
`ETF-ACADEMIC-001`, `MA-PRACT-001`, unresolved `MA-ACADEMIC-001`, and related
Zakamulin/SSRN-style candidates, records citation-quality cautions, and
recommends pausing until primary text and citation verification is complete.
It does not approve evidence, methodology, parameters, data, an ETF universe,
benchmark, cash proxy, reproduction, validation, implementation, evaluator
behavior, signal computation, or trading implication.

Phase 33 Step 14 adds the broad-ETF primary citation verification
normalization. It records the externally supplied Perplexity verification
report as scout material, normalizes citation metadata for Faber,
`ETF-ACADEMIC-001`, the unresolved "Simple Market Timing with Moving Averages"
label, `ZAKAMULIN-2014`, `ZAKAMULIN-2016`, and optional Zakamulin SSRN leads,
and separates verified source identity from evidence approval. It recommends a
conservative later limited formal review of Faber only after the open PDF and
SSRN metadata are verified in the repo trail. It does not approve evidence,
methodology, parameters, data, an ETF universe, benchmark, cash proxy,
reproduction, validation, implementation, evaluator behavior, signal
computation, or trading implication.

Phase 33 Step 15 adds the broad-ETF Faber limited formal evidence review. It
reviews Mebane T. Faber's "A Quantitative Approach to Tactical Asset
Allocation" as methodology and practitioner/TAA context only, records source
identity, SSRN ID 962461, author-hosted PDF and SSRN access status, the
monthly 10-month SMA rule framing, broad index asset classes, total-return
and cash treatment, buy-and-hold comparison framing, parameter-stability
discussion, practical friction caveats, index-proxy/ETF-inception limits,
transferability limits, cautious disposition labels, required follow-up, and
remaining blockers. It recommends ETF-ACADEMIC-001 full-text verification /
limited review if accessible. It does not approve evidence, methodology,
parameters, data, an ETF universe, benchmark, cash proxy, reproduction,
validation, implementation, evaluator behavior, signal computation, or
trading implication.

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
decision areas for dividends and distributions, splits and corporate actions,
adjusted-data transparency, expenses, cash/T-bill returns, benchmark
comparability, compounding, ETF inception alignment, missing/stale data,
frequency alignment, no-lookahead/as-of timing, and timing/action-date
implications. It keeps return construction blocked for approval and
recommends a docs-only no-lookahead/as-of protocol boundary next. It does not
approve a return basis, source, universe, benchmark, cash proxy, methodology,
parameter, data policy, reproduction protocol, implementation, signal
definition, evaluator, or trading implication.

Phase 33 Step 21 adds the broad-ETF no-lookahead/as-of protocol boundary. It
defines the core as-of principle, timing concepts for observation, decision,
action, effective trade date, close-to-close, next-open, next-close, monthly
rebalance, cash-rate observation, dividend/distribution dates, and
publication/revision timestamps, and records unresolved moving-average signal
timing, adjusted-data, total-return, cash, benchmark, ETF inception, and
delisting constraints. It keeps no-lookahead/as-of protocol approval blocked
and recommends a docs-only survivorship/inception/delisting boundary next. It
does not approve timing, return construction, source, universe, benchmark,
cash proxy, methodology, parameter, data policy, reproduction protocol,
implementation, signal definition, evaluator, or trading implication.

Phase 33 Step 22 adds the broad-ETF survivorship/inception/delisting boundary.
It defines the core pre-result universe principle and records unresolved
requirements for ETF inception dates, first usable observations,
inactive/delisted ETF history, survivorship bias, symbol identity, ticker
changes, fund mergers, closures, issuer metadata, universe membership timing,
source coverage, and the relationship to return construction and
no-lookahead/as-of timing. It keeps survivorship/inception/delisting policy
approval blocked and recommends a docs-only cash/benchmark return treatment
boundary next. It does not approve an ETF universe, source, benchmark, cash
proxy, return construction, no-lookahead/as-of protocol, methodology,
parameter, data policy, reproduction protocol, implementation, signal
definition, evaluator, or trading implication.

Phase 33 Step 23 adds the broad-ETF cash/benchmark return treatment boundary.
It scopes unresolved benchmark comparison candidates, cash/T-bill proxy
candidates, benchmark return basis, cash-return conversion and compounding,
daily/monthly frequency alignment, ETF signal cadence versus benchmark/cash
cadence, date alignment, FRED publication/revision/as-of timing,
non-trading-day treatment, out-of-market cash treatment, zero-return
placeholder limits, required future approval criteria, and the relationship to
return construction, no-lookahead/as-of timing, survivorship/inception/
delisting, source shortlist, universe/benchmark shortlist, and
storage/fixture policy gates. It keeps cash/benchmark return treatment
approval blocked and recommends a docs-only cost/friction assumptions
boundary next. It does not approve a benchmark, cash proxy, cash-rate series,
source, universe, return construction, no-lookahead/as-of protocol,
survivorship/inception/delisting policy, methodology, parameter, data policy,
reproduction protocol, implementation, signal definition, evaluator, or
trading implication.

Phase 35 Step 1 adds the default pytest network kill-switch. It patches
`socket.socket` and `socket.create_connection` during normal pytest
configuration so accidental network access fails loudly before any broker,
vendor, SDK, notebook, research, runtime, or trading path can make a socket.
The explicit escape hatches are `--allow-network` and
`ALGO_TRADER_ALLOW_NETWORK_TESTS=1`, reserved for future explicitly gated
integration tests only. Existing paper integration tests remain skipped by
default, and this step adds no source, broker, runtime, data, signal,
evaluator, portfolio, or trading behavior.

Phase 35 Step 2 adds the synthetic-only return construction / as-of mechanics
kernel in `algotrader.research.return_construction`. It provides arithmetic
`simple_return`, immutable close-to-close return tuple construction from
synthetic `Decimal` values, and lagged observation/action-date pairs from
strictly increasing synthetic `date` inputs. The lag examples use a simple
calendar-day offset only and make no trading-calendar, execution-calendar,
same-day execution, next-open, next-close, rebalance, or data-availability
claim. The kernel rejects malformed inputs, non-`Decimal` return inputs,
non-positive prior values, unordered or duplicate observation dates, and
negative lag values.

This kernel is mechanical only. It does not approve or implement real market
data, vendor data, data downloads, data files, adjusted-close logic,
total-return logic, dividends, splits, cash returns, benchmark returns, costs,
frictions, moving-average rules, strategies, signals, evaluators, backtests,
portfolio mutation, order generation, broker behavior, runtime behavior,
notebooks, vectorbt, QuantConnect, ML, LLM trading-path logic, validated
research artifacts, validated signal definitions, profitability claims,
validation claims, implementation-readiness claims, production thresholds, or
trading-readiness claims.

Phase 35 Step 3 adds the metadata-only fixture manifest contract in
`algotrader.research.fixture_manifest`. `ResearchFixtureManifest` is a frozen
slotted dataclass that records only provenance fields such as fixture identity,
fixture kind, source name/type, optional plain dates, field names, checksum,
normal-pytest eligibility, redistribution safety, limitations, and non-claims.
It supports synthetic fixtures, derived fixtures, and local-only snapshot
manifests as metadata categories only.

The manifest validates non-empty required strings, allowed fixture kinds and
source types, plain `date` values instead of `datetime`, ordered data date
ranges, immutable tuple fields, plain boolean flags, and normal-pytest
eligibility. A fixture can be normal-pytest eligible only when it is
redistribution-safe and does not use local-only, third-party, or local-snapshot
source categories. Local-only manifests and third-party raw-data manifests are
therefore metadata records only and remain outside normal pytest fixtures.

This contract does not add data files, data downloads, data acquisition, data
ingestion, vendor access, public data, source approval, ETF universe approval,
benchmark approval, cash-proxy approval, backtests, strategies, signal
evaluators, portfolio mutation, order generation, broker behavior, runtime
behavior, notebooks, scripts, `ValidatedResearchArtifact`,
`ValidatedSignalDefinition`, profitability claims, validation claims,
production thresholds, or trading-readiness claims.

Phase 36 adds the synthetic-only as-of replay kernel in
`algotrader.research.asof`. `AsofObservation` is a frozen slotted dataclass with
only `observation_date` and `available_after` plain `date` fields.
`iter_asof_available` returns an immutable tuple of observations whose
`available_after` date is on or before the requested as-of date while preserving
the input order, and `next_available_asof_date` returns the earliest
availability date from a non-empty observation sequence.

The as-of kernel validates plain `date` values only, rejects `datetime`, bool,
date subclasses, non-date values, malformed observation objects, duplicate
observation dates, unordered observation-date sequences, availability dates
before observation dates, non-date as-of values, and empty sequences where the
next available date is requested. It stays offline-safe and deterministic; it
does not add pandas, numpy, vectorbt, QuantConnect, broker/runtime/scheduler
logic, portfolio mutation, backtesting, signal evaluator logic, real-data
ingestion, ML, LLM usage, network access, source approval, validation claims,
or trading-path behavior.

Phase 37 adds metadata-only serialization helpers to
`ResearchFixtureManifest`. `to_dict()` returns a deterministic
JSON-compatible dictionary containing exactly the existing manifest metadata
fields, with optional plain dates serialized as `YYYY-MM-DD` strings and tuple
fields serialized as lists. `from_dict(...)` accepts only strict manifest
metadata dictionaries, rejects unknown fields and missing required fields,
parses only strict ISO calendar-date strings back to plain `date` values, and
restores list fields as immutable tuples before running the existing manifest
validation.

The serialization contract preserves normal-pytest eligibility restrictions
for local-only, third-party, and local-snapshot raw fixture categories. It does
not add JSON file persistence, file reads or writes, raw data loading, vendor
dependencies, real data ingestion, source approval, pandas, numpy, yfinance,
vectorbt, QuantConnect, network access, credentials, broker/runtime/scheduler
logic, backtesting, signal/evaluator behavior, portfolio mutation, order
generation, ML, LLM usage, validation claims, profitability claims,
trading-readiness claims, or trading-path behavior.

Phase 38 adds `algotrader.research.replay` as a tiny deterministic synthetic
replay snapshot package. `SyntheticReplayPoint` pairs one existing
`AsofObservation` with one synthetic `Decimal` value. `SyntheticReplaySnapshot`
records the manifest, as-of date, available points, and close-to-close returns
as immutable metadata only.

`build_synthetic_replay_snapshot(...)` validates the manifest, plain as-of
date, and replay point sequence; delegates duplicate and unordered observation
date rejection to the existing as-of kernel; filters by `available_after` with
no lookahead; preserves the original chronological point order and available
point object identity; and delegates multi-point return construction to
`close_to_close_returns(...)`. Zero or one available point is allowed and yields
an empty returns tuple. Snapshot serialization is dictionary-only metadata:
manifest metadata, ISO `YYYY-MM-DD` dates, available point dictionaries, and
Decimal values/returns as strings.

This package does not add file I/O, JSON file persistence, pandas, numpy,
yfinance, vectorbt, QuantConnect, real data ingestion, network access,
backtesting, strategy logic, signal/evaluator behavior, broker/runtime/
scheduler behavior, portfolio mutation, order generation, ML, LLM usage,
validation claims, profitability claims, trading-readiness claims, or
trading-path behavior.

Phase 39 adds `algotrader.research.replay_metrics` as a tiny descriptive
summary layer over existing `SyntheticReplaySnapshot` outputs.
`SyntheticReplaySummary` is a frozen slotted dataclass containing point and
return counts, optional starting and ending values, optional cumulative simple
return, and optional min/max/mean returns. `summarize_synthetic_replay_snapshot`
requires a `SyntheticReplaySnapshot` and reads only `available_points` and
`returns`.

Empty snapshots produce zero counts and `None` value/return metrics. One-point
snapshots report starting and ending values but no return-derived metrics.
Snapshots with returns report return count, min return, max return, arithmetic
mean return, and cumulative simple return as ending divided by starting, minus
one. `SyntheticReplaySummary.to_dict()` emits JSON-compatible primitive
metadata, preserving counts as integers, `None` as `None`, and Decimal values
as strings.

This summary layer is descriptive only. It does not imply strategy validity,
profitability, research validation, backtest approval, benchmark comparison,
source approval, trading-readiness, or production readiness. It adds no file
I/O, JSON file persistence, pandas, numpy, yfinance, vectorbt, QuantConnect,
real data ingestion, network access, broker/runtime/scheduler behavior,
signal/evaluator behavior, portfolio mutation, order generation, ML, LLM usage,
or trading-path behavior.

Phase 40 adds `algotrader.research.replay_result` as a tiny metadata-only
result package over the existing synthetic replay snapshot and summary layers.
`SyntheticResearchResult` is a frozen slotted dataclass containing exactly a
`SyntheticReplaySnapshot` and a `SyntheticReplaySummary`.
`build_synthetic_research_result(...)` requires a `SyntheticReplaySnapshot`,
computes the summary with `summarize_synthetic_replay_snapshot(...)`, and
preserves the original snapshot object identity.

`SyntheticResearchResult.to_dict()` emits deterministic JSON-compatible
metadata containing only `snapshot.to_dict()` and `summary.to_dict()`. Nested
Decimal serialization remains delegated to the existing serializers, so values
and returns remain strings. Direct construction rejects malformed snapshot and
summary objects, preserves immutability, and does not mutate the snapshot,
points, manifest, returns, or summary.

This result package is not a backtest result, benchmark result, strategy
result, signal-validation artifact, runtime artifact, or trading artifact. It
adds no file I/O, JSON file persistence, pandas, numpy, yfinance, vectorbt,
QuantConnect, real data ingestion, network access, broker/runtime/scheduler
behavior, signal/evaluator behavior, portfolio mutation, order generation, ML,
LLM usage, validation claims, profitability claims, trading-readiness claims,
or trading-path behavior.

Phase 41 adds `algotrader.research.workflow` as a thin synthetic research
workflow builder over the existing replay and result layers.
`build_synthetic_research_workflow_result(...)` accepts a
`ResearchFixtureManifest`, an iterable of `SyntheticReplayPoint` values, and an
explicit plain `date` as-of value. It builds a `SyntheticReplaySnapshot` by
delegating to `build_synthetic_replay_snapshot(...)`, then builds and returns a
`SyntheticResearchResult` by delegating to
`build_synthetic_research_result(...)`.

The workflow helper intentionally owns no duplicate replay, summary, or result
construction logic. Manifest validation, replay point validation, plain-date
as-of validation, duplicate and unordered observation rejection, no-lookahead
filtering, available-point return construction, zero/one-point behavior, and
summary behavior all remain owned by the existing builders. Serialization still
flows through `SyntheticResearchResult.to_dict()`, including nested manifest,
snapshot, and summary serialization with Decimal values rendered as strings.

This workflow is a metadata-only composition helper. It adds no file I/O, JSON
file persistence, pandas, numpy, yfinance, vectorbt, QuantConnect, real data
ingestion, network access, benchmark comparison, backtesting engine behavior,
broker/runtime/scheduler behavior, signal/evaluator behavior, portfolio
mutation, order generation, ML, LLM usage, strategy validation claims,
profitability claims, trading-readiness claims, or trading-path behavior.

Phase 42 adds `algotrader.research.external_intake` as a small metadata-only
intake contract for external research outputs. `ExternalResearchIntake` is a
frozen slotted dataclass that records source name and type, strategy name,
summary, universe, timeframe, assumptions, limitations, evidence links, a plain
`date` creation date, and an `advisory_only` flag that must be exactly `True`.
Allowed source types are limited to QuantConnect, vectorbt, notebooks,
Perplexity, Claude, Gemini, papers, manual notes, and other advisory sources.

The intake contract stores tuple fields as immutable tuples, rejects empty
strings, rejects unknown source types, requires plain `date` values instead of
`datetime`, bool, non-date values, or date subclasses, and preserves strict
advisory-only status. `to_dict()` emits deterministic JSON-compatible metadata
with tuples serialized as lists and `created_at` serialized as `YYYY-MM-DD`.
`from_dict(...)` accepts only strict metadata dictionaries, rejects unknown and
missing fields, parses only strict ISO calendar dates, restores tuple fields,
and reruns all validation.

This intake object is not a validated research artifact, strategy validation,
benchmark comparison, backtest result, signal input, evaluator input, broker
instruction, portfolio instruction, order instruction, result-metric carrier,
credential container, or runtime state. It adds no file I/O, JSON file
persistence, pandas, numpy, yfinance, vectorbt dependency, QuantConnect
dependency, real data ingestion, network access, benchmark comparison,
backtesting engine behavior, broker/runtime/scheduler behavior,
signal/evaluator behavior, portfolio mutation, order generation, ML, LLM usage,
strategy validation claims, profitability claims, trading-readiness claims, or
trading-path behavior.

Phase 43 confirms the research package now has two separate metadata-only
paths: an advisory external intake path for QuantConnect, vectorbt, notebooks,
Perplexity, Claude/Gemini, papers, and manual research, and a deterministic
synthetic local workflow path built from `ResearchFixtureManifest`,
`AsofObservation`, `SyntheticReplayPoint`, `SyntheticReplaySnapshot`,
`SyntheticReplaySummary`, `SyntheticResearchResult`, and
`build_synthetic_research_workflow_result(...)`.

These paths can coexist, but they remain intentionally distinct:
`ExternalResearchIntake` is not a `SyntheticResearchResult`, and
`SyntheticResearchResult` is not an `ExternalResearchIntake`. Neither path adds
file I/O, JSON file persistence, pandas, numpy, yfinance, vectorbt dependency,
QuantConnect dependency, real data ingestion, network access, benchmark
comparison, backtesting engine behavior, broker/runtime/scheduler behavior,
signal/evaluator behavior, portfolio mutation, order generation, ML, LLM
runtime usage, strategy validation claims, profitability claims,
trading-readiness claims, or trading-path behavior.

Phase 44 adds `algotrader.research.price_snapshot` as a deterministic local
CSV loader for daily historical price snapshots. `HistoricalPriceBar` and
`HistoricalPriceSnapshot` are frozen slotted dataclasses that normalize symbols,
require plain dates, preserve Decimal prices, reject malformed OHLC,
non-positive prices, bool volume values, symbol mismatches, duplicate dates,
unordered dates, and empty snapshots, and store bars as immutable tuples.

`load_historical_price_snapshot_csv(...)` reads exactly the supplied local CSV
path using stdlib `csv`, requires the columns `date`, `open`, `high`, `low`,
`close`, `adjusted_close`, and `volume`, allows an optional matching `symbol`
column, rejects unsupported extra columns, and performs no discovery or writes.
`price_snapshot_fingerprint(...)` produces a deterministic sha256 hex digest
from normalized primitive snapshot content without including file paths.

This utility is only a local snapshot loader and validator. Raw market data
remains out of git, with `.data/` reserved for ignored local snapshots such as
`.data/research_snapshots/`. It adds no pandas, numpy, yfinance, vectorbt,
QuantConnect, vendor SDK, API call, network access, ingestion pipeline,
benchmark comparison, backtesting engine, broker/runtime/scheduler behavior,
signal/evaluator behavior, portfolio mutation, order generation, ML, LLM
runtime usage, strategy validation claims, profitability claims,
trading-readiness claims, or trading-path behavior.

Phase 45 adds `algotrader.research.price_snapshot_manifest` as a metadata-only
manifest for pinned local historical price snapshots. `LocalPriceSnapshotManifest`
records source name/type, normalized symbol, file name, file sha256, snapshot
fingerprint, date range, row count, adjustment policy, creation date, strict
local-only status, normal-pytest ineligibility, and limitations.

`build_local_price_snapshot_manifest(...)` accepts an already validated
`HistoricalPriceSnapshot`, derives symbol, start date, end date, row count, and
the deterministic snapshot fingerprint, and combines them with caller-supplied
provenance metadata. It does not read files, load CSVs, persist JSON, inspect
local directories, include raw bar contents, include paths, or mutate snapshots
or bars. `to_dict()` and `from_dict(...)` round-trip JSON-compatible primitive
metadata with dates serialized as `YYYY-MM-DD` and limitations serialized as
lists.

This manifest is provenance metadata only. It adds no raw data, file I/O, JSON
file persistence, pandas, numpy, yfinance, vectorbt, QuantConnect, vendor SDK,
API call, network access, ingestion pipeline, benchmark comparison, backtesting
engine, broker/runtime/scheduler behavior, signal/evaluator behavior,
portfolio mutation, order generation, ML, LLM runtime usage, strategy
validation claims, profitability claims, trading-readiness claims, or
trading-path behavior.

Phase 46 adds `algotrader.research.daily_backtest` as a tiny deterministic
daily equity-curve utility over already-loaded `HistoricalPriceSnapshot` data
and precomputed `DailyExposure` values. `DailyBacktestAssumptions`,
`DailyExposure`, `DailyBacktestPoint`, and `DailyBacktestResult` are frozen
slotted dataclasses with strict plain-date and Decimal validation, immutable
point storage, exact snapshot/exposure date alignment, and deterministic
derived metrics for starting equity, ending equity, total return, maximum
drawdown, average exposure ratio, and turnover.

`run_daily_backtest(...)` uses adjusted close prices only, gives the first bar
an asset return of zero, applies prior-day exposure to today's asset return to
avoid same-day lookahead, charges first-day and later exposure-change costs from
caller-supplied fee/slippage basis points, and compounds a local equity curve
from the supplied initial equity. `DailyBacktestResult.to_dict()` serializes
dates as `YYYY-MM-DD`, Decimals as strings, assumptions as primitive metadata,
points as primitive dictionaries, and derived metrics without file data,
credentials, runtime state, order/fill fields, or profitability claims.

This utility is not a strategy framework or trading engine. It adds no file I/O,
CSV loading, JSON persistence, pandas, numpy, yfinance, vectorbt, QuantConnect,
vendor SDK, API call, network access, ingestion pipeline, benchmark comparison,
broker/runtime/scheduler behavior, signal/evaluator behavior, portfolio engine,
portfolio mutation outside the local equity curve calculation, order
generation, ML, LLM runtime usage, strategy validation claims, profitability
claims, trading-readiness claims, or trading-path behavior.

Phase 47 adds `algotrader.research.sma_exposure` as a deterministic
research-only SMA-200 exposure generator for the minimal daily backtest
harness. `build_sma_200_daily_exposures(...)` accepts an already validated
`HistoricalPriceSnapshot`, walks `snapshot.bars` in their existing
chronological order, uses adjusted close prices only, and returns one immutable
tuple of `DailyExposure` values aligned exactly to the snapshot bar dates.

The first 199 bars always receive `Decimal("0")`. Starting with the 200th bar,
the helper computes the arithmetic mean of the latest 200 adjusted close values,
including the current bar, and emits `Decimal("1")` only when the current
adjusted close is strictly greater than that trailing average. Equal or lower
prices emit `Decimal("0")`. The generated date-T exposure may use price data
available through date T; the daily backtest still applies that date-T exposure
only to the following asset return through its existing previous-exposure rule.

This helper is not a production signal evaluator, strategy framework, broker
instruction, portfolio engine, order generator, or validated strategy. It adds
no file I/O, CSV loading, JSON persistence, pandas, numpy, yfinance, vectorbt,
QuantConnect, vendor SDK, API call, network access, ingestion pipeline,
benchmark comparison, broker/runtime/scheduler behavior, signal/evaluator
behavior, portfolio engine, order generation, ML, LLM runtime usage, strategy
validation claims, profitability claims, trading-readiness claims, or
trading-path behavior.

Phase 48 adds `scripts/research/run_spy_sma200_research.py` as the first
local-only SPY SMA-200 research-run path. It requires an explicit CSV path,
accepts only optional local assumptions and provenance metadata, rejects CSV
paths outside `.data/research_snapshots/` unless an override flag is supplied,
computes a stdlib file sha256, builds a `LocalPriceSnapshotManifest`, builds
SMA-200 daily exposures plus a same-snapshot all-one buy-and-hold baseline,
runs the existing deterministic daily backtest for both paths, and renders a
markdown report to stdout unless an explicit non-`.data/` output path is
supplied. When a markdown output path is supplied, the runner also writes a
sibling deterministic JSON sidecar with sorted keys and no raw bar data.

The report contains an advisory-only disclaimer, source name/type, CSV file
name only, file sha256, snapshot fingerprint, date range, row count,
adjustment policy, assumptions, the SMA-200 rule, the buy-and-hold convention,
aggregate descriptive metrics, limitations, and a non-approval verdict. Return
metrics are labeled as price-return unless the snapshot adjustment policy is
explicitly `total_return`; the report presents numbers only and makes no
strategy outperformance claim. It never writes raw CSV rows into the report or
JSON sidecar and does not scan data directories or fetch data. The companion
`research/log/` README and template make research logs advisory-only and require
fingerprints/provenance before any local report is trusted.

This runner is not a production strategy, signal evaluator, benchmark
framework, broker/runtime system, portfolio engine beyond the existing local
equity curve, order generator, validated strategy, recommendation, or trading
workflow. It adds no raw committed market data, pandas, numpy, yfinance,
vectorbt, QuantConnect, vendor SDK, API call, network access, automatic data
discovery, benchmark comparison, broker/runtime/scheduler behavior, production
signal/evaluator behavior, order generation, ML, LLM runtime usage, strategy
validation claims, profitability claims, trading-readiness claims, or
trading-path behavior.

Phase 49 adds `scripts/research/fetch_alpaca_daily_snapshot.py` as an
explicitly gated local research utility for fetching daily OHLCV bars from the
Alpaca Market Data historical stock bars endpoint into ignored CSV snapshots
under `.data/research_snapshots/`. It requires explicit `--allow-network`,
explicit start and end dates, explicit output path, environment-only
credentials, default output-directory gating, and `--overwrite` before
replacing an existing CSV.

The fetcher writes exactly the `HistoricalPriceSnapshot` columns `date`,
`open`, `high`, `low`, `close`, `adjusted_close`, and `volume`; validates
malformed responses, missing OHLCV fields, duplicate or unordered dates,
non-positive prices, and negative volume; and computes a local CSV SHA-256. If
the API payload does not provide a separate adjusted close field, the script
writes `adjusted_close = close` and reports that adjustment-policy limitation
without claiming total-return accuracy.

This utility is a gated local snapshot convenience only. It adds no `src`
ingestion pipeline, pandas, numpy, yfinance, vectorbt, QuantConnect,
`alpaca-py` import, broker/trading API call, account/position/order/fill
access, order submission, scheduler/runtime service, production signal
evaluator, portfolio engine, ML/LLM runtime usage, strategy validation claim,
profitability claim, or trading behavior. Normal pytest remains offline and
credential-free, and unit tests use synthetic mocked payloads only.

Phase 45 - External SPY Price Parity Check adds
`scripts/research/check_spy_price_parity.py` as a local-only advisory utility.
It compares calendar-year close-price returns for overlapping years between an
explicit local snapshot CSV and an explicit manually supplied reference CSV,
reports local price return, reference price return, and basis-point
differences, and optionally writes only the markdown report. It fetches
nothing, commits no raw external data, adds no vendor abstraction, requires no
`.data/` path in tests, constructs no total-return series, handles no dividends
or corporate actions, validates no strategy, and makes no trading
recommendation.

Phase 45 - AI Operating Brief / Candidate Dossier Foundation adds
`algotrader.advisory.operating_brief` as a deterministic, metadata-only
contract layer for future AI operating briefs and candidate dossiers. It defines
immutable advisory labels, research candidate dossiers, strategy eligibility
metadata, risk authority metadata, and operating brief bundles that normalize
sequence inputs to tuples, reject malformed identifiers and non-string
uncertainty/failure-mode entries, and require explicit strategy and risk support
before paper, live-probe, or live-authorized labels can appear in a brief.

This phase adds no brief generator, AI prompt layer, LLM/API call, market-data
summary engine, strategy scorer, research evaluator, dashboard, broker access,
order/fill/execution/OMS/account/position/portfolio behavior, scheduler/runtime
behavior, persistence, real data, network calls, strategy validation claim,
trading recommendation, or mutation of capital-layer state.

Phase 46 - Advisory Operating Brief Serialization / Display Snapshot adds
deterministic `to_dict()` methods for the advisory dossier, strategy
eligibility, risk authority, and operating brief contracts. Serialization emits
plain dictionaries with JSON-compatible primitive values only: advisory labels
become strings, tuple fields become lists, nested advisory objects serialize
through their own primitive dictionaries, and operating brief dates serialize as
ISO `YYYY-MM-DD` strings. Repeated calls preserve deterministic ordering and do
not mutate source objects.

This phase adds no markdown report generation, dashboard code, AI prompt layer,
brief generator, market-data summary, strategy scoring, research evaluator,
alternate constructor, persistence, broker access, order/fill/execution/OMS
behavior, account/position/portfolio behavior, scheduler/runtime behavior,
LLM/API call, network call, market-data provider access, strategy validation
claim, trading recommendation, or capital-layer mutation.

Phase 47 - Deterministic Advisory Operating Brief Markdown Renderer adds
`algotrader.advisory.operating_brief_markdown.render_operating_brief_markdown`
as a deterministic display surface for an already constructed
`OperatingBrief`. The renderer accepts only an `OperatingBrief`, formats the
existing primitive advisory metadata into stable Markdown, preserves dossier,
strategy eligibility, and risk authority ordering, includes the as-of date,
explicit advisory-only language, uncertainty, failure modes, blocking reasons,
limitations, and deterministic non-claims, and ends with a final newline.

This phase adds no AI brief generation, prompt layer, market-data ingestion,
candidate discovery, strategy scoring, recommendation logic, dashboard code,
persistence, broker access, order/fill/execution/OMS behavior,
account/position/portfolio behavior, signal/evaluator behavior,
scheduler/runtime behavior, LLM/API call, network call, market-data provider
access, strategy validation claim, trading recommendation, or capital-layer
mutation.

Phase 48 - Advisory Operating Brief Board Summary adds
`algotrader.advisory.operating_brief_summary.build_operating_brief_board_summary`
as a deterministic metadata-only board layer for an already constructed
`OperatingBrief`. The summary accepts only an `OperatingBrief`, preserves the
source as-of date and source ordering, groups candidate ids by advisory label,
emits counts for every label including empty groups, surfaces existing strategy
and risk blocking reasons, live-authorization metadata, uncertainty, failure
modes, limitations, and advisory-only non-claims, and serializes to primitive
JSON-compatible dictionaries with dates as `YYYY-MM-DD` strings.

This phase adds no AI brief generation, prompt layer, market-data ingestion,
candidate generation, strategy scoring, ranking, recommendation logic,
dashboard code, persistence, broker access, order/fill/execution/OMS behavior,
account/position/portfolio behavior, signal/evaluator behavior,
scheduler/runtime behavior, LLM/API call, network call, market-data provider
access, strategy validation claim, trading recommendation, or capital-layer
mutation.

Phase 49 - Advisory Board Summary Markdown Renderer adds
`algotrader.advisory.operating_brief_summary_markdown.render_operating_brief_board_summary_markdown`
as a deterministic display surface for an already constructed
`OperatingBriefBoardSummary`. The renderer accepts only a board summary, formats
the source as-of date, advisory-only disclaimer, counts for every advisory
label, grouped candidate ids, research queue, watchlist, paper-eligible ids,
live-probe-eligible ids, live-authorized source metadata, strategy and risk
blockers, uncertainty, failure modes, limitations, source summary non-claims,
and fixed board non-claims into stable Markdown, preserves source ordering, and
ends with a final newline.

This phase adds no AI brief generation, prompt layer, market-data ingestion,
candidate generation, strategy scoring, ranking, recommendation logic,
dashboard code, persistence, broker access, order/fill/execution/OMS behavior,
account/position/portfolio behavior, signal/evaluator behavior,
scheduler/runtime behavior, LLM/API call, network call, market-data provider
access, strategy validation claim, trading recommendation, or capital-layer
mutation.

Phase 50 - Advisory Layer Review Hardening adds focused regression coverage for
the advisory operating-brief layer after external review. The tests pin complete
board-summary label counts, deterministic repeated `to_dict()` and Markdown
rendering, non-actionable label authority when strategy and risk statuses are
fully live-authorized, dataclass repr safety, and advisory safety boundaries.
Direct `OperatingBriefBoardSummary` construction now rejects negative
`candidate_counts_by_label` values while preserving builder-generated behavior.

This phase adds no new advisory features, strategy mandate integration,
synthetic fixtures, dashboard code, persistence, AI/LLM generation,
market-data ingestion, broker access, order/fill/execution/OMS behavior,
account/position/portfolio behavior, runtime/scheduler behavior, candidate
discovery, scoring, ranking, recommendation, trading behavior, or
capital-layer mutation.

Phase 51 - Synthetic Advisory Operating Brief Example Fixture adds
`tests.fixtures.advisory_operating_brief` as the canonical local-only synthetic
example for the advisory operating-brief layer. The fixture exposes builders for
one deterministic `OperatingBrief` and its derived `OperatingBriefBoardSummary`,
plus pinned literal Markdown snapshots for both renderers. The example covers
all five `AdvisoryLabel` values, fixed date `2026-01-15`, uncertainty, failure
modes, next research questions, limitations, non-claims, blocked strategy/risk
metadata, paper metadata, live-probe metadata, live-authorized metadata, and a
watchlist candidate whose strategy/risk metadata is intentionally more
permissive than the advisory label.

The fixture tests pin deterministic construction, serialization, summary
derivation, exact Markdown rendering, label grouping, constructor gates,
primitive JSON-compatible output, source immutability, and AST guardrails that
exclude file I/O, clocks, network/http, broker/execution/portfolio/runtime,
LLM, market-data provider, notebook, persistence, random, and subprocess
dependencies.

This phase adds no AI brief generation, market-data ingestion, candidate
generation, strategy scoring, ranking, recommendation logic, dashboard code,
persistence, broker access, order/fill/execution/OMS behavior,
account/position/portfolio behavior, runtime/scheduler behavior, LLM/API call,
network call, market-data provider access, strategy validation claim, trading
recommendation, or capital-layer mutation.

Phase 52 - Governance Status Snapshot Contracts adds
`algotrader.governance.status_snapshot` as a deterministic, metadata-only
source-contract layer for future advisory inputs. `StrategyMandateSnapshot`
captures strategy-side mandate, evidence, paper, live-probe, live-authorization,
validated artifact, requirement, blocker, limitation, uncertainty,
failure-mode, and non-claim metadata. `RiskAuthoritySnapshot` captures
risk-side paper, live-probe, live, kill-switch, policy, constraint, requirement,
blocker, limitation, uncertainty, failure-mode, and non-claim metadata.

Both snapshots are immutable, slotted dataclasses that accept only explicit
plain-date inputs, normalize sequence fields to immutable tuples, reject
malformed identifiers and string entries, enforce deterministic paper/probe/live
authority dependencies, and serialize to primitive JSON-compatible dictionaries
with dates as `YYYY-MM-DD` and tuple fields as lists. Focused tests pin
constructor gates, repeated deterministic serialization, source non-mutation,
safety field absence, and AST guardrails that exclude advisory imports, file
I/O, clocks, network/http, broker/execution/portfolio/runtime, LLM,
market-data provider, notebook, persistence, random, and subprocess
dependencies.

This phase defines source snapshots only. It adds no advisory adapter, AI brief
generation, market-data ingestion, candidate generation, strategy scoring,
ranking, recommendation logic, dashboard code, persistence, broker access,
order/fill/execution/OMS behavior, account/position/portfolio behavior,
runtime/scheduler behavior, LLM/API call, network call, market-data provider
access, strategy validation claim, trading behavior, or capital-layer mutation.

Phase 53 - Governance Snapshot to Advisory Status Adapter adds
`algotrader.advisory.governance_status_adapter` as a tiny deterministic
downstream adapter from Phase 52 governance snapshots into the existing advisory
status contracts. `strategy_mandate_snapshot_to_strategy_eligibility_status(...)`
accepts an explicit candidate id and converts `StrategyMandateSnapshot` into
`StrategyEligibilityStatus` through the existing advisory constructor.
`risk_authority_snapshot_to_risk_authority_status(...)` accepts an explicit
candidate id and converts `RiskAuthoritySnapshot` into `RiskAuthorityStatus`
through the existing advisory constructor.

The adapter preserves only fields supported by the existing advisory status
types: candidate ids supplied by the caller, mandate/authority ids, approval and
authority booleans, evidence refs from validated research and signal definition
ids, blockers, and limitations. It does not infer candidate identity from
strategy, mandate, or authority ids, does not upgrade authority beyond the
snapshot booleans, and lets existing advisory status validation reject
unsupported or inconsistent conversions. Focused tests pin type safety,
candidate-id validation, constructor usage, tuple ordering, repeated
deterministic conversion and serialization, source non-mutation, safety field
absence, and dependency-direction guardrails that keep governance independent
from advisory.

This phase adds no full `OperatingBrief` assembly, `ResearchCandidateDossier`
construction, `AdvisoryLabel` inference, AI brief generation, market-data
ingestion, candidate generation, strategy scoring, ranking, recommendation
logic, dashboard code, persistence, broker access, order/fill/execution/OMS
behavior, account/position/portfolio behavior, runtime/scheduler behavior,
LLM/API call, network call, market-data provider access, trading behavior, or
capital-layer mutation.

Phase 54 - Advisory Candidate Dossier Source Snapshot adds
`algotrader.advisory.candidate_snapshot.CandidateDossierSnapshot` as a
deterministic, metadata-only upstream source contract for future
`ResearchCandidateDossier` adaptation. The snapshot records candidate source
identity, source refs, proposed advisory label, label source and rationale,
strategy/mandate refs, universe/evidence refs, uncertainty, failure modes,
next questions, limitations, and non-claims without assembling an
`OperatingBrief`.

The contract is frozen and slotted, accepts only explicit plain dates,
normalizes sequence fields to immutable tuples, validates source type and label
source allowlists, serializes to primitive JSON-compatible dictionaries with
dates as `YYYY-MM-DD`, labels as strings, and tuple fields as lists, and leaves
source objects unchanged. Label authority is constructor-gated:
`research_only` and `watchlist_only` may be proposed by any allowed label
source, while `paper_eligible`, `live_probe_eligible`, and `live_authorized`
require deterministic/reviewed label sources. `live_authorized` additionally
requires strategy id, mandate id, evidence refs, and explicit non-claims;
`live_probe_eligible` requires strategy id, mandate id, and explicit
non-claims; `paper_eligible` requires strategy id and explicit non-claims.

Focused tests pin valid and invalid label-source combinations, plain-date and
string validation, tuple normalization, deterministic primitive serialization,
source non-mutation, non-claim safety, absence of scoring/ranking/discovery and
trading-runtime fields, and AST guardrails excluding governance imports, file
I/O, clocks, network/http, broker/execution/portfolio/runtime, LLM,
market-data provider, notebook, persistence, random, and subprocess
dependencies.

This phase adds no full `OperatingBrief` assembly, `ResearchCandidateDossier`
construction, candidate discovery, AI brief generation, market-data ingestion,
strategy scoring, ranking, recommendation logic, dashboard code, persistence,
broker access, order/fill/execution/OMS behavior, account/position/portfolio
behavior, runtime/scheduler behavior, LLM/API call, network call, market-data
provider access, trading behavior, or capital-layer mutation.

Phase 55 - Candidate Snapshot to Research Candidate Dossier Adapter adds
`algotrader.advisory.candidate_dossier_adapter` as a pure deterministic bridge
from already-validated `CandidateDossierSnapshot` metadata into the existing
`ResearchCandidateDossier` advisory contract. The adapter accepts only
candidate dossier snapshots, rejects other inputs with `ValidationError`, and
uses the existing dossier constructor as the validation boundary.

The conversion preserves only fields the current dossier contract supports:
candidate id, title, summary, the exact proposed advisory label, uncertainty
factors, failure modes, next questions, and limitations, with tuple ordering
unchanged. Source ids, label rationale/source metadata, strategy refs, mandate
refs, universe refs, evidence refs, and non-claims remain on the source
snapshot because the current dossier contract has no matching fields. The
adapter does not infer, upgrade, downgrade, or rewrite advisory labels and does
not mutate the source snapshot.

Focused tests pin research/watchlist/paper/live-probe/live-authorized
conversion, exact label preservation, constructor usage, deterministic repeated
conversion and serialization, primitive JSON-compatible output, source
non-mutation, supported-field-only projection, elevated-label source
restrictions remaining enforced by snapshot construction, and AST guardrails
excluding governance imports, status/brief assembly, file I/O, clocks, network,
broker/execution/portfolio/runtime, LLM, market-data provider, notebook,
persistence, random, and subprocess dependencies.

This phase adds no `OperatingBrief` assembly, strategy/risk status construction,
governance import in the adapter, AI brief generation, market-data ingestion,
candidate discovery, strategy scoring, ranking, recommendation logic,
dashboard code, persistence, broker access, order/fill/execution/OMS behavior,
account/position/portfolio behavior, runtime/scheduler behavior, LLM/API call,
network call, market-data provider access, trading behavior, or capital-layer
mutation.

Phase 56 - Advisory Operating Brief Assembly from Prepared Parts adds
`algotrader.advisory.operating_brief_assembly` as a pure deterministic
assembler for already-constructed advisory parts. The public
`assemble_operating_brief_from_parts(...)` function accepts an explicit plain
`date`, `ResearchCandidateDossier` objects, `StrategyEligibilityStatus`
objects, and `RiskAuthorityStatus` objects, normalizes the input iterables to
tuples, preserves source ordering, rejects empty dossier collections, duplicate
candidate ids, orphan strategy/risk statuses, and mismatched exposed
`as_of_date` values, then calls the existing `OperatingBrief` constructor as
the final validation boundary.

The assembler does not consume candidate or governance snapshots, does not call
candidate/governance adapters, and does not infer, upgrade, downgrade, or
rewrite advisory labels. Elevated dossier labels require matching prepared
strategy and risk status objects, while final actionable-label support remains
constructor-gated by `OperatingBrief`. Research-only and watchlist-only
dossiers may be assembled without statuses, and permissive statuses do not
change the dossier label or board grouping.

Focused tests cover successful assembly, constructor usage, frozen/slotted
output, tuple normalization, ordering, source non-mutation, deterministic
repeated calls, type validation, candidate-id validation, elevated-label gates,
non-actionable label authority, optional as-of consistency, primitive
serialization, Markdown rendering, board summary compatibility, safety surface,
and AST guardrails excluding snapshots, adapters, governance, broker/execution/
portfolio/runtime, LLM/network/market-data, persistence, notebooks, file I/O,
clocks, random, and subprocess dependencies.

This phase adds no snapshot-to-brief assembly, candidate dossier construction,
strategy/risk status construction, candidate discovery, AI brief generation,
market-data ingestion, strategy scoring, ranking, recommendation logic,
dashboard code, persistence, broker access, order/fill/execution/OMS behavior,
account/position/portfolio behavior, runtime/scheduler behavior, LLM/API call,
network call, market-data provider access, trading behavior, or capital-layer
mutation.

Phase 57 - Synthetic Advisory Pipeline Fixture adds
`tests.fixtures.advisory_pipeline` as a deterministic test-only end-to-end
fixture proving the existing advisory pieces compose when called explicitly:
candidate snapshots adapt into `ResearchCandidateDossier` objects, governance
snapshots adapt into prepared strategy/risk statuses with explicit candidate
ids, prepared parts assemble into an `OperatingBrief`, and the existing board
summary and Markdown renderers produce pinned literal output.

The fixture uses only synthetic identifiers and prose, fixed date `2026-01-16`,
all five `AdvisoryLabel` values, research-only without strategy/risk support,
watchlist-only with intentionally permissive optional support, and a
constructor-gated live-authorized path with matching strategy and risk support.
Focused tests pin deterministic builders, source non-mutation, exact label
preservation, prepared-part ordering, elevated-label support gates,
non-actionable label authority, primitive serialization, exact Markdown output,
safety content, and AST guardrails excluding file I/O, clocks, environment/Git
inspection, network/http, broker/execution/portfolio/runtime/scheduler, LLM,
market-data provider, notebook, persistence, random, and subprocess
dependencies.

This phase adds no production snapshot-to-brief assembler, production pipeline
function, OperatingBrief generation service, adapter authority inference, AI
brief generation, market-data ingestion, candidate discovery, strategy scoring,
ranking, recommendation logic, dashboard code, persistence, broker access,
order/fill/execution/OMS behavior, account/position/portfolio behavior,
runtime/scheduler behavior, LLM/API call, network call, trading behavior, or
capital-layer mutation.

Phase 58 - Advisory Pipeline Review Hardening adds focused regression
guardrails in response to the external advisory pipeline review. The new tests
pin governance-to-advisory import direction, advisory dataclass field-name
safety, hash-seed-independent `to_dict()` and Markdown renderer output,
compact JSON round-trip determinism for `OperatingBrief` and
`OperatingBriefBoardSummary`, reverse-direction rejection for elevated dossier
labels with lower prepared strategy/risk support, and the existing positive
asymmetry where non-actionable labels remain authoritative despite more
permissive support metadata.

This phase changes no validation behavior and adds no advisory feature,
production snapshot-to-brief assembler, OperatingBrief generation service,
candidate discovery, label inference, adapter, renderer, assembly behavior,
market-data ingestion, strategy scoring, ranking, recommendation logic,
dashboard code, persistence, broker/order/fill/execution/OMS behavior,
account/position/portfolio behavior, runtime/scheduler behavior, LLM/API call,
network call, trading behavior, or capital-layer mutation.

Phase 59 - SPY SMA-200 Research Runner Mechanics Hardening returns the work to
the existing local-only research runner without promoting any strategy. The
runner report now emits explicit SMA mechanics metadata in Markdown and JSON:
the fixed 200-observation window, minimum observations, fully formed SMA
observation count, insufficient-observation status, and same-close metadata
with previous-exposure backtest timing. It also emits explicit non-claims for
advisory/research-only use, not validated evidence, no trading recommendation,
no approved signal, no live or paper trading authority, and no broker/order/
fill/account/position/portfolio/allocation/target-weight behavior.

Focused tests now use deterministic synthetic CSVs under `tmp_path` without
`.data/`, real SPY data, network, credentials, vendors, environment reads, or
market-data providers. They pin duplicate, unordered, malformed-date, missing
close, and non-numeric close rejection through the existing loader contract;
reporting rather than rejection for insufficient SMA-200 observations; exact
date handling; no-lookahead SMA behavior; deterministic Markdown/JSON bytes
across repeated runs; adjustment-policy and return-basis honesty; JSON payload
field safety; and AST guardrails excluding broker/execution/portfolio/runtime,
network/http/socket, LLM/API, market-data provider, notebook/vectorbt,
persistence, random, subprocess, environment, scoring, ranking,
recommendation, candidate-discovery, order/fill, and portfolio behavior.

This phase changes report metadata only. It adds no advisory expansion, source
or data approval, real market data, strategy validation, profitability claim,
signal definition, evaluator behavior, trading recommendation, live/paper
trading authority, broker/order/fill/execution/OMS behavior,
account/position/portfolio behavior, runtime/scheduler behavior, LLM/API call,
network call, market-data ingestion, scoring, ranking, recommendation, or
candidate-discovery behavior.

Phase 60 - SPY SMA-200 Synthetic Output Contract Snapshot adds a canonical
synthetic regression test for the local research runner output contract. The
test builds a deterministic `tmp_path` CSV, runs the runner with explicit
synthetic input, explicit Markdown output, an explicit custom JSON sidecar path,
fixed local assumptions, and `allow_outside_data_dir=True`, then pins the
Markdown contract sections, JSON top-level keys, exact SMA mechanics payload,
unknown-adjustment/price-return honesty, non-claims, forbidden payload-field
safety, raw-row/path exclusion, and byte-identical Markdown/JSON output across
repeated runs.

To support that explicit sidecar contract, the runner now accepts an optional
`json_output_path`/`--json-output` value while preserving the existing default
sibling `.json` sidecar behavior when only a Markdown output path is supplied.
The validation remains local-only: JSON output still requires a Markdown output
path, must use a `.json` suffix, must stay outside `.data/`, and must be
separate from the Markdown report.

This phase adds no profitability validation, strategy approval, signal
definition, advisory expansion, source or data approval, real market data,
market-data ingestion, broker/order/fill/execution/OMS behavior,
account/position/portfolio/allocation/target-weight behavior, runtime/scheduler
behavior, LLM/API call, network call, scoring, ranking, recommendation,
candidate-discovery behavior, paper/live behavior, trading authority, or
trading behavior.

Phase 61 - SPY SMA-200 Synthetic Metric Semantics Contract pins exact metric
semantics for the local research runner on deterministic synthetic CSVs only.
The tests add a 205-row flat series proving the SMA fully forms, insufficient
observations are false, SMA exposure remains zero when close equals the trailing
SMA, strategy and buy-and-hold price returns remain zero, buy-and-hold exposure
stays one, unknown adjustment remains `price_return`, and repeated Markdown/JSON
outputs are byte-identical without raw rows or local paths. A controlled breakout
series proves that the first close above the SMA changes exposure according to
the existing same-close rule but earns no same-bar strategy profit under the
previous-exposure backtest convention; the later bar reflects the prior exposure,
and revised future closes do not alter earlier exposure.

This phase changes no runner behavior or validation behavior. It adds no
profitability validation, strategy approval, signal definition, advisory
expansion, source or data approval, real market data, market-data ingestion,
broker/order/fill/execution/OMS behavior, account/position/portfolio/allocation/
target-weight behavior, runtime/scheduler behavior, LLM/API call, network call,
scoring, ranking, recommendation, candidate-discovery behavior, paper/live
behavior, trading authority, or trading behavior.

Phase 62 - Synthetic Moving-Average Research Mechanics Kernel adds a small
offline-safe `algotrader.research.moving_average` mechanics contract for
synthetic research/backtesting experiments. It defines frozen/slotted metadata
dataclasses for dated positive `Decimal` inputs and per-row moving-average
observations, plus a pure trailing simple moving-average builder that accepts
ordered iterable inputs, returns immutable tuples, preserves input ordering,
uses only prior/current observations, marks the first `window - 1` rows as
unavailable, and treats equality to the moving average as not above.

The kernel rejects datetime values, non-date values, bools, non-Decimal values,
non-positive values, empty inputs, duplicate dates, unordered dates, malformed
entries, and malformed windows. Tests pin window 1 and window 200 synthetic
behavior, Decimal-only arithmetic, repeated-call determinism, no input mutation,
future-value no-lookahead behavior, and AST guardrails excluding broker/
execution/portfolio/runtime, network/http/socket, LLM/API, market-data provider,
notebook/vectorbt, persistence, random, subprocess, filesystem, pandas/numpy,
scoring, ranking, recommendation, candidate-discovery, order/fill/account/
position/portfolio/allocation/target-weight, signal/evaluator, and trading
behavior.

This phase does not refactor or extend the SPY SMA-200 runner. It adds no
strategy validation, approved signal, source or universe approval, benchmark,
real market data, broad ETF implementation, market-data ingestion, advisory
integration, dashboard, AI brief generation, paper/live behavior, broker/order/
fill/execution/OMS behavior, account/position/portfolio behavior,
runtime/scheduler behavior, LLM/API call, network call, scoring, ranking,
recommendation, candidate-discovery behavior, trading authority, or trading
behavior.

Phase 63 - Synthetic Moving-Average Exposure State Kernel adds
`algotrader.research.moving_average_exposure` as a small offline-safe research
metadata layer over already-built `MovingAverageObservation` rows. It defines a
frozen/slotted `MovingAverageExposureState` contract and a pure
`build_previous_exposure_states` function that normalizes iterable observation
inputs to immutable tuples, rejects empty input, malformed entries, duplicate
dates, unordered dates, and mixed windows, and preserves input ordering.

The exposure-state kernel uses a previous-row convention: the first
`current_exposure` is zero, each row's `next_exposure` is derived only from the
current moving-average observation, and the following row's `current_exposure`
reflects that prior `next_exposure`. Unavailable moving averages, equality to
the moving average, below-average rows, and missing above-average metadata all
produce zero `next_exposure`; above-average rows produce one `next_exposure`.
Tests pin direct state validation, no-lookahead behavior, repeated-call
determinism, input non-mutation, immutable output, and AST/field guardrails.

This phase does not compute returns and does not refactor or extend the SPY
SMA-200 runner. It adds no strategy validation, signal definition, evaluator,
source approval, real data, broad ETF implementation, advisory expansion,
dashboard, AI brief generation, paper/live behavior, broker/order/fill/
execution/OMS behavior, account/position/portfolio/allocation/target-weight
behavior, runtime/scheduler behavior, LLM/API call, network call,
market-data ingestion, scoring, ranking, recommendation,
candidate-discovery behavior, trading authority, or trading behavior.

Phase 64 - Synthetic Exposure-Applied Return Kernel adds
`algotrader.research.exposure_returns` as a small offline-safe research
metadata layer over ordered `MovingAverageInput` values and
`MovingAverageExposureState` rows. It defines a frozen/slotted
`ExposureReturnObservation` contract and a pure
`build_exposure_applied_returns` builder that normalizes iterable inputs to
immutable tuples, preserves ordering, rejects empty inputs, malformed entries,
length mismatches, date mismatches, duplicate dates, and unordered dates, and
uses Decimal-only close-to-close simple returns.

The kernel marks the first row return unavailable and applies each later row's
`current_exposure` to that row's asset return using previous-exposure
semantics. Zero current exposure produces zero exposure return, one current
exposure preserves the asset return, and a same-row breakout cannot create
same-row exposure-applied return. Tests pin direct observation validation,
return mechanics, Decimal preservation, declining-value returns, no-lookahead
future changes, repeated-call determinism, source non-mutation, immutable
output, and AST/field guardrails.

This phase does not compute cumulative returns, equity curves, performance
metrics, costs, slippage, fees, benchmarks, portfolio accounting, allocation,
target weights, position sizing, orders, fills, signals, execution plans, or
strategy validation. It does not refactor or extend the SPY SMA-200 runner and
adds no advisory expansion, source approval, real data, broad ETF
implementation, market-data ingestion, dashboard, AI brief generation,
paper/live behavior, broker/order/fill/execution/OMS behavior,
account/position/portfolio behavior, runtime/scheduler behavior, LLM/API call,
network call, scoring, ranking, recommendation, candidate-discovery behavior,
trading authority, or trading behavior.

Phase 65 - Synthetic Cumulative Exposure Return Path Kernel adds
`algotrader.research.cumulative_returns` as a small offline-safe research
metadata layer over already-built `ExposureReturnObservation` rows. It defines
a frozen/slotted `CumulativeReturnObservation` contract and a pure
`build_cumulative_return_path` builder that normalizes iterable input to an
immutable tuple, preserves ordering, rejects empty input, malformed entries,
duplicate dates, unordered dates, malformed return fields, non-Decimal
cumulative values, and bypassed malformed exposure-return rows, and uses
Decimal-only cumulative return arithmetic.

The kernel treats the first row as a cumulative baseline with zero asset and
exposure cumulative returns while preserving the source row's return
availability and return fields. Later available rows compound asset cumulative
return from `asset_return` and exposure cumulative return from
`exposure_return`; unavailable rows preserve prior cumulative values without
inventing returns. Tests pin direct observation validation, tuple immutability,
flat and two-return paths, previous-exposure breakout mechanics, no-lookahead
future changes, Decimal preservation, repeated-call determinism, source
non-mutation, and AST/field guardrails.

This phase does not compute equity curves, starting capital, PnL, Sharpe,
CAGR, drawdown, volatility, alpha, beta, benchmark comparisons, win rate,
performance scores, costs, slippage, fees, portfolio accounting, allocation,
target weights, position sizing, orders, fills, signals, execution plans,
strategy validation, source approval, real data ingestion, broad ETF
implementation, advisory integration, market-data ingestion, dashboard, AI
brief generation, paper/live behavior, broker/order/fill/execution/OMS
behavior, account/position/portfolio behavior, runtime/scheduler behavior,
LLM/API call, network call, scoring, ranking, recommendation,
candidate-discovery behavior, trading authority, or trading behavior. It does
not refactor or extend the SPY SMA-200 runner.

Phase 66 - Synthetic Cumulative Return Path Summary adds
`algotrader.research.cumulative_return_summary` as a small deterministic
research-only metadata layer over already-built `CumulativeReturnObservation`
rows. It defines a frozen/slotted `CumulativeReturnPathSummary` contract and a
pure `summarize_cumulative_return_path` builder that normalizes iterable input,
preserves source ordering for first/last/final-row semantics, rejects empty
input, non-cumulative-return entries, duplicate dates, unordered dates, and
malformed direct construction, and copies the last row's asset and exposure
cumulative return values without recomputing the path.

The summary records only first and last observation dates, total rows,
available and unavailable return counts, final asset and exposure cumulative
returns, whether any return rows were available, and research-only limitations
and non-claims. Its deterministic `to_dict()` serializes dates as `YYYY-MM-DD`,
Decimals as strings, tuples as lists, and counts/booleans as primitive values.
Tests pin constructor validation, iterable normalization, source non-mutation,
flat and mixed path summaries, full synthetic moving-average to cumulative-path
integration, previous-exposure/no-same-row visibility through the final
exposure cumulative value, JSON round-tripping, and AST/field guardrails.

This phase does not compute Sharpe, CAGR, drawdown, volatility, alpha, beta,
benchmark comparisons, win rate, performance scores, equity curves, starting
capital, PnL, costs, slippage, fees, benchmark returns, portfolio accounting,
allocation, target weights, position sizing, orders, fills, signals, execution
plans, optimization metrics, strategy validation, source approval, real data
ingestion, broad ETF implementation, advisory integration, market-data
ingestion, dashboard, AI brief generation, paper/live behavior,
broker/order/fill/execution/OMS behavior, account/position/portfolio behavior,
runtime/scheduler behavior, LLM/API call, network call, scoring, ranking,
recommendation, candidate-discovery behavior, trading authority, or trading
behavior. It does not refactor or extend the SPY SMA-200 runner.

Phase 67 - Synthetic Moving-Average Replay Package adds
`algotrader.research.moving_average_replay` as a small deterministic
research-only package over the already-built synthetic mechanics chain:
`MovingAverageInput`, `MovingAverageObservation`,
`MovingAverageExposureState`, `ExposureReturnObservation`,
`CumulativeReturnObservation`, and `CumulativeReturnPathSummary`. It defines a
frozen/slotted `MovingAverageReplayPackage` contract and a pure
`build_moving_average_replay_package` builder that composes the existing
moving-average, previous-exposure, exposure-return, cumulative-return, and
summary kernels in order.

The package records replay id, plain as-of date, moving-average window,
immutable tuple outputs for each mechanics stage, the cumulative path summary,
and replay-level research limitations and non-claims. Direct construction
validates sequence types, matching lengths, matching ordered dates, matching
windows, summary/path consistency, and exact agreement with the existing
kernels. Its deterministic `to_dict()` serializes dates as `YYYY-MM-DD`,
Decimals as strings, tuples as lists, and nested mechanics rows as explicit
primitive dictionaries without object reprs or non-deterministic ordering.

This phase does not compute Sharpe, CAGR, drawdown, volatility, alpha, beta,
benchmark comparisons, win rate, performance scores, equity curves, starting
capital, PnL, costs, slippage, fees, benchmark returns, portfolio accounting,
allocation, target weights, position sizing, orders, fills, signals, execution
plans, optimization metrics, strategy validation, source approval, real data
ingestion, broad ETF implementation, advisory integration, market-data
ingestion, dashboard, AI brief generation, paper/live behavior,
broker/order/fill/execution/OMS behavior, account/position/portfolio behavior,
runtime/scheduler behavior, LLM/API call, network call, scoring, ranking,
recommendation, candidate-discovery behavior, trading authority, or trading
behavior. It does not refactor or extend the SPY SMA-200 runner.

Phase 68 - Synthetic Moving-Average Replay JSON Contract Fixture freezes the
Phase 67 `MovingAverageReplayPackage.to_dict()` output by content with two
committed synthetic compact JSON fixtures:
`tests/fixtures/moving_average_replay_contract_flat.json` and
`tests/fixtures/moving_average_replay_contract_breakout.json`. The flat fixture
uses only a deterministic positive Decimal series and locks zero final asset and
exposure cumulative returns. The breakout fixture uses only synthetic values
that form an SMA, break above it, and then prove previous-row exposure behavior
through a later row. Both fixtures use fixed replay ids, fixed `2026-01-17`
as-of metadata, primitive JSON-compatible values, compact insertion-order
serialization, research-only limitations, and non-claims.

Phase 68 also adds focused review-hardening coverage for direct
`MovingAverageObservation` construction, exact current reason strings, strict
below-SMA exit mechanics, equality-after-true exposure reset mechanics, Decimal
context stability for the exact fixture path, and cumulative-return validation
asymmetry. The replay non-claims now explicitly state that exposure is a `0/1`
research indicator and not allocation, target weight, position size, or a
portfolio instruction. This phase does not add strategy validation, signal
definition, performance evaluation, broad ETF implementation, SPY runner
refactoring, real data, broker/order/fill/portfolio/runtime behavior, network
or LLM calls, scoring, ranking, recommendation, or candidate-discovery
behavior.

Phase 69 - SPY Runner / Moving-Average Replay Synthetic Parity Probe adds
tests-only parity coverage between the existing local SPY SMA-200 research
runner and the generic `MovingAverageReplayPackage` mechanics. The tests use
only deterministic synthetic CSV files under `tmp_path`, run the SPY runner
with explicit synthetic input and output paths plus
`allow_outside_data_dir=True`, and build a generic replay package from the same
CSV close values with `window=200`.

The parity probe covers a flat 205-row series, a controlled breakout series,
and an insufficient-observation series. It compares stable public mechanics:
SMA window and fully formed row counts, the unknown adjustment / `price_return`
metadata boundary, previous-exposure behavior, exposure-applied returns, and
final asset/exposure cumulative returns where the runner's metrics expose
equivalent values. It also pins repeated-run determinism, research-only
non-claims, absence of forbidden behavior field keys, absence of external data
source markers, and the normal offline, credential-free pytest boundary.

This phase does not refactor the SPY runner, adapt the SPY runner to the
generic kernel, change generic research kernels, validate a strategy, define a
signal, add a backtesting engine, add broad ETF implementation, add performance
metrics, ingest real data, read `.data/`, add broker/order/fill/portfolio/
runtime behavior, call network/LLM/market-data providers, add scoring, ranking,
recommendation, candidate-discovery behavior, or add paper/live/trading
behavior.

Phase 70 - SPY SMA-200 Runner Generic Replay Integration Probe performs a
narrow output-preserving runner refactor. The local SPY SMA-200 runner now
builds a `MovingAverageReplayPackage` from the loaded snapshot's selected
adjusted-close values using `MovingAverageInput` and
`build_moving_average_replay_package(..., window=200)`. The runner converts the
package's `next_exposure` states back into the existing `DailyExposure` shape,
so its SMA observation, previous-exposure state, exposure-applied return, and
no-cost cumulative-return mechanics are backed by the generic replay chain.

The public Markdown report and JSON sidecar contracts remain unchanged. The
runner still uses `run_daily_backtest` for the existing output metric envelope,
including starting/ending equity, max drawdown, exposure ratio, turnover, and
fee/slippage-adjusted custom-assumption behavior that the generic replay
package intentionally does not model. Unknown adjustment policy remains
`unknown` and `price_return`, default sibling `.json` sidecar behavior remains
explicit-output-only, and synthetic `tmp_path` tests continue to avoid `.data/`
and real market data.

Phase 70 does not change generic research kernels, validate a strategy, define
a signal, add a backtesting engine, add cost/slippage support to the generic
kernel, add performance metrics, ingest real data, read `.data/`, add advisory
integration, add broker/order/fill/account/position/portfolio/allocation/
target-weight/runtime behavior, call network/LLM/market-data providers, add
scoring, ranking, recommendation, candidate-discovery behavior, or add
paper/live/trading behavior.

Phase 71 - SPY Runner Generic Replay Integration Guardrails adds focused
regression coverage around the Phase 70 integration. The tests now prove the
SPY exposure builder calls the generic moving-average replay package with
snapshot adjusted-close `MovingAverageInput` values and `window=200`, then
converts replay `next_exposure` states back to `DailyExposure`. They also pin
that nonzero fee/slippage metrics remain owned by the runner's
`run_daily_backtest` path rather than the generic no-cost replay summary.

The canonical synthetic report guardrails now pin the JSON assumptions payload,
top-level sidecar key set, explicit and default JSON sidecar behavior, absence
of raw generic replay payloads or runtime/dataclass repr leaks, unknown
adjustment / `price_return` honesty, research-only non-claims, safety-field
absence, and AST import boundaries for only the allowed local research modules.
This phase adds no generic kernel changes, advisory expansion, strategy
validation, source approval, real data, broker/order/fill/portfolio/runtime/
LLM/network/market-data behavior, scoring, ranking, recommendation,
candidate-discovery, paper/live, or trading behavior.

Phase 72 - Research Scope Candidate Snapshot Contracts adds metadata-only
candidate contracts for future broad ETF / moving-average research planning.
`algotrader.research.research_scope` now defines frozen/slotted candidate
dataclasses for data sources, universes, benchmarks, and cash proxies, plus an
optional `ResearchScopeSnapshot` that bundles one or more of each candidate
type. Each contract is candidate-only, rejects `approval_state="approved"`,
normalizes sequence metadata to tuples, requires explicit non-approval
non-claims, and serializes deterministically to primitive JSON-compatible
dictionaries with dates as `YYYY-MM-DD` strings.

This phase adds no source approval, universe approval, benchmark approval, cash
proxy approval, methodology approval, parameter approval, data acquisition
path, strategy validation, signal approval, evaluator, backtest, broad ETF
implementation, real data ingestion, SPY runner change, generic
moving-average kernel change, advisory expansion, governance expansion,
broker/order/fill/portfolio/runtime behavior, LLM/API call, network call,
market-data call, scoring, ranking, recommendation, candidate-discovery
behavior, paper/live behavior, trading authority, or trading behavior.

Phase 73 - Synthetic Broad ETF Research Scope Fixture adds a deterministic
test/documentation fixture built from the Phase 72 research-scope candidate
contracts. `tests.fixtures.research_scope` now constructs one synthetic broad
ETF-style `ResearchScopeSnapshot` with one synthetic source candidate, one
`broad_etf_candidate` universe, one synthetic benchmark candidate, and one
synthetic cash proxy candidate. The fixture uses a fixed plain date
(`2026-01-18`), synthetic ids only, the four synthetic asset ids documented in
the test fixture, explicit blockers, limitations, required follow-up, and the
required research-scope non-claims. It also pins the expected primitive
dictionary and compact JSON representation for regression tests.

The fixture tests cover construction, nested candidate contract types,
candidate-only approval states, exact primitive serialization, byte-identical
compact JSON round-tripping, repeated construction determinism, absence of real
ETF tickers, raw market data, URLs, credentials, and vendor/source identifiers,
safety-field absence, no scoring/ranking/recommendation/candidate-discovery
fields, no affirmative approval or authority claims, and AST guardrails that
keep the fixture free of broker/execution/portfolio/runtime/network/LLM/
market-data/dataframe/random/file-I/O dependencies. This phase adds no source
approval, universe approval, benchmark approval, cash proxy approval,
methodology approval, parameter approval, data acquisition path, strategy
validation, signal approval, evaluator, backtest, broad ETF strategy
implementation, real data ingestion, SPY runner change, generic moving-average
kernel change, advisory expansion, governance expansion, broker/order/fill/
portfolio/runtime behavior, LLM/API call, network call, market-data call,
scoring, ranking, recommendation, candidate-discovery behavior, paper/live
behavior, trading authority, or trading behavior.

Phase 74 - Research Methodology / Parameter Candidate Snapshot Contracts adds
metadata-only candidate contracts for future broad ETF / moving-average
research planning. `algotrader.research.research_methodology` now defines
frozen/slotted dataclasses for methodology candidates, parameter-set
candidates, and an optional `ResearchMethodologyScopeSnapshot` that bundles
those candidates. The contracts reject `approval_state="approved"`, normalize
sequence metadata to tuples, validate the allowed candidate type and policy
strings, require positive unique moving-average window metadata, reject
orphaned parameter-set methodology references, require explicit non-approval
non-claims, and serialize deterministically to primitive JSON-compatible
dictionaries with dates as `YYYY-MM-DD` strings.

This phase adds no methodology approval, parameter approval, source approval,
universe approval, benchmark approval, cash proxy approval, trading rule,
signal approval, evaluator approval, strategy validation, data source,
universe, benchmark, cash proxy, backtest, broad ETF strategy implementation,
real data ingestion, SPY runner change, generic moving-average kernel change,
advisory expansion, governance expansion, broker/order/fill/portfolio/runtime
behavior, LLM/API call, network call, market-data call, scoring, ranking,
recommendation, candidate-discovery behavior, paper/live behavior, trading
authority, or trading behavior.

Phase 75 - Synthetic Broad ETF Methodology Scope Fixture adds a deterministic
test/documentation fixture built from the Phase 74 methodology and parameter
candidate contracts. `tests.fixtures.research_methodology` now constructs one
candidate-only `ResearchMethodologyScopeSnapshot` as of `2026-01-19`, with one
`moving_average_trend_candidate` methodology candidate, one
`single_window_candidate` parameter-set candidate containing only the synthetic
200-window metadata value, and a link to the Phase 73 synthetic broad ETF
research-scope fixture by synthetic scope id only. The fixture includes
explicit blockers, limitations, required follow-up, required methodology
non-claims, and pinned primitive dictionary and compact JSON payloads.

The fixture tests cover construction, nested candidate contract types,
non-approved approval states, methodology-to-parameter linkage,
synthetic-scope id linkage, exact primitive serialization, byte-identical
compact JSON round-tripping, repeated construction determinism, absence of real
ETF tickers, raw market data, URLs, credentials, and vendor/source identifiers,
safety-field absence, no scoring/ranking/recommendation/candidate-discovery
fields, no affirmative approval or authority claims, and AST guardrails that
keep the fixture free of broker/execution/portfolio/runtime/network/LLM/
market-data/dataframe/random/file-I/O dependencies. This phase adds no
methodology approval, parameter approval, source approval, universe approval,
benchmark approval, cash proxy approval, trading rule, signal approval,
evaluator approval, strategy validation, data source, universe, benchmark, cash
proxy, backtest, broad ETF strategy implementation, real data ingestion, SPY
runner change, generic moving-average kernel change, advisory expansion,
governance expansion, broker/order/fill/portfolio/runtime behavior, LLM/API
call, network call, market-data call, scoring, ranking, recommendation,
candidate-discovery behavior, paper/live behavior, trading authority, or
trading behavior.

Phase 76 - Synthetic Broad ETF Research Planning Package Fixture adds a
deterministic test/documentation package fixture that combines the Phase 73
synthetic research-scope fixture and the Phase 75 synthetic methodology-scope
fixture. `tests.fixtures.research_planning` now returns a primitive dictionary
as of `2026-01-20` with a fixed synthetic planning package id, embedded
research-scope and methodology-scope primitive payloads, limitations, and
explicit non-claims. The package preserves the methodology fixture's synthetic
linked-scope id reference back to the synthetic research-scope id and pins the
combined compact JSON representation by composing the already pinned nested
fixture JSON payloads.

The fixture tests cover primitive construction, fixed dates, embedded fixture
linkage, non-approved candidate states, required non-claims, exact compact JSON
serialization, byte-identical JSON round-tripping, repeated primitive safety,
absence of dataclass/tuple/set/Decimal/date/datetime/repr/memory-address
leakage, absence of real ETF tickers, raw market data, URLs, credentials,
vendor/source identifiers, account ids, runtime fields, and selection fields,
no affirmative approval or authority claims, and AST guardrails that keep the
planning fixture free of broker/execution/portfolio/runtime/network/LLM/
market-data/dataframe/random/file-I/O dependencies. This phase adds no source
approval, universe approval, benchmark approval, cash proxy approval,
methodology approval, parameter approval, strategy validation, signal approval,
evaluator approval, source ingestion path, broad ETF strategy implementation,
real data ingestion, SPY runner change, generic moving-average kernel change,
advisory expansion, governance expansion, broker/order/fill/portfolio/runtime
behavior, LLM/API call, network call, market-data call, scoring, ranking,
recommendation, candidate-discovery behavior, paper/live behavior, trading
authority, or trading behavior.

Phase 77 - Research Planning Review Hardening consolidates duplicated internal
research-planning validators into `algotrader.research._planning_validation`
while preserving the existing public scope and methodology contracts. The
scope and methodology modules now share required-string, allowed-string,
plain-date, string-tuple, candidate-tuple, duplicate-id, non-claim, and
deterministic date serialization helpers. Methodology-side non-claims now also
require `not evidence approval`, and the synthetic methodology and planning
fixtures pin that added non-claim in their compact JSON outputs.

The hardening tests add concise allowed-state coverage for all research scope
and methodology planning contracts, rejection coverage for `approved`,
` approved `, and `Approved`, a parameter/methodology linkage ordering
regression, a local primitive-package linked-scope assertion that fails loudly
for mismatched synthetic scope ids, a return/returns substring guard around
`return_construction_policy`, and AST guardrails for the new internal helper.
The planning package remains a primitive dictionary only. This phase adds no
source approval, universe approval, benchmark approval, cash proxy approval,
methodology approval, parameter approval, evidence approval, strategy
validation, signal/evaluator behavior, source ingestion path, broad ETF
strategy implementation, real data ingestion, SPY runner change, generic
moving-average kernel change, advisory expansion, governance expansion,
broker/order/fill/portfolio/runtime behavior, LLM/API call, network call,
market-data call, scoring, ranking, recommendation, candidate-discovery
behavior, paper/live behavior, trading authority, or trading behavior.

Phase 78 - Synthetic Planning Fixture Replay Consumer adds
`tests.fixtures.research_planning_replay` as a tiny synthetic-only consumer of
the Phase 76 primitive planning package. The fixture preserves the full
planning package as copied metadata, extracts only synthetic ids,
`linked_scope_ids`, `evidence_refs`, and the single candidate moving-average
window, then builds an existing `MovingAverageReplayPackage` through the
public `build_moving_average_replay_package(...)` path with deterministic
synthetic observations. The output is a primitive dictionary that contains the
planning metadata copy, consumed metadata, replay package `to_dict()` payload,
limitations, and explicit non-claims.

This proves planning fixture shape usability only. It does not promote the
planning package to a production contract, validate a strategy, approve any
source/universe/benchmark/cash proxy/methodology/parameter/evidence, infer
evidence validation from `evidence_refs`, infer trading readiness from replay
output, or add signal/evaluator/trading behavior. Tests pin deterministic
primitive JSON behavior, allowed planning states only, `not evidence approval`,
paired synthetic `linked_scope_ids`, non-mutation of planning and replay
objects, existing replay shape preservation, absence of new replay metrics,
absence of real data/tickers/vendor names/URLs/credentials/market-data paths,
and no broker/order/fill/portfolio/runtime/LLM/network/market-data/scoring/
ranking/recommendation/candidate-discovery behavior. Normal pytest remains
offline and credential-free.

Phase 79 - Synthetic Planning Replay Report Shape adds
`tests.fixtures.research_planning_replay_report` as a primitive synthetic-only
report/result fixture around the Phase 78 planning replay consumer. The report
summarizes only synthetic research scope id, methodology scope id,
`linked_scope_ids`, metadata-only `evidence_refs`, methodology non-claims,
non-approved planning states, the selected synthetic moving-average window,
and existing replay package shape metadata.

The report is fixture-level and non-validating. It does not approve any source,
universe, benchmark, cash proxy, methodology, parameter, or evidence; does not
add replay metrics; does not add signal/evaluator/trading behavior; and does
not add broker/order/fill/portfolio/runtime/LLM/network/market-data behavior.
Normal pytest remains offline and credential-free.

Phase 81 - Research Planning Fixture Guardrail Consolidation keeps the Phase
72-79 synthetic planning/replay/report fixture chain test-only while reducing
duplicated guardrail assertions. Shared test helpers now cover non-approved
planning-state checks, primitive JSON shape checks, negative-term screening,
metadata-only evidence non-claims, and real ticker/vendor/path/credential
exclusion. No production code changed, no fixture output semantics changed,
and normal pytest remains offline and credential-free.

Phase 83 - Broad ETF Data Source Policy / Local Snapshot Readiness Boundary
adds a documentation-only readiness boundary for future broad ETF source paths
and local snapshots. It defines candidate source-path categories, local
snapshot metadata requirements, adjustment/return-basis questions,
no-lookahead/as-of implications, repository/storage constraints, minimum
future implementation gates, and explicit non-claims. No source, data,
universe, benchmark, cash proxy, methodology, parameter, evidence, strategy
validation, or trading use was approved; no real data was added; no production
code or tests changed; and normal pytest remains offline and credential-free.

Phase 84 - Local Snapshot Manifest Metadata Contract adds a tiny deterministic
metadata-only `LocalSnapshotManifest` for describing future local research
snapshots without reading files, hashing files, checking paths, ingesting data,
or making local snapshots normal-pytest inputs. The contract validates plain
dates, observation date ordering, conservative source/adjustment/return-basis
allowlists, lowercase SHA-256 checksum shape, immutable tuple metadata,
required non-claims, and `normal_pytest_eligible=False`; it serializes to and
from deterministic primitive dictionaries. No source, data, universe,
benchmark, cash proxy, methodology, parameter, evidence, strategy validation,
or trading use was approved; no real data or ETF tickers were added; no
broker/order/fill/portfolio/runtime/LLM/network/market-data/scoring/ranking/
recommendation/candidate-discovery/signal/evaluator/rendering/trading behavior
was added; and normal pytest remains offline and credential-free.

Phase 86 - Synthetic Local Snapshot Manifest Fixture adds a tiny synthetic-only
`tests.fixtures.local_snapshot_manifest` consumer proving
`LocalSnapshotManifest` can be constructed, serialized, and round-tripped
deterministically in normal pytest. No production code changed, no real data or
local snapshot files were added, and the fixture remains metadata-only and
non-approving. Normal pytest remains offline and credential-free.

Phase 88 - Local Snapshot Return-Basis / As-Of Boundary adds a docs-only
interpretation boundary for future local snapshot metadata. It defines date
semantics, adjustment-policy interpretation, return-basis interpretation,
no-lookahead/as-of risks, future approval gates, and the relationship to the
metadata-only `LocalSnapshotManifest`. No source or data was approved, no
production code or tests changed, no real data was added, no manifest-to-
planning bridge was added, and normal pytest remains offline and
credential-free.

Phase 89 - Broad ETF Universe / Inception / Survivorship Boundary adds a
docs-only boundary for future broad ETF universe membership, inception
eligibility, survivorship and delisting risks, identifier questions,
no-lookahead universe rules, and minimum future approval gates. No universe or
ETF tickers were approved, no production code or tests changed, no real data
was added, and normal pytest remains offline and credential-free.

Phase 90 - Broad ETF Benchmark / Cash Timing Boundary adds a docs-only
boundary for future benchmark and cash-proxy interpretation. It defines
benchmark roles, benchmark return-basis requirements, cash proxy roles, cash
timing/publication risks, benchmark/cash no-lookahead rules, and future
approval gates. No benchmark or cash proxy was approved, no production code or
tests changed, no real data was added, and normal pytest remains offline and
credential-free.

Phase 91 - Broad ETF Cost / Friction Assumptions Boundary adds a docs-only
boundary for future transaction-cost, spread, slippage, liquidity, turnover,
rebalance, expense-ratio, tax, and implementation-friction assumptions. No
cost model or liquidity rule was approved, no production code or tests
changed, no real data was added, and normal pytest remains offline and
credential-free.

Phase 93 - Broad ETF Source Evidence Intake Plan adds a docs-only intake plan
for future review of candidate broad ETF source paths before any local
snapshot use. It defines candidate source-path categories, required evidence,
source-review questions, evidence labels, allowed review outcomes, forbidden
approval outcomes, a starter intake table, and explicit non-claims. No source
or data was approved, no production code or tests changed, no real data was
added, and normal pytest remains offline and credential-free.

Phase 94 - Broad ETF Source Evidence Normalization adds a docs-only
normalization of externally discovered broad ETF source-discovery output as
advisory intake material under the Phase 93 framework. It records candidate
source paths, separates primary-source needs from secondary/scout observations,
routes stronger and weaker later-review candidates, and records unresolved
questions. No source or data was approved, no production code or tests changed,
no real data was added, and normal pytest remains offline and credential-free.

Phase 95 - Broad ETF Primary Source Verification Normalization adds a
docs-only normalization of external primary-source verification output for
Stooq, Alpha Vantage, and FRED as advisory material only. It records reported
official docs and terms status, unresolved rights and methodology questions,
candidate confidence, and later-review ordering. No source, data, vendor,
benchmark, cash proxy, universe, methodology, parameter, evidence,
return-construction, no-lookahead, cost/friction, liquidity, strategy
validation, or trading use was approved; no production code or tests changed;
no real data was added; and normal pytest remains offline and credential-free.

Phase 96 - FRED Benchmark / Cash Rate Normalization Readiness adds a docs-only
readiness boundary for reviewing FRED as a future benchmark/cash/rate source
candidate only. It captures candidate use cases, Phase 95 advisory official-doc
findings, unresolved FRED questions, no-lookahead risks, future review gates,
allowed next steps, and explicit non-claims. No FRED series, cash proxy,
benchmark, rate source, source, data, universe, methodology, parameter,
evidence, return-construction, no-lookahead, cost/friction, liquidity,
strategy validation, or trading use was approved; no production code or tests
changed; no real data was added; and normal pytest remains offline and
credential-free.

Phase 97 - FRED Candidate Series Intake Plan adds a docs-only intake plan for
future review of possible FRED benchmark/cash/rate candidate series. It defines
candidate series roles, required per-series evidence, intake labels, allowed
candidate statuses, review questions, a placeholder starter intake table, and
future approval gates. No FRED series or cash proxy was approved, no production
code or tests changed, no real data was added, and normal pytest remains
offline and credential-free.

Phase 98 - FRED Candidate Series Discovery Normalization adds a docs-only
normalization of externally produced FRED candidate series discovery output as
advisory intake material under the Phase 97 framework. It records candidate
series such as TB3MS, TB6MS, EFFR, OBFR, the SOFR family, FEDFUNDS, UNRATE,
and generic non-official guide/blog references; separates reported official
source observations from secondary/scout observations; routes strongest,
context-only, and rejected-for-now candidates; records unresolved primary
source, ALFRED/vintage, timing, rights, conversion, and normal-pytest
questions; and recommends a later-review order. No FRED series, cash proxy,
benchmark, rate source, source, data, universe, methodology, parameter,
evidence, return-construction, no-lookahead, cost/friction, liquidity,
strategy validation, or trading use was approved; no production code or tests
changed; no real data was added; no FRED API calls or downloads occurred; and
normal pytest remains offline and credential-free.

Phase 99 - FRED TB3MS/TB6MS Primary Verification Normalization adds a
docs-only normalization of externally produced primary-verification output for
`TB3MS` and `TB6MS` as advisory material only. It records reportedly found
FRED series pages, FRED data/table pages, ALFRED pages, H.15 source/release
context, units, frequency, seasonal adjustment, observation-start metadata,
last-updated metadata, vintage notes, rights/terms caveats, point-in-time
questions, missing/stale questions, and discount-basis conversion questions.
Both series remain `candidate_for_later_series_review`. No FRED series, cash
proxy, benchmark, rate source, source, data, universe, methodology, parameter,
evidence, return-construction, no-lookahead, cost/friction, liquidity,
strategy validation, or trading use was approved; no production code or tests
changed; no real data was added; no FRED API calls or downloads occurred; and
normal pytest remains offline and credential-free.

Phase 101 - H.15 Discount-Basis Formula Normalization adds a docs-only
normalization of externally produced H.15 Treasury bill discount-basis formula
and convention discovery output as advisory methodology evidence only. It
records the reported TreasuryDirect bill pricing formula, 360-day year and
actual-days-to-maturity convention, H.15/FRED secondary-market discount-basis
classification for `TB3MS` and `TB6MS`, monthly-average and FRED
transformation uncertainties, daily quote construction uncertainties,
conversion/compounding risks, point-in-time and no-lookahead risks, official
source categories found, and a later-review recommendation. No formula
implementation was added, no conversion method was approved, no FRED series or
cash proxy was approved, no production code or tests changed, no real data was
added, no FRED API calls or downloads occurred, and normal pytest remains
offline and credential-free.

Phase 102 - H.15 Daily Quote / Monthly Averaging Normalization adds a
docs-only normalization of externally produced H.15 daily quote and monthly
averaging discovery output as advisory methodology context only. It records
reported H.15 posting schedule and aggregate averaging findings, daily
Treasury bill quote-construction gaps, FRED monthly provenance gaps,
revision/missing/stale uncertainty, point-in-time and no-lookahead risks, the
unproven relationship to Treasury daily bill-rate descriptions, and a
later-review recommendation. No averaging implementation was added, no formula
implementation was added, no conversion method was approved, no FRED series or
cash proxy was approved, no production code or tests changed, no real data was
added, no FRED/H.15 API calls or downloads occurred, and normal pytest remains
offline and credential-free.

Phase 104 - Alpha Vantage Primary Source Verification Normalization adds a
docs-only normalization of externally produced Alpha Vantage primary-source
verification output as advisory material only. It records reported official
API documentation, Terms of Service, support/rate-limit, premium/entitlement,
and realtime/market-data policy categories; time-series endpoint findings;
ETF coverage leads; adjustment, dividend, and split findings; survivorship,
listing-status, timestamp, revision, no-lookahead, terms, licensing, and
storage caveats; and an unresolved candidate disposition. Alpha Vantage
remains unresolved. No Alpha Vantage source, data, endpoint, universe,
benchmark, cash proxy, methodology, parameter, evidence, return-construction,
no-lookahead, cost/friction, liquidity, strategy validation, or trading use
was approved; no production code or tests changed; no real data was added; no
Alpha Vantage API calls or downloads occurred; and normal pytest remains
offline and credential-free.

Phase 105 - Alpha Vantage Public Docs Gap Normalization adds a docs-only
normalization of additional externally produced Alpha Vantage public-doc gap
review output as advisory material only. It records what public docs reportedly
answer, including endpoint, ETF-symbol, terms, realtime/delayed policy, and
listing-status leads; what remains unresolved across license/storage,
ETF/source-quality, adjustment, revision, point-in-time, survivorship, and
bulk-snapshot feasibility; and the support/legal questions needed before any
future local snapshot review. Alpha Vantage remains unresolved. No Alpha
Vantage source, data, endpoint, universe, benchmark, cash proxy, methodology,
parameter, evidence, return-construction, no-lookahead, cost/friction,
liquidity, strategy validation, or trading use was approved; no production
code or tests changed; no real data was added; no Alpha Vantage API calls or
downloads occurred; and normal pytest remains offline and credential-free.

Phase 106 - Stooq Public Docs Gap Normalization adds a docs-only normalization
of externally produced Stooq public-doc gap review output as advisory material
only. It records reported public CSV and bulk ASCII or Metastock-style download
surfaces, listed asset categories including ETF and U.S. ETF categories,
OHLCV-style availability, archive generation timestamps, third-party provider
references, adjustment UI controls, unresolved terms and storage questions,
unresolved schema/source-quality questions, unresolved adjustment and
point-in-time questions, and an unresolved candidate disposition. Stooq remains
unresolved. No Stooq source, data, download path, universe, benchmark, cash
proxy, methodology, parameter, evidence, return-construction, no-lookahead,
cost/friction, liquidity, strategy validation, or trading use was approved; no
production code or tests changed; no real data was added; no Stooq downloads
occurred; and normal pytest remains offline and credential-free.

Phase 107 - ETF Source Review Routing Checkpoint adds a docs-only routing
record after Alpha Vantage, Stooq, and Antigravity review. It records that
Alpha Vantage and Stooq remain unresolved, that the Antigravity review was
advisory and read-only, and that the project will not automatically redirect
to FRED unless a concrete ALFRED or point-in-time need emerges. No Alpha
Vantage, Stooq, FRED, source, data, endpoint, download path, universe,
benchmark, cash proxy, methodology, parameter, evidence, return-construction,
no-lookahead, cost/friction, liquidity, strategy validation, or trading use was
approved; no production code or tests changed; no real data was added; no API
calls or downloads occurred; and normal pytest remains offline and
credential-free.

Phase 108 - Polygon Public Docs Gap Normalization adds a docs-only
normalization of externally provided Polygon/Massive public-doc and
public-source verification output as advisory material only. It records
reported public documentation for aggregates, grouped daily aggregates, trades,
quotes, splits, dividends, reference tickers, ticker events, flat files,
API-key requirements, plan/pricing structure, split-adjusted aggregates, and
Market Data Terms non-redistribution language; unresolved license/storage,
ETF/source-quality, adjustment, and point-in-time questions; comparison to
Alpha Vantage and Stooq; and an unresolved candidate disposition.
Polygon/Massive remains unresolved and non-approved. No Polygon, Massive,
source, data, endpoint, flat-file path, universe, benchmark, cash proxy,
methodology, parameter, evidence, return-construction, no-lookahead,
cost/friction, liquidity, strategy validation, or trading use was approved; no
production code or tests changed; no real data was added; no API calls or
downloads occurred; and normal pytest remains offline and credential-free.

Phase 109 - ETF Source Candidate Comparison Checkpoint adds a docs-only
routing comparison of Alpha Vantage, Stooq, and Polygon/Massive after their
advisory source and public-doc reviews. It records that all candidates remain
unresolved and non-approved, compares technical surface, documentation,
terms/storage, adjustment/return-basis, point-in-time/revision,
survivorship/lifecycle, operational fit, blockers, disposition, and allowed
next steps, and recommends Polygon/Massive support/legal questions as the
smallest useful outreach path while keeping Nasdaq Data Link as a reasonable
external source-review alternative. No Alpha Vantage, Stooq, Polygon, Massive,
source, data, endpoint, download path, flat file, universe, benchmark, cash
proxy, methodology, parameter, evidence, return-construction, no-lookahead,
cost/friction, liquidity, strategy validation, or trading use was approved; no
production code or tests changed; no real data was added; no API calls or
downloads occurred; and normal pytest remains offline and credential-free.

Phase 110 - Polygon Deep Public Docs Normalization adds a docs-only
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
documented shapes. No source or data was approved; no production code or tests
changed; no real data was added; no API calls or downloads occurred; and
normal pytest remains offline and credential-free.

Phase 111 - Polygon Schema / Legal Routing Checkpoint adds a docs-only routing
decision after the deeper Polygon/Massive public-doc review. It records that
Alpha Vantage, Stooq, Polygon/Massive, and Nasdaq Data Link remain unresolved
and non-approved; that Polygon/Massive remains the strongest technical ETF
price-source candidate reviewed so far; and that the preferred next route is
candidate-only Polygon/Massive schema/interface normalization planning only if
it remains metadata-only and synthetic-only. Terms/legal review remains
required before any real Polygon/Massive data use, and Nasdaq Data Link
primary-source review remains the preferred alternative if schema/interface
planning is premature. No source or data was approved; no production code or
tests changed; no real data was added; no API calls or downloads occurred; and
normal pytest remains offline and credential-free.

Phase 112 - Polygon Candidate Schema / Interface Planning Boundary adds a
docs-only, candidate-only planning boundary for possible future
Polygon/Massive data normalization. It identifies candidate surfaces such as
aggregates, grouped daily aggregates, trades, quotes, reference tickers,
ticker details, ticker events, splits, dividends, flat files, ETF profile
surfaces, and possible calendar/session data; records metadata questions,
cross-surface risks, future implementation gates, and a future synthetic-only
fixture boundary; and keeps Polygon/Massive unresolved and non-approved. No
production code or tests changed; no fixtures changed; no real data was added;
no API calls or downloads occurred; no source, data, endpoint, or flat-file
approval was added; and normal pytest remains offline and credential-free.

Phase 113 - Synthetic Polygon Reference Ticker Fixture adds one tiny
synthetic-only Polygon/Massive-style reference ticker metadata fixture and a
focused normal-pytest unit test. The fixture uses primitive placeholder values
only, no real vendor data, no market-data rows, no API calls or downloads, no
credentials, and no `.data/` paths. No production code changed; no real data
was added; no source, data, endpoint, universe, benchmark, cash proxy,
evidence, return-construction, no-lookahead, strategy-validation, or trading
approval was added; and normal pytest remains offline and credential-free.

Phase 115 - Polygon/Massive Legal/PIT Source Decision Gate adds a docs-only
routing decision gate after the Polygon/Massive schema/interface boundary and
synthetic reference ticker fixture. It records current evidence, legal/storage
blockers, point-in-time/source-quality blockers, conservative decision rules,
and a recommended pause on additional Polygon/Massive synthetic fixtures that
involve prices, corporate actions, flat files, or return semantics. All
sources remain unresolved; no source or data was approved; no production code
or tests changed; no real data was added; no API calls or downloads occurred;
and normal pytest remains offline and credential-free.

Phase 116 - Source-Agnostic Synthetic Market Bar Fixture adds one tiny
source-agnostic synthetic market-bar fixture for primitive OHLCV-like research
input shape. No production code changed; no real data was added; no API calls
or downloads occurred; no source or data approval was added; and normal pytest
remains offline and credential-free.

Phase 117 - Source-Agnostic Synthetic Market Bar Sequence Fixture adds one
tiny source-agnostic synthetic market-bar sequence fixture using the Phase 116
bar shape. No production code changed; no real data was added; no API calls or
downloads occurred; no source or data approval was added; and normal pytest
remains offline and credential-free.

Phase 118 - Synthetic Market Bar Sequence Return Input Consumer adds a tiny
source-agnostic synthetic market-bar sequence return-input consumer in tests
and fixtures only. It extracts synthetic close values and feeds existing
close-to-close return-construction mechanics without adding production code,
real data, API calls, downloads, or source, data, or return-construction
approval. Normal pytest remains offline and credential-free.

Phase 120 - Source-Agnostic Research Return Input Snapshot Contract adds the
small frozen, slotted `ResearchReturnInputSnapshot` metadata contract for
already prepared observation dates, close values, and close-to-close returns.
It is source-agnostic, synthetic-only, candidate-only, immutable, and
deterministically serializes plain dates and Decimal values without adding real
data, API calls, downloads, file reads, ingestion, persistence, source or data
approval, return-construction approval, no-lookahead approval, strategy
approval or validation, trading readiness, or a market-bar production contract.
Normal pytest remains offline and credential-free.

Phase 121 - Synthetic Research Return Input Snapshot Fixture adds one tiny
deterministic fixture for the Phase 120 `ResearchReturnInputSnapshot`
contract. The fixture builds a reusable synthetic-only, candidate-only
snapshot and pins its primitive `to_dict()` representation for future tests.
It hard-codes artificial prepared observation dates, Decimal close values,
Decimal close-to-close returns, metadata, flags, and non-claims without
computing returns or adding production research, ingestion, market-bar,
strategy, evaluator, signal, benchmark, broker, runtime, persistence, or
trading behavior. No source, data, endpoint, universe, benchmark, cash proxy,
methodology, evidence, return-construction, no-lookahead, strategy-validation,
trading-readiness, or production-contract approval was added. Normal pytest
remains offline and credential-free.

Phase 122 - Research Return Input Snapshot Consistency Checker adds one tiny
deterministic internal checker for `ResearchReturnInputSnapshot`. It requires a
snapshot instance, recomputes exact Decimal close-to-close returns from the
prepared close values, compares them against the stored returns without
tolerance, rounding, quantization, annualization, or inferred values, and
returns the original object unchanged on success. Mismatched, malformed, or
non-snapshot inputs raise the project validation error. This is only an
arithmetic consistency aid for already prepared synthetic/candidate snapshots;
it adds no data access, source approval, endpoint approval, universe approval,
benchmark or cash proxy approval, methodology approval, evidence approval,
strategy, evaluator, signal, broker, runtime, persistence, portfolio mutation,
order generation, live/paper trading, trading readiness, market-bar production
contract, real data, vendor SDK, dependency, network call, credential, or file
I/O behavior. Normal pytest remains offline and credential-free.

Phase 123 - Research Return Input Snapshot Fingerprint adds one tiny
deterministic SHA-256 helper for `ResearchReturnInputSnapshot`. The helper first
uses the Phase 122 consistency checker, then hashes the snapshot's existing
primitive `to_dict()` payload serialized as sorted-key compact JSON and returns a
lowercase hex digest. Repeated calls, round-tripped snapshots, and unchanged
synthetic fixture content produce the same digest; different valid synthetic
content changes it. The digest is provenance support only and adds no data
access, source approval, endpoint approval, universe approval, benchmark or cash
proxy approval, methodology approval, evidence approval, signal, evaluator,
strategy, broker, runtime, persistence, portfolio mutation, order generation,
live/paper trading, trading readiness, production market-bar contract, real
data, vendor SDK, dependency, network call, credential, timestamp, local path,
environment lookup, or file I/O behavior. Normal pytest remains offline and
credential-free.

Phase 124 - Research Return Input Fingerprint / Serialization Hardening
clarifies the existing Phase 120-123 contracts and adds focused tests only.
`ResearchReturnInputSnapshot.from_dict()` is documented as serialization/schema
shape validation only, with no arithmetic consistency check. The consistency
helper is documented as an exact arithmetic check over already-prepared
snapshots with no rounding, tolerance, inference, or approval, and it still
returns the original snapshot object on success. The fingerprint helper is
documented as a deterministic content hash for candidate-only snapshots only; it
does not certify source, methodology, data, strategy, or downstream use. Tests
now pin digest stability through `to_dict()`/`from_dict()` round trips, primitive
payload mutation behavior, shape-valid arithmetic inconsistency acceptance by
`from_dict()`, consistency/fingerprint rejection of inconsistent snapshots, and
the existing Phase 121 fixture digest. No production behavior, ingestion,
runner, market-bar, strategy, evaluator, signal, broker/runtime, persistence,
portfolio mutation, order generation, trading behavior, real data, dependency,
network call, credential, or file I/O behavior was added. Normal pytest remains
offline and credential-free.

Phase 125 - Verified Research Return Input Package adds a tiny deterministic
`ResearchReturnInputPackage` contract that binds a
`ResearchReturnInputSnapshot` to its verified Phase 123 fingerprint after Phase
122 consistency validation. The builder preserves the original snapshot object,
returns an immutable package, and exposes only a primitive deterministic
`to_dict()` wrapper over the existing snapshot serialization and fingerprint.
Direct construction validates the snapshot type, lowercase SHA-256 fingerprint
shape, arithmetic consistency, and fingerprint match. This is provenance and
plumbing only; it adds no research runner, ingestion path, market-bar production
contract, strategy, signal, evaluator, benchmark or cash proxy logic, backtest,
broker/runtime behavior, persistence, scheduler behavior, portfolio mutation,
order generation, live/paper trading, trading readiness, real data, dependency,
network call, credential, or file I/O behavior. Normal pytest remains offline
and credential-free.

Phase 126 - Verified Research Return Input Package Deserialization adds narrow
deterministic `ResearchReturnInputPackage.from_dict()` plumbing for primitive
package payloads shaped only as `snapshot` plus `fingerprint`. The deserializer
rejects non-dicts, missing or unknown package fields, malformed nested snapshot
payloads, malformed lowercase SHA-256 fingerprint values, fingerprint mismatches,
and arithmetic-inconsistent reconstructed snapshots. Rebuilds always go through
`ResearchReturnInputSnapshot.from_dict()` and then the existing package
validation path, preserving current builder behavior and the existing
`to_dict()` output shape. This is provenance and serialization plumbing only; it
adds no research runner, ingestion path, market-bar production contract,
strategy, signal, evaluator, benchmark or cash proxy logic, backtest,
broker/runtime behavior, persistence, scheduler behavior, portfolio mutation,
order generation, live/paper trading, trading readiness, real data, dependency,
network call, credential, timestamp, environment lookup, local path, or file I/O
behavior. Normal pytest remains offline and credential-free.

Phase 127 - Verified Return Input Package Replay Adapter adds one narrow
deterministic adapter from `ResearchReturnInputPackage` into the existing
`SyntheticReplaySnapshot` metadata contract. The adapter requires an already
valid package, copies the package's prepared observation dates, prepared close
values, and stored close-to-close `Decimal` returns into replay metadata, and
does not call the replay builder that recomputes returns from values. Because
`SyntheticReplaySnapshot` has no dedicated package provenance field, the adapted
manifest carries the package snapshot id as `fixture_id` and the package
fingerprint as the manifest `checksum`; the manifest limitations document that
the required `available_after` values mirror observation dates as candidate
metadata only. This is deterministic metadata plumbing only; it adds no research
runner, ingestion path, file I/O, persistence, market-bar production contract,
strategy, signal, evaluator, benchmark or cash proxy logic, broker/runtime
behavior, scheduler behavior, portfolio mutation, order generation, live/paper
trading, trading readiness, real data, dependency, network call, credential,
timestamp, environment lookup, local path, source approval, data approval,
endpoint approval, universe approval, methodology approval, evidence approval,
return-construction approval, no-lookahead approval, strategy validation, or
production-contract approval. Normal pytest remains offline and credential-free.

Phase 128 - Verified Return Input Package Research Result Adapter adds one
narrow deterministic adapter from `ResearchReturnInputPackage` into the existing
`SyntheticResearchResult` contract. The adapter first reuses the Phase 127
package-to-replay adapter, preserving the package-derived manifest provenance
where the snapshot id is the manifest `fixture_id` and the package fingerprint
is the manifest `checksum`, then passes that replay snapshot to the existing
synthetic result builder. It adds no manual metrics, does not recompute returns
from prices, does not infer missing values, and does not introduce benchmarks,
cash returns, costs, positions, signals, orders, trades, strategy state, or
portfolio state. This remains synthetic candidate-only plumbing and does not
approve source, methodology, no-lookahead status, strategy validity, trading
readiness, or downstream use. It adds no research runner, ingestion path, file
I/O, persistence, market-bar production contract, evaluator behavior,
broker/runtime behavior, scheduler behavior, portfolio mutation, order
generation, live/paper trading, real data, dependency, network call, credential,
timestamp, environment lookup, local path, or production-contract approval.
Normal pytest remains offline and credential-free.

Phase 129 - Synthetic Return Input Result Fixture adds a tiny deterministic
test fixture that builds `SyntheticResearchResult` support through the existing
Phase 121 synthetic return-input snapshot fixture, the Phase 125 verified
package builder, and the Phase 128 package-to-result adapter. The helper exposes
both `build_synthetic_return_input_research_result()` and
`expected_synthetic_return_input_research_result_dict()`, with the expected
primitive payload delegated to stable `SyntheticResearchResult.to_dict()`
serialization. Provenance remains the Phase 127 convention: the package
snapshot id becomes the manifest `fixture_id`, and the manifest `checksum` is
`sha256:{package.fingerprint}`. The fixture does not compute returns from
prices, infer missing values, add metrics manually, mutate the source snapshot,
package, replay snapshot, or result, or introduce benchmarks, cash returns,
costs, positions, signals, orders, trades, strategy state, broker/runtime state,
portfolio state, ingestion, file I/O, persistence, runner behavior, real data,
network access, credentials, dependencies, or production-contract approval.
Normal pytest remains offline and credential-free.

Phase 130 - Return Input Research Result Provenance Verifier adds one narrow
deterministic verifier for confirming that an existing `SyntheticResearchResult`
matches a specific `ResearchReturnInputPackage` under the Phase 127 provenance
convention. The verifier requires the package and result contract types, checks
only that manifest `fixture_id` equals the package snapshot id and manifest
`checksum` equals `sha256:{package.fingerprint}`, and returns the original
result object unchanged on success. Mismatched or malformed inputs raise the
project validation error. It does not rebuild results, recompute returns, infer
missing values, mutate the package or result, introduce benchmarks, cash
returns, costs, positions, orders, trades, signals, strategy state,
broker/runtime fields, portfolio state, ingestion, file I/O, persistence,
runner behavior, real data, network access, credentials, dependencies, or
production-contract approval. It does not certify source, methodology,
no-lookahead status, strategy validity, trading readiness, or downstream use.
Normal pytest remains offline and credential-free.

Phase 131 - Return Input Research Chain Regression Guard adds a test-only
end-to-end regression guard for the existing Phase 120-130 return-input support
chain. The guard composes the Phase 121 synthetic
`ResearchReturnInputSnapshot` fixture, Phase 122 consistency validation, the
Phase 123 fingerprint helper pinned to
`07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2`,
Phase 125 package construction, Phase 126 package deserialization, Phase 127
replay adaptation, Phase 128 result adaptation, the Phase 129 result fixture,
and the Phase 130 provenance verifier. It verifies that consistency validation
returns the original snapshot object, package construction preserves snapshot
identity, package primitive round trips preserve fingerprint and snapshot
equality, replay adaptation preserves prepared observation order and stored
returns, result fixture output matches adapter output, provenance verification
returns the original result object, and the Phase 127 manifest convention still
uses the package snapshot id as `fixture_id` and `sha256:{package.fingerprint}`
as `checksum`. Repeated construction is deterministic, copied primitive payload
mutation fails existing validation/fingerprint/package/provenance checks, and
the test module self-audits for forbidden imports, calls, literal real-world
content, and disallowed payload fields. This phase adds no production behavior,
src changes, runner, ingestion path, file I/O, persistence, market-bar
production contract, strategy, signal, evaluator, benchmark or cash proxy
logic, broker/runtime behavior, scheduler behavior, portfolio mutation, order
generation, live/paper trading, real data, dependency, network call, credential,
source approval, data approval, endpoint approval, universe approval,
methodology approval, evidence approval, return-construction approval,
no-lookahead approval, strategy validation, trading readiness, or
production-contract approval. Normal pytest remains offline and credential-free.

Phase 132 - Candidate Research Result Dossier adds a tiny deterministic
metadata-only `CandidateResearchResultDossier` plus builder for wrapping an
existing `ResearchReturnInputPackage` and matching `SyntheticResearchResult`
after the Phase 130 provenance verifier accepts the pair. Construction
preserves the original package and result object identities, requires the fixed
advisory `candidate_only` status, and validates immutable non-empty limitations
and required non-claims. Those non-claims explicitly state that the dossier is
not source approval, data approval, endpoint approval, universe approval,
benchmark approval, cash proxy approval, methodology approval, evidence
approval, return-construction approval, no-lookahead approval, strategy
validation, trading readiness, production use, broker/runtime use, order
generation, or portfolio/allocation authority. `to_dict()` emits only
deterministic primitive metadata: package fingerprint, package snapshot id,
result manifest fixture id, result manifest checksum, status, limitations, and
non-claims. This phase adds no `from_dict()`, runner, ingestion path, file I/O,
persistence, market-bar production contract, strategy, signal, evaluator,
benchmark or cash proxy logic, broker/runtime behavior, scheduler behavior,
portfolio mutation, allocation behavior, order generation, live/paper trading,
real data, dependency, network call, credential, approval status, validation
claim, trading readiness, or production-contract approval. Normal pytest remains
offline and credential-free.

Phase 133 - Synthetic Candidate Research Result Dossier Fixture adds only a
tiny deterministic test fixture for `CandidateResearchResultDossier`. The
fixture composes the existing Phase 121 synthetic return-input snapshot fixture,
Phase 125 package builder, Phase 128 result adapter, and Phase 132 dossier
builder, then exposes both
`build_synthetic_candidate_research_result_dossier()` and
`expected_synthetic_candidate_research_result_dossier_dict()`. The expected
payload is exactly the dossier contract's `to_dict()` output. Tests pin the
Phase 123 fingerprint
`07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2`, preserve
the Phase 127 manifest convention that the fixture id comes from the package
snapshot id and the checksum is `sha256:{package.fingerprint}`, verify advisory
`candidate_only` status plus deterministic limitations and non-claims, check
object identity preservation where applicable, and self-audit the fixture module
for forbidden imports, calls, and real-world literals. This phase adds no
production behavior, `src/` changes, runner, ingestion path, file I/O,
persistence, market-bar production contract, strategy, signal, evaluator,
benchmark or cash proxy logic, broker/runtime behavior, scheduler behavior,
portfolio mutation, allocation behavior, order generation, live/paper trading,
real data, dependency, network call, credential, source approval, data approval,
endpoint approval, universe approval, methodology approval, evidence approval,
return-construction approval, no-lookahead approval, strategy validation,
trading readiness, or production-contract approval. Normal pytest remains
offline and credential-free.

Phase 134 - Candidate Research Brief Item adds a tiny deterministic,
metadata-only `CandidateResearchBriefItem` plus builder for deriving advisory
display metadata from an existing `CandidateResearchResultDossier`. The brief
item preserves dossier object identity, fixes `item_type` to
`candidate_research_result`, fixes status to `candidate_only`, derives a
deterministic headline and summary points only from dossier/package/result
metadata, and carries forward dossier limitations and non-claims. Direct
construction validates the dossier type, fixed item type, fixed status,
non-empty headline, immutable non-empty summary points, immutable non-empty
limitations, immutable non-empty non-claims, and preservation of the dossier's
required non-claims. `to_dict()` emits only deterministic primitive metadata:
item type, status, headline, summary points, package fingerprint, package
snapshot id, result manifest fixture id, result manifest checksum, limitations,
and non-claims. This phase adds no `from_dict()`, package re-export, runner,
ingestion path, file I/O, persistence, market-bar production contract,
strategy, signal, evaluator, benchmark or cash proxy logic, broker/runtime
behavior, scheduler behavior, portfolio mutation, allocation behavior, order
generation, live/paper trading, real data, dependency, network call,
credential, approval status, validation claim, trading readiness,
recommendation, action, or production-contract approval. Normal pytest remains
offline and credential-free.

Phase 135 - Synthetic Candidate Research Brief Item Fixture adds only a tiny
deterministic test fixture for `CandidateResearchBriefItem`. The fixture
composes the existing Phase 133 synthetic candidate dossier fixture with the
Phase 134 brief item builder, exposing
`build_synthetic_candidate_research_brief_item()` and
`expected_synthetic_candidate_research_brief_item_dict()`. The expected payload
matches `CandidateResearchBriefItem.to_dict()` exactly. Tests verify the fixed
`candidate_research_result` item type, advisory `candidate_only` status,
deterministic non-actionable headline and summary points, carried-forward
limitations and non-claims, required non-claim coverage, the Phase 123
fingerprint
`07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2`, and the
Phase 127 manifest fixture-id and `sha256:{package.fingerprint}` checksum
convention. The fixture self-audits for forbidden imports, calls, and
real-world literals, and repeated construction stays deterministic without
mutating source dossier, package, result, item, or primitive payloads. This
phase adds no production behavior, `src/` changes, runner, ingestion path, file
I/O, persistence, market-bar production contract, strategy, signal, evaluator,
benchmark or cash proxy logic, broker/runtime behavior, scheduler behavior,
portfolio mutation, allocation behavior, order generation, live/paper trading,
real data, dependency, network call, credential, approval status, validation
claim, trading readiness, recommendation, action, or production-contract
approval. Normal pytest remains offline and credential-free.

Phase 136 - Candidate Research Brief Section adds a frozen/slotted
`CandidateResearchBriefSection` plus
`build_candidate_research_brief_section()`. The section is fixed to
`candidate_research_results` with advisory `candidate_only` status and the
deterministic title `Candidate research results metadata`. The builder accepts
existing `CandidateResearchBriefItem` objects, normalizes them to an immutable
tuple, preserves object identity and caller-provided sequence exactly, rejects
empty or non-item payloads, and rejects duplicate item identities. Section
limitations and non-claims are deterministic metadata only, carry item
guardrails forward, and require the existing advisory non-claims to remain
present. `to_dict()` emits only primitive deterministic metadata: section type,
status, title, item count, item payloads, limitations, and non-claims; no
`from_dict()` is added. Tests cover direct construction validation,
serialization determinism, mutation resistance, required non-claim coverage,
forbidden field absence, and module-level import/call/text audits. The phase
does not re-export the section from package `__init__` and adds no LLM/agent,
runner, ingestion, file I/O, persistence, market-bar production contract,
strategy, signal, evaluator, benchmark or cash proxy logic, broker/runtime
behavior, scheduler behavior, portfolio mutation, allocation behavior, order
generation, live/paper trading, real data, dependency, network call,
credential, approval status, validation claim, trading readiness,
recommendation, action, or production-contract approval. Normal pytest remains
offline and credential-free.

Phase 137 - Synthetic Candidate Research Brief Section Fixture adds only a tiny
deterministic test fixture for `CandidateResearchBriefSection`. The fixture
composes the Phase 135 synthetic candidate research brief item fixture with the
Phase 136 section builder, exposing
`build_synthetic_candidate_research_brief_section()` and
`expected_synthetic_candidate_research_brief_section_dict()`. The expected
payload matches `CandidateResearchBriefSection.to_dict()` exactly. Tests verify
the fixed `candidate_research_results` section type, advisory `candidate_only`
status, deterministic non-actionable title, carried-forward limitations and
non-claims, required non-claim coverage, preserved item identity and ordering,
the Phase 123 fingerprint
`07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2`, and the
Phase 127 manifest fixture-id and `sha256:{package.fingerprint}` checksum
convention inside the section dict. The fixture self-audits for forbidden
imports, calls, and real-world literals, and repeated construction stays
deterministic without mutating source objects or primitive payloads. This phase
adds no production behavior, `src/` changes, LLM/agent behavior, runner,
ingestion path, file I/O, persistence, market-bar production contract,
strategy, signal, evaluator, benchmark or cash proxy logic, broker/runtime
behavior, scheduler behavior, portfolio mutation, allocation behavior, order
generation, live/paper trading, real data, dependency, network call,
credential, approval status, validation claim, trading readiness,
recommendation, action, ranking/scoring, or production-contract approval.
Normal pytest remains offline and credential-free.

Phase 138 - Candidate Research Brief Container adds only a tiny deterministic,
metadata-only `CandidateResearchBrief` in
`src/algotrader/research/candidate_research_brief.py` and focused unit coverage
in `tests/unit/test_candidate_research_brief.py`. The container groups existing
`CandidateResearchBriefSection` objects for future operating-brief and
research-queue surfaces without changing section, item, dossier, package,
result, snapshot, or manifest behavior. `build_candidate_research_brief()`
requires at least one section, normalizes the input to an immutable tuple,
preserves section object identity and input order exactly, rejects duplicate
section identities, fixes `brief_type` to `candidate_research_brief`, fixes
`status` to `candidate_only`, and carries deterministic limitations plus
required advisory non-claims forward. Direct construction validates the fixed
brief type and status, non-empty title, non-empty immutable section tuple,
non-empty immutable limitations and non-claims, section limitation/non-claim
carry-forward, and required non-claim coverage. `to_dict()` emits only
primitive deterministic metadata: brief type, status, title, section count,
section payloads, limitations, and non-claims; no `from_dict()` is added. Tests
verify determinism, identity/order preservation, no mutation, primitive-only
serialization, constructor rejection paths, forbidden import/call absence,
real-world literal absence, and absence of benchmark, cost, cash return,
position, order, trade, signal, strategy, broker/runtime, portfolio/allocation,
approval, recommendation, ranking/scoring, or trading-readiness fields. This
phase adds no LLM/agent behavior, runner, ingestion, file I/O, persistence,
database behavior, scheduler, runtime, notebook behavior, external-tool
behavior, market-bar production contract, strategy behavior, signal behavior,
evaluator behavior, benchmark or cash proxy logic, broker/runtime behavior,
portfolio mutation, allocation behavior, order generation, live/paper trading,
real data, dependency, network call, credential, approval status, validation
claim, trading readiness, recommendation, action, ranking/scoring, or
production-contract approval. Normal pytest remains offline and credential-free.

Phase 139 - Synthetic Candidate Research Brief Fixture adds only a tiny
deterministic test fixture for `CandidateResearchBrief`. The fixture composes
the Phase 137 synthetic candidate research brief section fixture with the Phase
138 brief builder, exposing `build_synthetic_candidate_research_brief()` and
`expected_synthetic_candidate_research_brief_dict()`. The expected payload
matches `CandidateResearchBrief.to_dict()` exactly. Tests verify the fixed
`candidate_research_brief` brief type, advisory `candidate_only` status,
deterministic non-actionable title, carried-forward limitations and non-claims,
required non-claim coverage, preserved section identity and ordering, fixed
section and item advisory types/statuses, the Phase 123 fingerprint
`07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2`, and the
Phase 127 manifest fixture-id and `sha256:{package.fingerprint}` checksum
convention inside the brief dict. The fixture self-audits for forbidden
imports, calls, and real-world literals, and repeated construction stays
deterministic without mutating source objects or primitive payloads. This phase
adds no production behavior, `src/` changes, LLM/agent behavior, runner,
ingestion path, file I/O, persistence, market-bar production contract,
strategy, signal, evaluator, benchmark or cash proxy logic, broker/runtime
behavior, scheduler behavior, portfolio mutation, allocation behavior, order
generation, live/paper trading, real data, dependency, network call,
credential, approval status, validation claim, trading readiness,
recommendation, action, ranking/scoring, or production-contract approval.
Normal pytest remains offline and credential-free.

Phase 140 - Candidate Research Brief Chain Regression Guard adds only a
test-only end-to-end regression guard in
`tests/unit/test_candidate_research_brief_chain_regression.py`. The guard
composes the existing Phase 132 `CandidateResearchResultDossier`, Phase 133
synthetic dossier fixture, Phase 134 brief item, Phase 135 brief item fixture,
Phase 136 brief section, Phase 137 brief section fixture, Phase 138 brief
container, and Phase 139 brief fixture, then proves the synthetic candidate
research result dossier reaches the final brief dict without drift. Tests pin
the Phase 123 fingerprint
`07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2`, preserve
the Phase 127 manifest fixture-id and `sha256:{package.fingerprint}` checksum
convention, verify fixed `candidate_research_brief`,
`candidate_research_results`, `candidate_research_result`, and `candidate_only`
advisory values, and confirm limitations plus required non-claims remain
present at dossier, item, section, and brief levels. The regression guard also
checks fixture determinism, builder identity/order preservation, repeated
full-chain determinism, primitive payload copy isolation, absence of forbidden
advisory/trading/runtime fields, and absence of forbidden imports, calls,
real-world literals, paths, credentials, dependencies, and provider markers in
the new test module. This phase adds no production behavior, `src/` changes,
LLM/agent behavior, runner, ingestion path, file I/O, persistence, market-bar
production contract, strategy, signal, evaluator, benchmark or cash proxy
logic, broker/runtime behavior, scheduler behavior, portfolio mutation,
allocation behavior, order generation, live/paper trading, real data,
dependency, network call, credential, approval status, validation claim,
trading readiness, recommendation, action, ranking/scoring, or
production-contract approval. Normal pytest remains offline and
credential-free.

Phase 141 - Research Return Input Provenance Contract adds only the frozen
`ResearchReturnInputProvenance` value object plus focused tests. The contract
explicitly encodes the Phase 127 convention that
`manifest.fixture_id == package.snapshot.snapshot_id` and
`manifest.checksum == sha256:{package.fingerprint}` while preserving the
existing manifest fields and all public payload shapes. The Phase 127 replay
adapter now uses the provenance builder internally when assigning those same
manifest values, and the Phase 130 result provenance verifier now uses the
same contract internally while preserving its public signature and return
object behavior. Tests cover builder output, direct-construction validation,
immutability, package/provenance matching, mismatch rejection, adapter
manifest output, result verifier identity preservation, regression-chain
payload stability, no mutation, and source-audit checks for forbidden
imports, calls, literals, dependencies, paths, credentials, and runtime or
trading concepts. This phase adds no ingestion, persistence, runner,
operating brief, LLM/agent behavior, market-bar production contract,
strategy, signal, evaluator, benchmark or cash proxy logic, broker/runtime
behavior, portfolio mutation, allocation behavior, order generation,
live/paper trading, real data, dependency, network call, credential,
approval status, validation claim, trading readiness, recommendation, action,
ranking/scoring, or production-contract approval. Normal pytest remains
offline and credential-free.

Phase 142 - Advisory Operating Brief Container adds only the frozen/slotted,
metadata-only `AdvisoryOperatingBrief` in
`src/algotrader/research/advisory_operating_brief.py` with focused unit
coverage in `tests/unit/test_advisory_operating_brief.py`. The container groups
existing `CandidateResearchBrief` objects for future operating-brief display
surfaces, fixes `operating_brief_type` to `advisory_operating_brief`, fixes
status to advisory `candidate_only`, preserves candidate brief object identity
and caller-provided sequence exactly, rejects empty inputs, non-brief inputs,
duplicate brief identities, forbidden brief types, approval-like statuses, and
malformed title, limitations, or non-claims. The builder carries candidate
brief limitations and non-claims forward without adding approval semantics, and
`to_dict()` emits only deterministic primitive metadata: operating brief type,
status, title, candidate brief count, nested candidate brief payloads,
limitations, and non-claims. Tests prove determinism, primitive serialization,
input non-mutation, package digest visibility, Phase 127/141 provenance
visibility, no package `__init__` re-export, and source-level import/call/text
guardrails. This phase adds no `from_dict()`, LLM/agent behavior, ingestion,
persistence, file I/O, local snapshot loading, scheduler, CLI, runtime
behavior, market-bar production contract, strategy, signal, evaluator,
benchmark or cash proxy logic, backtesting engine, broker/runtime behavior,
portfolio mutation, allocation behavior, order generation, live/paper trading,
real data, dependency, network call, credential, source approval, data
approval, methodology approval, evidence approval, strategy validation,
trading readiness, recommendation, ranking/scoring, or production-contract
approval. Normal pytest remains offline and credential-free.

Phase 143 - Synthetic Advisory Operating Brief Fixture replaces the older broad
test fixture in `tests/fixtures/advisory_operating_brief.py` with a tiny
deterministic fixture for the Phase 142 `AdvisoryOperatingBrief` surface and
adds focused fixture coverage in
`tests/unit/test_advisory_operating_brief_fixture.py`. The fixture builds only
through the Phase 139 synthetic candidate research brief fixture and the Phase
142 `build_advisory_operating_brief()` builder, preserves candidate brief
object identity and input sequence where applicable, and exposes
`build_synthetic_advisory_operating_brief()` plus
`expected_synthetic_advisory_operating_brief_dict()`. The expected payload is
exactly `AdvisoryOperatingBrief.to_dict()`, including the fixed
`advisory_operating_brief` type, advisory `candidate_only` status,
deterministic non-actionable title, nested candidate brief/section/item
advisory values, carried-forward limitations and non-claims, the Phase 123
digest `07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2`,
and the Phase 127/141 manifest convention that the fixture id comes from the
package snapshot id and the checksum is `sha256:{package.fingerprint}`. Tests
prove repeated-call determinism, primitive serialization copy isolation,
source-object non-mutation, absence of forbidden payload/object fields, and
fixture-module import/call/text guardrails. This phase adds no `src/` changes,
LLM/agent behavior, ingestion, persistence, runner, file I/O, local snapshot
loading, CLI, scheduler, runtime behavior, market-bar production contract,
strategy, signal, evaluator, benchmark or cash proxy logic, backtesting engine,
broker/runtime behavior, portfolio mutation, allocation behavior, order
generation, live/paper trading, real data, dependency, network call,
credential, source approval, endpoint approval, universe approval, methodology
approval, evidence approval, validation claim, trading readiness,
recommendation, ranking/scoring, or production-contract approval. Normal pytest
remains offline and credential-free.

Phase 144 - Advisory Operating Brief Chain Regression Guard adds only focused
unit coverage in
`tests/unit/test_advisory_operating_brief_chain_regression.py`. The guard proves
the Phase 139 synthetic candidate research brief fixture can pass through the
Phase 142 `AdvisoryOperatingBrief` contract and the Phase 143 synthetic
advisory operating brief fixture without payload drift. It pins the Phase 123
digest `07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2`,
verifies the Phase 127/141 manifest convention remains visible in the final
operating brief dict, checks fixed advisory type/status values through the
operating brief, candidate brief, section, item, and dossier chain, and proves
carried-forward limitations and non-claims remain present. Tests also cover
repeated full-chain determinism, object identity and sequence preservation where
applicable, primitive payload copy isolation, absence of forbidden advisory or
trading payload fields, and source-level import/call/text guardrails for the new
test module. This phase adds no `src/` changes, production behavior, LLM/agent
behavior, ingestion, persistence, runner, file I/O, local snapshot loading, CLI,
scheduler, runtime behavior, market-bar production contract, strategy, signal,
evaluator, benchmark or cash proxy logic, broker/runtime behavior, portfolio
mutation, allocation behavior, order generation, live/paper trading, real data,
dependency, network call, credential, source approval, endpoint approval,
universe approval, methodology approval, evidence approval, validation claim,
trading readiness, recommendation, ranking/scoring, or production-contract
approval. Normal pytest remains offline and credential-free.

Phase 145 - Advisory Operating Brief Text Renderer adds one narrow display-only
helper in `src/algotrader/research/advisory_operating_brief_renderer.py` and
focused coverage in
`tests/unit/test_advisory_operating_brief_renderer.py`. The renderer requires an
existing `AdvisoryOperatingBrief`, reads only its deterministic `to_dict()`
payload, and emits stable plain text with fixed headings. It preserves the
existing candidate brief, section, and item sequence exactly; includes fixed
advisory type/status metadata, limitations, and non-claims; and carries through
the Phase 123 digest plus the Phase 127/141 manifest convention fields when
they are visible in nested payloads. Tests prove fixture acceptance, invalid
input rejection, repeated-render determinism, sequence preservation,
non-mutation, source-level import/call/text guardrails, no package `__init__`
re-export, and that the renderer output uses only existing operating brief
data. This phase adds no parser, `from_text`, markdown writer, CLI, dashboard,
notebook, persistence, file I/O, local snapshot loading, scheduler, runtime
behavior, LLM/agent behavior, ingestion, market-bar production contract,
strategy, signal, evaluator, benchmark or cash proxy logic, backtesting engine,
broker/runtime behavior, portfolio mutation, allocation behavior, order
generation, live/paper trading, real data, dependency, network call,
credential, source approval, endpoint approval, universe approval, methodology
approval, evidence approval, validation claim, trading readiness,
recommendation, ranking/scoring, or production-contract approval. Normal pytest
remains offline and credential-free.

Phase 146 - Advisory Operating Brief Rendered Text Regression Guard adds a
test-only exact rendered-text pin in
`tests/unit/test_advisory_operating_brief_renderer_regression.py` using the
Phase 143 synthetic advisory operating brief fixture and the Phase 145
renderer. The guard compares the full deterministic line tuple, proves repeated
renders are byte-for-byte identical, checks fixed advisory type/status values,
preserves nested candidate brief/section/item sequence, carries through the
Phase 123 digest and Phase 127/141 manifest fixture/checksum convention, and
confirms limitations and non-claims remain visible. It also proves copied text
and copied primitive payload edits do not mutate the source operating brief,
and keeps import/call/literal guardrails in the test module. This phase adds no
`src/` changes, production behavior, parser, `from_text`, markdown writer, CLI,
dashboard, notebook, persistence, file I/O, local snapshot loading, scheduler,
runtime behavior, LLM/agent behavior, ingestion, market-bar production
contract, strategy, signal, evaluator, benchmark or cash proxy logic,
backtesting engine, broker/runtime behavior, portfolio mutation, allocation
behavior, order generation, live/paper trading, real data, dependency, network
call, credential, source approval, endpoint approval, universe approval,
methodology approval, evidence approval, validation claim, trading readiness,
recommendation, ranking/scoring, or production-contract approval. Normal pytest
remains offline and credential-free.

Phase 147 - Advisory Operating Brief In-Memory Export Helper adds a tiny
export-format helper in
`src/algotrader/research/advisory_operating_brief_export.py` with focused
coverage in `tests/unit/test_advisory_operating_brief_export.py`. The helper
requires an existing `AdvisoryOperatingBrief`, snapshots its deterministic
primitive `to_dict()` payload, emits compact sorted-key JSON with
`json.dumps(..., sort_keys=True, separators=(",", ":"))`, and delegates
rendered text to the existing Phase 145 renderer. Tests prove Phase 143 fixture
acceptance, invalid input rejection, frozen export fields, primitive payload
equality and copy isolation from source objects, byte-for-byte JSON
determinism, sorted/compact JSON behavior, JSON round-trip equality in tests,
rendered-text equivalence, repeated export determinism, Phase 123 digest
visibility, Phase 127/141 provenance convention visibility, fixed advisory
type/status visibility, no package `__init__` re-export, and source-level
import/call/literal guardrails. This phase adds no file I/O, parser,
deserializer, CLI, dashboard, notebook, persistence, local snapshot loading,
scheduler, runtime behavior, LLM/agent behavior, ingestion, market-bar
production contract, strategy, signal, evaluator, benchmark or cash proxy
logic, backtesting engine, broker/runtime behavior, portfolio mutation,
allocation behavior, order generation, live/paper trading, real data,
dependency, network call, credential, source approval, endpoint approval,
universe approval, methodology approval, evidence approval, validation claim,
trading readiness, recommendation, ranking/scoring, or production-contract
approval. Normal pytest remains offline and credential-free.

Phase 148 - Advisory Operating Brief Export Regression Guard adds a test-only
exact-output pin in
`tests/unit/test_advisory_operating_brief_export_regression.py` using the Phase
143 synthetic advisory operating brief fixture and the Phase 147 in-memory
export helper. The guard pins the compact JSON string, rendered line tuple,
payload key shape, repeated byte-for-byte export determinism, JSON round-trip
equality to the primitive payload, renderer equivalence to the Phase 145
renderer, exported-payload copy isolation from source objects, Phase 123 digest
visibility, Phase 127/141 provenance convention visibility, fixed advisory
type/status values, limitations, non-claims, and test-module
import/call/literal guardrails. This phase changes no `src/` files and adds no
production behavior, file I/O, parser, deserializer, CLI, dashboard, notebook,
persistence, local snapshot loading, scheduler, runtime behavior, LLM/agent
behavior, ingestion, market-bar production contract, strategy, signal,
evaluator, benchmark or cash proxy logic, backtesting engine, broker/runtime
behavior, portfolio mutation, allocation behavior, order generation,
live/paper trading, real data, dependency, network call, credential, source
approval, endpoint approval, universe approval, methodology approval, evidence
approval, validation claim, trading readiness, recommendation,
ranking/scoring, or production-contract approval. Normal pytest remains
offline and credential-free.

Phase 149 - Advisory Operating Brief CLI Preview adds a tiny developer preview
subcommand, `algotrader advisory-operating-brief-preview`, plus the narrow
production-safe synthetic preview builder in
`src/algotrader/research/advisory_operating_brief_cli.py`. The command builds
the same synthetic advisory operating brief payload as the Phase 143 fixture
without importing `tests.fixtures` from production code, exports it through the
Phase 147 in-memory helper, and writes only the selected export view to stdout:
rendered text by default or compact JSON with `--format json`. Focused tests in
`tests/unit/test_advisory_operating_brief_cli.py` prove parser registration,
Phase 143 fixture equivalence, byte-for-byte deterministic text and JSON
output, no file/path arguments, no file I/O, no environment reads, no network
access, no broker/runtime/vendor/LLM imports during preview invocation, fixed
type/status visibility, Phase 123 digest visibility, Phase 127/141 provenance
visibility, limitations and non-claims visibility, no extra decision language,
source-object non-mutation, and source-level import/call/literal guardrails.
The preview remains synthetic, offline, credential-free, and advisory only; it
adds no file output, input path, config/env loading, current time/date, random
value, real data loading, ingestion, persistence, scheduler/runtime behavior,
dashboard behavior, notebook behavior, external-tool behavior, LLM/agent
behavior, broker/runtime behavior, strategy/signal/evaluator behavior,
recommendation, ranking/scoring, allocation, order generation, source approval,
endpoint approval, universe approval, methodology approval, evidence approval,
validation claim, trading readiness, live/paper trading, or production-contract
approval.

Phase 150 - Advisory Operating Brief CLI Preview Regression Guard adds a
test-only exact-output pin in
`tests/unit/test_advisory_operating_brief_cli_regression.py` for the synthetic
developer preview command. The guard invokes the existing CLI entrypoint,
proves default stdout equals the Phase 145 renderer pin, proves
`--format json` stdout equals the Phase 147 compact JSON pin, parses the JSON
back to the expected primitive export payload, checks repeated CLI invocations
are byte-for-byte deterministic, and verifies fixed advisory type/status
values, the Phase 123 digest, Phase 127/141 provenance fields, limitations,
non-claims, parser-surface boundaries, no mutation of the synthetic brief
object, no added decision language outside the payload, and test-module
import/call/literal guardrails. This phase changes no `src/` files and adds no
production behavior, file I/O, path argument, file output, local snapshot
loading, persistence, database behavior, scheduler/runtime behavior, dashboard
behavior, notebook behavior, external-tool behavior, LLM/agent behavior,
broker/runtime behavior, strategy/signal/evaluator behavior, benchmark or cash
logic, portfolio/allocation mutation, order generation, real data, ingestion,
vendor API, credential, dependency, source approval, endpoint approval,
universe approval, methodology approval, evidence approval, validation claim,
no-lookahead claim, trading readiness, recommendation, ranking/scoring, or
production-contract approval. Normal pytest remains offline, deterministic,
and credential-free.

Phase 151 - Advisory Operating Brief Review Checklist Contract adds
`src/algotrader/research/advisory_operating_brief_review.py` and focused
coverage in `tests/unit/test_advisory_operating_brief_review.py`. The contract
accepts only an existing Phase 147/150 in-memory advisory operating brief
export, validates malformed export objects strictly, and returns a frozen,
slotted, metadata-only `AdvisoryOperatingBriefReviewChecklist` with fixed
`review_type` and `candidate_only` status. The checklist records deterministic
booleans for candidate-only status, advisory-only type shape, limitations,
non-claims, the Phase 123 fingerprint, and Phase 127/141 provenance
convention; it also records any blocked capital-authority field or language
paths as findings only. Serialization is primitive-only and deterministic via
`to_dict()`, tuple fields remain immutable, repeated construction produces
identical dictionaries, and the source export payload is not mutated. This
phase adds no CLI behavior, file I/O, local snapshot loading, persistence,
database behavior, dashboard behavior, scheduler/runtime behavior, notebook
behavior, external-tool behavior, LLM/agent behavior, broker/runtime behavior,
strategy/signal/evaluator behavior, benchmark or cash logic,
portfolio/allocation mutation, order generation, ranking/scoring,
recommendation, approval, real data, ingestion, vendor API, credential, or
dependency.

Phase 152 - Advisory Operating Brief Review Checklist Regression Guard adds a
test-only exact-output pin in
`tests/unit/test_advisory_operating_brief_review_regression.py` for the Phase
151 checklist contract. The guard builds the checklist only from the existing
synthetic Phase 147/150 in-memory advisory operating brief export chain, pins
the exact deterministic `to_dict()` payload, separately pins the source
export's candidate/advisory metadata, limitations, non-claims, Phase 123
fingerprint, and Phase 127/141 provenance convention, proves repeated
construction is dict-equal and byte-identical, proves tuple fields serialize to
primitive lists, and proves checklist construction does not mutate the source
export payload or text views. It also keeps injected capital-authority metadata
as checklist findings only and adds test-module import/call/literal guardrails
to prevent accidental broker, order, allocation, approval, or trading-authority
language outside explicit forbidden findings and negative non-claims. This
phase changes no `src/` files and adds no CLI behavior, file I/O, persistence,
dashboard behavior, runtime/scheduler behavior, network/socket access,
credentials, vendor API access, notebooks, LLM/agent behavior,
broker/runtime behavior, strategy/signal/evaluator behavior, ranking/scoring,
recommendations, allocation authority, orders, portfolio mutation, trading
readiness, source approval, methodology approval, validation approval, or
trading authority. Normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 153 - Advisory Strategy Eligibility Status Contract adds
`src/algotrader/research/strategy_eligibility_status.py` with focused coverage
in `tests/unit/test_strategy_eligibility_status.py`. The contract is a frozen,
slotted, metadata-only `StrategyEligibilityStatus` plus
`build_strategy_eligibility_status(...)` for describing a strategy candidate's
current advisory eligibility state. It pins `eligibility_type` to
`strategy_eligibility_status`, `authority` to `advisory_only`, and
`capital_authority` to `False`; permits only `research_only`,
`watchlist_only`, and `blocked`; and rejects paper, live, authorized,
trading-ready, approval-like, or trading-action state values. Required string
and tuple/list metadata is validated strictly, bools are rejected where strings
are expected, list inputs are copied into immutable tuples, and `to_dict()`
emits deterministic primitive dictionaries with tuple fields serialized as
lists. Required non-claims explicitly state that the contract is not
validation, not paper readiness, not live readiness, not a trading
recommendation, not allocation authority, and not order authority. The phase
adds no strategy execution behavior, signal/evaluator behavior, backtesting,
broker/runtime behavior, order generation, allocation, portfolio mutation,
reconciliation mutation, scheduler behavior, dashboard behavior, CLI behavior,
file I/O, persistence, network/socket access, credentials, vendor API,
LLM/agent behavior, notebook behavior, source approval, universe approval,
benchmark approval, methodology approval, validation approval, paper readiness,
live readiness, trading recommendation, trading authority, or dependency.
Normal pytest remains offline, credential-free, deterministic, and safe.

Phase 154 - Synthetic Strategy Eligibility Status Fixture adds
`tests/fixtures/strategy_eligibility_status.py` and focused coverage in
`tests/unit/test_strategy_eligibility_status_fixture.py`. The fixture builds a
single deterministic synthetic `research_only` `StrategyEligibilityStatus`
through the Phase 153 public `build_strategy_eligibility_status(...)` helper and
provides an exact expected primitive dictionary helper for later advisory
operating brief components. The pinned metadata includes stable synthetic
strategy id/name, reasons, limitations, negative non-claims, evidence refs,
blockers, and required next steps; `to_dict()` remains primitive-only with
tuple fields serialized as lists, repeated construction produces identical
dictionaries and compact JSON bytes, and helper payloads return fresh lists so
callers cannot mutate fixture source collections.

The fixture explicitly remains research-only and advisory-only. Its non-claims
state that it is not validation, not paper readiness, not live readiness, not a
trading recommendation, not allocation authority, not order authority, not
profitability evidence, not approval, and not capital authority. Guardrail tests
pin the allowed imports/calls and prove no broker/order/allocation/trading
authority fields, states, or runtime paths were added. This phase changes no
`src/` files and adds no CLI behavior, file I/O, persistence, dashboard
behavior, runtime/scheduler behavior, network/socket access, credentials,
vendor APIs, notebooks, LLM/agent behavior, broker/runtime behavior,
strategy/signal/evaluator behavior, backtesting behavior, ranking/scoring,
recommendations, allocation authority, orders, portfolio mutation, trading
readiness, source approval, methodology approval, validation approval, or
trading authority. Normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 155 - Advisory Strategy Eligibility Brief Item adds
`src/algotrader/research/strategy_eligibility_brief_item.py` with focused
coverage in `tests/unit/test_strategy_eligibility_brief_item.py`. The contract
is a frozen, slotted, metadata-only `StrategyEligibilityBriefItem` plus
`build_strategy_eligibility_brief_item(...)`, and it requires an exact
`StrategyEligibilityStatus` source object while preserving that object's
identity. It pins `item_type` to `strategy_eligibility_brief_item`, `status` to
`candidate_only`, `authority` to `advisory_only`, and `capital_authority` to
`False`; carries forward strategy id/name, eligibility state, reasons,
limitations, non-claims, evidence refs, blockers, and required next steps; and
adds deterministic advisory-only `headline` and `summary` text from safe source
metadata counts.

`to_dict()` emits deterministic primitive-only metadata with tuple fields
serialized as lists and includes the nested source status `to_dict()` payload.
Tests pin exact fixture-derived dictionaries and compact JSON, prove repeated
construction is identical, prove source status objects are not mutated, reject
non-status and malformed status-like objects, reject direct constructor metadata
that diverges from the source, and guard against adding paper/live/approved or
trading-ready states through the item. AST guardrails pin allowed imports/calls,
prove there is no `from_dict()`, and prove no broker, order, allocation,
portfolio, runtime, scheduler, dashboard, persistence, network/socket, vendor,
ML, LLM, pandas, numpy, vectorbt, QuantConnect, file I/O, CLI, strategy
execution, signal/evaluator, backtesting, allocation, order generation,
portfolio mutation, approval, readiness, or capital-authority behavior was
added. Normal pytest remains offline, credential-free, deterministic, and safe.

Phase 156 - Synthetic Strategy Eligibility Brief Item Fixture adds
`tests/fixtures/strategy_eligibility_brief_item.py` and focused coverage in
`tests/unit/test_strategy_eligibility_brief_item_fixture.py`. The fixture builds
a deterministic synthetic `StrategyEligibilityBriefItem` by composing the Phase
154 `build_synthetic_strategy_eligibility_status()` fixture through the Phase
155 public `build_strategy_eligibility_brief_item(...)` helper, preserving
validation and source status identity. Its expected dictionary helper composes
fresh primitive top-level lists while nesting the exact Phase 154 expected
status dictionary payload, pins `item_type` to
`strategy_eligibility_brief_item`, `status` to `candidate_only`, `authority` to
`advisory_only`, `capital_authority` to `False`, and pins deterministic
advisory-only headline and summary text.

The Phase 156 tests prove the fixture builds a `StrategyEligibilityBriefItem`
with a `StrategyEligibilityStatus` source, emits the exact expected primitive
dictionary and compact JSON bytes across repeated construction, serializes tuple
fields as lists, carries forward limitations and negative non-claims, and
returns fresh helper lists so payload mutation cannot affect source objects or
later helper calls. Guardrails prove the fixture added no forbidden broker,
order, allocation, trading-authority, account, portfolio, paper/live readiness,
approval, recommendation, capital authority, runtime, scheduler, dashboard,
file I/O, persistence, network/socket, credential, vendor API, notebook,
LLM/agent, strategy/signal/evaluator, backtesting, ranking/scoring, order,
portfolio mutation, trading readiness, source approval, methodology approval,
validation approval, or dependency behavior. This phase changes no `src/`
files, and normal pytest remains offline, credential-free, deterministic, and
safe.

Phase 157 - Advisory Strategy Eligibility Brief Section adds
`src/algotrader/research/strategy_eligibility_brief_section.py` with focused
coverage in `tests/unit/test_strategy_eligibility_brief_section.py`. The
contract defines a frozen, slotted, metadata-only
`StrategyEligibilityBriefSection` plus
`build_strategy_eligibility_brief_section(...)`, requires at least one exact
`StrategyEligibilityBriefItem`, rejects malformed item-like objects and
duplicate item identities, converts item collections to immutable tuples, and
preserves source item identity and input sequence. Fixed metadata is pinned to
`section_type=strategy_eligibility_brief_section`, `status=candidate_only`,
`authority=advisory_only`, and `capital_authority=False`.

The Phase 157 section derives only deterministic advisory title and summary
text from source item metadata, nests item `to_dict()` payloads in the original
sequence, carries forward limitations and non-claims with exact duplicate
strings removed, and emits primitive-only dictionaries plus pinned compact
JSON across repeated construction. Tests prove the Phase 156 synthetic item
fixture composes into the section without mutating the source item and that
paper/live/approved/trading-ready states remain impossible through section
metadata. AST and literal guardrails prove the module imports no forbidden
network, vendor, broker, runtime, scheduler, dashboard, persistence, file I/O,
ML, LLM/agent, pandas, numpy, vectorbt, QuantConnect, signal/evaluator,
backtesting, allocation, order, account, portfolio, or new dependency behavior.
Normal pytest remains offline, credential-free, deterministic, and safe.

Phase 158 - Synthetic Strategy Eligibility Brief Section Fixture adds
`tests/fixtures/strategy_eligibility_brief_section.py` and focused coverage in
`tests/unit/test_strategy_eligibility_brief_section_fixture.py`. The fixture
builds a deterministic `StrategyEligibilityBriefSection` by composing the Phase
156 `build_synthetic_strategy_eligibility_brief_item()` fixture through the
Phase 157 public `build_strategy_eligibility_brief_section(...)` helper, so it
does not bypass validation. Its expected dictionary helper derives from the
Phase 156 expected item dictionary, nests that exact item payload, pins
`section_type=strategy_eligibility_brief_section`, `status=candidate_only`,
`authority=advisory_only`, `capital_authority=False`, and pins deterministic
advisory-only title and summary text.

The Phase 158 tests prove the fixture builds a
`StrategyEligibilityBriefSection` containing a Phase 156
`StrategyEligibilityBriefItem`, emits the exact expected primitive dictionary
and compact JSON bytes across repeated construction, serializes section tuple
fields as lists, carries forward limitations and negative non-claims from the
nested item, and returns fresh helper payloads so payload mutation cannot affect
source objects or later helper calls. Guardrails prove the fixture added no
forbidden broker, order, allocation, trading-authority, account, portfolio,
paper/live readiness, approval, recommendation, capital authority, runtime,
scheduler, dashboard, file I/O, persistence, network/socket, credential, vendor
API, notebook, LLM/agent, strategy/signal/evaluator, backtesting,
ranking/scoring, order, portfolio mutation, trading readiness, source approval,
methodology approval, validation approval, or dependency behavior. This phase
changes no `src/` files, and normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 159 - Advisory Strategy Eligibility Brief Container adds
`src/algotrader/research/strategy_eligibility_brief.py` with focused coverage
in `tests/unit/test_strategy_eligibility_brief.py`. The contract defines a
frozen, slotted, metadata-only `StrategyEligibilityBrief` plus
`build_strategy_eligibility_brief(...)`, requires at least one exact
`StrategyEligibilityBriefSection`, rejects non-sections, malformed
section-like objects, empty collections, and duplicate section identities,
converts section collections to immutable tuples, and preserves source section
identity and input sequence. Fixed metadata is pinned to
`brief_type=strategy_eligibility_brief`, `status=candidate_only`,
`authority=advisory_only`, and `capital_authority=False`.

The Phase 159 brief derives only deterministic advisory title and summary text
from source section metadata, nests section `to_dict()` payloads in the
original sequence, carries forward limitations and non-claims with exact
duplicate strings removed, and emits primitive-only dictionaries plus pinned
compact JSON across repeated construction. Tests prove the Phase 158 synthetic
section fixture composes into the brief without mutating the source section
and that paper/live/approved/trading-ready states remain impossible through
brief metadata. AST and literal guardrails prove the module imports no
forbidden network, vendor, broker, runtime, scheduler, dashboard, persistence,
file I/O, ML, LLM/agent, pandas, numpy, vectorbt, QuantConnect,
signal/evaluator, backtesting, allocation, order, account, portfolio, or new
dependency behavior. Normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 160 - Synthetic Strategy Eligibility Brief Fixture adds
`tests/fixtures/strategy_eligibility_brief.py` and focused coverage in
`tests/unit/test_strategy_eligibility_brief_fixture.py`. The fixture builds a
deterministic `StrategyEligibilityBrief` by composing the Phase 158
`build_synthetic_strategy_eligibility_brief_section()` fixture through the
Phase 159 public `build_strategy_eligibility_brief(...)` helper, so validation
is not bypassed. Its expected dictionary helper returns the exact primitive
brief payload with the exact Phase 158 expected section dictionary nested in
`sections`, fresh top-level limitation and non-claim lists, and pinned
`brief_type=strategy_eligibility_brief`, `status=candidate_only`,
`authority=advisory_only`, `capital_authority=False`, title, and summary.

The Phase 160 tests prove the fixture builds a `StrategyEligibilityBrief`
containing a Phase 158 `StrategyEligibilityBriefSection`, emits exact expected
primitive dictionaries and compact JSON bytes across repeated construction,
serializes tuple fields as lists, carries forward limitations and negative
non-claims from the nested section, and returns fresh helper payloads so
payload mutation cannot affect source objects or later helper calls. Guardrails
prove the fixture added no forbidden broker, order, allocation,
trading-authority, account, portfolio, paper/live readiness, approval,
recommendation, capital authority, runtime, scheduler, dashboard, file I/O,
persistence, network/socket, credential, vendor API, notebook, LLM/agent,
strategy/signal/evaluator, backtesting, ranking/scoring, order, portfolio
mutation, trading readiness, source approval, methodology approval, validation
approval, trading authority, or dependency behavior. This phase changes no
`src/` files, and normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 161 - Advisory Operating Brief Content Bundle Contract adds
`src/algotrader/research/advisory_operating_brief_content_bundle.py` with
focused coverage in `tests/unit/test_advisory_operating_brief_content_bundle.py`.
The contract defines a frozen, slotted, metadata-only
`AdvisoryOperatingBriefContentBundle` plus
`build_advisory_operating_brief_content_bundle(...)` for grouping existing
`CandidateResearchBrief` and `StrategyEligibilityBrief` objects ahead of later
operating brief composition. It requires at least one total source brief while
allowing either supported family to be empty, rejects non-brief and malformed
brief-like inputs, converts source collections to immutable tuples, preserves
source object identity and input sequence within each family, and rejects
duplicate brief identities through one shared identity guard.

The Phase 161 bundle pins `bundle_type` to
`advisory_operating_brief_content_bundle`, `status` to `candidate_only`,
`authority` to `advisory_only`, and `capital_authority=False`. It derives only
advisory title and summary metadata from source brief counts and carried-forward
metadata, nests source `to_dict()` payloads in the original family order,
carries forward limitations and non-claims with exact duplicate strings
removed, and emits primitive-only deterministic dictionaries plus pinned
compact JSON for the combined synthetic candidate/strategy case. Tests prove
the Phase 160 strategy eligibility expected dictionary and the existing
candidate research expected dictionary are nested exactly, repeated
construction is deterministic, source briefs are not mutated, and paper/live/
approved/trading-ready states remain impossible through bundle metadata. This
phase does not modify the existing `AdvisoryOperatingBrief` contract, renderer,
export helper, or CLI behavior, and adds no strategy execution, signal/
evaluator, backtesting, broker/runtime, order generation, allocation,
portfolio mutation, reconciliation mutation, scheduler, dashboard, file I/O,
persistence, network/socket, credential, vendor API, LLM/agent, notebook, or
new dependency behavior. Normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 162 - Synthetic Advisory Operating Brief Content Bundle Fixture adds
`tests/fixtures/advisory_operating_brief_content_bundle.py` and focused
coverage in
`tests/unit/test_advisory_operating_brief_content_bundle_fixture.py`. The
fixture builds one deterministic `AdvisoryOperatingBriefContentBundle` by
composing the existing synthetic `CandidateResearchBrief` fixture, the Phase
160 `build_synthetic_strategy_eligibility_brief()` fixture, and the Phase 161
`build_advisory_operating_brief_content_bundle(...)` helper, so contract
validation remains in the construction path. Its expected dictionary helper
nests the existing expected synthetic candidate research brief dictionary and
the exact Phase 160 `expected_synthetic_strategy_eligibility_brief_dict()`
payload, pins `bundle_type=advisory_operating_brief_content_bundle`,
`status=candidate_only`, `authority=advisory_only`,
`capital_authority=False`, title, summary, counts, tuple-to-list
serialization, and fresh carried-forward limitation/non-claim lists.

The Phase 162 tests prove the fixture builds an
`AdvisoryOperatingBriefContentBundle` containing exactly one
`CandidateResearchBrief` and one `StrategyEligibilityBrief`, emits the exact
expected primitive dictionary and compact JSON bytes across repeated
construction, carries forward limitations and non-claims from both nested
brief families without shared mutable payload state, and does not mutate source
briefs. AST and literal guardrails prove the fixture added no forbidden broker,
order, allocation, trading-authority, account, portfolio, paper/live readiness,
approval, recommendation, runtime, scheduler, dashboard, file I/O,
persistence, network/socket, credential, vendor API, notebook, LLM/agent,
strategy/signal/evaluator, backtesting, ranking/scoring, portfolio mutation,
source approval, methodology approval, validation approval, trading authority,
or dependency behavior. This phase changes no `src/` files, does not modify
the existing `AdvisoryOperatingBrief` behavior, renderer, export helper, or
CLI behavior, and normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 163 - Advisory Operating Brief Content Bundle Text Renderer adds
`src/algotrader/research/advisory_operating_brief_content_bundle_renderer.py`
and focused coverage in
`tests/unit/test_advisory_operating_brief_content_bundle_renderer.py`. The
renderer exposes the pure
`render_advisory_operating_brief_content_bundle_text(...)` function, requires
an exact `AdvisoryOperatingBriefContentBundle`, rejects non-bundle and
bundle-like inputs, and renders only the primitive payload returned by
`bundle.to_dict()`. It uses fixed headings and fixed line sequencing for the
bundle metadata, title, summary, candidate research brief branch, strategy
eligibility branch, carried-forward limitations, and carried-forward
non-claims. Candidate research briefs, sections, and items retain source
sequence while showing titles, headline/summary points, package fingerprint,
snapshot id, and result manifest references. Strategy eligibility briefs,
sections, and items retain source sequence while showing title, summary,
eligibility state, reasons, evidence refs, blockers, required next steps,
limitations, non-claims, and source status metadata.

The Phase 163 tests pin the full Phase 162 synthetic rendered text, prove
byte-for-byte deterministic repeated rendering, preserve branch sequence for
both candidate research and strategy eligibility payloads, prove fixed
advisory metadata is present, represent the Phase 160 strategy eligibility
payload and existing candidate research payload, and verify rendering does
not mutate the source bundle. AST and literal guardrails prove the renderer
adds no forbidden broker, order, allocation, trading-authority, account,
portfolio, paper/live readiness, approval, recommendation, runtime,
scheduler, dashboard, CLI, file I/O, persistence, network/socket, credential,
vendor API, notebook, LLM/agent, ML, pandas, numpy, vectorbt, QuantConnect,
strategy/signal/evaluator, backtesting, ranking/scoring, portfolio mutation,
source approval, methodology approval, validation approval, or dependency
behavior. This phase does not modify the existing `AdvisoryOperatingBrief`
behavior, renderer, export helper, or CLI behavior, and normal pytest remains
offline, credential-free, deterministic, and safe.

Phase 164 - Advisory Operating Brief Content Bundle Renderer Regression Guard
adds the test-only
`tests/unit/test_advisory_operating_brief_content_bundle_renderer_regression.py`
guard for the Phase 163 content bundle text renderer. The guard uses the Phase
162 synthetic content bundle fixture, calls only
`render_advisory_operating_brief_content_bundle_text(...)`, and pins the exact
rendered line tuple plus repeated byte-for-byte rendering. It verifies fixed
bundle metadata, candidate research branch content, strategy eligibility branch
content, carried-forward limitations, carried-forward non-claims, advisory-only
authority markers, and preserved candidate/strategy branch order. It also
proves `bundle.to_dict()` is unchanged before and after rendering.

The Phase 164 guard confirms rendered authority-sensitive terms appear only as
explicit source metadata non-claims or cautions, with no approval,
recommendation, paper readiness, live readiness, allocation authority, order
authority, trading authority, or actionable readiness fields introduced. Its
AST guard keeps the regression test itself test-only and isolated from the
existing `AdvisoryOperatingBrief` renderer/export/CLI chain, and excludes
forbidden broker, order, allocation, trading-authority, account, portfolio,
paper/live readiness, runtime, scheduler, dashboard, file I/O, persistence,
network/socket, credential, vendor API, notebook, LLM/agent, strategy/signal/
evaluator, backtesting, ranking/scoring, source approval, methodology approval,
validation approval, and dependency behavior. This phase changes no `src/`
files, adds no CLI behavior, and normal pytest remains offline,
credential-free, deterministic, and safe.

Phase 165 - Advisory Operating Brief Content Bundle Export Contract adds
`src/algotrader/research/advisory_operating_brief_content_bundle_export.py`
with focused coverage in
`tests/unit/test_advisory_operating_brief_content_bundle_export.py`. The export
module defines the frozen, slotted
`AdvisoryOperatingBriefContentBundleExport` dataclass and the pure
`export_advisory_operating_brief_content_bundle(...)` builder. The builder
requires an exact `AdvisoryOperatingBriefContentBundle`, rejects non-bundle,
malformed bundle-like, and subclass inputs, and returns only three in-memory
views: the primitive `bundle.to_dict()` payload, compact sorted JSON text using
`separators=(",", ":")`, and
`render_advisory_operating_brief_content_bundle_text(bundle)` output.

The Phase 165 tests use the Phase 162 synthetic content bundle fixture, pin the
exact payload and compact JSON text, match rendered text to the Phase 163
renderer, prove JSON round-tripping, byte-for-byte repeated export
determinism, source bundle `to_dict()` stability, and payload mutation
isolation from caller-side primitive payload edits. AST and literal guardrails
prove the module adds no file I/O, paths, CLI behavior, dashboard behavior,
persistence, runtime/scheduler behavior, network/socket access, credentials,
vendor APIs, notebooks, LLM/agent behavior, ML, pandas, numpy, vectorbt,
QuantConnect, broker/runtime behavior, strategy/signal/evaluator behavior,
backtesting behavior, ranking/scoring, recommendations, allocation authority,
orders, portfolio mutation, trading readiness, source approval, methodology
approval, validation approval, trading authority, or new dependency behavior.
Existing `AdvisoryOperatingBrief`, advisory operating brief renderer/export/CLI
behavior, and content bundle renderer behavior remain unchanged, and normal
pytest remains offline, credential-free, deterministic, and safe.

Phase 166 - Advisory Operating Brief Content Bundle Export Regression Guard adds
`tests/unit/test_advisory_operating_brief_content_bundle_export_regression.py`
as a test-only guard for the Phase 165 in-memory export contract. The guard
uses the Phase 162 synthetic content bundle fixture, calls
`export_advisory_operating_brief_content_bundle(...)`, pins the exact compact
JSON export text, pins the exact rendered line tuple, derives the expected
primitive payload from the pinned JSON, verifies `json_text` round-trips back to
the payload, and verifies `rendered_text` exactly matches
`render_advisory_operating_brief_content_bundle_text(bundle)`.

The Phase 166 guard also proves repeated exports are byte-for-byte
deterministic, exported payload mutation does not mutate the source bundle or
later exports, and the source bundle `to_dict()` payload remains unchanged
before and after export. It pins fixed advisory metadata (`bundle_type`,
`status`, `authority`, and `capital_authority`), verifies candidate research and
strategy eligibility branches remain present and ordered, verifies limitations
and non-claims remain present, and checks approval/readiness/recommendation/
allocation/order/trading-authority language appears only as explicit
non-claims/cautions sourced from bundle metadata. Self-inspection guardrails
prove the regression test itself imports and calls only the content-bundle
fixture/export/renderer path plus standard-library inspection helpers, with no
file I/O, paths, CLI behavior, persistence, runtime/scheduler behavior,
network/socket access, credentials, vendor APIs, notebooks, LLM/agent behavior,
broker/runtime behavior, strategy/signal/evaluator behavior, backtesting
behavior, ranking/scoring, recommendations, allocation authority, orders,
portfolio mutation, trading readiness, source approval, methodology approval,
validation approval, trading authority, production-code changes, new
dependencies, or existing `AdvisoryOperatingBrief` renderer/export/CLI chain
behavior. Normal pytest remains offline, credential-free, deterministic, and
safe.

Phase 167 - Advisory Operating Brief Content Bundle CLI Preview adds
`src/algotrader/research/advisory_operating_brief_content_bundle_cli.py`,
wires the new `algotrader advisory-operating-brief-content-bundle-preview`
subcommand in `src/algotrader/cli.py`, and adds focused coverage in
`tests/unit/test_advisory_operating_brief_content_bundle_cli.py`. The preview
builds a production-safe synthetic `AdvisoryOperatingBriefContentBundle` in
production code using only public research builders, matches the Phase 162
synthetic content bundle fixture payload exactly, and exports only through the
Phase 165 `export_advisory_operating_brief_content_bundle(...)` contract.

The Phase 167 CLI supports only default text output, `--format text`, and
`--format json`. Text output is exactly `export.rendered_text`; JSON output is
exactly compact `export.json_text`; repeated text and JSON invocations are
byte-for-byte deterministic; and JSON output round-trips to the expected
primitive payload. The command exposes no file, path, source, vendor, broker,
or runtime options, performs no file I/O, persistence, environment reads,
network/socket access, external data access, credentials, dashboards,
runtime/scheduler behavior, notebooks, LLM/agent behavior, broker/runtime
behavior, strategy/signal/evaluator behavior, backtesting behavior,
ranking/scoring, recommendations, allocation authority, orders, portfolio
mutation, trading readiness, source approval, methodology approval, validation
approval, trading authority, or new dependency behavior. Existing
`advisory-operating-brief-preview`, `AdvisoryOperatingBrief`, renderer/export
chains, and content bundle renderer/export behavior remain unchanged. Normal
pytest remains offline, credential-free, deterministic, and safe.

Phase 168 - Advisory Operating Brief Content Bundle CLI Regression Guard adds
`tests/unit/test_advisory_operating_brief_content_bundle_cli_regression.py` as
a test-only guard for the Phase 167 preview command. The guard invokes
`main([...])`, pins default text stdout, `--format text` stdout, and
`--format json` stdout exactly against the Phase 165 export pins for the Phase
162 synthetic content bundle, verifies default text equals explicit text,
verifies JSON round-trips exactly to the expected primitive payload, and proves
repeated text and JSON invocations remain byte-for-byte deterministic.

The Phase 168 guard verifies candidate research and strategy eligibility
branches are both present, fixed advisory/candidate-only metadata remains
present, limitations and non-claims remain present, and approval/readiness/
recommendation/allocation/order/trading-authority language remains confined to
explicit caution metadata. It also proves the command exposes no file, path,
source, vendor, broker, or runtime options; the content bundle preview module
imports no tests or fixtures and adds no forbidden file I/O, persistence,
network/socket, credential, vendor, broker, runtime/scheduler, dashboard,
notebook, LLM/agent, strategy/signal/evaluator, backtesting, ranking/scoring,
recommendation, allocation, order, portfolio mutation, readiness, approval, or
trading-authority behavior; and existing `advisory-operating-brief-preview`
text and JSON pins remain unchanged. No `src/` production code or content
bundle renderer/export/CLI behavior changed. Normal pytest remains offline,
credential-free, deterministic, and safe.

Phase 169 - Advisory Risk Authority Status Contract adds
`src/algotrader/research/risk_authority_status.py` and focused coverage in
`tests/unit/test_risk_authority_status.py`. The contract defines the frozen,
slotted `RiskAuthorityStatus` dataclass and pure
`build_risk_authority_status(...)` builder for deterministic metadata-only
advisory risk-capital authority status. Fixed metadata is pinned to
`authority_type="risk_authority_status"`, `status="candidate_only"`,
`authority="advisory_only"`, and `capital_authority=False`; the only allowed
states are `not_authorized`, `blocked`, and `research_only`.

The Phase 169 tests prove tuple/list input copying, immutable tuple storage,
source input non-mutation, exact primitive `to_dict()` output, compact JSON
determinism, repeated construction determinism, frozen/slots behavior,
non-empty string validation, malformed collection rejection, unknown-state
rejection, and explicit rejection of paper/live/authorized/trading-ready/
allocation/order-capable/broker/account/portfolio authority-like states. The
required non-claims state that the contract is not risk approval, not
allocation authority, not order authority, not paper readiness, not live
readiness, not broker authority, not portfolio mutation authority, not capital
authority, and not trading authority. AST and literal guardrails prove the
module adds no actionable authority fields and no risk engine behavior,
strategy/signal/evaluator behavior, backtesting behavior, broker/runtime
behavior, order generation, allocation, portfolio mutation, reconciliation
mutation, scheduler behavior, dashboard behavior, CLI behavior, file I/O,
persistence, network/socket access, credentials, vendor APIs, LLM/agent
behavior, notebooks, new dependencies, paper readiness, live readiness, or
trading authority. Normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 170 - Synthetic Risk Authority Status Fixture adds
`tests/fixtures/risk_authority_status.py` and focused coverage in
`tests/unit/test_risk_authority_status_fixture.py`. The fixture uses the Phase
169 public `build_risk_authority_status(...)` builder to create a deterministic
`RiskAuthorityStatus` with `authority_state="not_authorized"` and fixed
advisory metadata pinned to `authority_type="risk_authority_status"`,
`status="candidate_only"`, `authority="advisory_only"`, and
`capital_authority=False`.

The Phase 170 fixture exposes only primitive synthetic metadata: reasons,
blockers, required next steps, limitations, non-claims, evidence references,
and related strategy ids. Its non-claims explicitly deny risk approval,
allocation authority, order authority, paper readiness, live readiness, broker
authority, portfolio mutation authority, capital authority, trading authority,
trading recommendation, order placement, broker access, and portfolio
mutation. Tests pin exact `to_dict()` output, compact JSON bytes, tuple
storage/list serialization, repeated construction determinism, fresh expected
payload list state, source collection non-mutation, use of the Phase 169 public
builder, and AST/literal guardrails proving no forbidden broker, order,
allocation, portfolio, or trading-authority fixture fields or imports were
added. No `src/` production code, CLI behavior, risk engine behavior, strategy
execution behavior, signal/evaluator behavior, backtesting behavior,
broker/runtime behavior, order generation, allocation, portfolio mutation,
reconciliation mutation, scheduler behavior, dashboard behavior, file I/O,
persistence, network/socket access, credentials, vendor APIs, LLM/agent
behavior, notebooks, or dependencies changed. Normal pytest remains offline,
credential-free, deterministic, and safe.

Phase 171 - Advisory Risk Authority Brief Item adds
`src/algotrader/research/risk_authority_brief_item.py` and focused coverage in
`tests/unit/test_risk_authority_brief_item.py`. The contract defines the frozen,
slotted `RiskAuthorityBriefItem` dataclass and pure
`build_risk_authority_brief_item(...)` builder for deterministic advisory-only
composition around an existing exact `RiskAuthorityStatus`. The item preserves
source status object identity, requires exact `RiskAuthorityStatus` inputs, and
rejects malformed status-like objects and subclass instances.

The Phase 171 item pins fixed metadata to
`item_type="risk_authority_brief_item"`, `status="candidate_only"`,
`authority="advisory_only"`, and `capital_authority=False`; carries forward
authority state, reasons, blockers, required next steps, limitations,
non-claims, evidence refs, and related strategy ids; adds deterministic
headline and summary text; and includes the nested source status `to_dict()`
payload. Tests pin exact primitive `to_dict()` output, compact JSON output,
tuple storage/list serialization, repeated construction determinism, nested
Phase 170 fixture payload equality, source status non-mutation, direct
constructor rejection when carried metadata diverges from the source, absence
of `from_dict()`, and AST/literal guardrails proving no actionable authority
fields or forbidden imports/calls were added. The headline and summary remain
advisory-only and do not express approval, recommendation, readiness,
allocation, order, broker, portfolio mutation, capital, or trading authority.
No risk engine behavior, strategy execution behavior, signal/evaluator
behavior, backtesting behavior, broker/runtime behavior, order generation,
allocation, portfolio mutation, reconciliation mutation, scheduler behavior,
dashboard behavior, CLI behavior, file I/O, persistence, network/socket access,
credentials, vendor APIs, LLM/agent behavior, notebooks, or dependencies
changed. Normal pytest remains offline, credential-free, deterministic, and
safe.

Phase 172 - Synthetic Risk Authority Brief Item Fixture adds
`tests/fixtures/risk_authority_brief_item.py` and focused coverage in
`tests/unit/test_risk_authority_brief_item_fixture.py`. The fixture composes
the Phase 170 `build_synthetic_risk_authority_status()` fixture with the Phase
171 `build_risk_authority_brief_item(...)` builder, preserving validation and
source status identity instead of hand-constructing a brief item. The expected
helper composes from `expected_synthetic_risk_authority_status_dict()` so the
nested source status payload exactly matches the Phase 170 fixture dictionary.

The Phase 172 fixture pins fixed advisory metadata to
`item_type="risk_authority_brief_item"`, `status="candidate_only"`,
`authority="advisory_only"`, and `capital_authority=False`; pins the
deterministic advisory-only headline and summary; and carries forward authority
state, reasons, blockers, required next steps, limitations, non-claims,
evidence refs, and related strategy ids. Its non-claims remain the Phase 170
denials of risk approval, allocation authority, order authority, paper
readiness, live readiness, broker authority, portfolio mutation authority,
capital authority, trading authority, trading recommendation, order placement,
broker access, and portfolio mutation. Tests pin exact primitive dictionary
output, nested source status equality, compact JSON bytes, tuple storage/list
serialization, repeated construction determinism, fresh expected-helper list
state, source collection non-mutation, use of the Phase 170 fixture and Phase
171 builder, and AST/literal guardrails proving no forbidden broker, order,
allocation, portfolio, or trading-authority fixture fields or imports were
added. No `src/` production code, CLI behavior, risk engine behavior, strategy
execution behavior, signal/evaluator behavior, backtesting behavior,
broker/runtime behavior, order generation, allocation, portfolio mutation,
reconciliation mutation, scheduler behavior, dashboard behavior, file I/O,
persistence, network/socket access, credentials, vendor APIs, LLM/agent
behavior, notebooks, or dependencies changed. Normal pytest remains offline,
credential-free, deterministic, and safe.

Phase 173 - Advisory Risk Authority Brief Section adds
`src/algotrader/research/risk_authority_brief_section.py` and focused coverage
in `tests/unit/test_risk_authority_brief_section.py`. The contract defines the
frozen, slotted `RiskAuthorityBriefSection` dataclass and pure
`build_risk_authority_brief_section(...)` builder for deterministic
metadata-only advisory grouping of one or more exact `RiskAuthorityBriefItem`
objects. It preserves source item object identity and caller ordering, converts
item collections to immutable tuples, rejects empty collections, rejects
malformed item-like objects, rejects subclass instances, and rejects duplicate
item identities.

The Phase 173 section pins fixed metadata to
`section_type="risk_authority_brief_section"`, `status="candidate_only"`,
`authority="advisory_only"`, and `capital_authority=False`. It derives
advisory-only title and summary text from item metadata, carries forward item
limitations and non-claims in deterministic first-seen order with exact
duplicates removed, includes nested item `to_dict()` payloads in original
order, and returns primitive-only deterministic `to_dict()` output with tuple
fields serialized as lists. Tests pin exact section dictionary output, compact
JSON output, nested Phase 172 fixture item equality, repeated construction
determinism, source item non-mutation, direct constructor rejection when
section metadata diverges from source items, absence of `from_dict()`, and
AST/literal guardrails proving no actionable authority fields or forbidden
imports/calls were added. The title and summary do not express approval,
recommendation, paper readiness, live readiness, allocation language, order
language, broker authority, portfolio mutation authority, capital authority,
or trading authority. The section does not create risk approval, paper
readiness, live readiness, recommendation, allocation authority, order
authority, broker authority, portfolio mutation authority, capital authority,
or trading authority. No risk engine behavior, strategy execution behavior,
signal/evaluator behavior, backtesting behavior, broker/runtime behavior,
order generation, allocation, portfolio mutation, reconciliation mutation,
scheduler behavior, dashboard behavior, CLI behavior, file I/O, persistence,
network/socket access, credentials, vendor APIs, LLM/agent behavior,
notebooks, or dependencies changed. Normal pytest remains offline,
credential-free, deterministic, and safe.

Phase 174 - Synthetic Risk Authority Brief Section Fixture adds
`tests/fixtures/risk_authority_brief_section.py` and focused coverage in
`tests/unit/test_risk_authority_brief_section_fixture.py`. The fixture composes
the Phase 172 `build_synthetic_risk_authority_brief_item()` fixture with the
Phase 173 `build_risk_authority_brief_section(...)` builder, so validation is
preserved and the nested item remains the deterministic Phase 172
`RiskAuthorityBriefItem`. The expected helper composes from
`expected_synthetic_risk_authority_brief_item_dict()`, pins the nested item
dictionary exactly, and returns fresh primitive list state for top-level and
nested payloads.

The Phase 174 fixture pins fixed metadata to
`section_type="risk_authority_brief_section"`, `status="candidate_only"`,
`authority="advisory_only"`, and `capital_authority=False`. Title and summary
text are deterministic advisory-only metadata, limitations and non-claims are
carried forward from the Phase 172 item, and non-claims deny risk approval,
allocation authority, order authority, paper readiness, live readiness, broker
authority, portfolio mutation authority, capital authority, and trading
authority. Tests pin exact primitive dictionary output, nested Phase 172 item
payload equality, compact JSON bytes, tuple storage/list serialization,
repeated construction determinism, expected-helper freshness, source item
non-mutation, and AST/literal guardrails proving no forbidden broker, order,
allocation, portfolio, or trading-authority fixture fields, imports, or calls
were added. No `src/` production code, CLI behavior, risk engine behavior,
strategy execution behavior, signal/evaluator behavior, backtesting behavior,
broker/runtime behavior, order generation, allocation, portfolio mutation,
reconciliation mutation, scheduler behavior, dashboard behavior, file I/O,
persistence, network/socket access, credentials, vendor APIs, LLM/agent
behavior, notebooks, or dependencies changed. Normal pytest remains offline,
credential-free, deterministic, and safe.

Phase 175 - Advisory Risk Authority Brief Container adds
`src/algotrader/research/risk_authority_brief.py` and focused coverage in
`tests/unit/test_risk_authority_brief.py`. The contract defines the frozen,
slotted `RiskAuthorityBrief` dataclass and pure
`build_risk_authority_brief(...)` builder for deterministic metadata-only
advisory grouping of one or more exact `RiskAuthorityBriefSection` objects. It
preserves source section object identity and caller ordering, converts section
collections to immutable tuples, rejects empty collections, rejects malformed
section-like objects, rejects subclass instances, and rejects duplicate section
identities.

The Phase 175 brief pins fixed metadata to
`brief_type="risk_authority_brief"`, `status="candidate_only"`,
`authority="advisory_only"`, and `capital_authority=False`. It derives
advisory-only title and summary text from section metadata, carries forward
section limitations and non-claims in deterministic first-seen order with exact
duplicates removed, includes nested section `to_dict()` payloads in original
order, and returns primitive-only deterministic `to_dict()` output with tuple
fields serialized as lists. Tests pin exact brief dictionary output, compact
JSON output, nested Phase 174 fixture section equality, repeated construction
determinism, source section non-mutation, direct constructor rejection when
brief metadata diverges from source sections, absence of `from_dict()`, and
AST/literal guardrails proving no actionable authority fields or forbidden
imports/calls were added. The title and summary do not express approval,
recommendation, paper readiness, live readiness, allocation language, order
language, broker authority, portfolio mutation authority, capital authority,
or trading authority. The brief does not create risk approval, paper
readiness, live readiness, recommendation, allocation authority, order
authority, broker authority, portfolio mutation authority, capital authority,
or trading authority. No risk engine behavior, strategy execution behavior,
signal/evaluator behavior, backtesting behavior, broker/runtime behavior,
order generation, allocation, portfolio mutation, reconciliation mutation,
scheduler behavior, dashboard behavior, CLI behavior, file I/O, persistence,
network/socket access, credentials, vendor APIs, LLM/agent behavior,
notebooks, or dependencies changed. Normal pytest remains offline,
credential-free, deterministic, and safe.

Phase 176 - Synthetic Risk Authority Brief Fixture adds
`tests/fixtures/risk_authority_brief.py` and focused coverage in
`tests/unit/test_risk_authority_brief_fixture.py`. The fixture composes the
Phase 174 `build_synthetic_risk_authority_brief_section()` fixture with the
Phase 175 `build_risk_authority_brief(...)` builder, so validation is
preserved and the nested section remains the deterministic Phase 174
`RiskAuthorityBriefSection`. The expected helper composes from
`expected_synthetic_risk_authority_brief_section_dict()`, pins the nested
section dictionary exactly, returns fresh primitive list state, and keeps fixed
metadata at `brief_type="risk_authority_brief"`, `status="candidate_only"`,
`authority="advisory_only"`, and `capital_authority=False`.

The Phase 176 fixture pins deterministic advisory-only title and summary text,
copies limitations and non-claims forward from the Phase 174 section, and keeps
non-claims denying risk approval, allocation authority, order authority, paper
readiness, live readiness, broker authority, portfolio mutation authority,
capital authority, and trading authority. Tests pin exact dictionary output,
nested Phase 174 section equality, compact JSON bytes, tuple storage/list
serialization, repeated construction determinism, expected-helper freshness,
source section non-mutation, and AST/literal guardrails proving no forbidden
broker, order, allocation, portfolio, or trading-authority fixture fields,
imports, or calls were added. No `src/` production code, CLI behavior, risk
engine behavior, strategy execution behavior, signal/evaluator behavior,
backtesting behavior, broker/runtime behavior, order generation, allocation,
portfolio mutation, reconciliation mutation, scheduler behavior, dashboard
behavior, file I/O, persistence, network/socket access, credentials, vendor
APIs, LLM/agent behavior, notebooks, or dependencies changed. Normal pytest
remains offline, credential-free, deterministic, and safe.

Phase 177 - Advisory Operating Brief Content Bundle Risk Authority Branch
extends `AdvisoryOperatingBriefContentBundle` in
`src/algotrader/research/advisory_operating_brief_content_bundle.py` so the
metadata-only content bundle can optionally group exact `RiskAuthorityBrief`
objects beside existing `CandidateResearchBrief` and
`StrategyEligibilityBrief` families. The builder keeps candidate and strategy
behavior backward-compatible, allows any one or two families to be empty while
requiring at least one total brief, preserves object identity and per-family
input ordering, converts all collections to immutable tuples, and rejects
malformed risk-authority-like objects, subclass instances, non-risk brief
inputs in the risk branch, and duplicate object identities across the supported
collections.

The Phase 177 bundle keeps fixed metadata unchanged at
`bundle_type="advisory_operating_brief_content_bundle"`,
`status="candidate_only"`, `authority="advisory_only"`, and
`capital_authority=False`. It carries limitations and non-claims forward from
candidate research, strategy eligibility, and risk authority branches in
deterministic first-seen order with exact duplicates removed. `to_dict()`
remains primitive-only and deterministic; risk authority brief counts and
nested risk authority brief payloads are emitted only when risk authority
briefs are present, preserving existing serialized output for the prior
synthetic candidate-plus-strategy fixture. Tests pin risk-only and
candidate-plus-strategy-plus-risk construction, nested Phase 176 fixture
payload equality, compact JSON output, repeated construction determinism,
source brief non-mutation, exact metadata values, and AST/literal guardrails.
No renderer, export, CLI, legacy `AdvisoryOperatingBrief`, risk engine,
strategy/signal/evaluator, backtesting, broker/runtime, scheduler, dashboard,
file I/O, persistence, network/socket, credentials, vendor API, LLM/agent,
notebook, dependency, recommendation, allocation, order, portfolio mutation,
paper-readiness, live-readiness, capital, or trading-authority behavior
changed. Normal pytest remains offline, credential-free, deterministic, and
safe.

Phase 178 - Synthetic Advisory Operating Brief Content Bundle With Risk
Fixture extends `tests/fixtures/advisory_operating_brief_content_bundle.py`
with additive risk-inclusive fixture helpers for future renderer, export, and
CLI composition tests. The existing Phase 162
`build_synthetic_advisory_operating_brief_content_bundle()` and
`expected_synthetic_advisory_operating_brief_content_bundle_dict()` outputs
remain unchanged. The new helper composes the existing synthetic
`CandidateResearchBrief`, the Phase 160 synthetic `StrategyEligibilityBrief`,
the Phase 176 synthetic `RiskAuthorityBrief`, and the Phase 177
`build_advisory_operating_brief_content_bundle(...)` builder, preserving
validation instead of constructing payloads directly.

The Phase 178 expected helper pins fixed advisory metadata at
`bundle_type="advisory_operating_brief_content_bundle"`,
`status="candidate_only"`, `authority="advisory_only"`, and
`capital_authority=False`; pins deterministic advisory-only title and summary
text; carries limitations and non-claims forward from candidate research,
strategy eligibility, and risk authority branches; and pins the nested Phase
176 risk authority dictionary exactly. Focused tests verify exact primitive
dictionary output, compact JSON bytes, nested candidate, strategy, and risk
payload equality, tuple storage/list serialization, repeated construction
determinism, fresh expected-helper mutable list state, source brief
non-mutation, old Phase 162 fixture compatibility, and AST/literal guardrails.
No `src/` production code, existing `AdvisoryOperatingBrief` behavior,
renderer/export/CLI behavior, risk engine behavior, strategy/signal/evaluator
behavior, backtesting behavior, broker/runtime behavior, scheduler behavior,
dashboard behavior, file I/O, persistence, network/socket access, credentials,
vendor APIs, notebooks, LLM/agent behavior, dependencies, recommendation,
allocation, order, portfolio mutation, paper-readiness, live-readiness,
capital, or trading-authority behavior changed. Normal pytest remains
offline, credential-free, deterministic, and safe.

Phase 179 - Advisory Operating Brief Content Bundle Renderer Risk Authority
Branch extends
`src/algotrader/research/advisory_operating_brief_content_bundle_renderer.py`
so `render_advisory_operating_brief_content_bundle_text(...)` conditionally
renders risk authority branch metadata only when `risk_authority_briefs` are
present in `bundle.to_dict()`. The renderer still validates that the input is
exactly an `AdvisoryOperatingBriefContentBundle`, renders only from the
primitive `to_dict()` payload, preserves candidate research and strategy
eligibility output for the Phase 162 no-risk synthetic bundle byte-for-byte,
and keeps deterministic fixed headings, branch ordering, and line ordering.

The Phase 179 risk branch renders advisory-only brief, section, item, and
source-status metadata including title, summary, `authority_state`, reasons,
blockers, required next steps, evidence references, related strategy ids,
limitations, and non-claims. Bundle-level limitations and non-claims continue
to render after branch content. Focused tests pin the exact risk-inclusive
line tuple, repeated byte-for-byte determinism, candidate, strategy, and risk
branch ordering, source bundle non-mutation, fixed metadata, all-branch
limitations and non-claims, rejected non-bundle and subclass inputs, and
AST/literal guardrails proving no forbidden network, vendor, broker, pandas,
numpy, vectorbt, QuantConnect, ML, LLM, file I/O, persistence, scheduler,
runtime, dashboard, CLI, dependency, or actionable authority behavior was
added. Existing `AdvisoryOperatingBrief`, renderer/export/CLI behavior,
content bundle export/CLI behavior, risk engine behavior,
strategy/signal/evaluator behavior, backtesting, broker/runtime behavior,
recommendation, allocation, order, portfolio mutation, paper-readiness,
live-readiness, capital, and trading-authority behavior remain unchanged.
Normal pytest remains offline, credential-free, deterministic, and safe.

Phase 180 - Advisory Operating Brief Content Bundle Export Risk-Branch
Regression Guard adds
`tests/unit/test_advisory_operating_brief_content_bundle_export_with_risk_regression.py`
as test-only coverage for the existing in-memory content bundle export path
after the Phase 179 renderer update. The guard composes the Phase 178
risk-inclusive synthetic bundle, compares the export payload to
`expected_synthetic_advisory_operating_brief_content_bundle_with_risk_dict()`,
pins compact sorted JSON, checks JSON round-trip behavior, and verifies that
rendered export text matches
`render_advisory_operating_brief_content_bundle_text(...)`.

The Phase 180 guard also proves repeated exports are byte-for-byte
deterministic, the risk authority count and nested risk metadata remain
present, candidate research and strategy eligibility branches stay before the
risk authority branch, limitations and non-claims are preserved, and the
source bundle is not mutated by export or exported-payload edits. It adds
self-inspection guardrails for the new test file and does not modify `src/`
production code, `AdvisoryOperatingBrief`, content bundle construction,
renderer, export, CLI, broker/runtime, scheduler/dashboard, file I/O,
persistence, network/socket, credentials, vendor APIs, notebooks, ML,
LLM/agent, strategy/signal/evaluator, backtesting, allocation/order/portfolio
mutation, risk approval, paper/live readiness, capital, or trading-authority
behavior. Normal pytest remains offline, credential-free, deterministic, and
safe.

Phase 181 - Advisory Operating Brief Content Bundle CLI Risk Preview extends
`algotrader advisory-operating-brief-content-bundle-preview` with an explicit
synthetic-only `--include-risk-authority` flag. When the flag is absent, the
existing default text output, `--format text`, and compact `--format json`
views remain byte-for-byte identical to the Phase 165 no-risk preview. When
the flag is present, the preview composes a production-safe synthetic bundle
from public production builders for candidate research, strategy eligibility,
and risk authority, then exports it through
`export_advisory_operating_brief_content_bundle(...)`.

The Phase 181 risk-inclusive CLI path renders text by default and compact
sorted JSON with `--format json`, includes `risk_authority_briefs` and
`risk_authority_brief_count` only on the explicit risk path, round-trips JSON
to the exported payload, and remains byte-for-byte deterministic across
repeated invocations and option ordering. Focused tests prove the default
preview remains unchanged, the production CLI modules import no `tests` or
`tests.fixtures`, no file/path/source/vendor/broker/network/runtime/credential
options were introduced, and no paper/live/approved/trading-ready/actionable
authority states or fields were added. No real data, ingestion, persistence,
file I/O, network/socket access, credentials, vendor APIs, scheduler/dashboard
behavior, notebooks, ML, LLM/agent behavior, strategy/signal/evaluator
behavior, backtesting, ranking/scoring, recommendations, allocation/order/
portfolio mutation, risk approval, paper/live readiness, capital authority, or
trading authority was added. Normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 182 - Advisory Research Queue Brief Family adds a metadata-only
research queue branch in `src/algotrader/research/research_queue_status.py`,
`src/algotrader/research/research_queue_brief_item.py`,
`src/algotrader/research/research_queue_brief_section.py`, and
`src/algotrader/research/research_queue_brief.py`. The branch represents
unresolved research work, blockers, required next steps, evidence gaps,
related strategy ids, limitations, and advisory non-claims. It pins every
level to `candidate_only`, `advisory_only`, and `capital_authority=False`,
uses frozen slotted dataclasses, exact-type composition, deterministic
primitive-only `to_dict()` serialization, input tuple conversion without
source mutation, identity/order preservation, duplicate identity rejection,
and duplicate-removed limitation/non-claim carry-forward.

The Phase 182 family is not connected to the existing content bundle,
renderer, export, or CLI paths. It adds no source/data approval, methodology
approval, signal/evaluator behavior, strategy execution, backtesting,
ranking/scoring, recommendations, allocation/order/portfolio mutation,
broker/runtime behavior, scheduler/dashboard behavior, paper/live readiness,
capital authority, trading authority, file I/O, persistence, network/socket
access, credentials, vendor APIs, notebooks, ML, LLM/agent behavior, or new
dependencies. Focused tests cover construction, direct-constructor validation,
immutability, slots, malformed input rejection, required non-claims,
forbidden language/state rejection, deterministic serialization,
identity/order preservation, duplicate identity rejection, and AST/import
guardrails. Normal pytest remains offline, credential-free, deterministic,
and safe.

Phase 183 - Synthetic Research Queue Brief Fixture adds
`tests/fixtures/research_queue_brief.py` and
`tests/unit/test_research_queue_brief_fixture.py` as test-only fixture support
for the Phase 182 research queue family. The fixture builds a broad ETF SMA
trend-following research queue item as unresolved, synthetic advisory metadata:
it is a pipeline-validation candidate with unresolved source clearance,
universe definition, benchmark/cash proxy, return policy, no-lookahead,
survivorship, reproduction, validation, provenance, robustness, cost/slippage,
and evidence questions. The expected dictionary helpers return fresh primitive
copies that match each object's `to_dict()` output exactly.

The Phase 183 fixture preserves Phase 182 identity semantics: the item keeps
the exact source status object, the section keeps item identity/order, and the
brief keeps section identity/order. Limitations and explicit non-claims carry
forward through item, section, and brief. The fixture remains synthetic and
does not change `src/`, content bundle construction, renderer, export, CLI,
source/data approval, methodology approval, signal/evaluator behavior,
strategy execution, backtesting, ranking/scoring, recommendations,
allocation/order/portfolio mutation, broker/runtime behavior,
scheduler/dashboard behavior, paper/live readiness, capital authority, trading
authority, file I/O, persistence, network/socket access, credentials, vendor
APIs, notebooks, ML, LLM/agent behavior, or dependencies. Normal pytest
remains offline, credential-free, deterministic, and safe.

Phase 184 - Advisory Operating Brief Content Bundle Research Queue Integration
adds the Phase 182/183 `ResearchQueueBrief` family as an optional fourth
branch in
`src/algotrader/research/advisory_operating_brief_content_bundle.py`. The
bundle still pins `bundle_type="advisory_operating_brief_content_bundle"`,
`status="candidate_only"`, `authority="advisory_only"`, and
`capital_authority=False`. The builder now accepts candidate research,
strategy eligibility, risk authority, and research queue brief iterables; each
branch may be empty, but at least one total brief is required. Object identity
and order are preserved within every branch, malformed/non-brief inputs are
rejected, duplicate object identities are rejected across all branches, and
limitations/non-claims are carried forward with first-seen de-duplication.

The Phase 184 `to_dict()` path emits `research_queue_brief_count` and
`research_queue_briefs` only for bundles that include research queue briefs,
preserving the existing Phase 162 no-risk and Phase 178 risk-inclusive fixture
payloads exactly. The new
`build_synthetic_advisory_operating_brief_content_bundle_with_research_queue()`
and
`expected_synthetic_advisory_operating_brief_content_bundle_with_research_queue_dict()`
helpers compose candidate, strategy, risk, and research queue branches through
the production builder and return deterministic primitive-only payloads with
fresh mutable expected dictionaries. Renderer, export, and CLI behavior are
unchanged. No source/data approval, methodology approval, signal/evaluator
behavior, strategy execution, backtesting, ranking/scoring, recommendations,
allocation/order/portfolio mutation, risk approval, paper/live readiness,
capital authority, trading authority, broker/runtime behavior,
scheduler/dashboard behavior, file I/O, persistence, network/socket access,
credentials, vendor APIs, notebooks, ML, LLM/agent behavior, or dependencies
were added. Normal pytest remains offline, credential-free, deterministic, and
safe.

Phase 185 - Advisory Operating Brief Content Bundle Renderer Research Queue
Branch extends
`src/algotrader/research/advisory_operating_brief_content_bundle_renderer.py`
to conditionally render the Phase 184 `research_queue_briefs` branch from the
bundle dictionary payload only. The renderer preserves the existing Phase 162
candidate+strategy and Phase 178 candidate+strategy+risk text output
byte-for-byte when no research queue branch is present. When present, the
research queue branch renders deterministic brief, section, item, and source
status metadata, including queue id, title, research state, priority bucket,
topic, hypothesis, blockers, required next steps, evidence gaps, related
strategy ids, evidence refs, limitations, and non-claims.

Phase 185 tests prove research queue branch ordering after candidate,
strategy, and risk branches and before aggregate limitations/non-claims;
byte-for-byte deterministic repeated rendering; no mutation of source bundle
objects or `to_dict()` payloads; dictionary-payload-only branch access; and
AST/import/call/literal guardrails. Content bundle construction, export, CLI,
source/data approval, methodology approval, signal/evaluator behavior,
strategy execution, backtesting, ranking/scoring, recommendations,
allocation/order/portfolio mutation, risk approval, paper/live readiness,
capital authority, trading authority, broker/runtime behavior,
scheduler/dashboard behavior, file I/O, persistence, network/socket access,
credentials, vendor APIs, notebooks, ML, LLM/agent behavior, and dependencies
are unchanged. Normal pytest remains offline, credential-free, deterministic,
and safe.

Phase 186 - Advisory Operating Brief Content Bundle Export Research Queue
Regression Guard adds
`tests/unit/test_advisory_operating_brief_content_bundle_export_with_research_queue_regression.py`
as a test-only guard for the existing export path with the Phase 184/185
research-queue-inclusive content bundle. The test composes the synthetic
candidate, strategy eligibility, risk authority, and research queue branches
through
`build_synthetic_advisory_operating_brief_content_bundle_with_research_queue()`,
pins the exported payload to
`expected_synthetic_advisory_operating_brief_content_bundle_with_research_queue_dict()`,
pins compact deterministic JSON with `sort_keys=True` and
`separators=(",", ":")`, verifies JSON round-trip behavior, and confirms
rendered text still comes from
`render_advisory_operating_brief_content_bundle_text(bundle)`.

The Phase 186 guard also proves repeated exports are byte-for-byte
deterministic, candidate/strategy/risk/research queue branch counts and
payload branches are present, `research_queue_brief_count` and
`research_queue_briefs` remain emitted for the inclusive fixture, nested
research queue brief/section/item/source-status metadata is preserved, branch
sequence remains candidate, strategy, risk, research queue, limitations, then
non-claims, limitations and explicit non-claims carry through to rendered
output, and mutating the exported payload does not mutate the source bundle or
later exports. It changes no `src/`, content bundle construction, renderer,
export, CLI, source/data approval, methodology approval, signal/evaluator
behavior, strategy execution, backtesting, ranking/scoring, recommendations,
allocation/order/portfolio mutation, risk approval, broker/runtime behavior,
scheduler/dashboard behavior, paper/live readiness, capital authority, trading
authority, file I/O, persistence, network/socket access, credentials, vendor
APIs, notebooks, ML, LLM/agent behavior, or dependencies. Normal pytest
remains offline, credential-free, deterministic, and safe.

Phase 187 - Advisory Operating Brief Content Bundle CLI Research Queue Preview
adds an explicit synthetic-only `--include-research-queue` flag to
`algotrader advisory-operating-brief-content-bundle-preview`. The default
preview remains candidate research plus strategy eligibility only, and the
existing `--include-risk-authority` text and JSON previews remain
byte-for-byte unchanged. With `--include-research-queue`, the preview composes
candidate research, strategy eligibility, and research queue branches; with
both `--include-risk-authority` and `--include-research-queue`, it composes all
four candidate, strategy, risk, and research queue branches.

The Phase 187 implementation uses only production builders and the existing
`export_advisory_operating_brief_content_bundle(...)` path, so text output
continues to come from `export.rendered_text` and JSON output from compact
deterministic `export.json_text`. The new CLI tests prove default and risk
compatibility, research queue text/JSON branch presence, risk omission unless
the risk flag is also present, both-flag branch composition, JSON round-trip
behavior, repeated byte-for-byte deterministic invocations, no production
imports from `tests` or `tests.fixtures`, no new file/path/source/vendor/
broker/network/runtime/credential options, and no paper/live/approved/
trading-ready/actionable authority states. No real data, ingestion,
persistence, file I/O, network/socket access, credentials, vendor APIs,
scheduler/dashboard behavior, notebooks, ML, LLM/agent behavior, dependencies,
source/data approval, methodology approval, strategy/signal/evaluator
behavior, backtesting, ranking/scoring, recommendations, allocation/order/
portfolio mutation, risk approval, paper/live readiness, capital authority, or
trading authority were added. Normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 188 - Advisory Operating Brief Package Contract adds
`AdvisoryOperatingBriefPackage` and
`build_advisory_operating_brief_package(...)` in
`src/algotrader/research/advisory_operating_brief_package.py`. The package is
a frozen/slotted metadata-only top-level handoff wrapper around an existing
`AdvisoryOperatingBriefContentBundle` and the existing
`export_advisory_operating_brief_content_bundle(...)` export. It pins
`package_type="advisory_operating_brief_package"`, `status="candidate_only"`,
`authority="advisory_only"`, and `capital_authority=False`, requires explicit
non-empty `package_id`, `title`, `summary`, and `as_of` strings, preserves the
source content bundle object identity, and carries forward bundle limitations
and non-claims with first-seen dedupe.

The Phase 188 package emits deterministic primitive-only `to_dict()` output
with package metadata, `content_bundle.to_dict()`, a primitive
`content_bundle_export` dictionary containing `payload`, `json_text`, and
`rendered_text`, plus limitations and non-claims. The builder requires the
exact content bundle type, builds the export through the existing export
function, rejects mismatched direct-constructor exports and malformed package
metadata, and rejects positive authority-like language while allowing existing
negative advisory cautions. It adds no `from_dict()`, current-time generation,
file I/O, persistence, network/socket access, credentials, vendor APIs,
broker/runtime behavior, scheduler/dashboard behavior, notebooks, ML,
LLM/agent behavior, source/data approval, methodology approval,
strategy/signal/evaluator behavior, backtesting, ranking/scoring,
recommendations, allocation/order/portfolio mutation, risk approval,
paper/live readiness, capital authority, trading authority, or dependencies.
Normal pytest remains offline, credential-free, deterministic, and safe.

Phase 189 - Synthetic Advisory Operating Brief Package Fixture adds
`tests/fixtures/advisory_operating_brief_package.py` and
`tests/unit/test_advisory_operating_brief_package_fixture.py` as test-only
coverage for the Phase 188 package contract. The fixture composes the existing
research-queue-inclusive synthetic content bundle through
`build_advisory_operating_brief_package(...)` with fixed metadata:
`package_id="advisory-operating-brief-package:synthetic:2026-01-20"`,
`title="Synthetic advisory operating brief package"`, an advisory-only
synthetic package summary, and `as_of="2026-01-20"`.

The Phase 189 tests prove the fixture returns an exact
`AdvisoryOperatingBriefPackage`, the expected dictionary helper matches
`to_dict()` exactly while returning fresh mutable primitive copies, repeated
construction and compact JSON bytes are deterministic, the nested
`content_bundle` equals the research-queue-inclusive expected bundle, the
nested export payload/json/rendered text matches existing content bundle export
and renderer behavior, source content bundle identity is preserved, fixed
metadata is pinned, limitations and non-claims carry forward, no `from_dict()`
exists, and positive paper/live/approved/trading-ready/actionable authority
states are absent except explicit negative advisory cautions. No `src/`,
existing `AdvisoryOperatingBrief`, content bundle, renderer, export, CLI,
package production, file I/O, persistence, network/socket access, credentials,
vendor APIs, broker/runtime behavior, scheduler/dashboard behavior, notebooks,
ML, LLM/agent behavior, source/data approval, methodology approval,
strategy/signal/evaluator behavior, backtesting, ranking/scoring,
recommendations, allocation/order/portfolio mutation, risk approval,
paper/live readiness, capital authority, trading authority, or dependencies
changed. Normal pytest remains offline, credential-free, deterministic, and
safe.

Phase 190 - Advisory Operating Brief Package Text Renderer adds
`src/algotrader/research/advisory_operating_brief_package_renderer.py` with
`render_advisory_operating_brief_package_text(package)`. The renderer accepts
only the exact `AdvisoryOperatingBriefPackage` type, rejects subclasses,
lookalikes, dictionaries, and `None`, and renders exclusively from
`package.to_dict()`. The output pins deterministic package metadata order:
package type, package id, title, summary, as-of, status, authority, and
capital authority, then a clear content bundle section containing the stored
`content_bundle_export.rendered_text` exactly, followed by package-level
limitations and non-claims.

The Phase 190 tests use the Phase 189 synthetic package fixture to pin exact
rendered lines, prove repeated byte-for-byte deterministic rendering, confirm
the package dictionary, nested content bundle identity, and stored export
payload remain unchanged, and verify candidate research, strategy eligibility,
risk authority, and research queue content flow through the nested rendered
content bundle. AST/import/call guardrails prove production code imports no
tests or `tests.fixtures`, adds no `from_dict()`, does not read nested package
objects directly, and adds no file I/O, persistence, network/socket access,
credentials, vendor APIs, broker/runtime behavior, scheduler/dashboard
behavior, notebooks, ML, LLM/agent behavior, source/data approval,
methodology approval, strategy/signal/evaluator behavior, backtesting,
ranking/scoring, recommendations, allocation/order/portfolio mutation, risk
approval, paper/live readiness, capital authority, trading authority, or
dependencies. Existing `AdvisoryOperatingBrief`, package, package fixture,
content bundle, content bundle renderer, content bundle export, and CLI
behavior are unchanged. Normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 191 - Advisory Operating Brief Package Export Contract adds
`src/algotrader/research/advisory_operating_brief_package_export.py` with
frozen/slotted `AdvisoryOperatingBriefPackageExport` and
`export_advisory_operating_brief_package(package)`. The builder accepts only
the exact `AdvisoryOperatingBriefPackage` type, rejects subclasses,
lookalikes, dictionaries, and `None`, takes `payload` from `package.to_dict()`,
emits compact deterministic JSON with `sort_keys=True` and
`separators=(",", ":")`, and renders text through
`render_advisory_operating_brief_package_text(package)`.

The Phase 191 export validates direct construction by requiring a non-empty
primitive payload dictionary, non-empty compact JSON text that round-trips to
the payload, and non-empty rendered text. The stored payload is defensively
copied and repeated `payload` access returns fresh primitive copies, so callers
cannot mutate the export's stored package view through the accessor. Tests use
the Phase 189 synthetic package fixture to prove payload/json/rendered parity,
byte-for-byte repeated determinism, package `to_dict()` non-mutation, nested
content bundle identity preservation, nested content bundle export
non-mutation, frozen/slotted behavior, exact type rejection, absence of
`from_dict()`, no production imports from tests or `tests.fixtures`, and
AST/import/call guardrails. Existing `AdvisoryOperatingBrief`, package,
package fixture, package renderer, content bundle, content bundle renderer,
content bundle export, and CLI behavior are unchanged. No file I/O,
persistence, network/socket access, credentials, vendor APIs, broker/runtime
behavior, scheduler/dashboard behavior, notebooks, ML, LLM/agent behavior,
source/data approval, methodology approval, strategy/signal/evaluator
behavior, backtesting, ranking/scoring, recommendations,
allocation/order/portfolio mutation, risk approval, paper/live readiness,
capital authority, trading authority, or dependencies were added. Normal
pytest remains offline, credential-free, deterministic, and safe.

Phase 192 - Advisory Operating Brief Package CLI Preview adds
`src/algotrader/research/advisory_operating_brief_package_cli.py` and registers
`algotrader advisory-operating-brief-package-preview`. The preview is
synthetic-only, accepts only `--format text` or `--format json`, defaults to
text, builds the nested content bundle through production builders with
candidate research, strategy eligibility, risk authority, and research queue
branches included, wraps it with
`build_advisory_operating_brief_package(...)` using the fixed package id,
title, advisory-only summary, and `as_of="2026-01-20"`, and emits only
`export_advisory_operating_brief_package(...)` rendered text or compact JSON.

The Phase 192 tests prove default output equals explicit text output, rendered
text and compact JSON equal the package export views, JSON round-trips to the
expected package payload, repeated invocations are byte-for-byte deterministic,
package metadata and all nested content branches are visible, existing content
bundle preview behavior is unchanged, production CLI modules do not import
tests or `tests.fixtures`, and no file/path/source/vendor/broker/network/
runtime/credential options or paper/live/approved/trading-ready/actionable
authority states are introduced. Existing `AdvisoryOperatingBrief`, package,
package renderer/export, content bundle, content bundle renderer/export, and
content bundle CLI behavior remain unchanged. The command adds no file I/O,
persistence, network/socket access, credentials, vendor APIs, broker/runtime
behavior, scheduler/dashboard behavior, notebooks, ML, LLM/agent behavior,
source/data approval, methodology approval, strategy/signal/evaluator
behavior, backtesting, ranking/scoring, recommendations,
allocation/order/portfolio mutation, risk approval, paper/live readiness,
capital authority, trading authority, or dependencies. Normal pytest remains
offline, credential-free, deterministic, and safe.

Phase 193 - Advisory Operating Brief Package CLI Regression Guard adds
`tests/unit/test_advisory_operating_brief_package_cli_regression.py` as a
narrow test-only pin for
`algotrader advisory-operating-brief-package-preview`. The guard anchors the
default text, explicit text, and compact JSON stdout to
`export_advisory_operating_brief_package(...)` using the current package
preview builder, proves JSON round-trips to the exported preview payload, and
verifies
package metadata, advisory-only/candidate-only/capital-authority-false
metadata, nested candidate research, strategy eligibility, risk authority,
and research queue branches, limitations, and non-claims remain visible.

The Phase 193 tests also prove repeated default, explicit text, and JSON
invocations are byte-for-byte deterministic, the package preview CLI exposes
only `--format text|json`, no file/path/source/vendor/broker/network/runtime/
credential options are present, and existing content bundle preview default,
risk, research queue, and combined-flag outputs remain equal to their current
exports. AST/import/call/source guardrails cover the package preview module
and the regression guard itself so the preview remains synthetic-only and adds
no file I/O, persistence, network/socket access, credentials, vendor APIs,
broker/account/order/fill/allocation/portfolio mutation, runtime,
scheduler/dashboard behavior, notebooks, ML, LLM/agent behavior, ranking/
scoring, recommendations, approval/readiness/trading authority, actionable
behavior, or dependencies. Production package, package renderer/export,
content bundle, content bundle renderer/export, and CLI behavior are
unchanged. Normal pytest remains offline, credential-free, deterministic,
and safe.

Phase 194 - Advisory Operating Brief Package Synthetic Preview Alignment adds
`src/algotrader/research/advisory_operating_brief_package_synthetic.py` with
`build_synthetic_advisory_operating_brief_package_preview()` as the single
production-safe synthetic package preview builder. The builder uses production
content bundle preview builders to include candidate research, strategy
eligibility, risk authority, and research queue branches, then wraps the bundle
through `build_advisory_operating_brief_package(...)` with the fixed package
id, title, advisory-only synthetic summary, and `as_of="2026-01-20"`.

The Phase 194 package CLI now renders exports from the canonical synthetic
builder, and the test fixture delegates to the same builder while returning
fresh `to_dict()` primitive payloads. Package fixture, CLI, and Phase 193
regression tests now pin default text, explicit text, compact JSON, and export
payloads against the fixture package, proving fixture/CLI byte parity and
repeated deterministic output. Guardrails cover the new production synthetic
module and confirm no imports from `tests` or `tests.fixtures`, no new external
input options, no paper/live/approved/trading-ready/actionable states, and no
file I/O, persistence, network/socket access, credentials, vendor APIs,
broker/account/order/fill/allocation/portfolio mutation, runtime,
scheduler/dashboard behavior, notebooks, ML, LLM/agent behavior, ranking/
scoring, recommendations, approval/readiness/trading authority, actionable
behavior, or dependencies. Existing `AdvisoryOperatingBrief`, package contract,
renderer/export, content bundle contract, content bundle renderer/export, and
content bundle CLI behavior remain unchanged. Normal pytest remains offline,
credential-free, deterministic, and safe.

Phase 195 - Synthetic SMA Research Observation Mechanics adds
`src/algotrader/research/sma_research_observation.py` with frozen/slotted
`SmaResearchPricePoint`, frozen/slotted `SmaResearchObservation`, and pure
`build_sma_research_observation(...)`. The artifact is fixture-only research
mechanics: it validates ISO `YYYY-MM-DD` dates using standard library parsing,
sorts price points deterministically by date, rejects duplicate dates,
non-price-point inputs, non-positive closes, empty symbol/as-of strings, and
`window < 1`, uses only samples with `date <= as_of`, counts later samples as
ignored, and computes a Decimal SMA from the latest eligible window only.

If eligible samples are below the window, the Phase 195 builder emits
`position_vs_sma="insufficient_history"` with SMA and distance fields set to
`None`; otherwise it emits one of `above`, `below`, or `equal` based solely on
Decimal distance from the SMA. `to_dict()` is deterministic and primitive-only,
serializes Decimals as strings and tuples as lists, and exposes no
`from_dict()`. Required non-claims explicitly deny strategy approval,
source/data approval, predictive validity, profitability, recommendation,
signal/evaluator behavior, allocation/order authority, broker authority,
portfolio mutation authority, paper/live readiness, capital authority, and
trading authority. Tests cover exact above/below/equal/insufficient payloads,
future-sample ignoring, duplicate and malformed input rejection,
frozen/slotted behavior, repeated deterministic construction, primitive
serialization, no actionable payload keys, no imports from tests or fixtures,
and AST/import guardrails against file I/O, persistence, network/socket,
vendor APIs, broker/runtime behavior, scheduler/dashboard behavior, notebooks,
ML, LLM/agent behavior, ranking/scoring, recommendations, approvals,
readiness, allocation/order/portfolio mutation, capital authority, trading
authority, or new dependencies. Advisory package, package synthetic builder,
package CLI, content bundle, renderer, export, and existing CLI behavior remain
unchanged. Normal pytest remains offline, credential-free, deterministic, and
safe.

Phase 196 - Synthetic SMA Research Observation Fixture adds
`tests/fixtures/sma_research_observation.py` and
`tests/unit/test_sma_research_observation_fixture.py` as a tests-only fixture
layer over the Phase 195 production types. The fixture exposes deterministic
synthetic broad ETF SMA-like price points for `symbol="SYNTH_ETF"`,
`as_of="2026-01-20"`, and `window=3`, plus exact expected primitive
dictionaries for the price points, the primary observation, and an
insufficient-history observation.

The primary Phase 196 observation includes one later-dated sample that is
ignored and counted, keeps three eligible samples, and pins
`position_vs_sma="above"` with `latest_close="110.00"`,
`sma_value="100.00"`, `distance_from_sma="10.00"`, and
`distance_from_sma_pct="0.1"`. The insufficient-history fixture keeps fewer
eligible samples than the window, preserves the latest eligible close, emits
`position_vs_sma="insufficient_history"`, and leaves SMA and distance fields
as `None` per the Phase 195 contract. Tests prove fixture builders return the
exact Phase 195 production types, expected dict helpers match `.to_dict()`
exactly, helpers return fresh mutable primitive copies, repeated construction
and compact JSON bytes are deterministic, future-sample counts are pinned,
fixed advisory metadata is stable, required limitations and non-claims are
present, and no paper/live/approved/trading-ready/actionable authority states
appear. Fixture AST/import/call/source guardrails cover broker/account/order/
fill/allocation/portfolio mutation behavior, file I/O, persistence,
network/socket access, vendor APIs, credentials, runtime/scheduler/dashboard
behavior, notebooks, ML, LLM/agent behavior, ranking/scoring,
recommendations, approval/readiness/trading authority language outside
explicit non-claims, and `from_dict()`. No `src` files, advisory operating
brief package, package synthetic builder, package CLI, content bundle,
renderer, export, existing CLI behavior, real data ingestion, evaluator,
backtesting, strategy execution, or dependencies change. Normal pytest remains
offline, credential-free, deterministic, and safe.

Phase 197 - SMA Research Observation Brief Item adds
`src/algotrader/research/sma_research_observation_brief.py` with frozen/slotted
`SmaResearchObservationBriefItem` and
`build_sma_research_observation_brief_item(observation)`. The wrapper accepts
only the exact Phase 195 `SmaResearchObservation` type, preserves the source
observation object identity, and emits fixed `item_type`,
candidate-only/advisory-only/capital-authority-false metadata.

The Phase 197 builder maps `position_vs_sma` deterministically to one of
`above_sma_observation`, `below_sma_observation`, `equal_sma_observation`, or
`insufficient_history`, then generates deterministic non-actionable headline
and summary text from observation metadata only. It carries forward source
limitations and non-claims with first-seen de-dupe and validates direct
construction against source metadata so malformed lookalikes, subclasses,
metadata mismatches, and authority/actionability wording outside explicit
non-claims are rejected. `to_dict()` is deterministic and primitive-only,
includes nested `source_observation.to_dict()`, serializes tuples as lists,
does not mutate the source observation, and adds no `from_dict()`.

Phase 197 tests cover above-SMA and insufficient-history fixture wrapping,
exact source identity, exact type rejection for non-observations, lookalikes,
and subclasses, fixed advisory metadata, all mechanical state mappings,
deterministic non-actionable headline and summary text, limitation/non-claim
carry-forward, primitive deterministic serialization, compact JSON byte
determinism, source observation non-mutation, frozen/slotted behavior, absence
of `from_dict()`, no public buy/sell/hold/signal/evaluator/order/allocation/
broker/portfolio/trading-authority payload fields, no production imports from
`tests` or `tests.fixtures`, and AST/import/call/source guardrails against
file I/O, persistence, network/socket access, vendor APIs, credentials,
broker/runtime behavior, scheduler/dashboard behavior, notebooks, ML,
LLM/agent behavior, ranking/scoring, recommendations, approvals/readiness,
allocation/order/portfolio mutation, capital authority, trading authority, or
new dependencies. SMA research observation mechanics and fixtures, advisory
operating brief package, package synthetic builder, package CLI, content
bundle, renderer, export, and existing CLI behavior remain unchanged. Normal
pytest remains offline, credential-free, deterministic, and safe.

Phase 198 - Synthetic SMA Research Observation Brief Fixture adds
`tests/fixtures/sma_research_observation_brief.py` and
`tests/unit/test_sma_research_observation_brief_fixture.py` as a tests-only
fixture layer over the Phase 197 brief item. The fixture builds its primary
brief item from `build_synthetic_sma_research_observation()` and its
insufficient-history brief item from
`build_synthetic_insufficient_history_sma_research_observation()`, preserving
the exact source observation object carried by the Phase 197 wrapper.

The primary Phase 198 fixture pins
`mechanical_state="above_sma_observation"` with nested
`source_observation` matching
`expected_synthetic_sma_research_observation_dict()`. The
insufficient-history fixture pins `mechanical_state="insufficient_history"`
with nested `source_observation` matching
`expected_synthetic_insufficient_history_sma_research_observation_dict()`.
Both expected dict helpers emit fixed
`item_type="sma_research_observation_brief_item"`, candidate-only/advisory-only
/capital-authority-false metadata, deterministic headline and summary text,
source limitations, source non-claims, and fresh primitive nested payload
copies. Tests prove exact Phase 197 production type construction, `.to_dict()`
parity, fresh mutable primitive expected dictionaries, deterministic repeated
construction, compact JSON byte determinism, Phase 196 nested source payload
parity, source observation identity preservation through the wrapper,
limitation/non-claim carry-forward, no `from_dict()`, no paper/live/approved/
trading-ready/actionable authority states outside explicit non-claims, and
fixture AST/import/call/source guardrails against broker/account/order/fill/
allocation/portfolio mutation behavior, file I/O, persistence, network/socket
access, vendor APIs, credentials, runtime/scheduler/dashboard behavior,
notebooks, ML, LLM/agent behavior, ranking/scoring, recommendations,
approval/readiness/trading authority language outside explicit non-claims, or
new dependencies. No `src` files, SMA mechanics, SMA observation fixtures,
advisory operating brief package, package synthetic builder, package CLI,
content bundle, renderer, export, or existing CLI behavior change. Normal
pytest remains offline, credential-free, deterministic, and safe.

Phase 199 - SMA Research Observation Brief Section adds
`src/algotrader/research/sma_research_observation_brief_section.py` with
frozen/slotted `SmaResearchObservationBriefSection` and
`build_sma_research_observation_brief_section(section_id, title, summary,
items)`. The section is a deterministic metadata-only advisory container for
Phase 197 `SmaResearchObservationBriefItem` objects. It emits fixed
`section_type="sma_research_observation_brief_section"`,
candidate-only/advisory-only/capital-authority-false metadata, requires
non-empty advisory-safe section id, title, and summary text, requires at least
one exact brief item, rejects malformed lookalikes and subclasses, rejects
duplicate item identities, and preserves item identity and order.

The Phase 199 builder carries item limitations and non-claims forward with
first-seen de-dupe. Direct construction validates fixed metadata and requires
section limitations and non-claims to match the item-derived values. `to_dict()`
is deterministic and primitive-only, includes section id, title, summary,
item count, each nested `item.to_dict()`, limitations, and non-claims, and does
not mutate source items. Tests build a two-item section from the Phase 198
above-SMA and insufficient-history fixtures; prove exact identity/order,
empty and duplicate item rejection, exact-type rejection, fixed advisory
metadata, limitation/non-claim carry-forward, primitive deterministic
serialization, compact JSON byte determinism, source item non-mutation,
frozen/slotted behavior, absence of `from_dict()`, no public buy/sell/hold/
signal/evaluator/order/allocation/broker/portfolio/trading-authority payload
fields, no production imports from `tests` or `tests.fixtures`, and
AST/import/call/source guardrails against file I/O, persistence,
network/socket access, vendor APIs, credentials, broker/runtime behavior,
scheduler/dashboard behavior, notebooks, ML, LLM/agent behavior,
ranking/scoring, recommendations, approvals/readiness, allocation/order/
portfolio mutation, capital authority, trading authority, or new dependencies.
SMA mechanics, SMA observation fixtures, SMA observation brief item behavior,
advisory operating brief package, package synthetic builder, package CLI,
content bundle, renderer, export, and existing CLI behavior remain unchanged.
Normal pytest remains offline, credential-free, deterministic, and safe.

Phase 200 - Synthetic SMA Research Observation Brief Section Fixture adds
`tests/fixtures/sma_research_observation_brief_section.py` and
`tests/unit/test_sma_research_observation_brief_section_fixture.py` as a
tests-only fixture layer over the Phase 199 section container. The fixture
builds from the Phase 198 above-SMA and insufficient-history brief item
fixtures, uses
`section_id="sma-research-observation-section:synthetic:broad-etf-sma"`,
`title="Synthetic broad ETF SMA observation summary"`, and a deterministic
summary stating the section is advisory-only synthetic SMA observation content.

The Phase 200 section fixture preserves exact item identity and order,
contains exactly two items (`above_sma_observation` followed by
`insufficient_history`), carries item limitations and non-claims forward with
first-seen de-dupe, and emits fixed
`section_type="sma_research_observation_brief_section"`,
candidate-only/advisory-only/capital-authority-false metadata. The expected
dict helper composes nested item payloads from the Phase 198 expected brief
item dictionaries and returns fresh primitive copies. Tests prove exact Phase
199 production type construction, `.to_dict()` parity, fresh mutable primitive
expected dictionaries, deterministic repeated construction, compact JSON byte
determinism, nested Phase 198 payload parity, item identity preservation
through the section builder, limitation/non-claim carry-forward, absence of
`from_dict()`, no paper/live/approved/trading-ready/actionable authority
states outside explicit non-claims, and fixture AST/import/call/source
guardrails against broker/account/order/fill/allocation/portfolio mutation
behavior, file I/O, persistence, network/socket access, vendor APIs,
credentials, runtime/scheduler/dashboard behavior, notebooks, ML, LLM/agent
behavior, ranking/scoring, recommendations, approval/readiness/trading
authority language outside explicit non-claims, or new dependencies. No `src`
files, SMA mechanics, SMA observation fixtures, SMA observation brief item
behavior, SMA observation brief section behavior, advisory operating brief
package, package synthetic builder, package CLI, content bundle, renderer,
export, or existing CLI behavior change. Normal pytest remains offline,
credential-free, deterministic, and safe.

Phase 201 - SMA Research Observation Brief Container adds
`src/algotrader/research/sma_research_observation_brief_container.py` with
frozen/slotted `SmaResearchObservationBrief` and
`build_sma_research_observation_brief(brief_id, title, summary, sections)`.
The module is separate from `sma_research_observation_brief.py` so the brief
item module remains item-only and avoids section/container import cycles. The
container accepts only exact Phase 199 `SmaResearchObservationBriefSection`
objects, requires at least one section, rejects malformed lookalikes and
subclasses, rejects duplicate section identities, preserves section identity
and order, and emits fixed `brief_type="sma_research_observation_brief"`,
candidate-only/advisory-only/capital-authority-false metadata.

The Phase 201 builder requires non-empty advisory-safe brief id, title, and
summary text, carries section limitations and non-claims forward with
first-seen de-dupe, and direct construction validates fixed metadata plus
section-derived limitations/non-claims. `to_dict()` is deterministic and
primitive-only, includes brief id, title, summary, section count, each nested
`section.to_dict()`, limitations, and non-claims, and does not mutate source
sections. Tests build a brief from the Phase 200 synthetic section fixture;
prove exact section identity/order, empty and duplicate section rejection,
exact-type rejection for non-sections/lookalikes/subclasses, fixed advisory
metadata, limitation/non-claim carry-forward, primitive deterministic
serialization, compact JSON byte determinism, source section non-mutation,
frozen/slotted behavior, absence of `from_dict()`, no public buy/sell/hold/
signal/evaluator/order/allocation/broker/portfolio/trading-authority payload
fields, no production imports from `tests` or `tests.fixtures`, and
AST/import/call/source guardrails against file I/O, persistence,
network/socket access, vendor APIs, credentials, broker/runtime behavior,
scheduler/dashboard behavior, notebooks, ML, LLM/agent behavior,
ranking/scoring, recommendations, approvals/readiness, allocation/order/
portfolio mutation, capital authority, trading authority, or new dependencies.
SMA mechanics, SMA observation fixtures, SMA observation brief item behavior,
SMA observation brief section behavior, SMA section fixtures, advisory
operating brief package, package synthetic builder, package CLI, content
bundle, renderer, export, and existing CLI behavior remain unchanged. Normal
pytest remains offline, credential-free, deterministic, and safe.

Phase 202 - Synthetic SMA Research Observation Brief Container Fixture adds
`tests/fixtures/sma_research_observation_brief_container.py` and
`tests/unit/test_sma_research_observation_brief_container_fixture.py` as a
tests-only fixture layer over the Phase 201 brief container. The fixture builds
from the Phase 200 synthetic section fixture, uses
`brief_id="sma-research-observation-brief:synthetic:broad-etf-sma"`,
`title="Synthetic broad ETF SMA research observation brief"`, and a
deterministic summary stating the brief is advisory-only synthetic SMA
observation content.

The Phase 202 container fixture preserves exact section identity and order,
contains exactly one section from the Phase 200 fixture, carries section
limitations and non-claims forward, and emits fixed
`brief_type="sma_research_observation_brief"`,
candidate-only/advisory-only/capital-authority-false metadata. The expected
dict helper composes the nested section payload from the Phase 200 expected
section dictionary and returns fresh primitive copies. Tests prove exact Phase
201 production type construction, `.to_dict()` parity, fresh mutable primitive
expected dictionaries, deterministic repeated construction, compact JSON byte
determinism, nested Phase 200 payload parity, section identity preservation
through the container builder, limitation/non-claim carry-forward, absence of
`from_dict()`, no paper/live/approved/trading-ready/actionable authority
states outside explicit non-claims, and fixture AST/import/call/source
guardrails against broker/account/order/fill/allocation/portfolio mutation
behavior, file I/O, persistence, network/socket access, vendor APIs,
credentials, runtime/scheduler/dashboard behavior, notebooks, ML, LLM/agent
behavior, ranking/scoring, recommendations, approval/readiness/trading
authority language outside explicit non-claims, or new dependencies. No `src`
files, SMA mechanics, SMA observation fixtures, SMA observation brief item
behavior, SMA observation brief section behavior, SMA section fixtures, SMA
brief container behavior, advisory operating brief package, package synthetic
builder, package CLI, content bundle, renderer, export, or existing CLI
behavior change. Normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 203 - SMA Research Observation Brief Text Renderer adds
`src/algotrader/research/sma_research_observation_brief_renderer.py` with
`render_sma_research_observation_brief_text(brief)` plus
`tests/unit/test_sma_research_observation_brief_renderer.py`. The renderer
accepts only exact Phase 201 `SmaResearchObservationBrief` objects, rejects
malformed lookalikes, dictionaries, `None`, and subclasses, and renders solely
from `brief.to_dict()` so source brief, section, item, and nested observation
objects are not mutated.

The Phase 203 renderer emits deterministic plain text for brief metadata,
sections, items, nested source observation mechanics, limitations, and
non-claims. It preserves section and item sequence, includes ignored future
sample counts, renders insufficient-history SMA and distance mechanics as
`null`, and keeps the output byte-for-byte stable across repeated renders.
Tests pin the exact rendered text for the Phase 202 synthetic brief fixture;
prove source `.to_dict()` and nested identities are unchanged; verify both
`above_sma_observation` and `insufficient_history`; reject invalid inputs; and
guard production imports, calls, source literals, public renderer concepts,
and rendered text against broker/account/order/fill/allocation/portfolio
mutation behavior, file I/O, persistence, network/socket access, vendor APIs,
credentials, runtime/scheduler/dashboard behavior, notebooks, ML, LLM/agent
behavior, ranking/scoring, recommendations, approval/readiness/trading
authority language outside explicit non-claims, or new dependencies. SMA
mechanics, fixtures, brief item behavior, section behavior, container behavior,
advisory operating brief package, package synthetic builder, package CLI,
content bundle, renderer, export, and existing CLI behavior remain unchanged.
Normal pytest remains offline, credential-free, deterministic, and safe.

Phase 204 - SMA Research Observation Brief Export Contract adds
`src/algotrader/research/sma_research_observation_brief_export.py` with
frozen/slotted `SmaResearchObservationBriefExport` and
`export_sma_research_observation_brief(brief)`, plus
`tests/unit/test_sma_research_observation_brief_export.py`. The export accepts
only exact Phase 201 `SmaResearchObservationBrief` objects, rejects malformed
lookalikes, dictionaries, `None`, and subclasses, and produces three
in-memory views only: primitive `payload`, compact deterministic `json_text`,
and Phase 203 `rendered_text`.

The Phase 204 export validates direct construction by requiring a non-empty
primitive payload dictionary, non-empty compact JSON text that round-trips to
the payload, and non-empty rendered text. Payload access returns fresh
primitive copies, repeated exports are byte-for-byte deterministic, and source
brief, section, item, and nested observation identities and `.to_dict()`
outputs remain unchanged. Tests prove builder acceptance of the Phase 202
synthetic fixture, compact JSON settings (`sort_keys=True` and
`separators=(",", ":")`), rendered text parity with the Phase 203 renderer,
frozen/slotted behavior, invalid input and malformed direct-construction
rejection, absence of `from_dict()`, no production imports from tests or
fixtures, no public buy/sell/hold/signal/evaluator/order/allocation/broker/
portfolio/trading-authority export concepts, and AST/import/call/source/text
guardrails against file I/O, persistence, network/socket access, vendor APIs,
credentials, runtime/scheduler/dashboard behavior, notebooks, ML, LLM/agent
behavior, ranking/scoring, recommendations, approvals/readiness/trading
authority language outside explicit non-claims, or new dependencies. SMA
mechanics, fixtures, brief item behavior, section behavior, container
behavior, renderer behavior, advisory operating brief package, package
synthetic builder, package CLI, content bundle, renderer, export, and existing
CLI behavior remain unchanged. Normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 205 - Advisory Operating Brief Content Bundle SMA Research Observation
Branch extends `src/algotrader/research/advisory_operating_brief_content_bundle.py`
with an optional `sma_research_observation_briefs` branch for exact Phase 201
`SmaResearchObservationBrief` objects. The bundle still emits fixed
`bundle_type="advisory_operating_brief_content_bundle"`,
candidate-only/advisory-only/capital-authority-false metadata, requires at
least one total brief across all supported branches, preserves object identity
and order inside each branch, rejects malformed inputs and subclasses, rejects
duplicate identities across all branches, and carries limitations and
non-claims forward with first-seen de-dupe.

The Phase 205 `to_dict()` output remains deterministic and primitive-only. It
adds `sma_research_observation_brief_count` and
`sma_research_observation_briefs` only when the SMA branch is populated, which
keeps the existing no-risk, risk-inclusive, and research-queue-inclusive
fixture payloads byte-for-byte unchanged. The new synthetic fixture helper
composes candidate research, strategy eligibility, risk authority, research
queue, and SMA research observation briefs through the production bundle
builder, and its expected dictionary nests the Phase 202 SMA brief expected
payload. Tests prove existing fixture compatibility, new SMA branch payload
presence, nested SMA payload parity, branch identity/order preservation,
cross-branch duplicate rejection, deterministic repeated construction, fresh
mutable primitive expected dictionaries, and unchanged renderer/export/CLI
behavior. No real data ingestion, broker/runtime behavior, file I/O,
persistence, network/socket access, credentials, scheduler/dashboard behavior,
notebooks, ML, LLM/agent behavior, ranking/scoring, recommendations,
approval/readiness/trading authority behavior, new dependencies, or `from_dict()`
are added. Normal pytest remains offline, credential-free, deterministic, and
safe.

Phase 206 - Advisory Operating Brief Content Bundle Renderer SMA Research
Observation Branch extends
`src/algotrader/research/advisory_operating_brief_content_bundle_renderer.py`
to conditionally render `sma_research_observation_briefs` solely from the
bundle `to_dict()` payload. Existing no-SMA renderer output for the Phase 162
candidate-plus-strategy fixture, Phase 178 risk-inclusive fixture, and Phase
184/185 research-queue-inclusive fixture remains byte-for-byte pinned.

The Phase 206 SMA branch is rendered after candidate research, strategy
eligibility, risk authority, and research queue branches, and before aggregate
limitations/non-claims. It emits deterministic text for SMA brief, section,
item, and nested source-observation metadata, including ignored future sample
counts, null SMA and distance mechanics for insufficient history, limitations,
and non-claims. Tests prove both `above_sma_observation` and
`insufficient_history`, repeated SMA-inclusive rendering stability, unchanged
source `.to_dict()` output and object identities, dictionary-only renderer
access, no production imports from tests or fixtures, no export/CLI/package/SMA
export coupling, and AST/import/call/source/text guardrails against file I/O,
persistence, network/socket access, vendor APIs, credentials,
runtime/scheduler/dashboard behavior, notebooks, ML, LLM/agent behavior,
ranking/scoring, recommendations, approvals/readiness/trading authority
behavior, dependencies, or `from_dict()`. Content bundle construction, content
bundle export, content bundle CLI, package behavior, SMA mechanics, SMA brief
renderer, SMA brief export, and existing CLI behavior remain unchanged. Normal
pytest remains offline, credential-free, deterministic, and safe.

Phase 207 - Advisory Operating Brief Content Bundle Export SMA Branch
Regression Guard adds
`tests/unit/test_advisory_operating_brief_content_bundle_export_with_sma_research_observation_regression.py`
as a test-only guard for the existing export path over the Phase 205/206
SMA-inclusive synthetic content bundle. The regression proves the exported
payload equals the pinned SMA-inclusive expected dictionary, compact JSON uses
`sort_keys=True` with `separators=(",", ":")`, JSON round-trips to the same
primitive payload, rendered text matches
`render_advisory_operating_brief_content_bundle_text(bundle)`, and repeated
exports are byte-for-byte deterministic.

The Phase 207 guard pins candidate research, strategy eligibility, risk
authority, research queue, and SMA research observation branches together,
including `sma_research_observation_brief_count`,
`sma_research_observation_briefs`, nested SMA source-observation metadata,
`above_sma_observation`, `insufficient_history`, ignored future sample counts,
and null SMA/distance fields for insufficient history. It also proves branch
sequence, limitations, non-claims, and source-bundle mutation isolation. No
source files, content bundle construction, renderer, export implementation,
CLI, package behavior, package synthetic builder, package CLI, SMA mechanics,
SMA brief renderer, SMA brief export, or existing CLI behavior changed. The
new test carries AST/import/call/source guardrails against real data
ingestion, file I/O, persistence, network/socket access, vendor APIs,
credentials, runtime/scheduler/dashboard behavior, notebooks, ML, LLM/agent
behavior, recommendations, ranking/scoring, approvals/readiness/trading
authority behavior outside explicit non-claims, dependencies, or `from_dict()`.
Normal pytest remains offline, credential-free, deterministic, and safe.

Phase 208 - Advisory Operating Brief Content Bundle CLI SMA Research
Observation Preview exposes the existing SMA-inclusive synthetic content bundle
through `algotrader advisory-operating-brief-content-bundle-preview` with the
hidden synthetic-only `--include-sma-research-observation` flag. The default,
`--format text|json`, `--include-risk-authority`,
`--include-research-queue`, and combined risk plus research-queue preview
outputs remain byte-for-byte unchanged.

The Phase 208 preview helper builds the SMA observation branch from production
SMA observation and brief builders only, then routes text and JSON through
`export_advisory_operating_brief_content_bundle(...)`. The new flag composes
candidate research, strategy eligibility, and SMA research observation
branches by default, and includes risk and/or research queue branches only when
their existing flags are also present. Tests pin compact deterministic JSON,
JSON round-tripping, repeated byte-identical SMA-inclusive CLI invocations,
`above_sma_observation`, `insufficient_history`, ignored future sample counts,
and null SMA/distance fields for insufficient history. Production CLI modules
still import no tests or fixtures and add no file/path/source/vendor/broker/
network/runtime/credential options, real data ingestion, persistence,
scheduler/dashboard behavior, notebooks, ML, LLM/agent behavior, scoring,
recommendations, approvals/readiness/trading authority behavior, dependencies,
or `from_dict()`. Normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 209 - Advisory Operating Brief Package Synthetic SMA Branch Alignment
updates `build_synthetic_advisory_operating_brief_package_preview()` so the
canonical package preview now builds the existing SMA-inclusive content bundle
with risk authority and research queue branches enabled. The package metadata
remains pinned to
`advisory-operating-brief-package:synthetic:2026-01-20`, the synthetic advisory
title/summary, `as_of="2026-01-20"`, `status="candidate_only"`,
`authority="advisory_only"`, and `capital_authority=False`.

The Phase 209 package fixture continues to delegate to the production-safe
synthetic package builder while tests pin candidate research, strategy
eligibility, risk authority, research queue, and SMA research observation
branches together. Package fixture, export, renderer, CLI, and CLI regression
tests now prove the nested content bundle payload/export/rendered text includes
`sma_research_observation_brief_count` and
`sma_research_observation_briefs`, round-trips through compact deterministic
JSON, and stays byte-for-byte deterministic across repeated fixture, export,
and CLI invocations. Content bundle preview behavior and package preview
options remain unchanged; no file/path/source/vendor/broker/network/runtime/
credential options, real data ingestion, persistence, scheduler/dashboard
behavior, notebooks, ML, LLM/agent behavior, recommendations, ranking/scoring,
approval/readiness/trading authority behavior, dependencies, or `from_dict()`
are added. Normal pytest remains offline, credential-free, deterministic, and
safe.

Phase 210 - Synthetic Close-to-Close Research Return Observation Mechanics adds
`algotrader.research.research_return_observation` as a tiny synthetic-only
research mechanics artifact. It defines frozen/slotted price points, return
points, and a candidate-only/advisory-only return series observation with
`capital_authority=False`, `return_method="close_to_close_simple_return"`, and
`price_basis="synthetic_close"`.

The Phase 210 builder validates strict `YYYY-MM-DD` dates, sorts synthetic
price points deterministically, ignores and counts future samples relative to
the supplied `as_of`, rejects duplicate dates and non-positive closes, and
constructs only consecutive close-to-close simple returns:
`(end_close / start_close) - Decimal("1")`. Fewer than two eligible samples
produce zero returns. The artifact does not annualize, compound, benchmark,
model transaction costs/slippage/dividends, claim adjusted-close or
corporate-action completeness, rank/score, recommend, emit signals, allocate,
order, mutate portfolios, approve sources/data/methodology/readiness, or add
broker/runtime behavior. Serialization is deterministic primitive-only output
with Decimal values as strings, tuple fields as lists, nested return points
through deterministic dictionaries, required negative non-claims, and no
`from_dict()`. Tests add AST/import/call/reference guardrails against file I/O,
network/socket access, vendor APIs, broker/runtime/scheduler/dashboard
behavior, persistence, credentials, notebooks, ML, LLM/agent behavior,
recommendations, ranking/scoring, approvals/readiness, allocation/order/
portfolio mutation, capital authority, trading authority, tests/fixture
imports, new dependencies, or real data ingestion. Normal pytest remains
offline, credential-free, deterministic, and safe.

Phase 211 - Synthetic Research Return Observation Fixture adds
`tests/fixtures/research_return_observation.py` and
`tests/unit/test_research_return_observation_fixture.py` as a deterministic
fixture layer over the Phase 210 production mechanics. The fixture uses only
synthetic broad ETF-like closes for `symbol="SYNTH_ETF"` and
`as_of="2026-01-20"`, pins `return_method` to
`close_to_close_simple_return`, `price_basis` to `synthetic_close`,
`status="candidate_only"`, `authority="advisory_only"`, and
`capital_authority=False`, and provides exact expected primitive dictionary
helpers for both the primary and insufficient-history observations.

The primary Phase 211 fixture has five deterministic price points, four
eligible samples, one ignored future sample, and consecutive eligible
close-to-close returns covering positive, negative, and zero simple returns.
The insufficient fixture has fewer than two eligible samples, counts one
ignored future sample, and emits `return_count=0` with `returns=[]`. Tests
prove fixture builders return exact Phase 210 production types, expected
dictionary helpers match `.to_dict()` exactly while returning fresh mutable
primitive copies, repeated construction and compact JSON bytes are
deterministic, future samples are excluded, fixed advisory metadata,
limitations, and non-claims are pinned, no `from_dict()` exists, and no
paper/live/approved/trading-ready/actionable authority states appear. Fixture
AST/import/call/literal guardrails exclude real data ingestion, file I/O,
persistence, network/socket access, vendor APIs, credentials, broker/account/
order/fill/allocation/portfolio mutation behavior, runtime/scheduler/
dashboard behavior, notebooks, ML, LLM/agent behavior, recommendations,
ranking/scoring, approvals/readiness/trading authority behavior outside
explicit non-claims, dependencies, or production imports from tests. No source
files, advisory package, synthetic package builder, package CLI, content
bundle, renderer/export, SMA mechanics, SMA brief renderer/export, or existing
CLI behavior changed. Normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 212 - Research Return Observation Brief Item adds
`algotrader.research.research_return_observation_brief` as a tiny
metadata-only advisory wrapper around Phase 210 research return observations.
It defines frozen/slotted `ResearchReturnObservationBriefItem` and
`build_research_return_observation_brief_item()` with fixed
`item_type="research_return_observation_brief_item"`,
`status="candidate_only"`, `authority="advisory_only"`, and
`capital_authority=False`.

The Phase 212 builder accepts only exact `ResearchReturnSeriesObservation`
instances, preserves source observation identity, maps `return_count=0` to
`insufficient_return_history` and nonzero return counts to
`returns_constructed`, and deterministically counts positive, negative, and
zero simple returns from the source return points. Headline and summary text
are generated from source observation metadata and return direction counts as
advisory research content only. Limitations and non-claims are carried forward
with first-seen de-duplication, while authority/actionability wording remains
rejected outside explicit non-claims. Serialization is deterministic
primitive-only output with nested `source_observation.to_dict()`, tuple fields
as lists, fixed metadata, mechanical state, return direction counts, and no
`from_dict()`. Tests pin the Phase 211 primary and insufficient fixtures,
source identity, exact source type rejection for malformed lookalikes and
subclasses, frozen/slotted behavior, compact JSON byte determinism, source
observation non-mutation, forbidden public payload keys, no production imports
from tests, and AST/import/call/literal guardrails against file I/O,
network/socket access, vendor APIs, broker/runtime/scheduler/dashboard
behavior, persistence, credentials, notebooks, ML, LLM/agent behavior,
recommendations, ranking/scoring, approvals/readiness, allocation/order/
portfolio mutation, capital authority, trading authority, dependencies, or
real data ingestion. Research return mechanics, fixtures, advisory packages,
synthetic package builders, package CLI/content bundle/renderer/export, SMA
mechanics/brief rendering/export, and existing CLI behavior remain unchanged.
Normal pytest remains offline, credential-free, deterministic, and safe.

Phase 213 - Synthetic Research Return Observation Brief Fixture adds
`tests/fixtures/research_return_observation_brief.py` and
`tests/unit/test_research_return_observation_brief_fixture.py` as a
deterministic fixture layer over the Phase 212 brief item. The primary helper
builds from the Phase 211 synthetic return observation, preserves the exact
source observation object inside the Phase 212 item, pins
`mechanical_state="returns_constructed"`, and pins positive, negative, and zero
return counts to one each. The insufficient-history helper builds from the
Phase 211 insufficient return observation, preserves source identity, pins
`mechanical_state="insufficient_return_history"`, and pins all return direction
counts to zero.

The Phase 213 expected dictionary helpers match `.to_dict()` exactly while
returning fresh mutable primitive copies. Their nested `source_observation`
payloads match the Phase 211 expected observation payloads, including fixed
candidate-only/advisory-only metadata, limitations, and non-claims. Tests prove
repeated construction and compact JSON bytes are deterministic, no
`from_dict()` exists, and no paper/live/approved/trading-ready/actionable
authority states appear. Fixture AST/import/call/literal guardrails exclude
broker/account/order/fill/allocation/portfolio mutation behavior, file I/O,
network/socket access, vendor APIs, credentials, runtime/scheduler/dashboard
behavior, notebooks, ML, LLM/agent behavior, recommendations, ranking/scoring,
approvals/readiness/trading authority language outside explicit non-claims,
new dependencies, and production imports from tests. No source files, research
return mechanics, Phase 211 observation fixtures, advisory package, synthetic
package builder, package CLI, content bundle, renderer/export, SMA mechanics,
SMA brief renderer/export, or existing CLI behavior changed. Normal pytest
remains offline, credential-free, deterministic, and safe.

Phase 214 - Research Return Observation Brief Section adds
`algotrader.research.research_return_observation_brief_section` as a frozen,
slotted, metadata-only advisory grouping for exact Phase 212
`ResearchReturnObservationBriefItem` objects. The builder accepts a section id,
title, summary, and one or more exact brief items, preserves item object
identity and order, rejects empty collections, duplicate item identities,
malformed lookalikes, and subclasses, and pins
`section_type="research_return_observation_brief_section"`,
`status="candidate_only"`, `authority="advisory_only"`, and
`capital_authority=False`.

The Phase 214 section carries item limitations and non-claims forward with
first-seen de-duplication while rejecting authority/actionability wording
outside explicit non-claims. Serialization is deterministic primitive-only
metadata with fixed section fields, item count, nested `item.to_dict()`
payloads, list-form tuple fields, and no `from_dict()`. Tests build from the
Phase 213 primary and insufficient-history fixtures, prove source item
`.to_dict()` outputs are unchanged before and after construction and
serialization, pin compact JSON byte determinism, verify frozen/slotted
behavior, confirm public payload keys avoid action/trading fields, and enforce
AST/import/call/literal guardrails against file I/O, network/socket access,
vendor APIs, broker/runtime/scheduler/dashboard behavior, persistence,
credentials, notebooks, ML, LLM/agent behavior, recommendations,
ranking/scoring, approvals/readiness, allocation/order/portfolio mutation,
capital authority, trading authority, new dependencies, and production imports
from tests. Research return mechanics, observation fixtures, brief item
behavior, advisory package, package synthetic builder, package CLI, content
bundle, renderer/export, SMA mechanics, SMA brief renderer/export, and existing
CLI behavior remain unchanged. Normal pytest remains offline,
credential-free, deterministic, and safe.

Phase 215 - Synthetic Research Return Observation Brief Section Fixture adds
`tests/fixtures/research_return_observation_brief_section.py` and
`tests/unit/test_research_return_observation_brief_section_fixture.py` as a
tests-only fixture layer over the Phase 214 section container. The fixture
builds from the Phase 213 primary and insufficient-history brief item fixtures,
uses
`section_id="research-return-observation-section:synthetic:broad-etf-return-construction"`,
`title="Synthetic broad ETF return observation summary"`, and a deterministic
summary stating the section is advisory-only synthetic close-to-close return
observation content.

The Phase 215 expected dictionary helper matches
`ResearchReturnObservationBriefSection.to_dict()` exactly while returning fresh
mutable primitive copies. It nests the exact Phase 213 primary
`returns_constructed` item payload followed by the
`insufficient_return_history` item payload, pins fixed candidate-only,
advisory-only, capital-authority-false section metadata, carries limitations
and non-claims forward with first-seen de-duplication, and preserves item
identity and section ordering through the Phase 214 builder. Tests prove
repeated construction and compact JSON bytes are deterministic, nested
positive/negative/zero return-count metadata and insufficient-history metadata
remain present, no `from_dict()` exists, no paper/live/approved/trading-ready/
actionable authority states appear, and fixture AST/import/call/literal
guardrails exclude broker/account/order/fill/allocation/portfolio mutation
behavior, file I/O, persistence, network/socket access, vendor APIs,
credentials, runtime/scheduler/dashboard behavior, notebooks, ML, LLM/agent
behavior, recommendations, ranking/scoring, approvals/readiness/trading
authority language outside explicit non-claims, and new dependencies. No
source files, research return mechanics, research return observation fixtures,
research return brief item behavior, research return brief section behavior,
advisory package, package synthetic builder, package CLI, content bundle,
renderer/export, SMA mechanics, SMA brief renderer/export, or existing CLI
behavior changed. Normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 216 - Research Return Observation Brief Container adds
`algotrader.research.research_return_observation_brief_container` as a frozen,
slotted, metadata-only advisory top-level grouping for exact Phase 214
`ResearchReturnObservationBriefSection` objects. The builder accepts a brief
id, title, summary, and one or more exact sections, preserves section object
identity and order, rejects empty collections, duplicate section identities,
malformed lookalikes, and subclasses, and pins
`brief_type="research_return_observation_brief"`, `status="candidate_only"`,
`authority="advisory_only"`, and `capital_authority=False`.

The Phase 216 brief carries section limitations and non-claims forward with
first-seen de-duplication while rejecting authority/actionability wording
outside explicit non-claims. Serialization is deterministic primitive-only
metadata with fixed brief fields, section count, nested `section.to_dict()`
payloads, list-form tuple fields, and no `from_dict()`. Tests build from the
Phase 215 synthetic section fixture, prove source section `.to_dict()` output
is unchanged before and after construction and serialization, pin compact JSON
byte determinism, verify frozen/slotted behavior, confirm public payload keys
avoid action/trading fields, and enforce AST/import/call/literal guardrails
against file I/O, network/socket access, vendor APIs, broker/runtime/
scheduler/dashboard behavior, persistence, credentials, notebooks, ML,
LLM/agent behavior, recommendations, ranking/scoring, approvals/readiness,
allocation/order/portfolio mutation, capital authority, trading authority,
new dependencies, and production imports from tests. Research return
mechanics, observation fixtures, brief item behavior, brief item fixtures,
brief section behavior, brief section fixtures, advisory package, package
synthetic builder, package CLI, content bundle, renderer/export, SMA
mechanics, SMA brief renderer/export, and existing CLI behavior remain
unchanged. Normal pytest remains offline, credential-free, deterministic, and
safe.

Phase 217 - Synthetic Research Return Observation Brief Container Fixture adds
`tests/fixtures/research_return_observation_brief_container.py` and
`tests/unit/test_research_return_observation_brief_container_fixture.py` as a
deterministic synthetic fixture layer for the Phase 216 advisory brief
container. The fixture builds exactly one Phase 215 synthetic section, preserves
that section's identity and order through the production builder, and emits the
fixed advisory metadata
`brief_id="research-return-observation-brief:synthetic:broad-etf-return-construction"`,
`title="Synthetic broad ETF return observation brief"`,
`brief_type="research_return_observation_brief"`, `status="candidate_only"`,
`authority="advisory_only"`, and `capital_authority=False`.

The Phase 217 expected-dict helper mirrors `.to_dict()` exactly with fresh
primitive mutable copies, deterministic compact JSON bytes, one nested section
payload matching the Phase 215 expected section dict, nested positive,
negative, and zero return-count metadata, the insufficient-history state, and
carried-forward limitations and non-claims. Tests confirm there is no
`from_dict()`, no positive approval/readiness/actionability/trading authority
state, and fixture-module AST/import/call/literal guardrails against broker,
account, order, fill, allocation, portfolio mutation, file I/O, network/socket
access, vendor APIs, credentials, runtime/scheduler/dashboard behavior,
notebooks, ML, LLM/agent behavior, recommendations, ranking/scoring,
approvals, or trading authority. No src files, research return mechanics,
observation fixtures, brief item behavior or fixtures, brief section behavior
or fixtures, container behavior, advisory/package/CLI/content/render/export
paths, SMA paths, or existing CLI behavior changed. Normal pytest remains
offline, credential-free, deterministic, and safe.

Phase 218 - Research Return Observation Brief Text Renderer adds
`algotrader.research.research_return_observation_brief_renderer` with
`render_research_return_observation_brief_text(brief)` as a deterministic
plain-text view over the Phase 216/217 synthetic advisory brief. The renderer
accepts only exact `ResearchReturnObservationBrief` instances, rejects
subclasses, dictionaries, malformed lookalikes, and `None`, and renders solely
from `brief.to_dict()` without touching source objects.

The Phase 218 text output pins top-level brief metadata, section metadata,
item metadata, positive/negative/zero return-count metadata, nested
close-to-close synthetic source observation mechanics, each nested return
point in source order, deterministic empty-return wording for
`insufficient_return_history`, and item/section/brief limitations and
non-claims. Tests pin the rendered text exactly, prove repeated byte-for-byte
determinism, verify source `.to_dict()` output and nested section/item/source
observation/return-point identities remain unchanged, and enforce
AST/import/call/literal guardrails. The renderer imports no tests or fixtures,
adds no `from_dict()`, and does not add real data ingestion, vendor/broker/
runtime behavior, file I/O, persistence, network/socket access, credentials,
scheduler/dashboard behavior, notebooks, ML, LLM/agent behavior, scoring,
ranking, recommendations, approval/readiness claims, trading authority,
capital authority beyond the existing false metadata field, or new
dependencies. Research return mechanics, observation fixtures, brief item/
section/container behavior and fixtures, advisory/package/CLI/content bundle
paths, existing renderer/export paths, SMA paths, and existing CLI behavior
remain unchanged. Normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 219 - Research Return Observation Brief Export Contract adds
`algotrader.research.research_return_observation_brief_export` with frozen,
slotted `ResearchReturnObservationBriefExport` and
`export_research_return_observation_brief(brief)` as a deterministic
in-memory export view over the Phase 216/217/218 research return observation
brief. The builder accepts only exact `ResearchReturnObservationBrief`
instances, rejects subclasses, dictionaries, malformed lookalikes, and `None`,
sets `payload` from `brief.to_dict()`, sets `json_text` with compact
deterministic JSON (`sort_keys=True`, `separators=(",", ":")`), and sets
`rendered_text` from the Phase 218 renderer.

The Phase 219 export validates direct construction, requiring a non-empty
primitive payload dictionary, non-empty compact JSON text that round-trips to
the payload, and non-empty rendered text. Payload access returns fresh
primitive copies, the export remains frozen/slotted, and no `from_dict()` is
added. Tests prove repeated byte-for-byte determinism, unchanged source
`.to_dict()` output, stable section/item/source observation/return-point
identities, exact fixture equality, renderer equality, and production imports
with no tests or fixtures. AST/import/call/literal guardrails confirm the
export adds no file I/O, persistence, network/socket access, vendor APIs,
credentials, broker/runtime/scheduler/dashboard behavior, notebooks, ML,
LLM/agent behavior, recommendations, ranking/scoring, approval/readiness
claims, source/data approval, methodology approval, adjusted-close completeness
claims, signal/evaluator behavior, allocation/order/portfolio mutation,
capital authority beyond existing false metadata, trading authority, new
dependencies, real data ingestion, or CLI behavior. Research return mechanics,
observation fixtures, brief item/section/container behavior and fixtures,
renderer behavior, advisory/package/CLI/content bundle paths, SMA paths, and
existing CLI behavior remain unchanged. Normal pytest remains offline,
credential-free, deterministic, and safe.

Phase 220 - Advisory Operating Brief Content Bundle Research Return
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
and carries limitations/non-claims forward with first-seen de-dupe.

The Phase 220 `to_dict()` output adds `research_return_observation_brief_count`
and `research_return_observation_briefs` only when that optional branch is
populated, preserving existing no-risk, risk-inclusive, research-queue-
inclusive, and SMA-inclusive fixture payloads byte-for-byte. The new fixture
helper composes candidate research, strategy eligibility, risk authority,
research queue, SMA research observation, and research return observation
branches through the production bundle builder, exposing the synthetic
close-to-close return-construction observation payload for later operating
brief rendering/export/CLI phases. Tests pin the nested research return
observation payload, including `returns_constructed`,
`insufficient_return_history`, positive/negative/zero return counts,
`close_to_close_simple_return`, `synthetic_close`, ignored future sample count,
and return points. No `from_dict()` is added. Renderer/export/CLI/package
paths, package synthetic builder paths, research return mechanics and
renderer/export paths, SMA mechanics and renderer/export paths, and existing
CLI behavior remain unchanged. Normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 221 - Advisory Operating Brief Content Bundle Renderer Research Return
Observation Branch extends
`algotrader.research.advisory_operating_brief_content_bundle_renderer` to
conditionally render Phase 220 `research_return_observation_briefs` from
`bundle.to_dict()` only. The renderer keeps the existing branch order of
candidate research, strategy eligibility, risk authority, research queue, SMA
research observation, research return observation, then aggregate limitations
and non-claims.

The Phase 221 research return branch renders deterministic brief, section, and
item metadata; positive, negative, and zero return-count metadata; nested
close-to-close synthetic source observation mechanics; return points in source
order; deterministic insufficient-history empty-return wording; and item,
section, and brief limitations and non-claims. Tests preserve Phase 162,
Phase 178, Phase 184/185, and Phase 205/206 no-return-branch renderer output,
pin the SMA-inclusive renderer bytes by length and SHA-256, prove repeated
research-return-inclusive rendering is byte-for-byte deterministic, and verify
source bundle `.to_dict()` payloads and nested objects are unchanged before
and after rendering.

Phase 221 adds no content bundle contract, export, CLI, package, synthetic
builder, research return mechanics, research return renderer/export, SMA
mechanics, SMA renderer/export, or existing CLI behavior changes. It adds no
real data ingestion, vendor data, broker/runtime behavior, file I/O,
persistence, network/socket access, credentials, scheduler/dashboard behavior,
notebooks, ML, LLM/agent behavior, scoring, ranking, recommendations,
approval/readiness claims, allocation/order/portfolio mutation, capital
authority beyond existing false metadata, trading authority, new dependencies,
or `from_dict()`. Normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 222 - Advisory Operating Brief Content Bundle Export Research Return
Observation Regression Guard adds a test-only regression file for the existing
`export_advisory_operating_brief_content_bundle(...)` path over the Phase
220/221 research-return-inclusive synthetic content bundle. The guard uses the
existing research-return-inclusive bundle builder and expected dictionary,
asserts the export payload equals that dictionary, pins compact deterministic
JSON with `sort_keys=True` and `separators=(",", ":")`, proves JSON
round-trips, and requires rendered text to match
`render_advisory_operating_brief_content_bundle_text(bundle)`.

The Phase 222 guard proves repeated exports are byte-for-byte deterministic;
candidate, strategy, risk, research queue, SMA, and research return branches
are all present; `research_return_observation_brief_count` and
`research_return_observation_briefs` are preserved; nested research return
brief, section, item, source observation, and return point metadata remain
present; return mechanics include `returns_constructed`,
`insufficient_return_history`, positive/negative/zero return counts,
`close_to_close_simple_return`, `synthetic_close`, ignored future sample count,
ordered return points, and deterministic empty-return representation; branch
sequence remains candidate, strategy, risk, research queue, SMA, research
return, limitations, and non-claims; limitations/non-claims are preserved; and
mutating the exported payload does not mutate the source bundle or later
exports. The guard also self-checks imports, calls, and source terms so the
test remains isolated from broker/account/order/fill/allocation/portfolio
mutation behavior, file I/O, network/socket, vendor APIs, credentials,
runtime/scheduler/dashboard paths, notebooks, ML, LLM/agent behavior,
recommendation/ranking/scoring/approval/readiness/trading authority behavior,
and `from_dict()`.

Phase 222 changes no source files and adds no content bundle, renderer, export,
CLI, package, package synthetic builder, package CLI, research return
mechanics, research return brief renderer/export, SMA mechanics, SMA brief
renderer/export, or existing CLI behavior changes. Existing no-risk,
risk-inclusive, research-queue-inclusive, and SMA-inclusive export regressions
remain the compatibility baseline. Normal pytest remains offline,
credential-free, deterministic, and safe.

Phase 223 - Advisory Operating Brief Content Bundle CLI Research Return
Observation Preview adds the hidden synthetic-only
`--include-research-return-observation` flag to
`algotrader advisory-operating-brief-content-bundle-preview`. The default
preview, `--format text|json`, risk-inclusive, research-queue-inclusive,
SMA-inclusive, and existing risk+research-queue+SMA outputs remain unchanged;
the new flag composes candidate research, strategy eligibility, and research
return observation branches, and combines with existing flags only when those
branches are explicitly requested.

The Phase 223 preview builds the research return branch through public
production builders only, using deterministic synthetic close samples. Text
still comes from `export_advisory_operating_brief_content_bundle(...).rendered_text`,
and JSON still comes from `.json_text` with compact deterministic ordering.
Tests cover JSON round-tripping, byte-for-byte repeated CLI determinism,
all-flags branch presence, `returns_constructed`,
`insufficient_return_history`, positive/negative/zero return counts,
`close_to_close_simple_return`, `synthetic_close`, ignored future sample count,
ordered return points, and deterministic insufficient-history empty-return
wording. Production CLI modules continue to import no tests or fixtures and
add no file/path/source/vendor/broker/network/runtime/credential options,
real data ingestion, persistence, network/socket access, credentials,
scheduler/dashboard behavior, notebooks, ML, LLM/agent behavior,
approval/readiness claims, recommendations, allocation/order/portfolio
mutation, risk approval, paper/live readiness, capital authority beyond
existing false metadata, trading authority, new dependencies, runtime
timestamps, or `from_dict()`.

Phase 224 - Advisory Operating Brief Package Synthetic Research Return Branch
Alignment updates the canonical synthetic package preview to build its nested
content bundle from the existing research-return-inclusive production helper.
The package now carries candidate research, strategy eligibility, risk
authority, research queue, SMA research observation, and research return
observation branches in the stored content bundle payload, nested content
bundle export payload, compact JSON, and rendered text.

The Phase 224 package keeps the fixed package metadata
`advisory-operating-brief-package:synthetic:2026-01-20`, title, advisory-only
summary, `as_of`, `candidate_only` status, `advisory_only` authority, and
`capital_authority=False`. The fixture continues to delegate to the
production-safe synthetic package builder. Package fixture, export, renderer,
CLI, and CLI regression tests pin byte-for-byte deterministic text and JSON
parity against the updated package export. The content bundle preview remains
unchanged and the package preview still exposes only `--format text|json`.
No package contract, renderer/export/CLI production code, content bundle
contract, research return mechanics, SMA mechanics, new input options, file or
environment behavior, network/socket access, credentials, scheduler/dashboard
behavior, notebooks, ML, LLM/agent behavior, approval/readiness claims,
recommendations, allocation/order/portfolio mutation, risk approval,
paper/live readiness, additional capital or trading authority, dependencies,
runtime timestamps, or `from_dict()` are added.

Phase 225 - Research Return Summary Observation Mechanics adds
`algotrader.research.research_return_summary_observation` as a tiny frozen,
slotted, deterministic descriptive summary over exact Phase 210
`ResearchReturnSeriesObservation` objects. The builder preserves source
observation object identity, accepts no subclasses or malformed lookalikes, and
sets fixed metadata `observation_type="research_return_summary_observation"`,
`status="candidate_only"`, `authority="advisory_only"`, and
`capital_authority=False`.

The Phase 225 summary records source symbol, `as_of`, return method, price
basis, source return count, positive/negative/zero return counts, and
Decimal-only min/max/mean simple return values when source returns exist. A
source observation with returns receives `summary_state="returns_summarized"`;
an empty source return history receives
`summary_state="insufficient_return_history"` and `None` min/max/mean values.
`to_dict()` emits deterministic primitive-only output, serializes Decimals as
strings and `None` as JSON null, nests `source_observation.to_dict()`, converts
tuples to lists, preserves the source observation, carries limitations and
non-claims forward with first-seen de-dupe, and adds no `from_dict()`.

Phase 225 changes no research return construction mechanics, research return
brief item/section/container/renderer/export paths, advisory package paths,
package synthetic builder, package CLI, content bundle, renderer/export/CLI,
SMA mechanics, SMA brief renderer/export, or existing CLI behavior. It adds no
real data ingestion, vendor data, broker/runtime behavior, file I/O,
persistence, network/socket access, credentials, scheduler/dashboard behavior,
notebooks, ML, LLM/agent behavior, source/data approval, adjusted-close
approval, corporate-action completeness claims, methodology approval,
signal/evaluator behavior, strategy execution, backtesting behavior,
ranking/scoring, recommendations, allocation/order/portfolio mutation, risk
approval, paper/live readiness, capital authority beyond fixed false metadata,
trading authority, runtime timestamps, new dependencies, or trading behavior.
Normal pytest remains offline, credential-free, deterministic, and safe.

Phase 226-230 - Research Return Summary Observation Advisory Integration adds a
bounded synthetic advisory branch for the Phase 225
`ResearchReturnSummaryObservation`. It introduces deterministic fixture helpers
for constructed-return and insufficient-history summaries, exact expected
primitive dictionaries matching `.to_dict()`, and a frozen/slotted
`ResearchReturnSummaryObservationBrief` with in-memory render/export helpers.
The brief preserves exact summary observation identities, carries limitations
and non-claims forward with first-seen de-dupe, emits compact deterministic
JSON, nests each source observation payload, and adds no deserialization path.

The Phase 226-230 branch is wired into the existing advisory content bundle only
as an optional additive branch after the existing research return observation
branch. The renderer/export/hidden CLI/package preview paths render and export
the summary branch when explicitly included by synthetic preview helpers. The
branch remains metadata-only, advisory-only, synthetic-fixture-only,
offline-safe, deterministic, non-actionable, and non-authoritative; it adds no
real market data, file I/O, network/socket/API access, credentials, broker,
execution, portfolio, runtime, scheduler, dashboard, persistence, ML, LLM,
agent, signal, evaluator, strategy approval, ranking/scoring, recommendation,
allocation/order authority, paper/live readiness, capital authority beyond fixed
false metadata, or trading authority.

Phase 231-236 - Tiny Synthetic SMA Mechanics Seed adds a tests-only regression
seed over the existing Phase 195 synthetic SMA research observation mechanics.
Because `SmaResearchObservation`, `SmaResearchPricePoint`, and
`build_sma_research_observation` already provide the deterministic SMA
observation object, this phase does not add a duplicate contract or production
module. The seed pins a four-row synthetic close-price series, exact Decimal
SMA arithmetic, explicit `as_of` filtering that ignores later samples,
deterministic insufficient-history non-formation, repeated compact JSON
stability, primitive-only `.to_dict()` payloads, source price-point non-mutation,
and absence of action/trading authority payload fields.

Phase 231-236 changes no SMA production mechanics, fixtures, advisory package
paths, renderer/export/CLI behavior, research return mechanics, real data
ingestion, vendor/public data handling, file I/O, network/socket/API access,
credentials, broker/execution/portfolio/runtime/scheduler/dashboard behavior,
ML, LLM/agent behavior, signal/evaluator/backtesting behavior, strategy
approval, validation/recommendation/ranking/scoring/readiness claims,
allocation/order authority, paper/live eligibility, capital authority beyond
fixed false metadata, trading authority, dependencies, or deserialization paths.
Normal pytest remains offline, credential-free, deterministic, and safe.

Phase 237 - SMA Research Summary Observation Mechanics adds
`algotrader.research.sma_research_summary_observation` as a tiny frozen,
slotted, deterministic, advisory-only summary over exact existing
`SmaResearchObservation` objects. The builder accepts only tuple/list inputs
containing exact `SmaResearchObservation` instances, rejects subclasses,
lookalikes, dictionaries, raw price points, and non-observations, preserves
source observation object identity and input ordering, and pins
`observation_type="sma_research_summary_observation"`, `status="candidate_only"`,
`authority="advisory_only"`, `research_scope="research_only"`, and
`capital_authority=False`.

The Phase 237 summary records only primitive descriptive counts: total source
observations, above-SMA, below-SMA, equal-SMA, and insufficient-history counts.
Non-empty inputs use `summary_state="observations_summarized"`; empty inputs use
`summary_state="empty_insufficient_observations"` with zero counts and explicit
advisory limitations/non-claims. `to_dict()` emits deterministic primitive-only
metadata, nests source observation `.to_dict()` payloads, converts tuples to
fresh lists, and adds no `from_dict()`.

Phase 237 changes no SMA observation construction mechanics, SMA brief
renderer/export paths, advisory package paths, content bundle behavior, CLI
behavior, research return mechanics, evaluator behavior, signal behavior,
portfolio state, trading behavior, real data ingestion, vendor/public data
handling, file/path/source/vendor/broker/network/runtime/credential options,
persistence, network/socket/API access, credentials, scheduler/dashboard
behavior, ML, LLM/agent behavior, profitability or predictive-validity claims,
recommendations, ranking/scoring, allocation/order/fill authority,
paper/live eligibility, readiness or approval flags, capital authority beyond
fixed false metadata, trading authority, dependencies, runtime timestamps, or
deserialization paths. Normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 238 - Advisory Content Bundle SMA Summary Observation Preview wires the
Phase 237 `SmaResearchSummaryObservation` into the synthetic advisory operating
brief content bundle preview path behind hidden
`--include-sma-research-summary-observation`. The preview builder constructs the
summary from the same synthetic SMA observations used by the existing SMA
observation preview branch, carries it through content bundle export and text
rendering as advisory metadata only, and omits the branch unless the hidden
synthetic-only flag is explicitly supplied.

Phase 238 preserves all default advisory operating brief content bundle preview
bytes and leaves the package preview unchanged. The added SMA summary branch
remains `candidate_only`, `advisory_only`, `research_only`, and
`capital_authority=False`; it adds no strategy validation, signal, evaluator,
recommendation, ranking/scoring, readiness state, allocation/order/fill
authority, paper/live eligibility, trading authority, broker/runtime/vendor
option, real data input, persistence, network/socket/API access, scheduler,
dashboard, ML, LLM/agent behavior, dependency, runtime timestamp, or
deserialization path.

Phase 239 - Advisory Package SMA Summary Alignment promotes the Phase 238 SMA
summary branch into the canonical synthetic advisory operating brief package
path. The package synthetic builder requests the content-bundle
`SmaResearchSummaryObservation`, carries the exact advisory-only summary object
into the rebuilt package content bundle, and keeps package export, renderer,
fixture, and CLI preview output deterministic.

Phase 239 is metadata-only. The promoted branch remains `candidate_only`,
`advisory_only`, `research_only`, and `capital_authority=False`, with the
summary counts rendered and exported alongside the existing SMA observation,
research return, and research return summary branches. It adds no strategy
approval, validation/readiness, recommendation, ranking/scoring, signal or
evaluator behavior, allocation/order/fill authority, broker/runtime/vendor
option, real data input, persistence, network/socket/API access, scheduler,
dashboard, ML, LLM/agent behavior, dependency, runtime timestamp, paper/live
eligibility, capital authority beyond fixed false metadata, trading authority,
or deserialization path.

Phase 240 - Research-Only SMA Return Alignment Mechanics adds
`algotrader.research.sma_return_alignment_observation` with frozen/slotted
`SmaReturnAlignmentPeriod` and `SmaReturnAlignmentObservation` contracts plus a
pure `build_sma_return_alignment_observation(...)` builder. The artifact joins
existing `SmaResearchObservation` state to existing
`ResearchReturnSeriesObservation` periods by selecting the latest SMA
observation whose `as_of` is on or before each return `start_date`.
Unavailable prior SMA state is represented explicitly, source observation
identity is preserved, duplicate SMA `as_of` inputs are rejected, and the
payload remains primitive-only and deterministic.

Phase 240 is research metadata only. It does not compute strategy returns,
exposure-adjusted returns, equity curves, benchmarks, costs, orders, positions,
allocations, portfolio state, readiness, approvals, recommendations, signals,
evaluator behavior, broker/runtime/vendor behavior, persistence, network/API
access, scheduler/dashboard behavior, ML/LLM behavior, capital authority, or
trading authority.

Phase 241 - SMA Return Alignment Summary Observation adds
`algotrader.research.sma_return_alignment_summary_observation` with a
frozen/slotted `SmaReturnAlignmentSummaryObservation` contract plus a pure
`build_sma_return_alignment_summary_observation(...)` builder. The artifact
summarizes an existing Phase 240 `SmaReturnAlignmentObservation` by preserving
the source object and counting total alignment periods, aligned return periods,
periods with no prior SMA state, aligned periods using insufficient-history
SMA observations, and aligned periods whose SMA state is above, below, or
equal. It also derives a deterministic alignment summary state for full,
partial, none, or empty return-period alignment.

Phase 241 remains advisory research metadata only. It does not compute
strategy returns, exposure-adjusted returns, equity curves, cash behavior,
benchmarks, costs, orders, positions, allocations, portfolio state, readiness,
approvals, recommendations, signals, evaluator behavior,
broker/runtime/vendor behavior, persistence, network/API access,
scheduler/dashboard behavior, ML/LLM behavior, capital authority, or trading
authority.

Phase 242 - Research-Only SMA Conditional Return Selection Observation adds
`algotrader.research.sma_conditional_return_selection_observation` with
frozen/slotted `SmaConditionalReturnSelectionPeriod` and
`SmaConditionalReturnSelectionObservation` contracts plus a pure
`build_sma_conditional_return_selection_observation(...)` builder. The
artifact consumes an existing Phase 240 `SmaReturnAlignmentObservation`,
preserves the source alignment object and period identities, and classifies
each aligned return period as `included` only when the aligned SMA state is
`above`; below, equal, insufficient-history, and no-prior-SMA cases are
classified as `excluded` with deterministic reasons and counts.

Phase 242 remains advisory research metadata only. It does not compute
strategy returns, compounded returns, equity curves, cash returns, benchmark
comparisons, portfolio state, exposure, positions, orders, allocation,
readiness, approvals, recommendations, signals, evaluator behavior,
broker/runtime/vendor behavior, persistence, network/API access,
scheduler/dashboard behavior, ML/LLM behavior, capital authority, or trading
authority. Verification: `python -m pytest` -> 4685 passed, 4 skipped.

Phase 243 - SMA Conditional Return Selection Summary Observation adds
`algotrader.research.sma_conditional_return_selection_summary_observation`
with a frozen/slotted `SmaConditionalReturnSelectionSummaryObservation`
contract plus a pure
`build_sma_conditional_return_selection_summary_observation(...)` builder. The
artifact consumes an existing Phase 242
`SmaConditionalReturnSelectionObservation`, preserves the source selection
object, counts selection periods, included periods, excluded periods, and the
deterministic excluded-reason buckets for no-prior-SMA, insufficient-history,
below-SMA, and equal-SMA classifications. It also derives a fixed summary
state for mixed, all-included, all-excluded, or empty classification sets.

Phase 243 remains advisory research metadata only. It does not calculate
returns, profit, equity curves, positions, orders, portfolio state, capital
authority, trading authority, approvals, recommendations, signals, evaluator
behavior, broker/runtime/vendor behavior, persistence, network/API access,
scheduler/dashboard behavior, ML/LLM behavior, or deserialization behavior.
Verification: `python -m pytest` -> 4698 passed, 4 skipped.

Phase 244 - SMA Selected Source Return Series Observation adds
`algotrader.research.sma_selected_source_return_series_observation` with
frozen/slotted `SmaSelectedSourceReturnPoint` and
`SmaSelectedSourceReturnSeriesObservation` contracts plus a pure
`build_sma_selected_source_return_series_observation(...)` builder. The
artifact consumes an existing Phase 242
`SmaConditionalReturnSelectionObservation`, preserves the source selection
object and selected period identities, and emits primitive-only source return
values only for selection periods marked `included`. It carries the source
simple return value, return period dates, selection rule, and count metadata
forward without aggregating or compounding the values.

Phase 244 remains advisory research metadata only. It does not calculate
strategy returns, compounded returns, equity curves, cash returns, benchmark
comparisons, portfolio state, exposure, positions, orders, allocation,
readiness, approvals, recommendations, signals, evaluator behavior,
broker/runtime/vendor behavior, persistence, network/API access,
scheduler/dashboard behavior, ML/LLM behavior, capital authority, trading
authority, or deserialization behavior. Verification: `python -m pytest` ->
4712 passed, 4 skipped.

Phase 245 - SMA Selected Source Return Summary Observation adds
`algotrader.research.sma_selected_source_return_summary_observation` with a
frozen/slotted `SmaSelectedSourceReturnSummaryObservation` contract and pure
`build_sma_selected_source_return_summary_observation(...)` builder. The
artifact consumes the Phase 244 `SmaSelectedSourceReturnSeriesObservation`,
preserves the source selected source return series object, and emits
primitive-only selected source return count, minimum selected source return,
maximum selected source return, and arithmetic mean selected source return
metadata. Empty selected source return inputs deterministically report no
selected source returns and `None` for the selected source return minimum,
maximum, and arithmetic mean fields.

Phase 245 remains advisory research metadata only. It summarizes selected
source return values without compounding them or converting them into any
strategy, portfolio, invested, backtest, cash, benchmark, exposure, position,
order, allocation, readiness, approval, recommendation, signal, evaluator,
broker/runtime/vendor, persistence, network/API, scheduler/dashboard, ML/LLM,
capital authority, trading authority, or deserialization behavior.
Verification: `python -m pytest` -> 4724 passed, 4 skipped.

Phase 246 - SMA Return Research Pipeline Observation adds
`algotrader.research.sma_return_research_pipeline_observation` with a
frozen/slotted `SmaReturnResearchPipelineObservation` contract and pure
`build_sma_return_research_pipeline_observation(...)` builder. The artifact
accepts the existing Phase 240 alignment observation, Phase 241 alignment
summary, Phase 242 above-SMA selection observation, Phase 243 selection
summary, Phase 244 selected source return series, and Phase 245 selected
source return summary. It validates that those six objects share the same
identity-preserved derivation chain, emits primitive-only top-level
source-count and summary-state metadata, and nests each source artifact in a
stable pipeline order.

Phase 246 remains advisory research metadata only. It composes existing SMA
return research artifacts without adding return math, strategy-return
calculation, selected source return compounding, backtest behavior, equity
curves, cash returns, benchmark comparisons, portfolio state, exposure,
positions, orders, allocation, readiness, approval, recommendation, signal,
evaluator behavior, broker/runtime/vendor behavior, persistence, network/API
access, scheduler/dashboard behavior, ML/LLM behavior, capital authority,
trading authority, or deserialization behavior. Verification:
`python -m pytest` -> 4737 passed, 4 skipped.

Phase 247 - Research Return Construction Policy Contract adds
`algotrader.research.research_return_construction_policy` with a frozen/slotted
`ResearchReturnConstructionPolicy` contract plus a pure
`build_research_return_construction_policy()` builder. The contract pins the
conservative research-only treatment before any future return-construction code:
selected periods may carry source return observations only, excluded periods
remain excluded without zero/cash/strategy mapping, missing periods are not
imputed, no cash proxy exists, costs and slippage are not included, compounding
is not allowed, and strategy-return, portfolio-return, cash-return,
equity-curve, and backtest outputs are all disallowed.

Phase 247 is policy metadata only. It does not accept source observations, apply
the policy, calculate strategy returns, calculate portfolio returns, calculate
cash returns, calculate equity curves, compound selected source returns, map
excluded periods to cash or zero, create a benchmark comparison, create a
backtest result, touch portfolio state, create exposure, create positions or
orders, add allocation/readiness/approval/recommendation/signal/evaluator
behavior, add broker/runtime/vendor behavior, add persistence, add network/API
access, add scheduler/dashboard behavior, add ML/LLM behavior, add capital
authority, add trading authority, or add deserialization behavior. Verification:
`python -m pytest` -> 4747 passed, 4 skipped.

Phase 248 - Research Return Construction Policy Observation Mechanics adds
`algotrader.research.research_return_construction_policy_observation` with a
frozen/slotted `ResearchReturnConstructionPolicyObservation` plus a pure
`build_research_return_construction_policy_observation()` builder. The
observation accepts only the exact Phase 247
`ResearchReturnConstructionPolicy` type, preserves source policy identity,
records deterministic zero audit counts for selected periods, excluded periods,
source return observations, and forbidden outputs, and nests the source
policy's existing primitive `to_dict()` payload unchanged.

Phase 248 is advisory audit metadata only. It does not accept period inputs,
construct returns, calculate strategy/portfolio/cash returns, calculate equity
curves, compound returns, map excluded periods to cash or zero, create a
benchmark comparison, create a backtest result, touch portfolio state, create
exposure, create positions or orders, add allocation/readiness/approval/
recommendation/signal/evaluator behavior, add broker/runtime/vendor behavior,
add persistence, add network/API access, add scheduler/dashboard behavior, add
ML/LLM behavior, add capital authority, add trading authority, or add
deserialization behavior. Verification: `python -m pytest` -> 4761 passed,
4 skipped.

Phase 249 - SMA Return Research Pipeline Construction Policy Observation
Attachment extends the existing
`algotrader.research.sma_return_research_pipeline_observation` payload with a
`return_construction_policy_observation` child. The pipeline builder constructs
the Phase 247 `ResearchReturnConstructionPolicy` first, then constructs the
Phase 248 `ResearchReturnConstructionPolicyObservation` from that exact policy
object, preserving the pipeline -> policy observation -> source policy identity
chain and nesting the policy observation's primitive `to_dict()` payload
unchanged.

Phase 249 remains advisory metadata only. It does not change the Phase 247 or
Phase 248 contracts, does not expose CLI/package behavior, and does not add
broker/runtime/vendor behavior, real data input, persistence, network/API
access, scheduler/dashboard behavior, ML/LLM behavior, evaluator/signal/trading
behavior, portfolio/cash/equity/PnL state, allocation/order/fill behavior,
benchmark comparison, backtest output, approval/readiness authority, timestamps,
randomness, global state, hidden I/O, capital authority, trading authority, or
deserialization behavior. Verification: `python -m pytest` -> 4762 passed,
4 skipped.

Phase 250 - Advisory Package SMA Return Pipeline Serialization Alignment pins
the canonical synthetic advisory package/export fixture path to the Phase 249
`SmaReturnResearchPipelineObservation` payload. The package payload now carries
the existing SMA return research pipeline dictionary unchanged, including the
nested Phase 248 `return_construction_policy_observation` generated from the
same Phase 247 policy object, while content-bundle branch ordering and package
CLI flags remain unchanged.

Phase 250 is serialization alignment only. It adds no new advisory conclusion,
ranking, readiness/approval state, trading behavior, broker/runtime/vendor
dependency, real data input, persistence, network/API access, scheduler/
dashboard behavior, ML/LLM behavior, portfolio/cash/equity/PnL state,
allocation/order/fill behavior, benchmark comparison, backtest output,
timestamps, randomness, global state, hidden I/O, capital authority, trading
authority, or deserialization behavior.

Phase 251 - Advisory Package CLI SMA Pipeline Serialization Regression Guard
adds a focused CLI/export test pin for the existing synthetic advisory package
JSON path. The guard proves the
`advisory-operating-brief-package-preview` command with `--format json`
preserves the Phase 250
`sma_return_research_pipeline_observation` payload byte-deterministically,
including exactly one nested `return_construction_policy_observation` matching
the canonical package/export fixture policy observation.

Phase 251 is a regression guard only. It adds no new CLI flags, commands,
renderer branches, package behavior, advisory conclusions, ranking,
readiness/approval state, trading behavior, broker/runtime/vendor dependency,
real data input, persistence, network/API access, scheduler/dashboard behavior,
ML/LLM behavior, portfolio/cash/equity/PnL state, allocation/order/fill
behavior, benchmark comparison, backtest output, timestamps, randomness, global
state, hidden I/O, capital authority, trading authority, or deserialization
behavior.

Phase 252 - SMA Return Research Pipeline Observation Export Snapshot adds
`algotrader.research.sma_return_research_pipeline_observation_export` with
`export_synthetic_sma_return_research_pipeline_observation_snapshot()`. The
helper constructs the existing deterministic synthetic SMA return research
pipeline through production research builders and returns the pipeline
observation's primitive `to_dict()` payload unchanged, including exactly one
nested `return_construction_policy_observation`.

Phase 252 is an export snapshot convenience only. It adds no CLI/package
behavior, renderer branch, evaluator/signal/trading behavior,
portfolio/cash/equity/PnL state, allocation/order/fill behavior, benchmark
comparison, backtest output, approval/readiness authority, broker/runtime/vendor
dependency, real data input, persistence, network/API access,
scheduler/dashboard behavior, ML/LLM behavior, timestamps, randomness, global
state, hidden I/O, capital authority, trading authority, or deserialization
behavior.

Phase 253 - SMA Return Pipeline Export Snapshot Fixture Regression adds a
focused test fixture for the Phase 252 standalone export snapshot. The fixture
pins the expected primitive dictionary and compact sorted-key JSON for
`export_synthetic_sma_return_research_pipeline_observation_snapshot()` by
reusing the canonical synthetic `SmaReturnResearchPipelineObservation.to_dict()`
payload, including exactly one nested `return_construction_policy_observation`.

Phase 253 is test/fixture regression coverage only. It changes no production
source and adds no CLI/package behavior, renderer branch, evaluator/signal/
trading behavior, portfolio/cash/equity/PnL state, allocation/order/fill
behavior, benchmark comparison, backtest output, approval/readiness authority,
broker/runtime/vendor dependency, real data input, persistence, network/API
access, scheduler/dashboard behavior, ML/LLM behavior, timestamps, randomness,
global state, hidden I/O, capital authority, trading authority, or
deserialization behavior.

Phase 254 - SMA Return Pipeline Export Snapshot Import Guard adds a focused
file-based AST/source regression guard for the standalone SMA return research
pipeline export snapshot and its expected fixture. The guard pins the export
source to deterministic research contracts/builders, pins the fixture to the
expected fixture helper, rejects forbidden CLI/package/broker/runtime/vendor/
network/file/path/env/credential/trading imports or tokens, and keeps the
export signature zero-argument while preserving the Phase 253 expected payload.

Phase 254 is test/guard coverage only. It changes no production source and adds
no CLI commands, CLI flags, package behavior, renderer branch, evaluator/signal/
trading behavior, portfolio/cash/equity/PnL state, allocation/order/fill
behavior, benchmark comparison, backtest output, approval/readiness authority,
broker/runtime/vendor dependency, real data input, persistence, network/API
access, scheduler/dashboard behavior, ML/LLM/agent behavior, timestamps,
randomness, global state, hidden I/O, capital authority, trading authority, or
deserialization behavior.

Phase 255 - Research Observation Manifest Contract adds
`algotrader.research.research_observation_manifest`, a generic in-memory
metadata manifest for primitive research observation payload dictionaries. The
builder preserves input ordering, rejects malformed or duplicate named payloads,
counts top-level payload keys, and hashes each payload with compact sorted-key
JSON SHA-256 while keeping `to_dict()` primitive-only and deterministic.

Phase 255 adds no file paths, persistence, CLI/package/renderer behavior,
evaluator/signal/trading behavior, portfolio/cash/equity/PnL state,
allocation/order/fill behavior, benchmark comparison, backtest output,
approval/readiness authority, broker/runtime/vendor dependency, real data input,
network/API access, scheduler/dashboard behavior, ML/LLM/agent behavior,
timestamps, randomness, global state, hidden I/O, capital authority, trading
authority, or deserialization behavior. The manifest remains generic and does
not import the SMA export snapshot module.

Phase 256 - SMA Export Snapshot Manifest Fixture Integration adds a test-only
fixture that represents the Phase 253 SMA return research pipeline export
snapshot with the generic Phase 255 research observation manifest contract. The
fixture builds a one-entry metadata manifest for the canonical synthetic
payload, pins the stable observation name, payload key count, compact sorted-key
JSON SHA-256 digest, primitive `to_dict()` shape, and deterministic compact
JSON serialization.

Phase 256 changes no production source and adds no CLI/package/renderer
behavior, evaluator/signal/trading behavior, portfolio/cash/equity/PnL state,
allocation/order/fill behavior, benchmark comparison, backtest output,
approval/readiness authority, broker/runtime/vendor dependency, real data
input, persistence, network/API access, scheduler/dashboard behavior,
ML/LLM/agent behavior, timestamps, randomness, global state, hidden I/O,
capital authority, trading authority, or deserialization behavior. The
production manifest remains generic and does not import SMA export modules.

Phase 257 - Research Observation Manifest Import Guard adds a focused
test-only AST/source guard for the Phase 255 manifest, Phase 256 fixture, and
SMA manifest integration test. The guard pins manifest imports to generic
deterministic dependencies, pins the fixture to the generic manifest contract
and Phase 253 expected payload fixture, rejects SMA production/export coupling
from the production manifest, and checks that the guarded files add no
CLI/package/renderer/storage/file-I/O/runtime/broker/vendor surface.

Phase 257 changes no production source and adds no CLI commands, CLI flags,
package behavior, renderer behavior, storage behavior, evaluator/signal/
trading behavior, portfolio/cash/equity/PnL state, allocation/order/fill
behavior, benchmark comparison, backtest output, approval/readiness authority,
broker/runtime/vendor dependency, real data input, persistence, network/API
access, scheduler/dashboard behavior, ML/LLM/agent behavior, timestamps,
randomness, global state, hidden I/O, capital authority, trading authority, or
deserialization behavior.

Phase 258 - Research Observation Manifest Export Snapshot adds
`algotrader.research.research_observation_manifest_export`, a generic
in-memory helper that accepts the Phase 255 manifest entry shape, builds the
generic manifest, and returns `to_dict()` unchanged for deterministic review.
The helper adds no new semantics beyond existing payload metadata and digest
behavior, preserves builder-defined ordering, and remains independent of SMA
production/export modules.

Phase 258 adds no CLI/package/renderer/storage behavior, file I/O,
evaluator/signal/trading behavior, portfolio/cash/equity/PnL state,
allocation/order/fill behavior, benchmark comparison, backtest output,
approval/readiness authority, broker/runtime/vendor dependency, real data
input, persistence, network/API access, scheduler/dashboard behavior,
ML/LLM/agent behavior, timestamps, randomness, global state, hidden I/O,
capital authority, trading authority, or deserialization behavior.

Phase 259 - Research Observation Manifest Export Import Guard adds a focused
test-only AST/source guard for `research_observation_manifest_export`. The guard
pins imports to `__future__`, `collections.abc`, and the generic manifest
builder, rejects SMA/package/CLI/renderer/runtime/broker/portfolio/vendor/
network/storage/ML/LLM/trading dependencies and file/path/env/config/network
helper surfaces, and verifies the helper returns
`build_research_observation_manifest(entries).to_dict()` unchanged with compact
sorted-key JSON determinism.

Phase 259 changes no production source and adds no CLI/package/renderer/storage
behavior, file I/O, evaluator/signal/trading behavior,
portfolio/cash/equity/PnL state, allocation/order/fill behavior, benchmark
comparison, backtest output, approval/readiness authority,
broker/runtime/vendor dependency, real data input, persistence, network/API
access, scheduler/dashboard behavior, ML/LLM/agent behavior, timestamps,
randomness, global state, hidden I/O, capital authority, trading authority, or
deserialization behavior.

Phase 260 - Advisory Package Research Observation Manifest Attachment extends
the advisory operating brief package with an optional exact
`ResearchObservationManifest` audit field. The field is metadata-only, preserves
manifest object identity, is omitted from `to_dict()` when absent, and serializes
the primitive manifest payload when present. The synthetic advisory package
preview now builds a one-entry manifest named
`sma_return_research_pipeline_observation` from the existing synthetic SMA
return research pipeline observation's primitive `to_dict()` payload, so the
manifest digest tracks the included observation payload deterministically.

Phase 260 adds no CLI flags, renderer behavior, storage behavior, file/path/env
inputs, evaluator/signal/trading behavior, portfolio/cash/equity/PnL state,
allocation/order/fill behavior, benchmark comparison, backtest output,
approval/readiness authority, broker/runtime/vendor dependency, real data input,
persistence, network/API access, scheduler/dashboard behavior, ML/LLM/agent
behavior, timestamps, randomness, global state, hidden I/O, capital authority,
trading authority, or deserialization behavior.

Phase 261 - Advisory Package Research Observation Manifest Dependency Guard adds
`tests.unit.test_advisory_operating_brief_package_manifest_dependency`, a focused
test-only AST/source guard for the Phase 260 package and synthetic preview
manifest attachment. The guard pins the package builder to the generic
`ResearchObservationManifest` contract without manifest snapshot or SMA export
coupling, checks the optional manifest exact-type boundary and optional
serialization, verifies the synthetic preview builds the one-entry manifest from
the included SMA return research pipeline observation payload, and asserts
compact sorted-key JSON determinism.

Phase 261 changes no production source and adds no CLI flags, renderer behavior,
storage behavior, file/path/env/config/network inputs, evaluator/signal/trading
behavior, portfolio/cash/equity/PnL state, allocation/order/fill behavior,
benchmark comparison, backtest output, approval/readiness/recommendation
authority, broker/runtime/vendor dependency, real data input, persistence,
network/API access, scheduler/dashboard behavior, ML/LLM/agent behavior,
timestamps, randomness, global state, hidden I/O, capital authority, trading
authority, or deserialization behavior.

Phase 262 - Advisory Package Manifest CLI Serialization Regression Guard extends
`tests.unit.test_advisory_operating_brief_package_cli_regression` to prove the
existing `advisory-operating-brief-package-preview --format json` path carries
the Phase 260 research observation manifest deterministically. The guard checks
the one-entry manifest metadata, recomputes the compact sorted-key JSON SHA-256
digest for the included SMA return research pipeline observation payload, and
asserts repeated JSON CLI output is byte-for-byte stable.

Phase 262 also guards that the package preview CLI surface remains limited to
the existing `--format text|json` option set and that default/text rendering does
not expose raw manifest internals. It changes no production source and adds no
CLI flags, renderer behavior, storage behavior, file/path/env/config/network
inputs, evaluator/signal/trading behavior, portfolio/cash/equity/PnL state,
allocation/order/fill behavior, benchmark comparison, backtest output,
approval/readiness/recommendation authority, broker/runtime/vendor dependency,
real data input, persistence, network/API access, scheduler/dashboard behavior,
ML/LLM/agent behavior, timestamps, randomness, global state, hidden I/O, capital
authority, trading authority, or deserialization behavior.

Phase 263 - Advisory Package Research Observation Manifest Export Helper adds a
tiny package-level helper,
`export_advisory_operating_brief_package_research_observation_manifest`, that
accepts only exact `AdvisoryOperatingBriefPackage` objects, requires an existing
`research_observation_manifest`, and returns that manifest's primitive
`to_dict()` payload unchanged. The helper does not rebuild the package or
manifest and is guarded with focused deterministic JSON, digest, exact-type, and
dependency-boundary tests.

Phase 263 adds no CLI flags, renderer behavior, package builder behavior,
synthetic builder behavior, storage behavior, file/path/env/config/network
inputs, evaluator/signal/trading behavior, portfolio/cash/equity/PnL state,
allocation/order/fill behavior, benchmark comparison, backtest output,
approval/readiness/recommendation authority, broker/runtime/vendor dependency,
real data input, persistence, network/API access, scheduler/dashboard behavior,
ML/LLM/agent behavior, timestamps, randomness, global state, hidden I/O, capital
authority, trading authority, or deserialization behavior.

Phase 264 - Advisory Package Manifest Export Dependency Guard adds
`tests.unit.test_advisory_operating_brief_package_manifest_export_dependency`,
a focused test-only AST/source guard for the Phase 263 package manifest export
helper. The guard pins the helper to `ValidationError` and exact
`AdvisoryOperatingBriefPackage` imports only, verifies the single-helper public
surface, exact package and manifest validation, unchanged attached-manifest
`to_dict()` export, no manifest builder/export helper calls, no I/O/runtime/
broker/vendor/network/storage/path/config/ML/LLM/agent surfaces, no package or
manifest mutation, and deterministic one-entry synthetic manifest export.

Phase 264 changes no production source and adds no CLI flags, renderer
behavior, package builder behavior, synthetic builder behavior, storage
behavior, file/path/env/config/network inputs, evaluator/signal/trading
behavior, portfolio/cash/equity/PnL state, allocation/order/fill behavior,
benchmark comparison, backtest output, approval/readiness/recommendation
authority, broker/runtime/vendor dependency, real data input, persistence,
network/API access, scheduler/dashboard behavior, ML/LLM/agent behavior,
timestamps, randomness, global state, hidden I/O, capital authority, trading
authority, or deserialization behavior.

Phase 265 - Advisory Package Manifest Export Snapshot Fixture adds
`tests.fixtures.advisory_operating_brief_package_manifest_export` plus
`tests.unit.test_advisory_operating_brief_package_manifest_export_fixture` as a
test-only reusable expected payload for the Phase 263 package manifest export
helper. The fixture builds the existing synthetic package preview, exports the
attached research observation manifest unchanged through the package-level
helper, and exposes both the primitive dict and compact sorted-key JSON. Focused
tests prove one-entry SMA pipeline metadata, SHA-256 digest alignment with the
included synthetic observation payload, deterministic JSON round-tripping, and
bounded fixture imports without production source changes or new CLI/renderer/
broker/runtime/vendor/network/persistence/trading behavior.

Phase 266 - Advisory Package Manifest Export Fixture Dependency Guard adds
`tests.unit.test_advisory_operating_brief_package_manifest_export_fixture_dependency`,
a focused test-only AST/source guard for the Phase 265 snapshot fixture. The
guard pins the fixture imports and `__all__`, verifies the dict helper remains
a thin synthetic-package build plus Phase 263 helper export, verifies the JSON
helper keeps compact sorted-key serialization, rejects direct generic manifest,
SMA, CLI, renderer, runtime, broker, vendor, network, storage, path, config,
ML/LLM/agent, I/O, digest, credential, authority, and trading tokens, and
rechecks deterministic one-entry fixture output without production source
changes.

Phase 267 - Advisory Package Audit Snapshot Export Helper adds
`export_advisory_operating_brief_package_audit_snapshot`, a tiny metadata-only
package audit snapshot helper. It accepts only exact
`AdvisoryOperatingBriefPackage` objects with an attached research observation
manifest, composes the Phase 263 manifest export helper, returns deterministic
package identity metadata, the manifest payload, and compact sorted-key JSON
SHA-256 digests for the package and manifest payloads. Focused tests guard exact
type rejection, primitive JSON round-tripping, byte-stable synthetic output,
no mutation, one-entry SMA pipeline manifest metadata, bounded imports, and no
CLI/renderer/broker/runtime/vendor/network/persistence/data-ingestion/trading
behavior changes.

Phase 268 - Advisory Package Audit Snapshot Export Dependency Guard adds
`tests.unit.test_advisory_operating_brief_package_audit_snapshot_export_dependency`,
a test-only AST/source guard for the Phase 267 audit snapshot helper. It pins
the helper to metadata-only imports, the Phase 263 manifest export helper,
compact sorted-key JSON SHA-256 digests, exact snapshot keys, deterministic
synthetic behavior, and no production source, CLI/renderer/broker/runtime/
vendor/network/persistence/data-ingestion/trading behavior changes.

Phase 269 - Research Data Source Readiness Contract adds
`ResearchDataSourceReadiness` and `build_research_data_source_readiness` as a
small frozen/slotted metadata-only contract for future research data source
candidate review. It pins `contract_type` and schema version, derives missing
controls from required and satisfied controls, validates readiness states,
negative non-claims, duplicate-free controls/scopes/evidence refs, primitive
`to_dict()` output, deterministic compact JSON behavior, and source-level
guardrails against file/path/env/network/vendor/broker/runtime/persistence/
portfolio/order/fill/backtest/ML/LLM/notebook/vectorbt/QuantConnect surfaces.
It adds no real data ingestion, source approval, CLI/renderer/broker/runtime/
vendor/network/persistence/backtest/trading behavior, strategy evaluation, or
capital authority.

Phase 270 - Research Data Source Readiness Dependency Guard adds
`tests.unit.test_research_data_source_readiness_dependency`, a focused test-only
AST/source guard for the Phase 269 contract. It pins imports and public surface,
verifies frozen/slotted dataclass shape, keyword-only builder metadata, fixed
contract metadata, exact readiness states, derived missing controls, duplicate
and unknown-control rejection, required limitations and negative non-claims,
negative-only authority/trading language, primitive deterministic `to_dict()`
output, and no file/path/env/network/vendor/broker/runtime/persistence/
backtest/trading dependency tokens. Phase 270 changes no production source and
adds no real data ingestion, CLI/renderer/broker/runtime/vendor/network/
persistence/backtest/trading behavior, approval authority, or capital
authority.

Phase 271 - Research Data Source Readiness Synthetic Fixture adds
`tests.fixtures.research_data_source_readiness` plus
`tests.unit.test_research_data_source_readiness_fixture` as a reusable
metadata-only candidate readiness payload for the Phase 269 contract. The
fixture builds through `build_research_data_source_readiness`, exposes the
object, primitive `to_dict()` output, and compact sorted-key JSON unchanged,
pins derived missing controls, synthetic/internal evidence refs, limitations,
and negative non-claims, and adds no production source, real data ingestion,
CLI/renderer/broker/runtime/vendor/network/persistence/backtest/trading
behavior, approval authority, data-source authorization, or capital authority.

Phase 272 - Research Data Source Readiness Export Snapshot adds test-only
export snapshot helpers to `tests.fixtures.research_data_source_readiness` plus
`tests.unit.test_research_data_source_readiness_export`. The snapshot dict is
exactly the existing primitive `to_dict()` fixture payload, and the JSON helper
serializes that payload with compact sorted keys. Focused tests pin byte-stable
JSON, fresh equal primitive payloads, builder-derived missing controls, and the
absence of wrapper, clock, digest, or raw payload fields. Phase 272 changes no
production source and adds no real data ingestion, CLI/renderer/broker/runtime/
vendor/network/persistence/backtest/trading behavior.

Phase 273 - Advisory Operating Brief Data Source Readiness Branch adds an
optional `ResearchDataSourceReadiness` diagnostic branch to the advisory
operating brief content bundle and synthetic package preview. The branch is
absent from existing bundle outputs unless explicitly supplied by a fixture or
the synthetic package builder, serializes through the existing readiness
`to_dict()` contract, preserves builder-derived `missing_controls`, and renders
required, satisfied, and missing controls as negative/diagnostic metadata.
Focused tests pin compact sorted-key JSON, rendered diagnostic text, byte-stable
repeated output, package inclusion, and absence of broker/order/fill/portfolio/
backtest/runtime/vendor/network/credential fields. Phase 273 adds no real data
ingestion, source/vendor approval, CLI options, runtime, persistence, broker,
backtest, order, portfolio, credential, network, or trading behavior.

Phase 274 - Advisory Content Bundle CLI Data Source Readiness Preview adds a
hidden synthetic-only `--include-research-data-source-readiness` flag to the
advisory operating brief content bundle preview. Default CLI output remains
unchanged; the explicit flag adds the existing readiness diagnostic branch in
text or compact sorted-key JSON, preserves deterministic branch order, and
keeps `missing_controls` computed by `build_research_data_source_readiness`.
Focused tests pin default stability, text/JSON readiness output,
byte-for-byte repeated determinism, visible option-surface restrictions, and
absence of broker/order/fill/portfolio/backtest/runtime/vendor/network/
credential fields. Phase 274 adds no real data ingestion, source selection,
vendor access, approval semantics, runtime, persistence, broker, network,
backtest, or trading behavior.

Phase 275 - Advisory Package CLI Data Source Readiness Regression adds focused
package-preview regression coverage for the existing synthetic research data
source readiness diagnostic branch. Tests pin that the package synthetic path,
package CLI text output, and compact sorted-key JSON output all carry the
branch deterministically; that the text output includes the required,
satisfied, and missing diagnostic controls; that JSON preserves
builder-computed `missing_controls`; that repeated package CLI text and JSON
output are byte-for-byte stable; and that the package preview exposes no new
input-bearing options beyond existing `--format text|json`. Phase 275 changes
no production source and adds no real data ingestion, source/vendor selection,
approval semantics, runtime, persistence, broker, network, backtest, or trading
behavior.

Phase 276 - Research Data Source Readiness Advisory Integration Dependency
Guard adds focused test-only dependency coverage for the content bundle
readiness branch, renderer diagnostic wording, package synthetic readiness
inclusion, and hidden content-bundle CLI preview flag. The guards pin
metadata-only imports, synthetic-only readiness inclusion where applicable,
hidden
boolean-only non-input CLI handling, diagnostic/negative rendering, and absence
of broker/runtime/vendor/network/persistence/backtest/trading calls or tokens.
Phase 276 changes no production source and adds no real data ingestion, source
selection, source/vendor approval, runtime, persistence, broker, network,
backtest, or trading behavior.

Phase 277 - Research Data Source Readiness Summary Observation adds a tiny
metadata-only `ResearchDataSourceReadinessSummary` contract over an exact
`ResearchDataSourceReadiness` object. The summary preserves source object
identity, mirrors the existing readiness state into `summary_state`, counts
required, satisfied, and builder-computed missing controls from the source
object only, and emits sorted diagnostic limitations as primitive deterministic
metadata without serializing a nested source payload. Focused tests pin exact
type rejection for subclasses and lookalikes, frozen/slotted immutability,
primitive `to_dict()` output, deterministic repeated builds with distinct
source identities, and dependency/import/call/token guardrails. Phase 277 adds
no real data ingestion, source selection, source/vendor approval, runtime,
persistence, broker, network, backtest, or trading behavior.

Phase 278 - Research Data Source Readiness Summary Fixture and Export Snapshot
adds synthetic fixture helpers and focused export snapshot coverage for the
Phase 277 summary contract. The fixture helpers build through the production
summary builder supplied by the caller, use the existing synthetic
`ResearchDataSourceReadiness` fixture, preserve source object identity when a
source fixture is supplied, and export primitive snapshot dicts equal to
`summary.to_dict()`. Focused tests pin compact sorted-key JSON, byte-stable
repeated output, summary state, required/satisfied/missing control counts,
diagnostic limitations, fresh primitive payload copies, and absence of source
wrappers, raw payloads, clocks, digests, approval fields, broker/order/fill/
portfolio/backtest/runtime fields, or trading behavior. Phase 278 changes no
production source and adds no real data ingestion, source selection,
source/vendor approval, runtime, persistence, broker, network, backtest, or
trading behavior.

Phase 279 - Advisory Content Bundle Data Source Readiness Summary Branch adds
an optional metadata-only `ResearchDataSourceReadinessSummary` branch to the
advisory operating brief content bundle. The branch is absent by default,
accepts exact summary objects only, serializes each summary through
`summary.to_dict()`, renders compact diagnostic counts and limitations, and is
included by the synthetic advisory package builder beside the existing
readiness diagnostic branch. Existing default bundle/package behavior remains
unchanged except for the explicit synthetic package summary inclusion. Focused
tests pin absent-by-default behavior, exact type rejection for subclasses and
lookalikes, renderer wording, compact sorted-key JSON determinism,
byte-for-byte repeated text/JSON output, deterministic package branch order,
and absence of broker/order/fill/portfolio/backtest/runtime/vendor/network/
credential fields. Phase 279 adds no real data ingestion, source selection,
source/vendor approval, runtime, persistence, broker, network, backtest, or
trading behavior.

Phase 280 - Advisory Content Bundle CLI Data Source Readiness Summary Preview
adds a hidden synthetic-only
`--include-research-data-source-readiness-summary` flag to the advisory
operating brief content bundle preview. Defaults remain byte-stable; the
explicit flag renders or exports only the compact
`ResearchDataSourceReadinessSummary` diagnostic branch with summary state,
required/satisfied/missing control counts, and diagnostic limitations. Focused
tests pin text and compact sorted-key JSON output, repeated byte-for-byte
determinism, hidden boolean-only non-input handling, visible option-surface
restrictions, deterministic branch order when paired with the existing
readiness diagnostic branch, and absence of broker/order/fill/portfolio/
backtest/runtime/vendor/network/credential fields. Phase 280 changes only the
synthetic content-bundle preview CLI path and adds no real data ingestion,
source selection, source/vendor approval, runtime, persistence, broker,
network, backtest, or trading behavior.

Phase 281 - Advisory Package CLI Data Source Readiness Summary Regression adds
test-only package-preview regression coverage for the existing synthetic
`ResearchDataSourceReadinessSummary` diagnostic branch. The coverage pins that
package synthetic output includes the summary branch, package CLI text includes
summary state, required/satisfied/missing control counts, and diagnostic
limitations, package CLI JSON preserves the deterministic summary count and
compact summary payload, and repeated package CLI text and JSON output remain
byte-for-byte deterministic. The package preview continues to expose only the
existing `--format text|json` option surface, and existing content bundle
preview behavior remains unchanged. Phase 281 changes no production source and
adds no real data ingestion, source selection, source/vendor approval, runtime,
persistence, broker, network, backtest, or trading behavior.

Phase 282 - Advisory Readiness Summary Integration Dependency Guard adds
test-only dependency/source guard coverage for the
`ResearchDataSourceReadinessSummary` integration paths. The focused guards pin
metadata-only content bundle summary inclusion, diagnostic-only renderer
wording, synthetic package summary inclusion, hidden boolean-only CLI preview
handling, exact primitive summary payload shape, and source/AST checks against
broker/runtime/vendor/network/persistence/backtest/trading calls, fields, and
positive approval vocabulary. Phase 282 changes no production source and adds
no real data ingestion, source selection, source/vendor approval, runtime,
persistence, broker, network, backtest, or trading behavior.

Phase 283 - Advisory Operating Brief Diagnostic Issue List adds a tiny
metadata-only issue-record builder for advisory operating brief content
bundles. The builder returns a deterministic tuple of frozen/slotted
`AdvisoryOperatingBriefDiagnosticIssue` records derived only from existing
research data source readiness and readiness summary diagnostic branches. Each
record carries plain primitive metadata: source branch, issue code, issue
state, diagnostic message, blocking controls, and limitations. Focused tests
pin paired synthetic readiness/readiness-summary inputs, missing controls as
diagnostic controls rather than approvals, deterministic branch ordering,
frozen/slotted immutability, primitive-only `to_dict()` output, repeated-build
equality, and absence of broker/order/fill/portfolio/backtest/runtime/vendor/
network/credential fields or approval/trading vocabulary. Phase 283 adds no
real data ingestion, source selection, source/vendor approval, runtime,
persistence, broker, network, backtest, or trading behavior.

Phase 284 - Advisory Diagnostic Issue Fixture and Export Snapshot adds
test-only synthetic fixture helpers plus export snapshot coverage for advisory
operating brief diagnostic issues. The fixture composes the existing synthetic
advisory content bundle with readiness/readiness-summary diagnostics, builds
records through the production diagnostic issue builder, and exposes only the
issue `to_dict()` payload list plus compact sorted-key JSON. Focused tests pin
snapshot equality with issue payloads, deterministic branch ordering, expected
source branch/issue code/state/message/blocking controls/limitations, repeated
fixture equality, fresh primitive payload copies, and absence of raw data,
timestamps, digest fields, wrapper fields, approval fields, or broker/order/
fill/portfolio/backtest/runtime/vendor/network behavior. Phase 284 changes no
production source and adds no real data ingestion, source selection,
source/vendor approval, runtime, persistence, broker, network, backtest, or
trading behavior.

Phase 285 - Advisory Content Bundle Diagnostic Issues Branch adds an optional
metadata-only `diagnostic_issues` branch to advisory operating brief content
bundles. The branch is absent from payloads unless explicitly supplied, accepts
only exact `AdvisoryOperatingBriefDiagnosticIssue` records, preserves supplied
issue order, and serializes each issue through `issue.to_dict()`. The content
bundle renderer emits only diagnostic issue metadata: source branch, issue
code, issue state, diagnostic message, blocking controls, and limitations. The
content bundle export keeps compact sorted-key JSON determinism, and the
synthetic advisory package preview explicitly opts in by deriving the existing
diagnostic issues from the package readiness diagnostics before export.
Focused tests pin default absence, exact type rejection for subclasses and
lookalikes, deterministic text and JSON bytes, synthetic package inclusion, and
absence of new execution, vendor, network, persistence, backtest, or trading
behavior.

Phase 286 - Advisory Content Bundle CLI Diagnostic Issues Preview adds a
hidden synthetic-only `--include-diagnostic-issues` flag to the advisory
operating brief content bundle preview. The default content bundle preview
remains byte-for-byte unchanged, while the explicit flag derives the existing
deterministic diagnostic issue records from the synthetic readiness diagnostics
and exposes only the `diagnostic_issues` branch, preserving supplied issue
order and compact sorted-key JSON determinism. Focused CLI regression tests pin
text and JSON issue fields, repeated byte-for-byte determinism, hidden
boolean-only non-input handling, visible option-surface restrictions, and
absence of broker/order/fill/portfolio/backtest/runtime/vendor/network/
credential fields or ranking/scoring/recommendation/approval vocabulary in the
diagnostic issue branch. This phase changes only synthetic preview CLI plumbing
and adds no real data ingestion, source selection, source/vendor approval,
runtime, persistence, broker, network, backtest, or trading behavior.

Phase 287 - Advisory Package CLI Diagnostic Issues Regression adds test-only
package-preview coverage proving the existing synthetic `diagnostic_issues`
branch is carried through the canonical advisory package path. The regression
pins package synthetic inclusion, package CLI text output for source branch,
issue code, issue state, diagnostic message, blocking controls, and
limitations, compact sorted-key JSON output, nested content-bundle export
payload inclusion, repeated byte-for-byte text/JSON determinism, no new
package input-bearing options beyond existing `--format text|json`, and no
broker/order/fill/portfolio/backtest/runtime/vendor/network/credential fields
or ranking/scoring/recommendation/approval vocabulary in the diagnostic issue
branch. Phase 287 changes no production source and adds no real data
ingestion, source selection, source/vendor approval, runtime, persistence,
broker, network, backtest, or trading behavior.

Phase 288 - Advisory Diagnostic Issues Integration Dependency Guard adds
focused test-only dependency/source guard coverage for the diagnostic issue
content bundle, renderer, synthetic package builder, CLI preview, and package
export integrations. The guards pin the diagnostic issue branch as
metadata-only and diagnostic-only, preserve deterministic issue ordering,
verify hidden boolean-only CLI preview handling, and assert export payloads add
no wrappers, timestamps, digests, authority fields, broker fields, or trading
vocabulary in the diagnostic issue branch. Phase 288 changes no production
source and adds no real data ingestion, source selection, source/vendor
approval, runtime, persistence, broker, network, backtest, or trading behavior.

Phase 289 - Advisory Operating Brief Section Records adds an unexported
metadata-only section layer in
`src/algotrader/research/advisory_operating_brief_section.py` for existing
advisory operating brief content bundles. The builder requires an exact
`AdvisoryOperatingBriefContentBundle`, rejects subclasses/lookalikes, emits
frozen/slotted `AdvisoryOperatingBriefSection` records only for present bundle
branches in fixed branch order, and records only section key/title/state,
source branch key, item count, diagnostic messages for diagnostic issues, and
section-layer limitations. The layer is not wired into package exports, CLI,
renderers, package preview, data paths, or runtime behavior. Focused tests pin
synthetic bundle construction, deterministic ordering, primitive-only
`to_dict()` copies, repeated-build equality, source-bundle non-mutation,
exact-type rejection, frozen/slotted immutability, dependency/source guards,
and absence of broker/order/fill/portfolio/backtest/runtime/vendor/network/
credential fields or ranking/scoring/recommendation/approval/trading
vocabulary. Phase 289 adds no real data ingestion, source selection,
source/vendor approval, runtime, persistence, broker, network, backtest, or
trading behavior.

Phase 290 - Advisory Section Fixture and Export Snapshot adds test-only
synthetic fixture helpers for `AdvisoryOperatingBriefSection` records. The
fixture composes the existing synthetic advisory content bundle and diagnostic
issue fixtures, then builds section records only through
`build_advisory_operating_brief_sections()`. Export snapshot helpers return
exactly each section `to_dict()` payload and compact sorted-key JSON, preserving
present-branches-only behavior, deterministic section ordering, diagnostic
messages, and section limitations without wrapper fields, timestamps, digests,
or raw branch payloads. Focused tests pin repeated-build equality, byte-for-byte
JSON determinism, primitive fresh-copy payloads, fixture dependency bounds, and
absence of broker/order/fill/portfolio/backtest/runtime/vendor/network/
credential fields or ranking/scoring/recommendation/approval/trading
vocabulary. Phase 290 changes no production source and adds no real data
ingestion, source selection, source/vendor approval, runtime, persistence,
broker, network, backtest, or trading behavior.

Phase 291 - Advisory Content Bundle Sections Branch adds an explicit optional
`advisory_sections` branch to advisory operating brief content bundles. The
branch is absent unless supplied, accepts only exact
`AdvisoryOperatingBriefSection` records, preserves supplied ordering, does not
make an otherwise empty bundle valid, serializes sections through
`section.to_dict()`, and contributes only section limitations to aggregate
bundle limitations. The renderer emits metadata only in an `Advisory Sections`
block after diagnostic issues and before aggregate limitations, and synthetic
package preview construction now derives sections from the diagnostic-inclusive
content bundle before explicitly including them in the final synthetic package
bundle. Phase 291 adds no content-bundle CLI surface, real data ingestion,
source selection, source/vendor approval, runtime, persistence, broker,
network, backtest, or trading behavior.

Phase 292 - Advisory Content Bundle CLI Sections Preview adds a hidden
synthetic-only `--include-advisory-sections` boolean flag to
`advisory-operating-brief-content-bundle-preview`. The default content bundle
preview remains byte-for-byte unchanged; when the flag is supplied, the CLI
builds deterministic advisory section records from the existing synthetic
diagnostic section source and attaches only the `advisory_sections` branch to
the preview bundle. Text and compact sorted-key JSON output preserve section
ordering exactly as built, exposing section key/title/state, source branches,
item count, diagnostic messages, and section limitations without file/path/
source/vendor/broker/network/credential CLI inputs. Focused regression tests
pin hidden boolean-only handling, text/JSON determinism, compact JSON output,
default-output stability, forbidden-field scans, and absence of ranking,
scoring, recommendation, or approval vocabulary in the advisory sections
branch. Phase 292 adds no real data ingestion, source selection, source/vendor
approval, runtime, persistence, broker, network, backtest, or trading behavior.

Phase 293 - Advisory Package CLI Sections Regression adds test-only package
preview coverage proving the existing synthetic `advisory_sections` branch is
carried through the canonical advisory package path. The regression pins text
output for section key, title, state, source branches, item count, diagnostic
messages, and metadata-only limitations; compact sorted-key JSON output;
nested content-bundle export payload inclusion; repeated byte-for-byte text and
JSON determinism; unchanged package input-bearing options; and absence of
broker/order/fill/portfolio/backtest/runtime/vendor/network/credential fields
or ranking/scoring/recommendation/approval vocabulary in the section branch.
Phase 293 changes no production source and adds no real data ingestion, source
selection, source/vendor approval, runtime, persistence, broker, network,
backtest, or trading behavior.

Phase 294 - Advisory Sections Integration Dependency Guard adds focused
test-only source and payload guard coverage for the `advisory_sections`
integration path across content bundle serialization, renderer wording,
synthetic package construction, hidden content-bundle CLI preview handling, and
package export payload shape. The guards pin metadata-only renderer fields,
hidden boolean-only CLI wiring, deterministic synthetic package section order,
compact JSON stability, and absence of wrapper/timestamp/digest/authority/
broker/order/fill/portfolio/runtime/vendor/network/credential fields or
ranking/scoring/recommendation/approval/trading vocabulary. Phase 294 changes
no production source and adds no real data ingestion, source selection,
source/vendor approval, runtime, persistence, broker, network, backtest, or
trading behavior.

Phase 295 - Advisory Operating Brief View Records adds
`src/algotrader/research/advisory_operating_brief_view.py`, a tiny
metadata-only advisory view model over existing
`AdvisoryOperatingBriefSection` records. The builder accepts either one exact
section record or a tuple of exact section records, rejects subclasses and
lookalikes, preserves supplied section order, and emits frozen/slotted
`AdvisoryOperatingBriefView` records with only view key/title/state, section
count, section keys, metadata summary lines, diagnostic messages, and
limitations. `to_dict()` returns fresh primitive-only deterministic payloads
without wrapper/timestamp/digest/raw-payload fields. Focused unit coverage pins
synthetic section fixture composition, exact-type validation, immutability,
source-section non-mutation, repeated-build equality, diagnostic-only wording,
and absence of broker/order/fill/portfolio/backtest/runtime/vendor/network/
credential fields or ranking/scoring/recommendation/approval/trading
vocabulary. Phase 295 adds no renderer, CLI, package, dashboard, scheduler,
runtime, persistence, broker, vendor, network, backtest, or trading behavior.

Phase 296 - Advisory View Fixture and Export Snapshot adds test-only synthetic
fixture helpers for `AdvisoryOperatingBriefView`. The fixture uses the
existing synthetic advisory section fixtures and builds only through
`build_advisory_operating_brief_view()`. Snapshot helpers return exactly
`view.to_dict()` plus compact sorted-key JSON, preserving supplied section
ordering and present-sections-only behavior. Focused tests pin view key, title,
state, section count, section keys, summary lines, diagnostic messages,
limitations, repeated-build equality, fresh primitive copies, fixture
dependency bounds, and absence of raw data, timestamps, digests, wrappers,
source payloads, broker/order/fill/portfolio/backtest/runtime fields, or
actionable trading vocabulary. Phase 296 changes no production source and adds
no package, CLI, renderer, dashboard, scheduler, runtime, persistence, broker,
vendor, network, backtest, or trading behavior.

Phase 297 - Advisory Content Bundle View Branch adds an optional
`advisory_view` branch to advisory operating brief content bundles. The branch
is absent by default, accepts only an exact `AdvisoryOperatingBriefView`, and
serializes through `view.to_dict()` without wrapper/timestamp/digest/raw
payload fields. The content-bundle renderer emits only view key, title, state,
section count, section keys, summary lines, diagnostic messages, and
limitations; compact sorted-key JSON remains deterministic. The synthetic
package preview explicitly includes the advisory view built from its existing
synthetic advisory sections, while content-bundle CLI behavior remains
unchanged. Focused tests pin default absence, exact-type rejection for
subclasses/lookalikes/non-view objects, text and JSON byte determinism, package
preview inclusion, metadata-only payload shape, and absence of broker/order/
fill/portfolio/backtest/runtime/vendor/network/credential fields or ranking/
scoring/recommendation/approval vocabulary. Phase 297 adds no real data
ingestion, source selection, source/vendor approval, runtime, persistence,
broker, network, backtest, or trading behavior.

Phase 300 - Synthetic Research MVP Operating Brief adds
`advisory-operating-brief-mvp-preview` as a deterministic local CLI command
that composes the existing synthetic advisory package, content bundle, section
view, diagnostic issues, data-source readiness records, and SMA/return research
observation surfaces into one human-readable terminal report. The report shows
the advisory view summary, present sections, diagnostic blockers, readiness
control gaps, synthetic research observations, and explicit blocked/missing
items before any real strategy, backtest, or trading use. Focused tests pin CLI
registration, text readability, compact JSON consistency, byte-for-byte
determinism, compatibility with existing preview commands, no file/environment/
network access, and no broker/credential/live/vendor runtime behavior. Phase
300 adds no real data ingestion, persistence, scheduler, dashboard, broker,
orders, fills, portfolio/reconciliation mutation, ranking, scoring,
recommendation, approval, backtest execution, or trading authority.

Phase 301 / Milestone 301 - Synthetic Operating Brief Work Queue extends the
MVP preview with a deterministic `Work Queue / Next Non-Trading Work Items`
section and matching JSON records derived from the existing synthetic package,
diagnostic, readiness, research observation, blocked, and missing surfaces.
Each item records a label, reason, state, and protected boundary for data-source
gaps, source/universe/benchmark/cash controls, real data approval gaps,
no-lookahead implementation, deterministic backtest readiness,
validation/reproduction evidence, diagnostic blockers, advisory-only research
observations, and absent trading authority. Phase 301 adds no real data
ingestion, persistence, scheduler, dashboard, broker, orders, fills,
portfolio/reconciliation mutation, ranking, scoring, recommendation, approval,
backtest execution, or trading authority.

Phase 302 / Milestone 302 - Synthetic Backtest Readiness Gate extends the MVP
preview with a deterministic `Backtest Readiness Gate` section and compact JSON
`backtest_readiness_gate` records. The gate reports real strategy backtesting as
blocked/not ready and enumerates project-control records for real data source
approval, source/universe/benchmark/cash policy, no-lookahead protocol, return
construction, validation/reproduction evidence, strategy approval, and trading
authority. Phase 302 is reporting-only and adds no real data ingestion,
persistence, scheduler, dashboard, broker, orders, fills, portfolio/
reconciliation mutation, ranking, scoring, recommendation, approval, actual
backtest execution, or trading authority.

Phase 303 / Milestone 303 - Synthetic Strategy Candidate Dossier Report extends
the MVP preview with a deterministic `Strategy Candidate Dossier` section and
compact JSON `strategy_candidate_dossiers` records for the synthetic broad ETF
SMA trend-following pipeline-validation candidate. The dossier is
synthetic-only and advisory-only; it records research purpose, synthetic
observation state, missing evidence and controls, blocked/not-ready backtest
state, not-approved strategy state, no trading authority, and the next
non-trading control step without adding real data ingestion, persistence,
scheduler, dashboard, broker, orders, fills, portfolio/reconciliation mutation,
ranking, scoring, recommendation, approval, actual backtest execution, or
trading authority.

Phase 309 / Milestone 309 - Logged Paper Lab Revalidation Brief adds
`paper-lab-revalidation-brief` as a deterministic local read-only CLI command
for summarizing an existing paper-lab snapshot JSONL run log. The brief reports
run ids, selected/latest run event counts, account cash/currency availability,
position count and symbols, recent order count and safe order-status fields,
missing observations, unavailable/error events with secret-safe details,
redaction markers, advisory labels, `profit_claim = none`, and one of
`usable_for_manual_review`, `insufficient_observation`,
`observation_unavailable`, or `invalid_run_log`. It is local-file-only and
adds no real equity, crypto, or options order submission, broker write path,
live profile behavior, credentials, network access, scheduler, autonomous loop,
market-data ingestion, portfolio/reconciliation mutation, ranking, scoring,
recommendation, trading authority, or trading hot-path LLM behavior.

Phase 311 / Milestone 311 - Crypto Paper Submit Gate Enablement opens only the
tiny BTCUSD crypto paper-lab submit harness through the existing
`paper-order-probe` path. The enabled crypto lane remains paper-profile-only,
buy-only, market-only, `time_in_force=gtc`, notional-only, capped by
`notional <= max_notional` and `max_notional <= 5.00`, and requires both
`--submit` and `--i-mean-it`; live profile and live URL remain rejected. The
SPY equity paper submit contract is preserved and the SPY paper probe still
waits for market hours, options submit remains disabled, and crypto paper
observations are a shared broker-path harness only, not evidence of equity
behavior. This milestone runs fake-only deterministic tests and does not run a
real broker submit; normal pytest remains offline, credential-free,
deterministic, and safe.

Phase 313 / Milestone 313 - Crypto Paper Submit Adapter Diagnostic records the
M312 BTCUSD tiny probe as failed safe: read-only snapshots observed `2000 USD`
cash, zero positions, zero recent orders, no broker receipt, and an
`observation_unavailable` revalidation state after two failed submit sequences.
The M312 run log is contaminated for future probes and must not be reused for
another submit. The hotfix keeps crypto as a broker-path harness only, preserves
the SPY equity path and disabled options submit, improves fake-backed sanitized
adapter/SDK submit-boundary diagnostics, and fixes crypto notional quantity
gate wording without adding network, credential, scheduler, autonomous trading,
research-layer submission, or broker retry behavior. No confirmed broker-side
crypto order exists from M312; no retry should occur until this hotfix is
complete and a fresh run id/log is used.

Phase 315 / Milestone 315 - BTCUSD Crypto Paper Submit APIError Diagnostic
inspects the M314 loaded-env BTCUSD run log without reusing it for another
submit. The log shows one guarded submit attempt, no broker response, and a
pre-response SDK `APIError` surfaced through the Alpaca adapter after the
paper profile, cash/position/order observations, and submit gates passed. The
SDK wrapper now preserves sanitized pre-response diagnostics for APIError-like
failures: submit stage, exception class, HTTP status code when exposed, Alpaca
error code when exposed, URL/token-redacted message text, and the request
shape summary (`asset_class`, `symbol`, `side`, `order_type`,
`time_in_force`, `sizing_mode`). The CLI and paper-lab JSONL failure rows carry
those fields while preserving `broker_response_received = false`,
`broker_response_parsed = false`, and unknown submitted/accepted/filled state.
This milestone adds only fake-backed deterministic tests and documentation; it
does not place another BTCUSD order, use a live profile or live URL, add
network access to normal pytest, weaken paper gates, add retries, or introduce
autonomous submit behavior.

Phase 317 / Milestone 317 - Crypto Minimum Notional Policy Gate turns the M316
BTCUSD paper observation into a deterministic local policy. The M316 fresh log
shows one guarded `BTCUSD` crypto paper submit attempt with `notional=1.00` and
`max_notional=5.00`; all prior local gates passed, then Alpaca returned
`APIError` status `403`, code `40310000`, and the sanitized message `cost basis
must be >= minimal amount of order 10` before any broker receipt. The crypto
paper policy now requires `min_notional=10.00` for `BTCUSD`, reports
`notional_below_crypto_min_notional` when a smaller notional is requested, logs
the gate result and required minimum in JSON/JSONL output, and raises the crypto
paper cap to `max_notional <= 10.00` so a future user-approved paper-only
`BTCUSD` probe has exactly one safe notional path: `notional=10.00` with
`max_notional=10.00`. The milestone preserves paper profile, paper URL, buy-only,
market/GTC, notional-only, `BTCUSD` allowlist, disabled options submit, SPY
equity behavior, no retries, no scheduler, and offline credential-free normal
pytest behavior. No real order is submitted by this local-policy milestone.

Execution-boundary work should remain pure and synthetic unless explicitly
approved otherwise. It should still exclude broker wiring, order submission,
scheduler/runtime behavior, persistence, cash reservation side effects, ML, and
LLM trading-path logic.

Real Alpaca SDK work and Phase 7 reconciliation remain deferred unless
explicitly approved.

## Alpaca Paper Planning Link

See [Alpaca Paper Integration Plan](alpaca_paper_integration_plan.md) for the safe future path toward Alpaca paper integration. That plan is documentation-only and does not add SDK dependencies, credentials, network calls, or runtime broker behavior.
