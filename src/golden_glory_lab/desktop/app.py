"""Functional Tkinter/ttk presentation for BUILD-001."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from golden_glory_lab.build_state import BuildStateError

from .dialogs import ManualEntryDialog, ShareCodeDialog
from .service import ApplicationService


def _state_text(value: dict[str, Any]) -> str:
    state = value.get("state", "unknown")
    observed = value.get("value")
    return state if observed is None else f"{state}: {observed}"


def _json_text(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    )


class GoldenGloryApp(tk.Tk):
    """BUILD-001 review UI; canonical behavior remains in ApplicationService."""

    def __init__(self, service: ApplicationService | None = None) -> None:
        super().__init__()
        self.service = service or ApplicationService()
        self.title("Golden Glory Lab")
        self.minsize(980, 700)
        self.geometry("1220x820")
        self.protocol("WM_DELETE_WINDOW", self._exit)
        self._refreshing = False
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_toolbar()
        self._build_status()
        body = ttk.Panedwindow(self, orient="horizontal")
        body.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        sets_frame = ttk.Labelframe(body, text="Imported item-set occurrences")
        detail_frame = ttk.Frame(body)
        body.add(sets_frame, weight=2)
        body.add(detail_frame, weight=5)
        self._build_item_sets(sets_frame)
        self._build_notebook(detail_frame)

    def _build_toolbar(self) -> None:
        toolbar = ttk.Frame(self, padding=(8, 8, 8, 4))
        toolbar.grid(row=0, column=0, sticky="ew")
        actions = (
            ("New", self._new),
            ("Open", self._open),
            ("Save", self._save),
            ("Save As", self._save_as),
            ("Import raw XML", self._import_raw_xml),
            ("Paste share code", self._import_share_code),
        )
        for column, (label, command) in enumerate(actions):
            ttk.Button(toolbar, text=label, command=command).grid(
                row=0, column=column, padx=(0, 5)
            )
        toolbar.grid_columnconfigure(len(actions), weight=1)
        ttk.Button(toolbar, text="Exit", command=self._exit).grid(
            row=0, column=len(actions) + 1
        )

    def _build_status(self) -> None:
        frame = ttk.Labelframe(self, text="Build, file, and evidence status")
        frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.status_var = tk.StringVar()
        self.failed_var = tk.StringVar()
        ttk.Label(frame, textvariable=self.status_var, wraplength=1160).grid(
            row=0, column=0, sticky="w", padx=8, pady=(5, 2)
        )
        ttk.Label(
            frame,
            textvariable=self.failed_var,
            foreground="#9a3412",
            wraplength=1160,
        ).grid(row=1, column=0, sticky="w", padx=8, pady=(0, 5))
        frame.grid_columnconfigure(0, weight=1)

    def _build_item_sets(self, parent: ttk.Frame) -> None:
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        columns = (
            "occurrence",
            "source-id",
            "title",
            "assignments",
            "weapons",
            "review",
        )
        self.set_tree = ttk.Treeview(parent, columns=columns, show="headings")
        headings = {
            "occurrence": "Occurrence ID",
            "source-id": "Source ID / state",
            "title": "Title / state",
            "assignments": "Assignments",
            "weapons": "Weapon set",
            "review": "Warnings / ambiguity",
        }
        widths = {
            "occurrence": 125,
            "source-id": 125,
            "title": 165,
            "assignments": 85,
            "weapons": 110,
            "review": 170,
        }
        for name in columns:
            self.set_tree.heading(name, text=headings[name])
            self.set_tree.column(name, width=widths[name], minwidth=70)
        y_scroll = ttk.Scrollbar(
            parent, orient="vertical", command=self.set_tree.yview
        )
        x_scroll = ttk.Scrollbar(
            parent, orient="horizontal", command=self.set_tree.xview
        )
        self.set_tree.configure(
            yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set
        )
        self.set_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.set_tree.bind("<<TreeviewSelect>>", self._show_occurrence_review)

    def _build_notebook(self, parent: ttk.Frame) -> None:
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        notebook = ttk.Notebook(parent)
        notebook.grid(row=0, column=0, sticky="nsew")
        mapping = ttk.Frame(notebook, padding=10)
        review = ttk.Frame(notebook, padding=6)
        manual = ttk.Frame(notebook, padding=8)
        evidence = ttk.Frame(notebook, padding=8)
        notes = ttk.Frame(notebook, padding=8)
        notebook.add(mapping, text="Explicit mapping")
        notebook.add(review, text="Imported review")
        notebook.add(manual, text="Manual Mercenary equipment")
        notebook.add(evidence, text="Evidence status")
        notebook.add(notes, text="Notes")
        self._build_mapping(mapping)
        self._build_review(review)
        self._build_manual(manual)
        self._build_evidence(evidence)
        self._build_notes(notes)

    def _build_mapping(self, parent: ttk.Frame) -> None:
        parent.grid_columnconfigure(1, weight=1)
        ttk.Label(
            parent,
            text=(
                "Mappings are always explicit occurrence selections. Titles, order, "
                "active state, and item contents never assign ownership."
            ),
            wraplength=780,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 14))
        ttk.Label(parent, text="Player occurrence").grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.player_combo = ttk.Combobox(parent, state="readonly", width=38)
        self.player_combo.grid(row=1, column=1, sticky="ew", pady=5)
        self.player_combo.bind("<<ComboboxSelected>>", self._set_player_mapping)
        ttk.Label(parent, text="Mercenary source").grid(
            row=2, column=0, sticky="nw", pady=5
        )
        modes = ttk.Frame(parent)
        modes.grid(row=2, column=1, sticky="w", pady=5)
        self.mercenary_mode_var = tk.StringVar()
        for row, (label, value) in enumerate(
            (
                ("Not yet selected", "not-yet-selected"),
                ("Mapped item-set occurrence", "mapped-item-set"),
                ("Opaque manual equipment", "manual-equipment"),
            )
        ):
            ttk.Radiobutton(
                modes,
                text=label,
                value=value,
                variable=self.mercenary_mode_var,
                command=self._set_mercenary_mode,
            ).grid(row=row, column=0, sticky="w", pady=2)
        ttk.Label(parent, text="Mercenary occurrence").grid(
            row=3, column=0, sticky="w", pady=5
        )
        self.mercenary_combo = ttk.Combobox(parent, state="readonly", width=38)
        self.mercenary_combo.grid(row=3, column=1, sticky="ew", pady=5)
        self.mercenary_combo.bind(
            "<<ComboboxSelected>>", self._set_mercenary_mapping
        )
        ttk.Label(
            parent,
            text=(
                "Selecting mapped mode deactivates but does not delete manual entries. "
                "A new import clears both occurrence mappings and requires mapping again."
            ),
            wraplength=780,
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(14, 0))

    def _build_review(self, parent: ttk.Frame) -> None:
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        notebook = ttk.Notebook(parent)
        notebook.grid(row=0, column=0, sticky="nsew")
        assignments = ttk.Frame(notebook)
        item_pool = ttk.Frame(notebook)
        report = ttk.Frame(notebook)
        failed = ttk.Frame(notebook)
        notebook.add(assignments, text="Occurrence assignments")
        notebook.add(item_pool, text="Complete item pool")
        notebook.add(report, text="Importer report")
        notebook.add(failed, text="Last failed attempt")
        self.assignment_tree, self.assignment_detail = self._tree_with_detail(
            assignments,
            (
                ("slot", "Assignment / slot", 180),
                ("reference", "Item reference state", 160),
                ("weapon", "Primary / swap", 100),
                ("active", "Active state", 100),
                ("item", "Resolved item occurrence", 160),
            ),
            self._show_assignment_detail,
        )
        self.item_tree, self.item_detail = self._tree_with_detail(
            item_pool,
            (
                ("occurrence", "Item occurrence", 130),
                ("source-id", "Source ID / state", 130),
                ("usage", "Usage", 100),
                ("source", "Source pointer", 260),
                ("warnings", "Warnings", 180),
            ),
            self._show_item_detail,
        )
        self.report_tree, self.report_detail = self._tree_with_detail(
            report,
            (
                ("report", "Report ID", 100),
                ("category", "Category", 130),
                ("code", "Code", 210),
                ("stage", "Stage", 100),
                ("pointer", "Source pointer", 300),
            ),
            self._show_report_detail,
        )
        failed.grid_rowconfigure(0, weight=1)
        failed.grid_columnconfigure(0, weight=1)
        self.failed_detail = self._text_box(failed)
        self.failed_detail.grid(row=0, column=0, sticky="nsew")

    def _tree_with_detail(
        self,
        parent: ttk.Frame,
        columns: tuple[tuple[str, str, int], ...],
        selection_callback: Any,
    ) -> tuple[ttk.Treeview, tk.Text]:
        parent.grid_rowconfigure(0, weight=2)
        parent.grid_rowconfigure(1, weight=3)
        parent.grid_columnconfigure(0, weight=1)
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        names = tuple(column[0] for column in columns)
        tree = ttk.Treeview(frame, columns=names, show="headings")
        for name, heading, width in columns:
            tree.heading(name, text=heading)
            tree.column(name, width=width, minwidth=70)
        y_scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        x_scroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        tree.bind("<<TreeviewSelect>>", selection_callback)
        detail_frame = ttk.Frame(parent)
        detail_frame.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        detail_frame.grid_rowconfigure(0, weight=1)
        detail_frame.grid_columnconfigure(0, weight=1)
        detail = self._text_box(detail_frame)
        detail.grid(row=0, column=0, sticky="nsew")
        return tree, detail

    def _text_box(self, parent: ttk.Frame) -> tk.Text:
        text = tk.Text(parent, wrap="none", state="disabled", undo=False)
        y_scroll = ttk.Scrollbar(parent, orient="vertical", command=text.yview)
        x_scroll = ttk.Scrollbar(parent, orient="horizontal", command=text.xview)
        text.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        return text

    def _build_manual(self, parent: ttk.Frame) -> None:
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_rowconfigure(3, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        self.manual_mode_label = ttk.Label(parent)
        self.manual_mode_label.grid(row=0, column=0, sticky="w", pady=(0, 6))
        columns = ("id", "slot", "review", "note")
        self.manual_tree = ttk.Treeview(parent, columns=columns, show="headings")
        for name, heading, width in (
            ("id", "Entry ID", 120),
            ("slot", "Slot label", 170),
            ("review", "Review state", 150),
            ("note", "Note", 360),
        ):
            self.manual_tree.heading(name, text=heading)
            self.manual_tree.column(name, width=width, minwidth=80)
        self.manual_tree.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(parent, orient="vertical", command=self.manual_tree.yview)
        self.manual_tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=1, column=1, sticky="ns")
        self.manual_tree.bind("<<TreeviewSelect>>", self._show_manual_detail)
        buttons = ttk.Frame(parent)
        buttons.grid(row=2, column=0, sticky="w", pady=7)
        self.manual_add = ttk.Button(buttons, text="Add", command=self._add_manual)
        self.manual_edit = ttk.Button(buttons, text="Edit", command=self._edit_manual)
        self.manual_delete = ttk.Button(
            buttons, text="Delete", command=self._delete_manual
        )
        for column, button in enumerate(
            (self.manual_add, self.manual_edit, self.manual_delete)
        ):
            button.grid(row=0, column=column, padx=(0, 5))
        detail_frame = ttk.Frame(parent)
        detail_frame.grid(row=3, column=0, columnspan=2, sticky="nsew")
        detail_frame.grid_rowconfigure(0, weight=1)
        detail_frame.grid_columnconfigure(0, weight=1)
        self.manual_detail = self._text_box(detail_frame)
        self.manual_detail.grid(row=0, column=0, sticky="nsew")

    def _build_evidence(self, parent: ttk.Frame) -> None:
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_rowconfigure(2, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        ttk.Label(
            parent,
            text=(
                "Unavailable mechanics are evidence states, never numeric zero. "
                "BUILD-001 performs no mechanics calculation."
            ),
            wraplength=850,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))
        columns = ("label", "status", "claims")
        self.evidence_tree = ttk.Treeview(parent, columns=columns, show="headings")
        for name, heading, width in (
            ("label", "Output", 280),
            ("status", "Status", 210),
            ("claims", "Audit / claim references", 350),
        ):
            self.evidence_tree.heading(name, text=heading)
            self.evidence_tree.column(name, width=width, minwidth=100)
        self.evidence_tree.grid(row=1, column=0, sticky="nsew")
        self.evidence_tree.bind("<<TreeviewSelect>>", self._show_evidence_detail)
        detail_frame = ttk.Frame(parent)
        detail_frame.grid(row=2, column=0, sticky="nsew", pady=(6, 0))
        detail_frame.grid_rowconfigure(0, weight=1)
        detail_frame.grid_columnconfigure(0, weight=1)
        self.evidence_detail = self._text_box(detail_frame)
        self.evidence_detail.grid(row=0, column=0, sticky="nsew")

    def _build_notes(self, parent: ttk.Frame) -> None:
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        ttk.Label(
            parent,
            text="User notes are canonical content and survive import replacement.",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.notes_text = tk.Text(parent, wrap="word", undo=True)
        self.notes_text.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(parent, orient="vertical", command=self.notes_text.yview)
        self.notes_text.configure(yscrollcommand=scroll.set)
        scroll.grid(row=1, column=1, sticky="ns")
        self.notes_text.bind("<<Modified>>", self._notes_modified)

    def _set_readonly_text(self, widget: tk.Text, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.configure(state="disabled")

    def _refresh_notes(self) -> None:
        notes = self.service.state["userNotes"]
        if self.notes_text.get("1.0", "end-1c") != notes:
            self.notes_text.delete("1.0", "end")
            self.notes_text.insert("1.0", notes)
        self.notes_text.edit_modified(False)

    def _refresh_title(self) -> None:
        path = self.service.current_path
        title_path = str(path) if path is not None else "Unsaved build"
        marker = " *" if self.service.dirty else ""
        self.title(f"Golden Glory Lab - {title_path}{marker}")

    def _restore_rejected_edit(self) -> None:
        was_refreshing = self._refreshing
        self._refreshing = True
        try:
            self._refresh_status()
            self._refresh_mapping()
            self._refresh_notes()
            self._refresh_title()
        finally:
            self._refreshing = was_refreshing

    def _guard(self, action: Any) -> bool:
        try:
            action()
        except BuildStateError as error:
            messagebox.showerror(error.code, error.message, parent=self)
            self._restore_rejected_edit()
            return False
        except OSError as error:
            messagebox.showerror("File operation failed", str(error), parent=self)
            return False
        self._refresh()
        return True

    def _maybe_discard(self, action: str) -> bool:
        if not self.service.dirty:
            return True
        return messagebox.askyesno(
            "Discard modified build?",
            f"The canonical build has unsaved changes. Discard them and {action}?",
            icon="warning",
            parent=self,
        )

    def _new(self) -> None:
        if self._maybe_discard("start a new build"):
            self.service.new_document()
            self._refresh()

    def _open(self) -> None:
        if not self._maybe_discard("open another build"):
            return
        selected = filedialog.askopenfilename(
            parent=self,
            title="Open Golden Glory Lab build state",
            filetypes=(("Golden Glory Lab JSON", "*.json"), ("All files", "*.*")),
        )
        if selected:
            self._guard(lambda: self.service.open(selected))

    def _save(self) -> None:
        if self.service.current_path is None:
            self._save_as()
            return
        if self._guard(self.service.save):
            messagebox.showinfo("Saved", "Build state saved atomically.", parent=self)

    def _save_as(self) -> None:
        selected = filedialog.asksaveasfilename(
            parent=self,
            title="Save Golden Glory Lab build state",
            defaultextension=".json",
            filetypes=(("Golden Glory Lab JSON", "*.json"), ("All files", "*.*")),
        )
        if selected and self._guard(lambda: self.service.save(selected)):
            messagebox.showinfo("Saved", "Build state saved atomically.", parent=self)

    def _import_raw_xml(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self,
            title="Select Path of Building raw XML",
            filetypes=(("Path of Building XML", "*.xml"), ("All files", "*.*")),
        )
        if selected:
            self._handle_import(self.service.attempt_raw_xml(selected))

    def _import_share_code(self) -> None:
        dialog = ShareCodeDialog(self)
        if dialog.value is not None:
            self._handle_import(self.service.attempt_share_code(dialog.value))

    def _handle_import(self, outcome: str) -> None:
        if outcome == "failed":
            failure = self.service.last_failed_import or {}
            messagebox.showerror(
                f"Import failed: {failure.get('code', 'unknown')}",
                (
                    f"Stage: {failure.get('stage', 'unknown')}\n"
                    f"{failure.get('message', '')}\n\n"
                    "The current import, mappings, manual entries, and readiness "
                    "were preserved."
                ),
                parent=self,
            )
        elif outcome == "confirmation-required":
            confirmed = messagebox.askyesno(
                "Replace successful import?",
                (
                    "The new import is staged. Replacing the existing import clears "
                    "player and Mercenary occurrence mappings, preserves manual "
                    "equipment and notes, and requires explicit mapping again."
                ),
                icon="warning",
                parent=self,
            )
            self._guard(lambda: self.service.confirm_pending_import(confirmed))
            return
        self._refresh()

    def _set_player_mapping(self, _event: tk.Event[Any]) -> None:
        value = self.player_combo.get() or None
        self._guard(lambda: self.service.set_player_mapping(value))

    def _set_mercenary_mapping(self, _event: tk.Event[Any]) -> None:
        value = self.mercenary_combo.get()
        if value:
            self._guard(
                lambda: self.service.set_mercenary_source("mapped-item-set", value)
            )

    def _set_mercenary_mode(self) -> None:
        mode = self.mercenary_mode_var.get()
        occurrence = self.mercenary_combo.get() or None
        if mode == "mapped-item-set" and occurrence is None:
            messagebox.showerror(
                "Explicit occurrence required",
                "Choose the Mercenary occurrence before selecting mapped mode.",
                parent=self,
            )
            self.mercenary_mode_var.set(self.service.state["mercenarySourceMode"])
            return
        self._guard(lambda: self.service.set_mercenary_source(mode, occurrence))

    def _selected_manual(self) -> dict[str, Any] | None:
        selected = self.manual_tree.selection()
        if not selected:
            return None
        entry_id = selected[0]
        return next(
            (
                entry
                for entry in self.service.state["manualMercenaryEquipment"]
                if entry["entryId"] == entry_id
            ),
            None,
        )

    def _add_manual(self) -> None:
        dialog = ManualEntryDialog(self, title="Add opaque manual equipment")
        if dialog.value:
            value = dialog.value
            self._guard(
                lambda: self.service.add_manual_entry(
                    value["slotLabel"], value["rawText"], value["note"]
                )
            )

    def _edit_manual(self) -> None:
        entry = self._selected_manual()
        if entry is None:
            messagebox.showinfo("Manual equipment", "Select an entry first.", parent=self)
            return
        dialog = ManualEntryDialog(
            self,
            title=f"Edit {entry['entryId']}",
            initial=entry,
        )
        if dialog.value:
            value = dialog.value
            self._guard(
                lambda: self.service.edit_manual_entry(
                    entry["entryId"],
                    value["slotLabel"],
                    value["rawText"],
                    value["note"],
                )
            )

    def _delete_manual(self) -> None:
        entry = self._selected_manual()
        if entry is None:
            messagebox.showinfo("Manual equipment", "Select an entry first.", parent=self)
            return
        confirmed = messagebox.askyesno(
            "Delete manual entry?",
            f"Delete {entry['entryId']}? This explicit action cannot be undone.",
            icon="warning",
            parent=self,
        )
        self._guard(
            lambda: self.service.delete_manual_entry(
                entry["entryId"], confirmed=confirmed
            )
        )

    def _notes_modified(self, _event: tk.Event[Any]) -> None:
        if self._refreshing:
            self.notes_text.edit_modified(False)
            return
        if not self.notes_text.edit_modified():
            return
        value = self.notes_text.get("1.0", "end-1c")
        try:
            self.service.set_user_notes(value)
        except BuildStateError as error:
            messagebox.showerror(error.code, error.message, parent=self)
            self._restore_rejected_edit()
            return
        self.notes_text.edit_modified(False)
        self._refresh_status()
        self._refresh_title()

    def _exit(self) -> None:
        if self._maybe_discard("exit"):
            self.destroy()

    def _refresh(self) -> None:
        self._refreshing = True
        try:
            self._refresh_status()
            self._refresh_item_sets()
            self._refresh_mapping()
            self._refresh_import_review()
            self._refresh_manual()
            self._refresh_evidence()
            self._refresh_notes()
            self._refresh_title()
        finally:
            self._refreshing = False

    def _refresh_status(self) -> None:
        status = self.service.status_summary()
        self.status_var.set(
            " | ".join(
                (
                    f"Import: {status['import']}",
                    f"Player mapping: {status['playerMapping']}",
                    f"Mercenary: {status['mercenarySourceMode']}",
                    f"File: {status['localFileState']}",
                    f"Importer warnings: {status['importerWarnings']}",
                    f"Mechanics: {status['mechanics']}",
                    f"Intake ready: {'yes' if status['intakeReady'] else 'no'}",
                )
            )
        )
        failure = self.service.last_failed_import
        self.failed_var.set(
            ""
            if failure is None
            else (
                f"Last failed attempt (not saved): {failure['code']} at "
                f"{failure['stage']} - {failure['message']}"
            )
        )

    def _refresh_item_sets(self) -> None:
        selected = self.set_tree.selection()
        selected_id = selected[0] if selected else None
        self.set_tree.delete(*self.set_tree.get_children())
        for item_set in self.service.item_sets():
            warning_codes = list(item_set.get("warnings", []))
            for assignment in item_set["assignments"]:
                warning_codes.extend(assignment.get("warnings", []))
                state = assignment["resolution"]["state"]
                if state in {"malformed", "unresolved", "ambiguous"}:
                    warning_codes.append(state)
            review = (
                "none"
                if not warning_codes
                else ", ".join(dict.fromkeys(warning_codes))
            )
            weapon = item_set["useSecondWeaponSet"]
            self.set_tree.insert(
                "",
                "end",
                iid=item_set["occurrenceId"],
                values=(
                    item_set["occurrenceId"],
                    _state_text(item_set["rawId"]),
                    _state_text(item_set["title"]),
                    len(item_set["assignments"]),
                    f"{_state_text(weapon['raw'])}; parsed={weapon['parsed']}",
                    review,
                ),
            )
        children = self.set_tree.get_children()
        if selected_id in children:
            self.set_tree.selection_set(selected_id)
        elif children:
            self.set_tree.selection_set(children[0])
        self._show_occurrence_review(None)

    def _refresh_mapping(self) -> None:
        occurrences = [entry["occurrenceId"] for entry in self.service.item_sets()]
        values = ["", *occurrences]
        self.player_combo.configure(values=values)
        self.mercenary_combo.configure(values=values)
        state = self.service.state
        self.player_combo.set(state["playerItemSetOccurrenceId"] or "")
        self.mercenary_combo.set(state["mercenaryItemSetOccurrenceId"] or "")
        self.mercenary_mode_var.set(state["mercenarySourceMode"])

    def _refresh_import_review(self) -> None:
        self.item_tree.delete(*self.item_tree.get_children())
        for item in self.service.imported_items():
            raw_id = item.get("rawId", {"state": "missing", "value": None})
            usage = item.get("usage", {}).get("state", "unknown")
            self.item_tree.insert(
                "",
                "end",
                iid=item["occurrenceId"],
                values=(
                    item["occurrenceId"],
                    _state_text(raw_id),
                    usage,
                    item["sourcePath"],
                    ", ".join(item.get("warnings", [])) or "none",
                ),
            )
        self.report_tree.delete(*self.report_tree.get_children())
        for entry in self.service.importer_report():
            self.report_tree.insert(
                "",
                "end",
                iid=entry["reportId"],
                values=(
                    entry["reportId"],
                    entry["category"],
                    entry["code"],
                    entry["stage"],
                    entry["sourcePointer"],
                ),
            )
        failure = self.service.last_failed_import
        self._set_readonly_text(
            self.failed_detail,
            "No failed import attempt in this session."
            if failure is None
            else _json_text(failure),
        )

    def _refresh_manual(self) -> None:
        self.manual_tree.delete(*self.manual_tree.get_children())
        state = self.service.state
        mode = state["mercenarySourceMode"]
        self.manual_mode_label.configure(
            text=(
                f"Current Mercenary source mode: {mode}. "
                "Entries remain stored when mapped mode is active."
            )
        )
        button_state = "normal" if mode == "manual-equipment" else "disabled"
        for button in (self.manual_add, self.manual_edit, self.manual_delete):
            button.configure(state=button_state)
        for entry in state["manualMercenaryEquipment"]:
            self.manual_tree.insert(
                "",
                "end",
                iid=entry["entryId"],
                values=(
                    entry["entryId"],
                    entry["slotLabel"],
                    entry["reviewState"],
                    entry["note"],
                ),
            )

    def _refresh_evidence(self) -> None:
        self.evidence_tree.delete(*self.evidence_tree.get_children())
        for entry in self.service.mechanics_status():
            self.evidence_tree.insert(
                "",
                "end",
                iid=entry["id"],
                values=(
                    entry["label"],
                    entry["status"],
                    ", ".join(entry["claimReferences"]),
                ),
            )

    def _selected_occurrence(self) -> dict[str, Any] | None:
        selected = self.set_tree.selection()
        if not selected:
            return None
        occurrence_id = selected[0]
        return next(
            (
                item_set
                for item_set in self.service.item_sets()
                if item_set["occurrenceId"] == occurrence_id
            ),
            None,
        )

    def _show_occurrence_review(self, _event: tk.Event[Any] | None) -> None:
        self.assignment_tree.delete(*self.assignment_tree.get_children())
        item_set = self._selected_occurrence()
        if item_set is None:
            return
        for assignment in item_set["assignments"]:
            candidates = assignment["resolution"]["candidateOccurrences"]
            slot = _state_text(assignment["originalSlotName"])
            original_name = assignment["originalSlotName"]["value"] or ""
            weapon = "swap" if " Swap" in original_name else "primary"
            active = assignment["active"]
            self.assignment_tree.insert(
                "",
                "end",
                iid=assignment["occurrenceId"],
                values=(
                    slot,
                    assignment["resolution"]["state"],
                    weapon,
                    f"{_state_text(active['raw'])}; parsed={active['parsed']}",
                    ", ".join(candidates) or "none",
                ),
            )

    def _assignment_by_id(self, identifier: str) -> dict[str, Any] | None:
        item_set = self._selected_occurrence()
        if item_set is None:
            return None
        return next(
            (
                assignment
                for assignment in item_set["assignments"]
                if assignment["occurrenceId"] == identifier
            ),
            None,
        )

    def _show_assignment_detail(self, _event: tk.Event[Any]) -> None:
        selected = self.assignment_tree.selection()
        if not selected:
            return
        assignment = self._assignment_by_id(selected[0])
        if assignment is None:
            return
        items = {
            item["occurrenceId"]: item for item in self.service.imported_items()
        }
        resolved = [
            {
                "occurrenceId": identifier,
                "sourcePath": items[identifier]["sourcePath"],
                "rawText": items[identifier]["xmlCharacterValue"],
                "orderedChildMaterial": items[identifier]["orderedChildMaterial"],
                "warnings": items[identifier].get("warnings", []),
            }
            for identifier in assignment["resolution"]["candidateOccurrences"]
            if identifier in items
        ]
        self._set_readonly_text(
            self.assignment_detail,
            _json_text({"assignment": assignment, "resolvedItems": resolved}),
        )

    def _show_item_detail(self, _event: tk.Event[Any]) -> None:
        selected = self.item_tree.selection()
        if not selected:
            return
        item = next(
            (
                entry
                for entry in self.service.imported_items()
                if entry["occurrenceId"] == selected[0]
            ),
            None,
        )
        if item is not None:
            self._set_readonly_text(self.item_detail, _json_text(item))

    def _show_report_detail(self, _event: tk.Event[Any]) -> None:
        selected = self.report_tree.selection()
        if not selected:
            return
        entry = next(
            (
                value
                for value in self.service.importer_report()
                if value["reportId"] == selected[0]
            ),
            None,
        )
        if entry is not None:
            self._set_readonly_text(self.report_detail, _json_text(entry))

    def _show_manual_detail(self, _event: tk.Event[Any]) -> None:
        entry = self._selected_manual()
        if entry is not None:
            self._set_readonly_text(self.manual_detail, _json_text(entry))

    def _show_evidence_detail(self, _event: tk.Event[Any]) -> None:
        selected = self.evidence_tree.selection()
        if not selected:
            return
        entry = next(
            (
                value
                for value in self.service.mechanics_status()
                if value["id"] == selected[0]
            ),
            None,
        )
        if entry is not None:
            self._set_readonly_text(self.evidence_detail, _json_text(entry))
