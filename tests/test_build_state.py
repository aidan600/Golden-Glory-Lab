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
    BuildStateError,
    MAX_SAVED_STATE_FILE_BYTES,
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


def external_document_bytes(document: dict) -> bytes:
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


def refresh_imported_digest(document: dict) -> None:
    document["importedResultSha256"] = imported_result_digest(
        document["importedResult"]
    )


def malformed_item_mutations(document: dict) -> list[tuple[str, dict, str]]:
    delete_field = object()
    usage_counts = {
        "equipmentCandidateReferenceCount": 0,
        "passiveCandidateReferenceCount": 0,
    }
    cases: list[tuple[str, str, object, str]] = [
        ("missing-raw-id", "rawId", delete_field, "NEUTRAL_RESULT_SHAPE"),
        ("null-raw-id", "rawId", None, "SHAPE_TYPE"),
        ("scalar-raw-id", "rawId", "bad", "SHAPE_TYPE"),
        ("array-raw-id", "rawId", [], "SHAPE_TYPE"),
        ("numeric-raw-id", "rawId", 7, "SHAPE_TYPE"),
        ("raw-id-missing-state", "rawId", {"value": None}, "NEUTRAL_RESULT_SHAPE"),
        ("raw-id-missing-value", "rawId", {"state": "missing"}, "NEUTRAL_RESULT_SHAPE"),
        (
            "raw-id-extra-field",
            "rawId",
            {"state": "missing", "value": None, "extra": True},
            "NEUTRAL_RESULT_SHAPE",
        ),
        (
            "raw-id-invalid-state",
            "rawId",
            {"state": "other", "value": None},
            "NEUTRAL_RESULT_SHAPE",
        ),
        (
            "raw-id-inconsistent-value",
            "rawId",
            {"state": "missing", "value": ""},
            "NEUTRAL_RESULT_SHAPE",
        ),
        ("missing-usage", "usage", delete_field, "NEUTRAL_RESULT_SHAPE"),
        ("null-usage", "usage", None, "SHAPE_TYPE"),
        ("scalar-usage", "usage", "bad", "SHAPE_TYPE"),
        ("array-usage", "usage", [], "SHAPE_TYPE"),
        ("numeric-usage", "usage", 7, "SHAPE_TYPE"),
        ("usage-missing-state", "usage", usage_counts, "NEUTRAL_RESULT_SHAPE"),
        (
            "usage-nonstring-state",
            "usage",
            {"state": 1, **usage_counts},
            "SHAPE_TYPE",
        ),
        (
            "usage-unsupported-state",
            "usage",
            {"state": "other", **usage_counts},
            "NEUTRAL_RESULT_SHAPE",
        ),
        (
            "missing-item-source-index",
            "sourceOccurrenceIndex",
            delete_field,
            "NEUTRAL_RESULT_SHAPE",
        ),
        (
            "negative-item-source-index",
            "sourceOccurrenceIndex",
            -1,
            "NEUTRAL_RESULT_SHAPE",
        ),
        (
            "boolean-item-source-index",
            "sourceOccurrenceIndex",
            True,
            "NEUTRAL_RESULT_SHAPE",
        ),
        (
            "string-item-source-index",
            "sourceOccurrenceIndex",
            "0",
            "NEUTRAL_RESULT_SHAPE",
        ),
        (
            "float-item-source-index",
            "sourceOccurrenceIndex",
            0.5,
            "NEUTRAL_RESULT_SHAPE",
        ),
        (
            "null-item-source-index",
            "sourceOccurrenceIndex",
            None,
            "NEUTRAL_RESULT_SHAPE",
        ),
    ]
    mutations: list[tuple[str, dict, str]] = []
    for name, field, value, expected_code in cases:
        candidate = copy.deepcopy(document)
        item = candidate["importedResult"]["document"]["items"][0]
        if value is delete_field:
            del item[field]
        else:
            item[field] = copy.deepcopy(value)
        mutations.append((name, candidate, expected_code))
    return mutations


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

    def test_report_retained_material_remains_opaque_and_preserved(self) -> None:
        document = imported_document()
        retained = {
            "nested": [1, {"future": ["opaque", None, True]}],
            "producerOwned": {"shape": "uninterpreted"},
        }
        document["importedResult"]["report"][0]["retainedMaterial"] = retained
        refresh_imported_digest(document)
        reopened = deserialize(serialize(document))
        self.assertEqual(
            reopened["importedResult"]["report"][0]["retainedMaterial"], retained
        )

    def test_importer_items_reopen_deterministically_with_review_fields(self) -> None:
        document = imported_document()
        expected_items = copy.deepcopy(document["importedResult"]["document"]["items"])
        encoded = serialize(document)
        reopened = deserialize(encoded)
        observed_items = reopened["importedResult"]["document"]["items"]

        self.assertEqual(serialize(reopened), encoded)
        self.assertEqual(
            [item["occurrenceId"] for item in observed_items],
            [item["occurrenceId"] for item in expected_items],
        )
        self.assertEqual(
            [item["sourceOccurrenceIndex"] for item in observed_items],
            list(range(len(observed_items))),
        )
        for expected, observed in zip(expected_items, observed_items, strict=True):
            self.assertEqual(observed["rawId"], expected["rawId"])
            self.assertEqual(observed["usage"], expected["usage"])
        self.assertEqual(observed_items, expected_items)

        future_usage = copy.deepcopy(document)
        opaque_usage_material = {"futureCounts": [1, {"producerOwned": True}]}
        future_usage["importedResult"]["document"]["items"][0]["usage"].update(
            opaque_usage_material
        )
        refresh_imported_digest(future_usage)
        future_reopened = deserialize(serialize(future_usage))
        reopened_usage = future_reopened["importedResult"]["document"]["items"][0][
            "usage"
        ]
        self.assertEqual(
            reopened_usage["futureCounts"], opaque_usage_material["futureCounts"]
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


class SavedStateBoundaryTests(unittest.TestCase):
    def test_limit_derivation_is_stable(self) -> None:
        self.assertEqual(MAX_SAVED_STATE_FILE_BYTES, 597_251_456)

    def test_exact_boundary_is_accepted(self) -> None:
        expected = serialize(empty_document())
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "exact.json"
            path.write_bytes(expected)
            with patch(
                "golden_glory_lab.build_state.codec.MAX_SAVED_STATE_FILE_BYTES",
                len(expected),
            ):
                loaded, raw = load_file(path)
        self.assertEqual(loaded, empty_document())
        self.assertEqual(raw, expected)

    def test_one_byte_over_is_rejected_without_opening(self) -> None:
        expected = serialize(empty_document())
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "one-over.json"
            path.write_bytes(expected + b" ")
            with (
                patch(
                    "golden_glory_lab.build_state.codec.MAX_SAVED_STATE_FILE_BYTES",
                    len(expected),
                ),
                patch.object(
                    Path,
                    "open",
                    side_effect=AssertionError("over-limit state must not be opened"),
                ),
                self.assertRaises(BuildStateError) as raised,
            ):
                load_file(path)
        self.assertEqual(raised.exception.code, "OPEN_FILE_TOO_LARGE")

    def test_growth_after_stat_is_rejected(self) -> None:
        expected = serialize(empty_document())
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "grew.json"
            path.write_bytes(expected)
            with (
                patch(
                    "golden_glory_lab.build_state.codec.MAX_SAVED_STATE_FILE_BYTES",
                    len(expected),
                ),
                patch.object(
                    Path,
                    "stat",
                    return_value=SimpleNamespace(st_size=len(expected)),
                ),
                patch.object(Path, "open", return_value=io.BytesIO(expected + b" ")),
                self.assertRaises(BuildStateError) as raised,
            ):
                load_file(path)
        self.assertEqual(raised.exception.code, "OPEN_FILE_GREW")

    def test_file_access_failure_has_stable_code(self) -> None:
        with (
            self.subTest(stage="stat"),
            patch.object(Path, "stat", side_effect=OSError("denied")),
            self.assertRaises(BuildStateError) as raised,
        ):
            load_file("unreadable.json")
        self.assertEqual(raised.exception.code, "OPEN_FILE_ACCESS")

        with (
            self.subTest(stage="read"),
            patch.object(Path, "stat", return_value=SimpleNamespace(st_size=0)),
            patch.object(Path, "open", side_effect=OSError("denied")),
            self.assertRaises(BuildStateError) as raised,
        ):
            load_file("unreadable.json")
        self.assertEqual(raised.exception.code, "OPEN_FILE_ACCESS")


class TransactionalMalformedOpenTests(unittest.TestCase):
    def _saved_service(self, directory: Path) -> ApplicationService:
        service = ApplicationService()
        self.assertEqual(
            service.attempt_raw_xml(POB_FIXTURES / "comprehensive.xml"), "imported"
        )
        service.set_player_mapping("item-set-0001")
        service.set_mercenary_source("manual-equipment")
        service.add_manual_entry(
            "Ring 1", "Opaque +999% observed value", "Preserve this entry."
        )
        service.set_user_notes("Preserve saved notes")
        service.set_mercenary_source("mapped-item-set", "item-set-0002")
        service.save(directory / "prior-valid.json")
        self.assertFalse(service.dirty)
        return service

    def _snapshot(self, service: ApplicationService) -> dict:
        state = service.state
        return {
            "state": state,
            "bytes": service.canonical_bytes,
            "path": service.current_path,
            "dirty": service.dirty,
            "fileState": service.file_state,
            "readiness": service.readiness(),
            "player": state["playerItemSetOccurrenceId"],
            "mercenaryMode": state["mercenarySourceMode"],
            "mercenary": state["mercenaryItemSetOccurrenceId"],
            "manual": state["manualMercenaryEquipment"],
            "notes": state["userNotes"],
        }

    def _assert_preserved(
        self, service: ApplicationService, before: dict
    ) -> None:
        self.assertEqual(self._snapshot(service), before)
        service.set_user_notes(before["notes"] + " changed")
        self.assertTrue(service.dirty)
        self.assertEqual(service.file_state, "modified")
        service.set_user_notes(before["notes"])
        self.assertFalse(service.dirty)
        self.assertEqual(service.file_state, "saved")

    def _write_mutation(self, path: Path, document: dict) -> None:
        refresh_imported_digest(document)
        path.write_bytes(external_document_bytes(document))

    def test_consumed_neutral_mutations_are_transactional(self) -> None:
        base = imported_document()
        mutations: list[tuple[str, dict]] = []

        missing_report_id = copy.deepcopy(base)
        del missing_report_id["importedResult"]["report"][0]["reportId"]
        mutations.append(("missing-report-id", missing_report_id))

        nonstring_report_id = copy.deepcopy(base)
        nonstring_report_id["importedResult"]["report"][0]["reportId"] = 1
        mutations.append(("nonstring-report-id", nonstring_report_id))

        empty_report_id = copy.deepcopy(base)
        empty_report_id["importedResult"]["report"][0]["reportId"] = ""
        mutations.append(("empty-report-id", empty_report_id))

        duplicate_report_id = copy.deepcopy(base)
        duplicate_report_id["importedResult"]["report"][1]["reportId"] = (
            duplicate_report_id["importedResult"]["report"][0]["reportId"]
        )
        mutations.append(("duplicate-report-id", duplicate_report_id))

        invalid_category = copy.deepcopy(base)
        invalid_category["importedResult"]["report"][0]["category"] = "other"
        mutations.append(("invalid-report-category", invalid_category))

        invalid_stage = copy.deepcopy(base)
        invalid_stage["importedResult"]["report"][0]["stage"] = "other"
        mutations.append(("invalid-report-stage", invalid_stage))

        negative_index = copy.deepcopy(base)
        negative_index["importedResult"]["document"]["itemSets"][0][
            "sourceOccurrenceIndex"
        ] = -1
        mutations.append(("negative-source-index", negative_index))

        negative_assignment_index = copy.deepcopy(base)
        negative_assignment_index["importedResult"]["document"]["itemSets"][0][
            "assignments"
        ][0]["sourceOccurrenceIndex"] = -1
        mutations.append(("negative-assignment-source-index", negative_assignment_index))

        boolean_set_index = copy.deepcopy(base)
        boolean_set_index["importedResult"]["document"]["itemSets"][0][
            "sourceOccurrenceIndex"
        ] = True
        mutations.append(("boolean-item-set-source-index", boolean_set_index))

        boolean_assignment_index = copy.deepcopy(base)
        boolean_assignment_index["importedResult"]["document"]["itemSets"][0][
            "assignments"
        ][0]["sourceOccurrenceIndex"] = True
        mutations.append(("boolean-assignment-source-index", boolean_assignment_index))

        duplicate_assignment = copy.deepcopy(base)
        assignments = duplicate_assignment["importedResult"]["document"]["itemSets"][
            0
        ]["assignments"]
        assignments[1]["occurrenceId"] = assignments[0]["occurrenceId"]
        mutations.append(("duplicate-assignment-id", duplicate_assignment))

        resolved_zero = copy.deepcopy(base)
        resolution = resolved_zero["importedResult"]["document"]["itemSets"][0][
            "assignments"
        ][0]["resolution"]
        resolution["state"] = "resolved"
        resolution["candidateOccurrences"] = []
        mutations.append(("resolved-zero", resolved_zero))

        resolved_many = copy.deepcopy(base)
        resolution = resolved_many["importedResult"]["document"]["itemSets"][0][
            "assignments"
        ][0]["resolution"]
        resolution["state"] = "resolved"
        resolution["candidateOccurrences"] = ["item-0001", "item-0002"]
        mutations.append(("resolved-many", resolved_many))

        ambiguous_one = copy.deepcopy(base)
        resolution = ambiguous_one["importedResult"]["document"]["itemSets"][0][
            "assignments"
        ][0]["resolution"]
        resolution["state"] = "ambiguous"
        resolution["candidateOccurrences"] = ["item-0001"]
        mutations.append(("ambiguous-one", ambiguous_one))

        unresolved_candidate = copy.deepcopy(base)
        resolution = unresolved_candidate["importedResult"]["document"]["itemSets"][
            0
        ]["assignments"][0]["resolution"]
        resolution["state"] = "unresolved"
        resolution["candidateOccurrences"] = ["item-0001"]
        mutations.append(("unresolved-candidate", unresolved_candidate))

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            service = self._saved_service(directory)
            before = self._snapshot(service)
            for name, mutation in mutations:
                with self.subTest(name=name):
                    path = directory / f"{name}.json"
                    self._write_mutation(path, mutation)
                    with self.assertRaises(BuildStateError) as raised:
                        service.open(path)
                    expected_code = (
                        "SHAPE_TYPE"
                        if name == "nonstring-report-id"
                        else "NEUTRAL_RESULT_SHAPE"
                    )
                    self.assertEqual(raised.exception.code, expected_code)
                    self._assert_preserved(service, before)

    def test_consumed_item_mutations_are_transactional(self) -> None:
        mutations = malformed_item_mutations(imported_document())
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            service = self._saved_service(directory)
            before = self._snapshot(service)
            for name, mutation, expected_code in mutations:
                with self.subTest(name=name):
                    path = directory / f"{name}.json"
                    self._write_mutation(path, mutation)
                    with self.assertRaises(BuildStateError) as raised:
                        service.open(path)
                    self.assertEqual(raised.exception.code, expected_code)
                    self._assert_preserved(service, before)

    def test_size_and_growth_failures_are_transactional(self) -> None:
        expected = serialize(empty_document())
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            service = self._saved_service(directory)
            before = self._snapshot(service)
            candidate = directory / "candidate.json"
            candidate.write_bytes(expected + b" ")

            with (
                patch.object(Path, "stat", side_effect=OSError("denied")),
                self.assertRaises(BuildStateError) as raised,
            ):
                service.open(candidate)
            self.assertEqual(raised.exception.code, "OPEN_FILE_ACCESS")
            self._assert_preserved(service, before)

            with (
                patch(
                    "golden_glory_lab.build_state.codec.MAX_SAVED_STATE_FILE_BYTES",
                    len(expected),
                ),
                patch.object(
                    Path,
                    "open",
                    side_effect=AssertionError("over-limit state must not be opened"),
                ),
                self.assertRaises(BuildStateError) as raised,
            ):
                service.open(candidate)
            self.assertEqual(raised.exception.code, "OPEN_FILE_TOO_LARGE")
            self._assert_preserved(service, before)

            with (
                patch(
                    "golden_glory_lab.build_state.codec.MAX_SAVED_STATE_FILE_BYTES",
                    len(expected),
                ),
                patch.object(
                    Path,
                    "stat",
                    return_value=SimpleNamespace(st_size=len(expected)),
                ),
                patch.object(Path, "open", return_value=io.BytesIO(expected + b" ")),
                self.assertRaises(BuildStateError) as raised,
            ):
                service.open(candidate)
            self.assertEqual(raised.exception.code, "OPEN_FILE_GREW")
            self._assert_preserved(service, before)

    def test_json_resource_failures_are_transactional(self) -> None:
        cases = (
            (
                "deep.json",
                ("[" * 10_000 + "]" * 10_000).encode("ascii"),
                "OPEN_JSON_NESTING",
            ),
            (
                "large-integer.json",
                ('{"value": ' + "1" * 5_000 + "}").encode("ascii"),
                "OPEN_JSON_NUMERIC_LIMIT",
            ),
        )
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            service = self._saved_service(directory)
            before = self._snapshot(service)
            for name, data, code in cases:
                with self.subTest(name=name):
                    path = directory / name
                    path.write_bytes(data)
                    with self.assertRaises(BuildStateError) as raised:
                        service.open(path)
                    self.assertEqual(raised.exception.code, code)
                    self._assert_preserved(service, before)

    def test_deterministic_serialization_recursion_is_transactional(self) -> None:
        candidate = imported_document()
        candidate["importedResult"]["futureOpaqueImporterMaterial"] = {
            "nested": ["retained"]
        }
        refresh_imported_digest(candidate)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path = directory / "nested-imported-material.json"
            path.write_bytes(external_document_bytes(candidate))
            service = self._saved_service(directory)
            before = self._snapshot(service)
            with (
                patch(
                    "golden_glory_lab.build_state.codec.deterministic_json_bytes",
                    side_effect=RecursionError("simulated nested importer material"),
                ),
                self.assertRaises(BuildStateError) as raised,
            ):
                service.open(path)
            self.assertEqual(raised.exception.code, "IMPORTED_RESULT_NESTING")
            self._assert_preserved(service, before)

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

    def test_schema_shared_rules_and_runtime_only_consumer_invariants(self) -> None:
        shared: list[tuple[str, dict]] = []

        missing_report_id = imported_document()
        del missing_report_id["importedResult"]["report"][0]["reportId"]
        shared.append(("missing-report-id", missing_report_id))

        invalid_category = imported_document()
        invalid_category["importedResult"]["report"][0]["category"] = "other"
        shared.append(("invalid-category", invalid_category))

        invalid_stage = imported_document()
        invalid_stage["importedResult"]["report"][0]["stage"] = "other"
        shared.append(("invalid-stage", invalid_stage))

        negative_index = imported_document()
        negative_index["importedResult"]["document"]["itemSets"][0][
            "sourceOccurrenceIndex"
        ] = -1
        shared.append(("negative-index", negative_index))

        negative_assignment_index = imported_document()
        negative_assignment_index["importedResult"]["document"]["itemSets"][0][
            "assignments"
        ][0]["sourceOccurrenceIndex"] = -1
        shared.append(("negative-assignment-index", negative_assignment_index))

        for state, candidates, name in (
            ("resolved", [], "resolved-zero"),
            ("resolved", ["item-0001", "item-0002"], "resolved-many"),
            ("ambiguous", ["item-0001"], "ambiguous-one"),
            ("unresolved", ["item-0001"], "unresolved-with-candidate"),
            ("missing", [], "equipment-resolution-missing"),
        ):
            mutation = imported_document()
            resolution = mutation["importedResult"]["document"]["itemSets"][0][
                "assignments"
            ][0]["resolution"]
            resolution["state"] = state
            resolution["candidateOccurrences"] = candidates
            shared.append((name, mutation))

        for name, mutation in shared:
            with self.subTest(shared=name):
                refresh_imported_digest(mutation)
                with self.assertRaises(BuildStateError):
                    validate_document(mutation)
                with self.assertRaises(ValidationError):
                    self.validator.validate(mutation)

        runtime_only: list[tuple[str, dict]] = []
        empty_report_id = imported_document()
        empty_report_id["importedResult"]["report"][0]["reportId"] = ""
        runtime_only.append(("empty-report-id", empty_report_id))

        empty_item_id = imported_document()
        empty_item_id["importedResult"]["document"]["items"][0]["occurrenceId"] = ""
        runtime_only.append(("empty-item-id", empty_item_id))

        empty_item_set_id = imported_document()
        empty_item_set_id["importedResult"]["document"]["itemSets"][0][
            "occurrenceId"
        ] = ""
        runtime_only.append(("empty-item-set-id", empty_item_set_id))

        duplicate_report_id = imported_document()
        duplicate_report_id["importedResult"]["report"][1]["reportId"] = (
            duplicate_report_id["importedResult"]["report"][0]["reportId"]
        )
        runtime_only.append(("duplicate-report-id", duplicate_report_id))

        duplicate_assignment = imported_document()
        assignments = duplicate_assignment["importedResult"]["document"]["itemSets"][
            0
        ]["assignments"]
        assignments[1]["occurrenceId"] = assignments[0]["occurrenceId"]
        runtime_only.append(("duplicate-assignment-id", duplicate_assignment))

        for name, mutation in runtime_only:
            with self.subTest(runtime_only=name):
                refresh_imported_digest(mutation)
                self.validator.validate(mutation)
                with self.assertRaises(BuildStateError) as raised:
                    validate_document(mutation)
                self.assertEqual(raised.exception.code, "NEUTRAL_RESULT_SHAPE")

        scoped_duplicate = imported_document()
        item_sets = scoped_duplicate["importedResult"]["document"]["itemSets"]
        item_sets[1]["assignments"][0]["occurrenceId"] = item_sets[0][
            "assignments"
        ][0]["occurrenceId"]
        refresh_imported_digest(scoped_duplicate)
        self.validator.validate(scoped_duplicate)
        validate_document(scoped_duplicate)

    def test_item_consumer_mutations_are_shared_schema_runtime_rules(self) -> None:
        for name, mutation, expected_code in malformed_item_mutations(
            imported_document()
        ):
            with self.subTest(name=name):
                refresh_imported_digest(mutation)
                with self.assertRaises(BuildStateError) as raised:
                    validate_document(mutation)
                self.assertEqual(raised.exception.code, expected_code)
                with self.assertRaises(ValidationError):
                    self.validator.validate(mutation)

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
