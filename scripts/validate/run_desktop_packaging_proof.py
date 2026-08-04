"""Build and validate the isolated Windows desktop packaging PROOF-002."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import venv
import zipfile
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "proofs" / "desktop_packaging_probe.py"
FIXTURE = ROOT / "fixtures" / "pob" / "proof" / "comprehensive.xml"
GOLDEN = (
    ROOT
    / "fixtures"
    / "pob"
    / "golden"
    / "comprehensive.raw.neutral-v1.json"
)
REQUIREMENTS = ROOT / "requirements" / "desktop-packaging-proof.txt"
PACKAGE_NAME = "GoldenGloryLabPackagingProbe"
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


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _displayed_command(command: Sequence[str]) -> str:
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
    print(f"+ {_displayed_command(command)}", flush=True)
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
            f"command failed with exit {completed.returncode}: "
            f"{_displayed_command(command)}"
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


def _canonical_json_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
            separators=(",", ": "),
        )
        + "\n"
    ).encode("utf-8")


def _stable_projection(value: dict[str, Any]) -> dict[str, Any]:
    projection = copy.deepcopy(value)
    del projection["envelope"]["runtimeSecurity"]
    return projection


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _verify_packaging_dependencies(
    python: Path, environment_root: Path, environment: dict[str, str]
) -> None:
    bootstrap = """
import importlib.metadata
import json
import pathlib
import sys

environment_root = pathlib.Path(sys.argv[1]).resolve()
expected = json.loads(sys.argv[2])
actual = {name: importlib.metadata.version(name) for name in expected}
assert actual == expected, (actual, expected)
for distribution_name in expected:
    distribution = importlib.metadata.distribution(distribution_name)
    location = pathlib.Path(distribution.locate_file(\"\")).resolve()
    assert location.is_relative_to(environment_root), (distribution_name, location)
print(json.dumps(actual, sort_keys=True))
"""
    _run(
        (
            str(python),
            "-I",
            "-c",
            bootstrap,
            str(environment_root),
            json.dumps(EXPECTED_PACKAGING_DEPENDENCIES, sort_keys=True),
        ),
        cwd=environment_root,
        env=environment,
    )


def _verify_installed_wheel(environment_root: Path) -> Path:
    site_packages = environment_root / "Lib" / "site-packages"
    module = site_packages / "golden_glory_lab" / "pob_import" / "__init__.py"
    if not module.is_file():
        raise AssertionError(f"installed importer is missing: {module}")
    metadata_files = list(site_packages.glob("golden_glory_lab-*.dist-info/METADATA"))
    if len(metadata_files) != 1:
        raise AssertionError(f"expected one installed project metadata file: {metadata_files}")
    requires_dist = [
        line
        for line in metadata_files[0].read_text(encoding="utf-8").splitlines()
        if line.startswith("Requires-Dist:")
    ]
    if requires_dist:
        raise AssertionError(f"production package unexpectedly has dependencies: {requires_dist}")
    return module


def _assert_analysis_uses_installed_importer(
    analysis_path: Path, environment_root: Path
) -> None:
    analysis = ast.literal_eval(analysis_path.read_text(encoding="utf-8"))

    def strings(value: Any) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple)):
            found: list[str] = []
            for child in value:
                found.extend(strings(child))
            return found
        if isinstance(value, dict):
            found = []
            for key, child in value.items():
                found.extend(strings(key))
                found.extend(strings(child))
            return found
        return []

    candidate_paths = [
        Path(value).resolve()
        for value in strings(analysis)
        if "golden_glory_lab" in value.lower()
        and ("\\" in value or "/" in value)
    ]
    installed = environment_root / "Lib" / "site-packages" / "golden_glory_lab"
    repository_source = ROOT / "src" / "golden_glory_lab"
    if not any(_is_under(path, installed) for path in candidate_paths):
        raise AssertionError(
            "PyInstaller analysis did not record the installed importer; "
            f"candidate paths: {candidate_paths}"
        )
    if any(_is_under(path, repository_source) for path in candidate_paths):
        raise AssertionError(
            "PyInstaller analysis imported the repository source package"
        )


def _source_network_imports() -> list[dict[str, str]]:
    inspected = [PROBE, *sorted((ROOT / "src" / "golden_glory_lab").rglob("*.py"))]
    blocked: list[dict[str, str]] = []
    for path in inspected:
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


def _zip_directory(source: Path, archive: Path) -> None:
    with zipfile.ZipFile(
        archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as output:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            output.write(path, path.relative_to(source.parent))


def _validate_probe_summary(
    summary: dict[str, Any],
    *,
    executable: Path,
    expected_golden_bytes: bytes,
    expected_stable_bytes: bytes,
) -> None:
    if summary["proofId"] != "PROOF-002" or summary["state"] != "PASS":
        raise AssertionError(f"packaged probe did not pass: {summary}")
    if summary["packaging"] != {
        "approach": "PyInstaller",
        "format": "one-directory",
        "frozenRuntimeReported": True,
        "version": "6.21.0",
    }:
        raise AssertionError(f"unexpected packaging metadata: {summary['packaging']}")
    if Path(summary["runtime"]["pythonExecutable"]).resolve() != executable.resolve():
        raise AssertionError("packaged Python executable path is not the launched executable")
    module_locator = Path(summary["importer"]["moduleLocator"]).resolve()
    if not _is_under(module_locator, executable.parent):
        raise AssertionError("packaged importer locator is outside the copied distribution")
    if _is_under(module_locator, ROOT):
        raise AssertionError("packaged importer locator resolved into the repository")
    if summary["resources"]["fixtureSha256"] != _sha256(FIXTURE.read_bytes()):
        raise AssertionError("packaged fixture hash does not match the retained fixture")
    if summary["resources"]["expectedGoldenSha256"] != _sha256(
        expected_golden_bytes
    ):
        raise AssertionError("packaged expected golden hash is wrong")
    result = summary["result"]
    if result["expectedStableProjectionSha256"] != _sha256(expected_stable_bytes):
        raise AssertionError("packaged expected stable projection hash is wrong")
    if not result["stableProjectionMatch"]:
        raise AssertionError("packaged stable projection did not match")
    if not result["fullDifferencesConfinedToRuntimeSecurity"]:
        raise AssertionError("packaged result differs outside runtime security")
    if not summary["runtime"]["runtimeSecurityIndependentlyValidated"]:
        raise AssertionError("packaged runtime security was not independently validated")
    if summary["runtime"]["importerAdmissionStatus"] != "supported":
        raise AssertionError("packaged importer runtime admission did not pass")
    if not summary["runtime"]["reparseDeferral"]["enabled"]:
        raise AssertionError("packaged Expat reparse deferral was not enabled")
    if not all(summary["structuralAssertions"].values()):
        raise AssertionError("one or more packaged neutral-contract assertions failed")
    if not all(summary["isolation"].values()):
        raise AssertionError("one or more packaged isolation assertions failed")


def _validate_result_bytes(
    actual_bytes: bytes,
    expected_bytes: bytes,
    summary: dict[str, Any],
) -> None:
    actual = json.loads(actual_bytes)
    expected = json.loads(expected_bytes)
    actual_stable = _canonical_json_bytes(_stable_projection(actual))
    expected_stable = _canonical_json_bytes(_stable_projection(expected))
    if actual_stable != expected_stable:
        raise AssertionError("runner stable projection comparison failed")
    if summary["result"]["actualFullSha256"] != _sha256(actual_bytes):
        raise AssertionError("probe full result hash does not match runner observation")
    if summary["result"]["actualStableProjectionSha256"] != _sha256(actual_stable):
        raise AssertionError("probe stable result hash does not match runner observation")
    reported_security = actual["envelope"]["runtimeSecurity"]
    observed_security = summary["runtime"]["independentlyObservedRuntimeSecurity"]
    if reported_security != observed_security:
        raise AssertionError("runner observed a packaged runtime-security mismatch")
    retained_security = expected["envelope"]["runtimeSecurity"]
    if reported_security == retained_security:
        if actual_bytes != expected_bytes or not summary["result"]["fullGoldenMatch"]:
            raise AssertionError("equal runtime security requires a full golden match")
    elif summary["result"]["fullGoldenMatch"]:
        raise AssertionError("different runtime security cannot report a full golden match")


def _default_temp_root() -> Path:
    windows_temp = Path(r"C:\tmp")
    if windows_temp.is_dir():
        return windows_temp
    return Path(tempfile.gettempdir())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and validate the isolated PROOF-002 Windows package."
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=RUN_COUNT_DEFAULT,
        help="Packaged executions to perform; values below three are rejected.",
    )
    parser.add_argument(
        "--temp-root",
        type=Path,
        default=_default_temp_root(),
        help="Existing directory for temporary isolated build and run outputs.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if os.name != "nt":
        raise RuntimeError("PROOF-002 requires a Windows build host")
    if args.runs < 3:
        raise ValueError("PROOF-002 requires at least three packaged executions")
    temp_root = args.temp_root.resolve()
    if not temp_root.is_dir():
        raise FileNotFoundError(f"temporary root does not exist: {temp_root}")
    if sys.version_info < (3, 11):
        raise RuntimeError("the adopted package requires Python 3.11 or newer")

    print(f"Host Python {platform.python_version()} at {sys.executable}", flush=True)
    print(f"Temporary isolation root: {temp_root}", flush=True)
    build_environment = _build_environment()
    expected_golden_bytes = GOLDEN.read_bytes()
    expected_result = json.loads(expected_golden_bytes)
    expected_stable_bytes = _canonical_json_bytes(
        _stable_projection(expected_result)
    )
    blocked_imports = _source_network_imports()
    if blocked_imports:
        raise AssertionError(f"network-capable source import found: {blocked_imports}")

    with tempfile.TemporaryDirectory(
        prefix="ggl-desktop-packaging-proof-", dir=temp_root
    ) as temporary:
        proof_root = Path(temporary).resolve()
        environment_root = proof_root / "build-environment"
        wheelhouse = proof_root / "wheelhouse"
        packaging_cwd = proof_root / "packaging-cwd"
        dist_root = proof_root / "build-dist"
        work_root = proof_root / "build-work"
        spec_root = proof_root / "build-spec"
        archive_root = proof_root / "archive"
        isolated_root = proof_root / "isolated-run"
        runtime_temp = isolated_root / "temp"
        runtime_working = isolated_root / "working"
        for path in (
            wheelhouse,
            packaging_cwd,
            dist_root,
            work_root,
            spec_root,
            archive_root,
            isolated_root,
            runtime_temp,
            runtime_working,
        ):
            path.mkdir(parents=True, exist_ok=True)

        print("[stage] create isolated build environment", flush=True)
        venv.EnvBuilder(with_pip=True, clear=True).create(environment_root)
        python = _venv_python(environment_root)
        if not python.is_file():
            raise AssertionError(f"isolated Python was not created: {python}")

        print("[stage] build project wheel", flush=True)
        _run(
            (
                str(python),
                "-m",
                "pip",
                "wheel",
                "--disable-pip-version-check",
                "--no-deps",
                "--wheel-dir",
                str(wheelhouse),
                str(ROOT),
            ),
            cwd=packaging_cwd,
            env=build_environment,
        )
        wheels = list(wheelhouse.glob("golden_glory_lab-*.whl"))
        if len(wheels) != 1:
            raise AssertionError(f"expected one project wheel, found {wheels}")
        _run(
            (
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-deps",
                str(wheels[0]),
            ),
            cwd=packaging_cwd,
            env=build_environment,
        )
        installed_importer = _verify_installed_wheel(environment_root)
        print(f"Installed production importer: {installed_importer}", flush=True)

        print("[stage] install exact proof-only packaging dependencies", flush=True)
        _run(
            (
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-deps",
                "-r",
                str(REQUIREMENTS),
            ),
            cwd=packaging_cwd,
            env=build_environment,
        )
        _verify_packaging_dependencies(python, environment_root, build_environment)
        _run(
            (str(python), "-m", "pip", "check"),
            cwd=packaging_cwd,
            env=build_environment,
        )

        print("[stage] build PyInstaller one-directory distributable", flush=True)
        build_started = time.perf_counter()
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
                "--console",
                "--name",
                PACKAGE_NAME,
                "--distpath",
                str(dist_root),
                "--workpath",
                str(work_root),
                "--specpath",
                str(spec_root),
                "--add-data",
                f"{FIXTURE}{os.pathsep}ggl_proof_resources/pob/proof",
                "--add-data",
                f"{GOLDEN}{os.pathsep}ggl_proof_resources/pob/golden",
                str(PROBE),
            ),
            cwd=packaging_cwd,
            env=build_environment,
        )
        build_seconds = time.perf_counter() - build_started
        built_bundle = dist_root / PACKAGE_NAME
        built_executable = built_bundle / f"{PACKAGE_NAME}.exe"
        built_fixture = (
            built_bundle
            / "_internal"
            / "ggl_proof_resources"
            / "pob"
            / "proof"
            / FIXTURE.name
        )
        built_golden = (
            built_bundle
            / "_internal"
            / "ggl_proof_resources"
            / "pob"
            / "golden"
            / GOLDEN.name
        )
        for required in (built_executable, built_fixture, built_golden):
            if not required.is_file():
                raise AssertionError(f"expected packaged artifact is missing: {required}")
        if built_fixture.read_bytes() != FIXTURE.read_bytes():
            raise AssertionError("packaged fixture bytes differ from retained fixture")
        if built_golden.read_bytes() != expected_golden_bytes:
            raise AssertionError("packaged golden bytes differ from retained golden")
        analysis_path = work_root / PACKAGE_NAME / "Analysis-00.toc"
        _assert_analysis_uses_installed_importer(analysis_path, environment_root)

        print("[stage] archive and copy distributable to isolated run directory", flush=True)
        archive = archive_root / f"{PACKAGE_NAME}-windows-x64.zip"
        _zip_directory(built_bundle, archive)
        copied_archive = isolated_root / archive.name
        shutil.copy2(archive, copied_archive)
        if _sha256_file(copied_archive) != _sha256_file(archive):
            raise AssertionError("copied distributable archive hash changed")
        with zipfile.ZipFile(copied_archive) as packaged_zip:
            packaged_zip.extractall(isolated_root / "distribution")
        copied_bundle = isolated_root / "distribution" / PACKAGE_NAME
        copied_executable = copied_bundle / f"{PACKAGE_NAME}.exe"
        if not copied_executable.is_file():
            raise AssertionError("copied packaged executable is missing")
        if _is_under(copied_executable, ROOT):
            raise AssertionError("packaged executable was not isolated from repository")

        print(f"[stage] run copied packaged probe {args.runs} times", flush=True)
        runtime_environment = _runtime_environment(runtime_temp)
        summaries: list[dict[str, Any]] = []
        summary_bytes: list[bytes] = []
        result_bytes: list[bytes] = []
        startup_seconds: list[float] = []
        for index in range(args.runs):
            result_output = runtime_working / f"actual-result-{index + 1}.json"
            command = (
                str(copied_executable),
                "--forbidden-path",
                str(ROOT),
                "--result-output",
                str(result_output),
            )
            started = time.perf_counter()
            completed = _run(
                command,
                cwd=runtime_working,
                env=runtime_environment,
                capture=True,
            )
            startup_seconds.append(time.perf_counter() - started)
            if completed.stderr:
                raise AssertionError(
                    f"packaged probe wrote stderr on run {index + 1}: "
                    f"{completed.stderr.decode('utf-8', errors='replace')}"
                )
            summary = json.loads(completed.stdout.decode("utf-8", errors="strict"))
            actual_bytes = result_output.read_bytes()
            _validate_probe_summary(
                summary,
                executable=copied_executable,
                expected_golden_bytes=expected_golden_bytes,
                expected_stable_bytes=expected_stable_bytes,
            )
            _validate_result_bytes(actual_bytes, expected_golden_bytes, summary)
            summaries.append(summary)
            summary_bytes.append(completed.stdout)
            result_bytes.append(actual_bytes)

        if len(set(summary_bytes)) != 1:
            raise AssertionError("repeated packaged proof summaries were not byte-identical")
        if len(set(result_bytes)) != 1:
            raise AssertionError("repeated packaged importer results were not byte-identical")

        bundle_files = sorted(path for path in built_bundle.rglob("*") if path.is_file())
        native_extensions = {".dll", ".exe", ".pyd"}
        native_files = [
            path for path in bundle_files if path.suffix.lower() in native_extensions
        ]
        summary = summaries[0]
        report = {
            "proofId": "PROOF-002",
            "result": "PASS WITH LIMITATIONS",
            "adoptionRecommendation": "ADOPT WITH NAMED LIMITATIONS",
            "packagingDependencies": EXPECTED_PACKAGING_DEPENDENCIES,
            "artifact": {
                "format": "ZIP containing a PyInstaller one-directory bundle",
                "fileCount": len(bundle_files),
                "uncompressedBytes": sum(path.stat().st_size for path in bundle_files),
                "archiveBytes": archive.stat().st_size,
                "archiveSha256": _sha256_file(archive),
                "primaryExecutableBytes": built_executable.stat().st_size,
                "primaryExecutableSha256": _sha256_file(built_executable),
                "nativeRuntimeFileCount": len(native_files),
                "copiedAndRunFromSeparateDirectory": True,
                "buildSeconds": round(build_seconds, 3),
                "startupSeconds": [round(value, 3) for value in startup_seconds],
            },
            "packagedRuntime": summary["runtime"],
            "importer": summary["importer"],
            "resources": summary["resources"],
            "deterministicResult": summary["result"],
            "structuralAssertions": summary["structuralAssertions"],
            "isolation": {
                **summary["isolation"],
                "packagedRuns": args.runs,
                "probeSummariesByteIdentical": True,
                "importerResultsByteIdentical": True,
                "sourceTreeImporterAbsentFromAnalysis": True,
                "networkBehaviorSourceInspectionPassed": True,
                "windowsSandboxUsed": False,
                "pythonFreeCleanMachineUsed": False,
                "outboundNetworkDenialEnforced": False,
            },
            "limitations": summary["knownLimitations"],
        }
        print("DESKTOP_PACKAGING_PROOF_RESULT", flush=True)
        print(
            json.dumps(report, ensure_ascii=True, allow_nan=False, indent=2, sort_keys=True),
            flush=True,
        )

    print("Desktop packaging PROOF suite passed; temporary outputs removed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
