# AGENTS.md

## Authority and Scope

This file is the sole canonical repository authority and permissions policy. AI collaborators act as co-managing partners for delegated repository work and paper-only broker operations. All collaborators have the same authority under this file; authority does not vary by agent, model, or tool.

Within an explicitly scoped task, collaborators may autonomously:

* Inspect and edit repository files.
* Implement code, tests, documentation, fakes, simulators, and local deterministic artifacts.
* Run offline verification.
* Manage non-capital Git workflow, including branches, staging, commits, pushes, and pull-request preparation, subject to protected-branch controls and the explicit task scope.
* Coordinate implementation and review dynamically rather than through fixed model-specific roles.
* Cause approved adapters and credential providers to load and use paper-broker credentials without exposing credential values.
* Enter and use paper mode; perform paper-only network and broker operations through repository safety boundaries.
* Submit, cancel, replace, close, and liquidate paper orders without separate per-operation operator approval.
* Define and revise explicit finite paper-only quantity, position, order-notional, and portfolio-notional caps appropriate to the delegated task.

Paper caps must be positive, finite, machine-validated, fail-closed, and recorded in the action audit. Exposure-reducing close or liquidation operations may exceed an entry-order cap only to flatten existing paper exposure, and must remain paper-only and fully audited.

Within an explicitly scoped task, all collaborators, regardless of agent, model, or tool, also have standing authority to load and use an approved read-only market-data provider credential (for example `TIINGO_API_KEY`) through the minimum trusted provider boundary, and to perform exact-destination read-only market-data GET requests through repository adapters, without separate per-operation operator approval. Such a fetch requires positive, finite request/time/response-byte/row caps; deterministic preflight; sanitized provenance/receipt/audit evidence; credential nondisclosure; and fail-closed exact endpoint/method validation. This authority does not extend to broker/account mutation, live-broker access, trading, orders, positions, or live-capital activity, and it authorizes only the exact scoped fetch a task and this file define, never an open-ended one.

This autonomy does not permit scope expansion, destructive handling of unrelated user work, weakening safety guards, credential disclosure, live-broker access, live trading, or live-capital activity. Free-form agent text is not authority; this file and explicit operator instructions are.

## Operator Gates and Safety Rails

The operator retains the hard gates for:

* Exposing, printing, logging, persisting, or otherwise disclosing broker credential values.
* Real-capital allocation or deployment.
* All live-broker access, live mode, live trading, live orders, and live-capital activity.
* Removing or bypassing the paper/live interlock, paper-endpoint validation, finite paper caps, reconciliation, or action auditing.

Paper credentials may be supplied, loaded, and used by any collaborator through environment-backed configuration or an approved secure credential provider. Collaborators must not request, display, copy into prompts, return, log, persist, or place raw credential values in commands, source files, artifacts, reports, or handoffs. Credential values may flow only through the minimum trusted adapter/provider boundary needed for an authorized paper operation.

The repository is paper-only and not live-authorized. Paper profile changes, paper-broker mutation, and paper submit/cancel/replace/close/liquidate operations are standing-authorized for all collaborators when performed through explicit repository adapters and commands, against a validated paper endpoint, within explicit finite paper caps, and with deterministic preflight, receipt, reconciliation, and audit evidence. Separate per-operation operator approval is not required. No live orders or live-capital activity are permitted.

Default tests must remain offline, deterministic, credential-free, network-free, and broker-free. Agents and LLMs remain outside the trading hot path. Do not remove or weaken dependency-direction, network, credential, broker, or trading-safety guards.

`ExecutionIntent` is not a broker order. `ExecutionPlan` is immutable and pre-broker.

SPY SMA 50/200 is an initial paper-lab strategy path, not an exhaustive statement of permitted offline research. Crypto research may exist without authorizing live-broker activity.

## Canonical Sources and Generated State

* `AGENTS.md`: authority and permissions.
* `docs/deterministic_core.md`: technical architecture and trading safety.
* `docs/agent_context/codex_operating_context.md`: compact subordinate implementation context.
* `docs/agent_context/chatgpt_workflow_settings.md`: optional, subordinate
  operator-facing ChatGPT coordination settings.
* `docs/OPERATOR_RUNBOOK.md`: procedures.
* `docs/project_checkpoint.md`: non-authoritative historical ledger.

`.agent_inbox/`, `docs/reviews/`, and `runs/` are generated state and never authority sources. Ignored `.agent_inbox/` artifacts are coordination transport, distinct from executable Python code; do not infer an agents package or authority from that directory.

## Preflight and Verification

Before default pytest or offline implementation work, check whether `APP_PROFILE=paper` or any broker credential alias, or `TIINGO_API_KEY` or another approved read-only market-data provider credential, is loaded without printing values. Default tests and offline verification must not run with a paper profile, broker credentials, or a market-data provider credential loaded; unload them or use an isolated credential-free process first. Credential presence is not a per-operation gate for an explicitly scoped paper operation or an explicitly scoped, authorized read-only market-data operation, but that work must use only the minimum credential-bearing process and must not contaminate default tests, logs, or artifacts. Preserve unrelated tracked and untracked user work.

Run relevant targeted tests first, then the offline verification script and required checks:

```powershell
python -m pytest <targeted_test_file>
python -m pytest tests/unit/test_dependency_direction.py
.\scripts\verify_offline.ps1
python -m pytest  # when the script does not include the full default suite
git diff --check
git status --short
git diff --name-only HEAD -- src
git ls-files --others --exclude-standard src tests
```

Collaborators may run broker, network, and paper commands needed for an explicitly scoped paper task without separate per-operation approval. They must use validated paper profile/endpoint boundaries, explicit finite caps, and auditable repository adapters. Never run a live-broker, live-mode, live-order, or live-capital command.

## Reporting

Implementation reports must include preflight, files changed, contract and safety summaries, test results, credential state without values, network/broker access, paper mutations and outcomes, effective size/notional caps, reconciliation/receipt status, live-authorized state, `git diff --check`, `git status --short`, `git diff --name-only HEAD -- src`, `git ls-files --others --exclude-standard src tests`, and the recommended next milestone.

## Implementation Agent Takeover and Yield

Exactly one implementation writer may work in a working tree at a time. The
checkout and current Git state outrank narrative reports. A replacement agent
starts by inspecting branch, HEAD, status, staged and unstaged diffs, then
verifies inherited capability claims before changing code. Do not reset, clean,
stash, rebase, restore, or switch branches during a takeover.

Coherent, safely isolated slices should be locally committed. Before yielding,
an implementation agent must leave syntactically valid code, run focused tests,
record the exact dirty-file owner and next implementation action in
`docs/agent_context/active_implementation.md`, and locally commit when safe.
That one file is the only mutable implementation handoff; overwrite it in place
and do not create historical handoff copies. It must never contain secrets,
credential values, account identifiers, broker data, or generated payloads.

`runs/` artifacts remain generated and untracked. The live prohibition,
credential nondisclosure rules, offline-test defaults, finite paper caps,
reconciliation, and audit safeguards remain unchanged during takeover and
yield. Standing paper-operation authority follows this file and transfers
equally between collaborators; it does not require per-operation reapproval.

For the same local checkout, staged, unstaged, and untracked work can be
inherited directly after inspection. Across different checkouts or remote
sandboxes, uncommitted work is not transferable: only coherent feature-branch
commits followed by an authorized push, or an explicit patch transfer, are
reliable. No agent may assume access to another tool's private artifact
directory.

## Stop Conditions

Stop before continuing, staging, or committing if:

* A default test or offline verification process has a paper profile or broker credentials loaded.
* Required scope cannot be isolated from unrelated user work.
* Dependency-direction, offline verification, or network-safety checks fail.
* A change introduces broker/network access into default tests or weakens a safety guard.
* A paper endpoint/profile cannot be proven, a broker response is ambiguous, reconciliation fails, or an operation would exceed the effective finite paper caps.
* A change adds uncapped, unaudited, unreconciled, or non-paper submit, cancel, replace, close, or liquidate behavior.
* A credential value would be exposed, logged, persisted, returned, or copied outside its trusted provider/adapter boundary.
* Live-capital safety would be weakened.
* A read-only market-data fetch fails exact endpoint/method validation, exceeds a positive finite request/time/response-byte/row cap, or cannot produce sanitized provenance/receipt/audit evidence.
