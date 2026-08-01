"""Terminal forward confirmation of the exact frozen V5.64 composite."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.research import nexustrade_monthly_independent_replication as _base

__all__ = [
    "build_v564_frozen_forward_preregistration",
    "run_v564_frozen_forward_confirmation",
]

_PROTOCOL_ID = "v5_70_v564_frozen_forward_confirmation_v1"
_PROTOCOL_HASH = "7977ef62d5b1da7b658e57aad34e85f91438659d9c5c639726abb23ee10e8e37"
_RECEIPT_HASH = "9ad6db6e4cacf9e5accace6911052fb44f72fbe201609ce15fdbe8ba705a8ef9"
_PARENT_PROTOCOL_HASH = "f24c98daa03462fccd0e73163abfe42f597ab601db83b331ecd4b487e31f4ee0"
_PARENT_ENGINE_HASH = "66d73e4e0cd6160c8f07febe3a80b90eb4eebdd1ea7375b7fb3b23cadeef87f5"
_OLD_DATA_HASH = "d296138a95a86546bdc92678af479e8c8e204b138e2db43f54979a19921c9575"
_OLD_MANIFEST_HASH = "e204a8a1824e5b49ce4d457f12884bfc284d52f99ad3ba07072c978d7223d8e1"
_FORWARD_DATA_HASH = "04344d4a60702dd936b183b20937a41b7f90e6813096a9120fc3b2e642d91688"
_FORWARD_MANIFEST_HASH = "43ae5c6bdd5c6addc2bd7e3d863818229748cad5d0b28f3cad569676340cb1ca"
_PARENT_ARTIFACT_HASHES = {
    "preregistration.json": "4c54d6c14de2579d1671a8257be6750bd49a586296d041fea95a3fe40e376e3c",
    "replication_results.json": "ca9f0177b0b42a3ec888b13799fdd3d39c5c5ae9caacedd2245a0292b42396da",
    "replication_summary.md": "af3b527db055c4568db7125047dad97ba9492fa55d5bbf2c3a6b6cc9002f41df",
    "manifest.json": "96338ea291f40ea7d9a1ea4a0d45dd17ed5a60c856333150655701f64841dcf6",
}
_ROOT = Path("runs/v5_70_v564_frozen_forward_confirmation")
_DATA = _ROOT / "forward_canonical.csv"
_DATA_MANIFEST = _ROOT / "data_acquisition/canonical_data_manifest.json"
_PROTOCOL = Path("docs/design/v5_70_v564_frozen_forward_confirmation.md")
_RECEIPT = Path("docs/design/v5_70_v564_forward_data_receipt.md")
_PARENT_PROTOCOL = Path("docs/design/v5_64_nexustrade_monthly_independent_replication.md")
_PARENT_ENGINE = Path("src/algotrader/research/nexustrade_monthly_independent_replication.py")
_PARENT_ROOT = Path("runs/v5_64_nexustrade_monthly_independent_replication")
_OLD_DATA = Path("runs/operator_input/multi_etf_adjusted_daily_canonical.csv")
_OLD_MANIFEST = Path("runs/v5_63_nexustrade_canonical_data/canonical_data_manifest.json")

_OLD_WINDOWS = (
    _base.ReplicationWindow("oos_walk_forward_1", date(2024, 3, 25), date(2024, 7, 24)),
    _base.ReplicationWindow("oos_walk_forward_2", date(2024, 7, 25), date(2024, 11, 21)),
    _base.ReplicationWindow("oos_walk_forward_3", date(2024, 11, 22), date(2025, 3, 28)),
)
_FORWARD_WINDOWS = (
    _base.ReplicationWindow("forward_fold_1", date(2025, 3, 31), date(2025, 8, 29)),
    _base.ReplicationWindow("forward_fold_2", date(2025, 9, 2), date(2026, 1, 30)),
    _base.ReplicationWindow("forward_fold_3", date(2026, 2, 2), date(2026, 6, 30)),
)


def _old_config() -> _base.NexusTradeMonthlyIndependentReplicationConfig:
    return _base.NexusTradeMonthlyIndependentReplicationConfig(
        data_path=_OLD_DATA,
        data_manifest_path=_OLD_MANIFEST,
        preregistration_path=_PARENT_PROTOCOL,
        expected_preregistration_sha256=_PARENT_PROTOCOL_HASH,
        expected_data_sha256=_OLD_DATA_HASH,
        expected_data_manifest_sha256=_OLD_MANIFEST_HASH,
        walk_forward_windows=_OLD_WINDOWS,
    )


def _forward_config() -> _base.NexusTradeMonthlyIndependentReplicationConfig:
    return _base.NexusTradeMonthlyIndependentReplicationConfig(
        output_root=_ROOT,
        data_path=_DATA,
        data_manifest_path=_DATA_MANIFEST,
        preregistration_path=_PARENT_PROTOCOL,
        expected_preregistration_sha256=_PARENT_PROTOCOL_HASH,
        expected_data_sha256=_FORWARD_DATA_HASH,
        expected_data_manifest_sha256=_FORWARD_MANIFEST_HASH,
        data_end=date(2026, 6, 30),
        oos_start=date(2025, 3, 29),
        oos_end=date(2026, 6, 30),
        walk_forward_windows=_FORWARD_WINDOWS,
        required_common_session_count=1883,
        required_oos_session_count=314,
    )


def build_v564_frozen_forward_preregistration() -> dict[str, object]:
    """Build the committed terminal contract without reading market data."""

    _validate_tracked_dependencies()
    return {
        "record_type": "v564_frozen_forward_confirmation_preregistration",
        "schema_version": 1,
        "protocol_id": _PROTOCOL_ID,
        "protocol_sha256": _PROTOCOL_HASH,
        "data_receipt_sha256": _RECEIPT_HASH,
        "candidate_id": _base.NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID,
        "claim": "exact_frozen_v564_forward_confirmation",
        "forward_start_boundary": "2025-03-28",
        "forward_first_observed_session": "2025-03-31",
        "forward_end": "2026-06-30",
        "forward_session_count": 314,
        "walk_forward_windows": [item.to_dict() for item in _FORWARD_WINDOWS],
        "frozen_mechanics": True,
        "parameter_search_performed": False,
        "terminal_routes": ["preview_review", "close_stock_filter_family"],
        "paper_promotion_allowed": False,
        "source_metrics_trust": "untrusted_external_evidence",
        "safety": _safety(),
    }


def run_v564_frozen_forward_confirmation(
    output_root: Path | str = _ROOT,
) -> dict[str, object]:
    """Reproduce V5.64, run its exact mechanics forward, and write artifacts."""

    root = Path(output_root)
    preregistration = build_v564_frozen_forward_preregistration()
    reproduction = _reproduce_frozen_parent()
    config = _forward_config()
    data = _base._load_aligned_data(config)
    _base._validate_chronology(data, config)
    base_preregistration = _base.build_nexustrade_monthly_independent_preregistration(config)
    forward_result = _base._build_replication_result(config, data, base_preregistration)
    composite = next(
        item for item in forward_result["candidates"]
        if item["candidate_id"] == _base.NEXUSTRADE_MONTHLY_INDEPENDENT_COMPOSITE_ID
    )
    all_passed = composite["gates"]["all_applicable_gates_passed"] is True
    terminal_route = "preview_review" if all_passed else "close_stock_filter_family"
    result = {
        "record_type": "v564_frozen_forward_confirmation_result",
        "schema_version": 1,
        "protocol_id": _PROTOCOL_ID,
        "preregistration": preregistration,
        "frozen_parent_reproduction": reproduction,
        "data_admission": {
            "data_sha256": data.data_sha256,
            "manifest_sha256": data.data_manifest_sha256,
            "common_session_count": len(data.dates),
            "forward_session_count": 314,
            "receipt_sha256": _RECEIPT_HASH,
        },
        "forward_replication": forward_result,
        "terminal_decision": {
            "candidate_id": composite["candidate_id"],
            "all_applicable_gates_passed": all_passed,
            "route": terminal_route,
            "failure_closes_stock_filter_family": not all_passed,
            "paper_promotion_allowed": False,
        },
        "safety": _safety(),
    }
    root.mkdir(parents=True, exist_ok=True)
    prereg_path = root / "preregistration.json"
    result_path = root / "forward_confirmation_results.json"
    summary_path = root / "forward_confirmation_summary.md"
    _base._write_json_atomic(prereg_path, preregistration)
    _base._write_json_atomic(result_path, result)
    _base._write_text_atomic(summary_path, _summary(result, composite))
    manifest = {
        "record_type": "v564_frozen_forward_confirmation_manifest",
        "schema_version": 1,
        "protocol_id": _PROTOCOL_ID,
        "artifacts": [_artifact(path) for path in (prereg_path, result_path, summary_path)],
        "inputs": {
            "data_sha256": _FORWARD_DATA_HASH,
            "data_manifest_sha256": _FORWARD_MANIFEST_HASH,
            "protocol_sha256": _PROTOCOL_HASH,
            "receipt_sha256": _RECEIPT_HASH,
        },
        "safety": _safety(),
    }
    manifest_path = root / "manifest.json"
    _base._write_json_atomic(manifest_path, manifest)
    completed = dict(result)
    completed["artifact_manifest"] = manifest
    completed["artifact_manifest_sha256"] = _hash(manifest_path)
    return completed


def _reproduce_frozen_parent() -> dict[str, object]:
    for name, expected in _PARENT_ARTIFACT_HASHES.items():
        if _hash(_PARENT_ROOT / name) != expected:
            raise ValidationError(f"frozen V5.64 artifact hash mismatch: {name}")
    config = _old_config()
    data = _base._load_aligned_data(config)
    _base._validate_chronology(data, config)
    prereg = _base.build_nexustrade_monthly_independent_preregistration(config)
    recorded_prereg = json.loads((_PARENT_ROOT / "preregistration.json").read_text(encoding="utf-8"))
    if prereg != recorded_prereg:
        raise ValidationError("frozen V5.64 preregistration reproduction failed.")
    result = _base._build_replication_result(config, data, prereg)
    recorded_result = json.loads((_PARENT_ROOT / "replication_results.json").read_text(encoding="utf-8"))
    if result != recorded_result:
        raise ValidationError("frozen V5.64 result reproduction failed.")
    if _base._render_summary(result) != (_PARENT_ROOT / "replication_summary.md").read_text(encoding="utf-8"):
        raise ValidationError("frozen V5.64 summary reproduction failed.")
    return {"passed": True, "preregistration_equal": True, "result_equal": True, "summary_equal": True}


def _validate_tracked_dependencies() -> None:
    for path, expected, name in (
        (_PROTOCOL, _PROTOCOL_HASH, "protocol"),
        (_RECEIPT, _RECEIPT_HASH, "data receipt"),
        (_PARENT_PROTOCOL, _PARENT_PROTOCOL_HASH, "V5.64 protocol"),
        (_PARENT_ENGINE, _PARENT_ENGINE_HASH, "V5.64 engine"),
    ):
        if _hash(path) != expected:
            raise ValidationError(f"{name} SHA-256 mismatch.")


def _artifact(path: Path) -> dict[str, object]:
    return {"path": str(path), "sha256": _hash(path), "byte_count": path.stat().st_size}


def _hash(path: Path) -> str:
    if not path.is_file():
        raise ValidationError(f"required file does not exist: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safety() -> dict[str, object]:
    return {
        "offline_replay": True,
        "credential_access": False,
        "network_access": False,
        "nexustrade_access": False,
        "broker_access": False,
        "paper_mutation": False,
        "live_activity": False,
        "paper_promotion_allowed": False,
        "live_authorized": False,
        "unchanged_v557_caps": {
            "entry_order_notional_usd": "25",
            "aggregate_marked_spy_entry_exposure_usd": "60",
            "broker_orders_per_secure_cycle": 1,
            "sleeve_intents_per_utc_day": 2,
        },
    }


def _summary(result: Mapping[str, object], composite: Mapping[str, Any]) -> str:
    decision = result["terminal_decision"]
    return "\n".join((
        "# V5.70 Frozen V5.64 Forward Confirmation",
        "",
        f"- Candidate: `{composite['candidate_id']}`.",
        f"- Terminal route: `{decision['route']}`.",
        f"- All gates passed: `{str(decision['all_applicable_gates_passed']).lower()}`.",
        "- Paper promotion allowed: `false`.",
        "- Network during replay, broker, paper mutation, and live activity: none.",
        "",
    ))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default=str(_ROOT))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    result = run_v564_frozen_forward_confirmation(args.output_root)
    if args.format == "json":
        print(json.dumps(_base._json_safe(result), indent=2, sort_keys=True))
    else:
        decision = result["terminal_decision"]
        print(f"route={decision['route']}")
        print(f"all_applicable_gates_passed={str(decision['all_applicable_gates_passed']).lower()}")
        print(f"artifact_manifest_sha256={result['artifact_manifest_sha256']}")
        print("paper_promotion_allowed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
