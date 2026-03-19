from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class StudyConfig:
    metadata_path: Optional[Path]
    metadata_sample_column: str
    condition_column: str
    output_dir: Path
    matrix_path: Optional[Path] = None
    manifest_path: Optional[Path] = None
    manifest_sample_column: str = "sample_id"
    batch_column: Optional[str] = None
    pair_column: Optional[str] = None
    covariates: list[str] = field(default_factory=list)
    contrast: Optional[str] = None
