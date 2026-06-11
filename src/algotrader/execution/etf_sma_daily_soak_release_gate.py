"""Offline Soak Acceptance Gate / Release Packet compiler (V3G).

Consumes the accepted V3F daily soak operator brief and the V3D artifact
validation report, then produces a compact JSONL release packet and text
summary for operator review.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError


@dataclass(frozen=True, slots=True)
class EtfSmaDailySoakReleaseGateConfig:
    """Configuration for the etf-sma-daily-soak-release-gate command."""

    soak_brief_jsonl: Path | str
    artifact_validation_jsonl: Path | str
    output_jsonl: Path | str = "runs/daily_soak/soak_release_gate.jsonl"
    output_text: Path | str = "runs/daily_soak/soak_release_gate.txt"
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


def _is_path_violating(path_str: str) -> bool:
    """Detects if a path is absolute, contains a drive letter, backslashes, or tilde/home folder."""
    if not path_str:
        return False
    # Check backslashes
    if "\\" in path_str:
        return True
    # Check drive letter
    if re.search(r"[a-zA-Z]:", path_str):
        return True
    # Check absolute
    if Path(path_str).is_absolute() or path_str.startswith("/"):
        return True
    # Check tilde
    if path_str.startswith("~"):
        return True
    # Check common user home indicators in path segments
    p_lower = path_str.lower()
    if "/home/" in p_lower or "/users/" in p_lower:
        return True
    
    # Check active home folder substring
    try:
        home_path = Path.home()
        home_posix = home_path.as_posix().lower()
        home_str = str(home_path).lower()
        if home_posix in p_lower or home_str in p_lower:
            return True
    except Exception:
        pass
        
    return False


REQUIRED_V3F_FIELDS = [
    "phase",
    "status",
    "start_date",
    "end_date",
    "attempted_date_count",
    "accepted_date_count",
    "blocked_date_count",
    "insufficient_history_date_count",
    "finding_count",
    "missing_expected_artifact_count",
    "absolute_path_finding_count",
    "regression_status",
    "artifact_paths",
    "live_trading_authorized",
    "paper_submit_authorized",
    "broker_mutation_authorized",
    "paper_broker_reads_authorized",
    "network_access_authorized",
    "credential_loading_authorized",
]


def run_etf_sma_daily_soak_release_gate(config: EtfSmaDailySoakReleaseGateConfig) -> dict[str, Any]:
    """Execute the release-gate packet compilation and verification."""
    soak_brief_path = Path(config.soak_brief_jsonl)
    if not soak_brief_path.exists():
        raise ValidationError(f"Soak brief file does not exist: {soak_brief_path}")

    validation_path = Path(config.artifact_validation_jsonl)
    if not validation_path.exists():
        raise ValidationError(f"Artifact validation report does not exist: {validation_path}")

    # 1. Read input files
    try:
        brief_lines = soak_brief_path.read_text(encoding="utf-8").splitlines()
        if not brief_lines:
            raise ValidationError("Soak brief file is empty.")
        brief_data = json.loads(brief_lines[0].strip())
    except Exception as exc:
        if isinstance(exc, ValidationError):
            raise
        raise ValidationError(f"Failed to read/parse soak brief file: {exc}")

    try:
        validation_lines = validation_path.read_text(encoding="utf-8").splitlines()
        if not validation_lines:
            raise ValidationError("Artifact validation report file is empty.")
        validation_data = json.loads(validation_lines[0].strip())
    except Exception as exc:
        if isinstance(exc, ValidationError):
            raise
        raise ValidationError(f"Failed to read/parse artifact validation report file: {exc}")

    blockers: list[str] = []

    # 2. Block if required V3F fields are missing
    missing_fields = [field for field in REQUIRED_V3F_FIELDS if field not in brief_data]
    if missing_fields:
        blockers.append(f"missing_required_v3f_fields: {', '.join(sorted(missing_fields))}")

    # 3. Block if artifact validation has any findings
    validation_finding_count = validation_data.get("finding_count", 0)
    validation_status = validation_data.get("status", "")
    if validation_finding_count > 0 or validation_status != "passed":
        blockers.append("artifact_validation_findings")

    # 4. Block if the V3F brief has any absolute_path_finding_count > 0
    brief_absolute_path_finding_count = brief_data.get("absolute_path_finding_count", 0) if not missing_fields else 0
    if brief_absolute_path_finding_count > 0:
        blockers.append("absolute_path_findings")

    # 5. Block if missing_expected_artifact_count > 0
    brief_missing_expected_artifact_count = brief_data.get("missing_expected_artifact_count", 0) if not missing_fields else 0
    if brief_missing_expected_artifact_count > 0:
        blockers.append("missing_expected_artifacts")

    # 6. Block if regression_status is mismatch
    brief_regression_status = brief_data.get("regression_status", "") if not missing_fields else ""
    if brief_regression_status == "mismatch":
        blockers.append("regression_mismatch")

    # 7. Block if any authorization boolean is true
    auth_booleans = {
        "live_trading_authorized": False,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "paper_broker_reads_authorized": False,
        "network_access_authorized": False,
        "credential_loading_authorized": False,
    }
    
    # Check brief's authorization fields
    brief_auth_true = False
    for field in auth_booleans:
        if brief_data.get(field) is True:
            brief_auth_true = True

    # Check validation safety flags
    validation_auth_true = False
    safety_flags = validation_data.get("safety_flags", {})
    for key, val in safety_flags.items():
        if val is True:
            validation_auth_true = True

    if brief_auth_true or validation_auth_true:
        blockers.append("authorization_boolean_true")

    # 8. Block if any output path is absolute, contains drive letter, backslashes, or user-home path
    output_jsonl_str = str(config.output_jsonl)
    output_text_str = str(config.output_text)
    if _is_path_violating(output_jsonl_str) or _is_path_violating(output_text_str):
        blockers.append("unsafe_output_path")

    # 9. Compile fields
    start_date = brief_data.get("start_date", "")
    end_date = brief_data.get("end_date", "")
    attempted_date_count = brief_data.get("attempted_date_count", 0)
    accepted_date_count = brief_data.get("accepted_date_count", 0)
    blocked_date_count = brief_data.get("blocked_date_count", 0)
    insufficient_history_date_count = brief_data.get("insufficient_history_date_count", 0)

    # Accumulate finding count
    total_finding_count = (
        brief_data.get("finding_count", 0) if not missing_fields else 0
    ) + validation_finding_count

    # Determine gate status
    release_gate_status = "blocked" if blockers else "accepted"

    # Combine artifact paths (normalize and sort)
    artifact_paths_raw = list(brief_data.get("artifact_paths", [])) if not missing_fields else []
    artifact_paths_raw.append(str(config.soak_brief_jsonl))
    artifact_paths_raw.append(str(config.artifact_validation_jsonl))
    artifact_paths_raw.append(output_jsonl_str)
    artifact_paths_raw.append(output_text_str)

    normalized_artifact_paths = sorted(list({_normalize_path(p) for p in artifact_paths_raw}))

    # 10. Construct the payload
    payload = {
        "phase": "offline_daily_loop_soak_release_gate",
        "status": release_gate_status,
        "source_soak_brief_path": _normalize_path(config.soak_brief_jsonl),
        "source_artifact_validation_path": _normalize_path(config.artifact_validation_jsonl),
        "start_date": start_date,
        "end_date": end_date,
        "attempted_date_count": attempted_date_count,
        "accepted_date_count": accepted_date_count,
        "blocked_date_count": blocked_date_count,
        "insufficient_history_date_count": insufficient_history_date_count,
        "finding_count": total_finding_count,
        "artifact_validation_finding_count": validation_finding_count,
        "missing_expected_artifact_count": brief_missing_expected_artifact_count,
        "absolute_path_finding_count": brief_absolute_path_finding_count,
        "regression_status": brief_regression_status if brief_regression_status else "not_requested",
        "release_gate_status": release_gate_status,
        "release_gate_blockers": sorted(blockers),
        "artifact_paths": normalized_artifact_paths,
        "live_trading_authorized": False,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "paper_broker_reads_authorized": False,
        "network_access_authorized": False,
        "credential_loading_authorized": False,
    }

    # Ensure output directory exists before writing (unless path validation says it's unsafe, but we still try to write if we can)
    try:
        Path(config.output_jsonl).parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    try:
        Path(config.output_text).parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    # Write output JSONL (exactly one line)
    jsonl_str = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    try:
        Path(config.output_jsonl).write_text(jsonl_str, encoding="utf-8", newline="\n")
    except Exception as exc:
        # If output path was unsafe or unwritable, we don't crash the program here, but we raise ValidationError
        # or handle it. Actually, if it fails to write, we should raise a ValidationError.
        raise ValidationError(f"Failed to write release gate JSONL file: {exc}")

    # Write output Text summary
    blockers_str = "\n".join(f"  - {b}" for b in sorted(blockers)) if blockers else "  none"
    artifacts_str = "\n".join(f"  - {path}" for path in normalized_artifact_paths)
    
    text_report = (
        f"ETF/SMA Daily Soak Release Gate (V3G) - {release_gate_status.upper()}\n"
        f"==============================================================\n"
        f"Date Range: {start_date} to {end_date}\n"
        f"Source Brief: {_normalize_path(config.soak_brief_jsonl)}\n"
        f"Source Validation Report: {_normalize_path(config.artifact_validation_jsonl)}\n\n"
        f"Acceptance Status:\n"
        f"- Release Gate Status: {release_gate_status.upper()}\n"
        f"- Total Findings:     {total_finding_count}\n"
        f"  * Artifact Validation Findings:  {validation_finding_count}\n"
        f"  * Soak Brief Path Findings:      {brief_absolute_path_finding_count}\n"
        f"  * Missing Expected Artifacts:    {brief_missing_expected_artifact_count}\n"
        f"  * Regression Comparison Status:  {brief_regression_status if brief_regression_status else 'not_requested'}\n\n"
        f"Active Release Gate Blockers:\n"
        f"{blockers_str}\n\n"
        f"Counts Summary:\n"
        f"- Total Attempted:       {attempted_date_count}\n"
        f"- Accepted:              {accepted_date_count}\n"
        f"- Blocked:               {blocked_date_count}\n"
        f"- Insufficient History:  {insufficient_history_date_count}\n\n"
        f"Output Release Gate Artifact Paths:\n"
        f"{artifacts_str}\n"
    )
    
    try:
        Path(config.output_text).write_text(text_report, encoding="utf-8", newline="\n")
    except Exception as exc:
        raise ValidationError(f"Failed to write release gate text report: {exc}")

    return payload
