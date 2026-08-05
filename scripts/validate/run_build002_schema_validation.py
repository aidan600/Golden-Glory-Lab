#!/usr/bin/env python3
"""Run all Draft 2020-12 self-checks and BUILD-002 instance contracts."""

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

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_JSONSCHEMA_VERSION = "4.26.0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--isolated", action="store_true")
    parser.add_argument("--dependency-target", type=Path)
    return parser


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _errors(validator: Any, instance: Any) -> list[str]:
    return [
        f"/{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
        for error in sorted(
            validator.iter_errors(instance), key=lambda value: list(value.absolute_path)
        )
    ]


def _require_valid(validator: Any, instance: Any, label: str) -> None:
    errors = _errors(validator, instance)
    if errors:
        raise RuntimeError(f"{label}: {errors[0]}")


def _require_invalid(validator: Any, instance: Any, label: str) -> None:
    if not _errors(validator, instance):
        raise RuntimeError(f"schema negative mutation was accepted: {label}")


def run_isolated(root: Path, dependency_target: Path) -> int:
    sys.path.insert(0, str(dependency_target))
    sys.path.insert(0, str(root / "src"))
    import jsonschema
    from referencing import Registry, Resource

    from golden_glory_lab.build_state import deserialize as deserialize_v2
    from golden_glory_lab.build_state.codec import deserialize as deserialize_v1
    from golden_glory_lab.evidence_gate import (
        load_enmity_reference,
        load_gate_manifest,
    )

    version = importlib.metadata.version("jsonschema")
    if version != EXPECTED_JSONSCHEMA_VERSION:
        raise RuntimeError(f"unexpected jsonschema version: {version}")

    schema_paths = sorted((root / "data" / "schemas").glob("*.schema.json"))
    schema_paths.append(root / "data" / "sources" / "registry.schema.json")
    schemas = {path.name: _load(path) for path in schema_paths}
    for path in schema_paths:
        jsonschema.Draft202012Validator.check_schema(schemas[path.name])
    registry = Registry().with_resources(
        [
            (schema["$id"], Resource.from_contents(schema))
            for schema in schemas.values()
        ]
    )

    def validator(name: str) -> Any:
        return jsonschema.Draft202012Validator(
            schemas[name], registry=registry
        )

    v1_validator = validator("build-state-v1.schema.json")
    v2_validator = validator("build-state-v2.schema.json")
    neutral_validator = validator("pob-neutral-import-v1.schema.json")
    gate_validator = validator("runtime-evidence-gate-v1.schema.json")
    registry_validator = validator("registry.schema.json")

    v1_paths = sorted((root / "fixtures" / "build_state").glob("*.build-state-v1.json"))
    v2_paths = sorted((root / "fixtures" / "build_state").glob("*.build-state-v2.json"))
    for path in v1_paths:
        raw = path.read_bytes()
        document = deserialize_v1(raw)
        _require_valid(v1_validator, document, str(path.relative_to(root)))
        migrated = deserialize_v2(raw)
        _require_valid(v2_validator, migrated, f"migrated {path.relative_to(root)}")
    for path in v2_paths:
        document = deserialize_v2(path.read_bytes())
        _require_valid(v2_validator, document, str(path.relative_to(root)))

    neutral_paths = sorted((root / "fixtures" / "pob" / "golden").glob("*.json"))
    for path in neutral_paths:
        _require_valid(
            neutral_validator, _load(path), str(path.relative_to(root))
        )

    manifest_path = (
        root
        / "src"
        / "golden_glory_lab"
        / "runtime_data"
        / "enmity-manual-gate-v1.json"
    )
    manifest_json = _load(manifest_path)
    _require_valid(gate_validator, manifest_json, str(manifest_path.relative_to(root)))
    manifest = load_gate_manifest()
    reference = load_enmity_reference()
    if manifest.manifestVersion != "1.0.0" or reference["resourceVersion"] != "1.0.0":
        raise RuntimeError("typed runtime resource version validation failed")

    source_registry = _load(root / "data" / "sources" / "registry.json")
    _require_valid(registry_validator, source_registry, "data/sources/registry.json")

    complete = _load(root / "fixtures" / "build_state" / "copied-enmity.build-state-v2.json")
    decimal = copy.deepcopy(complete)
    decimal["enmityManualInput"]["target"] = "1e2"
    _require_invalid(v2_validator, decimal, "v2 exponent decimal")
    locator = copy.deepcopy(complete)
    locator["enmityManualInput"]["observedItemReference"]["treeRowId"] = "I001"
    _require_invalid(v2_validator, locator, "v2 presentation locator")
    policy_ordinal = copy.deepcopy(manifest_json)
    policy_requirement = policy_ordinal["outputs"][0]["requirements"][2]
    policy_requirement["minimumStatus"] = "supported"
    _require_invalid(gate_validator, policy_ordinal, "policy with ordinal field")

    report = {
        "status": "PASS",
        "jsonschemaVersion": version,
        "schemasSelfChecked": len(schema_paths),
        "v1Fixtures": len(v1_paths),
        "v1MigrationsValidatedAsV2": len(v1_paths),
        "v2Fixtures": len(v2_paths),
        "neutralFixtures": len(neutral_paths),
        "runtimeResourcesTyped": 2,
        "schemaNegativeMutations": 3,
    }
    print("BUILD002_SCHEMA_SUMMARY=" + json.dumps(report, sort_keys=True))
    return 0


def run_parent(root: Path) -> int:
    requirements = root / "requirements" / "pob-import-proof.txt"
    with tempfile.TemporaryDirectory(prefix="gll-build002-schema-") as temporary:
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
            cwd=root,
            check=False,
        )
        if install.returncode:
            raise RuntimeError("could not provision pinned schema dependencies")
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
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        if child.returncode:
            raise RuntimeError(
                (child.stderr or child.stdout or "isolated schema validation failed").strip()
            )
        print(child.stdout.strip())
    return 0


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    if args.isolated:
        if args.dependency_target is None:
            raise RuntimeError("--isolated requires --dependency-target")
        return run_isolated(root, args.dependency_target.resolve())
    return run_parent(root)


if __name__ == "__main__":
    raise SystemExit(main())
