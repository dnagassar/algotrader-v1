# Assistant v1.31 — Execute Candidate Gap Closure Queue Item 011

Discovered from `src/algotrader/execution/etf_sma_daily_paper_lab.py` queue
generation (`_candidate_gap_closure_queue_items`,
`_candidate_gap_closure_queue_item`, and `_candidate_gap_closure_artifact`) and
confirmed by the generated offline `candidate_gap_closure_queue.jsonl` record.

## Item 011

- queue_item_id: `candidate_gap_closure_queue_item_011`
- action_id: `execute_candidate_gap_closure_queue_item_011`
- gap_id: `candidate_backtest_outputs_status`
- candidate_family: `Mean reversion candidate`
- candidate_family_id: `mean_reversion_candidate`
- closure_action: `materialize_candidate_backtest_benchmark_gap_packets`
- closure_objective: `Create candidate_backtest_result_packet.jsonl for Offline backtest output status using only deterministic offline packet evidence before any candidate implementation, promotion, paper observation, broker read, paper submit, or live trading.`
- expected_evidence_artifact: `candidate_backtest_result_packet.jsonl`
- next deterministic safe action after item 011: `execute_candidate_gap_closure_queue_item_012`

## Acceptance Criteria

- `candidate_backtest_result_packet.jsonl` is a deterministic offline JSONL artifact.
- Artifact records `source_queue_item_id=candidate_gap_closure_queue_item_011`.
- Artifact records `source_gap_id=candidate_backtest_outputs_status`.
- Artifact records `source_candidate_family_id=mean_reversion_candidate`.
- Artifact records `source_closure_action=materialize_candidate_backtest_benchmark_gap_packets`.
- Artifact records `source_expected_evidence_artifact=candidate_backtest_result_packet.jsonl`.
- Artifact preserves `broker_state_mode=broker_state_not_observed`.
- Artifact preserves `paper_submit_authorized=false`.
- Artifact preserves `profit_claim=none` and `safety_scope=offline_only`.
- Manifest, operating record, selector, work-order exports, brief, and handoff reference the generated artifact consistently.
- Unit coverage keeps default pytest offline, credential-free, broker-free, and network-free.

## Implementation Checklist

- [x] Advance candidate backtest result packet version/source constants to item 011.
- [x] Preserve the existing `candidate_backtest_result_packet.jsonl` artifact path and manifest/index wiring.
- [x] Update deterministic tests to assert item 011 source binding and item 012 next action.
- [x] Run targeted tests, safety guards, offline verification, smoke assertions, full pytest, and git hygiene checks.
