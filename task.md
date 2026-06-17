# Assistant v1.33 - Mission Control v0

Direction change: the candidate gap closure queue is complete after item 012.
This milestone does not add a new queue item, SMA catalog expansion, strategy
promotion, optimizer, registry expansion, or backtest engine.

## Goal

Produce one visible, self-contained daily paper-lab operating picture:

- local `index.html` dashboard
- `assistant_report.md`
- structured `mission_control.json`
- deterministic readiness score
- market-data lane
- broker-state lane
- decision lane
- work-order exports
- ignored local `.agent_inbox/` files
- rule-based dispatcher v0
- explicit `BrokerStateMode`
- `alpaca_paper_read_only` scaffold only, with no broker read in v1.33

## Safety Contract

- Default mode is `broker_state_not_observed`.
- `alpaca_paper_read_only` is scaffold-only and reports a blocked/read-requires-authorization state.
- Broker reads are not performed.
- Broker mutation is not performed.
- Paper submit is not authorized.
- Live trading is not authorized.
- No credentials, network calls, or broker SDK/client calls are required for default pytest.

## Implementation Checklist

- [x] Add Mission Control artifact generation to the existing daily paper-lab command.
- [x] Add deterministic readiness score with safety-gate override.
- [x] Add rule-based dispatcher v0 and handoff/work-order exports.
- [x] Add local ignored `.agent_inbox/` handoff files.
- [x] Add explicit `BrokerStateMode` in config, CLI, and PowerShell launcher.
- [x] Preserve existing offline safety rails and legacy packet validation.
