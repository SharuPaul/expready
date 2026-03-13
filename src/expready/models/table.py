from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Table:
    columns: list[str]
    rows: list[dict[str, str]]

    @property
    def empty(self) -> bool:
        return len(self.rows) == 0

    def column_values(self, name: str) -> list[str]:
        return [row.get(name, "") for row in self.rows]
