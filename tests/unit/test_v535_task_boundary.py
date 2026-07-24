from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET

from algotrader.execution.v535_unattended_readonly import (
    V535_TASK_ARGUMENTS,
    V535_TASK_EXECUTE,
    V535_TASK_IDENTITY,
    main,
    query_windows_task_snapshot,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPER = REPO_ROOT / "scripts" / "run_v535_unattended_readonly.ps1"
TASK_XML = REPO_ROOT / "docs" / "design" / "crypto_tournament_v2_oos_scheduler_task.xml"
MODULE = REPO_ROOT / "src" / "algotrader" / "execution" / "v535_unattended_readonly.py"


def test_task_definition_is_disabled_and_action_matches_runtime_contract() -> None:
    root = ET.parse(TASK_XML).getroot()
    namespace = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
    assert root.findtext("t:RegistrationInfo/t:URI", namespaces=namespace) == V535_TASK_IDENTITY
    assert root.findtext("t:Settings/t:Enabled", namespaces=namespace) == "false"
    assert root.findtext("t:Settings/t:AllowStartOnDemand", namespaces=namespace) == "false"
    assert root.findtext("t:Triggers/t:TimeTrigger/t:Enabled", namespaces=namespace) == "false"
    assert root.findtext("t:Actions/t:Exec/t:Command", namespaces=namespace) == V535_TASK_EXECUTE
    assert root.findtext("t:Actions/t:Exec/t:Arguments", namespaces=namespace) == V535_TASK_ARGUMENTS
    assert root.findtext("t:Settings/t:MultipleInstancesPolicy", namespaces=namespace) == "IgnoreNew"


def test_wrapper_uses_only_non_secret_references_and_never_registers_or_enables() -> None:
    text = WRAPPER.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "wincred:algotrader/v5.35/alpaca-market-data/production" in text
    assert "wincred:algotrader/v5.35/alpaca-paper-observation/production" in text
    assert "--credential-provider" in text
    assert "windows-credential-manager" in text
    assert "--paper-endpoint" in text
    assert "https://paper-api.alpaca.markets" in text
    assert "--market-data-endpoint" in text
    assert "https://data.alpaca.markets" in text
    assert "register-scheduledtask" not in lowered
    assert "enable-scheduledtask" not in lowered
    assert "start-scheduledtask" not in lowered
    assert "convertto-securestring" not in lowered
    assert "get-content" not in lowered
    assert ".env" not in lowered
    assert "alpaca_api_key=" not in lowered
    assert "alpaca_secret_key=" not in lowered


def test_production_module_has_no_broker_mutation_call_surface() -> None:
    text = MODULE.read_text(encoding="utf-8")
    for call in (
        ".submit_order(",
        ".cancel_order(",
        ".replace_order(",
        ".close_position(",
        ".close_all_positions(",
        ".liquidate(",
        "PreviewDispatcher",
    ):
        assert call not in text


def test_task_query_is_one_read_only_process_and_returns_typed_snapshot() -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def runner(argv: list[str], **kwargs: object) -> object:
        calls.append((argv, kwargs))
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "state": "Ready",
                    "enabled": True,
                    "action_execute": V535_TASK_EXECUTE,
                    "action_arguments": V535_TASK_ARGUMENTS,
                    "last_task_result": 0,
                    "last_run_time": "2026-07-20T01:05:00Z",
                }
            ),
            stderr="",
        )

    snapshot = query_windows_task_snapshot(
        runner=runner,
        clock=lambda: datetime(2026, 7, 20, 1, 6, tzinfo=UTC),
    )
    assert snapshot.task_identity == V535_TASK_IDENTITY
    assert snapshot.action_arguments == V535_TASK_ARGUMENTS
    assert snapshot.last_task_result == 0
    assert len(calls) == 1
    argv, kwargs = calls[0]
    assert argv[:3] == ["powershell.exe", "-NoProfile", "-NonInteractive"]
    command = argv[-1].lower()
    assert "get-scheduledtask" in command
    assert "get-scheduledtaskinfo" in command
    assert "register-scheduledtask" not in command
    assert "enable-scheduledtask" not in command
    assert kwargs["timeout"] == 30


def test_cli_defaults_fail_before_store_or_task_access(
    tmp_path: Path,
    capsys,
) -> None:
    output_root = tmp_path / "must_not_exist"
    exit_code = main(["--output-root", str(output_root)])
    assert exit_code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"classification": "read_only_authorization_incomplete"}
    assert not output_root.exists()
