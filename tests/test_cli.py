from pathlib import Path

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

    assert exit_code == 0
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
