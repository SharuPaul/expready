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

## Quick start
Run from project root.

Validate with matrix only:
```bash
python -m expready validate --matrix examples/matrix_valid.tsv --output reports/run1
```

Validate with metadata + matrix:
```bash
python -m expready validate --metadata examples/metadata_valid.csv --matrix examples/matrix_valid.tsv --output reports/run2
```

Validate with metadata + manifest:
```bash
python -m expready validate --metadata examples/metadata_valid.csv --manifest examples/manifest_valid.tsv --sample_col sample_id --output reports/run3
```

Run safe cleanup:
```bash
python -m expready fix --metadata examples/metadata_valid.csv --manifest examples/manifest_valid.tsv --output reports/fix1
```

## Input options
- Required: at least one of `--metadata` or `--matrix`
- Supported tabular file formats: `.csv`, `.tsv`, `.txt` (`.txt` is treated as tab-delimited)
- Common options
  - `--condition` (default: `condition`)
  - `--batch`
  - `--pair`
  - `--covars`
  - `--contrast` (`GroupA_vs_GroupB`)
  - `--manifest`
  - `--sample_col` (default: `sample_id`)
  - `--report` (validate only)

## Outputs
`validate` writes:
- `report.html` (or your `--report` filename)
- `metadata.inferred.csv` (only when `--metadata` is omitted)

`validate` input behavior (important):
- You must provide at least one of `--metadata` or `--matrix`.
- If you run `validate` with `--matrix` and no `--metadata`, metadata is inferred from matrix sample columns and written to `metadata.inferred.csv`.
- Manifest checks compare metadata `sample_id` values to the manifest sample column (`--sample_col`, default `sample_id`).
- If the manifest sample column is missing, validation returns a blocking issue (`FAIL`).
- `validate` does not auto-map different sample-ID schemes between files.

Examples:
```bash
# matrix-only validation (metadata inferred automatically)
python -m expready validate --matrix counts.tsv --output reports/validate_matrix_only

# metadata + matrix validation
python -m expready validate --metadata metadata.csv --matrix counts.tsv --output reports/validate_meta_matrix

# metadata + manifest validation (use correct manifest sample column)
python -m expready validate --metadata metadata.csv --manifest manifest.tsv --sample_col rownames --output reports/validate_meta_manifest
```

`fix` writes:
- `metadata.fixed.csv` (if `--metadata` is provided, or inferred from `--matrix`)
- `manifest.fixed.csv` (if manifest is provided)
- `fix.log`

`fix` input behavior (important):
- `--metadata` is optional.
- If you run `fix` with `--matrix` and no `--metadata`, metadata is inferred from matrix sample columns, then written to `metadata.fixed.csv`.
- If you run `fix` with only `--manifest`, `metadata.fixed.csv` is not created (because there is no metadata input and no matrix to infer from).
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
