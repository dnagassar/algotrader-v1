"""Import-pure default-path crypto readiness trial replay command."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from algotrader.execution.crypto_supervised_readiness_trial_core import (
    DEFAULT_CYCLE_COUNT,
    DEFAULT_DECISION_START,
    DEFAULT_OUTPUT_ROOT,
    OFFLINE_PAPER_ENVIRONMENT,
    run_crypto_supervised_readiness_trial,
)

COMMAND_NAME = "crypto-readiness-replay"
MILESTONE_NAME = "V5.47 Import-Pure Crypto Readiness Replay"


def run_crypto_readiness_replay(
    *,
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
    decision_start: datetime | str = DEFAULT_DECISION_START,
    cycle_count: int = DEFAULT_CYCLE_COUNT,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Import-pure default-path replay wrapper."""
    return run_crypto_supervised_readiness_trial(
        output_root=output_root,
        decision_start=decision_start,
        cycle_count=cycle_count,
        broker_observed_readiness=False,
        allow_alpaca_paper_read=False,
        write_artifacts=write_artifacts,
        receipt_root=None,
        paper_environment=OFFLINE_PAPER_ENVIRONMENT,
    )
