"""Metadata-only research scope candidate contracts."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import TypeVar

from algotrader.errors import ValidationError

__all__ = [
    "APPROVAL_STATES",
    "BENCHMARK_TYPES",
    "CASH_PROXY_TYPES",
    "REQUIRED_RESEARCH_SCOPE_NON_CLAIMS",
    "SOURCE_TYPES",
    "UNIVERSE_TYPES",
    "ResearchBenchmarkCandidate",
    "ResearchCashProxyCandidate",
    "ResearchDataSourceCandidate",
    "ResearchScopeSnapshot",
    "ResearchUniverseCandidate",
]


APPROVAL_STATES = ("candidate_only", "blocked", "deferred")
SOURCE_TYPES = (
    "synthetic",
    "local_snapshot_candidate",
    "vendor_candidate",
    "public_candidate",
    "manual_candidate",
    "other",
)
UNIVERSE_TYPES = (
    "synthetic",
    "broad_etf_candidate",
    "single_symbol_candidate",
    "other",
)
BENCHMARK_TYPES = (
    "synthetic",
    "buy_and_hold_candidate",
    "index_candidate",
    "cash_candidate",
    "other",
)
CASH_PROXY_TYPES = (
    "synthetic",
    "treasury_bill_candidate",
    "money_market_candidate",
    "zero_return_placeholder",
    "other",
)
REQUIRED_RESEARCH_SCOPE_NON_CLAIMS = (
    "not source approval",
    "not universe approval",
    "not benchmark approval",
    "not cash proxy approval",
    "not strategy validation",
    "not signal approval",
    "not trading authority",
    "no broker/order/fill/portfolio/runtime behavior",
    "no real data ingestion",
)

_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class ResearchDataSourceCandidate:
    """Candidate-only source metadata for future research planning."""

    source_id: str
    source_name: str
    source_type: str
    approval_state: str
    data_kind: str
    terms_status: str
    storage_policy: str
    adjustment_policy: str
    revision_policy: str
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]
    required_follow_up: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _required_string(self.source_id, "source_id"))
        object.__setattr__(
            self,
            "source_name",
            _required_string(self.source_name, "source_name"),
        )
        object.__setattr__(
            self,
            "source_type",
            _allowed_string(self.source_type, "source_type", SOURCE_TYPES),
        )
        object.__setattr__(
            self,
            "approval_state",
            _allowed_string(
                self.approval_state,
                "approval_state",
                APPROVAL_STATES,
            ),
        )
        object.__setattr__(self, "data_kind", _required_string(self.data_kind, "data_kind"))
        object.__setattr__(
            self,
            "terms_status",
            _required_string(self.terms_status, "terms_status"),
        )
        object.__setattr__(
            self,
            "storage_policy",
            _required_string(self.storage_policy, "storage_policy"),
        )
        object.__setattr__(
            self,
            "adjustment_policy",
            _required_string(self.adjustment_policy, "adjustment_policy"),
        )
        object.__setattr__(
            self,
            "revision_policy",
            _required_string(self.revision_policy, "revision_policy"),
        )
        object.__setattr__(self, "blockers", _string_tuple(self.blockers, "blockers"))
        object.__setattr__(
            self,
            "limitations",
            _string_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "required_follow_up",
            _string_tuple(self.required_follow_up, "required_follow_up"),
        )
        object.__setattr__(
            self,
            "non_claims",
            _required_non_claims(self.non_claims),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-compatible primitive source metadata."""

        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "approval_state": self.approval_state,
            "data_kind": self.data_kind,
            "terms_status": self.terms_status,
            "storage_policy": self.storage_policy,
            "adjustment_policy": self.adjustment_policy,
            "revision_policy": self.revision_policy,
            "blockers": list(self.blockers),
            "limitations": list(self.limitations),
            "required_follow_up": list(self.required_follow_up),
            "non_claims": list(self.non_claims),
        }


@dataclass(frozen=True, slots=True)
class ResearchUniverseCandidate:
    """Candidate-only universe metadata for future research planning."""

    universe_id: str
    universe_name: str
    universe_type: str
    approval_state: str
    asset_ids: tuple[str, ...]
    inclusion_rules: tuple[str, ...]
    exclusion_rules: tuple[str, ...]
    survivorship_policy: str
    inception_policy: str
    delisting_policy: str
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]
    required_follow_up: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "universe_id",
            _required_string(self.universe_id, "universe_id"),
        )
        object.__setattr__(
            self,
            "universe_name",
            _required_string(self.universe_name, "universe_name"),
        )
        object.__setattr__(
            self,
            "universe_type",
            _allowed_string(self.universe_type, "universe_type", UNIVERSE_TYPES),
        )
        object.__setattr__(
            self,
            "approval_state",
            _allowed_string(
                self.approval_state,
                "approval_state",
                APPROVAL_STATES,
            ),
        )
        object.__setattr__(
            self,
            "asset_ids",
            _unique_required_string_tuple(self.asset_ids, "asset_ids"),
        )
        object.__setattr__(
            self,
            "inclusion_rules",
            _string_tuple(self.inclusion_rules, "inclusion_rules"),
        )
        object.__setattr__(
            self,
            "exclusion_rules",
            _string_tuple(self.exclusion_rules, "exclusion_rules"),
        )
        object.__setattr__(
            self,
            "survivorship_policy",
            _required_string(self.survivorship_policy, "survivorship_policy"),
        )
        object.__setattr__(
            self,
            "inception_policy",
            _required_string(self.inception_policy, "inception_policy"),
        )
        object.__setattr__(
            self,
            "delisting_policy",
            _required_string(self.delisting_policy, "delisting_policy"),
        )
        object.__setattr__(self, "blockers", _string_tuple(self.blockers, "blockers"))
        object.__setattr__(
            self,
            "limitations",
            _string_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "required_follow_up",
            _string_tuple(self.required_follow_up, "required_follow_up"),
        )
        object.__setattr__(
            self,
            "non_claims",
            _required_non_claims(self.non_claims),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-compatible primitive universe metadata."""

        return {
            "universe_id": self.universe_id,
            "universe_name": self.universe_name,
            "universe_type": self.universe_type,
            "approval_state": self.approval_state,
            "asset_ids": list(self.asset_ids),
            "inclusion_rules": list(self.inclusion_rules),
            "exclusion_rules": list(self.exclusion_rules),
            "survivorship_policy": self.survivorship_policy,
            "inception_policy": self.inception_policy,
            "delisting_policy": self.delisting_policy,
            "blockers": list(self.blockers),
            "limitations": list(self.limitations),
            "required_follow_up": list(self.required_follow_up),
            "non_claims": list(self.non_claims),
        }


@dataclass(frozen=True, slots=True)
class ResearchBenchmarkCandidate:
    """Candidate-only comparison metadata for future research planning."""

    benchmark_id: str
    benchmark_name: str
    benchmark_type: str
    approval_state: str
    return_basis: str
    comparison_role: str
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]
    required_follow_up: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "benchmark_id",
            _required_string(self.benchmark_id, "benchmark_id"),
        )
        object.__setattr__(
            self,
            "benchmark_name",
            _required_string(self.benchmark_name, "benchmark_name"),
        )
        object.__setattr__(
            self,
            "benchmark_type",
            _allowed_string(self.benchmark_type, "benchmark_type", BENCHMARK_TYPES),
        )
        object.__setattr__(
            self,
            "approval_state",
            _allowed_string(
                self.approval_state,
                "approval_state",
                APPROVAL_STATES,
            ),
        )
        object.__setattr__(
            self,
            "return_basis",
            _required_string(self.return_basis, "return_basis"),
        )
        object.__setattr__(
            self,
            "comparison_role",
            _required_string(self.comparison_role, "comparison_role"),
        )
        object.__setattr__(self, "blockers", _string_tuple(self.blockers, "blockers"))
        object.__setattr__(
            self,
            "limitations",
            _string_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "required_follow_up",
            _string_tuple(self.required_follow_up, "required_follow_up"),
        )
        object.__setattr__(
            self,
            "non_claims",
            _required_non_claims(self.non_claims),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-compatible primitive benchmark metadata."""

        return {
            "benchmark_id": self.benchmark_id,
            "benchmark_name": self.benchmark_name,
            "benchmark_type": self.benchmark_type,
            "approval_state": self.approval_state,
            "return_basis": self.return_basis,
            "comparison_role": self.comparison_role,
            "blockers": list(self.blockers),
            "limitations": list(self.limitations),
            "required_follow_up": list(self.required_follow_up),
            "non_claims": list(self.non_claims),
        }


@dataclass(frozen=True, slots=True)
class ResearchCashProxyCandidate:
    """Candidate-only cash proxy metadata for future research planning."""

    cash_proxy_id: str
    cash_proxy_name: str
    cash_proxy_type: str
    approval_state: str
    return_basis: str
    availability_policy: str
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]
    required_follow_up: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "cash_proxy_id",
            _required_string(self.cash_proxy_id, "cash_proxy_id"),
        )
        object.__setattr__(
            self,
            "cash_proxy_name",
            _required_string(self.cash_proxy_name, "cash_proxy_name"),
        )
        object.__setattr__(
            self,
            "cash_proxy_type",
            _allowed_string(
                self.cash_proxy_type,
                "cash_proxy_type",
                CASH_PROXY_TYPES,
            ),
        )
        object.__setattr__(
            self,
            "approval_state",
            _allowed_string(
                self.approval_state,
                "approval_state",
                APPROVAL_STATES,
            ),
        )
        object.__setattr__(
            self,
            "return_basis",
            _required_string(self.return_basis, "return_basis"),
        )
        object.__setattr__(
            self,
            "availability_policy",
            _required_string(self.availability_policy, "availability_policy"),
        )
        object.__setattr__(self, "blockers", _string_tuple(self.blockers, "blockers"))
        object.__setattr__(
            self,
            "limitations",
            _string_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "required_follow_up",
            _string_tuple(self.required_follow_up, "required_follow_up"),
        )
        object.__setattr__(
            self,
            "non_claims",
            _required_non_claims(self.non_claims),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-compatible primitive cash proxy metadata."""

        return {
            "cash_proxy_id": self.cash_proxy_id,
            "cash_proxy_name": self.cash_proxy_name,
            "cash_proxy_type": self.cash_proxy_type,
            "approval_state": self.approval_state,
            "return_basis": self.return_basis,
            "availability_policy": self.availability_policy,
            "blockers": list(self.blockers),
            "limitations": list(self.limitations),
            "required_follow_up": list(self.required_follow_up),
            "non_claims": list(self.non_claims),
        }


@dataclass(frozen=True, slots=True)
class ResearchScopeSnapshot:
    """Candidate-only research scope snapshot metadata."""

    scope_id: str
    as_of_date: date
    approval_state: str
    source_candidates: tuple[ResearchDataSourceCandidate, ...]
    universe_candidates: tuple[ResearchUniverseCandidate, ...]
    benchmark_candidates: tuple[ResearchBenchmarkCandidate, ...]
    cash_proxy_candidates: tuple[ResearchCashProxyCandidate, ...]
    blockers: tuple[str, ...]
    limitations: tuple[str, ...]
    required_follow_up: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "scope_id", _required_string(self.scope_id, "scope_id"))
        object.__setattr__(
            self,
            "as_of_date",
            _plain_date(self.as_of_date, "as_of_date"),
        )
        object.__setattr__(
            self,
            "approval_state",
            _allowed_string(
                self.approval_state,
                "approval_state",
                APPROVAL_STATES,
            ),
        )
        object.__setattr__(
            self,
            "source_candidates",
            _candidate_tuple(
                self.source_candidates,
                "source_candidates",
                ResearchDataSourceCandidate,
            ),
        )
        object.__setattr__(
            self,
            "universe_candidates",
            _candidate_tuple(
                self.universe_candidates,
                "universe_candidates",
                ResearchUniverseCandidate,
            ),
        )
        object.__setattr__(
            self,
            "benchmark_candidates",
            _candidate_tuple(
                self.benchmark_candidates,
                "benchmark_candidates",
                ResearchBenchmarkCandidate,
            ),
        )
        object.__setattr__(
            self,
            "cash_proxy_candidates",
            _candidate_tuple(
                self.cash_proxy_candidates,
                "cash_proxy_candidates",
                ResearchCashProxyCandidate,
            ),
        )
        object.__setattr__(self, "blockers", _string_tuple(self.blockers, "blockers"))
        object.__setattr__(
            self,
            "limitations",
            _string_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "required_follow_up",
            _string_tuple(self.required_follow_up, "required_follow_up"),
        )
        object.__setattr__(
            self,
            "non_claims",
            _required_non_claims(self.non_claims),
        )
        _validate_unique_candidate_ids(
            self.source_candidates,
            "source_candidates",
            "source_id",
        )
        _validate_unique_candidate_ids(
            self.universe_candidates,
            "universe_candidates",
            "universe_id",
        )
        _validate_unique_candidate_ids(
            self.benchmark_candidates,
            "benchmark_candidates",
            "benchmark_id",
        )
        _validate_unique_candidate_ids(
            self.cash_proxy_candidates,
            "cash_proxy_candidates",
            "cash_proxy_id",
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic JSON-compatible primitive scope metadata."""

        return {
            "scope_id": self.scope_id,
            "as_of_date": self.as_of_date.isoformat(),
            "approval_state": self.approval_state,
            "source_candidates": [
                candidate.to_dict() for candidate in self.source_candidates
            ],
            "universe_candidates": [
                candidate.to_dict() for candidate in self.universe_candidates
            ],
            "benchmark_candidates": [
                candidate.to_dict() for candidate in self.benchmark_candidates
            ],
            "cash_proxy_candidates": [
                candidate.to_dict() for candidate in self.cash_proxy_candidates
            ],
            "blockers": list(self.blockers),
            "limitations": list(self.limitations),
            "required_follow_up": list(self.required_follow_up),
            "non_claims": list(self.non_claims),
        }


def _required_string(value: str, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return normalized


def _allowed_string(
    value: str,
    field_name: str,
    allowed_values: tuple[str, ...],
) -> str:
    normalized = _required_string(value, field_name)
    if normalized not in allowed_values:
        allowed = ", ".join(allowed_values)
        raise ValidationError(f"{field_name} must be one of: {allowed}.")

    return normalized


def _plain_date(value: date, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a plain date.")

    return value


def _string_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    if isinstance(values, str):
        raise ValidationError(f"{field_name} must be an iterable of strings.")

    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(f"{field_name} must be an iterable of strings.") from exc

    return tuple(
        _required_string(value, f"{field_name}[{index}]")
        for index, value in enumerate(items)
    )


def _required_string_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    items = _string_tuple(values, field_name)
    if not items:
        raise ValidationError(f"{field_name} must contain at least one string.")

    return items


def _unique_required_string_tuple(
    values: Iterable[str],
    field_name: str,
) -> tuple[str, ...]:
    items = _required_string_tuple(values, field_name)
    if len(frozenset(items)) != len(items):
        raise ValidationError(f"{field_name} must not contain duplicates.")

    return items


def _required_non_claims(values: Iterable[str]) -> tuple[str, ...]:
    items = _required_string_tuple(values, "non_claims")
    missing = tuple(
        claim for claim in REQUIRED_RESEARCH_SCOPE_NON_CLAIMS if claim not in items
    )
    if missing:
        raise ValidationError("non_claims must include required research scope non-claims.")

    return items


def _candidate_tuple(
    values: Iterable[_T],
    field_name: str,
    expected_type: type[_T],
) -> tuple[_T, ...]:
    if isinstance(values, str):
        raise ValidationError(
            f"{field_name} must be an iterable of {expected_type.__name__} values."
        )

    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            f"{field_name} must be an iterable of {expected_type.__name__} values."
        ) from exc

    if not items:
        raise ValidationError(f"{field_name} must contain at least one candidate.")

    for item in items:
        if not isinstance(item, expected_type):
            raise ValidationError(
                f"{field_name} must contain {expected_type.__name__} values."
            )

    return items


def _validate_unique_candidate_ids(
    candidates: Iterable[object],
    field_name: str,
    id_field_name: str,
) -> None:
    ids: list[str] = []
    for candidate in candidates:
        try:
            candidate_id = getattr(candidate, id_field_name)
        except AttributeError as exc:
            raise ValidationError(f"{field_name} contains malformed candidates.") from exc

        ids.append(_required_string(candidate_id, id_field_name))

    if len(frozenset(ids)) != len(ids):
        raise ValidationError(f"{field_name} must not contain duplicate ids.")
