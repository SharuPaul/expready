from pathlib import Path

from expready.models import StudyConfig
from expready.validation import run_validation


def test_study_summary_contains_design_breakdown() -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    config = StudyConfig(
        metadata_path=fixture_dir / "metadata_valid.csv",
        metadata_sample_column="sample_id",
        condition_column="condition",
        output_dir=Path("tests/.tmp/summary_out"),
        batch_column="batch",
    )

    report, _ = run_validation(config)
    summary = report.metadata["study_summary"]

    assert summary["total_samples"] == 4
    assert summary["unique_sample_ids"] == 4
    assert "condition" in summary["columns"]
    assert "batch" in summary["columns"]
    assert {"label": "Control", "count": 2} in summary["columns"]["condition"]["levels"]
    assert {"label": "Treated", "count": 2} in summary["columns"]["condition"]["levels"]


def test_condition_column_is_case_insensitive() -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    config = StudyConfig(
        metadata_path=fixture_dir / "metadata_condition_titlecase.csv",
        metadata_sample_column="sample_id",
        condition_column="condition",
        output_dir=Path("tests/.tmp/summary_out_case"),
        batch_column="batch",
    )

    report, _ = run_validation(config)
    ids = {issue.rule_id for issue in report.issues}

    assert report.metadata["condition_column"] == "Condition"
    assert "META_REQ_001" not in ids
    assert "DESIGN_REQ_001" not in ids


def test_default_condition_falls_back_to_treatment() -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    config = StudyConfig(
        metadata_path=fixture_dir / "metadata_treatment.csv",
        metadata_sample_column="sample_id",
        condition_column="condition",
        output_dir=Path("tests/.tmp/summary_out_treatment"),
        batch_column="batch",
    )

    report, _ = run_validation(config)
    ids = {issue.rule_id for issue in report.issues}

    assert report.metadata["condition_column"] == "treatment"
    assert "META_REQ_001" not in ids
    assert "DESIGN_REQ_001" not in ids
