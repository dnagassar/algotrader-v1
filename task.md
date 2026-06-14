# Assistant v1.16 - Materialized Candidate Evidence Requirements

- [x] Preserve Assistant v1 through v1.15 behavior and offline safety lockouts.
- [x] Add deterministic offline `candidate_evidence_requirements` packet object.
- [x] Emit one-record `candidate_evidence_requirements.jsonl` under the selected daily-lab output root.
- [x] Keep candidate strategies unimplemented, unpromoted, and not paper-ready.
- [x] Include deterministic evidence requirements for momentum/trend, mean reversion, and volatility/regime-filter candidate families.
- [x] Include shared evidence requirements, per-candidate missing evidence, promotion blockers, rejection triggers, next research artifacts, and offline-only selected next safe action.
- [x] Select offline-only next safe action `build_candidate_evidence_collection_plan`.
- [x] Surface the requirements in `operating_record.jsonl`, `manifest.jsonl`, `operating_brief.md`, `review_handoff.md`, `next_action_selector`, and `work_order_exports`.
- [x] Index `candidate_evidence_requirements.jsonl` in manifest `indexed_artifacts`.
- [x] Add quality-gate and validation checks for artifact existence, manifest indexing, packet equality, Markdown mentions, required values, candidate requirements, shared evidence, missing evidence, promotion/rejection gates, and safety lockouts.
- [x] Add unit coverage for requirements generation, packet wiring, manifest indexing, Markdown references, selector/export links, and validation pass.
