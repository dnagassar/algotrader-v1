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
SNAPSHOT_DIR = Path(".data") / "research_snapshots"
RAW_FIRST_ROW = "SPY,2025-01-01,100.00,101.00,99.00,100.00,100.00,900001"

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
    "numpy",
    "openai",
    "pandas",
    "QuantConnect",
    "quantconnect",
    "requests",
    "socket",
    "sqlmodel",
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
    "request",
    "requests",
    "rglob",
    "scheduler",
    "socket",
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
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    start = date(2025, 1, 1)
    lines = ["symbol,date,open,high,low,close,adjusted_close,volume"]

    for index in range(rows):
        current_date = start + timedelta(days=index)
        price = Decimal("100.00") + (Decimal(index) / Decimal("10"))
        high = price + Decimal("1.00")
        low = price - Decimal("1.00")
        volume = 900001 + index
        lines.append(
            ",".join(
                (
                    symbol,
                    current_date.isoformat(),
                    f"{price:.2f}",
                    f"{high:.2f}",
                    f"{low:.2f}",
                    f"{price:.2f}",
                    f"{price:.2f}",
                    str(volume),
                )
            )
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def snapshot_path(tmp_path: Path) -> Path:
    return write_synthetic_spy_csv(tmp_path / SNAPSHOT_DIR / "SPY_daily.csv")


def test_runner_renders_metadata_only_report_from_synthetic_spy_csv(
    tmp_path: Path,
) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)
    expected_sha256 = hashlib.sha256(csv_path.read_bytes()).hexdigest()

    report = runner.run_spy_sma200_research(csv_path, repo_root=tmp_path)

    assert report.startswith("# SPY SMA-200 Local Research Run\n")
    assert "Advisory only:" in report
    assert "not validated evidence" in report
    assert "not approved" in report
    assert "not a trading recommendation" in report
    assert f"- File SHA-256: {expected_sha256}" in report
    assert "- Snapshot fingerprint: " in report
    assert _snapshot_fingerprint_from(report)
    assert "- CSV file: SPY_daily.csv" in report
    assert "- Date range: 2025-01-01 to 2025-07-24" in report
    assert "- Row count: 205" in report
    assert "- Adjustment policy: adjusted_close" in report
    assert "- Source name: manual_local_snapshot" in report
    assert "- Source type: manual_download" in report
    assert "- Initial equity: 10000" in report
    assert "- Fee bps: 0" in report
    assert "- Slippage bps: 0" in report
    assert "Exposure = 1 when adjusted_close > trailing 200-day SMA." in report
    assert "First 199 bars are exposure 0." in report
    assert "previous-exposure convention" in report
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


def test_custom_assumptions_and_metadata_are_reflected_in_report(tmp_path: Path) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)

    report = runner.run_spy_sma200_research(
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
    assert "- return_basis: price_return" in report
    assert "- price_return_strategy: " in report
    assert "- total_return_strategy: " not in report


def test_total_return_label_is_used_only_for_total_return_policy(tmp_path: Path) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)

    report = runner.run_spy_sma200_research(
        csv_path,
        adjustment_policy="total_return",
        repo_root=tmp_path,
    )

    assert "- Adjustment policy: total_return" in report
    assert "- return_basis: total_return" in report
    assert "- total_return_strategy: " in report
    assert "- total_return_buy_and_hold: " in report
    assert "- price_return_strategy: " not in report


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
        tmp_path / SNAPSHOT_DIR / "SPY_daily.csv",
        symbol="QQQ",
    )

    with pytest.raises(ValidationError, match="symbol"):
        runner.run_spy_sma200_research(csv_path, repo_root=tmp_path)


def test_output_writing_is_explicit_only(tmp_path: Path) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)
    output_path = tmp_path / "spy_sma200_report.md"
    json_output_path = tmp_path / "spy_sma200_report.json"
    implicit_output_path = tmp_path / "implicit_report.md"
    implicit_json_output_path = tmp_path / "implicit_report.json"

    report = runner.run_spy_sma200_research(csv_path, repo_root=tmp_path)

    assert not implicit_output_path.exists()
    assert not implicit_json_output_path.exists()

    written_report = runner.run_spy_sma200_research(
        csv_path,
        output_path=output_path,
        repo_root=tmp_path,
    )

    assert output_path.read_text(encoding="utf-8") == written_report
    assert written_report == report
    sidecar = json.loads(json_output_path.read_text(encoding="utf-8"))
    assert sidecar["report_title"] == "SPY SMA-200 Local Research Run"
    assert sidecar["return_basis"] == "price_return"
    assert sidecar["provenance"]["file_name"] == "SPY_daily.csv"
    assert sidecar["provenance"]["file_sha256"] == hashlib.sha256(
        csv_path.read_bytes()
    ).hexdigest()
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


def test_output_path_json_suffix_is_rejected(tmp_path: Path) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)

    with pytest.raises(ValidationError, match="markdown report path"):
        runner.run_spy_sma200_research(
            csv_path,
            output_path=tmp_path / "spy_sma200_report.json",
            repo_root=tmp_path,
        )


def test_buy_and_hold_exposure_ratio_is_one(tmp_path: Path) -> None:
    runner = load_runner()
    csv_path = write_synthetic_spy_csv(
        tmp_path / SNAPSHOT_DIR / "SPY_daily.csv",
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
        tmp_path / SNAPSHOT_DIR / "SPY_daily.csv",
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
        tmp_path / SNAPSHOT_DIR / "SPY_daily.csv",
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


def test_main_renders_report_to_stdout_by_default(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)
    monkeypatch.setattr(runner, "_REPO_ROOT", tmp_path)

    exit_code = runner.main((str(csv_path),))
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.startswith("# SPY SMA-200 Local Research Run\n")
    assert captured.err == ""


def test_output_path_under_data_dir_is_rejected(tmp_path: Path) -> None:
    runner = load_runner()
    csv_path = snapshot_path(tmp_path)

    with pytest.raises(ValidationError, match="output path"):
        runner.run_spy_sma200_research(
            csv_path,
            output_path=tmp_path / ".data" / "report.md",
            repo_root=tmp_path,
        )


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
