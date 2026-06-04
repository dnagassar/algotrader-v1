# Deterministic Core Historical Context

This archive preserves the important historical context compacted out of
`docs/deterministic_core.md` during M387. It is intentionally condensed. The
active contract now lives in `docs/deterministic_core.md`; the detailed
checkpoint ledger remains in `docs/project_checkpoint.md`.

Historical context is not operational permission. Broker-facing or paper/live
actions still require explicit milestone scope, profile gates, credential
redaction, and operator approval.

## Compaction Boundary

Before M387, `docs/deterministic_core.md` mixed two roles:

- current deterministic-core contract
- long milestone ledger covering early phases through M385

M387 keeps the active contract lightweight and preserves history here by topic.
No source files, tests, broker code, paper commands, live commands, execution
code, CLI code, or config code were intentionally changed by this docs-only
cleanup.

## Foundational Local Core

The early project built a deterministic local trading core around explicit
inputs and structured results. The core established local portfolio state,
paper execution simulation, risk checks, local broker-like behavior, and
reconciliation helpers while keeping external broker connectivity out of
default workflows.

Important historical rails from this period:

- normal pytest stays offline and credential-free
- broker behavior is isolated behind explicit adapters
- Alpaca SDK work is gated and not part of default tests
- fake brokers and local simulators are preferred for development
- broker contract tests protect deterministic local behavior
- live trading remains forbidden

## Screener To Planning Path

Phases 8 through 20 built the deterministic pre-broker pipeline in small
layers:

- synthetic `Bar + Quote` ask-momentum screener
- deterministic `min_score` and `top_n` filters
- orchestration-owned screener-to-signal bridge
- screener-ordered signal evaluation
- Signal -> Risk evaluation
- dependency-direction guardrails
- risk-approved row selection
- internal `ExecutionIntent`
- immutable `ExecutionPlan`
- `PlanningPolicyResult`
- no-op planning policy
- max-accepted-intents planning policy

The historical contract stayed consistent: risk-approved rows are permission
signals only; execution intents and plans are pre-broker objects; planning
policy is pre-broker; none of those layers submits orders.

## Research And Advisory Boundary

The research track established a clear boundary between advisory research and
the deterministic trading path. Research artifacts, validated signal definition
metadata, evaluator input snapshots, time/as-of primitives, signal input
values, input bundles, and completeness checks were added as contracts or
metadata before any real trading behavior.

Historical constraints from this track:

- research output is evidence, not an order
- signal definitions are promoted metadata, not execution decisions
- signal evaluation remains advisory before risk
- LLM-assisted work may summarize or critique outside the hot path only
- LLMs do not enter signal, risk, execution, broker, or runtime trading logic
- feature and research code must not import broker, SDK, network, or execution
  dependencies

## Synthetic Replay And Data Readiness

Later research phases added synthetic-only replay, return construction,
manifest serialization, descriptive replay metrics, metadata-only research
result packages, local price snapshot metadata, daily backtest mechanics,
SMA exposure mechanics, export snapshots, data-source readiness records, and
advisory package attachments.

These phases did not approve real market-data ingestion, live data fetching,
broker access, trading, profitability claims, or autonomous runtime behavior.
They created local deterministic evidence structures and guardrails for future
review.

## Operating Brief And Advisory Artifacts

The advisory/operating brief path introduced governance snapshots, candidate
dossiers, prepared brief parts, board summaries, diagnostic issues, section
records, view records, content bundles, package previews, and synthetic MVP
operating brief artifacts.

The preserved contract is:

- operating brief output is advisory
- content bundles are local/reporting artifacts
- brief rendering does not authorize trading
- advisory artifacts do not mutate broker state
- default tests remain offline and deterministic

## Crypto Paper Lab History

Milestones around M309 through M329 explored BTCUSD paper-lab readiness,
submit gates, adapter diagnostics, minimum notional policy, receipts,
recent-order queries, reconciliation briefs, and close/exit probe preparation.

The important preserved context is that these were supervised paper-lab
experiments with explicit gates and reports, not live authorization and not
autonomous trading. Any crypto paper path remains separate from the current
active SPY ETF/SMA strategy contract.

## SPY ETF/SMA Research To Paper Path

Milestones M334 through M385 moved the project toward a small supervised SPY
paper-lab loop:

- M334-M338 shaped the SPY ETF/SMA research candidate, paper-lab experiment
  plan, offline backtest summary, and evidence packet.
- M339-M343 built preview and operator-review artifacts without submitting.
- M345-M350 created signal evaluation, intent, execution-plan, and review
  readiness artifacts for SPY ETF/SMA paper work.
- M351-M355 moved through explicitly scoped tiny SPY paper probe preparation
  and supervised paper-only action history.
- M363-M365 recorded read-only lifecycle observations and cancel-readiness
  boundaries.
- M366-M369 built reset evidence, paper preview, and operator-review gates.
- M371-M373 hardened paper order lifecycle replay and repaired the paper submit
  command surface offline.
- M375 prepared a broker-facing SPY close preview gate.
- M376 repaired the SPY close-submit path offline and produced the current
  M376 SPY paper close order lineage.
- M377A/M377B ran read-only SPY ETF/SMA cycle-preview attempts, with M377B
  observing an open SPY order blocker.
- M378 added the offline `etf-sma-backtest` artifact path.
- M379 added read-only `paper-order-reconcile` for exact M376 lineage.
- M382 added the generic offline `etf-sma-cycle` command.
- M383 refreshed M376 read-only reconciliation and kept SPY submit blocked.
- M384 added offline `paper-lab-daily-preview`.
- M385 refreshed M376 reconciliation again and kept M376 nonterminal/open.

The active result from this history is the current SPY daily long-only ETF SMA
50/200 paper-lab contract with a hard M376 open-order caution.

## M376 Preserved Caution

M376 is the SPY paper close order lineage that must remain blocking until
terminal read-only reconciliation says otherwise:

- client order id: `paper-order-close-m376_spy_paper_close_submit`
- broker order id: `dbb32dd3-58bf-49ea-b9b1-9aa44e85002d`
- expected side: `sell`
- expected quantity: `0.033172072`
- latest historical reconciliation in this archive: M385
- observed status: `accepted`
- observed filled quantity: `0`
- observed remaining quantity: `0.033172072`
- terminal state: `nonterminal`
- reconciliation decision: `m376_nonterminal_open`

SPY submits remain forbidden until a future explicitly scoped read-only
reconciliation artifact reports terminal evidence. This archive does not
authorize submit, cancel, replace, close, liquidation, delete, retry, live
profile, credential printing, or broker mutation.

## Current-History Split

Use the documents this way:

- `docs/deterministic_core.md`: current deterministic-core contract
- `docs/archive/deterministic_core_history.md`: condensed historical context
- `docs/project_checkpoint.md`: detailed checkpoint and milestone ledger

If these documents ever disagree, use the current contract plus the latest
explicit milestone scope and operator approval. Historical notes are evidence,
not authority.
