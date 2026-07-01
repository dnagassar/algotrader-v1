"""Deterministic signal-generation helpers."""

from .base import SignalGenerator
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
    "EtfSmaSignalConfig",
    "EtfSmaSignalEvaluator",
    "EtfSmaSignalResult",
    "SPY_RSI_MEAN_REVERSION_LABELS",
    "SPY_RSI_MEAN_REVERSION_POSTURES",
    "SPYRsiMeanReversionSignalConfig",
    "SPYRsiMeanReversionSignalEvaluator",
    "SPYRsiMeanReversionSignalResult",
    "SignalGenerator",
    "SignalEvaluationInputSnapshot",
    "SignalEvaluationResult",
    "SignalInputBundle",
    "SignalInputBundleCompletenessResult",
    "SignalInputValue",
    "ValidatedSignalDefinition",
    "evaluate_etf_sma_signal",
    "evaluate_spy_rsi_mean_reversion_signal",
    "generate_momentum_buy_order",
    "validate_signal_input_bundle_completeness",
]
