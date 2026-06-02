from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from decimal import Decimal
import json
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
import algotrader.execution.etf_sma_m369_operator_review as m369


MODULE_PATH = Path("src/algotrader/execution/etf_sma_m369_operator_review.py")
_RUN_ID = "m369_tiny_spy_paper_submit_operator_review"
_PREVIEW_RUN_ID = "m368b_spy_etf_sma_broker_preview_only"
_SNAPSHOT_RUN_ID = "m368b_fresh_read_only_paper_snapshot"
_PREVIEW_PATH = "runs/paper_lab/m368b_spy_etf_sma_broker_preview_only.jsonl"
_SNAPSHOT_PATH = "runs/paper_lab/m368b_fresh_read_only_paper_snapshot.jsonl"
_ALLOWED_IMPORTS = {
    "__future__",
    "collections.abc",
    "dataclasses",
    "decimal",
    "json",
    "pathlib",
    "typing",
    "algotrader.errors",
}
_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "alpaca",
    "alpaca_trade_api",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.portfolio",
    "algotrader.research",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
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
    "delete",
    "download",
    "liquidate",
    "post",
    "replace_order",
    "request",
    "retry",
    "socket.socket",
    "submit_order",
    "urlopen",
}


def test_ready_m368b_evidence_allows_separate_m370_submit_milestone() -> None:
    review = _ready_review()
    payload = review.to_dict()

    assert review.run_id == _RUN_ID
    assert review.decision == "ready_for_separate_tiny_spy_paper_submit_milestone"
    assert review.required_next_milestone == (
        "M370 - Tiny SPY paper submit only after explicit operator approval"
    )
    assert review.operator_review_ready is True
    assert review.separate_submit_milestone_required is True
    assert review.blockers == ()
    assert review.source_m368b_preview_run_id == _PREVIEW_RUN_ID
    assert review.source_m368b_snapshot_run_id == _SNAPSHOT_RUN_ID
    assert review.source_m368a_run_id == "m368a_offline_spy_etf_sma_next_experiment_review"
    assert review.source_m368a_signal_evidence_id == "m368a_offline_spy_etf_sma_fixture_signal"
    assert "deterministic fixture evidence" in review.source_m368a_signal_caveat
    assert review.snapshot_summary.cash == Decimal("1999.81")
    assert review.snapshot_summary.currency == "USD"
    assert review.snapshot_summary.position_count == 0
    assert review.snapshot_summary.position_symbols == ()
    assert review.snapshot_summary.open_order_count == 0
    assert review.snapshot_summary.recent_order_count == 0
    assert review.proposed_order == {
        "asset_class": "equity",
        "notional": "25.00",
        "order_type": "market",
        "side": "buy",
        "symbol": "SPY",
        "time_in_force": "day",
    }
    assert all(item.passed for item in review.checklist)
    assert [item.item for item in review.checklist] == [
        "M368A ready evidence present",
        "M368B fresh snapshot flat/clean",
        "M368B preview ready",
        "SPY-only scope",
        "cap <= 25.00",
        "no open orders",
        "no positions",
        "no broker mutation",
        "no submit authorization in this milestone",
        "separate submit milestone required",
    ]
    assert payload["snapshot_summary"]["credentials_redacted_present"] is True
    assert payload["submit_authorized"] is False
    assert payload["submitted"] is False
    assert payload["mutated"] is False


def test_m369_review_never_authorizes_submit_or_mutation() -> None:
    ready = _ready_review()
    blocked = m369.build_etf_sma_m369_operator_review(
        _record_with(("submit_authorized",), True),
        _ready_snapshot_summary(),
    )

    for review in (ready, blocked):
        assert review.labels == m369.ETF_SMA_M369_OPERATOR_REVIEW_LABELS
        assert review.submit_authorized is False
        assert review.submitted is False
        assert review.mutated is False
        assert review.broker_action_performed is False
        assert review.broker_preview_performed is False
        assert review.live_authorized is False
        assert review.profit_claim == "none"
        assert review.separate_submit_milestone_required is True
        assert "paper_submit_not_performed" in review.limitations


@pytest.mark.parametrize(
    ("path", "value", "expected_blocker"),
    (
        (("decision",), "stale_preview", "m368b_preview_decision_not_ready"),
        (
            ("required_next_milestone",),
            "M370 - Tiny SPY paper submit only after explicit operator approval",
            "m368b_required_next_milestone_unexpected",
        ),
        (("blockers",), ["stale"], "m368b_preview_blockers_present"),
        (("symbol",), "IVV", "symbol_not_spy"),
        (("notional_cap",), "25.01", "notional_cap_above_25"),
        (("submit_authorized",), True, "m368b_submit_authorized_not_false"),
        (("source_m368a_evidence_ids",), [], "m368a_source_evidence_ids_missing"),
        (
            ("preview_order", "symbol"),
            "IVV",
            "preview_order_symbol_not_spy",
        ),
    ),
)
def test_m368b_preview_gaps_block_m369_review(
    path: tuple[str, ...],
    value: object,
    expected_blocker: str,
) -> None:
    review = m369.build_etf_sma_m369_operator_review(
        _record_with(path, value),
        _ready_snapshot_summary(),
    )

    assert review.decision == "blocked_before_separate_tiny_spy_paper_submit_milestone"
    assert expected_blocker in review.blockers
    assert "operator_review_checklist_failed" in review.blockers
    assert review.operator_review_ready is False
    assert review.required_next_milestone == (
        "Resolve M369 operator-review blockers before any future submit milestone"
    )
    assert review.submit_authorized is False
    assert review.submitted is False
    assert review.mutated is False


@pytest.mark.parametrize(
    ("snapshot_kwargs", "expected_blocker"),
    (
        (
            {"position_count": 1, "position_symbols": ("SPY",)},
            "snapshot_positions_present",
        ),
        (
            {"open_order_count": 1, "recent_order_count": 1},
            "snapshot_open_orders_present",
        ),
        (
            {"credentials_redacted_present": False},
            "snapshot_credentials_not_redacted",
        ),
        (
            {"submitted": True},
            "snapshot_submitted_not_false",
        ),
        (
            {"account_observed": False},
            "snapshot_account_not_observed",
        ),
    ),
)
def test_m368b_snapshot_gaps_block_m369_review(
    snapshot_kwargs: dict[str, object],
    expected_blocker: str,
) -> None:
    snapshot = replace(_ready_snapshot_summary(), **snapshot_kwargs)

    review = m369.build_etf_sma_m369_operator_review(
        _ready_m368b_record(),
        snapshot,
    )

    assert review.decision == "blocked_before_separate_tiny_spy_paper_submit_milestone"
    assert expected_blocker in review.blockers
    assert "operator_review_checklist_failed" in review.blockers
    assert review.operator_review_ready is False


def test_loaders_require_one_preview_and_exact_snapshot_events(tmp_path: Path) -> None:
    preview_path = tmp_path / "m368b_preview.jsonl"
    snapshot_path = tmp_path / "m368b_snapshot.jsonl"
    _write_jsonl(preview_path, [_ready_m368b_record()])
    _write_snapshot_log(snapshot_path)

    preview = m369.load_m368b_preview_artifact_record(preview_path)
    snapshot = m369.load_m368b_snapshot_summary(snapshot_path)

    assert preview["run_id"] == _PREVIEW_RUN_ID
    assert snapshot.snapshot_run_id == _SNAPSHOT_RUN_ID
    assert snapshot.blockers() == ()

    _write_jsonl(preview_path, [_ready_m368b_record(), _ready_m368b_record()])
    with pytest.raises(ValidationError, match="exactly one"):
        m369.load_m368b_preview_artifact_record(preview_path)

    _write_jsonl(snapshot_path, _snapshot_records()[:-1])
    with pytest.raises(ValidationError, match="exactly four"):
        m369.load_m368b_snapshot_summary(snapshot_path)


def test_writer_and_rendering_are_deterministic_jsonl(tmp_path: Path) -> None:
    review = _ready_review()
    output_path = tmp_path / "runs" / "paper_lab" / "m369.jsonl"

    result = m369.write_etf_sma_m369_operator_review(
        review,
        m369.EtfSmaM369OperatorReviewWriteConfig(
            output_path=output_path,
            create_parent_dirs=True,
        ),
    )

    first = m369.render_etf_sma_m369_operator_review_json(review)
    second = m369.render_etf_sma_m369_operator_review_json(review)
    assert first == second
    text = output_path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert len(text.splitlines()) == 1
    payload = json.loads(text)
    assert payload["decision"] == "ready_for_separate_tiny_spy_paper_submit_milestone"
    assert payload["submit_authorized"] is False
    assert result.output_path == output_path
    assert result.record_count == 1
    assert result.submit_authorized is False


def test_text_render_includes_human_readable_checklist() -> None:
    text = m369.render_etf_sma_m369_operator_review_text(_ready_review())

    assert "M369 explicit operator review for tiny SPY paper submit" in text
    assert "checklist.M368A ready evidence present: pass" in text
    assert "checklist.separate submit milestone required: pass" in text
    assert "submit_authorized: false" in text


def test_review_is_frozen_slotted_and_primitive_only() -> None:
    review = _ready_review()

    assert hasattr(m369.EtfSmaM369OperatorReview, "__slots__")
    assert not hasattr(review, "__dict__")
    with pytest.raises(FrozenInstanceError):
        review.submitted = True

    field_names = {field.name for field in fields(m369.EtfSmaM369OperatorReview)}
    assert {
        "run_id",
        "source_m368b_preview_run_id",
        "source_m368b_snapshot_run_id",
        "source_m368a_signal_evidence_id",
        "snapshot_summary",
        "proposed_order",
        "checklist",
        "decision",
        "required_next_milestone",
        "operator_review_ready",
        "separate_submit_milestone_required",
        "submit_authorized",
        "submitted",
        "mutated",
        "blockers",
    }.issubset(field_names)
    _assert_primitive_only(review.to_dict())


def test_module_has_no_broker_sdk_network_or_mutation_calls() -> None:
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


def _ready_review() -> m369.EtfSmaM369OperatorReview:
    return m369.build_etf_sma_m369_operator_review(
        _ready_m368b_record(),
        _ready_snapshot_summary(),
    )


def _ready_snapshot_summary() -> m369.EtfSmaM369SnapshotSummary:
    return m369.EtfSmaM369SnapshotSummary(
        snapshot_run_id=_SNAPSHOT_RUN_ID,
        records_observed=True,
        event_types=(
            "paper_lab_snapshot_requested",
            "paper_lab_snapshot_account_observed",
            "paper_lab_snapshot_positions_observed",
            "paper_lab_snapshot_orders_observed",
        ),
        account_observed=True,
        positions_observed=True,
        orders_observed=True,
        cash=Decimal("1999.81"),
        currency="USD",
        position_count=0,
        position_symbols=(),
        open_order_count=0,
        recent_order_count=0,
        recent_order_query_metadata_complete=True,
        credentials_redacted_present=True,
        unavailable_observations=(),
        submitted=False,
        mutated=False,
        ok=True,
    )


def _ready_m368b_record() -> dict[str, object]:
    return {
        "account_observation_available": True,
        "allowlist": ["SPY"],
        "asset_class": "equity",
        "blockers": [],
        "broker_action_performed": False,
        "broker_preview_performed": False,
        "builder_name": "build_etf_sma_m368_paper_preview",
        "cash": "1999.81",
        "command": "etf-sma-m368-broker-preview-only",
        "currency": "USD",
        "decision": "ready_for_operator_review_before_tiny_spy_paper_submit",
        "fresh_paper_snapshot_summary": {
            "account_observation_available": True,
            "blockers": [],
            "cash": "1999.81",
            "currency": "USD",
            "fresh_snapshot_status": "read_only_snapshot_completed_for_manual_review",
            "mutated": False,
            "open_order_count": 0,
            "orders_observation_available": True,
            "position_count": 0,
            "position_symbols": [],
            "positions_observation_available": True,
            "recent_order_query_metadata_complete": True,
            "snapshot_evidence_id": _SNAPSHOT_RUN_ID,
            "snapshot_source": "fresh_read_only_paper_snapshot_run_log",
            "submitted": False,
            "unavailable_observations": [],
        },
        "labels": [
            "paper_lab_only",
            "preview_only",
            "not_live_authorized",
            "profit_claim=none",
        ],
        "local_payload_preview_performed": True,
        "mutated": False,
        "not_live_authorized": True,
        "notional": "25.00",
        "notional_cap": "25.00",
        "offline_signal_actionable_risk_on": True,
        "offline_signal_status": "bullish_risk_on",
        "open_order_count": 0,
        "order_type": "market",
        "orders_observation_available": True,
        "paper_only": True,
        "position_count": 0,
        "position_symbols": [],
        "positions_observation_available": True,
        "preview_only": True,
        "preview_order": {
            "asset_class": "equity",
            "notional": "25.00",
            "order_type": "market",
            "side": "buy",
            "symbol": "SPY",
            "time_in_force": "day",
        },
        "preview_version": "etf_sma_m368_paper_broker_preview_v1",
        "profit_claim": "none",
        "reason": (
            "M368A is ready, the paper snapshot is flat/clean, and only a "
            "local preview payload was rendered; M369 operator approval is "
            "required before any submit."
        ),
        "record_type": "etf_sma_m368_paper_broker_preview",
        "required_next_milestone": "M369 - Explicit operator review for tiny SPY paper submit",
        "run_id": _PREVIEW_RUN_ID,
        "side": "buy",
        "source_m368a_artifact_path": (
            "runs\\paper_lab\\m368a_offline_spy_etf_sma_next_experiment_review.jsonl"
        ),
        "source_m368a_decision": "ready_for_separate_broker_preview_milestone",
        "source_m368a_evidence_ids": [
            "m366_fresh_paper_lab_reset_snapshot",
            "m368a_offline_spy_etf_sma_fixture_signal",
        ],
        "source_m368a_mutated": False,
        "source_m368a_required_next_milestone": (
            "M368 - SPY ETF/SMA broker-facing preview-only milestone"
        ),
        "source_m368a_run_id": "m368a_offline_spy_etf_sma_next_experiment_review",
        "source_m368a_signal_evidence_id": "m368a_offline_spy_etf_sma_fixture_signal",
        "source_m368a_submit_authorized": False,
        "source_m368a_submitted": False,
        "submit_authorized": False,
        "submitted": False,
        "symbol": "SPY",
        "time_in_force": "day",
    }


def _record_with(path: tuple[str, ...], value: object) -> dict[str, object]:
    record = deepcopy(_ready_m368b_record())
    if len(path) == 1:
        record[path[0]] = value
        return record

    target = record
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return record


def _snapshot_records() -> tuple[dict[str, object], ...]:
    base = {
        "account_observation_available": True,
        "command": "paper-lab-snapshot",
        "error": "",
        "gate_summary": {"profile_gate": {"detail": "paper_profile_ready", "passed": True}},
        "mutated": False,
        "ok": True,
        "orders_observation_available": True,
        "position_count": 0,
        "position_symbols": [],
        "positions_observation_available": True,
        "recent_order_count": 0,
        "recent_order_query_after": None,
        "recent_order_query_asset_class_filter": "",
        "recent_order_query_attempted": True,
        "recent_order_query_available": True,
        "recent_order_query_contract_version": "paper_recent_order_query_v1",
        "recent_order_query_direction": "desc",
        "recent_order_query_limit": 100,
        "recent_order_query_metadata_complete": True,
        "recent_order_query_metadata_missing_fields": [],
        "recent_order_query_nested": False,
        "recent_order_query_returned_count": 0,
        "recent_order_query_side_filter": "",
        "recent_order_query_sort": "",
        "recent_order_query_source": "alpaca_sdk_client.get_orders",
        "recent_order_query_status_filter": "open",
        "recent_order_query_symbol_filter": "",
        "recent_order_query_until": None,
        "redaction": "credentials_redacted",
        "run_id": _SNAPSHOT_RUN_ID,
        "submitted": False,
        "unavailable_observations": [],
        "unavailable_reasons": {},
    }
    return (
        {
            **base,
            "event_type": "paper_lab_snapshot_requested",
        },
        {
            **base,
            "account": {"cash": "1999.81", "currency": "USD"},
            "event_type": "paper_lab_snapshot_account_observed",
        },
        {
            **base,
            "event_type": "paper_lab_snapshot_positions_observed",
            "positions": [],
        },
        {
            **base,
            "event_type": "paper_lab_snapshot_orders_observed",
            "recent_orders": [],
        },
    )


def _write_snapshot_log(path: Path) -> None:
    _write_jsonl(path, _snapshot_records())


def _write_jsonl(path: Path, records) -> None:
    path.write_text(
        "".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )


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
