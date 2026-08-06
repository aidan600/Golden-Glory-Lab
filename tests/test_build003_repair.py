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
        from golden_glory_lab.build_state.codec_v3 import decode

        decoded = decode(raw)
        self.assertTrue(decoded.migrated)
        golden = decoded.document["flameLinkPlayerChain"]["goldenGlory"]
        self.assertEqual(golden["recognitionSource"], {"kind": "none", "digest": None})

    def test_malformed_recognition_source_rejected(self) -> None:
        document = empty_document()
        document["flameLinkPlayerChain"]["goldenGlory"]["recognitionSource"] = "bad"
        raw = json.dumps(document).encode("utf-8")
        from golden_glory_lab.build_state.codec_v3 import decode

        with self.assertRaises(BuildStateError):
            decode(raw)

    def test_benchmark_requires_level_21(self) -> None:
        document = empty_document()
        document["flameLinkPlayerChain"]["flameLinkLevel"]["baseLevel"] = 20
        document["flameLinkPlayerChain"]["flameLinkLevel"][
            "baseLevelProvenance"
        ] = "manual-benchmark-default"
        with self.assertRaises(BuildStateError):
            validate_document(document)

    def test_unreviewed_additional_level_rejected_by_codec(self) -> None:
        document = empty_document()
        document["flameLinkPlayerChain"]["flameLinkLevel"]["additionalLinkGemLevels"].append(
            {
                "contributionId": "manual-level-0001",
                "label": "Unreviewed levels",
                "levels": 1,
                "activeState": "inactive",
                "provenanceKind": "unreviewed",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            }
        )
        with self.assertRaises(BuildStateError) as raised:
            validate_document(document)
        self.assertIn(
            raised.exception.code,
            {"FLAME_LINK_PROVENANCE", "FLAME_LINK_PROVENANCE_INVARIANT"},
        )


class FlameLinkArithmeticRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.table = load_flame_link_level_table()

    def test_conditional_cancellation_to_nine(self) -> None:
        chain = complete_chain()
        for entry in chain["conditionalContributions"]:
            entry["conditionState"] = "inactive"
        plus = "1" + ("0" * 126) + "9"  # 10^127 + 9
        minus = "-" + "1" + ("0" * 127)  # -(10^127)
        self.assertEqual(len(plus), 128)
        self.assertEqual(len(minus) - 1, 128)
        chain["conditionalContributions"].extend(
            [
                {
                    "contributionId": "manual-conditional-0001",
                    "label": "Plus",
                    "valuePct": plus,
                    "conditionState": "active",
                    "kind": "manual",
                    "provenanceKind": "manual-reviewed",
                    "rawSourceText": "",
                    "recognitionSource": {"kind": "none", "digest": None},
                },
                {
                    "contributionId": "manual-conditional-0002",
                    "label": "Minus",
                    "valuePct": minus,
                    "conditionState": "active",
                    "kind": "manual",
                    "provenanceKind": "manual-reviewed",
                    "rawSourceText": "",
                    "recognitionSource": {"kind": "none", "digest": None},
                },
            ]
        )
        result = evaluate_flame_link(chain, self.table)
        self.assertTrue(result.available)
        self.assertEqual(result.conditionalContributionPct, "9")

    def test_precision_independence_across_ambient_contexts(self) -> None:
        from decimal import getcontext, localcontext

        chain = complete_chain()
        for entry in chain["conditionalContributions"]:
            entry["conditionState"] = "inactive"
        chain["conditionalContributions"].append(
            {
                "contributionId": "manual-conditional-0001",
                "label": "Wide",
                "valuePct": "1" + ("0" * 40),
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
                "label": "Cancel",
                "valuePct": "-" + ("1" + ("0" * 40)),
                "conditionState": "active",
                "kind": "manual",
                "provenanceKind": "manual-reviewed",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            }
        )
        outcomes = []
        for precision in (6, 28, 200):
            with localcontext(getcontext().copy()) as ctx:
                ctx.prec = precision
                result = evaluate_flame_link(chain, self.table)
                outcomes.append(
                    (
                        result.available,
                        result.conditionalContributionPct,
                        result.modelledIntegerMin,
                        result.modelledIntegerMax,
                    )
                )
        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual(outcomes[1], outcomes[2])
        self.assertTrue(outcomes[0][0])
        self.assertEqual(outcomes[0][1], "0")

    def test_128_digit_life_exact(self) -> None:
        life = "1" + ("0" * 127)
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
        self.assertTrue(result.available)
        self.assertEqual(
            Decimal(result.lifeComponent or "0"),
            Decimal(life) * Decimal("0.05"),
        )

    def test_active_unreviewed_level_blocks(self) -> None:
        chain = complete_chain()
        chain["flameLinkLevel"]["additionalLinkGemLevels"].append(
            {
                "contributionId": "manual-level-unreviewed",
                "label": "Should not count",
                "levels": 3,
                "activeState": "active",
                "provenanceKind": "unreviewed",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            }
        )
        result = evaluate_flame_link(chain, self.table)
        self.assertFalse(result.available)
        self.assertIn(
            "ADDITIONAL_LINK_LEVEL_UNREVIEWED",
            {reason["code"] for reason in result.reasons},
        )

    def test_unknown_table_field_rejected(self) -> None:
        data = json.loads(TABLE_PATH.read_text(encoding="utf-8"))
        data["extraRoot"] = True
        with self.assertRaises(FlameLinkTableError) as raised:
            parse_flame_link_level_table_bytes(json.dumps(data).encode("utf-8"))
        self.assertEqual(raised.exception.code, "FLAME_LINK_TABLE_UNKNOWN_FIELD")
        data = json.loads(TABLE_PATH.read_text(encoding="utf-8"))
        data["tableBounds"]["extra"] = 1
        with self.assertRaises(FlameLinkTableError) as raised:
            parse_flame_link_level_table_bytes(json.dumps(data).encode("utf-8"))
        self.assertEqual(raised.exception.code, "FLAME_LINK_TABLE_UNKNOWN_FIELD")
        data = json.loads(TABLE_PATH.read_text(encoding="utf-8"))
        data["rows"][0]["extra"] = 1
        with self.assertRaises(FlameLinkTableError) as raised:
            parse_flame_link_level_table_bytes(json.dumps(data).encode("utf-8"))
        self.assertEqual(raised.exception.code, "FLAME_LINK_TABLE_UNKNOWN_FIELD")
        data = json.loads(TABLE_PATH.read_text(encoding="utf-8"))
        data["provenance"]["extra"] = "x"
        with self.assertRaises(FlameLinkTableError) as raised:
            parse_flame_link_level_table_bytes(json.dumps(data).encode("utf-8"))
        self.assertEqual(raised.exception.code, "FLAME_LINK_TABLE_UNKNOWN_FIELD")


class RecognitionSignRepairTests(unittest.TestCase):
    def test_reduced_uses_copy_negate(self) -> None:
        from decimal import getcontext, localcontext

        text = "12% reduced Light Radius"
        with localcontext(getcontext().copy()) as ctx:
            ctx.prec = 1
            found = recognize_player_chain_text(text)
        self.assertEqual(found[0].signedValueLexeme, "-12")


class DesktopPoBDemotionRepairTests(unittest.TestCase):
    def _import_once(self, service: ApplicationService) -> str:
        fixture = ROOT / "fixtures" / "pob" / "proof" / "equivalent.share.txt"
        return service.attempt_share_code(fixture.read_text(encoding="utf-8"))

    def test_pob_replace_demotion_matrix(self) -> None:
        service = ApplicationService()
        outcome = self._import_once(service)
        if outcome == "confirmation-required":
            service.confirm_pending_import(True)
        else:
            self.assertEqual(outcome, "imported")
        digest = "a" * 64
        pob = {"kind": "pob-import", "digest": digest}
        chain = service.state["flameLinkPlayerChain"]
        for entry in chain["conditionalContributions"]:
            if entry["contributionId"] == "powerful-bond":
                entry.update(
                    {
                        "conditionState": "active",
                        "provenanceKind": "recognized-reviewed",
                        "rawSourceText": "Powerful Bond",
                        "recognitionSource": pob,
                    }
                )
            else:
                entry["conditionState"] = "inactive"
        chain["conditionalContributions"].append(
            {
                "contributionId": "manual-conditional-pob",
                "label": "PoB manual conditional",
                "valuePct": "5",
                "conditionState": "active",
                "kind": "manual",
                "provenanceKind": "recognized-reviewed",
                "rawSourceText": "5% increased Effect of Link Skills",
                "recognitionSource": pob,
            }
        )
        chain["conditionalContributions"].append(
            {
                "contributionId": "manual-conditional-keep",
                "label": "Manual keep",
                "valuePct": "3",
                "conditionState": "inactive",
                "kind": "manual",
                "provenanceKind": "manual-reviewed",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            }
        )
        chain["flameLinkLevel"]["additionalLinkGemLevels"][0].update(
            {
                "activeState": "active",
                "provenanceKind": "recognized-reviewed",
                "rawSourceText": "Empowered Bond",
                "recognitionSource": pob,
            }
        )
        chain["flameLinkLevel"]["additionalLinkGemLevels"].append(
            {
                "contributionId": "manual-level-pob",
                "label": "PoB levels",
                "levels": 1,
                "activeState": "active",
                "provenanceKind": "recognized-reviewed",
                "rawSourceText": "+1 to Level of all Link Skill Gems",
                "recognitionSource": pob,
            }
        )
        chain["flameLinkLevel"]["baseLevel"] = 25
        chain["flameLinkLevel"]["baseLevelProvenance"] = "imported-recognized"
        service.set_flame_link_input(
            golden_glory={
                "allocatedState": "allocated",
                "mercenaryTargetState": "yes",
                "reviewedLightRadiusPct": "40",
                "provenanceKind": "recognized-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "40% increased Light Radius",
                "recognitionSource": pob,
            },
            direct_link_buff_effect={
                "reviewedDirectPct": "10",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            },
            conditional_contributions=chain["conditionalContributions"],
            flame_link_level=chain["flameLinkLevel"],
            luminary_maximum_life={
                "reviewedLife": "5000",
                "provenanceKind": "recognized-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "5000 Life",
                "recognitionSource": pob,
            },
        )
        self.assertEqual(self._import_once(service), "confirmation-required")
        self.assertEqual(
            service.confirm_pending_import(True, clear_observed_reference=True),
            "replaced",
        )
        after = service.state["flameLinkPlayerChain"]
        self.assertEqual(after["goldenGlory"]["provenanceKind"], "unreviewed")
        self.assertIsNone(after["goldenGlory"]["reviewedLightRadiusPct"])
        self.assertEqual(after["directLinkBuffEffect"]["provenanceKind"], "manual-reviewed")
        self.assertEqual(after["directLinkBuffEffect"]["reviewedDirectPct"], "10")
        self.assertEqual(after["luminaryMaximumLife"]["provenanceKind"], "unreviewed")
        self.assertIsNone(after["luminaryMaximumLife"]["reviewedLife"])
        self.assertEqual(after["flameLinkLevel"]["baseLevel"], 21)
        self.assertEqual(
            after["flameLinkLevel"]["baseLevelProvenance"], "manual-benchmark-default"
        )
        conditional_ids = {
            entry["contributionId"] for entry in after["conditionalContributions"]
        }
        self.assertIn("powerful-bond", conditional_ids)
        self.assertIn("inspiring-bond", conditional_ids)
        self.assertIn("manual-conditional-keep", conditional_ids)
        self.assertNotIn("manual-conditional-pob", conditional_ids)
        powerful = next(
            entry
            for entry in after["conditionalContributions"]
            if entry["contributionId"] == "powerful-bond"
        )
        self.assertEqual(powerful["provenanceKind"], "catalog-default")
        self.assertEqual(powerful["conditionState"], "unknown")
        self.assertEqual(powerful["recognitionSource"]["kind"], "none")
        level_ids = {
            entry["contributionId"]
            for entry in after["flameLinkLevel"]["additionalLinkGemLevels"]
        }
        self.assertIn("empowered-bond", level_ids)
        self.assertNotIn("manual-level-pob", level_ids)
        empowered = next(
            entry
            for entry in after["flameLinkLevel"]["additionalLinkGemLevels"]
            if entry["contributionId"] == "empowered-bond"
        )
        self.assertEqual(empowered["provenanceKind"], "catalog-default")
        self.assertEqual(empowered["activeState"], "unknown")
        self.assertEqual(empowered["levels"], 2)

    def test_apply_recognized_level_defaults_unknown(self) -> None:
        service = ApplicationService()
        service.apply_recognized_empowered_bond_level(
            raw_source_text="Empowered Bond"
        )
        empowered = next(
            entry
            for entry in service.state["flameLinkPlayerChain"]["flameLinkLevel"][
                "additionalLinkGemLevels"
            ]
            if entry["contributionId"] == "empowered-bond"
        )
        self.assertEqual(empowered["activeState"], "unknown")
        self.assertEqual(empowered["provenanceKind"], "recognized-reviewed")
        service.apply_recognized_generic_link_gem_level(
            1, raw_source_text="+1 to Level of all Link Skill Gems"
        )
        generic = service.state["flameLinkPlayerChain"]["flameLinkLevel"][
            "additionalLinkGemLevels"
        ][-1]
        self.assertEqual(generic["activeState"], "unknown")

    def test_draft_v3_injection_marks_upgrade_pending(self) -> None:
        service = ApplicationService()
        document = empty_document()
        chain = document["flameLinkPlayerChain"]
        del chain["goldenGlory"]["recognitionSource"]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "draft.json"
            path.write_bytes(json.dumps(document).encode("utf-8"))
            service.open(path)
        self.assertTrue(service.migration_pending)
        self.assertEqual(service.file_state, "upgrade-pending")


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
