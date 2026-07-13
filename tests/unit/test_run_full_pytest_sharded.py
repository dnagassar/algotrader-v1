from __future__ import annotations

import ast
from collections import Counter
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "run_full_pytest_sharded.py"


def _load_runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "algotrader_full_pytest_sharded_runner",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_preflight_is_default_offline_and_reports_names_without_values() -> None:
    runner = _load_runner()

    assert runner._preflight_blockers({}) == ()
    assert runner._preflight_blockers({"APP_PROFILE": "paper"}) == (
        "APP_PROFILE_paper_loaded",
    )
    assert runner._preflight_blockers({"APP_PROFILE": "live"}) == (
        "APP_PROFILE_live_loaded",
    )
    assert runner._preflight_blockers({"ALPACA_API_KEY": "sensitive"}) == (
        "broker_credentials_loaded",
    )
    assert runner._preflight_blockers(
        {"ALGO_TRADER_ALLOW_NETWORK_TESTS": "1"}
    ) == ("ALGO_TRADER_ALLOW_NETWORK_TESTS_enabled",)
    assert runner._preflight_blockers(
        {"RUN_ALPACA_PAPER_INTEGRATION_TESTS": "true"}
    ) == ("RUN_ALPACA_PAPER_INTEGRATION_TESTS_enabled",)
    assert runner._preflight_blockers({"PYTEST_ADDOPTS": "-x"}) == (
        "PYTEST_ADDOPTS_must_be_empty_for_exact_default_collection",
    )


def test_test_paths_are_confined_to_repository_tests(tmp_path: Path) -> None:
    runner = _load_runner()
    tests = tmp_path / "tests"
    tests.mkdir()
    unit = tests / "unit"
    unit.mkdir()
    test_file = unit / "test_example.py"
    test_file.write_text("def test_example(): pass\n", encoding="utf-8")

    assert runner._validated_test_paths(tmp_path, ()) == ("tests",)
    assert runner._validated_test_paths(
        tmp_path,
        ("tests/unit/test_example.py",),
    ) == ("tests/unit/test_example.py",)
    with pytest.raises(ValueError, match="within"):
        runner._validated_test_paths(tmp_path, ("outside.py",))
    with pytest.raises(ValueError, match="node IDs"):
        runner._validated_test_paths(
            tmp_path,
            ("tests/unit/test_example.py::test_example",),
        )
    with pytest.raises(ValueError, match="duplicate"):
        runner._validated_test_paths(
            tmp_path,
            ("tests", "tests"),
        )


def test_collection_parser_requires_unique_nodeids() -> None:
    runner = _load_runner()
    output = "\n".join(
        (
            "tests/unit/test_a.py::test_one",
            "tests\\unit\\test_b.py::test_two[value]",
            "tests/unit/test_b.py::test_path[C:\\data\\spy.csv]",
            "3 tests collected in 0.01s",
        )
    )

    assert runner._parse_nodeids(output) == (
        "tests/unit/test_a.py::test_one",
        "tests/unit/test_b.py::test_two[value]",
        "tests/unit/test_b.py::test_path[C:\\data\\spy.csv]",
    )
    with pytest.raises(ValueError, match="no test node IDs"):
        runner._parse_nodeids("2 tests collected")
    with pytest.raises(ValueError, match="duplicate"):
        runner._parse_nodeids(
            "tests/unit/test_a.py::test_one\n"
            "tests/unit/test_a.py::test_one\n"
        )


def test_partition_is_deterministic_balanced_disjoint_and_exact() -> None:
    runner = _load_runner()
    nodeids = tuple(
        f"tests/unit/test_{index % 3}.py::test_{index}"
        for index in range(17)
    )

    first = runner._partition_nodeids(nodeids, 4)
    second = runner._partition_nodeids(tuple(reversed(nodeids)), 4)

    assert first == second
    assert max(map(len, first)) - min(map(len, first)) <= 1
    assert runner._partition_errors(nodeids, first) == ()
    flattened = [nodeid for shard in first for nodeid in shard]
    assert Counter(flattened) == Counter(nodeids)
    assert all(set(left).isdisjoint(right) for left in first for right in first if left is not right)
    with pytest.raises(ValueError, match="between"):
        runner._partition_nodeids(nodeids, 0)


def test_partition_errors_identify_missing_extra_and_duplicates() -> None:
    runner = _load_runner()
    canonical = (
        "tests/unit/test_a.py::test_one",
        "tests/unit/test_b.py::test_two",
    )

    errors = runner._partition_errors(
        canonical,
        (
            (
                "tests/unit/test_a.py::test_one",
                "tests/unit/test_a.py::test_one",
                "tests/unit/test_c.py::test_three",
            ),
        ),
    )

    assert any(error.startswith("missing node IDs") for error in errors)
    assert any(error.startswith("unexpected node IDs") for error in errors)
    assert any(error.startswith("duplicate node IDs") for error in errors)


def test_junit_summary_aggregates_counts_and_file_timings(tmp_path: Path) -> None:
    runner = _load_runner()
    report = tmp_path / "report.xml"
    report.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite tests="3" failures="1" errors="0" skipped="1">
  <testcase classname="tests.unit.test_a" name="test_one" time="0.25" />
  <testcase classname="tests.unit.test_a.TestGroup" name="test_two" time="0.50"><skipped /></testcase>
  <testcase classname="tests.unit.test_b" name="test_three" time="1.25"><failure /></testcase>
</testsuite></testsuites>
""",
        encoding="utf-8",
    )

    summary = runner._junit_summary(
        report,
        {
            "tests.unit.test_a": "tests/unit/test_a.py",
            "tests.unit.test_b": "tests/unit/test_b.py",
        },
    )

    assert summary.tests == 3
    assert summary.passed == 1
    assert summary.failures == 1
    assert summary.errors == 0
    assert summary.skipped == 1
    assert summary.file_seconds == {
        "tests/unit/test_a.py": pytest.approx(0.75),
        "tests/unit/test_b.py": pytest.approx(1.25),
    }


def test_pytest_command_has_no_selection_or_network_override() -> None:
    runner = _load_runner()

    assert runner._pytest_base_command() == [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
    ]


def test_runner_source_imports_no_network_or_broker_boundary() -> None:
    tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"), filename=str(SCRIPT_PATH))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert imported.isdisjoint(
        {
            "alpaca",
            "httpx",
            "requests",
            "socket",
            "urllib",
            "algotrader.execution.alpaca_adapter",
            "algotrader.execution.durable_cancel",
        }
    )


def test_collect_only_runner_proves_exact_argument_file_equivalence() -> None:
    env = dict(os.environ)
    for name in (
        "APP_PROFILE",
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET_KEY",
        "ALPACA_SECRET_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "ALGO_TRADER_ALLOW_NETWORK_TESTS",
        "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
        "PYTEST_ADDOPTS",
    ):
        env.pop(name, None)
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--collect-only",
            "--shards",
            "3",
            "--test-path",
            "tests/unit/test_paper_cancellation_invocation.py",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "canonical_nodeids=26" in result.stdout
    assert "shard_01_assigned=9" in result.stdout
    assert "shard_02_assigned=9" in result.stdout
    assert "shard_03_assigned=8" in result.stdout
    assert "collection_equivalence=PASS" in result.stdout
    assert "execution=SKIPPED_BY_REQUEST" in result.stdout
