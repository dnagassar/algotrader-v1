"""Unit tests for crypto_readiness_replay command and CLI dispatch."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

import pytest

from algotrader.cli import build_parser, main as cli_main
from algotrader.execution.crypto_readiness_replay import (
    COMMAND_NAME,
    MILESTONE_NAME,
    run_crypto_readiness_replay,
)
from algotrader.execution.crypto_supervised_readiness_trial_core import (
    OFFLINE_PAPER_ENVIRONMENT,
    _json_safe,
    run_crypto_supervised_readiness_trial,
    validate_crypto_supervised_readiness_trial,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
PROTECTED_LAUNCHER_ENV_KEYS = {
    "APP_PROFILE",
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
    "ALPACA_BASE_URL",
    "ALPACA_PAPER_BASE_URL",
    "APCA_API_BASE_URL",
    "ALGO_TRADER_ALLOW_NETWORK_TESTS",
    "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
}


def _contains_decimal(value: object) -> bool:
    if isinstance(value, Decimal):
        return True
    if isinstance(value, Mapping):
        return any(_contains_decimal(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return any(_contains_decimal(item) for item in value)
    return False


def test_run_crypto_readiness_replay_returns_accepted(tmp_path: Path) -> None:
    output_root = tmp_path / "replay_output"
    packet = run_crypto_readiness_replay(
        output_root=output_root,
        cycle_count=8,
        write_artifacts=True,
    )
    assert packet["trial_classification"] == "accepted"
    assert packet["milestone_name"] == "V5.32 End-to-End Supervised Crypto Readiness Trial"
    assert packet["safety"]["app_profile_paper"] is False
    assert packet["safety"]["app_profile_live"] is False
    assert packet["safety"]["credentials_present"] is False
    assert packet["safety"]["network_used"] is False
    assert packet["safety"]["broker_read_occurred"] is False
    assert _contains_decimal(packet)
    assert (output_root / "readiness_packet.json").is_file()


def test_run_crypto_readiness_replay_matches_direct_core(tmp_path: Path) -> None:
    output_root = tmp_path / "equivalent_replay"
    decision_start = datetime(2026, 7, 19, 12, 0, tzinfo=UTC)
    replay_packet = run_crypto_readiness_replay(
        output_root=output_root,
        decision_start=decision_start,
        cycle_count=8,
        write_artifacts=False,
    )
    direct_packet = run_crypto_supervised_readiness_trial(
        output_root=output_root,
        decision_start=decision_start,
        cycle_count=8,
        broker_observed_readiness=False,
        allow_alpaca_paper_read=False,
        write_artifacts=False,
        receipt_root=None,
        paper_environment=OFFLINE_PAPER_ENVIRONMENT,
    )
    assert _json_safe(replay_packet) == _json_safe(direct_packet)


def test_exact_allowlist_argv_parses_to_frozen_defaults() -> None:
    args = build_parser().parse_args(["crypto-readiness-replay"])
    assert args.command == "crypto-readiness-replay"
    assert Path(args.output_root) == Path(
        "runs/crypto_supervised_readiness_trial/latest"
    )
    assert args.decision_start == "2026-07-19T12:00:00+00:00"
    assert args.cycle_count == 24
    assert args.format == "text"


def test_exact_allowlist_dispatch_forwards_frozen_defaults(
    capsys: pytest.CaptureFixture[str],
) -> None:
    packet = {
        "trial_classification": "accepted",
        "current_readiness_rung_code": "R1",
        "cycle_count": 24,
        "receipt_chain": {"final_receipt_hash": "abc"},
    }
    with patch(
        "algotrader.execution.crypto_readiness_replay."
        "run_crypto_readiness_replay",
        return_value=packet,
    ) as replay:
        exit_code = cli_main(["crypto-readiness-replay"])
    assert exit_code == 0
    replay.assert_called_once_with(
        output_root=Path("runs/crypto_supervised_readiness_trial/latest"),
        decision_start="2026-07-19T12:00:00+00:00",
        cycle_count=24,
        write_artifacts=True,
    )
    assert "v5_47_trial_classification=accepted" in capsys.readouterr().out


@pytest.mark.parametrize(
    "profile_option",
    [
        ("--profile", "dev"),
        ("--profile", "paper"),
        ("--profile", "live"),
        ("--profile=dev",),
        ("--profile=paper",),
        ("--profile=live",),
    ],
)
def test_explicit_root_profile_is_rejected_before_replay_dispatch(
    profile_option: tuple[str, ...],
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch(
        "algotrader.execution.crypto_readiness_replay."
        "run_crypto_readiness_replay",
    ) as replay:
        exit_code = cli_main([*profile_option, "crypto-readiness-replay"])
    assert exit_code == 2
    replay.assert_not_called()
    assert "explicit_profile_option_not_permitted" in capsys.readouterr().err


def test_central_cli_dispatch_forwards_exact_replay_arguments(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_root = tmp_path / "forwarded"
    packet = {
        "trial_classification": "accepted",
        "current_readiness_rung_code": "R1",
        "cycle_count": 9,
        "receipt_chain": {"final_receipt_hash": "abc"},
        "decimal_probe": Decimal("1.25"),
    }
    with patch(
        "algotrader.execution.crypto_readiness_replay."
        "run_crypto_readiness_replay",
        return_value=packet,
    ) as replay:
        exit_code = cli_main(
            [
                "crypto-readiness-replay",
                "--output-root",
                str(output_root),
                "--decision-start",
                "2026-07-20T00:00:00+00:00",
                "--cycle-count",
                "9",
                "--format",
                "json",
            ]
        )
    assert exit_code == 0
    replay.assert_called_once_with(
        output_root=output_root,
        decision_start="2026-07-20T00:00:00+00:00",
        cycle_count=9,
        write_artifacts=True,
    )
    assert json.loads(capsys.readouterr().out)["decimal_probe"] == "1.25"


def test_central_cli_replay_fails_closed_with_exit_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    packet = {
        "trial_classification": "failed_closed",
        "current_readiness_rung_code": "R1",
        "cycle_count": 8,
        "receipt_chain": {"final_receipt_hash": ""},
    }
    with patch(
        "algotrader.execution.crypto_readiness_replay."
        "run_crypto_readiness_replay",
        return_value=packet,
    ):
        exit_code = cli_main(
            [
                "crypto-readiness-replay",
                "--output-root",
                str(tmp_path / "blocked"),
                "--format",
                "text",
            ]
        )
    assert exit_code == 2
    assert (
        "v5_47_trial_classification=failed_closed"
        in capsys.readouterr().out
    )


def test_cli_crypto_readiness_replay_text_format(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output_root = tmp_path / "cli_text_output"
    exit_code = cli_main([
        "crypto-readiness-replay",
        "--output-root", str(output_root),
        "--cycle-count", "8",
        "--format", "text",
    ])
    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "v5_47_trial_classification=accepted" in captured
    assert "v5_47_current_readiness_rung=R1" in captured
    assert "v5_47_cycle_count=8" in captured
    assert "v5_47_receipt_chain_hash=" in captured
    assert "v5_47_paper_submit_performed=false" in captured
    assert "v5_47_broker_mutation_performed=false" in captured
    assert "v5_47_live_authorized=false" in captured


def test_cli_crypto_readiness_replay_json_format(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output_root = tmp_path / "cli_json_output"
    exit_code = cli_main([
        "crypto-readiness-replay",
        "--output-root", str(output_root),
        "--cycle-count", "8",
        "--format", "json",
    ])
    assert exit_code == 0
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["trial_classification"] == "accepted"
    assert data["cycle_count"] == 8


def test_cli_crypto_readiness_replay_no_broker_flags_on_parser() -> None:
    parser = build_parser()
    forbidden_options = (
        ("--broker-observed-readiness",),
        ("--receipt-root", "foo"),
        ("--allow-alpaca-paper-read",),
        ("--alpaca-api-key", "secret"),
        ("--api-key", "secret"),
        ("--credential", "secret"),
        ("--allow-network",),
        ("--paper",),
        ("--live",),
    )
    for option in forbidden_options:
        with pytest.raises(SystemExit):
            parser.parse_args(["crypto-readiness-replay", *option])


def test_exact_central_launcher_is_protected_and_import_pure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    isolated_root = tmp_path / "isolated-repository"
    shutil.copytree(
        REPO_ROOT / "src",
        isolated_root / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    (isolated_root / ".git").mkdir()
    harness = tmp_path / "launcher-harness"
    harness.mkdir()
    audit_path = harness / "audit.json"
    protected = sorted(PROTECTED_LAUNCHER_ENV_KEYS)
    sitecustomize = f"""
import atexit
import json
import os
from pathlib import Path
import sys

PROTECTED = set({protected!r})
VIOLATIONS = []

def _name(value):
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return str(value)

def _guard(value):
    name = _name(value)
    if name in PROTECTED:
        VIOLATIONS.append(name)
        raise RuntimeError("protected environment access: " + name)

class RaisingEnvironment(dict):
    def __getitem__(self, key):
        _guard(key)
        return super().__getitem__(key)
    def get(self, key, default=None):
        _guard(key)
        return super().get(key, default)
    def __contains__(self, key):
        _guard(key)
        return super().__contains__(key)
    def __iter__(self):
        for key in super().__iter__():
            _guard(key)
            yield key

os.environ._data = RaisingEnvironment(os.environ._data)

def _write_audit():
    Path(os.environ["V548_LAUNCHER_AUDIT_PATH"]).write_text(
        json.dumps({{
            "modules": sorted(sys.modules),
            "protected_environment_accesses": VIOLATIONS,
        }}),
        encoding="utf-8",
    )

atexit.register(_write_audit)
"""
    (harness / "sitecustomize.py").write_text(sitecustomize, encoding="utf-8")

    child_env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() not in PROTECTED_LAUNCHER_ENV_KEYS
    }
    child_env["PYTHONPATH"] = os.pathsep.join(
        (str(harness), str(isolated_root / "src"))
    )
    child_env["V548_LAUNCHER_AUDIT_PATH"] = str(audit_path)

    result = subprocess.run(
        [sys.executable, "-m", "algotrader.cli", "crypto-readiness-replay"],
        cwd=isolated_root,
        env=child_env,
        capture_output=True,
        text=True,
        check=False,
        timeout=240,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "v5_47_trial_classification=accepted",
        "v5_47_current_readiness_rung=R1",
        "v5_47_cycle_count=24",
        next(
            line
            for line in result.stdout.splitlines()
            if line.startswith("v5_47_receipt_chain_hash=")
        ),
        "v5_47_paper_submit_performed=false",
        "v5_47_broker_mutation_performed=false",
        "v5_47_live_authorized=false",
    ]

    output_root = (
        isolated_root
        / "runs"
        / "crypto_supervised_readiness_trial"
        / "latest"
    )
    packet = json.loads(
        (output_root / "readiness_packet.json").read_text(encoding="utf-8")
    )
    assert packet["trial_classification"] == "accepted"
    monkeypatch.chdir(isolated_root)
    assert (
        validate_crypto_supervised_readiness_trial(output_root)[
            "validation_status"
        ]
        == "passed"
    )

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["protected_environment_accesses"] == []
    loaded = set(audit["modules"])
    forbidden_modules = {
        "algotrader.config",
        "algotrader.execution.alpaca_sdk_client",
        "algotrader.execution.alpaca_client",
        "algotrader.execution.alpaca_broker",
        "algotrader.execution.alpaca_adapter",
        "algotrader.execution.alpaca_mapper",
        "algotrader.execution.alpaca_translator",
        "algotrader.execution.live_capital_interlock",
        "algotrader.execution.secure_credential_provider",
        "algotrader.execution.v536_credential_provisioning",
        "algotrader.execution.crypto_read_only_paper_observation_adapter",
        "algotrader.execution.tomorrow_crypto_trader_demo_broker_client_adapter",
        "algotrader.execution.tomorrow_crypto_trader_demo_cli",
        "algotrader.execution.read_only_paper_broker_snapshot_reconciliation",
        "algotrader.execution.read_only_paper_broker_snapshot_operator_review",
        "algotrader.orchestration.etf_sma_paper_broker_preview",
        "openai",
        "anthropic",
        "langchain",
        "langgraph",
    }
    assert loaded.isdisjoint(forbidden_modules)
