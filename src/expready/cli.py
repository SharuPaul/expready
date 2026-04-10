from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import re
import shlex
import sys
from typing import Optional, Sequence

from expready import __version__
from expready.loaders import detect_delimiter_mode, inspect_delimiter_issues, load_manifest, load_matrix, load_metadata
from expready.models import StudyConfig, Table
from expready.validation import build_metadata_from_matrix, ensure_output_directory, run_validation
from expready.reports import write_html_report


class ShortHelpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):  # type: ignore[override]
        if hasattr(parser, "format_short_help"):
            parser._print_message(parser.format_short_help())
        else:
            parser.print_usage()
        parser.exit()


class LongHelpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):  # type: ignore[override]
        parser.print_help()
        parser.exit()


class CombinedHelpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):  # type: ignore[override]
        if option_string == "-h":
            if hasattr(parser, "format_short_help"):
                parser._print_message(parser.format_short_help())
            else:
                parser.print_usage()
        else:
            parser.print_help()
        parser.exit()


class OrderedHelpParser(argparse.ArgumentParser):
    """ArgumentParser that prints description before usage and commands before options."""

    @staticmethod
    def _format_commands_group(action_groups: list[argparse._ArgumentGroup], formatter: argparse.HelpFormatter) -> bool:
        commands_groups = [g for g in action_groups if g.title == "commands"]
        if not commands_groups:
            return False

        formatter.start_section("commands")
        lines: list[str] = []
        for group in commands_groups:
            for action in group._group_actions:
                # Subcommands are represented by _SubParsersAction.
                if hasattr(action, "_get_subactions"):
                    for subaction in action._get_subactions():
                        name = getattr(subaction, "dest", "")
                        help_text = getattr(subaction, "help", "") or ""
                        lines.append(f"{name:<11} {help_text}")
        formatter.add_text("\n".join(lines))
        formatter.end_section()
        return True

    def format_help(self) -> str:
        formatter = self._get_formatter()

        if self.description:
            formatter.add_text(self.description)

        formatter.add_usage(self.usage, self._actions, self._mutually_exclusive_groups)

        commands_groups = [g for g in self._action_groups if g.title == "commands"]
        options_groups = [g for g in self._action_groups if g.title in {"options", "optional arguments"}]
        seen = set(commands_groups + options_groups)
        remaining_groups = [g for g in self._action_groups if g not in seen]
        has_commands = bool(commands_groups)
        ordered_groups = commands_groups + remaining_groups + ([] if has_commands else options_groups)

        if has_commands:
            self._format_commands_group(ordered_groups, formatter)
            for action_group in remaining_groups:
                formatter.start_section(action_group.title)
                formatter.add_text(action_group.description)
                formatter.add_arguments(action_group._group_actions)
                formatter.end_section()
        else:
            for action_group in ordered_groups:
                formatter.start_section(action_group.title)
                formatter.add_text(action_group.description)
                formatter.add_arguments(action_group._group_actions)
                formatter.end_section()

        if has_commands:
            formatter.start_section("help")
            formatter.add_text("-h, --help   print help message, --help for detailed help")
            formatter.end_section()

        formatter.add_text(self.epilog)
        return "\n" + formatter.format_help() + "\n"

    def format_short_help(self) -> str:
        formatter = self._get_formatter()
        short_text = getattr(self, "short_description", None)
        if not short_text and self.description:
            short_text = self.description.splitlines()[0]
        formatter.add_text(short_text)
        formatter.add_usage(self.usage, self._actions, self._mutually_exclusive_groups)

        command_names: list[str] = []
        for action_group in self._action_groups:
            if action_group.title != "commands":
                continue
            for action in action_group._group_actions:
                if hasattr(action, "_get_subactions"):
                    for subaction in action._get_subactions():
                        command_names.append(getattr(subaction, "dest", ""))
        if command_names:
            formatter.start_section("commands")
            formatter.add_text(", ".join(command_names))
            formatter.end_section()

        formatter.start_section("help")
        formatter.add_text("-h, --help   print help message, --help for detailed help")
        formatter.end_section()
        return "\n" + formatter.format_help() + "\n"


def _add_help_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-h",
        "--help",
        nargs=0,
        action=CombinedHelpAction,
        help="print help message, --help for detailed help",
    )


def _existing_file(path_text: str) -> str:
    path = Path(path_text)
    if not path.exists():
        raise argparse.ArgumentTypeError(f"File not found: {path_text}")
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"Not a file: {path_text}")
    try:
        with path.open("rb"):
            pass
    except OSError as exc:
        raise argparse.ArgumentTypeError(f"File is not readable: {path_text} ({exc})") from exc
    return path_text


def _write_metadata_table(table: Table, output_path: Path, *, delimiter: str = ",") -> None:
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=table.columns, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(table.rows)


def _build_study_config(args: argparse.Namespace, *, output_required: bool) -> StudyConfig:
    output_path = Path(args.output) if output_required else Path(args.output) if args.output else Path(".")
    shared_sample_column = args.sample_id or "sample_id"
    metadata_sample_column = args.metadata_sample or shared_sample_column
    manifest_sample_column = args.manifest_sample or shared_sample_column
    return StudyConfig(
        metadata_path=Path(args.metadata) if args.metadata else None,
        metadata_sample_column=metadata_sample_column,
        condition_column=args.condition,
        output_dir=output_path,
        matrix_path=Path(args.matrix) if args.matrix else None,
        manifest_path=Path(args.manifest) if args.manifest else None,
        manifest_sample_column=manifest_sample_column,
        manifest_path_column=args.manifest_path,
        check_manifest_paths=args.check_paths,
        batch_column=args.batch,
        pair_column=args.pair,
        contrast=args.contrast,
        covariates=args.covars or [],
    )


def _normalize_column_token(name: str) -> str:
    return re.sub(r"[\s\-_]+", "_", name.strip().lower())


def _resolve_column_name(columns: list[str], requested: str) -> str:
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


def _resolve_condition_column(columns: list[str], requested: str) -> str:
    resolved = _resolve_column_name(columns, requested)
    if resolved in columns:
        return resolved
    if _normalize_column_token(requested) == "condition":
        fallback = _resolve_column_name(columns, "treatment")
        if fallback in columns:
            return fallback
    return requested


def _guess_manifest_path_column(columns: list[str]) -> Optional[str]:
    common = ["file_path", "filepath", "path", "file", "fastq_path"]
    for candidate in common:
        resolved = _resolve_column_name(columns, candidate)
        if resolved in columns:
            return resolved
    return None


def _validate_inputs_before_run(config: StudyConfig) -> list[str]:
    errors: list[str] = []
    for label, path in [("metadata", config.metadata_path), ("matrix", config.matrix_path), ("manifest", config.manifest_path)]:
        if path is None:
            continue
        detail = inspect_delimiter_issues(path)
        if detail:
            errors.append(f"{label}: {detail}")

    metadata_table: Optional[Table] = None
    if config.metadata_path:
        metadata_table = load_metadata(config.metadata_path)
        resolved_sample = _resolve_column_name(metadata_table.columns, config.metadata_sample_column)
        if resolved_sample not in metadata_table.columns:
            errors.append(
                f"metadata: sample-ID column '{config.metadata_sample_column}' was not found. "
                f"Available columns: {', '.join(metadata_table.columns)}."
            )

        resolved_condition = _resolve_condition_column(metadata_table.columns, config.condition_column)
        if resolved_condition not in metadata_table.columns:
            errors.append(
                f"metadata: condition column '{config.condition_column}' was not found "
                f"(default fallback 'treatment' also not found). Available columns: {', '.join(metadata_table.columns)}."
            )

        requested = [config.batch_column, config.pair_column, *config.covariates]
        for column in [value for value in requested if value]:
            resolved = _resolve_column_name(metadata_table.columns, column)
            if resolved not in metadata_table.columns:
                errors.append(
                    f"metadata: requested column '{column}' was not found. "
                    f"Available columns: {', '.join(metadata_table.columns)}."
                )

    if config.manifest_path:
        manifest_table = load_manifest(config.manifest_path)
        resolved_manifest_sample = _resolve_column_name(manifest_table.columns, config.manifest_sample_column)
        if resolved_manifest_sample not in manifest_table.columns:
            errors.append(
                f"manifest: sample-ID column '{config.manifest_sample_column}' was not found. "
                f"Available columns: {', '.join(manifest_table.columns)}."
            )

        if config.manifest_path_column:
            resolved_path = _resolve_column_name(manifest_table.columns, config.manifest_path_column)
            if resolved_path not in manifest_table.columns:
                errors.append(
                    f"manifest: path column '{config.manifest_path_column}' was not found. "
                    f"Available columns: {', '.join(manifest_table.columns)}."
                )
        elif config.check_manifest_paths:
            guessed = _guess_manifest_path_column(manifest_table.columns)
            if guessed is None:
                errors.append(
                    "manifest: --check-paths requires a manifest path column. "
                    "Provide --manifest-path or include one of: file_path, filepath, path, file, fastq_path."
                )

    return errors


def _normalize_column_names(
    columns: list[str], *, replace_internal_spaces: bool
) -> tuple[list[str], dict[str, str], int]:
    normalized_columns: list[str] = []
    mapping: dict[str, str] = {}
    renamed_count = 0
    used: dict[str, int] = {}

    for column in columns:
        base = column.strip()
        if replace_internal_spaces:
            base = re.sub(r"\s+", "_", base)
        if base == "":
            base = "column"
        candidate = base
        index = 2
        while candidate in used:
            candidate = f"{base}_{index}"
            index += 1
        used[candidate] = 1
        mapping[column] = candidate
        normalized_columns.append(candidate)
        if candidate != column:
            renamed_count += 1

    return normalized_columns, mapping, renamed_count


def _normalize_table(table: Table, *, normalize_header_spaces: bool) -> tuple[Table, dict[str, int]]:
    empty_tokens = {"na", "n/a", "null", "none"}
    normalized_columns, column_map, renamed_columns = _normalize_column_names(
        table.columns,
        replace_internal_spaces=normalize_header_spaces,
    )
    normalized_rows: list[dict[str, str]] = []
    normalized_empty_values = 0
    removed_empty_rows = 0

    for row in table.rows:
        normalized_row: dict[str, str] = {}
        for column in table.columns:
            raw_value = str(row.get(column, "") if row.get(column, "") is not None else "").strip()
            lowered = raw_value.lower()
            normalized_column = column_map[column]
            if lowered in empty_tokens:
                normalized_row[normalized_column] = ""
                normalized_empty_values += 1
            else:
                normalized_row[normalized_column] = raw_value
        if any(value != "" for value in normalized_row.values()):
            normalized_rows.append(normalized_row)
        else:
            removed_empty_rows += 1

    return Table(columns=normalized_columns, rows=normalized_rows), {
        "normalized_empty_values": normalized_empty_values,
        "removed_empty_rows": removed_empty_rows,
        "renamed_columns": renamed_columns,
        "header_space_normalization_skipped": 0 if normalize_header_spaces else 1,
    }


def _write_change_log(
    output_path: Path,
    *,
    metadata_stats: Optional[dict[str, int]],
    manifest_stats: Optional[dict[str, int]],
    wrote_metadata: bool,
    wrote_manifest: bool,
) -> None:
    lines = [
        "Fix command change log",
        "",
        f"Metadata fixed file written: {'yes' if wrote_metadata else 'no'}",
        f"Manifest fixed file written: {'yes' if wrote_manifest else 'no'}",
        "",
    ]
    if metadata_stats:
        lines.extend(
            [
                "Metadata changes:",
                f"- Empty-like values standardized: {metadata_stats['normalized_empty_values']}",
                f"- Fully empty rows removed: {metadata_stats['removed_empty_rows']}",
                f"- Header names normalized: {metadata_stats['renamed_columns']}",
                "- Header-space normalization skipped: "
                f"{'yes (space-delimited input)' if metadata_stats['header_space_normalization_skipped'] else 'no'}",
                "",
            ]
        )
    if manifest_stats:
        lines.extend(
            [
                "Manifest changes:",
                f"- Empty-like values standardized: {manifest_stats['normalized_empty_values']}",
                f"- Fully empty rows removed: {manifest_stats['removed_empty_rows']}",
                f"- Header names normalized: {manifest_stats['renamed_columns']}",
                "- Header-space normalization skipped: "
                f"{'yes (space-delimited input)' if manifest_stats['header_space_normalization_skipped'] else 'no'}",
                "",
            ]
        )
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _resolve_report_path(output_dir: Path, report_name: Optional[str]) -> Path:
    if report_name:
        name = report_name.strip()
        if not name:
            name = "report"
        if name.lower().endswith(".html"):
            filename = name
        else:
            filename = f"{name}.html"
        return output_dir / filename

    base = output_dir / "report.html"
    if not base.exists():
        return base

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = output_dir / f"report_{stamp}.html"
    index = 1
    while candidate.exists():
        candidate = output_dir / f"report_{stamp}_{index}.html"
        index += 1
    return candidate


def _resolve_path_with_suffix(output_dir: Path, basename: str) -> Path:
    path = output_dir / basename
    if not path.exists():
        return path
    stem = Path(basename).stem
    suffix = Path(basename).suffix
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = output_dir / f"{stem}_{stamp}{suffix}"
    index = 1
    while candidate.exists():
        candidate = output_dir / f"{stem}_{stamp}_{index}{suffix}"
        index += 1
    return candidate


def _resolve_inferred_metadata_path(output_dir: Path) -> Path:
    base = output_dir / "metadata.inferred.csv"
    if not base.exists():
        return base

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = output_dir / f"metadata.inferred_{stamp}.csv"
    index = 1
    while candidate.exists():
        candidate = output_dir / f"metadata.inferred_{stamp}_{index}.csv"
        index += 1
    return candidate


def _fixed_table_basename(kind: str, output_format: str) -> str:
    suffix = ".tsv" if output_format == "tsv" else ".csv"
    return f"{kind}.fixed{suffix}"


def run_validate(args: argparse.Namespace) -> int:
    config = _build_study_config(args, output_required=True)
    if config.metadata_path is None and config.matrix_path is None:
        print("Please provide --metadata or --matrix.")
        return 2
    if config.manifest_path and config.check_manifest_paths and not config.manifest_path_column:
        manifest_table = load_manifest(config.manifest_path)
        guessed_path_column = _guess_manifest_path_column(manifest_table.columns)
        if guessed_path_column:
            config = StudyConfig(
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
    input_errors = _validate_inputs_before_run(config)
    if input_errors:
        print("Input error(s):")
        for error in input_errors:
            print(f"- {error}")
        return 2

    print("Running Experiment-Readiness Checker...")
    print("Inputs:")
    print(f"- Metadata: {config.metadata_path}")
    if config.matrix_path:
        print(f"- Matrix: {config.matrix_path}")
    if config.manifest_path:
        print(f"- Manifest: {config.manifest_path}")
    if not config.matrix_path and not config.manifest_path:
        print("- Mode: metadata + design checks")

    ensure_output_directory(config.output_dir)
    report, metadata_table = run_validation(config)
    report.metadata["provenance"] = {
        "tool_name": "Experiment-Readiness Checker",
        "tool_version": __version__,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": "expready " + " ".join(shlex.quote(token) for token in getattr(args, "_argv", [])),
    }

    html_path = _resolve_report_path(config.output_dir, args.report_name)
    write_html_report(report, html_path)
    inferred_metadata_path: Optional[Path] = None
    if config.metadata_path is None and config.matrix_path is not None:
        inferred_metadata_path = _resolve_inferred_metadata_path(config.output_dir)
        _write_metadata_table(metadata_table, inferred_metadata_path)

    print()
    print(f"Status: {report.status.upper()}")
    print("Generated files:")
    print(f"- HTML: {html_path}")
    if inferred_metadata_path:
        print(f"- Inferred metadata: {inferred_metadata_path}")
    return 1 if report.status == "fail" else 0


def run_fix(args: argparse.Namespace) -> int:
    config = _build_study_config(args, output_required=True)
    if config.metadata_path is None and config.matrix_path is None and config.manifest_path is None:
        print("Please provide --metadata, --matrix, or --manifest.")
        return 2

    print("Running Experiment-Readiness Checker fix...")
    print("Inputs:")
    print(f"- Metadata: {config.metadata_path}")
    if config.matrix_path:
        print(f"- Matrix: {config.matrix_path}")
    if config.manifest_path:
        print(f"- Manifest: {config.manifest_path}")

    ensure_output_directory(config.output_dir)
    table_delimiter = "\t" if args.format == "tsv" else ","

    fixed_metadata_path: Optional[Path] = None
    fixed_manifest_path: Optional[Path] = None
    metadata_stats: Optional[dict[str, int]] = None
    manifest_stats: Optional[dict[str, int]] = None

    metadata_table: Optional[Table] = None
    normalize_metadata_headers = True
    if config.metadata_path:
        metadata_table = load_metadata(config.metadata_path)
        normalize_metadata_headers = detect_delimiter_mode(config.metadata_path) != "whitespace"
    elif config.matrix_path:
        metadata_table = build_metadata_from_matrix(
            load_matrix(config.matrix_path),
            sample_id_column=config.metadata_sample_column,
        )
    if metadata_table is not None:
        metadata_fixed, metadata_stats = _normalize_table(
            metadata_table,
            normalize_header_spaces=normalize_metadata_headers,
        )
        fixed_metadata_path = _resolve_path_with_suffix(
            config.output_dir, _fixed_table_basename("metadata", args.format)
        )
        _write_metadata_table(metadata_fixed, fixed_metadata_path, delimiter=table_delimiter)

    if config.manifest_path:
        manifest_table = load_manifest(config.manifest_path)
        normalize_manifest_headers = detect_delimiter_mode(config.manifest_path) != "whitespace"
        manifest_fixed, manifest_stats = _normalize_table(
            manifest_table,
            normalize_header_spaces=normalize_manifest_headers,
        )
        fixed_manifest_path = _resolve_path_with_suffix(
            config.output_dir, _fixed_table_basename("manifest", args.format)
        )
        _write_metadata_table(manifest_fixed, fixed_manifest_path, delimiter=table_delimiter)

    fix_log_path = _resolve_path_with_suffix(config.output_dir, "fix.log")
    _write_change_log(
        fix_log_path,
        metadata_stats=metadata_stats,
        manifest_stats=manifest_stats,
        wrote_metadata=fixed_metadata_path is not None,
        wrote_manifest=fixed_manifest_path is not None,
    )

    print()
    print("Generated files:")
    if fixed_metadata_path:
        print(f"- Metadata (fixed): {fixed_metadata_path}")
    if fixed_manifest_path:
        print(f"- Manifest (fixed): {fixed_manifest_path}")
    print(f"- Fix log: {fix_log_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = OrderedHelpParser(
        prog="expready",
        usage="expready <command> [options]",
        description="Experiment-Readiness Checker checks whether your study inputs are analysis-ready.\n"
        "It validates metadata, design setup, and sample consistency across files.",
        add_help=False,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.short_description = "Experiment-Readiness Checker"
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="command",
        title="commands",
        parser_class=OrderedHelpParser,
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Run metadata, design, and sample consistency validation",
        usage="expready validate [options]",
        description="Run full validation and write an HTML report.",
        add_help=False,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    validate_parser.short_description = "Run full validation."
    validate_metadata_group = validate_parser.add_argument_group("metadata file options")
    validate_matrix_group = validate_parser.add_argument_group("matrix file options")
    validate_manifest_group = validate_parser.add_argument_group("manifest file options")
    validate_other_group = validate_parser.add_argument_group("other options")

    validate_metadata_group.add_argument(
        "--metadata",
        required=False,
        type=_existing_file,
        metavar="FILE",
        help="Metadata table path (.csv or .tsv). If omitted, metadata is inferred from --matrix sample names.",
    )
    validate_metadata_group.add_argument(
        "--sample-id",
        dest="sample_id",
        default=None,
        metavar="COLUMN",
        help="Shared sample-ID column name for metadata and manifest (default: sample_id).",
    )
    validate_metadata_group.add_argument(
        "--metadata-id",
        dest="metadata_sample",
        default=None,
        metavar="COLUMN",
        help="Column name in metadata that contains sample IDs (overrides --sample-id for metadata).",
    )
    validate_metadata_group.add_argument(
        "--condition",
        required=False,
        default="condition",
        metavar="COLUMN",
        help="Main grouping column you want to compare (for example: condition, cohort, treatment).",
    )
    validate_other_group.add_argument(
        "--output",
        required=True,
        metavar="DIR",
        help="Directory where the report files will be written.",
    )
    validate_other_group.add_argument(
        "--report",
        dest="report_name",
        required=False,
        default=None,
        metavar="NAME",
        help="Optional HTML report filename (with or without .html).",
    )
    validate_matrix_group.add_argument(
        "--matrix",
        required=False,
        type=_existing_file,
        metavar="FILE",
        help="Optional feature matrix (.csv/.tsv). Supports common layouts like 'gene_id, gene_name, <sample columns>'.",
    )
    validate_manifest_group.add_argument(
        "--manifest",
        required=False,
        type=_existing_file,
        metavar="FILE",
        help="Optional manifest file (.csv/.tsv) for sample-to-file consistency checks.",
    )
    validate_manifest_group.add_argument(
        "--manifest-id",
        dest="manifest_sample",
        default=None,
        metavar="COLUMN",
        help="Manifest column containing sample IDs (overrides --sample-id for manifest).",
    )
    validate_manifest_group.add_argument(
        "--manifest-path",
        dest="manifest_path",
        default=None,
        metavar="COLUMN",
        help="Manifest column containing file paths (for path quality checks).",
    )
    validate_manifest_group.add_argument(
        "--check-paths",
        dest="check_paths",
        action="store_true",
        help="Check whether manifest file paths exist on disk (uses --manifest-path or common path column names).",
    )
    validate_metadata_group.add_argument(
        "--batch",
        required=False,
        metavar="COLUMN",
        help="Optional processing/batch column for confounding checks.",
    )
    validate_metadata_group.add_argument(
        "--pair",
        required=False,
        metavar="COLUMN",
        help="Optional pair/block column for paired or blocked designs.",
    )
    validate_metadata_group.add_argument(
        "--contrast",
        required=False,
        metavar="A_vs_B",
        help="Optional contrast in 'GroupA_vs_GroupB' format.",
    )
    validate_metadata_group.add_argument(
        "--covars",
        dest="covars",
        nargs="*",
        default=None,
        metavar="COLS",
        help="Optional covariate columns, space-separated.",
    )
    _add_help_flags(validate_parser)
    validate_parser.set_defaults(handler=run_validate)

    fix_parser = subparsers.add_parser(
        "fix",
        help="Apply safe input cleanup",
        usage="expready fix [options]",
        description="Apply safe cleanup to metadata/manifest.",
        add_help=False,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    fix_parser.short_description = "Fix inputs."
    fix_metadata_group = fix_parser.add_argument_group("metadata file options")
    fix_matrix_group = fix_parser.add_argument_group("matrix file options")
    fix_manifest_group = fix_parser.add_argument_group("manifest file options")
    fix_other_group = fix_parser.add_argument_group("other options")

    fix_metadata_group.add_argument(
        "--metadata",
        required=False,
        type=_existing_file,
        metavar="FILE",
        help="Metadata table path (.csv or .tsv).",
    )
    fix_metadata_group.add_argument(
        "--sample-id",
        dest="sample_id",
        default=None,
        metavar="COLUMN",
        help="Shared sample-ID column name for metadata and manifest (default: sample_id).",
    )
    fix_metadata_group.add_argument(
        "--metadata-id",
        dest="metadata_sample",
        default=None,
        metavar="COLUMN",
        help="Column name in metadata that contains sample IDs (overrides --sample-id for metadata).",
    )
    fix_metadata_group.add_argument(
        "--condition",
        required=False,
        default="condition",
        metavar="COLUMN",
        help="Main grouping column to validate (default: condition).",
    )
    fix_other_group.add_argument(
        "--output",
        required=True,
        metavar="DIR",
        help="Directory where fixed files and log will be written.",
    )
    fix_matrix_group.add_argument(
        "--matrix",
        required=False,
        type=_existing_file,
        metavar="FILE",
        help="Optional feature matrix (.csv/.tsv). Used for validation and metadata inference if --metadata is omitted.",
    )
    fix_manifest_group.add_argument(
        "--manifest",
        required=False,
        type=_existing_file,
        metavar="FILE",
        help="Optional manifest file (.csv/.tsv).",
    )
    fix_manifest_group.add_argument(
        "--manifest-id",
        dest="manifest_sample",
        default=None,
        metavar="COLUMN",
        help="Manifest column containing sample IDs (overrides --sample-id for manifest).",
    )
    fix_manifest_group.add_argument(
        "--manifest-path",
        dest="manifest_path",
        default=None,
        metavar="COLUMN",
        help="Manifest column containing file paths.",
    )
    fix_manifest_group.add_argument(
        "--check-paths",
        dest="check_paths",
        action="store_true",
        help="Reserved for compatibility with validate; ignored by fix.",
    )
    fix_metadata_group.add_argument(
        "--batch",
        required=False,
        metavar="COLUMN",
        help="Optional processing/batch column for confounding checks.",
    )
    fix_metadata_group.add_argument(
        "--pair",
        required=False,
        metavar="COLUMN",
        help="Optional pair/block column for paired or blocked designs.",
    )
    fix_metadata_group.add_argument(
        "--contrast",
        required=False,
        metavar="A_vs_B",
        help="Optional contrast in 'GroupA_vs_GroupB' format.",
    )
    fix_metadata_group.add_argument(
        "--covars",
        dest="covars",
        nargs="*",
        default=None,
        metavar="COLS",
        help="Optional covariate columns, space-separated.",
    )
    fix_other_group.add_argument(
        "--format",
        dest="format",
        choices=["csv", "tsv"],
        default="tsv",
        metavar="FMT",
        help="Fixed-table output format: csv or tsv (default: tsv).",
    )
    _add_help_flags(fix_parser)
    fix_parser.set_defaults(handler=run_fix)

    _add_help_flags(parser)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    if not raw_argv:
        if hasattr(parser, "format_short_help"):
            parser._print_message(parser.format_short_help())
        else:
            parser.print_help()
        return 0

    if len(raw_argv) == 1 and raw_argv[0] not in {"-h", "--help"}:
        command_name = raw_argv[0]
        subparser: Optional[argparse.ArgumentParser] = None
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                subparser = action.choices.get(command_name)
                break
        if subparser is not None:
            if hasattr(subparser, "format_short_help"):
                parser._print_message(subparser.format_short_help())
            else:
                subparser.print_help()
            return 0

    args = parser.parse_args(raw_argv)
    args._argv = raw_argv
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
