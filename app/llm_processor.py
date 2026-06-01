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
                    "to the provided schema. Keep the output evidence-grounded and human-review-first. "
                    "Never infer or invent owners, action statuses, facts, or resolutions."
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
            'Use owner "unassigned" unless the incident text explicitly names an owner.',
            "",
            "Severity rubric:",
            "- sev1: broad customer-facing outage, critical flow unavailable, major availability failure, or widespread core service impact.",
            "- sev2: customer-facing degradation, partial outage, elevated error rates, or important functionality impaired.",
            "- sev3: internal-only impact, delayed reporting, limited blast radius, or degraded non-critical workflow.",
            "- sev4: minor issue, no material user impact, cosmetic/manual-process issue, or informational incident.",
            "",
            "Evidence requirements:",
            "- Every severity assessment must include evidence.",
            "- Every contributing factor must include evidence.",
            "- Every action item must include evidence from Follow-up Actions when available.",
            "- supporting_evidence should include at least impact, root_cause, resolution, and timeline evidence where present.",
            "- Do not return empty evidence arrays for action items or contributing factors.",
            "- If evidence is missing, omit that item or lower confidence and keep requires_human_review true.",
            "Keep requires_human_review true unless there is strong evidence and high confidence.",
            "",
            f"Summary: {incident.summary}",
            f"Timeline: {' | '.join(incident.timeline) if incident.timeline else 'not provided'}",
            f"Impact: {incident.impact}",
            f"Root Cause: {incident.root_cause}",
            f"Resolution: {incident.resolution}",
            f"Follow-up Actions: {' | '.join(incident.follow_up_actions) if incident.follow_up_actions else 'not provided'}",
        ]
    )
