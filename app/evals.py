from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.processor import process_incident_file
from app.schemas import IncidentTriage


DEFAULT_INCIDENTS_DIR = Path("seed_data/incidents")
DEFAULT_EXPECTED_DIR = Path("seed_data/expected")
DEFAULT_REPORT_PATH = Path("reports/eval_report.json")


class IncidentEvalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident: str
    schema_valid: bool
    exact_match: bool
    severity_match: bool
    action_item_count_matches: bool
    evidence_present: bool
    error: str | None = None


class EvalReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_incidents: int
    schema_valid_count: int
    exact_match_count: int
    severity_accuracy: float = Field(ge=0.0, le=1.0)
    action_item_count_matches: int
    evidence_present_rate: float = Field(ge=0.0, le=1.0)
    results: list[IncidentEvalResult] = Field(default_factory=list)


def run_evals(
    incidents_dir: Path = DEFAULT_INCIDENTS_DIR,
    expected_dir: Path = DEFAULT_EXPECTED_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> EvalReport:
    incident_paths = sorted(incidents_dir.glob("*.md"))
    results = [_evaluate_incident(path, expected_dir / f"{path.stem}.json") for path in incident_paths]
    report = _build_report(results)
    _write_report(report, report_path)
    return report


def main() -> int:
    report = run_evals()
    print(_format_report(report))
    return 0 if report.exact_match_count == report.total_incidents else 1


def _evaluate_incident(incident_path: Path, expected_path: Path) -> IncidentEvalResult:
    try:
        if not expected_path.exists():
            raise FileNotFoundError(f"Expected fixture not found: {expected_path}")

        actual = process_incident_file(incident_path)
        expected = IncidentTriage.model_validate_json(expected_path.read_text(encoding="utf-8"))

        actual_json = actual.model_dump(mode="json")
        expected_json = expected.model_dump(mode="json")

        return IncidentEvalResult(
            incident=incident_path.name,
            schema_valid=True,
            exact_match=actual_json == expected_json,
            severity_match=actual.severity.level == expected.severity.level,
            action_item_count_matches=len(actual.action_items) == len(expected.action_items),
            evidence_present=_has_evidence(actual),
        )
    except (FileNotFoundError, OSError, ValueError, ValidationError) as exc:
        return IncidentEvalResult(
            incident=incident_path.name,
            schema_valid=False,
            exact_match=False,
            severity_match=False,
            action_item_count_matches=False,
            evidence_present=False,
            error=str(exc),
        )


def _build_report(results: list[IncidentEvalResult]) -> EvalReport:
    total = len(results)
    if total == 0:
        return EvalReport(
            total_incidents=0,
            schema_valid_count=0,
            exact_match_count=0,
            severity_accuracy=0.0,
            action_item_count_matches=0,
            evidence_present_rate=0.0,
            results=[],
        )

    return EvalReport(
        total_incidents=total,
        schema_valid_count=sum(result.schema_valid for result in results),
        exact_match_count=sum(result.exact_match for result in results),
        severity_accuracy=round(sum(result.severity_match for result in results) / total, 2),
        action_item_count_matches=sum(result.action_item_count_matches for result in results),
        evidence_present_rate=round(sum(result.evidence_present for result in results) / total, 2),
        results=results,
    )


def _write_report(report: EvalReport, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _format_report(report: EvalReport) -> str:
    lines = [
        "Incident Triage Eval Report",
        "===========================",
        f"total_incidents: {report.total_incidents}",
        f"schema_valid_count: {report.schema_valid_count}",
        f"exact_match_count: {report.exact_match_count}",
        f"severity_accuracy: {report.severity_accuracy:.2f}",
        f"action_item_count_matches: {report.action_item_count_matches}",
        f"evidence_present_rate: {report.evidence_present_rate:.2f}",
    ]

    failures = [result for result in report.results if result.error or not result.exact_match]
    if failures:
        lines.append("")
        lines.append("Failures:")
        for result in failures:
            detail = result.error or "actual output did not match expected fixture"
            lines.append(f"- {result.incident}: {detail}")

    return "\n".join(lines)


def _has_evidence(triage: IncidentTriage) -> bool:
    return (
        bool(triage.supporting_evidence)
        and bool(triage.severity.evidence)
        and all(factor.evidence for factor in triage.contributing_factors)
        and all(action.evidence for action in triage.action_items)
    )


if __name__ == "__main__":
    raise SystemExit(main())
