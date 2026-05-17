"""Deterministic board-summary metadata for advisory operating briefs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from algotrader.advisory.operating_brief import AdvisoryLabel, OperatingBrief
from algotrader.errors import ValidationError

__all__ = [
    "OperatingBriefBoardSummary",
    "build_operating_brief_board_summary",
]


@dataclass(frozen=True, slots=True)
class OperatingBriefBoardSummary:
    """Display-ready metadata derived from an existing operating brief."""

    as_of_date: date
    candidate_ids_by_label: tuple[tuple[AdvisoryLabel, tuple[str, ...]], ...]
    candidate_counts_by_label: tuple[tuple[AdvisoryLabel, int], ...]
    research_queue_candidate_ids: tuple[str, ...]
    watchlist_candidate_ids: tuple[str, ...]
    paper_eligible_candidate_ids: tuple[str, ...]
    live_probe_eligible_candidate_ids: tuple[str, ...]
    live_authorized_candidate_ids: tuple[str, ...]
    live_authorization_statuses: tuple[
        tuple[str, AdvisoryLabel, bool, bool, bool, bool, bool],
        ...,
    ]
    strategy_blockers: tuple[tuple[str, str | None, tuple[str, ...]], ...]
    risk_blockers: tuple[tuple[str, str | None, tuple[str, ...]], ...]
    uncertainty_summaries: tuple[tuple[str, tuple[str, ...]], ...]
    failure_mode_summaries: tuple[tuple[str, tuple[str, ...]], ...]
    brief_limitations: tuple[str, ...]
    candidate_limitations: tuple[tuple[str, tuple[str, ...]], ...]
    strategy_limitations: tuple[tuple[str, str | None, tuple[str, ...]], ...]
    risk_limitations: tuple[tuple[str, str | None, tuple[str, ...]], ...]
    non_claims: tuple[str, ...] = (
        "This summary is advisory metadata only.",
        "It reports existing labels, blockers, uncertainty, failure modes, and limitations only.",
        "It does not create live action authority or validate profitability.",
        "It does not discover candidates or change their source status.",
    )

    def to_dict(self) -> dict[str, object]:
        """Return deterministic primitive board-summary metadata."""
        return {
            "as_of_date": _serialize_plain_date(self.as_of_date),
            "candidate_ids_by_label": {
                label.value: list(candidate_ids)
                for label, candidate_ids in self.candidate_ids_by_label
            },
            "candidate_counts_by_label": {
                label.value: count
                for label, count in self.candidate_counts_by_label
            },
            "research_queue_candidate_ids": list(self.research_queue_candidate_ids),
            "watchlist_candidate_ids": list(self.watchlist_candidate_ids),
            "paper_eligible_candidate_ids": list(self.paper_eligible_candidate_ids),
            "live_probe_eligible_candidate_ids": list(
                self.live_probe_eligible_candidate_ids
            ),
            "live_authorized_candidate_ids": list(self.live_authorized_candidate_ids),
            "live_authorization_statuses": [
                {
                    "candidate_id": candidate_id,
                    "advisory_label": advisory_label.value,
                    "strategy_status_present": strategy_status_present,
                    "strategy_live_authorized": strategy_live_authorized,
                    "risk_status_present": risk_status_present,
                    "risk_live_authorized": risk_live_authorized,
                    "label_live_authorized": label_live_authorized,
                }
                for (
                    candidate_id,
                    advisory_label,
                    strategy_status_present,
                    strategy_live_authorized,
                    risk_status_present,
                    risk_live_authorized,
                    label_live_authorized,
                ) in self.live_authorization_statuses
            ],
            "strategy_blockers": [
                {
                    "candidate_id": candidate_id,
                    "mandate_id": mandate_id,
                    "blocking_reasons": list(blocking_reasons),
                }
                for candidate_id, mandate_id, blocking_reasons in self.strategy_blockers
            ],
            "risk_blockers": [
                {
                    "candidate_id": candidate_id,
                    "authority_id": authority_id,
                    "blocking_reasons": list(blocking_reasons),
                }
                for candidate_id, authority_id, blocking_reasons in self.risk_blockers
            ],
            "uncertainty_summaries": [
                {
                    "candidate_id": candidate_id,
                    "uncertainty_factors": list(uncertainty_factors),
                }
                for candidate_id, uncertainty_factors in self.uncertainty_summaries
            ],
            "failure_mode_summaries": [
                {
                    "candidate_id": candidate_id,
                    "failure_modes": list(failure_modes),
                }
                for candidate_id, failure_modes in self.failure_mode_summaries
            ],
            "brief_limitations": list(self.brief_limitations),
            "candidate_limitations": [
                {
                    "candidate_id": candidate_id,
                    "limitations": list(limitations),
                }
                for candidate_id, limitations in self.candidate_limitations
            ],
            "strategy_limitations": [
                {
                    "candidate_id": candidate_id,
                    "mandate_id": mandate_id,
                    "limitations": list(limitations),
                }
                for candidate_id, mandate_id, limitations in self.strategy_limitations
            ],
            "risk_limitations": [
                {
                    "candidate_id": candidate_id,
                    "authority_id": authority_id,
                    "limitations": list(limitations),
                }
                for candidate_id, authority_id, limitations in self.risk_limitations
            ],
            "non_claims": list(self.non_claims),
        }

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "as_of_date",
            _plain_date(self.as_of_date, "as_of_date"),
        )
        object.__setattr__(
            self,
            "candidate_ids_by_label",
            _label_groups(self.candidate_ids_by_label),
        )
        object.__setattr__(
            self,
            "candidate_counts_by_label",
            _label_counts(self.candidate_counts_by_label),
        )
        object.__setattr__(
            self,
            "research_queue_candidate_ids",
            _string_tuple(
                self.research_queue_candidate_ids,
                "research_queue_candidate_ids",
            ),
        )
        object.__setattr__(
            self,
            "watchlist_candidate_ids",
            _string_tuple(self.watchlist_candidate_ids, "watchlist_candidate_ids"),
        )
        object.__setattr__(
            self,
            "paper_eligible_candidate_ids",
            _string_tuple(
                self.paper_eligible_candidate_ids,
                "paper_eligible_candidate_ids",
            ),
        )
        object.__setattr__(
            self,
            "live_probe_eligible_candidate_ids",
            _string_tuple(
                self.live_probe_eligible_candidate_ids,
                "live_probe_eligible_candidate_ids",
            ),
        )
        object.__setattr__(
            self,
            "live_authorized_candidate_ids",
            _string_tuple(
                self.live_authorized_candidate_ids,
                "live_authorized_candidate_ids",
            ),
        )
        object.__setattr__(
            self,
            "live_authorization_statuses",
            _live_authorization_statuses(self.live_authorization_statuses),
        )
        object.__setattr__(
            self,
            "strategy_blockers",
            _id_reason_records(self.strategy_blockers, "strategy_blockers"),
        )
        object.__setattr__(
            self,
            "risk_blockers",
            _id_reason_records(self.risk_blockers, "risk_blockers"),
        )
        object.__setattr__(
            self,
            "uncertainty_summaries",
            _candidate_text_records(
                self.uncertainty_summaries,
                "uncertainty_summaries",
            ),
        )
        object.__setattr__(
            self,
            "failure_mode_summaries",
            _candidate_text_records(
                self.failure_mode_summaries,
                "failure_mode_summaries",
            ),
        )
        object.__setattr__(
            self,
            "brief_limitations",
            _string_tuple(self.brief_limitations, "brief_limitations"),
        )
        object.__setattr__(
            self,
            "candidate_limitations",
            _candidate_text_records(
                self.candidate_limitations,
                "candidate_limitations",
            ),
        )
        object.__setattr__(
            self,
            "strategy_limitations",
            _id_reason_records(self.strategy_limitations, "strategy_limitations"),
        )
        object.__setattr__(
            self,
            "risk_limitations",
            _id_reason_records(self.risk_limitations, "risk_limitations"),
        )
        object.__setattr__(
            self,
            "non_claims",
            _string_tuple(self.non_claims, "non_claims"),
        )


def build_operating_brief_board_summary(
    brief: OperatingBrief,
) -> OperatingBriefBoardSummary:
    """Build a deterministic board summary from an existing operating brief."""
    if not isinstance(brief, OperatingBrief):
        raise ValidationError("brief must be an OperatingBrief.")

    candidate_ids_by_label = _candidate_ids_by_label(brief)
    strategy_by_candidate = {
        status.candidate_id: status for status in brief.strategy_statuses
    }
    risk_by_candidate = {status.candidate_id: status for status in brief.risk_statuses}

    return OperatingBriefBoardSummary(
        as_of_date=brief.as_of_date,
        candidate_ids_by_label=candidate_ids_by_label,
        candidate_counts_by_label=tuple(
            (label, len(candidate_ids))
            for label, candidate_ids in candidate_ids_by_label
        ),
        research_queue_candidate_ids=_candidate_ids_for_label(
            candidate_ids_by_label,
            AdvisoryLabel.RESEARCH_ONLY,
        ),
        watchlist_candidate_ids=_candidate_ids_for_label(
            candidate_ids_by_label,
            AdvisoryLabel.WATCHLIST_ONLY,
        ),
        paper_eligible_candidate_ids=_candidate_ids_for_label(
            candidate_ids_by_label,
            AdvisoryLabel.PAPER_ELIGIBLE,
        ),
        live_probe_eligible_candidate_ids=_candidate_ids_for_label(
            candidate_ids_by_label,
            AdvisoryLabel.LIVE_PROBE_ELIGIBLE,
        ),
        live_authorized_candidate_ids=_candidate_ids_for_label(
            candidate_ids_by_label,
            AdvisoryLabel.LIVE_AUTHORIZED,
        ),
        live_authorization_statuses=tuple(
            (
                dossier.candidate_id,
                dossier.advisory_label,
                dossier.candidate_id in strategy_by_candidate,
                strategy_by_candidate[dossier.candidate_id].live_authorized
                if dossier.candidate_id in strategy_by_candidate
                else False,
                dossier.candidate_id in risk_by_candidate,
                risk_by_candidate[dossier.candidate_id].live_authorized
                if dossier.candidate_id in risk_by_candidate
                else False,
                dossier.advisory_label == AdvisoryLabel.LIVE_AUTHORIZED,
            )
            for dossier in brief.dossiers
        ),
        strategy_blockers=tuple(
            (
                status.candidate_id,
                status.mandate_id,
                status.blocking_reasons,
            )
            for status in brief.strategy_statuses
            if status.blocking_reasons
        ),
        risk_blockers=tuple(
            (
                status.candidate_id,
                status.authority_id,
                status.blocking_reasons,
            )
            for status in brief.risk_statuses
            if status.blocking_reasons
        ),
        uncertainty_summaries=tuple(
            (dossier.candidate_id, dossier.uncertainty_factors)
            for dossier in brief.dossiers
            if dossier.uncertainty_factors
        ),
        failure_mode_summaries=tuple(
            (dossier.candidate_id, dossier.failure_modes)
            for dossier in brief.dossiers
            if dossier.failure_modes
        ),
        brief_limitations=brief.limitations,
        candidate_limitations=tuple(
            (dossier.candidate_id, dossier.limitations)
            for dossier in brief.dossiers
            if dossier.limitations
        ),
        strategy_limitations=tuple(
            (status.candidate_id, status.mandate_id, status.limitations)
            for status in brief.strategy_statuses
            if status.limitations
        ),
        risk_limitations=tuple(
            (status.candidate_id, status.authority_id, status.limitations)
            for status in brief.risk_statuses
            if status.limitations
        ),
    )


_ADVISORY_LABEL_ORDER = (
    AdvisoryLabel.RESEARCH_ONLY,
    AdvisoryLabel.WATCHLIST_ONLY,
    AdvisoryLabel.PAPER_ELIGIBLE,
    AdvisoryLabel.LIVE_PROBE_ELIGIBLE,
    AdvisoryLabel.LIVE_AUTHORIZED,
)


def _candidate_ids_by_label(
    brief: OperatingBrief,
) -> tuple[tuple[AdvisoryLabel, tuple[str, ...]], ...]:
    grouped: dict[AdvisoryLabel, list[str]] = {
        label: [] for label in _ADVISORY_LABEL_ORDER
    }

    for dossier in brief.dossiers:
        grouped[dossier.advisory_label].append(dossier.candidate_id)

    return tuple((label, tuple(grouped[label])) for label in _ADVISORY_LABEL_ORDER)


def _candidate_ids_for_label(
    candidate_ids_by_label: tuple[tuple[AdvisoryLabel, tuple[str, ...]], ...],
    label: AdvisoryLabel,
) -> tuple[str, ...]:
    for candidate_label, candidate_ids in candidate_ids_by_label:
        if candidate_label == label:
            return candidate_ids
    return ()


def _plain_date(value: object, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a date.")
    return value


def _serialize_plain_date(value: object) -> str:
    return _plain_date(value, "as_of_date").isoformat()


def _string_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    if isinstance(values, str):
        raise ValidationError(f"{field_name} must be an iterable of strings.")

    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(f"{field_name} must be an iterable of strings.") from exc

    return tuple(
        _required_string(value, f"{field_name}[{index}]")
        for index, value in enumerate(items)
    )


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} is required.")
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} is required.")
    return normalized


def _optional_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, field_name)


def _advisory_label(value: object, field_name: str) -> AdvisoryLabel:
    try:
        return AdvisoryLabel(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must be an AdvisoryLabel.") from exc


def _bool_value(value: object, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field_name} must be a bool.")
    return value


def _int_value(value: object, field_name: str) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field_name} must be an int.")
    return value


def _non_negative_int_value(value: object, field_name: str) -> int:
    count = _int_value(value, field_name)
    if count < 0:
        raise ValidationError(f"{field_name} must be non-negative.")
    return count


def _label_groups(
    values: Iterable[tuple[AdvisoryLabel, Iterable[str]]],
) -> tuple[tuple[AdvisoryLabel, tuple[str, ...]], ...]:
    groups: list[tuple[AdvisoryLabel, tuple[str, ...]]] = []
    for index, value in enumerate(tuple(values)):
        try:
            label, candidate_ids = value
        except (TypeError, ValueError) as exc:
            raise ValidationError("candidate_ids_by_label entries are invalid.") from exc
        groups.append(
            (
                _advisory_label(label, f"candidate_ids_by_label[{index}][0]"),
                _string_tuple(
                    candidate_ids,
                    f"candidate_ids_by_label[{index}][1]",
                ),
            )
        )
    return tuple(groups)


def _label_counts(
    values: Iterable[tuple[AdvisoryLabel, int]],
) -> tuple[tuple[AdvisoryLabel, int], ...]:
    counts: list[tuple[AdvisoryLabel, int]] = []
    for index, value in enumerate(tuple(values)):
        try:
            label, count = value
        except (TypeError, ValueError) as exc:
            raise ValidationError("candidate_counts_by_label entries are invalid.") from exc
        counts.append(
            (
                _advisory_label(label, f"candidate_counts_by_label[{index}][0]"),
                _non_negative_int_value(
                    count,
                    f"candidate_counts_by_label[{index}][1]",
                ),
            )
        )
    return tuple(counts)


def _live_authorization_statuses(
    values: Iterable[tuple[str, AdvisoryLabel, bool, bool, bool, bool, bool]],
) -> tuple[tuple[str, AdvisoryLabel, bool, bool, bool, bool, bool], ...]:
    statuses: list[tuple[str, AdvisoryLabel, bool, bool, bool, bool, bool]] = []
    for index, value in enumerate(tuple(values)):
        try:
            (
                candidate_id,
                advisory_label,
                strategy_status_present,
                strategy_live_authorized,
                risk_status_present,
                risk_live_authorized,
                label_live_authorized,
            ) = value
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "live_authorization_statuses entries are invalid."
            ) from exc
        statuses.append(
            (
                _required_string(
                    candidate_id,
                    f"live_authorization_statuses[{index}][0]",
                ),
                _advisory_label(
                    advisory_label,
                    f"live_authorization_statuses[{index}][1]",
                ),
                _bool_value(
                    strategy_status_present,
                    f"live_authorization_statuses[{index}][2]",
                ),
                _bool_value(
                    strategy_live_authorized,
                    f"live_authorization_statuses[{index}][3]",
                ),
                _bool_value(
                    risk_status_present,
                    f"live_authorization_statuses[{index}][4]",
                ),
                _bool_value(
                    risk_live_authorized,
                    f"live_authorization_statuses[{index}][5]",
                ),
                _bool_value(
                    label_live_authorized,
                    f"live_authorization_statuses[{index}][6]",
                ),
            )
        )
    return tuple(statuses)


def _id_reason_records(
    values: Iterable[tuple[str, str | None, Iterable[str]]],
    field_name: str,
) -> tuple[tuple[str, str | None, tuple[str, ...]], ...]:
    records: list[tuple[str, str | None, tuple[str, ...]]] = []
    for index, value in enumerate(tuple(values)):
        try:
            candidate_id, reference_id, text_values = value
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{field_name} entries are invalid.") from exc
        records.append(
            (
                _required_string(candidate_id, f"{field_name}[{index}][0]"),
                _optional_string(reference_id, f"{field_name}[{index}][1]"),
                _string_tuple(text_values, f"{field_name}[{index}][2]"),
            )
        )
    return tuple(records)


def _candidate_text_records(
    values: Iterable[tuple[str, Iterable[str]]],
    field_name: str,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    records: list[tuple[str, tuple[str, ...]]] = []
    for index, value in enumerate(tuple(values)):
        try:
            candidate_id, text_values = value
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{field_name} entries are invalid.") from exc
        records.append(
            (
                _required_string(candidate_id, f"{field_name}[{index}][0]"),
                _string_tuple(text_values, f"{field_name}[{index}][1]"),
            )
        )
    return tuple(records)
