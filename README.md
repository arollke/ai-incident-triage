# AI Incident Triage & Learning System

> Production-minded system for converting engineering incident reports into structured, auditable operational insights with evals and human-in-the-loop controls.

## Why

Incident reports are often inconsistent, difficult to search, and hard to learn from over time. This leads to:

- repeated incidents without clear pattern detection
- inconsistent severity classification
- poor visibility into systemic failure modes
- manual and subjective post-incident analysis

This project focuses on turning incidents into **structured, reviewable operational intelligence**, with a strong emphasis on:

- reliability engineering practices
- deterministic processing before AI
- evidence-grounded outputs
- measurable quality via evals
- safe AI adoption with human oversight

## Requirements

- Python 3.11+
- No secrets or external services required for deterministic mode
- `OPENAI_API_KEY` is required only for experimental LLM mode

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Demo

```bash
make demo
```

Equivalent CLI usage:

```bash
python -m app.cli ingest seed_data/incidents/payment_outage.md
python -m app.cli ingest seed_data/incidents/payment_outage.md --mode deterministic
```

The CLI prints pretty-formatted JSON to stdout and exits non-zero if parsing or validation fails.

## Test

```bash
make test
```

## Eval

```bash
make eval
```

The offline eval runner uses deterministic mode only. It reads markdown incidents from `seed_data/incidents/`, compares structured outputs against matching JSON fixtures in `seed_data/expected/`, prints a readable summary, applies quality gates, and writes `reports/eval_report.json`.

Deterministic evals are CI-safe: they do not require secrets, network access, or external services, and the same input should produce the same structured output every run.

The eval measures:

- `total_incidents`
- `schema_valid_count`
- `exact_match_count`
- `severity_accuracy`
- `action_item_count_matches`
- `evidence_present_rate`
- `quality_gates_passed`
- `quality_gate_failures`

Quality gates fail `make eval` if:

- `severity_accuracy` is below `0.80`
- `evidence_present_rate` is below `0.90`
- `schema_valid_count` does not equal `total_incidents`
- `exact_match_count` does not equal `total_incidents`

These gates protect the deterministic baseline before adding more AI sophistication, making regressions visible before experimental LLM behavior is introduced.

### Experimental LLM Eval

```bash
OPENAI_API_KEY=... make eval-llm
```

`make eval-llm` is experimental and is not required for CI. It requires `OPENAI_API_KEY`, calls the LLM processor for each incident, validates the LLM output against the `IncidentTriage` schema, compares LLM output against the expected fixtures, and compares LLM output against deterministic output. It writes `reports/llm_eval_report.json` and prints a readable summary.

LLM evals do not require exact fixture matches. Instead, their quality gates check minimum safety and quality expectations: every LLM output must be schema-valid, at least `0.80` of incidents must include evidence throughout the triage output, and at least `0.80` must keep the human-review-first behavior by setting `requires_human_review`.

The LLM eval reports:

- `total_incidents`
- `llm_schema_valid_count`
- `llm_severity_accuracy_against_expected`
- `llm_severity_agreement_with_deterministic`
- `llm_action_item_count_matches_expected`
- `llm_evidence_present_rate`
- `llm_human_review_rate`
- `llm_quality_gates_passed`
- `llm_quality_gate_failures`
- `model_name`
- `prompt_version`
- `run_timestamp_utc`

## What It Does

- Reads markdown incident reports from `seed_data/incidents/`
- Parses `Summary`, `Timeline`, `Impact`, `Root Cause`, `Resolution`, and `Follow-up Actions`
- Converts parsed incidents into validated Pydantic models
- Supports two processing modes:
  - `deterministic`
  - `llm`
- Produces structured triage output for:
  - `summary`
  - `severity`
  - `contributing_factors`
  - `action_items`
  - `confidence`
  - `requires_human_review`
  - `supporting_evidence`
- Compares demo output to a golden JSON file in `seed_data/expected/`
- Runs offline deterministic evals against all expected fixtures
- Runs optional experimental LLM comparison evals when `OPENAI_API_KEY` is configured

## Processing Modes

### Deterministic Mode

Deterministic mode is the default:

```bash
python -m app.cli ingest seed_data/incidents/payment_outage.md
python -m app.cli ingest seed_data/incidents/payment_outage.md --mode deterministic
```

This mode uses stable rule-based extraction and classification. It does not call an LLM, does not require secrets, and is used for repeatable evals and golden tests.

### LLM Mode

LLM mode is experimental and human-review-first:

```bash
OPENAI_API_KEY=... python -m app.cli ingest seed_data/incidents/payment_outage.md --mode llm
```

Environment variables:

- `OPENAI_API_KEY`: required for `--mode llm`
- `INCIDENT_TRIAGE_MODEL`: optional, defaults to `gpt-4o-mini`

LLM mode uses the same `IncidentTriage` Pydantic schema as deterministic mode and validates model output before printing JSON. If `OPENAI_API_KEY` is missing, the command fails safely with a clear error and non-zero exit code.

## Design Principles

- Deterministic-first, AI-second
- Structured outputs over free-text summaries
- Evidence-grounded extraction
- Human review as default
- Eval-driven development
- Minimal architecture (no unnecessary infrastructure)

## GitHub/Codex Cloud Setup Notes

1. Create an empty GitHub repo named `ai-incident-triage`.
2. Add the remote using the actual GitHub username or org, not an email address:

```bash
git remote add origin git@github.com:arollke/ai-incident-triage.git
```

3. Push:

```bash
git branch -M main
git push -u origin main
```

4. In Codex Cloud, connect/select that GitHub repo as the workspace.

All commands are runnable from a clean checkout after installing dependencies. The project deliberately avoids unnecessary infrastructure (databases, web services, agents, orchestration frameworks) to focus on correctness, determinism, and operational clarity.
