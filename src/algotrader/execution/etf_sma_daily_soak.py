"""Offline Multi-Day Soak Runner for V3 ETF/SMA Daily Loop.

This module coordinates running the canonical V3 daily check path sequentially
across a date range, writing per-day bundles and compiling a compact soak rollup.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.execution.etf_sma_daily import load_etf_sma_cycle_bars_csv
from algotrader.execution.etf_sma_daily_offline_check import (
    EtfSmaDailyOfflineCheckConfig,
    run_etf_sma_daily_offline_check,
)


@dataclass(frozen=True, slots=True)
class EtfSmaDailySoakConfig:
    """Configuration for the etf-sma-daily-soak command."""

    start_date: str
    end_date: str
    bars_csv: Path | str
    reconciliation_state_path: Path | str
    output_root: Path | str = "runs/daily"
    soak_rollup_jsonl: Path | str | None = None
    soak_rollup_text: Path | str | None = None


def _normalize_path(path: Path | str) -> str:
    """Computes POSIX path relative to current working directory safely."""
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.relative_to(Path.cwd())
        except ValueError:
            pass
    return str(p.as_posix())


def run_etf_sma_daily_soak(config: EtfSmaDailySoakConfig) -> dict[str, Any]:
    """Execute the multi-day daily loop soak run and write the aggregate rollup."""
    # 1. Validate date range format
    date_regex = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    if not date_regex.match(config.start_date):
        raise ValidationError(f"start_date must be YYYY-MM-DD: {config.start_date}")
    if not date_regex.match(config.end_date):
        raise ValidationError(f"end_date must be YYYY-MM-DD: {config.end_date}")
    if config.start_date > config.end_date:
        raise ValidationError(f"start_date {config.start_date} is after end_date {config.end_date}")

    # 2. Check bars_csv presence
    bars_path = Path(config.bars_csv)
    if not bars_path.exists():
        raise ValidationError(f"bars_csv path does not exist: {bars_path}")

    # Load bars to extract available dates
    bars = load_etf_sma_cycle_bars_csv(bars_path, symbol="SPY")
    if not bars:
        raise ValidationError("No usable bars found in CSV.")

    # Get unique dates sorting ascending
    bar_dates = sorted(list({bar.timestamp.strftime("%Y-%m-%d") for bar in bars}))

    # Select target dates within the range
    selected_dates = [d for d in bar_dates if config.start_date <= d <= config.end_date]
    if not selected_dates:
        raise ValidationError(f"No dates found in bars CSV between {config.start_date} and {config.end_date}")

    output_root_path = Path(config.output_root)
    output_root_path.mkdir(parents=True, exist_ok=True)

    attempted_dates: list[str] = []
    accepted_dates: list[str] = []
    blocked_dates: list[str] = []
    insufficient_history_dates: list[str] = []
    all_artifact_paths: list[str] = []
    daily_details: list[dict[str, Any]] = []
    total_findings = 0

    # 3. Sequentially execute the daily check loop
    for date_str in selected_dates:
        attempted_dates.append(date_str)
        day_dir = output_root_path / date_str

        check_conf = EtfSmaDailyOfflineCheckConfig(
            as_of_date=date_str,
            output_root=output_root_path,
            bars_csv=bars_path,
            reconciliation_state_path=config.reconciliation_state_path,
        )

        payload = run_etf_sma_daily_offline_check(check_conf)

        status = payload.get("status", "blocked")
        findings_count = payload.get("finding_count", 0)
        total_findings += findings_count

        # Load posture & blockers from local cycle.jsonl to verify
        cycle_json_path = day_dir / "cycle.jsonl"
        posture = "insufficient_history"
        cycle_decision = "hold/noop"
        blockers = []
        if cycle_json_path.exists():
            try:
                cycle_data = json.loads(cycle_json_path.read_text(encoding="utf-8").strip())
                posture = cycle_data.get("sma_posture", "insufficient_history")
                cycle_decision = cycle_data.get("decision", "hold/noop")
                blockers = cycle_data.get("blockers", [])
            except Exception:
                pass

        if status == "accepted":
            if posture == "insufficient_history":
                insufficient_history_dates.append(date_str)
            else:
                accepted_dates.append(date_str)
        else:
            blocked_dates.append(date_str)

        # Append normalized daily bundle paths
        bundle_files = [
            "cycle.jsonl",
            "brief.jsonl",
            "brief.txt",
            "gate.jsonl",
            "dashboard.txt",
            "bundle_manifest.jsonl",
            "bundle_status.jsonl",
            "bundle_status.txt",
            "offline_check.jsonl",
            "offline_check.txt",
        ]
        for fname in bundle_files:
            fpath = day_dir / fname
            if fpath.exists():
                all_artifact_paths.append(_normalize_path(fpath))

        daily_details.append({
            "as_of_date": date_str,
            "status": status,
            "posture": posture,
            "decision": cycle_decision,
            "blockers": list(blockers),
            "findings_count": findings_count,
        })

    # Add optional daily run index if generated
    index_file = output_root_path / "daily_run_index.jsonl"
    if index_file.exists():
        all_artifact_paths.append(_normalize_path(index_file))

    # 4. Evaluate Rollup Status
    if total_findings == 0 and len(accepted_dates) == len(attempted_dates):
        rollup_status = "accepted"
    else:
        rollup_status = "completed_with_findings"

    # 5. Build rollup payload
    rollup_payload = {
        "phase": "offline_daily_loop_soak",
        "status": rollup_status,
        "start_date": config.start_date,
        "end_date": config.end_date,
        "attempted_dates": attempted_dates,
        "accepted_dates": accepted_dates,
        "blocked_dates": blocked_dates,
        "insufficient_history_dates": insufficient_history_dates,
        "finding_count": total_findings,
        "artifact_paths": sorted(all_artifact_paths),
        "live_trading_authorized": False,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "paper_broker_reads_authorized": False,
        "network_access_authorized": False,
        "credential_loading_authorized": False,
    }

    # Write soak_rollup.jsonl (Exactly one aggregate line)
    soak_jsonl_path = Path(config.soak_rollup_jsonl) if config.soak_rollup_jsonl else output_root_path / "soak_rollup.jsonl"
    soak_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    jsonl_line = json.dumps(rollup_payload, sort_keys=True, separators=(",", ":")) + "\n"
    soak_jsonl_path.write_text(jsonl_line, encoding="utf-8", newline="\n")

    # Write optional soak_rollup.txt (ASCII Table formatting)
    soak_text_path = Path(config.soak_rollup_text) if config.soak_rollup_text else output_root_path / "soak_rollup.txt"
    soak_text_path.parent.mkdir(parents=True, exist_ok=True)

    rows_str = []
    for d in daily_details:
        blockers_str = ",".join(d["blockers"]) if d["blockers"] else "none"
        rows_str.append(f"{d['as_of_date']:10} | {d['status']:8} | {d['posture']:20} | {d['decision']:15} | {blockers_str}")

    table_content = "\n".join(rows_str)

    summary_text = (
        f"ETF/SMA Daily Soak Rollup (V3E) - {rollup_status.upper()}\n"
        f"========================================================\n"
        f"Date Range: {config.start_date} to {config.end_date}\n"
        f"Total Attempted: {len(attempted_dates)}\n"
        f"Accepted:        {len(accepted_dates)}\n"
        f"Blocked:         {len(blocked_dates)}\n"
        f"Insufficient H.: {len(insufficient_history_dates)}\n"
        f"Total Findings:  {total_findings}\n\n"
        f"Date Details:\n"
        f"date       | status   | posture              | decision        | blockers\n"
        f"-----------+----------+----------------------+-----------------+---------\n"
        f"{table_content}\n"
    )
    soak_text_path.write_text(summary_text, encoding="utf-8", newline="\n")

    return rollup_payload
