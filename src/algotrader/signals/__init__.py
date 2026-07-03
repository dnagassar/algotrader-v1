"""Deterministic signal-generation helpers."""

from .base import SignalGenerator
from .crypto_trend import (
    CRYPTO_TREND_LABELS,
    CRYPTO_TREND_POSTURES,
    CRYPTO_TREND_STRATEGY_FAMILY,
    CRYPTO_TREND_STRATEGY_ID,
    CryptoTrendSignalConfig,
    CryptoTrendSignalEvaluator,
    CryptoTrendSignalResult,
    evaluate_crypto_trend_signal,
)
from .etf_sma_evaluator import (
    ETF_SMA_SIGNAL_LABELS,
    ETF_SMA_SIGNAL_POSTURES,
    EtfSmaSignalConfig,
    EtfSmaSignalEvaluator,
    EtfSmaSignalResult,
    evaluate_etf_sma_signal,
)
from .spy_rsi_mean_reversion import (
    SPY_RSI_MEAN_REVERSION_LABELS,
    SPY_RSI_MEAN_REVERSION_POSTURES,
    SPYRsiMeanReversionSignalConfig,
    SPYRsiMeanReversionSignalEvaluator,
    SPYRsiMeanReversionSignalResult,
    evaluate_spy_rsi_mean_reversion_signal,
)
from .spy_vol_scaled_trend import (
    SPY_VOL_SCALED_TREND_LABELS,
    SPY_VOL_SCALED_TREND_POSTURES,
    SPY_VOL_SCALED_TREND_STRATEGY_FAMILY,
    SPY_VOL_SCALED_TREND_STRATEGY_ID,
    SPYVolScaledTrendSignalConfig,
    SPYVolScaledTrendSignalEvaluator,
    SPYVolScaledTrendSignalResult,
    evaluate_spy_vol_scaled_trend_signal,
)
from .signal_evaluation_input import SignalEvaluationInputSnapshot
from .signal_evaluation_result import SignalEvaluationResult
from .signal_input_bundle import SignalInputBundle
from .signal_input_bundle_completeness import (
    SignalInputBundleCompletenessResult,
    validate_signal_input_bundle_completeness,
)
from .signal_input_value import SignalInputValue
from .simple_rule import generate_momentum_buy_order
from .validated_signal_definition import ValidatedSignalDefinition

__all__ = [
    "ETF_SMA_SIGNAL_LABELS",
    "ETF_SMA_SIGNAL_POSTURES",
    "CRYPTO_TREND_LABELS",
    "CRYPTO_TREND_POSTURES",
    "CRYPTO_TREND_STRATEGY_FAMILY",
    "CRYPTO_TREND_STRATEGY_ID",
    "CryptoTrendSignalConfig",
    "CryptoTrendSignalEvaluator",
    "CryptoTrendSignalResult",
    "EtfSmaSignalConfig",
    "EtfSmaSignalEvaluator",
    "EtfSmaSignalResult",
    "SPY_RSI_MEAN_REVERSION_LABELS",
    "SPY_RSI_MEAN_REVERSION_POSTURES",
    "SPYRsiMeanReversionSignalConfig",
    "SPYRsiMeanReversionSignalEvaluator",
    "SPYRsiMeanReversionSignalResult",
    "SPY_VOL_SCALED_TREND_LABELS",
    "SPY_VOL_SCALED_TREND_POSTURES",
    "SPY_VOL_SCALED_TREND_STRATEGY_FAMILY",
    "SPY_VOL_SCALED_TREND_STRATEGY_ID",
    "SPYVolScaledTrendSignalConfig",
    "SPYVolScaledTrendSignalEvaluator",
    "SPYVolScaledTrendSignalResult",
    "SignalGenerator",
    "SignalEvaluationInputSnapshot",
    "SignalEvaluationResult",
    "SignalInputBundle",
    "SignalInputBundleCompletenessResult",
    "SignalInputValue",
    "ValidatedSignalDefinition",
    "evaluate_crypto_trend_signal",
    "evaluate_etf_sma_signal",
    "evaluate_spy_rsi_mean_reversion_signal",
    "evaluate_spy_vol_scaled_trend_signal",
    "generate_momentum_buy_order",
    "validate_signal_input_bundle_completeness",
]
