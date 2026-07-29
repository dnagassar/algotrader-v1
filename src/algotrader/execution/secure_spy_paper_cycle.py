"""Secure, bounded two-phase SPY paper operating cycle.

The existing paper autopilot deliberately separates a visibility pass from a
mutation pass with a readiness packet.  This module keeps that safety boundary
but consumes it inside one credential lease and one explicit operating cycle.
It never authorizes live access and never persists credential values.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from algotrader.config import DEFAULT_ALPACA_PAPER_BASE_URL
from algotrader.errors import ValidationError
from algotrader.execution.exchange_session import NyseExchangeSessionCalendar
from algotrader.execution.paper_autopilot_operator import (
    BrokerClientFactory,
    DailyLabRunner,
    PaperAutopilotOperatorConfig,
    run_paper_autopilot_operator,
)
from algotrader.execution.secure_credential_provider import (
    CredentialFamily,
    CredentialProvider,
    CredentialProviderError,
    CredentialReference,
    WINDOWS_PROVIDER_NAME,
    provider_from_name,
)
from algotrader.orchestration.strategy_router import (
    SMA_TRAINING_WHEEL_STRATEGY_ID,
    SPY_RSI_MEAN_REVERSION_PAPER_STRATEGY_ID,
)


SECURE_SPY_PAPER_CYCLE_SCHEMA_VERSION = "v5_57_secure_spy_paper_cycle_v1"
SECURE_SPY_PAPER_CYCLE_POLICY = "standing_bounded_paper_authority"
SECURE_SPY_PAPER_CREDENTIAL_REFERENCE = (
    "wincred:algotrader/v5.35/alpaca-paper-observation/production"
)
SECURE_SPY_PAPER_MAX_NOTIONAL = Decimal("25.00")
SECURE_SPY_PAPER_MAX_PORTFOLIO_NOTIONAL = Decimal("60.00")
SECURE_SPY_PAPER_MAX_SLEEVE_ORDERS_PER_SESSION = 2
SECURE_SPY_PAPER_EXECUTION_WINDOW_MINUTES = 60
SECURE_SPY_PAPER_DEFAULT_OUTPUT_ROOT = (
    "runs/paper_autopilot/secure_spy_paper_cycle"
)
SECURE_SPY_PAPER_DEFAULT_BARS_CSV = (
    "runs/operator_input/m446_spy_daily_tiingo_adjusted_canonical.csv"
)
SECURE_SPY_PAPER_DEFAULT_JOURNAL = (
    "runs/paper_autopilot/state/order_journal.sqlite3"
)
SECURE_SPY_PAPER_DEFAULT_SLEEVE_LEDGER = (
    "runs/paper_autopilot/state/strategy_sleeves.sqlite3"
)

_PAPER_ENDPOINT = DEFAULT_ALPACA_PAPER_BASE_URL.rstrip("/")
_NEW_YORK = ZoneInfo("America/New_York")
_FORBIDDEN_ENVIRONMENT_NAMES = (
    "APP_PROFILE",
    "ALPACA_API_KEY",
    "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
    "ALPACA_EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_PAPER_ACCOUNT_ID",
    "APCA_EXPECTED_PAPER_ACCOUNT_ID",
    "ALPACA_PAPER_BASE_URL",
    "ALPACA_BASE_URL",
    "ALPACA_LIVE_BASE_URL",
    "APCA_API_BASE_URL",
)
_RECONCILED_ACTION_CLASSIFICATIONS = frozenset({"healthy_paper_action_reconciled"})
_HEALTHY_NO_ACTION_CLASSIFICATIONS = frozenset(
    {
        "healthy_hold_noop",
        "no_new_completed_bar_noop",
    }
)
_MUTATION_PREVIEW_CLASSIFICATION = "mutation_would_be_required_no_submit_mode"
_MUTATION_PREVIEW_BLOCKER = "blocked/mutation_would_be_required_no_submit_mode"

Clock = Callable[[], datetime]
OperatorRunner = Callable[..., Mapping[str, Any]]


class SecureSpyPaperCycleError(RuntimeError):
    """Sanitized operating-cycle failure with a stable classification."""

    def __init__(self, classification: str) -> None:
        self.classification = classification
        super().__init__(classification)


@dataclass(frozen=True, slots=True)
class SecureSpyPaperCycleConfig:
    """Configuration for one secure paper-only operating cycle."""

    output_root: Path | str = SECURE_SPY_PAPER_DEFAULT_OUTPUT_ROOT
    bars_csv: Path | str = SECURE_SPY_PAPER_DEFAULT_BARS_CSV
    order_journal_path: Path | str = SECURE_SPY_PAPER_DEFAULT_JOURNAL
    strategy_sleeve_ledger_path: Path | str = (
        SECURE_SPY_PAPER_DEFAULT_SLEEVE_LEDGER
    )
    paper_credential_reference: CredentialReference | str = (
        SECURE_SPY_PAPER_CREDENTIAL_REFERENCE
    )
    max_notional: Decimal | str = SECURE_SPY_PAPER_MAX_NOTIONAL
    max_portfolio_notional: Decimal | str = (
        SECURE_SPY_PAPER_MAX_PORTFOLIO_NOTIONAL
    )
    max_sleeve_orders_per_session: int = (
        SECURE_SPY_PAPER_MAX_SLEEVE_ORDERS_PER_SESSION
    )
    allow_paper_mutation: bool = False
    adopt_existing_position_to_active_sleeve: bool = False
    execution_window_minutes: int = SECURE_SPY_PAPER_EXECUTION_WINDOW_MINUTES
    symbol: str = "SPY"
    active_strategy_id: str = SMA_TRAINING_WHEEL_STRATEGY_ID

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "output_root",
            _path(self.output_root, "output_root"),
        )
        object.__setattr__(
            self,
            "bars_csv",
            _path(self.bars_csv, "bars_csv"),
        )
        object.__setattr__(
            self,
            "order_journal_path",
            _path(self.order_journal_path, "order_journal_path"),
        )
        object.__setattr__(
            self,
            "strategy_sleeve_ledger_path",
            _path(
                self.strategy_sleeve_ledger_path,
                "strategy_sleeve_ledger_path",
            ),
        )
        reference = (
            self.paper_credential_reference
            if isinstance(self.paper_credential_reference, CredentialReference)
            else CredentialReference(self.paper_credential_reference)
        )
        if reference.family is not CredentialFamily.ALPACA_PAPER_OBSERVATION:
            raise ValidationError("paper credential reference family is invalid.")
        object.__setattr__(self, "paper_credential_reference", reference)
        max_notional = _positive_decimal(self.max_notional, "max_notional")
        if max_notional > SECURE_SPY_PAPER_MAX_NOTIONAL:
            raise ValidationError(
                f"max_notional cannot exceed {SECURE_SPY_PAPER_MAX_NOTIONAL}."
            )
        object.__setattr__(self, "max_notional", max_notional)
        max_portfolio_notional = _positive_decimal(
            self.max_portfolio_notional,
            "max_portfolio_notional",
        )
        if max_portfolio_notional > SECURE_SPY_PAPER_MAX_PORTFOLIO_NOTIONAL:
            raise ValidationError(
                "max_portfolio_notional cannot exceed "
                f"{SECURE_SPY_PAPER_MAX_PORTFOLIO_NOTIONAL}."
            )
        if max_portfolio_notional < max_notional:
            raise ValidationError(
                "max_portfolio_notional cannot be less than max_notional."
            )
        object.__setattr__(
            self,
            "max_portfolio_notional",
            max_portfolio_notional,
        )
        if (
            type(self.max_sleeve_orders_per_session) is not int
            or not 1
            <= self.max_sleeve_orders_per_session
            <= SECURE_SPY_PAPER_MAX_SLEEVE_ORDERS_PER_SESSION
        ):
            raise ValidationError(
                "max_sleeve_orders_per_session must be an integer from 1 to 2."
            )
        if type(self.allow_paper_mutation) is not bool:
            raise ValidationError("allow_paper_mutation must be a boolean.")
        if type(self.adopt_existing_position_to_active_sleeve) is not bool:
            raise ValidationError(
                "adopt_existing_position_to_active_sleeve must be a boolean."
            )
        if (
            self.adopt_existing_position_to_active_sleeve
            and self.allow_paper_mutation
        ):
            raise ValidationError(
                "strategy sleeve adoption requires a no-mutation bootstrap cycle."
            )
        if (
            type(self.execution_window_minutes) is not int
            or not 1 <= self.execution_window_minutes <= 60
        ):
            raise ValidationError(
                "execution_window_minutes must be an integer from 1 to 60."
            )
        if str(self.symbol).strip().upper() != "SPY":
            raise ValidationError("secure paper cycle is restricted to SPY.")
        object.__setattr__(self, "symbol", "SPY")
        active_strategy_id = str(self.active_strategy_id).strip()
        if active_strategy_id not in {
            SMA_TRAINING_WHEEL_STRATEGY_ID,
            SPY_RSI_MEAN_REVERSION_PAPER_STRATEGY_ID,
        }:
            raise ValidationError(
                "active_strategy_id is not supported by the secure paper cycle."
            )
        object.__setattr__(self, "active_strategy_id", active_strategy_id)


def run_secure_spy_paper_cycle(
    config: SecureSpyPaperCycleConfig | None = None,
    *,
    env: Mapping[str, str] | None = None,
    credential_provider: CredentialProvider | None = None,
    operator_runner: OperatorRunner | None = None,
    broker_client_factory: BrokerClientFactory | None = None,
    daily_lab_runner: DailyLabRunner | None = None,
    clock: Clock | None = None,
) -> dict[str, Any]:
    """Run visibility and, when explicitly enabled, one bounded mutation pass."""

    resolved = config or SecureSpyPaperCycleConfig()
    now = _aware_utc((clock or (lambda: datetime.now(UTC)))())
    cycle_id = _cycle_id(now)
    cycle_root = Path(resolved.output_root) / "cycles" / cycle_id
    preview_root = cycle_root / "preview" / "latest"
    preview_history_root = cycle_root / "preview" / "history"
    execution_root = cycle_root / "execution" / "latest"
    execution_history_root = cycle_root / "execution" / "history"
    public_env = dict(os.environ if env is None else env)
    preflight = _public_preflight(public_env)
    common = _base_receipt(
        resolved,
        now=now,
        cycle_id=cycle_id,
        preflight=preflight,
    )

    if preflight["passed"] is not True:
        return _persist_receipt(
            resolved,
            cycle_root,
            {
                **common,
                "state": "blocked_secure_preflight",
                "blockers": list(preflight["blockers"]),
            },
        )

    execution_window = _execution_window(
        now,
        window_minutes=resolved.execution_window_minutes,
    )
    common["execution_window"] = execution_window
    if (
        resolved.allow_paper_mutation
        and execution_window["eligible"] is not True
    ):
        return _persist_receipt(
            resolved,
            cycle_root,
            {
                **common,
                "state": "blocked_execution_window",
                "blockers": [str(execution_window["blocker"])],
            },
        )

    provider = credential_provider or provider_from_name(WINDOWS_PROVIDER_NAME)
    if getattr(provider, "provider_name", None) != WINDOWS_PROVIDER_NAME:
        return _persist_receipt(
            resolved,
            cycle_root,
            {
                **common,
                "state": "blocked_credential_provider",
                "credential_access_attempted": False,
                "blockers": ["credential_provider_mismatch"],
            },
        )

    runner = operator_runner or run_paper_autopilot_operator
    try:
        lease = provider.open(
            resolved.paper_credential_reference,
            expected_family=CredentialFamily.ALPACA_PAPER_OBSERVATION,
        )
    except CredentialProviderError as exc:
        return _persist_receipt(
            resolved,
            cycle_root,
            {
                **common,
                "state": "blocked_credential_provider",
                "credential_access_attempted": True,
                "blockers": [exc.classification],
            },
        )

    def operate(
        api_key: str,
        api_secret: str,
        expected_account: str | None,
    ) -> dict[str, Any]:
        if expected_account is None:
            raise SecureSpyPaperCycleError("expected_account_missing")
        secure_env = {
            "APP_PROFILE": "paper",
            "APCA_API_KEY_ID": api_key,
            "APCA_API_SECRET_KEY": api_secret,
            "ALPACA_EXPECTED_PAPER_ACCOUNT_ID": expected_account,
            "ALPACA_PAPER_BASE_URL": _PAPER_ENDPOINT,
        }
        preview_config = PaperAutopilotOperatorConfig(
            output_root=preview_root,
            history_root=preview_history_root,
            bars_csv=resolved.bars_csv,
            symbol=resolved.symbol,
            max_notional=str(resolved.max_notional),
            max_portfolio_notional=str(resolved.max_portfolio_notional),
            max_sleeve_orders_per_session=(
                resolved.max_sleeve_orders_per_session
            ),
            no_submit=True,
            order_journal_path=resolved.order_journal_path,
            strategy_sleeve_ledger_path=(
                resolved.strategy_sleeve_ledger_path
            ),
            active_strategy_id=resolved.active_strategy_id,
            adopt_existing_position_to_active_sleeve=(
                resolved.adopt_existing_position_to_active_sleeve
            ),
        )
        preview_result = runner(
            preview_config,
            env=secure_env,
            broker_client_factory=broker_client_factory,
            daily_lab_runner=daily_lab_runner,
            timestamp=now.isoformat(),
        )
        preview_summary = _operator_summary(preview_result)
        preview_receipt = _safe_operator_summary(preview_summary)
        receipt: dict[str, Any] = {
            **common,
            "credential_access_attempted": True,
            "credential_lease_consumed": True,
            "paper_broker_access_attempted": True,
            "preview": preview_receipt,
            "execution": {},
            "blockers": [],
        }

        if _preview_is_healthy_no_action(preview_summary):
            receipt.update(
                {
                    "state": "healthy_no_action",
                    "paper_broker_read_performed": (
                        preview_summary.get("broker_read_performed") is True
                    ),
                }
            )
            _assert_no_secret_values(
                receipt,
                (api_key, api_secret, expected_account),
            )
            return receipt

        if not _preview_is_mutation_ready(preview_summary):
            receipt.update(
                {
                    "state": "blocked_preview",
                    "blockers": _preview_blockers(preview_summary),
                    "paper_broker_read_performed": (
                        preview_summary.get("broker_read_performed") is True
                    ),
                }
            )
            _assert_no_secret_values(
                receipt,
                (api_key, api_secret, expected_account),
            )
            return receipt

        readiness_path = _readiness_packet_path(
            preview_summary,
            expected_root=preview_history_root,
        )
        readiness_sha256 = _file_sha256(readiness_path)
        receipt["readiness"] = {
            "generated": True,
            "packet_path": str(readiness_path),
            "packet_sha256": readiness_sha256,
            "standing_paper_authority_applied": (
                resolved.allow_paper_mutation
            ),
        }
        if not resolved.allow_paper_mutation:
            receipt.update(
                {
                    "state": "ready_no_submit",
                    "paper_broker_read_performed": (
                        preview_summary.get("broker_read_performed") is True
                    ),
                }
            )
            _assert_no_secret_values(
                receipt,
                (api_key, api_secret, expected_account),
            )
            return receipt

        if _file_sha256(readiness_path) != readiness_sha256:
            raise SecureSpyPaperCycleError("readiness_packet_changed")
        execution_config = PaperAutopilotOperatorConfig(
            output_root=execution_root,
            history_root=execution_history_root,
            bars_csv=resolved.bars_csv,
            symbol=resolved.symbol,
            max_notional=str(resolved.max_notional),
            max_portfolio_notional=str(resolved.max_portfolio_notional),
            max_sleeve_orders_per_session=(
                resolved.max_sleeve_orders_per_session
            ),
            no_submit=False,
            readiness_packet_path=readiness_path,
            order_journal_path=resolved.order_journal_path,
            strategy_sleeve_ledger_path=(
                resolved.strategy_sleeve_ledger_path
            ),
            active_strategy_id=resolved.active_strategy_id,
            adopt_existing_position_to_active_sleeve=False,
        )
        execution_result = runner(
            execution_config,
            env=secure_env,
            broker_client_factory=broker_client_factory,
            daily_lab_runner=daily_lab_runner,
            timestamp=now.isoformat(),
        )
        execution_summary = _operator_summary(execution_result)
        receipt["execution"] = _safe_operator_summary(execution_summary)
        receipt["paper_broker_read_performed"] = (
            execution_summary.get("broker_read_performed") is True
        )
        receipt["paper_submit_performed"] = (
            execution_summary.get("paper_submit_performed") is True
        )
        receipt["broker_mutation_performed"] = (
            execution_summary.get("broker_mutation_performed") is True
        )
        receipt["live_mutation_performed"] = (
            execution_summary.get("live_mutation_performed") is True
        )
        receipt["reconciliation_status"] = str(
            execution_summary.get("reconciliation_status") or ""
        )
        receipt["state"] = (
            "blocked_live_safety"
            if receipt["live_mutation_performed"]
            else _execution_state(execution_summary)
        )
        if receipt["state"] not in {
            "paper_action_reconciled",
            "revalidated_no_action",
        }:
            receipt["blockers"] = _execution_blockers(execution_summary)
        _assert_no_secret_values(
            receipt,
            (api_key, api_secret, expected_account),
        )
        return receipt

    try:
        receipt = lease.use(operate)
    except CredentialProviderError as exc:
        receipt = {
            **common,
            "state": "blocked_credential_provider",
            "credential_access_attempted": True,
            "blockers": [exc.classification],
        }
    except SecureSpyPaperCycleError as exc:
        receipt = {
            **common,
            "state": "blocked_secure_cycle",
            "credential_access_attempted": True,
            "credential_lease_consumed": lease.closed,
            "blockers": [exc.classification],
        }
    except Exception as exc:
        receipt = {
            **common,
            "state": "blocked_secure_cycle",
            "credential_access_attempted": True,
            "credential_lease_consumed": lease.closed,
            "blockers": [f"operator_failed:{exc.__class__.__name__}"],
        }
    return _persist_receipt(resolved, cycle_root, receipt)


def secure_spy_paper_cycle_exit_status(receipt: Mapping[str, Any]) -> int:
    """Return zero only for completed, reconciled, or intentional no-submit states."""

    if str(receipt.get("state") or "") in {
        "healthy_no_action",
        "ready_no_submit",
        "paper_action_reconciled",
        "revalidated_no_action",
    }:
        return 0
    return 2


def render_secure_spy_paper_cycle(receipt: Mapping[str, Any]) -> str:
    """Render a compact secret-free operating summary."""

    preview = _mapping(receipt.get("preview"))
    execution = _mapping(receipt.get("execution"))
    lines = (
        f"schema_version={receipt.get('schema_version', '')}",
        f"state={receipt.get('state', '')}",
        f"cycle_id={receipt.get('cycle_id', '')}",
        f"allow_paper_mutation={_bool_text(receipt.get('allow_paper_mutation'))}",
        f"max_order_notional={receipt.get('max_order_notional', '')}",
        f"max_portfolio_notional={receipt.get('max_portfolio_notional', '')}",
        "max_sleeve_orders_per_session="
        f"{receipt.get('max_sleeve_orders_per_session', '')}",
        f"active_strategy_id={receipt.get('active_strategy_id', '')}",
        f"preview_classification={preview.get('classification', '')}",
        f"preview_action={preview.get('execution_plan_action', '')}",
        f"selected_strategy_id={preview.get('selected_strategy_id', '')}",
        "strategy_sleeve_broker_quantity_match="
        f"{_bool_text(preview.get('strategy_sleeve_broker_quantity_match'))}",
        "strategy_sleeve_reconciliation_status="
        f"{execution.get('strategy_sleeve_reconciliation_status', '')}",
        f"execution_classification={execution.get('classification', '')}",
        f"paper_broker_read_performed={_bool_text(receipt.get('paper_broker_read_performed'))}",
        f"paper_submit_performed={_bool_text(receipt.get('paper_submit_performed'))}",
        f"broker_mutation_performed={_bool_text(receipt.get('broker_mutation_performed'))}",
        f"reconciliation_status={receipt.get('reconciliation_status', '')}",
        f"live_authorized={_bool_text(receipt.get('live_authorized'))}",
        "blockers=" + ",".join(str(item) for item in receipt.get("blockers", [])),
    )
    return "\n".join(lines) + "\n"


def _base_receipt(
    config: SecureSpyPaperCycleConfig,
    *,
    now: datetime,
    cycle_id: str,
    preflight: Mapping[str, object],
) -> dict[str, Any]:
    return {
        "schema_version": SECURE_SPY_PAPER_CYCLE_SCHEMA_VERSION,
        "policy": SECURE_SPY_PAPER_CYCLE_POLICY,
        "cycle_id": cycle_id,
        "observed_at": now.isoformat(),
        "symbol": config.symbol,
        "active_strategy_id": config.active_strategy_id,
        "bars_csv": str(config.bars_csv),
        "paper_endpoint": _PAPER_ENDPOINT,
        "credential_provider": WINDOWS_PROVIDER_NAME,
        "paper_credential_reference": str(config.paper_credential_reference),
        "credential_values_persisted": False,
        "credential_access_attempted": False,
        "credential_lease_consumed": False,
        "allow_paper_mutation": config.allow_paper_mutation,
        "max_orders_per_cycle": 1,
        "max_order_notional": str(config.max_notional),
        "max_entry_position_notional": str(config.max_notional),
        "max_portfolio_notional": str(config.max_portfolio_notional),
        "max_sleeve_orders_per_session": (
            config.max_sleeve_orders_per_session
        ),
        "strategy_sleeve_ledger_path": str(
            config.strategy_sleeve_ledger_path
        ),
        "adopt_existing_position_to_active_sleeve": (
            config.adopt_existing_position_to_active_sleeve
        ),
        "exposure_reducing_close_may_exceed_entry_cap": True,
        "paper_only": True,
        "live_authorized": False,
        "live_access_attempted": False,
        "live_mutation_performed": False,
        "paper_broker_access_attempted": False,
        "paper_broker_read_performed": False,
        "paper_submit_performed": False,
        "broker_mutation_performed": False,
        "reconciliation_status": "",
        "preflight": dict(preflight),
        "execution_window": {},
        "preview": {},
        "execution": {},
        "readiness": {},
    }


def _public_preflight(env: Mapping[str, str]) -> dict[str, object]:
    loaded = tuple(
        name
        for name in _FORBIDDEN_ENVIRONMENT_NAMES
        if str(env.get(name, "")).strip()
    )
    return {
        "passed": not loaded,
        "blockers": (
            ["credential_or_profile_environment_alias_loaded"] if loaded else []
        ),
        "loaded_forbidden_variable_count": len(loaded),
        "loaded_forbidden_variable_names": list(loaded),
        "process_credential_values_used": False,
        "paper_endpoint_fixed": True,
        "live_endpoint_indicator": False,
    }


def _execution_window(
    observed_at: datetime,
    *,
    window_minutes: int,
) -> dict[str, object]:
    calendar = NyseExchangeSessionCalendar()
    local_date = observed_at.astimezone(_NEW_YORK).date()
    session = calendar.session_for_date(local_date)
    if session is None:
        return {
            "eligible": False,
            "blocker": "no_nyse_session",
            "session_id": "",
            "opens_at": "",
            "closes_at": "",
        }
    window_end = min(
        session.opens_at + timedelta(minutes=window_minutes),
        session.closes_at,
    )
    eligible = session.opens_at <= observed_at < window_end
    return {
        "eligible": eligible,
        "blocker": "" if eligible else "outside_next_open_execution_window",
        "session_id": session.identity,
        "opens_at": session.opens_at.isoformat(),
        "window_ends_at": window_end.isoformat(),
        "closes_at": session.closes_at.isoformat(),
    }


def _operator_summary(result: Mapping[str, Any]) -> Mapping[str, Any]:
    summary = result.get("operator_summary")
    if not isinstance(summary, Mapping):
        raise SecureSpyPaperCycleError("operator_summary_missing")
    return summary


def _safe_operator_summary(summary: Mapping[str, Any]) -> dict[str, object]:
    fields = (
        "classification",
        "autonomy_status",
        "readiness_status",
        "readiness_packet_generated",
        "paper_mutation_readiness_packet",
        "hard_stop",
        "attention_required",
        "operator_exit_code",
        "run_id",
        "as_of_date",
        "latest_bar_date",
        "data_refresh_status",
        "data_freshness_status",
        "symbol",
        "sma_posture",
        "selected_strategy_id",
        "strategy_sleeve_enabled",
        "strategy_sleeve_strategy_id",
        "strategy_sleeve_generation",
        "strategy_sleeve_quantity",
        "strategy_sleeve_total_quantity",
        "strategy_sleeve_broker_quantity_match",
        "strategy_sleeve_pending_intent_count",
        "strategy_sleeve_reconciliation_status",
        "max_portfolio_notional",
        "max_sleeve_orders_per_session",
        "broker_state_mode",
        "broker_read_performed",
        "broker_state_observed",
        "expected_account_matched",
        "spy_position_observed",
        "spy_position_quantity",
        "open_spy_orders_observed",
        "unexpected_non_spy_positions_count",
        "blocker_status",
        "execution_plan_action",
        "paper_mutation_readiness_packet_consumed",
        "paper_mutation_readiness_gate_status",
        "paper_submit_performed",
        "broker_mutation_performed",
        "live_mutation_performed",
        "reconciliation_status",
    )
    return {field: summary.get(field) for field in fields}


def _preview_is_healthy_no_action(summary: Mapping[str, Any]) -> bool:
    return (
        str(summary.get("classification") or "")
        in _HEALTHY_NO_ACTION_CLASSIFICATIONS
        and summary.get("hard_stop") is not True
        and str(summary.get("execution_plan_action") or "")
        in {"", "hold", "no_action"}
        and summary.get("strategy_sleeve_enabled") is True
        and summary.get("strategy_sleeve_broker_quantity_match") is True
        and int(summary.get("strategy_sleeve_pending_intent_count") or 0) == 0
    )


def _preview_is_mutation_ready(summary: Mapping[str, Any]) -> bool:
    return (
        str(summary.get("classification") or "")
        == _MUTATION_PREVIEW_CLASSIFICATION
        and str(summary.get("blocker_status") or "") == _MUTATION_PREVIEW_BLOCKER
        and summary.get("readiness_packet_generated") is True
        and summary.get("broker_state_observed") is True
        and summary.get("expected_account_matched") is True
        and str(summary.get("execution_plan_action") or "") in {"buy", "sell_close"}
        and summary.get("paper_submit_performed") is not True
        and summary.get("broker_mutation_performed") is not True
        and summary.get("live_mutation_performed") is not True
        and summary.get("strategy_sleeve_enabled") is True
        and summary.get("strategy_sleeve_broker_quantity_match") is True
        and int(summary.get("strategy_sleeve_pending_intent_count") or 0) == 0
    )


def _preview_blockers(summary: Mapping[str, Any]) -> list[str]:
    blockers = []
    if summary.get("hard_stop") is True:
        blockers.append("preview_hard_stop")
    blocker = str(summary.get("blocker_status") or "")
    if blocker:
        blockers.append(blocker)
    classification = str(summary.get("classification") or "")
    if classification:
        blockers.append(f"preview_classification:{classification}")
    return list(dict.fromkeys(blockers or ["preview_not_mutation_ready"]))


def _readiness_packet_path(
    summary: Mapping[str, Any],
    *,
    expected_root: Path,
) -> Path:
    raw = str(summary.get("paper_mutation_readiness_packet") or "").strip()
    if not raw:
        raise SecureSpyPaperCycleError("readiness_packet_path_missing")
    path = Path(raw).resolve()
    root = expected_root.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SecureSpyPaperCycleError(
            "readiness_packet_path_outside_cycle"
        ) from exc
    if not path.is_file():
        raise SecureSpyPaperCycleError("readiness_packet_missing")
    return path


def _execution_state(summary: Mapping[str, Any]) -> str:
    classification = str(summary.get("classification") or "")
    if (
        classification in _RECONCILED_ACTION_CLASSIFICATIONS
        and summary.get("paper_submit_performed") is True
        and summary.get("broker_mutation_performed") is True
        and summary.get("live_mutation_performed") is not True
        and str(summary.get("strategy_sleeve_reconciliation_status") or "")
        in {
            "strategy_sleeve_reconciled_terminal",
            "strategy_sleeve_already_reconciled",
        }
    ):
        return "paper_action_reconciled"
    if _preview_is_healthy_no_action(summary):
        return "revalidated_no_action"
    if (
        summary.get("paper_submit_performed") is True
        or summary.get("broker_mutation_performed") is True
    ):
        return "reconciliation_required"
    return "blocked_execution"


def _execution_blockers(summary: Mapping[str, Any]) -> list[str]:
    blockers = []
    if summary.get("live_mutation_performed") is True:
        blockers.append("live_mutation_detected")
    if (
        summary.get("paper_submit_performed") is True
        or summary.get("broker_mutation_performed") is True
    ) and str(summary.get("classification") or "") not in (
        _RECONCILED_ACTION_CLASSIFICATIONS
    ):
        blockers.append("paper_action_not_terminally_reconciled")
    blocker = str(summary.get("blocker_status") or "")
    if blocker:
        blockers.append(blocker)
    return list(dict.fromkeys(blockers or ["execution_not_completed"]))


def _persist_receipt(
    config: SecureSpyPaperCycleConfig,
    cycle_root: Path,
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(receipt)
    cycle_root.mkdir(parents=True, exist_ok=True)
    cycle_path = cycle_root / "cycle_receipt.json"
    latest_path = Path(config.output_root) / "latest_receipt.json"
    text = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    _atomic_write(cycle_path, text)
    _atomic_write(latest_path, text)
    return payload


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def _assert_no_secret_values(
    receipt: Mapping[str, Any],
    values: Sequence[str],
) -> None:
    serialized = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    if any(value and value in serialized for value in values):
        raise SecureSpyPaperCycleError("credential_value_leak_detected")


def _execution_state_is_safe(receipt: Mapping[str, Any]) -> bool:
    return (
        receipt.get("live_authorized") is False
        and receipt.get("live_access_attempted") is False
        and receipt.get("live_mutation_performed") is False
    )


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cycle_id(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _aware_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValidationError("clock must return a timezone-aware datetime.")
    return value.astimezone(UTC)


def _positive_decimal(value: Decimal | str, field_name: str) -> Decimal:
    try:
        checked = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a decimal.") from exc
    if not checked.is_finite() or checked <= 0 or not math.isfinite(float(checked)):
        raise ValidationError(f"{field_name} must be positive and finite.")
    return checked


def _path(value: Path | str, field_name: str) -> Path:
    path = value if isinstance(value, Path) else Path(value)
    if not str(path).strip():
        raise ValidationError(f"{field_name} is required.")
    return path


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _bool_text(value: object) -> str:
    return "true" if value is True else "false"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one secure bounded SPY paper operating cycle.",
    )
    parser.add_argument(
        "--output-root",
        default=SECURE_SPY_PAPER_DEFAULT_OUTPUT_ROOT,
    )
    parser.add_argument(
        "--bars-csv",
        default=SECURE_SPY_PAPER_DEFAULT_BARS_CSV,
    )
    parser.add_argument(
        "--order-journal-path",
        default=SECURE_SPY_PAPER_DEFAULT_JOURNAL,
    )
    parser.add_argument(
        "--strategy-sleeve-ledger-path",
        default=SECURE_SPY_PAPER_DEFAULT_SLEEVE_LEDGER,
    )
    parser.add_argument(
        "--credential-provider",
        default=WINDOWS_PROVIDER_NAME,
    )
    parser.add_argument(
        "--paper-credential-reference",
        default=SECURE_SPY_PAPER_CREDENTIAL_REFERENCE,
    )
    parser.add_argument(
        "--max-notional",
        default=str(SECURE_SPY_PAPER_MAX_NOTIONAL),
    )
    parser.add_argument(
        "--max-portfolio-notional",
        default=str(SECURE_SPY_PAPER_MAX_PORTFOLIO_NOTIONAL),
    )
    parser.add_argument(
        "--max-sleeve-orders-per-session",
        type=int,
        default=SECURE_SPY_PAPER_MAX_SLEEVE_ORDERS_PER_SESSION,
    )
    parser.add_argument(
        "--active-strategy-id",
        default=SMA_TRAINING_WHEEL_STRATEGY_ID,
        choices=(
            SMA_TRAINING_WHEEL_STRATEGY_ID,
            SPY_RSI_MEAN_REVERSION_PAPER_STRATEGY_ID,
        ),
    )
    parser.add_argument("--allow-paper-mutation", action="store_true")
    parser.add_argument(
        "--adopt-existing-position-to-active-sleeve",
        action="store_true",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        provider = provider_from_name(args.credential_provider)
        receipt = run_secure_spy_paper_cycle(
            SecureSpyPaperCycleConfig(
                output_root=args.output_root,
                bars_csv=args.bars_csv,
                order_journal_path=args.order_journal_path,
                strategy_sleeve_ledger_path=args.strategy_sleeve_ledger_path,
                paper_credential_reference=args.paper_credential_reference,
                max_notional=args.max_notional,
                max_portfolio_notional=args.max_portfolio_notional,
                max_sleeve_orders_per_session=(
                    args.max_sleeve_orders_per_session
                ),
                allow_paper_mutation=args.allow_paper_mutation,
                active_strategy_id=args.active_strategy_id,
                adopt_existing_position_to_active_sleeve=(
                    args.adopt_existing_position_to_active_sleeve
                ),
            ),
            credential_provider=provider,
        )
    except (CredentialProviderError, SecureSpyPaperCycleError, ValidationError) as exc:
        classification = getattr(exc, "classification", exc.__class__.__name__)
        print(f"state=blocked_startup\nblockers={classification}")
        return 2
    if not _execution_state_is_safe(receipt):
        print("state=blocked_live_safety")
        return 2
    if args.format == "json":
        print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    else:
        print(render_secure_spy_paper_cycle(receipt), end="")
    return secure_spy_paper_cycle_exit_status(receipt)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "SECURE_SPY_PAPER_CREDENTIAL_REFERENCE",
    "SECURE_SPY_PAPER_CYCLE_POLICY",
    "SECURE_SPY_PAPER_CYCLE_SCHEMA_VERSION",
    "SECURE_SPY_PAPER_EXECUTION_WINDOW_MINUTES",
    "SECURE_SPY_PAPER_MAX_NOTIONAL",
    "SECURE_SPY_PAPER_MAX_PORTFOLIO_NOTIONAL",
    "SECURE_SPY_PAPER_MAX_SLEEVE_ORDERS_PER_SESSION",
    "SecureSpyPaperCycleConfig",
    "SecureSpyPaperCycleError",
    "main",
    "render_secure_spy_paper_cycle",
    "run_secure_spy_paper_cycle",
    "secure_spy_paper_cycle_exit_status",
]
