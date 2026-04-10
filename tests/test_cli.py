import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from expready.cli import _existing_file
from expready.cli import main


def test_cli_generates_reports(capsys) -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    out_dir = Path("tests/.tmp/cli_out")
    out_dir.mkdir(parents=True, exist_ok=True)

    exit_code = main(
        [
            "validate",
            "--metadata",
            str(fixture_dir / "metadata_valid.csv"),
            "--matrix",
            str(fixture_dir / "matrix_valid.tsv"),
            "--condition",
            "condition",
            "--output",
            str(out_dir),
        ]
    )
    _ = capsys.readouterr()

    assert exit_code == 0
    assert (out_dir / "report.html").exists()


def test_cli_accepts_matrix_flag(capsys) -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    out_dir = Path("tests/.tmp/cli_out_matrix")
    out_dir.mkdir(parents=True, exist_ok=True)

    exit_code = main(
        [
            "validate",
            "--metadata",
            str(fixture_dir / "metadata_valid.csv"),
            "--matrix",
            str(fixture_dir / "matrix_valid.tsv"),
            "--condition",
            "condition",
            "--output",
            str(out_dir),
        ]
    )
    _ = capsys.readouterr()

    assert exit_code == 0
    assert (out_dir / "report.html").exists()


def test_cli_supports_manifest(capsys) -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    out_dir = Path("tests/.tmp/cli_out_gatk")
    out_dir.mkdir(parents=True, exist_ok=True)

    exit_code = main(
        [
            "validate",
            "--metadata",
            str(fixture_dir / "metadata_valid.csv"),
            "--manifest",
            str(fixture_dir / "manifest_valid.tsv"),
            "--condition",
            "condition",
            "--output",
            str(out_dir),
        ]
    )
    _ = capsys.readouterr()

    assert exit_code == 0
    assert (out_dir / "report.html").exists()


def test_cli_supports_custom_metadata_sample_column(capsys) -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    out_dir = Path("tests/.tmp/cli_out_custom_sample")
    out_dir.mkdir(parents=True, exist_ok=True)

    exit_code = main(
        [
            "validate",
            "--metadata",
            str(fixture_dir / "metadata_custom_sample.csv"),
            "--metadata-id",
            "sample",
            "--matrix",
            str(fixture_dir / "matrix_valid.tsv"),
            "--condition",
            "condition",
            "--output",
            str(out_dir),
        ]
    )
    _ = capsys.readouterr()

    assert exit_code == 0
    assert (out_dir / "report.html").exists()


def test_cli_supports_shared_sample_id_option(capsys) -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    out_dir = Path("tests/.tmp/cli_out_shared_sample")
    out_dir.mkdir(parents=True, exist_ok=True)

    exit_code = main(
        [
            "validate",
            "--metadata",
            str(fixture_dir / "metadata_custom_sample.csv"),
            "--manifest",
            str(fixture_dir / "manifest_custom_sample.tsv"),
            "--sample-id",
            "sample",
            "--condition",
            "condition",
            "--output",
            str(out_dir),
        ]
    )
    _ = capsys.readouterr()

    assert exit_code == 0
    assert (out_dir / "report.html").exists()


def test_cli_validate_auto_metadata_from_matrix(capsys) -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    out_dir = Path("tests/.tmp/cli_out_auto")
    out_dir.mkdir(parents=True, exist_ok=True)

    exit_code = main(
        [
            "validate",
            "--matrix",
            str(fixture_dir / "matrix_auto.tsv"),
            "--output",
            str(out_dir),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "metadata_source" not in captured.out  # output stays user-facing only
    assert (out_dir / "report.html").exists()


def test_cli_fix_generates_fixed_outputs(capsys) -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    out_dir = Path("tests/.tmp/cli_fix_out")
    out_dir.mkdir(parents=True, exist_ok=True)

    exit_code = main(
        [
            "fix",
            "--metadata",
            str(fixture_dir / "metadata_valid.csv"),
            "--manifest",
            str(fixture_dir / "manifest_valid.tsv"),
            "--output",
            str(out_dir),
        ]
    )
    _ = capsys.readouterr()

    assert exit_code == 0
    assert (out_dir / "metadata.fixed.tsv").exists()
    assert (out_dir / "manifest.fixed.tsv").exists()
    assert (out_dir / "fix.log").exists()


def test_cli_fix_can_write_csv_outputs(capsys) -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    out_dir = Path("tests/.tmp/cli_fix_out_csv")
    out_dir.mkdir(parents=True, exist_ok=True)

    exit_code = main(
        [
            "fix",
            "--metadata",
            str(fixture_dir / "metadata_valid.csv"),
            "--manifest",
            str(fixture_dir / "manifest_valid.tsv"),
            "--output",
            str(out_dir),
            "--format",
            "csv",
        ]
    )
    _ = capsys.readouterr()

    assert exit_code == 0
    assert (out_dir / "metadata.fixed.csv").exists()
    assert (out_dir / "manifest.fixed.csv").exists()
    assert (out_dir / "fix.log").exists()


def test_cli_fix_normalizes_header_spaces_to_underscores(capsys) -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    out_dir = Path("tests/.tmp/cli_fix_out_header_norm")
    out_dir.mkdir(parents=True, exist_ok=True)

    exit_code = main(
        [
            "fix",
            "--metadata",
            str(fixture_dir / "metadata_space_header.csv"),
            "--output",
            str(out_dir),
        ]
    )
    _ = capsys.readouterr()

    assert exit_code == 0
    fixed_path = out_dir / "metadata.fixed.tsv"
    assert fixed_path.exists()
    header = fixed_path.read_text(encoding="utf-8").splitlines()[0]
    assert header == "sample_id\tcondition\tbatch_id"


def test_cli_fix_skips_header_space_normalization_for_space_delimited_input(capsys) -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    out_dir = Path("tests/.tmp/cli_fix_out_space_delimited")
    out_dir.mkdir(parents=True, exist_ok=True)

    exit_code = main(
        [
            "fix",
            "--metadata",
            str(fixture_dir / "metadata_space_delimited.txt"),
            "--output",
            str(out_dir),
        ]
    )
    _ = capsys.readouterr()

    assert exit_code == 0
    fix_log = (out_dir / "fix.log").read_text(encoding="utf-8")
    assert "Header-space normalization skipped: yes (space-delimited input)" in fix_log


def test_cli_no_command_prints_short_help(capsys) -> None:
    exit_code = main([])
    captured = capsys.readouterr()
    text = captured.out + captured.err

    assert exit_code == 0
    assert "usage: expready <command> [options]" in text
    assert "commands:" in text


def test_cli_validate_without_options_prints_short_help(capsys) -> None:
    exit_code = main(["validate"])
    captured = capsys.readouterr()
    text = captured.out + captured.err

    assert exit_code == 0
    assert "Run full validation." in text
    assert "usage: expready validate [options]" in text
    assert "help:" in text


def test_cli_fix_without_options_prints_short_help(capsys) -> None:
    exit_code = main(["fix"])
    captured = capsys.readouterr()
    text = captured.out + captured.err

    assert exit_code == 0
    assert "Fix inputs." in text
    assert "usage: expready fix [options]" in text
    assert "help:" in text


def test_cli_validate_fails_fast_when_metadata_id_column_missing(capsys) -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    out_dir = Path("tests/.tmp/cli_out_bad_metadata_col")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "report.html"
    if report_path.exists():
        report_path.unlink()

    exit_code = main(
        [
            "validate",
            "--metadata",
            str(fixture_dir / "metadata_valid.csv"),
            "--metadata-id",
            "bad_sample_col",
            "--output",
            str(out_dir),
        ]
    )
    captured = capsys.readouterr()
    text = captured.out + captured.err

    assert exit_code == 2
    assert "Input error(s):" in text
    assert not report_path.exists()


def test_cli_validate_fails_fast_when_manifest_id_column_missing(capsys) -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    out_dir = Path("tests/.tmp/cli_out_bad_manifest_col")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "report.html"
    if report_path.exists():
        report_path.unlink()

    exit_code = main(
        [
            "validate",
            "--metadata",
            str(fixture_dir / "metadata_valid.csv"),
            "--manifest",
            str(fixture_dir / "manifest_valid.tsv"),
            "--manifest-id",
            "bad_manifest_col",
            "--output",
            str(out_dir),
        ]
    )
    captured = capsys.readouterr()
    text = captured.out + captured.err

    assert exit_code == 2
    assert "Input error(s):" in text
    assert not report_path.exists()


def test_cli_validate_fails_fast_when_input_delimiters_are_inconsistent(capsys) -> None:
    fixture_dir = Path(__file__).parent / "fixtures"
    out_dir = Path("tests/.tmp/cli_out_bad_delimiter")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "report.html"
    if report_path.exists():
        report_path.unlink()

    exit_code = main(
        [
            "validate",
            "--metadata",
            str(fixture_dir / "metadata_valid.csv"),
            "--matrix",
            str(fixture_dir / "matrix_inconsistent_delimiter.tsv"),
            "--output",
            str(out_dir),
        ]
    )
    captured = capsys.readouterr()
    text = captured.out + captured.err

    assert exit_code == 2
    assert "Input error(s):" in text
    assert "inconsistent delimiters" in text
    assert not report_path.exists()


def test_existing_file_reports_unreadable_path() -> None:
    target = str((Path(__file__).parent / "fixtures" / "metadata_valid.csv"))
    with patch("pathlib.Path.open", side_effect=PermissionError("denied")):
        with pytest.raises(argparse.ArgumentTypeError) as exc:
            _existing_file(target)
    assert "File is not readable:" in str(exc.value)
