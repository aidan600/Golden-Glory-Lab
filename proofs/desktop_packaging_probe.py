"""Packaged PROOF-002 caller over the adopted public PoB importer seam.

The probe contains no PoB XML parsing or semantic projection logic, ownership
mapper, mechanics calculator, UI, or network behavior. It creates an empty
Expat parser only to verify packaged reparse-deferral state. PyInstaller
includes the existing fixture and retained
golden as explicit data resources beside this module in the frozen bundle.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import platform
import re
import sys
import zlib
from pathlib import Path
from typing import Any, Sequence
from xml.parsers import expat

import golden_glory_lab.pob_import as pob_import
from golden_glory_lab.pob_import import (
    CONTRACT_VERSION,
    IMPLEMENTATION_VERSION,
    deterministic_json_bytes,
    importPobRawXml,
)

PROOF_ID = "PROOF-002"
PROOF_RESULT_VERSION = "1.0.0"
PACKAGING_APPROACH = "PyInstaller"
PACKAGING_VERSION = "6.21.0"
MINIMUM_EXPAT_VERSION = (2, 7, 2)
MINIMUM_EXPAT_VERSION_TEXT = "2.7.2"
RESOURCE_ROOT = Path(__file__).resolve().parent / "ggl_proof_resources"
FIXTURE_PATH = RESOURCE_ROOT / "pob" / "proof" / "comprehensive.xml"
GOLDEN_PATH = (
    RESOURCE_ROOT / "pob" / "golden" / "comprehensive.raw.neutral-v1.json"
)
_EXPAT_VERSION_RE = re.compile(r"^(?:expat_)?([0-9]+)\.([0-9]+)\.([0-9]+)$")


class ProofFailure(Exception):
    """Expected machine-readable proof gate failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _read_bundled_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except FileNotFoundError as error:
        raise ProofFailure(f"BUNDLED_RESOURCE_MISSING:{path.name}") from error


def _decode_utf8_strict(value: bytes, resource_name: str) -> str:
    try:
        return value.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ProofFailure(f"BUNDLED_RESOURCE_UTF8_INVALID:{resource_name}") from error


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _stable_projection(result: dict[str, Any]) -> dict[str, Any]:
    projection = copy.deepcopy(result)
    envelope = projection.get("envelope")
    if not isinstance(envelope, dict) or "runtimeSecurity" not in envelope:
        raise ProofFailure("RUNTIME_SECURITY_MISSING")
    del envelope["runtimeSecurity"]
    return projection


def _escape_pointer_part(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _json_pointer_differences(
    expected: Any, actual: Any, path: str = ""
) -> list[str]:
    if type(expected) is not type(actual):
        return [path or "/"]
    if isinstance(expected, dict):
        differences: list[str] = []
        keys = sorted(set(expected) | set(actual))
        for key in keys:
            child_path = f"{path}/{_escape_pointer_part(key)}"
            if key not in expected or key not in actual:
                differences.append(child_path)
            else:
                differences.extend(
                    _json_pointer_differences(expected[key], actual[key], child_path)
                )
        return differences
    if isinstance(expected, list):
        differences = []
        if len(expected) != len(actual):
            differences.append(path or "/")
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            differences.extend(
                _json_pointer_differences(
                    expected_item, actual_item, f"{path}/{index}"
                )
            )
        return differences
    return [] if expected == actual else [path or "/"]


def _independent_runtime_security() -> dict[str, Any]:
    detected = getattr(expat, "EXPAT_VERSION", None)
    parsed: tuple[int, int, int] | None = None
    if isinstance(detected, str):
        match = _EXPAT_VERSION_RE.fullmatch(detected)
        if match:
            try:
                parsed = tuple(int(part) for part in match.groups())
            except (ValueError, OverflowError):
                parsed = None
    if parsed is None:
        status = "unparseable"
    elif parsed < MINIMUM_EXPAT_VERSION:
        status = "unsupported"
    else:
        status = "supported"
    return {
        "detectedExpatVersion": detected if isinstance(detected, str) else None,
        "parsedExpatVersion": list(parsed) if parsed is not None else None,
        "minimumExpatVersion": MINIMUM_EXPAT_VERSION_TEXT,
        "status": status,
    }


def _reparse_deferral_observation() -> dict[str, bool]:
    parser = expat.ParserCreate(encoding="UTF-8")
    available = hasattr(parser, "SetReparseDeferralEnabled")
    getter_available = hasattr(parser, "GetReparseDeferralEnabled")
    configured = False
    enabled = False
    if available:
        parser.SetReparseDeferralEnabled(True)
        configured = True
        enabled = (
            bool(parser.GetReparseDeferralEnabled())
            if getter_available
            else configured
        )
    return {
        "apiAvailable": available,
        "getterAvailable": getter_available,
        "configured": configured,
        "enabled": enabled,
    }


def _all_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            keys.append(key)
            keys.extend(_all_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.extend(_all_keys(child))
    return keys


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _runtime_path_observation(forbidden_paths: Sequence[str]) -> dict[str, Any]:
    executable = Path(sys.executable).resolve()
    module_file = getattr(pob_import, "__file__", None)
    if not isinstance(module_file, str):
        raise ProofFailure("IMPORTER_MODULE_LOCATOR_MISSING")
    module_locator = Path(module_file).resolve()
    current_directory = Path.cwd().resolve()
    resolved_forbidden = [Path(value).resolve() for value in forbidden_paths]
    observed_paths = [executable, module_locator, current_directory]
    observed_paths.extend(Path(value).resolve() for value in sys.path if value)
    forbidden_absent = not any(
        _is_under(observed, forbidden)
        for observed in observed_paths
        for forbidden in resolved_forbidden
    )
    ambient_site_packages_absent = not any(
        "site-packages" in value.lower() or "dist-packages" in value.lower()
        for value in sys.path
    )
    frozen = bool(getattr(sys, "frozen", False))
    bundle_root_value = getattr(sys, "_MEIPASS", None)
    bundle_root = (
        Path(bundle_root_value).resolve()
        if isinstance(bundle_root_value, str)
        else None
    )
    importer_is_bundled = bool(
        frozen and bundle_root is not None and _is_under(module_locator, bundle_root)
    )
    return {
        "pythonExecutable": str(executable),
        "importerModuleLocator": str(module_locator),
        "currentWorkingDirectory": str(current_directory),
        "frozen": frozen,
        "bundleRootAvailable": bundle_root is not None,
        "importerIsBundled": importer_is_bundled,
        "forbiddenRepositoryPathsAbsent": forbidden_absent,
        "ambientSitePackagesAbsent": ambient_site_packages_absent,
        "pythonPathAbsent": "PYTHONPATH" not in os.environ,
        "pythonHomeAbsent": "PYTHONHOME" not in os.environ,
        "pythonUserBaseAbsent": "PYTHONUSERBASE" not in os.environ,
    }


def _build_summary(
    *,
    forbidden_paths: Sequence[str],
    result_output: Path | None,
) -> dict[str, Any]:
    fixture_bytes = _read_bundled_bytes(FIXTURE_PATH)
    golden_bytes = _read_bundled_bytes(GOLDEN_PATH)
    fixture_text = _decode_utf8_strict(fixture_bytes, FIXTURE_PATH.name)
    golden_text = _decode_utf8_strict(golden_bytes, GOLDEN_PATH.name)
    try:
        expected_result = json.loads(golden_text)
    except json.JSONDecodeError as error:
        raise ProofFailure("BUNDLED_GOLDEN_JSON_INVALID") from error

    actual_result = importPobRawXml(fixture_text)
    actual_bytes = deterministic_json_bytes(actual_result)
    if result_output is not None:
        result_output.write_bytes(actual_bytes)

    expected_stable_bytes = deterministic_json_bytes(
        _stable_projection(expected_result)
    )
    actual_stable_bytes = deterministic_json_bytes(_stable_projection(actual_result))
    differences = _json_pointer_differences(expected_result, actual_result)
    differences_confined = all(
        pointer == "/envelope/runtimeSecurity"
        or pointer.startswith("/envelope/runtimeSecurity/")
        for pointer in differences
    )
    full_exact_match = actual_bytes == golden_bytes
    stable_exact_match = actual_stable_bytes == expected_stable_bytes
    runtime_security_matches_golden = (
        actual_result.get("envelope", {}).get("runtimeSecurity")
        == expected_result.get("envelope", {}).get("runtimeSecurity")
    )

    observed_security = _independent_runtime_security()
    reported_security = actual_result.get("envelope", {}).get("runtimeSecurity")
    runtime_security_valid = (
        reported_security == observed_security
        and observed_security["status"] == "supported"
    )
    reparse_deferral = _reparse_deferral_observation()
    runtime_paths = _runtime_path_observation(forbidden_paths)

    document = actual_result.get("document")
    item_sets = document.get("itemSets", []) if isinstance(document, dict) else []
    report = actual_result.get("report", [])
    mapping_entries = [
        entry
        for entry in report
        if isinstance(entry, dict) and entry.get("code") == "OWNERSHIP_MAPPING_REQUIRED"
    ]
    keys = _all_keys(actual_result)
    no_ownership_keys = not [key for key in keys if "owner" in key.lower()]
    no_mechanics_keys = not [
        key
        for key in keys
        if key.lower()
        in {
            "combinedscore",
            "damagepersecond",
            "dps",
            "enmitycalculation",
            "firepenetration",
            "flamelinkdamage",
            "goldenglorycontribution",
            "lightradiuscalculation",
            "resistancecalculation",
        }
    ]
    observed_item = next(
        (
            item
            for item in (document.get("items", []) if isinstance(document, dict) else [])
            if item.get("parsedId") == 7
        ),
        None,
    )

    structural_assertions = {
        "resultStatusSuccess": actual_result.get("status") == "success",
        "contractVersionExpected": actual_result.get("contractVersion") == "1.0.0",
        "threeItemSetsRetained": [
            entry.get("occurrenceId") for entry in item_sets
        ]
        == ["item-set-0001", "item-set-0002", "item-set-0003"],
        "noOwnershipFieldInvented": no_ownership_keys,
        "mappingRemainsManuallyRequired": len(mapping_entries) == 1
        and mapping_entries[0].get("category") == "manually required"
        and mapping_entries[0].get("candidateTargets")
        == ["item-set-0001", "item-set-0002", "item-set-0003"],
        "observedItemTextPreserved": isinstance(observed_item, dict)
        and "+999% to Fire Resistance" in observed_item.get("xmlCharacterValue", ""),
        "noMechanicsFieldInvented": no_mechanics_keys,
    }

    assertion_failures: list[str] = []

    def require(condition: bool, code: str) -> None:
        if not condition:
            assertion_failures.append(code)

    require(CONTRACT_VERSION == "1.0.0", "PUBLIC_CONTRACT_VERSION_UNEXPECTED")
    require(
        IMPLEMENTATION_VERSION == "pob-importer-python/0.1.1",
        "PUBLIC_IMPLEMENTATION_VERSION_UNEXPECTED",
    )
    for name, passed in structural_assertions.items():
        require(passed, f"STRUCTURAL_ASSERTION_FAILED:{name}")
    require(stable_exact_match, "STABLE_PROJECTION_MISMATCH")
    require(differences_confined, "NON_RUNTIME_SECURITY_DIFFERENCE")
    require(runtime_security_valid, "RUNTIME_SECURITY_VALIDATION_FAILED")
    require(
        reparse_deferral["configured"] and reparse_deferral["enabled"],
        "REPARSE_DEFERRAL_NOT_ENABLED",
    )
    if runtime_security_matches_golden:
        require(full_exact_match, "FULL_GOLDEN_MISMATCH_WITH_EQUAL_RUNTIME_SECURITY")
    require(runtime_paths["frozen"], "RUNTIME_NOT_FROZEN")
    require(runtime_paths["importerIsBundled"], "IMPORTER_NOT_BUNDLED")
    require(
        runtime_paths["forbiddenRepositoryPathsAbsent"],
        "REPOSITORY_PATH_PRESENT_AT_RUNTIME",
    )
    require(
        runtime_paths["ambientSitePackagesAbsent"],
        "AMBIENT_SITE_PACKAGES_PRESENT",
    )
    require(runtime_paths["pythonPathAbsent"], "PYTHONPATH_PRESENT")
    require(runtime_paths["pythonHomeAbsent"], "PYTHONHOME_PRESENT")
    require(runtime_paths["pythonUserBaseAbsent"], "PYTHONUSERBASE_PRESENT")

    return {
        "proofId": PROOF_ID,
        "proofResultVersion": PROOF_RESULT_VERSION,
        "state": "PASS" if not assertion_failures else "FAIL",
        "packaging": {
            "approach": PACKAGING_APPROACH,
            "version": PACKAGING_VERSION,
            "format": "one-directory",
            "frozenRuntimeReported": runtime_paths["frozen"],
        },
        "importer": {
            "contractVersion": CONTRACT_VERSION,
            "implementationVersion": IMPLEMENTATION_VERSION,
            "moduleLocator": runtime_paths["importerModuleLocator"],
            "publicEntryPoint": "importPobRawXml",
        },
        "runtime": {
            "pythonVersion": platform.python_version(),
            "pythonExecutable": runtime_paths["pythonExecutable"],
            "expatVersion": getattr(expat, "EXPAT_VERSION", None),
            "zlibVersion": zlib.ZLIB_RUNTIME_VERSION,
            "importerAdmissionStatus": observed_security["status"],
            "reportedRuntimeSecurity": reported_security,
            "independentlyObservedRuntimeSecurity": observed_security,
            "runtimeSecurityIndependentlyValidated": runtime_security_valid,
            "reparseDeferral": reparse_deferral,
        },
        "resources": {
            "fixtureSha256": _sha256(fixture_bytes),
            "expectedGoldenSha256": _sha256(golden_bytes),
        },
        "result": {
            "actualFullSha256": _sha256(actual_bytes),
            "fullGoldenMatch": full_exact_match,
            "runtimeSecurityMatchesGolden": runtime_security_matches_golden,
            "expectedStableProjectionSha256": _sha256(expected_stable_bytes),
            "actualStableProjectionSha256": _sha256(actual_stable_bytes),
            "stableProjectionMatch": stable_exact_match,
            "fullDifferencesConfinedToRuntimeSecurity": differences_confined,
            "fullDifferenceCount": len(differences),
        },
        "structuralAssertions": structural_assertions,
        "isolation": {
            "repositorySourcePathsAbsent": runtime_paths[
                "forbiddenRepositoryPathsAbsent"
            ],
            "ambientSitePackagesAbsent": runtime_paths[
                "ambientSitePackagesAbsent"
            ],
            "pythonPathAbsent": runtime_paths["pythonPathAbsent"],
            "pythonHomeAbsent": runtime_paths["pythonHomeAbsent"],
            "pythonUserBaseAbsent": runtime_paths["pythonUserBaseAbsent"],
        },
        "knownLimitations": [
            "Local sanitized-process isolation is not a Python-free clean-machine test.",
            "Outbound network denial was not directly enforced by this executable.",
            "This console proof does not select the first BUILD's UI toolkit.",
            "The adopted PROOF-001 importer limitations remain in force.",
        ],
        "assertionFailures": assertion_failures,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run packaged PROOF-002 assertions.")
    parser.add_argument(
        "--forbidden-path",
        action="append",
        default=[],
        help="Absolute repository path that must not appear in packaged runtime paths.",
    )
    parser.add_argument(
        "--result-output",
        type=Path,
        help="Optional temporary path for the full deterministic importer result.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = _build_summary(
            forbidden_paths=args.forbidden_path,
            result_output=args.result_output,
        )
    except ProofFailure as error:
        summary = {
            "proofId": PROOF_ID,
            "proofResultVersion": PROOF_RESULT_VERSION,
            "state": "FAIL",
            "failureCode": error.code,
        }
    except Exception as error:  # pragma: no cover - packaged safety boundary
        summary = {
            "proofId": PROOF_ID,
            "proofResultVersion": PROOF_RESULT_VERSION,
            "state": "FAIL",
            "failureCode": f"UNEXPECTED_PROBE_FAILURE:{type(error).__name__}",
        }
    encoded = (
        json.dumps(summary, ensure_ascii=True, allow_nan=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    sys.stdout.buffer.write(encoded)
    return 0 if summary["state"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
