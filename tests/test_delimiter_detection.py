from pathlib import Path

from expready.models import StudyConfig
from expready.validation import run_validation


def test_inconsistent_delimiters_are_reported_as_blocking_issue() -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    config = StudyConfig(
        metadata_path=fixture_dir / "metadata_valid.csv",
        metadata_sample_column="sample_id",
        condition_column="condition",
        output_dir=Path("tests/.tmp/delimiter_out"),
        matrix_path=fixture_dir / "matrix_inconsistent_delimiter.tsv",
    )

    report, _ = run_validation(config)
    ids = {issue.rule_id for issue in report.issues}
    assert "INPUT_DELIM_001" in ids
    assert report.status == "fail"


def test_header_spaces_are_reported_as_minor_issue() -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    config = StudyConfig(
        metadata_path=fixture_dir / "metadata_valid.csv",
        metadata_sample_column="sample_id",
        condition_column="condition",
        output_dir=Path("tests/.tmp/header_space_out"),
        matrix_path=fixture_dir / "matrix_otu_header.tsv",
    )

    report, _ = run_validation(config)
    header_issues = [issue for issue in report.issues if issue.rule_id == "INPUT_HEADER_001"]
    assert header_issues
    assert all(issue.severity.value == "warning" for issue in header_issues)
