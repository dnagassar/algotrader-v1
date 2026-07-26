"""Unit tests for crypto_readiness_replay command and CLI dispatch."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from algotrader.cli import main as cli_main
from algotrader.execution.crypto_readiness_replay import (
    COMMAND_NAME,
    MILESTONE_NAME,
    run_crypto_readiness_replay,
)
from algotrader.execution.crypto_supervised_readiness_trial_core import (
    OFFLINE_PAPER_ENVIRONMENT,
    _json_safe,
    run_crypto_supervised_readiness_trial,
)


def _contains_decimal(value: object) -> bool:
    if isinstance(value, Decimal):
        return True
    if isinstance(value, Mapping):
        return any(_contains_decimal(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return any(_contains_decimal(item) for item in value)
    return False


def test_run_crypto_readiness_replay_returns_accepted(tmp_path: Path) -> None:
    output_root = tmp_path / "replay_output"
    packet = run_crypto_readiness_replay(
        output_root=output_root,
        cycle_count=8,
        write_artifacts=True,
    )
    assert packet["trial_classification"] == "accepted"
    assert packet["milestone_name"] == "V5.32 End-to-End Supervised Crypto Readiness Trial"
    assert packet["safety"]["app_profile_paper"] is False
    assert packet["safety"]["app_profile_live"] is False
    assert packet["safety"]["credentials_present"] is False
    assert packet["safety"]["network_used"] is False
    assert packet["safety"]["broker_read_occurred"] is False
    assert _contains_decimal(packet)
    assert (output_root / "readiness_packet.json").is_file()


def test_run_crypto_readiness_replay_matches_direct_core(tmp_path: Path) -> None:
    output_root = tmp_path / "equivalent_replay"
    decision_start = datetime(2026, 7, 19, 12, 0, tzinfo=UTC)
    replay_packet = run_crypto_readiness_replay(
        output_root=output_root,
        decision_start=decision_start,
        cycle_count=8,
        write_artifacts=False,
    )
    direct_packet = run_crypto_supervised_readiness_trial(
        output_root=output_root,
        decision_start=decision_start,
        cycle_count=8,
        broker_observed_readiness=False,
        allow_alpaca_paper_read=False,
        write_artifacts=False,
        receipt_root=None,
        paper_environment=OFFLINE_PAPER_ENVIRONMENT,
    )
    assert _json_safe(replay_packet) == _json_safe(direct_packet)


def test_central_cli_dispatch_forwards_exact_replay_arguments(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_root = tmp_path / "forwarded"
    packet = {
        "trial_classification": "accepted",
        "current_readiness_rung_code": "R1",
        "cycle_count": 9,
        "receipt_chain": {"final_receipt_hash": "abc"},
        "decimal_probe": Decimal("1.25"),
    }
    with patch(
        "algotrader.execution.crypto_readiness_replay."
        "run_crypto_readiness_replay",
        return_value=packet,
    ) as replay:
        exit_code = cli_main(
            [
                "crypto-readiness-replay",
                "--output-root",
                str(output_root),
                "--decision-start",
                "2026-07-20T00:00:00+00:00",
                "--cycle-count",
                "9",
                "--format",
                "json",
            ]
        )
    assert exit_code == 0
    replay.assert_called_once_with(
        output_root=output_root,
        decision_start="2026-07-20T00:00:00+00:00",
        cycle_count=9,
        write_artifacts=True,
    )
    assert json.loads(capsys.readouterr().out)["decimal_probe"] == "1.25"


def test_central_cli_replay_fails_closed_with_exit_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    packet = {
        "trial_classification": "failed_closed",
        "current_readiness_rung_code": "R1",
        "cycle_count": 8,
        "receipt_chain": {"final_receipt_hash": ""},
    }
    with patch(
        "algotrader.execution.crypto_readiness_replay."
        "run_crypto_readiness_replay",
        return_value=packet,
    ):
        exit_code = cli_main(
            [
                "crypto-readiness-replay",
                "--output-root",
                str(tmp_path / "blocked"),
                "--format",
                "text",
            ]
        )
    assert exit_code == 2
    assert (
        "v5_47_trial_classification=failed_closed"
        in capsys.readouterr().out
    )


def test_cli_crypto_readiness_replay_text_format(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output_root = tmp_path / "cli_text_output"
    exit_code = cli_main([
        "crypto-readiness-replay",
        "--output-root", str(output_root),
        "--cycle-count", "8",
        "--format", "text",
    ])
    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "v5_47_trial_classification=accepted" in captured
    assert "v5_47_current_readiness_rung=R1" in captured
    assert "v5_47_cycle_count=8" in captured
    assert "v5_47_receipt_chain_hash=" in captured
    assert "v5_47_paper_submit_performed=false" in captured
    assert "v5_47_broker_mutation_performed=false" in captured
    assert "v5_47_live_authorized=false" in captured


def test_cli_crypto_readiness_replay_json_format(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output_root = tmp_path / "cli_json_output"
    exit_code = cli_main([
        "crypto-readiness-replay",
        "--output-root", str(output_root),
        "--cycle-count", "8",
        "--format", "json",
    ])
    assert exit_code == 0
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["trial_classification"] == "accepted"
    assert data["cycle_count"] == 8


def test_cli_crypto_readiness_replay_no_broker_flags_on_parser() -> None:
    from algotrader.cli import build_parser
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["crypto-readiness-replay", "--broker-observed-readiness"])
    with pytest.raises(SystemExit):
        parser.parse_args(["crypto-readiness-replay", "--receipt-root", "foo"])
    with pytest.raises(SystemExit):
        parser.parse_args(
            ["crypto-readiness-replay", "--allow-alpaca-paper-read"]
        )
