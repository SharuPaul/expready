from __future__ import annotations

import csv
from pathlib import Path

from expready.models import Table


def _separator_for_path(path: Path) -> str:
    return "\t" if path.suffix.lower() in {".tsv", ".txt"} else ","


def load_matrix(path: Path) -> Table:
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


def _is_number(text: str) -> bool:
    if text == "":
        return False
    try:
        float(text)
        return True
    except ValueError:
        return False


def infer_sample_columns(matrix_table: Table, *, max_rows: int = 50, threshold: float = 0.8) -> list[str]:
    """Infer sample columns by numeric density in the matrix values."""
    if not matrix_table.columns:
        return []
    probe_rows = matrix_table.rows[:max_rows]
    if not probe_rows:
        annotation_like = {"gene_id", "gene", "feature_id", "feature", "id", "gene_name", "symbol", "name"}
        first_cols = matrix_table.columns[:2]
        skip = 0
        for col in first_cols:
            normalized = col.strip().lower()
            if normalized in annotation_like:
                skip += 1
        return matrix_table.columns[skip:] if skip else matrix_table.columns[1:]

    sample_columns: list[str] = []
    for column in matrix_table.columns:
        values = [row.get(column, "") for row in probe_rows]
        non_empty = [value for value in values if value != ""]
        if not non_empty:
            continue
        numeric = sum(1 for value in non_empty if _is_number(value))
        if (numeric / len(non_empty)) >= threshold:
            sample_columns.append(column)
    return sample_columns
