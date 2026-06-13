# Assistant v1.7 - Research Candidate Evidence Queue

- [x] Preserve Assistant v1/v1.1/v1.2/v1.3/v1.4/v1.5/v1.6 brief, operating record, manifest, validation, history-delta, executive action queue, research board, review handoff, decision-ledger, selector, and work-order outputs.
- [x] Add deterministic `research_candidate_queue` fields to the operating record, manifest, operating brief, review handoff, executive dashboard, selector metadata, and work-order exports.
- [x] Generate `research_candidate_queue.jsonl` under the selected output root as an offline deterministic JSONL artifact.
- [x] Rank candidates with fixed P0/P1/P2/P3 priority rules from packet evidence instead of manual intuition or SMA catalog expansion.
- [x] Seed evidence-building candidates for active-baseline health, benchmark comparison status, active-baseline evidence gaps, paper-lab observation readiness, strategy intake requirements, and a blocked future non-SMA research slot.
- [x] Keep broker state explicitly `broker_state_not_observed` / `offline_preview_only` with no broker reads, broker mutation, paper submit, live trading, network calls, external services, protected broker material, new accounts, or capital actions.
- [x] Route the next-action selector to the top safe queued research candidate only when the quality gate and decision ledger allow it.
- [x] Add focused unit coverage for queue shape, artifact generation, manifest indexing, markdown references, quality-gate validation, and selector routing.
