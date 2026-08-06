from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golden_glory_lab.build_state import (  # noqa: E402
    BuildStateError,
    atomic_save,
    decode,
    deserialize,
    empty_document,
    migrate_v1_document,
    migrate_v2_document,
    serialize,
    validate_document,
)
from golden_glory_lab.build_state import codec as legacy_codec  # noqa: E402
from golden_glory_lab.build_state import codec_v2 as v2_codec  # noqa: E402

BUILD_FIXTURES = ROOT / "fixtures" / "build_state"


def v3_schema_validator() -> Draft202012Validator:
    schemas = [
        json.loads(
            (ROOT / "data" / "schemas" / name).read_text(encoding="utf-8")
        )
        for name in (
            "pob-neutral-import-v1.schema.json",
            "build-state-v3.schema.json",
        )
    ]
    for schema in schemas:
        Draft202012Validator.check_schema(schema)
    registry = Registry().with_resources(
        [(schema["$id"], Resource.from_contents(schema)) for schema in schemas]
    )
    return Draft202012Validator(schemas[-1], registry=registry)


def external_bytes(document: dict) -> bytes:
    return (
        json.dumps(
            document,
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
            separators=(",", ": "),
        )
        + "\n"
    ).encode("utf-8")


class BuildStateV3RoundTripTests(unittest.TestCase):
    def test_empty_and_flame_link_documents_round_trip(self) -> None:
        names = (
            "empty-migrated.build-state-v3.json",
            "flame-link.build-state-v3.json",
        )
        for name in names:
            path = BUILD_FIXTURES / name
            document = deserialize(path.read_bytes())
            first = serialize(document)
            second = serialize(deserialize(first))
            with self.subTest(name=name):
                self.assertEqual(first, second)
                self.assertEqual(document["schemaVersion"], "3.0.0")
                self.assertIn("flameLinkPlayerChain", document)

    def test_committed_v3_fixtures_are_runtime_and_schema_valid(self) -> None:
        validator = v3_schema_validator()
        observed = {path.name for path in BUILD_FIXTURES.glob("*.build-state-v3.json")}
        self.assertEqual(
            observed,
            {
                "empty-migrated.build-state-v3.json",
                "flame-link.build-state-v3.json",
            },
        )
        for path in sorted(BUILD_FIXTURES.glob("*.build-state-v3.json")):
            document = deserialize(path.read_bytes())
            validate_document(document)
            validator.validate(document)

    def test_byte_stable_save_open_save(self) -> None:
        document = deserialize(
            (BUILD_FIXTURES / "flame-link.build-state-v3.json").read_bytes()
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.json"
            first = atomic_save(path, document)
            reopened, raw = deserialize(path.read_bytes()), path.read_bytes()
            self.assertEqual(raw, first)
            second = atomic_save(path, reopened)
            self.assertEqual(first, second)


class BuildStateV3MigrationTests(unittest.TestCase):
    def test_v2_to_v3_migration_inserts_defaults_without_fabricating_facts(self) -> None:
        source = v2_codec.deserialize(
            (BUILD_FIXTURES / "copied-enmity.build-state-v2.json").read_bytes()
        )
        migrated = migrate_v2_document(source)
        self.assertEqual(migrated["schemaVersion"], "3.0.0")
        self.assertEqual(migrated["applicationDataContractVersion"], "3.0.0")
        self.assertEqual(migrated["copiedItemEntries"], source["copiedItemEntries"])
        self.assertEqual(migrated["enmityManualInput"], source["enmityManualInput"])
        chain = migrated["flameLinkPlayerChain"]
        self.assertEqual(chain["flameLinkLevel"]["baseLevel"], 21)
        self.assertEqual(
            chain["flameLinkLevel"]["baseLevelProvenance"],
            "manual-benchmark-default",
        )
        self.assertEqual(chain["goldenGlory"]["allocatedState"], "unknown")
        self.assertEqual(chain["goldenGlory"]["reviewState"], "unreviewed")
        self.assertIsNone(chain["goldenGlory"]["reviewedLightRadiusPct"])
        self.assertEqual(
            chain["conditionalContributions"][0]["conditionState"], "unknown"
        )
        self.assertEqual(
            chain["flameLinkLevel"]["additionalLinkGemLevels"][0]["activeState"],
            "unknown",
        )

    def test_v1_migrates_through_v2_to_v3(self) -> None:
        source = legacy_codec.deserialize(
            (BUILD_FIXTURES / "empty.build-state-v1.json").read_bytes()
        )
        migrated = migrate_v1_document(source)
        self.assertEqual(migrated["schemaVersion"], "3.0.0")
        decoded = decode((BUILD_FIXTURES / "empty.build-state-v1.json").read_bytes())
        self.assertTrue(decoded.migrated)
        self.assertEqual(decoded.sourceSchemaVersion, "1.0.0")
        self.assertEqual(decoded.document["schemaVersion"], "3.0.0")
        expected = (BUILD_FIXTURES / "empty-migrated.build-state-v3.json").read_bytes()
        self.assertEqual(decoded.canonicalV3Bytes, expected)

    def test_v2_open_migrates_to_v3(self) -> None:
        raw = (BUILD_FIXTURES / "copied-enmity.build-state-v2.json").read_bytes()
        decoded = decode(raw)
        self.assertTrue(decoded.migrated)
        self.assertEqual(decoded.sourceSchemaVersion, "2.0.0")
        self.assertEqual(decoded.document["schemaVersion"], "3.0.0")

    def test_unknown_future_version_is_rejected(self) -> None:
        future = empty_document()
        future["schemaVersion"] = "4.0.0"
        with self.assertRaises(BuildStateError) as raised:
            deserialize(external_bytes(future))
        self.assertEqual(raised.exception.code, "SCHEMA_VERSION")

    def test_malformed_flame_link_rejected(self) -> None:
        document = empty_document()
        document["flameLinkPlayerChain"]["goldenGlory"]["allocatedState"] = "maybe"
        with self.assertRaises(BuildStateError) as raised:
            validate_document(document)
        self.assertEqual(raised.exception.code, "GOLDEN_GLORY_ALLOCATED_STATE")

        broken = empty_document()
        broken["flameLinkPlayerChain"]["extra"] = True
        with self.assertRaises(BuildStateError) as raised:
            validate_document(broken)
        self.assertEqual(raised.exception.code, "SHAPE_UNKNOWN_FIELD")

        missing = empty_document()
        del missing["flameLinkPlayerChain"]["formulaVersionId"]
        with self.assertRaises(BuildStateError) as raised:
            validate_document(missing)
        self.assertEqual(raised.exception.code, "SHAPE_MISSING_FIELD")

        bad_decimal = empty_document()
        bad_decimal["flameLinkPlayerChain"]["directLinkBuffEffect"][
            "reviewedDirectPct"
        ] = "1e2"
        with self.assertRaises(BuildStateError) as raised:
            validate_document(bad_decimal)
        self.assertEqual(raised.exception.code, "DECIMAL_TEXT_GRAMMAR")

    def test_v2_source_is_not_mutated_by_migration(self) -> None:
        source = v2_codec.deserialize(
            (BUILD_FIXTURES / "empty-migrated.build-state-v2.json").read_bytes()
        )
        before = copy.deepcopy(source)
        migrate_v2_document(source)
        self.assertEqual(source, before)
        self.assertNotIn("flameLinkPlayerChain", source)


if __name__ == "__main__":
    unittest.main()
