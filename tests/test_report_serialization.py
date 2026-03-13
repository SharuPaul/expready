from expready.models import Report
from expready.rules import make_issue


def test_report_dict_is_stable() -> None:
    report = Report(
        metadata={
            "metadata_path": "tests/fixtures/metadata_valid.csv",
            "provenance": {"tool_name": "Experiment-Readiness Checker", "tool_version": "0.1.0"},
        }
    )
    report.add_issue(make_issue("META_OK_001"))
    payload = report.to_dict()
    assert payload["status"] == "pass"
    assert payload["severity_counts"] == {"error": 0, "warning": 0, "info": 1}
    assert "section_counts" in payload
    assert "action_plan" in payload
    assert payload["metadata"]["provenance"]["tool_name"] == "Experiment-Readiness Checker"
    assert payload["issues"][0]["rule_id"] == "META_OK_001"
