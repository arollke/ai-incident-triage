import json

from app.processor import process_incident, process_incident_file
from app.schemas import IncidentTriage, ParsedIncident, Severity


def test_processor_returns_validated_model():
    result = process_incident_file("seed_data/incidents/payment_outage.md")

    assert isinstance(result, IncidentTriage)
    assert result.severity.level is Severity.SEV1
    assert result.confidence == 0.85
    assert result.severity.confidence == 0.85
    assert result.requires_human_review is True
    assert result.action_items
    assert result.action_items[0].owner == "unassigned"
    assert result.action_items[0].status == "open"
    assert result.supporting_evidence


def test_processor_requires_human_review_for_lower_completeness():
    incident = ParsedIncident(
        summary="Internal reporting job failed.",
        impact="Operators could not view the latest report.",
        root_cause="The job failed because a dependency timed out.",
        resolution="The job was retried successfully.",
    )

    result = process_incident(incident)

    assert result.confidence == 0.57
    assert result.requires_human_review is True
    assert result.severity.level is Severity.SEV2


def test_payment_outage_matches_golden_output():
    result = process_incident_file("seed_data/incidents/payment_outage.md")

    with open("seed_data/expected/payment_outage.json", encoding="utf-8") as expected_file:
        expected = json.load(expected_file)

    assert result.model_dump(mode="json") == expected
