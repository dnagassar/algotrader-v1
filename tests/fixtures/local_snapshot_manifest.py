"""Synthetic-only LocalSnapshotManifest fixture metadata."""

from __future__ import annotations

import json
from datetime import date

from algotrader.research.local_snapshot_manifest import LocalSnapshotManifest


SYNTHETIC_LOCAL_SNAPSHOT_CHECKSUM_SHA256 = "0" * 64
SYNTHETIC_LOCAL_SNAPSHOT_NON_CLAIMS = (
    "not source approval",
    "not data approval",
    "not universe approval",
    "not benchmark approval",
    "not cash proxy approval",
    "not methodology approval",
    "not parameter approval",
    "not evidence approval",
    "not strategy validation",
    "not trading readiness",
)


def build_synthetic_local_snapshot_manifest() -> LocalSnapshotManifest:
    return LocalSnapshotManifest(
        snapshot_id="synthetic-local-snapshot-manifest-001",
        source_name="Synthetic Placeholder Source",
        source_type="manual_local_snapshot",
        acquisition_date=date(2026, 1, 5),
        observation_start_date=date(2026, 1, 2),
        observation_end_date=date(2026, 1, 3),
        as_of_date=date(2026, 1, 6),
        symbols_policy="synthetic placeholder identifiers only",
        schema_name="synthetic_metadata_schema_v1",
        fields=("synthetic_observation_label", "synthetic_measure_label"),
        adjustment_policy="unknown",
        return_basis="unknown",
        checksum_sha256=SYNTHETIC_LOCAL_SNAPSHOT_CHECKSUM_SHA256,
        storage_uri="synthetic-storage-marker",
        redistribution_status="synthetic fixture only; redistribution not reviewed",
        license_note="synthetic placeholder only; no external terms reviewed",
        provenance_note="synthetic metadata only; no rows inspected",
        limitations=(
            "synthetic metadata only",
            "placeholder schema only",
            "deterministic unit-test fixture only",
        ),
        non_claims=SYNTHETIC_LOCAL_SNAPSHOT_NON_CLAIMS,
        normal_pytest_eligible=False,
    )


def build_synthetic_local_snapshot_manifest_dict() -> dict[str, object]:
    return build_synthetic_local_snapshot_manifest().to_dict()


def build_synthetic_local_snapshot_manifest_json_bytes() -> bytes:
    return json.dumps(
        build_synthetic_local_snapshot_manifest_dict(),
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
