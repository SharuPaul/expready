from pathlib import Path

from expready.loaders import load_metadata
from expready.validators import validate_design


FIXTURES = Path(__file__).parent / "fixtures"


def test_confounded_batch_condition_is_error() -> None:
    table = load_metadata(FIXTURES / "metadata_confounded.csv")
    issues = validate_design(table, condition_column="condition", batch_column="batch")
    ids = {issue.rule_id for issue in issues}
    assert "DESIGN_CONF_001" in ids


def test_low_replicate_group_is_warning() -> None:
    table = load_metadata(FIXTURES / "metadata_low_repl.csv")
    issues = validate_design(table, condition_column="condition", batch_column="batch")
    ids = {issue.rule_id for issue in issues}
    assert "DESIGN_REPL_001" in ids
