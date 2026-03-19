# Experiment Readiness Checker (`expready`)

`expready` is a CLI tool that checks whether study inputs are analysis-ready before downstream workflows.
It focuses on metadata quality, design quality, and sample-ID consistency across files.

## Get the code
```bash
git clone https://github.com/SharuPaul/expready.git
cd expready
```

SSH:
```bash
git clone git@github.com:SharuPaul/expready.git
cd expready
```

## Setup
Create and activate a virtual environment, then install the project:

```bash
python -m venv expread_venv
source expread_venv/bin/activate
pip install -e .
```

Windows PowerShell:
```powershell
python -m venv expread_venv
.\expread_venv\Scripts\Activate.ps1
pip install -e .
```

## Commands
- `validate`: check your inputs and create an HTML report.
- `fix`: clean common formatting issues in metadata/manifest files.

`validate` checks:
- Metadata quality: required columns, duplicate sample IDs, missing key values, suspicious sample-ID formatting.
- Design quality: at least two condition groups, low replicate groups, batch-condition confounding, pair/block completeness, group imbalance, and contrast format/group existence.
- Cross-file consistency: metadata sample IDs vs matrix sample columns, and metadata sample IDs vs manifest sample column.

`fix` checks and cleans:
- Trims leading/trailing spaces across metadata and manifest values.
- Standardizes empty-like values (`na`, `n/a`, `null`, `none`, case-insensitive) to empty values.
- Removes rows that are fully empty after cleanup.

## Test run
```bash
python -m expready validate --matrix examples/matrix_valid.tsv --output reports/test_run
```

Expected outputs:
- `report.html`
- `metadata.inferred.csv`

## Input options
- `validate`: requires at least one of `--metadata` or `--matrix`
- `fix`: requires at least one of `--metadata`, `--matrix`, or `--manifest`
- Supported tabular file formats: `.csv`, `.tsv`, `.txt` (`.txt` is treated as tab-delimited)

| Option | Purpose | Notes |
|---|---|---|
| `--metadata FILE` | Sample sheet with one row per sample | Must include `sample_id` and your condition column (default: `condition`) |
| `--matrix FILE` | Feature-by-sample table | Sample IDs are read from sample columns |
| `--manifest FILE` | Sample file inventory table | Used to compare metadata sample IDs with file-level sample IDs |
| `--sample COLUMN` | Manifest sample-ID column name | Default: `sample_id` |
| `--condition COLUMN` | Main analysis grouping variable | Default: `condition` |
| `--batch COLUMN` | Technical grouping variable | Example: sequencing run or center |
| `--pair COLUMN` | Pair/block variable | For paired or blocked designs |
| `--covars COLS...` | Extra model columns for design checks | Provide as space-separated names |
| `--contrast A_vs_B` | Target comparison format | Example: `Treated_vs_Control` |
| `--report NAME` | Output report filename | `validate` only; `.html` is added if omitted |

## Outputs
### `validate`
Writes:
- `report.html` (or your `--report` filename)
- `metadata.inferred.csv` (only when `--metadata` is omitted)

Behavior:
- Provide at least one of `--metadata` or `--matrix`.
- If you provide only `--matrix`, expready builds metadata from matrix sample columns and saves it as `metadata.inferred.csv`.
- If you provide `--manifest`, expready compares metadata `sample_id` values to the manifest column set by `--sample` (default `sample_id`).
- If the manifest sample column is missing, validation returns a blocking issue (`FAIL`).
- `validate` expects sample IDs to match exactly across files.

Examples:
```bash
# matrix-only validation (metadata inferred automatically)
python -m expready validate --matrix counts.tsv --output reports/validate_matrix_only

# metadata + matrix validation
python -m expready validate --metadata metadata.csv --matrix counts.tsv --output reports/validate_meta_matrix

# metadata + manifest validation (manifest column is named "rownames")
python -m expready validate --metadata metadata.csv --manifest manifest.tsv --sample rownames --output reports/validate_meta_manifest
```

### `fix`
Writes:
- `metadata.fixed.csv` (if `--metadata` is provided, or inferred from `--matrix`)
- `manifest.fixed.csv` (if manifest is provided)
- `fix.log`

Behavior:
- `--metadata` is optional.
- With `--matrix` and no `--metadata`, metadata is inferred and saved to `metadata.fixed.csv`.
- With only `--manifest`, no `metadata.fixed.csv` is written.
- `fix` does not map different sample-ID schemes. It only does safe cleanup (trim spaces, standardize empty-like values, remove fully empty rows).

Examples:
```bash
# metadata fixed + manifest fixed + fix.log
python -m expready fix --metadata metadata.csv --manifest manifest.tsv --output reports/fix_meta_manifest

# metadata inferred from matrix, then fixed + fix.log
python -m expready fix --matrix counts.tsv --output reports/fix_from_matrix

# only manifest fixed + fix.log
python -m expready fix --manifest manifest.tsv --output reports/fix_manifest_only
```

## Status and severity
- Overall status
  - `PASS`: no blocking issues found
  - `FAIL`: one or more blocking issues found
- Issue levels
  - `Extreme`: blocking
  - `Moderate`: important, non-blocking
  - `None`: informational

## Help
```bash
python -m expready --help
python -m expready validate --help
python -m expready fix --help
```
