"""Bounded Windows Task Scheduler boundary for the V5.36 canary."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import subprocess
from typing import Protocol
import xml.etree.ElementTree as ET

from algotrader.execution.v536_canary_authorization import (
    V536AuthorizationError,
    V536CanaryAuthorization,
)


V536_TASK_EXECUTE = "powershell.exe"
V536_TASK_SCHEMA = "v5_36_bounded_canary_task_v1"
V536_TASK_NAMESPACE = "http://schemas.microsoft.com/windows/2004/02/mit/task"
V536_EXECUTION_LIMIT = "PT15M"
V536_MULTIPLE_INSTANCES_POLICY = "IgnoreNew"


class V536TaskError(RuntimeError):
    """Sanitized Task Scheduler boundary failure."""

    def __init__(self, classification: str) -> None:
        self.classification = classification
        super().__init__(classification)


@dataclass(frozen=True, slots=True)
class V536TaskSpec:
    schema_version: str
    task_identity: str
    principal: str
    logon_type: str
    trigger_start: datetime
    trigger_end: datetime
    trigger_enabled: bool
    task_enabled: bool
    action_execute: str
    action_arguments: str
    working_directory: Path
    allow_start_on_demand: bool
    restart_on_failure: bool
    multiple_instances_policy: str
    execution_time_limit: str
    authorization_sha256: str


@dataclass(frozen=True, slots=True)
class V536TaskSnapshot:
    task_identity: str
    principal: str
    logon_type: str
    run_level: str
    task_enabled: bool
    trigger_enabled: bool
    trigger_start: datetime
    trigger_end: datetime
    state: str
    action_execute: str
    action_arguments: str
    working_directory: Path
    allow_start_on_demand: bool
    restart_on_failure: bool
    multiple_instances_policy: str
    execution_time_limit: str
    last_task_result: int
    last_run_time: datetime | None
    next_run_time: datetime | None
    observed_at: datetime


class V536TaskScheduler(Protocol):
    def install_disabled(self, spec: V536TaskSpec) -> None:
        ...

    def read(self, task_identity: str) -> V536TaskSnapshot:
        ...

    def arm(self, task_identity: str) -> None:
        ...

    def disarm(self, task_identity: str) -> None:
        ...


def build_v536_task_spec(
    authorization: V536CanaryAuthorization,
) -> V536TaskSpec:
    if not isinstance(authorization, V536CanaryAuthorization):
        raise V536TaskError("task_authorization_malformed")
    artifact_path = authorization.artifact_path
    if artifact_path is None or not artifact_path.is_absolute():
        raise V536TaskError("task_authorization_path_missing")
    try:
        root = authorization.deployment_root.resolve(strict=True)
        wrapper = (
            root / "scripts" / "run_v536_windows_host_canary.ps1"
        ).resolve(strict=True)
        if not root.is_dir() or not wrapper.is_file():
            raise ValueError
        wrapper.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        raise V536TaskError("task_path_escape") from None
    try:
        artifact_is_symlink = artifact_path.is_symlink()
        resolved_artifact = artifact_path.resolve(strict=True)
        artifact_is_file = resolved_artifact.is_file()
    except (OSError, RuntimeError):
        raise V536TaskError("task_authorization_path_invalid") from None
    if artifact_is_symlink or not artifact_is_file:
        raise V536TaskError("task_authorization_path_invalid")
    arguments = (
        '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass '
        f'-File "{wrapper}" -Mode execute '
        f'-AuthorizationArtifact "{resolved_artifact}" '
        "-TaskMutationAuthorized -CredentialReadAuthorized -ExecuteAuthorized"
    )
    return V536TaskSpec(
        schema_version=V536_TASK_SCHEMA,
        task_identity=authorization.task_identity,
        principal=authorization.windows_principal,
        logon_type=authorization.task_logon_type,
        trigger_start=authorization.scheduled_start,
        trigger_end=authorization.automatic_disarm_deadline,
        trigger_enabled=False,
        task_enabled=False,
        action_execute=V536_TASK_EXECUTE,
        action_arguments=arguments,
        working_directory=root,
        allow_start_on_demand=False,
        restart_on_failure=False,
        multiple_instances_policy=V536_MULTIPLE_INSTANCES_POLICY,
        execution_time_limit=V536_EXECUTION_LIMIT,
        authorization_sha256=authorization.canonical_authorization_sha256,
    )


def render_v536_task_xml(spec: V536TaskSpec) -> str:
    _validate_spec(spec)
    ET.register_namespace("", V536_TASK_NAMESPACE)

    def element(parent: ET.Element, name: str, text: object) -> ET.Element:
        child = ET.SubElement(parent, f"{{{V536_TASK_NAMESPACE}}}{name}")
        child.text = str(text)
        return child

    root = ET.Element(
        f"{{{V536_TASK_NAMESPACE}}}Task",
        {"version": "1.4"},
    )
    registration = ET.SubElement(
        root,
        f"{{{V536_TASK_NAMESPACE}}}RegistrationInfo",
    )
    element(registration, "Author", "Operator")
    element(
        registration,
        "Description",
        "Bounded V5.36 scheduled read-only canary; initially disabled.",
    )
    element(registration, "URI", spec.task_identity)
    element(registration, "Source", spec.authorization_sha256)

    triggers = ET.SubElement(root, f"{{{V536_TASK_NAMESPACE}}}Triggers")
    trigger = ET.SubElement(triggers, f"{{{V536_TASK_NAMESPACE}}}TimeTrigger")
    element(trigger, "StartBoundary", _windows_utc(spec.trigger_start))
    element(trigger, "EndBoundary", _windows_utc(spec.trigger_end))
    element(trigger, "Enabled", _bool_text(spec.trigger_enabled))

    principals = ET.SubElement(root, f"{{{V536_TASK_NAMESPACE}}}Principals")
    principal = ET.SubElement(
        principals,
        f"{{{V536_TASK_NAMESPACE}}}Principal",
        {"id": "CanaryPrincipal"},
    )
    element(principal, "UserId", spec.principal)
    element(principal, "LogonType", spec.logon_type)
    element(principal, "RunLevel", "LeastPrivilege")

    settings = ET.SubElement(root, f"{{{V536_TASK_NAMESPACE}}}Settings")
    element(settings, "MultipleInstancesPolicy", spec.multiple_instances_policy)
    element(settings, "DisallowStartIfOnBatteries", "false")
    element(settings, "StopIfGoingOnBatteries", "false")
    element(settings, "AllowHardTerminate", "true")
    element(settings, "StartWhenAvailable", "false")
    element(settings, "RunOnlyIfNetworkAvailable", "true")
    element(settings, "AllowStartOnDemand", _bool_text(spec.allow_start_on_demand))
    element(settings, "Enabled", _bool_text(spec.task_enabled))
    element(settings, "Hidden", "false")
    element(settings, "RunOnlyIfIdle", "false")
    element(settings, "WakeToRun", "false")
    element(settings, "ExecutionTimeLimit", spec.execution_time_limit)
    element(settings, "Priority", "7")
    element(settings, "DeleteExpiredTaskAfter", "PT1H")

    actions = ET.SubElement(
        root,
        f"{{{V536_TASK_NAMESPACE}}}Actions",
        {"Context": "CanaryPrincipal"},
    )
    action = ET.SubElement(actions, f"{{{V536_TASK_NAMESPACE}}}Exec")
    element(action, "Command", spec.action_execute)
    element(action, "Arguments", spec.action_arguments)
    element(action, "WorkingDirectory", str(spec.working_directory))
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def validate_v536_task_snapshot(
    snapshot: V536TaskSnapshot,
    spec: V536TaskSpec,
    *,
    phase: str,
) -> None:
    if phase not in {"disabled", "armed", "running", "post_run"}:
        raise V536TaskError("task_attestation_phase_invalid")
    if not isinstance(snapshot, V536TaskSnapshot):
        raise V536TaskError("task_snapshot_malformed")
    _validate_spec(spec)
    if snapshot.task_identity != spec.task_identity:
        raise V536TaskError("task_identity_mismatch")
    if snapshot.principal.casefold() != spec.principal.casefold():
        raise V536TaskError("task_principal_mismatch")
    if snapshot.logon_type != spec.logon_type:
        raise V536TaskError("task_logon_type_mismatch")
    if snapshot.run_level != "LeastPrivilege":
        raise V536TaskError("task_privilege_mismatch")
    if snapshot.trigger_start != spec.trigger_start:
        raise V536TaskError("task_trigger_mismatch")
    if snapshot.trigger_end != spec.trigger_end:
        raise V536TaskError("task_trigger_mismatch")
    if snapshot.action_execute.casefold() != spec.action_execute.casefold():
        raise V536TaskError("task_action_mismatch")
    if snapshot.action_arguments != spec.action_arguments:
        raise V536TaskError("task_action_mismatch")
    if snapshot.working_directory.resolve() != spec.working_directory.resolve():
        raise V536TaskError("task_working_directory_mismatch")
    if snapshot.allow_start_on_demand is not False:
        raise V536TaskError("task_on_demand_start_enabled")
    if snapshot.restart_on_failure is not False:
        raise V536TaskError("task_restart_enabled")
    if snapshot.multiple_instances_policy != spec.multiple_instances_policy:
        raise V536TaskError("task_overlap_policy_mismatch")
    if snapshot.execution_time_limit != spec.execution_time_limit:
        raise V536TaskError("task_execution_limit_mismatch")

    if phase == "disabled":
        if snapshot.task_enabled or snapshot.trigger_enabled:
            raise V536TaskError("task_not_disabled")
        if snapshot.state not in {"Disabled", "Ready"}:
            raise V536TaskError("task_state_mismatch")
    elif phase == "armed":
        if not snapshot.task_enabled or not snapshot.trigger_enabled:
            raise V536TaskError("task_not_armed")
        if snapshot.state != "Ready":
            raise V536TaskError("task_state_mismatch")
        if snapshot.next_run_time != spec.trigger_start:
            raise V536TaskError("task_next_run_mismatch")
    elif phase == "running":
        if not snapshot.task_enabled or not snapshot.trigger_enabled:
            raise V536TaskError("task_not_armed")
        if snapshot.state != "Running":
            raise V536TaskError("task_not_running")
        if snapshot.last_run_time is None:
            raise V536TaskError("task_run_time_missing")
        if not spec.trigger_start <= snapshot.last_run_time < spec.trigger_end:
            raise V536TaskError("task_run_time_mismatch")
    else:
        if snapshot.task_enabled or snapshot.trigger_enabled:
            raise V536TaskError("task_post_run_not_disabled")
        if snapshot.state not in {"Disabled", "Ready"}:
            raise V536TaskError("task_state_mismatch")
        if snapshot.last_task_result != 0:
            raise V536TaskError("task_terminal_result_failed")
        if snapshot.last_run_time is None:
            raise V536TaskError("task_run_time_missing")
        if not spec.trigger_start <= snapshot.last_run_time < spec.trigger_end:
            raise V536TaskError("task_run_time_mismatch")
        if snapshot.next_run_time is not None:
            raise V536TaskError("task_second_run_possible")


class WindowsTaskSchedulerAdapter:
    """Narrow PowerShell adapter for the explicit Task Scheduler boundary."""

    def __init__(
        self,
        *,
        process_runner: Callable[..., object] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._process_runner = process_runner or subprocess.run
        self._clock = clock or (lambda: datetime.now(UTC))

    def install_disabled(self, spec: V536TaskSpec) -> None:
        xml = render_v536_task_xml(spec)
        name = _task_name(spec.task_identity)
        command = (
            f"$existing=Get-ScheduledTask -TaskName '{_ps_quote(name)}' "
            "-ErrorAction SilentlyContinue;"
            "if($null -ne $existing){exit 17};"
            "$xml=[Console]::In.ReadToEnd();"
            f"Register-ScheduledTask -TaskName '{_ps_quote(name)}' "
            "-Xml $xml -ErrorAction Stop | Out-Null"
        )
        self._run_mutation(command, input_text=xml, failure="task_install_failed")

    def read(self, task_identity: str) -> V536TaskSnapshot:
        name = _task_name(task_identity)
        command = (
            f"$t=Get-ScheduledTask -TaskName '{_ps_quote(name)}' -ErrorAction Stop;"
            f"$i=Get-ScheduledTaskInfo -TaskName '{_ps_quote(name)}' -ErrorAction Stop;"
            "$tr=$t.Triggers[0];$a=$t.Actions[0];$restart=$null -ne $t.Settings.RestartCount -and $t.Settings.RestartCount -gt 0;"
            "[ordered]@{"
            "principal=[string]$t.Principal.UserId;logon_type=[string]$t.Principal.LogonType;run_level=[string]$t.Principal.RunLevel;"
            "task_enabled=[bool]$t.Settings.Enabled;trigger_enabled=[bool]$tr.Enabled;"
            "trigger_start=([datetime]$tr.StartBoundary).ToUniversalTime().ToString('o');"
            "trigger_end=([datetime]$tr.EndBoundary).ToUniversalTime().ToString('o');state=[string]$t.State;"
            "action_execute=[string]$a.Execute;action_arguments=[string]$a.Arguments;working_directory=[string]$a.WorkingDirectory;"
            "allow_start_on_demand=[bool]$t.Settings.AllowDemandStart;restart_on_failure=[bool]$restart;"
            "multiple_instances_policy=[string]$t.Settings.MultipleInstances;execution_time_limit=[string]$t.Settings.ExecutionTimeLimit;"
            "last_task_result=[int]$i.LastTaskResult;"
            "last_run_time=if($i.LastRunTime.Year -lt 2000){$null}else{$i.LastRunTime.ToUniversalTime().ToString('o')};"
            "next_run_time=if($i.NextRunTime.Year -lt 2000){$null}else{$i.NextRunTime.ToUniversalTime().ToString('o')}"
            "}|ConvertTo-Json -Compress"
        )
        result = self._run_read(command)
        try:
            payload = json.loads(str(getattr(result, "stdout", "")))
            if not isinstance(payload, dict):
                raise ValueError
            return V536TaskSnapshot(
                task_identity=task_identity,
                principal=_snapshot_text(payload, "principal"),
                logon_type=_snapshot_text(payload, "logon_type"),
                run_level=_snapshot_text(payload, "run_level"),
                task_enabled=_snapshot_bool(payload, "task_enabled"),
                trigger_enabled=_snapshot_bool(payload, "trigger_enabled"),
                trigger_start=_parse_utc(payload.get("trigger_start")),
                trigger_end=_parse_utc(payload.get("trigger_end")),
                state=_snapshot_text(payload, "state"),
                action_execute=_snapshot_text(payload, "action_execute"),
                action_arguments=_snapshot_text(payload, "action_arguments"),
                working_directory=Path(
                    _snapshot_text(payload, "working_directory")
                ),
                allow_start_on_demand=_snapshot_bool(
                    payload,
                    "allow_start_on_demand",
                ),
                restart_on_failure=_snapshot_bool(
                    payload,
                    "restart_on_failure",
                ),
                multiple_instances_policy=_snapshot_text(
                    payload,
                    "multiple_instances_policy",
                ),
                execution_time_limit=_snapshot_text(
                    payload,
                    "execution_time_limit",
                ),
                last_task_result=_snapshot_int(payload, "last_task_result"),
                last_run_time=_optional_utc(payload.get("last_run_time")),
                next_run_time=_optional_utc(payload.get("next_run_time")),
                observed_at=_parse_utc(self._clock()),
            )
        except V536TaskError:
            raise
        except Exception:
            raise V536TaskError("task_snapshot_malformed") from None

    def arm(self, task_identity: str) -> None:
        name = _task_name(task_identity)
        command = (
            f"$t=Get-ScheduledTask -TaskName '{_ps_quote(name)}' -ErrorAction Stop;"
            "if($t.Triggers.Count -ne 1){exit 18};"
            "$t.Triggers[0].Enabled=$true;"
            "Set-ScheduledTask -InputObject $t -ErrorAction Stop | Out-Null;"
            f"Enable-ScheduledTask -TaskName '{_ps_quote(name)}' -ErrorAction Stop | Out-Null"
        )
        self._run_mutation(command, failure="task_arm_failed")

    def disarm(self, task_identity: str) -> None:
        name = _task_name(task_identity)
        command = (
            f"$t=Get-ScheduledTask -TaskName '{_ps_quote(name)}' -ErrorAction SilentlyContinue;"
            "if($null -eq $t){exit 0};"
            "if($t.Triggers.Count -ne 1){exit 18};"
            "$t.Triggers[0].Enabled=$false;"
            "Set-ScheduledTask -InputObject $t -ErrorAction Stop | Out-Null;"
            f"Disable-ScheduledTask -TaskName '{_ps_quote(name)}' -ErrorAction Stop | Out-Null"
        )
        self._run_mutation(command, failure="task_disarm_failed")

    def _run_read(self, command: str) -> object:
        try:
            result = self._process_runner(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    command,
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except Exception:
            raise V536TaskError("task_read_failed") from None
        if getattr(result, "returncode", 1) != 0:
            raise V536TaskError("task_read_failed")
        return result

    def _run_mutation(
        self,
        command: str,
        *,
        input_text: str | None = None,
        failure: str,
    ) -> None:
        try:
            result = self._process_runner(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    command,
                ],
                input=input_text,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except Exception:
            raise V536TaskError(failure) from None
        if getattr(result, "returncode", 1) != 0:
            raise V536TaskError(failure)


def _validate_spec(spec: V536TaskSpec) -> None:
    if not isinstance(spec, V536TaskSpec) or spec.schema_version != V536_TASK_SCHEMA:
        raise V536TaskError("task_spec_malformed")
    if spec.task_enabled or spec.trigger_enabled:
        raise V536TaskError("task_spec_not_disabled")
    if spec.allow_start_on_demand or spec.restart_on_failure:
        raise V536TaskError("task_spec_unsafe")
    if spec.logon_type != "InteractiveToken":
        raise V536TaskError("task_spec_logon_type_unsafe")
    if spec.multiple_instances_policy != V536_MULTIPLE_INSTANCES_POLICY:
        raise V536TaskError("task_spec_overlap_policy_unsafe")
    if spec.execution_time_limit != V536_EXECUTION_LIMIT:
        raise V536TaskError("task_spec_execution_limit_unsafe")
    if not spec.trigger_start < spec.trigger_end:
        raise V536TaskError("task_spec_trigger_malformed")
    if not spec.working_directory.is_absolute():
        raise V536TaskError("task_spec_working_directory_malformed")


def _task_name(task_identity: str) -> str:
    if task_identity != "\\crypto-tournament-v2-oos-scheduler":
        raise V536TaskError("task_identity_mismatch")
    return task_identity.removeprefix("\\")


def _ps_quote(value: str) -> str:
    return value.replace("'", "''")


def _windows_utc(value: datetime) -> str:
    parsed = _parse_utc(value)
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _parse_utc(value: object) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif type(value) is str:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise V536TaskError("task_time_malformed") from None
    else:
        raise V536TaskError("task_time_malformed")
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise V536TaskError("task_time_malformed")
    return parsed.astimezone(UTC)


def _optional_utc(value: object) -> datetime | None:
    return None if value is None else _parse_utc(value)


def _snapshot_text(payload: dict[str, object], field: str) -> str:
    value = payload.get(field)
    if type(value) is not str or not value.strip():
        raise V536TaskError("task_snapshot_malformed")
    return value


def _snapshot_bool(payload: dict[str, object], field: str) -> bool:
    value = payload.get(field)
    if type(value) is not bool:
        raise V536TaskError("task_snapshot_malformed")
    return value


def _snapshot_int(payload: dict[str, object], field: str) -> int:
    value = payload.get(field)
    if type(value) is not int:
        raise V536TaskError("task_snapshot_malformed")
    return value


__all__ = [
    "V536TaskError",
    "V536TaskScheduler",
    "V536TaskSnapshot",
    "V536TaskSpec",
    "WindowsTaskSchedulerAdapter",
    "build_v536_task_spec",
    "render_v536_task_xml",
    "validate_v536_task_snapshot",
]
