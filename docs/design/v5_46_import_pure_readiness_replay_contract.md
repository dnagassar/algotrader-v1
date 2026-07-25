# V5.46 Import-Pure Crypto Readiness Replay Contract

## Status And Scope

- Milestone: `V5.46 — contract-first design for an import-pure crypto
  readiness replay command`.
- Parent milestone: `V5.45 — read-only executor reachability boundary
  audit` (`docs/design/v5_45_executor_reachability_boundary_audit.md`),
  whose "Selected next milestone: V5.46" section and
  `docs/agent_context/active_implementation.md` "Next Highest-Leverage
  Safe Action" both defined this contract's exact charter.
- This is a **frozen, standalone design contract**. It changes no `src`
  or `tests` file, adds no CLI subcommand, classifies no new action
  token, and touches `AUTONOMY_EXECUTOR_ALLOWLIST` nowhere. It is
  independently reviewable before any implementation work starts.
- Not strategy-profit, paper-order, broker-mutation, activation, or
  live-trading evidence. No credential was read, no network or broker
  call occurred, and no file outside `docs/` was modified while writing
  this contract.
- Working branch: `claude/v5.46-import-pure-readiness-replay-contract`.
  Base commit at session start: `9f0d45d9d02ed77aae157a619c2319df82939a1d`
  ("V5.45 correction: fix base-commit claim and reachability enumeration
  errors") — this branch was created carrying the full accepted V5.45
  history (`...1394be0 -> c1311b6 -> 9f0d45d`), not forked fresh from
  `main`; no rebase or branch switch was performed. Verified before any
  edit: branch, `HEAD`, `git status --porcelain`, staged/unstaged/
  untracked diffs (all clean), and credential/profile presence booleans
  (`APP_PROFILE`, every listed Alpaca credential alias,
  `ALGO_TRADER_ALLOW_NETWORK_TESTS`, `RUN_ALPACA_PAPER_INTEGRATION_TESTS`)
  — all absent/false.

## Method

Static, offline inspection only. No code executed, no `runs/` artifact
read or written, no network or broker call made. Every import-graph
claim below was verified two ways: (1) reading each source file's
top-of-file `import`/`from` statements directly, and (2) manually
walking the transitive closure of every module-level import reachable
from `tomorrow_crypto_trader_demo.py`, file by file, recorded in full
in "Root-Cause Import-Purity Analysis" below — not re-cited from the
V5.45 audit, re-derived from this worktree's checkout.

## Problem Restatement (From V5.45)

`crypto_supervised_readiness_trial.py` (`run_crypto_supervised_readiness_trial`)
writes exactly the artifact the `crypto_supervised_readiness_trial`
lane reads (`autonomy_supervisor.py:339-360`,
`artifact_relpath="crypto_supervised_readiness_trial/latest/readiness_packet.json"`),
is fully-defaulted, is decision-deterministic (two independent in-process
24-cycle replays produce identical receipt chains by construction), and
under default arguments (`broker_observed_readiness=False`,
`allow_alpaca_paper_read=False`) never attempts a broker read. It is
disqualified from the executor allowlist today purely on **import-graph**
grounds: its sole production import,
`from algotrader.execution.tomorrow_crypto_trader_demo import
run_tomorrow_crypto_trader_demo`
(`crypto_supervised_readiness_trial.py:22-24`), pulls in
`tomorrow_crypto_trader_demo.py`, which at module level (line 26-28) does:

```python
from algotrader.execution.alpaca_sdk_client import (
    crypto_market_data_symbol_normalization,
)
```

Importing `alpaca_sdk_client` at all — regardless of whether any function
in it is ever called — executes *its* module-level imports
(`alpaca_sdk_client.py:15-17`):

```python
from algotrader.config import AlpacaPaperConfig, require_paper_profile
from algotrader.execution.live_capital_interlock import require_live_capital_interlock
from algotrader.execution.alpaca_client import (...)
```

This is the entire defect: a profile/credential/live-interlock import
surface reachable purely by `import`-ing the module, independent of
runtime arguments. The executor's own docstring requires every
allowlisted command's producing module to be "verified to import no
network, broker, credential, or profile surface" — an import-graph
property, not a runtime-behavior one — and this chain fails it by
construction (`autonomy_offline_executor.py:11-14`).

## Root-Cause Import-Purity Analysis

The single offending edge is `tomorrow_crypto_trader_demo.py:26-28`. This
was proven, not assumed, by walking every other module-level import
`tomorrow_crypto_trader_demo.py` makes (`tomorrow_crypto_trader_demo.py:10-49`)
to its own module-level imports, recursively, until every leaf was stdlib
or `algotrader.errors`:

```
tomorrow_crypto_trader_demo.py
├── algotrader.core.types            -> algotrader.core.validation, algotrader.errors
├── algotrader.execution.alpaca_sdk_client   [OFFENDING EDGE — see below]
├── algotrader.execution.simulator   -> algotrader.core.types, algotrader.errors
├── algotrader.orchestration.execution_planning_flow
│     -> algotrader.orchestration.risk_execution_flow
├── algotrader.orchestration.execution_planning_policy
│     -> algotrader.orchestration.execution_planning_flow,
│        algotrader.orchestration.risk_execution_flow, algotrader.errors
├── algotrader.orchestration.risk_execution_flow
│     -> algotrader.orchestration.signal_risk_flow
├── algotrader.orchestration.screener_signal_flow
│     -> algotrader.core.types, algotrader.errors, algotrader.screener,
│        algotrader.signals.simple_rule
├── algotrader.orchestration.signal_risk_flow
│     -> algotrader.core.types, algotrader.orchestration.screener_signal_flow,
│        algotrader.portfolio.state, algotrader.risk.{config,engine,state}
├── algotrader.portfolio.state       -> algotrader.core.{types,validation}, algotrader.errors
├── algotrader.risk.config           -> algotrader.core.validation, algotrader.errors
├── algotrader.risk.engine           -> algotrader.core.{types,validation},
│                                        algotrader.errors, algotrader.portfolio.state,
│                                        algotrader.risk.{config,context,state}
├── algotrader.risk.state            -> algotrader.portfolio.state
├── algotrader.risk.context          -> algotrader.core.time, algotrader.core.validation,
│                                        algotrader.errors
├── algotrader.screener (__init__)   -> algotrader.screener.momentum
│     algotrader.screener.momentum   -> algotrader.core.types, algotrader.errors
├── algotrader.signals.crypto_trend  -> algotrader.core.time, algotrader.core.types,
│                                        algotrader.errors
├── algotrader.signals.simple_rule   -> algotrader.core.types, algotrader.core.validation,
│                                        algotrader.errors
├── algotrader.core.validation       -> algotrader.errors
├── algotrader.core.time             -> algotrader.errors
└── algotrader.errors                -> (stdlib only)

algotrader.execution.alpaca_sdk_client   [OFFENDING EDGE]
├── algotrader.config                     (AlpacaPaperConfig, require_paper_profile)
├── algotrader.execution.live_capital_interlock  (require_live_capital_interlock)
└── algotrader.execution.alpaca_client
```

Every leaf on every branch except the `alpaca_sdk_client` branch is
stdlib, `algotrader.errors`, `algotrader.core.*`, or one of the
`algotrader.orchestration`/`algotrader.portfolio`/`algotrader.risk`/
`algotrader.screener`/`algotrader.signals` modules listed above — none of
which import `algotrader.config`, `algotrader.execution.alpaca_sdk_client`,
`algotrader.execution.alpaca_client`,
`algotrader.execution.live_capital_interlock`, `alpaca`, or
`alpaca_trade_api` anywhere (verified by reading each file's import
block directly in this checkout). **The `alpaca_sdk_client` import is the
only impure edge in the entire transitive closure**, and the only thing
`tomorrow_crypto_trader_demo.py` needs from it is one pure, symbol-string
helper: `crypto_market_data_symbol_normalization`
(`alpaca_sdk_client.py:300-378`) plus its dataclass
`CryptoMarketDataSymbolNormalization` (`alpaca_sdk_client.py:32-38`) and
two module constants,
`SUPPORTED_CRYPTO_MARKET_DATA_QUOTE_SUFFIXES` and
`_CRYPTO_MARKET_DATA_SYMBOL_PART_PATTERN` (`alpaca_sdk_client.py:296-297`).
That function's body (`alpaca_sdk_client.py:300-378`) does string
parsing only — no SDK object, no network call, no config type — it is
misplaced, not inherently impure. This is a code-location defect, not a
behavioral one, and it is the entire fix.

This also matters at runtime, not just at import time: the one scenario
in `crypto_supervised_readiness_trial.py`
(`_run_scenario_matrix`'s `broker_unobserved_or_unavailable_block`
probe, `crypto_supervised_readiness_trial.py:538-551`) that calls
`run_tomorrow_crypto_trader_demo(..., broker_observed_readiness=True,
allow_alpaca_paper_read=(allow_alpaca_paper_read and
broker_observed_readiness))` reaches
`_broker_observed_readiness_preview` (`tomorrow_crypto_trader_demo.py:3185`),
which returns immediately at its `if not broker_read_authorized: return
...` guard (`tomorrow_crypto_trader_demo.py:3343-3349`) whenever
`allow_alpaca_paper_read` is `False` — before ever reaching the deferred,
function-local `from algotrader.config import AlpacaPaperConfig` /
`from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient`
import at `tomorrow_crypto_trader_demo.py:3560-3561`. Under this
contract's fixed `broker_observed_readiness=False,
allow_alpaca_paper_read=False` call (see "New Module" below),
`allow_alpaca_paper_read and broker_observed_readiness` is always
`False`, so that deferred import never executes even at runtime — it is
provably dead code on this path, not merely usually-untaken.

## Design: Three-Part Change Set (Not Executed By This Contract)

The next implementation milestone (not this one) must make exactly these
three changes, in this order, each independently testable:

### Part 1 — Extract the pure normalization helper

Move, verbatim (no behavior change), out of
`src/algotrader/execution/alpaca_sdk_client.py` into a new pure leaf
module `src/algotrader/execution/crypto_market_data_symbol_normalization.py`:

- `CryptoMarketDataSymbolNormalization` (dataclass, `alpaca_sdk_client.py:32-38`)
- `SUPPORTED_CRYPTO_MARKET_DATA_QUOTE_SUFFIXES` (`alpaca_sdk_client.py:296`)
- `_CRYPTO_MARKET_DATA_SYMBOL_PART_PATTERN` (`alpaca_sdk_client.py:297`)
- `crypto_market_data_symbol_normalization` (`alpaca_sdk_client.py:300-378`)

The new module's only imports are `from __future__ import annotations`,
`dataclasses.dataclass`, and `re` — all stdlib. `alpaca_sdk_client.py`
then does
`from .crypto_market_data_symbol_normalization import (CryptoMarketDataSymbolNormalization,
SUPPORTED_CRYPTO_MARKET_DATA_QUOTE_SUFFIXES, crypto_market_data_symbol_normalization)`
and keeps re-exporting all three names unchanged, because
`tests/unit/test_alpaca_sdk_client.py:26-33` imports them directly from
`algotrader.execution.alpaca_sdk_client` today and must keep passing
unmodified. This part alone is a mechanical, zero-behavior-change move;
`test_alpaca_sdk_client.py`'s existing normalization tests
(`test_crypto_market_data_symbol_normalization_accepts_usd_pairs`,
`test_crypto_market_data_symbol_normalization_rejects_unsupported_symbols`)
are the regression proof and must pass byte-for-byte unchanged.

### Part 2 — Repoint `tomorrow_crypto_trader_demo.py`'s one import

Change `tomorrow_crypto_trader_demo.py:26-28` from importing
`crypto_market_data_symbol_normalization` out of
`algotrader.execution.alpaca_sdk_client` to importing it out of the new
`algotrader.execution.crypto_market_data_symbol_normalization` module.
No other line in `tomorrow_crypto_trader_demo.py` changes. After this
part, `tomorrow_crypto_trader_demo.py`'s full module-level import graph
is exactly the closure proved pure in "Root-Cause Import-Purity
Analysis" above, with the offending edge removed — it no longer imports
`alpaca_sdk_client`, `alpaca_client`, `live_capital_interlock`,
`AlpacaPaperConfig`, or `require_paper_profile` at module level anywhere.
As a direct consequence, `crypto_supervised_readiness_trial.py` (whose
only non-stdlib import is `tomorrow_crypto_trader_demo`) is also
import-pure at module level after this part, with no change to
`crypto_supervised_readiness_trial.py` itself required.

### Part 3 — New narrowly-scoped command module

Add `src/algotrader/execution/crypto_readiness_replay.py`, a thin,
narrowly-scoped wrapper — not a reimplementation — over
`run_crypto_supervised_readiness_trial`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from algotrader.execution.crypto_supervised_readiness_trial import (
    DEFAULT_CYCLE_COUNT,
    DEFAULT_DECISION_START,
    DEFAULT_OUTPUT_ROOT,
    run_crypto_supervised_readiness_trial,
)

COMMAND_NAME = "crypto-readiness-replay"
MILESTONE_NAME = "V5.4x Import-Pure Crypto Readiness Replay"


def run_crypto_readiness_replay(
    *,
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
    decision_start = DEFAULT_DECISION_START,
    cycle_count: int = DEFAULT_CYCLE_COUNT,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Import-pure default-path replay. Broker observation and receipt
    validation are structurally excluded, not merely defaulted off."""
    return run_crypto_supervised_readiness_trial(
        output_root=output_root,
        decision_start=decision_start,
        cycle_count=cycle_count,
        broker_observed_readiness=False,
        allow_alpaca_paper_read=False,
        write_artifacts=write_artifacts,
        receipt_root=None,
    )
```

with a `main(argv)` entry point registered in `cli.py` as a new
subparser (see "Exact CLI Argv" below). This module's only production
import is `crypto_supervised_readiness_trial`, which after Part 2 is
import-pure; `crypto_readiness_replay.py` itself never imports
`alpaca_sdk_client`, `alpaca_client`, `live_capital_interlock`,
`algotrader.config`, `alpaca`, or `alpaca_trade_api`, directly or
transitively.

**Why a new module instead of allowlisting `crypto-readiness-verify`
directly once Parts 1-2 land:** `crypto-readiness-verify`
(`cli.py:4191-4196`, handler `_run_crypto_readiness_verify` at
`cli.py:13923`) calls `run_crypto_supervised_readiness_trial` with
`write_artifacts=True` only — it does not pass
`broker_observed_readiness` or `allow_alpaca_paper_read` today, so it
also defaults to `False`/`False`. But its argparse surface
(`cli.py:4191-4196`) and handler are a general-purpose "operator runs
this manually" entry point; nothing structurally prevents a future
change from adding a `--broker-observed-readiness` flag to that parser,
since the underlying function already accepts the parameter. If that
happened, the *allowlist's* safety would then depend on
`crypto-readiness-verify`'s argparse defaults never changing — a
runtime-behavior property, exactly the class of property the executor's
import-purity bar exists to avoid depending on. `crypto_readiness_replay.py`
instead hardcodes `broker_observed_readiness=False,
allow_alpaca_paper_read=False, receipt_root=None` as positional keyword
literals with **no corresponding CLI flag at all** (see next section) —
the dangerous parameters are structurally unreachable from this
command's argv, not merely defaulted. This is a stronger, allowlist-
grade invariant than defaulted-but-present flags, at the cost of one
small new file.

## Exact CLI Argv

New subparser in `cli.py`, modeled directly on the existing
`etf-sma-offline-daily-cycle-rerun-m446` subparser
(`cli.py:2221-2274`) — the one command already on
`AUTONOMY_EXECUTOR_ALLOWLIST` — and on `crypto-readiness-verify`
(`cli.py:4191-4196`) for the crypto-specific defaults:

```python
crypto_readiness_replay_parser = subparsers.add_parser(
    "crypto-readiness-replay",
    help="Import-pure default-path crypto readiness trial replay.",
)
crypto_readiness_replay_parser.add_argument(
    "--output-root", type=Path, default="runs/crypto_supervised_readiness_trial/latest",
)
crypto_readiness_replay_parser.add_argument(
    "--decision-start", default="2026-07-19T12:00:00+00:00",
)
crypto_readiness_replay_parser.add_argument(
    "--cycle-count", type=int, default=24,
)
crypto_readiness_replay_parser.add_argument(
    "--format", choices=("text", "json"), default="text",
)
```

No `--broker-observed-readiness`, `--allow-alpaca-paper-read`, or
`--receipt-root` flag exists on this parser — full stop, not merely
unset by default. This is the single structural difference from
`crypto-readiness-verify`'s parser and is the load-bearing safety
property of this command.

**The allowlist argv this command is designed to support later is the
single fixed token, with zero flags, exactly mirroring the m446
pattern:**

```python
"run_supervised_readiness_trial_to_seed_r1_evidence": (
    "crypto-readiness-replay",
),
```

The executor always invokes the bare subcommand name with no
arguments, relying entirely on the parser's own hardcoded defaults
above — never a caller- or lane-supplied value — exactly like
`AUTONOMY_EXECUTOR_ALLOWLIST["rerun_offline_daily_cycle_chain"] =
("etf-sma-offline-daily-cycle-rerun-m446",)`
(`autonomy_offline_executor.py:100-104`). `_execute`'s existing defence-
in-depth check, `AUTONOMY_EXECUTOR_ALLOWLIST[action.recommended_action]
!= action.argv` (`autonomy_offline_executor.py:297-298`), continues to
reject any other argv unchanged — this contract adds a dict entry, not a
change to that check.

## Output Path And Schema Compatibility

`run_crypto_readiness_replay` calls `run_crypto_supervised_readiness_trial`
with no schema-affecting parameter changed: same `output_root` default
(`runs/crypto_supervised_readiness_trial/latest`), same
`SCHEMA_VERSION = "v5_32_supervised_crypto_readiness_trial_v1"`, same
`_write_trial_artifacts` write path
(`crypto_supervised_readiness_trial.py:810-850`), writing the identical
five-file set at the identical relative paths under `output_root`:
`readiness_packet.json`, `operating_report.md`, `cycle_receipts.jsonl`,
`scenario_receipts.jsonl`, `manifest.json`. The
`crypto_supervised_readiness_trial` lane's `LaneSpec.artifact_relpath`
(`autonomy_supervisor.py:342`) and its `state_fields`/`as_of_fields`
(`autonomy_supervisor.py:344-345`) read `readiness_packet.json` exactly
as they do today; the lane reader requires **zero changes** because the
artifact this command writes is byte-for-byte the same shape
`run_crypto_supervised_readiness_trial` already produces — this command
changes *which caller reaches* that function under what argument
surface, not what the function produces. `validate_crypto_supervised_readiness_trial`
(`crypto_supervised_readiness_trial.py:275-308`) validates this
command's output with zero modification, since the output is
structurally identical to what it already validates.

## Deterministic Input/Time Semantics

Unchanged from `run_crypto_supervised_readiness_trial`, inherited
as-is because this command hardcodes the only branch that could
introduce nondeterminism away:

- `decision_start` defaults to the fixed
  `DEFAULT_DECISION_START = datetime(2026, 7, 19, 12, 0, tzinfo=UTC)`;
  no `datetime.now()`/`time.time()` call anywhere on the default
  execution path.
- `cycle_count` defaults to the fixed `DEFAULT_CYCLE_COUNT = 24`, bounded
  `[MINIMUM_CYCLE_COUNT=8, MAXIMUM_CYCLE_COUNT=24]`.
- `UNIVERSE = ("BTCUSD", "ETHUSD", "SOLUSD")` and `SCENARIO_PATTERN` are
  fixed tuples; all price/bar data comes from the existing deterministic
  offline fixture generator already used by
  `run_tomorrow_crypto_trader_demo`, unchanged by this contract.
- `receipt_root=None` is hardcoded (not a CLI flag), which means
  `_validate_offline_receipt`'s only wall-clock read
  (`crypto_supervised_readiness_trial.py:1211-1215`, the observation-
  freshness `age_hours` check) is **unreachable code on this command's
  path** — `is_fail_layout`/`validation` are never computed
  (`crypto_supervised_readiness_trial.py:93-96` short-circuits on
  `receipt_root is not None`).
- Two independent in-process replays (`replay_a`, `replay_b`,
  `crypto_supervised_readiness_trial.py:75-84`) from the same fixed
  `decision_start`/`cycle_count` must produce identical receipt chains
  (`deterministic_rerun["equivalent"]`); this determinism proof is
  unchanged and inherited verbatim.
- The one accepted source of run-to-run *metadata* variance already
  present in the existing artifact — `branch_and_commit.branch` via
  `_git_branch_name()` (`crypto_supervised_readiness_trial.py:974-985`,
  a read-only local `git branch --show-current` call) — is an existing,
  already-accepted property of the schema this contract inherits
  unchanged; it is not new, and it does not affect
  `trial_classification`, `receipt_chain_hash`, or any accepted-vs-
  blocked decision.

## Import-Purity Proof And Test

A new automated test, following the exact pattern already established
by `test_crypto_read_only_paper_observation_adapter_does_not_import_downstream_layers`
(`tests/unit/test_dependency_direction.py:838-855`) and
`test_paper_lab_revalidation_brief_has_no_network_or_broker_sdk_paths`
(`tests/unit/test_dependency_direction.py:1538`), must be added to
`tests/unit/test_dependency_direction.py`. Because `_dependency_violations`
checks only each named file's **direct** imports
(`test_dependency_direction.py`'s `_dependency_violations`/
`_import_references`), proving the full transitive closure requires
listing every module in it explicitly as a `DependencyRule.paths` entry
— mirroring how `ORCHESTRATION_BOUNDARY_MODULES` already checks many
modules against one shared forbidden-prefix list
(`test_dependency_direction.py:180-220`):

```python
CRYPTO_READINESS_REPLAY_IMPORT_CLOSURE = (
    "algotrader.execution.crypto_readiness_replay",
    "algotrader.execution.crypto_supervised_readiness_trial",
    "algotrader.execution.tomorrow_crypto_trader_demo",
    "algotrader.execution.crypto_market_data_symbol_normalization",
    "algotrader.execution.simulator",
    "algotrader.orchestration.execution_planning_flow",
    "algotrader.orchestration.execution_planning_policy",
    "algotrader.orchestration.risk_execution_flow",
    "algotrader.orchestration.screener_signal_flow",
    "algotrader.orchestration.signal_risk_flow",
    "algotrader.portfolio.state",
    "algotrader.risk.config",
    "algotrader.risk.context",
    "algotrader.risk.engine",
    "algotrader.risk.state",
    "algotrader.screener.momentum",
    "algotrader.signals.crypto_trend",
    "algotrader.signals.simple_rule",
    "algotrader.core.types",
    "algotrader.core.validation",
    "algotrader.core.time",
    "algotrader.errors",
)

CRYPTO_READINESS_REPLAY_FORBIDDEN_PREFIXES = (
    "algotrader.config",
    "algotrader.execution.alpaca_sdk_client",
    "algotrader.execution.alpaca_client",
    "algotrader.execution.alpaca_broker",
    "algotrader.execution.alpaca_adapter",
    "algotrader.execution.alpaca_mapper",
    "algotrader.execution.alpaca_translator",
    "algotrader.execution.live_capital_interlock",
    "algotrader.execution.crypto_read_only_paper_observation_adapter",
    "alpaca",
    "alpaca_trade_api",
    "requests",
    "httpx",
    "socket",
    "urllib",
)


def test_crypto_readiness_replay_import_closure_is_broker_credential_and_profile_free() -> None:
    violations: list[str] = []
    for module_name in CRYPTO_READINESS_REPLAY_IMPORT_CLOSURE:
        rule = DependencyRule(
            source=module_name,
            paths=(_module_path(module_name),),
            forbidden_prefixes=CRYPTO_READINESS_REPLAY_FORBIDDEN_PREFIXES,
        )
        violations.extend(_dependency_violations(rule))
    assert violations == []
```

`algotrader.screener` is a package (`src/algotrader/screener/__init__.py`
re-exporting from `.momentum`); use the file's own `_package_files("algotrader.screener")`
helper (already used at `test_dependency_direction.py:253`) for that one
entry's `paths=`, not `_module_path`, since `_module_path` assumes a
single `.py` file and would resolve to the non-existent
`src/algotrader/screener.py`. `algotrader.screener.momentum` itself is a
plain module and uses `_module_path` normally.

`CRYPTO_READINESS_REPLAY_IMPORT_CLOSURE` must be the *exhaustive* set of
modules reachable from `crypto_readiness_replay.py`'s module-level
imports, recursively — the implementer must re-derive it against the
actual post-Part-1/2 source (this contract's derivation above is the
starting point, not a substitute for re-checking at implementation
time, since Parts 1-2 change two files this closure depends on). If a
future edit adds a new module-level import anywhere in this closure that
is not itself walked and added to
`CRYPTO_READINESS_REPLAY_IMPORT_CLOSURE`, this test can only catch
prefix violations in modules it is told to check — it is not a
whole-program import-graph crawler. A second, complementary test should
therefore also assert group membership is complete:

```python
def test_crypto_readiness_replay_import_closure_has_no_untracked_first_party_imports() -> None:
    tracked = set(CRYPTO_READINESS_REPLAY_IMPORT_CLOSURE)
    discovered: set[str] = set(tracked)
    frontier = list(tracked)
    while frontier:
        module_name = frontier.pop()
        for import_reference in _import_references(_module_path(module_name)):
            if not import_reference.module.startswith("algotrader."):
                continue
            resolved = import_reference.module
            if resolved not in discovered:
                discovered.add(resolved)
                frontier.append(resolved)
    assert discovered == tracked, (
        "crypto_readiness_replay's real import closure has grown beyond "
        "CRYPTO_READINESS_REPLAY_IMPORT_CLOSURE; add the new module(s) to "
        "the tracked set and re-verify them against "
        "CRYPTO_READINESS_REPLAY_FORBIDDEN_PREFIXES before allowlisting."
    )
```

This second test is what actually proves the closure captured above is
complete, not just that each listed module individually passes — it
fails closed (an assertion error, not a silent pass) if the real graph
grows without the tracked set growing with it. The sketch above is
illustrative, not literal: `_module_path` cannot resolve a package
import (`algotrader.screener`, reached via `screener_signal_flow.py`'s
`from algotrader.screener import ...`) to a real file, since that
resolves to a package `__init__.py`, not `algotrader/screener.py`. The
implementer must special-case package-shaped import references the same
way `_package_files("algotrader.screener")` already does elsewhere in
this file (`test_dependency_direction.py:253`) — either by resolving a
package import to its `__init__.py` before recursing, or by walking
into the concrete submodule the code actually re-exports from
(`algotrader.screener.momentum`) and asserting the `__init__.py`
re-export itself imports nothing else. Either resolution is acceptable;
what is not acceptable is silently dropping package-shaped import
references from the walk, since that would let a real transitive edge
go unchecked. Both tests must be
added and passing, alongside a runtime smoke check
(`import algotrader.execution.crypto_readiness_replay; assert
"alpaca_sdk_client" not in sys.modules` in a subprocess with a clean
`sys.modules`, since a same-process import can be contaminated by test
order) before this command is eligible for allowlisting.

## Dependency Direction

`test_dependency_direction.py`'s existing `EXECUTION_BOUNDARY_FORBIDDEN_PREFIXES`
(`test_dependency_direction.py:33-46`) already lists
`algotrader.execution.alpaca_sdk_client` as a forbidden prefix for
orchestration-boundary modules — that rule is untouched by this
contract. The new `crypto_readiness_replay.py` module sits in
`algotrader.execution` alongside `crypto_supervised_readiness_trial.py`
and `etf_sma_offline_daily_cycle_rerun_m446.py`; it depends downward
only (into `crypto_supervised_readiness_trial`, which depends downward
into `tomorrow_crypto_trader_demo`, which depends downward into
`orchestration`/`risk`/`portfolio`/`signals`/`screener`/`core`) — no new
upward or lateral edge is introduced anywhere in `algotrader.execution`.
`alpaca_sdk_client.py` keeps depending on the new
`crypto_market_data_symbol_normalization.py` leaf module (a strictly
downward edge, since the new module has no dependencies at all), so
Part 1 adds one new downward edge into `algotrader.execution` and
removes zero existing edges anyone else relies on (the re-export keeps
every external call site unchanged).

## Atomic Artifact Behavior

`_write_trial_artifacts` (`crypto_supervised_readiness_trial.py:810-850`),
which `crypto_readiness_replay.py` inherits unmodified, currently writes
`readiness_packet.json` via `_write_json`
(`crypto_supervised_readiness_trial.py:1045-1051`), a direct
`path.write_text(...)` — **not atomic**. This is an existing property of
`crypto_supervised_readiness_trial.py` today, not something this
contract's new module introduces, but because this command is the one
being positioned for **unattended, allowlisted, autonomous execution**
(unlike today's manual `crypto-readiness-verify` invocation), an
implementer adding this command should also harden
`_write_json`/`_write_jsonl` (or add an atomic-write wrapper
`crypto_readiness_replay.py` calls after delegating to
`run_crypto_supervised_readiness_trial(write_artifacts=False)` and
writing the artifacts itself) to the same atomic pattern
`cli.py:_write_receipt_atomically` already uses
(`cli.py`, `_write_receipt_atomically`): write to a `tempfile.mkstemp`
sibling in the same directory, `flush()` + `os.fsync(fd)`, `os.replace()`
into place, then best-effort `os.fsync` the parent directory file
descriptor. This guarantees a reader (the supervisor lane reader, or a
concurrent manual invocation) never observes a partially-written
`readiness_packet.json`, `manifest.json`, or any of the other four
artifact files, even if the process is killed mid-write. Whether this
hardening lands inside `_write_trial_artifacts` itself (benefiting
`crypto-readiness-verify` too) or only in a new
`crypto_readiness_replay`-local writer is an implementation choice left
open by this contract; either is acceptable as long as every file under
`output_root` is written via the temp-file-then-`os.replace` pattern,
never a direct in-place `write_text`/`open("w")`, before this command is
allowlisted for unattended execution.

## Fail-Closed Validation

Unchanged, inherited from `run_crypto_supervised_readiness_trial`: a
malformed input CSV row raises inside `_maximum_csv_timestamp`
(`crypto_supervised_readiness_trial.py:949-955`), an out-of-range
`cycle_count` raises `ValueError` before any replay starts
(`crypto_supervised_readiness_trial.py:65-69`), and every safety-gate
scenario in the matrix (duplicate intent, open order, unexpected
position, stale/mismatched state) is required to resolve to a
`blocked_*` decision with `acceptance_passed is True` for the trial to
reach `trial_classification == "accepted"`
(`crypto_supervised_readiness_trial.py:147-178`) — an exception or an
unexpected non-blocked decision both fail the trial closed rather than
silently passing. `crypto_readiness_replay.py`'s CLI `main()` must
propagate the same exit-code convention as `crypto_supervised_readiness_trial.main()`
(`crypto_supervised_readiness_trial.py:1343-1378`): return `0` only when
`trial_classification == "accepted"`, `2` otherwise, and let any raised
`ValueError` propagate as a non-zero process exit rather than being
caught and reported as a soft failure — the executor's `_execute`
(`autonomy_offline_executor.py:293-310`) already treats any non-zero
`exit_code` as `succeeded: False` without needing this command to do
its own success/failure translation.

## Safety Invariants Preserved

Every property below is unchanged by this contract and by the design it
specifies — none is weakened, relaxed, or made conditional:

- **Fixed argv allowlisting**: the eventual allowlist entry is a single
  bare-token tuple, `("crypto-readiness-replay",)`, with the same
  `_execute` defence-in-depth equality check
  (`autonomy_offline_executor.py:295-298`) unchanged.
- **Executor preflight**: `execution_preflight`
  (`autonomy_offline_executor.py:112-131`) still refuses to execute
  anything, including this command, whenever `APP_PROFILE` is
  `paper`/`live` or any credential/network-test variable is loaded —
  unmodified by this contract.
- **Sanitized child environment**: `_run_subprocess`'s
  `_STRIPPED_CHILD_ENV_KEYS` stripping
  (`autonomy_offline_executor.py:313-325`) applies to this command
  exactly as it does to the m446 rerun today — unmodified.
- **Zero network/broker/credential/profile access**: proved above both
  at import time (Root-Cause Import-Purity Analysis) and at runtime
  (the `broker_read_authorized` early-return trace) for this command's
  fixed, flag-free invocation.
- **No paper mutation**: `run_crypto_supervised_readiness_trial`'s
  `safety.paper_submit_performed`/`broker_mutation_performed` are `False`
  by construction on every path (`crypto_supervised_readiness_trial.py:236-246`),
  unchanged.
- **`live_authorized=false`**: emitted unconditionally in both the
  trial packet's `safety` block and its `manifest.json`
  (`crypto_supervised_readiness_trial.py:240,847`), unchanged.

This contract adds one new command and, as prerequisite refactors, moves
one pure helper and repoints one import — it does not touch
`AUTONOMY_EXECUTOR_ALLOWLIST`, `AUTONOMY_ACTION_CLASSIFICATION`,
`AUTONOMY_SUPERVISOR_LANES`, `execution_preflight`, `_run_subprocess`,
or any existing test's assertions.

## Absent vs Stale: Shared Or Separate Tokens

**Decision: separate tokens, sharing the same eventual allowlist argv.**
Concretely: `run_supervised_readiness_trial_to_seed_r1_evidence` (the
`STATE_ABSENT` remedy) is the one reclassified to
`EXECUTION_AUTO_OFFLINE` with `command="crypto-readiness-replay"` in the
later wiring step; `rerun_supervised_readiness_trial` (the
`STATE_STALE` remedy, already a distinct dict key in
`LaneSpec.next_actions`, `autonomy_supervisor.py:353`) is left as-is for
now (see "Later Wiring" below for why it stays inert) but, if a future
change ever makes it reachable, should map to the *same* command rather
than being merged into one shared token today.

Justification, from truthful-artifact semantics rather than mechanical
convenience:

1. **The distinction already exists and is load-bearing in this exact
   lane.** `LaneSpec.next_actions` (`autonomy_supervisor.py:350-358`)
   already carries two separate keys —
   `STATE_STALE: "rerun_supervised_readiness_trial"` and
   `STATE_ABSENT: "run_supervised_readiness_trial_to_seed_r1_evidence"`
   — frozen in the registry today, before this contract touches
   anything. Collapsing them onto one token would be a *regression* in
   the lane's existing diagnostic resolution, not a simplification of
   something this contract introduces.
2. **"Never produced evidence" and "produced evidence that decayed" are
   different facts about the system**, even when the remedy command
   happens to be identical. An operator or an audit trail reading
   `recommended_action` needs to be able to tell "this lane has never
   been seeded" from "this lane was healthy and then its evidence aged
   out" — the same distinction the `spy_offline_daily_cycle` lane's own
   comment already draws explicitly (`autonomy_supervisor.py:331-336`:
   the m446 rerun "can never cure staleness" for that lane precisely
   *because* seed and rerun are different commands there). Sharing a
   token here would erase that signal for readers of the plan/ledger
   even in the one case where, today, the underlying argv is identical
   — the token is documentation of *why* the action is needed, not just
   *what* to run.
3. **This directly continues the truthfulness doctrine this branch's own
   recent history established.** V5.37a/V5.38a's dead-fallback defect,
   V5.42's tri-state `all_executions_succeeded` fix, and V5.44's
   "zero executions is not a success claim" correction
   (`autonomy_offline_executor.py:192-201`) are all instances of the
   same principle: collapsing two distinguishable system states onto one
   value (or one vacuous truth) reads as more certain than the system
   actually knows. Merging `absent` and `stale` into one token here
   would be a new instance of exactly that class of defect — a real,
   distinguishable state (never-seeded vs. decayed) reported as
   indistinguishable — for a savings of one dict entry.
4. **It costs nothing to keep them separate.** Two `AUTONOMY_ACTION_CLASSIFICATION`
   entries pointing at the same `command` string is not a materially
   more complex allowlist or executor; `AUTONOMY_EXECUTOR_ALLOWLIST`
   only needs a *token -> argv* mapping, and nothing prevents two tokens
   from mapping to the same argv (the allowlist is keyed by
   `recommended_action`, and `_partition_actions`
   (`autonomy_offline_executor.py:253-290`) already handles many tokens
   funneling into few allowlist entries — the m446 rerun is one entry
   already reached by exactly one token, but the mechanism does not
   assume a 1:1 token:reachability relationship). Keeping them separate
   costs one extra `ActionClass` entry and buys forward-compatibility:
   if the seed and rerun remedies ever diverge (for example, if a later
   change makes `crypto-readiness-replay` resumable/incremental for a
   `stale`-not-`absent` rerun, writing a smaller delta instead of two
   full 24-cycle replays), the tokens are already separate and no
   breaking rename is needed under time pressure.

## Later Registry/Classification/Allowlist Wiring (Not Done By This Contract)

This section specifies, but does not perform, the exact changes a
follow-on milestone must make to move from "command exists and is
import-pure" to "one safe action is genuinely reachable" — mirroring
the reachability chain the V5.45 audit traced
(`docs/design/v5_45_executor_reachability_boundary_audit.md`, "The
Reachability Chain"):

1. **`autonomy_next_plan.py` — `AUTONOMY_ACTION_CLASSIFICATION`**: change
   the `run_supervised_readiness_trial_to_seed_r1_evidence` entry
   (currently `_operator_gated(_GATE_NO_OFFLINE_COMMAND, ...)`,
   `autonomy_next_plan.py:382-386`) to:
   ```python
   "run_supervised_readiness_trial_to_seed_r1_evidence": ActionClass(
       execution_class=EXECUTION_AUTO_OFFLINE,
       offline_runnable=True,
       gate=_GATE_UNATTENDED_EXECUTION,
       gate_detail=(
           "fully-defaulted, import-pure offline command that reproduces "
           "the crypto supervised readiness trial's default-path evidence; "
           "only unattended execution authority remains."
       ),
       command="python -m algotrader.cli crypto-readiness-replay",
   )
   ```
   modeled directly on the existing `rerun_offline_daily_cycle_chain`
   entry (`autonomy_next_plan.py:270-289`). Leave
   `rerun_supervised_readiness_trial` (the `stale` token) as
   `_operator_gated(_GATE_NO_OFFLINE_COMMAND, ...)` unchanged, because
   `crypto_supervised_readiness_trial`'s `LaneSpec.max_age_hours=0`
   (`autonomy_supervisor.py:346`) means `_staleness`
   (`autonomy_supervisor.py:968-996`, `stale = lane.max_age_hours > 0
   and ...`) can never return `True` for this lane today — the `stale`
   branch is structurally unreachable, so reclassifying it now would be
   speculative, untestable wiring. If a future milestone gives this lane
   a nonzero `max_age_hours`, that milestone should reclassify
   `rerun_supervised_readiness_trial` to the same `EXECUTION_AUTO_OFFLINE`
   / `crypto-readiness-replay` command at that time, per the "Absent vs
   Stale" decision above.
2. **`autonomy_offline_executor.py` — `AUTONOMY_EXECUTOR_ALLOWLIST`**:
   add exactly one entry,
   `"run_supervised_readiness_trial_to_seed_r1_evidence": ("crypto-readiness-replay",)`,
   alongside the existing `rerun_offline_daily_cycle_chain` entry
   (`autonomy_offline_executor.py:100-104`) — the allowlist becomes a
   two-entry dict, not a redesigned one.
3. **`cli.py`**: add the `crypto-readiness-replay` subparser and
   dispatch arm exactly as specified in "Exact CLI Argv" above.
4. **Tests to update at that time** (not by this contract): re-derive
   `test_allowlisted_actions_are_unreachable_from_current_lane_registry`
   and `test_every_supervisor_action_is_classified` (both cited and
   re-derived, not just re-read, in the V5.45 audit) — the first
   assertion changes from "the allowlist is unreachable" to "exactly one
   token, `run_supervised_readiness_trial_to_seed_r1_evidence`, is
   reachable, and it is reachable only when the
   `crypto_supervised_readiness_trial` lane is `absent`"; the second
   continues to require full coverage of every token the registry can
   emit. `test_allowlist_is_the_verified_offline_command_only` must be
   extended to assert `crypto-readiness-replay` never appears in any
   `AUTONOMY_ACTION_CLASSIFICATION` entry whose
   `required_operator_inputs` is non-empty, mirroring the existing
   assertion for the seed command
   (`docs/design/v5_45_executor_reachability_boundary_audit.md`,
   "Candidate B").
5. This wiring must land as its **own** frozen, reviewed contract or
   commit sequence, separate from the Parts 1-3 source change — the
   import-purity refactor (Parts 1-3) and the reachability wiring
   (steps 1-3 above) are independently reviewable and should not be
   bundled into one commit, so that an import-purity regression and a
   reachability-scope change are never conflated in one diff.

## Tests And Acceptance Criteria

An implementer executing this contract must satisfy all of the
following before the import-purity refactor (Parts 1-3) is considered
complete (the later wiring in the previous section is separately gated
and has its own acceptance criteria, listed under item 4 above):

1. `tests/unit/test_alpaca_sdk_client.py` passes unmodified — Part 1 is
   a pure move with a compatibility re-export, proven by zero test edits
   required there.
2. `tests/unit/test_tomorrow_crypto_trader_demo.py` passes unmodified —
   Part 2 changes only which module a symbol is imported from, not any
   behavior.
3. `tests/unit/test_crypto_supervised_readiness_trial.py` passes
   unmodified — this module's own source is untouched by Parts 1-3.
4. New `tests/unit/test_crypto_readiness_replay.py` (new file) asserting,
   at minimum:
   - `run_crypto_readiness_replay()` with all defaults produces a
     `readiness_packet.json` at
     `runs/crypto_supervised_readiness_trial/latest/readiness_packet.json`
     (in a temp/isolated `output_root` for the test) whose
     `trial_classification`, `receipt_chain.final_receipt_hash`, and
     `safety` block are identical to calling
     `run_crypto_supervised_readiness_trial(broker_observed_readiness=False,
     allow_alpaca_paper_read=False, receipt_root=None, ...)` directly
     with the same `output_root`/`decision_start`/`cycle_count` —
     proving the wrapper is behavior-preserving, not just import-pure.
   - `validate_crypto_supervised_readiness_trial(output_root)` (imported
     from `crypto_supervised_readiness_trial`, unmodified) returns
     `validation_status == "passed"` against this command's own output.
   - The CLI `main()` returns `0` on an accepted trial and non-zero
     otherwise, matching
     `crypto_supervised_readiness_trial.main()`'s convention.
   - The new module's `argparse` parser has no `--broker-observed-
     readiness`, `--allow-alpaca-paper-read`, or `--receipt-root`
     option (assert `parser.parse_args(["--broker-observed-readiness"])`
     raises `SystemExit` via `argparse`'s own unrecognized-argument
     handling).
5. `tests/unit/test_dependency_direction.py`'s two new tests specified
   under "Import-Purity Proof And Test" both pass:
   `test_crypto_readiness_replay_import_closure_is_broker_credential_and_profile_free`
   and
   `test_crypto_readiness_replay_import_closure_has_no_untracked_first_party_imports`.
6. A subprocess-isolated smoke test (new, in
   `test_crypto_readiness_replay.py` or `test_dependency_direction.py`):
   spawn `python -c "import algotrader.execution.crypto_readiness_replay,
   sys; assert 'algotrader.execution.alpaca_sdk_client' not in
   sys.modules"` with `PYTHONPATH=src` and assert exit code `0` — proving
   the import graph is pure in a fresh interpreter, not merely in a test
   process where `alpaca_sdk_client` may already be cached in
   `sys.modules` from an earlier, unrelated test import.
7. `python -m pytest tests/unit/test_dependency_direction.py` and the
   full existing crypto/tomorrow-demo/alpaca-sdk-client test files all
   pass together in one run (proving no cross-test `sys.modules`
   contamination masks a regression).
8. `.\scripts\verify_offline.ps1` passes with the new files present.
9. `git diff --check` is clean and no `src`/`tests` file is touched by
   *this* contract-writing commit (only true for this document; Parts
   1-3 and the later wiring are, by design, separate future commits that
   the acceptance criteria above apply to).

Acceptance for the later wiring step (allowlisting) additionally
requires the two re-derived reachability tests from item 4 of "Later
Registry/Classification/Allowlist Wiring" to pass, and a manual dry-run
(`apply=False`, the default) of `autonomy-apply-plan` to show exactly
one `eligible_actions` entry with `recommended_action ==
"run_supervised_readiness_trial_to_seed_r1_evidence"` and `argv ==
["crypto-readiness-replay"]` when the `crypto_supervised_readiness_trial`
lane's artifact is absent, and zero eligible actions from this lane
otherwise.

## Explicitly Out Of Scope For This Contract

- No `src` or `tests` file is modified by this document.
- No CLI subcommand is added.
- No entry is added to `AUTONOMY_ACTION_CLASSIFICATION` or
  `AUTONOMY_EXECUTOR_ALLOWLIST`.
- No `max_age_hours` change to the `crypto_supervised_readiness_trial`
  `LaneSpec` is proposed or authorized here.
- The atomic-write hardening described under "Atomic Artifact Behavior"
  is specified but not implemented here.
- Nothing in this contract grants the later wiring step's changes
  standing authorization; that wiring is its own explicitly-gated,
  separately-reviewed step per "Later Registry/Classification/Allowlist
  Wiring" item 5.

## Next Highest-Leverage Safe Action

**Implement Parts 1-3** (the extraction of
`crypto_market_data_symbol_normalization` into its own pure module, the
one-import repoint in `tomorrow_crypto_trader_demo.py`, and the new
`crypto_readiness_replay.py` module plus its `cli.py` subparser) as one
reviewable change, satisfying every acceptance criterion in "Tests And
Acceptance Criteria" items 1-9, **without** touching
`AUTONOMY_ACTION_CLASSIFICATION` or `AUTONOMY_EXECUTOR_ALLOWLIST` in the
same change. The later reachability wiring (this document's "Later
Registry/Classification/Allowlist Wiring" section) is deliberately a
separate, subsequent milestone so that the import-purity refactor can be
reviewed and accepted purely on its own (zero-behavior-change,
zero-new-reachability) merits before any new autonomous-execution
surface is opened.
