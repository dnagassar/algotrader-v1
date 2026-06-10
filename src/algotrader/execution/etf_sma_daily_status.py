"""Offline Daily Bundle Validator and Status Reporter.

This module validates that a generated V3A daily bundle meets safety, integrity,
and consistency checks, and writes status artifacts.
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


@dataclass(frozen=True, slots=True)
class EtfSmaDailyStatusConfig:
    """Configuration for the etf-sma-daily-status validator command."""

    bundle_dir: Path | str | None = None
    output_status_jsonl: Path | str | None = None
    output_status_text: Path | str | None = None


def compute_sha256(path: Path) -> str:
    """Compute sha256 hash of a file on disk."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


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


def run_etf_sma_daily_status(config: EtfSmaDailyStatusConfig) -> dict[str, Any]:
    """Execute the daily bundle validation status check."""
    # 1. Resolve bundle directory
    if config.bundle_dir:
        bundle_dir = Path(config.bundle_dir)
    else:
        # Scan default runs/daily directory for latest subfolder
        default_root = Path("runs/daily")
        if not default_root.exists() or not default_root.is_dir():
            raise ValidationError("Default runs/daily directory does not exist. Please specify --bundle-dir.")
        
        subdirs = []
        for p in default_root.iterdir():
            if p.is_dir() and re.match(r"^\d{4}-\d{2}-\d{2}$", p.name):
                subdirs.append(p)
        
        if not subdirs:
            raise ValidationError("No date-based subdirectories found in runs/daily. Please specify --bundle-dir.")
        
        # Latest by lexicographical sorting
        subdirs.sort(key=lambda x: x.name)
        bundle_dir = subdirs[-1]

    if not bundle_dir.exists():
        raise ValidationError(f"Bundle directory does not exist: {bundle_dir}")

    # Validate bundle_dir name format (as_of_date)
    as_of_date = bundle_dir.name
    findings = []
    
    # Flags to report
    required_files_present = True
    jsonl_parse_ok = True
    manifest_hashes_match = True
    daily_index_matches = True
    labels_present = True
    safety_booleans_present = True
    status_consistency_ok = True
    credential_scan_ok = True
    validate_artifacts_ok = True

    # 1. Check date format
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", as_of_date):
        findings.append({
            "code": "invalid_date_format",
            "message": f"Bundle directory name '{as_of_date}' is not in YYYY-MM-DD format."
        })
        # If the date format is completely invalid, we can't do index lookup properly, but we can continue.

    # Required files in the bundle directory
    required_files = DAILY_BUNDLE_REQUIRED_FILES
    
    for f_name in required_files:
        f_path = bundle_dir / f_name
        if not f_path.exists():
            required_files_present = False
            findings.append({
                "code": "file_missing",
                "message": f"Required file '{f_name}' is missing in bundle directory."
            })

    # Output root is the parent of the bundle dir
    output_root = bundle_dir.parent
    daily_index_path = output_root / "daily_run_index.jsonl"
    if not daily_index_path.exists():
        required_files_present = False
        findings.append({
            "code": "file_missing",
            "message": f"Required file 'daily_run_index.jsonl' is missing in output root '{output_root}'."
        })

    # Read and validate JSONL files (only if they exist)
    jsonl_records: dict[str, dict[str, Any]] = {}
    for f_name in ["cycle.jsonl", "brief.jsonl", "gate.jsonl", "bundle_manifest.jsonl"]:
        f_path = bundle_dir / f_name
        if f_path.exists():
            # Run existing artifact validator
            record = validate_artifact(f_path)
            
            if not record.parse_ok or not record.object_records_ok:
                jsonl_parse_ok = False
                validate_artifacts_ok = False
                findings.append({
                    "code": "jsonl_parse_error",
                    "message": f"JSONL parsing or syntax error in '{f_name}': {record.findings}"
                })
                continue
                
            if record.record_count != 1:
                findings.append({
                    "code": "record_count_mismatch",
                    "message": f"Expected exactly 1 record in '{f_name}', found {record.record_count}."
                })
            
            # Map validation record results
            if not record.credential_scan_ok:
                credential_scan_ok = False
            if not record.redaction_ok:
                validate_artifacts_ok = False
            if record.status != "passed":
                validate_artifacts_ok = False
                for finding in record.findings:
                    findings.append({
                        "code": "validate_artifacts_failed",
                        "message": f"Artifact validator failed for '{f_name}': {finding.get('message')} at line {finding.get('line')}."
                    })
            
            # Parse record dictionary
            try:
                content = f_path.read_text(encoding="utf-8").strip()
                if content:
                    jsonl_records[f_name] = json.loads(content)
            except Exception as exc:
                jsonl_parse_ok = False
                findings.append({
                    "code": "jsonl_parse_error",
                    "message": f"Could not load parsed content from '{f_name}': {exc}"
                })

    # Scan plain text files for leaks
    for f_name in ["brief.txt", "dashboard.txt"]:
        f_path = bundle_dir / f_name
        if f_path.exists():
            leak_findings = _check_txt_file_for_leaks(f_path)
            if leak_findings:
                credential_scan_ok = False
                findings.extend(leak_findings)

    # 2. Check manifest hashes and sizes
    manifest = jsonl_records.get("bundle_manifest.jsonl")
    if manifest:
        files_info = manifest.get("files", [])
        for f_info in files_info:
            rel_path_str = f_info.get("path")
            expected_sha256 = f_info.get("sha256")
            expected_size = f_info.get("byte_size")
            
            if rel_path_str:
                f_path = Path(rel_path_str)
                if not f_path.exists():
                    manifest_hashes_match = False
                    findings.append({
                        "code": "manifest_hash_mismatch",
                        "message": f"File referenced in manifest does not exist: {rel_path_str}"
                    })
                else:
                    actual_sha256 = compute_sha256(f_path)
                    actual_size = f_path.stat().st_size
                    if actual_sha256 != expected_sha256:
                        manifest_hashes_match = False
                        findings.append({
                            "code": "manifest_hash_mismatch",
                            "message": f"SHA256 mismatch for '{rel_path_str}': expected {expected_sha256}, got {actual_sha256}."
                        })
                    if actual_size != expected_size:
                        manifest_hashes_match = False
                        findings.append({
                            "code": "manifest_size_mismatch",
                            "message": f"Byte size mismatch for '{rel_path_str}': expected {expected_size}, got {actual_size}."
                        })

    # 3. Check daily index matches
    if daily_index_path.exists():
        index_entry = None
        try:
            with daily_index_path.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        if entry.get("as_of_date") == as_of_date:
                            index_entry = entry
                            break
        except Exception as exc:
            daily_index_matches = False
            findings.append({
                "code": "jsonl_parse_error",
                "message": f"Error parsing daily_run_index.jsonl: {exc}"
            })

        if not index_entry:
            daily_index_matches = False
            findings.append({
                "code": "daily_index_missing_entry",
                "message": f"No entry found in daily_run_index.jsonl for date '{as_of_date}'."
            })
        elif manifest:
            manifest_path_actual = bundle_dir / "bundle_manifest.jsonl"
            expected_norm_path = _normalize_path(manifest_path_actual)
            
            idx_manifest_path = index_entry.get("bundle_manifest_path")
            idx_sha256 = index_entry.get("sha256")
            idx_size = index_entry.get("byte_size")
            idx_status = index_entry.get("status")
            
            actual_sha256 = compute_sha256(manifest_path_actual)
            actual_size = manifest_path_actual.stat().st_size
            
            if idx_manifest_path != expected_norm_path:
                daily_index_matches = False
                findings.append({
                    "code": "daily_index_mismatch",
                    "message": f"Index path mismatch: expected '{expected_norm_path}', got '{idx_manifest_path}'."
                })
            if idx_sha256 != actual_sha256:
                daily_index_matches = False
                findings.append({
                    "code": "daily_index_mismatch",
                    "message": f"Index SHA256 mismatch: expected '{actual_sha256}', got '{idx_sha256}'."
                })
            if idx_size != actual_size:
                daily_index_matches = False
                findings.append({
                    "code": "daily_index_mismatch",
                    "message": f"Index byte size mismatch: expected {actual_size}, got {idx_size}."
                })
            if idx_status != manifest.get("bundle_state"):
                daily_index_matches = False
                findings.append({
                    "code": "daily_index_mismatch",
                    "message": f"Index status mismatch: expected '{manifest.get('bundle_state')}', got '{idx_status}'."
                })

    # 4. Check labels in manifest
    if manifest:
        labels = manifest.get("labels", [])
        required_labels = ["paper_lab_only", "not_live_authorized", "profit_claim=none"]
        for r_lbl in required_labels:
            if r_lbl not in labels:
                labels_present = False
                findings.append({
                    "code": "label_missing",
                    "message": f"Required safety label '{r_lbl}' is missing in bundle manifest."
                })

    # 5. Check safety booleans in JSONL records
    safety_booleans = {
        "cycle.jsonl": {
            "submitted": False,
            "mutated": False,
            "broker_action_performed": False,
            "broker_mutation_allowed": False,
            "live_authorized": False,
            "network_access_attempted": False,
            "credential_access_attempted": False,
        },
        "brief.jsonl": {
            "submitted": False,
            "mutated": False,
            "broker_action_performed": False,
            "network_access_attempted": False,
            "credential_access_attempted": False,
            "live_authorized": False,
            "paper_submit_allowed": False,
            "live_submit_allowed": False,
        },
        "gate.jsonl": {
            "submitted": False,
            "mutated": False,
            "broker_action_performed": False,
            "network_access_attempted": False,
            "credential_access_attempted": False,
            "live_authorized": False,
            "paper_submit_allowed": False,
            "live_submit_allowed": False,
            "order_authorization": False,
        },
        "bundle_manifest.jsonl": {
            "submitted": False,
            "mutated": False,
            "broker_action_performed": False,
            "broker_mutation_allowed": False,
            "live_authorized": False,
            "network_access_attempted": False,
            "credential_access_attempted": False,
        }
    }
    
    for f_name, expected_vars in safety_booleans.items():
        rec = jsonl_records.get(f_name)
        if rec:
            for var_name, expected_val in expected_vars.items():
                if var_name not in rec:
                    safety_booleans_present = False
                    findings.append({
                        "code": "safety_boolean_invalid",
                        "message": f"Safety key '{var_name}' is missing in '{f_name}'."
                    })
                elif rec[var_name] != expected_val:
                    safety_booleans_present = False
                    findings.append({
                        "code": "safety_boolean_invalid",
                        "message": f"Safety key '{var_name}' in '{f_name}' has invalid value: expected {expected_val}, got {rec[var_name]}."
                    })

    # Check safety fields in txt files
    txt_safety_patterns = {
        "brief.txt": {
            r"^submitted=false$": "submitted=false",
            r"^mutated=false$": "mutated=false",
            r"^paper_submit_allowed=false$": "paper_submit_allowed=false",
            r"^live_submit_allowed=false$": "live_submit_allowed=false",
            r"^profit_claim=none$": "profit_claim=none"
        },
        "dashboard.txt": {
            r"^submitted=false$": "submitted=false",
            r"^mutated=false$": "mutated=false",
            r"^paper_submit_allowed=false$": "paper_submit_allowed=false",
            r"^live_submit_allowed=false$": "live_submit_allowed=false",
            r"^scheduler_install_allowed=false$": "scheduler_install_allowed=false",
            r"^order_authorization=false$": "order_authorization=false"
        }
    }
    
    for f_name, expected_lines in txt_safety_patterns.items():
        f_path = bundle_dir / f_name
        if f_path.exists():
            try:
                lines = f_path.read_text(encoding="utf-8").splitlines()
                lines_stripped = [l.strip() for l in lines]
                for pattern, line_repr in expected_lines.items():
                    # Look for exact matching line
                    found = False
                    for l in lines_stripped:
                        if re.match(pattern, l, re.IGNORECASE):
                            found = True
                            break
                    if not found:
                        safety_booleans_present = False
                        findings.append({
                            "code": "safety_boolean_invalid",
                            "message": f"Safety line '{line_repr}' is missing or invalid in '{f_name}'."
                        })
            except Exception as exc:
                safety_booleans_present = False
                findings.append({
                    "code": "file_read_error",
                    "message": f"Failed to read '{f_name}': {exc}"
                })

    # 6. Check status consistency
    cycle_rec = jsonl_records.get("cycle.jsonl")
    brief_rec = jsonl_records.get("brief.jsonl")
    gate_rec = jsonl_records.get("gate.jsonl")
    manifest_rec = jsonl_records.get("bundle_manifest.jsonl")
    
    cycle_blockers = set(cycle_rec.get("blockers", [])) if cycle_rec else None
    brief_blockers = set(brief_rec.get("blockers", [])) if brief_rec else None
    gate_blockers = set(gate_rec.get("blockers", [])) if gate_rec else None
    manifest_blockers = set(manifest_rec.get("blockers", [])) if manifest_rec else None
    
    # Are blockers lists equal?
    blockers_sets = [s for s in [cycle_blockers, brief_blockers, gate_blockers, manifest_blockers] if s is not None]
    if blockers_sets:
        first_set = blockers_sets[0]
        for s in blockers_sets[1:]:
            if s != first_set:
                status_consistency_ok = False
                findings.append({
                    "code": "status_inconsistency",
                    "message": "Blocker lists are not consistent across bundle JSONL files."
                })
                break

    # Determine expected status state based on blockers
    has_blockers = False
    if cycle_rec and cycle_rec.get("blockers"):
        has_blockers = True
    elif brief_rec and brief_rec.get("blockers"):
        has_blockers = True
    elif gate_rec and gate_rec.get("blockers"):
        has_blockers = True
    elif manifest_rec and manifest_rec.get("blockers"):
        has_blockers = True

    if has_blockers:
        # Check blocked states
        if cycle_rec:
            dec = str(cycle_rec.get("decision", ""))
            if not dec.startswith("blocked/"):
                status_consistency_ok = False
                findings.append({
                    "code": "status_inconsistency",
                    "message": f"Cycle decision is '{dec}' but blockers are present."
                })
        if brief_rec:
            if brief_rec.get("brief_state") != "blocked":
                status_consistency_ok = False
                findings.append({
                    "code": "status_inconsistency",
                    "message": f"Brief state is '{brief_rec.get('brief_state')}' but blockers are present."
                })
            if brief_rec.get("current_action") != "blocked/fail_closed":
                status_consistency_ok = False
                findings.append({
                    "code": "status_inconsistency",
                    "message": f"Brief current_action is '{brief_rec.get('current_action')}' but blockers are present."
                })
            if brief_rec.get("recommended_operator_action") != "repair_m450_pipeline_manifest_before_operator_brief_use":
                status_consistency_ok = False
                findings.append({
                    "code": "status_inconsistency",
                    "message": f"Brief recommended_operator_action is '{brief_rec.get('recommended_operator_action')}' but blockers are present."
                })
        
        # Check brief.txt
        brief_txt = bundle_dir / "brief.txt"
        if brief_txt.exists():
            try:
                txt = brief_txt.read_text(encoding="utf-8")
                if "OPERATOR BRIEF (V3A) - BLOCKED" not in txt.upper():
                    status_consistency_ok = False
                    findings.append({
                        "code": "status_inconsistency",
                        "message": "brief.txt does not state BLOCKED status."
                    })
            except Exception:
                pass
                
        # Check gate.jsonl
        if gate_rec:
            if gate_rec.get("acceptance_gate_state") != "blocked_or_invalid":
                status_consistency_ok = False
                findings.append({
                    "code": "status_inconsistency",
                    "message": f"Gate state is '{gate_rec.get('acceptance_gate_state')}' but blockers are present."
                })
            if gate_rec.get("accepted_for_operator_observation") is not False:
                status_consistency_ok = False
                findings.append({
                    "code": "status_inconsistency",
                    "message": f"Gate accepted_for_operator_observation is True but blockers are present."
                })
                
        # Check dashboard.txt
        dash_txt = bundle_dir / "dashboard.txt"
        if dash_txt.exists():
            try:
                txt = dash_txt.read_text(encoding="utf-8")
                found_state_line = False
                for l in txt.splitlines():
                    if "export_state:" in l:
                        found_state_line = True
                        if "blocked" not in l.lower():
                            status_consistency_ok = False
                            findings.append({
                                "code": "status_inconsistency",
                                "message": f"dashboard.txt export_state is not 'blocked': '{l}'"
                            })
                if not found_state_line:
                    status_consistency_ok = False
                    findings.append({
                        "code": "status_inconsistency",
                        "message": "dashboard.txt is missing export_state line."
                    })
            except Exception:
                pass

        # Check bundle_manifest.jsonl
        if manifest_rec:
            if manifest_rec.get("bundle_state") != "blocked_or_invalid":
                status_consistency_ok = False
                findings.append({
                    "code": "status_inconsistency",
                    "message": f"Manifest bundle_state is '{manifest_rec.get('bundle_state')}' but blockers are present."
                })
            # Check individual files status
            files_list = manifest_rec.get("files", [])
            for f_entry in files_list:
                if f_entry.get("status") != "blocked":
                    status_consistency_ok = False
                    findings.append({
                        "code": "status_inconsistency",
                        "message": f"File '{f_entry.get('path')}' status in manifest is not 'blocked'."
                    })
    else:
        # Check ready states
        if cycle_rec:
            dec = str(cycle_rec.get("decision", ""))
            if dec.startswith("blocked/"):
                status_consistency_ok = False
                findings.append({
                    "code": "status_inconsistency",
                    "message": f"Cycle decision is '{dec}' but blockers are empty."
                })
        if brief_rec:
            if brief_rec.get("brief_state") != "ready":
                status_consistency_ok = False
                findings.append({
                    "code": "status_inconsistency",
                    "message": f"Brief state is '{brief_rec.get('brief_state')}' but blockers are empty."
                })
            if brief_rec.get("current_action") == "blocked/fail_closed":
                status_consistency_ok = False
                findings.append({
                    "code": "status_inconsistency",
                    "message": f"Brief current_action is 'blocked/fail_closed' but blockers are empty."
                })
                
        # Check brief.txt
        brief_txt = bundle_dir / "brief.txt"
        if brief_txt.exists():
            try:
                txt = brief_txt.read_text(encoding="utf-8")
                if "OPERATOR BRIEF (V3A) - READY" not in txt.upper():
                    status_consistency_ok = False
                    findings.append({
                        "code": "status_inconsistency",
                        "message": "brief.txt does not state READY status."
                    })
            except Exception:
                pass
                
        # Check gate.jsonl
        if gate_rec:
            if gate_rec.get("acceptance_gate_state") != "accepted_for_preview_only_observation":
                status_consistency_ok = False
                findings.append({
                    "code": "status_inconsistency",
                    "message": f"Gate state is '{gate_rec.get('acceptance_gate_state')}' but blockers are empty."
                })
            if gate_rec.get("accepted_for_operator_observation") is not True:
                status_consistency_ok = False
                findings.append({
                    "code": "status_inconsistency",
                    "message": f"Gate accepted_for_operator_observation is False but blockers are empty."
                })
                
        # Check dashboard.txt
        dash_txt = bundle_dir / "dashboard.txt"
        if dash_txt.exists():
            try:
                txt = dash_txt.read_text(encoding="utf-8")
                found_state_line = False
                for l in txt.splitlines():
                    if "export_state:" in l:
                        found_state_line = True
                        if "ready" not in l.lower():
                            status_consistency_ok = False
                            findings.append({
                                "code": "status_inconsistency",
                                "message": f"dashboard.txt export_state is not 'ready': '{l}'"
                            })
                if not found_state_line:
                    status_consistency_ok = False
                    findings.append({
                        "code": "status_inconsistency",
                        "message": "dashboard.txt is missing export_state line."
                    })
            except Exception:
                pass

        # Check bundle_manifest.jsonl
        if manifest_rec:
            if manifest_rec.get("bundle_state") != "ready":
                status_consistency_ok = False
                findings.append({
                    "code": "status_inconsistency",
                    "message": f"Manifest bundle_state is '{manifest_rec.get('bundle_state')}' but blockers are empty."
                })
            # Check individual files status
            files_list = manifest_rec.get("files", [])
            for f_entry in files_list:
                if f_entry.get("status") != "ready":
                    status_consistency_ok = False
                    findings.append({
                        "code": "status_inconsistency",
                        "message": f"File '{f_entry.get('path')}' status in manifest is not 'ready'."
                    })

    # Overall Status evaluation
    # Status is accepted if there are no findings and the manifest status is ready (no blockers).
    # If there are findings, or the files have blockers, we mark it blocked.
    # Wait, the prompt says:
    # "status: accepted or blocked"
    # "It should exit successfully when it can produce a status artifact, even if the status is blocked/failed due to validation findings."
    status = "accepted"
    if findings or has_blockers:
        status = "blocked"

    # Deterministic sorting of findings
    findings.sort(key=lambda x: (x.get("code", ""), x.get("message", "")))

    # Output paths
    status_jsonl_path = Path(config.output_status_jsonl) if config.output_status_jsonl else bundle_dir / "bundle_status.jsonl"
    status_text_path = Path(config.output_status_text) if config.output_status_text else bundle_dir / "bundle_status.txt"

    # Status record dict
    status_payload = {
        "as_of_date": as_of_date if re.match(r"^\d{4}-\d{2}-\d{2}$", as_of_date) else None,
        "bundle_dir": _normalize_path(bundle_dir),
        "credential_scan_ok": credential_scan_ok,
        "daily_index_matches": daily_index_matches,
        "finding_count": len(findings),
        "findings": findings,
        "jsonl_parse_ok": jsonl_parse_ok,
        "labels_present": labels_present,
        "manifest_hashes_match": manifest_hashes_match,
        "phase": "offline_daily_bundle_status",
        "required_files_present": required_files_present,
        "safety_booleans_present": safety_booleans_present,
        "status": status,
        "status_consistency_ok": status_consistency_ok,
        "validate_artifacts_ok": validate_artifacts_ok,
    }

    # Ensure parents exist
    status_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    status_text_path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSONL status record (exactly one line)
    json_str = json.dumps(status_payload, sort_keys=True, separators=(",", ":"))
    status_jsonl_path.write_text(json_str + "\n", encoding="utf-8", newline="\n")

    # Write concise text status report
    findings_str = "\n".join(f"- [{f['code']}] {f['message']}" for f in findings) if findings else "none"
    as_of_display = as_of_date if re.match(r"^\d{4}-\d{2}-\d{2}$", as_of_date) else "None"
    text_report = (
        f"ETF/SMA Daily Bundle Status (V3B) - {status.upper()}\n"
        f"============================================\n"
        f"bundle_dir: {_normalize_path(bundle_dir)}\n"
        f"as_of_date: {as_of_display}\n"
        f"required_files_present: {str(required_files_present).lower()}\n"
        f"jsonl_parse_ok: {str(jsonl_parse_ok).lower()}\n"
        f"manifest_hashes_match: {str(manifest_hashes_match).lower()}\n"
        f"daily_index_matches: {str(daily_index_matches).lower()}\n"
        f"labels_present: {str(labels_present).lower()}\n"
        f"safety_booleans_present: {str(safety_booleans_present).lower()}\n"
        f"status_consistency_ok: {str(status_consistency_ok).lower()}\n"
        f"credential_scan_ok: {str(credential_scan_ok).lower()}\n"
        f"validate_artifacts_ok: {str(validate_artifacts_ok).lower()}\n"
        f"finding_count: {len(findings)}\n\n"
        f"Findings:\n"
        f"{findings_str}\n"
    )
    status_text_path.write_text(text_report, encoding="utf-8", newline="\n")

    return status_payload
