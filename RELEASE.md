# Release Checklist

This document is the command-first release process for `expready`.

## 1. Pre-release validation

Run tests:
```bash
PYTHONPATH=src python -m pytest -q
```

Build distribution artifacts:
```bash
python -m build
```

Validate package metadata/rendering:
```bash
python -m twine check dist/*
```

Optional local install smoke test:
```bash
python -m pip install --force-reinstall dist/*.whl
expready --help
```

## 2. Bump version

Update version in both files:
- `pyproject.toml` -> `[project].version`
- `src/expready/__init__.py` -> `__version__`

Update `CHANGELOG.md`:
- Move release notes from `[Unreleased]` into a dated version section.
- Keep a fresh `[Unreleased]` section for next cycle.

Commit:
```bash
git add pyproject.toml src/expready/__init__.py CHANGELOG.md
git commit -m "release: vX.Y.Z"
git push
```

## 3. Tag and GitHub release

Create and push tag:
```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

Create GitHub release from tag `vX.Y.Z`:
- Title: `vX.Y.Z`
- Include key highlights from `CHANGELOG.md`

## 4. Publish to PyPI

Authenticate with PyPI token (recommended via `TWINE_PASSWORD` with `__token__` user).

Upload artifacts:
```bash
python -m twine upload dist/*
```

Verify install from PyPI:
```bash
python -m pip install --upgrade expready==X.Y.Z
expready --help
```

## 5. Post-release housekeeping

Start next cycle:
- Add new notes under `## [Unreleased]` in `CHANGELOG.md`.
- If needed, increment to next development version.
