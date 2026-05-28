"""Synthetic research MVP operating brief report renderer."""

from __future__ import annotations

import json

from algotrader.errors import ValidationError
from algotrader.research.advisory_operating_brief_package import (
    AdvisoryOperatingBriefPackage,
)
from algotrader.research.advisory_operating_brief_package_synthetic import (
    build_synthetic_advisory_operating_brief_package_preview,
)

__all__ = [
    "build_synthetic_advisory_operating_brief_mvp_report_payload",
    "render_advisory_operating_brief_mvp_report_json",
    "render_advisory_operating_brief_mvp_report_text",
    "render_synthetic_advisory_operating_brief_mvp_report",
]

_LINE_BREAK = chr(10)
_REPORT_TYPE = "synthetic_research_mvp_operating_brief"
_REPORT_TITLE = "Synthetic Research MVP Operating Brief"
_REPORT_SCOPE = "synthetic_only_advisory_only"
_REAL_SOURCE_STATUS = "No real data source is approved."
_MVP_DESCRIPTION = (
    "Deterministic terminal brief over the synthetic advisory package, "
    "content bundle, advisory sections, diagnostics, readiness records, "
    "research observations, and backtest readiness gates."
)
_PREVIEW_FORMATS = ("text", "json")
_IMPORTANT_NON_CLAIMS = (
    "not strategy validation",
    "not backtesting validation",
    "not paper readiness",
    "not live readiness",
    "not a recommendation",
    "not ranking",
    "not scoring",
    "not order authority",
    "not broker access",
    "not portfolio mutation",
    "not capital authority",
    "not trading authority",
)


def build_synthetic_advisory_operating_brief_mvp_report_payload() -> (
    dict[str, object]
):
    """Return a deterministic concise report payload for the synthetic package."""

    package = build_synthetic_advisory_operating_brief_package_preview()
    payload = _primitive_json_copy(_build_report_payload(package))
    return _dict(payload, "mvp_report_payload")


def render_synthetic_advisory_operating_brief_mvp_report(
    output_format: str = "text",
) -> str:
    """Return the synthetic MVP operating brief in a stable output format."""

    payload = build_synthetic_advisory_operating_brief_mvp_report_payload()
    if output_format == "text":
        return render_advisory_operating_brief_mvp_report_text(payload)
    if output_format == "json":
        return render_advisory_operating_brief_mvp_report_json(payload)

    expected = ", ".join(_PREVIEW_FORMATS)
    raise ValueError(
        "unsupported advisory operating brief MVP preview format: "
        f"{output_format!r}. Expected one of: {expected}."
    )


def render_advisory_operating_brief_mvp_report_json(
    payload: dict[str, object],
) -> str:
    """Return compact deterministic JSON for the concise report payload."""

    _report_payload(payload)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def render_advisory_operating_brief_mvp_report_text(
    payload: dict[str, object],
) -> str:
    """Return stable human-readable text for the concise report payload."""

    report = _report_payload(payload)
    view = _dict(report["advisory_view_summary"], "advisory_view_summary")
    sections = _list(report["sections_present"], "sections_present")
    issues = _list(report["diagnostic_issues"], "diagnostic_issues")
    readiness = _dict(report["data_source_readiness"], "data_source_readiness")
    observations = _dict(report["research_observations"], "research_observations")
    work_queue = _list(report["work_queue"], "work_queue")
    backtest_gate = _list(report["backtest_readiness_gate"], "backtest_readiness_gate")
    blocked = _dict(
        report["blocked_missing_before_real_use"],
        "blocked_missing_before_real_use",
    )
    safety = _list(report["safety"], "safety")

    lines: list[str] = [
        _string(report["title"], "title"),
        f"report_type: {_string(report['report_type'], 'report_type')}",
        f"scope: {_string(report['scope'], 'scope')}",
        f"real_source_status: {_string(report['real_source_status'], 'real_source_status')}",
        f"description: {_string(report['description'], 'description')}",
        "",
        "Advisory View Summary",
        f"- package_id: {_string(view['package_id'], 'package_id')}",
        f"- package_title: {_string(view['package_title'], 'package_title')}",
        f"- package_summary: {_string(view['package_summary'], 'package_summary')}",
        f"- bundle_title: {_string(view['bundle_title'], 'bundle_title')}",
        f"- bundle_summary: {_string(view['bundle_summary'], 'bundle_summary')}",
        f"- status: {_string(view['status'], 'status')}",
        f"- authority: {_string(view['authority'], 'authority')}",
        f"- capital_authority: {_format_value(view['capital_authority'])}",
        f"- view_key: {_string(view['view_key'], 'view_key')}",
        f"- view_title: {_string(view['view_title'], 'view_title')}",
        f"- view_state: {_string(view['view_state'], 'view_state')}",
        f"- section_count: {_format_value(view['section_count'])}",
        f"- represents: {_string(view['represents'], 'represents')}",
        "",
        "Sections Present",
    ]
    for index, section in enumerate(sections, start=1):
        item = _dict(section, f"sections_present[{index}]")
        lines.append(
            f"{index}. {_string(item['section_key'], 'section_key')} | "
            f"{_string(item['section_title'], 'section_title')} | "
            f"status={_string(item['section_state'], 'section_state')} | "
            f"items={_format_value(item['item_count'])}"
        )
        diagnostic_messages = _list(
            item["diagnostic_messages"],
            "diagnostic_messages",
        )
        if diagnostic_messages:
            lines.append(
                f"   diagnostics: {_join_values(diagnostic_messages)}"
            )

    lines.extend(("", "Diagnostic Issues"))
    for index, issue in enumerate(issues, start=1):
        item = _dict(issue, f"diagnostic_issues[{index}]")
        lines.append(
            f"{index}. source={_string(item['source_branch'], 'source_branch')} | "
            f"category={_string(item['category'], 'category')} | "
            f"status={_string(item['status'], 'status')} | "
            f"severity={_string(item['severity'], 'severity')}"
        )
        lines.append(f"   message: {_string(item['message'], 'message')}")
        lines.append(
            f"   blocks: {_join_values(_list(item['blocks'], 'blocks'))}"
        )
        lines.append(
            f"   indicates: {_string(item['indicates'], 'indicates')}"
        )

    lines.extend(("", "Data-Source Readiness Problems"))
    readiness_items = _list(readiness["items"], "readiness.items")
    readiness_summaries = _list(readiness["summaries"], "readiness.summaries")
    lines.append(f"- state: {_string(readiness['state'], 'readiness.state')}")
    lines.append(
        f"- summary_state: {_string(readiness['summary_state'], 'readiness.summary_state')}"
    )
    lines.append(
        f"- missing_control_count: {_format_value(readiness['missing_control_count'])}"
    )
    lines.append(
        f"- statement: {_string(readiness['real_source_statement'], 'real_source_statement')}"
    )
    for index, item in enumerate(readiness_items, start=1):
        readiness_item = _dict(item, f"readiness_items[{index}]")
        lines.append(
            f"- readiness {index}: "
            f"{_string(readiness_item['source_name'], 'source_name')} "
            f"({_string(readiness_item['source_id'], 'source_id')}); "
            f"intended_use={_string(readiness_item['intended_use'], 'intended_use')}"
        )
        lines.append(
            f"  required_controls: {_join_values(_list(readiness_item['required_controls'], 'required_controls'))}"
        )
        lines.append(
            f"  satisfied_controls: {_join_values(_list(readiness_item['satisfied_controls'], 'satisfied_controls'))}"
        )
        lines.append(
            f"  missing_controls: {_join_values(_list(readiness_item['missing_controls'], 'missing_controls'))}"
        )
    for index, summary in enumerate(readiness_summaries, start=1):
        summary_item = _dict(summary, f"readiness_summaries[{index}]")
        lines.append(
            f"- readiness summary {index}: required={_format_value(summary_item['required_control_count'])}; "
            f"satisfied={_format_value(summary_item['satisfied_control_count'])}; "
            f"missing={_format_value(summary_item['missing_control_count'])}"
        )

    lines.extend(("", "Research Observations"))
    _append_observation_group(
        lines,
        "SMA observations",
        _list(observations["sma_observations"], "sma_observations"),
        (
            "symbol",
            "as_of",
            "window",
            "position_vs_sma",
            "latest_close",
            "sma_value",
            "distance_from_sma",
        ),
    )
    _append_observation_group(
        lines,
        "SMA summary observations",
        _list(observations["sma_summary_observations"], "sma_summary_observations"),
        (
            "summary_state",
            "total_observation_count",
            "above_sma_count",
            "below_sma_count",
            "equal_sma_count",
            "insufficient_history_count",
        ),
    )
    _append_observation_group(
        lines,
        "Return observations",
        _list(observations["return_observations"], "return_observations"),
        (
            "symbol",
            "as_of",
            "return_method",
            "price_basis",
            "return_count",
            "positive_return_count",
            "negative_return_count",
            "zero_return_count",
        ),
    )
    _append_observation_group(
        lines,
        "Return summary observations",
        _list(
            observations["return_summary_observations"],
            "return_summary_observations",
        ),
        (
            "symbol",
            "summary_state",
            "source_return_count",
            "min_simple_return",
            "max_simple_return",
            "mean_simple_return",
        ),
    )
    _append_observation_group(
        lines,
        "SMA-return pipeline observation",
        _list(
            observations["sma_return_pipeline_observations"],
            "sma_return_pipeline_observations",
        ),
        (
            "pipeline_state",
            "symbol",
            "as_of",
            "pipeline_component_count",
            "alignment_period_count",
            "selection_period_count",
            "included_period_count",
            "excluded_period_count",
            "selected_source_return_count",
        ),
    )
    _append_observation_group(
        lines,
        "Data-source readiness observations",
        _list(
            observations["data_source_readiness_observations"],
            "data_source_readiness_observations",
        ),
        (
            "source_id",
            "readiness_state",
            "missing_control_count",
            "real_source_status",
        ),
    )
    _append_observation_group(
        lines,
        "Research observation manifest",
        _list(observations["research_observation_manifest"], "manifest"),
        (
            "observation_name",
            "observation_type",
            "payload_key_count",
        ),
    )
    lines.append(
        "- observation_language: observed synthetic mechanics only; no strategy "
        "approval, ranking, scoring, recommendation, or trade authority."
    )

    lines.extend(("", "Work Queue / Next Non-Trading Work Items"))
    for index, work_item in enumerate(work_queue, start=1):
        item = _dict(work_item, f"work_queue[{index}]")
        lines.append(
            f"{index}. label={_string(item['label'], 'label')} | "
            f"state={_string(item['state'], 'state')} | "
            f"boundary={_string(item['boundary'], 'boundary')}"
        )
        lines.append(f"   reason: {_string(item['reason'], 'reason')}")

    lines.extend(("", "Backtest Readiness Gate"))
    lines.append("- gate_state: blocked_not_ready")
    lines.append(
        "- statement: real strategy backtesting is blocked or not ready; this "
        "section reports project controls and does not run a backtest."
    )
    for index, gate_record in enumerate(backtest_gate, start=1):
        item = _dict(gate_record, f"backtest_readiness_gate[{index}]")
        lines.append(
            f"{index}. label={_string(item['label'], 'label')} | "
            f"state={_string(item['state'], 'state')} | "
            f"boundary={_string(item['boundary'], 'boundary')}"
        )
        lines.append(f"   reason: {_string(item['reason'], 'reason')}")
        lines.append(
            f"   required_control: {_string(item['required_control'], 'required_control')}"
        )

    lines.extend(("", "Blocked / Missing Before Real Strategy, Backtest, Or Trading Use"))
    lines.append("- blocked_items:")
    _append_values(lines, _list(blocked["blocked_items"], "blocked_items"), indent="  ")
    lines.append("- missing_items:")
    _append_values(lines, _list(blocked["missing_items"], "missing_items"), indent="  ")
    lines.append("- required_next_steps:")
    _append_values(
        lines,
        _list(blocked["required_next_steps"], "required_next_steps"),
        indent="  ",
    )
    lines.append("- explicit_non_authority:")
    _append_values(
        lines,
        _list(blocked["explicit_non_authority"], "explicit_non_authority"),
        indent="  ",
    )

    lines.extend(("", "Safety"))
    _append_values(lines, safety)

    return _LINE_BREAK.join(lines)


def _build_report_payload(package: AdvisoryOperatingBriefPackage) -> dict[str, object]:
    if type(package) is not AdvisoryOperatingBriefPackage:
        raise ValidationError(
            "package must be exactly an AdvisoryOperatingBriefPackage."
        )

    package_payload = package.to_dict()
    bundle = _dict(package_payload["content_bundle"], "content_bundle")
    view = _dict(bundle.get("advisory_view", {}), "advisory_view")
    sections = [_section_row(item) for item in _list_value(bundle, "advisory_sections")]
    issues = [_diagnostic_issue_row(item) for item in _list_value(bundle, "diagnostic_issues")]
    readiness_items = [
        _readiness_row(item)
        for item in _list_value(bundle, "research_data_source_readiness")
    ]
    readiness_summaries = [
        _readiness_summary_row(item)
        for item in _list_value(bundle, "research_data_source_readiness_summaries")
    ]
    missing_controls = _dedupe_first_seen(
        tuple(
            control
            for item in readiness_items
            for control in _string_list(item["missing_controls"])
        )
    )
    blocked_items = _dedupe_first_seen(
        (
            *_collect_string_lists(bundle, "blockers"),
            *missing_controls,
        )
    )
    missing_items = _dedupe_first_seen(
        (
            *_collect_string_lists(bundle, "evidence_gaps"),
            *missing_controls,
        )
    )
    required_next_steps = _dedupe_first_seen(
        _collect_string_lists(bundle, "required_next_steps")
    )
    non_claims = _dedupe_first_seen(
        (
            *_string_list(package_payload["non_claims"]),
            *_collect_string_lists(package_payload, "non_claims"),
        )
    )
    data_source_readiness = {
        "state": _readiness_state(readiness_items),
        "summary_state": _summary_state(readiness_summaries),
        "missing_control_count": len(missing_controls),
        "real_source_statement": (
            "No real data source is approved; the readiness records are "
            "synthetic candidate-only diagnostics."
        ),
        "items": readiness_items,
        "summaries": readiness_summaries,
    }
    research_observations = {
        "sma_observations": _sma_observation_rows(bundle),
        "sma_summary_observations": _sma_summary_rows(bundle),
        "return_observations": _return_observation_rows(bundle),
        "return_summary_observations": _return_summary_rows(bundle),
        "sma_return_pipeline_observations": _pipeline_rows(package_payload),
        "data_source_readiness_observations": [
            {
                "source_id": item["source_id"],
                "readiness_state": item["readiness_state"],
                "missing_control_count": len(
                    _string_list(item["missing_controls"])
                ),
                "real_source_status": _REAL_SOURCE_STATUS,
            }
            for item in readiness_items
        ],
        "research_observation_manifest": _manifest_rows(package_payload),
    }
    blocked_missing = {
        "blocked_items": blocked_items,
        "missing_items": missing_items,
        "required_next_steps": required_next_steps,
        "explicit_non_authority": tuple(
            claim for claim in _IMPORTANT_NON_CLAIMS if claim in non_claims
        ),
    }

    return {
        "report_type": _REPORT_TYPE,
        "title": _REPORT_TITLE,
        "scope": _REPORT_SCOPE,
        "real_source_status": _REAL_SOURCE_STATUS,
        "description": _MVP_DESCRIPTION,
        "advisory_view_summary": {
            "package_id": package_payload["package_id"],
            "package_title": package_payload["title"],
            "package_summary": package_payload["summary"],
            "synthetic_as_of": package_payload["as_of"],
            "bundle_title": bundle["title"],
            "bundle_summary": bundle["summary"],
            "status": package_payload["status"],
            "authority": package_payload["authority"],
            "capital_authority": package_payload["capital_authority"],
            "view_key": view.get("view_key", "not_present"),
            "view_title": view.get("view_title", "not_present"),
            "view_state": view.get("view_state", "not_present"),
            "section_count": view.get("section_count", len(sections)),
            "represents": (
                "Metadata-only view over synthetic advisory sections, "
                "diagnostic issues, data-source readiness, and research "
                "observation surfaces."
            ),
        },
        "sections_present": sections,
        "diagnostic_issues": issues,
        "data_source_readiness": data_source_readiness,
        "research_observations": research_observations,
        "work_queue": _work_queue_rows(
            readiness_items=readiness_items,
            diagnostic_issues=issues,
            research_observations=research_observations,
            blocked_missing=blocked_missing,
            capital_authority=package_payload["capital_authority"],
        ),
        "backtest_readiness_gate": _backtest_readiness_gate_rows(),
        "blocked_missing_before_real_use": blocked_missing,
        "safety": (
            "synthetic-only package preview; no real data ingestion is performed",
            "advisory-only and capital_authority is False",
            "no broker, network, credential, live, or vendor runtime behavior is used",
            "no orders, fills, portfolio, reconciliation, or persistence mutation is performed",
            "no ranking, scoring, recommendation, approval, or trading authority is represented",
        ),
    }


def _backtest_readiness_gate_rows() -> tuple[dict[str, str], ...]:
    return (
        _backtest_gate_item(
            label="Real data source approval",
            state="blocked",
            reason="No real data source is approved for this candidate strategy path.",
            required_control="approved and pinned data source with provenance",
            boundary="data_source",
        ),
        _backtest_gate_item(
            label="Source, universe, benchmark, and cash controls",
            state="missing",
            reason=(
                "Source, universe, benchmark, and cash proxy controls are not "
                "accepted for deterministic use."
            ),
            required_control="deterministic source, universe, benchmark, and cash policy",
            boundary="research_controls",
        ),
        _backtest_gate_item(
            label="No-lookahead protocol",
            state="missing",
            reason=(
                "As-of and clock contracts are not yet applied to this "
                "candidate backtest path."
            ),
            required_control="explicit no-lookahead validation protocol",
            boundary="no_lookahead",
        ),
        _backtest_gate_item(
            label="Return construction policy",
            state="advisory_only",
            reason=(
                "Synthetic return observations exist, but they are not a "
                "complete strategy return engine."
            ),
            required_control=(
                "deterministic return construction policy promoted into the "
                "accepted path"
            ),
            boundary="return_construction",
        ),
        _backtest_gate_item(
            label="Validation and reproduction evidence",
            state="missing",
            reason=(
                "No real-data reproduction, robustness, OOS or walk-forward, "
                "cost, or liquidity validation exists."
            ),
            required_control="deterministic validation evidence package",
            boundary="validation",
        ),
        _backtest_gate_item(
            label="Strategy approval",
            state="blocked",
            reason="Advisory observations do not authorize any strategy.",
            required_control=(
                "strategy mandate and validation scorecard accepted through a "
                "future control process"
            ),
            boundary="strategy_approval",
        ),
        _backtest_gate_item(
            label="Trading authority",
            state="blocked",
            reason=(
                "No backtest gate may create paper, live, order, or capital "
                "authority."
            ),
            required_control="future explicitly scoped capital-layer authorization",
            boundary="trading_authority",
        ),
    )


def _backtest_gate_item(
    *,
    label: str,
    state: str,
    reason: str,
    required_control: str,
    boundary: str,
) -> dict[str, str]:
    return {
        "label": label,
        "state": state,
        "reason": reason,
        "required_control": required_control,
        "boundary": boundary,
    }


def _work_queue_rows(
    *,
    readiness_items: list[dict[str, object]],
    diagnostic_issues: list[dict[str, object]],
    research_observations: dict[str, object],
    blocked_missing: dict[str, object],
    capital_authority: object,
) -> tuple[dict[str, str], ...]:
    blocked_items = _string_list(blocked_missing["blocked_items"])
    missing_items = _string_list(blocked_missing["missing_items"])
    required_next_steps = _string_list(blocked_missing["required_next_steps"])
    explicit_non_authority = _string_list(blocked_missing["explicit_non_authority"])
    missing_controls = _dedupe_first_seen(
        tuple(
            control
            for item in readiness_items
            for control in _string_list(item["missing_controls"])
        )
    )
    source_ids = _dedupe_first_seen(
        tuple(_string(item["source_id"], "source_id") for item in readiness_items)
    )
    rows: list[dict[str, str]] = []

    if missing_controls:
        rows.append(
            _work_item(
                label="Data-source readiness gaps",
                reason=(
                    "Candidate source controls are missing before real source "
                    f"use for {_join_values(source_ids)}: "
                    f"{_join_values(missing_controls)}."
                ),
                state="missing",
                boundary="data_source",
            )
        )

    if _contains_any(blocked_items, ("source data clearance",)):
        rows.append(
            _work_item(
                label="Real data source approval",
                reason=(
                    "No real data source is approved; source data clearance is "
                    "unresolved before real data use."
                ),
                state="blocked",
                boundary="data_source",
            )
        )

    source_control_terms = _matching_items(
        (*blocked_items, *missing_items),
        (
            "source data clearance",
            "ETF universe",
            "benchmark and cash",
            "cash handling",
        ),
    )
    if source_control_terms:
        rows.append(
            _work_item(
                label="Source, universe, benchmark, and cash controls",
                reason=(
                    "Existing blocked/missing surfaces list unresolved project "
                    f"controls: {_join_values(source_control_terms)}."
                ),
                state="missing",
                boundary="validation",
            )
        )

    no_lookahead_terms = _matching_items(
        (*blocked_items, *required_next_steps),
        ("no-lookahead", "no_lookahead"),
    )
    if no_lookahead_terms:
        rows.append(
            _work_item(
                label="No-lookahead protocol implementation",
                reason=(
                    "Existing surfaces still require deterministic no-lookahead "
                    f"implementation evidence: {_join_values(no_lookahead_terms)}."
                ),
                state="blocked",
                boundary="no_lookahead",
            )
        )

    backtest_terms = _matching_items(
        (*explicit_non_authority, *blocked_items, *missing_items),
        (
            "not backtesting validation",
            "validation review",
            "cost and slippage",
            "out-of-sample robustness",
        ),
    )
    if backtest_terms:
        rows.append(
            _work_item(
                label="Deterministic backtest readiness evidence",
                reason=(
                    "Missing before real backtest use because the existing "
                    f"surfaces list: {_join_values(backtest_terms)}."
                ),
                state="insufficient",
                boundary="validation",
            )
        )

    validation_terms = _matching_items(
        (*blocked_items, *missing_items),
        ("validation evidence", "reproduction", "robustness evidence"),
    )
    if validation_terms:
        rows.append(
            _work_item(
                label="Validation and reproduction evidence",
                reason=(
                    "Blocks strategy validation until the missing evidence is "
                    f"recorded: {_join_values(validation_terms)}."
                ),
                state="missing",
                boundary="validation",
            )
        )

    if diagnostic_issues:
        issue_categories = _dedupe_first_seen(
            tuple(_string(issue["category"], "category") for issue in diagnostic_issues)
        )
        blocking_controls = _dedupe_first_seen(
            tuple(
                control
                for issue in diagnostic_issues
                for control in _string_list(issue["blocks"])
            )
        )
        rows.append(
            _work_item(
                label="Diagnostic blockers",
                reason=(
                    "Diagnostic issues remain represented in the synthetic "
                    f"package: {_join_values(issue_categories)}; blocks: "
                    f"{_join_values(blocking_controls)}."
                ),
                state="blocked",
                boundary="data_source",
            )
        )

    observation_counts = _observation_counts(research_observations)
    if observation_counts:
        rows.append(
            _work_item(
                label="Advisory-only research observations",
                reason=(
                    "Research observations are available but advisory-only and "
                    "not sufficient for strategy approval: "
                    f"{_join_values(observation_counts)}."
                ),
                state="advisory_only",
                boundary="strategy_approval",
            )
        )

    strategy_terms = _matching_items(
        explicit_non_authority,
        ("not strategy validation", "not ranking", "not scoring", "not a recommendation"),
    )
    if strategy_terms:
        rows.append(
            _work_item(
                label="Strategy validation controls",
                reason=(
                    "Requires deterministic validation controls before any "
                    f"strategy approval claim: {_join_values(strategy_terms)}."
                ),
                state="blocked",
                boundary="strategy_approval",
            )
        )

    authority_terms = _matching_items(
        explicit_non_authority,
        ("not order authority", "not capital authority", "not trading authority"),
    )
    if authority_terms or capital_authority is False:
        rows.append(
            _work_item(
                label="Trading authority remains absent",
                reason=(
                    "No trading authority; explicit non-authority remains in "
                    f"effect: {_join_values(authority_terms)}; "
                    f"capital_authority={_format_value(capital_authority)}."
                ),
                state="blocked",
                boundary="trading_authority",
            )
        )

    return tuple(rows)


def _work_item(
    *,
    label: str,
    reason: str,
    state: str,
    boundary: str,
) -> dict[str, str]:
    return {
        "label": label,
        "reason": reason,
        "state": state,
        "boundary": boundary,
    }


def _matching_items(values: tuple[str, ...], needles: tuple[str, ...]) -> tuple[str, ...]:
    return _dedupe_first_seen(
        tuple(value for value in values if _contains_any((value,), needles))
    )


def _contains_any(values: tuple[str, ...], needles: tuple[str, ...]) -> bool:
    return any(
        needle.lower() in value.lower()
        for value in values
        for needle in needles
    )


def _observation_counts(
    research_observations: dict[str, object],
) -> tuple[str, ...]:
    rows: list[str] = []
    for key in (
        "sma_observations",
        "sma_summary_observations",
        "return_observations",
        "return_summary_observations",
        "sma_return_pipeline_observations",
        "data_source_readiness_observations",
        "research_observation_manifest",
    ):
        count = len(_list(research_observations[key], key))
        if count:
            rows.append(f"{key}={count}")
    return tuple(rows)


def _section_row(payload: object) -> dict[str, object]:
    section = _dict(payload, "section")
    return {
        "section_key": section["section_key"],
        "section_title": section["section_title"],
        "section_state": section["section_state"],
        "item_count": section["item_count"],
        "diagnostic_messages": list(_string_list(section["diagnostic_messages"])),
    }


def _diagnostic_issue_row(payload: object) -> dict[str, object]:
    issue = _dict(payload, "diagnostic_issue")
    return {
        "source_branch": issue["source_branch"],
        "category": issue["issue_code"],
        "status": issue["issue_state"],
        "severity": "blocking_control_gap",
        "message": issue["diagnostic_message"],
        "blocks": list(_string_list(issue["blocking_controls"])),
        "indicates": "missing diagnostic controls prevent real data-source use",
    }


def _readiness_row(payload: object) -> dict[str, object]:
    readiness = _dict(payload, "readiness")
    return {
        "source_id": readiness["source_id"],
        "source_name": readiness["source_name"],
        "intended_use": readiness["intended_use"],
        "readiness_state": readiness["readiness_state"],
        "required_controls": list(_string_list(readiness["required_controls"])),
        "satisfied_controls": list(_string_list(readiness["satisfied_controls"])),
        "missing_controls": list(_string_list(readiness["missing_controls"])),
        "non_claims": list(_string_list(readiness["non_claims"])),
    }


def _readiness_summary_row(payload: object) -> dict[str, object]:
    summary = _dict(payload, "readiness_summary")
    return {
        "summary_state": summary["summary_state"],
        "required_control_count": summary["required_control_count"],
        "satisfied_control_count": summary["satisfied_control_count"],
        "missing_control_count": summary["missing_control_count"],
    }


def _sma_observation_rows(bundle: dict[str, object]) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for brief in _list_value(bundle, "sma_research_observation_briefs"):
        for item in _brief_items(brief):
            source = _dict(item["source_observation"], "source_observation")
            rows.append(
                {
                    "symbol": source["symbol"],
                    "as_of": source["as_of"],
                    "window": source["window"],
                    "position_vs_sma": source["position_vs_sma"],
                    "latest_close": source["latest_close"],
                    "sma_value": source["sma_value"],
                    "distance_from_sma": source["distance_from_sma"],
                    "mechanical_state": item["mechanical_state"],
                }
            )
    return tuple(rows)


def _sma_summary_rows(bundle: dict[str, object]) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "summary_state": summary["summary_state"],
            "total_observation_count": summary["total_observation_count"],
            "above_sma_count": summary["above_sma_count"],
            "below_sma_count": summary["below_sma_count"],
            "equal_sma_count": summary["equal_sma_count"],
            "insufficient_history_count": summary["insufficient_history_count"],
        }
        for summary in (
            _dict(item, "sma_summary")
            for item in _list_value(bundle, "sma_research_summary_observations")
        )
    )


def _return_observation_rows(bundle: dict[str, object]) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for brief in _list_value(bundle, "research_return_observation_briefs"):
        for item in _brief_items(brief):
            source = _dict(item["source_observation"], "source_observation")
            rows.append(
                {
                    "symbol": source["symbol"],
                    "as_of": source["as_of"],
                    "return_method": source["return_method"],
                    "price_basis": source["price_basis"],
                    "return_count": source["return_count"],
                    "positive_return_count": item["positive_return_count"],
                    "negative_return_count": item["negative_return_count"],
                    "zero_return_count": item["zero_return_count"],
                    "mechanical_state": item["mechanical_state"],
                }
            )
    return tuple(rows)


def _return_summary_rows(bundle: dict[str, object]) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for brief in _list_value(bundle, "research_return_summary_observation_briefs"):
        brief_payload = _dict(brief, "research_return_summary_brief")
        for item in _list(brief_payload["summary_observations"], "summary_observations"):
            summary = _dict(item, "summary_observation")
            rows.append(
                {
                    "symbol": summary["symbol"],
                    "summary_state": summary["summary_state"],
                    "source_return_count": summary["source_return_count"],
                    "min_simple_return": summary["min_simple_return"],
                    "max_simple_return": summary["max_simple_return"],
                    "mean_simple_return": summary["mean_simple_return"],
                }
            )
    return tuple(rows)


def _pipeline_rows(package_payload: dict[str, object]) -> tuple[dict[str, object], ...]:
    if "sma_return_research_pipeline_observation" not in package_payload:
        return ()

    observation = _dict(
        package_payload["sma_return_research_pipeline_observation"],
        "sma_return_research_pipeline_observation",
    )
    return (
        {
            "pipeline_state": observation["pipeline_state"],
            "symbol": observation["symbol"],
            "as_of": observation["as_of"],
            "pipeline_component_count": observation["pipeline_component_count"],
            "alignment_period_count": observation["alignment_period_count"],
            "selection_period_count": observation["selection_period_count"],
            "included_period_count": observation["included_period_count"],
            "excluded_period_count": observation["excluded_period_count"],
            "selected_source_return_count": observation[
                "selected_source_return_count"
            ],
            "alignment_rule": observation["alignment_rule"],
            "selection_rule": observation["selection_rule"],
        },
    )


def _manifest_rows(package_payload: dict[str, object]) -> tuple[dict[str, object], ...]:
    if "research_observation_manifest" not in package_payload:
        return ()

    manifest = _dict(
        package_payload["research_observation_manifest"],
        "research_observation_manifest",
    )
    return tuple(
        {
            "observation_name": entry["observation_name"],
            "observation_type": entry["observation_type"],
            "payload_key_count": entry["payload_key_count"],
        }
        for entry in (
            _dict(item, "manifest_entry")
            for item in _list(manifest["entries"], "manifest.entries")
        )
    )


def _brief_items(payload: object) -> tuple[dict[str, object], ...]:
    brief = _dict(payload, "brief")
    items: list[dict[str, object]] = []
    for section in _list(brief["sections"], "brief.sections"):
        section_payload = _dict(section, "brief.section")
        for item in _list(section_payload["items"], "brief.section.items"):
            items.append(_dict(item, "brief.section.item"))
    return tuple(items)


def _readiness_state(items: list[dict[str, object]]) -> str:
    states = _dedupe_first_seen(
        tuple(_string(item["readiness_state"], "readiness_state") for item in items)
    )
    return _join_values(states)


def _summary_state(items: list[dict[str, object]]) -> str:
    states = _dedupe_first_seen(
        tuple(_string(item["summary_state"], "summary_state") for item in items)
    )
    return _join_values(states)


def _collect_string_lists(payload: object, field_name: str) -> tuple[str, ...]:
    values: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == field_name and isinstance(value, list):
                values.extend(_string_list(value))
            else:
                values.extend(_collect_string_lists(value, field_name))
    elif isinstance(payload, list):
        for item in payload:
            values.extend(_collect_string_lists(item, field_name))
    return tuple(values)


def _list_value(payload: dict[str, object], key: str) -> list[object]:
    if key not in payload:
        return []
    return _list(payload[key], key)


def _report_payload(payload: object) -> dict[str, object]:
    report = _dict(payload, "payload")
    if report.get("report_type") != _REPORT_TYPE:
        raise ValidationError(
            "payload must be a synthetic research MVP operating brief report."
        )
    return report


def _dict(value: object, field_name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValidationError(f"{field_name} must be a dictionary.")
    return value


def _list(value: object, field_name: str) -> list[object]:
    if isinstance(value, tuple):
        return list(value)
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list.")
    return value


def _string(value: object, field_name: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field_name} must be a string.")
    return value


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValidationError("value must be a list or tuple of strings.")

    items = tuple(value)
    for item in items:
        if type(item) is not str:
            raise ValidationError("value must contain only strings.")
    return items


def _dedupe_first_seen(values: tuple[str, ...]) -> tuple[str, ...]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)
    return tuple(deduped)


def _append_observation_group(
    lines: list[str],
    heading: str,
    rows: list[object],
    fields: tuple[str, ...],
) -> None:
    lines.append(f"- {heading}:")
    if not rows:
        lines.append("  - none present")
        return
    for index, row in enumerate(rows, start=1):
        item = _dict(row, heading)
        values = tuple(f"{field}={_format_value(item[field])}" for field in fields)
        lines.append(f"  {index}. {_join_values(values)}")


def _append_values(lines: list[str], values: list[object], *, indent: str = "") -> None:
    if not values:
        lines.append(f"{indent}- none")
        return
    for value in values:
        lines.append(f"{indent}- {_format_value(value)}")


def _join_values(values: object) -> str:
    items = tuple(_format_value(value) for value in values)
    if not items:
        return "none"
    return "; ".join(items)


def _format_value(value: object) -> str:
    if value is None:
        return "none"
    return str(value)


def _primitive_json_copy(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _primitive_json_copy(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_primitive_json_copy(item) for item in value]
    return value
