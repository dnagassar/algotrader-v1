"""Developer preview helpers for synthetic advisory package exports."""

from __future__ import annotations

from algotrader.research.advisory_operating_brief_package import (
    AdvisoryOperatingBriefPackage,
)
from algotrader.research.advisory_operating_brief_package_export import (
    export_advisory_operating_brief_package,
)
from algotrader.research.advisory_operating_brief_package_synthetic import (
    build_synthetic_advisory_operating_brief_package_preview,
)

__all__ = [
    "build_synthetic_advisory_operating_brief_package",
    "render_advisory_operating_brief_package_preview",
]

_PREVIEW_FORMATS = ("text", "json")


def build_synthetic_advisory_operating_brief_package() -> (
    AdvisoryOperatingBriefPackage
):
    """Return the deterministic synthetic advisory package preview."""

    return build_synthetic_advisory_operating_brief_package_preview()


def render_advisory_operating_brief_package_preview(
    output_format: str = "text",
) -> str:
    """Return the deterministic synthetic advisory package export."""

    exported = export_advisory_operating_brief_package(
        build_synthetic_advisory_operating_brief_package_preview()
    )
    if output_format == "text":
        return exported.rendered_text
    if output_format == "json":
        return exported.json_text

    expected = ", ".join(_PREVIEW_FORMATS)
    raise ValueError(
        "unsupported advisory operating brief package preview format: "
        f"{output_format!r}. Expected one of: {expected}."
    )
