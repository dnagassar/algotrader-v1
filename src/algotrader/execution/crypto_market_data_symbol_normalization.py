"""Stdlib-only crypto market-data symbol normalization leaf."""

from __future__ import annotations

from dataclasses import dataclass
import re

SUPPORTED_CRYPTO_MARKET_DATA_QUOTE_SUFFIXES = ("USD",)
_CRYPTO_MARKET_DATA_SYMBOL_PART_PATTERN = re.compile(r"^[A-Z0-9]+$")


@dataclass(frozen=True, slots=True)
class CryptoMarketDataSymbolNormalization:
    input_symbol: str
    compact_symbol: str
    provider_symbol: str
    status: str
    blocker_code: str = ""


def crypto_market_data_symbol_normalization(
    symbol: str,
) -> CryptoMarketDataSymbolNormalization:
    raw_symbol = "" if symbol is None else str(symbol).strip()
    upper_symbol = raw_symbol.upper()
    if not upper_symbol:
        return CryptoMarketDataSymbolNormalization(
            input_symbol=raw_symbol,
            compact_symbol="",
            provider_symbol="",
            status="failed",
            blocker_code="broker_price_symbol_normalization_failed",
        )

    if "/" in upper_symbol:
        parts = tuple(part.strip() for part in upper_symbol.split("/"))
        if (
            len(parts) != 2
            or not parts[0]
            or not parts[1]
            or parts[1] not in SUPPORTED_CRYPTO_MARKET_DATA_QUOTE_SUFFIXES
            or not _CRYPTO_MARKET_DATA_SYMBOL_PART_PATTERN.fullmatch(parts[0])
        ):
            return CryptoMarketDataSymbolNormalization(
                input_symbol=raw_symbol,
                compact_symbol="".join(parts),
                provider_symbol="",
                status="failed",
                blocker_code="broker_price_symbol_normalization_failed",
            )
        if parts[0] in SUPPORTED_CRYPTO_MARKET_DATA_QUOTE_SUFFIXES:
            return CryptoMarketDataSymbolNormalization(
                input_symbol=raw_symbol,
                compact_symbol="".join(parts),
                provider_symbol="",
                status="ambiguous",
                blocker_code="broker_price_symbol_ambiguous",
            )
        return CryptoMarketDataSymbolNormalization(
            input_symbol=raw_symbol,
            compact_symbol="".join(parts),
            provider_symbol=f"{parts[0]}/{parts[1]}",
            status="already_normalized",
        )

    if not _CRYPTO_MARKET_DATA_SYMBOL_PART_PATTERN.fullmatch(upper_symbol):
        return CryptoMarketDataSymbolNormalization(
            input_symbol=raw_symbol,
            compact_symbol=upper_symbol,
            provider_symbol="",
            status="failed",
            blocker_code="broker_price_symbol_normalization_failed",
        )

    matches: list[tuple[str, str]] = []
    for quote in SUPPORTED_CRYPTO_MARKET_DATA_QUOTE_SUFFIXES:
        if upper_symbol.endswith(quote) and upper_symbol != quote:
            base = upper_symbol[: -len(quote)]
            if base:
                matches.append((base, quote))

    if not matches:
        return CryptoMarketDataSymbolNormalization(
            input_symbol=raw_symbol,
            compact_symbol=upper_symbol,
            provider_symbol="",
            status="failed",
            blocker_code="broker_price_symbol_normalization_failed",
        )
    if len(matches) != 1 or matches[0][0] in SUPPORTED_CRYPTO_MARKET_DATA_QUOTE_SUFFIXES:
        return CryptoMarketDataSymbolNormalization(
            input_symbol=raw_symbol,
            compact_symbol=upper_symbol,
            provider_symbol="",
            status="ambiguous",
            blocker_code="broker_price_symbol_ambiguous",
        )

    base, quote = matches[0]
    return CryptoMarketDataSymbolNormalization(
        input_symbol=raw_symbol,
        compact_symbol=upper_symbol,
        provider_symbol=f"{base}/{quote}",
        status="normalized",
    )
