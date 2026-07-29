"""Offline NexusTrade candidate intake routed into deterministic local replay."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

from algotrader.errors import ValidationError
from algotrader.research.strategy_challenger_factory import (
    StrategyChallengerCandidate,
    StrategyChallengerFactoryConfig,
    build_default_strategy_challenger_candidates,
    run_strategy_challenger_factory,
)

__all__ = [
    "NEXUSTRADE_INTAKE_LABELS",
    "NexusTradeStrategyIntakeConfig",
    "build_nexustrade_strategy_intake_payload",
    "load_nexustrade_strategy_batch",
    "main",
    "run_nexustrade_strategy_intake",
]


NEXUSTRADE_INTAKE_LABELS = (
    "research_only",
    "offline_only",
    "untrusted_source_metrics",
    "local_replay_required",
    "not_live_authorized",
    "no_broker_access",
    "no_paper_promotion",
)

_SCHEMA_VERSION = "1"
_RECORD_TYPE = "nexustrade_strategy_intake"
_PROVIDER = "nexustrade"
_MAX_INPUT_BYTES = 2 * 1024 * 1024
_MAX_CANDIDATES = 50
_DEFAULT_DATA_PATH = Path("runs/operator_input/multi_etf_adjusted_daily_canonical.csv")
_DEFAULT_OUTPUT_ROOT = Path("runs/nexustrade_strategy_intake/latest")
_DEFAULT_INITIAL_EQUITY = Decimal("10000")
_DEFAULT_FEE_BPS = Decimal("0")
_DEFAULT_SLIPPAGE_BPS = Decimal("0")
_SUPPORTED_FAMILIES = (
    "sma_crossover_long_only",
    "time_series_momentum_long_only",
    "drawdown_filter_long_only",
    "etf_relative_momentum_basket",
)
_PAIRING_ROLES = (
    "standalone",
    "confirmation_filter",
    "risk_regime_filter",
    "diversifier",
)
_VALIDATION_METHODS = (
    "none",
    "holdout",
    "train_validation_test",
    "walk_forward",
)
_SOURCE_DATA_MODES = ("daily_ohlc", "intraday")
_RESERVED_OPERATING_IDS = frozenset(
    (
        "spy_sma_50_200_training_wheel",
        "spy_sma_50_200_baseline",
        "spy_rsi_14_mean_reversion_paper",
    )
)
_REPLAY_BASE_IDS = frozenset(
    (
        "spy_sma_50_200_baseline",
        "spy_buy_and_hold_comparator",
        "spy_sma_50_200_cash_risk_off_comparator",
    )
)
_FORBIDDEN_FIELD_FRAGMENTS = (
    "account_id",
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "broker_order",
    "client_secret",
    "credential",
    "password",
    "secret",
    "token",
)


@dataclass(frozen=True, slots=True)
class NexusTradeStrategyIntakeConfig:
    """Paths and deterministic replay assumptions for one intake batch."""

    input_path: Path | str
    output_root: Path | str
    data_path: Path | str = _DEFAULT_DATA_PATH
    as_of: date | str | None = None
    initial_equity: Decimal | str = _DEFAULT_INITIAL_EQUITY
    fee_bps: Decimal | str = _DEFAULT_FEE_BPS
    slippage_bps: Decimal | str = _DEFAULT_SLIPPAGE_BPS

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_path", _path(self.input_path, "input_path"))
        object.__setattr__(
            self,
            "output_root",
            _path(self.output_root, "output_root"),
        )
        object.__setattr__(self, "data_path", _path(self.data_path, "data_path"))
        object.__setattr__(self, "as_of", _optional_date(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "initial_equity",
            _positive_decimal(self.initial_equity, "initial_equity"),
        )
        object.__setattr__(
            self,
            "fee_bps",
            _non_negative_decimal(self.fee_bps, "fee_bps"),
        )
        object.__setattr__(
            self,
            "slippage_bps",
            _non_negative_decimal(self.slippage_bps, "slippage_bps"),
        )


def load_nexustrade_strategy_batch(path: Path | str) -> dict[str, object]:
    """Load one bounded JSON batch without contacting NexusTrade or a broker."""

    checked_path = _path(path, "input_path")
    if not checked_path.is_file():
        raise ValidationError("input_path must identify an existing file.")
    if checked_path.stat().st_size > _MAX_INPUT_BYTES:
        raise ValidationError("NexusTrade intake input exceeds the 2 MiB limit.")
    try:
        payload = json.loads(checked_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError("NexusTrade intake input must be valid UTF-8 JSON.") from exc
    if not isinstance(payload, dict):
        raise ValidationError("NexusTrade intake root must be an object.")
    _reject_sensitive_fields(payload)
    return payload


def run_nexustrade_strategy_intake(
    config: NexusTradeStrategyIntakeConfig,
) -> dict[str, object]:
    """Normalize a batch, replay eligible candidates, and write a compact report."""

    checked = _config(config)
    source_payload = load_nexustrade_strategy_batch(checked.input_path)
    payload, replay_candidates = build_nexustrade_strategy_intake_payload(
        source_payload,
        input_sha256=_file_sha256(checked.input_path),
    )
    replay = _run_local_replay(checked, replay_candidates)
    completed = dict(payload)
    completed["local_replay"] = replay
    completed["candidate_routes"] = _candidate_routes(
        tuple(completed["candidates"]),  # type: ignore[arg-type]
        replay,
    )
    completed["paper_promotion_allowed"] = False
    completed["broker_access_attempted"] = False
    completed["network_access_attempted"] = False
    completed["broker_mutation_performed"] = False
    completed["live_mutation_performed"] = False
    _write_report(completed, checked.output_root)
    return completed


def build_nexustrade_strategy_intake_payload(
    payload: Mapping[str, object],
    *,
    input_sha256: str,
) -> tuple[dict[str, object], tuple[StrategyChallengerCandidate, ...]]:
    """Validate source provenance and classify candidates for local replay."""

    _require_exact_fields(
        payload,
        required=(
            "schema_version",
            "provider",
            "captured_at",
            "source_url",
            "candidates",
        ),
        field_name="NexusTrade intake root",
    )
    if payload["schema_version"] != _SCHEMA_VERSION:
        raise ValidationError("schema_version must be exactly '1'.")
    if payload["provider"] != _PROVIDER:
        raise ValidationError("provider must be exactly 'nexustrade'.")
    captured_at = _iso_date(payload["captured_at"], "captured_at")
    source_url = _nexustrade_url(payload["source_url"], "source_url")
    raw_candidates = payload["candidates"]
    if not isinstance(raw_candidates, list):
        raise ValidationError("candidates must be a list.")
    if not raw_candidates:
        raise ValidationError("candidates must contain at least one candidate.")
    if len(raw_candidates) > _MAX_CANDIDATES:
        raise ValidationError("candidates must contain at most 50 candidates.")

    normalized: list[dict[str, object]] = []
    replay_candidates: list[StrategyChallengerCandidate] = []
    seen_ids: set[str] = set()
    seen_signatures = _existing_local_signatures()

    for index, raw_candidate in enumerate(raw_candidates):
        record, replay_candidate = _normalize_candidate(
            raw_candidate,
            index=index,
            batch_source_url=source_url,
        )
        candidate_id = str(record["candidate_id"])
        if candidate_id in seen_ids:
            raise ValidationError(f"duplicate candidate_id at candidates[{index}].")
        seen_ids.add(candidate_id)

        if replay_candidate is not None:
            signature = _candidate_signature(replay_candidate)
            if signature in seen_signatures:
                blockers = list(record["blockers"])
                blockers.append("duplicate_existing_local_candidate")
                record["blockers"] = blockers
                record["intake_status"] = "rejected_duplicate"
                record["local_replay_eligible"] = False
                record["local_candidate"] = None
                replay_candidate = None
            else:
                seen_signatures.add(signature)

        normalized.append(record)
        if replay_candidate is not None:
            replay_candidates.append(replay_candidate)

    counts = {
        status: sum(1 for record in normalized if record["intake_status"] == status)
        for status in (
            "ready_for_local_replay",
            "needs_source_evidence",
            "needs_local_adapter",
            "rejected_duplicate",
        )
    }
    return (
        {
            "record_type": _RECORD_TYPE,
            "schema_version": _SCHEMA_VERSION,
            "labels": list(NEXUSTRADE_INTAKE_LABELS),
            "provider": _PROVIDER,
            "captured_at": captured_at.isoformat(),
            "source_url": source_url,
            "input_sha256": _sha256_text(input_sha256),
            "candidate_count": len(normalized),
            "eligible_candidate_count": len(replay_candidates),
            "classification_counts": counts,
            "intake_status": (
                "ready_for_local_replay"
                if replay_candidates
                else "no_candidate_ready_for_local_replay"
            ),
            "candidates": normalized,
            "source_metrics_used_for_ranking": False,
            "source_metrics_used_for_promotion": False,
            "paper_promotion_allowed": False,
        },
        tuple(replay_candidates),
    )


def _normalize_candidate(
    value: object,
    *,
    index: int,
    batch_source_url: str,
) -> tuple[dict[str, object], StrategyChallengerCandidate | None]:
    field_name = f"candidates[{index}]"
    if not isinstance(value, dict):
        raise ValidationError(f"{field_name} must be an object.")
    _require_exact_fields(
        value,
        required=(
            "candidate_id",
            "strategy_name",
            "hypothesis",
            "source_url",
            "family",
            "symbol",
            "timeframe",
            "parameters",
            "source_rules",
            "source_backtest",
            "parent_strategy_ids",
            "pairing_role",
        ),
        field_name=field_name,
    )
    candidate_id = _identifier(value["candidate_id"], f"{field_name}.candidate_id")
    strategy_name = _required_string(
        value["strategy_name"],
        f"{field_name}.strategy_name",
    )
    hypothesis = _required_string(value["hypothesis"], f"{field_name}.hypothesis")
    source_url = _nexustrade_url(value["source_url"], f"{field_name}.source_url")
    if _nexustrade_host(source_url) != _nexustrade_host(batch_source_url):
        raise ValidationError(f"{field_name}.source_url must match the batch host.")
    family = _identifier(value["family"], f"{field_name}.family")
    symbol = _symbol(value["symbol"], f"{field_name}.symbol")
    timeframe = _required_string(value["timeframe"], f"{field_name}.timeframe").lower()
    parameters = _mapping(value["parameters"], f"{field_name}.parameters")
    source_rules = _source_rules(value["source_rules"], f"{field_name}.source_rules")
    source_backtest = _source_backtest(
        value["source_backtest"],
        f"{field_name}.source_backtest",
    )
    parent_ids = _identifier_list(
        value["parent_strategy_ids"],
        f"{field_name}.parent_strategy_ids",
    )
    if candidate_id in parent_ids:
        raise ValidationError(f"{field_name} cannot name itself as a parent.")
    pairing_role = _one_of(
        value["pairing_role"],
        f"{field_name}.pairing_role",
        _PAIRING_ROLES,
    )

    blockers = _source_evidence_blockers(source_backtest)
    replay_candidate: StrategyChallengerCandidate | None = None
    local_candidate_payload: dict[str, object] | None = None

    if candidate_id in _RESERVED_OPERATING_IDS:
        blockers.append("reserved_operating_strategy_id")
    if timeframe != "1d":
        blockers.append("local_timeframe_adapter_required")
    if source_backtest["data_mode"] not in (None, "daily_ohlc"):
        blockers.append("local_data_mode_adapter_required")
    if family not in _SUPPORTED_FAMILIES:
        blockers.append("local_strategy_family_adapter_required")
    else:
        blockers.extend(_local_parameter_adapter_blockers(family, parameters))

    adapter_blockers = tuple(
        blocker
        for blocker in blockers
        if blocker.endswith("_adapter_required")
        or blocker == "local_strategy_family_adapter_required"
    )
    evidence_blockers = tuple(
        blocker
        for blocker in blockers
        if blocker not in adapter_blockers and blocker != "reserved_operating_strategy_id"
    )
    if not blockers:
        replay_candidate = _to_local_candidate(
            candidate_id=candidate_id,
            family=family,
            symbol=symbol,
            timeframe=timeframe,
            parameters=parameters,
        )
        local_candidate_payload = replay_candidate.to_dict()
        status = "ready_for_local_replay"
    elif "reserved_operating_strategy_id" in blockers:
        status = "rejected_duplicate"
    elif adapter_blockers:
        status = "needs_local_adapter"
    elif evidence_blockers:
        status = "needs_source_evidence"
    else:
        status = "needs_source_evidence"

    return (
        {
            "candidate_id": candidate_id,
            "strategy_name": strategy_name,
            "hypothesis": hypothesis,
            "source_url": source_url,
            "family": family,
            "symbol": symbol,
            "timeframe": timeframe,
            "parameters": _json_safe(parameters),
            "source_rules": source_rules,
            "source_backtest": source_backtest,
            "parent_strategy_ids": list(parent_ids),
            "pairing_role": pairing_role,
            "blockers": blockers,
            "intake_status": status,
            "local_replay_eligible": replay_candidate is not None,
            "local_candidate": local_candidate_payload,
            "source_metrics_trust": "untrusted_external_evidence",
            "source_metrics_used_for_ranking": False,
            "source_metrics_used_for_promotion": False,
        },
        replay_candidate,
    )


def _to_local_candidate(
    *,
    candidate_id: str,
    family: str,
    symbol: str,
    timeframe: str,
    parameters: Mapping[str, object],
) -> StrategyChallengerCandidate:
    if family == "sma_crossover_long_only":
        _require_exact_fields(
            parameters,
            required=("fast_window", "slow_window"),
            field_name="parameters",
        )
        return StrategyChallengerCandidate(
            candidate_id=candidate_id,
            strategy_family=family,
            symbol=symbol,
            timeframe=timeframe,
            fast_window=_positive_int(parameters["fast_window"], "fast_window"),
            slow_window=_positive_int(parameters["slow_window"], "slow_window"),
        )
    if family == "time_series_momentum_long_only":
        _require_exact_fields(
            parameters,
            required=("lookback_days",),
            field_name="parameters",
        )
        return StrategyChallengerCandidate(
            candidate_id=candidate_id,
            strategy_family=family,
            symbol=symbol,
            timeframe=timeframe,
            fast_window=1,
            slow_window=_positive_int(parameters["lookback_days"], "lookback_days"),
        )
    if family == "drawdown_filter_long_only":
        _require_exact_fields(
            parameters,
            required=("lookback_days", "max_drawdown_percent"),
            field_name="parameters",
        )
        threshold = _decimal_value(
            parameters["max_drawdown_percent"],
            "max_drawdown_percent",
        )
        if threshold != Decimal("20"):
            raise ValidationError(
                "max_drawdown_percent requires a local adapter unless exactly 20."
            )
        return StrategyChallengerCandidate(
            candidate_id=candidate_id,
            strategy_family=family,
            symbol=symbol,
            timeframe=timeframe,
            fast_window=1,
            slow_window=_positive_int(parameters["lookback_days"], "lookback_days"),
            risk_off_state="cash_below_20pct_drawdown",
        )

    _require_exact_fields(
        parameters,
        required=(
            "lookback_days",
            "top_n",
            "rebalance_rule",
            "basket_symbols",
            "cash_filter",
        ),
        field_name="parameters",
    )
    basket_symbols = _symbol_list(parameters["basket_symbols"], "basket_symbols")
    top_n = _positive_int(parameters["top_n"], "top_n")
    rebalance_rule = _one_of(
        parameters["rebalance_rule"],
        "rebalance_rule",
        ("daily", "monthly"),
    )
    cash_filter = parameters["cash_filter"]
    if type(cash_filter) is not bool:
        raise ValidationError("cash_filter must be a boolean.")
    if cash_filter and top_n != 1:
        raise ValidationError("cash_filter currently supports top_n=1 only.")
    risk_off_state = (
        "cash_filter_positive_momentum"
        if cash_filter
        else (
            "fully_invested_top_ranked_etf"
            if top_n == 1
            else "fully_invested_top_ranked_etfs"
        )
    )
    return StrategyChallengerCandidate(
        candidate_id=candidate_id,
        strategy_family=family,
        symbol="ETF_BASKET",
        timeframe=timeframe,
        fast_window=top_n,
        slow_window=_positive_int(parameters["lookback_days"], "lookback_days"),
        basket_symbols=basket_symbols,
        top_n=top_n,
        rebalance_rule=rebalance_rule,
        risk_off_state=risk_off_state,
    )


def _local_parameter_adapter_blockers(
    family: str,
    parameters: Mapping[str, object],
) -> list[str]:
    if family == "drawdown_filter_long_only":
        _require_exact_fields(
            parameters,
            required=("lookback_days", "max_drawdown_percent"),
            field_name="parameters",
        )
        _positive_int(parameters["lookback_days"], "lookback_days")
        threshold = _decimal_value(
            parameters["max_drawdown_percent"],
            "max_drawdown_percent",
        )
        return [] if threshold == Decimal("20") else ["local_parameter_adapter_required"]
    if family == "etf_relative_momentum_basket":
        _require_exact_fields(
            parameters,
            required=(
                "lookback_days",
                "top_n",
                "rebalance_rule",
                "basket_symbols",
                "cash_filter",
            ),
            field_name="parameters",
        )
        _positive_int(parameters["lookback_days"], "lookback_days")
        top_n = _positive_int(parameters["top_n"], "top_n")
        _one_of(parameters["rebalance_rule"], "rebalance_rule", ("daily", "monthly"))
        _symbol_list(parameters["basket_symbols"], "basket_symbols")
        cash_filter = parameters["cash_filter"]
        if type(cash_filter) is not bool:
            raise ValidationError("cash_filter must be a boolean.")
        return (
            ["local_parameter_adapter_required"]
            if cash_filter and top_n != 1
            else []
        )
    return []


def _source_rules(value: object, field_name: str) -> dict[str, str]:
    mapping = _mapping(value, field_name)
    _require_exact_fields(
        mapping,
        required=("entry", "exit", "evaluation", "allocation"),
        field_name=field_name,
    )
    return {
        name: _required_string(mapping[name], f"{field_name}.{name}")
        for name in ("entry", "exit", "evaluation", "allocation")
    }


def _source_backtest(value: object, field_name: str) -> dict[str, object]:
    mapping = _mapping(value, field_name)
    _require_exact_fields(
        mapping,
        required=(
            "start_date",
            "end_date",
            "data_mode",
            "validation_method",
            "fee_bps",
            "slippage_bps",
            "trade_count",
            "metrics",
        ),
        field_name=field_name,
    )
    metrics = _mapping(mapping["metrics"], f"{field_name}.metrics")
    _require_exact_fields(
        metrics,
        required=("total_return", "max_drawdown", "sharpe_ratio"),
        field_name=f"{field_name}.metrics",
    )
    return {
        "start_date": _optional_iso_date_text(
            mapping["start_date"],
            f"{field_name}.start_date",
        ),
        "end_date": _optional_iso_date_text(
            mapping["end_date"],
            f"{field_name}.end_date",
        ),
        "data_mode": _optional_one_of(
            mapping["data_mode"],
            f"{field_name}.data_mode",
            _SOURCE_DATA_MODES,
        ),
        "validation_method": _optional_one_of(
            mapping["validation_method"],
            f"{field_name}.validation_method",
            _VALIDATION_METHODS,
        ),
        "fee_bps": _optional_decimal_text(mapping["fee_bps"], f"{field_name}.fee_bps"),
        "slippage_bps": _optional_decimal_text(
            mapping["slippage_bps"],
            f"{field_name}.slippage_bps",
        ),
        "trade_count": _optional_non_negative_int(
            mapping["trade_count"],
            f"{field_name}.trade_count",
        ),
        "metrics": {
            "total_return": _optional_decimal_text(
                metrics["total_return"],
                f"{field_name}.metrics.total_return",
            ),
            "max_drawdown": _optional_decimal_text(
                metrics["max_drawdown"],
                f"{field_name}.metrics.max_drawdown",
            ),
            "sharpe_ratio": _optional_decimal_text(
                metrics["sharpe_ratio"],
                f"{field_name}.metrics.sharpe_ratio",
            ),
        },
    }


def _source_evidence_blockers(source_backtest: Mapping[str, object]) -> list[str]:
    blockers: list[str] = []
    start_text = source_backtest["start_date"]
    end_text = source_backtest["end_date"]
    if start_text is None or end_text is None:
        blockers.append("source_backtest_dates_missing")
    elif date.fromisoformat(str(start_text)) >= date.fromisoformat(str(end_text)):
        blockers.append("source_backtest_date_range_invalid")
    if source_backtest["data_mode"] is None:
        blockers.append("source_data_mode_missing")
    if source_backtest["validation_method"] in (None, "none"):
        blockers.append("source_out_of_sample_validation_missing")
    if source_backtest["fee_bps"] is None or source_backtest["slippage_bps"] is None:
        blockers.append("source_cost_assumptions_missing")
    trade_count = source_backtest["trade_count"]
    if trade_count is None or trade_count == 0:
        blockers.append("source_trade_count_missing")
    metrics = _mapping(source_backtest["metrics"], "source_backtest.metrics")
    if any(metrics[name] is None for name in metrics):
        blockers.append("source_summary_metrics_missing")
    return blockers


def _run_local_replay(
    config: NexusTradeStrategyIntakeConfig,
    replay_candidates: tuple[StrategyChallengerCandidate, ...],
) -> dict[str, object]:
    if not replay_candidates:
        return {
            "status": "not_run_no_eligible_candidates",
            "eligible_candidate_ids": [],
            "output_root": None,
            "best_candidate_id": None,
            "best_candidate_classification": None,
            "classification_recommendation": "complete_or_translate_candidate_specs",
            "results": [],
            "source_metrics_used_for_ranking": False,
            "paper_promotion_allowed": False,
        }

    base_candidates = tuple(
        candidate
        for candidate in build_default_strategy_challenger_candidates()
        if candidate.candidate_id in _REPLAY_BASE_IDS
    )
    candidates = (*base_candidates, *replay_candidates)
    symbols = _replay_symbols(candidates)
    replay_root = config.output_root / "local_replay"
    replay_payload = run_strategy_challenger_factory(
        StrategyChallengerFactoryConfig(
            output_root=replay_root,
            data_path=config.data_path,
            symbols=symbols,
            as_of=config.as_of,
            initial_equity=config.initial_equity,
            fee_bps=config.fee_bps,
            slippage_bps=config.slippage_bps,
            candidates=candidates,
        )
    )
    recommendations = _mapping(
        replay_payload["promotion_recommendations"],
        "promotion_recommendations",
    )
    imported_ids = {candidate.candidate_id for candidate in replay_candidates}
    results = [
        _compact_replay_result(result)
        for result in replay_payload["results"]  # type: ignore[union-attr]
        if isinstance(result, Mapping) and result.get("candidate_id") in imported_ids
    ]
    missing_symbols = tuple(
        replay_payload.get("cross_asset_validation", {}).get("symbols_missing_data", [])
    )
    return {
        "status": (
            "completed_with_missing_data"
            if missing_symbols
            else "completed"
        ),
        "eligible_candidate_ids": sorted(imported_ids),
        "output_root": "local_replay",
        "best_candidate_id": recommendations.get("best_candidate_id"),
        "best_candidate_classification": recommendations.get(
            "best_candidate_classification"
        ),
        "classification_recommendation": recommendations.get(
            "classification_recommendation"
        ),
        "symbols_missing_data": list(missing_symbols),
        "results": results,
        "source_metrics_used_for_ranking": False,
        "paper_promotion_allowed": False,
    }


def _compact_replay_result(result: Mapping[str, object]) -> dict[str, object]:
    return {
        "candidate_id": result.get("candidate_id"),
        "symbol": result.get("symbol"),
        "metrics_status": result.get("metrics_status"),
        "data_availability_status": result.get("data_availability_status"),
        "oos_status": result.get("oos_status"),
        "cost_sensitivity_status": result.get("cost_sensitivity_status"),
        "promotion_classification": result.get("promotion_classification"),
        "promotion_reasons": list(result.get("promotion_reasons", [])),
        "total_return": result.get("total_return"),
        "max_drawdown": result.get("max_drawdown"),
        "sharpe_ratio": result.get("sharpe_ratio"),
        "baseline_total_return_delta": result.get("baseline_total_return_delta"),
        "baseline_max_drawdown_delta": result.get("baseline_max_drawdown_delta"),
        "baseline_sharpe_ratio_delta": result.get("baseline_sharpe_ratio_delta"),
    }


def _candidate_routes(
    candidates: tuple[Mapping[str, object], ...],
    replay: Mapping[str, object],
) -> list[dict[str, object]]:
    results_by_id: dict[str, list[Mapping[str, object]]] = {}
    for result in replay.get("results", []):
        if isinstance(result, Mapping):
            results_by_id.setdefault(str(result.get("candidate_id")), []).append(result)
    routes: list[dict[str, object]] = []
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        results = results_by_id.get(candidate_id, [])
        classifications = {str(result.get("promotion_classification")) for result in results}
        metrics_valid = any(result.get("metrics_status") == "valid" for result in results)
        if candidate["intake_status"] != "ready_for_local_replay":
            route = "repair_intake_blockers"
        elif not results or not metrics_valid:
            route = "await_or_repair_local_data"
        elif "preview_only" in classifications:
            route = "preview_review"
        elif classifications == {"reject"}:
            route = "reject"
        else:
            route = "continue_local_research"
        routes.append(
            {
                "candidate_id": candidate_id,
                "route": route,
                "local_result_count": len(results),
                "paper_promotion_allowed": False,
            }
        )
    return routes


def _existing_local_signatures() -> set[tuple[object, ...]]:
    return {
        _candidate_signature(candidate)
        for candidate in build_default_strategy_challenger_candidates()
    }


def _candidate_signature(candidate: StrategyChallengerCandidate) -> tuple[object, ...]:
    return (
        candidate.strategy_family,
        candidate.symbol,
        candidate.timeframe,
        candidate.fast_window,
        candidate.slow_window,
        candidate.risk_off_state,
        candidate.basket_symbols,
        candidate.top_n,
        candidate.rebalance_rule,
    )


def _replay_symbols(
    candidates: tuple[StrategyChallengerCandidate, ...],
) -> tuple[str, ...]:
    symbols: list[str] = ["SPY"]
    for candidate in candidates:
        values = candidate.basket_symbols or (
            () if candidate.symbol == "ETF_BASKET" else (candidate.symbol,)
        )
        for symbol in values:
            if symbol not in symbols:
                symbols.append(symbol)
    return tuple(symbols)


def _write_report(payload: Mapping[str, object], output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    report_path = output_root / "nexustrade_intake_report.json"
    report_path.write_text(_json_dumps(payload), encoding="utf-8")


def _require_exact_fields(
    value: Mapping[str, object],
    *,
    required: tuple[str, ...],
    field_name: str,
) -> None:
    keys = set(value)
    expected = set(required)
    missing = expected - keys
    unknown = keys - expected
    if missing:
        raise ValidationError(
            f"{field_name} missing field(s): {', '.join(sorted(missing))}."
        )
    if unknown:
        raise ValidationError(
            f"{field_name} has unknown field(s): {', '.join(sorted(unknown))}."
        )


def _reject_sensitive_fields(value: object, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValidationError(f"{path} field names must be strings.")
            normalized = key.lower().replace("-", "_").replace(" ", "_")
            if any(fragment in normalized for fragment in _FORBIDDEN_FIELD_FRAGMENTS):
                raise ValidationError(f"{path} contains a forbidden sensitive field.")
            _reject_sensitive_fields(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_sensitive_fields(item, f"{path}[{index}]")
    elif isinstance(value, str):
        normalized = value.lower()
        if any(
            fragment in normalized
            for fragment in (
                "api key",
                "apikey",
                "authorization:",
                "bearer ",
                "password=",
                "secret=",
                "token=",
            )
        ):
            raise ValidationError(f"{path} contains forbidden sensitive text.")


def _mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be an object.")
    return value


def _required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _identifier(value: object, field_name: str) -> str:
    text = _required_string(value, field_name).lower()
    if len(text) > 96 or any(not (char.isalnum() or char == "_") for char in text):
        raise ValidationError(
            f"{field_name} must contain only lowercase letters, digits, and underscores."
        )
    return text


def _identifier_list(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list.")
    items = tuple(
        _identifier(item, f"{field_name}[{index}]")
        for index, item in enumerate(value)
    )
    if len(set(items)) != len(items):
        raise ValidationError(f"{field_name} must not contain duplicates.")
    return items


def _symbol(value: object, field_name: str) -> str:
    text = _required_string(value, field_name).upper()
    if len(text) > 16 or any(not (char.isalnum() or char in ".-") for char in text):
        raise ValidationError(f"{field_name} must be an uppercase market symbol.")
    return text


def _symbol_list(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list.")
    symbols = tuple(
        _symbol(item, f"{field_name}[{index}]")
        for index, item in enumerate(value)
    )
    if len(symbols) < 2:
        raise ValidationError(f"{field_name} must contain at least two symbols.")
    if len(set(symbols)) != len(symbols):
        raise ValidationError(f"{field_name} must not contain duplicates.")
    return symbols


def _one_of(value: object, field_name: str, choices: tuple[str, ...]) -> str:
    text = _required_string(value, field_name).lower()
    if text not in choices:
        raise ValidationError(f"{field_name} must be one of: {', '.join(choices)}.")
    return text


def _optional_one_of(
    value: object,
    field_name: str,
    choices: tuple[str, ...],
) -> str | None:
    if value is None:
        return None
    return _one_of(value, field_name, choices)


def _nexustrade_url(value: object, field_name: str) -> str:
    text = _required_string(value, field_name)
    if not text.startswith("https://"):
        raise ValidationError(f"{field_name} must be an HTTPS NexusTrade URL.")
    host = _nexustrade_host(text)
    if not (
        host == "nexustrade.io" or host.endswith(".nexustrade.io")
    ):
        raise ValidationError(f"{field_name} must be an HTTPS NexusTrade URL.")
    if any(fragment in text for fragment in ("@", "?", "#")):
        raise ValidationError(f"{field_name} must not contain credentials or query data.")
    return text


def _nexustrade_host(value: str) -> str:
    remainder = value[len("https://") :]
    return remainder.split("/", 1)[0].lower()


def _iso_date(value: object, field_name: str) -> date:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be an ISO date.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be an ISO date.") from exc
    if parsed.isoformat() != value:
        raise ValidationError(f"{field_name} must use YYYY-MM-DD.")
    return parsed


def _optional_iso_date_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _iso_date(value, field_name).isoformat()


def _optional_date(value: date | str | None, field_name: str) -> date | None:
    if value is None:
        return None
    if type(value) is date:
        return value
    return _iso_date(value, field_name)


def _positive_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")
    return value


def _optional_non_negative_int(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValidationError(f"{field_name} must be a non-negative integer or null.")
    return value


def _decimal_value(value: object, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, str):
        try:
            result = Decimal(value.strip())
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError(f"{field_name} must be decimal text.") from exc
    else:
        raise ValidationError(f"{field_name} must be decimal text.")
    if not result.is_finite():
        raise ValidationError(f"{field_name} must be finite.")
    return result


def _positive_decimal(value: object, field_name: str) -> Decimal:
    result = _decimal_value(value, field_name)
    if result <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return result


def _non_negative_decimal(value: object, field_name: str) -> Decimal:
    result = _decimal_value(value, field_name)
    if result < 0:
        raise ValidationError(f"{field_name} must be zero or greater.")
    return result


def _optional_decimal_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return format(_decimal_value(value, field_name), "f")


def _path(value: Path | str, field_name: str) -> Path:
    if isinstance(value, Path):
        return value
    if isinstance(value, str) and value.strip():
        return Path(value)
    raise ValidationError(f"{field_name} must be a local path.")


def _config(value: NexusTradeStrategyIntakeConfig) -> NexusTradeStrategyIntakeConfig:
    if not isinstance(value, NexusTradeStrategyIntakeConfig):
        raise ValidationError("config must be NexusTradeStrategyIntakeConfig.")
    return value


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(value: str) -> str:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValidationError("input_sha256 must be lowercase SHA-256 text.")
    return value


def _json_safe(value: object) -> object:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    raise ValidationError("input contains a non-JSON-compatible value.")


def _json_dumps(payload: Mapping[str, object]) -> str:
    return json.dumps(
        _json_safe(payload),
        indent=2,
        sort_keys=True,
        ensure_ascii=True,
    ) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nexustrade-strategy-intake")
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--output-root", default=str(_DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--data-path", default=str(_DEFAULT_DATA_PATH))
    parser.add_argument("--as-of-date", default=None)
    parser.add_argument("--initial-equity", default=str(_DEFAULT_INITIAL_EQUITY))
    parser.add_argument("--fee-bps", default=str(_DEFAULT_FEE_BPS))
    parser.add_argument("--slippage-bps", default=str(_DEFAULT_SLIPPAGE_BPS))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_nexustrade_strategy_intake(
            NexusTradeStrategyIntakeConfig(
                input_path=args.input_path,
                output_root=args.output_root,
                data_path=args.data_path,
                as_of=args.as_of_date,
                initial_equity=args.initial_equity,
                fee_bps=args.fee_bps,
                slippage_bps=args.slippage_bps,
            )
        )
    except ValidationError as exc:
        print("nexustrade_strategy_intake_status=blocked_invalid_input")
        print(f"blocker={exc}")
        print("broker_access_attempted=false")
        print("network_access_attempted=false")
        print("broker_mutation_performed=false")
        print("live_mutation_performed=false")
        return 2
    replay = _mapping(result["local_replay"], "local_replay")
    print("nexustrade_strategy_intake_status=completed")
    print(f"intake_status={result['intake_status']}")
    print(f"eligible_candidate_count={result['eligible_candidate_count']}")
    print(f"local_replay_status={replay['status']}")
    print(f"best_candidate_id={replay['best_candidate_id']}")
    print("source_metrics_used_for_ranking=false")
    print("paper_promotion_allowed=false")
    print("broker_access_attempted=false")
    print("network_access_attempted=false")
    print("broker_mutation_performed=false")
    print("live_mutation_performed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
