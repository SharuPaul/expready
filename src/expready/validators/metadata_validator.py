from __future__ import annotations

import re

from expready.models import Issue, Table
from expready.rules import make_issue
from expready.validators.schema_validator import validate_required_columns

_SAMPLE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def validate_metadata(table: Table, *, condition_column: str, sample_id_column: str = "sample_id") -> list[Issue]:
    issues: list[Issue] = []

    if table.empty:
        issues.append(make_issue("META_EMPTY_001"))
        return issues

    required_columns = [sample_id_column, condition_column]
    issues.extend(validate_required_columns(table, required_columns))
    if any(issue.rule_id == "META_REQ_001" for issue in issues):
        return issues

    sample_ids = table.column_values(sample_id_column)
    duplicates = sorted({value for value in sample_ids if sample_ids.count(value) > 1})
    if duplicates:
        issues.append(make_issue("META_DUP_001", detail=f"Duplicates: {', '.join(duplicates)}."))

    for column in required_columns:
        missing = sum(1 for value in table.column_values(column) if value.strip() == "")
        if missing:
            issues.append(make_issue("META_MISS_001", detail=f"Column '{column}' has {missing} missing value(s)."))

    suspicious_ids = sorted({value for value in sample_ids if not _SAMPLE_ID_PATTERN.match(value)})
    if suspicious_ids:
        issues.append(make_issue("META_FMT_001", detail=f"Suspicious IDs: {', '.join(suspicious_ids[:10])}."))

    if not any(issue.severity.value == "error" for issue in issues):
        issues.append(make_issue("META_OK_001"))
    return issues
