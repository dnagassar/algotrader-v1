# Assistant v1.36 - Offline Data Freshness Planning + Daily Operator Review Flow

This milestone makes Mission Control more useful as a daily paper-lab operator
console while remaining fully offline and non-broker.

## Goal

Produce a clear daily operator flow around stale or missing local data:

- structured `data_freshness_plan.json`
- visible `operator_review.md`
- Mission Control surfacing in `mission_control.json`, `assistant_report.md`,
  `index.html`, `manifest.jsonl`, and validation
- dispatcher routing toward offline data freshness/operator review improvement
- generated prompts that point agents at `daily_latest`, validation, the data
  freshness plan, and the operator review

## Safety Contract

- Broker reads are not performed.
- Broker mutation is not performed.
- Paper submit is not authorized.
- Live trading is not authorized.
- Stale data is never labeled current.
- `broker_state_not_observed` never claims no positions or no open orders.
- No credentials, network calls, external API setup, paid services, or broker
  SDK/client calls are required for default pytest.
- Generated `runs/`, `.agent_inbox/`, and `docs/reviews/` artifacts must not be
  staged or tracked.

## Implementation Checklist

- [x] Add deterministic data freshness planning fields and artifact.
- [x] Add short daily operator review artifact.
- [x] Surface freshness and operator review in Mission Control.
- [x] Tighten deterministic dispatcher routes and forbidden routes.
- [x] Update generated work-order prompts for the new review flow.
- [x] Preserve Mission Control validation and offline safety invariants.
