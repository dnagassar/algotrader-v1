import ast
import hashlib
import importlib.util
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest

from algotrader.errors import ValidationError


MODULE_PATH = Path("scripts/research/run_spy_sma200_research.py")
RAW_FIRST_ROW = "SPY,2025-01-01,100.00,101.00,99.00,100.00,100.00,900001"
_CSV_COLUMNS = ("symbol", "date", "open", "high", "low", "close", "adjusted_close", "volume")
_FORBIDDEN_PAYLOAD_KEY_PARTS = (
    "account",
    "allocation",
    "candidate",
    "fill",
    "order",
    "position",
    "rank",
    "recommendation",
    "score",
    "target_weight",
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
    "sqlmodel",
    "sqlite3",
    "sqlalchemy",
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
    "api",
    "broker",
    "cash",
    "client_order_id",
    "connect",
    "create_order",
    "download",
    "environ",
    "fill",
    "fit",
    "glob",
    "iterdir",
    "llm",
    "ml",
    "numpy",
    "order",
    "pandas",
    "predict",
    "Popen",
    "position",
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
    "walk",
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
    "get",
    "getenv",
    "glob",
    "iterdir",
    "makedirs",
    "mkdir",
    "os.environ.get",
    "os.getenv",
    "post",
    "predict",
    "read_csv",
    "request",
    "requests.get",
    "requests.post",
    "rglob",
    "scandir",
    "socket",
    "submit_order",
    "to_sql",
    "urlopen",
    "walk",
}
_FORBIDDEN_CALL_SUFFIXES = (
    ".connect",
    ".create_order",
    ".download",
    ".fit",
    ".get",
    ".glob",
    ".iterdir",
    ".post",
    ".predict",
    ".read_csv",
    ".request",
    ".rglob",
    ".scandir",
    ".submit_order",
    ".to_sql",
    ".urlopen",
    ".walk",
)
_CANONICAL_SIDECAR_TOP_LEVEL_KEYS = {
    "adjusted_close_available",
    "adjusted_close_source",
    "adjustment_policy",
    "baseline",
    "disclaimer",
    "limitations",
    "metrics",
    "non_claims",
    "provenance",
    "report_title",
    "return_basis",
    "rule",
    "sma_mechanics",
    "verdict",
}
_CANONICAL_METRIC_KEYS = {
    "ending_equity_buy_and_hold",
    "ending_equity_strategy",
    "exposure_ratio_buy_and_hold",
    "exposure_ratio_strategy",
    "max_drawdown_buy_and_hold",
    "max_drawdown_strategy",
    "price_return_buy_and_hold",
    "price_return_strategy",
    "starting_equity",
    "turnover_buy_and_hold",
    "turnover_strategy",
}
_CANONICAL_REPORT_LINES_IN_ORDER = (
    "# SPY SMA-200 Local Research Run",
    "Advisory/research only:",
    "## Data Source",
    "- Adjustment policy: unknown",
    "- Return basis: price_return",
    "## Assumptions",
    "## Rule",
    "## SMA Mechanics",
    "## Baseline",
    "## Metrics",
    "## Limitations",
    "## Non-Claims",
    "## Verdict",
)
_CANONICAL_SMA_MECHANICS = {
    "fully_formed_sma_observations": 6,
    "insufficient_observations": False,
    "minimum_observations": 200,
    "sma_window": 200,
    "timing": "same-close observation metadata with previous-exposure backtest convention",
}
_FORBIDDEN_OUTPUT_CONTRACT_PHRASES = (
    "account_id",
    "allocation_pct",
    "approved signal definition",
    "broker_id",
    "candidate discovery",
    "create_order",
    "execution_intent",
    "execution_plan",
    "fill_id",
    "live trading enabled",
    "order_id",
    "paper trading enabled",
    "portfolio_id",
    "position_id",
    "ranking model",
    "recommendation_score",
    "score:",
    "scoring model",
    "signal approval",
    "submit_order",
    "target_weight",
    "validated signal",
)


def load_runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("spy_sma200_runner", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_synthetic_spy_csv(
    path: Path,
    *,
    symbol: str = "SPY",
    rows: int = 205,
    blank_adjusted_close: bool = False,
    price_step: Decimal = Decimal("0.10"),
    close_overrides: dict[int, Decimal] | None = None,
    date_overrides: dict[int, str] | None = None,
    row_overrides: dict[int, dict[str, str]] | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    start = date(2025, 1, 1)
    close_overrides = close_overrides or {}
    date_overrides = date_overrides or {}
    row_overrides = row_overrides or {}
    lines = [",".join(_CSV_COLUMNS)]

    for index in range(rows):
        current_date = start + timedelta(days=index)
        price = close_overrides.get(
            index,
            Decimal("100.00") + (Decimal(index) * price_step),
        )
        high = price + Decimal("1.00")
        low = price - Decimal("1.00")
        volume = 900001 + index
        adjusted_close = "" if blank_adjusted_close else f"{price:.2f}"
        row = {
            "symbol": symbol,
            "date": date_overrides.get(index, current_date.isoformat()),
            "open": f"{price:.2f}",
            "high": f"{high:.2f}",
            "low": f"{low:.2f}",
            "close": f"{price:.2f}",
            "adjusted_close": adjusted_close,
            "volume": str(volume),
        }
        row.update(row_overrides.get(index, {}))
        lines.append(",".join(row[column] for column in _CSV_COLUMNS))

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def snapshot_path(tmp_path: Path) -> Path:
    return write_synthetic_spy_csv(tmp_path / "SPY_daily.csv")


def run_synthetic_research(
    runner: ModuleType,
    csv_path: Path,
    **kwargs: object,
) -> str:
    kwargs.setdefault("allow_outside_data_dir", True)
    return runner.run_spy_sma200_research(csv_path, **kwargs)


def test_flat_synthetic_series_metrics_are_zero_and_byte_stable(
    tmp_path: Path,
) -> None:
    runner = load_runner()
    csv_path = write_synthetic_spy_csv(
        tmp_path / "SPY_flat_daily.csv",
        rows=205,
        price_step=Decimal("0"),
    )
    first_output_path = tmp_path / "flat_spy_sma200_report.md"
    first_json_output_path = tmp_path / "flat_spy_sma200_report.json"
    second_output_path = tmp_path / "flat_spy_sma200_report_rerun.md"
    second_json_output_path = tmp_path / "flat_spy_sma200_report_rerun.json"
    fixed_kwargs = {
        "initial_equity": Decimal("10000"),
        "fee_bps": Decimal("0"),
        "slippage_bps": Decimal("0"),
        "source_name": "synthetic_flat_metric_contract",
        "source_type": "synthetic_test",
        "adjustment_policy": "unknown",
        "repo_root": tmp_path,
    }

    first_report = run_synthetic_research(
        runner,
        csv_path,
        output_path=first_output_path,
        json_output_path=first_json_output_path,
        **fixed_kwargs,
    )
    second_report = run_synthetic_research(
        runner,
        csv_path,
        output_path=second_output_path,
        json_output_path=second_json_output_path,
        **fixed_kwargs,
    )
    first_json_text = first_json_output_path.read_text(encoding="utf-8")
    sidecar = json.loads(first_json_text)

    assert first_report == second_report
    assert first_output_path.read_bytes() == second_output_path.read_bytes()
    assert first_json_output_path.read_bytes() == second_json_output_path.read_bytes()
    assert sidecar["sma_mechanics"] == {
        "fully_formed_sma_observations": 6,
        "insufficient_observations": False,
        "minimum_observations": 200,
        "sma_window": 200,
        "timing": "same-close observation metadata with previous-exposure backtest convention",
    }
    assert sidecar["metrics"] == {
        "ending_equity_buy_and_hold": "10000",
        "ending_equity_strategy": "10000",
        "exposure_ratio_buy_and_hold": "1",
        "exposure_ratio_strategy": "0",
        "max_drawdown_buy_and_hold": "0",
        "max_drawdown_strategy": "0",
        "price_return_buy_and_hold": "0",
        "price_return_strategy": "0",
        "starting_equity": "10000",
        "turnover_buy_and_hold": "1",
        "turnover_strategy": "0",
    }
    assert "- insufficient_observations: false" in first_report
    assert "- price_return_strategy: 0" in first_report
    assert "- price_return_buy_and_hold: 0" in first_report
    assert "- exposure_ratio_strategy: 0" in first_report
    assert "- turnover_strategy: 0" in first_report
    _assert_unknown_price_return_metric_contract(first_report, sidecar)
    _assert_markdown_non_claims(first_report)
    _assert_json_non_claims(sidecar)
    _assert_no_forbidden_payload_keys(sidecar)
    _assert_stable_output_excludes_paths_and_raw_rows(
        first_report,
        first_json_text,
        (
            csv_path,
            csv_path.parent,
            first_output_path,
            first_json_output_path,
            second_output_path,
            second_json_output_path,
        ),
    )


def test_controlled_breakout_metrics_use_previous_exposure_convention(
    tmp_path: Path,
) -> None:
    runner = load_runner()
    csv_path = write_synthetic_spy_csv(
        tmp_path / "SPY_breakout_daily.csv",
        rows=202,
        price_step=Decimal("0"),
        close_overrides={
            200: Decimal("300.00"),
            201: Decimal("330.00"),
        },
    )
    revised_future_csv_path = write_synthetic_spy_csv(
        tmp_path / "SPY_breakout_revised_future_daily.csv",
        rows=202,
        price_step=Decimal("0"),
        close_overrides={
            200: Decimal("300.00"),
            201: Decimal("900.00"),
        },
    )
    output_path = tmp_path / "breakout_spy_sma200_report.md"
    json_output_path = tmp_path / "breakout_spy_sma200_report.json"

    report = run_synthetic_research(
        runner,
        csv_path,
        output_path=output_path,
        json_output_path=json_output_path,
        initial_equity=Decimal("10000"),
        fee_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
        source_name="synthetic_breakout_metric_contract",
        source_type="synthetic_test",
        adjustment_policy="unknown",
        repo_root=tmp_path,
    )
    json_text = json_output_path.read_text(encoding="utf-8")
    sidecar = json.loads(json_text)
    snapshot = runner.load_historical_price_snapshot_csv(csv_path, "SPY")
    revised_future_snapshot = runner.load_historical_price_snapshot_csv(
        revised_future_csv_path,
        "SPY",
    )
    exposures = runner.build_sma_200_daily_exposures(snapshot)
    revised_future_exposures = runner.build_sma_200_daily_exposures(
        revised_future_snapshot
    )
    result = runner.run_daily_backtest(
        snapshot,
        exposures,
        runner.DailyBacktestAssumptions(
            initial_equity=Decimal("10000"),
            fee_bps=Decimal("0"),
            slippage_bps=Decimal("0"),
        ),
    )

    assert sidecar["sma_mechanics"] == {
        "fully_formed_sma_observations": 3,
        "insufficient_observations": False,
        "minimum_observations": 200,
        "sma_window": 200,
        "timing": "same-close observation metadata with previous-exposure backtest convention",
    }
    assert sidecar["metrics"] == {
        "ending_equity_buy_and_hold": "33000.0",
        "ending_equity_strategy": "11000.0",
        "exposure_ratio_buy_and_hold": "1",
        "exposure_ratio_strategy": "0.009900990099009900990099009901",
        "max_drawdown_buy_and_hold": "0",
        "max_drawdown_strategy": "0",
        "price_return_buy_and_hold": "2.3",
        "price_return_strategy": "0.1",
        "starting_equity": "10000",
        "turnover_buy_and_hold": "1",
        "turnover_strategy": "1",
    }
    assert "- price_return_strategy: 0.1" in report
    assert "- price_return_buy_and_hold: 2.3" in report
    assert "- exposure_ratio_strategy: 0.009900990099009900990099009901" in report
    assert [exposure.exposure for exposure in exposures[198:202]] == [
        Decimal("0"),
        Decimal("0"),
        Decimal("1"),
        Decimal("1"),
    ]
    assert exposures[:201] == revised_future_exposures[:201]
    assert result.points[200].date == date(2025, 7, 20)
    assert result.points[200].exposure == Decimal("1")
    assert result.points[200].asset_return == Decimal("2")
    assert result.points[200].strategy_return_before_costs == Decimal("0")
    assert result.points[200].strategy_return_after_costs == Decimal("0")
    assert result.points[200].equity == Decimal("10000")
    assert result.points[201].date == date(2025, 7, 21)
    assert result.points[201].asset_return == Decimal("0.1")
    assert result.points[201].strategy_return_before_costs == Decimal("0.1")
    assert result.points[201].strategy_return_after_costs == Decimal("0.1")
    assert result.points[201].equity == Decimal("11000.0")
    _assert_unknown_price_return_metric_contract(report, sidecar)
    _assert_markdown_non_claims(report)
    _assert_json_non_claims(sidecar)
    _assert_no_forbidden_payload_keys(sidecar)
    _assert_stable_output_excludes_paths_and_raw_rows(
        report,
        json_text,
        (
            csv_path,
            csv_path.parent,
            output_path,
            json_output_path,
            revised_future_csv_path,
        ),
    )


def test_sma200_exposures_are_derived_from_generic_replay_package(
    tmp_path: Path,
) -> None:
    runner = load_runner()
    csv_path = write_synthetic_spy_csv(
        tmp_path / "SPY_breakout_daily.csv",
        rows=202,
        price_step=Decimal("0"),
        close_overrides={
            200: Decimal("300.00"),
            201: Decimal("330.00"),
        },
    )
    snapshot = runner.load_historical_price_snapshot_csv(csv_path, "SPY")
    package = runner._build_spy_sma200_replay_package(snapshot)
    exposures = runner.build_sma_200_daily_exposures(snapshot)
    result = runner.run_daily_backtest(
        snapshot,
        exposures,
        runner.DailyBacktestAssumptions(
            initial_equity=Decimal("10000"),
            fee_bps=Decimal("0"),
            slippage_bps=Decimal("0"),
        ),
    )
    buy_and_hold_result = runner.run_daily_backtest(
        snapshot,
        runner._build_buy_and_hold_daily_exposures(snapshot),
        runner.DailyBacktestAssumptions(
            initial_equity=Decimal("10000"),
            fee_bps=Decimal("0"),
            slippage_bps=Decimal("0"),
        ),
    )

    assert [exposure.date for exposure in exposures] == [
        state.observation_date for state in package.exposure_states
    ]
    assert [int(exposure.exposure) for exposure in exposures] == [
        state.next_exposure for state in package.exposure_states
    ]
    assert package.summary.final_exposure_cumulative_return == result.total_return
    assert package.summary.final_asset_cumulative_return == (
        buy_and_hold_result.total_return
    )


def test_nonzero_cost_metrics_remain_runner_specific_after_replay_integration(
    tmp_path: Path,
) -> None:
    runner = load_runner()
    csv_path = write_synthetic_spy_csv(
        tmp_path / "SPY_breakout_daily.csv",
        rows=202,
        price_step=Decimal("0"),
        close_overrides={
            200: Decimal("300.00"),
            201: Decimal("330.00"),
        },
    )
    output_path = tmp_path / "breakout_cost_report.md"

    report = run_synthetic_research(
        runner,
        csv_path,
        output_path=output_path,
        initial_equity=Decimal("10000"),
        fee_bps=Decimal("100"),
        slippage_bps=Decimal("0"),
        source_name="synthetic_breakout_cost_boundary",
        source_type="synthetic_test",
        adjustment_policy="unknown",
        repo_root=tmp_path,
    )
    sidecar = json.loads(output_path.with_suffix(".json").read_text(encoding="utf-8"))
    snapshot = runner.load_historical_price_snapshot_csv(csv_path, "SPY")
    package = runner._build_spy_sma200_replay_package(snapshot)
    result = runner.run_daily_backtest(
        snapshot,
        runner.build_sma_200_daily_exposures(snapshot),
        runner.DailyBacktestAssumptions(
            initial_equity=Decimal("10000"),
            fee_bps=Decimal("100"),
            slippage_bps=Decimal("0"),
        ),
    )

    assert "- Fee bps: 100" in report
    assert Decimal(sidecar["metrics"]["price_return_strategy"]) == result.total_return
    assert result.total_return != package.summary.final_exposure_cumulative_return
    assert package.summary.final_exposure_cumulative_return == Decimal("0.1")
    _assert_unknown_price_return_metric_contract(report, sidecar)


def test_canonical_synthetic_output_contract_snapshot_is_stable(
    tmp_path: Path,
) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)
    expected_sha256 = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    first_output_path = tmp_path / "canonical_spy_sma200_report.md"
    first_json_output_path = tmp_path / "canonical_spy_sma200_contract.json"
    second_output_path = tmp_path / "canonical_spy_sma200_report_rerun.md"
    second_json_output_path = tmp_path / "canonical_spy_sma200_contract_rerun.json"
    fixed_kwargs = {
        "initial_equity": Decimal("10000"),
        "fee_bps": Decimal("0"),
        "slippage_bps": Decimal("0"),
        "source_name": "synthetic_contract_snapshot",
        "source_type": "synthetic_test",
        "adjustment_policy": "unknown",
        "repo_root": tmp_path,
    }

    first_report = run_synthetic_research(
        runner,
        csv_path,
        output_path=first_output_path,
        json_output_path=first_json_output_path,
        **fixed_kwargs,
    )
    second_report = run_synthetic_research(
        runner,
        csv_path,
        output_path=second_output_path,
        json_output_path=second_json_output_path,
        **fixed_kwargs,
    )
    first_json_text = first_json_output_path.read_text(encoding="utf-8")
    sidecar = json.loads(first_json_text)

    assert first_report == second_report
    assert first_output_path.read_text(encoding="utf-8") == first_report
    assert first_output_path.read_bytes() == second_output_path.read_bytes()
    assert first_json_output_path.read_bytes() == second_json_output_path.read_bytes()
    assert not first_output_path.with_suffix(".json").exists()
    assert not second_output_path.with_suffix(".json").exists()

    _assert_lines_in_order(first_report, _CANONICAL_REPORT_LINES_IN_ORDER)
    assert "- Source name: synthetic_contract_snapshot" in first_report
    assert "- Source type: synthetic_test" in first_report
    assert "- CSV file: SPY_daily.csv" in first_report
    assert f"- File SHA-256: {expected_sha256}" in first_report
    assert "- Snapshot fingerprint: " in first_report
    assert "- Date range: 2025-01-01 to 2025-07-24" in first_report
    assert "- Row count: 205" in first_report
    assert "- Adjusted close available: false" in first_report
    assert "- Adjusted close source: close_price_fallback" in first_report
    assert "- Initial equity: 10000" in first_report
    assert "- Fee bps: 0" in first_report
    assert "- Slippage bps: 0" in first_report
    assert "- sma_window: 200" in first_report
    assert "- minimum_observations: 200" in first_report
    assert "- fully_formed_sma_observations: 6" in first_report
    assert "- insufficient_observations: false" in first_report
    assert "- timing: same-close observation metadata with previous-exposure backtest convention" in first_report
    assert "- return_basis: price_return" in first_report
    assert "- price_return_strategy: " in first_report
    assert "- price_return_buy_and_hold: " in first_report
    assert "total_return" not in first_report

    assert set(sidecar) == _CANONICAL_SIDECAR_TOP_LEVEL_KEYS
    assert set(sidecar["metrics"]) == _CANONICAL_METRIC_KEYS
    assert sidecar["sma_mechanics"] == _CANONICAL_SMA_MECHANICS
    assert sidecar["report_title"] == "SPY SMA-200 Local Research Run"
    assert sidecar["adjustment_policy"] == "unknown"
    assert sidecar["return_basis"] == "price_return"
    assert sidecar["adjusted_close_available"] is False
    assert sidecar["adjusted_close_source"] == "close_price_fallback"
    assert sidecar["provenance"]["file_name"] == "SPY_daily.csv"
    assert sidecar["provenance"]["file_sha256"] == expected_sha256
    assert sidecar["provenance"]["adjustment_policy"] == "unknown"

    _assert_markdown_non_claims(first_report)
    _assert_json_non_claims(sidecar)
    _assert_no_forbidden_payload_keys(sidecar)
    for phrase in _FORBIDDEN_OUTPUT_CONTRACT_PHRASES:
        assert phrase not in first_report.lower()
        assert phrase not in first_json_text.lower()
    for path in (
        csv_path,
        csv_path.parent,
        first_output_path,
        first_json_output_path,
        second_output_path,
        second_json_output_path,
    ):
        assert str(path) not in first_report
        assert str(path) not in first_json_text
    if csv_path.drive:
        assert csv_path.drive not in first_report
        assert csv_path.drive not in first_json_text
    assert RAW_FIRST_ROW not in first_report
    assert RAW_FIRST_ROW not in first_json_text
    assert "900001" not in first_report
    assert "900001" not in first_json_text
    assert "output_path" not in first_json_text
    assert "json_output_path" not in first_json_text


def test_runner_renders_metadata_only_report_from_synthetic_spy_csv(
    tmp_path: Path,
) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)
    expected_sha256 = hashlib.sha256(csv_path.read_bytes()).hexdigest()

    report = run_synthetic_research(runner, csv_path, repo_root=tmp_path)

    assert report.startswith("# SPY SMA-200 Local Research Run\n")
    assert "Advisory/research only:" in report
    assert "not validated evidence" in report
    assert "not an approved signal" in report
    assert "not a trading recommendation" in report
    assert "not live or paper trading authority" in report
    assert "No broker, order, fill, account, position, portfolio" in report
    assert f"- File SHA-256: {expected_sha256}" in report
    assert "- Snapshot fingerprint: " in report
    assert _snapshot_fingerprint_from(report)
    assert "- CSV file: SPY_daily.csv" in report
    assert "- Date range: 2025-01-01 to 2025-07-24" in report
    assert "- Row count: 205" in report
    assert "- Adjustment policy: unknown" in report
    assert "- Return basis: price_return" in report
    assert "- Adjusted close available: false" in report
    assert "- Adjusted close source: close_price_fallback" in report
    assert "- Source name: manual_local_snapshot" in report
    assert "- Source type: manual_download" in report
    assert "- Initial equity: 10000" in report
    assert "- Fee bps: 0" in report
    assert "- Slippage bps: 0" in report
    assert "SMA window: 200 selected close observations." in report
    assert "Exposure = 1 when the selected close series > trailing 200-day SMA." in report
    assert "First 199 bars are exposure 0." in report
    assert "previous-exposure convention" in report
    assert "- sma_window: 200" in report
    assert "- minimum_observations: 200" in report
    assert "- fully_formed_sma_observations: 6" in report
    assert "- insufficient_observations: false" in report
    assert "Buy-and-hold baseline uses the same loaded local snapshot" in report
    assert "Buy-and-hold exposure is 1 on every loaded bar." in report
    assert "Total return:" not in report

    for metric in (
        "return_basis",
        "starting_equity",
        "ending_equity_strategy",
        "ending_equity_buy_and_hold",
        "price_return_strategy",
        "price_return_buy_and_hold",
        "max_drawdown_strategy",
        "max_drawdown_buy_and_hold",
        "exposure_ratio_strategy",
        "exposure_ratio_buy_and_hold",
        "turnover_strategy",
        "turnover_buy_and_hold",
    ):
        assert f"- {metric}: " in report

    assert RAW_FIRST_ROW not in report
    assert "900001" not in report
    assert str(csv_path) not in report
    assert str(csv_path.parent) not in report
    if csv_path.drive:
        assert csv_path.drive not in report
    _assert_markdown_non_claims(report)


def test_custom_assumptions_and_metadata_are_reflected_in_report(tmp_path: Path) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)

    report = run_synthetic_research(
        runner,
        csv_path,
        initial_equity=Decimal("25000.50"),
        fee_bps=Decimal("1.25"),
        slippage_bps="2.5",
        source_name="local_test_snapshot",
        source_type="synthetic_test",
        adjustment_policy="raw",
        repo_root=tmp_path,
    )

    assert "- Initial equity: 25000.50" in report
    assert "- Fee bps: 1.25" in report
    assert "- Slippage bps: 2.5" in report
    assert "- Source name: local_test_snapshot" in report
    assert "- Source type: synthetic_test" in report
    assert "- Adjustment policy: raw" in report
    assert "- Adjusted close available: false" in report
    assert "- Adjusted close source: close_price_fallback" in report
    assert "- return_basis: price_return" in report
    assert "- price_return_strategy: " in report
    assert "- total_return_strategy: " not in report


def test_total_return_label_is_used_only_for_total_return_policy(tmp_path: Path) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)

    report = run_synthetic_research(
        runner,
        csv_path,
        adjustment_policy="total_return",
        repo_root=tmp_path,
    )

    assert "- Adjustment policy: total_return" in report
    assert "- Return basis: total_return" in report
    assert "- Adjusted close available: true" in report
    assert "- Adjusted close source: true_adjusted_close" in report
    assert "- return_basis: total_return" in report
    assert "- total_return_strategy: " in report
    assert "- total_return_buy_and_hold: " in report
    assert "- price_return_strategy: " not in report


def test_unknown_adjustment_policy_reports_price_return_not_total_return(
    tmp_path: Path,
) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)

    report = run_synthetic_research(
        runner,
        csv_path,
        adjustment_policy="unknown",
        repo_root=tmp_path,
    )

    assert "- Adjustment policy: unknown" in report
    assert "- Return basis: price_return" in report
    assert "- Adjusted close available: false" in report
    assert "- Adjusted close source: close_price_fallback" in report
    assert "- return_basis: price_return" in report
    assert "- price_return_strategy: " in report
    assert "- price_return_buy_and_hold: " in report
    assert "total_return" not in report


def test_unknown_adjustment_policy_json_sidecar_reports_price_return_basis(
    tmp_path: Path,
) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)
    output_path = tmp_path / "spy_sma200_report.md"
    json_output_path = tmp_path / "spy_sma200_report.json"

    run_synthetic_research(
        runner,
        csv_path,
        adjustment_policy="unknown",
        output_path=output_path,
        repo_root=tmp_path,
    )

    sidecar = json.loads(json_output_path.read_text(encoding="utf-8"))
    assert sidecar["adjustment_policy"] == "unknown"
    assert sidecar["return_basis"] == "price_return"
    assert sidecar["adjusted_close_available"] is False
    assert sidecar["adjusted_close_source"] == "close_price_fallback"
    assert sidecar["provenance"]["adjustment_policy"] == "unknown"
    assert sidecar["sma_mechanics"] == {
        "fully_formed_sma_observations": 6,
        "insufficient_observations": False,
        "minimum_observations": 200,
        "sma_window": 200,
        "timing": "same-close observation metadata with previous-exposure backtest convention",
    }
    _assert_json_non_claims(sidecar)
    _assert_no_forbidden_payload_keys(sidecar)
    assert "price_return_strategy" in sidecar["metrics"]
    assert "price_return_buy_and_hold" in sidecar["metrics"]
    assert "total_return_strategy" not in sidecar["metrics"]
    assert "total_return_buy_and_hold" not in sidecar["metrics"]


def test_total_return_policy_requires_usable_adjusted_close(tmp_path: Path) -> None:
    runner = load_runner()
    csv_path = write_synthetic_spy_csv(
        tmp_path / "SPY_daily.csv",
        blank_adjusted_close=True,
    )
    output_path = tmp_path / "spy_sma200_report.md"

    with pytest.raises(ValidationError, match="adjusted_close"):
        runner.run_spy_sma200_research(
            csv_path,
            adjustment_policy="total_return",
            allow_outside_data_dir=True,
            output_path=output_path,
            repo_root=tmp_path,
        )

    assert not output_path.exists()
    assert not output_path.with_suffix(".json").exists()


def test_invalid_adjustment_policy_is_rejected_before_report_output(
    tmp_path: Path,
) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)
    output_path = tmp_path / "spy_sma200_report.md"

    with pytest.raises(ValidationError, match="adjustment_policy"):
        runner.run_spy_sma200_research(
            csv_path,
            adjustment_policy="split_adjusted",
            allow_outside_data_dir=True,
            output_path=output_path,
            repo_root=tmp_path,
        )

    assert not output_path.exists()
    assert not output_path.with_suffix(".json").exists()


def test_missing_csv_path_is_rejected(tmp_path: Path) -> None:
    runner = load_runner()

    with pytest.raises(ValidationError, match="CSV path is required"):
        runner.run_spy_sma200_research(None, repo_root=tmp_path)

    with pytest.raises(SystemExit):
        runner.build_parser().parse_args(())


def test_non_spy_symbol_csv_is_rejected_when_symbol_column_exists(
    tmp_path: Path,
) -> None:
    runner = load_runner()
    csv_path = write_synthetic_spy_csv(
        tmp_path / "SPY_daily.csv",
        symbol="QQQ",
    )

    with pytest.raises(ValidationError, match="symbol"):
        runner.run_spy_sma200_research(
            csv_path,
            allow_outside_data_dir=True,
            repo_root=tmp_path,
        )


@pytest.mark.parametrize(
    ("date_overrides", "row_overrides", "match"),
    (
        ({10: "2025-01-10"}, {}, "duplicate dates"),
        ({10: "2024-12-31"}, {}, "strictly increasing"),
        ({1: "2025/01/02"}, {}, "ISO date"),
        ({}, {1: {"close": ""}}, "close.*Decimal string"),
        ({}, {1: {"close": "not-a-number"}}, "close.*Decimal string"),
    ),
)
def test_synthetic_csv_validation_rejects_bad_dates_and_close_values(
    tmp_path: Path,
    date_overrides: dict[int, str],
    row_overrides: dict[int, dict[str, str]],
    match: str,
) -> None:
    runner = load_runner()
    csv_path = write_synthetic_spy_csv(
        tmp_path / "SPY_daily.csv",
        date_overrides=date_overrides,
        row_overrides=row_overrides,
    )

    with pytest.raises(ValidationError, match=match):
        runner.run_spy_sma200_research(
            csv_path,
            allow_outside_data_dir=True,
            repo_root=tmp_path,
        )


def test_output_writing_is_explicit_only(tmp_path: Path) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)
    output_path = tmp_path / "spy_sma200_report.md"
    json_output_path = tmp_path / "spy_sma200_report.json"
    implicit_output_path = tmp_path / "implicit_report.md"
    implicit_json_output_path = tmp_path / "implicit_report.json"

    report = run_synthetic_research(runner, csv_path, repo_root=tmp_path)

    assert not implicit_output_path.exists()
    assert not implicit_json_output_path.exists()

    written_report = run_synthetic_research(
        runner,
        csv_path,
        output_path=output_path,
        repo_root=tmp_path,
    )

    assert output_path.read_text(encoding="utf-8") == written_report
    assert written_report == report
    sidecar = json.loads(json_output_path.read_text(encoding="utf-8"))
    assert sidecar["report_title"] == "SPY SMA-200 Local Research Run"
    assert sidecar["adjustment_policy"] == "unknown"
    assert sidecar["return_basis"] == "price_return"
    assert sidecar["adjusted_close_available"] is False
    assert sidecar["adjusted_close_source"] == "close_price_fallback"
    assert sidecar["provenance"]["file_name"] == "SPY_daily.csv"
    assert sidecar["provenance"]["adjustment_policy"] == "unknown"
    assert sidecar["provenance"]["file_sha256"] == hashlib.sha256(
        csv_path.read_bytes()
    ).hexdigest()
    assert sidecar["non_claims"]
    assert sidecar["sma_mechanics"]["sma_window"] == 200
    assert sidecar["metrics"]["price_return_strategy"]
    assert sidecar["metrics"]["price_return_buy_and_hold"]
    assert sidecar["metrics"]["max_drawdown_strategy"]
    assert sidecar["metrics"]["max_drawdown_buy_and_hold"]
    assert sidecar["metrics"]["exposure_ratio_strategy"]
    assert sidecar["metrics"]["exposure_ratio_buy_and_hold"] == "1"
    assert sidecar["metrics"]["turnover_strategy"]
    assert sidecar["metrics"]["turnover_buy_and_hold"] == "1"
    assert "points" not in sidecar
    assert RAW_FIRST_ROW not in json_output_path.read_text(encoding="utf-8")
    assert "900001" not in json_output_path.read_text(encoding="utf-8")


def test_repeated_synthetic_runs_are_byte_identical(tmp_path: Path) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)
    first_output_path = tmp_path / "first_report.md"
    second_output_path = tmp_path / "second_report.md"

    first_report = run_synthetic_research(
        runner,
        csv_path,
        output_path=first_output_path,
        repo_root=tmp_path,
    )
    second_report = run_synthetic_research(
        runner,
        csv_path,
        output_path=second_output_path,
        repo_root=tmp_path,
    )

    assert first_report == second_report
    assert first_output_path.read_bytes() == second_output_path.read_bytes()
    assert (
        first_output_path.with_suffix(".json").read_bytes()
        == second_output_path.with_suffix(".json").read_bytes()
    )


def test_insufficient_sma200_observations_are_reported_without_rejection(
    tmp_path: Path,
) -> None:
    runner = load_runner()
    csv_path = write_synthetic_spy_csv(tmp_path / "SPY_daily.csv", rows=199)
    output_path = tmp_path / "spy_sma200_report.md"

    report = run_synthetic_research(
        runner,
        csv_path,
        output_path=output_path,
        repo_root=tmp_path,
    )
    sidecar = json.loads(output_path.with_suffix(".json").read_text(encoding="utf-8"))

    assert "- Row count: 199" in report
    assert "- fully_formed_sma_observations: 0" in report
    assert "- insufficient_observations: true" in report
    assert sidecar["sma_mechanics"]["fully_formed_sma_observations"] == 0
    assert sidecar["sma_mechanics"]["insufficient_observations"] is True
    assert sidecar["metrics"]["exposure_ratio_strategy"] == "0"


def test_output_path_json_suffix_is_rejected(tmp_path: Path) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)

    with pytest.raises(ValidationError, match="markdown report path"):
        runner.run_spy_sma200_research(
            csv_path,
            allow_outside_data_dir=True,
            output_path=tmp_path / "spy_sma200_report.json",
            repo_root=tmp_path,
        )


def test_explicit_json_output_path_requires_markdown_output(tmp_path: Path) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)
    json_output_path = tmp_path / "spy_sma200_report.json"

    with pytest.raises(ValidationError, match="requires a markdown output path"):
        runner.run_spy_sma200_research(
            csv_path,
            allow_outside_data_dir=True,
            json_output_path=json_output_path,
            repo_root=tmp_path,
        )

    assert not json_output_path.exists()


def test_explicit_json_output_path_must_use_json_suffix(tmp_path: Path) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)
    output_path = tmp_path / "spy_sma200_report.md"
    json_output_path = tmp_path / "spy_sma200_report.txt"

    with pytest.raises(ValidationError, match=r"\.json suffix"):
        runner.run_spy_sma200_research(
            csv_path,
            allow_outside_data_dir=True,
            output_path=output_path,
            json_output_path=json_output_path,
            repo_root=tmp_path,
        )

    assert not output_path.exists()
    assert not json_output_path.exists()


def test_buy_and_hold_exposure_ratio_is_one(tmp_path: Path) -> None:
    runner = load_runner()
    csv_path = write_synthetic_spy_csv(
        tmp_path / "SPY_daily.csv",
        rows=3,
    )
    snapshot = runner.load_historical_price_snapshot_csv(csv_path, "SPY")
    result = runner.run_daily_backtest(
        snapshot,
        runner._build_buy_and_hold_daily_exposures(snapshot),
        runner.DailyBacktestAssumptions(
            initial_equity=Decimal("1000"),
            fee_bps=Decimal("0"),
            slippage_bps=Decimal("0"),
        ),
    )

    assert result.exposure_ratio == Decimal("1")


def test_buy_and_hold_price_return_matches_last_over_first_minus_one_within_tolerance(
    tmp_path: Path,
) -> None:
    runner = load_runner()
    csv_path = write_synthetic_spy_csv(
        tmp_path / "SPY_daily.csv",
        rows=3,
    )
    snapshot = runner.load_historical_price_snapshot_csv(csv_path, "SPY")
    result = runner.run_daily_backtest(
        snapshot,
        runner._build_buy_and_hold_daily_exposures(snapshot),
        runner.DailyBacktestAssumptions(
            initial_equity=Decimal("1000"),
            fee_bps=Decimal("0"),
            slippage_bps=Decimal("0"),
        ),
    )
    expected_return = (
        snapshot.bars[-1].adjusted_close / snapshot.bars[0].adjusted_close
    ) - Decimal("1")

    assert abs(result.total_return - expected_return) <= Decimal("0.0000000001")


def test_buy_and_hold_max_drawdown_is_zero_on_monotonically_increasing_series(
    tmp_path: Path,
) -> None:
    runner = load_runner()
    csv_path = write_synthetic_spy_csv(
        tmp_path / "SPY_daily.csv",
        rows=3,
    )
    snapshot = runner.load_historical_price_snapshot_csv(csv_path, "SPY")
    result = runner.run_daily_backtest(
        snapshot,
        runner._build_buy_and_hold_daily_exposures(snapshot),
        runner.DailyBacktestAssumptions(
            initial_equity=Decimal("1000"),
            fee_bps=Decimal("0"),
            slippage_bps=Decimal("0"),
        ),
    )

    assert result.max_drawdown == Decimal("0")


def test_sma200_uses_same_close_metadata_without_future_leakage(
    tmp_path: Path,
) -> None:
    runner = load_runner()
    base_csv_path = write_synthetic_spy_csv(
        tmp_path / "SPY_daily_base.csv",
        rows=202,
        price_step=Decimal("0"),
        close_overrides={200: Decimal("300.00"), 201: Decimal("50.00")},
    )
    revised_future_csv_path = write_synthetic_spy_csv(
        tmp_path / "SPY_daily_revised_future.csv",
        rows=202,
        price_step=Decimal("0"),
        close_overrides={200: Decimal("300.00"), 201: Decimal("1000.00")},
    )
    base_snapshot = runner.load_historical_price_snapshot_csv(base_csv_path, "SPY")
    revised_future_snapshot = runner.load_historical_price_snapshot_csv(
        revised_future_csv_path,
        "SPY",
    )

    base_exposures = runner.build_sma_200_daily_exposures(base_snapshot)
    revised_future_exposures = runner.build_sma_200_daily_exposures(
        revised_future_snapshot
    )

    assert [exposure.exposure for exposure in base_exposures[:199]] == [
        Decimal("0")
    ] * 199
    assert base_exposures[198].date == date(2025, 7, 18)
    assert base_exposures[199].date == date(2025, 7, 19)
    assert base_exposures[199].exposure == Decimal("0")
    assert base_exposures[200].date == date(2025, 7, 20)
    assert base_exposures[200].exposure == Decimal("1")
    assert base_exposures[:201] == revised_future_exposures[:201]


def test_main_renders_report_to_stdout_by_default(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)
    monkeypatch.setattr(runner, "_REPO_ROOT", tmp_path)

    exit_code = runner.main((str(csv_path), "--allow-outside-data-dir"))
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.startswith("# SPY SMA-200 Local Research Run\n")
    assert captured.err == ""


def test_data_path_outside_snapshot_dir_requires_override(tmp_path: Path) -> None:
    runner = load_runner()
    outside_path = write_synthetic_spy_csv(tmp_path / "SPY_daily.csv")

    with pytest.raises(ValidationError, match="research_snapshots"):
        runner.run_spy_sma200_research(outside_path, repo_root=tmp_path)

    report = runner.run_spy_sma200_research(
        outside_path,
        allow_outside_data_dir=True,
        repo_root=tmp_path,
    )

    assert "- CSV file: SPY_daily.csv" in report
    assert str(outside_path.parent) not in report


def test_runner_ast_guardrails_against_network_vendor_runtime_and_discovery() -> None:
    import_violations = [
        module
        for module in _import_references()
        if _matches_forbidden_prefix(module, _FORBIDDEN_IMPORT_PREFIXES)
    ]
    call_violations = [
        name
        for name in _call_names()
        if name in _FORBIDDEN_CALL_NAMES
        or any(name.endswith(suffix) for suffix in _FORBIDDEN_CALL_SUFFIXES)
    ]

    assert import_violations == []
    assert _referenced_names().isdisjoint(_FORBIDDEN_REFERENCE_NAMES)
    assert call_violations == []


def test_runner_has_only_explicit_report_and_sidecar_output_writes() -> None:
    write_text_calls = [
        node
        for node in ast.walk(_tree())
        if isinstance(node, ast.Call) and _call_name(node.func).endswith(".write_text")
    ]
    source = MODULE_PATH.read_text(encoding="utf-8")

    assert len(write_text_calls) == 2
    assert "if checked_output_path is not None:\n        checked_output_path.write_text" in source
    assert "json_output_path.write_text" in source


def _assert_lines_in_order(text: str, expected_lines: tuple[str, ...]) -> None:
    start = 0
    for expected_line in expected_lines:
        index = text.find(expected_line, start)
        assert index >= start
        start = index + len(expected_line)


def _assert_markdown_non_claims(report: str) -> None:
    for line in (
        "Advisory/research only.",
        "Not validated evidence.",
        "Not a trading recommendation.",
        "Not an approved signal.",
        "Not live or paper trading authority.",
        "No broker, order, fill, account, position, portfolio, allocation, or target-weight behavior.",
        "No executable signals, execution plans, portfolio updates, or trading actions are created.",
    ):
        assert f"- {line}" in report


def _assert_json_non_claims(sidecar: dict[str, object]) -> None:
    assert sidecar["disclaimer"].startswith("Advisory/research only:")
    assert sidecar["non_claims"] == [
        "Advisory/research only.",
        "Not validated evidence.",
        "Not a trading recommendation.",
        "Not an approved signal.",
        "Not live or paper trading authority.",
        "No broker, order, fill, account, position, portfolio, allocation, or target-weight behavior.",
        "No executable signals, execution plans, portfolio updates, or trading actions are created.",
    ]


def _assert_no_forbidden_payload_keys(payload: object) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized_key = str(key).lower().replace("-", "_")
            assert not any(
                forbidden in normalized_key
                for forbidden in _FORBIDDEN_PAYLOAD_KEY_PARTS
            )
            _assert_no_forbidden_payload_keys(value)
    elif isinstance(payload, list):
        for value in payload:
            _assert_no_forbidden_payload_keys(value)


def _assert_unknown_price_return_metric_contract(
    report: str,
    sidecar: dict[str, object],
) -> None:
    metrics = sidecar["metrics"]
    provenance = sidecar["provenance"]
    limitations = sidecar["limitations"]
    assert isinstance(metrics, dict)
    assert isinstance(provenance, dict)
    assert isinstance(limitations, list)
    assert sidecar["adjustment_policy"] == "unknown"
    assert sidecar["return_basis"] == "price_return"
    assert sidecar["adjusted_close_available"] is False
    assert sidecar["adjusted_close_source"] == "close_price_fallback"
    assert provenance["adjustment_policy"] == "unknown"
    assert set(metrics) == _CANONICAL_METRIC_KEYS
    assert "price_return_strategy" in metrics
    assert "price_return_buy_and_hold" in metrics
    assert all("total_return" not in key for key in metrics)
    assert "- Adjustment policy: unknown" in report
    assert "- Return basis: price_return" in report
    assert "- return_basis: price_return" in report
    assert "- price_return_strategy: " in report
    assert "- price_return_buy_and_hold: " in report
    assert "- total_return_strategy: " not in report
    assert "- total_return_buy_and_hold: " not in report
    assert (
        "No dividend, corporate-action, or total-return claim is made unless explicitly supported."
        in report
    )
    assert (
        "No dividend, corporate-action, or total-return claim is made unless explicitly supported."
        in limitations
    )


def _assert_stable_output_excludes_paths_and_raw_rows(
    report: str,
    json_text: str,
    paths: tuple[Path, ...],
) -> None:
    for path in paths:
        assert str(path) not in report
        assert str(path) not in json_text
        if path.drive:
            assert path.drive not in report
            assert path.drive not in json_text

    assert RAW_FIRST_ROW not in report
    assert RAW_FIRST_ROW not in json_text
    assert "900001" not in report
    assert "900001" not in json_text
    assert "output_path" not in json_text
    assert "json_output_path" not in json_text


def _snapshot_fingerprint_from(report: str) -> str:
    prefix = "- Snapshot fingerprint: "
    for line in report.splitlines():
        if line.startswith(prefix):
            value = line.removeprefix(prefix)
            assert len(value) == 64
            int(value, 16)
            return value

    return ""


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
