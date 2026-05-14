# Phase 33 Step 7 - Broad ETF Data-Source Terms / License Review Boundary

## Purpose

This document reviews public terms, license, and offline-use constraints for
candidate broad-ETF data and metadata sources.

It does not provide legal advice. It is a research-routing boundary only.

It does not approve data, a data source, an ETF universe, a benchmark, a cash
proxy, methodology, reproduction, validation, signal definition, evaluator,
implementation, or trading use.

This phase is documentation-only. It adds no data, notebook, script, schema,
test, source code, evaluator, signal computation, trading-path behavior,
broker behavior, runtime behavior, scheduler behavior, persistence behavior,
portfolio behavior, ledger behavior, reconciliation behavior, Alpaca behavior,
ML behavior, or LLM trading-path behavior.

## Candidate Sources Reviewed

The terms and license review covers these candidate or context categories:

- Stooq
- Yahoo Finance / yfinance / Yahoo API terms
- Nasdaq Data Link
- Alpha Vantage
- FRED
- ETF issuer pages, including iShares, Vanguard, SPDR, and Invesco
- broker historical data as context only

Public documentation pointers reviewed include:

- Stooq terms of service:
  <https://stooq.com/terms.html>
- Yahoo terms of service:
  <https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html>
- Yahoo Developer API terms:
  <https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.html>
- yfinance legal disclaimer:
  <https://ranaroussi.github.io/yfinance/>
- Nasdaq Data Link terms and documentation:
  <https://data.nasdaq.com/terms> and
  <https://docs.data.nasdaq.com/docs/data-organization>
- Alpha Vantage terms and support:
  <https://www.alphavantage.co/terms_of_service/> and
  <https://www.alphavantage.co/support/>
- FRED legal and API terms:
  <https://fred.stlouisfed.org/legal/> and
  <https://fred.stlouisfed.org/docs/api/terms_of_use.html>
- ETF issuer website terms for BlackRock/iShares, Vanguard, SSGA/SPDR, and
  Invesco:
  <https://www.blackrock.com/institutions/en-us/compliance/terms-and-conditions>,
  <https://advisors.vanguard.com/site/terms-and-conditions>,
  <https://www.ssga.com/fr/en_gb/footer/terms-and-conditions>, and
  <https://www.invesco.com/us/en/resources/terms-of-use.html>
- Alpaca market data documentation as broker-data context only:
  <https://docs.alpaca.markets/us/v1.4.2/docs/about-market-data-api>

Source URLs and terms may change. Any future source approval must repeat or
refresh this review against then-current official terms and, where needed,
obtain owner or legal review outside this document.

## Terms-Risk Labels

Only cautious labels are used:

- low apparent terms risk pending final review
- moderate terms uncertainty
- high terms uncertainty
- likely unsuitable for project-local archival
- context only

| Source/category | Terms-risk label | Current status |
| --- | --- | --- |
| Stooq | moderate terms uncertainty | Candidate only, not approved. |
| Yahoo Finance / yfinance / Yahoo API terms | high terms uncertainty | Candidate only, not approved. |
| Nasdaq Data Link | moderate terms uncertainty | Secondary/check candidate only, not approved. |
| Alpha Vantage | moderate terms uncertainty | Secondary/check candidate only, not approved. |
| FRED | low apparent terms risk pending final review | Cash/risk-free proxy candidate only, not approved. |
| ETF issuer pages | context only | Metadata/context only, not approved. |
| Broker historical data | context only | Context only, not default source, not approved. |

## Source Review Records

| Source/category | Personal/local research use | Manual/API constraints and rate/access limits | Caching, archival, private repo, and offline use | Redistribution and derived publication | Snapshot feasibility and terms clarity | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Stooq | Public website use appears possible, but the reviewed public terms do not by themselves approve project use. | Manual or URL-based access must respect the website terms; no project API route is approved. | Local archival and private-repo storage are not explicitly approved by this phase. The terms reviewed prohibit redistribution without Stooq consent, so private archival must not be assumed safe without final review. | Raw-data redistribution is not allowed without consent. Derived statistics or charts must avoid raw-data redistribution and must later follow source terms. | Deterministic snapshotting may be technically plausible only if a later terms review approves local storage/versioning. Terms clarity remains incomplete for project-local archival. | Candidate only, not approved. |
| Yahoo Finance / yfinance / Yahoo API terms | yfinance describes itself as research/educational and points users to Yahoo terms; Yahoo terms create uncertainty for anything beyond personal use. | Yahoo terms restrict automated collection without prior permission and Yahoo API terms include storage and support limits. yfinance is not endorsed by Yahoo. | Local caching, long-term archival, private-repo snapshots, and offline reuse are high-uncertainty unless Yahoo terms or explicit permission clearly allow them. | Redistribution, competing databases, and public reuse are high-risk unless expressly permitted. Derived statistics or charts must be reviewed carefully and avoid exposing raw Yahoo data. | Deterministic snapshots are not approved. Terms clarity is not sufficient for default project-local archival. | Candidate only, not approved. |
| Nasdaq Data Link | Personal/local use depends on the exact dataset and whether it is free or premium. | Documentation indicates dataset products use specific APIs and product pages. API, subscription, entitlement, and route support vary by product. | Caching, archival, private-repo use, and offline reuse must be checked at the dataset-license level. | Redistribution and derived publication rights depend on the original source, publisher, and subscription terms. | Snapshot feasibility is dataset-specific and not approved until exact coverage and terms are clear. Terms clarity is moderate because dataset terms may vary. | Secondary/check candidate only, not approved. |
| Alpha Vantage | Personal, non-commercial use appears possible under the reviewed terms, but the terms define some research/testing contexts as commercial use, so this remains uncertain. | API-key access and rate limits must be respected. The reviewed support page reports a free standard limit of 25 requests per day. | Local caching, archival, private-repo snapshots, and offline reuse require final terms review and possibly a paid/commercial agreement. | Redistribution and public reuse are not approved. Derived statistics or charts must avoid raw-data redistribution and follow Alpha Vantage terms. | Deterministic snapshots are not approved. Rate limits and possible commercial-use classification make this secondary/check only. | Secondary/check candidate only, not approved. |
| FRED | Public research, educational, non-commercial, and personal use appears promising, subject to FRED terms and series-owner restrictions. | API use requires an API key and must follow API terms, usage limits, and any series-specific copyright notices. | Local archival and offline use may be feasible only after recording API terms, series-owner status, citation requirements, and fixture/storage rules. Normal pytest must not call FRED or require credentials. | Raw redistribution and third-party copyrighted series need care. Derived statistics, charts, and citations must follow FRED and underlying source requirements. | Deterministic snapshotting is promising for limited cash/risk-free proxy series only if a later policy records terms, citation, and storage rules. | Cash/risk-free proxy candidate only, not approved. |
| ETF issuer pages, including iShares, Vanguard, SPDR, and Invesco | Page viewing for metadata/context appears possible, but issuer pages are not approved as project data sources. | Manual access must respect each issuer's website terms. Automated scraping or repeated extraction is generally not appropriate without permission. | Caching, local archival, private-repo storage, and offline reuse of issuer page content are not approved. | Raw page content, fund tables, holdings, and branded materials must not be redistributed unless permitted. Derived metadata summaries need citation and source-specific review. | Deterministic snapshots of issuer metadata are not approved. Terms clarity supports context-only routing, not archival. | Metadata/context only, not approved. |
| Broker historical data | Broker data may support account-specific or subscription-specific research outside normal pytest, but only as context here. | Broker access usually requires credentials, subscription entitlements, account terms, runtime API calls, and rate limits. | Direct broker data use conflicts with default offline, credential-free testing unless a later explicit fixture/storage policy permits a detached deterministic snapshot. | Redistribution and derived publication depend on broker and exchange data agreements. | Snapshot feasibility is not assessed here. Broker data is not a default source because credentials, terms, and runtime access conflict with normal offline tests if used directly. | Context only, not default source, not approved. |

## Source-Specific Cautions

- Stooq: public terms reviewed do not explicitly allow local archival or
  private-repo use for project snapshots. Do not assume permission.
- Yahoo Finance / yfinance / Yahoo API terms: Yahoo personal-use,
  automation, storage, and redistribution uncertainty remains high. Keep this
  as candidate only.
- Nasdaq Data Link: dataset-specific terms may vary. Keep it secondary/check
  only unless exact dataset terms are clear.
- Alpha Vantage: rate limits and terms must be respected. Keep it
  secondary/check only unless project use, archival, and publication rights are
  explicitly acceptable.
- FRED: public research use is promising, but API terms, series-owner
  restrictions, archival rules, citation requirements, and normal-pytest
  fixture policy must be recorded before any use.
- ETF issuer pages: use as metadata/context only. Reuse, scraping, copying,
  or archival of issuer content must respect each issuer's website terms.
- Broker data: context only, not default source. Credentials, subscriptions,
  terms, and runtime access conflict with default offline testing if used
  directly.

## Required Conclusions

No source is approved in this phase.

Any future approved source must permit deterministic local snapshotting or
must have an explicit fixture/storage policy that avoids normal pytest network
or credential access.

Any future derived-stat publication must avoid raw-data redistribution and
must follow source terms, citation requirements, and any underlying data-owner
restrictions.

Normal `python -m pytest` must remain offline and credential-free.

Public terms review is not final legal approval. A later approval phase must
record the exact source, exact dataset or endpoint, permitted use, caching and
archival policy, private-repo policy, redistribution limits, derived-stat
publication limits, API/rate-limit constraints, offline-use policy, and
deterministic snapshot/versioning policy before any data use.

## Recommended Next Gate

Recommended next docs-only gate: final source shortlist decision boundary.

Acceptable later gates remain:

- broad ETF evidence/source package for moving-average literature
- data storage/fixture policy boundary only after source terms are acceptable
- reproduction protocol boundary only after source, universe, benchmark, and
  data policy approval

No next gate may acquire data, ingest data, approve data, approve a universe,
approve a benchmark, approve a cash proxy, approve methodology, approve
parameters, reproduce results, validate, backtest, compute signals, implement
an evaluator, or create trading implications unless a later phase explicitly
scopes and approves that narrower work.

## Explicit Non-Goals

This phase does not perform or authorize:

- legal advice
- source approval
- universe approval
- benchmark approval
- cash proxy approval
- methodology approval
- moving-average parameter approval
- data acquisition
- data ingestion
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
- profitability claim
- production-readiness claim
- implementation-readiness claim
- trading implication
- broker, OMS, runtime, scheduler, persistence, portfolio, ledger,
  reconciliation, Alpaca, ML, or LLM trading-path behavior

## Remaining Blockers

Evaluator implementation and any production route remain blocked by all of the
following:

- no `ValidatedResearchArtifact`
- no `ValidatedSignalDefinition`
- no approved ETF universe
- no selected/approved data source
- no approved benchmark/cash proxy
- no approved methodology or parameters
- no approved data storage/fixture policy
- no acquired data
- no project-local deterministic reproduction
- no no-lookahead audit
- no production threshold/config provenance
- no implementation-scope approval
- no evaluator tests
- no approved data license or offline-use path
- no approved local snapshot/versioning policy
- no approved source-specific local archival/private-repo policy
- no approved redistribution or derived-stat publication policy
- no approved API rate-limit/access policy
- no approved total-return versus price-return decision
- no approved dividend/reinvestment treatment
- no approved corporate-action handling policy
- no approved correction/revision policy
- no approved point-in-time/as-of policy
- no approved ETF universe shortlist
- no approved inactive-fund, delisting, merger, or ticker-change policy
- no approved benchmark/cash-proxy frequency alignment rule
- no approved cash-rate conversion or compounding rule
- no approved transaction cost, slippage, spread, rebalance, fund-expense, or
  friction assumption
- no result-review template
- no promotion/rejection decision
- no trading implication or production threshold
