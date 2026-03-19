from __future__ import annotations

from collections import Counter, defaultdict
from typing import Optional

from expready.models import Issue, Table
from expready.rules import make_issue


def _missing_requested_columns(
    table: Table,
    *,
    condition_column: str,
    batch_column: Optional[str],
    pair_column: Optional[str],
    covariates: list[str],
) -> list[Issue]:
    requested = [condition_column]
    if batch_column:
        requested.append(batch_column)
    if pair_column:
        requested.append(pair_column)
    requested.extend(covariates)

    issues: list[Issue] = []
    for column in sorted(set(requested)):
        if column not in table.columns:
            issues.append(make_issue("DESIGN_REQ_001", detail=f"Missing column: '{column}'."))
    return issues


def _singleton_levels(values: list[str]) -> list[str]:
    counts = Counter(values)
    return sorted([level for level, count in counts.items() if level != "" and count == 1])


def _validate_contrast(contrast: str, groups: set[str]) -> Optional[Issue]:
    normalized = contrast.strip()
    if "_vs_" not in normalized:
        return make_issue("DESIGN_CONTRAST_001", detail=f"Expected format '<A>_vs_<B>', got '{contrast}'.")
    left, right = normalized.split("_vs_", maxsplit=1)
    missing = [group for group in (left.strip(), right.strip()) if group.strip() not in groups]
    if missing:
        return make_issue("DESIGN_CONTRAST_001", detail=f"Missing levels in condition: {', '.join(missing)}.")
    return None


def validate_design(
    table: Table,
    *,
    condition_column: str,
    batch_column: Optional[str] = None,
    pair_column: Optional[str] = None,
    covariates: Optional[list[str]] = None,
    contrast: Optional[str] = None,
) -> list[Issue]:
    issues: list[Issue] = []
    covariates = covariates or []

    issues.extend(
        _missing_requested_columns(
            table,
            condition_column=condition_column,
            batch_column=batch_column,
            pair_column=pair_column,
            covariates=covariates,
        )
    )
    if issues:
        return issues

    condition_values = [value for value in table.column_values(condition_column) if value != ""]
    group_counts = Counter(condition_values)
    groups = set(group_counts.keys())

    if len(groups) < 2:
        issues.append(make_issue("DESIGN_GROUP_001"))
        return issues

    low_repl = sorted([group for group, count in group_counts.items() if count < 2])
    if low_repl:
        issues.append(make_issue("DESIGN_REPL_001", detail=f"Low-replicate groups: {', '.join(low_repl)}."))

    if group_counts:
        min_size = min(group_counts.values())
        max_size = max(group_counts.values())
        if min_size > 0 and (max_size / min_size) >= 3.0:
            issues.append(
                make_issue(
                    "DESIGN_IMBAL_001",
                    detail=f"Group size range is {min_size} to {max_size}.",
                )
            )

    singleton_factors: list[str] = []
    for column in [condition_column] + ([batch_column] if batch_column else []) + covariates:
        singletons = _singleton_levels(table.column_values(column))
        if singletons:
            singleton_factors.append(f"{column}: {', '.join(singletons)}")
    if singleton_factors:
        issues.append(make_issue("DESIGN_SINGLE_001", detail="; ".join(singleton_factors) + "."))

    if batch_column:
        condition_to_batch: dict[str, set[str]] = defaultdict(set)
        batch_to_condition: dict[str, set[str]] = defaultdict(set)
        for row in table.rows:
            cond = row.get(condition_column, "")
            batch = row.get(batch_column, "")
            if cond and batch:
                condition_to_batch[cond].add(batch)
                batch_to_condition[batch].add(cond)
        if condition_to_batch and batch_to_condition:
            cond_single_batch = all(len(batches) == 1 for batches in condition_to_batch.values())
            batch_single_cond = all(len(conds) == 1 for conds in batch_to_condition.values())
            if cond_single_batch and batch_single_cond and len(condition_to_batch) > 1 and len(batch_to_condition) > 1:
                issues.append(make_issue("DESIGN_CONF_001"))

    if pair_column:
        pair_values = [value for value in table.column_values(pair_column) if value != ""]
        pair_counts = Counter(pair_values)
        missing_pair = sum(1 for value in table.column_values(pair_column) if value == "")
        singleton_pairs = sorted([pair for pair, count in pair_counts.items() if count < 2])
        if missing_pair or singleton_pairs:
            detail_parts = []
            if missing_pair:
                detail_parts.append(f"Missing pair IDs: {missing_pair}")
            if singleton_pairs:
                detail_parts.append(f"Singleton pairs: {', '.join(singleton_pairs)}")
            issues.append(make_issue("PAIR_META_001", detail=". ".join(detail_parts) + "."))

    if contrast:
        contrast_issue = _validate_contrast(contrast, groups)
        if contrast_issue:
            issues.append(contrast_issue)

    # Approximate fixed-effect complexity for early hazard detection.
    n_samples = len(table.rows)
    param_count = 1 + (len(groups) - 1)
    for column in [batch_column] + covariates:
        if column:
            levels = {value for value in table.column_values(column) if value != ""}
            if levels:
                param_count += max(0, len(levels) - 1)
    if pair_column:
        pair_levels = {value for value in table.column_values(pair_column) if value != ""}
        if pair_levels:
            param_count += max(0, len(pair_levels) - 1)
    if param_count >= n_samples:
        issues.append(
            make_issue(
                "DESIGN_SIZE_001",
                detail=f"Estimated parameter count {param_count} with {n_samples} samples.",
            )
        )

    if not any(issue.section == "design" and issue.severity.value in {"error", "warning"} for issue in issues):
        issues.append(make_issue("DESIGN_OK_001"))

    return issues
