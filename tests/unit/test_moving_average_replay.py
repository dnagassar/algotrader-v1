import ast
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

import algotrader.research.moving_average_replay as replay_module
from algotrader.errors import ValidationError
from algotrader.research.cumulative_return_summary import (
    summarize_cumulative_return_path,
)
from algotrader.research.cumulative_returns import (
    CumulativeReturnObservation,
    build_cumulative_return_path,
)
from algotrader.research.exposure_returns import build_exposure_applied_returns
from algotrader.research.moving_average import (
    MovingAverageInput,
    MovingAverageObservation,
    build_simple_moving_average_observations,
)
from algotrader.research.moving_average_exposure import (
    MovingAverageExposureState,
    build_previous_exposure_states,
)
from algotrader.research.moving_average_replay import (
    MovingAverageReplayPackage,
    build_moving_average_replay_package,
)


MODULE_PATH = Path("src/algotrader/research/moving_average_replay.py")

_REQUIRED_NON_CLAIMS = (
    "not validated evidence",
    "not a strategy approval",
    "not a trading recommendation",
    "not an approved signal",
    "not paper/live trading authority",
    "no broker/order/fill/portfolio/runtime behavior",
)

_FORBIDDEN_IMPORT_PREFIXES = (
    "aiohttp",
    "algotrader.broker",
    "algotrader.brokers",
    "algotrader.execution",
    "algotrader.llm",
    "algotrader.llms",
    "algotrader.ml",
    "algotrader.orchestration",
    "algotrader.persistence",
    "algotrader.portfolio",
    "algotrader.risk",
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "csv",
    "database",
    "duckdb",
    "httpx",
    "ipynb",
    "json",
    "langchain",
    "langgraph",
    "llm",
    "market_data",
    "notebook",
    "numpy",
    "openai",
    "os",
    "pandas",
    "pathlib",
    "persistence",
    "QuantConnect",
    "quantconnect",
    "random",
    "requests",
    "socket",
    "sqlmodel",
    "subprocess",
    "urllib",
    "vectorbt",
    "yfinance",
)

_FORBIDDEN_REFERENCE_NAMES = {
    "Account",
    "AlpacaPaperBroker",
    "ExecutionIntent",
    "ExecutionPlan",
    "LocalBroker",
    "PortfolioState",
    "ProposedOrder",
    "RiskEngine",
    "RiskVerdict",
    "ValidatedSignalDefinition",
    "account",
    "allocation",
    "alpha",
    "alpaca",
    "api",
    "benchmark",
    "beta",
    "broker",
    "cagr",
    "candidate",
    "cash",
    "client_order_id",
    "connect",
    "create_order",
    "download",
    "drawdown",
    "equity",
    "evaluator",
    "execution",
    "fill",
    "ingestion",
    "llm",
    "market_data",
    "ml",
    "notebook",
    "order",
    "pnl",
    "portfolio",
    "position",
    "rank",
    "ranking",
    "recommendation",
    "request",
    "runtime",
    "scheduler",
    "score",
    "sharpe",
    "signal",
    "submit_order",
    "target_weight",
    "vectorbt",
    "volatility",
    "win_rate",
}

_FORBIDDEN_CALL_NAMES = {
    "DictReader",
    "connect",
    "create_order",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "download",
    "dump",
    "dumps",
    "environ.get",
    "fit",
    "get",
    "getenv",
    "glob",
    "iterdir",
    "load",
    "loads",
    "makedirs",
    "mkdir",
    "open",
    "os.environ.get",
    "os.getenv",
    "post",
    "predict",
    "read",
    "read_csv",
    "read_text",
    "request",
    "rglob",
    "scandir",
    "submit_order",
    "time.time",
    "to_sql",
    "urlopen",
    "walk",
    "write",
    "write_text",
}

_FORBIDDEN_FIELD_PARTS = (
    "account",
    "allocation",
    "alpha",
    "benchmark",
    "beta",
    "cagr",
    "candidate",
    "drawdown",
    "equity",
    "execution",
    "fill",
    "order",
    "pnl",
    "portfolio",
    "position",
    "rank",
    "recommendation",
    "score",
    "sharpe",
    "target_weight",
    "volatility",
    "win_rate",
)


def value_series(values: tuple[str, ...]) -> tuple[MovingAverageInput, ...]:
    return tuple(
        MovingAverageInput(
            observation_date=date(2025, 1, 1) + timedelta(days=index),
            value=Decimal(value),
        )
        for index, value in enumerate(values)
    )


def replay_components(
    values: tuple[str, ...] = ("10", "10", "30", "33"),
    *,
    window: int = 3,
) -> dict[str, object]:
    inputs = value_series(values)
    moving_average_observations = build_simple_moving_average_observations(
        inputs,
        window=window,
    )
    exposure_states = build_previous_exposure_states(moving_average_observations)
    exposure_returns = build_exposure_applied_returns(inputs, exposure_states)
    cumulative_path = build_cumulative_return_path(exposure_returns)
    summary = summarize_cumulative_return_path(cumulative_path)

    return {
        "replay_id": "synthetic-ma-replay",
        "as_of_date": date(2025, 1, 31),
        "window": window,
        "inputs": inputs,
        "moving_average_observations": moving_average_observations,
        "exposure_states": exposure_states,
        "exposure_returns": exposure_returns,
        "cumulative_path": cumulative_path,
        "summary": summary,
        "limitations": (" research-only replay package ",),
        "non_claims": tuple(f" {claim} " for claim in _REQUIRED_NON_CLAIMS),
    }


def valid_package(**overrides: object) -> MovingAverageReplayPackage:
    values = replay_components()
    values.update(overrides)
    return MovingAverageReplayPackage(**values)


def test_replay_package_is_frozen_and_slotted() -> None:
    package = valid_package()

    assert is_dataclass(MovingAverageReplayPackage)
    assert not hasattr(package, "__dict__")
    with pytest.raises(FrozenInstanceError):
        package.replay_id = "changed"


def test_replay_package_accepts_valid_manual_construction_and_normalizes_text() -> None:
    package = valid_package()

    assert package.replay_id == "synthetic-ma-replay"
    assert package.limitations == ("research-only replay package",)
    assert package.non_claims == _REQUIRED_NON_CLAIMS
    assert package.summary == summarize_cumulative_return_path(package.cumulative_path)


@pytest.mark.parametrize("bad_replay_id", ("", "   ", True, 123, None))
def test_replay_package_rejects_empty_bool_or_non_string_replay_id(
    bad_replay_id: object,
) -> None:
    with pytest.raises(ValidationError, match="replay_id"):
        valid_package(replay_id=bad_replay_id)


def test_replay_package_rejects_datetime_as_of_date() -> None:
    with pytest.raises(ValidationError, match="plain date"):
        valid_package(as_of_date=datetime(2025, 1, 31))


@pytest.mark.parametrize("bad_window", (0, -1, True, Decimal("3"), "3"))
def test_replay_package_rejects_invalid_window_values(bad_window: object) -> None:
    with pytest.raises(ValidationError, match="window"):
        valid_package(window=bad_window)


def test_replay_package_rejects_sequence_length_mismatches() -> None:
    parts = replay_components()

    with pytest.raises(ValidationError, match="matching lengths"):
        valid_package(inputs=parts["inputs"][:-1])


def test_replay_package_rejects_sequence_date_mismatches() -> None:
    parts = replay_components()
    last_path_row = parts["cumulative_path"][-1]
    revised_last_path_row = CumulativeReturnObservation(
        observation_date=date(2025, 1, 5),
        asset_return=last_path_row.asset_return,
        exposure_return=last_path_row.exposure_return,
        asset_cumulative_return=last_path_row.asset_cumulative_return,
        exposure_cumulative_return=last_path_row.exposure_cumulative_return,
        return_available=last_path_row.return_available,
        reason=last_path_row.reason,
    )

    with pytest.raises(ValidationError, match="matching ordered observation dates"):
        valid_package(
            cumulative_path=parts["cumulative_path"][:-1] + (revised_last_path_row,)
        )


def test_replay_package_rejects_mixed_moving_average_windows() -> None:
    parts = replay_components()
    first_observation = parts["moving_average_observations"][0]
    revised_first_observation = MovingAverageObservation(
        observation_date=first_observation.observation_date,
        value=first_observation.value,
        window=2,
        moving_average=first_observation.moving_average,
        moving_average_available=first_observation.moving_average_available,
        is_above_moving_average=first_observation.is_above_moving_average,
    )

    with pytest.raises(ValidationError, match="moving_average_observations"):
        valid_package(
            moving_average_observations=(
                revised_first_observation,
                *parts["moving_average_observations"][1:],
            )
        )


def test_replay_package_rejects_mixed_exposure_state_windows() -> None:
    parts = replay_components()
    first_state = parts["exposure_states"][0]
    revised_first_state = MovingAverageExposureState(
        observation_date=first_state.observation_date,
        window=2,
        moving_average_available=first_state.moving_average_available,
        is_above_moving_average=first_state.is_above_moving_average,
        current_exposure=first_state.current_exposure,
        next_exposure=first_state.next_exposure,
        reason=first_state.reason,
    )

    with pytest.raises(ValidationError, match="exposure_states"):
        valid_package(
            exposure_states=(revised_first_state, *parts["exposure_states"][1:])
        )


def test_replay_package_rejects_non_summary_summary() -> None:
    with pytest.raises(ValidationError, match="summary"):
        valid_package(summary=object())


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("limitations", "text"),
        ("limitations", ()),
        ("limitations", ("",)),
        ("limitations", (1,)),
        ("non_claims", "text"),
        ("non_claims", ()),
        ("non_claims", ("",)),
        ("non_claims", (1,)),
        ("non_claims", ("not validated evidence",)),
    ),
)
def test_replay_package_rejects_malformed_limitations_and_non_claims(
    field_name: str,
    bad_value: object,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        valid_package(**{field_name: bad_value})


def test_replay_package_rejects_malformed_direct_construction() -> None:
    parts = replay_components()
    malformed_input = object.__new__(MovingAverageInput)

    with pytest.raises(ValidationError, match="dated observations"):
        valid_package(inputs=(malformed_input, *parts["inputs"][1:]))


def test_replay_package_to_dict_returns_json_compatible_primitives() -> None:
    payload = valid_package().to_dict()

    assert payload["replay_id"] == "synthetic-ma-replay"
    assert payload["as_of_date"] == "2025-01-31"
    assert payload["window"] == 3
    assert payload["inputs"][0] == {
        "observation_date": "2025-01-01",
        "value": "10",
    }
    assert payload["summary"]["final_exposure_cumulative_return"] == "0.1"
    _assert_json_primitive(payload)


def test_builder_builds_full_chain_from_synthetic_inputs() -> None:
    inputs = value_series(("10", "10", "30", "33"))
    package = build_moving_average_replay_package(
        replay_id="synthetic-ma-replay",
        as_of_date=date(2025, 1, 31),
        inputs=inputs,
        window=3,
    )

    moving_average_observations = build_simple_moving_average_observations(
        inputs,
        window=3,
    )
    exposure_states = build_previous_exposure_states(moving_average_observations)
    exposure_returns = build_exposure_applied_returns(inputs, exposure_states)
    cumulative_path = build_cumulative_return_path(exposure_returns)

    assert package.inputs == inputs
    assert package.moving_average_observations == moving_average_observations
    assert package.exposure_states == exposure_states
    assert package.exposure_returns == exposure_returns
    assert package.cumulative_path == cumulative_path
    assert package.summary == summarize_cumulative_return_path(cumulative_path)


def test_builder_preserves_input_ordering() -> None:
    inputs = value_series(("100", "90", "95", "120"))

    package = build_moving_average_replay_package(
        replay_id="ordering-check",
        as_of_date=date(2025, 1, 31),
        inputs=inputs,
        window=2,
    )

    assert tuple(row.value for row in package.inputs) == tuple(
        row.value for row in inputs
    )
    assert tuple(row.observation_date for row in package.exposure_returns) == tuple(
        row.observation_date for row in inputs
    )


def test_builder_uses_existing_kernels_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    original_moving_average = replay_module.build_simple_moving_average_observations
    original_exposure_states = replay_module.build_previous_exposure_states
    original_exposure_returns = replay_module.build_exposure_applied_returns
    original_cumulative_path = replay_module.build_cumulative_return_path
    original_summary = replay_module.summarize_cumulative_return_path

    def moving_average_wrapper(
        observations: tuple[MovingAverageInput, ...],
        *,
        window: int,
    ) -> tuple[MovingAverageObservation, ...]:
        calls.append("moving_average")
        return original_moving_average(observations, window=window)

    def exposure_states_wrapper(
        observations: tuple[MovingAverageObservation, ...],
    ) -> tuple[MovingAverageExposureState, ...]:
        calls.append("exposure_states")
        return original_exposure_states(observations)

    def exposure_returns_wrapper(
        values: tuple[MovingAverageInput, ...],
        exposure_states: tuple[MovingAverageExposureState, ...],
    ):
        calls.append("exposure_returns")
        return original_exposure_returns(values, exposure_states)

    def cumulative_path_wrapper(exposure_returns):
        calls.append("cumulative_path")
        return original_cumulative_path(exposure_returns)

    def summary_wrapper(cumulative_path):
        calls.append("summary")
        return original_summary(cumulative_path)

    monkeypatch.setattr(
        replay_module,
        "build_simple_moving_average_observations",
        moving_average_wrapper,
    )
    monkeypatch.setattr(
        replay_module,
        "build_previous_exposure_states",
        exposure_states_wrapper,
    )
    monkeypatch.setattr(
        replay_module,
        "build_exposure_applied_returns",
        exposure_returns_wrapper,
    )
    monkeypatch.setattr(
        replay_module,
        "build_cumulative_return_path",
        cumulative_path_wrapper,
    )
    monkeypatch.setattr(
        replay_module,
        "summarize_cumulative_return_path",
        summary_wrapper,
    )

    build_moving_average_replay_package(
        replay_id="kernel-check",
        as_of_date=date(2025, 1, 31),
        inputs=value_series(("10", "10", "30", "33")),
        window=3,
    )

    assert calls[:5] == [
        "moving_average",
        "exposure_states",
        "exposure_returns",
        "cumulative_path",
        "summary",
    ]


def test_builder_returns_immutable_tuple_outputs() -> None:
    package = build_moving_average_replay_package(
        replay_id="tuple-check",
        as_of_date=date(2025, 1, 31),
        inputs=value_series(("10", "10", "30", "33")),
        window=3,
    )

    assert isinstance(package.inputs, tuple)
    assert isinstance(package.moving_average_observations, tuple)
    assert isinstance(package.exposure_states, tuple)
    assert isinstance(package.exposure_returns, tuple)
    assert isinstance(package.cumulative_path, tuple)


def test_builder_does_not_mutate_source_inputs() -> None:
    source_inputs = list(value_series(("10", "10", "30", "33")))
    original_snapshot = tuple(
        (item.observation_date, item.value) for item in source_inputs
    )

    package = build_moving_average_replay_package(
        replay_id="mutation-check",
        as_of_date=date(2025, 1, 31),
        inputs=source_inputs,
        window=3,
    )

    assert tuple((item.observation_date, item.value) for item in source_inputs) == (
        original_snapshot
    )
    assert package.inputs == tuple(source_inputs)


def test_builder_repeated_calls_with_equivalent_inputs_produce_equal_packages() -> None:
    first = build_moving_average_replay_package(
        replay_id="repeatable",
        as_of_date=date(2025, 1, 31),
        inputs=value_series(("10", "10", "30", "33")),
        window=3,
    )
    second = build_moving_average_replay_package(
        replay_id="repeatable",
        as_of_date=date(2025, 1, 31),
        inputs=tuple(value_series(("10", "10", "30", "33"))),
        window=3,
    )

    assert first == second


def test_flat_series_builds_zero_final_cumulative_values() -> None:
    package = build_moving_average_replay_package(
        replay_id="flat",
        as_of_date=date(2025, 1, 31),
        inputs=value_series(("10", "10", "10", "10")),
        window=3,
    )

    assert package.summary.final_asset_cumulative_return == Decimal("0")
    assert package.summary.final_exposure_cumulative_return == Decimal("0")


def test_controlled_breakout_path_preserves_previous_exposure_behavior() -> None:
    package = build_moving_average_replay_package(
        replay_id="breakout",
        as_of_date=date(2025, 1, 31),
        inputs=value_series(("10", "10", "30", "33")),
        window=3,
    )

    assert package.moving_average_observations[2].is_above_moving_average is True
    assert package.exposure_returns[2].asset_return == Decimal("2")
    assert package.exposure_returns[2].exposure_return == Decimal("0")
    assert package.exposure_returns[3].current_exposure == 1
    assert package.exposure_returns[3].exposure_return == Decimal("0.1")
    assert package.summary.final_exposure_cumulative_return == Decimal("0.1")


def test_to_dict_is_deterministic_and_json_round_trips_byte_identically() -> None:
    package = valid_package()
    first_payload = package.to_dict()
    second_payload = package.to_dict()

    assert first_payload == second_payload
    first_encoded = json.dumps(first_payload, separators=(",", ":"))
    second_encoded = json.dumps(second_payload, separators=(",", ":"))
    round_tripped = json.dumps(json.loads(first_encoded), separators=(",", ":"))

    assert first_encoded == second_encoded
    assert round_tripped == first_encoded
    assert " at 0x" not in first_encoded
    assert "Decimal(" not in first_encoded
    assert "datetime." not in first_encoded
    assert "MovingAverage" not in first_encoded


def test_serialized_output_contains_no_non_primitive_objects() -> None:
    _assert_no_forbidden_serialized_values(valid_package().to_dict())


def test_package_summary_matches_summary_builder() -> None:
    package = valid_package()

    assert package.summary == summarize_cumulative_return_path(package.cumulative_path)


def test_package_final_summary_values_match_last_cumulative_path_row() -> None:
    package = valid_package()
    final_row = package.cumulative_path[-1]

    assert package.summary.final_asset_cumulative_return == (
        final_row.asset_cumulative_return
    )
    assert package.summary.final_exposure_cumulative_return == (
        final_row.exposure_cumulative_return
    )


def test_package_exposure_returns_match_current_exposure_application() -> None:
    package = valid_package()

    for exposure_return in package.exposure_returns:
        if not exposure_return.return_available:
            assert exposure_return.asset_return is None
            assert exposure_return.exposure_return is None
        elif exposure_return.current_exposure == 0:
            assert exposure_return.exposure_return == Decimal("0")
        else:
            assert exposure_return.exposure_return == exposure_return.asset_return


def test_future_value_changes_do_not_change_prior_replay_observations() -> None:
    base_package = build_moving_average_replay_package(
        replay_id="no-lookahead",
        as_of_date=date(2025, 1, 31),
        inputs=value_series(("10", "10", "30", "33")),
        window=3,
    )
    revised_package = build_moving_average_replay_package(
        replay_id="no-lookahead",
        as_of_date=date(2025, 1, 31),
        inputs=value_series(("10", "10", "30", "100")),
        window=3,
    )

    assert base_package.inputs[:3] == revised_package.inputs[:3]
    assert base_package.moving_average_observations[:3] == (
        revised_package.moving_average_observations[:3]
    )
    assert base_package.exposure_states[:3] == revised_package.exposure_states[:3]
    assert base_package.exposure_returns[:3] == revised_package.exposure_returns[:3]
    assert base_package.cumulative_path[:3] == revised_package.cumulative_path[:3]


def test_module_imports_no_vendor_network_runtime_or_trading_path_modules() -> None:
    violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]

    assert violations == []


def test_module_references_no_broker_order_signal_scoring_or_runtime_names() -> None:
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)


def test_module_makes_no_file_network_clock_vendor_or_trading_calls() -> None:
    assert _call_names().isdisjoint(_FORBIDDEN_CALL_NAMES)


def test_replay_contract_has_only_metadata_fields_and_no_forbidden_metrics() -> None:
    field_names = {field.name for field in fields(MovingAverageReplayPackage)}

    assert field_names == {
        "replay_id",
        "as_of_date",
        "window",
        "inputs",
        "moving_average_observations",
        "exposure_states",
        "exposure_returns",
        "cumulative_path",
        "summary",
        "limitations",
        "non_claims",
    }
    assert all(
        forbidden_part not in field_name
        for field_name in field_names
        for forbidden_part in _FORBIDDEN_FIELD_PARTS
    )


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

    assert value is None or type(value) in (str, int, float, bool)


def _assert_no_forbidden_serialized_values(value: object) -> None:
    assert not is_dataclass(value)
    assert not isinstance(value, (tuple, set, Decimal, date, datetime))
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

    assert value is None or type(value) in (str, int, float, bool)


def _tree() -> ast.AST:
    return ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))


def _import_references() -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def _matches_forbidden_prefix(module: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(
        module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in forbidden_prefixes
    )


def _referenced_names() -> set[str]:
    names: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)

    return names


def _call_names() -> set[str]:
    return {
        _call_name(node.func)
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""
