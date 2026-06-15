# Assistant v1.20 - Candidate Gap Closure Queue

- [x] Preserve Assistant v1 through v1.19 behavior and offline safety lockouts.
- [x] Add deterministic offline `candidate_gap_closure_queue` packet object.
- [x] Emit one-record `candidate_gap_closure_queue.jsonl` under the selected daily-lab output root.
- [x] Derive queue items from v1.19 ranked gap groups, highest-priority gaps, and next gap-closure actions only.
- [x] Keep candidate strategies unimplemented, unpromoted, and not paper-ready.
- [x] Include queue item fields for rank, priority, candidate family, gap group, gap id, closure action, closure objective, expected evidence artifact, recommended agent, allowed/forbidden scope, acceptance criteria, blockers, Daniel-action status, broker-state mode, paper-submit authorization, profit claim, and safety scope.
- [x] Preserve `broker_state_not_observed`, `paper_submit_authorized=false`, `daniel_action_required=false`, and `profit_claim=none`.
- [x] Preserve safety labels including `offline_only`, `research_only`, `signal_evaluation_only`, `not_live_authorized`, `paper_lab_only`, and `profit_claim=none`.
- [x] Select first concrete queue action `execute_candidate_gap_closure_queue_item_001` after queue construction.
- [x] Surface the queue object in `operating_record.jsonl`, `manifest.jsonl`, `operating_brief.md`, `review_handoff.md`, `next_action_selector`, and `work_order_exports`.
- [x] Index `candidate_gap_closure_queue.jsonl` in manifest `indexed_artifacts`.
- [x] Add quality-gate and validation checks for artifact existence, manifest indexing, packet equality, Markdown mentions, required queue fields, non-empty queue items, selected concrete action, and safety lockouts.
