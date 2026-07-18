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
- SPY daily long-only ETF SMA 50/200 remains the initial paper-lab path;
  tournament-v2 BTCUSD/ETHUSD/SOLUSD is the current primary research-to-paper
  evidence lane. Neither path grants live authority.
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
- Read-only durable-cancellation reconciliation accepts one explicit
  cancel-intent, client-order, and broker-order identity plus one already
  injected broker-order observation. It performs no target discovery, broker
  read, credential access, network access, polling, or broker mutation. The
  local SQLite journal requires exact identity agreement across the request,
  observation, cancel-intent record, and order record; only an attempted,
  unknown, or accepted cancel intent is eligible. One transaction validates a
  non-stale UTC observation and converges the order and cancel-intent records
  together, or updates neither. Terminal cancel intents, reserved-only intents,
  stale observations, identity mismatches, and terminal-order regressions fail
  closed. The workflow remains non-retryable, cannot change runtime control,
  and exposes no submit, cancel, replace, close, liquidation, target-selection,
  or live capability. Obtaining any real broker observation remains a separate
  exact operator and network-access gate outside this workflow.
- The exact paper-cancellation observation boundary supplies that separate
  gate without granting cancellation authority. One immutable operator
  authorization is limited to paper mode, the read-only exact-order operation,
  one cancel-intent/client-order/broker-order identity, and at most 300 seconds.
  Invocation separately requires default-false observation and network
  permissions plus affirmative paper-profile, API-key-presence,
  secret-key-presence, exact-paper-endpoint, no-live-endpoint, and expected
  account facts. Only after every gate passes may the boundary invoke one
  injected exact-order reader with the authorized broker-order ID. It validates
  exact account and three-part order identity plus observation time before
  producing one `CancellationReconciliationObservation`. Failures are
  non-retryable and produce no observation. The boundary imports no broker SDK,
  reads no environment or credential values, constructs no network client,
  performs no target selection or polling, cannot update the journal or invoke
  reconciliation, and exposes no submit, cancel, replace, close, liquidation,
  or live capability.
- The paper-cancellation SDK reader is the narrow binding for that injected
  callback. Construction revalidates a complete paper profile and requires the
  exact canonical Alpaca paper endpoint; its client is private and exposes no
  raw SDK handle. On one exact broker-order ID it consumes itself before I/O,
  reads the paper account once, reads that exact order once, translates through
  the canonical response DTOs, and cannot poll, enumerate targets, retry, or
  mutate broker state. Wrong target identity is rejected before I/O; account,
  order, translation, and construction failures expose only a safe stage and
  exception type. The binding reads no environment variables, owns no runtime
  control or journal capability, and exposes no submit, cancel, replace, close,
  liquidation, or live method. Default verification injects deterministic fake
  clients and clocks. Any actual broker read remains a separate, fresh,
  exact operator-authorized operation and is not performed by verification.
- The exact paper-cancellation reconciliation workflow is the single
  repository-owned composition from that reader contract to local convergence.
  It accepts one explicit three-part cancellation identity, one pre-existing
  authorization/request, one caller-supplied exact reader, and one local
  journal. It invokes the observation boundary once and invokes the atomic
  reconciler once only when account, authorization, time, cancel-intent,
  client-order, and broker-order validation all succeed. Pre-read rejection
  performs no read and no journal mutation. Read failure or post-read rejection
  performs no reconciliation. Local validation or transaction failure updates
  neither journal record. Success converges both records in the existing single
  SQLite transaction while leaving runtime control unchanged. The workflow
  imports no SDK or configuration module, constructs no client, reads no
  credentials or environment, enumerates no unresolved intents, and exposes no
  target selection, polling, retry, submit, cancel, replace, close,
  liquidation, or live capability. Offline tests prove the complete chain with
  deterministic fakes; they do not authorize or perform a real broker read.
- The exact reconciliation operator binding is the default-disabled outer
  control-plane boundary. Its immutable request requires an explicit journal
  path, cancel-intent ID, client-order ID, broker-order ID, expected account,
  pre-existing authorization ID, UTC occurrence time, and separate affirmative
  operator-binding and network permissions. It derives paper-profile,
  credential-presence, canonical-endpoint, and live-endpoint facts from an
  injected `AlpacaPaperConfig`; it does not read environment variables or
  serialize credential or account values. Before reader construction it
  evaluates the existing authorization without minting one, requires the exact
  journal file, and checks only the named order and cancel-intent records for
  identity and reconciliation readiness. It never enumerates unresolved
  intents. Only then may it construct one private exact reader and invoke the
  one-shot workflow once. The general CLI cannot import this binding. Results
  are sanitized and non-retryable and expose no submit, cancel, replace, close,
  liquidation, target-selection, polling, or live capability. Default tests
  inject fake clients and clocks and block sockets; no real broker read is
  authorized or performed.
- The standalone exact reconciliation command is the dedicated operator-only
  entrypoint for that binding and is not registered in the general CLI. Its
  strict loader accepts only one size-bounded UTF-8 JSON object whose exact
  key set and canonical values match an existing
  `PaperCancellationObservationAuthorization.to_dict()` export. It rejects
  duplicate or extra fields, malformed or noncanonical UTC timestamps,
  unsupported versions, forged authorization IDs, and any evidence that
  cannot be reconstructed by the immutable authorization contract. The loader
  calls no authorization builder and cannot mint, renew, discover, or broaden
  authority. The command independently requires the exact authorization,
  cancel-intent, client-order, broker-order, journal, expected-account, and UTC
  occurrence facts. Operator-binding and network permissions are separate
  default-false flags checked before artifact or environment access. Only after
  both flags and a valid artifact may the command load canonical paper config
  and call the outer binding once. Output hides credential and account values,
  remains non-retryable, and declares no target selection, unresolved-intent
  enumeration, polling, runtime-control change, broker mutation, submit,
  cancel, replace, close, liquidation, or live authority. Default execution
  and all tests use missing artifacts or deterministic fakes with sockets
  blocked; verification never loads credentials or contacts a broker.
- The credential-free exact reconciliation readiness receipt moves every
  locally discoverable blocker ahead of a credentialed shell. Its immutable
  request requires the same explicit artifact, authorization ID,
  cancel-intent/client-order/broker-order identity, expected-account presence,
  local journal path, bounded UTC occurrence time, and a separate default-false
  offline-readiness flag. Network filesystem paths are rejected. The receipt
  uses the strict existing-artifact loader, the observation boundary's shared
  pure authorization matcher, and the operator binding's shared pure exact
  local-record check. It reads only the named order and cancel-intent records;
  it cannot enumerate or select targets. A ready result proves only that the
  offline inputs are internally consistent and reconciliation-ready. It does
  not verify the broker account or grant credential loading, paper config,
  network access, broker reading, operator binding, reconciliation, retry, or
  mutation authority. The receipt has no injected callback seam, imports no
  config, SDK, broker, environment, or network module, writes no artifact or
  journal state, and leaves runtime control unchanged. It is available only
  through its dedicated module/script and is not registered in the general
  CLI.
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

The repository distinguishes offline/reporting commands, exact-destination
read-only market-data commands, and broker-facing paper commands. Keep those
three capability surfaces explicit in docs, tests, and future milestones.

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

### Exact-Destination Read-Only Market-Data Commands

The Tiingo adjusted daily-bars refresh is a narrow network capability, not an
offline command and not a broker-facing command. Its executable surfaces are
`scripts/refresh_spy_adjusted_data.ps1` and
`algotrader.execution.etf_sma_adjusted_spy_data_refresh`.

Read-only market-data command contract:

- default mode remains `dry_run` and performs no credential lookup or network
  access
- an actual fetch requires both `live_market_data_fetch` mode and the explicit
  `LiveMarketDataFetchAuthorized` switch
- only HTTPS `GET` is permitted
- the authority must equal `api.tiingo.com`, with no port, user info, redirect,
  alternate host, or suffix match
- the path must equal `/tiingo/daily/{approved_symbol}/prices`, where the symbol
  is one of `SPY`, `QQQ`, `IWM`, `TLT`, or `GLD`
- query keys are limited to `startDate`, `endDate`, and `format=json`
- `TIINGO_API_KEY` is the only credential variable the adapter can load or send;
  broker credential variable names are not read by the adapter
- `APP_PROFILE=paper` and broker variables may coexist with this isolated
  capability; `APP_PROFILE=live` remains blocked
- the adapter imports no broker SDK, constructs no broker client, and cannot
  submit, cancel, replace, close, or liquidate
- a ten-calendar-day trailing window is fetched by default so same-date vendor
  corrections can be observed rather than skipped
- manifests record the provider response hash, prior canonical hash, normalized
  candidate hash, final canonical hash, changed dates, and new/unchanged/revised
  row counts
- when the explicit soak outputs are configured, each authorized live attempt
  adds a compact secret-free receipt to an atomically replaced JSONL ledger
- the readiness report deduplicates by expected NYSE session and measures the
  current consecutive qualifying-session streak across weekends and holidays
- retries do not inflate the streak; a failed latest session blocks readiness
  until that same session succeeds
- five consecutive sessions prove unattended data operation, not strategy edge
- raw, candidate, canonical, and manifest artifacts are promoted by same-volume
  atomic replacement after deterministic validation
- HTTP failures, invalid JSON, invalid bars, stale provider data, or scope
  violations preserve the previous canonical file and fail closed

The isolated Task Scheduler template
`docs/design/spy_eod_market_data_refresh_scheduled_task.xml` runs at 20:10
host-local New York time on weekdays, after Tiingo’s stated 20:00 correction
window. It is deliberately separate from the paper-mutation supervisor, uses
`IgnoreNew`, requires network availability, retries three times at fifteen-minute
intervals, and resolves the latest actually completed NYSE session across
pre-close runs, weekends, holidays, and early closes.
The task writes the soak ledger and report in the same invocation as the data
refresh. Neither artifact loads credentials, opens a network connection, calls
a broker, or authorizes an order. The readiness classification changes only
from accumulated refresh receipts; no LLM or agent judgment is in the decision
path.

Default pytest remains socket-blocked, credential-free, and network-free. Tests
exercise this boundary only through injected transports and local fixtures.

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

## Preregistered Crypto Tournament

The V5.22 crypto tournament is a separate research-only schema over the public
crypto CSV loader. It does not alter the legacy V5.19/V5.21 battery or the
closed ADA repair candidate.

- exactly 12 code-frozen candidates cover BTCUSD, ETHUSD, SOLUSD, and ADAUSD
  across 72-hour trend, 168-hour breakout, and 24/168-hour moving-average
  regime rules
- a shared consecutive one-hour UTC grid requires at least 4,320 bars per
  symbol; the final 1,728 hours form four untouched OOS folds
- the input path and SHA-256, exact refresh window, source, symbols, timeframe,
  row coverage, and no-mutation flags must match a passing guarded refresh
  packet; unbound input is never evidence-eligible
- at least 95% of hourly rows per symbol must carry positive reported volume
- four-hour robustness is aggregated locally from complete UTC buckets of the
  same source data
- one-bar causal execution, post-return-notional transition charging, 40 bps
  base transition cost, and 80 bps stress cost are fixed before evaluation
- cash, symbol buy-and-hold, and drifted equal-weight buy-and-hold are mandatory
  benchmarks
- multi-fold stability, profit concentration, drawdown, transition, completed
  round-trip, stress-cost, and four-hour robustness gates must all pass
- the maximum outcome is `eligible_for_no_submit_shadow_evaluation`; paper
  planning, broker execution, capital allocation, and live trading remain
  ineligible

The canonical contract and fingerprint are recorded in
`docs/design/v5_22_crypto_preregistered_tournament.md`. Default tests and the
tournament runner remain local, deterministic, credential-free, network-free,
broker-free, and no-submit. A separately authorized history refresh may produce
the input CSV through the existing fixed-host market-data adapter only.

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

## Crypto Tournament V2 Forward-OOS Contract

Tournament v1 remains closed at its terminal four-symbol input-quality gate.
Tournament v2 is the separately fingerprinted BTCUSD, ETHUSD, and SOLUSD
research lane defined by fingerprint
2ed9489543d8d21ab00d9f2f4000927b8012decf39882cb721cb2d1ce0b9376b.

The research state machine imports only research types and deterministic return
math. It validates local receipt-bound files, freezes discovery, accrues raw
embargo/OOS bars, applies the preregistered isolated-gap policy, and releases
candidate metrics only at 2026-08-13T00:00:00Z or later. It has no network,
credential, broker, account, order, paper-mode, or live-mode path.

The orchestration wrapper is the sole v2 bridge to the existing guarded crypto
history adapter. Its network mode is narrowed to exactly the next missing
completed UTC hour range, exactly BTCUSD/ETHUSD/SOLUSD, timeframe 1Hour, and
location us. It requires the adapter's explicit allow-network and
market-data-fetch authorization flags. The adapter must run in
data-intake-only mode: it validates and binds OHLCV without invoking the legacy
strategy evidence battery. V2 validates the receipt and its own frozen
per-symbol quality policy directly.

State files use atomic replacement and bind the manifest, discovery snapshot,
raw embargo/OOS histories, and receipt ledger by SHA-256 plus a state
fingerprint. Exact retries deduplicate. Conflicting rewrites fail closed.
Interim artifacts contain no targets, trades, returns, drawdowns, rankings, or
selection. Terminal scoring includes the embargo-close to first-OOS-close
return under the final embargo signal, charges its OOS boundary entry, and
excludes embargo round trips. A terminal success or input-quality failure
creates one hash-bound terminal packet; later checks replay it and reject new
deltas or rescoring. Terminal input failure does not extend the endpoint.

Even a terminal winner is eligible only for a new no-submit single-winner
forward-shadow contract. Paper planning, paper mutation, broker execution,
capital allocation, live trading, and profit claims remain unauthorized.

## Tournament V2 Forward-Shadow Activation Contract

The candidate-agnostic V5.24 forward-shadow contract is frozen before
tournament-v2 selection under fingerprint
7ff152e69bd00eb8da9376d1f2be15194fbd04ed6a420151e30c3c46bec82436.
It accepts only the public tournament state machine's validated terminal
packet, requires the sealed terminal packet SHA-256 and evidence fingerprint,
and binds exactly one selected candidate ID/fingerprint from the frozen v2
manifest. A nonterminal tournament emits only
`waiting_for_tournament_terminal`; a terminal rejection cannot mint a shadow
activation.

The future window contains 168 untouched one-hour observations beginning at
the first complete UTC hour not earlier than both terminal closure and the v2
OOS endpoint. A delayed closure advances the start to the next full hour.
Early stopping, extension, parameter changes, post-selection gate changes,
paper planning, broker access, paper mutation, capital allocation, and live
trading remain disabled. Even complete shadow evidence permits only a later
bounded-paper-probe review, not a paper probe or live-capital action.

## Tournament V2 Forward-Shadow State Contract

V5.25 implements the V5.24 activation without changing its fingerprint or
thresholds. It remains dormant before one sealed eligible tournament-v2 winner,
then freezes the activation, the byte-bound terminal source, the exact selected
candidate, and 169 selected-symbol causal context bars. A delayed activation
interval is accrued as unscored signal warmup; the scored future window remains
exactly 168 one-hour bars with completeness-only checkpoints at 24, 72, and 168.

Raw history, normalized history, and hourly causal decisions are monotonic.
Committed evidence must end on a raw boundary bar. One proven isolated interior
gap uses prior-close OHLC, zero volume, and prior-target hold; a missing trailing
bar is not prematurely committed, an excessive gap stops the committed prefix,
and no later raw row may replace a committed imputation. Replays must reproduce
the prior normalized and decision prefixes exactly. Exact duplicate receipts
deduplicate and conflicting rewrites fail closed.

Mutable generations use a fingerprinted recovery journal under an exclusive
state lock. Canonical evidence files are replaced only after their staged
SHA-256 identities and prior state fingerprint are validated, and the frozen
state is published last. A later invocation finishes an interrupted generation
before loading it. Status cannot synthesize a new state identity, and
initialization cannot return a frozen identity without persisting it.

The locked 0.995 raw-coverage threshold means one missing terminal hour is
already disqualifying over 168 hours. Terminal evaluation still records the
predeclared imputation behavior but seals the input-quality outcome. A complete
window uses the existing one-bar-lag return engine, 40/80 bps transition costs,
cash and same-symbol buy-and-hold benchmarks, and no forced terminal
liquidation. It seals either decision evidence for a bounded-paper-probe review
or a terminal shadow input-quality gate, then rejects later deltas and rescoring.

The research state module contains no network or execution dependency. Its
separate operating bridge derives exactly one symbol and one inclusive completed
hour range from frozen state and delegates only to the existing guarded crypto
market-data adapter. Both explicit network switches remain required. Fetch
preparation is non-mutating; a returned receipt must match its on-disk JSON and
output SHA-256 before state accrual. Dormant, waiting, and terminal states never
invoke the adapter.

The complete network-capable operating cycle is also serialized by a distinct
process lock spanning frozen-state status, adapter invocation, receipt
validation, and accrual. A competing cycle fails before any second adapter
call; the state-generation lock continues to protect local publication.

The detailed contract is recorded in
`docs/design/v5_25_crypto_tournament_v2_forward_shadow_state.md`. V5.25 improves
end-to-end research autonomy and removes post-selection workflow delay. It does
not itself add strategy performance evidence before the future calendar window,
and it grants no broker, paper-mutation, capital, or live authority.

## Tournament V2 Bounded Paper-Probe Review Contract

V5.26 preregisters the decision boundary after one sealed V5.25 forward-shadow
outcome. Its fingerprint is
`3b82ebcaf3c80b9c1fbda5797623b2e616dfef0a3ed38d2cc52c0b1d3151efb5`.
The state exporter recovers and locks V5.25 state, validates every persisted
identity, independently regenerates normalization, decisions, metrics, and the
terminal evidence fingerprint, and returns a path-free export without creating
new evidence state. It may first complete an already-journaled interrupted V5.25
transaction under the state lock. V5.26 then requires the exact frozen v2 candidate, exact 168-hour window,
canonical checkpoint state, terminal scoring flag, closure ordering, metric
algebra, and false-authority contract.

The eight frozen gates require positive base and stress returns, positive base
and stress excess returns versus same-symbol buy-and-hold, base and stress
drawdown no greater than 20 percent, and each drawdown no worse than the
corresponding buy-and-hold drawdown. Evaluation is driven directly by the
fingerprinted manifest. No result-dependent transition minimum, retuning,
candidate substitution, ranking, rescue path, or window extension is allowed.

The prospective probe envelope is exact-selected-symbol, long/cash, USD 10
maximum notional/principal, USD 2 durable loss halt, one position/open
order/entry/exit, one cancel attempt per order, zero replacements, and 168
hours, with no leverage, margin, shorting, pyramiding, or cross-symbol exposure.
Venue, policy, lifecycle plus independent flat reconciliation, and durable
kill/loss capabilities are all required. Capability files must bind canonical
bytes to separate producer-source files, exact upstream source contracts, one
policy fingerprint, and one coherent bundle fingerprint; assertions alone are
invalid. Every cited upstream artifact is resolved from a fixed local path,
bound by canonical bytes, and semantically validated; claims and observation
time are derived from those bytes.

For a multi-source capability, the earliest upstream observation controls the
kind expiry; a fresh reconciliation cannot refresh stale mechanics evidence.
The normalized policy, lifecycle, and kill upstream schemas still require real
canonical producers and resolved subordinate code/test receipts before they can
constitute operational evidence; coherent unit fixtures are contract tests only.

The deterministic outcomes are waiting, terminal input-quality closure,
economic rejection, operational-evidence block, or
`eligible_for_operator_review_only`. Eligible review packets expire at the
earliest effective capability expiry. Their full safety-critical identity is
fingerprinted. The V5.26 persisted validator is structural only. V5.27 supplies
the separate source-bound capability producer and pinned generation-replay
consumer that replays the snapshotted terminal, capability, producer, and
upstream sources with trusted current UTC and requires the exact historical
fingerprint. Publication uses a local process lock, immutable
fingerprint-addressed generations containing the terminal source and only
capability sources actually evaluated after strategy acceptance, and an atomic
latest manifest written last. Replay validation remains non-authorizing.

This module imports no execution adapter and has no network, credential,
account, broker, order, paper-mutation, capital, or live path. Its strongest
outcome still has every authority field false and requires a separate exact
operator authorization. The full contract is in
`docs/design/v5_26_crypto_tournament_v2_bounded_paper_probe_review.md`.

## Tournament V2 Capability Production And Replay Contract

V5.27 implements the candidate-deferred operational-evidence path for the
frozen BTCUSD, ETHUSD, and SOLUSD tournament. Its bounded-probe safety-policy
fingerprint is
`c0abbc047f7bdf01f19d46e06d3824acd980016b4bd992d78dd4994db6d2c407`.
Before V5.25 seals an accepted terminal winner, production publishes only
`candidate_deferred_pending_terminal_winner`; malformed or irrelevant
capability inputs cannot alter that classification. A quality or economic
rejection also terminates before capability resolution.

The offline bounded-probe safety module combines a pure evaluator with a durable
local SQLite control store. It is default-paused and has no broker, credential,
network, adapter, or order-submission import. Its source-bound certification
covers the USD 1-10 entry envelope, cash/account/data gates, durable
restart-latched USD 2 loss halt, atomic entry admission, persistent
entry/cancel/exit attempt budgets, and risk-reducing cancel or exit admission
while entry is halted. All authority fields remain false.

Venue capability requires one coherent V5.1 paper-read packet plus the exact
refresh, visibility-wrapper, and supervisor source bytes. It validates manifest
hashes, read-only safety fields, candidate-specific order increments and
notional limits, nested runtime metadata, and an exact selected-symbol match.
Both runtime visibility and the V5.1 refresh independently expire after 24
hours; the older observation controls. V5.28 adds an optional exact BTCUSD,
ETHUSD, or SOLUSD target validated before SDK construction or broker reads. The
target is the supervisor's sole preference and absence never falls back to
another symbol. Operational venue normalization requires target scope and an
exact target/selected-symbol/winner match; the sealed review independently
validates those normalized target fields.

Advertised minimum notional, size, and trade increments must exactly match
their broker-observed and runtime counterparts. Optional required fields must
contain matching empty strings when unavailable; a nonempty alternate
`min_order_notional` must equal the primary minimum. A derived minimum order
value above USD 10 fails closed.

Lifecycle capability requires a locally hash-coherent V5.6-V5.10 chain and the
exact producer source bytes. The legacy V5.8/V5.10 path is BTCUSD-only and
cannot certify ETHUSD or SOLUSD. The current historical mutable-latest chain is
also rejected because it no longer retains the exact V5.6 bytes named by V5.8.
All five lifecycle timestamps must be ordered and non-future, and the earliest
antecedent controls freshness. A newer downstream receipt cannot refresh an
older precursor. Historical lifecycle account observations must be active and
carry all three explicit false block flags; the V5.9 packet has an exact schema
and canonical operator phrase, with all authority, network, and
credential-exposure fields false. V5.8 must have zero fill and empty residual
state. V5.10 entry and exit fills must both be positive, match the nested final
orders, and follow the ordered run, submit, fill, exit-submit, exit-fill
chronology. Its broker-reported exit `filled_at` is the final mutation time.
Independent flat reconciliation requires completed account/position/order read
attestations, zero account-wide positions and open orders, and a fresh receipt
observed at or after that final mutation time. The sealed review independently
re-derives that ordering and the venue semantics from normalized upstreams.
Lifecycle and flat evidence must bind the same expected paper account through a
domain-separated hash; raw account identifiers are absent from normalized
capability and flat outputs.

Capability and review generations are immutable and fingerprint-addressed,
with an exclusive local lock and latest pointer written last. Canonical loaders
and replay reject duplicate or noncanonical JSON, unsafe paths and Windows path
aliases, links/reparse points, hash or manifest drift, authority injection,
mixed layouts, and stale or future-dated evidence. A pinned replay reconstructs
production from captured source bytes and trusted current UTC and must match the
exact historical fingerprints. It grants no paper mutation, capital, live, or
broker authority.

Blocked or malformed inputs are not snapshotted. Exact raw lifecycle bytes are
retained only for a fully validated local bundle so replay can re-execute the
legacy provenance chain. These ignored `runs/` artifacts may contain
noncredential account/order identifiers and must not be treated as shareable
reports; normalized outputs use the non-secret account binding.

The real 2026-07-17 offline pipeline run certified the safety kernel for all
three frozen symbols and correctly remained candidate-deferred because no
V5.25 terminal winner exists. This materially improves research-to-paper
operational autonomy and evidence integrity, but adds no strategy-return
evidence and does not change live-capital readiness. The full contract is in
`docs/design/v5_27_crypto_tournament_v2_capability_production_and_replay.md`.

### V5.29 Target-Scoped Independent Flat Collection

V5.29 adds the canonical broker-read boundary for the existing pure independent
flat validator. It validates the exact BTCUSD, ETHUSD, or SOLUSD target and a
same-symbol filled-exit lifecycle before environment resolution or client
construction. The read-capable path requires explicit read and network
switches, paper profile and endpoint, credentials, and expected-account
matching. It reads only the account, all positions, and all open orders.

Success requires a fully active, unblocked account with zero account-wide
positions and open orders. Raw account identifiers remain process-local and
only the V5.27 domain-separated account binding is persisted. Receipt and
manifest bytes bind the exact lifecycle and collector source hashes. A newer
failed or nonflat read moves any previous mutable-latest receipt into a
recoverable generated superseded directory so stale evidence cannot remain
active.

The collector exposes no submit, cancel, replace, close, or liquidation seam.
It grants no paper mutation, capital, or live authority. The full contract is
in
`docs/design/v5_29_crypto_target_scoped_independent_flat_collection.md`.
