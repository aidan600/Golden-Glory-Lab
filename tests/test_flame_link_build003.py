from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golden_glory_lab.build_state import empty_flame_link_player_chain  # noqa: E402
from golden_glory_lab.domain import (  # noqa: E402
    FLAME_LINK_OUTPUT_LABEL,
    evaluate_flame_link,
    load_flame_link_level_table,
    recognize_player_chain_text,
    round_half_up,
)


def complete_chain(**overrides: object) -> dict:
    chain = empty_flame_link_player_chain()
    chain["goldenGlory"] = {
        "allocatedState": "not-allocated",
        "mercenaryTargetState": "yes",
        "reviewedLightRadiusPct": "0",
        "provenanceKind": "manual-reviewed",
        "reviewState": "reviewed",
        "rawSourceText": "",
        "recognitionSource": {"kind": "none", "digest": None},
    }
    chain["directLinkBuffEffect"] = {
        "reviewedDirectPct": "0",
        "provenanceKind": "manual-reviewed",
        "reviewState": "reviewed",
        "rawSourceText": "",
        "recognitionSource": {"kind": "none", "digest": None},
    }
    for entry in chain["conditionalContributions"]:
        entry["conditionState"] = "inactive"
    chain["flameLinkLevel"]["additionalLinkGemLevels"][0]["activeState"] = "inactive"
    chain["luminaryMaximumLife"] = {
        "reviewedLife": "5000",
        "provenanceKind": "manual-reviewed",
        "reviewState": "reviewed",
        "rawSourceText": "",
        "recognitionSource": {"kind": "none", "digest": None},
    }
    for key, value in overrides.items():
        if key == "goldenGlory" and isinstance(value, dict):
            chain["goldenGlory"].update(value)
        elif key == "directLinkBuffEffect" and isinstance(value, dict):
            chain["directLinkBuffEffect"].update(value)
        elif key == "luminaryMaximumLife" and isinstance(value, dict):
            chain["luminaryMaximumLife"].update(value)
        elif key == "flameLinkLevel" and isinstance(value, dict):
            chain["flameLinkLevel"].update(value)
        else:
            chain[key] = value
    return chain


class FlameLinkCalculationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.table = load_flame_link_level_table()

    def test_level_table_anchors(self) -> None:
        self.assertEqual(self.table.row_for(1).flatMin, Decimal(23))
        self.assertEqual(self.table.row_for(1).flatMax, Decimal(35))
        self.assertEqual(self.table.row_for(20).flatMin, Decimal(169))
        self.assertEqual(self.table.row_for(20).flatMax, Decimal(254))

    def test_benchmark_level_21_without_empowered(self) -> None:
        result = evaluate_flame_link(complete_chain(), self.table)
        self.assertTrue(result.available)
        self.assertEqual(result.label, FLAME_LINK_OUTPUT_LABEL)
        self.assertNotIn("DPS", result.label)
        self.assertEqual(result.baseFlameLinkLevel, 21)
        self.assertEqual(result.additionalLinkGemLevels, 0)
        self.assertEqual(result.effectiveFlameLinkLevel, 21)
        self.assertEqual(result.lifeComponent, "250")
        self.assertEqual(result.unscaledMin, "437")
        self.assertEqual(result.unscaledMax, "531")
        self.assertEqual(result.modelledIntegerMin, 437)
        self.assertEqual(result.modelledIntegerMax, 531)
        self.assertEqual(
            complete_chain()["flameLinkLevel"]["baseLevelProvenance"],
            "manual-benchmark-default",
        )

    def test_empowered_bond_raises_effective_level_to_23(self) -> None:
        chain = complete_chain()
        chain["flameLinkLevel"]["additionalLinkGemLevels"][0]["activeState"] = "active"
        result = evaluate_flame_link(chain, self.table)
        self.assertTrue(result.available)
        self.assertEqual(result.effectiveFlameLinkLevel, 23)
        self.assertEqual(result.levelFlatMin, "229")
        self.assertEqual(result.levelFlatMax, "343")
        self.assertEqual(result.unscaledMin, "479")
        self.assertEqual(result.unscaledMax, "593")

    def test_life_component_is_five_percent(self) -> None:
        chain = complete_chain(
            luminaryMaximumLife={
                "reviewedLife": "1234",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "",
            }
        )
        result = evaluate_flame_link(chain, self.table)
        self.assertEqual(result.lifeComponent, "61.7")

    def test_gg_and_direct_are_additive_not_multiplied(self) -> None:
        chain = complete_chain(
            goldenGlory={
                "allocatedState": "allocated",
                "mercenaryTargetState": "yes",
                "reviewedLightRadiusPct": "40",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "",
            },
            directLinkBuffEffect={
                "reviewedDirectPct": "10",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "",
            },
        )
        result = evaluate_flame_link(chain, self.table)
        self.assertTrue(result.available)
        self.assertEqual(result.goldenGloryContributionPct, "40")
        self.assertEqual(result.directLinkContributionPct, "10")
        self.assertEqual(result.netLinkSkillBuffEffectPct, "50")
        self.assertEqual(result.linkEffectMultiplier, "1.5")
        # 437 * 1.5 = 655.5 -> 656; 531 * 1.5 = 796.5 -> 797
        self.assertEqual(result.exactPreRoundMin, "655.5")
        self.assertEqual(result.exactPreRoundMax, "796.5")
        self.assertEqual(result.modelledIntegerMin, 656)
        self.assertEqual(result.modelledIntegerMax, 797)

    def test_active_conditional_adds_inactive_does_not(self) -> None:
        chain = complete_chain()
        for entry in chain["conditionalContributions"]:
            if entry["contributionId"] == "powerful-bond":
                entry["conditionState"] = "active"
            else:
                entry["conditionState"] = "inactive"
        result = evaluate_flame_link(chain, self.table)
        self.assertTrue(result.available)
        self.assertEqual(result.conditionalContributionPct, "20")
        self.assertEqual(result.linkEffectMultiplier, "1.2")

    def test_unknown_conditional_blocks(self) -> None:
        chain = complete_chain()
        # defaults already unknown for conditionals in empty, but complete_chain
        # sets inactive; restore unknown for one catalog entry
        chain["conditionalContributions"][0]["conditionState"] = "unknown"
        result = evaluate_flame_link(chain, self.table)
        self.assertFalse(result.available)
        self.assertEqual(result.state, "unavailable")
        self.assertIn(
            "CONDITIONAL_CONTRIBUTION_UNKNOWN",
            {reason["code"] for reason in result.reasons},
        )

    def test_unknown_additional_level_blocks(self) -> None:
        chain = complete_chain()
        chain["flameLinkLevel"]["additionalLinkGemLevels"][0]["activeState"] = "unknown"
        result = evaluate_flame_link(chain, self.table)
        self.assertFalse(result.available)
        self.assertIn(
            "ADDITIONAL_LINK_LEVEL_UNKNOWN",
            {reason["code"] for reason in result.reasons},
        )

    def test_negative_light_radius_and_direct(self) -> None:
        chain = complete_chain(
            goldenGlory={
                "allocatedState": "allocated",
                "mercenaryTargetState": "yes",
                "reviewedLightRadiusPct": "-10",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "",
            },
            directLinkBuffEffect={
                "reviewedDirectPct": "-5",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "",
            },
        )
        result = evaluate_flame_link(chain, self.table)
        self.assertTrue(result.available)
        self.assertEqual(result.netLinkSkillBuffEffectPct, "-15")
        self.assertEqual(result.linkEffectMultiplier, "0.85")

    def test_gg_eligibility_not_allocated_is_zero(self) -> None:
        chain = complete_chain(
            goldenGlory={
                "allocatedState": "not-allocated",
                "mercenaryTargetState": "yes",
                "reviewedLightRadiusPct": "99",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "",
            }
        )
        result = evaluate_flame_link(chain, self.table)
        self.assertTrue(result.available)
        self.assertEqual(result.goldenGloryContributionPct, "0")

    def test_gg_eligibility_unknown_blocks(self) -> None:
        chain = complete_chain(
            goldenGlory={
                "allocatedState": "unknown",
                "mercenaryTargetState": "yes",
                "reviewedLightRadiusPct": "40",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "",
            }
        )
        result = evaluate_flame_link(chain, self.table)
        self.assertFalse(result.available)
        self.assertIn(
            "GOLDEN_GLORY_ELIGIBILITY_UNKNOWN",
            {reason["code"] for reason in result.reasons},
        )

    def test_unsupported_effective_level(self) -> None:
        chain = complete_chain(
            flameLinkLevel={
                "baseLevel": 40,
                "baseLevelProvenance": "manual-reviewed",
                "additionalLinkGemLevels": [
                    {
                        "contributionId": "empowered-bond",
                        "label": "Empowered Bond",
                        "levels": 2,
                        "activeState": "active",
                        "provenanceKind": "catalog-default",
                        "rawSourceText": "",
                    }
                ],
            }
        )
        result = evaluate_flame_link(chain, self.table)
        self.assertEqual(result.state, "unsupported-effective-level")
        self.assertFalse(result.available)
        self.assertEqual(result.effectiveFlameLinkLevel, 42)

    def test_unsupported_effect_multiplier(self) -> None:
        chain = complete_chain(
            directLinkBuffEffect={
                "reviewedDirectPct": "-100",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            }
        )
        result = evaluate_flame_link(chain, self.table)
        self.assertTrue(result.available)
        self.assertEqual(result.state, "available")
        self.assertEqual(result.linkEffectMultiplier, "0")
        self.assertEqual(result.modelledIntegerMin, 0)
        self.assertEqual(result.modelledIntegerMax, 0)
        self.assertEqual(result.exactPreRoundMin, "0")
        self.assertEqual(result.exactPreRoundMax, "0")

    def test_negative_effect_multiplier_unavailable(self) -> None:
        chain = complete_chain(
            directLinkBuffEffect={
                "reviewedDirectPct": "-150",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "",
                "recognitionSource": {"kind": "none", "digest": None},
            }
        )
        result = evaluate_flame_link(chain, self.table)
        self.assertEqual(result.state, "unsupported-effect-multiplier")
        self.assertFalse(result.available)

    def test_half_up_tie_and_helper(self) -> None:
        self.assertEqual(round_half_up(Decimal("655.5")), 656)
        self.assertEqual(round_half_up(Decimal("0.5")), 1)
        self.assertEqual(round_half_up(Decimal("1.4")), 1)

    def test_boundary_levels_1_and_40(self) -> None:
        for level in (1, 40):
            chain = complete_chain(
                flameLinkLevel={
                    "baseLevel": level,
                    "baseLevelProvenance": "manual-reviewed",
                    "additionalLinkGemLevels": [
                        {
                            "contributionId": "empowered-bond",
                            "label": "Empowered Bond",
                            "levels": 2,
                            "activeState": "inactive",
                            "provenanceKind": "catalog-default",
                            "rawSourceText": "",
                        }
                    ],
                }
            )
            result = evaluate_flame_link(chain, self.table)
            with self.subTest(level=level):
                self.assertTrue(result.available)
                self.assertEqual(result.effectiveFlameLinkLevel, level)

    def test_quality_not_an_input(self) -> None:
        encoded = evaluate_flame_link(complete_chain(), self.table).to_dict()
        self.assertNotIn("quality", encoded)
        self.assertNotIn("dps", str(encoded).lower())


class PlayerChainRecognitionTests(unittest.TestCase):
    def test_light_radius_increased_and_reduced(self) -> None:
        increased = recognize_player_chain_text("40% increased Light Radius")
        reduced = recognize_player_chain_text("15% reduced Light Radius")
        self.assertEqual(increased[0].kind, "light-radius")
        self.assertEqual(increased[0].signedValueLexeme, "40")
        self.assertEqual(reduced[0].signedValueLexeme, "-15")

    def test_direct_link_buff_effect_patterns(self) -> None:
        lines = (
            "12% increased Effect of your Link Skills",
            "8% increased Buff Effect of Link Skills",
            "5% increased Effect of Link Skills",
        )
        for line in lines:
            found = recognize_player_chain_text(line)
            with self.subTest(line=line):
                self.assertEqual(found[0].kind, "direct-link-buff-effect")

    def test_powerful_bond_is_not_plus_two_levels(self) -> None:
        found = recognize_player_chain_text("Powerful Bond")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].kind, "powerful-bond-conditional")
        self.assertEqual(found[0].signedValueLexeme, "20")
        self.assertNotEqual(found[0].kind, "empowered-bond-level")
        self.assertIn(
            "conditional-buff-effect-not-additional-gem-levels",
            found[0].notes,
        )

    def test_empowered_bond_level_candidate(self) -> None:
        found = recognize_player_chain_text("Empowered Bond")
        self.assertEqual(found[0].kind, "empowered-bond-level")
        self.assertEqual(found[0].signedValueLexeme, "2")

    def test_generic_link_gem_level_preserves_signed_value(self) -> None:
        plus_one = recognize_player_chain_text("+1 to Level of all Link Skill Gems")
        plus_three = recognize_player_chain_text("+3 to Level of all Link Skill Gems")
        self.assertEqual(plus_one[0].kind, "generic-link-gem-level")
        self.assertEqual(plus_one[0].signedValueLexeme, "1")
        self.assertEqual(plus_three[0].signedValueLexeme, "3")
        self.assertNotEqual(plus_one[0].kind, "empowered-bond-level")

    def test_does_not_infer_ownership(self) -> None:
        found = recognize_player_chain_text("40% increased Light Radius")
        joined = " ".join(found[0].notes)
        self.assertIn("does-not-infer-ownership-or-target", joined)


if __name__ == "__main__":
    unittest.main()
