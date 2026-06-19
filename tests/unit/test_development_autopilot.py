from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import algotrader.development_autopilot as development_autopilot
from algotrader.cli import build_parser
from algotrader.development_autopilot import (
    DevelopmentAutopilotOptions,
    NEXT_ACTIONS,
    run_development_autopilot,
)


SAFE_LABELS = [
    "development_autopilot_only",
    "non_capital_work",
    "offline_verification_required",
    "not_live_authorized",
    "broker_mutation_forbidden",
    "paper_submit_forbidden",
    "profit_claim=none",
]
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


def test_cli_parser_registers_development_autopilot_command() -> None:
    args = build_parser().parse_args(
        [
            "development-autopilot",
            "--output-root",
            "runs/dev",
            "--work-order-path",
            "work-order.json",
            "--expected-head",
            "abc",
            "--agent-route",
            "codex",
            "--agent-command",
            "fake-codex",
            "--git-mode",
            "verify_only",
            "--command-timeout-seconds",
            "120",
            "--full-pytest-policy",
            "changed_files_only",
        ]
    )

    assert args.command == "development-autopilot"
    assert args.output_root == "runs/dev"
    assert args.work_order_path == "work-order.json"
    assert args.expected_head == "abc"
    assert args.agent_route == "codex"
    assert args.agent_command == "fake-codex"
    assert args.git_mode == "verify_only"
    assert args.command_timeout_seconds == 120
    assert args.full_pytest_policy == "changed_files_only"


def test_cli_parser_accepts_full_pytest_policy_always() -> None:
    args = build_parser().parse_args(
        ["development-autopilot", "--full-pytest-policy", "always"]
    )

    assert args.full_pytest_policy == "always"


def test_cli_parser_accepts_full_pytest_policy_changed_files_only() -> None:
    args = build_parser().parse_args(
        ["development-autopilot", "--full-pytest-policy", "changed_files_only"]
    )

    assert args.full_pytest_policy == "changed_files_only"


def test_cli_parser_rejects_invalid_full_pytest_policy() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            ["development-autopilot", "--full-pytest-policy", "sometimes"]
        )


def test_baseline_match_and_clean_repo_state_allows_dispatch(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    output_root = tmp_path / "out"
    allowed_file = "src/allowed.py"
    work_order = _write_work_order(tmp_path, head, allowed_files=[allowed_file])
    agent = _fake_agent(tmp_path, write_path=allowed_file)

    result = _run(repo, output_root, work_order, head, agent)

    assert result["exit_code"] == 0
    assert result["outcome"] == "accepted"
    assert result["next_action_packet"]["next_action"] == NEXT_ACTIONS["verify_only_success"]
    assert (repo / allowed_file).read_text(encoding="utf-8") == "build-output\n"
    latest = _read_json(output_root / "development_autopilot_latest.json")
    assert latest["allowed_files_result"] == "passed"
    assert latest["forbidden_path_result"] == "passed"
    assert latest["agent_exit_code"] == 0
    assert (output_root / "agent_stdout.txt").read_text(encoding="utf-8") == "agent stdout\n"
    assert (output_root / "agent_stderr.txt").read_text(encoding="utf-8") == "agent stderr\n"
    assert _git(repo, "diff", "--cached", "--name-only") == ""


def test_baseline_mismatch_blocks_before_dispatch(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    allowed_file = "src/allowed.py"
    work_order = _write_work_order(tmp_path, head, allowed_files=[allowed_file])
    agent = _fake_agent(tmp_path, write_path=allowed_file)

    result = _run(repo, tmp_path / "out", work_order, "0" * 40, agent)

    assert result["exit_code"] == 2
    assert result["outcome"] == "blocked"
    assert result["reason"] == "baseline_mismatch"
    assert result["next_action_packet"]["next_action"] == NEXT_ACTIONS["repository_state"]
    assert not (repo / allowed_file).exists()


def test_unexpected_dirty_tracked_file_blocks_before_dispatch(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    (repo / "README.md").write_text("dirty\n", encoding="utf-8")
    work_order = _write_work_order(tmp_path, head)
    agent = _fake_agent(tmp_path)

    result = _run(repo, tmp_path / "out", work_order, head, agent)

    assert result["reason"] == "unexpected_tracked_changes_before_dispatch"
    assert result["next_action_packet"]["next_action"] == NEXT_ACTIONS["repository_state"]


def test_unexpected_untracked_source_file_blocks_before_dispatch(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    (repo / "src" / "new_source.py").write_text("x = 1\n", encoding="utf-8")
    work_order = _write_work_order(tmp_path, head)
    agent = _fake_agent(tmp_path)

    result = _run(repo, tmp_path / "out", work_order, head, agent)

    assert result["reason"] == "unexpected_untracked_files_before_dispatch"
    assert result["next_action_packet"]["next_action"] == NEXT_ACTIONS["repository_state"]


def test_expected_docs_reviews_residue_is_recognized_and_not_touched(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    review_path = repo / "docs" / "reviews" / "note.md"
    review_path.parent.mkdir(parents=True)
    review_path.write_text("operator residue\n", encoding="utf-8")
    allowed_file = "src/allowed.py"
    work_order = _write_work_order(tmp_path, head, allowed_files=[allowed_file])
    agent = _fake_agent(tmp_path, write_path=allowed_file)

    result = _run(repo, tmp_path / "out", work_order, head, agent)

    assert result["outcome"] == "accepted"
    before = result["latest"]["dirty_state_before"]
    assert before["expected_docs_reviews_residue_present"] is True
    assert review_path.read_text(encoding="utf-8") == "operator residue\n"


def test_staged_files_before_dispatch_block(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    staged = repo / "src" / "staged.py"
    staged.write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "src/staged.py")
    work_order = _write_work_order(tmp_path, head)
    agent = _fake_agent(tmp_path)

    result = _run(repo, tmp_path / "out", work_order, head, agent)

    assert result["reason"] == "staged_files_before_dispatch"
    assert result["next_action_packet"]["next_action"] == NEXT_ACTIONS["repository_state"]


def test_missing_work_order_blocks_with_exact_next_action(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)

    result = run_development_autopilot(
        DevelopmentAutopilotOptions(
            output_root=tmp_path / "out",
            expected_head=head,
            agent_command=str(_fake_agent(tmp_path)),
            repository_verification_commands=(),
        ),
        repo_root=repo,
        env=_safe_env(),
    )

    assert result["exit_code"] == 2
    assert result["reason"] == "missing_work_order"
    assert result["next_action_packet"] == {
        "schema_version": "1.0",
        "run_id": result["next_action_packet"]["run_id"],
        "outcome": "blocked",
        "reason": "missing_work_order",
        "next_action": NEXT_ACTIONS["work_order"],
        "work_order_id": "",
        "command_timeout_seconds": 1800,
        "full_pytest_policy": "always",
        "full_pytest_required": True,
        "full_pytest_status": "not_started",
        "no_change_fast_path_used": False,
    }


def test_invalid_work_order_schema_blocks(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    work_order = tmp_path / "invalid.json"
    work_order.write_text(json.dumps({"schema_version": "1.0"}), encoding="utf-8")

    result = _run(repo, tmp_path / "out", work_order, head, _fake_agent(tmp_path))

    assert result["outcome"] == "blocked"
    assert result["reason"].startswith("invalid_work_order_schema:")
    assert result["next_action_packet"]["next_action"] == NEXT_ACTIONS["work_order"]


def test_missing_allow_no_change_fast_path_defaults_to_false(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    work_order = _write_work_order(tmp_path, head)
    agent = _fake_agent(tmp_path)

    result = _run(
        repo,
        tmp_path / "out",
        work_order,
        head,
        agent,
        full_pytest_policy="changed_files_only",
    )

    assert result["outcome"] == "accepted"
    assert result["latest"]["no_change_fast_path_allowed"] is False
    assert result["latest"]["no_change_fast_path_used"] is False


def test_non_boolean_allow_no_change_fast_path_rejects_work_order(
    tmp_path: Path,
) -> None:
    repo, head = _make_repo(tmp_path)
    work_order = _write_work_order(
        tmp_path,
        head,
        overrides={"allow_no_change_fast_path": "true"},
    )

    result = _run(repo, tmp_path / "out", work_order, head, _fake_agent(tmp_path))

    assert result["outcome"] == "blocked"
    assert result["reason"] == "invalid_work_order_schema:allow_no_change_fast_path"
    assert not result["latest"]["route_available"]


def test_work_order_timeout_value_must_be_positive_integer(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    work_order = _write_work_order(
        tmp_path,
        head,
        overrides={"command_timeout_seconds": 1},
    )

    result = _run(repo, tmp_path / "out", work_order, head, _fake_agent(tmp_path))

    assert result["outcome"] == "accepted"
    assert result["latest"]["command_timeout_seconds"] == 1
    assert result["latest"]["work_order_command_timeout_seconds"] == 1


@pytest.mark.parametrize("value", [0, -1, "10"])
def test_invalid_work_order_timeout_value_rejects_work_order(
    tmp_path: Path,
    value: object,
) -> None:
    repo, head = _make_repo(tmp_path)
    work_order = _write_work_order(
        tmp_path,
        head,
        overrides={"command_timeout_seconds": value},
    )

    result = _run(repo, tmp_path / "out", work_order, head, _fake_agent(tmp_path))

    assert result["outcome"] == "blocked"
    assert result["reason"] == "invalid_work_order_schema:command_timeout_seconds"


def test_excessive_work_order_timeout_value_rejects_work_order(
    tmp_path: Path,
) -> None:
    repo, head = _make_repo(tmp_path)
    work_order = _write_work_order(
        tmp_path,
        head,
        overrides={"command_timeout_seconds": 7201},
    )

    result = _run(repo, tmp_path / "out", work_order, head, _fake_agent(tmp_path))

    assert result["outcome"] == "blocked"
    assert result["reason"] == "invalid_work_order_schema:command_timeout_seconds"


@pytest.mark.parametrize("field", HARD_GATE_FIELDS)
def test_work_order_hard_gate_true_is_rejected(tmp_path: Path, field: str) -> None:
    repo, head = _make_repo(tmp_path)
    work_order = _write_work_order(tmp_path, head, overrides={field: True})
    agent = _fake_agent(tmp_path)

    result = _run(repo, tmp_path / "out", work_order, head, agent)

    assert result["outcome"] == "rejected"
    assert result["reason"] == f"hard_gate:{field}"
    assert result["next_action_packet"]["next_action"] == NEXT_ACTIONS["hard_gate"]


def test_missing_required_safety_label_rejects_work_order(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    work_order = _write_work_order(
        tmp_path,
        head,
        overrides={"labels": SAFE_LABELS[:-1]},
    )

    result = _run(repo, tmp_path / "out", work_order, head, _fake_agent(tmp_path))

    assert result["reason"] == "invalid_work_order_schema:missing_required_safety_labels"
    assert result["next_action_packet"]["next_action"] == NEXT_ACTIONS["work_order"]


def test_forbidden_path_in_allowed_files_rejects_work_order(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    work_order = _write_work_order(tmp_path, head, allowed_files=["runs/bad.txt"])

    result = _run(repo, tmp_path / "out", work_order, head, _fake_agent(tmp_path))

    assert result["reason"] == "invalid_work_order_schema:allowed_file_forbidden"


def test_path_traversal_in_allowed_files_rejects_work_order(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    work_order = _write_work_order(tmp_path, head, allowed_files=["../bad.py"])

    result = _run(repo, tmp_path / "out", work_order, head, _fake_agent(tmp_path))

    assert result["reason"] == "invalid_work_order_schema:path_traversal"


def test_secret_like_prompt_rejects_work_order_without_invoking_agent(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    work_order = _write_work_order(
        tmp_path,
        head,
        overrides={"agent_prompt": "ALPACA_API_KEY=secret-looking-value"},
    )
    agent = _fake_agent(tmp_path, write_path="src/allowed.py")

    result = _run(repo, tmp_path / "out", work_order, head, agent)

    assert result["reason"] == "invalid_work_order_schema:secret_like_value"
    assert not (repo / "src" / "allowed.py").exists()


def test_local_builder_route_unavailable_blocks_safely(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, head = _make_repo(tmp_path)
    work_order = _write_work_order(tmp_path, head)
    monkeypatch.setattr(development_autopilot.shutil, "which", lambda _name: None)

    result = run_development_autopilot(
        DevelopmentAutopilotOptions(
            output_root=tmp_path / "out",
            work_order_path=work_order,
            expected_head=head,
            repository_verification_commands=(),
        ),
        repo_root=repo,
        env=_safe_env(),
    )

    assert result["reason"] == "blocked/local_builder_route_unavailable"
    assert result["next_action_packet"]["next_action"] == NEXT_ACTIONS["route_unavailable"]


def test_agent_failure_records_failed_outcome_and_next_action(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    work_order = _write_work_order(tmp_path, head)
    agent = _fake_agent(tmp_path, exit_code=7)

    result = _run(repo, tmp_path / "out", work_order, head, agent)

    assert result["exit_code"] == 1
    assert result["outcome"] == "failed"
    assert result["reason"] == "agent_execution_failed"
    assert result["latest"]["agent_exit_code"] == 7
    assert result["next_action_packet"]["next_action"] == NEXT_ACTIONS["agent_failed"]


def test_agent_timeout_records_status_and_stops_before_verification(
    tmp_path: Path,
) -> None:
    repo, head = _make_repo(tmp_path)
    verification_marker = tmp_path / "markers" / "verification.txt"
    work_order = _write_work_order(
        tmp_path,
        head,
        verification_commands=[_marker_command(verification_marker)],
    )
    agent = _fake_agent(tmp_path, sleep_seconds=5)

    result = _run(
        repo,
        tmp_path / "out",
        work_order,
        head,
        agent,
        command_timeout_seconds=1,
        repository_verification_commands=_repo_verification_commands(tmp_path),
    )

    assert result["exit_code"] == 1
    assert result["outcome"] == "failed"
    assert result["reason"] == "agent_command_timeout"
    assert result["latest"]["agent_timeout"] is True
    assert result["latest"]["verification_commands"] == []
    assert result["next_action_packet"]["next_action"] == NEXT_ACTIONS["agent_timeout"]
    assert not verification_marker.exists()
    assert result["latest"]["staging_occurred"] is False
    assert result["latest"]["commit_occurred"] is False
    assert result["latest"]["push_occurred"] is False
    assert _git(repo, "diff", "--cached", "--name-only") == ""


def test_agent_created_disallowed_file_rejects_before_commit(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    work_order = _write_work_order(tmp_path, head, allowed_files=["src/allowed.py"])
    agent = _fake_agent(tmp_path, write_path="src/disallowed.py")

    result = _run(repo, tmp_path / "out", work_order, head, agent)

    assert result["outcome"] == "rejected"
    assert result["reason"] == "changed_file_not_allowed"
    assert result["next_action_packet"]["next_action"] == NEXT_ACTIONS["unexpected_changes"]
    assert _git(repo, "diff", "--cached", "--name-only") == ""


def test_failed_verification_command_produces_repair_required(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    allowed_file = "src/allowed.py"
    work_order = _write_work_order(
        tmp_path,
        head,
        allowed_files=[allowed_file],
        verification_commands=[[sys.executable, "-c", "import sys; sys.exit(3)"]],
    )
    agent = _fake_agent(tmp_path, write_path=allowed_file)

    result = _run(repo, tmp_path / "out", work_order, head, agent)

    assert result["exit_code"] == 1
    assert result["outcome"] == "repair_required"
    assert result["reason"] == "verification_failed"
    assert result["next_action_packet"]["next_action"] == NEXT_ACTIONS["verification_failed"]


def test_verification_command_timeout_records_status_and_stops(
    tmp_path: Path,
) -> None:
    repo, head = _make_repo(tmp_path)
    repo_verification_marker = tmp_path / "markers" / "repo-verification.txt"
    work_order = _write_work_order(
        tmp_path,
        head,
        verification_commands=[_sleep_command(seconds=5)],
    )

    result = _run(
        repo,
        tmp_path / "out",
        work_order,
        head,
        _fake_agent(tmp_path),
        command_timeout_seconds=1,
        repository_verification_commands=(
            _marker_command(repo_verification_marker),
            _marker_command(tmp_path / "markers" / "verify-offline.txt"),
            _marker_command(tmp_path / "markers" / "full-pytest.txt"),
        ),
    )

    assert result["exit_code"] == 1
    assert result["outcome"] == "repair_required"
    assert result["reason"] == "verification_command_timeout"
    assert result["latest"]["verification_timeout"] is True
    assert result["latest"]["verification_timeout_reason"] == "verification_command_timeout"
    assert result["latest"]["verification_commands"][0]["timed_out"] is True
    assert result["next_action_packet"]["next_action"] == NEXT_ACTIONS["verification_timeout"]
    assert not repo_verification_marker.exists()
    assert result["latest"]["staging_occurred"] is False
    assert result["latest"]["commit_occurred"] is False
    assert result["latest"]["push_occurred"] is False
    assert _git(repo, "diff", "--cached", "--name-only") == ""


def test_full_pytest_timeout_records_status_and_stops_before_git_mutation(
    tmp_path: Path,
) -> None:
    repo, head = _make_repo(tmp_path)
    targeted_marker = tmp_path / "markers" / "targeted.txt"
    safety_marker = tmp_path / "markers" / "safety.txt"
    verify_marker = tmp_path / "markers" / "verify-offline.txt"
    work_order = _write_work_order(
        tmp_path,
        head,
        verification_commands=[_marker_command(targeted_marker)],
    )

    result = _run(
        repo,
        tmp_path / "out",
        work_order,
        head,
        _fake_agent(tmp_path),
        command_timeout_seconds=1,
        repository_verification_commands=(
            _marker_command(safety_marker),
            _marker_command(verify_marker),
            _sleep_command(seconds=5),
        ),
    )

    assert result["exit_code"] == 1
    assert result["outcome"] == "repair_required"
    assert result["reason"] == "full_pytest_timeout"
    assert result["latest"]["full_pytest_status"] == "timeout"
    assert result["latest"]["full_pytest_exit_code"] == -1
    assert result["latest"]["verification_timeout_reason"] == "full_pytest_timeout"
    assert result["next_action_packet"]["next_action"] == NEXT_ACTIONS["verification_timeout"]
    assert targeted_marker.exists()
    assert safety_marker.exists()
    assert verify_marker.exists()
    assert result["latest"]["staging_occurred"] is False
    assert result["latest"]["commit_occurred"] is False
    assert result["latest"]["push_occurred"] is False
    assert _git(repo, "diff", "--cached", "--name-only") == ""


def test_app_profile_paper_blocks_before_agent_invocation(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    work_order = _write_work_order(tmp_path, head, allowed_files=["src/allowed.py"])
    agent = _fake_agent(tmp_path, write_path="src/allowed.py")

    result = _run(
        repo,
        tmp_path / "out",
        work_order,
        head,
        agent,
        env=_safe_env(APP_PROFILE="paper"),
    )

    assert result["reason"] == "APP_PROFILE_is_paper"
    assert not (repo / "src" / "allowed.py").exists()


@pytest.mark.parametrize("env_name", ["ALPACA_API_KEY", "APCA_API_SECRET_KEY"])
def test_credential_variables_block_before_agent_invocation(
    tmp_path: Path,
    env_name: str,
) -> None:
    repo, head = _make_repo(tmp_path)
    work_order = _write_work_order(tmp_path, head, allowed_files=["src/allowed.py"])
    agent = _fake_agent(tmp_path, write_path="src/allowed.py")

    result = _run(
        repo,
        tmp_path / "out",
        work_order,
        head,
        agent,
        env=_safe_env(**{env_name: "present"}),
    )

    assert result["reason"] == "credential_environment_loaded"
    assert not (repo / "src" / "allowed.py").exists()


def test_verify_only_mode_never_stages_commits_or_pushes(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    allowed_file = "src/allowed.py"
    work_order = _write_work_order(tmp_path, head, allowed_files=[allowed_file])
    agent = _fake_agent(tmp_path, write_path=allowed_file)

    result = _run(repo, tmp_path / "out", work_order, head, agent, git_mode="verify_only")

    assert result["outcome"] == "accepted"
    assert result["latest"]["staging_occurred"] is False
    assert result["latest"]["commit_occurred"] is False
    assert result["latest"]["push_occurred"] is False
    assert result["latest"]["push_authorization_required"] is False
    assert result["latest"]["push_authorization_status"] == "not_applicable"
    assert result["latest"]["push_authorization_blocker"] is None
    assert _git(repo, "rev-parse", "HEAD") == head
    assert _git(repo, "diff", "--cached", "--name-only") == ""


def test_no_change_fast_path_skips_full_pytest_after_required_checks(
    tmp_path: Path,
) -> None:
    repo, head = _make_repo(tmp_path)
    output_root = tmp_path / "out"
    targeted_marker = tmp_path / "markers" / "targeted.txt"
    safety_marker = tmp_path / "markers" / "safety.txt"
    verify_marker = tmp_path / "markers" / "verify-offline.txt"
    full_marker = tmp_path / "markers" / "full-pytest.txt"
    work_order = _write_work_order(
        tmp_path,
        head,
        verification_commands=[_marker_command(targeted_marker)],
        overrides={"allow_no_change_fast_path": True},
    )

    result = _run(
        repo,
        output_root,
        work_order,
        head,
        _fake_agent(tmp_path),
        full_pytest_policy="changed_files_only",
        repository_verification_commands=(
            _marker_command(safety_marker),
            _marker_command(verify_marker),
            _marker_command(full_marker),
        ),
    )

    assert result["exit_code"] == 0
    assert result["outcome"] == "accepted"
    assert targeted_marker.exists()
    assert safety_marker.exists()
    assert verify_marker.exists()
    assert not full_marker.exists()
    latest = _read_json(output_root / "development_autopilot_latest.json")
    assert latest["full_pytest_policy"] == "changed_files_only"
    assert latest["full_pytest_required"] is False
    assert latest["full_pytest_status"] == "skipped"
    assert latest["full_pytest_skipped_reason"] == "no_source_test_script_changes"
    assert latest["no_change_fast_path_allowed"] is True
    assert latest["no_change_fast_path_used"] is True
    assert latest["normal_pytest_offline_invariant_preserved"] is True
    assert latest["staging_occurred"] is False
    assert latest["commit_occurred"] is False
    assert latest["push_occurred"] is False
    assert latest["push_authorization_required"] is False
    assert latest["push_authorization_status"] == "not_applicable"
    assert latest["push_authorization_blocker"] is None
    assert latest["next_action_packet"]["next_action"] == NEXT_ACTIONS["verify_only_success"]

    verification_results = _read_json(output_root / "verification_results.json")
    assert verification_results["full_pytest_status"] == "skipped"
    assert verification_results["full_pytest_required"] is False
    assert verification_results["push_authorization_status"] == "not_applicable"
    assert len(verification_results["commands"]) == 3

    ledger_line = (output_root / "development_autopilot_ledger.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()[-1]
    ledger = json.loads(ledger_line)
    assert ledger["full_pytest_status"] == "skipped"
    assert ledger["no_change_fast_path_used"] is True

    report = (output_root / "development_autopilot_report.md").read_text(
        encoding="utf-8"
    )
    assert "full_pytest_status: skipped" in report
    assert "normal_pytest_offline_invariant_preserved: True" in report
    assert _git(repo, "diff", "--cached", "--name-only") == ""


def test_changed_files_only_with_source_changes_still_runs_full_pytest(
    tmp_path: Path,
) -> None:
    repo, head = _make_repo(tmp_path)
    full_marker = tmp_path / "markers" / "full-pytest.txt"
    work_order = _write_work_order(
        tmp_path,
        head,
        allowed_files=["src/allowed.py"],
        overrides={"allow_no_change_fast_path": True},
    )

    result = _run(
        repo,
        tmp_path / "out",
        work_order,
        head,
        _fake_agent(tmp_path, write_path="src/allowed.py"),
        full_pytest_policy="changed_files_only",
        repository_verification_commands=_repo_verification_commands(
            tmp_path,
            full_marker=full_marker,
        ),
    )

    assert result["outcome"] == "accepted"
    assert full_marker.exists()
    assert result["latest"]["full_pytest_required"] is True
    assert result["latest"]["full_pytest_status"] == "passed"
    assert result["latest"]["no_change_fast_path_used"] is False


def test_changed_files_only_without_work_order_permission_runs_full_pytest(
    tmp_path: Path,
) -> None:
    repo, head = _make_repo(tmp_path)
    full_marker = tmp_path / "markers" / "full-pytest.txt"
    work_order = _write_work_order(tmp_path, head)

    result = _run(
        repo,
        tmp_path / "out",
        work_order,
        head,
        _fake_agent(tmp_path),
        full_pytest_policy="changed_files_only",
        repository_verification_commands=_repo_verification_commands(
            tmp_path,
            full_marker=full_marker,
        ),
    )

    assert result["outcome"] == "accepted"
    assert full_marker.exists()
    assert result["latest"]["full_pytest_required"] is True
    assert result["latest"]["full_pytest_status"] == "passed"
    assert result["latest"]["no_change_fast_path_allowed"] is False


def test_always_policy_runs_full_pytest_even_with_no_changes(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    full_marker = tmp_path / "markers" / "full-pytest.txt"
    work_order = _write_work_order(
        tmp_path,
        head,
        overrides={"allow_no_change_fast_path": True},
    )

    result = _run(
        repo,
        tmp_path / "out",
        work_order,
        head,
        _fake_agent(tmp_path),
        full_pytest_policy="always",
        repository_verification_commands=_repo_verification_commands(
            tmp_path,
            full_marker=full_marker,
        ),
    )

    assert result["outcome"] == "accepted"
    assert full_marker.exists()
    assert result["latest"]["full_pytest_required"] is True
    assert result["latest"]["full_pytest_status"] == "passed"
    assert result["latest"]["no_change_fast_path_used"] is False


@pytest.mark.parametrize("git_mode", ["commit_only", "commit_and_push"])
def test_git_mutation_modes_require_full_pytest_before_mutation_outcome(
    tmp_path: Path,
    git_mode: str,
) -> None:
    repo, head = _make_repo(tmp_path)
    full_marker = tmp_path / "markers" / "full-pytest.txt"
    work_order = _write_work_order(
        tmp_path,
        head,
        overrides={
            "allow_no_change_fast_path": True,
            "git_mode_allowed": ["verify_only", "commit_only", "commit_and_push"],
        },
    )

    result = _run(
        repo,
        tmp_path / "out",
        work_order,
        head,
        _fake_agent(tmp_path),
        git_mode=git_mode,
        full_pytest_policy="changed_files_only",
        repository_verification_commands=_repo_verification_commands(
            tmp_path,
            full_marker=full_marker,
        ),
    )

    assert result["exit_code"] == 2
    assert result["reason"] == "no_changed_files_to_commit"
    assert full_marker.exists()
    assert result["latest"]["full_pytest_required"] is True
    assert result["latest"]["full_pytest_status"] == "passed"
    assert result["latest"]["no_change_fast_path_allowed"] is False
    assert result["latest"]["commit_occurred"] is False
    assert result["latest"]["push_occurred"] is False


@pytest.mark.parametrize("authorization_overrides", [None, {"nonlocal_push_authorized": False}])
def test_commit_and_push_records_staged_committed_and_local_remote_provenance(
    tmp_path: Path,
    authorization_overrides: dict[str, object] | None,
) -> None:
    repo, head = _make_repo(tmp_path)
    remote = tmp_path / "origin.git"
    _run_subprocess(["git", "init", "--bare", str(remote)], cwd=tmp_path)
    _git(repo, "remote", "add", "origin", str(remote))
    output_root = tmp_path / "out"
    allowed_file = "src/allowed.py"
    full_marker = tmp_path / "markers" / "full-pytest.txt"
    work_order = _write_work_order(
        tmp_path,
        head,
        allowed_files=[allowed_file],
        overrides={
            "git_mode_allowed": ["verify_only", "commit_only", "commit_and_push"],
            **(authorization_overrides or {}),
        },
    )

    result = _run(
        repo,
        output_root,
        work_order,
        head,
        _fake_agent(tmp_path, write_path=allowed_file),
        env=_safe_env(PATH=os.environ.get("PATH", "")),
        git_mode="commit_and_push",
        repository_verification_commands=_repo_verification_commands(
            tmp_path,
            full_marker=full_marker,
        ),
    )

    assert result["outcome"] == "accepted"
    assert result["reason"] == "commit_and_push_success"
    assert full_marker.exists()
    assert _git(repo, "diff", "--cached", "--name-only") == ""
    latest = _read_json(output_root / "development_autopilot_latest.json")
    ledger = json.loads(
        (output_root / "development_autopilot_ledger.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()[-1]
    )
    verification_results = _read_json(output_root / "verification_results.json")

    for payload in (latest, ledger, verification_results):
        assert payload["staging_occurred"] is True
        assert payload["commit_occurred"] is True
        assert payload["push_occurred"] is True
        assert payload["staged_files"] == [allowed_file]
        assert payload["committed_files"] == [allowed_file]
        assert payload["push_remote_name"] == "origin"
        assert payload["push_remote_url_sanitized"]
        assert payload["push_remote_url_kind"] == "local_path"
        assert payload["push_remote_url_is_network"] is False
        assert payload["push_remote_url_is_local_path"] is True
        assert payload["push_remote_url_redacted"] is False
        assert payload["nonlocal_push_authorized"] is False
        assert payload["push_authorization_required"] is False
        assert payload["push_authorization_status"] == "local_remote_allowed"
        assert payload["push_authorization_blocker"] is None

    report = (output_root / "development_autopilot_report.md").read_text(
        encoding="utf-8"
    )
    assert 'staged_files: ["src/allowed.py"]' in report
    assert 'committed_files: ["src/allowed.py"]' in report
    assert "push_remote_url_kind: local_path" in report
    assert "push_remote_url_is_network: False" in report
    assert "push_remote_url_is_local_path: True" in report
    assert "nonlocal_push_authorized: False" in report
    assert "push_authorization_required: False" in report
    assert "push_authorization_status: local_remote_allowed" in report
    assert "push_authorization_blocker: None" in report


@pytest.mark.parametrize(
    "authorization_overrides",
    [None, {"nonlocal_push_authorized": False}, {"nonlocal_push_authorized": None}],
)
def test_unauthorized_network_remote_blocks_before_git_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    authorization_overrides: dict[str, object] | None,
) -> None:
    repo, head = _make_repo(tmp_path)
    raw_url = (
        "https://fixture-user:SECRET_SENTINEL_123@example.invalid/org/repo.git"
        "?credential=SECRET_SENTINEL_123#SECRET_SENTINEL_123"
    )
    _git(repo, "remote", "add", "origin", raw_url)
    output_root = tmp_path / "out"
    allowed_file = "src/allowed.py"
    work_order = _write_work_order(
        tmp_path,
        head,
        allowed_files=[allowed_file],
        overrides={
            "git_mode_allowed": ["verify_only", "commit_only", "commit_and_push"],
            **(authorization_overrides or {}),
        },
    )
    commands: list[tuple[str, ...]] = []
    original_run_command = development_autopilot._run_command

    def recording_run_command(
        command: tuple[str, ...],
        *,
        cwd: Path,
        env: dict[str, str],
    ) -> development_autopilot.CommandResult:
        commands.append(command)
        return original_run_command(command, cwd=cwd, env=env)

    monkeypatch.setattr(development_autopilot, "_run_command", recording_run_command)

    result = _run(
        repo,
        output_root,
        work_order,
        head,
        _fake_agent(tmp_path, write_path=allowed_file),
        env=_safe_env(PATH=os.environ.get("PATH", "")),
        git_mode="commit_and_push",
        repository_verification_commands=_repo_verification_commands(tmp_path),
    )

    assert result["exit_code"] == 2
    assert result["outcome"] == "blocked"
    assert result["reason"] == "network_push_not_authorized"
    assert result["next_action_packet"]["next_action"] == NEXT_ACTIONS["push_authorization"]
    assert _git(repo, "rev-parse", "HEAD") == head
    assert _git(repo, "diff", "--cached", "--name-only") == ""
    assert not _command_was_called(commands, ("git", "add"))
    assert not _command_was_called(commands, ("git", "commit"))
    assert not _command_was_called(commands, ("git", "push"))

    latest = _read_json(output_root / "development_autopilot_latest.json")
    ledger = json.loads(
        (output_root / "development_autopilot_ledger.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()[-1]
    )
    verification_results = _read_json(output_root / "verification_results.json")
    for payload in (latest, ledger, verification_results):
        assert payload["staging_occurred"] is False
        assert payload["commit_occurred"] is False
        assert payload["push_occurred"] is False
        assert payload["staged_files"] == []
        assert payload["committed_files"] == []
        assert payload["push_remote_name"] == "origin"
        assert payload["push_remote_url_sanitized"] == (
            "https://<redacted>@example.invalid/org/repo.git?<redacted>#<redacted>"
        )
        assert payload["push_remote_url_kind"] == "network"
        assert payload["push_remote_url_is_network"] is True
        assert payload["push_remote_url_is_local_path"] is False
        assert payload["push_remote_url_redacted"] is True
        assert payload["nonlocal_push_authorized"] is False
        assert payload["push_authorization_required"] is True
        assert (
            payload["push_authorization_status"]
            == "blocked_network_remote_not_authorized"
        )
        assert payload["push_authorization_blocker"] == "network_push_not_authorized"

    artifacts = _combined_artifact_text(output_root)
    assert raw_url not in artifacts
    assert "fixture-user" not in artifacts
    assert "SECRET_SENTINEL_123" not in artifacts
    assert "push_authorization_status: blocked_network_remote_not_authorized" in artifacts
    assert "push_authorization_blocker: network_push_not_authorized" in artifacts


def test_authorized_network_remote_reaches_intercepted_push_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, head = _make_repo(tmp_path)
    raw_url = (
        "https://fixture-user:SECRET_SENTINEL_456@example.invalid/org/repo.git"
        "?credential=SECRET_SENTINEL_456#SECRET_SENTINEL_456"
    )
    _git(repo, "remote", "add", "origin", raw_url)
    output_root = tmp_path / "out"
    allowed_file = "src/allowed.py"
    work_order = _write_work_order(
        tmp_path,
        head,
        allowed_files=[allowed_file],
        overrides={
            "git_mode_allowed": ["verify_only", "commit_only", "commit_and_push"],
            "nonlocal_push_authorized": True,
        },
    )
    commands: list[tuple[str, ...]] = []
    original_run_command = development_autopilot._run_command

    def intercepted_push_run_command(
        command: tuple[str, ...],
        *,
        cwd: Path,
        env: dict[str, str],
    ) -> development_autopilot.CommandResult:
        commands.append(command)
        if command[:2] == ("git", "push"):
            return development_autopilot.CommandResult(
                command=command,
                exit_code=0,
                stdout="simulated push\n",
            )
        return original_run_command(command, cwd=cwd, env=env)

    monkeypatch.setattr(
        development_autopilot,
        "_run_command",
        intercepted_push_run_command,
    )

    result = _run(
        repo,
        output_root,
        work_order,
        head,
        _fake_agent(tmp_path, write_path=allowed_file),
        env=_safe_env(PATH=os.environ.get("PATH", "")),
        git_mode="commit_and_push",
        repository_verification_commands=_repo_verification_commands(tmp_path),
    )

    assert result["exit_code"] == 0
    assert result["outcome"] == "accepted"
    assert result["reason"] == "commit_and_push_success"
    assert _command_was_called(commands, ("git", "push"))
    assert _first_command_index(commands, ("git", "config", "--get")) < _first_command_index(
        commands,
        ("git", "add"),
    )
    assert _first_command_index(commands, ("git", "add")) < _first_command_index(
        commands,
        ("git", "commit"),
    )
    assert _first_command_index(commands, ("git", "commit")) < _first_command_index(
        commands,
        ("git", "push"),
    )

    latest = _read_json(output_root / "development_autopilot_latest.json")
    ledger = json.loads(
        (output_root / "development_autopilot_ledger.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()[-1]
    )
    verification_results = _read_json(output_root / "verification_results.json")
    for payload in (latest, ledger, verification_results):
        assert payload["staging_occurred"] is True
        assert payload["commit_occurred"] is True
        assert payload["push_occurred"] is True
        assert payload["staged_files"] == [allowed_file]
        assert payload["committed_files"] == [allowed_file]
        assert payload["push_remote_url_kind"] == "network"
        assert payload["push_remote_url_is_network"] is True
        assert payload["push_remote_url_redacted"] is True
        assert payload["nonlocal_push_authorized"] is True
        assert payload["push_authorization_required"] is True
        assert payload["push_authorization_status"] == "network_remote_authorized"
        assert payload["push_authorization_blocker"] is None

    artifacts = _combined_artifact_text(output_root)
    assert raw_url not in artifacts
    assert "fixture-user" not in artifacts
    assert "SECRET_SENTINEL_456" not in artifacts
    assert "push_authorization_status: network_remote_authorized" in artifacts


def test_unknown_remote_blocks_even_when_nonlocal_push_is_authorized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, head = _make_repo(tmp_path)
    output_root = tmp_path / "out"
    allowed_file = "src/allowed.py"
    work_order = _write_work_order(
        tmp_path,
        head,
        allowed_files=[allowed_file],
        overrides={
            "git_mode_allowed": ["verify_only", "commit_only", "commit_and_push"],
            "nonlocal_push_authorized": True,
        },
    )
    commands: list[tuple[str, ...]] = []
    original_run_command = development_autopilot._run_command

    def recording_run_command(
        command: tuple[str, ...],
        *,
        cwd: Path,
        env: dict[str, str],
    ) -> development_autopilot.CommandResult:
        commands.append(command)
        return original_run_command(command, cwd=cwd, env=env)

    monkeypatch.setattr(development_autopilot, "_run_command", recording_run_command)

    result = _run(
        repo,
        output_root,
        work_order,
        head,
        _fake_agent(tmp_path, write_path=allowed_file),
        env=_safe_env(PATH=os.environ.get("PATH", "")),
        git_mode="commit_and_push",
        repository_verification_commands=_repo_verification_commands(tmp_path),
    )

    assert result["exit_code"] == 2
    assert result["outcome"] == "blocked"
    assert result["reason"] == "push_remote_unknown"
    assert result["next_action_packet"]["next_action"] == NEXT_ACTIONS["push_authorization"]
    assert _git(repo, "rev-parse", "HEAD") == head
    assert _git(repo, "diff", "--cached", "--name-only") == ""
    assert not _command_was_called(commands, ("git", "add"))
    assert not _command_was_called(commands, ("git", "commit"))
    assert not _command_was_called(commands, ("git", "push"))

    latest = _read_json(output_root / "development_autopilot_latest.json")
    verification_results = _read_json(output_root / "verification_results.json")
    for payload in (latest, verification_results):
        assert payload["staging_occurred"] is False
        assert payload["commit_occurred"] is False
        assert payload["push_occurred"] is False
        assert payload["staged_files"] == []
        assert payload["committed_files"] == []
        assert payload["push_remote_name"] == "origin"
        assert payload["push_remote_url_sanitized"] == ""
        assert payload["push_remote_url_kind"] == "unknown"
        assert payload["nonlocal_push_authorized"] is True
        assert payload["push_authorization_required"] is True
        assert payload["push_authorization_status"] == "blocked_unknown_remote"
        assert payload["push_authorization_blocker"] == "push_remote_unknown"


def test_non_boolean_nonlocal_push_authorization_rejects_work_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, head = _make_repo(tmp_path)
    _git(repo, "remote", "add", "origin", "https://example.invalid/org/repo.git")
    work_order = _write_work_order(
        tmp_path,
        head,
        allowed_files=["src/allowed.py"],
        overrides={
            "git_mode_allowed": ["verify_only", "commit_only", "commit_and_push"],
            "nonlocal_push_authorized": "true",
        },
    )
    commands: list[tuple[str, ...]] = []
    original_run_command = development_autopilot._run_command

    def recording_run_command(
        command: tuple[str, ...],
        *,
        cwd: Path,
        env: dict[str, str],
    ) -> development_autopilot.CommandResult:
        commands.append(command)
        return original_run_command(command, cwd=cwd, env=env)

    monkeypatch.setattr(development_autopilot, "_run_command", recording_run_command)

    result = _run(
        repo,
        tmp_path / "out",
        work_order,
        head,
        _fake_agent(tmp_path, write_path="src/allowed.py"),
        env=_safe_env(PATH=os.environ.get("PATH", "")),
        git_mode="commit_and_push",
    )

    assert result["exit_code"] == 2
    assert result["outcome"] == "blocked"
    assert result["reason"] == "invalid_work_order_schema:nonlocal_push_authorized"
    assert _git(repo, "rev-parse", "HEAD") == head
    assert _git(repo, "diff", "--cached", "--name-only") == ""
    assert not (repo / "src" / "allowed.py").exists()
    assert not _command_was_called(commands, ("git", "add"))
    assert not _command_was_called(commands, ("git", "commit"))
    assert not _command_was_called(commands, ("git", "push"))


def test_credential_bearing_remote_url_is_sanitized_without_raw_secret() -> None:
    raw_url = "https://user:token@example.com/org/repo.git"

    sanitized_url, redacted = development_autopilot._sanitize_remote_url(raw_url)
    kind = development_autopilot._remote_url_kind(raw_url)
    serialized = json.dumps(
        {
            "push_remote_url_sanitized": sanitized_url,
            "push_remote_url_kind": kind,
            "push_remote_url_is_network": kind == "network",
            "push_remote_url_is_local_path": kind == "local_path",
            "push_remote_url_redacted": redacted,
        },
        sort_keys=True,
    )

    assert sanitized_url == "https://<redacted>@example.com/org/repo.git"
    assert kind == "network"
    assert redacted is True
    assert raw_url not in serialized
    assert "user:token" not in serialized
    assert "token@example.com" not in serialized


@pytest.mark.parametrize("git_mode", ["commit_only", "commit_and_push"])
def test_git_mutation_modes_are_rejected_unless_work_order_allows_them(
    tmp_path: Path,
    git_mode: str,
) -> None:
    repo, head = _make_repo(tmp_path)
    work_order = _write_work_order(
        tmp_path,
        head,
        overrides={"git_mode_allowed": ["verify_only"]},
    )
    agent = _fake_agent(tmp_path, write_path="src/allowed.py")

    result = _run(repo, tmp_path / "out", work_order, head, agent, git_mode=git_mode)

    assert result["outcome"] == "rejected"
    assert result["reason"] == "git_mode_not_allowed_by_work_order"
    assert not (repo / "src" / "allowed.py").exists()
    assert _git(repo, "diff", "--cached", "--name-only") == ""


def test_runtime_artifacts_and_ledger_are_written_under_output_root(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    output_root = tmp_path / "out"
    work_order = _write_work_order(tmp_path, head, allowed_files=["src/allowed.py"])
    agent = _fake_agent(tmp_path, write_path="src/allowed.py")

    result = _run(repo, output_root, work_order, head, agent)

    assert result["outcome"] == "accepted"
    expected_artifacts = {
        "development_autopilot_latest.json",
        "development_autopilot_ledger.jsonl",
        "development_autopilot_report.md",
        "agent_stdout.txt",
        "agent_stderr.txt",
        "work_order_packet.json",
        "verification_results.json",
        "next_action_packet.json",
    }
    assert expected_artifacts.issubset({path.name for path in output_root.iterdir()})
    assert _read_json(output_root / "next_action_packet.json")["next_action"] == (
        NEXT_ACTIONS["verify_only_success"]
    )
    ledger_lines = (output_root / "development_autopilot_ledger.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(ledger_lines) == 1
    assert json.loads(ledger_lines[0])["outcome"] == "accepted"
    assert "runs/" not in _git(repo, "status", "--short")
    assert ".agent_inbox/" not in _git(repo, "status", "--short")
    assert ".data/" not in _git(repo, "status", "--short")


def test_ledger_is_append_only_for_repeated_blocked_runs(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    output_root = tmp_path / "out"
    options = DevelopmentAutopilotOptions(
        output_root=output_root,
        expected_head=head,
        agent_command=str(_fake_agent(tmp_path)),
        repository_verification_commands=(),
    )

    first = run_development_autopilot(options, repo_root=repo, env=_safe_env())
    second = run_development_autopilot(options, repo_root=repo, env=_safe_env())

    assert first["reason"] == "missing_work_order"
    assert second["reason"] == "missing_work_order"
    ledger_lines = (output_root / "development_autopilot_ledger.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(ledger_lines) == 2


def test_next_action_packet_emits_exactly_one_action(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    work_order = _write_work_order(tmp_path, head, allowed_files=["src/allowed.py"])
    agent = _fake_agent(tmp_path, write_path="src/allowed.py")

    result = _run(repo, tmp_path / "out", work_order, head, agent)

    packet = result["next_action_packet"]
    assert set(packet).issuperset({"next_action"})
    assert "next_actions" not in packet
    assert isinstance(packet["next_action"], str)


def _command_was_called(
    commands: list[tuple[str, ...]],
    prefix: tuple[str, ...],
) -> bool:
    return any(command[: len(prefix)] == prefix for command in commands)


def _first_command_index(
    commands: list[tuple[str, ...]],
    prefix: tuple[str, ...],
) -> int:
    for index, command in enumerate(commands):
        if command[: len(prefix)] == prefix:
            return index
    raise AssertionError(f"command prefix not called: {prefix!r}")


def _combined_artifact_text(output_root: Path) -> str:
    names = (
        "development_autopilot_latest.json",
        "development_autopilot_ledger.jsonl",
        "verification_results.json",
        "development_autopilot_report.md",
    )
    return "\n".join(
        (output_root / name).read_text(encoding="utf-8") for name in names
    )


def _run(
    repo: Path,
    output_root: Path,
    work_order: Path,
    expected_head: str,
    agent_command: Path,
    *,
    env: dict[str, str] | None = None,
    git_mode: str = "verify_only",
    repository_verification_commands: tuple[tuple[str, ...], ...] | None = (),
    command_timeout_seconds: int = 1800,
    full_pytest_policy: str = "always",
) -> dict[str, object]:
    return run_development_autopilot(
        DevelopmentAutopilotOptions(
            output_root=output_root,
            work_order_path=work_order,
            expected_head=expected_head,
            agent_command=f"{sys.executable} {agent_command}",
            git_mode=git_mode,
            repository_verification_commands=repository_verification_commands,
            command_timeout_seconds=command_timeout_seconds,
            full_pytest_policy=full_pytest_policy,
        ),
        repo_root=repo,
        env=_safe_env() if env is None else env,
    )


def _make_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "Tests")
    (repo / "src").mkdir()
    (repo / "tests").mkdir()
    (repo / "scripts").mkdir()
    (repo / "README.md").write_text("baseline\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "baseline")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    return repo, _git(repo, "rev-parse", "HEAD")


def _write_work_order(
    tmp_path: Path,
    expected_head: str,
    *,
    allowed_files: list[str] | None = None,
    verification_commands: list[list[str]] | None = None,
    overrides: dict[str, object] | None = None,
) -> Path:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "work_order_id": "wo-1",
        "phase": "v1.47B",
        "goal": "test work order",
        "created_by": "pytest",
        "source_of_truth": "unit-test",
        "expected_head": expected_head,
        "agent_route": "codex",
        "agent_prompt": "Make the allowed deterministic test edit.",
        "allowed_files": allowed_files or ["src/allowed.py"],
        "forbidden_paths": ["runs/", ".agent_inbox/", ".data/", "docs/reviews/"],
        "required_verification_commands": verification_commands
        if verification_commands is not None
        else [[sys.executable, "-c", "print('verification ok')"]],
        "git_mode_allowed": ["verify_only"],
        "commit_message": "Test development autopilot work order",
        "broker_read_authorized": False,
        "broker_mutation_authorized": False,
        "paper_submit_authorized": False,
        "live_trading_authorized": False,
        "capital_authorized": False,
        "paid_service_authorized": False,
        "credential_access_authorized": False,
        "network_access_authorized": False,
        "labels": list(SAFE_LABELS),
    }
    if overrides:
        payload.update(overrides)
    path = tmp_path / f"work-order-{len(list(tmp_path.glob('work-order-*.json')))}.json"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _fake_agent(
    tmp_path: Path,
    *,
    write_path: str | None = None,
    exit_code: int = 0,
    sleep_seconds: int = 0,
) -> Path:
    script = tmp_path / f"fake-agent-{len(list(tmp_path.glob('fake-agent-*.py')))}.py"
    write_literal = repr(write_path)
    script.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "import sys",
                "import time",
                "prompt = sys.stdin.read()",
                "print('agent stdout', flush=True)",
                "print('agent stderr', file=sys.stderr, flush=True)",
                f"time.sleep({sleep_seconds})",
                f"write_path = {write_literal}",
                "if write_path:",
                "    path = Path(write_path)",
                "    path.parent.mkdir(parents=True, exist_ok=True)",
                "    path.write_text('build-output\\n', encoding='utf-8')",
                f"raise SystemExit({exit_code})",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return script


def _marker_command(
    marker_path: Path,
    *,
    text: str = "ran",
    exit_code: int = 0,
) -> tuple[str, ...]:
    code = (
        "from pathlib import Path; "
        f"path = Path({str(marker_path)!r}); "
        "path.parent.mkdir(parents=True, exist_ok=True); "
        f"path.write_text({text!r}, encoding='utf-8'); "
        f"raise SystemExit({exit_code})"
    )
    return (sys.executable, "-c", code)


def _sleep_command(*, seconds: int) -> tuple[str, ...]:
    code = f"import time; print('sleeping', flush=True); time.sleep({seconds})"
    return (sys.executable, "-c", code)


def _repo_verification_commands(
    tmp_path: Path,
    *,
    full_marker: Path | None = None,
) -> tuple[tuple[str, ...], ...]:
    return (
        _marker_command(tmp_path / "markers" / "safety.txt"),
        _marker_command(tmp_path / "markers" / "verify-offline.txt"),
        _marker_command(full_marker or tmp_path / "markers" / "full-pytest.txt"),
    )


def _safe_env(**overrides: str) -> dict[str, str]:
    env = {
        "PATH": str(Path(sys.executable).parent),
        "SYSTEMROOT": "C:\\Windows",
    }
    env.update(overrides)
    return env


def _git(repo: Path, *args: str) -> str:
    return _run_subprocess(["git", *args], cwd=repo).stdout.strip()


def _run_subprocess(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))
