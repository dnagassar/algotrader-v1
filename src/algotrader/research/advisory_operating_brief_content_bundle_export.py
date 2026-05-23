"""Deterministic in-memory export for advisory content bundle metadata."""

from __future__ import annotations

from dataclasses import dataclass
import json

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_content_bundle import (
    AdvisoryOperatingBriefContentBundle,
)
from algotrader.research.advisory_operating_brief_content_bundle_renderer import (
    render_advisory_operating_brief_content_bundle_text,
)

__all__ = [
    "AdvisoryOperatingBriefContentBundleExport",
    "export_advisory_operating_brief_content_bundle",
]


@dataclass(frozen=True, slots=True)
class AdvisoryOperatingBriefContentBundleExport:
    """Primitive payload, compact JSON, and rendered text for a content bundle."""

    payload: dict[str, object]
    json_text: str
    rendered_text: str


def export_advisory_operating_brief_content_bundle(
    bundle: AdvisoryOperatingBriefContentBundle,
) -> AdvisoryOperatingBriefContentBundleExport:
    """Return deterministic in-memory export views for an existing content bundle."""

    if type(bundle) is not AdvisoryOperatingBriefContentBundle:
        raise ValidationError(
            "bundle must be exactly an AdvisoryOperatingBriefContentBundle."
        )

    payload = bundle.to_dict()
    return AdvisoryOperatingBriefContentBundleExport(
        payload=payload,
        json_text=json.dumps(payload, sort_keys=True, separators=(",", ":")),
        rendered_text=render_advisory_operating_brief_content_bundle_text(bundle),
    )
