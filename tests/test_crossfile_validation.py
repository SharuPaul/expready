from pathlib import Path

from expready.loaders import load_matrix, load_metadata
from expready.models import StudyConfig
from expready.models import Table
from expready.validation import run_validation
from expready.validators import validate_metadata_vs_matrix
from expready.validators import validate_metadata_vs_manifest
from expready.validators import validate_manifest_paths


FIXTURES = Path(__file__).parent / "fixtures"


def test_matrix_and_metadata_match() -> None:
    metadata_df = load_metadata(FIXTURES / "metadata_valid.csv")
    matrix_df = load_matrix(FIXTURES / "matrix_valid.tsv")
    issues = validate_metadata_vs_matrix(metadata_df, matrix_df)
    assert any(issue.rule_id == "CROSS_OK_001" for issue in issues)


def test_matrix_mismatch_raises_issues() -> None:
    metadata_df = load_metadata(FIXTURES / "metadata_valid.csv")
    matrix_df = load_matrix(FIXTURES / "matrix_mismatch.tsv")
    issues = validate_metadata_vs_matrix(metadata_df, matrix_df)
    ids = {issue.rule_id for issue in issues}
    assert "CROSS_SAMPLE_001" in ids
    assert "CROSS_SAMPLE_002" in ids


def test_manifest_missing_sample_column_is_error() -> None:
    metadata_df = load_metadata(FIXTURES / "metadata_valid.csv")
    manifest_df = Table(
        columns=["rownames", "batch"],
        rows=[
            {"rownames": "S1", "batch": "B1"},
            {"rownames": "S2", "batch": "B1"},
        ],
    )
    issues = validate_metadata_vs_manifest(metadata_df, manifest_df, manifest_sample_column="sample_id")
    ids = {issue.rule_id for issue in issues}
    assert "CROSS_MANIFEST_003" in ids


def test_run_validation_resolves_default_sample_id_variants() -> None:
    config = StudyConfig(
        metadata_path=FIXTURES / "metadata_sample_dash_case.csv",
        metadata_sample_column="sample_id",
        condition_column="condition",
        output_dir=Path("tests/.tmp/column_resolution_out"),
        manifest_path=FIXTURES / "manifest_sample_upper_underscore.tsv",
        manifest_sample_column="sample_id",
    )

    report, _ = run_validation(config)
    ids = {issue.rule_id for issue in report.issues}
    assert "META_REQ_001" not in ids
    assert "CROSS_MANIFEST_003" not in ids
    assert "CROSS_OK_001" in ids


def test_manifest_path_checks_report_missing_and_duplicates() -> None:
    manifest_df = Table(
        columns=["sample_id", "file_path"],
        rows=[
            {"sample_id": "S1", "file_path": "reads/S1.fastq.gz"},
            {"sample_id": "S2", "file_path": "reads/S1.fastq.gz"},
            {"sample_id": "S3", "file_path": ""},
        ],
    )
    issues = validate_manifest_paths(manifest_df, manifest_path_column="file_path", check_exists=False)
    ids = {issue.rule_id for issue in issues}
    assert "CROSS_PATH_002" in ids
    assert "CROSS_PATH_003" in ids


def test_manifest_path_checks_file_existence() -> None:
    manifest_df = Table(
        columns=["sample_id", "file_path"],
        rows=[
            {"sample_id": "S1", "file_path": "definitely_missing_file.fastq.gz"},
        ],
    )
    issues = validate_manifest_paths(manifest_df, manifest_path_column="file_path", check_exists=True, manifest_base_dir=FIXTURES)
    ids = {issue.rule_id for issue in issues}
    assert "CROSS_PATH_004" in ids
