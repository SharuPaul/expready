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

## Input file requirements
Supported formats for all inputs: `.csv`, `.tsv`, `.txt`.
Delimiter handling is flexible: expready auto-detects common delimiters (comma, tab, semicolon, pipe, or whitespace-separated columns).
All input files must include a header row (column names in the first row). Headerless files are not supported.

`metadata` file (`--metadata`):
- One row per sample.
- Required columns:
  - Metadata sample-ID column (default `sample_id`, or the column passed via `--meta-id`)
  - Condition column (default `condition`, or the column passed via `--condition`)
- If you pass `--batch`, `--pair`, or `--covars`, those columns must exist in metadata.
- Metadata sample-ID values should be unique and non-empty.

`matrix` file (`--matrix`):
- Feature-by-sample table (rows = features, sample IDs in columns).
- Sample column names should match metadata sample-ID values exactly when both files are used.
- If metadata is not provided, `expready` infers metadata from matrix sample columns.

`manifest` file (`--manifest`):
- Sample inventory table (for example, sample ID + file path columns).
- Must contain the sample-ID column specified by `--sample` (default `sample_id`).
- Sample IDs in this column should match metadata sample-ID values exactly.

Minimal examples:

Metadata (`metadata.csv`)
```csv
sample_id,condition,batch
S1,Control,B1
S2,Control,B1
S3,Treated,B2
S4,Treated,B2
```

Matrix (`matrix.tsv`)
```tsv
gene_id	S1	S2	S3	S4
GeneA	10	12	4	6
GeneB	0	1	8	9
```

Manifest (`manifest.tsv`)
```tsv
sample_id	file_path
S1	/data/S1.fastq.gz
S2	/data/S2.fastq.gz
S3	/data/S3.fastq.gz
S4	/data/S4.fastq.gz
```

## Test runs
Pass example (metadata + matrix):
```bash
expready validate --metadata examples/metadata_valid.csv --matrix examples/matrix_valid.tsv --output reports/test_pass --report pass_report
```
Expected:
- Console shows `Status: PASS`
- Writes `reports/test_pass/pass_report.html`

Fail example (matrix only):
```bash
expready validate --matrix examples/matrix_valid.tsv --output reports/test_fail --report fail_report
```
Expected:
- Console may show `Status: FAIL` (this is expected for this demo path)
- Writes `reports/test_fail/fail_report.html`
- Writes `reports/test_fail/metadata.inferred.csv`

## Input options
- `validate`: requires at least one of `--metadata` or `--matrix`
- `fix`: requires at least one of `--metadata`, `--matrix`, or `--manifest`
- Supported tabular file formats: `.csv`, `.tsv`, `.txt` (delimiter is auto-detected)

| Option | Purpose | Notes |
|---|---|---|
| `--metadata FILE` | Sample sheet with one row per sample | Must include your metadata sample-ID column (`--meta-id`) and condition column (`--condition`) |
| `--matrix FILE` | Feature-by-sample table | Sample IDs are read from sample columns |
| `--manifest FILE` | Sample file inventory table | Used to compare metadata sample IDs with file-level sample IDs |
| `--meta-id COLUMN` | Column name in metadata that contains sample IDs | Default: `sample_id` |
| `--sample COLUMN` | Column name in manifest that contains sample IDs | Default: `sample_id` |
| `--condition COLUMN` | Main analysis grouping variable | Default: `condition` |
| `--batch COLUMN` | Technical grouping variable | Example: sequencing run or center |
| `--pair COLUMN` | Pair/block variable | For paired or blocked designs |
| `--covars COLS...` | Extra model columns for design checks | Provide as space-separated names |
| `--contrast A_vs_B` | Target comparison format | Example: `Treated_vs_Control` |
| `--report NAME` | Output report filename | `validate` only; `.html` is added if omitted |
| `--format FMT` | Fixed table output format | `fix` only; `tsv` or `csv` (default: `tsv`) |

## Outputs
### `validate`
Writes:
- `report.html` (or your `--report` filename)
- `metadata.inferred.csv` (only when `--metadata` is omitted)

Behavior:
- Provide at least one of `--metadata` or `--matrix`.
- If you provide only `--matrix`, expready builds metadata from matrix sample columns and saves it as `metadata.inferred.csv`.
- If you provide `--manifest`, expready compares metadata sample-ID values (from `--meta-id`, default `sample_id`) to the manifest column set by `--sample` (default `sample_id`).
- `--meta-id` is for metadata; `--sample` is for manifest.
- If the manifest sample column is missing, validation returns a blocking issue (`FAIL`).
- `validate` expects sample IDs to match exactly across files.

Examples:
```bash
# matrix-only validation (metadata inferred automatically)
expready validate --matrix counts.tsv --output reports/validate_matrix_only

# metadata + matrix validation
expready validate --metadata metadata.csv --matrix counts.tsv --output reports/validate_meta_matrix

# metadata + manifest validation (manifest column is named "rownames")
expready validate --metadata metadata.csv --manifest manifest.tsv --sample rownames --output reports/validate_meta_manifest
```

### `fix`
Writes:
- `metadata.fixed.<fmt>` (if `--metadata` is provided, or inferred from `--matrix`)
- `manifest.fixed.<fmt>` (if manifest is provided)
- `fix.log`

Behavior:
- `--metadata` is optional.
- With `--matrix` and no `--metadata`, metadata is inferred and saved to `metadata.fixed.<fmt>`.
- With only `--manifest`, no `metadata.fixed.<fmt>` is written.
- `--format` controls fixed table format and extension (`tsv` -> `.tsv`, `csv` -> `.csv`).
- `fix` does not map different sample-ID schemes. It only does safe cleanup (trim spaces, standardize empty-like values, remove fully empty rows).

Examples:
```bash
# metadata fixed + manifest fixed + fix.log
expready fix --metadata metadata.csv --manifest manifest.tsv --output reports/fix_meta_manifest

# metadata inferred from matrix, then fixed + fix.log
expready fix --matrix counts.tsv --output reports/fix_from_matrix

# only manifest fixed + fix.log
expready fix --manifest manifest.tsv --output reports/fix_manifest_only

# optional: write fixed tables as CSV instead of the default TSV
expready fix --metadata metadata.csv --manifest manifest.tsv --output reports/fix_csv --format csv
```

## Understanding outputs and issues
What each output file means:
- `report.html`: main validation report with status, issue list, and suggested fixes.
- `metadata.inferred.csv`: metadata generated from matrix sample columns (only when metadata input is omitted).
- `metadata.fixed.<fmt>`: cleaned metadata written by `fix` (`fmt` is `tsv` by default, or `csv` if selected).
- `manifest.fixed.<fmt>`: cleaned manifest written by `fix` (`fmt` is `tsv` by default, or `csv` if selected).
- `fix.log`: summary of what `fix` changed (empty-like values standardized, fully empty rows removed).

How to read validation status:
- `PASS`: no blocking issues were found.
- `FAIL`: at least one blocking issue was found.

How to prioritize issues in `report.html`:
- `Extreme`: blocking issue; fix these first.
- `Moderate`: non-blocking but important quality risk.
- `None`: informational check passed/no action required.

Issue sections:
- `Metadata`: schema and sample-ID quality checks.
- `Design`: group structure and model-readiness checks.
- `Cross-file`: sample-ID consistency across metadata, matrix, and manifest.

## Report wording guide
Common report language and what it means:
- `Blocking issue`: an issue severe enough to set overall status to `FAIL`.
- `Some metadata sample IDs are missing in the matrix`: sample IDs exist in metadata but are not found in matrix sample columns.
- `Some matrix sample IDs are not listed in metadata`: sample IDs exist in matrix columns but not in metadata.
- `Some metadata sample IDs are missing in the manifest`: sample IDs exist in metadata but are not found in the manifest sample-ID column.
- `Manifest sample-ID column was not found`: the column passed via `--sample` does not exist in manifest.
- `Input file appears to have inconsistent delimiters`: rows do not have a consistent column structure (often caused by mixed tabs/spaces/commas). The report will suggest standardizing delimiters or running `expready fix` and then re-running `validate`.
- `Duplicate sample IDs`: the same metadata sample-ID value appears in more than one metadata row.
- `Required metadata fields are empty`: required columns (like metadata sample ID or condition) contain missing values.
- `Some condition groups have too few replicates`: at least one condition group has fewer than 2 samples.
- `Condition and batch are fully linked`: condition and batch are one-to-one, so their effects cannot be separated.
- `A category value appears only once`: a value in condition, batch, or covariates appears for only one sample.
- `Model setup is too complex for the sample count`: estimated model terms are too many for available samples.

## Help
```bash
expready --help
expready validate --help
expready fix --help
```
