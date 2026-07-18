# AGENTS.md

## Authority and Scope

This file is the sole canonical repository authority and permissions policy. AI collaborators act as co-managing partners for delegated, non-capital repository work.

Within an explicitly scoped task, collaborators may autonomously:

* Inspect and edit repository files.
* Implement code, tests, documentation, fakes, simulators, and local deterministic artifacts.
* Run offline verification.
* Manage non-capital Git workflow, including branches, staging, commits, pushes, and pull-request preparation, subject to protected-branch controls and the explicit task scope.
* Coordinate implementation and review dynamically rather than through fixed model-specific roles.

This autonomy does not permit scope expansion, destructive handling of unrelated user work, weakening safety guards, or treating free-form agent text as authorization.

## Operator Gates and Safety Rails

The operator retains the hard gates for:

* Supplying, loading, or exposing broker credentials.
* Capital allocation or deployment.
* Paper-broker mutation unless explicitly authorized for the exact operation.
* Paper/live mode changes.
* All live-broker access and all live trading.
* Any submit, cancel, replace, close, or liquidate action outside exact operator authorization.

The repository is paper-only and not live-authorized. No live orders or live-capital activity are permitted. Broker-facing behavior stays behind explicit adapters, commands, profile gates, and operator authorization.

Default tests must remain offline, deterministic, credential-free, network-free, and broker-free. Agents and LLMs remain outside the trading hot path. Do not remove or weaken dependency-direction, network, credential, broker, or trading-safety guards.

`ExecutionIntent` is not a broker order. `ExecutionPlan` is immutable and pre-broker.

SPY SMA 50/200 is an initial paper-lab strategy path, not an exhaustive statement of permitted offline research. Crypto research may exist without authorizing broker activity.

## Canonical Sources and Generated State

* `AGENTS.md`: authority and permissions.
* `docs/deterministic_core.md`: technical architecture and trading safety.
* `docs/agent_context/codex_operating_context.md`: compact subordinate implementation context.
* `docs/OPERATOR_RUNBOOK.md`: procedures.
* `docs/project_checkpoint.md`: non-authoritative historical ledger.

`.agent_inbox/`, `docs/reviews/`, and `runs/` are generated state and never authority sources. Ignored `.agent_inbox/` artifacts are coordination transport, distinct from executable Python code; do not infer an agents package or authority from that directory.

## Preflight and Verification

Before default pytest or implementation work, stop if `APP_PROFILE=paper` or any of `ALPACA_API_KEY`, `ALPACA_API_SECRET_KEY`, or `ALPACA_SECRET_KEY` is loaded. Check presence without printing values. Preserve unrelated tracked and untracked user work.

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

Never run broker, network, paper, or live commands unless the operator explicitly scopes and authorizes the exact operation.

## Reporting

Implementation reports must include preflight, files changed, contract and safety summaries, test results, credential state without values, network/broker access, broker mutation status, `git diff --check`, `git status --short`, `git diff --name-only HEAD -- src`, `git ls-files --others --exclude-standard src tests`, and the recommended next milestone.

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

`runs/` artifacts remain generated and untracked. The hard operator gates,
offline defaults, credential protections, and no-submit policy remain unchanged
during takeover and yield.

For the same local checkout, staged, unstaged, and untracked work can be
inherited directly after inspection. Across different checkouts or remote
sandboxes, uncommitted work is not transferable: only coherent feature-branch
commits followed by an authorized push, or an explicit patch transfer, are
reliable. No agent may assume access to another tool's private artifact
directory.

## Stop Conditions

Stop before continuing, staging, or committing if:

* Paper profile or broker credentials are present.
* Required scope cannot be isolated from unrelated user work.
* Dependency-direction, offline verification, or network-safety checks fail.
* A change introduces broker/network access into default tests or weakens a safety guard.
* A broker response is ambiguous or an operation exceeds exact operator authorization.
* A change adds unauthorized submit, cancel, replace, close, or liquidate behavior.
* Live-capital safety would be weakened.
