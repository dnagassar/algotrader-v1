# Phase 32 Step 17 - S05 Public-Documentation-Only Feasibility Decision

## Purpose

This document records a public-documentation-only feasibility decision for
`P30-BL-002-S05`.

It explicitly avoids direct vendor, source-owner, sales, support, or license
contact for now. It does not select, approve, acquire, download, ingest,
reproduce, validate, implement, or promote any dataset.

This phase is documentation-only. It adds no schema, notebook, script, code,
test, backtest, evaluator, signal computation, signal scoring, production
threshold, `ValidatedResearchArtifact`, or `ValidatedSignalDefinition`.

## Owner Decision

The project owner intentionally avoids external vendor/source contact at this
time.

Direct vendor/source confirmation remains optional future work. It is not a
current dependency, and the project must not rely on future vendor replies,
private confirmations, subscription discussions, or sales/support contact to
continue safe research planning.

## Consequence Of No Vendor Contact

Without direct vendor/source confirmation or acquired data access, exact S05
reproduction cannot be established.

No source can be selected, approved, purchased, acquired, ingested, or treated
as implementation-ready from public documentation alone. Public documentation
can support only cautious routing labels.

The following items remain unresolved unless fully answered by public
documentation:

- licensing and signed-use approval
- local archival permission
- private repository use
- automated local test use
- derived-statistics publication
- point-in-time/as-of and historical-version semantics
- correction and prior-version preservation
- exact universe coverage
- January 1965 through December 2009 instrument-level coverage
- raw contract versus continuous-contract availability
- roll methodology and roll metadata
- survivorship, delisting, missing-data, and quality flags
- pricing, entitlement, subscription, and offline-use terms

S05 can only proceed, if at all, as a public-doc-supported partial/proxy
planning route.

## Current Source Routing

Under public-documentation-only evidence, the current S05 source routing is:

| Source/category | Public-doc-only routing label | Boundary |
| --- | --- | --- |
| AQR | calibration/context only | Public factor or methodology material does not establish raw instrument-level S05 reproduction data. |
| CSI | documentation-supported partial candidate, not selected | Public docs may support further partial planning, but exact coverage, versioning, licensing, and archival rights remain unresolved. |
| Pinnacle/CLC | documentation-supported partial/proxy candidate, not selected | Public docs may support partial/proxy planning, but exact cross-asset coverage, roll methods, PIT/versioning, and rights remain unresolved. |
| Norgate | documentation-supported proxy candidate, not selected | Public docs may support a modern or reduced-universe proxy route, not exact S05 reproduction. |
| Portara/PortaraCQG | documentation-supported partial candidate, not selected | Public docs may support partial planning, but exact S05 mapping, metadata, PIT/versioning, rights, and cost remain unresolved. |
| TradeStation | likely unsuitable as primary source; conditional/proxy only | Platform dependence, access, export rights, history depth, and offline archival rights remain unresolved. |
| Institutional feeds | calibration/context only under personal/offline constraints | Possible institutional coverage does not fit current personal, offline, credential-free project constraints without access and license changes. |
| Broker-native APIs | likely unsuitable | Broker/API routes imply account, credential, network, depth, versioning, and archive constraints incompatible with primary S05 reproduction under current rules. |
| Public/free APIs and ETF/index proxies | proxy only | Public/free and ETF/index routes cannot establish the original futures/forwards panel and remain proxy-only. |

No label above selects or approves a provider, dataset, license, data source, or
implementation route.

## Feasibility Decision

S05 remains a public-doc-supported proxy/partial planning candidate only.

Exact reproduction, source selection, dataset approval, data acquisition,
schema design, validation, and implementation are paused unless future evidence
changes materially through public documentation, owner-approved direct
confirmation, or owner-approved data/access changes.

This is not a downgrade to methodology/context only because current public
documentation still supports cautious proxy/partial routing for some retail or
specialist futures-data categories. It is also not approval to proceed with
S05-exact work.

## Recommended Next Route

Safe next options are:

- Option A: pursue a docs-only proxy reproduction boundary using public/free or
  retail-accessible data assumptions, explicitly not S05-exact.
- Option B: pause S05 and evaluate another candidate with easier data
  availability.
- Option C: keep S05 in the backlog pending future vendor contact, budget
  change, license/access change, or stronger public documentation.

No implementation is allowed in this phase.

## Explicit Non-Goals

This phase does not perform or authorize:

- vendor contact
- vendor decision
- purchase
- subscription decision
- data acquisition
- data download
- data ingestion
- dataset storage
- schema, code, notebook, or script
- backtest
- reproduction
- strategy implementation
- evaluator or signal implementation
- signal computation
- signal scoring, ranking, direction, confidence, or actionability
- `ValidatedResearchArtifact`
- `ValidatedSignalDefinition`
- new contract type
- production threshold
- production-readiness claim
- implementation-readiness claim
- profitability, actionability, or trading implication
- broker, OMS, runtime, scheduler, persistence, portfolio, ledger,
  reconciliation, Alpaca, ML, or LLM trading-path behavior

Public documentation must not be treated as equivalent to signed license
approval or dataset approval.

## Remaining Blockers

Evaluator implementation and any production route remain blocked by all of the
following:

- no exact `ValidatedResearchArtifact`
- no exact `ValidatedSignalDefinition`
- no selected/approved dataset
- no completed primary-source vendor verification
- no acquired data
- no project-local deterministic reproduction
- no production threshold/config provenance
- no applied no-lookahead audit inside the project
- no implementation-scope approval
- no evaluator tests
- no signed or otherwise explicit license approval for the intended local use
- no deterministic offline snapshot path for any candidate source
- no resolved exact S05 universe reconstruction
- no resolved instrument-level January 1965 through December 2009 coverage
- no resolved raw contract, roll metadata, PIT/as-of, correction-history, or
  versioning basis

Do not start implementation from this decision boundary.

## Verification

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
