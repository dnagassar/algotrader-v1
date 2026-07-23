# Agent Workflow Settings - Optional ChatGPT Coordination Bridge

## Goal

Align the ChatGPT-to-agent handoff with the repository's current collaboration
model:

- `AGENTS.md` remains the sole repository authority.
- ChatGPT is an optional operator-facing coordination bridge.
- Current checkout and verification evidence outrank narrative or generated
  handoffs.
- Agent roles are dynamic rather than permanently assigned by model name.
- Exactly one implementation writer works in a working tree at a time.

## Deliverables

- Add copy-ready repo-specific ChatGPT workflow settings.
- Include the settings in the compact agent context.
- Update generated Mission Control prompts and JSON context with the current
  authority and collaboration contract.
- Remove stale wording that calls GPT the repository source of truth.
- Add deterministic tests for the revised prompt contract.

## Safety Contract

- No broker or network access.
- No credential loading or exposure.
- No paper or live mutation.
- No capital action or trading-mode change.
- Normal tests remain offline, deterministic, credential-free, network-free,
  and broker-free.
- Generated `runs/`, `.agent_inbox/`, and `docs/reviews/` artifacts remain
  non-authoritative and untracked.
