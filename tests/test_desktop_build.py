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
    serialize,
)
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


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


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
            self.assertEqual(status["status"], MECHANICS_STATUS)
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
