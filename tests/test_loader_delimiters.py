from pathlib import Path

from expready.loaders import infer_sample_columns, load_matrix, load_metadata
from expready.validators import validate_metadata_vs_matrix


FIXTURES = Path(__file__).parent / "fixtures"


def test_matrix_loader_handles_mixed_whitespace_delimiters() -> None:
    metadata_table = load_metadata(FIXTURES / "metadata_valid.csv")
    matrix_table = load_matrix(FIXTURES / "matrix_mixed_delimiter.txt")

    issues = validate_metadata_vs_matrix(metadata_table, matrix_table)
    assert any(issue.rule_id == "CROSS_OK_001" for issue in issues)


def test_matrix_loader_keeps_otu_id_header_with_tabs() -> None:
    metadata_table = load_metadata(FIXTURES / "metadata_valid.csv")
    matrix_table = load_matrix(FIXTURES / "matrix_otu_header.tsv")

    assert "#OTU ID" in matrix_table.columns
    issues = validate_metadata_vs_matrix(metadata_table, matrix_table)
    assert any(issue.rule_id == "CROSS_OK_001" for issue in issues)


def test_loader_handles_quoted_delimiters_in_csv() -> None:
    table = load_metadata(FIXTURES / "metadata_quoted.csv")
    assert table.columns == ["sample_id", "condition", "note"]
    assert table.rows[0]["note"] == "contains,comma"


def test_loader_strips_utf8_bom_from_header() -> None:
    table = load_metadata(FIXTURES / "metadata_bom.csv")
    assert "sample_id" in table.columns
    assert table.columns[0] == "sample_id"


def test_infer_sample_columns_skips_annotation_columns() -> None:
    matrix_table = load_matrix(FIXTURES / "matrix_annotation.tsv")
    assert infer_sample_columns(matrix_table) == ["S1", "S2"]
