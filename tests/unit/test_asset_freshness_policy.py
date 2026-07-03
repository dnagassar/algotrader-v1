from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from algotrader.execution.asset_freshness_policy import (
    evaluate_asset_class_freshness,
)


def test_equity_freshness_uses_expected_latest_session_date() -> None:
    receipt = evaluate_asset_class_freshness(
        asset_class="equity",
        latest_bar_at=datetime(2026, 7, 2, tzinfo=UTC),
        observed_at=datetime(2026, 7, 3, 2, tzinfo=UTC),
        expected_latest_bar_date=date(2026, 7, 2),
    )

    assert receipt.data_freshness_status == "current_for_daily_bar_lab"
    assert receipt.freshness_policy == "exchange_session_expected_latest_bar_date"
    assert receipt.blockers == ()


def test_equity_stale_data_still_blocks_by_expected_latest_session_date() -> None:
    receipt = evaluate_asset_class_freshness(
        asset_class="equity",
        latest_bar_at=datetime(2026, 7, 1, tzinfo=UTC),
        observed_at=datetime(2026, 7, 3, 2, tzinfo=UTC),
        expected_latest_bar_date="2026-07-02",
    )

    assert receipt.data_freshness_status == "stale_data_preview_only"
    assert receipt.blockers == ("latest_bar_date_before_expected",)


def test_crypto_freshness_uses_24_7_bar_age_threshold() -> None:
    receipt = evaluate_asset_class_freshness(
        asset_class="crypto",
        latest_bar_at=datetime(2026, 7, 3, 1, tzinfo=UTC),
        observed_at=datetime(2026, 7, 3, 2, tzinfo=UTC),
        crypto_max_age=timedelta(hours=2),
    )

    assert receipt.data_freshness_status == "current_for_24_7_crypto_lab"
    assert receipt.freshness_policy == "crypto_24_7_max_bar_age"
    assert receipt.age_seconds == 3600
    assert receipt.max_age_seconds == 7200
    assert receipt.blockers == ()


def test_stale_crypto_data_blocks_crypto_readiness() -> None:
    receipt = evaluate_asset_class_freshness(
        asset_class="crypto",
        latest_bar_at=datetime(2026, 7, 2, 20, tzinfo=UTC),
        observed_at=datetime(2026, 7, 3, 2, tzinfo=UTC),
        crypto_max_age=timedelta(hours=2),
    )

    assert receipt.data_freshness_status == "stale_crypto_data_preview_only"
    assert receipt.blockers == ("crypto_bar_age_exceeds_threshold",)
