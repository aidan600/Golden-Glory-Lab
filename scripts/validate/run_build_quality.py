"""Run Ruff from an exact, disposable BUILD-001 quality environment."""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
import venv
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = ROOT / "requirements" / "build-quality.txt"
EXPECTED_VERSION = "0.15.22"


def _environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "PYTHONUSERBASE"):
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def _run(command: Sequence[str], *, env: dict[str, str]) -> None:
    print(f"+ {subprocess.list2cmdline(command)}", flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install and run the exact pinned Ruff BUILD-001 gate."
    )
    parser.add_argument(
        "--temp-root",
        type=Path,
        default=Path(tempfile.gettempdir()),
        help="Existing parent for the disposable quality environment.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.temp_root.is_dir():
        raise FileNotFoundError(f"temporary parent does not exist: {args.temp_root}")
    expected_requirement = f"ruff=={EXPECTED_VERSION}\n"
    if REQUIREMENTS.read_text(encoding="utf-8") != expected_requirement:
        raise AssertionError("build-quality.txt must contain only the exact Ruff pin")

    environment = _environment()
    with tempfile.TemporaryDirectory(
        prefix="golden-glory-lab-ruff-",
        dir=args.temp_root,
    ) as temporary:
        environment_root = Path(temporary) / "environment"
        venv.EnvBuilder(with_pip=True, clear=True).create(environment_root)
        python = environment_root / "Scripts" / "python.exe"
        ruff = environment_root / "Scripts" / "ruff.exe"
        _run(
            (
                str(python),
                "-I",
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                "--no-deps",
                "--requirement",
                str(REQUIREMENTS),
            ),
            env=environment,
        )
        completed = subprocess.run(
            (str(ruff), "--version"),
            cwd=ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        observed = completed.stdout.strip()
        if observed != f"ruff {EXPECTED_VERSION}":
            raise AssertionError(f"unexpected Ruff version: {observed}")
        print(
            f"isolated Ruff: {observed} at {ruff}",
            flush=True,
        )
        _run((str(ruff), "check", ".", "--no-cache"), env=environment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
