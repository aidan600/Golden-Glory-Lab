"""Build the one-file Golden Glory Calculator Windows executable.

Uses the pinned desktop packaging environment from
requirements/desktop-packaging-proof.txt. Does not commit the executable.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements" / "desktop-packaging-proof.txt"
PACKAGE_NAME = "GoldenGloryCalculator"
EXPECTED_PACKAGING_DEPENDENCIES = {
    "altgraph": "0.17.5",
    "packaging": "26.2",
    "pefile": "2024.8.26",
    "pyinstaller": "6.21.0",
    "pyinstaller-hooks-contrib": "2026.6",
    "pywin32-ctypes": "0.2.3",
    "setuptools": "75.8.2",
}
FLAME_LINK_TABLE = "flame-link-level-table-v1.json"
EXPECTED_FLAME_LINK_SHA256 = (
    "e2cf21212e0ae6e1c3a23cab5ea94e723b69bf0bae89bf0c6906740c71c4a70c"
)


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _run(
    command: Sequence[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> None:
    print(f"+ {subprocess.list2cmdline(list(command))}", flush=True)
    completed = subprocess.run(list(command), cwd=cwd, env=env, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed with exit {completed.returncode}: "
            f"{subprocess.list2cmdline(list(command))}"
        )


def _build_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "PYTHONUSERBASE"):
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def _venv_python(environment_root: Path) -> Path:
    return environment_root / "Scripts" / "python.exe"


def _git_sha() -> str:
    completed = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip()


def _verify_packaging_pins(python: Path, *, cwd: Path, env: dict[str, str]) -> None:
    script = (
        "import importlib.metadata as metadata\n"
        f"expected = {EXPECTED_PACKAGING_DEPENDENCIES!r}\n"
        "for name, version in expected.items():\n"
        "    found = metadata.version(name)\n"
        "    if found != version:\n"
        "        raise SystemExit(f'{name}: expected {version}, found {found}')\n"
        "print('packaging pins ok')\n"
    )
    _run((str(python), "-I", "-c", script), cwd=cwd, env=env)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build GoldenGloryCalculator.exe (PyInstaller one-file)."
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Destination path for GoldenGloryCalculator.exe",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the output file if it already exists.",
    )
    parser.add_argument(
        "--keep-work",
        action="store_true",
        help="Keep the temporary build directory (for debugging).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if sys.platform != "win32":
        raise SystemExit("build_calculator_exe.py is Windows-only")

    args = build_parser().parse_args(argv)
    output = args.output.expanduser().resolve()
    if output.exists() and not args.overwrite:
        raise SystemExit(
            f"output already exists (pass --overwrite to replace): {output}"
        )
    if output.suffix.lower() != ".exe":
        raise SystemExit("output path must end with .exe")
    if not REQUIREMENTS.is_file():
        raise SystemExit(f"missing packaging requirements: {REQUIREMENTS}")

    source_sha = _git_sha()
    build_environment = _build_environment()
    temp_root = Path(tempfile.mkdtemp(prefix="ggl-calculator-exe-"))
    try:
        environment_root = temp_root / "venv"
        distribution_root = temp_root / "dist"
        work_root = temp_root / "work"
        spec_root = temp_root / "spec"
        build_cwd = temp_root / "cwd"
        for path in (distribution_root, work_root, spec_root, build_cwd):
            path.mkdir(parents=True, exist_ok=True)

        print(f"creating packaging venv at {environment_root}", flush=True)
        venv.EnvBuilder(with_pip=True, clear=True).create(environment_root)
        python = _venv_python(environment_root)
        if not python.is_file():
            raise RuntimeError(f"venv python missing: {python}")

        _run(
            (
                str(python),
                "-I",
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                "--upgrade",
                "pip",
            ),
            cwd=build_cwd,
            env=build_environment,
        )
        _run(
            (
                str(python),
                "-I",
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                "-r",
                str(REQUIREMENTS),
            ),
            cwd=build_cwd,
            env=build_environment,
        )
        _verify_packaging_pins(python, cwd=build_cwd, env=build_environment)
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
                str(ROOT),
            ),
            cwd=build_cwd,
            env=build_environment,
        )

        site_packages = environment_root / "Lib" / "site-packages"
        package = site_packages / "golden_glory_lab"
        launcher = package / "desktop" / "launcher.py"
        table_path = package / "runtime_data" / FLAME_LINK_TABLE
        icons_root = package / "desktop" / "icons"
        if not launcher.is_file():
            raise RuntimeError(f"installed launcher missing: {launcher}")
        if not table_path.is_file():
            raise RuntimeError(f"Flame Link table missing: {table_path}")
        if not icons_root.is_dir():
            raise RuntimeError(f"breakdown icons missing: {icons_root}")
        icon_files = sorted(icons_root.glob("*.png"))
        if len(icon_files) < 12:
            raise RuntimeError(
                f"expected at least 12 breakdown icon PNGs, found {len(icon_files)}"
            )
        table_digest = _sha256_file(table_path)
        if table_digest != EXPECTED_FLAME_LINK_SHA256:
            raise RuntimeError(
                f"Flame Link table digest mismatch: {table_digest} != "
                f"{EXPECTED_FLAME_LINK_SHA256}"
            )

        _run(
            (
                str(python),
                "-I",
                "-m",
                "PyInstaller",
                "--clean",
                "--noconfirm",
                "--noupx",
                "--onefile",
                "--windowed",
                "--name",
                PACKAGE_NAME,
                "--hidden-import",
                "golden_glory_lab.runtime_data",
                "--hidden-import",
                "golden_glory_lab.desktop.icons",
                "--collect-all",
                "tkinter",
                "--distpath",
                str(distribution_root),
                "--workpath",
                str(work_root),
                "--specpath",
                str(spec_root),
                "--add-data",
                f"{table_path}{os.pathsep}golden_glory_lab/runtime_data",
                "--add-data",
                f"{icons_root}{os.pathsep}golden_glory_lab/desktop/icons",
                str(launcher),
            ),
            cwd=build_cwd,
            env=build_environment,
        )

        built = distribution_root / f"{PACKAGE_NAME}.exe"
        if not built.is_file():
            raise RuntimeError(f"PyInstaller did not produce {built}")

        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            output.unlink()
        shutil.copy2(built, output)

        size = output.stat().st_size
        digest = _sha256_file(output)
        print("", flush=True)
        print(f"executable path: {output}", flush=True)
        print(f"size: {size} bytes", flush=True)
        print(f"SHA-256: {digest}", flush=True)
        print(f"source git SHA: {source_sha}", flush=True)
        return 0
    finally:
        if args.keep_work:
            print(f"kept work directory: {temp_root}", flush=True)
        else:
            shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
