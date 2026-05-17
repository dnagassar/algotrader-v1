import ast
from dataclasses import FrozenInstanceError, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from pathlib import Path
from types import ModuleType

import pytest

import algotrader.advisory.candidate_dossier_adapter as adapter
from algotrader.advisory import (
    AdvisoryLabel,
    CandidateDossierSnapshot,
    ResearchCandidateDossier,
    candidate_snapshot_to_research_candidate_dossier,
)
from algotrader.errors import ValidationError


MODULE_PATH = Path("src/algotrader/advisory/candidate_dossier_adapter.py")

_UNSUPPORTED_SNAPSHOT_FIELDS = (
    "as_of_date",
    "source_type",
    "source_ids",
    "label_source",
    "label_rationale",
    "strategy_id",
    "mandate_id",
    "universe_refs",
    "evidence_refs",
    "non_claims",
)

_FORBIDDEN_FIELD_NAMES = {
    "account",
    "account_id",
    "allocation",
    "alpaca",
    "api_key",
    "broker",
    "broker_order",
    "candidate_discovery",
    "credential",
    "credentials",
    "execution",
    "execution_request",
    "fill",
    "fill_id",
    "market_data",
    "network",
    "order",
    "order_id",
    "portfolio",
    "position",
    "position_id",
    "rank",
    "ranking",
    "recommendation",
    "recommendations",
    "runtime",
    "scheduler",
    "score",
    "scoring",
    "sdk",
    "submit_order",
    "target_weight",
}

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.governance",
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
    "http",
    "httpx",
    "importlib",
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

_FORBIDDEN_REFERENCE_NAMES = {
    "Account",
    "AdvisoryLabel",
    "AlpacaPaperBroker",
    "BrokerOrderResult",
    "ExecutionIntent",
    "ExecutionPlan",
    "Fill",
    "LocalBroker",
    "OperatingBrief",
    "PortfolioState",
    "Position",
    "ProposedOrder",
    "RiskAuthoritySnapshot",
    "RiskAuthorityStatus",
    "StrategyEligibilityStatus",
    "StrategyMandateSnapshot",
    "account",
    "account_id",
    "allocation",
    "alpaca",
    "api_key",
    "broker",
    "broker_order",
    "candidate_discovery",
    "credential",
    "credentials",
    "execution",
    "fill",
    "fill_id",
    "market_data",
    "network",
    "order",
    "portfolio",
    "position",
    "rank",
    "ranking",
    "recommendation",
    "recommendations",
    "runtime",
    "scheduler",
    "score",
    "scoring",
    "sdk",
    "submit_order",
    "target_weight",
}

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
    "os.environ.get",
    "os.getenv",
    "post",
    "random",
    "random.random",
    "read",
    "request",
    "schedule",
    "socket.socket",
    "submit_order",
    "time.monotonic",
    "time.time",
    "to_sql",
    "urlopen",
    "uuid.uuid4",
    "uuid4",
    "write",
}

_TRADING_RECOMMENDATION_LANGUAGE = {
    "buy",
    "hold",
    "recommendation",
    "sell",
    "trade",
    "trading",
}


def snapshot(**overrides: object) -> CandidateDossierSnapshot:
    values: dict[str, object] = {
        "candidate_id": "candidate-001",
        "as_of_date": date(2026, 5, 17),
        "title": "ETF trend research candidate",
        "summary": "Upstream advisory source metadata for future review.",
        "source_type": "external_research",
        "source_ids": ("research-note-001",),
        "proposed_label": AdvisoryLabel.RESEARCH_ONLY,
        "label_source": "external_research_proposed",
        "label_rationale": ("External source proposes research review only.",),
        "strategy_id": "",
        "mandate_id": "",
        "universe_refs": ("broad-etf-universe",),
        "evidence_refs": (),
        "uncertainty_factors": (
            "Input provenance is not fully reviewed.",
            "Universe membership may change.",
        ),
        "failure_modes": (
            "Source assumptions may be stale.",
            "Regime shift could invalidate assumptions.",
        ),
        "next_questions": (
            "Which deterministic evidence package is required?",
            "Which governance review owns promotion?",
        ),
        "limitations": (
            "Candidate source snapshot only.",
            "Advisory dossier metadata only.",
        ),
        "non_claims": ("No capital authority is represented.",),
    }
    values.update(overrides)
    return CandidateDossierSnapshot(**values)


def watchlist_snapshot(**overrides: object) -> CandidateDossierSnapshot:
    values: dict[str, object] = {
        "source_type": "research_log",
        "source_ids": ("research-log-001", "research-log-002"),
        "proposed_label": AdvisoryLabel.WATCHLIST_ONLY,
        "label_source": "ai_proposed",
        "label_rationale": ("Source proposes watchlist metadata only.",),
        "strategy_id": "strategy-sma-200",
        "mandate_id": "mandate-sma-200",
        "evidence_refs": ("evidence-package-001",),
    }
    values.update(overrides)
    return snapshot(**values)


def paper_snapshot(**overrides: object) -> CandidateDossierSnapshot:
    values: dict[str, object] = {
        "source_type": "governance_snapshot",
        "proposed_label": AdvisoryLabel.PAPER_ELIGIBLE,
        "label_source": "deterministic_governance",
        "label_rationale": ("Governance source permits paper metadata label.",),
        "strategy_id": "strategy-sma-200",
        "non_claims": ("No capital authority is represented.",),
    }
    values.update(overrides)
    return snapshot(**values)


def live_probe_snapshot(**overrides: object) -> CandidateDossierSnapshot:
    values: dict[str, object] = {
        "source_type": "governance_snapshot",
        "proposed_label": AdvisoryLabel.LIVE_PROBE_ELIGIBLE,
        "label_source": "deterministic_risk",
        "label_rationale": ("Risk source permits live-probe metadata label.",),
        "strategy_id": "strategy-sma-200",
        "mandate_id": "mandate-sma-200",
        "non_claims": ("No capital authority is represented.",),
    }
    values.update(overrides)
    return snapshot(**values)


def live_authorized_snapshot(**overrides: object) -> CandidateDossierSnapshot:
    values: dict[str, object] = {
        "source_type": "governance_snapshot",
        "proposed_label": AdvisoryLabel.LIVE_AUTHORIZED,
        "label_source": "deterministic_governance",
        "label_rationale": ("Governance source permits live-authorized metadata.",),
        "strategy_id": "strategy-sma-200",
        "mandate_id": "mandate-sma-200",
        "evidence_refs": ("evidence-package-001",),
        "non_claims": ("No capital authority is represented.",),
    }
    values.update(overrides)
    return snapshot(**values)


def adapt(item: CandidateDossierSnapshot) -> ResearchCandidateDossier:
    return candidate_snapshot_to_research_candidate_dossier(item)


def test_adapter_converts_valid_research_only_snapshot_to_dossier() -> None:
    source = snapshot()

    dossier = adapt(source)

    assert isinstance(dossier, ResearchCandidateDossier)
    assert dossier.candidate_id == "candidate-001"
    assert dossier.title == "ETF trend research candidate"
    assert dossier.summary == "Upstream advisory source metadata for future review."
    assert dossier.advisory_label is AdvisoryLabel.RESEARCH_ONLY
    assert dossier.advisory_label is source.proposed_label
    assert dossier.uncertainty_factors == source.uncertainty_factors
    assert dossier.failure_modes == source.failure_modes
    assert dossier.next_questions == source.next_questions
    assert dossier.limitations == source.limitations
    assert not hasattr(dossier, "__dict__")


def test_adapter_converts_valid_watchlist_snapshot_to_dossier() -> None:
    source = watchlist_snapshot()

    dossier = adapt(source)

    assert dossier.advisory_label is AdvisoryLabel.WATCHLIST_ONLY
    assert dossier.candidate_id == source.candidate_id
    assert dossier.uncertainty_factors == source.uncertainty_factors
    assert dossier.failure_modes == source.failure_modes
    assert dossier.next_questions == source.next_questions
    assert dossier.limitations == source.limitations


@pytest.mark.parametrize(
    "builder,expected_label",
    (
        (paper_snapshot, AdvisoryLabel.PAPER_ELIGIBLE),
        (live_probe_snapshot, AdvisoryLabel.LIVE_PROBE_ELIGIBLE),
        (live_authorized_snapshot, AdvisoryLabel.LIVE_AUTHORIZED),
    ),
)
def test_adapter_converts_valid_elevated_snapshots_when_source_allows_them(
    builder,
    expected_label: AdvisoryLabel,
) -> None:
    source = builder()

    dossier = adapt(source)

    assert dossier.advisory_label is expected_label
    assert dossier.advisory_label is source.proposed_label


def test_adapter_preserves_supported_metadata_and_tuple_ordering_only() -> None:
    source = snapshot(
        candidate_id="candidate-ordered",
        title="Ordered candidate metadata",
        summary="Ordered source metadata for advisory conversion.",
        source_ids=("source-a", "source-b"),
        label_rationale=("first rationale", "second rationale"),
        universe_refs=("universe-a", "universe-b"),
        evidence_refs=("evidence-a", "evidence-b"),
        uncertainty_factors=("first uncertainty", "second uncertainty"),
        failure_modes=("first failure", "second failure"),
        next_questions=("first question?", "second question?"),
        limitations=("first limitation", "second limitation"),
    )

    dossier = adapt(source)

    assert dossier.candidate_id == "candidate-ordered"
    assert dossier.title == "Ordered candidate metadata"
    assert dossier.summary == "Ordered source metadata for advisory conversion."
    assert dossier.uncertainty_factors == (
        "first uncertainty",
        "second uncertainty",
    )
    assert dossier.failure_modes == ("first failure", "second failure")
    assert dossier.next_questions == ("first question?", "second question?")
    assert dossier.limitations == ("first limitation", "second limitation")
    for unsupported_field in _UNSUPPORTED_SNAPSHOT_FIELDS:
        assert not hasattr(dossier, unsupported_field)


def test_adapter_does_not_mutate_source_snapshot_and_is_deterministic() -> None:
    source = live_authorized_snapshot()
    before = source.to_dict()

    first_dossier = adapt(source)
    second_dossier = adapt(source)

    assert first_dossier == second_dossier
    assert source.to_dict() == before
    with pytest.raises(FrozenInstanceError):
        first_dossier.summary = "changed"


def test_adapter_does_not_upgrade_watchlist_from_strategy_metadata() -> None:
    source = watchlist_snapshot(
        label_source="deterministic_governance",
        label_rationale=("Governance source still proposes watchlist only.",),
        strategy_id="strategy-sma-200",
        mandate_id="mandate-sma-200",
        evidence_refs=("evidence-package-001",),
    )

    dossier = adapt(source)

    assert dossier.advisory_label is AdvisoryLabel.WATCHLIST_ONLY


def test_adapter_does_not_downgrade_live_authorized_source_label() -> None:
    source = live_authorized_snapshot()

    dossier = adapt(source)

    assert dossier.advisory_label is AdvisoryLabel.LIVE_AUTHORIZED


def test_adapter_does_not_infer_label_from_source_or_strategy_metadata() -> None:
    source = snapshot(
        source_type="governance_snapshot",
        label_source="deterministic_governance",
        label_rationale=("Source keeps the candidate research only.",),
        proposed_label=AdvisoryLabel.RESEARCH_ONLY,
        strategy_id="strategy-sma-200",
        mandate_id="mandate-sma-200",
        evidence_refs=("evidence-package-001",),
    )

    dossier = adapt(source)

    assert dossier.advisory_label is AdvisoryLabel.RESEARCH_ONLY


@pytest.mark.parametrize("bad_input", (None, object(), {}, "candidate-001"))
def test_adapter_rejects_non_candidate_snapshot_inputs(bad_input: object) -> None:
    with pytest.raises(ValidationError, match="CandidateDossierSnapshot"):
        candidate_snapshot_to_research_candidate_dossier(bad_input)


def test_adapter_uses_existing_dossier_constructor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    real_constructor = adapter.ResearchCandidateDossier

    def spy_constructor(**kwargs: object) -> ResearchCandidateDossier:
        calls.append(kwargs)
        return real_constructor(**kwargs)

    monkeypatch.setattr(adapter, "ResearchCandidateDossier", spy_constructor)
    source = snapshot()

    dossier = adapter.candidate_snapshot_to_research_candidate_dossier(source)

    assert isinstance(dossier, real_constructor)
    assert calls == [
        {
            "candidate_id": "candidate-001",
            "title": "ETF trend research candidate",
            "summary": "Upstream advisory source metadata for future review.",
            "advisory_label": AdvisoryLabel.RESEARCH_ONLY,
            "uncertainty_factors": (
                "Input provenance is not fully reviewed.",
                "Universe membership may change.",
            ),
            "failure_modes": (
                "Source assumptions may be stale.",
                "Regime shift could invalidate assumptions.",
            ),
            "next_questions": (
                "Which deterministic evidence package is required?",
                "Which governance review owns promotion?",
            ),
            "limitations": (
                "Candidate source snapshot only.",
                "Advisory dossier metadata only.",
            ),
        }
    ]


def test_adapter_relies_on_dossier_constructor_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raising_constructor(**_: object) -> ResearchCandidateDossier:
        raise ValidationError("constructor validation boundary")

    monkeypatch.setattr(adapter, "ResearchCandidateDossier", raising_constructor)

    with pytest.raises(ValidationError, match="constructor validation boundary"):
        adapter.candidate_snapshot_to_research_candidate_dossier(snapshot())


def test_no_alternate_public_dossier_constructors_are_added() -> None:
    public_callables = {
        name
        for name, value in vars(ResearchCandidateDossier).items()
        if not name.startswith("_") and callable(value)
    }

    assert public_callables == {"to_dict"}
    assert adapter.__all__ == ["candidate_snapshot_to_research_candidate_dossier"]


def test_adapted_dossier_serialization_remains_primitive_and_deterministic() -> None:
    dossier = adapt(live_authorized_snapshot())

    first_payload = dossier.to_dict()
    second_payload = dossier.to_dict()

    assert first_payload == second_payload
    assert first_payload == {
        "candidate_id": "candidate-001",
        "title": "ETF trend research candidate",
        "summary": "Upstream advisory source metadata for future review.",
        "advisory_label": "live_authorized",
        "uncertainty_factors": [
            "Input provenance is not fully reviewed.",
            "Universe membership may change.",
        ],
        "failure_modes": [
            "Source assumptions may be stale.",
            "Regime shift could invalidate assumptions.",
        ],
        "next_questions": [
            "Which deterministic evidence package is required?",
            "Which governance review owns promotion?",
        ],
        "limitations": [
            "Candidate source snapshot only.",
            "Advisory dossier metadata only.",
        ],
    }
    _assert_primitive_json_compatible(first_payload)
    assert "ResearchCandidateDossier(" not in str(first_payload)
    assert "CandidateDossierSnapshot(" not in str(first_payload)
    assert " at 0x" not in str(first_payload)


def test_adapter_output_contains_no_trading_runtime_or_selection_fields() -> None:
    payload = adapt(live_authorized_snapshot()).to_dict()
    keys = _all_serialized_keys(payload)

    assert keys.isdisjoint(_FORBIDDEN_FIELD_NAMES)
    for forbidden_key in (
        "candidate_discovery",
        "rank",
        "ranking",
        "recommendation",
        "score",
        "scoring",
        "target_weight",
    ):
        assert forbidden_key not in keys


def test_adapter_output_contains_no_trading_recommendation_language() -> None:
    payload = adapt(live_authorized_snapshot()).to_dict()
    serialized_text = str(payload).lower()

    for term in _TRADING_RECOMMENDATION_LANGUAGE:
        assert term not in serialized_text


def test_elevated_labels_remain_metadata_only() -> None:
    dossier = adapt(live_authorized_snapshot())

    assert dossier.advisory_label is AdvisoryLabel.LIVE_AUTHORIZED
    for behavior_name in (
        "assemble_operating_brief",
        "create_order",
        "discover_candidate",
        "generate_brief",
        "rank_candidate",
        "score_strategy",
        "submit_order",
        "update_portfolio",
    ):
        assert not hasattr(dossier, behavior_name)


def test_source_label_restrictions_are_not_bypassed_by_adapter() -> None:
    with pytest.raises(ValidationError, match="paper_eligible"):
        paper_snapshot(label_source="ai_proposed")

    with pytest.raises(ValidationError, match="live_authorized"):
        live_authorized_snapshot(label_source="external_research_proposed")


def test_adapter_module_imports_no_forbidden_runtime_or_external_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_adapter_module_references_no_forbidden_status_or_trading_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_adapter_module_makes_no_io_network_clock_or_runtime_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def _assert_primitive_json_compatible(value: object) -> None:
    assert not is_dataclass(value)
    assert not isinstance(value, Enum)
    assert not isinstance(value, tuple)
    assert not isinstance(value, set)
    assert not isinstance(value, Decimal)
    assert not isinstance(value, date)
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
