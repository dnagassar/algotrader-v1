"""Deterministic text renderer for advisory content bundle metadata."""

from __future__ import annotations

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_content_bundle import (
    AdvisoryOperatingBriefContentBundle,
)

__all__ = [
    "render_advisory_operating_brief_content_bundle_text",
]

_LINE_BREAK = chr(10)


def render_advisory_operating_brief_content_bundle_text(
    bundle: AdvisoryOperatingBriefContentBundle,
) -> str:
    """Return stable plain text from an existing content bundle."""

    if type(bundle) is not AdvisoryOperatingBriefContentBundle:
        raise ValidationError(
            "bundle must be exactly an AdvisoryOperatingBriefContentBundle."
        )

    payload = bundle.to_dict()
    lines: list[str] = []

    lines.extend(
        (
            "Advisory Operating Brief Content Bundle",
            f"bundle_type: {payload['bundle_type']}",
            f"status: {payload['status']}",
            f"authority: {payload['authority']}",
            f"capital_authority: {payload['capital_authority']}",
            f"title: {payload['title']}",
            f"summary: {payload['summary']}",
            (
                "candidate_research_brief_count: "
                f"{payload['candidate_research_brief_count']}"
            ),
            (
                "strategy_eligibility_brief_count: "
                f"{payload['strategy_eligibility_brief_count']}"
            ),
            "",
            "Candidate Research Briefs",
        )
    )
    for brief_index, candidate_payload in enumerate(
        payload["candidate_research_briefs"],
        start=1,
    ):
        _append_candidate_research_brief(lines, candidate_payload, brief_index)

    lines.extend(("", "Strategy Eligibility Briefs"))
    for brief_index, eligibility_payload in enumerate(
        payload["strategy_eligibility_briefs"],
        start=1,
    ):
        _append_strategy_eligibility_brief(lines, eligibility_payload, brief_index)

    lines.extend(("", "Limitations"))
    _append_values(lines, payload["limitations"])
    lines.extend(("", "Non-Claims"))
    _append_values(lines, payload["non_claims"])

    return _LINE_BREAK.join(lines)


def _append_candidate_research_brief(
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
            "Sections",
        )
    )

    for section_index, section_payload in enumerate(
        payload["sections"],
        start=1,
    ):
        _append_candidate_research_section(
            lines,
            section_payload,
            brief_index,
            section_index,
        )


def _append_candidate_research_section(
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
            "Items",
        )
    )

    for item_index, item_payload in enumerate(
        payload["items"],
        start=1,
    ):
        _append_candidate_research_item(
            lines,
            item_payload,
            brief_index,
            section_index,
            item_index,
        )


def _append_candidate_research_item(
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
            "summary_points:",
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
        )
    )


def _append_strategy_eligibility_brief(
    lines: list[str],
    payload: dict[str, object],
    brief_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"Strategy Eligibility Brief {brief_index}",
            f"brief_type: {payload['brief_type']}",
            f"status: {payload['status']}",
            f"authority: {payload['authority']}",
            f"capital_authority: {payload['capital_authority']}",
            f"title: {payload['title']}",
            f"summary: {payload['summary']}",
            f"section_count: {payload['section_count']}",
            "Sections",
        )
    )

    for section_index, section_payload in enumerate(
        payload["sections"],
        start=1,
    ):
        _append_strategy_eligibility_section(
            lines,
            section_payload,
            brief_index,
            section_index,
        )


def _append_strategy_eligibility_section(
    lines: list[str],
    payload: dict[str, object],
    brief_index: int,
    section_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"Strategy Eligibility Brief {brief_index} Section {section_index}",
            f"section_type: {payload['section_type']}",
            f"status: {payload['status']}",
            f"authority: {payload['authority']}",
            f"capital_authority: {payload['capital_authority']}",
            f"title: {payload['title']}",
            f"summary: {payload['summary']}",
            f"item_count: {payload['item_count']}",
            "Items",
        )
    )

    for item_index, item_payload in enumerate(
        payload["items"],
        start=1,
    ):
        _append_strategy_eligibility_item(
            lines,
            item_payload,
            brief_index,
            section_index,
            item_index,
        )


def _append_strategy_eligibility_item(
    lines: list[str],
    payload: dict[str, object],
    brief_index: int,
    section_index: int,
    item_index: int,
) -> None:
    source_status = payload["source_status"]
    lines.extend(
        (
            "",
            (
                f"Strategy Eligibility Brief {brief_index} "
                f"Section {section_index} Item {item_index}"
            ),
            f"item_type: {payload['item_type']}",
            f"status: {payload['status']}",
            f"authority: {payload['authority']}",
            f"capital_authority: {payload['capital_authority']}",
            f"strategy_id: {payload['strategy_id']}",
            f"strategy_name: {payload['strategy_name']}",
            f"eligibility_state: {payload['eligibility_state']}",
            f"headline: {payload['headline']}",
            f"summary: {payload['summary']}",
            "reasons:",
        )
    )
    _append_values(lines, payload["reasons"])
    lines.extend(("evidence_refs:",))
    _append_values(lines, payload["evidence_refs"])
    lines.extend(("blockers:",))
    _append_values(lines, payload["blockers"])
    lines.extend(("required_next_steps:",))
    _append_values(lines, payload["required_next_steps"])
    lines.extend(("limitations:",))
    _append_values(lines, payload["limitations"])
    lines.extend(("non_claims:",))
    _append_values(lines, payload["non_claims"])
    lines.extend(
        (
            "source_status:",
            f"source_status.eligibility_type: {source_status['eligibility_type']}",
            f"source_status.authority: {source_status['authority']}",
            (
                "source_status.capital_authority: "
                f"{source_status['capital_authority']}"
            ),
        )
    )


def _append_values(lines: list[str], values: object) -> None:
    for value in values:
        lines.append(f"- {value}")
