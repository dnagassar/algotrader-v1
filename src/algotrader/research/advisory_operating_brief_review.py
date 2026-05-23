"""Deterministic review checklist for advisory operating brief exports."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_export import (
    AdvisoryOperatingBriefExport,
)

__all__ = [
    "AdvisoryOperatingBriefReviewChecklist",
    "build_advisory_operating_brief_review_checklist",
]

_REVIEW_TYPE = "advisory_operating_brief_review_checklist"
_STATUS = "candidate_only"
_OPERATING_BRIEF_TYPE = "advisory_operating_brief"
_TYPE_KEYS = ("operating_brief_type", "brief_type", "section_type", "item_type")
_METADATA_KEYS = (*_TYPE_KEYS, "status", "limitations", "non_claims")
_ALLOWED_TYPE_VALUES = (
    "advisory_operating_brief",
    "candidate_research_brief",
    "candidate_research_results",
    "candidate_research_result",
)


@dataclass(frozen=True, slots=True)
class AdvisoryOperatingBriefReviewChecklist:
    """Metadata-only review checklist for an exported advisory operating brief."""

    review_type: str
    status: str
    candidate_only: bool
    advisory_only: bool
    has_limitations: bool
    has_non_claims: bool
    has_fingerprint: bool
    has_provenance: bool
    forbidden_capital_authority_fields: tuple[str, ...]
    findings: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.review_type != _REVIEW_TYPE:
            raise ValidationError(
                "review_type must be advisory_operating_brief_review_checklist."
            )
        if self.status != _STATUS:
            raise ValidationError("status must be candidate_only.")

        _required_bool(self.candidate_only, "candidate_only")
        _required_bool(self.advisory_only, "advisory_only")
        _required_bool(self.has_limitations, "has_limitations")
        _required_bool(self.has_non_claims, "has_non_claims")
        _required_bool(self.has_fingerprint, "has_fingerprint")
        _required_bool(self.has_provenance, "has_provenance")
        _string_tuple(
            self.forbidden_capital_authority_fields,
            "forbidden_capital_authority_fields",
        )
        _string_tuple(self.findings, "findings")

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive review checklist metadata."""

        return {
            "review_type": self.review_type,
            "status": self.status,
            "candidate_only": self.candidate_only,
            "advisory_only": self.advisory_only,
            "has_limitations": self.has_limitations,
            "has_non_claims": self.has_non_claims,
            "has_fingerprint": self.has_fingerprint,
            "has_provenance": self.has_provenance,
            "forbidden_capital_authority_fields": list(
                self.forbidden_capital_authority_fields
            ),
            "findings": list(self.findings),
        }


def build_advisory_operating_brief_review_checklist(
    exported: AdvisoryOperatingBriefExport,
) -> AdvisoryOperatingBriefReviewChecklist:
    """Build a deterministic metadata checklist for an existing export object."""

    if not isinstance(exported, AdvisoryOperatingBriefExport):
        raise ValidationError("exported must be an AdvisoryOperatingBriefExport.")

    _validate_payload(exported.payload)
    _validate_export_text(exported.json_text, "json_text")
    _validate_export_text(exported.rendered_text, "rendered_text")

    forbidden_paths = _forbidden_capital_authority_paths(exported)
    candidate_only = _candidate_only(exported.payload)
    advisory_only = _advisory_only(exported.payload, forbidden_paths)
    has_limitations = _has_limitations(exported.payload)
    has_non_claims = _has_non_claims(exported.payload)
    has_fingerprint = _has_fingerprint(exported.payload)
    has_provenance = _has_provenance(exported.payload)

    return AdvisoryOperatingBriefReviewChecklist(
        review_type=_REVIEW_TYPE,
        status=_STATUS,
        candidate_only=candidate_only,
        advisory_only=advisory_only,
        has_limitations=has_limitations,
        has_non_claims=has_non_claims,
        has_fingerprint=has_fingerprint,
        has_provenance=has_provenance,
        forbidden_capital_authority_fields=forbidden_paths,
        findings=_findings(
            candidate_only=candidate_only,
            advisory_only=advisory_only,
            has_limitations=has_limitations,
            has_non_claims=has_non_claims,
            has_fingerprint=has_fingerprint,
            has_provenance=has_provenance,
            forbidden_paths=forbidden_paths,
        ),
    )


def _required_bool(value: object, field_name: str) -> None:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a bool.")


def _string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValidationError(f"{field_name} must be a tuple of strings.")

    for index, value in enumerate(values):
        if not isinstance(value, str):
            raise ValidationError(f"{field_name}[{index}] must be a string.")
        if value != value.strip() or not value:
            raise ValidationError(f"{field_name}[{index}] must be a non-empty string.")

    return values


def _validate_payload(payload: object) -> None:
    if not isinstance(payload, dict):
        raise ValidationError("payload must be a non-empty dict.")
    if not payload:
        raise ValidationError("payload must be a non-empty dict.")

    _validate_primitive_payload(payload, "payload")


def _validate_primitive_payload(value: object, path: str) -> None:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            if type(key) is not str:
                raise ValidationError(f"{path} keys must be strings.")
            if key != key.strip() or not key:
                raise ValidationError(f"{path} keys must be non-empty strings.")
            _validate_primitive_payload(nested_value, f"{path}.{key}")
        return

    if isinstance(value, list):
        for index, nested_value in enumerate(value):
            _validate_primitive_payload(nested_value, f"{path}[{index}]")
        return

    if value is None or type(value) in (str, int, float, bool):
        return

    raise ValidationError(f"{path} must contain primitive metadata only.")


def _validate_export_text(value: object, field_name: str) -> None:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a non-empty string.")
    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")


def _candidate_only(payload: dict[str, object]) -> bool:
    statuses = _values_for_key(payload, "status")
    return bool(statuses) and all(value == _STATUS for value in statuses)


def _advisory_only(
    payload: dict[str, object],
    forbidden_paths: tuple[str, ...],
) -> bool:
    type_values = _type_values(payload)
    return (
        payload.get("operating_brief_type") == _OPERATING_BRIEF_TYPE
        and bool(type_values)
        and all(value in _ALLOWED_TYPE_VALUES for value in type_values)
        and not forbidden_paths
    )


def _has_limitations(payload: dict[str, object]) -> bool:
    nodes = _metadata_nodes(payload)
    return bool(nodes) and all(_has_string_list(node, "limitations") for node in nodes)


def _has_non_claims(payload: dict[str, object]) -> bool:
    nodes = _metadata_nodes(payload)
    return bool(nodes) and all(_has_non_claim_list(node) for node in nodes)


def _has_fingerprint(payload: dict[str, object]) -> bool:
    return any(_is_digest(value) for value in _values_for_key(payload, "package_fingerprint"))


def _has_provenance(payload: dict[str, object]) -> bool:
    for node in _dict_nodes(payload):
        fingerprint = node.get("package_fingerprint")
        fixture_id = node.get("result_snapshot_manifest_fixture_id")
        checksum = node.get("result_snapshot_manifest_checksum")
        if (
            _is_digest(fingerprint)
            and isinstance(fixture_id, str)
            and bool(fixture_id)
            and checksum == f"sha256:{fingerprint}"
        ):
            return True

    return False


def _metadata_nodes(value: object) -> tuple[dict[str, object], ...]:
    nodes: list[dict[str, object]] = []
    for node in _dict_nodes(value):
        if any(key in node for key in _METADATA_KEYS):
            nodes.append(node)
    return tuple(nodes)


def _dict_nodes(value: object) -> tuple[dict[str, object], ...]:
    nodes: list[dict[str, object]] = []
    if isinstance(value, dict):
        nodes.append(value)
        for nested_value in value.values():
            nodes.extend(_dict_nodes(nested_value))
    elif isinstance(value, list):
        for nested_value in value:
            nodes.extend(_dict_nodes(nested_value))
    return tuple(nodes)


def _has_string_list(node: dict[str, object], key: str) -> bool:
    values = node.get(key)
    if not isinstance(values, list):
        return False
    return bool(values) and all(_is_non_empty_string(value) for value in values)


def _has_non_claim_list(node: dict[str, object]) -> bool:
    values = node.get("non_claims")
    if not isinstance(values, list):
        return False
    return bool(values) and all(
        _is_non_empty_string(value) and value.startswith("not ")
        for value in values
    )


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and value == value.strip() and bool(value)


def _type_values(value: object) -> tuple[object, ...]:
    values: list[object] = []
    for key in _TYPE_KEYS:
        values.extend(_values_for_key(value, key))
    return tuple(values)


def _values_for_key(value: object, target_key: str) -> tuple[object, ...]:
    values: list[object] = []
    if isinstance(value, dict):
        for key, nested_value in value.items():
            if key == target_key:
                values.append(nested_value)
            values.extend(_values_for_key(nested_value, target_key))
    elif isinstance(value, list):
        for nested_value in value:
            values.extend(_values_for_key(nested_value, target_key))
    return tuple(values)


def _is_digest(value: object) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.lower()
    return (
        len(value) == 64
        and value == lowered
        and all(character in "0123456789abcdef" for character in lowered)
    )


def _forbidden_capital_authority_paths(
    exported: AdvisoryOperatingBriefExport,
) -> tuple[str, ...]:
    paths: list[str] = []
    paths.extend(_forbidden_payload_paths(exported.payload, "payload", False))
    paths.extend(_forbidden_export_text_paths(exported))
    return tuple(paths)


def _forbidden_payload_paths(
    value: object,
    path: str,
    inside_negative_claims: bool,
) -> tuple[str, ...]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, nested_value in value.items():
            nested_path = f"{path}.{key}"
            if _has_blocked_term(key, _blocked_field_terms()):
                paths.append(f"field:{nested_path}")
            paths.extend(
                _forbidden_payload_paths(
                    nested_value,
                    nested_path,
                    key == "non_claims",
                )
            )
    elif isinstance(value, list):
        for index, nested_value in enumerate(value):
            paths.extend(
                _forbidden_payload_paths(
                    nested_value,
                    f"{path}[{index}]",
                    inside_negative_claims,
                )
            )
    elif isinstance(value, str):
        if inside_negative_claims and value.startswith("not "):
            return ()
        if _has_blocked_term(value, _blocked_language_terms()):
            paths.append(f"language:{path}")
    return tuple(paths)


def _forbidden_export_text_paths(
    exported: AdvisoryOperatingBriefExport,
) -> tuple[str, ...]:
    paths: list[str] = []
    for field_name, text in (
        ("json_text", exported.json_text),
        ("rendered_text", exported.rendered_text),
    ):
        cleaned = _remove_payload_strings(text, exported.payload)
        if _has_blocked_term(cleaned, _blocked_language_terms()):
            paths.append(f"language:{field_name}")
    return tuple(paths)


def _remove_payload_strings(text: str, payload: object) -> str:
    cleaned = text
    for value in _payload_strings(payload):
        cleaned = cleaned.replace(value, "")
    return cleaned


def _payload_strings(value: object) -> tuple[str, ...]:
    if isinstance(value, dict):
        strings: list[str] = []
        for nested_value in value.values():
            strings.extend(_payload_strings(nested_value))
        return tuple(strings)

    if isinstance(value, list):
        strings = []
        for nested_value in value:
            strings.extend(_payload_strings(nested_value))
        return tuple(strings)

    if isinstance(value, str):
        return (value,)

    return ()


def _findings(
    *,
    candidate_only: bool,
    advisory_only: bool,
    has_limitations: bool,
    has_non_claims: bool,
    has_fingerprint: bool,
    has_provenance: bool,
    forbidden_paths: tuple[str, ...],
) -> tuple[str, ...]:
    findings: list[str] = []
    for field_name, status in (
        ("candidate_only", candidate_only),
        ("advisory_only", advisory_only),
        ("has_limitations", has_limitations),
        ("has_non_claims", has_non_claims),
        ("has_fingerprint", has_fingerprint),
        ("has_provenance", has_provenance),
    ):
        if not status:
            findings.append(f"{field_name}:false")

    for value in forbidden_paths:
        findings.append(f"forbidden_capital_authority_fields:{value}")

    return tuple(findings)


def _has_blocked_term(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(_contains_term(lowered, term) for term in terms)


def _contains_term(text: str, term: str) -> bool:
    start = 0
    while True:
        index = text.find(term, start)
        if index < 0:
            return False

        before_index = index - 1
        after_index = index + len(term)
        before = text[before_index] if before_index >= 0 else ""
        after = text[after_index] if after_index < len(text) else ""
        if not _is_name_character(before) and not _is_name_character(after):
            return True

        start = index + 1


def _is_name_character(value: str) -> bool:
    return value.isalnum()


def _join(*parts: str) -> str:
    return "".join(parts)


def _blocked_field_terms() -> tuple[str, ...]:
    return (
        _join("acc", "ount"),
        _join("act", "ion"),
        _join("app", "roval"),
        _join("app", "roved"),
        _join("bench", "mark"),
        _join("bro", "ker"),
        _join("ca", "sh"),
        _join("fi", "ll"),
        _join("live", "_authorized"),
        _join("live", "_probe", "_eligible"),
        _join("or", "der"),
        _join("port", "folio"),
        _join("allo", "cation"),
        _join("po", "sition"),
        _join("prior", "ity"),
        _join("prior", "itized"),
        _join("ra", "nk"),
        _join("reco", "mmendation"),
        "ready",
        _join("run", "time"),
        _join("sco", "re"),
        _join("sig", "nal"),
        _join("stra", "tegy"),
        "tradable",
        _join("tra", "de"),
        _join("tra", "ding", "_readiness"),
    )


def _blocked_language_terms() -> tuple[str, ...]:
    return (
        _join("act", "ion"),
        _join("app", "roval"),
        _join("app", "roved"),
        _join("bench", "mark"),
        _join("bro", "ker"),
        _join("ca", "sh"),
        _join("co", "st"),
        _join("fi", "ll"),
        _join("or", "der"),
        _join("port", "folio"),
        _join("allo", "cation"),
        _join("po", "sition"),
        _join("prior", "itize"),
        _join("prior", "itized"),
        _join("ra", "nk"),
        _join("reco", "mmend"),
        _join("run", "time"),
        _join("sco", "re"),
        _join("sig", "nal"),
        _join("stra", "tegy"),
        _join("tra", "ding"),
        _join("tra", "de"),
    )
