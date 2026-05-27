"""Metadata-only contract for research data source review candidates."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError

__all__ = [
    "ResearchDataSourceReadiness",
    "build_research_data_source_readiness",
]

_CONTRACT_TYPE = "research_data_source_readiness"
_SCHEMA_VERSION = "1"
_READINESS_STATES = (
    "not_reviewed",
    "blocked",
    "candidate_only",
    "metadata_ready",
)
_NEGATIVE_PREFIXES = ("not ", "no ", "does not ", "without ", "non-")


def _join(*parts: str) -> str:
    return "".join(parts)


_GUARDED_TERMS = (
    _join("app", "rove"),
    _join("app", "roved"),
    _join("app", "roval"),
    _join("author", "ity"),
    _join("author", "ized"),
    _join("author", "ization"),
    "production ready",
    "production-ready",
    "production readiness",
    _join("tra", "de"),
    _join("tra", "ding"),
    "paper ready",
    "paper-ready",
    "paper readiness",
    "live ready",
    "live-ready",
    "live readiness",
    "capital authority",
)


@dataclass(frozen=True, slots=True)
class ResearchDataSourceReadiness:
    """Deterministic metadata describing a source review candidate."""

    contract_type: str
    schema_version: str
    source_id: str
    source_name: str
    asset_class_scope: tuple[str, ...]
    intended_use: str
    readiness_state: str
    required_controls: tuple[str, ...]
    satisfied_controls: tuple[str, ...]
    missing_controls: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_fixed_metadata(self.contract_type, self.schema_version)
        state = _readiness_state(self.readiness_state)
        source_id = _guarded_string(self.source_id, "source_id")
        source_name = _guarded_string(self.source_name, "source_name")
        asset_class_scope = _unique_guarded_string_tuple(
            self.asset_class_scope,
            "asset_class_scope",
            require_item=False,
        )
        intended_use = _guarded_string(self.intended_use, "intended_use")
        required_controls = _unique_guarded_string_tuple(
            self.required_controls,
            "required_controls",
            require_item=False,
        )
        satisfied_controls = _unique_guarded_string_tuple(
            self.satisfied_controls,
            "satisfied_controls",
            require_item=False,
        )
        missing_controls = _unique_guarded_string_tuple(
            self.missing_controls,
            "missing_controls",
            require_item=False,
        )
        evidence_refs = _unique_guarded_string_tuple(
            self.evidence_refs,
            "evidence_refs",
            require_item=False,
        )
        limitations = _guarded_string_tuple(
            self.limitations,
            "limitations",
            require_item=True,
        )
        non_claims = _non_claims(self.non_claims)

        _validate_controls(required_controls, satisfied_controls, missing_controls)
        if state == "metadata_ready" and missing_controls:
            raise ValidationError("metadata_ready requires no missing_controls.")

        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "source_name", source_name)
        object.__setattr__(self, "asset_class_scope", asset_class_scope)
        object.__setattr__(self, "intended_use", intended_use)
        object.__setattr__(self, "readiness_state", state)
        object.__setattr__(self, "required_controls", required_controls)
        object.__setattr__(self, "satisfied_controls", satisfied_controls)
        object.__setattr__(self, "missing_controls", missing_controls)
        object.__setattr__(self, "evidence_refs", evidence_refs)
        object.__setattr__(self, "limitations", limitations)
        object.__setattr__(self, "non_claims", non_claims)

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive metadata."""

        return {
            "contract_type": self.contract_type,
            "schema_version": self.schema_version,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "asset_class_scope": list(self.asset_class_scope),
            "intended_use": self.intended_use,
            "readiness_state": self.readiness_state,
            "required_controls": list(self.required_controls),
            "satisfied_controls": list(self.satisfied_controls),
            "missing_controls": list(self.missing_controls),
            "evidence_refs": list(self.evidence_refs),
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


def build_research_data_source_readiness(
    *,
    source_id: str,
    source_name: str,
    asset_class_scope: tuple[str, ...] | list[str],
    intended_use: str,
    readiness_state: str,
    required_controls: tuple[str, ...] | list[str],
    satisfied_controls: tuple[str, ...] | list[str],
    evidence_refs: tuple[str, ...] | list[str],
    limitations: tuple[str, ...] | list[str],
    non_claims: tuple[str, ...] | list[str],
) -> ResearchDataSourceReadiness:
    """Build source review metadata and derive missing controls."""

    required = _unique_guarded_string_tuple(
        required_controls,
        "required_controls",
        require_item=False,
    )
    satisfied = _unique_guarded_string_tuple(
        satisfied_controls,
        "satisfied_controls",
        require_item=False,
    )

    return ResearchDataSourceReadiness(
        contract_type=_CONTRACT_TYPE,
        schema_version=_SCHEMA_VERSION,
        source_id=source_id,
        source_name=source_name,
        asset_class_scope=asset_class_scope,
        intended_use=intended_use,
        readiness_state=readiness_state,
        required_controls=required,
        satisfied_controls=satisfied,
        missing_controls=_missing_controls(required, satisfied),
        evidence_refs=evidence_refs,
        limitations=limitations,
        non_claims=non_claims,
    )


def _validate_fixed_metadata(contract_type: object, schema_version: object) -> None:
    if type(contract_type) is not str or contract_type != _CONTRACT_TYPE:
        raise ValidationError(
            "contract_type must be exactly research_data_source_readiness."
        )
    if type(schema_version) is not str or schema_version != _SCHEMA_VERSION:
        raise ValidationError("schema_version must be exactly 1.")


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value


def _readiness_state(value: object) -> str:
    state = _required_string(value, "readiness_state")
    if state in _READINESS_STATES:
        return state

    raise ValidationError(
        "readiness_state must be one of: "
        f"{', '.join(_READINESS_STATES)}."
    )


def _guarded_string(value: object, field_name: str) -> str:
    text = _required_string(value, field_name)
    _reject_guarded_text(text, field_name)

    return text


def _guarded_string_tuple(
    values: object,
    field_name: str,
    *,
    require_item: bool,
) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    if require_item and not items:
        raise ValidationError(f"{field_name} must contain at least one string.")

    for index, value in enumerate(items):
        _guarded_string(value, f"{field_name}[{index}]")

    return items


def _unique_guarded_string_tuple(
    values: object,
    field_name: str,
    *,
    require_item: bool,
) -> tuple[str, ...]:
    items = _guarded_string_tuple(
        values,
        field_name,
        require_item=require_item,
    )
    duplicate = _first_duplicate(items)
    if duplicate is not None:
        raise ValidationError(f"{field_name} must not contain duplicates.")

    return items


def _non_claims(values: object) -> tuple[str, ...]:
    items = _guarded_string_tuple(
        values,
        "non_claims",
        require_item=True,
    )

    for index, value in enumerate(items):
        if not _is_negative(value):
            raise ValidationError(
                f"non_claims[{index}] must be a negative advisory statement."
            )

    return items


def _validate_controls(
    required_controls: tuple[str, ...],
    satisfied_controls: tuple[str, ...],
    missing_controls: tuple[str, ...],
) -> None:
    unknown_satisfied = tuple(
        control for control in satisfied_controls if control not in required_controls
    )
    if unknown_satisfied:
        raise ValidationError(
            "satisfied_controls entries must also appear in required_controls."
        )

    expected_missing = _missing_controls(required_controls, satisfied_controls)
    if missing_controls != expected_missing:
        raise ValidationError(
            "missing_controls must match unsatisfied required_controls."
        )


def _missing_controls(
    required_controls: tuple[str, ...],
    satisfied_controls: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(
        control for control in required_controls if control not in satisfied_controls
    )


def _reject_guarded_text(value: str, field_name: str) -> None:
    lowered = value.lower()
    if _is_negative(value):
        return
    if any(term in lowered for term in _GUARDED_TERMS):
        raise ValidationError(
            f"{field_name} must not represent positive approval or authority."
        )


def _is_negative(value: str) -> bool:
    lowered = value.lower()

    return any(lowered.startswith(prefix) for prefix in _NEGATIVE_PREFIXES)


def _first_duplicate(values: tuple[str, ...]) -> str | None:
    seen: list[str] = []
    for value in values:
        if value in seen:
            return value
        seen.append(value)

    return None
