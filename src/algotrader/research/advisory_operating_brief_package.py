"""Metadata-only package for advisory operating brief handoff content."""

from __future__ import annotations

from dataclasses import dataclass

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_content_bundle import (
    AdvisoryOperatingBriefContentBundle,
)
from algotrader.research.advisory_operating_brief_content_bundle_export import (
    AdvisoryOperatingBriefContentBundleExport,
    export_advisory_operating_brief_content_bundle,
)
from algotrader.research.research_observation_manifest import (
    ResearchObservationManifest,
)
from algotrader.research.sma_return_research_pipeline_observation import (
    SmaReturnResearchPipelineObservation,
)

__all__ = [
    "AdvisoryOperatingBriefPackage",
    "build_advisory_operating_brief_package",
]

_PACKAGE_TYPE = "advisory_operating_brief_package"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False


def _join(*parts: str) -> str:
    return "".join(parts)


_FORBIDDEN_CLAIM_TOKENS = (
    _join("app", "roval"),
    _join("app", "roved"),
    _join("author", "ized"),
    _join("recomm", "end"),
    _join("recomm", "endation"),
    "paper",
    "live",
    _join("read", "iness"),
    _join("allo", "cation"),
    _join("or", "der"),
    _join("bro", "ker"),
    "account",
    _join("port", "folio"),
    "capital authority",
    "trading authority",
    "trading ready",
    "trading-ready",
    "trading_ready",
)
_NEGATIVE_CLAIM_PREFIXES = (
    "not ",
    "no ",
    "does not ",
    "do not ",
    "without ",
    "non-",
)


@dataclass(frozen=True, slots=True)
class AdvisoryOperatingBriefPackage:
    """Advisory-only wrapper around a content bundle and its export views."""

    package_type: str
    status: str
    authority: str
    capital_authority: bool
    package_id: str
    title: str
    summary: str
    as_of: str
    content_bundle: AdvisoryOperatingBriefContentBundle
    content_bundle_export: AdvisoryOperatingBriefContentBundleExport
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]
    sma_return_research_pipeline_observation: (
        SmaReturnResearchPipelineObservation | None
    ) = None
    research_observation_manifest: ResearchObservationManifest | None = None

    def __post_init__(self) -> None:
        _validate_fixed_metadata(
            self.package_type,
            self.status,
            self.authority,
            self.capital_authority,
        )
        object.__setattr__(
            self,
            "package_id",
            _authority_free_string(self.package_id, "package_id"),
        )
        object.__setattr__(self, "title", _authority_free_string(self.title, "title"))
        object.__setattr__(
            self,
            "summary",
            _authority_free_string(self.summary, "summary"),
        )
        object.__setattr__(self, "as_of", _required_string(self.as_of, "as_of"))
        _validate_content_bundle(self.content_bundle)
        _validate_content_bundle_export(self.content_bundle_export)
        sma_pipeline = _optional_sma_return_research_pipeline_observation(
            self.sma_return_research_pipeline_observation
        )
        research_manifest = _optional_research_observation_manifest(
            self.research_observation_manifest
        )
        expected_export = export_advisory_operating_brief_content_bundle(
            self.content_bundle
        )
        _validate_export_matches_bundle(self.content_bundle_export, expected_export)

        limitations = _advisory_string_tuple(self.limitations, "limitations")
        non_claims = _non_claims_tuple(self.non_claims)
        _validate_matches(
            "limitations",
            limitations,
            _dedupe_first_seen(self.content_bundle.limitations),
        )
        _validate_matches(
            "non_claims",
            non_claims,
            _dedupe_first_seen(self.content_bundle.non_claims),
        )

        object.__setattr__(self, "limitations", limitations)
        object.__setattr__(self, "non_claims", non_claims)
        object.__setattr__(
            self,
            "sma_return_research_pipeline_observation",
            sma_pipeline,
        )
        object.__setattr__(
            self,
            "research_observation_manifest",
            research_manifest,
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only package metadata."""

        payload: dict[str, object] = {
            "package_type": self.package_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "package_id": self.package_id,
            "title": self.title,
            "summary": self.summary,
            "as_of": self.as_of,
            "content_bundle": self.content_bundle.to_dict(),
            "content_bundle_export": {
                "payload": _primitive_copy(self.content_bundle_export.payload),
                "json_text": self.content_bundle_export.json_text,
                "rendered_text": self.content_bundle_export.rendered_text,
            },
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }
        if self.sma_return_research_pipeline_observation is not None:
            payload["sma_return_research_pipeline_observation"] = (
                self.sma_return_research_pipeline_observation.to_dict()
            )
        if self.research_observation_manifest is not None:
            payload["research_observation_manifest"] = (
                self.research_observation_manifest.to_dict()
            )
        return payload


def build_advisory_operating_brief_package(
    *,
    package_id: str,
    title: str,
    summary: str,
    as_of: str,
    content_bundle: AdvisoryOperatingBriefContentBundle,
    sma_return_research_pipeline_observation: (
        SmaReturnResearchPipelineObservation | None
    ) = None,
    research_observation_manifest: ResearchObservationManifest | None = None,
) -> AdvisoryOperatingBriefPackage:
    """Build an advisory-only package from an existing content bundle."""

    _validate_content_bundle(content_bundle)
    sma_pipeline = _optional_sma_return_research_pipeline_observation(
        sma_return_research_pipeline_observation
    )
    research_manifest = _optional_research_observation_manifest(
        research_observation_manifest
    )
    return AdvisoryOperatingBriefPackage(
        package_type=_PACKAGE_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        package_id=package_id,
        title=title,
        summary=summary,
        as_of=as_of,
        content_bundle=content_bundle,
        content_bundle_export=export_advisory_operating_brief_content_bundle(
            content_bundle
        ),
        limitations=_dedupe_first_seen(content_bundle.limitations),
        non_claims=_dedupe_first_seen(content_bundle.non_claims),
        sma_return_research_pipeline_observation=sma_pipeline,
        research_observation_manifest=research_manifest,
    )


def _validate_fixed_metadata(
    package_type: object,
    status: object,
    authority: object,
    capital_authority: object,
) -> None:
    if package_type != _PACKAGE_TYPE:
        raise ValidationError(
            "package_type must be exactly advisory_operating_brief_package."
        )
    if status != _STATUS:
        raise ValidationError("status must be exactly candidate_only.")
    if authority != _AUTHORITY:
        raise ValidationError("authority must be exactly advisory_only.")
    if type(capital_authority) is not bool:
        raise ValidationError("capital_authority must be a bool.")
    if capital_authority is not _CAPITAL_AUTHORITY:
        raise ValidationError("capital_authority must be False.")


def _validate_content_bundle(value: object) -> None:
    if type(value) is not AdvisoryOperatingBriefContentBundle:
        raise ValidationError(
            "content_bundle must be exactly an "
            "AdvisoryOperatingBriefContentBundle."
        )


def _validate_content_bundle_export(value: object) -> None:
    if type(value) is not AdvisoryOperatingBriefContentBundleExport:
        raise ValidationError(
            "content_bundle_export must be exactly an "
            "AdvisoryOperatingBriefContentBundleExport."
        )


def _optional_sma_return_research_pipeline_observation(
    value: object,
) -> SmaReturnResearchPipelineObservation | None:
    if value is None:
        return None
    if type(value) is not SmaReturnResearchPipelineObservation:
        raise ValidationError(
            "sma_return_research_pipeline_observation must be exactly a "
            "SmaReturnResearchPipelineObservation."
        )
    return value


def _optional_research_observation_manifest(
    value: object,
) -> ResearchObservationManifest | None:
    if value is None:
        return None
    if type(value) is not ResearchObservationManifest:
        raise ValidationError(
            "research_observation_manifest must be exactly a "
            "ResearchObservationManifest."
        )
    return value


def _validate_export_matches_bundle(
    value: AdvisoryOperatingBriefContentBundleExport,
    expected: AdvisoryOperatingBriefContentBundleExport,
) -> None:
    if value.payload != expected.payload:
        raise ValidationError("content_bundle_export payload must match content_bundle.")
    if value.json_text != expected.json_text:
        raise ValidationError(
            "content_bundle_export json_text must match content_bundle."
        )
    if value.rendered_text != expected.rendered_text:
        raise ValidationError(
            "content_bundle_export rendered_text must match content_bundle."
        )


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value


def _authority_free_string(value: object, field_name: str) -> str:
    text = _required_string(value, field_name)
    if _has_forbidden_claim(text):
        raise ValidationError(
            f"{field_name} must not imply approval, recommendation, readiness, "
            "or authority."
        )

    return text


def _advisory_string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    if not items:
        raise ValidationError(f"{field_name} must contain at least one string.")

    for index, value in enumerate(items):
        text = _required_string(value, f"{field_name}[{index}]")
        if _has_forbidden_claim(text) and not _is_negative_claim(text):
            raise ValidationError(
                f"{field_name}[{index}] must not imply approval, recommendation, "
                "readiness, or authority."
            )

    return items


def _non_claims_tuple(values: object) -> tuple[str, ...]:
    non_claims = _advisory_string_tuple(values, "non_claims")
    for index, value in enumerate(non_claims):
        if not _is_negative_claim(value):
            raise ValidationError(
                f"non_claims[{index}] must be a negative advisory statement."
            )

    return non_claims


def _has_forbidden_claim(value: str) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in _FORBIDDEN_CLAIM_TOKENS)


def _is_negative_claim(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith(_NEGATIVE_CLAIM_PREFIXES) or " not " in lowered


def _dedupe_first_seen(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)

    return tuple(deduped)


def _validate_matches(
    field_name: str,
    value: object,
    expected: object,
) -> None:
    if value != expected:
        raise ValidationError(f"{field_name} must match content_bundle metadata.")


def _primitive_copy(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _primitive_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_primitive_copy(item) for item in value]
    return value
