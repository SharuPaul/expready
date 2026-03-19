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
