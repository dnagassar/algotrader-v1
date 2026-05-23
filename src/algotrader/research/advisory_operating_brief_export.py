"""Deterministic in-memory export for advisory operating brief metadata."""

from __future__ import annotations

from dataclasses import dataclass
import json

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief import AdvisoryOperatingBrief
from algotrader.research.advisory_operating_brief_renderer import (
    render_advisory_operating_brief_text,
)

__all__ = [
    "AdvisoryOperatingBriefExport",
    "export_advisory_operating_brief",
]


@dataclass(frozen=True, slots=True)
class AdvisoryOperatingBriefExport:
    """Primitive payload, compact JSON, and rendered text for a brief."""

    payload: dict[str, object]
    json_text: str
    rendered_text: str


def export_advisory_operating_brief(
    brief: AdvisoryOperatingBrief,
) -> AdvisoryOperatingBriefExport:
    """Return deterministic in-memory export views for an existing brief."""

    if not isinstance(brief, AdvisoryOperatingBrief):
        raise ValidationError("brief must be an AdvisoryOperatingBrief.")

    payload = brief.to_dict()
    return AdvisoryOperatingBriefExport(
        payload=payload,
        json_text=json.dumps(payload, sort_keys=True, separators=(",", ":")),
        rendered_text=render_advisory_operating_brief_text(brief),
    )
