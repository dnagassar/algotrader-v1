# V5.46 Import-Pure Crypto Readiness Replay Contract (Third Correction)

## Status And Scope

- Milestone: `V5.46 — contract-first design for an import-pure crypto
  readiness replay command`. The milestone number remains unchanged
  across correction passes, following the V5.45 convention.
- This is a **third correction pass**. The first version (`81124ad`)
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
  checker being used. The second correction (`6f1566d`) replaced that
  evasion with real dependency inversion, but its packet-last
  publication design was also rejected: it overwrote the supporting
  files and manifest before replacing `readiness_packet.json`, so a
  crash immediately before that final replace left the old packet
  paired with new files and therefore did not preserve a valid old
  bundle as claimed. This pass retains the dependency inversion,
  replaces in-place multi-file publication with immutable generations
  plus one atomic root commit marker, and tightens the facade and broker
  wrapper compatibility requirements. The dependency design removes
  every `importlib`/`__import__`/
  dynamic-string-loading construct from the design entirely and
  replaces it with a real dependency-inversion boundary: pure
  replay-closure modules with no static dependency or enumerated
  dynamic-loading mechanism capable of reaching broker/profile/
  credential/adapter code, rather than modules that merely evade one
  scanner while retaining an ordinary dynamic import. See
  "What Changed In This Third Correction" for the itemized diff against
  `6f1566d`.
- Still a **frozen, standalone design contract**, not implementation.
  Changes no `src` file (only the two `docs/` files this pass touches),
  adds no CLI subcommand, classifies no new action token, touches
  `AUTONOMY_EXECUTOR_ALLOWLIST` nowhere.
- Not strategy-profit, paper-order, broker-mutation, activation, or
  live-trading evidence. No credential was read, no network or broker
  call occurred, no file outside `docs/` was modified while writing this
  correction.
- Working branch: `claude/v5.46-import-pure-readiness-replay-contract`
  (kept per instruction; no rebase, reset, clean, stash, or branch
  switch performed). Verified before this pass's edits: branch, `HEAD`
  (`6f1566dbdfd50fba9d515fff148f3021d7bc0c9c`), remote feature ref at
  the same commit, and staged/unstaged/untracked state all clean.
  Independent credential/profile/network-test presence booleans
  (`APP_PROFILE`, `ALPACA_API_KEY`, `ALPACA_API_KEY_ID`,
  `ALPACA_API_SECRET_KEY`, `ALPACA_SECRET_KEY`, `APCA_API_KEY_ID`,
  `APCA_API_SECRET_KEY`, `ALGO_TRADER_ALLOW_NETWORK_TESTS`, and
  `RUN_ALPACA_PAPER_INTEGRATION_TESTS`) were all absent/false; values
  were never requested or printed.

## Method

Static, offline inspection only. No source or test code executed, no `runs/` artifact
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

Independent review also re-read the current writer and validator at
`crypto_supervised_readiness_trial.py:275-308` and `:810-850`. The
validator reads both the root packet and root manifest, then verifies
every manifest hash. Therefore the rejected `6f1566d` order cannot
satisfy its own interruption assertion: replacing the manifest and
supporting files before the packet necessarily invalidates the still-
old packet/bundle view.

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
architectural boundary — pure modules that contain neither static
forbidden imports nor the concrete dynamic-loading mechanisms and
module-root literals specified below. The static tests cover the known
evasion class without claiming that finite AST analysis proves the
absence of every conceivable runtime code-generation technique.

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
file's source through any of the static or dynamic-loading mechanisms
covered by the acceptance rules.

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
changes. A real client, injected only by the impure composition roots,
will
implement `get_orders(status_filter=None, symbol_filter=None)` and
translate internally to a genuine `AlpacaRecentOrderQuery` — that
translation lives entirely inside the facade-side object, never inside
this file.

**Ambient paper-environment reads also move outside the pure module.**
Today `_alpaca_paper_packet` and
`_broker_observed_readiness_preview` both use
`paper_environment or _paper_environment_from_os()`. That reads
`APP_PROFILE`, endpoint variables, and credential aliases even when
broker observation is not requested, and it treats an intentionally
empty `{}` injection as false and discards it. Part 2 therefore moves
`_paper_environment_from_os` to the impure adapter in Part 2b and
changes both pure-module resolvers to:

```python
env = (
    dict(OFFLINE_PAPER_ENVIRONMENT)
    if paper_environment is None
    else dict(paper_environment)
)
```

`OFFLINE_PAPER_ENVIRONMENT` is a read-only mapping whose known profile,
credential-presence, and endpoint fields are all empty/false. The
distinction between `None` and `{}` is mandatory: an explicit empty
mapping is a valid fail-closed injection and must never trigger ambient
fallback. The pure module contains no `os.environ`, `os.getenv`,
imported `environ`/`getenv`, or dynamic equivalent. Direct in-process
calls that omit `paper_environment` now get deterministic fail-closed
offline state; the impure CLI/facade composition roots inject the
ambient snapshot where existing operator-facing behavior requires it.
This narrow default-behavior change is intentional and safety-
increasing, not described as behavior-identical.

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
dynamically, by anything in the replay closure. Exposes the client
builder:

```python
def build_alpaca_read_client() -> object:
    """Construct a real, protocol-shaped read client. The returned
    object's get_orders(status_filter=None, symbol_filter=None) accepts
    the plain keyword protocol tomorrow_crypto_trader_demo._read_open_orders
    uses, translating internally to AlpacaRecentOrderQuery — the pure
    core never needs to know that type exists. The wrapper exposes only
    the complete read protocol described below."""
```

It also owns the moved ambient reader:

```python
def read_paper_environment_from_os() -> dict[str, object]:
    """Return profile/endpoint text and credential-presence booleans.
    Never return a credential value."""
```

This preserves the current `_paper_environment_from_os` semantics at
the impure boundary while keeping raw credential values out of the
returned mapping and out of logs/artifacts.

containing the exact construction logic currently in
`_build_alpaca_read_client` (`tomorrow_crypto_trader_demo.py:3559-3576`,
moved verbatim), returning a thin wrapper object that explicitly
delegates `get_account`, `get_positions`, and `list_assets`; builds
`AlpacaRecentOrderQuery(status_filter=status_filter,
symbol_filter=symbol_filter)` internally before delegating to the real
SDK client's own order-query method; and explicitly exposes every
read-only price alias probed by `LATEST_PRICE_READ_METHOD_GROUPS`:

```text
get_latest_quote          get_crypto_latest_quote
get_latest_crypto_quote   get_latest_trade
get_crypto_latest_trade   get_latest_crypto_trade
get_latest_bar            get_crypto_latest_bar
get_latest_crypto_bar
```

Each generic/alias method delegates to the corresponding existing
`AlpacaSdkClient` crypto read method. The wrapper must not use broad
`__getattr__` forwarding, because that would also expose submit or
other mutation methods. Tests with a fake underlying SDK client must
exercise all thirteen read names (the four gate methods, including
translated `get_orders`, plus all nine price aliases), prove arguments
and return values are preserved, and assert that submit/cancel/replace/
close/liquidate methods are absent. This complete protocol is mandatory:
after the four-method gate,
`_broker_observed_readiness_preview` calls
`_read_latest_price_evidence`, which probes all nine aliases; a
four-method-only wrapper would silently replace genuine broker price
evidence with fixture fallback.

### Part 2c — New composition-root CLI module (outside the closure)

New module: `src/algotrader/execution/tomorrow_crypto_trader_demo_cli.py`.
Contains the full `main(argv)` moved verbatim from
`tomorrow_crypto_trader_demo.py`'s current `main()`
(`tomorrow_crypto_trader_demo.py:~7900-7960`), with **identical**
argparse flags, defaults, and dispatch logic. Imports
`run_tomorrow_crypto_trader_demo`/`validate_tomorrow_crypto_trader_demo`
from the now-pure `tomorrow_crypto_trader_demo` module, and imports
`build_alpaca_read_client` and `read_paper_environment_from_os` from
the new adapter module (Part 2b) at module level — this module is
explicitly and deliberately impure, named so, and lives outside
`CRYPTO_READINESS_REPLAY_IMPORT_CLOSURE`. When
`args.broker_observed_readiness and args.allow_alpaca_paper_read` are
both set, `main()` constructs
`broker_observed_client_factory=build_alpaca_read_client` and passes it
to `run_tomorrow_crypto_trader_demo(...)` — using the DI seam that
already exists in that function's public signature today
(`broker_observed_client_factory: Callable[[], object] | None = None`,
`tomorrow_crypto_trader_demo.py:690`) and, per constraint 3/Part 2a
above, is an explicit route to a real client, exactly preserving
today's actual operator-facing behavior (a genuine broker read still
happens under the same two flags, in the same paper-credentialed
shell), just reached through the composition root's explicit wiring
instead of the pure core's own internal construction. The impure
supervised-trial facade in Part 3 is the other required composition
root because its existing broker-observed scenario exposes the same
two flags.

The composition root calls `read_paper_environment_from_os()` and
passes the resulting `paper_environment` only when broker-observed read
flags request that state or the selected mode is `AlpacaPaper`.
Default SimBroker and `--validate-only` execution pass
`OFFLINE_PAPER_ENVIRONMENT` and perform no ambient profile/credential
read. Credential values never leave the trusted adapter; the injected
snapshot contains credential-presence booleans only.

Trailer: `if __name__ == "__main__": raise SystemExit(main())` lives in
this new file, matching the pattern every other CLI-entry module in
this repository already uses.

### Part 3 — `crypto_supervised_readiness_trial.py`: pure-core/facade split via injected dependencies, exact callable compatibility

Unlike Part 2, this file's split is required to preserve the exact
existing callable signature and tested behavior with zero existing-test
or script changes, because nothing here is
constrained by a `python -m <exact module>` invocation path — only by
call-site imports, which this contract can freely redirect.

**New pure-core module**: `src/algotrader/execution/crypto_supervised_readiness_trial_core.py`.
Contains the pure trial logic currently in
`crypto_supervised_readiness_trial.py`, but not the impure facade's
`_validate_offline_receipt`, `main()`, argparse construction, or
`if __name__ == "__main__"` trailer: all of `_run_sequential_replay`,
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
    broker_observed_client_factory: Callable[[], object] | None = None,
    paper_environment: Mapping[str, object] | None = None,
) -> dict[str, object]:
    ...
    environment = (
        dict(OFFLINE_PAPER_ENVIRONMENT)
        if paper_environment is None
        else dict(paper_environment)
    )
    environment_preflight = _environment_preflight(environment)
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
    scenario_receipts = _run_scenario_matrix(
        ...,
        broker_observed_client_factory=broker_observed_client_factory,
        paper_environment=environment,
    )
    ...
```

This module now imports nothing beyond `tomorrow_crypto_trader_demo`
(after Part 2a-2c, pure) and stdlib — it is a real pure core, not merely
one that happens not to be called with a receipt_root.
`crypto_readiness_replay.py` (Part 4) imports directly from *this*
module and never supplies `receipt_root`, so `receipt_validator` is
never even relevant on its path. `_run_scenario_matrix` also accepts
the optional `broker_observed_client_factory` and passes it to
`run_tomorrow_crypto_trader_demo`'s existing
`broker_observed_client_factory` parameter for the broker-observed
scenario. If both broker flags are true but no factory was injected,
the existing `blocked_adapter_unavailable` path remains fail closed.
`crypto_readiness_replay.py` fixes both broker flags false and injects
no factory, so this seam does not add broker reachability to the replay
closure.

The core's `_environment_preflight` becomes a pure function of the
injected mapping; it never reads `os.environ`. The computed snapshot is
reused for all three `packet["safety"]` fields instead of calling the
preflight three times. `_run_sequential_replay`,
`_deterministic_rerun_evidence`, `_run_scenario_matrix`, and every
sub-scenario helper propagate the same `paper_environment` to **all
six** current `run_tomorrow_crypto_trader_demo` call sites. No helper is
allowed to substitute `None` or omit the argument. A source-level test
enumerates those call sites and a runtime raising-environment test
guards the behavior.

**Existing file becomes the facade**:
`src/algotrader/execution/crypto_supervised_readiness_trial.py` shrinks
to: normal, static, top-level imports of
`get_source_provenance`/`PreflightCheckError` from
`crypto_read_only_paper_observation_adapter` and
`build_alpaca_read_client`/`read_paper_environment_from_os` from
`tomorrow_crypto_trader_demo_broker_client_adapter` (no dynamic
loading, since this file is deliberately outside the closure and being
openly impure here is correct, not a compromise);
`_validate_offline_receipt` unchanged from today; and:

```python
from algotrader.execution.crypto_supervised_readiness_trial_core import (
    DEFAULT_CYCLE_COUNT,
    DEFAULT_DECISION_START,
    DEFAULT_OUTPUT_ROOT,
    MILESTONE_NAME,
    SCHEMA_VERSION,
    _json_safe,
    _mapping,
    validate_crypto_supervised_readiness_trial,
    run_crypto_supervised_readiness_trial as _run_crypto_supervised_readiness_trial_core,
)


def run_crypto_supervised_readiness_trial(
    *,
    output_root: Path | str = DEFAULT_OUTPUT_ROOT,
    decision_start: datetime | str = DEFAULT_DECISION_START,
    cycle_count: int = DEFAULT_CYCLE_COUNT,
    broker_observed_readiness: bool = False,
    allow_alpaca_paper_read: bool = False,
    write_artifacts: bool = True,
    receipt_root: Path | str | None = None,
) -> dict[str, object]:
    """Facade preserving the exact existing public signature."""
    validator = _validate_offline_receipt if receipt_root is not None else None
    broker_factory = (
        build_alpaca_read_client
        if broker_observed_readiness and allow_alpaca_paper_read
        else None
    )
    environment = read_paper_environment_from_os()
    return _run_crypto_supervised_readiness_trial_core(
        output_root=output_root,
        decision_start=decision_start,
        cycle_count=cycle_count,
        broker_observed_readiness=broker_observed_readiness,
        allow_alpaca_paper_read=allow_alpaca_paper_read,
        write_artifacts=write_artifacts,
        receipt_root=receipt_root,
        receipt_validator=validator,
        broker_observed_client_factory=broker_factory,
        paper_environment=environment,
    )
```

The facade explicitly re-exports every symbol used by existing tests
and CLI code, at minimum `SCHEMA_VERSION`, `MILESTONE_NAME`,
`DEFAULT_OUTPUT_ROOT`, `DEFAULT_DECISION_START`,
`DEFAULT_CYCLE_COUNT`, `run_crypto_supervised_readiness_trial`, and
`validate_crypto_supervised_readiness_trial`; implementation-time
`rg` must enumerate any additional existing imports and preserve them.
`_json_safe` and `_mapping` are also imported explicitly because the
facade retains today's `main()` unchanged and that function calls both;
leaving them only in the core without imports would make the retained
CLI fail at runtime.
Only the pure-core function gains the three dependency-injection
parameters (`receipt_validator`, `broker_observed_client_factory`, and
`paper_environment`). The facade must not replace its
public parameters with `**kwargs`, because doing so would change
signature introspection and error behavior despite passing ordinary
calls. This propagation is mandatory: the current
`_run_scenario_matrix` calls `run_tomorrow_crypto_trader_demo` with the
two broker flags and relies on the self-builder Part 2 deletes. Without
facade injection through the core, the existing broker-observed trial
path would regress to `blocked_adapter_unavailable`.

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
Apart from the separately disclosed generational-artifact path
assertion, existing calls in
`tests/unit/test_crypto_supervised_readiness_trial.py` keep identical
behavior because the facade auto-injects all impure dependencies.
The facade reads ambient profile/credential-presence state once per
call, preserving its current operator-facing behavior; the replay
never imports or calls this facade.

**Source-provenance binding is extended, never narrowed.**
`crypto_read_only_paper_observation_adapter.compute_source_bundle_digest`
currently binds the monolithic
`crypto_supervised_readiness_trial.py`. After the split, leaving only
that facade in `relative_paths` would omit executable code that now
determines trial, broker-preview, normalization, publication, and
validation behavior. The implementation must retain every existing
manifest entry and append at least:

```text
src/algotrader/execution/crypto_supervised_readiness_trial_core.py
src/algotrader/execution/tomorrow_crypto_trader_demo.py
src/algotrader/execution/tomorrow_crypto_trader_demo_broker_client_adapter.py
src/algotrader/execution/tomorrow_crypto_trader_demo_cli.py
src/algotrader/execution/crypto_market_data_symbol_normalization.py
src/algotrader/execution/crypto_readiness_replay.py
```

`tests/unit/test_v5_33_2_source_provenance.py` must assert these entries
are present and that changing any one changes
`adapter_source_bundle_sha256`. This is a security-preserving
consequence of relocating code, not optional test cleanup.

### Part 4 — New narrowly-scoped command module

```python
from __future__ import annotations

from pathlib import Path

from algotrader.execution.crypto_supervised_readiness_trial_core import (
    DEFAULT_CYCLE_COUNT,
    DEFAULT_DECISION_START,
    DEFAULT_OUTPUT_ROOT,
    OFFLINE_PAPER_ENVIRONMENT,
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
        paper_environment=OFFLINE_PAPER_ENVIRONMENT,
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

`build_parser()` owns that subparser. Central dispatch adds exactly:

```python
if command == "crypto-readiness-replay":
    return _run_crypto_readiness_replay(args)
```

and the handler is:

```python
def _run_crypto_readiness_replay(args: argparse.Namespace) -> int:
    from .execution.crypto_readiness_replay import run_crypto_readiness_replay
    from .execution.crypto_supervised_readiness_trial_core import _json_safe

    packet = run_crypto_readiness_replay(
        output_root=args.output_root,
        decision_start=args.decision_start,
        cycle_count=args.cycle_count,
        write_artifacts=True,
    )
    if args.format == "json":
        print(json.dumps(_json_safe(packet), sort_keys=True))
    else:
        print(f"v5_47_trial_classification={packet['trial_classification']}")
        print(
            "v5_47_current_readiness_rung="
            f"{packet['current_readiness_rung_code']}"
        )
        print(f"v5_47_cycle_count={packet['cycle_count']}")
        print(
            "v5_47_receipt_chain_hash="
            f"{packet['receipt_chain']['final_receipt_hash']}"
        )
        print("v5_47_paper_submit_performed=false")
        print("v5_47_broker_mutation_performed=false")
        print("v5_47_live_authorized=false")
    return 0 if packet["trial_classification"] == "accepted" else 2
```

The handler must not import the impure supervised-trial facade.
Accepted output returns
zero, a completed but non-accepted packet returns two, and validation/
argument exceptions remain nonzero through the CLI's existing error
boundary. Tests cover both formats, exact text keys, the dispatch
branch, output-root/decision-start/cycle-count forwarding, zero for an
accepted packet, and nonzero for a fail-closed packet. This is the exact
behavior meant by “directly runnable CLI command.”

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

## Output Path And Schema Compatibility (corrected and disclosed)

The `output_root` default, `SCHEMA_VERSION`, five logical artifact
names, and root commit-marker path `readiness_packet.json` remain
unchanged. `LaneSpec.artifact_relpath` therefore requires zero changes.
The four supporting artifacts are deliberately no longer overwritten
at fixed root paths. They live under
`generations/<bundle_id>/`, and the root packet's existing
`artifact_paths` mapping points to that immutable generation.

This is a real artifact-location behavior change, not “zero
modification”: consumers that hard-code `output_root/manifest.json`,
`operating_report.md`, `cycle_receipts.jsonl`, or
`scenario_receipts.jsonl` must instead follow `artifact_paths`.
`validate_crypto_supervised_readiness_trial` is updated accordingly and
must retain validation support for legacy fixed-root packets already
written under the same `SCHEMA_VERSION`. The implementation must use
`rg` to enumerate repository consumers and tests of the four old fixed
paths and update them to follow `artifact_paths`. The contract review
already found one such assertion:
`tests/unit/test_crypto_supervised_readiness_trial.py` currently reads
`output_root / "operating_report.md"`; it must instead read
`Path(packet["artifact_paths"]["operating_report"])`. No compatibility
mirror is written at the old supporting-file paths, because
independently overwriting such mirrors would reintroduce a second,
non-atomic view of the bundle.

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
    "importlib",
    "runpy",
    "pkgutil",
)


def test_crypto_readiness_replay_import_closure_is_broker_credential_and_profile_free() -> None:
    rule = DependencyRule(
        source="crypto readiness replay import closure",
        paths=CRYPTO_READINESS_REPLAY_MODULE_PATHS,
        forbidden_prefixes=CRYPTO_READINESS_REPLAY_FORBIDDEN_MODULE_SUBSTRINGS,
    )
    assert _dependency_violations(rule) == []


def test_crypto_readiness_replay_import_closure_bans_dynamic_loading_and_forbidden_literals() -> None:
    """Ban executable dynamic-import machinery and module-root literals."""
    banned_call_names = {"import_module", "__import__"}
    forbidden_literal_roots = tuple(
        item.lower()
        for item in CRYPTO_READINESS_REPLAY_FORBIDDEN_MODULE_SUBSTRINGS
    )
    for path in CRYPTO_READINESS_REPLAY_MODULE_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        docstring_nodes = _ast_docstring_constant_nodes(tree)
        os_aliases = _import_aliases_for_module(tree, "os")
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "os":
                assert not {
                    alias.name for alias in node.names
                }.intersection({"environ", "getenv"}), (
                    f"{path}:{node.lineno}: ambient environment access is banned"
                )
            if isinstance(node, ast.Name):
                assert node.id not in {
                    "importlib", "runpy", "pkgutil", "__import__"
                }, f"{path}:{node.lineno}: dynamic import machinery is banned"
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
                if called_name == "getattr" and len(node.args) >= 2:
                    attribute_name = _fold_static_string(node.args[1])
                    assert attribute_name not in banned_call_names, (
                        f"{path}:{node.lineno}: constructed lookup of "
                        f"{attribute_name!r} is banned"
                    )
                    if (
                        isinstance(node.args[0], ast.Name)
                        and node.args[0].id in os_aliases
                    ):
                        assert attribute_name not in {"environ", "getenv"}, (
                            f"{path}:{node.lineno}: constructed ambient "
                            "environment access is banned"
                        )
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id in os_aliases
            ):
                assert node.attr not in {"environ", "getenv"}, (
                    f"{path}:{node.lineno}: ambient environment access is banned"
                )
            folded = _fold_static_string(node)
            if folded is not None and id(node) not in docstring_nodes:
                normalized = folded.strip().lower()
                assert not any(
                    normalized == root or normalized.startswith(root + ".")
                    for root in forbidden_literal_roots
                ), f"{path}:{node.lineno}: forbidden module literal {folded!r}"
```

`_ast_docstring_constant_nodes` deterministically identifies only the
leading string-expression docstring of each module, class, function,
and async function; comments are absent from the AST. `_fold_static_string`
recursively folds `ast.Constant(str)`, `ast.BinOp(Add)` whose operands
both fold, and all-constant `ast.JoinedStr` nodes. It returns `None` for
anything runtime-dependent. There is no length heuristic: generic
roots including exact `"alpaca"` and `"socket"` are checked, while
unrelated keys such as `"allow_alpaca_paper_read"` do not equal a root
or begin with `<root>.`. Static imports of `importlib`, `runpy`, and
`pkgutil` are independently rejected by the forbidden-prefix test;
name references, direct dynamic-import calls, and constructed
`getattr(..., "im" + "port_module")` lookups are rejected here.

Required negative tests feed the checker synthetic source for direct
`importlib.import_module`, aliased/static `importlib`, `__import__`,
`getattr(importlib, "im" + "port_module")("alpaca.data.historical")`,
and a table value `"socket.socket"` and prove each is rejected. They
also cover `os.environ`, aliased `os.getenv`,
`from os import environ`, and `getattr(os, "en" + "viron")`.
Required positive tests prove docstrings may document these names and
that `"allow_alpaca_paper_read"` is not a false positive. This is a
concrete guard against the known evasion class; it does not make an
unbounded claim that static analysis can prove the absence of every
conceivable runtime code-generation technique.

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

### Test 4 — Actual replay performs zero ambient profile/credential reads

Run the real `run_crypto_readiness_replay` (not a mocked core result)
against a temporary output root while `os.environ` is replaced by a
delegating guard mapping that raises on `get`, indexing, membership, or
iteration of any of:

```text
APP_PROFILE
ALPACA_API_KEY
ALPACA_API_SECRET_KEY
ALPACA_SECRET_KEY
APCA_API_KEY_ID
APCA_API_SECRET_KEY
ALPACA_BASE_URL
ALPACA_PAPER_BASE_URL
APCA_API_BASE_URL
```

Unrelated environment keys remain delegated so subprocess/Git behavior
is not artificially disabled. The replay must complete with an
accepted packet, its safety snapshot must contain paper/live/profile/
credential booleans all false, and rendering that actual packet through
`_json_safe` plus `json.dumps` must succeed. This test fails on the
current implementation at both `_environment_preflight()` and
`_paper_environment_from_os()`, so it is a regression-capable proof,
not a vacuous mock assertion.

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

## Atomic Publication (corrected: immutable generations plus one commit marker)

The rejected in-place “supporting files first, packet last” order is
not crash-consistent: before the packet replace, the old packet is
paired with a new manifest/supporting set and no longer validates.
Temp-file replacement makes each individual file atomic; it cannot make
five independently named files one atomic transaction.

The implementation uses one mutable commit point and immutable
generation data:

1. Build the semantic packet and the three content artifacts
   (`operating_report.md`, `cycle_receipts.jsonl`, and
   `scenario_receipts.jsonl`) as exact bytes in memory. Compute the
   SHA-256 and size of each. Derive `bundle_id` as the full lowercase
   SHA-256 of a canonical object containing both (a) the semantic packet
   with publication-only fields removed and (b) the three ordered
   content-artifact hashes and sizes. Thus the generation name itself
   commits to both semantics and supporting bytes.
2. Define the final layout as:

   ```
   <output_root>/readiness_packet.json
   <output_root>/generations/<bundle_id>/operating_report.md
   <output_root>/generations/<bundle_id>/cycle_receipts.jsonl
   <output_root>/generations/<bundle_id>/scenario_receipts.jsonl
   <output_root>/generations/<bundle_id>/manifest.json
   ```

   The generation manifest contains the three content-artifact
   hash/size entries, `bundle_id`, schema/record type, and the existing
   semantic safety fields. It does **not** contain a
   `readiness_packet` hash entry. Serialize it canonically and compute
   its hash/size.
3. Build the final root packet with `bundle_id`, the existing
   `artifact_paths` mapping, and a new `artifact_integrity` mapping that
   contains the hash/size of all four immutable generation files,
   including `manifest.json`. Serialize the exact final packet bytes.
   This is non-circular: the manifest never hashes the packet; the root
   packet hashes the manifest and all three content artifacts. The
   packet is therefore the trust root and cryptographically commits to
   every supporting byte, not merely to a pathname.
4. Write the four supporting files into a unique staging directory
   under `<output_root>/generations`, flush/close every file, validate
   all sizes and hashes there, then rename that directory to
   `<bundle_id>` on the same filesystem. A generation destination is
   create-once and never overwritten. If it already exists, validate
   byte-for-byte equivalence and reuse it; otherwise fail closed.
5. Re-read and validate the complete immutable generation against the
   root packet's `artifact_integrity`, recompute `bundle_id` from the
   packet semantics plus the three content hashes/sizes, and require the
   manifest's entries to match the packet exactly. Only then write the
   packet bytes to a temp
   file in `<output_root>`, flush/close it, and atomically
   `os.replace` it onto `<output_root>/readiness_packet.json`.
   Immediately validate the newly committed root view. An error before
   the replace leaves the prior root packet and every generation it
   references untouched; an interruption after the replace sees a
   complete new generation.

The validator first reads the root packet, resolves its
`artifact_paths`, and verifies that every referenced path is within
`output_root` (with legacy fixed-root support) and that a new-layout
packet's four supporting paths share exactly one
`generations/<bundle_id>` directory. It recomputes every
`artifact_integrity` hash/size, requires manifest equality with the
packet's committed content entries, and recomputes `bundle_id` from the
semantic packet plus the three content hashes/sizes before applying the
existing semantic safety checks. Path traversal, symlink escape, mixed
generations, a missing generation, an unexpected extra mutable pointer,
coordinated support-plus-manifest rewriting, or any hash mismatch fails
closed.

This is a **mandatory tested prerequisite before any allowlist
wiring**. The regression test first publishes generation A and saves
the exact root packet bytes. It injects a failure after generation B is
fully renamed and validated but immediately before the root
`os.replace`; it then asserts the root bytes are unchanged and the old
bundle still validates as `"passed"`. A subsequent un-faulted publish
must switch to B and validate as `"passed"`. The same test run against
the rejected in-place algorithm must fail, proving that the injection
point is capable of detecting the original defect rather than merely
exercising a harmless earlier interruption. A separate tamper test
changes a supporting file and recomputes the manifest; validation must
still fail because the unchanged root packet's `artifact_integrity` and
`bundle_id` no longer match.

The proven atomicity claim is deliberately limited to **process
interruption on a filesystem where same-volume directory rename and
file `os.replace` are atomic**. `flush`/close alone does not prove
power-loss or post-reboot durability. Power-loss durability is outside
this slice unless the implementation adds and tests platform-supported
file and directory synchronization; the implementation and reports
must not claim it. If the required same-volume atomic rename/replace
semantics cannot be established, publication fails closed.

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
- **Zero network/broker/credential/profile access**: acceptance requires
  a real dependency boundary, the concrete static/dynamic guards in
  Tests 1-2, the import smoke test in Test 3, and the raising protected-
  environment execution in Test 4. The replay injects deterministic
  false/empty environment state through every core and tomorrow-demo
  call. No such runtime proof is claimed by this docs-only commit.
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
4. `tests/unit/test_crypto_supervised_readiness_trial.py` passes with
   one required, disclosed publication-path change: its hard-coded
   `output_root / "operating_report.md"` read follows
   `packet["artifact_paths"]["operating_report"]` instead. Part 3's
   facade split itself requires no assertion change.
5. New `tests/unit/test_crypto_supervised_readiness_trial_core.py` (or
   folded into the existing file): direct tests of the pure core's
   `receipt_validator` injection, including the new
   `blocked_receipt_validator_not_provided` fail-closed path when
   `receipt_root` is set without a validator; and broker-factory
   propagation through `_run_scenario_matrix`, including preservation
   of the existing facade's two-flag broker-observed behavior and the
   pure replay's no-factory path; and propagation of one explicit
   `paper_environment` snapshot to all six tomorrow-demo calls with a
   pure `_environment_preflight(mapping)`.
6. New `tests/unit/test_tomorrow_crypto_trader_demo_cli.py`: tests that
   the composition root wires `build_alpaca_read_client` through to
   `run_tomorrow_crypto_trader_demo` correctly when both broker flags
   are set (using a fake/mocked adapter, not real credentials), and
   that omitting either flag never constructs a client. Adapter tests
   exercise all thirteen explicit read-only method names and prove
   mutation methods are not exposed.
7. New `tests/unit/test_crypto_readiness_replay.py`: behavior-
   equivalence against direct core calls; parser has no broker/receipt-
   root flags; exact central dispatch, argument forwarding, JSON/text
   rendering, and exit-code behavior. JSON coverage uses an actual
   Decimal-bearing replay packet, not a mocked JSON-native dictionary.
8. `tests/unit/test_dependency_direction.py`'s three new tests (Test
   1's forbidden-prefix check, Test 1's dynamic-loading/string-literal
   ban with all required negative/positive synthetic cases, Test 2's
   closure completeness) all pass.
9. Test 3 (fresh-process `sys.modules` smoke test) and Test 4 (actual
   replay under a raising protected-environment mapping) pass.
10. `tests/unit/test_v5_33_2_source_provenance.py` proves all relocated/
    new modules are source-bound and each changes the aggregate digest.
    `python -m pytest tests/unit/test_dependency_direction.py
     tests/unit/test_alpaca_sdk_client.py
     tests/unit/test_tomorrow_crypto_trader_demo.py
     tests/unit/test_tomorrow_crypto_trader_demo_cli.py
     tests/unit/test_crypto_supervised_readiness_trial.py
     tests/unit/test_crypto_supervised_readiness_trial_core.py
     tests/unit/test_crypto_readiness_replay.py
     tests/unit/test_v5_33_2_source_provenance.py` all pass together in
     one run.
11. The generational bundle interruption/regression test under
    "Atomic Publication" passes, including: legacy fixed-root bundle
    validation; generation-A validity; injected failure after
    generation B is complete but before root-pointer replacement;
    byte-identical and still-valid A after that failure; valid B after
    an un-faulted retry; rejection of mixed-generation, path-escape,
    symlink-escape, support-plus-manifest coordinated tampering, and
    root-integrity/bundle-id mismatch cases; and proof that the
    rejected in-place writer fails the same pre-commit interruption
    assertion.
12. `.\scripts\verify_offline.ps1` passes with the new files present.
13. `git diff --check` clean; no `src`/`tests` file is touched by *this*
    contract-correction commit.

Acceptance for the later wiring step additionally requires re-derived
reachability tests and a manual dry-run showing exactly one eligible
action when the lane's artifact is absent.

## Explicitly Out Of Scope For This Contract

- No `src` file is modified by this document.
- This docs-only correction adds no CLI subcommand,
  `AUTONOMY_ACTION_CLASSIFICATION` entry, or
  `AUTONOMY_EXECUTOR_ALLOWLIST` entry. Part 4 explicitly requires the
  subsequent V5.47 implementation slice to add the
  `crypto-readiness-replay` subparser; that source change is specified
  here but is not performed by this contract commit.
- No `max_age_hours` change to the `crypto_supervised_readiness_trial`
  `LaneSpec` is proposed.
- The bundle-commit atomic-write hardening is specified but not
  implemented.
- The later wiring step is reserved for a separate contract for review-
  separation reasons — not an authorization gap.
- The two PS1-script and one-test-assertion changes in Part 2a are
  specified but not performed here.

## What Changed In This Third Correction (Against Rejected Commit `6f1566d`)

1. Replaced the false in-place packet-last claim with an immutable,
   generation-specific bundle and one atomically replaced root packet.
   The root packet now commits to all supporting hashes/sizes and the
   generation ID commits to semantic content plus content-artifact
   hashes, without a circular packet/manifest relationship.
2. Added a regression-capable interruption test that proves the old
   algorithm fails, the pre-commit old generation remains valid, and
   the post-commit new generation is valid.
3. Disclosed the supporting-artifact location change and required
   legacy fixed-root validation plus a repository-wide consumer audit.
4. Preserved the facade's exact explicit function signature, required
   re-export/import of `SCHEMA_VERSION`, `MILESTONE_NAME`,
   `_json_safe`, `_mapping`, and all existing imported symbols, and
   propagated the broker client factory through the pure core so the
   existing two-flag broker-observed trial path does not regress.
5. Expanded the narrow broker wrapper to all thirteen explicitly
   required read-only names while prohibiting broad forwarding of
   mutation methods.
6. Extended source-provenance binding to every new/relocated executable
   module in the trial/read path.
7. Replaced the length-based literal heuristic with concrete
   docstring-aware AST folding and negative evasion tests.
8. Scoped atomicity to process interruption unless platform durability
   synchronization is separately implemented and tested.
9. Specified exact central CLI parser, dispatch, forwarding, text/JSON
   output, and exit-code behavior while clarifying that this correction
   itself remains docs-only.
10. Moved ambient paper-environment reads to the impure composition
    roots, injected one deterministic offline snapshot through the pure
    core and all six tomorrow-demo calls, distinguished `None` from
    `{}`, and required a raising-environment runtime proof.

## What The Second Correction Changed (Against Rejected Commit `9dd7e14`)

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
3. **Proposed a static dynamic-loading/string-literal test**, beyond
   `ast.Import`/`ast.ImportFrom`. Its intent was retained, but its
   length heuristic still admitted short forbidden roots and the third
   correction replaces it with the concrete AST rules above.
4. The package-aware closure walker, equal-authority/no-operator-gate
   framing for later wiring, additive-not-zero-behavior-change framing
   for the new CLI command, and exact `V5.47` milestone name were
   preserved. The second correction's packet-last protocol was not
   preserved; the third correction replaces it because its
   interruption guarantee was false.

## Next Highest-Leverage Safe Action

**Implement Parts 1-4 as specified above** — the single feasible
implementation action this contract now supports, in this exact order:
(1) extract the pure normalization helper; (2) in
`tomorrow_crypto_trader_demo.py`, delete `_build_alpaca_read_client`
and its self-construct fallback, switch `_read_open_orders` to the
plain-keyword protocol call, and remove `main()`, moving it verbatim
into a new `tomorrow_crypto_trader_demo_cli.py` composition root that
imports the new `tomorrow_crypto_trader_demo_broker_client_adapter.py`
for real client construction and ambient environment snapshots —
updating both PS1 scripts and the one test assertion that reference the
old module path; (3) split
`crypto_supervised_readiness_trial.py` into a pure core module (with
injected, fail-closed receipt validator, broker client factory, and
deterministic environment), an exact-signature behavior-preserving
facade, and extended source-provenance binding; (4) add
`crypto_readiness_replay.py` (importing from
the pure core, not the facade), its fully specified `cli.py` subparser/
dispatch, the generational publication protocol, and every test in
"Tests And Acceptance Criteria",
**without** touching `AUTONOMY_ACTION_CLASSIFICATION` or
`AUTONOMY_EXECUTOR_ALLOWLIST`. This is source-code implementation work,
to be scoped, executed, and verified as its own milestone, separate
from the later reachability-wiring step this contract specifies but
reserves for a subsequent contract.
