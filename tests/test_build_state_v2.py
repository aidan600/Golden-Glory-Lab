from __future__ import annotations

import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golden_glory_lab.build_state import (  # noqa: E402
    MAX_CONTEXT_FIELD_CHARACTERS,
    MAX_SAVED_STATE_FILE_BYTES,
    MEASUREMENT_CONTEXT_FIELDS,
    BuildStateError,
    atomic_save,
    decode,
    deserialize,
    empty_document,
    imported_result_digest,
    load_file,
    load_file_result,
    migrate_v1_document,
    serialize,
    validate_document,
)
from golden_glory_lab.build_state import codec as legacy_codec  # noqa: E402
from golden_glory_lab.domain import DECIMAL_DIGIT_LIMIT  # noqa: E402
from golden_glory_lab.desktop.service import ApplicationService  # noqa: E402
from golden_glory_lab.item_review import COPIED_ITEM_LIMITS, ReviewSourceLocator  # noqa: E402
from golden_glory_lab.pob_import import importPobRawXml  # noqa: E402

BUILD_FIXTURES = ROOT / "fixtures" / "build_state"
POB_FIXTURES = ROOT / "fixtures" / "pob" / "proof"


def v2_schema_validator() -> Draft202012Validator:
    schemas = [
        json.loads(
            (ROOT / "data" / "schemas" / name).read_text(encoding="utf-8")
        )
        for name in (
            "pob-neutral-import-v1.schema.json",
            "build-state-v2.schema.json",
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


def imported_v2(name: str = "comprehensive.xml") -> dict:
    result = importPobRawXml((POB_FIXTURES / name).read_text(encoding="utf-8"))
    assert result["status"] == "success"
    document = empty_document()
    document["importedResult"] = result
    document["importedResultSha256"] = imported_result_digest(result)
    return document


def copied_enmity_document() -> dict:
    return deserialize((BUILD_FIXTURES / "copied-enmity.build-state-v2.json").read_bytes())


class BuildStateV2RoundTripTests(unittest.TestCase):
    def test_empty_copied_and_enmity_documents_round_trip_deterministically(self) -> None:
        for document in (empty_document(), copied_enmity_document()):
            first = serialize(document)
            second = serialize(deserialize(first))
            with self.subTest(copied=bool(document["copiedItemEntries"])):
                self.assertEqual(first, second)
                self.assertEqual(deserialize(first), document)
                self.assertTrue(first.endswith(b"\n"))

    def test_exact_copied_text_and_decimal_lexemes_survive(self) -> None:
        document = copied_enmity_document()
        reopened = deserialize(serialize(document))
        copied = reopened["copiedItemEntries"][0]
        self.assertIn("\r\n", copied["rawText"])
        self.assertEqual(copied["rawText"], document["copiedItemEntries"][0]["rawText"])
        enmity = reopened["enmityManualInput"]
        self.assertEqual(enmity["finalUncappedFireResistance"], "0300.00")
        self.assertEqual(enmity["maximumFireResistance"], "075.0")
        self.assertEqual(enmity["target"], "200.0")

    def test_derived_and_session_values_are_never_persisted(self) -> None:
        encoded = serialize(copied_enmity_document())
        for prohibited in (
            b"recognitionState",
            b"recognitionReports",
            b"reviewInstanceId",
            b"gateDecision",
            b"inputBeyondCap",
            b"migrationPending",
            b"dirty",
            b"currentPath",
        ):
            self.assertNotIn(prohibited, encoded)

    def test_committed_v2_fixtures_are_runtime_and_schema_valid(self) -> None:
        validator = v2_schema_validator()
        names = {
            "empty-migrated.build-state-v2.json",
            "copied-enmity.build-state-v2.json",
        }
        observed = {path.name for path in BUILD_FIXTURES.glob("*.build-state-v2.json")}
        self.assertEqual(observed, names)
        for path in sorted(BUILD_FIXTURES.glob("*.build-state-v2.json")):
            document = deserialize(path.read_bytes())
            validate_document(document)
            validator.validate(document)


class BuildStateV1MigrationTests(unittest.TestCase):
    def test_all_v1_fixtures_validate_before_migration_and_preserve_v1_content(self) -> None:
        for path in sorted(BUILD_FIXTURES.glob("*.build-state-v1.json")):
            source = legacy_codec.deserialize(path.read_bytes())
            decoded = decode(path.read_bytes())
            with self.subTest(path=path.name):
                self.assertTrue(decoded.migrated)
                self.assertEqual(decoded.sourceSchemaVersion, "1.0.0")
                self.assertEqual(decoded.document["schemaVersion"], "2.0.0")
                for field in (
                    "importedResult",
                    "importedResultSha256",
                    "playerItemSetOccurrenceId",
                    "mercenarySourceMode",
                    "mercenaryItemSetOccurrenceId",
                    "manualMercenaryEquipment",
                    "userNotes",
                ):
                    self.assertEqual(decoded.document[field], source[field])
                self.assertEqual(decoded.document["copiedItemEntries"], [])
                self.assertIsNone(
                    decoded.document["enmityManualInput"]["finalUncappedFireResistance"]
                )
                self.assertEqual(
                    decoded.document["enmityManualInput"]["equipmentInclusionState"],
                    "unrecorded",
                )
                self.assertEqual(decoded.canonicalV2Bytes, serialize(decoded.document))

    def test_empty_v1_migration_matches_committed_expected_fixture(self) -> None:
        source = (BUILD_FIXTURES / "empty.build-state-v1.json").read_bytes()
        expected = (BUILD_FIXTURES / "empty-migrated.build-state-v2.json").read_bytes()
        self.assertEqual(decode(source).canonicalV2Bytes, expected)

    def test_service_open_is_upgrade_pending_dirty_and_never_writes_until_save(self) -> None:
        source = (BUILD_FIXTURES / "mapped.build-state-v1.json").read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "legacy.json"
            path.write_bytes(source)
            service = ApplicationService()
            service.open(path)
            self.assertEqual(path.read_bytes(), source)
            self.assertTrue(service.migration_pending)
            self.assertTrue(service.dirty)
            self.assertEqual(service.file_state, "upgrade-pending")
            self.assertEqual(service.state["schemaVersion"], "2.0.0")
            saved = service.save()
            self.assertEqual(path.read_bytes(), saved)
            self.assertFalse(service.migration_pending)
            self.assertFalse(service.dirty)
            self.assertEqual(service.file_state, "saved")
            reopened = ApplicationService()
            reopened.open(path)
            self.assertFalse(reopened.migration_pending)
            self.assertEqual(reopened.canonical_bytes, saved)

    def test_unknown_future_version_is_rejected(self) -> None:
        future = empty_document()
        future["schemaVersion"] = "3.0.0"
        with self.assertRaises(BuildStateError) as raised:
            deserialize(external_bytes(future))
        self.assertEqual(raised.exception.code, "SCHEMA_VERSION")


class BuildStateV2ReferenceTests(unittest.TestCase):
    def test_dangling_copied_manual_and_pob_references_are_rejected(self) -> None:
        cases = []
        for provenance in ("copied-text", "manual-entry", "pob-import"):
            document = empty_document()
            document["enmityManualInput"]["observedItemReference"] = {
                "provenanceKind": provenance,
                "sourceId": "missing-0001",
            }
            cases.append((provenance, document))
        for provenance, document in cases:
            with self.subTest(provenance=provenance), self.assertRaises(
                BuildStateError
            ) as raised:
                validate_document(document)
            self.assertEqual(raised.exception.code, "DANGLING_OBSERVED_ITEM_REFERENCE")

    def test_referenced_copied_deletion_confirmation_is_atomic(self) -> None:
        service = ApplicationService()
        identifier = service.add_copied_entry(
            "Item Class: Rings\nRarity: Rare\nSynthetic\nVermillion Ring\n",
        )
        locator = ReviewSourceLocator("copied-text", identifier)
        service.set_enmity_input(observed_item_reference=locator)
        before = service.state
        self.assertFalse(service.delete_copied_entry(identifier, confirmed=False))
        self.assertEqual(service.state, before)
        with self.assertRaises(BuildStateError) as raised:
            service.delete_copied_entry(identifier, confirmed=True)
        self.assertEqual(
            raised.exception.code, "OBSERVED_REFERENCE_CLEAR_CONFIRMATION_REQUIRED"
        )
        self.assertEqual(service.state, before)
        self.assertTrue(
            service.delete_copied_entry(
                identifier,
                confirmed=True,
                clear_observed_reference=True,
            )
        )
        self.assertEqual(service.state["copiedItemEntries"], [])
        self.assertIsNone(service.state["enmityManualInput"]["observedItemReference"])

    def test_referenced_manual_deletion_confirmation_is_atomic(self) -> None:
        service = ApplicationService()
        service.set_mercenary_source("manual-equipment")
        identifier = service.add_manual_entry("Ring 1", "Opaque")
        service.set_enmity_input(
            observed_item_reference=ReviewSourceLocator("manual-entry", identifier)
        )
        before = service.state
        with self.assertRaises(BuildStateError):
            service.delete_manual_entry(identifier, confirmed=True)
        self.assertEqual(service.state, before)
        service.delete_manual_entry(
            identifier,
            confirmed=True,
            clear_observed_reference=True,
        )
        self.assertIsNone(service.state["enmityManualInput"]["observedItemReference"])

    def test_replacing_referenced_pob_source_requires_atomic_clear(self) -> None:
        service = ApplicationService()
        self.assertEqual(
            service.attempt_raw_xml(POB_FIXTURES / "reimport-before.xml"), "imported"
        )
        service.set_enmity_input(
            observed_item_reference=ReviewSourceLocator("pob-import", "item-0001")
        )
        before = service.state
        self.assertEqual(
            service.attempt_raw_xml(POB_FIXTURES / "reimport-after.xml"),
            "confirmation-required",
        )
        with self.assertRaises(BuildStateError) as raised:
            service.confirm_pending_import(True)
        self.assertEqual(
            raised.exception.code, "OBSERVED_REFERENCE_CLEAR_CONFIRMATION_REQUIRED"
        )
        self.assertEqual(service.state, before)
        self.assertIsNotNone(service.pending_import_result)
        self.assertEqual(
            service.confirm_pending_import(True, clear_observed_reference=True),
            "replaced",
        )
        self.assertIsNone(service.state["enmityManualInput"]["observedItemReference"])
        self.assertIsNone(service.state["playerItemSetOccurrenceId"])
        self.assertEqual(service.state["mercenarySourceMode"], "not-yet-selected")


class BuildStateV2BoundaryAndTransactionTests(unittest.TestCase):
    def test_saved_state_limit_arithmetic_is_stable_and_producer_derived(self) -> None:
        copied_characters = COPIED_ITEM_LIMITS["maxEntries"] * (
            COPIED_ITEM_LIMITS["maxEntryIdCharacters"]
            + COPIED_ITEM_LIMITS["maxRawTextCharacters"]
            + len("unassigned")
            + COPIED_ITEM_LIMITS["maxSlotLabelCharacters"]
            + COPIED_ITEM_LIMITS["maxUserLabelCharacters"]
            + COPIED_ITEM_LIMITS["maxNoteCharacters"]
        )
        decimal_characters = DECIMAL_DIGIT_LIMIT + 2
        enmity_characters = (
            3 * decimal_characters
            + len("not-equipped")
            + len("unrecorded")
            + len("confirmed-3.29.1")
            + len(MEASUREMENT_CONTEXT_FIELDS) * MAX_CONTEXT_FIELD_CHARACTERS
            + len("manual-entry")
            + COPIED_ITEM_LIMITS["maxEntryIdCharacters"]
        )
        expected = legacy_codec.MAX_SAVED_STATE_FILE_BYTES + 12 * (
            copied_characters + enmity_characters
        )
        self.assertEqual(expected, 682_649_696)
        self.assertEqual(MAX_SAVED_STATE_FILE_BYTES, expected)

    def test_v2_exact_boundary_and_growth_protections(self) -> None:
        expected = serialize(empty_document())
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.json"
            path.write_bytes(expected)
            with patch(
                "golden_glory_lab.build_state.codec_v2.MAX_SAVED_STATE_FILE_BYTES",
                len(expected),
            ):
                loaded, raw = load_file(path)
            self.assertEqual(loaded, empty_document())
            self.assertEqual(raw, expected)

            path.write_bytes(expected + b" ")
            with (
                patch(
                    "golden_glory_lab.build_state.codec_v2.MAX_SAVED_STATE_FILE_BYTES",
                    len(expected),
                ),
                patch.object(
                    Path,
                    "open",
                    side_effect=AssertionError("over-limit input must not open"),
                ),
                self.assertRaises(BuildStateError) as raised,
            ):
                load_file(path)
            self.assertEqual(raised.exception.code, "OPEN_FILE_TOO_LARGE")

            path.write_bytes(expected)
            with (
                patch(
                    "golden_glory_lab.build_state.codec_v2.MAX_SAVED_STATE_FILE_BYTES",
                    len(expected),
                ),
                patch.object(Path, "stat", return_value=SimpleNamespace(st_size=len(expected))),
                patch.object(Path, "open", return_value=io.BytesIO(expected + b" ")),
                self.assertRaises(BuildStateError) as raised,
            ):
                load_file(path)
            self.assertEqual(raised.exception.code, "OPEN_FILE_GREW")

    def test_failed_v2_open_preserves_complete_prior_session(self) -> None:
        mutations = []
        missing_copied_key = copied_enmity_document()
        del missing_copied_key["copiedItemEntries"][0]["role"]
        mutations.append(missing_copied_key)

        bad_decimal = copied_enmity_document()
        bad_decimal["enmityManualInput"]["target"] = "1e2"
        mutations.append(bad_decimal)

        missing_context = copied_enmity_document()
        del missing_context["enmityManualInput"]["measurementContext"][
            "captureTimingDescription"
        ]
        mutations.append(missing_context)

        dangling = copied_enmity_document()
        dangling["enmityManualInput"]["observedItemReference"]["sourceId"] = "missing"
        mutations.append(dangling)

        future = copied_enmity_document()
        future["schemaVersion"] = "99.0.0"
        mutations.append(future)

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            prior_path = directory / "prior.json"
            service = ApplicationService()
            service.add_copied_entry("opaque", role="player")
            service.save(prior_path)
            before = (
                service.state,
                service.canonical_bytes,
                service.current_path,
                service.dirty,
                service.migration_pending,
            )
            for index, mutation in enumerate(mutations):
                path = directory / f"bad-{index}.json"
                path.write_bytes(external_bytes(mutation))
                with self.subTest(index=index), self.assertRaises(BuildStateError):
                    service.open(path)
                self.assertEqual(
                    (
                        service.state,
                        service.canonical_bytes,
                        service.current_path,
                        service.dirty,
                        service.migration_pending,
                    ),
                    before,
                )

    def test_atomic_save_failure_preserves_prior_bytes(self) -> None:
        document = copied_enmity_document()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.json"
            path.write_bytes(b"prior")

            def fail_replace(_source: object, _destination: object) -> None:
                raise OSError("simulated")

            with self.assertRaises(BuildStateError) as raised:
                atomic_save(path, document, replace=fail_replace)
            self.assertEqual(raised.exception.code, "SAVE_FAILED")
            self.assertEqual(path.read_bytes(), b"prior")
            self.assertEqual(list(path.parent.glob(".state.json.*.tmp")), [])

    def test_load_file_result_reports_migration_without_losing_raw_bytes(self) -> None:
        raw = (BUILD_FIXTURES / "manual.build-state-v1.json").read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manual-v1.json"
            path.write_bytes(raw)
            decoded, observed = load_file_result(path)
        self.assertTrue(decoded.migrated)
        self.assertEqual(observed, raw)
        self.assertEqual(decoded.document, migrate_v1_document(legacy_codec.deserialize(raw)))


class BuildStateV2SchemaRuntimeParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = v2_schema_validator()

    def test_each_new_consumed_field_has_shared_runtime_schema_rejections(self) -> None:
        base = copied_enmity_document()
        shared: list[tuple[str, dict]] = []

        for field in ("entryId", "rawText", "role", "slotLabel", "userLabel", "note"):
            mutation = copy.deepcopy(base)
            del mutation["copiedItemEntries"][0][field]
            shared.append((f"copied-missing-{field}", mutation))

        bad_role = copy.deepcopy(base)
        bad_role["copiedItemEntries"][0]["role"] = "inferred-owner"
        shared.append(("copied-role", bad_role))
        bad_label = copy.deepcopy(base)
        bad_label["copiedItemEntries"][0]["userLabel"] = "x" * 81
        shared.append(("copied-label-limit", bad_label))
        bad_raw = copy.deepcopy(base)
        bad_raw["copiedItemEntries"][0]["rawText"] = ""
        shared.append(("copied-empty-raw", bad_raw))

        for field in (
            "finalUncappedFireResistance",
            "maximumFireResistance",
            "equippedState",
            "equipmentInclusionState",
            "measurementContext",
            "targetGameVersionAcknowledgement",
            "observedItemReference",
            "target",
        ):
            mutation = copy.deepcopy(base)
            del mutation["enmityManualInput"][field]
            shared.append((f"enmity-missing-{field}", mutation))

        for field in (
            "finalUncappedFireResistance",
            "maximumFireResistance",
            "target",
        ):
            mutation = copy.deepcopy(base)
            mutation["enmityManualInput"][field] = "+75"
            shared.append((f"decimal-{field}", mutation))

        bad_equipped = copy.deepcopy(base)
        bad_equipped["enmityManualInput"]["equippedState"] = "recognized-item"
        shared.append(("equipped-enum", bad_equipped))
        bad_inclusion = copy.deepcopy(base)
        bad_inclusion["enmityManualInput"]["equipmentInclusionState"] = "missing"
        shared.append(("inclusion-enum", bad_inclusion))
        bad_ack = copy.deepcopy(base)
        bad_ack["enmityManualInput"]["targetGameVersionAcknowledgement"] = "inferred"
        shared.append(("ack-enum", bad_ack))

        for context_field in MEASUREMENT_CONTEXT_FIELDS:
            mutation = copy.deepcopy(base)
            del mutation["enmityManualInput"]["measurementContext"][context_field]
            shared.append((f"context-{context_field}", mutation))
        long_context = copy.deepcopy(base)
        long_context["enmityManualInput"]["measurementContext"][
            "zoneOrUiContext"
        ] = "x" * (MAX_CONTEXT_FIELD_CHARACTERS + 1)
        shared.append(("context-limit", long_context))

        bad_locator = copy.deepcopy(base)
        bad_locator["enmityManualInput"]["observedItemReference"][
            "provenanceKind"
        ] = "tree-row"
        shared.append(("locator-provenance", bad_locator))
        locator_extra = copy.deepcopy(base)
        locator_extra["enmityManualInput"]["observedItemReference"]["rowId"] = "I001"
        shared.append(("locator-presentation-id", locator_extra))

        for name, mutation in shared:
            with self.subTest(name=name):
                with self.assertRaises(BuildStateError):
                    validate_document(mutation)
                with self.assertRaises(ValidationError):
                    self.validator.validate(mutation)

    def test_runtime_only_uniqueness_utf8_and_reference_resolution_rules(self) -> None:
        duplicate = copied_enmity_document()
        duplicate["copiedItemEntries"].append(
            copy.deepcopy(duplicate["copiedItemEntries"][0])
        )
        self.validator.validate(duplicate)
        with self.assertRaises(BuildStateError) as raised:
            validate_document(duplicate)
        self.assertEqual(raised.exception.code, "COPIED_ENTRY_ID")

        lone_surrogate = copied_enmity_document()
        lone_surrogate["copiedItemEntries"][0]["rawText"] = "\ud800"
        self.validator.validate(lone_surrogate)
        with self.assertRaises(BuildStateError) as raised:
            validate_document(lone_surrogate)
        self.assertEqual(raised.exception.code, "STRICT_UTF8_REQUIRED")

        dangling = copied_enmity_document()
        dangling["enmityManualInput"]["observedItemReference"]["sourceId"] = "other"
        self.validator.validate(dangling)
        with self.assertRaises(BuildStateError) as raised:
            validate_document(dangling)
        self.assertEqual(raised.exception.code, "DANGLING_OBSERVED_ITEM_REFERENCE")


class TransactionalOpenBoundaryTests(unittest.TestCase):
    def _snapshot(self, service: ApplicationService) -> tuple:
        return (
            service.state,
            service.canonical_bytes,
            service.current_path,
            service.dirty,
            service.file_state,
            service.migration_pending,
            service.state["playerItemSetOccurrenceId"],
            service.state["mercenarySourceMode"],
            service.state["mercenaryItemSetOccurrenceId"],
            service.state["copiedItemEntries"],
            service.state["manualMercenaryEquipment"],
            service.state["enmityManualInput"],
            service.state["userNotes"],
            service.pending_import_result,
            service.last_failed_import,
        )

    def _saved_mapped_session(self, directory: Path) -> ApplicationService:
        service = ApplicationService()
        document = imported_v2()
        document["playerItemSetOccurrenceId"] = "item-set-0001"
        document["mercenarySourceMode"] = "mapped-item-set"
        document["mercenaryItemSetOccurrenceId"] = "item-set-0002"
        document["copiedItemEntries"] = [
            {
                "entryId": "copied-0001",
                "rawText": "Rarity: Unique\nOpaque Copied\nSynthetic Base",
                "role": "player",
                "slotLabel": "Ring 1",
                "userLabel": "Prior",
                "note": "keep",
            }
        ]
        document["manualMercenaryEquipment"] = [
            {
                "entryId": "manual-0001",
                "slotLabel": "Ring 2",
                "rawText": "Opaque manual",
                "reviewState": "unparsed-manual",
                "note": "manual",
            }
        ]
        document["enmityManualInput"]["finalUncappedFireResistance"] = "300"
        document["enmityManualInput"]["maximumFireResistance"] = "75"
        document["enmityManualInput"]["equippedState"] = "equipped"
        document["enmityManualInput"]["equipmentInclusionState"] = "included"
        document["enmityManualInput"]["targetGameVersionAcknowledgement"] = (
            "confirmed-3.29.1"
        )
        document["enmityManualInput"]["measurementContext"] = {
            field: f"context-{field}" for field in MEASUREMENT_CONTEXT_FIELDS
        }
        document["enmityManualInput"]["observedItemReference"] = {
            "provenanceKind": "copied-text",
            "sourceId": "copied-0001",
        }
        document["userNotes"] = "baseline notes"
        path = directory / "prior.json"
        path.write_bytes(serialize(document))
        service.open(path)
        service.add_copied_entry("extra retained", role="unassigned")
        self.assertTrue(service.dirty)
        return service

    def _assert_refreshable(self, service: ApplicationService) -> None:
        reviews = service.item_reviews()
        self.assertTrue(reviews)
        self.assertTrue(service.item_reviews(provenance="copied-text"))
        self.assertIsNotNone(service.enmity_result())
        self.assertIsNotNone(service.runtime_evidence_status())

    def test_surrogate_and_nesting_failures_preserve_complete_session(self) -> None:
        mutations: list[tuple[str, dict]] = []

        copied_id = copied_enmity_document()
        copied_id["copiedItemEntries"][0]["entryId"] = "\ud800"
        mutations.append(("copied-id", copied_id))

        copied_raw = copied_enmity_document()
        copied_raw["copiedItemEntries"][0]["rawText"] = "\ud800"
        mutations.append(("copied-raw", copied_raw))

        manual = imported_v2()
        manual["mercenarySourceMode"] = "manual-equipment"
        manual["manualMercenaryEquipment"] = [
            {
                "entryId": "\ud800",
                "slotLabel": "Ring",
                "rawText": "opaque",
                "reviewState": "unparsed-manual",
                "note": "",
            }
        ]
        mutations.append(("manual-id", manual))

        manual_raw = imported_v2()
        manual_raw["mercenarySourceMode"] = "manual-equipment"
        manual_raw["manualMercenaryEquipment"] = [
            {
                "entryId": "manual-0001",
                "slotLabel": "Ring",
                "rawText": "\ud800",
                "reviewState": "unparsed-manual",
                "note": "",
            }
        ]
        mutations.append(("manual-raw", manual_raw))

        imported = imported_v2()
        imported["importedResult"]["document"]["items"][0]["occurrenceId"] = "\ud800"
        imported["importedResultSha256"] = imported_result_digest(
            imported["importedResult"]
        )
        mutations.append(("imported-id", imported))

        imported_raw = imported_v2()
        imported_raw["importedResult"]["document"]["items"][0][
            "xmlCharacterValue"
        ] = "\ud800"
        imported_raw["importedResultSha256"] = imported_result_digest(
            imported_raw["importedResult"]
        )
        mutations.append(("imported-raw", imported_raw))

        bad_locator = copied_enmity_document()
        bad_locator["enmityManualInput"]["observedItemReference"] = {
            "provenanceKind": "copied-text",
            "sourceId": "\ud800",
        }
        mutations.append(("locator", bad_locator))

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            service = self._saved_mapped_session(directory)
            before = self._snapshot(service)
            for name, mutation in mutations:
                path = directory / f"bad-{name}.json"
                path.write_bytes(external_bytes(mutation))
                with self.subTest(name=name), self.assertRaises(BuildStateError) as raised:
                    service.open(path)
                self.assertEqual(raised.exception.code, "STRICT_UTF8_REQUIRED")
                self.assertEqual(self._snapshot(service), before)
                self._assert_refreshable(service)

            nesting_path = directory / "nesting.json"
            nesting_path.write_bytes(serialize(copied_enmity_document()))
            with (
                patch(
                    "golden_glory_lab.desktop.service.copy.deepcopy",
                    side_effect=RecursionError("simulated"),
                ),
                self.assertRaises(BuildStateError) as raised,
            ):
                service.open(nesting_path)
            self.assertEqual(raised.exception.code, "OPEN_STATE_NESTING")
            self.assertEqual(self._snapshot(service), before)
            self._assert_refreshable(service)

            migration_path = directory / "migration-v1.json"
            migration_path.write_bytes(
                (BUILD_FIXTURES / "manual.build-state-v1.json").read_bytes()
            )
            with (
                patch(
                    "golden_glory_lab.build_state.codec_v2.copy.deepcopy",
                    side_effect=RecursionError("simulated migration"),
                ),
                self.assertRaises(BuildStateError) as raised,
            ):
                service.open(migration_path)
            self.assertEqual(raised.exception.code, "MIGRATION_NESTING")
            self.assertEqual(self._snapshot(service), before)
            self._assert_refreshable(service)

    def test_moderately_deep_retained_material_still_opens(self) -> None:
        document = imported_v2()
        nested: dict = {"leaf": "retained"}
        current = nested
        for index in range(40):
            nxt = {"level": index}
            current["child"] = nxt
            current = nxt
        document["importedResult"]["document"]["items"][0][
            "orderedChildMaterial"
        ].append({"kind": "opaque-retained", "value": nested})
        document["importedResultSha256"] = imported_result_digest(
            document["importedResult"]
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "deep.json"
            path.write_bytes(serialize(document))
            service = ApplicationService()
            service.open(path)
            self.assertFalse(service.dirty)
            self.assertEqual(len(service.item_reviews()), len(document["importedResult"]["document"]["items"]))


if __name__ == "__main__":
    unittest.main()
