from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "run_exact_paper_cancellation_reconciliation.py"


def test_standalone_script_is_dedicated_to_the_read_only_command() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "paper_cancellation_reconciliation_command" in source
    assert "algotrader.cli" not in source
    for forbidden in (
        "cancel_order",
        "close_position",
        "liquidate",
        "replace_order",
        "submit_order",
    ):
        assert forbidden not in source


def test_standalone_script_defaults_to_pre_artifact_offline_block(
    tmp_path: Path,
) -> None:
    credential_names = (
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
    )
    env = os.environ.copy()
    env["APP_PROFILE"] = "dev"
    for name in credential_names:
        env.pop(name, None)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--authorization-artifact",
            str(tmp_path / "missing-authorization.json"),
            "--journal-path",
            str(tmp_path / "missing-journal.sqlite3"),
            "--cancel-intent-id",
            "cancel-intent-1",
            "--client-order-id",
            "client-order-1",
            "--broker-order-id",
            "broker-order-1",
            "--expected-authorization-id",
            "authorization-1",
            "--expected-paper-account-id",
            "expected-account-1",
            "--occurred-at",
            datetime(2026, 7, 14, 14, 0, tzinfo=UTC).isoformat(),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 2, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "blocked_before_operator"
    assert payload["blocker"] == "operator_binding_not_permitted"
    assert payload["authorization_artifact_loaded"] is False
    assert payload["paper_configuration_loaded"] is False
    assert payload["process_environment_read"] is False
    assert payload["operator_invoked"] is False
    assert not (tmp_path / "missing-journal.sqlite3").exists()
