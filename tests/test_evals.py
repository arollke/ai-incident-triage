import json
from pathlib import Path

from app.evals import EvalReport, IncidentEvalResult, _build_report, run_evals


def test_eval_runner_reports_all_seed_fixtures(tmp_path):
    report_path = tmp_path / "eval_report.json"

    report = run_evals(
        incidents_dir=Path("seed_data/incidents"),
        expected_dir=Path("seed_data/expected"),
        report_path=report_path,
    )

    assert isinstance(report, EvalReport)
    assert report.total_incidents == 5
    assert report.schema_valid_count == 5
    assert report.exact_match_count == 5
    assert report.severity_accuracy == 1.0
    assert report.action_item_count_matches == 5
    assert report.evidence_present_rate == 1.0
    assert report.quality_gates_passed is True
    assert report.quality_gate_failures == []


def test_eval_runner_writes_json_report(tmp_path):
    report_path = tmp_path / "reports" / "eval_report.json"

    report = run_evals(report_path=report_path)

    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved == report.model_dump(mode="json")
    assert saved["total_incidents"] == 5
    assert saved["quality_gates_passed"] is True
    assert saved["quality_gate_failures"] == []
    assert all(result["error"] is None for result in saved["results"])


def test_eval_quality_gates_pass_for_clean_results():
    report = _build_report(
        [
            IncidentEvalResult(
                incident="one.md",
                schema_valid=True,
                exact_match=True,
                severity_match=True,
                action_item_count_matches=True,
                evidence_present=True,
            )
        ]
    )

    assert report.quality_gates_passed is True
    assert report.quality_gate_failures == []


def test_eval_quality_gates_fail_for_low_quality_results():
    report = _build_report(
        [
            IncidentEvalResult(
                incident="one.md",
                schema_valid=True,
                exact_match=False,
                severity_match=False,
                action_item_count_matches=True,
                evidence_present=False,
            ),
            IncidentEvalResult(
                incident="two.md",
                schema_valid=False,
                exact_match=False,
                severity_match=False,
                action_item_count_matches=False,
                evidence_present=False,
                error="invalid schema",
            ),
        ]
    )

    assert report.quality_gates_passed is False
    assert "schema_valid_count 1 != total_incidents 2" in report.quality_gate_failures
    assert "exact_match_count 0 != total_incidents 2" in report.quality_gate_failures
    assert "severity_accuracy 0.00 < 0.80" in report.quality_gate_failures
    assert "evidence_present_rate 0.00 < 0.90" in report.quality_gate_failures
