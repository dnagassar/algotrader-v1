from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from algotrader.core.crypto_bounded_probe_lifecycle import (
    build_dormant_lifecycle_plan,
    canonical_json_bytes,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / (
    "run_crypto_tournament_v2_bounded_paper_probe_lifecycle.ps1"
)
KEY = "wrapper-paper-key-never-print"
SECRET = "wrapper-paper-secret-never-print"
ACCOUNT = "wrapper-paper-account-never-print"
AUTHORIZATION = (
    "Authorize exact BTCUSD entry and exit for plan fingerprint "
    + "a" * 64
)
OPERATOR_ROOT_BLOCK = '''$OperatorGrantRoot = Join-Path (
    [Environment]::GetFolderPath(
        [System.Environment+SpecialFolder]::LocalApplicationData
    )
) "algo_trader\\operator_grants"'''


def test_v530_lifecycle_wrapper_contract_is_exact_and_bounded() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert (
        "algotrader.execution."
        "crypto_tournament_v2_bounded_paper_probe_lifecycle_operator"
    ) in script
    assert "$PaperMutationAuthorized.IsPresent" in script
    assert "$AllowNetwork.IsPresent" in script
    assert "$GrantedAuthorizationPath" in script
    assert "v530_exact_operation_authorization_provided=" in script
    assert "credential_values_exposed=false" in script
    assert "live_endpoint_touched=false" in script
    assert "--exact-operation-authorization-stdin" in script
    assert ".StandardInput.Write($AuthorizationText)" in script
    assert ".ArgumentList.Add" in script
    assert '"-I",' in script
    assert "$TrustedPythonPath" in script
    assert "Get-AuthenticodeSignature" in script
    assert "Python Software Foundation" in script
    assert "Resolve-ExternalOperatorGrant" in script
    assert "Test-ReparsePointFreePath" in script
    assert "LocalApplicationData" in script
    assert '$ProcessInfo.FileName = "python"' not in script
    for variable_name in (
        "PYTHONPATH",
        "PYTHONHOME",
        "PYTHONSTARTUP",
        "PYTHONINSPECT",
        "PYTHONUSERBASE",
        "PYTHONBREAKPOINT",
        "PYTHONPYCACHEPREFIX",
    ):
        assert f'$ProcessInfo.Environment.Remove($Name)' in script
        assert f'"{variable_name}"' in script
    assert "Start-Process" not in script
    for forbidden in (
        '"--exact-operation-authorization",',
        "--expected-paper-account-id",
        '"--as-of",',
        "$ExactOperationAuthorization",
        "$ExpectedPaperAccountId",
        "$AsOf",
        "broker_mutation_performed=false",
        "paper_submit_performed=false",
        "paper_cancel_performed=false",
        "--submit",
        "--cancel",
        "--replace",
        "--close",
        "--liquidate",
    ):
        assert forbidden not in script


@pytest.mark.parametrize(
    "omitted",
    ("all", "paper_switch", "network_switch", "authorization", "plan"),
)
def test_v530_wrapper_missing_gate_never_invokes_python(
    tmp_path: Path,
    omitted: str,
) -> None:
    plan = tmp_path / "plan.json"
    plan.write_text("{}", encoding="utf-8")
    capture = tmp_path / "args.json"
    env = _fake_python_env(tmp_path, capture)
    arguments = _authorized_arguments(plan)
    if omitted == "all":
        arguments = []
    elif omitted == "paper_switch":
        arguments.remove("-PaperMutationAuthorized")
    elif omitted == "network_switch":
        arguments.remove("-AllowNetwork")
    elif omitted == "authorization":
        index = arguments.index("-GrantedAuthorizationPath")
        del arguments[index : index + 2]
    elif omitted == "plan":
        index = arguments.index("-Plan")
        del arguments[index : index + 2]

    result = _invoke(arguments, env)

    assert result.returncode == 2, result.stdout + result.stderr
    assert not capture.exists()
    assert KEY not in result.stdout + result.stderr
    assert SECRET not in result.stdout + result.stderr


def test_v530_wrapper_forwards_exact_authorization_only_over_stdin(
    tmp_path: Path,
) -> None:
    plan = tmp_path / "sealed plan.json"
    _write_dormant_plan(plan)
    capture = tmp_path / "args.json"
    env = _fake_python_env(tmp_path, capture)

    result = _invoke(_authorized_arguments(plan), env)

    combined = result.stdout + result.stderr
    assert result.returncode == 2, combined
    assert "dormant_pending_terminal_winner" in combined
    assert "v530_stop_reasons=" not in combined
    assert not capture.exists()
    assert not Path(env["PYTHON_STDIN_CAPTURE"]).exists()
    assert not Path(env["PYTHON_STARTUP_MARKER"]).exists()
    assert KEY not in combined
    assert SECRET not in combined
    assert ACCOUNT not in combined
    assert AUTHORIZATION not in combined


def test_v530_wrapper_rejects_planner_request_as_grant(
    tmp_path: Path,
) -> None:
    plan = tmp_path / "plan.json"
    plan.write_text("{}", encoding="utf-8")
    capture = tmp_path / "args.json"
    env = _fake_python_env(tmp_path, capture)
    arguments = _authorized_arguments(plan)
    request = tmp_path / "authorization_request.txt"
    request.write_text(AUTHORIZATION, encoding="utf-8")
    grant_index = arguments.index("-GrantedAuthorizationPath") + 1
    arguments[grant_index] = str(request)

    result = _invoke(arguments, env)

    assert result.returncode == 2, result.stdout + result.stderr
    assert not capture.exists()
    assert AUTHORIZATION not in result.stdout + result.stderr


def test_v530_wrapper_rejects_renamed_request_inside_repository(
    tmp_path: Path,
) -> None:
    fixture_repo = tmp_path / "fixture-repo"
    script = _copy_test_wrapper(
        fixture_repo,
        fixture_repo,
    )
    plan = tmp_path / "plan.json"
    plan.write_text("{}", encoding="utf-8")
    grant = fixture_repo / "renamed-grant.txt"
    grant.write_text(AUTHORIZATION, encoding="utf-8")
    capture = tmp_path / "args.json"
    env = _fake_python_env(tmp_path, capture)

    result = _invoke(
        [
            "-PaperMutationAuthorized",
            "-AllowNetwork",
            "-Plan",
            str(plan),
            "-GrantedAuthorizationPath",
            str(grant),
        ],
        env,
        script=script,
        cwd=fixture_repo,
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert "exact_operation_authorization_required" in result.stdout
    assert not capture.exists()


@pytest.mark.parametrize(
    "payload",
    (b"", b"   \r\n", b"\x00", b"\xff", b"a" * 4097),
)
def test_v530_wrapper_rejects_invalid_authorization_file_before_python(
    tmp_path: Path,
    payload: bytes,
) -> None:
    plan = tmp_path / "plan.json"
    plan.write_text("{}", encoding="utf-8")
    capture = tmp_path / "args.json"
    env = _fake_python_env(tmp_path, capture)
    arguments = _authorized_arguments(plan)
    _grant_path(plan).write_bytes(payload)

    result = _invoke(arguments, env)

    assert result.returncode == 2, result.stdout + result.stderr
    assert not capture.exists()
    assert AUTHORIZATION not in result.stdout + result.stderr


@pytest.mark.parametrize("kind", ("missing", "directory"))
def test_v530_wrapper_rejects_missing_or_nonfile_authorization(
    tmp_path: Path,
    kind: str,
) -> None:
    plan = tmp_path / "plan.json"
    plan.write_text("{}", encoding="utf-8")
    capture = tmp_path / "args.json"
    env = _fake_python_env(tmp_path, capture)
    arguments = _authorized_arguments(plan)
    grant = _grant_path(plan)
    grant.unlink()
    if kind == "directory":
        grant.mkdir()

    result = _invoke(arguments, env)

    assert result.returncode == 2, result.stdout + result.stderr
    assert not capture.exists()


def test_v530_wrapper_preserves_exact_4096_byte_authorization(
    tmp_path: Path,
) -> None:
    plan = tmp_path / "plan.json"
    _write_dormant_plan(plan)
    capture = tmp_path / "args.json"
    env = _fake_python_env(tmp_path, capture)
    arguments = _authorized_arguments(plan)
    authorization = "a" * 4096
    _grant_path(plan).write_text(authorization, encoding="utf-8")

    result = _invoke(arguments, env)

    combined = result.stdout + result.stderr
    assert result.returncode == 2, combined
    assert "dormant_pending_terminal_winner" in combined
    assert "v530_stop_reasons=" not in combined
    assert not Path(env["PYTHON_STDIN_CAPTURE"]).exists()


@pytest.mark.parametrize(
    ("change", "value"),
    (
        ("APP_PROFILE", "live"),
        ("APP_PROFILE", "development"),
        ("ALPACA_PAPER_BASE_URL", "https://api.alpaca.markets"),
        ("ALPACA_PAPER_BASE_URL", "https://example.invalid"),
        ("NETWORK_TESTS", "true"),
        ("ALPACA_API_KEY", ""),
        ("ALPACA_SECRET_KEY", ""),
        ("ALPACA_EXPECTED_PAPER_ACCOUNT_ID", ""),
    ),
)
def test_v530_wrapper_rejects_unsafe_preflight_before_python(
    tmp_path: Path,
    change: str,
    value: str,
) -> None:
    plan = tmp_path / "plan.json"
    plan.write_text("{}", encoding="utf-8")
    capture = tmp_path / "args.json"
    env = _fake_python_env(tmp_path, capture)
    env[change] = value

    result = _invoke(_authorized_arguments(plan), env)

    assert result.returncode == 2, result.stdout + result.stderr
    assert not capture.exists()
    assert KEY not in result.stdout + result.stderr
    assert SECRET not in result.stdout + result.stderr
    assert ACCOUNT not in result.stdout + result.stderr
    assert AUTHORIZATION not in result.stdout + result.stderr


def test_v530_wrapper_passes_real_child_failure_without_startup_injection(
    tmp_path: Path,
) -> None:
    plan = tmp_path / "plan.json"
    plan.write_text("{}", encoding="utf-8")
    capture = tmp_path / "args.json"
    env = _fake_python_env(tmp_path, capture)

    result = _invoke(_authorized_arguments(plan), env)

    assert result.returncode == 1
    assert not capture.exists()
    assert not Path(env["PYTHON_STDIN_CAPTURE"]).exists()
    assert not Path(env["PYTHON_STARTUP_MARKER"]).exists()
    combined = result.stdout + result.stderr
    assert KEY not in combined
    assert SECRET not in combined
    assert ACCOUNT not in combined
    assert AUTHORIZATION not in combined


def _grant_path(plan: Path) -> Path:
    return plan.with_name("granted authorization.txt")


def _authorized_arguments(plan: Path) -> list[str]:
    grant = _grant_path(plan)
    grant.write_text(AUTHORIZATION, encoding="utf-8")
    return [
        "-PaperMutationAuthorized",
        "-AllowNetwork",
        "-Plan",
        str(plan),
        "-GrantedAuthorizationPath",
        str(grant),
    ]


def _write_dormant_plan(path: Path) -> None:
    path.write_bytes(
        canonical_json_bytes(
            build_dormant_lifecycle_plan(
                datetime(2026, 8, 13, tzinfo=UTC)
            )
        )
    )


def _copy_test_wrapper(
    fixture_repo: Path,
    operator_root: Path,
) -> Path:
    scripts = fixture_repo / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    escaped_root = str(operator_root).replace("'", "''")
    source = SCRIPT.read_text(encoding="utf-8")
    assert source.count(OPERATOR_ROOT_BLOCK) == 1
    source = source.replace(
        OPERATOR_ROOT_BLOCK,
        f"$OperatorGrantRoot = '{escaped_root}'",
    )
    wrapper = scripts / SCRIPT.name
    wrapper.write_text(source, encoding="utf-8")
    return wrapper


def _invoke(
    arguments: list[str],
    env: dict[str, str],
    *,
    script: Path | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    if script is None and "-GrantedAuthorizationPath" in arguments:
        index = arguments.index("-GrantedAuthorizationPath") + 1
        operator_root = Path(arguments[index]).parent
        fixture_repo = operator_root / "wrapper-fixture-repo"
        script = _copy_test_wrapper(fixture_repo, operator_root)
        cwd = fixture_repo
    if script is None:
        script = SCRIPT
    if cwd is None:
        cwd = PROJECT_ROOT
    return subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            *arguments,
        ],
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=30,
    )


def _fake_python_env(
    tmp_path: Path,
    capture: Path,
) -> dict[str, str]:
    module_dir = tmp_path / "algotrader" / "execution"
    module_dir.mkdir(parents=True)
    (module_dir.parent / "__init__.py").write_text("", encoding="utf-8")
    (module_dir / "__init__.py").write_text("", encoding="utf-8")
    module = module_dir / (
        "crypto_tournament_v2_bounded_paper_probe_lifecycle_operator.py"
    )
    module.write_text(
        "import json, os, pathlib, sys\n"
        "args = getattr(sys, 'orig_argv', sys.argv)[1:]\n"
        "pathlib.Path(os.environ['PYTHON_ARG_CAPTURE']).write_text("
        "json.dumps(args), encoding='utf-8')\n"
        "pathlib.Path(os.environ['PYTHON_STDIN_CAPTURE']).write_bytes("
        "sys.stdin.buffer.read())\n"
        "print('{\"paper_submit_performed\":false}')\n"
        "raise SystemExit(int(os.environ.get('FAKE_PYTHON_EXIT', '0')))\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        f"{tmp_path}{os.pathsep}{env.get('PYTHONPATH', '')}"
    )
    env["PYTHON_ARG_CAPTURE"] = str(capture)
    env["PYTHON_STDIN_CAPTURE"] = str(
        capture.with_name("authorization-stdin.txt")
    )
    startup_marker = capture.with_name("python-startup-marker.txt")
    (tmp_path / "sitecustomize.py").write_text(
        "import os, pathlib\n"
        "pathlib.Path(os.environ['PYTHON_STARTUP_MARKER']).write_text("
        "'executed', encoding='utf-8')\n",
        encoding="utf-8",
    )
    env["PYTHON_STARTUP_MARKER"] = str(startup_marker)
    env["APP_PROFILE"] = "paper"
    env["ALPACA_API_KEY"] = KEY
    env["ALPACA_SECRET_KEY"] = SECRET
    env["ALPACA_EXPECTED_PAPER_ACCOUNT_ID"] = ACCOUNT
    env["ALPACA_PAPER_BASE_URL"] = "https://paper-api.alpaca.markets"
    for name in (
        "ALPACA_BASE_URL",
        "APCA_API_BASE_URL",
        "ALGO_TRADER_ALLOW_NETWORK_TESTS",
        "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
        "PYTEST_NETWORK",
        "NETWORK_TESTS",
        "ALLOW_NETWORK_TESTS",
        "PYTEST_ADDOPTS",
    ):
        env.pop(name, None)
    return env


def _powershell() -> str:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        pytest.skip("PowerShell is required to verify the V5.30 wrapper.")
    return executable
