"""Synthetic-only Polygon/Massive-style reference ticker metadata fixture."""

from __future__ import annotations

__all__ = [
    "build_synthetic_polygon_reference_ticker",
    "expected_synthetic_polygon_reference_ticker_dict",
    "expected_synthetic_polygon_reference_ticker_json",
]


_SYNTHETIC_POLYGON_REFERENCE_TICKER_NON_CLAIMS = (
    "not Polygon approval",
    "not Massive approval",
    "not endpoint approval",
    "not source approval",
    "not data approval",
    "not universe approval",
    "not benchmark approval",
    "not cash proxy approval",
    "not evidence approval",
    "not return-construction approval",
    "not no-lookahead approval",
    "not strategy validation",
    "not trading readiness",
)


def build_synthetic_polygon_reference_ticker() -> dict[str, object]:
    """Return one deterministic primitive candidate reference-ticker row."""

    return expected_synthetic_polygon_reference_ticker_dict()


def expected_synthetic_polygon_reference_ticker_dict() -> dict[str, object]:
    """Return the pinned primitive payload for the synthetic ticker fixture."""

    return {
        "ticker": "SYNREF001",
        "name": "Synthetic Reference Ticker Placeholder",
        "market": "synthetic_market",
        "locale": "synthetic_locale",
        "primary_exchange": "SYNTHETIC_EXCHANGE",
        "type": "synthetic_reference_type",
        "active": False,
        "currency_name": "synthetic_currency",
        "composite_figi": "SYNTHETIC_COMPOSITE_FIGI",
        "share_class_figi": "SYNTHETIC_SHARE_CLASS_FIGI",
        "cik": "SYNTHETIC_CIK",
        "last_updated_utc": "2026-01-22T00:00:00Z",
        "source_category": "synthetic_reference_metadata_shape",
        "official_doc_status": "field-category placeholder only",
        "candidate_only": True,
        "non_claims": list(_SYNTHETIC_POLYGON_REFERENCE_TICKER_NON_CLAIMS),
    }


def expected_synthetic_polygon_reference_ticker_json() -> str:
    """Return the pinned compact JSON payload for the synthetic ticker fixture."""

    return _EXPECTED_SYNTHETIC_POLYGON_REFERENCE_TICKER_JSON


_EXPECTED_SYNTHETIC_POLYGON_REFERENCE_TICKER_JSON = (
    '{"ticker":"SYNREF001","name":"Synthetic Reference Ticker Placeholder",'
    '"market":"synthetic_market","locale":"synthetic_locale",'
    '"primary_exchange":"SYNTHETIC_EXCHANGE","type":"synthetic_reference_type",'
    '"active":false,"currency_name":"synthetic_currency",'
    '"composite_figi":"SYNTHETIC_COMPOSITE_FIGI",'
    '"share_class_figi":"SYNTHETIC_SHARE_CLASS_FIGI","cik":"SYNTHETIC_CIK",'
    '"last_updated_utc":"2026-01-22T00:00:00Z",'
    '"source_category":"synthetic_reference_metadata_shape",'
    '"official_doc_status":"field-category placeholder only","candidate_only":true,'
    '"non_claims":["not Polygon approval","not Massive approval",'
    '"not endpoint approval","not source approval","not data approval",'
    '"not universe approval","not benchmark approval","not cash proxy approval",'
    '"not evidence approval","not return-construction approval",'
    '"not no-lookahead approval","not strategy validation",'
    '"not trading readiness"]}'
)
