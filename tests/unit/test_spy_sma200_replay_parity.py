import ast
import csv
import importlib.util
import json
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from types import ModuleType

from algotrader.research.moving_average import MovingAverageInput
from algotrader.research.moving_average_replay import (
    MovingAverageReplayPackage,
    build_moving_average_replay_package,
)
from conftest import NETWORK_BLOCK_MESSAGE, _network_tests_allowed


MODULE_PATH = Path("scripts/research/run_spy_sma200_research.py")
THIS_MODULE_PATH = Path(__file__)
_CSV_COLUMNS = (
    "symbol",
    "date",
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
)
_START_DATE = date(2025, 1, 1)
_WINDOW = 200
_INITIAL_EQUITY = Decimal("10000")
_ZERO = Decimal("0")
_ONE = Decimal("1")

_FORBIDDEN_FIELD_KEY_PARTS = (
    "broker",
    "order",
    "fill",
    "account",
    "position",
    "portfolio",
    "allocation",
    "target_weight",
    "submit_order",
    "execution_request",
    "recommendation",
    "ranking",
    "scoring",
)
_FORBIDDEN_EXTERNAL_MARKERS = (
    ".data",
    "http://",
    "https://",
    "www.",
    "alpaca",
    "polygon",
    "iex",
    "tiingo",
    "quandl",
    "stooq",
    "yahoo",
    "yfinance",
    "nasdaq",
    "api_key",
    "apikey",
    "secret_key",
    "access_token",
    "refresh_token",
    "credential_id",
    "account_id",
    "broker_id",
    "vendor_id",
    "client_order_id",
    "manual_local_snapshot",
)
_FORBIDDEN_AUTHORITY_PHRASES = (
    "approved signal definition",
    "live trading enabled",
    "paper trading enabled",
    "signal approval",
    "validated signal",
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
    "algotrader.runtime",
    "algotrader.scheduler",
    "algotrader.screener",
    "algotrader.signals",
    "alpaca",
    "alpaca_trade_api",
    "anthropic",
    "database",
    "duckdb",
    "httpx",
    "langchain",
    "langgraph",
    "llm",
    "notebook",
    "numpy",
    "openai",
    "os",
    "pandas",
    "QuantConnect",
    "quantconnect",
    "random",
    "requests",
    "socket",
    "sqlalchemy",
    "sqlmodel",
    "sqlite3",
    "subprocess",
    "urllib",
    "vectorbt",
    "yfinance",
)
_FORBIDDEN_REFERENCE_NAMES = {
    "AlpacaPaperBroker",
    "ExecutionIntent",
    "ExecutionPlan",
    "LocalBroker",
    "PortfolioState",
    "ProposedOrder",
    "RiskEngine",
    "RiskVerdict",
    "ValidatedSignalDefinition",
    "alpaca",
    "broker",
    "connect",
    "create_order",
    "download",
    "environ",
    "fill",
    "fit",
    "git",
    "getenv",
    "llm",
    "numpy",
    "order",
    "pandas",
    "portfolio",
    "position",
    "predict",
    "Popen",
    "random",
    "rank",
    "recommendation",
    "request",
    "requests",
    "rglob",
    "scheduler",
    "score",
    "seed",
    "socket",
    "subprocess",
    "submit_order",
    "vectorbt",
    "yfinance",
}
_FORBIDDEN_CALL_NAMES = {
    "connect",
    "create_order",
    "date.today",
    "datetime.now",
    "datetime.utcnow",
    "download",
    "environ.get",
    "fit",
    "getenv",
    "os.environ.get",
    "os.getenv",
    "post",
    "predict",
    "request",
    "requests.get",
    "requests.post",
    "socket",
    "subprocess.run",
    "submit_order",
    "urlopen",
}
_FORBIDDEN_CALL_SUFFIXES = (
    ".connect",
    ".create_order",
    ".download",
    ".fit",
    ".getenv",
    ".post",
    ".predict",
    ".request",
    ".submit_order",
    ".urlopen",
)


@dataclass(frozen=True, slots=True)
class _ParityRun:
    runner: ModuleType
    csv_path: Path
    markdown_text: str
    json_text: str
    sidecar: dict[str, object]
    package: MovingAverageReplayPackage


class _FakePytestConfig:
    def getoption(self, name: str, default: object = None) -> object:
        if name == "allow_network":
            return False
        return default


def test_flat_synthetic_series_spy_runner_and_replay_package_parity(
    tmp_path: Path,
) -> None:
    parity = _run_parity_case(tmp_path, "flat", _flat_closes(205))
    sidecar = parity.sidecar
    package = parity.package

    assert sidecar["return_basis"] == "price_return"
    assert sidecar["adjustment_policy"] == "unknown"
    assert sidecar["provenance"]["adjustment_policy"] == "unknown"
    assert sidecar["sma_mechanics"] == {
        "fully_formed_sma_observations": 6,
        "insufficient_observations": False,
        "minimum_observations": 200,
        "sma_window": 200,
        "timing": "same-close observation metadata with previous-exposure backtest convention",
    }
    _assert_sma_window_parity(sidecar, package)

    assert package.summary.observation_count == 205
    assert package.summary.final_asset_cumulative_return == Decimal("0")
    assert package.summary.final_exposure_cumulative_return == Decimal("0")
    assert all(row.current_exposure == 0 for row in package.exposure_returns)
    assert all(
        row.exposure_return in (None, Decimal("0"))
        for row in package.exposure_returns
    )
    _assert_final_cumulative_metrics_match(sidecar, package)
    _assert_research_only_boundaries(sidecar, package)


def test_controlled_breakout_spy_runner_and_replay_package_parity(
    tmp_path: Path,
) -> None:
    parity = _run_parity_case(tmp_path, "breakout", _breakout_closes())
    runner = parity.runner
    sidecar = parity.sidecar
    package = parity.package
    snapshot = runner.load_historical_price_snapshot_csv(parity.csv_path, "SPY")
    exposures = runner.build_sma_200_daily_exposures(snapshot)
    result = runner.run_daily_backtest(
        snapshot,
        exposures,
        runner.DailyBacktestAssumptions(
            initial_equity=_INITIAL_EQUITY,
            fee_bps=_ZERO,
            slippage_bps=_ZERO,
        ),
    )

    assert sidecar["sma_mechanics"] == {
        "fully_formed_sma_observations": 3,
        "insufficient_observations": False,
        "minimum_observations": 200,
        "sma_window": 200,
        "timing": "same-close observation metadata with previous-exposure backtest convention",
    }
    _assert_sma_window_parity(sidecar, package)

    breakout_index = 200
    next_index = 201
    assert package.moving_average_observations[199].moving_average == Decimal("100.00")
    assert package.moving_average_observations[199].is_above_moving_average is False
    assert package.moving_average_observations[breakout_index].is_above_moving_average
    assert package.exposure_states[breakout_index].current_exposure == 0
    assert package.exposure_states[breakout_index].next_exposure == 1
    assert package.exposure_returns[breakout_index].asset_return == Decimal("2")
    assert package.exposure_returns[breakout_index].exposure_return == Decimal("0")

    assert exposures[breakout_index].exposure == Decimal("1")
    assert int(exposures[breakout_index].exposure) == (
        package.exposure_states[breakout_index].next_exposure
    )
    assert result.points[breakout_index].asset_return == (
        package.exposure_returns[breakout_index].asset_return
    )
    assert result.points[breakout_index].strategy_return_before_costs == (
        package.exposure_returns[breakout_index].exposure_return
    )
    assert result.points[breakout_index].strategy_return_after_costs == Decimal("0")

    assert package.exposure_returns[next_index].current_exposure == 1
    assert package.exposure_returns[next_index].asset_return == Decimal("0.1")
    assert package.exposure_returns[next_index].exposure_return == Decimal("0.1")
    assert result.points[next_index].strategy_return_before_costs == (
        package.exposure_returns[next_index].exposure_return
    )
    assert result.points[next_index].strategy_return_after_costs == Decimal("0.1")

    assert package.summary.final_asset_cumulative_return == Decimal("2.3")
    assert package.summary.final_exposure_cumulative_return == Decimal("0.1")
    _assert_final_cumulative_metrics_match(sidecar, package)
    _assert_research_only_boundaries(sidecar, package)


def test_insufficient_observation_metadata_is_consistent(tmp_path: Path) -> None:
    parity = _run_parity_case(tmp_path, "insufficient", _flat_closes(199))
    sidecar = parity.sidecar
    package = parity.package

    assert sidecar["sma_mechanics"]["sma_window"] == 200
    assert sidecar["sma_mechanics"]["insufficient_observations"] is True
    assert sidecar["sma_mechanics"]["fully_formed_sma_observations"] == 0
    assert package.summary.observation_count == 199
    assert package.summary.has_available_returns is True
    assert all(
        not observation.moving_average_available
        for observation in package.moving_average_observations
    )
    assert all(state.next_exposure == 0 for state in package.exposure_states)
    assert package.summary.final_asset_cumulative_return == Decimal("0")
    assert package.summary.final_exposure_cumulative_return == Decimal("0")
    _assert_final_cumulative_metrics_match(sidecar, package)
    _assert_research_only_boundaries(sidecar, package)


def test_runner_and_replay_outputs_are_deterministic_across_repeated_builds(
    tmp_path: Path,
) -> None:
    closes = _breakout_closes()
    first = _run_parity_case(tmp_path, "deterministic", closes, output_suffix="first")
    second = _run_parity_case(tmp_path, "deterministic", closes, output_suffix="second")
    first_package_json = json.dumps(first.package.to_dict(), separators=(",", ":"))
    second_package_json = json.dumps(second.package.to_dict(), separators=(",", ":"))

    assert first.markdown_text == second.markdown_text
    assert first.json_text == second.json_text
    assert first.package == second.package
    assert first_package_json == second_package_json


def test_outputs_contain_no_forbidden_behavior_field_keys(tmp_path: Path) -> None:
    runs = _parity_runs_for_boundary_checks(tmp_path)

    for parity in runs:
        _assert_no_forbidden_field_keys(parity.sidecar)
        _assert_no_forbidden_field_keys(parity.package.to_dict())
        for phrase in _FORBIDDEN_AUTHORITY_PHRASES:
            assert phrase not in parity.markdown_text.lower()
            assert phrase not in parity.json_text.lower()


def test_outputs_contain_no_real_data_vendor_url_credential_or_account_markers(
    tmp_path: Path,
) -> None:
    runs = _parity_runs_for_boundary_checks(tmp_path)

    for parity in runs:
        package_text = json.dumps(parity.package.to_dict(), sort_keys=True)
        _assert_no_external_markers(parity.markdown_text)
        _assert_no_external_markers(parity.json_text)
        _assert_no_external_markers(package_text)
        assert str(parity.csv_path) not in parity.markdown_text
        assert str(parity.csv_path) not in parity.json_text
        assert "- Source type: synthetic_test" in parity.markdown_text
        assert parity.sidecar["provenance"]["source_type"] == "synthetic_test"


def test_normal_pytest_network_guard_remains_offline_and_credential_free() -> None:
    assert _network_tests_allowed(_FakePytestConfig(), {}) is False
    assert "offline and credential-free" in NETWORK_BLOCK_MESSAGE


def test_parity_test_module_has_no_forbidden_helper_dependencies_or_calls() -> None:
    assert [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ] == []
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)
    call_names = _call_names()

    assert call_names.isdisjoint(_FORBIDDEN_CALL_NAMES)
    assert not any(
        call_name.endswith(suffix)
        for call_name in call_names
        for suffix in _FORBIDDEN_CALL_SUFFIXES
    )


def _run_parity_case(
    tmp_path: Path,
    case_id: str,
    closes: tuple[Decimal, ...],
    *,
    output_suffix: str = "run",
) -> _ParityRun:
    runner = _load_runner()
    csv_path = _write_synthetic_spy_csv(
        tmp_path / f"synthetic_{case_id}.csv",
        closes,
    )
    output_path = tmp_path / f"synthetic_{case_id}_{output_suffix}.md"
    json_output_path = tmp_path / f"synthetic_{case_id}_{output_suffix}.json"
    markdown_text = runner.run_spy_sma200_research(
        csv_path,
        output_path=output_path,
        json_output_path=json_output_path,
        allow_outside_data_dir=True,
        adjustment_policy="unknown",
        initial_equity=_INITIAL_EQUITY,
        fee_bps=_ZERO,
        slippage_bps=_ZERO,
        source_name=f"synthetic_{case_id}_parity",
        source_type="synthetic_test",
        repo_root=tmp_path,
    )
    json_text = json_output_path.read_text(encoding="utf-8")
    package = _build_replay_package(csv_path, case_id)

    return _ParityRun(
        runner=runner,
        csv_path=csv_path,
        markdown_text=markdown_text,
        json_text=json_text,
        sidecar=json.loads(json_text),
        package=package,
    )


def _load_runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("spy_sma200_runner", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_synthetic_spy_csv(path: Path, closes: tuple[Decimal, ...]) -> Path:
    lines = [",".join(_CSV_COLUMNS)]

    for index, close in enumerate(closes):
        current_date = _START_DATE + timedelta(days=index)
        high = close + _ONE
        low = close - _ONE
        row = {
            "symbol": "SPY",
            "date": current_date.isoformat(),
            "open": str(close),
            "high": str(high),
            "low": str(low),
            "close": str(close),
            "adjusted_close": str(close),
            "volume": str(900000 + index),
        }
        lines.append(",".join(row[column] for column in _CSV_COLUMNS))

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _build_replay_package(csv_path: Path, case_id: str) -> MovingAverageReplayPackage:
    inputs = _moving_average_inputs_from_csv(csv_path)

    return build_moving_average_replay_package(
        replay_id=f"spy-sma200-parity-{case_id}",
        as_of_date=inputs[-1].observation_date,
        inputs=inputs,
        window=_WINDOW,
    )


def _moving_average_inputs_from_csv(csv_path: Path) -> tuple[MovingAverageInput, ...]:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        return tuple(
            MovingAverageInput(
                observation_date=date.fromisoformat(row["date"]),
                value=Decimal(row["close"]),
            )
            for row in csv.DictReader(handle)
        )


def _flat_closes(rows: int) -> tuple[Decimal, ...]:
    return tuple(Decimal("100.00") for _ in range(rows))


def _breakout_closes() -> tuple[Decimal, ...]:
    return (
        *(Decimal("100.00") for _ in range(200)),
        Decimal("300.00"),
        Decimal("330.00"),
    )


def _parity_runs_for_boundary_checks(tmp_path: Path) -> tuple[_ParityRun, ...]:
    return (
        _run_parity_case(tmp_path, "boundary_flat", _flat_closes(205)),
        _run_parity_case(tmp_path, "boundary_breakout", _breakout_closes()),
        _run_parity_case(tmp_path, "boundary_insufficient", _flat_closes(199)),
    )


def _assert_sma_window_parity(
    sidecar: dict[str, object],
    package: MovingAverageReplayPackage,
) -> None:
    mechanics = sidecar["sma_mechanics"]
    fully_formed_replay_rows = sum(
        1
        for observation in package.moving_average_observations
        if observation.moving_average_available
    )

    assert package.window == mechanics["sma_window"] == _WINDOW
    assert mechanics["minimum_observations"] == _WINDOW
    assert package.summary.observation_count == sidecar["provenance"]["row_count"]
    assert fully_formed_replay_rows == mechanics["fully_formed_sma_observations"]


def _assert_final_cumulative_metrics_match(
    sidecar: dict[str, object],
    package: MovingAverageReplayPackage,
) -> None:
    metrics = sidecar["metrics"]

    assert Decimal(metrics["price_return_buy_and_hold"]) == (
        package.summary.final_asset_cumulative_return
    )
    assert Decimal(metrics["price_return_strategy"]) == (
        package.summary.final_exposure_cumulative_return
    )


def _assert_research_only_boundaries(
    sidecar: dict[str, object],
    package: MovingAverageReplayPackage,
) -> None:
    runner_text = json.dumps(sidecar, sort_keys=True).lower()
    package_text = json.dumps(package.to_dict(), sort_keys=True).lower()

    assert "advisory/research only" in runner_text
    assert "not validated evidence" in runner_text
    assert "not a trading recommendation" in runner_text
    assert "not an approved signal" in runner_text
    assert "not live or paper trading authority" in runner_text
    assert sidecar["verdict"] == "Advisory only / not validated / not approved."
    assert "research-only" in package_text
    assert "not validated evidence" in package_text
    assert "not a trading recommendation" in package_text
    assert "not an approved signal" in package_text
    assert "not paper/live trading authority" in package_text


def _assert_no_forbidden_field_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = key.lower().replace("-", "_")
            assert all(
                forbidden not in normalized_key
                for forbidden in _FORBIDDEN_FIELD_KEY_PARTS
            )
            _assert_no_forbidden_field_keys(item)
        return

    if isinstance(value, list):
        for item in value:
            _assert_no_forbidden_field_keys(item)


def _assert_no_external_markers(text: str) -> None:
    normalized_text = text.lower()

    for marker in _FORBIDDEN_EXTERNAL_MARKERS:
        assert marker not in normalized_text


def _tree() -> ast.AST:
    return ast.parse(THIS_MODULE_PATH.read_text(encoding="utf-8"))


def _import_references() -> set[str]:
    imports: set[str] = set()

    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def _matches_forbidden_prefix(module: str, prefixes: tuple[str, ...]) -> bool:
    return any(
        module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
        for forbidden_prefix in prefixes
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
