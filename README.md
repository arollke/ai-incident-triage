# AI Incident Triage

Weekend MVP vertical slice for an AI Incident Triage & Learning System.

The project reads markdown incident reports, parses common post-incident sections, validates the parsed data with Pydantic, and produces deterministic structured JSON without calling an LLM or external API.

## Requirements

- Python 3.11+
- No secrets or external services required

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
```

The CLI prints pretty-formatted JSON to stdout and exits non-zero if parsing or validation fails.

## Test

```bash
make test
```

## What It Does

- Reads markdown incident reports from `seed_data/incidents/`
- Parses `Summary`, `Timeline`, `Impact`, `Root Cause`, `Resolution`, and `Follow-up Actions`
- Converts parsed incidents into validated Pydantic models
- Runs deterministic rule-based triage for:
  - `summary`
  - `severity`
  - `contributing_factors`
  - `action_items`
  - `confidence`
  - `supporting_evidence`
- Compares demo output to a golden JSON file in `seed_data/expected/`

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

All commands are runnable from a clean checkout after installing dependencies. The project does not rely on local absolute paths, secrets, databases, web services, LangChain, agents, or external APIs.
