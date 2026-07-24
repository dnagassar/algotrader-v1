from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import pytest

from algotrader.execution.v536_canary_authorization import (
    V536_AUTHORIZATION_SCHEMA,
    canonical_authorization_sha256,
    parse_v536_authorization,
)
from algotrader.execution.v536_windows_task import (
    V536TaskError,
    V536TaskSnapshot,
    WindowsTaskSchedulerAdapter,
    build_v536_task_spec,
    render_v536_task_xml,
    validate_v536_task_snapshot,
)


WINDOW_START = datetime(2026, 8, 1, 12, tzinfo=UTC)
SCHEDULED_START = WINDOW_START + timedelta(hours=1, minutes=5)
NAMESPACE = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}


def _authorization(
    root: Path,
    *,
    artifact_root: Path | None = None,
):  # type: ignore[no-untyped-def]
    wrapper = root / "scripts" / "run_v536_windows_host_canary.ps1"
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text("# safe test wrapper\n", encoding="utf-8")
    artifact = (
        root / "runs" / "v5_36" / "authorization.json"
        if artifact_root is None
        else artifact_root / "authorization.json"
    )
    artifact.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "schema_version": V536_AUTHORIZATION_SCHEMA,
        "authorization_id": "v536-task-test",
        "task_identity": "\\crypto-tournament-v2-oos-scheduler",
        "target_window_start_utc": WINDOW_START.isoformat(),
        "target_window_end_utc": (WINDOW_START + timedelta(hours=1)).isoformat(),
        "scheduled_start_utc": SCHEDULED_START.isoformat(),
        "automatic_disarm_deadline_utc": (
            SCHEDULED_START + timedelta(minutes=40)
        ).isoformat(),
        "windows_principal": "DOMAIN\\canary-user",
        "credential_vault_owner": "DOMAIN\\canary-user",
        "task_logon_type": "InteractiveToken",
        "deployment_root": str(root.resolve()),
        "source_commit_sha": "a" * 40,
        "source_tree_sha": "b" * 40,
        "credential_provider": "windows-credential-manager",
        "market_data_credential_reference": (
            "wincred:algotrader/v5.35/alpaca-market-data/production"
        ),
        "paper_credential_reference": (
            "wincred:algotrader/v5.35/alpaca-paper-observation/production"
        ),
        "market_data_endpoint": "https://data.alpaca.markets",
        "paper_endpoint": "https://paper-api.alpaca.markets",
        "credential_reads_authorized": True,
        "task_registration_authorized": True,
        "task_arming_authorized": True,
        "task_disarming_authorized": True,
        "market_data_read_authorized": True,
        "paper_observation_authorized": True,
        "allow_network": True,
        "paper_submit_authorized": False,
        "paper_cancel_authorized": False,
        "paper_replace_authorized": False,
        "paper_close_authorized": False,
        "paper_liquidation_authorized": False,
        "paper_mutation_authorized": False,
        "live_access_authorized": False,
        "retry_authorized": False,
        "additional_windows_authorized": False,
        "operator_approved": True,
        "canonical_authorization_sha256": "",
    }
    payload["canonical_authorization_sha256"] = canonical_authorization_sha256(
        payload
    )
    artifact.write_text(json.dumps(payload), encoding="utf-8")
    return parse_v536_authorization(payload, artifact_path=artifact.resolve())


def _snapshot(spec, *, phase: str) -> V536TaskSnapshot:  # type: ignore[no-untyped-def]
    values = {
        "task_identity": spec.task_identity,
        "principal": spec.principal,
        "logon_type": spec.logon_type,
        "run_level": "LeastPrivilege",
        "task_enabled": False,
        "trigger_enabled": False,
        "trigger_start": spec.trigger_start,
        "trigger_end": spec.trigger_end,
        "state": "Disabled",
        "action_execute": spec.action_execute,
        "action_arguments": spec.action_arguments,
        "working_directory": spec.working_directory,
        "allow_start_on_demand": False,
        "restart_on_failure": False,
        "multiple_instances_policy": spec.multiple_instances_policy,
        "execution_time_limit": spec.execution_time_limit,
        "last_task_result": 0,
        "last_run_time": None,
        "next_run_time": None,
        "observed_at": spec.trigger_start - timedelta(minutes=1),
    }
    if phase == "armed":
        values.update(
            task_enabled=True,
            trigger_enabled=True,
            state="Ready",
            next_run_time=spec.trigger_start,
        )
    elif phase == "running":
        values.update(
            task_enabled=True,
            trigger_enabled=True,
            state="Running",
            last_task_result=267009,
            last_run_time=spec.trigger_start,
            next_run_time=None,
            observed_at=spec.trigger_start + timedelta(minutes=1),
        )
    elif phase == "post_run":
        values.update(
            last_run_time=spec.trigger_start,
            observed_at=spec.trigger_start + timedelta(minutes=2),
        )
    return V536TaskSnapshot(**values)


def test_task_spec_uses_absolute_paths_and_only_non_secret_arguments(
    tmp_path: Path,
) -> None:
    spec = build_v536_task_spec(_authorization(tmp_path))
    assert spec.task_identity == "\\crypto-tournament-v2-oos-scheduler"
    assert spec.working_directory == tmp_path.resolve()
    assert "%REPO_ROOT%" not in spec.action_arguments
    assert str(tmp_path.resolve()) in spec.action_arguments
    assert "-Mode execute" in spec.action_arguments
    assert "-TaskMutationAuthorized" in spec.action_arguments
    assert "-CredentialReadAuthorized" in spec.action_arguments
    assert "-ExecuteAuthorized" in spec.action_arguments
    assert "ALPACA_API_KEY" not in spec.action_arguments
    assert "ALPACA_SECRET_KEY" not in spec.action_arguments


def test_task_spec_accepts_exact_external_operator_authorization_path(
    tmp_path: Path,
) -> None:
    deployment_root = tmp_path / "deployment"
    authorization = _authorization(
        deployment_root,
        artifact_root=tmp_path / "operator_grants",
    )

    spec = build_v536_task_spec(authorization)

    expected_artifact = authorization.artifact_path
    assert expected_artifact is not None
    assert expected_artifact.parent != deployment_root.resolve()
    assert (
        f'-AuthorizationArtifact "{expected_artifact}"'
        in spec.action_arguments
    )
    assert spec.working_directory == deployment_root.resolve()


def test_task_spec_rejects_relative_authorization_path(
    tmp_path: Path,
) -> None:
    authorization = replace(
        _authorization(tmp_path),
        artifact_path=Path("authorization.json"),
    )

    with pytest.raises(V536TaskError, match="task_authorization_path_missing"):
        build_v536_task_spec(authorization)


@pytest.mark.parametrize("artifact_kind", ("missing", "directory"))
def test_task_spec_rejects_non_file_authorization_path(
    tmp_path: Path,
    artifact_kind: str,
) -> None:
    authorization = _authorization(tmp_path / "deployment")
    invalid_path = (tmp_path / artifact_kind).resolve()
    if artifact_kind == "directory":
        invalid_path.mkdir()

    with pytest.raises(V536TaskError, match="task_authorization_path_invalid"):
        build_v536_task_spec(
            replace(authorization, artifact_path=invalid_path)
        )


def test_task_spec_rejects_symlink_authorization_path_without_os_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization = _authorization(tmp_path)
    artifact_path = authorization.artifact_path
    assert artifact_path is not None
    original_is_symlink = Path.is_symlink

    def fake_is_symlink(path: Path) -> bool:
        if path == artifact_path:
            return True
        return original_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)

    with pytest.raises(V536TaskError, match="task_authorization_path_invalid"):
        build_v536_task_spec(authorization)


def test_task_spec_still_rejects_repository_wrapper_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment_root = tmp_path / "deployment"
    authorization = _authorization(deployment_root)
    wrapper = (
        authorization.deployment_root
        / "scripts"
        / "run_v536_windows_host_canary.ps1"
    )
    escaped_wrapper = tmp_path / "outside" / wrapper.name
    escaped_wrapper.parent.mkdir()
    escaped_wrapper.write_text("# escaped test wrapper\n", encoding="utf-8")
    original_resolve = Path.resolve

    def fake_resolve(path: Path, strict: bool = False) -> Path:
        if path == wrapper:
            return escaped_wrapper
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    with pytest.raises(V536TaskError, match="task_path_escape"):
        build_v536_task_spec(authorization)


def test_rendered_task_is_one_time_least_privilege_and_disabled(
    tmp_path: Path,
) -> None:
    spec = build_v536_task_spec(_authorization(tmp_path))
    root = ET.fromstring(render_v536_task_xml(spec))
    assert root.findtext("t:RegistrationInfo/t:URI", namespaces=NAMESPACE) == (
        spec.task_identity
    )
    assert root.findtext("t:RegistrationInfo/t:Source", namespaces=NAMESPACE) == (
        spec.authorization_sha256
    )
    assert root.findtext("t:Principals/t:Principal/t:UserId", namespaces=NAMESPACE) == (
        spec.principal
    )
    assert root.findtext("t:Principals/t:Principal/t:LogonType", namespaces=NAMESPACE) == (
        "InteractiveToken"
    )
    assert root.findtext("t:Principals/t:Principal/t:RunLevel", namespaces=NAMESPACE) == (
        "LeastPrivilege"
    )
    assert root.findtext("t:Settings/t:Enabled", namespaces=NAMESPACE) == "false"
    assert root.findtext("t:Settings/t:AllowStartOnDemand", namespaces=NAMESPACE) == (
        "false"
    )
    assert root.findtext("t:Triggers/t:TimeTrigger/t:Enabled", namespaces=NAMESPACE) == (
        "false"
    )
    assert root.find(".//t:Repetition", NAMESPACE) is None
    assert root.find(".//t:RestartOnFailure", NAMESPACE) is None
    assert root.findtext("t:Settings/t:MultipleInstancesPolicy", namespaces=NAMESPACE) == (
        "IgnoreNew"
    )
    assert root.findtext("t:Settings/t:ExecutionTimeLimit", namespaces=NAMESPACE) == (
        "PT15M"
    )


@pytest.mark.parametrize("phase", ("disabled", "armed", "running", "post_run"))
def test_exact_task_snapshot_is_valid_for_each_truthful_phase(
    tmp_path: Path,
    phase: str,
) -> None:
    spec = build_v536_task_spec(_authorization(tmp_path))
    validate_v536_task_snapshot(_snapshot(spec, phase=phase), spec, phase=phase)


@pytest.mark.parametrize(
    ("phase", "change", "classification"),
    (
        ("disabled", {"task_enabled": True}, "task_not_disabled"),
        ("armed", {"next_run_time": None}, "task_next_run_mismatch"),
        ("running", {"state": "Ready"}, "task_not_running"),
        ("running", {"last_task_result": 1}, None),
        ("post_run", {"last_task_result": 1}, "task_terminal_result_failed"),
        ("post_run", {"task_enabled": True}, "task_post_run_not_disabled"),
        ("post_run", {"next_run_time": SCHEDULED_START}, "task_second_run_possible"),
        ("disabled", {"principal": "DOMAIN\\other"}, "task_principal_mismatch"),
        ("disabled", {"action_arguments": "wrong"}, "task_action_mismatch"),
        (
            "disabled",
            {"working_directory": Path("C:/wrong")},
            "task_working_directory_mismatch",
        ),
        ("disabled", {"allow_start_on_demand": True}, "task_on_demand_start_enabled"),
        ("disabled", {"restart_on_failure": True}, "task_restart_enabled"),
    ),
)
def test_task_mismatch_fails_closed_and_running_result_is_explicitly_deferred(
    tmp_path: Path,
    phase: str,
    change: dict[str, object],
    classification: str | None,
) -> None:
    spec = build_v536_task_spec(_authorization(tmp_path))
    snapshot = replace(_snapshot(spec, phase=phase), **change)
    if classification is None:
        validate_v536_task_snapshot(snapshot, spec, phase=phase)
    else:
        with pytest.raises(V536TaskError, match=classification):
            validate_v536_task_snapshot(snapshot, spec, phase=phase)


def test_windows_adapter_uses_only_narrow_scheduler_commands(
    tmp_path: Path,
) -> None:
    spec = build_v536_task_spec(_authorization(tmp_path))
    calls: list[tuple[list[str], dict[str, object]]] = []

    def runner(argv: list[str], **kwargs: object) -> object:
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="discarded-secret")

    adapter = WindowsTaskSchedulerAdapter(process_runner=runner)
    adapter.install_disabled(spec)
    adapter.arm(spec.task_identity)
    adapter.disarm(spec.task_identity)
    assert len(calls) == 3
    install, arm, disarm = calls
    assert "register-scheduledtask" in install[0][-1].lower()
    assert "-force" not in install[0][-1].lower()
    assert install[1]["input"] == render_v536_task_xml(spec)
    assert "enable-scheduledtask" in arm[0][-1].lower()
    assert "start-scheduledtask" not in arm[0][-1].lower()
    assert "disable-scheduledtask" in disarm[0][-1].lower()
    assert "unregister-scheduledtask" not in disarm[0][-1].lower()
    assert all(call[1]["capture_output"] is True for call in calls)


def test_windows_adapter_read_parses_snapshot_and_is_read_only(
    tmp_path: Path,
) -> None:
    spec = build_v536_task_spec(_authorization(tmp_path))
    calls: list[list[str]] = []
    payload = {
        "principal": spec.principal,
        "logon_type": spec.logon_type,
        "run_level": "LeastPrivilege",
        "task_enabled": False,
        "trigger_enabled": False,
        "trigger_start": spec.trigger_start.isoformat(),
        "trigger_end": spec.trigger_end.isoformat(),
        "state": "Disabled",
        "action_execute": spec.action_execute,
        "action_arguments": spec.action_arguments,
        "working_directory": str(spec.working_directory),
        "allow_start_on_demand": False,
        "restart_on_failure": False,
        "multiple_instances_policy": spec.multiple_instances_policy,
        "execution_time_limit": spec.execution_time_limit,
        "last_task_result": 0,
        "last_run_time": None,
        "next_run_time": None,
    }

    def runner(argv: list[str], **_kwargs: object) -> object:
        calls.append(argv)
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        )

    adapter = WindowsTaskSchedulerAdapter(
        process_runner=runner,
        clock=lambda: SCHEDULED_START - timedelta(minutes=10),
    )
    snapshot = adapter.read(spec.task_identity)
    validate_v536_task_snapshot(snapshot, spec, phase="disabled")
    assert len(calls) == 1
    command = calls[0][-1].lower()
    assert "get-scheduledtask" in command
    assert "get-scheduledtaskinfo" in command
    assert "register-scheduledtask" not in command
    assert "enable-scheduledtask" not in command
    assert "disable-scheduledtask" not in command
    assert "start-scheduledtask" not in command


def test_adapter_failures_are_sanitized() -> None:
    def runner(_argv: list[str], **_kwargs: object) -> object:
        raise RuntimeError("V536_SECRET_SENTINEL")

    adapter = WindowsTaskSchedulerAdapter(process_runner=runner)
    with pytest.raises(V536TaskError) as captured:
        adapter.disarm("\\crypto-tournament-v2-oos-scheduler")
    assert str(captured.value) == "task_disarm_failed"
    assert "SENTINEL" not in repr(captured.value)
