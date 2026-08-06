from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golden_glory_lab.desktop.service import ApplicationService  # noqa: E402
from golden_glory_lab.domain import FLAME_LINK_OUTPUT_LABEL  # noqa: E402


class DesktopBuild003ServiceTests(unittest.TestCase):
    def test_new_document_includes_flame_link_defaults(self) -> None:
        service = ApplicationService()
        self.assertEqual(service.state["schemaVersion"], "3.0.0")
        chain = service.state["flameLinkPlayerChain"]
        self.assertEqual(chain["flameLinkLevel"]["baseLevel"], 21)
        self.assertEqual(
            chain["conditionalContributions"][0]["contributionId"], "powerful-bond"
        )
        self.assertEqual(
            chain["flameLinkLevel"]["additionalLinkGemLevels"][0]["contributionId"],
            "empowered-bond",
        )
        self.assertEqual(service.flame_link_table_status()["state"], "available")
        result = service.flame_link_result()
        self.assertFalse(result.available)
        self.assertEqual(result.label, FLAME_LINK_OUTPUT_LABEL)

    def test_manual_flame_link_round_trip_and_enmity_isolation(self) -> None:
        service = ApplicationService()
        chain = service.state["flameLinkPlayerChain"]
        for entry in chain["conditionalContributions"]:
            entry["conditionState"] = "inactive"
        chain["flameLinkLevel"]["additionalLinkGemLevels"][0]["activeState"] = "active"
        service.set_flame_link_input(
            golden_glory={
                "allocatedState": "allocated",
                "mercenaryTargetState": "yes",
                "reviewedLightRadiusPct": "40",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "40% increased Light Radius",
            },
            direct_link_buff_effect={
                "reviewedDirectPct": "0",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "",
            },
            conditional_contributions=chain["conditionalContributions"],
            flame_link_level=chain["flameLinkLevel"],
            luminary_maximum_life={
                "reviewedLife": "5000",
                "provenanceKind": "manual-reviewed",
                "reviewState": "reviewed",
                "rawSourceText": "",
            },
        )
        flame = service.flame_link_result()
        self.assertTrue(flame.available)
        self.assertEqual(flame.effectiveFlameLinkLevel, 23)
        self.assertEqual(service.enmity_result().state, "unavailable")

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "build.json"
            saved = service.save(path)
            reopened = ApplicationService()
            reopened.open(path)
            self.assertEqual(reopened.save(), saved)
            self.assertEqual(
                reopened.flame_link_result().to_dict(),
                flame.to_dict(),
            )
            self.assertEqual(
                reopened.state["enmityManualInput"]["equippedState"],
                "unknown",
            )

    def test_recognition_helpers_are_advisory_until_applied(self) -> None:
        service = ApplicationService()
        before = service.state["flameLinkPlayerChain"]["goldenGlory"][
            "reviewedLightRadiusPct"
        ]
        found = service.recognize_player_chain_from_text(
            "25% increased Light Radius\nPowerful Bond"
        )
        kinds = {line.kind for line in found}
        self.assertIn("light-radius", kinds)
        self.assertIn("powerful-bond-conditional", kinds)
        self.assertNotIn("empowered-bond-level", kinds)
        self.assertIsNone(
            service.state["flameLinkPlayerChain"]["goldenGlory"]["reviewedLightRadiusPct"]
        )
        self.assertEqual(
            service.state["flameLinkPlayerChain"]["goldenGlory"][
                "reviewedLightRadiusPct"
            ],
            before,
        )
        light = next(line for line in found if line.kind == "light-radius")
        service.apply_recognized_light_radius(
            light.signedValueLexeme or "0",
            raw_source_text=light.sourceLine,
        )
        self.assertEqual(
            service.state["flameLinkPlayerChain"]["goldenGlory"][
                "reviewedLightRadiusPct"
            ],
            "25",
        )
        self.assertEqual(
            service.state["flameLinkPlayerChain"]["goldenGlory"]["provenanceKind"],
            "recognized-reviewed",
        )

    def test_status_summary_includes_flame_link(self) -> None:
        status = ApplicationService().status_summary()
        self.assertIn("flameLinkOutput", status)
        self.assertIn("flameLinkTable", status)
        self.assertEqual(status["flameLinkTable"], "available")


if __name__ == "__main__":
    unittest.main()
