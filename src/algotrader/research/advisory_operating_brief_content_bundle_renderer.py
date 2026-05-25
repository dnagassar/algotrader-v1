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
        )
    )
    if "risk_authority_briefs" in payload:
        lines.append(
            "risk_authority_brief_count: "
            f"{payload['risk_authority_brief_count']}"
        )
    if "research_queue_briefs" in payload:
        lines.append(
            "research_queue_brief_count: "
            f"{payload['research_queue_brief_count']}"
        )
    if "sma_research_observation_briefs" in payload:
        lines.append(
            "sma_research_observation_brief_count: "
            f"{payload['sma_research_observation_brief_count']}"
        )
    if "research_return_observation_briefs" in payload:
        lines.append(
            "research_return_observation_brief_count: "
            f"{payload['research_return_observation_brief_count']}"
        )

    lines.extend(("", "Candidate Research Briefs"))
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

    if "risk_authority_briefs" in payload:
        lines.extend(("", "Risk Authority Briefs"))
        for brief_index, risk_payload in enumerate(
            payload["risk_authority_briefs"],
            start=1,
        ):
            _append_risk_authority_brief(lines, risk_payload, brief_index)

    if "research_queue_briefs" in payload:
        lines.extend(("", "Research Queue Briefs"))
        for brief_index, research_queue_payload in enumerate(
            payload["research_queue_briefs"],
            start=1,
        ):
            _append_research_queue_brief(
                lines,
                research_queue_payload,
                brief_index,
            )

    if "sma_research_observation_briefs" in payload:
        lines.extend(("", "SMA Research Observation Briefs"))
        for brief_index, sma_payload in enumerate(
            payload["sma_research_observation_briefs"],
            start=1,
        ):
            _append_sma_research_observation_brief(lines, sma_payload, brief_index)

    if "research_return_observation_briefs" in payload:
        lines.extend(("", "Research Return Observation Briefs"))
        for brief_index, return_payload in enumerate(
            payload["research_return_observation_briefs"],
            start=1,
        ):
            _append_research_return_observation_brief(
                lines,
                return_payload,
                brief_index,
            )

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


def _append_risk_authority_brief(
    lines: list[str],
    payload: dict[str, object],
    brief_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"Risk Authority Brief {brief_index}",
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
        _append_risk_authority_section(
            lines,
            section_payload,
            brief_index,
            section_index,
        )


def _append_risk_authority_section(
    lines: list[str],
    payload: dict[str, object],
    brief_index: int,
    section_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"Risk Authority Brief {brief_index} Section {section_index}",
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
        _append_risk_authority_item(
            lines,
            item_payload,
            brief_index,
            section_index,
            item_index,
        )


def _append_risk_authority_item(
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
                f"Risk Authority Brief {brief_index} "
                f"Section {section_index} Item {item_index}"
            ),
            f"item_type: {payload['item_type']}",
            f"status: {payload['status']}",
            f"authority: {payload['authority']}",
            f"capital_authority: {payload['capital_authority']}",
            f"authority_state: {payload['authority_state']}",
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
    lines.extend(("related_strategy_ids:",))
    _append_values(lines, payload["related_strategy_ids"])
    lines.extend(("limitations:",))
    _append_values(lines, payload["limitations"])
    lines.extend(("non_claims:",))
    _append_values(lines, payload["non_claims"])
    lines.extend(
        (
            "source_status:",
            f"source_status.authority_type: {source_status['authority_type']}",
            f"source_status.authority: {source_status['authority']}",
            (
                "source_status.capital_authority: "
                f"{source_status['capital_authority']}"
            ),
            f"source_status.authority_state: {source_status['authority_state']}",
        )
    )


def _append_research_queue_brief(
    lines: list[str],
    payload: dict[str, object],
    brief_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"Research Queue Brief {brief_index}",
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
        _append_research_queue_section(
            lines,
            section_payload,
            brief_index,
            section_index,
        )


def _append_research_queue_section(
    lines: list[str],
    payload: dict[str, object],
    brief_index: int,
    section_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"Research Queue Brief {brief_index} Section {section_index}",
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
        _append_research_queue_item(
            lines,
            item_payload,
            brief_index,
            section_index,
            item_index,
        )


def _append_research_queue_item(
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
                f"Research Queue Brief {brief_index} "
                f"Section {section_index} Item {item_index}"
            ),
            f"item_type: {payload['item_type']}",
            f"status: {payload['status']}",
            f"authority: {payload['authority']}",
            f"capital_authority: {payload['capital_authority']}",
            f"headline: {payload['headline']}",
            f"summary: {payload['summary']}",
            "source_status:",
            f"source_status.queue_id: {source_status['queue_id']}",
            f"source_status.title: {source_status['title']}",
            f"source_status.research_state: {source_status['research_state']}",
            f"source_status.priority_bucket: {source_status['priority_bucket']}",
            f"source_status.topic: {source_status['topic']}",
            f"source_status.hypothesis: {source_status['hypothesis']}",
            "blockers:",
        )
    )
    _append_values(lines, payload["blockers"])
    lines.extend(("required_next_steps:",))
    _append_values(lines, payload["required_next_steps"])
    lines.extend(("evidence_gaps:",))
    _append_values(lines, payload["evidence_gaps"])
    lines.extend(("related_strategy_ids:",))
    _append_values(lines, payload["related_strategy_ids"])
    lines.extend(("evidence_refs:",))
    _append_values(lines, payload["evidence_refs"])
    lines.extend(("limitations:",))
    _append_values(lines, payload["limitations"])
    lines.extend(("non_claims:",))
    _append_values(lines, payload["non_claims"])


def _append_sma_research_observation_brief(
    lines: list[str],
    payload: dict[str, object],
    brief_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"SMA Research Observation Brief {brief_index}",
            f"brief_type: {payload['brief_type']}",
            f"brief_id: {payload['brief_id']}",
            f"title: {payload['title']}",
            f"summary: {payload['summary']}",
            f"status: {payload['status']}",
            f"authority: {payload['authority']}",
            f"capital_authority: {payload['capital_authority']}",
            f"section_count: {payload['section_count']}",
            "Brief Limitations",
        )
    )
    _append_values(lines, payload["limitations"])
    lines.extend(("Brief Non-Claims",))
    _append_values(lines, payload["non_claims"])
    lines.extend(("Sections",))

    for section_index, section_payload in enumerate(
        payload["sections"],
        start=1,
    ):
        _append_sma_research_observation_section(
            lines,
            section_payload,
            brief_index,
            section_index,
        )


def _append_sma_research_observation_section(
    lines: list[str],
    payload: dict[str, object],
    brief_index: int,
    section_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"SMA Research Observation Brief {brief_index} Section {section_index}",
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

    for item_index, item_payload in enumerate(
        payload["items"],
        start=1,
    ):
        _append_sma_research_observation_item(
            lines,
            item_payload,
            brief_index,
            section_index,
            item_index,
        )


def _append_sma_research_observation_item(
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
                f"SMA Research Observation Brief {brief_index} "
                f"Section {section_index} Item {item_index}"
            ),
            f"item_type: {payload['item_type']}",
            f"headline: {payload['headline']}",
            f"summary: {payload['summary']}",
            f"mechanical_state: {payload['mechanical_state']}",
            f"status: {payload['status']}",
            f"authority: {payload['authority']}",
            f"capital_authority: {payload['capital_authority']}",
            "Source Observation",
        )
    )
    _append_sma_source_observation(lines, payload["source_observation"])
    lines.extend(("Item Limitations",))
    _append_values(lines, payload["limitations"])
    lines.extend(("Item Non-Claims",))
    _append_values(lines, payload["non_claims"])


def _append_sma_source_observation(
    lines: list[str],
    payload: dict[str, object],
) -> None:
    for key in (
        "symbol",
        "as_of",
        "window",
        "sample_count",
        "eligible_sample_count",
        "ignored_future_sample_count",
        "latest_close",
        "sma_value",
        "distance_from_sma",
        "distance_from_sma_pct",
        "position_vs_sma",
    ):
        lines.append(f"{key}: {_format_value(payload[key])}")


def _append_research_return_observation_brief(
    lines: list[str],
    payload: dict[str, object],
    brief_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"Research Return Observation Brief {brief_index}",
            f"brief_type: {payload['brief_type']}",
            f"brief_id: {payload['brief_id']}",
            f"title: {payload['title']}",
            f"summary: {payload['summary']}",
            f"status: {payload['status']}",
            f"authority: {payload['authority']}",
            f"capital_authority: {payload['capital_authority']}",
            f"section_count: {payload['section_count']}",
            "Brief Limitations",
        )
    )
    _append_values(lines, payload["limitations"])
    lines.extend(("Brief Non-Claims",))
    _append_values(lines, payload["non_claims"])
    lines.extend(("Sections",))

    for section_index, section_payload in enumerate(
        payload["sections"],
        start=1,
    ):
        _append_research_return_observation_section(
            lines,
            section_payload,
            brief_index,
            section_index,
        )


def _append_research_return_observation_section(
    lines: list[str],
    payload: dict[str, object],
    brief_index: int,
    section_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"Research Return Observation Brief {brief_index} Section {section_index}",
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

    for item_index, item_payload in enumerate(
        payload["items"],
        start=1,
    ):
        _append_research_return_observation_item(
            lines,
            item_payload,
            brief_index,
            section_index,
            item_index,
        )


def _append_research_return_observation_item(
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
                f"Research Return Observation Brief {brief_index} "
                f"Section {section_index} Item {item_index}"
            ),
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
    _append_research_return_source_observation(
        lines,
        payload["source_observation"],
        payload["mechanical_state"],
    )
    lines.extend(("Item Limitations",))
    _append_values(lines, payload["limitations"])
    lines.extend(("Item Non-Claims",))
    _append_values(lines, payload["non_claims"])


def _append_research_return_source_observation(
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
    _append_research_return_points(lines, payload["returns"], mechanical_state)


def _append_research_return_points(
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
