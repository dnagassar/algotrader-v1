from __future__ import annotations

import ast
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.execution import (
    crypto_bounded_probe_safety_certification as certification,
)
from algotrader.execution.crypto_bounded_probe_safety import (
    CRYPTO_BOUNDED_PROBE_SAFETY_POLICY_FINGERPRINT,
)
from algotrader.execution.crypto_bounded_probe_safety_certification import (
    CRYPTO_BOUNDED_PROBE_SAFETY_CERTIFICATION_SCHEMA_VERSION,
    build_crypto_bounded_probe_safety_certification,
    run_crypto_bounded_probe_safety_certification,
    validate_crypto_bounded_probe_safety_certification,
)


NOW = datetime(2026, 7, 16, 18, 0, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[2]
KERNEL = ROOT / "src" / "algotrader" / "execution" / "crypto_bounded_probe_safety.py"
CERTIFIER = (
    ROOT
    / "src"
    / "algotrader"
    / "execution"
    / "crypto_bounded_probe_safety_certification.py"
)
FOCUSED_TEST = ROOT / "tests" / "unit" / "test_crypto_bounded_probe_safety.py"


@pytest.fixture(scope="module")
def source_bytes() -> dict[str, bytes]:
    return {
        "kernel": KERNEL.read_bytes(),
        "certifier": CERTIFIER.read_bytes(),
        "test": FOCUSED_TEST.read_bytes(),
    }


@pytest.fixture(scope="module")
def receipt(source_bytes: dict[str, bytes]) -> dict[str, object]:
    return build_crypto_bounded_probe_safety_certification(
        kernel_source_bytes=source_bytes["kernel"],
        certifier_source_bytes=source_bytes["certifier"],
        focused_test_source_bytes=source_bytes["test"],
        as_of=NOW,
    )


def test_certification_executes_exact_all_symbol_contract(
    receipt: dict[str, object],
) -> None:
    assert receipt["schema_version"] == (
        CRYPTO_BOUNDED_PROBE_SAFETY_CERTIFICATION_SCHEMA_VERSION
    )
    assert receipt["policy_fingerprint"] == (
        CRYPTO_BOUNDED_PROBE_SAFETY_POLICY_FINGERPRINT
    )
    assert receipt["supported_symbols"] == ["BTCUSD", "ETHUSD", "SOLUSD"]
    assert [item["symbol"] for item in receipt["symbol_results"]] == [
        "BTCUSD",
        "ETHUSD",
        "SOLUSD",
    ]
    assert all(item["passed"] is True for item in receipt["symbol_results"])
    assert receipt["claims"]["loss_halt_usd"] == "2"
    assert receipt["claims"]["cancel_exit_path_certified"] is True
    assert receipt["authority"]["paper_mutation_authorized"] is False
    assert receipt["authority"]["live_authorized"] is False


def test_certification_validation_binds_exact_source_bytes(
    receipt: dict[str, object],
    source_bytes: dict[str, bytes],
) -> None:
    validate_crypto_bounded_probe_safety_certification(
        receipt,
        kernel_source_bytes=source_bytes["kernel"],
        certifier_source_bytes=source_bytes["certifier"],
        focused_test_source_bytes=source_bytes["test"],
    )

    with pytest.raises(ValidationError, match="source bytes drifted"):
        validate_crypto_bounded_probe_safety_certification(
            receipt,
            kernel_source_bytes=source_bytes["kernel"] + b"\n# tamper\n",
            certifier_source_bytes=source_bytes["certifier"],
            focused_test_source_bytes=source_bytes["test"],
        )


def test_certification_fingerprint_tamper_fails_closed(
    receipt: dict[str, object],
    source_bytes: dict[str, bytes],
) -> None:
    tampered = json.loads(json.dumps(receipt))
    tampered["claims"]["test_passed"] = False

    with pytest.raises(ValidationError, match="fingerprint mismatch"):
        validate_crypto_bounded_probe_safety_certification(
            tampered,
            kernel_source_bytes=source_bytes["kernel"],
            certifier_source_bytes=source_bytes["certifier"],
            focused_test_source_bytes=source_bytes["test"],
        )


def test_runner_resolves_sources_and_writes_canonical_receipt(tmp_path: Path) -> None:
    output = tmp_path / "certification.json"

    result = run_crypto_bounded_probe_safety_certification(
        kernel_source_path=KERNEL,
        certifier_source_path=CERTIFIER,
        focused_test_source_path=FOCUSED_TEST,
        output_path=output,
        as_of=NOW,
    )

    assert output.read_bytes() == (
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    assert result["authority"]["broker_mutation_occurred"] is False


@pytest.mark.parametrize(
    "role",
    ("kernel", "certifier", "test"),
)
def test_certification_rejects_marker_bearing_noncanonical_source(
    source_bytes: dict[str, bytes],
    role: str,
) -> None:
    supplied = dict(source_bytes)
    supplied[role] += b"\n# marker-preserving but different source\n"

    with pytest.raises(
        ValidationError,
        match="does not match (loaded runtime|canonical bytes)",
    ):
        build_crypto_bounded_probe_safety_certification(
            kernel_source_bytes=supplied["kernel"],
            certifier_source_bytes=supplied["certifier"],
            focused_test_source_bytes=supplied["test"],
            as_of=NOW,
        )


def test_certification_rejects_stale_loaded_runtime_identity(
    source_bytes: dict[str, bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        certification,
        "_LOADED_KERNEL_SOURCE_SHA256",
        "0" * 64,
    )

    with pytest.raises(ValidationError, match="does not match loaded runtime"):
        build_crypto_bounded_probe_safety_certification(
            kernel_source_bytes=source_bytes["kernel"],
            certifier_source_bytes=source_bytes["certifier"],
            focused_test_source_bytes=source_bytes["test"],
            as_of=NOW,
        )


def test_certifier_has_no_broker_network_or_order_construction_imports() -> None:
    tree = ast.parse(CERTIFIER.read_text(encoding="utf-8"), filename=str(CERTIFIER))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert not any(
        name.startswith(("alpaca", "httpx", "requests", "socket", "urllib"))
        for name in imports
    )
    assert calls.isdisjoint(
        {
            "cancel_order",
            "close_position",
            "get_account",
            "get_orders",
            "replace_order",
            "submit_order",
            "urlopen",
        }
    )
