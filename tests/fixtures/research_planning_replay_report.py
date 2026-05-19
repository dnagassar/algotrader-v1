"""Primitive report fixture for the synthetic planning replay consumer."""

from __future__ import annotations

from tests.fixtures.research_planning_replay import (
    build_synthetic_broad_etf_planning_replay_fixture,
)

__all__ = [
    "build_synthetic_broad_etf_planning_replay_report",
]


_REPORT_ID = "synthetic_broad_etf_planning_replay_report_candidate"
_ALLOWED_APPROVAL_STATES = ("candidate_only", "blocked", "deferred")

_NON_CLAIMS = (
    "synthetic report output only",
    "not a strategy validation artifact",
    "not a validated research artifact",
    "not a validated signal definition",
    "not a signal evaluator",
    "not source approval",
    "not universe approval",
    "not benchmark approval",
    "not cash proxy approval",
    "not methodology approval",
    "not parameter approval",
    "not evidence approval",
    "not trading-ready",
    "not broker/runtime-facing",
    "not candidate discovery",
    "not ranking, scoring, or recommendation",
    "does not create orders, positions, portfolio state, broker calls, or runtime behavior",
    "no real data ingestion",
    "no market-data, network, LLM, credential, paper, or live behavior",
)


def build_synthetic_broad_etf_planning_replay_report(
    planning_replay_fixture: dict[str, object] | None = None,
) -> dict[str, object]:
    """Return a JSON-safe synthetic report around the Phase 78 fixture."""

    fixture = (
        build_synthetic_broad_etf_planning_replay_fixture()
        if planning_replay_fixture is None
        else planning_replay_fixture
    )
    consumed = _dict_value(
        fixture["consumed_planning_metadata"],
        "consumed_planning_metadata",
    )
    planning_package = _dict_value(fixture["planning_package"], "planning_package")
    methodology_scope = _dict_value(
        planning_package["methodology_scope"],
        "methodology_scope",
    )
    replay_package = _dict_value(fixture["replay_package"], "replay_package")
    replay_summary = _dict_value(replay_package["summary"], "summary")
    selected_window = _int_value(
        consumed["moving_average_window"],
        "moving_average_window",
    )

    if replay_package["window"] != selected_window:
        raise ValueError("replay window must match consumed planning metadata.")

    return {
        "planning_replay_report_id": _REPORT_ID,
        "source_planning_replay_fixture_id": _string_value(
            fixture["planning_replay_fixture_id"],
            "planning_replay_fixture_id",
        ),
        "synthetic_only": True,
        "advisory_only": True,
        "validates_strategy": False,
        "approves_source": False,
        "approves_universe": False,
        "approves_benchmark": False,
        "approves_cash_proxy": False,
        "approves_methodology": False,
        "approves_parameters": False,
        "approves_evidence": False,
        "trading_ready": False,
        "research_scope_id": _string_value(
            consumed["research_scope_id"],
            "research_scope_id",
        ),
        "methodology_scope_id": _string_value(
            consumed["methodology_scope_id"],
            "methodology_scope_id",
        ),
        "linked_scope_ids": _string_list(
            consumed["linked_scope_ids"],
            "linked_scope_ids",
        ),
        "evidence_refs": _string_list(
            consumed["evidence_refs"],
            "evidence_refs",
        ),
        "evidence_refs_metadata_only": True,
        "methodology_non_claims": _string_list(
            methodology_scope["non_claims"],
            "methodology_non_claims",
        ),
        "planning_approval_states": _approval_states(planning_package),
        "selected_moving_average_window": selected_window,
        "replay_package_metadata": {
            "replay_id": _string_value(replay_package["replay_id"], "replay_id"),
            "as_of_date": _string_value(replay_package["as_of_date"], "as_of_date"),
            "window": _int_value(replay_package["window"], "window"),
            "top_level_keys": list(replay_package),
            "summary_keys": list(replay_summary),
            "row_counts": {
                "inputs": len(_list_value(replay_package["inputs"], "inputs")),
                "moving_average_observations": len(
                    _list_value(
                        replay_package["moving_average_observations"],
                        "moving_average_observations",
                    )
                ),
                "exposure_states": len(
                    _list_value(replay_package["exposure_states"], "exposure_states")
                ),
                "exposure_returns": len(
                    _list_value(
                        replay_package["exposure_returns"],
                        "exposure_returns",
                    )
                ),
                "cumulative_path": len(
                    _list_value(replay_package["cumulative_path"], "cumulative_path")
                ),
            },
        },
        "non_claims": list(_NON_CLAIMS),
    }


def _approval_states(value: object) -> list[str]:
    states: list[str] = []
    seen: set[str] = set()

    for state in _approval_state_values(value):
        if state not in _ALLOWED_APPROVAL_STATES:
            raise ValueError("planning approval states must remain non-approved.")
        if state not in seen:
            seen.add(state)
            states.append(state)

    if not states:
        raise ValueError("planning approval states must be present.")

    return states


def _approval_state_values(value: object) -> list[str]:
    states: list[str] = []

    if type(value) is dict:
        approval_state = value.get("approval_state")
        if approval_state is not None:
            states.append(_string_value(approval_state, "approval_state"))
        for item in value.values():
            states.extend(_approval_state_values(item))
    elif type(value) is list:
        for item in value:
            states.extend(_approval_state_values(item))

    return states


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


def _string_value(value: object, field_name: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{field_name} must be a non-empty string.")

    return value


def _int_value(value: object, field_name: str) -> int:
    if type(value) is not int or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")

    return value
