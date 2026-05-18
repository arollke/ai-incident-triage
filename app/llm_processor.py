from __future__ import annotations

import os
from pathlib import Path

from app.parser import parse_incident_file
from app.schemas import IncidentTriage, ParsedIncident


DEFAULT_MODEL = "gpt-4o-mini"


def process_incident_file_with_llm(path: str | Path) -> IncidentTriage:
    incident = parse_incident_file(path)
    return process_incident_with_llm(incident)


def process_incident_with_llm(incident: ParsedIncident) -> IncidentTriage:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for llm mode.")

    model = os.getenv("INCIDENT_TRIAGE_MODEL", DEFAULT_MODEL)

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("The openai package is required for llm mode. Install project dependencies first.") from exc

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "You are an incident triage assistant. Return only structured JSON that conforms "
                    "to the provided schema. Keep the output evidence-grounded and human-review-first."
                ),
            },
            {
                "role": "user",
                "content": _incident_prompt(incident),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "incident_triage",
                "schema": IncidentTriage.model_json_schema(),
                "strict": True,
            }
        },
    )

    return IncidentTriage.model_validate_json(response.output_text)


def _incident_prompt(incident: ParsedIncident) -> str:
    return "\n".join(
        [
            "Convert this parsed incident report into the IncidentTriage schema.",
            "Use the provided text as evidence. Do not invent facts, owners, statuses, or resolved actions.",
            "Set requires_human_review to true unless the evidence is exceptionally complete.",
            "",
            f"Summary: {incident.summary}",
            f"Timeline: {' | '.join(incident.timeline) if incident.timeline else 'not provided'}",
            f"Impact: {incident.impact}",
            f"Root Cause: {incident.root_cause}",
            f"Resolution: {incident.resolution}",
            f"Follow-up Actions: {' | '.join(incident.follow_up_actions) if incident.follow_up_actions else 'not provided'}",
        ]
    )
