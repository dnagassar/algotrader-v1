from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE = PROJECT_ROOT / "scripts" / (
    "run_crypto_tournament_v2_capability_pipeline.ps1"
)
REPLAY = PROJECT_ROOT / "scripts" / (
    "replay_crypto_tournament_v2_bounded_paper_probe_review.ps1"
)
FINGERPRINT = "a" * 64


def test_pipeline_script_is_offline_no_submit_and_no_authority() -> None:
    source = PIPELINE.read_text(encoding="utf-8")

    for fragment in (
        "credential-free, network-free, broker-free, no-submit",
        "crypto_tournament_v2_capability_pipeline_offline=true",
        "credential_values_exposed=false",
        "network_access_attempted=false",
        "broker_read_occurred=false",
        "broker_mutation_occurred=false",
        "paper_mutation_authorized=false",
        "capital_allocation_authorized=false",
        "live_authorized=false",
        "crypto_bounded_probe_safety_certification",
        "crypto_tournament_v2_bounded_paper_probe_capability_producer",
    ):
        assert fragment in source
    for forbidden in (
        "[switch]$AllowNetwork",
        "[switch]$Submit",
        "--allow-network",
        "--submit",
        "--cancel",
        "--replace",
        "--liquidate",
    ):
        assert forbidden not in source


def test_pipeline_forwards_only_local_offline_arguments(tmp_path: Path) -> None:
    capture = tmp_path / "args.txt"
    env = _fake_python_env(tmp_path, capture)
    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PIPELINE),
            "-ShadowRoot",
            "shadow",
            "-CapabilityRoot",
            "capabilities",
            "-SafetyReceiptPath",
            "receipt.json",
            "-AsOf",
            "2026-08-20T00:00:00+00:00",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "capability_pipeline_offline=true" in result.stdout
    args = capture.read_text(encoding="utf-8")
    assert (
        "-m algotrader.execution."
        "crypto_bounded_probe_safety_certification"
    ) in args
    assert (
        "-m algotrader.orchestration."
        "crypto_tournament_v2_bounded_paper_probe_capability_producer"
    ) in args
    assert "--shadow-root shadow" in args
    assert "--output-root capabilities" in args
    assert "--safety-certification-receipt-path receipt.json" in args
    assert "--as-of 2026-08-20T00:00:00+00:00" in args
    assert "--allow-network" not in args


@pytest.mark.parametrize(
    ("name", "value", "message", "sensitive"),
    (
        (
            "APP_PROFILE",
            " PaPeR ",
            "APP_PROFILE=paper or live is not allowed",
            False,
        ),
        (
            "ALPACA_API_SECRET_KEY",
            "loaded-but-never-printed",
            "requires a credential-free process",
            True,
        ),
        (
            "ALLOW_NETWORK_TESTS",
            "enabled",
            "rejects network-test flags",
            False,
        ),
    ),
)
def test_pipeline_rejects_nonoffline_process_before_python(
    tmp_path: Path,
    name: str,
    value: str,
    message: str,
    sensitive: bool,
) -> None:
    capture = tmp_path / "args.txt"
    env = _fake_python_env(tmp_path, capture)
    env[name] = value
    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PIPELINE),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert message in result.stdout + result.stderr
    assert not capture.exists()
    if sensitive:
        assert value not in result.stdout + result.stderr


def test_replay_script_requires_and_forwards_exact_fingerprint(
    tmp_path: Path,
) -> None:
    capture = tmp_path / "args.txt"
    env = _fake_python_env(tmp_path, capture)
    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPLAY),
            "-ExpectedPublicationFingerprint",
            FINGERPRINT,
            "-ReviewRoot",
            "review",
            "-TrustedCurrentUtc",
            "2026-08-20T00:00:00+00:00",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "review_replay_offline=true" in result.stdout
    args = capture.read_text(encoding="utf-8")
    assert (
        "-m algotrader.certification."
        "crypto_tournament_v2_bounded_paper_probe_generation_replay"
    ) in args
    assert f"--expected-publication-fingerprint {FINGERPRINT}" in args
    assert "--review-root review" in args
    assert "--trusted-current-utc 2026-08-20T00:00:00+00:00" in args


@pytest.mark.parametrize(
    ("name", "value", "message", "sensitive"),
    (
        (
            "APP_PROFILE",
            " live ",
            "APP_PROFILE=paper or live is not allowed",
            False,
        ),
        (
            "APCA_API_KEY_ID",
            "loaded-but-never-printed",
            "requires a credential-free process",
            True,
        ),
        (
            "NETWORK_TESTS",
            "enabled",
            "rejects network-test flags",
            False,
        ),
        (
            "ALPACA_BASE_URL",
            "https://api.alpaca.markets",
            "rejects live endpoint indicators",
            False,
        ),
    ),
)
def test_replay_rejects_nonoffline_process_before_python(
    tmp_path: Path,
    name: str,
    value: str,
    message: str,
    sensitive: bool,
) -> None:
    capture = tmp_path / "args.txt"
    env = _fake_python_env(tmp_path, capture)
    env[name] = value
    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPLAY),
            "-ExpectedPublicationFingerprint",
            FINGERPRINT,
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert message in result.stdout + result.stderr
    assert not capture.exists()
    if sensitive:
        assert value not in result.stdout + result.stderr


def _fake_python_env(tmp_path: Path, capture: Path) -> dict[str, str]:
    fake_python = tmp_path / "python.cmd"
    fake_python.write_text(
        "@echo off\r\n"
        ">> \"%PYTHON_ARG_CAPTURE%\" echo %*\r\n"
        "echo {\"classification\":\"waiting\"}\r\n"
        "exit /B 0\r\n",
        encoding="utf-8",
        newline="",
    )
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}{os.pathsep}{env.get('PATH', '')}"
    env["PYTHON_ARG_CAPTURE"] = str(capture)
    env["APP_PROFILE"] = "dev"
    for name in (
        "ALPACA_API_KEY",
        "ALPACA_API_KEY_ID",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "APCA_API_BASE_URL",
        "ALPACA_BASE_URL",
        "ALPACA_PAPER_BASE_URL",
        "PYTEST_NETWORK",
        "NETWORK_TESTS",
        "ALLOW_NETWORK_TESTS",
        "ALGO_TRADER_ALLOW_NETWORK_TESTS",
        "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
    ):
        env.pop(name, None)
    return env


def _powershell() -> str:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        pytest.skip("PowerShell is required for wrapper verification")
    return executable



def test_target_pipeline_forwards_only_pinned_local_evidence(
    tmp_path: Path,
) -> None:
    capture = tmp_path / "target-args.txt"
    env = _fake_python_env(tmp_path, capture)
    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PIPELINE),
            "-InputFamily",
            "target",
            "-ShadowRoot",
            "shadow",
            "-CapabilityRoot",
            "capabilities",
            "-SafetyReceiptPath",
            "safety.json",
            "-TargetTerminalEvidencePath",
            "terminal-evidence.json",
            "-TargetLifecyclePlanPath",
            "lifecycle-plan.json",
            "-TargetLifecycleReceiptPath",
            "lifecycle-receipt.json",
            "-TargetLifecycleManifestPath",
            "lifecycle-manifest.json",
            "-IndependentFlatReconciliationPath",
            "flat-receipt.json",
            "-IndependentFlatStatusPath",
            "flat-status.json",
            "-IndependentFlatManifestPath",
            "flat-manifest.json",
            "-AsOf",
            "2026-08-20T00:01:00+00:00",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    lines = capture.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    args = lines[0]
    assert (
        "-m algotrader.orchestration."
        "crypto_tournament_v2_bounded_paper_probe_capability_producer_v530"
    ) in args
    assert "crypto_bounded_probe_safety_certification" not in args
    expected = (
        "--target-terminal-evidence-path terminal-evidence.json",
        "--target-lifecycle-plan-path lifecycle-plan.json",
        "--target-lifecycle-receipt-path lifecycle-receipt.json",
        "--target-lifecycle-manifest-path lifecycle-manifest.json",
        "--independent-flat-reconciliation-path flat-receipt.json",
        "--independent-flat-status-path flat-status.json",
        "--independent-flat-manifest-path flat-manifest.json",
    )
    for fragment in expected:
        assert args.count(fragment) == 1
    for forbidden in (
        "bounded_paper_probe_lifecycle_operator",
        "independent_flat_operator",
        "--paper-mutation-authorized",
        "--allow-network",
        "--submit",
        "--cancel",
        "--replace",
        "--close",
        "--liquidate",
    ):
        assert forbidden not in args


def test_legacy_pipeline_rejects_explicit_target_paths_before_python(
    tmp_path: Path,
) -> None:
    capture = tmp_path / "legacy-target-args.txt"
    env = _fake_python_env(tmp_path, capture)
    result = subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PIPELINE),
            "-TargetLifecyclePlanPath",
            "must-not-forward.json",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "-InputFamily target" in result.stdout + result.stderr
    assert not capture.exists()
