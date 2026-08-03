"""Run the complete reusable PoB importer PROOF suite."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path
from xml.parsers import expat

ROOT = Path(__file__).resolve().parents[2]


def run(*command: str, env: dict[str, str] | None = None) -> None:
    print(f"+ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def main() -> int:
    print(f"Python {platform.python_version()}", flush=True)
    print(f"zlib {zlib.ZLIB_RUNTIME_VERSION}", flush=True)
    print(f"Expat {expat.EXPAT_VERSION}", flush=True)
    environment = os.environ.copy()
    source_environment = {**environment, "PYTHONPATH": str(ROOT / "src")}
    run(
        sys.executable,
        "-m",
        "compileall",
        "-q",
        "src",
        "proofs",
        "tests",
        env=source_environment,
    )
    with tempfile.TemporaryDirectory(prefix="ggl-pob-proof-") as proof_target:
        target_root = Path(proof_target)
        install_target = target_root / "production"
        proof_dependencies = target_root / "proof-dependencies"
        run(
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-deps",
            "--target",
            str(install_target),
            ".",
            env=environment,
        )
        smoke = (
            "import sys; "
            f"sys.path.insert(0, {str(install_target)!r}); "
            "from golden_glory_lab.pob_import import importPobRawXml; "
            "result = importPobRawXml('<PathOfBuilding/>'); "
            "assert result['status'] == 'success', result"
        )
        run(sys.executable, "-I", "-c", smoke, env=environment)
        run(
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-deps",
            "--target",
            str(proof_dependencies),
            "-r",
            "requirements/pob-import-proof.txt",
            env=environment,
        )
        test_environment = {
            **environment,
            "PYTHONPATH": os.pathsep.join(
                (str(ROOT / "src"), str(proof_dependencies))
            ),
        }
        run(
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-v",
            env=test_environment,
        )
    run("node", "scripts/validate/check_repository.mjs", env=environment)
    run("git", "diff", "--check", env=environment)
    print("PoB importer PROOF suite passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
