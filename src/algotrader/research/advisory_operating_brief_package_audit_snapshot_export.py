"""Metadata-only audit snapshot export helper for advisory packages."""

from __future__ import annotations

import hashlib
import json

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_package import (
    AdvisoryOperatingBriefPackage,
)
from algotrader.research.advisory_operating_brief_package_manifest_export import (
    export_advisory_operating_brief_package_research_observation_manifest,
)

__all__ = [
    "export_advisory_operating_brief_package_audit_snapshot",
]


def export_advisory_operating_brief_package_audit_snapshot(
    package: AdvisoryOperatingBriefPackage,
) -> dict[str, object]:
    """Return a deterministic metadata-only package audit snapshot."""

    if type(package) is not AdvisoryOperatingBriefPackage:
        raise ValidationError(
            "package must be exactly an AdvisoryOperatingBriefPackage."
        )

    manifest_payload = (
        export_advisory_operating_brief_package_research_observation_manifest(
            package
        )
    )
    package_payload = package.to_dict()

    return {
        "snapshot_type": "advisory_operating_brief_package_audit_snapshot",
        "schema_version": "1",
        "package_type": package.package_type,
        "status": package.status,
        "authority": package.authority,
        "capital_authority": package.capital_authority,
        "package_id": package.package_id,
        "as_of": package.as_of,
        "package_payload_digest_sha256": _payload_digest(package_payload),
        "manifest_payload_digest_sha256": _payload_digest(manifest_payload),
        "research_observation_manifest": manifest_payload,
    }


def _payload_digest(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        _compact_sorted_json(payload).encode("utf-8")
    ).hexdigest()


def _compact_sorted_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
