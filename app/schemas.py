from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Severity(str, Enum):
    SEV1 = "sev1"
    SEV2 = "sev2"
    SEV3 = "sev3"
    SEV4 = "sev4"


class ContributingFactorCategory(str, Enum):
    CONFIGURATION = "configuration"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    DEPENDENCY = "dependency"
    PROCESS = "process"
    CAPACITY = "capacity"
    UNKNOWN = "unknown"


class ActionItemPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionItemStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class ParsedIncident(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    timeline: list[str] = Field(default_factory=list)
    impact: str = Field(min_length=1)
    root_cause: str = Field(min_length=1)
    resolution: str = Field(min_length=1)
    follow_up_actions: list[str] = Field(default_factory=list)


class SupportingEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: str = Field(min_length=1)
    text: str = Field(min_length=1)


class SeverityAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: Severity
    rationale: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[SupportingEvidence] = Field(default_factory=list)


class ContributingFactor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1)
    category: ContributingFactorCategory
    evidence: list[SupportingEvidence] = Field(default_factory=list)


class ActionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1)
    owner: str = "unassigned"
    priority: ActionItemPriority
    status: ActionItemStatus
    evidence: list[SupportingEvidence] = Field(default_factory=list)


class IncidentTriage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    severity: SeverityAssessment
    contributing_factors: list[ContributingFactor] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    requires_human_review: bool
    supporting_evidence: list[SupportingEvidence] = Field(default_factory=list)
