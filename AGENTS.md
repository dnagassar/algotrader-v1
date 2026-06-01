# AGENTS.md

## Project Mission

This repository supports deterministic algorithmic trading research, backtesting,
and paper-trading tooling. Live capital remains locked down.

## Tool Roles

- ChatGPT project chat: milestone steering, prompt design, and synthesis.
- Codex/local repo: default implementation tool.
- Antigravity: repo health checks, review, and orchestration critique.
- Claude/Gemini: independent critique/review only unless explicitly promoted.
- Manual/operator: credentialed paper snapshots and broker-facing runs.

## Safety Rules

- Normal pytest must remain offline, credential-free, deterministic, and safe.
- Never print credential values.
- Stop before default pytest if `APP_PROFILE=paper` or Alpaca env vars are loaded.
- Do not run broker, network, or paper commands unless the milestone explicitly
  scopes them.
- No live trading or live orders.
- No autonomous submit, cancel, close, or liquidate behavior.
- LLMs and agents are not allowed in the trading hot path.

## Required Default Verification

- `python -m pytest <targeted_test_file>`
- `python -m pytest tests/unit/test_dependency_direction.py`
- `python -m pytest`
- `git diff --check`
- `git status --short`
- `git diff --name-only HEAD -- src`
- `git ls-files --others --exclude-standard src tests`

## Report Format

- Preflight
- Files changed
- Contract summary
- Safety summary
- Test results
- Recommended next milestone
