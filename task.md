# Assistant v1.15 - Candidate Strategy Evidence Template

- [x] Preserve Assistant v1 through v1.14 behavior and offline safety lockouts.
- [x] Add deterministic offline `candidate_strategy_evidence_template` packet object.
- [x] Emit one-record `candidate_strategy_evidence_template.jsonl` under the selected daily-lab output root.
- [x] Keep candidate strategies unimplemented, unapproved, and not paper-ready.
- [x] Include deterministic candidate families for momentum/trend, mean reversion, and volatility/regime-filter slots.
- [x] Include required evidence sections, minimum promotion requirements, rejection criteria, baseline comparison requirements, offline artifact requirements, and human review questions.
- [x] Select offline-only next safe action `materialize_candidate_evidence_requirements`.
- [x] Surface the template in `operating_record.jsonl`, `manifest.jsonl`, `operating_brief.md`, `review_handoff.md`, `next_action_selector`, and `work_order_exports`.
- [x] Index `candidate_strategy_evidence_template.jsonl` in manifest `indexed_artifacts`.
- [x] Add quality-gate and validation checks for artifact existence, manifest indexing, packet equality, Markdown mentions, required values, candidate families, evidence sections, promotion/rejection gates, and safety lockouts.
- [x] Add unit coverage for template generation, packet wiring, manifest indexing, Markdown references, selector/export links, and validation pass.
- [x] Complete required verification, including targeted test, safety guard group, offline verifier, v1.15 smoke sequence, preflight-gated full pytest, `git diff --check`, and final git status/reporting.
