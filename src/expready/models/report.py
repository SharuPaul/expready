from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from expready.models.issue import Issue, Severity


@dataclass
class Report:
    status: str = "pass"
    issues: list[Issue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_issue(self, issue: Issue) -> None:
        self.issues.append(issue)
        if issue.severity == Severity.ERROR:
            self.status = "fail"

    @property
    def severity_counts(self) -> dict[str, int]:
        counts = {Severity.ERROR.value: 0, Severity.WARNING.value: 0, Severity.INFO.value: 0}
        for issue in self.issues:
            counts[issue.severity.value] += 1
        return counts

    def sorted_issues(self) -> list[Issue]:
        order = {Severity.ERROR.value: 0, Severity.WARNING.value: 1, Severity.INFO.value: 2}
        return sorted(self.issues, key=lambda i: (order[i.severity.value], i.rule_id, i.title.lower()))

    @property
    def section_counts(self) -> dict[str, dict[str, int]]:
        counts: dict[str, dict[str, int]] = {}
        for issue in self.issues:
            section = issue.section or "general"
            if section not in counts:
                counts[section] = {"error": 0, "warning": 0, "info": 0, "total": 0}
            counts[section][issue.severity.value] += 1
            counts[section]["total"] += 1
        return counts

    def action_plan(self) -> list[dict[str, str]]:
        steps: list[dict[str, str]] = []
        ranked = [i for i in self.sorted_issues() if i.severity.value in {"error", "warning"}]
        for i, issue in enumerate(ranked, start=1):
            priority = "high" if issue.severity.value == "error" else "medium"
            steps.append(
                {
                    "step": f"Step {i}",
                    "priority": priority,
                    "severity": issue.severity.value,
                    "rule_id": issue.rule_id,
                    "title": issue.title,
                    "suggested_fix": issue.suggested_fix,
                }
            )
        return steps

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "severity_counts": self.severity_counts,
            "section_counts": self.section_counts,
            "metadata": self.metadata,
            "action_plan": self.action_plan(),
            "issues": [issue.to_dict() for issue in self.sorted_issues()],
        }
