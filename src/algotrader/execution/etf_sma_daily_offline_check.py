"""Offline daily loop smoke check runner and validator (V3C).

This module coordinates running V3A bundle generation, V3B status validation,
and verifying core artifact validator agreement. It produces one unified JSONL
and TXT check report.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from algotrader.errors import ValidationError
from algotrader.core.artifacts import validate_artifact
from algotrader.core.daily_bundle_schema import DAILY_BUNDLE_REQUIRED_FILES
from algotrader.execution.etf_sma_daily import (
    EtfSmaDailyConfig,
    run_etf_sma_daily,
    load_etf_sma_cycle_bars_csv,
)
from algotrader.execution.etf_sma_daily_status import (
    EtfSmaDailyStatusConfig,
    run_etf_sma_daily_status,
)


@dataclass(frozen=True, slots=True)
class EtfSmaDailyOfflineCheckConfig:
    """Configuration for the etf-sma-daily-offline-check command."""

    as_of_date: str | None = None
    output_root: Path | str = "runs/daily"
    bars_csv: Path | str | None = None
    reconciliation_state_path: Path | str | None = None
    output_check_jsonl: Path | str | None = None
    output_check_text: Path | str | None = None


def _normalize_path(path: Path | str) -> str:
    """Computes POSIX path relative to current working directory safely."""
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.relative_to(Path.cwd())
        except ValueError:
            pass
    return str(p.as_posix())


def _check_txt_file_for_leaks(path: Path) -> list[dict[str, Any]]:
    """Scan plain text file for credentials using patterns from artifacts.py."""
    from algotrader.core.artifacts import (
        PRIVATE_KEY_RE,
        ASSIGN_RE,
        BEARER_RE,
        SAFE_VALUES,
        SAFE_PLACEHOLDERS,
    )
    findings = []
    rel_path = _normalize_path(path)
    if not path.exists():
        return findings
    try:
        content = path.read_text(encoding="utf-8")
        for idx, line in enumerate(content.splitlines(), 1):
            if PRIVATE_KEY_RE.search(line):
                findings.append({
                    "code": "credential_leak",
                    "message": f"Potential private key material detected in raw line in {rel_path}:{idx}.",
                })
            for match in ASSIGN_RE.finditer(line):
                key, val = match.groups()
                val_clean = val.strip().strip('"\'').lower()
                if val_clean in SAFE_VALUES or val_clean in SAFE_PLACEHOLDERS:
                    continue
                findings.append({
                    "code": "credential_leak",
                    "message": f"Potential credential leak in raw assignment of '{key}' in {rel_path}:{idx}.",
                })
            match = BEARER_RE.search(line)
            if match:
                val = match.group(1)
                val_clean = val.strip().strip('"\'').lower()
                if val_clean != "" and val_clean not in SAFE_PLACEHOLDERS:
                    findings.append({
                        "code": "credential_leak",
                        "message": f"Potential credential leak in raw Bearer Authorization header in {rel_path}:{idx}.",
                    })
    except Exception as exc:
        findings.append({
            "code": "file_read_error",
            "message": f"Failed to read file {rel_path}: {exc}"
        })
    return findings


def run_etf_sma_daily_offline_check(config: EtfSmaDailyOfflineCheckConfig) -> dict[str, Any]:
    """Orchestrate and validate the offline daily loop bundle and status checks."""
    if not config.bars_csv:
        raise ValidationError("bars_csv is required.")
    bars_path = Path(config.bars_csv)
    if not bars_path.exists():
        raise ValidationError(f"bars_csv path does not exist: {bars_path}")

    # 1. Determine as_of_date
    if config.as_of_date:
        as_of_date = config.as_of_date
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", as_of_date):
            raise ValidationError(f"as_of_date must be in YYYY-MM-DD format: {as_of_date}")
    else:
        bars = load_etf_sma_cycle_bars_csv(bars_path, symbol="SPY")
        if not bars:
            raise ValidationError("No usable bars found to derive default as-of date.")
        latest_dt = max(bar.timestamp for bar in bars)
        as_of_date = latest_dt.strftime("%Y-%m-%d")

    output_root = Path(config.output_root)
    bundle_dir = output_root / as_of_date

    findings: list[dict[str, Any]] = []
    daily_bundle_created = False
    daily_status_created = False
    daily_status_accepted = False
    validate_artifacts_ok = True

    # 2. Run V3A daily bundle logic
    try:
        v3a_payload = run_etf_sma_daily(EtfSmaDailyConfig(
            as_of_date=as_of_date,
            output_root=output_root,
            bars_csv=bars_path,
            reconciliation_state_path=config.reconciliation_state_path,
        ))
        daily_bundle_created = True
        
        # If the bundle itself flagged blockers, we propagate them
        if v3a_payload.get("blockers"):
            for blocker in v3a_payload["blockers"]:
                findings.append({
                    "code": blocker,
                    "message": f"V3A daily bundle generation reported blocker: {blocker}"
                })
    except Exception as exc:
        findings.append({
            "code": "daily_bundle_generation_failed",
            "message": f"V3A daily bundle generation failed: {exc}"
        })

    # 3. Run V3B daily status validator logic
    if daily_bundle_created:
        try:
            status_jsonl_path = bundle_dir / "bundle_status.jsonl"
            status_text_path = bundle_dir / "bundle_status.txt"
            
            v3b_payload = run_etf_sma_daily_status(EtfSmaDailyStatusConfig(
                bundle_dir=bundle_dir,
                output_status_jsonl=status_jsonl_path,
                output_status_text=status_text_path,
            ))
            daily_status_created = True
            if v3b_payload.get("status") == "accepted":
                daily_status_accepted = True
            
            # Merge findings from V3B status validator
            if v3b_payload.get("findings"):
                for f in v3b_payload["findings"]:
                    findings.append({
                        "code": f.get("code", "status_finding"),
                        "message": f.get("message", "V3B daily status finding")
                    })
        except Exception as exc:
            findings.append({
                "code": "daily_status_generation_failed",
                "message": f"V3B status validation failed: {exc}"
            })

    # 4. Check validate-artifacts agreement
    jsonl_files_to_check = [f for f in DAILY_BUNDLE_REQUIRED_FILES if f.endswith(".jsonl")]
    if daily_status_created:
        jsonl_files_to_check.append("bundle_status.jsonl")

    for fname in jsonl_files_to_check:
        fpath = bundle_dir / fname
        if fpath.exists():
            val_record = validate_artifact(fpath)
            if val_record.status != "passed":
                validate_artifacts_ok = False
                for f in val_record.findings:
                    findings.append({
                        "code": "artifact_validation_failed",
                        "message": f"Artifact validation failed for {fname}:{f.get('line')}: {f.get('message')} (rule: {f.get('rule_id')})"
                    })
        else:
            validate_artifacts_ok = False
            findings.append({
                "code": "missing_required_output",
                "message": f"Expected JSONL file '{fname}' is missing."
            })

    # Check that required text files and index file exist
    expected_txt_files = [f for f in DAILY_BUNDLE_REQUIRED_FILES if f.endswith(".txt")]
    if daily_status_created:
        expected_txt_files.append("bundle_status.txt")

    for fname in expected_txt_files:
        fpath = bundle_dir / fname
        if not fpath.exists():
            findings.append({
                "code": "missing_required_output",
                "message": f"Expected text file '{fname}' is missing."
            })

    index_file = output_root / "daily_run_index.jsonl"
    if not index_file.exists():
        findings.append({
            "code": "missing_required_output",
            "message": "Expected daily run index 'daily_run_index.jsonl' in output root is missing."
        })

    # 5. Scan text files for credential leaks
    for fname in expected_txt_files:
        fpath = bundle_dir / fname
        if fpath.exists():
            leak_findings = _check_txt_file_for_leaks(fpath)
            if leak_findings:
                findings.extend(leak_findings)

    # 6. Evaluate overall V3C status
    # Offline check status is accepted if there are no findings,
    # daily bundle and status were successfully created, daily status is accepted, and validate artifacts is ok.
    status = "accepted"
    if findings or not daily_bundle_created or not daily_status_accepted or not validate_artifacts_ok:
        status = "blocked"

    # Deterministic sorting of findings
    findings.sort(key=lambda x: (x.get("code", ""), x.get("message", "")))

    next_operator_action = "proceed_to_operator_brief" if status == "accepted" else "repair_blockers"

    # Prepare output paths
    output_jsonl_path = Path(config.output_check_jsonl) if config.output_check_jsonl else bundle_dir / "offline_check.jsonl"
    output_text_path = Path(config.output_check_text) if config.output_check_text else bundle_dir / "offline_check.txt"

    # Build the check record payload
    check_payload = {
        "phase": "offline_daily_loop_offline_check",
        "status": status,
        "as_of_date": as_of_date,
        "output_root": _normalize_path(output_root),
        "bundle_dir": _normalize_path(bundle_dir),
        "daily_bundle_created": daily_bundle_created,
        "daily_status_created": daily_status_created,
        "daily_status_accepted": daily_status_accepted,
        "validate_artifacts_ok": validate_artifacts_ok,
        "decision_matrix_required": True,
        "tests_required": ["tests/unit/test_etf_sma_cycle_decision_matrix.py"],
        "finding_count": len(findings),
        "findings": findings,
        "next_operator_action": next_operator_action,
        "authorization_status": {
            "live_trading_authorized": False,
            "paper_submit_authorized": False,
            "broker_mutation_authorized": False,
            "paper_broker_reads_authorized": False,
            "network_authorized": False,
            "credential_loading_authorized": False,
        }
    }

    # Ensure parent directories exist
    output_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    output_text_path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSONL offline check record (exactly one line)
    json_str = json.dumps(check_payload, sort_keys=True, separators=(",", ":"))
    output_jsonl_path.write_text(json_str + "\n", encoding="utf-8", newline="\n")

    # Write concise text status report
    findings_str = "\n".join(f"- [{f['code']}] {f['message']}" for f in findings) if findings else "none"
    text_report = (
        f"ETF/SMA Daily Offline Check (V3C) - {status.upper()}\n"
        f"================================================\n"
        f"as_of_date: {as_of_date}\n"
        f"bundle_dir: {_normalize_path(bundle_dir)}\n"
        f"daily_bundle_created: {str(daily_bundle_created).lower()}\n"
        f"daily_status_created: {str(daily_status_created).lower()}\n"
        f"daily_status_accepted: {str(daily_status_accepted).lower()}\n"
        f"validate_artifacts_ok: {str(validate_artifacts_ok).lower()}\n"
        f"finding_count: {len(findings)}\n\n"
        f"Findings:\n"
        f"{findings_str}\n\n"
        f"Authorization Status:\n"
        f"- live_trading_authorized: false\n"
        f"- paper_submit_authorized: false\n"
        f"- broker_mutation_authorized: false\n"
        f"- paper_broker_reads_authorized: false\n"
        f"- network_authorized: false\n"
        f"- credential_loading_authorized: false\n\n"
        f"Next Operator Action:\n"
        f"{next_operator_action}\n"
    )
    output_text_path.write_text(text_report, encoding="utf-8", newline="\n")

    return check_payload
