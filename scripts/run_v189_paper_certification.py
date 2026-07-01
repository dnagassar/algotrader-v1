"""Run the v1.89 bounded SPY paper certification drill."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient
from algotrader.execution.paper_mutation_oms import (
    ALLOWED_LABELS,
    EXPECTED_PAPER_ACCOUNT_ENV,
    PaperCertificationRuntime,
    PaperMutationGateway,
    V189_DEFAULT_OUTPUT_ROOT,
    paper_config_from_env_aliases,
    run_paper_certification_drill,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="run_v189_paper_certification.py")
    parser.add_argument(
        "--output-root",
        default=V189_DEFAULT_OUTPUT_ROOT,
        help="Runtime artifact root for the v1.89 certification packet.",
    )
    parser.add_argument(
        "--expected-paper-account-id",
        default=None,
        help=(
            "Expected Alpaca paper account id. Defaults to "
            f"{EXPECTED_PAPER_ACCOUNT_ENV}."
        ),
    )
    parser.add_argument(
        "--client-order-id",
        default=None,
        help="Optional unique client order id for this bounded drill run.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run id stored in the drill artifacts.",
    )
    parser.add_argument(
        "--extra-label",
        action="append",
        default=[],
        dest="extra_labels",
        help="Additional non-secret safety label to include in artifacts.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=45.0,
        help="Bounded reconciliation timeout after cancellation request.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=2.0,
        help="Polling interval during reconciliation.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="text",
        dest="output_format",
        help="Safe summary output format.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    env = dict(os.environ)
    expected_account = (
        args.expected_paper_account_id
        if args.expected_paper_account_id is not None
        else env.get(EXPECTED_PAPER_ACCOUNT_ENV, "")
    )
    paper_config = paper_config_from_env_aliases(env)
    try:
        client = AlpacaSdkClient(paper_config)
        gateway = PaperMutationGateway(client)
    except Exception as exc:
        gateway = PaperMutationGateway(_UnavailablePaperClient(str(exc)))
    latest = run_paper_certification_drill(
        paper_config=paper_config,
        gateway=gateway,
        runtime=PaperCertificationRuntime(
            output_root=Path(args.output_root),
            expected_paper_account_id=str(expected_account or ""),
            timeout_seconds=args.timeout_seconds,
            poll_interval_seconds=args.poll_interval_seconds,
            client_order_id=str(args.client_order_id or ""),
            run_id=str(args.run_id or ""),
            labels=tuple(dict.fromkeys((*ALLOWED_LABELS, *args.extra_labels))),
        ),
        env=env,
    )
    summary = _safe_summary(latest, Path(args.output_root))
    if args.output_format == "json":
        print(json.dumps(summary, sort_keys=True, indent=2))
    else:
        print(f"outcome_classification={summary['outcome_classification']}")
        print(f"blocker={summary['blocker'] or 'none'}")
        print(f"client_order_id={summary['client_order_id']}")
        print(f"paper_submit_performed={summary['paper_submit_performed']}")
        print(f"broker_mutation_performed={summary['broker_mutation_performed']}")
        print(f"artifact_root={summary['artifact_root']}")
    return 0


class _UnavailablePaperClient:
    def __init__(self, message: str) -> None:
        self.message = message

    @property
    def raw_trading_client(self) -> "_UnavailablePaperClient":
        return self

    def get_account(self) -> object:
        raise RuntimeError(self.message)

    def get_positions(self) -> list[object]:
        raise RuntimeError(self.message)

    def get_orders(self, query: object) -> list[object]:
        raise RuntimeError(self.message)

    def get_asset(self, symbol: str) -> object:
        raise RuntimeError(self.message)

    def submit_order(self, request: object) -> object:
        raise RuntimeError(self.message)


def _safe_summary(latest: dict[str, object], output_root: Path) -> dict[str, object]:
    preflight = latest.get("preflight")
    if not isinstance(preflight, dict):
        preflight = {}
    return {
        "outcome_classification": latest.get("outcome_classification", ""),
        "blocker": latest.get("blocker", ""),
        "client_order_id": latest.get("client_order_id", ""),
        "paper_submit_performed": latest.get("paper_submit_performed", False),
        "broker_mutation_performed": latest.get("broker_mutation_performed", False),
        "APP_PROFILE_is_paper": preflight.get("APP_PROFILE_is_paper", False),
        "paper_credentials_loaded": preflight.get("paper_credentials_loaded", False),
        "paper_endpoint_exact_match": preflight.get(
            "paper_endpoint_exact_match",
            False,
        ),
        "expected_paper_account_match": preflight.get(
            "expected_paper_account_match",
            False,
        ),
        "credential_values_exposed": False,
        "artifact_root": str(output_root),
    }


if __name__ == "__main__":
    sys.exit(main())
