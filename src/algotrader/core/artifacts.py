"""Pure standard library JSONL artifact validation module."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import re
from pathlib import Path
from typing import Sequence, Any, Optional

# Regex patterns for credential leakage check in raw lines
ASSIGN_RE = re.compile(
    r'\b(ALPACA_API_KEY|ALPACA_SECRET_KEY|ALPACA_API_SECRET_KEY|APCA_API_KEY_ID|APCA_API_SECRET_KEY)\s*[:=]\s*([^\s,;}"\'\\]+)',
    re.IGNORECASE
)
BEARER_RE = re.compile(r'\bAuthorization\s*:\s*Bearer\s+([^\s,;}"\'\\]+)', re.IGNORECASE)
PRIVATE_KEY_RE = re.compile(r'-----BEGIN\s+(?:[A-Z]+\s+)?PRIVATE\s+KEY-----', re.IGNORECASE)

# Safe values that are allowed and won't trigger credential leaks
SAFE_PLACEHOLDERS = {
    "redacted",
    "<redacted>",
    "***redacted***",
    "credentials_redacted",
}
SAFE_VALUES = {"true", "false", "null", "none", ""}

EXACT_SECRET_KEYS = {
    "api_key", "secret_key", "token", "password", "authorization", "bearer", "private_key",
    "alpaca_api_key", "alpaca_secret_key", "alpaca_api_secret_key", "apca_api_key_id", "apca_api_secret_key"
}


@dataclass
class ArtifactValidationRecord:
    path: str
    parse_ok: bool
    object_records_ok: bool
    record_count: int
    required_keys_ok: bool
    redaction_ok: bool
    credential_scan_ok: bool
    findings: list[dict[str, Any]]
    status: str


@dataclass
class ArtifactValidationReport:
    report_schema_version: int
    tool: str
    input_root: str
    output_path: str
    status: str
    scanned_file_count: int
    scanned_record_count: int
    file_result_count: int
    finding_count: int
    required_keys_checked: list[str]
    safety_flags: dict[str, bool]
    file_results: list[ArtifactValidationRecord]
    findings: list[dict[str, Any]]


def to_cwd_relative_posix_path(path: Path) -> str:
    """Computes POSIX path relative to current working directory."""
    try:
        abs_path = path.resolve()
        abs_base = Path.cwd().resolve()
        rel = abs_path.relative_to(abs_base)
        return rel.as_posix()
    except ValueError:
        return os.path.relpath(path, Path.cwd()).replace("\\", "/")


def is_probable_secret(val: str, key_name: str) -> bool:
    """Detects mixed-case 40-char or PK/AK 20-char secret shapes.
    Ignores hashes and git commit SHAs.
    """
    k_lower = key_name.lower()
    # If the key name indicates a hash/checksum/digest/git/fingerprint, do not flag it
    if any(h in k_lower for h in ("hash", "sha256", "checksum", "digest", "commit", "git", "signature", "fingerprint")):
        return False
    
    # Check for fake keys (e.g. PKFAKEFAKEFAKEFAKE12 or PKFAKE_NOT_A_SECRET)
    if re.search(r'\b(?:PK|SK|AK)FAKE_[A-Z0-9_]+\b', val, re.IGNORECASE):
        return True
    if re.search(r'\b(?:PK|SK|AK)FAKE[A-Z0-9_]{5,50}\b', val):
        return True
    
    # Check for Alpaca Public Key ID: PK or AK followed by 18 alphanumeric chars
    if re.search(r'\b(?:PK|AK)[A-Z0-9]{18}\b', val):
        return True
        
    # Check for 40-character alphanumeric secret key
    if re.search(r'\b[A-Za-z0-9]{40}\b', val):
        # Check if it is a pure lowercase/uppercase hex string (often a git SHA or hash)
        is_pure_hex = bool(re.match(r'^[0-9a-fA-F]{40}$', val))
        if is_pure_hex:
            return False
        return True
        
    return False


def check_raw_line_for_leaks(line: str, rel_path: str, line_num: int, findings: list[dict[str, Any]]) -> None:
    """Checks raw text lines for credentials before JSON parsing."""
    if PRIVATE_KEY_RE.search(line):
        findings.append({
            "path": rel_path,
            "line": line_num,
            "rule_id": "credential_leak",
            "message": "Potential private key material detected in raw line.",
            "field_path": "raw_line",
        })
        return

    for match in ASSIGN_RE.finditer(line):
        key, val = match.groups()
        val_clean = val.strip().strip('"\'').lower()
        if val_clean in SAFE_VALUES or val_clean in SAFE_PLACEHOLDERS:
            continue
        findings.append({
            "path": rel_path,
            "line": line_num,
            "rule_id": "credential_leak",
            "message": f"Potential credential leak in raw assignment of '{key}'.",
            "field_path": "raw_line",
        })

    match = BEARER_RE.search(line)
    if match:
        val = match.group(1)
        val_clean = val.strip().strip('"\'').lower()
        if val_clean != "" and val_clean not in SAFE_PLACEHOLDERS:
            findings.append({
                "path": rel_path,
                "line": line_num,
                "rule_id": "credential_leak",
                "message": "Potential credential leak in raw Bearer Authorization header.",
                "field_path": "raw_line",
            })


def scan_value_recursive(
    val: Any,
    field_path: str,
    rel_path: str,
    line_num: int,
    findings: list[dict[str, Any]],
    key_name: str
) -> None:
    """Recursively checks dicts and lists for credential shapes or redaction violations."""
    if isinstance(val, dict):
        for k, v in val.items():
            new_path = f"{field_path}.{k}" if field_path else k
            scan_value_recursive(v, new_path, rel_path, line_num, findings, k)
        return
        
    if isinstance(val, (list, tuple)):
        for idx, item in enumerate(val):
            new_path = f"{field_path}[{idx}]"
            scan_value_recursive(item, new_path, rel_path, line_num, findings, key_name)
        return

    if isinstance(val, bool) or val is None:
        return
        
    val_str = str(val)
    val_clean = val_str.strip().lower()
    
    if val_str == "" or val_clean in SAFE_PLACEHOLDERS:
        return

    k_lower = key_name.lower()
    
    # Ignore hash/digest/checksum/signature key names
    if any(h in k_lower for h in ("hash", "sha256", "checksum", "digest", "commit", "git", "signature", "fingerprint")):
        return

    is_secret_like = k_lower in EXACT_SECRET_KEYS
    
    if is_secret_like:
        findings.append({
            "path": rel_path,
            "line": line_num,
            "rule_id": "redaction_violation",
            "message": f"Secret-like key '{key_name}' has a non-redacted value.",
            "field_path": field_path,
        })
    else:
        if is_probable_secret(val_str, key_name):
            findings.append({
                "path": rel_path,
                "line": line_num,
                "rule_id": "credential_leak",
                "message": f"Potential credential leak detected in value of '{field_path}'.",
                "field_path": field_path,
            })


def sort_findings(findings_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sorts findings deterministically."""
    def key_func(f: dict[str, Any]) -> tuple[str, int, str, str]:
        return (
            str(f.get("path", "")),
            int(f.get("line", 0)),
            str(f.get("rule_id", "")),
            str(f.get("field_path", ""))
        )
    return sorted(findings_list, key=key_func)


def read_jsonl(path: Path) -> list[dict[str, object]]:
    """Reads valid JSONL objects. Throws ValueError on blank lines or invalid records."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                raise ValueError(f"Line {i}: Blank lines are not allowed inside JSONL artifacts.")
            try:
                record = json.loads(line_str)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Line {i}: Malformed JSON: {exc}")
            if not isinstance(record, dict):
                raise ValueError(f"Line {i}: JSONL record is not a JSON object.")
            records.append(record)
    return records


def validate_artifact(
    path: Path,
    *,
    required_keys: Sequence[str] = (),
    profile_name: str | None = None
) -> ArtifactValidationRecord:
    """Checks one file for syntax, required keys, credentials, and redactions."""
    rel_path = to_cwd_relative_posix_path(path)
    
    findings = []
    record_count = 0
    parse_ok = True
    object_records_ok = True
    required_keys_ok = True
    redaction_ok = True
    credential_scan_ok = True

    if not path.exists():
        findings.append({
            "path": rel_path,
            "line": 1,
            "rule_id": "file_not_found",
            "message": "File not found.",
            "field_path": "file"
        })
        return ArtifactValidationRecord(
            path=rel_path,
            parse_ok=False,
            object_records_ok=False,
            record_count=0,
            required_keys_ok=False,
            redaction_ok=False,
            credential_scan_ok=False,
            findings=findings,
            status="failed",
        )

    lines = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as exc:
        parse_ok = False
        findings.append({
            "path": rel_path,
            "line": 1,
            "rule_id": "invalid_json",
            "message": f"Failed to open/read file: {exc}",
            "field_path": "file",
        })

    if parse_ok:
        for i, line_raw in enumerate(lines, 1):
            line_str = line_raw.strip()
            
            if not line_str:
                parse_ok = False
                findings.append({
                    "path": rel_path,
                    "line": i,
                    "rule_id": "blank_line",
                    "message": "Blank lines are not allowed inside JSONL artifacts.",
                    "field_path": "raw_line",
                })
                continue

            check_raw_line_for_leaks(line_raw, rel_path, i, findings)

            try:
                record = json.loads(line_str)
            except json.JSONDecodeError as exc:
                parse_ok = False
                findings.append({
                    "path": rel_path,
                    "line": i,
                    "rule_id": "invalid_json",
                    "message": f"Malformed JSON: {exc}",
                    "field_path": "raw_line",
                })
                continue

            if not isinstance(record, dict):
                object_records_ok = False
                findings.append({
                    "path": rel_path,
                    "line": i,
                    "rule_id": "non_object",
                    "message": "JSONL record is not a JSON object.",
                    "field_path": "raw_line",
                })
                continue

            record_count += 1

            for req_key in required_keys:
                if req_key not in record:
                    required_keys_ok = False
                    findings.append({
                        "path": rel_path,
                        "line": i,
                        "rule_id": "missing_required_key",
                        "message": f"Missing required top-level key: '{req_key}'",
                        "field_path": req_key,
                    })

            scan_value_recursive(record, "", rel_path, i, findings, "")

    for f in findings:
        rid = f["rule_id"]
        if rid in ("invalid_json", "blank_line"):
            parse_ok = False
        elif rid == "non_object":
            object_records_ok = False
        elif rid == "missing_required_key":
            required_keys_ok = False
        elif rid == "redaction_violation":
            redaction_ok = False
        elif rid == "credential_leak":
            credential_scan_ok = False

    status = "passed" if not findings else "failed"

    return ArtifactValidationRecord(
        path=rel_path,
        parse_ok=parse_ok,
        object_records_ok=object_records_ok,
        record_count=record_count,
        required_keys_ok=required_keys_ok,
        redaction_ok=redaction_ok,
        credential_scan_ok=credential_scan_ok,
        findings=findings,
        status=status,
    )


def check_output_path_safety(input_root: Path, output_path: Path) -> None:
    """Enforces report writing safety rules."""
    abs_input = input_root.resolve()
    abs_output = output_path.resolve()
    
    if abs_output == abs_input:
        raise ValueError("Output path cannot be the same as the input root.")
        
    if abs_output.is_dir():
        raise ValueError("Output path must be a file path, not a directory.")
        
    is_inside = False
    try:
        abs_output.relative_to(abs_input)
        is_inside = True
    except ValueError:
        pass
        
    if is_inside:
        rel_parts = abs_output.relative_to(abs_input).parts
        if "validation" not in rel_parts and "report" not in rel_parts:
            raise ValueError(
                "Unsafe output path: --output is inside the input root but not under an excluded validation/report directory."
            )
            
    if abs_output.exists():
        if is_inside:
            rel_parts = abs_output.relative_to(abs_input).parts
            if "validation" not in rel_parts and "report" not in rel_parts:
                raise ValueError("Unsafe output path: Refusing to overwrite a scanned input artifact.")


def validate_tree(
    input_root: Path,
    *,
    output_path: Path,
    required_keys: Sequence[str] = ()
) -> ArtifactValidationReport:
    """Recursively validates jsonl files, avoiding output report directory scanning."""
    check_output_path_safety(input_root, output_path)
    
    abs_output_path = output_path.resolve()
    scanned_files = []
    
    if input_root.exists():
        for path in input_root.rglob("*.jsonl"):
            abs_p = path.resolve()
            
            # Exclude output file path
            if abs_p == abs_output_path:
                continue
                
            # Exclude output report directory if it contains validation or report
            is_excluded = False
            try:
                abs_p.relative_to(abs_output_path.parent)
                parent_parts = abs_output_path.parent.parts
                if "validation" in parent_parts or "report" in parent_parts:
                    is_excluded = True
            except ValueError:
                pass
                
            if is_excluded:
                continue
                
            scanned_files.append(path)
            
    # Deterministic sorting
    scanned_files.sort(key=lambda p: to_cwd_relative_posix_path(p))
    
    file_results = []
    global_findings = []
    scanned_record_count = 0
    
    for f in scanned_files:
        record = validate_artifact(f, required_keys=required_keys)
        file_results.append(record)
        scanned_record_count += record.record_count
        global_findings.extend(record.findings)
        
    status = "passed"
    if any(f["rule_id"] in ("credential_leak", "redaction_violation", "invalid_json", "blank_line") for f in global_findings):
        status = "blocked"
    elif global_findings:
        status = "failed"
        
    safety_flags = {
        "submitted": False,
        "mutated": False,
        "broker_accessed": False,
        "network_accessed": False,
        "credentials_read": False,
        "live_authorized": False,
        "paper_submit_authorized": False,
        "scanned_files_mutated": False,
    }
    
    return ArtifactValidationReport(
        report_schema_version=1,
        tool="validate-artifacts",
        input_root=to_cwd_relative_posix_path(input_root),
        output_path=to_cwd_relative_posix_path(output_path),
        status=status,
        scanned_file_count=len(scanned_files),
        scanned_record_count=scanned_record_count,
        file_result_count=len(file_results),
        finding_count=len(global_findings),
        required_keys_checked=list(required_keys),
        safety_flags=safety_flags,
        file_results=file_results,
        findings=global_findings,
    )


def write_validation_report(report: ArtifactValidationReport, output_path: Path) -> None:
    """Writes report deterministically to exactly one JSONL line."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    report_dict = {
        "report_schema_version": report.report_schema_version,
        "tool": report.tool,
        "input_root": report.input_root,
        "output_path": report.output_path,
        "status": report.status,
        "scanned_file_count": report.scanned_file_count,
        "scanned_record_count": report.scanned_record_count,
        "file_result_count": report.file_result_count,
        "finding_count": report.finding_count,
        "required_keys_checked": sorted(report.required_keys_checked),
        "safety_flags": report.safety_flags,
        "file_results": [
            {
                "path": res.path,
                "parse_ok": res.parse_ok,
                "object_records_ok": res.object_records_ok,
                "record_count": res.record_count,
                "required_keys_ok": res.required_keys_ok,
                "redaction_ok": res.redaction_ok,
                "credential_scan_ok": res.credential_scan_ok,
                "findings": sort_findings(res.findings),
                "status": res.status,
            }
            for res in report.file_results
        ],
        "findings": sort_findings(report.findings),
    }

    # Deterministic output serialization
    json_str = json.dumps(report_dict, sort_keys=True, separators=(",", ":"))
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json_str + "\n")
