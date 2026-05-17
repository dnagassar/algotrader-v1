"""Deterministic Markdown rendering for advisory operating briefs."""

from __future__ import annotations

from algotrader.advisory.operating_brief import OperatingBrief
from algotrader.errors import ValidationError

__all__ = ["render_operating_brief_markdown"]


def render_operating_brief_markdown(brief: OperatingBrief) -> str:
    """Render an already-validated operating brief as Markdown."""
    _require_operating_brief(brief)
    payload = brief.to_dict()
    lines: list[str] = [
        "# Advisory Operating Brief",
        "",
        f"As-of date: {payload['as_of_date']}",
        "",
        "Advisory status:",
        "This brief is advisory metadata only. It is not a trading recommendation, "
        "not a signal, not an order request, and not live-trading authority.",
        "",
        "## Candidate Dossiers",
        "",
    ]

    _extend_dossier_lines(lines, payload["dossiers"])
    lines.extend(
        [
            "## Strategy Eligibility",
            "",
        ]
    )
    _extend_strategy_status_lines(lines, payload["strategy_statuses"])
    lines.extend(
        [
            "## Risk Authority",
            "",
        ]
    )
    _extend_risk_status_lines(lines, payload["risk_statuses"])
    lines.extend(
        [
            "## Non-Claims",
            "",
            "- The brief does not validate profitability.",
            "- `paper_eligible` does not imply live readiness.",
            "- `live_probe_eligible` is operational eligibility only.",
            "- `live_authorized` must remain constructor-gated by strategy "
            "eligibility and risk authority.",
            "- The brief does not create broker, portfolio, order, fill, "
            "execution, or runtime behavior.",
            "",
        ]
    )
    return "\n".join(lines)


def _require_operating_brief(brief: object) -> None:
    if not isinstance(brief, OperatingBrief):
        raise ValidationError("brief must be an OperatingBrief.")


def _extend_dossier_lines(lines: list[str], dossiers: object) -> None:
    items = _list_value(dossiers)
    if not items:
        lines.extend(["No candidate dossiers recorded.", ""])
        return

    for index, dossier in enumerate(items, start=1):
        lines.extend(
            [
                f"### {index}. {_string_value(dossier, 'candidate_id')}",
                "",
                f"- Candidate id: {_string_value(dossier, 'candidate_id')}",
                f"- Title: {_string_value(dossier, 'title')}",
                f"- Advisory label: {_string_value(dossier, 'advisory_label')}",
                f"- Thesis/context: {_string_value(dossier, 'summary')}",
                "- Uncertainty:",
            ]
        )
        _extend_bullets(lines, dossier["uncertainty_factors"])
        lines.append("- Failure modes:")
        _extend_bullets(lines, dossier["failure_modes"])
        lines.append("- Next questions / research needs:")
        _extend_bullets(lines, dossier["next_questions"])
        lines.append("- Limitations / non-claims:")
        _extend_bullets(lines, dossier["limitations"])
        lines.append("")


def _extend_strategy_status_lines(lines: list[str], statuses: object) -> None:
    items = _list_value(statuses)
    if not items:
        lines.extend(["No strategy eligibility statuses recorded.", ""])
        return

    for index, status in enumerate(items, start=1):
        lines.extend(
            [
                f"### {index}. {_string_value(status, 'candidate_id')}",
                "",
                f"- Candidate id: {_string_value(status, 'candidate_id')}",
                f"- Mandate id: {_optional_string_value(status, 'mandate_id')}",
                f"- Mandate approved: {_bool_value(status, 'mandate_approved')}",
                f"- Evidence approved: {_bool_value(status, 'evidence_approved')}",
                "- Evidence refs:",
            ]
        )
        _extend_bullets(lines, status["evidence_refs"])
        lines.extend(
            [
                "- Eligibility flags:",
                f"  - paper_eligible: {_bool_value(status, 'paper_eligible')}",
                "  - live_probe_eligible: "
                f"{_bool_value(status, 'live_probe_eligible')}",
                f"  - live_authorized: {_bool_value(status, 'live_authorized')}",
                "- Blocking reasons:",
            ]
        )
        _extend_bullets(lines, status["blocking_reasons"])
        lines.append("- Limitations:")
        _extend_bullets(lines, status["limitations"])
        lines.append("")


def _extend_risk_status_lines(lines: list[str], statuses: object) -> None:
    items = _list_value(statuses)
    if not items:
        lines.extend(["No risk authority statuses recorded.", ""])
        return

    for index, status in enumerate(items, start=1):
        lines.extend(
            [
                f"### {index}. {_string_value(status, 'candidate_id')}",
                "",
                f"- Candidate id: {_string_value(status, 'candidate_id')}",
                f"- Authority id: {_optional_string_value(status, 'authority_id')}",
                "- Authority flags:",
                f"  - paper_allowed: {_bool_value(status, 'paper_allowed')}",
                "  - live_probe_allowed: "
                f"{_bool_value(status, 'live_probe_allowed')}",
                f"  - live_authorized: {_bool_value(status, 'live_authorized')}",
                "- Blocking reasons:",
            ]
        )
        _extend_bullets(lines, status["blocking_reasons"])
        lines.append("- Limitations:")
        _extend_bullets(lines, status["limitations"])
        lines.append("")


def _extend_bullets(lines: list[str], values: object) -> None:
    items = _list_value(values)
    if not items:
        lines.append("  - None recorded.")
        return

    for item in items:
        lines.append(f"  - {item}")


def _list_value(value: object) -> list[dict[str, object]] | list[str]:
    if not isinstance(value, list):
        raise ValidationError("serialized brief field must be a list.")
    return value


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
