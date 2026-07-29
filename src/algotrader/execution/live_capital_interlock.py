"""Live-capital interlock: the paper-only execution boundary guard.

This is the single choke-point every autonomous broker-touching action must pass
before it may run. It refuses anything that is not the pinned paper profile and a
paper endpoint, and it fails closed on any live signal it can detect in the
environment. The live-capital gate is held both by the operator's standing policy
and by this structural guard: the autonomous path cannot reach a live endpoint or
submit a live order while this interlock stands in front of it.

Safety: it composes the existing :func:`algotrader.config.require_paper_profile`
boundary and adds explicit live-signal detection. It reads configuration presence
and endpoint *shape* only — it never reads, logs, or returns a credential value,
imports no broker SDK, opens no socket, and performs no order, mutation, or live
action. Detected offending environment variables are reported by *name* only.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os

from algotrader.config import (
    AlpacaPaperConfig,
    ConfigValidationError,
    LIVE_APP_PROFILE,
    PAPER_APP_PROFILE,
    require_paper_profile,
)
from algotrader.errors import ValidationError

__all__ = [
    "ENDPOINT_LIVE",
    "ENDPOINT_PAPER",
    "ENDPOINT_UNKNOWN",
    "LIVE_ENABLE_ENV_KEYS",
    "LIVE_HOST_MARKER",
    "LiveCapitalGateError",
    "LiveCapitalInterlockVerdict",
    "evaluate_live_capital_interlock",
    "require_live_capital_interlock",
]


# The live Alpaca trading host. A base URL containing this marker but not the
# paper marker is a live endpoint and is refused.
LIVE_HOST_MARKER = "api.alpaca.markets"
_PAPER_MARKER = "paper"

ENDPOINT_PAPER = "paper"
ENDPOINT_LIVE = "live"
ENDPOINT_UNKNOWN = "unknown"

# Environment variables that, when set truthy, explicitly ask for live trading.
# Presence of any of these is a hard refusal.
LIVE_ENABLE_ENV_KEYS = (
    "ALGO_TRADER_ALLOW_LIVE",
    "ALGO_TRADER_ALLOW_LIVE_TRADING",
    "ALLOW_LIVE_TRADING",
    "ENABLE_LIVE_TRADING",
    "LIVE_TRADING_ENABLED",
)

# Environment variables that carry a broker base URL. If any points at the live
# host without the paper marker, it is a hard refusal.
_BASE_URL_ENV_KEYS = (
    "ALPACA_BASE_URL",
    "ALPACA_LIVE_BASE_URL",
    "ALPACA_PAPER_BASE_URL",
    "APCA_API_BASE_URL",
)

_TRUTHY = frozenset({"1", "true", "yes", "on", "enabled"})


class LiveCapitalGateError(RuntimeError):
    """Raised when the live-capital interlock refuses an execution boundary."""


@dataclass(frozen=True, slots=True)
class LiveCapitalInterlockVerdict:
    """Result of evaluating the paper-only execution boundary.

    ``paper_boundary_ok`` is ``True`` only when the profile is paper, the
    resolved endpoint is a paper endpoint, and no live signal was detected. The
    ``live_signals`` and ``blockers`` name offending variables/reasons only; no
    credential value is ever included. ``live_authorized`` is always ``False``.
    """

    paper_boundary_ok: bool
    app_profile: str
    profile_is_paper: bool
    endpoint_class: str
    paper_endpoint_ok: bool
    expected_paper_account_present: bool
    live_signals: tuple[str, ...]
    blockers: tuple[str, ...]
    live_authorized: bool = False

    def __post_init__(self) -> None:
        if self.live_authorized is not False:
            raise ValidationError("live_authorized must be false.")
        object.__setattr__(self, "live_signals", tuple(self.live_signals))
        object.__setattr__(self, "blockers", tuple(self.blockers))

    def to_dict(self) -> dict[str, object]:
        return {
            "paper_boundary_ok": self.paper_boundary_ok,
            "app_profile": self.app_profile,
            "profile_is_paper": self.profile_is_paper,
            "endpoint_class": self.endpoint_class,
            "paper_endpoint_ok": self.paper_endpoint_ok,
            "expected_paper_account_present": self.expected_paper_account_present,
            "live_signals": list(self.live_signals),
            "blockers": list(self.blockers),
            "live_authorized": self.live_authorized,
            "submitted": False,
            "mutated": False,
            "broker_action_performed": False,
            "network_access_attempted": False,
            "credential_access_attempted": False,
        }


def _classify_endpoint(base_url: str) -> str:
    lowered = base_url.strip().lower()
    if not lowered:
        return ENDPOINT_UNKNOWN
    if _PAPER_MARKER in lowered:
        return ENDPOINT_PAPER
    if LIVE_HOST_MARKER in lowered:
        return ENDPOINT_LIVE
    return ENDPOINT_UNKNOWN


def _detect_live_signals(source: Mapping[str, str]) -> list[str]:
    signals: list[str] = []
    for key in LIVE_ENABLE_ENV_KEYS:
        value = source.get(key)
        if isinstance(value, str) and value.strip().lower() in _TRUTHY:
            signals.append(f"live_enable_flag:{key}")

    for key in _BASE_URL_ENV_KEYS:
        value = source.get(key)
        if not isinstance(value, str):
            continue
        lowered = value.strip().lower()
        if LIVE_HOST_MARKER in lowered and _PAPER_MARKER not in lowered:
            signals.append(f"live_base_url:{key}")

    # Catch-all: any other variable whose value points at the live host without
    # the paper marker. Only the variable name is recorded, never the value.
    known = set(LIVE_ENABLE_ENV_KEYS) | set(_BASE_URL_ENV_KEYS)
    for key, value in source.items():
        if key in known or not isinstance(value, str):
            continue
        lowered = value.strip().lower()
        if LIVE_HOST_MARKER in lowered and _PAPER_MARKER not in lowered:
            signals.append(f"live_host_in_env:{key}")

    return sorted(dict.fromkeys(signals))


def evaluate_live_capital_interlock(
    env: Mapping[str, str] | None = None,
    *,
    require_broker_credentials: bool = True,
) -> LiveCapitalInterlockVerdict:
    """Evaluate the paper-only execution boundary without raising.

    Returns a verdict describing whether an autonomous broker-touching action may
    proceed. This never grants live authority; ``live_authorized`` is always
    ``False``.
    """

    source = os.environ if env is None else env
    if not isinstance(source, Mapping):
        raise ValidationError("env must be a mapping.")
    if type(require_broker_credentials) is not bool:
        raise ValidationError("require_broker_credentials must be a boolean.")

    config = AlpacaPaperConfig.from_env(source)
    app_profile = config.app_profile.strip().lower()
    profile_is_paper = app_profile == PAPER_APP_PROFILE

    endpoint_class = _classify_endpoint(config.alpaca_paper_base_url)
    paper_endpoint_ok = endpoint_class == ENDPOINT_PAPER

    live_signals = _detect_live_signals(source)

    expected_present = _present(source.get("EXPECTED_PAPER_ACCOUNT_ID"))

    blockers: list[str] = []
    if not profile_is_paper:
        if app_profile == LIVE_APP_PROFILE:
            blockers.append("app_profile_is_live")
        else:
            blockers.append(f"app_profile_not_paper:{app_profile or 'unset'}")
    if not paper_endpoint_ok:
        blockers.append(f"endpoint_not_paper:{endpoint_class}")
    if live_signals:
        blockers.append("live_signal_detected")

    # Compose the existing config boundary as a defence-in-depth check. It should
    # already agree; a disagreement is itself a blocker.
    if (
        require_broker_credentials
        and profile_is_paper
        and paper_endpoint_ok
        and not live_signals
    ):
        try:
            require_paper_profile(config)
        except ConfigValidationError as exc:
            blockers.append(f"config_paper_boundary_rejected:{type(exc).__name__}")

    paper_boundary_ok = not blockers

    return LiveCapitalInterlockVerdict(
        paper_boundary_ok=paper_boundary_ok,
        app_profile=app_profile or "unset",
        profile_is_paper=profile_is_paper,
        endpoint_class=endpoint_class,
        paper_endpoint_ok=paper_endpoint_ok,
        expected_paper_account_present=expected_present,
        live_signals=tuple(live_signals),
        blockers=tuple(sorted(dict.fromkeys(blockers))),
    )


def require_live_capital_interlock(
    env: Mapping[str, str] | None = None,
    *,
    require_broker_credentials: bool = True,
) -> LiveCapitalInterlockVerdict:
    """Return the verdict if the paper boundary holds, else raise.

    Every autonomous broker-touching action must call this and proceed only on a
    returned (passing) verdict. It refuses fail-closed: any missing paper
    profile, non-paper endpoint, or live signal raises
    :class:`LiveCapitalGateError`.
    """

    verdict = evaluate_live_capital_interlock(
        env,
        require_broker_credentials=require_broker_credentials,
    )
    if not verdict.paper_boundary_ok:
        raise LiveCapitalGateError(
            "live-capital interlock refused execution boundary: "
            + (", ".join(verdict.blockers) or "unknown_blocker")
        )
    return verdict


def _present(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""
