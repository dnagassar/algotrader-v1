"""Deterministic Markdown rendering for advisory operating board summaries."""

from __future__ import annotations

from algotrader.advisory.operating_brief import AdvisoryLabel
from algotrader.advisory.operating_brief_summary import OperatingBriefBoardSummary
from algotrader.errors import ValidationError

__all__ = ["render_operating_brief_board_summary_markdown"]


_LABEL_SECTIONS = (
    (AdvisoryLabel.RESEARCH_ONLY.value, "Research Only"),
    (AdvisoryLabel.WATCHLIST_ONLY.value, "Watchlist Only"),
    (AdvisoryLabel.PAPER_ELIGIBLE.value, "Paper Eligible"),
    (AdvisoryLabel.LIVE_PROBE_ELIGIBLE.value, "Live Probe Eligible"),
    (AdvisoryLabel.LIVE_AUTHORIZED.value, "Live Authorized"),
)

_REQUIRED_NON_CLAIMS = (
    "The board does not validate profitability.",
    "The board does not rank or score candidates.",
    "The board does not create trading recommendations.",
    "`paper_eligible` does not imply live readiness.",
    "`live_probe_eligible` is operational eligibility only.",
    "`live_authorized` remains constructor-gated by strategy eligibility and risk "
    "authority.",
    "The board does not create broker, portfolio, order, fill, execution, or "
    "runtime behavior.",
)


def render_operating_brief_board_summary_markdown(
    summary: OperatingBriefBoardSummary,
) -> str:
    """Render an already-built operating brief board summary as Markdown."""
    _require_operating_brief_board_summary(summary)
    payload = summary.to_dict()
    lines: list[str] = [
        "# Advisory Operating Board Summary",
        "",
        f"As-of date: {_string_value(payload, 'as_of_date')}",
        "",
        "Advisory status:",
        "This board is advisory metadata only. It is not a trading recommendation, "
        "not a signal, not an order request, and not live-trading authority.",
        "",
        "## Candidate Counts",
        "",
    ]

    _extend_count_lines(lines, payload["candidate_counts_by_label"])
    lines.extend(["## Candidate Groups", ""])
    _extend_candidate_group_lines(lines, payload["candidate_ids_by_label"])
    lines.extend(["## Research Queue", ""])
    _extend_candidate_id_lines(lines, payload["research_queue_candidate_ids"])
    lines.extend(["## Watchlist", ""])
    _extend_candidate_id_lines(lines, payload["watchlist_candidate_ids"])
    lines.extend(["## Paper-Eligible Board IDs", ""])
    _extend_candidate_id_lines(lines, payload["paper_eligible_candidate_ids"])
    lines.extend(["## Live-Probe-Eligible Board IDs", ""])
    _extend_candidate_id_lines(lines, payload["live_probe_eligible_candidate_ids"])
    lines.extend(["## Live-Authorized Metadata", ""])
    lines.append(
        "Live-authorized board ids are metadata only and do not create trading "
        "authority."
    )
    lines.append("")
    lines.extend(["### Board IDs", ""])
    _extend_candidate_id_lines(lines, payload["live_authorized_candidate_ids"])
    lines.extend(["### Source Status", ""])
    _extend_live_authorization_status_lines(
        lines,
        payload["live_authorization_statuses"],
    )
    lines.extend(["## Strategy Blockers", ""])
    _extend_reference_reason_lines(lines, payload["strategy_blockers"], "mandate_id")
    lines.extend(["## Risk Blockers", ""])
    _extend_reference_reason_lines(lines, payload["risk_blockers"], "authority_id")
    lines.extend(["## Uncertainty", ""])
    _extend_candidate_text_lines(
        lines,
        payload["uncertainty_summaries"],
        "uncertainty_factors",
    )
    lines.extend(["## Failure Modes", ""])
    _extend_candidate_text_lines(
        lines,
        payload["failure_mode_summaries"],
        "failure_modes",
    )
    lines.extend(["## Limitations", "", "### Brief", ""])
    _extend_candidate_id_lines(lines, payload["brief_limitations"])
    lines.extend(["### Candidate", ""])
    _extend_candidate_text_lines(lines, payload["candidate_limitations"], "limitations")
    lines.extend(["### Strategy", ""])
    _extend_reference_reason_lines(
        lines,
        payload["strategy_limitations"],
        "mandate_id",
        text_field_name="limitations",
    )
    lines.extend(["### Risk", ""])
    _extend_reference_reason_lines(
        lines,
        payload["risk_limitations"],
        "authority_id",
        text_field_name="limitations",
    )
    lines.extend(["## Non-Claims", ""])
    _extend_bullets(lines, _REQUIRED_NON_CLAIMS)
    lines.extend(["### Source Summary Non-Claims", ""])
    _extend_candidate_id_lines(lines, payload["non_claims"])
    return "\n".join(lines)


def _require_operating_brief_board_summary(summary: object) -> None:
    if not isinstance(summary, OperatingBriefBoardSummary):
        raise ValidationError("summary must be an OperatingBriefBoardSummary.")


def _extend_count_lines(lines: list[str], value: object) -> None:
    counts = _dict_value(value, "candidate_counts_by_label")
    for label_value, _heading in _LABEL_SECTIONS:
        count = counts.get(label_value)
        if type(count) is not int:
            raise ValidationError(f"{label_value} count must be serialized as an int.")
        lines.append(f"- {label_value}: {count}")
    lines.append("")


def _extend_candidate_group_lines(lines: list[str], value: object) -> None:
    groups = _dict_value(value, "candidate_ids_by_label")
    for label_value, heading in _LABEL_SECTIONS:
        lines.extend([f"### {heading} ({label_value})", ""])
        _extend_candidate_id_lines(
            lines,
            groups.get(label_value, []),
            append_blank=False,
        )
        lines.append("")


def _extend_live_authorization_status_lines(lines: list[str], value: object) -> None:
    statuses = _list_value(value, "live_authorization_statuses")
    if not statuses:
        lines.extend(["- None recorded.", ""])
        return

    for status in statuses:
        item = _dict_payload(status, "live_authorization_statuses")
        lines.append(
            "- "
            f"{_string_value(item, 'candidate_id')}: "
            f"advisory_label={_string_value(item, 'advisory_label')}; "
            "strategy_status_present="
            f"{_bool_value(item, 'strategy_status_present')}; "
            "strategy_live_authorized="
            f"{_bool_value(item, 'strategy_live_authorized')}; "
            f"risk_status_present={_bool_value(item, 'risk_status_present')}; "
            "risk_live_authorized="
            f"{_bool_value(item, 'risk_live_authorized')}; "
            f"label_live_authorized={_bool_value(item, 'label_live_authorized')}"
        )
    lines.append("")


def _extend_reference_reason_lines(
    lines: list[str],
    value: object,
    reference_field_name: str,
    *,
    text_field_name: str = "blocking_reasons",
) -> None:
    records = _list_value(value, reference_field_name)
    if not records:
        lines.extend(["- None recorded.", ""])
        return

    for record in records:
        item = _dict_payload(record, reference_field_name)
        reference_id = _optional_string_value(item, reference_field_name)
        text = _joined_text_values(item[text_field_name], text_field_name)
        lines.append(
            f"- {_string_value(item, 'candidate_id')}: "
            f"{reference_field_name}={reference_id}; {text}"
        )
    lines.append("")


def _extend_candidate_text_lines(
    lines: list[str],
    value: object,
    text_field_name: str,
) -> None:
    records = _list_value(value, text_field_name)
    if not records:
        lines.extend(["- None recorded.", ""])
        return

    for record in records:
        item = _dict_payload(record, text_field_name)
        lines.append(
            f"- {_string_value(item, 'candidate_id')}: "
            f"{_joined_text_values(item[text_field_name], text_field_name)}"
        )
    lines.append("")


def _extend_candidate_id_lines(
    lines: list[str],
    value: object,
    *,
    append_blank: bool = True,
) -> None:
    _extend_bullets(lines, _string_list(value, "candidate_ids"))
    if append_blank:
        lines.append("")


def _extend_bullets(lines: list[str], values: tuple[str, ...]) -> None:
    if not values:
        lines.append("- None recorded.")
        return

    for value in values:
        lines.append(f"- {value}")


def _joined_text_values(value: object, field_name: str) -> str:
    values = _string_list(value, field_name)
    if not values:
        return "None recorded."
    return "; ".join(values)


def _dict_value(value: object, field_name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValidationError(f"{field_name} must be serialized as a dict.")
    return value


def _dict_payload(value: object, field_name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValidationError(f"{field_name} entries must be serialized as dicts.")
    return value


def _list_value(value: object, field_name: str) -> list[object]:
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be serialized as a list.")
    return value


def _string_list(value: object, field_name: str) -> tuple[str, ...]:
    items = _list_value(value, field_name)
    strings: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, str):
            raise ValidationError(f"{field_name}[{index}] must be a string.")
        strings.append(item)
    return tuple(strings)


def _string_value(payload: dict[str, object], field_name: str) -> str:
    value = payload[field_name]
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be serialized as a string.")
    return value


def _optional_string_value(payload: dict[str, object], field_name: str) -> str:
    value = payload[field_name]
    if value is None:
        return "not set"
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be serialized as a string.")
    return value


def _bool_value(payload: dict[str, object], field_name: str) -> str:
    value = payload[field_name]
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be serialized as a bool.")
    return "true" if value else "false"
