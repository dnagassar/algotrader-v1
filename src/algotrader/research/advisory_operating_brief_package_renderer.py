"""Deterministic text renderer for advisory operating brief packages."""

from __future__ import annotations

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_package import (
    AdvisoryOperatingBriefPackage,
)

__all__ = [
    "render_advisory_operating_brief_package_text",
]

_LINE_BREAK = chr(10)


def render_advisory_operating_brief_package_text(
    package: AdvisoryOperatingBriefPackage,
) -> str:
    """Return stable plain text from an existing advisory package."""

    if type(package) is not AdvisoryOperatingBriefPackage:
        raise ValidationError(
            "package must be exactly an AdvisoryOperatingBriefPackage."
        )

    payload = package.to_dict()
    content_bundle_export = payload["content_bundle_export"]
    lines: list[str] = [
        "Advisory Operating Brief Package",
        f"package_type: {payload['package_type']}",
        f"package_id: {payload['package_id']}",
        f"title: {payload['title']}",
        f"summary: {payload['summary']}",
        f"as_of: {payload['as_of']}",
        f"status: {payload['status']}",
        f"authority: {payload['authority']}",
        f"capital_authority: {payload['capital_authority']}",
        "",
        "Content Bundle",
        content_bundle_export["rendered_text"],
        "",
        "Package Limitations",
    ]
    _append_values(lines, payload["limitations"])
    lines.extend(("", "Package Non-Claims"))
    _append_values(lines, payload["non_claims"])

    return _LINE_BREAK.join(lines)


def _append_values(lines: list[str], values: object) -> None:
    for value in values:
        lines.append(f"- {value}")
