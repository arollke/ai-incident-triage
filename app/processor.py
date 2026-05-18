from __future__ import annotations

import re
from enum import Enum
from pathlib import Path

from app.parser import parse_incident_file
from app.schemas import (
    ActionItem,
    ActionItemPriority,
    ActionItemStatus,
    ContributingFactor,
    ContributingFactorCategory,
    IncidentTriage,
    ParsedIncident,
    Severity,
    SeverityAssessment,
    SupportingEvidence,
)


SEV1_KEYWORDS = ("outage", "unavailable", "could not complete", "sev1")
SEV2_KEYWORDS = ("degraded", "failed", "failure", "error", "latency", "sev2")
SEV3_KEYWORDS = ("partial", "intermittent", "warning", "retry", "sev3")


class ProcessingMode(str, Enum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"


def process_incident_file(path: str | Path) -> IncidentTriage:
    parsed = parse_incident_file(path)
    return process_incident(parsed)


def process_incident_file_with_mode(path: str | Path, mode: ProcessingMode | str = ProcessingMode.DETERMINISTIC) -> IncidentTriage:
    processing_mode = ProcessingMode(mode)
    if processing_mode is ProcessingMode.DETERMINISTIC:
        return process_incident_file(path)

    from app.llm_processor import process_incident_file_with_llm

    return process_incident_file_with_llm(path)


def process_incident(incident: ParsedIncident) -> IncidentTriage:
    confidence = _confidence(incident)
    supporting_evidence = _supporting_evidence(incident)

    return IncidentTriage(
        summary=incident.summary,
        severity=_assess_severity(incident, confidence),
        contributing_factors=_extract_contributing_factors(incident),
        action_items=_extract_action_items(incident),
        confidence=confidence,
        requires_human_review=confidence < 0.9,
        supporting_evidence=supporting_evidence,
    )


def _assess_severity(incident: ParsedIncident, confidence: float) -> SeverityAssessment:
    severity = _infer_severity(incident)
    rationale = _severity_rationale(severity)
    evidence = [
        SupportingEvidence(section="summary", text=incident.summary),
        SupportingEvidence(section="impact", text=incident.impact),
    ]

    return SeverityAssessment(
        level=severity,
        rationale=rationale,
        confidence=confidence,
        evidence=evidence,
    )


def _infer_severity(incident: ParsedIncident) -> Severity:
    if _is_internal_only_impact(incident.impact):
        return Severity.SEV3

    text = " ".join(
        [
            incident.summary,
            incident.impact,
            incident.root_cause,
        ]
    ).lower()

    if any(keyword in text for keyword in SEV1_KEYWORDS):
        return Severity.SEV1
    if any(keyword in text for keyword in SEV2_KEYWORDS):
        return Severity.SEV2
    if any(keyword in text for keyword in SEV3_KEYWORDS):
        return Severity.SEV3
    return Severity.SEV4


def _is_internal_only_impact(impact: str) -> bool:
    lowered = impact.lower()
    return "internal" in lowered and "no customer-facing" in lowered


def _severity_rationale(severity: Severity) -> str:
    rationales = {
        Severity.SEV1: "Customer-facing outage or complete inability to use a critical flow.",
        Severity.SEV2: "Customer-facing degradation or high error rate in an important flow.",
        Severity.SEV3: "Partial or intermittent impact with available workaround or limited blast radius.",
        Severity.SEV4: "Low impact incident or informational follow-up.",
    }
    return rationales[severity]


def _extract_contributing_factors(incident: ParsedIncident) -> list[ContributingFactor]:
    factor_descriptions: list[str] = []
    root_cause_sentences = _split_sentences(incident.root_cause)

    for sentence in root_cause_sentences:
        lowered = sentence.lower()
        if any(
            keyword in lowered
            for keyword in ("caused", "because", "changed", "configured", "misconfigured", "missing", "exhausted")
        ):
            factor_descriptions.append(sentence)

    if not factor_descriptions:
        factor_descriptions.append(incident.root_cause)

    return [
        ContributingFactor(
            description=description,
            category=_factor_category(description),
            evidence=[SupportingEvidence(section="root_cause", text=incident.root_cause)],
        )
        for description in _dedupe(factor_descriptions)
    ]


def _factor_category(description: str) -> ContributingFactorCategory:
    lowered = description.lower()
    if any(keyword in lowered for keyword in ("deploy", "release", "rollback")):
        return ContributingFactorCategory.DEPLOYMENT
    if any(keyword in lowered for keyword in ("pool", "saturation", "exhausted", "capacity")):
        return ContributingFactorCategory.CAPACITY
    if any(keyword in lowered for keyword in ("config", "limit", "setting")):
        return ContributingFactorCategory.CONFIGURATION
    if any(keyword in lowered for keyword in ("alert", "monitor")):
        return ContributingFactorCategory.MONITORING
    if any(keyword in lowered for keyword in ("vendor", "gateway", "dependency", "third-party")):
        return ContributingFactorCategory.DEPENDENCY
    if any(keyword in lowered for keyword in ("procedure", "process", "review")):
        return ContributingFactorCategory.PROCESS
    return ContributingFactorCategory.UNKNOWN


def _extract_action_items(incident: ParsedIncident) -> list[ActionItem]:
    return [
        ActionItem(
            description=description,
            priority=_action_priority(description),
            status=ActionItemStatus.OPEN,
            evidence=_action_evidence(description, incident),
        )
        for description in incident.follow_up_actions
    ]


def _action_priority(description: str) -> ActionItemPriority:
    lowered = description.lower()
    if any(keyword in lowered for keyword in ("alert", "failure", "pre-deploy", "prevent")):
        return ActionItemPriority.HIGH
    if any(keyword in lowered for keyword in ("document", "runbook", "procedure")):
        return ActionItemPriority.MEDIUM
    return ActionItemPriority.LOW


def _action_evidence(description: str, incident: ParsedIncident) -> list[SupportingEvidence]:
    evidence = [SupportingEvidence(section="follow_up_actions", text=description)]
    lowered = description.lower()

    if any(keyword in lowered for keyword in ("config", "deploy", "rollback", "pool")):
        evidence.append(SupportingEvidence(section="root_cause", text=incident.root_cause))
    if any(keyword in lowered for keyword in ("alert", "failure", "customer")):
        evidence.append(SupportingEvidence(section="impact", text=incident.impact))

    return evidence


def _confidence(incident: ParsedIncident) -> float:
    present_sections = 4
    if incident.timeline:
        present_sections += 1
    if incident.follow_up_actions:
        present_sections += 1
    return round((present_sections / 6) * 0.85, 2)


def _supporting_evidence(incident: ParsedIncident) -> list[SupportingEvidence]:
    evidence = [
        SupportingEvidence(section="impact", text=incident.impact),
        SupportingEvidence(section="root_cause", text=incident.root_cause),
        SupportingEvidence(section="resolution", text=incident.resolution),
    ]

    if incident.timeline:
        evidence.append(SupportingEvidence(section="timeline", text=" | ".join(incident.timeline)))

    return evidence


def _split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
