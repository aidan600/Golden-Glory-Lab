"""Run the complete reusable PoB importer PROOF suite."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import tempfile
import textwrap
import zlib
from pathlib import Path
from xml.parsers import expat

ROOT = Path(__file__).resolve().parents[2]

PRODUCTION_SMOKE_BOOTSTRAP = textwrap.dedent(
    r"""
    import os
    import pathlib
    import sys

    target = pathlib.Path(sys.argv[1]).resolve()
    original_path = tuple(sys.path)
    sys.path.insert(0, str(target))

    assert sys.flags.isolated, sys.flags
    assert sys.flags.no_site, sys.flags
    assert sys.flags.ignore_environment, sys.flags
    assert "PYTHONPATH" not in os.environ, os.environ.get("PYTHONPATH")
    assert "" not in sys.path, sys.path
    assert str(pathlib.Path.cwd().resolve()) not in sys.path, sys.path
    assert all(
        path in original_path or path == str(target)
        for path in sys.path
    ), sys.path
    assert not [
        path
        for path in sys.path
        if "site-packages" in pathlib.Path(path).parts
        or "dist-packages" in pathlib.Path(path).parts
    ], sys.path

    import golden_glory_lab.pob_import as pob_import

    module_path = pathlib.Path(pob_import.__file__).resolve()
    assert module_path.is_relative_to(target), module_path
    metadata_files = list(target.glob("golden_glory_lab-*.dist-info/METADATA"))
    assert len(metadata_files) == 1, metadata_files
    requires_dist = [
        line
        for line in metadata_files[0].read_text(encoding="utf-8").splitlines()
        if line.startswith("Requires-Dist:")
    ]
    assert not requires_dist, requires_dist
    result = pob_import.importPobRawXml("<PathOfBuilding/>")
    assert result["status"] == "success", result
    print(f"installed production import: {module_path}")
    print("installed production Requires-Dist: []")
    print(f"isolated production sys.path: {sys.path!r}")
    """
)

PROOF_BOOTSTRAP = textwrap.dedent(
    r"""
    import importlib
    import importlib.metadata
    import json
    import os
    import pathlib
    import sys
    import unittest

    source_root = pathlib.Path(sys.argv[1]).resolve()
    dependency_root = pathlib.Path(sys.argv[2]).resolve()
    tests_root = pathlib.Path(sys.argv[3]).resolve()
    mode = sys.argv[4]
    original_path = tuple(sys.path)
    explicit_paths = (str(source_root), str(dependency_root), str(tests_root))
    for path in reversed(explicit_paths):
        sys.path.insert(0, path)

    def assert_isolated_path() -> None:
        assert sys.flags.isolated, sys.flags
        assert sys.flags.no_site, sys.flags
        assert sys.flags.ignore_environment, sys.flags
        assert "PYTHONPATH" not in os.environ, os.environ.get("PYTHONPATH")
        assert "" not in sys.path, sys.path
        assert str(pathlib.Path.cwd().resolve()) not in sys.path, sys.path
        assert all(
            path in original_path or path in explicit_paths
            for path in sys.path
        ), sys.path
        assert not [
            path
            for path in sys.path
            if (
                "site-packages" in pathlib.Path(path).parts
                or "dist-packages" in pathlib.Path(path).parts
            )
            and not pathlib.Path(path).resolve().is_relative_to(dependency_root)
        ], sys.path

    assert_isolated_path()
    expected_modules = {
        "attrs": "attrs",
        "jsonschema": "jsonschema",
        "jsonschema_specifications": "jsonschema-specifications",
        "referencing": "referencing",
        "rpds": "rpds-py",
    }
    expected_versions = {
        "attrs": "26.1.0",
        "jsonschema": "4.26.0",
        "jsonschema-specifications": "2025.9.1",
        "referencing": "0.37.0",
        "rpds-py": "2026.6.3",
    }
    if sys.version_info < (3, 13):
        expected_modules["typing_extensions"] = "typing-extensions"
        expected_versions["typing-extensions"] = "4.15.0"
    else:
        unexpected_typing_extensions = sorted(
            path.name for path in dependency_root.glob("typing_extensions*")
        )
        assert not unexpected_typing_extensions, unexpected_typing_extensions

    module_locations = {}
    for module_name, distribution_name in expected_modules.items():
        module = importlib.import_module(module_name)
        module_path = pathlib.Path(module.__file__).resolve()
        assert module_path.is_relative_to(dependency_root), (
            distribution_name,
            module_path,
        )
        module_locations[distribution_name] = str(module_path)

    production_module = importlib.import_module("golden_glory_lab.pob_import")
    production_module_path = pathlib.Path(production_module.__file__).resolve()
    assert production_module_path.is_relative_to(source_root), production_module_path

    installed_versions = {
        distribution_name: importlib.metadata.version(distribution_name)
        for distribution_name in expected_versions
    }
    assert installed_versions == expected_versions, installed_versions
    print(
        json.dumps(
            {
                "proofDependencyModules": module_locations,
                "proofDependencyVersions": installed_versions,
                "isolatedProofSysPath": sys.path,
                "productionSourceModule": str(production_module_path),
            },
            indent=2,
            sort_keys=True,
        )
    )

    if mode == "tests":
        suite = unittest.defaultTestLoader.discover(
            start_dir=str(tests_root),
            pattern="test*.py",
            top_level_dir=str(tests_root),
        )
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        assert_isolated_path()
        if not result.wasSuccessful():
            raise SystemExit(1)
    elif mode != "check":
        raise AssertionError(f"unknown isolated bootstrap mode: {mode}")
    """
)


def displayed_command(command: tuple[str, ...]) -> str:
    visible = list(command)
    if "-c" in visible:
        bootstrap_index = visible.index("-c") + 1
        visible[bootstrap_index] = "<isolated bootstrap>"
    return " ".join(visible)


def run(*command: str, env: dict[str, str] | None = None) -> None:
    print(f"+ {displayed_command(command)}", flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def isolated_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "PYTHONUSERBASE"):
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def isolated_proof_command(
    source_root: Path,
    dependency_root: Path,
    tests_root: Path,
    mode: str,
) -> tuple[str, ...]:
    return (
        sys.executable,
        "-I",
        "-S",
        "-c",
        PROOF_BOOTSTRAP,
        str(source_root),
        str(dependency_root),
        str(tests_root),
        mode,
    )


def prove_conditional_dependency_is_required(
    source_root: Path,
    dependency_root: Path,
    tests_root: Path,
    environment: dict[str, str],
) -> None:
    if sys.version_info >= (3, 13):
        print(
            "typing-extensions omission self-check: not applicable on Python 3.13+",
            flush=True,
        )
        return

    candidates = [
        dependency_root / "typing_extensions.py",
        dependency_root / "typing_extensions",
    ]
    import_artifacts = [path for path in candidates if path.exists()]
    if len(import_artifacts) != 1:
        raise AssertionError(
            f"expected one typing_extensions import artifact, found {import_artifacts}"
        )
    import_artifact = import_artifacts[0]
    hidden_artifact = import_artifact.with_name(f"{import_artifact.name}.proof-hidden")
    import_artifact.replace(hidden_artifact)
    try:
        command = isolated_proof_command(
            source_root, dependency_root, tests_root, "check"
        )
        print(
            f"+ {displayed_command(command)}  # expected failure", flush=True
        )
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if completed.returncode == 0:
            raise AssertionError(
                "isolated dependency check passed without typing_extensions"
            )
        failure_summary = completed.stdout.rstrip().splitlines()[-1]
        print(
            "typing-extensions omission self-check failed as required: "
            f"exit {completed.returncode} ({failure_summary})",
            flush=True,
        )
    finally:
        hidden_artifact.replace(import_artifact)


def main() -> int:
    print(f"Python {platform.python_version()}", flush=True)
    print(f"zlib {zlib.ZLIB_RUNTIME_VERSION}", flush=True)
    print(f"Expat {expat.EXPAT_VERSION}", flush=True)
    environment = isolated_environment()
    run(
        sys.executable,
        "-I",
        "-S",
        "-m",
        "compileall",
        "-q",
        "src",
        "proofs",
        "tests",
        env=environment,
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
        run(
            sys.executable,
            "-I",
            "-S",
            "-c",
            PRODUCTION_SMOKE_BOOTSTRAP,
            str(install_target),
            env=environment,
        )
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
        source_root = ROOT / "src"
        tests_root = ROOT / "tests"
        run(
            *isolated_proof_command(
                source_root, proof_dependencies, tests_root, "check"
            ),
            env=environment,
        )
        prove_conditional_dependency_is_required(
            source_root,
            proof_dependencies,
            tests_root,
            environment,
        )
        run(
            *isolated_proof_command(
                source_root, proof_dependencies, tests_root, "tests"
            ),
            env=environment,
        )
    run("node", "scripts/validate/check_repository.mjs", env=environment)
    run("git", "diff", "--check", env=environment)
    print("PoB importer PROOF suite passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
