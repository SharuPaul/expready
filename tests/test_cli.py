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
    assert (out_dir / "metadata.fixed.csv").exists()
    assert (out_dir / "manifest.fixed.csv").exists()
    assert (out_dir / "fix.log").exists()


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
    assert "Fix inputs and re-validate." in text
    assert "usage: expready fix [options]" in text
    assert "help:" in text
