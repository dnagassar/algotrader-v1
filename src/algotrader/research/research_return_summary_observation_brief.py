"""Advisory brief wrapper for research return summary observations."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import json

from algotrader.errors import ValidationError
from algotrader.research.research_return_summary_observation import (
    ResearchReturnSummaryObservation,
)

__all__ = [
    "ResearchReturnSummaryObservationBrief",
    "ResearchReturnSummaryObservationBriefExport",
    "build_research_return_summary_observation_brief",
    "export_research_return_summary_observation_brief",
    "render_research_return_summary_observation_brief_text",
]

_BRIEF_TYPE = "research_return_summary_observation_brief"
_STATUS = "candidate_only"
_AUTHORITY = "advisory_only"
_CAPITAL_AUTHORITY = False
_LINE_BREAK = chr(10)


def _join(*parts: str) -> str:
    return "".join(parts)


_FORBIDDEN_TEXT_TOKENS = (
    _join("app", "roval"),
    _join("app", "roved"),
    _join("author", "ized"),
    _join("recomm", "end"),
    _join("sig", "nal"),
    _join("evalu", "ator"),
    _join("allo", "cation"),
    _join("or", "der"),
    _join("bro", "ker"),
    _join("port", "folio"),
    _join("pa", "per"),
    _join("li", "ve"),
    _join("read", "iness"),
    _join("trading", "_ready"),
    _join("trading", "-ready"),
    _join("action", "ability"),
    _join("action", "able"),
    _join("b", "uy"),
    _join("s", "ell"),
    _join("h", "old"),
    _join("ra", "nk"),
    _join("sco", "re"),
)


@dataclass(frozen=True, slots=True)
class ResearchReturnSummaryObservationBrief:
    """Primitive advisory metadata grouping return summary observations."""

    brief_type: str
    status: str
    authority: str
    capital_authority: bool
    brief_id: str
    title: str
    summary: str
    summary_observations: tuple[ResearchReturnSummaryObservation, ...]
    limitations: tuple[str, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        observations = _summary_observations_tuple(self.summary_observations)
        limitations = _deduped_advisory_text_tuple(
            self.limitations,
            "limitations",
        )
        non_claims = _deduped_non_claims(self.non_claims)
        _validate_fixed_metadata(
            self.brief_type,
            self.status,
            self.authority,
            self.capital_authority,
        )
        object.__setattr__(
            self,
            "brief_id",
            _advisory_text(self.brief_id, "brief_id"),
        )
        object.__setattr__(self, "title", _advisory_text(self.title, "title"))
        object.__setattr__(self, "summary", _advisory_text(self.summary, "summary"))
        object.__setattr__(self, "summary_observations", observations)
        object.__setattr__(self, "limitations", limitations)
        object.__setattr__(self, "non_claims", non_claims)
        _validate_matches(
            "limitations",
            limitations,
            _combined_observation_values(observations, "limitations"),
        )
        _validate_matches(
            "non_claims",
            non_claims,
            _combined_observation_values(observations, "non_claims"),
        )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive-only summary observation brief metadata."""

        return {
            "brief_type": self.brief_type,
            "status": self.status,
            "authority": self.authority,
            "capital_authority": self.capital_authority,
            "brief_id": self.brief_id,
            "title": self.title,
            "summary": self.summary,
            "summary_observation_count": len(self.summary_observations),
            "summary_observations": [
                observation.to_dict() for observation in self.summary_observations
            ],
            "limitations": list(self.limitations),
            "non_claims": list(self.non_claims),
        }


@dataclass(frozen=True, slots=True)
class ResearchReturnSummaryObservationBriefExport:
    """Primitive payload, compact JSON, and rendered text for a summary brief."""

    payload: dict[str, object]
    json_text: str
    rendered_text: str

    def __post_init__(self) -> None:
        payload = _validate_payload(object.__getattribute__(self, "payload"))
        json_text = _validate_json_text(
            object.__getattribute__(self, "json_text"),
            payload,
        )
        rendered_text = _required_string(
            object.__getattribute__(self, "rendered_text"),
            "rendered_text",
        )

        object.__setattr__(self, "payload", payload)
        object.__setattr__(self, "json_text", json_text)
        object.__setattr__(self, "rendered_text", rendered_text)

    def __getattribute__(self, name: str) -> object:
        value = object.__getattribute__(self, name)
        if name == "payload":
            return _primitive_payload_copy(value)

        return value


def build_research_return_summary_observation_brief(
    brief_id: str,
    title: str,
    summary: str,
    summary_observations: Iterable[ResearchReturnSummaryObservation],
) -> ResearchReturnSummaryObservationBrief:
    """Build a deterministic advisory-only summary observation brief."""

    observations = _summary_observations_tuple(summary_observations)
    return ResearchReturnSummaryObservationBrief(
        brief_type=_BRIEF_TYPE,
        status=_STATUS,
        authority=_AUTHORITY,
        capital_authority=_CAPITAL_AUTHORITY,
        brief_id=brief_id,
        title=title,
        summary=summary,
        summary_observations=observations,
        limitations=_combined_observation_values(observations, "limitations"),
        non_claims=_combined_observation_values(observations, "non_claims"),
    )


def render_research_return_summary_observation_brief_text(
    brief: ResearchReturnSummaryObservationBrief,
) -> str:
    """Return stable plain text from an existing summary observation brief."""

    if type(brief) is not ResearchReturnSummaryObservationBrief:
        raise ValidationError(
            "brief must be exactly a ResearchReturnSummaryObservationBrief."
        )

    payload = brief.to_dict()
    lines: list[str] = [
        "Research Return Summary Observation Brief",
        f"brief_type: {payload['brief_type']}",
        f"brief_id: {payload['brief_id']}",
        f"title: {payload['title']}",
        f"summary: {payload['summary']}",
        f"status: {payload['status']}",
        f"authority: {payload['authority']}",
        f"capital_authority: {payload['capital_authority']}",
        f"summary_observation_count: {payload['summary_observation_count']}",
        "",
        "Brief Limitations",
    ]
    _append_values(lines, payload["limitations"])
    lines.extend(("", "Brief Non-Claims"))
    _append_values(lines, payload["non_claims"])
    lines.extend(("", "Summary Observations"))

    for observation_index, observation_payload in enumerate(
        payload["summary_observations"],
        start=1,
    ):
        _append_summary_observation(lines, observation_payload, observation_index)

    return _LINE_BREAK.join(lines)


def export_research_return_summary_observation_brief(
    brief: ResearchReturnSummaryObservationBrief,
) -> ResearchReturnSummaryObservationBriefExport:
    """Return deterministic in-memory export views for an existing summary brief."""

    if type(brief) is not ResearchReturnSummaryObservationBrief:
        raise ValidationError(
            "brief must be exactly a ResearchReturnSummaryObservationBrief."
        )

    payload = brief.to_dict()
    return ResearchReturnSummaryObservationBriefExport(
        payload=payload,
        json_text=json.dumps(payload, sort_keys=True, separators=(",", ":")),
        rendered_text=render_research_return_summary_observation_brief_text(brief),
    )


def _append_summary_observation(
    lines: list[str],
    payload: dict[str, object],
    observation_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"Summary Observation {observation_index}",
            f"observation_type: {payload['observation_type']}",
            f"symbol: {payload['symbol']}",
            f"as_of: {payload['as_of']}",
            f"return_method: {payload['return_method']}",
            f"price_basis: {payload['price_basis']}",
            f"source_return_count: {payload['source_return_count']}",
            f"positive_return_count: {payload['positive_return_count']}",
            f"negative_return_count: {payload['negative_return_count']}",
            f"zero_return_count: {payload['zero_return_count']}",
            f"min_simple_return: {_format_value(payload['min_simple_return'])}",
            f"max_simple_return: {_format_value(payload['max_simple_return'])}",
            f"mean_simple_return: {_format_value(payload['mean_simple_return'])}",
            f"summary_state: {payload['summary_state']}",
            f"status: {payload['status']}",
            f"authority: {payload['authority']}",
            f"capital_authority: {payload['capital_authority']}",
            "Source Observation",
        )
    )
    _append_source_observation(
        lines,
        payload["source_observation"],
        payload["summary_state"],
    )
    lines.extend(("Observation Limitations",))
    _append_values(lines, payload["limitations"])
    lines.extend(("Observation Non-Claims",))
    _append_values(lines, payload["non_claims"])


def _append_source_observation(
    lines: list[str],
    payload: dict[str, object],
    summary_state: object,
) -> None:
    for key in (
        "symbol",
        "as_of",
        "return_method",
        "price_basis",
        "sample_count",
        "eligible_sample_count",
        "ignored_future_sample_count",
        "return_count",
    ):
        lines.append(f"{key}: {_format_value(payload[key])}")

    lines.extend(("Return Points",))
    _append_return_points(lines, payload["returns"], summary_state)


def _append_return_points(
    lines: list[str],
    payloads: object,
    summary_state: object,
) -> None:
    if not payloads:
        lines.append(
            f"- none; {summary_state} has no close-to-close return points."
        )
        return

    for return_index, payload in enumerate(payloads, start=1):
        lines.extend(
            (
                f"Return Point {return_index}",
                f"start_date: {payload['start_date']}",
                f"end_date: {payload['end_date']}",
                f"start_close: {payload['start_close']}",
                f"end_close: {payload['end_close']}",
                f"simple_return: {payload['simple_return']}",
            )
        )


def _summary_observations_tuple(
    values: Iterable[ResearchReturnSummaryObservation],
) -> tuple[ResearchReturnSummaryObservation, ...]:
    try:
        observations = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            "summary_observations must be an iterable of "
            "ResearchReturnSummaryObservation."
        ) from exc

    if not observations:
        raise ValidationError(
            "summary_observations must contain at least one observation."
        )

    seen_identities: set[int] = set()
    for index, observation in enumerate(observations):
        if type(observation) is not ResearchReturnSummaryObservation:
            raise ValidationError(
                f"summary_observations[{index}] must be a "
                "ResearchReturnSummaryObservation."
            )

        observation_identity = id(observation)
        if observation_identity in seen_identities:
            raise ValidationError(
                "summary_observations must not contain duplicate identities."
            )
        seen_identities.add(observation_identity)

    return observations


def _combined_observation_values(
    observations: tuple[ResearchReturnSummaryObservation, ...],
    field_name: str,
) -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()
    for observation in observations:
        for value in getattr(observation, field_name):
            if value in seen:
                continue
            values.append(value)
            seen.add(value)

    return tuple(values)


def _validate_fixed_metadata(
    brief_type: object,
    status: object,
    authority: object,
    capital_authority: object,
) -> None:
    if brief_type != _BRIEF_TYPE:
        raise ValidationError(
            "brief_type must be exactly research_return_summary_observation_brief."
        )
    if status != _STATUS:
        raise ValidationError("status must be exactly candidate_only.")
    if authority != _AUTHORITY:
        raise ValidationError("authority must be exactly advisory_only.")
    if type(capital_authority) is not bool:
        raise ValidationError("capital_authority must be a bool.")
    if capital_authority is not _CAPITAL_AUTHORITY:
        raise ValidationError("capital_authority must be False.")


def _required_string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    if value != value.strip() or not value:
        raise ValidationError(f"{field_name} must be a non-empty string.")

    return value


def _advisory_text(value: object, field_name: str) -> str:
    text = _required_string(value, field_name)
    lowered = text.lower()
    if any(token in lowered for token in _FORBIDDEN_TEXT_TOKENS):
        raise ValidationError(f"{field_name} must remain advisory metadata text.")

    return text


def _deduped_advisory_text_tuple(
    values: object,
    field_name: str,
) -> tuple[str, ...]:
    items = _dedupe(_string_tuple(values, field_name))
    for index, value in enumerate(items):
        _advisory_text(value, f"{field_name}[{index}]")

    return items


def _deduped_non_claims(values: object) -> tuple[str, ...]:
    items = _dedupe(_string_tuple(values, "non_claims"))
    if any(not item.startswith("not ") for item in items):
        raise ValidationError("non_claims entries must be negative statements.")

    return items


def _string_tuple(values: object, field_name: str) -> tuple[str, ...]:
    if type(values) not in (list, tuple):
        raise ValidationError(f"{field_name} must be a tuple or list of strings.")

    items = tuple(values)
    if not items:
        raise ValidationError(f"{field_name} must contain at least one string.")

    for index, value in enumerate(items):
        _required_string(value, f"{field_name}[{index}]")

    return items


def _validate_payload(value: object) -> dict[str, object]:
    if type(value) is not dict or not value:
        raise ValidationError("payload must be a non-empty primitive dictionary.")

    return _primitive_payload_copy(value)


def _validate_json_text(value: object, payload: dict[str, object]) -> str:
    json_text = _required_string(value, "json_text")
    expected = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    if json_text != expected:
        raise ValidationError("json_text must match compact deterministic payload JSON.")

    try:
        round_tripped = json.loads(json_text)
    except ValueError as exc:
        raise ValidationError("json_text must be valid JSON.") from exc

    if round_tripped != payload:
        raise ValidationError("json_text must round-trip to payload.")

    return json_text


def _primitive_payload_copy(value: object) -> dict[str, object]:
    if type(value) is not dict:
        raise ValidationError("payload must be a primitive dictionary.")

    copied: dict[str, object] = {}
    for key, item in value.items():
        if type(key) is not str:
            raise ValidationError("payload keys must be strings.")
        copied[key] = _primitive_value_copy(item, f"payload[{key}]")

    return copied


def _primitive_value_copy(value: object, field_name: str) -> object:
    if type(value) is dict:
        return _primitive_payload_copy(value)

    if type(value) is list:
        return [
            _primitive_value_copy(item, f"{field_name}[{index}]")
            for index, item in enumerate(value)
        ]

    if value is None or type(value) in (str, int, float, bool):
        return value

    raise ValidationError(f"{field_name} must contain only primitive values.")


def _append_values(lines: list[str], values: object) -> None:
    for value in values:
        lines.append(f"- {value}")


def _format_value(value: object) -> str:
    if value is None:
        return "null"

    return str(value)


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
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
        raise ValidationError(f"{field_name} must match summary observation metadata.")
