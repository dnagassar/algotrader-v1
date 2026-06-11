"""Offline Soak Operator Brief + Regression Comparison module (V3F).

Consumes V3E daily soak rollups and daily bundle artifacts to produce a
compact JSONL + text summary for operator review.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError


@dataclass(frozen=True, slots=True)
class EtfSmaDailySoakBriefConfig:
    """Configuration for the etf-sma-daily-soak-brief command."""

    soak_rollup_jsonl: Path | str
    daily_root: Path | str
    output_jsonl: Path | str = "runs/daily_soak/soak_operator_brief.jsonl"
    output_text: Path | str = "runs/daily_soak/soak_operator_brief.txt"
    baseline_rollup_jsonl: Path | str | None = None
    output_format: str = "text"


def _normalize_path(path: Path | str) -> str:
    """Computes POSIX path relative to current working directory safely."""
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.relative_to(Path.cwd())
        except ValueError:
            pass
    return str(p.as_posix())


def _is_absolute_path(val: str) -> bool:
    """Determines if a string represents a Windows or POSIX absolute path."""
    if not isinstance(val, str):
        return False
    if re.search(r"^[a-zA-Z]:[/\\]", val) or "C:" in val or "c:" in val:
        return True
    if val.startswith("/") and not val.startswith("//"):
        if "://" not in val:
            return True
    return False


def _scan_val_for_absolute_paths(val: Any) -> int:
    """Recursively counts absolute or backslash paths in JSON-like structure."""
    count = 0
    if isinstance(val, dict):
        for k, v in val.items():
            count += _scan_val_for_absolute_paths(v)
    elif isinstance(val, (list, tuple)):
        for item in val:
            count += _scan_val_for_absolute_paths(item)
    elif isinstance(val, str):
        if _is_absolute_path(val):
            count += 1
    return count


def _scan_text_file_for_absolute_paths(path: Path) -> int:
    """Counts absolute path occurrences in text file lines by splitting into words."""
    count = 0
    if not path.exists():
        return 0
    try:
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            for word in line.split():
                clean = word.strip("()'\",;[]{}")
                if _is_absolute_path(clean):
                    count += 1
    except Exception:
        pass
    return count


def _scan_jsonl_file_for_absolute_paths(path: Path) -> int:
    """Counts absolute path occurrences in a JSONL file."""
    count = 0
    if not path.exists():
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    count += _scan_val_for_absolute_paths(obj)
                except Exception:
                    for word in line.split():
                        clean = word.strip("()'\",;[]{}")
                        if _is_absolute_path(clean):
                            count += 1
    except Exception:
        pass
    return count


def _resolve_artifact_path(path_str: str, daily_root_path: Path) -> Path | None:
    """Resolves an artifact path either directly or relative to daily_root."""
    p = Path(path_str)
    if p.exists():
        return p
    # Try direct child of daily_root
    p_sub = daily_root_path / path_str
    if p_sub.exists():
        return p_sub
    # Match part names to daily_root structure
    p_parts = p.parts
    if daily_root_path.name in p_parts:
        idx = p_parts.index(daily_root_path.name)
        sub_path = Path(*p_parts[idx:])
        p_parent = daily_root_path.parent / sub_path
        if p_parent.exists():
            return p_parent
    return None


def run_etf_sma_daily_soak_brief(config: EtfSmaDailySoakBriefConfig) -> dict[str, Any]:
    """Execute the offline soak rollup brief compiler and regression check."""
    soak_rollup_path = Path(config.soak_rollup_jsonl)
    if not soak_rollup_path.exists():
        raise ValidationError(f"Soak rollup file does not exist: {soak_rollup_path}")

    daily_root_path = Path(config.daily_root)
    if not daily_root_path.exists() or not daily_root_path.is_dir():
        raise ValidationError(f"Daily root directory does not exist or is not a directory: {daily_root_path}")

    # 1. Read the soak rollup
    try:
        # soak_rollup.jsonl has exactly one aggregate line
        lines = soak_rollup_path.read_text(encoding="utf-8").splitlines()
        if not lines:
            raise ValidationError("Soak rollup file is empty.")
        rollup_data = json.loads(lines[0].strip())
    except Exception as exc:
        raise ValidationError(f"Failed to read/parse soak rollup file: {exc}")

    # 2. Extract key fields
    start_date = rollup_data.get("start_date", "")
    end_date = rollup_data.get("end_date", "")
    attempted_dates = rollup_data.get("attempted_dates", [])
    accepted_dates = rollup_data.get("accepted_dates", [])
    blocked_dates = rollup_data.get("blocked_dates", [])
    insufficient_history_dates = rollup_data.get("insufficient_history_dates", [])
    soak_finding_count = rollup_data.get("finding_count", 0)
    soak_status = rollup_data.get("status", "")
    soak_artifact_paths = rollup_data.get("artifact_paths", [])

    attempted_date_count = len(attempted_dates)
    accepted_date_count = len(accepted_dates)
    blocked_date_count = len(blocked_dates)
    insufficient_history_date_count = len(insufficient_history_dates)

    # 3. Check for missing expected daily artifacts
    missing_expected_artifacts: list[str] = []
    expected_filenames = [
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

    for date_str in attempted_dates:
        day_dir = daily_root_path / date_str
        for fname in expected_filenames:
            fpath = day_dir / fname
            if not fpath.exists():
                missing_expected_artifacts.append(_normalize_path(fpath))

    missing_expected_artifact_count = len(missing_expected_artifacts)

    # 4. Gather posture, decision, and blocker counts
    posture_counts: dict[str, int] = {}
    cycle_decision_counts: dict[str, int] = {}
    blocker_counts: dict[str, int] = {}

    for date_str in attempted_dates:
        day_dir = daily_root_path / date_str
        cycle_path = day_dir / "cycle.jsonl"
        posture = "insufficient_history"
        decision = "hold/noop"
        blockers = []

        if cycle_path.exists():
            try:
                cycle_data = json.loads(cycle_path.read_text(encoding="utf-8").strip())
                posture = cycle_data.get("sma_posture", "insufficient_history")
                decision = cycle_data.get("decision", "hold/noop")
                blockers = cycle_data.get("blockers", [])
            except Exception:
                pass

        posture_counts[posture] = posture_counts.get(posture, 0) + 1
        cycle_decision_counts[decision] = cycle_decision_counts.get(decision, 0) + 1
        for blocker in blockers:
            blocker_counts[blocker] = blocker_counts.get(blocker, 0) + 1

    # 5. Scan files for absolute paths or backslashes
    absolute_path_finding_count = 0
    # Collect all existing paths we want to scan (including rollup file)
    files_to_scan = [soak_rollup_path]
    for path_str in soak_artifact_paths:
        resolved_fpath = _resolve_artifact_path(path_str, daily_root_path)
        if resolved_fpath:
            files_to_scan.append(resolved_fpath)

    for fpath in files_to_scan:
        if fpath.suffix == ".jsonl":
            absolute_path_finding_count += _scan_jsonl_file_for_absolute_paths(fpath)
        else:
            absolute_path_finding_count += _scan_text_file_for_absolute_paths(fpath)

    # 6. Baseline regression comparison
    regression_status = "not_requested"
    regression_findings: list[str] = []

    if config.baseline_rollup_jsonl:
        baseline_path = Path(config.baseline_rollup_jsonl)
        if not baseline_path.exists():
            regression_status = "mismatch"
            regression_findings.append(f"Baseline rollup file does not exist: {config.baseline_rollup_jsonl}")
        else:
            try:
                baseline_lines = baseline_path.read_text(encoding="utf-8").splitlines()
                if not baseline_lines:
                    regression_status = "mismatch"
                    regression_findings.append("Baseline rollup file is empty.")
                else:
                    baseline_data = json.loads(baseline_lines[0].strip())
                    mismatches = []
                    fields_to_compare = [
                        "start_date",
                        "end_date",
                        "attempted_dates",
                        "accepted_dates",
                        "blocked_dates",
                        "insufficient_history_dates",
                        "finding_count",
                        "status",
                    ]
                    for field in fields_to_compare:
                        curr_val = rollup_data.get(field)
                        base_val = baseline_data.get(field)
                        if curr_val != base_val:
                            mismatches.append(f"{field} mismatch: current={curr_val}, baseline={base_val}")

                    if mismatches:
                        regression_status = "mismatch"
                        regression_findings.extend(mismatches)
                    else:
                        regression_status = "matched"
            except Exception as exc:
                regression_status = "mismatch"
                regression_findings.append(f"Failed to parse baseline rollup file: {exc}")

    # 7. Resolve final brief status
    # status can be: blocked, completed_with_findings, accepted
    if blocked_date_count > 0 or any(blocker_counts.values()):
        brief_status = "blocked"
    elif (
        soak_status != "accepted"
        or missing_expected_artifact_count > 0
        or absolute_path_finding_count > 0
        or regression_status == "mismatch"
    ):
        brief_status = "completed_with_findings"
    else:
        brief_status = "accepted"

    # Construct the list of output brief artifact paths relative to CWD
    output_jsonl_posix = _normalize_path(config.output_jsonl)
    output_text_posix = _normalize_path(config.output_text)
    
    # Merge existing artifact paths with output brief paths
    brief_artifact_paths = set()
    for path_str in soak_artifact_paths:
        brief_artifact_paths.add(_normalize_path(path_str))
    brief_artifact_paths.add(output_jsonl_posix)
    brief_artifact_paths.add(output_text_posix)

    # 8. Construct payload
    brief_payload = {
        "phase": "offline_daily_loop_soak_brief",
        "status": brief_status,
        "source_soak_rollup_path": _normalize_path(config.soak_rollup_jsonl),
        "daily_root": _normalize_path(config.daily_root),
        "start_date": start_date,
        "end_date": end_date,
        "attempted_date_count": attempted_date_count,
        "accepted_date_count": accepted_date_count,
        "blocked_date_count": blocked_date_count,
        "insufficient_history_date_count": insufficient_history_date_count,
        "finding_count": soak_finding_count + missing_expected_artifact_count + absolute_path_finding_count,
        "attempted_dates": attempted_dates,
        "accepted_dates": accepted_dates,
        "blocked_dates": blocked_dates,
        "insufficient_history_dates": insufficient_history_dates,
        "posture_counts": posture_counts,
        "cycle_decision_counts": cycle_decision_counts,
        "blocker_counts": blocker_counts,
        "missing_expected_artifact_count": missing_expected_artifact_count,
        "missing_expected_artifacts": sorted(missing_expected_artifacts),
        "absolute_path_finding_count": absolute_path_finding_count,
        "regression_status": regression_status,
        "regression_findings": regression_findings,
        "artifact_paths": sorted(list(brief_artifact_paths)),
        "live_trading_authorized": False,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "paper_broker_reads_authorized": False,
        "network_access_authorized": False,
        "credential_loading_authorized": False,
    }

    # Ensure output directories exist
    Path(config.output_jsonl).parent.mkdir(parents=True, exist_ok=True)
    Path(config.output_text).parent.mkdir(parents=True, exist_ok=True)

    # Write JSONL output (exactly one line)
    jsonl_str = json.dumps(brief_payload, sort_keys=True, separators=(",", ":")) + "\n"
    Path(config.output_jsonl).write_text(jsonl_str, encoding="utf-8", newline="\n")

    # Write Text output
    # Format counts and distribution beautifully
    posture_dist_str = ", ".join(f"{k}: {v}" for k, v in sorted(posture_counts.items())) if posture_counts else "none"
    decision_dist_str = ", ".join(f"{k}: {v}" for k, v in sorted(cycle_decision_counts.items())) if cycle_decision_counts else "none"
    blockers_list_str = "\n".join(f"  - {k}: {v}" for k, v in sorted(blocker_counts.items())) if blocker_counts else "  none"
    missing_artifacts_str = "\n".join(f"  - {path}" for path in missing_expected_artifacts) if missing_expected_artifacts else "  none"
    regression_findings_str = "\n".join(f"  - {f}" for f in regression_findings) if regression_findings else "  none"
    artifacts_str = "\n".join(f"  - {path}" for path in sorted(list(brief_artifact_paths)))

    text_report = (
        f"ETF/SMA Daily Soak Operator Brief (V3F) - {brief_status.upper()}\n"
        f"==========================================================\n"
        f"Date Range: {start_date} to {end_date}\n"
        f"Daily Root: {_normalize_path(config.daily_root)}\n"
        f"Source Rollup: {_normalize_path(config.soak_rollup_jsonl)}\n\n"
        f"Counts Summary:\n"
        f"- Total Attempted:       {attempted_date_count}\n"
        f"- Accepted:              {accepted_date_count}\n"
        f"- Blocked:               {blocked_date_count}\n"
        f"- Insufficient History:  {insufficient_history_date_count}\n"
        f"- Total Findings:        {brief_payload['finding_count']} (Soak findings: {soak_finding_count}, Missing artifacts: {missing_expected_artifact_count}, Absolute path leaks: {absolute_path_finding_count})\n\n"
        f"Distributions:\n"
        f"- Postures:  {posture_dist_str}\n"
        f"- Decisions: {decision_dist_str}\n\n"
        f"Active Blockers:\n"
        f"{blockers_list_str}\n\n"
        f"Missing Expected Daily Artifacts ({missing_expected_artifact_count}):\n"
        f"{missing_artifacts_str}\n\n"
        f"Absolute Path Leaks Detected: {absolute_path_finding_count}\n\n"
        f"Regression Comparison Status: {regression_status}\n"
        f"Regression Findings:\n"
        f"{regression_findings_str}\n\n"
        f"Output Artifact Paths:\n"
        f"{artifacts_str}\n"
    )
    Path(config.output_text).write_text(text_report, encoding="utf-8", newline="\n")

    return brief_payload
