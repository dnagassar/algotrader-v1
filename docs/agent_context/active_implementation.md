# Active Implementation Checkpoint

## Status

The optional ChatGPT coordination-bridge settings update is complete and fully
verified. Durable repository authority remains in `AGENTS.md`; generated GPT
handoffs now present ChatGPT as operator-facing coordination rather than a
fixed source-of-truth role.

## Repository Reference State

- Branch: `main`
- Baseline HEAD and `origin/main` at preflight:
  `9d40560052b2fb155586d5e978e25fd21f241cae`
- Exactly one implementation writer was active in this worktree (`Codex`).
- No reset, clean, stash, rebase, restore, branch switch, broker command, or
  generated-artifact staging occurred.

## Implemented Contract

1. **Copy-ready ChatGPT settings**:
   `docs/agent_context/chatgpt_workflow_settings.md` defines the optional
   operator-facing bridge, evidence hierarchy, dynamic agent roles,
   single-writer rule, handoff fields, report-classification behavior, and hard
   safety gates.
2. **Authority alignment**: `AGENTS.md` remains the sole repository authority.
   Current branch, HEAD, status, diffs, and verification evidence outrank
   narrative reports and generated handoffs.
3. **Generated prompt contract**: Mission Control work-order prompts and GPT
   decision JSON now include an explicit authority/collaboration contract.
   GPT classification is operator-facing advice, not repository authority.
4. **Compatibility without fixed roles**: Existing `.agent_inbox/gpt` and GPT
   work-order names remain compatibility routing labels. Human-facing
   source-of-truth claims were removed, and selected model names are described
   as packet-specific routing hints.
5. **Compact context refresh**: The compact agent context now covers ChatGPT
   bridge sessions and reflects the merged V5.33.2 operational baseline rather
   than the stale V5.28 implementation slice.
6. **Regression coverage**: Tests pin the new prompt wording, JSON role and
   work-order type, authority fields, single-writer policy, operator gates, and
   absence of the stale fixed-authority wording.

## Changed Files

- `AGENTS.md`
- `task.md`
- `docs/agent_context/chatgpt_workflow_settings.md`
- `docs/agent_context/codex_operating_context.md`
- `docs/agent_context/active_implementation.md` (this file)
- `src/algotrader/execution/etf_sma_daily_paper_lab.py`
- `tests/unit/test_etf_sma_daily_paper_lab.py`

## Verification Evidence

- Credential/profile preflight: `APP_PROFILE_is_paper=False`; all checked
  `ALPACA_*` and `APCA_*` credential-presence booleans `False`; network and
  paper-integration escape hatches `False`. No values were printed.
- Focused prompt-contract tests: `PASS` (2 passed, 141 deselected).
- Full paper-lab unit file: `PASS` (143 passed in 696.29 seconds).
- Dependency-direction guard: `PASS` (34 passed).
- Default offline verifier: `PASS` (99 safety-guard tests passed).
- Full offline verifier: `PASS` (9,608 tests collected exactly once; 9,604
  passed, 4 skipped, 0 failures, 0 errors).
- Broker/network access: none.
- Broker mutation, paper submit, mode change, capital action, or live action:
  none.
- `git diff --check`: `PASS` before checkpoint finalization; rerun before
  commit.
- `git diff --name-only HEAD -- src`:
  `src/algotrader/execution/etf_sma_daily_paper_lab.py`.
- `git ls-files --others --exclude-standard src tests`: no output.

## Exact Next Action

Review the local settings commit and decide whether to push it or open a pull
request. For a plain ChatGPT session, copy the settings from
`docs/agent_context/chatgpt_workflow_settings.md` into the repo-specific chat
context. Do not perform broker reads, broker mutation, credential loading,
paper submit, live trading, capital allocation, or mode changes as part of that
review.
