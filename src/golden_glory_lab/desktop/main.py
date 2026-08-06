"""Installed GUI entry point for Golden Glory Lab."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .self_test import run_self_test


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Golden Glory Calculator")
    parser.add_argument(
        "--self-test-output",
        type=Path,
        help="Run the noninteractive packaged self-test and write machine-readable JSON.",
    )
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="Open the experimental diagnostic desktop shell instead of the calculator.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.self_test_output is not None:
        return run_self_test(args.self_test_output)
    if args.diagnostic:
        from .app import GoldenGloryApp

        application = GoldenGloryApp()
    else:
        from .calculator_app import GoldenGloryCalculatorApp

        application = GoldenGloryCalculatorApp()
    application.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
