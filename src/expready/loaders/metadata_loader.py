from __future__ import annotations

import csv
from pathlib import Path

from expready.models import Table


def _separator_for_path(path: Path) -> str:
    return "\t" if path.suffix.lower() in {".tsv", ".txt"} else ","


def load_metadata(path: Path) -> Table:
    sep = _separator_for_path(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=sep)
        columns = [str(column).strip() for column in (reader.fieldnames or [])]
        rows: list[dict[str, str]] = []
        for row in reader:
            normalized: dict[str, str] = {}
            for column in columns:
                value = row.get(column, "")
                normalized[column] = str(value).strip() if value is not None else ""
            rows.append(normalized)
    return Table(columns=columns, rows=rows)
