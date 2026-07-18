from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    PROJECT_ROOT
    / "scripts"
    / "build_exact_paper_cancellation_reconciliation_readiness.py"
)


def test_readiness_script_is_dedicated_and_has_no_active_surface() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "paper_cancellation_reconciliation_readiness" in source
    assert "algotrader.cli" not in source
    for forbidden in (
        "alpaca",
        "cancel_order",
        "close_position",
        "liquidate",
        "replace_order",
        "submit_order",
    ):
        assert forbidden not in source


def test_readiness_script_defaults_to_pre_artifact_offline_block(
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
    assert payload["status"] == "blocked"
    assert payload["blocker"] == "offline_readiness_not_permitted"
    assert payload["authorization_artifact_loaded"] is False
    assert payload["journal_path_checked"] is False
    assert payload["environment_read"] is False
    assert payload["credentials_accessed"] is False
    assert payload["network_accessed"] is False
    assert payload["broker_read_performed"] is False
    assert not (tmp_path / "missing-journal.sqlite3").exists()
