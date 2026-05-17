import ast
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import json
from pathlib import Path
import re
import subprocess
import sys
from types import ModuleType

import pytest

import algotrader.advisory.candidate_snapshot as candidate_snapshot_module
import algotrader.advisory.operating_brief as operating_brief_module
import algotrader.advisory.operating_brief_summary as operating_brief_summary_module
from algotrader.advisory import (
    AdvisoryLabel,
    CandidateDossierSnapshot,
    OperatingBrief,
    OperatingBriefBoardSummary,
    ResearchCandidateDossier,
    RiskAuthorityStatus,
    StrategyEligibilityStatus,
    assemble_operating_brief_from_parts,
    build_operating_brief_board_summary,
)
from algotrader.errors import ValidationError
from tests.fixtures.advisory_pipeline import (
    build_synthetic_advisory_board_summary_from_pipeline,
    build_synthetic_advisory_operating_brief_from_pipeline,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PACKAGE_ROOT = PROJECT_ROOT / "src" / "algotrader"
GOVERNANCE_ROOT = SRC_PACKAGE_ROOT / "governance"

FORBIDDEN_ADVISORY_FIELD_FRAGMENTS = (
    "order",
    "fill",
    "broker",
    "allocation",
    "weight",
    "position",
    "size",
    "target",
    "submit",
    "execute",
    "account",
    "portfolio",
    "pnl",
    "runtime",
    "scheduler",
    "credential",
    "sdk",
    "network",
)

EXPECTED_ADVISORY_DATACLASSES = {
    "CandidateDossierSnapshot",
    "ResearchCandidateDossier",
    "StrategyEligibilityStatus",
    "RiskAuthorityStatus",
    "OperatingBrief",
    "OperatingBriefBoardSummary",
}

OBJECT_REPR_PATTERN = re.compile(r"<[^>]+ at 0x[0-9a-fA-F]+>")
MEMORY_ADDRESS_PATTERN = re.compile(r"\b0x[0-9a-fA-F]{6,}\b")


def test_governance_modules_do_not_import_advisory() -> None:
    scanned_paths = _governance_module_paths()
    discovered_paths = tuple(sorted(GOVERNANCE_ROOT.rglob("*.py")))

    assert scanned_paths == discovered_paths
    assert GOVERNANCE_ROOT / "__init__.py" in scanned_paths
    assert GOVERNANCE_ROOT / "status_snapshot.py" in scanned_paths

    violations = [
        f"{reference.path}:{reference.line}: governance must not import {reference.module}"
        for path in scanned_paths
        for reference in _import_references(path)
        if _matches_forbidden_prefix(reference.module, ("algotrader.advisory",))
    ]

    assert violations == []


def test_advisory_dataclass_field_names_do_not_add_runtime_terms() -> None:
    dataclass_types = _advisory_dataclass_types()
    dataclass_names = {item.__name__ for item in dataclass_types}
    violations: list[str] = []

    assert EXPECTED_ADVISORY_DATACLASSES <= dataclass_names

    for dataclass_type in dataclass_types:
        for field in fields(dataclass_type):
            lowered_name = field.name.lower()
            for fragment in FORBIDDEN_ADVISORY_FIELD_FRAGMENTS:
                if fragment in lowered_name:
                    violations.append(
                        f"{dataclass_type.__name__}.{field.name} contains {fragment!r}"
                    )

    assert violations == []


def test_to_dict_and_markdown_are_hash_seed_deterministic() -> None:
    first = _run_hash_seed_script("1")
    second = _run_hash_seed_script("2")

    assert first.returncode == 0, first.stderr.decode("utf-8", errors="replace")
    assert second.returncode == 0, second.stderr.decode("utf-8", errors="replace")
    assert first.stdout
    assert first.stdout == second.stdout


@pytest.mark.parametrize(
    ("name", "payload"),
    (
        (
            "brief",
            build_synthetic_advisory_operating_brief_from_pipeline().to_dict(),
        ),
        (
            "summary",
            build_synthetic_advisory_board_summary_from_pipeline().to_dict(),
        ),
    ),
)
def test_advisory_payloads_round_trip_as_identical_compact_json(
    name: str,
    payload: dict[str, object],
) -> None:
    compact_json = json.dumps(payload, separators=(",", ":"))
    round_tripped = json.dumps(json.loads(compact_json), separators=(",", ":"))

    assert compact_json, name
    assert round_tripped == compact_json
    _assert_json_payload_safe(payload)


@pytest.mark.parametrize(
    ("label", "strategy_status", "risk_status", "message"),
    (
        (
            AdvisoryLabel.LIVE_AUTHORIZED,
            lambda: live_probe_strategy_status(),
            lambda: live_risk_status(),
            "live_authorized",
        ),
        (
            AdvisoryLabel.LIVE_AUTHORIZED,
            lambda: live_strategy_status(),
            lambda: live_probe_risk_status(),
            "live_authorized",
        ),
        (
            AdvisoryLabel.LIVE_PROBE_ELIGIBLE,
            lambda: paper_strategy_status(),
            lambda: paper_risk_status(),
            "live_probe_eligible",
        ),
        (
            AdvisoryLabel.PAPER_ELIGIBLE,
            lambda: approved_non_paper_strategy_status(),
            lambda: paper_risk_status(),
            "paper_eligible",
        ),
        (
            AdvisoryLabel.PAPER_ELIGIBLE,
            lambda: paper_strategy_status(),
            lambda: non_paper_risk_status(),
            "paper_eligible",
        ),
    ),
)
def test_assembler_rejects_elevated_dossier_labels_with_lower_status_support(
    label: AdvisoryLabel,
    strategy_status,
    risk_status,
    message: str,
) -> None:
    candidate = dossier(advisory_label=label)
    before = candidate.to_dict()

    with pytest.raises(ValidationError, match=message):
        assemble_operating_brief_from_parts(
            as_of_date=date(2026, 5, 17),
            dossiers=(candidate,),
            strategy_statuses=(strategy_status(),),
            risk_statuses=(risk_status(),),
        )

    assert candidate.advisory_label is label
    assert candidate.to_dict() == before


def test_non_actionable_labels_keep_dossier_authority_despite_permissive_statuses() -> None:
    research = dossier(candidate_id="candidate-research")
    watchlist = dossier(
        candidate_id="candidate-watchlist",
        advisory_label=AdvisoryLabel.WATCHLIST_ONLY,
    )

    brief = assemble_operating_brief_from_parts(
        as_of_date=date(2026, 5, 17),
        dossiers=(research, watchlist),
        strategy_statuses=(
            live_strategy_status(candidate_id="candidate-research"),
            live_strategy_status(candidate_id="candidate-watchlist"),
        ),
        risk_statuses=(
            live_risk_status(candidate_id="candidate-research"),
            live_risk_status(candidate_id="candidate-watchlist"),
        ),
    )
    summary = build_operating_brief_board_summary(brief)

    assert isinstance(brief, OperatingBrief)
    assert isinstance(summary, OperatingBriefBoardSummary)
    assert brief.dossiers[0].advisory_label is AdvisoryLabel.RESEARCH_ONLY
    assert brief.dossiers[1].advisory_label is AdvisoryLabel.WATCHLIST_ONLY
    assert summary.research_queue_candidate_ids == ("candidate-research",)
    assert summary.watchlist_candidate_ids == ("candidate-watchlist",)
    assert summary.paper_eligible_candidate_ids == ()
    assert summary.live_probe_eligible_candidate_ids == ()
    assert summary.live_authorized_candidate_ids == ()
    assert summary.candidate_ids_by_label == (
        (AdvisoryLabel.RESEARCH_ONLY, ("candidate-research",)),
        (AdvisoryLabel.WATCHLIST_ONLY, ("candidate-watchlist",)),
        (AdvisoryLabel.PAPER_ELIGIBLE, ()),
        (AdvisoryLabel.LIVE_PROBE_ELIGIBLE, ()),
        (AdvisoryLabel.LIVE_AUTHORIZED, ()),
    )


def dossier(**overrides: object) -> ResearchCandidateDossier:
    values: dict[str, object] = {
        "candidate_id": "candidate-001",
        "title": "Synthetic advisory candidate",
        "summary": "Prepared advisory metadata for guardrail tests.",
        "advisory_label": AdvisoryLabel.RESEARCH_ONLY,
        "uncertainty_factors": ("Synthetic uncertainty is documented.",),
        "failure_modes": ("Synthetic failure mode is documented.",),
        "next_questions": ("Which review note should be checked next?",),
        "limitations": ("Guardrail fixture only.",),
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
        "blocking_reasons": ("Strategy support is not approved.",),
        "limitations": ("Strategy status is synthetic metadata only.",),
    }
    values.update(overrides)
    return StrategyEligibilityStatus(**values)


def approved_non_paper_strategy_status(**overrides: object) -> StrategyEligibilityStatus:
    values: dict[str, object] = {
        "mandate_id": "mandate-approved-no-paper",
        "mandate_approved": True,
        "evidence_approved": True,
        "evidence_refs": ("evidence-approved-no-paper",),
        "blocking_reasons": ("Paper eligibility is not approved.",),
    }
    values.update(overrides)
    return strategy_status(**values)


def paper_strategy_status(**overrides: object) -> StrategyEligibilityStatus:
    values: dict[str, object] = {
        "mandate_id": "mandate-paper",
        "mandate_approved": True,
        "evidence_approved": True,
        "evidence_refs": ("evidence-paper",),
        "paper_eligible": True,
        "blocking_reasons": ("Probe eligibility is not approved.",),
    }
    values.update(overrides)
    return strategy_status(**values)


def live_probe_strategy_status(**overrides: object) -> StrategyEligibilityStatus:
    values: dict[str, object] = {
        "mandate_id": "mandate-probe",
        "mandate_approved": True,
        "evidence_approved": True,
        "evidence_refs": ("evidence-probe",),
        "paper_eligible": True,
        "live_probe_eligible": True,
        "blocking_reasons": ("Live authorization is not approved.",),
    }
    values.update(overrides)
    return strategy_status(**values)


def live_strategy_status(**overrides: object) -> StrategyEligibilityStatus:
    values: dict[str, object] = {
        "mandate_id": "mandate-live",
        "mandate_approved": True,
        "evidence_approved": True,
        "evidence_refs": ("evidence-live",),
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
        "blocking_reasons": ("Risk support is not approved.",),
        "limitations": ("Risk status is synthetic metadata only.",),
    }
    values.update(overrides)
    return RiskAuthorityStatus(**values)


def non_paper_risk_status(**overrides: object) -> RiskAuthorityStatus:
    return risk_status(**overrides)


def paper_risk_status(**overrides: object) -> RiskAuthorityStatus:
    values: dict[str, object] = {
        "authority_id": "risk-paper",
        "paper_allowed": True,
        "blocking_reasons": ("Probe authority is not approved.",),
    }
    values.update(overrides)
    return risk_status(**values)


def live_probe_risk_status(**overrides: object) -> RiskAuthorityStatus:
    values: dict[str, object] = {
        "authority_id": "risk-probe",
        "paper_allowed": True,
        "live_probe_allowed": True,
        "blocking_reasons": ("Live authority is not approved.",),
    }
    values.update(overrides)
    return risk_status(**values)


def live_risk_status(**overrides: object) -> RiskAuthorityStatus:
    values: dict[str, object] = {
        "authority_id": "risk-live",
        "paper_allowed": True,
        "live_probe_allowed": True,
        "live_authorized": True,
        "blocking_reasons": (),
    }
    values.update(overrides)
    return risk_status(**values)


def _run_hash_seed_script(seed: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-c", _HASH_SEED_SCRIPT],
        cwd=PROJECT_ROOT,
        env=_subprocess_env(seed),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _subprocess_env(seed: str) -> dict[str, str]:
    path_separator = ";" if sys.platform == "win32" else ":"
    env = {
        "PYTHONHASHSEED": seed,
        "PYTHONPATH": path_separator.join(
            (str(PROJECT_ROOT / "src"), str(PROJECT_ROOT))
        ),
    }
    if sys.platform == "win32":
        env["SystemRoot"] = "C:\\Windows"
    return env


def _advisory_dataclass_types() -> tuple[type[object], ...]:
    modules = (
        candidate_snapshot_module,
        operating_brief_module,
        operating_brief_summary_module,
    )
    dataclass_types: list[type[object]] = []
    for module in modules:
        for value in vars(module).values():
            if (
                isinstance(value, type)
                and is_dataclass(value)
                and value.__module__ == module.__name__
            ):
                dataclass_types.append(value)
    return tuple(sorted(dataclass_types, key=lambda item: item.__name__))


def _assert_json_payload_safe(value: object) -> None:
    assert not is_dataclass(value)
    assert not isinstance(value, Enum)
    assert not isinstance(value, tuple)
    assert not isinstance(value, set)
    assert not isinstance(value, Decimal)
    assert not isinstance(value, (date, datetime))
    assert not callable(value)
    assert not isinstance(value, ModuleType)

    if value is None or type(value) in (bool, int, float):
        return

    if type(value) is str:
        assert not OBJECT_REPR_PATTERN.search(value)
        assert not MEMORY_ADDRESS_PATTERN.search(value)
        return

    if type(value) is list:
        for item in value:
            _assert_json_payload_safe(item)
        return

    if type(value) is dict:
        for key, item in value.items():
            assert type(key) is str
            assert not OBJECT_REPR_PATTERN.search(key)
            assert not MEMORY_ADDRESS_PATTERN.search(key)
            _assert_json_payload_safe(item)
        return

    raise AssertionError(f"non-primitive serialized value: {type(value)!r}")


def _governance_module_paths() -> tuple[Path, ...]:
    return tuple(sorted(GOVERNANCE_ROOT.rglob("*.py")))


def _import_references(path: Path) -> tuple["ImportReference", ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[ImportReference] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(
                ImportReference(path=path, line=node.lineno, module=alias.name)
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            imports.extend(
                ImportReference(path=path, line=node.lineno, module=module)
                for module in _import_from_modules(path, node)
            )

    return tuple(imports)


def _import_from_modules(path: Path, node: ast.ImportFrom) -> tuple[str, ...]:
    if node.level == 0:
        return (node.module,) if node.module else ()

    base_module = _relative_import_base(path, node.level)
    if node.module:
        return (f"{base_module}.{node.module}",)

    return tuple(f"{base_module}.{alias.name}" for alias in node.names)


def _relative_import_base(path: Path, level: int) -> str:
    module_name = _module_name(path)
    if path.name == "__init__.py":
        package_name = module_name
    else:
        package_name = module_name.rsplit(".", maxsplit=1)[0]

    package_parts = package_name.split(".")
    base_parts = package_parts[: len(package_parts) - level + 1]
    return ".".join(base_parts)


def _module_name(path: Path) -> str:
    relative_path = path.relative_to(SRC_PACKAGE_ROOT.parent)
    return ".".join(relative_path.with_suffix("").parts)


def _matches_forbidden_prefix(module: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(
        module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )


class ImportReference:
    def __init__(self, *, path: Path, line: int, module: str) -> None:
        self.path = path
        self.line = line
        self.module = module


_HASH_SEED_SCRIPT = r"""
import json

from algotrader.advisory import (
    render_operating_brief_board_summary_markdown,
    render_operating_brief_markdown,
)
from tests.fixtures.advisory_pipeline import (
    build_synthetic_advisory_board_summary_from_pipeline,
    build_synthetic_advisory_operating_brief_from_pipeline,
)

brief = build_synthetic_advisory_operating_brief_from_pipeline()
summary = build_synthetic_advisory_board_summary_from_pipeline()
payload = {
    "brief": brief.to_dict(),
    "summary": summary.to_dict(),
    "brief_markdown": render_operating_brief_markdown(brief),
    "summary_markdown": render_operating_brief_board_summary_markdown(summary),
}
print(json.dumps(payload, separators=(",", ":")))
"""
