from __future__ import annotations

import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from golden_glory_lab.desktop.app import (  # noqa: E402
    GoldenGloryApp,
    _enmity_result_text,
    _review_detail_text,
    _review_row,
)
from golden_glory_lab.desktop.service import ApplicationService  # noqa: E402
from golden_glory_lab.desktop.dialogs import CopiedItemDialog  # noqa: E402
from golden_glory_lab.build_state import (  # noqa: E402
    MAX_CONTEXT_FIELD_CHARACTERS,
    BuildStateError,
)
from golden_glory_lab.item_review import ReviewSourceLocator  # noqa: E402

COPIED_FIXTURE = (
    "Item Class: Rings\r\n"
    "Rarity: Unique\r\n"
    "Enmity's Embrace\r\n"
    "Vermillion Ring\r\n"
    "--------\r\n"
    "Unsupported exact line\r\n"
)


class FakeValue:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


class FakeText:
    def __init__(self) -> None:
        self.value = ""
        self.state = "disabled"

    def configure(self, **values: str) -> None:
        self.state = values.get("state", self.state)

    def delete(self, _start: str, _end: str) -> None:
        self.value = ""

    def insert(self, _start: str, value: str) -> None:
        self.value = value


class FakeTree:
    def __init__(self) -> None:
        self.rows: dict[str, tuple] = {}
        self.selected: tuple[str, ...] = ()

    def selection(self) -> tuple[str, ...]:
        return self.selected

    def selection_set(self, identifier: str) -> None:
        self.selected = (identifier,)

    def get_children(self) -> tuple[str, ...]:
        return tuple(self.rows)

    def delete(self, *identifiers: str) -> None:
        for identifier in identifiers:
            self.rows.pop(identifier, None)
        if self.selected and self.selected[0] not in self.rows:
            self.selected = ()

    def insert(
        self,
        _parent: str,
        _index: str,
        *,
        iid: str,
        values: tuple,
    ) -> None:
        self.rows[iid] = values


class FakePasteText:
    def __init__(self) -> None:
        self.value = "replace me"

    def tag_ranges(self, name: str) -> tuple[str, str]:
        self.assert_name = name
        return ("1.0", "1.10")

    def delete(self, start: str, end: str) -> None:
        self.deleted = (start, end)
        self.value = ""

    def insert(self, index: str, value: str) -> None:
        self.inserted_at = index
        self.value += value


class CopiedItemDialogTests(unittest.TestCase):
    def test_native_clipboard_paste_preserves_crlf_exactly(self) -> None:
        raw = "first\r\nsecond\r\n"
        dialog = CopiedItemDialog.__new__(CopiedItemDialog)
        dialog._raw = FakePasteText()
        count_updates: list[bool] = []
        dialog._update_count = lambda: count_updates.append(True)
        with patch(
            "golden_glory_lab.desktop.dialogs._windows_clipboard_text",
            return_value=raw,
        ):
            result = dialog._paste_exact_clipboard(None)
        self.assertEqual(result, "break")
        self.assertEqual(dialog._raw.value, raw)
        self.assertEqual(dialog._raw.assert_name, "sel")
        self.assertEqual(dialog._raw.deleted, ("sel.first", "sel.last"))
        self.assertEqual(dialog._raw.inserted_at, "insert")
        self.assertEqual(count_updates, [True])


class LayoutPresentationTests(unittest.TestCase):
    def test_tabs_and_enmity_controls_remain_readable_at_minimum_size(self) -> None:
        try:
            app = GoldenGloryApp()
        except tk.TclError as error:
            self.skipTest(f"Tk display unavailable: {error}")
        try:
            app.attributes("-alpha", 0.0)
            app.geometry("980x700+0+0")

            def descendants(widget: tk.Misc):
                for child in widget.winfo_children():
                    yield child
                    yield from descendants(child)

            main = max(
                (
                    widget
                    for widget in descendants(app)
                    if isinstance(widget, ttk.Notebook)
                ),
                key=lambda widget: len(widget.tabs()),
            )
            self.assertEqual(
                [main.tab(tab, "text") for tab in main.tabs()],
                [
                    "Mapping",
                    "PoB review",
                    "Common review",
                    "Copied",
                    "Manual gear",
                    "Enmity",
                    "Evidence",
                    "Notes",
                ],
            )
            main.select(5)
            app.update()
            page = app.nametowidget(main.tabs()[5])
            input_notebook = next(
                widget
                for widget in descendants(page)
                if isinstance(widget, ttk.Notebook)
                and [widget.tab(tab, "text") for tab in widget.tabs()]
                == ["Numbers", "States", "Context"]
            )
            entries: list[int] = []
            combos: list[int] = []
            result_texts = [
                (widget.winfo_width(), widget.winfo_height())
                for widget in descendants(page)
                if isinstance(widget, tk.Text) and widget.winfo_ismapped()
            ]
            output_notebook = next(
                widget
                for widget in descendants(page)
                if isinstance(widget, ttk.Notebook) and len(widget.tabs()) == 2
            )
            apply_button = next(
                widget
                for widget in descendants(page)
                if isinstance(widget, ttk.Button)
                and widget.cget("text") == "Apply manual Enmity input"
            )
            self.assertTrue(apply_button.winfo_ismapped())
            for tab in input_notebook.tabs():
                input_notebook.select(tab)
                app.update()
                visible_controls = [
                    widget
                    for widget in descendants(page)
                    if isinstance(widget, (ttk.Entry, ttk.Combobox, ttk.Button))
                    and widget.winfo_ismapped()
                ]
                entries.extend(
                    widget.winfo_width()
                    for widget in visible_controls
                    if isinstance(widget, ttk.Entry)
                )
                combos.extend(
                    widget.winfo_width()
                    for widget in visible_controls
                    if isinstance(widget, ttk.Combobox)
                )
                self.assertLessEqual(
                    max(
                        widget.winfo_rooty() + widget.winfo_height()
                        for widget in visible_controls
                    ),
                    output_notebook.winfo_rooty(),
                )
            self.assertGreaterEqual(min(entries), 120)
            self.assertGreaterEqual(min(combos), 120)
            self.assertTrue(
                any(width >= 400 and height >= 180 for width, height in result_texts)
            )
        finally:
            app.destroy()


def complete_context_vars() -> dict[str, FakeValue]:
    return {
        "mercenaryIdentityLevel": FakeValue("Synthetic Mercenary level 90"),
        "activeStateSelection": FakeValue("Active state"),
        "zoneOrUiContext": FakeValue("Hideout UI"),
        "relevantEffectsConditions": FakeValue("No temporary effects"),
        "equipmentStateDescription": FakeValue("Enmity equipped"),
        "captureTimingDescription": FakeValue("After refresh"),
    }


class CommonReviewPresentationTests(unittest.TestCase):
    def test_row_and_detail_expose_provenance_roles_identity_reports_and_exact_raw(self) -> None:
        service = ApplicationService()
        service.add_copied_entry(
            COPIED_FIXTURE,
            role="mercenary",
            slot_label="Ring 1",
            user_label="Observed",
            note="Exact synthetic source",
        )
        review = service.item_reviews()[0]
        row = _review_row(review)
        self.assertEqual(row[0], "copied-text")
        self.assertEqual(row[1], "mercenary")
        self.assertEqual(row[3], "Ring 1, Observed")
        self.assertEqual(row[5], "partially-recognized")
        detail = _review_detail_text(review)
        self.assertIn(COPIED_FIXTURE, detail)
        self.assertIn("UNRECOGNIZED_ORDERED_ITEM_MATERIAL", detail)
        self.assertIn(review.rawTextSha256, detail)
        self.assertLess(
            detail.index("--- EXACT RETAINED RAW TEXT START ---"),
            detail.index(COPIED_FIXTURE),
        )

    def test_headless_common_review_filters_and_exact_detail(self) -> None:
        service = ApplicationService()
        service.add_copied_entry(COPIED_FIXTURE, role="mercenary")
        app = GoldenGloryApp.__new__(GoldenGloryApp)
        app.service = service
        app.common_tree = FakeTree()
        app.common_detail = FakeText()
        app.common_provenance_var = FakeValue("all")
        app.common_role_var = FakeValue("all")
        app.common_recognition_var = FakeValue("all")
        app._refresh_common_review()
        self.assertEqual(len(app.common_tree.rows), 1)
        self.assertIn(COPIED_FIXTURE, app.common_detail.value)

        app.common_role_var.set("player")
        app._refresh_common_review()
        self.assertEqual(app.common_tree.rows, {})
        self.assertIn("No common item-review instance", app.common_detail.value)

    def test_empty_pob_item_appears_under_manually_required_filter(self) -> None:
        xml = (
            '<PathOfBuilding><Build targetVersion="3_0"/>'
            '<Items activeItemSet="1"><Item id="1"></Item>'
            '<ItemSet id="1" title="Boundary" useSecondWeaponSet="false">'
            '<Slot name="Weapon 1" itemId="1"/></ItemSet></Items></PathOfBuilding>'
        )
        from golden_glory_lab.build_state import (
            empty_document,
            imported_result_digest,
            serialize,
        )
        from golden_glory_lab.pob_import import importPobRawXml

        result = importPobRawXml(xml)
        self.assertEqual(result["status"], "success")
        document = empty_document()
        document["importedResult"] = result
        document["importedResultSha256"] = imported_result_digest(result)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "empty-pob.json"
            path.write_bytes(serialize(document))
            service = ApplicationService()
            service.open(path)
            review = next(
                item
                for item in service.item_reviews()
                if item.sourceLocator.sourceId
                == result["document"]["items"][0]["occurrenceId"]
            )
            self.assertEqual(review.recognitionState, "manually-required")
            app = GoldenGloryApp.__new__(GoldenGloryApp)
            app.service = service
            app.common_tree = FakeTree()
            app.common_detail = FakeText()
            app.common_provenance_var = FakeValue("all")
            app.common_role_var = FakeValue("all")
            app.common_recognition_var = FakeValue("manually-required")
            app._refresh_common_review()
            self.assertIn(review.reviewInstanceId, app.common_tree.rows)
            app.common_recognition_var.set("unrecognized")
            app._refresh_common_review()
            self.assertNotIn(review.reviewInstanceId, app.common_tree.rows)


class EnmityControllerPresentationTests(unittest.TestCase):
    def _headless_form(self, service: ApplicationService) -> GoldenGloryApp:
        app = GoldenGloryApp.__new__(GoldenGloryApp)
        app.service = service
        app._refreshing = False
        app.enmity_u_var = FakeValue("300")
        app.enmity_m_var = FakeValue("75")
        app.enmity_target_var = FakeValue("200")
        app.enmity_equipped_var = FakeValue("equipped")
        app.enmity_inclusion_var = FakeValue("unknown")
        app.enmity_ack_var = FakeValue("confirmed-3.29.1")
        app.enmity_observed_var = FakeValue("(none)")
        app.enmity_context_vars = complete_context_vars()
        app._observed_locator_by_display = {"(none)": None}

        def guard(action: object) -> bool:
            action()
            return True

        app._guard = guard
        return app

    def test_form_applies_exact_lexemes_context_states_target_and_observed_locator(self) -> None:
        service = ApplicationService()
        identifier = service.add_copied_entry(COPIED_FIXTURE, role="unassigned")
        self.assertEqual(service.state["enmityManualInput"]["equippedState"], "unknown")
        app = self._headless_form(service)
        locator = ReviewSourceLocator("copied-text", identifier)
        app._observed_locator_by_display["observed"] = locator
        app.enmity_observed_var.set("observed")
        app.enmity_u_var.set("0300.00")
        app.enmity_m_var.set("075.0")
        app._apply_enmity_input()

        state = service.state["enmityManualInput"]
        self.assertEqual(state["finalUncappedFireResistance"], "0300.00")
        self.assertEqual(state["maximumFireResistance"], "075.0")
        self.assertEqual(state["observedItemReference"], locator.to_dict())
        result = service.enmity_result()
        self.assertTrue(result.available)
        self.assertEqual(result.overcap, 225)
        self.assertEqual(result.value, 200)
        self.assertEqual(result.inputBeyondCap, 25)
        self.assertEqual(result.target.state, "available")

    def test_available_zero_unavailable_fractional_and_target_states_are_visible(self) -> None:
        service = ApplicationService()
        app = self._headless_form(service)
        app.enmity_u_var.set("75")
        app._apply_enmity_input()
        zero = service.enmity_result()
        zero_text = _enmity_result_text(zero)
        self.assertTrue(zero.available)
        self.assertTrue(zero_text.startswith("AVAILABLE NUMERIC VALUE: 0"))
        self.assertIn('"value": 0', zero_text)

        app.enmity_u_var.set("75.5")
        app._apply_enmity_input()
        fractional = service.enmity_result()
        fractional_text = _enmity_result_text(fractional)
        self.assertEqual(fractional.state, "rounding-evidence-required")
        self.assertTrue(fractional_text.startswith("NUMERIC VALUE: unavailable"))
        self.assertIn('"value": null', fractional_text)

        app.enmity_u_var.set("300")
        app.enmity_target_var.set("200.5")
        app._apply_enmity_input()
        target = service.enmity_result()
        self.assertTrue(target.available)
        self.assertEqual(target.value, 200)
        self.assertEqual(target.target.state, "invalid-target")

        app.enmity_equipped_var.set("not-equipped")
        app._apply_enmity_input()
        not_applicable = service.enmity_result()
        self.assertEqual(not_applicable.state, "not-applicable")
        self.assertIsNone(not_applicable.value)

    def test_gate_details_are_structured_and_blocked_outputs_remain_null(self) -> None:
        service = ApplicationService()
        evidence = service.runtime_evidence_status()
        self.assertEqual(evidence["state"], "available")
        self.assertEqual(len(evidence["manifest"]["claims"]), 4)
        self.assertTrue(all(value["available"] for value in evidence["outputs"].values()))
        blocked = service.mechanics_status()
        self.assertTrue(blocked)
        self.assertTrue(all(value["value"] is None for value in blocked))
        labels = {value["label"] for value in blocked}
        self.assertIn("Total penetration", labels)
        self.assertIn("Damage and DPS", labels)
        self.assertIn("Golden Glory arithmetic", labels)

    def _restoring_form(self, service: ApplicationService) -> GoldenGloryApp:
        app = self._headless_form(service)
        app.enmity_result_detail = FakeText()
        app.enmity_gate_detail = FakeText()
        app.status_var = FakeValue()
        app.failed_var = FakeValue()
        app.enmity_observed_combo = FakeValue()
        app.enmity_observed_combo.configure = lambda **_values: None
        app.title = lambda value=None: getattr(app, "_title", "") if value is None else setattr(app, "_title", value)
        app._title = "Golden Glory Lab - test"

        def set_readonly(widget: FakeText, value: str) -> None:
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            widget.insert("1.0", value)
            widget.configure(state="disabled")

        app._set_readonly_text = set_readonly
        app._refresh_status = GoldenGloryApp._refresh_status.__get__(app, GoldenGloryApp)
        app._refresh_mapping = lambda: None
        app._refresh_notes = lambda: None
        app._refresh_title = GoldenGloryApp._refresh_title.__get__(app, GoldenGloryApp)
        app._refresh_enmity = GoldenGloryApp._refresh_enmity.__get__(app, GoldenGloryApp)
        app._restore_rejected_edit = GoldenGloryApp._restore_rejected_edit.__get__(
            app, GoldenGloryApp
        )

        def guard(action: object) -> bool:
            try:
                action()
            except BuildStateError as error:
                app._last_error = error
                app._restore_rejected_edit()
                return False
            app._refresh_enmity()
            app._refresh_status()
            app._refresh_title()
            return True

        app._guard = guard
        app._last_error = None
        app._refresh_enmity()
        app._refresh_status()
        app._refresh_title()
        return app

    def test_rejected_enmity_edits_restore_canonical_widgets(self) -> None:
        service = ApplicationService()
        identifier = service.add_copied_entry(COPIED_FIXTURE, role="unassigned")
        locator = ReviewSourceLocator("copied-text", identifier)
        service.set_enmity_input(
            final_uncapped_fire_resistance="300",
            maximum_fire_resistance="75",
            equipped_state="equipped",
            equipment_inclusion_state="included",
            measurement_context={
                field: fake.get()
                for field, fake in complete_context_vars().items()
            },
            target_game_version_acknowledgement="confirmed-3.29.1",
            observed_item_reference=locator,
            target="200",
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "clean.json"
            service.save(path)
            self.assertFalse(service.dirty)
            app = self._restoring_form(service)
            before_result = app.enmity_result_detail.value
            before_gates = app.enmity_gate_detail.value
            before_title = app._title

            app.enmity_u_var.set(" 300")
            app._apply_enmity_input()
            self.assertEqual(app._last_error.code, "DECIMAL_TEXT_GRAMMAR")
            self.assertEqual(app.enmity_u_var.get(), "300")
            self.assertEqual(app.enmity_result_detail.value, before_result)
            self.assertEqual(app.enmity_gate_detail.value, before_gates)
            self.assertEqual(app._title, before_title)
            self.assertFalse(service.dirty)

            service.set_enmity_input(final_uncapped_fire_resistance="310")
            self.assertTrue(service.dirty)
            app = self._restoring_form(service)
            app.enmity_m_var.set("75 ")
            app._apply_enmity_input()
            self.assertEqual(app.enmity_m_var.get(), "75")
            self.assertEqual(app.enmity_u_var.get(), "310")
            self.assertIn(" *", app._title)

            context = {
                field: variable.get()
                for field, variable in app.enmity_context_vars.items()
            }
            context["zoneOrUiContext"] = "x" * MAX_CONTEXT_FIELD_CHARACTERS
            service.set_enmity_input(measurement_context=context)
            app = self._restoring_form(service)
            self.assertEqual(
                app.enmity_context_vars["zoneOrUiContext"].get(),
                "x" * MAX_CONTEXT_FIELD_CHARACTERS,
            )

            app.enmity_context_vars["zoneOrUiContext"].set(
                "x" * (MAX_CONTEXT_FIELD_CHARACTERS + 1)
            )
            before_result = app.enmity_result_detail.value
            app._apply_enmity_input()
            self.assertEqual(
                app.enmity_context_vars["zoneOrUiContext"].get(),
                "x" * MAX_CONTEXT_FIELD_CHARACTERS,
            )
            self.assertEqual(app.enmity_result_detail.value, before_result)

            app.enmity_observed_var.set("missing-locator")
            app._observed_locator_by_display["missing-locator"] = ReviewSourceLocator(
                "copied-text", "missing"
            )
            app._apply_enmity_input()
            self.assertIn(identifier, app.enmity_observed_var.get())
            self.assertIn(identifier, app.enmity_result_detail.value)

            app.enmity_u_var.set("75.5")
            app._apply_enmity_input()
            result = service.enmity_result()
            self.assertEqual(result.state, "rounding-evidence-required")
            self.assertIsNone(result.value)
            self.assertIn("rounding-evidence-required", app.enmity_result_detail.value)


class MigrationStatusPresentationTests(unittest.TestCase):
    def test_v1_open_displays_upgrade_pending_status(self) -> None:
        source = (
            ROOT / "fixtures" / "build_state" / "empty.build-state-v1.json"
        ).read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "legacy.json"
            path.write_bytes(source)
            service = ApplicationService()
            service.open(path)
            app = GoldenGloryApp.__new__(GoldenGloryApp)
            app.service = service
            app.status_var = FakeValue()
            app.failed_var = FakeValue()
            app._refresh_status()
        self.assertIn("File: upgrade-pending", app.status_var.get())
        self.assertIn("Migration: upgrade pending", app.status_var.get())


if __name__ == "__main__":
    unittest.main()
