from __future__ import annotations

from pathlib import Path

from expready.loaders.table_loader import load_table
from expready.models import Table


def load_metadata(path: Path) -> Table:
    return load_table(path)
