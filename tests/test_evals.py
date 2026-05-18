import json
from pathlib import Path

from app.evals import EvalReport, run_evals


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


def test_eval_runner_writes_json_report(tmp_path):
    report_path = tmp_path / "reports" / "eval_report.json"

    report = run_evals(report_path=report_path)

    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved == report.model_dump(mode="json")
    assert saved["total_incidents"] == 5
    assert all(result["error"] is None for result in saved["results"])
