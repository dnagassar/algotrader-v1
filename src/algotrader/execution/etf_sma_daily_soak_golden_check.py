"""Deterministic End-to-End Golden Acceptance Loop Orchestrator (V3H).

Coordinates running V3E daily soak, V3F soak brief, artifact validation,
V3G release gate, post-release artifact validation, and final golden check assertions.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from algotrader.errors import ValidationError
from algotrader.core.artifacts import validate_tree, write_validation_report
from algotrader.execution.etf_sma_daily_soak import (
    EtfSmaDailySoakConfig,
    run_etf_sma_daily_soak,
)
from algotrader.execution.etf_sma_daily_soak_brief import (
    EtfSmaDailySoakBriefConfig,
    run_etf_sma_daily_soak_brief,
)
from algotrader.execution.etf_sma_daily_soak_release_gate import (
    EtfSmaDailySoakReleaseGateConfig,
    run_etf_sma_daily_soak_release_gate,
)


@dataclass(frozen=True, slots=True)
class EtfSmaDailySoakGoldenCheckConfig:
    """Configuration for the etf-sma-daily-soak-golden-check command."""

    start_date: str
    end_date: str
    bars_csv: Path | str
    reconciliation_state_path: Path | str
    output_root: Path | str = "runs/daily_soak"
    validation_output: Path | str = "runs/validation/artifact_validation_report.jsonl"
    post_release_validation_output: Path | str = (
        "runs/validation/artifact_validation_after_release_gate_report.jsonl"
    )
    output_jsonl: Path | str = "runs/daily_soak/soak_golden_acceptance.jsonl"
    output_text: Path | str = "runs/daily_soak/soak_golden_acceptance.txt"
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


def _does_path_cross_roots(
    path_str: str, output_root: str, val_out: str, post_val_out: str
) -> bool:
    """Blocks if any path goes outside of the output root or validation outputs."""
    p = _normalize_path(path_str)
    r = _normalize_path(output_root)
    v = _normalize_path(val_out)
    pv = _normalize_path(post_val_out)
    
    if p == v or p == pv:
        return False
    if p == r or p.startswith(r + "/"):
        return False
    return True


def _is_git_tracked_or_staged(path_str: str) -> bool:
    """Checks if a file path is currently tracked or staged in git."""
    try:
        res_tracked = subprocess.run(
            ["git", "ls-files", path_str],
            capture_output=True,
            text=True,
            check=False
        )
        if res_tracked.returncode == 0 and res_tracked.stdout.strip():
            return True
            
        res_staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only", path_str],
            capture_output=True,
            text=True,
            check=False
        )
        if res_staged.returncode == 0 and res_staged.stdout.strip():
            return True
    except Exception:
        pass
    return False


REQUIRED_V3E_FIELDS = [
    "phase",
    "status",
    "start_date",
    "end_date",
    "attempted_dates",
    "accepted_dates",
    "blocked_dates",
    "insufficient_history_dates",
    "finding_count",
    "artifact_paths",
    "live_trading_authorized",
    "paper_submit_authorized",
    "broker_mutation_authorized",
    "paper_broker_reads_authorized",
    "network_access_authorized",
    "credential_loading_authorized",
]

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

REQUIRED_V3G_FIELDS = [
    "phase",
    "status",
    "source_soak_brief_path",
    "source_artifact_validation_path",
    "start_date",
    "end_date",
    "attempted_date_count",
    "accepted_date_count",
    "blocked_date_count",
    "insufficient_history_date_count",
    "finding_count",
    "artifact_validation_finding_count",
    "missing_expected_artifact_count",
    "absolute_path_finding_count",
    "regression_status",
    "release_gate_status",
    "release_gate_blockers",
    "artifact_paths",
    "live_trading_authorized",
    "paper_submit_authorized",
    "broker_mutation_authorized",
    "paper_broker_reads_authorized",
    "network_access_authorized",
    "credential_loading_authorized",
]


def run_etf_sma_daily_soak_golden_check(
    config: EtfSmaDailySoakGoldenCheckConfig
) -> dict[str, Any]:
    """Orchestrate the end-to-end V3 Daily Soak Acceptance Golden check."""
    # Ensure directories exist
    output_root_path = Path(config.output_root)
    output_root_path.mkdir(parents=True, exist_ok=True)
    Path(config.validation_output).parent.mkdir(parents=True, exist_ok=True)
    Path(config.post_release_validation_output).parent.mkdir(parents=True, exist_ok=True)

    blockers: list[str] = []

    # Pin intermediate filenames as POSIX strings to avoid backslash leaks on Windows
    soak_rollup_jsonl = (output_root_path / "soak_rollup.jsonl").as_posix()
    soak_rollup_text = (output_root_path / "soak_rollup.txt").as_posix()
    soak_brief_jsonl = (output_root_path / "soak_operator_brief.jsonl").as_posix()
    soak_brief_text = (output_root_path / "soak_operator_brief.txt").as_posix()
    release_gate_jsonl = (output_root_path / "soak_release_gate.jsonl").as_posix()
    release_gate_text = (output_root_path / "soak_release_gate.txt").as_posix()

    output_root_str = output_root_path.as_posix()
    validation_output_str = Path(config.validation_output).as_posix()
    post_release_validation_output_str = Path(config.post_release_validation_output).as_posix()

    # Step 1: Run V3E daily soak runner
    soak_payload: dict[str, Any] | None = None
    try:
        soak_payload = run_etf_sma_daily_soak(
            EtfSmaDailySoakConfig(
                start_date=config.start_date,
                end_date=config.end_date,
                bars_csv=config.bars_csv,
                reconciliation_state_path=config.reconciliation_state_path,
                output_root=output_root_str,
                soak_rollup_jsonl=soak_rollup_jsonl,
                soak_rollup_text=soak_rollup_text,
            )
        )
    except Exception as exc:
        blockers.append(f"soak_phase_failed: {exc}")

    # Step 2: Run V3F daily soak brief
    brief_payload: dict[str, Any] | None = None
    if soak_payload is not None:
        try:
            brief_payload = run_etf_sma_daily_soak_brief(
                EtfSmaDailySoakBriefConfig(
                    soak_rollup_jsonl=soak_rollup_jsonl,
                    daily_root=output_root_str,
                    output_jsonl=soak_brief_jsonl,
                    output_text=soak_brief_text,
                    baseline_rollup_jsonl=None,
                    output_format=config.output_format,
                )
            )
        except Exception as exc:
            blockers.append(f"soak_brief_phase_failed: {exc}")
    else:
        blockers.append("soak_brief_phase_skipped_due_to_soak_failure")

    # Step 3: Run artifact validation before release gate
    val_report: Any | None = None
    if soak_payload is not None:
        try:
            val_report = validate_tree(
                input_root=output_root_path,
                output_path=Path(validation_output_str),
                required_keys=[],
            )
            write_validation_report(val_report, Path(validation_output_str))
        except Exception as exc:
            blockers.append(f"artifact_validation_failed: {exc}")
    else:
        blockers.append("artifact_validation_skipped_due_to_soak_failure")

    # Step 4: Run V3G daily soak release gate
    release_gate_payload: dict[str, Any] | None = None
    if brief_payload is not None and val_report is not None:
        try:
            release_gate_payload = run_etf_sma_daily_soak_release_gate(
                EtfSmaDailySoakReleaseGateConfig(
                    soak_brief_jsonl=soak_brief_jsonl,
                    artifact_validation_jsonl=validation_output_str,
                    output_jsonl=release_gate_jsonl,
                    output_text=release_gate_text,
                    output_format=config.output_format,
                )
            )
        except Exception as exc:
            blockers.append(f"release_gate_phase_failed: {exc}")
    else:
        blockers.append("release_gate_phase_skipped_due_to_upstream_failure")

    # Step 5: Run artifact validation after release gate
    post_val_report: Any | None = None
    if soak_payload is not None:
        try:
            post_val_report = validate_tree(
                input_root=output_root_path,
                output_path=Path(post_release_validation_output_str),
                required_keys=[],
            )
            write_validation_report(
                post_val_report, Path(post_release_validation_output_str)
            )
        except Exception as exc:
            blockers.append(f"post_release_artifact_validation_failed: {exc}")
    else:
        blockers.append("post_release_artifact_validation_skipped_due_to_soak_failure")

    # Gather data from upstream steps (fail-safe fallback defaults)
    attempted_date_count = 0
    accepted_date_count = 0
    blocked_date_count = 0
    insufficient_history_date_count = 0
    release_gate_status = "blocked"
    artifact_validation_finding_count = 0
    post_release_artifact_validation_finding_count = 0

    auth_flags = {
        "live_trading_authorized": False,
        "paper_submit_authorized": False,
        "broker_mutation_authorized": False,
        "paper_broker_reads_authorized": False,
        "network_access_authorized": False,
        "credential_loading_authorized": False,
    }

    raw_artifact_paths: list[str] = []

    # Assert required fields presence and safety booleans
    # 1. Soak Rollup Checks
    if soak_payload is not None:
        missing_fields = [f for f in REQUIRED_V3E_FIELDS if f not in soak_payload]
        if missing_fields:
            blockers.append(f"missing_required_v3e_fields: {', '.join(sorted(missing_fields))}")
        
        for key in auth_flags:
            if soak_payload.get(key) is True:
                auth_flags[key] = True
                blockers.append("authorization_boolean_true")

    # 2. Soak Brief Checks
    if brief_payload is not None:
        missing_fields = [f for f in REQUIRED_V3F_FIELDS if f not in brief_payload]
        if missing_fields:
            blockers.append(f"missing_required_v3f_fields: {', '.join(sorted(missing_fields))}")

        attempted_date_count = brief_payload.get("attempted_date_count", 0)
        accepted_date_count = brief_payload.get("accepted_date_count", 0)
        blocked_date_count = brief_payload.get("blocked_date_count", 0)
        insufficient_history_date_count = brief_payload.get("insufficient_history_date_count", 0)

        for key in auth_flags:
            if brief_payload.get(key) is True:
                auth_flags[key] = True
                blockers.append("authorization_boolean_true")

    # 3. Artifact Validation checks
    if val_report is not None:
        artifact_validation_finding_count = val_report.finding_count
        if val_report.finding_count > 0 or val_report.status != "passed":
            blockers.append("artifact_validation_findings")
        
        for key, val in val_report.safety_flags.items():
            if val is True:
                blockers.append("authorization_boolean_true")

    # 4. Release Gate Checks
    if release_gate_payload is not None:
        missing_fields = [f for f in REQUIRED_V3G_FIELDS if f not in release_gate_payload]
        if missing_fields:
            blockers.append(f"missing_required_v3g_fields: {', '.join(sorted(missing_fields))}")

        release_gate_status = release_gate_payload.get("release_gate_status", "blocked")
        if release_gate_status == "blocked":
            blockers.append("release_gate_blocked")
            
        for key in auth_flags:
            if release_gate_payload.get(key) is True:
                auth_flags[key] = True
                blockers.append("authorization_boolean_true")

        # Start gathering generated paths from release gate artifact_paths
        raw_artifact_paths.extend(release_gate_payload.get("artifact_paths", []))

    # 5. Post Release Validation Checks
    if post_val_report is not None:
        post_release_artifact_validation_finding_count = post_val_report.finding_count
        if post_val_report.finding_count > 0 or post_val_report.status != "passed":
            blockers.append("post_release_artifact_validation_findings")
        
        for key, val in post_val_report.safety_flags.items():
            if val is True:
                blockers.append("authorization_boolean_true")

    # Include validation reports & golden check artifacts themselves
    raw_artifact_paths.append(validation_output_str)
    raw_artifact_paths.append(post_release_validation_output_str)
    raw_artifact_paths.append(Path(config.output_jsonl).as_posix())
    raw_artifact_paths.append(Path(config.output_text).as_posix())

    # Normalize, deduplicate, and sort all generated paths
    all_artifact_paths = sorted(list({_normalize_path(p) for p in raw_artifact_paths}))

    # Verify path restrictions (POSIX, no drive, backslashes, absolute, or home directories)
    path_violators = []
    cross_root_violators = []
    git_violators = []

    for path in all_artifact_paths:
        if _is_path_violating(path):
            path_violators.append(path)
        if _does_path_cross_roots(
            path, output_root_str, validation_output_str, post_release_validation_output_str
        ):
            cross_root_violators.append(path)
        if _is_git_tracked_or_staged(path):
            git_violators.append(path)

    if path_violators:
        blockers.append("unsafe_artifact_path")
    if cross_root_violators:
        blockers.append("artifacts_crossed_roots")
    if git_violators:
        blockers.append("generated_artifacts_tracked_or_staged")

    # Determine final acceptance status
    golden_acceptance_status = "blocked" if blockers else "accepted"

    # Construct the Golden Check Rollup record
    payload = {
        "phase": "offline_daily_loop_soak_golden_check",
        "status": golden_acceptance_status,
        "start_date": config.start_date,
        "end_date": config.end_date,
        "output_root": output_root_str,
        "soak_rollup_path": soak_rollup_jsonl,
        "soak_brief_path": soak_brief_jsonl,
        "artifact_validation_path": validation_output_str,
        "release_gate_path": release_gate_jsonl,
        "post_release_artifact_validation_path": post_release_validation_output_str,
        "attempted_date_count": attempted_date_count,
        "accepted_date_count": accepted_date_count,
        "blocked_date_count": blocked_date_count,
        "insufficient_history_date_count": insufficient_history_date_count,
        "release_gate_status": release_gate_status,
        "artifact_validation_finding_count": artifact_validation_finding_count,
        "post_release_artifact_validation_finding_count": (
            post_release_artifact_validation_finding_count
        ),
        "golden_acceptance_status": golden_acceptance_status,
        "golden_acceptance_blockers": sorted(list(set(blockers))),
        "artifact_paths": all_artifact_paths,
        "live_trading_authorized": auth_flags["live_trading_authorized"],
        "paper_submit_authorized": auth_flags["paper_submit_authorized"],
        "broker_mutation_authorized": auth_flags["broker_mutation_authorized"],
        "paper_broker_reads_authorized": auth_flags["paper_broker_reads_authorized"],
        "network_access_authorized": auth_flags["network_access_authorized"],
        "credential_loading_authorized": auth_flags["credential_loading_authorized"],
    }

    # Ensure output directories exist before writing
    try:
        Path(config.output_jsonl).parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    try:
        Path(config.output_text).parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    # Write output JSONL (Exactly one line)
    jsonl_str = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    try:
        Path(config.output_jsonl).write_text(jsonl_str, encoding="utf-8", newline="\n")
    except Exception as exc:
        raise ValidationError(f"Failed to write golden check JSONL output: {exc}")

    # Write output Text summary
    blockers_str = "\n".join(f"  - {b}" for b in sorted(list(set(blockers)))) if blockers else "  none"
    violators_str = "\n".join(f"  - {v}" for v in path_violators) if path_violators else "  none"
    crossed_str = "\n".join(f"  - {c}" for c in cross_root_violators) if cross_root_violators else "  none"
    git_str = "\n".join(f"  - {g}" for g in git_violators) if git_violators else "  none"
    artifacts_str = "\n".join(f"  - {path}" for path in all_artifact_paths)

    text_report = (
        f"ETF/SMA Daily Soak Golden Acceptance (V3H) - {golden_acceptance_status.upper()}\n"
        f"==================================================================\n"
        f"Date Range: {config.start_date} to {config.end_date}\n"
        f"Output Root: {output_root_str}\n\n"
        f"Golden Acceptance Status: {golden_acceptance_status.upper()}\n"
        f"Golden Acceptance Blockers:\n"
        f"{blockers_str}\n\n"
        f"Upstream Path Details:\n"
        f"- Soak Rollup Path:                  {soak_rollup_jsonl}\n"
        f"- Soak Brief Path:                   {soak_brief_jsonl}\n"
        f"- Pre-Gate Validation Path:          {validation_output_str}\n"
        f"- Release Gate Path:                 {release_gate_jsonl}\n"
        f"- Post-Gate Validation Path:         {post_release_validation_output_str}\n\n"
        f"Upstream Status & Findings Summary:\n"
        f"- Attempted Date Count:              {attempted_date_count}\n"
        f"- Accepted Date Count:               {accepted_date_count}\n"
        f"- Blocked Date Count:                {blocked_date_count}\n"
        f"- Insufficient History Date Count:   {insufficient_history_date_count}\n"
        f"- Release Gate Status:               {release_gate_status.upper()}\n"
        f"- Pre-Gate Validation Findings:      {artifact_validation_finding_count}\n"
        f"- Post-Gate Validation Findings:     {post_release_artifact_validation_finding_count}\n\n"
        f"Violations Summary:\n"
        f"- Path Violators:\n"
        f"{violators_str}\n"
        f"- Cross Root Violators:\n"
        f"{crossed_str}\n"
        f"- Git Tracked/Staged Violators:\n"
        f"{git_str}\n\n"
        f"Authorization Flags (Must all be False):\n"
        f"- live_trading_authorized:            {payload['live_trading_authorized']}\n"
        f"- paper_submit_authorized:           {payload['paper_submit_authorized']}\n"
        f"- broker_mutation_authorized:         {payload['broker_mutation_authorized']}\n"
        f"- paper_broker_reads_authorized:     {payload['paper_broker_reads_authorized']}\n"
        f"- network_access_authorized:         {payload['network_access_authorized']}\n"
        f"- credential_loading_authorized:     {payload['credential_loading_authorized']}\n\n"
        f"Generated Artifact Paths:\n"
        f"{artifacts_str}\n"
    )

    try:
        Path(config.output_text).write_text(text_report, encoding="utf-8", newline="\n")
    except Exception as exc:
        raise ValidationError(f"Failed to write golden check text summary output: {exc}")

    return payload
