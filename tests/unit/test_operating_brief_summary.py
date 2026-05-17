import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from pathlib import Path
from types import ModuleType

import pytest

from algotrader.advisory import (
    AdvisoryLabel,
    OperatingBrief,
    OperatingBriefBoardSummary,
    ResearchCandidateDossier,
    RiskAuthorityStatus,
    StrategyEligibilityStatus,
    build_operating_brief_board_summary,
)
from algotrader.errors import ValidationError


MODULE_PATH = Path("src/algotrader/advisory/operating_brief_summary.py")

_FORBIDDEN_IMPORT_PREFIXES = (
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
    "httpx",
    "ipynb",
    "langchain",
    "langgraph",
    "llm",
    "notebook",
    "openai",
    "pandas",
    "QuantConnect",
    "quantconnect",
    "requests",
    "socket",
    "sqlmodel",
    "urllib",
    "vectorbt",
    "yfinance",
)

_FORBIDDEN_CALL_NAMES = {
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
    "os.getenv",
    "post",
    "read",
    "request",
    "socket.socket",
    "submit_order",
    "time.time",
    "to_sql",
    "urlopen",
    "write",
}

_FORBIDDEN_REFERENCE_NAMES = {
    "Account",
    "AlpacaPaperBroker",
    "BrokerOrderResult",
    "ExecutionIntent",
    "ExecutionPlan",
    "Fill",
    "LocalBroker",
    "PortfolioState",
    "Position",
    "ProposedOrder",
    "account_id",
    "allocation",
    "alpaca",
    "broker_order",
    "execution_request",
    "fill_id",
    "market_data",
    "order_id",
    "portfolio_update",
    "position_size",
    "submit_order",
    "target_weight",
}

_FORBIDDEN_FIELD_NAMES = {
    "account",
    "account_id",
    "allocation",
    "broker_order",
    "execution_request",
    "fill",
    "fill_id",
    "order",
    "order_id",
    "portfolio",
    "portfolio_update",
    "rank",
    "ranking",
    "recommendation",
    "recommendations",
    "runtime",
    "score",
    "scoring",
    "submit_order",
    "target_weight",
    "position_size",
}


def dossier(**overrides: object) -> ResearchCandidateDossier:
    values: dict[str, object] = {
        "candidate_id": "candidate-001",
        "title": "ETF trend research candidate",
        "summary": "Advisory metadata for future review only.",
        "advisory_label": AdvisoryLabel.RESEARCH_ONLY,
        "uncertainty_factors": ("Input provenance is not yet reviewed.",),
        "failure_modes": ("Regime shift could invalidate assumptions.",),
        "next_questions": ("What deterministic evidence package is required?",),
        "limitations": ("No trading action is authorized.",),
    }
    values.update(overrides)
    return ResearchCandidateDossier(**values)


def strategy_status(**overrides: object) -> StrategyEligibilityStatus:
    values: dict[str, object] = {
        "candidate_id": "candidate-001",
        "mandate_id": None,
        "mandate_approved": False,
        "evidence_approved": False,
        "evidence_refs": (),
        "paper_eligible": False,
        "live_probe_eligible": False,
        "live_authorized": False,
        "blocking_reasons": ("No approved strategy mandate.",),
        "limitations": ("Advisory status only.",),
    }
    values.update(overrides)
    return StrategyEligibilityStatus(**values)


def paper_strategy_status(**overrides: object) -> StrategyEligibilityStatus:
    values: dict[str, object] = {
        "mandate_id": "mandate-paper-001",
        "mandate_approved": True,
        "evidence_approved": True,
        "evidence_refs": ("evidence-package-001",),
        "paper_eligible": True,
        "live_probe_eligible": False,
        "live_authorized": False,
        "blocking_reasons": ("Live probe mandate is not approved.",),
    }
    values.update(overrides)
    return strategy_status(**values)


def live_probe_strategy_status(**overrides: object) -> StrategyEligibilityStatus:
    values: dict[str, object] = {
        "mandate_id": "mandate-probe-001",
        "mandate_approved": True,
        "evidence_approved": True,
        "evidence_refs": ("evidence-package-001",),
        "paper_eligible": True,
        "live_probe_eligible": True,
        "live_authorized": False,
        "blocking_reasons": ("Live strategy authorization is not approved.",),
    }
    values.update(overrides)
    return strategy_status(**values)


def live_strategy_status(**overrides: object) -> StrategyEligibilityStatus:
    values: dict[str, object] = {
        "mandate_id": "mandate-live-001",
        "mandate_approved": True,
        "evidence_approved": True,
        "evidence_refs": ("evidence-package-001",),
        "paper_eligible": True,
        "live_probe_eligible": True,
        "live_authorized": True,
        "blocking_reasons": (),
    }
    values.update(overrides)
    return strategy_status(**values)


def risk_status(**overrides: object) -> RiskAuthorityStatus:
    values: dict[str, object] = {
        "candidate_id": "candidate-001",
        "authority_id": None,
        "paper_allowed": False,
        "live_probe_allowed": False,
        "live_authorized": False,
        "blocking_reasons": ("No risk authority is approved.",),
        "limitations": ("Authority metadata grants no trading action by itself.",),
    }
    values.update(overrides)
    return RiskAuthorityStatus(**values)


def paper_risk_status(**overrides: object) -> RiskAuthorityStatus:
    values: dict[str, object] = {
        "authority_id": "risk-paper-001",
        "paper_allowed": True,
        "live_probe_allowed": False,
        "live_authorized": False,
        "blocking_reasons": ("Live probe authority is not approved.",),
    }
    values.update(overrides)
    return risk_status(**values)


def live_probe_risk_status(**overrides: object) -> RiskAuthorityStatus:
    values: dict[str, object] = {
        "authority_id": "risk-probe-001",
        "paper_allowed": True,
        "live_probe_allowed": True,
        "live_authorized": False,
        "blocking_reasons": ("Live authority is not approved.",),
    }
    values.update(overrides)
    return risk_status(**values)


def live_risk_status(**overrides: object) -> RiskAuthorityStatus:
    values: dict[str, object] = {
        "authority_id": "risk-live-001",
        "paper_allowed": True,
        "live_probe_allowed": True,
        "live_authorized": True,
        "blocking_reasons": (),
    }
    values.update(overrides)
    return risk_status(**values)


def brief(**overrides: object) -> OperatingBrief:
    values: dict[str, object] = {
        "brief_id": "brief-2026-05-17",
        "as_of_date": date(2026, 5, 17),
        "dossiers": (dossier(),),
        "strategy_statuses": (strategy_status(),),
        "risk_statuses": (risk_status(),),
        "limitations": ("Advisory metadata only.",),
    }
    values.update(overrides)
    return OperatingBrief(**values)


def board_brief() -> OperatingBrief:
    candidates = (
        dossier(candidate_id="candidate-research-a"),
        dossier(
            candidate_id="candidate-watchlist",
            advisory_label=AdvisoryLabel.WATCHLIST_ONLY,
        ),
        dossier(
            candidate_id="candidate-paper",
            advisory_label=AdvisoryLabel.PAPER_ELIGIBLE,
        ),
        dossier(
            candidate_id="candidate-probe",
            advisory_label=AdvisoryLabel.LIVE_PROBE_ELIGIBLE,
        ),
        dossier(
            candidate_id="candidate-live",
            advisory_label=AdvisoryLabel.LIVE_AUTHORIZED,
        ),
        dossier(candidate_id="candidate-research-b"),
    )

    return brief(
        dossiers=candidates,
        strategy_statuses=(
            strategy_status(candidate_id="candidate-research-a"),
            strategy_status(
                candidate_id="candidate-watchlist",
                blocking_reasons=("Watchlist strategy review is incomplete.",),
            ),
            paper_strategy_status(candidate_id="candidate-paper"),
            live_probe_strategy_status(candidate_id="candidate-probe"),
            live_strategy_status(candidate_id="candidate-live"),
            strategy_status(
                candidate_id="candidate-research-b",
                blocking_reasons=("Second research strategy review is incomplete.",),
            ),
        ),
        risk_statuses=(
            risk_status(candidate_id="candidate-research-a"),
            risk_status(
                candidate_id="candidate-watchlist",
                blocking_reasons=("Watchlist risk review is incomplete.",),
            ),
            paper_risk_status(candidate_id="candidate-paper"),
            live_probe_risk_status(candidate_id="candidate-probe"),
            live_risk_status(candidate_id="candidate-live"),
            risk_status(
                candidate_id="candidate-research-b",
                blocking_reasons=("Second research risk review is incomplete.",),
            ),
        ),
    )


def test_builder_accepts_only_operating_brief_and_returns_frozen_slotted_summary() -> None:
    with pytest.raises(ValidationError, match="OperatingBrief"):
        build_operating_brief_board_summary({"brief_id": "not-a-brief"})

    summary = build_operating_brief_board_summary(brief())

    assert isinstance(summary, OperatingBriefBoardSummary)
    assert is_dataclass(summary)
    assert not hasattr(summary, "__dict__")
    assert "__slots__" in OperatingBriefBoardSummary.__dict__
    with pytest.raises(FrozenInstanceError):
        summary.research_queue_candidate_ids = ()

    for field in fields(summary):
        if field.name != "as_of_date":
            assert isinstance(getattr(summary, field.name), tuple)


def test_builder_preserves_ordering_and_does_not_mutate_source_objects() -> None:
    item = board_brief()
    first_candidate = item.dossiers[0]
    first_strategy = item.strategy_statuses[0]
    first_risk = item.risk_statuses[0]
    before = item.to_dict()

    summary = build_operating_brief_board_summary(item)

    assert summary.research_queue_candidate_ids == (
        "candidate-research-a",
        "candidate-research-b",
    )
    assert summary.watchlist_candidate_ids == ("candidate-watchlist",)
    assert summary.paper_eligible_candidate_ids == ("candidate-paper",)
    assert summary.live_probe_eligible_candidate_ids == ("candidate-probe",)
    assert summary.live_authorized_candidate_ids == ("candidate-live",)
    assert [record[0] for record in summary.strategy_blockers] == [
        "candidate-research-a",
        "candidate-watchlist",
        "candidate-paper",
        "candidate-probe",
        "candidate-research-b",
    ]
    assert item.to_dict() == before
    assert first_candidate.uncertainty_factors == (
        "Input provenance is not yet reviewed.",
    )
    assert first_strategy.blocking_reasons == ("No approved strategy mandate.",)
    assert first_risk.limitations == (
        "Authority metadata grants no trading action by itself.",
    )


def test_label_grouping_counts_and_empty_groups_are_deterministic() -> None:
    summary = build_operating_brief_board_summary(board_brief())
    payload = summary.to_dict()

    assert summary.candidate_ids_by_label == (
        (
            AdvisoryLabel.RESEARCH_ONLY,
            ("candidate-research-a", "candidate-research-b"),
        ),
        (AdvisoryLabel.WATCHLIST_ONLY, ("candidate-watchlist",)),
        (AdvisoryLabel.PAPER_ELIGIBLE, ("candidate-paper",)),
        (AdvisoryLabel.LIVE_PROBE_ELIGIBLE, ("candidate-probe",)),
        (AdvisoryLabel.LIVE_AUTHORIZED, ("candidate-live",)),
    )
    assert payload["candidate_ids_by_label"] == {
        "research_only": ["candidate-research-a", "candidate-research-b"],
        "watchlist_only": ["candidate-watchlist"],
        "paper_eligible": ["candidate-paper"],
        "live_probe_eligible": ["candidate-probe"],
        "live_authorized": ["candidate-live"],
    }
    assert payload["candidate_counts_by_label"] == {
        "research_only": 2,
        "watchlist_only": 1,
        "paper_eligible": 1,
        "live_probe_eligible": 1,
        "live_authorized": 1,
    }

    minimal = brief(
        dossiers=(dossier(candidate_id="candidate-research-only"),),
        strategy_statuses=(),
        risk_statuses=(),
    )
    minimal_payload = build_operating_brief_board_summary(minimal).to_dict()

    assert minimal_payload["candidate_ids_by_label"] == {
        "research_only": ["candidate-research-only"],
        "watchlist_only": [],
        "paper_eligible": [],
        "live_probe_eligible": [],
        "live_authorized": [],
    }
    assert minimal_payload["candidate_counts_by_label"] == {
        "research_only": 1,
        "watchlist_only": 0,
        "paper_eligible": 0,
        "live_probe_eligible": 0,
        "live_authorized": 0,
    }


def test_blocking_summaries_include_source_reasons_without_action_fields() -> None:
    payload = build_operating_brief_board_summary(board_brief()).to_dict()

    assert payload["strategy_blockers"] == [
        {
            "candidate_id": "candidate-research-a",
            "mandate_id": None,
            "blocking_reasons": ["No approved strategy mandate."],
        },
        {
            "candidate_id": "candidate-watchlist",
            "mandate_id": None,
            "blocking_reasons": ["Watchlist strategy review is incomplete."],
        },
        {
            "candidate_id": "candidate-paper",
            "mandate_id": "mandate-paper-001",
            "blocking_reasons": ["Live probe mandate is not approved."],
        },
        {
            "candidate_id": "candidate-probe",
            "mandate_id": "mandate-probe-001",
            "blocking_reasons": ["Live strategy authorization is not approved."],
        },
        {
            "candidate_id": "candidate-research-b",
            "mandate_id": None,
            "blocking_reasons": ["Second research strategy review is incomplete."],
        },
    ]
    assert payload["risk_blockers"][0] == {
        "candidate_id": "candidate-research-a",
        "authority_id": None,
        "blocking_reasons": ["No risk authority is approved."],
    }
    for blocker in payload["strategy_blockers"] + payload["risk_blockers"]:
        assert set(blocker) <= {
            "candidate_id",
            "mandate_id",
            "authority_id",
            "blocking_reasons",
        }


def test_uncertainty_failure_modes_limitations_and_non_claims_are_preserved() -> None:
    item = brief(
        dossiers=(
            dossier(
                candidate_id="candidate-explicit",
                uncertainty_factors=("Manual data provenance is unresolved.",),
                failure_modes=("A liquidity regime change may break assumptions.",),
                limitations=("Advisory-only limitation is retained.",),
            ),
        ),
        strategy_statuses=(strategy_status(candidate_id="candidate-explicit"),),
        risk_statuses=(risk_status(candidate_id="candidate-explicit"),),
        limitations=("Brief-level limitation is retained.",),
    )

    payload = build_operating_brief_board_summary(item).to_dict()

    assert payload["uncertainty_summaries"] == [
        {
            "candidate_id": "candidate-explicit",
            "uncertainty_factors": ["Manual data provenance is unresolved."],
        }
    ]
    assert payload["failure_mode_summaries"] == [
        {
            "candidate_id": "candidate-explicit",
            "failure_modes": ["A liquidity regime change may break assumptions."],
        }
    ]
    assert payload["brief_limitations"] == ["Brief-level limitation is retained."]
    assert payload["candidate_limitations"] == [
        {
            "candidate_id": "candidate-explicit",
            "limitations": ["Advisory-only limitation is retained."],
        }
    ]
    assert payload["non_claims"][0] == "This summary is advisory metadata only."


def test_to_dict_returns_deterministic_json_compatible_primitives() -> None:
    summary = build_operating_brief_board_summary(board_brief())

    first_payload = summary.to_dict()
    second_payload = summary.to_dict()

    assert first_payload == second_payload
    assert first_payload["as_of_date"] == "2026-05-17"
    _assert_primitive_json_compatible(first_payload)
    assert "OperatingBriefBoardSummary(" not in str(first_payload)
    assert "AdvisoryLabel." not in str(first_payload)
    assert " at 0x" not in str(first_payload)


def test_to_dict_lists_do_not_mutate_summary_tuples() -> None:
    summary = build_operating_brief_board_summary(brief())
    payload = summary.to_dict()

    payload["research_queue_candidate_ids"].append("mutated")
    payload["candidate_ids_by_label"]["research_only"].append("mutated")

    assert summary.research_queue_candidate_ids == ("candidate-001",)
    assert summary.candidate_ids_by_label[0] == (
        AdvisoryLabel.RESEARCH_ONLY,
        ("candidate-001",),
    )


def test_summary_output_contains_no_trading_behavior_or_selection_fields() -> None:
    payload = build_operating_brief_board_summary(board_brief()).to_dict()

    assert _all_serialized_keys(payload).isdisjoint(_FORBIDDEN_FIELD_NAMES)
    for forbidden_key in (
        "submit_order",
        "execution_request",
        "position_size",
        "allocation",
        "target_weight",
        "broker_order",
        "ranking",
        "scoring",
        "recommendation",
    ):
        assert forbidden_key not in _all_serialized_keys(payload)


def test_live_authorization_status_is_source_metadata_only() -> None:
    payload = build_operating_brief_board_summary(board_brief()).to_dict()

    assert payload["live_authorization_statuses"] == [
        {
            "candidate_id": "candidate-research-a",
            "advisory_label": "research_only",
            "strategy_status_present": True,
            "strategy_live_authorized": False,
            "risk_status_present": True,
            "risk_live_authorized": False,
            "label_live_authorized": False,
        },
        {
            "candidate_id": "candidate-watchlist",
            "advisory_label": "watchlist_only",
            "strategy_status_present": True,
            "strategy_live_authorized": False,
            "risk_status_present": True,
            "risk_live_authorized": False,
            "label_live_authorized": False,
        },
        {
            "candidate_id": "candidate-paper",
            "advisory_label": "paper_eligible",
            "strategy_status_present": True,
            "strategy_live_authorized": False,
            "risk_status_present": True,
            "risk_live_authorized": False,
            "label_live_authorized": False,
        },
        {
            "candidate_id": "candidate-probe",
            "advisory_label": "live_probe_eligible",
            "strategy_status_present": True,
            "strategy_live_authorized": False,
            "risk_status_present": True,
            "risk_live_authorized": False,
            "label_live_authorized": False,
        },
        {
            "candidate_id": "candidate-live",
            "advisory_label": "live_authorized",
            "strategy_status_present": True,
            "strategy_live_authorized": True,
            "risk_status_present": True,
            "risk_live_authorized": True,
            "label_live_authorized": True,
        },
        {
            "candidate_id": "candidate-research-b",
            "advisory_label": "research_only",
            "strategy_status_present": True,
            "strategy_live_authorized": False,
            "risk_status_present": True,
            "risk_live_authorized": False,
            "label_live_authorized": False,
        },
    ]


def test_summary_module_imports_no_forbidden_runtime_or_external_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_summary_module_references_no_forbidden_trading_runtime_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_summary_module_makes_no_io_network_broker_llm_or_scheduler_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


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
