#!/usr/bin/env python3
"""Run the reusable first-release evidence schema contract in isolation."""

from __future__ import annotations

import argparse
import copy
import importlib.metadata
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ARTIFACT_PATHS = (
    "data/curated/aud-002-mercenary-input-contract-v1.json",
    "data/curated/aud-003-light-radius-passive-sources-v1.json",
    "data/curated/aud-003-light-radius-observed-stat-terms-v1.json",
    "data/curated/aud-003-link-effect-passive-sources-v1.json",
    "data/curated/aud-003-link-effect-observed-stat-terms-v1.json",
    "data/curated/aud-003-golden-glory-mechanic-v1.json",
    "data/curated/aud-004-flame-link-reference-v1.json",
    "fixtures/mechanics/aud-004-flame-link-gates-v1.json",
    "data/curated/aud-005-enmitys-embrace-reference-v1.json",
    "fixtures/mechanics/aud-005-enmitys-embrace-gates-v1.json",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--isolated", action="store_true")
    parser.add_argument("--dependency-target", type=Path)
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def pointer(parts: Any) -> str:
    if not parts:
        return "/"
    return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in parts)


def validate_in_memory(validator: Any, instance: Any) -> list[str]:
    """Validate an in-memory artifact through the actual Draft 2020-12 validator."""
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.absolute_path))
    return [f"{pointer(error.absolute_path)}: {error.message}" for error in errors]


def require_rejected(validator: Any, label: str, instance: Any, expected_path: str) -> None:
    errors = validate_in_memory(validator, instance)
    if not errors:
        raise RuntimeError(f"schema negative mutation was accepted: {label}")
    if not any(error.startswith(expected_path + ":") and "not valid under any of the given schemas" in error for error in errors):
        raise RuntimeError(
            f"schema negative mutation {label} failed at an unstable path; "
            f"expected {expected_path}, got {errors[0]}"
        )


def build_validator(root: Path) -> Any:
    import jsonschema  # pylint: disable=import-outside-toplevel

    version = importlib.metadata.version("jsonschema")
    if version != "4.26.0":
        raise RuntimeError(f"unexpected jsonschema version: {version}")
    schema = load_json(root / "data/schemas/audit-evidence-artifact-v1.schema.json")
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def run_isolated(root: Path, dependency_target: Path) -> int:
    sys.path.insert(0, str(dependency_target))
    validator = build_validator(root)
    artifacts = [load_json(root / path) for path in ARTIFACT_PATHS]
    failures = []
    for path, artifact in zip(ARTIFACT_PATHS, artifacts, strict=True):
        errors = validate_in_memory(validator, artifact)
        if errors:
            failures.append(f"{path}: {errors[0]}")
    if failures:
        raise RuntimeError("Draft 2020-12 validation failed:\n" + "\n".join(failures))

    mutations: list[tuple[str, Any, str]] = []
    wrong_id = copy.deepcopy(artifacts[0])
    wrong_id["artifactId"] = "wrong"
    mutations.append(("artifact ID", wrong_id, "/"))

    wrong_record_id = copy.deepcopy(artifacts[0])
    wrong_record_id["records"][0]["id"] = "wrong"
    mutations.append(("record ID", wrong_record_id, "/"))

    unexpected_nested = copy.deepcopy(artifacts[6])
    unexpected_nested["records"][0]["data"]["components"]["sourceMaximumLife"]["invented"] = True
    mutations.append(("unexpected nested field", unexpected_nested, "/"))

    missing_nested = copy.deepcopy(artifacts[6])
    del missing_nested["records"][0]["data"]["standardQuality"]["millisecondsPerQuality"]
    mutations.append(("missing nested field", missing_nested, "/"))

    wrong_formula = copy.deepcopy(artifacts[8])
    wrong_formula["records"][1]["data"]["formula"]["overcap"] = "U-M"
    mutations.append(("canonical Enmity formula", wrong_formula, "/"))

    wrong_numeric = copy.deepcopy(artifacts[9])
    wrong_numeric["records"][0]["data"]["input"]["U"] = "75"
    mutations.append(("numeric Enmity input", wrong_numeric, "/"))

    wrong_state = copy.deepcopy(artifacts[7])
    wrong_state["records"][0]["data"]["expectedState"] = "calculated-anyway"
    mutations.append(("Flame Link fixture state", wrong_state, "/"))

    wrong_ordinal = copy.deepcopy(artifacts[6])
    wrong_ordinal["records"][1]["data"]["upstreamDependencies"][0]["minimumStatus"] = "unknown"
    mutations.append(("ordinal gate status", wrong_ordinal, "/"))

    missing_gate_mode = copy.deepcopy(artifacts[6])
    del missing_gate_mode["records"][1]["data"]["upstreamDependencies"][0]["gateMode"]
    mutations.append(("capability gate mode", missing_gate_mode, "/"))

    policy_with_ordinal = copy.deepcopy(artifacts[8])
    policy_with_ordinal["records"][2]["data"]["requiredPolicyClaims"][0]["minimumStatus"] = "supported"
    mutations.append(("policy ordinal field", policy_with_ordinal, "/"))

    missing_policy_mode = copy.deepcopy(artifacts[9])
    del missing_policy_mode["records"][8]["data"]["requiredPolicyClaims"][0]["policyMode"]
    mutations.append(("policy mode", missing_policy_mode, "/"))

    wrong_locator = copy.deepcopy(artifacts[8])
    wrong_locator["records"][0]["data"]["sourceLocators"]["developmentSnapshot"]["dynamicStatDescription"] = "generated stat-description record 2919"
    mutations.append(("Enmity development locator", wrong_locator, "/"))

    for label, mutation, expected_path in mutations:
        require_rejected(validator, label, mutation, expected_path)

    print(
        "EVIDENCE_SCHEMA_SUMMARY="
        + json.dumps({"artifacts": len(ARTIFACT_PATHS), "schemaMutations": len(mutations)}, sort_keys=True)
    )
    return 0


def run_parent(root: Path) -> int:
    requirements = root / "requirements/pob-import-proof.txt"
    if not requirements.is_file():
        raise RuntimeError(f"missing pinned validation requirements: {requirements}")
    with tempfile.TemporaryDirectory(prefix="gll-evidence-schema-") as temporary:
        dependency_target = Path(temporary) / "site-packages"
        install = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-deps",
                "--target",
                str(dependency_target),
                "--requirement",
                str(requirements),
            ],
            check=False,
            text=True,
        )
        if install.returncode:
            raise RuntimeError("could not provision pinned schema-validation dependencies")
        child = subprocess.run(
            [
                sys.executable,
                "-I",
                "-S",
                str(Path(__file__).resolve()),
                "--isolated",
                "--root",
                str(root),
                "--dependency-target",
                str(dependency_target),
            ],
            check=False,
            text=True,
            capture_output=True,
        )
        if child.returncode:
            raise RuntimeError((child.stderr or child.stdout or "isolated schema validator failed").strip())
        print(child.stdout.strip())
        return 0


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if args.isolated:
        if args.dependency_target is None:
            raise RuntimeError("--isolated requires --dependency-target")
        return run_isolated(root, args.dependency_target.resolve())
    return run_parent(root)


if __name__ == "__main__":
    raise SystemExit(main())
