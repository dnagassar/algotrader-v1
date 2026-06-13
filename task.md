# Assistant v1.11 - Turnover and Cost Model Evidence Materialization

- [x] Preserve Assistant v1/v1.1/v1.2/v1.3/v1.4/v1.5/v1.6/v1.7/v1.8/v1.9/v1.10 brief, operating record, manifest, validation, history-delta, executive action queue, research board, review handoff, decision-ledger, selector, work-order, research-candidate queue, baseline-health, and baseline-evidence behavior.
- [x] Materialize deterministic local `turnover_summary.jsonl` from SPY SMA 50/200 signal-transition evidence under the selected daily-lab output root.
- [x] Materialize deterministic local `cost_model_summary.jsonl` as an assumptions-only cost-model inventory that explicitly refuses per-trade and total-cost estimates without fill, spread, notional, and commission-schedule sources.
- [x] Ingest turnover and cost-model artifacts into `baseline_evidence_metrics` with explicit artifact paths, hashes, parse statuses, ingest statuses, metric statuses, and remaining missing metric sources.
- [x] Preserve `paper_observation_summary` as the only broker-read hard-gated metric source after all deterministic offline metric artifacts are present.
- [x] Keep `profit_claim=none`, `paper_submit_readiness_status=not_ready_for_paper_submit`, `broker_state_not_observed`, and no broker/network/runtime dependency behavior intact.
- [x] Update quality-gate checks, research candidate queue, baseline-health evaluation, next-action selector, work-order exports, operating brief, review handoff, operating record, and manifest for v1.11 turnover/cost evidence.
- [x] Make prerequisite artifact chains explicit in generated work orders: daily packet output root, v1.10 prerequisite metric materialization, rerun daily packet for ingest, and leave paper observation hard-gated.
- [ ] Complete required verification, including targeted test, safety guard group, offline verifier, v1.11 smoke sequence, preflight-gated full pytest, `git diff --check`, and final git status/reporting.
