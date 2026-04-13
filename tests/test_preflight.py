from pathlib import Path

from expready.models import StudyConfig
from expready.preflight import (
    collect_input_error_groups,
    format_grouped_input_errors,
    guess_manifest_path_column,
    resolve_column_name,
    resolve_condition_column,
    with_inferred_manifest_path_column,
)


FIXTURES = Path(__file__).parent / "fixtures"


def test_resolve_column_name_matches_case_and_token_variants() -> None:
    columns = ["Sample-ID", "Condition Group", "Batch"]
    assert resolve_column_name(columns, "sample_id") == "Sample-ID"
    assert resolve_column_name(columns, "condition_group") == "Condition Group"


def test_resolve_condition_column_falls_back_to_treatment() -> None:
    columns = ["sample_id", "treatment"]
    assert resolve_condition_column(columns, "condition") == "treatment"


def test_guess_manifest_path_column_finds_common_alias() -> None:
    columns = ["sample_id", "file_path", "lane"]
    assert guess_manifest_path_column(columns) == "file_path"


def test_with_inferred_manifest_path_column_updates_config_when_detected() -> None:
    config = StudyConfig(
        metadata_path=FIXTURES / "metadata_valid.csv",
        metadata_sample_column="sample_id",
        condition_column="condition",
        output_dir=Path("tests/.tmp/preflight_infer_path"),
        manifest_path=FIXTURES / "manifest_valid.tsv",
        check_manifest_paths=True,
    )
    updated = with_inferred_manifest_path_column(config)
    assert updated.manifest_path_column == "file_path"


def test_collect_input_error_groups_for_missing_columns() -> None:
    config = StudyConfig(
        metadata_path=FIXTURES / "metadata_valid.csv",
        metadata_sample_column="missing_id",
        condition_column="missing_condition",
        output_dir=Path("tests/.tmp/preflight_errors"),
    )
    groups = collect_input_error_groups(config)
    assert "metadata" in groups
    assert any("Sample-ID column 'missing_id' was not found" in line for line in groups["metadata"])
    assert any("Condition column 'missing_condition' was not found" in line for line in groups["metadata"])


def test_format_grouped_input_errors_includes_section_hints() -> None:
    grouped = {
        "metadata": ["Sample-ID column 'sample' was not found."],
        "manifest": ["Path column 'file_path' was not found."],
    }
    lines = format_grouped_input_errors(grouped)
    text = "\n".join(lines)
    assert "- metadata:" in text
    assert "Hint: Verify metadata headers" in text
    assert "- manifest:" in text
    assert "Hint: Verify manifest headers" in text
