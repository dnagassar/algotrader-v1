# Phase 34 Step 2 - External Research Artifact Intake Checklist

## Purpose

This checklist defines how external research artifacts enter the project trail
before they can influence project decisions.

The local Git repository, reviewed docs, and deterministic tests remain the
trust boundary. External artifacts may accelerate discovery, critique, and
context gathering, but they do not become trusted production dependencies,
source-of-truth artifacts, validated research, validated signal definitions,
normal pytest inputs, or trading-path behavior.

This phase is documentation-only. It adds no implementation, dependency,
notebook, data, schema, script, evaluator, signal computation, broker behavior,
runtime behavior, scheduler behavior, persistence behavior, QuantConnect
integration, vectorbt integration, ML behavior, LLM runtime integration, or
trading implication.

## Artifact Types Covered

Coverage means intake rules apply. It does not mean the artifact is trusted,
approved, canonical, reproducible, or eligible for implementation.

| Artifact type | Intake handling |
| --- | --- |
| Perplexity reports | Scout research only. Record cited sources, inferred claims, uncertainty, and required primary-source checks. |
| Claude/Gemini reviews | Critique only. Record issues found, contradictions suggested, and claims that still need repo or source verification. |
| Codex implementation reports | Local scoped-agent reports only. Trust comes from reviewed diffs, docs, tests, and human review, not from the report text. |
| QuantConnect results | External reference only. Record platform, settings, data assumptions, dates, and why project-local reproduction is still required. |
| vectorbt experiments | Prototype notes only unless a later scoped phase approves dependency policy, deterministic behavior, and tests. |
| Notebooks | Exploratory only. They are not canonical and cannot be treated as reviewed evidence without later normalization. |
| Vendor/public data documentation | Candidate context or candidate evidence only. Terms, license, storage, provenance, citation, and offline-use questions remain open until reviewed. |
| Academic/practitioner papers | Candidate evidence only. Prefer primary sources, separate method claims from performance claims, and record reproducibility gaps. |
| Spreadsheets/ad hoc analysis files | Scratch analysis only. Record formulas, inputs, assumptions, and uncertainty before any reviewed-doc normalization. |
| Screenshots/manual observations | Manual observation only. Record date, source identity, URL or file identity, and the exact observation made. |

## Required Intake Metadata

Each external artifact should record:

- artifact title
- source/tool
- date received or reviewed
- author/tool identity
- input prompt or query if applicable
- files/links reviewed
- source type: primary / secondary / LLM inference / manual observation
- claims made
- evidence cited
- assumptions
- uncertainty
- proposed use
- allowed status: scout / critique / context / candidate evidence / rejected /
  needs verification

Allowed status meanings:

| Status | Meaning |
| --- | --- |
| scout | May point reviewers toward sources or questions. It is not evidence by itself. |
| critique | May identify risks, contradictions, missing tests, or unclear language. It is not disposition authority. |
| context | May provide background only. It cannot support promotion or implementation. |
| candidate evidence | May be reviewed later after source quality, scope, and uncertainty are recorded. It is not validated. |
| rejected | Should not influence project decisions except as a recorded rejected route or unsupported claim. |
| needs verification | Requires primary-source, repo-local, terms, license, or deterministic reproduction review before further use. |

## Evidence Classification

Use these labels when normalizing claims from external artifacts:

| Evidence label | Meaning |
| --- | --- |
| primary source | Direct source material such as official documentation, paper text, source-owner terms, or original methodology/results. |
| secondary source | Commentary, summaries, derived writeups, indexes, or third-party explanations about primary material. |
| external-tool inference | LLM, hosted platform, notebook, vectorbt, QuantConnect, spreadsheet, or ad hoc conclusion that requires verification. |
| local repo evidence | Reviewed project docs, code, tests, fixtures, git history, or deterministic local verification output. |
| manual observation | Human-observed screenshot, web page, UI state, or file inspection with date and source identity recorded. |
| unverified claim | A claim lacking sufficient evidence, source identity, reproducibility, or review. |
| rejected / unsupported claim | A claim that conflicts with reviewed evidence, lacks required support, or is out of scope. |

LLM-generated text, hosted backtest output, notebook output, screenshots, and
spreadsheet conclusions are not primary evidence unless the underlying source
material itself is primary and separately reviewed.

## Required Review Questions

Before an artifact can affect a project decision, reviewers should answer:

- What claim is being made?
- Is the claim supported by primary evidence?
- Does it conflict with existing repo docs?
- Does it require current web/source verification?
- Does it involve data, licensing, performance, methodology, or
  implementation claims?
- Does it require deterministic local reproduction before trust?
- Does it introduce lookahead, survivorship, data-snooping, or licensing risk?
- Does it imply code, dependency, network, credential, broker, runtime, or
  trading-path behavior?
- What is explicitly out of scope?

If any answer is unknown, the artifact remains scout, critique, context,
rejected, or needs verification. Unknowns do not become approvals.

## Routing Outcomes

Possible routing outcomes:

| Outcome | Use |
| --- | --- |
| reject | Record why the artifact or claim should not influence the project. |
| keep as scout/context only | Preserve as background or discovery input without promotion. |
| normalize into docs/design | Convert reviewed claims, evidence labels, uncertainty, non-claims, and routing decisions into a phase document. |
| place in docs/proposals if speculative | Store speculative external-agent output only if `docs/proposals` exists or is explicitly created later for that purpose. |
| require primary-source verification | Block further reliance until primary material is checked and cited. |
| require terms/license review | Block source, data, storage, or publication use until terms and license questions are reviewed. |
| require deterministic reproduction plan | Block trust until a repo-local, offline-safe, deterministic reproduction plan is scoped. |
| require human owner decision | Route unresolved scope, budget, legal, data, or priority decisions to a human owner. |
| eligible for later scoped phase | Allow a future prompt to define narrow docs, tests, data-policy, or implementation scope without approving it now. |

## Promotion Constraints

External artifacts cannot directly create or approve:

- `ValidatedResearchArtifact`
- `ValidatedSignalDefinition`
- signal/evaluator code
- production threshold/config
- trading action
- broker/runtime behavior
- normal pytest dependency
- source/data approval

They also cannot directly approve notebooks as canonical, vendor/public data as
project data, hosted backtest results as reproduced, or LLM output as project
authority.

## Repository Placement

Repository placement rules:

- `docs/design` is for reviewed phase decisions, boundaries, normalized
  evidence summaries, and project policy.
- `docs/proposals` is for speculative external-agent outputs only if that
  directory exists or is explicitly created later.
- `docs/project_checkpoint.md` is for concise milestone records after a phase
  decision is complete.
- Raw vendor data, downloaded datasets, notebook outputs, hosted exports, and
  scratch analysis files must not be added without an approved storage/fixture
  policy.
- `src` may change only after later scoped implementation approval.
- Tests should change only when a later phase explicitly needs deterministic
  enforcement.

Normal `python -m pytest` must remain offline, credential-free,
deterministic, and free of external service, broker, notebook, data download,
ML, LLM, QuantConnect, vectorbt, runtime, scheduler, and trading-path calls.

## Checklist Template

Future phases may copy this intake section:

```markdown
## External Research Artifact Intake

- [ ] Artifact title:
- [ ] Source/tool:
- [ ] Date received or reviewed:
- [ ] Author/tool identity:
- [ ] Input prompt or query, if applicable:
- [ ] Files/links reviewed:
- [ ] Source type: primary / secondary / LLM inference / manual observation
- [ ] Claims made:
- [ ] Evidence cited:
- [ ] Evidence labels:
- [ ] Assumptions:
- [ ] Uncertainty:
- [ ] Proposed use:
- [ ] Allowed status: scout / critique / context / candidate evidence /
      rejected / needs verification

### Review Questions

- [ ] What claim is being made?
- [ ] Is the claim supported by primary evidence?
- [ ] Does it conflict with existing repo docs?
- [ ] Does it require current web/source verification?
- [ ] Does it involve data, licensing, performance, methodology, or
      implementation claims?
- [ ] Does it require deterministic local reproduction before trust?
- [ ] Does it introduce lookahead, survivorship, data-snooping, or licensing
      risk?
- [ ] Does it imply code, dependency, network, credential, broker, runtime, or
      trading-path behavior?
- [ ] What is explicitly out of scope?

### Routing

- [ ] Outcome: reject / keep as scout/context only / normalize into docs/design /
      place in docs/proposals if later approved / require primary-source
      verification / require terms/license review / require deterministic
      reproduction plan / require human owner decision / eligible for later
      scoped phase
- [ ] Required follow-up:
- [ ] Explicit non-goals:
- [ ] Decision owner, if needed:
- [ ] Normal pytest impact: none, or blocked until isolated
- [ ] Repository placement:
```

Completing the template records intake only. It does not validate, approve,
promote, implement, reproduce, or make any artifact actionable.

## Recommended Next Routing

Recommended next docs-only gate: notebook/prototype policy boundary.

That gate should define how notebooks, vectorbt prototypes, spreadsheets, and
other exploratory artifacts may be referenced or summarized without becoming
canonical repo artifacts, dependencies, datasets, normal pytest inputs,
validated research, signal definitions, or trading-path behavior. It should
not create notebooks, add vectorbt, add data, implement reproduction, or
approve any prototype as trusted.

## Explicit Non-Goals

This phase does not perform or authorize:

- implementation
- dependencies
- dependency lockfile changes
- notebooks
- data acquisition
- data ingestion
- schema/code/script/contract type
- backtest
- reproduction
- QuantConnect/vectorbt integration
- LLM runtime integration
- ML behavior
- evaluator/signal implementation
- signal computation
- signal scoring, ranking, direction, confidence, or actionability
- `ValidatedResearchArtifact`
- `ValidatedSignalDefinition`
- production threshold
- source approval
- data approval
- profitability claim
- trading implication

## Remaining Blockers

Evaluator implementation, validation, reproduction, production routing, and
trading use remain blocked by all of the following:

- no `ValidatedResearchArtifact` from external artifacts
- no `ValidatedSignalDefinition` from external artifacts
- no approved external research integration
- no approved data storage/fixture policy
- no approved Phase 33 source/universe/benchmark/cash proxy
- no project-local deterministic reproduction
- no no-lookahead audit
- no implementation-scope approval
- no evaluator tests
- no approved notebook/prototype policy
- no approved terms/license route for external data or hosted outputs
- no approved source/data approval route from external artifacts
- no approved result-review template for reproduced outputs
- no promotion/rejection decision for any specific external artifact
- no trading implication or production threshold
