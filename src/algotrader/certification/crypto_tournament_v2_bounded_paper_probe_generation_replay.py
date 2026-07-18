"""Authorization-grade replay of one pinned V5.27 capability generation.

The strongest result is eligibility for a separate exact operator review.  It
never grants paper mutation, capital allocation, live endpoint, or trading
authority.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Mapping

from algotrader.errors import ValidationError
from algotrader.execution.crypto_bounded_probe_safety_certification import (
    build_crypto_bounded_probe_safety_certification,
)
from algotrader.orchestration import (
    crypto_tournament_v2_bounded_paper_probe_capability_producer as producer,
    crypto_tournament_v2_bounded_paper_probe_capability_producer_v530
    as target_producer,
    crypto_tournament_v2_bounded_paper_probe_review as review,
)


CRYPTO_TOURNAMENT_V2_CAPABILITY_REPLAY_SCHEMA_VERSION = (
    "v5_27_crypto_tournament_v2_bounded_paper_probe_generation_replay_v1"
)

_PRODUCTION_BUILDER_NAME = (
    "build_crypto_tournament_v2_bounded_paper_probe_"
    "capability_production"
)
_FALSE_AUTHORITY = {
    "network_access_authorized": False,
    "network_access_occurred": False,
    "broker_read_authorized": False,
    "broker_read_occurred": False,
    "broker_mutation_authorized": False,
    "broker_mutation_occurred": False,
    "paper_probe_authorized": False,
    "paper_mutation_authorized": False,
    "paper_mutation_occurred": False,
    "capital_allocation_authorized": False,
    "live_authorized": False,
    "live_endpoint_touched": False,
}

__all__ = [
    "CRYPTO_TOURNAMENT_V2_CAPABILITY_REPLAY_SCHEMA_VERSION",
    "replay_crypto_tournament_v2_bounded_paper_probe_generation",
    "replay_crypto_tournament_v2_bounded_paper_probe_review_generation",
    "main",
]


def replay_crypto_tournament_v2_bounded_paper_probe_generation(
    generation_root: Path | str,
    *,
    expected_publication_fingerprint: str,
    trusted_current_utc: datetime | str,
) -> dict[str, object]:
    """Replay exact bytes, re-execute safety checks, and re-evaluate freshness."""

    current_utc = _utc_datetime(trusted_current_utc, "trusted_current_utc")
    loaded = (
        producer.load_crypto_tournament_v2_bounded_paper_probe_capability_generation(
            generation_root,
            expected_publication_fingerprint=expected_publication_fingerprint,
        )
    )
    status = dict(loaded.status)
    blockers: list[str] = []
    historical_reproduction_equal = False
    safety_certification_reexecuted = False
    current_production: producer.CryptoBoundedProbeCapabilityProduction | None = None

    if status.get("capability_bundle_emitted") is not True:
        blockers.append("pinned_generation_did_not_emit_capability_bundle")
    else:
        terminal_bytes = loaded.artifacts.get("inputs/terminal_evidence.json")
        if terminal_bytes is None:
            raise ValidationError("pinned generation terminal evidence is absent.")
        terminal = producer._json_mapping(terminal_bytes, "terminal_evidence")
        producer._require_canonical_json(
            terminal_bytes,
            terminal,
            "terminal_evidence",
        )
        input_family, raw_inputs = _resolved_input_bytes(loaded.artifacts)
        builder_module = (
            target_producer if input_family == "target" else producer
        )
        builder = getattr(builder_module, _PRODUCTION_BUILDER_NAME)
        target_terminal_kwargs = (
            {"terminal_evidence_source_bytes": terminal_bytes}
            if input_family == "target"
            else {}
        )
        recorded_at = _utc_datetime(status.get("as_of"), "status.as_of")
        historical = (
            builder(
                terminal,
                resolved_input_bytes=raw_inputs,
                as_of=recorded_at,
                **target_terminal_kwargs,
            )
        )
        if dict(historical.artifacts) != dict(loaded.artifacts):
            raise ValidationError(
                "pinned generation failed exact historical reproduction."
            )
        historical_reproduction_equal = True
        receipt_bytes = raw_inputs["safety_certification_receipt"]
        receipt = producer._json_mapping(
            receipt_bytes,
            "safety_certification_receipt",
        )
        rebuilt_receipt = build_crypto_bounded_probe_safety_certification(
            kernel_source_bytes=raw_inputs["safety_kernel_source"],
            certifier_source_bytes=raw_inputs["safety_certifier_source"],
            focused_test_source_bytes=raw_inputs["safety_focused_test_source"],
            as_of=receipt.get("as_of"),
        )
        if producer._json_bytes(rebuilt_receipt) != receipt_bytes:
            raise ValidationError(
                "safety certification receipt failed executable replay."
            )
        safety_certification_reexecuted = True
        current_production = (
            builder(
                terminal,
                resolved_input_bytes=raw_inputs,
                as_of=current_utc,
                **target_terminal_kwargs,
            )
        )
        if current_production.status.get("capability_bundle_emitted") is not True:
            blockers.extend(
                str(item) for item in current_production.status.get("blockers", [])
            )
        elif current_production.status.get("review_preview_classification") != (
            "eligible_for_operator_review_only"
        ):
            blockers.append("trusted_time_review_is_not_operator_review_eligible")
        elif current_production.status.get("review_preview_fingerprint") != (
            status.get("review_preview_fingerprint")
        ):
            blockers.append("trusted_time_review_fingerprint_drifted")

    eligible = not blockers and current_production is not None
    replay: dict[str, object] = {
        "schema_version": (
            CRYPTO_TOURNAMENT_V2_CAPABILITY_REPLAY_SCHEMA_VERSION
        ),
        "record_type": "crypto_bounded_probe_capability_generation_replay",
        "trusted_current_utc": current_utc.isoformat(),
        "expected_publication_fingerprint": _sha256(
            expected_publication_fingerprint,
            "expected_publication_fingerprint",
        ),
        "pinned_status_fingerprint": status["status_fingerprint"],
        "pinned_classification": status["classification"],
        "historical_reproduction_equal": historical_reproduction_equal,
        "safety_certification_reexecuted": safety_certification_reexecuted,
        "classification": (
            "eligible_for_operator_review_only" if eligible else "blocked"
        ),
        "review_fingerprint": (
            str(current_production.status["review_preview_fingerprint"])
            if eligible and current_production is not None
            else ""
        ),
        "blockers": list(dict.fromkeys(blockers)),
        "operator_review_required": True,
        "separate_exact_operator_authorization_required": True,
        "profit_claim": "none",
        **_FALSE_AUTHORITY,
    }
    replay["replay_fingerprint"] = _stable_hash(replay)
    return replay


def replay_crypto_tournament_v2_bounded_paper_probe_review_generation(
    review_root: Path | str,
    *,
    expected_publication_fingerprint: str,
    trusted_current_utc: datetime | str,
) -> dict[str, object]:
    """Replay one exact V5.26 review and its embedded V5.27 production."""

    current_utc = _utc_datetime(trusted_current_utc, "trusted_current_utc")
    root = producer._local_path(review_root, "review_root")
    review_publication = _sha256(
        expected_publication_fingerprint,
        "expected_publication_fingerprint",
    )
    generation = root / "generations" / review_publication
    producer._assert_safe_tree_path(root, generation, must_exist=False)
    if not generation.is_dir() or producer._is_link_or_reparse(generation):
        raise ValidationError("pinned review generation is absent.")
    producer._assert_safe_tree_path(root, generation, must_exist=True)
    manifest_bytes = producer._read_regular_bytes(
        generation / "generation_manifest.json",
        "review_generation_manifest",
    )
    manifest = producer._json_mapping(
        manifest_bytes,
        "review_generation_manifest",
    )
    producer._require_canonical_json(
        manifest_bytes,
        manifest,
        "review_generation_manifest",
    )
    if (
        set(manifest) != review._REVIEW_GENERATION_MANIFEST_KEYS
        or manifest.get("schema_version")
        != review.CRYPTO_TOURNAMENT_V2_BOUNDED_PAPER_PROBE_REVIEW_SCHEMA_VERSION
        or manifest.get("record_type")
        != "crypto_tournament_v2_bounded_paper_probe_review_generation"
        or manifest.get("publication_fingerprint") != review_publication
        or manifest.get("broker_mutation_authorized") is not False
        or manifest.get("paper_mutation_authorized") is not False
        or manifest.get("capital_allocation_authorized") is not False
        or manifest.get("live_authorized") is not False
    ):
        raise ValidationError("pinned review generation identity mismatch.")
    digest_map = manifest.get("artifact_sha256")
    if not isinstance(digest_map, Mapping) or not digest_map:
        raise ValidationError("pinned review artifact manifest is empty.")
    artifacts: dict[str, bytes] = {}
    for raw_name, raw_digest in digest_map.items():
        name = producer._safe_relative_name(raw_name)
        digest = _sha256(raw_digest, f"review_artifact_sha256.{name}")
        artifact_path = generation / name
        producer._assert_safe_descendant(generation, artifact_path)
        payload = producer._read_regular_bytes(artifact_path, name)
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ValidationError("pinned review artifact hash mismatch.")
        artifacts[name] = payload
    actual_names = producer._actual_artifact_names(generation)
    if actual_names != set(artifacts):
        raise ValidationError("pinned review artifact set drifted.")
    if _stable_hash(dict(digest_map)) != review_publication:
        raise ValidationError("pinned review publication fingerprint mismatch.")

    preregistration_bytes = artifacts.get("preregistration.json")
    expected_preregistration = review._json_artifact_bytes(
        review.build_crypto_tournament_v2_bounded_paper_probe_preregistration()
    )
    if preregistration_bytes != expected_preregistration:
        raise ValidationError("pinned review preregistration bytes drifted.")
    packet_bytes = artifacts.get("review_packet.json")
    markdown_bytes = artifacts.get("review_packet.md")
    terminal_bytes = artifacts.get("inputs/terminal_evidence.json")
    if packet_bytes is None or markdown_bytes is None or terminal_bytes is None:
        raise ValidationError("pinned eligible review inputs are incomplete.")
    packet = producer._json_mapping(packet_bytes, "review_packet")
    terminal = producer._json_mapping(terminal_bytes, "terminal_evidence")
    producer._require_canonical_json(packet_bytes, packet, "review_packet")
    producer._require_canonical_json(
        terminal_bytes,
        terminal,
        "terminal_evidence",
    )
    (
        capabilities,
        capability_hashes,
        sources,
        source_hashes,
        upstreams,
        upstream_hashes,
    ) = _review_capability_inputs(artifacts)
    recorded_at = _utc_datetime(packet.get("as_of"), "review_packet.as_of")
    historical = review.build_crypto_tournament_v2_bounded_paper_probe_review(
        terminal,
        capability_evidence=capabilities,
        capability_artifact_sha256=capability_hashes,
        capability_source_evidence=sources,
        capability_source_artifact_sha256=source_hashes,
        capability_upstream_evidence=upstreams,
        capability_upstream_artifact_sha256=upstream_hashes,
        as_of=recorded_at,
    )
    if historical != packet:
        raise ValidationError("pinned review failed exact historical reproduction.")
    expected_markdown = (
        review.render_crypto_tournament_v2_bounded_paper_probe_review_markdown(
            packet
        ).encode("utf-8")
    )
    if markdown_bytes != expected_markdown:
        raise ValidationError("pinned review Markdown failed reproduction.")
    if (
        manifest.get("review_fingerprint") != packet.get("review_fingerprint")
        or manifest.get("admission_fingerprint")
        != packet.get("admission_fingerprint")
        or manifest.get("as_of") != packet.get("as_of")
    ):
        raise ValidationError("pinned review manifest binding mismatch.")

    embedded_root = generation / "inputs" / "capability_production"
    pointer_bytes = producer._read_regular_bytes(
        embedded_root / "latest_manifest.json",
        "embedded_capability_latest_pointer",
    )
    pointer = producer._json_mapping(
        pointer_bytes,
        "embedded_capability_latest_pointer",
    )
    producer._require_canonical_json(
        pointer_bytes,
        pointer,
        "embedded_capability_latest_pointer",
    )
    pointer_basis = dict(pointer)
    pointer_fingerprint = _sha256(
        pointer_basis.pop("pointer_fingerprint", ""),
        "embedded_pointer_fingerprint",
    )
    embedded_publication = _sha256(
        pointer.get("publication_fingerprint"),
        "embedded_publication_fingerprint",
    )
    if (
        set(pointer) != producer._LATEST_POINTER_KEYS
        or pointer_fingerprint != _stable_hash(pointer_basis)
        or pointer.get("schema_version")
        != producer.CRYPTO_TOURNAMENT_V2_CAPABILITY_PRODUCTION_SCHEMA_VERSION
        or pointer.get("record_type")
        != "crypto_bounded_probe_capability_latest_pointer"
        or pointer.get("generation_relative_path")
        != f"generations/{embedded_publication}"
        or pointer.get("broker_mutation_authorized") is not False
        or pointer.get("paper_mutation_authorized") is not False
        or pointer.get("capital_allocation_authorized") is not False
        or pointer.get("live_authorized") is not False
    ):
        raise ValidationError("embedded capability pointer binding failed.")
    embedded_loaded = (
        producer.load_crypto_tournament_v2_bounded_paper_probe_capability_generation(
            embedded_root,
            expected_publication_fingerprint=embedded_publication,
        )
    )
    embedded_manifest_path = (
        embedded_root
        / "generations"
        / embedded_publication
        / "generation_manifest.json"
    )
    producer._assert_safe_tree_path(
        embedded_root,
        embedded_manifest_path,
        must_exist=True,
    )
    embedded_manifest_bytes = producer._read_regular_bytes(
        embedded_manifest_path,
        "embedded_capability_generation_manifest",
    )
    if (
        hashlib.sha256(embedded_manifest_bytes).hexdigest()
        != pointer.get("generation_manifest_sha256")
        or pointer.get("status_fingerprint")
        != embedded_loaded.status.get("status_fingerprint")
        or pointer.get("classification")
        != embedded_loaded.status.get("classification")
        or pointer.get("as_of") != embedded_loaded.status.get("as_of")
    ):
        raise ValidationError("embedded capability pointer status binding failed.")
    _validate_outer_embedded_input_equality(
        outer_artifacts=artifacts,
        embedded_artifacts=embedded_loaded.artifacts,
    )
    capability_replay = (
        replay_crypto_tournament_v2_bounded_paper_probe_generation(
            embedded_root,
            expected_publication_fingerprint=embedded_publication,
            trusted_current_utc=current_utc,
        )
    )
    blockers: list[str] = []
    if packet.get("classification") != "eligible_for_operator_review_only":
        blockers.append("pinned_review_is_not_operator_review_eligible")
    if capability_replay.get("classification") != (
        "eligible_for_operator_review_only"
    ):
        blockers.extend(
            str(item) for item in capability_replay.get("blockers", [])
        )
    if capability_replay.get("review_fingerprint") != packet.get(
        "review_fingerprint"
    ):
        blockers.append("embedded_capability_review_fingerprint_drifted")
    if not blockers:
        review.validate_crypto_tournament_v2_bounded_paper_probe_review_packet(
            packet,
            as_of=current_utc,
        )
    eligible = not blockers
    result: dict[str, object] = {
        "schema_version": (
            CRYPTO_TOURNAMENT_V2_CAPABILITY_REPLAY_SCHEMA_VERSION
        ),
        "record_type": "crypto_bounded_probe_review_generation_replay",
        "trusted_current_utc": current_utc.isoformat(),
        "expected_review_publication_fingerprint": review_publication,
        "embedded_capability_publication_fingerprint": embedded_publication,
        "historical_review_reproduction_equal": True,
        "capability_replay_fingerprint": capability_replay[
            "replay_fingerprint"
        ],
        "safety_certification_reexecuted": capability_replay[
            "safety_certification_reexecuted"
        ],
        "classification": (
            "eligible_for_operator_review_only" if eligible else "blocked"
        ),
        "review_fingerprint": (
            str(packet["review_fingerprint"]) if eligible else ""
        ),
        "blockers": list(dict.fromkeys(blockers)),
        "operator_review_required": True,
        "separate_exact_operator_authorization_required": True,
        "profit_claim": "none",
        **_FALSE_AUTHORITY,
    }
    result["replay_fingerprint"] = _stable_hash(result)
    return result


def _validate_outer_embedded_input_equality(
    *,
    outer_artifacts: Mapping[str, bytes],
    embedded_artifacts: Mapping[str, bytes],
) -> None:
    pairs: list[tuple[str, str]] = [
        (
            "inputs/terminal_evidence.json",
            "inputs/terminal_evidence.json",
        ),
        ("review_packet.json", "bundle/review_preview.json"),
    ]
    for kind in review._CAPABILITY_KINDS:
        pairs.extend(
            (
                (
                    f"inputs/capabilities/{kind}.json",
                    f"bundle/{kind}.json",
                ),
                (
                    f"inputs/producer_sources/{kind}.json",
                    f"bundle/sources/{kind}/producer_source.json",
                ),
            )
        )
        for role, _schema, _record_type in (
            review._CAPABILITY_UPSTREAM_SOURCE_CONTRACTS[kind]
        ):
            pairs.append(
                (
                    f"inputs/upstreams/{kind}/{role}.json",
                    f"bundle/sources/{kind}/upstream/{role}.json",
                )
            )
    for outer_name, embedded_name in pairs:
        outer = outer_artifacts.get(outer_name)
        embedded = embedded_artifacts.get(embedded_name)
        if outer is None or embedded is None or outer != embedded:
            raise ValidationError(
                "outer review and embedded capability inputs diverged: "
                f"{outer_name}."
            )


def _resolved_input_bytes(
    artifacts: Mapping[str, bytes],
) -> tuple[str, dict[str, bytes]]:
    resolved_paths = {
        name
        for name in artifacts
        if name.startswith("resolved_sources/")
    }
    families = {
        "legacy": producer._INPUT_ARTIFACT_PATHS,
        "target": target_producer._TARGET_INPUT_ARTIFACT_PATHS,
    }
    matches = [
        family
        for family, paths in families.items()
        if resolved_paths == set(paths.values())
    ]
    if len(matches) != 1:
        raise ValidationError(
            "pinned generation resolved source family is not exact."
        )
    family = matches[0]
    result: dict[str, bytes] = {}
    for role, relative_path in families[family].items():
        payload = artifacts.get(relative_path)
        if not isinstance(payload, bytes) or not payload:
            raise ValidationError(
                f"pinned generation source is absent: {role}."
            )
        result[role] = payload
    return family, result


def _review_capability_inputs(
    artifacts: Mapping[str, bytes],
) -> tuple[
    dict[str, Mapping[str, object]],
    dict[str, str],
    dict[str, Mapping[str, object]],
    dict[str, str],
    dict[str, dict[str, Mapping[str, object]]],
    dict[str, dict[str, str]],
]:
    capabilities: dict[str, Mapping[str, object]] = {}
    capability_hashes: dict[str, str] = {}
    sources: dict[str, Mapping[str, object]] = {}
    source_hashes: dict[str, str] = {}
    upstreams: dict[str, dict[str, Mapping[str, object]]] = {}
    upstream_hashes: dict[str, dict[str, str]] = {}
    for kind in producer._CAPABILITY_KINDS:
        capability_name = f"inputs/capabilities/{kind}.json"
        source_name = f"inputs/producer_sources/{kind}.json"
        capability_bytes = artifacts.get(capability_name)
        source_bytes = artifacts.get(source_name)
        if capability_bytes is None or source_bytes is None:
            raise ValidationError("pinned review capability inputs are absent.")
        capability = producer._json_mapping(capability_bytes, capability_name)
        source = producer._json_mapping(source_bytes, source_name)
        producer._require_canonical_json(
            capability_bytes,
            capability,
            capability_name,
        )
        producer._require_canonical_json(source_bytes, source, source_name)
        capabilities[kind] = capability
        capability_hashes[kind] = hashlib.sha256(capability_bytes).hexdigest()
        sources[kind] = source
        source_hashes[kind] = hashlib.sha256(source_bytes).hexdigest()
        kind_upstreams: dict[str, Mapping[str, object]] = {}
        kind_hashes: dict[str, str] = {}
        for role, _, _ in producer._UPSTREAM_CONTRACTS[kind]:
            name = f"inputs/upstreams/{kind}/{role}.json"
            payload = artifacts.get(name)
            if payload is None:
                raise ValidationError("pinned review upstream input is absent.")
            parsed = producer._json_mapping(payload, name)
            producer._require_canonical_json(payload, parsed, name)
            kind_upstreams[role] = parsed
            kind_hashes[role] = hashlib.sha256(payload).hexdigest()
        upstreams[kind] = kind_upstreams
        upstream_hashes[kind] = kind_hashes
    return (
        capabilities,
        capability_hashes,
        sources,
        source_hashes,
        upstreams,
        upstream_hashes,
    )


def _utc_datetime(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be ISO-8601.") from exc
    else:
        raise ValidationError(f"{field_name} must be a datetime.")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError(f"{field_name} must be timezone-aware.")
    try:
        return parsed.astimezone(timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise ValidationError(f"{field_name} is outside the UTC range.") from exc


def _sha256(value: object, field_name: str) -> str:
    text = str(value).strip().lower()
    if len(text) != 64 or any(
        character not in "0123456789abcdef"
        for character in text
    ):
        raise ValidationError(f"{field_name} must be a SHA-256 digest.")
    return text


def _stable_hash(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-root", required=True)
    parser.add_argument("--expected-publication-fingerprint", required=True)
    parser.add_argument("--trusted-current-utc", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = replay_crypto_tournament_v2_bounded_paper_probe_review_generation(
        args.review_root,
        expected_publication_fingerprint=(
            args.expected_publication_fingerprint
        ),
        trusted_current_utc=args.trusted_current_utc,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return (
        0
        if result.get("classification") == "eligible_for_operator_review_only"
        and result.get("blockers") == []
        else 2
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
