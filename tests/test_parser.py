import pytest

from app.parser import parse_incident_file, parse_incident_markdown


def test_parse_payment_outage_sections():
    incident = parse_incident_file("seed_data/incidents/payment_outage.md")

    assert incident.summary == (
        "Checkout payments were unavailable for customers in the US region for 42 minutes on Saturday morning."
    )
    assert len(incident.timeline) == 5
    assert incident.timeline[0] == "09:02 UTC - Alert fired for elevated payment authorization failures."
    assert "18% of checkout attempts failed" in incident.impact
    assert "connection pool limit from 100 to 20" in incident.root_cause
    assert incident.follow_up_actions == [
        "Add a pre-deploy configuration check for payment gateway pool limits.",
        "Add an alert for connection pool saturation before customer-facing failures occur.",
        "Document the rollback procedure for payment gateway configuration changes.",
    ]


def test_parse_requires_core_sections():
    markdown = """
## Summary
Something happened.

## Impact
Customers were impacted.
"""

    with pytest.raises(ValueError, match="root_cause, resolution"):
        parse_incident_markdown(markdown)
