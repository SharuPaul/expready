# Experiment Readiness Checker (`expready`)

`expready` is a CLI tool that checks whether study inputs are analysis-ready before downstream workflows.
It focuses on metadata quality, design quality, and sample-ID consistency across files.

## What it checks
- Metadata quality
  - Required columns
  - Duplicate sample IDs
  - Missing key values
  - Suspicious sample ID formatting
- Design quality
  - At least two condition groups
  - Low replicate groups
  - Batch-condition confounding
  - Pair/block completeness
  - Group imbalance
  - Contrast format and group existence
- Cross-file consistency
  - Metadata sample IDs vs matrix sample columns
  - Metadata sample IDs vs manifest sample column

## Get the code
```bash
git clone https://github.com/SharuPaul/expready.git
cd expready
```

## Commands
- `validate`: run checks and generate an HTML report
- `fix`: apply safe cleanup to metadata/manifest and write fixed files + log

## Test run
```bash
python -m expready validate --matrix examples/matrix_valid.tsv --output reports/test_run
```

Expected outputs:
- `report.html`
- `metadata.inferred.csv`

## Input options
- Required: at least one of `--metadata` or `--matrix`
- Supported tabular file formats: `.csv`, `.tsv`, `.txt` (`.txt` is treated as tab-delimited)

| Option | Purpose | Notes |
|---|---|---|
| `--metadata FILE` | Sample sheet with one row per sample | Must include `sample_id` and your condition column (default: `condition`) |
| `--matrix FILE` | Feature-by-sample table | Sample IDs are read from sample columns |
| `--manifest FILE` | Sample file inventory table | Used to compare metadata sample IDs with file-level sample IDs |
| `--sample COLUMN` | Manifest sample-ID column name | Default: `sample_id`. |
| `--condition COLUMN` | Main analysis grouping variable | Default: `condition` |
| `--batch COLUMN` | Technical grouping variable | Example: sequencing run or center |
| `--pair COLUMN` | Pair/block variable | For paired or blocked designs |
| `--covars COLS...` | Extra model columns for design checks | Provide as space-separated names |
| `--contrast A_vs_B` | Target comparison format | Example: `Treated_vs_Control` |
| `--report NAME` | Output report filename for `validate` | Optional; `.html` is added if omitted |

## Outputs
### `validate`
Writes:
- `report.html` (or your `--report` filename)
- `metadata.inferred.csv` (only when `--metadata` is omitted)

Behavior:
- You must provide at least one of `--metadata` or `--matrix`.
- With `--matrix` and no `--metadata`, metadata is inferred from matrix sample columns and written to `metadata.inferred.csv`.
- Manifest checks compare metadata `sample_id` to the manifest sample column (`--sample`, default `sample_id`).
- If the manifest sample column is missing, validation returns a blocking issue (`FAIL`).
- `validate` does not auto-map different sample-ID schemes between files.

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
- With `--matrix` and no `--metadata`, metadata is inferred and written to `metadata.fixed.csv`.
- With only `--manifest`, `metadata.fixed.csv` is not created.
- `fix` does not map between different sample-ID schemes. It performs safe cleanup only (trim spaces, standardize empty-like values, remove fully empty rows).

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
