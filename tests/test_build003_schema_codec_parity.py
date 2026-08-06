from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golden_glory_lab.build_state import (  # noqa: E402
    BuildStateError,
    empty_document,
    validate_document,
)

try:
    import jsonschema
    from referencing import Registry, Resource
except ImportError:  # pragma: no cover - exercised in isolated schema CI
    jsonschema = None  # type: ignore[assignment]
    Registry = None  # type: ignore[assignment]
    Resource = None  # type: ignore[assignment]


SCHEMA_PATH = ROOT / "data" / "schemas" / "build-state-v3.schema.json"
DIGEST = "a" * 64


def _load_validator() -> Any:
    if jsonschema is None or Registry is None or Resource is None:
        raise unittest.SkipTest("jsonschema and referencing are required for parity tests")
    schemas = {}
    for path in sorted((ROOT / "data" / "schemas").glob("*.schema.json")):
        schemas[path.name] = json.loads(path.read_text(encoding="utf-8"))
    registry = Registry().with_resources(
        [
            (schema["$id"], Resource.from_contents(schema))
            for schema in schemas.values()
        ]
    )
    return jsonschema.Draft202012Validator(
        schemas["build-state-v3.schema.json"], registry=registry
    )


def _schema_valid(validator: Any, document: dict[str, Any]) -> bool:
    return not any(validator.iter_errors(document))


def _codec_valid(document: dict[str, Any]) -> bool:
    try:
        validate_document(document)
    except BuildStateError:
        return False
    return True


def _mutate(document: dict[str, Any], mutator: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    updated = copy.deepcopy(document)
    mutator(updated)
    return updated


class SchemaCodecParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = _load_validator()
        cls.base = empty_document()

    def _assert_parity(self, label: str, document: dict[str, Any], *, expect_valid: bool) -> None:
        schema_ok = _schema_valid(self.validator, document)
        codec_ok = _codec_valid(document)
        with self.subTest(label=label, expect_valid=expect_valid):
            self.assertEqual(schema_ok, expect_valid, f"schema validity mismatch for {label}")
            self.assertEqual(codec_ok, expect_valid, f"codec validity mismatch for {label}")
            self.assertEqual(schema_ok, codec_ok, f"schema/codec disagreement for {label}")

    def test_table_driven_parity(self) -> None:
        cases: list[tuple[str, bool, Callable[[dict[str, Any]], None]]] = [
            ("empty-valid", True, lambda _doc: None),
            (
                "unreviewed-review-mismatch",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["goldenGlory"].update(
                    {"provenanceKind": "unreviewed", "reviewState": "reviewed"}
                ),
            ),
            (
                "manual-reviewed-missing-value",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["directLinkBuffEffect"].update(
                    {
                        "provenanceKind": "manual-reviewed",
                        "reviewState": "reviewed",
                        "reviewedDirectPct": None,
                    }
                ),
            ),
            (
                "recognized-reviewed-needs-identity",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["goldenGlory"].update(
                    {
                        "allocatedState": "allocated",
                        "mercenaryTargetState": "yes",
                        "reviewedLightRadiusPct": "10",
                        "provenanceKind": "recognized-reviewed",
                        "reviewState": "reviewed",
                        "rawSourceText": "",
                        "recognitionSource": {"kind": "none", "digest": None},
                    }
                ),
            ),
            (
                "recognized-reviewed-with-raw",
                True,
                lambda doc: doc["flameLinkPlayerChain"]["goldenGlory"].update(
                    {
                        "allocatedState": "allocated",
                        "mercenaryTargetState": "yes",
                        "reviewedLightRadiusPct": "10",
                        "provenanceKind": "recognized-reviewed",
                        "reviewState": "reviewed",
                        "rawSourceText": "10% increased Light Radius",
                        "recognitionSource": {"kind": "none", "digest": None},
                    }
                ),
            ),
            (
                "recognized-reviewed-with-digest",
                True,
                lambda doc: doc["flameLinkPlayerChain"]["directLinkBuffEffect"].update(
                    {
                        "reviewedDirectPct": "5",
                        "provenanceKind": "recognized-reviewed",
                        "reviewState": "reviewed",
                        "rawSourceText": "",
                        "recognitionSource": {"kind": "advisory-text", "digest": DIGEST},
                    }
                ),
            ),
            (
                "conditional-unreviewed-forbidden",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["conditionalContributions"][0].update(
                    {"provenanceKind": "unreviewed"}
                ),
            ),
            (
                "additional-level-unreviewed-forbidden",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["flameLinkLevel"][
                    "additionalLinkGemLevels"
                ][0].update({"provenanceKind": "unreviewed"}),
            ),
            (
                "empowered-catalog-levels-must-be-two",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["flameLinkLevel"][
                    "additionalLinkGemLevels"
                ][0].update({"levels": 3}),
            ),
            (
                "powerful-bond-as-level-id-forbidden",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["flameLinkLevel"][
                    "additionalLinkGemLevels"
                ].append(
                    {
                        "contributionId": "powerful-bond",
                        "label": "Powerful Bond",
                        "levels": 1,
                        "activeState": "inactive",
                        "provenanceKind": "manual-reviewed",
                        "rawSourceText": "",
                        "recognitionSource": {"kind": "none", "digest": None},
                    }
                ),
            ),
            (
                "benchmark-requires-21",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["flameLinkLevel"].update(
                    {"baseLevel": 20, "baseLevelProvenance": "manual-benchmark-default"}
                ),
            ),
            (
                "benchmark-21-valid",
                True,
                lambda doc: doc["flameLinkPlayerChain"]["flameLinkLevel"].update(
                    {"baseLevel": 21, "baseLevelProvenance": "manual-benchmark-default"}
                ),
            ),
            (
                "catalog-default-non-empowered-level-forbidden",
                False,
                lambda doc: doc["flameLinkPlayerChain"]["flameLinkLevel"][
                    "additionalLinkGemLevels"
                ].append(
                    {
                        "contributionId": "manual-level-0001",
                        "label": "Bad catalog",
                        "levels": 2,
                        "activeState": "inactive",
                        "provenanceKind": "catalog-default",
                        "rawSourceText": "",
                        "recognitionSource": {"kind": "none", "digest": None},
                    }
                ),
            ),
        ]
        for label, expect_valid, mutator in cases:
            document = _mutate(self.base, mutator)
            self._assert_parity(label, document, expect_valid=expect_valid)


if __name__ == "__main__":
    unittest.main()
