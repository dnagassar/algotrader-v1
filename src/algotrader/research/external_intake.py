"""Advisory-only metadata contract for external research outputs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from algotrader.errors import ValidationError

__all__ = [
    "EXTERNAL_RESEARCH_SOURCE_TYPES",
    "ExternalResearchIntake",
]


EXTERNAL_RESEARCH_SOURCE_TYPES = (
    "quantconnect",
    "vectorbt",
    "notebook",
    "perplexity",
    "claude",
    "gemini",
    "paper",
    "manual",
    "other",
)
_INTAKE_FIELD_NAMES = (
    "source_name",
    "source_type",
    "strategy_name",
    "summary",
    "universe",
    "timeframe",
    "assumptions",
    "limitations",
    "evidence_links",
    "created_at",
    "advisory_only",
)
_TUPLE_FIELD_NAMES = frozenset(
    ("universe", "assumptions", "limitations", "evidence_links")
)
_TEXT_FIELD_NAMES = frozenset(
    (
        "source_name",
        "strategy_name",
        "summary",
        "universe",
        "timeframe",
        "assumptions",
        "limitations",
        "evidence_links",
    )
)
_FORBIDDEN_TEXT_FRAGMENTS = (
    "access token",
    "account id",
    "alpaca order",
    "api key",
    "apikey",
    "approval status",
    "approved for",
    "approved to",
    "backtest result",
    "benchmark comparison",
    "bearer ",
    "beats benchmark",
    "broker account",
    "broker order",
    "capital allocation",
    "cagr",
    "client secret",
    "drawdown",
    "fill price",
    "filled quantity",
    "live trading",
    "market order",
    "order instruction",
    "outperforms benchmark",
    "password",
    "place order",
    "position size",
    "position sizing",
    "profit factor",
    "profitability",
    "profitable",
    "runtime state",
    "secret=",
    "sharpe",
    "signal validation",
    "sortino",
    "strategy approval",
    "submit order",
    "target weight",
    "token=",
    "trading ready",
    "validated for",
    "validation status",
    "win rate",
)


@dataclass(frozen=True, slots=True)
class ExternalResearchIntake:
    """Metadata-only record for untrusted external research inputs."""

    source_name: str
    source_type: str
    strategy_name: str
    summary: str
    universe: tuple[str, ...]
    timeframe: str
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    evidence_links: tuple[str, ...]
    created_at: date
    advisory_only: bool = True

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic JSON-compatible metadata representation."""
        payload: dict[str, object] = {}

        for field_name in _INTAKE_FIELD_NAMES:
            value = getattr(self, field_name)
            if field_name in _TUPLE_FIELD_NAMES:
                payload[field_name] = list(value)
            elif field_name == "created_at":
                payload[field_name] = _serialize_plain_date(value)
            else:
                payload[field_name] = value

        return payload

    @classmethod
    def from_dict(cls, payload: object) -> "ExternalResearchIntake":
        """Restore an intake record from strict JSON-compatible metadata."""
        if not isinstance(payload, dict):
            raise ValidationError("external research intake payload must be a dict.")

        _validate_intake_payload_fields(payload)
        values: dict[str, object] = {}

        for field_name in _INTAKE_FIELD_NAMES:
            value = payload[field_name]
            if field_name in _TUPLE_FIELD_NAMES:
                values[field_name] = _deserialize_string_list(value, field_name)
            elif field_name == "created_at":
                values[field_name] = _deserialize_plain_date(value, field_name)
            else:
                values[field_name] = value

        return cls(**values)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_name",
            _required_string(self.source_name, "source_name"),
        )
        object.__setattr__(
            self,
            "source_type",
            _allowed_string(
                self.source_type,
                "source_type",
                EXTERNAL_RESEARCH_SOURCE_TYPES,
            ),
        )
        object.__setattr__(
            self,
            "strategy_name",
            _required_string(self.strategy_name, "strategy_name"),
        )
        object.__setattr__(self, "summary", _required_string(self.summary, "summary"))
        object.__setattr__(
            self,
            "universe",
            _string_tuple(self.universe, "universe"),
        )
        object.__setattr__(
            self,
            "timeframe",
            _required_string(self.timeframe, "timeframe"),
        )
        object.__setattr__(
            self,
            "assumptions",
            _string_tuple(self.assumptions, "assumptions"),
        )
        object.__setattr__(
            self,
            "limitations",
            _string_tuple(self.limitations, "limitations"),
        )
        object.__setattr__(
            self,
            "evidence_links",
            _string_tuple(self.evidence_links, "evidence_links"),
        )
        object.__setattr__(
            self,
            "created_at",
            _plain_date(self.created_at, "created_at"),
        )
        object.__setattr__(
            self,
            "advisory_only",
            _required_true(self.advisory_only, "advisory_only"),
        )
        _validate_advisory_metadata_text(self)


def _required_string(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} is required.")
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} is required.")
    return normalized


def _allowed_string(
    value: str,
    field_name: str,
    allowed_values: tuple[str, ...],
) -> str:
    normalized = _required_string(value, field_name)
    if normalized not in allowed_values:
        allowed = ", ".join(allowed_values)
        raise ValidationError(f"{field_name} must be one of: {allowed}.")
    return normalized


def _string_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    if isinstance(values, str):
        raise ValidationError(f"{field_name} must be an iterable of strings.")

    try:
        items = tuple(values)
    except TypeError as exc:
        raise ValidationError(f"{field_name} must be an iterable of strings.") from exc

    return tuple(
        _required_string(value, f"{field_name}[{index}]")
        for index, value in enumerate(items)
    )


def _plain_date(value: date, field_name: str) -> date:
    if type(value) is not date:
        raise ValidationError(f"{field_name} must be a date.")
    return value


def _required_true(value: bool, field_name: str) -> bool:
    if value is not True:
        raise ValidationError(f"{field_name} must be exactly True.")
    return value


def _serialize_plain_date(value: object) -> str:
    if type(value) is not date:
        raise ValidationError("created_at must be a plain date.")
    return value.isoformat()


def _deserialize_plain_date(value: object, field_name: str) -> date:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be an ISO date string.")

    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} must be an ISO YYYY-MM-DD date string."
        ) from exc

    if parsed.isoformat() != value:
        raise ValidationError(f"{field_name} must use YYYY-MM-DD date format.")
    return parsed


def _deserialize_string_list(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list of strings.")
    return tuple(value)


def _validate_intake_payload_fields(payload: dict[object, object]) -> None:
    unknown_fields = tuple(
        field_name for field_name in payload if field_name not in _INTAKE_FIELD_NAMES
    )
    if unknown_fields:
        unknown = ", ".join(str(field_name) for field_name in unknown_fields)
        raise ValidationError(f"unknown external research intake field(s): {unknown}.")

    missing_fields = tuple(
        field_name for field_name in _INTAKE_FIELD_NAMES if field_name not in payload
    )
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValidationError(f"missing external research intake field(s): {missing}.")


def _validate_advisory_metadata_text(intake: ExternalResearchIntake) -> None:
    for field_name in _TEXT_FIELD_NAMES:
        value = getattr(intake, field_name)
        if isinstance(value, tuple):
            for index, item in enumerate(value):
                _reject_forbidden_text(item, f"{field_name}[{index}]")
        else:
            _reject_forbidden_text(value, field_name)


def _reject_forbidden_text(value: str, field_name: str) -> None:
    normalized = value.lower().replace("_", " ").replace("-", " ")
    for fragment in _FORBIDDEN_TEXT_FRAGMENTS:
        if fragment in normalized:
            raise ValidationError(
                f"{field_name} contains non-advisory research metadata."
            )
