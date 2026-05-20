from dataclasses import is_dataclass
from datetime import date, datetime
from decimal import Decimal
import re
from types import ModuleType


ALLOWED_PLANNING_STATES = frozenset({"candidate_only", "blocked", "deferred"})
REJECTED_PLANNING_STATE_EXAMPLES = ("approved", " approved ", "Approved")
REQUIRED_EVIDENCE_METADATA_NON_CLAIM = "not evidence approval"

REAL_ETF_TICKERS = (
    "SPY",
    "QQQ",
    "IWM",
    "DIA",
    "VTI",
    "EFA",
    "EEM",
    "TLT",
    "GLD",
    "AGG",
    "BND",
    "VNQ",
    "XLF",
    "XLK",
    "XLE",
    "IVV",
    "VOO",
)

REAL_VENDOR_OR_SOURCE_IDENTIFIERS = (
    "alpaca",
    "alphavantage",
    "alpha_vantage",
    "bloomberg",
    "eodhd",
    "factset",
    "fmp",
    "fred",
    "iex",
    "intrinio",
    "morningstar",
    "nasdaq",
    "polygon",
    "quantconnect",
    "quandl",
    "refinitiv",
    "stooq",
    "tiingo",
    "yahoo",
    "yfinance",
)

FORBIDDEN_RUNTIME_FIELD_NAMES = frozenset(
    {
        "account",
        "account_id",
        "allocation",
        "broker",
        "broker_call",
        "broker_calls",
        "capital_allocation",
        "credential",
        "credentials",
        "execution",
        "execution_intent",
        "fill",
        "live",
        "order",
        "order_intent",
        "paper_eligible",
        "portfolio",
        "position",
        "position_size",
        "position_sizing",
        "runtime",
        "scheduler",
        "target_weight",
        "tradable",
        "trading_action",
    }
)

FORBIDDEN_SELECTION_FIELD_NAMES = frozenset(
    {
        "candidate_discovery",
        "candidate_discovery_fields",
        "rank",
        "ranking",
        "recommendation",
        "recommendations",
        "score",
        "scoring",
    }
)

FORBIDDEN_RAW_MARKET_FIELD_NAMES = frozenset(
    {
        "adjusted_close",
        "adj_close",
        "close",
        "dividend",
        "high",
        "low",
        "ohlc",
        "ohlcv",
        "open",
        "price",
        "prices",
        "split",
        "volume",
    }
)

FORBIDDEN_NEW_REPLAY_METRIC_KEYS = frozenset(
    {
        "alpha",
        "benchmark_relative_return",
        "beta",
        "cagr",
        "drawdown",
        "information_ratio",
        "max_drawdown",
        "sharpe",
    }
)

FORBIDDEN_EVIDENCE_APPROVAL_FIELD_NAMES = frozenset(
    {
        "evidence_approval",
        "evidence_validated",
        "validated_evidence",
    }
)

SENSITIVE_TEXT_TERMS = (
    "approved",
    "approval",
    "validated",
    "tradable",
    "live",
    "paper_eligible",
    "order",
    "orders",
    "broker",
    "portfolio",
    "position size",
    "position sizing",
    "signal",
    "evaluator",
)

NEGATIVE_MARKERS = (
    "not ",
    "no ",
    "does not",
    "do not",
    "cannot ",
)

_OBJECT_REPR_PATTERN = re.compile(r"<[^>]+ at 0x[0-9a-fA-F]+>")
_MEMORY_ADDRESS_PATTERN = re.compile(r"\b0x[0-9a-fA-F]{6,}\b")


def assert_planning_states_are_non_approved(
    states: object,
    *,
    context: str,
) -> None:
    observed = tuple(states)
    unexpected = sorted(set(observed) - ALLOWED_PLANNING_STATES)

    assert observed, f"{context} should include at least one planning state"
    assert unexpected == [], (
        f"{context} contains states outside the non-approved fixture set: "
        f"{unexpected!r}"
    )

    for rejected_state in REJECTED_PLANNING_STATE_EXAMPLES:
        assert rejected_state not in observed, (
            f"{context} unexpectedly contains rejected approval label "
            f"{rejected_state!r}"
        )


def approval_states(value: object) -> tuple[str, ...]:
    states: list[str] = []

    if isinstance(value, dict):
        approval_state = value.get("approval_state")
        if isinstance(approval_state, str):
            states.append(approval_state)
        for item in value.values():
            states.extend(approval_states(item))
    elif isinstance(value, list):
        for item in value:
            states.extend(approval_states(item))

    return tuple(states)


def assert_json_payload_uses_only_primitives(
    value: object,
    *,
    context: str,
) -> None:
    _assert_json_payload_uses_only_primitives(value, path=context)


def all_serialized_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key) for key in value}
        for item in value.values():
            keys.update(all_serialized_keys(item))
        return keys

    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(all_serialized_keys(item))
        return keys

    return set()


def assert_no_forbidden_terms(
    text: str,
    forbidden_terms: tuple[str, ...],
    *,
    context: str,
) -> None:
    hits = [term for term in forbidden_terms if term in text]
    assert hits == [], f"{context} contains forbidden terms: {hits!r}"


def assert_no_real_etf_tickers(serialized: str, *, context: str) -> None:
    for ticker in REAL_ETF_TICKERS:
        assert not re.search(
            rf"(?<![A-Z0-9_]){re.escape(ticker)}(?![A-Z0-9_])",
            serialized,
        ), f"{context} contains real ETF ticker {ticker!r}"


def assert_no_real_vendor_or_source_identifiers(
    serialized: str,
    *,
    context: str,
) -> None:
    lowered = serialized.lower()
    hits = [
        identifier
        for identifier in REAL_VENDOR_OR_SOURCE_IDENTIFIERS
        if identifier in lowered
    ]
    assert hits == [], f"{context} contains real vendor/source identifiers: {hits!r}"


def assert_no_raw_market_data_surface(
    payload: dict[str, object],
    serialized: str,
    *,
    context: str,
) -> None:
    raw_keys = all_serialized_keys(payload) & FORBIDDEN_RAW_MARKET_FIELD_NAMES
    assert raw_keys == set(), f"{context} contains raw market-data keys: {raw_keys!r}"

    lowered = serialized.lower()
    assert_no_forbidden_terms(
        lowered,
        (
            "adjusted close",
            "daily return",
            "return series",
            "ohlc",
            "volume",
        ),
        context=context,
    )
    assert "$" not in serialized, f"{context} contains currency/price-like text"


def scrub_negative_assertions(
    lowered_json: str,
    payload: dict[str, object],
    *,
    field_names: tuple[str, ...] = (
        "methodology_non_claims",
        "non_claims",
        "limitations",
    ),
) -> str:
    scrubbed = lowered_json
    for text in sorted(
        _all_text_values_for_fields(payload, field_names=field_names),
        key=len,
        reverse=True,
    ):
        scrubbed = scrubbed.replace(text.lower(), "")
    return scrubbed


def assert_required_non_claims_present(
    actual_non_claims: object,
    required_non_claims: set[str],
    *,
    context: str,
) -> None:
    missing = sorted(required_non_claims - set(actual_non_claims))
    assert missing == [], f"{context} is missing required non-claims: {missing!r}"


def assert_non_claims_include_not_evidence_approval(
    non_claims: object,
    *,
    context: str,
) -> None:
    assert REQUIRED_EVIDENCE_METADATA_NON_CLAIM in non_claims, (
        f"{context} must keep evidence_refs metadata-only via "
        f"{REQUIRED_EVIDENCE_METADATA_NON_CLAIM!r}"
    )


def assert_no_evidence_approval_fields(
    payload: object,
    *,
    context: str,
) -> None:
    evidence_keys = all_serialized_keys(payload) & FORBIDDEN_EVIDENCE_APPROVAL_FIELD_NAMES
    assert evidence_keys == set(), (
        f"{context} contains evidence approval/validation fields: {evidence_keys!r}"
    )


def assert_sensitive_terms_are_negative_only(
    payload: dict[str, object],
    *,
    context: str,
) -> None:
    for key in all_serialized_keys(payload):
        lowered_key = key.lower()
        if "approval" in lowered_key:
            assert lowered_key == "approval_state", (
                f"{context} contains unexpected approval key {key!r}"
            )
        for forbidden_key in (
            "approved",
            "validated",
            "tradable",
            "paper_eligible",
            "position_sizing",
        ):
            assert forbidden_key not in lowered_key, (
                f"{context} contains sensitive key {key!r}"
            )

    for path, text in _string_values(payload):
        lowered = text.lower()
        if not any(term in lowered for term in SENSITIVE_TEXT_TERMS):
            continue
        assert _is_negative_assertion(path, lowered), (
            f"{context} contains non-negative sensitive text at {'.'.join(path)}: "
            f"{text!r}"
        )


def _assert_json_payload_uses_only_primitives(
    value: object,
    *,
    path: str,
) -> None:
    assert not is_dataclass(value), f"{path} contains dataclass value {type(value)!r}"
    assert not isinstance(value, tuple), f"{path} contains tuple value"
    assert not isinstance(value, set), f"{path} contains set value"
    assert not isinstance(value, Decimal), f"{path} contains Decimal value"
    assert not isinstance(value, (date, datetime)), f"{path} contains date/datetime"
    assert not callable(value), f"{path} contains callable value"
    assert not isinstance(value, ModuleType), f"{path} contains module value"

    if value is None or type(value) in (str, bool, int, float):
        if type(value) is str:
            assert not _OBJECT_REPR_PATTERN.search(value), (
                f"{path} contains object repr text {value!r}"
            )
            assert not _MEMORY_ADDRESS_PATTERN.search(value), (
                f"{path} contains memory address text {value!r}"
            )
        return

    if type(value) is list:
        for index, item in enumerate(value):
            _assert_json_payload_uses_only_primitives(
                item,
                path=f"{path}[{index}]",
            )
        return

    if type(value) is dict:
        for key, item in value.items():
            assert type(key) is str, f"{path} contains non-string key {key!r}"
            assert not _OBJECT_REPR_PATTERN.search(key), (
                f"{path} contains object repr key {key!r}"
            )
            assert not _MEMORY_ADDRESS_PATTERN.search(key), (
                f"{path} contains memory address key {key!r}"
            )
            _assert_json_payload_uses_only_primitives(
                item,
                path=f"{path}.{key}",
            )
        return

    raise AssertionError(f"{path} contains non-primitive value {type(value)!r}")


def _all_text_values_for_fields(
    value: object,
    *,
    field_names: tuple[str, ...],
    path: tuple[str, ...] = (),
) -> tuple[str, ...]:
    values: list[str] = []

    if isinstance(value, dict):
        for key, item in value.items():
            values.extend(
                _all_text_values_for_fields(
                    item,
                    field_names=field_names,
                    path=(*path, str(key)),
                )
            )
    elif isinstance(value, list):
        field_name = path[-1] if path else "item"
        for item in value:
            values.extend(
                _all_text_values_for_fields(
                    item,
                    field_names=field_names,
                    path=(*path, field_name),
                )
            )
    elif isinstance(value, str) and path and path[-1] in field_names:
        values.append(value)

    return tuple(values)


def _string_values(
    value: object,
    path: tuple[str, ...] = (),
) -> tuple[tuple[tuple[str, ...], str], ...]:
    values: list[tuple[tuple[str, ...], str]] = []

    if isinstance(value, dict):
        for key, item in value.items():
            values.extend(_string_values(item, (*path, str(key))))
    elif isinstance(value, list):
        field_name = path[-1] if path else "item"
        for item in value:
            values.extend(_string_values(item, (*path, field_name)))
    elif isinstance(value, str):
        values.append((path, value))

    return tuple(values)


def _is_negative_assertion(path: tuple[str, ...], lowered: str) -> bool:
    if path and path[-1] in {"non_claims", "limitations", "methodology_non_claims"}:
        return any(marker in lowered for marker in NEGATIVE_MARKERS)

    return any(marker in lowered for marker in ("does not", "do not"))
