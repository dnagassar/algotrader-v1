import ast
from dataclasses import FrozenInstanceError, is_dataclass
from decimal import Decimal
from enum import Enum
from pathlib import Path
from types import ModuleType

import pytest

from algotrader.advisory import (
    AdvisoryLabel,
    OperatingBrief,
    OperatingBriefBoardSummary,
    build_operating_brief_board_summary,
    render_operating_brief_board_summary_markdown,
    render_operating_brief_markdown,
)
from tests.fixtures.advisory_operating_brief import (
    build_synthetic_advisory_operating_brief,
    build_synthetic_advisory_operating_brief_summary,
    expected_synthetic_operating_brief_board_summary_markdown,
    expected_synthetic_operating_brief_markdown,
)


MODULE_PATH = Path("tests/fixtures/advisory_operating_brief.py")

EXPECTED_IDS_BY_LABEL = {
    AdvisoryLabel.RESEARCH_ONLY: ("synthetic_research_candidate",),
    AdvisoryLabel.WATCHLIST_ONLY: ("synthetic_watchlist_candidate",),
    AdvisoryLabel.PAPER_ELIGIBLE: ("synthetic_paper_candidate",),
    AdvisoryLabel.LIVE_PROBE_ELIGIBLE: ("synthetic_live_probe_candidate",),
    AdvisoryLabel.LIVE_AUTHORIZED: ("synthetic_live_authorized_candidate",),
}

FORBIDDEN_SERIALIZED_FIELD_NAMES = {
    "account",
    "account_id",
    "allocation",
    "broker",
    "broker_order",
    "broker_order_id",
    "candidate_discovery",
    "client_order_id",
    "credential",
    "credentials",
    "execution_request",
    "fill",
    "fill_id",
    "order",
    "order_id",
    "orders",
    "portfolio",
    "portfolio_update",
    "position",
    "position_size",
    "rank",
    "ranking",
    "recommendation",
    "recommendations",
    "runtime",
    "score",
    "scoring",
    "submit_order",
    "target_weight",
}

FORBIDDEN_CONTENT_TERMS = (
    "account_id",
    "allocation",
    "alpaca",
    "api_key",
    "broker_order",
    "candidate discovery",
    "candidate_discovery",
    "credential",
    "execution_request",
    "fill_id",
    "http://",
    "https://",
    "market data",
    "market-data",
    "order_id",
    "password",
    "position_size",
    "price",
    "quantconnect",
    "ranking",
    "recommendation",
    "score",
    "scoring",
    "secret",
    "submit_order",
    "symbol",
    "target_weight",
    "ticker",
    "token",
    "vendor",
    "volume",
)

FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    "algotrader.persistence",
    "algotrader.portfolio",
    "algotrader.research",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "database",
    "duckdb",
    "http",
    "httpx",
    "ipynb",
    "langchain",
    "langgraph",
    "llm",
    "notebook",
    "numpy",
    "openai",
    "os",
    "pandas",
    "pathlib",
    "QuantConnect",
    "quantconnect",
    "random",
    "requests",
    "socket",
    "sqlmodel",
    "subprocess",
    "urllib",
    "vectorbt",
    "yfinance",
)

FORBIDDEN_CALL_NAMES = {
    "__import__",
    "connect",
    "create_order",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "eval",
    "exec",
    "getenv",
    "import_module",
    "importlib.import_module",
    "open",
    "os.environ.get",
    "os.getenv",
    "Path",
    "post",
    "random",
    "random.random",
    "read",
    "render_operating_brief_board_summary_markdown",
    "render_operating_brief_markdown",
    "request",
    "socket.socket",
    "submit_order",
    "time.time",
    "to_sql",
    "urlopen",
    "write",
}

FORBIDDEN_REFERENCE_NAMES = {
    "account",
    "account_id",
    "allocation",
    "alpaca",
    "api_key",
    "broker",
    "broker_order",
    "candidate_discovery",
    "client_order_id",
    "credential",
    "credentials",
    "execution",
    "execution_request",
    "fill",
    "fill_id",
    "market_data",
    "open",
    "order",
    "order_id",
    "os",
    "Path",
    "portfolio",
    "portfolio_update",
    "position",
    "position_size",
    "random",
    "rank",
    "ranking",
    "recommendation",
    "runtime",
    "score",
    "scoring",
    "socket",
    "submit_order",
    "target_weight",
}


def test_fixture_builders_return_expected_frozen_slotted_types() -> None:
    first_brief = build_synthetic_advisory_operating_brief()
    second_brief = build_synthetic_advisory_operating_brief()
    first_summary = build_synthetic_advisory_operating_brief_summary()
    second_summary = build_synthetic_advisory_operating_brief_summary()

    assert isinstance(first_brief, OperatingBrief)
    assert isinstance(first_summary, OperatingBriefBoardSummary)
    assert is_dataclass(first_brief)
    assert is_dataclass(first_summary)
    assert "__slots__" in OperatingBrief.__dict__
    assert "__slots__" in OperatingBriefBoardSummary.__dict__
    assert not hasattr(first_brief, "__dict__")
    assert not hasattr(first_summary, "__dict__")
    assert first_brief == second_brief
    assert first_summary == second_summary
    assert first_brief is not second_brief
    assert first_summary is not second_summary
    assert first_brief.dossiers[0] is not second_brief.dossiers[0]

    with pytest.raises(FrozenInstanceError):
        first_brief.brief_id = "changed"
    with pytest.raises(FrozenInstanceError):
        first_summary.research_queue_candidate_ids = ()


def test_summary_and_rendering_do_not_mutate_source_objects() -> None:
    brief = build_synthetic_advisory_operating_brief()
    before_brief = brief.to_dict()

    summary = build_operating_brief_board_summary(brief)
    before_summary = summary.to_dict()
    render_operating_brief_markdown(brief)
    render_operating_brief_board_summary_markdown(summary)

    assert brief.to_dict() == before_brief
    assert summary.to_dict() == before_summary
    assert brief.dossiers[0].uncertainty_factors == (
        "Synthetic source notes have not been reconciled against an approved "
        "evidence checklist.",
    )


def test_fixture_covers_every_advisory_label_with_expected_ids() -> None:
    brief = build_synthetic_advisory_operating_brief()
    summary = build_synthetic_advisory_operating_brief_summary()
    labels = tuple(dossier.advisory_label for dossier in brief.dossiers)

    assert labels == tuple(AdvisoryLabel)
    assert len(set(labels)) == len(tuple(AdvisoryLabel))
    assert dict(summary.candidate_ids_by_label) == EXPECTED_IDS_BY_LABEL
    assert summary.candidate_counts_by_label == tuple(
        (label, 1) for label in AdvisoryLabel
    )
    for label, expected_ids in EXPECTED_IDS_BY_LABEL.items():
        assert dict(summary.candidate_ids_by_label)[label] == expected_ids


def test_live_authorized_gate_and_non_actionable_authority_are_pinned() -> None:
    brief = build_synthetic_advisory_operating_brief()
    summary = build_synthetic_advisory_operating_brief_summary()
    strategy_by_id = {status.candidate_id: status for status in brief.strategy_statuses}
    risk_by_id = {status.candidate_id: status for status in brief.risk_statuses}
    dossier_by_id = {dossier.candidate_id: dossier for dossier in brief.dossiers}

    live_id = "synthetic_live_authorized_candidate"
    assert dossier_by_id[live_id].advisory_label is AdvisoryLabel.LIVE_AUTHORIZED
    assert strategy_by_id[live_id].live_authorized is True
    assert risk_by_id[live_id].live_authorized is True

    watchlist_id = "synthetic_watchlist_candidate"
    assert dossier_by_id[watchlist_id].advisory_label is AdvisoryLabel.WATCHLIST_ONLY
    assert strategy_by_id[watchlist_id].live_authorized is True
    assert risk_by_id[watchlist_id].live_authorized is True
    assert summary.watchlist_candidate_ids == (watchlist_id,)
    assert summary.live_authorized_candidate_ids == (live_id,)
    assert {
        status["candidate_id"]: status
        for status in summary.to_dict()["live_authorization_statuses"]
    }[watchlist_id] == {
        "candidate_id": watchlist_id,
        "advisory_label": "watchlist_only",
        "strategy_status_present": True,
        "strategy_live_authorized": True,
        "risk_status_present": True,
        "risk_live_authorized": True,
        "label_live_authorized": False,
    }


def test_fixture_serialization_is_deterministic_and_primitive() -> None:
    brief = build_synthetic_advisory_operating_brief()
    summary = build_synthetic_advisory_operating_brief_summary()

    first_brief_payload = brief.to_dict()
    second_brief_payload = brief.to_dict()
    first_summary_payload = summary.to_dict()
    second_summary_payload = summary.to_dict()

    assert first_brief_payload == second_brief_payload
    assert first_summary_payload == second_summary_payload
    assert first_brief_payload["as_of_date"] == "2026-01-15"
    assert first_summary_payload["as_of_date"] == "2026-01-15"
    _assert_primitive_json_compatible(first_brief_payload)
    _assert_primitive_json_compatible(first_summary_payload)
    for payload in (first_brief_payload, first_summary_payload):
        serialized_repr = repr(payload)
        assert " at 0x" not in serialized_repr
        assert "AdvisoryLabel." not in serialized_repr
        assert "OperatingBrief(" not in serialized_repr
        assert "OperatingBriefBoardSummary(" not in serialized_repr


def test_fixture_markdown_matches_pinned_expected_strings() -> None:
    brief = build_synthetic_advisory_operating_brief()
    summary = build_synthetic_advisory_operating_brief_summary()
    expected_brief_markdown = expected_synthetic_operating_brief_markdown()
    expected_summary_markdown = (
        expected_synthetic_operating_brief_board_summary_markdown()
    )

    assert expected_brief_markdown.endswith("\n")
    assert expected_summary_markdown.endswith("\n")
    assert render_operating_brief_markdown(brief) == expected_brief_markdown
    assert (
        render_operating_brief_board_summary_markdown(summary)
        == expected_summary_markdown
    )
    for text in (expected_brief_markdown, expected_summary_markdown):
        assert "advisory metadata only" in text
        assert "Uncertainty" in text
        assert "Failure" in text
        assert "Block" in text
        assert "Limitations" in text
        assert "Non-Claims" in text
    assert expected_summary_markdown.index("research_only") < (
        expected_summary_markdown.index("watchlist_only")
    )
    assert expected_brief_markdown.index("synthetic_research_candidate") < (
        expected_brief_markdown.index("synthetic_watchlist_candidate")
    )


def test_fixture_content_contains_no_runtime_trading_selection_or_vendor_data() -> None:
    brief_payload = build_synthetic_advisory_operating_brief().to_dict()
    summary_payload = build_synthetic_advisory_operating_brief_summary().to_dict()

    for payload in (brief_payload, summary_payload):
        assert _all_serialized_keys(payload).isdisjoint(
            FORBIDDEN_SERIALIZED_FIELD_NAMES
        )
        content = repr(payload).lower()
        for forbidden_term in FORBIDDEN_CONTENT_TERMS:
            assert forbidden_term not in content
        assert "$" not in content
        assert "://" not in content


def test_fixture_module_has_no_forbidden_imports_or_nondeterministic_calls() -> None:
    imports = _import_references()
    call_names = _call_names()
    reference_names = _referenced_names()

    violations = [
        module
        for module in imports
        if _matches_forbidden_prefix(module, FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []
    assert call_names.isdisjoint(FORBIDDEN_CALL_NAMES)
    assert reference_names.isdisjoint(FORBIDDEN_REFERENCE_NAMES)
    assert "render_operating_brief_markdown" not in imports
    assert "render_operating_brief_board_summary_markdown" not in imports


def _assert_primitive_json_compatible(value: object) -> None:
    assert not is_dataclass(value)
    assert not isinstance(value, Enum)
    assert not isinstance(value, tuple)
    assert not isinstance(value, set)
    assert not isinstance(value, Decimal)
    assert not callable(value)
    assert not isinstance(value, ModuleType)

    if value is None or type(value) in (str, bool, int, float):
        return

    if type(value) is list:
        for item in value:
            _assert_primitive_json_compatible(item)
        return

    if type(value) is dict:
        for key, item in value.items():
            assert type(key) is str
            _assert_primitive_json_compatible(item)
        return

    raise AssertionError(f"non-primitive serialized value: {type(value)!r}")


def _all_serialized_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key) for key in value}
        for item in value.values():
            keys.update(_all_serialized_keys(item))
        return keys

    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(_all_serialized_keys(item))
        return keys

    return set()


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


def _referenced_names() -> set[str]:
    names: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)

    return names


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
