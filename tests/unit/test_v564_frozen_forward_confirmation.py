from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.errors import ValidationError
from algotrader.research.v564_frozen_forward_confirmation import (
    build_v564_frozen_forward_preregistration,
    run_v564_frozen_forward_confirmation,
)

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "docs/design/v5_70_v564_frozen_forward_confirmation.md"
RECEIPT = ROOT / "docs/design/v5_70_v564_forward_data_receipt.md"
MODULE = ROOT / "src/algotrader/research/v564_frozen_forward_confirmation.py"
SCRIPT = ROOT / "scripts/run_v564_frozen_forward_confirmation.ps1"


def test_protocol_and_receipt_hashes_are_frozen() -> None:
    assert _hash(PROTOCOL) == "7977ef62d5b1da7b658e57aad34e85f91438659d9c5c639726abb23ee10e8e37"
    assert _hash(RECEIPT) == "9ad6db6e4cacf9e5accace6911052fb44f72fbe201609ce15fdbe8ba705a8ef9"


def test_preregistration_is_terminal_and_does_not_write(tmp_path: Path) -> None:
    payload = build_v564_frozen_forward_preregistration()
    assert payload["protocol_id"] == "v5_70_v564_frozen_forward_confirmation_v1"
    assert payload["forward_session_count"] == 314
    assert payload["parameter_search_performed"] is False
    assert payload["terminal_routes"] == ["preview_review", "close_stock_filter_family"]
    assert list(tmp_path.iterdir()) == []


def test_full_forward_replay_is_deterministic_and_terminal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    output = tmp_path / "output"
    first = run_v564_frozen_forward_confirmation(output)
    first_hashes = {p.name: _hash(p) for p in output.iterdir() if p.is_file()}
    second = run_v564_frozen_forward_confirmation(output)
    second_hashes = {p.name: _hash(p) for p in output.iterdir() if p.is_file()}
    assert first_hashes == second_hashes
    assert first["frozen_parent_reproduction"]["passed"] is True
    assert first["terminal_decision"]["route"] in {"preview_review", "close_stock_filter_family"}
    assert first["terminal_decision"]["paper_promotion_allowed"] is False
    assert first["safety"]["network_access"] is False
    assert first["safety"]["broker_access"] is False


def test_tampered_receipt_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tampered = tmp_path / "receipt.md"
    tampered.write_text(RECEIPT.read_text(encoding="utf-8") + "tamper\n", encoding="utf-8")
    import algotrader.research.v564_frozen_forward_confirmation as module
    monkeypatch.setattr(module, "_RECEIPT", tampered)
    with pytest.raises(ValidationError, match="data receipt SHA-256 mismatch"):
        build_v564_frozen_forward_preregistration()


def test_module_and_wrapper_are_offline_fail_closed(tmp_path: Path) -> None:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    assert not any(name.startswith(("requests", "httpx", "socket", "alpaca", "algotrader.execution", "algotrader.broker")) for name in imports)
    text = SCRIPT.read_text(encoding="utf-8")
    assert "preflight_sensitive_variables_loaded" in text
    assert "blocked_unsafe_environment" in text
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        return
    env = os.environ.copy()
    env["TIINGO_API_KEY"] = "sentinel-not-a-real-secret"
    completed = subprocess.run(
        [powershell, "-NoProfile", "-File", str(SCRIPT), "-OutputRoot", str(tmp_path / "blocked")],
        cwd=ROOT, env=env, capture_output=True, text=True, check=False, timeout=30,
    )
    combined = completed.stdout + completed.stderr
    assert completed.returncode == 2
    assert "preflight_sensitive_variables_loaded=true" in combined
    assert env["TIINGO_API_KEY"] not in combined


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
