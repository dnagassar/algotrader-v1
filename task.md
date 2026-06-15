# Assistant v1.21 - Candidate Risk Rule Status Artifact

- [x] Preserve Assistant v1 through v1.20 behavior and offline safety lockouts.
- [x] Add deterministic offline `candidate_risk_rule_status` packet object.
- [x] Emit one-record `candidate_risk_rule_status.jsonl` under the selected daily-lab output root.
- [x] Derive status from the candidate gap closure queue, candidate evidence gap summary, candidate evidence requirements, and candidate evidence collection artifacts.
- [x] Keep candidate strategies unimplemented, unpromoted, and not paper-ready.
- [x] Mark each candidate family risk-rule evidence incomplete when required evidence is missing.
- [x] Include candidate summaries for risk-rule status, sizing definition, drawdown/loss boundary, entry/exit boundary, stop/deactivation rule, data-quality risk rule, promotion blockers, missing evidence, closure action, and expected evidence artifact.
- [x] Preserve `broker_state_not_observed`, `paper_submit_authorized=false`, `daniel_action_required_now=false`, and `profit_claim=none`.
- [x] Preserve safety labels including `offline_only`, `research_only`, `signal_evaluation_only`, `not_live_authorized`, `paper_lab_only`, and `profit_claim=none`.
- [x] Record `source_queue_item_id=candidate_gap_closure_queue_item_001` and `source_gap_id=candidate_risk_rule_status`.
- [x] Advance the status artifact and packet-wide selector to `execute_candidate_gap_closure_queue_item_002`.
- [x] Surface the status object in `operating_record.jsonl`, `manifest.jsonl`, `operating_brief.md`, `review_handoff.md`, `next_action_selector`, and `work_order_exports`.
- [x] Index `candidate_risk_rule_status.jsonl` in manifest `indexed_artifacts`.
- [x] Add quality-gate and validation checks for artifact existence, manifest indexing, packet equality, Markdown mentions, required risk-rule status fields, explicit missing evidence, deterministic next action, and safety lockouts.
