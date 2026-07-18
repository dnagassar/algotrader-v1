from __future__ import annotations

import ast
from datetime import timedelta
import json
from pathlib import Path
import runpy

import pytest

from algotrader.certification.crypto_tournament_v2_bounded_paper_probe_generation_replay import (
    replay_crypto_tournament_v2_bounded_paper_probe_generation,
    replay_crypto_tournament_v2_bounded_paper_probe_review_generation,
)
from algotrader.errors import ValidationError
from algotrader.orchestration import (
    crypto_tournament_v2_bounded_paper_probe_capability_producer as producer,
    crypto_tournament_v2_bounded_paper_probe_capability_producer_v530
    as target_producer,
    crypto_tournament_v2_bounded_paper_probe_review as review,
)


ROOT = Path(__file__).resolve().parents[2]
PRODUCER_TEST = ROOT / "tests" / "unit" / (
    "test_crypto_tournament_v2_capability_producer.py"
)
V530_PRODUCER_TEST = ROOT / "tests" / "unit" / (
    "test_crypto_tournament_v2_bounded_paper_probe_capability_producer_v530.py"
)
V530_HELPERS = runpy.run_path(str(V530_PRODUCER_TEST))
HELPERS = runpy.run_path(str(PRODUCER_TEST))
TERMINAL_EVIDENCE = HELPERS["TERMINAL_EVIDENCE"]
AS_OF = HELPERS["AS_OF"]
BUILD_SAFETY_SOURCES = HELPERS["_build_safety_sources"]
BUILD_VENUE_SOURCES = HELPERS["_build_venue_sources"]
RAW_SOURCES = HELPERS["_raw_sources"]
MODULE = ROOT / "src" / "algotrader" / "certification" / (
    "crypto_tournament_v2_bounded_paper_probe_generation_replay.py"
)


@pytest.fixture(scope="module")
def complete_production(
    tmp_path_factory: pytest.TempPathFactory,
) -> producer.CryptoBoundedProbeCapabilityProduction:
    safety = {
        **BUILD_SAFETY_SOURCES(),
        **BUILD_VENUE_SOURCES(tmp_path_factory.mktemp("replay_venue")),
    }
    return producer.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
        TERMINAL_EVIDENCE(),
        resolved_input_bytes=RAW_SOURCES(safety, symbol="BTCUSD"),
        as_of=AS_OF,
    )
@pytest.fixture(scope="module")
def target_complete_production(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[producer.CryptoBoundedProbeCapabilityProduction, object]:
    terminal, raw, produced_at = V530_HELPERS["_target_case"](
        tmp_path_factory.mktemp("replay_v530"),
        "BTCUSD",
    )
    production = (
        target_producer.build_crypto_tournament_v2_bounded_paper_probe_capability_production(
            terminal,
            resolved_input_bytes=raw,
            as_of=produced_at,
        )
    )
    assert production.status["capability_bundle_emitted"] is True
    return production, produced_at


def _publish(
    root: Path,
    production: producer.CryptoBoundedProbeCapabilityProduction,
) -> str:
    latest = producer._publish_production(root, production)
    return str(latest["publication_fingerprint"])


def _publish_review(
    root: Path,
    production: producer.CryptoBoundedProbeCapabilityProduction,
    *,
    packet_mutation: str = "",
) -> str:
    capability_root = root / "capabilities"
    producer._publish_production(capability_root, production)
    (
        capabilities,
        capability_hashes,
        sources,
        source_hashes,
        upstreams,
        upstream_hashes,
        support,
    ) = review._load_capability_artifacts(capability_root)
    terminal_bytes = production.artifacts[
        "inputs/terminal_evidence.json"
    ]
    terminal = producer._json_mapping(
        terminal_bytes,
        "terminal_evidence",
    )
    producer._require_canonical_json(
        terminal_bytes,
        terminal,
        "terminal_evidence",
    )
    review_at = producer._utc_datetime(production.status["as_of"], "as_of")
    packet = review.build_crypto_tournament_v2_bounded_paper_probe_review(
        terminal,
        capability_evidence=capabilities,
        capability_artifact_sha256=capability_hashes,
        capability_source_evidence=sources,
        capability_source_artifact_sha256=source_hashes,
        capability_upstream_evidence=upstreams,
        capability_upstream_artifact_sha256=upstream_hashes,
        as_of=review_at,
    )
    if packet_mutation:
        packet = json.loads(json.dumps(packet))
        packet["next_action"] = packet_mutation
    review_root = root / "review"
    latest = review._publish_review_artifacts(
        review_root,
        preregistration=(
            review.build_crypto_tournament_v2_bounded_paper_probe_preregistration()
        ),
        packet=packet,
        markdown=(
            review.render_crypto_tournament_v2_bounded_paper_probe_review_markdown(
                packet
            )
        ),
        terminal_evidence=terminal,
        terminal_evidence_bytes=terminal_bytes,
        capability_evidence=capabilities,
        capability_source_evidence=sources,
        capability_upstream_evidence=upstreams,
        capability_support_artifacts=support,
    )
    return str(latest["publication_fingerprint"])


def test_pinned_generation_replays_sources_and_certification_exactly(
    tmp_path: Path,
    complete_production: producer.CryptoBoundedProbeCapabilityProduction,
) -> None:
    root = tmp_path / "capabilities"
    fingerprint = _publish(root, complete_production)

    replay = replay_crypto_tournament_v2_bounded_paper_probe_generation(
        root,
        expected_publication_fingerprint=fingerprint,
        trusted_current_utc=AS_OF,
    )

    assert replay["classification"] == "eligible_for_operator_review_only"
    assert replay["historical_reproduction_equal"] is True
    assert replay["safety_certification_reexecuted"] is True
    assert replay["review_fingerprint"] == (
        complete_production.status["review_preview_fingerprint"]
    )
    assert replay["paper_mutation_authorized"] is False
    assert replay["capital_allocation_authorized"] is False
    assert replay["live_authorized"] is False


def test_replay_freshness_boundary_is_exact(
    tmp_path: Path,
    complete_production: producer.CryptoBoundedProbeCapabilityProduction,
) -> None:
    root = tmp_path / "capabilities"
    fingerprint = _publish(root, complete_production)

    exact = replay_crypto_tournament_v2_bounded_paper_probe_generation(
        root,
        expected_publication_fingerprint=fingerprint,
        trusted_current_utc=AS_OF,
    )
    expired = replay_crypto_tournament_v2_bounded_paper_probe_generation(
        root,
        expected_publication_fingerprint=fingerprint,
        trusted_current_utc=AS_OF + timedelta(microseconds=1),
    )

    assert exact["classification"] == "eligible_for_operator_review_only"
    assert expired["classification"] == "blocked"
    assert expired["review_fingerprint"] == ""
    assert expired["paper_mutation_authorized"] is False


def test_recomputed_outer_hashes_cannot_hide_source_tamper(
    tmp_path: Path,
    complete_production: producer.CryptoBoundedProbeCapabilityProduction,
) -> None:
    artifacts = dict(complete_production.artifacts)
    kernel_path = producer._INPUT_ARTIFACT_PATHS["safety_kernel_source"]
    artifacts[kernel_path] += b"\n# semantically unbound tamper\n"
    tampered = producer.CryptoBoundedProbeCapabilityProduction(
        status=complete_production.status,
        artifacts=artifacts,
    )
    root = tmp_path / "tampered"
    fingerprint = _publish(root, tampered)

    with pytest.raises(ValidationError, match="historical reproduction"):
        replay_crypto_tournament_v2_bounded_paper_probe_generation(
            root,
            expected_publication_fingerprint=fingerprint,
            trusted_current_utc=AS_OF,
        )


def test_recomputed_outer_hashes_cannot_hide_duplicate_json_keys(
    tmp_path: Path,
    complete_production: producer.CryptoBoundedProbeCapabilityProduction,
) -> None:
    artifacts = dict(complete_production.artifacts)
    venue_path = producer._INPUT_ARTIFACT_PATHS["orderability_metadata"]
    artifacts[venue_path] = b'{"schema_version":"x","schema_version":"y"}\n'
    tampered = producer.CryptoBoundedProbeCapabilityProduction(
        status=complete_production.status,
        artifacts=artifacts,
    )
    root = tmp_path / "duplicate"
    fingerprint = _publish(root, tampered)

    with pytest.raises(ValidationError, match="historical reproduction"):
        replay_crypto_tournament_v2_bounded_paper_probe_generation(
            root,
            expected_publication_fingerprint=fingerprint,
            trusted_current_utc=AS_OF,
        )


def test_wrong_pinned_fingerprint_and_unmanifested_file_fail_closed(
    tmp_path: Path,
    complete_production: producer.CryptoBoundedProbeCapabilityProduction,
) -> None:
    root = tmp_path / "capabilities"
    fingerprint = _publish(root, complete_production)

    with pytest.raises(ValidationError, match="generation is absent"):
        replay_crypto_tournament_v2_bounded_paper_probe_generation(
            root,
            expected_publication_fingerprint="f" * 64,
            trusted_current_utc=AS_OF,
        )

    generation = root / "generations" / fingerprint
    (generation / "unmanifested.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="artifact set drifted"):
        replay_crypto_tournament_v2_bounded_paper_probe_generation(
            root,
            expected_publication_fingerprint=fingerprint,
            trusted_current_utc=AS_OF,
        )


def test_reparse_point_in_artifact_chain_fails_closed(
    tmp_path: Path,
    complete_production: producer.CryptoBoundedProbeCapabilityProduction,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "capabilities"
    fingerprint = _publish(root, complete_production)
    original = producer._is_link_or_reparse

    def reports_reparse(path: Path) -> bool:
        return path.name == "resolved_sources" or original(path)

    monkeypatch.setattr(producer, "_is_link_or_reparse", reports_reparse)
    with pytest.raises(ValidationError, match="link or reparse point"):
        replay_crypto_tournament_v2_bounded_paper_probe_generation(
            root,
            expected_publication_fingerprint=fingerprint,
            trusted_current_utc=AS_OF,
        )


def test_replay_module_has_no_broker_network_or_order_calls() -> None:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"), filename=str(MODULE))
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


def test_review_generation_replays_embedded_production_end_to_end(
    tmp_path: Path,
    complete_production: producer.CryptoBoundedProbeCapabilityProduction,
) -> None:
    fingerprint = _publish_review(tmp_path, complete_production)

    replay = replay_crypto_tournament_v2_bounded_paper_probe_review_generation(
        tmp_path / "review",
        expected_publication_fingerprint=fingerprint,
        trusted_current_utc=AS_OF,
    )

    assert replay["classification"] == "eligible_for_operator_review_only"
    assert replay["historical_review_reproduction_equal"] is True
    assert replay["safety_certification_reexecuted"] is True
    assert replay["paper_mutation_authorized"] is False
    assert replay["live_authorized"] is False


def test_review_generation_replay_blocks_one_microsecond_after_expiry(
    tmp_path: Path,
    complete_production: producer.CryptoBoundedProbeCapabilityProduction,
) -> None:
    fingerprint = _publish_review(tmp_path, complete_production)

    replay = replay_crypto_tournament_v2_bounded_paper_probe_review_generation(
        tmp_path / "review",
        expected_publication_fingerprint=fingerprint,
        trusted_current_utc=AS_OF + timedelta(microseconds=1),
    )

    assert replay["classification"] == "blocked"
    assert replay["review_fingerprint"] == ""
    assert replay["capital_allocation_authorized"] is False


def test_review_outer_hash_recomputation_cannot_hide_packet_tamper(
    tmp_path: Path,
    complete_production: producer.CryptoBoundedProbeCapabilityProduction,
) -> None:
    fingerprint = _publish_review(
        tmp_path,
        complete_production,
        packet_mutation="tampered_action",
    )

    with pytest.raises(ValidationError, match="historical reproduction"):
        replay_crypto_tournament_v2_bounded_paper_probe_review_generation(
            tmp_path / "review",
            expected_publication_fingerprint=fingerprint,
            trusted_current_utc=AS_OF,
        )



def test_target_generation_replays_historical_and_current_exactly(
    tmp_path: Path,
    target_complete_production: tuple[
        producer.CryptoBoundedProbeCapabilityProduction,
        object,
    ],
) -> None:
    production, produced_at = target_complete_production
    root = tmp_path / "target_capabilities"
    fingerprint = _publish(root, production)

    replay = replay_crypto_tournament_v2_bounded_paper_probe_generation(
        root,
        expected_publication_fingerprint=fingerprint,
        trusted_current_utc=produced_at,
    )

    assert replay["classification"] == "eligible_for_operator_review_only"
    assert replay["historical_reproduction_equal"] is True
    assert replay["safety_certification_reexecuted"] is True
    assert replay["review_fingerprint"] == (
        production.status["review_preview_fingerprint"]
    )
    assert replay["paper_mutation_authorized"] is False
    assert replay["live_authorized"] is False


def test_target_review_replays_embedded_target_production(
    tmp_path: Path,
    target_complete_production: tuple[
        producer.CryptoBoundedProbeCapabilityProduction,
        object,
    ],
) -> None:
    production, produced_at = target_complete_production
    fingerprint = _publish_review(tmp_path, production)

    replay = replay_crypto_tournament_v2_bounded_paper_probe_review_generation(
        tmp_path / "review",
        expected_publication_fingerprint=fingerprint,
        trusted_current_utc=produced_at,
    )

    assert replay["classification"] == "eligible_for_operator_review_only"
    assert replay["historical_review_reproduction_equal"] is True
    assert replay["safety_certification_reexecuted"] is True
    assert replay["paper_mutation_authorized"] is False
    assert replay["live_authorized"] is False


@pytest.mark.parametrize("mutation", ("partial", "mixed", "extra"))
def test_target_replay_rejects_nonexact_resolved_path_families(
    tmp_path: Path,
    target_complete_production: tuple[
        producer.CryptoBoundedProbeCapabilityProduction,
        object,
    ],
    mutation: str,
) -> None:
    production, produced_at = target_complete_production
    artifacts = dict(production.artifacts)
    if mutation == "partial":
        artifacts.pop(
            target_producer._TARGET_INPUT_ARTIFACT_PATHS[
                "target_lifecycle_manifest"
            ]
        )
    elif mutation == "mixed":
        artifacts[
            producer._INPUT_ARTIFACT_PATHS["paper_oms_dry_run"]
        ] = b"legacy-only"
    else:
        artifacts["resolved_sources/unexpected.json"] = b"extra"
    tampered = producer.CryptoBoundedProbeCapabilityProduction(
        status=production.status,
        artifacts=artifacts,
    )
    root = tmp_path / mutation
    fingerprint = _publish(root, tampered)

    with pytest.raises(
        ValidationError,
        match="resolved source family is not exact",
    ):
        replay_crypto_tournament_v2_bounded_paper_probe_generation(
            root,
            expected_publication_fingerprint=fingerprint,
            trusted_current_utc=produced_at,
        )


def test_review_runner_reuses_embedded_target_terminal_bytes(
    tmp_path: Path,
    target_complete_production: tuple[
        producer.CryptoBoundedProbeCapabilityProduction,
        object,
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    production, produced_at = target_complete_production
    capability_root = tmp_path / "target_capabilities"
    producer._publish_production(capability_root, production)
    monkeypatch.setattr(
        review,
        "export_crypto_tournament_v2_forward_shadow_terminal_evidence",
        lambda **_: (_ for _ in ()).throw(
            AssertionError("pinned terminal must not be re-exported")
        ),
    )
    review_root = tmp_path / "review"

    packet = review.run_crypto_tournament_v2_bounded_paper_probe_review(
        shadow_root=tmp_path / "missing_shadow",
        capability_root=capability_root,
        output_root=review_root,
        as_of=produced_at,
    )

    assert packet["classification"] == "eligible_for_operator_review_only"
    latest = producer._json_mapping(
        (review_root / "latest_manifest.json").read_bytes(),
        "review_latest",
    )
    terminal_path = (
        review_root
        / str(latest["generation_relative_path"])
        / "inputs"
        / "terminal_evidence.json"
    )
    assert terminal_path.read_bytes() == (
        production.artifacts["inputs/terminal_evidence.json"]
    )
