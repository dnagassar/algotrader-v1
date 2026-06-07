from __future__ import annotations

import json
from pathlib import Path
from decimal import Decimal

import algotrader.cli as cli_module
from algotrader.research.etf_sma_adjusted_basis_promotion_packet import (
    EtfSmaAdjustedBasisPromotionPacketConfig,
    build_etf_sma_adjusted_basis_promotion_packet,
    render_etf_sma_adjusted_basis_promotion_packet_json,
    write_etf_sma_adjusted_basis_promotion_packet_jsonl,
)


_COMMAND = "etf-sma-adjusted-basis-promotion-packet"
_READY_STATUS = "ready_to_promote_adjusted_matched_window_basis"
_BLOCKED_STATUS = "blocked_adjusted_matched_window_basis_promotion"
_RAW_BASIS = "raw_close_price_return"
_ADJUSTED_BASIS = "adjusted_close_price_return"
_EXPECTED_SLICES = (
    ("full_evaluated_window", "2022-03-21", "2026-06-05", 1055),
    ("stress_2022", "2022-03-21", "2022-12-30", 197),
    ("recovery_2023", "2022-12-30", "2023-12-29", 250),
    ("bull_2024", "2023-12-29", "2024-12-31", 252),
    ("whipsaw_2025", "2024-12-31", "2025-12-31", 250),
    ("ytd_2026", "2025-12-31", "2026-06-05", 106),
)
_SAFETY_FALSE_FIELDS = (
    "submitted",
    "mutated",
    "broker_action_performed",
    "network_access_attempted",
    "credential_access_attempted",
    "live_authorized",
)
_RAW_METRICS = {
    "full_evaluated_window": (
        "0.54417778320572773590445375",
        "0.659690812124485249443056769",
        "0.1899890688985691677679343483",
        "0.2274726465171704040732315010",
    ),
    "stress_2022": (
        "0",
        "-0.13942707981727761650802223",
        "0",
        "0.2274726465171704040732315010",
    ),
    "recovery_2023": (
        "0.140319758625653822160372375",
        "0.242867975838715581936563552",
        "0.1029074466458419799471373328",
        "0.1029074466458419799471373337",
    ),
    "bull_2024": (
        "0.233047905577412635963897243",
        "0.233047905577412635963897243",
        "0.0840562263215664058350741781",
        "0.0840562263215664058350741781",
    ),
    "whipsaw_2025": (
        "0.015389483559769921301533055",
        "0.163527163527163527163527164",
        "0.1899890688985691677679343485",
        "0.1899890688985691677679343485",
    ),
    "ytd_2026": (
        "0.081578484279680900985452837",
        "0.081578484279680900985452837",
        "0.0913312916073559648593078266",
        "0.0913312916073559648593078266",
    ),
}
_ADJUSTED_METRICS = {
    "full_evaluated_window": (
        "0.62307367524076557019890148",
        "0.757757631674850346984645900",
        "0.1875538828742623777640176394",
        "0.2209306139270709641671885088",
    ),
    "stress_2022": (
        "0",
        "-0.1281057188534055953263990608",
        "0",
        "0.2209306139270709641671885088",
    ),
    "recovery_2023": (
        "0.192188856880660030861946091",
        "0.261895506347034435866141922",
        "0.0997041421358366367164781918",
        "0.0997041421358366367164781909",
    ),
    "bull_2024": (
        "0.248851497230754838155963985",
        "0.248851497230754838155963985",
        "0.0840562263215665947063700480",
        "0.0840562263215665947063700480",
    ),
    "whipsaw_2025": (
        "0.003121203736565910800231781",
        "0.177150534406597127174944422",
        "0.1875538828742623777640176392",
        "0.1875538828742623777640176392",
    ),
    "ytd_2026": (
        "0.086748292052124741226546213",
        "0.086748292052124741226546213",
        "0.0888136346693031971134936107",
        "0.0888136346693031971134936107",
    ),
}


def test_promotion_success_path_from_deterministic_fixture_artifacts(
    tmp_path: Path,
) -> None:
    raw_path, adjusted_path = _write_fixture_artifacts(tmp_path)

    payload = build_etf_sma_adjusted_basis_promotion_packet(
        _config(raw_path, adjusted_path)
    )

    assert payload["promotion_status"] == _READY_STATUS
    assert payload["comparison_basis"] == "matched_window"
    assert payload["raw_basis"] == _RAW_BASIS
    assert payload["adjusted_basis"] == _ADJUSTED_BASIS
    assert payload["source_raw_artifact"] == str(raw_path)
    assert payload["source_adjusted_artifact"] == str(adjusted_path)
    assert payload["same_slice_counts"] is True
    assert payload["same_slice_dates"] is True
    assert payload["m417a_slice_counts_unchanged"] is True
    assert payload["matched_total_interval_count"] == 1055
    assert payload["matched_evaluated_return_count"] == 1055
    assert payload["full_adjusted_history_evaluated_return_count"] == 8195
    assert payload["return_conclusions_unchanged"] is True
    assert payload["return_conclusion_changes"] == []
    assert payload["drawdown_conclusion_changes"] == ["recovery_2023"]
    assert payload["basis_delta_review_required"] is True
    assert payload["baseline_recommendation"] == "adjusted_close_matched_window"
    assert payload["preferred_offline_baseline_ready"] is True
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"
    for field_name in _SAFETY_FALSE_FIELDS:
        assert payload[field_name] is False

    changes = payload["basis_delta_explanations"]
    assert changes == [
        {
            "slice_name": "recovery_2023",
            "changed_field": "drawdown_conclusion",
            "raw_conclusion": "strategy_drawdown_below_benchmark",
            "adjusted_conclusion": "strategy_drawdown_above_benchmark",
            "explanation": (
                "Adjusted close keeps the matched window fixed while "
                "distribution-adjusted prices move the drawdown comparison "
                "across the raw-close conclusion boundary."
            ),
        }
    ]
    run_log = tmp_path / "m421.jsonl"
    write_etf_sma_adjusted_basis_promotion_packet_jsonl(payload, run_log)
    assert json.loads(run_log.read_text(encoding="utf-8")) == json.loads(
        render_etf_sma_adjusted_basis_promotion_packet_json(payload)
    )


def test_fails_closed_if_m420_is_full_history_adjusted_validation(
    tmp_path: Path,
) -> None:
    raw_path, adjusted_path = _write_fixture_artifacts(
        tmp_path,
        adjusted_mutator=lambda payload: payload.update(
            {
                "record_type": "etf_sma_adjusted_basis_validation",
                "basis_validation_status": "completed_adjusted_close_basis_validation",
            }
        ),
    )

    payload = build_etf_sma_adjusted_basis_promotion_packet(
        _config(raw_path, adjusted_path)
    )

    assert payload["promotion_status"] == _BLOCKED_STATUS
    assert "adjusted_artifact_not_m420_matched_window_validation" in payload["blockers"]
    assert "adjusted_artifact_not_completed_matched_window_validation" in (
        payload["blockers"]
    )


def test_fails_closed_if_slice_counts_differ(tmp_path: Path) -> None:
    def mutate(adjusted_payload: dict[str, object]) -> None:
        adjusted_payload["regime_slices"][2]["evaluated_return_count"] = 249

    raw_path, adjusted_path = _write_fixture_artifacts(
        tmp_path,
        adjusted_mutator=mutate,
    )

    payload = build_etf_sma_adjusted_basis_promotion_packet(
        _config(raw_path, adjusted_path)
    )

    assert payload["promotion_status"] == _BLOCKED_STATUS
    assert "adjusted_slice_count_mismatch_recovery_2023" in payload["blockers"]


def test_fails_closed_if_slice_dates_differ(tmp_path: Path) -> None:
    def mutate(adjusted_payload: dict[str, object]) -> None:
        adjusted_payload["regime_slices"][4]["slice_start_date"] = "2025-01-02"

    raw_path, adjusted_path = _write_fixture_artifacts(
        tmp_path,
        adjusted_mutator=mutate,
    )

    payload = build_etf_sma_adjusted_basis_promotion_packet(
        _config(raw_path, adjusted_path)
    )

    assert payload["promotion_status"] == _BLOCKED_STATUS
    assert "adjusted_slice_start_date_mismatch_whipsaw_2025" in payload["blockers"]


def test_fails_closed_if_adjusted_basis_label_is_not_adjusted(
    tmp_path: Path,
) -> None:
    raw_path, adjusted_path = _write_fixture_artifacts(
        tmp_path,
        adjusted_mutator=lambda payload: payload.update(
            {"data_basis": "raw_close_price_return"}
        ),
    )

    payload = build_etf_sma_adjusted_basis_promotion_packet(
        _config(raw_path, adjusted_path)
    )

    assert payload["promotion_status"] == _BLOCKED_STATUS
    assert "adjusted_basis_label_not_adjusted_or_total_return" in payload["blockers"]


def test_fails_closed_if_safety_flags_are_dirty(tmp_path: Path) -> None:
    raw_path, adjusted_path = _write_fixture_artifacts(
        tmp_path,
        adjusted_mutator=lambda payload: payload.update({"submitted": True}),
    )

    payload = build_etf_sma_adjusted_basis_promotion_packet(
        _config(raw_path, adjusted_path)
    )

    assert payload["promotion_status"] == _BLOCKED_STATUS
    assert "adjusted_safety_flag_dirty_submitted" in payload["blockers"]
    assert payload["trade_recommendation"] == "none"
    assert payload["profit_claim"] == "none"


def test_cli_writes_packet_before_runtime_config_loading(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    raw_path, adjusted_path = _write_fixture_artifacts(tmp_path)
    run_log = tmp_path / "m421_cli.jsonl"

    def fail_runtime_config(*args: object, **kwargs: object) -> object:
        raise AssertionError("M421 offline command must not load runtime config")

    monkeypatch.setattr(cli_module, "_load_runtime_config", fail_runtime_config)

    assert cli_module.main(
        [
            _COMMAND,
            "--symbol",
            "SPY",
            "--run-id",
            "unit_m421_cli",
            "--run-log",
            str(run_log),
            "--source-m417-artifact",
            str(raw_path),
            "--source-m420-artifact",
            str(adjusted_path),
            "--format",
            "json",
        ]
    ) == 0

    payload = json.loads(run_log.read_text(encoding="utf-8"))
    stdout = capsys.readouterr().out
    assert json.loads(stdout) == payload
    assert payload["promotion_status"] == _READY_STATUS


def _config(
    raw_path: Path,
    adjusted_path: Path,
) -> EtfSmaAdjustedBasisPromotionPacketConfig:
    return EtfSmaAdjustedBasisPromotionPacketConfig(
        run_id="unit_m421",
        symbol="SPY",
        source_m417_artifact=raw_path,
        source_m420_artifact=adjusted_path,
    )


def _write_fixture_artifacts(
    tmp_path: Path,
    *,
    raw_mutator=None,  # noqa: ANN001
    adjusted_mutator=None,  # noqa: ANN001
) -> tuple[Path, Path]:
    raw_payload = _raw_payload()
    adjusted_payload = _adjusted_payload()
    if raw_mutator is not None:
        raw_mutator(raw_payload)
    if adjusted_mutator is not None:
        adjusted_mutator(adjusted_payload)

    raw_path = tmp_path / "m417.jsonl"
    adjusted_path = tmp_path / "m420.jsonl"
    raw_path.write_text(json.dumps(raw_payload, sort_keys=True) + "\n", encoding="utf-8")
    adjusted_path.write_text(
        json.dumps(adjusted_payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return raw_path, adjusted_path


def _raw_payload() -> dict[str, object]:
    return {
        "record_type": "etf_sma_regime_slice_evidence",
        "schema_version": "1",
        "milestone": "M417",
        "run_id": "unit_m417",
        "symbol": "SPY",
        "data_basis": _RAW_BASIS,
        "evaluated_return_count": 1055,
        "profit_claim": "none",
        "regime_slices": [
            _slice_payload(name, start, end, count, _RAW_METRICS[name], _RAW_BASIS)
            for name, start, end, count in _EXPECTED_SLICES
        ],
    }


def _adjusted_payload() -> dict[str, object]:
    payload: dict[str, object] = {
        "record_type": "etf_sma_adjusted_matched_window_validation",
        "schema_version": "1",
        "milestone": "M420",
        "run_id": "unit_m420",
        "symbol": "SPY",
        "data_basis": _ADJUSTED_BASIS,
        "price_field": "adjusted_close",
        "basis_validation_status": "completed_adjusted_matched_window_validation",
        "adjusted_close_available": True,
        "same_slice_counts": True,
        "same_slice_dates": True,
        "m417a_slice_counts_unchanged": True,
        "matched_total_interval_count": 1055,
        "evaluated_return_count": 1055,
        "full_history_evaluated_return_count": 8195,
        "returns_fabricated": False,
        "no_fabricated_returns": True,
        "trade_recommendation": "none",
        "profit_claim": "none",
        "adjusted_close_source_inspection": {
            "valid": True,
            "adjusted_close_available": True,
            "close_adjusted_close_diff_count": 12,
        },
        "regime_slices": [
            _slice_payload(
                name,
                start,
                end,
                count,
                _ADJUSTED_METRICS[name],
                _ADJUSTED_BASIS,
            )
            for name, start, end, count in _EXPECTED_SLICES
        ],
    }
    for field_name in _SAFETY_FALSE_FIELDS:
        payload[field_name] = False
    payload["matched_slice_comparisons"] = [
        _embedded_comparison(name)
        for name, _, _, _ in _EXPECTED_SLICES
    ]
    return payload


def _slice_payload(
    name: str,
    start_date: str,
    end_date: str,
    count: int,
    metrics: tuple[str, str, str, str],
    data_basis: str,
) -> dict[str, object]:
    (
        strategy_return,
        benchmark_return,
        strategy_drawdown,
        benchmark_drawdown,
    ) = metrics
    return {
        "slice_name": name,
        "slice_start_date": start_date,
        "slice_end_date": end_date,
        "evaluated_return_count": count,
        "data_basis": data_basis,
        "strategy_total_return": strategy_return,
        "benchmark_total_return": benchmark_return,
        "strategy_max_drawdown": strategy_drawdown,
        "benchmark_max_drawdown": benchmark_drawdown,
        "profit_claim": "none",
    }


def _embedded_comparison(name: str) -> dict[str, object]:
    raw_slice = _slice_payload(name, "", "", 0, _RAW_METRICS[name], _RAW_BASIS)
    adjusted_slice = _slice_payload(
        name,
        "",
        "",
        0,
        _ADJUSTED_METRICS[name],
        _ADJUSTED_BASIS,
    )
    raw_return = _return_conclusion(raw_slice)
    adjusted_return = _return_conclusion(adjusted_slice)
    raw_drawdown = _drawdown_conclusion(raw_slice)
    adjusted_drawdown = _drawdown_conclusion(adjusted_slice)
    return {
        "slice_name": name,
        "raw_strategy_total_return": raw_slice["strategy_total_return"],
        "adjusted_strategy_total_return": adjusted_slice["strategy_total_return"],
        "raw_benchmark_total_return": raw_slice["benchmark_total_return"],
        "adjusted_benchmark_total_return": adjusted_slice["benchmark_total_return"],
        "raw_strategy_max_drawdown": raw_slice["strategy_max_drawdown"],
        "adjusted_strategy_max_drawdown": adjusted_slice["strategy_max_drawdown"],
        "raw_return_conclusion": raw_return,
        "adjusted_return_conclusion": adjusted_return,
        "return_conclusion_unchanged": raw_return == adjusted_return,
        "raw_drawdown_conclusion": raw_drawdown,
        "adjusted_drawdown_conclusion": adjusted_drawdown,
        "drawdown_conclusion_unchanged": raw_drawdown == adjusted_drawdown,
    }


def _return_conclusion(item: dict[str, object]) -> str:
    strategy_return = Decimal(str(item["strategy_total_return"]))
    benchmark_return = Decimal(str(item["benchmark_total_return"]))
    if strategy_return > benchmark_return:
        return "strategy_return_above_benchmark"
    if strategy_return < benchmark_return:
        return "strategy_return_below_benchmark"
    return "strategy_return_matches_benchmark"


def _drawdown_conclusion(item: dict[str, object]) -> str:
    strategy_drawdown = Decimal(str(item["strategy_max_drawdown"]))
    benchmark_drawdown = Decimal(str(item["benchmark_max_drawdown"]))
    if strategy_drawdown > benchmark_drawdown:
        return "strategy_drawdown_above_benchmark"
    if strategy_drawdown < benchmark_drawdown:
        return "strategy_drawdown_below_benchmark"
    return "strategy_drawdown_matches_benchmark"
