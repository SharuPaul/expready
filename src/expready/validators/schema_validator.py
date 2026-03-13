from __future__ import annotations

from expready.models import Issue, Table
from expready.rules import make_issue


def validate_required_columns(table: Table, required_columns: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    missing = [column for column in required_columns if column not in table.columns]
    for column in missing:
        issues.append(make_issue("META_REQ_001", detail=f"Missing column: '{column}'."))
    return issues
