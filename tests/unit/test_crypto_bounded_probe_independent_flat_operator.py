from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import runpy
import pytest

from algotrader.core.crypto_bounded_probe_lifecycle import canonical_json_bytes
from algotrader.errors import ValidationError
from algotrader.execution import (
    crypto_bounded_probe_independent_flat_operator as flat_subject,
)
from algotrader.execution.crypto_bounded_probe_independent_flat_operator import (
    LEGACY_LIFECYCLE_SCHEMA_VERSION,
    TARGET_LIFECYCLE_SCHEMA_VERSION,
    run_crypto_bounded_probe_independent_flat_operator,
)


AS_OF = datetime(2026, 8, 21, 12, 5, tzinfo=UTC)
EXIT_FILLED_AT = "2026-08-21T12:00:00+00:00"
ACCOUNT_ID = "paper-account-v530"


class FlatPaperClient:
    def __init__(
        self,
        *,
        positions: list[dict[str, object]] | None = None,
        open_orders: list[dict[str, object]] | None = None,
        account: dict[str, object] | None = None,
    ) -> None:
        self.positions = [] if positions is None else positions
        self.open_orders = [] if open_orders is None else open_orders
        self.account = (
            {
                "id": ACCOUNT_ID,
                "account_id": ACCOUNT_ID,
                "account_number": "paper-number-never-persist",
                "status": "ACTIVE",
                "account_blocked": False,
                "trading_blocked": False,
            }
            if account is None
            else dict(account)
        )
        self.order_queries: list[object] = []

    def get_account(self) -> dict[str, object]:
        return dict(self.account)

    def get_positions(self) -> list[dict[str, object]]:
        return self.positions

    def get_orders(self, query: object) -> list[dict[str, object]]:
        self.order_queries.append(query)
        return self.open_orders


def _paper_env() -> dict[str, str]:
    return {
        "APP_PROFILE": "paper",
        "ALPACA_API_KEY": "not-a-real-key",
        "ALPACA_SECRET_KEY": "not-a-real-secret",
        "ALPACA_PAPER_BASE_URL": "https://paper-api.alpaca.markets",
        "ALPACA_EXPECTED_PAPER_ACCOUNT_ID": ACCOUNT_ID,
    }


def _target_lifecycle(path: Path, symbol: str) -> Path:
    helpers = runpy.run_path(
        str(
            Path(__file__).with_name(
                "test_crypto_tournament_v2_bounded_paper_probe_lifecycle_operator.py"
            )
        )
    )
    plan = helpers["_plan"](symbol)
    client = helpers["StatefulLifecycleClient"](symbol)
    receipt = helpers["_run"](
        path.parent / "v530_lifecycle_source",
        plan,
        client,
        timestamp=helpers["NOW"],
    )
    path.write_bytes(canonical_json_bytes(receipt))
    return path


@pytest.mark.parametrize("symbol", ("BTCUSD", "ETHUSD", "SOLUSD"))
def test_exact_target_emits_sanitized_flat_receipt(
    tmp_path: Path,
    symbol: str,
) -> None:
    lifecycle = _target_lifecycle(tmp_path / "lifecycle.json", symbol)
    output_root = tmp_path / "out"
    client = FlatPaperClient()

    status = run_crypto_bounded_probe_independent_flat_operator(
        symbol=symbol,
        lifecycle_path=lifecycle,
        output_root=output_root,
        timestamp=AS_OF,
        clock=lambda: AS_OF,
        env=_paper_env(),
        broker_client_factory=lambda _config: client,
        independent_flat_read_authorized=True,
        allow_network=True,
    )

    assert status["classification"] == "independent_flat_receipt_emitted"
    assert status["receipt_emitted"] is True
    assert status["broker_read_occurred"] is True
    assert status["broker_mutation_occurred"] is False
    assert status["paper_mutation_occurred"] is False
    assert status["subject"]["symbol"] == symbol
    assert status["lifecycle_binding"]["source_sha256"] == hashlib.sha256(
        lifecycle.read_bytes()
    ).hexdigest()
    assert len(client.order_queries) == 1

    receipt_path = output_root / "independent_flat_reconciliation.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["subject"]["symbol"] == symbol
    assert receipt["final_position_count"] == 0
    assert receipt["final_open_order_count"] == 0
    assert receipt["account_binding"]["expected_account_matched"] is True
    assert ACCOUNT_ID not in receipt_path.read_text(encoding="utf-8")
    assert ACCOUNT_ID not in (
        output_root / "latest_status.json"
    ).read_text(encoding="utf-8")
    manifest = json.loads(
        (output_root / "independent_flat_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["lifecycle_source_sha256"] == hashlib.sha256(
        lifecycle.read_bytes()

    ).hexdigest()
    assert len(manifest["collector_source_sha256"]) == 64

@pytest.mark.parametrize(
    ("mode", "expected_blocker"),
    (
        ("missing_newline", "target_lifecycle_source_not_canonical_json"),
        ("pretty", "target_lifecycle_source_not_canonical_json"),
        ("duplicate", "lifecycle_source_duplicate_keys"),
        ("oversize", "lifecycle_source_too_large"),
        ("invalid_utf8", "lifecycle_source_not_utf8"),
        ("not_object", "lifecycle_source_not_object"),
    ),
)
def test_target_lifecycle_source_fails_closed_before_client(
    tmp_path: Path,
    mode: str,
    expected_blocker: str,
) -> None:
    lifecycle = _target_lifecycle(tmp_path / "lifecycle.json", "BTCUSD")
    payload = lifecycle.read_bytes()
    if mode == "missing_newline":
        lifecycle.write_bytes(payload.rstrip(b"\n"))
    elif mode == "pretty":
        lifecycle.write_text(
            json.dumps(json.loads(payload), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    elif mode == "duplicate":
        lifecycle.write_bytes(
            payload.replace(
                b'"schema_version":',
                b'"schema_version":"duplicate","schema_version":',
                1,
            )
        )
    elif mode == "oversize":
        lifecycle.write_bytes(
            b"{" + b" " * flat_subject._MAX_LIFECYCLE_SOURCE_BYTES + b"}"
        )
    elif mode == "invalid_utf8":
        lifecycle.write_bytes(b"\xff")
    else:
        lifecycle.write_text("[]\n", encoding="utf-8")
    constructed = False

    def factory(_config: object) -> FlatPaperClient:
        nonlocal constructed
        constructed = True
        return FlatPaperClient()

    status = run_crypto_bounded_probe_independent_flat_operator(
        symbol="BTCUSD",
        lifecycle_path=lifecycle,
        timestamp=AS_OF,
        clock=lambda: AS_OF,
        env=_paper_env(),
        broker_client_factory=factory,
        independent_flat_read_authorized=True,
        allow_network=True,
        write_artifacts=False,
    )

    assert status["blockers"] == [expected_blocker]
    assert status["broker_read_occurred"] is False
    assert constructed is False


def test_target_lifecycle_reparse_fails_closed_before_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle = _target_lifecycle(tmp_path / "lifecycle.json", "BTCUSD")
    monkeypatch.setattr(
        flat_subject,
        "_is_link_or_reparse",
        lambda path: path == lifecycle,
    )
    constructed = False

    def factory(_config: object) -> FlatPaperClient:
        nonlocal constructed
        constructed = True
        return FlatPaperClient()

    status = run_crypto_bounded_probe_independent_flat_operator(
        symbol="BTCUSD",
        lifecycle_path=lifecycle,
        timestamp=AS_OF,
        clock=lambda: AS_OF,
        env=_paper_env(),
        broker_client_factory=factory,
        independent_flat_read_authorized=True,
        allow_network=True,
        write_artifacts=False,
    )

    assert status["blockers"] == [
        "lifecycle_source_not_regular_non_reparse_file"
    ]
    assert status["broker_read_occurred"] is False
    assert constructed is False


_MISSING = object()


@pytest.mark.parametrize(
    ("field", "value", "expected_blocker"),
    (
        ("account_blocked", _MISSING, "paper_account_blocking_fields_invalid"),
        ("trading_blocked", _MISSING, "paper_account_blocking_fields_invalid"),
        ("account_blocked", None, "paper_account_blocking_fields_invalid"),
        ("trading_blocked", "false", "paper_account_blocking_fields_invalid"),
        ("account_blocked", 0, "paper_account_blocking_fields_invalid"),
        ("blocked", None, "paper_account_blocking_fields_invalid"),
        ("blocked", 1, "paper_account_blocking_fields_invalid"),
        ("account_blocked", True, "paper_account_trading_blocked"),
        ("trading_blocked", True, "paper_account_trading_blocked"),
        ("blocked", True, "paper_account_trading_blocked"),
    ),
)
def test_ambiguous_or_blocked_account_flags_never_emit_receipt(
    tmp_path: Path,
    field: str,
    value: object,
    expected_blocker: str,
) -> None:
    lifecycle = _target_lifecycle(tmp_path / "lifecycle.json", "BTCUSD")
    account: dict[str, object] = {
        "id": ACCOUNT_ID,
        "account_id": ACCOUNT_ID,
        "account_number": "paper-number-never-persist",
        "status": "ACTIVE",
        "account_blocked": False,
        "trading_blocked": False,
    }
    if value is _MISSING:
        account.pop(field, None)
    else:
        account[field] = value
    status = run_crypto_bounded_probe_independent_flat_operator(
        symbol="BTCUSD",
        lifecycle_path=lifecycle,
        timestamp=AS_OF,
        clock=lambda: AS_OF,
        env=_paper_env(),
        broker_client_factory=lambda _config: FlatPaperClient(account=account),
        independent_flat_read_authorized=True,
        allow_network=True,
        write_artifacts=False,
    )

    assert status["classification"] == "blocked_by_flat_reconciliation"
    assert expected_blocker in status["blockers"]
    assert status["receipt_emitted"] is False


def test_minimal_target_counterfeit_is_rejected_before_client(
    tmp_path: Path,
) -> None:
    lifecycle = tmp_path / "counterfeit.json"
    lifecycle.write_text(
        json.dumps(
            {
                "schema_version": TARGET_LIFECYCLE_SCHEMA_VERSION,
                "record_type": (
                    "crypto_tournament_v2_bounded_paper_probe_lifecycle"
                ),
                "subject": {
                    "asset_class": "crypto",
                    "symbol": "BTCUSD",
                    "environment": "alpaca_paper",
                },
                "outcome_classification": "filled_exit_confirmed",
                "exit_final_order": {
                    "symbol": "BTCUSD",
                    "status": "filled",
                    "filled_at": EXIT_FILLED_AT,
                },
            }
        ),
        encoding="utf-8",
    )
    lifecycle.write_bytes(
        canonical_json_bytes(json.loads(lifecycle.read_bytes()))
    )
    constructed = False

    def factory(_config: object) -> FlatPaperClient:
        nonlocal constructed
        constructed = True
        return FlatPaperClient()

    status = run_crypto_bounded_probe_independent_flat_operator(
        symbol="BTCUSD",
        lifecycle_path=lifecycle,
        timestamp=AS_OF,
        clock=lambda: AS_OF,
        env=_paper_env(),
        broker_client_factory=factory,
        independent_flat_read_authorized=True,
        allow_network=True,
        write_artifacts=False,
    )

    assert "target_lifecycle_receipt_invalid" in status["blockers"]
    assert status["broker_read_occurred"] is False
    assert constructed is False
def test_legacy_btc_lifecycle_is_accepted(tmp_path: Path) -> None:
    lifecycle = tmp_path / "legacy.json"
    lifecycle.write_text(
        json.dumps(
            {
                "schema_version": LEGACY_LIFECYCLE_SCHEMA_VERSION,
                "symbol": "BTCUSD",
                "outcome_classification": "filled_exit_confirmed",
                "exit_final_order": {
                    "status": "filled",
                    "filled_at": EXIT_FILLED_AT,
                },
            }
        ),
        encoding="utf-8",
    )

    status = run_crypto_bounded_probe_independent_flat_operator(
        symbol="BTCUSD",
        lifecycle_path=lifecycle,
        output_root=tmp_path / "out",
        timestamp=AS_OF,
        clock=lambda: AS_OF,
        env=_paper_env(),
        broker_client_factory=lambda _config: FlatPaperClient(),
        independent_flat_read_authorized=True,
        allow_network=True,
    )

    assert status["classification"] == "independent_flat_receipt_emitted"


def test_invalid_target_rejected_before_client_construction(
    tmp_path: Path,
) -> None:
    constructed = False

    def factory(_config: object) -> FlatPaperClient:
        nonlocal constructed
        constructed = True
        return FlatPaperClient()

    with pytest.raises(
        ValidationError,
        match="target symbol is unsupported",
    ):
        run_crypto_bounded_probe_independent_flat_operator(
            symbol="DOGEUSD",
            lifecycle_path=tmp_path / "absent.json",
            timestamp=AS_OF,
            env=_paper_env(),
            broker_client_factory=factory,
            independent_flat_read_authorized=True,
            allow_network=True,
            write_artifacts=False,
        )

    assert constructed is False


def test_authorization_and_network_switches_fail_before_client(
    tmp_path: Path,
) -> None:
    lifecycle = _target_lifecycle(
        tmp_path / "lifecycle.json",
        "SOLUSD",
    )
    constructed = False

    def factory(_config: object) -> FlatPaperClient:
        nonlocal constructed
        constructed = True
        return FlatPaperClient()

    status = run_crypto_bounded_probe_independent_flat_operator(
        symbol="SOLUSD",
        lifecycle_path=lifecycle,
        timestamp=AS_OF,
        clock=lambda: AS_OF,
        env=_paper_env(),
        broker_client_factory=factory,
        write_artifacts=False,
    )

    assert status["classification"] == "blocked_before_broker_read"
    assert status["blockers"] == [
        "independent_flat_read_authorization_required",
        "allow_network_switch_required",
    ]
    assert status["broker_read_occurred"] is False
    assert constructed is False


def test_lifecycle_symbol_mismatch_fails_before_client(
    tmp_path: Path,
) -> None:
    lifecycle = _target_lifecycle(
        tmp_path / "lifecycle.json",
        "ETHUSD",
    )
    constructed = False

    def factory(_config: object) -> FlatPaperClient:
        nonlocal constructed
        constructed = True
        return FlatPaperClient()

    status = run_crypto_bounded_probe_independent_flat_operator(
        symbol="SOLUSD",
        lifecycle_path=lifecycle,
        timestamp=AS_OF,
        clock=lambda: AS_OF,
        env=_paper_env(),
        broker_client_factory=factory,
        independent_flat_read_authorized=True,
        allow_network=True,
        write_artifacts=False,
    )

    assert "lifecycle_selected_symbol_mismatch" in status["blockers"]
    assert constructed is False


def test_flat_observation_cannot_precede_exit_fill(
    tmp_path: Path,
) -> None:
    lifecycle = _target_lifecycle(
        tmp_path / "lifecycle.json",
        "BTCUSD",
    )
    constructed = False

    def factory(_config: object) -> FlatPaperClient:
        nonlocal constructed
        constructed = True
        return FlatPaperClient()

    status = run_crypto_bounded_probe_independent_flat_operator(
        symbol="BTCUSD",
        lifecycle_path=lifecycle,
        timestamp="2026-08-13T00:04:59Z",
        clock=lambda: datetime.fromisoformat("2026-08-13T00:04:59+00:00"),
        env=_paper_env(),
        broker_client_factory=factory,
        independent_flat_read_authorized=True,
        allow_network=True,
        write_artifacts=False,
    )

    assert "flat_observation_precedes_exit_fill" in status["blockers"]
    assert constructed is False


@pytest.mark.parametrize(
    ("client", "expected_blocker"),
    (
        (
            FlatPaperClient(
                positions=[
                    {"symbol": "ETHUSD", "qty": "0.1", "side": "long"}
                ]
            ),
            "account_wide_position_observed",
        ),
        (
            FlatPaperClient(
                open_orders=[
                    {
                        "symbol": "BTCUSD",
                        "status": "new",
                        "client_order_id": "open-order",
                    }
                ]
            ),
            "account_wide_open_order_observed",
        ),
    ),
)
def test_nonflat_account_never_emits_receipt(
    tmp_path: Path,
    client: FlatPaperClient,
    expected_blocker: str,
) -> None:
    lifecycle = _target_lifecycle(
        tmp_path / "lifecycle.json",
        "BTCUSD",
    )
    output_root = tmp_path / "out"

    status = run_crypto_bounded_probe_independent_flat_operator(
        symbol="BTCUSD",
        lifecycle_path=lifecycle,
        output_root=output_root,
        timestamp=AS_OF,
        clock=lambda: AS_OF,
        env=_paper_env(),
        broker_client_factory=lambda _config: client,
        independent_flat_read_authorized=True,
        allow_network=True,
    )

    assert status["classification"] == "blocked_by_flat_reconciliation"
    assert expected_blocker in status["blockers"]
    assert status["receipt_emitted"] is False
    assert not (
        output_root / "independent_flat_reconciliation.json"
    ).exists()


def test_failed_newer_read_supersedes_prior_mutable_latest_receipt(
    tmp_path: Path,
) -> None:
    lifecycle = _target_lifecycle(
        tmp_path / "lifecycle.json",
        "BTCUSD",
    )
    output_root = tmp_path / "out"
    first = run_crypto_bounded_probe_independent_flat_operator(
        symbol="BTCUSD",
        lifecycle_path=lifecycle,
        output_root=output_root,
        timestamp=AS_OF,
        clock=lambda: AS_OF,
        env=_paper_env(),
        broker_client_factory=lambda _config: FlatPaperClient(),
        independent_flat_read_authorized=True,
        allow_network=True,
    )
    assert first["classification"] == "independent_flat_receipt_emitted"

    blocked = run_crypto_bounded_probe_independent_flat_operator(
        symbol="BTCUSD",
        lifecycle_path=lifecycle,
        output_root=output_root,
        timestamp="2026-08-21T12:06:00Z",
        clock=lambda: datetime.fromisoformat("2026-08-21T12:06:00+00:00"),
        env=_paper_env(),
        broker_client_factory=lambda _config: FlatPaperClient(
            positions=[
                {"symbol": "BTCUSD", "qty": "0.1", "side": "long"}
            ]
        ),
        independent_flat_read_authorized=True,
        allow_network=True,
    )

    assert blocked["classification"] == "blocked_by_flat_reconciliation"
    assert not (
        output_root / "independent_flat_reconciliation.json"
    ).exists()
    superseded_names = {
        path.name for path in (output_root / "superseded").iterdir()
    }
    assert any(
        name.endswith("-independent_flat_reconciliation.json")
        for name in superseded_names
    )


def test_live_endpoint_is_rejected_before_client(tmp_path: Path) -> None:
    lifecycle = _target_lifecycle(
        tmp_path / "lifecycle.json",
        "SOLUSD",
    )
    env = _paper_env()
    env["APCA_API_BASE_URL"] = "https://api.alpaca.markets"
    constructed = False

    def factory(_config: object) -> FlatPaperClient:
        nonlocal constructed
        constructed = True
        return FlatPaperClient()

    status = run_crypto_bounded_probe_independent_flat_operator(
        symbol="SOLUSD",
        lifecycle_path=lifecycle,
        timestamp=AS_OF,
        clock=lambda: AS_OF,
        env=env,
        broker_client_factory=factory,
        independent_flat_read_authorized=True,
        allow_network=True,
        write_artifacts=False,
    )

    assert "live_endpoint_indicator" in status["blockers"]
    assert constructed is False


def test_wrapper_has_exact_read_only_boundary() -> None:
    text = Path(
        "scripts/run_crypto_bounded_probe_independent_flat_operator.ps1"
    ).read_text(encoding="utf-8")

    assert '[ValidateSet("BTCUSD", "ETHUSD", "SOLUSD")]' in text
    assert "-IndependentFlatReadAuthorized" not in text
    assert "$IndependentFlatReadAuthorized.IsPresent" in text
    assert "$AllowNetwork.IsPresent" in text
    assert "broker_mutation_occurred=false" in text
    assert "paper_mutation_occurred=false" in text
    assert "live_endpoint_touched=false" in text
    assert '"-I",' in text
    assert "$TrustedPythonPath" in text
    assert "Get-AuthenticodeSignature" in text
    assert "Python Software Foundation" in text
    assert "Test-ReparsePointFreePath" in text
    assert "$ProcessInfo.Environment.Remove($Name)" in text
    assert "& python" not in text
    assert '$ProcessInfo.FileName = "python"' not in text
    for forbidden in (
        "submit_order",
        "cancel_order",
        "replace_order",
        "close_position",
        "close_all_positions",
    ):
        assert forbidden not in text


def test_flat_wrapper_ignores_python_startup_injection_before_safe_block(
    tmp_path: Path,
) -> None:
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell is None:
        pytest.skip("PowerShell is required to verify the flat wrapper.")
    injection_root = tmp_path / "python-injection"
    injection_root.mkdir()
    marker = tmp_path / "startup-marker.txt"
    (injection_root / "sitecustomize.py").write_text(
        "import os, pathlib\n"
        "pathlib.Path(os.environ['PYTHON_STARTUP_MARKER']).write_text("
        "'executed', encoding='utf-8')\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(injection_root),
            "PYTHON_STARTUP_MARKER": str(marker),
            "APP_PROFILE": "paper",
            "ALPACA_API_KEY": "flat-wrapper-key-never-print",
            "ALPACA_SECRET_KEY": "flat-wrapper-secret-never-print",
            "ALPACA_EXPECTED_PAPER_ACCOUNT_ID": (
                "flat-wrapper-account-never-print"
            ),
            "ALPACA_PAPER_BASE_URL": (
                "https://paper-api.alpaca.markets"
            ),
        }
    )
    for name in (
        "ALPACA_BASE_URL",
        "APCA_API_BASE_URL",
        "ALGO_TRADER_ALLOW_NETWORK_TESTS",
        "RUN_ALPACA_PAPER_INTEGRATION_TESTS",
        "PYTEST_NETWORK",
        "NETWORK_TESTS",
        "ALLOW_NETWORK_TESTS",
        "PYTEST_ADDOPTS",
    ):
        env.pop(name, None)

    result = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(
                Path(
                    "scripts/"
                    "run_crypto_bounded_probe_independent_flat_operator.ps1"
                ).resolve()
            ),
            "-TargetSymbol",
            "BTCUSD",
            "-IndependentFlatReadAuthorized",
            "-AllowNetwork",
            "-LifecyclePath",
            str(tmp_path / "missing-lifecycle.json"),
            "-OutputRoot",
            str(tmp_path / "out"),
        ],
        cwd=Path.cwd(),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=30,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 2, combined
    assert "blocked_before_broker_read" in combined
    assert not marker.exists()
    for secret in (
        "flat-wrapper-key-never-print",
        "flat-wrapper-secret-never-print",
        "flat-wrapper-account-never-print",
    ):
        assert secret not in combined


class SequenceClock:
    def __init__(self, *values: datetime) -> None:
        self.values = list(values)
        self.last = values[-1]

    def __call__(self) -> datetime:
        if self.values:
            self.last = self.values.pop(0)
        return self.last


def test_flat_receipt_uses_trusted_read_completion_time(
    tmp_path: Path,
) -> None:
    lifecycle = _target_lifecycle(
        tmp_path / "lifecycle.json",
        "BTCUSD",
    )
    completed_at = AS_OF + timedelta(seconds=30)
    clock = SequenceClock(AS_OF, completed_at)
    output_root = tmp_path / "out"

    status = run_crypto_bounded_probe_independent_flat_operator(
        symbol="BTCUSD",
        lifecycle_path=lifecycle,
        output_root=output_root,
        timestamp=AS_OF - timedelta(minutes=1),
        clock=clock,
        env=_paper_env(),
        broker_client_factory=lambda _config: FlatPaperClient(),
        independent_flat_read_authorized=True,
        allow_network=True,
    )

    assert status["classification"] == "independent_flat_receipt_emitted"
    assert status["as_of"] == completed_at.isoformat()
    receipt = json.loads(
        (output_root / "independent_flat_reconciliation.json").read_bytes()
    )
    assert receipt["as_of"] == completed_at.isoformat()


def test_flat_trusted_clock_regression_blocks_receipt(
    tmp_path: Path,
) -> None:
    lifecycle = _target_lifecycle(
        tmp_path / "lifecycle.json",
        "ETHUSD",
    )
    output_root = tmp_path / "out"
    clock = SequenceClock(AS_OF, AS_OF - timedelta(microseconds=1))

    status = run_crypto_bounded_probe_independent_flat_operator(
        symbol="ETHUSD",
        lifecycle_path=lifecycle,
        output_root=output_root,
        timestamp=AS_OF,
        clock=clock,
        env=_paper_env(),
        broker_client_factory=lambda _config: FlatPaperClient(),
        independent_flat_read_authorized=True,
        allow_network=True,
    )

    assert status["classification"] == "blocked_by_flat_reconciliation"
    assert "trusted_clock_invalid" in status["blockers"]
    assert status["receipt_emitted"] is False
    assert not (
        output_root / "independent_flat_reconciliation.json"
    ).exists()


def test_flat_future_not_before_claim_blocks_before_client(
    tmp_path: Path,
) -> None:
    lifecycle = _target_lifecycle(
        tmp_path / "lifecycle.json",
        "SOLUSD",
    )
    constructed = False

    def factory(_config: object) -> FlatPaperClient:
        nonlocal constructed
        constructed = True
        return FlatPaperClient()

    status = run_crypto_bounded_probe_independent_flat_operator(
        symbol="SOLUSD",
        lifecycle_path=lifecycle,
        timestamp=AS_OF + timedelta(seconds=1),
        clock=lambda: AS_OF,
        env=_paper_env(),
        broker_client_factory=factory,
        independent_flat_read_authorized=True,
        allow_network=True,
        write_artifacts=False,
    )

    assert "trusted_clock_precedes_requested_not_before" in (
        status["blockers"]
    )
    assert status["broker_read_occurred"] is False
    assert constructed is False


def test_flat_open_order_limit_is_treated_as_incomplete(
    tmp_path: Path,
) -> None:
    lifecycle = _target_lifecycle(
        tmp_path / "lifecycle.json",
        "BTCUSD",
    )
    orders = [
        {
            "symbol": "AAPL",
            "status": "new",
            "client_order_id": f"foreign-{index}",
        }
        for index in range(100)
    ]
    client = FlatPaperClient(open_orders=orders)

    status = run_crypto_bounded_probe_independent_flat_operator(
        symbol="BTCUSD",
        lifecycle_path=lifecycle,
        timestamp=AS_OF,
        clock=lambda: AS_OF,
        env=_paper_env(),
        broker_client_factory=lambda _config: client,
        independent_flat_read_authorized=True,
        allow_network=True,
        write_artifacts=False,
    )

    assert status["classification"] == "blocked_by_flat_reconciliation"
    assert "account_wide_open_order_scan_may_be_truncated" in (
        status["blockers"]
    )
    assert status["final_open_order_count"] == 100
    query = client.order_queries[-1]
    assert getattr(query, "limit", None) == 100
    assert getattr(query, "status_filter", None) == "open"
    assert getattr(query, "asset_class_filter", None) == ""
    assert getattr(query, "symbol_filter", None) == ""


@pytest.mark.parametrize(
    ("name", "value"),
    (
        ("NETWORK_TESTS", "yes"),
        ("ALLOW_NETWORK_TESTS", "on"),
        ("PYTEST_ADDOPTS", "-q --allow-network"),
    ),
)
def test_flat_direct_invocation_rejects_all_network_test_flags(
    tmp_path: Path,
    name: str,
    value: str,
) -> None:
    lifecycle = _target_lifecycle(
        tmp_path / "lifecycle.json",
        "BTCUSD",
    )
    constructed = False

    def factory(_config: object) -> FlatPaperClient:
        nonlocal constructed
        constructed = True
        return FlatPaperClient()

    status = run_crypto_bounded_probe_independent_flat_operator(
        symbol="BTCUSD",
        lifecycle_path=lifecycle,
        timestamp=AS_OF,
        clock=lambda: AS_OF,
        env={**_paper_env(), name: value},
        broker_client_factory=factory,
        independent_flat_read_authorized=True,
        allow_network=True,
        write_artifacts=False,
    )

    assert status["classification"] == "blocked_before_broker_read"
    assert "network_test_flag_enabled" in status["blockers"]
    assert constructed is False


def test_flat_cli_and_wrapper_do_not_accept_caller_time_or_account_argv() -> None:
    module_source = Path(
        "src/algotrader/execution/"
        "crypto_bounded_probe_independent_flat_operator.py"
    ).read_text(encoding="utf-8")
    wrapper_source = Path(
        "scripts/run_crypto_bounded_probe_independent_flat_operator.ps1"
    ).read_text(encoding="utf-8")

    for forbidden in (
        "parser.add_argument(\"--timestamp\"",
        "parser.add_argument(\"--expected-paper-account-id\"",
        "$AsOfTimestamp",
        "$ExpectedPaperAccountId",
        "--timestamp",
        "--expected-paper-account-id",
    ):
        assert forbidden not in module_source
        assert forbidden not in wrapper_source
    assert "allow_abbrev=False" in module_source
