"""Deterministic assembly of operating briefs from prepared advisory parts."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from algotrader.advisory.operating_brief import (
    AdvisoryLabel,
    OperatingBrief,
    ResearchCandidateDossier,
    RiskAuthorityStatus,
    StrategyEligibilityStatus,
)
from algotrader.errors import ValidationError

__all__ = ["assemble_operating_brief_from_parts"]


_ELEVATED_LABELS = frozenset(
    (
        AdvisoryLabel.PAPER_ELIGIBLE,
        AdvisoryLabel.LIVE_PROBE_ELIGIBLE,
        AdvisoryLabel.LIVE_AUTHORIZED,
    )
)

_ASSEMBLED_BRIEF_LIMITATIONS = ("Advisory metadata only.",)


def assemble_operating_brief_from_parts(
    *,
    as_of_date: date,
    dossiers: Iterable[ResearchCandidateDossier],
    strategy_statuses: Iterable[StrategyEligibilityStatus],
    risk_statuses: Iterable[RiskAuthorityStatus],
) -> OperatingBrief:
    """Assemble an OperatingBrief from already-built advisory objects."""
    assembly_date = _plain_date(as_of_date, "as_of_date")
    dossier_items = _typed_tuple(
        dossiers,
        ResearchCandidateDossier,
        "dossiers",
        "ResearchCandidateDossier",
    )
    strategy_items = _typed_tuple(
        strategy_statuses,
        StrategyEligibilityStatus,
        "strategy_statuses",
        "StrategyEligibilityStatus",
    )
    risk_items = _typed_tuple(
        risk_statuses,
        RiskAuthorityStatus,
        "risk_statuses",
        "RiskAuthorityStatus",
    )

    if not dossier_items:
        raise ValidationError("dossiers must include at least one entry.")

    _reject_as_of_date_mismatches(assembly_date, dossier_items, "dossiers")
    _reject_as_of_date_mismatches(
        assembly_date,
        strategy_items,
        "strategy_statuses",
    )
    _reject_as_of_date_mismatches(assembly_date, risk_items, "risk_statuses")

    dossier_ids = _unique_candidate_ids(dossier_items, "dossiers")
    strategy_ids = _unique_candidate_ids(strategy_items, "strategy_statuses")
    risk_ids = _unique_candidate_ids(risk_items, "risk_statuses")

    _reject_orphan_statuses(dossier_ids, strategy_items, "strategy")
    _reject_orphan_statuses(dossier_ids, risk_items, "risk")
    _require_elevated_status_matches(dossier_items, strategy_ids, risk_ids)

    return OperatingBrief(
        brief_id=f"brief-{assembly_date.isoformat()}",
        as_of_date=assembly_date,
        dossiers=dossier_items,
        strategy_statuses=strategy_items,
        risk_statuses=risk_items,
        limitations=_ASSEMBLED_BRIEF_LIMITATIONS,
    )


def _plain_date(value: object, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a date.")
    return value


def _typed_tuple(
    values: Iterable[object],
    expected_type: type[object],
    field_name: str,
    expected_name: str,
) -> tuple[object, ...]:
    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(
            f"{field_name} must be an iterable of {expected_name}."
        ) from exc

    for item in items:
        if not isinstance(item, expected_type):
            raise ValidationError(f"{field_name} must contain {expected_name}.")

    return items


def _reject_as_of_date_mismatches(
    as_of_date: date,
    items: tuple[object, ...],
    field_name: str,
) -> None:
    for item in items:
        if hasattr(item, "as_of_date") and item.as_of_date != as_of_date:
            raise ValidationError(
                f"{field_name} as_of_date must match assembly as_of_date."
            )


def _unique_candidate_ids(items: tuple[object, ...], field_name: str) -> frozenset[str]:
    seen: set[str] = set()
    for item in items:
        if item.candidate_id in seen:
            raise ValidationError(f"{field_name} contains duplicate candidate_id.")
        seen.add(item.candidate_id)
    return frozenset(seen)


def _reject_orphan_statuses(
    dossier_ids: frozenset[str],
    statuses: tuple[StrategyEligibilityStatus, ...] | tuple[RiskAuthorityStatus, ...],
    status_name: str,
) -> None:
    unknown_ids = tuple(
        status.candidate_id
        for status in statuses
        if status.candidate_id not in dossier_ids
    )
    if unknown_ids:
        unknown = ", ".join(unknown_ids)
        raise ValidationError(
            f"{status_name} status candidate is not in dossiers: {unknown}."
        )


def _require_elevated_status_matches(
    dossiers: tuple[ResearchCandidateDossier, ...],
    strategy_ids: frozenset[str],
    risk_ids: frozenset[str],
) -> None:
    for dossier in dossiers:
        if dossier.advisory_label not in _ELEVATED_LABELS:
            continue

        if dossier.candidate_id not in strategy_ids:
            raise ValidationError(
                "elevated advisory labels require matching strategy status."
            )
        if dossier.candidate_id not in risk_ids:
            raise ValidationError(
                "elevated advisory labels require matching risk status."
            )
