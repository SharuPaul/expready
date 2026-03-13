from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Issue:
    rule_id: str
    severity: Severity
    title: str
    description: str
    rationale: str
    suggested_fix: str
    section: str = "general"

    def to_dict(self) -> dict[str, str]:
        payload = asdict(self)
        payload["severity"] = self.severity.value
        return payload
