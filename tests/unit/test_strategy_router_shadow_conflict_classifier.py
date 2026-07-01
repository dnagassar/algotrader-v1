from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.research.strategy_router_shadow_conflict_classifier import (
    build_strategy_router_shadow_conflict_classification,
    classify_strategy_router_shadow_replay_rows,
    read_strategy_router_shadow_replay_rows,
    write_strategy_router_shadow_conflict_artifacts,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT
    / "src"
    / "algotrader"
    / "research"
    / "strategy_router_shadow_conflict_classifier.py"
)
SCRIPT_PATH = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "run_strategy_router_shadow_conflict_classifier.py"
)


def test_classifier_reads_replay_rows_deterministically(tmp_path: Path) -> None:
    replay_jsonl = _write_jsonl(
        tmp_path / "replay.jsonl",
        [
            _row(
                "2026-01-02",
                sma_posture="bullish_risk_on",
                rsi_posture="overbought_cash_candidate",
                sma_action="buy",
                rsi_action="sell_close",
                candidate_conflict=True,
                candidate_disagreement=True,
                rsi_shadow_blocked=True,
                router_blocked_signal_ids=["spy_rsi_14_mean_reversion_shadow"],
            ),
            _row(
                "2026-01-03",
                sma_posture="neutral_no_trade",
                rsi_posture="neutral_no_trade",
                sma_state="no_trade",
                rsi_state="no_trade",
                sma_action="no_action",
                rsi_action="no_action",
                candidate_conflict=False,
                candidate_disagreement=False,
            ),
        ],
    )

    first = build_strategy_router_shadow_conflict_classification(replay_jsonl)
    second = build_strategy_router_shadow_conflict_classification(replay_jsonl)

    assert first == second
    assert read_strategy_router_shadow_replay_rows(replay_jsonl)[0]["data_as_of"] == (
        "2026-01-02T00:00:00+00:00"
    )
    assert first["summary"]["row_count"] == 2
    assert first["records"][0]["primary_bucket"] == (
        "sma_risk_on_rsi_overbought_conflict"
    )


def test_conflict_buckets_are_counted_correctly() -> None:
    classification = classify_strategy_router_shadow_replay_rows(
        [
            _row(
                "2026-01-02",
                sma_posture="bullish_risk_on",
                rsi_posture="overbought_cash_candidate",
                sma_action="buy",
                rsi_action="sell_close",
                candidate_conflict=True,
                candidate_disagreement=True,
                rsi_shadow_blocked=True,
                router_blocked_signal_ids=["spy_rsi_14_mean_reversion_shadow"],
            ),
            _row(
                "2026-01-03",
                sma_posture="defensive_risk_off",
                rsi_posture="oversold_buy_candidate",
                sma_action="sell_close",
                rsi_action="buy",
                candidate_conflict=True,
                candidate_disagreement=True,
                rsi_shadow_blocked=True,
                router_blocked_signal_ids=["spy_rsi_14_mean_reversion_shadow"],
            ),
            _row(
                "2026-01-04",
                sma_posture="bullish_risk_on",
                rsi_posture="neutral_no_trade",
                sma_action="buy",
                rsi_action="no_action",
                rsi_state="no_trade",
                candidate_conflict=False,
                candidate_disagreement=True,
            ),
            _row(
                "2026-01-05",
                sma_posture="insufficient_history",
                rsi_posture="neutral_no_trade",
                sma_state="no_trade",
                rsi_state="no_trade",
                sma_action="no_action",
                rsi_action="no_action",
                candidate_conflict=False,
                candidate_disagreement=False,
            ),
        ],
    )

    summary = classification["summary"]
    assert summary["conflict_row_count"] == 2
    assert summary["bucket_counts"]["sma_risk_on_rsi_overbought_conflict"] == 1
    assert summary["bucket_counts"]["sma_risk_off_rsi_oversold_conflict"] == 1
    assert summary["bucket_counts"]["router_conflict_block"] == 2
    assert summary["bucket_counts"]["rsi_neutral_sma_active_disagreement"] == 1
    assert summary["bucket_counts"]["no_action_alignment"] == 1
    assert summary["conflict_bucket_summary"]["router_conflict_block"] == {
        "count": 2,
        "representative_dates": ["2026-01-02", "2026-01-03"],
    }


def test_shadow_blocked_rows_remain_rsi_mutation_ineligible() -> None:
    classification = classify_strategy_router_shadow_replay_rows(
        [
            _row(
                "2026-01-02",
                sma_posture="bullish_risk_on",
                rsi_posture="oversold_buy_candidate",
                sma_action="buy",
                rsi_action="buy",
                candidate_conflict=False,
                candidate_disagreement=False,
                rsi_shadow_blocked=True,
                final_mutation_eligibility=True,
                router_blocked_signal_ids=["spy_rsi_14_mean_reversion_shadow"],
            ),
            _row(
                "2026-01-03",
                sma_posture="insufficient_history",
                rsi_posture="oversold_buy_candidate",
                sma_state="no_trade",
                rsi_state="trade_candidate",
                sma_action="no_action",
                rsi_action="buy",
                candidate_conflict=False,
                candidate_disagreement=True,
                rsi_shadow_blocked=True,
                final_mutation_eligibility=False,
                route_status="blocked",
                router_reason="all_candidates_blocked",
                adapter_status="blocked",
                adapter_reason="strategy_router_all_candidates_blocked",
            ),
        ],
    )

    records = classification["records"]
    summary = classification["summary"]
    assert all(record["rsi_mutation_eligible"] is False for record in records)
    assert summary["shadow_blocked_row_count"] == 2
    assert summary["rsi_shadow_mutation_eligible_count"] == 0
    assert summary["bucket_counts"]["rsi_shadow_trade_candidate_blocked"] == 2
    assert summary["bucket_counts"]["adapter_registry_shadow_block"] == 1
    assert summary["rsi_mutation_eligibility"] is False


def test_missing_or_invalid_replay_input_fails_cleanly(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="does not exist"):
        read_strategy_router_shadow_replay_rows(tmp_path / "missing.jsonl")

    invalid_jsonl = tmp_path / "invalid.jsonl"
    invalid_jsonl.write_text("{not-json}\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="line 1 must be valid JSON"):
        read_strategy_router_shadow_replay_rows(invalid_jsonl)

    missing_field_jsonl = tmp_path / "missing-field.jsonl"
    _write_jsonl(missing_field_jsonl, [{"record_type": "strategy_router_shadow_replay_row"}])
    with pytest.raises(ValidationError, match="missing required field"):
        read_strategy_router_shadow_replay_rows(missing_field_jsonl)

    with pytest.raises(ValidationError, match="local path"):
        read_strategy_router_shadow_replay_rows("https://example.test/replay.jsonl")


def test_output_summary_contains_required_fields_and_writes_artifacts(
    tmp_path: Path,
) -> None:
    classification = classify_strategy_router_shadow_replay_rows(
        [
            _row(
                "2026-01-02",
                sma_posture="bullish_risk_on",
                rsi_posture="overbought_cash_candidate",
                sma_action="buy",
                rsi_action="sell_close",
                candidate_conflict=True,
                candidate_disagreement=True,
                rsi_shadow_blocked=True,
                router_blocked_signal_ids=["spy_rsi_14_mean_reversion_shadow"],
            )
        ],
        source_replay_jsonl=tmp_path / "replay.jsonl",
    )

    paths = write_strategy_router_shadow_conflict_artifacts(
        classification,
        tmp_path / "runs" / "strategy_router_shadow_replay" / "latest",
    )
    summary = classification["summary"]

    required_fields = {
        "record_type",
        "schema_version",
        "classification_recommendation",
        "secondary_recommendations",
        "recommendation_categories",
        "evidence_classification",
        "row_count",
        "conflict_row_count",
        "shadow_blocked_row_count",
        "primary_bucket_counts",
        "bucket_counts",
        "bucket_representative_dates",
        "conflict_bucket_summary",
        "shadow_blocked_bucket_summary",
        "profit_claim",
        "broker_read_performed",
        "broker_mutation_performed",
        "paper_submit_performed",
        "live_endpoint_used",
        "network_fetch_performed",
        "strategy_promotion_performed",
        "threshold_change_performed",
        "rsi_promotion_status",
        "rsi_mutation_eligibility",
        "labels",
    }
    assert required_fields <= set(summary)
    assert summary["classification_recommendation"] == "keep_shadow"
    assert "needs_threshold_review" in summary["secondary_recommendations"]
    assert summary["recommendation_categories"]["reject_candidate"]["applies"] is False
    assert summary["profit_claim"] == "none"
    assert summary["broker_read_performed"] is False
    assert summary["broker_mutation_performed"] is False
    assert summary["paper_submit_performed"] is False
    assert summary["live_endpoint_used"] is False
    assert summary["network_fetch_performed"] is False
    assert summary["strategy_promotion_performed"] is False
    assert summary["threshold_change_performed"] is False
    assert summary["rsi_promotion_status"] == "shadow_only"
    assert summary["rsi_mutation_eligibility"] is False

    assert paths["conflict_summary_json"].name == "conflict_summary.json"
    assert paths["conflict_rows_jsonl"].name == "conflict_rows.jsonl"
    assert paths["conflict_brief_md"].name == "conflict_brief.md"
    assert json.loads(
        paths["conflict_summary_json"].read_text(encoding="utf-8")
    )["row_count"] == 1
    brief = paths["conflict_brief_md"].read_text(encoding="utf-8")
    assert "profit_claim: none" in brief
    assert "does not promote RSI" in brief


def test_classifier_introduces_no_broker_network_or_order_imports() -> None:
    forbidden_prefixes = (
        "algotrader.execution",
        "alpaca",
        "alpaca_trade_api",
        "httpx",
        "requests",
        "socket",
        "urllib",
    )
    forbidden_calls = {
        "cancel_order",
        "close_position",
        "connect",
        "create_order",
        "liquidate",
        "request",
        "socket.socket",
        "submit_order",
        "urlopen",
    }

    for path in (MODULE_PATH, SCRIPT_PATH):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        import_modules = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        ]
        import_modules.extend(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        call_names = {
            _call_name(node.func)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
        }

        assert not any(
            module == prefix or module.startswith(f"{prefix}.")
            for module in import_modules
            for prefix in forbidden_prefixes
        )
        assert call_names.isdisjoint(forbidden_calls)
        assert "submit_order" not in text


def _row(
    day: str,
    *,
    sma_posture: str,
    rsi_posture: str,
    sma_state: str = "trade_candidate",
    rsi_state: str = "trade_candidate",
    sma_action: str,
    rsi_action: str,
    candidate_conflict: bool,
    candidate_disagreement: bool,
    rsi_shadow_blocked: bool = False,
    final_mutation_eligibility: bool = False,
    route_status: str = "action_routed",
    router_reason: str = "single_promoted_candidate_routed",
    router_blocked_signal_ids: list[str] | None = None,
    adapter_status: str = "resolved",
    adapter_reason: str = "strategy_adapter_resolved",
) -> dict[str, object]:
    return {
        "record_type": "strategy_router_shadow_replay_row",
        "schema_version": "1",
        "run_id": "unit_shadow_replay",
        "data_as_of": f"{day}T00:00:00+00:00",
        "source_adjusted_close": "100",
        "sma_strategy": {
            "strategy_id": "spy_sma_50_200_training_wheel",
            "strategy_family": "long_only_broad_etf_sma_trend_filter",
            "symbol": "SPY",
            "posture": sma_posture,
            "state": sma_state,
            "signal_state": sma_state,
            "intended_action": sma_action,
            "intended_side": _side_for_action(sma_action),
            "promotion_status": "paper_mutation_candidate",
            "labels": ["paper_lab_only", "not_live_authorized", "profit_claim=none"],
            "blockers": [],
        },
        "rsi_strategy": {
            "strategy_id": "spy_rsi_14_mean_reversion_shadow",
            "strategy_family": "mean_reversion",
            "symbol": "SPY",
            "posture": rsi_posture,
            "state": rsi_state,
            "signal_state": rsi_state,
            "intended_action": rsi_action,
            "intended_side": _side_for_action(rsi_action),
            "promotion_status": "shadow_only",
            "labels": [
                "paper_lab_only",
                "shadow_only",
                "not_live_authorized",
                "profit_claim=none",
            ],
            "blockers": [],
        },
        "router_decision": {
            "route_status": route_status,
            "route_action": sma_action,
            "paper_mutation_allowed": final_mutation_eligibility,
            "reason": router_reason,
            "candidate_signal_ids": ["spy_sma_50_200_training_wheel"],
            "blocked_signal_ids": router_blocked_signal_ids or [],
            "labels": ["paper_lab_only", "not_live_authorized", "profit_claim=none"],
            "blockers": [],
        },
        "adapter_resolution": {
            "resolution_status": adapter_status,
            "reason": adapter_reason,
            "strategy_id": "spy_sma_50_200_training_wheel",
            "promotion_status": "paper_mutation_candidate",
            "adapter_id": "spy_sma_50_200_paper_mutation_adapter",
            "adapter_mode": "paper_mutation",
            "paper_mutation_allowed": final_mutation_eligibility,
            "blockers": [],
            "adapter": None,
        },
        "candidate_disagreement": candidate_disagreement,
        "candidate_conflict": candidate_conflict,
        "rsi_shadow_blocked_from_mutation": rsi_shadow_blocked,
        "final_mutation_eligibility": final_mutation_eligibility,
        "labels": [
            "paper_lab_only",
            "offline_only",
            "rsi_shadow_only_no_promotion",
            "not_live_authorized",
            "profit_claim=none",
        ],
        "profit_claim": "none",
        "broker_read_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_endpoint_used": False,
        "network_fetch_performed": False,
    }


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> Path:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def _side_for_action(action: str) -> str:
    if action == "buy":
        return "buy"
    if action == "sell_close":
        return "sell"
    return ""


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""
