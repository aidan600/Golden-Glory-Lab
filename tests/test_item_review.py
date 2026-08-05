from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golden_glory_lab.build_state import (  # noqa: E402
    BuildStateError,
    empty_document,
    imported_result_digest,
    serialize,
    validate_document,
)
from golden_glory_lab.desktop.service import ApplicationService  # noqa: E402
from golden_glory_lab.evidence_gate import load_enmity_reference  # noqa: E402
from golden_glory_lab.item_review import (  # noqa: E402
    COPIED_ITEM_LIMITS,
    STATE_AGGREGATION_TABLE,
    CopiedItemRecognitionError,
    derive_item_reviews,
    recognize_copied_item,
)
from golden_glory_lab.pob_import import importPobRawXml  # noqa: E402
from golden_glory_lab.pob_import.limits import DEFAULT_IMPORT_LIMITS  # noqa: E402

FIXTURE = ROOT / "fixtures" / "item_review" / "copied-items-v1.json"
POB_FIXTURE = ROOT / "fixtures" / "pob" / "proof" / "comprehensive.xml"


def fixture_cases() -> dict[str, dict]:
    value = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return {case["id"]: case for case in value["cases"]}


def imported_document() -> dict:
    result = importPobRawXml(POB_FIXTURE.read_text(encoding="utf-8"))
    assert result["status"] == "success"
    document = empty_document()
    document["importedResult"] = result
    document["importedResultSha256"] = imported_result_digest(result)
    return document


class CopiedItemRecognitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = fixture_cases()
        cls.reference = load_enmity_reference()

    def test_state_aggregation_table_is_explicit_and_ordered(self) -> None:
        self.assertEqual(
            [row["state"] for row in STATE_AGGREGATION_TABLE],
            [
                "malformed",
                "manually-required",
                "partially-recognized",
                "unrecognized",
                "recognized",
            ],
        )

    def test_all_static_fixtures_have_expected_states_and_deterministic_reports(self) -> None:
        for case in self.cases.values():
            if case.get("kind") == "generated-boundary":
                continue
            with self.subTest(case=case["id"]):
                raw = case["rawText"]
                first = recognize_copied_item(raw, enmity_reference=self.reference)
                second = recognize_copied_item(raw, enmity_reference=self.reference)
                self.assertEqual(first.state, case["expectedState"])
                self.assertEqual(first, second)
                self.assertEqual(first.rawText, raw)
                self.assertEqual(
                    first.rawTextSha256,
                    hashlib.sha256(raw.encode("utf-8", errors="strict")).hexdigest(),
                )
                self.assertEqual(first.to_dict(), second.to_dict())

    def test_lf_crlf_blank_and_unicode_source_locations_address_raw_text(self) -> None:
        for case_id in (
            "recognizable-enmity-crlf",
            "generic-recognized-lf",
            "leading-trailing-blank-material",
        ):
            raw = self.cases[case_id]["rawText"]
            result = recognize_copied_item(raw, enmity_reference=self.reference)
            for report in result.reports:
                if report.lineNumber is None:
                    continue
                start = report.characterStart
                end = report.characterEnd
                assert start is not None and end is not None
                self.assertEqual(raw[start:end], report.rawLine)
                self.assertEqual(raw[end : end + len(report.lineEnding or "")], report.lineEnding)
            if "crlf" in case_id:
                self.assertIn(
                    "\r\n",
                    next(iter(result.normalizations))["observedLineEndings"],
                )
                self.assertEqual(result.rawText.count("\r\n"), raw.count("\r\n"))

    def test_enmity_match_is_identity_only_and_does_not_apply_modifier_semantics(self) -> None:
        case = self.cases["recognizable-enmity-crlf"]
        result = recognize_copied_item(
            case["rawText"], enmity_reference=self.reference
        )
        self.assertEqual(result.referenceMatch["stableReferenceId"], case["expectedReferenceId"])
        self.assertFalse(result.referenceMatch["establishesOwnership"])
        self.assertFalse(result.referenceMatch["establishesEquippedState"])
        self.assertFalse(result.referenceMatch["establishesAvailability"])
        unknown = [
            report
            for report in result.reports
            if report.code == "UNRECOGNIZED_ORDERED_ITEM_MATERIAL"
        ]
        self.assertEqual(
            [report.rawLine for report in unknown],
            [
                "Damage Penetrates Fire Resistance equal to your Overcapped Fire Resistance, up to a maximum of 200%"
            ],
        )
        self.assertNotIn("calculatedValue", result.to_dict())

    def test_partial_unknown_lines_remain_visible_and_ordered(self) -> None:
        raw = self.cases["partial-unknown-line"]["rawText"]
        result = recognize_copied_item(raw, enmity_reference=self.reference)
        reports = [
            report
            for report in result.reports
            if report.code == "UNRECOGNIZED_ORDERED_ITEM_MATERIAL"
        ]
        self.assertEqual([report.rawLine for report in reports], ["Unsupported synthetic modifier"])
        self.assertEqual(result.state, "partially-recognized")

    def test_unsupported_structure_reports_every_material_line(self) -> None:
        raw = self.cases["unsupported-localized-structure"]["rawText"]
        result = recognize_copied_item(raw, enmity_reference=self.reference)
        material = [report.rawLine for report in result.reports if report.rawLine]
        self.assertEqual(material, raw.splitlines())
        self.assertEqual(result.state, "unrecognized")

    def test_out_of_range_value_is_informational_and_never_clamped(self) -> None:
        raw = self.cases["out-of-reviewed-range"]["rawText"]
        result = recognize_copied_item(raw, enmity_reference=self.reference)
        report = next(
            value
            for value in result.reports
            if value.code == "OBSERVED_VALUE_OUTSIDE_REVIEWED_NATURAL_RANGE"
        )
        self.assertEqual(report.rawLine, "123% reduced Fire Resistance")
        self.assertEqual(report.retainedMaterial["observed"], 123)
        self.assertFalse(report.retainedMaterial["clamped"])
        self.assertIn("123%", result.rawText)

    def test_entry_text_limits_utf8_and_empty_reject_before_parsing(self) -> None:
        maximum = self.cases["maximum-accepted-generated"]
        accepted = maximum["baseText"] + "x" * (
            maximum["targetCharacters"] - len(maximum["baseText"])
        )
        self.assertEqual(len(accepted), COPIED_ITEM_LIMITS["maxRawTextCharacters"])
        self.assertEqual(recognize_copied_item(accepted).rawText, accepted)

        over = self.cases["over-limit-generated"]
        rejected = over["baseText"] + "x" * (
            over["targetCharacters"] - len(over["baseText"])
        )
        with self.assertRaises(CopiedItemRecognitionError) as raised:
            recognize_copied_item(rejected)
        self.assertEqual(raised.exception.code, "COPIED_TEXT_LIMIT")
        with self.assertRaises(CopiedItemRecognitionError) as raised:
            recognize_copied_item("\ud800")
        self.assertEqual(raised.exception.code, "COPIED_TEXT_UTF8")
        with self.assertRaises(CopiedItemRecognitionError) as raised:
            recognize_copied_item("")
        self.assertEqual(raised.exception.code, "COPIED_TEXT_EMPTY")


class CommonItemReviewTests(unittest.TestCase):
    def test_pob_copied_and_manual_sources_share_one_derived_model(self) -> None:
        document = imported_document()
        document["playerItemSetOccurrenceId"] = "item-set-0001"
        document["mercenarySourceMode"] = "manual-equipment"
        document["manualMercenaryEquipment"] = [
            {
                "entryId": "manual-0001",
                "slotLabel": "Ring 1",
                "rawText": "Opaque manual ring text",
                "reviewState": "unparsed-manual",
                "note": "Manual note",
            }
        ]
        document["copiedItemEntries"] = [
            {
                "entryId": "copied-0001",
                "rawText": fixture_cases()["recognizable-enmity-crlf"]["rawText"],
                "role": "unassigned",
                "slotLabel": "Ring 2",
                "userLabel": "Observed",
                "note": "Copied note",
            }
        ]
        reviews = derive_item_reviews(document, enmity_reference=load_enmity_reference())
        by_kind = {kind: [r for r in reviews if r.provenanceKind == kind] for kind in (
            "pob-import",
            "copied-text",
            "manual-entry",
        )}
        self.assertTrue(by_kind["pob-import"])
        self.assertEqual(len(by_kind["copied-text"]), 1)
        self.assertEqual(len(by_kind["manual-entry"]), 1)
        self.assertEqual(by_kind["manual-entry"][0].recognitionState, "manually-required")
        self.assertEqual(by_kind["copied-text"][0].userNote, "Copied note")
        self.assertEqual(by_kind["pob-import"][0].userNote, "")

    def test_role_bindings_are_only_explicit_and_one_pob_item_keeps_many_bindings(self) -> None:
        document = imported_document()
        document["playerItemSetOccurrenceId"] = "item-set-0001"
        document["mercenarySourceMode"] = "mapped-item-set"
        document["mercenaryItemSetOccurrenceId"] = "item-set-0002"
        reviews = derive_item_reviews(document)
        first = next(r for r in reviews if r.sourceLocator.sourceId == "item-0001")
        self.assertEqual(len(first.bindings), 3)
        self.assertEqual(
            {binding.basis for binding in first.bindings},
            {
                "explicit-player-item-set-mapping",
                "explicit-mercenary-item-set-mapping",
            },
        )
        unmapped = next(r for r in reviews if r.sourceLocator.sourceId == "item-0005")
        self.assertEqual([binding.role for binding in unmapped.bindings], ["unassigned"])
        self.assertEqual([binding.basis for binding in unmapped.bindings], ["unmapped"])

    def test_copied_role_is_user_metadata_and_enmity_never_sets_owner_or_equipped(self) -> None:
        service = ApplicationService()
        raw = fixture_cases()["recognizable-enmity-crlf"]["rawText"]
        identifier = service.add_copied_entry(raw, role="unassigned")
        review = service.item_reviews()[0]
        self.assertEqual(review.sourceLocator.sourceId, identifier)
        self.assertEqual(review.bindings[0].role, "unassigned")
        self.assertIsNotNone(review.referenceMatch)
        self.assertEqual(service.state["enmityManualInput"]["equippedState"], "unknown")
        service.edit_copied_entry(identifier, role="player")
        self.assertEqual(service.item_reviews()[0].bindings[0].role, "player")
        self.assertEqual(service.state["enmityManualInput"]["equippedState"], "unknown")

    def test_review_ids_are_deterministic_and_projection_is_not_persisted(self) -> None:
        document = imported_document()
        first = derive_item_reviews(document)
        second = derive_item_reviews(document)
        self.assertEqual(
            [review.reviewInstanceId for review in first],
            [review.reviewInstanceId for review in second],
        )
        encoded = serialize(document)
        for prohibited in (
            b"reviewInstanceId",
            b"recognitionReports",
            b"recognitionState",
            b"referenceMatch",
        ):
            self.assertNotIn(prohibited, encoded)

    def test_common_filters_and_metadata_limits_are_enforced(self) -> None:
        service = ApplicationService()
        raw = fixture_cases()["generic-recognized-lf"]["rawText"]
        service.add_copied_entry(raw, role="mercenary", slot_label="Ring")
        self.assertEqual(len(service.item_reviews(provenance="copied-text")), 1)
        self.assertEqual(len(service.item_reviews(role="mercenary")), 1)
        self.assertEqual(len(service.item_reviews(role="player")), 0)
        self.assertEqual(len(service.item_reviews(recognition_state="recognized")), 1)
        with self.assertRaises(BuildStateError):
            service.add_copied_entry(raw, user_label="x" * 81)


class RetainedPobReviewBoundaryTests(unittest.TestCase):
    def _item_xml(self, text: str) -> str:
        return (
            '<PathOfBuilding><Build targetVersion="3_0"/>'
            f'<Items activeItemSet="1"><Item id="1">{text}</Item>'
            '<ItemSet id="1" title="Boundary" useSecondWeaponSet="false">'
            '<Slot name="Weapon 1" itemId="1"/></ItemSet></Items></PathOfBuilding>'
        )

    def _assert_reviewable(self, text: str, *, expected_code: str | None = None) -> None:
        result = importPobRawXml(self._item_xml(text))
        self.assertEqual(result["status"], "success")
        document = empty_document()
        document["importedResult"] = result
        document["importedResultSha256"] = imported_result_digest(result)
        validate_document(document)
        reviews = derive_item_reviews(document)
        self.assertEqual(len(reviews), 1)
        review = reviews[0]
        self.assertEqual(review.exactRawText, text)
        self.assertEqual(
            review.rawTextSha256,
            hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )
        service = ApplicationService()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "boundary.json"
            path.write_bytes(serialize(document))
            service.open(path)
            opened = service.item_reviews()
            self.assertEqual(len(opened), 1)
            self.assertEqual(opened[0].exactRawText, text)
            self.assertEqual(opened[0].rawTextSha256, review.rawTextSha256)
            self.assertIsNotNone(service.enmity_result())
        if expected_code is not None:
            self.assertEqual(review.recognitionReports[0].code, expected_code)

    def test_empty_and_large_pob_item_text_remain_reviewable(self) -> None:
        self._assert_reviewable("", expected_code="POB_ITEM_TEXT_EMPTY")
        exact = "a" * COPIED_ITEM_LIMITS["maxRawTextCharacters"]
        self._assert_reviewable(exact)
        over_analysis = "b" * (COPIED_ITEM_LIMITS["maxRawTextCharacters"] + 1)
        self._assert_reviewable(
            over_analysis,
            expected_code="POB_ITEM_TEXT_EXCEEDS_COPIED_RECOGNITION_ANALYSIS_LIMIT",
        )
        importer_max = "c" * DEFAULT_IMPORT_LIMITS.maxTextBytesPerElement
        self._assert_reviewable(
            importer_max,
            expected_code="POB_ITEM_TEXT_EXCEEDS_COPIED_RECOGNITION_ANALYSIS_LIMIT",
        )
        over_importer = "d" * (DEFAULT_IMPORT_LIMITS.maxTextBytesPerElement + 1)
        failed = importPobRawXml(self._item_xml(over_importer))
        self.assertEqual(failed["status"], "failure")
        self.assertEqual(failed["failure"]["code"], "XML_TEXT_LIMIT")

    def test_copied_entry_admission_limits_remain_unchanged(self) -> None:
        with self.assertRaises(CopiedItemRecognitionError) as raised:
            recognize_copied_item("")
        self.assertEqual(raised.exception.code, "COPIED_TEXT_EMPTY")
        with self.assertRaises(CopiedItemRecognitionError) as raised:
            recognize_copied_item("x" * (COPIED_ITEM_LIMITS["maxRawTextCharacters"] + 1))
        self.assertEqual(raised.exception.code, "COPIED_TEXT_LIMIT")
        retained = recognize_copied_item(
            "x" * (COPIED_ITEM_LIMITS["maxRawTextCharacters"] + 1),
            admission="retained-source",
        )
        self.assertEqual(retained.state, "manually-required")


if __name__ == "__main__":
    unittest.main()
