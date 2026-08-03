"""Run the complete reusable PoB importer PROOF suite."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(*command: str, env: dict[str, str] | None = None) -> None:
    print(f"+ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def main() -> int:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    run(
        sys.executable,
        "-m",
        "compileall",
        "-q",
        "src",
        "proofs",
        "tests",
        env=environment,
    )
    with tempfile.TemporaryDirectory(prefix="ggl-pob-install-") as install_target:
        run(
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-deps",
            "--no-build-isolation",
            "--target",
            install_target,
            ".",
            env=environment,
        )
    run(
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
        "-v",
        env=environment,
    )
    run("node", "scripts/validate/check_repository.mjs", env=environment)
    run("git", "diff", "--check", env=environment)
    print("PoB importer PROOF suite passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
