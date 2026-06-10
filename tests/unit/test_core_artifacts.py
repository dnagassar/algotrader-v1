"""Unit tests for the canonical artifact validator and CLI command."""

from __future__ import annotations

import ast
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any
import pytest

from algotrader.core.artifacts import (
    read_jsonl,
    validate_artifact,
    validate_tree,
    write_validation_report,
    ArtifactValidationRecord,
    ArtifactValidationReport,
)

FIXTURES_DIR = Path("tests/fixtures/artifact_samples")


def test_read_jsonl_valid() -> None:
    records = read_jsonl(FIXTURES_DIR / "valid.jsonl")
    assert len(records) == 2
    assert records[0]["status"] == "passed"
    assert records[1]["status"] == "completed"


def test_read_jsonl_malformed() -> None:
    with pytest.raises(ValueError, match="Malformed JSON"):
        read_jsonl(FIXTURES_DIR / "malformed.jsonl")


def test_read_jsonl_blank_line() -> None:
    # We can write a custom temp file to verify blank line rejection
    pass


def test_parser_blank_line_rejection(tmp_path: Path) -> None:
    p = tmp_path / "blank.jsonl"
    p.write_text('{"a": 1}\n\n{"b": 2}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="Blank lines are not allowed"):
        read_jsonl(p)
        
    res = validate_artifact(p)
    assert res.parse_ok is False
    assert any(f["rule_id"] == "blank_line" for f in res.findings)


def test_parser_non_object_rejection(tmp_path: Path) -> None:
    p = tmp_path / "non_object.jsonl"
    p.write_text('{"a": 1}\n[1, 2, 3]\n', encoding="utf-8")
    with pytest.raises(ValueError, match="JSONL record is not a JSON object"):
        read_jsonl(p)
        
    res = validate_artifact(p)
    assert res.object_records_ok is False
    assert any(f["rule_id"] == "non_object" for f in res.findings)


def test_parser_empty_file_handling(tmp_path: Path) -> None:
    p = tmp_path / "empty.jsonl"
    p.write_text("", encoding="utf-8")
    records = read_jsonl(p)
    assert len(records) == 0
    
    res = validate_artifact(p)
    assert res.parse_ok is True
    assert res.record_count == 0
    assert len(res.findings) == 0


def test_parser_truncated_final_line(tmp_path: Path) -> None:
    p = tmp_path / "truncated.jsonl"
    p.write_text('{"a": 1}\n{"b": ', encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed JSON"):
        read_jsonl(p)
        
    res = validate_artifact(p)
    assert res.parse_ok is False
    assert any(f["rule_id"] == "invalid_json" for f in res.findings)


def test_parser_crlf_behavior(tmp_path: Path) -> None:
    p = tmp_path / "crlf.jsonl"
    p.write_bytes(b'{"a": 1}\r\n{"b": 2}\r\n')
    records = read_jsonl(p)
    assert len(records) == 2
    assert records[0]["a"] == 1
    assert records[1]["b"] == 2


def test_required_keys_checking() -> None:
    res = validate_artifact(FIXTURES_DIR / "missing_keys.jsonl", required_keys=["status"])
    assert res.required_keys_ok is False
    assert any(f["rule_id"] == "missing_required_key" for f in res.findings)
    
    res_ok = validate_artifact(FIXTURES_DIR / "valid.jsonl", required_keys=["status"])
    assert res_ok.required_keys_ok is True
    assert len(res_ok.findings) == 0


def test_credential_leak_fake_credential_leak() -> None:
    res = validate_artifact(FIXTURES_DIR / "credential_leak.jsonl")
    assert res.credential_scan_ok is False
    assert any(f["rule_id"] == "credential_leak" for f in res.findings)
    
    # Verify report/findings do NOT contain the value PKFAKEFAKEFAKEFAKE12
    report_json = json.dumps(res.findings)
    assert "PKFAKEFAKEFAKEFAKE12" not in report_json


def test_credential_leak_nested_leak(tmp_path: Path) -> None:
    p = tmp_path / "nested_leak.jsonl"
    p.write_text('{"nested": {"auth_token": "PKFAKEFAKEFAKEFAKE12"}}\n', encoding="utf-8")
    res = validate_artifact(p)
    assert res.credential_scan_ok is False or res.redaction_ok is False
    assert len(res.findings) > 0
    assert "PKFAKEFAKEFAKEFAKE12" not in json.dumps(res.findings)


def test_false_positive_regression_for_legitimate_fields(tmp_path: Path) -> None:
    p = tmp_path / "safe_fields.jsonl"
    p.write_text(
        '{"credential_access_attempted": true, '
        '"ALPACA_API_KEY_loaded": false, '
        '"ALPACA_SECRET_KEY_loaded": false, '
        '"APCA_API_KEY_ID_loaded": false, '
        '"APCA_API_SECRET_KEY_loaded": false, '
        '"redaction": "credentials_redacted", '
        '"sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}\n',
        encoding="utf-8"
    )
    res = validate_artifact(p)
    assert res.status == "passed"
    assert len(res.findings) == 0


def test_redacted_placeholder_values_pass(tmp_path: Path) -> None:
    p = tmp_path / "redacted.jsonl"
    p.write_text(
        '{"api_key": "REDACTED", "secret": "<REDACTED>", '
        '"token": "***REDACTED***", "password": "credentials_redacted", '
        '"authorization": null}\n',
        encoding="utf-8"
    )
    res = validate_artifact(p)
    assert res.status == "passed"
    assert len(res.findings) == 0


def test_determinism_and_byte_stability(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    input_root.mkdir()
    (input_root / "file2.jsonl").write_text('{"status": "passed"}\n', encoding="utf-8")
    (input_root / "file1.jsonl").write_text('{"status": "passed"}\n', encoding="utf-8")
    
    output = tmp_path / "report.jsonl"
    
    report1 = validate_tree(input_root, output_path=output)
    write_validation_report(report1, output)
    content1 = output.read_bytes()
    
    report2 = validate_tree(input_root, output_path=output)
    write_validation_report(report2, output)
    content2 = output.read_bytes()
    
    assert content1 == content2


def test_determinism_second_run_does_not_scan_first_report(tmp_path: Path) -> None:
    # If the report is written inside input_root but in validation/ subfolder, it should be excluded
    input_root = tmp_path / "runs"
    input_root.mkdir()
    (input_root / "a.jsonl").write_text('{"status": "passed"}\n', encoding="utf-8")
    
    output_path = input_root / "validation" / "artifact_validation_report.jsonl"
    
    report1 = validate_tree(input_root, output_path=output_path)
    write_validation_report(report1, output_path)
    
    # Scanned file count should be 1, not 2
    assert report1.scanned_file_count == 1
    
    # Run again: should still be 1 scanned file
    report2 = validate_tree(input_root, output_path=output_path)
    assert report2.scanned_file_count == 1


def test_unsafe_output_path_refusal(tmp_path: Path) -> None:
    input_root = tmp_path / "runs"
    input_root.mkdir()
    (input_root / "a.jsonl").write_text('{"status": "passed"}\n', encoding="utf-8")
    
    # Unsafe output path: inside input_root but not under validation/ or report/
    unsafe_output = input_root / "unsafe_report.jsonl"
    with pytest.raises(ValueError, match="Unsafe output path"):
        validate_tree(input_root, output_path=unsafe_output)


def test_scanned_files_unchanged(tmp_path: Path) -> None:
    input_root = tmp_path / "runs"
    input_root.mkdir()
    f = input_root / "a.jsonl"
    f.write_text('{"status": "passed"}\n', encoding="utf-8")
    initial_content = f.read_bytes()
    
    output_path = input_root / "validation" / "report.jsonl"
    report = validate_tree(input_root, output_path=output_path)
    write_validation_report(report, output_path)
    
    assert f.read_bytes() == initial_content


def test_artifacts_ast_guard() -> None:
    path = Path("src/algotrader/core/artifacts.py")
    content = path.read_text(encoding="utf-8")
    tree = ast.parse(content)
    
    forbidden_prefixes = (
        "algotrader.execution", "algotrader.broker", "algotrader.brokers", "algotrader.llm",
        "algotrader.llms", "algotrader.runtime", "alpaca", "alpaca_trade_api",
        "socket", "subprocess", "requests", "httpx", "urllib", "aiohttp"
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(alias.name.startswith(p) for p in forbidden_prefixes), f"Forbidden import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                assert not any(node.module.startswith(p) for p in forbidden_prefixes), f"Forbidden import from: {node.module}"
                
    forbidden_calls = {"os.getenv", "os.environ.get", "getenv", "environ.get", "socket.socket", "subprocess.run", "subprocess.Popen"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            call_name = ""
            if isinstance(func, ast.Name):
                call_name = func.id
            elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                call_name = f"{func.value.id}.{func.attr}"
            elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Attribute) and isinstance(func.value.value, ast.Name):
                call_name = f"{func.value.value.id}.{func.value.attr}.{func.attr}"
                
            assert call_name not in forbidden_calls, f"Forbidden call: {call_name}"


def test_cli_command_exit_codes(tmp_path: Path) -> None:
    from algotrader.cli import main
    
    fixture_root = tmp_path / "runs"
    fixture_root.mkdir()
    
    # 1. Clean run: exit 0
    (fixture_root / "valid.jsonl").write_text('{"status": "passed"}\n', encoding="utf-8")
    output_report = fixture_root / "validation" / "report.jsonl"
    
    code = main([
        "validate-artifacts",
        "--input-root", str(fixture_root),
        "--output", str(output_report),
        "--required-key", "status"
    ])
    assert code == 0
    assert output_report.exists()
    
    # 2. Findings run: exit 1
    (fixture_root / "invalid.jsonl").write_text('{"status": "passed"}\ninvalid_json\n', encoding="utf-8")
    code = main([
        "validate-artifacts",
        "--input-root", str(fixture_root),
        "--output", str(output_report)
    ])
    assert code == 1
    
    # 3. Operational error run (unsafe path): exit 2
    unsafe_report = fixture_root / "unsafe_report.jsonl"
    code = main([
        "validate-artifacts",
        "--input-root", str(fixture_root),
        "--output", str(unsafe_report)
    ])
    assert code == 2
