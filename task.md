# Assistant v1.8 - Baseline Health Evaluation Packet

- [x] Preserve Assistant v1/v1.1/v1.2/v1.3/v1.4/v1.5/v1.6/v1.7 brief, operating record, manifest, validation, history-delta, executive action queue, research board, review handoff, decision-ledger, selector, work-order, and research-candidate queue behavior.
- [x] Add deterministic `baseline_health_evaluation` fields to the operating record, manifest, operating brief, review handoff, executive dashboard, and work-order exports.
- [x] Generate `baseline_health_evaluation.jsonl` under the selected output root as an offline deterministic JSONL artifact.
- [x] Evaluate the active `SPY` / `SMA 50/200` control harness from existing packet evidence only.
- [x] Preserve explicit `broker_state_not_observed` and `offline_preview_only` wording without broker reads, broker mutation, paper submit, live trading, network calls, external services, protected broker material, new accounts, or capital actions.
- [x] Report conservative baseline-health status, confidence/evidence gaps, required next artifacts, promotion/deprecation criteria, replacement research status, and the next safe offline test.
- [x] Route the research candidate queue and next-action work orders to the baseline-health next safe test when quality gate and decision ledger allow offline research.
- [x] Add quality-gate and unit-test coverage for baseline-health schema, artifact generation, manifest indexing, markdown references, work-order references, and JSONL parity.
