from __future__ import annotations

import json
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
        ]
    )

    assert args.command == "development-autopilot"
    assert args.output_root == "runs/dev"
    assert args.work_order_path == "work-order.json"
    assert args.expected_head == "abc"
    assert args.agent_route == "codex"
    assert args.agent_command == "fake-codex"
    assert args.git_mode == "verify_only"


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
    }


def test_invalid_work_order_schema_blocks(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path)
    work_order = tmp_path / "invalid.json"
    work_order.write_text(json.dumps({"schema_version": "1.0"}), encoding="utf-8")

    result = _run(repo, tmp_path / "out", work_order, head, _fake_agent(tmp_path))

    assert result["outcome"] == "blocked"
    assert result["reason"].startswith("invalid_work_order_schema:")
    assert result["next_action_packet"]["next_action"] == NEXT_ACTIONS["work_order"]


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
    assert _git(repo, "rev-parse", "HEAD") == head
    assert _git(repo, "diff", "--cached", "--name-only") == ""


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


def _run(
    repo: Path,
    output_root: Path,
    work_order: Path,
    expected_head: str,
    agent_command: Path,
    *,
    env: dict[str, str] | None = None,
    git_mode: str = "verify_only",
) -> dict[str, object]:
    return run_development_autopilot(
        DevelopmentAutopilotOptions(
            output_root=output_root,
            work_order_path=work_order,
            expected_head=expected_head,
            agent_command=f"{sys.executable} {agent_command}",
            git_mode=git_mode,
            repository_verification_commands=(),
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
) -> Path:
    script = tmp_path / f"fake-agent-{len(list(tmp_path.glob('fake-agent-*.py')))}.py"
    write_literal = repr(write_path)
    script.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "import sys",
                "prompt = sys.stdin.read()",
                "print('agent stdout')",
                "print('agent stderr', file=sys.stderr)",
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
