from __future__ import annotations

import re
from typing import Optional

from expready.loaders import inspect_delimiter_issues, load_manifest, load_metadata
from expready.models import StudyConfig

_GROUP_ORDER = ["metadata", "matrix", "manifest"]
_GROUP_HINTS = {
    "metadata": "Verify metadata headers and update options like --metadata-id/--condition/--batch/--pair/--covars.",
    "matrix": "Fix table delimiters/structure and ensure the matrix file uses a consistent separator.",
    "manifest": "Verify manifest headers and update options like --manifest-id/--manifest-path/--check-paths.",
}


def _normalize_column_token(name: str) -> str:
    return re.sub(r"[\s\-_]+", "_", name.strip().lower())


def resolve_column_name(columns: list[str], requested: str) -> str:
    if requested in columns:
        return requested

    requested_lower = requested.lower()
    for column in columns:
        if column.lower() == requested_lower:
            return column

    requested_token = _normalize_column_token(requested)
    for column in columns:
        if _normalize_column_token(column) == requested_token:
            return column

    return requested


def resolve_condition_column(columns: list[str], requested: str) -> str:
    resolved = resolve_column_name(columns, requested)
    if resolved in columns:
        return resolved
    if _normalize_column_token(requested) == "condition":
        fallback = resolve_column_name(columns, "treatment")
        if fallback in columns:
            return fallback
    return requested


def guess_manifest_path_column(columns: list[str]) -> Optional[str]:
    common = ["file_path", "filepath", "path", "file", "fastq_path"]
    for candidate in common:
        resolved = resolve_column_name(columns, candidate)
        if resolved in columns:
            return resolved
    return None


def with_inferred_manifest_path_column(config: StudyConfig) -> StudyConfig:
    if not config.manifest_path or not config.check_manifest_paths or config.manifest_path_column:
        return config

    manifest_table = load_manifest(config.manifest_path)
    guessed_path_column = guess_manifest_path_column(manifest_table.columns)
    if not guessed_path_column:
        return config

    return StudyConfig(
        metadata_path=config.metadata_path,
        metadata_sample_column=config.metadata_sample_column,
        condition_column=config.condition_column,
        output_dir=config.output_dir,
        matrix_path=config.matrix_path,
        manifest_path=config.manifest_path,
        manifest_sample_column=config.manifest_sample_column,
        manifest_path_column=guessed_path_column,
        check_manifest_paths=config.check_manifest_paths,
        batch_column=config.batch_column,
        pair_column=config.pair_column,
        covariates=config.covariates,
        contrast=config.contrast,
    )


def collect_input_error_groups(config: StudyConfig) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}

    def add(group: str, message: str) -> None:
        grouped.setdefault(group, []).append(message)

    for label, path in [("metadata", config.metadata_path), ("matrix", config.matrix_path), ("manifest", config.manifest_path)]:
        if path is None:
            continue
        detail = inspect_delimiter_issues(path)
        if detail:
            add(label, f"Inconsistent delimiter structure detected. {detail}")

    if config.metadata_path:
        metadata_table = load_metadata(config.metadata_path)
        resolved_sample = resolve_column_name(metadata_table.columns, config.metadata_sample_column)
        if resolved_sample not in metadata_table.columns:
            add(
                "metadata",
                f"Sample-ID column '{config.metadata_sample_column}' was not found. "
                f"Available columns: {', '.join(metadata_table.columns)}.",
            )

        resolved_condition = resolve_condition_column(metadata_table.columns, config.condition_column)
        if resolved_condition not in metadata_table.columns:
            add(
                "metadata",
                f"Condition column '{config.condition_column}' was not found "
                f"(default fallback 'treatment' also not found). Available columns: {', '.join(metadata_table.columns)}.",
            )

        requested = [config.batch_column, config.pair_column, *config.covariates]
        for column in [value for value in requested if value]:
            resolved = resolve_column_name(metadata_table.columns, column)
            if resolved not in metadata_table.columns:
                add(
                    "metadata",
                    f"Requested column '{column}' was not found. "
                    f"Available columns: {', '.join(metadata_table.columns)}.",
                )

    if config.manifest_path:
        manifest_table = load_manifest(config.manifest_path)
        resolved_manifest_sample = resolve_column_name(manifest_table.columns, config.manifest_sample_column)
        if resolved_manifest_sample not in manifest_table.columns:
            add(
                "manifest",
                f"Sample-ID column '{config.manifest_sample_column}' was not found. "
                f"Available columns: {', '.join(manifest_table.columns)}.",
            )

        if config.manifest_path_column:
            resolved_path = resolve_column_name(manifest_table.columns, config.manifest_path_column)
            if resolved_path not in manifest_table.columns:
                add(
                    "manifest",
                    f"Path column '{config.manifest_path_column}' was not found. "
                    f"Available columns: {', '.join(manifest_table.columns)}.",
                )
        elif config.check_manifest_paths:
            guessed = guess_manifest_path_column(manifest_table.columns)
            if guessed is None:
                add(
                    "manifest",
                    "--check-paths requires a manifest path column. "
                    "Provide --manifest-path or include one of: file_path, filepath, path, file, fastq_path."
                )

    return grouped


def collect_input_errors(config: StudyConfig) -> list[str]:
    grouped = collect_input_error_groups(config)
    flattened: list[str] = []
    for group in _GROUP_ORDER:
        for message in grouped.get(group, []):
            flattened.append(f"{group}: {message}")
    for group, messages in grouped.items():
        if group in _GROUP_ORDER:
            continue
        for message in messages:
            flattened.append(f"{group}: {message}")
    return flattened


def format_grouped_input_errors(grouped: dict[str, list[str]]) -> list[str]:
    lines: list[str] = []
    ordered_groups = [name for name in _GROUP_ORDER if name in grouped] + [
        name for name in grouped if name not in _GROUP_ORDER
    ]
    for group in ordered_groups:
        issues = grouped.get(group, [])
        if not issues:
            continue
        lines.append(f"- {group}:")
        for issue in issues:
            lines.append(f"  - {issue}")
        hint = _GROUP_HINTS.get(group)
        if hint:
            lines.append(f"  Hint: {hint}")
    return lines
