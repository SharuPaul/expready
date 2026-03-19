from __future__ import annotations

from expready.models import Report

SEVERITY_LABELS = {
    "error": "Extreme",
    "warning": "Moderate",
    "info": "None",
}


def _format_column_summary(column_name: str, payload: dict[str, object]) -> str:
    levels = payload.get("levels", [])
    missing = int(payload.get("missing", 0))
    level_text = ", ".join(f"{entry['label']}={entry['count']}" for entry in levels) if levels else "no non-missing values"
    if missing:
        level_text = f"{level_text} (missing={missing})"
    return f"- {column_name}: {level_text}"


def render_console_summary(report: Report) -> str:
    counts = report.severity_counts
    lines = [
        f"Overall result: {report.status.upper()}",
        "Issue levels -> "
        f"{SEVERITY_LABELS['error']}: {counts['error']} | "
        f"{SEVERITY_LABELS['warning']}: {counts['warning']} | "
        f"{SEVERITY_LABELS['info']}: {counts['info']}",
    ]
    summary = report.metadata.get("study_summary")
    if isinstance(summary, dict):
        total = summary.get("total_samples")
        unique = summary.get("unique_sample_ids")
        lines.append(f"Samples: {total} (unique sample IDs: {unique})")
        condition_stats = summary.get("condition_stats", {})
        if isinstance(condition_stats, dict) and condition_stats:
            ratio = condition_stats.get("imbalance_ratio")
            if ratio is not None:
                lines.append(
                    "Condition balance: "
                    f"{condition_stats.get('min_group_size')} to {condition_stats.get('max_group_size')} "
                    f"(ratio={ratio:.2f})"
                )
        duplicates = summary.get("duplicate_sample_ids", [])
        if duplicates:
            lines.append(f"Duplicate sample ID values: {', '.join(duplicates)}")
        columns = summary.get("columns", {})
        if isinstance(columns, dict) and columns:
            lines.append("Study breakdown:")
            for column_name, payload in columns.items():
                if isinstance(payload, dict):
                    lines.append(_format_column_summary(column_name, payload))

    blocking = [issue for issue in report.sorted_issues() if issue.severity.value == "error"]
    if blocking:
        lines.append(f"Most important {SEVERITY_LABELS['error']} issues to fix:")
        for issue in blocking[:5]:
            lines.append(f"- {issue.rule_id}: {issue.title}")
    else:
        warnings = [issue for issue in report.sorted_issues() if issue.severity.value == "warning"]
        if warnings:
            lines.append(f"{SEVERITY_LABELS['warning']} issues to review:")
            for issue in warnings[:5]:
                lines.append(f"- {issue.rule_id}: {issue.title}")
        else:
            lines.append("No blocking issues found.")

    plan = report.action_plan()
    if plan:
        lines.append("Action plan:")
        for step in plan[:3]:
            lines.append(f"- {step['step']} [{step['priority']}]: {step['rule_id']} -> {step['suggested_fix']}")

    return "\n".join(lines)
