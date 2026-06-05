from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOAD_ENV_SCRIPT = PROJECT_ROOT / "scripts" / "dev" / "load_env.ps1"


def test_load_env_aliases_api_secret_key_without_printing_value(tmp_path) -> None:
    powershell = _powershell()
    env_path = tmp_path / ".env"
    env_path.write_text("ALPACA_API_SECRET_KEY=alias-secret-for-test\n", encoding="utf-8")

    result = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-Command",
            "\n".join(
                (
                    "$ErrorActionPreference = 'Stop'",
                    "Remove-Item -Path Env:ALPACA_SECRET_KEY -ErrorAction SilentlyContinue",
                    "Remove-Item -Path Env:ALPACA_API_SECRET_KEY -ErrorAction SilentlyContinue",
                    f". '{_ps_quote(LOAD_ENV_SCRIPT)}' -Path '{_ps_quote(env_path)}' -Quiet",
                    "if ($env:ALPACA_SECRET_KEY -and "
                    "($env:ALPACA_SECRET_KEY -eq $env:ALPACA_API_SECRET_KEY)) "
                    "{ 'alias:set' } else { 'alias:missing' }",
                )
            ),
        ],
        cwd=PROJECT_ROOT,
        env=_scrubbed_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "alias:set"
    assert "alias-secret-for-test" not in result.stdout
    assert "alias-secret-for-test" not in result.stderr


def _powershell() -> str:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify scripts/dev/load_env.ps1")
    return powershell


def _scrubbed_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("ALPACA_API_SECRET_KEY", None)
    env.pop("ALPACA_SECRET_KEY", None)
    return env


def _ps_quote(path: Path) -> str:
    return str(path).replace("'", "''")
