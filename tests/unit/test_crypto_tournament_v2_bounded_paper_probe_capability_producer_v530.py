"""V5.30 exact-family capability production and legacy compatibility tests."""

from __future__ import annotations

from datetime import timedelta
import hashlib
import json
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

from algotrader.core.crypto_bounded_probe_lifecycle import (
    canonical_json_bytes,
    stable_hash,
)
from algotrader.errors import ValidationError
from algotrader.execution.crypto_bounded_probe_independent_flat_operator import (
    run_crypto_bounded_probe_independent_flat_operator,
)
from algotrader.orchestration import (
    crypto_tournament_v2_bounded_paper_probe_capability_producer as legacy,
)
from algotrader.orchestration import (
    crypto_tournament_v2_bounded_paper_probe_capability_producer_v530 as subject,
)
from algotrader.orchestration.crypto_tournament_v2_bounded_paper_probe_lifecycle import (
    build_crypto_tournament_v2_bounded_paper_probe_lifecycle_plan,
)


ROOT = Path(__file__).resolve().parents[2]
PRODUCER_HELPERS = runpy.run_path(
    str(ROOT / "tests" / "unit" / "test_crypto_tournament_v2_capability_producer.py")
)
LIFECYCLE_HELPERS = runpy.run_path(
    str(
        ROOT
        / "tests"
        / "unit"
        / "test_crypto_tournament_v2_bounded_paper_probe_lifecycle_operator.py"
    )
)
FLAT_HELPERS = runpy.run_path(
    str(
        ROOT
        / "tests"
        / "unit"
        / "test_crypto_bounded_probe_independent_flat_operator.py"
    )
)
AS_OF = PRODUCER_HELPERS["AS_OF"]
ACCOUNT_ID = LIFECYCLE_HELPERS["ACCOUNT_ID"]
FROZEN_DIGEST = (
    "31919e9d787c90fa0f5b9444726035f919ed7a57d4bca378d7bcf0941f7efaba"
)


def _pretty_bytes(value: dict[str, object]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _frozen_state_for_terminal(
    terminal: dict[str, object],
) -> dict[str, object]:
    source = dict(terminal["source_binding"])
    return {
        "terminal_outcome_closed": True,
        "preregistration_fingerprint": source[
            "preregistration_fingerprint"
        ],
        "schema_version": source["state_schema_version"],
        "activation_fingerprint": source["activation_fingerprint"],
        "source_state_fingerprint": source[
            "activation_source_state_fingerprint"
        ],
        "state_fingerprint": source["state_fingerprint"],
        "context_sha256": source["context_sha256"],
        "terminal_packet_sha256": source["terminal_packet_sha256"],
        "terminal_evidence_fingerprint": source[
            "terminal_evidence_fingerprint"
        ],
        "terminal_closed_at": source["terminal_closed_at"],
        "artifact_sha256": dict(source["artifact_sha256"]),
    }


def _target_case(
    root: Path,
    symbol: str,
) -> tuple[dict[str, object], dict[str, bytes], object]:
    safety = PRODUCER_HELPERS["_build_safety_sources"]()
    venue = PRODUCER_HELPERS["_build_venue_sources"](
        root / "venue",
        symbol,
    )
    terminal = PRODUCER_HELPERS["TERMINAL_EVIDENCE"](symbol=symbol)
    safety_receipt = json.loads(
        safety["safety_certification_receipt"].decode("utf-8")
    )
    plan = build_crypto_tournament_v2_bounded_paper_probe_lifecycle_plan(
        terminal,
        venue_source_bytes=venue,
        safety_certification=safety_receipt,
        safety_certification_source_sha256=hashlib.sha256(
            safety["safety_certification_receipt"]
        ).hexdigest(),
        safety_kernel_source_bytes=safety["safety_kernel_source"],
        safety_certifier_source_bytes=safety["safety_certifier_source"],
        safety_focused_test_source_bytes=safety[
            "safety_focused_test_source"
        ],
        expected_paper_account_id=ACCOUNT_ID,
        terminal_source_sha256=hashlib.sha256(
            _pretty_bytes(terminal)
        ).hexdigest(),
        as_of=AS_OF,
    )
    lifecycle_at = AS_OF + timedelta(seconds=4)
    lifecycle_root = root / "lifecycle"
    lifecycle_client = LIFECYCLE_HELPERS["StatefulLifecycleClient"](
        symbol,
        now=lifecycle_at,
    )
    lifecycle_receipt = LIFECYCLE_HELPERS["_run"](
        lifecycle_root,
        plan,
        lifecycle_client,
        timestamp=lifecycle_at,
    )
    assert lifecycle_receipt["outcome_classification"] == "filled_exit_confirmed"
    lifecycle_latest = lifecycle_root / "out" / "latest"

    flat_at = AS_OF + timedelta(minutes=1)
    flat_root = root / "flat"
    flat_status = run_crypto_bounded_probe_independent_flat_operator(
        symbol=symbol,
        lifecycle_path=lifecycle_latest / "lifecycle_result.json",
        output_root=flat_root,
        timestamp=flat_at,
        clock=lambda: flat_at,
        env=FLAT_HELPERS["_paper_env"](),
        broker_client_factory=lambda _config: FLAT_HELPERS["FlatPaperClient"](),
        expected_paper_account_id=ACCOUNT_ID,
        independent_flat_read_authorized=True,
        allow_network=True,
        write_artifacts=True,
    )
    assert flat_status["classification"] == "independent_flat_receipt_emitted"

    raw = {
        **safety,
        **venue,
        "target_capability_producer_source": Path(subject.__file__).read_bytes(),
        "target_lifecycle_plan": (
            lifecycle_latest / "lifecycle_plan.json"
        ).read_bytes(),
        "target_lifecycle_receipt": (
            lifecycle_latest / "lifecycle_result.json"
        ).read_bytes(),
        "target_lifecycle_manifest": (
            lifecycle_latest / "manifest.json"
        ).read_bytes(),
        "target_lifecycle_operator_source": (
            ROOT
            / "src"
            / "algotrader"
            / "execution"
            / "crypto_tournament_v2_bounded_paper_probe_lifecycle_operator.py"
        ).read_bytes(),
        "independent_flat_reconciliation": (
            flat_root / "independent_flat_reconciliation.json"
        ).read_bytes(),
        "independent_flat_status": (
            flat_root / "latest_status.json"
        ).read_bytes(),
        "independent_flat_manifest": (
            flat_root / "independent_flat_manifest.json"
        ).read_bytes(),
        "independent_flat_operator_source": (
            ROOT
            / "src"
            / "algotrader"
            / "execution"
            / "crypto_bounded_probe_independent_flat_operator.py"
        ).read_bytes(),
    }
    assert set(raw) == set(subject._TARGET_INPUT_ARTIFACT_PATHS)
    return terminal, raw, flat_at


@pytest.fixture(scope="module")
def target_cases(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, tuple[dict[str, object], dict[str, bytes], object]]:
    root = tmp_path_factory.mktemp("v530_target_family")
    return {
        symbol: _target_case(root / symbol.lower(), symbol)
        for symbol in ("BTCUSD", "ETHUSD", "SOLUSD")
    }


@pytest.mark.parametrize("symbol", ("BTCUSD", "ETHUSD", "SOLUSD"))
def test_genuine_target_family_emits_exact_winner_bundle(
    target_cases: dict[
        str,
        tuple[dict[str, object], dict[str, bytes], object],
    ],
    symbol: str,
) -> None:
    terminal, raw, produced_at = target_cases[symbol]

    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            terminal,
            resolved_input_bytes=raw,
            as_of=produced_at,
        )
    )

    assert production.status["classification"] == (
        "selected_winner_capability_bundle_emitted"
    ), production.status["blockers"]
    assert production.status["review_preview_classification"] == (
        "eligible_for_operator_review_only"
    )
    assert production.status["capability_bundle_emitted"] is True, (
        production.status["blockers"]
    )
    for role, artifact_name in subject._TARGET_INPUT_ARTIFACT_PATHS.items():
        assert production.artifacts[artifact_name] == raw[role]


def test_exact_legacy_family_delegates_byte_identically(
    target_cases: dict[
        str,
        tuple[dict[str, object], dict[str, bytes], object],
    ],
) -> None:
    terminal, target_raw, _ = target_cases["BTCUSD"]
    shared = {
        role: target_raw[role]
        for role in subject._COMMON_TARGET_INPUT_ARTIFACT_PATHS
        if role != "independent_flat_reconciliation"
    }
    legacy_raw = PRODUCER_HELPERS["_raw_sources"](
        shared,
        symbol="BTCUSD",
    )

    expected = legacy.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
        terminal,
        resolved_input_bytes=legacy_raw,
        as_of=AS_OF,
    )
    actual = subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
        terminal,
        resolved_input_bytes=legacy_raw,
        as_of=AS_OF,
    )

    assert actual == expected
    assert hashlib.sha256(Path(legacy.__file__).read_bytes()).hexdigest() == (
        FROZEN_DIGEST
    )


def test_partial_mixed_and_extra_target_families_fail_closed(
    target_cases: dict[
        str,
        tuple[dict[str, object], dict[str, bytes], object],
    ],
) -> None:
    terminal, raw, produced_at = target_cases["BTCUSD"]

    partial = dict(raw)
    partial.pop("target_lifecycle_manifest")
    with pytest.raises(ValidationError, match="partial V5.30"):
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            terminal,
            resolved_input_bytes=partial,
            as_of=produced_at,
        )

    mixed = dict(raw)
    mixed["paper_oms_dry_run"] = b"legacy-only"
    with pytest.raises(ValidationError, match="mixed legacy and V5.30"):
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            terminal,
            resolved_input_bytes=mixed,
            as_of=produced_at,
        )

    extra = dict(raw)
    extra["unknown_target_role"] = b"extra"
    with pytest.raises(ValidationError, match="partial V5.30"):
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            terminal,
            resolved_input_bytes=extra,
            as_of=produced_at,
        )


@pytest.mark.parametrize(
    "tamper",
    (
        "operator_source",
        "manifest_digest",
        "nested_authorization",
        "order_shape",
    ),
)
def test_target_source_and_nested_tampering_blocks_emission(
    target_cases: dict[
        str,
        tuple[dict[str, object], dict[str, bytes], object],
    ],
    tamper: str,
) -> None:
    terminal, source_raw, produced_at = target_cases["BTCUSD"]
    raw = dict(source_raw)
    if tamper == "operator_source":
        raw["target_lifecycle_operator_source"] += b"\n# tamper\n"
    elif tamper == "manifest_digest":
        manifest = json.loads(
            raw["target_lifecycle_manifest"].decode("utf-8")
        )
        manifest["receipt_sha256"] = "0" * 64
        manifest["manifest_fingerprint"] = stable_hash(
            {
                key: value
                for key, value in manifest.items()
                if key != "manifest_fingerprint"
            }
        )
        raw["target_lifecycle_manifest"] = canonical_json_bytes(manifest)
    elif tamper == "nested_authorization":
        receipt = json.loads(
            raw["target_lifecycle_receipt"].decode("utf-8")
        )
        receipt["authorization"]["injected_authority"] = False
        receipt["lifecycle_fingerprint"] = stable_hash(
            {
                key: value
                for key, value in receipt.items()
                if key != "lifecycle_fingerprint"
            }
        )
        raw["target_lifecycle_receipt"] = canonical_json_bytes(receipt)
    else:
        receipt = json.loads(
            raw["target_lifecycle_receipt"].decode("utf-8")
        )
        entry_order = receipt["entry_final_order"]
        entry_order["asset_class"] = "equity"
        entry_order["order_fingerprint"] = stable_hash(
            {
                key: value
                for key, value in entry_order.items()
                if key != "order_fingerprint"
            }
        )
        receipt["lifecycle_fingerprint"] = stable_hash(
            {
                key: value
                for key, value in receipt.items()
                if key != "lifecycle_fingerprint"
            }
        )
        raw["target_lifecycle_receipt"] = canonical_json_bytes(receipt)
        manifest = json.loads(
            raw["target_lifecycle_manifest"].decode("utf-8")
        )
        manifest["receipt_sha256"] = hashlib.sha256(
            raw["target_lifecycle_receipt"]
        ).hexdigest()
        manifest["manifest_fingerprint"] = stable_hash(
            {
                key: value
                for key, value in manifest.items()
                if key != "manifest_fingerprint"
            }
        )
        raw["target_lifecycle_manifest"] = canonical_json_bytes(manifest)

    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            terminal,
            resolved_input_bytes=raw,
            as_of=produced_at,
        )
    )

    assert production.status["classification"] == (
        "selected_winner_operational_evidence_blocked"
    )
    assert production.status["capability_bundle_emitted"] is False
    assert not any(
        name.startswith("bundle/") for name in production.artifacts
    )



def test_target_family_preserves_exact_terminal_source_bytes(
    target_cases: dict[
        str,
        tuple[dict[str, object], dict[str, bytes], object],
    ],
) -> None:
    terminal, raw, produced_at = target_cases["BTCUSD"]
    terminal_bytes = _pretty_bytes(terminal)

    production = (
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            terminal,
            resolved_input_bytes=raw,
            terminal_evidence_source_bytes=terminal_bytes,
            as_of=produced_at,
        )
    )

    assert production.status["capability_bundle_emitted"] is True
    assert production.artifacts["inputs/terminal_evidence.json"] == (
        terminal_bytes
    )
    drifted_bytes = _pretty_bytes({**terminal, "as_of": "2099-01-01T00:00:00+00:00"})
    with pytest.raises(ValidationError, match="do not match the mapping"):
        subject.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            terminal,
            resolved_input_bytes=raw,
            terminal_evidence_source_bytes=drifted_bytes,
            as_of=produced_at,
        )


def test_target_runner_prefers_pinned_terminal_without_reexport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = PRODUCER_HELPERS["TERMINAL_EVIDENCE"](
        symbol="BTCUSD"
    )
    terminal_bytes = _pretty_bytes(terminal)
    terminal_path = tmp_path / "terminal_evidence.json"
    terminal_path.write_bytes(terminal_bytes)
    shadow_root = tmp_path / "shadow"
    shadow_root.mkdir()
    (shadow_root / "frozen_state.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        legacy,
        "run_crypto_tournament_v2_forward_shadow_state",
        lambda **_: {"frozen_state": _frozen_state_for_terminal(terminal)},
    )
    reference_calls: list[object] = []

    def export_reference(**_: object) -> dict[str, object]:
        reference_calls.append(object())
        return {**terminal, "as_of": AS_OF.isoformat()}

    monkeypatch.setattr(
        legacy,
        "export_crypto_tournament_v2_forward_shadow_terminal_evidence",
        export_reference,
    )
    monkeypatch.setattr(
        legacy,
        "build_crypto_tournament_v2_bounded_paper_probe_capability_production",
        lambda *args, **kwargs: SimpleNamespace(
            status={
                "classification": (
                    "selected_winner_operational_evidence_blocked"
                )
            },
            artifacts={},
        ),
    )
    monkeypatch.setattr(subject, "_TARGET_INPUT_ARTIFACT_PATHS", {})
    captured: dict[str, object] = {}

    def fake_target_builder(
        terminal_evidence: object,
        **kwargs: object,
    ) -> SimpleNamespace:
        captured["terminal_evidence"] = terminal_evidence
        captured.update(kwargs)
        return SimpleNamespace(
            status={
                "classification": (
                    "selected_winner_capability_bundle_emitted"
                ),
                "capability_bundle_emitted": True,
            },
            artifacts={},
        )

    monkeypatch.setattr(
        subject,
        "build_crypto_tournament_v2_bounded_paper_probe_capability_production",
        fake_target_builder,
    )

    status = subject.run_crypto_tournament_v2_bounded_paper_probe_capability_producer(
        shadow_root=shadow_root,
        output_root=tmp_path / "output",
        target_terminal_evidence_path=terminal_path,
        as_of=AS_OF,
        write_artifacts=False,
    )

    assert status["capability_bundle_emitted"] is True
    assert captured["terminal_evidence"] == terminal
    assert captured["terminal_evidence_source_bytes"] == terminal_bytes


    assert len(reference_calls) == 1

def test_target_runner_rejects_pinned_terminal_winner_spoof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = PRODUCER_HELPERS["TERMINAL_EVIDENCE"](symbol="BTCUSD")
    tampered = json.loads(json.dumps(terminal))
    tampered["selected_candidate"]["candidate_id"] = "spoofed-winner"
    identity = {
        key: value
        for key, value in tampered.items()
        if key not in {"as_of", "evidence_export_fingerprint"}
    }
    tampered["evidence_export_fingerprint"] = stable_hash(identity)
    terminal_path = tmp_path / "terminal_evidence.json"
    terminal_path.write_bytes(_pretty_bytes(tampered))
    shadow_root = tmp_path / "shadow"
    shadow_root.mkdir()
    (shadow_root / "frozen_state.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        legacy,
        "run_crypto_tournament_v2_forward_shadow_state",
        lambda **_: {"frozen_state": _frozen_state_for_terminal(terminal)},
    )
    monkeypatch.setattr(
        legacy,
        "export_crypto_tournament_v2_forward_shadow_terminal_evidence",
        lambda **_: terminal,
    )

    with pytest.raises(
        ValidationError,
        match="does not match current frozen shadow",
    ):
        subject.run_crypto_tournament_v2_bounded_paper_probe_capability_producer(
            shadow_root=shadow_root,
            output_root=tmp_path / "output",
            target_terminal_evidence_path=terminal_path,
            as_of=AS_OF,
            write_artifacts=False,
        )


def test_target_cli_rejects_abbreviated_options() -> None:
    with pytest.raises(SystemExit):
        subject.build_parser().parse_args(["--shadow-r", "ignored"])
def test_target_runner_rejects_pinned_terminal_from_other_shadow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = PRODUCER_HELPERS["TERMINAL_EVIDENCE"](
        symbol="BTCUSD"
    )
    terminal_path = tmp_path / "terminal_evidence.json"
    terminal_path.write_bytes(_pretty_bytes(terminal))
    shadow_root = tmp_path / "shadow"
    shadow_root.mkdir()
    (shadow_root / "frozen_state.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    frozen_state = _frozen_state_for_terminal(terminal)
    frozen_state["terminal_evidence_fingerprint"] = "0" * 64
    monkeypatch.setattr(
        legacy,
        "run_crypto_tournament_v2_forward_shadow_state",
        lambda **_: {"frozen_state": frozen_state},
    )
    monkeypatch.setattr(
        legacy,
        "export_crypto_tournament_v2_forward_shadow_terminal_evidence",
        lambda **_: terminal,
    )

    with pytest.raises(
        ValidationError,
        match="does not match current frozen shadow",
    ):
        subject.run_crypto_tournament_v2_bounded_paper_probe_capability_producer(
            shadow_root=shadow_root,
            output_root=tmp_path / "output",
            target_terminal_evidence_path=terminal_path,
            as_of=AS_OF,
            write_artifacts=False,
        )


@pytest.mark.parametrize(
    ("status", "expected"),
    (
        (
            {
                "classification": (
                    "selected_winner_capability_bundle_emitted"
                ),
                "capability_bundle_emitted": True,
            },
            0,
        ),
        (
            {
                "classification": (
                    "selected_winner_operational_evidence_blocked"
                ),
                "capability_bundle_emitted": False,
            },
            2,
        ),
    ),
)
def test_target_main_exit_code_is_truthful(
    monkeypatch: pytest.MonkeyPatch,
    status: dict[str, object],
    expected: int,
) -> None:
    monkeypatch.setattr(
        subject,
        "run_crypto_tournament_v2_bounded_paper_probe_capability_producer",
        lambda **_: status,
    )

    assert subject.main(["--as-of", AS_OF.isoformat(), "--no-write"]) == expected
