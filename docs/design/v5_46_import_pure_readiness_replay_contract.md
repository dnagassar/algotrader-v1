# V5.46 Import-Pure Crypto Readiness Replay Contract (Second Correction)

## Status And Scope

- Milestone: `V5.46 — contract-first design for an import-pure crypto
  readiness replay command`. Same milestone number as both prior
  passes, per the same convention V5.45's correction used.
- This is a **second correction pass**. The first version (`81124ad`)
  was rejected for an unsound import-purity proof (its test sketch
  checked only the one edge its own Parts 1-2 fixed, not the six edges
  the actual `ast.walk`-based mechanism would find). The first
  correction (`9dd7e14`) fixed the edge count but tried to close the
  remaining five edges with `importlib.import_module("...")` calls
  confined to their existing call sites, reasoning that a plain
  `ast.Call` is invisible to `ast.Import`/`ast.ImportFrom` matching.
  Independent review rejected that too, correctly: **dynamic loading
  that is merely invisible to one specific static-analysis mechanism is
  test evasion, not import purity** — the instruction was to remove or
  isolate the forbidden edges, not to hide them from the particular
  checker being used. This pass removes every `importlib`/`__import__`/
  dynamic-string-loading construct from the design entirely and
  replaces it with a real dependency-inversion boundary: pure
  replay-closure modules that structurally cannot reach broker/profile/
  credential/adapter code, not modules that merely evade one scanner
  while still containing the capability to reach it dynamically. See
  "What Changed In This Correction" for the itemized diff against
  `9dd7e14`.
- Still a **frozen, standalone design contract**, not implementation.
  Changes no `src` file (only the two `docs/` files this pass touches),
  adds no CLI subcommand, classifies no new action token, touches
  `AUTONOMY_EXECUTOR_ALLOWLIST` nowhere.
- Not strategy-profit, paper-order, broker-mutation, activation, or
  live-trading evidence. No credential was read, no network or broker
  call occurred, no file outside `docs/` was modified while writing this
  correction.
- Working branch: `claude/v5.46-import-pure-readiness-replay-contract`
  (kept per instruction; no rebase, reset, or branch switch performed).
  Verified before this pass's edits: branch, `HEAD`
  (`9dd7e1478ff8ee84b50d445c57bf1e11080cc46e`, the previous commit on
  this branch), `git status --porcelain`, staged/unstaged/untracked
  diffs all clean, and credential/profile presence booleans
  (`APP_PROFILE`, `ALGO_TRADER_ALLOW_NETWORK_TESTS`,
  `RUN_ALPACA_PAPER_INTEGRATION_TESTS`) all absent/false.

## Method

Static, offline inspection only. No code executed, no `runs/` artifact
touched, no network or broker call made. This pass re-read every call
site it proposes to change directly in this checkout (not from memory
of the prior passes), including `_read_open_orders`,
`_broker_observed_readiness_preview`'s client-resolution branch,
`_validate_offline_receipt`'s two schema branches, the test fixtures
that exercise them (`_FakeBrokerReadClient.get_orders`'s exact
signature), and the two PS1 scripts and one test assertion that pin
`tomorrow_crypto_trader_demo.py`'s exact module path — specifically to
avoid repeating the previous passes' mistake of designing against an
assumed rather than verified constraint set.

## Why The First Correction Was Still Wrong

`importlib.import_module("algotrader.execution.tomorrow_crypto_trader_demo_broker_client_adapter")`
inside a pure-closure file is a real, executable code path that reaches
the broker/config surface at runtime whenever that branch runs — it
differs from `from algotrader.execution.tomorrow_crypto_trader_demo_broker_client_adapter
import build_alpaca_read_client` only in which specific
`ast`-node-matching heuristic notices it. The instruction was "remove
or isolate all forbidden dependency edges from every module in the
replay closure" — an edge that still exists, still executes, and is
merely encoded so today's specific scanner regex/AST-matcher can't spot
it is not removed and is not isolated; it is hidden. A static test built
to detect the previous encoding would have passed for the wrong reason:
because the checker doesn't recognize the dependency, not because the
dependency doesn't exist. This pass replaces that with an actual
architectural boundary — pure modules that do not contain the
capability to reach the forbidden surface *by any mechanism*, static or
dynamic, and an explicit static test that checks for both forms
(imports **and** dynamic-loading calls **and** forbidden module-name
string literals), so the proof is sound regardless of which technique a
future edit might otherwise be tempted to use.

## The Six Edges (re-confirmed, unchanged from the first correction)

```
tomorrow_crypto_trader_demo.py:26    from algotrader.execution.alpaca_sdk_client import (...)         [module level]
tomorrow_crypto_trader_demo.py:3560  from algotrader.config import AlpacaPaperConfig                   [inside _build_alpaca_read_client]
tomorrow_crypto_trader_demo.py:3561  from algotrader.execution.alpaca_sdk_client import AlpacaSdkClient [inside _build_alpaca_read_client]
tomorrow_crypto_trader_demo.py:3940  from algotrader.execution.alpaca_client import AlpacaRecentOrderQuery  [inside _read_open_orders]
crypto_supervised_readiness_trial.py:1150  from algotrader.execution.crypto_read_only_paper_observation_adapter import get_source_provenance, PreflightCheckError  [inside _validate_offline_receipt, production-schema branch]
crypto_supervised_readiness_trial.py:1302  from algotrader.execution.crypto_read_only_paper_observation_adapter import get_source_provenance, PreflightCheckError  [inside _validate_offline_receipt, failure-schema branch]
```

## Verified Constraints (re-checked directly in this checkout, not assumed)

1. `tests/unit/test_tomorrow_crypto_trader_demo.py:test_scripts_expose_simbroker_and_validator_contracts`
   asserts the literal string `"algotrader.execution.tomorrow_crypto_trader_demo"`
   appears in `scripts/run_tomorrow_crypto_trader_demo.ps1`'s text (one
   assertion, checking the *run* script only, not the validator script),
   alongside `--broker-observed-readiness`/`--allow-alpaca-paper-read`
   fragment checks. Both `scripts/run_tomorrow_crypto_trader_demo.ps1:148`
   and `scripts/validate_tomorrow_crypto_trader_demo.ps1:39` invoke
   `python -m algotrader.execution.tomorrow_crypto_trader_demo` directly
   — confirmed by reading both files.
2. No test in `test_tomorrow_crypto_trader_demo.py` imports or calls
   `main()` in-process — its own top-of-file import list
   (`test_tomorrow_crypto_trader_demo.py:15-24`) imports only
   `run_tomorrow_crypto_trader_demo`, `validate_tomorrow_crypto_trader_demo`,
   `_broker_observed_readiness_preview`, and a handful of constants —
   never `main`. All CLI-level testing goes through the PS1 scripts as
   subprocesses. This means relocating `main()` requires updating the
   two PS1 scripts and the one PS1-content assertion, but **zero**
   in-process test call sites.
3. `_FakeBrokerReadClient.get_orders(self, query: object | None = None)`
   (the test double injected everywhere via `broker_observed_client=...`)
   takes one optional positional-or-keyword parameter and returns
   `self.open_orders` unconditionally, ignoring the argument's content
   entirely. No test asserts on the *type* or *shape* of the object
   passed to `get_orders`, only that `"get_orders"` appears in
   `self.calls`. This means `_read_open_orders`'s call signature can
   change from a positional `AlpacaRecentOrderQuery` instance to keyword
   arguments without affecting any existing assertion — confirmed by
   reading the fake's definition and every test that constructs it.
4. `receipt_root` on `run_crypto_supervised_readiness_trial` is a real,
   tested, production-wired parameter — `cli.py:14071` and
   `crypto_supervised_readiness_trial.py:1365` (this module's own
   `main()`) both pass it, and `tests/unit/test_crypto_read_only_paper_observation.py:1036`
   calls it directly. It cannot be dropped from any function
   `crypto-readiness-verify` or `crypto_supervised_readiness_trial.py`'s
   own `main()` still needs to call. It **can** be kept out of a new,
   separate pure-core function, since `crypto_readiness_replay.py` never
   needs to call it.

## Design: Four-Part Change Set, True Dependency Inversion (Not Executed By This Contract)

### Part 1 — Extract the pure normalization helper (unchanged from both prior passes)

Move `CryptoMarketDataSymbolNormalization`,
`SUPPORTED_CRYPTO_MARKET_DATA_QUOTE_SUFFIXES`,
`_CRYPTO_MARKET_DATA_SYMBOL_PART_PATTERN`, and
`crypto_market_data_symbol_normalization` out of `alpaca_sdk_client.py`
into a new pure leaf module
`src/algotrader/execution/crypto_market_data_symbol_normalization.py`
(stdlib-only imports). `alpaca_sdk_client.py` re-imports and re-exports
all three names so `tests/unit/test_alpaca_sdk_client.py:26-33` keeps
passing unmodified. Repoint `tomorrow_crypto_trader_demo.py:26-28` to
the new module, fixing the one module-level edge. Genuinely
behavior-identical: a code move plus one import repoint.

### Part 2a — `tomorrow_crypto_trader_demo.py`: remove the two remaining edges via real protocol-based dependency injection, no dynamic loading

**`_build_alpaca_read_client` is deleted outright**, not moved-and-
called-dynamically. Its one call site
(`tomorrow_crypto_trader_demo.py:3390-3392`,
`client = broker_client or (broker_client_factory() if
broker_client_factory is not None else _build_alpaca_read_client())`)
becomes:

```python
client = broker_client or (
    broker_client_factory() if broker_client_factory is not None else None
)
```

When `client is None`, the code falls through to the **already-existing**
`if client is None: return ... blocked_adapter_unavailable ...` branch
(`tomorrow_crypto_trader_demo.py:3393-3403`), which needs no new code at
all — this is the fail-closed behavior the reviewer requires for a
missing injection, and it already exists in this file today. No import
of `algotrader.config`/`alpaca_sdk_client` remains anywhere in this
file's source, by any mechanism.

**`_read_open_orders` is changed to a plain keyword-argument call,
never constructing `AlpacaRecentOrderQuery` itself:**

```python
def _read_open_orders(client: object, symbol: str) -> Sequence[object]:
    method = getattr(client, "get_orders")
    try:
        return method(status_filter="open", symbol_filter=symbol)
    except TypeError:
        return method()
```

This is a genuine protocol/duck-typing boundary, not an obfuscation:
`tomorrow_crypto_trader_demo.py` now depends only on "whatever object is
injected has a `get_orders` callable that accepts `status_filter`/
`symbol_filter` keywords, or falls back to a no-argument call" — it
never references `AlpacaRecentOrderQuery` or any Alpaca-specific type by
name, anywhere. `_FakeBrokerReadClient.get_orders(self, query=None)`
does not accept these keywords, so this raises `TypeError` and falls
back to `method()` — returning `self.open_orders` exactly as before
(confirmed by constraint 3 above); no existing test's assertion
changes. A real client, injected only by the facade (Part 2c), will
implement `get_orders(status_filter=None, symbol_filter=None)` and
translate internally to a genuine `AlpacaRecentOrderQuery` — that
translation lives entirely inside the facade-side object, never inside
this file.

**`main()`, its `argparse` parser, and the `if __name__ == "__main__":`
block are removed from `tomorrow_crypto_trader_demo.py` entirely** and
move to a new composition-root module (Part 2c). This file becomes a
library module only: `run_tomorrow_crypto_trader_demo`, its helpers, and
`validate_tomorrow_crypto_trader_demo` remain importable exactly as
before; there is no longer a way to `python -m
algotrader.execution.tomorrow_crypto_trader_demo` directly. This is a
**genuine, disclosed, narrow invocation-path change** — not backward
compatible in the one specific sense of "which exact module path you
invoke with `python -m`" — required because (a) `main()`'s CLI can never
carry a Python callable, so it cannot inject a factory the way
in-process callers already do; (b) the only way to keep the actual
capability (constructing a real client on operator request) requires an
import of the broker surface somewhere; and (c) that import cannot live
in this file without recreating exactly the edge this contract removes.
No other option was found that satisfies both "identical `python -m`
invocation path" and "zero broker-surface reference, static or dynamic,
anywhere in this file's source" simultaneously — they are mutually
exclusive given constraint 1 above, so this contract picks the latter
and discloses the former's loss explicitly, per the reviewer's own
stated fallback.

**Required, disclosed follow-on changes** (all specified exactly, none
executed by this contract):

- `scripts/run_tomorrow_crypto_trader_demo.ps1:148`: change
  `"-m", "algotrader.execution.tomorrow_crypto_trader_demo"` to
  `"-m", "algotrader.execution.tomorrow_crypto_trader_demo_cli"`.
- `scripts/validate_tomorrow_crypto_trader_demo.ps1:39`: same change
  (this script also invokes the CLI, for `--validate-only`; since
  `main()` moves as a whole, both scripts must point at the new
  module).
- `tests/unit/test_tomorrow_crypto_trader_demo.py:test_scripts_expose_simbroker_and_validator_contracts`:
  change the expected fragment from
  `"algotrader.execution.tomorrow_crypto_trader_demo"` to
  `"algotrader.execution.tomorrow_crypto_trader_demo_cli"`. This is the
  **only** test-assertion change Part 2a requires (confirmed by
  constraint 2 above — no test calls `main()` in-process, so nothing
  else references the module path as a Python import target).

### Part 2b — New broker-bound adapter module (outside the closure, freely impure)

New module: `src/algotrader/execution/tomorrow_crypto_trader_demo_broker_client_adapter.py`.
Imports `algotrader.config.AlpacaPaperConfig`,
`algotrader.execution.alpaca_sdk_client.AlpacaSdkClient`, and
`algotrader.execution.alpaca_client.AlpacaRecentOrderQuery` freely, at
module level — this module is never referenced, statically or
dynamically, by anything in the replay closure. Exposes one function:

```python
def build_alpaca_read_client() -> object:
    """Construct a real, protocol-shaped read client. The returned
    object's get_orders(status_filter=None, symbol_filter=None) accepts
    the plain keyword protocol tomorrow_crypto_trader_demo._read_open_orders
    uses, translating internally to AlpacaRecentOrderQuery — the pure
    core never needs to know that type exists."""
```

containing the exact construction logic currently in
`_build_alpaca_read_client` (`tomorrow_crypto_trader_demo.py:3559-3576`,
moved verbatim), returning a thin wrapper object (or the real
`AlpacaSdkClient` extended with a `get_orders(status_filter=,
symbol_filter=)` method) that builds
`AlpacaRecentOrderQuery(status_filter=status_filter,
symbol_filter=symbol_filter)` internally before delegating to the real
SDK client's own order-query method.

### Part 2c — New composition-root CLI module (outside the closure, the sole caller that wires broker access to the pure core)

New module: `src/algotrader/execution/tomorrow_crypto_trader_demo_cli.py`.
Contains the full `main(argv)` moved verbatim from
`tomorrow_crypto_trader_demo.py`'s current `main()`
(`tomorrow_crypto_trader_demo.py:~7900-7960`), with **identical**
argparse flags, defaults, and dispatch logic. Imports
`run_tomorrow_crypto_trader_demo`/`validate_tomorrow_crypto_trader_demo`
from the now-pure `tomorrow_crypto_trader_demo` module, and imports
`build_alpaca_read_client` from the new adapter module (Part 2b) at
module level — this module is explicitly and deliberately impure, named
so, and lives outside `CRYPTO_READINESS_REPLAY_IMPORT_CLOSURE`. When
`args.broker_observed_readiness and args.allow_alpaca_paper_read` are
both set, `main()` constructs
`broker_observed_client_factory=build_alpaca_read_client` and passes it
to `run_tomorrow_crypto_trader_demo(...)` — using the DI seam that
already exists in that function's public signature today
(`broker_observed_client_factory: Callable[[], object] | None = None`,
`tomorrow_crypto_trader_demo.py:690`) and, per constraint 3/Part 2a
above, is now the *only* route to a real client, exactly preserving
today's actual operator-facing behavior (a genuine broker read still
happens under the same two flags, in the same paper-credentialed
shell), just reached through the composition root's explicit wiring
instead of the pure core's own internal construction.

Trailer: `if __name__ == "__main__": raise SystemExit(main())` lives in
this new file, matching the pattern every other CLI-entry module in
this repository already uses.

### Part 3 — `crypto_supervised_readiness_trial.py`: pure-core/facade split via injected validator, full backward compatibility (no invocation-path change needed here)

Unlike Part 2, this file's split can preserve **100% of existing
behavior with zero test or script changes**, because nothing here is
constrained by a `python -m <exact module>` invocation path — only by
call-site imports, which this contract can freely redirect.

**New pure-core module**: `src/algotrader/execution/crypto_supervised_readiness_trial_core.py`.
Contains everything currently in `crypto_supervised_readiness_trial.py`
**except** `_validate_offline_receipt`: all of `_run_sequential_replay`,
`_cycle_receipt`, `_deterministic_rerun_evidence`, `_run_scenario_matrix`
and its sub-scenarios, `_broker_observed_result`, `_write_trial_artifacts`,
`_render_operating_report`, `_human_report_answers`, `_r4_blockers`, every
JSON/hash helper, `validate_crypto_supervised_readiness_trial` (already
adapter-free), all `DEFAULT_*` constants, and `run_crypto_supervised_readiness_trial`
itself — with one change to the latter's `receipt_root`-handling branch:
replace the internal call `_validate_offline_receipt(receipt_root)` with
an injected parameter:

```python
def run_crypto_supervised_readiness_trial(
    *,
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
    decision_start: datetime | str = DEFAULT_DECISION_START,
    cycle_count: int = DEFAULT_CYCLE_COUNT,
    broker_observed_readiness: bool = False,
    allow_alpaca_paper_read: bool = False,
    write_artifacts: bool = True,
    receipt_root: Path | str | None = None,
    receipt_validator: Callable[[Path | str], dict[str, Any]] | None = None,
) -> dict[str, object]:
    ...
    is_fail_layout = False
    if receipt_root is not None:
        if receipt_validator is None:
            # Fail closed: a receipt_root was given but no validator was
            # injected to check it. This is the required fail-closed
            # behavior for a missing broker/receipt-path dependency.
            validation = {
                "valid": False,
                "classification": "blocked_receipt_validator_not_provided",
                "broker_state_observed": False,
                "network_used": False,
                "broker_read_occurred": False,
            }
        else:
            validation = receipt_validator(receipt_root)
        ...  # unchanged from here
    else:
        broker_observed = _broker_observed_result(...)
    ...
```

This module now imports nothing beyond `tomorrow_crypto_trader_demo`
(after Part 2a-2c, pure) and stdlib — it is a real pure core, not merely
one that happens not to be called with a receipt_root.
`crypto_readiness_replay.py` (Part 4) imports directly from *this*
module and never supplies `receipt_root`, so `receipt_validator` is
never even relevant on its path.

**Existing file becomes the facade**:
`src/algotrader/execution/crypto_supervised_readiness_trial.py` shrinks
to: a normal, static, top-level `from algotrader.execution.crypto_read_only_paper_observation_adapter
import get_source_provenance, PreflightCheckError` (restored to a plain
import — no dynamic loading, since this file is deliberately outside
the closure and being openly impure here is correct, not a compromise);
`_validate_offline_receipt` unchanged from today; and:

```python
from algotrader.execution.crypto_supervised_readiness_trial_core import (
    DEFAULT_CYCLE_COUNT,
    DEFAULT_DECISION_START,
    DEFAULT_OUTPUT_ROOT,
    validate_crypto_supervised_readiness_trial,
    run_crypto_supervised_readiness_trial as _run_crypto_supervised_readiness_trial_core,
)


def run_crypto_supervised_readiness_trial(
    *, receipt_root: Path | str | None = None, **kwargs: object
) -> dict[str, object]:
    """Facade preserving the full existing public signature: supplies
    _validate_offline_receipt automatically when receipt_root is set,
    so every existing caller of this exact function/module keeps
    working unmodified."""
    validator = _validate_offline_receipt if receipt_root is not None else None
    return _run_crypto_supervised_readiness_trial_core(
        receipt_root=receipt_root, receipt_validator=validator, **kwargs
    )
```

`main()` (this file's own CLI, with its `--receipt-root` flag,
`crypto_supervised_readiness_trial.py:1343-1378`) is **not moved** —
it stays in this file and calls the facade's
`run_crypto_supervised_readiness_trial` exactly as it does today,
unmodified. `cli.py`'s `_run_crypto_readiness_verify`
(`from .execution.crypto_supervised_readiness_trial import
run_crypto_supervised_readiness_trial`) is **not changed** — it keeps
importing from the same module path and gets the facade, which behaves
identically to today's monolithic function for its own call (no
`receipt_root` passed, so the branch is irrelevant either way).
`tests/unit/test_crypto_supervised_readiness_trial.py` passes
**unmodified**: every existing call to `run_crypto_supervised_readiness_trial`
from this module path gets identical behavior, since the facade's
auto-injection makes the split invisible to any caller of the facade.

### Part 4 — New narrowly-scoped command module

```python
from __future__ import annotations

import argparse
from pathlib import Path

from algotrader.execution.crypto_supervised_readiness_trial_core import (
    DEFAULT_CYCLE_COUNT,
    DEFAULT_DECISION_START,
    DEFAULT_OUTPUT_ROOT,
    run_crypto_supervised_readiness_trial,
)

COMMAND_NAME = "crypto-readiness-replay"
MILESTONE_NAME = "V5.47 Import-Pure Crypto Readiness Replay"


def run_crypto_readiness_replay(
    *,
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
    decision_start = DEFAULT_DECISION_START,
    cycle_count: int = DEFAULT_CYCLE_COUNT,
    write_artifacts: bool = True,
) -> dict[str, object]:
    """Import-pure default-path replay. broker_observed_readiness,
    allow_alpaca_paper_read, and receipt_root/receipt_validator are
    structurally absent from this wrapper's own parameters — not merely
    defaulted off — because it imports the pure core directly, which
    never requires them to reach an accepted trial."""
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

Note `crypto_readiness_replay.py` imports from
`crypto_supervised_readiness_trial_core`, **not** from
`crypto_supervised_readiness_trial` (the facade) — this is the one
detail that actually keeps the closure pure; importing from the facade
module by mistake would silently reintroduce the adapter edge, since
the facade's own top-level import of it is deliberate and correct for
*that* module but must never be reached from this one.

**This is additive behavior, not zero-behavior-change** — a new,
directly runnable CLI command that did not exist before is real,
additive capability. What is unchanged is **autonomous reachability**:
no entry is added to `AUTONOMY_ACTION_CLASSIFICATION` or
`AUTONOMY_EXECUTOR_ALLOWLIST`. The accurate claim is "zero new
autonomous reachability," not "zero behavior change."

## Exact CLI Argv (unchanged)

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
`--receipt-root` flag exists on this parser, structurally. Eventual
allowlist argv (added only in the later, separate wiring step):

```python
"run_supervised_readiness_trial_to_seed_r1_evidence": (
    "crypto-readiness-replay",
),
```

mirroring `AUTONOMY_EXECUTOR_ALLOWLIST["rerun_offline_daily_cycle_chain"]
= ("etf-sma-offline-daily-cycle-rerun-m446",)`
(`autonomy_offline_executor.py:100-104`); `_execute`'s existing
defence-in-depth equality check is unchanged.

## Output Path And Schema Compatibility (unchanged)

Identical `output_root` default, `SCHEMA_VERSION`, and five-file
artifact set. `LaneSpec.artifact_relpath` requires zero changes.
`validate_crypto_supervised_readiness_trial` (now living in the pure
core, re-exported by the facade) validates this command's output with
zero modification.

## Deterministic Input/Time Semantics (unchanged)

Fixed `DEFAULT_DECISION_START`/`DEFAULT_CYCLE_COUNT` bounded `[8, 24]`,
fixed `UNIVERSE`/`SCENARIO_PATTERN`, deterministic offline fixture data,
no `datetime.now()`/`time.time()` on the default path.
`crypto_readiness_replay.py` never passes `receipt_root`, so the
receipt-validator branch — now a real, statically-absent-from-this-
closure code path rather than a merely-dynamically-hidden one — is not
just unreached but architecturally unreachable from this command.

## Import-Purity Proof And Tests

### Test 1 — Named closure is forbidden-prefix-free, including dynamic-loading and string-literal bans

The rejected `9dd7e14` design relied on `ast.Import`/`ast.ImportFrom`
matching alone, which a dynamic-loading call evades by construction.
This design does not need that loophole (Parts 2-3 remove the need for
it), but the static test must **also** positively rule it out, so
neither this design nor a future edit can reintroduce it unnoticed:

```python
CRYPTO_READINESS_REPLAY_MODULE_PATHS = (
    _module_path("algotrader.execution.crypto_readiness_replay"),
    _module_path("algotrader.execution.crypto_supervised_readiness_trial_core"),
    _module_path("algotrader.execution.tomorrow_crypto_trader_demo"),
    _module_path("algotrader.execution.crypto_market_data_symbol_normalization"),
    _module_path("algotrader.execution.simulator"),
    _module_path("algotrader.orchestration.execution_planning_flow"),
    _module_path("algotrader.orchestration.execution_planning_policy"),
    _module_path("algotrader.orchestration.risk_execution_flow"),
    _module_path("algotrader.orchestration.screener_signal_flow"),
    _module_path("algotrader.orchestration.signal_risk_flow"),
    _module_path("algotrader.portfolio.state"),
    _module_path("algotrader.risk.config"),
    _module_path("algotrader.risk.context"),
    _module_path("algotrader.risk.engine"),
    _module_path("algotrader.risk.state"),
    _module_path("algotrader.signals.crypto_trend"),
    _module_path("algotrader.signals.simple_rule"),
    _module_path("algotrader.core.types"),
    _module_path("algotrader.core.validation"),
    _module_path("algotrader.core.time"),
    _module_path("algotrader.errors"),
    *_package_files("algotrader.screener"),
)

CRYPTO_READINESS_REPLAY_FORBIDDEN_MODULE_SUBSTRINGS = (
    "algotrader.config",
    "algotrader.execution.alpaca_sdk_client",
    "algotrader.execution.alpaca_client",
    "algotrader.execution.alpaca_broker",
    "algotrader.execution.alpaca_adapter",
    "algotrader.execution.alpaca_mapper",
    "algotrader.execution.alpaca_translator",
    "algotrader.execution.live_capital_interlock",
    "algotrader.execution.crypto_read_only_paper_observation_adapter",
    "algotrader.execution.tomorrow_crypto_trader_demo_broker_client_adapter",
    "algotrader.execution.tomorrow_crypto_trader_demo_cli",
    "alpaca",
    "alpaca_trade_api",
    "requests",
    "httpx",
    "socket",
    "urllib",
)


def test_crypto_readiness_replay_import_closure_is_broker_credential_and_profile_free() -> None:
    rule = DependencyRule(
        source="crypto readiness replay import closure",
        paths=CRYPTO_READINESS_REPLAY_MODULE_PATHS,
        forbidden_prefixes=CRYPTO_READINESS_REPLAY_FORBIDDEN_MODULE_SUBSTRINGS,
    )
    assert _dependency_violations(rule) == []


def test_crypto_readiness_replay_import_closure_bans_dynamic_loading_and_forbidden_literals() -> None:
    """Independent of _dependency_violations: directly bans importlib,
    __import__, and any string literal containing a forbidden module
    name, anywhere in the closure's source. This is what actually rules
    out the technique the second-rejected design used."""
    banned_call_names = {"import_module", "__import__"}
    for path in CRYPTO_READINESS_REPLAY_MODULE_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                called_name = (
                    func.attr if isinstance(func, ast.Attribute)
                    else func.id if isinstance(func, ast.Name)
                    else None
                )
                assert called_name not in banned_call_names, (
                    f"{path}:{node.lineno}: dynamic module loading via "
                    f"{called_name!r} is banned in the replay closure — "
                    "use a statically-checkable import (which will then "
                    "be caught by the forbidden-prefix test) or, if the "
                    "target is genuinely broker/profile/credential-bound, "
                    "move the caller out of the closure entirely."
                )
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                lowered = node.value.lower()
                assert not any(
                    forbidden.lower() in lowered
                    for forbidden in CRYPTO_READINESS_REPLAY_FORBIDDEN_MODULE_SUBSTRINGS
                    if len(forbidden) > 6  # skip short/generic tokens like "alpaca" alone if too broad; tune to avoid false positives on unrelated text
                ), (
                    f"{path}:{node.lineno}: string literal {node.value!r} "
                    "names a forbidden module — even as inert text this "
                    "indicates a dynamic-loading or string-keyed lookup "
                    "path into forbidden territory and must be removed "
                    "from the replay closure."
                )
```

This test is deliberately broader than "ban `importlib.import_module`
specifically" — it also bans the `__import__` builtin and any
`ast.Attribute`/`ast.Name` call whose name matches, and it separately
bans forbidden module-name string literals regardless of what function
they are (or are not) passed to, closing the door on `getattr(importlib,
"im" + "port_module")(...)`-style evasions or a table-driven
service-locator keyed by a string constant. The implementer should tune
the string-literal substring list to avoid false positives against
unrelated text (for example, comments or docstrings quoting a forbidden
module name for documentation purposes are also source text an
`ast.Constant` check would flag if they happen to be string
expressions — the implementer should decide whether docstrings should
be scanned or excluded, and document that choice, since over-triggering
on legitimate documentation is a usability problem this contract does
not resolve in advance).

### Test 2 — Closure completeness (unchanged design from the first correction, package-aware)

```python
def test_crypto_readiness_replay_import_closure_has_no_untracked_first_party_imports() -> None:
    tracked_paths = set(CRYPTO_READINESS_REPLAY_MODULE_PATHS)
    tracked_modules = {_module_name(path) for path in tracked_paths}
    discovered_modules: set[str] = set(tracked_modules)
    frontier = list(tracked_paths)
    while frontier:
        path = frontier.pop()
        for import_reference in _import_references(path):
            module = import_reference.module
            if not module.startswith("algotrader.") or module in discovered_modules:
                continue
            discovered_modules.add(module)
            candidate_module_path = _module_path(module)
            candidate_package_dir = Path("src").joinpath(*module.split("."))
            if candidate_module_path.is_file():
                frontier.append(candidate_module_path)
            elif candidate_package_dir.is_dir():
                frontier.extend(_package_files(module))
            else:
                raise AssertionError(
                    f"import reference {module!r} (from {path}:"
                    f"{import_reference.line}) resolves to neither a "
                    "module file nor a package directory."
                )
    assert discovered_modules == tracked_modules, (
        "crypto_readiness_replay's real import closure has grown beyond "
        "CRYPTO_READINESS_REPLAY_MODULE_PATHS; add the new module(s) and "
        "re-verify them before allowlisting."
    )
```

### Test 3 — Fresh-process `sys.modules` smoke test (retained; now a genuine confirmation, not compensating for a hidden dynamic load)

Spawn a clean subprocess importing `algotrader.execution.crypto_readiness_replay`
and assert `algotrader.execution.alpaca_sdk_client`,
`algotrader.execution.alpaca_client`, `algotrader.config`,
`algotrader.execution.live_capital_interlock`,
`algotrader.execution.crypto_read_only_paper_observation_adapter`,
`algotrader.execution.tomorrow_crypto_trader_demo_broker_client_adapter`,
and `algotrader.execution.tomorrow_crypto_trader_demo_cli` are all
absent from `sys.modules`. After Parts 1-4, this should pass trivially
(nothing in the closure references any of these names by any
mechanism) — it is kept as a genuine, independent runtime check, not
because the static tests are expected to be insufficient this time, but
because a runtime proof of "nothing this deep in a call chain manages
to reach it anyway" is cheap insurance and was explicitly requested to
be retained regardless.

## Dependency Direction (updated module list)

`EXECUTION_BOUNDARY_FORBIDDEN_PREFIXES`
(`test_dependency_direction.py:33-46`) is untouched.
`crypto_readiness_replay.py` and `crypto_supervised_readiness_trial_core.py`
depend downward only. `tomorrow_crypto_trader_demo_broker_client_adapter.py`
and `tomorrow_crypto_trader_demo_cli.py` have no dependents inside the
replay closure — nothing in the closure references either, statically
or dynamically, by construction (not merely by omission from a tracked
list). `crypto_supervised_readiness_trial.py` (the facade) depends on
`crypto_supervised_readiness_trial_core.py` (downward, into the
closure) **and** on `crypto_read_only_paper_observation_adapter.py`
(downward, outside the closure) — this is fine and expected: the facade
is deliberately impure, and nothing in the closure imports the facade.

## Atomic Publication (unchanged from the first correction: bundle consistency, packet-last)

`readiness_packet.json` remains the single commit marker for the whole
five-file bundle. Order: (1) build and internally validate the full
in-memory packet; (2) write `operating_report.md`, `cycle_receipts.jsonl`,
`scenario_receipts.jsonl` via temp-file-then-`os.replace`; (3) write
`manifest.json` last among supporting files, referencing the
already-computed hashes of the files just written; (4) only then,
atomically publish `readiness_packet.json` as the final commit point.
Interrupting anywhere before step 4's `os.replace` leaves the prior
valid `readiness_packet.json` byte-for-byte unchanged. This is a
**mandatory tested prerequisite before any allowlist wiring** — the
required test simulates a kill between steps 3 and 4 and asserts the
prior packet is unchanged and still validates as `"passed"`.

## Fail-Closed Validation (extended: the new injected-validator path)

Unchanged from the rejected/corrected versions for cycle-count bounds
and scenario-matrix acceptance. Newly specified by Part 3: when
`receipt_root is not None` and `receipt_validator is None`, the pure
core's `run_crypto_supervised_readiness_trial` returns
`classification="blocked_receipt_validator_not_provided"` and a
`trial_classification` that is not `"accepted"` (via the existing
`is_fail_layout`/`accepted` logic, unmodified in shape) — a real,
new, deliberate fail-closed branch for the "someone called the pure
core directly with a `receipt_root` but no validator" case, which
should never happen via `crypto_readiness_replay.py` (which never
passes `receipt_root`) but must still fail closed rather than silently
skip validation if it ever did.

## Safety Invariants Preserved

- **Fixed argv allowlisting, executor preflight, sanitized child
  environment**: unchanged, as in both prior passes.
- **Zero network/broker/credential/profile access**: now proved by a
  real architectural boundary (Tests 1-2, which ban both static and
  dynamic reach) plus the runtime smoke test (Test 3), not by a
  technique that merely evaded one specific checker.
- **No paper mutation, `live_authorized=false`**: unchanged.
- **Missing broker/receipt dependency fails closed**: newly explicit —
  `tomorrow_crypto_trader_demo.py`'s existing `if client is None: ...
  blocked_adapter_unavailable` (already present, unmodified) and the
  new `receipt_validator is None` branch in
  `crypto_supervised_readiness_trial_core.py` (Part 3) both fail closed
  rather than silently proceeding.

## Absent vs Stale: Shared Or Separate Tokens (unchanged)

Separate tokens, sharing the eventual allowlist argv
(`("crypto-readiness-replay",)`). Full justification unchanged from the
prior two passes: the distinction already exists and is load-bearing in
`LaneSpec.next_actions`; collapsing it would repeat the
distinguishable-states-collapsed-to-one-value defect class
(V5.37a/V5.38a/V5.42a/V5.44); it costs nothing to keep separate; it
buys forward-compatibility if the remedies ever diverge.

## Later Registry/Classification/Allowlist Wiring (equal authority; reserved for review separation, not lacking authorization)

Unchanged framing from the first correction: `AGENTS.md` already grants
every collaborator standing, equal authority for this scoped source/
allowlist work. The later wiring
(`AUTONOMY_ACTION_CLASSIFICATION`'s
`run_supervised_readiness_trial_to_seed_r1_evidence` entry,
`AUTONOMY_EXECUTOR_ALLOWLIST`'s one new entry, the `cli.py` subparser,
and re-deriving `test_allowlisted_actions_are_unreachable_from_current_lane_registry`/
`test_every_supervisor_action_is_classified`) is reserved for its own
separate contract and commit sequence purely so an import-purity
refactor and a new-reachability change are never conflated in one
diff — a review-separation scoping choice, not an authorization gap.

## Tests And Acceptance Criteria

1. `tests/unit/test_alpaca_sdk_client.py` passes unmodified.
2. `tests/unit/test_tomorrow_crypto_trader_demo.py` passes **with one
   required, disclosed change**: the expected module-path fragment in
   `test_scripts_expose_simbroker_and_validator_contracts` changes from
   `"algotrader.execution.tomorrow_crypto_trader_demo"` to
   `"algotrader.execution.tomorrow_crypto_trader_demo_cli"`. Every other
   assertion in this file passes unmodified, since no other test
   references `main()` or the module path (constraint 2 above).
3. `scripts/run_tomorrow_crypto_trader_demo.ps1` and
   `scripts/validate_tomorrow_crypto_trader_demo.ps1` both updated to
   invoke `python -m algotrader.execution.tomorrow_crypto_trader_demo_cli`.
4. `tests/unit/test_crypto_supervised_readiness_trial.py` passes
   unmodified (Part 3's facade preserves exact existing behavior).
5. New `tests/unit/test_crypto_supervised_readiness_trial_core.py` (or
   folded into the existing file): direct tests of the pure core's
   `receipt_validator` injection, including the new
   `blocked_receipt_validator_not_provided` fail-closed path when
   `receipt_root` is set without a validator.
6. New `tests/unit/test_tomorrow_crypto_trader_demo_cli.py`: tests that
   the composition root wires `build_alpaca_read_client` through to
   `run_tomorrow_crypto_trader_demo` correctly when both broker flags
   are set (using a fake/mocked adapter, not real credentials), and
   that omitting either flag never constructs a client.
7. New `tests/unit/test_crypto_readiness_replay.py`: behavior-
   equivalence against direct core calls; parser has no broker/receipt-
   root flags.
8. `tests/unit/test_dependency_direction.py`'s three new tests (Test
   1's forbidden-prefix check, Test 1's dynamic-loading/string-literal
   ban, Test 2's closure completeness) all pass.
9. Test 3 (fresh-process `sys.modules` smoke test) passes.
10. `python -m pytest tests/unit/test_dependency_direction.py
    tests/unit/test_alpaca_sdk_client.py
    tests/unit/test_tomorrow_crypto_trader_demo.py
    tests/unit/test_tomorrow_crypto_trader_demo_cli.py
    tests/unit/test_crypto_supervised_readiness_trial.py
    tests/unit/test_crypto_supervised_readiness_trial_core.py
    tests/unit/test_crypto_readiness_replay.py` all pass together in
    one run.
11. The bundle-commit interruption test under "Atomic Publication"
    passes.
12. `.\scripts\verify_offline.ps1` passes with the new files present.
13. `git diff --check` clean; no `src`/`tests` file is touched by *this*
    contract-correction commit.

Acceptance for the later wiring step additionally requires re-derived
reachability tests and a manual dry-run showing exactly one eligible
action when the lane's artifact is absent.

## Explicitly Out Of Scope For This Contract

- No `src` file is modified by this document.
- No CLI subcommand, `AUTONOMY_ACTION_CLASSIFICATION` entry, or
  `AUTONOMY_EXECUTOR_ALLOWLIST` entry is added.
- No `max_age_hours` change to the `crypto_supervised_readiness_trial`
  `LaneSpec` is proposed.
- The bundle-commit atomic-write hardening is specified but not
  implemented.
- The later wiring step is reserved for a separate contract for review-
  separation reasons — not an authorization gap.
- The two PS1-script and one-test-assertion changes in Part 2a are
  specified but not performed here.

## What Changed In This Correction (Against Rejected Commit `9dd7e14`)

1. **Removed all `importlib.import_module`/dynamic-loading design.**
   The prior correction's core mechanism — confining forbidden imports
   behind `importlib.import_module("...")` calls at their existing call
   sites — is deleted entirely, on the grounds (verified, not just
   asserted) that it is invisible to one specific static-analysis
   mechanism while still being a real, executable dependency edge; that
   is evasion of the check, not satisfaction of the underlying
   requirement.
2. **Real dependency inversion, verified against actual constraints.**
   `tomorrow_crypto_trader_demo.py`: `_build_alpaca_read_client` is
   deleted (relying purely on the already-existing
   `broker_observed_client_factory` DI parameter and the already-
   existing fail-closed `client is None` branch); `_read_open_orders`
   switched to a protocol-based keyword call, verified against the
   exact fake client signature used throughout the test suite to
   confirm no test regresses; `main()` moved to a new, explicitly
   impure composition-root module
   (`tomorrow_crypto_trader_demo_cli.py`), since keeping it in the pure
   file is structurally incompatible with banning all broker-surface
   references (static or dynamic) from that file — verified this is a
   genuine, irreducible constraint clash, not an oversight, by directly
   checking `main()`'s CLI cannot carry a callable and that the PS1
   scripts/one test assertion pin this file's exact module path.
   `crypto_supervised_readiness_trial.py`: split into a pure core
   (`crypto_supervised_readiness_trial_core.py`, with `_validate_offline_receipt`
   replaced by an injected `receipt_validator` parameter that fails
   closed when absent) and a facade (the existing file, kept, now
   openly importing the adapter statically since it is correctly
   outside the closure) — verified this split achieves full backward
   compatibility with zero test changes, unlike the
   `tomorrow_crypto_trader_demo.py` case.
3. **New static test explicitly bans dynamic loading and forbidden
   string literals**, not just `ast.Import`/`ast.ImportFrom` nodes —
   closing the exact gap the rejected design exploited, and guarding
   against related future evasions (`__import__`, `getattr`-based
   indirection, string-keyed service locators).
4. Everything else — the package-aware closure walker, the packet-last
   bundle-commit atomic-publication protocol, the equal-authority/no-
   operator-gate framing for later wiring, the additive-not-zero-
   behavior-change framing for the new CLI command, and the exact
   `V5.47` milestone name — is preserved unchanged from the first
   correction, per instruction.

## Next Highest-Leverage Safe Action

**Implement Parts 1-4 as specified above** — the single feasible
implementation action this contract now supports, in this exact order:
(1) extract the pure normalization helper; (2) in
`tomorrow_crypto_trader_demo.py`, delete `_build_alpaca_read_client`
and its self-construct fallback, switch `_read_open_orders` to the
plain-keyword protocol call, and remove `main()`, moving it verbatim
into a new `tomorrow_crypto_trader_demo_cli.py` composition root that
imports the new `tomorrow_crypto_trader_demo_broker_client_adapter.py`
for real client construction — updating both PS1 scripts and the one
test assertion that reference the old module path; (3) split
`crypto_supervised_readiness_trial.py` into a pure core module (with
injected, fail-closed `receipt_validator`) and a thin, unmodified-
behavior facade; (4) add `crypto_readiness_replay.py` (importing from
the pure core, not the facade) and its `cli.py` subparser, plus every
test in "Tests And Acceptance Criteria" — all thirteen items,
**without** touching `AUTONOMY_ACTION_CLASSIFICATION` or
`AUTONOMY_EXECUTOR_ALLOWLIST`. This is source-code implementation work,
to be scoped, executed, and verified as its own milestone, separate
from the later reachability-wiring step this contract specifies but
reserves for a subsequent contract.
