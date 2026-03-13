from pathlib import Path

from expready.loaders import load_metadata
from expready.validators import validate_metadata


FIXTURES = Path(__file__).parent / "fixtures"


def test_valid_metadata_has_info_pass_issue() -> None:
    df = load_metadata(FIXTURES / "metadata_valid.csv")
    issues = validate_metadata(df, condition_column="condition")
    assert any(issue.rule_id == "META_OK_001" for issue in issues)
    assert all(issue.severity.value != "error" for issue in issues)


def test_duplicate_sample_ids_are_errors() -> None:
    df = load_metadata(FIXTURES / "metadata_duplicate.csv")
    issues = validate_metadata(df, condition_column="condition")
    assert any(issue.rule_id == "META_DUP_001" for issue in issues)
    assert any(issue.severity.value == "error" for issue in issues)


def test_missing_required_column_is_error() -> None:
    df = load_metadata(FIXTURES / "metadata_missing_required.csv")
    issues = validate_metadata(df, condition_column="condition")
    assert any(issue.rule_id == "META_REQ_001" for issue in issues)
