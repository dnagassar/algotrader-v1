"""Offline v2.17 research hypothesis triage and next-family selection."""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from algotrader.errors import ValidationError

__all__ = [
    "RESEARCH_HYPOTHESIS_TRIAGE_CLASSIFICATIONS",
    "RESEARCH_HYPOTHESIS_TRIAGE_LABELS",
    "ResearchHypothesisTriageConfig",
    "build_research_hypothesis_triage_payload",
    "load_research_hypothesis_triage_inputs",
    "main",
    "render_research_hypothesis_triage_markdown",
    "run_research_hypothesis_triage",
    "write_research_hypothesis_triage_artifacts",
]


RESEARCH_HYPOTHESIS_TRIAGE_LABELS = (
    "research_only",
    "offline_only",
    "not_live_authorized",
    "paper_submit_authorized=false",
    "profit_claim=none",
    "broker_state_not_required",
    "no_strategy_promoted",
)
RESEARCH_HYPOTHESIS_TRIAGE_CLASSIFICATIONS = (
    "next_family_selected_for_offline_research",
    "needs_more_evidence_before_selection",
    "triage_blocked_artifacts_missing",
    "triage_blocked_safety_invariant",
)

_RECORD_TYPE = "research_hypothesis_triage"
_SCHEMA_VERSION = "1"
_PHASE = "v2.17_research_hypothesis_triage_next_family_selection"
_DEFAULT_CHALLENGER_ROOT = Path("runs/strategy_challengers/latest")
_DEFAULT_PREVIEW_REVIEW_ROOT = Path("runs/strategy_challengers/preview_review_latest")
_DEFAULT_OUTPUT_ROOT = Path(
    "runs/strategy_challengers/research_hypothesis_triage_latest"
)
_RELATIVE_MOMENTUM_FAMILY = "etf_relative_momentum_basket"
_SMA_TREND_FAMILIES = {
    "sma_crossover_long_only",
    "sma_crossover_long_only_cash_risk_off",
    "time_series_momentum_long_only",
    "drawdown_filter_long_only",
}
_HASH_CHUNK_SIZE = 1024 * 1024

_SCORING_CRITERIA = (
    "orthogonality_to_failed_sma_relative_momentum_hypotheses",
    "expected_information_value",
    "uses_already_validated_local_etf_data",
    "minimal_additional_data_dependency",
    "anti_overfit_risk",
    "implementation_size",
    "paper_lab_integration_relevance",
    "safety_impact",
    "interpretability_for_operator_brief",
)

_NEXT_FAMILY_SCORECARD = {
    "mean reversion / defensive rotation": {
        "criteria_scores": {
            "orthogonality_to_failed_sma_relative_momentum_hypotheses": 5,
            "expected_information_value": 4,
            "uses_already_validated_local_etf_data": 5,
            "minimal_additional_data_dependency": 5,
            "anti_overfit_risk": 3,
            "implementation_size": 3,
            "paper_lab_integration_relevance": 3,
            "safety_impact": 5,
            "interpretability_for_operator_brief": 4,
        },
        "rationale": (
            "Materially different from trend-following and relative momentum, "
            "but needs careful regime and rebalance constraints to avoid fitting "
            "defensive switches to the same historical stress windows."
        ),
    },
    "volatility-regime filter": {
        "criteria_scores": {
            "orthogonality_to_failed_sma_relative_momentum_hypotheses": 4,
            "expected_information_value": 5,
            "uses_already_validated_local_etf_data": 5,
            "minimal_additional_data_dependency": 5,
            "anti_overfit_risk": 4,
            "implementation_size": 4,
            "paper_lab_integration_relevance": 5,
            "safety_impact": 5,
            "interpretability_for_operator_brief": 5,
        },
        "rationale": (
            "Tests whether risk regime, rather than another directional lookback, "
            "explains the failed SMA and relative-momentum evidence while reusing "
            "local ETF bars and simple operator-readable diagnostics."
        ),
    },
    "trend + breadth/regime composite": {
        "criteria_scores": {
            "orthogonality_to_failed_sma_relative_momentum_hypotheses": 2,
            "expected_information_value": 4,
            "uses_already_validated_local_etf_data": 5,
            "minimal_additional_data_dependency": 5,
            "anti_overfit_risk": 3,
            "implementation_size": 3,
            "paper_lab_integration_relevance": 4,
            "safety_impact": 5,
            "interpretability_for_operator_brief": 4,
        },
        "rationale": (
            "Potentially useful as an operating filter, but still partly extends "
            "the rejected trend hypothesis family and has higher combinatorial "
            "overfit risk than a single regime diagnostic."
        ),
    },
    "simple carry/defensive asset rotation": {
        "criteria_scores": {
            "orthogonality_to_failed_sma_relative_momentum_hypotheses": 4,
            "expected_information_value": 3,
            "uses_already_validated_local_etf_data": 3,
            "minimal_additional_data_dependency": 3,
            "anti_overfit_risk": 4,
            "implementation_size": 3,
            "paper_lab_integration_relevance": 3,
            "safety_impact": 5,
            "interpretability_for_operator_brief": 4,
        },
        "rationale": (
            "Conceptually different, but a true carry test would need extra yield "
            "or rate inputs; ETF-price-only defensive rotation would risk becoming "
            "another relative-strength variant."
        ),
    },
}


@dataclass(frozen=True, slots=True)
class ResearchHypothesisTriageConfig:
    """Inputs for one offline research hypothesis triage packet."""

    output_root: Path | str = _DEFAULT_OUTPUT_ROOT
    challenger_root: Path | str = _DEFAULT_CHALLENGER_ROOT
    preview_review_root: Path | str = _DEFAULT_PREVIEW_REVIEW_ROOT

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_root", _path(self.output_root, "output_root"))
        object.__setattr__(
            self,
            "challenger_root",
            _path(self.challenger_root, "challenger_root"),
        )
        object.__setattr__(
            self,
            "preview_review_root",
            _path(self.preview_review_root, "preview_review_root"),
        )


def run_research_hypothesis_triage(
    config: ResearchHypothesisTriageConfig,
) -> dict[str, object]:
    """Load local research evidence, build triage, and write artifacts."""

    checked_config = _config(config)
    inputs = load_research_hypothesis_triage_inputs(
        challenger_root=checked_config.challenger_root,
        preview_review_root=checked_config.preview_review_root,
    )
    payload = build_research_hypothesis_triage_payload(inputs)
    manifest = write_research_hypothesis_triage_artifacts(
        payload,
        checked_config.output_root,
    )
    result = dict(payload)
    result["manifest"] = manifest
    return result


def load_research_hypothesis_triage_inputs(
    *,
    challenger_root: Path | str = _DEFAULT_CHALLENGER_ROOT,
    preview_review_root: Path | str = _DEFAULT_PREVIEW_REVIEW_ROOT,
) -> dict[str, object]:
    """Load local challenger and preview review artifacts without broker access."""

    challenger_path = _path(challenger_root, "challenger_root")
    preview_path = _path(preview_review_root, "preview_review_root")
    artifact_specs = (
        (
            "challenger_results",
            challenger_path / "challenger_results.json",
            True,
            ("results", "promotion_recommendations"),
        ),
        (
            "promotion_recommendations",
            challenger_path / "promotion_recommendations.json",
            False,
            (),
        ),
        (
            "strategy_review_packet",
            challenger_path / "strategy_review_packet.json",
            False,
            (),
        ),
        (
            "cost_sensitivity",
            challenger_path / "cost_sensitivity.json",
            False,
            (),
        ),
        (
            "cross_asset_validation",
            challenger_path / "cross_asset_validation.json",
            False,
            (),
        ),
        (
            "validation_windows",
            challenger_path / "validation_windows.json",
            False,
            (),
        ),
        (
            "preview_candidate_review",
            preview_path / "preview_candidate_review.json",
            True,
            ("candidate_reviews", "overall_recommendation"),
        ),
        (
            "anti_overfit_flags",
            preview_path / "anti_overfit_flags.json",
            False,
            (),
        ),
        (
            "offline_shadow_candidates",
            preview_path / "offline_shadow_candidates.json",
            False,
            (),
        ),
    )

    artifacts: dict[str, object] = {}
    source_artifacts: list[dict[str, object]] = []
    for name, path, required, required_fields in artifact_specs:
        record, data = _read_json_artifact(
            name=name,
            path=path,
            required=required,
            required_fields=required_fields,
        )
        source_artifacts.append(record)
        artifacts[name] = data

    return {
        "challenger_root": str(challenger_path),
        "preview_review_root": str(preview_path),
        "source_artifacts": source_artifacts,
        "artifacts": artifacts,
    }


def build_research_hypothesis_triage_payload(
    inputs: Mapping[str, object],
) -> dict[str, object]:
    """Build the deterministic v2.17 triage payload."""

    input_items = dict(inputs)
    artifacts = _mapping_or_empty(input_items.get("artifacts"))
    source_artifacts = _artifact_records(input_items.get("source_artifacts", []))
    challenger_results = _mapping_or_empty(artifacts.get("challenger_results"))
    preview_review = _mapping_or_empty(artifacts.get("preview_candidate_review"))
    promotion_recommendations = _promotion_recommendations(
        challenger_results,
        artifacts.get("promotion_recommendations"),
    )
    cross_asset_validation = _cross_asset_validation(
        challenger_results,
        artifacts.get("cross_asset_validation"),
    )
    preview_candidate_reviews = _review_list(preview_review.get("candidate_reviews"))
    results = _result_list(challenger_results.get("results"))

    evidence_inventory = _evidence_inventory(
        source_artifacts=source_artifacts,
        results=results,
        preview_candidate_reviews=preview_candidate_reviews,
    )
    failure_taxonomy = _failure_taxonomy(
        challenger_results=challenger_results,
        results=results,
        preview_candidate_reviews=preview_candidate_reviews,
        cross_asset_validation=cross_asset_validation,
        source_artifacts=source_artifacts,
    )
    family_diagnosis = _candidate_family_diagnosis(
        results=results,
        preview_candidate_reviews=preview_candidate_reviews,
        promotion_recommendations=promotion_recommendations,
        failure_taxonomy=failure_taxonomy,
    )
    family_scores = _family_scores()
    artifact_blockers = [
        artifact
        for artifact in source_artifacts
        if artifact.get("required") is True and artifact.get("status") != "available"
    ]
    safety_violations = _source_safety_violations(challenger_results, preview_review)

    selected_family = None
    selected_rationale: dict[str, object]
    rejected_or_deferred: list[dict[str, object]]
    if safety_violations:
        classification = "triage_blocked_safety_invariant"
        selected_rationale = {
            "evidence": list(safety_violations),
            "inference": [
                "Triage must not select a next family when source artifacts report broker or mutation activity."
            ],
        }
        rejected_or_deferred = []
    elif artifact_blockers:
        classification = "triage_blocked_artifacts_missing"
        selected_rationale = {
            "evidence": [
                f"{artifact.get('name')}: {artifact.get('status')}"
                for artifact in artifact_blockers
            ],
            "inference": [
                "Required challenger or preview evidence is unavailable, malformed, or incomplete."
            ],
        }
        rejected_or_deferred = []
    elif not results:
        classification = "needs_more_evidence_before_selection"
        selected_rationale = {
            "evidence": ["No challenger result records were found."],
            "inference": [
                "A next family should not be selected without at least one evaluated candidate record."
            ],
        }
        rejected_or_deferred = []
    else:
        classification = "next_family_selected_for_offline_research"
        selected_family = str(family_scores[0]["family"])
        selected_rationale = _selected_family_rationale(
            selected_family,
            promotion_recommendations=promotion_recommendations,
            preview_review=preview_review,
            failure_taxonomy=failure_taxonomy,
        )
        rejected_or_deferred = _rejected_or_deferred_families(
            selected_family,
            family_scores,
        )

    payload = {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "phase": _PHASE,
        "classification": classification,
        "generated_at": _deterministic_generated_at(challenger_results),
        "source_artifacts": source_artifacts,
        "evidence_inventory": evidence_inventory,
        "failure_taxonomy": failure_taxonomy,
        "candidate_family_diagnosis": family_diagnosis,
        "family_scores": family_scores,
        "selected_next_family": selected_family,
        "selected_next_family_rationale": selected_rationale,
        "rejected_or_deferred_families": rejected_or_deferred,
        "v2_18_next_action": _v2_18_next_action(selected_family),
        "paper_candidate_count": _paper_candidate_count(promotion_recommendations),
        "offline_shadow_candidate_count": _offline_shadow_candidate_count(
            preview_review,
        ),
        "safety_labels": list(RESEARCH_HYPOTHESIS_TRIAGE_LABELS),
        "broker_access_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_mutation_performed": False,
        "normal_pytest_offline_credential_free": True,
        "safety": _safety_payload(),
        "limitations": [
            "offline deterministic research triage only",
            "reads existing local strategy challenger and preview review artifacts only",
            "does not fetch market data",
            "does not read or mutate broker state",
            "does not submit paper or live orders",
            "does not promote any strategy to paper",
            "does not make a profitability claim",
        ],
    }
    _validate_classification(str(payload["classification"]))
    return payload


def write_research_hypothesis_triage_artifacts(
    payload: Mapping[str, object],
    output_root: Path | str,
) -> dict[str, object]:
    """Write required JSON, markdown, and manifest artifacts."""

    root = _path(output_root, "output_root")
    root.mkdir(parents=True, exist_ok=True)
    payload_dict = dict(payload)
    artifact_writers = (
        (
            "research_hypothesis_triage.json",
            lambda path: _write_text(path, _json_dumps(payload_dict) + "\n"),
        ),
        (
            "research_hypothesis_triage.md",
            lambda path: _write_text(
                path,
                render_research_hypothesis_triage_markdown(payload_dict),
            ),
        ),
    )

    artifact_paths: list[Path] = []
    for filename, writer in artifact_writers:
        artifact_path = root / filename
        writer(artifact_path)
        artifact_paths.append(artifact_path)

    manifest = _manifest_payload(payload_dict, root, artifact_paths)
    _write_text(root / "manifest.json", _json_dumps(manifest) + "\n")
    return manifest


def render_research_hypothesis_triage_markdown(
    payload: Mapping[str, object],
) -> str:
    """Render the triage packet as compact markdown."""

    payload_dict = dict(payload)
    inventory = _mapping_or_empty(payload_dict.get("evidence_inventory"))
    taxonomy = _mapping_or_empty(payload_dict.get("failure_taxonomy"))
    diagnosis = _mapping_or_empty(payload_dict.get("candidate_family_diagnosis"))
    selected_rationale = _mapping_or_empty(
        payload_dict.get("selected_next_family_rationale")
    )
    next_action = _mapping_or_empty(payload_dict.get("v2_18_next_action"))
    lines = [
        "# Research Hypothesis Triage",
        "",
        "Labels: "
        + ", ".join(str(item) for item in payload_dict.get("safety_labels", [])),
        "",
        "## Summary",
        f"- phase: {payload_dict.get('phase')}",
        f"- classification: {payload_dict.get('classification')}",
        f"- generated_at: {payload_dict.get('generated_at')}",
        f"- selected_next_family: {payload_dict.get('selected_next_family')}",
        f"- paper_candidate_count: {payload_dict.get('paper_candidate_count')}",
        f"- offline_shadow_candidate_count: {payload_dict.get('offline_shadow_candidate_count')}",
        "- paper_submit_authorized: false",
        "- profit_claim: none",
        "",
        "## Evidence Inventory",
        f"- artifact_count: {len(_artifact_records(payload_dict.get('source_artifacts', [])))}",
        f"- candidate_record_count: {inventory.get('candidate_record_count')}",
        f"- unique_candidate_count: {inventory.get('unique_candidate_count')}",
        f"- preview_candidate_review_count: {inventory.get('preview_candidate_review_count')}",
        f"- records_unavailable: {', '.join(str(item) for item in inventory.get('records_unavailable', [])) or 'none'}",
        f"- records_malformed: {', '.join(str(item) for item in inventory.get('records_malformed', [])) or 'none'}",
        f"- records_incomplete: {', '.join(str(item) for item in inventory.get('records_incomplete', [])) or 'none'}",
        "",
        "## Failure Taxonomy",
        "| category | count | candidate_ids |",
        "| --- | ---: | --- |",
    ]
    for category in (
        "oos_failure",
        "edge_broken",
        "high_cost_sensitivity",
        "anti_overfit_rejection",
        "insufficient_evidence",
        "data_validation_issue",
        "preview_only_but_not_promotable",
        "paper_promotion_blocked",
    ):
        item = _mapping_or_empty(taxonomy.get(category))
        lines.append(
            "| {category} | {count} | {ids} |".format(
                category=category,
                count=item.get("count", 0),
                ids=", ".join(str(value) for value in item.get("candidate_ids", []))
                or "none",
            )
        )

    lines.extend(["", "## Candidate-Family Diagnosis"])
    for family_key in ("sma_trend", "etf_relative_dual_momentum"):
        family = _mapping_or_empty(diagnosis.get(family_key))
        lines.extend(["", f"### {family.get('label', family_key)}", "", "Evidence:"])
        for item in family.get("evidence", []):
            lines.append(f"- {item}")
        lines.append("")
        lines.append("Inference:")
        for item in family.get("inference", []):
            lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Next-Family Scoring",
            "| rank | family | total_score | rationale |",
            "| ---: | --- | ---: | --- |",
        ]
    )
    for score in _score_records(payload_dict.get("family_scores", [])):
        lines.append(
            "| {rank} | {family} | {total} | {rationale} |".format(
                rank=score.get("rank"),
                family=score.get("family"),
                total=score.get("total_score"),
                rationale=score.get("rationale"),
            )
        )

    lines.extend(
        [
            "",
            "## Selection",
            f"- selected_next_family: {payload_dict.get('selected_next_family')}",
            "- selection_type: research-direction decision only",
            "- paper_approval: false",
            "- strategy_promoted: false",
            "",
            "Evidence:",
        ]
    )
    for item in selected_rationale.get("evidence", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Inference:")
    for item in selected_rationale.get("inference", []):
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## v2.18 Next Action",
            f"- title: {next_action.get('title')}",
            f"- smallest_safe_slice: {next_action.get('smallest_safe_slice')}",
            f"- implementation_prompt: {next_action.get('implementation_prompt')}",
            "",
            "## Safety",
            "- broker_access_performed: false",
            "- broker_mutation_performed: false",
            "- paper_submit_performed: false",
            "- live_mutation_performed: false",
            "- normal_pytest_offline_credential_free: true",
            "",
        ]
    )
    return "\n".join(lines)


def _evidence_inventory(
    *,
    source_artifacts: Sequence[Mapping[str, object]],
    results: Sequence[Mapping[str, object]],
    preview_candidate_reviews: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    unavailable = [
        str(artifact.get("name"))
        for artifact in source_artifacts
        if artifact.get("status") == "unavailable"
    ]
    malformed = [
        str(artifact.get("name"))
        for artifact in source_artifacts
        if artifact.get("status") == "malformed"
    ]
    incomplete = [
        str(artifact.get("name"))
        for artifact in source_artifacts
        if artifact.get("status") == "incomplete"
    ]
    incomplete.extend(_incomplete_candidate_record_ids(results))
    return {
        "artifacts_inspected": [
            {
                "name": artifact.get("name"),
                "path": artifact.get("path"),
                "status": artifact.get("status"),
                "required": artifact.get("required"),
                "record_type": artifact.get("record_type"),
                "schema_version": artifact.get("schema_version"),
            }
            for artifact in source_artifacts
        ],
        "candidate_record_count": len(results),
        "unique_candidate_count": len(
            {str(result.get("candidate_id")) for result in results if result.get("candidate_id")}
        ),
        "candidate_records_found": _candidate_summaries(results),
        "preview_candidate_review_count": len(preview_candidate_reviews),
        "preview_review_records_found": [
            {
                "candidate_id": review.get("candidate_id"),
                "final_review_classification": review.get(
                    "final_review_classification"
                ),
                "anti_overfit_reasons": list(
                    _string_list(review.get("anti_overfit_reasons"))
                ),
            }
            for review in preview_candidate_reviews
        ],
        "records_unavailable": sorted(unavailable),
        "records_malformed": sorted(malformed),
        "records_incomplete": sorted(incomplete),
    }


def _failure_taxonomy(
    *,
    challenger_results: Mapping[str, object],
    results: Sequence[Mapping[str, object]],
    preview_candidate_reviews: Sequence[Mapping[str, object]],
    cross_asset_validation: Mapping[str, object],
    source_artifacts: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    taxonomy = {
        "oos_failure": _empty_taxonomy_item(
            "Out-of-sample validation failed for one or more windows or symbols."
        ),
        "edge_broken": _empty_taxonomy_item(
            "Moderate cost assumptions broke the measured edge."
        ),
        "high_cost_sensitivity": _empty_taxonomy_item(
            "Returns or edge were highly sensitive to cost assumptions."
        ),
        "anti_overfit_rejection": _empty_taxonomy_item(
            "Preview-only candidate failed deterministic anti-overfit review."
        ),
        "insufficient_evidence": _empty_taxonomy_item(
            "Required fields or candidate evidence were unavailable."
        ),
        "data_validation_issue": _empty_taxonomy_item(
            "Source data or result metrics reported validation issues."
        ),
        "preview_only_but_not_promotable": _empty_taxonomy_item(
            "Candidate was preview-only and not an offline-shadow or paper candidate."
        ),
        "paper_promotion_blocked": _empty_taxonomy_item(
            "Candidate was blocked from paper promotion by factory or review policy."
        ),
    }

    for result in results:
        candidate_id = _candidate_id(result)
        if candidate_id is None:
            _append_taxonomy_detail(
                taxonomy["insufficient_evidence"],
                "unknown",
                "candidate_result_missing_candidate_id",
            )
            continue
        if _result_has_oos_failure(result):
            _append_taxonomy_detail(
                taxonomy["oos_failure"],
                candidate_id,
                _result_detail(result),
            )
        if _result_edge_broken(result):
            _append_taxonomy_detail(
                taxonomy["edge_broken"],
                candidate_id,
                _result_detail(result),
            )
        if _result_highly_cost_sensitive(result):
            _append_taxonomy_detail(
                taxonomy["high_cost_sensitivity"],
                candidate_id,
                _result_detail(result),
            )
        if result.get("promotion_classification") == "preview_only":
            _append_taxonomy_detail(
                taxonomy["preview_only_but_not_promotable"],
                candidate_id,
                _result_detail(result),
            )
        if _result_incomplete(result):
            _append_taxonomy_detail(
                taxonomy["insufficient_evidence"],
                candidate_id,
                "candidate_result_missing_required_triage_fields",
            )
        metrics_status = result.get("metrics_status")
        if metrics_status not in (None, "valid"):
            _append_taxonomy_detail(
                taxonomy["data_validation_issue"],
                candidate_id,
                f"metrics_status={metrics_status}",
            )

    for review in preview_candidate_reviews:
        candidate_id = str(review.get("candidate_id") or "unknown")
        if review.get("final_review_classification") == "reject_preview":
            reasons = ", ".join(_string_list(review.get("anti_overfit_reasons")))
            detail = reasons or "reject_preview"
            _append_taxonomy_detail(
                taxonomy["anti_overfit_rejection"],
                candidate_id,
                detail,
            )
            _append_taxonomy_detail(
                taxonomy["preview_only_but_not_promotable"],
                candidate_id,
                "anti_overfit_review_rejected_preview",
            )

    rollups = _candidate_rollups(cross_asset_validation)
    if not rollups:
        rollups = _candidate_rollups(challenger_results.get("cross_asset_validation"))
    for rollup in rollups:
        candidate_id = str(rollup.get("candidate_id") or "unknown")
        blockers = _string_list(rollup.get("paper_candidate_blockers"))
        if rollup.get("paper_candidate_allowed") is False or blockers:
            _append_taxonomy_detail(
                taxonomy["paper_promotion_blocked"],
                candidate_id,
                ", ".join(blockers) or "paper_candidate_allowed=false",
            )

    symbols_missing = _string_list(challenger_results.get("symbols_missing_data"))
    if symbols_missing:
        _append_taxonomy_detail(
            taxonomy["data_validation_issue"],
            "source_data",
            "symbols_missing_data=" + ",".join(symbols_missing),
        )

    for artifact in source_artifacts:
        status = artifact.get("status")
        if status in {"malformed", "incomplete"}:
            _append_taxonomy_detail(
                taxonomy["data_validation_issue"],
                str(artifact.get("name") or "artifact"),
                f"artifact_status={status}",
            )
        if status == "unavailable" and artifact.get("required") is True:
            _append_taxonomy_detail(
                taxonomy["insufficient_evidence"],
                str(artifact.get("name") or "artifact"),
                "required_artifact_unavailable",
            )

    return {key: _finalize_taxonomy_item(value) for key, value in taxonomy.items()}


def _candidate_family_diagnosis(
    *,
    results: Sequence[Mapping[str, object]],
    preview_candidate_reviews: Sequence[Mapping[str, object]],
    promotion_recommendations: Mapping[str, object],
    failure_taxonomy: Mapping[str, object],
) -> dict[str, object]:
    sma_ids = sorted(
        {
            str(result.get("candidate_id"))
            for result in results
            if result.get("strategy_family") in _SMA_TREND_FAMILIES
            and result.get("candidate_id")
        }
    )
    relative_ids = sorted(
        {
            str(result.get("candidate_id"))
            for result in results
            if result.get("strategy_family") == _RELATIVE_MOMENTUM_FAMILY
            and result.get("candidate_id")
        }
    )
    preview_rejected_ids = sorted(
        {
            str(review.get("candidate_id"))
            for review in preview_candidate_reviews
            if review.get("final_review_classification") == "reject_preview"
            and review.get("candidate_id")
        }
    )
    classification_counts = _mapping_or_empty(
        promotion_recommendations.get("classification_counts")
    )
    paper_candidate_count = _paper_candidate_count(promotion_recommendations)
    return {
        "sma_trend": {
            "label": "SMA and trend-following evidence",
            "candidate_ids": sma_ids,
            "evidence": [
                f"{len(sma_ids)} unique SMA/trend candidate IDs were found in challenger results.",
                f"Factory classification counts were {_compact_mapping(classification_counts)}.",
                f"Paper candidate count was {paper_candidate_count}.",
                "Preview anti-overfit review rejected: "
                + (", ".join(preview_rejected_ids) if preview_rejected_ids else "none"),
            ],
            "inference": [
                "Additional SMA lookback variants have low expected information value because the artifact already covers multiple trend windows and cross-ETF validation.",
                "The repeated OOS and cost-sensitivity failures point toward testing a different explanatory axis rather than another trend parameter sweep.",
            ],
        },
        "etf_relative_dual_momentum": {
            "label": "ETF relative and dual momentum evidence",
            "candidate_ids": relative_ids,
            "evidence": [
                f"{len(relative_ids)} ETF relative/dual momentum candidate IDs were found.",
                "OOS-failure candidates include: "
                + _taxonomy_ids_text(failure_taxonomy, "oos_failure", relative_ids),
                "High-cost-sensitivity candidates include: "
                + _taxonomy_ids_text(
                    failure_taxonomy,
                    "high_cost_sensitivity",
                    relative_ids,
                ),
                "Edge-broken candidates include: "
                + _taxonomy_ids_text(failure_taxonomy, "edge_broken", relative_ids),
            ],
            "inference": [
                "The relative/dual momentum family is not paper-ready and should not be promoted from this evidence.",
                "More relative momentum variants would mostly retest the same directional ranking hypothesis, so the next family should be materially different.",
            ],
        },
    }


def _family_scores() -> list[dict[str, object]]:
    scores = []
    for family, scorecard in _NEXT_FAMILY_SCORECARD.items():
        criteria_scores = dict(scorecard["criteria_scores"])
        missing = [
            criterion
            for criterion in _SCORING_CRITERIA
            if criterion not in criteria_scores
        ]
        if missing:
            raise ValidationError("family scorecard missing required criteria.")
        total = sum(int(criteria_scores[criterion]) for criterion in _SCORING_CRITERIA)
        scores.append(
            {
                "family": family,
                "criteria_scores": {
                    criterion: int(criteria_scores[criterion])
                    for criterion in _SCORING_CRITERIA
                },
                "total_score": total,
                "rationale": str(scorecard["rationale"]),
            }
        )
    ranked = sorted(scores, key=lambda item: (-int(item["total_score"]), str(item["family"])))
    return [
        {
            "rank": index,
            **score,
        }
        for index, score in enumerate(ranked, start=1)
    ]


def _selected_family_rationale(
    selected_family: str,
    *,
    promotion_recommendations: Mapping[str, object],
    preview_review: Mapping[str, object],
    failure_taxonomy: Mapping[str, object],
) -> dict[str, object]:
    return {
        "evidence": [
            "Inspected artifacts reported paper_candidate_count="
            + str(_paper_candidate_count(promotion_recommendations))
            + " and offline_shadow_candidate_count="
            + str(_offline_shadow_candidate_count(preview_review))
            + ".",
            "Preview review overall recommendation was "
            + str(preview_review.get("overall_recommendation"))
            + ".",
            "OOS, cost-sensitivity, anti-overfit, and paper-promotion-blocked failure categories all have inspected evidence counts: "
            + ", ".join(
                f"{key}={_mapping_or_empty(failure_taxonomy.get(key)).get('count', 0)}"
                for key in (
                    "oos_failure",
                    "high_cost_sensitivity",
                    "anti_overfit_rejection",
                    "paper_promotion_blocked",
                )
            )
            + ".",
        ],
        "inference": [
            f"{selected_family} has the highest deterministic information-value score because it tests risk-state conditioning instead of another SMA or relative-momentum lookback.",
            "The selection is a v2.18 offline research direction only; it is not paper approval, a trading recommendation, or a profitability claim.",
        ],
    }


def _rejected_or_deferred_families(
    selected_family: str,
    family_scores: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    deferred = []
    for score in family_scores:
        family = str(score.get("family"))
        if family == selected_family:
            continue
        deferred.append(
            {
                "family": family,
                "total_score": score.get("total_score"),
                "reason": str(score.get("rationale")),
            }
        )
    return deferred


def _v2_18_next_action(selected_family: str | None) -> dict[str, object]:
    if selected_family is None:
        return {
            "title": "Restore required local evidence before next-family research",
            "smallest_safe_slice": "Regenerate or repair the missing local challenger and preview review artifacts, then rerun v2.17 triage.",
            "implementation_prompt": (
                "v2.18 is blocked until v2.17 source artifacts are available, "
                "well-formed, and offline-only."
            ),
            "forbidden": _forbidden_next_action_items(),
        }
    return {
        "title": "Build deterministic volatility-regime offline evidence packet",
        "selected_family": selected_family,
        "smallest_safe_slice": (
            "Use existing local ETF adjusted daily bars to compute a fixed realized-volatility regime diagnostic and compare whether regime-conditioned exposure explains current SMA and relative-momentum failures."
        ),
        "implementation_prompt": (
            "v2.18: Add the smallest offline volatility-regime research packet. "
            "Read only existing local ETF data and v2.17/v2.16 artifacts, use a "
            "fixed predeclared regime rule, output JSON/markdown under ignored "
            "runs/, include no broker reads, no broker mutation, no paper submit, "
            "no live endpoints, no paid services, no credentials, no strategy "
            "promotion, and no profitability claim."
        ),
        "forbidden": _forbidden_next_action_items(),
    }


def _forbidden_next_action_items() -> list[str]:
    return [
        "broker reads",
        "broker mutation",
        "paper submit",
        "live endpoints",
        "live mutation",
        "paid services",
        "new credentials",
        "new market-data fetches",
        "strategy paper promotion",
        "profitability claims",
    ]


def _source_safety_violations(
    challenger_results: Mapping[str, object],
    preview_review: Mapping[str, object],
) -> list[str]:
    violations = []
    for source_name, source in (
        ("challenger_results", challenger_results),
        ("preview_candidate_review", preview_review),
    ):
        safety = _mapping_or_empty(source.get("safety"))
        for field in (
            "broker_access_attempted",
            "broker_access_performed",
            "broker_mutation_performed",
            "paper_submit_performed",
            "live_mutation_performed",
            "network_access_attempted",
            "credential_access_attempted",
        ):
            if safety.get(field) is True:
                violations.append(f"{source_name}.{field}=true")
    return violations


def _read_json_artifact(
    *,
    name: str,
    path: Path,
    required: bool,
    required_fields: Sequence[str],
) -> tuple[dict[str, object], object | None]:
    record: dict[str, object] = {
        "name": name,
        "path": str(path),
        "required": required,
        "available": False,
        "status": "unavailable",
    }
    if not path.exists():
        record["issue"] = "missing"
        return record, None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        record["issue"] = f"read_error:{exc.__class__.__name__}"
        return record, None
    record["available"] = True
    record["sha256"] = _sha256_text(text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        record["status"] = "malformed"
        record["issue"] = "json_decode_error"
        return record, None
    if not isinstance(data, Mapping):
        record["status"] = "malformed"
        record["issue"] = "top_level_json_not_object"
        return record, data
    record["record_type"] = data.get("record_type")
    record["schema_version"] = data.get("schema_version")
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        record["status"] = "incomplete"
        record["missing_fields"] = missing_fields
        return record, dict(data)
    record["status"] = "available"
    return record, dict(data)


def _promotion_recommendations(
    challenger_results: Mapping[str, object],
    promotion_artifact: object,
) -> dict[str, object]:
    artifact_mapping = _mapping_or_empty(promotion_artifact)
    if artifact_mapping:
        return dict(artifact_mapping)
    return dict(_mapping_or_empty(challenger_results.get("promotion_recommendations")))


def _cross_asset_validation(
    challenger_results: Mapping[str, object],
    cross_asset_artifact: object,
) -> dict[str, object]:
    artifact_mapping = _mapping_or_empty(cross_asset_artifact)
    if "cross_asset_validation" in artifact_mapping:
        return dict(_mapping_or_empty(artifact_mapping.get("cross_asset_validation")))
    if artifact_mapping:
        return dict(artifact_mapping)
    return dict(_mapping_or_empty(challenger_results.get("cross_asset_validation")))


def _candidate_summaries(
    results: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    grouped: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for result in results:
        candidate_id = _candidate_id(result)
        if candidate_id is not None:
            grouped[candidate_id].append(result)

    summaries = []
    for candidate_id in sorted(grouped):
        candidate_results = grouped[candidate_id]
        summaries.append(
            {
                "candidate_id": candidate_id,
                "strategy_family": _first_text(
                    result.get("strategy_family") for result in candidate_results
                ),
                "symbols": sorted(
                    {
                        str(result.get("symbol"))
                        for result in candidate_results
                        if result.get("symbol")
                    }
                ),
                "promotion_classifications": sorted(
                    {
                        str(result.get("promotion_classification"))
                        for result in candidate_results
                        if result.get("promotion_classification")
                    }
                ),
                "promotion_reasons": sorted(
                    {
                        reason
                        for result in candidate_results
                        for reason in _string_list(result.get("promotion_reasons"))
                    }
                ),
                "oos_failed_symbols": sorted(
                    {
                        str(result.get("symbol"))
                        for result in candidate_results
                        if _result_has_oos_failure(result) and result.get("symbol")
                    }
                ),
                "high_cost_sensitivity_symbols": sorted(
                    {
                        str(result.get("symbol"))
                        for result in candidate_results
                        if _result_highly_cost_sensitive(result)
                        and result.get("symbol")
                    }
                ),
                "edge_broken_symbols": sorted(
                    {
                        str(result.get("symbol"))
                        for result in candidate_results
                        if _result_edge_broken(result) and result.get("symbol")
                    }
                ),
            }
        )
    return summaries


def _candidate_rollups(value: object) -> list[Mapping[str, object]]:
    mapping = _mapping_or_empty(value)
    rollups = mapping.get("candidate_rollups")
    if not isinstance(rollups, Sequence) or isinstance(rollups, (str, bytes)):
        return []
    return [dict(item) for item in rollups if isinstance(item, Mapping)]


def _result_has_oos_failure(result: Mapping[str, object]) -> bool:
    validation = _mapping_or_empty(result.get("out_of_sample_validation"))
    return (
        result.get("oos_status") == "failed"
        or validation.get("validation_failed") is True
        or validation.get("validation_passed") is False
        or validation.get("primary_window_failed") is True
    )


def _result_edge_broken(result: Mapping[str, object]) -> bool:
    summary = _mapping_or_empty(result.get("cost_sensitivity_summary"))
    return (
        result.get("cost_sensitivity_status") == "edge_broken"
        or summary.get("edge_broken_by_moderate_cost") is True
    )


def _result_highly_cost_sensitive(result: Mapping[str, object]) -> bool:
    summary = _mapping_or_empty(result.get("cost_sensitivity_summary"))
    return (
        result.get("cost_sensitivity_status") == "highly_sensitive"
        or summary.get("returns_highly_cost_sensitive") is True
    )


def _result_incomplete(result: Mapping[str, object]) -> bool:
    return not (
        result.get("candidate_id")
        and result.get("strategy_family")
        and result.get("promotion_classification")
    )


def _incomplete_candidate_record_ids(
    results: Sequence[Mapping[str, object]],
) -> list[str]:
    incomplete = []
    for index, result in enumerate(results):
        if _result_incomplete(result):
            incomplete.append(str(result.get("candidate_id") or f"result_index_{index}"))
    return incomplete


def _empty_taxonomy_item(description: str) -> dict[str, object]:
    return {
        "description": description,
        "candidate_ids": [],
        "details": [],
    }


def _append_taxonomy_detail(
    item: dict[str, object],
    candidate_id: str,
    detail: str,
) -> None:
    ids = item["candidate_ids"]
    details = item["details"]
    if isinstance(ids, list):
        ids.append(candidate_id)
    if isinstance(details, list):
        details.append({"candidate_id": candidate_id, "detail": detail})


def _finalize_taxonomy_item(item: Mapping[str, object]) -> dict[str, object]:
    candidate_ids = sorted(set(_string_list(item.get("candidate_ids"))))
    details = _detail_records(item.get("details"))
    return {
        "description": item.get("description"),
        "count": len(candidate_ids),
        "candidate_ids": candidate_ids,
        "details": details,
    }


def _detail_records(value: object) -> list[dict[str, object]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    records = [dict(item) for item in value if isinstance(item, Mapping)]
    return sorted(
        records,
        key=lambda item: (str(item.get("candidate_id")), str(item.get("detail"))),
    )


def _result_detail(result: Mapping[str, object]) -> str:
    parts = []
    for field in (
        "symbol",
        "promotion_classification",
        "oos_status",
        "cost_sensitivity_status",
    ):
        if result.get(field) is not None:
            parts.append(f"{field}={result.get(field)}")
    reasons = _string_list(result.get("promotion_reasons"))
    if reasons:
        parts.append("promotion_reasons=" + ",".join(reasons))
    return "; ".join(parts)


def _taxonomy_ids_text(
    failure_taxonomy: Mapping[str, object],
    category: str,
    filter_ids: Sequence[str],
) -> str:
    category_item = _mapping_or_empty(failure_taxonomy.get(category))
    ids = set(_string_list(category_item.get("candidate_ids")))
    filtered = sorted(ids.intersection(set(filter_ids)))
    return ", ".join(filtered) if filtered else "none"


def _paper_candidate_count(promotion_recommendations: Mapping[str, object]) -> int:
    return _int_or_zero(promotion_recommendations.get("paper_candidate_count"))


def _offline_shadow_candidate_count(preview_review: Mapping[str, object]) -> int:
    candidates = preview_review.get("offline_shadow_candidates")
    if isinstance(candidates, Sequence) and not isinstance(candidates, (str, bytes)):
        return len(candidates)
    return _int_or_zero(preview_review.get("offline_shadow_candidate_count"))


def _safety_payload() -> dict[str, object]:
    return {
        "research_only": True,
        "offline_only": True,
        "not_live_authorized": True,
        "broker_state_not_required": True,
        "broker_access_performed": False,
        "broker_mutation_performed": False,
        "paper_submit_authorized": False,
        "paper_submit_performed": False,
        "live_mutation_performed": False,
        "profit_claim": "none",
        "no_strategy_promoted": True,
    }


def _manifest_payload(
    payload: Mapping[str, object],
    root: Path,
    artifact_paths: Sequence[Path],
) -> dict[str, object]:
    return {
        "record_type": "research_hypothesis_triage_manifest",
        "schema_version": _SCHEMA_VERSION,
        "phase": payload.get("phase"),
        "classification": payload.get("classification"),
        "generated_at": payload.get("generated_at"),
        "artifact_count": len(artifact_paths),
        "artifacts": [
            {
                "name": artifact_path.name,
                "path": str(artifact_path),
                "sha256": _sha256_file(artifact_path),
            }
            for artifact_path in artifact_paths
        ],
        "output_root": str(root),
        "safety": _safety_payload(),
    }


def _deterministic_generated_at(challenger_results: Mapping[str, object]) -> str:
    as_of_end = challenger_results.get("as_of_end")
    if isinstance(as_of_end, str) and as_of_end:
        return f"{as_of_end}T00:00:00Z"
    run_id = challenger_results.get("run_id")
    if isinstance(run_id, str) and run_id:
        return f"source_run:{run_id}"
    return "source_artifacts_unavailable"


def _validate_classification(classification: str) -> str:
    if classification not in RESEARCH_HYPOTHESIS_TRIAGE_CLASSIFICATIONS:
        raise ValidationError("unsupported research hypothesis triage classification.")
    return classification


def _config(config: ResearchHypothesisTriageConfig) -> ResearchHypothesisTriageConfig:
    if not isinstance(config, ResearchHypothesisTriageConfig):
        raise TypeError("config must be ResearchHypothesisTriageConfig.")
    return config


def _mapping_or_empty(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _artifact_records(value: object) -> list[dict[str, object]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _result_list(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _review_list(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _score_records(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value)


def _candidate_id(result: Mapping[str, object]) -> str | None:
    value = result.get("candidate_id")
    if isinstance(value, str) and value:
        return value
    return None


def _first_text(values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def _int_or_zero(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _compact_mapping(value: Mapping[str, object]) -> str:
    if not value:
        return "{}"
    return ", ".join(f"{key}={value[key]}" for key in sorted(value))


def _path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value:
        return Path(value)
    raise ValidationError(f"{field_name} must be a non-empty path.")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _json_dumps(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build deterministic offline v2.17 research hypothesis triage artifacts."
    )
    parser.add_argument(
        "--challenger-root",
        default=str(_DEFAULT_CHALLENGER_ROOT),
        help="Directory containing strategy challenger artifacts.",
    )
    parser.add_argument(
        "--preview-review-root",
        default=str(_DEFAULT_PREVIEW_REVIEW_ROOT),
        help="Directory containing preview candidate review artifacts.",
    )
    parser.add_argument(
        "--output-root",
        default=str(_DEFAULT_OUTPUT_ROOT),
        help="Directory where triage artifacts will be written.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = run_research_hypothesis_triage(
        ResearchHypothesisTriageConfig(
            challenger_root=args.challenger_root,
            preview_review_root=args.preview_review_root,
            output_root=args.output_root,
        )
    )
    print("research_hypothesis_triage_status=completed")
    print(f"classification={payload.get('classification')}")
    print(f"selected_next_family={payload.get('selected_next_family')}")
    print(f"paper_candidate_count={payload.get('paper_candidate_count')}")
    print(
        "offline_shadow_candidate_count="
        f"{payload.get('offline_shadow_candidate_count')}"
    )
    print("broker_access_performed=false")
    print("broker_mutation_performed=false")
    print("paper_submit_performed=false")
    print("live_mutation_performed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
