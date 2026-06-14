# Assistant v1.17 - Candidate Evidence Collection Plan

- [x] Preserve Assistant v1 through v1.16R behavior and offline safety lockouts.
- [x] Add deterministic offline `candidate_evidence_collection_plan` packet object.
- [x] Emit one-record `candidate_evidence_collection_plan.jsonl` under the selected daily-lab output root.
- [x] Keep candidate strategies unimplemented, unpromoted, and not paper-ready.
- [x] Include deterministic collection-plan entries for momentum/trend, mean reversion, and volatility/regime-filter candidate families.
- [x] Include shared collection steps, data requirements, metric requirements, safety requirements, expected offline artifacts, and blocking conditions.
- [x] Select offline-only next safe action `build_candidate_evidence_collection_status`.
- [x] Surface the plan in `operating_record.jsonl`, `manifest.jsonl`, `operating_brief.md`, `review_handoff.md`, `next_action_selector`, and `work_order_exports`.
- [x] Index `candidate_evidence_collection_plan.jsonl` in manifest `indexed_artifacts`.
- [x] Add quality-gate and validation checks for artifact existence, manifest indexing, packet equality, Markdown mentions, required values, candidate collection plans, non-empty requirements, expected artifacts, and safety lockouts.
- [x] Add unit coverage for plan generation, packet wiring, manifest indexing, Markdown references, selector/export links, and validation pass.
