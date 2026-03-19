from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import shlex
import sys
from typing import Optional, Sequence

from expready import __version__
from expready.loaders import load_manifest, load_matrix, load_metadata
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
    return path_text


def _write_metadata_table(table: Table, output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=table.columns)
        writer.writeheader()
        writer.writerows(table.rows)


def _build_study_config(args: argparse.Namespace, *, output_required: bool) -> StudyConfig:
    output_path = Path(args.output) if output_required else Path(args.output) if args.output else Path(".")
    return StudyConfig(
        metadata_path=Path(args.metadata) if args.metadata else None,
        metadata_sample_column=args.metadata_sample,
        condition_column=args.condition,
        output_dir=output_path,
        matrix_path=Path(args.matrix) if args.matrix else None,
        manifest_path=Path(args.manifest) if args.manifest else None,
        manifest_sample_column=args.sample,
        batch_column=args.batch,
        pair_column=args.pair,
        contrast=args.contrast,
        covariates=args.covars or [],
    )


def _normalize_table(table: Table) -> tuple[Table, dict[str, int]]:
    empty_tokens = {"na", "n/a", "null", "none"}
    normalized_rows: list[dict[str, str]] = []
    normalized_empty_values = 0
    removed_empty_rows = 0

    for row in table.rows:
        normalized_row: dict[str, str] = {}
        for column in table.columns:
            raw_value = str(row.get(column, "") if row.get(column, "") is not None else "").strip()
            lowered = raw_value.lower()
            if lowered in empty_tokens:
                normalized_row[column] = ""
                normalized_empty_values += 1
            else:
                normalized_row[column] = raw_value
        if any(value != "" for value in normalized_row.values()):
            normalized_rows.append(normalized_row)
        else:
            removed_empty_rows += 1

    return Table(columns=table.columns, rows=normalized_rows), {
        "normalized_empty_values": normalized_empty_values,
        "removed_empty_rows": removed_empty_rows,
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
                "",
            ]
        )
    if manifest_stats:
        lines.extend(
            [
                "Manifest changes:",
                f"- Empty-like values standardized: {manifest_stats['normalized_empty_values']}",
                f"- Fully empty rows removed: {manifest_stats['removed_empty_rows']}",
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


def run_validate(args: argparse.Namespace) -> int:
    config = _build_study_config(args, output_required=True)
    if config.metadata_path is None and config.matrix_path is None:
        print("Please provide --metadata or --matrix.")
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

    fixed_metadata_path: Optional[Path] = None
    fixed_manifest_path: Optional[Path] = None
    metadata_stats: Optional[dict[str, int]] = None
    manifest_stats: Optional[dict[str, int]] = None

    metadata_table: Optional[Table] = None
    if config.metadata_path:
        metadata_table = load_metadata(config.metadata_path)
    elif config.matrix_path:
        metadata_table = build_metadata_from_matrix(load_matrix(config.matrix_path))
    if metadata_table is not None:
        metadata_fixed, metadata_stats = _normalize_table(metadata_table)
        fixed_metadata_path = _resolve_path_with_suffix(config.output_dir, "metadata.fixed.csv")
        _write_metadata_table(metadata_fixed, fixed_metadata_path)

    if config.manifest_path:
        manifest_table = load_manifest(config.manifest_path)
        manifest_fixed, manifest_stats = _normalize_table(manifest_table)
        fixed_manifest_path = _resolve_path_with_suffix(config.output_dir, "manifest.fixed.csv")
        _write_metadata_table(manifest_fixed, fixed_manifest_path)

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
    validate_parser.add_argument(
        "--metadata",
        required=False,
        type=_existing_file,
        metavar="FILE",
        help="Metadata table path (.csv or .tsv). If omitted, metadata is inferred from --matrix sample names.",
    )
    validate_parser.add_argument(
        "--meta-id",
        dest="metadata_sample",
        default="sample_id",
        metavar="COLUMN",
        help="Metadata column containing sample IDs (default: sample_id).",
    )
    validate_parser.add_argument(
        "--condition",
        required=False,
        default="condition",
        metavar="COLUMN",
        help="Main grouping column you want to compare (for example: condition, cohort, treatment).",
    )
    validate_parser.add_argument(
        "--output",
        required=True,
        metavar="DIR",
        help="Directory where the report files will be written.",
    )
    validate_parser.add_argument(
        "--report",
        dest="report_name",
        required=False,
        default=None,
        metavar="NAME",
        help="Optional HTML report filename (with or without .html).",
    )
    validate_parser.add_argument(
        "--matrix",
        required=False,
        type=_existing_file,
        metavar="FILE",
        help="Optional feature matrix (.csv/.tsv). Supports common layouts like 'gene_id, gene_name, <sample columns>'.",
    )
    validate_parser.add_argument(
        "--manifest",
        required=False,
        type=_existing_file,
        metavar="FILE",
        help="Optional manifest file (.csv/.tsv) for sample-to-file consistency checks.",
    )
    validate_parser.add_argument(
        "--sample",
        dest="sample",
        default="sample_id",
        metavar="COLUMN",
        help="Manifest column containing sample IDs (default: sample_id).",
    )
    validate_parser.add_argument(
        "--batch",
        required=False,
        metavar="COLUMN",
        help="Optional processing/batch column for confounding checks.",
    )
    validate_parser.add_argument(
        "--pair",
        required=False,
        metavar="COLUMN",
        help="Optional pair/block column for paired or blocked designs.",
    )
    validate_parser.add_argument(
        "--contrast",
        required=False,
        metavar="A_vs_B",
        help="Optional contrast in 'GroupA_vs_GroupB' format.",
    )
    validate_parser.add_argument(
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
    fix_parser.add_argument(
        "--metadata",
        required=False,
        type=_existing_file,
        metavar="FILE",
        help="Metadata table path (.csv or .tsv).",
    )
    fix_parser.add_argument(
        "--meta-id",
        dest="metadata_sample",
        default="sample_id",
        metavar="COLUMN",
        help="Metadata column containing sample IDs (default: sample_id).",
    )
    fix_parser.add_argument(
        "--condition",
        required=False,
        default="condition",
        metavar="COLUMN",
        help="Main grouping column to validate (default: condition).",
    )
    fix_parser.add_argument(
        "--output",
        required=True,
        metavar="DIR",
        help="Directory where fixed files and log will be written.",
    )
    fix_parser.add_argument(
        "--matrix",
        required=False,
        type=_existing_file,
        metavar="FILE",
        help="Optional feature matrix (.csv/.tsv). Used for validation and metadata inference if --metadata is omitted.",
    )
    fix_parser.add_argument(
        "--manifest",
        required=False,
        type=_existing_file,
        metavar="FILE",
        help="Optional manifest file (.csv/.tsv).",
    )
    fix_parser.add_argument(
        "--sample",
        dest="sample",
        default="sample_id",
        metavar="COLUMN",
        help="Manifest column containing sample IDs (default: sample_id).",
    )
    fix_parser.add_argument(
        "--batch",
        required=False,
        metavar="COLUMN",
        help="Optional processing/batch column for confounding checks.",
    )
    fix_parser.add_argument(
        "--pair",
        required=False,
        metavar="COLUMN",
        help="Optional pair/block column for paired or blocked designs.",
    )
    fix_parser.add_argument(
        "--contrast",
        required=False,
        metavar="A_vs_B",
        help="Optional contrast in 'GroupA_vs_GroupB' format.",
    )
    fix_parser.add_argument(
        "--covars",
        dest="covars",
        nargs="*",
        default=None,
        metavar="COLS",
        help="Optional covariate columns, space-separated.",
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
