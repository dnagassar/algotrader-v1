"""Offline M424 guarded ETF/SMA preferred-baseline comparison authorization."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path

from .etf_sma_preferred_baseline_manifest import (
    DEFAULT_PREFERRED_ADJUSTED_BASELINE_MANIFEST_PATH,
    PreferredBaselineGuardResult,
    load_and_validate_preferred_adjusted_baseline_manifest,
)

__all__ = [
    "DEFAULT_GUARDED_PREFERRED_BASELINE_COMPARISON_AUTHORIZATION_PATH",
    "EtfSmaGuardedPreferredBaselineComparisonConfig",
    "build_etf_sma_guarded_preferred_baseline_comparison_authorization",
    "render_etf_sma_guarded_preferred_baseline_comparison_json",
    "render_etf_sma_guarded_preferred_baseline_comparison_text",
    "write_etf_sma_guarded_preferred_baseline_comparison_jsonl",
]


DEFAULT_GUARDED_PREFERRED_BASELINE_COMPARISON_AUTHORIZATION_PATH = (
    Path("runs")
    / "paper_lab"
    / "m424_guarded_preferred_baseline_comparison_authorization.jsonl"
)


@dataclass(frozen=True)
class EtfSmaGuardedPreferredBaselineComparisonConfig:
    """Configuration for the offline M424 comparison authorization artifact."""

    run_id: str
    symbol: str
    manifest_path: str | Path = DEFAULT_PREFERRED_ADJUSTED_BASELINE_MANIFEST_PATH


_COMMAND = "etf-sma-preferred-baseline-comparison-guard"
_RECORD_TYPE = "etf_sma_guarded_preferred_baseline_comparison_authorization"
_SCHEMA_VERSION = "1"
_MILESTONE = "M424"
_BASELINE_SOURCE_MILESTONE = "M422"
_GUARD_SOURCE_MILESTONE = "M423"
_GUARD_READY_STATUS = "preferred_adjusted_baseline_guard_ready"
_AUTHORIZED_STATUS = "preferred_baseline_guard_passed"
_BLOCKED_STATUS = "blocked_preferred_baseline_guard"
_DOWNSTREAM_USE = "offline_etf_sma_preferred_baseline_comparison"


def build_etf_sma_guarded_preferred_baseline_comparison_authorization(
    config: EtfSmaGuardedPreferredBaselineComparisonConfig,
) -> dict[str, object]:
    """Build one fail-closed downstream comparison authorization record."""

    manifest_path = Path(config.manifest_path)
    guard_result = load_and_validate_preferred_adjusted_baseline_manifest(
        manifest_path
    )
    blockers = _guard_blockers(guard_result)
    payload = _base_payload(config, manifest_path, guard_result)
    if blockers:
        return _blocked_payload(payload, blockers)

    payload.update(
        {
            "comparison_authorization_status": _AUTHORIZED_STATUS,
            "downstream_comparison_authorized": True,
            "active_preferred_baseline": guard_result.preferred_baseline,
            "active_preferred_basis": guard_result.preferred_basis,
            "comparison_basis": guard_result.comparison_basis,
            "matched_total_interval_count": (
                guard_result.matched_total_interval_count
            ),
            "known_basis_delta_slices": list(
                guard_result.known_basis_delta_slices
            ),
            "blockers": [],
        }
    )
    payload.update(_safety_false_fields())
    return payload


def render_etf_sma_guarded_preferred_baseline_comparison_json(
    payload: Mapping[str, object],
) -> str:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))


def render_etf_sma_guarded_preferred_baseline_comparison_text(
    payload: Mapping[str, object],
) -> str:
    lines = [
        "comparison_authorization_status: "
        f"{payload['comparison_authorization_status']}",
        f"guard_status: {payload['guard_status']}",
        "downstream_comparison_authorized: "
        f"{_bool_text(payload.get('downstream_comparison_authorized'))}",
        f"symbol: {payload['symbol']}",
        f"manifest_path: {payload['manifest_path']}",
        f"baseline_source_milestone: {payload['baseline_source_milestone']}",
        f"guard_source_milestone: {payload['guard_source_milestone']}",
    ]
    if payload.get("downstream_comparison_authorized") is True:
        lines.extend(
            [
                f"active_preferred_baseline: {payload['active_preferred_baseline']}",
                f"active_preferred_basis: {payload['active_preferred_basis']}",
                f"comparison_basis: {payload['comparison_basis']}",
                "known_basis_delta_slices: "
                f"{','.join(_payload_string_tuple(payload.get('known_basis_delta_slices')))}",
            ]
        )

    blockers = _payload_string_tuple(payload.get("blockers"))
    if blockers:
        lines.append(f"blockers: {','.join(blockers)}")

    lines.extend(
        [
            f"trade_recommendation: {payload['trade_recommendation']}",
            f"profit_claim: {payload['profit_claim']}",
        ]
    )
    return "\n".join(lines)


def write_etf_sma_guarded_preferred_baseline_comparison_jsonl(
    payload: Mapping[str, object],
    run_log: str | Path,
) -> Path:
    path = Path(run_log)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_etf_sma_guarded_preferred_baseline_comparison_json(payload) + "\n",
        encoding="utf-8",
    )
    return path


def _base_payload(
    config: EtfSmaGuardedPreferredBaselineComparisonConfig,
    manifest_path: Path,
    guard_result: PreferredBaselineGuardResult,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "record_type": _RECORD_TYPE,
        "schema_version": _SCHEMA_VERSION,
        "command": _COMMAND,
        "milestone": _MILESTONE,
        "run_id": config.run_id,
        "symbol": config.symbol,
        "manifest_path": str(manifest_path),
        "guard_status": guard_result.guard_status,
        "comparison_authorization_status": _BLOCKED_STATUS,
        "downstream_comparison_authorized": False,
        "baseline_source_milestone": _BASELINE_SOURCE_MILESTONE,
        "guard_source_milestone": _GUARD_SOURCE_MILESTONE,
        "downstream_use": _DOWNSTREAM_USE,
        "trade_recommendation": "none",
        "operator_trade_recommendation": "none",
        "profit_claim": "none",
        "no_trade_recommendation": True,
        "not_live_authorized": True,
        "paper_lab_only": True,
        "research_only": True,
        "signal_evaluation_only": True,
        "broker_mutation_status": "none",
        "network_broker_access_status": "not_attempted",
        "credential_access_status": "not_attempted",
        "blockers": [],
    }
    payload.update(_safety_false_fields())
    return payload


def _blocked_payload(
    payload: dict[str, object],
    blockers: Sequence[str],
) -> dict[str, object]:
    clean_blockers = [str(blocker) for blocker in blockers if str(blocker)]
    payload.update(
        {
            "comparison_authorization_status": _BLOCKED_STATUS,
            "downstream_comparison_authorized": False,
            "blockers": clean_blockers,
            "blocked_reason": clean_blockers[0] if clean_blockers else "blocked",
            "trade_recommendation": "none",
            "operator_trade_recommendation": "none",
            "profit_claim": "none",
        }
    )
    payload.update(_safety_false_fields())
    return payload


def _guard_blockers(
    guard_result: PreferredBaselineGuardResult,
) -> tuple[str, ...]:
    blockers = list(guard_result.blockers)
    if guard_result.guard_status != _GUARD_READY_STATUS:
        blockers.append("preferred_baseline_guard_not_ready")
    if guard_result.preferred_baseline_active is not True:
        blockers.append("preferred_baseline_guard_not_active")
    return tuple(dict.fromkeys(str(blocker) for blocker in blockers if str(blocker)))


def _safety_false_fields() -> dict[str, bool]:
    return {
        "submitted": False,
        "mutated": False,
        "broker_action_performed": False,
        "network_access_attempted": False,
        "credential_access_attempted": False,
        "live_authorized": False,
    }


def _payload_string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value)


def _bool_text(value: object) -> str:
    return "true" if bool(value) else "false"
