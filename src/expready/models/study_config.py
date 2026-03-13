from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class StudyConfig:
    metadata_path: Path | None
    condition_column: str
    output_dir: Path
    matrix_path: Path | None = None
    manifest_path: Path | None = None
    manifest_sample_column: str = "sample_id"
    batch_column: str | None = None
    pair_column: str | None = None
    covariates: list[str] = field(default_factory=list)
    contrast: str | None = None
