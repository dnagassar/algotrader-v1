from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path

import pytest

from algotrader.errors import ValidationError
from algotrader.execution.crypto_bounded_probe_independent_flat_operator import (
    LEGACY_LIFECYCLE_SCHEMA_VERSION,
    TARGET_LIFECYCLE_SCHEMA_VERSION,
    run_crypto_bounded_probe_independent_flat_operator,
)


AS_OF = datetime(2026, 8, 21, 12, 5, tzinfo=UTC)
EXIT_FILLED_AT = "2026-08-21T12:00:00+00:00"
ACCOUNT_ID = "paper-account-id-never-persist"


class FlatPaperClient:
    def __init__(
        self,
        *,
        positions: list[dict[str, object]] | None = None,
        open_orders: list[dict[str, object]] | None = None,
    ) -> None:
        self.positions = [] if positions is None else positions
        self.open_orders = [] if open_orders is None else open_orders
        self.order_queries: list[object] = []

    def get_account(self) -> dict[str, object]:
        return {
            "id": ACCOUNT_ID,
            "account_id": ACCOUNT_ID,
            "account_number": "paper-number-never-persist",
            "status": "ACTIVE",
            "blocked": False,
            "account_blocked": False,
            "trading_blocked": False,
        }

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
    payload = {
        "schema_version": TARGET_LIFECYCLE_SCHEMA_VERSION,
        "record_type": (
            "crypto_tournament_v2_bounded_paper_probe_lifecycle"
        ),
        "subject": {
            "asset_class": "crypto",
            "symbol": symbol,
            "environment": "alpaca_paper",
        },
        "outcome_classification": "filled_exit_confirmed",
        "exit_final_order": {
            "symbol": symbol,
            "status": "filled",
            "filled_qty": "0.1",
            "filled_at": EXIT_FILLED_AT,
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
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
        timestamp="2026-08-21T11:59:59Z",
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
    for forbidden in (
        "submit_order",
        "cancel_order",
        "replace_order",
        "close_position",
        "close_all_positions",
    ):
        assert forbidden not in text
