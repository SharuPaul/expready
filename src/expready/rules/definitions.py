from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from expready.models import Issue, Severity


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    severity: Severity
    title: str
    description: str
    rationale: str
    suggested_fix: str
    section: str


RULES: dict[str, RuleDefinition] = {
    "META_EMPTY_001": RuleDefinition(
        rule_id="META_EMPTY_001",
        severity=Severity.ERROR,
        title="Metadata file is empty",
        description="The metadata table has no rows.",
        rationale="A study design cannot be checked without at least one sample row.",
        suggested_fix="Provide a metadata file with one row per sample.",
        section="metadata",
    ),
    "META_REQ_001": RuleDefinition(
        rule_id="META_REQ_001",
        severity=Severity.ERROR,
        title="Required metadata column is missing",
        description="A required column is absent from the metadata table.",
        rationale="Missing key columns prevent design and consistency checks.",
        suggested_fix="Add required columns and ensure names match exactly.",
        section="metadata",
    ),
    "META_DUP_001": RuleDefinition(
        rule_id="META_DUP_001",
        severity=Severity.ERROR,
        title="Duplicate sample IDs",
        description="At least one sample_id appears more than once.",
        rationale="Duplicate IDs cause ambiguous mapping between files and model rows.",
        suggested_fix="Make every sample_id unique in metadata and related inputs.",
        section="metadata",
    ),
    "META_MISS_001": RuleDefinition(
        rule_id="META_MISS_001",
        severity=Severity.ERROR,
        title="Missing value in key column",
        description="A key metadata column contains missing values.",
        rationale="Missing key fields break grouping and contrast definitions.",
        suggested_fix="Fill missing values for key columns or remove incomplete samples.",
        section="metadata",
    ),
    "META_FMT_001": RuleDefinition(
        rule_id="META_FMT_001",
        severity=Severity.WARNING,
        title="Suspicious sample ID format",
        description="Sample IDs contain leading/trailing spaces or unusual characters.",
        rationale="Inconsistent identifiers can cause silent cross-file mismatches.",
        suggested_fix="Use stable sample IDs with letters, numbers, underscore, hyphen, or dot.",
        section="metadata",
    ),
    "CROSS_SAMPLE_001": RuleDefinition(
        rule_id="CROSS_SAMPLE_001",
        severity=Severity.ERROR,
        title="Metadata sample missing from matrix",
        description="One or more metadata sample IDs are not found in feature matrix columns.",
        rationale="Sample misalignment invalidates downstream models and interpretations.",
        suggested_fix="Align sample IDs exactly between metadata and feature matrix headers.",
        section="cross_file",
    ),
    "CROSS_SAMPLE_002": RuleDefinition(
        rule_id="CROSS_SAMPLE_002",
        severity=Severity.WARNING,
        title="Extra matrix sample not in metadata",
        description="Feature matrix contains sample columns not represented in metadata.",
        rationale="Extra columns indicate stale, duplicated, or wrong samples.",
        suggested_fix="Remove unmatched matrix columns or add corresponding metadata rows.",
        section="cross_file",
    ),
    "META_OK_001": RuleDefinition(
        rule_id="META_OK_001",
        severity=Severity.INFO,
        title="Metadata checks passed",
        description="No blocking metadata schema issues were detected.",
        rationale="Clean metadata supports reliable validation diagnostics.",
        suggested_fix="No action required.",
        section="metadata",
    ),
    "CROSS_OK_001": RuleDefinition(
        rule_id="CROSS_OK_001",
        severity=Severity.INFO,
        title="Cross-file sample IDs match",
        description="Metadata sample IDs and linked input columns are consistent.",
        rationale="Consistent sample identifiers reduce downstream analysis risk.",
        suggested_fix="No action required.",
        section="cross_file",
    ),
    "CROSS_MANIFEST_001": RuleDefinition(
        rule_id="CROSS_MANIFEST_001",
        severity=Severity.ERROR,
        title="Metadata sample missing from manifest",
        description="One or more metadata sample IDs are not found in manifest entries.",
        rationale="Downstream workflows cannot locate expected sample files.",
        suggested_fix="Align sample IDs exactly between metadata and manifest.",
        section="cross_file",
    ),
    "CROSS_MANIFEST_002": RuleDefinition(
        rule_id="CROSS_MANIFEST_002",
        severity=Severity.WARNING,
        title="Extra manifest sample not in metadata",
        description="Manifest contains samples not represented in metadata.",
        rationale="Extra manifest rows can indicate stale files or incorrect sample mapping.",
        suggested_fix="Remove unmatched manifest rows or add corresponding metadata rows.",
        section="cross_file",
    ),
    "CROSS_MANIFEST_003": RuleDefinition(
        rule_id="CROSS_MANIFEST_003",
        severity=Severity.ERROR,
        title="Manifest sample ID column is missing",
        description="The sample ID column requested for the manifest was not found.",
        rationale="Sample matching cannot be performed without the correct manifest sample ID column.",
        suggested_fix="Provide the correct manifest sample ID column name with --sample.",
        section="cross_file",
    ),
    "DESIGN_GROUP_001": RuleDefinition(
        rule_id="DESIGN_GROUP_001",
        severity=Severity.ERROR,
        title="Condition has fewer than two groups",
        description="Primary analysis variable does not contain at least two groups.",
        rationale="Group comparison analysis requires at least two condition levels.",
        suggested_fix="Provide a condition column with at least two biological groups.",
        section="design",
    ),
    "DESIGN_REPL_001": RuleDefinition(
        rule_id="DESIGN_REPL_001",
        severity=Severity.WARNING,
        title="Insufficient replicates in one or more groups",
        description="At least one condition group has fewer than two samples.",
        rationale="Low replication reduces statistical power and robustness.",
        suggested_fix="Add biological replicates where possible.",
        section="design",
    ),
    "DESIGN_CONF_001": RuleDefinition(
        rule_id="DESIGN_CONF_001",
        severity=Severity.ERROR,
        title="Condition is perfectly confounded with batch",
        description="Condition and batch are in one-to-one mapping.",
        rationale="Condition effect cannot be separated from batch effect.",
        suggested_fix="Include condition levels across batches or redesign batch assignment.",
        section="design",
    ),
    "PAIR_META_001": RuleDefinition(
        rule_id="PAIR_META_001",
        severity=Severity.WARNING,
        title="Incomplete pairing/block metadata",
        description="Pair/block IDs are missing or occur only once.",
        rationale="Pairing terms require complete and repeated block structure.",
        suggested_fix="Provide complete pair IDs where each pair/block has at least two samples.",
        section="design",
    ),
    "DESIGN_SINGLE_001": RuleDefinition(
        rule_id="DESIGN_SINGLE_001",
        severity=Severity.WARNING,
        title="Singleton factor level detected",
        description="A factor level contains only one sample.",
        rationale="Singleton levels can destabilize model fitting and interpretation.",
        suggested_fix="Merge sparse levels or add samples to singleton levels.",
        section="design",
    ),
    "DESIGN_IMBAL_001": RuleDefinition(
        rule_id="DESIGN_IMBAL_001",
        severity=Severity.WARNING,
        title="Severe group imbalance detected",
        description="Largest condition group is much larger than the smallest group.",
        rationale="Severe imbalance can bias estimates and reduce effective power.",
        suggested_fix="Rebalance group sizes where possible or interpret with caution.",
        section="design",
    ),
    "DESIGN_SIZE_001": RuleDefinition(
        rule_id="DESIGN_SIZE_001",
        severity=Severity.ERROR,
        title="Too many model parameters for sample count",
        description="Estimated model complexity is too high for available samples.",
        rationale="Over-parameterized designs lead to unstable or inestimable models.",
        suggested_fix="Reduce model complexity or increase sample size.",
        section="design",
    ),
    "DESIGN_CONTRAST_001": RuleDefinition(
        rule_id="DESIGN_CONTRAST_001",
        severity=Severity.ERROR,
        title="Requested contrast is not valid",
        description="Requested contrast levels are not present in the condition column.",
        rationale="Invalid contrast cannot be estimated from observed groups.",
        suggested_fix="Use a contrast that references existing condition levels.",
        section="design",
    ),
    "DESIGN_REQ_001": RuleDefinition(
        rule_id="DESIGN_REQ_001",
        severity=Severity.ERROR,
        title="Requested design column is missing",
        description="A requested batch/pair/covariate column is missing in metadata.",
        rationale="Model terms cannot be used if corresponding columns are absent.",
        suggested_fix="Add the missing design column or remove it from the CLI options.",
        section="design",
    ),
    "DESIGN_OK_001": RuleDefinition(
        rule_id="DESIGN_OK_001",
        severity=Severity.INFO,
        title="Design checks passed",
        description="No major experiment design hazards were detected.",
        rationale="A well-structured design improves validity of downstream results.",
        suggested_fix="No action required.",
        section="design",
    ),
}


def make_issue(rule_id: str, *, detail: Optional[str] = None) -> Issue:
    rule = RULES[rule_id]
    description = rule.description if detail is None else f"{rule.description} Details: {detail}"
    return Issue(
        rule_id=rule.rule_id,
        severity=rule.severity,
        title=rule.title,
        description=description,
        rationale=rule.rationale,
        suggested_fix=rule.suggested_fix,
        section=rule.section,
    )
