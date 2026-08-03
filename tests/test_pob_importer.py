from __future__ import annotations

import base64
import copy
import hashlib
import json
import subprocess
import sys
import unittest
import zlib
from unittest.mock import patch
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import golden_glory_lab.pob_import.importer as importer_module  # noqa: E402
import golden_glory_lab.pob_import.xml_tree as xml_tree_module  # noqa: E402
from golden_glory_lab.pob_import import (  # noqa: E402
    CONTRACT_VERSION,
    DEFAULT_IMPORT_LIMITS,
    deterministic_json,
    deterministic_json_bytes,
    importPobRawXml,
    importPobShareCode,
)
from golden_glory_lab.pob_import.xml_tree import (  # noqa: E402
    XmlLoadInstrumentation,
    character_value,
    load_xml_tree,
)

FIXTURES = ROOT / "fixtures" / "pob" / "proof"
GOLDENS = ROOT / "fixtures" / "pob" / "golden"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_bytes().decode("utf-8")


def share_code_for(xml: str, *, padding: bool = True) -> str:
    value = base64.b64encode(zlib.compress(xml.encode("utf-8"))).decode("ascii")
    value = value.replace("+", "-").replace("/", "_")
    return value if padding else value.rstrip("=")


def encoded_compressed(compressed: bytes) -> str:
    return (
        base64.b64encode(compressed).decode("ascii").replace("+", "-").replace("/", "_")
    )


def report_codes(result: dict[str, Any]) -> list[str]:
    return [entry["code"] for entry in result["report"]]


def all_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            keys.append(key)
            keys.extend(all_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.extend(all_keys(child))
    return keys


class PublicContractTests(unittest.TestCase):
    def test_public_contract_version_and_failure_shape(self) -> None:
        success = importPobRawXml(fixture_text("equivalent.xml"))
        failure = importPobShareCode("not!base64")
        self.assertEqual(CONTRACT_VERSION, "1.0.0")
        self.assertEqual(success["contractVersion"], CONTRACT_VERSION)
        self.assertEqual(success["status"], "success")
        self.assertIsNone(success["failure"])
        self.assertEqual(failure["contractVersion"], CONTRACT_VERSION)
        self.assertEqual(failure["status"], "failure")
        self.assertIsNone(failure["document"])
        self.assertEqual(failure["report"][0]["category"], "malformed")

    def test_options_and_producing_version_are_explicit(self) -> None:
        xml = fixture_text("equivalent.xml")
        unknown = importPobRawXml(xml)
        supplied = importPobRawXml(xml, {"producingPobVersion": "2.66.2"})
        self.assertIsNone(unknown["sourceMetadata"]["producingPobVersion"])
        self.assertEqual(unknown["sourceMetadata"]["gameTargetVersion"]["value"], "3_0")
        self.assertEqual(supplied["sourceMetadata"]["producingPobVersion"], "2.66.2")

    def test_real_draft_2020_12_schema_validates_complete_contract(self) -> None:
        schema = json.loads(
            (ROOT / "data" / "schemas" / "pob-neutral-import-v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        representative_results = [
            importPobRawXml(fixture_text("equivalent.xml")),
            importPobShareCode("%%%"),
            importPobShareCode(encoded_compressed(b"not a zlib stream")),
            importPobRawXml("<PathOfBuilding><Items></PathOfBuilding>"),
            importPobRawXml(fixture_text("duplicates-and-malformed.xml")),
            json.loads(
                (GOLDENS / "comprehensive.raw.neutral-v1.json").read_text(
                    encoding="utf-8"
                )
            ),
        ]
        for result in representative_results:
            with self.subTest(
                status=result["status"],
                failure=result["failure"]["code"] if result["failure"] else None,
            ):
                validator.validate(result)

        missing_required = copy.deepcopy(representative_results[0])
        del missing_required["document"]["sourceTree"]
        with self.assertRaises(ValidationError):
            validator.validate(missing_required)

        wrong_nested_type = copy.deepcopy(representative_results[0])
        wrong_nested_type["document"]["itemSets"][0][
            "sourceOccurrenceIndex"
        ] = "not-an-integer"
        with self.assertRaises(ValidationError):
            validator.validate(wrong_nested_type)


class Aud001FixtureMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.comprehensive = importPobRawXml(fixture_text("comprehensive.xml"))
        cls.malformed = importPobRawXml(fixture_text("duplicates-and-malformed.xml"))

    def test_matrix_01_one_set_and_empty_slot(self) -> None:
        result = importPobRawXml(fixture_text("equivalent.xml"))
        self.assertEqual(len(result["document"]["itemSets"]), 1)
        assignments = result["document"]["itemSets"][0]["assignments"]
        self.assertEqual(assignments[1]["rawItemReference"]["value"], "0")
        self.assertEqual(assignments[1]["resolution"]["state"], "empty-reference")

    def test_matrix_02_explicit_player_and_mercenary_candidates_have_no_owner(
        self,
    ) -> None:
        sets = self.comprehensive["document"]["itemSets"]
        self.assertEqual(
            [entry["title"]["value"] for entry in sets[:2]],
            ["Player candidate", "Mercenary candidate"],
        )
        self.assertNotIn("ownershipMapping", self.comprehensive["document"])
        ownership_keys = [
            key for key in all_keys(self.comprehensive) if "owner" in key.lower()
        ]
        self.assertEqual(ownership_keys, [])
        separate_application_fact = {
            "playerItemSetOccurrence": sets[0]["occurrenceId"],
            "mercenaryItemSetOccurrence": sets[1]["occurrenceId"],
        }
        self.assertNotIn(separate_application_fact, self.comprehensive.values())

    def test_matrix_03_multiple_mapping_candidates_are_manually_required(self) -> None:
        entry = next(
            item
            for item in self.comprehensive["report"]
            if item["code"] == "OWNERSHIP_MAPPING_REQUIRED"
        )
        self.assertEqual(entry["category"], "manually required")
        self.assertEqual(
            entry["candidateTargets"],
            ["item-set-0001", "item-set-0002", "item-set-0003"],
        )

    def test_matrix_04_title_states_and_duplicate_generic_titles(self) -> None:
        titles = [entry["title"] for entry in self.malformed["document"]["itemSets"]]
        self.assertEqual(titles[0], {"state": "missing", "value": None})
        self.assertEqual(titles[1], {"state": "empty", "value": ""})
        self.assertEqual(titles[2]["value"], "Item Set")
        self.assertEqual(titles[3]["value"], "Item Set")

    def test_matrix_05_primary_and_alternate_weapons_are_all_retained(self) -> None:
        sets = self.comprehensive["document"]["itemSets"]
        first_names = [
            entry["originalSlotName"]["value"] for entry in sets[0]["assignments"]
        ]
        second_names = [
            entry["originalSlotName"]["value"] for entry in sets[1]["assignments"]
        ]
        self.assertTrue(
            {"Weapon 1", "Weapon 2", "Weapon 1 Swap", "Weapon 2 Swap"}.issubset(
                first_names
            )
        )
        self.assertTrue(
            {"Weapon 1", "Weapon 2", "Weapon 1 Swap", "Weapon 2 Swap"}.issubset(
                second_names
            )
        )
        self.assertFalse(sets[0]["useSecondWeaponSet"]["parsed"])
        self.assertTrue(sets[1]["useSecondWeaponSet"]["parsed"])

    def test_matrix_06_shield_and_quiver_remain_weapon_2_assignments(self) -> None:
        items = {
            entry["parsedId"]: entry
            for entry in self.comprehensive["document"]["items"]
        }
        self.assertIn("Synthetic Shield", items[2]["xmlCharacterValue"])
        self.assertIn("Synthetic Quiver", items[3]["xmlCharacterValue"])
        weapon_two_refs = [
            assignment["parsedItemId"]
            for item_set in self.comprehensive["document"]["itemSets"]
            for assignment in item_set["assignments"]
            if assignment["originalSlotName"]["value"] == "Weapon 2"
        ]
        self.assertEqual(weapon_two_refs, [2, 3])

    def test_matrix_07_abyssal_children_include_empty_and_missing_parent_states(
        self,
    ) -> None:
        assignments = self.comprehensive["document"]["itemSets"][0]["assignments"]
        children = [
            entry for entry in assignments if entry["derivedAbyssalParent"] is not None
        ]
        self.assertEqual(len(children), 3)
        self.assertIn(
            "empty-reference", [entry["resolution"]["state"] for entry in children]
        )
        self.assertIn(
            "missing-parent-assignment",
            [entry["derivedAbyssalParent"]["state"] for entry in children],
        )
        self.assertTrue(all(entry["originalSlotName"]["value"] for entry in children))

    def test_matrix_08_passive_jewels_remain_separate_from_equipment(self) -> None:
        refs = self.comprehensive["document"]["passiveJewelReferences"]
        self.assertEqual(len(refs), 3)
        self.assertEqual(
            [entry["resolution"]["state"] for entry in refs],
            ["resolved", "empty-reference", "resolved"],
        )
        item = next(
            entry
            for entry in self.comprehensive["document"]["items"]
            if entry["parsedId"] == 5
        )
        self.assertEqual(item["usage"]["passiveCandidateReferenceCount"], 2)
        self.assertEqual(item["usage"]["equipmentCandidateReferenceCount"], 0)

    def test_matrix_09_unused_pool_item_is_retained(self) -> None:
        item = next(
            entry
            for entry in self.comprehensive["document"]["items"]
            if entry["parsedId"] == 6
        )
        self.assertEqual(item["usage"]["state"], "unused")
        self.assertIn("UNUSED_POOL_ITEM_RETAINED", report_codes(self.comprehensive))

    def test_matrix_10_reused_and_duplicate_references_never_last_write_win(
        self,
    ) -> None:
        document = self.malformed["document"]
        self.assertEqual([item["parsedId"] for item in document["items"][:2]], [1, 1])
        first_ref = document["itemSets"][0]["assignments"][0]
        self.assertEqual(first_ref["resolution"]["state"], "ambiguous")
        self.assertEqual(
            first_ref["resolution"]["candidateOccurrences"], ["item-0001", "item-0002"]
        )
        duplicate_slots = document["itemSets"][0]["assignments"][:2]
        self.assertEqual(len(duplicate_slots), 2)
        self.assertIn("DUPLICATE_SLOT_ASSIGNMENT", duplicate_slots[0]["warnings"])
        self.assertEqual(
            document["itemsSections"][0]["activeItemSetReference"]["resolution"][
                "state"
            ],
            "ambiguous",
        )

    def test_matrix_11_observed_out_of_range_text_is_opaque_and_unclamped(self) -> None:
        item = next(
            entry
            for entry in self.comprehensive["document"]["items"]
            if entry["parsedId"] == 7
        )
        self.assertIn("+999% to Fire Resistance", item["xmlCharacterValue"])
        self.assertNotIn("clamp", deterministic_json(item).lower())
        self.assertNotIn("ownershipMapping", self.comprehensive["document"])

    def test_matrix_12_xml_entities_cdata_boundaries_and_line_endings(self) -> None:
        xml = (
            '<PathOfBuilding>\r\n<Items><Item id="1">A &amp; B<![CDATA[<C>]]>\rD\nE</Item>'
            '<ItemSet id="1"><Slot name="Weapon 1" itemId="1"/></ItemSet></Items></PathOfBuilding>'
        )
        result = importPobRawXml(xml)
        self.assertEqual(result["envelope"]["originalInput"], xml)
        self.assertIsNone(result["envelope"]["decodedXml"])
        self.assertEqual(
            result["document"]["items"][0]["xmlCharacterValue"], "A & B<C>\nD\nE"
        )
        child_kinds = [
            child["kind"]
            for child in result["document"]["items"][0]["orderedChildMaterial"]
        ]
        self.assertEqual(child_kinds, ["text", "cdata", "text"])

    def test_matrix_13_malformed_references_unknown_slots_attributes_and_elements(
        self,
    ) -> None:
        codes = report_codes(self.malformed)
        for code in [
            "MALFORMED_ITEM_REFERENCE",
            "UNRESOLVED_ITEM_REFERENCE",
            "AMBIGUOUS_ITEM_REFERENCE",
            "UNKNOWN_SLOT_NAME",
            "UNKNOWN_ATTRIBUTE",
        ]:
            self.assertIn(code, codes)
        assignments = self.malformed["document"]["itemSets"][0]["assignments"]
        self.assertEqual(
            [entry["resolution"]["state"] for entry in assignments],
            [
                "ambiguous",
                "unresolved",
                "malformed",
                "malformed",
                "empty-reference",
                "ambiguous",
            ],
        )
        self.assertEqual(len(self.malformed["document"]["items"]), 4)

    def test_matrix_14_reimport_candidates_expose_evidence_without_merge(self) -> None:
        before = importPobRawXml(fixture_text("reimport-before.xml"))
        after = importPobRawXml(fixture_text("reimport-after.xml"))
        before_unique = next(
            item for item in before["document"]["items"] if item["parsedId"] == 1
        )
        after_unique = next(
            item for item in after["document"]["items"] if item["parsedId"] == 1
        )
        self.assertEqual(
            before_unique["comparisonEvidence"]["uniqueIdLine"]["value"],
            "stable-api-id",
        )
        self.assertEqual(
            after_unique["comparisonEvidence"]["uniqueIdLine"]["value"], "stable-api-id"
        )
        self.assertNotEqual(
            before_unique["comparisonEvidence"]["exactXmlCharacterValueSha256"],
            after_unique["comparisonEvidence"]["exactXmlCharacterValueSha256"],
        )
        self.assertFalse(any("merge" in key.lower() for key in all_keys(before)))
        self.assertEqual(
            [item_set["parsedId"] for item_set in before["document"]["itemSets"]],
            [1, 2],
        )
        self.assertEqual(
            [item_set["parsedId"] for item_set in after["document"]["itemSets"]],
            [2, 1],
        )
        self.assertEqual(before["document"]["itemSets"][0]["title"]["value"], "Before")
        renamed = next(
            item_set
            for item_set in after["document"]["itemSets"]
            if item_set["parsedId"] == 1
        )
        self.assertEqual(renamed["title"]["value"], "Renamed")

    def test_matrix_15_legacy_synthesizes_once_and_transitional_does_not_double_count(
        self,
    ) -> None:
        legacy = importPobRawXml(fixture_text("legacy.xml"))
        transitional = importPobRawXml(fixture_text("transitional.xml"))
        self.assertEqual(len(legacy["document"]["itemSets"]), 1)
        self.assertTrue(legacy["document"]["itemSets"][0]["provenance"]["synthesized"])
        self.assertEqual(len(transitional["document"]["itemSets"]), 1)
        section = transitional["document"]["itemsSections"][0]
        self.assertTrue(section["transitionalTopLevelRepresentation"])
        self.assertEqual(len(section["legacyTopLevelAssignments"]), 1)

    def test_matrix_16_equivalent_raw_and_share_envelopes_have_same_semantics(
        self,
    ) -> None:
        xml = fixture_text("equivalent.xml")
        code = fixture_text("equivalent.share.txt")
        raw = importPobRawXml(xml)
        share = importPobShareCode(code)
        self.assertEqual(raw["status"], "success")
        self.assertEqual(share["status"], "success")
        self.assertEqual(raw["document"], share["document"])
        self.assertEqual(raw["sourceMetadata"], share["sourceMetadata"])
        self.assertEqual(raw["report"], share["report"])
        self.assertNotEqual(
            raw["envelope"]["inputKind"], share["envelope"]["inputKind"]
        )
        self.assertEqual(share["envelope"]["decodedXml"], xml)

    def test_matrix_17_fatal_syntax_stops_without_partial_tree(self) -> None:
        xml = fixture_text("equivalent.xml")
        compressed = zlib.compress(xml.encode("utf-8"))
        raw_compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
        raw_deflate = (
            raw_compressor.compress(xml.encode("utf-8")) + raw_compressor.flush()
        )
        cases = {
            "invalid-base64": importPobShareCode("%%%"),
            "truncated-zlib": importPobShareCode(encoded_compressed(compressed[:-2])),
            "trailing-zlib": importPobShareCode(
                encoded_compressed(compressed + b"trailing")
            ),
            "raw-deflate": importPobShareCode(encoded_compressed(raw_deflate)),
            "ill-formed-xml": importPobRawXml(
                "<PathOfBuilding><Items></PathOfBuilding>"
            ),
        }
        expected = {
            "invalid-base64": "INVALID_BASE64_ALPHABET",
            "truncated-zlib": "ZLIB_TRUNCATED",
            "trailing-zlib": "ZLIB_TRAILING_DATA",
            "raw-deflate": "ZLIB_INVALID_STREAM",
            "ill-formed-xml": "XML_SYNTAX_ERROR",
        }
        for name, result in cases.items():
            with self.subTest(name=name):
                self.assertEqual(result["status"], "failure")
                self.assertEqual(result["failure"]["code"], expected[name])
                self.assertIsNone(result["document"])
                self.assertIn("originalInput", result["envelope"])
        truncated = cases["truncated-zlib"]["envelope"]
        self.assertEqual(
            truncated["normalizedShareCode"], encoded_compressed(compressed[:-2])
        )
        self.assertEqual(
            truncated["sizes"]["decodedCompressedBytes"], len(compressed) - 2
        )
        self.assertIn(
            "decoded-compressed-sha256",
            [entry["name"] for entry in truncated["hashes"]],
        )

    def test_matrix_18_hostile_bounds_and_all_limit_boundaries(self) -> None:
        xml = fixture_text("equivalent.xml")
        code = share_code_for(xml)
        compressed_size = len(
            base64.b64decode(code.replace("-", "+").replace("_", "/"))
        )
        xml_size = len(xml.encode("utf-8"))
        boundary_cases = [
            (
                "share-below",
                importPobShareCode(
                    code, {"limits": {"maxShareCodeCharacters": len(code) + 1}}
                ),
                "success",
            ),
            (
                "share-at",
                importPobShareCode(
                    code, {"limits": {"maxShareCodeCharacters": len(code)}}
                ),
                "success",
            ),
            (
                "share-above",
                importPobShareCode(
                    code, {"limits": {"maxShareCodeCharacters": len(code) - 1}}
                ),
                "SHARE_CODE_INPUT_LIMIT",
            ),
            (
                "decoded-below",
                importPobShareCode(
                    code, {"limits": {"maxDecodedCompressedBytes": compressed_size + 1}}
                ),
                "success",
            ),
            (
                "decoded-at",
                importPobShareCode(
                    code, {"limits": {"maxDecodedCompressedBytes": compressed_size}}
                ),
                "success",
            ),
            (
                "decoded-above",
                importPobShareCode(
                    code, {"limits": {"maxDecodedCompressedBytes": compressed_size - 1}}
                ),
                "DECODED_COMPRESSED_LIMIT",
            ),
            (
                "decompressed-below",
                importPobShareCode(
                    code, {"limits": {"maxDecompressedXmlBytes": xml_size + 1}}
                ),
                "success",
            ),
            (
                "decompressed-at",
                importPobShareCode(
                    code, {"limits": {"maxDecompressedXmlBytes": xml_size}}
                ),
                "success",
            ),
            (
                "decompressed-above",
                importPobShareCode(
                    code, {"limits": {"maxDecompressedXmlBytes": xml_size - 1}}
                ),
                "DECOMPRESSED_XML_LIMIT",
            ),
            (
                "raw-below",
                importPobRawXml(xml, {"limits": {"maxRawXmlBytes": xml_size + 1}}),
                "success",
            ),
            (
                "raw-at",
                importPobRawXml(xml, {"limits": {"maxRawXmlBytes": xml_size}}),
                "success",
            ),
            (
                "raw-above",
                importPobRawXml(xml, {"limits": {"maxRawXmlBytes": xml_size - 1}}),
                "RAW_XML_LIMIT",
            ),
        ]
        for name, result, expectation in boundary_cases:
            with self.subTest(name=name):
                actual = (
                    result["status"]
                    if result["status"] == "success"
                    else result["failure"]["code"]
                )
                self.assertEqual(actual, expectation)

        depth_at = "<PathOfBuilding><a><b><c/></b></a></PathOfBuilding>"
        depth_above = "<PathOfBuilding><a><b><c><d/></c></b></a></PathOfBuilding>"
        self.assertEqual(
            importPobRawXml(depth_at, {"limits": {"maxXmlDepth": 5}})["status"],
            "success",
        )
        self.assertEqual(
            importPobRawXml(depth_at, {"limits": {"maxXmlDepth": 4}})["status"],
            "success",
        )
        self.assertEqual(
            importPobRawXml(depth_above, {"limits": {"maxXmlDepth": 4}})["failure"][
                "code"
            ],
            "XML_DEPTH_LIMIT",
        )
        elements_at = "<PathOfBuilding><a/><b/></PathOfBuilding>"
        elements_above = "<PathOfBuilding><a/><b/><c/></PathOfBuilding>"
        self.assertEqual(
            importPobRawXml(elements_at, {"limits": {"maxXmlElements": 4}})["status"],
            "success",
        )
        self.assertEqual(
            importPobRawXml(elements_at, {"limits": {"maxXmlElements": 3}})["status"],
            "success",
        )
        self.assertEqual(
            importPobRawXml(elements_above, {"limits": {"maxXmlElements": 3}})[
                "failure"
            ]["code"],
            "XML_ELEMENT_LIMIT",
        )
        attrs_at = '<PathOfBuilding a="1" b="2"/>'
        attrs_above = '<PathOfBuilding a="1" b="2" c="3"/>'
        self.assertEqual(
            importPobRawXml(attrs_at, {"limits": {"maxAttributesPerElement": 3}})[
                "status"
            ],
            "success",
        )
        self.assertEqual(
            importPobRawXml(attrs_at, {"limits": {"maxAttributesPerElement": 2}})[
                "status"
            ],
            "success",
        )
        self.assertEqual(
            importPobRawXml(attrs_above, {"limits": {"maxAttributesPerElement": 2}})[
                "failure"
            ]["code"],
            "XML_ATTRIBUTE_LIMIT",
        )
        text_at = "<PathOfBuilding>12345</PathOfBuilding>"
        text_above = "<PathOfBuilding>123456</PathOfBuilding>"
        self.assertEqual(
            importPobRawXml(text_at, {"limits": {"maxTextBytesPerElement": 6}})[
                "status"
            ],
            "success",
        )
        self.assertEqual(
            importPobRawXml(text_at, {"limits": {"maxTextBytesPerElement": 5}})[
                "status"
            ],
            "success",
        )
        self.assertEqual(
            importPobRawXml(text_above, {"limits": {"maxTextBytesPerElement": 5}})[
                "failure"
            ]["code"],
            "XML_TEXT_LIMIT",
        )
        report_limited = importPobRawXml(
            '<PathOfBuilding a="1" b="2" c="3" d="4"/>',
            {"limits": {"maxReportEntries": 3}},
        )
        self.assertEqual(len(report_limited["report"]), 3)
        self.assertEqual(report_limited["report"][-1]["code"], "REPORT_LIMIT_REACHED")

        dtd = '<!DOCTYPE PathOfBuilding [<!ENTITY x SYSTEM "file:///definitely-not-read">]><PathOfBuilding>&x;</PathOfBuilding>'
        dtd_result = importPobRawXml(dtd)
        self.assertEqual(dtd_result["failure"]["code"], "XML_DTD_FORBIDDEN")
        self.assertNotIn(
            "definitely-not-read", deterministic_json(dtd_result["document"])
        )

    def test_matrix_19_deterministic_repetition_and_golden_output(self) -> None:
        xml = fixture_text("comprehensive.xml")
        outputs = [deterministic_json_bytes(importPobRawXml(xml)) for _ in range(3)]
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[1], outputs[2])
        digests = [hashlib.sha256(output).hexdigest() for output in outputs]
        self.assertEqual(len(set(digests)), 1)
        golden = (GOLDENS / "comprehensive.raw.neutral-v1.json").read_bytes()
        self.assertEqual(len(golden), 87_288)
        self.assertEqual(
            hashlib.sha256(golden).hexdigest(),
            "a1dc0f9fd312b82ab05307e1112906525fa75fab0e8f3c06265094f804da0429",
        )
        self.assertEqual(outputs[0], golden)


class SecurityBoundaryRepairTests(unittest.TestCase):
    def test_fragmented_character_data_is_linear_bounded_and_deterministic(self) -> None:
        repetitions = 2_000
        expected = "a&" * repetitions
        xml = (
            '<PathOfBuilding><Items><Item id="1">'
            + "a&amp;" * repetitions
            + '</Item><ItemSet id="1"/></Items></PathOfBuilding>'
        )
        limits = DEFAULT_IMPORT_LIMITS.with_overrides(
            {"maxTextBytesPerElement": len(expected.encode("utf-8"))}
        )
        instrumentation = XmlLoadInstrumentation()
        loaded = load_xml_tree(
            bytearray(xml.encode("utf-8")),
            limits,
            instrumentation=instrumentation,
        )
        items = next(
            child
            for child in loaded["root"]["children"]
            if child["kind"] == "element" and child["name"] == "Items"
        )
        item = next(
            child
            for child in items["children"]
            if child["kind"] == "element" and child["name"] == "Item"
        )
        self.assertEqual(character_value(item), expected)
        self.assertEqual([child["kind"] for child in item["children"]], ["text"])
        self.assertGreater(instrumentation.characterCallbacks, repetitions)
        self.assertEqual(
            instrumentation.characterUtf8EncodeCalls,
            instrumentation.characterCallbacks,
        )
        self.assertEqual(instrumentation.retainedTextRescans, 0)
        self.assertGreater(instrumentation.maxChunksPerConsolidation, repetitions)

        accepted = importPobRawXml(
            xml,
            {"limits": {"maxTextBytesPerElement": len(expected.encode("utf-8"))}},
        )
        repeated = importPobRawXml(
            xml,
            {"limits": {"maxTextBytesPerElement": len(expected.encode("utf-8"))}},
        )
        self.assertEqual(deterministic_json_bytes(accepted), deterministic_json_bytes(repeated))
        rejected = importPobRawXml(
            xml,
            {
                "limits": {
                    "maxTextBytesPerElement": len(expected.encode("utf-8")) - 1
                }
            },
        )
        self.assertEqual(rejected["failure"]["code"], "XML_TEXT_LIMIT")

    def test_oversized_input_rejection_never_encodes_a_complete_copy(self) -> None:
        real_encoder = importer_module._encode_utf8_chunk
        encoded_chunk_sizes: list[int] = []

        def instrument(value: str) -> bytes:
            encoded = real_encoder(value)
            encoded_chunk_sizes.append(len(encoded))
            return encoded

        raw = "é" * 2_000
        with patch.object(importer_module, "_encode_utf8_chunk", side_effect=instrument):
            result = importPobRawXml(
                raw,
                {
                    "limits": {
                        "maxRawXmlBytes": 10,
                        "inputEncodingChunkCharacters": 7,
                    }
                },
            )
        self.assertEqual(result["failure"]["code"], "RAW_XML_LIMIT")
        self.assertIs(result["envelope"]["originalInput"], raw)
        self.assertEqual(result["envelope"]["sizes"]["originalInputUtf8Bytes"], 4_000)
        self.assertEqual(
            result["envelope"]["sizes"]["originalInputUtf8State"],
            "limit-exceeded",
        )
        self.assertTrue(encoded_chunk_sizes)
        self.assertLessEqual(max(encoded_chunk_sizes), 28)
        self.assertNotIn(4_000, encoded_chunk_sizes)

        encoded_chunk_sizes.clear()
        share = "A" * 2_000
        with patch.object(importer_module, "_encode_utf8_chunk", side_effect=instrument):
            share_result = importPobShareCode(
                share,
                {"limits": {"maxShareCodeCharacters": 10}},
            )
        self.assertEqual(
            share_result["failure"]["code"], "SHARE_CODE_INPUT_LIMIT"
        )
        self.assertIs(share_result["envelope"]["originalInput"], share)
        self.assertEqual(encoded_chunk_sizes, [])
        self.assertEqual(
            share_result["envelope"]["sizes"]["originalInputUtf8State"],
            "not-scanned-input-limit",
        )

    def test_supported_below_floor_and_malformed_expat_versions(self) -> None:
        xml = fixture_text("equivalent.xml")
        actual = importPobRawXml(xml)
        self.assertEqual(actual["status"], "success")
        self.assertEqual(actual["envelope"]["runtimeSecurity"]["status"], "supported")
        self.assertGreaterEqual(
            actual["envelope"]["runtimeSecurity"]["parsedExpatVersion"],
            [2, 7, 2],
        )

        with patch.object(xml_tree_module.expat, "EXPAT_VERSION", "expat_2.7.2"):
            supported = importPobRawXml(xml)
        self.assertEqual(supported["status"], "success")

        with patch.object(xml_tree_module.expat, "EXPAT_VERSION", "expat_2.7.1"):
            unsupported = importPobRawXml(xml)
        self.assertEqual(unsupported["failure"]["code"], "XML_RUNTIME_UNSUPPORTED")
        self.assertEqual(unsupported["failure"]["stage"], "xml")
        self.assertEqual(
            unsupported["envelope"]["runtimeSecurity"]["status"], "unsupported"
        )

        with patch.object(xml_tree_module.expat, "EXPAT_VERSION", "future-version"):
            malformed = importPobRawXml(xml)
        self.assertEqual(malformed["failure"]["code"], "XML_RUNTIME_UNSUPPORTED")
        self.assertEqual(
            malformed["envelope"]["runtimeSecurity"]["status"], "unparseable"
        )

        with patch.object(
            xml_tree_module.expat,
            "EXPAT_VERSION",
            f"expat_{'9' * 5_000}.0.0",
        ):
            protected_numeric = importPobRawXml(xml)
        self.assertEqual(
            protected_numeric["failure"]["code"], "XML_RUNTIME_UNSUPPORTED"
        )
        self.assertEqual(
            protected_numeric["envelope"]["runtimeSecurity"]["status"],
            "unparseable",
        )

    def test_numeric_lexeme_boundaries_and_protected_int_conversion(self) -> None:
        def result_for(value: str) -> dict[str, Any]:
            xml = (
                f'<PathOfBuilding><Items activeItemSet="{value}">'
                f'<ItemSet id="{value}"/></Items></PathOfBuilding>'
            )
            return importPobRawXml(
                xml, {"limits": {"maxNumericLexemeDigits": 4}}
            )

        below = result_for("999")
        at = result_for("9999")
        above = result_for("99999")
        self.assertEqual(
            below["document"]["itemsSections"][0]["activeItemSetReference"][
                "resolution"
            ]["state"],
            "resolved",
        )
        self.assertEqual(
            at["document"]["itemsSections"][0]["activeItemSetReference"][
                "resolution"
            ]["state"],
            "resolved",
        )
        self.assertEqual(
            above["document"]["itemsSections"][0]["activeItemSetReference"][
                "resolution"
            ]["state"],
            "malformed",
        )
        self.assertEqual(above["document"]["itemSets"][0]["rawId"]["value"], "99999")
        self.assertIsNone(above["document"]["itemSets"][0]["parsedId"])

        protected = "9" * 5_000
        protected_result = importPobRawXml(
            f'<PathOfBuilding><Items activeItemSet="{protected}"><ItemSet id="{protected}"/></Items></PathOfBuilding>'
        )
        self.assertEqual(protected_result["status"], "success")
        self.assertEqual(
            protected_result["document"]["itemsSections"][0][
                "activeItemSetReference"
            ]["resolution"]["state"],
            "malformed",
        )

        passive_result = importPobRawXml(
            f'<PathOfBuilding><Tree><Spec><Sockets><Socket nodeId="{protected}" itemId="0"/></Sockets></Spec></Tree></PathOfBuilding>'
        )
        passive = passive_result["document"]["passiveJewelReferences"][0]
        self.assertEqual(passive["rawNodeId"]["value"], protected)
        self.assertIsNone(passive["parsedNodeId"])
        self.assertIn("MALFORMED_PASSIVE_NODE_ID", passive["warnings"])

    def test_lone_surrogates_return_stable_public_failures(self) -> None:
        raw = importPobRawXml("<PathOfBuilding>\ud800</PathOfBuilding>")
        share = importPobShareCode("AA\ud800AA")
        self.assertEqual(raw["failure"]["code"], "RAW_XML_UTF8_INVALID")
        self.assertEqual(raw["failure"]["stage"], "xml")
        self.assertEqual(share["failure"]["code"], "SHARE_CODE_UTF8_INVALID")
        self.assertEqual(share["failure"]["stage"], "envelope")
        self.assertIn(b"\\ud800", deterministic_json_bytes(raw))
        self.assertIn(b"\\ud800", deterministic_json_bytes(share))


class ReferenceSemanticsRepairTests(unittest.TestCase):
    def test_complete_active_item_set_state_matrix(self) -> None:
        result = importPobRawXml(
            fixture_text("active-set-states.xml"),
            {"limits": {"maxNumericLexemeDigits": 4}},
        )
        references = [
            section["activeItemSetReference"]
            for section in result["document"]["itemsSections"]
        ]
        self.assertEqual(
            [reference["resolution"]["state"] for reference in references],
            [
                "missing",
                "malformed",
                "malformed",
                "malformed",
                "unresolved",
                "unresolved",
                "ambiguous",
                "resolved",
            ],
        )
        self.assertEqual(references[0]["raw"], {"state": "missing", "value": None})
        self.assertEqual(references[3]["raw"]["value"], "12345")
        self.assertEqual(references[4]["parsedId"], 0)
        self.assertNotIn(
            "/PathOfBuilding[1]/Items[1]/@activeItemSet",
            [
                entry["location"]
                for entry in result["report"]
                if entry["code"] == "MALFORMED_ITEM_SET_REFERENCE"
            ],
        )

    def test_zero_semantics_are_context_specific(self) -> None:
        paths = importPobRawXml(fixture_text("reference-paths.xml"))
        section = paths["document"]["itemsSections"][0]
        self.assertEqual(
            section["activeItemSetReference"]["resolution"]["state"], "resolved"
        )
        self.assertEqual(
            paths["document"]["itemSets"][0]["assignments"][0]["resolution"][
                "state"
            ],
            "empty-reference",
        )
        self.assertEqual(
            paths["document"]["passiveJewelReferences"][0]["resolution"]["state"],
            "empty-reference",
        )
        self.assertEqual(
            [
                reference["resolution"]["state"]
                for reference in paths["document"]["itemSetCrossReferences"]
            ],
            ["resolved", "unresolved"],
        )
        active_matrix = importPobRawXml(
            fixture_text("active-set-states.xml"),
            {"limits": {"maxNumericLexemeDigits": 4}},
        )
        self.assertEqual(
            active_matrix["document"]["itemsSections"][4][
                "activeItemSetReference"
            ]["resolution"]["state"],
            "unresolved",
        )

    def test_only_audited_socket_and_gem_paths_are_projected(self) -> None:
        result = importPobRawXml(fixture_text("reference-paths.xml"))
        passive = result["document"]["passiveJewelReferences"]
        cross = result["document"]["itemSetCrossReferences"]
        self.assertEqual(len(passive), 1)
        self.assertEqual(len(cross), 2)
        self.assertEqual(
            passive[0]["sourcePath"],
            "/PathOfBuilding[1]/Tree[1]/Spec[1]/Sockets[1]/Socket[1]",
        )
        self.assertTrue(
            all("/Future[" not in reference["sourcePath"] for reference in passive + cross)
        )
        retained = deterministic_json(result["document"]["sourceTree"])
        self.assertIn('"name": "Future"', retained)
        self.assertIn('"name": "offPath"', retained)


class PreservationAndIsolationRepairTests(unittest.TestCase):
    def test_adjacent_cdata_and_document_level_events_are_preserved(self) -> None:
        xml = fixture_text("preservation-events.xml")
        first = importPobRawXml(xml)
        second = importPobRawXml(xml)
        self.assertEqual(
            [event["kind"] for event in first["document"]["documentEvents"]],
            [
                "processing-instruction",
                "comment",
                "root-element",
                "comment",
                "processing-instruction",
            ],
        )
        events = first["document"]["documentEvents"]
        self.assertEqual(events[0], {"kind": "processing-instruction", "target": "before", "value": "proof"})
        self.assertEqual(events[1], {"kind": "comment", "value": "before-root"})
        self.assertEqual(events[3], {"kind": "comment", "value": "after-root"})
        self.assertEqual(events[4], {"kind": "processing-instruction", "target": "after", "value": "proof"})
        item = first["document"]["items"][0]
        self.assertEqual(
            [child["kind"] for child in item["orderedChildMaterial"]],
            ["text", "cdata", "cdata", "text"],
        )
        self.assertEqual(
            [child["value"] for child in item["orderedChildMaterial"]],
            ["start", "first", "second", "end"],
        )
        self.assertEqual(item["xmlCharacterValue"], "startfirstsecondend")
        self.assertEqual(deterministic_json_bytes(first), deterministic_json_bytes(second))

    def test_results_are_deeply_isolated_from_global_state(self) -> None:
        xml = fixture_text("equivalent.xml")
        pristine = importPobRawXml(xml)
        mutated = importPobRawXml(xml)
        mutated["envelope"]["evidenceProfile"][0]["sourceId"] = "mutated"
        mutated["envelope"]["runtimeSecurity"]["parsedExpatVersion"][0] = 0
        mutated["envelope"]["limits"]["maxRawXmlBytes"] = 1
        mutated["envelope"]["normalizations"].append({"code": "MUTATED"})
        later = importPobRawXml(xml)
        self.assertEqual(later, pristine)
        self.assertEqual(
            deterministic_json_bytes(later), deterministic_json_bytes(pristine)
        )
        self.assertEqual(DEFAULT_IMPORT_LIMITS.maxRawXmlBytes, 8_000_000)


class EnvelopeNormalizationTests(unittest.TestCase):
    def test_outer_whitespace_and_missing_padding_are_explicit(self) -> None:
        xml = fixture_text("equivalent.xml")
        code = share_code_for(xml, padding=False)
        result = importPobShareCode(f" \r\n{code}\t")
        self.assertEqual(result["status"], "success")
        self.assertEqual(
            [entry["code"] for entry in result["envelope"]["normalizations"]],
            ["TRIM_OUTER_ASCII_WHITESPACE", "RESTORE_BASE64_PADDING"],
        )

    def test_trim_is_reported_even_when_later_base64_validation_fails(self) -> None:
        result = importPobShareCode(" \r\n%%%\t")
        self.assertEqual(result["failure"]["code"], "INVALID_BASE64_ALPHABET")
        self.assertEqual(result["envelope"]["normalizedShareCode"], "%%%")
        self.assertEqual(
            [entry["code"] for entry in result["envelope"]["normalizations"]],
            ["TRIM_OUTER_ASCII_WHITESPACE"],
        )

    def test_internal_whitespace_is_not_silently_discarded(self) -> None:
        code = share_code_for(fixture_text("equivalent.xml"))
        midpoint = len(code) // 2
        result = importPobShareCode(code[:midpoint] + "\n" + code[midpoint:])
        self.assertEqual(result["failure"]["code"], "INVALID_BASE64_ALPHABET")


class CliSmokeTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [sys.executable, str(ROOT / "proofs" / "pob_import_cli.py"), *args],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_raw_xml_file_smoke(self) -> None:
        completed = self.run_cli("--raw-xml", str(FIXTURES / "equivalent.xml"))
        self.assertEqual(completed.returncode, 0, completed.stderr.decode())
        self.assertEqual(json.loads(completed.stdout)["status"], "success")

    def test_share_code_file_and_string_smoke(self) -> None:
        path_result = self.run_cli(
            "--share-code-file", str(FIXTURES / "equivalent.share.txt")
        )
        string_result = self.run_cli(
            "--share-code", fixture_text("equivalent.share.txt").strip()
        )
        self.assertEqual(path_result.returncode, 0, path_result.stderr.decode())
        self.assertEqual(string_result.returncode, 0, string_result.stderr.decode())
        self.assertEqual(
            json.loads(path_result.stdout)["document"],
            json.loads(string_result.stdout)["document"],
        )

    def test_fatal_input_has_nonzero_exit_and_structured_output(self) -> None:
        completed = self.run_cli("--share-code", "not!base64")
        self.assertEqual(completed.returncode, 2)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "failure")
        self.assertEqual(result["failure"]["stage"], "envelope")


class DefaultLimitContractTests(unittest.TestCase):
    def test_exact_proof_defaults(self) -> None:
        self.assertEqual(
            DEFAULT_IMPORT_LIMITS.to_dict(),
            {
                "maxShareCodeCharacters": 4_000_000,
                "maxDecodedCompressedBytes": 3_000_000,
                "maxDecompressedXmlBytes": 8_000_000,
                "maxRawXmlBytes": 8_000_000,
                "maxXmlDepth": 64,
                "maxXmlElements": 50_000,
                "maxAttributesPerElement": 64,
                "maxTextBytesPerElement": 1_000_000,
                "maxNumericLexemeDigits": 128,
                "maxReportEntries": 256,
                "inputEncodingChunkCharacters": 4_096,
                "decompressionChunkBytes": 16_384,
            },
        )


if __name__ == "__main__":
    unittest.main()
