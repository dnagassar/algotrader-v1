# Assistant v1.9 - Baseline Evidence Metrics Snapshot

- [x] Preserve Assistant v1/v1.1/v1.2/v1.3/v1.4/v1.5/v1.6/v1.7/v1.8 brief, operating record, manifest, validation, history-delta, executive action queue, research board, review handoff, decision-ledger, selector, work-order, research-candidate queue, and baseline-health behavior.
- [x] Add deterministic `baseline_evidence_metrics` fields to the operating record, manifest, operating brief, review handoff, executive dashboard, and work-order exports.
- [x] Generate `baseline_evidence_metrics.jsonl` under the selected output root as an offline deterministic JSONL artifact.
- [x] Snapshot available packet-local metric sources and missing metric sources for the active `SPY` / `SMA 50/200` control harness without inventing performance metrics.
- [x] Preserve explicit `broker_state_not_observed`, `offline_preview_only`, `not_ready_for_paper_submit`, and `profit_claim=none` wording without broker reads, broker mutation, paper submit, live trading, network calls, external services, protected broker material, new accounts, or capital actions.
- [x] Reference the metrics snapshot status from `baseline_health_evaluation` while keeping health status conservative.
- [x] Route the research candidate queue, next-action selector, and work-order exports toward the next safe offline metric command/artifact when quality gate and decision ledger allow offline research.
- [x] Add quality-gate and unit-test coverage for baseline-evidence metrics schema, artifact generation, manifest indexing, markdown references, work-order references, and JSONL parity.
