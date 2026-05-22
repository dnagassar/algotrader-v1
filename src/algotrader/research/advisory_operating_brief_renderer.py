"""Deterministic text renderer for advisory operating brief metadata."""

from __future__ import annotations

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief import AdvisoryOperatingBrief

__all__ = [
    "render_advisory_operating_brief_text",
]

_LINE_BREAK = chr(10)


def render_advisory_operating_brief_text(
    brief: AdvisoryOperatingBrief,
) -> str:
    """Return stable plain text from an existing advisory operating brief."""

    if not isinstance(brief, AdvisoryOperatingBrief):
        raise ValidationError("brief must be an AdvisoryOperatingBrief.")

    payload = brief.to_dict()
    lines: list[str] = []

    lines.extend(
        (
            "Advisory Operating Brief",
            f"operating_brief_type: {payload['operating_brief_type']}",
            f"status: {payload['status']}",
            f"title: {payload['title']}",
            (
                "candidate_research_brief_count: "
                f"{payload['candidate_research_brief_count']}"
            ),
            "",
            "Limitations",
        )
    )
    _append_values(lines, payload["limitations"])
    lines.extend(("", "Non-Claims"))
    _append_values(lines, payload["non_claims"])
    lines.extend(("", "Candidate Research Briefs"))

    for brief_index, candidate_payload in enumerate(
        payload["candidate_research_briefs"],
        start=1,
    ):
        _append_candidate_brief(lines, candidate_payload, brief_index)

    return _LINE_BREAK.join(lines)


def _append_candidate_brief(
    lines: list[str],
    payload: dict[str, object],
    brief_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"Candidate Research Brief {brief_index}",
            f"brief_type: {payload['brief_type']}",
            f"status: {payload['status']}",
            f"title: {payload['title']}",
            f"section_count: {payload['section_count']}",
            "Limitations",
        )
    )
    _append_values(lines, payload["limitations"])
    lines.extend(("Non-Claims",))
    _append_values(lines, payload["non_claims"])
    lines.extend(("Sections",))

    for section_index, section_payload in enumerate(
        payload["sections"],
        start=1,
    ):
        _append_section(lines, section_payload, brief_index, section_index)


def _append_section(
    lines: list[str],
    payload: dict[str, object],
    brief_index: int,
    section_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"Candidate Research Brief {brief_index} Section {section_index}",
            f"section_type: {payload['section_type']}",
            f"status: {payload['status']}",
            f"title: {payload['title']}",
            f"item_count: {payload['item_count']}",
            "Limitations",
        )
    )
    _append_values(lines, payload["limitations"])
    lines.extend(("Non-Claims",))
    _append_values(lines, payload["non_claims"])
    lines.extend(("Items",))

    for item_index, item_payload in enumerate(
        payload["items"],
        start=1,
    ):
        _append_item(lines, item_payload, brief_index, section_index, item_index)


def _append_item(
    lines: list[str],
    payload: dict[str, object],
    brief_index: int,
    section_index: int,
    item_index: int,
) -> None:
    lines.extend(
        (
            "",
            (
                f"Candidate Research Brief {brief_index} "
                f"Section {section_index} Item {item_index}"
            ),
            f"item_type: {payload['item_type']}",
            f"status: {payload['status']}",
            f"headline: {payload['headline']}",
            "Summary Points",
        )
    )
    _append_values(lines, payload["summary_points"])
    lines.extend(
        (
            f"package_fingerprint: {payload['package_fingerprint']}",
            f"package_snapshot_id: {payload['package_snapshot_id']}",
            (
                "result_snapshot_manifest_fixture_id: "
                f"{payload['result_snapshot_manifest_fixture_id']}"
            ),
            (
                "result_snapshot_manifest_checksum: "
                f"{payload['result_snapshot_manifest_checksum']}"
            ),
            "Limitations",
        )
    )
    _append_values(lines, payload["limitations"])
    lines.extend(("Non-Claims",))
    _append_values(lines, payload["non_claims"])


def _append_values(lines: list[str], values: object) -> None:
    for value in values:
        lines.append(f"- {value}")
