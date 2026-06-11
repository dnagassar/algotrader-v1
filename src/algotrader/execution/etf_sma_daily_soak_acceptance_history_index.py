"""Indexer for prior daily soak golden acceptance outputs (V3J).

Scan prior runs, validate schemas, aggregate counts, blocker trends,
and key artifact paths, writing a deterministic JSONL index.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError


@dataclass(frozen=True, slots=True)
class EtfSmaDailySoakAcceptanceHistoryIndexConfig:
    """Configuration for V3J Daily Soak Acceptance History Index."""

    daily_soak_dir: Path | str = "runs/daily_soak"
    out: Path | str = "runs/daily_soak/v3j_daily_soak_acceptance_history_index.jsonl"


def _normalize_path(path: Path | str) -> str:
    """Computes POSIX path relative to current working directory safely."""
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.relative_to(Path.cwd())
        except ValueError:
            pass
    return str(p.as_posix())


def run_etf_sma_daily_soak_acceptance_history_index(
    config: EtfSmaDailySoakAcceptanceHistoryIndexConfig,
) -> list[dict[str, Any]]:
    """Execute historical indexing over daily soak golden checks."""
    daily_soak_path = Path(config.daily_soak_dir)
    out_path = Path(config.out)

    # Scanned and valid records
    scanned_file_count = 0
    indexed_records: list[dict[str, Any]] = []
    validation_finding_count_total = 0

    if daily_soak_path.exists() and daily_soak_path.is_dir():
        # Recursively find all candidate .jsonl files
        # To be fully deterministic, sort file paths alphabetically first
        candidate_paths = sorted(list(daily_soak_path.rglob("*.jsonl")))
        for path in candidate_paths:
            # Skip output index file if it resides in the same directory
            if path.resolve() == out_path.resolve():
                continue

            scanned_file_count += 1
            try:
                content = path.read_text(encoding="utf-8").strip()
                if not content:
                    continue
                # Daily soak golden check outputs are single-line JSON records
                lines = [line.strip() for line in content.splitlines() if line.strip()]
                if not lines:
                    continue
                
                # Check the first line for the golden check signature
                try:
                    data = json.loads(lines[0])
                except json.JSONDecodeError:
                    # Malformed JSON in candidate is a validation finding
                    validation_finding_count_total += 1
                    continue

                if not isinstance(data, dict):
                    continue

                # Safely identify if this is a golden check output.
                is_candidate = (
                    data.get("phase") == "offline_daily_loop_soak_golden_check"
                    or "golden_acceptance_status" in data
                )
                if not is_candidate:
                    continue

                # Verify mandatory schema fields
                mandatory_fields = ["start_date", "end_date", "status"]
                missing = [f for f in mandatory_fields if f not in data]
                if missing:
                    validation_finding_count_total += 1
                    continue

                # Keep a reference to the relative path of the file
                data["_file_path"] = _normalize_path(path)
                indexed_records.append(data)

            except Exception:
                validation_finding_count_total += 1

    # Deterministic sorting independent of filesystem order or modified time.
    # Sort by: start_date (asc), end_date (asc), then relative file path (asc).
    indexed_records.sort(
        key=lambda r: (
            r.get("start_date", ""),
            r.get("end_date", ""),
            r.get("_file_path", ""),
        )
    )

    # Aggregates
    indexed_count = len(indexed_records)
    attempted_count = 0
    accepted_count = 0
    blocked_count = 0
    insufficient_history_count = 0
    blocker_trends: dict[str, int] = {}
    
    for rec in indexed_records:
        attempted_count += rec.get("attempted_date_count", 0)
        accepted_count += rec.get("accepted_date_count", 0)
        blocked_count += rec.get("blocked_date_count", 0)
        insufficient_history_count += rec.get("insufficient_history_date_count", 0)
        
        # Accumulate validation findings
        validation_finding_count_total += rec.get("artifact_validation_finding_count", 0)
        validation_finding_count_total += rec.get("post_release_artifact_validation_finding_count", 0)
        
        # Accumulate blocker trends
        blockers = rec.get("golden_acceptance_blockers", [])
        if isinstance(blockers, list):
            for b in blockers:
                blocker_trends[b] = blocker_trends.get(b, 0) + 1

    # Safety authorizations (strictly false)
    safety_auths = {
        "live_authorized": False,
        "paper_submit_authorized": False,
        "paper_broker_reads_authorized": False,
        "broker_mutation_authorized": False,
        "network_authorized": False,
        "credentials_loaded": False,
    }

    # Latest record metadata
    latest_golden_acceptance_status = None
    latest_release_gate_status = None
    latest_run_id = None
    latest_as_of = None
    key_artifact_paths: list[str] = []
    status = "blocked-no-history"

    if indexed_records:
        latest_rec = indexed_records[-1]
        latest_golden_acceptance_status = latest_rec.get("golden_acceptance_status") or latest_rec.get("status")
        latest_release_gate_status = latest_rec.get("release_gate_status")
        latest_run_id = f"{latest_rec.get('start_date')}_{latest_rec.get('end_date')}"
        latest_as_of = latest_rec.get("end_date")
        
        # Pull key artifact paths from the latest run, converting to relative paths
        raw_paths = latest_rec.get("artifact_paths", [])
        key_artifact_paths = sorted(list({_normalize_path(p) for p in raw_paths}))
        
        status = "accepted" if latest_golden_acceptance_status == "accepted" else "blocked"

    # Build the output JSONL records
    records_to_write: list[dict[str, Any]] = []

    # 1. Summary Record
    summary_rec = {
        "phase": "V3J",
        "record_type": "summary",
        "status": status,
        "input_daily_soak_dir": _normalize_path(config.daily_soak_dir),
        "scanned_file_count": scanned_file_count,
        "indexed_golden_acceptance_count": indexed_count,
        "latest_golden_acceptance_status": latest_golden_acceptance_status,
        "latest_release_gate_status": latest_release_gate_status,
        "latest_run_id": latest_run_id,
        "latest_as_of": latest_as_of,
        "validation_finding_count_total": validation_finding_count_total,
        "attempted_count": attempted_count,
        "accepted_count": accepted_count,
        "blocked_count": blocked_count,
        "insufficient_history_count": insufficient_history_count,
        "blocker_trends": dict(sorted(blocker_trends.items())),
        "key_artifact_paths": key_artifact_paths,
        "safety_authorizations": safety_auths,
    }
    records_to_write.append(summary_rec)

    # 2. Latest Run Record
    latest_run_rec = {
        "phase": "V3J",
        "record_type": "latest_run",
        "latest_as_of": latest_as_of,
        "latest_golden_acceptance_status": latest_golden_acceptance_status,
        "latest_release_gate_status": latest_release_gate_status,
        "key_artifact_paths": key_artifact_paths,
        "safety_authorizations": safety_auths,
    }
    records_to_write.append(latest_run_rec)

    # 3. Blocker Trends Record
    blocker_trends_rec = {
        "phase": "V3J",
        "record_type": "blocker_trends",
        "blocker_trends": dict(sorted(blocker_trends.items())),
        "safety_authorizations": safety_auths,
    }
    records_to_write.append(blocker_trends_rec)

    # 4. Per-Run Records
    for idx, rec in enumerate(indexed_records):
        per_run_status = rec.get("golden_acceptance_status") or rec.get("status")
        per_run_rec = {
            "phase": "V3J",
            "record_type": "per_run",
            "run_index": idx,
            "start_date": rec.get("start_date"),
            "end_date": rec.get("end_date"),
            "golden_acceptance_status": per_run_status,
            "release_gate_status": rec.get("release_gate_status"),
            "validation_finding_count": (
                rec.get("artifact_validation_finding_count", 0)
                + rec.get("post_release_artifact_validation_finding_count", 0)
            ),
            "attempted_date_count": rec.get("attempted_date_count", 0),
            "accepted_date_count": rec.get("accepted_date_count", 0),
            "blocked_date_count": rec.get("blocked_date_count", 0),
            "insufficient_history_date_count": rec.get("insufficient_history_date_count", 0),
            "blockers": rec.get("golden_acceptance_blockers", []),
            "file_path": rec.get("_file_path"),
            "safety_authorizations": safety_auths,
        }
        # If source artifact has safety booleans, preserve in source-derived section
        source_safety = {}
        for k in ["live_trading_authorized", "paper_submit_authorized", "broker_mutation_authorized",
                  "paper_broker_reads_authorized", "network_access_authorized", "credential_loading_authorized"]:
            if k in rec:
                source_safety[k] = rec[k]
        if source_safety:
            per_run_rec["source_derived_safety"] = source_safety

        records_to_write.append(per_run_rec)

    # Ensure target output directory exists
    if out_path.parent != Path(".") and not out_path.parent.exists():
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    # Write output JSONL
    try:
        lines_str = "".join(
            json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n"
            for r in records_to_write
        )
        out_path.write_text(lines_str, encoding="utf-8", newline="\n")
    except Exception as exc:
        raise ValidationError(f"Failed to write history index JSONL output: {exc}")

    return records_to_write
