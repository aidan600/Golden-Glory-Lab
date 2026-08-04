#!/usr/bin/env python3
"""Validate the first-release evidence pack with an isolated Draft 2020-12 runtime."""

from __future__ import annotations

import argparse
import copy
import importlib.metadata
import json
import subprocess
import sys
import tempfile
from pathlib import Path


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


def load_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_instance(validator: object, instance: object) -> list[str]:
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.absolute_path))
    return [error.message for error in errors]


def run_isolated(root: Path, dependency_target: Path) -> int:
    sys.path.insert(0, str(dependency_target))
    import jsonschema  # pylint: disable=import-outside-toplevel

    installed_jsonschema_version = importlib.metadata.version("jsonschema")
    if installed_jsonschema_version != "4.26.0":
        raise RuntimeError(f"unexpected jsonschema version: {installed_jsonschema_version}")

    schema = load_json(root / "data/schemas/audit-evidence-artifact-v1.schema.json")
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    artifacts = [load_json(root / relative_path) for relative_path in ARTIFACT_PATHS]

    failures: list[str] = []
    for relative_path, artifact in zip(ARTIFACT_PATHS, artifacts, strict=True):
        errors = validate_instance(validator, artifact)
        if errors:
            failures.append(f"{relative_path}: {errors[0]}")
    if failures:
        raise RuntimeError("Draft 2020-12 validation failed:\n" + "\n".join(failures))

    mutations: list[tuple[str, object]] = []
    invalid_artifact_id = copy.deepcopy(artifacts[0])
    invalid_artifact_id["artifactId"] = "not-an-evidence-artifact"
    mutations.append(("artifact ID", invalid_artifact_id))

    invalid_formula = copy.deepcopy(artifacts[8])
    invalid_formula["records"][1]["data"]["formula"]["overcap"] = "U-M"
    mutations.append(("canonical Enmity formula", invalid_formula))

    invalid_numeric = copy.deepcopy(artifacts[9])
    invalid_numeric["records"][0]["data"]["input"]["U"] = "75"
    mutations.append(("numeric Enmity input", invalid_numeric))

    invalid_fixture_state = copy.deepcopy(artifacts[7])
    invalid_fixture_state["records"][0]["data"]["expectedState"] = "calculated-anyway"
    mutations.append(("Flame Link fixture expected state", invalid_fixture_state))

    for label, mutation in mutations:
        if not validate_instance(validator, mutation):
            raise RuntimeError(f"schema negative mutation was accepted: {label}")

    print(
        "Draft 2020-12 evidence schema: validated 10 artifacts; "
        "negative mutations rejected: artifact ID, canonical formula, numeric input, fixture state."
    )
    return 0


def run_parent(root: Path) -> int:
    requirements = root / "requirements/pob-import-proof.txt"
    if not requirements.is_file():
        raise RuntimeError(f"missing pinned validation requirements: {requirements}")

    with tempfile.TemporaryDirectory(prefix="gll-evidence-schema-") as temporary_directory:
        dependency_target = Path(temporary_directory) / "site-packages"
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
            raise RuntimeError("could not provision the pinned schema-validation dependencies")
        command = [
            sys.executable,
            "-I",
            "-S",
            str(Path(__file__).resolve()),
            "--isolated",
            "--root",
            str(root),
            "--dependency-target",
            str(dependency_target),
        ]
        return subprocess.run(command, check=False).returncode


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
