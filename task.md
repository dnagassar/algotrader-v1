# Assistant v1.6 - Agent Work Order Export + Next Action Selector

- [x] Preserve Assistant v1/v1.1/v1.2/v1.3/v1.4/v1.5 brief, operating record, manifest, validation, history-delta, executive action queue, research board, review handoff, and decision-ledger outputs.
- [x] Add deterministic `next_action_selector` fields to the operating record, manifest, review handoff, and operating brief.
- [x] Add deterministic `work_order_exports` fields to the operating record, manifest, and review handoff.
- [x] Generate offline paste-ready work orders under `work_orders/` for GPT, Codex, Antigravity, and Claude.
- [x] Keep work orders as text artifacts only with no runtime LLM, agent, browser, broker, network, credential, paper-submit, or live-trading calls.
- [x] Preserve broker state unobserved, paper submit unauthorized, and live capital locked down.
- [x] Add focused unit coverage for selector routing, work-order exports, repair feedback, accepted review feedback, and command artifacts.
