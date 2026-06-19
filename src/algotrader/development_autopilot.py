"""Repo-local development autopilot bootstrap.

This module is intentionally outside the trading hot path. It coordinates one
local non-capital builder command against one safe machine-readable work order,
then records deterministic verification and next-action artifacts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import shutil
import subprocess
import sys
import time
from typing import Any


SCHEMA_VERSION = "1.0"
SUPPORTED_WORK_ORDER_SCHEMA_VERSIONS = {"1", "1.0"}
DEFAULT_OUTPUT_ROOT = Path("runs/development_autopilot")
DEFAULT_AGENT_ROUTE = "codex"
DEFAULT_COMMAND_TIMEOUT_SECONDS = 1800
MIN_COMMAND_TIMEOUT_SECONDS = 1
MAX_COMMAND_TIMEOUT_SECONDS = 7200
GIT_MODES = ("verify_only", "commit_only", "commit_and_push")
FULL_PYTEST_POLICIES = ("always", "changed_files_only")
FULL_PYTEST_POLICY_ALWAYS = "always"
FULL_PYTEST_POLICY_CHANGED_FILES_ONLY = "changed_files_only"
SAFE_REQUIRED_LABELS = frozenset(
    {
        "development_autopilot_only",
        "non_capital_work",
        "offline_verification_required",
        "not_live_authorized",
        "broker_mutation_forbidden",
        "paper_submit_forbidden",
        "profit_claim=none",
    }
)
HARD_GATE_FIELDS = (
    "broker_read_authorized",
    "broker_mutation_authorized",
    "paper_submit_authorized",
    "live_trading_authorized",
    "capital_authorized",
    "paid_service_authorized",
    "credential_access_authorized",
    "network_access_authorized",
)
REQUIRED_WORK_ORDER_FIELDS = (
    "schema_version",
    "work_order_id",
    "phase",
    "goal",
    "created_by",
    "source_of_truth",
    "expected_head",
    "agent_route",
    "allowed_files",
    "forbidden_paths",
    "required_verification_commands",
    "git_mode_allowed",
    "commit_message",
    "labels",
) + HARD_GATE_FIELDS
SCRUBBED_ENV_VARS = (
    "APP_PROFILE",
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
    "ALPACA_PAPER_BASE_URL",
    "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
)
PROFILE_CREDENTIAL_PRECHECK_NAMES = (
    "APP_PROFILE",
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
)
DEFAULT_FORBIDDEN_PATH_PREFIXES = (
    "runs/",
    ".agent_inbox/",
    ".data/",
    "docs/reviews/",
)
TOO_BROAD_ALLOWED_PATHS = {
    ".",
    "*",
    "src",
    "src/",
    "tests",
    "tests/",
    "scripts",
    "scripts/",
    "docs",
    "docs/",
}
SECRET_LOOKING_MARKERS = (
    "alpaca_api_key=",
    "alpaca_api_secret_key=",
    "alpaca_secret_key=",
    "apca_api_key_id=",
    "apca_api_secret_key=",
    "-----begin",
    "private key-----",
    "api_key=",
    "secret_key=",
    "password=",
    "bearer ",
)
UNAUTHORIZED_PROMPT_MARKERS = (
    "broker mutation authorized",
    "broker_mutation_authorized=true",
    "paper submit authorized",
    "paper_submit_authorized=true",
    "live trading authorized",
    "live_trading_authorized=true",
    "capital authorized",
    "capital_authorized=true",
)
NEXT_ACTIONS = {
    "hard_gate": "stop_for_gpt_and_operator_hard_gate_review",
    "repository_state": "restore_or_review_repository_state_before_dispatch",
    "work_order": "replace_or_repair_work_order",
    "route_unavailable": (
        "install_or_configure_local_builder_route_or_use_manual_builder_flow"
    ),
    "agent_failed": "review_agent_failure_and_issue_repair_prompt",
    "unexpected_changes": "review_unexpected_changes_before_verification_or_commit",
    "verification_failed": "issue_repair_prompt_with_failed_checks",
    "agent_timeout": "review_agent_timeout_and_issue_repair_prompt",
    "verification_timeout": "issue_repair_prompt_with_timed_out_checks",
    "verify_only_success": "send_report_to_gpt_for_classification_and_commit_commands",
    "commit_only_success": "review_local_commit_and_push_if_appropriate",
    "commit_and_push_success": "select_next_safe_milestone",
    "push_authorization": "review_push_authorization_blocker_before_git_mutation",
}


@dataclass(frozen=True)
class DevelopmentAutopilotOptions:
    output_root: Path = DEFAULT_OUTPUT_ROOT
    work_order_path: Path | None = None
    expected_head: str | None = None
    agent_route: str = DEFAULT_AGENT_ROUTE
    agent_command: str | None = None
    git_mode: str = "verify_only"
    repository_verification_commands: tuple[tuple[str, ...], ...] | None = None
    command_timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS
    full_pytest_policy: str = FULL_PYTEST_POLICY_ALWAYS


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    stdout_path: str | None = None
    stderr_path: str | None = None
    started_at: str = ""
    ended_at: str = ""
    elapsed_seconds: float = 0.0
    timed_out: bool = False
    timeout_seconds: int | None = None
    reason: str = ""
    command_kind: str = ""


@dataclass(frozen=True)
class RepoStatusEntry:
    code: str
    path: str


@dataclass(frozen=True)
class RepoState:
    branch: str
    head: str
    origin_main: str
    status_entries: tuple[RepoStatusEntry, ...]

    @property
    def expected_docs_reviews_residue_present(self) -> bool:
        return any(_is_expected_docs_reviews_residue(entry) for entry in self.status_entries)

    @property
    def staged_files(self) -> tuple[str, ...]:
        return tuple(
            entry.path
            for entry in self.status_entries
            if entry.code != "??" and entry.code[:1] != " "
        )

    @property
    def relevant_changed_files(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                entry.path
                for entry in self.status_entries
                if not _is_expected_docs_reviews_residue(entry)
            )
        )

    def as_summary(self) -> dict[str, object]:
        return {
            "branch": self.branch,
            "head": self.head,
            "origin_main": self.origin_main,
            "status_entries": [
                {"code": entry.code, "path": entry.path}
                for entry in self.status_entries
            ],
            "expected_docs_reviews_residue_present": (
                self.expected_docs_reviews_residue_present
            ),
            "staged_files": list(self.staged_files),
            "changed_files": list(self.relevant_changed_files),
        }


@dataclass(frozen=True)
class WorkOrder:
    raw: dict[str, object]
    path: Path
    work_order_id: str
    phase: str
    expected_head: str
    agent_route: str
    prompt: str
    allowed_files: tuple[str, ...]
    forbidden_paths: tuple[str, ...]
    required_verification_commands: tuple[tuple[str, ...], ...]
    git_mode_allowed: tuple[str, ...]
    commit_message: str
    labels: tuple[str, ...]
    allow_no_change_fast_path: bool
    command_timeout_seconds: int | None
    nonlocal_push_authorized: bool


@dataclass(frozen=True)
class RepositoryVerificationPlan:
    safety_guard_commands: tuple[tuple[str, ...], ...]
    verify_offline_command: tuple[str, ...] | None
    full_pytest_command: tuple[str, ...] | None


def run_development_autopilot(
    options: DevelopmentAutopilotOptions | None = None,
    *,
    repo_root: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Run one fail-closed development-autopilot cycle."""

    resolved_options = options or DevelopmentAutopilotOptions()
    root = (repo_root or Path.cwd()).resolve()
    process_env = dict(os.environ if env is None else env)
    output_root = _resolve_path(root, resolved_options.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    artifacts = _artifact_paths(output_root)
    _ensure_empty_capture_files(artifacts)

    started_at = _utc_now_text()
    run_id = _run_id(started_at)
    record: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "phase": "",
        "work_order_id": "",
        "expected_head": resolved_options.expected_head or "",
        "starting_head": "",
        "ending_head": "",
        "origin_main_before": "",
        "origin_main_after": "",
        "branch": "",
        "dirty_state_before": {},
        "dirty_state_after": {},
        "route_name": resolved_options.agent_route,
        "route_available": False,
        "agent_command_hash": "",
        "agent_command_identity": "",
        "agent_exit_code": None,
        "changed_files": [],
        "allowed_files_result": "not_checked",
        "forbidden_path_result": "not_checked",
        "verification_commands": [],
        "safety_guard_statuses": {},
        "verify_offline_status": "not_started",
        "preflight_booleans": _preflight_booleans(process_env),
        "git_mode": resolved_options.git_mode,
        **_empty_git_mutation_record(),
        "final_classification": "blocked",
        "exact_next_action": "",
        "required_labels": sorted(SAFE_REQUIRED_LABELS),
        "broker_read_attempted": False,
        "broker_mutation_attempted": False,
        "paper_submit_attempted": False,
        "live_trading_attempted": False,
        "capital_operation_attempted": False,
        "paid_service_attempted": False,
        "credential_access_attempted": False,
        "network_access_authorized": False,
        "command_timeout_seconds": resolved_options.command_timeout_seconds,
        "work_order_command_timeout_seconds": None,
        "agent_timeout": False,
        "verification_timeout": False,
        "verification_timeout_reason": "",
        "full_pytest_policy": resolved_options.full_pytest_policy,
        "full_pytest_required": True,
        "full_pytest_status": "not_started",
        "full_pytest_exit_code": None,
        "full_pytest_elapsed_seconds": 0.0,
        "full_pytest_skipped_reason": "",
        "no_change_fast_path_allowed": False,
        "no_change_fast_path_used": False,
        "normal_pytest_offline_invariant_preserved": True,
    }

    timeout_error = _command_timeout_validation_error(
        resolved_options.command_timeout_seconds,
        field_name="command_timeout_seconds",
    )
    if timeout_error:
        return _finish(
            artifacts,
            record,
            outcome="blocked",
            reason=timeout_error,
            next_action=NEXT_ACTIONS["work_order"],
            exit_code=2,
            repo_root=root,
        )

    if resolved_options.full_pytest_policy not in FULL_PYTEST_POLICIES:
        return _finish(
            artifacts,
            record,
            outcome="blocked",
            reason="invalid_full_pytest_policy",
            next_action=NEXT_ACTIONS["work_order"],
            exit_code=2,
            repo_root=root,
        )

    if resolved_options.git_mode not in GIT_MODES:
        return _finish(
            artifacts,
            record,
            outcome="blocked",
            reason="invalid_git_mode",
            next_action=NEXT_ACTIONS["work_order"],
            exit_code=2,
            repo_root=root,
        )

    repo_before = _inspect_repo(root)
    record["branch"] = repo_before.branch
    record["starting_head"] = repo_before.head
    record["origin_main_before"] = repo_before.origin_main
    record["dirty_state_before"] = repo_before.as_summary()

    baseline_expected = resolved_options.expected_head
    if baseline_expected and not _baseline_matches(repo_before, baseline_expected):
        return _finish(
            artifacts,
            record,
            outcome="blocked",
            reason="baseline_mismatch",
            next_action=NEXT_ACTIONS["repository_state"],
            exit_code=2,
            repo_root=root,
        )

    repo_block_reason = _pre_dispatch_repo_block_reason(repo_before)
    if repo_block_reason:
        return _finish(
            artifacts,
            record,
            outcome="blocked",
            reason=repo_block_reason,
            next_action=NEXT_ACTIONS["repository_state"],
            exit_code=2,
            repo_root=root,
        )

    work_order_path = _select_work_order_path(root, resolved_options.work_order_path)
    if work_order_path is None:
        return _finish(
            artifacts,
            record,
            outcome="blocked",
            reason="missing_work_order",
            next_action=NEXT_ACTIONS["work_order"],
            exit_code=2,
            repo_root=root,
        )
    if isinstance(work_order_path, str):
        return _finish(
            artifacts,
            record,
            outcome="blocked",
            reason=work_order_path,
            next_action=NEXT_ACTIONS["work_order"],
            exit_code=2,
            repo_root=root,
        )

    work_order_result = _load_work_order(work_order_path)
    if isinstance(work_order_result, str):
        _write_json_file(
            artifacts["work_order_packet"],
            {"copied": False, "error": work_order_result},
        )
        next_action = (
            NEXT_ACTIONS["hard_gate"]
            if work_order_result.startswith("hard_gate:")
            else NEXT_ACTIONS["work_order"]
        )
        outcome = "rejected" if work_order_result.startswith("hard_gate:") else "blocked"
        return _finish(
            artifacts,
            record,
            outcome=outcome,
            reason=work_order_result,
            next_action=next_action,
            exit_code=2,
            repo_root=root,
        )

    work_order = work_order_result
    record["phase"] = work_order.phase
    record["work_order_id"] = work_order.work_order_id
    record["expected_head"] = resolved_options.expected_head or work_order.expected_head
    record["route_name"] = resolved_options.agent_route or work_order.agent_route
    command_timeout_seconds = _effective_command_timeout_seconds(
        resolved_options.command_timeout_seconds,
        work_order.command_timeout_seconds,
    )
    record["command_timeout_seconds"] = command_timeout_seconds
    record["work_order_command_timeout_seconds"] = work_order.command_timeout_seconds
    record["nonlocal_push_authorized"] = work_order.nonlocal_push_authorized
    record["allow_no_change_fast_path"] = work_order.allow_no_change_fast_path
    record["no_change_fast_path_allowed"] = _no_change_fast_path_allowed(
        resolved_options.full_pytest_policy,
        resolved_options.git_mode,
        work_order,
    )
    _write_json_file(artifacts["work_order_packet"], _sanitized_work_order_packet(work_order))

    expected_head = resolved_options.expected_head or work_order.expected_head
    if expected_head and not _baseline_matches(repo_before, expected_head):
        return _finish(
            artifacts,
            record,
            outcome="blocked",
            reason="work_order_expected_head_mismatch",
            next_action=NEXT_ACTIONS["repository_state"],
            exit_code=2,
            repo_root=root,
        )

    if resolved_options.git_mode != "verify_only" and resolved_options.git_mode not in work_order.git_mode_allowed:
        return _finish(
            artifacts,
            record,
            outcome="rejected",
            reason="git_mode_not_allowed_by_work_order",
            next_action=NEXT_ACTIONS["work_order"],
            exit_code=2,
            repo_root=root,
        )
    if (
        resolved_options.git_mode == "commit_and_push"
        and "commit_only" not in work_order.git_mode_allowed
    ):
        return _finish(
            artifacts,
            record,
            outcome="rejected",
            reason="commit_and_push_requires_commit_only_permission",
            next_action=NEXT_ACTIONS["work_order"],
            exit_code=2,
            repo_root=root,
        )

    preflight_reason = _blocking_preflight_reason(process_env)
    if preflight_reason:
        return _finish(
            artifacts,
            record,
            outcome="blocked",
            reason=preflight_reason,
            next_action=NEXT_ACTIONS["hard_gate"],
            exit_code=2,
            repo_root=root,
        )

    route_command = _resolve_agent_command(
        resolved_options.agent_route or work_order.agent_route,
        resolved_options.agent_command,
    )
    if route_command is None:
        return _finish(
            artifacts,
            record,
            outcome="blocked",
            reason="blocked/local_builder_route_unavailable",
            next_action=NEXT_ACTIONS["route_unavailable"],
            exit_code=2,
            repo_root=root,
        )

    record["route_available"] = True
    record["agent_command_hash"] = _command_hash(route_command)
    record["agent_command_identity"] = _sanitized_command_identity(route_command)

    agent_result = _invoke_agent(
        root,
        route_command,
        work_order.prompt,
        artifacts["agent_stdout"],
        artifacts["agent_stderr"],
        process_env,
        timeout_seconds=command_timeout_seconds,
    )
    record["agent_exit_code"] = agent_result.exit_code
    record["agent_started_at"] = agent_result.started_at
    record["agent_ended_at"] = agent_result.ended_at
    record["agent_elapsed_seconds"] = agent_result.elapsed_seconds
    record["agent_stdout_path"] = agent_result.stdout_path
    record["agent_stderr_path"] = agent_result.stderr_path
    record["agent_timeout"] = agent_result.timed_out

    repo_after_agent = _inspect_repo(root)
    changed_after_agent = repo_after_agent.relevant_changed_files
    record["changed_files"] = list(changed_after_agent)
    record["dirty_state_after_agent"] = repo_after_agent.as_summary()

    if agent_result.timed_out:
        return _finish(
            artifacts,
            record,
            outcome="failed",
            reason="agent_command_timeout",
            next_action=NEXT_ACTIONS["agent_timeout"],
            exit_code=1,
            repo_root=root,
        )

    if agent_result.exit_code != 0:
        return _finish(
            artifacts,
            record,
            outcome="failed",
            reason="agent_execution_failed",
            next_action=NEXT_ACTIONS["agent_failed"],
            exit_code=1,
            repo_root=root,
        )

    file_policy_reason = _changed_file_policy_reason(
        changed_after_agent,
        allowed_files=work_order.allowed_files,
        forbidden_paths=work_order.forbidden_paths,
    )
    if file_policy_reason:
        record["allowed_files_result"] = "failed"
        record["forbidden_path_result"] = "failed"
        return _finish(
            artifacts,
            record,
            outcome="rejected",
            reason=file_policy_reason,
            next_action=NEXT_ACTIONS["unexpected_changes"],
            exit_code=2,
            repo_root=root,
        )

    record["allowed_files_result"] = "passed"
    record["forbidden_path_result"] = "passed"

    preflight_reason = _blocking_preflight_reason(process_env)
    if preflight_reason:
        return _finish(
            artifacts,
            record,
            outcome="blocked",
            reason=preflight_reason,
            next_action=NEXT_ACTIONS["hard_gate"],
            exit_code=2,
            repo_root=root,
        )

    verification_results: list[CommandResult] = []
    targeted_results = _run_verification_commands(
        root,
        output_root,
        work_order.required_verification_commands,
        process_env,
        timeout_seconds=command_timeout_seconds,
        command_kind="work_order_verification",
        timeout_reason="verification_command_timeout",
    )
    verification_results.extend(targeted_results)
    _update_verification_record(record, tuple(verification_results))

    timed_out_verification = _first_timed_out(targeted_results)
    if timed_out_verification is not None:
        _record_verification_timeout(record, "verification_command_timeout")
        return _finish(
            artifacts,
            record,
            outcome="repair_required",
            reason="verification_command_timeout",
            next_action=NEXT_ACTIONS["verification_timeout"],
            exit_code=1,
            repo_root=root,
        )

    failed_verification = _first_failed(targeted_results)
    if failed_verification is not None:
        return _finish(
            artifacts,
            record,
            outcome="repair_required",
            reason="verification_failed",
            next_action=NEXT_ACTIONS["verification_failed"],
            exit_code=1,
            repo_root=root,
        )

    repository_plan = _repository_verification_plan(
        resolved_options.repository_verification_commands
    )
    safety_guard_results = _run_verification_commands(
        root,
        output_root,
        repository_plan.safety_guard_commands,
        process_env,
        timeout_seconds=command_timeout_seconds,
        command_kind="safety_guard",
        timeout_reason="safety_guard_timeout",
        start_index=len(verification_results) + 1,
    )
    verification_results.extend(safety_guard_results)
    _update_verification_record(record, tuple(verification_results))

    timed_out_verification = _first_timed_out(safety_guard_results)
    if timed_out_verification is not None:
        _record_verification_timeout(record, "safety_guard_timeout")
        return _finish(
            artifacts,
            record,
            outcome="repair_required",
            reason="safety_guard_timeout",
            next_action=NEXT_ACTIONS["verification_timeout"],
            exit_code=1,
            repo_root=root,
        )

    failed_verification = _first_failed(safety_guard_results)
    if failed_verification is not None:
        return _finish(
            artifacts,
            record,
            outcome="repair_required",
            reason="verification_failed",
            next_action=NEXT_ACTIONS["verification_failed"],
            exit_code=1,
            repo_root=root,
        )

    verify_offline_results: tuple[CommandResult, ...] = ()
    if repository_plan.verify_offline_command is not None:
        verify_offline_results = _run_verification_commands(
            root,
            output_root,
            (repository_plan.verify_offline_command,),
            process_env,
            timeout_seconds=command_timeout_seconds,
            command_kind="verify_offline",
            timeout_reason="verify_offline_timeout",
            start_index=len(verification_results) + 1,
        )
        verification_results.extend(verify_offline_results)
        _update_verification_record(record, tuple(verification_results))

    timed_out_verification = _first_timed_out(verify_offline_results)
    if timed_out_verification is not None:
        _record_verification_timeout(record, "verify_offline_timeout")
        record["verify_offline_status"] = "timeout"
        return _finish(
            artifacts,
            record,
            outcome="repair_required",
            reason="verify_offline_timeout",
            next_action=NEXT_ACTIONS["verification_timeout"],
            exit_code=1,
            repo_root=root,
        )

    failed_verification = _first_failed(verify_offline_results)
    if failed_verification is not None:
        record["verify_offline_status"] = "failed"
        return _finish(
            artifacts,
            record,
            outcome="repair_required",
            reason="verification_failed",
            next_action=NEXT_ACTIONS["verification_failed"],
            exit_code=1,
            repo_root=root,
        )
    record["verify_offline_status"] = (
        "passed" if verify_offline_results else "not_configured"
    )

    repo_after_verification = _inspect_repo(root)
    changed_after_verification = repo_after_verification.relevant_changed_files
    record["changed_files"] = list(changed_after_verification)
    record["dirty_state_after_verification"] = repo_after_verification.as_summary()
    file_policy_reason = _changed_file_policy_reason(
        changed_after_verification,
        allowed_files=work_order.allowed_files,
        forbidden_paths=work_order.forbidden_paths,
    )
    if file_policy_reason:
        record["allowed_files_result"] = "failed"
        record["forbidden_path_result"] = "failed"
        return _finish(
            artifacts,
            record,
            outcome="rejected",
            reason=file_policy_reason,
            next_action=NEXT_ACTIONS["unexpected_changes"],
            exit_code=2,
            repo_root=root,
        )

    if _should_use_no_change_fast_path(
        full_pytest_policy=resolved_options.full_pytest_policy,
        git_mode=resolved_options.git_mode,
        work_order=work_order,
        agent_result=agent_result,
        targeted_results=targeted_results,
        safety_guard_results=safety_guard_results,
        verify_offline_results=verify_offline_results,
        repo_state=repo_after_verification,
        repository_plan=repository_plan,
    ):
        record["full_pytest_required"] = False
        record["full_pytest_status"] = "skipped"
        record["full_pytest_exit_code"] = None
        record["full_pytest_elapsed_seconds"] = 0.0
        record["full_pytest_skipped_reason"] = "no_source_test_script_changes"
        record["no_change_fast_path_used"] = True
    elif repository_plan.full_pytest_command is None:
        record["full_pytest_required"] = False
        record["full_pytest_status"] = "not_configured"
        record["full_pytest_exit_code"] = None
        record["full_pytest_elapsed_seconds"] = 0.0
        record["full_pytest_skipped_reason"] = "full_pytest_command_not_configured"
    else:
        record["full_pytest_required"] = True
        full_pytest_results = _run_verification_commands(
            root,
            output_root,
            (repository_plan.full_pytest_command,),
            process_env,
            timeout_seconds=command_timeout_seconds,
            command_kind="full_pytest",
            timeout_reason="full_pytest_timeout",
            start_index=len(verification_results) + 1,
        )
        verification_results.extend(full_pytest_results)
        _update_verification_record(record, tuple(verification_results))
        full_pytest_result = full_pytest_results[0]
        record["full_pytest_exit_code"] = full_pytest_result.exit_code
        record["full_pytest_elapsed_seconds"] = full_pytest_result.elapsed_seconds

        if full_pytest_result.timed_out:
            record["full_pytest_status"] = "timeout"
            _record_verification_timeout(record, "full_pytest_timeout")
            return _finish(
                artifacts,
                record,
                outcome="repair_required",
                reason="full_pytest_timeout",
                next_action=NEXT_ACTIONS["verification_timeout"],
                exit_code=1,
                repo_root=root,
            )

        if full_pytest_result.exit_code != 0:
            record["full_pytest_status"] = "failed"
            return _finish(
                artifacts,
                record,
                outcome="repair_required",
                reason="verification_failed",
                next_action=NEXT_ACTIONS["verification_failed"],
                exit_code=1,
                repo_root=root,
            )
        record["full_pytest_status"] = "passed"

        repo_after_verification = _inspect_repo(root)
        changed_after_verification = repo_after_verification.relevant_changed_files
        record["changed_files"] = list(changed_after_verification)
        record["dirty_state_after_verification"] = repo_after_verification.as_summary()
        file_policy_reason = _changed_file_policy_reason(
            changed_after_verification,
            allowed_files=work_order.allowed_files,
            forbidden_paths=work_order.forbidden_paths,
        )
        if file_policy_reason:
            record["allowed_files_result"] = "failed"
            record["forbidden_path_result"] = "failed"
            return _finish(
                artifacts,
                record,
                outcome="rejected",
                reason=file_policy_reason,
                next_action=NEXT_ACTIONS["unexpected_changes"],
                exit_code=2,
                repo_root=root,
            )

    if resolved_options.git_mode == "verify_only":
        return _finish(
            artifacts,
            record,
            outcome="accepted",
            reason="verify_only_success_needs_gpt_review",
            next_action=NEXT_ACTIONS["verify_only_success"],
            exit_code=0,
            repo_root=root,
        )

    mutation_result = _perform_git_mutation(
        root,
        work_order,
        resolved_options.git_mode,
        changed_after_verification,
        expected_head,
        repo_after_verification,
        process_env,
    )
    record.update(mutation_result["record"])
    if not mutation_result["ok"]:
        blocker = record.get("push_authorization_blocker")
        return _finish(
            artifacts,
            record,
            outcome="blocked",
            reason=str(mutation_result["reason"]),
            next_action=(
                NEXT_ACTIONS["push_authorization"]
                if blocker
                else NEXT_ACTIONS["repository_state"]
            ),
            exit_code=2,
            repo_root=root,
        )

    success_key = (
        "commit_only_success"
        if resolved_options.git_mode == "commit_only"
        else "commit_and_push_success"
    )
    return _finish(
        artifacts,
        record,
        outcome="accepted",
        reason=success_key,
        next_action=NEXT_ACTIONS[success_key],
        exit_code=0,
        repo_root=root,
    )


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="algotrader development-autopilot")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--work-order-path", default=None)
    parser.add_argument("--expected-head", default=None)
    parser.add_argument("--agent-route", default=DEFAULT_AGENT_ROUTE)
    parser.add_argument("--agent-command", default=None)
    parser.add_argument("--git-mode", choices=GIT_MODES, default="verify_only")
    parser.add_argument(
        "--command-timeout-seconds",
        type=_command_timeout_seconds_arg,
        default=DEFAULT_COMMAND_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--full-pytest-policy",
        choices=FULL_PYTEST_POLICIES,
        default=FULL_PYTEST_POLICY_ALWAYS,
    )
    args = parser.parse_args(argv)

    result = run_development_autopilot(
        DevelopmentAutopilotOptions(
            output_root=Path(args.output_root),
            work_order_path=Path(args.work_order_path) if args.work_order_path else None,
            expected_head=args.expected_head,
            agent_route=args.agent_route,
            agent_command=args.agent_command,
            git_mode=args.git_mode,
            command_timeout_seconds=args.command_timeout_seconds,
            full_pytest_policy=args.full_pytest_policy,
        )
    )
    print(json.dumps(result["next_action_packet"], sort_keys=True))
    return int(result["exit_code"])


def _artifact_paths(output_root: Path) -> dict[str, Path]:
    return {
        "latest": output_root / "development_autopilot_latest.json",
        "ledger": output_root / "development_autopilot_ledger.jsonl",
        "report": output_root / "development_autopilot_report.md",
        "agent_stdout": output_root / "agent_stdout.txt",
        "agent_stderr": output_root / "agent_stderr.txt",
        "work_order_packet": output_root / "work_order_packet.json",
        "verification_results": output_root / "verification_results.json",
        "next_action_packet": output_root / "next_action_packet.json",
    }


def _ensure_empty_capture_files(artifacts: Mapping[str, Path]) -> None:
    artifacts["agent_stdout"].write_text("", encoding="utf-8")
    artifacts["agent_stderr"].write_text("", encoding="utf-8")


def _inspect_repo(repo_root: Path) -> RepoState:
    git_env = _scrubbed_env(os.environ.copy())
    branch = _git_text(repo_root, "branch", "--show-current", env=git_env)
    head = _git_text(repo_root, "rev-parse", "HEAD", env=git_env)
    origin_main_result = _run_command(
        ("git", "rev-parse", "origin/main"),
        cwd=repo_root,
        env=git_env,
    )
    origin_main = (
        origin_main_result.stdout.strip()
        if origin_main_result.exit_code == 0
        else "unavailable"
    )
    status_result = _run_command(
        ("git", "status", "--porcelain", "--untracked-files=all"),
        cwd=repo_root,
        env=git_env,
    )
    if status_result.exit_code != 0:
        raise RuntimeError("git status --porcelain failed")
    status = status_result.stdout.rstrip()
    return RepoState(
        branch=branch,
        head=head,
        origin_main=origin_main,
        status_entries=_parse_porcelain_status(status),
    )


def _git_text(repo_root: Path, *args: str, env: Mapping[str, str] | None = None) -> str:
    result = _run_command(
        ("git",) + args,
        cwd=repo_root,
        env=_scrubbed_env(os.environ.copy()) if env is None else env,
    )
    if result.exit_code != 0:
        raise RuntimeError(f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _parse_porcelain_status(status: str) -> tuple[RepoStatusEntry, ...]:
    entries: list[RepoStatusEntry] = []
    for line in status.splitlines():
        if not line:
            continue
        code = line[:2]
        path = line[3:] if len(line) > 3 else ""
        entries.append(RepoStatusEntry(code=code, path=_normalize_status_path(path)))
    return tuple(entries)


def _normalize_status_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized == "docs/reviews":
        return "docs/reviews/"
    return normalized


def _baseline_matches(repo_state: RepoState, expected_head: str) -> bool:
    return repo_state.head == expected_head and repo_state.origin_main == expected_head


def _pre_dispatch_repo_block_reason(repo_state: RepoState) -> str:
    if repo_state.branch != "main":
        return "unexpected_branch"
    unexpected_entries = [
        entry
        for entry in repo_state.status_entries
        if not _is_expected_docs_reviews_residue(entry)
    ]
    if any(entry.code != "??" and entry.code[:1] != " " for entry in unexpected_entries):
        return "staged_files_before_dispatch"
    if any(entry.code != "??" for entry in unexpected_entries):
        return "unexpected_tracked_changes_before_dispatch"
    if unexpected_entries:
        return "unexpected_untracked_files_before_dispatch"
    return ""


def _is_expected_docs_reviews_residue(entry: RepoStatusEntry) -> bool:
    return entry.code == "??" and (
        entry.path == "docs/reviews/" or entry.path.startswith("docs/reviews/")
    )


def _select_work_order_path(repo_root: Path, supplied_path: Path | None) -> Path | str | None:
    if supplied_path is not None:
        selected = _resolve_path(repo_root, supplied_path)
        return selected if selected.is_file() else "missing_work_order"

    inbox = repo_root / ".agent_inbox"
    if not inbox.is_dir():
        return None
    candidates = sorted(inbox.glob("*.json"))
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        return "multiple_work_orders_found"
    return None


def _load_work_order(path: Path) -> WorkOrder | str:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "invalid_work_order_json"
    if not isinstance(raw, dict):
        return "invalid_work_order_schema"

    validation_error = _validate_work_order_raw(raw)
    if validation_error:
        return validation_error

    prompt_result = _work_order_prompt(raw, path.parent)
    if isinstance(prompt_result, str) and prompt_result.startswith("error:"):
        return prompt_result.removeprefix("error:")
    prompt = prompt_result

    prompt_policy_error = _prompt_policy_error(prompt)
    if prompt_policy_error:
        return prompt_policy_error

    return WorkOrder(
        raw=raw,
        path=path,
        work_order_id=str(raw["work_order_id"]),
        phase=str(raw["phase"]),
        expected_head=str(raw["expected_head"]),
        agent_route=str(raw["agent_route"]),
        prompt=prompt,
        allowed_files=tuple(str(item) for item in raw["allowed_files"]),
        forbidden_paths=tuple(str(item) for item in raw["forbidden_paths"]),
        required_verification_commands=tuple(
            tuple(str(part) for part in command)
            for command in raw["required_verification_commands"]
        ),
        git_mode_allowed=tuple(str(item) for item in raw["git_mode_allowed"]),
        commit_message=str(raw["commit_message"]),
        labels=tuple(str(item) for item in raw["labels"]),
        allow_no_change_fast_path=bool(raw.get("allow_no_change_fast_path", False)),
        command_timeout_seconds=(
            int(raw["command_timeout_seconds"])
            if "command_timeout_seconds" in raw
            else None
        ),
        nonlocal_push_authorized=raw.get("nonlocal_push_authorized") is True,
    )


def _validate_work_order_raw(raw: dict[str, object]) -> str:
    for field in REQUIRED_WORK_ORDER_FIELDS:
        if field not in raw:
            return f"invalid_work_order_schema:missing_{field}"
    if "agent_prompt" not in raw and "agent_prompt_path" not in raw:
        return "invalid_work_order_schema:missing_agent_prompt"
    if str(raw["schema_version"]) not in SUPPORTED_WORK_ORDER_SCHEMA_VERSIONS:
        return "invalid_work_order_schema:unsupported_schema_version"
    for field in HARD_GATE_FIELDS:
        if raw[field] is not False:
            return f"hard_gate:{field}"
    labels = raw.get("labels")
    if not _is_string_sequence(labels):
        return "invalid_work_order_schema:labels"
    missing_labels = SAFE_REQUIRED_LABELS.difference(str(label) for label in labels)
    if missing_labels:
        return "invalid_work_order_schema:missing_required_safety_labels"
    allowed_files = raw.get("allowed_files")
    if not _is_string_sequence(allowed_files) or not allowed_files:
        return "invalid_work_order_schema:allowed_files"
    forbidden_paths = raw.get("forbidden_paths")
    if not _is_string_sequence(forbidden_paths):
        return "invalid_work_order_schema:forbidden_paths"
    path_error = _path_policy_error(
        tuple(str(path) for path in allowed_files),
        tuple(str(path) for path in forbidden_paths),
    )
    if path_error:
        return path_error
    commands = raw.get("required_verification_commands")
    if not isinstance(commands, list) or any(
        not _is_string_sequence(command) or not command for command in commands
    ):
        return "invalid_work_order_schema:required_verification_commands"
    git_modes = raw.get("git_mode_allowed")
    if not _is_string_sequence(git_modes) or any(str(mode) not in GIT_MODES for mode in git_modes):
        return "invalid_work_order_schema:git_mode_allowed"
    if "verify_only" not in {str(mode) for mode in git_modes}:
        return "invalid_work_order_schema:verify_only_git_mode_required"
    if "allow_no_change_fast_path" in raw and not isinstance(
        raw["allow_no_change_fast_path"],
        bool,
    ):
        return "invalid_work_order_schema:allow_no_change_fast_path"
    if (
        "nonlocal_push_authorized" in raw
        and raw["nonlocal_push_authorized"] is not None
        and not isinstance(raw["nonlocal_push_authorized"], bool)
    ):
        return "invalid_work_order_schema:nonlocal_push_authorized"
    if "command_timeout_seconds" in raw and _command_timeout_validation_error(
        raw["command_timeout_seconds"],
        field_name="command_timeout_seconds",
    ):
        return "invalid_work_order_schema:command_timeout_seconds"
    if not _safe_required_string(raw.get("commit_message")):
        return "invalid_work_order_schema:commit_message"
    if not _safe_required_string(raw.get("work_order_id")):
        return "invalid_work_order_schema:work_order_id"
    if not _safe_required_string(raw.get("phase")):
        return "invalid_work_order_schema:phase"
    if not _safe_required_string(raw.get("expected_head")):
        return "invalid_work_order_schema:expected_head"
    if str(raw.get("agent_route")) != DEFAULT_AGENT_ROUTE:
        return "invalid_work_order_schema:unsupported_agent_route"
    unsafe_value_error = _work_order_value_policy_error(raw)
    if unsafe_value_error:
        return unsafe_value_error
    return ""


def _work_order_prompt(raw: Mapping[str, object], base_dir: Path) -> str:
    if "agent_prompt" in raw and "agent_prompt_path" in raw:
        return "error:invalid_work_order_schema:multiple_agent_prompt_sources"
    if "agent_prompt" in raw:
        value = raw["agent_prompt"]
        return value if isinstance(value, str) and value.strip() else "error:invalid_work_order_schema:agent_prompt"

    value = raw.get("agent_prompt_path")
    if not isinstance(value, str) or not value.strip():
        return "error:invalid_work_order_schema:agent_prompt_path"
    prompt_path_error = _single_relative_file_path_error(value)
    if prompt_path_error:
        return f"error:{prompt_path_error}"
    try:
        return (base_dir / value).resolve().read_text(encoding="utf-8")
    except OSError:
        return "error:invalid_work_order_schema:agent_prompt_path_unreadable"


def _work_order_value_policy_error(raw: Mapping[str, object]) -> str:
    text_values = "\n".join(_string_values(raw))
    return _prompt_policy_error(text_values)


def _prompt_policy_error(prompt: str) -> str:
    normalized = prompt.lower()
    if any(marker in normalized for marker in SECRET_LOOKING_MARKERS):
        return "invalid_work_order_schema:secret_like_value"
    if any(marker in normalized for marker in UNAUTHORIZED_PROMPT_MARKERS):
        return "invalid_work_order_schema:unauthorized_prompt_authority"
    return ""


def _string_values(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        strings: list[str] = []
        for item in value.values():
            strings.extend(_string_values(item))
        return tuple(strings)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        strings = []
        for item in value:
            strings.extend(_string_values(item))
        return tuple(strings)
    return ()


def _path_policy_error(
    allowed_files: tuple[str, ...],
    forbidden_paths: tuple[str, ...],
) -> str:
    normalized_forbidden: list[str] = []
    for path in forbidden_paths:
        path_error = _relative_path_error(path)
        if path_error:
            return path_error
        normalized_forbidden.append(_normalize_relative_path(path, allow_directory=True))

    for path in allowed_files:
        path_error = _single_relative_file_path_error(path)
        if path_error:
            return path_error
        normalized = _normalize_relative_path(path)
        if normalized in TOO_BROAD_ALLOWED_PATHS or "*" in normalized:
            return "invalid_work_order_schema:allowed_file_too_broad"
        if _is_forbidden_path(normalized, tuple(normalized_forbidden)):
            return "invalid_work_order_schema:allowed_file_forbidden"
    return ""


def _single_relative_file_path_error(path: str) -> str:
    path_error = _relative_path_error(path)
    if path_error:
        return path_error
    normalized = _normalize_relative_path(path)
    if normalized.endswith("/") or PurePosixPath(normalized).suffix == "":
        return "invalid_work_order_schema:allowed_file_too_broad"
    return ""


def _relative_path_error(path: str) -> str:
    if not isinstance(path, str) or not path.strip():
        return "invalid_work_order_schema:empty_path"
    normalized = path.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or ":" in pure.parts[0]:
        return "invalid_work_order_schema:absolute_path"
    if ".." in pure.parts:
        return "invalid_work_order_schema:path_traversal"
    return ""


def _normalize_relative_path(path: str, *, allow_directory: bool = False) -> str:
    normalized = path.replace("\\", "/").strip()
    if allow_directory and normalized and not PurePosixPath(normalized).suffix and not normalized.endswith("/"):
        normalized += "/"
    return normalized


def _is_forbidden_path(path: str, work_order_forbidden_paths: tuple[str, ...]) -> bool:
    normalized = _normalize_relative_path(path)
    prefixes = DEFAULT_FORBIDDEN_PATH_PREFIXES + tuple(
        _normalize_relative_path(item, allow_directory=True)
        for item in work_order_forbidden_paths
    )
    if any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in prefixes):
        return True
    if normalized.endswith(".csv") and (
        "operator" in normalized.lower() or "market" in normalized.lower()
    ):
        return True
    return False


def _is_string_sequence(value: object) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(item, str) and item.strip() for item in value)
    )


def _safe_required_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _resolve_agent_command(agent_route: str, agent_command: str | None) -> tuple[str, ...] | None:
    if agent_route != DEFAULT_AGENT_ROUTE:
        return None
    if agent_command:
        command = tuple(shlex.split(agent_command, posix=os.name != "nt"))
        return command or None
    discovered = shutil.which(DEFAULT_AGENT_ROUTE)
    return (discovered,) if discovered else None


def _invoke_agent(
    repo_root: Path,
    command: tuple[str, ...],
    prompt: str,
    stdout_path: Path,
    stderr_path: Path,
    env: Mapping[str, str],
    *,
    timeout_seconds: int,
) -> CommandResult:
    child_env = _scrubbed_env(env)
    started = _utc_now_text()
    start_time = time.monotonic()
    timed_out = False
    exit_code = 0
    with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open(
        "w",
        encoding="utf-8",
    ) as stderr_file:
        try:
            completed = subprocess.run(
                command,
                cwd=repo_root,
                env=child_env,
                input=prompt,
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
                check=False,
                timeout=timeout_seconds,
            )
            exit_code = completed.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            exit_code = -1
    ended = _utc_now_text()
    return CommandResult(
        command=command,
        exit_code=exit_code,
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        started_at=started,
        ended_at=ended,
        elapsed_seconds=round(time.monotonic() - start_time, 6),
        timed_out=timed_out,
        timeout_seconds=timeout_seconds,
        reason="agent_command_timeout" if timed_out else "",
        command_kind="agent",
    )


def _repository_verification_commands(
    override: tuple[tuple[str, ...], ...] | None,
) -> tuple[tuple[str, ...], ...]:
    if override is not None:
        return override
    return (
        (
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_dependency_direction.py",
            "tests/unit/test_broker_mutation_surface_invariant.py",
            "tests/unit/test_default_pytest_network_guard.py",
            "-q",
        ),
        (
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts\\verify_offline.ps1",
        ),
        (sys.executable, "-m", "pytest"),
    )


def _repository_verification_plan(
    override: tuple[tuple[str, ...], ...] | None,
) -> RepositoryVerificationPlan:
    commands = _repository_verification_commands(override)
    if not commands:
        return RepositoryVerificationPlan(
            safety_guard_commands=(),
            verify_offline_command=None,
            full_pytest_command=None,
        )
    if override is None:
        return RepositoryVerificationPlan(
            safety_guard_commands=(commands[0],),
            verify_offline_command=commands[1],
            full_pytest_command=commands[2],
        )
    if len(commands) == 1:
        return RepositoryVerificationPlan(
            safety_guard_commands=(),
            verify_offline_command=None,
            full_pytest_command=commands[0],
        )
    if len(commands) == 2:
        return RepositoryVerificationPlan(
            safety_guard_commands=(),
            verify_offline_command=commands[0],
            full_pytest_command=commands[1],
        )
    return RepositoryVerificationPlan(
        safety_guard_commands=commands[:-2],
        verify_offline_command=commands[-2],
        full_pytest_command=commands[-1],
    )


def _run_verification_commands(
    repo_root: Path,
    output_root: Path,
    commands: tuple[tuple[str, ...], ...],
    env: Mapping[str, str],
    *,
    timeout_seconds: int,
    command_kind: str,
    timeout_reason: str,
    start_index: int = 1,
) -> tuple[CommandResult, ...]:
    results: list[CommandResult] = []
    for index, command in enumerate(commands, start=start_index):
        stdout_path = output_root / f"verification_{index:02d}_stdout.txt"
        stderr_path = output_root / f"verification_{index:02d}_stderr.txt"
        started = _utc_now_text()
        start_time = time.monotonic()
        timed_out = False
        exit_code = 0
        with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open(
            "w",
            encoding="utf-8",
        ) as stderr_file:
            try:
                completed = subprocess.run(
                    command,
                    cwd=repo_root,
                    env=_scrubbed_env(env),
                    stdout=stdout_file,
                    stderr=stderr_file,
                    text=True,
                    check=False,
                    timeout=timeout_seconds,
                )
                exit_code = completed.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                exit_code = -1
        ended = _utc_now_text()
        results.append(
            CommandResult(
                command=command,
                exit_code=exit_code,
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                started_at=started,
                ended_at=ended,
                elapsed_seconds=round(time.monotonic() - start_time, 6),
                timed_out=timed_out,
                timeout_seconds=timeout_seconds,
                reason=timeout_reason if timed_out else "",
                command_kind=command_kind,
            )
        )
        if timed_out:
            break
    return tuple(results)


def _run_command(
    command: tuple[str, ...],
    *,
    cwd: Path,
    env: Mapping[str, str],
) -> CommandResult:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return CommandResult(
        command=command,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _command_timeout_validation_error(value: object, *, field_name: str) -> str:
    if isinstance(value, bool) or not isinstance(value, int):
        return f"invalid_{field_name}"
    if not MIN_COMMAND_TIMEOUT_SECONDS <= value <= MAX_COMMAND_TIMEOUT_SECONDS:
        return f"invalid_{field_name}"
    return ""


def _command_timeout_seconds_arg(value: str) -> int:
    import argparse

    try:
        timeout_seconds = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "command timeout must be an integer number of seconds"
        ) from exc
    if _command_timeout_validation_error(
        timeout_seconds,
        field_name="command_timeout_seconds",
    ):
        raise argparse.ArgumentTypeError(
            "command timeout must be between "
            f"{MIN_COMMAND_TIMEOUT_SECONDS} and {MAX_COMMAND_TIMEOUT_SECONDS} seconds"
        )
    return timeout_seconds


def _effective_command_timeout_seconds(
    cli_timeout_seconds: int,
    work_order_timeout_seconds: int | None,
) -> int:
    if work_order_timeout_seconds is None:
        return cli_timeout_seconds
    return min(cli_timeout_seconds, work_order_timeout_seconds)


def _update_verification_record(
    record: dict[str, object],
    results: tuple[CommandResult, ...],
) -> None:
    record["verification_commands"] = [
        _command_result_record(result) for result in results
    ]
    record["safety_guard_statuses"] = _safety_guard_statuses(results)
    if any(result.timed_out for result in results):
        record["verification_timeout"] = True


def _first_timed_out(results: tuple[CommandResult, ...]) -> CommandResult | None:
    return next((result for result in results if result.timed_out), None)


def _first_failed(results: tuple[CommandResult, ...]) -> CommandResult | None:
    return next(
        (result for result in results if result.exit_code != 0 and not result.timed_out),
        None,
    )


def _record_verification_timeout(record: dict[str, object], reason: str) -> None:
    record["verification_timeout"] = True
    record["verification_timeout_reason"] = reason


def _no_change_fast_path_allowed(
    full_pytest_policy: str,
    git_mode: str,
    work_order: WorkOrder,
) -> bool:
    return (
        full_pytest_policy == FULL_PYTEST_POLICY_CHANGED_FILES_ONLY
        and git_mode == "verify_only"
        and work_order.allow_no_change_fast_path
    )


def _should_use_no_change_fast_path(
    *,
    full_pytest_policy: str,
    git_mode: str,
    work_order: WorkOrder,
    agent_result: CommandResult,
    targeted_results: tuple[CommandResult, ...],
    safety_guard_results: tuple[CommandResult, ...],
    verify_offline_results: tuple[CommandResult, ...],
    repo_state: RepoState,
    repository_plan: RepositoryVerificationPlan,
) -> bool:
    return (
        _no_change_fast_path_allowed(full_pytest_policy, git_mode, work_order)
        and repository_plan.full_pytest_command is not None
        and agent_result.exit_code == 0
        and not agent_result.timed_out
        and bool(targeted_results)
        and _all_commands_passed(targeted_results)
        and bool(safety_guard_results)
        and _all_commands_passed(safety_guard_results)
        and bool(verify_offline_results)
        and _all_commands_passed(verify_offline_results)
        and not repo_state.relevant_changed_files
        and not repo_state.staged_files
        and not _repo_status_has_forbidden_runtime_artifact(repo_state)
    )


def _all_commands_passed(results: tuple[CommandResult, ...]) -> bool:
    return all(result.exit_code == 0 and not result.timed_out for result in results)


def _repo_status_has_forbidden_runtime_artifact(repo_state: RepoState) -> bool:
    return any(
        not _is_expected_docs_reviews_residue(entry)
        and _is_forbidden_path(entry.path, ())
        for entry in repo_state.status_entries
    )


def _changed_file_policy_reason(
    changed_files: tuple[str, ...],
    *,
    allowed_files: tuple[str, ...],
    forbidden_paths: tuple[str, ...],
) -> str:
    allowed = {_normalize_relative_path(path) for path in allowed_files}
    forbidden = tuple(_normalize_relative_path(path, allow_directory=True) for path in forbidden_paths)
    for path in changed_files:
        normalized = _normalize_relative_path(path)
        if _is_forbidden_path(normalized, forbidden):
            return "changed_file_forbidden_path"
        if normalized not in allowed:
            return "changed_file_not_allowed"
    return ""


def _perform_git_mutation(
    repo_root: Path,
    work_order: WorkOrder,
    git_mode: str,
    changed_files: tuple[str, ...],
    expected_head: str,
    repo_state: RepoState,
    env: Mapping[str, str],
) -> dict[str, object]:
    record = _empty_git_mutation_record()
    if not changed_files:
        return {"ok": False, "reason": "no_changed_files_to_commit", "record": record}
    if repo_state.staged_files:
        return {"ok": False, "reason": "staged_files_before_git_mutation", "record": record}
    if expected_head and not _baseline_matches(repo_state, expected_head):
        return {"ok": False, "reason": "baseline_mismatch_before_git_mutation", "record": record}

    git_env = _scrubbed_env(env)
    if git_mode == "commit_and_push":
        remote_name = "origin"
        record.update(
            _push_authorization_record(
                work_order,
                _push_remote_provenance(repo_root, remote_name, env=git_env),
            )
        )
        if record["push_authorization_blocker"]:
            return {
                "ok": False,
                "reason": record["push_authorization_blocker"],
                "record": record,
            }

    add_result = _run_command(("git", "add", "--") + changed_files, cwd=repo_root, env=git_env)
    if add_result.exit_code != 0:
        return {"ok": False, "reason": "git_add_failed", "record": record}
    record["staging_occurred"] = True
    record["staged_files"] = list(
        _git_file_list(repo_root, "diff", "--cached", "--name-only", "--", env=git_env)
    )

    commit_result = _run_command(
        ("git", "commit", "-m", work_order.commit_message),
        cwd=repo_root,
        env=git_env,
    )
    if commit_result.exit_code != 0:
        return {"ok": False, "reason": "git_commit_failed", "record": record}
    record["commit_occurred"] = True
    record["committed_files"] = list(
        _git_file_list(
            repo_root,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            "HEAD",
            env=git_env,
        )
    )

    if git_mode == "commit_and_push":
        remote_name = "origin"
        origin_main = _git_text(repo_root, "rev-parse", "origin/main")
        if expected_head and origin_main != expected_head:
            return {"ok": False, "reason": "origin_main_changed_before_push", "record": record}
        branch = _git_text(repo_root, "branch", "--show-current")
        push_result = _run_command(
            ("git", "push", remote_name, branch),
            cwd=repo_root,
            env=git_env,
        )
        if push_result.exit_code != 0:
            return {"ok": False, "reason": "git_push_failed", "record": record}
        record["push_occurred"] = True

    return {"ok": True, "reason": "", "record": record}


def _empty_git_mutation_record() -> dict[str, object]:
    return {
        "staging_occurred": False,
        "commit_occurred": False,
        "push_occurred": False,
        "staged_files": [],
        "committed_files": [],
        "push_remote_name": "",
        "push_remote_url_sanitized": "",
        "push_remote_url_kind": "unknown",
        "push_remote_url_is_network": False,
        "push_remote_url_is_local_path": False,
        "push_remote_url_redacted": False,
        "nonlocal_push_authorized": False,
        "push_authorization_required": False,
        "push_authorization_status": "not_applicable",
        "push_authorization_blocker": None,
    }


def _push_authorization_record(
    work_order: WorkOrder,
    provenance: Mapping[str, object],
) -> dict[str, object]:
    record = dict(provenance)
    authorized = work_order.nonlocal_push_authorized
    record["nonlocal_push_authorized"] = authorized

    kind = str(record.get("push_remote_url_kind", "unknown"))
    if kind == "local_path":
        record["push_authorization_required"] = False
        record["push_authorization_status"] = "local_remote_allowed"
        record["push_authorization_blocker"] = None
    elif kind == "network":
        record["push_authorization_required"] = True
        if authorized:
            record["push_authorization_status"] = "network_remote_authorized"
            record["push_authorization_blocker"] = None
        else:
            record["push_authorization_status"] = "blocked_network_remote_not_authorized"
            record["push_authorization_blocker"] = "network_push_not_authorized"
    else:
        record["push_authorization_required"] = True
        record["push_authorization_status"] = "blocked_unknown_remote"
        record["push_authorization_blocker"] = "push_remote_unknown"

    return record


def _git_file_list(
    repo_root: Path,
    *args: str,
    env: Mapping[str, str],
) -> tuple[str, ...]:
    output = _git_text(repo_root, *args, env=env)
    if not output:
        return ()
    return tuple(line for line in output.splitlines() if line)


def _push_remote_provenance(
    repo_root: Path,
    remote_name: str,
    *,
    env: Mapping[str, str],
) -> dict[str, object]:
    remote_url = ""
    result = _run_command(
        ("git", "config", "--get", f"remote.{remote_name}.url"),
        cwd=repo_root,
        env=env,
    )
    if result.exit_code == 0:
        remote_url = result.stdout.strip()
    sanitized_url, redacted = _sanitize_remote_url(remote_url)
    kind = _remote_url_kind(remote_url)
    return {
        "push_remote_name": remote_name,
        "push_remote_url_sanitized": sanitized_url,
        "push_remote_url_kind": kind,
        "push_remote_url_is_network": kind == "network",
        "push_remote_url_is_local_path": kind == "local_path",
        "push_remote_url_redacted": redacted,
    }


def _sanitize_remote_url(remote_url: str) -> tuple[str, bool]:
    value = remote_url.strip()
    if not value:
        return "", False

    if "://" in value:
        scheme, remainder = value.split("://", 1)
        netloc, suffix = _split_url_authority(remainder)
        redacted = False
        if "@" in netloc:
            netloc = f"<redacted>@{netloc.rsplit('@', 1)[1]}"
            redacted = True
        sanitized_suffix, suffix_redacted = _sanitize_url_suffix(suffix)
        return f"{scheme}://{netloc}{sanitized_suffix}", redacted or suffix_redacted

    if _looks_like_scp_remote(value):
        user_host, separator, remote_path = value.partition(":")
        if "@" in user_host:
            host = user_host.rsplit("@", 1)[1]
            return f"<redacted>@{host}{separator}{remote_path}", True

    return value, False


def _remote_url_kind(remote_url: str) -> str:
    value = remote_url.strip()
    if not value:
        return "unknown"
    if _looks_like_local_remote(value):
        return "local_path"
    if _looks_like_network_remote(value):
        return "network"
    return "unknown"


def _looks_like_local_remote(remote_url: str) -> bool:
    value = remote_url.strip()
    if value.lower().startswith("file://"):
        return True
    if _has_windows_drive_prefix(value):
        return True
    return value.startswith(("/", "\\", "./", "../"))


def _looks_like_network_remote(remote_url: str) -> bool:
    value = remote_url.strip()
    if "://" in value:
        return _url_scheme(value) in {"git", "http", "https", "ssh", "rsync"}
    return _looks_like_scp_remote(value)


def _looks_like_scp_remote(remote_url: str) -> bool:
    value = remote_url.strip()
    if "://" in value or _has_windows_drive_prefix(value):
        return False
    before_colon, separator, after_colon = value.partition(":")
    if not separator or not before_colon or not after_colon:
        return False
    return "/" not in before_colon and "\\" not in before_colon


def _has_windows_drive_prefix(remote_url: str) -> bool:
    return (
        len(remote_url) >= 3
        and remote_url[0].isalpha()
        and remote_url[1] == ":"
        and remote_url[2] in {"/", "\\"}
    )


def _url_scheme(remote_url: str) -> str:
    return remote_url.split("://", 1)[0].lower()


def _split_url_authority(remainder: str) -> tuple[str, str]:
    suffix_indexes = [
        index
        for separator in ("/", "?", "#")
        if (index := remainder.find(separator)) != -1
    ]
    if not suffix_indexes:
        return remainder, ""
    split_at = min(suffix_indexes)
    return remainder[:split_at], remainder[split_at:]


def _sanitize_url_suffix(suffix: str) -> tuple[str, bool]:
    suffix_indexes = [
        index
        for separator in ("?", "#")
        if (index := suffix.find(separator)) != -1
    ]
    if not suffix_indexes:
        return suffix, False
    path = suffix[: min(suffix_indexes)]
    sanitized = path
    if "?" in suffix:
        sanitized += "?<redacted>"
    if "#" in suffix:
        sanitized += "#<redacted>"
    return sanitized, True


def _finish(
    artifacts: Mapping[str, Path],
    record: dict[str, object],
    *,
    outcome: str,
    reason: str,
    next_action: str,
    exit_code: int,
    repo_root: Path,
) -> dict[str, object]:
    repo_after = _inspect_repo(repo_root)
    record["ending_head"] = repo_after.head
    record["origin_main_after"] = repo_after.origin_main
    record["dirty_state_after"] = repo_after.as_summary()
    record["changed_files"] = list(repo_after.relevant_changed_files)
    record["final_classification"] = outcome
    record["outcome"] = outcome
    record["reason"] = reason
    record["exact_next_action"] = next_action
    record["completed_at"] = _utc_now_text()

    next_action_packet = {
        "schema_version": SCHEMA_VERSION,
        "run_id": record["run_id"],
        "outcome": outcome,
        "reason": reason,
        "next_action": next_action,
        "work_order_id": record.get("work_order_id", ""),
        "command_timeout_seconds": record.get("command_timeout_seconds"),
        "full_pytest_policy": record.get("full_pytest_policy"),
        "full_pytest_required": record.get("full_pytest_required"),
        "full_pytest_status": record.get("full_pytest_status"),
        "no_change_fast_path_used": record.get("no_change_fast_path_used"),
    }
    latest = dict(record)
    latest["next_action_packet"] = next_action_packet
    latest["artifact_paths"] = {name: str(path) for name, path in artifacts.items()}

    _write_json_file(artifacts["verification_results"], _verification_results_payload(record))
    _write_json_file(artifacts["latest"], latest)
    _append_jsonl(artifacts["ledger"], record)
    _write_json_file(artifacts["next_action_packet"], next_action_packet)
    _write_report(artifacts["report"], latest)
    return {
        "exit_code": exit_code,
        "outcome": outcome,
        "reason": reason,
        "next_action_packet": next_action_packet,
        "latest": latest,
    }


def _verification_results_payload(record: Mapping[str, object]) -> dict[str, object]:
    return {
        "commands": list(record.get("verification_commands", [])),
        "command_timeout_seconds": record.get("command_timeout_seconds"),
        "agent_timeout": record.get("agent_timeout"),
        "verification_timeout": record.get("verification_timeout"),
        "verification_timeout_reason": record.get("verification_timeout_reason"),
        "safety_guard_statuses": record.get("safety_guard_statuses", {}),
        "verify_offline_status": record.get("verify_offline_status"),
        "full_pytest_policy": record.get("full_pytest_policy"),
        "full_pytest_required": record.get("full_pytest_required"),
        "full_pytest_status": record.get("full_pytest_status"),
        "full_pytest_exit_code": record.get("full_pytest_exit_code"),
        "full_pytest_elapsed_seconds": record.get("full_pytest_elapsed_seconds"),
        "full_pytest_skipped_reason": record.get("full_pytest_skipped_reason"),
        "no_change_fast_path_allowed": record.get("no_change_fast_path_allowed"),
        "no_change_fast_path_used": record.get("no_change_fast_path_used"),
        "normal_pytest_offline_invariant_preserved": record.get(
            "normal_pytest_offline_invariant_preserved"
        ),
        "staging_occurred": record.get("staging_occurred", False),
        "commit_occurred": record.get("commit_occurred", False),
        "push_occurred": record.get("push_occurred", False),
        "staged_files": list(record.get("staged_files", [])),
        "committed_files": list(record.get("committed_files", [])),
        "push_remote_name": record.get("push_remote_name", ""),
        "push_remote_url_sanitized": record.get("push_remote_url_sanitized", ""),
        "push_remote_url_kind": record.get("push_remote_url_kind", "unknown"),
        "push_remote_url_is_network": record.get("push_remote_url_is_network", False),
        "push_remote_url_is_local_path": record.get(
            "push_remote_url_is_local_path",
            False,
        ),
        "push_remote_url_redacted": record.get("push_remote_url_redacted", False),
        "nonlocal_push_authorized": record.get("nonlocal_push_authorized", False),
        "push_authorization_required": record.get(
            "push_authorization_required",
            False,
        ),
        "push_authorization_status": record.get(
            "push_authorization_status",
            "not_applicable",
        ),
        "push_authorization_blocker": record.get("push_authorization_blocker"),
    }


def _write_report(path: Path, latest: Mapping[str, object]) -> None:
    lines = [
        "# Development Autopilot Report",
        "",
        f"run_id: {latest.get('run_id', '')}",
        f"outcome: {latest.get('outcome', '')}",
        f"reason: {latest.get('reason', '')}",
        f"next_action: {latest.get('exact_next_action', '')}",
        f"git_mode: {latest.get('git_mode', '')}",
        f"staging_occurred: {latest.get('staging_occurred', '')}",
        f"commit_occurred: {latest.get('commit_occurred', '')}",
        f"push_occurred: {latest.get('push_occurred', '')}",
        f"staged_files: {json.dumps(latest.get('staged_files', []), sort_keys=True)}",
        f"committed_files: {json.dumps(latest.get('committed_files', []), sort_keys=True)}",
        f"push_remote_name: {latest.get('push_remote_name', '')}",
        f"push_remote_url_sanitized: {latest.get('push_remote_url_sanitized', '')}",
        f"push_remote_url_kind: {latest.get('push_remote_url_kind', '')}",
        f"push_remote_url_is_network: {latest.get('push_remote_url_is_network', '')}",
        f"push_remote_url_is_local_path: {latest.get('push_remote_url_is_local_path', '')}",
        f"push_remote_url_redacted: {latest.get('push_remote_url_redacted', '')}",
        f"nonlocal_push_authorized: {latest.get('nonlocal_push_authorized', '')}",
        f"push_authorization_required: {latest.get('push_authorization_required', '')}",
        f"push_authorization_status: {latest.get('push_authorization_status', '')}",
        f"push_authorization_blocker: {latest.get('push_authorization_blocker', '')}",
        f"work_order_id: {latest.get('work_order_id', '')}",
        f"route_name: {latest.get('route_name', '')}",
        f"agent_exit_code: {latest.get('agent_exit_code', '')}",
        f"command_timeout_seconds: {latest.get('command_timeout_seconds', '')}",
        f"agent_timeout: {latest.get('agent_timeout', '')}",
        f"verification_timeout: {latest.get('verification_timeout', '')}",
        f"verification_timeout_reason: {latest.get('verification_timeout_reason', '')}",
        f"full_pytest_policy: {latest.get('full_pytest_policy', '')}",
        f"full_pytest_required: {latest.get('full_pytest_required', '')}",
        f"full_pytest_status: {latest.get('full_pytest_status', '')}",
        f"full_pytest_exit_code: {latest.get('full_pytest_exit_code', '')}",
        f"full_pytest_elapsed_seconds: {latest.get('full_pytest_elapsed_seconds', '')}",
        f"full_pytest_skipped_reason: {latest.get('full_pytest_skipped_reason', '')}",
        f"no_change_fast_path_allowed: {latest.get('no_change_fast_path_allowed', '')}",
        f"no_change_fast_path_used: {latest.get('no_change_fast_path_used', '')}",
        "normal_pytest_offline_invariant_preserved: "
        f"{latest.get('normal_pytest_offline_invariant_preserved', '')}",
        "",
        "Safety:",
        "broker_read_attempted: false",
        "broker_mutation_attempted: false",
        "paper_submit_attempted: false",
        "live_trading_attempted: false",
        "capital_operation_attempted: false",
        "credential_access_attempted: false",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _sanitized_work_order_packet(work_order: WorkOrder) -> dict[str, object]:
    packet = dict(work_order.raw)
    packet["nonlocal_push_authorized"] = work_order.nonlocal_push_authorized
    if "agent_prompt" in packet:
        packet["agent_prompt_sha256"] = hashlib.sha256(work_order.prompt.encode("utf-8")).hexdigest()
        packet["agent_prompt"] = "<captured-by-hash>"
    return packet


def _preflight_booleans(env: Mapping[str, str]) -> dict[str, bool]:
    return {
        "APP_PROFILE_is_paper": env.get("APP_PROFILE") == "paper",
        "ALPACA_API_KEY_loaded": "ALPACA_API_KEY" in env,
        "ALPACA_API_SECRET_KEY_loaded": "ALPACA_API_SECRET_KEY" in env,
        "ALPACA_SECRET_KEY_loaded": "ALPACA_SECRET_KEY" in env,
        "APCA_API_KEY_ID_loaded": "APCA_API_KEY_ID" in env,
        "APCA_API_SECRET_KEY_loaded": "APCA_API_SECRET_KEY" in env,
    }


def _blocking_preflight_reason(env: Mapping[str, str]) -> str:
    booleans = _preflight_booleans(env)
    if booleans["APP_PROFILE_is_paper"]:
        return "APP_PROFILE_is_paper"
    loaded = [name for name, loaded in booleans.items() if name.endswith("_loaded") and loaded]
    if loaded:
        return "credential_environment_loaded"
    return ""


def _scrubbed_env(env: Mapping[str, str]) -> dict[str, str]:
    scrubbed = dict(env)
    for name in SCRUBBED_ENV_VARS:
        scrubbed.pop(name, None)
    return scrubbed


def _command_result_record(result: CommandResult) -> dict[str, object]:
    return {
        "command": list(result.command),
        "sanitized_command_identity": _sanitized_command_identity(result.command),
        "exit_code": result.exit_code,
        "stdout_path": result.stdout_path,
        "stderr_path": result.stderr_path,
        "started_at": result.started_at,
        "ended_at": result.ended_at,
        "elapsed_seconds": result.elapsed_seconds,
        "timed_out": result.timed_out,
        "timeout_seconds": result.timeout_seconds,
        "reason": result.reason,
        "command_kind": result.command_kind,
    }


def _safety_guard_statuses(results: tuple[CommandResult, ...]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for result in results:
        command_text = " ".join(result.command)
        status = (
            "timeout"
            if result.timed_out
            else "passed"
            if result.exit_code == 0
            else "failed"
        )
        if result.command_kind == "safety_guard":
            statuses.setdefault("safety_guard", status)
        if "test_dependency_direction.py" in command_text:
            statuses["dependency_direction"] = status
        if "test_default_pytest_network_guard.py" in command_text:
            statuses["network_guard"] = status
        if "test_broker_mutation_surface_invariant.py" in command_text:
            statuses["broker_mutation_surface"] = status
    return statuses


def _command_hash(command: tuple[str, ...]) -> str:
    return hashlib.sha256("\0".join(command).encode("utf-8")).hexdigest()


def _sanitized_command_identity(command: tuple[str, ...]) -> str:
    if not command:
        return ""
    first = Path(command[0]).name or command[0]
    return " ".join((first,) + tuple("<arg>" for _ in command[1:]))


def _resolve_path(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (repo_root / path).resolve()


def _write_json_file(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _append_jsonl(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")


def _utc_now_text() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_id(started_at: str) -> str:
    normalized = started_at.replace(":", "").replace("-", "").replace("Z", "z")
    return f"development_autopilot_{normalized}"


if __name__ == "__main__":
    raise SystemExit(main())
