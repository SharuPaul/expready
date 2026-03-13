from pathlib import Path

from expready.loaders import load_manifest, load_metadata
from expready.validators import validate_metadata_vs_manifest


FIXTURES = Path(__file__).parent / "fixtures"


def test_manifest_and_metadata_match() -> None:
    metadata_table = load_metadata(FIXTURES / "metadata_valid.csv")
    manifest_table = load_manifest(FIXTURES / "manifest_valid.tsv")
    issues = validate_metadata_vs_manifest(metadata_table, manifest_table)
    assert any(issue.rule_id == "CROSS_OK_001" for issue in issues)


def test_manifest_mismatch_raises_issues() -> None:
    metadata_table = load_metadata(FIXTURES / "metadata_valid.csv")
    manifest_table = load_manifest(FIXTURES / "manifest_mismatch.tsv")
    issues = validate_metadata_vs_manifest(metadata_table, manifest_table)
    ids = {issue.rule_id for issue in issues}
    assert "CROSS_MANIFEST_001" in ids
    assert "CROSS_MANIFEST_002" in ids
