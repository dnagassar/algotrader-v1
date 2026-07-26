"""Impure CLI composition root for tomorrow_crypto_trader_demo."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path

from algotrader.execution.tomorrow_crypto_trader_demo import (
    BROKER_OBSERVED_CONSISTENCY_FIELDS,
    COMMAND_NAME,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_SCENARIO,
    OFFLINE_PAPER_ENVIRONMENT,
    _bool_text,
    _json_safe,
    _run_summary_payload,
    _string_sequence,
    _text,
    run_tomorrow_crypto_trader_demo,
    validate_tomorrow_crypto_trader_demo,
)
from algotrader.execution.tomorrow_crypto_trader_demo_broker_client_adapter import (
    build_alpaca_read_client,
    read_paper_environment_from_os,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=COMMAND_NAME,
        description="Run or validate the v6.1 crypto SimBroker operating loop.",
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--state-root", type=Path, default=None)
    parser.add_argument(
        "--mode", choices=("SimBroker", "AlpacaPaper"), default="SimBroker"
    )
    parser.add_argument("--allow-alpaca-paper-mutation", action="store_true")
    parser.add_argument("--broker-observed-readiness", action="store_true")
    parser.add_argument("--allow-alpaca-paper-read", action="store_true")
    parser.add_argument("--as-of", default="")
    parser.add_argument(
        "--scenario",
        choices=("risk_on", "risk_off", "all_blocked", "bad_data"),
        default=DEFAULT_SCENARIO,
    )
    parser.add_argument("--reset-state", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    if args.validate_only:
        validation = validate_tomorrow_crypto_trader_demo(args.output_root)
        if args.format == "json":
            print(json.dumps(_json_safe(validation), sort_keys=True))
        else:
            print(
                "tomorrow_crypto_trader_demo_validation_status="
                f"{validation['validation_status']}"
            )
            for field in BROKER_OBSERVED_CONSISTENCY_FIELDS:
                value = validation.get(field)
                if type(value) is bool:
                    rendered = _bool_text(value)
                else:
                    rendered = _text(value)
                print(f"tomorrow_crypto_trader_demo_validator_{field}={rendered}")
            print("errors=" + ",".join(_string_sequence(validation.get("errors"))))
        return 0 if validation["validation_status"] == "passed" else 1

    broker_factory = (
        build_alpaca_read_client
        if (args.broker_observed_readiness and args.allow_alpaca_paper_read)
        else None
    )
    paper_env = (
        read_paper_environment_from_os()
        if (args.broker_observed_readiness or args.mode == "AlpacaPaper")
        else OFFLINE_PAPER_ENVIRONMENT
    )

    packet = run_tomorrow_crypto_trader_demo(
        output_root=args.output_root,
        mode=args.mode,
        allow_alpaca_paper_mutation=args.allow_alpaca_paper_mutation,
        broker_observed_readiness=args.broker_observed_readiness,
        allow_alpaca_paper_read=args.allow_alpaca_paper_read,
        as_of=args.as_of or None,
        state_root=args.state_root,
        scenario=args.scenario,
        reset_state=args.reset_state,
        write_artifacts=True,
        broker_observed_client_factory=broker_factory,
        paper_environment=paper_env,
    )
    if args.format == "json":
        print(json.dumps(_json_safe(packet), sort_keys=True))
    else:
        run_summary = _run_summary_payload(packet)
        for line in _string_sequence(run_summary.get("console_lines")):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
