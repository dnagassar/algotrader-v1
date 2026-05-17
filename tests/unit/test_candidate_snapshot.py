import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from types import ModuleType

import pytest

from algotrader.advisory import AdvisoryLabel, CandidateDossierSnapshot
from algotrader.errors import ValidationError


MODULE_PATH = Path("src/algotrader/advisory/candidate_snapshot.py")

_STRING_TUPLE_FIELDS = (
    "source_ids",
    "label_rationale",
    "universe_refs",
    "evidence_refs",
    "uncertainty_factors",
    "failure_modes",
    "next_questions",
    "limitations",
    "non_claims",
)

_FORBIDDEN_FIELD_FRAGMENTS = (
    "account",
    "allocation",
    "broker",
    "credential",
    "execution",
    "fill",
    "llm",
    "network",
    "order",
    "portfolio",
    "position",
    "runtime",
    "scheduler",
    "sdk",
    "target_weight",
)

_FORBIDDEN_FIELD_NAMES = {
    "candidate_discovery",
    "rank",
    "ranking",
    "recommendation",
    "recommendations",
    "score",
    "scoring",
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
    "AlpacaPaperBroker",
    "BrokerOrderResult",
    "ExecutionIntent",
    "ExecutionPlan",
    "Fill",
    "LocalBroker",
    "PortfolioState",
    "Position",
    "ProposedOrder",
    "account",
    "account_id",
    "allocation",
    "alpaca",
    "api_key",
    "broker_order",
    "broker_order_id",
    "candidate_discovery",
    "credential",
    "credentials",
    "execution",
    "fill",
    "fill_id",
    "market_data",
    "network",
    "order_id",
    "portfolio_state",
    "position",
    "position_id",
    "rank",
    "ranking",
    "recommend",
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

_RESTRICTED_NON_CLAIM_TERMS = {
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
        "uncertainty_factors": ("Input provenance is not fully reviewed.",),
        "failure_modes": ("Source assumptions may be stale.",),
        "next_questions": ("Which deterministic evidence package is required?",),
        "limitations": ("Candidate source snapshot only.",),
        "non_claims": ("No order generation or capital mutation is represented.",),
    }
    values.update(overrides)
    return CandidateDossierSnapshot(**values)


def paper_snapshot(**overrides: object) -> CandidateDossierSnapshot:
    values: dict[str, object] = {
        "source_type": "governance_snapshot",
        "proposed_label": AdvisoryLabel.PAPER_ELIGIBLE,
        "label_source": "deterministic_governance",
        "label_rationale": ("Governance source permits paper metadata label.",),
        "strategy_id": "strategy-sma-200",
        "non_claims": ("No order generation or capital mutation is represented.",),
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
        "non_claims": (
            "No order generation, portfolio mutation, or broker action is represented.",
        ),
    }
    values.update(overrides)
    return snapshot(**values)


def live_authorized_snapshot(**overrides: object) -> CandidateDossierSnapshot:
    values: dict[str, object] = {
        "source_type": "governance_snapshot",
        "proposed_label": AdvisoryLabel.LIVE_AUTHORIZED,
        "label_source": "deterministic_governance",
        "label_rationale": ("Governance source permits live-authorized metadata label.",),
        "strategy_id": "strategy-sma-200",
        "mandate_id": "mandate-sma-200",
        "evidence_refs": ("evidence-package-001",),
        "non_claims": (
            "No order generation, portfolio mutation, or broker action is represented.",
        ),
    }
    values.update(overrides)
    return snapshot(**values)


def test_accepts_valid_research_only_snapshot_from_external_research_source() -> None:
    item = snapshot()

    assert item.proposed_label is AdvisoryLabel.RESEARCH_ONLY
    assert item.label_source == "external_research_proposed"
    assert item.source_type == "external_research"


def test_accepts_valid_watchlist_only_snapshot_from_ai_source() -> None:
    item = snapshot(
        proposed_label=AdvisoryLabel.WATCHLIST_ONLY,
        label_source="ai_proposed",
        label_rationale=("AI source proposes watchlist metadata only.",),
    )

    assert item.proposed_label is AdvisoryLabel.WATCHLIST_ONLY
    assert item.label_source == "ai_proposed"


def test_accepts_valid_paper_eligible_snapshot_from_deterministic_governance() -> None:
    item = paper_snapshot()

    assert item.proposed_label is AdvisoryLabel.PAPER_ELIGIBLE
    assert item.strategy_id == "strategy-sma-200"


@pytest.mark.parametrize("label_source", ("deterministic_risk", "human_review"))
def test_accepts_valid_live_probe_snapshot_from_reviewed_sources(
    label_source: str,
) -> None:
    item = live_probe_snapshot(label_source=label_source)

    assert item.proposed_label is AdvisoryLabel.LIVE_PROBE_ELIGIBLE
    assert item.label_source == label_source
    assert item.strategy_id == "strategy-sma-200"
    assert item.mandate_id == "mandate-sma-200"


@pytest.mark.parametrize("label_source", ("deterministic_governance", "synthetic_fixture"))
def test_accepts_valid_live_authorized_snapshot_with_required_refs(
    label_source: str,
) -> None:
    item = live_authorized_snapshot(
        label_source=label_source,
        source_type="synthetic" if label_source == "synthetic_fixture" else "governance_snapshot",
    )

    assert item.proposed_label is AdvisoryLabel.LIVE_AUTHORIZED
    assert item.label_source == label_source
    assert item.evidence_refs == ("evidence-package-001",)


def test_candidate_dossier_snapshot_is_frozen_and_slotted() -> None:
    item = snapshot()

    assert hasattr(CandidateDossierSnapshot, "__slots__")
    assert not hasattr(item, "__dict__")
    with pytest.raises(FrozenInstanceError):
        item.title = "changed"


def test_candidate_dossier_snapshot_normalizes_all_sequences_to_tuples() -> None:
    sequence_values = {
        "source_ids": ["source-001"],
        "label_rationale": ["Label rationale."],
        "universe_refs": ["universe-001"],
        "evidence_refs": ["evidence-001"],
        "uncertainty_factors": ["Uncertainty."],
        "failure_modes": ["Failure mode."],
        "next_questions": ["Question?"],
        "limitations": ["Limitation."],
        "non_claims": ["No order generation is represented."],
    }

    item = snapshot(**sequence_values)
    for values in sequence_values.values():
        values.append("late mutation")

    for field_name in _STRING_TUPLE_FIELDS:
        assert getattr(item, field_name) == (sequence_values[field_name][0],)
        assert isinstance(getattr(item, field_name), tuple)

    with pytest.raises(TypeError):
        item.source_ids[0] = "changed"


@pytest.mark.parametrize(
    "field_name,value",
    (
        ("candidate_id", ""),
        ("candidate_id", " "),
        ("title", ""),
        ("title", " "),
        ("summary", ""),
        ("summary", " "),
        ("source_type", ""),
        ("source_type", " "),
        ("label_source", ""),
        ("label_source", " "),
    ),
)
def test_rejects_empty_required_strings(field_name: str, value: object) -> None:
    with pytest.raises(ValidationError, match=field_name):
        snapshot(**{field_name: value})


@pytest.mark.parametrize(
    "field_name,value",
    (
        ("candidate_id", True),
        ("title", False),
        ("summary", True),
        ("source_type", False),
        ("label_source", True),
        ("strategy_id", True),
        ("mandate_id", False),
    ),
)
def test_rejects_bool_where_string_is_expected(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        snapshot(**{field_name: value})


def test_rejects_datetime_as_as_of_date() -> None:
    with pytest.raises(ValidationError, match="as_of_date"):
        snapshot(as_of_date=datetime(2026, 5, 17))


@pytest.mark.parametrize(
    "field_name,value",
    (
        ("source_ids", "source-001"),
        ("source_ids", ("valid", None)),
        ("label_rationale", ("valid", "")),
        ("universe_refs", ("valid", True)),
        ("evidence_refs", ("valid", 1)),
        ("uncertainty_factors", "uncertain"),
        ("uncertainty_factors", ("valid", False)),
        ("failure_modes", ("valid", "")),
        ("next_questions", ("valid", None)),
        ("limitations", ("valid", " ")),
        ("non_claims", ("valid", 1)),
    ),
)
def test_rejects_malformed_tuple_entries(field_name: str, value: object) -> None:
    with pytest.raises(ValidationError, match=field_name):
        snapshot(**{field_name: value})


def test_rejects_unknown_source_type() -> None:
    with pytest.raises(ValidationError, match="source_type"):
        snapshot(source_type="web_scrape")


def test_rejects_unknown_label_source() -> None:
    with pytest.raises(ValidationError, match="label_source"):
        snapshot(label_source="unreviewed_ai")


@pytest.mark.parametrize("value", ("research_only", object()))
def test_rejects_non_advisory_label_proposed_label(value: object) -> None:
    with pytest.raises(ValidationError, match="proposed_label"):
        snapshot(proposed_label=value)


def test_rejects_paper_eligible_from_ai_source() -> None:
    with pytest.raises(ValidationError, match="paper_eligible"):
        paper_snapshot(label_source="ai_proposed")


def test_rejects_live_probe_eligible_from_external_research_source() -> None:
    with pytest.raises(ValidationError, match="live_probe_eligible"):
        live_probe_snapshot(label_source="external_research_proposed")


def test_rejects_live_authorized_from_ai_source() -> None:
    with pytest.raises(ValidationError, match="live_authorized"):
        live_authorized_snapshot(label_source="ai_proposed")


def test_rejects_live_authorized_without_strategy_id() -> None:
    with pytest.raises(ValidationError, match="strategy_id"):
        live_authorized_snapshot(strategy_id="")


def test_rejects_live_authorized_without_mandate_id() -> None:
    with pytest.raises(ValidationError, match="mandate_id"):
        live_authorized_snapshot(mandate_id="")


def test_rejects_live_authorized_without_evidence_refs() -> None:
    with pytest.raises(ValidationError, match="evidence_refs"):
        live_authorized_snapshot(evidence_refs=())


@pytest.mark.parametrize(
    "builder",
    (paper_snapshot, live_probe_snapshot, live_authorized_snapshot),
)
def test_rejects_elevated_labels_without_required_non_claims(builder) -> None:
    with pytest.raises(ValidationError, match="non_claims"):
        builder(non_claims=())


def test_rejects_paper_eligible_without_strategy_id() -> None:
    with pytest.raises(ValidationError, match="strategy_id"):
        paper_snapshot(strategy_id="")


@pytest.mark.parametrize("field_name", ("strategy_id", "mandate_id"))
def test_rejects_live_probe_eligible_without_strategy_or_mandate(
    field_name: str,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        live_probe_snapshot(**{field_name: ""})


def test_rejects_non_claims_with_trading_recommendation_language() -> None:
    with pytest.raises(ValidationError, match="non_claims"):
        snapshot(non_claims=("No buy language belongs here.",))


def test_to_dict_returns_deterministic_primitive_json_compatible_output() -> None:
    item = live_authorized_snapshot()

    first_payload = item.to_dict()
    second_payload = item.to_dict()

    assert first_payload == second_payload
    assert first_payload == {
        "candidate_id": "candidate-001",
        "as_of_date": "2026-05-17",
        "title": "ETF trend research candidate",
        "summary": "Upstream advisory source metadata for future review.",
        "source_type": "governance_snapshot",
        "source_ids": ["research-note-001"],
        "proposed_label": "live_authorized",
        "label_source": "deterministic_governance",
        "label_rationale": [
            "Governance source permits live-authorized metadata label."
        ],
        "strategy_id": "strategy-sma-200",
        "mandate_id": "mandate-sma-200",
        "universe_refs": ["broad-etf-universe"],
        "evidence_refs": ["evidence-package-001"],
        "uncertainty_factors": ["Input provenance is not fully reviewed."],
        "failure_modes": ["Source assumptions may be stale."],
        "next_questions": ["Which deterministic evidence package is required?"],
        "limitations": ["Candidate source snapshot only."],
        "non_claims": [
            "No order generation, portfolio mutation, or broker action is represented."
        ],
    }
    assert isinstance(first_payload["as_of_date"], str)
    assert first_payload["as_of_date"] == "2026-05-17"
    assert isinstance(first_payload["proposed_label"], str)
    for field_name in _STRING_TUPLE_FIELDS:
        assert isinstance(first_payload[field_name], list)
    _assert_primitive_json_compatible(first_payload)
    assert "CandidateDossierSnapshot(" not in str(first_payload)
    assert " at 0x" not in str(first_payload)


def test_to_dict_does_not_mutate_source_snapshot() -> None:
    item = snapshot()

    payload = item.to_dict()
    payload["source_ids"].append("late-source")
    payload["non_claims"].append("late non-claim")

    assert item.source_ids == ("research-note-001",)
    assert item.non_claims == ("No order generation or capital mutation is represented.",)
    assert item.to_dict()["source_ids"] == ["research-note-001"]
    assert item.to_dict()["non_claims"] == [
        "No order generation or capital mutation is represented."
    ]


def test_snapshot_contract_exposes_no_forbidden_fields() -> None:
    field_names = {field.name for field in fields(CandidateDossierSnapshot)}

    assert field_names.isdisjoint(_FORBIDDEN_FIELD_NAMES)
    for fragment in _FORBIDDEN_FIELD_FRAGMENTS:
        assert all(fragment not in field_name for field_name in field_names)


def test_snapshot_contract_exposes_no_scoring_ranking_or_discovery_fields() -> None:
    field_names = {field.name for field in fields(CandidateDossierSnapshot)}

    for forbidden_fragment in (
        "candidate_discovery",
        "discovery",
        "rank",
        "ranking",
        "recommendation",
        "score",
        "scoring",
    ):
        assert all(forbidden_fragment not in field_name for field_name in field_names)


def test_non_claims_do_not_contain_trading_recommendation_language() -> None:
    item = live_authorized_snapshot()

    for non_claim in item.non_claims:
        words = {
            part.strip(".,;:!?()[]{}").lower() for part in non_claim.split()
        }
        assert words.isdisjoint(_RESTRICTED_NON_CLAIM_TERMS)


def test_elevated_labels_are_metadata_only() -> None:
    item = live_authorized_snapshot()

    assert item.proposed_label is AdvisoryLabel.LIVE_AUTHORIZED
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
        assert not hasattr(item, behavior_name)


@pytest.mark.parametrize(
    "proposed_label,label_source",
    (
        (AdvisoryLabel.PAPER_ELIGIBLE, "ai_proposed"),
        (AdvisoryLabel.PAPER_ELIGIBLE, "external_research_proposed"),
        (AdvisoryLabel.PAPER_ELIGIBLE, "other"),
        (AdvisoryLabel.LIVE_PROBE_ELIGIBLE, "ai_proposed"),
        (AdvisoryLabel.LIVE_PROBE_ELIGIBLE, "external_research_proposed"),
        (AdvisoryLabel.LIVE_PROBE_ELIGIBLE, "other"),
        (AdvisoryLabel.LIVE_AUTHORIZED, "ai_proposed"),
        (AdvisoryLabel.LIVE_AUTHORIZED, "external_research_proposed"),
        (AdvisoryLabel.LIVE_AUTHORIZED, "other"),
    ),
)
def test_ai_external_and_other_sources_cannot_directly_assign_elevated_labels(
    proposed_label: AdvisoryLabel,
    label_source: str,
) -> None:
    with pytest.raises(ValidationError, match=proposed_label.value):
        live_authorized_snapshot(
            proposed_label=proposed_label,
            label_source=label_source,
            evidence_refs=("evidence-package-001",),
        )


def test_no_alternate_public_constructors_exist() -> None:
    public_callables = {
        name
        for name, value in vars(CandidateDossierSnapshot).items()
        if not name.startswith("_") and callable(value)
    }

    assert public_callables == {"to_dict"}


def test_candidate_snapshot_module_imports_no_forbidden_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_candidate_snapshot_module_references_no_forbidden_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_candidate_snapshot_module_makes_no_io_network_clock_or_runtime_calls() -> None:
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
