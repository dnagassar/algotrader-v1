"""Offline v2.15 preview-only candidate anti-overfit review."""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

from algotrader.errors import ValidationError

__all__ = [
    "PREVIEW_CANDIDATE_FINAL_CLASSIFICATIONS",
    "PREVIEW_CANDIDATE_OVERALL_RECOMMENDATIONS",
    "PREVIEW_CANDIDATE_REVIEW_LABELS",
    "PreviewCandidateReviewConfig",
    "build_preview_candidate_review_payload",
    "classify_preview_candidate_review",
    "load_preview_candidate_review_inputs",
    "main",
    "render_preview_candidate_review_markdown",
    "run_preview_candidate_review",
    "validate_preview_review_classification",
    "write_preview_candidate_review_artifacts",
]


PREVIEW_CANDIDATE_REVIEW_LABELS = (
    "research_only",
    "offline_only",
    "not_live_authorized",
    "profit_claim=none",
    "no_paper_promotion",
)
PREVIEW_CANDIDATE_FINAL_CLASSIFICATIONS = (
    "reject_preview",
    "keep_researching",
    "offline_shadow_candidate",
)
PREVIEW_CANDIDATE_OVERALL_RECOMMENDATIONS = (
    "reject_all_preview_only",
    "keep_researching_selected",
    "promote_to_offline_shadow_candidate",
)

_RECORD_TYPE = "preview_candidate_review"
_SCHEMA_VERSION = "1"
_REVIEW_ID = "v2.15_preview_candidate_review"
_DEFAULT_INPUT_ROOT = Path("runs/strategy_challengers/latest")
_DEFAULT_OUTPUT_ROOT = Path("runs/strategy_challengers/preview_review_latest")
_BASELINE_CANDIDATE_ID = "spy_sma_50_200_baseline"
_BUY_AND_HOLD_COMPARATOR_ID = "spy_buy_and_hold_comparator"
_CASH_RISK_OFF_COMPARATOR_ID = "spy_sma_50_200_cash_risk_off_comparator"
_OPERATING_SYMBOL = "SPY"
_LATER_TEST_WINDOW_ID = "later_test"
_MODERATE_COST_IDS = {"moderate_cost", "moderate_cost_5bps"}
_HASH_CHUNK_SIZE = 1024 * 1024

_DEFAULT_LIMITATIONS = (
    "offline deterministic research only",
    "second-stage review of preview-only challenger evidence",
    "uses local strategy challenger artifacts only",
    "no new market data, broker reads, broker mutation, paper submit, live submit, or capital authority",
    "anti-overfit flags are deterministic review heuristics, not trading recommendations",
    "offline shadow candidate is not a paper candidate",
)


@dataclass(frozen=True, slots=True)
class PreviewCandidateReviewConfig:
    """Inputs for one offline preview-only candidate review."""

    output_root: Path | str
    input_root: Path | str = _DEFAULT_INPUT_ROOT

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_root", _path(self.output_root, "output_root"))
        object.__setattr__(self, "input_root", _path(self.input_root, "input_root"))


def run_preview_candidate_review(
    config: PreviewCandidateReviewConfig,
) -> dict[str, object]:
    """Load challenger artifacts, build the review, and write review artifacts."""

    checked_config = _config(config)
    inputs = load_preview_candidate_review_inputs(checked_config.input_root)
    payload = build_preview_candidate_review_payload(
        inputs,
        source_root=checked_config.input_root,
    )
    manifest = write_preview_candidate_review_artifacts(
        payload,
        checked_config.output_root,
    )
    result = dict(payload)
    result["manifest"] = manifest
    return result


def load_preview_candidate_review_inputs(
    input_root: Path | str,
) -> dict[str, object]:
    """Load the local strategy challenger artifacts needed by the review."""

    root = _path(input_root, "input_root")
    challenger_results = _read_required_json(root / "challenger_results.json")
    promotion_recommendations = _read_optional_json(
        root / "promotion_recommendations.json"
    )
    strategy_review_packet = _read_optional_json(root / "strategy_review_packet.json")
    cross_asset_validation_artifact = _read_optional_json(
        root / "cross_asset_validation.json"
    )
    return {
        "input_root": str(root),
        "challenger_results": challenger_results,
        "promotion_recommendations": promotion_recommendations,
        "strategy_review_packet": strategy_review_packet,
        "cross_asset_validation": _normalize_cross_asset_validation(
            cross_asset_validation_artifact,
            challenger_results,
        ),
    }


def build_preview_candidate_review_payload(
    inputs: Mapping[str, object],
    *,
    source_root: Path | str | None = None,
) -> dict[str, object]:
    """Build the deterministic anti-overfit review payload."""

    input_items = dict(inputs)
    challenger_results = _mapping_required(
        input_items.get("challenger_results"),
        "challenger_results",
    )
    promotion_recommendations = _mapping_or_empty(
        input_items.get("promotion_recommendations")
    )
    strategy_review_packet = _mapping_or_empty(
        input_items.get("strategy_review_packet")
    )
    cross_asset_validation = _mapping_or_empty(
        input_items.get("cross_asset_validation")
    )
    results = _result_list(challenger_results)
    preview_results = [
        result
        for result in results
        if result.get("promotion_classification") == "preview_only"
    ]
    preview_candidate_ids = sorted(
        {
            str(result.get("candidate_id"))
            for result in preview_results
            if result.get("candidate_id") is not None
        }
    )
    candidate_reviews = [
        _candidate_review(
            candidate_id,
            results=results,
            preview_results=preview_results,
            strategy_review_packet=strategy_review_packet,
            cross_asset_validation=cross_asset_validation,
        )
        for candidate_id in preview_candidate_ids
    ]
    overall_recommendation = _overall_recommendation(candidate_reviews)
    offline_shadow_candidates = [
        _offline_shadow_candidate_record(review)
        for review in candidate_reviews
        if review.get("final_review_classification") == "offline_shadow_candidate"
    ]
    source_root_text = (
        str(source_root)
        if source_root is not None
        else str(input_items.get("input_root") or "")
    )
    payload = {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "review_id": _REVIEW_ID,
        "source_artifact_root": source_root_text,
        "source_factory_id": challenger_results.get("factory_id"),
        "source_run_id": challenger_results.get("run_id"),
        "source_promotion_recommendation": promotion_recommendations.get(
            "classification_recommendation"
        )
        or _mapping_or_empty(
            challenger_results.get("promotion_recommendations")
        ).get("classification_recommendation"),
        "labels": list(PREVIEW_CANDIDATE_REVIEW_LABELS),
        "operating_baseline_symbol": challenger_results.get(
            "operating_baseline_symbol",
            _OPERATING_SYMBOL,
        ),
        "symbols": list(challenger_results.get("symbols", [])),
        "preview_result_count": len(preview_results),
        "preview_candidate_count": len(candidate_reviews),
        "paper_candidate_forbidden": True,
        "paper_candidate_count": 0,
        "overall_recommendation": overall_recommendation,
        "candidate_reviews": candidate_reviews,
        "anti_overfit_flags": _anti_overfit_flags_artifact(candidate_reviews),
        "offline_shadow_candidates": offline_shadow_candidates,
        "safety": _safety_payload(),
        "limitations": list(_DEFAULT_LIMITATIONS),
    }
    _assert_no_paper_candidate_classification(payload)
    return payload


def classify_preview_candidate_review(
    *,
    anti_overfit_flags: Mapping[str, object],
    oos_summary: Mapping[str, object],
    cost_sensitivity_summary: Mapping[str, object],
) -> tuple[str, tuple[str, ...]]:
    """Classify one preview-only candidate under v2.15 offline review rules."""

    flags = {str(key): bool(value) for key, value in anti_overfit_flags.items()}
    oos = dict(oos_summary)
    cost = dict(cost_sensitivity_summary)
    reasons: list[str] = []

    if flags.get("severe_return_degradation_flag"):
        reasons.append("severe_return_degradation")
    if flags.get("baseline_similarity_flag"):
        reasons.append("too_similar_to_operating_baseline")
    if flags.get("cost_fragility_flag") and flags.get("high_churn_flag"):
        reasons.append("high_churn_cost_fragility")
    if (
        flags.get("window_instability_flag")
        and flags.get("single_symbol_edge_flag")
        and flags.get("concentrated_edge_flag")
    ):
        reasons.append("single_symbol_window_unstable_edge")
    if (
        flags.get("cost_fragility_flag")
        and flags.get("window_instability_flag")
        and flags.get("concentrated_edge_flag")
    ):
        reasons.append("fragile_concentrated_unstable_edge")

    if reasons:
        return "reject_preview", tuple(dict.fromkeys(reasons))

    oos_passed_symbols = tuple(
        str(symbol) for symbol in oos.get("oos_passed_symbols", [])
    )
    fragile_symbols = tuple(
        str(symbol) for symbol in cost.get("fragile_symbols", [])
    )
    if (
        oos.get("spy_oos_passed") is True
        and len(oos_passed_symbols) >= 2
        and not fragile_symbols
        and not any(flags.values())
    ):
        return "offline_shadow_candidate", (
            "strict_oos_and_cost_review_passed_offline_only",
        )

    return "keep_researching", ("preview_evidence_interesting_but_not_shadow_ready",)


def validate_preview_review_classification(classification: str) -> str:
    """Validate a v2.15 preview review classification."""

    checked = _required_string(classification, "classification")
    if checked == "paper_candidate":
        raise ValidationError("v2.15 preview review cannot classify paper_candidate.")
    if checked not in PREVIEW_CANDIDATE_FINAL_CLASSIFICATIONS:
        raise ValidationError("unsupported preview review classification.")
    return checked


def write_preview_candidate_review_artifacts(
    payload: Mapping[str, object],
    output_root: Path | str,
) -> dict[str, object]:
    """Write required JSON, markdown, flags, shadow list, and manifest files."""

    root = _path(output_root, "output_root")
    root.mkdir(parents=True, exist_ok=True)
    payload_dict = dict(payload)
    _assert_no_paper_candidate_classification(payload_dict)

    artifact_writers = (
        (
            "preview_candidate_review.json",
            lambda path: _write_text(path, _json_dumps(payload_dict) + "\n"),
        ),
        (
            "preview_candidate_review.md",
            lambda path: _write_text(
                path,
                render_preview_candidate_review_markdown(payload_dict),
            ),
        ),
        (
            "anti_overfit_flags.json",
            lambda path: _write_text(
                path,
                _json_dumps(_anti_overfit_flags_artifact(payload_dict.get("candidate_reviews", [])))
                + "\n",
            ),
        ),
        (
            "offline_shadow_candidates.json",
            lambda path: _write_text(
                path,
                _json_dumps(_offline_shadow_candidates_artifact(payload_dict)) + "\n",
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


def render_preview_candidate_review_markdown(payload: Mapping[str, object]) -> str:
    """Render the preview candidate review as compact markdown."""

    payload_dict = dict(payload)
    lines = [
        "# Preview Candidate Review",
        "",
        "Labels: " + ", ".join(str(item) for item in payload_dict.get("labels", [])),
        "",
        "## Summary",
        f"- review_id: {payload_dict.get('review_id')}",
        f"- source_run_id: {payload_dict.get('source_run_id')}",
        f"- preview_result_count: {payload_dict.get('preview_result_count')}",
        f"- preview_candidate_count: {payload_dict.get('preview_candidate_count')}",
        f"- overall_recommendation: {payload_dict.get('overall_recommendation')}",
        "- paper_candidate_count: 0",
        "- broker_access_performed: false",
        "- broker_mutation_performed: false",
        "- paper_submit_performed: false",
        "- live_mutation_performed: false",
        "",
        "## Candidate Reviews",
        "| candidate_id | preview_symbols | OOS passed | fragile symbols | flags | classification |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for review in _review_list(payload_dict.get("candidate_reviews", [])):
        oos = _mapping_or_empty(review.get("oos_summary"))
        cost = _mapping_or_empty(review.get("cost_sensitivity_summary"))
        flags = _mapping_or_empty(review.get("anti_overfit_flags"))
        active_flags = [
            str(name)
            for name, value in flags.items()
            if value is True
        ]
        lines.append(
            "| {candidate_id} | {preview_symbols} | {oos_passed} | {fragile} | {flags} | {classification} |".format(
                candidate_id=review.get("candidate_id"),
                preview_symbols=", ".join(
                    str(item) for item in review.get("preview_symbols", [])
                ),
                oos_passed=", ".join(
                    str(item) for item in oos.get("oos_passed_symbols", [])
                ),
                fragile=", ".join(
                    str(item) for item in cost.get("fragile_symbols", [])
                ),
                flags=", ".join(active_flags) if active_flags else "none",
                classification=review.get("final_review_classification"),
            )
        )

    lines.extend(["", "## Operator Takeaways"])
    for review in _review_list(payload_dict.get("candidate_reviews", [])):
        lines.append(
            "- {candidate_id}: {takeaway}".format(
                candidate_id=review.get("candidate_id"),
                takeaway=review.get("operator_takeaway"),
            )
        )

    lines.extend(["", "## Limitations"])
    for limitation in payload_dict.get("limitations", []):
        lines.append(f"- {limitation}")
    lines.append("")
    return "\n".join(lines)


def _candidate_review(
    candidate_id: str,
    *,
    results: Sequence[Mapping[str, object]],
    preview_results: Sequence[Mapping[str, object]],
    strategy_review_packet: Mapping[str, object],
    cross_asset_validation: Mapping[str, object],
) -> dict[str, object]:
    candidate_results = [
        dict(result) for result in results if result.get("candidate_id") == candidate_id
    ]
    candidate_preview_results = [
        dict(result)
        for result in preview_results
        if result.get("candidate_id") == candidate_id
    ]
    if not candidate_preview_results:
        raise ValidationError("candidate review requires preview-only evidence.")

    preview_symbols = _sorted_symbols(
        result.get("symbol") for result in candidate_preview_results
    )
    symbols_evaluated = _sorted_symbols(
        result.get("symbol")
        for result in candidate_results
        if result.get("metrics_status") == "valid"
    )
    if not symbols_evaluated:
        symbols_evaluated = preview_symbols

    oos_summary = _oos_summary(candidate_results, candidate_preview_results)
    cost_summary = _cost_summary(candidate_results, candidate_preview_results)
    transition_summary = _transition_summary(candidate_results)
    drawdown_summary = _drawdown_summary(candidate_results)
    return_summary = _return_degradation_summary(candidate_results)
    baseline_comparison = _baseline_comparison_summary(candidate_results)
    edge_concentration = _edge_concentration_summary(candidate_results)
    material_difference = _material_difference_summary(candidate_preview_results)
    review_packet_summary = _review_packet_candidate_summary(
        strategy_review_packet,
        candidate_id,
    )
    cross_asset_summary = _cross_asset_candidate_summary(
        cross_asset_validation,
        candidate_id,
    )
    flags = {
        "concentrated_edge_flag": bool(edge_concentration["edge_concentrated"]),
        "single_symbol_edge_flag": len(oos_summary["oos_passed_symbols"]) <= 1,
        "window_instability_flag": bool(oos_summary["window_instability_detected"]),
        "high_churn_flag": bool(transition_summary["high_churn_symbols"]),
        "cost_fragility_flag": bool(cost_summary["fragile_symbols"]),
        "baseline_similarity_flag": not bool(material_difference["materially_different"]),
        "severe_return_degradation_flag": bool(
            return_summary["severe_return_degradation_symbols"]
            or return_summary["severe_oos_window_degradation_symbols"]
        ),
    }
    classification, reasons = classify_preview_candidate_review(
        anti_overfit_flags=flags,
        oos_summary=oos_summary,
        cost_sensitivity_summary=cost_summary,
    )
    classification = validate_preview_review_classification(classification)

    return {
        "candidate_id": candidate_id,
        "symbols_evaluated": symbols_evaluated,
        "preview_symbols": preview_symbols,
        "preview_reason": _preview_reasons(candidate_preview_results),
        "anti_overfit_flags": flags,
        "anti_overfit_reasons": list(reasons),
        "oos_summary": oos_summary,
        "cost_sensitivity_summary": cost_summary,
        "transition_churn_summary": transition_summary,
        "drawdown_behavior_summary": drawdown_summary,
        "return_degradation_summary": return_summary,
        "edge_concentration_summary": edge_concentration,
        "baseline_comparison": baseline_comparison,
        "material_difference_from_spy_sma_50_200": material_difference,
        "strategy_review_packet_summary": review_packet_summary,
        "cross_asset_summary": cross_asset_summary,
        "operator_takeaway": _operator_takeaway(classification, flags, reasons),
        "final_review_classification": classification,
        "limitations": list(_DEFAULT_LIMITATIONS),
        "safety_labels": list(PREVIEW_CANDIDATE_REVIEW_LABELS),
    }


def _oos_summary(
    candidate_results: Sequence[Mapping[str, object]],
    preview_results: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    per_symbol: dict[str, dict[str, object]] = {}
    oos_passed_symbols: list[str] = []
    oos_failed_symbols: list[str] = []
    window_instability_detected = False
    for result in candidate_results:
        symbol = str(result.get("symbol"))
        validation = _mapping_or_empty(result.get("out_of_sample_validation"))
        failed_window_count = _int_or_zero(validation.get("failed_window_count"))
        passed_window_count = _int_or_zero(validation.get("passed_window_count"))
        status = str(result.get("oos_status", "not_evaluable"))
        if status == "passed":
            oos_passed_symbols.append(symbol)
        if status == "failed":
            oos_failed_symbols.append(symbol)
        if status != "passed" and result in preview_results:
            window_instability_detected = True
        if failed_window_count > 0 and result in preview_results:
            window_instability_detected = True
        per_symbol[symbol] = {
            "oos_status": status,
            "validation_passed": validation.get("validation_passed") is True,
            "validation_failed": validation.get("validation_failed") is True,
            "passed_window_count": passed_window_count,
            "failed_window_count": failed_window_count,
            "primary_window_passed": validation.get("primary_window_passed") is True,
            "primary_window_failed": validation.get("primary_window_failed") is True,
            "window_results": _window_result_summary(validation.get("window_results", [])),
        }

    spy = per_symbol.get(_OPERATING_SYMBOL, {})
    non_spy_passed = [
        symbol for symbol in sorted(set(oos_passed_symbols)) if symbol != _OPERATING_SYMBOL
    ]
    non_spy_failed = [
        symbol for symbol in sorted(set(oos_failed_symbols)) if symbol != _OPERATING_SYMBOL
    ]
    return {
        "spy_oos_status": spy.get("oos_status", "not_evaluable"),
        "spy_oos_passed": spy.get("oos_status") == "passed",
        "spy_oos_failed": spy.get("oos_status") == "failed",
        "non_spy_oos_passed_symbols": non_spy_passed,
        "non_spy_oos_failed_symbols": non_spy_failed,
        "oos_passed_symbols": sorted(set(oos_passed_symbols)),
        "oos_failed_symbols": sorted(set(oos_failed_symbols)),
        "window_instability_detected": window_instability_detected,
        "per_symbol": per_symbol,
    }


def _cost_summary(
    candidate_results: Sequence[Mapping[str, object]],
    preview_results: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    per_symbol: dict[str, dict[str, object]] = {}
    fragile_symbols: list[str] = []
    max_return_degradation: Decimal | None = None
    for result in candidate_results:
        symbol = str(result.get("symbol"))
        summary = _mapping_or_empty(result.get("cost_sensitivity_summary"))
        status = str(result.get("cost_sensitivity_status", "not_evaluable"))
        edge_broken = summary.get("edge_broken_by_moderate_cost") is True
        highly_sensitive = summary.get("returns_highly_cost_sensitive") is True
        fragile = status in {"edge_broken", "highly_sensitive"} or edge_broken or highly_sensitive
        if fragile and result in preview_results:
            fragile_symbols.append(symbol)
        degradation = _optional_decimal(summary.get("moderate_cost_return_degradation"))
        if degradation is not None:
            max_return_degradation = (
                degradation
                if max_return_degradation is None
                else max(max_return_degradation, degradation)
            )
        per_symbol[symbol] = {
            "cost_sensitivity_status": status,
            "edge_broken_by_moderate_cost": edge_broken,
            "returns_highly_cost_sensitive": highly_sensitive,
            "moderate_cost_return_degradation": _decimal_text_or_none(degradation),
            "moderate_cost_edge_degradation": _decimal_text_or_none(
                _optional_decimal(summary.get("moderate_cost_edge_degradation"))
            ),
            "zero_cost_baseline_total_return_delta": summary.get(
                "zero_cost_baseline_total_return_delta"
            ),
            "moderate_cost_baseline_total_return_delta": summary.get(
                "moderate_cost_baseline_total_return_delta"
            ),
        }
    return {
        "fragile_symbols": sorted(set(fragile_symbols)),
        "max_moderate_cost_return_degradation": _decimal_text_or_none(
            max_return_degradation
        ),
        "per_symbol": per_symbol,
    }


def _transition_summary(
    candidate_results: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    baseline_by_symbol = {
        str(result.get("symbol")): dict(result)
        for result in candidate_results
        if result.get("candidate_id") == _BASELINE_CANDIDATE_ID
    }
    per_symbol: dict[str, dict[str, object]] = {}
    high_churn_symbols: list[str] = []
    max_transition_count = 0
    for result in candidate_results:
        candidate_id = str(result.get("candidate_id"))
        if candidate_id == _BASELINE_CANDIDATE_ID:
            continue
        symbol = str(result.get("symbol"))
        transition_count = _int_or_zero(result.get("transition_count"))
        max_transition_count = max(max_transition_count, transition_count)
        baseline_transition_count = _int_or_zero(
            baseline_by_symbol.get(symbol, {}).get("transition_count")
        )
        high_churn = _is_high_churn(transition_count, baseline_transition_count)
        if high_churn:
            high_churn_symbols.append(symbol)
        per_symbol[symbol] = {
            "transition_count": transition_count,
            "baseline_transition_count": baseline_transition_count,
            "transition_count_delta": transition_count - baseline_transition_count,
            "high_churn": high_churn,
        }
    return {
        "max_transition_count": max_transition_count,
        "high_churn_symbols": sorted(set(high_churn_symbols)),
        "per_symbol": per_symbol,
    }


def _drawdown_summary(
    candidate_results: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    per_symbol: dict[str, dict[str, object]] = {}
    worse_symbols: list[str] = []
    improved_symbols: list[str] = []
    for result in candidate_results:
        symbol = str(result.get("symbol"))
        drawdown_delta = _optional_decimal(result.get("baseline_max_drawdown_delta"))
        if drawdown_delta is not None:
            if drawdown_delta > Decimal("0"):
                worse_symbols.append(symbol)
            elif drawdown_delta < Decimal("0"):
                improved_symbols.append(symbol)
        per_symbol[symbol] = {
            "max_drawdown": result.get("max_drawdown"),
            "baseline_max_drawdown_delta": _decimal_text_or_none(drawdown_delta),
            "drawdown_improved_vs_baseline": drawdown_delta is not None
            and drawdown_delta < Decimal("0"),
            "drawdown_worse_vs_baseline": drawdown_delta is not None
            and drawdown_delta > Decimal("0"),
        }
    return {
        "drawdown_improved_symbols": sorted(set(improved_symbols)),
        "drawdown_worse_symbols": sorted(set(worse_symbols)),
        "per_symbol": per_symbol,
    }


def _return_degradation_summary(
    candidate_results: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    per_symbol: dict[str, dict[str, object]] = {}
    severe_symbols: list[str] = []
    severe_oos_symbols: list[str] = []
    worst_oos_delta: Decimal | None = None
    for result in candidate_results:
        symbol = str(result.get("symbol"))
        return_delta = _optional_decimal(result.get("baseline_total_return_delta"))
        if return_delta is not None and return_delta <= Decimal("-0.05"):
            severe_symbols.append(symbol)
        oos_window_deltas = _oos_window_return_deltas(result)
        symbol_worst_oos = min(oos_window_deltas, default=None)
        if symbol_worst_oos is not None:
            worst_oos_delta = (
                symbol_worst_oos
                if worst_oos_delta is None
                else min(worst_oos_delta, symbol_worst_oos)
            )
            if symbol_worst_oos <= Decimal("-0.20"):
                severe_oos_symbols.append(symbol)
        per_symbol[symbol] = {
            "baseline_total_return_delta": _decimal_text_or_none(return_delta),
            "worst_oos_window_total_return_delta": _decimal_text_or_none(
                symbol_worst_oos
            ),
            "severe_full_sample_return_degradation": return_delta is not None
            and return_delta <= Decimal("-0.05"),
            "severe_oos_window_return_degradation": symbol_worst_oos is not None
            and symbol_worst_oos <= Decimal("-0.20"),
        }
    return {
        "severe_return_degradation_symbols": sorted(set(severe_symbols)),
        "severe_oos_window_degradation_symbols": sorted(set(severe_oos_symbols)),
        "worst_oos_window_total_return_delta": _decimal_text_or_none(worst_oos_delta),
        "per_symbol": per_symbol,
    }


def _baseline_comparison_summary(
    candidate_results: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    per_symbol: dict[str, dict[str, object]] = {}
    for result in candidate_results:
        symbol = str(result.get("symbol"))
        per_symbol[symbol] = {
            "baseline_candidate_id": result.get(
                "baseline_candidate_id",
                _BASELINE_CANDIDATE_ID,
            ),
            "baseline_total_return_delta": result.get("baseline_total_return_delta"),
            "baseline_max_drawdown_delta": result.get("baseline_max_drawdown_delta"),
            "baseline_sharpe_ratio_delta": result.get("baseline_sharpe_ratio_delta"),
            "same_as_baseline": _mapping_or_empty(
                result.get("benchmark_baseline_comparison")
            ).get("same_as_baseline")
            is True,
        }
    return {
        "baseline_candidate_id": _BASELINE_CANDIDATE_ID,
        "per_symbol": per_symbol,
    }


def _edge_concentration_summary(
    candidate_results: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    positive_edges_by_symbol: dict[str, Decimal] = {}
    positive_edges_by_window: dict[str, Decimal] = {}
    for result in candidate_results:
        symbol = str(result.get("symbol"))
        edge = _optional_decimal(result.get("baseline_total_return_delta"))
        if edge is not None and edge > Decimal("0"):
            positive_edges_by_symbol[symbol] = positive_edges_by_symbol.get(
                symbol,
                Decimal("0"),
            ) + edge
        for window_key, window_edge in _positive_oos_window_edges(result):
            positive_edges_by_window[f"{symbol}:{window_key}"] = window_edge

    symbol_share = _strongest_edge_share(positive_edges_by_symbol)
    window_share = _strongest_edge_share(positive_edges_by_window)
    edge_concentrated = (
        bool(positive_edges_by_symbol)
        and (len(positive_edges_by_symbol) <= 1 or symbol_share >= Decimal("0.70"))
    ) or (
        bool(positive_edges_by_window)
        and (len(positive_edges_by_window) <= 1 or window_share >= Decimal("0.70"))
    )
    return {
        "positive_edge_symbols": sorted(positive_edges_by_symbol),
        "positive_oos_edge_windows": sorted(positive_edges_by_window),
        "strongest_symbol_edge_share": _decimal_text(symbol_share),
        "strongest_window_edge_share": _decimal_text(window_share),
        "edge_concentrated": edge_concentrated,
    }


def _material_difference_summary(
    preview_results: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    materially_different_symbols: list[str] = []
    baseline_like_symbols: list[str] = []
    per_symbol: dict[str, dict[str, object]] = {}
    for result in preview_results:
        symbol = str(result.get("symbol"))
        return_delta = _optional_decimal(result.get("baseline_total_return_delta"))
        drawdown_delta = _optional_decimal(result.get("baseline_max_drawdown_delta"))
        sharpe_delta = _optional_decimal(result.get("baseline_sharpe_ratio_delta"))
        transition_count = _int_or_zero(result.get("transition_count"))
        same_as_baseline = _mapping_or_empty(
            result.get("benchmark_baseline_comparison")
        ).get("same_as_baseline") is True
        baseline_like = bool(
            same_as_baseline
            or (
                _abs_or_large(return_delta) <= Decimal("0.02")
                and _abs_or_large(drawdown_delta) <= Decimal("0.01")
                and _abs_or_large(sharpe_delta) <= Decimal("0.05")
                and transition_count <= 40
            )
        )
        if baseline_like:
            baseline_like_symbols.append(symbol)
        else:
            materially_different_symbols.append(symbol)
        per_symbol[symbol] = {
            "baseline_like": baseline_like,
            "baseline_total_return_delta": _decimal_text_or_none(return_delta),
            "baseline_max_drawdown_delta": _decimal_text_or_none(drawdown_delta),
            "baseline_sharpe_ratio_delta": _decimal_text_or_none(sharpe_delta),
            "transition_count": transition_count,
        }
    materially_different = bool(materially_different_symbols) and not (
        baseline_like_symbols and not materially_different_symbols
    )
    return {
        "materially_different": materially_different,
        "materially_different_symbols": sorted(set(materially_different_symbols)),
        "baseline_like_symbols": sorted(set(baseline_like_symbols)),
        "per_symbol": per_symbol,
    }


def _review_packet_candidate_summary(
    packet: Mapping[str, object],
    candidate_id: str,
) -> dict[str, object]:
    candidates = packet.get("candidates", [])
    if not isinstance(candidates, Iterable) or isinstance(
        candidates,
        (str, bytes, Mapping),
    ):
        return {}
    matching = [
        dict(candidate)
        for candidate in candidates
        if isinstance(candidate, Mapping)
        and candidate.get("candidate_id") == candidate_id
    ]
    return {
        "matching_review_records": len(matching),
        "operator_takeaways": [
            str(candidate.get("operator_takeaway"))
            for candidate in matching
            if candidate.get("operator_takeaway")
        ],
    }


def _cross_asset_candidate_summary(
    cross_asset: Mapping[str, object],
    candidate_id: str,
) -> dict[str, object]:
    for rollup in cross_asset.get("candidate_rollups", []):
        if isinstance(rollup, Mapping) and rollup.get("candidate_id") == candidate_id:
            return {
                "symbols_with_valid_metrics": list(
                    rollup.get("symbols_with_valid_metrics", [])
                ),
                "oos_passed_symbols": list(rollup.get("oos_passed_symbols", [])),
                "oos_failed_symbols": list(rollup.get("oos_failed_symbols", [])),
                "cost_survived_symbols": list(rollup.get("cost_survived_symbols", [])),
                "cost_broken_symbols": list(rollup.get("cost_broken_symbols", [])),
                "paper_candidate_allowed": False,
                "paper_candidate_blockers": list(
                    rollup.get("paper_candidate_blockers", [])
                ),
            }
    return {}


def _preview_reasons(preview_results: Sequence[Mapping[str, object]]) -> list[str]:
    reasons: list[str] = []
    for result in preview_results:
        for reason in result.get("promotion_reasons", []):
            if isinstance(reason, str):
                reasons.append(reason)
    if not reasons:
        reasons.append("promotion_classification=preview_only")
    return list(dict.fromkeys(reasons))


def _operator_takeaway(
    classification: str,
    flags: Mapping[str, object],
    reasons: Sequence[str],
) -> str:
    active_flags = [name for name, value in flags.items() if value is True]
    if classification == "offline_shadow_candidate":
        return (
            "Offline shadow candidate only; strict offline OOS and cost checks passed, "
            "with no paper promotion authority."
        )
    if classification == "reject_preview":
        detail = ", ".join(reasons or active_flags)
        return f"Reject preview-only evidence before paper reconsideration: {detail}."
    detail = ", ".join(active_flags) if active_flags else "strict shadow criteria not met"
    return f"Keep researching offline; evidence remains preview-only because {detail}."


def _overall_recommendation(
    candidate_reviews: Sequence[Mapping[str, object]],
) -> str:
    classifications = {
        str(review.get("final_review_classification"))
        for review in candidate_reviews
    }
    if "offline_shadow_candidate" in classifications:
        return "promote_to_offline_shadow_candidate"
    if "keep_researching" in classifications:
        return "keep_researching_selected"
    return "reject_all_preview_only"


def _anti_overfit_flags_artifact(value: object) -> dict[str, object]:
    reviews = _review_list(value)
    flag_counts: dict[str, int] = {
        "concentrated_edge_flag": 0,
        "single_symbol_edge_flag": 0,
        "window_instability_flag": 0,
        "high_churn_flag": 0,
        "cost_fragility_flag": 0,
        "baseline_similarity_flag": 0,
        "severe_return_degradation_flag": 0,
    }
    candidates: list[dict[str, object]] = []
    for review in reviews:
        flags = dict(_mapping_or_empty(review.get("anti_overfit_flags")))
        for flag_name, enabled in flags.items():
            if enabled is True:
                flag_counts[flag_name] = flag_counts.get(flag_name, 0) + 1
        candidates.append(
            {
                "candidate_id": review.get("candidate_id"),
                "preview_symbols": list(review.get("preview_symbols", [])),
                "anti_overfit_flags": flags,
                "final_review_classification": review.get(
                    "final_review_classification"
                ),
            }
        )
    return {
        "record_type": "preview_candidate_anti_overfit_flags",
        "schema_version": _SCHEMA_VERSION,
        "review_id": _REVIEW_ID,
        "labels": list(PREVIEW_CANDIDATE_REVIEW_LABELS),
        "flag_counts": flag_counts,
        "candidates": candidates,
        "safety": _safety_payload(),
    }


def _offline_shadow_candidates_artifact(
    payload: Mapping[str, object],
) -> dict[str, object]:
    candidates = [
        _offline_shadow_candidate_record(review)
        for review in _review_list(payload.get("candidate_reviews", []))
        if review.get("final_review_classification") == "offline_shadow_candidate"
    ]
    return {
        "record_type": "offline_shadow_candidates",
        "schema_version": _SCHEMA_VERSION,
        "review_id": _REVIEW_ID,
        "labels": list(PREVIEW_CANDIDATE_REVIEW_LABELS),
        "overall_recommendation": payload.get("overall_recommendation"),
        "paper_candidate_count": 0,
        "candidates": candidates,
        "safety": _safety_payload(),
    }


def _offline_shadow_candidate_record(
    review: Mapping[str, object],
) -> dict[str, object]:
    return {
        "candidate_id": review.get("candidate_id"),
        "symbols_evaluated": list(review.get("symbols_evaluated", [])),
        "preview_symbols": list(review.get("preview_symbols", [])),
        "final_review_classification": review.get("final_review_classification"),
        "operator_takeaway": review.get("operator_takeaway"),
        "safety_labels": list(PREVIEW_CANDIDATE_REVIEW_LABELS),
    }


def _manifest_payload(
    payload: Mapping[str, object],
    output_root: Path,
    artifact_paths: Sequence[Path],
) -> dict[str, object]:
    artifacts = tuple(_artifact_record(output_root, path) for path in artifact_paths)
    return {
        "record_type": "preview_candidate_review_manifest",
        "schema_version": _SCHEMA_VERSION,
        "review_id": _REVIEW_ID,
        "labels": list(PREVIEW_CANDIDATE_REVIEW_LABELS),
        "output_root": str(output_root),
        "source_artifact_root": payload.get("source_artifact_root"),
        "source_run_id": payload.get("source_run_id"),
        "artifact_count": len(artifacts),
        "artifacts": list(artifacts),
        "preview_result_count": payload.get("preview_result_count"),
        "preview_candidate_count": payload.get("preview_candidate_count"),
        "overall_recommendation": payload.get("overall_recommendation"),
        "paper_candidate_count": 0,
        "safety": _safety_payload(),
        "profit_claim": "none",
    }


def _artifact_record(output_root: Path, path: Path) -> dict[str, object]:
    return {
        "name": path.name,
        "path": str(path),
        "path_relative_to_output_root": path.relative_to(output_root).as_posix(),
        "sha256": _file_sha256(path),
        "byte_size": path.stat().st_size,
    }


def _normalize_cross_asset_validation(
    artifact: Mapping[str, object],
    challenger_results: Mapping[str, object],
) -> Mapping[str, object]:
    if isinstance(artifact.get("cross_asset_validation"), Mapping):
        return _mapping_or_empty(artifact.get("cross_asset_validation"))
    if artifact:
        return artifact
    return _mapping_or_empty(challenger_results.get("cross_asset_validation"))


def _result_list(payload: Mapping[str, object]) -> list[dict[str, object]]:
    raw_results = payload.get("results")
    if not isinstance(raw_results, list):
        raise ValidationError("challenger_results results must be a list.")
    return [dict(item) for item in raw_results if isinstance(item, Mapping)]


def _review_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _window_result_summary(value: object) -> list[dict[str, object]]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return []
    summaries = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        summaries.append(
            {
                "window_id": item.get("window_id"),
                "passed": item.get("passed") is True,
                "failed": item.get("failed") is True,
                "total_return_delta": item.get("total_return_delta"),
                "max_drawdown_delta": item.get("max_drawdown_delta"),
                "sharpe_ratio_delta": item.get("sharpe_ratio_delta"),
            }
        )
    return summaries


def _oos_window_return_deltas(
    result: Mapping[str, object],
) -> tuple[Decimal, ...]:
    validation = _mapping_or_empty(result.get("out_of_sample_validation"))
    deltas: list[Decimal] = []
    for window in validation.get("window_results", []):
        if not isinstance(window, Mapping):
            continue
        delta = _optional_decimal(window.get("total_return_delta"))
        if delta is not None:
            deltas.append(delta)
    return tuple(deltas)


def _positive_oos_window_edges(
    result: Mapping[str, object],
) -> tuple[tuple[str, Decimal], ...]:
    validation = _mapping_or_empty(result.get("out_of_sample_validation"))
    edges: list[tuple[str, Decimal]] = []
    for window in validation.get("window_results", []):
        if not isinstance(window, Mapping):
            continue
        delta = _optional_decimal(window.get("total_return_delta"))
        if delta is not None and delta > Decimal("0"):
            edges.append((str(window.get("window_id")), delta))
    return tuple(edges)


def _strongest_edge_share(values: Mapping[str, Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    total = sum(values.values(), Decimal("0"))
    if total <= Decimal("0"):
        return Decimal("0")
    return max(values.values()) / total


def _is_high_churn(
    transition_count: int,
    baseline_transition_count: int,
) -> bool:
    if transition_count >= 100:
        return True
    if baseline_transition_count <= 0:
        return transition_count >= 80
    return transition_count >= max(80, baseline_transition_count * 2)


def _sorted_symbols(values: Iterable[object]) -> list[str]:
    return sorted({str(value) for value in values if value is not None})


def _abs_or_large(value: Decimal | None) -> Decimal:
    if value is None:
        return Decimal("999")
    return abs(value)


def _read_required_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ValidationError(f"required artifact is missing: {path}")
    return _read_json(path)


def _read_optional_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    return _read_json(path)


def _read_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValidationError(f"artifact could not be read: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"artifact is not valid JSON: {path}") from exc
    if not isinstance(payload, Mapping):
        raise ValidationError(f"artifact must contain a JSON object: {path}")
    return dict(payload)


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(_HASH_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _json_dumps(payload: Mapping[str, object]) -> str:
    return json.dumps(
        _json_safe(payload),
        sort_keys=True,
        separators=(",", ":"),
    )


def _json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_safe(item) for item in value]
    return value


def _safety_payload() -> dict[str, object]:
    return {
        "research_only": True,
        "offline_only": True,
        "not_live_authorized": True,
        "no_paper_promotion": True,
        "profit_claim": "none",
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "broker_access_attempted": False,
        "broker_mutation_performed": False,
        "paper_submit_performed": False,
        "live_mutation_performed": False,
    }


def _assert_no_paper_candidate_classification(payload: Mapping[str, object]) -> None:
    if payload.get("paper_candidate_count") not in {0, None}:
        raise ValidationError("v2.15 preview review cannot contain paper candidates.")
    for review in _review_list(payload.get("candidate_reviews", [])):
        validate_preview_review_classification(
            str(review.get("final_review_classification"))
        )


def _optional_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not decimal_value.is_finite():
        return None
    return decimal_value


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _decimal_text_or_none(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _decimal_text(value)


def _int_or_zero(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def _mapping_required(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping.")
    return value


def _mapping_or_empty(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return {}


def _config(value: PreviewCandidateReviewConfig) -> PreviewCandidateReviewConfig:
    if not isinstance(value, PreviewCandidateReviewConfig):
        raise ValidationError("config must be a PreviewCandidateReviewConfig.")
    return value


def _path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str):
        checked = _required_string(value, field_name)
        if "://" in checked:
            raise ValidationError(f"{field_name} must be a local path.")
        path = Path(checked)
    else:
        raise ValidationError(f"{field_name} must be a path.")
    return path


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a non-empty string.")
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return normalized


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="preview-candidate-review")
    parser.add_argument(
        "--input-root",
        default=str(_DEFAULT_INPUT_ROOT),
        help="Directory containing strategy challenger artifacts.",
    )
    parser.add_argument(
        "--output-root",
        default=str(_DEFAULT_OUTPUT_ROOT),
        help="Directory for preview review artifacts.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = PreviewCandidateReviewConfig(
        input_root=args.input_root,
        output_root=args.output_root,
    )
    payload = run_preview_candidate_review(config)
    print("preview_candidate_review_status=completed")
    print(f"input_root={config.input_root}")
    print(f"output_root={config.output_root}")
    print(f"preview_result_count={payload.get('preview_result_count')}")
    print(f"preview_candidate_count={payload.get('preview_candidate_count')}")
    print(f"overall_recommendation={payload.get('overall_recommendation')}")
    print(
        "offline_shadow_candidate_count="
        f"{len(payload.get('offline_shadow_candidates', []))}"
    )
    print("broker_access_performed=false")
    print("broker_mutation_performed=false")
    print("paper_submit_performed=false")
    print("live_mutation_performed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
