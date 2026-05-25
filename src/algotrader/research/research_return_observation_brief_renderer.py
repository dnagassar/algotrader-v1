"""Deterministic text renderer for research return observation briefs."""

from __future__ import annotations

from algotrader.errors import ValidationError
from algotrader.research.research_return_observation_brief_container import (
    ResearchReturnObservationBrief,
)

__all__ = [
    "render_research_return_observation_brief_text",
]

_LINE_BREAK = chr(10)


def render_research_return_observation_brief_text(
    brief: ResearchReturnObservationBrief,
) -> str:
    """Return stable plain text from an existing return observation brief."""

    if type(brief) is not ResearchReturnObservationBrief:
        raise ValidationError(
            "brief must be exactly a ResearchReturnObservationBrief."
        )

    payload = brief.to_dict()
    lines: list[str] = [
        "Research Return Observation Brief",
        f"brief_type: {payload['brief_type']}",
        f"brief_id: {payload['brief_id']}",
        f"title: {payload['title']}",
        f"summary: {payload['summary']}",
        f"status: {payload['status']}",
        f"authority: {payload['authority']}",
        f"capital_authority: {payload['capital_authority']}",
        f"section_count: {payload['section_count']}",
        "",
        "Brief Limitations",
    ]
    _append_values(lines, payload["limitations"])
    lines.extend(("", "Brief Non-Claims"))
    _append_values(lines, payload["non_claims"])
    lines.extend(("", "Sections"))

    for section_index, section_payload in enumerate(payload["sections"], start=1):
        _append_section(lines, section_payload, section_index)

    return _LINE_BREAK.join(lines)


def _append_section(
    lines: list[str],
    payload: dict[str, object],
    section_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"Section {section_index}",
            f"section_type: {payload['section_type']}",
            f"section_id: {payload['section_id']}",
            f"title: {payload['title']}",
            f"summary: {payload['summary']}",
            f"status: {payload['status']}",
            f"authority: {payload['authority']}",
            f"capital_authority: {payload['capital_authority']}",
            f"item_count: {payload['item_count']}",
            "Section Limitations",
        )
    )
    _append_values(lines, payload["limitations"])
    lines.extend(("Section Non-Claims",))
    _append_values(lines, payload["non_claims"])
    lines.extend(("Items",))

    for item_index, item_payload in enumerate(payload["items"], start=1):
        _append_item(lines, item_payload, section_index, item_index)


def _append_item(
    lines: list[str],
    payload: dict[str, object],
    section_index: int,
    item_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"Section {section_index} Item {item_index}",
            f"item_type: {payload['item_type']}",
            f"headline: {payload['headline']}",
            f"summary: {payload['summary']}",
            f"mechanical_state: {payload['mechanical_state']}",
            f"positive_return_count: {payload['positive_return_count']}",
            f"negative_return_count: {payload['negative_return_count']}",
            f"zero_return_count: {payload['zero_return_count']}",
            f"status: {payload['status']}",
            f"authority: {payload['authority']}",
            f"capital_authority: {payload['capital_authority']}",
            "Source Observation",
        )
    )
    _append_source_observation(
        lines,
        payload["source_observation"],
        payload["mechanical_state"],
    )
    lines.extend(("Item Limitations",))
    _append_values(lines, payload["limitations"])
    lines.extend(("Item Non-Claims",))
    _append_values(lines, payload["non_claims"])


def _append_source_observation(
    lines: list[str],
    payload: dict[str, object],
    mechanical_state: object,
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
    _append_return_points(lines, payload["returns"], mechanical_state)


def _append_return_points(
    lines: list[str],
    payloads: object,
    mechanical_state: object,
) -> None:
    if not payloads:
        lines.append(
            f"- none; {mechanical_state} has no close-to-close return points."
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


def _append_values(lines: list[str], values: object) -> None:
    for value in values:
        lines.append(f"- {value}")


def _format_value(value: object) -> str:
    if value is None:
        return "null"

    return str(value)
