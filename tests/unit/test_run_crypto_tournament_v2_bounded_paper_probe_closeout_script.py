from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / (
    "run_crypto_tournament_v2_bounded_paper_probe_closeout.ps1"
)
KEY = "closeout-paper-key-never-print"
SECRET = "closeout-paper-secret-never-print"
ACCOUNT = "closeout-paper-account-never-print"
FINGERPRINT = "a" * 64
SENSITIVE_NAMES = (
    "APP_PROFILE",
    "ALPACA_API_KEY",
    "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
    "ALPACA_EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_PAPER_ACCOUNT_ID",
    "APCA_EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_BASE_URL",
    "ALPACA_PAPER_BASE_URL",
    "APCA_API_BASE_URL",
    "PYTEST_NETWORK",
    "NETWORK_TESTS",
    "ALLOW_NETWORK_TESTS",
    "ALGO_TRADER_ALLOW_NETWORK_TESTS",
    "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
    "PYTEST_ADDOPTS",
    "PYTHONPATH",
    "PYTHONHOME",
    "PYTHONSTARTUP",
    "PYTHONINSPECT",
    "PYTHONUSERBASE",
    "PYTHONBREAKPOINT",
    "PYTHONPYCACHEPREFIX",
)


def test_closeout_shell_is_post_exit_read_then_offline_only() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    parameter_block = script.split("Set-StrictMode", maxsplit=1)[0]

    for required in (
        "run_crypto_bounded_probe_independent_flat_operator.ps1",
        "run_crypto_tournament_v2_capability_pipeline.ps1",
        "run_crypto_tournament_v2_bounded_paper_probe_review.ps1",
        "replay_crypto_tournament_v2_bounded_paper_probe_review.ps1",
        "SetEnvironmentVariable($Name, $null, \"Process\")",
            "publication_fingerprint",
            "v530_closeout_complete=true",
            "GetCurrentProcess().MainModule.FileName",
        ):
        assert required in script
    for forbidden in (
        "run_crypto_tournament_v2_bounded_paper_probe_lifecycle.ps1",
        "build_crypto_tournament_v2_bounded_paper_probe_lifecycle_plan.ps1",
        "PaperMutationAuthorized",
        "GrantedAuthorizationPath",
        "ExactOperationAuthorization",
        "[string]$AsOf",
        "[string]$TrustedCurrentUtc",
        "[string]$ExpectedPublicationFingerprint",
        "[string]$ExpectedPaperAccountId",
    ):
        assert forbidden not in parameter_block
    assert "Start-Process" not in script
    for forbidden_launch in (
        "Get-Command pwsh",
        "Get-Command powershell",
        "& python",
        "python.exe",
    ):
        assert forbidden_launch not in script


def test_closeout_happy_path_scrubs_before_offline_children(
    tmp_path: Path,
) -> None:
    calls = tmp_path / "calls.jsonl"
    env = _fake_child_powershell_env(tmp_path, calls)
    paths = _paths(tmp_path)
    _write_lifecycle_quartet(paths["lifecycle"])
    arguments = _arguments(paths)

    result = _invoke(arguments, env)

    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    records = _read_calls(calls)
    assert [record["script"] for record in records] == [
        "run_crypto_bounded_probe_independent_flat_operator.ps1",
        "run_crypto_tournament_v2_capability_pipeline.ps1",
        "run_crypto_tournament_v2_bounded_paper_probe_review.ps1",
        "replay_crypto_tournament_v2_bounded_paper_probe_review.ps1",
    ]
    assert records[0]["sensitive_loaded"] is True
    assert all(
        record["sensitive_loaded"] is False
        for record in records[1:]
    )
    flat_args = records[0]["args"]
    assert flat_args[flat_args.index("-TargetSymbol") + 1] == "BTCUSD"
    assert "-IndependentFlatReadAuthorized" in flat_args
    assert "-AllowNetwork" in flat_args
    pipeline_args = records[1]["args"]
    assert pipeline_args[pipeline_args.index("-InputFamily") + 1] == "target"
    assert (
        pipeline_args[
            pipeline_args.index("-TargetTerminalEvidencePath") + 1
        ]
        == str(paths["lifecycle"] / "latest" / "terminal_evidence.json")
    )
    replay_args = records[3]["args"]
    assert (
        replay_args[
            replay_args.index("-ExpectedPublicationFingerprint") + 1
        ]
        == FINGERPRINT
    )
    assert "v530_closeout_complete=true" in combined
    assert not Path(env["PATH_HIJACK_MARKER"]).exists()
    for value in (KEY, SECRET, ACCOUNT):
        assert value not in combined
        assert all(
            value not in json.dumps(record)
            for record in records
        )


@pytest.mark.parametrize(
    ("stage", "expected_calls"),
    (
        ("flat", 1),
        ("pipeline", 2),
        ("review", 3),
        ("replay", 4),
    ),
)
def test_closeout_propagates_stage_failure_and_stops(
    tmp_path: Path,
    stage: str,
    expected_calls: int,
) -> None:
    calls = tmp_path / "calls.jsonl"
    env = _fake_child_powershell_env(tmp_path, calls)
    env["FAKE_FAIL_STAGE"] = stage
    env["FAKE_FAIL_CODE"] = "7"
    paths = _paths(tmp_path)
    _write_lifecycle_quartet(paths["lifecycle"])

    result = _invoke(_arguments(paths), env)

    assert result.returncode == 7, result.stdout + result.stderr
    assert len(_read_calls(calls)) == expected_calls
    assert "v530_closeout_complete=true" not in result.stdout


@pytest.mark.parametrize(
    "mode",
    ("missing", "malformed", "empty", "oversize"),
)
def test_closeout_rejects_missing_or_malformed_review_pointer(
    tmp_path: Path,
    mode: str,
) -> None:
    calls = tmp_path / "calls.jsonl"
    env = _fake_child_powershell_env(tmp_path, calls)
    env["FAKE_REVIEW_MANIFEST_MODE"] = mode
    paths = _paths(tmp_path)
    _write_lifecycle_quartet(paths["lifecycle"])

    result = _invoke(_arguments(paths), env)

    assert result.returncode == 2, result.stdout + result.stderr
    assert len(_read_calls(calls)) == 3
    assert "v530_closeout_failed_stage=review_manifest" in result.stdout


@pytest.mark.parametrize(
    "omission",
    ("read_switch", "network_switch", "lifecycle"),
)
def test_closeout_preflight_never_starts_child(
    tmp_path: Path,
    omission: str,
) -> None:
    calls = tmp_path / "calls.jsonl"
    env = _fake_child_powershell_env(tmp_path, calls)
    paths = _paths(tmp_path)
    _write_lifecycle_quartet(paths["lifecycle"])
    arguments = _arguments(paths)
    if omission == "read_switch":
        arguments.remove("-IndependentFlatReadAuthorized")
    elif omission == "network_switch":
        arguments.remove("-AllowNetwork")
    else:
        (paths["lifecycle"] / "latest" / "manifest.json").unlink()

    result = _invoke(arguments, env)

    assert result.returncode == 2, result.stdout + result.stderr
    assert not calls.exists()


def _paths(tmp_path: Path) -> dict[str, Path]:
    return {
        "shadow": tmp_path / "shadow",
        "lifecycle": tmp_path / "lifecycle",
        "flat": tmp_path / "flat",
        "capability": tmp_path / "capability",
        "review": tmp_path / "review",
    }


def _write_lifecycle_quartet(root: Path) -> None:
    latest = root / "latest"
    latest.mkdir(parents=True)
    for name in (
        "terminal_evidence.json",
        "lifecycle_plan.json",
        "lifecycle_result.json",
        "manifest.json",
    ):
        (latest / name).write_text("{}\n", encoding="utf-8")


def _arguments(paths: dict[str, Path]) -> list[str]:
    return [
        "-TargetSymbol",
        "BTCUSD",
        "-IndependentFlatReadAuthorized",
        "-AllowNetwork",
        "-ShadowRoot",
        str(paths["shadow"]),
        "-LifecycleRoot",
        str(paths["lifecycle"]),
        "-FlatRoot",
        str(paths["flat"]),
        "-CapabilityRoot",
        str(paths["capability"]),
        "-ReviewRoot",
        str(paths["review"]),
    ]


def _invoke(
    arguments: list[str],
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            env["CLOSEOUT_SCRIPT"],
            *arguments,
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=60,
    )


def _fake_child_powershell_env(
    tmp_path: Path,
    calls: Path,
) -> dict[str, str]:
    fake_scripts = tmp_path / "scripts"
    fake_scripts.mkdir()
    closeout_copy = fake_scripts / SCRIPT.name
    shutil.copy2(SCRIPT, closeout_copy)
    sensitive_literals = ", ".join(
        f'"{name}"' for name in SENSITIVE_NAMES
    )
    fake_child = (
        "param()\n"
        f"$SensitiveNames = @({sensitive_literals})\n"
        "$SensitiveLoaded = $false\n"
        "foreach ($Name in $SensitiveNames) {\n"
        "  if (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($Name, 'Process'))) {\n"
        "    $SensitiveLoaded = $true\n"
        "  }\n"
        "}\n"
        "$Script = $MyInvocation.MyCommand.Name\n"
        "$Stages = @{\n"
        "  'run_crypto_bounded_probe_independent_flat_operator.ps1' = 'flat'\n"
        "  'run_crypto_tournament_v2_capability_pipeline.ps1' = 'pipeline'\n"
        "  'run_crypto_tournament_v2_bounded_paper_probe_review.ps1' = 'review'\n"
        "  'replay_crypto_tournament_v2_bounded_paper_probe_review.ps1' = 'replay'\n"
        "}\n"
        "$Stage = $Stages[$Script]\n"
        "$Record = [ordered]@{\n"
        "  script = $Script\n"
        "  args = @($args)\n"
        "  sensitive_loaded = $SensitiveLoaded\n"
        "}\n"
        "$Record | ConvertTo-Json -Compress | Add-Content -LiteralPath $env:CLOSEOUT_CALLS -Encoding utf8\n"
        "if ($Stage -eq 'review' -and $env:FAKE_REVIEW_MANIFEST_MODE -ne 'missing') {\n"
        "  $ReviewRoot = $null\n"
        "  for ($Index = 0; $Index -lt $args.Count; $Index++) {\n"
        "    if ($args[$Index] -eq '-OutputRoot') {\n"
        "      $ReviewRoot = $args[$Index + 1]\n"
        "    }\n"
        "  }\n"
        "  New-Item -ItemType Directory -Path $ReviewRoot -Force | Out-Null\n"
        "  $ManifestPath = Join-Path $ReviewRoot 'latest_manifest.json'\n"
        "  if ($env:FAKE_REVIEW_MANIFEST_MODE -eq 'empty') {\n"
        "    Set-Content -LiteralPath $ManifestPath -Value '' -NoNewline\n"
        "  } elseif ($env:FAKE_REVIEW_MANIFEST_MODE -eq 'oversize') {\n"
        "    Set-Content -LiteralPath $ManifestPath -Value ('a' * 65537) -NoNewline\n"
        "  } else {\n"
        "    $Fingerprint = if ($env:FAKE_REVIEW_MANIFEST_MODE -eq 'malformed') { 'bad' } else { 'a' * 64 }\n"
        "    [ordered]@{publication_fingerprint = $Fingerprint} | ConvertTo-Json -Compress | Set-Content -LiteralPath $ManifestPath -Encoding utf8\n"
        "  }\n"
        "}\n"
        "if ($env:FAKE_FAIL_STAGE -eq $Stage) {\n"
        "  exit [int]$env:FAKE_FAIL_CODE\n"
        "}\n"
        "exit 0\n"
    )
    for name in (
        "run_crypto_bounded_probe_independent_flat_operator.ps1",
        "run_crypto_tournament_v2_capability_pipeline.ps1",
        "run_crypto_tournament_v2_bounded_paper_probe_review.ps1",
        "replay_crypto_tournament_v2_bounded_paper_probe_review.ps1",
    ):
        (fake_scripts / name).write_text(fake_child, encoding="utf-8")
    env = os.environ.copy()
    env["CLOSEOUT_SCRIPT"] = str(closeout_copy)
    env["CLOSEOUT_CALLS"] = str(calls)
    env["APP_PROFILE"] = "paper"
    env["ALPACA_API_KEY"] = KEY
    env["ALPACA_SECRET_KEY"] = SECRET
    env["ALPACA_EXPECTED_PAPER_ACCOUNT_ID"] = ACCOUNT
    env["ALPACA_PAPER_BASE_URL"] = "https://paper-api.alpaca.markets"
    env["PYTEST_ADDOPTS"] = "--allow-network"
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    marker = tmp_path / "path-hijack-marker.txt"
    (fake_bin / "pwsh.cmd").write_text(
        '@echo hijacked > "%PATH_HIJACK_MARKER%"\n',
        encoding="utf-8",
    )
    env["PATH_HIJACK_MARKER"] = str(marker)
    env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
    return env


def _read_calls(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]


def _powershell() -> str:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        pytest.skip("PowerShell is required to verify the closeout shell.")
    return executable
