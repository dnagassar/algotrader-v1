"""Synthetic planning-fixture consumer for moving-average replay tests."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from algotrader.research.moving_average import MovingAverageInput
from algotrader.research.moving_average_replay import (
    MovingAverageReplayPackage,
    build_moving_average_replay_package,
)
from tests.fixtures.research_planning import (
    build_synthetic_broad_etf_research_planning_package,
)

__all__ = [
    "build_synthetic_broad_etf_planning_replay_fixture",
    "build_synthetic_broad_etf_planning_replay_package",
]


_PLANNING_REPLAY_FIXTURE_ID = (
    "synthetic_broad_etf_planning_replay_fixture_candidate"
)
_REPLAY_ID = "synthetic_broad_etf_planning_replay_candidate"
_REPLAY_AS_OF_DATE = date(2026, 1, 21)
_REPLAY_START_DATE = date(2025, 7, 5)

_LIMITATIONS = (
    "Consumes the Phase 76 synthetic planning package only as metadata for a "
    "deterministic fixture replay.",
    "Builds the replay package through the existing public moving-average "
    "replay builder without changing replay mechanics.",
)

_NON_CLAIMS = (
    "synthetic fixture output only",
    "not source approval",
    "not universe approval",
    "not benchmark approval",
    "not cash proxy approval",
    "not methodology approval",
    "not parameter approval",
    "not evidence approval",
    "not a strategy validation artifact",
    "not trading-ready",
    "not a signal definition",
    "not an evaluator",
    "not candidate discovery",
    "not ranking, scoring, or recommendation",
    "does not create orders, positions, portfolio state, broker calls, or runtime behavior",
    "no real data ingestion",
    "no market-data, network, LLM, credential, paper, or live behavior",
)


def build_synthetic_broad_etf_planning_replay_package(
    planning_package: dict[str, object] | None = None,
) -> MovingAverageReplayPackage:
    """Build a synthetic replay package using primitive planning metadata."""

    planning = (
        build_synthetic_broad_etf_research_planning_package()
        if planning_package is None
        else planning_package
    )
    consumed_metadata = _consumed_planning_metadata(planning)
    window = _int_value(
        consumed_metadata["moving_average_window"],
        "moving_average_window",
    )

    return build_moving_average_replay_package(
        replay_id=_REPLAY_ID,
        as_of_date=_REPLAY_AS_OF_DATE,
        inputs=_synthetic_replay_inputs(window),
        window=window,
    )


def build_synthetic_broad_etf_planning_replay_fixture(
    planning_package: dict[str, object] | None = None,
    replay_package: MovingAverageReplayPackage | None = None,
) -> dict[str, object]:
    """Return a primitive metadata-only planning-to-replay fixture payload."""

    planning = (
        build_synthetic_broad_etf_research_planning_package()
        if planning_package is None
        else planning_package
    )
    consumed_metadata = _consumed_planning_metadata(planning)
    replay = (
        build_synthetic_broad_etf_planning_replay_package(planning)
        if replay_package is None
        else replay_package
    )

    if replay.window != consumed_metadata["moving_average_window"]:
        raise ValueError("replay window must match consumed planning metadata.")

    return {
        "planning_replay_fixture_id": _PLANNING_REPLAY_FIXTURE_ID,
        "as_of_date": _REPLAY_AS_OF_DATE.isoformat(),
        "planning_package": _primitive_copy(planning),
        "consumed_planning_metadata": consumed_metadata,
        "replay_package": replay.to_dict(),
        "limitations": list(_LIMITATIONS),
        "non_claims": list(_NON_CLAIMS),
    }


def _consumed_planning_metadata(
    planning_package: dict[str, object],
) -> dict[str, object]:
    research_scope = _dict_value(planning_package["research_scope"], "research_scope")
    methodology_scope = _dict_value(
        planning_package["methodology_scope"],
        "methodology_scope",
    )
    methodology = _first_dict(
        methodology_scope["methodology_candidates"],
        "methodology_candidates",
    )
    parameter_set = _first_dict(
        methodology_scope["parameter_set_candidates"],
        "parameter_set_candidates",
    )
    moving_average_windows = _int_list(
        parameter_set["moving_average_windows"],
        "moving_average_windows",
    )

    return {
        "planning_package_id": _string_value(
            planning_package["planning_package_id"],
            "planning_package_id",
        ),
        "research_scope_id": _string_value(research_scope["scope_id"], "scope_id"),
        "methodology_scope_id": _string_value(
            methodology_scope["methodology_scope_id"],
            "methodology_scope_id",
        ),
        "methodology_id": _string_value(
            methodology["methodology_id"],
            "methodology_id",
        ),
        "parameter_set_id": _string_value(
            parameter_set["parameter_set_id"],
            "parameter_set_id",
        ),
        "methodology_type": _string_value(
            methodology["methodology_type"],
            "methodology_type",
        ),
        "rule_family": _string_value(methodology["rule_family"], "rule_family"),
        "comparison_rule": _string_value(
            parameter_set["comparison_rule"],
            "comparison_rule",
        ),
        "linked_scope_ids": _string_list(
            methodology["linked_scope_ids"],
            "linked_scope_ids",
        ),
        "evidence_refs": _string_list(methodology["evidence_refs"], "evidence_refs"),
        "moving_average_window": _single_window(moving_average_windows),
    }


def _synthetic_replay_inputs(window: int) -> tuple[MovingAverageInput, ...]:
    observation_count = window + 1

    return tuple(
        MovingAverageInput(
            observation_date=_REPLAY_START_DATE + timedelta(days=index),
            value=Decimal(1000 + index),
        )
        for index in range(observation_count)
    )


def _primitive_copy(value: object) -> object:
    if type(value) is dict:
        return {
            _string_value(key, "metadata key"): _primitive_copy(item)
            for key, item in value.items()
        }

    if type(value) is list:
        return [_primitive_copy(item) for item in value]

    return value


def _first_dict(value: object, field_name: str) -> dict[str, object]:
    items = _list_value(value, field_name)
    if len(items) != 1:
        raise ValueError(f"{field_name} must contain exactly one item.")

    return _dict_value(items[0], field_name)


def _single_window(values: list[int]) -> int:
    if len(values) != 1:
        raise ValueError("moving_average_windows must contain exactly one window.")

    return values[0]


def _dict_value(value: object, field_name: str) -> dict[str, object]:
    if type(value) is not dict:
        raise ValueError(f"{field_name} must be a primitive dict.")

    return value


def _list_value(value: object, field_name: str) -> list[object]:
    if type(value) is not list:
        raise ValueError(f"{field_name} must be a primitive list.")

    return value


def _string_list(value: object, field_name: str) -> list[str]:
    return [_string_value(item, field_name) for item in _list_value(value, field_name)]


def _int_list(value: object, field_name: str) -> list[int]:
    return [_int_value(item, field_name) for item in _list_value(value, field_name)]


def _string_value(value: object, field_name: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{field_name} must be a non-empty string.")

    return value


def _int_value(value: object, field_name: str) -> int:
    if type(value) is not int or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")

    return value
