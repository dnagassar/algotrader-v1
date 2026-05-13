# Phase 32 Step 20 - S05 Route-Neutral Proxy Dataset Requirements Boundary

## Purpose

This document defines minimum requirements for any future `P30-BL-002-S05`
proxy dataset.

It is route-neutral. It does not choose among modern futures, reduced futures,
ETF/index proxy, AQR factor-level context, or manual table-check routes.

It does not select, approve, acquire, ingest, reproduce, validate, or implement
any dataset. It does not approve a provider, vendor, subscription, schema,
reproduction protocol, implementation path, production threshold, or trading
use.

This phase is documentation-only. It adds no schema, notebook, script, code,
test, backtest, evaluator, signal computation, signal scoring, production
threshold, `ValidatedResearchArtifact`, or `ValidatedSignalDefinition`.

## Dataset Requirement Categories

Any future proxy dataset plan must define these categories before route
narrowing, calculation, reproduction discussion, validation discussion, or
implementation discussion:

| Category | Minimum requirement |
| --- | --- |
| Universe definition | Identify the instruments, factors, indexes, ETFs, contracts, or published-table rows included and excluded. State whether the universe is futures-like, reduced futures, ETF/index, factor-level, or table-check only. |
| Date range | State start date, end date, sample breaks, excluded intervals, and whether the range is full, partial, modern-only, or table-period-only. |
| Frequency | State daily, monthly, contract-level, factor-level, table-level, or other cadence, and whether resampling would be needed in a later separately approved protocol. |
| Price/return fields | Identify required raw price, adjusted price, return, excess return, collateral/risk-free, roll return, or table value fields at a descriptive level only. Do not design a project schema from this boundary. |
| Timestamp/as-of semantics | Define observation timestamp, availability timestamp, publication timing, correction timing, and no-lookahead assumptions. Ambiguous timing must default to a weaker proxy label. |
| Provenance | Record source owner, source document or product name, citation or URL, access date, public/private status, and whether the claim is primary documentation, secondary documentation, or inference. |
| Versioning/snapshot discipline | Require a deterministic local snapshot plan, source version label, retrieval/access date, checksum or manifest concept, and rules for corrections or reissued data before any data is used. |
| Missing-data handling | State how missing instruments, missing dates, stale values, outliers, holidays, delistings, and unavailable fields would be recorded before any calculation. |
| Survivorship assumptions | State whether the universe is survivorship-free, survivorship-biased, unknown, or not applicable. Unknown survivorship blocks stronger claims. |
| Corporate action or contract adjustment assumptions | Where applicable, state whether equities/index proxies require corporate-action adjustment details and whether futures require contract-level adjustment details. |
| Roll/continuous construction assumptions | Where applicable, state roll schedule, roll trigger, back-adjustment, chaining, excess-return construction, and whether continuous-series logic is source-defined, reviewer-defined, or unavailable. |
| Currency handling | State quoted currency, conversion source, conversion timing, base currency, and whether currency effects are included, excluded, or unknown. |
| Cost/slippage/liquidity assumptions | State whether costs, slippage, bid/ask, commissions, financing, margin, liquidity, or capacity assumptions are relevant. If ignored, the plan must label the comparison as gross or cost-unadjusted. |
| License/offline-use constraints | State permitted local storage, private repository use, offline replay, derived-statistics publication, redistribution limits, subscription dependency, and unresolved legal or rights questions. |
| Reproducibility constraints | State how normal `python -m pytest` remains offline and credential-free, and how any future research-only data use would be isolated from normal tests and production paths. |
| Comparison target | State whether the target is exact S05 context, broad published behavior, methodology mechanics, factor-level calibration, public-table arithmetic, or workflow discipline. The target must match the proxy label. |

## Route-Specific Notes Without Route Selection

The notes below identify special requirements and weaknesses only. They do not
select a route, provider, dataset, schema, reproduction protocol, or
implementation path.

| Possible route | Special requirements | Main weaknesses |
| --- | --- | --- |
| Modern futures subset | Needs explicit futures universe, contract coverage, roll/continuous construction, currency, exchange/holiday, cost/slippage, and local snapshot rights. | May be modern-only, may exclude the original S05 period, may require licensed data, and may be overclaimed as exact S05 evidence. |
| Reduced-universe futures | Needs explicit exclusion labels, instrument-level coverage gaps, reduced-period labels, roll rules, and comparison targets that account for changed universe composition. | Exclusions can change the research question, weaken comparability, and make broad S05 claims unsafe. |
| ETF/index proxy | Needs explicit ETF/index universe, inception dates, corporate-action adjustment assumptions, expense/cost handling, survivorship assumptions, and a workflow-only comparison target. | Low S05 similarity; ETF/index returns are not futures/forwards time-series momentum evidence. |
| AQR factor-level calibration/context | Needs exact factor file/document identity, factor construction notes, date/version labels, publication timing, and a context-only comparison target. | Factor-level data is not raw instrument-level reproduction and cannot test project-local signal behavior or raw data handling. |
| Manually reconstructed published-table checks | Needs table identity, transcription discipline, citation, page/table labels, arithmetic checks, and table-check-only comparison target. | Cannot test raw data sourcing, universe construction, roll logic, no-lookahead mechanics, or implementation behavior. |

## Minimum Acceptance Criteria

A future proxy dataset plan must satisfy all of the following before it can be
used for any further proxy planning:

- carry an explicit non-S05-exact label
- state whether the route is partial reproduction, proxy reproduction, or
  methodology-only/context use
- define a clear universe and date range
- document source, provenance, access date, and evidence type
- define a deterministic local snapshot plan before use
- state explicit `as_of` and no-lookahead assumptions
- state explicit survivorship and missing-data assumptions
- state corporate-action, contract-adjustment, and roll assumptions where
  applicable
- state explicit cost, slippage, liquidity, and gross/net assumptions where
  relevant
- identify the comparison target and keep it aligned with the proxy label
- state limitations and non-claims before any result review
- preserve normal `python -m pytest` as offline and credential-free

Meeting these criteria would make a future plan reviewable only. It would not
approve the dataset, select the route, validate S05, or authorize
implementation.

## Rejection Criteria

Reject or defer any future proxy plan if any of the following is true:

- source, provenance, source owner, version, or access date is unclear
- the route is framed as exact S05 replication
- the data cannot be snapshotted deterministically for local review
- licensing or offline-use constraints are incompatible with local use
- licensing or offline-use constraints are unresolved in a way that blocks
  local use
- `as_of` and no-lookahead assumptions cannot be stated
- universe or date range is ambiguous
- missing-data, survivorship, adjustment, roll, or currency assumptions are
  unstated where relevant
- the comparison target is unclear or stronger than the proxy route supports
- the methodology encourages overclaiming
- the plan implies implementation or validation before reproduction review
- the plan would require normal pytest to use credentials, network access,
  broker state, or external data services

## Required Non-Claims

Any future proxy dataset plan must explicitly state that it does not prove:

- exact S05 replication
- original S05 edge
- profitability
- live trading readiness
- paper trading readiness
- production threshold validity
- strategy generalization
- implementation approval
- `ValidatedResearchArtifact` eligibility
- `ValidatedSignalDefinition` eligibility

Proxy results, if ever separately approved for review, cannot validate S05 by
themselves.

## Future Gates

Possible next docs-only gates after this boundary are:

1. Proxy route selection revisit.
2. Proxy dataset source shortlist boundary.
3. Proxy data storage/fixture policy boundary.
4. Proxy reproduction protocol boundary.
5. Proxy result-review template.
6. Pause S05 and evaluate another easier-data candidate.

Each gate must preserve route neutrality until a later prompt explicitly scopes
route narrowing, and no gate may imply dataset approval by itself.

## Recommended Next Routing

The safest next routing is to keep S05 in backlog after documenting these
proxy requirements.

If one more S05 planning step is useful, use a docs-only proxy dataset source
shortlist boundary that records possible source categories without selecting,
approving, acquiring, ingesting, or implementing any dataset.

If the research track needs faster progress toward reviewable evidence,
evaluate another easier-data research candidate instead of narrowing S05.

Do not implement from this boundary.

## Explicit Non-Goals

This phase does not perform or authorize:

- exact replication
- route selection
- dataset selection
- data acquisition
- ingestion
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
- no selected proxy route
- no approved proxy dataset source shortlist
- no approved proxy data-storage or fixture policy
- no approved proxy reproduction protocol
- no deterministic offline snapshot path for any candidate source
- no resolved exact S05 universe, 1965-2009 instrument coverage, raw contract,
  roll, PIT/as-of, correction-history, or versioning basis
