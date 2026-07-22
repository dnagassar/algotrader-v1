from __future__ import annotations

from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]
CANARY_WRAPPER = REPO_ROOT / "scripts" / "run_v536_windows_host_canary.ps1"
PROVISION_WRAPPER = REPO_ROOT / "scripts" / "provision_v536_windows_credential.ps1"


def test_canary_wrapper_passes_only_authorization_path_mode_and_boolean_gates() -> None:
    text = CANARY_WRAPPER.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "--authorization-artifact" in text
    assert "--task-mutation-authorized" in text
    assert "--credential-read-authorized" in text
    assert "--execute-authorized" in text
    assert "register-scheduledtask" not in lowered
    assert "enable-scheduledtask" not in lowered
    assert "disable-scheduledtask" not in lowered
    assert "start-scheduledtask" not in lowered
    assert "get-content" not in lowered
    assert "convertto-securestring" not in lowered
    assert "alpaca_api_key=" not in lowered
    assert "alpaca_secret_key=" not in lowered
    assert ".env" not in lowered


def test_provisioning_wrapper_has_no_secret_parameter_or_helper_store() -> None:
    text = PROVISION_WRAPPER.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "--authorization-artifact" in text
    assert "--provision-authorized" in text
    assert "apikey" not in lowered
    assert "apisecret" not in lowered
    assert "password" not in lowered
    assert "read-host" not in lowered
    assert "cmdkey" not in lowered
    assert "convertto-securestring" not in lowered
    assert "register-scheduledtask" not in lowered
    assert "enable-scheduledtask" not in lowered


def test_canary_wrapper_gate_fails_before_missing_artifact_or_python() -> None:
    missing = REPO_ROOT / "runs" / "must_not_exist_v536_authorization.json"
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(CANARY_WRAPPER),
            "-Mode",
            "execute",
            "-AuthorizationArtifact",
            str(missing),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "task-mutation authorization" in (result.stdout + result.stderr)
    assert not missing.exists()


def test_provisioning_wrapper_gate_fails_before_missing_artifact_or_prompt() -> None:
    missing = REPO_ROOT / "runs" / "must_not_exist_v536_provisioning.json"
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PROVISION_WRAPPER),
            "-AuthorizationArtifact",
            str(missing),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "separate explicit write authorization" in (
        result.stdout + result.stderr
    )
    assert not missing.exists()
