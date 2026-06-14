# Assistant v1.14 - Offline Strategy Comparison Scaffold

- [x] Preserve Assistant v1 through v1.13A behavior and offline safety lockouts.
- [x] Add deterministic offline `strategy_comparison_scaffold` packet object.
- [x] Emit one-record `strategy_comparison_scaffold.jsonl` under the selected daily-lab output root.
- [x] Keep the scaffold as comparison metadata only: no new trading strategy, backtester, optimizer, broker adapter, strategy registry, broker read, broker mutation, paper submit, or live trading.
- [x] Compare the `spy_sma_50_200_control` control harness against deterministic placeholder candidate slots for momentum/trend, mean reversion, and volatility/regime-filter families.
- [x] Include deterministic comparison dimensions, required promotion evidence, and offline-only selected next safe action `build_candidate_strategy_evidence_template`.
- [x] Surface the scaffold in `operating_record.jsonl`, `manifest.jsonl`, `operating_brief.md`, `review_handoff.md`, `next_action_selector`, and `work_order_exports`.
- [x] Index `strategy_comparison_scaffold.jsonl` in manifest `indexed_artifacts`.
- [x] Add quality-gate and validation checks for scaffold artifact existence, manifest indexing, packet equality, Markdown mentions, required values, candidate slots, comparison dimensions, and safety lockouts.
- [x] Add unit coverage for scaffold generation, packet wiring, manifest indexing, Markdown references, selector/export links, and validation pass.
- [x] Complete required verification, including targeted test, safety guard group, offline verifier, v1.14 smoke sequence, preflight-gated full pytest, `git diff --check`, and final git status/reporting.
