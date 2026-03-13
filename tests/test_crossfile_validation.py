from pathlib import Path

from expready.loaders import load_matrix, load_metadata
from expready.models import Table
from expready.validators import validate_metadata_vs_matrix
from expready.validators import validate_metadata_vs_manifest


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
