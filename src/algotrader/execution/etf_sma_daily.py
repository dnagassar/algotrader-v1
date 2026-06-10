"""One-command offline daily bundle orchestrator.

This module coordinates running the ETF/SMA daily loop, writing the bundle artifacts,
and updating the daily run index.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any
from datetime import datetime

from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_cycle import (
    EtfSmaCycleConfig,
    build_etf_sma_cycle_from_offline_inputs,
    write_etf_sma_cycle_jsonl,
    load_etf_sma_cycle_bars_csv,
)

_WARNING_TEXT = "WARNING: This brief is preview-only and does not authorize or recommend submitting paper or live orders."


@dataclass(frozen=True, slots=True)
class EtfSmaDailyConfig:
    """Configuration for the etf-sma-daily orchestrator command."""

    as_of_date: str | None = None
    output_root: Path | str = "runs/daily"
    bars_csv: Path | str | None = None
    reconciliation_state_path: Path | str | None = None


def compute_sha256(path: Path) -> str:
    """Compute sha256 hash of a file on disk."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def count_records(path: Path) -> int:
    """Count non-empty lines in a JSONL file."""
    try:
        content = path.read_text(encoding="utf-8")
        return len([line for line in content.splitlines() if line.strip()])
    except Exception:
        return 0


def _normalize_path(path: Path | str) -> str:
    """Computes POSIX path relative to current working directory safely."""
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.relative_to(Path.cwd())
        except ValueError:
            pass
    return str(p.as_posix())


def rebuild_daily_run_index(output_root: Path) -> None:
    """Scan date subdirectories and rebuild the daily run index sorted by date."""
    entries = []
    for path in output_root.iterdir():
        if path.is_dir() and re.match(r"^\d{4}-\d{2}-\d{2}$", path.name):
            manifest_path = path / "bundle_manifest.jsonl"
            if manifest_path.exists() and manifest_path.is_file():
                try:
                    content = manifest_path.read_text(encoding="utf-8").strip()
                    if content:
                        manifest_data = json.loads(content)
                        sha256_val = compute_sha256(manifest_path)
                        byte_size = manifest_path.stat().st_size
                        entries.append({
                            "as_of_date": path.name,
                            "bundle_manifest_path": _normalize_path(manifest_path),
                            "sha256": sha256_val,
                            "byte_size": byte_size,
                            "status": manifest_data.get("bundle_state", "ready")
                        })
                except Exception:
                    pass

    # Sort lexicographically by date ascending
    entries.sort(key=lambda x: x["as_of_date"])

    index_file = output_root / "daily_run_index.jsonl"
    lines = [json.dumps(e, sort_keys=True, separators=(",", ":")) + "\n" for e in entries]
    index_file.write_text("".join(lines), encoding="utf-8", newline="\n")


def run_etf_sma_daily(config: EtfSmaDailyConfig) -> dict[str, Any]:
    """Execute the daily loop orchestration and write the bundle."""
    # Ensure bars_csv is provided
    if not config.bars_csv:
        raise ValidationError("bars_csv is required.")
    bars_path = Path(config.bars_csv)
    if not bars_path.exists():
        raise ValidationError(f"bars_csv path does not exist: {bars_path}")

    # Determine as_of_date
    if config.as_of_date:
        as_of_date = config.as_of_date
        # Validate format
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", as_of_date):
            raise ValidationError(f"as_of_date must be in YYYY-MM-DD format: {as_of_date}")
    else:
        # Load bars and derive latest timestamp
        bars = load_etf_sma_cycle_bars_csv(bars_path, symbol="SPY")
        if not bars:
            raise ValidationError("No usable bars found to derive default as-of date.")
        latest_dt = max(bar.timestamp for bar in bars)
        as_of_date = latest_dt.strftime("%Y-%m-%d")

    output_root_path = Path(config.output_root)
    target_dir = output_root_path / as_of_date
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Run cycle and write cycle.jsonl
    cycle_conf = EtfSmaCycleConfig(
        run_id=f"daily_cycle_{as_of_date}",
        symbol="SPY",
        as_of=as_of_date,
        market_data_csv=bars_path,
        order_reconciliation_log=Path(config.reconciliation_state_path) if config.reconciliation_state_path else None,
    )
    cycle_payload = build_etf_sma_cycle_from_offline_inputs(cycle_conf)
    cycle_file = target_dir / "cycle.jsonl"
    write_etf_sma_cycle_jsonl(cycle_payload, cycle_file)

    # 2. Extract values and run brief
    posture = cycle_payload.get("sma_posture")
    cycle_decision = cycle_payload.get("decision")
    blockers = cycle_payload.get("blockers", [])

    if blockers:
        current_action = "blocked/fail_closed"
        recommended_operator_action = "repair_m450_pipeline_manifest_before_operator_brief_use"
        brief_state = "blocked"
    elif posture == "insufficient_history":
        current_action = "observe_insufficient_history"
        recommended_operator_action = "observe_insufficient_history"
        brief_state = "ready"
    else:
        current_action = "observe_hold_noop" if cycle_decision == "hold/noop" else str(cycle_decision)
        recommended_operator_action = current_action
        brief_state = "ready"

    # Write brief.jsonl
    brief_payload = {
        "milestone": "V3A",
        "phase": "offline_daily_bundle_brief",
        "command": "etf-sma-daily",
        "brief_state": brief_state,
        "as_of_date": as_of_date,
        "posture": posture,
        "cycle_decision": cycle_decision,
        "current_action": current_action,
        "recommended_operator_action": recommended_operator_action,
        "operator_warning": "preview_only_not_order_authorization",
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "paper_submit_allowed": False,
        "live_submit_allowed": False,
        "profit_claim": "none",
        "blockers": list(blockers),
    }
    brief_jsonl_file = target_dir / "brief.jsonl"
    brief_jsonl_file.write_text(
        json.dumps(brief_payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n"
    )

    # Write brief.txt
    blockers_str = ", ".join(blockers) if blockers else "none"
    brief_txt_content = (
        f"ETF/SMA Daily Operator Brief (V3A) - {brief_state.upper()}\n"
        f"==================================\n"
        f"{_WARNING_TEXT}\n\n"
        f"as_of_date: {as_of_date}\n"
        f"posture: {posture}\n"
        f"cycle_decision: {cycle_decision}\n"
        f"current_action: {current_action}\n"
        f"recommended_operator_action: {recommended_operator_action}\n"
        f"blockers: {blockers_str}\n"
        f"submitted=false\n"
        f"mutated=false\n"
        f"paper_submit_allowed=false\n"
        f"live_submit_allowed=false\n"
        f"profit_claim=none\n"
    )
    brief_txt_file = target_dir / "brief.txt"
    brief_txt_file.write_text(brief_txt_content, encoding="utf-8", newline="\n")

    # 3. Write gate.jsonl
    if blockers:
        gate_state = "blocked_or_invalid"
        accepted_obs = False
    else:
        gate_state = "accepted_for_preview_only_observation"
        accepted_obs = True

    gate_payload = {
        "milestone": "V3A",
        "phase": "offline_daily_bundle_gate",
        "command": "etf-sma-daily",
        "acceptance_gate_state": gate_state,
        "accepted_for_operator_observation": accepted_obs,
        "order_authorization": False,
        "paper_submit_allowed": False,
        "live_submit_allowed": False,
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
        "profit_claim": "none",
        "blockers": list(blockers),
    }
    gate_file = target_dir / "gate.jsonl"
    gate_file.write_text(
        json.dumps(gate_payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n"
    )

    # 4. Write dashboard.txt
    dashboard_content = (
        "ETF/SMA Daily Operator Dashboard Export (V3A)\n"
        "==============================================\n"
        f"export_state: {brief_state}\n"
        f"decision_summary: {cycle_decision}\n"
        f"posture_summary: {posture}\n"
        f"blockers: {blockers_str}\n"
        "submitted=false\n"
        "mutated=false\n"
        "paper_submit_allowed=false\n"
        "live_submit_allowed=false\n"
        "scheduler_install_allowed=false\n"
        "order_authorization=false\n"
    )
    dashboard_file = target_dir / "dashboard.txt"
    dashboard_file.write_text(dashboard_content, encoding="utf-8", newline="\n")

    # 5. Write bundle_manifest.jsonl
    bundle_files = ["cycle.jsonl", "brief.jsonl", "brief.txt", "gate.jsonl", "dashboard.txt"]
    file_records = []
    for fname in bundle_files:
        fpath = target_dir / fname
        rel_fpath = _normalize_path(fpath)
        sha256_val = compute_sha256(fpath)
        byte_size = fpath.stat().st_size
        rec_count = count_records(fpath) if fname.endswith(".jsonl") else 0
        file_records.append({
            "path": rel_fpath,
            "sha256": sha256_val,
            "byte_size": byte_size,
            "record_count": rec_count,
            "status": "blocked" if blockers else "ready",
        })

    manifest_payload = {
        "milestone": "V3A",
        "phase": "offline_daily_bundle_manifest",
        "command": "etf-sma-daily",
        "bundle_state": "blocked_or_invalid" if blockers else "ready",
        "as_of_date": as_of_date,
        "labels": [
            "paper_lab_only",
            "signal_evaluation_only",
            "not_live_authorized",
            "profit_claim=none"
        ],
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "broker_mutation_allowed": False,
        "live_authorized": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "blockers": list(blockers),
        "files": file_records,
    }
    manifest_file = target_dir / "bundle_manifest.jsonl"
    manifest_file.write_text(
        json.dumps(manifest_payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n"
    )

    # 6. Rebuild daily run index
    rebuild_daily_run_index(output_root_path)

    return manifest_payload
