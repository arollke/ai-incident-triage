import json
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from app.llm_evals import LlmIncidentEvalResult, _build_llm_report, _format_llm_report, main, run_llm_evals
from app.schemas import IncidentTriage


def test_llm_eval_fails_clearly_without_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is required for LLM evals"):
        run_llm_evals(report_path=tmp_path / "llm_eval_report.json")


def test_llm_eval_aggregation_works_with_mocked_llm_results():
    report = _build_llm_report(
        [
            LlmIncidentEvalResult(
                incident="one.md",
                llm_schema_valid=True,
                llm_severity_matches_expected=True,
                llm_severity_matches_deterministic=True,
                llm_action_item_count_matches_expected=True,
                llm_evidence_present=True,
                llm_requires_human_review=True,
            ),
            LlmIncidentEvalResult(
                incident="two.md",
                llm_schema_valid=True,
                llm_severity_matches_expected=False,
                llm_severity_matches_deterministic=True,
                llm_action_item_count_matches_expected=False,
                llm_evidence_present=False,
                llm_requires_human_review=False,
            ),
        ]
    )

    assert report.total_incidents == 2
    assert report.llm_schema_valid_count == 2
    assert report.llm_severity_accuracy_against_expected == 0.5
    assert report.llm_severity_agreement_with_deterministic == 1.0
    assert report.llm_action_item_count_matches_expected == 1
    assert report.llm_evidence_present_rate == 0.5
    assert report.llm_human_review_rate == 0.5
    assert report.llm_quality_gates_passed is False
    assert "llm_evidence_present_rate 0.50 < 0.80" in report.llm_quality_gate_failures
    assert "llm_human_review_rate 0.50 < 0.80" in report.llm_quality_gate_failures


def test_llm_eval_runner_uses_mocked_llm_processor(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("INCIDENT_TRIAGE_MODEL", "test-model")
    monkeypatch.setenv("INCIDENT_TRIAGE_PROMPT_VERSION", "test_prompt_v2")
    report_path = tmp_path / "reports" / "llm_eval_report.json"

    def mocked_llm_processor(path: Path) -> IncidentTriage:
        expected_path = Path("seed_data/expected") / f"{path.stem}.json"
        return IncidentTriage.model_validate_json(expected_path.read_text(encoding="utf-8"))

    report = run_llm_evals(report_path=report_path, llm_processor=mocked_llm_processor)
    saved = json.loads(report_path.read_text(encoding="utf-8"))

    assert saved == report.model_dump(mode="json")
    assert report.model_name == "test-model"
    assert report.prompt_version == "test_prompt_v2"
    assert report.run_timestamp_utc.endswith("Z")
    datetime.fromisoformat(report.run_timestamp_utc.replace("Z", "+00:00"))
    assert report.total_incidents == 5
    assert report.llm_schema_valid_count == 5
    assert report.llm_severity_accuracy_against_expected == 1.0
    assert report.llm_severity_agreement_with_deterministic == 1.0
    assert report.llm_action_item_count_matches_expected == 5
    assert report.llm_evidence_present_rate == 1.0
    assert report.llm_human_review_rate == 1.0
    assert report.llm_quality_gates_passed is True
    assert report.llm_quality_gate_failures == []


def test_llm_eval_quality_gate_failure_for_invalid_schema_count():
    report = _build_llm_report(
        [
            LlmIncidentEvalResult(
                incident="one.md",
                llm_schema_valid=False,
                llm_severity_matches_expected=False,
                llm_severity_matches_deterministic=False,
                llm_action_item_count_matches_expected=False,
                llm_evidence_present=False,
                llm_requires_human_review=False,
                error="invalid schema",
            )
        ]
    )

    assert report.llm_quality_gates_passed is False
    assert "llm_schema_valid_count 0 != total_incidents 1" in report.llm_quality_gate_failures


def test_llm_eval_format_prints_quality_gates():
    report = _build_llm_report(
        [
            LlmIncidentEvalResult(
                incident="one.md",
                llm_schema_valid=True,
                llm_severity_matches_expected=True,
                llm_severity_matches_deterministic=True,
                llm_action_item_count_matches_expected=True,
                llm_evidence_present=True,
                llm_requires_human_review=True,
            )
        ]
    )

    formatted = _format_llm_report(report)

    assert "model_name: " in formatted
    assert "prompt_version: llm_triage_v1" in formatted
    assert "run_timestamp_utc: " in formatted
    assert "LLM Quality Gates" in formatted
    assert "llm_quality_gates_passed: true" in formatted
    assert "llm_quality_gate_failures: none" in formatted


def test_llm_eval_main_fails_when_quality_gates_fail(monkeypatch, capsys):
    report = _build_llm_report(
        [
            LlmIncidentEvalResult(
                incident="one.md",
                llm_schema_valid=True,
                llm_severity_matches_expected=True,
                llm_severity_matches_deterministic=True,
                llm_action_item_count_matches_expected=True,
                llm_evidence_present=False,
                llm_requires_human_review=False,
            )
        ]
    )
    monkeypatch.setattr("app.llm_evals.run_llm_evals", lambda: report)

    exit_code = main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "llm_quality_gates_passed: false" in captured.out
    assert captured.err == ""


def test_llm_eval_main_fails_when_incident_error_exists(monkeypatch, capsys):
    report = _build_llm_report(
        [
            LlmIncidentEvalResult(
                incident="one.md",
                llm_schema_valid=True,
                llm_severity_matches_expected=True,
                llm_severity_matches_deterministic=True,
                llm_action_item_count_matches_expected=True,
                llm_evidence_present=True,
                llm_requires_human_review=True,
                error="provider failed after validation",
            )
        ]
    )
    monkeypatch.setattr("app.llm_evals.run_llm_evals", lambda: report)

    exit_code = main()
    captured = capsys.readouterr()

    assert report.llm_quality_gates_passed is True
    assert exit_code == 1
    assert "error: provider failed after validation" in captured.out
    assert captured.err == ""


def test_make_eval_still_works():
    completed = subprocess.run(
        ["make", "eval"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "Incident Triage Eval Report" in completed.stdout
    assert "quality_gates_passed: true" in completed.stdout
