"""Functional Tkinter/ttk presentation for BUILD-002."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from golden_glory_lab.build_state import BuildStateError, MEASUREMENT_CONTEXT_FIELDS
from golden_glory_lab.item_review import ReviewSourceLocator

from .dialogs import CopiedItemDialog, ManualEntryDialog, ShareCodeDialog
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


def _review_identity_text(review: Any) -> str:
    identity = review.parsedIdentity
    if identity is None:
        return "unrecognized"
    return " / ".join(
        value
        for value in (identity.itemName, identity.baseType)
        if value
    ) or "structure only"


def _review_row(review: Any) -> tuple[str, ...]:
    roles = ", ".join(dict.fromkeys(binding.role for binding in review.bindings))
    return (
        review.provenanceKind,
        roles,
        review.sourceLocator.sourceId,
        ", ".join(review.slotOrAssignmentLabels) or "none",
        _review_identity_text(review),
        review.recognitionState,
        ", ".join(review.warnings) or "none",
    )


def _review_detail_text(review: Any) -> str:
    metadata = review.to_dict()
    exact = metadata.pop("exactRawText")
    return (
        "SOURCE PROVENANCE AND ORDERED RECOGNITION REPORT\n"
        + _json_text(metadata)
        + "\n\n--- EXACT RETAINED RAW TEXT START ---\n"
        + exact
        + "\n--- EXACT RETAINED RAW TEXT END ---\n"
    )


def _enmity_result_text(result: Any, observed_summary: Any = None) -> str:
    numeric_summary = (
        f"AVAILABLE NUMERIC VALUE: {result.value}"
        if result.available
        else "NUMERIC VALUE: unavailable (null; never substituted with zero)"
    )
    return numeric_summary + "\n\n" + _json_text(
        {
            "result": result.to_dict(),
            "observedItemSummary": observed_summary,
        }
    )


def _flame_link_result_text(result: Any) -> str:
    if result.available:
        numeric_summary = (
            f"MODELLED INTEGER RANGE: {result.modelledIntegerMin}-"
            f"{result.modelledIntegerMax} ({result.roundingPolicyLabel})\n"
            f"EXACT PRE-ROUND: {result.exactPreRoundMin}-{result.exactPreRoundMax}"
        )
    else:
        numeric_summary = (
            "NUMERIC VALUE: unavailable (null; never substituted with zero or DPS)"
        )
    return numeric_summary + "\n\n" + _json_text(result.to_dict())


class GoldenGloryApp(tk.Tk):
    """BUILD-003 review UI; canonical behavior remains in ApplicationService."""

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
            ("Paste copied item", self._add_copied),
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
        common = ttk.Frame(notebook, padding=6)
        copied = ttk.Frame(notebook, padding=8)
        manual = ttk.Frame(notebook, padding=8)
        enmity = ttk.Frame(notebook, padding=8)
        flame = ttk.Frame(notebook, padding=8)
        evidence = ttk.Frame(notebook, padding=8)
        notes = ttk.Frame(notebook, padding=8)
        notebook.add(mapping, text="Mapping")
        notebook.add(review, text="PoB review")
        notebook.add(common, text="Common review")
        notebook.add(copied, text="Copied")
        notebook.add(manual, text="Manual gear")
        notebook.add(enmity, text="Enmity")
        notebook.add(flame, text="Flame Link")
        notebook.add(evidence, text="Evidence")
        notebook.add(notes, text="Notes")
        self._build_mapping(mapping)
        self._build_review(review)
        self._build_common_review(common)
        self._build_copied(copied)
        self._build_manual(manual)
        self._build_enmity(enmity)
        self._build_flame_link(flame)
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

    def _build_common_review(self, parent: ttk.Frame) -> None:
        parent.grid_rowconfigure(1, weight=2)
        parent.grid_rowconfigure(3, weight=3)
        parent.grid_columnconfigure(0, weight=1)
        filters = ttk.Frame(parent)
        filters.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.common_provenance_var = tk.StringVar(value="all")
        self.common_role_var = tk.StringVar(value="all")
        self.common_recognition_var = tk.StringVar(value="all")
        filter_specs = (
            (
                "Provenance",
                self.common_provenance_var,
                ("all", "pob-import", "copied-text", "manual-entry"),
            ),
            (
                "Role",
                self.common_role_var,
                ("all", "player", "mercenary", "unassigned"),
            ),
            (
                "Recognition",
                self.common_recognition_var,
                (
                    "all",
                    "recognized",
                    "partially-recognized",
                    "unrecognized",
                    "malformed",
                    "manually-required",
                ),
            ),
        )
        column = 0
        for label, variable, values in filter_specs:
            ttk.Label(filters, text=label).grid(row=0, column=column, padx=(0, 4))
            combo = ttk.Combobox(
                filters,
                textvariable=variable,
                values=values,
                state="readonly",
                width=21,
            )
            combo.grid(row=0, column=column + 1, padx=(0, 10))
            combo.bind("<<ComboboxSelected>>", self._common_filter_changed)
            column += 2

        columns = (
            "provenance",
            "roles",
            "source",
            "slot",
            "identity",
            "recognition",
            "warnings",
        )
        self.common_tree = ttk.Treeview(parent, columns=columns, show="headings")
        for name, heading, width in (
            ("provenance", "Provenance", 110),
            ("roles", "Explicit role binding(s)", 170),
            ("source", "Source / entry", 155),
            ("slot", "Slot / assignment", 180),
            ("identity", "Recognized identity", 220),
            ("recognition", "Recognition state", 160),
            ("warnings", "Warnings", 240),
        ):
            self.common_tree.heading(name, text=heading)
            self.common_tree.column(name, width=width, minwidth=80)
        self.common_tree.grid(row=1, column=0, sticky="nsew")
        common_scroll = ttk.Scrollbar(
            parent, orient="vertical", command=self.common_tree.yview
        )
        self.common_tree.configure(yscrollcommand=common_scroll.set)
        common_scroll.grid(row=1, column=1, sticky="ns")
        self.common_tree.bind("<<TreeviewSelect>>", self._show_common_review_detail)
        ttk.Button(
            parent,
            text="Copy exact raw text",
            command=self._copy_common_raw,
        ).grid(row=2, column=0, sticky="w", pady=6)
        detail_frame = ttk.Frame(parent)
        detail_frame.grid(row=3, column=0, columnspan=2, sticky="nsew")
        detail_frame.grid_rowconfigure(0, weight=1)
        detail_frame.grid_columnconfigure(0, weight=1)
        self.common_detail = self._text_box(detail_frame)
        self.common_detail.grid(row=0, column=0, sticky="nsew")

    def _build_copied(self, parent: ttk.Frame) -> None:
        parent.grid_rowconfigure(1, weight=2)
        parent.grid_rowconfigure(3, weight=3)
        parent.grid_columnconfigure(0, weight=1)
        ttk.Label(
            parent,
            text=(
                "Copied text is retained exactly. Role, slot, label, and note are "
                "explicit build-state metadata; recognition never assigns ownership."
            ),
            wraplength=850,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        columns = ("id", "role", "slot", "label", "recognition", "note")
        self.copied_tree = ttk.Treeview(parent, columns=columns, show="headings")
        for name, heading, width in (
            ("id", "Entry ID", 120),
            ("role", "Explicit role", 110),
            ("slot", "Slot label", 130),
            ("label", "User label", 170),
            ("recognition", "Recognition", 160),
            ("note", "Note", 260),
        ):
            self.copied_tree.heading(name, text=heading)
            self.copied_tree.column(name, width=width, minwidth=75)
        self.copied_tree.grid(row=1, column=0, sticky="nsew")
        copied_scroll = ttk.Scrollbar(
            parent, orient="vertical", command=self.copied_tree.yview
        )
        self.copied_tree.configure(yscrollcommand=copied_scroll.set)
        copied_scroll.grid(row=1, column=1, sticky="ns")
        self.copied_tree.bind("<<TreeviewSelect>>", self._show_copied_detail)
        buttons = ttk.Frame(parent)
        buttons.grid(row=2, column=0, sticky="w", pady=6)
        for column, (label, command) in enumerate(
            (
                ("Paste copied item", self._add_copied),
                ("Edit explicit metadata", self._edit_copied),
                ("Delete", self._delete_copied),
            )
        ):
            ttk.Button(buttons, text=label, command=command).grid(
                row=0, column=column, padx=(0, 5)
            )
        detail_frame = ttk.Frame(parent)
        detail_frame.grid(row=3, column=0, columnspan=2, sticky="nsew")
        detail_frame.grid_rowconfigure(0, weight=1)
        detail_frame.grid_columnconfigure(0, weight=1)
        self.copied_detail = self._text_box(detail_frame)
        self.copied_detail.grid(row=0, column=0, sticky="nsew")

    def _build_enmity(self, parent: ttk.Frame) -> None:
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        ttk.Label(
            parent,
            text=(
                "Manual isolated output only — Path of Exile 1 3.29.1. "
                "No sheet derivation, resistance-penalty reconstruction, aggregate "
                "penetration, enemy resistance, damage, or DPS is calculated."
            ),
            wraplength=900,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))
        split = ttk.Panedwindow(parent, orient="vertical")
        split.grid(row=1, column=0, sticky="nsew")
        form = ttk.Frame(split, padding=(0, 0, 0, 6))
        output = ttk.Frame(split)
        # Keep the form at its requested height so its final context entry and
        # Apply button cannot be hidden behind the output pane. The output pane
        # receives all surplus vertical space.
        split.add(form, weight=0)
        split.add(output, weight=1)
        form.grid_columnconfigure(0, weight=1)
        input_notebook = ttk.Notebook(form)
        input_notebook.grid(row=0, column=0, sticky="nsew")
        numeric = ttk.Frame(input_notebook, padding=6)
        states = ttk.Frame(input_notebook, padding=6)
        context = ttk.Frame(input_notebook, padding=6)
        input_notebook.add(numeric, text="Numbers")
        input_notebook.add(states, text="States")
        input_notebook.add(context, text="Context")
        numeric.grid_columnconfigure(0, weight=1)
        states.grid_columnconfigure(0, weight=1)
        context.grid_columnconfigure(0, weight=1)
        context.grid_columnconfigure(1, weight=1)

        self.enmity_u_var = tk.StringVar()
        self.enmity_m_var = tk.StringVar()
        self.enmity_target_var = tk.StringVar()
        self.enmity_equipped_var = tk.StringVar()
        self.enmity_inclusion_var = tk.StringVar()
        self.enmity_ack_var = tk.StringVar()
        self.enmity_observed_var = tk.StringVar()
        row = 0
        for label, variable in (
            ("Final Uncapped Fire Resistance U", self.enmity_u_var),
            ("Maximum Fire Resistance M", self.enmity_m_var),
            ("Optional Enmity-only target T", self.enmity_target_var),
        ):
            field_row = row * 2
            ttk.Label(numeric, text=label).grid(
                row=field_row,
                column=0,
                sticky="w",
                pady=(2, 0),
            )
            ttk.Entry(numeric, textvariable=variable, width=18).grid(
                row=field_row + 1,
                column=0,
                sticky="ew",
                pady=(0, 2),
            )
            row += 1
        state_row = 0
        for label, variable, values in (
            (
                "Enmity equipped state",
                self.enmity_equipped_var,
                ("unknown", "equipped", "not-equipped"),
            ),
            (
                "Equipment inclusion state",
                self.enmity_inclusion_var,
                ("unrecorded", "included", "excluded", "unknown"),
            ),
            (
                "Target-version acknowledgement",
                self.enmity_ack_var,
                ("unknown", "confirmed-3.29.1", "other-version"),
            ),
        ):
            field_row = state_row * 2
            ttk.Label(states, text=label).grid(
                row=field_row,
                column=0,
                sticky="w",
                pady=(2, 0),
            )
            ttk.Combobox(
                states,
                textvariable=variable,
                values=values,
                state="readonly",
                width=17,
            ).grid(
                row=field_row + 1,
                column=0,
                sticky="ew",
                pady=(0, 2),
            )
            state_row += 1
        ttk.Label(states, text="Optional observed item material").grid(
            row=state_row * 2,
            column=0,
            sticky="w",
            pady=(2, 0),
        )
        self.enmity_observed_combo = ttk.Combobox(
            states,
            textvariable=self.enmity_observed_var,
            state="readonly",
            width=17,
        )
        self.enmity_observed_combo.grid(
            row=state_row * 2 + 1,
            column=0,
            sticky="ew",
            pady=(0, 2),
        )

        self.enmity_context_vars: dict[str, tk.StringVar] = {}
        context_labels = {
            "mercenaryIdentityLevel": "Mercenary identity / level",
            "activeStateSelection": "Active-state selection",
            "zoneOrUiContext": "Zone or UI context",
            "relevantEffectsConditions": "Relevant effects / conditions",
            "equipmentStateDescription": "Equipment-state description",
            "captureTimingDescription": "Capture timing description",
        }
        for context_row, field in enumerate(MEASUREMENT_CONTEXT_FIELDS):
            variable = tk.StringVar()
            self.enmity_context_vars[field] = variable
            field_column = context_row % 2
            field_row = (context_row // 2) * 2
            ttk.Label(context, text=context_labels[field]).grid(
                row=field_row,
                column=field_column,
                sticky="w",
                padx=(0, 4) if field_column == 0 else (4, 0),
                pady=(2, 0),
            )
            ttk.Entry(context, textvariable=variable, width=24).grid(
                row=field_row + 1,
                column=field_column,
                sticky="ew",
                padx=(0, 4) if field_column == 0 else (4, 0),
                pady=(0, 2),
            )
        ttk.Button(
            form,
            text="Apply manual Enmity input",
            command=self._apply_enmity_input,
        ).grid(row=1, column=0, sticky="w", pady=(4, 1))

        output.grid_rowconfigure(0, weight=1)
        output.grid_columnconfigure(0, weight=1)
        notebook = ttk.Notebook(output)
        notebook.grid(row=0, column=0, sticky="nsew")
        result_page = ttk.Frame(notebook)
        gate_page = ttk.Frame(notebook)
        notebook.add(result_page, text="Result and target")
        notebook.add(gate_page, text="Exact evidence gates")
        for page in (result_page, gate_page):
            page.grid_rowconfigure(0, weight=1)
            page.grid_columnconfigure(0, weight=1)
        self.enmity_result_detail = self._text_box(result_page)
        self.enmity_result_detail.grid(row=0, column=0, sticky="nsew")
        self.enmity_gate_detail = self._text_box(gate_page)
        self.enmity_gate_detail.grid(row=0, column=0, sticky="nsew")
        self._observed_locator_by_display: dict[str, ReviewSourceLocator | None] = {
            "(none)": None
        }

    def _build_flame_link(self, parent: ttk.Frame) -> None:
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        ttk.Label(
            parent,
            text=(
                "Manual-first Flame Link player chain — Added Fire Damage granted to "
                "linked Mercenary. Never DPS. Quality does not affect damage. "
                "Unknown conditionals and additional levels block resolution."
            ),
            wraplength=900,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        outer = ttk.Frame(parent)
        outer.grid(row=1, column=0, sticky="nsew")
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        form = ttk.Frame(canvas, padding=(0, 0, 8, 0))
        form_window = canvas.create_window((0, 0), window=form, anchor="nw")

        def _sync_scroll(_event: object | None = None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(form_window, width=canvas.winfo_width())

        form.bind("<Configure>", _sync_scroll)
        canvas.bind("<Configure>", _sync_scroll)

        self.flame_gg_allocated_var = tk.StringVar()
        self.flame_gg_target_var = tk.StringVar()
        self.flame_gg_lr_var = tk.StringVar()
        self.flame_direct_var = tk.StringVar()
        self.flame_life_var = tk.StringVar()
        self.flame_base_level_var = tk.StringVar()
        self.flame_powerful_state_var = tk.StringVar()
        self.flame_inspiring_state_var = tk.StringVar()
        self.flame_empowered_state_var = tk.StringVar()
        self.flame_recognize_var = tk.StringVar()

        row = 0
        gg = ttk.Labelframe(form, text="Golden Glory / Light Radius", padding=6)
        gg.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        gg.grid_columnconfigure(1, weight=1)
        ttk.Label(gg, text="Allocated").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            gg,
            textvariable=self.flame_gg_allocated_var,
            values=("unknown", "allocated", "not-allocated"),
            state="readonly",
            width=18,
        ).grid(row=0, column=1, sticky="w", padx=(6, 0))
        ttk.Label(gg, text="Mercenary target").grid(row=1, column=0, sticky="w")
        ttk.Combobox(
            gg,
            textvariable=self.flame_gg_target_var,
            values=("unknown", "yes", "no"),
            state="readonly",
            width=18,
        ).grid(row=1, column=1, sticky="w", padx=(6, 0))
        ttk.Label(gg, text="Reviewed Light Radius %").grid(row=2, column=0, sticky="w")
        ttk.Entry(gg, textvariable=self.flame_gg_lr_var, width=18).grid(
            row=2, column=1, sticky="w", padx=(6, 0)
        )

        row += 1
        direct = ttk.Labelframe(form, text="Direct Link Skill Buff Effect", padding=6)
        direct.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        direct.grid_columnconfigure(1, weight=1)
        ttk.Label(direct, text="Reviewed direct %").grid(row=0, column=0, sticky="w")
        ttk.Entry(direct, textvariable=self.flame_direct_var, width=18).grid(
            row=0, column=1, sticky="w", padx=(6, 0)
        )

        row += 1
        conditional = ttk.Labelframe(form, text="Conditional contributions", padding=6)
        conditional.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        conditional.grid_columnconfigure(1, weight=1)
        ttk.Label(conditional, text="Powerful Bond (20%)").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Combobox(
            conditional,
            textvariable=self.flame_powerful_state_var,
            values=("unknown", "active", "inactive"),
            state="readonly",
            width=18,
        ).grid(row=0, column=1, sticky="w", padx=(6, 0))
        ttk.Label(conditional, text="Inspiring Bond (20%)").grid(
            row=1, column=0, sticky="w"
        )
        ttk.Combobox(
            conditional,
            textvariable=self.flame_inspiring_state_var,
            values=("unknown", "active", "inactive"),
            state="readonly",
            width=18,
        ).grid(row=1, column=1, sticky="w", padx=(6, 0))

        row += 1
        level = ttk.Labelframe(form, text="Flame Link level", padding=6)
        level.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        level.grid_columnconfigure(1, weight=1)
        ttk.Label(level, text="Base level").grid(row=0, column=0, sticky="w")
        ttk.Entry(level, textvariable=self.flame_base_level_var, width=18).grid(
            row=0, column=1, sticky="w", padx=(6, 0)
        )
        ttk.Label(level, text="Empowered Bond (+2 levels)").grid(
            row=1, column=0, sticky="w"
        )
        ttk.Combobox(
            level,
            textvariable=self.flame_empowered_state_var,
            values=("unknown", "active", "inactive"),
            state="readonly",
            width=18,
        ).grid(row=1, column=1, sticky="w", padx=(6, 0))

        row += 1
        life = ttk.Labelframe(form, text="Luminary Maximum Life", padding=6)
        life.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        life.grid_columnconfigure(1, weight=1)
        ttk.Label(life, text="Reviewed life").grid(row=0, column=0, sticky="w")
        ttk.Entry(life, textvariable=self.flame_life_var, width=18).grid(
            row=0, column=1, sticky="w", padx=(6, 0)
        )

        row += 1
        recognize = ttk.Labelframe(
            form, text="Advisory recognition (does not auto-apply)", padding=6
        )
        recognize.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        recognize.grid_columnconfigure(0, weight=1)
        ttk.Entry(recognize, textvariable=self.flame_recognize_var).grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Button(
            recognize,
            text="Recognize text",
            command=self._recognize_flame_link_text,
        ).grid(row=0, column=1, padx=(6, 0))
        recognition_page = ttk.Frame(recognize)
        recognition_page.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        recognition_page.grid_rowconfigure(0, weight=1)
        recognition_page.grid_columnconfigure(0, weight=1)
        self.flame_recognition_detail = self._text_box(recognition_page)
        self.flame_recognition_detail.grid(row=0, column=0, sticky="nsew")
        self.flame_recognition_detail.configure(height=6)

        row += 1
        ttk.Button(
            form,
            text="Apply Flame Link input",
            command=self._apply_flame_link_input,
        ).grid(row=row, column=0, sticky="w", pady=(0, 6))

        row += 1
        result_frame = ttk.Labelframe(form, text="Result", padding=6)
        result_frame.grid(row=row, column=0, sticky="nsew")
        result_frame.grid_rowconfigure(0, weight=1)
        result_frame.grid_columnconfigure(0, weight=1)
        result_page = ttk.Frame(result_frame)
        result_page.grid(row=0, column=0, sticky="nsew")
        result_page.grid_rowconfigure(0, weight=1)
        result_page.grid_columnconfigure(0, weight=1)
        self.flame_result_detail = self._text_box(result_page)
        self.flame_result_detail.grid(row=0, column=0, sticky="nsew")
        self.flame_result_detail.configure(height=16)

    def _build_evidence(self, parent: ttk.Frame) -> None:
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_rowconfigure(2, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        ttk.Label(
            parent,
            text=(
                "Unavailable or deferred mechanics are evidence states, never numeric zero. "
                "Manual-first Flame Link granted damage and the isolated manual Enmity "
                "contribution are available on their own tabs. Outputs below remain blocked."
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
            try:
                object.__getattribute__(self, "enmity_u_var")
            except AttributeError:
                pass
            else:
                self._refresh_enmity()
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
            observed = self.service.state["enmityManualInput"][
                "observedItemReference"
            ]
            clears_observed = bool(
                observed is not None
                and observed["provenanceKind"] == "pob-import"
            )
            confirmed = messagebox.askyesno(
                "Replace successful import?",
                (
                    "The new import is staged. Replacing the existing import clears "
                    "player and Mercenary occurrence mappings, preserves manual "
                    "equipment and notes, and requires explicit mapping again."
                    + (
                        " It also atomically clears the selected observed-item "
                        "reference because that reference belongs to the old PoB source."
                        if clears_observed
                        else ""
                    )
                ),
                icon="warning",
                parent=self,
            )
            self._guard(
                lambda: self.service.confirm_pending_import(
                    confirmed,
                    clear_observed_reference=confirmed and clears_observed,
                )
            )
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
        observed = self.service.state["enmityManualInput"]["observedItemReference"]
        clears_observed = observed == {
            "provenanceKind": "manual-entry",
            "sourceId": entry["entryId"],
        }
        confirmed = messagebox.askyesno(
            "Delete manual entry?",
            (
                f"Delete {entry['entryId']}? This explicit action cannot be undone."
                + (
                    " The observed-item reference will be cleared atomically."
                    if clears_observed
                    else ""
                )
            ),
            icon="warning",
            parent=self,
        )
        self._guard(
            lambda: self.service.delete_manual_entry(
                entry["entryId"],
                confirmed=confirmed,
                clear_observed_reference=confirmed and clears_observed,
            )
        )

    def _selected_copied(self) -> dict[str, Any] | None:
        selected = self.copied_tree.selection()
        if not selected:
            return None
        identifier = selected[0]
        return next(
            (
                entry
                for entry in self.service.state["copiedItemEntries"]
                if entry["entryId"] == identifier
            ),
            None,
        )

    def _add_copied(self) -> None:
        dialog = CopiedItemDialog(self, title="Paste copied item")
        if dialog.value is None:
            return
        value = dialog.value
        self._guard(
            lambda: self.service.add_copied_entry(
                value["rawText"],
                role=value["role"],
                slot_label=value["slotLabel"],
                user_label=value["userLabel"],
                note=value["note"],
            )
        )

    def _edit_copied(self) -> None:
        entry = self._selected_copied()
        if entry is None:
            messagebox.showinfo("Copied items", "Select an entry first.", parent=self)
            return
        dialog = CopiedItemDialog(
            self,
            title=f"Edit metadata for {entry['entryId']}",
            initial=entry,
            metadata_only=True,
        )
        if dialog.value is None:
            return
        value = dialog.value
        self._guard(
            lambda: self.service.edit_copied_entry(
                entry["entryId"],
                role=value["role"],
                slot_label=value["slotLabel"],
                user_label=value["userLabel"],
                note=value["note"],
            )
        )

    def _delete_copied(self) -> None:
        entry = self._selected_copied()
        if entry is None:
            messagebox.showinfo("Copied items", "Select an entry first.", parent=self)
            return
        observed = self.service.state["enmityManualInput"]["observedItemReference"]
        clears_observed = observed == {
            "provenanceKind": "copied-text",
            "sourceId": entry["entryId"],
        }
        confirmed = messagebox.askyesno(
            "Delete copied item?",
            (
                f"Delete {entry['entryId']} and its exact retained source text?"
                + (
                    " The observed-item reference will be cleared atomically."
                    if clears_observed
                    else ""
                )
            ),
            icon="warning",
            parent=self,
        )
        self._guard(
            lambda: self.service.delete_copied_entry(
                entry["entryId"],
                confirmed=confirmed,
                clear_observed_reference=confirmed and clears_observed,
            )
        )

    def _common_filter_changed(self, _event: tk.Event[Any]) -> None:
        if not self._refreshing:
            self._refresh_common_review()

    def _apply_enmity_input(self) -> None:
        display = self.enmity_observed_var.get() or "(none)"
        locator = self._observed_locator_by_display.get(display)
        context = {
            field: variable.get()
            for field, variable in self.enmity_context_vars.items()
        }
        self._guard(
            lambda: self.service.set_enmity_input(
                final_uncapped_fire_resistance=self.enmity_u_var.get() or None,
                maximum_fire_resistance=self.enmity_m_var.get() or None,
                equipped_state=self.enmity_equipped_var.get(),
                equipment_inclusion_state=self.enmity_inclusion_var.get(),
                measurement_context=context,
                target_game_version_acknowledgement=self.enmity_ack_var.get(),
                observed_item_reference=locator,
                target=self.enmity_target_var.get() or None,
            )
        )

    def _apply_flame_link_input(self) -> None:
        chain = self.service.state["flameLinkPlayerChain"]
        lr = self.flame_gg_lr_var.get().strip()
        direct = self.flame_direct_var.get().strip()
        life = self.flame_life_var.get().strip()
        try:
            base_level = int(self.flame_base_level_var.get().strip())
        except ValueError:
            messagebox.showerror(
                "FLAME_LINK_BASE_LEVEL",
                "Base Flame Link level must be an integer",
                parent=self,
            )
            return

        def apply() -> None:
            conditionals = []
            for entry in chain["conditionalContributions"]:
                updated = dict(entry)
                if entry["contributionId"] == "powerful-bond":
                    updated["conditionState"] = self.flame_powerful_state_var.get()
                elif entry["contributionId"] == "inspiring-bond":
                    updated["conditionState"] = self.flame_inspiring_state_var.get()
                conditionals.append(updated)
            additions = []
            for entry in chain["flameLinkLevel"]["additionalLinkGemLevels"]:
                updated = dict(entry)
                if entry["contributionId"] == "empowered-bond":
                    updated["activeState"] = self.flame_empowered_state_var.get()
                additions.append(updated)
            provenance = (
                "manual-benchmark-default"
                if base_level == 21
                else "manual-reviewed"
            )
            self.service.set_flame_link_input(
                golden_glory={
                    "allocatedState": self.flame_gg_allocated_var.get(),
                    "mercenaryTargetState": self.flame_gg_target_var.get(),
                    "reviewedLightRadiusPct": lr or None,
                    "provenanceKind": (
                        "manual-reviewed" if lr else "unreviewed"
                    ),
                    "reviewState": "reviewed" if lr else "unreviewed",
                    "rawSourceText": chain["goldenGlory"].get("rawSourceText", ""),
                },
                direct_link_buff_effect={
                    "reviewedDirectPct": direct or None,
                    "provenanceKind": (
                        "manual-reviewed" if direct else "unreviewed"
                    ),
                    "reviewState": "reviewed" if direct else "unreviewed",
                    "rawSourceText": chain["directLinkBuffEffect"].get(
                        "rawSourceText", ""
                    ),
                },
                conditional_contributions=conditionals,
                flame_link_level={
                    "baseLevel": base_level,
                    "baseLevelProvenance": provenance,
                    "additionalLinkGemLevels": additions,
                },
                luminary_maximum_life={
                    "reviewedLife": life or None,
                    "provenanceKind": "manual-reviewed" if life else "unreviewed",
                    "reviewState": "reviewed" if life else "unreviewed",
                    "rawSourceText": chain["luminaryMaximumLife"].get(
                        "rawSourceText", ""
                    ),
                },
            )

        self._guard(apply)

    def _recognize_flame_link_text(self) -> None:
        text = self.flame_recognize_var.get()
        lines = self.service.recognize_player_chain_from_text(text)
        self._set_readonly_text(
            self.flame_recognition_detail,
            _json_text([line.to_dict() for line in lines])
            if lines
            else "No advisory player-chain lines recognized.",
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
            self._refresh_common_review()
            self._refresh_copied()
            self._refresh_manual()
            self._refresh_enmity()
            self._refresh_flame_link()
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
                    f"Migration: {'upgrade pending' if status['migrationPending'] else 'current v3'}",
                    f"Importer warnings: {status['importerWarnings']}",
                    f"Runtime evidence: {status['runtimeEvidence']}",
                    f"Enmity output: {status['enmityOutput']}",
                    f"Flame Link: {status['flameLinkOutput']}",
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

    @staticmethod
    def _active_filter(value: str) -> str | None:
        return None if value == "all" else value

    def _refresh_common_review(self) -> None:
        selected = self.common_tree.selection()
        selected_id = selected[0] if selected else None
        self.common_tree.delete(*self.common_tree.get_children())
        reviews = self.service.item_reviews(
            provenance=self._active_filter(self.common_provenance_var.get()),
            role=self._active_filter(self.common_role_var.get()),
            recognition_state=self._active_filter(self.common_recognition_var.get()),
        )
        for review in reviews:
            self.common_tree.insert(
                "",
                "end",
                iid=review.reviewInstanceId,
                values=_review_row(review),
            )
        children = self.common_tree.get_children()
        if selected_id in children:
            self.common_tree.selection_set(selected_id)
        elif children:
            self.common_tree.selection_set(children[0])
        if children:
            self._show_common_review_detail(None)
        else:
            self._set_readonly_text(
                self.common_detail,
                "No common item-review instance matches the current filters.",
            )

    def _refresh_copied(self) -> None:
        selected = self.copied_tree.selection()
        selected_id = selected[0] if selected else None
        self.copied_tree.delete(*self.copied_tree.get_children())
        reviews = {
            review.sourceLocator.sourceId: review
            for review in self.service.item_reviews(provenance="copied-text")
        }
        for entry in self.service.state["copiedItemEntries"]:
            review = reviews[entry["entryId"]]
            self.copied_tree.insert(
                "",
                "end",
                iid=entry["entryId"],
                values=(
                    entry["entryId"],
                    entry["role"],
                    entry["slotLabel"] or "none",
                    entry["userLabel"] or "none",
                    review.recognitionState,
                    entry["note"],
                ),
            )
        children = self.copied_tree.get_children()
        if selected_id in children:
            self.copied_tree.selection_set(selected_id)
        elif children:
            self.copied_tree.selection_set(children[0])
        if children:
            self._show_copied_detail(None)
        else:
            self._set_readonly_text(
                self.copied_detail,
                "No copied-item entries. Use Paste copied item to retain one exactly.",
            )

    def _refresh_enmity(self) -> None:
        state = self.service.state["enmityManualInput"]
        self.enmity_u_var.set(state["finalUncappedFireResistance"] or "")
        self.enmity_m_var.set(state["maximumFireResistance"] or "")
        self.enmity_target_var.set(state["target"] or "")
        self.enmity_equipped_var.set(state["equippedState"])
        self.enmity_inclusion_var.set(state["equipmentInclusionState"])
        self.enmity_ack_var.set(state["targetGameVersionAcknowledgement"])
        for field, variable in self.enmity_context_vars.items():
            variable.set(state["measurementContext"][field])

        options: dict[str, ReviewSourceLocator | None] = {"(none)": None}
        selected_display = "(none)"
        selected_locator = state["observedItemReference"]
        for review in self.service.item_reviews():
            display = (
                f"{review.sourceLocator.key} | {_review_identity_text(review)} | "
                f"{review.recognitionState}"
            )
            options[display] = review.sourceLocator
            if (
                selected_locator is not None
                and review.sourceLocator.to_dict() == selected_locator
            ):
                selected_display = display
        self._observed_locator_by_display = options
        self.enmity_observed_combo.configure(values=tuple(options))
        self.enmity_observed_var.set(selected_display)

        result = self.service.enmity_result()
        observed_review = (
            None
            if selected_locator is None
            else self.service.review_for_locator(selected_locator)
        )
        observed_summary = (
            None
            if observed_review is None
            else {
                "sourceLocator": observed_review.sourceLocator.to_dict(),
                "rawTextSha256": observed_review.rawTextSha256,
                "recognitionState": observed_review.recognitionState,
                "identity": (
                    None
                    if observed_review.parsedIdentity is None
                    else observed_review.parsedIdentity.to_dict()
                ),
                "ownershipInferred": False,
                "equippedStateInferred": False,
            }
        )
        self._set_readonly_text(
            self.enmity_result_detail,
            _enmity_result_text(result, observed_summary),
        )
        self._set_readonly_text(
            self.enmity_gate_detail,
            _json_text(self.service.runtime_evidence_status()),
        )

    def _refresh_flame_link(self) -> None:
        chain = self.service.state["flameLinkPlayerChain"]
        golden = chain["goldenGlory"]
        self.flame_gg_allocated_var.set(golden["allocatedState"])
        self.flame_gg_target_var.set(golden["mercenaryTargetState"])
        self.flame_gg_lr_var.set(golden["reviewedLightRadiusPct"] or "")
        self.flame_direct_var.set(
            chain["directLinkBuffEffect"]["reviewedDirectPct"] or ""
        )
        self.flame_life_var.set(chain["luminaryMaximumLife"]["reviewedLife"] or "")
        self.flame_base_level_var.set(str(chain["flameLinkLevel"]["baseLevel"]))
        powerful = next(
            (
                entry
                for entry in chain["conditionalContributions"]
                if entry["contributionId"] == "powerful-bond"
            ),
            {"conditionState": "unknown"},
        )
        inspiring = next(
            (
                entry
                for entry in chain["conditionalContributions"]
                if entry["contributionId"] == "inspiring-bond"
            ),
            {"conditionState": "unknown"},
        )
        empowered = next(
            (
                entry
                for entry in chain["flameLinkLevel"]["additionalLinkGemLevels"]
                if entry["contributionId"] == "empowered-bond"
            ),
            {"activeState": "unknown"},
        )
        self.flame_powerful_state_var.set(powerful["conditionState"])
        self.flame_inspiring_state_var.set(inspiring["conditionState"])
        self.flame_empowered_state_var.set(empowered["activeState"])
        self._set_readonly_text(
            self.flame_result_detail,
            _flame_link_result_text(self.service.flame_link_result()),
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

    def _selected_common_review(self) -> Any | None:
        selected = self.common_tree.selection()
        if not selected:
            return None
        identifier = selected[0]
        return next(
            (
                review
                for review in self.service.item_reviews()
                if review.reviewInstanceId == identifier
            ),
            None,
        )

    def _show_common_review_detail(
        self, _event: tk.Event[Any] | None
    ) -> None:
        review = self._selected_common_review()
        if review is not None:
            self._set_readonly_text(self.common_detail, _review_detail_text(review))

    def _copy_common_raw(self) -> None:
        review = self._selected_common_review()
        if review is None:
            messagebox.showinfo("Common item review", "Select an item first.", parent=self)
            return
        self.clipboard_clear()
        self.clipboard_append(review.exactRawText)

    def _show_copied_detail(self, _event: tk.Event[Any] | None) -> None:
        entry = self._selected_copied()
        if entry is None:
            return
        review = self.service.review_for_locator(
            ReviewSourceLocator("copied-text", entry["entryId"])
        )
        if review is not None:
            self._set_readonly_text(self.copied_detail, _review_detail_text(review))

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
