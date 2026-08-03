"""Thin repository harness for the production PoB importer CLI."""

from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from golden_glory_lab.pob_import.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
