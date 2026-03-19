from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Optional

from expready.models import Table


_WHITESPACE_SPLIT = re.compile(r"\s+")
_DELIMITER_CANDIDATES = [",", "\t", ";", "|"]


def _split_fields(line: str, mode: str) -> list[str]:
    if mode == "whitespace":
        return _WHITESPACE_SPLIT.split(line.strip())
    return next(csv.reader([line], delimiter=mode))


def _score_mode(lines: list[str], mode: str) -> tuple[int, int]:
    counts: list[int] = []
    for line in lines:
        fields = _split_fields(line, mode)
        counts.append(len(fields))

    if not counts:
        return (0, 0)

    max_count = max(counts)
    consistent = sum(1 for count in counts if count == max_count)
    if max_count <= 1:
        return (0, 0)
    return (max_count, consistent)


def _detect_mode(lines: list[str]) -> str:
    probe = lines[:30]
    best_mode = ","
    best_score = (0, 0)

    for mode in _DELIMITER_CANDIDATES + ["whitespace"]:
        score = _score_mode(probe, mode)
        if score > best_score:
            best_mode = mode
            best_score = score
    return best_mode


def load_table(path: Path) -> Table:
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    lines = [line for line in raw_lines if line.strip() != ""]
    if not lines:
        return Table(columns=[], rows=[])

    mode = _detect_mode(lines)
    header = _split_fields(lines[0], mode)
    columns = [str(column).strip() for column in header]

    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        fields = _split_fields(line, mode)
        normalized: dict[str, str] = {}
        for index, column in enumerate(columns):
            value = fields[index] if index < len(fields) else ""
            normalized[column] = str(value).strip() if value is not None else ""
        rows.append(normalized)

    return Table(columns=columns, rows=rows)


def inspect_delimiter_issues(path: Path) -> Optional[str]:
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    lines = [line for line in raw_lines if line.strip() != ""]
    if len(lines) < 2:
        return None

    mode = _detect_mode(lines)
    header_fields = _split_fields(lines[0], mode)
    expected = len(header_fields)
    if expected <= 1:
        return None

    mismatches: list[tuple[int, int]] = []
    for idx, line in enumerate(lines[1:], start=2):
        observed = len(_split_fields(line, mode))
        if observed != expected:
            mismatches.append((idx, observed))

    if not mismatches:
        return None

    preview = ", ".join(f"line {line_no}: {count} fields" for line_no, count in mismatches[:3])
    mode_label = "whitespace" if mode == "whitespace" else repr(mode)
    return (
        f"Detected delimiter mode {mode_label} with {expected} header fields, but "
        f"{len(mismatches)} row(s) have a different field count ({preview}). "
        "This often indicates mixed or inconsistent delimiters."
    )
