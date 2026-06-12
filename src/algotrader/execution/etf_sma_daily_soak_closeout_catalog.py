"""Offline closeout bundle catalog generator (V3Q)."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError


@dataclass(frozen=True, slots=True)
class DailyLabCloseoutCatalogConfig:
    """Configuration for V3Q Daily Lab Closeout Bundle Catalog."""

    bundle_roots: list[str]
    output_jsonl: str = "runs/daily_soak/closeout_catalog.jsonl"
    output_text: str = "runs/daily_soak/closeout_catalog.md"


_SAFETY_BOOLEANS = {
    "broker_reads": False,
    "broker_mutations": False,
    "paper_submit": False,
    "credentials_required": False,
    "network_required": False,
    "live_trading": False,
}

_DEFAULT_LABELS = [
    "paper_lab_only",
    "research_only",
    "not_live_authorized",
    "profit_claim=none",
    "offline_only",
]


def run_daily_lab_closeout_catalog(
    config: DailyLabCloseoutCatalogConfig,
) -> list[dict[str, Any]]:
    """Scan the closeout bundle roots and build the catalog."""
    if not config.bundle_roots:
        raise ValidationError("At least one bundle root must be supplied.")

    # 1. Deterministic sorting of bundle roots based on normalized paths
    sorted_roots = sorted(list(set(config.bundle_roots)), key=_normalize_path)
    records: list[dict[str, Any]] = []

    expected_artifacts = [
        ("v3j_history_index", "v3j_daily_soak_acceptance_history_index.jsonl"),
        ("v3k_operator_summary_jsonl", "v3k_daily_soak_operator_summary.jsonl"),
        ("v3k_operator_summary_markdown", "v3k_daily_soak_operator_summary.md"),
        ("v3l_closeout_packet_jsonl", "v3l_daily_soak_closeout_packet.jsonl"),
        ("v3l_closeout_packet_markdown", "v3l_daily_soak_closeout_packet.md"),
        ("v3n_receipt_jsonl", "v3n_daily_lab_closeout_run_receipt.jsonl"),
        ("v3n_receipt_markdown", "v3n_daily_lab_closeout_run_receipt.md"),
        ("v3o_daily_lab_closeout_bundle_validation", "v3o_daily_lab_closeout_bundle_validation.jsonl"),
        ("v3o_daily_lab_closeout_bundle_validation_markdown", "v3o_daily_lab_closeout_bundle_validation.md"),
    ]

    for raw_root in sorted_roots:
        root_path = Path(raw_root)
        exists = root_path.exists() and root_path.is_dir()

        artifact_count = 0
        artifacts_details: dict[str, dict[str, Any]] = {}
        validation_status = "not_available"
        validation_record: dict[str, Any] | None = None

        if exists:
            # Check for validation record first
            val_path = root_path / "v3o_daily_lab_closeout_bundle_validation.jsonl"
            if val_path.exists() and val_path.is_file():
                try:
                    with val_path.open("r", encoding="utf-8-sig") as f:
                        lines = [line.strip() for line in f if line.strip()]
                        if lines:
                            validation_record = json.loads(lines[0])
                            if validation_record and "status" in validation_record:
                                validation_status = validation_record["status"]
                except Exception:
                    validation_status = "corrupt"

            # Check all expected artifacts
            for kind, filename in expected_artifacts:
                art_path = root_path / filename
                art_exists = art_path.exists() and art_path.is_file()
                size_bytes = None
                sha256 = None

                if art_exists:
                    artifact_count += 1
                    try:
                        size_bytes = art_path.stat().st_size
                        sha256 = _sha256(art_path)
                    except Exception:
                        pass

                artifacts_details[kind] = {
                    "path": _normalize_path(art_path),
                    "exists": art_exists,
                    "size_bytes": size_bytes,
                    "sha256": sha256,
                }

        # Resolve status
        if not exists:
            status = "not_available"
        elif validation_status == "passed":
            status = "passed"
        elif validation_status == "failed":
            status = "failed"
        else:
            status = "not_available"

        # Recommended action
        if status == "passed":
            recommended_action = "review_closeout_packet"
        elif status == "failed":
            recommended_action = "inspect_validation_failures"
        else:
            recommended_action = "run_validation"

        # Safety & Labels (extract from validation record if available, else defaults)
        labels = list(_DEFAULT_LABELS)
        safety = dict(_SAFETY_BOOLEANS)

        if validation_record:
            if "labels" in validation_record and isinstance(validation_record["labels"], list):
                labels = list(validation_record["labels"])
            if "safety" in validation_record and isinstance(validation_record["safety"], dict):
                safety = dict(validation_record["safety"])

        records.append({
            "bundle_root": _normalize_path(root_path),
            "status": status,
            "validation_status": validation_status,
            "artifact_count": artifact_count,
            "artifacts": artifacts_details,
            "recommended_next_action": recommended_action,
            "labels": labels,
            "safety": safety,
        })

    # 2. Write JSONL output
    jsonl_path = Path(config.output_jsonl)
    _write_jsonl(jsonl_path, records)

    # 3. Write Markdown summary output
    text_path = Path(config.output_text)
    _write_markdown(text_path, records)

    return records


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_path(path: Path | str) -> str:
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.relative_to(Path.cwd())
        except ValueError:
            pass
    return str(p.as_posix())


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    if path.parent != Path(".") and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = "".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
            for record in records
        )
        path.write_text(payload, encoding="utf-8", newline="\n")
    except Exception as exc:
        raise ValidationError(f"Failed to write catalog JSONL output: {exc}")


def _write_markdown(path: Path, records: list[dict[str, Any]]) -> None:
    if path.parent != Path(".") and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    for r in records:
        summary_rows.append(
            f"| `{r['bundle_root']}` | `{r['status']}` | `{r['validation_status']}` | {r['artifact_count']} | `{r['recommended_next_action']}` |"
        )
    summary_table = "\n".join(summary_rows)

    details_sections = []
    for r in records:
        # Create artifacts sub-table
        art_rows = []
        # Sort artifact details deterministically by kind
        for kind in sorted(r["artifacts"].keys()):
            art = r["artifacts"][kind]
            exists_str = "Yes" if art["exists"] else "No"
            size_str = str(art["size_bytes"]) if art["size_bytes"] is not None else "-"
            sha_str = f"`{art['sha256']}`" if art["sha256"] else "-"
            art_rows.append(
                f"| {kind} | `{art['path']}` | {exists_str} | {size_str} | {sha_str} |"
            )
        art_table = "\n".join(art_rows)

        labels_str = ", ".join(f"`{lbl}`" for lbl in r["labels"])
        safety_list = [f"- **{k}**: `{v}`" for k, v in sorted(r["safety"].items())]
        safety_str = "\n".join(safety_list)

        detail = (
            f"### Bundle: `{r['bundle_root']}`\n\n"
            f"- **Overall Status**: `{r['status']}`\n"
            f"- **Validation Status**: `{r['validation_status']}`\n"
            f"- **Artifact Count**: {r['artifact_count']}\n"
            f"- **Recommended Next Action**: `{r['recommended_next_action']}`\n"
            f"- **Safety Labels**: {labels_str}\n\n"
            f"#### Safety Booleans\n"
            f"{safety_str}\n\n"
            f"#### Discovered Artifacts\n"
            f"| Artifact Kind | Relative Path | Exists | Size (Bytes) | SHA-256 Hash |\n"
            f"| --- | --- | --- | --- | --- |\n"
            f"{art_table}\n"
        )
        details_sections.append(detail)

    details_str = "\n---\n\n".join(details_sections)

    report = (
        f"# Daily Lab Closeout Catalog Index\n\n"
        f"This catalog index provides a deterministic overview of daily lab closeout bundles across scanned roots.\n\n"
        f"## Summary Table\n\n"
        f"| Bundle Root | Status | Validation Status | Artifact Count | Recommended Next Action |\n"
        f"| --- | --- | --- | --- | --- |\n"
        f"{summary_table}\n\n"
        f"## Detailed Bundle Overview\n\n"
        f"{details_str}\n\n"
        f"This catalog index is offline and does not authorize broker reads, paper submit, broker mutation, or live trading.\n"
    )

    try:
        path.write_text(report, encoding="utf-8", newline="\n")
    except Exception as exc:
        raise ValidationError(f"Failed to write catalog text output: {exc}")
