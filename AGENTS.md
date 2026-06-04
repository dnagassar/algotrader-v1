# AGENTS.md

## Project Mission

This repository supports deterministic algorithmic trading research, backtesting, and paper-trading tooling for personal use.

Near-term goal: build a working paper-trading lab quickly.

Long-term goal: supervised live trading across equities, crypto, and possibly options.

Live capital remains locked down.

## Operating Principle

Move fast, but keep hard safety rails.

Agents may build the machine. Agents may not operate the broker, allocate capital, or authorize live trading.

The human operator has final authority over:

* Broker credentials.
* Paper broker mutation.
* Live/paper mode changes.
* Capital deployment.
* Merge approval.

## Tool Roles

* ChatGPT project chat: source-of-truth router, milestone steering, prompt design, architecture decisions, and synthesis.
* Codex/local repo: default implementation tool for scoped code, tests, docs, and local verification.
* Antigravity/Gemini: broad repo inspection, orchestration critique, alternate implementation review, and sandboxed experiments.
* Claude: independent critique, safety review, and implementation review unless explicitly promoted.
* Manual/operator: credentialed paper snapshots, broker-facing runs, merge approval, and capital decisions.

## Fast-Track Development Mode

Prefer larger vertical slices over tiny ceremonial changes when safety boundaries are clear.

Good agent tasks:

* Build local paper-trading infrastructure.
* Add fake brokers and simulators.
* Add strategy registry components.
* Add local backtests and replay tools.
* Add portfolio ledger / PnL tracking.
* Add operator review artifacts.
* Add dashboards or reporting tools.
* Add tests that lock safety invariants.
* Update docs and checkpoints.

Avoid:

* Broad unreviewed rewrites.
* Hidden runtime dependencies.
* New broker mutation surfaces.
* Network access in default tests.
* Agent-controlled trading decisions.
* Agent-controlled paper/live mode changes.

## Safety Rules

Normal pytest must remain offline, credential-free, deterministic, and safe.

Before default pytest, stop if:

* `APP_PROFILE=paper`
* `ALPACA_API_KEY` is loaded
* `ALPACA_API_SECRET_KEY` is loaded
* `ALPACA_SECRET_KEY` is loaded
* paper/live broker credentials are active

Never print credential values.

Do not run broker, network, paper, or live commands unless the milestone explicitly scopes them.

No live trading or live orders.

No autonomous submit, cancel, replace, close, or liquidate behavior.

LLMs and agents are not allowed in the trading hot path.

## Agent Permission Matrix

Agents may:

* Inspect code.
* Edit source files.
* Add unit tests.
* Add docs.
* Run offline tests.
* Read local artifacts.
* Use fake brokers.
* Build simulators.
* Propose paper-trading infrastructure.
* Produce implementation reports.

Agents must not:

* Load Alpaca credentials.
* Submit paper or live orders.
* Cancel, replace, close, or liquidate orders.
* Query live/paper broker state unless explicitly scoped.
* Change live/paper mode.
* Deploy trading services to cloud.
* Remove safety guards.
* Weaken dependency-direction tests.
* Add network access to default pytest.
* Put LLMs in the trading hot path.

## Architecture

Canonical flow:

Market Data
→ Features
→ Screener
→ Signals
→ Risk
→ ExecutionIntent
→ ExecutionPlan
→ PlanningPolicy
→ Paper OMS / Broker Adapter
→ Paper Fills
→ Portfolio / Reconciliation Observation
→ Operating Brief

`ExecutionIntent` is not a broker order.

`ExecutionPlan` is immutable and pre-broker.

Research, signal, advisory, and LLM layers must not import execution, broker, SDK, network, or runtime trading dependencies.

Broker-facing behavior must stay behind explicit adapters, commands, profile gates, and operator approval.

## Current Strategy Path

Initial strategy path:

SPY equity daily long-only ETF SMA 50/200 trend filter.

Risk-on:
SMA50 > SMA200.

Risk-off:
SMA50 <= SMA200.

Insufficient history:
fewer than 200 usable as-of bars.

Initial allowlist:
SPY only.

Paper sizing:
tiny notional experiments only unless explicitly changed by the operator.

Labels:

* `paper_lab_only`
* `not_live_authorized`
* `profit_claim=none`

## Required Default Verification

For implementation work, run the relevant targeted tests first, then full verification.

Required checks:

```powershell
python -m pytest <targeted_test_file>
python -m pytest tests/unit/test_dependency_direction.py
python -m pytest
git diff --check
git status --short
git diff --name-only HEAD -- src
git ls-files --others --exclude-standard src tests
```

If scripts exist, prefer the project verification script:

```powershell
.\scripts\verify_offline.ps1
```

## Required Report Format

Every implementation report should include:

* Preflight
* Files changed
* Contract summary
* Safety summary
* Test results
* Credential state
* Network/broker access status
* Broker mutation status
* `git diff --check`
* `git status --short`
* `git diff --name-only HEAD -- src`
* `git ls-files --others --exclude-standard src tests`
* Recommended next milestone

## Stop Conditions

Stop before continuing if:

* Default pytest environment has paper profile or Alpaca credentials loaded.
* Dependency-direction or network-guard tests fail.
* A change introduces broker/network access into default tests.
* A change adds unauthorized submit/cancel/replace/close/liquidate behavior.
* A broker response is ambiguous.
* A paper/live command would run outside explicit milestone scope.
* Live-capital safety would be weakened.
* The agent attempts to remove or bypass safety tests.

## Preferred Development Style

Build faster by making the rails reusable.

Prefer:

* Larger scoped vertical slices.
* Fake brokers and simulators.
* Deterministic local artifacts.
* Strong safety tests.
* Operator approval packets.
* Clear handoff reports.
* Fast critique loops with Claude/Gemini/Antigravity.

Do not turn the system into an autonomous trading agent.

The goal is a fast, supervised paper-trading lab first, then progressively safer operator-approved broker integration.
