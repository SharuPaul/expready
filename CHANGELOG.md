# Changelog

All notable changes to `expready` are documented in this file.

The format follows Keep a Changelog, and this project uses SemVer.

## [Unreleased]

### Added
- Fail-fast input-contract validation for `validate` (no report on input errors).
- Manifest path validation support (`--manifest-path`, `--check-paths`).
- UTF-8 BOM-safe table loading (`utf-8-sig`).
- Additional tests for malformed inputs and CLI fail-fast behavior.
- CI workflow for tests/build/twine checks and release smoke test.

### Changed
- Matrix-only inferred metadata behavior tuned to provide a fail-path demo in docs.
- CLI preflight validation logic extracted into `src/expready/preflight.py`.
- Package metadata license field updated to SPDX string (`MIT`).

### Fixed
- README behavior notes aligned with fail-fast validation behavior.

## [0.1.0] - 2026-04-10

### Added
- Initial public release.
- `validate` command for metadata/design/cross-file checks.
- `fix` command for safe metadata/manifest cleanup.
- HTML reporting with severity labels and action guidance.
