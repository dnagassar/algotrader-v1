"""Deterministic offline crypto research-pipeline integration slice.

The pipeline composes existing normalization/evidence, opportunity scanning,
and frozen forward-OOS contracts.  It writes only local artifacts and exposes
no broker, credential, submit, mutation, or network surface.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from algotrader.core.types import Bar
from algotrader.errors import ValidationError
from algotrader.orchestration.crypto_repair_forward_oos_accrual import (
    CRYPTO_REPAIR_FORWARD_OOS_ACCRUAL_SCHEMA_VERSION,
    CRYPTO_REPAIR_FORWARD_OOS_DEFAULT_HISTORY_PATH,
    CRYPTO_REPAIR_FORWARD_OOS_DEFAULT_OUTPUT_ROOT,
    run_crypto_repair_forward_oos_accrual,
)
from algotrader.orchestration.opportunity_router import (
    OPPORTUNITY_ROUTER_SCHEMA_VERSION,
    build_crypto_opportunity_candidates_for_symbol,
    classify_bar_history,
    normalize_crypto_asset_metadata,
)
from algotrader.research.crypto_strategy_evidence_battery import (
    CRYPTO_STRATEGY_CANDIDATE_FACTORY_VERSION,
    CRYPTO_STRATEGY_EVIDENCE_BATTERY_SCHEMA_VERSION,
    DEFAULT_CRYPTO_EVIDENCE_SYMBOLS,
    DEFAULT_FRESH_OOS_REPAIR_CANDIDATE,
    DEFAULT_REPAIR_DISCOVERY_CUTOFF,
    CryptoEvidenceAssumptions,
    build_crypto_strategy_candidate_factory,
    build_crypto_strategy_real_data_evidence_packet,
    default_existing_local_crypto_history_paths,
)
from algotrader.signals.crypto_trend import normalize_crypto_symbol


CRYPTO_RESEARCH_PIPELINE_SCHEMA_VERSION = "v5_21_crypto_research_pipeline_v1"
CRYPTO_RESEARCH_SCANNER_POLICY_VERSION = "v5_21_crypto_opportunity_scanner_v1"
CRYPTO_RESEARCH_PIPELINE_DEFAULT_OUTPUT_ROOT = Path(
    "runs/crypto_research_pipeline/latest"
)
CRYPTO_RESEARCH_PIPELINE_DEFAULT_DISCOVERY_HISTORY_PATH = (
    CRYPTO_REPAIR_FORWARD_OOS_DEFAULT_HISTORY_PATH
)
CRYPTO_RESEARCH_PIPELINE_PREFERRED_LOCAL_HISTORY_PATHS = (
    Path(
        "runs/v5_19_6R_same_process_720h_crypto_history_refresh/"
        "normalized_crypto_ohlc_history.csv"
    ),
    Path(
        "runs/v5_19_3_crypto_history_refresh_and_normalization_packet/"
        "normalized_crypto_ohlc_history.csv"
    ),
)
CRYPTO_RESEARCH_SCANNER_REQUIRED_BARS = 50
CRYPTO_RESEARCH_SCANNER_MAX_BAR_AGE = timedelta(hours=2)
CRYPTO_RESEARCH_REGIME_LOOKBACK = 24
CRYPTO_RESEARCH_LOW_VOLATILITY_THRESHOLD = Decimal("0.01")
CRYPTO_RESEARCH_HIGH_VOLATILITY_THRESHOLD = Decimal("0.03")
CRYPTO_RESEARCH_TREND_THRESHOLD = Decimal("0.005")

_SAFETY_BOOLEAN_FIELDS = (
    "paper_submit_authorized",
    "broker_mutation_authorized",
    "live_authorized",
    "broker_read_occurred",
    "broker_mutation_occurred",
    "paper_submit_occurred",
    "paper_cancel_occurred",
    "paper_replace_occurred",
    "paper_close_occurred",
    "paper_liquidate_occurred",
    "live_endpoint_touched",
    "credential_values_accessed",
    "credential_values_exposed",
    "market_data_fetch_occurred",
    "network_access_attempted",
)
_ALLOWED_BROKER_STATE_MODES = {
    "alpaca_paper_observed",
    "paper_observed",
    "simulated_offline",
    "broker_state_not_observed",
    "offline_preview_only",
    "blocked_live_endpoint_indicator",
    "unknown",
}

__all__ = [
    "CRYPTO_RESEARCH_PIPELINE_DEFAULT_DISCOVERY_HISTORY_PATH",
    "CRYPTO_RESEARCH_PIPELINE_DEFAULT_OUTPUT_ROOT",
    "CRYPTO_RESEARCH_PIPELINE_PREFERRED_LOCAL_HISTORY_PATHS",
    "CRYPTO_RESEARCH_PIPELINE_SCHEMA_VERSION",
    "CRYPTO_RESEARCH_SCANNER_POLICY_VERSION",
    "render_crypto_research_pipeline_markdown",
    "run_crypto_research_pipeline",
]


def run_crypto_research_pipeline(
    csv_paths: Iterable[Path | str] | Path | str,
    *,
    as_of: datetime | str,
    output_root: Path | str = CRYPTO_RESEARCH_PIPELINE_DEFAULT_OUTPUT_ROOT,
    universe_symbols: Iterable[str] | None = None,
    availability_json_path: Path | str | None = None,
    discovery_cutoff: datetime | str = DEFAULT_REPAIR_DISCOVERY_CUTOFF,
    forward_oos_state_root: Path | str = CRYPTO_REPAIR_FORWARD_OOS_DEFAULT_OUTPUT_ROOT,
    forward_oos_discovery_history_path: Path | str | None = None,
    assumptions: CryptoEvidenceAssumptions | None = None,
) -> dict[str, object]:
    """Run the complete local crypto research pipeline and write its packet."""

    input_paths = _path_tuple(csv_paths)
    evaluated_at = _utc_datetime(as_of, "as_of")
    cutoff = _utc_datetime(discovery_cutoff, "discovery_cutoff")
    root = Path(output_root)
    symbols = _configured_symbols(universe_symbols, assumptions)
    checked_assumptions = assumptions or CryptoEvidenceAssumptions(
        candidate_symbols=symbols
    )
    if checked_assumptions.candidate_symbols != symbols:
        raise ValidationError(
            "universe_symbols must match assumptions.candidate_symbols when both are supplied."
        )

    paths = _artifact_paths(root)
    evidence_packet = build_crypto_strategy_real_data_evidence_packet(
        input_paths,
        as_of=evaluated_at,
        data_source="normalized_local_crypto_history",
        data_freshness="operator_supplied_as_of_replay",
        assumptions=checked_assumptions,
        normalized_output_path=paths["normalized_history"],
    )
    bars_by_symbol = _read_normalized_bars_by_symbol(paths["normalized_history"])
    availability = _load_local_availability(availability_json_path)
    scanner_packet = _build_scanner_packet(
        symbols=symbols,
        bars_by_symbol=bars_by_symbol,
        as_of=evaluated_at,
        data_inventory=_mapping(evidence_packet.get("data_inventory")),
        normalized_history_path=paths["normalized_history"],
        availability=availability,
        evidence_required_rows=checked_assumptions.min_history_rows_per_symbol,
    )
    candidate_factory = build_crypto_strategy_candidate_factory()

    oos_recovery_source_path = (
        Path(forward_oos_discovery_history_path)
        if forward_oos_discovery_history_path not in (None, "")
        else None
    )
    forward_oos_packet = run_crypto_repair_forward_oos_accrual(
        output_root=forward_oos_state_root,
        discovery_history_path=oos_recovery_source_path,
        as_of=evaluated_at,
        discovery_cutoff=cutoff,
        assumptions=checked_assumptions,
        write_artifacts=False,
    )
    registry = _build_candidate_registry(
        symbols=symbols,
        candidate_factory=candidate_factory,
        evidence_packet=evidence_packet,
        scanner_packet=scanner_packet,
        forward_oos_packet=forward_oos_packet,
        assumptions=checked_assumptions,
        discovery_cutoff=cutoff,
    )

    root.mkdir(parents=True, exist_ok=True)
    _write_json(paths["evidence_packet"], evidence_packet)
    _write_json(paths["scanner_packet"], scanner_packet)
    _write_json(
        paths["candidate_registry"],
        {
            "schema_version": CRYPTO_RESEARCH_PIPELINE_SCHEMA_VERSION,
            "record_type": "crypto_research_ranked_candidate_registry",
            "as_of": evaluated_at.isoformat(),
            "discovery_cutoff": cutoff.isoformat(),
            "factory_version": candidate_factory["factory_version"],
            "candidates": registry,
        },
    )

    operator_packet = _build_operator_packet(
        evaluated_at=evaluated_at,
        cutoff=cutoff,
        input_paths=input_paths,
        paths=paths,
        evidence_packet=evidence_packet,
        scanner_packet=scanner_packet,
        candidate_factory=candidate_factory,
        registry=registry,
        forward_oos_packet=forward_oos_packet,
        availability=availability,
        assumptions=checked_assumptions,
    )
    _write_json(paths["operator_packet_json"], operator_packet)
    paths["operator_packet_markdown"].write_text(
        render_crypto_research_pipeline_markdown(operator_packet),
        encoding="utf-8",
        newline="\n",
    )
    return operator_packet


def render_crypto_research_pipeline_markdown(
    packet: Mapping[str, object],
) -> str:
    """Render the concise human-facing v5.21 operator packet."""

    universe = _mapping(packet.get("universe"))
    scanner = _mapping(packet.get("scanner"))
    evidence = _mapping(packet.get("evidence"))
    counts = _mapping(packet.get("candidate_counts"))
    planning = _mapping(packet.get("no_submit_planning"))
    safety = _mapping(packet.get("side_effects"))
    registry = _mapping_sequence(packet.get("ranked_candidate_registry"))
    frozen = _mapping_sequence(packet.get("frozen_candidates"))
    lines = [
        "# v5.21 Crypto Research Pipeline",
        "",
        f"- Classification: `{packet.get('classification', '')}`",
        f"- As of / discovery cutoff: `{packet.get('as_of', '')}` / `{packet.get('discovery_cutoff', '')}`",
        f"- Universe scanned: `{','.join(_string_sequence(universe.get('scanned_symbols')))}`",
        f"- Excluded symbols: `{len(_mapping_sequence(universe.get('exclusions')))}`",
        f"- Candidates considered / rejected / no-submit eligible: `{counts.get('considered', 0)}` / `{counts.get('rejected', 0)}` / `{counts.get('no_submit_planning_eligible', 0)}`",
        f"- Evidence: `{evidence.get('coverage_classification', '')}` / `{evidence.get('no_submit_decision', '')}`",
        f"- Planning eligibility: `{planning.get('eligibility', '')}`",
        "",
        "## Universe and scanner",
        "",
        "| Symbol | Research scan | Planning scan | Freshness | Rows | Availability | Liquidity proxy | Volatility / regime | Rejections |",
        "| --- | --- | --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for record in _mapping_sequence(scanner.get("records")):
        liquidity = _mapping(record.get("liquidity_proxy"))
        regime = _mapping(record.get("regime_characteristics"))
        lines.append(
            "| "
            + " | ".join(
                (
                    _markdown_text(record.get("symbol")),
                    _markdown_text(record.get("research_scan_status")),
                    _markdown_text(record.get("planning_scan_status")),
                    _markdown_text(record.get("freshness_status")),
                    _markdown_text(record.get("usable_bar_count")),
                    _markdown_text(record.get("availability_status")),
                    _markdown_text(liquidity.get("status")),
                    _markdown_text(
                        f"{regime.get('volatility', '')}/{regime.get('trend', '')}"
                    ),
                    _markdown_text(
                        ",".join(_string_sequence(record.get("rejection_reasons")))
                    ),
                )
            )
            + " |"
        )

    lines.extend(
        (
            "",
            "## Ranked candidate registry",
            "",
            "| Rank | Candidate | Fingerprint | Evidence status | Forward OOS | Rows remaining | No-submit planning | Reasons |",
            "| ---: | --- | --- | --- | --- | ---: | --- | --- |",
        )
    )
    for candidate in registry:
        lines.append(
            "| "
            + " | ".join(
                (
                    _markdown_text(candidate.get("registry_rank")),
                    _markdown_text(candidate.get("candidate_id")),
                    _markdown_text(candidate.get("candidate_fingerprint")),
                    _markdown_text(candidate.get("evidence_status")),
                    _markdown_text(candidate.get("forward_oos_status")),
                    _markdown_text(candidate.get("forward_oos_rows_remaining")),
                    _markdown_text(candidate.get("no_submit_planning_eligibility")),
                    _markdown_text(
                        ",".join(_string_sequence(candidate.get("rejection_reasons")))
                    ),
                )
            )
            + " |"
        )

    lines.extend(("", "## Frozen forward OOS", ""))
    for item in frozen:
        lines.extend(
            (
                f"- Candidate: `{item.get('candidate_id', '')}`",
                f"- Frozen fingerprint: `{item.get('frozen_candidate_fingerprint', '')}`",
                f"- Status / rows remaining: `{item.get('classification', '')}` / `{item.get('rows_still_required', 0)}`",
                f"- Paper-planning eligibility: `{item.get('paper_planning_eligibility', '')}`",
            )
        )
    lines.extend(
        (
            "",
            "## Side effects",
            "",
            f"- Network / market-data fetch: `{_bool_text(safety.get('network_access_attempted'))}` / `{_bool_text(safety.get('market_data_fetch_occurred'))}`",
            f"- Broker read / mutation / paper submit: `{_bool_text(safety.get('broker_read_occurred'))}` / `{_bool_text(safety.get('broker_mutation_occurred'))}` / `{_bool_text(safety.get('paper_submit_occurred'))}`",
            f"- Live endpoint / authorization: `{_bool_text(safety.get('live_endpoint_touched'))}` / `{_bool_text(safety.get('live_authorized'))}`",
            f"- Local artifacts written / runs tracked: `{_bool_text(safety.get('local_files_written'))}` / `{_bool_text(safety.get('runs_tracked'))}`",
            "",
        )
    )
    return "\n".join(lines)


def _build_scanner_packet(
    *,
    symbols: tuple[str, ...],
    bars_by_symbol: Mapping[str, tuple[Bar, ...]],
    as_of: datetime,
    data_inventory: Mapping[str, object],
    normalized_history_path: Path,
    availability: Mapping[str, object],
    evidence_required_rows: int,
) -> dict[str, object]:
    metadata_by_symbol = _mapping(availability.get("metadata_by_symbol"))
    broker_state_mode = str(
        availability.get("broker_state_mode", "broker_state_not_observed")
    )
    rows_per_symbol = _mapping(data_inventory.get("rows_per_symbol_after_normalization"))
    fixture_only = bool(data_inventory.get("fixture_source_detected", False))
    records: list[dict[str, object]] = []
    for symbol in symbols:
        bars = bars_by_symbol.get(symbol, ())
        quality = classify_bar_history(
            symbol=symbol,
            asset_class="crypto",
            bars=bars,
            as_of=as_of,
            required_bar_count=CRYPTO_RESEARCH_SCANNER_REQUIRED_BARS,
            max_bar_age=CRYPTO_RESEARCH_SCANNER_MAX_BAR_AGE,
            data_path=str(normalized_history_path),
            source_mode="normalized_local_crypto_history",
        )
        raw_metadata = metadata_by_symbol.get(symbol)
        metadata = _mapping(raw_metadata) if isinstance(raw_metadata, Mapping) else None
        opportunity_candidates = build_crypto_opportunity_candidates_for_symbol(
            symbol=symbol,
            bars=bars,
            as_of=as_of,
            asset_metadata=metadata,
            broker_state_mode=broker_state_mode,
            venue="local_cached_crypto",
            source="normalized_local_crypto_history",
            data_path=str(normalized_history_path),
            max_bar_age=CRYPTO_RESEARCH_SCANNER_MAX_BAR_AGE,
        )
        research_reasons = list(quality.blockers)
        if int(rows_per_symbol.get(symbol, 0) or 0) < evidence_required_rows:
            research_reasons.append("insufficient_evidence_history")
        if fixture_only:
            research_reasons.append("fixture_only_history")
        planning_blockers = list(
            dict.fromkeys(
                blocker
                for candidate in opportunity_candidates
                for blocker in candidate.blockers
            )
        )
        planning_eligible = any(
            candidate.blocker_status == "eligible" and not candidate.blockers
            for candidate in opportunity_candidates
        )
        availability_statuses = tuple(
            dict.fromkeys(candidate.orderability_status for candidate in opportunity_candidates)
        )
        rejection_reasons = list(
            dict.fromkeys(
                [
                    *research_reasons,
                    *([] if planning_eligible else planning_blockers),
                ]
            )
        )
        records.append(
            {
                "symbol": symbol,
                "research_scan_status": (
                    "accepted_for_research" if not research_reasons else "excluded"
                ),
                "planning_scan_status": (
                    "eligible" if planning_eligible else "blocked"
                ),
                "bar_count": quality.bar_count,
                "usable_bar_count": quality.usable_bar_count,
                "scanner_required_bar_count": quality.required_bar_count,
                "evidence_required_bar_count": evidence_required_rows,
                "latest_timestamp": (
                    "" if quality.latest_timestamp is None else quality.latest_timestamp.isoformat()
                ),
                "data_quality_status": quality.data_quality_status,
                "history_status": quality.history_status,
                "freshness_status": quality.freshness_status,
                "gap_count": quality.gap_count,
                "max_gap_seconds": quality.max_gap_seconds,
                "availability_status": (
                    availability_statuses[0]
                    if len(availability_statuses) == 1
                    else ",".join(availability_statuses)
                ),
                "availability_source": availability.get("source", "not_supplied"),
                "broker_state_mode": broker_state_mode,
                "liquidity_proxy": _liquidity_proxy(bars, as_of),
                "regime_characteristics": _regime_characteristics(bars, as_of),
                "opportunity_candidates": [
                    {
                        "candidate_id": candidate.candidate_id,
                        "strategy_id": candidate.strategy_id,
                        "signal_status": candidate.signal_status,
                        "signal_direction": candidate.signal_direction,
                        "router_score": _decimal_text(candidate.router_score),
                        "blocker_status": candidate.blocker_status,
                        "blockers": list(candidate.blockers),
                        "risk_notes": list(candidate.risk_notes),
                    }
                    for candidate in opportunity_candidates
                ],
                "research_rejection_reasons": list(dict.fromkeys(research_reasons)),
                "planning_blockers": planning_blockers,
                "rejection_reasons": rejection_reasons,
            }
        )
    exclusions = [
        {
            "symbol": record["symbol"],
            "reasons": record["rejection_reasons"],
        }
        for record in records
        if record["research_scan_status"] == "excluded"
        or record["planning_scan_status"] == "blocked"
    ]
    return {
        "schema_version": CRYPTO_RESEARCH_SCANNER_POLICY_VERSION,
        "record_type": "crypto_multi_asset_opportunity_scanner_packet",
        "as_of": as_of.isoformat(),
        "router_contract_version": OPPORTUNITY_ROUTER_SCHEMA_VERSION,
        "configured_symbols": list(symbols),
        "scanned_symbol_count": len(symbols),
        "accepted_for_research_count": sum(
            record["research_scan_status"] == "accepted_for_research"
            for record in records
        ),
        "planning_scan_eligible_count": sum(
            record["planning_scan_status"] == "eligible" for record in records
        ),
        "records": records,
        "exclusions": exclusions,
        "fixed_characteristic_policy": {
            "regime_lookback_bars": CRYPTO_RESEARCH_REGIME_LOOKBACK,
            "low_volatility_mean_abs_return_max": _decimal_text(
                CRYPTO_RESEARCH_LOW_VOLATILITY_THRESHOLD
            ),
            "high_volatility_mean_abs_return_min": _decimal_text(
                CRYPTO_RESEARCH_HIGH_VOLATILITY_THRESHOLD
            ),
            "trend_return_threshold": _decimal_text(
                CRYPTO_RESEARCH_TREND_THRESHOLD
            ),
            "dynamic_optimization": False,
        },
    }


def _build_candidate_registry(
    *,
    symbols: tuple[str, ...],
    candidate_factory: Mapping[str, object],
    evidence_packet: Mapping[str, object],
    scanner_packet: Mapping[str, object],
    forward_oos_packet: Mapping[str, object],
    assumptions: CryptoEvidenceAssumptions,
    discovery_cutoff: datetime,
) -> list[dict[str, object]]:
    evaluations = {
        str(item.get("candidate_id", "")): item
        for item in (
            *_mapping_sequence(evidence_packet.get("candidate_evaluations")),
            *_mapping_sequence(
                evidence_packet.get("diagnostic_repair_candidate_evaluations")
            ),
        )
        if str(item.get("candidate_id", "")).strip()
    }
    scan_by_symbol = {
        str(item.get("symbol", "")): item
        for item in _mapping_sequence(scanner_packet.get("records"))
    }
    frozen = _mapping(forward_oos_packet.get("frozen_candidate"))
    factory_specs: list[tuple[str, Mapping[str, object]]] = [
        ("current", item)
        for item in _mapping_sequence(candidate_factory.get("base_candidates"))
    ]
    factory_specs.extend(
        ("diagnostic_repair", item)
        for item in _mapping_sequence(
            candidate_factory.get("diagnostic_repair_candidates")
        )
    )
    records: list[dict[str, object]] = []
    for symbol in symbols:
        scan = scan_by_symbol.get(symbol, {})
        for origin, spec in factory_specs:
            strategy_id = str(spec.get("strategy_id", ""))
            candidate_id = f"crypto:{symbol}:{strategy_id}"
            evaluation = evaluations.get(candidate_id, {})
            evidence_decision = str(
                evaluation.get("candidate_decision", "insufficient_data")
            )
            evidence_reasons = list(
                _string_sequence(evaluation.get("rejection_reasons"))
            )
            promotion_blockers = list(
                _string_sequence(evaluation.get("promotion_blockers"))
            )
            routes_to_existing_oos = (
                candidate_id == DEFAULT_FRESH_OOS_REPAIR_CANDIDATE
                and origin == "diagnostic_repair"
                and str(frozen.get("candidate_id", ""))
                == DEFAULT_FRESH_OOS_REPAIR_CANDIDATE
            )
            if routes_to_existing_oos:
                forward_status = str(forward_oos_packet.get("classification", ""))
                rows_remaining = int(
                    forward_oos_packet.get("rows_still_required", 0) or 0
                )
                if forward_status == "awaiting_fresh_oos":
                    evidence_status = "awaiting_fresh_oos"
                elif forward_status == "eligible_for_no_submit_paper_planning":
                    evidence_status = "fresh_oos_passed"
                elif forward_status == "fresh_oos_rejected":
                    evidence_status = "fresh_oos_rejected"
                else:
                    evidence_status = forward_status or "forward_oos_blocked"
                oos_reasons = list(
                    _string_sequence(
                        forward_oos_packet.get("blocker_rejection_reasons")
                    )
                )
                evidence_passed = (
                    forward_status == "eligible_for_no_submit_paper_planning"
                )
            else:
                forward_status = "not_required"
                rows_remaining = 0
                oos_reasons = []
                evidence_status = evidence_decision
                evidence_passed = evidence_decision == "promote_to_no_submit_plan"

            scanner_eligible = scan.get("planning_scan_status") == "eligible"
            rejection_reasons = list(
                dict.fromkeys(
                    [
                        *evidence_reasons,
                        *promotion_blockers,
                        *oos_reasons,
                        *(
                            []
                            if scanner_eligible
                            else _string_sequence(scan.get("planning_blockers"))
                        ),
                    ]
                )
            )
            if not evaluation:
                rejection_reasons.insert(0, "evidence_not_runnable")
            eligible = evidence_passed and scanner_eligible
            fingerprint_payload = {
                "candidate_id": candidate_id,
                "symbol": symbol,
                "strategy_id": strategy_id,
                "strategy_family": spec.get("strategy_family", ""),
                "parameters": dict(_mapping(spec.get("parameters"))),
                "candidate_origin": origin,
                "factory_version": candidate_factory.get("factory_version", ""),
                "evidence_policy_version": candidate_factory.get(
                    "evidence_policy_version", ""
                ),
                "discovery_cutoff": discovery_cutoff.isoformat(),
                "assumptions": _assumptions_payload(assumptions),
            }
            evidence_rank = _int_or_none(evaluation.get("rank"))
            records.append(
                {
                    "registry_rank": 0,
                    "evidence_rank": evidence_rank,
                    "candidate_id": candidate_id,
                    "symbol": symbol,
                    "strategy_id": strategy_id,
                    "strategy_family": spec.get("strategy_family", ""),
                    "parameters": dict(_mapping(spec.get("parameters"))),
                    "candidate_origin": origin,
                    "factory_version": candidate_factory.get("factory_version", ""),
                    "candidate_fingerprint": _stable_hash(fingerprint_payload),
                    "discovery_cutoff": discovery_cutoff.isoformat(),
                    "research_scan_status": scan.get("research_scan_status", "excluded"),
                    "planning_scan_status": scan.get("planning_scan_status", "blocked"),
                    "evidence_decision": evidence_decision,
                    "evidence_status": evidence_status,
                    "evidence_rejection_reasons": evidence_reasons,
                    "promotion_blockers": promotion_blockers,
                    "forward_oos_required": routes_to_existing_oos,
                    "forward_oos_status": forward_status,
                    "forward_oos_rows_remaining": rows_remaining,
                    "frozen_candidate_fingerprint": (
                        frozen.get("frozen_candidate_fingerprint", "")
                        if routes_to_existing_oos
                        else ""
                    ),
                    "no_submit_planning_eligibility": (
                        "eligible_for_no_submit_plan" if eligible else "not_eligible"
                    ),
                    "broker_execution_eligibility": "not_eligible",
                    "rejection_reasons": rejection_reasons,
                }
            )
    records.sort(
        key=lambda item: (
            item["evidence_rank"] is None,
            item["evidence_rank"] if item["evidence_rank"] is not None else 0,
            str(item["candidate_id"]),
        )
    )
    for rank, record in enumerate(records, start=1):
        record["registry_rank"] = rank
    return records


def _build_operator_packet(
    *,
    evaluated_at: datetime,
    cutoff: datetime,
    input_paths: tuple[Path, ...],
    paths: Mapping[str, Path],
    evidence_packet: Mapping[str, object],
    scanner_packet: Mapping[str, object],
    candidate_factory: Mapping[str, object],
    registry: Sequence[Mapping[str, object]],
    forward_oos_packet: Mapping[str, object],
    availability: Mapping[str, object],
    assumptions: CryptoEvidenceAssumptions,
) -> dict[str, object]:
    scanned_symbols = _string_sequence(scanner_packet.get("configured_symbols"))
    exclusions = _mapping_sequence(scanner_packet.get("exclusions"))
    eligible_ids = [
        str(item.get("candidate_id", ""))
        for item in registry
        if item.get("no_submit_planning_eligibility")
        == "eligible_for_no_submit_plan"
    ]
    evidence_status_counts = Counter(
        str(item.get("evidence_status", "")) for item in registry
    )
    not_planning_eligible = sum(
        item.get("no_submit_planning_eligibility") != "eligible_for_no_submit_plan"
        for item in registry
    )
    rejected = sum(
        str(item.get("evidence_status", ""))
        in {"reject_candidate", "fresh_oos_rejected"}
        for item in registry
    )
    frozen = _mapping(forward_oos_packet.get("frozen_candidate"))
    frozen_candidates = [
        {
            "candidate_id": frozen.get(
                "candidate_id", DEFAULT_FRESH_OOS_REPAIR_CANDIDATE
            ),
            "candidate_configuration_fingerprint": frozen.get(
                "candidate_configuration_fingerprint", ""
            ),
            "frozen_candidate_fingerprint": frozen.get(
                "frozen_candidate_fingerprint", ""
            ),
            "discovery_cutoff": frozen.get("discovery_cutoff", cutoff.isoformat()),
            "classification": forward_oos_packet.get("classification", ""),
            "rows_still_required": forward_oos_packet.get("rows_still_required", 0),
            "paper_planning_eligibility": forward_oos_packet.get(
                "paper_planning_eligibility", "not_eligible"
            ),
            "blocker_rejection_reasons": list(
                _string_sequence(
                    forward_oos_packet.get("blocker_rejection_reasons")
                )
            ),
        }
    ]
    if eligible_ids:
        classification = "eligible_for_no_submit_planning"
    elif forward_oos_packet.get("classification") == "awaiting_fresh_oos":
        classification = "research_only_awaiting_fresh_oos"
    else:
        classification = "research_only_no_eligible_candidates"

    selected = _mapping(evidence_packet.get("selected_candidate"))
    inventory = _mapping(evidence_packet.get("data_inventory"))
    side_effects = {
        **{field: False for field in _SAFETY_BOOLEAN_FIELDS},
        "broker_sdk_imported": False,
        "local_files_written": True,
        "runs_tracked": False,
    }
    return {
        "schema_version": CRYPTO_RESEARCH_PIPELINE_SCHEMA_VERSION,
        "record_type": "crypto_research_pipeline_operator_packet",
        "classification": classification,
        "as_of": evaluated_at.isoformat(),
        "discovery_cutoff": cutoff.isoformat(),
        "pipeline_components": [
            {
                "stage": "normalized_local_crypto_history",
                "classification": "reused",
                "contract": CRYPTO_STRATEGY_EVIDENCE_BATTERY_SCHEMA_VERSION,
            },
            {
                "stage": "multi_asset_opportunity_scanner",
                "classification": "reused_router_plus_v5_21_adapter",
                "contract": OPPORTUNITY_ROUTER_SCHEMA_VERSION,
            },
            {
                "stage": "versioned_fixed_candidate_factory",
                "classification": "reused_battery_specs_plus_descriptor",
                "contract": CRYPTO_STRATEGY_CANDIDATE_FACTORY_VERSION,
            },
            {
                "stage": "backtest_and_evidence_battery",
                "classification": "reused",
                "contract": CRYPTO_STRATEGY_EVIDENCE_BATTERY_SCHEMA_VERSION,
            },
            {
                "stage": "ranked_candidate_registry",
                "classification": "added_v5_21_adapter",
                "contract": CRYPTO_RESEARCH_PIPELINE_SCHEMA_VERSION,
            },
            {
                "stage": "frozen_forward_oos_tracking",
                "classification": "reused",
                "contract": CRYPTO_REPAIR_FORWARD_OOS_ACCRUAL_SCHEMA_VERSION,
            },
            {
                "stage": "explicit_no_submit_planning_eligibility",
                "classification": "added_v5_21_adapter",
                "contract": CRYPTO_RESEARCH_PIPELINE_SCHEMA_VERSION,
            },
        ],
        "universe": {
            "configured_symbols": list(scanned_symbols),
            "scanned_symbols": list(scanned_symbols),
            "scanned_symbol_count": len(scanned_symbols),
            "exclusions": [dict(item) for item in exclusions],
            "input_paths": [str(path) for path in input_paths],
            "normalized_history_path": str(paths["normalized_history"]),
            "rows_per_symbol": dict(
                _mapping(inventory.get("rows_per_symbol_after_normalization"))
            ),
            "date_range_per_symbol": dict(
                _mapping(inventory.get("date_range_per_symbol"))
            ),
            "volume_status": inventory.get("volume_status", "not_checked"),
            "normalization_blockers": list(
                _string_sequence(inventory.get("blocking_reasons"))
            ),
        },
        "scanner": {
            "policy_version": scanner_packet.get("schema_version", ""),
            "router_contract_version": scanner_packet.get(
                "router_contract_version", ""
            ),
            "accepted_for_research_count": scanner_packet.get(
                "accepted_for_research_count", 0
            ),
            "planning_scan_eligible_count": scanner_packet.get(
                "planning_scan_eligible_count", 0
            ),
            "availability_source": availability.get("source", "not_supplied"),
            "records": [
                _concise_scanner_record(item)
                for item in _mapping_sequence(scanner_packet.get("records"))
            ],
        },
        "strategy_factory": dict(candidate_factory),
        "evidence": {
            "battery_version": CRYPTO_STRATEGY_EVIDENCE_BATTERY_SCHEMA_VERSION,
            "coverage_classification": evidence_packet.get("classification", ""),
            "no_submit_decision": evidence_packet.get("no_submit_decision", ""),
            "selected_candidate_id": selected.get("candidate_id", ""),
            "rejection_reasons": list(
                _string_sequence(evidence_packet.get("rejection_reasons"))
            ),
            "cost_assumptions": {
                "fee_bps": _decimal_text(assumptions.fee_bps),
                "slippage_bps": _decimal_text(assumptions.slippage_bps),
            },
            "risk_constraints": dict(
                _mapping(evidence_packet.get("risk_constraints"))
            ),
            "benchmark_gate_summary": {
                "cash": True,
                "buy_and_hold": True,
                "equal_weight_crypto_basket": True,
                "oos_train_test_split_preserved": True,
                "diagnostic_repairs_require_fresh_oos": True,
            },
            "validation_status": evidence_packet.get("validation_status", ""),
            "validation_errors": list(
                _string_sequence(evidence_packet.get("validation_errors"))
            ),
        },
        "candidate_counts": {
            "considered": len(registry),
            "ranked": len(registry),
            "rejected": rejected,
            "not_planning_eligible": not_planning_eligible,
            "no_submit_planning_eligible": len(eligible_ids),
            "evidence_statuses": dict(sorted(evidence_status_counts.items())),
        },
        "ranked_candidate_registry": [
            _concise_registry_record(item) for item in registry
        ],
        "frozen_candidates": frozen_candidates,
        "forward_oos": {
            "contract_version": CRYPTO_REPAIR_FORWARD_OOS_ACCRUAL_SCHEMA_VERSION,
            "classification": forward_oos_packet.get("classification", ""),
            "candidate_id": frozen.get(
                "candidate_id", DEFAULT_FRESH_OOS_REPAIR_CANDIDATE
            ),
            "oos_rows": forward_oos_packet.get("oos_row_count", 0),
            "rows_still_required": forward_oos_packet.get(
                "rows_still_required", 0
            ),
            "paper_planning_eligibility": forward_oos_packet.get(
                "paper_planning_eligibility", "not_eligible"
            ),
            "blocker_rejection_reasons": list(
                _string_sequence(
                    forward_oos_packet.get("blocker_rejection_reasons")
                )
            ),
        },
        "no_submit_planning": {
            "eligibility": (
                "eligible_for_no_submit_plan" if eligible_ids else "not_eligible"
            ),
            "eligible_candidate_ids": eligible_ids,
            "paper_submit_authorized": False,
            "broker_execution_eligibility": "not_eligible",
        },
        "side_effects": side_effects,
        "artifact_paths": {key: str(path) for key, path in paths.items()},
        "labels": [
            "crypto_research_pipeline",
            "research_only",
            "paper_lab_only",
            "no_submit",
            "offline_default",
            "no_broker_read",
            "no_broker_mutation",
            "not_live_authorized",
            "profit_claim=none",
        ],
        "profit_claim": "none",
    }


def _concise_scanner_record(value: Mapping[str, object]) -> dict[str, object]:
    return {
        "symbol": value.get("symbol", ""),
        "research_scan_status": value.get("research_scan_status", ""),
        "planning_scan_status": value.get("planning_scan_status", ""),
        "usable_bar_count": value.get("usable_bar_count", 0),
        "data_quality_status": value.get("data_quality_status", ""),
        "history_status": value.get("history_status", ""),
        "freshness_status": value.get("freshness_status", ""),
        "availability_status": value.get("availability_status", ""),
        "liquidity_proxy": dict(_mapping(value.get("liquidity_proxy"))),
        "regime_characteristics": dict(
            _mapping(value.get("regime_characteristics"))
        ),
        "rejection_reasons": list(
            _string_sequence(value.get("rejection_reasons"))
        ),
    }


def _concise_registry_record(value: Mapping[str, object]) -> dict[str, object]:
    return {
        "registry_rank": value.get("registry_rank", 0),
        "candidate_id": value.get("candidate_id", ""),
        "candidate_fingerprint": value.get("candidate_fingerprint", ""),
        "evidence_status": value.get("evidence_status", ""),
        "forward_oos_status": value.get("forward_oos_status", ""),
        "forward_oos_rows_remaining": value.get(
            "forward_oos_rows_remaining", 0
        ),
        "no_submit_planning_eligibility": value.get(
            "no_submit_planning_eligibility", "not_eligible"
        ),
        "rejection_reasons": list(
            _string_sequence(value.get("rejection_reasons"))
        ),
    }


def _liquidity_proxy(bars: Sequence[Bar], as_of: datetime) -> dict[str, object]:
    usable = tuple(sorted((bar for bar in bars if bar.timestamp <= as_of), key=lambda bar: bar.timestamp))
    volumes = tuple(bar.volume for bar in usable)
    positive = tuple(value for value in volumes if value > Decimal("0"))
    if not volumes or not positive:
        status = "volume_not_locally_evidenced"
    else:
        status = "positive_volume_observed_not_a_liquidity_guarantee"
    average_volume = (
        sum(volumes, Decimal("0")) / Decimal(len(volumes)) if volumes else Decimal("0")
    )
    average_notional = (
        sum((bar.volume * bar.close for bar in usable), Decimal("0"))
        / Decimal(len(usable))
        if usable
        else Decimal("0")
    )
    return {
        "status": status,
        "volume_observation_count": len(volumes),
        "positive_volume_observation_count": len(positive),
        "latest_volume": _decimal_text(volumes[-1]) if volumes else "",
        "average_volume": _decimal_text(average_volume),
        "average_close_times_volume": _decimal_text(average_notional),
        "limitations": "local_bar_volume_proxy_only",
    }


def _regime_characteristics(
    bars: Sequence[Bar],
    as_of: datetime,
) -> dict[str, object]:
    usable = tuple(sorted((bar for bar in bars if bar.timestamp <= as_of), key=lambda bar: bar.timestamp))
    if len(usable) < 2:
        return {
            "status": "insufficient_data",
            "lookback_bars": 0,
            "return_over_lookback": "",
            "mean_absolute_return": "",
            "volatility": "not_classified",
            "trend": "not_classified",
        }
    window = usable[-(CRYPTO_RESEARCH_REGIME_LOOKBACK + 1) :]
    returns = tuple(
        (current.close / previous.close) - Decimal("1")
        for previous, current in zip(window, window[1:])
    )
    total_return = (window[-1].close / window[0].close) - Decimal("1")
    mean_abs = sum((abs(value) for value in returns), Decimal("0")) / Decimal(
        len(returns)
    )
    if mean_abs <= CRYPTO_RESEARCH_LOW_VOLATILITY_THRESHOLD:
        volatility = "low"
    elif mean_abs >= CRYPTO_RESEARCH_HIGH_VOLATILITY_THRESHOLD:
        volatility = "high"
    else:
        volatility = "moderate"
    if total_return > CRYPTO_RESEARCH_TREND_THRESHOLD:
        trend = "positive"
    elif total_return < -CRYPTO_RESEARCH_TREND_THRESHOLD:
        trend = "negative"
    else:
        trend = "flat"
    return {
        "status": "classified",
        "lookback_bars": len(returns),
        "return_over_lookback": _decimal_text(total_return),
        "mean_absolute_return": _decimal_text(mean_abs),
        "volatility": volatility,
        "trend": trend,
    }


def _load_local_availability(path: Path | str | None) -> dict[str, object]:
    if path in (None, ""):
        return {
            "source": "not_supplied",
            "path": "",
            "broker_state_mode": "broker_state_not_observed",
            "metadata_by_symbol": {},
            "blockers": ["local_availability_metadata_not_supplied"],
        }
    availability_path = Path(path)
    if not availability_path.is_file():
        return {
            "source": "missing_local_cached_artifact",
            "path": str(availability_path),
            "broker_state_mode": "broker_state_not_observed",
            "metadata_by_symbol": {},
            "blockers": ["local_availability_metadata_missing"],
        }
    payload = _read_json_mapping(availability_path)
    records: list[Mapping[str, object]] = list(
        _mapping_sequence(payload.get("records"))
    )
    for key in ("crypto_assets",):
        records.extend(_mapping_sequence(payload.get(key)))
    asset_metadata = payload.get("asset_metadata")
    if isinstance(asset_metadata, Mapping):
        for symbol, raw in asset_metadata.items():
            if isinstance(raw, Mapping):
                records.append({"symbol": symbol, **dict(raw)})
    metadata_by_symbol: dict[str, dict[str, object]] = {}
    blockers: list[str] = []
    for record in records:
        try:
            normalized = normalize_crypto_asset_metadata(record)
        except ValidationError:
            blockers.append("invalid_local_availability_record")
            continue
        metadata_by_symbol[str(normalized["symbol"])] = normalized
    broker_state_mode = str(
        payload.get("broker_state_mode", "broker_state_not_observed")
    ).strip()
    if broker_state_mode not in _ALLOWED_BROKER_STATE_MODES:
        broker_state_mode = "unknown"
    return {
        "source": "local_cached_artifact",
        "path": str(availability_path),
        "broker_state_mode": broker_state_mode,
        "metadata_by_symbol": metadata_by_symbol,
        "blockers": list(dict.fromkeys(blockers)),
    }


def _read_normalized_bars_by_symbol(path: Path) -> dict[str, tuple[Bar, ...]]:
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ValidationError(f"unable to read normalized crypto history: {path}") from exc
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        raise ValidationError("normalized crypto history requires a CSV header.")
    grouped: dict[str, list[Bar]] = {}
    for row in reader:
        if None in row:
            raise ValidationError("normalized crypto history contains a malformed row.")
        symbol = normalize_crypto_symbol(str(row.get("symbol", "")))
        volume_text = str(row.get("volume", "")).strip()
        grouped.setdefault(symbol, []).append(
            Bar(
                symbol=symbol,
                timestamp=_utc_datetime(row.get("timestamp", ""), "timestamp"),
                open=_decimal(row.get("open", ""), "open"),
                high=_decimal(row.get("high", ""), "high"),
                low=_decimal(row.get("low", ""), "low"),
                close=_decimal(row.get("close", ""), "close"),
                volume=_decimal(volume_text or "0", "volume"),
            )
        )
    return {
        symbol: tuple(sorted(values, key=lambda bar: bar.timestamp))
        for symbol, values in sorted(grouped.items())
    }


def _assumptions_payload(
    assumptions: CryptoEvidenceAssumptions,
) -> dict[str, object]:
    return {
        "initial_equity": _decimal_text(assumptions.initial_equity),
        "fee_bps": _decimal_text(assumptions.fee_bps),
        "slippage_bps": _decimal_text(assumptions.slippage_bps),
        "min_bars_per_symbol": assumptions.min_bars_per_symbol,
        "min_history_rows_per_symbol": assumptions.min_history_rows_per_symbol,
        "min_history_span_hours": assumptions.min_history_span_hours,
        "train_fraction_numerator": assumptions.train_fraction_numerator,
        "train_fraction_denominator": assumptions.train_fraction_denominator,
        "max_test_drawdown": _decimal_text(assumptions.max_test_drawdown),
        "min_test_excess_return_vs_buy_hold": _decimal_text(
            assumptions.min_test_excess_return_vs_buy_hold
        ),
        "min_test_total_return": _decimal_text(
            assumptions.min_test_total_return
        ),
        "paper_max_notional": _decimal_text(assumptions.paper_max_notional),
        "max_paper_allocation_fraction": _decimal_text(
            assumptions.max_paper_allocation_fraction
        ),
        "candidate_symbols": list(assumptions.candidate_symbols),
    }


def _configured_symbols(
    values: Iterable[str] | None,
    assumptions: CryptoEvidenceAssumptions | None,
) -> tuple[str, ...]:
    if values is None:
        return (
            assumptions.candidate_symbols
            if assumptions is not None
            else DEFAULT_CRYPTO_EVIDENCE_SYMBOLS
        )
    symbols = tuple(normalize_crypto_symbol(value) for value in values)
    if not symbols:
        raise ValidationError("universe_symbols must not be empty.")
    if len(set(symbols)) != len(symbols):
        raise ValidationError("universe_symbols must not contain duplicates.")
    return symbols


def _default_pipeline_input_paths() -> tuple[Path, ...]:
    for path in CRYPTO_RESEARCH_PIPELINE_PREFERRED_LOCAL_HISTORY_PATHS:
        if path.is_file():
            return (path,)
    return default_existing_local_crypto_history_paths()


def _artifact_paths(root: Path) -> dict[str, Path]:
    return {
        "normalized_history": root / "normalized_crypto_history.csv",
        "scanner_packet": root / "scanner_packet.json",
        "evidence_packet": root / "evidence_packet.json",
        "candidate_registry": root / "candidate_registry.json",
        "operator_packet_json": root / "operator_packet.json",
        "operator_packet_markdown": root / "operator_packet.md",
    }


def _path_tuple(
    paths: Iterable[Path | str] | Path | str,
) -> tuple[Path, ...]:
    if isinstance(paths, (str, Path)):
        return (Path(paths),)
    if isinstance(paths, bytes):
        raise ValidationError("csv_paths must be paths, not bytes.")
    return tuple(Path(path) for path in paths)


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _read_json_mapping(path: Path) -> Mapping[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"unable to read local availability JSON: {path}") from exc
    if not isinstance(payload, Mapping):
        raise ValidationError("local availability JSON must contain an object.")
    return payload


def _stable_hash(value: object) -> str:
    canonical = json.dumps(
        _json_safe(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _utc_datetime(value: datetime | str | object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if not text:
            raise ValidationError(f"{field_name} is required.")
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(f"{field_name} must be ISO formatted.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _decimal(value: object, field_name: str) -> Decimal:
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be decimal text.") from exc
    if not parsed.is_finite():
        raise ValidationError(f"{field_name} must be finite.")
    return parsed


def _decimal_text(value: Decimal) -> str:
    if value == Decimal("0"):
        return "0"
    return format(value.normalize(), "f")


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _mapping_sequence(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _string_sequence(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value if str(item).strip())


def _int_or_none(value: object) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _markdown_text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _bool_text(value: object) -> str:
    return "true" if bool(value) else "false"


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the deterministic offline v5.21 crypto research pipeline."
    )
    parser.add_argument(
        "--input-csv",
        action="append",
        default=[],
        help="Local crypto history CSV. May be supplied multiple times.",
    )
    parser.add_argument("--as-of", required=True, help="Deterministic UTC replay timestamp.")
    parser.add_argument(
        "--output-root",
        default=str(CRYPTO_RESEARCH_PIPELINE_DEFAULT_OUTPUT_ROOT),
    )
    parser.add_argument(
        "--symbols",
        default=",".join(DEFAULT_CRYPTO_EVIDENCE_SYMBOLS),
        help="Comma-separated configured local crypto universe.",
    )
    parser.add_argument(
        "--availability-json",
        default="",
        help="Optional local cached availability/orderability JSON; no broker read occurs.",
    )
    parser.add_argument(
        "--discovery-cutoff",
        default=DEFAULT_REPAIR_DISCOVERY_CUTOFF.isoformat(),
    )
    parser.add_argument(
        "--forward-oos-state-root",
        default=str(CRYPTO_REPAIR_FORWARD_OOS_DEFAULT_OUTPUT_ROOT),
    )
    parser.add_argument(
        "--forward-oos-recovery-source-path",
        "--forward-oos-discovery-history-path",
        dest="forward_oos_recovery_source_path",
        default="",
        help=(
            "Optional explicit recovery source for a missing frozen snapshot; "
            "normal pipeline consumption uses the existing state snapshot."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_paths = tuple(Path(path) for path in args.input_csv)
    if not input_paths:
        input_paths = _default_pipeline_input_paths()
    packet = run_crypto_research_pipeline(
        input_paths,
        as_of=args.as_of,
        output_root=args.output_root,
        universe_symbols=tuple(
            item.strip() for item in args.symbols.split(",") if item.strip()
        ),
        availability_json_path=args.availability_json or None,
        discovery_cutoff=args.discovery_cutoff,
        forward_oos_state_root=args.forward_oos_state_root,
        forward_oos_discovery_history_path=(
            args.forward_oos_recovery_source_path or None
        ),
    )
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
