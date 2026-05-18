import json
from dataclasses import is_dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, getcontext, localcontext
from enum import Enum
from pathlib import Path
from types import ModuleType

import pytest

from algotrader.research.moving_average import MovingAverageInput
from algotrader.research.moving_average_replay import (
    MovingAverageReplayPackage,
    build_moving_average_replay_package,
)


FLAT_FIXTURE = Path("tests/fixtures/moving_average_replay_contract_flat.json")
BREAKOUT_FIXTURE = Path(
    "tests/fixtures/moving_average_replay_contract_breakout.json"
)

_REQUIRED_NON_CLAIMS = (
    "not validated evidence",
    "not a strategy approval",
    "not a trading recommendation",
    "not an approved signal",
    "not paper/live trading authority",
    "no broker/order/fill/portfolio/runtime behavior",
    "exposure is a 0/1 research indicator and not allocation, target weight, position size, or portfolio instruction",
)

_FORBIDDEN_FIXTURE_SUBSTRINGS = (
    " at 0x",
    "Decimal(",
    "datetime.",
    "date(",
    "<",
    "MovingAverageInput(",
    "MovingAverageObservation(",
    "MovingAverageExposureState(",
    "ExposureReturnObservation(",
    "CumulativeReturnObservation(",
    "CumulativeReturnPathSummary(",
    "MovingAverageReplayPackage(",
)


def flat_package() -> MovingAverageReplayPackage:
    return build_moving_average_replay_package(
        replay_id="synthetic_ma_flat_contract",
        as_of_date=date(2026, 1, 17),
        inputs=input_series(("10", "10", "10", "10"), start_date=date(2026, 1, 14)),
        window=2,
    )


def breakout_package() -> MovingAverageReplayPackage:
    return build_moving_average_replay_package(
        replay_id="synthetic_ma_breakout_contract",
        as_of_date=date(2026, 1, 17),
        inputs=input_series(
            ("10", "10", "12", "15", "12", "12"),
            start_date=date(2026, 1, 12),
        ),
        window=2,
    )


def input_series(
    values: tuple[str, ...],
    *,
    start_date: date,
) -> tuple[MovingAverageInput, ...]:
    return tuple(
        MovingAverageInput(
            observation_date=start_date + timedelta(days=index),
            value=Decimal(value),
        )
        for index, value in enumerate(values)
    )


@pytest.mark.parametrize(
    ("package_builder", "fixture_path"),
    (
        (flat_package, FLAT_FIXTURE),
        (breakout_package, BREAKOUT_FIXTURE),
    ),
)
def test_replay_package_contract_matches_frozen_compact_json_fixture(
    package_builder,
    fixture_path: Path,
) -> None:
    payload = package_builder().to_dict()
    encoded = compact_json(payload)
    fixture_text = fixture_path.read_text(encoding="utf-8")

    assert encoded == fixture_text
    assert compact_json(json.loads(fixture_text)) == fixture_text
    _assert_json_primitive(payload)
    _assert_no_forbidden_serialized_values(payload)
    _assert_fixture_text_is_clean(fixture_text)
    _assert_required_research_caveats(payload)


def test_flat_contract_fixture_locks_zero_final_cumulative_returns() -> None:
    payload = flat_package().to_dict()

    assert payload["summary"]["final_asset_cumulative_return"] == "0"
    assert payload["summary"]["final_exposure_cumulative_return"] == "0"


def test_breakout_contract_fixture_pins_previous_exposure_behavior() -> None:
    payload = breakout_package().to_dict()

    assert payload["moving_average_observations"][2]["is_above_moving_average"] is True
    assert payload["exposure_states"][2]["current_exposure"] == 0
    assert payload["exposure_states"][2]["next_exposure"] == 1
    assert payload["exposure_returns"][2]["asset_return"] == "0.2"
    assert payload["exposure_returns"][2]["exposure_return"] == "0"
    assert payload["exposure_returns"][3]["current_exposure"] == 1
    assert payload["exposure_returns"][3]["exposure_return"] == "0.25"
    assert payload["exposure_states"][4]["current_exposure"] == 1
    assert payload["exposure_states"][4]["next_exposure"] == 0
    assert payload["exposure_returns"][4]["exposure_return"] == "-0.2"
    assert payload["exposure_states"][5]["current_exposure"] == 0
    assert payload["exposure_returns"][5]["exposure_return"] == "0"


def test_replay_contract_json_is_stable_under_changed_decimal_context() -> None:
    original_context = getcontext().copy()

    with localcontext() as context:
        context.prec = 9
        lower_precision_json = compact_json(breakout_package().to_dict())

    with localcontext() as context:
        context.prec = 50
        higher_precision_json = compact_json(breakout_package().to_dict())

    assert lower_precision_json == higher_precision_json
    assert getcontext().prec == original_context.prec


def compact_json(payload: object) -> str:
    return json.dumps(payload, separators=(",", ":"))


def _assert_required_research_caveats(payload: dict[str, object]) -> None:
    assert payload["limitations"]
    assert payload["non_claims"]
    assert payload["summary"]["limitations"]
    assert payload["summary"]["non_claims"]
    for claim in _REQUIRED_NON_CLAIMS:
        assert claim in payload["non_claims"]
        assert claim in payload["summary"]["non_claims"]


def _assert_fixture_text_is_clean(fixture_text: str) -> None:
    assert '"limitations":[' in fixture_text
    assert '"non_claims":[' in fixture_text
    for forbidden in _FORBIDDEN_FIXTURE_SUBSTRINGS:
        assert forbidden not in fixture_text


def _assert_json_primitive(value: object) -> None:
    if isinstance(value, dict):
        assert all(type(key) is str for key in value)
        for item in value.values():
            _assert_json_primitive(item)
        return

    if isinstance(value, list):
        for item in value:
            _assert_json_primitive(item)
        return

    assert value is None or type(value) in (str, int, bool)


def _assert_no_forbidden_serialized_values(value: object) -> None:
    assert not is_dataclass(value)
    assert not isinstance(
        value,
        (Enum, tuple, set, Decimal, date, datetime, ModuleType),
    )
    assert not callable(value)

    if isinstance(value, dict):
        for key, item in value.items():
            assert type(key) is str
            _assert_no_forbidden_serialized_values(item)
        return

    if isinstance(value, list):
        for item in value:
            _assert_no_forbidden_serialized_values(item)
        return

    assert value is None or type(value) in (str, int, bool)
