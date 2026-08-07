from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golden_glory_lab.domain import (  # noqa: E402
    FIXED_LIGHT_RADIUS_SLOTS,
    INITIAL_JEWEL_COUNT,
    LightRadiusBreakdown,
    ManualCalculatorInput,
    enmity_overcap_contribution,
    evaluate_manual_calculator,
    load_flame_link_level_table,
)


def manual_input(**overrides: object) -> ManualCalculatorInput:
    values = {
        "maximum_life": "5000",
        "increased_light_radius_pct": "40",
        "other_link_skill_buff_effect_pct": "0",
        "flame_link_level": "23",
        "golden_glory_allocated": True,
        "powerful_bond_active": False,
        "inspiring_bond_active": False,
        "total_fire_resistance_on_gear": "300",
        "luminary_aura_fire_resistance": "100",
        "enmity_reduced_fire_resistance": "20",
        "maximum_fire_resistance": "85",
        "enmity_equipped": True,
    }
    values.update(overrides)
    return ManualCalculatorInput(**values)  # type: ignore[arg-type]


class ManualCalculatorDomainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.table = load_flame_link_level_table()

    def test_known_flame_link_vector(self) -> None:
        result = evaluate_manual_calculator(manual_input(), level_table=self.table)
        self.assertIsNone(result.flame_link_error)
        self.assertEqual(result.net_link_skill_buff_effect_pct, "40")
        self.assertEqual(result.link_effect_multiplier, "1.40")
        self.assertEqual(result.flame_link_min, 671)
        self.assertEqual(result.flame_link_max, 830)

    def test_high_life_vector(self) -> None:
        result = evaluate_manual_calculator(
            manual_input(
                maximum_life="8432",
                increased_light_radius_pct="120",
                other_link_skill_buff_effect_pct="40",
            ),
            level_table=self.table,
        )
        self.assertIsNone(result.flame_link_error)
        self.assertEqual(result.net_link_skill_buff_effect_pct, "160")
        self.assertEqual(result.link_effect_multiplier, "2.60")
        self.assertEqual(result.flame_link_min, 1692)
        self.assertEqual(result.flame_link_max, 1988)

    def test_enmity_gear_aura_reduction_hits_cap(self) -> None:
        result = evaluate_manual_calculator(manual_input(), level_table=self.table)
        self.assertEqual(result.pre_enmity_fire_resistance, "400")
        self.assertEqual(result.final_uncapped_fire_resistance, "320")
        self.assertEqual(result.overcapped_fire_resistance, "235")
        self.assertEqual(result.enmity_penetration, 200)
        self.assertIsNone(result.enmity_error)
        overcap, contribution = enmity_overcap_contribution(320, 85)
        self.assertEqual(overcap, 235)
        self.assertEqual(contribution, 200)

    def test_enmity_moderate_overcap(self) -> None:
        result = evaluate_manual_calculator(
            manual_input(
                total_fire_resistance_on_gear="100",
                luminary_aura_fire_resistance="50",
                enmity_reduced_fire_resistance="20",
                maximum_fire_resistance="75",
            ),
            level_table=self.table,
        )
        self.assertEqual(result.pre_enmity_fire_resistance, "150")
        self.assertEqual(result.final_uncapped_fire_resistance, "120")
        self.assertEqual(result.enmity_penetration, 45)
        self.assertIsNone(result.enmity_error)

    def test_enmity_blank_aura_treated_as_zero(self) -> None:
        result = evaluate_manual_calculator(
            manual_input(
                total_fire_resistance_on_gear="100",
                luminary_aura_fire_resistance="",
                enmity_reduced_fire_resistance="20",
                maximum_fire_resistance="75",
            ),
            level_table=self.table,
        )
        self.assertEqual(result.pre_enmity_fire_resistance, "100")
        self.assertEqual(result.final_uncapped_fire_resistance, "80")
        self.assertEqual(result.enmity_penetration, 5)
        self.assertIsNone(result.enmity_error)

    def test_blank_other_link_buff_effect_treated_as_zero(self) -> None:
        blanked = evaluate_manual_calculator(
            manual_input(other_link_skill_buff_effect_pct=""),
            level_table=self.table,
        )
        explicit = evaluate_manual_calculator(
            manual_input(other_link_skill_buff_effect_pct="0"),
            level_table=self.table,
        )
        self.assertIsNone(blanked.flame_link_error)
        self.assertEqual(blanked.net_link_skill_buff_effect_pct, explicit.net_link_skill_buff_effect_pct)
        self.assertEqual(blanked.link_effect_multiplier, explicit.link_effect_multiplier)
        self.assertEqual(blanked.flame_link_min, explicit.flame_link_min)
        self.assertEqual(blanked.flame_link_max, explicit.flame_link_max)
        self.assertEqual(blanked.net_link_skill_buff_effect_pct, "40")
        self.assertEqual(blanked.link_effect_multiplier, "1.40")
        self.assertEqual(blanked.flame_link_min, 671)
        self.assertEqual(blanked.flame_link_max, 830)

    def test_enmity_truncates_fractional_final_uncapped_like_pob(self) -> None:
        """633 * 0.39 = 246.87 truncates to 246 before the overcap subtraction."""

        result = evaluate_manual_calculator(
            manual_input(
                total_fire_resistance_on_gear="633",
                luminary_aura_fire_resistance="0",
                enmity_reduced_fire_resistance="61",
                maximum_fire_resistance="76",
            ),
            level_table=self.table,
        )
        self.assertEqual(result.pre_enmity_fire_resistance, "633")
        self.assertEqual(result.final_uncapped_fire_resistance, "246")
        self.assertEqual(result.overcapped_fire_resistance, "170")
        self.assertEqual(result.enmity_penetration, 170)
        self.assertIsNone(result.enmity_error)

    def test_bond_toggles_each_add_exactly_20(self) -> None:
        base = evaluate_manual_calculator(manual_input(), level_table=self.table)
        powerful = evaluate_manual_calculator(
            manual_input(powerful_bond_active=True), level_table=self.table
        )
        inspiring = evaluate_manual_calculator(
            manual_input(inspiring_bond_active=True), level_table=self.table
        )
        both = evaluate_manual_calculator(
            manual_input(powerful_bond_active=True, inspiring_bond_active=True),
            level_table=self.table,
        )
        self.assertEqual(base.net_link_skill_buff_effect_pct, "40")
        self.assertEqual(powerful.net_link_skill_buff_effect_pct, "60")
        self.assertEqual(inspiring.net_link_skill_buff_effect_pct, "60")
        self.assertEqual(both.net_link_skill_buff_effect_pct, "80")

    def test_golden_glory_off_excludes_light_radius(self) -> None:
        result = evaluate_manual_calculator(
            manual_input(golden_glory_allocated=False),
            level_table=self.table,
        )
        self.assertEqual(result.net_link_skill_buff_effect_pct, "0")
        self.assertEqual(result.link_effect_multiplier, "1.00")

    def test_zero_multiplier_remains_0_0(self) -> None:
        result = evaluate_manual_calculator(
            manual_input(
                increased_light_radius_pct="0",
                other_link_skill_buff_effect_pct="-100",
                golden_glory_allocated=False,
            ),
            level_table=self.table,
        )
        self.assertIsNone(result.flame_link_error)
        self.assertEqual(result.link_effect_multiplier, "0.00")
        self.assertEqual(result.flame_link_min, 0)
        self.assertEqual(result.flame_link_max, 0)

    def test_negative_multiplier_remains_unsupported(self) -> None:
        result = evaluate_manual_calculator(
            manual_input(
                increased_light_radius_pct="0",
                other_link_skill_buff_effect_pct="-150",
                golden_glory_allocated=False,
            ),
            level_table=self.table,
        )
        self.assertIsNone(result.flame_link_min)
        self.assertIsNone(result.flame_link_max)
        self.assertIn("unsupported", (result.flame_link_error or "").lower())

    def test_enmity_off_shows_no_value(self) -> None:
        result = evaluate_manual_calculator(
            manual_input(enmity_equipped=False),
            level_table=self.table,
        )
        self.assertEqual(result.pre_enmity_fire_resistance, "400")
        self.assertEqual(result.final_uncapped_fire_resistance, "400")
        self.assertIsNone(result.enmity_penetration)
        self.assertIsNone(result.enmity_error)


class LightRadiusBreakdownTests(unittest.TestCase):
    def test_breakdown_sum(self) -> None:
        breakdown = LightRadiusBreakdown()
        breakdown.slots["Helmet"] = Decimal("10")
        breakdown.slots["Body Armour"] = Decimal("5")
        breakdown.jewels[0] = Decimal("7")
        breakdown.jewels[1] = Decimal("-2")
        self.assertEqual(breakdown.total(), Decimal("20"))

    def test_adding_and_resetting_jewels(self) -> None:
        breakdown = LightRadiusBreakdown()
        self.assertEqual(len(breakdown.jewels), INITIAL_JEWEL_COUNT)
        breakdown.add_jewel()
        breakdown.jewels[-1] = Decimal("12")
        self.assertEqual(len(breakdown.jewels), INITIAL_JEWEL_COUNT + 1)
        self.assertTrue(breakdown.can_remove_jewel(INITIAL_JEWEL_COUNT))
        self.assertFalse(breakdown.can_remove_jewel(0))
        breakdown.remove_jewel(INITIAL_JEWEL_COUNT)
        self.assertEqual(len(breakdown.jewels), INITIAL_JEWEL_COUNT)
        breakdown.slots["Helmet"] = Decimal("9")
        breakdown.jewels[0] = Decimal("3")
        breakdown.add_jewel()
        breakdown.reset()
        self.assertEqual(len(breakdown.jewels), INITIAL_JEWEL_COUNT)
        self.assertEqual(breakdown.total(), Decimal(0))
        self.assertTrue(all(value == 0 for value in breakdown.slots.values()))


class ManualCalculatorAppTests(unittest.TestCase):
    def setUp(self) -> None:
        try:
            from golden_glory_lab.desktop.calculator_app import (
                GoldenGloryCalculatorApp,
            )

            self.app = GoldenGloryCalculatorApp()
        except Exception as error:  # pragma: no cover - environment dependent
            self.skipTest(f"Tk unavailable: {error}")

    def tearDown(self) -> None:
        app = getattr(self, "app", None)
        if app is not None:
            app.destroy()

    def test_both_pages_fit_the_fixed_window_when_populated(self) -> None:
        """The window is not resizable, so neither tab may need more height."""

        self.assertEqual(self.app.resizable(), (0, 0))
        self.app.maximum_life_var.set("abc")  # forces Results validation text
        self.app.gear_fire_res_var.set("633")
        self.app.aura_fire_res_var.set("0")
        self.app.enmity_reduced_var.set("abc")  # forces Enmity validation text
        self.app.maximum_fire_var.set("76")
        self.app.enmity_equipped_var.set(True)
        for _ in range(7):
            self.app.add_jewel_row()

        for page in (self.app.calculator_page, self.app.breakdown_page):
            self.app.notebook.select(page)
            self.app.update_idletasks()
            self.app.update()
            available = page.winfo_height()
            if available <= 1:  # pragma: no cover - unmapped window
                self.skipTest("window geometry unavailable")
            for card in page.winfo_children():
                self.assertLessEqual(
                    card.winfo_reqheight(),
                    available,
                    f"{self.app.notebook.tab(page, 'text')} tab clips its content",
                )

    def test_exactly_two_top_level_pages(self) -> None:
        titles = self.app.top_level_page_titles()
        self.assertEqual(titles, ("Calculator", "Light Radius Breakdown"))

    def test_does_not_expose_diagnostic_ui(self) -> None:
        forbidden = (
            "Mapping",
            "PoB review",
            "Evidence",
            "Open",
            "Save As",
            "Import raw XML",
            "Paste share code",
        )
        widget_text: list[str] = []

        def collect(widget: object) -> None:
            for child in widget.winfo_children():  # type: ignore[attr-defined]
                for option in ("text", "label"):
                    try:
                        value = child.cget(option)  # type: ignore[attr-defined]
                    except Exception:
                        value = None
                    if isinstance(value, str) and value:
                        widget_text.append(value)
                collect(child)

        collect(self.app)
        notebook_titles = self.app.top_level_page_titles()
        combined = " | ".join([*widget_text, *notebook_titles])
        for label in forbidden:
            self.assertNotIn(label, combined)

    def test_apply_total_copies_value_to_calculator_field(self) -> None:
        self.app._slot_vars["Helmet"].set("15")
        self.app._slot_vars["Body Armour"].set("25")
        self.app._on_breakdown_changed()
        self.app.apply_breakdown_total()
        self.assertEqual(self.app.light_radius_var.get(), "40")
        self.assertEqual(
            self.app.notebook.index(self.app.notebook.select()),
            self.app.notebook.index(self.app.calculator_page),
        )

    def test_breakdown_has_no_gloves_slot(self) -> None:
        """No current Light Radius source exists on gloves."""

        self.assertNotIn("Gloves", self.app._slot_vars)
        self.assertNotIn("Gloves", FIXED_LIGHT_RADIUS_SLOTS)
        for expected in (
            "Helmet",
            "Body Armour",
            "Boots",
            "Main Hand",
            "Off Hand",
            "Amulet",
            "Ring 1",
            "Ring 2",
            "Belt",
            "Passive Tree / Ascendancy",
            "Other / Misc",
        ):
            self.assertIn(expected, self.app._slot_vars)

    def test_add_and_reset_jewels_in_ui(self) -> None:
        self.app.add_jewel_row()
        self.assertEqual(len(self.app._jewel_vars), INITIAL_JEWEL_COUNT + 1)
        self.app._jewel_vars[-1].set("8")
        self.app._on_breakdown_changed()
        self.assertEqual(self.app._breakdown.total(), Decimal("8"))
        self.app.reset_breakdown()
        self.assertEqual(len(self.app._jewel_vars), INITIAL_JEWEL_COUNT)
        self.assertEqual(self.app._breakdown.total(), Decimal(0))

    def test_calculator_does_not_import_application_service(self) -> None:
        import ast

        import golden_glory_lab.desktop.calculator_app as module

        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                imported_names.add(module_name)
                imported_names.update(
                    f"{module_name}.{alias.name}" if module_name else alias.name
                    for alias in node.names
                )
        self.assertNotIn("ApplicationService", imported_names)
        joined = " ".join(sorted(imported_names))
        self.assertNotIn("desktop.service", joined)
        self.assertNotIn("ApplicationService", joined)


if __name__ == "__main__":
    unittest.main()
