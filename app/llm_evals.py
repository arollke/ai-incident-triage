from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.evals import DEFAULT_EXPECTED_DIR, DEFAULT_INCIDENTS_DIR, _has_evidence
from app.processor import process_incident_file
from app.schemas import IncidentTriage


DEFAULT_LLM_REPORT_PATH = Path("reports/llm_eval_report.json")
DEFAULT_PROMPT_VERSION = "llm_triage_v1"
MIN_LLM_EVIDENCE_PRESENT_RATE = 0.80
MIN_LLM_HUMAN_REVIEW_RATE = 0.80
LLMProcessor = Callable[[Path], IncidentTriage | dict]


class LlmIncidentEvalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident: str
    llm_schema_valid: bool
    llm_severity_matches_expected: bool
    llm_severity_matches_deterministic: bool
    llm_action_item_count_matches_expected: bool
    llm_evidence_present: bool
    llm_requires_human_review: bool
    owner_hallucination_detected: bool
    error: str | None = None


class LlmEvalReport(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    model_name: str
    prompt_version: str
    run_timestamp_utc: str
    total_incidents: int
    llm_schema_valid_count: int
    llm_severity_accuracy_against_expected: float = Field(ge=0.0, le=1.0)
    llm_severity_agreement_with_deterministic: float = Field(ge=0.0, le=1.0)
    llm_action_item_count_matches_expected: int
    llm_evidence_present_rate: float = Field(ge=0.0, le=1.0)
    llm_human_review_rate: float = Field(ge=0.0, le=1.0)
    llm_owner_hallucination_count: int
    llm_quality_gates_passed: bool
    llm_quality_gate_failures: list[str] = Field(default_factory=list)
    results: list[LlmIncidentEvalResult] = Field(default_factory=list)


def run_llm_evals(
    incidents_dir: Path = DEFAULT_INCIDENTS_DIR,
    expected_dir: Path = DEFAULT_EXPECTED_DIR,
    report_path: Path = DEFAULT_LLM_REPORT_PATH,
    llm_processor: LLMProcessor | None = None,
) -> LlmEvalReport:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for LLM evals. Set it before running make eval-llm.")

    if llm_processor is None:
        from app.llm_processor import process_incident_file_with_llm

        llm_processor = process_incident_file_with_llm

    incident_paths = sorted(incidents_dir.glob("*.md"))
    results = [
        _evaluate_llm_incident(
            incident_path=path,
            expected_path=expected_dir / f"{path.stem}.json",
            llm_processor=llm_processor,
        )
        for path in incident_paths
    ]
    report = _build_llm_report(results)
    _write_llm_report(report, report_path)
    return report


def main() -> int:
    try:
        report = run_llm_evals()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(_format_llm_report(report))
    has_incident_errors = any(result.error for result in report.results)
    return 0 if not has_incident_errors and report.llm_quality_gates_passed else 1


def _evaluate_llm_incident(
    incident_path: Path,
    expected_path: Path,
    llm_processor: LLMProcessor,
) -> LlmIncidentEvalResult:
    try:
        if not expected_path.exists():
            raise FileNotFoundError(f"Expected fixture not found: {expected_path}")

        deterministic = process_incident_file(incident_path)
        expected = IncidentTriage.model_validate_json(expected_path.read_text(encoding="utf-8"))
        llm_output = IncidentTriage.model_validate(llm_processor(incident_path))
        source_text = incident_path.read_text(encoding="utf-8")

        return LlmIncidentEvalResult(
            incident=incident_path.name,
            llm_schema_valid=True,
            llm_severity_matches_expected=llm_output.severity.level == expected.severity.level,
            llm_severity_matches_deterministic=llm_output.severity.level == deterministic.severity.level,
            llm_action_item_count_matches_expected=len(llm_output.action_items) == len(expected.action_items),
            llm_evidence_present=_has_evidence(llm_output),
            llm_requires_human_review=llm_output.requires_human_review,
            owner_hallucination_detected=_has_owner_hallucination(llm_output, source_text),
        )
    except (FileNotFoundError, OSError, ValueError, ValidationError, RuntimeError) as exc:
        return LlmIncidentEvalResult(
            incident=incident_path.name,
            llm_schema_valid=False,
            llm_severity_matches_expected=False,
            llm_severity_matches_deterministic=False,
            llm_action_item_count_matches_expected=False,
            llm_evidence_present=False,
            llm_requires_human_review=False,
            owner_hallucination_detected=False,
            error=str(exc),
        )


def _build_llm_report(results: list[LlmIncidentEvalResult]) -> LlmEvalReport:
    total = len(results)
    if total == 0:
        quality_gate_failures = _llm_quality_gate_failures(
            total_incidents=0,
            llm_schema_valid_count=0,
            llm_evidence_present_rate=0.0,
            llm_human_review_rate=0.0,
            llm_owner_hallucination_count=0,
        )
        return LlmEvalReport(
            model_name=_llm_model_name(),
            prompt_version=_llm_prompt_version(),
            run_timestamp_utc=_utc_timestamp(),
            total_incidents=0,
            llm_schema_valid_count=0,
            llm_severity_accuracy_against_expected=0.0,
            llm_severity_agreement_with_deterministic=0.0,
            llm_action_item_count_matches_expected=0,
            llm_evidence_present_rate=0.0,
            llm_human_review_rate=0.0,
            llm_owner_hallucination_count=0,
            llm_quality_gates_passed=not quality_gate_failures,
            llm_quality_gate_failures=quality_gate_failures,
            results=[],
        )

    llm_schema_valid_count = sum(result.llm_schema_valid for result in results)
    llm_evidence_present_rate = round(sum(result.llm_evidence_present for result in results) / total, 2)
    llm_human_review_rate = round(sum(result.llm_requires_human_review for result in results) / total, 2)
    llm_owner_hallucination_count = sum(result.owner_hallucination_detected for result in results)
    quality_gate_failures = _llm_quality_gate_failures(
        total_incidents=total,
        llm_schema_valid_count=llm_schema_valid_count,
        llm_evidence_present_rate=llm_evidence_present_rate,
        llm_human_review_rate=llm_human_review_rate,
        llm_owner_hallucination_count=llm_owner_hallucination_count,
    )

    return LlmEvalReport(
        model_name=_llm_model_name(),
        prompt_version=_llm_prompt_version(),
        run_timestamp_utc=_utc_timestamp(),
        total_incidents=total,
        llm_schema_valid_count=llm_schema_valid_count,
        llm_severity_accuracy_against_expected=round(
            sum(result.llm_severity_matches_expected for result in results) / total,
            2,
        ),
        llm_severity_agreement_with_deterministic=round(
            sum(result.llm_severity_matches_deterministic for result in results) / total,
            2,
        ),
        llm_action_item_count_matches_expected=sum(
            result.llm_action_item_count_matches_expected for result in results
        ),
        llm_evidence_present_rate=llm_evidence_present_rate,
        llm_human_review_rate=llm_human_review_rate,
        llm_owner_hallucination_count=llm_owner_hallucination_count,
        llm_quality_gates_passed=not quality_gate_failures,
        llm_quality_gate_failures=quality_gate_failures,
        results=results,
    )


def _write_llm_report(report: LlmEvalReport, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _format_llm_report(report: LlmEvalReport) -> str:
    lines = [
        "LLM Incident Triage Eval Report",
        "===============================",
        f"model_name: {report.model_name}",
        f"prompt_version: {report.prompt_version}",
        f"run_timestamp_utc: {report.run_timestamp_utc}",
        f"total_incidents: {report.total_incidents}",
        f"llm_schema_valid_count: {report.llm_schema_valid_count}",
        (
            "llm_severity_accuracy_against_expected: "
            f"{report.llm_severity_accuracy_against_expected:.2f}"
        ),
        (
            "llm_severity_agreement_with_deterministic: "
            f"{report.llm_severity_agreement_with_deterministic:.2f}"
        ),
        (
            "llm_action_item_count_matches_expected: "
            f"{report.llm_action_item_count_matches_expected}"
        ),
        f"llm_evidence_present_rate: {report.llm_evidence_present_rate:.2f}",
        f"llm_human_review_rate: {report.llm_human_review_rate:.2f}",
        f"llm_owner_hallucination_count: {report.llm_owner_hallucination_count}",
        "",
        "LLM Quality Gates",
        "-----------------",
        f"llm_quality_gates_passed: {str(report.llm_quality_gates_passed).lower()}",
    ]

    if report.llm_quality_gate_failures:
        lines.append("llm_quality_gate_failures:")
        for failure in report.llm_quality_gate_failures:
            lines.append(f"- {failure}")
    else:
        lines.append("llm_quality_gate_failures: none")

    lines.extend(
        [
            "",
            "Incidents",
            "---------",
        ]
    )

    for result in report.results:
        lines.append(
            "- "
            f"{result.incident}: "
            f"schema_valid={str(result.llm_schema_valid).lower()}, "
            f"severity_expected={str(result.llm_severity_matches_expected).lower()}, "
            f"severity_deterministic={str(result.llm_severity_matches_deterministic).lower()}, "
            f"action_count_expected={str(result.llm_action_item_count_matches_expected).lower()}, "
            f"evidence_present={str(result.llm_evidence_present).lower()}, "
            f"requires_human_review={str(result.llm_requires_human_review).lower()}, "
            f"owner_hallucination={str(result.owner_hallucination_detected).lower()}"
        )
        if result.error:
            lines.append(f"  error: {result.error}")

    return "\n".join(lines)


def _llm_quality_gate_failures(
    total_incidents: int,
    llm_schema_valid_count: int,
    llm_evidence_present_rate: float,
    llm_human_review_rate: float,
    llm_owner_hallucination_count: int,
) -> list[str]:
    failures: list[str] = []

    if llm_schema_valid_count != total_incidents:
        failures.append(
            f"llm_schema_valid_count {llm_schema_valid_count} != total_incidents {total_incidents}"
        )
    if llm_evidence_present_rate < MIN_LLM_EVIDENCE_PRESENT_RATE:
        failures.append(
            f"llm_evidence_present_rate {llm_evidence_present_rate:.2f} < "
            f"{MIN_LLM_EVIDENCE_PRESENT_RATE:.2f}"
        )
    if llm_human_review_rate < MIN_LLM_HUMAN_REVIEW_RATE:
        failures.append(
            f"llm_human_review_rate {llm_human_review_rate:.2f} < "
            f"{MIN_LLM_HUMAN_REVIEW_RATE:.2f}"
        )
    if llm_owner_hallucination_count != 0:
        failures.append(f"llm_owner_hallucination_count {llm_owner_hallucination_count} != 0")

    return failures


def _owner_hallucination_detected(triage: IncidentTriage, source_text: str) -> bool:
    normalized_source = source_text.casefold()
    return any(
        action.owner != "unassigned" and action.owner.casefold() not in normalized_source
        for action in triage.action_items
    )

def _has_owner_hallucination(
    triage: IncidentTriage,
    source_text: str,
) -> bool:
    lowered = source_text.lower()

    for item in triage.action_items:
        owner = item.owner.strip()

        if owner == "unassigned":
            continue

        if owner.lower() not in lowered:
            return True

    return False


def _llm_model_name() -> str:
    from app.llm_processor import DEFAULT_MODEL

    return os.getenv("INCIDENT_TRIAGE_MODEL", DEFAULT_MODEL)


def _llm_prompt_version() -> str:
    return os.getenv("INCIDENT_TRIAGE_PROMPT_VERSION", DEFAULT_PROMPT_VERSION)


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
