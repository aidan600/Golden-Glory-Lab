from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golden_glory_lab.build_state import (  # noqa: E402
    BuildStateError,
    atomic_save,
    deserialize,
    empty_document,
    imported_result_digest,
    load_file,
    serialize,
    validate_document,
)
from golden_glory_lab.desktop.service import ApplicationService  # noqa: E402
from golden_glory_lab.pob_import import importPobRawXml  # noqa: E402

POB_FIXTURES = ROOT / "fixtures" / "pob" / "proof"


def fixture_text(name: str) -> str:
    return (POB_FIXTURES / name).read_text(encoding="utf-8")


def imported_document(name: str = "comprehensive.xml") -> dict:
    result = importPobRawXml(fixture_text(name))
    assert result["status"] == "success"
    document = empty_document()
    document["importedResult"] = result
    document["importedResultSha256"] = imported_result_digest(result)
    return document


def schema_validator() -> Draft202012Validator:
    build_schema = json.loads(
        (ROOT / "data" / "schemas" / "build-state-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    neutral_schema = json.loads(
        (ROOT / "data" / "schemas" / "pob-neutral-import-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(neutral_schema)
    Draft202012Validator.check_schema(build_schema)
    registry = Registry().with_resources(
        [
            (
                neutral_schema["$id"],
                Resource.from_contents(neutral_schema),
            ),
            (
                build_schema["$id"],
                Resource.from_contents(build_schema),
            ),
        ]
    )
    return Draft202012Validator(build_schema, registry=registry)


class BuildStateCodecTests(unittest.TestCase):
    def test_empty_imported_mapped_and_manual_round_trips(self) -> None:
        empty = empty_document()
        imported = imported_document()
        mapped = copy.deepcopy(imported)
        mapped["playerItemSetOccurrenceId"] = "item-set-0001"
        mapped["mercenarySourceMode"] = "mapped-item-set"
        mapped["mercenaryItemSetOccurrenceId"] = "item-set-0002"
        manual = copy.deepcopy(imported)
        manual["playerItemSetOccurrenceId"] = "item-set-0001"
        manual["mercenarySourceMode"] = "manual-equipment"
        manual["manualMercenaryEquipment"] = [
            {
                "entryId": "manual-0001",
                "slotLabel": "Ring 1",
                "rawText": "Exact +999% observed text\r\nwith original line ending",
                "reviewState": "unparsed-manual",
                "note": "Opaque and unclamped.",
            }
        ]
        for name, document in (
            ("empty", empty),
            ("imported", imported),
            ("mapped", mapped),
            ("manual", manual),
        ):
            with self.subTest(name=name):
                encoded = serialize(document)
                self.assertEqual(deserialize(encoded), document)
                self.assertEqual(encoded, serialize(deserialize(encoded)))
                self.assertTrue(encoded.endswith(b"\n"))

    def test_imported_result_order_and_digest_survive_build_serialization(self) -> None:
        document = imported_document()
        encoded = serialize(document)
        reopened = deserialize(encoded)
        self.assertEqual(
            reopened["importedResultSha256"],
            imported_result_digest(reopened["importedResult"]),
        )
        self.assertEqual(encoded, serialize(reopened))

    def test_runtime_preserves_unconsumed_importer_owned_material(self) -> None:
        document = imported_document("equivalent.xml")
        document["importedResult"]["futureOpaqueImporterMaterial"] = {
            "preserved": ["without", "runtime", "interpretation"]
        }
        document["importedResultSha256"] = imported_result_digest(
            document["importedResult"]
        )
        reopened = deserialize(serialize(document))
        self.assertEqual(
            reopened["importedResult"]["futureOpaqueImporterMaterial"],
            {"preserved": ["without", "runtime", "interpretation"]},
        )

    def test_atomic_failure_preserves_prior_file_and_cleans_temporary(self) -> None:
        prior = empty_document()
        changed = copy.deepcopy(prior)
        changed["userNotes"] = "new content"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.json"
            path.write_bytes(serialize(prior))

            def fail_replace(_source: object, _destination: object) -> None:
                raise OSError("simulated replace failure")

            with self.assertRaises(BuildStateError) as raised:
                atomic_save(path, changed, replace=fail_replace)
            self.assertEqual(raised.exception.code, "SAVE_FAILED")
            self.assertEqual(path.read_bytes(), serialize(prior))
            self.assertEqual(list(path.parent.glob(f".{path.name}.*.tmp")), [])

    def test_malformed_wrong_type_versions_digest_and_mappings_are_rejected(self) -> None:
        base = imported_document()
        mutations = []
        wrong_type = copy.deepcopy(base)
        wrong_type["documentType"] = "other"
        mutations.append(("DOCUMENT_TYPE", wrong_type))
        future = copy.deepcopy(base)
        future["schemaVersion"] = "2.0.0"
        mutations.append(("SCHEMA_VERSION", future))
        importer_future = copy.deepcopy(base)
        importer_future["importerContractVersion"] = "2.0.0"
        mutations.append(("IMPORTER_CONTRACT_VERSION", importer_future))
        bad_digest = copy.deepcopy(base)
        bad_digest["importedResultSha256"] = "0" * 64
        mutations.append(("IMPORTED_RESULT_DIGEST", bad_digest))
        dangling = copy.deepcopy(base)
        dangling["playerItemSetOccurrenceId"] = "item-set-9999"
        mutations.append(("DANGLING_PLAYER_MAPPING", dangling))
        same = copy.deepcopy(base)
        same["playerItemSetOccurrenceId"] = "item-set-0001"
        same["mercenarySourceMode"] = "mapped-item-set"
        same["mercenaryItemSetOccurrenceId"] = "item-set-0001"
        mutations.append(("SAME_OCCURRENCE_MAPPING", same))
        for code, mutation in mutations:
            with self.subTest(code=code):
                with self.assertRaises(BuildStateError) as raised:
                    validate_document(mutation)
                self.assertEqual(raised.exception.code, code)

        for value, code in (
            (b"{", "OPEN_JSON"),
            (b'{"value": NaN}', "JSON_NONFINITE"),
            (b'{"value": 1, "value": 2}', "JSON_DUPLICATE_KEY"),
            (b"\xff", "OPEN_UTF8"),
        ):
            with self.subTest(code=code):
                with self.assertRaises(BuildStateError) as raised:
                    deserialize(value)
                self.assertEqual(raised.exception.code, code)

    def test_failed_open_preserves_current_service_state(self) -> None:
        service = ApplicationService()
        service.set_user_notes("keep this")
        before = service.state
        before_bytes = service.canonical_bytes
        with tempfile.TemporaryDirectory() as temporary:
            invalid = Path(temporary) / "invalid.json"
            invalid.write_text("{", encoding="utf-8")
            with self.assertRaises(BuildStateError):
                service.open(invalid)
        self.assertEqual(service.state, before)
        self.assertEqual(service.canonical_bytes, before_bytes)
        self.assertIsNone(service.current_path)

    def test_volatile_session_fields_never_appear_in_saved_json(self) -> None:
        service = ApplicationService()
        service.set_user_notes("canonical")
        service.last_failed_import = {
            "kind": "test",
            "code": "TRANSIENT",
            "stage": "desktop-intake",
            "message": "not persisted",
            "report": [],
        }
        encoded = service.canonical_bytes
        prohibited = (
            b"current_path",
            b"currentPath",
            b"dirty",
            b"saved",
            b"last_failed",
            b"lastFailed",
            b"readiness",
            b"windowGeometry",
            b"selectedTab",
            b"calculated",
        )
        for field in prohibited:
            self.assertNotIn(field, encoded)


class BuildStateSchemaParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = schema_validator()

    def test_representative_runtime_valid_documents_match_schema(self) -> None:
        documents = [empty_document(), imported_document("equivalent.xml")]
        mapped = imported_document()
        mapped["playerItemSetOccurrenceId"] = "item-set-0001"
        mapped["mercenarySourceMode"] = "mapped-item-set"
        mapped["mercenaryItemSetOccurrenceId"] = "item-set-0002"
        documents.append(mapped)
        manual = imported_document()
        manual["mercenarySourceMode"] = "manual-equipment"
        manual["manualMercenaryEquipment"] = [
            {
                "entryId": "manual-0001",
                "slotLabel": "Ring 1",
                "rawText": "Opaque text",
                "reviewState": "unparsed-manual",
                "note": "",
            }
        ]
        documents.append(manual)
        for document in documents:
            validate_document(document)
            self.validator.validate(document)

    def test_schema_and_runtime_negative_roles_are_explicit(self) -> None:
        missing = empty_document()
        del missing["userNotes"]
        with self.assertRaises(BuildStateError):
            validate_document(missing)
        with self.assertRaises(ValidationError):
            self.validator.validate(missing)

        wrong_manual = empty_document()
        wrong_manual["manualMercenaryEquipment"] = [
            {
                "entryId": "manual-0001",
                "slotLabel": "",
                "rawText": "x",
                "reviewState": "parsed",
                "note": "",
            }
        ]
        with self.assertRaises(BuildStateError):
            validate_document(wrong_manual)
        with self.assertRaises(ValidationError):
            self.validator.validate(wrong_manual)

        same = imported_document()
        same["playerItemSetOccurrenceId"] = "item-set-0001"
        same["mercenarySourceMode"] = "mapped-item-set"
        same["mercenaryItemSetOccurrenceId"] = "item-set-0001"
        self.validator.validate(same)
        with self.assertRaises(BuildStateError) as raised:
            validate_document(same)
        self.assertEqual(raised.exception.code, "SAME_OCCURRENCE_MAPPING")

    def test_file_loader_returns_validated_content_and_bytes(self) -> None:
        document = imported_document("equivalent.xml")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.json"
            expected = serialize(document)
            path.write_bytes(expected)
            loaded, raw = load_file(path)
        self.assertEqual(loaded, document)
        self.assertEqual(raw, expected)

    def test_committed_valid_fixtures_are_runtime_and_schema_valid(self) -> None:
        fixtures = ROOT / "fixtures" / "build_state"
        names = {
            "empty.build-state-v1.json",
            "imported.build-state-v1.json",
            "mapped.build-state-v1.json",
            "manual.build-state-v1.json",
        }
        self.assertEqual({path.name for path in fixtures.glob("*.json")}, names)
        for path in sorted(fixtures.glob("*.json")):
            data = path.read_bytes()
            document = deserialize(data)
            self.validator.validate(document)

if __name__ == "__main__":
    unittest.main()
