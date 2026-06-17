# Assistant v1.38 - Offline Accepted Data Refresh Bridge

This milestone makes Mission Control more operational around stale accepted data
without adding any data download, broker, credential, paper-submit, live-trading,
paid-service, or strategy-promotion surface.

## Goal

Add a deterministic local bridge for a future operator-supplied SPY adjusted-close
CSV:

- `data_refresh_bridge.json`
- `data_refresh_operator_checklist.md`
- Mission Control, latest-run, manifest, report, operator-review, and validation
  references to both artifacts
- dispatcher/work-order routing toward offline accepted-data refresh bridge work
- validator failures when bridge/checklist artifacts or references are missing

## Safety Contract

- Broker reads are not performed.
- Broker mutation is not performed.
- Paper submit is not authorized.
- Live trading is not authorized.
- Stale data is never labeled current.
- `broker_state_not_observed` never claims no positions or no open orders.
- No credentials, network calls, external API setup, paid services, or broker
  SDK/client calls are required for default pytest.
- Operator-supplied CSVs and generated `.data/`, `runs/`, `.agent_inbox/`, and
  `docs/reviews/` artifacts must not be staged or tracked.

## Implementation Checklist

- [x] Add deterministic data refresh bridge artifact.
- [x] Add short operator-facing data refresh checklist artifact.
- [x] Surface refresh bridge/checklist in Mission Control and latest-run.
- [x] Tighten Mission Control validation for refresh artifacts and safety fields.
- [x] Update dispatcher/work-order routing around offline data refresh.
- [x] Preserve stale-data preview-only and broker-state-not-observed invariants.
