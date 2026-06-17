# Assistant v1.32 — Execute Candidate Gap Closure Queue Item 012

Discovered from `src/algotrader/execution/etf_sma_daily_paper_lab.py` queue
generation (`_candidate_gap_closure_queue_items`,
`_candidate_gap_closure_queue_item`, and `_candidate_gap_closure_artifact`) and
confirmed by the generated offline `candidate_gap_closure_queue.jsonl` record.

## Item 012

- queue_item_id: `candidate_gap_closure_queue_item_012`
- action_id: `execute_candidate_gap_closure_queue_item_012`
- gap_id: `candidate_backtest_outputs_status`
- candidate_family: `Volatility or regime filter candidate`
- candidate_family_id: `volatility_or_regime_filter_candidate`
- closure_action: `materialize_candidate_backtest_benchmark_gap_packets`
- closure_objective: `Create candidate_backtest_result_packet.jsonl for Offline backtest output status using only deterministic offline packet evidence before any candidate implementation, promotion, paper observation, broker read, paper submit, or live trading.`
- expected_evidence_artifact: `candidate_backtest_result_packet.jsonl`
- next deterministic safe action after item 012: none; deterministic queue item 012 is rank 12 of 12, so the artifact records `candidate_gap_closure_queue_complete_no_remaining_items`

## Acceptance Criteria

- `candidate_backtest_result_packet.jsonl` is a deterministic offline JSONL artifact.
- Artifact records `source_queue_item_id=candidate_gap_closure_queue_item_012`.
- Artifact records `source_gap_id=candidate_backtest_outputs_status`.
- Artifact records `source_candidate_family_id=volatility_or_regime_filter_candidate`.
- Artifact records `source_closure_action=materialize_candidate_backtest_benchmark_gap_packets`.
- Artifact records `source_expected_evidence_artifact=candidate_backtest_result_packet.jsonl`.
- Artifact records `selected_next_safe_action=candidate_gap_closure_queue_complete_no_remaining_items`.
- Artifact records `next_candidate_backtest_result_packet_closure_actions=[]`.
- Artifact preserves `broker_state_mode=broker_state_not_observed`.
- Artifact preserves `paper_submit_authorized=false`.
- Artifact preserves `profit_claim=none` and `safety_scope=offline_only`.
- Manifest, operating record, selector, work-order exports, brief, and handoff reference the generated artifact consistently.
- Unit coverage keeps default pytest offline, credential-free, broker-free, and network-free.

## Implementation Checklist

- [x] Advance candidate backtest result packet version/source constants to item 012.
- [x] Preserve the existing `candidate_backtest_result_packet.jsonl` artifact path and manifest/index wiring.
- [x] Update deterministic tests to assert item 012 source binding and terminal queue-complete next action.
- [x] Run targeted tests, safety guards, offline verification, smoke assertions, full pytest, and git hygiene checks.
