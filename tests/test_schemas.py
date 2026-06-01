from app.schemas import IncidentTriage


def test_incident_triage_json_schema_requires_strict_output_fields():
    schema = IncidentTriage.model_json_schema()

    assert set(schema["required"]) == {
        "summary",
        "severity",
        "contributing_factors",
        "action_items",
        "confidence",
        "requires_human_review",
        "supporting_evidence",
    }

    definitions = schema["$defs"]
    assert "evidence" in definitions["SeverityAssessment"]["required"]
    assert "evidence" in definitions["ContributingFactor"]["required"]
    assert "owner" in definitions["ActionItem"]["required"]
    assert "evidence" in definitions["ActionItem"]["required"]
