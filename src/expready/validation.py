from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
from typing import Optional

from expready.loaders import infer_sample_columns, inspect_delimiter_issues, load_manifest, load_matrix, load_metadata
from expready.models import Report, StudyConfig, Table
from expready.rules import make_issue
from expready.validators import (
    validate_design,
    validate_metadata,
    validate_metadata_vs_matrix,
    validate_metadata_vs_manifest,
)


_REPLICATE_PATTERN = re.compile(r"^R\d+$", re.IGNORECASE)


def _parse_sample_id(sample_id: str, *, sample_id_column: str) -> dict[str, str]:
    parts = sample_id.split("_")
    condition = parts[0] if parts else sample_id
    replicate = ""
    dissection = ""

    for token in reversed(parts):
        if _REPLICATE_PATTERN.match(token):
            replicate = token
            break

    if replicate and len(parts) >= 2:
        rep_index = len(parts) - 1 - parts[::-1].index(replicate)
        if rep_index - 1 >= 0:
            dissection = parts[rep_index - 1]
    elif len(parts) >= 2:
        dissection = parts[1]

    return {
        sample_id_column: sample_id,
        "condition": condition,
        "dissection": dissection,
        "replicate": replicate,
    }


def build_metadata_from_matrix(matrix_table: Table, *, sample_id_column: str = "sample_id") -> Table:
    sample_columns = infer_sample_columns(matrix_table)
    rows = [_parse_sample_id(sample_id, sample_id_column=sample_id_column) for sample_id in sample_columns]
    return Table(columns=[sample_id_column, "condition", "dissection", "replicate"], rows=rows)


def build_study_summary(metadata_table: Table, config: StudyConfig) -> dict[str, object]:
    sample_col = config.metadata_sample_column
    sample_ids = metadata_table.column_values(sample_col) if sample_col in metadata_table.columns else []
    duplicate_ids = sorted({sid for sid in sample_ids if sid and sample_ids.count(sid) > 1})

    summary_columns: list[str] = []
    for column in [config.condition_column, config.batch_column, config.pair_column, *config.covariates]:
        if column and column in metadata_table.columns and column not in summary_columns:
            summary_columns.append(column)

    columns_summary: dict[str, dict[str, object]] = {}
    for column in summary_columns:
        values = metadata_table.column_values(column)
        missing = sum(1 for value in values if value == "")
        counts = Counter(value for value in values if value != "")
        levels = [{"label": label, "count": count} for label, count in sorted(counts.items())]
        columns_summary[column] = {
            "missing": missing,
            "missing_fraction": (missing / len(values)) if values else 0.0,
            "unique_levels": len(counts),
            "levels": levels,
        }

    condition_stats: dict[str, object] = {}
    if config.condition_column in columns_summary:
        condition_levels = columns_summary[config.condition_column].get("levels", [])
        counts = [int(entry["count"]) for entry in condition_levels if isinstance(entry, dict) and "count" in entry]
        if counts:
            min_count = min(counts)
            max_count = max(counts)
            condition_stats = {
                "group_count": len(counts),
                "min_group_size": min_count,
                "max_group_size": max_count,
                "imbalance_ratio": (max_count / min_count) if min_count else None,
            }

    return {
        "total_samples": len(metadata_table.rows),
        "unique_sample_ids": len({sid for sid in sample_ids if sid != ""}),
        "duplicate_sample_ids": duplicate_ids,
        "columns": columns_summary,
        "condition_stats": condition_stats,
    }


def run_validation(config: StudyConfig) -> tuple[Report, Table]:
    report = Report(
        metadata={
            "metadata_path": str(config.metadata_path) if config.metadata_path else None,
            "matrix_path": str(config.matrix_path) if config.matrix_path else None,
            "manifest_path": str(config.manifest_path) if config.manifest_path else None,
            "condition_column": config.condition_column,
        }
    )

    input_paths: list[tuple[str, Optional[Path]]] = [
        ("metadata", config.metadata_path),
        ("matrix", config.matrix_path),
        ("manifest", config.manifest_path),
    ]
    for label, path in input_paths:
        if path is None:
            continue
        detail = inspect_delimiter_issues(path)
        if detail:
            report.add_issue(make_issue("INPUT_DELIM_001", detail=f"{label} file '{path}': {detail}"))

    matrix_table = load_matrix(config.matrix_path) if config.matrix_path else None
    manifest_table = load_manifest(config.manifest_path) if config.manifest_path else None
    if config.metadata_path:
        metadata_table = load_metadata(config.metadata_path)
    elif matrix_table is not None:
        metadata_table = build_metadata_from_matrix(matrix_table, sample_id_column=config.metadata_sample_column)
        report.metadata["metadata_source"] = "auto_from_matrix"
    else:
        metadata_table = Table(columns=[config.metadata_sample_column, config.condition_column], rows=[])
        report.metadata["metadata_source"] = "missing"

    header_checks: list[tuple[str, Optional[Table]]] = [
        ("metadata", metadata_table if config.metadata_path else None),
        ("matrix", matrix_table),
        ("manifest", manifest_table),
    ]
    for label, table in header_checks:
        if table is None:
            continue
        spaced = [column for column in table.columns if " " in column]
        if spaced:
            preview = ", ".join(spaced[:5])
            report.add_issue(
                make_issue(
                    "INPUT_HEADER_001",
                    detail=f"{label} headers with spaces: {preview}.",
                )
            )

    report.metadata["study_summary"] = build_study_summary(metadata_table, config)

    for issue in validate_metadata(
        metadata_table,
        condition_column=config.condition_column,
        sample_id_column=config.metadata_sample_column,
    ):
        report.add_issue(issue)

    for issue in validate_design(
        metadata_table,
        condition_column=config.condition_column,
        batch_column=config.batch_column,
        pair_column=config.pair_column,
        covariates=config.covariates,
        contrast=config.contrast,
    ):
        report.add_issue(issue)

    if matrix_table is not None:
        for issue in validate_metadata_vs_matrix(
            metadata_table,
            matrix_table,
            sample_id_column=config.metadata_sample_column,
        ):
            report.add_issue(issue)

    if manifest_table is not None:
        for issue in validate_metadata_vs_manifest(
            metadata_table,
            manifest_table,
            metadata_sample_column=config.metadata_sample_column,
            manifest_sample_column=config.manifest_sample_column,
        ):
            report.add_issue(issue)

    return report, metadata_table


def ensure_output_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
