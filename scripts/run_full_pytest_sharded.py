"""Run the complete default pytest collection in exact bounded offline shards."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET


DEFAULT_SHARDS = 4
DEFAULT_SHARD_TIMEOUT_SECONDS = 1800
DEFAULT_COLLECTION_TIMEOUT_SECONDS = 300
MAXIMUM_SHARDS = 16
BLOCKED_CREDENTIAL_VARIABLES = (
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
)
BLOCKED_NETWORK_VARIABLES = (
    "ALGO_TRADER_ALLOW_NETWORK_TESTS",
    "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
)


@dataclass(frozen=True, slots=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    elapsed_seconds: float
    timed_out: bool = False


@dataclass(frozen=True, slots=True)
class ShardResult:
    index: int
    assigned_count: int
    command: CommandResult
    junit_path: Path


@dataclass(frozen=True, slots=True)
class JunitSummary:
    tests: int
    failures: int
    errors: int
    skipped: int
    file_seconds: Mapping[str, float]

    @property
    def passed(self) -> int:
        return self.tests - self.failures - self.errors - self.skipped


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Collect the default offline pytest suite once, verify exact "
            "node-ID partitions, and execute bounded parallel shards."
        )
    )
    parser.add_argument(
        "--shards",
        type=int,
        default=DEFAULT_SHARDS,
        help=f"parallel shard count (default: {DEFAULT_SHARDS})",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_SHARD_TIMEOUT_SECONDS,
        help=(
            "timeout for each execution shard "
            f"(default: {DEFAULT_SHARD_TIMEOUT_SECONDS})"
        ),
    )
    parser.add_argument(
        "--collection-timeout-seconds",
        type=int,
        default=DEFAULT_COLLECTION_TIMEOUT_SECONDS,
        help=(
            "timeout for canonical and shard collection "
            f"(default: {DEFAULT_COLLECTION_TIMEOUT_SECONDS})"
        ),
    )
    parser.add_argument(
        "--top-slowest-files",
        type=int,
        default=20,
        help="number of aggregate per-file test timings to print",
    )
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="verify exact shard collection without executing tests",
    )
    parser.add_argument(
        "--test-path",
        action="append",
        default=[],
        help=(
            "test file or directory below tests/; repeatable and intended for "
            "runner self-tests. The default is the complete tests directory."
        ),
    )
    return parser


def _preflight_blockers(env: Mapping[str, str]) -> tuple[str, ...]:
    blockers: list[str] = []
    profile = str(env.get("APP_PROFILE", "")).strip().lower()
    if profile in {"paper", "live"}:
        blockers.append(f"APP_PROFILE_{profile}_loaded")
    if any(str(env.get(name, "")).strip() for name in BLOCKED_CREDENTIAL_VARIABLES):
        blockers.append("broker_credentials_loaded")
    for name in BLOCKED_NETWORK_VARIABLES:
        if _truthy(env.get(name, "")):
            blockers.append(f"{name}_enabled")
    if str(env.get("PYTEST_ADDOPTS", "")).strip():
        blockers.append("PYTEST_ADDOPTS_must_be_empty_for_exact_default_collection")
    return tuple(blockers)


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _validated_test_paths(root: Path, values: Sequence[str]) -> tuple[str, ...]:
    tests_root = (root / "tests").resolve()
    raw_values = tuple(values) or ("tests",)
    paths: list[str] = []
    for raw in raw_values:
        if "::" in raw:
            raise ValueError("--test-path accepts files or directories, not node IDs.")
        candidate = Path(raw)
        resolved = (
            candidate.resolve()
            if candidate.is_absolute()
            else (root / candidate).resolve()
        )
        if not resolved.is_relative_to(tests_root):
            raise ValueError("--test-path must stay within the repository tests directory.")
        if not resolved.exists():
            raise ValueError(f"test path does not exist: {raw}")
        paths.append(resolved.relative_to(root).as_posix())
    if len(paths) != len(set(paths)):
        raise ValueError("duplicate --test-path values are not allowed.")
    return tuple(paths)


def _pytest_base_command() -> list[str]:
    return [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
    ]


def _child_environment(env: Mapping[str, str]) -> dict[str, str]:
    child = dict(env)
    child["PYTHONIOENCODING"] = "utf-8"
    child["PYTHONUTF8"] = "1"
    return child


def _run_command(
    command: Sequence[str],
    *,
    root: Path,
    env: Mapping[str, str],
    timeout_seconds: int,
) -> CommandResult:
    started = time.monotonic()
    try:
        result = subprocess.run(
            list(command),
            cwd=root,
            env=_child_environment(env),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            returncode=124,
            stdout=_timeout_text(exc.stdout),
            stderr=_timeout_text(exc.stderr),
            elapsed_seconds=time.monotonic() - started,
            timed_out=True,
        )
    return CommandResult(
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        elapsed_seconds=time.monotonic() - started,
    )


def _timeout_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _parse_nodeids(output: str) -> tuple[str, ...]:
    normalized_lines = tuple(
        _normalize_nodeid(line.strip()) for line in output.splitlines()
    )
    nodeids = tuple(
        line
        for line in normalized_lines
        if line.startswith("tests/") and "::" in line
    )
    if not nodeids:
        raise ValueError("pytest collection returned no test node IDs.")
    duplicates = tuple(
        sorted(nodeid for nodeid, count in Counter(nodeids).items() if count > 1)
    )
    if duplicates:
        raise ValueError(
            "pytest collection returned duplicate node IDs: "
            + ", ".join(duplicates[:5])
        )
    return nodeids


def _normalize_nodeid(value: str) -> str:
    file_name, separator, remainder = value.partition("::")
    if not separator:
        return value
    normalized_file_name = file_name.replace("\\", "/")
    return f"{normalized_file_name}::{remainder}"


def _partition_nodeids(
    nodeids: Sequence[str],
    shard_count: int,
) -> tuple[tuple[str, ...], ...]:
    if type(shard_count) is not int or not 1 <= shard_count <= MAXIMUM_SHARDS:
        raise ValueError(f"shards must be between 1 and {MAXIMUM_SHARDS}.")
    ordered = tuple(sorted(nodeids))
    if not ordered:
        raise ValueError("cannot partition an empty collection.")
    actual_count = min(shard_count, len(ordered))
    shards: list[list[str]] = [[] for _ in range(actual_count)]
    for index, nodeid in enumerate(ordered):
        shards[index % actual_count].append(nodeid)
    return tuple(tuple(shard) for shard in shards)


def _partition_errors(
    canonical: Sequence[str],
    shards: Sequence[Sequence[str]],
) -> tuple[str, ...]:
    expected = Counter(canonical)
    observed = Counter(nodeid for shard in shards for nodeid in shard)
    errors: list[str] = []
    missing = sorted((expected - observed).elements())
    extra = sorted((observed - expected).elements())
    duplicated = sorted(nodeid for nodeid, count in observed.items() if count > 1)
    if missing:
        errors.append(f"missing node IDs: {', '.join(missing[:5])}")
    if extra:
        errors.append(f"unexpected node IDs: {', '.join(extra[:5])}")
    if duplicated:
        errors.append(f"duplicate node IDs: {', '.join(duplicated[:5])}")
    return tuple(errors)


def _write_argument_files(
    directory: Path,
    shards: Sequence[Sequence[str]],
) -> tuple[Path, ...]:
    paths: list[Path] = []
    for index, nodeids in enumerate(shards, start=1):
        path = directory / f"shard_{index:02d}.args"
        path.write_text("\n".join(nodeids) + "\n", encoding="utf-8")
        paths.append(path)
    return tuple(paths)


def _collect(
    *,
    root: Path,
    env: Mapping[str, str],
    paths: Sequence[str],
    timeout_seconds: int,
) -> tuple[tuple[str, ...], CommandResult]:
    command = [*_pytest_base_command(), "--collect-only", *paths]
    result = _run_command(
        command,
        root=root,
        env=env,
        timeout_seconds=timeout_seconds,
    )
    if result.returncode != 0:
        return (), result
    try:
        return _parse_nodeids(result.stdout), result
    except ValueError as exc:
        return (), CommandResult(
            returncode=2,
            stdout=result.stdout,
            stderr=f"{result.stderr}\n{exc}",
            elapsed_seconds=result.elapsed_seconds,
        )


def _collect_argument_file(
    index: int,
    path: Path,
    *,
    root: Path,
    env: Mapping[str, str],
    timeout_seconds: int,
) -> tuple[int, tuple[str, ...], CommandResult]:
    nodeids, result = _collect(
        root=root,
        env=env,
        paths=(f"@{path}",),
        timeout_seconds=timeout_seconds,
    )
    return index, nodeids, result


def _execute_shard(
    index: int,
    argument_file: Path,
    assigned_count: int,
    *,
    root: Path,
    env: Mapping[str, str],
    timeout_seconds: int,
    temp_root: Path,
) -> ShardResult:
    junit_path = temp_root / f"shard_{index:02d}.xml"
    base_temp = temp_root / f"pytest_tmp_{index:02d}"
    command = [
        *_pytest_base_command(),
        f"--junitxml={junit_path}",
        f"--basetemp={base_temp}",
        f"@{argument_file}",
    ]
    result = _run_command(
        command,
        root=root,
        env=env,
        timeout_seconds=timeout_seconds,
    )
    return ShardResult(
        index=index,
        assigned_count=assigned_count,
        command=result,
        junit_path=junit_path,
    )


def _module_to_file(nodeids: Sequence[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for nodeid in nodeids:
        file_name = nodeid.split("::", 1)[0]
        module_name = file_name.removesuffix(".py").replace("/", ".")
        mapping[module_name] = file_name
    return mapping


def _junit_summary(path: Path, module_to_file: Mapping[str, str]) -> JunitSummary:
    root = ET.parse(path).getroot()
    file_seconds: defaultdict[str, float] = defaultdict(float)
    failures = 0
    errors = 0
    skipped = 0
    testcases = list(root.iter("testcase"))
    modules = tuple(sorted(module_to_file, key=len, reverse=True))
    for testcase in testcases:
        classname = str(testcase.attrib.get("classname", ""))
        file_name = _file_for_classname(classname, modules, module_to_file)
        file_seconds[file_name] += float(testcase.attrib.get("time", "0") or 0)
        if testcase.find("failure") is not None:
            failures += 1
        if testcase.find("error") is not None:
            errors += 1
        if testcase.find("skipped") is not None:
            skipped += 1
    return JunitSummary(
        tests=len(testcases),
        failures=failures,
        errors=errors,
        skipped=skipped,
        file_seconds=dict(file_seconds),
    )


def _file_for_classname(
    classname: str,
    modules: Sequence[str],
    module_to_file: Mapping[str, str],
) -> str:
    for module in modules:
        if classname == module or classname.startswith(f"{module}."):
            return module_to_file[module]
    return f"<unmapped:{classname or 'unknown'}>"


def _print_command_failure(label: str, result: CommandResult) -> None:
    print(f"{label}: FAIL exit={result.returncode} timeout={result.timed_out}")
    if result.stdout.strip():
        print(f"--- {label} stdout ---")
        print(result.stdout.rstrip())
    if result.stderr.strip():
        print(f"--- {label} stderr ---")
        print(result.stderr.rstrip())


def _positive(value: int, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    blockers = _preflight_blockers(env)
    if blockers:
        print("preflight: BLOCKED")
        for blocker in blockers:
            print(f"- {blocker}")
        return 2
    try:
        _positive(args.timeout_seconds, "timeout-seconds")
        _positive(args.collection_timeout_seconds, "collection-timeout-seconds")
        _positive(args.top_slowest_files, "top-slowest-files")
        if not 1 <= args.shards <= MAXIMUM_SHARDS:
            raise ValueError(f"shards must be between 1 and {MAXIMUM_SHARDS}.")
        test_paths = _validated_test_paths(root, args.test_path)
    except ValueError as exc:
        print(f"configuration: BLOCKED - {exc}")
        return 2

    print("preflight: PASS (offline, credential-free, default collection)")
    print(f"test_paths={','.join(test_paths)}")
    canonical, collection = _collect(
        root=root,
        env=env,
        paths=test_paths,
        timeout_seconds=args.collection_timeout_seconds,
    )
    if collection.returncode != 0:
        _print_command_failure("canonical_collection", collection)
        return 1
    shards = _partition_nodeids(canonical, args.shards)
    partition_errors = _partition_errors(canonical, shards)
    if partition_errors:
        print("in_memory_partition: FAIL")
        for error in partition_errors:
            print(f"- {error}")
        return 1
    file_count = len({nodeid.split("::", 1)[0] for nodeid in canonical})
    print(f"canonical_nodeids={len(canonical)}")
    print(f"canonical_files={file_count}")
    print(f"shard_count={len(shards)}")
    for index, shard in enumerate(shards, start=1):
        print(f"shard_{index:02d}_assigned={len(shard)}")

    with tempfile.TemporaryDirectory(prefix="algotrader_pytest_shards_") as raw_temp:
        temp_root = Path(raw_temp)
        argument_files = _write_argument_files(temp_root, shards)
        recollected: list[tuple[str, ...] | None] = [None] * len(shards)
        collection_failures: list[tuple[int, CommandResult]] = []
        with ThreadPoolExecutor(max_workers=len(shards)) as executor:
            futures = {
                executor.submit(
                    _collect_argument_file,
                    index,
                    path,
                    root=root,
                    env=env,
                    timeout_seconds=args.collection_timeout_seconds,
                ): index
                for index, path in enumerate(argument_files, start=1)
            }
            for future in as_completed(futures):
                index, nodeids, result = future.result()
                if result.returncode != 0:
                    collection_failures.append((index, result))
                else:
                    recollected[index - 1] = nodeids
        if collection_failures:
            for index, result in sorted(collection_failures):
                _print_command_failure(f"shard_{index:02d}_collection", result)
            return 1
        actual_shards = tuple(shard or () for shard in recollected)
        for index, (assigned, actual) in enumerate(
            zip(shards, actual_shards, strict=True),
            start=1,
        ):
            if set(assigned) != set(actual) or len(assigned) != len(actual):
                print(f"shard_{index:02d}_collection_equivalence: FAIL")
                for error in _partition_errors(assigned, (actual,)):
                    print(f"- {error}")
                return 1
        global_errors = _partition_errors(canonical, actual_shards)
        if global_errors:
            print("global_collection_equivalence: FAIL")
            for error in global_errors:
                print(f"- {error}")
            return 1
        print("collection_equivalence=PASS")
        if args.collect_only:
            print("execution=SKIPPED_BY_REQUEST")
            return 0

        print("execution=STARTED")
        shard_results: list[ShardResult] = []
        with ThreadPoolExecutor(max_workers=len(shards)) as executor:
            futures = {
                executor.submit(
                    _execute_shard,
                    index,
                    argument_file,
                    len(shards[index - 1]),
                    root=root,
                    env=env,
                    timeout_seconds=args.timeout_seconds,
                    temp_root=temp_root,
                ): index
                for index, argument_file in enumerate(argument_files, start=1)
            }
            for future in as_completed(futures):
                shard_results.append(future.result())
        shard_results.sort(key=lambda item: item.index)
        failed = False
        summaries: list[JunitSummary] = []
        module_map = _module_to_file(canonical)
        for result in shard_results:
            command = result.command
            print(
                f"shard_{result.index:02d}_result="
                f"exit:{command.returncode},tests:{result.assigned_count},"
                f"wall_seconds:{command.elapsed_seconds:.2f},"
                f"timeout:{str(command.timed_out).lower()}"
            )
            if command.returncode != 0:
                failed = True
                _print_command_failure(f"shard_{result.index:02d}", command)
                continue
            if not result.junit_path.exists():
                failed = True
                print(f"shard_{result.index:02d}_junit: FAIL missing report")
                continue
            try:
                summary = _junit_summary(result.junit_path, module_map)
            except (ET.ParseError, OSError, ValueError) as exc:
                failed = True
                print(f"shard_{result.index:02d}_junit: FAIL {exc}")
                continue
            summaries.append(summary)
            if summary.tests != result.assigned_count:
                failed = True
                print(
                    f"shard_{result.index:02d}_execution_count: FAIL "
                    f"expected={result.assigned_count} observed={summary.tests}"
                )
        if failed:
            print("bounded_full_suite=FAIL")
            return 1

        total_tests = sum(item.tests for item in summaries)
        total_failures = sum(item.failures for item in summaries)
        total_errors = sum(item.errors for item in summaries)
        total_skipped = sum(item.skipped for item in summaries)
        total_passed = sum(item.passed for item in summaries)
        if total_tests != len(canonical):
            print(
                "execution_equivalence=FAIL "
                f"expected={len(canonical)} observed={total_tests}"
            )
            return 1
        file_seconds: defaultdict[str, float] = defaultdict(float)
        for summary in summaries:
            for file_name, seconds in summary.file_seconds.items():
                file_seconds[file_name] += seconds
        print("execution_equivalence=PASS")
        print(
            "aggregate_result="
            f"tests:{total_tests},passed:{total_passed},skipped:{total_skipped},"
            f"failures:{total_failures},errors:{total_errors}"
        )
        print("slowest_files_by_testcase_seconds:")
        for file_name, seconds in sorted(
            file_seconds.items(),
            key=lambda item: (-item[1], item[0]),
        )[: args.top_slowest_files]:
            print(f"- {seconds:.3f}s {file_name}")
        print("bounded_full_suite=PASS")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
