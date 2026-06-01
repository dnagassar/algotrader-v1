from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, is_dataclass
from decimal import Decimal
import json
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
import algotrader.orchestration.etf_sma_paper_probe_operator_review as m350


MODULE_PATH = Path("src/algotrader/orchestration/etf_sma_paper_probe_operator_review.py")
_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "decimal",
    "json",
    "pathlib",
    "typing",
    "algotrader.errors",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.portfolio",
    "algotrader.research",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "database",
    "duckdb",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
    "openai",
    "os",
    "pandas",
    "polygon",
    "QuantConnect",
    "quantconnect",
    "requests",
    "socket",
    "subprocess",
    "urllib",
    "vectorbt",
    "yfinance",
)
_FORBIDDEN_CALL_NAMES = {
    "ExecutionIntent",
    "ExecutionPlan",
    "cancel_order",
    "close_position",
    "connect",
    "create_order",
    "download",
    "liquidate",
    "post",
    "request",
    "socket.socket",
    "submit_order",
    "urlopen",
}


def test_ready_m349_preview_produces_ready_for_separate_future_probe_milestone() -> None:
    review = m350.build_etf_sma_paper_probe_operator_review(_ready_m349_record())
    payload = review.to_dict()

    assert review.review_status == "ready_for_separate_tiny_spy_paper_probe_milestone"
    assert review.approved_next_action == "scope_m351_tiny_spy_paper_probe_milestone_only"
    assert review.next_action == (
        "m351_separate_tiny_spy_paper_probe_scope_if_operator_approves"
    )
    assert review.source_m348_run_id == "m348_etf_sma_fresh_read_only_snapshot"
    assert review.source_m349_run_id == "m349_etf_sma_paper_preview_only"
    assert review.symbol == "SPY"
    assert review.asset_class == "equity"
    assert review.side == "buy"
    assert review.order_type == "market"
    assert review.time_in_force == "day"
    assert review.notional == Decimal("25.00")
    assert review.max_notional == Decimal("25.00")
    assert review.blockers == ()
    assert payload["notional"] == "25.00"
    assert payload["max_notional"] == "25.00"


@pytest.mark.parametrize(
    ("path", "value", "expected_blocker"),
    (
        (("prior_snapshot",), None, "m348_prior_snapshot_missing"),
        (
            ("prior_snapshot", "prior_snapshot_revalidation_state"),
            "insufficient_observation",
            "m348_nested_revalidation_state_not_usable",
        ),
        (
            ("prior_snapshot", "usable_for_manual_review"),
            False,
            "m348_not_usable_for_manual_review",
        ),
        (
            ("prior_snapshot", "account_observation_available"),
            False,
            "m348_account_observation_missing",
        ),
        (
            ("prior_snapshot", "positions_observation_available"),
            False,
            "m348_positions_observation_missing",
        ),
        (
            ("prior_snapshot", "orders_observation_available"),
            False,
            "m348_orders_observation_missing",
        ),
        (("symbol",), "IVV", "m349_symbol_not_spy"),
        (("asset_class",), "crypto", "m349_asset_class_not_equity"),
        (("submitted",), True, "m349_submitted_true"),
        (("mutated",), True, "m349_mutated_true"),
        (
            ("broker_action_performed",),
            True,
            "m349_broker_action_performed_true",
        ),
        (
            ("broker_preview_performed",),
            True,
            "m349_broker_preview_performed_true",
        ),
    ),
)
def test_m350_blocks_unsafe_m348_or_m349_evidence(
    path: tuple[str, ...],
    value: object,
    expected_blocker: str,
) -> None:
    record = _record_with(path, value)

    review = m350.build_etf_sma_paper_probe_operator_review(record)

    assert review.review_status == "blocked_from_tiny_spy_paper_probe_milestone"
    assert expected_blocker in review.blockers
    assert review.approved_next_action == "resolve_m350_operator_review_blockers"
    assert review.submit_allowed is False
    assert review.paper_probe_performed is False


def test_unexpected_positions_block_review() -> None:
    record = _ready_m349_record()
    record["prior_snapshot_position_count"] = 1
    record["prior_snapshot"]["position_count"] = 1
    record["prior_snapshot"]["position_symbols"] = ["MSFT"]

    review = m350.build_etf_sma_paper_probe_operator_review(record)

    assert review.review_status == "blocked_from_tiny_spy_paper_probe_milestone"
    assert "m348_unexpected_positions" in review.blockers


def test_recent_open_orders_block_review() -> None:
    record = _ready_m349_record()
    record["prior_snapshot_recent_open_order_count"] = 1
    record["prior_snapshot"]["recent_open_order_count"] = 1

    review = m350.build_etf_sma_paper_probe_operator_review(record)

    assert review.review_status == "blocked_from_tiny_spy_paper_probe_milestone"
    assert "m348_recent_open_orders_present" in review.blockers


def test_incomplete_recent_order_metadata_blocks_review() -> None:
    record = _ready_m349_record()
    record["prior_snapshot_recent_order_query_metadata_complete"] = False
    record["prior_snapshot"]["recent_order_query_metadata_complete"] = False

    review = m350.build_etf_sma_paper_probe_operator_review(record)

    assert review.review_status == "blocked_from_tiny_spy_paper_probe_milestone"
    assert "m348_recent_order_metadata_incomplete" in review.blockers


def test_notional_above_cap_blocks_without_authorizing_submit() -> None:
    record = _ready_m349_record()
    record["notional"] = "25.01"
    record["max_notional"] = "25.01"
    record["broker_payload_preview"]["notional"] = "25.01"

    review = m350.build_etf_sma_paper_probe_operator_review(record)

    assert review.review_status == "blocked_from_tiny_spy_paper_probe_milestone"
    assert "m349_notional_above_cap" in review.blockers
    assert "m349_max_notional_above_cap" in review.blockers
    assert review.notional == Decimal("25.01")
    assert review.submit_allowed is False
    assert review.submitted is False


def test_live_authorized_label_blocks_review() -> None:
    record = _ready_m349_record()
    record["labels"] = [*record["labels"], "live_authorized"]

    review = m350.build_etf_sma_paper_probe_operator_review(record)

    assert review.review_status == "blocked_from_tiny_spy_paper_probe_milestone"
    assert "live_authorized_evidence_present" in review.blockers
    assert review.live_authorized is False


def test_non_none_profit_claim_blocks_review() -> None:
    record = _ready_m349_record()
    record["source_record"]["source_preview"]["labels"] = [
        "paper_lab_only",
        "offline_execution_preview_only",
        "not_live_authorized",
        "profit_claim=positive",
    ]

    review = m350.build_etf_sma_paper_probe_operator_review(record)

    assert review.review_status == "blocked_from_tiny_spy_paper_probe_milestone"
    assert "non_none_profit_claim_present" in review.blockers
    assert review.profit_claim == "none"


def test_output_never_authorizes_submit_now_and_requires_future_probe_milestone() -> None:
    ready_review = m350.build_etf_sma_paper_probe_operator_review(_ready_m349_record())
    blocked_review = m350.build_etf_sma_paper_probe_operator_review(
        _record_with(("submitted",), True)
    )

    for review in (ready_review, blocked_review):
        assert review.operator_review_required is True
        assert review.separate_future_probe_milestone_required is True
        assert review.submit_allowed is False
        assert review.submitted is False
        assert review.mutated is False
        assert review.broker_action_performed is False
        assert review.broker_preview_performed is False
        assert review.paper_probe_performed is False
        assert review.live_authorized is False
        assert "submit" not in review.approved_next_action


def test_loader_reviews_one_local_m349_jsonl_record(tmp_path: Path) -> None:
    run_log = tmp_path / "m349.jsonl"
    run_log.write_text(
        json.dumps(_ready_m349_record(), sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    review = m350.load_etf_sma_paper_probe_operator_review_from_jsonl(run_log)

    assert review.review_status == "ready_for_separate_tiny_spy_paper_probe_milestone"
    assert review.source_m349_run_id == "m349_etf_sma_paper_preview_only"


def test_json_rendering_is_deterministic_and_primitive_only() -> None:
    review = m350.build_etf_sma_paper_probe_operator_review(_ready_m349_record())

    first = m350.render_etf_sma_paper_probe_operator_review_json(review)
    second = m350.render_etf_sma_paper_probe_operator_review_json(review)

    assert first == second
    payload = json.loads(first)
    assert payload["review_status"] == (
        "ready_for_separate_tiny_spy_paper_probe_milestone"
    )
    assert payload["submit_allowed"] is False
    assert payload["paper_probe_performed"] is False
    _assert_primitive_only(payload)


def test_review_is_frozen_slotted_and_has_required_output_fields() -> None:
    review = m350.build_etf_sma_paper_probe_operator_review(_ready_m349_record())

    assert hasattr(m350.EtfSmaPaperProbeOperatorReview, "__slots__")
    assert not hasattr(review, "__dict__")
    with pytest.raises(FrozenInstanceError):
        review.submitted = True

    field_names = {field.name for field in fields(m350.EtfSmaPaperProbeOperatorReview)}
    assert {
        "review_status",
        "approved_next_action",
        "source_m348_run_id",
        "source_m349_run_id",
        "symbol",
        "asset_class",
        "side",
        "notional",
        "max_notional",
        "operator_review_required",
        "separate_future_probe_milestone_required",
        "submit_allowed",
        "submitted",
        "mutated",
        "broker_action_performed",
        "broker_preview_performed",
        "paper_probe_performed",
        "live_authorized",
        "next_action",
        "blockers",
        "limitations",
    }.issubset(field_names)


def test_module_has_no_broker_sdk_network_or_credential_imports() -> None:
    imports = _import_references()

    assert imports == _ALLOWED_IMPORTS
    assert [
        module
        for module in imports
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)
    source = MODULE_PATH.read_text(encoding="utf-8").lower()
    assert "alpaca" not in source
    assert "socket" not in source


def test_module_does_not_use_execution_intent_or_execution_plan() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")

    for forbidden in (
        "Execution" + "Intent",
        "Execution" + "Plan",
        "execution_" + "intent",
        "execution_" + "plan",
    ):
        assert forbidden not in source

    field_names = {field.name for field in fields(m350.EtfSmaPaperProbeOperatorReview)}
    assert "execution_" + "intent" not in field_names
    assert "execution_" + "plan" not in field_names


def test_loader_rejects_ambiguous_jsonl_records(tmp_path: Path) -> None:
    run_log = tmp_path / "m349.jsonl"
    record = _ready_m349_record()
    run_log.write_text(
        "".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
            for _ in range(2)
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="exactly one"):
        m350.load_etf_sma_paper_probe_operator_review_from_jsonl(run_log)


def _ready_m349_record() -> dict[str, object]:
    labels = [
        "paper_lab_only",
        "signal_evaluation_only",
        "broker_facing_preview_only",
        "not_live_authorized",
        "profit_claim=none",
    ]
    artifact_labels = [
        "paper_lab_only",
        "offline_execution_preview_only",
        "local_preview_jsonl_artifact_only",
        "not_live_authorized",
        "profit_claim=none",
    ]
    source_preview_labels = [
        "paper_lab_only",
        "offline_execution_preview_only",
        "not_live_authorized",
        "profit_claim=none",
    ]
    source_signal_labels = [
        "paper_lab_only",
        "signal_evaluation_only",
        "not_live_authorized",
        "profit_claim=none",
    ]
    prior_snapshot = {
        "account_observation_available": True,
        "credential_leak_evidence": False,
        "credentials_redacted_present": True,
        "fresh_snapshot_status": "read_only_snapshot_completed_for_manual_review",
        "live_profile_evidence": False,
        "mutated": False,
        "orders_observation_available": True,
        "position_count": 0,
        "position_symbols": [],
        "positions_observation_available": True,
        "prior_snapshot_revalidation_state": "usable_for_manual_review",
        "prior_snapshot_run_id": "m348_etf_sma_fresh_read_only_snapshot",
        "recent_open_order_count": 0,
        "recent_order_query_metadata_complete": True,
        "snapshot_records_observed": True,
        "submitted": False,
        "unavailable_observations": [],
        "usable_for_manual_review": True,
    }
    return {
        "accepted_for_broker_payload_preview": True,
        "asset_class": "equity",
        "block_reason": "",
        "blocked": False,
        "broker_action_performed": False,
        "broker_payload_preview": {
            "asset_class": "equity",
            "notional": "25.00",
            "order_type": "market",
            "side": "buy",
            "symbol": "SPY",
            "time_in_force": "day",
        },
        "broker_preview_performed": False,
        "labels": labels,
        "local_payload_preview_performed": True,
        "max_notional": "25.00",
        "mutated": False,
        "next_action": "m350_operator_review_before_any_tiny_spy_paper_probe",
        "notional": "25.00",
        "order_type": "market",
        "preview_status": "broker_facing_local_payload_previewed",
        "preview_version": "etf_sma_paper_broker_preview_v1",
        "prior_snapshot": prior_snapshot,
        "prior_snapshot_position_count": 0,
        "prior_snapshot_position_symbols": [],
        "prior_snapshot_recent_open_order_count": 0,
        "prior_snapshot_recent_order_query_metadata_complete": True,
        "prior_snapshot_revalidation_state": "usable_for_manual_review",
        "prior_snapshot_run_id": "m348_etf_sma_fresh_read_only_snapshot",
        "profit_claim": "none",
        "quantity": None,
        "record_type": "etf_sma_paper_broker_preview",
        "run_id": "m349_etf_sma_paper_preview_only",
        "side": "buy",
        "signal_posture": "bullish_risk_on",
        "skipped": False,
        "source_record": {
            "labels": artifact_labels,
            "profit_claim": "none",
            "source_preview": {
                "labels": source_preview_labels,
                "profit_claim": "none",
            },
            "source_signal_result": {
                "labels": source_signal_labels,
                "profit_claim": "none",
            },
        },
        "source_record_labels": artifact_labels,
        "submit_allowed": False,
        "submitted": False,
        "symbol": "SPY",
        "time_in_force": "day",
    }


def _record_with(path: tuple[str, ...], value: object) -> dict[str, object]:
    record = deepcopy(_ready_m349_record())
    if len(path) == 1:
        if value is None:
            record.pop(path[0], None)
        else:
            record[path[0]] = value
        return record

    target = record
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return record


def _assert_primitive_only(value: object) -> None:
    assert not is_dataclass(value)
    assert not isinstance(value, (tuple, set, Decimal))
    assert not callable(value)

    if isinstance(value, dict):
        for key, item in value.items():
            assert type(key) is str
            _assert_primitive_only(item)
        return

    if isinstance(value, list):
        for item in value:
            _assert_primitive_only(item)
        return

    assert value is None or type(value) in (str, int, bool)


def _tree() -> ast.AST:
    return ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))


def _import_references() -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def _matches_forbidden_prefix(module: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(
        module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )


def _call_names() -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""
