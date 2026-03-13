from pathlib import Path

from expready.models import StudyConfig
from expready.preflight import run_preflight


def test_study_summary_contains_design_breakdown() -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    config = StudyConfig(
        metadata_path=fixture_dir / "metadata_valid.csv",
        condition_column="condition",
        output_dir=Path("tests/.tmp/summary_out"),
        batch_column="batch",
    )

    report, _ = run_preflight(config)
    summary = report.metadata["study_summary"]

    assert summary["total_samples"] == 4
    assert summary["unique_sample_ids"] == 4
    assert "condition" in summary["columns"]
    assert "batch" in summary["columns"]
    assert {"label": "Control", "count": 2} in summary["columns"]["condition"]["levels"]
    assert {"label": "Treated", "count": 2} in summary["columns"]["condition"]["levels"]
