"""Build and validate the isolated Windows BUILD-002 desktop package."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[2]
POB_FIXTURE = ROOT / "fixtures" / "pob" / "proof" / "comprehensive.xml"
COPIED_FIXTURE = ROOT / "fixtures" / "item_review" / "copied-items-v1.json"
REQUIREMENTS = ROOT / "requirements" / "desktop-packaging-proof.txt"
PACKAGE_NAME = "GoldenGloryLab"
RUN_COUNT_DEFAULT = 3
EXPECTED_PACKAGING_DEPENDENCIES = {
    "altgraph": "0.17.5",
    "packaging": "26.2",
    "pefile": "2024.8.26",
    "pyinstaller": "6.21.0",
    "pyinstaller-hooks-contrib": "2026.6",
    "pywin32-ctypes": "0.2.3",
    "setuptools": "75.8.2",
}
EXPECTED_RUNTIME_RESOURCE_SHA256 = {
    "enmity-manual-gate-v1.json": (
        "ba1886d67324c75a40997cbd761a81424247ba6995f45898b2b627117190528d"
    ),
    "enmity-reference-v1.json": (
        "949b75154049bb4d1fb0ea55c6f640a43d95f09da26fd4deabf5b51e2303ce19"
    ),
}
BLOCKED_NETWORK_IMPORTS = {
    "aiohttp",
    "ftplib",
    "http.client",
    "http.server",
    "httpx",
    "imaplib",
    "requests",
    "smtplib",
    "socket",
    "ssl",
    "telnetlib",
    "urllib.request",
    "webbrowser",
}


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _tree_sha256(root: Path) -> str:
    hasher = hashlib.sha256()
    for path in sorted(value for value in root.rglob("*") if value.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        hasher.update(len(relative).to_bytes(4, "big"))
        hasher.update(relative)
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
    return hasher.hexdigest()


def _displayed(command: Sequence[str]) -> str:
    visible = list(command)
    if "-c" in visible:
        visible[visible.index("-c") + 1] = "<isolated bootstrap>"
    return subprocess.list2cmdline(visible)


def _run(
    command: Sequence[str],
    *,
    cwd: Path,
    env: dict[str, str],
    capture: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    print(f"+ {_displayed(command)}", flush=True)
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        env=env,
        check=False,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if completed.returncode != 0:
        if capture:
            if completed.stdout:
                sys.stderr.buffer.write(completed.stdout)
            if completed.stderr:
                sys.stderr.buffer.write(completed.stderr)
        raise RuntimeError(
            f"command failed with exit {completed.returncode}: {_displayed(command)}"
        )
    return completed


def _build_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "PYTHONUSERBASE"):
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def _runtime_environment(temp_root: Path) -> dict[str, str]:
    environment: dict[str, str] = {}
    for name in (
        "COMSPEC",
        "NUMBER_OF_PROCESSORS",
        "OS",
        "PATHEXT",
        "PROCESSOR_ARCHITECTURE",
        "SYSTEMROOT",
        "WINDIR",
    ):
        value = os.environ.get(name)
        if value is not None:
            environment[name] = value
    windows_root = environment.get("SYSTEMROOT", r"C:\Windows")
    environment["PATH"] = os.pathsep.join(
        [str(Path(windows_root) / "System32"), windows_root]
    )
    environment["TEMP"] = str(temp_root)
    environment["TMP"] = str(temp_root)
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def _venv_python(environment_root: Path) -> Path:
    return environment_root / "Scripts" / "python.exe"


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _source_network_imports() -> list[dict[str, str]]:
    blocked: list[dict[str, str]] = []
    for path in sorted((ROOT / "src" / "golden_glory_lab").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if any(
                    name == blocked_name or name.startswith(f"{blocked_name}.")
                    for blocked_name in BLOCKED_NETWORK_IMPORTS
                ):
                    blocked.append(
                        {
                            "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                            "module": name,
                        }
                    )
    return blocked


def _verify_installed_package(
    environment_root: Path,
) -> tuple[Path, Path, dict[str, Any]]:
    site_packages = environment_root / "Lib" / "site-packages"
    package = site_packages / "golden_glory_lab"
    launcher = package / "desktop" / "launcher.py"
    if not launcher.is_file():
        raise AssertionError(f"installed desktop launcher is missing: {launcher}")
    metadata_files = list(site_packages.glob("golden_glory_lab-*.dist-info/METADATA"))
    if len(metadata_files) != 1:
        raise AssertionError(f"expected one project metadata file: {metadata_files}")
    requires_dist = [
        line
        for line in metadata_files[0].read_text(encoding="utf-8").splitlines()
        if line.startswith("Requires-Dist:")
    ]
    if requires_dist:
        raise AssertionError(f"unexpected production dependencies: {requires_dist}")
    metadata_lines = metadata_files[0].read_text(encoding="utf-8").splitlines()
    versions = [line.removeprefix("Version: ") for line in metadata_lines if line.startswith("Version: ")]
    if versions != ["0.2.0"]:
        raise AssertionError(f"unexpected installed project version: {versions}")
    resource_root = package / "runtime_data"
    resource_hashes: dict[str, str] = {}
    for name, expected_hash in EXPECTED_RUNTIME_RESOURCE_SHA256.items():
        path = resource_root / name
        if not path.is_file():
            raise AssertionError(f"installed runtime resource is missing: {path}")
        observed_hash = _sha256_file(path)
        if observed_hash != expected_hash:
            raise AssertionError(
                f"installed runtime resource hash mismatch: {name}: {observed_hash}"
            )
        resource_hashes[name] = observed_hash
    return launcher, site_packages, {
        "name": "golden-glory-lab",
        "version": versions[0],
        "requiresDist": requires_dist,
        "metadataPath": str(metadata_files[0].resolve()),
        "runtimeResourceSha256": resource_hashes,
    }


def _verify_packaging_dependencies(
    python: Path,
    *,
    cwd: Path,
    env: dict[str, str],
) -> dict[str, dict[str, str]]:
    bootstrap = r"""
import importlib.metadata
import json
import pathlib
import sys

expected = json.loads(sys.argv[1])
environment_root = pathlib.Path(sys.argv[2]).resolve()
observed = {}
for name, version in sorted(expected.items()):
    distribution = importlib.metadata.distribution(name)
    location = pathlib.Path(distribution.locate_file("")).resolve()
    if not location.is_relative_to(environment_root):
        raise AssertionError((name, location, environment_root))
    installed = distribution.version
    if installed != version:
        raise AssertionError((name, installed, version))
    observed[name] = {"version": installed, "location": str(location)}
print(json.dumps(observed, sort_keys=True))
"""
    completed = _run(
        (
            str(python),
            "-I",
            "-c",
            bootstrap,
            json.dumps(EXPECTED_PACKAGING_DEPENDENCIES, sort_keys=True),
            str(python.parents[1]),
        ),
        cwd=cwd,
        env=env,
        capture=True,
    )
    return json.loads(completed.stdout.decode("utf-8"))


def _verify_tk_runtime(
    python: Path,
    *,
    cwd: Path,
    env: dict[str, str],
) -> dict[str, str]:
    bootstrap = r"""
import json
import pathlib
import sys
import tkinter
import tkinter as tk

root = tk.Tk()
root.withdraw()
root.update_idletasks()
result = {
    "module": str(pathlib.Path(tkinter.__file__).resolve()),
    "tclVersion": str(root.tk.call("info", "patchlevel")),
    "tkVersion": str(root.tk.call("package", "require", "Tk")),
    "python": sys.version.split()[0],
}
root.destroy()
print(json.dumps(result, sort_keys=True))
"""
    completed = _run(
        (str(python), "-I", "-c", bootstrap),
        cwd=cwd,
        env=env,
        capture=True,
    )
    return json.loads(completed.stdout.decode("utf-8"))


def _verify_analysis(work_root: Path, site_packages: Path) -> dict[str, str]:
    analyses = list(work_root.rglob("Analysis-00.toc"))
    if len(analyses) != 1:
        raise AssertionError(f"expected one PyInstaller analysis: {analyses}")
    analysis = analyses[0]
    text = analysis.read_text(encoding="utf-8", errors="strict").casefold()
    text = text.replace("\\\\", "\\")
    expected_sources = {
        "pobImporter": site_packages / "golden_glory_lab" / "pob_import" / "__init__.py",
        "buildState": site_packages / "golden_glory_lab" / "build_state" / "__init__.py",
        "itemReview": site_packages / "golden_glory_lab" / "item_review" / "__init__.py",
        "domain": site_packages / "golden_glory_lab" / "domain" / "__init__.py",
        "evidenceGate": site_packages / "golden_glory_lab" / "evidence_gate" / "__init__.py",
        "runtimeData": site_packages / "golden_glory_lab" / "runtime_data" / "__init__.py",
        "desktop": site_packages / "golden_glory_lab" / "desktop" / "main.py",
    }
    for label, source in expected_sources.items():
        if str(source.resolve()).casefold() not in text:
            raise AssertionError(f"{label} did not originate in installed package: {source}")
    repository_source = str((ROOT / "src" / "golden_glory_lab").resolve()).casefold()
    if repository_source in text:
        raise AssertionError("PyInstaller analysis referenced the repository source tree")
    if "_tkinter" not in text:
        raise AssertionError("PyInstaller analysis did not collect _tkinter")
    return {
        label: str(source.resolve()) for label, source in expected_sources.items()
    }


def _bundle_inventory(bundle: Path) -> dict[str, Any]:
    executable = bundle / f"{PACKAGE_NAME}.exe"
    if not executable.is_file():
        raise AssertionError(f"packaged executable is missing: {executable}")
    files = sorted(value for value in bundle.rglob("*") if value.is_file())
    relative = {value.relative_to(bundle).as_posix() for value in files}
    required_resources = {
        "pobFixture": "_internal/ggl_app_resources/pob/proof/comprehensive.xml",
        "copiedItemFixture": (
            "_internal/ggl_app_resources/item_review/copied-items-v1.json"
        ),
        "runtimeGateManifest": (
            "_internal/golden_glory_lab/runtime_data/enmity-manual-gate-v1.json"
        ),
        "runtimeEnmityReference": (
            "_internal/golden_glory_lab/runtime_data/enmity-reference-v1.json"
        ),
        "runtimeFlameLinkTable": (
            "_internal/golden_glory_lab/runtime_data/flame-link-level-table-v1.json"
        ),
    }
    missing_resources = {
        label: path for label, path in required_resources.items() if path not in relative
    }
    if missing_resources:
        raise AssertionError(f"packaged BUILD-002 resources are missing: {missing_resources}")
    tkinter_extensions = [value for value in files if value.name == "_tkinter.pyd"]
    if len(tkinter_extensions) != 1:
        raise AssertionError(f"expected one bundled _tkinter extension: {tkinter_extensions}")
    tcl_initializers = [value for value in files if value.name.casefold() == "init.tcl"]
    tk_initializers = [value for value in files if value.name.casefold() == "tk.tcl"]
    if not tcl_initializers or not tk_initializers:
        raise AssertionError(
            "bundled Tcl/Tk script libraries are incomplete: "
            f"init.tcl={tcl_initializers}, tk.tcl={tk_initializers}"
        )
    return {
        "executable": str(executable),
        "executableSha256": _sha256_file(executable),
        "fileCount": len(files),
        "sizeBytes": sum(value.stat().st_size for value in files),
        "treeSha256": _tree_sha256(bundle),
        "tkinterExtension": tkinter_extensions[0].relative_to(bundle).as_posix(),
        "tclInitializerCount": len(tcl_initializers),
        "tkInitializerCount": len(tk_initializers),
        "requiredResources": required_resources,
    }


def _verify_gui_subsystem(
    python: Path,
    executable: Path,
    *,
    cwd: Path,
    env: dict[str, str],
) -> int:
    bootstrap = r"""
import pefile
import sys

image = pefile.PE(sys.argv[1], fast_load=True)
subsystem = image.OPTIONAL_HEADER.Subsystem
image.close()
if subsystem != 2:
    raise AssertionError(f"expected Windows GUI subsystem 2, observed {subsystem}")
print(subsystem)
"""
    completed = _run(
        (str(python), "-I", "-c", bootstrap, str(executable)),
        cwd=cwd,
        env=env,
        capture=True,
    )
    return int(completed.stdout.decode("ascii").strip())


def _exercise_bundle(
    executable: Path,
    *,
    runs: int,
    runtime_root: Path,
) -> tuple[dict[str, Any], list[str]]:
    working_directory = runtime_root / "empty-working-directory"
    working_directory.mkdir()
    environment = _runtime_environment(runtime_root / "process-temp")
    Path(environment["TEMP"]).mkdir()
    output_bytes: list[bytes] = []
    output_hashes: list[str] = []
    parsed: list[dict[str, Any]] = []
    for index in range(runs):
        output = runtime_root / f"self-test-{index + 1}.json"
        _run(
            (str(executable), "--self-test-output", str(output)),
            cwd=working_directory,
            env=environment,
        )
        if not output.is_file():
            raise AssertionError(f"packaged self-test did not write output: {output}")
        payload = output.read_bytes()
        output_bytes.append(payload)
        output_hashes.append(hashlib.sha256(payload).hexdigest())
        parsed.append(json.loads(payload.decode("utf-8")))
    if any(payload != output_bytes[0] for payload in output_bytes[1:]):
        raise AssertionError(f"packaged self-test output was nondeterministic: {output_hashes}")
    if any(result.get("state") != "PASS" for result in parsed):
        raise AssertionError(f"packaged self-test failed: {parsed}")
    return parsed[0], output_hashes


def _copy_validated_bundle(source: Path, destination: Path) -> None:
    resolved = destination.resolve()
    if destination.exists():
        raise FileExistsError(f"copy destination already exists: {destination}")
    if _is_under(resolved, ROOT):
        raise ValueError("validated bundle copy must remain outside the repository")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and validate the isolated Windows BUILD-002 package."
    )
    parser.add_argument("--runs", type=int, default=RUN_COUNT_DEFAULT)
    parser.add_argument(
        "--temp-root",
        type=Path,
        default=Path(tempfile.gettempdir()),
        help="Existing parent for disposable clean-machine build directories.",
    )
    parser.add_argument(
        "--copy-output",
        type=Path,
        help="Optional nonexistent, out-of-repository path for the validated bundle.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if platform.system() != "Windows":
        raise RuntimeError("BUILD-002 desktop packaging validation requires Windows")
    if args.runs < RUN_COUNT_DEFAULT:
        raise ValueError(f"--runs must be at least {RUN_COUNT_DEFAULT}")
    if not args.temp_root.is_dir():
        raise FileNotFoundError(f"temporary parent does not exist: {args.temp_root}")
    network_imports = _source_network_imports()
    if network_imports:
        raise AssertionError(f"production source imports network clients: {network_imports}")

    build_environment = _build_environment()
    with tempfile.TemporaryDirectory(
        prefix="golden-glory-lab-build-002-",
        dir=args.temp_root,
    ) as temporary:
        workspace = Path(temporary)
        environment_root = workspace / "environment"
        wheelhouse = workspace / "wheelhouse"
        distribution_root = workspace / "distribution"
        work_root = workspace / "pyinstaller-work"
        spec_root = workspace / "pyinstaller-spec"
        runtime_root = workspace / "runtime"
        build_cwd = workspace / "empty-build-directory"
        for directory in (
            wheelhouse,
            distribution_root,
            work_root,
            spec_root,
            runtime_root,
            build_cwd,
        ):
            directory.mkdir()

        venv.EnvBuilder(with_pip=True, clear=True).create(environment_root)
        python = _venv_python(environment_root)
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
            cwd=build_cwd,
            env=build_environment,
        )
        _run(
            (str(python), "-I", "-m", "pip", "check"),
            cwd=build_cwd,
            env=build_environment,
        )
        packaging_dependencies = _verify_packaging_dependencies(
            python,
            cwd=build_cwd,
            env=build_environment,
        )
        _run(
            (
                str(python),
                "-I",
                "-m",
                "pip",
                "wheel",
                "--disable-pip-version-check",
                "--no-deps",
                "--no-build-isolation",
                "--wheel-dir",
                str(wheelhouse),
                str(ROOT),
            ),
            cwd=build_cwd,
            env=build_environment,
        )
        wheels = list(wheelhouse.glob("golden_glory_lab-*.whl"))
        if len(wheels) != 1:
            raise AssertionError(f"expected one project wheel: {wheels}")
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
                str(wheels[0]),
            ),
            cwd=build_cwd,
            env=build_environment,
        )
        launcher, site_packages, project_metadata = _verify_installed_package(
            environment_root
        )
        build_tk = _verify_tk_runtime(
            python,
            cwd=build_cwd,
            env=build_environment,
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
                "--onedir",
                "--windowed",
                "--name",
                PACKAGE_NAME,
                "--hidden-import",
                "golden_glory_lab.runtime_data",
                "--distpath",
                str(distribution_root),
                "--workpath",
                str(work_root),
                "--specpath",
                str(spec_root),
                "--add-data",
                f"{POB_FIXTURE}{os.pathsep}ggl_app_resources/pob/proof",
                "--add-data",
                f"{COPIED_FIXTURE}{os.pathsep}ggl_app_resources/item_review",
                "--add-data",
                (
                    f"{site_packages / 'golden_glory_lab' / 'runtime_data' / 'enmity-manual-gate-v1.json'}"
                    f"{os.pathsep}golden_glory_lab/runtime_data"
                ),
                "--add-data",
                (
                    f"{site_packages / 'golden_glory_lab' / 'runtime_data' / 'enmity-reference-v1.json'}"
                    f"{os.pathsep}golden_glory_lab/runtime_data"
                ),
                "--add-data",
                (
                    f"{site_packages / 'golden_glory_lab' / 'runtime_data' / 'flame-link-level-table-v1.json'}"
                    f"{os.pathsep}golden_glory_lab/runtime_data"
                ),
                str(launcher),
            ),
            cwd=build_cwd,
            env=build_environment,
        )

        installed_sources = _verify_analysis(work_root, site_packages)
        built_bundle = distribution_root / PACKAGE_NAME
        isolated_bundle = runtime_root / "isolated-distribution" / PACKAGE_NAME
        isolated_bundle.parent.mkdir()
        shutil.copytree(built_bundle, isolated_bundle)
        inventory = _bundle_inventory(isolated_bundle)
        executable = isolated_bundle / f"{PACKAGE_NAME}.exe"
        subsystem = _verify_gui_subsystem(
            python,
            executable,
            cwd=build_cwd,
            env=build_environment,
        )
        self_test, output_hashes = _exercise_bundle(
            executable,
            runs=args.runs,
            runtime_root=runtime_root,
        )
        copied_output: str | None = None
        if args.copy_output is not None:
            _copy_validated_bundle(isolated_bundle, args.copy_output)
            copied_output = str(args.copy_output.resolve())

        report = {
            "status": "PASS",
            "packageFormat": "PyInstaller one-directory Windows GUI application",
            "packagingRunner": str(Path(__file__).relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "wheel": {
                "filename": wheels[0].name,
                "sha256": _sha256_file(wheels[0]),
            },
            "projectMetadata": project_metadata,
            "productionRequiresDist": [],
            "sourceNetworkClientImports": network_imports,
            "runtimeNetworkPolicy": (
                "No network client imports or production dependencies are present; "
                "operating-system egress is not technically blocked."
            ),
            "packagingDependencies": packaging_dependencies,
            "buildInterpreter": build_tk,
            "installedSources": installed_sources,
            "bundle": inventory,
            "windowsSubsystem": subsystem,
            "selfTestRuns": args.runs,
            "selfTestOutputSha256": output_hashes,
            "selfTest": self_test,
            "copiedOutput": copied_output,
        }
        print(json.dumps(report, indent=2, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
