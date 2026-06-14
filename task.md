# Assistant v1.18 - Candidate Evidence Collection Status

- [x] Preserve Assistant v1 through v1.17 behavior and offline safety lockouts.
- [x] Add deterministic offline `candidate_evidence_collection_status` packet object.
- [x] Emit one-record `candidate_evidence_collection_status.jsonl` under the selected daily-lab output root.
- [x] Keep candidate strategies unimplemented, unpromoted, and not paper-ready.
- [x] Include deterministic status entries for momentum/trend, mean reversion, and volatility/regime-filter candidate families.
- [x] Include shared collection status items for data basis, hypothesis, feature, signal, risk, backtest, benchmark, cost, turnover, drawdown, regime, dependency, network, mutation, broker, LLM/agent, and paper-observation deferral evidence.
- [x] Include non-empty not-started, blocked, ready-to-collect, missing, and promotion-blocker evidence rollups.
- [x] Select offline-only next safe action `build_candidate_evidence_gap_summary`.
- [x] Surface the status object in `operating_record.jsonl`, `manifest.jsonl`, `operating_brief.md`, `review_handoff.md`, `next_action_selector`, and `work_order_exports`.
- [x] Index `candidate_evidence_collection_status.jsonl` in manifest `indexed_artifacts`.
- [x] Add quality-gate and validation checks for artifact existence, manifest indexing, packet equality, Markdown mentions, required values, candidate status entries, shared status entries, evidence item statuses, non-empty rollups, and safety lockouts.
- [x] Add unit coverage for status generation, packet wiring, manifest indexing, Markdown references, selector/export links, and validation pass.
