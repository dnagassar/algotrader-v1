from __future__ import annotations

import ast
import inspect
import json
import re
import sys
from dataclasses import replace

import pytest

from algotrader.errors import ValidationError
from algotrader.research import (
    research_return_input_result_adapter as result_adapter_module,
)
from algotrader.research.research_return_input import ResearchReturnInputSnapshot
from algotrader.research.research_return_input_consistency import (
    validate_research_return_input_snapshot_consistency,
)
from algotrader.research.research_return_input_fingerprint import (
    research_return_input_snapshot_fingerprint,
)
from algotrader.research.research_return_input_package import (
    ResearchReturnInputPackage,
    build_research_return_input_package,
)
from algotrader.research.research_return_input_replay_adapter import (
    build_synthetic_replay_snapshot_from_return_input_package,
)
from algotrader.research.research_return_input_result_adapter import (
    build_synthetic_research_result_from_return_input_package,
)
from algotrader.research.research_return_input_result_provenance import (
    validate_research_result_matches_return_input_package,
)
from tests.fixtures.research_return_input import (
    build_synthetic_research_return_input_snapshot,
)
from tests.fixtures.research_return_input_result import (
    build_synthetic_return_input_research_result,
    expected_synthetic_return_input_research_result_dict,
)


_PINNED_DIGEST = (
    "07bc8b37a15dfefb2d8d80c130ac12a15783b2e7af1acd0e2a885afe0d3585e2"
)


def test_complete_existing_chain_reaches_verified_result_without_drift() -> None:
    chain = _build_chain()
    snapshot = chain["snapshot"]
    checked_snapshot = chain["checked_snapshot"]
    package = chain["package"]
    package_payload = chain["package_payload"]
    package_payload_before = chain["package_payload_before"]
    round_tripped_package = chain["round_tripped_package"]
    replay_snapshot = chain["replay_snapshot"]
    result = chain["result"]
    fixture_result = chain["fixture_result"]

    assert checked_snapshot is snapshot
    assert chain["digest"] == _PINNED_DIGEST
    assert package.snapshot is snapshot
    assert package.fingerprint == _PINNED_DIGEST
    assert package_payload == package_payload_before

    assert round_tripped_package.fingerprint == package.fingerprint
    assert round_tripped_package.snapshot == snapshot
    assert round_tripped_package.snapshot is not snapshot

    manifest = replay_snapshot.manifest
    assert manifest.fixture_id == round_tripped_package.snapshot.snapshot_id
    assert manifest.checksum == f"sha256:{round_tripped_package.fingerprint}"

    assert tuple(
        point.observation.observation_date
        for point in replay_snapshot.available_points
    ) == snapshot.observation_dates
    assert tuple(
        point.observation.available_after for point in replay_snapshot.available_points
    ) == snapshot.observation_dates
    assert tuple(point.value for point in replay_snapshot.available_points) == (
        snapshot.close_values
    )
    assert replay_snapshot.returns is (
        round_tripped_package.snapshot.close_to_close_returns
    )
    assert replay_snapshot.returns == snapshot.close_to_close_returns

    assert result.snapshot == replay_snapshot
    assert fixture_result == result
    assert fixture_result.to_dict() == result.to_dict()
    assert result.to_dict() == expected_synthetic_return_input_research_result_dict()
    assert chain["verified"] is result


def test_result_adapter_receives_replay_snapshot_from_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = build_research_return_input_package(
        build_synthetic_research_return_input_snapshot()
    )
    replay_snapshot = build_synthetic_replay_snapshot_from_return_input_package(
        package
    )
    calls: list[object] = []

    def replay_adapter(value: object) -> object:
        calls.append(value)
        return replay_snapshot

    monkeypatch.setattr(
        result_adapter_module,
        "build_synthetic_replay_snapshot_from_return_input_package",
        replay_adapter,
    )

    result = (
        result_adapter_module.build_synthetic_research_result_from_return_input_package(
            package
        )
    )

    assert calls == [package]
    assert result.snapshot is replay_snapshot


def test_repeated_complete_chain_construction_is_deterministic() -> None:
    assert _chain_payload() == _chain_payload()


def test_mutated_copied_primitive_payload_fails_existing_checks() -> None:
    snapshot = build_synthetic_research_return_input_snapshot()
    package = build_research_return_input_package(snapshot)
    payload = _copy_primitive(package.to_dict())
    nested_snapshot = payload["snapshot"]
    assert isinstance(nested_snapshot, dict)
    close_values = nested_snapshot["close_values"]
    assert isinstance(close_values, list)
    close_values[1] = "10.6000"

    mutated_snapshot = ResearchReturnInputSnapshot.from_dict(nested_snapshot)
    with pytest.raises(ValidationError, match="close_to_close_returns"):
        validate_research_return_input_snapshot_consistency(mutated_snapshot)
    with pytest.raises(ValidationError, match="close_to_close_returns"):
        research_return_input_snapshot_fingerprint(mutated_snapshot)
    with pytest.raises(ValidationError, match="close_to_close_returns"):
        ResearchReturnInputPackage.from_dict(payload)

    result = build_synthetic_research_result_from_return_input_package(package)
    bad_manifest = replace(
        result.snapshot.manifest,
        checksum=f"sha256:{'0' * 64}",
    )
    bad_result = replace(
        result,
        snapshot=replace(result.snapshot, manifest=bad_manifest),
    )

    with pytest.raises(ValidationError, match="checksum"):
        validate_research_result_matches_return_input_package(package, bad_result)


def test_result_payload_adds_no_disallowed_fields() -> None:
    result = build_synthetic_return_input_research_result()
    payload = result.to_dict()
    disallowed = _disallowed_payload_fields()

    assert _payload_keys(payload).isdisjoint(disallowed)
    assert all(not hasattr(result, field_name) for field_name in disallowed)
    assert all(not hasattr(result.snapshot, field_name) for field_name in disallowed)
    assert all(not hasattr(result.summary, field_name) for field_name in disallowed)


def test_module_imports_and_calls_stay_inside_existing_chain() -> None:
    tree = _module_tree()
    imports = _import_references(tree)
    blocked_imports = _blocked_import_prefixes()

    assert [
        name for name in imports if _matches_prefix(name, blocked_imports)
    ] == []
    assert _call_names(tree).isdisjoint(_blocked_call_names())


def test_module_text_has_no_disallowed_literal_content() -> None:
    source = _module_source()
    lowered = source.lower()
    upper_source = source.upper()

    for code_points in _real_symbol_codes():
        symbol = "".join(chr(code_point) for code_point in code_points)
        assert re.search(rf"(?<![A-Z0-9]){symbol}(?![A-Z0-9])", upper_source) is None
    for term in _disallowed_literal_terms():
        assert term not in lowered


def _build_chain() -> dict[str, object]:
    snapshot = build_synthetic_research_return_input_snapshot()
    checked_snapshot = validate_research_return_input_snapshot_consistency(snapshot)
    digest = research_return_input_snapshot_fingerprint(checked_snapshot)
    package = build_research_return_input_package(checked_snapshot)
    package_payload = package.to_dict()
    package_payload_before = _copy_primitive(package_payload)
    round_tripped_package = ResearchReturnInputPackage.from_dict(package_payload)
    replay_snapshot = build_synthetic_replay_snapshot_from_return_input_package(
        round_tripped_package
    )
    result = build_synthetic_research_result_from_return_input_package(
        round_tripped_package
    )
    fixture_result = build_synthetic_return_input_research_result()
    verified = validate_research_result_matches_return_input_package(
        round_tripped_package,
        result,
    )

    return {
        "snapshot": snapshot,
        "checked_snapshot": checked_snapshot,
        "digest": digest,
        "package": package,
        "package_payload": package_payload,
        "package_payload_before": package_payload_before,
        "round_tripped_package": round_tripped_package,
        "replay_snapshot": replay_snapshot,
        "result": result,
        "fixture_result": fixture_result,
        "verified": verified,
    }


def _chain_payload() -> dict[str, object]:
    chain = _build_chain()

    return {
        "snapshot": chain["snapshot"].to_dict(),
        "digest": chain["digest"],
        "package": chain["package"].to_dict(),
        "round_tripped_package": chain["round_tripped_package"].to_dict(),
        "replay_snapshot": chain["replay_snapshot"].to_dict(),
        "result": chain["result"].to_dict(),
        "fixture_result": chain["fixture_result"].to_dict(),
        "verified": chain["verified"].to_dict(),
    }


def _copy_primitive(payload: dict[str, object]) -> dict[str, object]:
    copied = json.loads(json.dumps(payload, sort_keys=True))
    assert isinstance(copied, dict)
    return copied


def _payload_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys: set[str] = set()
        for key, nested_value in value.items():
            keys.add(str(key))
            keys.update(_payload_keys(nested_value))
        return keys

    if isinstance(value, list):
        keys = set()
        for nested_value in value:
            keys.update(_payload_keys(nested_value))
        return keys

    return set()


def _disallowed_payload_fields() -> set[str]:
    bucket_a = _s("ca", "sh")
    bucket_b = _s("co", "st")
    one = {
        _s("bench", "mark"),
        _s("bench", "marks"),
        bucket_a,
        f"{bucket_a}_return",
        f"{bucket_a}_returns",
        bucket_b,
        f"{bucket_b}s",
        _s("po", "sition"),
        _s("po", "sitions"),
        _s("or", "der"),
        _s("or", "ders"),
        _s("fi", "ll"),
        _s("fi", "lls"),
        _s("sig", "nal"),
        _s("sig", "nals"),
        _s("stra", "tegy"),
        _s("stra", "tegy_state"),
        _s("bro", "ker"),
        _s("bro", "kers"),
        _s("run", "time"),
        _s("run", "times"),
        _s("port", "folio"),
        _s("port", "folios"),
        _s("tra", "de"),
        _s("tra", "des"),
    }
    return one


def _module_source() -> str:
    return inspect.getsource(sys.modules[__name__])


def _module_tree() -> ast.AST:
    return ast.parse(_module_source())


def _import_references(tree: ast.AST) -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
            elif node.level > 0:
                imports.add("__future__")

    return imports


def _call_names(tree: ast.AST) -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""


def _matches_prefix(value: str, prefixes: set[str]) -> bool:
    return any(value == prefix or value.startswith(f"{prefix}.") for prefix in prefixes)


def _blocked_import_prefixes() -> set[str]:
    return {
        _s("aio", "http"),
        _s("algotrader.", "bro", "ker"),
        _s("algotrader.", "bro", "kers"),
        _s("algotrader.", "execution"),
        _s("algotrader.", "llm"),
        _s("algotrader.", "llms"),
        _s("algotrader.", "ml"),
        _s("algotrader.", "orchestration"),
        _s("algotrader.", "persist", "ence"),
        _s("algotrader.", "port", "folio"),
        _s("algotrader.", "risk"),
        _s("algotrader.", "run", "time"),
        _s("algotrader.", "scheduler"),
        _s("algotrader.", "screener"),
        _s("algotrader.", "sig", "nals"),
        _s("al", "paca"),
        _s("al", "paca_", "trade_", "a", "pi"),
        _s("data", "base"),
        _s("duck", "db"),
        _s("http", "x"),
        _s("mas", "sive"),
        _s("num", "py"),
        _s("pan", "das"),
        _s("poly", "gon"),
        _s("poly", "gon_", "a", "pi", "_client"),
        _s("quant", "connect"),
        _s("re", "quests"),
        _s("so", "cket"),
        _s("sql", "model"),
        _s("url", "lib"),
        _s("vector", "bt"),
        _s("y", "finance"),
    }


def _blocked_call_names() -> set[str]:
    return {
        "__import__",
        _s("con", "nect"),
        _s("down", "load"),
        "eval",
        "exec",
        _s("exists"),
        _s("get", "env"),
        _s("glob"),
        _s("import", "_module"),
        _s("ing", "est"),
        _s("is", "_file"),
        _s("iter", "dir"),
        _s("mk", "dir"),
        _s("open"),
        _s("parse"),
        _s("persist"),
        _s("post"),
        _s("read"),
        _s("read", "_bytes"),
        _s("read", "_csv"),
        _s("read", "_text"),
        _s("request"),
        _s("re", "quests.get"),
        _s("r", "glob"),
        _s("so", "cket.socket"),
        _s("stat"),
        _s("submit", "_", "or", "der"),
        _s("to", "_sql"),
        _s("url", "open"),
        _s("walk"),
        _s("write"),
        _s("write", "_text"),
    }


def _disallowed_literal_terms() -> set[str]:
    wire = _s("a", "pi")
    auth = {
        f"{wire}_key",
        f"{wire}key",
        _s("bear", "er"),
        _s("client", "_", "sec", "ret"),
        _s("cred", "ential"),
        _s("oa", "uth"),
        _s("pass", "word"),
        _s("private", "_key"),
        _s("sec", "ret"),
        _s("to", "ken"),
    }
    locations = {
        _s(":", chr(47), chr(47)),
        _s("http", ":"),
        _s("https", ":"),
        _s("www", "."),
        _s(".", "com"),
        _s(".", "data", chr(47)),
        _s(".", "csv"),
        _s(".", "jsonl"),
        _s(".", "parquet"),
        _s(".", "zip"),
        chr(47),
        chr(92),
    }
    external = {
        wire,
        _s("net", "work"),
        _s("persist", "ence"),
        _s("al", "paca"),
        _s("alpha", " vantage"),
        _s("bloom", "berg"),
        _s("fact", "set"),
        _s("finn", "hub"),
        _s("fr", "ed"),
        _s("interactive ", "bro", "kers"),
        _s("mas", "sive"),
        _s("morning", "star"),
        _s("nas", "daq"),
        _s("poly", "gon"),
        _s("quant", "connect"),
        _s("quan", "dl"),
        _s("ref", "initiv"),
        _s("sto", "oq"),
        _s("tii", "ngo"),
        _s("ya", "hoo"),
        _s("y", "finance"),
    }
    return auth | locations | external | (_disallowed_payload_fields() - {_s("tra", "de"), _s("tra", "des")})


def _real_symbol_codes() -> tuple[tuple[int, ...], ...]:
    return (
        (83, 80, 89),
        (73, 86, 86),
        (86, 79, 79),
        (81, 81, 81),
        (86, 84, 73),
        (73, 87, 77),
        (68, 73, 65),
        (65, 71, 71),
        (66, 78, 68),
        (84, 76, 84),
        (71, 76, 68),
        (69, 70, 65),
        (69, 69, 77),
        (88, 76, 75),
        (88, 76, 70),
        (88, 76, 69),
        (88, 76, 86),
        (88, 76, 85),
        (88, 76, 73),
        (88, 76, 89),
        (88, 76, 80),
        (88, 76, 82, 69),
    )


def _s(*parts: str) -> str:
    return "".join(parts)
