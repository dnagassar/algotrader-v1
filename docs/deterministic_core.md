# Deterministic Trading Core

This document is the current contract for the deterministic trading core.
It is intentionally compact. Historical milestone detail that used to live in
this file is preserved in
[`docs/archive/deterministic_core_history.md`](archive/deterministic_core_history.md)
and in the project checkpoint ledger.

The near-term goal remains a supervised paper-trading lab. The long-term goal
may include supervised live trading, but this repository is not live-authorized.
Live capital remains locked down.

## Current Contract Summary

- The core is deterministic, offline-first, and credential-free by default.
- Normal `python -m pytest` must remain offline, network-free, broker-free,
  credential-free, and deterministic.
- Paper/live broker commands are explicit command surfaces behind profile
  gates, operator intent flags, and milestone-specific approval.
- No live trading is authorized.
- No agent or LLM may autonomously submit, cancel, replace, close, liquidate,
  or otherwise mutate broker/account/order state.
- LLMs and agents are not allowed in the trading hot path.
- The current active strategy path is SPY daily long-only ETF SMA 50/200.
- M376 remains treated as an open/nonterminal SPY paper close order until a
  read-only reconciliation artifact says terminal.

## Non-Negotiable Safety Rails

- Live trading is forbidden.
- Live broker credentials must not be loaded by default test or docs work.
- Paper broker credentials must not be loaded unless a milestone explicitly
  scopes a paper broker command.
- Credential values must never be printed.
- Broker-facing commands must not run unless the milestone explicitly scopes
  them and all required gates pass.
- Agents may build code, tests, docs, fakes, simulators, local artifacts, and
  reports.
- Agents may not operate the broker, allocate capital, authorize live mode, or
  decide to mutate paper/live broker state.
- No autonomous submit behavior is allowed.
- No autonomous cancel behavior is allowed.
- No autonomous replace behavior is allowed.
- No autonomous close behavior is allowed.
- No autonomous liquidation behavior is allowed.
- No paper/live mode changes may be made without explicit operator approval.
- No live order path may be added or enabled.
- No source change may weaken dependency-direction tests.
- No default test may gain network access.
- No default test may require credentials.
- No default test may contact a broker.
- No LLM may be placed in signal, risk, execution, broker, or runtime trading
  logic.
- Any ambiguous broker response fails closed.
- Any open order evidence blocks overlapping SPY submit intent.
- Any nonterminal M376 evidence keeps SPY submit blocked.

## Default Pytest And Credential Gate

Before full default pytest, stop if any of these are true:

- `APP_PROFILE=paper`
- `ALPACA_API_KEY` is loaded
- `ALPACA_API_SECRET_KEY` is loaded
- `ALPACA_SECRET_KEY` is loaded
- Any other active paper/live broker credential is loaded

When full pytest is run, report booleans only. Do not print credential values.

Default verification must remain:

- offline
- credential-free
- broker-free
- network-free
- deterministic
- safe to run from a normal shell

Network-enabled or broker-facing tests, if any, must remain explicitly gated
outside normal pytest. They are not part of the default current contract.

## Canonical Architecture

The current architecture is:

```text
Market Data
-> Features
-> Screener
-> Signals
-> Risk
-> ExecutionIntent
-> ExecutionPlan
-> PlanningPolicy
-> Paper OMS/Broker Adapter
-> Paper Fills
-> Portfolio/Reconciliation Observation
-> Operating Brief
```

This flow is a contract boundary, not permission to trade.

- Market Data is an explicit input source, preferably local and deterministic
  for default work.
- Features are deterministic transformations over explicit inputs.
- Screener ranks or filters candidates and remains broker-free.
- Signals produce advisory or proposed outputs and do not approve trades.
- Risk produces permission verdicts and still does not execute.
- `ExecutionIntent` is internal, pre-broker, and not a broker order.
- `ExecutionPlan` is immutable, pre-broker, and not executable by itself.
- `PlanningPolicy` makes deterministic pre-broker batch eligibility decisions.
- `CancellationPlan` is immutable, broker-free, and pre-cancellation. It is not
  a broker cancellation request and cannot invoke a broker boundary.
- The deterministic cancellation-planning policy consumes only an explicit
  local order observation and explicit runtime/operator controls. It emits at
  most one same-order plan when identity, freshness, permission, runtime state,
  and cancelable status all agree; otherwise it returns one typed fail-closed
  blocker. It is deliberately not connected to `DurableCancelCoordinator`, a
  broker adapter, or any mutation callback and grants no cancellation authority.
- The pure paper cancellation-planning adapter replays only caller-supplied
  `PaperOrderLifecycleEvent` values, validates explicit as-of ordering and a
  conflict-free order identity, and feeds one latest usable observation into
  that policy. Its immutable primitive artifact always records no-submit,
  no-broker-access, and no-mutation facts. The adapter performs no file or
  journal reads and remains disconnected from `DurableCancelCoordinator`.
- The deterministic cancellation-candidate selector consumes only an explicit
  tuple of local `OrderJournalRecord` values plus explicit symbol, UTC as-of,
  minimum-open-age, reason, and runtime/planning controls. It selects only when
  exactly one sufficiently old cancelable identity exists. Multiple eligible
  records, duplicate broker identity, malformed or future timestamps, unknown
  state, incomplete identity, terminal-only state, and disabled controls each
  return a typed blocker. Selection performs no journal read, broker access,
  mutation callback, ranking, or cancellation.
- The pure durable-cancellation handoff preview consumes only one typed
  cancellation-planning result, its matching local `OrderJournalRecord`, an
  explicit UTC as-of, a record-age bound, and a separate offline handoff
  permission. A prepared artifact binds the plan ID to deterministic
  `DurableCancelIdentity`-compatible primitives, including the originating
  reservation run ID. Plan/record identity, status, and observation time must
  match exactly. The artifact always records `cancel_allowed=false`,
  `execution_authorized=false`, no callback, no coordinator invocation, and no
  journal or broker mutation. The module cannot import `durable_cancel`, a
  broker adapter, network I/O, or the status control.
- The pure paper-cancellation admission contract is the last typed boundary
  before durable execution. It consumes a prepared handoff, explicit UTC
  evaluation time, trading/stop/snapshot facts, and optional immutable
  operator-authorization evidence. Authorization must be affirmative, unexpired,
  paper-mode, cancel-scoped, and exactly bound to source plan, cancel-intent,
  client-order, and broker-order identity. Only exact evidence emits typed
  `DurableCancelIdentity` and `DurableCancelEvidence`; every mismatch returns one
  typed blocker and no durable inputs. The module imports only those two durable
  input types and cannot instantiate a coordinator, accept a callback, acquire a
  lease, reserve an intent, read a journal, perform I/O, or execute cancellation.
- The operator-gated paper-cancellation invocation bridge is the only consumer
  allowed to connect an admitted result to `DurableCancelCoordinator`. Its
  request must re-bind the exact admission ID, carry an explicit UTC occurrence
  time inside the immutable authorization validity window, confirm a fresh
  snapshot, use a bounded fixed-name fencing lease, and set a separately
  default-false invocation permission. Only then may it reserve the durable
  cancel intent, acquire the lease, and pass injected cancel/observation
  callbacks to the coordinator. The coordinator still owns the atomic journal
  claim before callback invocation, ambiguous outcomes remain non-retryable,
  and the bridge releases the lease in `finally`. The bridge imports no broker
  adapter, constructs no broker client, and is not reachable from status or CLI.
- `paper-autopilot-control status` may optionally project one explicitly
  targeted local journal record into that adapter, or use a separately
  default-off flag to select exactly one aged candidate from the local journal.
  Both modes require an explicit UTC as-of and planning-only permission, derive
  freshness plus stop/trading controls from local state, and fail closed on
  missing, duplicate, multiple, ambiguous, or otherwise ineligible records.
  Explicit and automatic target modes cannot be mixed. Status emits only the
  primitive no-submit artifact. A separately default-disabled handoff preview
  may expose the default-denied durable identity inputs after a successful
  plan, but it cannot reserve an intent, acquire a lease, accept a callback,
  instantiate `DurableCancelCoordinator`, construct a broker client, mutate
  journal state, or grant broker cancellation permission. Control output schema
  is `paper_autopilot_control_v7`. A separately default-disabled admission
  preview intentionally supplies no authorization object and therefore can only
  expose the typed `authorization_missing` gate; status and CLI have no path to
  manufacture or load cancellation authorization.
- Paper OMS/Broker Adapter is the first broker boundary and must be explicitly
  gated.
- Direct production submit and cancel call sites are a closed, executable
  inventory. The paper autopilot is the only autonomous mutation caller and
  must atomically persist its final fenced journal claim before invoking the
  injected broker boundary. Older certification and drill entrypoints remain
  separately operator-gated; adding any unclassified mutation call fails the
  default offline invariant suite.
- The operator-only M370/M435 tiny SPY entry paths and M376 quantity-based SPY
  close path are legacy submits migrated onto the shared durable contract. Each
  dedicated local journal must acquire a
  fenced lease, reserve the immutable request identity, and persist the final
  pre-mutation claim before its single broker call. Broker exceptions become
  durable unknown state, and crash reruns cannot resubmit.
- `DurableSubmitCoordinator` is the shared final-submit hot-path contract used
  by paper autopilot, M370, M376, and M435. Callers provide typed immutable
  identity, fenced lease evidence, explicit canonical-risk and
  snapshot-freshness booleans, an
  injected submit callback, and a broker-observation mapper. The coordinator
  alone owns the atomic claim/callback/observation sequence; failed predicates
  leave the callback untouched, and callback or observation ambiguity is
  persisted as durable unknown state.
- `DurableCancelCoordinator` is an offline-proven cancel contract. Schema-v4
  cancel intents and events are separate from order-submit state; the
  coordinator requires a unique broker-order target, fenced lease, explicit
  cancel permission, and a fresh snapshot before its injected callback.
  Callback or observation ambiguity becomes durable unknown state and cannot
  be retried after restart. Its production consumers are limited by executable
  allowlist to the exactly authorized v5.8 BTCUSD paper submit/cancel
  certification, the v4.12C bounded crypto paper-mutation drill, and the v1.89
  paper-mutation OMS cancellation/restart-recovery boundary. All three
  initialize dedicated local journals before submit and remain behind their
  existing operator, paper-only, same-order, and reconciliation gates; the OMS
  additionally retains its process lock. The OMS fake-only rehearsal may
  exercise the same contract while keeping paper authorization and every
  real-broker activity flag false. The coordinator adds no authority and has
  only been exercised in these migrations with offline fakes. The executable
  allowlist now covers all four known dynamic production cancellation
  dispatchers, each still separately operator-gated; it authorizes no new
  caller and no autonomous cancellation.
- Paper fills are simulated or broker-observed paper records only.
- Portfolio/Reconciliation Observation is reporting and comparison, not
  autonomous correction.
- Operating Brief output is advisory/operator-facing and not an order request.

## Dependency Direction

Research, signal, advisory, and LLM-assisted layers must not import execution,
broker, SDK, network, or runtime trading dependencies.

The intended dependency direction is:

- data contracts and validation primitives may be shared downward
- screener may feed orchestration-owned signal inputs
- signal evaluation may feed risk evaluation
- risk-approved rows may feed execution-intent construction
- execution intents may feed immutable execution plans
- execution plans may feed planning policies
- planning-policy results may feed a gated paper OMS or broker adapter
- local order observations and explicit controls may feed immutable
  cancellation plans, but plans do not cross a cancellation boundary by
  themselves
- broker observations may feed reconciliation and operator reporting

Forbidden dependency direction includes:

- research importing broker or execution modules
- signal evaluators importing broker, execution, runtime, persistence, ML, or
  LLM trading-path modules
- advisory/brief rendering importing broker SDKs or making network calls
- default tests importing or constructing live/paper broker clients
- offline commands loading runtime paper profile before their offline work

## Trading Object Semantics

`ExecutionIntent`:

- wraps a risk-approved source evaluation by identity
- remains pre-submission
- remains broker-agnostic
- is not a broker order
- is not a request to route or submit
- does not reserve cash
- does not mutate portfolio state

`ExecutionPlan`:

- is immutable
- preserves intent order and identity
- is pre-broker
- does not route orders
- does not submit orders
- does not generate broker mutations
- does not resolve live account state
- does not authorize trading

`PlanningPolicyResult`:

- records accepted and skipped intents
- preserves source-evaluation traceability
- may cap or skip intents deterministically
- remains pre-broker
- does not carry fill, SDK, account, or broker mutation behavior

`RiskEngine` output:

- is a permission verdict only
- does not execute
- does not submit
- does not authorize live trading
- does not override broker gates

## Active Strategy Path

The active supervised paper-lab strategy path is:

- symbol: `SPY`
- asset class: equity ETF
- cadence: daily bars
- direction: long-only
- filter: SMA 50/200 trend
- risk-on: `SMA50 > SMA200`
- risk-off: `SMA50 <= SMA200`
- insufficient history: fewer than 200 usable as-of bars
- allowlist: `SPY` only
- paper sizing: tiny notional experiments only unless the operator explicitly
  changes the scope
- live authorization: none

The strategy labels remain:

- `paper_lab_only`
- `not_live_authorized`
- `profit_claim=none`

Strategy routing:

- multiple strategy signals may be represented before paper planning
- `research_only`, `shadow_only`, and blocked strategy signals cannot feed
  paper-mutating plans
- only `paper_mutation_candidate` signals with required safety labels may route
  toward the paper supervisor
- conflicting promoted candidates block with operator review required
- the current SPY SMA 50/200 path is the first router-compatible strategy, not
  a broad strategy catalog

The strategy does not imply:

- live readiness
- profitability
- autonomous trading
- broad ETF universe support
- short selling
- leverage
- options support
- crypto support for this path
- market-data fetch approval

## Crypto Research Forward-OOS State

The ADA repair diagnostic is a separate research-only path. Its frozen
candidate state uses an immutable discovery snapshot, a manifest-pinned
discovery hash, strict post-cutoff OOS accrual, and no-submit eligibility only
after the existing fresh-OOS evidence gate passes.

An unrecoverable frozen candidate may be invalidated only through the explicit
operator reset workflow. That workflow:

- requires the invalidation switch, a non-empty reason, an explicit recovery
  source, and an explicit sibling archive path
- validates the complete replacement source before moving current state
- rejects an unchanged discovery hash, archive collisions, state-contained
  recovery sources, refresh modes, and network authorization
- moves the old state intact to the archive and never deletes it
- writes the invalidation record to both the archive and replacement state
- reinitializes through the same manifest-first frozen-snapshot path
- preserves all no-submit, no-broker-mutation, no-live, and `profit_claim=none`
  constraints

State invalidation does not validate the candidate, change evidence thresholds,
authorize a market-data fetch, or authorize paper/live trading. A read-only
market-data refresh remains a separate explicitly gated operation.

The forward-OOS refresh-readiness packet is an offline preflight only. It:

- validates the manifest, frozen discovery hash, accrued OOS state, and strict
  next refresh window
- recomputes the frozen candidate identity and fails closed on manifest drift,
  post-`as_of` lookahead, duplicate bars, or overlapping accrued bars
- reuses the refresh adapter's boolean-only paper-profile, credential-presence,
  paper-endpoint, and live-endpoint checks
- never includes credential values
- may report `ready_for_explicit_read_only_market_data_fetch`, but still keeps
  market-data authorization false and requires the separate explicit fetch
  operation
- performs no network access, market-data fetch, broker read, broker mutation,
  paper submit, or live action

## Command Surface Distinction

The repository distinguishes offline/reporting commands from broker-facing
paper commands. Keep that distinction explicit in docs, tests, and future
milestones.

### Offline Preview, Backtest, And Brief Commands

Offline commands are safe only when they stay local and deterministic.

Examples of offline/current reporting surfaces:

- `etf-sma-backtest`
- `etf-sma-cycle`
- `paper-lab-daily-preview`
- `etf-sma-paper-lab-review-packet`
- advisory or operating-brief rendering commands
- local content/package preview commands

Offline command contract:

- run before runtime paper profile loading
- consume local deterministic inputs
- may read local CSV, JSONL, fixtures, or explicit CLI values
- may read a local read-only reconciliation artifact
- write local artifacts only
- do not construct paper/live broker clients
- do not import Alpaca SDK paths for execution
- do not access credentials
- do not access the network
- do not fetch market data
- do not submit, cancel, replace, close, or liquidate
- preserve safety booleans such as `submitted=false`, `mutated=false`,
  `broker_action_performed=false`, `broker_mutation_allowed=false`,
  `network_access_attempted=false`, and `credential_access_attempted=false`
  where those fields are part of the artifact

`paper-lab-daily-preview` is offline-only despite its name. It consumes an
explicit local order-reconciliation JSONL artifact and delegates cycle decision
logic to the offline ETF/SMA cycle builder. It must fail closed on missing,
malformed, ambiguous, or conflicting reconciliation evidence.

`etf-sma-paper-lab-review-packet` is offline-only. It consumes an M401
local-bars ETF/SMA cycle proof JSONL artifact and writes one operator handoff
record. A ready 200-bar `buy_preview` proof becomes operator-review-only, while
insufficient history, non-SPY scope, or any source submit/mutation/network/
credential/live flag blocks the handoff. It authorizes no broker action.

### Broker-Facing Paper Commands

Broker-facing paper commands are not part of default offline operation.

Examples of broker-facing paper surfaces include:

- read-only paper order reconciliation
- read-only paper account, position, or order snapshots
- read-only paper broker snapshot/reconciliation records for operator review
- paper submit or close commands when explicitly scoped

Broker-facing paper command contract:

- require explicit milestone scope
- require operator approval when mutation is possible
- require paper profile gates before broker construction
- require credentials to be loaded only in the scoped shell
- print booleans and redacted metadata only
- must not print credential values
- must never use live URLs
- must fail closed on ambiguous responses
- must write deterministic operator artifacts where applicable
- must preserve `live_authorized=false`
- must preserve `not_live_authorized`
- must not run from default pytest

`paper-lab-read-only-broker-snapshot-reconciliation` is a read-only
paper-facing operator review command. It consumes the latest M402 review packet
plus a gated paper account/positions/open-orders/recent-orders observation and
writes exactly one JSONL record. Its only terminal states are operator-ready or
blocked states for profile gate failure, broker unavailability, incomplete
observation, open SPY orders, or unexpected non-SPY positions. It has no submit,
cancel, replace, close, liquidation, or retry-mutation path.

`paper-lab-read-only-broker-snapshot-operator-review` is offline-only. It
consumes the latest local read-only broker snapshot/reconciliation JSONL record,
validates clean flat/no-open-order observations and false safety authority
flags, writes one sanitized operator-review JSONL record, and has no credential,
network, broker adapter, submit, cancel, replace, close, liquidation, or live
support path.

Mutation-capable paper commands also require explicit intent flags such as
`--submit` and `--i-mean-it` where the command surface defines them. Those
flags are not enough by themselves; the milestone must also explicitly scope
the broker mutation.

## M376 Open-Order Caution

M376 remains the active open-order caution for SPY.

Current conservative state:

- order lineage: M376 SPY paper close order
- client order id: `paper-order-close-m376_spy_paper_close_submit`
- broker order id: `dbb32dd3-58bf-49ea-b9b1-9aa44e85002d`
- expected side: `sell`
- expected quantity: `0.033172072`
- latest recorded reconciliation context: M385
- observed status in that context: `accepted`
- observed filled quantity: `0`
- observed remaining quantity: `0.033172072`
- terminal state: `nonterminal`
- reconciliation decision: `m376_nonterminal_open`
- SPY position quantity observed in that context: `0.033172072`
- open SPY order evidence: present

Contract until superseded by a read-only terminal reconciliation:

- treat M376 as open/nonterminal
- block SPY submits
- block duplicate or overlapping SPY order intent
- allow offline work
- allow read-only reconciliation only when explicitly scoped
- do not submit a second SPY order
- do not cancel, replace, close, liquidate, delete, or retry as an autonomous
  action
- preserve `submitted=false`, `mutated=false`, and
  `broker_action_performed=false` for offline previews

The next allowed action for this caution is offline work or explicitly scoped
read-only reconciliation. A terminal state must come from a read-only
reconciliation artifact before this caution can be relaxed.

## Current Local Components

The deterministic local core currently includes these conceptual component
groups. This list is descriptive and does not authorize broker use.

Market data and research mechanics:

- synthetic fixtures
- local price snapshot metadata
- local replay and as-of mechanics
- local return construction examples
- fixture manifests and export snapshots
- research observation metadata

Screener and signal path:

- deterministic ask-momentum screener over synthetic `Bar + Quote` inputs
- screener-to-signal input bridge preserving order and object identity
- screener-ordered signal evaluation
- advisory signal-evaluation contracts
- explicit input-value and input-bundle contracts
- no LLM trading-path logic

Risk and execution planning path:

- deterministic risk checks
- `SignalRiskEvaluation`
- risk-approved row selection
- internal `ExecutionIntent`
- immutable `ExecutionPlan`
- no-op planning policy
- max-accepted-intents planning policy

Broker and portfolio path:

- local deterministic broker/reference behavior
- paper execution simulator
- portfolio state updates for local fills
- local reconciliation helpers
- order-event ledger contracts
- fake broker coverage
- Alpaca paper adapter work only behind explicit gates

Advisory and operating brief path:

- advisory artifacts
- candidate dossiers
- governance status snapshots
- data-source readiness summaries
- diagnostic issues and section/view records
- operating brief/reporting outputs
- no broker mutation authority

Offline research/backtest path:

- `etf-sma-backtest-stats` produces a research-only SPY ETF/SMA 50/200 daily
  long-only statistics artifact from strict local daily bars.
- `etf-sma-local-bars-canonicalize` catalogs local CSV candidates and only
  writes a strict canonical SPY daily-bars CSV when the source is non-synthetic,
  local operator evidence with at least 201 usable bars.
- `etf-sma-local-bars-manual-import` accepts one operator-specified local SPY
  daily-bars CSV only with a separate explicit provenance manifest whose
  `expected_input_sha256` exactly matches the computed CSV SHA-256, writes a
  strict canonical CSV only after manifest and data validation pass, and reruns
  the local-bars refresh path only after that canonicalization succeeds.
- `etf-sma-local-bars-backtest-refresh` validates a prior offline stats
  artifact, evaluates a strict local SPY daily-bars CSV, and classifies the
  refresh as blocked until at least 201 usable bars are available.
- It uses the conservative one-bar lookahead policy: posture through bar `t`
  may only affect the next return interval `t->t+1`.
- It is not paper/live authorization, not a profit claim, and not broker
  mutation authority.

## Reconciliation Contract

Reconciliation is observation, not autonomous repair.

Local reconciliation may compare expected portfolio state with broker-like
observed state and report:

- cash mismatch
- missing expected position
- unexpected broker position
- position quantity mismatch
- optional valuation mismatch when quote data is supplied
- missing order evidence
- ambiguous order evidence
- nonterminal order evidence

Read-only paper reconciliation may observe paper account, position, and order
state only when explicitly scoped. It may not mutate broker state. It must
redact credentials and fail closed when evidence is missing, ambiguous, or
conflicting.

## Short Selling

Short selling is not modeled end-to-end. `RiskConfig.allow_short` remains a
reserved field for future work, but short positions, borrow rules, margin,
valuation, reconciliation, and broker behavior are not part of the active SPY
strategy path.

The current SPY ETF/SMA path is long-only.

## Historical Context

The prior `docs/deterministic_core.md` acted as both current contract and
long-form milestone ledger. M387 separates those roles:

- this file is the current contract
- `docs/archive/deterministic_core_history.md` preserves a condensed historical
  overview
- `docs/project_checkpoint.md` remains the detailed checkpoint ledger

Historical notes are not permission to run paper or live commands. Current
permission must come from the active milestone scope and operator approval.

## Current Safe Next Actions

Preferred next work remains offline unless explicitly scoped otherwise:

- keep default tests offline, credential-free, and broker-free
- maintain the SPY ETF/SMA current-contract docs
- extend fake brokers and deterministic simulators
- improve local reconciliation artifacts and operator reports
- acquire or locally place real non-synthetic SPY daily bars with clear operator
  provenance, a manifest-pinned `expected_input_sha256`, and at least 201
  usable bars, then run the manual import gate before treating them as backtest
  evidence
- run read-only M376 reconciliation only under an explicit paper milestone
- keep SPY submit blocked until M376 is terminal by read-only reconciliation

Do not promote any paper/live mutation from this document alone.
