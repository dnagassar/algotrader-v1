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
    if "sma_research_summary_observations" in payload:
        lines.append(
            "sma_research_summary_observation_count: "
            f"{payload['sma_research_summary_observation_count']}"
        )
    if "research_return_observation_briefs" in payload:
        lines.append(
            "research_return_observation_brief_count: "
            f"{payload['research_return_observation_brief_count']}"
        )
    if "research_return_summary_observation_briefs" in payload:
        lines.append(
            "research_return_summary_observation_brief_count: "
            f"{payload['research_return_summary_observation_brief_count']}"
        )
    if "research_data_source_readiness" in payload:
        lines.append(
            "research_data_source_readiness_count: "
            f"{payload['research_data_source_readiness_count']}"
        )
    if "research_data_source_readiness_summaries" in payload:
        lines.append(
            "research_data_source_readiness_summary_count: "
            f"{payload['research_data_source_readiness_summary_count']}"
        )
    if "diagnostic_issues" in payload:
        lines.append(
            "diagnostic_issue_count: "
            f"{payload['diagnostic_issue_count']}"
        )
    if "advisory_sections" in payload:
        lines.append(
            "advisory_section_count: "
            f"{payload['advisory_section_count']}"
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

    if "sma_research_summary_observations" in payload:
        lines.extend(("", "SMA Research Summary Observations"))
        for observation_index, summary_payload in enumerate(
            payload["sma_research_summary_observations"],
            start=1,
        ):
            _append_sma_research_summary_observation(
                lines,
                summary_payload,
                observation_index,
            )

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

    if "research_return_summary_observation_briefs" in payload:
        lines.extend(("", "Research Return Summary Observation Briefs"))
        for brief_index, summary_payload in enumerate(
            payload["research_return_summary_observation_briefs"],
            start=1,
        ):
            _append_research_return_summary_observation_brief(
                lines,
                summary_payload,
                brief_index,
            )

    if "research_data_source_readiness" in payload:
        lines.extend(("", "Research Data Source Readiness Diagnostics"))
        for readiness_index, readiness_payload in enumerate(
            payload["research_data_source_readiness"],
            start=1,
        ):
            _append_research_data_source_readiness(
                lines,
                readiness_payload,
                readiness_index,
            )

    if "research_data_source_readiness_summaries" in payload:
        lines.extend(("", "Research Data Source Readiness Summary Diagnostics"))
        for summary_index, summary_payload in enumerate(
            payload["research_data_source_readiness_summaries"],
            start=1,
        ):
            _append_research_data_source_readiness_summary(
                lines,
                summary_payload,
                summary_index,
            )

    if "diagnostic_issues" in payload:
        lines.extend(("", "Diagnostic Issues"))
        for issue_index, issue_payload in enumerate(
            payload["diagnostic_issues"],
            start=1,
        ):
            _append_diagnostic_issue(lines, issue_payload, issue_index)

    if "advisory_sections" in payload:
        lines.extend(("", "Advisory Sections"))
        for section_index, section_payload in enumerate(
            payload["advisory_sections"],
            start=1,
        ):
            _append_advisory_section(lines, section_payload, section_index)

    if "advisory_view" in payload:
        lines.extend(("", "Advisory View"))
        _append_advisory_view(lines, payload["advisory_view"])

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


def _append_sma_research_summary_observation(
    lines: list[str],
    payload: dict[str, object],
    observation_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"SMA Research Summary Observation {observation_index}",
            f"observation_type: {payload['observation_type']}",
            f"status: {payload['status']}",
            f"authority: {payload['authority']}",
            f"capital_authority: {payload['capital_authority']}",
            f"research_scope: {payload['research_scope']}",
            f"total_observation_count: {payload['total_observation_count']}",
            f"above_sma_count: {payload['above_sma_count']}",
            f"below_sma_count: {payload['below_sma_count']}",
            f"equal_sma_count: {payload['equal_sma_count']}",
            (
                "insufficient_history_count: "
                f"{payload['insufficient_history_count']}"
            ),
            f"summary_state: {payload['summary_state']}",
            "Source Observations",
        )
    )
    _append_sma_summary_source_observations(
        lines,
        payload["source_observations"],
        payload["summary_state"],
    )
    lines.extend(("Observation Limitations",))
    _append_values(lines, payload["limitations"])
    lines.extend(("Observation Non-Claims",))
    _append_values(lines, payload["non_claims"])


def _append_sma_summary_source_observations(
    lines: list[str],
    payloads: object,
    summary_state: object,
) -> None:
    if not payloads:
        lines.append(f"- none; {summary_state} has no source SMA observations.")
        return

    for source_index, payload in enumerate(payloads, start=1):
        lines.extend(("", f"Source SMA Observation {source_index}"))
        _append_sma_source_observation(lines, payload)


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


def _append_research_return_summary_observation_brief(
    lines: list[str],
    payload: dict[str, object],
    brief_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"Research Return Summary Observation Brief {brief_index}",
            f"brief_type: {payload['brief_type']}",
            f"brief_id: {payload['brief_id']}",
            f"title: {payload['title']}",
            f"summary: {payload['summary']}",
            f"status: {payload['status']}",
            f"authority: {payload['authority']}",
            f"capital_authority: {payload['capital_authority']}",
            f"summary_observation_count: {payload['summary_observation_count']}",
            "Brief Limitations",
        )
    )
    _append_values(lines, payload["limitations"])
    lines.extend(("Brief Non-Claims",))
    _append_values(lines, payload["non_claims"])
    lines.extend(("Summary Observations",))

    for observation_index, observation_payload in enumerate(
        payload["summary_observations"],
        start=1,
    ):
        _append_research_return_summary_observation(
            lines,
            observation_payload,
            brief_index,
            observation_index,
        )


def _append_research_return_summary_observation(
    lines: list[str],
    payload: dict[str, object],
    brief_index: int,
    observation_index: int,
) -> None:
    lines.extend(
        (
            "",
            (
                f"Research Return Summary Observation Brief {brief_index} "
                f"Observation {observation_index}"
            ),
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
    _append_research_return_source_observation(
        lines,
        payload["source_observation"],
        payload["summary_state"],
    )
    lines.extend(("Observation Limitations",))
    _append_values(lines, payload["limitations"])
    lines.extend(("Observation Non-Claims",))
    _append_values(lines, payload["non_claims"])


def _append_research_data_source_readiness(
    lines: list[str],
    payload: dict[str, object],
    readiness_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"Research Data Source Readiness Diagnostic {readiness_index}",
            f"contract_type: {payload['contract_type']}",
            f"schema_version: {payload['schema_version']}",
            f"source_id: {payload['source_id']}",
            f"source_name: {payload['source_name']}",
            "asset_class_scope:",
        )
    )
    _append_values(lines, payload["asset_class_scope"])
    lines.extend(
        (
            f"intended_use: {payload['intended_use']}",
            f"readiness_state: {payload['readiness_state']}",
            "required_controls:",
        )
    )
    _append_values(lines, payload["required_controls"])
    lines.extend(("satisfied_controls:",))
    _append_values(lines, payload["satisfied_controls"])
    lines.extend(("missing_controls:",))
    _append_values(lines, payload["missing_controls"])
    lines.extend(("evidence_refs:",))
    _append_values(lines, payload["evidence_refs"])
    lines.extend(("limitations:",))
    _append_values(lines, payload["limitations"])
    lines.extend(("non_claims:",))
    _append_values(lines, payload["non_claims"])


def _append_research_data_source_readiness_summary(
    lines: list[str],
    payload: dict[str, object],
    summary_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"Research Data Source Readiness Summary Diagnostic {summary_index}",
            f"summary_type: {payload['summary_type']}",
            f"schema_version: {payload['schema_version']}",
            f"summary_scope: {payload['summary_scope']}",
            f"summary_state: {payload['summary_state']}",
            f"required_control_count: {payload['required_control_count']}",
            f"satisfied_control_count: {payload['satisfied_control_count']}",
            f"missing_control_count: {payload['missing_control_count']}",
            "diagnostic_limitations:",
        )
    )
    _append_values(lines, payload["diagnostic_limitations"])


def _append_diagnostic_issue(
    lines: list[str],
    payload: dict[str, object],
    issue_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"Diagnostic Issue {issue_index}",
            f"source_branch: {payload['source_branch']}",
            f"issue_code: {payload['issue_code']}",
            f"issue_state: {payload['issue_state']}",
            f"diagnostic_message: {payload['diagnostic_message']}",
            "blocking_controls:",
        )
    )
    _append_values(lines, payload["blocking_controls"])
    lines.extend(("limitations:",))
    _append_values(lines, payload["limitations"])


def _append_advisory_section(
    lines: list[str],
    payload: dict[str, object],
    section_index: int,
) -> None:
    lines.extend(
        (
            "",
            f"Advisory Section {section_index}",
            f"section_key: {payload['section_key']}",
            f"section_title: {payload['section_title']}",
            f"section_state: {payload['section_state']}",
            "source_branches:",
        )
    )
    _append_values(lines, payload["source_branches"])
    lines.extend(
        (
            f"item_count: {payload['item_count']}",
            "diagnostic_messages:",
        )
    )
    _append_values(lines, payload["diagnostic_messages"])
    lines.extend(("limitations:",))
    _append_values(lines, payload["limitations"])


def _append_advisory_view(
    lines: list[str],
    payload: dict[str, object],
) -> None:
    lines.extend(
        (
            f"view_key: {payload['view_key']}",
            f"view_title: {payload['view_title']}",
            f"view_state: {payload['view_state']}",
            f"section_count: {payload['section_count']}",
            "section_keys:",
        )
    )
    _append_values(lines, payload["section_keys"])
    lines.extend(("summary_lines:",))
    _append_values(lines, payload["summary_lines"])
    lines.extend(("diagnostic_messages:",))
    _append_values(lines, payload["diagnostic_messages"])
    lines.extend(("limitations:",))
    _append_values(lines, payload["limitations"])


def _append_values(lines: list[str], values: object) -> None:
    for value in values:
        lines.append(f"- {value}")


def _format_value(value: object) -> str:
    if value is None:
        return "null"

    return str(value)
