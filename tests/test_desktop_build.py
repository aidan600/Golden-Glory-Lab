from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golden_glory_lab.build_state import (  # noqa: E402
    BuildStateError,
    imported_result_digest,
    serialize,
)
from golden_glory_lab.build_state.codec import (  # noqa: E402
    MAX_USER_NOTES_CHARACTERS,
)
from golden_glory_lab.desktop.app import GoldenGloryApp  # noqa: E402
from golden_glory_lab.desktop.dialogs import ManualEntryDialog  # noqa: E402
from golden_glory_lab.desktop.evidence import (  # noqa: E402
    MECHANICS_STATUS,
    mechanics_availability,
)
from golden_glory_lab.desktop.intake import (  # noqa: E402
    DesktopIntakeError,
    import_raw_xml_file,
    import_share_code_text,
)
from golden_glory_lab.desktop.service import ApplicationService  # noqa: E402
from golden_glory_lab.pob_import import (  # noqa: E402
    DEFAULT_IMPORT_LIMITS,
    importPobRawXml,
    importPobShareCode,
)

FIXTURES = ROOT / "fixtures" / "pob" / "proof"


class FakeValue:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


class FakeCombo(FakeValue):
    def __init__(self, value: str = "") -> None:
        super().__init__(value)
        self.configuration: dict = {}

    def configure(self, **values: object) -> None:
        self.configuration.update(values)


class FakeText:
    def __init__(self, value: str = "") -> None:
        self.value = value
        self.modified = False

    def get(self, _start: str, _end: str) -> str:
        return self.value

    def delete(self, _start: str, _end: str) -> None:
        self.value = ""

    def insert(self, _index: str, value: str) -> None:
        self.value += value

    def edit_modified(self, value: bool | None = None) -> bool:
        if value is None:
            return self.modified
        self.modified = value
        return self.modified


class FakeTree:
    def __init__(self, selected: str | None = None) -> None:
        self.selected = selected
        self.rows: dict[str, tuple[object, ...]] = {}

    def selection(self) -> tuple[str, ...]:
        return () if self.selected is None else (self.selected,)

    def selection_set(self, selected: str) -> None:
        self.selected = selected

    def get_children(self) -> tuple[str, ...]:
        return tuple(self.rows)

    def delete(self, *identifiers: str) -> None:
        for identifier in identifiers:
            self.rows.pop(identifier, None)

    def insert(
        self,
        _parent: str,
        _index: str,
        *,
        iid: str,
        values: tuple[object, ...],
    ) -> str:
        self.rows[iid] = tuple(values)
        return iid


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


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


class DesktopImportBoundaryTests(unittest.TestCase):
    def test_pre_read_xml_size_rejection_does_not_open_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "oversized.xml"
            with path.open("wb") as handle:
                handle.truncate(DEFAULT_IMPORT_LIMITS.maxRawXmlBytes + 1)
            with patch.object(
                Path,
                "open",
                side_effect=AssertionError("over-limit file must not be opened"),
            ):
                with self.assertRaises(DesktopIntakeError) as raised:
                    import_raw_xml_file(path)
        self.assertEqual(raised.exception.code, "RAW_XML_FILE_SIZE")

    def test_strict_utf8_failure_is_desktop_intake_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "invalid.xml"
            path.write_bytes(b"\xff")
            with self.assertRaises(DesktopIntakeError) as raised:
                import_raw_xml_file(path)
        self.assertEqual(raised.exception.code, "RAW_XML_FILE_UTF8")
        self.assertEqual(raised.exception.stage, "desktop-intake")

    def test_share_length_rejection_precedes_importer_invocation(self) -> None:
        importer = Mock(side_effect=AssertionError("importer must not run"))
        value = "A" * (DEFAULT_IMPORT_LIMITS.maxShareCodeCharacters + 1)
        with self.assertRaises(DesktopIntakeError) as raised:
            import_share_code_text(value, importer=importer)
        self.assertEqual(raised.exception.code, "SHARE_CODE_LENGTH")
        importer.assert_not_called()

    def test_raw_xml_and_share_code_use_public_importer_successfully(self) -> None:
        raw = import_raw_xml_file(FIXTURES / "comprehensive.xml")
        share = import_share_code_text(fixture_text("equivalent.share.txt"))
        direct_raw = importPobRawXml(fixture_text("comprehensive.xml"))
        direct_share = importPobShareCode(fixture_text("equivalent.share.txt"))
        self.assertEqual(raw, direct_raw)
        self.assertEqual(share, direct_share)
        self.assertEqual(
            [entry["occurrenceId"] for entry in raw["document"]["itemSets"]],
            ["item-set-0001", "item-set-0002", "item-set-0003"],
        )


class ApplicationServiceTests(unittest.TestCase):
    def imported_service(self) -> ApplicationService:
        service = ApplicationService()
        self.assertEqual(
            service.attempt_raw_xml(FIXTURES / "comprehensive.xml"), "imported"
        )
        return service

    def configured_service(self) -> ApplicationService:
        service = self.imported_service()
        service.set_player_mapping("item-set-0001")
        service.set_mercenary_source("manual-equipment")
        service.add_manual_entry(
            "Ring 1",
            "Exact opaque +999% to Fire Resistance",
            "Preserve out-of-range observed material.",
        )
        service.set_user_notes("Keep across reimport")
        service.set_mercenary_source("mapped-item-set", "item-set-0002")
        return service

    def test_failed_import_preserves_canonical_state_and_readiness(self) -> None:
        service = self.configured_service()
        before = service.state
        before_bytes = service.canonical_bytes
        readiness = service.readiness()
        outcome = service.attempt_share_code(
            "bad",
            importer=lambda _value: importPobShareCode("not!base64"),
        )
        self.assertEqual(outcome, "failed")
        self.assertEqual(service.state, before)
        self.assertEqual(service.canonical_bytes, before_bytes)
        self.assertEqual(service.readiness(), readiness)
        self.assertEqual(
            service.last_failed_import["code"], "INVALID_BASE64_ALPHABET"
        )
        self.assertNotIn(b"last_failed", service.canonical_bytes)
        self.assertNotIn(b"INVALID_BASE64_ALPHABET", service.canonical_bytes)

    def test_successful_replacement_requires_confirmation_and_preserves_manual(self) -> None:
        service = self.configured_service()
        before = service.state
        outcome = service.attempt_share_code(fixture_text("equivalent.share.txt"))
        self.assertEqual(outcome, "confirmation-required")
        self.assertEqual(service.state, before)
        self.assertIsNotNone(service.pending_import_result)
        self.assertEqual(service.confirm_pending_import(False), "canceled")
        self.assertEqual(service.state, before)

        self.assertEqual(
            service.attempt_share_code(fixture_text("equivalent.share.txt")),
            "confirmation-required",
        )
        self.assertEqual(service.confirm_pending_import(True), "replaced")
        state = service.state
        self.assertEqual(len(service.item_sets()), 1)
        self.assertIsNone(state["playerItemSetOccurrenceId"])
        self.assertIsNone(state["mercenaryItemSetOccurrenceId"])
        self.assertEqual(state["mercenarySourceMode"], "not-yet-selected")
        self.assertEqual(state["userNotes"], "Keep across reimport")
        self.assertEqual(len(state["manualMercenaryEquipment"]), 1)
        self.assertEqual(
            state["manualMercenaryEquipment"][0]["rawText"],
            "Exact opaque +999% to Fire Resistance",
        )

    def test_all_item_sets_remain_distinct_visible_and_unmapped(self) -> None:
        service = self.imported_service()
        sets = service.item_sets()
        self.assertEqual(
            [entry["occurrenceId"] for entry in sets],
            ["item-set-0001", "item-set-0002", "item-set-0003"],
        )
        self.assertEqual(
            [entry["title"]["value"] for entry in sets],
            ["Player candidate", "Mercenary candidate", "Animate Guardian"],
        )
        state = service.state
        self.assertIsNone(state["playerItemSetOccurrenceId"])
        self.assertIsNone(state["mercenaryItemSetOccurrenceId"])
        observed = next(
            item for item in service.imported_items() if item["parsedId"] == 7
        )
        self.assertIn("+999% to Fire Resistance", observed["xmlCharacterValue"])
        self.assertTrue(service.importer_report())

    def test_mapping_uses_occurrences_and_same_occurrence_fails(self) -> None:
        service = self.imported_service()
        service.set_player_mapping("item-set-0001")
        service.set_mercenary_source("mapped-item-set", "item-set-0002")
        self.assertEqual(
            service.state["mercenaryItemSetOccurrenceId"], "item-set-0002"
        )
        with self.assertRaises(BuildStateError) as raised:
            service.set_mercenary_source("mapped-item-set", "item-set-0001")
        self.assertEqual(raised.exception.code, "SAME_OCCURRENCE_MAPPING")
        self.assertEqual(
            service.state["mercenaryItemSetOccurrenceId"], "item-set-0002"
        )

    def test_manual_and_mapped_modes_are_distinct_and_delete_is_explicit(self) -> None:
        service = self.imported_service()
        service.set_mercenary_source("manual-equipment")
        identifier = service.add_manual_entry("Gloves", "Opaque manual text")
        service.set_mercenary_source("mapped-item-set", "item-set-0002")
        self.assertEqual(len(service.state["manualMercenaryEquipment"]), 1)
        self.assertIsNotNone(service.state["mercenaryItemSetOccurrenceId"])
        service.set_mercenary_source("manual-equipment")
        self.assertIsNone(service.state["mercenaryItemSetOccurrenceId"])
        self.assertFalse(service.delete_manual_entry(identifier, confirmed=False))
        self.assertEqual(len(service.state["manualMercenaryEquipment"]), 1)
        self.assertTrue(service.delete_manual_entry(identifier, confirmed=True))
        self.assertEqual(service.state["manualMercenaryEquipment"], [])

    def test_dirty_file_state_and_readiness_are_derived_from_content(self) -> None:
        service = ApplicationService()
        self.assertFalse(service.dirty)
        self.assertEqual(service.file_state, "unsaved")
        self.assertEqual(service.readiness()["import"], "missing")
        service.set_user_notes("changed")
        self.assertTrue(service.dirty)
        service.set_user_notes("")
        self.assertFalse(service.dirty)

        service = self.imported_service()
        self.assertFalse(service.readiness()["intakeReady"])
        service.set_player_mapping("item-set-0001")
        self.assertFalse(service.readiness()["intakeReady"])
        service.set_mercenary_source("manual-equipment")
        self.assertTrue(service.readiness()["intakeReady"])
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.json"
            service.save(path)
            self.assertFalse(service.dirty)
            self.assertEqual(service.file_state, "saved")
            service.set_user_notes("modified")
            self.assertEqual(service.file_state, "modified")
            service.set_user_notes("")
            self.assertEqual(service.file_state, "saved")

    def test_raw_review_material_and_warning_report_stay_intact(self) -> None:
        service = self.imported_service()
        before_items = service.imported_items()
        before_report = service.importer_report()
        service.set_player_mapping("item-set-0001")
        service.set_mercenary_source("manual-equipment")
        self.assertEqual(service.imported_items(), before_items)
        self.assertEqual(service.importer_report(), before_report)
        first = service.item_sets()[0]["assignments"][0]
        self.assertEqual(first["originalSlotName"]["value"], "Weapon 1")
        self.assertEqual(first["resolution"]["state"], "resolved")
        self.assertEqual(
            first["resolution"]["candidateOccurrences"], ["item-0001"]
        )


class RejectedEditPresentationTests(unittest.TestCase):
    def _saved_service(self, directory: Path) -> ApplicationService:
        service = ApplicationService()
        self.assertEqual(
            service.attempt_raw_xml(FIXTURES / "comprehensive.xml"), "imported"
        )
        service.set_player_mapping("item-set-0001")
        service.set_mercenary_source("mapped-item-set", "item-set-0002")
        service.save(directory / "presentation.json")
        return service

    def _headless_app(self, service: ApplicationService) -> GoldenGloryApp:
        app = GoldenGloryApp.__new__(GoldenGloryApp)
        app.service = service
        app._refreshing = False
        state = service.state
        app.player_combo = FakeCombo(state["playerItemSetOccurrenceId"] or "")
        app.mercenary_combo = FakeCombo(
            state["mercenaryItemSetOccurrenceId"] or ""
        )
        app.mercenary_mode_var = FakeValue(state["mercenarySourceMode"])
        app.notes_text = FakeText(state["userNotes"])
        app.status_var = FakeValue()
        app.failed_var = FakeValue()
        app.title = Mock()
        app._restore_rejected_edit()
        return app

    def test_same_occurrence_rejection_restores_both_mapping_directions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = self._saved_service(Path(temporary))
            app = self._headless_app(service)
            canonical = service.state
            with patch(
                "golden_glory_lab.desktop.app.messagebox.showerror"
            ) as showerror:
                app.player_combo.set("item-set-0002")
                app._set_player_mapping(None)
                self.assertEqual(
                    app.player_combo.get(), canonical["playerItemSetOccurrenceId"]
                )
                self.assertEqual(
                    app.mercenary_combo.get(),
                    canonical["mercenaryItemSetOccurrenceId"],
                )
                self.assertEqual(
                    app.mercenary_mode_var.get(), canonical["mercenarySourceMode"]
                )

                app.mercenary_combo.set("item-set-0001")
                app._set_mercenary_mapping(None)
                self.assertEqual(
                    app.player_combo.get(), canonical["playerItemSetOccurrenceId"]
                )
                self.assertEqual(
                    app.mercenary_combo.get(),
                    canonical["mercenaryItemSetOccurrenceId"],
                )
                self.assertEqual(
                    app.mercenary_mode_var.get(), canonical["mercenarySourceMode"]
                )

            self.assertEqual(showerror.call_count, 2)
            self.assertEqual(service.state, canonical)
            self.assertFalse(service.dirty)
            self.assertEqual(service.file_state, "saved")
            self.assertTrue(service.readiness()["intakeReady"])
            self.assertIn("File: saved", app.status_var.get())
            self.assertIn("Intake ready: yes", app.status_var.get())
            self.assertFalse(app.title.call_args.args[0].endswith(" *"))

    def test_notes_exact_limit_and_rejected_character_restore_visible_state(self) -> None:
        maximum = "n" * MAX_USER_NOTES_CHARACTERS
        with tempfile.TemporaryDirectory() as temporary:
            service = self._saved_service(Path(temporary))
            app = self._headless_app(service)

            app.notes_text.value = maximum
            app.notes_text.modified = True
            with patch(
                "golden_glory_lab.desktop.app.messagebox.showerror"
            ) as showerror:
                app._notes_modified(None)
            showerror.assert_not_called()
            self.assertEqual(service.state["userNotes"], maximum)
            self.assertEqual(app.notes_text.value, maximum)
            self.assertFalse(app.notes_text.modified)
            self.assertTrue(service.dirty)
            self.assertIn("File: modified", app.status_var.get())
            self.assertTrue(app.title.call_args.args[0].endswith(" *"))

            service.save()
            app._restore_rejected_edit()
            app.notes_text.value = maximum + "x"
            app.notes_text.modified = True
            with patch(
                "golden_glory_lab.desktop.app.messagebox.showerror"
            ) as showerror:
                app._notes_modified(None)
            self.assertEqual(showerror.call_args.args[0], "USER_NOTES_LIMIT")
            self.assertEqual(service.state["userNotes"], maximum)
            self.assertEqual(app.notes_text.value, maximum)
            self.assertFalse(app.notes_text.modified)
            self.assertFalse(service.dirty)
            self.assertEqual(service.file_state, "saved")
            self.assertIn("File: saved", app.status_var.get())
            self.assertFalse(app.title.call_args.args[0].endswith(" *"))

            with patch(
                "golden_glory_lab.desktop.app.messagebox.askyesno"
            ) as askyesno:
                self.assertTrue(app._maybe_discard("continue"))
                askyesno.assert_not_called()

            service.set_user_notes(maximum[:-1])
            with patch(
                "golden_glory_lab.desktop.app.messagebox.askyesno",
                return_value=False,
            ) as askyesno:
                self.assertFalse(app._maybe_discard("continue"))
                askyesno.assert_called_once()

    def test_assignment_lookup_is_scoped_to_selected_item_set(self) -> None:
        service = ApplicationService()
        self.assertEqual(
            service.attempt_raw_xml(FIXTURES / "comprehensive.xml"), "imported"
        )
        document = service.state
        item_sets = document["importedResult"]["document"]["itemSets"]
        shared_id = item_sets[0]["assignments"][0]["occurrenceId"]
        item_sets[1]["assignments"][0]["occurrenceId"] = shared_id
        document["importedResultSha256"] = imported_result_digest(
            document["importedResult"]
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "scoped-assignment.json"
            path.write_bytes(serialize(document))
            scoped_service = ApplicationService()
            scoped_service.open(path)
            app = GoldenGloryApp.__new__(GoldenGloryApp)
            app.service = scoped_service
            app.set_tree = FakeTree(item_sets[1]["occurrenceId"])
            observed = app._assignment_by_id(shared_id)
        self.assertIsNotNone(observed)
        self.assertEqual(
            observed["sourcePath"], item_sets[1]["assignments"][0]["sourcePath"]
        )


class ImportedItemPresentationBoundaryTests(unittest.TestCase):
    def test_rejected_malformed_item_never_reaches_review_presentation(self) -> None:
        marker = "malformed-item-candidate-marker"
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            valid_path = directory / "valid-presentation.json"
            source_service = ApplicationService()
            self.assertEqual(
                source_service.attempt_raw_xml(FIXTURES / "comprehensive.xml"),
                "imported",
            )
            source_service.set_player_mapping("item-set-0001")
            source_service.set_mercenary_source("manual-equipment")
            source_service.add_manual_entry(
                "Ring 1", "Opaque observed item", "Preserve presentation baseline."
            )
            source_service.set_user_notes("Preserve item review")
            source_service.set_mercenary_source("mapped-item-set", "item-set-0002")
            source_service.save(valid_path)

            service = ApplicationService()
            service.open(valid_path)
            expected_items = service.imported_items()
            self.assertGreater(len(expected_items), 0)

            malformed = service.state
            malformed_item = malformed["importedResult"]["document"]["items"][0]
            malformed_item["rawId"] = "bad"
            malformed_item["sourcePath"] = marker
            malformed["importedResultSha256"] = imported_result_digest(
                malformed["importedResult"]
            )
            malformed_path = directory / "malformed-presentation.json"
            malformed_path.write_bytes(external_document_bytes(malformed))

            with self.assertRaises(BuildStateError) as raised:
                service.open(malformed_path)
            self.assertEqual(raised.exception.code, "SHAPE_TYPE")
            self.assertEqual(service.imported_items(), expected_items)

            app = GoldenGloryApp.__new__(GoldenGloryApp)
            app.service = service
            app.item_tree = FakeTree()
            app.report_tree = FakeTree()
            app.failed_detail = object()
            app.item_detail = object()
            app._set_readonly_text = Mock()
            app._refresh_import_review()

            expected_ids = [item["occurrenceId"] for item in expected_items]
            self.assertEqual(list(app.item_tree.rows), expected_ids)
            for item in expected_items:
                row = app.item_tree.rows[item["occurrenceId"]]
                self.assertEqual(row[2], item["usage"]["state"])
            self.assertNotIn(marker, repr(app.item_tree.rows))

            app.item_tree.selection_set(expected_ids[0])
            app._set_readonly_text.reset_mock()
            app._show_item_detail(None)
            app._set_readonly_text.assert_called_once()
            rendered_detail = json.loads(app._set_readonly_text.call_args.args[1])
            self.assertEqual(rendered_detail, expected_items[0])
            self.assertNotIn(marker, app._set_readonly_text.call_args.args[1])


class EvidenceStatusTests(unittest.TestCase):
    def test_blocked_mechanics_are_referenced_nonnumeric_and_not_persisted(self) -> None:
        statuses = mechanics_availability()
        self.assertEqual(len(statuses), 7)
        required = {
            "AUD-002-C03",
            "AUD-003-C12",
            "AUD-004-C09",
            "AUD-004-C10",
            "AUD-005-C07",
        }
        observed = {
            claim for status in statuses for claim in status["claimReferences"]
        }
        self.assertTrue(required.issubset(observed))
        for status in statuses:
            self.assertEqual(status["status"], "unavailable-pending-evidence")
            self.assertIsNone(status["value"])
            self.assertNotEqual(status["value"], 0)
        persisted = json.loads(serialize(ApplicationService().state))
        self.assertNotIn("mechanics", persisted)
        serialized = json.dumps(persisted).lower()
        for prohibited in (
            "combinedscore",
            "flamelinkdamage",
            "firepenetration",
            "damagepersecond",
        ):
            self.assertNotIn(prohibited, serialized)

    def test_warning_state_is_independent_from_mechanics_availability(self) -> None:
        service = ApplicationService()
        self.assertEqual(service.importer_warning_state(), "none")
        service.attempt_raw_xml(FIXTURES / "comprehensive.xml")
        self.assertEqual(service.importer_warning_state(), "review-required")
        self.assertEqual(service.status_summary()["mechanics"], MECHANICS_STATUS)


class ManualEntryDialogTests(unittest.TestCase):
    def test_return_in_text_widget_inserts_newline_and_stops_dialog_ok(self) -> None:
        widget = Mock()
        event = Mock(widget=widget)

        result = ManualEntryDialog._insert_text_newline(event)

        widget.insert.assert_called_once_with("insert", "\n")
        self.assertEqual(result, "break")

if __name__ == "__main__":
    unittest.main()
