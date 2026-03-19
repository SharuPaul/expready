from __future__ import annotations

from expready.loaders import infer_sample_columns
from expready.models import Issue, Table
from expready.rules import make_issue


def validate_metadata_vs_matrix(
    metadata_table: Table, matrix_table: Table, *, sample_id_column: str = "sample_id"
) -> list[Issue]:
    issues: list[Issue] = []
    if sample_id_column not in metadata_table.columns or not matrix_table.columns:
        return issues

    matrix_columns = infer_sample_columns(matrix_table)
    metadata_ids = set(metadata_table.column_values(sample_id_column))
    matrix_ids = set(matrix_columns)

    missing_from_matrix = sorted(metadata_ids - matrix_ids)
    if missing_from_matrix:
        issues.append(make_issue("CROSS_SAMPLE_001", detail=f"Missing in matrix: {', '.join(missing_from_matrix)}."))

    extra_in_matrix = sorted(matrix_ids - metadata_ids)
    if extra_in_matrix:
        issues.append(make_issue("CROSS_SAMPLE_002", detail=f"Not in metadata: {', '.join(extra_in_matrix)}."))

    if not missing_from_matrix and not extra_in_matrix:
        issues.append(make_issue("CROSS_OK_001"))

    return issues


def validate_metadata_vs_manifest(
    metadata_table: Table,
    manifest_table: Table,
    *,
    metadata_sample_column: str = "sample_id",
    manifest_sample_column: str = "sample_id",
) -> list[Issue]:
    issues: list[Issue] = []
    if metadata_sample_column not in metadata_table.columns:
        return issues
    if manifest_sample_column not in manifest_table.columns:
        issues.append(
            make_issue(
                "CROSS_MANIFEST_003",
                detail=f"Requested column '{manifest_sample_column}' not found. Available columns: {', '.join(manifest_table.columns)}.",
            )
        )
        return issues

    metadata_ids = set(metadata_table.column_values(metadata_sample_column))
    manifest_ids = set(manifest_table.column_values(manifest_sample_column))

    missing_from_manifest = sorted(metadata_ids - manifest_ids)
    if missing_from_manifest:
        issues.append(
            make_issue(
                "CROSS_MANIFEST_001",
                detail=f"Missing in manifest: {', '.join(missing_from_manifest)}.",
            )
        )

    extra_in_manifest = sorted(manifest_ids - metadata_ids)
    if extra_in_manifest:
        issues.append(
            make_issue(
                "CROSS_MANIFEST_002",
                detail=f"Not in metadata: {', '.join(extra_in_manifest)}.",
            )
        )

    if not missing_from_manifest and not extra_in_manifest:
        issues.append(make_issue("CROSS_OK_001"))

    return issues
