from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
CANARY_WRAPPER = REPO_ROOT / "scripts" / "run_v536_windows_host_canary.ps1"
PROVISION_WRAPPER = REPO_ROOT / "scripts" / "provision_v536_windows_credential.ps1"
PROVISION_LAUNCHER = REPO_ROOT / "scripts" / "launch_v536_credential_provisioning.py"


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
    assert "-I" in text
    assert "-B" in text
    assert "launch_v536_credential_provisioning.py" in text
    assert "-m algotrader.execution.v536_credential_provisioning" not in lowered
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


def test_exact_launcher_rejects_conflicting_pythonpath_package(tmp_path: Path) -> None:
    conflict_root = tmp_path / "conflicting editable"
    conflict_module = (
        conflict_root
        / "algotrader"
        / "execution"
        / "v536_credential_provisioning.py"
    )
    conflict_module.parent.mkdir(parents=True)
    (conflict_root / "algotrader" / "__init__.py").write_text("", encoding="utf-8")
    (conflict_module.parent / "__init__.py").write_text("", encoding="utf-8")
    conflict_module.write_text(
        'print("CONFLICTING_EDITABLE_IMPORTED")\n',
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(conflict_root)
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(PROVISION_LAUNCHER),
            "--authorization-artifact",
            str((tmp_path / "missing.json").resolve()),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "provisioning_write_not_authorized" in result.stdout
    assert "CONFLICTING_EDITABLE_IMPORTED" not in (result.stdout + result.stderr)


def test_production_wrapper_uses_exact_deployment_with_spaces_from_other_cwd(
    tmp_path: Path,
) -> None:
    deployment = tmp_path / "deployment with spaces"
    deployment.mkdir()
    ignored = shutil.ignore_patterns(
        ".git",
        "runs",
        ".pytest_cache",
        "__pycache__",
        "*.pyc",
    )
    for directory in ("src", "scripts", "docs"):
        shutil.copytree(
            REPO_ROOT / directory,
            deployment / directory,
            ignore=ignored,
        )
    module_path = (
        deployment
        / "src"
        / "algotrader"
        / "execution"
        / "v536_credential_provisioning.py"
    )
    module_text = module_path.read_text(encoding="utf-8")
    module_text = module_text.replace(
        '"provisioning_authorization_unavailable"',
        '"provisioning_authorization_unavailable_exact_fixture"',
    )
    module_path.write_text(module_text, encoding="utf-8")
    for args in (
        ("init",),
        ("config", "user.email", "offline@example.invalid"),
        ("config", "user.name", "Offline Test"),
        ("config", "core.autocrlf", "false"),
        ("add", "."),
        ("commit", "-m", "fixture"),
    ):
        subprocess.run(
            ["git", *args],
            cwd=deployment,
            capture_output=True,
            text=True,
            check=True,
        )

    conflict_root = tmp_path / "conflict package"
    conflict_module = (
        conflict_root
        / "algotrader"
        / "execution"
        / "v536_credential_provisioning.py"
    )
    conflict_module.parent.mkdir(parents=True)
    (conflict_root / "algotrader" / "__init__.py").write_text("", encoding="utf-8")
    (conflict_module.parent / "__init__.py").write_text("", encoding="utf-8")
    conflict_module.write_text(
        'print("CONFLICTING_EDITABLE_IMPORTED")\n',
        encoding="utf-8",
    )
    caller = tmp_path / "unrelated caller cwd"
    caller.mkdir()
    missing = deployment / "missing authorization.json"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(conflict_root)
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(deployment / "scripts" / PROVISION_WRAPPER.name),
            "-AuthorizationArtifact",
            str(missing),
            "-ProvisionAuthorized",
        ],
        cwd=caller,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 2
    assert "provisioning_authorization_unavailable_exact_fixture" in output
    assert "CONFLICTING_EDITABLE_IMPORTED" not in output
    assert not missing.exists()


def test_missing_launcher_is_sanitized_before_python_or_prompt(tmp_path: Path) -> None:
    scripts = tmp_path / "deployment" / "scripts"
    scripts.mkdir(parents=True)
    wrapper = scripts / PROVISION_WRAPPER.name
    shutil.copy2(PROVISION_WRAPPER, wrapper)
    secret_path_sentinel = tmp_path / "V536_SECRET_PATH_SENTINEL.json"
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(wrapper),
            "-AuthorizationArtifact",
            str(secret_path_sentinel),
            "-ProvisionAuthorized",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 2
    assert "provisioning_runtime_source_unavailable" in output
    assert "V536_SECRET_PATH_SENTINEL" not in output
    assert not secret_path_sentinel.exists()
