from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golden_glory_lab.build_state import (  # noqa: E402
    BuildStateError,
    empty_document,
    empty_flame_link_player_chain,
    validate_document,
)
from golden_glory_lab.desktop.service import ApplicationService  # noqa: E402
from golden_glory_lab.domain import (  # noqa: E402
    EXPECTED_ARTIFACT_ID,
    FlameLinkTableError,
    evaluate_flame_link,
    load_flame_link_level_table,
    numeric_context_for,
    parse_flame_link_level_table_bytes,
    recognize_player_chain_text,
    table_sha256,
)
from golden_glory_lab.domain.decimal_input import DECIMAL_DIGIT_LIMIT  # noqa: E402


def complete_chain(**overrides: object) -> dict:
    chain = empty_flame_link_player_chain()
    chain["goldenGlory"].update(
        {
            "allocatedState": "not-allocated",
            "mercenaryTargetState": "yes",
            "reviewedLightRadiusPct": "0",
            "provenanceKind": "manual-reviewed",
            "reviewState": "reviewed",
        }
    )
    chain["directLinkBuffEffect"].update(
        {
            "reviewedDirectPct": "0",
            "provenanceKind": "manual-reviewed",
            "reviewState": "reviewed",
        }
    )
    for entry in chain["conditionalContributions"]:
        entry["conditionState"] = "inactive"
    chain["flameLinkLevel"]["additionalLinkGemLevels"][0]["activeState"] = "inactive"
    chain["luminaryMaximumLife"].update(
        {
            "reviewedLife": "5000",
            "provenanceKind": "manual-reviewed",
            "reviewState": "reviewed",
        }
    )
    for key, value in overrides.items():
        if key in {
            "goldenGlory",
            "directLinkBuffEffect",
            "luminaryMaximumLife",
            "flameLinkLevel",
        } and isinstance(value, dict):
            chain[key].update(value)
        else:
            chain[key] = value
    return chain


TABLE_PATH = (
    ROOT
    / "src"
    / "golden_glory_lab"
    / "runtime_data"
    / "flame-link-level-table-v1.json"
)
PINNED_TABLE_SHA256 = (
    "e2cf21212e0ae6e1c3a23cab5ea94e723b69bf0bae89bf0c6906740c71c4a70c"
)


class NumericContextTests(unittest.TestCase):
    def test_numeric_context_covers_digit_limit_products(self) -> None:
        left = Decimal("9" * DECIMAL_DIGIT_LIMIT)
        right = Decimal("9" * 40)
        context = numeric_context_for(left, right, Decimal("0.05"), Decimal("1.5"))
        self.assertGreaterEqual(context.prec, DECIMAL_DIGIT_LIMIT + 40)


class FlameLinkRepairDomainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.table = load_flame_link_level_table()

    def test_negative_life_unavailable_without_exception(self) -> None:
        chain = complete_chain(
            luminaryMaximumLife={
                "reviewedLife": "-1",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            }
        )
        result = evaluate_flame_link(chain, self.table)
        self.assertFalse(result.available)
        self.assertIn(
            "LUMINARY_MAXIMUM_LIFE_NEGATIVE",
            {reason["code"] for reason in result.reasons},
        )

    def test_zero_life_is_valid(self) -> None:
        chain = complete_chain(
            luminaryMaximumLife={
                "reviewedLife": "0",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            }
        )
        result = evaluate_flame_link(chain, self.table)
        self.assertTrue(result.available)
        self.assertEqual(result.lifeComponent, "0")

    def test_exact_arithmetic_29_and_40_digit_life(self) -> None:
        for digits in (29, 40):
            life = "1" + ("0" * (digits - 1))
            chain = complete_chain(
                luminaryMaximumLife={
                    "reviewedLife": life,
                    "provenanceKind": "manual-reviewed",
                    "reviewState": "reviewed",
                    "rawSourceText": "",
                    "recognitionSource": {"kind": "none", "digest": None},
                }
            )
            result = evaluate_flame_link(chain, self.table)
            with self.subTest(digits=digits):
                self.assertTrue(result.available)
                self.assertEqual(result.luminaryMaximumLife, life)
                self.assertEqual(
                    Decimal(result.lifeComponent or "0"),
                    Decimal(life) * Decimal("0.05"),
                )
                again = evaluate_flame_link(chain, self.table)
                self.assertEqual(result.to_dict(), again.to_dict())

    def test_manual_conditional_and_level_contributions(self) -> None:
        chain = complete_chain()
        chain["conditionalContributions"].append(
            {
                "contributionId": "manual-conditional-0001",
                "label": "Manual conditional",
                "valuePct": "12.5",
                "conditionState": "active",
                "kind": "manual",
                "provenanceKind": "manual-reviewed",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            }
        )
        chain["conditionalContributions"].append(
            {
                "contributionId": "manual-conditional-0002",
                "label": "Negative conditional",
                "valuePct": "-5",
                "conditionState": "active",
                "kind": "manual",
                "provenanceKind": "manual-reviewed",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            }
        )
        chain["flameLinkLevel"]["additionalLinkGemLevels"].append(
            {
                "contributionId": "manual-level-0001",
                "label": "Manual +1",
                "levels": 1,
                "activeState": "active",
                "provenanceKind": "manual-reviewed",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            }
        )
        chain["flameLinkLevel"]["additionalLinkGemLevels"].append(
            {
                "contributionId": "manual-level-0002",
                "label": "Manual -1",
                "levels": -1,
                "activeState": "active",
                "provenanceKind": "manual-reviewed",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            }
        )
        result = evaluate_flame_link(chain, self.table)
        self.assertTrue(result.available)
        self.assertEqual(result.conditionalContributionPct, "7.5")
        self.assertEqual(result.additionalLinkGemLevels, 0)
        self.assertEqual(result.effectiveFlameLinkLevel, 21)

    def test_runtime_table_pin_and_hardening(self) -> None:
        data = TABLE_PATH.read_bytes()
        self.assertEqual(table_sha256(data), PINNED_TABLE_SHA256)
        table = parse_flame_link_level_table_bytes(data)
        self.assertEqual(table.artifactId, EXPECTED_ARTIFACT_ID)
        self.assertEqual(len(table.rows), 40)
        for level in range(1, 41):
            self.assertIn(level, table.rows)
        broken = json.loads(data.decode("utf-8"))
        broken["artifactId"] = "wrong"
        with self.assertRaises(FlameLinkTableError):
            parse_flame_link_level_table_bytes(
                json.dumps(broken).encode("utf-8")
            )
        broken = json.loads(data.decode("utf-8"))
        broken["rows"][0]["level"] = "1"
        with self.assertRaises(FlameLinkTableError):
            parse_flame_link_level_table_bytes(
                json.dumps(broken).encode("utf-8")
            )


class CodecRepairTests(unittest.TestCase):
    def test_negative_life_rejected(self) -> None:
        document = empty_document()
        document["flameLinkPlayerChain"]["luminaryMaximumLife"] = {
            "reviewedLife": "-10",
            "provenanceKind": "manual-reviewed",
            "reviewState": "reviewed",
            "rawSourceText": "",
            "recognitionSource": {"kind": "none", "digest": None},
        }
        with self.assertRaises(BuildStateError) as raised:
            validate_document(document)
        self.assertEqual(raised.exception.code, "LUMINARY_MAXIMUM_LIFE_NEGATIVE")

    def test_recognition_source_defaults_on_decode(self) -> None:
        document = empty_document()
        chain = document["flameLinkPlayerChain"]
        for block in (
            chain["goldenGlory"],
            chain["directLinkBuffEffect"],
            chain["luminaryMaximumLife"],
        ):
            del block["recognitionSource"]
        for entry in chain["conditionalContributions"]:
            del entry["recognitionSource"]
        for entry in chain["flameLinkLevel"]["additionalLinkGemLevels"]:
            del entry["recognitionSource"]
        raw = json.dumps(document).encode("utf-8")
        # bypass serialize validation by writing raw JSON shape then decode path
        from golden_glory_lab.build_state.codec_v3 import decode

        decoded = decode(raw)
        golden = decoded.document["flameLinkPlayerChain"]["goldenGlory"]
        self.assertEqual(golden["recognitionSource"], {"kind": "none", "digest": None})

    def test_benchmark_requires_level_21(self) -> None:
        document = empty_document()
        document["flameLinkPlayerChain"]["flameLinkLevel"]["baseLevel"] = 20
        document["flameLinkPlayerChain"]["flameLinkLevel"][
            "baseLevelProvenance"
        ] = "manual-benchmark-default"
        with self.assertRaises(BuildStateError):
            validate_document(document)


class DesktopRepairTests(unittest.TestCase):
    def test_apply_light_radius_preserves_eligibility(self) -> None:
        service = ApplicationService()
        golden = dict(service.state["flameLinkPlayerChain"]["goldenGlory"])
        golden["allocatedState"] = "not-allocated"
        golden["mercenaryTargetState"] = "no"
        service.set_flame_link_input(golden_glory=golden)
        service.apply_recognized_light_radius(
            "33", raw_source_text="33% increased Light Radius"
        )
        golden = service.state["flameLinkPlayerChain"]["goldenGlory"]
        self.assertEqual(golden["allocatedState"], "not-allocated")
        self.assertEqual(golden["mercenaryTargetState"], "no")
        self.assertEqual(golden["reviewedLightRadiusPct"], "33")
        self.assertFalse(service.flame_link_result().available)

    def test_provenance_preserving_life_edit(self) -> None:
        service = ApplicationService()
        chain = service.state["flameLinkPlayerChain"]
        for entry in chain["conditionalContributions"]:
            entry["conditionState"] = "inactive"
        chain["flameLinkLevel"]["additionalLinkGemLevels"][0]["activeState"] = "inactive"
        service.set_flame_link_input(
            golden_glory={
                "allocatedState": "allocated",
                "mercenaryTargetState": "yes",
                "reviewedLightRadiusPct": "40",
                "provenanceKind": "recognized-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "40% increased Light Radius",
                "recognitionSource": {
                    "kind": "advisory-text",
                    "digest": "a" * 64,
                },
            },
            direct_link_buff_effect={
                "reviewedDirectPct": "10",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            },
            conditional_contributions=chain["conditionalContributions"],
            flame_link_level={
                "baseLevel": 21,
                "baseLevelProvenance": "imported-recognized",
                "additionalLinkGemLevels": chain["flameLinkLevel"][
                    "additionalLinkGemLevels"
                ],
            },
            luminary_maximum_life={
                "reviewedLife": "5000",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            },
        )
        before = copy.deepcopy(service.state["flameLinkPlayerChain"])
        service.set_flame_link_input(
            luminary_maximum_life={
                "reviewedLife": "6000",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            }
        )
        after = service.state["flameLinkPlayerChain"]
        self.assertEqual(after["goldenGlory"], before["goldenGlory"])
        self.assertEqual(after["directLinkBuffEffect"], before["directLinkBuffEffect"])
        self.assertEqual(
            after["flameLinkLevel"]["baseLevelProvenance"], "imported-recognized"
        )
        self.assertEqual(after["luminaryMaximumLife"]["reviewedLife"], "6000")

    def test_manual_contribution_round_trip(self) -> None:
        service = ApplicationService()
        contribution_id = service.next_manual_conditional_id()
        level_id = service.next_manual_level_id()
        chain = service.state["flameLinkPlayerChain"]
        conditionals = [dict(entry) for entry in chain["conditionalContributions"]]
        conditionals.append(
            {
                "contributionId": contribution_id,
                "label": "Manual conditional",
                "valuePct": "0",
                "conditionState": "inactive",
                "kind": "manual",
                "provenanceKind": "manual-reviewed",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            }
        )
        level = dict(chain["flameLinkLevel"])
        additions = [dict(entry) for entry in level["additionalLinkGemLevels"]]
        additions.append(
            {
                "contributionId": level_id,
                "label": "Manual levels",
                "levels": 1,
                "activeState": "inactive",
                "provenanceKind": "manual-reviewed",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            }
        )
        level["additionalLinkGemLevels"] = additions
        service.set_flame_link_input(
            conditional_contributions=conditionals, flame_link_level=level
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "build.json"
            service.save(path)
            reopened = ApplicationService()
            reopened.open(path)
            ids = {
                entry["contributionId"]
                for entry in reopened.state["flameLinkPlayerChain"][
                    "conditionalContributions"
                ]
            }
            self.assertIn(contribution_id, ids)
            level_ids = {
                entry["contributionId"]
                for entry in reopened.state["flameLinkPlayerChain"]["flameLinkLevel"][
                    "additionalLinkGemLevels"
                ]
            }
            self.assertIn(level_id, level_ids)

    def test_generic_recognition_kinds(self) -> None:
        found = recognize_player_chain_text(
            "Empowered Bond\n+2 to Level of all Link Skill Gems\nPowerful Bond"
        )
        kinds = [line.kind for line in found]
        self.assertIn("empowered-bond-level", kinds)
        self.assertIn("generic-link-gem-level", kinds)
        self.assertIn("powerful-bond-conditional", kinds)
        generic = next(line for line in found if line.kind == "generic-link-gem-level")
        self.assertEqual(generic.signedValueLexeme, "2")


if __name__ == "__main__":
    unittest.main()
